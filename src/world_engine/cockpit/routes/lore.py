"""Lore consultation routes (TICKET-0085, BRIEF-0085-c).

Thin orchestration only -- no `chat(`, no `select(` here, matching the
`routes/observation.py` doctrine: every read and every model call happens in
`lore_plan.py` / `lore_query.py` / `lore_candidates.py` / `lore_resolve.py`.

The plan is client-held (Scope OUT: no server-side plan storage, no cache).
`/api/lore/ask` drafts a plan through the model and executes it; `/api/lore/
resolve` takes that same plan back from the client together with creator
bindings for any ambiguous mention, re-validates each binding, and executes
-- it never calls `draft_plan` again, so disambiguation cannot shift the
question.

Every step that reaches the model is journaled through `lore_usage`
(TICKET-0103, BRIEF-0103-C, decision A2), under the panel's `attempt_id`:
the question, the response as sent, and the model exchanges it took. A
journal row is the only write either route makes.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from ... import lore_candidates as _lore_candidates
from ... import lore_plan as _lore_plan
from ... import lore_prompt as _lore_prompt
from ... import lore_render as _lore_render
from ... import lore_resolve as _lore_resolve
from ... import lore_usage as _usage
from ... import model_exchange, ollama_client
from ...db import get_session
from ...llm_parse import LlmParseError
from ...lore_query import LorePlan, PlanCall, PlanMention, execute_plan

router = APIRouter()


class LoreAskBody(BaseModel):
    question: str
    world_id: str
    attempt_id: Optional[str] = None


class LoreResolveBody(BaseModel):
    plan: dict
    bindings: dict[str, str]
    world_id: str
    # The plan is client-held (no server-side plan storage); so is the
    # question it was drafted from. A resolved plan can turn out "answered"
    # (BRIEF-0085-c: a binding can settle every mention), and rendering that
    # verdict needs the original question text for the model prompt --
    # nothing server-side remembers it between /ask and /resolve.
    question: str
    attempt_id: Optional[str] = None


def _serialize_plan(plan: LorePlan) -> dict:
    return {
        "mentions": [
            {"ref": m.ref, "surface_form": m.surface_form, "category": m.category}
            for m in plan.mentions
        ],
        "calls": [{"selector": c.selector, "args": list(c.args)} for c in plan.calls],
    }


def _deserialize_plan(raw: dict) -> LorePlan:
    try:
        mentions = tuple(
            PlanMention(ref=m["ref"], surface_form=m["surface_form"], category=m["category"])
            for m in raw.get("mentions", [])
        )
        calls = tuple(
            PlanCall(selector=c["selector"], args=tuple(c["args"]))
            for c in raw.get("calls", [])
        )
    except (KeyError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=f"malformed plan: {exc}") from exc
    return LorePlan(mentions=mentions, calls=calls)


def _result_body(plan: LorePlan, result, question: str, db: Session, exchanges: list) -> dict:
    candidates: dict[str, list[dict]] = {}
    if result.verdict == "ambiguous_mention":
        candidates = {
            am["ref"]: _lore_candidates.describe_candidates(am["candidate_ids"], db)
            for am in result.ambiguous_mentions
        }
    spec = _lore_prompt.load(db, _lore_render.PROSE_USAGE)
    rendered = _lore_render.render(result, question, spec, candidates, exchanges)
    return {
        "verdict": result.verdict,
        "rows": list(result.rows),
        "trace": result.trace,
        "plan": _serialize_plan(plan),
        "candidates": candidates,
        "answer": rendered.prose,
        "renderer": rendered.renderer,
        "near": list(result.near),
    }


def _journal(db: Session, attempt: str, world_id: str, step: str, outcome: str,
             payload: dict, exchanges: list) -> None:
    _usage.record(db, attempt=attempt, world_id=world_id, kind="consult", step=step,
                  outcome=outcome, payload=payload, exchanges=exchanges)


@router.post("/api/lore/ask")
def ask_lore(body: LoreAskBody, db: Session = Depends(get_session)) -> dict:
    attempt = _usage.attempt_id(body.attempt_id)
    payload = {"question": body.question, "response": None}
    exchanges: list = []
    try:
        ollama_client.ping()
    except ollama_client.OllamaError as exc:
        _journal(db, attempt, body.world_id, "ask", "unavailable",
                 dict(payload, error=_lore_render.PLANNER_UNAVAILABLE_MESSAGE), exchanges)
        raise HTTPException(
            status_code=503, detail=_lore_render.PLANNER_UNAVAILABLE_MESSAGE
        ) from exc

    try:
        plan = _lore_plan.draft_plan(body.question, body.world_id, db, exchanges)
    except ollama_client.OllamaError as exc:
        model_exchange.fail(exchanges, exc)
        _journal(db, attempt, body.world_id, "ask", "unavailable",
                 dict(payload, error=_lore_render.PLANNER_UNAVAILABLE_MESSAGE), exchanges)
        raise HTTPException(
            status_code=503, detail=_lore_render.PLANNER_UNAVAILABLE_MESSAGE
        ) from exc
    except LlmParseError as exc:
        model_exchange.fail(exchanges, exc)
        detail = f"lore plan drafting failed: {exc}"
        _journal(db, attempt, body.world_id, "ask", "parse_error", dict(payload, error=detail), exchanges)
        raise HTTPException(status_code=502, detail=detail) from exc

    result = execute_plan(plan, body.world_id, db)
    response = _result_body(plan, result, body.question, db, exchanges)
    _journal(db, attempt, body.world_id, "ask", "ok", dict(payload, response=response, error=None),
             exchanges)
    return response


def _validated_plan(body: LoreResolveBody, db: Session) -> LorePlan:
    plan = _deserialize_plan(body.plan)

    mention_by_ref = {m.ref: m for m in plan.mentions}
    for ref, entity_id in body.bindings.items():
        mention = mention_by_ref.get(ref)
        if mention is None:
            raise HTTPException(status_code=422, detail=f"binding ref {ref!r} is not in the submitted plan")
        if not _lore_resolve.validate_binding(entity_id, mention.category, body.world_id, db):
            raise HTTPException(
                status_code=422,
                detail=(
                    f"binding {entity_id!r} for {ref!r} is not an active "
                    f"{mention.category} entity in this world"
                ),
            )
    return plan


@router.post("/api/lore/resolve")
def resolve_lore(body: LoreResolveBody, db: Session = Depends(get_session)) -> dict:
    attempt = _usage.attempt_id(body.attempt_id)
    payload = {"question": body.question, "plan": body.plan, "bindings": body.bindings,
               "response": None}
    try:
        plan = _validated_plan(body, db)
    except HTTPException as exc:
        _journal(db, attempt, body.world_id, "resolve", "refused", dict(payload, error=str(exc.detail)), [])
        raise

    exchanges: list = []
    result = execute_plan(plan, body.world_id, db, bindings=body.bindings)
    response = _result_body(plan, result, body.question, db, exchanges)
    _journal(db, attempt, body.world_id, "resolve", "ok", dict(payload, response=response, error=None),
             exchanges)
    return response
