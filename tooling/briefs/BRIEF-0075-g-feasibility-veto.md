# BRIEF — Step "Feasibility veto"

## Context

The four `requires` forms from BRIEF-0075-b are mechanical: a knowledge row,
a relation threshold, a ledger balance, graph reachability. None of them
captures whether a plan is PLAUSIBLE — whether this character, with this
history, could realistically find a fence in a single day.

This step adds one model call that can judge that, under a shape that makes it
structurally unable to do damage: **the veto can only SHORTEN the day, never
extend it.** Python computes the cut from declared costs; the model may reduce
the number of retained steps, with a cited reason; it may never add one, never
raise a cost, never overturn a prerequisite verdict.

Decision **Y1**, taken now rather than in phase 2. This is deliberately the
only place in the chain where fuzzy judgment is allowed, and the asymmetry is
the whole safety argument: a model that can only subtract cannot break F1.

Executes AFTER BRIEF-0075-e, so the review queue and the day account already
exist to observe the veto's behaviour.

## Mini-RECON

Anchors to re-measure. Each is a STOP condition.

- **[M1]** `day_plan.py` from BRIEF-0075-b as amended: `DAY_BUDGET_SLOTS`
  derived from the phase vocabulary, `REQUIREMENT_TYPES`, `_EVALUATORS`,
  `budget_cut` (pure, sequential truncation, not a knapsack),
  `evaluate_requirements`, `_day_reachable_ids` (BRIEF-0075-b AMENDMENT 1).
- **[M2]** `BudgetResult` — its exact fields: the included steps, the slots
  consumed, the index of the first excluded step, and the failing verdict when
  a prerequisite truncated the plan.
- **[M3]** `llm_parse` / `LlmParseError` — the sole JSON chokepoint.
- **[M4]** `PROMPT_REGISTRY` / `PromptSpec`: `surface`, `world_scoped`,
  `dry_run_capable`, `call_sites`, `default_model`. `_game_model()`.
- **[M5]** `POST /api/day/{batch_id}/plan` in `routes/day.py` and its ordering
  after BRIEF-0075-c: extract, concord, reconcile (once -f lands), plan, cut.
- **[DELEGATED D1]** What character context is already assembled for the
  extraction passes in `day_extract.py`. The veto needs the same frame and
  must reuse it, not build a second one — an ad-hoc frame is how a secret
  reaches a prompt. Report the builder used before writing.

**STOP conditions.**

- S1. `budget_cut` is no longer pure, or `BudgetResult` no longer carries the
  first-excluded index.
- S2. A prompt key collides with `day_feasibility`.
- S3. The character frame from D1 cannot be reused and would have to be
  rebuilt here.
- S4. Any existing caller depends on `budget_cut`'s output being final.

## Scope IN

### 1. The veto call — `src/world_engine/day_feasibility.py` (new)

- `PROMPT_REGISTRY` entry `day_feasibility`: `surface="play"`,
  `world_scoped=True`, `dry_run_capable=True`, `default_model=_game_model`,
  `call_sites` naming this module.
- `veto(budget_result, character_frame, declaration, db) -> VetoVerdict`.
  ONE call, parsed through `llm_parse` (M3), then domain-validated here.
- Input: the steps Python already RETAINED, in order, with their objectives
  and costs; the character frame from D1; the declaration. The model does not
  see the excluded steps, the requirement verdicts, the ids or the registry.
  It answers one question: given who this character is, how many of these
  retained steps could plausibly happen in one day?
- Output shape, validated strictly: `retained: int` and `reason: str`
  (non-empty). `cited_step_order: int` naming the first step the veto drops,
  required when `retained` is lower than the input count and forbidden
  otherwise.
- **Positive-form prompt only** — the gameplay model is abliterated. Ask for
  the two or three fields, give the range, give one worked example. Everything
  that can only be phrased as a prohibition is enforced in the clamp below.
  Write the prompt out in full in the execution notes.

### 2. The clamp — where the safety lives

A pure function in the same module, applied to every verdict before it is
used:

- `retained` is clamped to `[0, len(input_steps)]`. A value above the input
  count is clamped DOWN, never honoured, and the clamping is recorded.
- A verdict that would retain MORE steps than Python retained is not an error
  and not a widening: it is clamped to Python's count and recorded as
  `veto_ignored`. **The veto is monotonic downward by construction, not by
  instruction.**
- A missing or unparseable field, or a `cited_step_order` naming a step not in
  the input, makes the whole verdict `veto_unavailable`: the day proceeds on
  Python's cut, unchanged, and the failure is reported. **A veto that cannot
  be understood never shortens the day either** — it is inert, not
  conservative.
- `retained = 0` is allowed and means the day accomplishes nothing. It is a
  legitimate outcome, not an error, and the narration must be able to render
  it.
- The clamp is pure: no DB, no model, no clock, no randomness.

### 3. Wiring

- `POST /api/day/{batch_id}/plan` calls `veto` AFTER `budget_cut` and after
  `evaluate_requirements`, never before. Python's cut is the input, so the
  veto can only operate on an already-legal plan.
- The response gains a `feasibility` block: Python's retained count, the
  veto's retained count, the reason, the cited step's objective, and a flag
  saying whether the verdict was honoured, clamped or unavailable.
- Steps dropped by the veto stay `pending`. They are not failed and not
  deleted; tomorrow's reconciliation may pick them up.
- The Journée surface shows the reason in plain language next to the day's
  objectives. The player learns the day was shorter than hoped, and why.

### 4. Observability — the point of doing this now

Nia's stated motive is to test AI judgment. That requires evidence, so the
step must produce it:

- Every verdict is recorded in `PassPlay.history` alongside the resolution
  entry: Python's count, the veto's count, the reason, and the honoured /
  clamped / unavailable flag. Append-only, per BRIEF-0075-d's contract.
- The execution notes report, across every day resolved during verification:
  how many verdicts were honoured, how many clamped, how many unavailable, and
  the distribution of `python_retained - veto_retained`.
- A veto that never fires and a veto that always drops to zero are both
  failures of calibration, not successes of safety. The numbers are what make
  that visible.

### 5. Verify — `tooling/verify/checks/day_feasibility.py` (new)

Stdlib `ast` and text only. Fail-closed, vacuity-guarded, each failure naming
the empty collection.

- R1. The clamp is pure: no `db`, no `select(`, no `chat(`, no `datetime`, no
  `randint` in its body.
- R2. The clamp's upper bound is the input step count, and no code path
  assigns a `retained` value greater than it. Assert the clamp exists as an
  explicit `min(...)` or equivalent, not as a prompt instruction.
- R3. `day_feasibility.py` writes nothing: no `db.add(`, no `.commit(`, no
  `ProposedMutation(`.
- R4. `veto` is called after `budget_cut` in `routes/day.py` — assert the call
  order, not merely the presence of both.
- R5. The veto never touches requirement verdicts: `day_feasibility.py`
  contains no reference to `REQUIREMENT_TYPES`, `_EVALUATORS` or
  `evaluate_requirements`.
- R6. `veto_unavailable` leaves Python's cut untouched: assert the branch
  exists and returns the input unchanged.
- R7. `day_feasibility` is in `PROMPT_REGISTRY` with `call_sites` naming this
  module.
- R8. Vacuity guard on every collection above.

## Scope OUT

- **Any upward influence.** The veto cannot add a step, raise a cost, lower a
  cost, overturn a prerequisite verdict, or change `DAY_BUDGET_SLOTS`. Y3 —
  the model deciding how many steps fit, replacing Python's sum — was rejected
  as F3 and stays rejected.
- **Retrying a rejected verdict.** One call, then honour, clamp or ignore.
- **Feeding the veto the registry, the ids, or the excluded steps.**
- **Mutation emission.** Nothing here proposes canon.
- **Skills** — X1's deferral stands.
- **`world.current_phase`**, `schedule_reads.py`, `PUT /api/world/phase`,
  TICKET-0069, `npc_move`, location germs, auto-approve, `flag_reason`,
  multiplayer — all untouched.
- **Tuning the prompt against observed output.** Record the numbers; changing
  the prompt on the basis of them is a later, separate pass, so that the
  calibration data stays honest.

## Invariants to defend

- **Model proposes, code judges.** The veto is the narrowest possible
  exception and it is not an exception at all: the model's output is clamped
  by a pure function before it can affect anything. R1 and R2 are the
  tripwires, and R2 in particular must assert a real `min`, because a clamp
  that lives only in the prompt is no clamp at all against an abliterated
  model.
- **Fail-closed, in the correct direction.** An unusable verdict leaves the
  day at Python's cut. It neither shortens nor lengthens. Silent conservatism
  would be as wrong as silent permissiveness, because both hide the failure.
- **Secrets stay structurally excluded.** The character frame is reused from
  the extraction path (D1), never rebuilt here.
- **History is sacred.** The verdict record appends to `PassPlay.history`.
- **Minimal first.** One call, one number, one reason. No per-step scoring, no
  confidence values, no second opinion.

## Done means

- [ ] A plan Python cuts to three steps, with a veto returning two, resolves
      two steps; the third stays `pending` and the response names the cited
      step and the reason.
- [ ] A veto returning five on a three-step input is CLAMPED to three, the
      response says `clamped`, and the day resolves three.
- [ ] A veto returning a malformed payload leaves the day at three, the
      response says `unavailable`, and the failure is reported.
- [ ] A veto citing a step not in the input is treated as `unavailable`, not
      as a valid drop.
- [ ] `retained = 0` resolves a day in which nothing is accomplished, and the
      narration renders it without inventing an outcome.
- [ ] The veto cannot raise Python's count under any input; verified by
      feeding it a deliberately inflated response.
- [ ] Requirement verdicts are identical with and without the veto: turning
      the call off changes only the step count, never a prerequisite outcome.
- [ ] `PassPlay.history` holds one veto record per resolution, appended, with
      the prior entries intact.
- [ ] The calibration numbers from item 4 are in the execution notes, over at
      least five resolved days.
- [ ] `python tooling/verify/checks/day_feasibility.py` green, each of R1–R8
      observed FAILING under a deliberate local mutation before revert.
- [ ] `day_plan.py`, `day_concordance.py`, `day_narration.py`,
      `day_mutations.py`, `pipeline_wiring.py`, `single_canon_write.py`,
      `npc_schedule.py`, `corpus_gate.py` all green.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md`: a subsection on Y1 — why a
  downward-only veto is not an exception to "model proposes, code judges", and
  a "proves X, not Y" note: the clamp proves the veto cannot lengthen a day;
  it does NOT prove the veto's judgment is good, which is what the calibration
  numbers are for.
- `tooling/standards/DECISIONS_INDEX.md`: Y1, and X1's deferral with its
  reactivation condition.
- No schema change. The verdict record rides in `PassPlay.history`.
- The `day_feasibility` prompt text: verbatim in the execution notes.
