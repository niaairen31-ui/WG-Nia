# BRIEF — Step "migrate Observation to a shell-native Svelte surface"

## Context

Observation is the last Creation-era surface still rendered by the legacy
document. `BRIEF-0060-a` repaired `observation_surface.py` against that
document; this brief moves the surface out of it and re-homes the check onto
the result, in the same brief, so no fail-closed guard is red between commits.

Measured scope (RECON-0060-a): markup `index.html:612..683` (72 lines), code
`index.html:2834..3189` (356 lines, contiguous), 18 functions, longest 47
lines, no graph, nine stable API endpoints, zero Observation-specific rules in
the inline `<style>` block.

Three defects are fixed **by** the migration rather than beside it:

- `.r-warn` / `.r-err` are defined only in `creation.css:137-138`, which the
  legacy document no longer links — every Observation error currently renders
  uncoloured. Decision **D1** puts them in the component's scoped `<style>`.
- `WORLD_ID` (`index.html:697`) is written once at legacy boot (`:1832`) and
  never refreshed by `activateWorldCascade`
  (`frontend/src/creation/tabs.js:703`), so a run started after a Header world
  switch is created in the previously active world. Decision **F1** removes
  the stale global from the path entirely.
- `obsInitialized` (`index.html:2843`) is a one-shot latch, so the location
  list never reloads. **F1** replaces it with a world-reactive effect.

Locked decisions governing this brief: **D1**, **E1** (full Svelte templating,
no `{@html}`), **F1**, **H1** (two files under `frontend/src/observation/`),
**I2** (`legacy_mount.py` rule 4 gains a retired-surface DOM assertion).

## Mini-RECON — verify before writing

Report `file:line` for each. **If any anchor does not resolve as described,
STOP and escalate — do not adapt.**

1. `src/world_engine/cockpit/index.html` — confirm the file is 3205 lines;
   the Observation markup opens at `<div class="app-view"
   id="observation-view"` and closes at `</div><!-- #observation-view -->`;
   the Observation code block runs from `let obsInitialized` to the end of
   `_obsLoadProposals`, immediately before the `DOMContentLoaded` listener.
   Report the exact first and last line of each range.
2. `src/world_engine/cockpit/index.html` — confirm `showPlayView()` and
   `showObservationView()` are each defined once, and report every line in
   `showPlayView`'s body that names `observation-view` or
   `mode-tab-observation`.
3. `src/world_engine/cockpit/index.html` — confirm the header contains
   exactly two `.mode-tab` buttons and report their lines.
4. Confirm **no** function outside the Observation range calls any
   `observation*` or `_obs*` name, and **no** Observation function calls any
   Play-only name. The four shared helpers `api`, `esc`, `shortId`, `fmtDate`
   are the expected exceptions — report which of the four Observation
   actually uses.
5. `frontend/src/legacy/registry.js` — confirm `LEGACY_MOUNTS` has exactly two
   entries and that `observation` declares `retiredBy: 'TICKET-0060'`.
6. `frontend/src/App.svelte` — confirm `onObservationOpenPrompt`, the
   `legacyDocument().addEventListener('observation:open-prompt', …)` line, and
   the `.legacy-slot` `style:display` expression; report all three lines.
7. `frontend/src/creation/mount.js` — confirm the island mount passes
   `legacyDoc: node.ownerDocument`, and that Creation's containers live in
   the shell document, so `Prompts.svelte`'s `creation:open-prompt` listener
   is bound to the shell document.
8. `frontend/src/creation/sheetRequest.svelte.js` — confirm `export async
   function api(path, options)` exists and is byte-equivalent in behaviour to
   the legacy `api()` at `index.html:731`.
9. `frontend/public/creation.css` — confirm `.r-warn` and `.r-err` are
   declared there and **nowhere else**, and confirm zero consumers under
   `frontend/src`.
10. `tooling/verify/checks/legacy_mount.py` — report the line range of rule 4
    (`showFn` resolves as a top-level function in the legacy document).
11. Run `WORLD_ENGINE_ENV=dev PYTHONPATH=src python tooling/verify/checks/observation_surface.py`
    and confirm it is GREEN before you change anything. If it is red, the
    tree is not post-`BRIEF-0060-a` — STOP.

## Scope IN

Five commits, in this order. **`frontend_build_fresh.py` is expected RED on
commits 1–4 and is a gate point only at HEAD**: rebuild the bundle and commit
`cockpit/static/` once, in commit 5. Do not rebuild five times.

### Commit 1 — `frontend/src/observation/observation.svelte.js`

New directory, new module. State plus logic; no template, not yet imported by
anything.

Import `api` from `../creation/sheetRequest.svelte.js` and `serverState` from
`../lib/serverState.svelte.js`. Do **not** re-implement fetch/error handling.

Export a single `$state` object named `observationState` carrying exactly
these fields — this is the seam the component renders and must not be
renamed or reshaped:

```
locations, selectedLocationId, presentNpcs, presentMessage,
params { maxBeats, quiescence, cooldown, debtWeight, propensityMode, mjNarration },
launchErrors, activeRunId, activeRunStatus, beatCount, sequenceRunning,
sequenceAbort, sequenceProgress, eventText, runs, runsLoading,
selectedRunId, detail, beats, proposals, proposalsMessage
```

`presentNpcs` is `null` before any load and an array after. `launchErrors` is
an array of strings — every current `r-err` write becomes an entry in it, and
the empty array is the no-error state. `presentMessage` and `proposalsMessage`
carry the single-string warning/empty states.

Port these functions, preserving behaviour exactly:

| Legacy | New export | Behaviour to preserve verbatim |
|---|---|---|
| `observationLoadLocations` | `loadLocations()` | `GET /api/locations` |
| `observationLocationChanged` | `selectLocation(id)` | `GET /api/observation/locations/{id}/present-npcs`; the no-NPC case sets `presentMessage` to `Aucun PNJ présent à cet endroit.` |
| `observationStartRun` | `startRun()` | `POST /api/observation/runs`; a 422 populates `launchErrors` with one entry per failure; `Choisissez un lieu.` when no location is selected |
| `observationStepRun` | `stepRun()` | `POST …/step` |
| `observationRunBeats` | `runBeats()` | the sequence loop, unchanged in every respect below |
| `observationAbortSequence` | `abortSequence()` | raises `sequenceAbort` only |
| `observationStopRun` | `stopRun()` | `POST …/stop` |
| `observationInjectEvent` | `injectEvent()` | `POST …/events` |
| `observationLoadRunList` | `loadRunList()` | `GET /api/observation/runs` |
| `observationSelectRun` | `selectRun(id)` | sets `selectedRunId`, then refreshes detail |
| `observationRefreshDetail` | `refreshDetail(opts)` | `GET …/{id}`; `opts.proposals === false` skips the proposals fetch |
| `_obsLoadProposals` | `loadProposals(runId)` | `GET …/{id}/proposals` |

`OBS_OUTCOME_LABEL` moves here unchanged as a module-level frozen constant.

**`runBeats()` — invariants that must survive the port, verbatim in
semantics:**

- The in-flight guard is the first statement: a call while
  `sequenceRunning` is true returns immediately. One sequence per surface,
  ever.
- `sequenceAbort` is checked **between** beats only. A beat in flight always
  completes. Never abort a request mid-flight — its `observation_beat` and
  `observation_intent` rows are already being written, and history is sacred.
- The loop reuses `POST /api/observation/runs/{id}/step`. It must not call any
  batch route, and must not re-derive the stop rule: the words `max_beats` and
  `quiescence` must not appear anywhere in the function.
- The closure exit is the server's: `result.run.status !== 'running'` breaks
  the loop with the note `run fermé (…) après N beat(s)`.
- A step error breaks the loop with `arrêté sur erreur après N beat(s)` and
  writes the message into `launchErrors`.
- The `finally` block always clears `sequenceRunning`, writes the final
  progress note, refreshes the detail and reloads the run list.

**F1 — the world is read, never cached.** `startRun()` sends
`world_id: serverState.worldId`, read at call time. There is no module-level
world variable, no `initialized` latch, and no world argument threaded through
the call chain. Export:

```js
export async function reloadForWorld() { … }   // loadLocations() + loadRunList(),
                                               // and resets selection/run state
```

Add this comment above it, verbatim:

```js
/* TICKET-0060 (BRIEF-0060-b, F1). The legacy surface read a WORLD_ID global
   written once at document boot (index.html:1832) and never refreshed by
   activateWorldCascade (creation/tabs.js:703) -- so a run started after a
   Header world switch was created in the PREVIOUSLY active world, and its
   mutation proposals with it. Nothing here caches a world: startRun reads
   serverState.worldId at call time, and this function is driven by an
   effect on that same field. The server still trusts the client's
   world_id (routes/observation.py:48-59); hardening that is TICKET-0060
   decision F3, deferred to its own ticket after TICKET-0061. */
```

### Commit 2 — `frontend/src/observation/Observation.svelte`

Template plus scoped styles. Still not imported by `App.svelte`.

Props: `let { active = false } = $props();` — visibility only, exactly as
`Creation.svelte` does. The component is always mounted and never destroyed.

**E1 — real templates, no `{@html}` anywhere in this file.** All four string
renderers become markup:

- `_obsRenderRunDetail` → the status/stop badges, the location name, the
  five pinned parameters (`cooldown_beats`, `debt_weight`, `propensity_mode`,
  `mj_narration`, `model`) and an `{#each run.templates}` block rendering
  `usage` plus a `v{version}` control.
- `_obsRenderTranscript` → `{#each beats}` of `<details>` elements, each with
  the beat index, an outcome badge whose class is `badge b-{beat.outcome}`,
  the actor/line summary, the optional MJ narration, and the intents block.
- `_obsRenderIntents` → `{#each beat.intents}` with the NPC name, the
  `call_status` badge, the `sélectionné` badge when selected, the derived
  `raison (dérivée)` when not, the four arbitration components
  (`act`, `urgency`, `propensity`, `cooldown_active`, `debt_score`,
  `final_score`) with the same `toFixed(2)` formatting, and the optional
  `why` quote.
- `_obsLoadProposals`'s render half → `{#each proposals}` with a
  `badge b-{p.mutation_type}` badge, the target table and truncated beat id,
  and the rationale.

Every `${esc(...)}` disappears: Svelte interpolation escapes. Do not import,
re-create, or port `esc`.

Preserve the two-panel structure and every id used as a styling or test
anchor: `#observation-view`, `#obs-launch-panel`, `#obs-detail-panel`.
The other 24 ids were behavioural hooks for `getElementById` and have no
styling rule anywhere — drop them rather than carrying dead attributes, and
bind the corresponding controls directly.

Keep every visible French string byte-identical, including
`Scène observée — lancer`, `Sélectionnez un lieu.`,
`Aucun PNJ présent à cet endroit.`, `Runs précédents`, `Aucun beat.`,
`Aucune proposition.`, `Aucune proposition produite par ce run.`,
`Aucun candidat (événement).`,
`Propositions produites (F3 — jamais dans la file de revue)`, and the six
button labels with their symbols (`▶ Démarrer`, `⏭ Un beat`,
`⏩ Faire X beats`, `⏸ Interrompre`, `⏹ Arrêter`, `⚡ Injecter`).

**D1 — the two stranded rules land here, scoped:**

```css
  .r-warn { color: var(--yellow); }
  .r-err  { color: var(--red); }
```

Add this comment above them, verbatim:

```css
  /* TICKET-0060 (BRIEF-0060-b, D1). These two rules lived in
     frontend/public/creation.css, which cockpit/index.html stopped linking
     when TICKET-0059 retired the Creation mount -- stylesheet_partition.py
     rule5 ties that link's lifetime to LEGACY_MOUNTS.creation, so the
     removal was structurally forced. Observation kept applying both
     classes from inside that document, at nine sites, and every error
     message rendered uncoloured. They are Observation's only two exclusive
     rules and have no consumer under frontend/src, so they belong in this
     component's scoped block rather than in any global sheet: no selector
     is added to the partition, and rule7's SCOPED(F) term covers them.
     Commit 4 deletes them from creation.css. */
```

**F1 — the world-reactive effect.** One `$effect` reading
`serverState.worldId` and calling `reloadForWorld()`. No `onMount` load, no
`initialized` flag, no load-on-first-activation. Cost accepted: Observation
performs two reads at shell boot even if never visited, the same as
`Creation.svelte`.

**The prompt link.** The `v{version}` control calls, on this document:

```js
navigate('creation', 'prompts');
document.dispatchEvent(new CustomEvent('creation:open-prompt', { detail: { templateId } }));
```

`navigate` from `../lib/router.js`. This is the same signal
`App.svelte:44-49` re-dispatched; it now originates in the right document.

### Commit 3 — wire the shell

- `App.svelte`: import `Observation` and render
  `<Observation active={currentSurface === 'observation'} />` as a sibling of
  `<Creation …>`.
- `App.svelte`: `applyRoute` stops calling `showSurface('observation')`. Only
  `play` still routes through the legacy bridge.
- `App.svelte`: the `.legacy-slot` `style:display` expression becomes
  visible for `play` only.
- `App.svelte`: delete `onObservationOpenPrompt` and its
  `legacyDocument().addEventListener('observation:open-prompt', …)`
  registration. **Leave `initCreationMount(legacyDocument())` in place** — its
  `mutations:proposed` listener originates in Play and is TICKET-0061's.
- `Header.svelte` already renders both mode-tabs and needs no change; confirm
  and report rather than editing.

At the end of this commit the surface is live and the legacy one is dead code.

### Commit 4 — retire the legacy surface

- `index.html`: delete the `#observation-view` block in full.
- `index.html`: delete the `mode-tab-observation` button.
- `index.html`: delete `showObservationView()`.
- `index.html`: delete the Observation banner comment, the seven module
  globals, `OBS_OUTCOME_LABEL`, and all 18 functions.
- `index.html`: edit `showPlayView()` so it names no retired surface. Every
  reference to `observation-view` and `mode-tab-observation` must go —
  `getElementById` would return `null` and throw. Leave a one-line comment
  citing TICKET-0060.
- `frontend/src/legacy/registry.js`: delete the `observation` entry. Update
  the header comment to state that `play` alone remains, retiring at
  TICKET-0061. **Do not touch
  `tooling/verify/baselines/legacy_mounts.baseline`** — it is a shrink
  ceiling, not a required set.
- `frontend/public/creation.css`: delete `.r-warn` and `.r-err`.
- `CLAUDE.md`: amend the two stale lines. Line 18's clause about Creation
  being "partly Svelte islands mounted into the legacy document" and about
  "the remaining Creation tabs" is already false on `main`; line 414 must
  narrow the legacy host to Play, retiring at TICKET-0061. **CLAUDE.md is
  under an enforced line budget (`claude_md_contract.py`) — amend the
  existing lines in place; do not add lines.**

### Commit 5 — re-home the guards, rebuild

- `tooling/verify/checks/observation_surface.py`: re-anchor onto
  `frontend/src/observation/`. Every assertion is preserved, none softened:
  - Rule 1 becomes a mount assertion: `App.svelte` renders `Observation` with
    an `active` prop derived from the surface, and `observation` is absent
    from `LEGACY_MOUNTS`.
  - Rule 2 is unchanged (it already reads `page_contract.py` and `tabs.js`).
  - Rule 3 still requires four outcome literals in `OBS_OUTCOME_LABEL` and
    `.b-silence` / `.b-degraded` resolving to **different** class bodies in
    `shared.css`.
  - Rule 4 still requires the run-detail renderer to name `cooldown_beats`,
    `debt_weight`, `propensity_mode`, `templates`, `template_id`, `version`.
  - Rule 5 unchanged.
  - Rule 6 unchanged.
  - Rule 7 still asserts the client-side sequence: `/step` reused,
    the three guard tokens present, `max_beats` / `quiescence` absent, no
    `/steps` route and no batch-count field.
  - The vacuous-proof guard still FAILS below four collected renderers and
    four outcome literals.
  - Add a rule asserting `{@html}` appears **nowhere** in
    `frontend/src/observation/` — E1 made scoped styles possible and
    `{@html}` would silently break `.r-err` (D1).
- `tooling/verify/checks/legacy_mount.py` — **I2**: extend rule 4 so a
  `showFn`'s body may not reference the DOM of any surface absent from
  `LEGACY_MOUNTS`. For each registry key, derive its view/tab id tokens
  (`{key}-view`, `mode-tab-{key}`); for each declared `showFn`, FAIL if its
  body names a token belonging to a key that is not in the registry. Add this
  comment verbatim:

  ```python
  # TICKET-0060 (BRIEF-0060-b, I2). Rule 4 asserted only that a showFn
  # EXISTS. Retiring a surface leaves the surviving showFn calling
  # getElementById on markup that has just been deleted -- a null
  # dereference at the first surface switch, invisible to every other
  # check. This is a guard on the RETIREMENT, not on check staleness: the
  # TICKET-0059 lapse was a stale check over correct code, which is
  # BRIEF-0060-d's corpus gate, not this rule.
  ```
- Run `npm run build` in `frontend/` and commit the resulting
  `src/world_engine/cockpit/static/` output.

### Red tests

Perform, capture the transcript, revert. No mutation is committed.

- **I2.** Re-add `document.getElementById('observation-view')` to
  `showPlayView`. `legacy_mount.py` must FAIL naming the retired surface.
- **observation_surface Rule 1.** Remove the `<Observation …>` line from
  `App.svelte`. The check must FAIL.
- **The `{@html}` rule.** Insert `{@html ''}` into `Observation.svelte`. The
  check must FAIL.
- **D1.** Delete the two scoped rules from `Observation.svelte`.
  `stylesheet_partition.py` must still PASS — and report that it does. This
  is the honest result: rule7 does not yet cover the legacy direction, and
  proving it silent here is what motivates `BRIEF-0060-c`.

## Scope OUT

1. **No backend change.** Not `routes/observation.py`, not
   `observation_runner.py`, not any `/api/observation/*` handler. Decision F3
   defers server-side world derivation to a named ticket after TICKET-0061.
2. **No Play migration.** Play's markup, its four sub-tabs, `loadScene`,
   the spatial canvas, `loadBootstrap`, and the `WORLD_ID` global itself all
   stay. `WORLD_ID` remains stale for Play's own paths — that is TICKET-0061's
   problem, not a defect this brief may fix.
3. **Do not delete `index.html`**, do not remove `LegacyFrame`, do not empty
   `LEGACY_MOUNTS`. One mount survives. TICKET-0061 owns the decommission.
4. **Do not touch `legacy_mounts.baseline` or `legacy_calls.baseline`.**
5. **Do not extend `stylesheet_partition.py`.** The rule7 `APPLIED`-domain
   extension is `BRIEF-0060-c`. The fourth red test above will show it silent;
   report that and move on.
6. **Do not build the corpus gate** or edit `tooling/verify/run.py`. That is
   `BRIEF-0060-d`.
7. **No graph.** Observation renders none. Do not import `Graph.svelte`, do
   not add a registry entry, do not touch `graph_primitive.py`.
8. **Not a Creation island.** Observation is shell-native, a sibling of
   Creation. Do not add an entry to `frontend/src/creation/registry.js`, do
   not route it through `creation/mount.js`, do not give it a `CREATION_TABS`
   entry — `observation_surface.py` Rule 2 exists precisely to forbid that.
9. **No approve/reject on proposals.** The proposals panel is read-only (F3
   visibility from TICKET-0051). Reached through `observation_mutation_link`,
   never through `/api/mutations`, never through the Review Queue.
10. **No third file.** H1 is two files. Do not extract a `RunDetail.svelte`,
    a `Transcript.svelte`, or a shared badge component — there is one reader.
11. **Do not "improve" the arbitration display.** The four components, the
    `toFixed(2)` formatting, and the `raison (dérivée)` label are the
    surface form of TICKET-0051's measurement claim. Port them, do not
    redesign them.
12. **Do not rebuild the bundle on commits 1–4.**

## Invariants to defend

- **History is sacred.** `runBeats`'s cooperative abort exists because a
  cancelled in-flight request would abandon a beat whose `observation_beat`
  and `observation_intent` rows are mid-write. Any port that cancels a
  request, races the loop, or aborts within a beat defeats this.
- **The stop rule belongs to the server.** The client counts beats; it never
  decides closure. `max_beats` and `quiescence` must not appear in the client
  module.
- **Single canon-write authority.** This brief writes no canon. Every call is
  an existing route.
- **Structural, not instructional, exclusion.** The proposals panel is
  read-only because the route exposes no write, not because the component
  declines to offer one.
- **Fail-closed guards never lapse.** Commit 5 re-homes the guards in the
  same brief that moves what they guard. At no commit boundary is a check
  asserting a file that has just been emptied.
- **No structure without a reader.** The 24 dropped ids had no styling rule
  and no remaining reader once `getElementById` goes.

## Done means

- [ ] `WORLD_ENGINE_ENV=dev PYTHONPATH=src` — `observation_surface.py`,
      `legacy_mount.py`, `legacy_call.py`, `stylesheet_partition.py`,
      `page_contract.py`, `creation_island.py`, `graph_primitive.py`,
      `module_budget.py`, `function_length.py`, `shell_height_chain.py` and
      `frontend_build_fresh.py` all exit 0 at HEAD.
- [ ] `observation_surface.py`'s PASS line still names four renderer
      functions and four outcome literals.
- [ ] `legacy_mount.py`'s PASS line reports **1 mount**.
- [ ] `grep -rn "observation" src/world_engine/cockpit/index.html` returns
      nothing but comments.
- [ ] `grep -rn "r-warn\|r-err" frontend/public/` returns nothing.
- [ ] `grep -rn "{@html" frontend/src/observation/` returns nothing.
- [ ] `grep -n "WORLD_ID" frontend/src/observation/` returns nothing.
- [ ] Both new files are under 1000 lines; no new function exceeds 80.
- [ ] `git diff --stat` per commit matches the five-commit division above,
      with the bundle rebuilt only in commit 5.
- [ ] Four red-test transcripts are in the execution report, each showing the
      expected verdict, with every mutation reverted and `git status` clean.
- [ ] Live: the Observation mode-tab renders the surface in the shell, the
      legacy iframe is hidden for it, and `/observation` loads it on a cold
      boot.
- [ ] Live: launch panel populates; an empty location shows the no-NPC
      warning **in colour**; a refused start shows its failures **in colour**.
- [ ] Live: start → one beat → multi-beat sequence → interrupt mid-sequence →
      stop, with the progress indicator and abort button behaving as before.
- [ ] Live: inject an event; it appears in the transcript.
- [ ] Live: `acted` / `silence` / `degraded` / `event` are distinguishable at
      a glance and `degraded` never looks like `silence`.
- [ ] Live: the run-detail panel shows the five pinned parameters and the
      per-usage template id/version; proposals are read-only.
- [ ] Live: the `v{version}` link navigates to Creation → Prompts with that
      template selected, both cold and on warm re-navigation.
- [ ] **Live: switch the active world in the Header, then start a run — the
      run is created in the newly active world and the location select has
      reloaded.**
- [ ] Live: Play is unaffected — mode-tab, four sub-tabs, scene view, spatial
      canvas.

## Docs to update

- `CLAUDE.md` lines 18 and 414, amended in place, within the enforced budget
  (commit 4).
- `tooling/standards/ARCHITECTURE_DECISIONS.md`: one appended TICKET-0060
  section covering D1 (why two rules moved into a scoped block rather than a
  global sheet), E1 (why `{@html}` is forbidden and how it is enforced), F1
  (the stale-world path, its consequence, and why the server-side half is
  deferred to F3), H1 (the two-file cut and the `frontend/src/observation/`
  home), and I2 (a retirement guard, explicitly not a staleness guard).
- `CHANGELOG.md`: a TICKET-0060 entry, no schema change, written for a reader
  of the cockpit — what they will and will not notice.
- No schema change; `world-engine-schema.md` and its changelog are untouched.
