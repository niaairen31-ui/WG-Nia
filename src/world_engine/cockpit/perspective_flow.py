"""The shared public-perspective flow behind two doors (TICKET-0125, BRIEF-0125-E, C-15).

One implementation, two callers: the creator's Lore route
(`routes/lore_perspective.py`), which answers the full body with the rows
and the audit, and the player's route (`routes/player.py`), which answers
only `{verdict, answer, renderer, candidates, plan}` of it. Each step pings
the planner, drafts the plan over `PERSPECTIVE_DESCRIPTIONS`, runs it
through `execute_public_plan`, computes the audit (`perspective_audit`),
renders through `render_public` (an empty verdict never reaches a model,
INV-58) and journals one row of kind `perspective` through `lore_usage`
(INV-59). Thin orchestration: no `chat(`, no `select(` here.
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
from ..perspective_audit import withheld as _withheld
from ..perspective_query import BindingRefused, execute_public_plan
from ..perspective_render import render_public
from ..perspective_selectors import PERSPECTIVE_DESCRIPTIONS
from .routes.lore import _deserialize_plan, _serialize_plan

PERSPECTIVE = "public"
BINDING_REFUSED_MESSAGE = "Choix refusé."


def _journal(db: Session, attempt: str, world_id: str, step: str, outcome: str,
             payload: dict, exchanges: list) -> None:
    _usage.record(db, attempt=attempt, world_id=world_id, kind="perspective", step=step,
                  outcome=outcome, payload=payload, exchanges=exchanges)


def _answer(plan: LorePlan, world_id: str, question: str, db: Session, exchanges: list,
            bindings: dict | None = None) -> dict:
    result = execute_public_plan(plan, world_id, db, bindings)
    audit = _withheld(plan, world_id, db, bindings)
    spec = _lore_prompt.load(db, _lore_render.PROSE_USAGE)
    rendered = render_public(result, question, spec, exchanges)
    return {
        "verdict": result.verdict,
        "answer": rendered.prose,
        "renderer": rendered.renderer,
        "candidates": {item["ref"]: list(item["candidates"]) for item in result.ambiguous},
        "plan": _serialize_plan(plan),
        "rows": list(result.rows),
        "withheld": audit,
    }


def ask_flow(db: Session, *, question: str, world_id: str, asked_by: str, attempt: str) -> dict:
    """Draft, execute, audit, render, journal (`perspective_ask`); the full
    creator body. 503 / 502 raised after journaling."""
    payload = {"question": question, "perspective": PERSPECTIVE, "asked_by": asked_by,
               "response": None, "withheld": []}
    exchanges: list = []
    try:
        ollama_client.ping()
    except ollama_client.OllamaError as exc:
        _journal(db, attempt, world_id, "perspective_ask", "unavailable",
                 dict(payload, error=_lore_render.PLANNER_UNAVAILABLE_MESSAGE), exchanges)
        raise HTTPException(status_code=503, detail=_lore_render.PLANNER_UNAVAILABLE_MESSAGE) from exc

    try:
        plan = _lore_plan.draft_plan(question, world_id, db, exchanges,
                                     descriptions=PERSPECTIVE_DESCRIPTIONS)
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

    response = _answer(plan, world_id, question, db, exchanges)
    _journal(db, attempt, world_id, "perspective_ask", "ok",
             dict(payload, response=response, withheld=response["withheld"], error=None), exchanges)
    return response


def resolve_flow(db: Session, *, plan_raw: dict, bindings: dict[str, str], question: str,
                 world_id: str, asked_by: str, attempt: str) -> dict:
    """The client-held plan re-run with the bindings (`perspective_resolve`);
    never drafts again. A malformed plan or a refused binding -> 422,
    journaled `refused`."""
    payload = {"question": question, "perspective": PERSPECTIVE, "asked_by": asked_by,
               "plan": plan_raw, "bindings": bindings, "response": None, "withheld": []}
    exchanges: list = []
    try:
        plan = _deserialize_plan(plan_raw)
        response = _answer(plan, world_id, question, db, exchanges, bindings)
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
