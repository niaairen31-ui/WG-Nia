"""Room batch orchestrator (TICKET-0042). Two phases mirroring the region
generator: generate_room_batch_manifest(anchor_id, count, db) runs the
manifest model call and returns it for creator editing (Phase A);
generate_room_batch_draft (BRIEF-0042-b) turns the edited manifest into one
fiche per room. Writes NO canon -- every draft is ephemeral until the atomic
commit route (BRIEF-0042-e). Type authority is the manifest, validated
against location_type_catalog (P1), NEVER the _LOCATION_TYPES enum."""

from __future__ import annotations

import re
import unicodedata
from typing import Any, Optional

from sqlmodel import Session, select

from . import llm_parse
from .entity_author import AUTHOR_MODEL, generate_entity_draft
from .models import Entity, Location, LocationSubculture, LocationTypeCatalog, PromptTemplate, Relation
from .ollama_client import OllamaError, chat
from .prompt_registry import effective_model
from .prompt_store import current_prompt
from .spatial_author import _catalog_row

MIN_COUNT = 3
MAX_COUNT = 25

_ANCHOR_PARENT_KEY = "__anchor__"
_SELF_PARENT_KEY = "__self__"
_UNRESOLVED_PARENT_KEY = "__unresolved__"

_SLUG_NON_WORD = re.compile(r"[^a-z0-9]+")


def _load_manifest_template(db: Session) -> PromptTemplate | None:
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.usage == "room_batch_manifest")
        .where(PromptTemplate.is_active == True)  # noqa: E712
    )
    return db.exec(stmt).first()


def _name_key(name: str) -> str:
    """Normalize a name for dedup/resolution comparison only (mirrors
    region_author._name_key) — the surviving row keeps its original,
    unnormalized name."""
    s = unicodedata.normalize("NFC", name)
    s = s.replace("’", "'").replace("ʼ", "'").replace("`", "'")
    s = " ".join(s.split())
    return s.lower()


def _dedupe_by_name(raw: Any, notes: list[str]) -> list[dict]:
    """Drop later case-insensitive duplicate room names (mirrors
    region_author._dedupe_by_name)."""
    rows: list[dict] = []
    if not isinstance(raw, list):
        return rows
    seen: set[str] = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        key = _name_key(name)
        if key in seen:
            notes.append(f"Pièce dupliquée ignorée : '{name}'")
            continue
        seen.add(key)
        rows.append(item)
    return rows


def _one_line(description: Optional[str]) -> str:
    """First sentence, or first ~140 chars, of a sibling's description."""
    if not isinstance(description, str) or not description.strip():
        return ""
    text = description.strip()
    for sep in (". ", "! ", "? "):
        idx = text.find(sep)
        if idx != -1:
            return text[: idx + 1].strip()
    if len(text) <= 140:
        return text
    return text[:140].rstrip() + "…"


def _compose_batch_context(anchor_id: str, anchor_entity: Entity, db: Session) -> dict:
    """I1 context: anchor fiche + non-hidden subculture + canon siblings
    (name/type/one_line) + existing connects_to edges among those siblings.
    NOTHING else: no hidden subculture, no discoverable_detail, no NPC.
    """
    anchor_location = db.get(Location, anchor_id)

    subculture_rows = db.exec(
        select(LocationSubculture).where(
            LocationSubculture.location_id == anchor_id,
            LocationSubculture.is_hidden == False,  # noqa: E712
        )
    ).all()

    anchor = {
        "name": anchor_entity.name,
        "location_type": anchor_location.location_type if anchor_location else None,
        "description": anchor_entity.description,
        "access_level": anchor_location.access_level if anchor_location else None,
        "subculture": {row.key: row.value for row in subculture_rows},
    }

    sibling_locations = db.exec(
        select(Location).where(Location.parent_location_id == anchor_id)
    ).all()
    sibling_ids = [loc.id for loc in sibling_locations]
    sibling_entities: dict[str, Entity] = {}
    if sibling_ids:
        sibling_entities = {
            e.id: e for e in db.exec(select(Entity).where(Entity.id.in_(sibling_ids))).all()
        }

    siblings = []
    for loc in sibling_locations:
        entity = sibling_entities.get(loc.id)
        siblings.append(
            {
                "name": entity.name if entity else loc.id,
                "location_type": loc.location_type,
                "one_line": _one_line(entity.description if entity else None),
            }
        )

    edges: list[dict] = []
    if len(sibling_ids) >= 2:
        relations = db.exec(
            select(Relation).where(
                Relation.type == "connects_to",
                Relation.entity_a_id.in_(sibling_ids),
                Relation.entity_b_id.in_(sibling_ids),
            )
        ).all()
        for rel in relations:
            a_entity = sibling_entities.get(rel.entity_a_id)
            b_entity = sibling_entities.get(rel.entity_b_id)
            edges.append(
                {
                    "a_name": a_entity.name if a_entity else rel.entity_a_id,
                    "b_name": b_entity.name if b_entity else rel.entity_b_id,
                }
            )

    return {"anchor": anchor, "siblings": siblings, "edges": edges}


def _catalog_type_names(world_id: str, db: Session) -> list[str]:
    rows = db.exec(
        select(LocationTypeCatalog).where(LocationTypeCatalog.world_id == world_id)
    ).all()
    return [row.name for row in rows]


def _anchor_block(anchor: dict) -> str:
    lines = [f"Nom : {anchor['name']}"]
    if anchor.get("location_type"):
        lines.append(f"Type : {anchor['location_type']}")
    if anchor.get("access_level"):
        lines.append(f"Accès : {anchor['access_level']}")
    if anchor.get("description"):
        lines.append(f"Description : {anchor['description']}")
    for key, value in anchor.get("subculture", {}).items():
        lines.append(f"{key} : {value}")
    return "\n".join(lines)


def _siblings_block(siblings: list[dict]) -> str:
    if not siblings:
        return "(aucune pièce existante sous cet ancre)"
    return "\n".join(
        f"- {s['name']} ({s.get('location_type') or 'type inconnu'}) : {s.get('one_line', '')}"
        for s in siblings
    )


def _edges_block(edges: list[dict]) -> str:
    if not edges:
        return "(aucune liaison existante entre ces pièces)"
    return "\n".join(f"- {e['a_name']} <-> {e['b_name']}" for e in edges)


# ── Manifest parsing + normalization (code judges) ───────────────────────────


def _resolve_parent_keys(rooms: list[dict], anchor_key: str) -> dict[int, str | None]:
    """First pass: raw parent_room -> a stable key per room index.

    A key is one of: None (already anchor), _ANCHOR_PARENT_KEY (equivalent
    to None; never chained through), _SELF_PARENT_KEY, _UNRESOLVED_PARENT_KEY,
    or another room's name_key. Kept separate from the room dict so the
    cycle-detection pass below walks the ORIGINAL resolution, unaffected by
    the forced-attach mutations it makes along the way.
    """
    name_keys = {_name_key(r["name"]) for r in rooms}
    resolved: dict[int, str | None] = {}
    for i, room in enumerate(rooms):
        raw_parent = room.get("parent_room")
        own_key = _name_key(room["name"])
        if not isinstance(raw_parent, str) or not raw_parent.strip():
            resolved[i] = None
            continue
        key = _name_key(raw_parent)
        if key == anchor_key:
            resolved[i] = None
        elif key == own_key:
            resolved[i] = _SELF_PARENT_KEY
        elif key in name_keys:
            resolved[i] = key
        else:
            resolved[i] = _UNRESOLVED_PARENT_KEY
    return resolved


def _detect_cycle(i: int, rooms: list[dict], key_to_index: dict[str, int], resolved: dict[int, str | None]) -> bool:
    """Walk the parent chain from room i; True if it loops back to itself."""
    own_key = _name_key(rooms[i]["name"])
    visited = {own_key}
    cur = resolved[i]
    while cur is not None and cur not in (_SELF_PARENT_KEY, _UNRESOLVED_PARENT_KEY):
        if cur in visited:
            return True
        visited.add(cur)
        next_index = key_to_index.get(cur)
        if next_index is None:
            return False
        cur = resolved[next_index]
    return False


def _normalize_batch_parents(rooms: list[dict], anchor_name: str, notes: list[str]) -> None:
    """K1 spanning tree: force-attach any unresolved name, self-parent or
    cycle participant to the anchor (parent_room = None), noting each.
    Mutates `rooms` in place. Mirrors region_author._normalize_location_parents'
    SHAPE; cycle detection is new (region has no interior cycles to guard)."""
    anchor_key = _name_key(anchor_name)
    resolved = _resolve_parent_keys(rooms, anchor_key)
    key_to_index = {_name_key(r["name"]): i for i, r in enumerate(rooms)}

    for i, room in enumerate(rooms):
        parent_key = resolved[i]
        if parent_key is None:
            room["parent_room"] = None
        elif parent_key == _SELF_PARENT_KEY:
            notes.append(f"Pièce '{room['name']}' — parent = elle-même, rattachée à l'ancre")
            room["parent_room"] = None
        elif parent_key == _UNRESOLVED_PARENT_KEY:
            notes.append(
                f"Pièce '{room['name']}' — parent '{room.get('parent_room')}' introuvable, "
                "rattachée à l'ancre"
            )
            room["parent_room"] = None
        elif _detect_cycle(i, rooms, key_to_index, resolved):
            notes.append(f"Pièce '{room['name']}' — cycle de parenté détecté, rattachée à l'ancre")
            room["parent_room"] = None
        else:
            room["parent_room"] = rooms[key_to_index[parent_key]]["name"]


def _normalize_batch_types(rooms: list[dict], world_id: str, notes: list[str], db: Session) -> None:
    """P1 type validation: a type absent from location_type_catalog is KEPT
    verbatim (never repli-fallen to 'other') and noted; the creator resolves
    it in Phase A. NEVER call entity_author._validate_location_type."""
    for room in rooms:
        type_name = room.get("location_type")
        if not isinstance(type_name, str) or not type_name.strip():
            room["location_type"] = ""
            continue
        if _catalog_row(db, world_id=world_id, type_name=type_name) is None:
            notes.append(
                f"Type '{type_name}' absent du catalogue -- ce lieu naîtra sans bounds "
                "tant que le type n'est pas classifié"
            )


def _normalize_batch_manifest(parsed: dict, anchor_name: str, world_id: str, notes: list[str], db: Session) -> dict:
    """Structural normalization of a parsed room-batch manifest."""
    rooms = _dedupe_by_name(parsed.get("rooms"), notes)
    for room in rooms:
        one_liner = room.get("one_liner")
        room["one_liner"] = one_liner if isinstance(one_liner, str) else ""
    _normalize_batch_types(rooms, world_id, notes, db)
    _normalize_batch_parents(rooms, anchor_name, notes)
    return {"rooms": rooms}


def _parse_batch_manifest_response(raw: str, anchor_name: str, world_id: str, db: Session) -> dict:
    """Returns {"ok": True, "manifest": ..., "notes": [...], "skipped": [...]}
    or {"ok": False, "error": ...}. Never raises."""
    try:
        parsed = llm_parse.extract_object(raw)
    except llm_parse.LlmParseError:
        return {"ok": False, "error": "Model returned non-JSON manifest"}
    if not parsed:
        return {"ok": False, "error": "Model returned an empty or malformed manifest"}

    notes: list[str] = []
    manifest = _normalize_batch_manifest(parsed, anchor_name, world_id, notes, db)
    return {"ok": True, "manifest": manifest, "notes": notes, "skipped": []}


# ── Entry point ───────────────────────────────────────────────────────────


def generate_room_batch_manifest(anchor_id: str, count: int, db: Session) -> dict:
    """Phase A — produce the room-batch manifest for a creator-chosen anchor.

    `count` is clamped to [3, 25] at this boundary only (it bounds the
    request; it never pads a short model response — count shortfall is
    Phase A editing, per ticket decision S). Writes no canon. Never raises
    into the caller: every failure path returns {"ok": False, "error": ...}
    verbatim (missing anchor, missing template, Ollama error,
    malformed/non-JSON manifest).
    """
    anchor_entity = db.get(Entity, anchor_id)
    if anchor_entity is None:
        return {"ok": False, "error": "Anchor location not found"}

    clamped_count = max(MIN_COUNT, min(MAX_COUNT, count))

    template = _load_manifest_template(db)
    if template is None:
        return {"ok": False, "error": "No active pt-room-batch-manifest template found"}

    context = _compose_batch_context(anchor_id, anchor_entity, db)
    catalog_types = _catalog_type_names(anchor_entity.world_id, db)

    version = current_prompt(db, template)
    user_message = (
        version.user_template
        .replace("{anchor_block}", _anchor_block(context["anchor"]))
        .replace("{siblings_block}", _siblings_block(context["siblings"]))
        .replace("{edges_block}", _edges_block(context["edges"]))
        .replace("{catalog_types}", ", ".join(catalog_types) if catalog_types else "(aucun)")
        .replace("{count}", str(clamped_count))
    )

    messages = [
        {"role": "system", "content": version.system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        raw = chat(messages, model=effective_model(template, AUTHOR_MODEL), format="json")
    except OllamaError as exc:
        return {"ok": False, "error": str(exc)}

    result = _parse_batch_manifest_response(raw, context["anchor"]["name"], anchor_entity.world_id, db)
    if not result["ok"]:
        return result
    result["anchor"] = context["anchor"]
    return result


# ── Phase B — per-room fiche generation ──────────────────────────────────────


def _room_local_id(name: str, index: int) -> str:
    """Stable per-batch id: a slug of the room name plus its manifest index."""
    slug = _SLUG_NON_WORD.sub("-", _name_key(name)).strip("-")
    return f"room-{index}-{slug}" if slug else f"room-{index}"


def _compose_room_brief(anchor: dict, manifest: dict, this_room: dict) -> str:
    """Manifest-sourced-only brief: anchor + full manifest as peer context +
    this room highlighted as the one to write. No DB re-read, no secrets."""
    anchor_one_line = _one_line(anchor.get("description"))
    anchor_block = f"{anchor.get('name', '')} ({anchor.get('location_type') or 'type inconnu'})"
    if anchor_one_line:
        anchor_block += f" — {anchor_one_line}"

    rooms = manifest.get("rooms") if isinstance(manifest, dict) else None
    rooms = rooms if isinstance(rooms, list) else []
    lines = []
    for r in rooms:
        if not isinstance(r, dict):
            continue
        parent = r.get("parent_room")
        suffix = f" (sous {parent})" if parent else " (sous l'ancre)"
        lines.append(
            f"- {r.get('name', '')}{suffix} [{r.get('location_type') or 'type inconnu'}] : "
            f"{r.get('one_liner', '')}"
        )
    rooms_block = "\n".join(lines) if lines else "(aucune autre pièce)"

    this_parent = this_room.get("parent_room")
    this_suffix = f" (sous {this_parent})" if this_parent else " (sous l'ancre)"
    return (
        f"--- Ancre ---\n{anchor_block}\n\n"
        f"--- Pièces du lot ---\n{rooms_block}\n\n"
        f"--- Cette pièce à rédiger ---\n"
        f"{this_room.get('name', '')}{this_suffix} — Type : {this_room.get('location_type') or 'inconnu'} — "
        f"{this_room.get('one_liner', '')}"
    )


def _draft_room_with_retry(brief: str, db: Session) -> dict:
    """Retry-once-then-skip (R). `generate_entity_draft` never raises, but a
    defensive backstop mirrors the brief's "parse error, exception, empty
    draft" failure list exactly once before giving up."""
    for _ in range(2):
        try:
            result = generate_entity_draft("location", brief, db)
        except Exception as exc:  # pragma: no cover - defensive backstop only
            result = {"ok": False, "error": str(exc)}
        if result.get("ok"):
            return result
    return result


def generate_room_batch_draft(manifest: dict, anchor: dict, db: Session) -> dict:
    """Phase B — one full location fiche per room, from an already-produced
    (and possibly creator-edited) manifest. Each call sees the whole
    manifest as peer context. Writes no canon anywhere in this function or
    its call path.

    P1 type override: the fiche's `location_type` is always the manifest's
    verbatim value, never the atomic author's echo (which may have
    repli-fallen to "other") — the enum gate (`_validate_location_type`) is
    never touched here. Skipped rooms are NOT reparented; their children
    keep pointing at the absent `parent_room` (the review cascade
    reparents to the anchor at review time, BRIEF-0042-d).
    """
    rooms_in = manifest.get("rooms") if isinstance(manifest, dict) else None
    rooms_in = rooms_in if isinstance(rooms_in, list) else []

    notes: list[str] = []
    skipped: list[dict] = []
    rooms_out: list[dict] = []

    for i, room in enumerate(rooms_in):
        if not isinstance(room, dict) or not room.get("name"):
            continue
        name = room["name"]
        local_id = _room_local_id(name, i)
        brief = _compose_room_brief(anchor, manifest, room)
        result = _draft_room_with_retry(brief, db)
        if not result.get("ok"):
            skipped.append({"local_id": local_id, "name": name, "reason": result.get("error")})
            continue

        for note in result.get("notes", []):
            notes.append(f"{name} : {note}")

        draft = result["draft"]
        manifest_type = room.get("location_type") or ""
        model_type = draft["public"].get("location_type")
        if manifest_type and model_type != manifest_type:
            notes.append(
                f"Pièce '{name}' — type modèle '{model_type}' remplacé par le type "
                f"du manifeste '{manifest_type}'"
            )
        draft["public"]["location_type"] = manifest_type

        rooms_out.append(
            {
                "local_id": local_id,
                "name": name,
                "parent_room": room.get("parent_room"),
                "result": {"draft": draft},
            }
        )

    return {"ok": True, "rooms": rooms_out, "skipped": skipped, "notes": notes}
