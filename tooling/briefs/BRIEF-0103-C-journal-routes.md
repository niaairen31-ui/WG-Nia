<!-- slug: journal-routes -->
# BRIEF 0103-C — "Journal the five Lore routes under their attempt"

Lot: LOT-0103-lore-usage-journal.md (authoritative on conflict)
Depends on: BRIEF-0103-A (`write_usage_event`, `PAYLOAD_KEYS`), BRIEF-0103-B (`model_exchange`, the `exchanges` parameters)
Commit header for decisions: `(BRIEF-0103-c, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0103`, on the tree BRIEF-0103-B left, before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/cockpit/routes/lore_write.py:15` → `(K1); nothing is written by a draft route, ever.`; `:38` → `class StatementBody(BaseModel):`; `:43` → `class CommitBody(BaseModel):`; `:60` → `@router.post("/api/lore/write/questions")`; `:93-94` → `@router.post("/api/lore/write/commit")` / `def write_commit(`; `:109` → `@router.get("/api/lore/write/entries")`.
- `src/world_engine/cockpit/routes/lore.py:34` → `class LoreAskBody(BaseModel):`; `:76` → `def _result_body(plan: LorePlan, result, question: str, db: Session) -> dict:`; `:83` → `    spec = _lore_prompt.load(db, "lore_rows_to_prose")`; `:98` → `def ask_lore(`; `:107` → `        plan = _lore_plan.draft_plan(body.question, body.world_id, db)` inside a `try` catching `LlmParseError` only; `:116` → `def resolve_lore(`.
- `src/world_engine/lore_write_apply.py:84` → `            item["_type"] = item["type"]`; `:89` → `            item["_type"] = entity.type`.
- `tooling/verify/checks/lore_write.py:63` → `      no draft request changes any row count;`; `:606` → `def check_e2() -> None:` (commits only in `write_commit`).
- `tooling/verify/checks/lore_isolation.py:37` → R16's docstring (every `OllamaError` handler in `ask_lore` raises `HTTPException` with a named `detail`).
- `src/world_engine/lore_render.py` defines `PLANNER_UNAVAILABLE_MESSAGE` and, since B, `PROSE_USAGE`; `src/world_engine/lore_plan.py` defines `PLAN_USAGE`; `src/world_engine/model_exchange.py` defines `fail`.
- `src/world_engine/lore_usage.py` does not exist.

## Facts carried

### R-02 — the draft is client-held, the draft routes write nothing [M]
Opened: `src/world_engine/cockpit/routes/lore_write.py:15` (« nothing is
written by a draft route, ever »), `:60-90`; `tooling/verify/checks/
lore_write.py:63` (E1b) and `:113` (`_COUNTED_TABLES`).
Finding: `/questions` and `/draft` return their result and write no row;
E1b asserts that no draft request changes the count of `_COUNTED_TABLES`
(`entity, fact, fact_participant, fact_default, knowledge, relation,
faction_membership, lore_entry, lore_entry_row`).
Consequence: journaling a draft makes these routes write; E1b stays true
(the journal is not counted) and its wording is narrowed in C; the route
docstring says « no canon row ».

### R-07 — the consultation route [M]
Opened: `src/world_engine/cockpit/routes/lore.py:34-46, 76-131`;
`lore_isolation.py` R6 (`:21`, no `chat(`/`select(` call in the route),
R7 (`:24`, no `draft_plan` in resolve), R16 (`:37` and implementation
311-389: every `except` naming `OllamaError` in `ask_lore` raises
`HTTPException(detail=<named constant>)`).
Finding: `ask_lore` pings Ollama (503 + `PLANNER_UNAVAILABLE_MESSAGE` when
down), then `draft_plan` with only `LlmParseError` caught (502): an
`OllamaError` raised by the plan's own `chat` call is unhandled (500).
`resolve_lore` validates the plan and bindings (422) and never redrafts.
Neither route writes (enumeration E3).
Consequence: C catches the mid-plan `OllamaError` too, journals it as
`unavailable`, and answers the same named 503 (R16 holds by construction).

### R-08 — the writing route's commit discipline [M]
Opened: `tooling/verify/checks/lore_write.py:606-619` (E2 implementation:
the route file contains no `select(`/`chat(` substring, and its `.commit(`
calls all sit in `write_commit`, exactly one).
Finding: a second `.commit(` anywhere in the route file fails E2.
Consequence: the routes never commit a journal row themselves: the
recorder's `record` commits (C-04); `write_commit` keeps its one commit,
which also carries the `ok` journal row (`stage`).

### R-09 — `apply_proposal` annotates its input [M]
Opened: `src/world_engine/lore_write_apply.py:72-93`
(`_validate_entities`: `item["_type"] = …` at 84 and 89).
Finding: the proposal dict the route passes is mutated during validation.
Consequence: `write_commit` deep-copies the proposal before applying it and
journals the copy (found by the prototype's U8c).

### R-11 — JSON columns and `json.loads` are gated [M]
Opened: `tooling/verify/checks/json_ui_boundary.py:43-102` (volet c: every
`Column(JSON` is a named allow-list entry), `tooling/verify/checks/
llm_parse_chokepoint.py:3-16` (a `json.loads` site in `src/` must be the
chokepoint or allow-listed).
Finding: both gates are fail-closed on a new site.
Consequence: A allow-lists `LoreUsageEvent.payload` and `.model_calls` with
their reason; the recorder copies payloads with
`fastapi.encoders.jsonable_encoder` (no `json.loads`; `fastapi` is already
imported outside `cockpit/`, enumeration E11).

### R-13 — sessions and transactions [M]
Opened: `src/world_engine/db.py:89-147` (WAL, explicit BEGIN), `:157-161`
(`get_session`); `src/world_engine/cockpit/routes/day.py:613-621` (X1b:
rollback, write the record, commit, on the refused path).
Finding: one request-scoped session; the X1b precedent journals a refusal
after a rollback, on the same session.
Consequence: `record` commits on the request session (a draft or a
consultation has nothing else staged); a refused commit rolls back first.

### R-16 — checks that call the Lore routes [M]
Opened: enumeration E8; `tooling/verify/checks/lore_write.py:530-603`,
`origin_guard.py`.
Finding: `lore_write.py` posts to the writing routes and `origin_guard.py`
posts through the guard; neither counts a table the journal touches.
Consequence: both stay green unchanged except for E1b's wording (C);
their journal rows land in their own temp databases.

## Contracts

### C-01 — `writes/lore_usage.write_usage_event` (consumed through C-04)
Signature: `write_usage_event(db, *, attempt_id, world_ref, world_name,
kind, step, outcome, payload, model_calls, lore_entry_ref=None)`; adds the
row, never commits; `ValueError` on any shape the table refuses (BRIEF-0103-A).

### C-02 — `PAYLOAD_KEYS` (consumed)
- `questions`: `statement, questions, error`
- `draft`: `statement, answers, draft, error`
- `commit`: `proposal, result, error`
- `ask`: `question, response, error`
- `resolve`: `question, plan, bindings, response, error`
`error` is None on `ok` and the message the creator was shown otherwise;
the answer key is None when the step did not answer.

### C-03 — the capturing call sites (consumed)
`draft_plan(question, world_id, db, exchanges=None)`; `render(result,
question, spec, candidates, exchanges=None)`; `draft_questions(db,
world_id, statement, exchanges=None)`; `draft_proposal(db, world_id,
statement, answers="", exchanges=None)`; `model_exchange.fail(exchanges,
exc)` records an error on the last exchange without one.

### C-04 — the recorder `lore_usage`
Produced by: BRIEF-0103-C   Consumed by: the two Lore route modules
`attempt_id(raw) -> str` (canonical UUID, or a fresh `uuid4` for None, ''
or malformed); `stage(db, *, attempt, world_id, kind, step, outcome,
payload, exchanges=None, lore_entry_ref=None)` (reads the world's name now;
`WORLD_NAME_UNKNOWN = "(monde introuvable)"` when the id matches no world;
payload and model calls copied through `jsonable_encoder`; never commits);
`record(db, **same)` = `stage` + `db.commit()`.

### C-05 — what each route journals
Produced by: BRIEF-0103-C   Consumed by: D, E, the analysis
Family (five routes; written before any member, re-read after the fifth).
Only requests that reach the model or the apply step are journaled.
- `POST /api/lore/write/questions` → `write/questions`: `ok` (questions),
  `unavailable` (503, `WRITE_UNAVAILABLE_MESSAGE`), `parse_error` (502).
  `record`.
- `POST /api/lore/write/draft` → `write/draft`: `ok` (the draft as
  returned), `unavailable`, `parse_error`. `record`.
- `POST /api/lore/write/commit` → `write/commit`: `ok` staged in the
  commit's transaction with `lore_entry_ref`; `refused` (422
  `ProposalError`, or an `HTTPException` from the entity creator) recorded
  after the rollback. The proposal as received (deep copy, R-09).
- `POST /api/lore/ask` → `consult/ask`: `unavailable` (ping down, or an
  `OllamaError` from the plan's call, 503 `PLANNER_UNAVAILABLE_MESSAGE`),
  `parse_error` (502), `ok` (the response body as returned, exchanges
  `[plan, prose?]`). `record`.
- `POST /api/lore/resolve` → `consult/resolve`: `refused` (422 malformed
  plan or binding), `ok` (response body, exchanges `[prose?]`). `record`.
Response bodies are unchanged.

### C-06 — the attempt id on the wire (server half)
Every request body of the five routes accepts an optional `attempt_id`
(`Optional[str] = None`), normalized by `lore_usage.attempt_id`.

## Context

The routes now hand a list to the model calls (B) and journal each step through one recorder (A's writer underneath). Requests refused before reaching the model or the apply step — no active world, an empty text, a non-local origin — are not journaled. Response bodies do not change; the panels start sending their attempt id in D.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`)
are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It: creates `src/world_engine/lore_usage.py` (C-04); in `cockpit/routes/lore_write.py`, adds `attempt_id` to both bodies, journals `questions` and `draft` (C-05) through `_journal_failure` / `_usage.record`, deep-copies the proposal before `apply_proposal`, journals a refused commit after its rollback (`_refuse_commit`) and stages the `ok` row before the route's one `db.commit()`, and narrows the docstring to « no canon row »; in `cockpit/routes/lore.py`, adds `attempt_id` to both bodies, threads an `exchanges` list through `draft_plan` and `_result_body` → `render`, catches an `OllamaError` from `draft_plan` with the named 503, journals every outcome through `_journal`, and moves the resolve validation into `_validated_plan` so a refusal is journaled; replaces the `"lore_rows_to_prose"` literal by `_lore_render.PROSE_USAGE`; in the check `tooling/verify/checks/lore_write.py`, narrows E1b's wording and the PASS line to « write canon only on commit »; extends the check `tooling/verify/checks/lore_usage.py` with U7-U10 and adds the recorder `lore_usage.py` to its `_WRITER_CALLERS`; appends the decision entry.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(lore): journal every Lore writing and consultation step under its attempt (BRIEF-0103-c)`.

````diff
diff --git a/src/world_engine/cockpit/routes/lore.py b/src/world_engine/cockpit/routes/lore.py
index c1e9b1f..1b5f010 100644
--- a/src/world_engine/cockpit/routes/lore.py
+++ b/src/world_engine/cockpit/routes/lore.py
@@ -10,10 +10,17 @@ resolve` takes that same plan back from the client together with creator
 bindings for any ambiguous mention, re-validates each binding, and executes
 -- it never calls `draft_plan` again, so disambiguation cannot shift the
 question.
+
+Every step that reaches the model is journaled through `lore_usage`
+(TICKET-0103, BRIEF-0103-C, decision A2), under the panel's `attempt_id`:
+the question, the response as sent, and the model exchanges it took. A
+journal row is the only write either route makes.
 """
 
 from __future__ import annotations
 
+from typing import Optional
+
 from fastapi import APIRouter, Depends, HTTPException
 from pydantic import BaseModel
 from sqlmodel import Session
@@ -23,7 +30,8 @@ from ... import lore_plan as _lore_plan
 from ... import lore_prompt as _lore_prompt
 from ... import lore_render as _lore_render
 from ... import lore_resolve as _lore_resolve
-from ... import ollama_client
+from ... import lore_usage as _usage
+from ... import model_exchange, ollama_client
 from ...db import get_session
 from ...llm_parse import LlmParseError
 from ...lore_query import LorePlan, PlanCall, PlanMention, execute_plan
@@ -34,6 +42,7 @@ router = APIRouter()
 class LoreAskBody(BaseModel):
     question: str
     world_id: str
+    attempt_id: Optional[str] = None
 
 
 class LoreResolveBody(BaseModel):
@@ -46,6 +55,7 @@ class LoreResolveBody(BaseModel):
     # verdict needs the original question text for the model prompt --
     # nothing server-side remembers it between /ask and /resolve.
     question: str
+    attempt_id: Optional[str] = None
 
 
 def _serialize_plan(plan: LorePlan) -> dict:
@@ -73,15 +83,15 @@ def _deserialize_plan(raw: dict) -> LorePlan:
     return LorePlan(mentions=mentions, calls=calls)
 
 
-def _result_body(plan: LorePlan, result, question: str, db: Session) -> dict:
+def _result_body(plan: LorePlan, result, question: str, db: Session, exchanges: list) -> dict:
     candidates: dict[str, list[dict]] = {}
     if result.verdict == "ambiguous_mention":
         candidates = {
             am["ref"]: _lore_candidates.describe_candidates(am["candidate_ids"], db)
             for am in result.ambiguous_mentions
         }
-    spec = _lore_prompt.load(db, "lore_rows_to_prose")
-    rendered = _lore_render.render(result, question, spec, candidates)
+    spec = _lore_prompt.load(db, _lore_render.PROSE_USAGE)
+    rendered = _lore_render.render(result, question, spec, candidates, exchanges)
     return {
         "verdict": result.verdict,
         "rows": list(result.rows),
@@ -94,26 +104,49 @@ def _result_body(plan: LorePlan, result, question: str, db: Session) -> dict:
     }
 
 
+def _journal(db: Session, attempt: str, world_id: str, step: str, outcome: str,
+             payload: dict, exchanges: list) -> None:
+    _usage.record(db, attempt=attempt, world_id=world_id, kind="consult", step=step,
+                  outcome=outcome, payload=payload, exchanges=exchanges)
+
+
 @router.post("/api/lore/ask")
 def ask_lore(body: LoreAskBody, db: Session = Depends(get_session)) -> dict:
+    attempt = _usage.attempt_id(body.attempt_id)
+    payload = {"question": body.question, "response": None}
+    exchanges: list = []
     try:
         ollama_client.ping()
     except ollama_client.OllamaError as exc:
+        _journal(db, attempt, body.world_id, "ask", "unavailable",
+                 dict(payload, error=_lore_render.PLANNER_UNAVAILABLE_MESSAGE), exchanges)
         raise HTTPException(
             status_code=503, detail=_lore_render.PLANNER_UNAVAILABLE_MESSAGE
         ) from exc
 
     try:
-        plan = _lore_plan.draft_plan(body.question, body.world_id, db)
+        plan = _lore_plan.draft_plan(body.question, body.world_id, db, exchanges)
+    except ollama_client.OllamaError as exc:
+        model_exchange.fail(exchanges, exc)
+        _journal(db, attempt, body.world_id, "ask", "unavailable",
+                 dict(payload, error=_lore_render.PLANNER_UNAVAILABLE_MESSAGE), exchanges)
+        raise HTTPException(
+            status_code=503, detail=_lore_render.PLANNER_UNAVAILABLE_MESSAGE
+        ) from exc
     except LlmParseError as exc:
-        raise HTTPException(status_code=502, detail=f"lore plan drafting failed: {exc}") from exc
+        model_exchange.fail(exchanges, exc)
+        detail = f"lore plan drafting failed: {exc}"
+        _journal(db, attempt, body.world_id, "ask", "parse_error", dict(payload, error=detail), exchanges)
+        raise HTTPException(status_code=502, detail=detail) from exc
 
     result = execute_plan(plan, body.world_id, db)
-    return _result_body(plan, result, body.question, db)
+    response = _result_body(plan, result, body.question, db, exchanges)
+    _journal(db, attempt, body.world_id, "ask", "ok", dict(payload, response=response, error=None),
+             exchanges)
+    return response
 
 
-@router.post("/api/lore/resolve")
-def resolve_lore(body: LoreResolveBody, db: Session = Depends(get_session)) -> dict:
+def _validated_plan(body: LoreResolveBody, db: Session) -> LorePlan:
     plan = _deserialize_plan(body.plan)
 
     mention_by_ref = {m.ref: m for m in plan.mentions}
@@ -129,6 +162,23 @@ def resolve_lore(body: LoreResolveBody, db: Session = Depends(get_session)) -> d
                     f"{mention.category} entity in this world"
                 ),
             )
+    return plan
+
+
+@router.post("/api/lore/resolve")
+def resolve_lore(body: LoreResolveBody, db: Session = Depends(get_session)) -> dict:
+    attempt = _usage.attempt_id(body.attempt_id)
+    payload = {"question": body.question, "plan": body.plan, "bindings": body.bindings,
+               "response": None}
+    try:
+        plan = _validated_plan(body, db)
+    except HTTPException as exc:
+        _journal(db, attempt, body.world_id, "resolve", "refused", dict(payload, error=str(exc.detail)), [])
+        raise
 
+    exchanges: list = []
     result = execute_plan(plan, body.world_id, db, bindings=body.bindings)
-    return _result_body(plan, result, body.question, db)
+    response = _result_body(plan, result, body.question, db, exchanges)
+    _journal(db, attempt, body.world_id, "resolve", "ok", dict(payload, response=response, error=None),
+             exchanges)
+    return response
diff --git a/src/world_engine/cockpit/routes/lore_write.py b/src/world_engine/cockpit/routes/lore_write.py
index d4babbb..76f2b35 100644
--- a/src/world_engine/cockpit/routes/lore_write.py
+++ b/src/world_engine/cockpit/routes/lore_write.py
@@ -12,11 +12,17 @@ untouched: this module imports none of `lore_selectors`, `lore_query`,
 POST passes the origin guard first (BRIEF-0098-A).
 
 Ollama down answers 503 with `lore_write_draft.WRITE_UNAVAILABLE_MESSAGE`
-(K1); nothing is written by a draft route, ever.
+(K1); no canon row is written by a draft route, ever.
+
+Every step that reaches the model or the apply step is journaled through
+`lore_usage` (TICKET-0103, BRIEF-0103-C), under the panel's `attempt_id`:
+a draft step in its own transaction (`record`), a successful commit in the
+commit's own transaction (`stage`), a refused commit after its rollback.
 """
 
 from __future__ import annotations
 
+import copy
 from typing import Any, Optional
 
 from fastapi import APIRouter, Depends, HTTPException
@@ -24,9 +30,11 @@ from pydantic import BaseModel
 from sqlmodel import Session
 
 from ... import lore_mentions_read as _world
+from ... import lore_usage as _usage
 from ... import lore_write_apply as _apply
 from ... import lore_write_draft as _draft
 from ... import lore_write_read as _read
+from ... import model_exchange
 from ...db import get_session
 from ...llm_parse import LlmParseError
 from ...ollama_client import OllamaError
@@ -38,10 +46,12 @@ router = APIRouter()
 class StatementBody(BaseModel):
     statement: str
     answers: Optional[str] = None
+    attempt_id: Optional[str] = None
 
 
 class CommitBody(BaseModel):
     proposal: dict[str, Any]
+    attempt_id: Optional[str] = None
 
 
 def _world_id(db: Session) -> str:
@@ -57,27 +67,58 @@ def _statement(body: StatementBody) -> str:
     return body.statement
 
 
+def _journal_failure(db: Session, attempt: str, world_id: str, step: str, outcome: str,
+                     payload: dict, exchanges: list, exc: Exception, detail: str) -> None:
+    model_exchange.fail(exchanges, exc)
+    _usage.record(db, attempt=attempt, world_id=world_id, kind="write", step=step,
+                  outcome=outcome, payload=dict(payload, error=detail), exchanges=exchanges)
+
+
 @router.post("/api/lore/write/questions")
 def write_questions(body: StatementBody, db: Session = Depends(get_session)) -> dict:
     world_id = _world_id(db)
+    statement = _statement(body)
+    attempt = _usage.attempt_id(body.attempt_id)
+    payload = {"statement": statement, "questions": None}
+    exchanges: list = []
     try:
-        questions = _draft.draft_questions(db, world_id, _statement(body))
+        questions = _draft.draft_questions(db, world_id, statement, exchanges)
     except OllamaError as exc:
+        _journal_failure(db, attempt, world_id, "questions", "unavailable", payload, exchanges,
+                         exc, _draft.WRITE_UNAVAILABLE_MESSAGE)
         raise HTTPException(status_code=503, detail=_draft.WRITE_UNAVAILABLE_MESSAGE) from exc
     except LlmParseError as exc:
-        raise HTTPException(status_code=502, detail=f"lore questions drafting failed: {exc}") from exc
+        detail = f"lore questions drafting failed: {exc}"
+        _journal_failure(db, attempt, world_id, "questions", "parse_error", payload, exchanges,
+                         exc, detail)
+        raise HTTPException(status_code=502, detail=detail) from exc
+    _usage.record(db, attempt=attempt, world_id=world_id, kind="write", step="questions",
+                  outcome="ok", payload=dict(payload, questions=questions, error=None),
+                  exchanges=exchanges)
     return {"questions": questions}
 
 
 @router.post("/api/lore/write/draft")
 def write_draft(body: StatementBody, db: Session = Depends(get_session)) -> dict:
     world_id = _world_id(db)
+    statement = _statement(body)
+    attempt = _usage.attempt_id(body.attempt_id)
+    payload = {"statement": statement, "answers": body.answers or None, "draft": None}
+    exchanges: list = []
     try:
-        return _draft.draft_proposal(db, world_id, _statement(body), body.answers or "")
+        draft = _draft.draft_proposal(db, world_id, statement, body.answers or "", exchanges)
     except OllamaError as exc:
+        _journal_failure(db, attempt, world_id, "draft", "unavailable", payload, exchanges,
+                         exc, _draft.WRITE_UNAVAILABLE_MESSAGE)
         raise HTTPException(status_code=503, detail=_draft.WRITE_UNAVAILABLE_MESSAGE) from exc
     except LlmParseError as exc:
-        raise HTTPException(status_code=502, detail=f"lore proposal drafting failed: {exc}") from exc
+        detail = f"lore proposal drafting failed: {exc}"
+        _journal_failure(db, attempt, world_id, "draft", "parse_error", payload, exchanges,
+                         exc, detail)
+        raise HTTPException(status_code=502, detail=detail) from exc
+    _usage.record(db, attempt=attempt, world_id=world_id, kind="write", step="draft",
+                  outcome="ok", payload=dict(payload, draft=draft, error=None), exchanges=exchanges)
+    return draft
 
 
 def _entity_creator(db: Session):
@@ -90,20 +131,33 @@ def _entity_creator(db: Session):
     return create
 
 
+def _refuse_commit(db: Session, attempt: str, world_id: str, proposal: dict, detail: str) -> None:
+    db.rollback()
+    _usage.record(db, attempt=attempt, world_id=world_id, kind="write", step="commit",
+                  outcome="refused", payload={"proposal": proposal, "result": None, "error": detail})
+
+
 @router.post("/api/lore/write/commit")
 def write_commit(body: CommitBody, db: Session = Depends(get_session)) -> dict:
     world_id = _world_id(db)
+    attempt = _usage.attempt_id(body.attempt_id)
+    # `apply_proposal` annotates the dict it validates (`_type` on each
+    # entity); the journal keeps the proposal as the panel sent it.
+    received = copy.deepcopy(body.proposal)
     try:
         result = _apply.apply_proposal(db, world_id, body.proposal, _entity_creator(db))
     except _apply.ProposalError as exc:
-        db.rollback()
+        _refuse_commit(db, attempt, world_id, received, str(exc))
         raise HTTPException(status_code=422, detail=str(exc)) from exc
-    except HTTPException:
-        db.rollback()
+    except HTTPException as exc:
+        _refuse_commit(db, attempt, world_id, received, str(exc.detail))
         raise
+    answer = {"entry_id": result.entry_id, "written": result.written, "skipped": result.skipped}
+    _usage.stage(db, attempt=attempt, world_id=world_id, kind="write", step="commit",
+                 outcome="ok", payload={"proposal": received, "result": answer, "error": None},
+                 lore_entry_ref=result.entry_id)
     db.commit()
-    return {"ok": True, "entry_id": result.entry_id, "written": result.written,
-            "skipped": result.skipped}
+    return {"ok": True, **answer}
 
 
 @router.get("/api/lore/write/entries")
diff --git a/src/world_engine/lore_usage.py b/src/world_engine/lore_usage.py
new file mode 100644
index 0000000..20ffc6a
--- /dev/null
+++ b/src/world_engine/lore_usage.py
@@ -0,0 +1,71 @@
+"""The Lore shell's usage recorder (TICKET-0103, BRIEF-0103-C, C-04).
+
+The routes of the Lore shell -- consultation (`cockpit/routes/lore.py`) and
+writing (`cockpit/routes/lore_write.py`) -- record each step they serve
+here, once the request has reached the model or the apply step: what the
+step received and answered (`writes/lore_usage.PAYLOAD_KEYS`) and the model
+exchanges it captured (`model_exchange.ModelExchange`). Requests refused
+before that point (no active world, an empty text, a non-local origin) are
+not recorded.
+
+`stage` adds the row to the caller's transaction (a successful commit
+journals atomically with the canon it wrote); `record` stages and commits,
+for a route that has nothing else to commit -- a draft, a question, a
+consultation, or a refusal after its rollback. Nothing here reads the
+journal back, calls a model, or imports the consultation pipeline or the
+writing panel (`lore_usage.py` U10).
+"""
+
+from __future__ import annotations
+
+import uuid
+from typing import Any, Optional
+
+from fastapi.encoders import jsonable_encoder
+from sqlmodel import Session
+
+from .model_exchange import ModelExchange
+from .models import World
+from .writes.lore_usage import write_usage_event
+
+WORLD_NAME_UNKNOWN = "(monde introuvable)"
+
+
+def attempt_id(raw: Optional[str]) -> str:
+    """The panel's attempt id in canonical form when it is a UUID; a fresh
+    one otherwise (absent, empty or malformed) -- a journal id never fails
+    the creator's request."""
+    try:
+        return str(uuid.UUID(str(raw)))
+    except (ValueError, TypeError, AttributeError):
+        return str(uuid.uuid4())
+
+
+def _plain(value: Any) -> Any:
+    """A JSON-native copy of `value` (a date becomes ISO text), detached from
+    any dict the caller may still change -- the encoding FastAPI applies to
+    the response itself."""
+    return jsonable_encoder(value)
+
+
+def stage(
+    db: Session, *, attempt: str, world_id: str, kind: str, step: str, outcome: str,
+    payload: dict, exchanges: Optional[list[ModelExchange]] = None,
+    lore_entry_ref: Optional[str] = None,
+) -> None:
+    """Add one journal row to `db`'s transaction; never commits. The world's
+    name is read now, so the row stays readable after the world is gone."""
+    world = db.get(World, world_id) if world_id else None
+    write_usage_event(
+        db, attempt_id=attempt, world_ref=world_id or WORLD_NAME_UNKNOWN,
+        world_name=world.name if world is not None else WORLD_NAME_UNKNOWN,
+        kind=kind, step=step, outcome=outcome, payload=_plain(payload),
+        model_calls=[_plain(e.to_record()) for e in exchanges or []],
+        lore_entry_ref=lore_entry_ref,
+    )
+
+
+def record(db: Session, **row: Any) -> None:
+    """`stage`, then commit: for a step whose session holds nothing else."""
+    stage(db, **row)
+    db.commit()
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 8b7710f..c5eb2e9 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17647,6 +17647,23 @@ fallback. `prompt_load.RenderSpec` gains `version_id` and `version_number`,
 plain values, so the Session-free renderer names the version without a row.
 Without a list every call behaves as before.
 
+
+## EVERY LORE STEP IS JOURNALED UNDER ITS ATTEMPT (TICKET-0103) -- FAILURES INCLUDED (BRIEF-0103-c, no schema change)
+
+**A2, C1.** `lore_usage.py` is the routes' recorder: `attempt_id` keeps the
+panel's UUID or mints one (a journal id never fails a request), `stage` adds
+a row to the caller's transaction and `record` stages and commits. The five
+Lore routes journal every step that reaches the model or the apply step:
+`questions`, `draft`, `ask` in their own transaction (`ok`, `unavailable`,
+`parse_error`, each with its model exchanges); `commit` atomically with the
+canon it wrote, or after its rollback when refused; `resolve` likewise.
+Requests refused before that point (no active world, empty text, non-local
+origin) are not journaled. The committed proposal is journaled as the panel
+sent it: `apply_proposal` annotates the dict it validates, so the route
+copies it first. `ask` now answers an `OllamaError` raised while drafting
+the plan with the named 503 message, as it already did for a failed ping,
+instead of an unhandled 500 -- the step must be caught to be journaled.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/lore_usage.py b/tooling/verify/checks/lore_usage.py
index 34890d7..4621a2c 100644
--- a/tooling/verify/checks/lore_usage.py
+++ b/tooling/verify/checks/lore_usage.py
@@ -47,6 +47,37 @@ U6 -- capture (C-03), `chat` stubbed in each module, on seeded prompt heads:
    c. `lore_write_draft.draft_questions` and `draft_proposal` each append one
       exchange, usage `QUESTIONS_USAGE` and `PROPOSAL_USAGE`;
    d. every exchange's `to_record()` is accepted by `write_usage_event`.
+U7 -- the recorder (BRIEF-0103-C, C-04). `lore_usage.attempt_id` keeps a
+   UUID in canonical form and mints a fresh, distinct one for None, '' and a
+   malformed id; `record` writes one row carrying the world's name and
+   commits it; a world id matching no world is journaled as
+   `WORLD_NAME_UNKNOWN`.
+U8 -- the writing routes (C-05), `TestClient` on the active fixture world,
+   `lore_write_draft.chat` stubbed, one attempt id:
+   a. questions answered -> one `questions/ok` row, its questions as
+      answered, one model call; Ollama down -> `questions/unavailable`, error
+      `WRITE_UNAVAILABLE_MESSAGE`, its model call carrying the error;
+   b. draft answered -> one `draft/ok` row whose `draft` equals the response
+      body; an unparsable reply -> 502 and one `draft/parse_error` row whose
+      model call keeps the raw reply;
+   c. a valid commit -> one `commit/ok` row, `lore_entry_ref` the response's
+      `entry_id`, its proposal as sent; an invalid commit -> 422, one
+      `commit/refused` row with the response's detail, no canon row written;
+   d. every row carries the attempt id and the world's name; a request with
+      no attempt id is journaled under a fresh one.
+U9 -- the consultation routes (C-05), same client, `lore_plan.chat`,
+   `lore_render.chat` and `ollama_client.ping` stubbed:
+   a. ping down -> 503 and one `ask/unavailable` row with no model call;
+   b. an answered question -> one `ask/ok` row whose `response` equals the
+      response body, model calls `[PLAN_USAGE, PROSE_USAGE]`;
+   c. an unparsable plan -> 502 and one `ask/parse_error` row keeping the raw
+      reply; Ollama failing mid-plan -> 503, one `ask/unavailable` row;
+   d. a binding to an unknown ref -> 422 and one `resolve/refused` row; a
+      valid resolve -> one `resolve/ok` row under the same attempt.
+U10 -- structure. Neither route file calls `write_usage_event` (they go
+   through `lore_usage`); `lore_usage.py` contains no `chat(` and no
+   `select(`, and imports no consultation-pipeline and no writing-panel
+   module.
 
 Fresh temp-file SQLite database for any fixture rule
 (`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) -- never
@@ -71,7 +102,11 @@ FAILURES: list[str] = []
 _NAMING_FILES: frozenset[str] = frozenset({
     "models/pipeline.py", "models/__init__.py", "writes/lore_usage.py",
 })
-_WRITER_CALLERS: frozenset[str] = frozenset({"writes/lore_usage.py"})
+_WRITER_CALLERS: frozenset[str] = frozenset({"writes/lore_usage.py", "lore_usage.py"})
+_ROUTES = ("cockpit/routes/lore.py", "cockpit/routes/lore_write.py")
+_PIPELINE = {"lore_selectors", "lore_query", "lore_plan", "lore_render", "lore_prompt"}
+_PANEL = {"lore_write_apply", "lore_write_draft", "lore_write_read", "lore_mentions_read",
+          "lore_choices_read"}
 _NOT_NULL = ("attempt_id", "world_ref", "world_name", "kind", "step", "outcome",
              "payload", "model_calls")
 
@@ -498,6 +533,243 @@ def check_u6() -> None:
             fail(f"U6d: the writer refused captured exchanges: {exc}")
 
 
+def _events(db, attempt: str) -> list:
+    from sqlmodel import select
+
+    from world_engine.models import LoreUsageEvent
+
+    return list(db.exec(select(LoreUsageEvent).where(LoreUsageEvent.attempt_id == attempt)
+                        .order_by(LoreUsageEvent.created_at, LoreUsageEvent.id)).all())
+
+
+def check_u7() -> None:
+    import uuid
+
+    from sqlmodel import Session
+
+    from world_engine import lore_usage
+    from world_engine.db import engine
+    from world_engine.models import World
+
+    raw = "A0B1C2D3-0000-4000-8000-000000000001"
+    if lore_usage.attempt_id(raw) != raw.lower():
+        fail("U7: a UUID attempt id is not kept in canonical form")
+    minted = [lore_usage.attempt_id(v) for v in (None, "", "pas-un-uuid")]
+    if len(set(minted)) != 3 or any(str(uuid.UUID(m)) != m for m in minted):
+        fail(f"U7: minted ids {minted}")
+    with Session(engine) as db:
+        world = World(name="Recorder 0103")
+        db.add(world)
+        db.commit()
+        payload = {"question": "q", "response": None, "error": "x"}
+        lore_usage.record(db, attempt="att-u7", world_id=world.id, kind="consult", step="ask",
+                          outcome="unavailable", payload=payload)
+        lore_usage.record(db, attempt="att-u7", world_id="no-such-world", kind="consult",
+                          step="ask", outcome="unavailable", payload=payload)
+    with Session(engine) as db:
+        names = [e.world_name for e in _events(db, "att-u7")]
+        if names != ["Recorder 0103", lore_usage.WORLD_NAME_UNKNOWN]:
+            fail(f"U7: recorded world names {names}")
+
+
+def _route_world(db) -> dict:
+    from sqlmodel import select
+
+    from world_engine.models import Entity, Faction, World
+
+    world = World(name="Routes 0103")
+    db.add(world)
+    db.flush()
+    faction = Entity(world_id=world.id, type="faction", name="Guilde des Passeurs")
+    db.add(faction)
+    db.flush()
+    db.add(Faction(id=faction.id))
+    for other in db.exec(select(World)).all():
+        other.is_active = False
+        db.add(other)
+    db.flush()
+    world.is_active = True
+    db.add(world)
+    db.commit()
+    return {"world": world.id, "faction": faction.id}
+
+
+def _canon_counts(db) -> dict:
+    from sqlalchemy import text
+
+    tables = ("entity", "fact", "knowledge", "lore_entry", "lore_entry_row")
+    return {t: db.exec(text(f"SELECT COUNT(*) FROM {t}")).one()[0] for t in tables}
+
+
+def _one(db, attempt: str, step: str, outcome: str, label: str):
+    rows = [e for e in _events(db, attempt) if (e.step, e.outcome) == (step, outcome)]
+    if len(rows) != 1:
+        fail(f"{label}: {len(rows)} {step}/{outcome} row(s) under {attempt}")
+        return None
+    return rows[0]
+
+
+def check_u8() -> None:
+    from fastapi.testclient import TestClient
+    from sqlmodel import Session
+
+    from world_engine import lore_write_draft as lwd
+    from world_engine.cockpit.app import app
+    from world_engine.db import engine
+    from world_engine.ollama_client import OllamaError
+
+    with Session(engine) as db:
+        _seed_prompts(db)
+        ids = _route_world(db)
+    client = TestClient(app, base_url="http://127.0.0.1")
+    attempt = "0b0b0b0b-0000-4000-8000-000000000008"
+    body = {"statement": "La Guilde des Passeurs garde le port.", "attempt_id": attempt}
+    original = _swap(lwd, _Stub([{"questions": ["Qui le sait ?"]}, OllamaError("down"),
+                                 {"entities": [], "facts": [], "memberships": [], "controls": []},
+                                 "pas du json"]))
+    try:
+        ok_q = client.post("/api/lore/write/questions", json=body)
+        down = client.post("/api/lore/write/questions", json=body)
+        draft = client.post("/api/lore/write/draft", json=dict(body, answers="Tout le monde."))
+        broken = client.post("/api/lore/write/draft", json=body)
+    finally:
+        lwd.chat = original
+    if (ok_q.status_code, down.status_code, draft.status_code, broken.status_code) != (200, 503, 200, 502):
+        fail(f"U8: statuses {ok_q.status_code} {down.status_code} {draft.status_code} {broken.status_code}")
+        return
+    proposal = {"statement": body["statement"], "entities": [
+        {"ref": "e1", "action": "existing", "entity_id": ids["faction"]}], "facts": [
+        {"ref": "f1", "action": "create", "facet": "information", "content": "Le port ferme la nuit.",
+         "participants": ["e1"], "defaults": [{"scope_type": "world"}], "knowers": []}]}
+    with Session(engine) as db:
+        before = _canon_counts(db)
+    bad = dict(proposal, facts=[dict(proposal["facts"][0], facet="lien")])
+    refused = client.post("/api/lore/write/commit", json={"proposal": bad, "attempt_id": attempt})
+    with Session(engine) as db:
+        if refused.status_code != 422 or _canon_counts(db) != before:
+            fail(f"U8c: an invalid commit answered {refused.status_code} or wrote canon")
+    done = client.post("/api/lore/write/commit", json={"proposal": proposal, "attempt_id": attempt})
+    anonymous = client.post("/api/lore/write/commit", json={"proposal": bad})
+    with Session(engine) as db:
+        row = _one(db, attempt, "questions", "ok", "U8a")
+        if row and (row.payload["questions"] != ["Qui le sait ?"] or len(row.model_calls) != 1):
+            fail(f"U8a: questions row {row.payload} / {len(row.model_calls)} call(s)")
+        row = _one(db, attempt, "questions", "unavailable", "U8a")
+        if row and (row.payload["error"] != lwd.WRITE_UNAVAILABLE_MESSAGE
+                    or not (row.model_calls[0]["error"] or "").startswith("OllamaError")):
+            fail("U8a: the unavailable row lacks its message or its model call's error")
+        row = _one(db, attempt, "draft", "ok", "U8b")
+        if row and row.payload["draft"] != draft.json():
+            fail("U8b: the draft row is not the response body")
+        row = _one(db, attempt, "draft", "parse_error", "U8b")
+        if row and row.model_calls[0]["raw_output"] != "pas du json":
+            fail("U8b: the parse_error row lost the raw reply")
+        row = _one(db, attempt, "commit", "ok", "U8c")
+        if row and (done.status_code != 200 or row.lore_entry_ref != done.json().get("entry_id")
+                    or row.payload["proposal"] != proposal):
+            fail(f"U8c: commit answered {done.status_code}; row {row.lore_entry_ref} {row.payload}"[:300])
+        row = _one(db, attempt, "commit", "refused", "U8c")
+        if row and row.payload["error"] != refused.json().get("detail"):
+            fail("U8c: the refused row does not carry the response's detail")
+        rows = _events(db, attempt)
+        if len(rows) != 6 or {e.world_name for e in rows} != {"Routes 0103"} \
+                or {e.kind for e in rows} != {"write"}:
+            fail(f"U8d: {len(rows)} row(s) under the attempt, worlds {[e.world_name for e in rows]}")
+        from sqlmodel import select
+
+        from world_engine.models import LoreUsageEvent
+
+        strays = db.exec(select(LoreUsageEvent).where(
+            LoreUsageEvent.world_ref == ids["world"], LoreUsageEvent.attempt_id != attempt)).all()
+        if anonymous.status_code != 422 or len(strays) != 1:
+            fail(f"U8d: a request without attempt id left {len(strays)} row(s) under another id")
+
+
+def check_u9() -> None:
+    from fastapi.testclient import TestClient
+    from sqlmodel import Session
+
+    from world_engine import lore_plan, lore_render, ollama_client
+    from world_engine.cockpit.app import app
+    from world_engine.db import engine
+
+    with Session(engine) as db:
+        _seed_prompts(db)
+        ids = _route_world(db)
+    client = TestClient(app, base_url="http://127.0.0.1")
+    attempt = "0c0c0c0c-0000-4000-8000-000000000009"
+    body = {"question": "Quelles factions ?", "world_id": ids["world"], "attempt_id": attempt}
+    plan = {"mentions": [], "calls": [{"selector": "world_factions", "args": ["$world"]}]}
+    original_ping = ollama_client.ping
+
+    def down(*args, **kwargs):
+        raise ollama_client.OllamaError("down")
+
+    plan_original = _swap(lore_plan, _Stub([plan, "pas du json", ollama_client.OllamaError("down")]))
+    prose_original = _swap(lore_render, _Stub(["Une guilde garde le port.", "Toujours elle."]))
+    try:
+        ollama_client.ping = down
+        unavailable = client.post("/api/lore/ask", json=body)
+        ollama_client.ping = lambda *a, **k: []
+        answered = client.post("/api/lore/ask", json=body)
+        broken = client.post("/api/lore/ask", json=body)
+        mid = client.post("/api/lore/ask", json=body)
+        resolve = {"plan": answered.json().get("plan", plan), "world_id": ids["world"],
+                   "question": body["question"], "attempt_id": attempt}
+        refused = client.post("/api/lore/resolve", json=dict(resolve, bindings={"m9": ids["faction"]}))
+        resolved = client.post("/api/lore/resolve", json=dict(resolve, bindings={}))
+    finally:
+        ollama_client.ping = original_ping
+        lore_plan.chat = plan_original
+        lore_render.chat = prose_original
+    statuses = (unavailable.status_code, answered.status_code, broken.status_code, mid.status_code,
+                refused.status_code, resolved.status_code)
+    if statuses != (503, 200, 502, 503, 422, 200):
+        fail(f"U9: statuses {statuses}")
+        return
+    with Session(engine) as db:
+        rows = [e for e in _events(db, attempt) if (e.step, e.outcome) == ("ask", "unavailable")]
+        if len(rows) != 2 or rows[0].model_calls != [] or len(rows[1].model_calls) != 1:
+            fail(f"U9a/c: unavailable rows carry {[len(r.model_calls) for r in rows]} model call(s)")
+        row = _one(db, attempt, "ask", "ok", "U9b")
+        if row and (row.payload["response"] != answered.json()
+                    or [c["usage"] for c in row.model_calls] != [lore_plan.PLAN_USAGE, lore_render.PROSE_USAGE]):
+            fail(f"U9b: ask row usages {[c['usage'] for c in row.model_calls]}")
+        row = _one(db, attempt, "ask", "parse_error", "U9c")
+        if row and row.model_calls[0]["raw_output"] != "pas du json":
+            fail("U9c: the parse_error row lost the raw reply")
+        row = _one(db, attempt, "resolve", "refused", "U9d")
+        if row and row.payload["error"] != refused.json().get("detail"):
+            fail("U9d: the refused row does not carry the response's detail")
+        row = _one(db, attempt, "resolve", "ok", "U9d")
+        if row and (row.payload["response"] != resolved.json() or row.kind != "consult"):
+            fail("U9d: the resolve row is not the response body")
+
+
+def check_u10() -> None:
+    import ast
+
+    for rel in _ROUTES:
+        if "write_usage_event" in (SRC / rel).read_text(encoding="utf-8"):
+            fail(f"U10: {rel} calls write_usage_event directly")
+    text = (SRC / "lore_usage.py").read_text(encoding="utf-8")
+    for needle in ("chat(", "select("):
+        if needle in text:
+            fail(f"U10: lore_usage.py contains {needle!r}")
+    imported: set[str] = set()
+    for node in ast.walk(ast.parse(text)):
+        if isinstance(node, ast.ImportFrom):
+            imported.add((node.module or "").rsplit(".", 1)[-1])
+            imported.update(alias.name for alias in node.names)
+        elif isinstance(node, ast.Import):
+            imported.update(alias.name.rsplit(".", 1)[-1] for alias in node.names)
+    if not imported:
+        fail("U10: no import collected from lore_usage.py")
+    hits = imported & (_PIPELINE | _PANEL)
+    if hits:
+        fail(f"U10: lore_usage.py imports {sorted(hits)}")
+
+
 def main() -> int:
     tmp = tempfile.mkdtemp(prefix="lore_usage_")
     db_path = f"{tmp}/u.db"
@@ -511,6 +783,10 @@ def main() -> int:
     check_u4()
     check_u5()
     check_u6()
+    check_u7()
+    check_u8()
+    check_u9()
+    check_u10()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -518,7 +794,8 @@ def main() -> int:
     print("PASS: lore_usage -- the journal is named by its model and its writer only; "
           "v2.13 declares it without world_id or FK and migrates from v2.12 only; the "
           "writer refuses every malformed record; a journal row outlives its world; every "
-          "Lore model call can be captured with its prompt version and raw reply")
+          "Lore model call can be captured with its prompt version and raw reply; every "
+          "writing and consultation step is journaled under its attempt, failures included")
     return 0
 
 
diff --git a/tooling/verify/checks/lore_write.py b/tooling/verify/checks/lore_write.py
index 54c02b1..f929b8f 100644
--- a/tooling/verify/checks/lore_write.py
+++ b/tooling/verify/checks/lore_write.py
@@ -60,7 +60,9 @@ E1 -- routes (BRIEF-0098-E), through `TestClient(app, base_url=...)` on the
    a. `POST /api/lore/write/questions` answers the questions; with Ollama
       down it answers 503 with exactly `WRITE_UNAVAILABLE_MESSAGE`;
    b. `POST /api/lore/write/draft` answers the draft; with Ollama down, 503;
-      no draft request changes any row count;
+      no draft request changes any row count of `_COUNTED_TABLES` (the
+      usage journal, which every step now writes, is TICKET-0103's and is
+      held by `lore_usage.py` U8);
    c. `POST /api/lore/write/commit` of a valid proposal creating a
       character answers 200; the entity has its `character` row as an NPC;
       `GET /api/lore/write/entries` lists the entry first, with a label per
@@ -684,7 +686,7 @@ def main() -> int:
           "v2.11 declares the source record and migrates from v2.10 only; a proposal "
           "writes all or nothing, each row recorded, existing rows skipped; the draft "
           "names things by name and code only and resolves both in code; the routes are "
-          "thin, guarded, and write only on commit; the panel lives in the Lore shell's "
+          "thin, guarded, and write canon only on commit; the panel lives in the Lore shell's "
           "'Écrire' tab")
     return 0
 
````

## Scope OUT

- Frontend changes: the panels sending `attempt_id` (D). Until D, each request is journaled under its own minted id.
- Any change to a response body or status code, except the one in Scope IN: an `OllamaError` raised by `draft_plan` now answers the named 503 instead of an unhandled 500.
- Journaling requests refused before the model or the apply step (no world, empty text, non-local origin).
- Journaling `GET /api/lore/write/entries`, the names panel (`lore_mentions`), the choice review (`lore_choices`) or any route outside the five.
- Reading the journal anywhere in the application (E's export is its only reader).
- A second `.commit(` in either route file, or a direct `write_usage_event` call from a route.
- Every later brief of the lot: BRIEF-0103-D, E.

## Invariants to defend

**A lore statement commits whole or not at all, through `apply_proposal`:** the `ok` journal row joins that one transaction; a refusal rolls back the canon before its journal row is written, so no canon row survives a refused commit. **Every POST passes the origin guard first:** unchanged — a non-local request never reaches the routes, so it is never journaled. **The lore renderer receives rows, never a `Session`:** `render` gets a plain list. **Thin routes (R6):** no `chat(`/`select(` in either route file.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- `lore_isolation.py` (R6, R7, R16, R17) or `lore_write.py` (E1, E2, F1) fails after the commit.
- A refused commit leaves any canon or `lore_entry` row behind (U8c, E1c).
- The full corpus is not green after the commit, for a reason the diff does not explain.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- Any Starlette/httpx deprecation warning printed by a check.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `python tooling/verify/checks/lore_usage.py` → `PASS: lore_usage -- … every Lore model call can be captured with its prompt version and raw reply; every writing and consultation step is journaled under its attempt, failures included`.
- `lore_write.py` → `PASS … the routes are thin, guarded, and write canon only on commit; …`.
- `lore_isolation.py`, `llm_parse_chokepoint.py`, `single_canon_write.py`, `origin_guard.py`, `function_length.py`, `module_budget.py` → `PASS`.
- Mutation test: in `cockpit/routes/lore.py`, delete the line journaling `"parse_error"` in `ask_lore`; U9c fails; revert.
- Mutation test: in `cockpit/routes/lore_write.py`, journal `body.proposal` instead of `received` on the `ok` commit; U8c fails; revert.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 137/137.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `EVERY LORE STEP IS JOURNALED UNDER ITS ATTEMPT (TICKET-0103) -- FAILURES INCLUDED (BRIEF-0103-c, no schema change)` — in the diff. No schema change. CLAUDE.md's invariant arrives with the reader (E).
