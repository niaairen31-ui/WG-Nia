# BRIEF — Step "graph mount, single document"

TICKET-0065. Executes AFTER BRIEF-0065-a has merged, so the graph surfaces are
live-testable inside a correctly sized Creation layout.

## Context

`creation/mount.js` was migrated off the legacy document at BRIEF-0059-l
(`frontend/src/creation/mount.js:11-15`), and `:23` explicitly excluded
`graph/mount.js` as "a distinct, already-established mechanism". That exclusion
was true while Creation lived in the iframe and became false in the same merge
train. The result: every `graph:slot` / `graph:invalidate` dispatch now fires on
the shell document while both listeners sit on the legacy document
(`App.svelte:54`, `graph/mount.js:246,253`), so no graph mounts at all — and if
one did, `legacyContainer(id)` would throw, because all four mount targets are
`Creation.svelte`'s own children. Four surfaces are dead: the NPC relation
graph, the Lieux graph, and the Region and RoomBatch pre-commit previews. The
whole verify corpus is green throughout.

This step moves the seam fully onto the shell — the same migration
`creation/mount.js` already made — and lands the check that makes the two
documents impossible to desynchronise again.

## Mini-RECON — verify before writing

Report `file:line` for each, and STOP and escalate if any does not hold:

1. `frontend/src/graph/mount.js` — confirm `legacyContainer` is imported once
   and called at exactly two sites, and that no third site exists.
2. `frontend/src/legacy/bridge.js` — confirm `legacyContainer` has no importer
   outside `graph/mount.js` after step 1 (comments mentioning it do not count).
3. `frontend/src/App.svelte` — confirm `legacyDocument()` retains at least one
   other caller besides `initGraphMount` (expected: `initCreationMount` and the
   `observation:open-prompt` listener). If not, `legacyDocument` itself loses
   its last reader and that is an escalation, not a silent deletion.
4. Enumerate every `graph: { ... }` spec's `mountId`/`containerId` and every
   `slots[].containerId` carrying a `graph` key, and confirm each id exists as
   an element in `Creation.svelte`, `Region.svelte` or `RoomBatch.svelte` —
   i.e. in the shell document. Report the full list; rule 11 ranges over it.
5. `tooling/verify/checks/graph_primitive.py` — confirm the rule numbering
   currently ends at 10 and report the exact `_report_and_exit` counts dict
   keys, so rule 11 extends rather than reshapes it.

## Scope IN

1. **`frontend/src/graph/mount.js` — container resolution.** Remove the
   `legacyContainer` import (line 31) and replace both call sites (lines 122
   and 193) with `document.getElementById(containerId)`. A null result must
   throw with the same shape the bridge used, so a missing container stays a
   loud failure rather than a silent no-op. Use exactly:

   ```js
   const node = document.getElementById(containerId);
   if (!node) {
     throw new Error(`graph/mount: no element #${containerId} in the shell document`);
   }
   ```

2. **`frontend/src/graph/mount.js` — listener registration.**
   `initGraphMount(legacyDoc)` loses its parameter and registers both listeners
   on `document`. Replace the function's signature and both
   `legacyDoc.addEventListener` calls with `document.addEventListener`, and
   replace the header comment above it (currently lines 242-244) verbatim with:

   ```js
   /* TICKET-0065 (BRIEF-0065-b). One document, one bus. Creation stopped
      living in the legacy iframe at TICKET-0059, which moved every graph
      mount target into the shell document and every dispatcher onto it --
      but this listener stayed on the legacy document, so no graph mounted
      at all. There is no cross-document signal left here: dispatchers and
      listeners are both `document`, and graph_primitive.py rule 11 holds
      that identity structurally. */
   ```

3. **`frontend/src/App.svelte:54`** — `initGraphMount(legacyDocument())`
   becomes `initGraphMount()`. Leave lines 55-56 untouched:
   `initCreationMount(legacyDocument())` and the `observation:open-prompt`
   listener are genuine cross-document signals and stay.

4. **`frontend/src/legacy/bridge.js`** — delete the `legacyContainer` export
   (currently lines 55-67, including its TICKET-0057 header comment, whose
   stated premise "Creation is a legacy mount until TICKET-0059" is now
   self-refuting). No structure without a reader. `legacyDocument`,
   `legacyCall`, `showSurface`, `hideLegacyHeader` and `mountLegacy` all stay.

5. **`tooling/verify/checks/graph_primitive.py` — new rule 11, single
   document.** Extend the existing check; do not create a new file. Three
   assertions, all vacuous-proof:

   - **11a.** Zero occurrences of `legacyContainer` anywhere under
     `frontend/src/graph/`, any context, comments included.
   - **11b.** Every mount target enumerated in mini-RECON item 4 resolves to an
     element id present in the shell-side component set
     (`frontend/src/creation/` and `frontend/src/graph/`). An id declared in a
     `graph:` spec with no matching element is a FAILURE. Collecting zero mount
     targets is a FAILURE — the rule must not pass by finding nothing.
   - **11c.** Every `dispatchEvent(new CustomEvent('graph:slot'` and
     `'graph:invalidate'` site under `frontend/src/` dispatches on a receiver
     that is either the bare `document` or a `legacyDoc` binding proven to be
     `node.ownerDocument` from `creation/mount.js:91`; and
     `graph/mount.js`'s `addEventListener` sites register on the bare
     `document`. Any dispatcher registering against `legacyDocument()` or a
     `contentWindow` document is a FAILURE. Collecting zero dispatch sites is a
     FAILURE.

   Extend the module docstring's numbered rule list with rule 11 in the same
   voice as rules 1-10, and extend the `_report_and_exit` counts dict so the
   PASS line reports the mount-target and dispatch-site counts.

6. **`tooling/verify/checks/graph_primitive.py` — rule 8 rationale.** Rule 8
   (no scoped `<style>` in `Graph.svelte`) keeps its assertion but its stated
   rationale becomes factually false once the graph mounts in the shell:
   Svelte's scoped CSS now DOES reach it. Replace the rule-8 paragraph in the
   docstring, and the `fail()` message at the rule-8 site, so the reason given
   is single-stylesheet authority — all graph CSS lives in `creation.css` under
   `stylesheet_partition`'s rule7 coverage — not an unreachable-injection
   physics claim. Do not weaken or remove the rule.

7. **`npm --prefix frontend run build`**, and commit the regenerated
   `src/world_engine/cockpit/static/` output.

8. **`ARCHITECTURE_DECISIONS.md`** — append an entry: the graph mount seam is
   single-document (shell) as of TICKET-0065; `legacyContainer` is retired;
   rule 11 holds the dispatcher/listener identity structurally. Record the
   generalised lesson explicitly: **a named exclusion must state the check that
   assumes its governance burden, and an exclusion justified by a state of the
   world is invalid the moment a later commit changes that state.**

## Scope OUT

- **Renaming the `legacyDoc` prop** (`creation/mount.js:91` and its consumers in
  `Region.svelte`, `RoomBatch.svelte`, `Sheet.svelte`, `linkAgent.svelte.js`,
  `EntityList.svelte`, `NpcAgent.svelte`, `LinkAgent.svelte`, `Prompts.svelte`
  and others). The name is misleading — it already resolves to the shell
  document — but the rename is a wide mechanical diff with no behavioural
  content. TICKET-0061.
- **Deleting `legacyDocument`, `legacyCall`, or the bridge module itself.**
  Only `legacyContainer` retires here (item 4); the rest have live readers and
  belong to TICKET-0061's decommission.
- **Adding scoped `<style>` to `Graph.svelte`** now that it would work. Rule 8
  stands; item 6 only corrects why.
- **Touching `frontend/src/graph/Graph.svelte` or any consumer under
  `frontend/src/graph/consumers/`.** The renderer and the consumers are
  correct; only the seam between them and the DOM is wrong.
- **`.graph-mount-target` / `.graph-side-panel`** (`graph/mount.js:152,154`).
  These are `querySelector` hooks carrying their own inline styles, not a CSS
  coverage hole. Leave both the classes and the inline styles exactly as they
  are.
- **TICKET-0060 territory.** Whether Observation renders a graph, and whether it
  should become a primitive consumer, is 0060's first open decision. This step
  must not add an Observation mount target or pre-answer it.
- **The `graph_impls.baseline` / `graph_impls.retired` files.** No
  implementation converges or retires here; both are untouched, and rule 3's
  shrink-only property must not be exercised.
- **The unhashed-stylesheet cache asymmetry.** Deferred at ticket level.

## Invariants to defend

- **"No structure without a reader."** Item 4 is not cleanup; leaving
  `legacyContainer` exported with zero callers is the dormant-code failure rule
  1 of this same check exists to prevent.
- **Fail-closed over advisory.** Rule 11 must be able to fail. Demonstrate each
  of 11a/11b/11c failing once against a deliberate temporary break, then revert.
- **Vacuous-proof guards.** 11b and 11c must FAIL on a zero-length collection.
  A rule that passes by finding nothing is the exact gap that let this
  regression ship under a green corpus.
- **Single canon-write authority / frontend-only scope.** Nothing here touches
  `_apply_mutation`, mutation gating, or the schema. The graph primitive never
  fetches and never writes (rule 7) — that must remain true.
- **Prescription vs verification.** The mini-RECON above is the only source of
  tree-specific line numbers for this step. If a line number in this brief does
  not match the working tree, do not adapt silently — report the discrepancy
  and stop.

## Done means

- [ ] `WORLD_ENGINE_ENV=dev PYTHONPATH=src python3 tooling/verify/checks/graph_primitive.py` returns PASS, and its report line includes non-zero mount-target and dispatch-site counts
- [ ] The same command returns FAIL when `legacyContainer` is temporarily reintroduced under `frontend/src/graph/` (demonstrate, revert)
- [ ] The same command returns FAIL when a `graph:` spec's `mountId` is temporarily pointed at a non-existent id (demonstrate, revert)
- [ ] The same command returns FAIL when `initGraphMount` is temporarily switched back to a `legacyDocument()` receiver (demonstrate, revert)
- [ ] `grep -rn "legacyContainer" frontend/src/` returns nothing
- [ ] `legacy_mount`, `legacy_call`, `relation_graph`, `creation_island`, `page_contract`, `review_component`, `stylesheet_partition`, `frontend_build_fresh` all return PASS
- [ ] Live: Création > NPC > "Voir le graphe" mounts the relation graph; ego/global toggle, strength buckets, edge panel save and delete all work
- [ ] Live: Création > Lieux graph slot mounts; drag-to-place still persists node positions across a tab leave/re-enter
- [ ] Live: Création > Région, after generating a draft, "Voir le graphe des lieux" mounts the pre-commit preview
- [ ] Live: Création > Lieux > "Générer un lot ici", after drafting, "Voir le graphe" mounts the batch pre-commit preview
- [ ] Live: browser console shows zero `legacy/bridge: no element #...` and zero `graph/mount:` errors across all four surfaces
- [ ] Live: a world switch while a graph is open remounts it from `consumer.defaultMeta` rather than erroring
- [ ] `/review-step` and `/close-step` run

## Docs to update

- `ARCHITECTURE_DECISIONS.md` — the single-document seam entry plus the
  exclusion-governance lesson (item 8).
- `graph_primitive.py` module docstring — rule 11 added, rule 8 rationale
  corrected (items 5 and 6). This step IS that doc update.
- `CLAUDE.md` — verify whether any line asserts that graph islands render inside
  the legacy iframe. Amend only if such a line exists; report either way.
- No schema changelog entry: no schema change.
