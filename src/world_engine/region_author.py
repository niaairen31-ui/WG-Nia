"""Region orchestrator — BRIEF-34, chantier 1; split into two phases by
BRIEF-38. Character-population machinery retired by TICKET-0037 (A1) — new
characters now enter the world exclusively through the group generation
agent.

Turns a creator region brief into a **region draft**: a tree of per-entity
drafts plus draft-local references, produced by composing the atomic entity
generators (`entity_author.generate_entity_draft`). Writes NO canon — mirrors
`entity_author.py`'s posture exactly: the draft is returned to the caller,
ephemeral, never persisted here. `generate_entity_draft` itself is never
modified or monkeypatched — this module composes it as-is.

Two phases, split by a creator checkpoint (BRIEF-38, C1 — one-liner text
editing only): `generate_region_manifest(brief, db)` runs Stage 0 (the
model call producing the manifest) and returns it for the creator to edit;
`generate_region_draft(manifest, db)` takes that manifest (advisory —
re-normalized server-side first) and runs Stages 1-2 (Factions ->
Locations (root first)).

Locked design (see ARCHITECTURE_DECISIONS.md, "REGION GENERATION —
orchestrator (chantier 1)"): A3 (structural skeleton only, link suggestions
are confirm-by-creator), B1 (order Factions -> Locations), C1
(bounded forward context), F1 (sequential, peers as context), I1 (factions
flat in v1), J1 (stage-0 failure aborts; per-entity failure drops and
continues).
"""

from __future__ import annotations

import unicodedata
from typing import Any, Optional

from sqlmodel import Session, select

from . import llm_parse
from .entity_author import AUTHOR_MODEL, generate_entity_draft
from .models import PromptTemplate, World, WorldLaw
from .ollama_client import OllamaError, chat
from .prompt_registry import effective_model
from .prompt_store import current_prompt


def _active_world(db: Session) -> World | None:
    """BRIEF-44: the active world, for the manifest's premise reader."""
    return db.exec(select(World).where(World.is_active == True)).first()  # noqa: E712


def _load_manifest_template(db: Session) -> PromptTemplate | None:
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.usage == "region_manifest")
        .where(PromptTemplate.is_active == True)  # noqa: E712
    )
    return db.exec(stmt).first()


# ── Stage 0 — manifest parsing (code judges, mirroring the atomic parsers) ──


def _name_key(name: str) -> str:
    """Normalize a name for dedup comparison only — apostrophe/whitespace/
    accent-composition variants of the same name fold to one key. The
    surviving row keeps its original, unnormalized name (RECON H1 fix)."""
    s = unicodedata.normalize("NFC", name)
    s = s.replace("’", "'").replace("ʼ", "'").replace("`", "'")
    s = " ".join(s.split())
    return s.lower()


def _dedupe_by_name(raw: Any, label: str, notes: list[str]) -> list[dict]:
    """Drop later case-insensitive duplicate names within one manifest list."""
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
            notes.append(f"{label} dupliqué ignoré : '{name}'")
            continue
        seen.add(key)
        rows.append(item)
    return rows


def _normalize_concept(parsed: dict) -> str:
    """The small local model sometimes emits a list of sentences instead of
    one string — coerce rather than drop (see CLAUDE.md "Local model notes":
    format compliance is best-effort, not guaranteed)."""
    concept_raw = parsed.get("concept")
    if isinstance(concept_raw, str):
        return concept_raw
    if isinstance(concept_raw, list):
        return " ".join(str(part) for part in concept_raw if isinstance(part, str))
    return ""


def _normalize_root_location(locations: list[dict], notes: list[str]) -> Optional[str]:
    """Exactly one root location. Mutates `locations` in place; returns the
    resolved root's name (None if `locations` is empty)."""
    root_indices = [i for i, l in enumerate(locations) if l.get("is_root") is True]
    if not root_indices:
        if locations:
            locations[0]["is_root"] = True
            notes.append(
                f"Aucun lieu racine désigné — '{locations[0]['name']}' promu racine"
            )
    elif len(root_indices) > 1:
        for i in root_indices[1:]:
            locations[i]["is_root"] = False
        notes.append(
            f"Plusieurs lieux racine désignés — seul '{locations[root_indices[0]]['name']}' "
            "reste racine"
        )

    for l in locations:
        if l.get("is_root") is True:
            return l["name"]
    return None


def _normalize_location_parents(
    locations: list[dict], location_names: set[str], root_name: Optional[str], notes: list[str],
) -> None:
    """parent_name validation for non-root locations. Mutates `locations` in place."""
    for l in locations:
        if l.get("is_root") is True:
            l["parent_name"] = None
            continue
        parent_name = l.get("parent_name")
        valid = (
            isinstance(parent_name, str)
            and parent_name.strip().lower() in location_names
            and parent_name.strip().lower() != l["name"].strip().lower()
        )
        if not valid:
            l["parent_name"] = root_name
            notes.append(
                f"Lieu '{l['name']}' — parent invalide ou absent, rattaché à la racine"
            )


def _normalize_manifest(parsed: dict, notes: list[str]) -> tuple[dict, list[dict]]:
    """Structural normalization of a parsed manifest. Returns (manifest, skipped)."""
    skipped: list[dict] = []

    concept = _normalize_concept(parsed)
    factions = _dedupe_by_name(parsed.get("factions"), "Faction", notes)
    locations = _dedupe_by_name(parsed.get("locations"), "Lieu", notes)

    location_names = {l["name"].strip().lower() for l in locations}

    root_name = _normalize_root_location(locations, notes)
    _normalize_location_parents(locations, location_names, root_name, notes)

    manifest = {
        "concept": concept,
        "factions": factions,
        "locations": locations,
    }
    return manifest, skipped


def _parse_manifest_response(raw: str) -> dict:
    """Returns {"ok": True, "manifest": ..., "notes": [...], "skipped": [...]}
    or {"ok": False, "error": ...}. Never raises."""
    try:
        parsed = llm_parse.extract_object(raw)
    except llm_parse.LlmParseError:
        return {"ok": False, "error": "Model returned non-JSON manifest"}
    if not parsed:
        return {"ok": False, "error": "Model returned an empty or malformed manifest"}

    notes: list[str] = []
    manifest, skipped = _normalize_manifest(parsed, notes)
    return {"ok": True, "manifest": manifest, "notes": notes, "skipped": skipped}


# ── Stage 2b — compact peer context, manifest-sourced only ──────────────────


def _compose_faction_brief(concept: str, factions: list[dict], this_faction: dict) -> str:
    peers = [
        f"- {f['name']} : {f.get('one_liner', '')}"
        for f in factions
        if f["name"] != this_faction["name"]
    ]
    peer_block = "\n".join(peers) if peers else "(aucune autre faction)"
    return (
        f"{concept}\n\n"
        f"--- Autres factions de la région ---\n{peer_block}\n\n"
        f"--- Cette faction ---\n{this_faction['name']} : {this_faction.get('one_liner', '')}"
    )


def _compose_location_brief(concept: str, locations: list[dict], this_location: dict) -> str:
    lines = []
    for l in locations:
        parent = l.get("parent_name")
        suffix = f" (sous {parent})" if parent else " (racine)"
        lines.append(f"- {l['name']}{suffix} : {l.get('one_liner', '')}")
    loc_block = "\n".join(lines) if lines else "(aucun autre lieu)"
    return (
        f"{concept}\n\n"
        f"--- Lieux de la région ---\n{loc_block}\n\n"
        f"--- Ce lieu ---\n{this_location['name']} : {this_location.get('one_liner', '')}"
    )


# ── Entry point ───────────────────────────────────────────────────────────


def generate_region_manifest(brief: str, db: Session) -> dict:
    """Phase A — produce the Stage-0 region manifest from a creator brief.

    Writes no canon. Never raises into the caller: every failure path
    returns {"ok": False, "error": ...} verbatim (empty brief, missing
    template, template format error, Ollama error, malformed/non-JSON
    manifest).
    """
    if not brief or not brief.strip():
        return {"ok": False, "error": "brief must not be empty"}

    template = _load_manifest_template(db)
    if template is None:
        return {"ok": False, "error": "No active pt-region-manifest template found"}

    world = _active_world(db)
    description = (world.description if world else None) or ""
    laws = db.exec(
        select(WorldLaw).where(WorldLaw.world_id == world.id).order_by(WorldLaw.position)
    ).all() if world else []
    fundamental_laws = "\n".join(law.text_ for law in laws)
    world_description = f"Contexte du monde : {description}\n\n" if description else ""
    world_fundamental_laws = (
        f"Lois fondamentales du monde (contraintes absolues) : {fundamental_laws}\n\n"
        if fundamental_laws else ""
    )

    version = current_prompt(db, template)
    user_message = (
        version.user_template
        .replace("{brief}", brief)
        .replace("{world_description}", world_description)
        .replace("{world_fundamental_laws}", world_fundamental_laws)
    )

    messages = [
        {"role": "system", "content": version.system_prompt},
        {"role": "user", "content": user_message},
    ]

    try:
        raw = chat(messages, model=effective_model(template, AUTHOR_MODEL), format="json")
    except OllamaError as exc:
        return {"ok": False, "error": str(exc)}

    return _parse_manifest_response(raw)


def _draft_factions(
    concept: str, factions_in: list[dict], skipped: list[dict], db: Session,
) -> tuple[dict[str, str], list[dict]]:
    """Stage 1 — factions. Returns (faction_local_id, factions_out)."""
    faction_local_id: dict[str, str] = {}
    factions_out: list[dict] = []
    for i, fac in enumerate(factions_in):
        local_id = f"fac-{i}"
        composite_brief = _compose_faction_brief(concept, factions_in, fac)
        result = generate_entity_draft("faction", composite_brief, db)
        if not result.get("ok"):
            skipped.append(
                {"stage": "faction", "name": fac["name"], "reason": result.get("error")}
            )
            continue
        faction_local_id[fac["name"].strip().lower()] = local_id
        factions_out.append({"local_id": local_id, "manifest": fac, "result": result})
    return faction_local_id, factions_out


def _draft_locations(
    concept: str, locations_in: list[dict], skipped: list[dict], notes: list[str], db: Session,
) -> tuple[dict[str, str], list[dict]]:
    """Stage 2 — locations, root first then the rest in manifest order.
    Returns (location_local_id, locations_out)."""
    root_first = sorted(
        enumerate(locations_in), key=lambda pair: 0 if pair[1].get("is_root") else 1
    )
    location_local_id: dict[str, str] = {}
    locations_out: list[dict] = []
    for i, loc in root_first:
        local_id = f"loc-{i}"
        composite_brief = _compose_location_brief(concept, locations_in, loc)
        result = generate_entity_draft("location", composite_brief, db)
        if not result.get("ok"):
            skipped.append(
                {"stage": "location", "name": loc["name"], "reason": result.get("error")}
            )
            continue
        parent_name = loc.get("parent_name")
        parent_local_id = None
        if parent_name:
            parent_local_id = location_local_id.get(parent_name.strip().lower())
            if parent_local_id is None and not loc.get("is_root"):
                notes.append(
                    f"Lieu '{loc['name']}' — parent '{parent_name}' indisponible (généré en échec)"
                )
        location_local_id[loc["name"].strip().lower()] = local_id
        locations_out.append(
            {
                "local_id": local_id,
                "parent_local_id": parent_local_id,
                "manifest": loc,
                "result": result,
            }
        )
    return location_local_id, locations_out


def generate_region_draft(manifest: dict, db: Session) -> dict:
    """Phase B — generate a region draft (factions/locations) from an
    already-produced manifest dict (Phase A's output, possibly creator-edited).

    The incoming manifest is advisory; this function re-runs
    `_normalize_manifest` on it first and uses the result as authoritative,
    guaranteeing invariants on untrusted re-submitted input. Writes no canon
    anywhere in this function or its call path. Never raises into the
    caller: a per-entity Stage 1-2 failure drops that entity (recorded in
    `region.skipped`) and the run continues. See `_draft_factions` /
    `_draft_locations` for the per-stage logic.
    """
    notes: list[str] = []
    manifest, skipped = _normalize_manifest(dict(manifest), notes)

    concept = manifest["concept"]
    factions_in = manifest["factions"]
    locations_in = manifest["locations"]

    _, factions_out = _draft_factions(concept, factions_in, skipped, db)
    _, locations_out = _draft_locations(concept, locations_in, skipped, notes, db)

    region = {
        "concept": concept,
        "factions": factions_out,
        "locations": locations_out,
        "skipped": skipped,
        "notes": notes,
    }
    return {"ok": True, "region": region}
