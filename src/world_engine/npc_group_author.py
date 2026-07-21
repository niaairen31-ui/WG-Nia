"""NPC group agent — staging substrate, placement plan, and generation run
(TICKET-0037, BRIEF-0037-a/b).

Standalone NPC group generation agent that replaces the region wizard's
retired NPC machinery (BRIEF-0037-d). `resolve_vocabulary` is the read-only
vocabulary resolver (BRIEF-0037-a); `plan_placements` (one model call per
batch, at most once, S1-resolved against the expanded location set) and
`run_next_npc` (one `generate_entity_draft` call per NPC, H1 — exact count
by construction) are this step's generation core. `run_next_npc` never
retries a name collision or a placement miss — both degrade in place (a
verbatim note, or a root-location fallback) and the row still stages; the
count contract forbids a silent shortfall. `patch_npc_row` is the inline
creator review edit, sibling of `link_author.patch_row`. The commit path
(BRIEF-0037-c) is not here. `npc_batch`/`npc_batch_row` stay ephemeral
stratum (models/ephemeral.py NOTE), never a canon write site
(`tooling/verify/checks/npc_agent_strata.py` enforces).
"""

from __future__ import annotations

import json
import unicodedata
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import attributes as sa_attrs
from sqlmodel import Session, select

from . import link_author, llm_parse
from .entity_author import AUTHOR_MODEL, generate_entity_draft, generate_npc_goals
from .models import Entity, Faction, NpcBatch, NpcBatchRow, PromptTemplate, World
from .ollama_client import OllamaError, chat
from .prompt_registry import effective_model
from .prompt_store import current_prompt

JOURNAL_DIR = Path.home() / ".world_engine" / "npc_agent_journal"


def journal_append(batch_id: str, event: dict) -> None:
    """Append one JSON line {ts, **event} to this batch's journal file,
    creating ~/.world_engine/npc_agent_journal/ if absent. Absolute
    home-anchored path, never repo-relative — outside the git tree and
    outside the DB's npc_batch retention purge."""
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    line = {"ts": datetime.now(UTC).isoformat(), **event}
    path = JOURNAL_DIR / f"{batch_id}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")


def resolve_vocabulary(db: Session, root_location_id: str) -> dict:
    """Expand `root_location_id` (S1 BFS descent, `link_author.
    expand_location_ids`) into the placement vocabulary available to a batch
    anchored on this region root: the expanded location set and the active
    world's active faction entities. Read-only, writes nothing."""
    expanded = sorted(link_author.expand_location_ids(db, [root_location_id]))

    location_rows = db.exec(
        select(Entity.id, Entity.name).where(Entity.id.in_(expanded))
    ).all()
    locations = [{"id": eid, "name": name} for eid, name in location_rows]

    world = db.exec(select(World).where(World.is_active == True)).first()  # noqa: E712
    factions: list[dict] = []
    if world is not None:
        faction_rows = db.exec(
            select(Entity.id, Entity.name)
            .join(Faction, Faction.id == Entity.id)
            .where(Entity.world_id == world.id, Entity.status == "active")
        ).all()
        factions = [{"id": eid, "name": name} for eid, name in faction_rows]

    return {
        "expanded_location_ids": expanded,
        "locations": locations,
        "factions": factions,
    }


# ── Prompt wiring ────────────────────────────────────────────────────────


def _load_placement_template(db: Session) -> PromptTemplate | None:
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.usage == "npc_batch_placement")
        .where(PromptTemplate.is_active == True)  # noqa: E712
    )
    return db.exec(stmt).first()


# ── Placement plan (one model call per batch, at most once) ─────────────


def _cache_placement_plan(db: Session, batch: NpcBatch, plan: dict[int, list[str | None]]) -> None:
    scope = dict(batch.scope)
    scope["placement_plan"] = {str(k): v for k, v in plan.items()}
    batch.scope = scope
    sa_attrs.flag_modified(batch, "scope")
    db.add(batch)
    db.commit()


def _run_placement_call(
    db: Session, batch: NpcBatch, unanchored: list[tuple[int, dict]], plan: dict[int, list[str | None]],
) -> None:
    """One `chat(..., format="json")` call through `llm_parse.extract_object`
    covering every unanchored line at once. A whole-call failure, or a
    per-line count mismatch, leaves that line's slots at their `None`
    default — never aborts the batch (S1: code resolves names, never the
    model)."""
    template = _load_placement_template(db)
    if template is None:
        raise HTTPException(status_code=503, detail="No active pt-npc-batch-placement template found")

    expanded_ids = batch.scope["expanded_location_ids"]
    location_rows = db.exec(select(Entity.id, Entity.name).where(Entity.id.in_(expanded_ids))).all()
    name_to_id: dict[str, str] = {}
    candidate_names: list[str] = []
    for eid, name in location_rows:
        candidate_names.append(name)
        name_to_id.setdefault(name.strip().lower(), eid)

    spec_lines_block = "\n".join(f"{i}: {line['description']} (count={line['count']})" for i, line in unanchored)
    version = current_prompt(db, template)
    user_message = (
        version.user_template
        .replace("{group_brief}", batch.scope.get("group_brief") or "")
        .replace("{spec_lines}", spec_lines_block)
        .replace("{candidate_locations}", ", ".join(candidate_names))
    )
    messages = [
        {"role": "system", "content": version.system_prompt},
        {"role": "user", "content": user_message},
    ]
    journal_append(batch.id, {"event": "placement_call", "prompt": messages})

    try:
        raw = chat(messages, model=effective_model(template, AUTHOR_MODEL), format="json")
        parsed = llm_parse.extract_object(raw)
        placements = parsed["placements"]
        if not isinstance(placements, dict):
            raise ValueError("'placements' is not an object")
    except (OllamaError, llm_parse.LlmParseError, KeyError, ValueError) as exc:
        journal_append(batch.id, {"event": "placement_parse_error", "reason": str(exc)})
        return

    for i, line in unanchored:
        names = placements.get(str(i))
        if not isinstance(names, list) or len(names) != line["count"]:
            continue
        plan[i] = [
            name_to_id.get(name.strip().lower()) if isinstance(name, str) else None
            for name in names
        ]
    journal_append(batch.id, {"event": "placement_result", "raw": raw, "plan": plan})


def plan_placements(db: Session, batch: NpcBatch) -> dict[int, list[str | None]]:
    """Batch-level placement plan, run at most once per batch (on the first
    `run_next_npc` call), cached into `scope["placement_plan"]` (JSON
    round-trip safe: string keys). Lines with a pinned `location_id` are
    excluded — zero unanchored lines means no model call, empty plan. A
    placement failure never blocks the count contract: unresolved slots
    fall back to `scope["root_location_id"]` at unit-resolution time
    (`run_next_npc`)."""
    cached = batch.scope.get("placement_plan")
    if cached is not None:
        return {int(k): v for k, v in cached.items()}

    lines = batch.scope["lines"]
    unanchored = [(i, line) for i, line in enumerate(lines) if not line.get("location_id")]
    plan: dict[int, list[str | None]] = {i: [None] * line["count"] for i, line in unanchored}
    if unanchored:
        _run_placement_call(db, batch, unanchored, plan)
    _cache_placement_plan(db, batch, plan)
    return plan


# ── Run driver (flattened unit order) ────────────────────────────────────


def _line_units(batch: NpcBatch) -> list[tuple[int, int]]:
    """The flattened run order: (line_index, ordinal) for each NPC, lines
    in order, ordinals 0..count-1. Unit k of the run = `_line_units[k]`."""
    units: list[tuple[int, int]] = []
    for i, line in enumerate(batch.scope["lines"]):
        units.extend((i, ordinal) for ordinal in range(line["count"]))
    return units


def _resolve_unit_location(
    batch: NpcBatch, plan: dict[int, list[str | None]], line: dict, line_index: int, ordinal: int, notes: list[str],
) -> str:
    """Pin > plan > root fallback. A miss (absent slot, or the plan never
    resolved this line) degrades to the root, verbatim-noted — never blocks
    the unit."""
    location_id = line.get("location_id")
    if location_id is not None:
        return location_id
    slots = plan.get(line_index, [])
    resolved = slots[ordinal] if ordinal < len(slots) else None
    if resolved is not None:
        return resolved
    notes.append("Placement non résolu — replié sur la racine")
    return batch.scope["root_location_id"]


def _resolve_faction_context(db: Session, faction_id: str | None) -> dict | None:
    if faction_id is None:
        return None
    faction_entity = db.get(Entity, faction_id)
    if faction_entity is None:
        return None
    return {"name": faction_entity.name, "description": (faction_entity.description or "")[:300]}


def _batch_siblings(db: Session, batch: NpcBatch, line_index: int) -> list[NpcBatchRow]:
    """Already-staged, non-rejected rows for this same spec line, in
    generation order — the anti-clone context for the next NPC of the
    line."""
    return db.exec(
        select(NpcBatchRow)
        .where(NpcBatchRow.batch_id == batch.id)
        .where(NpcBatchRow.line_index == line_index)
        .where(NpcBatchRow.row_status != "rejected")
        .order_by(NpcBatchRow.created_at)
    ).all()


def _compose_group_npc_brief(
    group_brief: str,
    line: dict,
    other_lines: list[dict],
    siblings: list[NpcBatchRow],
    faction_ctx: dict | None,
    location_name: str | None,
) -> str:
    """Mirrors `region_author._compose_npc_brief`'s prose style, adapted:
    peers become spec lines + already-generated siblings, not manifest
    one-liners."""
    parts = [
        group_brief,
        f"--- Cette ligne ---\n{line['description']} (count={line['count']})",
    ]
    if other_lines:
        other_block = "\n".join(f"- {l['description']}" for l in other_lines)
        parts.append(f"--- Autres lignes du groupe ---\n{other_block}")
    if faction_ctx is not None:
        parts.append(f"--- Sa faction ---\n{faction_ctx['name']} : {faction_ctx['description']}")
    if location_name is not None:
        parts.append(f"--- Son lieu ---\n{location_name}")
    if siblings:
        sibling_lines = "\n".join(
            f"{row.payload['draft']['public']['name']} : "
            f"{(row.payload['draft']['public'].get('description') or '')[:120]}"
            for row in siblings
        )
        parts.append(
            "--- Déjà générés pour cette ligne ---\n"
            f"{sibling_lines}\n"
            "Ce PNJ doit être clairement distinct de chacun d'eux : autre nom,\n"
            "autre tempérament, autre angle sur le même rôle."
        )
    return "\n\n".join(parts)


# ── Name dedup (BRIEF-42 `_name_key` posture) ────────────────────────────


def _name_key(name: str) -> str:
    """Normalize a name for dedup comparison only — apostrophe/whitespace/
    accent-composition variants of the same name fold to one key."""
    s = unicodedata.normalize("NFC", name or "")
    s = s.replace("’", "'").replace("ʼ", "'").replace("`", "'")
    s = " ".join(s.split())
    return s.lower()


def _check_name_collision(db: Session, batch: NpcBatch, name: str) -> str | None:
    """Compares against (a) staged non-rejected rows of this batch and (b)
    active `entity` names of the world. Returns the colliding name, or None.
    Never drops, never retries — the row stages regardless, noted."""
    key = _name_key(name)
    staged = db.exec(
        select(NpcBatchRow)
        .where(NpcBatchRow.batch_id == batch.id)
        .where(NpcBatchRow.row_status != "rejected")
    ).all()
    for row in staged:
        other = row.payload.get("draft", {}).get("public", {}).get("name", "")
        if _name_key(other) == key:
            return other
    active_names = db.exec(
        select(Entity.name).where(Entity.world_id == batch.world_id, Entity.status == "active")
    ).all()
    for other in active_names:
        if _name_key(other) == key:
            return other
    return None


def _generate_row_goals(db: Session, draft: dict, notes: list[str]) -> dict | None:
    """`generate_npc_goals` with `faction_goals` read from the resolved
    faction's `Faction.goals` (None when factionless). A failure never
    blocks the row — appended as a note instead."""
    pub = draft["public"]
    faction_id = pub.get("faction_id")
    faction_goals = None
    if faction_id is not None:
        faction = db.get(Faction, faction_id)
        faction_goals = faction.goals if faction is not None else None

    result = generate_npc_goals(pub.get("name", ""), pub.get("description", ""), pub.get("backstory", ""), faction_goals, db)
    if result.get("ok"):
        return {"long": result.get("long", ""), "shorts": result.get("shorts", [])}
    notes.append(f"Génération des objectifs échouée : {result.get('error')}")
    return None


def run_next_npc(db: Session, batch: NpcBatch) -> dict:
    """Process exactly one NPC unit: composite brief -> `generate_entity_draft`
    -> stage `NpcBatchRow`. Mirror of `link_author.run_pair` (link_author.py:
    398). `ok: False` -> journal `npc_parse_error`, raise 502, unit left
    pending — a silence is never a verdict, `npcs_done` unchanged."""
    if batch.status != "open":
        raise HTTPException(status_code=409, detail=f"NPC batch {batch.id!r} is not open")

    units = _line_units(batch)
    if batch.npcs_done >= len(units):
        raise HTTPException(status_code=409, detail="batch already fully generated")

    plan = plan_placements(db, batch)
    line_index, ordinal = units[batch.npcs_done]
    lines = batch.scope["lines"]
    line = lines[line_index]

    notes: list[str] = []
    location_id = _resolve_unit_location(batch, plan, line, line_index, ordinal, notes)
    location_entity = db.get(Entity, location_id)
    location_name = location_entity.name if location_entity else None
    faction_ctx = _resolve_faction_context(db, line.get("faction_id"))
    other_lines = [l for i, l in enumerate(lines) if i != line_index]
    siblings = _batch_siblings(db, batch, line_index)

    brief = _compose_group_npc_brief(
        batch.scope.get("group_brief") or "", line, other_lines, siblings, faction_ctx, location_name,
    )
    journal_append(batch.id, {"event": "npc_call", "line_index": line_index, "ordinal": ordinal, "brief": brief})

    result = generate_entity_draft("character", brief, db)
    if not result.get("ok"):
        journal_append(batch.id, {
            "event": "npc_parse_error", "line_index": line_index, "ordinal": ordinal,
            "reason": result.get("error"),
        })
        raise HTTPException(status_code=502, detail=f"NPC generation failed: {result.get('error')}")

    draft = result["draft"]
    faction_id = line.get("faction_id")
    if faction_id is not None:
        draft["public"]["faction_id"] = faction_id
    notes.extend(result.get("notes", []))

    name = draft["public"].get("name") or ""
    collision = _check_name_collision(db, batch, name)
    if collision is not None:
        notes.append(f"Nom en collision avec {collision} — à éditer avant commit")

    goals = _generate_row_goals(db, draft, notes)

    payload = {"draft": draft, "location_id": location_id, "goals": goals, "notes": notes}
    row = NpcBatchRow(batch_id=batch.id, line_index=line_index, kind="draft", payload=payload, row_status="proposed")
    db.add(row)
    batch.npcs_done += 1
    db.add(batch)
    db.commit()
    db.refresh(row)
    journal_append(batch.id, {"event": "npc_result", "line_index": line_index, "row_id": row.id, "name": name})

    return {"line_index": line_index, "name": name, "npcs_done": batch.npcs_done, "npcs_total": batch.npcs_total}


# ── Row edits (creator inline review, staging only) ──────────────────────


_NPC_ROW_STATUS_ALLOWED = ("proposed", "rejected")
_NPC_PLAIN_STR_FIELDS = ("description", "appearance", "backstory", "aversion")


def _coerce_npc_patch_value(db: Session, batch: NpcBatch, field: str, value):
    """Validates + coerces one `payload_patch` field. Returns
    (ok, reason, coerced_value). Ids of batch/rows, `line_index`, `kind`
    are never reachable here — they're not on this vocabulary."""
    if field == "name":
        if not isinstance(value, str) or not value.strip():
            return False, "name must be a non-empty string", None
        return True, None, value
    if field in _NPC_PLAIN_STR_FIELDS:
        if not isinstance(value, str):
            return False, f"{field} is not a string", None
        return True, None, value
    if field == "physical_tier":
        try:
            tier = int(value)
        except (TypeError, ValueError):
            return False, "physical_tier is not an integer", None
        return True, None, max(-1, min(2, tier))
    if field == "faction_id":
        if value is None:
            return True, None, None
        faction_entity = db.get(Entity, value)
        if (
            faction_entity is None or faction_entity.type != "faction"
            or faction_entity.status != "active" or faction_entity.world_id != batch.world_id
        ):
            return False, f"faction_id {value!r} is not an active faction of this world", None
        return True, None, value
    if field == "location_id":
        if value not in batch.scope.get("expanded_location_ids", []):
            return False, f"location_id {value!r} is outside the expanded set", None
        return True, None, value
    if field == "goals.long":
        if not isinstance(value, str):
            return False, "goals.long is not a string", None
        return True, None, value
    if field == "goals.shorts":
        if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
            return False, "goals.shorts is not a list of strings", None
        return True, None, value
    return False, f"{field!r} is not a patchable field", None


def patch_npc_row(
    db: Session, batch: NpcBatch, row_id: str,
    payload_patch: dict | None, row_status: str | None,
) -> dict:
    """Edits ONE staged row's payload fields and/or row_status — staging
    only, batch must be open. Sibling of `link_author.patch_row`
    (link_author.py:451): ids, `line_index`, `kind` stay unpatchable;
    `row_status` is reversible while the batch stays open."""
    if batch.status != "open":
        raise HTTPException(status_code=409, detail=f"NPC batch {batch.id!r} is not open")

    row = db.get(NpcBatchRow, row_id)
    if row is None or row.batch_id != batch.id:
        raise HTTPException(status_code=404, detail=f"row {row_id!r} not found in batch {batch.id!r}")

    if payload_patch:
        merged = dict(row.payload)
        draft_public = dict(merged.get("draft", {}).get("public", {}))
        goals = dict(merged.get("goals") or {})
        for field, value in payload_patch.items():
            ok, reason, coerced = _coerce_npc_patch_value(db, batch, field, value)
            if not ok:
                raise HTTPException(status_code=422, detail=reason)
            if field == "location_id":
                merged["location_id"] = coerced
            elif field == "goals.long":
                goals["long"] = coerced
            elif field == "goals.shorts":
                goals["shorts"] = coerced
            else:
                draft_public[field] = coerced
        merged["draft"] = {**merged.get("draft", {}), "public": draft_public}
        merged["goals"] = goals
        row.payload = merged
        row.row_status = "edited"
        row.updated_at = datetime.now(UTC)
        db.add(row)

    if row_status is not None:
        if row_status not in _NPC_ROW_STATUS_ALLOWED:
            raise HTTPException(status_code=422, detail=f"row_status {row_status!r} is not allowed")
        row.row_status = row_status
        row.updated_at = datetime.now(UTC)
        db.add(row)

    db.commit()
    db.refresh(row)
    journal_append(batch.id, {
        "event": "row_patched", "row_id": row.id,
        "payload_patch": payload_patch, "row_status": row_status,
    })
    return row.model_dump()
