# BRIEF — Step "legacy-mount registry + iframe bridge + fail-closed gate"

## MINI-RECON — run before executing this brief

Report-only. Confirm each assertion empirically; do NOT state any of them as
"presumably true". If any fails, STOP and escalate — this brief's anchors are
wrong and the fix is a re-authored brief, not an improvised adaptation.

```bash
git fetch origin && git checkout -b ticket/0056 origin/main
grep -n "app.mount(\"/static\"" src/world_engine/cockpit/app.py
grep -n "def serve_ui\|def serve_shell\|def serve_vendor_file" src/world_engine/cockpit/app.py
grep -n "^function showPlayView\|^function showCreationView\|^function showObservationView" src/world_engine/cockpit/index.html
ls frontend/src/
python tooling/verify/checks/frontend_build_fresh.py
```

Assertions that must hold:

1. `app.py` has the `/static` mount, `serve_ui` (`GET /`), `serve_shell`
   (`GET /shell`), `serve_vendor_file` (`GET /vendor/{filename}`), and NO
   route named `/legacy`.
2. `index.html` defines top-level `showPlayView`, `showCreationView`,
   `showObservationView` (expected around lines 3331 / 3340 / 3356 — the exact
   numbers may drift, the names may not).
3. `frontend/src/` contains exactly `main.js` and `Beachhead.svelte`.
4. `frontend_build_fresh.py` is GREEN before any edit.

## Context

TICKET-0055 landed the Svelte/Vite toolchain, the `/static` mount and a
beachhead island at `/shell`, and left exactly one named deferral: the
legacy-mount registry — "an enumerated, monotonically shrinking registry
policed by a fail-closed check, reaching exactly one entry (Play) at
TICKET-0061". This step builds it, together with the seam it governs: one
same-origin iframe hosting the whole legacy cockpit, and one bridge module
that is the only place in the frontend allowed to touch it. `index.html` is
not edited — not in this brief, not in this ticket.

## Scope IN

1. **`frontend/src/legacy/registry.js`** — the enumerated registry, the ONLY
   declaration of which legacy surfaces exist. Verbatim:

   ```js
   /* TICKET-0056 (A2). The legacy-mount registry: an enumerated,
      MONOTONICALLY SHRINKING list of surfaces still served by the legacy
      vanilla-JS document. One entry is removed by each surface-migration
      ticket; exactly one (play) survives at TICKET-0061, until Play's own
      rewrite on its own stack. Adding an entry is a fail-closed error --
      tooling/verify/checks/legacy_mount.py compares this set against
      tooling/verify/baselines/legacy_mounts.baseline and refuses any key
      that is not already there. */
   export const LEGACY_MOUNTS = Object.freeze({
     play:        Object.freeze({ showFn: 'showPlayView',        retiredBy: 'TICKET-0061' }),
     creation:    Object.freeze({ showFn: 'showCreationView',    retiredBy: 'TICKET-0059' }),
     observation: Object.freeze({ showFn: 'showObservationView', retiredBy: 'TICKET-0060' }),
   });

   export const LEGACY_SURFACES = Object.freeze(Object.keys(LEGACY_MOUNTS));
   ```

2. **`frontend/src/legacy/bridge.js`** — the sole module permitted to reach
   into the legacy document. No other file under `frontend/src/` may name
   `contentWindow` or `legacy-frame`; `legacy_mount.py` enforces this. Exports:
   `mountLegacy(frameEl)` (records the frame, resolves when it has loaded),
   `showSurface(key)` (looks `key` up in `LEGACY_MOUNTS`, calls the declared
   `showFn` on the legacy window; an unknown key is a thrown error, never a
   silent no-op), `whenLegacyReady(predicate, {timeoutMs})` (bounded polling
   helper; on timeout it THROWS and the caller surfaces a visible failure —
   never resolves-anyway). The module holds one module-level `frame` reference
   and one internal `legacyWindow()` accessor; `frame.src` is never assigned
   here.

3. **`frontend/src/LegacyFrame.svelte`** — renders the single iframe and
   nothing else. The `src` is a static attribute, written exactly once in the
   whole codebase:

   ```svelte
   <iframe id="legacy-frame" title="Cockpit (legacy)" src="/legacy"></iframe>
   ```

   Verbatim comment above it:

   ```
   <!-- TICKET-0056 (B1): ONE iframe, ONE src, assigned once and never
        reassigned. An iframe navigation pushes an entry onto the PARENT
        history stack -- reassigning src to switch surfaces would make the
        browser Back button replay legacy boots instead of shell routes.
        Surface switching goes through legacy/bridge.js by direct
        same-origin call. legacy_mount.py enforces the single-assignment
        rule. -->
   ```

   Styling: `width: 100%`, `border: 0`, `display: block`. Height is the
   parent's problem and is set in BRIEF-0056-b; here it is `height: 100vh`.

4. **`frontend/src/App.svelte`** — replaces the beachhead as the mounted root.
   It renders `<LegacyFrame />` and calls `mountLegacy` on mount. No header, no
   router yet (BRIEF-0056-b and -c). **Delete `frontend/src/Beachhead.svelte`**
   and point `frontend/src/main.js` at `App.svelte`.

5. **`app.py` — add `GET /legacy`**, a pure addition. `GET /` and `GET /shell`
   are untouched by this brief (the seam flip is BRIEF-0056-c). Verbatim
   docstring:

   ```python
   @app.get("/legacy", response_class=HTMLResponse)
   def serve_legacy() -> str:
       """The legacy single-file cockpit, served verbatim (TICKET-0056, B1).

       The shell hosts this document in ONE same-origin iframe; it also stays
       directly reachable as an escape hatch. `index.html` is byte-untouched
       by TICKET-0056 -- nine structural checks and `relation_graph.py`'s
       Lieux-graph byte-equality assertion against `main` depend on it.
       """
       return _INDEX_HTML.read_text(encoding="utf-8")
   ```

6. **`tooling/verify/baselines/legacy_mounts.baseline`** — the three keys, one
   per line, sorted: `creation`, `observation`, `play`. A trailing newline.

7. **`tooling/verify/checks/legacy_mount.py`** — new fail-closed G1 check,
   same idiom as `import_cycle.py` (module-level `FAILURES` list, `fail()`,
   `_report_and_exit()`, `ROOT = Path(__file__).resolve().parents[3]`), stdlib
   only, no DB, never imports application code. Six assertions, each
   vacuous-proof (a missing or empty input is a FAILURE, never a trivially
   satisfied comparison):

   1. **Registry parses, non-empty.** `frontend/src/legacy/registry.js` exists;
      the `LEGACY_MOUNTS` entries are extracted by regex over the object
      literal; zero entries found is a FAILURE.
   2. **Monotone shrink.** The baseline file exists and is non-empty; the
      current key set is a SUBSET of it. A key not in the baseline fails with
      the message `legacy mount 'X' is not in the baseline -- the registry may
      only SHRINK (TICKET-0056)`. A key removed from the registry passes.
   3. **Every entry declares a retiring ticket.** Each `retiredBy` matches
      `^TICKET-\d{4}$`. A missing or malformed field is a FAILURE.
   4. **Every `showFn` exists in the legacy document.** For each entry, a
      top-level `function <showFn>(` occurs in
      `src/world_engine/cockpit/index.html`. This is the link that makes a
      legacy rename a red gate instead of a runtime no-op.
   5. **Confinement.** Scanning every file under `frontend/src/`: the tokens
      `contentWindow` and `legacy-frame` occur ONLY in
      `frontend/src/legacy/bridge.js` and `frontend/src/LegacyFrame.svelte`
      (the frame element declares the id; the bridge resolves it). Any other
      file naming either token is a FAILURE. Scanning zero files is a FAILURE.
   6. **Single frame-src assignment.** Across `frontend/src/`, exactly one
      occurrence of `src="/legacy"`, and ZERO occurrences of the pattern
      `\.src\s*=` . Both counts are reported in the PASS line.

   PASS line shape:
   `PASS: legacy_mount — 3 mount(s) within baseline, 3 retiring ticket(s), 3 legacy fn(s) resolved, access confined to bridge, 1 frame src site`

8. **Rebuild and commit the build output**: `cd frontend && npm ci && npm run
   build`, then commit `src/world_engine/cockpit/static/`. `frontend/src/` has
   changed, so `frontend_build_fresh.py` is red until this is done.

## Scope OUT

- **The seam flip.** `GET /` keeps serving `index.html`; `GET /shell` keeps
  serving the built shell. BRIEF-0056-c flips them. Do not delete `serve_ui`
  or `serve_shell` here.
- **Any routing.** No `pushState`, no `popstate`, no URL parsing, no
  `_SHELL_ROUTES`. BRIEF-0056-c.
- **Any chrome.** No header, no world selector, no mode tabs, no hiding of the
  legacy header. BRIEF-0056-b.
- **Any state store.** No `/api/bootstrap` read, no world/player mirror.
  BRIEF-0056-b.
- **`showCreationTab` / sub-tab handling.** The bridge gets `showSurface` only.
  BRIEF-0056-c adds the sub-tab path with its readiness wait.
- **Editing `index.html` in any way**, including "just adding a message
  listener" — the bridge is same-origin and needs none. If something appears to
  require a legacy edit, that is an escalation, not a small edit.
- **Renaming `index.html`.** TICKET-0061.
- **Touching `vendor/`, the cytoscape file, or the graph code.** The graph
  primitive is TICKET-0057.
- **Any backend change beyond the single `GET /legacy` addition.** No
  canon-write, no mutation gating, no schema (frontend-only ticket).
- **Re-homing any existing check.** G1: none moves in this ticket.
- **A CLAUDE.md or ARCHITECTURE_DECISIONS edit.** BRIEF-0056-d.

## Invariants to defend

- **Structural over disciplinary.** The registry without `legacy_mount.py` is a
  comment. Both land in this brief, together; the check is not deferred to a
  later brief "once the shape settles".
- **No structure without a reader.** Every field declared in the registry is
  read by an assertion: `showFn` by assertion 4, `retiredBy` by assertion 3.
  Do not add a field this brief does not check.
- **Fail-closed over advisory.** Every assertion refuses rather than warns; an
  empty scan is a failure. `showSurface` on an unknown key throws;
  `whenLegacyReady` on timeout throws.
- **Frontend-only scope** (map PART C.2). One additive route is the whole
  backend surface of this brief.
- **`index.html` byte-untouched** — the nine index-anchored checks and
  `relation_graph.py`'s Lieux byte-equality against `main` must stay green
  without any re-homing.

## Done means

- [ ] `frontend/src/legacy/registry.js`, `frontend/src/legacy/bridge.js`,
      `frontend/src/LegacyFrame.svelte`, `frontend/src/App.svelte` exist;
      `frontend/src/Beachhead.svelte` no longer exists; `main.js` mounts `App`.
- [ ] `git diff origin/main -- src/world_engine/cockpit/index.html` is EMPTY.
- [ ] `git diff origin/main -- src/world_engine/cockpit/app.py` shows exactly
      one added route (`serve_legacy`) and no other change.
- [ ] `npm ci && npm run build` completes; `git status` is clean after the
      build output is committed.
- [ ] `python tooling/verify/checks/legacy_mount.py` prints the PASS line with
      the four counts.
- [ ] `python tooling/verify/checks/frontend_build_fresh.py` is green.
- [ ] `python tooling/verify/checks/page_contract.py`,
      `review_component.py`, `relation_graph.py`, `observation_surface.py`,
      `creation_return_nav.py` are all green (unchanged targets).
- [ ] **Red-tests, all four run and reported:**
      (a) adding a fourth key `foo` to `LEGACY_MOUNTS` -> `legacy_mount.py`
      red on assertion 2; reverted.
      (b) changing `play`'s `showFn` to `showPlayViewX` -> red on assertion 4;
      reverted.
      (c) adding `const w = frame.contentWindow;` to `App.svelte` -> red on
      assertion 5; reverted.
      (d) DELETING the `observation` key -> **GREEN** (monotone shrink is
      allowed); reverted. This one proves the check is not merely an equality.
- [ ] **Live:** `python scripts/cockpit.py` starts. `http://127.0.0.1:8000/`
      renders the legacy cockpit exactly as on `main`.
      `http://127.0.0.1:8000/legacy` renders the same thing.
      `http://127.0.0.1:8000/shell` renders the legacy cockpit INSIDE the
      shell's iframe — two headers visible (shell has none yet, legacy has its
      own), Play discussion loads, a Creation sub-tab opens, the NPC relation
      graph renders. Nothing is expected to be pretty at this step; it is
      expected to WORK.
- [ ] `/review-step` and `/close-step` run (engine code touched: `app.py`).

## Docs to update

None in this brief. No schema change (`schema_version_touched: none`).
`CLAUDE.md`, `ARCHITECTURE_DECISIONS.md`, `DECISIONS_INDEX.md`,
`docs/launch-procedure.md` are all BRIEF-0056-d's, deliberately batched so the
doctrine is written once against the finished shape rather than amended four
times.
