"""NPC link agent — coherence-pass serialization (TICKET-0036, BRIEF-0036-c).

Code-owned, no model call: builds the two JSON blobs the coherence prompt
consumes (`{staged_serialized}`, `{canon_serialized}`) and renders the
final coherence messages. Split out of `link_author.py` to keep that module
under its budget (CLAUDE.md link_author.py note, BRIEF-0036-b invariants) —
same rationale as `build_pair_context` staying pure/code-owned, just in its
own file because this step adds a second, budget-truncated serializer.

`serialize_canon_graph` reuses `context.RELATION_GRAPH_EXCLUDED_TYPES` (the
same structural exclusion as the relation-graph endpoints and the F1 pair
exclusion) — never a re-typed `("connects_to", "controls")` literal.
"""

from __future__ import annotations

import json

from sqlmodel import Session, select

from .context import RELATION_GRAPH_EXCLUDED_TYPES
from .models import Entity, Knowledge, LinkBatch, LinkBatchRow, PromptTemplate, Relation
from .prompt_store import current_prompt

# RECON-0036 R-1: hard character budget for the canon-graph blob. Exceeding
# it truncates at a row boundary (never mid-JSON) and the batch's coherence
# pass is labeled 'partial' — a truncated pass is never reported as complete.
CANON_SERIAL_BUDGET = 24000


def _entity_name(db: Session, entity_id: str) -> str:
    entity = db.get(Entity, entity_id)
    return entity.name if entity else entity_id


def serialize_staged_batch(db: Session, batch: LinkBatch) -> str:
    """Every non-rejected row of `batch`, row id + kind + resolved pair
    names + full payload, in deterministic (created_at, id) order."""
    rows = db.exec(
        select(LinkBatchRow)
        .where(LinkBatchRow.batch_id == batch.id)
        .where(LinkBatchRow.row_status != "rejected")
        .order_by(LinkBatchRow.created_at, LinkBatchRow.id)
    ).all()
    return json.dumps(
        [
            {
                "id": row.id,
                "kind": row.kind,
                "pair_a_name": _entity_name(db, row.pair_a_id),
                "pair_b_name": _entity_name(db, row.pair_b_id),
                "payload": row.payload,
            }
            for row in rows
        ],
        ensure_ascii=False,
    )


def _canon_entries(db: Session, batch: LinkBatch) -> list[tuple[int, str, str, dict]]:
    """(touch_priority, kind, id, row) for every candidate canon row —
    relations between active characters of the world (structural exclusion,
    RECON-0036 E1-tout-le-graphe) plus knowledge rows touching the batch
    roster (subject npc:{id} OR entity_id in the roster, RECON-0036 s.8/D3).
    touch_priority = how many endpoints are in the batch's NPC roster —
    higher sorts first (RECON-0036 R-1: "rows touching batch NPCs first")."""
    npc_ids = set(batch.scope.get("npc_ids", []))
    npc_subjects = {f"npc:{i}" for i in npc_ids}

    active_ids = set(
        db.exec(
            select(Entity.id).where(
                Entity.world_id == batch.world_id,
                Entity.type == "character",
                Entity.status == "active",
            )
        ).all()
    )

    rel_rows = db.exec(
        select(Relation).where(
            Relation.world_id == batch.world_id,
            Relation.type.not_in(RELATION_GRAPH_EXCLUDED_TYPES),
            Relation.entity_a_id.in_(active_ids),
            Relation.entity_b_id.in_(active_ids),
        )
    ).all()
    know_rows = db.exec(
        select(Knowledge).where(
            (Knowledge.subject.in_(npc_subjects)) | (Knowledge.entity_id.in_(npc_ids))
        )
    ).all()

    entries: list[tuple[int, str, str, dict]] = []
    for r in rel_rows:
        touch = (r.entity_a_id in npc_ids) + (r.entity_b_id in npc_ids)
        entries.append((touch, "relation", r.id, {
            "kind": "relation", "id": r.id,
            "entity_a_id": r.entity_a_id, "entity_a_name": _entity_name(db, r.entity_a_id),
            "entity_b_id": r.entity_b_id, "entity_b_name": _entity_name(db, r.entity_b_id),
            "type": r.type, "intensity": r.intensity, "direction": r.direction,
            "visible_to_b": r.visible_to_b, "notes": r.notes,
        }))
    for k in know_rows:
        touch = (k.entity_id in npc_ids) + (k.subject in npc_subjects)
        entries.append((touch, "knowledge", k.id, {
            "kind": "knowledge", "id": k.id,
            "entity_id": k.entity_id, "entity_name": _entity_name(db, k.entity_id),
            "subject": k.subject, "level": k.level, "content": k.content,
            "source": k.source, "is_incorrect": k.is_incorrect,
            "is_secret": k.is_secret, "share_threshold": k.share_threshold,
        }))

    entries.sort(key=lambda e: (-e[0], e[1], e[2]))
    return entries


def serialize_canon_graph(db: Session, batch: LinkBatch) -> tuple[str, bool]:
    """Returns (json_text, truncated). Rows are added in priority order
    until the next row would push the blob past CANON_SERIAL_BUDGET
    characters — truncation always lands on a row boundary, never mid-row."""
    entries = _canon_entries(db, batch)
    included: list[dict] = []
    for _touch, _kind, _id, row in entries:
        candidate = included + [row]
        if len(json.dumps(candidate, ensure_ascii=False)) > CANON_SERIAL_BUDGET:
            break
        included = candidate
    truncated = len(included) < len(entries)
    return json.dumps(included, ensure_ascii=False), truncated


def render_coherence_messages(
    db: Session,
    template: PromptTemplate,
    world_name: str,
    staged_serialized: str,
    canon_serialized: str,
    truncation_marker: str,
) -> list[dict]:
    version = current_prompt(db, template)
    system_content = version.system_prompt.replace("{world_name}", world_name)
    user_content = (
        version.user_template
        .replace("{staged_serialized}", staged_serialized)
        .replace("{canon_serialized}", canon_serialized)
        .replace("{truncation_marker}", truncation_marker)
    )
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": user_content},
    ]
