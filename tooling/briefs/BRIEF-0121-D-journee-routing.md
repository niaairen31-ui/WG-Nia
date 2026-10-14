<!-- slug: journee-routing -->
# BRIEF 0121-D — "Journée routes a declaration to a quest -- the selection's third answer, blocked and unanchored steps open requests, the inquiry band (K1, K1b, R1, T1; no schema change)"

Lot: LOT-0121-journee-quest-designer.md (authoritative on conflict)
Depends on: BRIEF-0121-B (`open_request`, `inquiry_step_ids`, the trigger constants)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0121-B).

- `src/world_engine/cockpit/routes/day.py` -> `def _feasibility_dict(` (one caller outside `_finalize_plan`, in the day read route), `def _plan_step_dict(`, `def _finalize_plan(` with the call order `anchor_requirements` -> `evaluate_requirements` -> `budget_cut` -> `feasibility_veto` -> `write_day_plan` -> `write_day_feasibility`; the file at 991 lines (`wc -l`), 28 functions.
- `src/world_engine/cockpit/routes/day.py` -> in `plan_day`: `selected = day_plan_select.select_plan(rendered, day_plans.open_plans(character, db), db)`, then `if selected is not None:` ... `else:` `day_plans.park_active_plan(character, db)` / `raw_steps = emit_plan(rendered, character, db)` / `result = _finalize_plan(...)`.
- `src/world_engine/cockpit/day_reconcile_apply.py` -> `result = _day._finalize_plan(world_id, character, pass_play, raw_steps, db)` in `_finalize_replace`.
- `src/world_engine/day_plan_select.py:75` -> `def select_plan(declaration: str, plans: list[Agenda], db: Session) -> Optional[Agenda]:` with `if not plans: return None` first.
- `scripts/seed_pilot.py:2618` -> `DAY_PLAN_SELECT_SYSTEM_PROMPT` containing `- "rationale" : une phrase courte justifiant ton choix.` and `{"selected":<entier ou null>,"rationale":"<...>"}`.
- `src/world_engine/day_resolve.py:190` -> `BLOCKED_BAND: str = "blocked"`; `_roll_included_steps` (`if evaluated.step.domain is None:` -> `band = "success"`); `_truncate_on_failure` (`if item.band == "failure": break`).
- `src/world_engine/day_narration.py:64` -> `BAND_MARKERS` with four keys; `:71` `BAND_LABELS_FR` with four keys.
- `src/world_engine/day_mutations.py:306` -> `emit_mutations` looping `for outcome in outcomes:` / `for emitter in _EMITTERS.values():`.
- `tooling/verify/checks/day_narration.py` R13 -> « the four bands »; `day_feasibility.py` R4 and `day_plan.py` R27 read `_finalize_plan` from `DAY_ROUTE_FILE`.
- `src/world_engine/writes/quest_requests.py` -> `open_request`, `QUEST_REQUEST_TRIGGERS`; `src/world_engine/quest_requests.py` -> `inquiry_step_ids` (BRIEF-0121-B).
- No `src/world_engine/cockpit/day_plan_finalize.py`, no `tooling/verify/checks/journee_inquiry.py`.

## Facts carried

### R-09 — the plan finalizer and the route's budget [M]
Opened: `cockpit/routes/day.py:156-175` (`_feasibility_dict`), `:382` (`_plan_step_dict`), `:549-618` (`_finalize_plan`), `:634-704` (`plan_day`); `cockpit/day_reconcile_apply.py:181-207` (`_finalize_replace` calls `_day._finalize_plan`); `tooling/verify/checks/module_budget.py:57-59`; `tooling/verify/checks/day_feasibility.py:161-185` (R4); `day_plan.py:1072-1100` (R27).
Finding: `routes/day.py` is 991 lines (cap 1000), 28 functions (cap 40). `_finalize_plan` runs `anchor_requirements` -> `evaluate_requirements` -> `budget_cut` -> `feasibility_veto` -> blocked index -> `write_day_plan` -> `write_day_feasibility` -> `pass_play.status = "resolving"`, `agenda_id`. R4 and R27 read `_finalize_plan` from the route file by name.
Consequence: D first moves `_finalize_plan`, `_plan_step_dict` and `_feasibility_dict` to `cockpit/day_plan_finalize.py` (pure move, the `day_reconcile_apply.py` precedent) and points R4 and R27 at the new file.

### R-10 — the plan selection [M]
Opened: `day_plan_select.py:1-118`; `scripts/seed_pilot.py:2618-2642` (`DAY_PLAN_SELECT_SYSTEM_PROMPT`, `DAY_PLAN_SELECT_USER_TEMPLATE`), `:2770-2780` (head `pt-day-plan-select`); `prompt_registry.py:371-377`; `scripts/apply_ticket_0119_tick_prompt.py:1-100`.
Finding: `select_plan(declaration, plans, db) -> Optional[Agenda]` returns `None` WITHOUT a model call when `plans` is empty; otherwise one call answering `{"selected": <int or null>, "rationale": ...}`, the ordinal checked. The template's placeholders are `{plans}` and `{declaration}`. A prompt already on the live DB changes through a fragment script that writes a new `prompt_version` and keeps the creator's edits.
Consequence: K1 makes the call on every declaration, empty list included (`(aucun plan ouvert)`), and adds `"route"` to the answer; delivered by `apply_ticket_0121_select_prompt.py` (fragments in `seed_pilot`).

### R-11 — anchoring a knowledge gate [M]
Opened: `day_plan.py:204-220` (`_anchorable_facts`), `:222-245` (`anchor_requirements`), `:285-306` (`_validate_step`: `cost` 1..`DAY_BUDGET_SLOTS`, `domain` in `BASE_SKILL_DOMAINS`), `:337-346` (`_resolve_knowledge_codes`), `:349-408` (`emit_plan`, its call through `ollama_client.chat`).
Finding: a `knowledge` leaf is kept only when its fact is held, in the world, by an entity other than the character, on a row `is_secret == False`. Otherwise the LEAF is dropped -- the step stays, ungated -- and reported `{step_index, objective, target_key}`. A code the model invented stays as emitted and is dropped the same way.
Consequence: R1 -- the first step with a dropped leaf becomes the day's inquiry step and the plan stops there; a secret-only fact reaches the designer through this path.

### R-12 — resolving a day, bands and emitters [M]
Opened: `cockpit/routes/day.py:916-990` (`resolve_day`); `day_resolve.py:95-131` (`StepOutcome`, `StepFact`), `:190` (`BLOCKED_BAND`), `:211-235` (`_roll_included_steps`: `domain is None` -> band `success`), `:237-258` (`_truncate_on_failure`), `:349-390` (`_append_blocked_step`), `:392-426` (`resolve_steps`); `day_narration.py:64-73` (`BAND_MARKERS`, `BAND_LABELS_FR`); `day_mutations.py:114-124` (`_step_action`), `:233-281` (`_emit_new_knowledge`), `:294-321` (`_EMITTERS`, `emit_mutations`); `tooling/verify/checks/day_narration.py:567-615` (R13), `:479-520` (R11: `day_resolve.py` imports no agenda writer, adds and commits nothing); `tooling/verify/checks/day_mutations.py:1-70` (R7: no response of `routes/day.py` carries an agenda or step id).
Finding: `resolve_day` refuses without the character's active agenda. A no-roll step is `success`, so every emitter fires for it (an `agenda_step_change` « complete » among them). `_emit_new_knowledge` proposes a rumor-level lead on a blocked step's unmet `knowledge` verdict (kept, U1). R13 pins `BAND_MARKERS` to exactly four bands with `[BLOQUÉ]`.
Consequence: T1 adds a fifth band `inquiry`: no roll, no emitter, the walk stops after it, its step closed directly; R13 moves to five.

### R-13 — the agenda tables and their writers [M]
Opened: `models/config.py:71-100` (`AgendaStep`: CHECK `status IN ('pending','active','completed','failed')`, one active step per agenda); `models/canon.py:779-797` (`Agenda`: CHECK `status IN ('active','paused','completed','failed','abandoned')`); `writes/goals_agendas.py:289-325` (`write_agenda_step`), `:326-360` (`write_agenda_step_status`), `:532-560` (`write_agenda_status`), `:610-655` (`write_day_plan`); `canon_write_policy.txt:106-107`.
Finding: both status writers append the previous state to `change_history`; they are allow-listed write sites; `write_day_plan` writes one agenda, its steps, their prerequisites.
Consequence: the inquiry day is a one-step plan written by `write_day_plan`; the inquiry band closes its step with `write_agenda_step_status(..., "completed", outcome="inquiry")` and, when no open step remains, the agenda with `write_agenda_status(..., "completed")`.

### R-24 — how a DB-backed check builds its fixture [M]
Opened: `tooling/verify/checks/mutation_reviews.py:77-82` (`_fresh_db`), `:269-276` (`main`); `.claude/rules/verify-checks.md`.
Finding: `_fresh_db()` points `WORLD_ENGINE_DATABASE_URL` at a temp file and defaults `WORLD_ENGINE_ENV=test` before any `world_engine` import; `main` then imports `world_engine.models` (registering every table) and runs `SQLModel.metadata.create_all(engine)`; rows go through the real writers; failures collect in `FAILURES`; 15 s per check under `corpus_gate.py`.
Consequence: every new DB-backed check of this lot follows these two functions; a table missing from `create_all` means its model is not exported from `models/__init__.py`.


## Contracts

### C-02 — `quest_request` (v2.28) and its writer
Produced by: BRIEF-0121-B   Consumed by: D, E, G
Table `quest_request` in `models/pipeline.py`:
`id` TEXT PK; `world_id` FK world NOT NULL; `character_id` FK entity NOT NULL; `pass_play_id` FK pass_play NOT NULL; `agenda_step_id` FK agenda_step NOT NULL; `trigger` TEXT NOT NULL; `declaration` TEXT NOT NULL; `subject` TEXT NULL; `status` TEXT NOT NULL DEFAULT `'new'`; `existence_answer` TEXT NULL; `creator_text` TEXT NULL; `existing_entity_id` FK entity NULL; `lore_entry_id` FK lore_entry NULL; `mutation_id` FK proposed_mutation NULL; `offer_id` FK quest_offer NULL; `note` TEXT NULL; `created_at`, `updated_at` (`_created_ts()`); `change_history` JSON NOT NULL DEFAULT `'[]'`.
CHECKs: `ck_quest_request_trigger` `trigger IN ('route','blocked','dropped')`; `ck_quest_request_status` `status IN ('new','asking','writing_lore','proposed','covered','dropped')`; `ck_quest_request_answer` `existence_answer IS NULL OR existence_answer IN ('exists','absent','already')`.
Indexes: `idx_quest_request_world` (`world_id`, `created_at`); `idx_quest_request_step` UNIQUE (`agenda_step_id`): one request per step.
Constants in `writes/quest_requests.py`: `QUEST_REQUEST_TRIGGERS = ("route", "blocked", "dropped")`, `QUEST_REQUEST_STATUSES = ("new", "asking", "writing_lore", "proposed", "covered", "dropped")`, `EXISTENCE_ANSWERS = ("exists", "absent", "already")`, `QUEST_OFFER_CREATION = "quest_offer_creation"`, `DESIGNER_PRODUCER = "local_ai_quest_designer"`.
Writer:
- `open_request(db, *, world_id, character_id, pass_play_id, trigger, declaration, agenda_step_id) -> QuestRequest` -- `ValueError` on an unknown trigger, an empty declaration, a missing step; a step that already has a request returns that request unchanged (idempotent per step). Adds and flushes, never commits.
Reads in `src/world_engine/quest_requests.py`: `inquiry_step_ids(db, agenda_id) -> frozenset[str]` -- the `agenda_step_id`s of the requests on that agenda's steps whose trigger is `route` or `dropped`.
- `move_request(db, request, status, **fields) -> QuestRequest` -- appends `{status, updated_at, <every field it changes, before>}` to `change_history`, then sets `status`, `updated_at` and the given fields (only `subject`, `existence_answer`, `creator_text`, `existing_entity_id`, `lore_entry_id`, `mutation_id`, `offer_id`, `note`); `ValueError` on an unknown status, an unknown field, an answer outside `EXISTENCE_ANSWERS`. Never commits.
Status meanings: `new` -- waits for « Concevoir »; `asking` -- the subject is unknown, the existence question is shown; `writing_lore` -- answered `exists` or `absent`, the Lore panel is open for it; `proposed` -- a `quest_offer_creation` (`mutation_id`) exists; whether it was approved or rejected is that row's `status`, never a second column; `covered` -- an open offer already covers it (`offer_id`); `dropped` -- the creator set it aside. Re-design is allowed from `new`, `covered`, and `proposed` when its proposal is `rejected`; refused otherwise (C-12).

### C-06 — the plan selection's answer
Produced by: BRIEF-0121-D   Consumed by: `plan_day`
`day_plan_select.PlanSelection(agenda: Optional[Agenda], route: str)` with `route in PLAN_ROUTES = ("plan", "quest")`. `select_plan(declaration, plans, db) -> PlanSelection`: ALWAYS one model call; an empty `plans` renders `(aucun plan ouvert)`. Answer `{"selected": <int or null>, "route": "plan" | "quest", "rationale": "..."}`; `selected` non-null -> `PlanSelection(plans[selected-1], "plan")` whatever `route` says; null -> `PlanSelection(None, route)`; a missing or unknown `route` with `selected` null -> `LlmParseError` (never a silent default). Fragments `seed_pilot.DAY_PLAN_SELECT_FRAGMENTS_0121`, delivered by `scripts/apply_ticket_0121_select_prompt.py`.

### C-07 — the three openers of a request
Produced by: BRIEF-0121-D   Consumed by: (the request list)
In `cockpit/day_plan_finalize.py`:
- `finalize_inquiry_day(world_id, character, pass_play, rendered, db) -> dict` (K1): writes, through `write_day_plan`, a one-step plan titled like `_finalize_plan`'s title, its step `objective = "Se renseigner : " + <rendered first line, 180 chars>`, `cost = 1`, `domain = None`, no prerequisite, `active_step_index = 0`; opens `open_request(trigger="route", declaration=rendered, agenda_step_id=<the plan's one step>)`; records no feasibility entry; `pass_play.status = "resolving"`, `agenda_id`; commits; returns the `/plan` response with the one step and `"inquiry": true`.
- in `_finalize_plan`, after the blocked index: when a step is blocked on an unmet prerequisite (the existing `blocked_index`), `open_request(trigger="blocked", declaration=<that step's objective>, agenda_step_id=<its row>)` (K1b);
- in `_finalize_plan`, after anchoring and BEFORE `write_day_plan`: when `dropped` is non-empty, the first step index with a dropped leaf `k` becomes the inquiry step -- steps after `k` are NOT written (reported `inquiry_cut: <n>` in the response); the plan is written with `k`'s requirements as anchored; `open_request(trigger="dropped", declaration=<k's objective>, agenda_step_id=<k's row>)` (R1). A blocked index before `k` keeps its existing meaning and also opens its `blocked` request.
Every opener runs after `write_day_plan`, reading the written step rows by `agenda_id` and `step_order`. `resolve_steps` reads the inquiry steps through `quest_requests.inquiry_step_ids` (C-02).

### C-08 — the `inquiry` band
Produced by: BRIEF-0121-D   Consumed by: narration, emitters
`day_resolve.INQUIRY_BAND = "inquiry"`. `resolve_steps` gives an included step whose id is in `inquiry_step_ids(db, agenda.id)` the band `inquiry` (no roll, `verdict=None`) and stops the walk after it (like `failure`). `BAND_MARKERS["inquiry"] = "[RECHERCHE]"`; `BAND_LABELS_FR["inquiry"] = "recherche en cours, sans réponse encore"`. `emit_mutations` skips an `inquiry` outcome (no emitter runs). `_finalize_resolution` closes each `inquiry` outcome's step: `write_agenda_step_status(step, "completed", outcome="inquiry")`, then `write_agenda_status(agenda, "completed")` when the agenda has no `pending`/`active` step left -- direct writes, in the resolution's transaction (T1: a decision of 0121, not a proposal; V1 of 0075 keeps every other step transition). A replay finds the step `completed` and does not walk it again (`_load_evaluated_steps` excludes terminal steps).


## Context

K1, K1b, R1, T1: a declaration that seeks something a day cannot give is
spent searching -- a one-step plan narrated as a search, no dice, nothing
proposed -- and a quest request is born on the creator's side. A step
blocked on an unmet prerequisite opens one too; a knowledge the planner
cannot anchor stops the plan there. The player is never told a quest is
being prepared (J2-a1): the narrator reads the declaration only.

## Scope IN

**Commit 1 -- pure move (no behaviour change).**

1. Create `src/world_engine/cockpit/day_plan_finalize.py` holding `_feasibility_dict`, `_plan_step_dict` and `_finalize_plan`, byte-identical, with the imports they need and a docstring « relocated from `routes/day.py` for module-budget headroom (TICKET-0121, BRIEF-0121-D) -- the `day_reconcile_apply.py` precedent ». `routes/day.py` imports the three names from it; `day_reconcile_apply._finalize_replace` imports `_finalize_plan` from it (its docstring's « stays in `routes/day.py` » corrected).
2. `day_feasibility.py` R4 and `day_plan.py` R27: a constant `DAY_FINALIZE_FILE` naming the new file, used where they locate `_finalize_plan`; their docstrings say so. No rule weakened.
3. Proof in the commit message: the three function bodies diff-identical (`git diff --color-moved`), `routes/day.py` line count before and after.

**Commit 2 -- the selection's third answer (K1).**

4. `day_plan_select.py`: `PLAN_ROUTES = ("plan", "quest")`, the frozen dataclass `PlanSelection(agenda, route)`, and `select_plan` as C-06 -- the `if not plans: return None` shortcut removed; `_render_plans([])` returns `(aucun plan ouvert)`; the docstrings updated (K1, TICKET-0121).
5. `scripts/seed_pilot.py`: `DAY_PLAN_SELECT_FRAGMENTS_0121: tuple[tuple[str, str, str], ...]` -- `(target, old, new)`, the precedent of `CONDITION_INTERPRET_FRAGMENTS` -- with exactly two fragments on `system_prompt`:
   - old `- "rationale" : une phrase courte justifiant ton choix.` -> new
     this line, then a line break, then the unchanged rationale line:
     `- "route" : quand "selected" est null, ce que la déclaration ouvre : "quest" si le joueur cherche à obtenir ce qu'une journée d'activité ne suffit pas à lui donner (un savoir précis, une personne à trouver, un objet, un accès qu'il n'a pas), "plan" si c'est une activité qu'il peut mener aujourd'hui. Quand "selected" est un numéro, "route" vaut "plan".`
   - old `{"selected":<entier ou null>,"rationale":"<...>"}` -> new `{"selected":<entier ou null>,"route":"plan" ou "quest","rationale":"<...>"}`.
   The seeded head's text is the 0077 text with these fragments applied (a fresh seed gets them; `upsert_prompt_template` never rewrites an existing text).
6. `scripts/apply_ticket_0121_select_prompt.py`: the fragment delivery of `apply_ticket_0119_tick_prompt.py`, verbatim in shape, on head `pt-day-plan-select` (no variable change): new text found -> done; old found -> replaced; neither -> reported « edit by hand »; a changed text is a new `prompt_version`; « unchanged » on a re-run.
7. `routes/day.py::plan_day`: `selection = day_plan_select.select_plan(...)`; `if selection.agenda is not None:` the reconcile path unchanged; `elif selection.route == "quest":` `day_plans.park_active_plan(character, db)` then `result = finalize_inquiry_day(world_id, character, pass_play, rendered, db)`; `else:` the existing park / `emit_plan` / `_finalize_plan`. The pinned-quest path (O1) unchanged. The docstring gains one sentence (K1).

**Commit 3 -- openers and the inquiry band (K1b, R1, T1).**

8. `day_plan_finalize.py`: `finalize_inquiry_day` as C-07 (the title as `_finalize_plan` computes it; no veto, no feasibility entry; `"inquiry": true` and the single step in the response, built with `_plan_step_dict`).
9. `_finalize_plan`, as C-07: after `anchor_requirements`, when `dropped` is non-empty, `k = min(d["step_index"] for d in dropped)` and `anchored_steps = anchored_steps[: k + 1]`, `inquiry_cut = <steps removed>`; the evaluation, budget and veto run on the cut list; after `write_day_plan`, read the written steps (`select(AgendaStep).where(AgendaStep.agenda_id == agenda.id).order_by(AgendaStep.step_order)`) and open `dropped` on step k, `blocked` on `blocked_index`'s step when there is one. When k is 0 the plan is that one step, the inquiry step. The response gains `"inquiry_cut": <int>` (0 when nothing was cut). No id in the response (R7 of `day_mutations.py`).
10. `day_resolve.py`: `INQUIRY_BAND: str = "inquiry"`; `resolve_steps` reads `inquiry_step_ids(db, agenda.id)` once and passes it to `_roll_included_steps`, which gives such a step `verdict=None`, `band = INQUIRY_BAND`; `_truncate_on_failure` stops after `failure` OR `inquiry`. `_append_blocked_step` unchanged (an inquiry step is the last step of its plan, R1's cut, so no step is excluded after it). `day_resolve.py` still imports no writer (R11 of `day_narration.py`).
11. `day_narration.py`: `BAND_MARKERS[INQUIRY_BAND] = "[RECHERCHE]"`, `BAND_LABELS_FR[INQUIRY_BAND] = "recherche en cours, sans réponse encore"`. `day_narration.py` (the check) R13: « the five bands », `[BLOQUÉ]` and `[RECHERCHE]` asserted.
12. `day_mutations.py::emit_mutations`: `if outcome.band == INQUIRY_BAND: continue` before the emitter loop, with the comment `# T1 (TICKET-0121): an inquiry proposes nothing.`
13. `day_plan_finalize.py::close_inquiry_steps(outcomes, agenda, db) -> None` as C-08 (step `completed`, `outcome="inquiry"`; agenda `completed` when no `pending`/`active` step is left), called from `routes/day.py::_finalize_resolution` on the success path, before the mutations are added, never on the judge-failure path.
14. New check `tooling/verify/checks/journee_inquiry.py` (R-24's fixture; `world_engine.ollama_client.chat` replaced by a stub -- `select_plan` calls it as `ollama_client.chat`, R-10; rows through the real writers):
    - **JI1** `select_plan` with an empty list calls the model once and returns `PlanSelection(None, "quest")` for `{"selected": null, "route": "quest"}`; `{"selected": 1, "route": "quest"}` with one plan returns that plan, route `plan`; `{"selected": null}` raises `LlmParseError`.
    - **JI2** `finalize_inquiry_day`: one agenda, one step `Se renseigner : ...` with no domain and no condition, one request `route` on it, `pass_play.status == "resolving"`, `agenda_id` set; the response has `"inquiry": true` and no id.
    - **JI3** `_finalize_plan` on three steps whose second needs a knowledge no one holds non-secretly: the plan holds two steps, `inquiry_cut == 1`, one request `dropped` on step 2.
    - **JI4** `_finalize_plan` on two steps whose second needs to have met an NPC not met: two steps written, one request `blocked` on step 2; a second `_finalize_plan`-equivalent call for the same step opens nothing new.
    - **JI5** `resolve_steps` on JI3's plan: step 1 rolled, step 2 `inquiry`, nothing after; `emit_mutations` emits nothing for step 2; `close_inquiry_steps` marks step 2 `completed` with outcome `inquiry`, and the agenda `completed`.
    - **JI6** `BAND_MARKERS` and `BAND_LABELS_FR` have the same five keys; `assemble_beats` writes `[RECHERCHE]` for an inquiry step.
    - **JI7** static: `day_resolve.py` imports `inquiry_step_ids` and no writer; `routes/day.py` stays under `module_budget.py`'s caps.
15. `tooling/standards/ARCHITECTURE_DECISIONS.md`: entries above the footer, one per commit 2-3:
    `## JOURNÉE ROUTES A DECLARATION TO A QUEST (TICKET-0121) -- THE SELECTION'S THIRD ANSWER (BRIEF-0121-d, no schema change)` (K1, the call made on every declaration);
    `## A SEARCH IS A DAY WITHOUT DICE (TICKET-0121) -- THE INQUIRY BAND; BLOCKED AND UNANCHORED STEPS OPEN A REQUEST (BRIEF-0121-d, no schema change)` (K1b, R1 and its cut, T1 and why its step closes directly -- an exception to V1 of 0075 decided by Nia, nothing else -- U1: the blocked lead is kept). Regenerate `DECISIONS_INDEX.md` and `FILE_MAP.md`.

## Scope OUT

- The `modify`, `continue` and `resume` reconciliation paths: they open no request (drafting decision 2).
- The planner's forms (`MODEL_REQUIREMENT_TYPES`), its prompt, `emit_plan`.
- `_emit_new_knowledge`: unchanged (U1).
- Telling the player anything about the request (J2-a1): no field in a player response names it.
- Designing a request (E), the request panel (G).
- Every later brief of this lot.

## Invariants to defend

- **INV-02** -- the narrator's input: the inquiry step's objective is the player's own declaration; no request field, no lore the designer will read, reaches the fact sheet.
- **INV-11** -- commit before touching a canon-writing path: `close_inquiry_steps` writes `agenda_step` and `agenda`; commit 1 and 2 land first.
- **INV-14** -- nothing here proposes: the inquiry band emits nothing; the step it closes is a direct write decided by T1, named in the decision entry.
- **INV-18** -- `open_request` never commits; the route's existing commit carries it.

## Decision rights

STOP:
- an anchor does not hold;
- the pure move changes a function body (any hunk other than imports and the moved blocks);
ADAPT:
- `_finalize_plan` needs a helper that also lives in `routes/day.py`: move it with the three (same commit), report.
- `routes/day.py` exceeds 1000 lines after commit 3: move `_finalize_resolution`'s inquiry call site's helper further out, never shrink a docstring, report.
REPORT-ONLY:
- how a production world's open plans answer the new prompt (if Nia runs it live).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `journee_inquiry.py` PASS (JI1-JI7); `day_plan.py`, `day_feasibility.py`, `day_narration.py`, `day_mutations.py`, `day_narration_beats.py`, `quests.py`, `module_budget.py`, `prompt_registry.py` PASS.
- [ ] Named mutations, red then reverted: restore the `if not plans: return None` shortcut (JI1); drop the cut after k (JI3); give the inquiry step the `success` band (JI5); remove `[RECHERCHE]` (JI6).
- [ ] `apply_ticket_0121_select_prompt.py` on the test DB: `v<n> -> v<n+1>`, then `unchanged`.
- [ ] `/review-step` then `/close-step` on each of the three commits.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` (two entries), regenerated `DECISIONS_INDEX.md`, `FILE_MAP.md`. No schema change. CLAUDE.md unchanged.
