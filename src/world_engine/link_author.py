"""NPC link agent — roster resolution, pair-pass orchestration, coherence
pass, and journal substrate (TICKET-0036, BRIEF-0036-a/b/c).

`resolve_roster` is the S1 location-subtree expansion: code-owned, no model
call. `enumerate_pairs`/`run_pair` are the pair pass (BRIEF-0036-b): one LLM
call per NPC pair proposes relations/knowledge, validated and clamped by
code, staged into `link_batch_row` — never canon. `run_coherence` is the
final pass (BRIEF-0036-c): mechanical fail-closed checks (phase 1, code)
plus one model review over the staged batch AND the full canon character
graph (phase 2, `link_context.py`'s serializers), producing pre-validated
findings (`_validate_patch`, the W gate). `apply_finding` and `commit_batch`
are the ONLY places this ticket touches canon, and both do so exclusively
through `write_relation`/`write_knowledge` — the sanctioned chokepoints,
never a bespoke write. `journal_append` is the append-only generation
journal (R1) — long memory for a batch, kept OUTSIDE the git tree and
outside the DB's last-2 retention purge. `link_batch`/`link_batch_row`
never appear in `writes/` or `canon_write_policy.txt` (link_agent_strata.py
enforces, including a dedicated AST scan for a direct `db.add(Relation(...))`
/ `db.add(Knowledge(...))` or raw canon SQL in this file or its routes).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from itertools import combinations
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy.orm import attributes as sa_attrs
from sqlmodel import Session, select

from . import llm_parse
from .context import RELATION_GRAPH_EXCLUDED_TYPES, read_public_memberships
from .entity_author import AUTHOR_MODEL
from .link_context import (
    render_coherence_messages,
    serialize_canon_graph,
    serialize_staged_batch,
)
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
from .writes import KNOWLEDGE_LEVELS, write_knowledge, write_relation

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
            # cockpit.crud.relations.get_global_relation_graph.
            Relation.type.not_in(RELATION_GRAPH_EXCLUDED_TYPES),
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


# ── Coherence pass — prompt wiring ──────────────────────────────────────


def _load_coherence_template(db: Session) -> PromptTemplate | None:
    stmt = (
        select(PromptTemplate)
        .where(PromptTemplate.usage == "npc_link_coherence")
        .where(PromptTemplate.is_active == True)  # noqa: E712
    )
    return db.exec(stmt).first()


# ── Coherence pass — phase 1, mechanical findings (code, no model) ──────


def _flag(target_scope: str, target_id: str, problem: str) -> dict:
    """A code-owned finding: always a flag, never a patch (mechanical
    findings are FLAGS ONLY — the brief's `patch=null, always`)."""
    return {
        "source": "code",
        "target": {"scope": target_scope, "id": target_id},
        "problem": problem,
        "patch": None,
        "rationale": "mechanical check",
        "validation": "valid",
        "validation_reason": None,
        "applied_at": None,
    }


def _duplicate_pair_findings(rows: list[LinkBatchRow]) -> list[dict]:
    """Duplicate staged rows for the same pair + kind + discriminator
    (relation type, or knowledge subject) — flags every row past the
    first in each group, in deterministic (created_at, id) order."""
    groups: dict[tuple, list[LinkBatchRow]] = {}
    for row in rows:
        if row.kind == "no_links":
            continue
        discriminator = row.payload.get("type") if row.kind == "relation" else row.payload.get("subject")
        key = (frozenset((row.pair_a_id, row.pair_b_id)), row.kind, discriminator)
        groups.setdefault(key, []).append(row)

    findings = []
    for group in groups.values():
        if len(group) < 2:
            continue
        ordered = sorted(group, key=lambda r: (r.created_at, r.id))
        for dup in ordered[1:]:
            findings.append(_flag("staged", dup.id, f"duplicate staged {dup.kind} row for this pair"))
    return findings


def _canon_relation_exists(db: Session, a_id: str, b_id: str) -> bool:
    """Both-directions F1 check for a single pair (RECON-0036 s.9's
    per-row commit-time mirror), same structural exclusion as
    `enumerate_pairs`'s bulk query and the relation-graph endpoints."""
    return db.exec(
        select(Relation.id).where(
            (
                ((Relation.entity_a_id == a_id) & (Relation.entity_b_id == b_id))
                | ((Relation.entity_a_id == b_id) & (Relation.entity_b_id == a_id))
            ),
            Relation.type.not_in(RELATION_GRAPH_EXCLUDED_TYPES),
        )
    ).first() is not None


def _stale_relation_findings(db: Session, rows: list[LinkBatchRow]) -> list[dict]:
    """A staged relation whose pair gained a canon relation since this
    batch was generated (F1 re-run at coherence time)."""
    findings = []
    for row in rows:
        if row.kind != "relation":
            continue
        if _canon_relation_exists(db, row.pair_a_id, row.pair_b_id):
            findings.append(_flag("staged", row.id, "pair now has a canon relation since this row was generated"))
    return findings


def _vocab_findings(rows: list[LinkBatchRow]) -> list[dict]:
    """Defense in depth vs BRIEF-0036-b: re-validate closed vocab / 1-100
    bounds on every non-rejected staged payload."""
    findings = []
    for row in rows:
        p = row.payload
        if row.kind == "relation":
            if p.get("type") not in _LINK_RELATION_TYPES:
                findings.append(_flag("staged", row.id, f"relation type {p.get('type')!r} outside vocabulary"))
            if p.get("direction") not in _LINK_DIRECTIONS:
                findings.append(_flag("staged", row.id, f"relation direction {p.get('direction')!r} outside vocabulary"))
            value = p.get("value")
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not (1 <= value <= 100):
                findings.append(_flag("staged", row.id, "relation intensity out of 1-100 bounds"))
        elif row.kind == "knowledge":
            if p.get("level") not in KNOWLEDGE_LEVELS:
                findings.append(_flag("staged", row.id, f"knowledge level {p.get('level')!r} outside vocabulary"))
            threshold = p.get("share_threshold")
            if not isinstance(threshold, (int, float)) or isinstance(threshold, bool) or not (1 <= threshold <= 100):
                findings.append(_flag("staged", row.id, "knowledge share_threshold out of 1-100 bounds"))
    return findings


def _subject_stamp_findings(rows: list[LinkBatchRow]) -> list[dict]:
    """D3 defense in depth: a staged knowledge row whose subject doesn't
    match npc:{other_id} for its own pair."""
    findings = []
    for row in rows:
        if row.kind != "knowledge":
            continue
        holder_id = row.payload.get("entity_id")
        other_id = row.pair_b_id if holder_id == row.pair_a_id else row.pair_a_id
        expected = f"npc:{other_id}"
        if row.payload.get("subject") != expected:
            findings.append(_flag(
                "staged", row.id,
                f"knowledge subject {row.payload.get('subject')!r} does not match expected {expected!r}",
            ))
    return findings


def _mechanical_findings(db: Session, batch: LinkBatch) -> list[dict]:
    """Phase 1 (code, runs even if the model call fails below)."""
    rows = db.exec(
        select(LinkBatchRow)
        .where(LinkBatchRow.batch_id == batch.id)
        .where(LinkBatchRow.row_status != "rejected")
    ).all()
    return (
        _duplicate_pair_findings(rows)
        + _stale_relation_findings(db, rows)
        + _vocab_findings(rows)
        + _subject_stamp_findings(rows)
    )


# ── Coherence pass — phase 2, model findings + patch validation (W) ─────


_CANON_RELATION_WHITELIST = {"intensity", "notes", "type", "direction", "visible_to_b"}
_CANON_KNOWLEDGE_WHITELIST = {"level", "content", "source", "is_incorrect", "is_secret", "share_threshold"}


def _coerce_patch_value(domain: str, field: str, value):
    """Same vocab/clamp validation as BRIEF-0036-b's item builders, keyed
    by `domain` in ('staged_relation', 'staged_knowledge', 'canon_relation',
    'canon_knowledge') — staged relation payloads name the intensity field
    'value' (write_relation's kwarg); canon patches name it 'intensity'
    (the schema column / creator-facing whitelist). Identity fields (ids,
    mode, subject, session bookkeeping) are NEVER patchable, on either
    side — "ids and subjects are NEVER patchable" applies structurally,
    not just to the canon whitelist that states it explicitly.
    Returns (ok, reason, coerced_value)."""
    if domain.endswith("relation"):
        intensity_key = "value" if domain == "staged_relation" else "intensity"
        if field == "type":
            if value not in _LINK_RELATION_TYPES:
                return False, f"type {value!r} outside vocabulary", None
            return True, None, value
        if field == "direction":
            if value not in _LINK_DIRECTIONS:
                return False, f"direction {value!r} outside vocabulary", None
            return True, None, value
        if field == intensity_key:
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                return False, f"{field} is not a number", None
            return True, None, _clamp_1_100(int(value))
        if field == "visible_to_b":
            if not isinstance(value, bool):
                return False, "visible_to_b is not a boolean", None
            return True, None, value
        if field == "notes":
            return True, None, value
        return False, f"{field!r} is not a patchable relation field", None

    if field == "level":
        if value not in KNOWLEDGE_LEVELS:
            return False, f"level {value!r} outside vocabulary", None
        return True, None, value
    if field == "share_threshold":
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            return False, "share_threshold is not a number", None
        return True, None, _clamp_1_100(int(value))
    if field in ("is_incorrect", "is_secret"):
        if not isinstance(value, bool):
            return False, f"{field} is not a boolean", None
        return True, None, value
    if field in ("content", "source"):
        return True, None, value
    return False, f"{field!r} is not a patchable knowledge field", None


def _validate_patch(db: Session, batch: LinkBatch, scope, target_id, patch):
    """Time-of-use-safe: called both when a model finding is first stored
    (W) and again right before an apply (re-validation). Returns
    (validation, reason, resolved_patch, target_kind) — target_kind in
    ('staged', 'relation', 'knowledge', None)."""
    if scope not in ("staged", "canon") or not target_id:
        return "rejected", f"malformed target {scope!r}/{target_id!r}", None, None

    if scope == "staged":
        row = db.get(LinkBatchRow, target_id)
        if row is None or row.batch_id != batch.id or row.row_status == "rejected":
            return "rejected", "staged target not found in this batch", None, "staged"
        if patch is None:
            return "valid", None, None, "staged"
        field = patch.get("field")
        if field not in row.payload:
            return "rejected", f"field {field!r} is not on the staged payload", None, "staged"
        domain = "staged_relation" if row.kind == "relation" else "staged_knowledge"
        ok, reason, new_value = _coerce_patch_value(domain, field, patch.get("new_value"))
        if not ok:
            return "rejected", reason, None, "staged"
        return "valid", None, {"field": field, "new_value": new_value}, "staged"

    rel = db.get(Relation, target_id)
    if rel is not None and rel.world_id == batch.world_id:
        return _validate_canon_patch(patch, "relation", _CANON_RELATION_WHITELIST)
    know = db.get(Knowledge, target_id)
    if know is not None:
        holder = db.get(Entity, know.entity_id)
        if holder is not None and holder.world_id == batch.world_id:
            return _validate_canon_patch(patch, "knowledge", _CANON_KNOWLEDGE_WHITELIST)
    return "rejected", "canon target not found in this world", None, None


def _validate_canon_patch(patch, kind: str, whitelist: set[str]):
    if patch is None:
        return "valid", None, None, kind
    field = patch.get("field")
    if field not in whitelist:
        return "rejected", f"field {field!r} is not patchable on canon {kind}", None, kind
    ok, reason, new_value = _coerce_patch_value(f"canon_{kind}", field, patch.get("new_value"))
    if not ok:
        return "rejected", reason, None, kind
    return "valid", None, {"field": field, "new_value": new_value}, kind


def _model_findings(db: Session, batch: LinkBatch, raw_findings) -> list[dict]:
    findings = []
    for item in raw_findings if isinstance(raw_findings, list) else []:
        if not isinstance(item, dict):
            continue
        target = item.get("target") if isinstance(item.get("target"), dict) else {}
        scope, target_id = target.get("scope"), target.get("id")
        patch = item.get("patch") if isinstance(item.get("patch"), dict) else None
        validation, reason, resolved_patch, _kind = _validate_patch(db, batch, scope, target_id, patch)
        findings.append({
            "source": "model",
            "target": {"scope": scope, "id": target_id},
            "problem": item.get("problem"),
            "patch": resolved_patch if validation == "valid" else None,
            "rationale": item.get("rationale"),
            "validation": validation,
            "validation_reason": reason,
            "applied_at": None,
        })
    return findings


# ── Coherence pass — orchestrator ───────────────────────────────────────


def run_coherence(db: Session, batch: LinkBatch) -> dict:
    """Phase 1 (mechanical) always runs; phase 2 (model) failure still
    persists phase-1 findings before raising — a silence is never a
    verdict, but a code-side flag is never lost to a model hiccup."""
    if batch.status != "open":
        raise HTTPException(status_code=409, detail=f"link batch {batch.id!r} is not open")

    template = _load_coherence_template(db)
    if template is None:
        raise HTTPException(status_code=503, detail="No active pt-npc-link-coherence template found")

    mechanical = _mechanical_findings(db, batch)

    world = db.get(World, batch.world_id)
    staged_serialized = serialize_staged_batch(db, batch)
    canon_serialized, truncated = serialize_canon_graph(db, batch)
    truncation_marker = "\nWARNING: canon graph truncated for length." if truncated else ""
    if truncated:
        journal_append(batch.id, {"event": "coherence_truncated"})

    messages = render_coherence_messages(
        db, template, world.name if world else "", staged_serialized, canon_serialized, truncation_marker,
    )
    journal_append(batch.id, {"event": "coherence_call", "prompt": messages})

    try:
        raw = chat(messages, model=effective_model(template, AUTHOR_MODEL), format="json")
        parsed = llm_parse.extract_object(raw)
        raw_findings = parsed["findings"]
        if not isinstance(raw_findings, list):
            raise ValueError("'findings' is not an array")
    except (OllamaError, llm_parse.LlmParseError, KeyError, ValueError) as exc:
        batch.coherence_findings = mechanical
        db.add(batch)
        db.commit()
        journal_append(batch.id, {"event": "coherence_parse_error", "reason": str(exc)})
        raise HTTPException(status_code=502, detail=f"coherence: model call failed or returned malformed output: {exc}") from exc

    all_findings = mechanical + _model_findings(db, batch, raw_findings)
    batch.coherence_findings = all_findings
    batch.coherence_status = "partial" if truncated else "ran"
    db.add(batch)
    db.commit()
    journal_append(batch.id, {"event": "coherence_result", "raw": raw, "finding_count": len(all_findings)})

    return {"coherence_status": batch.coherence_status, "findings": all_findings}


# ── Patch apply (creator-direct authority, ONLY through writes/) ────────


def _apply_staged_patch(db: Session, target_id: str, field: str, new_value) -> None:
    row = db.get(LinkBatchRow, target_id)
    payload = dict(row.payload)
    payload[field] = new_value
    row.payload = payload
    row.row_status = "edited"
    row.updated_at = datetime.now(UTC)
    db.add(row)


def _apply_canon_relation_patch(db: Session, target_id: str, field: str, new_value) -> None:
    rel = db.get(Relation, target_id)
    merged = {
        "type": rel.type, "value": rel.intensity, "direction": rel.direction,
        "visible_to_b": rel.visible_to_b, "notes": rel.notes,
    }
    merged["value" if field == "intensity" else field] = new_value
    write_relation(
        db, mode="set", relation_id=rel.id, world_id=rel.world_id,
        entity_a_id=rel.entity_a_id, entity_b_id=rel.entity_b_id,
        type=merged["type"], value=merged["value"], direction=merged["direction"],
        visible_to_b=merged["visible_to_b"], notes=merged["notes"],
    )


def _apply_canon_knowledge_patch(db: Session, target_id: str, field: str, new_value) -> None:
    know = db.get(Knowledge, target_id)
    merged = {
        "level": know.level, "content": know.content, "source": know.source,
        "is_incorrect": know.is_incorrect, "is_secret": know.is_secret,
        "share_threshold": know.share_threshold,
    }
    merged[field] = new_value
    write_knowledge(
        db, mode="update", knowledge_id=know.id, entity_id=know.entity_id,
        subject=know.subject, level=merged["level"], content=merged["content"],
        source=merged["source"], is_incorrect=merged["is_incorrect"],
        is_secret=merged["is_secret"], share_threshold=merged["share_threshold"],
        session_id=know.session_id, changed_by="link_agent_coherence",
    )


def apply_finding(db: Session, batch: LinkBatch, index: int) -> dict:
    """Refuses unless the finding exists, is valid, unapplied, and the
    batch is open. Re-validates the target at time-of-use before writing —
    a target that changed underneath the finding since coherence ran is
    rejected in place, never silently applied."""
    if batch.status != "open":
        raise HTTPException(status_code=409, detail=f"link batch {batch.id!r} is not open")

    findings = list(batch.coherence_findings or [])
    if index < 0 or index >= len(findings):
        raise HTTPException(status_code=404, detail=f"finding index {index} not found")
    finding = findings[index]
    if finding.get("validation") != "valid":
        raise HTTPException(status_code=409, detail="finding is not valid")
    if finding.get("applied_at"):
        raise HTTPException(status_code=409, detail="finding already applied")
    patch = finding.get("patch")
    if patch is None:
        raise HTTPException(status_code=409, detail="finding has no patch to apply")

    target = finding.get("target", {})
    scope, target_id = target.get("scope"), target.get("id")
    validation, reason, resolved_patch, target_kind = _validate_patch(db, batch, scope, target_id, patch)
    if validation != "valid":
        finding["validation"], finding["validation_reason"], finding["patch"] = "rejected", reason, None
        findings[index] = finding
        batch.coherence_findings = findings
        sa_attrs.flag_modified(batch, "coherence_findings")
        db.add(batch)
        db.commit()
        raise HTTPException(status_code=409, detail=f"target no longer valid: {reason}")

    field, new_value = resolved_patch["field"], resolved_patch["new_value"]
    if scope == "staged":
        _apply_staged_patch(db, target_id, field, new_value)
    elif target_kind == "relation":
        _apply_canon_relation_patch(db, target_id, field, new_value)
    else:
        _apply_canon_knowledge_patch(db, target_id, field, new_value)

    finding["applied_at"] = datetime.now(UTC).isoformat()
    findings[index] = finding
    batch.coherence_findings = findings
    sa_attrs.flag_modified(batch, "coherence_findings")
    db.add(batch)
    db.commit()
    journal_append(batch.id, {"event": "patch_applied", "index": index, "target": target})
    return finding


# ── Commit ───────────────────────────────────────────────────────────────


def commit_batch(db: Session, batch: LinkBatch) -> dict:
    """Every non-rejected, non-committed row writes canon exactly once,
    through write_relation/write_knowledge only — single transaction.
    Refuses when coherence never ran (coherence_status is NULL); a
    'partial' coherence pass may still commit (Nia's call). Per-row F1
    re-check: a relation row whose pair gained a canon relation since
    generation is skipped and surfaced, never silently double-written."""
    if batch.status != "open":
        raise HTTPException(status_code=409, detail=f"link batch {batch.id!r} is not open")
    if batch.coherence_status is None:
        raise HTTPException(status_code=409, detail="coherence has not run for this batch yet")

    rows = db.exec(
        select(LinkBatchRow)
        .where(LinkBatchRow.batch_id == batch.id)
        .where(LinkBatchRow.row_status.in_(("proposed", "edited")))
    ).all()

    committed: list[str] = []
    skipped: list[dict] = []
    now = datetime.now(UTC)
    for row in rows:
        if row.kind == "relation":
            if _canon_relation_exists(db, row.pair_a_id, row.pair_b_id):
                skipped.append({"id": row.id, "reason": "pair now has a canon relation"})
                continue
            write_relation(db, **row.payload)
        elif row.kind == "knowledge":
            write_knowledge(db, **row.payload)
        row.row_status = "committed"
        row.updated_at = now
        db.add(row)
        committed.append(row.id)

    batch.status = "committed"
    batch.closed_at = now
    db.add(batch)
    db.commit()
    journal_append(batch.id, {"event": "commit", "committed": committed, "skipped": skipped})
    return {"committed": committed, "skipped": skipped}
