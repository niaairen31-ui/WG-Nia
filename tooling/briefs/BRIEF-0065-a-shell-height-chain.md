# BRIEF — Step "shell height chain"

TICKET-0065. Execute AFTER the E1 gate has been run and reported; do not start
if the reported outcome contradicts the prediction recorded in the ticket.

## Context

TICKET-0059 moved Creation out of the legacy iframe. `.app-view` and `.layout`
were written against a parent chain that ended at the legacy document's own
`body` (a full-height flex column); the shell inserts `#app` and `.shell-layout`
between them, and neither carries a height or a flex context. Creation's
`flex:1 / min-height:0` ladder therefore resolves against an auto-height
ancestor, so `.conv-list` never becomes scrollable and content below the fold is
unreachable under `html, body { overflow:hidden }`. Play and Observation are
unaffected only because `LegacyFrame.svelte` sizes its iframe off `100vh`
directly — a second, independent height authority.

This step restores one height authority for the whole shell.

## Scope IN

1. **`frontend/src/App.svelte`, the scoped `<style>` block (currently lines
   71-79).** Replace the `.shell-layout` rule and add an `#app` rule. Final
   content of the block, verbatim:

   ```css
   :global(html, body) {
     margin: 0;
     padding: 0;
   }
   /* TICKET-0065 (BRIEF-0065-a). The shell owns ONE height authority.
      shared.css:11 makes html/body full-height; these two rules carry that
      height down to the surfaces, so `.app-view`'s own `flex:1; min-height:0`
      (shared.css:41) resolves against a definite-height flex parent exactly
      as it did when it was a direct child of the legacy document's body.
      Before this, #app had no rule at all and .shell-layout set only a
      custom property, so every Creation flex ladder below resolved against
      an auto-height ancestor and .conv-list never became scrollable. */
   :global(#app) {
     flex: 1;
     min-height: 0;
     display: flex;
     flex-direction: column;
   }
   .shell-layout {
     --header-height: 56px;
     flex: 1;
     min-height: 0;
     display: flex;
     flex-direction: column;
   }
   ```

2. **`frontend/src/App.svelte`, the LegacyFrame wrapper (currently line 64).**
   The wrapper div must become a sized flex item, or the iframe has nothing to
   fill. Replace:

   ```svelte
   <div style:display={currentSurface === 'creation' ? 'none' : ''}>
   ```

   with:

   ```svelte
   <div class="legacy-slot" style:display={currentSurface === 'creation' ? 'none' : 'flex'}>
   ```

   and add to the same scoped `<style>` block:

   ```css
   .legacy-slot {
     flex: 1;
     min-height: 0;
     flex-direction: column;
   }
   ```

   Note the `'flex'` (not `''`) in the display expression: the element's
   non-hidden state must be an explicit flex context, and `''` would fall back
   to the class rule's absent `display`.

3. **`frontend/src/LegacyFrame.svelte`, the scoped `<style>` block (currently
   lines 24-33).** Retire the `calc(100vh - …)` height — the second authority.
   Final content, verbatim:

   ```css
   iframe {
     width: 100%;
     /* TICKET-0065 (BRIEF-0065-a): the iframe fills the slot the shell gives
        it instead of computing its own viewport height. --header-height is
        still read by Header.svelte's own `height` rule; this was its only
        other consumer, and it was the shell's second, independent height
        authority. shell_height_chain.py forbids a 100vh literal returning. */
     flex: 1;
     min-height: 0;
     border: 0;
     display: block;
   }
   ```

4. **`tooling/verify/checks/shell_height_chain.py`** — new fail-closed check,
   same idiom as `import_cycle.py` / `legacy_mount.py`: module-level `FAILURES`
   list, `fail()`, `_report_and_exit(counts)`, `ROOT` via `parents[3]`, stdlib
   only, no DB, no subprocess. Two rules, both vacuous-proof.

   - **rule1 — one height authority.** Scan every file under `frontend/src/`
     and `frontend/public/` and `frontend/index.html`. Zero occurrences of the
     literal `100vh`, in any context, comments included. Vacuous-proof: if the
     scan visits zero files, that is a FAILURE, not a pass.
   - **rule2 — the chain is declared.** `frontend/src/App.svelte` must contain
     a `:global(#app)` rule and a `.shell-layout` rule, and each must declare
     `display: flex`, `flex-direction: column` and `min-height: 0`. A missing
     `App.svelte`, a missing rule, or a rule missing any of the three
     declarations is a FAILURE.

   Report line on success, matching the corpus style:
   `PASS: shell_height_chain — N file(s) scanned, zero 100vh literal(s), shell chain declared on #app and .shell-layout`

5. **`npm --prefix frontend run build`**, and commit the regenerated
   `src/world_engine/cockpit/static/` output, so `frontend_build_fresh` stays
   green.

6. **`ARCHITECTURE_DECISIONS.md`** — append an entry: the shell owns exactly one
   height authority (`html/body` → `#app` → `.shell-layout` → surface), the
   iframe's `calc(100vh - …)` is retired, and `shell_height_chain.py` holds the
   invariant structurally rather than by convention.

## Scope OUT

- **The graph mount seam.** BRIEF-0065-b owns it entirely. Do not touch
  `frontend/src/graph/`, `frontend/src/legacy/bridge.js`, or
  `App.svelte:54`'s `initGraphMount(legacyDocument())` call in this step, even
  though line 54 sits three lines from an edit this brief does make.
- **Any CSS content change in `shared.css` or `creation.css`.** RECON proved the
  partition healthy and rule7 green; `.layout`, `.sidebar`, `.right-col`,
  `.panel-head`, `.conv-list` and `.btn-send` are all correctly placed and must
  not be moved, duplicated or re-tuned.
- **The unhashed-stylesheet cache asymmetry** (`app.py:91` `StaticFiles` with no
  `Cache-Control`, `shared.css`/`creation.css` unhashed while the bundle is
  content-hashed). Recorded in TICKET-0065 as deferred with a named
  reactivation condition. Do not add a query string, a `Cache-Control` header,
  or a hashed filename here.
- **Renaming the `legacyDoc` prop** (`creation/mount.js:91` and its ~15
  consumers). The name is now misleading — it resolves to the shell document —
  but the rename is a wide mechanical diff with no behavioural content and
  belongs to TICKET-0061's decommission pass.
- **The Observation surface.** Whether it has a mirror-image sizing loss is an
  open TICKET-0060 question; this step must not pre-empt it. Observation is
  legacy-mounted and inherits the iframe's sizing, which item 3 changes — verify
  it still fills the viewport (live gate) but change nothing inside it.
- **`.author-type-tabs` / `.author-new-row`** — known dead CSS in `creation.css`,
  carried over verbatim at TICKET-0059. Leave them.
- **`.signpost-group` (DiscDetailsEditor.svelte) and `.tick-controls`
  (QueueFilters.svelte)** — used with `class=` but defined in no stylesheet.
  REPORT ONLY: state whether either renders visibly unstyled. Do not add rules.

## Invariants to defend

- **"No structure without a reader."** `--header-height` keeps exactly one
  reader after item 3 (`Header.svelte`'s `header { height: var(--header-height) }`).
  If that reader is gone, the custom property must go with it — verify before
  assuming.
- **Frontend-only scope** (workstream map PART C rule 2). Nothing in this step
  touches canon-write paths, mutation gating, or the schema. If a sizing fix
  appears to need a backend change, that is an escalation, not a silent edit.
- **Fail-closed over advisory.** Item 4 is not optional documentation of the
  fix; without it the `100vh` literal can silently return at the next feature,
  which is exactly how the second height authority was born.
- **Vacuous-proof guards.** Both rules in item 4 must fail on an empty scan or a
  missing file. Zero parsed machine-checkable criteria is a failure, not a pass.

## Done means

- [ ] `WORLD_ENGINE_ENV=dev PYTHONPATH=src python3 tooling/verify/checks/shell_height_chain.py` returns PASS with a non-zero file count in its report line
- [ ] The same command returns FAIL when `100vh` is temporarily reintroduced into `LegacyFrame.svelte` (demonstrate once, revert)
- [ ] The same command returns FAIL when `min-height: 0` is temporarily removed from `.shell-layout` (demonstrate once, revert)
- [ ] `frontend_build_fresh`, `stylesheet_partition`, `legacy_mount`, `legacy_call`, `creation_island`, `page_contract` all return PASS
- [ ] `grep -rn "100vh" frontend/` returns nothing
- [ ] Live: Création > NPC renders a 300px left column with a visible right border, and the list scrolls independently while the sub-tab bar and shell band stay fixed
- [ ] Live: clicking an NPC opens its editable sheet in the right column
- [ ] Live: Play fills the viewport below the header, unchanged from before this step
- [ ] Live: Observation fills the viewport below the header, unchanged from before this step
- [ ] Live: Play -> Création -> Observation -> Création leaves no scroll or sizing artifact
- [ ] `/review-step` and `/close-step` run (engine code untouched, but the verify corpus is)
- [ ] Report on `.signpost-group` and `.tick-controls` delivered, no rules added

## Docs to update

- `ARCHITECTURE_DECISIONS.md` — the single-height-authority entry (item 6).
- No schema changelog entry: no schema change.
- `CLAUDE.md` — only if it names `LegacyFrame`'s viewport calc as doctrine.
  Verify; amend only if a line asserts it.
