# BRIEF 0108-B — "A quest is accepted as a paused plan, pinned to a day, abandoned"

Lot: LOT-0108-quest-offers.md (authoritative on conflict)
Depends on: BRIEF-0108-A

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0108-A's commit). The facts carried below quote `main`'s line
numbers, as the lot does; where A moved a line, the anchor here gives where it now is.

- `src/world_engine/writes/goals_agendas.py:245` -> `def write_agenda(` takes no `status`; the guard `if owner.type == "character":` at `:274`; the row born `status="active",` at `:288`.
- `src/world_engine/day_plan.py:387` -> `def evaluate_specs(`; `MAX_PLAN_STEPS = 12` at `:103`.
- `src/world_engine/models/quests.py:39` -> `class QuestOffer(`; `:120` -> `class Quest(`.
- `src/world_engine/cockpit/routes/day.py` is 979 lines; `:629` -> `@router.post("/api/day/{batch_id}/plan")` on `def plan_day(batch_id: str, db: Session = Depends(get_session)) -> dict:`; `:675` -> `    plans = day_plans.open_plans(character, db)`.
- `src/world_engine/cockpit/routes/day.py:126` -> `def _resolve_player_character(world_id: str, db: Session) -> Character:`.
- `src/world_engine/cockpit/routes/day.py:762` -> `ProposedMutation.status == "proposed",`.
- `src/world_engine/cockpit/mutations.py:843` -> `if step.status != "active":`.
- `src/world_engine/cockpit/crud/_shared.py:57` -> `def _world_id(db: DbSession) -> str:`.
- `src/world_engine/cockpit/app.py:140` -> `app.include_router(_routes_lore_write.router)` is the last router.
- `tooling/verify/canon_write_policy.txt:50` -> `src/world_engine/writes/goals_agendas.py::write_day_plan       agenda_step_requirement`.

## Facts carried

### R-01 — one active agenda per character, held in code only [M]
Opened: `src/world_engine/writes/goals_agendas.py:234-282` (`write_agenda`:
the guard `:263-271`, the row born `status="active"` at `:277`), `:523-583`
(`write_agenda_status`: the same guard, `:549-563`); `src/world_engine/
models/canon.py:772-792` (`Agenda`: `ck_agenda_status` allows `paused`;
`idx_agenda_owner_status` is not unique).
Finding: the rule is an explicit SELECT in the two writers; the schema
allows several active rows. `write_agenda` always creates `active`.
Consequence: a quest accepted while a day plan is active would raise. An
accepted quest is born `paused` (A1): `write_agenda` takes `status`
(`active` or `paused`), the guard applying to `active` only.

### R-02 — a planned day is an agenda of the player [M]
Opened: `goals_agendas.py:640-684` (`write_day_plan` calls `write_agenda` at
`:670`); `src/world_engine/cockpit/routes/day.py:579-597` (`_finalize_plan`;
`pass_play.agenda_id` set at `:597`).
Finding: every newly planned day creates the player's active agenda.
Consequence: a quest coexists with day plans as one open plan among them.

### R-03 — several open plans; a day selects one (TICKET-0077) [M]
Opened: `src/world_engine/day_plans.py:24-58` (`OPEN_PLAN_STATUSES =
("active", "paused")`, `open_plans`, `active_plan`, `park_active_plan`);
`routes/day.py:629-688` (`plan_day`: `select_plan` over the open plans at
`:675-679`; `None` parks the active plan and emits a new one);
`src/world_engine/cockpit/day_reconcile_apply.py:138-179` (`modify` only
accepts an identical plan), `:181-205` (`replace` parks the standing plan),
`:207-258` (`_reconcile_and_finalize`: a `paused` selection is swapped in at
`:227-235`).
Finding: a parked plan is resumed by a day that selects it; no verdict
rewrites a plan's steps; `replace` parks.
Consequence: A1 needs no change to reconciliation. The pin (O1) replaces
only the selection call; a `replace` verdict still parks a pinned quest.

### R-04 — activating an agenda promotes its first pending step [M]
Opened: `goals_agendas.py:488-520` (`_activate_lowest_pending_step_if_none_
active`), called at `:583`.
Consequence: an accepted quest born with its first step `active` (R-17's
precedent) is consistent with every later activation.

### R-15 — a step change does not check its agenda's status [M]
Opened: `src/world_engine/cockpit/mutations.py:828-887`.
Finding: the step must be `active` (`:843`); `complete` activates the next
pending step or writes the agenda `completed` (`:884`); `fail` writes it
`failed`; the agenda's own status is never read.
Consequence: a quest is abandoned only when no step change of it is
`proposed`; a quest's `completed`/`failed` come from here (M1).

### R-16 — awaiting review is `status = 'proposed'` [M]
Opened: `routes/day.py:741-773` (`_guard_no_pending_agenda_step_change`:
`mutation_type == "agenda_step_change"`, `status == "proposed"`, the
payload's `step_id`).
Consequence: `abandon_refusal` restates this query (the guard raises an
HTTP error and lives in a route module).

### R-17 — a creator agenda starts with its first step active [M]
Opened: `src/world_engine/cockpit/crud/agendas.py:173-207` (`:203`).

### R-18 — budgets [M]
Opened: `tooling/verify/checks/module_budget.py:57-58` (40 functions, 1000
lines per module), `tooling/verify/checks/function_length.py:29` (80 lines);
`routes/day.py` is 979 lines on `main`.
Consequence: the quest routes live in their own module; the pin adds 11
lines to `routes/day.py` (990).

### R-19 — Journée never sees the agenda [M]
Opened: `tooling/verify/checks/day_mutations.py:25-34`, `:332-352` (R7: no
dict built in `routes/day.py` has an `agenda_id`/`step_id` key; `Journee.
svelte` names neither).
Consequence: quest payloads carry `quest_id`/`offer_id` only; `quests.py`
extends R7 to the new modules (QB4, QC3).

### R-20 — the player and the active world [M]
Opened: `routes/day.py:126-139` (`_resolve_player_character`: exactly one
player character, else 400); `src/world_engine/cockpit/crud/_shared.py:
57-61` (`_world_id`).

### R-23 — canon writes, and the full-replace deletes [M]
Opened: `tooling/verify/canon_write_policy.txt` (`[CANON_TABLES]`;
`[ALLOWED_SITES]` is function-scoped, not interprocedural);
`tooling/verify/checks/single_canon_write.py:46-90` (the hard-delete law
and its full-replace list); `src/world_engine/writes/config.py:76-106`
(`write_npc_prices`: `DELETE FROM` scoped to its parent, then insert).

## Contracts

### C-01 — the requirement vocabulary (family contract)
Produced by: BRIEF-0108-A   Consumed by: BRIEF-0108-B, BRIEF-0108-C
Written before its members; re-read after the last (`quest_completed`).

In `src/world_engine/day_plan.py`, literal tuples, in this order:

```python
REQUIREMENT_TYPES = ("knowledge", "relation_gte", "resource", "location_reachable",
                     "has_met", "faction_member", "skill_rank_gte", "quest_completed")
MODEL_REQUIREMENT_TYPES = ("knowledge", "relation_gte", "resource", "location_reachable")
ENTITY_TARGET_TYPES = ("relation_gte", "location_reachable", "has_met", "faction_member")
KEY_TARGET_TYPES = ("knowledge", "resource", "skill_rank_gte", "quest_completed")
THRESHOLD_TYPES = ("relation_gte", "resource", "skill_rank_gte")
```

The two CHECK texts, carried byte for byte by `agenda_step_requirement`
(`ck_agenda_step_requirement_type`, `_shape`) and `quest_offer_requirement`
(`ck_quest_offer_requirement_type`, `_shape`):

```
type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed')
(type NOT IN ('relation_gte','location_reachable','has_met','faction_member') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)
```

Members (every row has all six columns):

| form | target | threshold | met iff | blocked reason (French) | `_clean_requirement` refuses | model |
|---|---|---|---|---|---|---|
| `knowledge` | key: fact id | -- | the character holds a row on the fact | unchanged | a fact not of the world | yes |
| `relation_gte` | entity | >= 1 | the target's social row toward the character >= threshold (0 if none) | unchanged | an entity not of the world | yes |
| `resource` | key: a label | >= 1 | the character's ledger balance >= threshold | unchanged | -- (label) | yes |
| `location_reachable` | entity | -- | the target is in the character's `connects_to` component | unchanged | an entity not of the world | yes |
| `has_met` | entity | -- | a `rencontre` row of the sorted pair | « il n'a encore jamais rencontré {name} » | an entity not of the world | no |
| `faction_member` | entity: a faction | -- | an active membership, secret included | « il n'appartient pas à {name} » | not a faction of the world | no |
| `skill_rank_gte` | key: base domain or definition id | 1-5 | `held_rank` >= threshold | « sa maîtrise de « {label} » ne suffit pas encore » | an unknown skill; threshold 0 or > 5 | no |
| `quest_completed` | key: quest offer id | -- | a quest of the character from that offer whose agenda is `completed` | « il doit d'abord mener à bien « {title} » » | an offer not of the world | no |

`Verdict.required_label` carries the target's name for `relation_gte` and
the four new forms.

### C-02 — evaluation
Produced by: BRIEF-0108-A   Consumed by: BRIEF-0108-B
Signature: `day_plan.evaluate_specs(requirements: tuple[RequirementSpec, ...],
character: Character, db: Session) -> list[Verdict]`; `evaluate_requirements
(step, character, db)` returns `evaluate_specs(step.requirements, character,
db)`. `skill_access.held_rank(db, character_id, skill_key) -> Optional[int]`.
Return shape: one `Verdict(type, met, current, required, reason,
required_label)` per requirement, in order.
Error and empty cases: an unknown type raises `ValueError`; an empty tuple
returns `[]`; `_day_reachable_ids` runs at most once, only for a
`location_reachable`.

### C-03 — the writers
Produced by: BRIEF-0108-B   Consumed by: BRIEF-0108-C (through C-04)

- `write_agenda(db, *, world_id, owner_entity_id, title, mutation_id=None,
  status="active") -> Agenda`: `status` is `active` or `paused`, else
  `ValueError`; the one-active guard applies to `active` only.
- `writes.quests.write_quest_offer(db, *, world_id, offer: Optional[QuestOffer],
  giver_entity_id, title, summary, repeatable, status, eligibility:
  list[RequirementSpec], steps: list[PlanStep]) -> QuestOffer`. Refuses,
  before any write, with `ValueError`: a blank title; a status outside
  `QUEST_OFFER_STATUSES`; a giver that is not an active character or
  faction of the world (`QUEST_GIVER_TYPES`); a requirement refused by
  `_clean_requirement`; 0 or more than `MAX_PLAN_STEPS` steps; a blank
  objective; a cost outside 1-4; a domain outside `BASE_SKILL_DOMAINS`; on a
  save, a `quest_completed` on the offer itself. A save snapshots the offer
  (`giver_entity_id`, `title`, `summary`, `repeatable`, `status`,
  `updated_at`) into `change_history`, then `DELETE FROM` its requirements
  and steps and writes the submitted set.
- `acceptance_refusal(db, offer, character) -> Optional[str]` (French):
  case table (b-1).
- `accept_quest(db, *, offer, character) -> Quest`: `ValueError` with the
  refusal, before any write. Writes one agenda (`paused`, the offer's
  title), its steps in order (the first `active`, the others `pending`, with
  `cost` and `domain`), each step's requirements (through
  `_clean_requirement`), one `quest` row.
- `abandon_refusal(db, quest) -> Optional[str]` (French): case table (b-2).
- `abandon_quest(db, *, quest) -> Agenda`: `ValueError` with the refusal;
  the agenda to `abandoned` through `write_agenda_status`.
- `offer_requirements(db, offer_id, step_id) -> tuple[RequirementSpec, ...]`:
  `step_id` None reads the eligibility.
- `QUEST_GIVER_TYPES = ("character", "faction")`, `OPEN_QUEST_STATUSES =
  ("active", "paused")`.

None commits.

### C-04 — reads and routes
Produced by: BRIEF-0108-B   Consumed by: BRIEF-0108-C

`src/world_engine/quest_reads.py` (reads only):
- `QUEST_STATE_LABELS = {"active": "en cours", "paused": "en cours",
  "completed": "accomplie", "failed": "échouée", "abandoned": "abandonnée"}`.
- `offer_dict(offer, db)`: `id, giver_entity_id, giver_name, title, summary,
  repeatable, status, eligibility: [req], steps: [{objective, cost, domain,
  requirements: [req]}]`, `req = {type, target_entity_id, target_key,
  threshold}`.
- `editor_choices(world_id, db)`: `givers, characters, locations, factions`
  (`{id, name}`), `facts` (`{id, text}`), `skills` (`{key, label}`: the four
  base domains, then the definitions), `offers` (`{id, title}`),
  `giver_types`.
- `available_offers(character, db)`: the open offers whose
  `acceptance_refusal` is None.
- `journee_payload(character, db)`: `{offers: [{offer_id, title, summary,
  giver_name, steps: [objective]}], quests: [{quest_id, offer_id, title,
  giver_name, summary, state, open, steps: [{order, objective, status,
  blocked: [French reason]}]}]}` -- `blocked` only for the active step. No
  `agenda_id` or `step_id` at any depth.
- `pinned_plan(quest_id, character, db) -> Agenda` (C-05).

`src/world_engine/cockpit/routes/quests.py`:

| route | body | success | refusal |
|---|---|---|---|
| `GET /api/quest-offers` | -- | 200 `[offer_dict]` | 400 no active world |
| `GET /api/quest-offers/choices` | -- | 200 `editor_choices` | 400 |
| `POST /api/quest-offers` | `OfferBody` | 201 `offer_dict` | 422 the writer's message |
| `PUT /api/quest-offers/{id}` | `OfferBody` | 200 `offer_dict` | 404 unknown, 422 |
| `GET /api/quests` | -- | 200 `journee_payload` | 400 not one player |
| `POST /api/quests/accept` | `{offer_id}` | 201 `journee_payload` | 404 unknown offer, 409 refusal |
| `POST /api/quests/{quest_id}/abandon` | -- | 200 `journee_payload` | 404 not his quest, 409 refusal |

`OfferBody = {giver_entity_id, title, summary?, repeatable=false,
status="open", eligibility: [req], steps: [{objective, cost, domain?,
requirements: [req]}]}`.

### C-05 — the pin (O1)
Produced by: BRIEF-0108-B   Consumed by: BRIEF-0108-C
`routes/day.py`: `class PlanDayBody(BaseModel): quest_id: Optional[str] =
None`; `plan_day(batch_id, body: Optional[PlanDayBody] = None, db)`. A
non-empty `body.quest_id` -> `quest_reads.pinned_plan(...)` is the selected
plan and `select_plan` is not called; otherwise unchanged. `pinned_plan`
raises `LookupError` (-> 404) when the quest is not the character's,
`ValueError` (-> 409) when its agenda is not `active`/`paused`. The
selected plan then goes through `_reconcile_and_finalize` unchanged.

## Context

With v2.17 in place (A), this brief makes quests happen: the creator saves offers, the player accepts one -- an agenda born `paused`, its steps and requirements copied, the player's plan of the day untouched (A1) -- pins a day to it (O1) or abandons it (N1). Every rule lives in the writers, so no route can skip one; the player's payloads name quests, never the agenda behind them.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. The generated `tooling/standards/DECISIONS_INDEX.md`
is not in the diff: regenerate it as listed.

1. Apply the embedded diff. It:
   - adds `status="active"` to `write_agenda` (`active` or `paused`; the guard for `active` only -- C-03, b-4);
   - creates `src/world_engine/writes/quests.py` (`write_quest_offer`, `acceptance_refusal`, `accept_quest`, `abandon_refusal`, `abandon_quest`, `offer_requirements`, `QUEST_GIVER_TYPES`, `OPEN_QUEST_STATUSES` -- C-03), exported by `writes`;
   - allow-lists `write_quest_offer` and `accept_quest` in `canon_write_policy.txt`, and names `write_quest_offer` in `single_canon_write.py`'s full-replace list;
   - creates `src/world_engine/quest_reads.py` (C-04);
   - creates `src/world_engine/cockpit/routes/quests.py` (C-04's seven routes) and registers it in `cockpit/app.py`;
   - in `routes/day.py`, adds `PlanDayBody` and the pin to `plan_day` (C-05; 990 lines after);
   - adds QB1-QB4 to `quests.py`;
   - appends the decision entry above the footer.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(quests): accept, pin and abandon a quest; the creator's offer routes (BRIEF-0108-b)`.

````diff
diff --git a/src/world_engine/cockpit/app.py b/src/world_engine/cockpit/app.py
index 7579d75..d978b06 100644
--- a/src/world_engine/cockpit/app.py
+++ b/src/world_engine/cockpit/app.py
@@ -66,6 +66,7 @@ from .routes import npc_agent as _routes_npc_agent
 from .routes import observation as _routes_observation
 from .routes import play as _routes_play
 from .routes import prompts as _routes_prompts
+from .routes import quests as _routes_quests
 from .routes import regions as _routes_regions
 from .routes import room_batch as _routes_room_batch
 from .routes import scene as _routes_scene
@@ -138,6 +139,7 @@ app.include_router(_routes_lore.router)
 app.include_router(_routes_lore_mentions.router)
 app.include_router(_routes_lore_choices.router)
 app.include_router(_routes_lore_write.router)
+app.include_router(_routes_quests.router)
 
 app.mount("/static", _FreshnessAwareStaticFiles(directory=_STATIC_DIR), name="static")
 
diff --git a/src/world_engine/cockpit/routes/day.py b/src/world_engine/cockpit/routes/day.py
index e52e482..3b73439 100644
--- a/src/world_engine/cockpit/routes/day.py
+++ b/src/world_engine/cockpit/routes/day.py
@@ -32,7 +32,7 @@ from fastapi import APIRouter, Depends, HTTPException
 from pydantic import BaseModel, Field
 from sqlmodel import Session, select
 
-from ... import day_plan_select, day_plans, day_rewrite
+from ... import day_plan_select, day_plans, day_rewrite, quest_reads
 from ...day_choice import choose
 from ...day_concordance import AmbiguousMention, ConcordanceResult, concord, emit_germs
 from ...day_extract import extract_factions, extract_persons, extract_places
@@ -626,8 +626,12 @@ def _record_refused_choices(world_id: str, pass_play_id: str, records: tuple[dic
         db.commit()
 
 
+class PlanDayBody(BaseModel):
+    quest_id: Optional[str] = None  # O1 (TICKET-0108): the quest this day advances
+
+
 @router.post("/api/day/{batch_id}/plan")
-def plan_day(batch_id: str, db: Session = Depends(get_session)) -> dict:
+def plan_day(batch_id: str, body: Optional[PlanDayBody] = None, db: Session = Depends(get_session)) -> dict:
     """Emit and persist a day plan (TICKET-0075, BRIEF-0075-b; extraction and
     concordance, BRIEF-0075-c; reconciliation, BRIEF-0075-f as corrected by
     AMENDMENT 1; dedicated plan selection, TICKET-0077/BRIEF-0077-c). ONE
@@ -642,7 +646,9 @@ def plan_day(batch_id: str, db: Session = Depends(get_session)) -> dict:
     the active one; `None` means the declaration opens something new, and
     the standing active plan (if any) is parked before a fresh one is
     emitted. `agenda_id`/`step_id` never appear in the response — the
-    player never sees the agenda (ticket Scope OUT)."""
+    player never sees the agenda (ticket Scope OUT). O1 (TICKET-0108): a
+    `quest_id` pins the day to that open quest's plan -- no selection call,
+    the reconciliation runs against it as against any selected plan."""
     world_id = _crud._world_id(db)
     pass_play = _load_plannable_day(batch_id, world_id, db)
     character = _resolve_player_character(world_id, db)
@@ -672,11 +678,16 @@ def plan_day(batch_id: str, db: Session = Depends(get_session)) -> dict:
     rendered, rewrite_row = _write_declaration_rewrite(world_id, pass_play, concordance_result, db)
     write_day_mention_choices(db, world_id=world_id, pass_play_id=pass_play.id, records=list(choice_records))
 
-    plans = day_plans.open_plans(character, db)
-    try:
-        selected = day_plan_select.select_plan(rendered, plans, db)
-    except LlmParseError as exc:
-        raise HTTPException(status_code=502, detail=f"plan selection failed: {exc}") from exc
+    if body is not None and body.quest_id:  # O1: the player pinned the quest; no selection call
+        try:
+            selected = quest_reads.pinned_plan(body.quest_id, character, db)
+        except (LookupError, ValueError) as exc:
+            raise HTTPException(status_code=404 if isinstance(exc, LookupError) else 409, detail=str(exc)) from exc
+    else:
+        try:
+            selected = day_plan_select.select_plan(rendered, day_plans.open_plans(character, db), db)
+        except LlmParseError as exc:
+            raise HTTPException(status_code=502, detail=f"plan selection failed: {exc}") from exc
     if selected is not None:
         result = _reconcile_and_finalize(character, pass_play, selected, concordance_result, rendered, db)
     else:
diff --git a/src/world_engine/cockpit/routes/quests.py b/src/world_engine/cockpit/routes/quests.py
new file mode 100644
index 0000000..e4c5a86
--- /dev/null
+++ b/src/world_engine/cockpit/routes/quests.py
@@ -0,0 +1,148 @@
+"""Quest routes (TICKET-0108, BRIEF-0108-B, contracts C-03 to C-05).
+
+The creator's offers (E1) -- creator CRUD, a sanctioned canon-write path:
+    GET  /api/quest-offers           every offer of the active world
+    GET  /api/quest-offers/choices   what the editor's pickers list
+    POST /api/quest-offers           create one offer
+    PUT  /api/quest-offers/{id}      save one offer (steps replaced whole)
+
+The player's quests (Journée):
+    GET  /api/quests                     the offers he may accept, his quests
+    POST /api/quests/accept              accept one offer (B1, A1)
+    POST /api/quests/{quest_id}/abandon  abandon one quest (N1)
+
+Every rule lives in `writes/quests.py` (what may be written) and
+`quest_reads.py` (what is shown); this module parses, maps a refusal to its
+status code, and commits. No response carries an agenda or step id.
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
+from ... import quest_reads
+from ...day_plan import PlanStep, RequirementSpec
+from ...db import get_session
+from ...models import Quest, QuestOffer
+from ...writes import abandon_quest, accept_quest, write_quest_offer
+from .. import crud as _crud
+from .day import _resolve_player_character
+
+router = APIRouter()
+
+
+class RequirementBody(BaseModel):
+    type: str
+    target_entity_id: Optional[str] = None
+    target_key: Optional[str] = None
+    threshold: Optional[int] = None
+
+
+class OfferStepBody(BaseModel):
+    objective: str
+    cost: int
+    domain: Optional[str] = None
+    requirements: list[RequirementBody] = Field(default_factory=list)
+
+
+class OfferBody(BaseModel):
+    giver_entity_id: str
+    title: str
+    summary: Optional[str] = None
+    repeatable: bool = False
+    status: str = "open"
+    eligibility: list[RequirementBody] = Field(default_factory=list)
+    steps: list[OfferStepBody] = Field(default_factory=list)
+
+
+class AcceptBody(BaseModel):
+    offer_id: str
+
+
+def _spec(req: RequirementBody) -> RequirementSpec:
+    return RequirementSpec(type=req.type, target_entity_id=req.target_entity_id or None,
+                           target_key=req.target_key or None, threshold=req.threshold)
+
+
+def _save_offer(body: OfferBody, offer: Optional[QuestOffer], world_id: str, db: Session) -> dict:
+    steps = [PlanStep(objective=s.objective, cost=s.cost, domain=s.domain or None,
+                      requirements=tuple(_spec(r) for r in s.requirements)) for s in body.steps]
+    try:
+        offer = write_quest_offer(
+            db, world_id=world_id, offer=offer, giver_entity_id=body.giver_entity_id, title=body.title,
+            summary=body.summary, repeatable=body.repeatable, status=body.status,
+            eligibility=[_spec(r) for r in body.eligibility], steps=steps,
+        )
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=422, detail=str(exc)) from exc
+    db.commit()
+    db.refresh(offer)
+    return quest_reads.offer_dict(offer, db)
+
+
+@router.get("/api/quest-offers")
+def list_offers(db: Session = Depends(get_session)) -> list[dict]:
+    world_id = _crud._world_id(db)
+    return [quest_reads.offer_dict(o, db) for o in quest_reads.world_offers(world_id, db)]
+
+
+@router.get("/api/quest-offers/choices")
+def offer_choices(db: Session = Depends(get_session)) -> dict:
+    return quest_reads.editor_choices(_crud._world_id(db), db)
+
+
+@router.post("/api/quest-offers", status_code=201)
+def create_offer(body: OfferBody, db: Session = Depends(get_session)) -> dict:
+    return _save_offer(body, None, _crud._world_id(db), db)
+
+
+@router.put("/api/quest-offers/{offer_id}")
+def save_offer(offer_id: str, body: OfferBody, db: Session = Depends(get_session)) -> dict:
+    world_id = _crud._world_id(db)
+    offer = db.get(QuestOffer, offer_id)
+    if offer is None or offer.world_id != world_id:
+        raise HTTPException(status_code=404, detail=f"quest offer {offer_id!r} not found")
+    return _save_offer(body, offer, world_id, db)
+
+
+@router.get("/api/quests")
+def journee_quests(db: Session = Depends(get_session)) -> dict:
+    character = _resolve_player_character(_crud._world_id(db), db)
+    return quest_reads.journee_payload(character, db)
+
+
+@router.post("/api/quests/accept", status_code=201)
+def accept(body: AcceptBody, db: Session = Depends(get_session)) -> dict:
+    world_id = _crud._world_id(db)
+    character = _resolve_player_character(world_id, db)
+    offer = db.get(QuestOffer, body.offer_id)
+    if offer is None or offer.world_id != world_id:
+        raise HTTPException(status_code=404, detail=f"quest offer {body.offer_id!r} not found")
+    try:
+        accept_quest(db, offer=offer, character=character)
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=409, detail=str(exc)) from exc
+    db.commit()
+    return quest_reads.journee_payload(character, db)
+
+
+@router.post("/api/quests/{quest_id}/abandon")
+def abandon(quest_id: str, db: Session = Depends(get_session)) -> dict:
+    world_id = _crud._world_id(db)
+    character = _resolve_player_character(world_id, db)
+    quest = db.get(Quest, quest_id)
+    if quest is None or quest.character_id != character.id:
+        raise HTTPException(status_code=404, detail=f"quest {quest_id!r} not found")
+    try:
+        abandon_quest(db, quest=quest)
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=409, detail=str(exc)) from exc
+    db.commit()
+    return quest_reads.journee_payload(character, db)
diff --git a/src/world_engine/quest_reads.py b/src/world_engine/quest_reads.py
new file mode 100644
index 0000000..4f38e6e
--- /dev/null
+++ b/src/world_engine/quest_reads.py
@@ -0,0 +1,170 @@
+"""Quest offers and quests: what the two surfaces read (TICKET-0108,
+BRIEF-0108-B, contract C-04). Reads only: this module never writes.
+
+Two audiences. The creator's offer editor (`offer_dict`, `editor_choices`)
+sees the offers whole. The player's Journée panel (`journee_payload`) sees
+the open offers he is eligible for (I1) and his quests: titles, giver,
+objectives and states -- never an agenda or step id (the agenda stays
+invisible, TICKET-0075's Scope OUT, kept for quests by Nia), so its dicts
+carry a `quest_id`, an `offer_id`, and nothing else that names a row.
+
+A quest's state is its agenda's (M1), worded by `QUEST_STATE_LABELS`.
+"""
+
+from __future__ import annotations
+
+from typing import Optional
+
+from sqlmodel import Session, select
+
+from .day_resolve import requirement_detail_fr
+from .day_plan import evaluate_agenda_step
+from .models import (
+    BASE_SKILL_DOMAINS,
+    Agenda,
+    AgendaStep,
+    Character,
+    Entity,
+    Fact,
+    Quest,
+    QuestOffer,
+    QuestOfferStep,
+    SkillDefinition,
+)
+from .prose_render import fact_texts
+from .writes.quests import QUEST_GIVER_TYPES, acceptance_refusal, offer_requirements
+
+# M1: the agenda's status, as the player reads it.
+QUEST_STATE_LABELS: dict[str, str] = {
+    "active": "en cours",
+    "paused": "en cours",
+    "completed": "accomplie",
+    "failed": "échouée",
+    "abandoned": "abandonnée",
+}
+
+
+def _requirement_dict(req) -> dict:
+    return {"type": req.type, "target_entity_id": req.target_entity_id, "target_key": req.target_key,
+            "threshold": req.threshold}
+
+
+def _name(db: Session, entity_id: Optional[str]) -> Optional[str]:
+    entity = db.get(Entity, entity_id) if entity_id else None
+    return entity.name if entity is not None else None
+
+
+def offer_dict(offer: QuestOffer, db: Session) -> dict:
+    """The creator's view of one offer: every field, its eligibility and its
+    steps with their requirements, in order."""
+    steps = db.exec(select(QuestOfferStep).where(QuestOfferStep.offer_id == offer.id)
+                    .order_by(QuestOfferStep.step_order)).all()
+    return {
+        "id": offer.id, "giver_entity_id": offer.giver_entity_id, "giver_name": _name(db, offer.giver_entity_id),
+        "title": offer.title, "summary": offer.summary, "repeatable": offer.repeatable, "status": offer.status,
+        "eligibility": [_requirement_dict(r) for r in offer_requirements(db, offer.id, None)],
+        "steps": [{
+            "objective": step.objective, "cost": step.cost, "domain": step.domain,
+            "requirements": [_requirement_dict(r) for r in offer_requirements(db, offer.id, step.id)],
+        } for step in steps],
+    }
+
+
+def world_offers(world_id: str, db: Session) -> list[QuestOffer]:
+    """Every offer of the world, open first, then by title."""
+    offers = db.exec(select(QuestOffer).where(QuestOffer.world_id == world_id)).all()
+    return sorted(offers, key=lambda o: (o.status != "open", o.title.lower(), o.id))
+
+
+def _named(db: Session, world_id: str, entity_type: str) -> list[dict]:
+    rows = db.exec(select(Entity).where(Entity.world_id == world_id, Entity.type == entity_type,
+                                        Entity.status == "active")).all()
+    return sorted(({"id": e.id, "name": e.name} for e in rows), key=lambda d: (d["name"].lower(), d["id"]))
+
+
+def editor_choices(world_id: str, db: Session) -> dict:
+    """What the offer editor's pickers list: givers, characters, locations,
+    factions, facts (their text), skills (base domains, then definitions)
+    and offers."""
+    facts = db.exec(select(Fact).where(Fact.world_id == world_id)).all()
+    definitions = db.exec(select(SkillDefinition).where(SkillDefinition.world_id == world_id)).all()
+    characters = _named(db, world_id, "character")
+    factions = _named(db, world_id, "faction")
+    return {
+        "givers": characters + factions,
+        "characters": characters,
+        "locations": _named(db, world_id, "location"),
+        "factions": factions,
+        "facts": sorted(({"id": f.id, "text": t} for f, t in zip(facts, fact_texts(db, facts))),
+                        key=lambda d: (d["text"].lower(), d["id"])),
+        "skills": [{"key": d, "label": d} for d in BASE_SKILL_DOMAINS]
+        + sorted(({"key": d.id, "label": d.name} for d in definitions), key=lambda d: d["label"].lower()),
+        "offers": [{"id": o.id, "title": o.title} for o in world_offers(world_id, db)],
+        "giver_types": list(QUEST_GIVER_TYPES),
+    }
+
+
+def available_offers(character: Character, db: Session) -> list[QuestOffer]:
+    """I1: the open offers of the world `character` may accept now."""
+    offers = db.exec(select(QuestOffer).where(QuestOffer.world_id == character.world_id,
+                                              QuestOffer.status == "open")).all()
+    return sorted((o for o in offers if acceptance_refusal(db, o, character) is None),
+                  key=lambda o: (o.title.lower(), o.id))
+
+
+def _steps_view(agenda: Agenda, character: Character, db: Session) -> list[dict]:
+    steps = db.exec(select(AgendaStep).where(AgendaStep.agenda_id == agenda.id)
+                    .order_by(AgendaStep.step_order)).all()
+    view = []
+    for step in steps:
+        blocked: list[str] = []
+        if step.status == "active":
+            evaluated = evaluate_agenda_step(step, character, db)
+            blocked = [requirement_detail_fr(v) for v in evaluated.verdicts if not v.met]
+        view.append({"order": step.step_order, "objective": step.objective, "status": step.status,
+                     "blocked": blocked})
+    return view
+
+
+def player_quests(character: Character, db: Session) -> list[dict]:
+    """The character's quests, open first then most recent: title, giver,
+    state, steps (the active one with what it still needs)."""
+    rows = db.exec(select(Quest, Agenda).join(Agenda, Agenda.id == Quest.agenda_id)
+                   .where(Quest.character_id == character.id)).all()
+    ordered = sorted(rows, key=lambda r: (QUEST_STATE_LABELS[r[1].status] != "en cours",
+                                          -r[0].accepted_at.timestamp(), r[0].id))
+    view = []
+    for quest, agenda in ordered:
+        offer = db.get(QuestOffer, quest.offer_id)
+        view.append({
+            "quest_id": quest.id, "offer_id": quest.offer_id, "title": agenda.title,
+            "giver_name": _name(db, offer.giver_entity_id) if offer is not None else None,
+            "summary": offer.summary if offer is not None else None,
+            "state": QUEST_STATE_LABELS[agenda.status], "open": agenda.status in ("active", "paused"),
+            "steps": _steps_view(agenda, character, db),
+        })
+    return view
+
+
+def journee_payload(character: Character, db: Session) -> dict:
+    """GET /api/quests (C-04): the offers the player may accept and his
+    quests. No agenda or step id (checked by `quests.py`)."""
+    offers = [{"offer_id": o.id, "title": o.title, "summary": o.summary,
+               "giver_name": _name(db, o.giver_entity_id),
+               "steps": [s.objective for s in db.exec(select(QuestOfferStep).where(
+                   QuestOfferStep.offer_id == o.id).order_by(QuestOfferStep.step_order)).all()]}
+              for o in available_offers(character, db)]
+    return {"offers": offers, "quests": player_quests(character, db)}
+
+
+def pinned_plan(quest_id: str, character: Character, db: Session) -> Agenda:
+    """O1 (C-05): the agenda of the character's OPEN quest `quest_id`, for a
+    day the player pinned to it. `LookupError` when no such quest is his,
+    `ValueError` when it is over."""
+    quest = db.get(Quest, quest_id) if quest_id else None
+    if quest is None or quest.character_id != character.id:
+        raise LookupError(f"quest {quest_id!r} not found for this character")
+    agenda = db.get(Agenda, quest.agenda_id)
+    if agenda is None or agenda.status not in ("active", "paused"):
+        raise ValueError("cette quête est terminée : elle ne peut plus être avancée")
+    return agenda
diff --git a/src/world_engine/writes/__init__.py b/src/world_engine/writes/__init__.py
index fd0b054..9098738 100644
--- a/src/world_engine/writes/__init__.py
+++ b/src/world_engine/writes/__init__.py
@@ -38,6 +38,10 @@ Layout, by canon domain:
     prompts.py          — `prompt_version`/`prompt_variable` (non-canon;
                           moved for module hygiene, not policy).
     pipeline.py         — `batch`/`pass_play` (TICKET-0075, BRIEF-0075-a).
+    quests.py           — `quest_offer`/`quest_offer_step`/
+                          `quest_offer_requirement`/`quest`:
+                          `write_quest_offer`, `accept_quest`,
+                          `abandon_quest` (TICKET-0108, BRIEF-0108-B).
     worlds.py           — `delete_world_cascade` (the sole delete-side
                           helper, wildcard-allowed in canon_write_policy.txt).
 
@@ -113,6 +117,16 @@ from .knowledge import (
     write_knowledge,
 )
 from .mentions import bind_mention, dismiss_mention, record_unresolved, resolve_mention
+from .quests import (
+    OPEN_QUEST_STATUSES,
+    QUEST_GIVER_TYPES,
+    abandon_quest,
+    abandon_refusal,
+    accept_quest,
+    acceptance_refusal,
+    offer_requirements,
+    write_quest_offer,
+)
 from .pipeline import (
     BATCH_RESOLVED_STATUS,
     BATCH_STATUSES,
diff --git a/src/world_engine/writes/goals_agendas.py b/src/world_engine/writes/goals_agendas.py
index e0bbe1d..7fac0a2 100644
--- a/src/world_engine/writes/goals_agendas.py
+++ b/src/world_engine/writes/goals_agendas.py
@@ -17,7 +17,7 @@ baselined.
   `active -> completed` and `active -> abandoned` — anything else (including
   reopening a closed goal) raises `ValueError`. Appends the previous state to
   `change_history` first (history is sacred).
-- `write_agenda(...)`                   : insert an `active` `agenda` row
+- `write_agenda(...)`                   : insert an `active` (or, for a quest, `paused`) `agenda` row
   (BRIEF-0018-a). A1 structural: `owner_entity_id` must resolve to an ACTIVE
   faction entity, else `ValueError`. The only constructor of `Agenda`.
 - `write_agenda_step(...)`              : insert one `agenda_step` row
@@ -249,9 +249,12 @@ def write_agenda(
     owner_entity_id: str,
     title: str,
     mutation_id: Optional[str] = None,
+    status: str = "active",
 ) -> Agenda:
     """Insert an `active` `agenda` row (TICKET-0018, BRIEF-0018-a; owner
-    unlock TICKET-0020, BRIEF-0020-a).
+    unlock TICKET-0020, BRIEF-0020-a) -- or a `paused` one (TICKET-0108,
+    BRIEF-0108-B, A1: an accepted quest is born parked, one open plan among
+    the player's, and displaces nothing). Any other `status` raises.
 
     The ONLY constructor of `Agenda` in gameplay code — both sanctioned
     canon-write paths (`_apply_mutation`'s `agenda_creation` branch and the
@@ -266,12 +269,14 @@ def write_agenda(
     `_apply_mutation` writers and is not otherwise used here.
     """
     del mutation_id
+    if status not in ("active", "paused"):
+        raise ValueError(f"write_agenda: an agenda is born 'active' or 'paused', got {status!r}")
     owner = db.get(Entity, owner_entity_id)
     if owner is None or owner.world_id != world_id:
         raise ValueError(f"write_agenda: owner {owner_entity_id!r} not found in world {world_id!r}")
     if owner.type not in ("faction", "character") or owner.status != "active":
         raise ValueError(f"write_agenda: owner {owner_entity_id!r} is not an active faction or character")
-    if owner.type == "character":
+    if owner.type == "character" and status == "active":
         existing = db.exec(
             select(Agenda).where(
                 Agenda.owner_entity_id == owner_entity_id,
@@ -285,7 +290,7 @@ def write_agenda(
         world_id=world_id,
         owner_entity_id=owner_entity_id,
         title=title,
-        status="active",
+        status=status,
         change_history=[],
     )
     db.add(agenda)
diff --git a/src/world_engine/writes/quests.py b/src/world_engine/writes/quests.py
new file mode 100644
index 0000000..fadd6c4
--- /dev/null
+++ b/src/world_engine/writes/quests.py
@@ -0,0 +1,231 @@
+"""Quest offers and quests: the writers (TICKET-0108, BRIEF-0108-B,
+contract C-03).
+
+- `write_quest_offer(...)` : create or save one offer, all or nothing. Its
+  steps and requirements are replaced whole (the `write_npc_prices`
+  full-replace shape, `DELETE FROM` scoped to the offer, then the submitted
+  set); the offer row snapshots its previous state into `change_history`.
+- `accept_quest(...)`      : the player takes an offer (B1, A1): one agenda
+  born `paused` through `write_agenda`, its steps (the first `active`, the
+  creator-agenda precedent) and their requirements copied from the offer,
+  and the `quest` row. Eligibility and L1 are judged HERE, so no caller can
+  skip them.
+- `abandon_quest(...)`     : N1, the quest's agenda to `abandoned` through
+  `write_agenda_status`; nothing is deleted.
+
+Every requirement goes through `goals_agendas._clean_requirement`, the same
+shape and target checks as a day plan's (B1: one language). None of these
+functions commits.
+"""
+
+from __future__ import annotations
+
+from datetime import UTC, datetime
+from typing import Optional
+
+from sqlalchemy import text
+from sqlalchemy.orm import attributes as sa_attrs
+from sqlmodel import Session, select
+
+from ..day_plan import MAX_PLAN_STEPS, PlanStep, RequirementSpec, evaluate_specs
+from ..models import (
+    BASE_SKILL_DOMAINS,
+    QUEST_OFFER_STATUSES,
+    Agenda,
+    AgendaStep,
+    AgendaStepRequirement,
+    Character,
+    Entity,
+    PassPlay,
+    ProposedMutation,
+    Quest,
+    QuestOffer,
+    QuestOfferRequirement,
+    QuestOfferStep,
+)
+from .goals_agendas import _clean_requirement, write_agenda, write_agenda_status, write_agenda_step
+
+# An offer is given by a character or a faction of the world (H1).
+QUEST_GIVER_TYPES: tuple[str, ...] = ("character", "faction")
+
+# The agenda statuses of a quest still open (M1): the others are over.
+OPEN_QUEST_STATUSES: tuple[str, ...] = ("active", "paused")
+
+
+def _clean_offer_steps(db: Session, world_id: str, steps: list[PlanStep]) -> list[tuple[PlanStep, list[dict]]]:
+    if not 1 <= len(steps) <= MAX_PLAN_STEPS:
+        raise ValueError(f"write_quest_offer: an offer has 1 to {MAX_PLAN_STEPS} steps, got {len(steps)}")
+    clean: list[tuple[PlanStep, list[dict]]] = []
+    for index, step in enumerate(steps):
+        if not isinstance(step.objective, str) or not step.objective.strip():
+            raise ValueError(f"write_quest_offer: step {index} needs an objective")
+        if not isinstance(step.cost, int) or isinstance(step.cost, bool) or not 1 <= step.cost <= 4:
+            raise ValueError(f"write_quest_offer: step {index} has invalid cost {step.cost!r}")
+        if step.domain is not None and step.domain not in BASE_SKILL_DOMAINS:
+            raise ValueError(f"write_quest_offer: step {index} has invalid domain {step.domain!r}")
+        clean.append((step, [_clean_requirement(db, world_id, index, req) for req in step.requirements]))
+    return clean
+
+
+def _check_giver(db: Session, world_id: str, giver_entity_id: str) -> None:
+    giver = db.get(Entity, giver_entity_id) if giver_entity_id else None
+    if (giver is None or giver.world_id != world_id or giver.type not in QUEST_GIVER_TYPES
+            or giver.status != "active"):
+        raise ValueError(f"write_quest_offer: giver {giver_entity_id!r} is not an active character or faction")
+
+
+def _snapshot(offer: QuestOffer) -> None:
+    history = list(offer.change_history or [])
+    history.append({
+        "giver_entity_id": offer.giver_entity_id, "title": offer.title, "summary": offer.summary,
+        "repeatable": offer.repeatable, "status": offer.status,
+        "updated_at": offer.updated_at.isoformat() if offer.updated_at else None,
+    })
+    offer.change_history = history
+    sa_attrs.flag_modified(offer, "change_history")
+
+
+def write_quest_offer(
+    db: Session,
+    *,
+    world_id: str,
+    offer: Optional[QuestOffer],
+    giver_entity_id: str,
+    title: str,
+    summary: Optional[str],
+    repeatable: bool,
+    status: str,
+    eligibility: list[RequirementSpec],
+    steps: list[PlanStep],
+) -> QuestOffer:
+    """Create (`offer` None) or save one offer (C-03). Everything is
+    validated before the first write; a `quest_completed` requirement on the
+    offer itself is refused (it could never be met)."""
+    if not isinstance(title, str) or not title.strip():
+        raise ValueError("write_quest_offer: title is required")
+    if status not in QUEST_OFFER_STATUSES:
+        raise ValueError(f"write_quest_offer: status must be one of {QUEST_OFFER_STATUSES}, got {status!r}")
+    _check_giver(db, world_id, giver_entity_id)
+    every = list(eligibility) + [req for step in steps for req in step.requirements]
+    if offer is not None and any(r.type == "quest_completed" and r.target_key == offer.id for r in every):
+        raise ValueError("write_quest_offer: an offer cannot require its own completion")
+    clean_eligibility = [_clean_requirement(db, world_id, -1, req) for req in eligibility]
+    clean_steps = _clean_offer_steps(db, world_id, steps)
+
+    if offer is None:
+        offer = QuestOffer(world_id=world_id, giver_entity_id=giver_entity_id, title=title.strip(), change_history=[])
+    else:
+        _snapshot(offer)
+        db.execute(text("DELETE FROM quest_offer_requirement WHERE offer_id = :oid"), {"oid": offer.id})
+        db.execute(text("DELETE FROM quest_offer_step WHERE offer_id = :oid"), {"oid": offer.id})
+    offer.giver_entity_id = giver_entity_id
+    offer.title = title.strip()
+    offer.summary = (summary or "").strip() or None
+    offer.repeatable = bool(repeatable)
+    offer.status = status
+    offer.updated_at = datetime.now(UTC)
+    db.add(offer)
+    db.flush()
+
+    for clean in clean_eligibility:
+        db.add(QuestOfferRequirement(world_id=world_id, offer_id=offer.id, step_id=None, **clean))
+    for order, (step, clean_requirements) in enumerate(clean_steps, start=1):
+        row = QuestOfferStep(world_id=world_id, offer_id=offer.id, step_order=order,
+                             objective=step.objective.strip(), cost=step.cost, domain=step.domain)
+        db.add(row)
+        db.flush()
+        for clean in clean_requirements:
+            db.add(QuestOfferRequirement(world_id=world_id, offer_id=offer.id, step_id=row.id, **clean))
+    return offer
+
+
+def offer_requirements(db: Session, offer_id: str, step_id: Optional[str]) -> tuple[RequirementSpec, ...]:
+    """An offer's eligibility (`step_id` None) or one step's requirements."""
+    condition = (QuestOfferRequirement.step_id.is_(None) if step_id is None
+                 else QuestOfferRequirement.step_id == step_id)
+    rows = db.exec(select(QuestOfferRequirement).where(
+        QuestOfferRequirement.offer_id == offer_id, condition).order_by(QuestOfferRequirement.id)).all()
+    return tuple(RequirementSpec(type=r.type, target_entity_id=r.target_entity_id, target_key=r.target_key,
+                                 threshold=r.threshold) for r in rows)
+
+
+def acceptance_refusal(db: Session, offer: QuestOffer, character: Character) -> Optional[str]:
+    """Why `character` cannot take `offer` now, or None (C-04): a closed
+    offer, an unmet eligibility requirement, or L1 -- a non-repeatable offer
+    already taken, a repeatable one still open."""
+    if offer.status != "open":
+        return "cette quête n'est plus proposée"
+    taken = db.exec(
+        select(Agenda.status).join(Quest, Quest.agenda_id == Agenda.id)
+        .where(Quest.offer_id == offer.id, Quest.character_id == character.id)
+    ).all()
+    if taken and not offer.repeatable:
+        return "quête déjà acceptée"
+    if any(status in OPEN_QUEST_STATUSES for status in taken):
+        return "quête déjà en cours"
+    unmet = [v for v in evaluate_specs(offer_requirements(db, offer.id, None), character, db) if not v.met]
+    if unmet:
+        return "; ".join(v.reason for v in unmet)
+    return None
+
+
+def accept_quest(db: Session, *, offer: QuestOffer, character: Character) -> Quest:
+    """B1/A1 (C-03): the agenda is born `paused`, never displacing the
+    player's active plan; its first step is `active`. Raises `ValueError`
+    with `acceptance_refusal`'s reason before any write."""
+    refusal = acceptance_refusal(db, offer, character)
+    if refusal is not None:
+        raise ValueError(refusal)
+    steps = db.exec(select(QuestOfferStep).where(QuestOfferStep.offer_id == offer.id)
+                    .order_by(QuestOfferStep.step_order)).all()
+    if not steps:
+        raise ValueError("accept_quest: the offer has no step")
+    copied = [(step, [_clean_requirement(db, offer.world_id, step.step_order, req)
+                      for req in offer_requirements(db, offer.id, step.id)]) for step in steps]
+
+    agenda = write_agenda(db, world_id=offer.world_id, owner_entity_id=character.id, title=offer.title,
+                          status="paused")
+    db.flush()
+    for step, clean_requirements in copied:
+        row = write_agenda_step(db, agenda_id=agenda.id, step_order=step.step_order, objective=step.objective,
+                                status="active" if step.step_order == 1 else "pending",
+                                cost=step.cost, domain=step.domain)
+        db.flush()
+        for clean in clean_requirements:
+            db.add(AgendaStepRequirement(world_id=offer.world_id, step_id=row.id, **clean))
+    quest = Quest(world_id=offer.world_id, offer_id=offer.id, character_id=character.id, agenda_id=agenda.id)
+    db.add(quest)
+    return quest
+
+
+def abandon_refusal(db: Session, quest: Quest) -> Optional[str]:
+    """Why the quest cannot be abandoned now, or None: it is over, a day is
+    resolving against it, or a step change of it awaits review (applying it
+    after the abandon would move an abandoned plan)."""
+    agenda = db.get(Agenda, quest.agenda_id)
+    if agenda is None or agenda.status not in OPEN_QUEST_STATUSES:
+        return "cette quête est terminée"
+    resolving = db.exec(select(PassPlay.id).where(
+        PassPlay.agenda_id == agenda.id, PassPlay.status == "resolving")).first()
+    if resolving is not None:
+        return "une journée est en cours de résolution sur cette quête"
+    # The `routes/day.py::_guard_no_pending_agenda_step_change` query (a
+    # proposal awaiting review is `status='proposed'`), restated here: that
+    # guard raises an HTTP error and lives in a route module.
+    step_ids = set(db.exec(select(AgendaStep.id).where(AgendaStep.agenda_id == agenda.id)).all())
+    pending = db.exec(select(ProposedMutation).where(
+        ProposedMutation.mutation_type == "agenda_step_change", ProposedMutation.status == "proposed",
+    )).all()
+    if any(isinstance(m.payload, dict) and m.payload.get("step_id") in step_ids for m in pending):
+        return "une étape de cette quête attend la revue"
+    return None
+
+
+def abandon_quest(db: Session, *, quest: Quest) -> Agenda:
+    """N1 (C-03): the agenda to `abandoned`; `ValueError` with
+    `abandon_refusal`'s reason before any write."""
+    refusal = abandon_refusal(db, quest)
+    if refusal is not None:
+        raise ValueError(refusal)
+    agenda = db.get(Agenda, quest.agenda_id)
+    return write_agenda_status(db, agenda=agenda, status="abandoned")
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index f7d97ac..d5277fa 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18077,6 +18077,39 @@ agenda_id`, the resolve guard and `active_plan` all assume one. A separate
 targeting vocabulary for eligibility (B2): a second language. Renaming
 `resource`: a data migration and a prompt change for a label.
 
+
+## A QUEST IS TAKEN, PINNED, ABANDONED (TICKET-0108) -- THE WRITERS JUDGE, THE PLAYER NEVER SEES THE AGENDA (BRIEF-0108-b, no schema change)
+
+**E1.** The creator authors offers from her own routes (`/api/quest-offers`,
+creator CRUD); `write_quest_offer` validates the whole offer -- giver,
+title, status, steps, every requirement through `_clean_requirement` --
+before its first write.
+
+**B1, A1, L1, I1.** `accept_quest` judges the offer itself (open,
+eligibility met, L1: a non-repeatable offer once per character, a
+repeatable one again only once the last quest taken from it is over), so
+no caller can skip the judgment; the Journée list (`available_offers`) is
+the same judgment, never a second one. The agenda is born `paused` through
+`write_agenda` (which now takes `status="paused"`), its first step
+`active` -- the creator-agenda precedent -- and the player's active plan is
+untouched.
+
+**O1.** `POST /api/day/{id}/plan` takes an optional `quest_id`: the day is
+pinned to that open quest's plan and no selection call is made; the
+reconciliation then runs against it as against any selected plan, so a
+`replace` verdict still parks it.
+
+**N1.** `abandon_quest` refuses while a day is resolving against the quest
+or a step change of it awaits review (applying it afterwards would move an
+abandoned plan); otherwise the agenda becomes `abandoned`, nothing deleted.
+
+**The agenda stays invisible.** The player's payload names a quest by
+`quest_id` and an offer by `offer_id`; no agenda or step id reaches it
+(`quests.py` QB4, the TICKET-0075 Scope OUT kept for quests).
+
+**Rejected.** Accepting through a mutation in the review queue: Nia is the
+one accepting; the queue would ask her to approve her own click.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index f5526fc..1991453 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -48,6 +48,10 @@ src/world_engine/writes/config.py::upsert_skill_rank           skill_rank
 src/world_engine/writes/zone_promotion.py::apply_promotion     item discoverable_detail
 # TICKET-0075, BRIEF-0075-b: write_day_plan is the 30th site — its OWN body writes agenda_step_requirement only (it calls write_agenda/write_agenda_step, whose own db.add sites are already allow-listed above; single_canon_write.py is function-scoped, not interprocedural).
 src/world_engine/writes/goals_agendas.py::write_day_plan       agenda_step_requirement
+# TICKET-0108, BRIEF-0108-B: write_quest_offer creates or saves one quest offer -- its steps and requirements replaced whole (the write_npc_prices full-replace shape), the offer row snapshotted; creator CRUD only.
+src/world_engine/writes/quests.py::write_quest_offer           quest_offer quest_offer_step quest_offer_requirement
+# TICKET-0108, BRIEF-0108-B: accept_quest writes the quest row and copies the offer's step requirements; its agenda and steps go through write_agenda/write_agenda_step, allow-listed above (the write_day_plan precedent).
+src/world_engine/writes/quests.py::accept_quest                agenda_step_requirement quest
 # TICKET-0044, BRIEF-0044-c: create_entity_type is the 26th site — the governed
 # structural-write authority (D2), a NEW sanctioned site distinct from the two
 # canon-write paths (AI-proposal pipeline, creator CRUD). Its `CREATE TABLE
diff --git a/tooling/verify/checks/quests.py b/tooling/verify/checks/quests.py
index 5acef3c..b5a6167 100644
--- a/tooling/verify/checks/quests.py
+++ b/tooling/verify/checks/quests.py
@@ -37,6 +37,36 @@ QA3 -- the evaluators (fixture). `relation_gte` reads what the target feels
    6, an unknown skill, an unknown quest offer, and accepts each form well
    aimed.
 
+QB1 -- the offer writer (BRIEF-0108-B, fixture). `write_quest_offer` refuses
+   a location as giver, an empty title, a status `draft`, no step, a cost of
+   5, a domain `magic`, a `faction_member` aimed at a character, and an
+   offer requiring its own completion -- each with no row written. A valid
+   offer writes its eligibility and its steps with their requirements;
+   saving it again replaces its steps and requirements whole (the old rows
+   gone) and appends one `change_history` entry.
+QB2 -- acceptance (fixture, B1, A1, L1). An unmet eligibility refuses with
+   no agenda written. Met: one agenda, `paused`, titled as the offer, the
+   player's active plan still `active`; its steps copied in order, the first
+   `active`, the others `pending`, with their requirements; one `quest` row.
+   The same non-repeatable offer is refused a second time; a repeatable one
+   is refused while its quest is open, accepted again once it is
+   `completed`; a `closed` offer is refused. `available_offers` lists
+   exactly the offers accepted would succeed for.
+QB3 -- abandon (fixture, N1). A quest with an `agenda_step_change` of its
+   step still `proposed` is refused; without it, its agenda becomes
+   `abandoned` (one more `change_history` entry, nothing deleted); a second
+   abandon is refused. `pinned_plan` (O1) returns the agenda of the player's
+   open quest, raises `LookupError` for another character's quest and
+   `ValueError` for an abandoned one. The non-repeatable offer, its quest
+   now over, is still neither available nor accepted (L1).
+QB4 -- what the player sees (fixture and static). `journee_payload` and the
+   route functions `journee_quests`, `accept`, `abandon` return no key
+   `agenda_id` or `step_id` at any depth; a quest's state reads `en cours`,
+   then `abandonnée`. Statically, `routes/quests.py` and `quest_reads.py`
+   build no dict literal with either key, and `plan_day` calls
+   `quest_reads.pinned_plan(` in the branch that does not call
+   `select_plan(`.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
@@ -409,6 +439,324 @@ def check_qa3(engine) -> None:
         _qa3_wording_and_cleaning(session, ids, pc)
 
 
+# --- QB --------------------------------------------------------------------------
+
+def _qb_world(session) -> dict:
+    from world_engine.models import Agenda, Character, Entity, Faction, World
+
+    world = World(name="Quests QB", is_active=False)
+    session.add(world)
+    session.flush()
+    ids = {"world": world.id}
+    for key, kind in (("pc", "player"), ("npc", "npc"), ("other", "npc")):
+        row = Entity(world_id=world.id, type="character", name=key.upper())
+        session.add(row)
+        session.flush()
+        session.add(Character(id=row.id, world_id=world.id, character_type=kind))
+        ids[key] = row.id
+    for key, kind in (("guild", "faction"), ("place", "location")):
+        row = Entity(world_id=world.id, type=kind, name=key.title())
+        session.add(row)
+        session.flush()
+        if kind == "faction":
+            session.add(Faction(id=row.id))
+        ids[key] = row.id
+    plan = Agenda(world_id=world.id, owner_entity_id=ids["pc"], title="Plan du jour", status="active",
+                  change_history=[])
+    session.add(plan)
+    session.commit()
+    ids["plan"] = plan.id
+    return ids
+
+
+def _offer_kwargs(ids: dict, **over) -> dict:
+    from world_engine.day_plan import PlanStep, RequirementSpec
+
+    steps = [
+        PlanStep(objective="Traquer le loup", cost=2, domain="perception",
+                 requirements=(RequirementSpec(type="has_met", target_entity_id=ids["npc"]),)),
+        PlanStep(objective="Rapporter la fourrure", cost=1, domain=None),
+    ]
+    base = dict(world_id=ids["world"], offer=None, giver_entity_id=ids["npc"], title="La fourrure",
+                summary="Le chasseur veut la fourrure.", repeatable=False, status="open",
+                eligibility=[RequirementSpec(type="faction_member", target_entity_id=ids["guild"])], steps=steps)
+    base.update(over)
+    return base
+
+
+def _counts(session) -> tuple:
+    from sqlmodel import func, select
+
+    from world_engine.models import Agenda, Quest, QuestOffer, QuestOfferRequirement, QuestOfferStep
+
+    return tuple(session.exec(select(func.count()).select_from(m)).one()
+                 for m in (QuestOffer, QuestOfferStep, QuestOfferRequirement, Quest, Agenda))
+
+
+def _qb1_refusals(session, ids) -> None:
+    from world_engine.day_plan import PlanStep, RequirementSpec
+    from world_engine.writes import write_quest_offer
+
+    bad = (
+        {"giver_entity_id": ids["place"]}, {"title": "  "}, {"status": "draft"}, {"steps": []},
+        {"steps": [PlanStep(objective="o", cost=5, domain=None)]},
+        {"steps": [PlanStep(objective="o", cost=1, domain="magic")]},
+        {"eligibility": [RequirementSpec(type="faction_member", target_entity_id=ids["npc"])]},
+    )
+    for over in bad:
+        before = _counts(session)
+        try:
+            write_quest_offer(session, **_offer_kwargs(ids, **over))
+        except ValueError:
+            session.rollback()
+            if _counts(session) != before:
+                fail(f"QB1: a refused offer {over} wrote rows")
+            continue
+        session.rollback()
+        fail(f"QB1: write_quest_offer accepts {over}")
+
+
+def check_qb1(session, ids) -> None:
+    from sqlmodel import select
+
+    from world_engine.day_plan import PlanStep, RequirementSpec
+    from world_engine.models import QuestOfferRequirement, QuestOfferStep
+    from world_engine.writes import write_quest_offer
+
+    _qb1_refusals(session, ids)
+    offer = write_quest_offer(session, **_offer_kwargs(ids))
+    session.commit()
+    ids["offer"] = offer.id
+    steps = session.exec(select(QuestOfferStep).where(QuestOfferStep.offer_id == offer.id)).all()
+    reqs = session.exec(select(QuestOfferRequirement).where(QuestOfferRequirement.offer_id == offer.id)).all()
+    if [s.step_order for s in sorted(steps, key=lambda s: s.step_order)] != [1, 2] or len(reqs) != 2:
+        fail(f"QB1: a new offer wrote {len(steps)} step(s), {len(reqs)} requirement(s)")
+    try:
+        write_quest_offer(session, **_offer_kwargs(ids, offer=offer, eligibility=[
+            RequirementSpec(type="quest_completed", target_key=offer.id)]))
+        fail("QB1: an offer requiring its own completion was saved")
+    except ValueError:
+        session.rollback()
+    old_ids = {s.id for s in steps}
+    write_quest_offer(session, **_offer_kwargs(ids, offer=offer, steps=[PlanStep(objective="Seule", cost=1, domain=None)]))
+    session.commit()
+    after = session.exec(select(QuestOfferStep).where(QuestOfferStep.offer_id == offer.id)).all()
+    if len(after) != 1 or {s.id for s in after} & old_ids or len(offer.change_history) != 1:
+        fail(f"QB1: a save left {len(after)} step(s), history {len(offer.change_history)}")
+    write_quest_offer(session, **_offer_kwargs(ids, offer=offer))
+    session.commit()
+
+
+def _accept_refused(session, offer, pc, label: str) -> None:
+    from world_engine.writes import accept_quest
+
+    before = _counts(session)
+    try:
+        accept_quest(session, offer=offer, character=pc)
+    except ValueError:
+        session.rollback()
+        if _counts(session) != before:
+            fail(f"QB2: a refused acceptance ({label}) wrote rows")
+        return
+    session.rollback()
+    fail(f"QB2: accept_quest accepts {label}")
+
+
+def _qb2_accepted(session, ids, quest) -> None:
+    from sqlmodel import select
+
+    from world_engine.models import Agenda, AgendaStep, AgendaStepRequirement
+
+    agenda = session.get(Agenda, quest.agenda_id)
+    if agenda is None or agenda.status != "paused" or agenda.title != "La fourrure":
+        fail(f"QB2: the quest's agenda is {agenda}")
+        return
+    if session.get(Agenda, ids["plan"]).status != "active":
+        fail("QB2: accepting a quest displaced the active plan")
+    steps = sorted(session.exec(select(AgendaStep).where(AgendaStep.agenda_id == agenda.id)).all(),
+                   key=lambda s: s.step_order)
+    if [(s.objective, s.status, s.cost) for s in steps] != [
+            ("Traquer le loup", "active", 2), ("Rapporter la fourrure", "pending", 1)]:
+        fail(f"QB2: the copied steps are {[(s.objective, s.status, s.cost) for s in steps]}")
+    reqs = session.exec(select(AgendaStepRequirement).where(AgendaStepRequirement.step_id == steps[0].id)).all()
+    if [(r.type, r.target_entity_id) for r in reqs] != [("has_met", ids["npc"])]:
+        fail(f"QB2: the copied requirements are {[(r.type, r.target_entity_id) for r in reqs]}")
+
+
+def check_qb2(session, ids) -> None:
+    from world_engine.models import Agenda, Character, FactionMembership, QuestOffer
+    from world_engine.quest_reads import available_offers
+    from world_engine.writes import accept_quest, write_quest_offer
+
+    pc = session.get(Character, ids["pc"])
+    offer = session.get(QuestOffer, ids["offer"])
+    if available_offers(pc, session):
+        fail("QB2: an offer whose eligibility is unmet is available")
+    _accept_refused(session, offer, pc, "an unmet eligibility")
+    session.add(FactionMembership(world_id=ids["world"], entity_id=ids["pc"], faction_id=ids["guild"]))
+    session.commit()
+    if [o.id for o in available_offers(pc, session)] != [offer.id]:
+        fail("QB2: the eligible offer is not available")
+    try:
+        quest = accept_quest(session, offer=offer, character=pc)
+    except ValueError as exc:
+        session.rollback()
+        fail(f"QB2: an eligible offer was refused: {exc}")
+        return
+    session.commit()
+    ids["quest"] = quest.id
+    _qb2_accepted(session, ids, quest)
+    if available_offers(pc, session):
+        fail("QB2: an offer already taken is still available")
+    _accept_refused(session, offer, pc, "a non-repeatable offer taken twice")
+
+    errand = write_quest_offer(session, **_offer_kwargs(ids, title="Bois", repeatable=True, eligibility=[]))
+    session.commit()
+    first = accept_quest(session, offer=errand, character=pc)
+    session.commit()
+    _accept_refused(session, errand, pc, "a repeatable offer still open")
+    done = session.get(Agenda, first.agenda_id)
+    done.status = "completed"
+    session.add(done)
+    session.commit()
+    accept_quest(session, offer=errand, character=pc)
+    session.commit()
+    closed = write_quest_offer(session, **_offer_kwargs(ids, title="Fermée", status="closed", eligibility=[]))
+    session.commit()
+    _accept_refused(session, closed, pc, "a closed offer")
+
+
+def check_qb3(session, ids) -> None:
+    from sqlmodel import select
+
+    from world_engine.models import Agenda, AgendaStep, Character, ProposedMutation, Quest, QuestOffer
+    from world_engine.quest_reads import available_offers, pinned_plan
+    from world_engine.writes import abandon_quest
+
+    quest = session.get(Quest, ids["quest"])
+    pc, other = session.get(Character, ids["pc"]), session.get(Character, ids["other"])
+    if pinned_plan(quest.id, pc, session).id != quest.agenda_id:
+        fail("QB3: pinned_plan does not return the open quest's agenda")
+    try:
+        pinned_plan(quest.id, other, session)
+        fail("QB3: pinned_plan returns another character's quest")
+    except LookupError:
+        pass
+    step = session.exec(select(AgendaStep).where(AgendaStep.agenda_id == quest.agenda_id,
+                                                 AgendaStep.status == "active")).first()
+    proposal = ProposedMutation(world_id=ids["world"], source_type="pass_play", mutation_type="agenda_step_change",
+                                payload={"step_id": step.id, "action": "complete"}, status="proposed")
+    session.add(proposal)
+    session.commit()
+    try:
+        abandon_quest(session, quest=quest)
+        fail("QB3: a quest with a step change awaiting review was abandoned")
+    except ValueError:
+        session.rollback()
+    proposal.status = "rejected"
+    session.add(proposal)
+    session.commit()
+    agenda = session.get(Agenda, quest.agenda_id)
+    history = len(agenda.change_history)
+    if agenda.status == "paused":
+        abandon_quest(session, quest=quest)
+        session.commit()
+    if agenda.status != "abandoned" or len(agenda.change_history) != history + 1:
+        fail(f"QB3: the abandoned agenda is {agenda.status}, history {len(agenda.change_history)}")
+    # L1, the quest now over: a non-repeatable offer is still never taken twice.
+    if ids["offer"] in {o.id for o in available_offers(pc, session)}:
+        fail("QB3: a non-repeatable offer whose quest is over is available again")
+    _accept_refused(session, session.get(QuestOffer, ids["offer"]), pc, "a non-repeatable offer after its quest")
+    try:
+        abandon_quest(session, quest=quest)
+        fail("QB3: a quest was abandoned twice")
+    except ValueError:
+        session.rollback()
+    try:
+        pinned_plan(quest.id, pc, session)
+        fail("QB3: pinned_plan returns an abandoned quest")
+    except ValueError:
+        pass
+
+
+def _keys(value) -> set:
+    if isinstance(value, dict):
+        return set(value) | {k for v in value.values() for k in _keys(v)}
+    if isinstance(value, list):
+        return {k for v in value for k in _keys(v)}
+    return set()
+
+
+def _dict_literal_keys(path: pathlib.Path) -> set:
+    import ast
+
+    tree = ast.parse(path.read_text(encoding="utf-8"))
+    return {k.value for n in ast.walk(tree) if isinstance(n, ast.Dict)
+            for k in n.keys if isinstance(k, ast.Constant)}
+
+
+def _pin_branch_ok() -> bool:
+    import ast
+
+    tree = ast.parse((ROOT / "src" / "world_engine" / "cockpit" / "routes" / "day.py").read_text(encoding="utf-8"))
+    plan = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "plan_day"), None)
+    for node in ast.walk(plan) if plan is not None else ():
+        if isinstance(node, ast.If):
+            pinned = ast.unparse(ast.Module(body=node.body, type_ignores=[]))
+            other = ast.unparse(ast.Module(body=node.orelse, type_ignores=[]))
+            if "quest_reads.pinned_plan(" in pinned and "select_plan(" not in pinned and "select_plan(" in other:
+                return True
+    return False
+
+
+def check_qb4(session, ids) -> None:
+    from world_engine.models import Character, World
+    from world_engine.quest_reads import journee_payload
+
+    payload = journee_payload(session.get(Character, ids["pc"]), session)
+    states = [q["state"] for q in payload["quests"]]
+    if not payload["quests"] or "abandonnée" not in states or "en cours" not in states:
+        fail(f"QB4: the quest states are {states}")
+    from sqlmodel import select
+
+    for world in session.exec(select(World).where(World.is_active == True)).all():  # noqa: E712
+        world.is_active = False
+        session.add(world)
+    session.flush()
+    ours = session.get(World, ids["world"])
+    ours.is_active = True
+    session.add(ours)
+    session.commit()
+    from world_engine.cockpit.routes import quests as routes
+
+    seen = [payload, routes.journee_quests(db=session)]
+    if seen[1].get("quests") is None:
+        fail("QB4: GET /api/quests returned no quests")
+    leaked = {"agenda_id", "step_id"} & set().union(*(_keys(v) for v in seen))
+    if leaked:
+        fail(f"QB4: the player's payload carries {sorted(leaked)}")
+    for path in (ROOT / "src" / "world_engine" / "cockpit" / "routes" / "quests.py",
+                 ROOT / "src" / "world_engine" / "quest_reads.py"):
+        found = {"agenda_id", "step_id"} & _dict_literal_keys(path)
+        if found:
+            fail(f"QB4: {path.name} builds a dict with {sorted(found)}")
+    if not _pin_branch_ok():
+        fail("QB4: plan_day does not call quest_reads.pinned_plan( apart from select_plan(")
+
+
+def check_qb(engine) -> None:
+    from sqlmodel import Session
+
+    with Session(engine) as session:
+        ids = _qb_world(session)
+        check_qb1(session, ids)
+        check_qb2(session, ids)
+        if "quest" not in ids:  # QB2 already failed: no quest to abandon or show
+            return
+        check_qb3(session, ids)
+        check_qb4(session, ids)
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_qa1()
@@ -416,13 +764,17 @@ def main() -> int:
     from world_engine.db import create_db_and_tables, engine
     create_db_and_tables()
     check_qa3(engine)
+    check_qb(engine)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
         return 1
     print("PASS: quests -- v2.17 widens the requirement vocabulary to eight forms the model "
           "emits only four of, shared byte for byte by quest offers, migrates from v2.16 only, "
-          "and judges what the target feels, encounters, memberships, ranks and completed quests")
+          "and judges what the target feels, encounters, memberships, ranks and completed quests; "
+          "an offer is validated whole and saved whole, accepted only when eligible as a paused "
+          "plan with its steps, once unless repeatable, abandoned unless a step awaits review, "
+          "pinned to a day, and shown to the player without an agenda or step id")
     return 0
 
 
diff --git a/tooling/verify/checks/single_canon_write.py b/tooling/verify/checks/single_canon_write.py
index 5b50e7d..dd42503 100644
--- a/tooling/verify/checks/single_canon_write.py
+++ b/tooling/verify/checks/single_canon_write.py
@@ -77,11 +77,13 @@ and `write_faction_role(mode="delete")` (blocked while an active membership
 holds the role) — creator-CRUD-only, never reachable from any AI or play
 path. Full-replace config deletes (whole-set replace, not
 single-row correction): `write_npc_prices`, `write_world_laws`,
-`write_location_obstacles`, and `write_location_doors` each `DELETE FROM`
-their table(s) scoped to one parent (NPC / world / location / location)
-then re-insert the submitted set, in one transaction — creator-CRUD and
-world-bootstrap only (`set_npc_prices`, `create_world`,
-`set_location_geometry`, `set_location_doors`; `location_subculture` and
+`write_location_obstacles`, `write_location_doors` and `write_quest_offer`
+(TICKET-0108, BRIEF-0108-B: an offer's steps and requirements) each
+`DELETE FROM` their table(s) scoped to one parent (NPC / world / location /
+location / offer) then re-insert the submitted set, in one transaction —
+creator-CRUD and world-bootstrap only (`set_npc_prices`, `create_world`,
+`set_location_geometry`, `set_location_doors`, `save_offer`;
+`location_subculture` and
 its writer were dropped in schema v2.06, TICKET-0091, BRIEF-0091-I), never
 reachable from any AI or play path. These
 tables carry no `change_history` by design (metadata-config category);
````

## Scope OUT

- The surfaces (C): no frontend file changes here.
- An offer delete route (offers are closed, never deleted).
- Accepting through a mutation in the review queue (rejected, D2's reasoning).
- Costs and rewards applied at acceptance or completion; « déclarer accomplie » (TICKET-0109).
- A guard on the agenda's status in `_mutation_apply_agenda_step_change` (R-15): the abandon refuses instead; a general guard is its own change.
- Naming a `has_met` target as the day's rendezvous (R-11).
- Moving `_guard_no_pending_agenda_step_change` out of `routes/day.py` to share it (R-16: restated, reported).
- Every later brief of this lot.

## Invariants to defend

**Two canon-write paths:** the offer routes are creator CRUD; acceptance and abandon are creator-direct writes from Journée, through `writes/quests.py`, allow-listed by function. **The one-active-agenda rule:** unchanged -- an accepted quest is born `paused`, the guard still runs for every `active` birth. **History is sacred:** an offer save snapshots the offer; an abandon appends to the agenda's `change_history`; nothing is deleted but an offer's steps and requirements on a save (the named full-replace exception). **The player never sees the agenda:** QB4 checks the payloads and the new modules.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `routes/day.py` is not exactly 990 lines after the commit.
- Any existing caller of `write_agenda` would now create something other than an `active` agenda.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing).
- `pyflakes` reporting `VetoVerdict` imported but unused in `routes/day.py` (pre-existing).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/quests.py` -> `PASS: quests -- v2.17 widens the requirement vocabulary to eight forms the model emits only four of, shared byte for byte by quest offers, migrates from v2.16 only, and judges what the target feels, encounters, memberships, ranks and completed quests; an offer is validated whole and saved whole, accepted only when eligible as a paused plan with its steps, once unless repeatable, abandoned unless a step awaits review, pinned to a day, and shown to the player without an agenda or step id`.
- `single_canon_write.py`, `day_mutations.py`, `day_plan.py`, `module_budget.py`, `function_length.py`, `undefined_names.py`, `world_cascade.py`, `pipeline_state.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted, in `writes/quests.py`: in `accept_quest`, `                          status="paused")` -> `                          status="active")` -> `QB2`; in `acceptance_refusal`, `    if taken and not offer.repeatable:` -> `    if False:` -> `QB2` and `QB3`; in `abandon_refusal`, `    if any(isinstance(m.payload, dict) and m.payload.get("step_id") in step_ids for m in pending):` -> `    if False:` -> `QB3`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 141/141.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `A QUEST IS TAKEN, PINNED, ABANDONED (TICKET-0108) -- THE WRITERS JUDGE, THE PLAYER NEVER SEES THE AGENDA (BRIEF-0108-b, no schema change)`; `single_canon_write.py`'s full-replace list — all in the diff. No schema change, no CLAUDE.md change.
