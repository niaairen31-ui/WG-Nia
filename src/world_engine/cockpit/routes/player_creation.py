"""The player's character creation (TICKET-0126, BRIEF-0126-G; E1', B2, S1, U1, V1). Every path is under `/api/joueur/creation/`, keyed by the world and the profile, never by `World.is_active`. What the player learns of the world comes from the public view (INV-66); the rules from `creation_rules`; every sheet is judged by `creation_check` (INV-67). The designer's calls are journaled through `lore_usage`, kind `creation`.

A profile holds at most one open draft per world (V1). The routes open,
save, check, design and submit it; nothing here writes canon -- a
submitted draft waits for the creator (TICKET-0129). The designer route
pings the local model, asks the story's names and words
(`creation_designer.backstory_terms`), then the proposal
(`creation_designer.design`), and applies it with both journal rows in
one transaction; a model failure journals what was reached after a
rollback. Refusals before the model (404, 409) journal nothing.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from ... import creation_designer as _designer
from ... import lore_usage as _usage
from ... import model_exchange, ollama_client
from ...creation_check import Violation, check_creation, check_draft, verdict_dict
from ...creation_lore import public_places
from ...creation_rules import rules_dict, start_sheet, world_creation_rules
from ...db import get_session
from ...llm_parse import LlmParseError
from ...models import PcDraft, PcDraftSkill
from ...pc_draft_reads import draft_view, open_draft_of
from ...perspective_selectors import public_factions, public_skills, public_view
from ...skill_ranks import world_ladder
from ...writes.pc_drafts import (
    DRAFT_LOCKED_MESSAGE, DraftLocked, PcExists, apply_design, open_draft, save_player_draft, submit_draft,
)
from .player import _open_world, _player_profile

router = APIRouter()

NO_DRAFT = "Aucun brouillon de personnage."
DESIGNER_UNREADABLE_MESSAGE = "Le concepteur a répondu dans un format illisible."
CREATION_KIND = "creation"


class DraftOpenBody(BaseModel):
    profile_id: str
    world_id: str


class DraftSkillItem(BaseModel):
    skill_key: str
    rank: Optional[int] = Field(default=None, ge=0, le=5)
    justification: Optional[str] = None


class DraftSketchItem(BaseModel):
    id: Optional[str] = None
    name: str = ""
    role: str = ""
    sentence: str = ""
    group_label: str = ""
    kind: str
    skill_key: Optional[str] = None
    existing_entity_id: Optional[str] = None


class DraftMembershipItem(BaseModel):
    faction_id: str
    role: Optional[str] = None


class DraftKnowledgeItem(BaseModel):
    id: Optional[str] = None
    level: str
    content: str = ""


class DraftSaveBody(BaseModel):
    profile_id: str
    world_id: str
    name: str = ""
    story: str = ""
    start_location_id: Optional[str] = None
    skills: list[DraftSkillItem] = []
    sketches: list[DraftSketchItem] = []
    memberships: list[DraftMembershipItem] = []
    knowledge: list[DraftKnowledgeItem] = []


class VerifySkillItem(BaseModel):
    skill_key: str
    rank: Any = None


class VerifyBody(BaseModel):
    profile_id: str
    world_id: str
    skills: list[VerifySkillItem] = []


class DesignerBody(BaseModel):
    profile_id: str
    world_id: str
    attempt_id: Optional[str] = None


class SubmitBody(BaseModel):
    profile_id: str
    world_id: str


# ── shared steps ───────────────────────────────────────────────────────────


def _door(profile_id: str, world_id: str, db: Session) -> None:
    _open_world(world_id, db)
    _player_profile(profile_id, db)


def _open_draft(profile_id: str, world_id: str, db: Session) -> PcDraft:
    draft = open_draft_of(db, world_id=world_id, user_id=profile_id)
    if draft is None:
        raise HTTPException(status_code=404, detail=NO_DRAFT)
    return draft


def _writable(draft: PcDraft) -> None:
    if draft.status != "draft":
        raise HTTPException(status_code=409, detail=DRAFT_LOCKED_MESSAGE)


def _verdict(db: Session, draft: PcDraft) -> dict:
    """The player ranks judged by `check_creation`, with `check_draft`'s violations."""
    rows = db.exec(select(PcDraftSkill).where(PcDraftSkill.draft_id == draft.id)).all()
    choices = {row.skill_key: row.player_rank for row in rows if row.player_rank is not None}
    verdict = check_creation(db, draft.world_id, choices, enforce_visibility=True)
    return verdict_dict(verdict, check_draft(db, draft))


def _draft_body(db: Session, draft: PcDraft) -> dict:
    return {"draft": draft_view(db, draft, view=public_view(db, draft.world_id)),
            "verdict": _verdict(db, draft)}


def _violation_dicts(violations: tuple[Violation, ...]) -> list[dict]:
    return [{"code": v.code, "skill_key": v.skill_key, "message": v.message} for v in violations]


# ── the catalogue, the draft ───────────────────────────────────────────────


@router.get("/api/joueur/creation/catalogue")
def creation_catalogue(profile_id: str, world_id: str, db: Session = Depends(get_session)) -> dict:
    """What a character can be made of in this world: the rules, the rank
    labels, the skills everybody knows, the starting places, the factions."""
    _door(profile_id, world_id, db)
    view = public_view(db, world_id)
    rules = world_creation_rules(db, world_id)
    known = {row["skill_id"]: row for row in public_skills(world_id, view, db)}
    skills = []
    for line in start_sheet(db, world_id, rules):
        base = line.skill_key == line.base_domain
        if not base and line.skill_key not in view.skill_ids:
            continue
        row = known.get(line.skill_key, {})
        skills.append({
            "skill_key": line.skill_key, "name": line.name, "base_domain": line.base_domain,
            "system": row.get("system"), "description": row.get("description"),
            "requires_master": line.requires_master, "start_rank": line.start_rank, "max_rank": line.max_rank,
        })
    factions = [{"entity_id": f["entity_id"], "name": f["name"], "description": f["description"]}
                for f in public_factions(world_id, view, db)]
    return {
        "rules": rules_dict(rules),
        "ranks": [step.label for step in world_ladder(db, world_id)],
        "skills": skills,
        "places": public_places(db, world_id, view),
        "factions": factions,
    }


@router.get("/api/joueur/creation/brouillon")
def get_draft(profile_id: str, world_id: str, db: Session = Depends(get_session)) -> dict:
    _door(profile_id, world_id, db)
    draft = open_draft_of(db, world_id=world_id, user_id=profile_id)
    if draft is None:
        return {"draft": None, "verdict": None}
    return _draft_body(db, draft)


@router.post("/api/joueur/creation/brouillon", status_code=201)
def open_player_draft(body: DraftOpenBody, db: Session = Depends(get_session)) -> dict:
    _door(body.profile_id, body.world_id, db)
    try:
        draft = open_draft(db, world_id=body.world_id, user_id=body.profile_id)
    except PcExists as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.commit()
    db.refresh(draft)
    return _draft_body(db, draft)


@router.put("/api/joueur/creation/brouillon")
def save_draft(body: DraftSaveBody, db: Session = Depends(get_session)) -> dict:
    _door(body.profile_id, body.world_id, db)
    draft = _open_draft(body.profile_id, body.world_id, db)
    try:
        save_player_draft(
            db, draft, name=body.name, story=body.story, start_location_id=body.start_location_id,
            skills=[item.model_dump() for item in body.skills],
            sketches=[item.model_dump() for item in body.sketches],
            memberships=[item.model_dump() for item in body.memberships],
            knowledge=[item.model_dump() for item in body.knowledge],
        )
    except DraftLocked as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    db.refresh(draft)
    return _draft_body(db, draft)


@router.post("/api/joueur/creation/verifier")
def verify_sheet(body: VerifyBody, db: Session = Depends(get_session)) -> dict:
    """A sheet judged as it stands; writes nothing."""
    _door(body.profile_id, body.world_id, db)
    choices = {item.skill_key: item.rank for item in body.skills}
    verdict = check_creation(db, body.world_id, choices, enforce_visibility=True)
    return verdict_dict(verdict, verdict.violations)


# ── the designer ───────────────────────────────────────────────────────────


def _subject_payload(draft: PcDraft, asked_by: str, names: tuple[str, ...], keywords: tuple[str, ...],
                     error: Optional[str]) -> dict:
    return {"draft_id": draft.id, "asked_by": asked_by, "story": draft.story, "names": list(names),
            "keywords": list(keywords), "error": error}


def _design_payload(draft: PcDraft, asked_by: str, error: Optional[str], design=None) -> dict:
    if design is None:
        return {"draft_id": draft.id, "asked_by": asked_by, "lore": [], "proposal": None,
                "violations": [], "notes": [], "error": error}
    return {"draft_id": draft.id, "asked_by": asked_by, "lore": list(design.lore.lines),
            "proposal": _designer.design_record(design), "violations": _violation_dicts(design.violations),
            "notes": list(design.notes), "error": error}


@router.post("/api/joueur/creation/concepteur")
def ask_designer(body: DesignerBody, db: Session = Depends(get_session)) -> dict:
    """The designer's proposal laid over the draft; both calls journaled."""
    _door(body.profile_id, body.world_id, db)
    draft = _open_draft(body.profile_id, body.world_id, db)
    _writable(draft)
    journal = {"attempt": _usage.attempt_id(body.attempt_id), "world_id": draft.world_id,
               "kind": CREATION_KIND}
    asked_by = f"player:{body.profile_id}"
    subject_exchanges: list = []
    design_exchanges: list = []

    def refuse_subject(outcome: str, message: str, status: int) -> HTTPException:
        db.rollback()
        _usage.record(db, **journal, step=_designer.SUBJECT_USAGE, outcome=outcome,
                      payload=_subject_payload(draft, asked_by, (), (), message), exchanges=subject_exchanges)
        return HTTPException(status_code=status, detail=message)

    try:
        ollama_client.ping()
    except ollama_client.OllamaError as exc:
        raise refuse_subject("unavailable", _designer.DESIGNER_UNAVAILABLE_MESSAGE, 503) from exc
    try:
        names, keywords = _designer.backstory_terms(db, draft, subject_exchanges)
    except ollama_client.OllamaError as exc:
        model_exchange.fail(subject_exchanges, exc)
        raise refuse_subject("unavailable", _designer.DESIGNER_UNAVAILABLE_MESSAGE, 503) from exc
    except LlmParseError as exc:
        model_exchange.fail(subject_exchanges, exc)
        raise refuse_subject("parse_error", DESIGNER_UNREADABLE_MESSAGE, 502) from exc

    subject_ok = dict(journal, step=_designer.SUBJECT_USAGE, outcome="ok",
                      payload=_subject_payload(draft, asked_by, names, keywords, None),
                      exchanges=subject_exchanges)
    try:
        design = _designer.design(db, draft, names, keywords, design_exchanges)
    except (ollama_client.OllamaError, LlmParseError) as exc:
        model_exchange.fail(design_exchanges, exc)
        unavailable = isinstance(exc, ollama_client.OllamaError)
        message = _designer.DESIGNER_UNAVAILABLE_MESSAGE if unavailable else DESIGNER_UNREADABLE_MESSAGE
        db.rollback()
        _usage.stage(db, **subject_ok)
        _usage.record(db, **journal, step=_designer.DESIGN_USAGE,
                      outcome="unavailable" if unavailable else "parse_error",
                      payload=_design_payload(draft, asked_by, message), exchanges=design_exchanges)
        raise HTTPException(status_code=503 if unavailable else 502, detail=message) from exc

    apply_design(db, draft, design)
    _usage.stage(db, **subject_ok)
    _usage.stage(db, **journal, step=_designer.DESIGN_USAGE, outcome="ok",
                 payload=_design_payload(draft, asked_by, None, design), exchanges=design_exchanges)
    db.commit()
    db.refresh(draft)
    return dict(_draft_body(db, draft),
                designer={"notes": list(design.notes), "violations": _violation_dicts(design.violations)})


# ── the submission ─────────────────────────────────────────────────────────


@router.post("/api/joueur/creation/soumettre")
def submit_player_draft(body: SubmitBody, db: Session = Depends(get_session)) -> dict:
    """Submitted only when `check_draft` finds nothing (INV-67); otherwise nothing is written."""
    _door(body.profile_id, body.world_id, db)
    draft = _open_draft(body.profile_id, body.world_id, db)
    _writable(draft)
    violations = check_draft(db, draft)
    if violations:
        return dict(_draft_body(db, draft), submitted=False)
    submit_draft(db, draft, violations)
    db.commit()
    db.refresh(draft)
    return dict(_draft_body(db, draft), submitted=True)
