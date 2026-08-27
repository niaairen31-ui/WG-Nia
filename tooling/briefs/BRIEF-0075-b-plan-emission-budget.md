# BRIEF — Step "Plan emission and budget"

## Context

BRIEF-0075-a landed the declaration socle: a day can be declared, stored and
read back, with `Batch.day_number` as the day ordinal. Nothing resolves yet.

This step gives a declaration a PLAN. One model call emits the full step list
for the player's objective; Python then cuts it against the day budget and
judges each step's prerequisites. The model proposes the steps; the code
decides how many happen.

Decisions in force: **F1** (one emission, Python cut), **M1** (the four
`SCHEDULE_PHASES` are the budget slots), **P2** (every day gets all four
slots regardless of `world.current_phase`), **S1** (four requirement forms,
each with a named evaluator), **H1** (plans reuse `Agenda`/`AgendaStep`).

This brief authors no prose and emits no mutation. Its output is a persisted
plan plus a computed, deterministic answer to "how much of it happens today".

## Mini-RECON

Anchors measured against `main` on 2026-08-24 at schema v1.93. Re-measure;
each is a STOP condition if it does not hold.

- **[M1]** `Agenda` — `src/world_engine/models/canon.py`, class `Agenda`.
  `world_id`, `owner_entity_id` (FK `entity.id`), `title`, `status` with
  `CheckConstraint("status IN ('active','completed','failed','abandoned')")`,
  `change_history` JSON NOT NULL default `'[]'`.
- **[M2]** `AgendaStep` — same file. `agenda_id`, `step_order: int`,
  `objective: str`, `status` CHECK
  `IN ('pending','active','completed','failed')`, `outcome`,
  `visibility_trace`, `change_history` JSON. Partial unique index
  `idx_agenda_step_one_active` on `agenda_id` where `status = 'active'`.
  **No `cost`, no `domain`, no location column of any kind.**
- **[M3]** `GoalPrerequisite` — same file. The relational-prerequisite
  precedent: `world_id`, `goal_id`, `type`, `target_entity_id` (FK
  `entity.id`, NOT NULL), `threshold: int`, with
  `CheckConstraint("type IN ('relation_gte')")`,
  `CheckConstraint("threshold BETWEEN 1 AND 100")`, and a unique index over
  `(goal_id, type, target_entity_id)`.
- **[M4]** `NPC_GOAL_PREREQUISITE_TYPES = frozenset({"relation_gte"})` —
  `src/world_engine/writes/goals_agendas.py`. `write_npc_goal_prerequisites`
  is the sole chokepoint, full-replace, snapshotting the previous rows into
  `npc_goal.change_history` first.
- **[M5]** The live prerequisite judge — `_mutation_goal_change_close` in
  `src/world_engine/cockpit/mutations.py`. Reject strings carry
  `"prerequisite not met"`, the current value and `"requires >= "`, plus a
  fail-closed `"unknown prerequisite type"` branch.
  `tooling/verify/checks/prereq_judge.py` asserts all five substrings.
- **[M6]** `resolve_physical(domain, player_tier, npc_tier=0) -> Verdict` —
  `src/world_engine/resolution.py`. Pure, `randint`-based, 2d6 plus
  `player_tier - npc_tier`, bands `<=6 failure / 7-9 partial / >=10 success`.
  No DB, no model.
- **[M7]** `PROMPT_REGISTRY: dict[str, PromptSpec]` —
  `src/world_engine/prompt_registry.py`. `PromptSpec` is a frozen dataclass:
  `surface` (`"play"|"authoring"`), `world_scoped: bool`,
  `dry_run_capable: bool`, `call_sites: tuple[str, ...]`,
  `default_model: Callable[[], str]`. `_game_model()` returns
  `ollama_client.DEFAULT_MODEL`.
- **[M8]** `prompt_store.current_prompt(db, template) -> PromptVersion` is the
  only read path for prompt text.
- **[M9]** `llm_parse` — `src/world_engine/llm_parse.py`. Sole chokepoint for
  parsing local-model JSON: fence stripping, `<think>` stripping via
  `ollama_client.strip_think`, first-balanced-JSON extraction, shape
  coercion. Raises `LlmParseError`. Domain validation stays with callers.
- **[M10]** `SCHEDULE_PHASES` — the four-phase vocabulary landed by
  TICKET-0074. Locate its single declaring module; `npc_schedule.py`'s
  `check_single_vocabulary_source` asserts there is exactly one.
- **[M11]** `writes/pipeline.py` — `MAX_DECLARATION_CHARS = 4000`,
  `PASS_PLAY_STATUSES = ("submitted", "resolving", "resolved", "flagged")`,
  `write_batch`, `write_pass_play`. Commit-free contract: the caller adds and
  commits.
- **[M12]** `routes/day.py` — `_get_or_open_session`,
  `_resolve_player_character` (fail-closed on a count other than 1),
  `_day_dict`, and the three routes. `_crud._world_id(db)` resolves the
  active world.

**STOP conditions.** Escalate rather than proceed if:

- S1. `AgendaStep` already carries a cost, duration, domain or location
  column, or any table already references `agenda_step` as a parent.
- S2. `SCHEDULE_PHASES` is declared in more than one module, or does not have
  exactly four members.
- S3. Any existing `Agenda` row is owned by a `character_type='player'`
  entity. This brief assumes the player has no standing agenda; reconciliation
  is BRIEF-0075-f. If one exists, stop.
- S4. `write_npc_goal_prerequisites`'s validation cannot be read as a
  reusable shape, or `goal_prerequisite` turns out to have writers beyond
  that chokepoint.
- S5. A prompt usage key colliding with `day_plan` already exists in
  `PROMPT_REGISTRY`.

## Scope IN

### 1. Schema — plan metadata on steps (migration, next version)

Two additive pieces. Follow the `migrate_v1_92_npc_schedule.py` precedent for
the mixed table/column shape and the fail-closed env guard.

**1a. `AgendaStep` gains two nullable columns.**

- `cost: Optional[int]` — how many day slots the step consumes. NULL for
  every NPC agenda step, which is the entire existing population.
- `domain: Optional[str]` — the resolution domain handed to
  `resolve_physical` (M6). NULL when the step needs no roll.
- `CheckConstraint("cost IS NULL OR cost BETWEEN 1 AND 4")`, riding on the
  `ALTER TABLE ... ADD COLUMN` statement (SQLite has no `ADD CONSTRAINT` —
  the same asymmetry v1.91 and v1.92 both document).
- No backfill. Existing steps keep NULL and behave exactly as today.

**This is the H1 consequence, taken deliberately: a plan is a plan.** NPC
agendas gain the same two columns and simply do not use them yet.

**1b. New table `agenda_step_requirement`**, mirroring `GoalPrerequisite`
(M3) in shape and discipline.

- `id`, `world_id` (FK `world.id`), `step_id` (FK `agenda_step.id`, NOT NULL),
  `type: str`, `target_entity_id: Optional[str]` (FK `entity.id`),
  `target_key: Optional[str]`, `threshold: Optional[int]`.
- `CheckConstraint("type IN ('knowledge','relation_gte','resource','location_reachable')")`.
- A per-type shape CHECK, so an ill-formed row cannot exist:
  `relation_gte` and `location_reachable` require `target_entity_id` NOT NULL;
  `knowledge` and `resource` require `target_key` NOT NULL; `relation_gte` and
  `resource` require `threshold` NOT NULL. Write it as one CHECK expression;
  the exact SQL is Claude Code's to compose, but every one of those six
  conditions must be enforced by the constraint, not by Python.
- Unique index over `(step_id, type, target_entity_id, target_key)`.
- No `change_history`: curated plan metadata, same family as `npc_schedule`.

**The positional wall.** `agenda_step` gets NO location column, and
`location_reachable` stores a location on the REQUIREMENT row, not on the
step. This is deliberate and load-bearing:
BRIEF-0074-a-amendment-1 rests on the measured fact that no agenda table
carries a location, so that no positional read can ever be tempted to consult
one. A requirement row states "the player must be able to reach L" — a
precondition on the player, never a position of an NPC. Item 5's check
enforces the distinction.

### 2. Requirement vocabulary and evaluators — `src/world_engine/day_plan.py` (new)

- `DAY_BUDGET_SLOTS: int` — declared here, equal to `len(SCHEDULE_PHASES)`,
  computed from the vocabulary rather than written as `4`. Under P2 every day
  gets the full budget; `world.current_phase` is NOT read anywhere in this
  module.
- `REQUIREMENT_TYPES: tuple[str, ...] = ("knowledge", "relation_gte", "resource", "location_reachable")`,
  and `_EVALUATORS: dict[str, Callable[...]]` whose key set must equal
  `REQUIREMENT_TYPES` exactly — the `_SOURCE_LOOKUPS` bijection precedent from
  `schedule_reads.py`.
- Four named evaluators, each returning a verdict object carrying `met: bool`,
  `current`, `required`, and a human-readable `reason`:
  - `_eval_knowledge` — does the character hold a `Knowledge` row matching
    `target_key`? Mini-RECON: read the `Knowledge` model's own shape and
    match on its subject/topic field; do NOT invent a column.
  - `_eval_relation_gte` — reuse M5's arithmetic verbatim. The reject reason
    must carry the same three substrings the existing judge does
    (`"prerequisite not met"`, the current value, `"requires >= "`), so that
    one message family covers both judges.
  - `_eval_resource` — does the character hold at least `threshold` of
    `target_key`? Mini-RECON: locate the resource/ledger read; the `ledger`
    table is INSERT-only, so this is a sum, not a column read.
  - `_eval_location_reachable` — is `target_entity_id` reachable through the
    door graph from the character's `current_location_id`? Mini-RECON: reuse
    the existing traversal; do not write a second one. If no reusable
    traversal exists, STOP and report rather than authoring one here.
- `evaluate_requirements(step, character, db) -> list[Verdict]`. An unknown
  `type` raises, fail-closed, with the message
  `"unknown requirement type {type!r}"`. It cannot happen through the DB
  (the CHECK forbids it); the branch exists so that widening the tuple
  without adding an evaluator fails loudly.

### 3. Budget cut — pure function, same module

- `budget_cut(steps, budget) -> BudgetResult`. Steps in `step_order`, taken
  greedily in order until the next step's `cost` would exceed the remaining
  budget. **Not a knapsack**: a plan is sequential, and step 3 cannot happen
  before step 2. Returns the included steps, the slots consumed, and the
  index of the first excluded step.
- A step with `cost` NULL is a plan-emission failure, not a free step: raise.
- A step whose requirements are unmet truncates the plan AT that step: it and
  everything after it are excluded, and the result carries the failing
  verdict. That is what makes "do you have the contacts to find this person"
  bite.
- Pure: no DB, no model, no clock. Deterministic given the same input.

### 4. Plan emission — model call

- New `PROMPT_REGISTRY` entry `day_plan`: `surface="play"`,
  `world_scoped=True`, `dry_run_capable=True`, `default_model=_game_model`,
  `call_sites=("src/world_engine/day_plan.py:emit_plan",)`.
- Seed the prompt template and its first version through the existing
  authoring path, not by hand-inserting rows.
- `emit_plan(declaration, character, db) -> list[PlanStep]`. ONE call. Output
  parsed through `llm_parse` (M9); domain validation stays here, per M9's
  contract: every step must carry `objective` (non-empty str), `cost` (int
  1..4), `domain` (str or null), and `requires` (list, possibly empty) whose
  items each carry a `type` drawn from `REQUIREMENT_TYPES`.
- Bounds, declared as named constants in this module: at most
  `MAX_PLAN_STEPS = 12` steps; anything beyond is truncated with a reported
  count, not silently dropped.
- **The prompt is positive-form only.** The gameplay model is abliterated and
  does not follow negative constraints; express every requirement as
  something to DO ("emit exactly these fields", "cost is an integer from 1 to
  4"), never as a prohibition. Where a constraint cannot be phrased
  positively, enforce it in the parser instead of asking for it. Write the
  prompt text out in full in the execution notes so it is reviewable.
- A parse failure or a shape violation is a resolution failure that reports
  and stops. It never falls back to a partial plan.

### 5. Persistence and the route

- `write_day_plan(...)` in `src/world_engine/writes/goals_agendas.py`, beside
  the existing agenda writers, following their commit-free contract. Creates
  one `Agenda` owned by the player character (`title` = the declaration's
  first line, truncated, or a model-supplied objective), its `AgendaStep`
  rows in order with `cost`/`domain`, and their `agenda_step_requirement`
  rows. All-or-nothing validation before any row is constructed.
- The first budgeted step is written `status='active'`; every other step is
  `'pending'`. The partial unique index (M2) is the guarantee that this stays
  true.
- `POST /api/day/{batch_id}/plan` in `routes/day.py`. Fail-closed when the
  batch is not in the active world, when its `PassPlay.status` is not
  `submitted`, or when the player already owns an `active` agenda (S3 —
  reconciliation is BRIEF-0075-f). Sets `PassPlay.status = 'resolving'`.
- Response: the ordered steps with `objective`, `cost`, `domain`, `status`,
  their requirement verdicts, plus `slots_consumed`, `slots_budget` and the
  first excluded index. `agenda_id` and `step_id` are NOT in the payload —
  the player never sees the agenda (ticket Scope OUT). The Journée surface
  renders the objectives and the cut, nothing more.

### 6. Verify — `tooling/verify/checks/day_plan.py` (new)

Stdlib `ast` and text only, no DB. Fail-closed and vacuity-guarded: every
check asserts a non-zero collected count and names which one came back empty.

- R1. `_EVALUATORS`' key set equals `REQUIREMENT_TYPES` exactly, in both
  directions (the `_SOURCE_LOOKUPS` bijection precedent).
- R2. `agenda_step_requirement`'s `type` CHECK lists exactly the same four
  values as `REQUIREMENT_TYPES`.
- R3. The per-type shape CHECK exists and covers all six conditions from 1b.
- R4. `DAY_BUDGET_SLOTS` is derived from the phase vocabulary, not written as
  a numeric literal.
- R5. `day_plan.py` contains no reference to `current_phase` (P2), and no
  `select(` against `NpcSchedule` (positional reads stay in
  `schedule_reads.py`).
- R6. **The positional wall.** No `location` column is declared on `Agenda` or
  `AgendaStep`, and no module reachable from `schedule_reads.py` imports
  `Agenda`, `AgendaStep` or `AgendaStepRequirement`.
- R7. `budget_cut` is pure: its body contains no `db`, no `select(`, no
  `chat(`, no `datetime`, no `randint`.
- R8. `emit_plan` routes its parse through `llm_parse`, and `day_plan` appears
  in `PROMPT_REGISTRY` with a `call_sites` entry naming it.
- R9. `MAX_PLAN_STEPS` and `DAY_BUDGET_SLOTS` are module-level named
  constants; the route reads bounds from them rather than restating literals.

## Scope OUT

- **Extraction and concordance** (C1) — BRIEF-0075-c. `emit_plan` receives the
  declaration as written; it does not resolve names to ids, and it emits no
  `entity_creation` germ.
- **Step resolution and narration** — BRIEF-0075-d. No `resolve_physical` call
  in this brief; `resolution.py` is imported by nobody new here.
- **Mutation emission** — BRIEF-0075-e. No `ProposedMutation` row is written.
- **Reconciliation** (R1) — BRIEF-0075-f. This brief refuses when a standing
  player agenda exists rather than reasoning about it.
- **`world.current_phase`** — not read (P2). `PUT /api/world/phase` untouched.
- **`schedule_reads.py`** — untouched. No precedence term added, no positional
  read performed.
- **NPC agendas.** The two new columns and the new table apply to them
  structurally and are used by nothing. Do not backfill, do not expose them in
  the Creation tab's agenda editor, do not touch `agenda_generation`.
- **Re-planning across days.** A plan is emitted once per declaration.
- **Exposing `agenda_id` or `step_id` to the player.**
- **Vestigial `Batch` columns** — still REPORT ONLY.

## Invariants to defend

- **Model proposes, code judges.** The cut, the evaluators and the bounds are
  all Python. A model call anywhere on the cut path is the failure mode; R7
  is the tripwire.
- **The positional wall** (BRIEF-0074-a-amendment-1). No agenda table gains a
  location. R6 is the tripwire, and it is the single most important check in
  this brief.
- **No structure without a reader.** `cost`, `domain` and every column on
  `agenda_step_requirement` are consumed by `budget_cut` and the evaluators in
  this same brief.
- **Fail-closed.** Unknown requirement type raises; NULL cost raises; parse
  failure stops; more than one active step is structurally impossible.
- **All-or-nothing writes.** Validate the whole plan before constructing the
  first row, per the existing `writes/` contract.

## Done means

- [ ] Migration runs on a fresh DB and on the existing one; a second run
      changes nothing and says so. Version constant, `schema_meta` and the
      schema doc header all agree, in one commit.
- [ ] Inserting an `agenda_step` with `cost = 5` raises an integrity error;
      `cost = NULL` is accepted.
- [ ] Inserting an `agenda_step_requirement` of type `relation_gte` with a
      NULL `target_entity_id` raises; of type `knowledge` with a NULL
      `target_key` raises; an unknown type raises.
- [ ] `POST /api/day/{id}/plan` on a fresh declaration returns ordered steps
      with costs and per-requirement verdicts, and `slots_consumed` never
      exceeds `slots_budget`.
- [ ] A plan whose steps sum to more than four slots is truncated, and the
      response names the first excluded index.
- [ ] A plan whose second step has an unmet `relation_gte` is truncated AT
      that step, and the verdict reason carries the current and the required
      value.
- [ ] Exactly one step is `active` in the DB after planning; forcing a second
      raises an integrity error.
- [ ] Calling the route twice on the same batch fails closed the second time.
- [ ] The response payload contains no `agenda_id` and no `step_id`.
- [ ] `python tooling/verify/checks/day_plan.py` green, and each of R1–R9 has
      been observed to FAIL under a deliberate local mutation before revert.
- [ ] `npc_schedule.py`, `prereq_judge.py`, `pipeline_wiring.py`,
      `single_canon_write.py` and `corpus_gate.py` all still green.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `world-engine-schema-changelog.md`: entry at the next version — the two
  `agenda_step` columns and `agenda_step_requirement`, naming TICKET-0075 /
  BRIEF-0075-b and decisions F1, M1, P2, S1, H1. State the positional-wall
  rationale for putting `location_reachable`'s target on the requirement row.
- `world-engine-schema.md`: header version, the `agenda_step` entry, the new
  table entry.
- `src/world_engine/schema_version.py`.
- `tooling/standards/ARCHITECTURE_DECISIONS.md`: a subsection recording that
  the plan-vs-position separation is what keeps the 0074 amendment true, and
  that `agenda_step_requirement` is a precondition table, not a positional
  one.
- `tooling/standards/DECISIONS_INDEX.md`: F1, M1, P2, S1.
