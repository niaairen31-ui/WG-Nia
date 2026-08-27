---
id: RECON-0060-a
ticket: TICKET-0060
title: Observation surface — pre-migration RECON
kind: RECON result (report-only)
status: complete
recon_target: niaairen31-ui/WG-Nia @ main (tarball, fetched this session)
recon_anchors:
  - src/world_engine/cockpit/index.html (3205 lines)
  - frontend/src/** (85 source files)
  - tooling/verify/checks/** (81 checks)
executed_by: Claude (chat), stdlib-only container
---

# RECON-0060-a — Observation surface

**Report-only.** No file was modified, no check was edited, no baseline was
touched. Every line reference below is anchored to `main` as fetched this
session and will drift as tickets land.

Every claim is tagged **[M]** (measured this session, with the command or
anchor that produced it) or **[I]** (inference — stated as such, never as a
finding). The brief author must not promote an **[I]** to a Scope IN item
without a mini-RECON re-measurement.

---

## PART A — State of `main`

### A1. Ticket statuses [M — `tooling/tickets/*.md` frontmatter]

| Ticket | Subject | `status` |
|---|---|---|
| TICKET-0055 | frontend build + serving foundation | `done` |
| TICKET-0056 | cockpit shell + surface boundary | `done` |
| TICKET-0057 | graph primitive | `done` |
| TICKET-0058 | Creation spine migration | `done` |
| TICKET-0059 | Creation periphery + mount retirement | `live-gate` |
| TICKET-0062 | location sheet effect cycle | `done` |
| TICKET-0063 | cockpit stylesheet partition | `live-gate` |
| TICKET-0064 | Creation stylesheet coverage | `live-gate` |
| TICKET-0065 | Creation shell seam regressions | `live-gate` |
| TICKET-0066 | static asset freshness | `live-gate` |

No `TICKET-0060-*.md` exists. The `live-gate` values reflect un-rewritten
checkboxes, not un-run gates: the creator performs the live gate and
intervenes on failure without re-authoring the file. Treat `live-gate` here
as "merged, human-verified, file not updated".

### A2. `TICKET-0064` landed [M — `tooling/verify/checks/stylesheet_partition.py`]

`stylesheet_partition.py` now carries **rule7 (coverage)** and passes on
`main`:

```
PASS: stylesheet_partition — 307 top-level selector(s) across
shared.css/creation.css/inline, zero duplicates; rule7 scanned 81
frontend/src file(s), 110 applied class name(s), 100 applied id name(s),
83 inline selector name(s), zero stranded
```

rule7's formula, as documented in the check's own header:

```
STRANDED(F) = APPLIED(F) ∩ INLINE − REACHABLE − SCOPED(F)
REACHABLE   = base rules in shared.css ∪ creation.css ∪ the built bundle
SCOPED(F)   = base rules in F's own <style> block
```

`APPLIED(F)` is literal `class="…"` / `id="…"` markup **in one
`frontend/src` file**. This scan domain is load-bearing for finding C2 below.

### A3. `index.html` size [M — `wc -l`]

12 708 → **3 205 lines**. Block structure:

| Block | Lines |
|---|---|
| `<head>` | 3 .. 433 |
| `<style>` (inline) | 12 .. 431 |
| `<body>` markup | 434 .. 684 |
| `<script>` | 685 .. 3199 |

92 top-level functions remain (was 540). Two surfaces remain: Play and
Observation.

---

## PART B — Observation surface inventory

### B1. The block is contiguous [M]

| Part | Lines | Size |
|---|---|---|
| markup `#observation-view` | 612 .. 683 | 72 ln |
| state block + banner comment | 2834 .. 2850 | 17 ln |
| functions | 2852 .. 3189 | 338 ln |

**Total ≈ 428 lines.** Unlike PART A2 of the workstream map (domains
physically interleaved, extraction is a function-by-function move), the
Observation code is one unbroken range. The preceding function is
`spatialTalkTo` (`:2485`), the following content is the `DOMContentLoaded`
bootstrap (`:3194`). Nothing is wedged inside it.

### B2. Function census [M]

18 functions: 13 `observation*` + 5 `_obs*`.

| Function | Line | Lines |
|---|---|---|
| `observationInit` | 2852 | 6 |
| `observationLoadLocations` | 2858 | 11 |
| `observationLocationChanged` | 2869 | 21 |
| `observationStartRun` | 2890 | 40 |
| `observationStepRun` | 2930 | 21 |
| `observationRunBeats` | 2951 | 47 |
| `observationAbortSequence` | 2998 | 6 |
| `_obsSetSequenceUi` | 3004 | 7 |
| `observationStopRun` | 3011 | 13 |
| `observationInjectEvent` | 3024 | 18 |
| `observationLoadRunList` | 3042 | 19 |
| `observationSelectRun` | 3061 | 12 |
| `observationRefreshDetail` | 3073 | 17 |
| `_obsRenderRunDetail` | 3090 | 40 |
| `observationOpenPrompt` | 3130 | 9 |
| `_obsRenderTranscript` | 3139 | 14 |
| `_obsRenderIntents` | 3153 | 20 |
| `_obsLoadProposals` | 3173 | 17 |

Longest function: 47 lines. `function_length.py` ceiling is 80,
`module_budget.py` is 1000 lines / 40 functions per file. **No budget
pressure at any plausible file cut.**

### B3. Module-level state [M — `index.html:2843..2850`]

```
obsInitialized, obsLocations, obsActiveRunId, obsSelectedRunId,
obsSequenceRunning, obsSequenceAbort, OBS_OUTCOME_LABEL
```

Six mutable globals plus one frozen label map. All Observation-exclusive —
no other function in the document reads them [M — grep across `index.html`].

### B4. No graph [M]

Zero occurrence of `graph`, `svg`, `cytoscape` or `canvas` in either the
markup range (612..683) or the code range (2834..3190).

**This answers open decision D-A of TICKET-0060 in the workstream map:
Observation renders no graph and is not a consumer of the graph primitive.**
`graph_primitive.py` needs no change from this ticket.

### B5. API surface [M]

Eight call sites, all against stable routes:

| Called from | Endpoint |
|---|---|
| `observationLoadLocations` | `GET /api/locations` |
| `observationLocationChanged` | `GET /api/observation/locations/{id}/present-npcs` |
| `observationStartRun` | `POST /api/observation/runs` |
| `observationStepRun`, `observationRunBeats` | `POST /api/observation/runs/{id}/step` |
| `observationStopRun` | `POST /api/observation/runs/{id}/stop` |
| `observationInjectEvent` | `POST /api/observation/runs/{id}/events` |
| `observationLoadRunList` | `GET /api/observation/runs` |
| `observationRefreshDetail` | `GET /api/observation/runs/{id}` |
| `_obsLoadProposals` | `GET /api/observation/runs/{id}/proposals` |

All nine route declarations are present in
`src/world_engine/cockpit/routes/observation.py:48..123`. **No backend change
is required by the migration itself** — the cross-cutting frontend-only rule
(workstream map PART C, item 2) holds. See finding C3 for the one place this
is contested.

### B6. Rendering shape [M]

Four functions build HTML as strings and assign `innerHTML`:
`_obsRenderRunDetail` (2090-char template), `_obsRenderTranscript`,
`_obsRenderIntents`, `_obsLoadProposals` — ≈ 90 lines combined. Six further
functions assign `innerHTML` for status/error strings.

Two **dynamic class expressions** exist:

```
index.html: badge b-${esc(b.outcome)}          (_obsRenderTranscript)
index.html: badge b-${esc(p.mutation_type)}    (_obsLoadProposals)
```

These are the rule7 complication (a class name that no static scan can
resolve) present concretely in the surface being migrated. Their resolved
values are covered: `.b-acted/.b-silence/.b-degraded/.b-event` at
`frontend/public/shared.css:150..153`, and the `mutation_type` family at
`shared.css:120..126`.

---

## PART C — Findings

### C1 — `observation_surface.py` is RED on `main` [M]

```
$ WORLD_ENGINE_ENV=dev PYTHONPATH=src python3 \
    tooling/verify/checks/observation_surface.py   # exit 1
FAIL: Rule 1: showObservationView() does not reference 'creation-view' — contract incomplete
FAIL: Rule 1: showObservationView() does not reference 'mode-tab-creation' — contract incomplete
FAIL: Rule 2: CREATION_TABS registry literal not found in index.html
FAIL: Rule 5: json_ui_boundary failed: ModuleNotFoundError: No module named 'sqlalchemy'
```

The first three are genuine. The fourth is an artifact of this RECON
container (see PART F).

**Cause.** `check_rule1_mode_tab` (`observation_surface.py:82..104`) asserts
that `showObservationView()`'s body names all six tokens of a *three-view*
contract. `TICKET-0059` (BRIEF-0059-l commit 4) took Creation out of the
legacy document, so `showObservationView` (`index.html:1808..1817`) now
toggles two views:

```js
function showObservationView() {
  document.getElementById('play-view').style.display = 'none';
  document.getElementById('observation-view').style.display = '';
  document.getElementById('mode-tab-play').classList.remove('active');
  document.getElementById('mode-tab-observation').classList.add('active');
  if (!obsInitialized) observationInit();
}
```

`check_rule2_no_creation_leak` (`:109..122`) looks for the `CREATION_TABS`
literal in `index.html`; that registry now lives in
`frontend/src/creation/tabs.js`.

**Why it lapsed silently.** `tooling/verify/run.py:13..23` parses only the
`### Machine-checkable` section of the ticket named on the command line and
runs the checks reachable through its `-> verify/checks/NAME.py` arrows.
`TICKET-0059`'s Machine section links **eleven** checks [M]:

```
creation_island, creation_return_nav, faction_roster_panel,
frontend_build_fresh, legacy_call, legacy_mount, location_tree,
modal_primitive, page_contract, review_component, stylesheet_partition
```

`observation_surface.py` is not among them. No gate has executed it since.

**Structural reading.** This is the same failure class as the TICKET-0064
CSS bug, one level up. There, a partition check proved non-duplication but
not coverage. Here, the G1 gate proves *the checks a ticket names* but not
*the corpus*. The cross-cutting rule "fail-closed guards never lapse"
(workstream map PART C, item 1) is currently **unverifiable by construction**:
nothing can detect a guard that no ticket references.

### C2 — Mirror-image CSS coverage loss: CONFIRMED [M]

`.r-warn` and `.r-err` are defined in exactly one place:

```
frontend/public/creation.css:137   .r-warn { color: var(--yellow); }
frontend/public/creation.css:138   .r-err  { color: var(--red); }
```

`cockpit/index.html` links `shared.css` only (`:6`); the `creation.css`
`<link>` was removed at `:7` by BRIEF-0059-l commit 4 — **structurally
required** by `stylesheet_partition.py` rule5, which ties that link's
lifetime to `LEGACY_MOUNTS.creation` existing. Removing the mount forced
removing the link.

Observation applies both classes at **nine sites**, all inside the legacy
document:

| Line | Context |
|---|---|
| 2879 | `r-warn` — "Aucun PNJ présent à cet endroit." |
| 2881 | `r-err` — present-NPC load failure |
| 2893 | `r-err` — "Choisissez un lieu." |
| 2916 | `r-err` — start-run validation failures (per failure) |
| 2926 | `r-err` — start-run exception |
| 2938 | `r-err` — step exception |
| 2974 | `r-err` — run-beats exception |
| 3020 | `r-err` — stop exception |
| 3038 | `r-err` — inject-event exception |

**Live consequence on `main`: every Observation error message and the
no-NPC warning render with no colour.** The launch-panel validation
failures — the surface's only feedback that a run refused to start — are
indistinguishable from ordinary body text.

**Why rule7 does not catch it.** `APPLIED(F)` iterates `frontend/src` files
only (PART A2). `cockpit/index.html` is never an applying file, so the
direction *legacy document applies a class living in `creation.css`* is
outside the scan domain entirely. rule7 is sound for what it covers and
blind here.

Grep confirms `.r-warn`/`.r-err` have **zero consumers under
`frontend/src`** [M]. After migration they are Observation-exclusive.

### C3 — Stale `WORLD_ID`: a run can be started against the wrong world [M]

Chain, fully anchored:

1. `index.html:697` — `let WORLD_ID = null;`
2. `index.html:1832` — `WORLD_ID = ctx.world_id;` inside `loadBootstrap()`.
   This is the **only** writer in the document [M — 3 total occurrences of
   the identifier].
3. `index.html:3194..3198` — `loadBootstrap()` runs once, on
   `DOMContentLoaded`.
4. `frontend/src/Header.svelte:25` — a world change calls
   `activateWorldCascade(id, refreshServerState)`.
5. `frontend/src/creation/tabs.js:703..718` — that cascade POSTs
   `/api/worlds/{id}/activate`, awaits `refreshServerState()`, then calls
   `handleWorldChanged()`. **It never reaches into the legacy document.**
6. `index.html:2896` — `observationStartRun` sends `world_id: WORLD_ID`.
7. `routes/observation.py:34..59` — `ObservationStartBody.world_id` is a
   required client field, passed straight to `_runner.start_run(...)`. The
   route does not re-derive the active world.

**Consequence.** After any Header world switch within a session, starting an
observation run writes `observation_run` rows — and the mutation proposals
that run produces — scoped to the world that was active at legacy boot.

Secondary: `obsInitialized` (`index.html:2843`, latched at `:2853`, read at
`:1813`) is a one-shot guard, so `observationLoadLocations()` never re-runs
either. The location dropdown and the `world_id` are consistently stale
together, which is why the failure is silent rather than a visible mismatch.

**[I] — not measured:** the same stale-global pattern plausibly affects Play
(`loadScene`, `loadPlayerKnowledge`, `startConversation`). This RECON did not
measure Play's paths. Do not carry that claim into a brief without measuring.

---

## PART D — Seams that move

| Seam | Anchor | Required change |
|---|---|---|
| `LEGACY_MOUNTS.observation` | `frontend/src/legacy/registry.js` (`showFn: 'showObservationView', retiredBy: 'TICKET-0060'`) | delete the entry; `play` alone remains |
| `legacy_mounts.baseline` | `tooling/verify/baselines/legacy_mounts.baseline` (`observation`, `play`) | **unchanged** — the baseline is a shrink ceiling, not a required set (`legacy_mount.py` rule 2) |
| `legacy_calls.baseline` | one record: `frontend/src/App.svelte::showFn::TICKET-0061` | **unchanged** — `showSurface` survives for `play` |
| reverse-bridge `observation:open-prompt` | dispatch `index.html:3131`; listener `App.svelte:56`; handler `App.svelte:44..49` | collapses — same document; Observation calls `navigate('creation','prompts')` then dispatches `creation:open-prompt` directly |
| `showObservationView` | `index.html:1808..1817` | deleted |
| `showPlayView` | `index.html:1795..1800` | must stop referencing `#observation-view` / `#mode-tab-observation` |
| `#observation-view` markup | `index.html:612..683` | deleted from the legacy document |
| legacy mode-tab buttons | `index.html:448..449` | the Observation button goes; Header.svelte already owns both (`Header.svelte:41`) |
| `legacy-slot` visibility | `App.svelte:64` — `currentSurface === 'creation' ? 'none' : 'flex'` | must become "visible only for `play`" |
| shell routes | `app.py:284`, `frontend/src/lib/router.js:10` | **unchanged** — `/observation` is already a shell route in both lists |
| `CLAUDE.md:18` | "Creation is partly Svelte islands mounted into the legacy document […] Play and the remaining Creation tabs stay legacy" | already stale on `main`; corrected by this ticket |
| `CLAUDE.md:414` | "legacy host for Play and Observation until TICKET-0060/0061" | narrows to Play |

**[I]** — the `App.svelte:64` condition and the `Header.svelte` tab wiring are
read from source but not exercised; the exact expression the brief should
prescribe is a drafting decision, not a measurement.

---

## PART E — What this ticket does NOT touch

Measured, not assumed:

- **Backend.** Nine routes, `routes/observation.py:48..123`, all consumed
  unchanged (B5). No canon-write path, no mutation gate, no schema.
- **The graph primitive.** No graph in the surface (B4).
- **The inline `<style>` block.** Zero occurrence of `obs` or `observation`
  in `index.html:12..431` [M]. 108 rule bodies, none Observation-specific.
- **`shared.css`.** All eleven of Observation's shared classes
  (`app-view`, `b-acted`, `b-other`, `badge`, `btn-icon`, `empty`,
  `panel-head`, `queue-body`, `queue-panel`, `spin`, `target-ref`) already
  live there and are consumed by Creation too.
- **Observation's 27 element ids.** All are behavioural hooks; none resolves
  to a rule in any of the three sheets [M].
- **`observation_window_parity.py`, `observation_socle.py`,
  `observation_runner.py`, `observation_metrics.py`.** Backend checks; none
  reads `index.html` [M — grep for the path across `checks/`].

---

## PART F — Verify-check impact

Sixteen checks reference `cockpit/index.html` [M]. Run on `main` in this
container:

| Check | Result | Note |
|---|---|---|
| `observation_surface` | **FAIL (real)** | finding C1 — re-homed by this ticket |
| `stylesheet_partition` | PASS | rule7 present; blind direction is finding C2 |
| `legacy_mount` | PASS | 2 mounts, 5 shell routes agreed |
| `page_contract` | PASS | 14/14 CREATION_TABS migrated |
| `creation_island` | PASS | 15 islands |
| `graph_primitive` | PASS | 0 live impls |
| `review_component` | PASS | |
| `modal_primitive` | PASS | 48 `.svelte` scanned |
| `relation_graph` | PASS | |
| `creation_return_nav` | PASS | |
| `event_tab` | PASS | |
| `faction_roster_panel` | PASS | |
| `review_root_fallback` | PASS | |
| `frontend_build_fresh` | PASS | 85 sources, manifest hash matches |
| `static_asset_freshness` | PASS | |
| `shell_height_chain` | PASS | 84 files, zero `100vh` |

**Environment caveat — read before trusting any absence above.** This RECON
ran in a stdlib-only container. `fastapi` and `sqlalchemy` are absent, so
`observation_socle`, `observation_runner`, `observation_metrics`,
`json_ui_boundary` and `schema_*` **could not be evaluated**. They are
recorded here as **UNKNOWN, not PASS**. `observation_surface`'s Rule 5
failure is a consequence of that same absence and must be re-measured on a
real dev environment before any brief asserts it.

This caveat is itself evidence for decision B1 below: a corpus-wide gate
without an explicit environment contract would report `ModuleNotFoundError`
as a check failure and become noise, or swallow it and become fail-open.

---

## PART G — Decisions locked (context for the ticket author; not actions)

Locked by the creator after this RECON was reported. Recorded here so the
brief author does not re-open them. **The RECON itself took no action on any
of these.**

| Code | Decision |
|---|---|
| **A1** | Brief -a repairs `observation_surface.py` **first**, anchored on today's tree — red-test proving it goes green on `main` as-is — before any migration. The migration brief then re-homes it onto the Svelte files. Two commits, two separate proofs. |
| **B1** | Add a corpus-wide gate (`verify/run.py --all` or equivalent) that executes every `tooling/verify/checks/*.py`, fail-closed, plus a ticket criterion asserting it green. Must carry an explicit environment contract (PART F) so a missing dependency is a hard failure, never a skip. |
| **C3** | Extend rule7's `APPLIED` domain to include `cockpit/index.html`, with `REACHABLE(legacy) = shared.css ∪ inline` only — excluding `creation.css` and the built bundle. **The extension carries a retirement condition: it is removed when it serves nothing.** That condition must be written in verifiable terms (see PART H, item 1). |
| **D1** | `.r-warn` / `.r-err` move into the Observation component's own scoped `<style>` and are **deleted** from `creation.css`. No global selector is added; rule7's `SCOPED(F)` term covers them; `creation.css` stays honestly Creation-only. |
| **E1** | Full Svelte templating. The four `innerHTML` string renderers (B6) become real templates. No `{@html}` — this is what makes D1 possible, since Svelte scoped styles do not reach `{@html}` content. |
| **F1** | The world-switch bug (C3 finding) is fixed **by** this migration: Observation reads `serverState.worldId` directly, keeps no local latch, and reloads locations plus run list on a `worldId` change. Explicit observable criterion in Done-means. |
| **F3** | Server-side hardening — `start_run` derives the active world and stops trusting `body.world_id` — is deferred to a **named ticket opened after TICKET-0061**, i.e. once the frontend refactor series is closed. It is a backend write and therefore an escalation under the frontend-only cross-cutting rule, not a silent edit inside 0060. |
| **G1** | Sequencing confirmed. The upstream `live-gate` statuses are file-state, not gate-state (PART A1); no gate blocks 0060. |

---

## PART H — Open items the brief author must settle

1. **C3's retirement condition must be stated verifiably.** "When it serves
   nothing" is qualitative. The measurable form available today: the
   extension is removable when `LEGACY_MOUNTS` no longer contains a key
   whose surface applies any class defined outside `shared.css` and the
   inline block. After TICKET-0061 that set is empty by construction. The
   brief must name the check that assumes this governance burden and state
   the condition in terms it can evaluate. *(Named-deferral discipline: a
   deferral without a verifiable reactivation condition is not a deferral.)*

2. **B1's environment contract is undesigned.** Whether the corpus gate
   requires a live DB, or partitions checks into "static" and
   "environment-bearing" tiers with the tier itself asserted, is an open
   design choice. PART F shows both failure modes are real.

3. **File cut for the Svelte surface is unchosen.** ≈ 428 lines across 18
   functions fits one module (B2), but the split between component template,
   a `.svelte.js` state module, and the run-detail sub-render follows the
   Creation precedent (`Creation.svelte` + `tabs.js` + per-panel
   `*.svelte.js`) and should be an explicit Scope IN decision rather than an
   executor judgement call.

4. **`observationOpenPrompt`'s new form.** `index.html:3130..3132` currently
   dispatches on the legacy document. Post-migration it is a same-document
   call to `navigate('creation','prompts')` plus a `creation:open-prompt`
   dispatch — but `Prompts.svelte:97` listens via a `legacyDoc` prop
   supplied by `mount.js`. Whether that prop still resolves to the shell
   document for this path is **[I], unmeasured**; the brief's mini-RECON
   must verify it before prescribing the call shape.

5. **Whether the two-view `showPlayView` needs its own contract check.**
   Once `observation_surface.py` is re-homed onto Svelte, nothing asserts
   that the legacy document's single remaining surface still shows itself.
   That is TICKET-0061 territory, but the boundary should be named rather
   than left to fall between the two tickets.

---

## PART I — RECON re-fetch discipline

Anchors above are `main`-as-of-this-session. Per the workstream map's
cross-cutting rule 5, the ticket conversation re-fetches the branch tarball
before authoring, and any brief anchoring on a `file:line` here restates it
in its own mini-RECON section rather than trusting this document.
