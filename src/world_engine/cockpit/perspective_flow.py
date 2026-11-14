"""The shared perspective flow behind two doors, as everybody or as one character (TICKET-0125, BRIEF-0125-E, C-15; TICKET-0127, C-12).

One implementation, two callers: the creator's Lore route
(`routes/lore_perspective.py`), which answers the full body with the rows
and the audit, and the player's routes (`routes/player.py`), which answer
only `{verdict, answer, renderer, candidates, plan}` of it. Each step first
builds the view -- everybody's (`public_view`) or one character's through a
door (`perspective_view.character_view`; an unknown character is refused
before any journal row) -- then pings the planner, drafts the plan over
`descriptions_for(view)`, runs it through `execute_perspective_plan`,
computes the audit (`withheld_for`), renders through `render_perspective`
(an empty verdict never reaches a model, INV-58) and journals one row of
kind `perspective` through `lore_usage` (INV-59). Thin orchestration: no
`chat(`, no `select(` here.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlmodel import Session

from .. import lore_plan as _lore_plan
from .. import lore_prompt as _lore_prompt
from .. import lore_render as _lore_render
from .. import lore_usage as _usage
from .. import model_exchange, ollama_client
from ..llm_parse import LlmParseError
from ..lore_query import LorePlan
from ..perspective_audit import withheld_for
from ..perspective_query import BindingRefused, execute_perspective_plan
from ..perspective_render import render_perspective
from ..perspective_selectors import PerspectiveView, descriptions_for, public_view
from ..perspective_view import UnknownCharacter, character_view
from .routes.lore import _deserialize_plan, _serialize_plan

BINDING_REFUSED_MESSAGE = "Choix refusé."
UNKNOWN_CHARACTER_MESSAGE = "Personnage inconnu."


def _journal(db: Session, attempt: str, world_id: str, step: str, outcome: str,
             payload: dict, exchanges: list) -> None:
    _usage.record(db, attempt=attempt, world_id=world_id, kind="perspective", step=step,
                  outcome=outcome, payload=payload, exchanges=exchanges)


def _view(db: Session, world_id: str, character_id: str | None, door: str) -> PerspectiveView:
    """Everybody's view, or the character's through `door`; an unknown
    character -> 422, raised before any journal row."""
    if character_id is None:
        return public_view(db, world_id)
    try:
        return character_view(db, world_id, character_id, door=door)
    except UnknownCharacter as exc:
        raise HTTPException(status_code=422, detail=UNKNOWN_CHARACTER_MESSAGE) from exc


def _answer(plan: LorePlan, view: PerspectiveView, question: str, db: Session, exchanges: list,
            bindings: dict | None = None) -> dict:
    result = execute_perspective_plan(plan, view, db, bindings)
    audit = withheld_for(plan, view, db, bindings)
    spec = _lore_prompt.load(db, _lore_render.PROSE_USAGE)
    rendered = render_perspective(result, question, spec, nom=view.character_name, exchanges=exchanges)
    return {
        "verdict": result.verdict,
        "answer": rendered.prose,
        "renderer": rendered.renderer,
        "candidates": {item["ref"]: list(item["candidates"]) for item in result.ambiguous},
        "plan": _serialize_plan(plan),
        "rows": list(result.rows),
        "withheld": audit,
    }


def ask_flow(db: Session, *, question: str, world_id: str, asked_by: str, attempt: str,
             character_id: str | None = None, door: str = "creator") -> dict:
    """Draft, execute, audit, render, journal (`perspective_ask`); the full
    creator body. 503 / 502 raised after journaling."""
    view = _view(db, world_id, character_id, door)
    payload = {"question": question, "perspective": view.kind, "character_id": character_id,
               "asked_by": asked_by, "response": None, "withheld": []}
    exchanges: list = []
    try:
        ollama_client.ping()
    except ollama_client.OllamaError as exc:
        _journal(db, attempt, world_id, "perspective_ask", "unavailable",
                 dict(payload, error=_lore_render.PLANNER_UNAVAILABLE_MESSAGE), exchanges)
        raise HTTPException(status_code=503, detail=_lore_render.PLANNER_UNAVAILABLE_MESSAGE) from exc

    try:
        plan = _lore_plan.draft_plan(question, world_id, db, exchanges,
                                     descriptions=descriptions_for(view))
    except ollama_client.OllamaError as exc:
        model_exchange.fail(exchanges, exc)
        _journal(db, attempt, world_id, "perspective_ask", "unavailable",
                 dict(payload, error=_lore_render.PLANNER_UNAVAILABLE_MESSAGE), exchanges)
        raise HTTPException(status_code=503, detail=_lore_render.PLANNER_UNAVAILABLE_MESSAGE) from exc
    except LlmParseError as exc:
        model_exchange.fail(exchanges, exc)
        detail = f"lore plan drafting failed: {exc}"
        _journal(db, attempt, world_id, "perspective_ask", "parse_error", dict(payload, error=detail), exchanges)
        raise HTTPException(status_code=502, detail=detail) from exc

    response = _answer(plan, view, question, db, exchanges)
    _journal(db, attempt, world_id, "perspective_ask", "ok",
             dict(payload, response=response, withheld=response["withheld"], error=None), exchanges)
    return response


def resolve_flow(db: Session, *, plan_raw: dict, bindings: dict[str, str], question: str,
                 world_id: str, asked_by: str, attempt: str,
                 character_id: str | None = None, door: str = "creator") -> dict:
    """The client-held plan re-run with the bindings (`perspective_resolve`);
    never drafts again. A malformed plan or a refused binding -> 422,
    journaled `refused`."""
    view = _view(db, world_id, character_id, door)
    payload = {"question": question, "perspective": view.kind, "character_id": character_id,
               "asked_by": asked_by, "plan": plan_raw, "bindings": bindings, "response": None,
               "withheld": []}
    exchanges: list = []
    try:
        plan = _deserialize_plan(plan_raw)
        response = _answer(plan, view, question, db, exchanges, bindings)
    except HTTPException as exc:
        _journal(db, attempt, world_id, "perspective_resolve", "refused",
                 dict(payload, error=str(exc.detail)), exchanges)
        raise
    except BindingRefused as exc:
        _journal(db, attempt, world_id, "perspective_resolve", "refused",
                 dict(payload, error=BINDING_REFUSED_MESSAGE), exchanges)
        raise HTTPException(status_code=422, detail=BINDING_REFUSED_MESSAGE) from exc
    _journal(db, attempt, world_id, "perspective_resolve", "ok",
             dict(payload, response=response, withheld=response["withheld"], error=None), exchanges)
    return response
