"""Reads for the model-choice review (TICKET-0095, K1, C-05/C-06): the
choices of the active world that wait for Nia's verdict (E2, J1), what the
model cited and where it came from, and the scope K1 proposes for an
appellation (C2). Candidates and evidence are read from their rows (G1),
never from the JSON audit columns.

Read-only: no `db.add`, no commit, no model call. Isolated from the
consultation pipeline like the names panel (`lore_isolation.py` R17).
"""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session, select

from .day_choice import excerpt_key
from .facet_reads import facts_of
from .facets import FACETS
from .lore_mentions_read import excerpt as text_excerpt
from .lore_resolve import normalize_surface
from .models import (
    Batch,
    DayMentionChoice,
    DayMentionChoiceCandidate,
    DayMentionChoiceEvidence,
    DayMentionReview,
    DayRewrite,
    Entity,
    Fact,
    FactDefault,
    PassPlay,
)

REVIEWABLE_VERDICTS: tuple[str, ...] = ("accepted", "rejected")


def is_reviewable(choice: DayMentionChoice) -> bool:
    """E2: an accepted choice, or a rejected one that still names an entity
    (a refused excerpt, not an out-of-range number)."""
    return choice.verdict == "accepted" or (
        choice.verdict == "rejected" and choice.chosen_entity_id is not None
    )


def reviewable_choice(db: Session, choice_id: str, world_id: str) -> Optional[DayMentionChoice]:
    """The choice when it exists, belongs to `world_id` and is reviewable —
    reviewed or not. `None` otherwise."""
    choice = db.get(DayMentionChoice, choice_id)
    if choice is None or choice.world_id != world_id or not is_reviewable(choice):
        return None
    return choice


def is_reviewed(db: Session, choice_id: str) -> bool:
    """J1: any `day_mention_review` row on this choice."""
    return db.exec(
        select(DayMentionReview.id).where(DayMentionReview.choice_id == choice_id)
    ).first() is not None


def _entity_name(db: Session, entity_id: Optional[str]) -> Optional[str]:
    if entity_id is None:
        return None
    entity = db.get(Entity, entity_id)
    return entity.name if entity is not None else None


def _fact_scopes(db: Session, fact_ids: list[str]) -> dict[str, list[dict]]:
    """R-07: the scopes above `unaware` of each fact — `world` first when the
    fact's own `default_level` is above it, then its `fact_default` rows by
    `(scope_type, id)`, duplicates skipped. Two queries."""
    scopes: dict[str, list[dict]] = {fid: [] for fid in fact_ids}
    if not fact_ids:
        return scopes
    for fact in db.exec(select(Fact).where(Fact.id.in_(fact_ids))).all():
        if fact.default_level != "unaware":
            scopes[fact.id].append({"scope_type": "world", "scope_name": None})
    defaults = db.exec(
        select(FactDefault)
        .where(FactDefault.fact_id.in_(fact_ids), FactDefault.level != "unaware")
        .order_by(FactDefault.scope_type, FactDefault.id)
    ).all()
    for default in defaults:
        entry = {"scope_type": default.scope_type, "scope_name": _entity_name(db, default.scope_id)}
        if entry not in scopes[default.fact_id]:
            scopes[default.fact_id].append(entry)
    return scopes


def cited_evidence(db: Session, choice: DayMentionChoice, declaration: str) -> tuple[str, list[dict]]:
    """Where the model's excerpt comes from, found with the judge's own key
    (C-04): `("facts", [...])` when it is in cited facts of the chosen
    entity (rendered through `facts_of`, creator-only facts excluded),
    `("declaration", [])` when only in the declaration, `("none", [])`
    otherwise or when the key is shorter than three characters."""
    key = excerpt_key(choice.excerpt or "")
    if len(key) < 3:
        return "none", []
    evidence_ids = db.exec(
        select(DayMentionChoiceEvidence.fact_id)
        .where(DayMentionChoiceEvidence.choice_id == choice.id)
        .order_by(DayMentionChoiceEvidence.ordinal)
    ).all()
    cited = set(evidence_ids)
    hits = []
    if choice.chosen_entity_id is not None and cited:
        rows = facts_of(db, entity_id=choice.chosen_entity_id, facets=tuple(FACETS))
        hits = [row for row in rows if row.fact_id in cited and key in normalize_surface(row.content)]
    if hits:
        scopes = _fact_scopes(db, [row.fact_id for row in hits])
        return "facts", [
            {"fact_id": row.fact_id, "content": row.content, "scopes": scopes[row.fact_id]}
            for row in hits
        ]
    if key in normalize_surface(declaration):
        return "declaration", []
    return "none", []


def preselected_scope(source: str, evidence: list[dict]) -> str:
    """C2: `world` iff the excerpt comes from a cited fact known to everyone;
    `rencontre` otherwise."""
    if source == "facts" and any(
        scope["scope_type"] == "world" for item in evidence for scope in item["scopes"]
    ):
        return "world"
    return "rencontre"


def _entity_ref(entity: Entity) -> dict:
    return {"id": entity.id, "name": entity.name, "type": entity.type}


def _candidates(db: Session, choice_id: str) -> list[dict]:
    rows = db.exec(
        select(Entity)
        .join(DayMentionChoiceCandidate, DayMentionChoiceCandidate.entity_id == Entity.id)
        .where(DayMentionChoiceCandidate.choice_id == choice_id)
        .order_by(DayMentionChoiceCandidate.ordinal)
    ).all()
    return [_entity_ref(entity) for entity in rows]


def _planned(db: Session, choice: DayMentionChoice) -> bool:
    """R-11: some rewrite of the choice's `pass_play` was constructed before
    the choice (the plan path); a 409 attempt has none."""
    stamps = db.exec(
        select(DayRewrite.created_at).where(DayRewrite.pass_play_id == choice.pass_play_id)
    ).all()
    return any(stamp <= choice.created_at for stamp in stamps)


def _pending_row(db: Session, choice: DayMentionChoice) -> dict:
    """One pending row (C-06)."""
    pass_play = db.get(PassPlay, choice.pass_play_id)
    batch = db.get(Batch, pass_play.batch_id)
    declared = pass_play.declared_action
    source, evidence = cited_evidence(db, choice, declared)
    return {
        "id": choice.id,
        "surface_form": choice.surface_form, "category": choice.category, "trigger": choice.trigger,
        "verdict": choice.verdict,
        "verdict_detail": choice.verdict_detail, "excerpt": choice.excerpt, "reason": choice.reason,
        "day": {
            "day_number": batch.day_number,
            "character_name": _entity_name(db, pass_play.character_id),
            "declaration": text_excerpt(declared, choice.surface_form),
            "planned": _planned(db, choice),
        },
        "chosen": _entity_ref(db.get(Entity, choice.chosen_entity_id)),
        "candidates": _candidates(db, choice.id),
        "excerpt_source": source,
        "evidence": evidence,
        "preselected_scope": preselected_scope(source, evidence),
    }


def list_pending_choices(db: Session, world_id: str) -> list[dict]:
    """Every reviewable, not-yet-reviewed choice of `world_id` (E2, J1),
    ordered by `(created_at, id)`, as pending rows. Empty list when none."""
    choices = db.exec(
        select(DayMentionChoice)
        .where(DayMentionChoice.world_id == world_id, DayMentionChoice.verdict.in_(REVIEWABLE_VERDICTS))
        .order_by(DayMentionChoice.created_at, DayMentionChoice.id)
    ).all()
    return [
        _pending_row(db, choice)
        for choice in choices
        if is_reviewable(choice) and not is_reviewed(db, choice.id)
    ]
