# BRIEF — Step "Observation multi-beat sequence"

## Context

The Observation surface advances a run one beat per click (`index.html:1572` ->
`observationStepRun()`, `index.html:12161-12170`). Nia wants "faire X beats" consecutively.
Everything needed to execute a beat already exists and is reused verbatim: `step_run`
(`observation_runner.py:541-551`) and its route `POST /api/observation/runs/{run_id}/step`
(`routes/observation.py:62-74`). `routes/observation.py:1-15` already records the design this
brief implements — there is no run-to-completion route on purpose, and "the client [...]
drives it forward by calling `step` repeatedly". This brief writes that client.

**This step adds no backend code.** `observation_runner.py` and
`cockpit/routes/observation.py` must be byte-identical to `main` when the step lands.

## Scope IN

### 1. Markup — `index.html`, inside `#obs-run-controls` (currently `index.html:1569-1577`)

Give the two existing buttons ids and add the sequence controls. The resulting control row
(replacing `index.html:1571-1576`) is exactly:

```html
<div style="display:flex; gap:8px; flex-wrap:wrap; margin-top:6px">
  <button id="obs-step-btn" onclick="observationStepRun()">⏭ Un beat</button>
  <label>Suite <input id="obs-beat-count" type="number" value="5" min="1" style="width:60px"></label>
  <button id="obs-run-beats-btn" onclick="observationRunBeats()">⏩ Faire X beats</button>
  <button id="obs-abort-btn" onclick="observationAbortSequence()" style="display:none">⏸ Interrompre</button>
  <span id="obs-sequence-progress" class="target-ref"></span>
  <button onclick="observationStopRun()">⏹ Arrêter</button>
  <input id="obs-event-text" type="text" placeholder="Texte de l'événement injecté…" style="flex:1; min-width:200px">
  <button id="obs-inject-btn" onclick="observationInjectEvent()">⚡ Injecter</button>
</div>
```

The "⏹ Arrêter" button deliberately gets NO id and is NOT disabled during a sequence (ticket
D3) — closing the run mid-sequence must stay reachable.

### 2. Module state — `index.html`, beside the existing `obs*` declarations (`index.html:12076-12079`)

Add exactly two flags, with this comment verbatim:

```js
let obsSequenceRunning = false; // in-flight guard (G1) — one sequence per surface, ever
let obsSequenceAbort   = false; // cooperative stop, honoured BETWEEN beats only (D2)
```

### 3. `observationRefreshDetail` gains a proposals opt-out — replaces `index.html:12228-12240`

Signature becomes `observationRefreshDetail({ proposals = true } = {})`; the proposals call at
the end becomes conditional. All four existing call sites
(`observationStepRun`, `observationStopRun`, `observationInjectEvent`, `observationSelectRun`)
stay no-arg and keep their current behaviour. Do NOT duplicate the body into a second
"transcript only" function. Prepend this comment verbatim:

```js
/** `proposals:false` is used per beat inside a sequence (TICKET-0053, F1):
 *  produce_run_proposals runs ONCE after the run closes
 *  (observation_runner.py:616-621), so polling /proposals per beat is a
 *  guaranteed-empty GET. The sequence calls this once more, with proposals,
 *  when it ends. */
```

### 4. `observationRunBeats()` — new, placed immediately after `observationStepRun()`

Behaviour, exhaustively:

1. Return immediately if `!obsActiveRunId` or `obsSequenceRunning`.
2. Read `#obs-beat-count`; `total = Number.isFinite(parsed) && parsed >= 1 ? parsed : 1`.
3. Set `obsSequenceRunning = true`, `obsSequenceAbort = false`, call `_obsSetSequenceUi(true)`.
4. Loop `i` from `0` to `total - 1`:
   a. If `obsSequenceAbort`, record `interrompu apres N beat(s)` and break.
   b. Write `beat ${i + 1}/${total}…` into `#obs-sequence-progress`.
   c. `await api('/api/observation/runs/' + obsActiveRunId + '/step', { method: 'POST' })`
      inside its own try/catch. On throw: write the message into `#obs-launch-status` as
      `<div class="r-err">`, record `arrete sur erreur apres N beat(s)`, break.
   d. Increment the executed count; update `#obs-active-run-status` to
      `${result.run.id} (${result.run.status})`, exactly as `observationStepRun` does today
      (`index.html:12165`).
   e. `await observationRefreshDetail({ proposals: false })`.
   f. If `result.run.status !== 'running'`, record
      `run ferme (${result.run.stop_reason || result.run.status}) apres N beat(s)` and break.
5. In a `finally`: clear `obsSequenceRunning`, call `_obsSetSequenceUi(false)`, write the
   recorded note (or `N/total beat(s)`) into `#obs-sequence-progress`, then
   `await observationRefreshDetail()` (with proposals) and `await observationLoadRunList()`.

Docstring, verbatim:

```js
/** Multi-beat sequence (TICKET-0053, A1): X consecutive beats driven from the
 *  client, one POST /step per beat — the same single-beat path a manual click
 *  takes. There is no backend loop route by design
 *  (routes/observation.py:1-15); this function IS the client that docstring
 *  describes, not a workaround for it. The stop rule is NOT re-derived here:
 *  max_beats counts non-event beats only (observation_runner.py:253-256) and
 *  that arithmetic stays server-side — the loop simply exits when the run
 *  stops reporting status 'running'. Stops on the first of: X beats done, the
 *  run leaving 'running', a step error, an interrupt. */
```

### 5. `observationAbortSequence()` — new, immediately after `observationRunBeats()`

```js
/** D2: raises the flag only. The beat in flight completes and persists — a
 *  cancelled request would abandon a beat whose observation_beat and
 *  observation_intent rows are already being written (history is sacred). */
function observationAbortSequence() {
  if (!obsSequenceRunning) return;
  obsSequenceAbort = true;
  document.getElementById('obs-sequence-progress').textContent = 'interruption apres ce beat…';
}
```

### 6. `_obsSetSequenceUi(active)` — new helper

Disables `#obs-run-beats-btn`, `#obs-step-btn`, `#obs-inject-btn` while `active`; shows
`#obs-abort-btn` while `active` and hides it otherwise. Touches no other control.

### 7. Guards on the two existing handlers

- `observationStepRun()` (`index.html:12161`): add `if (obsSequenceRunning) return;` after the
  existing `if (!obsActiveRunId) return;`. Belt-and-braces behind the disabled attribute.
- `observationStopRun()` (`index.html:12172`): set `obsSequenceAbort = true;` as its first
  statement, with the comment
  `// D3: closing the run also ends any sequence — cleanly, not via a 422 next iteration.`
  Nothing else in that function changes.

### 8. Verify check — new Rule 7 in `tooling/verify/checks/observation_surface.py`

Add a `check_rule7_sequence_client_side(html)` function, called from `main()` after
`check_rule6_no_direct_write()`. It asserts, on the brace-balanced body of
`function observationRunBeats()` obtained via the module's existing `_braced_block` helper
(`observation_surface.py:48-65`), and increments `_renderer_functions_found` once the body is
found:

- **7a** the body is found (otherwise `fail` and return);
- **7b** the body contains `/step` — the sequence reuses the existing route;
- **7c** the body contains `obsSequenceRunning`, `obsSequenceAbort`, and the substring
  `!== 'running'` — the in-flight guard, the interrupt and the closure exit are all present;
- **7d** the body contains NEITHER `max_beats` NOR `quiescence` — the stop rule is not
  re-derived client-side (ticket finding 4, E1);
- **7e** `ROUTES_FILE`'s source contains no `"/steps"` path literal, and its AST contains no
  `ClassDef` field named `count`, `n` or `beats` — A1 asserted structurally.

Raise the vacuous-proof guard at `observation_surface.py:200` from
`_renderer_functions_found < 3` to `< 4`, and extend the module docstring's numbered rule list
with Rule 7 and the renumbered vacuous-proof entry (currently listed as item 7).

Red-test it: temporarily rename `observationRunBeats` in `index.html`, confirm the check
FAILS, restore. Report the observed failure line in the step report.

## Scope OUT

1. **No backend change whatsoever.** No new route, no `steps`/`batch` endpoint, no new
   function in `observation_runner.py`, no signature change to `step_run`, `run_bounded`,
   `run_one_beat`, `stop_run` or `inject_event`. `observation_runner.py` and
   `cockpit/routes/observation.py` must show zero diff against `main`.
2. **Do not expose `run_bounded` over HTTP.** It stays the Python-level entry point for
   scripts and the verify check (`routes/observation.py:9-10`).
3. **No unattended / background execution** (D-0053-unattended). No SSE, no polling loop, no
   task queue, no "run until it finishes even if the tab closes".
4. **No persistence of the sequence** (D-0053-sequence-record). No column, no row, no
   `observation_run` field recording that beats were batched. No schema change: this step
   touches no table, adds no version.
5. **No client-side beats-remaining arithmetic**, no clamp of X to the remaining allowance, no
   "X exceeds max_beats" warning. `max_beats` bounds the run; C2 handles the closure.
6. **Do not change `max_beats`, `quiescence_limit`, or any launch-form default**
   (`index.html:1551-1561`). The sequence count is a separate, non-persisted UI value.
7. **Do not touch `observationStartRun`** (`index.html:12121-12159`) — no auto-sequence on
   start, no "start and run X beats" combined control.
8. **Do not touch `_obsRenderTranscript`** (`index.html:12279`), `_obsRenderRunDetail`
   (`index.html:12245`) or `_obsRenderIntents` (`index.html:12293`). Rules 3 and 4 of
   `observation_surface.py` anchor on their exact signatures.
9. **Do not add an eighth observation check module** (H1). Rule 7 extends the existing
   `observation_surface.py`.
10. **No repetition work.** The beat-8 similarity onset is D-0052-repetition, a separate
    workstream. Running more beats faster is not a repetition fix and must not be presented
    as one.
11. **No abort of an in-flight beat**, no `AbortController`, no request cancellation (D2).
12. **No approve/reject on the proposals panel** — still read-only here (BRIEF-0051-f).

## Invariants to defend

- **History is sacred.** D2 exists for this invariant: interruption never cancels a beat
  mid-write. The only way a beat is not persisted is a backend failure, already handled by
  `_run_beat_safely` (`observation_runner.py:511-522`).
- **Single canon-write authority (S-norme).** Untouched: the sequence issues no write of its
  own, it calls an existing route whose writes already funnel through
  `observation_writes.py`. Rule 6 of `observation_surface.py` continues to assert this.
- **No structure without a reader (E2).** Nothing is stored by this step, so nothing can lack
  a reader; D-0053-sequence-record records why the sequence is deliberately not persisted.
- **Fail-closed over advisory.** Rules 7d and 7e are refusals, not warnings: a future
  re-derivation of the stop rule in JS, or a batch route sneaking in, fails the gate.
- **Model proposes, code judges** — unaffected, no model call is added or altered. The
  sequence changes only how often the existing calls are triggered.

## Done means

- [ ] `git diff --stat` shows `src/world_engine/cockpit/index.html` and
      `tooling/verify/checks/observation_surface.py` only (plus the docs of the next section).
      `observation_runner.py` and `routes/observation.py`: zero diff.
- [ ] `python tooling/verify/checks/observation_surface.py` prints PASS with 4 renderer
      function(s) verified.
- [ ] The red-test is reported: with `observationRunBeats` renamed, the check FAILS on Rule
      7a; restored, it PASSES.
- [ ] `python tooling/verify/checks/observation_runner.py` still PASSES (unchanged code path).
- [ ] `python tooling/verify/checks/module_budget.py` and
      `python tooling/verify/checks/json_ui_boundary.py` PASS.
- [ ] Live, on a location with >= 2 NPCs and active goals: a run started, "Faire X beats" with
      X=5, five beats appear one after the other, the transcript grows between each, the
      progress span counts `beat 1/5` … `beat 5/5`.
- [ ] Live: a run started with `max_beats=3`, sequence requested with X=10 -> exactly 3 beats,
      progress span reads `run ferme (max_beats) apres 3 beat(s)`, `#obs-launch-status` shows
      no error.
- [ ] Live: "Interrompre" pressed during a 20-beat sequence -> the sequence ends after the
      beat then in flight, the run detail still shows status `running`, and "⏭ Un beat"
      produces one further beat.
- [ ] Live: "Arrêter" pressed during a sequence -> the run shows `stopped` / `creator_stop`,
      the sequence ends, no error is displayed.
- [ ] Live: Ollama stopped mid-sequence -> the sequence halts, the error text is visible in
      `#obs-launch-status`, and the run detail shows `failed` / `error`.
- [ ] Live: "Faire X beats" double-clicked -> one sequence only; the beat count after it
      equals X, not 2X.
- [ ] Live: during a sequence the proposals panel is not refetched (observable in the network
      tab or the server log: one `/proposals` GET at the end, not one per beat).
- [ ] `/review-step` and `/close-step` run and reported — engine-adjacent code (a verify check)
      is touched.

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md` — one new section,
  `OBSERVATION MULTI-BEAT SEQUENCE — client-driven loop (TICKET-0053, BRIEF-0053-a, no schema change)`,
  recording: A1 and the two rejected alternatives with the reason
  (`routes/observation.py:1-15`'s process-model finding); the Interrompre / Arrêter split (D1,
  D3); why interruption is between-beats only (D2); why no client-side allowance arithmetic
  exists (E1 + `_regular_beat_count`'s event exemption); and both named deferrals
  (D-0053-unattended, D-0053-sequence-record).
- `DECISIONS_INDEX.md` — regenerate, do not hand-edit:
  `python tooling/glue/gen_decisions_index.py`.
- `world-engine-schema.md` and `world-engine-schema-changelog.md` — NO entry. No table, no
  column, no version. State this explicitly in the step report so the absence is a recorded
  finding rather than an omission.
- `CLAUDE.md` — no change.

---

## Drafting decisions flagged (protocol rule 8)

Judgment calls embedded above that you may want to reverse before sending:

1. **Client-side loop rather than a backend batch route** (A1). Grounded in
   `routes/observation.py:1-15`, but it does mean a closed tab kills the sequence. If you want
   unattended runs, that is a different ticket with an async design — say so and I re-author.
2. **Default X = 5** in the input. Arbitrary; `max_beats` default is 30. Say a number and I
   change it.
3. **"Interrompre" as a separate button** rather than making "Arrêter" do double duty. Costs a
   control in an already busy row; buys a pause that does not burn the run.
4. **Per-beat refresh of the full run detail**, not just the transcript. It is one extra GET
   per beat against a route that also re-reads intents; a beat costs several model calls, so
   the GET is noise by comparison — but it is a choice, not a necessity.
5. **`observationRefreshDetail` gets a parameter** instead of a second narrow function. Changes
   an existing 4-call-site signature (compatibly, via a default). The alternative duplicates
   six lines.
6. **Rule 7d forbids the literals `max_beats` and `quiescence`** inside the sequence body. This
   is a crude proxy for "no re-derived stop rule" and would also reject a purely informational
   display of those values inside that function. I judged that acceptable — that display
   belongs in `_obsRenderRunDetail`, which already has it.
7. **Rule 7e scans `routes/observation.py` for a `/steps` literal and for body fields named
   `count`/`n`/`beats`.** It is a denylist, so a batch route named something else slips
   through. A stricter form (allowlist of route paths in that module) would be more robust but
   touches more of the check; say the word and I tighten it.
8. **No cap on X** (E1). A fat-fingered `500` will sit there making model calls until
   `max_beats` stops it — which it will, but slowly. A confirmation above, say, 30 is one line
   if you want it.
9. **Progress text and labels in French**, matching the surrounding surface; the artifacts and
   comments stay English per convention.
