"""The player's door (TICKET-0125, BRIEF-0125-E, C-11): profiles, open worlds, what everybody knows.

Every path is under `/api/joueur/`. A profile is a `user` row with
`role='player'` (K1), written by `writes/users.create_player_profile`; its
id travels in the request body -- no session, no cookie (drafting
decision 9). A world is offered to a player only when `open_to_players`
(C1), never by `World.is_active` (B2). The savoir routes serve the public
perspective only -- there is no role switch here: they run the shared flow
(`cockpit/perspective_flow.py`) as `player:<profile_id>` and answer only
`{verdict, answer, renderer, candidates, plan}`; the rows and the audit are
journaled, never returned (INV-01, INV-02).
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from ... import lore_usage as _usage
from ...db import get_session
from ...models import User, World
from ...writes.users import ProfileNameTaken, create_player_profile
from .. import perspective_flow as _flow
from .creator import _world_detail

router = APIRouter()

WORLD_NOT_FOUND = "Monde introuvable."
PROFILE_NOT_FOUND = "Profil introuvable."
PLAYER_ANSWER_KEYS: tuple[str, ...] = ("verdict", "answer", "renderer", "candidates", "plan")


class ProfileCreateBody(BaseModel):
    name: str


class SavoirAskBody(BaseModel):
    profile_id: str
    world_id: str
    question: str
    attempt_id: Optional[str] = None


class SavoirResolveBody(BaseModel):
    profile_id: str
    world_id: str
    plan: dict
    bindings: dict[str, str]
    question: str
    attempt_id: Optional[str] = None


def _open_world(world_id: str, db: Session) -> World:
    world = db.get(World, world_id)
    if world is None or not world.open_to_players:
        raise HTTPException(status_code=404, detail=WORLD_NOT_FOUND)
    return world


def _player_profile(profile_id: str, db: Session) -> User:
    user = db.get(User, profile_id)
    if user is None or not user.is_active or user.role != "player":
        raise HTTPException(status_code=404, detail=PROFILE_NOT_FOUND)
    return user


def _player_answer(body: dict) -> dict:
    return {key: body[key] for key in PLAYER_ANSWER_KEYS}


@router.get("/api/joueur/profils")
def list_profiles(db: Session = Depends(get_session)) -> list[dict]:
    users = db.exec(
        select(User).where(User.role == "player", User.is_active == True)  # noqa: E712
        .order_by(User.name, User.id)
    ).all()
    return [{"id": u.id, "name": u.name} for u in users]


@router.post("/api/joueur/profils", status_code=201)
def create_profile(body: ProfileCreateBody, db: Session = Depends(get_session)) -> dict:
    try:
        user = create_player_profile(db, body.name)
    except ProfileNameTaken as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    db.refresh(user)
    return {"id": user.id, "name": user.name}


@router.get("/api/joueur/mondes")
def list_open_worlds(db: Session = Depends(get_session)) -> list[dict]:
    worlds = db.exec(
        select(World).where(World.open_to_players == True)  # noqa: E712
        .order_by(World.name, World.id)
    ).all()
    out = []
    for world in worlds:
        detail = _world_detail(world, db)
        out.append({key: detail[key] for key in ("id", "name", "description", "laws")})
    return out


@router.post("/api/joueur/savoir/ask")
def ask_savoir(body: SavoirAskBody, db: Session = Depends(get_session)) -> dict:
    _open_world(body.world_id, db)
    _player_profile(body.profile_id, db)
    response = _flow.ask_flow(db, question=body.question, world_id=body.world_id,
                              asked_by=f"player:{body.profile_id}",
                              attempt=_usage.attempt_id(body.attempt_id))
    return _player_answer(response)


@router.post("/api/joueur/savoir/resolve")
def resolve_savoir(body: SavoirResolveBody, db: Session = Depends(get_session)) -> dict:
    _open_world(body.world_id, db)
    _player_profile(body.profile_id, db)
    response = _flow.resolve_flow(db, plan_raw=body.plan, bindings=body.bindings,
                                  question=body.question, world_id=body.world_id,
                                  asked_by=f"player:{body.profile_id}",
                                  attempt=_usage.attempt_id(body.attempt_id))
    return _player_answer(response)
