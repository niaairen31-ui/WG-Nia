<!-- slug: interpreter-routes -->
# BRIEF 0112-D — "The interpreter's routes -- a proposal is journaled, picked, inserted or discarded; saving the offer marks it saved"

Lot: LOT-0112-condition-interpreter.md (authoritative on conflict)
Depends on: BRIEF-0112-B (C-07), BRIEF-0112-C (C-04)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0112-C's commit).

- `src/world_engine/cockpit/routes/quests.py:51` -> `class OfferStepBody(BaseModel):`
- `src/world_engine/cockpit/routes/quests.py:72` -> `class OfferBody(BaseModel):`
- `src/world_engine/cockpit/routes/quests.py:116` -> `def _save_offer(body: OfferBody, offer: Optional[QuestOffer], world_id: str, db: Session) -> dict:`
- `src/world_engine/cockpit/app.py:143` -> `app.include_router(_routes_quests.router)`
- `src/world_engine/condition_interpreter.py:441` -> `def interpret(`
- `src/world_engine/condition_interpreter.py:466` -> `def resolve(db: Session, world_id: str, pending: dict, mentions: list[dict], notes: list[str],`
- `src/world_engine/writes/condition_drafts.py:100` -> `def mark_draft_saved(`
- `src/world_engine/quest_reads.py:61` -> `def condition_view(db: Session, tree) -> dict:`
- `src/world_engine/lore_usage.py:34` -> `def attempt_id(raw: Optional[str]) -> str:`
- No `src/world_engine/cockpit/routes/conditions.py` exists.

## Facts carried

### R-04 — one model exchange, and its failure [M]
Opened: `src/world_engine/model_exchange.py:25-37` (`ModelExchange`,
`to_record`), `:40-55` (`begin`: appends when the caller keeps a list),
`:58-64` (`fail`: records the error on the last exchange without one).
Consequence: the interpreter and its route keep exchanges the same way;
`fail` is the route's on `OllamaError` / `LlmParseError` (D).

### R-11 — the offer API and the editor [M]
Opened: `src/world_engine/cockpit/routes/quests.py:51-58` (`OfferStepBody`),
`:72-84` (`OfferBody`), `:116-137` (`_save_offer`: `node_from_dict` and
`write_quest_offer` inside one `try`, `ValueError` -> rollback and 422, then
`commit`); `src/world_engine/quest_reads.py:61-67` (`condition_view`: tree,
flat rows or None, French lines), `:98-101` (`world_offers`).
`frontend/src/creation/ConditionEditor.svelte:10` (props `cond, choices,
emptyLabel, addLabel`), its locked branch (lines, « Effacer »);
`frontend/src/creation/QuestOffers.svelte:137,160,162` (three
`ConditionEditor`s); `frontend/src/creation/questRequirements.js:32`
(`MONEY_KEY = 'monnaie'`), `:98-109` (`conditionDraft(view)`), `:111-113`
(`blankCondition`), `conditionBody` (locked tree, `all` of the rows, or
null); `frontend/src/creation/questOffers.svelte.js:118-131` (`draftBody`);
`frontend/src/creation/sheetRequest.svelte.js:30-35` (`api`: throws an
`Error` carrying `detail`).
Consequence: nothing new writes an offer; the proposal's view is
`condition_view`'s shape, so `conditionDraft(view)` inserts it; the save
carries one draft id per condition.

### R-12 — the Lore journal is closed by its CHECKs [M]
Opened: `src/world_engine/models/pipeline.py:363-421` (`lore_usage_event`:
`kind` / `step` CHECK on two kinds, outcome CHECK, `payload` JSON, no
`world_id`, `world_ref` + `world_name`); `src/world_engine/lore_usage.py:34-41`
(`attempt_id`: the panel's UUID in canonical form, or a fresh one -- « a
journal id never fails the creator's request »);
`scripts/migrate_v2_13_lore_usage.py` (refuse when behind, idempotent,
zero-row post-check, `schema_meta` converged).
Consequence: IH2 would rebuild a CHECKed table; B creates its own table on
the same posture and reuses `attempt_id` and the migration's shape.

### R-18 — routes are mounted by name, guarded globally [M]
Opened: `src/world_engine/cockpit/app.py:56-70` (route imports), `:125`
(`app.middleware("http")(origin_guard)`: every POST), `:126-144`
(`include_router`); `src/world_engine/cockpit/crud/_shared.py:57-61`
(`_world_id`: 400 when no world is active).
Consequence: D mounts one router; no per-route guard.

### R-19 — the model's failures [M]
Opened: `src/world_engine/ollama_client.py:39` (`OllamaError(RuntimeError)`);
`src/world_engine/llm_parse.py:21` (`LlmParseError(ValueError)`);
`src/world_engine/lore_write_draft.py:44-48` (`WRITE_UNAVAILABLE_MESSAGE`).
Consequence: the route catches both before anything else and journals
them; `LlmParseError` is a `ValueError`, so the route never wraps the
interpreter in a bare `except ValueError`.

### Case tables

b-4 -- `mark_draft_saved` (C-07, C-08).

| draft id         | draft's world | draft's outcome | result | row                                  |
|------------------|---------------|-----------------|--------|--------------------------------------|
| None / empty     | --            | --              | False  | unchanged                            |
| unknown          | --            | --              | False  | --                                   |
| known            | another       | any             | False  | unchanged                            |
| known            | this          | not `inserted`  | False  | unchanged                            |
| known            | this          | `inserted`      | True   | `saved`, `offer_ref`, `saved_as_proposed = (tree == payload.proposed)`, `decided_at` |

b-5 -- the routes' statuses (C-06).

| route     | case                                                         | status | journal                          |
|-----------|--------------------------------------------------------------|--------|----------------------------------|
| interpret | no active world                                              | 400    | none                             |
| interpret | empty sentence, unknown role, current tree that does not hold | 422    | none                             |
| interpret | `OllamaError`                                                | 503 `INTERPRET_UNAVAILABLE_MESSAGE` | `unavailable`, the call's error |
| interpret | `LlmParseError`                                              | 502 `PARSE_ERROR_MESSAGE` | `parse_error`, the raw reply  |
| interpret | otherwise                                                    | 200    | the b-1 outcome, `retried`        |
| resolve   | unknown draft or another world's                             | 404    | none                             |
| resolve   | draft not `needs_choice`                                     | 409    | unchanged                        |
| resolve   | a pick missing or outside its choices                        | 422    | unchanged                        |
| resolve   | otherwise                                                    | 200    | moved, payload with `bindings`    |
| decision  | unknown draft or another world's                             | 404    | none                             |
| decision  | decision not `inserted` / `discarded`                        | 422    | unchanged                        |
| decision  | move outside b-2                                             | 409    | unchanged                        |
| decision  | otherwise                                                    | 200    | moved                            |

## Contracts

### C-04 — `condition_interpreter`: `interpret`, `resolve`, `Interpretation`
Produced by: BRIEF-0112-C   Consumed by: BRIEF-0112-D
Signatures: `interpret(db, world_id: str, role: str, instruction: str,
current: Optional[ConditionTree], exchanges=None) -> Interpretation`;
`resolve(db, world_id: str, pending: dict, mentions: list[dict], notes:
list[str], bindings: dict[str, str]) -> Interpretation`.
`Interpretation(outcome, tree, pending, mentions, notes, errors, retried)`:
`outcome` in `proposed` | `needs_choice` | `refused`; `tree` the clean
`ConditionTree` when `proposed` (a lone leaf as `all` of it), else None;
`pending` the dict form of the read tree, its waiting leaves carrying
`subject_mention` / `target_mention`; `mentions` `[{ref, name, kind,
status: matched | ambiguous | unmatched, entity_id, choices: [{entity_id,
name, type[, score]}]}]`; `notes` French lines (IF1, IA1); `errors` French
or writer messages. `Interpretation.payload(current, bindings=None) ->
dict` with exactly `writes.condition_drafts.PAYLOAD_KEYS` (C-07).
Error cases: `interpret` lets `OllamaError` and `LlmParseError` propagate;
`resolve` raises `ValueError` when a waiting mention has no pick or one
outside its choices. Neither writes. Outcomes: b-1.
Constants: `INTERPRET_USAGE = "condition_interpret"`,
`INTERPRET_UNAVAILABLE_MESSAGE`, `RESOURCE_KEY = "monnaie"`.

### C-06 — the routes
Produced by: BRIEF-0112-D   Consumed by: BRIEF-0112-E
`POST /api/conditions/interpret` body `{instruction: str, role: str,
current: dict | null, attempt_id: str | null}`;
`POST /api/conditions/drafts/{draft_id}/resolve` body `{bindings: {ref:
entity_id}}`; `POST /api/conditions/drafts/{draft_id}/decision` body
`{decision: "inserted" | "discarded"}`.
Answer (all three): `{draft_id, outcome, view: {tree, flat, lines} | null,
mentions: [the mentions waiting for a pick: not matched, with choices],
notes: [str], errors: [str]}` -- `view` is `quest_reads.condition_view` of
the proposed tree; the decision's answer carries `draft_id` and the new
`outcome` with empty lists.
Statuses: b-5.

### C-07 — `condition_draft` and its writer
Produced by: BRIEF-0112-B   Consumed by: BRIEF-0112-D
Table (v2.21): `id, attempt_id, world_ref, world_name, role, instruction,
outcome, retried, offer_ref, saved_as_proposed, payload, model_calls,
created_at, decided_at`; CHECKs `ck_condition_draft_role` (role in
`CONDITION_ROLES`), `ck_condition_draft_outcome` (the eight outcomes),
`ck_condition_draft_saved` (`offer_ref` and `saved_as_proposed` set exactly
on `saved`); indexes `idx_condition_draft_attempt (attempt_id,
created_at)`, `idx_condition_draft_world (world_ref, created_at)`; no
`world_id`, no FK. `models.CONDITION_DRAFT_OUTCOMES` in CHECK order.
Writer (`writes/condition_drafts.py`): `FIRST_OUTCOMES`,
`CONDITION_DRAFT_MOVES` (b-2), `PAYLOAD_KEYS = {current, pending, mentions,
bindings, proposed, notes, errors}`;
`write_condition_draft(db, *, attempt_id, world_id, role, instruction,
outcome, payload, model_calls, retried=False) -> ConditionDraft`;
`move_condition_draft(db, draft, outcome, payload=None) -> ConditionDraft`;
`mark_draft_saved(db, *, world_id, draft_id, offer_id, tree) -> bool`.
Error cases: `ValueError` before any row for an empty attempt / world /
instruction, an unknown role, a first outcome outside `FIRST_OUTCOMES`, a
payload without exactly `PAYLOAD_KEYS`, a non-list `model_calls`, a move
outside b-2 (and any move to `saved`). `mark_draft_saved` never raises:
b-4. None commits.

### C-08 — the offer body's draft ids
Produced by: BRIEF-0112-D   Consumed by: BRIEF-0112-E
`OfferBody.eligibility_draft_id: Optional[str]`;
`OfferStepBody.prerequisite_draft_id`, `.completion_draft_id:
Optional[str]`. `routes/quests._mark_drafts(body, offer_id, world_id, db)`,
called by `_save_offer` after `write_quest_offer` and before `commit`: for
each given id, the condition as written
(`node_to_dict(clean_condition(node_from_dict(raw)))`) goes to
`mark_draft_saved`. Frontend: a condition draft carries `draftId` (null by
default, the inserted proposal's id), sent as those three fields.

## Context

The interpreter proposes (C) and the journal is ready (B). This brief puts them behind three routes the editor will call, journals every proposal that reached the model -- the failures included -- and links the creator's save to what she inserted, so D1's acceptance rate is a fact in the database. No route writes an offer: « Enregistrer » stays the only way in.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md` and `src/world_engine/cockpit/static/` are not in the
diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - creates `src/world_engine/cockpit/routes/conditions.py` (C-06, b-5): `interpret`, `resolve`, `decide`, `PARSE_ERROR_MESSAGE`, `DECISIONS`; journals through `write_condition_draft` / `move_condition_draft`; `OllamaError` -> 503 with `condition_interpreter.INTERPRET_UNAVAILABLE_MESSAGE`, `LlmParseError` -> 502, both journaled with `model_exchange.fail`;
   - `cockpit/app.py`: imports and mounts the router after the quests router;
   - `cockpit/routes/quests.py`: `OfferBody.eligibility_draft_id`, `OfferStepBody.prerequisite_draft_id` / `completion_draft_id`, and `_mark_drafts` called by `_save_offer` after `write_quest_offer`, before `commit` (C-08, b-4);
   - adds ND1-ND3 to `condition_interpreter.py`;
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - src/world_engine/cockpit/app.py
   - src/world_engine/cockpit/routes/conditions.py
   - src/world_engine/cockpit/routes/quests.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/condition_interpreter.py

````diff
diff --git a/src/world_engine/cockpit/app.py b/src/world_engine/cockpit/app.py
index ae6456b..457d8cd 100644
--- a/src/world_engine/cockpit/app.py
+++ b/src/world_engine/cockpit/app.py
@@ -54,6 +54,7 @@ from ..models import LinkBatch, LinkBatchRow, NpcBatch, NpcBatchRow, SchemaMeta
 from ..schema_version import EXPECTED_STATIC_SCHEMA_VERSION
 from . import crud as _crud
 from .origin_guard import origin_guard
+from .routes import conditions as _routes_conditions
 from .routes import creator as _routes_creator
 from .routes import day as _routes_day
 from .routes import debts as _routes_debts
@@ -141,6 +142,7 @@ app.include_router(_routes_lore_mentions.router)
 app.include_router(_routes_lore_choices.router)
 app.include_router(_routes_lore_write.router)
 app.include_router(_routes_quests.router)
+app.include_router(_routes_conditions.router)
 app.include_router(_routes_debts.router)
 
 app.mount("/static", _FreshnessAwareStaticFiles(directory=_STATIC_DIR), name="static")
diff --git a/src/world_engine/cockpit/routes/conditions.py b/src/world_engine/cockpit/routes/conditions.py
new file mode 100644
index 0000000..9e340b9
--- /dev/null
+++ b/src/world_engine/cockpit/routes/conditions.py
@@ -0,0 +1,161 @@
+"""The condition interpreter's routes (TICKET-0112, BRIEF-0112-D; decisions
+IB1, IG1, IH1, IJ1).
+
+The offer editor asks for a condition in French and gets a proposal back;
+nothing here touches an offer -- the creator inserts the proposal into her
+draft and her « Enregistrer » writes it (`routes/quests.py`), A1 of the
+conditions series:
+    POST /api/conditions/interpret                    a sentence -> a proposal
+    POST /api/conditions/drafts/{draft_id}/resolve    the names she picked
+    POST /api/conditions/drafts/{draft_id}/decision   inserted | discarded
+
+Every model call lives in `condition_interpreter`, every journal write in
+`writes/condition_drafts.py`; this module parses, maps a refusal to its
+status code, and commits once per request. Every proposal that reached the
+model is journaled, the unavailable and the unparsable included (IH1, D1);
+a request refused before the model (no active world, an empty sentence, an
+unknown role, a current tree that does not hold) is not. Every POST passes
+the origin guard (`cockpit/origin_guard.py`, mounted on the app).
+"""
+
+from __future__ import annotations
+
+from typing import Optional
+
+from fastapi import APIRouter, Depends, HTTPException
+from pydantic import BaseModel, Field
+from sqlmodel import Session
+
+from ... import condition_interpreter as _interpreter
+from ... import model_exchange
+from ...conditions import node_from_dict
+from ...db import get_session
+from ...llm_parse import LlmParseError
+from ...lore_usage import attempt_id as _attempt_id
+from ...models import CONDITION_ROLES, ConditionDraft
+from ...ollama_client import OllamaError
+from ...quest_reads import condition_view
+from ...writes.conditions import clean_condition
+from ...writes.condition_drafts import move_condition_draft, write_condition_draft
+from .. import crud as _crud
+
+router = APIRouter()
+
+PARSE_ERROR_MESSAGE = (
+    "Le modèle a répondu dans une forme illisible : aucune condition n'a été proposée "
+    "et rien n'a changé dans l'offre. Relance, ou reformule ta phrase."
+)
+DECISIONS: tuple[str, ...] = ("inserted", "discarded")
+
+
+class InterpretBody(BaseModel):
+    instruction: str
+    role: str
+    # The condition being edited (IC1), in the dict form of
+    # `conditions.node_to_dict`; null when the creator starts from nothing.
+    current: Optional[dict] = None
+    attempt_id: Optional[str] = None
+
+
+class ResolveBody(BaseModel):
+    bindings: dict[str, str] = Field(default_factory=dict)
+
+
+class DecisionBody(BaseModel):
+    decision: str
+
+
+def _current(body: InterpretBody, world_id: str, db: Session):
+    if not body.instruction.strip():
+        raise HTTPException(status_code=422, detail="Écris d'abord la condition en une phrase.")
+    if body.role not in CONDITION_ROLES:
+        raise HTTPException(status_code=422, detail=f"unknown condition role {body.role!r}")
+    try:
+        return clean_condition(db, world_id, node_from_dict(body.current), where="current: ")
+    except ValueError as exc:
+        raise HTTPException(status_code=422, detail=f"La condition actuelle ne tient pas : {exc}") from exc
+
+
+def _answer(draft: ConditionDraft, result: Optional[_interpreter.Interpretation], db: Session) -> dict:
+    """C-06: what the editor shows."""
+    if result is None:
+        return {"draft_id": draft.id, "outcome": draft.outcome, "view": None, "mentions": [], "notes": [],
+                "errors": []}
+    return {
+        "draft_id": draft.id, "outcome": result.outcome,
+        "view": condition_view(db, result.tree) if result.tree is not None else None,
+        "mentions": [m for m in result.mentions if m["status"] != "matched" and m["choices"]],
+        "notes": result.notes, "errors": result.errors,
+    }
+
+
+def _failed(db: Session, body: InterpretBody, world_id: str, current, outcome: str,
+            exchanges: list, exc: Exception) -> None:
+    model_exchange.fail(exchanges, exc)
+    empty = _interpreter.Interpretation(outcome, None, None, [], [], [])
+    write_condition_draft(
+        db, attempt_id=_attempt_id(body.attempt_id), world_id=world_id, role=body.role,
+        instruction=body.instruction, outcome=outcome, payload=empty.payload(current),
+        model_calls=[e.to_record() for e in exchanges],
+    )
+    db.commit()
+
+
+@router.post("/api/conditions/interpret")
+def interpret(body: InterpretBody, db: Session = Depends(get_session)) -> dict:
+    world_id = _crud._world_id(db)
+    current = _current(body, world_id, db)
+    exchanges: list[model_exchange.ModelExchange] = []
+    try:
+        result = _interpreter.interpret(db, world_id, body.role, body.instruction, current, exchanges)
+    except OllamaError as exc:
+        _failed(db, body, world_id, current, "unavailable", exchanges, exc)
+        raise HTTPException(status_code=503, detail=_interpreter.INTERPRET_UNAVAILABLE_MESSAGE) from exc
+    except LlmParseError as exc:
+        _failed(db, body, world_id, current, "parse_error", exchanges, exc)
+        raise HTTPException(status_code=502, detail=PARSE_ERROR_MESSAGE) from exc
+    draft = write_condition_draft(
+        db, attempt_id=_attempt_id(body.attempt_id), world_id=world_id, role=body.role,
+        instruction=body.instruction, outcome=result.outcome, retried=result.retried,
+        payload=result.payload(current), model_calls=[e.to_record() for e in exchanges],
+    )
+    db.commit()
+    return _answer(draft, result, db)
+
+
+def _draft(db: Session, draft_id: str) -> ConditionDraft:
+    world_id = _crud._world_id(db)
+    draft = db.get(ConditionDraft, draft_id)
+    if draft is None or draft.world_ref != world_id:
+        raise HTTPException(status_code=404, detail=f"condition draft {draft_id!r} not found")
+    return draft
+
+
+@router.post("/api/conditions/drafts/{draft_id}/resolve")
+def resolve(draft_id: str, body: ResolveBody, db: Session = Depends(get_session)) -> dict:
+    draft = _draft(db, draft_id)
+    if draft.outcome != "needs_choice":
+        raise HTTPException(status_code=409, detail=f"a {draft.outcome!r} proposal has no name to pick")
+    stored = draft.payload
+    try:
+        result = _interpreter.resolve(db, draft.world_ref, stored["pending"], stored["mentions"],
+                                      stored["notes"], body.bindings)
+    except ValueError as exc:
+        raise HTTPException(status_code=422, detail=str(exc)) from exc
+    move_condition_draft(db, draft, result.outcome,
+                         result.payload(node_from_dict(stored["current"]), body.bindings))
+    db.commit()
+    return _answer(draft, result, db)
+
+
+@router.post("/api/conditions/drafts/{draft_id}/decision")
+def decide(draft_id: str, body: DecisionBody, db: Session = Depends(get_session)) -> dict:
+    draft = _draft(db, draft_id)
+    if body.decision not in DECISIONS:
+        raise HTTPException(status_code=422, detail=f"unknown decision {body.decision!r}")
+    try:
+        move_condition_draft(db, draft, body.decision)
+    except ValueError as exc:
+        raise HTTPException(status_code=409, detail=str(exc)) from exc
+    db.commit()
+    return _answer(draft, None, db)
diff --git a/src/world_engine/cockpit/routes/quests.py b/src/world_engine/cockpit/routes/quests.py
index 71e2385..22825b0 100644
--- a/src/world_engine/cockpit/routes/quests.py
+++ b/src/world_engine/cockpit/routes/quests.py
@@ -31,7 +31,7 @@ from pydantic import BaseModel, Field
 from sqlmodel import Session, select
 
 from ... import quest_reads
-from ...conditions import node_from_dict
+from ...conditions import node_from_dict, node_to_dict
 from ...day_plan import PlanStep
 from ...db import get_session
 from ...models import Quest, QuestEconomy, QuestOffer
@@ -41,6 +41,8 @@ from ...writes import (
     TermSpec, abandon_quest, accept_quest, settle_quest, settle_quest_on_credit, upsert_quest_economy,
     write_quest_offer,
 )
+from ...writes.condition_drafts import mark_draft_saved
+from ...writes.conditions import clean_condition
 from ...writes.quest_terms import ECONOMY_COLUMNS
 from .. import crud as _crud
 from .day import _resolve_player_character
@@ -56,6 +58,10 @@ class OfferStepBody(BaseModel):
     # `conditions.node_to_dict`; null is none.
     prerequisite: Optional[dict] = None
     completion: Optional[dict] = None
+    # TICKET-0112 (IH1): the interpreter's proposal the creator inserted into
+    # each condition, if any; saving marks it `saved` (`mark_draft_saved`).
+    prerequisite_draft_id: Optional[str] = None
+    completion_draft_id: Optional[str] = None
 
 
 class TermBody(BaseModel):
@@ -82,6 +88,8 @@ class OfferBody(BaseModel):
     # TICKET-0109 (B1): the offer's costs and rewards, replaced whole; absent
     # (None) keeps the stored ones.
     terms: Optional[list[TermBody]] = None
+    # TICKET-0112 (IH1): the interpreter's proposal inserted into the eligibility.
+    eligibility_draft_id: Optional[str] = None
 
 
 class ValueBody(BaseModel):
@@ -128,11 +136,26 @@ def _save_offer(body: OfferBody, offer: Optional[QuestOffer], world_id: str, db:
     except ValueError as exc:
         db.rollback()
         raise HTTPException(status_code=422, detail=str(exc)) from exc
+    _mark_drafts(body, offer.id, world_id, db)
     db.commit()
     db.refresh(offer)
     return quest_reads.offer_dict(offer, db)
 
 
+def _mark_drafts(body: OfferBody, offer_id: str, world_id: str, db: Session) -> None:
+    """IH1: each inserted proposal is `saved` with the offer, in its
+    transaction, compared with the condition as written (its clean dict
+    form). A draft that cannot be marked is skipped: the journal never fails
+    the creator's save."""
+    pairs = [(body.eligibility_draft_id, body.eligibility)] + [
+        pair for step in body.steps
+        for pair in ((step.prerequisite_draft_id, step.prerequisite), (step.completion_draft_id, step.completion))]
+    for draft_id, raw in pairs:
+        if draft_id:
+            tree = node_to_dict(clean_condition(db, world_id, node_from_dict(raw)))
+            mark_draft_saved(db, world_id=world_id, draft_id=draft_id, offer_id=offer_id, tree=tree)
+
+
 @router.get("/api/quest-offers")
 def list_offers(db: Session = Depends(get_session)) -> list[dict]:
     world_id = _crud._world_id(db)
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 0d9ff2b..e340bc4 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18612,6 +18612,27 @@ authoring model by default, the creator's per-template override otherwise.
 interpreter writes nothing: `condition_interpreter.py` calls no model
 directly (its `_call` is `prompt_call.call_json`) and no write.
 
+## THE INTERPRETER'S ROUTES (TICKET-0112) -- A PROPOSAL IS JOURNALED, PICKED, INSERTED OR DISCARDED; SAVING THE OFFER MARKS IT SAVED (BRIEF-0112-d, no schema change)
+
+**IG1, IH1, IJ1.** `POST /api/conditions/interpret` turns the creator's
+sentence for one condition into a proposal: its French lines and, when it
+is insertable, the view the offer editor inserts (`quest_reads.condition_view`);
+the names waiting for her pick with their choices; the notes and errors.
+`POST /api/conditions/drafts/{id}/resolve` applies her picks (no model
+call); `POST /api/conditions/drafts/{id}/decision` records `inserted` or
+`discarded`. No route touches an offer: the creator's « Enregistrer »
+writes the condition through `routes/quests.py` as before (A1 of the
+series), and the offer body names, per condition, the proposal she
+inserted there -- saving marks it `saved` in the same transaction, with
+whether the saved condition is the proposed one. A draft that cannot be
+marked is skipped: the journal never fails her save.
+
+Every proposal that reached the model is journaled -- Ollama down (503,
+`INTERPRET_UNAVAILABLE_MESSAGE`, her sentence kept: K1 of TICKET-0098) and
+an unparsable reply (502) included; a request refused before the model is
+not. A proposal's attempt id is the editor's, in canonical form, or a
+fresh one (`lore_usage.attempt_id`).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/condition_interpreter.py b/tooling/verify/checks/condition_interpreter.py
index e81864a..4b76434 100644
--- a/tooling/verify/checks/condition_interpreter.py
+++ b/tooling/verify/checks/condition_interpreter.py
@@ -90,6 +90,33 @@ NC4 -- the interpreter writes nothing (fixture). Across NC3, the counts of
    `condition`, `condition_node`, `fact`, `entity`, `knowledge` and
    `condition_draft` do not move.
 
+ND1 -- the routes' shape (BRIEF-0112-D; static, AST). `cockpit/routes/
+   conditions.py` declares POST `/api/conditions/interpret`,
+   `/api/conditions/drafts/{draft_id}/resolve` and `/decision`, calls
+   neither `chat` nor `select`, and its `OllamaError` handler raises a 503
+   whose detail is the named `INTERPRET_UNAVAILABLE_MESSAGE`; `app.py`
+   mounts its router. `routes/quests.py`'s `_save_offer` calls `_mark_drafts`
+   after `write_quest_offer` and before `commit`, and `_mark_drafts` calls
+   `mark_draft_saved`.
+ND2 -- the routes (fixture, route functions, `condition_interpreter.chat`
+   stubbed). a. a sentence -> `proposed`, its view (tree, flat rows, French
+   lines), one `proposed` row whose payload's `proposed` is the view's
+   tree, one model call, a fresh attempt id; no condition row. b. Ollama
+   down -> 503 with the named message, one `unavailable` row whose model
+   call carries the error. c. an unparsable reply -> 502, one `parse_error`
+   row keeping the raw reply. d. an empty sentence, an unknown role, a
+   current tree that does not hold -> 422, no row. e. a name two
+   characters carry -> `needs_choice` with its choices; a pick outside them
+   -> 422, the row unmoved; a pick -> `proposed`, the row moved with its
+   bindings; a second resolve -> 409. f. `inserted` -> the row inserted; a
+   second decision -> 409; an unknown decision -> 422; a draft of another
+   world -> 404.
+ND3 -- saving the offer (fixture). An offer saved with its eligibility as
+   inserted and its id -> the draft `saved`, `offer_ref` the offer,
+   `saved_as_proposed` true; a step's completion inserted then changed ->
+   `saved`, false; an unknown draft id and a `proposed` draft's id leave
+   the save whole and the `proposed` draft unmoved.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
@@ -861,6 +888,233 @@ def check_nc3_nc4(engine, ids) -> None:
         fail(f"NC4: the interpreter wrote rows: {before} -> {after}")
 
 
+# --- ND1 -----------------------------------------------------------------------
+
+def _decorated_paths(tree: ast.Module) -> dict[str, str]:
+    found = {}
+    for node in tree.body:
+        if isinstance(node, ast.FunctionDef):
+            for deco in node.decorator_list:
+                if isinstance(deco, ast.Call) and _callee(deco) == "post" and deco.args \
+                        and isinstance(deco.args[0], ast.Constant):
+                    found[deco.args[0].value] = node.name
+    return found
+
+
+def _nd1_route() -> None:
+    path = SRC / "cockpit" / "routes" / "conditions.py"
+    if not path.exists():
+        fail("ND1: cockpit/routes/conditions.py is missing")
+        return
+    tree = _parse(path)
+    paths = set(_decorated_paths(tree))
+    want = {"/api/conditions/interpret", "/api/conditions/drafts/{draft_id}/resolve",
+            "/api/conditions/drafts/{draft_id}/decision"}
+    if paths != want:
+        fail(f"ND1: the routes are {sorted(paths)}")
+    calls = {_callee(n) for n in ast.walk(tree) if isinstance(n, ast.Call)} & {"chat", "select"}
+    if calls:
+        fail(f"ND1: routes/conditions.py calls {sorted(calls)}")
+    handlers = [h for h in ast.walk(tree) if isinstance(h, ast.ExceptHandler)
+                and isinstance(h.type, ast.Name) and h.type.id == "OllamaError"]
+    named = False
+    for handler in handlers:
+        for node in ast.walk(handler):
+            if isinstance(node, ast.Call) and _callee(node) == "HTTPException":
+                kw = {k.arg: k.value for k in node.keywords}
+                named = (isinstance(kw.get("status_code"), ast.Constant) and kw["status_code"].value == 503
+                         and isinstance(kw.get("detail"), ast.Attribute)
+                         and kw["detail"].attr == "INTERPRET_UNAVAILABLE_MESSAGE")
+    if not handlers or not named:
+        fail("ND1: the OllamaError handler does not raise 503 with INTERPRET_UNAVAILABLE_MESSAGE")
+    app = (SRC / "cockpit" / "app.py").read_text(encoding="utf-8")
+    if "app.include_router(_routes_conditions.router)" not in app:
+        fail("ND1: app.py does not mount the conditions router")
+
+
+def _nd1_save() -> None:
+    tree = _parse(SRC / "cockpit" / "routes" / "quests.py")
+    fns = {n.name: n for n in tree.body if isinstance(n, ast.FunctionDef)}
+    save, mark = fns.get("_save_offer"), fns.get("_mark_drafts")
+    if save is None or mark is None:
+        fail("ND1: routes/quests.py lacks _save_offer or _mark_drafts")
+        return
+    order = [(n.lineno, _callee(n)) for n in ast.walk(save) if isinstance(n, ast.Call)
+             and _callee(n) in ("write_quest_offer", "_mark_drafts", "commit")]
+    names = [name for _, name in sorted(order)]
+    if names != ["write_quest_offer", "_mark_drafts", "commit"]:
+        fail(f"ND1: _save_offer calls {names}, not write_quest_offer -> _mark_drafts -> commit")
+    if "mark_draft_saved" not in {_callee(n) for n in ast.walk(mark) if isinstance(n, ast.Call)}:
+        fail("ND1: _mark_drafts does not call mark_draft_saved")
+
+
+def check_nd1() -> None:
+    _nd1_route()
+    _nd1_save()
+
+
+# --- ND2 / ND3 -----------------------------------------------------------------
+
+def _activate(session, world_id: str) -> None:
+    from sqlmodel import select
+
+    from world_engine.models import World
+
+    for world in session.exec(select(World).where(World.is_active == True)).all():  # noqa: E712
+        world.is_active = False
+        session.add(world)
+    ours = session.get(World, world_id)
+    ours.is_active = True
+    session.add(ours)
+    session.commit()
+
+
+def _drafts(session) -> list:
+    from sqlmodel import select
+
+    from world_engine.models import ConditionDraft
+
+    session.expire_all()
+    return list(session.exec(select(ConditionDraft).order_by(ConditionDraft.created_at)).all())
+
+
+def _post(routes, fn, *args, **kw):
+    """Call a route function; (answer, None) or (None, status_code)."""
+    from fastapi import HTTPException
+
+    try:
+        return fn(*args, **kw), None
+    except HTTPException as exc:
+        return None, (exc.status_code, exc.detail)
+
+
+def _with_stub(ci, replies, fn):
+    stub, original = _Stub(replies), ci.chat
+    ci.chat = stub
+    try:
+        return fn()
+    finally:
+        ci.chat = original
+
+
+def _nd2_interpret(session, ids, routes, ci) -> dict:
+    from sqlmodel import select
+
+    from world_engine.models import Condition
+    from world_engine.ollama_client import OllamaError
+
+    before = len(_drafts(session))
+    body = routes.InterpretBody(instruction="Le joueur a 15 fourrures ou est de la Guilde", role="eligibility")
+    answer, err = _with_stub(ci, [_answer({"op": "any", "children": [FURS, GUILD]})],
+                             lambda: _post(routes, routes.interpret, body, db=session))
+    rows = _drafts(session)
+    row = rows[-1] if len(rows) == before + 1 else None
+    if err or answer["outcome"] != "proposed" or answer["view"]["flat"] is not None \
+            or not answer["view"]["lines"] or row is None or row.outcome != "proposed" \
+            or row.payload["proposed"] != answer["view"]["tree"] or len(row.model_calls) != 1 \
+            or len(row.attempt_id) != 36 or session.exec(select(Condition)).first():
+        fail(f"ND2a: answer {answer}, error {err}, row {row and row.outcome}")
+    for label, reply, status, outcome in (("Ollama down", OllamaError("down"), 503, "unavailable"),
+                                          ("an unparsable reply", "pas du json", 502, "parse_error")):
+        _, err = _with_stub(ci, [reply], lambda: _post(routes, routes.interpret, body, db=session))
+        last = _drafts(session)[-1]
+        call = last.model_calls[0] if last.model_calls else {}
+        kept = call.get("error") if outcome == "unavailable" else call.get("raw_output") == "pas du json"
+        if not err or err[0] != status or last.outcome != outcome or not kept \
+                or (status == 503 and err[1] != ci.INTERPRET_UNAVAILABLE_MESSAGE):
+            fail(f"ND2{'b' if status == 503 else 'c'}: {label} gave {err}, row {last.outcome}, call {call}")
+    count = len(_drafts(session))
+    for label, bad in (("an empty sentence", dict(instruction=" ", role="eligibility")),
+                       ("an unknown role", dict(instruction="x", role="reward")),
+                       ("a current tree that does not hold",
+                        dict(instruction="x", role="eligibility", current={"op": "not", "children": []}))):
+        _, err = _post(routes, routes.interpret, routes.InterpretBody(**bad), db=session)
+        if not err or err[0] != 422 or len(_drafts(session)) != count:
+            fail(f"ND2d: {label} gave {err}")
+    return answer
+
+
+def _nd2_choice(session, ids, routes, ci) -> None:
+    mira = _ml("has_met", target={"name": "Mira", "kind": "person"})
+    body = routes.InterpretBody(instruction="Le joueur a rencontré Mira", role="completion")
+    answer, _ = _with_stub(ci, [_answer(mira)], lambda: _post(routes, routes.interpret, body, db=session))
+    if not answer or answer["outcome"] != "needs_choice" or len(answer["mentions"]) != 1:
+        fail(f"ND2e: an ambiguous name answered {answer}")
+        return
+    ref, draft_id = answer["mentions"][0]["ref"], answer["draft_id"]
+    _, err = _post(routes, routes.resolve, draft_id, routes.ResolveBody(bindings={ref: ids["garde"]}), db=session)
+    if not err or err[0] != 422 or _drafts(session)[-1].outcome != "needs_choice":
+        fail(f"ND2e: a pick outside the choices gave {err}")
+    done, err = _post(routes, routes.resolve, draft_id, routes.ResolveBody(bindings={ref: ids["mira1"]}), db=session)
+    row = _drafts(session)[-1]
+    if err or done["outcome"] != "proposed" or row.outcome != "proposed" or row.payload["bindings"] != {ref: ids["mira1"]}:
+        fail(f"ND2e: a pick gave {done or err}, row {row.outcome}")
+    _, err = _post(routes, routes.resolve, draft_id, routes.ResolveBody(bindings={ref: ids["mira1"]}), db=session)
+    if not err or err[0] != 409:
+        fail(f"ND2e: a second resolve gave {err}")
+
+
+def _nd2_decision(session, ids, routes, ci, draft_id: str, other_world: str) -> None:
+    from world_engine.writes.condition_drafts import write_condition_draft
+
+    done, err = _post(routes, routes.decide, draft_id, routes.DecisionBody(decision="inserted"), db=session)
+    if err or done["outcome"] != "inserted":
+        fail(f"ND2f: inserted gave {done or err}")
+    for label, decision, status in (("a second decision", "discarded", 409), ("an unknown decision", "kept", 422)):
+        _, err = _post(routes, routes.decide, draft_id, routes.DecisionBody(decision=decision), db=session)
+        if not err or err[0] != status:
+            fail(f"ND2f: {label} gave {err}")
+    foreign = write_condition_draft(session, attempt_id="a", world_id=other_world, role="eligibility",
+                                    instruction="x", outcome="proposed", payload=_payload(), model_calls=[])
+    session.commit()
+    _, err = _post(routes, routes.decide, foreign.id, routes.DecisionBody(decision="inserted"), db=session)
+    if not err or err[0] != 404:
+        fail(f"ND2f: another world's draft gave {err}")
+
+
+def _nd3_save(session, ids, routes, quests, ci, eligibility: dict, draft_id: str) -> None:
+    from world_engine.models import ConditionDraft
+
+    body = routes.InterpretBody(instruction="L'objectif : 15 fourrures", role="completion")
+    answer, _ = _with_stub(ci, [_answer(FURS)], lambda: _post(routes, routes.interpret, body, db=session))
+    changed_id = answer["draft_id"]
+    routes.decide(changed_id, routes.DecisionBody(decision="inserted"), db=session)
+    proposed, _ = _with_stub(ci, [_answer(GUILD)], lambda: _post(routes, routes.interpret, body, db=session))
+    changed = {"op": "all", "children": [_leafd("item_held", target_entity_id=ids["fur"], threshold=20)]}
+    offer = quests.OfferBody(
+        giver_entity_id=ids["garde"], title="Interprétée", eligibility=eligibility, eligibility_draft_id=draft_id,
+        steps=[quests.OfferStepBody(objective="Rapporter", cost=1, completion=changed,
+                                    completion_draft_id=changed_id, prerequisite_draft_id="no-such-draft"),
+               quests.OfferStepBody(objective="Encore", cost=1, completion=changed,
+                                    completion_draft_id=proposed["draft_id"])])
+    saved, err = _post(quests, quests.create_offer, offer, db=session)
+    session.expire_all()
+    one, two, three = (session.get(ConditionDraft, i) for i in (draft_id, changed_id, proposed["draft_id"]))
+    if err or (one.outcome, one.offer_ref, one.saved_as_proposed) != ("saved", saved["id"], True):
+        fail(f"ND3: the inserted eligibility reads {one.outcome, one.offer_ref, one.saved_as_proposed}, {err}")
+    if (two.outcome, two.saved_as_proposed) != ("saved", False) or three.outcome != "proposed":
+        fail(f"ND3: the changed completion reads {two.outcome, two.saved_as_proposed}, the proposed {three.outcome}")
+
+
+def check_nd2_nd3(engine, ids) -> None:
+    from sqlmodel import Session
+
+    from world_engine import condition_interpreter as ci
+    from world_engine.cockpit.routes import conditions as routes
+    from world_engine.cockpit.routes import quests
+    from world_engine.models import World
+
+    with Session(engine) as session:
+        _activate(session, ids["world"])
+        other = World(name="Autre ND", is_active=False)
+        session.add(other)
+        session.commit()
+        answer = _nd2_interpret(session, ids, routes, ci)
+        _nd2_choice(session, ids, routes, ci)
+        _nd2_decision(session, ids, routes, ci, answer["draft_id"], other.id)
+        _nd3_save(session, ids, routes, quests, ci, answer["view"]["tree"], answer["draft_id"])
+
+
 def main() -> int:
     db_path = _fresh_db()
     from world_engine.db import create_db_and_tables, engine
@@ -876,6 +1130,8 @@ def main() -> int:
         nc_ids = _nc_world(session)
     check_nc2(engine, nc_ids)
     check_nc3_nc4(engine, nc_ids)
+    check_nd1()
+    check_nd2_nd3(engine, nc_ids)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -885,7 +1141,9 @@ def main() -> int:
           "of the interpreter, outside any world, its outcome moving one way to « saved »; the "
           "interpreter shows the model the language and coded lists, reads its answer back through codes "
           "and the name index, validates every leaf, asks once more with the errors, leaves a name to "
-          "the creator, never writes a condition, and sends a cost back to the offer's terms")
+          "the creator, never writes a condition, and sends a cost back to the offer's terms; its routes "
+          "journal every proposal that reached the model, move it on the creator's pick and decision, and "
+          "saving the offer marks what she inserted saved, as proposed or changed")
     return 0
 
 
````

2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit as one commit: `BRIEF-0112-D: the interpreter's routes and the save marking`.

## Scope OUT

- Any route that writes an offer or a condition: the editor's save does (A1 of the series).
- A route that reads the journal back for a list or a rate (TICKET-0115).
- A per-route origin check: the middleware guards every POST (R-18).
- Refusing a save because a draft id is unknown or stale: the journal never fails the creator's save (b-4).
- The editor (BRIEF-0112-E).

## Invariants to defend

**Creator control is structural** -- no route here writes an offer; `_mark_drafts` only moves journal rows, inside the save's own transaction (ND1, ND3). **Two sanctioned canon-write paths** -- the offer is still written by `write_quest_offer` through the creator CRUD; `condition_draft` is non-canon. **Ollama down is explicit** -- a named message, the sentence kept on the client, nothing inserted (K1 of 0098; ND1, ND2 b). **The player never sees any of this** -- every route is a creator route; no payload reaches Journée.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- A named mutation does not turn its rule red.
- `quests.py` or `conditions.py` (the 0111 check) turns red: the offer API changed shape.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run; a check that times out under load and passes when rerun alone (name it).
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.
- `lore_usage.attempt_id` reused for the attempt id (it is the Lore shell's function, imported, not copied).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/condition_interpreter.py` -> `PASS: condition_interpreter -- one coded list names facts, quest offers and skills by code; one templated JSON call serves the creator's authoring tools; v2.21 journals every proposal of the interpreter, outside any world, its outcome moving one way to « saved »; the interpreter shows the model the language and coded lists, reads its answer back through codes and the name index, validates every leaf, asks once more with the errors, leaves a name to the creator, never writes a condition, and sends a cost back to the offer's terms; its routes journal every proposal that reached the model, move it on the creator's pick and decision, and saving the offer marks what she inserted saved, as proposed or changed`
- `quests.py`, `conditions.py`, `debts.py`, `lore_usage.py`, `single_canon_write.py`, `module_budget.py`, `function_length.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`condition_interpreter.py` exits 1 with the rule named):
  - in `src/world_engine/cockpit/routes/conditions.py`, `        _failed(db, body, world_id, current, "unavailable", exchanges, exc)` -> `        pass` -> `ND2`
  - in `src/world_engine/cockpit/routes/quests.py`, `    _mark_drafts(body, offer.id, world_id, db)` -> `    pass` -> `ND1`
  - in `src/world_engine/cockpit/routes/conditions.py`, `        "mentions": [m for m in result.mentions if m["status"] != "matched" and m["choices"]],` -> `        "mentions": [],` -> `ND2`
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 145/145.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry « THE INTERPRETER'S ROUTES (TICKET-0112) -- A PROPOSAL IS JOURNALED, PICKED, INSERTED OR DISCARDED; SAVING THE OFFER MARKS IT SAVED (BRIEF-0112-d, no schema change) » -- in the diff. No schema change.
