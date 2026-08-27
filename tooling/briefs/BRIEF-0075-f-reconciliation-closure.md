# BRIEF — Step "Plan reconciliation and closure"

## Context

After -e a full day is playable, but only ever the FIRST day. Briefs -b
through -e all refuse a declaration when the player already owns an active
agenda, because reconciling a new declaration against a standing plan is the
most delicate pass in the chain: it decides, alone, whether the player has
inertia.

This step lands it, and closes the ticket.

Decision **R1**: the model CLASSIFIES the new declaration against the standing
agenda as `continue`, `modify` or `replace`, and must justify by citing the
step it is reasoning about — but the EFFECT goes through
`agenda_step_change` / `agenda_creation`, hence through Nia's review. Model
proposes, code judges, unchanged. `replace` closes the old agenda `failed` and
opens a new one; the old one stays on file.

Locked upstream and binding here: a plan covers ONE day, unconsumed steps stay
`pending`, and if the player wants to continue tomorrow they can — through
this pass.

## Mini-RECON

Measured 2026-08-24 at schema v1.93 unless delegated. Each anchor is a STOP
condition.

- **[M1]** `Agenda.status` CHECK `IN ('active','completed','failed','abandoned')`;
  `AgendaStep.status` CHECK `IN ('pending','active','completed','failed')`;
  partial unique index `idx_agenda_step_one_active` on `agenda_id` where
  `status = 'active'`. Both carry `change_history` JSON NOT NULL.
- **[M2]** `write_agenda` — `src/world_engine/writes/goals_agendas.py`.
  Requires `owner_entity_id` to resolve to an ACTIVE faction or character;
  player characters qualify. Commit-free contract.
- **[M3]** `agenda_step_change` and `agenda_creation` branches in
  `_apply_mutation` — `cockpit/mutations.py`. Read what each accepts before
  emitting either; do not widen them.
- **[M4]** `day_plan.py` (-b) — `emit_plan`, `budget_cut`,
  `evaluate_requirements`, `write_day_plan`. `day_concordance.py` (-c).
  `day_resolve.py` and `day_narration_guard.py` (-d). `day_mutations.py` (-e),
  `EMITTED_MUTATION_TYPES`.
- **[M5]** The S3 refusal in `POST /api/day/{id}/plan` (-b): the route fails
  closed when the player owns an active agenda. This brief REPLACES that
  refusal with the reconciliation pass; the refusal must not survive as dead
  code.
- **[M6]** `PROMPT_REGISTRY` / `PromptSpec` shape; `llm_parse` /
  `LlmParseError`.
- **[DELEGATED D1]** The full set of `PASS_PLAY_STATUSES` and batch statuses
  in use after -d/-e, and whether any transition is missing for a day that is
  declared but whose plan is a continuation rather than a new plan. Report
  before writing.
- **[DELEGATED D2]** Whether any check authored in -b through -e asserts the
  S3 refusal directly. If one does, it must be retargeted in this brief, not
  deleted — report which.

**STOP conditions.**

- S1. More than one `Agenda` with `status='active'` exists for the player
  character. The chain's premise is at most one; if two exist, stop.
- S2. `agenda_step_change` cannot express reordering, insertion or status
  transitions the `modify` verdict needs. Report what it CAN express and stop
  rather than widening it here.
- S3. Closing an agenda `failed` has side effects beyond the status change —
  for instance a cascade onto linked goals. Report and stop.
- S4. A prompt key collides with `day_reconcile`.
- S5. The S3 refusal from -b is asserted by a check that cannot be retargeted
  without weakening it (D2).

## Scope IN

### 1. The reconciliation pass — `src/world_engine/day_reconcile.py` (new)

- `PROMPT_REGISTRY` entry `day_reconcile`: `surface="play"`,
  `world_scoped=True`, `dry_run_capable=True`, `default_model=_game_model`,
  `call_sites` naming this module.
- `reconcile(declaration, agenda, steps, db) -> Reconciliation`. ONE call.
  Parsed through `llm_parse`, then domain-validated here.
- Output shape, validated strictly: `verdict` in
  `("continue", "modify", "replace")`; `cited_step_order: int` naming a step
  that EXISTS on the standing agenda; `rationale`, a non-empty string. A
  verdict outside the trio, or a citation naming a step that does not exist,
  is a validation failure that reports and stops — never a silent fallback to
  `continue`.
- **The citation is the point.** A verdict without a locatable step is not
  reviewable, and the whole pass exists to be reviewed. Validate the citation
  against real `step_order` values, in Python, before anything else.
- **Positive-form prompt only** — the gameplay model is abliterated. Ask for
  the three fields and give the vocabulary; do not phrase requirements as
  prohibitions. Anything that can only be prohibited is enforced in the
  validator. Write the prompt out in full in the execution notes.
- The pass sees the declaration, the standing agenda's title, and its steps'
  `objective` / `step_order` / `status`. It does NOT see costs, requirements,
  ids or the registry — it classifies intent, nothing more.

### 2. Effects, all through the queue

Each verdict maps to mutations at `status='proposed'`. **Nothing takes effect
before Nia approves**, consistent with A1 and O1.

- **`continue`** — no structural change. The standing agenda's next `pending`
  step is proposed `active` via `agenda_step_change`. If a step is already
  `active`, the verdict is a no-op and the day proceeds to budget and resolve
  against the standing plan. Emit no mutation for a no-op; an empty proposal
  is noise in the queue.
- **`modify`** — the model's classification is a signal, not an edit. Re-run
  `emit_plan` (-b) on the declaration WITH the standing agenda's remaining
  steps as context, producing a revised step list, and propose the diff as
  `agenda_step_change` mutations bounded by what M3 accepts. If M3 cannot
  express the diff, that is S2 and a STOP.
- **`replace`** — propose `agenda_creation` for the new plan and an
  `agenda_step_change` closing the old agenda `failed`. **The old agenda
  stays on file with its steps and its `change_history` intact.** No delete,
  no `abandoned` shortcut that erases the attempt: the player tried something
  and stopped, and that is history.
- Every emitted mutation carries a `rationale` that names the verdict and
  quotes the cited step's objective, so the queue entry explains itself.

### 3. Wiring

- `POST /api/day/{batch_id}/plan` (-b): the S3 refusal (M5) is REPLACED. When
  the player owns an active agenda, run the reconciliation pass; when they do
  not, emit a fresh plan exactly as -b does today. The refusal must be gone,
  not commented out, and D2's check retargeted rather than deleted.
- Ordering inside the route: extract and concord (-c) FIRST, then reconcile,
  then plan or diff. The concordance result feeds both branches — a
  continuation still needs its names resolved.
- The response gains a `reconciliation` block: the verdict, the cited step's
  objective, the rationale, and the mutation ids proposed. **Still no
  `agenda_id`, no `step_id`** — the player sees objectives, never the plan
  structure.
- All-or-nothing: a reconciliation failure means no plan, no diff, no germ
  committed.

### 4. Ticket closure

- Sweep the ticket's Scope OUT list and confirm every named deferral is still
  deferred and none leaked in: multiplayer and `batch_order` beyond 1;
  auto-approve; `flag_reason`; location germs; D3's prologue; P1's
  phase-anchored budget; M3's interval unification; TICKET-0069;
  `schedule_reads.py` untouched; `PUT /api/world/phase` untouched.
- Report the state of the four vestigial `Batch` columns after the full chain
  (`local_summary`, `message_to_claude`, `claude_raw_response`,
  `final_result`): which now have writers, which still have none. Any still
  at zero after -f is a no-reader review candidate for a later ticket —
  REPORT ONLY, do not drop.
- Report the rewrite-firing counter from -d across every day resolved during
  this ticket's verification. That number is the evidence the D3 reactivation
  condition is phrased against, and it should be zero or near it.

### 5. Verify — extend `tooling/verify/checks/day_plan.py`

Rather than a ninth check module, extend the one that already owns the plan
path. Fail-closed and vacuity-guarded, each failure naming the empty
collection.

- R1. `day_reconcile.py` contains no `db.add(` of an `Agenda` or `AgendaStep`
  and no `_apply_mutation` call: it proposes, it does not write canon.
- R2. The verdict vocabulary is a named constant whose members are exactly
  `continue`, `modify`, `replace`, and the dispatch's key set equals it, both
  directions.
- R3. The citation validator exists and compares against real `step_order`
  values; a validation failure path exists and does not fall back to a default
  verdict. Assert the absence of a `continue` default explicitly.
- R4. The `replace` path never emits a status of `abandoned` and never deletes
  an `Agenda` or `AgendaStep` row: no `db.delete(` in the module.
- R5. The S3 refusal from -b is gone from `routes/day.py`, and the check that
  asserted it (D2) now asserts the reconciliation path instead.
- R6. `day_reconcile.py` contains no `select(` against costs, requirements or
  `agenda_step_requirement`: the pass classifies intent and sees nothing else.
- R7. Every mutation emitted by the reconciliation path carries a non-empty
  `rationale` argument at its construction site.
- R8. Re-assert, from this brief's angle, that the day chain still emits no
  `npc_move`, still sets every mutation `proposed`, and still reads no agenda
  for a position.
- R9. Vacuity guard on every collection above.

## Scope OUT

- **Auto-approve** (O1). Its own ticket.
- **Exposing the agenda.** A verdict and a cited objective are surfaced; the
  plan structure is not. R2 in -e and R7 here both guard it.
- **Letting the player choose the verdict** (rejected R2). The classification
  is the model's, the effect is Nia's.
- **Re-planning from scratch every day** (rejected R3). Inertia is the point.
- **Widening `agenda_step_change`.** If the `modify` diff does not fit, STOP.
- **Multi-day plans.** A plan still covers one day; continuation is what this
  pass provides.
- **`world.current_phase`**, `schedule_reads.py`, `PUT /api/world/phase`,
  TICKET-0069, location germs, `npc_move`, `flag_reason` — all still
  untouched.
- **Cleaning up the vestigial `Batch` columns.** REPORT ONLY.
- **P1, D3, M3.** Named deferrals with their reactivation conditions intact.

## Invariants to defend

- **Model proposes, code judges.** The verdict is a classification; the effect
  is a proposal; the application is Nia's. R1 is the tripwire.
- **History is sacred.** A replaced agenda closes `failed` and stays, with its
  steps and `change_history`. R4 is the tripwire, and it is the most important
  check in this brief.
- **Fail-closed.** An unparseable verdict, or a citation naming a step that
  does not exist, stops the day. A silent default to `continue` would be the
  worst possible failure mode: it looks like inertia and is actually a
  swallowed error. R3 exists for that alone.
- **At most one active step.** The partial unique index carries it; the
  `continue` and `modify` paths must not propose two.
- **The positional wall.** Still nothing reads an agenda for a position.

## Done means

- [ ] Day 1 declares and resolves as before; no reconciliation runs.
- [ ] Day 2 with a declaration that clearly continues yields `continue`, cites
      a real step, and proposes at most one `agenda_step_change`. Approving it
      makes the next step `active`.
- [ ] Day 2 with a declaration that shifts approach yields `modify`, and the
      proposed diff is bounded by what `agenda_step_change` accepts.
- [ ] Day 2 with an unrelated declaration yields `replace`. After approval the
      old agenda is `failed`, still present, with its steps and
      `change_history` intact, and a new agenda is active.
- [ ] Before approval, in all three cases, the standing agenda is unchanged in
      the DB.
- [ ] A model output naming a step that does not exist STOPS the day with a
      reported reason, and nothing is committed.
- [ ] A model output with a verdict outside the trio STOPS the day; it does
      not fall back to `continue`.
- [ ] Exactly one `AgendaStep` is `active` after each path; forcing a second
      raises an integrity error.
- [ ] No `agenda_id` or `step_id` in any response or in `Journee.svelte`.
- [ ] The S3 refusal from -b is gone from the codebase, and the check that
      asserted it now asserts the reconciliation path.
- [ ] Three consecutive days resolve end to end: declare, reconcile, plan,
      resolve, review, read the account, play an armed rendezvous.
- [ ] `python tooling/verify/checks/day_plan.py` green with R1–R9 added, each
      observed FAILING under a deliberate local mutation before revert.
- [ ] Every check in the corpus green: `day_plan.py`, `day_concordance.py`,
      `day_narration.py`, `day_mutations.py`, `pipeline_wiring.py`,
      `npc_schedule.py`, `prereq_judge.py`, `single_canon_write.py`,
      `json_ui_boundary.py`, `legacy_mount.py`, `corpus_gate.py`.
- [ ] The Scope OUT sweep (item 4) is reported, item by item.
- [ ] The vestigial-column report and the rewrite-firing counter are in the
      execution notes.
- [ ] `/review-step` and `/close-step` run.
- [ ] TICKET-0075 moves to `live-gate`, then `done` on Nia's word.

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md`: a subsection on R1 — why the
  verdict is a classification and never an edit, why the citation is mandatory,
  and why `replace` closes `failed` rather than `abandoned`. Add a
  "proves X, not Y" note: the citation validator proves the model reasoned
  about a real step; it does NOT prove the model reasoned about the RIGHT
  step, which is why the verdict goes through review.
- `tooling/standards/DECISIONS_INDEX.md`: R1, and a final sweep confirming
  every code from TICKET-0075 is indexed — A1, B4 (as amended by AMENDMENT 1),
  C1, F1, H1, I1, L1, M1, N1, O1, P2, Q1, R1, S1, T1, U1.
- `tooling/tickets/TICKET-0075-day-resolution-chain.md`: status transition
  only. The Clarifications and Scope OUT sections are history and stay as
  deposited; AMENDMENT 1 remains the corrective artifact for B4.
- `CLAUDE.md`: only if it enumerates surfaces or canon-write paths.
  TICKET-0071's hygiene pass owns that file otherwise.
- No schema change expected in this brief.
