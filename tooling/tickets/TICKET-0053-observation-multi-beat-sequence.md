---
id: TICKET-0053
title: Observation multi-beat sequence - run X consecutive beats from the observation surface
type: feature
status: live-gate
created: 2026-07-29
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
brief_ids: [BRIEF-0053-a]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Un mini ticket (0053), je veux que dans mon interface d'observation avoir la
> possibilite de demander plusieurs beat a la fois qui se font de facons
> consecutives. Faire X beat. [...] Je veux que tu reprenne ce qui permet de
> faire un beat, ne recree pas ce qui existe deja.

**English gloss.** The Observation surface today advances a run one beat per click
(`index.html:1572`, `observationStepRun()` at `index.html:12161-12170`). This ticket adds a
"run X consecutive beats" control that drives the EXISTING single-beat path X times. No new
beat mechanism, no new backend loop.

## Findings that motivated the design (RECON against `main`, fresh tarball 2026-07-29)

1. **The single-beat entry point already exists and is already the shared one.**
   `step_run` (`observation_runner.py:541-551`) executes one beat via `_run_beat_safely`
   (`observation_runner.py:511-522`) then applies the same stop conditions
   (`_apply_stop_conditions`, `observation_runner.py:528-538`) that the bounded loop applies.
   Its own docstring records the intent: "a manual step and a bounded loop converge on the
   same terminal state."
2. **A bounded loop also already exists - in Python, deliberately not over HTTP.**
   `run_bounded` (`observation_runner.py:554-563`) loops `step_run` until a stop condition.
   `routes/observation.py:1-15` states why it is not exposed as a route: a bounded run can be
   ~150 model calls (5 NPCs x 30 beats), too long for one synchronous HTTP request, so
   "there is no 'run to completion' route. `start` only creates the run; the client [...]
   drives it forward by calling `step` repeatedly."
3. **The client-side loop is therefore the documented design, not a workaround.** This ticket
   implements the client that `routes/observation.py`'s docstring already describes.
4. **Stop conditions are backend-owned and must stay there.** `_regular_beat_count`
   (`observation_runner.py:253-256`) implements the non-obvious rule that `max_beats` counts
   NPC-decision beats only - an injected event consumes no allowance (K2). Any client-side
   "beats remaining" arithmetic would be a second implementation of that rule.
5. **Per-beat proposal polling would be a guaranteed-empty GET.** `produce_run_proposals`
   (`observation_runner.py:616-621`) runs once, after the run closes; but
   `observationRefreshDetail` (`index.html:12228-12240`) unconditionally calls
   `_obsLoadProposals` (`index.html:12313-12329`). Refreshing per beat as-is doubles the
   request count for a response that cannot contain anything until the run is terminal.
6. **A non-running run refuses the step route loudly.** `step_run` raises `ValueError` on
   `status != 'running'` (`observation_runner.py:547-548`), surfaced as 422
   (`routes/observation.py:66-67`). A sequence that keeps POSTing after a close produces a
   spurious error instead of a clean stop.
7. **Two concurrent sequences on one run are currently unguarded.** `obsActiveRunId`
   (`index.html:12078`) is module state with no in-flight flag; nothing today prevents two
   overlapping loops interleaving beats against the same run.
8. **`function_length.py` does not cover the cockpit.** It ASTs `src/**/*.py` only
   (`tooling/verify/checks/function_length.py:1-18`); R1's 80-line ceiling does not apply to
   `index.html` JS. No extraction is forced by this ticket.

## Clarifications resolved (intake)

| Code | Decision |
|---|---|
| **A1** | The loop lives in the client (`index.html`), calling the existing `POST /api/observation/runs/{id}/step` X times. Rejected: a backend batch route `POST /runs/{id}/steps {count}`, which would contradict `routes/observation.py:1-15`'s recorded process-model finding, hold N x NPC model calls in one request, and remove both progressive feedback and interruption. Rejected: exposing `run_bounded` over HTTP, same reason plus it has no count parameter. |
| **B1** | Zero backend change. No new route, no new runner function, no signature change in `observation_runner.py`. The ticket's entire diff is `index.html` plus one verify check rule. |
| **C1** | The sequence stops on the FIRST of four conditions: X beats executed; the run leaves `running`; a step call errors; the creator interrupts. It never continues past any of them. |
| **C2** | Run closure mid-sequence is a normal outcome, not an error. The loop reads `run.status` from each step response (`routes/observation.py:73`) and exits reporting `stop_reason`, so `max_beats` / `quiescence` reached at beat 4 of 10 is displayed as such, never as a 422. |
| **D1** | "Interrompre" (pause the sequence) and "Arreter" (close the run) stay two distinct verbs with two distinct buttons. Interrupting leaves the run `running` and steppable; the existing stop button keeps its current meaning untouched. |
| **D2** | Interruption is cooperative and takes effect BETWEEN beats. The in-flight beat is never cancelled - it completes and persists. Rationale: history is sacred; a cancelled request would abandon a beat whose `observation_beat` / `observation_intent` rows are already being written. |
| **D3** | The existing "Arreter" button stays ENABLED during a sequence and also raises the interrupt flag, so killing a run mid-sequence exits cleanly instead of via a 422 on the next iteration. |
| **E1** | No client-side cap on X and no clamp to the remaining allowance. `max_beats` already bounds the run and C2 handles the closure; clamping client-side would reimplement `_regular_beat_count`'s event-exemption rule (finding 4) in JS. Only `X >= 1` is enforced, by input `min` plus a parse fallback. |
| **F1** | Per-beat refresh of transcript + run detail (watching it happen is the point of an observation surface), but NOT of proposals - `observationRefreshDetail` gains an opt-out parameter rather than a duplicated body. Proposals are fetched once, when the sequence ends. |
| **G1** | Re-entrancy is blocked structurally: a module-level in-flight flag refuses a second sequence, and the step / sequence / inject buttons are disabled while one runs. |
| **H1** | The new rule extends the existing `tooling/verify/checks/observation_surface.py` rather than adding an eighth observation check module. The surface contract already lives there (R6, no catch-all modules, is not threatened: the module's subject is "the Observation cockpit surface"). |
| **I1** | One brief. Single surface, no schema change, no new module. |

## Named deferrals opened by this ticket

- **D-0053-unattended** - a fully unattended run (close the tab, let it finish server-side)
  still does not exist and is not attempted here. It would require the batch/async design A1
  rejected, plus a progress channel (SSE or polling). Reactivate only if a measurement
  workstream needs runs longer than a creator will sit through.
- **D-0053-sequence-record** - the sequence is a UI gesture and is persisted nowhere. Nothing
  in `observation_run` records that beats 4-9 were requested as one batch. Deliberate: no
  reader exists for that fact (E2, no structure without a reader). Reactivate if metrics ever
  need to distinguish batched from hand-stepped beats.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `observationRunBeats()` exists in `index.html`, calls the existing `/step` path, and
      references the in-flight guard, the interrupt flag and a non-`running` status test
      -> verify/checks/observation_surface.py (new Rule 7)
- [ ] `observationRunBeats()`'s body references neither `max_beats` nor `quiescence` - the
      stop rule is not re-derived client-side (finding 4, E1)
      -> verify/checks/observation_surface.py (new Rule 7)
- [ ] `cockpit/routes/observation.py` declares no batch-step route and no request-body field
      named `count` / `n` / `beats` - A1 asserted structurally, not by comment
      -> verify/checks/observation_surface.py (new Rule 7)
- [ ] `observation_surface.py`'s vacuous-proof guard is raised to the new collected-function
      count and still FAILS on zero -> verify/checks/observation_surface.py (red-tested by
      temporarily renaming the function)
- [ ] Existing Rules 1-6 of `observation_surface.py` still pass unchanged; `observation_runner.py`
      and `routes/observation.py` are byte-identical to `main`
      -> verify/checks/observation_surface.py + `git diff --stat`
- [ ] `module_budget.py` and `json_ui_boundary.py` still pass -> existing checks

### Live  ->  human gate (Nia)
- [ ] Starting a run and asking for 5 beats produces 5 beats consecutively, with the
      transcript growing visibly between each one.
- [ ] A run whose `max_beats` is reached at beat 3 of a requested 10 stops at 3 and displays
      the stop reason - no error message, no 422.
- [ ] "Interrompre" during a 20-beat sequence stops it after the beat then in flight; the run
      is still `running` and "⏭ Un beat" still works.
- [ ] "Arreter" during a sequence closes the run and ends the sequence without an error toast.
- [ ] Ollama stopped mid-sequence: the sequence halts on the first failure, the error is
      displayed, and the run is `failed` / `error` (existing `_run_beat_safely` behaviour,
      unchanged).
- [ ] Double-clicking "Faire X beats" starts exactly one sequence.
- [ ] Proposals appear once at the end of the sequence when the run closed, and the panel is
      not hammered during the sequence.
