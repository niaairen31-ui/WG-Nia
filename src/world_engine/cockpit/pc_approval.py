"""The creator's approval of a character draft (TICKET-0129): the review batches, one per group of people to create, and the one transaction that writes the draft to canon. Never commits.

A review batch is an NPC group agent batch (`npc_batch`, ephemeral staging)
carrying `pc_draft_id` and `pc_group_label` (C-09): one per group of the
draft's sketches the creator chose to `create`, anchored on the character
-- his story in the brief, his starting place as every line's pinned
location, so no placement call is made. Each line carries its sketch's
`name` and `pc_draft_sketch_id`; `run_next_npc` forces the name and copies
the sketch id onto the row (C-10). The agent's panel never lists these
batches and its commit refuses them: only the approval writes them.

`approve_draft` (C-11, BRIEF-0129-E) writes the draft to canon, in the
caller's transaction, only through writers: the review batches' rows
(`npc_group_commit._commit_npc_row`), the masters' Maître rank and the
character at the player's ranks with each taught skill's teacher
(`writes/player_characters.py`), his memberships and the encounters with
the factions' public members (`public_member_ids`), the relation every
person of his story has for him, and the draft closed with its character.
Refused unless `check_review` and `review_blockers` find nothing (INV-68).
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Session, select

from ..creation_check import check_review, review_place_id
from ..creation_rules import start_sheet
from ..encounters import record_encounter
from ..models import (
    NpcBatch, NpcBatchRow, PcDraft, PcDraftKnowledge, PcDraftMembership, PcDraftSkill, PcDraftSketch,
)
from ..npc_group_author import resolve_vocabulary
from ..perspective_selectors import public_member_ids, public_view
from ..writes import write_membership, write_relation
from ..writes.pc_drafts import REVIEW_LOCKED_MESSAGE, DraftLocked, mark_approved
from ..writes.player_characters import write_master_rank, write_player_character
from .npc_group_commit import _commit_npc_row

NO_ONE_TO_CREATE = "Ce groupe n'a personne à créer."
LOT_ALREADY_OPEN = "Un lot est déjà ouvert pour ce groupe."
PLACE_REFUSED = "Ce lieu de départ ne peut pas être choisi."
APPROVAL_REFUSED = "Ce personnage ne peut pas encore être approuvé."
GROUP_BRIEF = (
    "Ces personnes viennent de l'histoire de {name}, un personnage joueur qui entre dans le monde. "
    "Chacune le connaît ; développe-la avec tout ce que le monde sait.\n"
    "Groupe : {group}.\n"
    "\n"
    "Histoire de {name} :\n"
    "{story}"
)


def _label(group_label: str) -> str:
    return group_label or "sans groupe"


def _created_sketches(db: Session, draft: PcDraft) -> list[PcDraftSketch]:
    return list(db.exec(select(PcDraftSketch).where(
        PcDraftSketch.draft_id == draft.id, PcDraftSketch.review_action == "create",
    ).order_by(PcDraftSketch.position, PcDraftSketch.id)).all())


def review_groups(db: Session, draft: PcDraft) -> list[dict]:
    """The draft's `create` sketches by group, groups in order of first appearance."""
    groups: dict[str, list[str]] = {}
    for sketch in _created_sketches(db, draft):
        groups.setdefault(sketch.group_label, []).append(sketch.id)
    return [{"label": label, "sketch_ids": ids} for label, ids in groups.items()]


def open_review_lots(db: Session, draft: PcDraft) -> list[NpcBatch]:
    """The draft's open review batches, by creation."""
    return list(db.exec(select(NpcBatch).where(
        NpcBatch.pc_draft_id == draft.id, NpcBatch.status == "open",
    ).order_by(NpcBatch.created_at, NpcBatch.id)).all())


def lot_view(batch: NpcBatch) -> dict:
    return {"batch_id": batch.id, "status": batch.status, "npcs_done": batch.npcs_done,
            "npcs_total": batch.npcs_total}


def _description(sketch: PcDraftSketch, draft: PcDraft, skill_names: dict[str, str]) -> str:
    text = f"{sketch.name}, {sketch.role or 'une personne de son histoire'}."
    if sketch.sentence:
        text += f" {sketch.sentence}"
    if sketch.kind == "master":
        skill = skill_names.get(sketch.skill_key, sketch.skill_key)
        text += f" Maître en « {skill} », il a enseigné cette compétence à {draft.name}."
    return text


def prepare_group_lot(db: Session, draft: PcDraft, group_label: str) -> NpcBatch:
    """Open the review batch of one group (C-09): one line per `create`
    sketch of the group, pinned to the character's starting place. Added
    and flushed; never commits."""
    if draft.status != "submitted":
        raise DraftLocked(REVIEW_LOCKED_MESSAGE)
    sketches = [s for s in _created_sketches(db, draft) if s.group_label == group_label]
    if not sketches:
        raise ValueError(NO_ONE_TO_CREATE)
    if any(batch.pc_group_label == group_label for batch in open_review_lots(db, draft)):
        raise ValueError(LOT_ALREADY_OPEN)
    root = review_place_id(draft)
    if root is None:
        raise ValueError(PLACE_REFUSED)
    vocabulary = resolve_vocabulary(db, root)
    if root not in vocabulary["expanded_location_ids"]:
        raise ValueError(PLACE_REFUSED)
    skill_names = {line.skill_key: line.name for line in start_sheet(db, draft.world_id)}
    lines = [
        {"count": 1, "description": _description(sketch, draft, skill_names), "faction_id": None,
         "location_id": root, "name": sketch.name, "pc_draft_sketch_id": sketch.id}
        for sketch in sketches
    ]
    brief = GROUP_BRIEF.format(name=draft.name, group=_label(group_label), story=draft.story)
    batch = NpcBatch(
        world_id=draft.world_id,
        scope={"root_location_id": root, "expanded_location_ids": vocabulary["expanded_location_ids"],
               "lines": lines, "group_brief": brief},
        npcs_total=len(lines), pc_draft_id=draft.id, pc_group_label=group_label,
    )
    db.add(batch)
    db.flush()
    return batch


def abandon_review_lots(db: Session, draft: PcDraft) -> list[str]:
    """Every open review batch of the draft -> `abandoned`; their ids."""
    now = datetime.now(UTC)
    ids = []
    for batch in open_review_lots(db, draft):
        batch.status = "abandoned"
        batch.closed_at = now
        db.add(batch)
        ids.append(batch.id)
    db.flush()
    return ids


def _kept_row(db: Session, batch: NpcBatch, sketch_id: str) -> bool:
    return db.exec(select(NpcBatchRow.id).where(
        NpcBatchRow.batch_id == batch.id, NpcBatchRow.pc_draft_sketch_id == sketch_id,
        NpcBatchRow.kind == "draft", NpcBatchRow.row_status.in_(("proposed", "edited")),
    )).first() is not None


def review_blockers(db: Session, draft: PcDraft) -> list[dict]:
    """What keeps the people to create from the approval (C-09): a group
    with no lot, a lot not fully generated, a sketch with no kept row."""
    lots = {batch.pc_group_label: batch for batch in open_review_lots(db, draft)}
    blockers: list[dict] = []
    seen_groups: set[str] = set()
    for sketch in _created_sketches(db, draft):
        label = sketch.group_label
        batch = lots.get(label)
        if batch is None or batch.npcs_done < batch.npcs_total:
            if label in seen_groups:
                continue
            seen_groups.add(label)
            if batch is None:
                code, message = "lot_missing", f"« {_label(label)} » : prépare le lot de ce groupe."
            else:
                code, message = "lot_incomplete", f"« {_label(label)} » : la génération du lot n'est pas terminée."
            blockers.append({"code": code, "label": label, "sketch_id": sketch.id, "message": message})
        elif not _kept_row(db, batch, sketch.id):
            blockers.append({"code": "row_missing", "label": label, "sketch_id": sketch.id,
                             "message": f"« {sketch.name} » : aucune fiche retenue dans le lot."})
    return blockers


class ApprovalRefused(ValueError):
    """The draft's final version or its review batches are not ready (C-11 step 0)."""


def _draft_sketches(db: Session, draft: PcDraft) -> list[PcDraftSketch]:
    return list(db.exec(select(PcDraftSketch).where(PcDraftSketch.draft_id == draft.id)
                        .order_by(PcDraftSketch.position, PcDraftSketch.id)).all())


def _commit_lots(db: Session, draft: PcDraft) -> tuple[dict[str, str], list[str], list[str]]:
    """Step 1: every kept row of the draft's review batches written to canon.
    Returns (sketch id -> new NPC id, NPC ids, batch ids)."""
    now = datetime.now(UTC)
    npc_of: dict[str, str] = {}
    npc_ids: list[str] = []
    lot_ids: list[str] = []
    for batch in open_review_lots(db, draft):
        rows = db.exec(select(NpcBatchRow).where(
            NpcBatchRow.batch_id == batch.id, NpcBatchRow.kind == "draft",
            NpcBatchRow.row_status.in_(("proposed", "edited")),
        ).order_by(NpcBatchRow.created_at, NpcBatchRow.id)).all()
        for row in rows:
            sketch = db.get(PcDraftSketch, row.pc_draft_sketch_id) if row.pc_draft_sketch_id else None
            if sketch is None or sketch.draft_id != draft.id or sketch.review_action != "create":
                row.row_status = "rejected"
            else:
                entity_id = _commit_npc_row(row, batch, db)["entity_id"]
                npc_of[sketch.id] = entity_id
                npc_ids.append(entity_id)
                row.row_status = "committed"
            row.updated_at = now
        batch.status = "committed"
        batch.closed_at = now
        lot_ids.append(batch.id)
    return npc_of, npc_ids, lot_ids


def _teachers(db: Session, draft: PcDraft, sketches: list[PcDraftSketch],
              npc_of: dict[str, str]) -> tuple[dict[str, int], dict[str, str]]:
    """Step 3: the player's ranks, and each taught skill's first kept master."""
    skills = db.exec(select(PcDraftSkill).where(PcDraftSkill.draft_id == draft.id)).all()
    ranks = {row.skill_key: row.player_rank for row in skills if row.player_rank is not None}
    needs_master = {line.skill_key for line in start_sheet(db, draft.world_id) if line.requires_master}
    teachers: dict[str, str] = {}
    for key, rank in ranks.items():
        if rank < 1 or key not in needs_master:
            continue
        master = next((s for s in sketches if s.kind == "master" and s.skill_key == key
                       and s.review_action not in (None, "drop")), None)
        if master is not None:
            teacher = master.review_entity_id if master.review_action == "attach" else npc_of.get(master.id)
            if teacher is not None:
                teachers[key] = teacher
    return ranks, teachers


def approve_draft(db: Session, draft: PcDraft) -> dict:
    """Write the submitted `draft` to canon (C-11), in the caller's
    transaction; never commits. `DraftLocked` when it is not submitted,
    `ApprovalRefused` while `check_review` or `review_blockers` find
    anything."""
    if draft.status != "submitted":
        raise DraftLocked(REVIEW_LOCKED_MESSAGE)
    if check_review(db, draft) or review_blockers(db, draft):
        raise ApprovalRefused(APPROVAL_REFUSED)
    world_id = draft.world_id
    view = public_view(db, world_id)
    sketches = _draft_sketches(db, draft)

    npc_of, npc_ids, lot_ids = _commit_lots(db, draft)

    for sketch in sketches:
        if sketch.kind == "master" and sketch.review_action == "create" and sketch.id in npc_of:
            write_master_rank(db, character_id=npc_of[sketch.id], skill_key=sketch.skill_key)

    ranks, teachers = _teachers(db, draft, sketches, npc_of)
    knowledge = db.exec(select(PcDraftKnowledge).where(PcDraftKnowledge.draft_id == draft.id)
                        .order_by(PcDraftKnowledge.position, PcDraftKnowledge.id)).all()
    pc = write_player_character(
        db, world_id=world_id, user_id=draft.user_id, name=draft.name.strip(),
        current_location_id=review_place_id(draft), facets={"histoire": draft.story},
        knowledge=list(knowledge), ranks=ranks, teachers=teachers,
    )

    memberships = db.exec(select(PcDraftMembership).where(PcDraftMembership.draft_id == draft.id)
                          .order_by(PcDraftMembership.id)).all()
    for membership in memberships:
        if membership.review_dropped:
            continue
        write_membership(db, mode="open", world_id=world_id, entity_id=pc.id,
                         faction_id=membership.faction_id, role=membership.role)
        for member_id in public_member_ids(membership.faction_id, world_id, view, db):
            record_encounter(db, world_id=world_id, a_id=pc.id, b_id=member_id,
                             source="pc_creation", source_ref=draft.id)

    for sketch in sketches:
        if sketch.review_action == "create":
            other = npc_of.get(sketch.id)
        elif sketch.review_action == "attach":
            other = sketch.review_entity_id
        else:
            continue
        if other is None:
            raise ApprovalRefused(APPROVAL_REFUSED)
        write_relation(db, mode="set", world_id=world_id, entity_a_id=other, entity_b_id=pc.id,
                       type=sketch.review_relation_type.strip(), value=sketch.review_intensity,
                       direction="a_to_b", notes=sketch.role or None, changed_by="creator_crud")

    mark_approved(db, draft, character_id=pc.id)
    return {"character_id": pc.id, "name": pc.name, "npc_ids": npc_ids, "lot_ids": lot_ids}
