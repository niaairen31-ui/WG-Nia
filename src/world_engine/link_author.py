"""NPC link agent — roster resolution, pair-pass orchestration, and journal
substrate (TICKET-0036, BRIEF-0036-a, BRIEF-0036-b).

`resolve_roster` is the S1 location-subtree expansion: code-owned, no model
call. `enumerate_pairs`/`run_pair` are the pair pass (BRIEF-0036-b): one LLM
call per NPC pair proposes relations/knowledge, validated and clamped by
code, staged into `link_batch_row` — never canon. `journal_append` is the
append-only generation journal (R1) — long memory for a batch, kept OUTSIDE
the git tree and outside the DB's last-2 retention purge. Nothing in this
module writes canon; `link_batch`/`link_batch_row` never appear in
`writes/` or `canon_write_policy.txt` (link_agent_strata.py enforces).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path

from fastapi import HTTPException
from sqlmodel import Session, select

from . import llm_parse
from .context import read_public_memberships
from .entity_author import AUTHOR_MODEL
from .models import (
    Character,
    Entity,
    Knowledge,
    LinkBatch,
    LinkBatchRow,
    Location,
    PromptTemplate,
    Relation,
    World,
)
from .ollama_client import OllamaError, chat
from .prompt_registry import effective_model
from .prompt_store import current_prompt
from .writes import KNOWLEDGE_LEVELS

JOURNAL_DIR = Path.home() / ".world_engine" / "link_agent_journal"

# Closed vocab for the pair-pass model (RECON-0036 s.1): deliberately
# NARROWER than cockpit.crud._shared.RELATION_TYPES — connects_to/controls
# are location-map topology / control edges, structurally impossible for
# the link agent to propose.
_LINK_RELATION_TYPES = (
    "ally", "enemy", "debt", "fear", "fascination", "shared_secret",
    "instrumentalizes", "interest", "indifference", "rejection",
    "passive_attention", "other",
)
assert "connects_to" not in _LINK_RELATION_TYPES
assert "controls" not in _LINK_RELATION_TYPES

_LINK_DIRECTIONS = ("mutual", "a_to_b", "b_to_a")


def resolve_roster(db: Session, root_location_ids: list[str]) -> dict:
    """BFS-expand `root_location_ids` through `parent_location_id` descent,
    then collect the present NPC roster over the expanded set.

    Roster = characters with character_type='npc', vital_status='alive',
    entity.status='active', current_location_id in the expanded set.
    Returns {expanded_location_ids, npcs: [{id, name}], pair_count} where
    pair_count = N*(N-1)/2. Writes nothing."""
    expanded: set[str] = set(root_location_ids)
    frontier = list(root_location_ids)
    while frontier:
        children = db.exec(
            select(Location.id).where(Location.parent_location_id.in_(frontier))
        ).all()
        new_children = [c for c in children if c not in expanded]
        expanded.update(new_children)
        frontier = new_children

    rows = db.exec(
        select(Entity, Character)
        .join(Character, Character.id == Entity.id)
        .where(Character.character_type == "npc")
        .where(Character.vital_status == "alive")
        .where(Entity.status == "active")
        .where(Character.current_location_id.in_(list(expanded)))
    ).all()
    npcs = [{"id": e.id, "name": e.name} for e, _ in rows]

    n = len(npcs)
    return {
        "expanded_location_ids": sorted(expanded),
        "npcs": npcs,
        "pair_count": n * (n - 1) // 2,
    }


def journal_append(batch_id: str, event: dict) -> None:
    """Append one JSON line {ts, **event} to this batch's journal file,
    creating ~/.world_engine/link_agent_journal/ if absent. Absolute
    home-anchored path, never repo-relative — outside the git tree and
    outside the DB's link_batch retention purge."""
    JOURNAL_DIR.mkdir(parents=True, exist_ok=True)
    line = {"ts": datetime.now(UTC).isoformat(), **event}
    path = JOURNAL_DIR / f"{batch_id}.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")


# ── Prompt wiring ────────────────────────────────────────────────────────


def _load_pair_template(db: Session) -> PromptTemplate | None:
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.usage == "npc_link_pair")
        .where(PromptTemplate.is_active == True)  # noqa: E712
    )
    return db.exec(stmt).first()


# ── Context assembly (code-owned, no model call) ────────────────────────


def _location_chain_names(db: Session, location_id: str | None) -> list[str]:
    """Immediate location name, then each ancestor's name up the
    `parent_location_id` chain. Cycle-guarded (visited set)."""
    names: list[str] = []
    visited: set[str] = set()
    current_id = location_id
    while current_id is not None and current_id not in visited:
        visited.add(current_id)
        entity = db.get(Entity, current_id)
        location = db.get(Location, current_id)
        if entity is None or location is None:
            break
        names.append(entity.name)
        current_id = location.parent_location_id
    return names


def _npc_sheet(db: Session, entity_id: str) -> str:
    entity = db.get(Entity, entity_id)
    character = db.get(Character, entity_id)
    memberships = read_public_memberships(entity_id, db)
    factions = "; ".join(
        f"{name} ({role})" if role else name for name, role in memberships
    ) or "none"
    location_ids = character.current_location_id if character else None
    location_chain = _location_chain_names(db, location_ids)
    location_text = " -> ".join(location_chain) if location_chain else "unknown"

    return "\n".join([
        f"Name: {entity.name if entity else 'unknown'}",
        f"Description: {(entity.description if entity else None) or ''}",
        f"Appearance: {(character.appearance if character else None) or ''}",
        f"Backstory: {(character.backstory if character else None) or ''}",
        f"Aversion: {(character.aversion if character else None) or ''}",
        f"Vital status: {character.vital_status if character else 'unknown'}",
        f"Factions: {factions}",
        f"Location: {location_text}",
    ])


def _shared_knowledge_lines(db: Session, holder_id: str, other_id: str, holder_name: str) -> list[str]:
    """Existing knowledge `holder_id` holds ABOUT `other_id`, via the D3
    `npc:{entity_id}` subject convention — the same stamp this pass writes.
    is_secret=TRUE rows MAY enter (creator-surface exception, RECON-0036
    R-4); rows about anyone else (third parties) never match this subject
    and are excluded by construction."""
    rows = db.exec(
        select(Knowledge).where(
            Knowledge.entity_id == holder_id,
            Knowledge.subject == f"npc:{other_id}",
        )
    ).all()
    return [
        f"- {holder_name} already knows (level={r.level}, secret={r.is_secret}): "
        f"{r.content or '(no content recorded)'}"
        for r in rows
    ]


def build_pair_context(db: Session, a_id: str, b_id: str) -> dict:
    # character.secrets (creator meta-narrative) is NEVER read here -- same
    # exclusion as every context assembler. Only knowledge rows may enter,
    # including is_secret=TRUE rows: this is a CREATOR-SURFACE exception,
    # valid solely because the link agent's output is reviewed by the
    # creator before commit.
    a_entity = db.get(Entity, a_id)
    b_entity = db.get(Entity, b_id)
    a_character = db.get(Character, a_id)
    b_character = db.get(Character, b_id)

    same_location = (
        a_character is not None
        and b_character is not None
        and a_character.current_location_id is not None
        and a_character.current_location_id == b_character.current_location_id
    )
    a_factions = {name for name, _ in read_public_memberships(a_id, db)}
    b_factions = {name for name, _ in read_public_memberships(b_id, db)}
    shared_factions = sorted(a_factions & b_factions)

    lines = [
        f"Same location: {'yes' if same_location else 'no'}",
        f"Shared factions: {', '.join(shared_factions) if shared_factions else 'none'}",
    ]
    lines.extend(_shared_knowledge_lines(db, a_id, b_id, a_entity.name if a_entity else "NPC A"))
    lines.extend(_shared_knowledge_lines(db, b_id, a_id, b_entity.name if b_entity else "NPC B"))

    return {
        "a_sheet": _npc_sheet(db, a_id),
        "b_sheet": _npc_sheet(db, b_id),
        "shared_context": "\n".join(lines),
    }


# ── Pair enumeration (F1) ────────────────────────────────────────────────


def enumerate_pairs(db: Session, batch: LinkBatch) -> list[tuple[str, str]]:
    """All unordered pairs from `batch.scope["npc_ids"]`, sorted ids,
    MINUS pairs already holding a canon `relation` row in either direction
    (F1) — one query over the whole id set, never N^2. Excluded pairs are
    journaled (pair_skipped_existing) and consume no LLM call."""
    npc_ids = sorted(batch.scope.get("npc_ids", []))
    combos = list(combinations(npc_ids, 2))
    if not combos:
        return []

    rows = db.exec(
        select(Relation.entity_a_id, Relation.entity_b_id).where(
            Relation.entity_a_id.in_(npc_ids),
            Relation.entity_b_id.in_(npc_ids),
            # Structural exclusion (CLAUDE.md): connects_to/controls are
            # location-map topology/control edges, never a social signal —
            # any new world-wide relation scan MUST exclude them, same as
            # cockpit.crud.relations._RELATION_GRAPH_EXCLUDED_TYPES.
            Relation.type.not_in(("connects_to", "controls")),
        )
    ).all()
    existing = {frozenset((a, b)) for a, b in rows}

    pending: list[tuple[str, str]] = []
    for a, b in combos:
        if frozenset((a, b)) in existing:
            journal_append(batch.id, {"event": "pair_skipped_existing", "a": a, "b": b})
            continue
        pending.append((a, b))
    return pending


def pending_pairs(db: Session, batch: LinkBatch) -> list[tuple[str, str]]:
    """`enumerate_pairs` minus pairs that already have any `link_batch_row`
    (relation/knowledge/no_links) in this batch — recomputed on every call,
    so resume-after-restart is free."""
    candidates = enumerate_pairs(db, batch)
    done_rows = db.exec(
        select(LinkBatchRow.pair_a_id, LinkBatchRow.pair_b_id).where(
            LinkBatchRow.batch_id == batch.id
        )
    ).all()
    done = {(a, b) for a, b in done_rows}
    return [pair for pair in candidates if pair not in done]


# ── Link item validation (code judges) ───────────────────────────────────


class _LinkItemRejected(Exception):
    """One link item failed validation — dropped alone, never the whole
    pair (`reason` is journaled as `link_item_rejected`)."""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


def _clamp_1_100(value: int) -> int:
    return max(1, min(100, value))


def _build_relation_row(batch: LinkBatch, a_id: str, b_id: str, item: dict) -> LinkBatchRow:
    type_ = item.get("type")
    if type_ not in _LINK_RELATION_TYPES:
        raise _LinkItemRejected(f"invalid relation type {type_!r}")
    direction = item.get("direction")
    if direction not in _LINK_DIRECTIONS:
        raise _LinkItemRejected(f"invalid direction {direction!r}")
    intensity = item.get("intensity")
    if not isinstance(intensity, (int, float)) or isinstance(intensity, bool):
        raise _LinkItemRejected("intensity is not a number")

    payload = {
        "mode": "set", "relation_id": None, "world_id": batch.world_id,
        "entity_a_id": a_id, "entity_b_id": b_id, "type": type_,
        "value": _clamp_1_100(int(intensity)), "direction": direction,
        "visible_to_b": bool(item.get("visible_to_b", True)),
        "notes": item.get("notes"),
    }
    return LinkBatchRow(batch_id=batch.id, pair_a_id=a_id, pair_b_id=b_id, kind="relation", payload=payload)


def _build_knowledge_row(batch: LinkBatch, a_id: str, b_id: str, item: dict) -> LinkBatchRow:
    holder = item.get("holder")
    if holder not in ("a", "b"):
        raise _LinkItemRejected(f"invalid holder {holder!r}")
    level = item.get("level")
    if level not in KNOWLEDGE_LEVELS:
        raise _LinkItemRejected(f"invalid level {level!r}")

    holder_id = a_id if holder == "a" else b_id
    other_id = b_id if holder == "a" else a_id
    threshold = item.get("share_threshold", 50)
    if not isinstance(threshold, (int, float)) or isinstance(threshold, bool):
        threshold = 50

    payload = {
        "mode": "update", "knowledge_id": None, "entity_id": holder_id,
        # D3, code-stamped: the model never emits "subject" — this is the
        # single construction site (link_agent_strata.py asserts it).
        "subject": f"npc:{other_id}",
        "level": level,
        "content": item.get("content"), "source": item.get("source"),
        "is_incorrect": bool(item.get("is_incorrect", False)),
        "is_secret": bool(item.get("is_secret", False)),
        "share_threshold": _clamp_1_100(int(threshold)),
        "session_id": None, "changed_by": "link_agent",
    }
    return LinkBatchRow(batch_id=batch.id, pair_a_id=a_id, pair_b_id=b_id, kind="knowledge", payload=payload)


def _build_link_row(batch: LinkBatch, a_id: str, b_id: str, item) -> LinkBatchRow:
    if not isinstance(item, dict):
        raise _LinkItemRejected("item is not a JSON object")
    kind = item.get("kind")
    if kind == "relation":
        return _build_relation_row(batch, a_id, b_id, item)
    if kind == "knowledge":
        return _build_knowledge_row(batch, a_id, b_id, item)
    raise _LinkItemRejected(f"unknown kind {kind!r}")


def _write_pair_rows(db: Session, batch: LinkBatch, a_id: str, b_id: str, verdict: str, links_raw) -> tuple[int, int]:
    if verdict == "no_links":
        db.add(LinkBatchRow(batch_id=batch.id, pair_a_id=a_id, pair_b_id=b_id, kind="no_links", payload={}))
        return 0, 0

    items = links_raw if isinstance(links_raw, list) else []
    kept = 0
    dropped = 0
    for item in items:
        try:
            row = _build_link_row(batch, a_id, b_id, item)
        except _LinkItemRejected as exc:
            dropped += 1
            journal_append(batch.id, {
                "event": "link_item_rejected", "a": a_id, "b": b_id,
                "item": item, "reason": exc.reason,
            })
            continue
        db.add(row)
        kept += 1
    return kept, dropped


# ── Pair processing (one model call per pair) ───────────────────────────


def _render_pair_messages(db: Session, template: PromptTemplate, world_name: str, ctx: dict) -> list[dict]:
    version = current_prompt(db, template)
    system_content = version.system_prompt.replace("{world_name}", world_name)
    user_content = (
        version.user_template
        .replace("{a_sheet}", ctx["a_sheet"])
        .replace("{b_sheet}", ctx["b_sheet"])
        .replace("{shared_context}", ctx["shared_context"])
    )
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]


def run_pair(db: Session, batch: LinkBatch, a_id: str, b_id: str) -> dict:
    """Process exactly one pair: one LLM call, code-validated, staged into
    `link_batch_row`. Raises HTTPException(502) on a parse/verdict failure
    — the pair is left pending (no row written); a silence is never a
    verdict. Commits on success."""
    template = _load_pair_template(db)
    if template is None:
        raise HTTPException(status_code=503, detail="No active pt-npc-link-pair template found")

    world = db.get(World, batch.world_id)
    ctx = build_pair_context(db, a_id, b_id)
    messages = _render_pair_messages(db, template, world.name if world else "", ctx)
    journal_append(batch.id, {"event": "pair_call", "a": a_id, "b": b_id, "prompt": messages})

    try:
        raw = chat(messages, model=effective_model(template, AUTHOR_MODEL), format="json")
    except OllamaError as exc:
        journal_append(batch.id, {"event": "pair_parse_error", "a": a_id, "b": b_id, "reason": str(exc)})
        raise HTTPException(status_code=502, detail=f"pair ({a_id}, {b_id}): model call failed: {exc}") from exc

    try:
        parsed = llm_parse.extract_object(raw)
    except llm_parse.LlmParseError as exc:
        journal_append(batch.id, {"event": "pair_parse_error", "a": a_id, "b": b_id, "raw": raw, "reason": str(exc)})
        raise HTTPException(status_code=502, detail=f"pair ({a_id}, {b_id}): model returned non-JSON output") from exc

    verdict = parsed.get("verdict")
    if verdict not in ("links", "no_links"):
        journal_append(batch.id, {
            "event": "pair_parse_error", "a": a_id, "b": b_id, "raw": raw,
            "reason": "missing or invalid verdict",
        })
        raise HTTPException(status_code=502, detail=f"pair ({a_id}, {b_id}): missing or invalid verdict")

    kept, dropped = _write_pair_rows(db, batch, a_id, b_id, verdict, parsed.get("links"))
    journal_append(batch.id, {
        "event": "pair_result", "a": a_id, "b": b_id, "verdict": verdict,
        "raw": raw, "kept": kept, "dropped": dropped,
    })

    batch.pairs_done += 1
    db.add(batch)
    db.commit()

    return {"verdict": verdict, "row_count": 1 if verdict == "no_links" else kept}
