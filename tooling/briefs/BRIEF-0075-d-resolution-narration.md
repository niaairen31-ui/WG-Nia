# BRIEF — Step "Resolution, fact sheet and narration"

## Context

After BRIEF-0075-b and -c, a declaration has a concorded plan: steps in order,
each with a cost, a domain and requirement verdicts, with canon ids where the
registry matched and role hints where it did not.

This step RESOLVES the budgeted portion and tells the player what happened.
Python rolls the dice, freezes a fact sheet, and only then does a model write
prose — constrained by facts it cannot alter. A judge verifies the prose
before it is stored.

Decisions in force: **B4 as corrected by AMENDMENT 1** (narration is last, not
first), **T1** (the rewrite is a net with a fail-closed judge), and the
standing rule that dice are Python and never a model.

The single most important property of this brief: **the prose is a RENDERING
of an already-decided outcome, never a source of one.** Nothing the narration
says can contradict canon, because the narration receives the result rather
than the freedom.

## Mini-RECON

Measured 2026-08-24 at schema v1.93 unless delegated. Each anchor is a STOP
condition.

- **[M1]** `resolve_physical(domain, player_tier, npc_tier=0) -> Verdict` —
  `src/world_engine/resolution.py`. Pure, no DB, no model. `Verdict` is a
  frozen dataclass: `domain`, `dice: tuple[int, int]`, `modifier`, `total`,
  `band` in `failure | partial | success`. Bands: `<=6`, `7-9`, `>=10`.
  Player-roll rule, verbatim in the module docstring: *the roll always belongs
  to the player*; NPC tier is opposition, never its own roll.
- **[M2]** The MJ chain precedent — `src/world_engine/cockpit/play_physical.py`
  plus prompts `mj_interpretation`, `mj_arbitration`, `mj_establishment` in
  `PROMPT_REGISTRY`. Establishment narrates an already-computed verdict. This
  brief's narration is the same shape at day granularity; read that chain
  before writing this one.
- **[M3]** `llm_parse` / `LlmParseError` — `src/world_engine/llm_parse.py`.
  Sole JSON-extraction chokepoint. `ollama_client.strip_think` is applied
  inside it.
- **[M4]** `Batch` — `models/pipeline.py`. Carries `local_summary`,
  `message_to_claude`, `claude_raw_response`, `final_result`, all vestigial
  from the abandoned Claude-checkpoint pipeline, all with zero writers as of
  BRIEF-0075-a's execution notes. Also `status`, `processed_at`, `applied_at`,
  and `day_number` from -a.
- **[M5]** `PassPlay.history` — JSON NOT NULL, server default `'[]'`.
  Untouched by -a, which writes `[]`. `PASS_PLAY_STATUSES` in
  `writes/pipeline.py` is `("submitted", "resolving", "resolved", "flagged")`.
- **[M6]** `day_plan.py` from -b — `budget_cut`, `evaluate_requirements`,
  `DAY_BUDGET_SLOTS`. `day_concordance.py` from -c — `concord`, `emit_germs`.
- **[M7]** `AgendaStep.status` CHECK `IN ('pending','active','completed','failed')`,
  `outcome: Optional[str]`, `change_history` JSON, and the partial unique index
  `idx_agenda_step_one_active`.
- **[DELEGATED D1]** The player's tier for a given domain. `resolve_physical`
  takes `player_tier: int`. Locate how the existing physical chain derives it
  (skill rows, resistance tier, or a default) and reuse that derivation
  verbatim. If more than one derivation exists, report both and STOP rather
  than choosing.
- **[DELEGATED D2]** NPC opposition tier, same question, same rule.
- **[DELEGATED D3]** Whether `local_summary` and `final_result` are safe to
  repurpose: confirm zero writers and zero readers for both, in `src/` and in
  `tooling/`. If either has a reader, STOP and report — item 4 depends on
  this.

**STOP conditions.**

- S1. `resolve_physical` has acquired a DB or model dependency.
- S2. `local_summary` or `final_result` has any reader or writer (D3).
- S3. The player-tier derivation is ambiguous (D1) or absent.
- S4. A prompt key collides with `day_narration` or `day_rewrite`.
- S5. Any existing code path writes `PassPlay.history`. This brief must be its
      first writer; if it is not, the append contract must be reconciled first.

## Scope IN

### 1. Step resolution — `src/world_engine/day_resolve.py` (new)

- `resolve_steps(plan, character, db) -> list[StepOutcome]`. For each step
  included by `budget_cut`, in `step_order`:
  - If `domain` is NULL, the step resolves without a roll; its outcome band is
    `success` unless a requirement verdict says otherwise.
  - Otherwise call `resolve_physical` (M1) with the derived tiers (D1, D2).
    **The roll is Python. No model is consulted about an outcome, ever.**
  - A `failure` band TRUNCATES the day at that step: it and every later step
    are not attempted. A `partial` continues but is recorded as partial.
- `StepOutcome` carries the step's `objective`, its `Verdict` (or an explicit
  "no roll" marker), the band, the requirement verdicts, and the canon ids the
  concordance pass attached to that step.
- Persist: each attempted step's `AgendaStep.status` moves to `completed` or
  `failed`, `outcome` gets a short factual line (not prose — the narration is
  item 3), and the transition is appended to `change_history`. The next
  unattempted step becomes `active`; the partial unique index (M7) guarantees
  there is at most one.
- Pure/impure split: the banding and truncation logic is a pure function
  taking verdicts and returning the outcome list; persistence is a separate
  function. The check in item 5 asserts the split.

### 2. The frozen fact sheet

- `freeze_facts(outcomes, concordance, batch) -> FactSheet`, a frozen
  dataclass, built once and never mutated.
- It carries exactly: the day number; per step, the objective, band, dice,
  modifier and total; the NPC ids interacted with and their display names;
  the location ids visited and their display names; every role hint used in
  place of a name; and the resource, knowledge and skill deltas the outcomes
  imply (computed, not yet emitted as mutations — that is -e).
- It also carries `authorised_names: frozenset[str]` — every proper name the
  narration is permitted to use: the resolved display names, plus the player
  character's name. **Role hints are NOT names**; a role hint appears in the
  fact sheet as a role, and the narration must render it as a function.
- The fact sheet is the ONLY thing item 3 receives besides the declaration.
  The narration never sees the registry, never sees the DB, and never sees an
  unresolved candidate list.

### 3. Narration

- `PROMPT_REGISTRY` entry `day_narration`: `surface="play"`,
  `world_scoped=True`, `dry_run_capable=True`, `default_model=_game_model`,
  `call_sites` naming this module.
- `narrate(fact_sheet, declaration, db) -> str`. One call. The prompt receives
  the fact sheet as structured data and asks for prose that renders it.
- **Positive-form prompt only.** The gameplay model is abliterated and does
  not follow negative constraints, so "do not invent names" is worthless as an
  instruction. Say instead: *name only these people and places*, and give the
  list. Say: *render each role as a function, in this form*, and give an
  example. Everything that can only be phrased as a prohibition is enforced by
  the judge in item 4, not asked for in the prompt. Write the prompt out in
  full in the execution notes.
- The prose must state the outcomes in the fact sheet's own terms; a `failure`
  band reads as a failure. The prompt asks for that positively: *state what
  the character attempted and what came of it, for each beat, using the given
  band*.

### 4. The T1 judge and the conditional rewrite

- `judge_narration(prose, fact_sheet) -> JudgeVerdict` in a dedicated module,
  `src/world_engine/day_narration_guard.py`. Python only, no model.
  Fail-closed and vacuity-guarded:
  - **Name containment.** Every proper-name candidate extracted from the prose
    must be in `fact_sheet.authorised_names`. A name outside it is a failure
    naming the offending token. Extraction heuristic is Claude Code's to
    choose, but it must be deterministic and it must be documented in the
    module docstring, because a weak extractor makes this check vacuous.
  - **Outcome survival.** Every step in the fact sheet must be discernible in
    the prose with its band intact. Implement as a per-step assertion; a step
    that cannot be located is a failure.
  - **Anti-vacuity.** Zero names extracted, or zero steps checked, is a
    FAILURE, not a pass. This is the single most important line in the module.
- On a judge failure, the day does not silently degrade: report, store
  nothing as final, and stop. Nia sees the rejected prose and the reason.
- **The rewrite pass** (`day_rewrite` prompt, same registry shape). It fires
  ONLY on a narrow, named trigger: a late delta discovered during step
  resolution that the concordance pass could not have known — in practice, an
  outcome that resolved a role to a canon id after narration was already
  drafted. It receives the frozen fact sheet plus that single delta, and
  nothing else. Its output goes through the SAME judge, with the delta's name
  added to `authorised_names`. A rewrite that fails the judge is a stop, not a
  retry loop; retries are bounded at `MAX_REWRITE_ATTEMPTS = 1`, a named
  constant.
- **The rewrite is expected never to fire** in a correctly ordered run, because
  concordance precedes narration (AMENDMENT 1). Count the firings: increment a
  counter recorded in the execution notes for each live day resolved. That
  count is the evidence the D3 reactivation condition is phrased against.

### 5. Persistence and the route

- `Batch.local_summary` receives the accepted narration draft;
  `Batch.final_result` receives the post-judge accepted prose (identical when
  no rewrite fired). Subject to D3: if either column has any reader or writer,
  STOP and use new columns instead. Repurposing them gives two vestigial
  columns a reader, which is the doctrine's preference over adding new ones.
- `Batch.processed_at` set. `Batch.status` moves to a value naming the state
  "resolved, awaiting review"; declare the batch status vocabulary as a named
  constant beside `PASS_PLAY_STATUSES` in `writes/pipeline.py`, and have the
  route read it from there.
- `PassPlay.status` moves to `resolved`. **`PassPlay.history` gains one
  append** per resolution attempt: the fact sheet, the prose, the judge
  verdict, and a timestamp. Append-only — the write path may only extend the
  list, never replace an element. `declared_action` is not touched; it has no
  update path and never gains one.
- `POST /api/day/{batch_id}/resolve` in `routes/day.py`. Fail-closed when the
  batch is not in the active world or when `PassPlay.status != 'resolving'`.
  One transaction: outcomes, agenda step transitions, narration, history
  append, status moves.
- The response carries the prose, the NPC list, the location list and the
  computed deltas. No `agenda_id`, no `step_id`, no fact-sheet internals
  beyond what the player should see.
- **A replay** re-runs the chain on the same immutable `declared_action` and
  appends a SECOND entry to `history`. Nothing is overwritten. The route must
  accept a batch already at `resolved` for exactly this purpose, and must say
  in the response that it is a replay.

### 6. Verify — `tooling/verify/checks/day_narration.py` (new)

Stdlib `ast` and text only. Fail-closed, vacuity-guarded, each failure naming
the empty collection.

- R1. `day_resolve.py` calls `resolve_physical`, and no module in the day
  chain contains a `randint` call of its own.
- R2. The banding/truncation function is pure: no `db`, no `select(`, no
  `chat(`, no `datetime`, no `randint` in its body.
- R3. `narrate` receives the fact sheet and the declaration and nothing else:
  its signature takes no `db`-derived registry object, and its body contains
  no `select(`.
- R4. `day_narration_guard.py` contains no `chat(` — the judge is Python.
- R5. The judge's anti-vacuity guard exists: assert the module fails on zero
      names and on zero steps, by locating both explicit guards.
- R6. `MAX_REWRITE_ATTEMPTS` is a named constant with the value 1, and the
      rewrite call site is reachable from exactly one trigger condition.
- R7. `PassPlay.history` is only ever appended to: no assignment of a fresh
      list to `.history` outside `write_pass_play`'s constructor, and no
      `.history[` index assignment anywhere.
- R8. No assignment to `.declared_action` anywhere (re-assert -a's R3 from
      this brief's angle, since this brief is the first to write the same row).
- R9. `day_narration` and `day_rewrite` are in `PROMPT_REGISTRY` with
      `call_sites` naming their functions.
- R10. Vacuity guard on every collection above.

## Scope OUT

- **Mutation emission** — BRIEF-0075-e. The fact sheet COMPUTES deltas; no
  `ProposedMutation` row is written here except the germs -c already emits.
- **The day account UI and the rendezvous** (I1) — BRIEF-0075-e.
- **Reconciliation** (R1) — BRIEF-0075-f.
- **`world.current_phase`** — not read (P2), not written. The four-slot budget
  comes from -b's constant.
- **`schedule_reads.py`** — consumed through -c's concordance only. No new
  positional read here, no precedence term, no edit to `where_is`.
- **NPC displacement** (N1). The schedule IS the prediction. A step whose
  target NPC is off-schedule FAILS; that is drama, not a bug, and the
  narration renders it as such. Do not add a fallback that relocates the NPC.
- **Auto-approve** (O1). Nothing applies without Nia.
- **`message_to_claude` / `claude_raw_response`.** Still REPORT ONLY; do not
  repurpose them even though item 5 repurposes their two siblings.
- **A retry loop on judge failure.** One rewrite attempt, then stop.
- **Injection filtering.** `flagged` stays unwritten.

## Invariants to defend

- **Model proposes, code judges.** Dice are Python (R1), banding is pure (R2),
  the judge is Python (R4). Any of the three drifting into a model call is the
  failure mode.
- **The prose is a rendering, not a source.** R3 is the tripwire: the narration
  cannot reach the DB, so it cannot contradict what it cannot see.
- **History is sacred.** `history` appends only (R7); `declared_action` never
  changes (R8); a replay adds, never replaces.
- **Fail-closed and vacuous-proof.** A judge that checks nothing and passes is
  the worst possible outcome of this brief. R5 exists for that alone.
- **The positional wall.** Nothing here reads an agenda for a position.

## Done means

- [ ] A one-step plan with `domain` set produces a `Verdict` with real dice in
      the response, and the same day replayed produces different dice and a
      second `history` entry, with the first entry intact.
- [ ] A `failure` band truncates the day: later steps stay `pending`, and the
      prose says the attempt failed.
- [ ] Exactly one `AgendaStep` is `active` after resolution; forcing a second
      raises an integrity error.
- [ ] The prose names only people and places in `authorised_names`. Manually
      injecting an unauthorised name into a stored draft makes the judge FAIL
      and names the token.
- [ ] Manually deleting one step's outcome from a stored draft makes the judge
      FAIL and names the step.
- [ ] A fact sheet with zero steps, or zero authorised names, makes the judge
      FAIL — not pass.
- [ ] A role-hinted NPC is rendered as a function, without a proper name, and
      the judge accepts it.
- [ ] `Batch.local_summary` and `final_result` hold the draft and the accepted
      prose; `processed_at` is set; `PassPlay.status` is `resolved`.
- [ ] The response contains no `agenda_id` and no `step_id`.
- [ ] The rewrite-firing counter is recorded in the execution notes, with the
      number of live days resolved during verification.
- [ ] `python tooling/verify/checks/day_narration.py` green, each of R1–R10
      observed FAILING under a deliberate local mutation before revert.
- [ ] `day_plan.py`, `day_concordance.py`, `npc_schedule.py`,
      `pipeline_wiring.py`, `single_canon_write.py`, `corpus_gate.py` green.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md`: a subsection on the fact
  sheet — why the narration receives a frozen result instead of the registry,
  what the T1 judge proves and, explicitly, what it does NOT prove (name
  containment proves no unauthorised name appears; it does not prove the prose
  is coherent, and it does not prove a role was rendered as a role rather than
  quietly dropped). Record the rewrite-firing counter as the metric behind the
  D3 reactivation condition.
- `tooling/standards/DECISIONS_INDEX.md`: B4 (as amended), T1, N1.
- `world-engine-schema-changelog.md`: only if D3 forces new columns instead of
  repurposing. If `local_summary` and `final_result` are reused, note the
  repurposing in the changelog under the current version without a bump, and
  say so in the execution notes.
- Prompt texts for `day_narration` and `day_rewrite`: verbatim in the
  execution notes.
