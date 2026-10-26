"""The creator's approval of a character draft (TICKET-0129): the review batches, one per group of people to create, and the one transaction that writes the draft to canon. Never commits.

A review batch is an NPC group agent batch (`npc_batch`, ephemeral staging)
carrying `pc_draft_id` and `pc_group_label` (C-09): one per group of the
draft's sketches the creator chose to `create`, anchored on the character
-- his story in the brief, his starting place as every line's pinned
location, so no placement call is made. Each line carries its sketch's
`name` and `pc_draft_sketch_id`; `run_next_npc` forces the name and copies
the sketch id onto the row (C-10). The agent's panel never lists these
batches and its commit refuses them: only the approval writes them.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlmodel import Session, select

from ..creation_check import review_place_id
from ..creation_rules import start_sheet
from ..models import NpcBatch, NpcBatchRow, PcDraft, PcDraftSketch
from ..npc_group_author import resolve_vocabulary
from ..writes.pc_drafts import REVIEW_LOCKED_MESSAGE, DraftLocked

NO_ONE_TO_CREATE = "Ce groupe n'a personne à créer."
LOT_ALREADY_OPEN = "Un lot est déjà ouvert pour ce groupe."
PLACE_REFUSED = "Ce lieu de départ ne peut pas être choisi."
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
