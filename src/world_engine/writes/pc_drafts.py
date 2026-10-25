"""The one writer of a player's character draft (TICKET-0126, BRIEF-0126-G; B1, C1, V1, T1). Never commits; never writes a canon table.

A draft (`pc_draft` and its four child tables) is non-canon: it waits for
the creator's review (TICKET-0129). Every row of a draft carries an
`origin` -- `player` for what the player wrote, `designer` for what the
character designer proposed; a designer row the player edits becomes
`player` and survives the next design. A skill row keeps both ranks: the
player's and the designer's counter-proposal, never one over the other.

- `open_draft(...)` : the user's open draft of the world, else a new one;
  refused when the user already holds a player character there (R-09).
- `save_player_draft(...)` : the player's whole draft, replaced.
- `apply_design(...)` : a `creation_designer.CreationDesign` laid over the
  draft: the designer's rows replaced, the player's kept.
- `submit_draft(...)` : `draft` -> `submitted`, only with no violation
  (`creation_check.check_draft`, INV-67).

Only `draft` status is writable (`DraftLocked` otherwise). The caller owns
the transaction (INV-18's posture).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Optional

from sqlmodel import Session, select

from ..models import (
    PC_KNOWLEDGE_LEVELS, PC_SKETCH_KINDS, PC_SKETCH_MAX, Character, PcDraft, PcDraftKnowledge,
    PcDraftMembership, PcDraftSketch, PcDraftSkill,
)

PC_EXISTS_MESSAGE = "Ce joueur a déjà un personnage dans ce monde."
DRAFT_LOCKED_MESSAGE = "Ce personnage est soumis : il ne peut plus être modifié."

_SKETCH_FIELDS: tuple[str, ...] = (
    "name", "role", "sentence", "group_label", "kind", "skill_key", "existing_entity_id",
)


class PcExists(ValueError):
    """The user already holds a player character of the world."""


class DraftLocked(ValueError):
    """The draft is no longer in `draft` status."""


def _now() -> datetime:
    return datetime.now(UTC)


def _require_open(draft: PcDraft) -> None:
    if draft.status != "draft":
        raise DraftLocked(DRAFT_LOCKED_MESSAGE)


def _text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _optional_text(value: Any) -> Optional[str]:
    text = _text(value)
    return text or None


def _skills(db: Session, draft: PcDraft) -> list[PcDraftSkill]:
    return list(db.exec(select(PcDraftSkill).where(PcDraftSkill.draft_id == draft.id)).all())


def _sketches(db: Session, draft: PcDraft) -> list[PcDraftSketch]:
    return list(db.exec(select(PcDraftSketch).where(PcDraftSketch.draft_id == draft.id)).all())


def _memberships(db: Session, draft: PcDraft) -> list[PcDraftMembership]:
    return list(db.exec(select(PcDraftMembership).where(PcDraftMembership.draft_id == draft.id)).all())


def _knowledge(db: Session, draft: PcDraft) -> list[PcDraftKnowledge]:
    return list(db.exec(select(PcDraftKnowledge).where(PcDraftKnowledge.draft_id == draft.id)).all())


def open_draft(db: Session, *, world_id: str, user_id: str) -> PcDraft:
    """The user's not yet approved draft of the world, or a new one, flushed."""
    pc = db.exec(select(Character.id).where(
        Character.world_id == world_id, Character.user_id == user_id,
        Character.character_type == "player",
    )).first()
    if pc is not None:
        raise PcExists(PC_EXISTS_MESSAGE)
    draft = db.exec(select(PcDraft).where(
        PcDraft.world_id == world_id, PcDraft.user_id == user_id, PcDraft.status != "approved",
    )).first()
    if draft is not None:
        return draft
    draft = PcDraft(world_id=world_id, user_id=user_id)
    db.add(draft)
    db.flush()
    return draft


# ── the player's save ──────────────────────────────────────────────────────


def _save_skills(db: Session, draft: PcDraft, skills: list[dict]) -> None:
    wanted: dict[str, dict] = {}
    for item in skills:
        key = item.get("skill_key")
        if key in wanted:
            raise ValueError("Une compétence est donnée deux fois.")
        wanted[key] = item
    stored = {row.skill_key: row for row in _skills(db, draft)}
    rows = dict(stored)
    for key, item in wanted.items():
        row = rows.get(key)
        if row is None:
            row = PcDraftSkill(draft_id=draft.id, world_id=draft.world_id, skill_key=key)
            rows[key] = row
        row.player_rank = item.get("rank")
        row.justification = _optional_text(item.get("justification"))
    for key, row in rows.items():
        if key not in wanted:
            row.player_rank = None
            row.justification = None
    _settle_skills(db, list(rows.values()), set(stored))


def _settle_skills(db: Session, rows: list[PcDraftSkill], stored: set[str]) -> None:
    """Keep every skill row holding a rank; delete a stored one (its key in `stored`) holding none."""
    for row in rows:
        if row.player_rank is not None or row.designer_rank is not None:
            db.add(row)
        elif row.skill_key in stored:
            db.delete(row)


def _sketch_values(item: dict) -> dict:
    name = _text(item.get("name"))
    if not name:
        raise ValueError("Chaque personne a un nom.")
    kind = item.get("kind")
    if kind not in PC_SKETCH_KINDS:
        raise ValueError("Sorte de personne inconnue.")
    skill_key = _optional_text(item.get("skill_key")) if kind == "master" else None
    if kind == "master" and skill_key is None:
        raise ValueError("Un maître enseigne une compétence.")
    return {
        "name": name, "role": _text(item.get("role")), "sentence": _text(item.get("sentence")),
        "group_label": _text(item.get("group_label")), "kind": kind, "skill_key": skill_key,
        "existing_entity_id": _optional_text(item.get("existing_entity_id")),
    }


def _save_sketches(db: Session, draft: PcDraft, sketches: list[dict]) -> None:
    if len(sketches) > PC_SKETCH_MAX:
        raise ValueError(f"Au plus {PC_SKETCH_MAX} personnes d'ancrage.")
    values = [(item.get("id"), _sketch_values(item)) for item in sketches]
    stored = _sketches(db, draft)
    rows = {row.id: row for row in stored}
    listed = {row_id for row_id, _ in values if row_id}
    for row in stored:
        if row.id not in listed:
            db.delete(row)
    for position, (row_id, fields) in enumerate(values):
        row = rows.get(row_id) if row_id else None
        if row is None:
            row = PcDraftSketch(draft_id=draft.id, world_id=draft.world_id, position=position,
                                origin="player", **fields)
        else:
            if any(getattr(row, f) != fields[f] for f in _SKETCH_FIELDS):
                row.origin = "player"
            for f in _SKETCH_FIELDS:
                setattr(row, f, fields[f])
            row.position = position
        db.add(row)


def _save_memberships(db: Session, draft: PcDraft, memberships: list[dict]) -> None:
    wanted: dict[str, Optional[str]] = {}
    for item in memberships:
        faction_id = item.get("faction_id")
        if faction_id in wanted:
            raise ValueError("Une faction est donnée deux fois.")
        wanted[faction_id] = _optional_text(item.get("role"))
    stored = _memberships(db, draft)
    rows = {row.faction_id: row for row in stored}
    for row in stored:
        if row.faction_id not in wanted:
            db.delete(row)
    for faction_id, role in wanted.items():
        row = rows.get(faction_id)
        if row is None:
            row = PcDraftMembership(draft_id=draft.id, world_id=draft.world_id, faction_id=faction_id,
                                    role=role, origin="player")
        elif row.role != role:
            row.role = role
            row.origin = "player"
        db.add(row)


def _save_knowledge(db: Session, draft: PcDraft, knowledge: list[dict]) -> None:
    values = []
    for item in knowledge:
        level = item.get("level")
        if level not in PC_KNOWLEDGE_LEVELS:
            raise ValueError("Niveau de connaissance inconnu.")
        content = _text(item.get("content"))
        if content:
            values.append((item.get("id"), level, content))
    stored = _knowledge(db, draft)
    rows = {row.id: row for row in stored}
    listed = {row_id for row_id, _, _ in values if row_id}
    for row in stored:
        if row.id not in listed:
            db.delete(row)
    for position, (row_id, level, content) in enumerate(values):
        row = rows.get(row_id) if row_id else None
        if row is None:
            row = PcDraftKnowledge(draft_id=draft.id, world_id=draft.world_id, position=position,
                                   level=level, content=content, origin="player")
        else:
            if row.level != level or row.content != content:
                row.origin = "player"
            row.level, row.content, row.position = level, content, position
        db.add(row)


def save_player_draft(db: Session, draft: PcDraft, *, name: str, story: str,
                      start_location_id: Optional[str], skills: list[dict],
                      sketches: list[dict], memberships: list[dict], knowledge: list[dict]) -> None:
    """Replace the player's draft with what the screen sent (C-12). A
    `ValueError` names the first malformed item; the caller then rolls back."""
    _require_open(draft)
    _save_skills(db, draft, skills)
    _save_sketches(db, draft, sketches)
    _save_memberships(db, draft, memberships)
    _save_knowledge(db, draft, knowledge)
    draft.name = _text(name)
    draft.story = _text(story)
    draft.start_location_id = start_location_id
    draft.start_location_set_by = "player" if start_location_id is not None else None
    draft.updated_at = _now()
    db.add(draft)
    db.flush()


# ── the designer's proposal ────────────────────────────────────────────────


def apply_design(db: Session, draft: PcDraft, design) -> None:
    """Lay `design` (a `creation_designer.CreationDesign`) over the draft:
    every designer rank and row is replaced, every player row kept."""
    _require_open(draft)
    stored = {row.skill_key: row for row in _skills(db, draft)}
    rows = dict(stored)
    for row in rows.values():
        row.designer_rank = None
        row.designer_reason = None
    for skill in design.skills:
        row = rows.get(skill.skill_key)
        if row is None:
            row = PcDraftSkill(draft_id=draft.id, world_id=draft.world_id, skill_key=skill.skill_key)
            rows[skill.skill_key] = row
        row.designer_rank = skill.rank
        row.designer_reason = skill.reason
    _settle_skills(db, list(rows.values()), set(stored))

    sketches = _sketches(db, draft)
    for row in sketches:
        if row.origin == "designer":
            db.delete(row)
    position = max((r.position for r in sketches if r.origin == "player"), default=-1) + 1
    for offset, sketch in enumerate(design.sketches):
        db.add(PcDraftSketch(
            draft_id=draft.id, world_id=draft.world_id, position=position + offset, name=sketch.name,
            role=sketch.role, sentence=sketch.sentence, group_label=sketch.group_label, kind=sketch.kind,
            skill_key=sketch.skill_key, existing_entity_id=sketch.existing_entity_id, origin="designer",
        ))

    memberships = _memberships(db, draft)
    held = {row.faction_id for row in memberships if row.origin == "player"}
    for row in memberships:
        if row.origin == "designer":
            db.delete(row)
    db.flush()   # the deletes first: a re-proposed faction meets the unique (draft, faction) index
    for membership in design.memberships:
        if membership.faction_id in held:
            continue
        held.add(membership.faction_id)
        db.add(PcDraftMembership(draft_id=draft.id, world_id=draft.world_id,
                                 faction_id=membership.faction_id, role=membership.role, origin="designer"))

    knowledge = _knowledge(db, draft)
    for row in knowledge:
        if row.origin == "designer":
            db.delete(row)
    position = max((r.position for r in knowledge if r.origin == "player"), default=-1) + 1
    for offset, line in enumerate(design.knowledge):
        db.add(PcDraftKnowledge(draft_id=draft.id, world_id=draft.world_id, position=position + offset,
                                level=line.level, content=line.content, origin="designer"))

    if draft.start_location_set_by != "player":
        draft.start_location_id = design.start_location_id
        draft.start_location_set_by = "designer" if design.start_location_id is not None else None
    draft.updated_at = _now()
    db.add(draft)
    db.flush()


# ── the submission ─────────────────────────────────────────────────────────


def submit_draft(db: Session, draft: PcDraft, violations: tuple) -> None:
    """`draft` -> `submitted` when `violations` (`creation_check.check_draft`
    of this draft) is empty; refused otherwise, nothing written."""
    _require_open(draft)
    if violations:
        raise ValueError("Le personnage ne peut pas être soumis.")
    now = _now()
    draft.status = "submitted"
    draft.submitted_at = now
    draft.updated_at = now
    db.add(draft)
    db.flush()
