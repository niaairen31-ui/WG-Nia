# BRIEF — Step "the convergence lock: graph_primitive.py + shrinking baseline"

## Context

Two of three implementations have converged. Without a lock, that is a
refactor: the third can stay forever and a fourth can be born at the next
feature, exactly as `reviewGraphRender` was born beside `graphRender`. This
step makes a second graph engine constructible only by defeating a
fail-closed check.

It also discharges locked decision F. `relation_graph.py` clause 5
(`:192-206`) asserts the twelve Lieux functions are byte-identical to
`main` via `git show`. On a branch it bites; once merged, `main == HEAD`
and it passes trivially forever after. It is a transient branch freeze
wearing the costume of a permanent guard - fail-open by construction after
merge. It is not merely deleted here: it is REPLACED by a guard that holds.

The check's GONE rule is also the structural form of the creator's
zero-dormant-code constraint. `undefined_names.py` runs pyflakes over
`src/` and therefore covers Python only; there is no automated safety net
for a dangling JS reference. This rule is that net.

## Scope IN

1. **New `frontend/src/graph/registry.js`** - the enumerated,
   monotonically shrinking list of graph implementations NOT yet converged
   onto the primitive. Header comment verbatim:

   ```
   TICKET-0057 (C1). Every graph implementation that is NOT the primitive,
   enumerated. The list may only SHRINK: one entry is removed by the ticket
   that converges it, and an entry may never be added --
   tooling/verify/checks/graph_primitive.py compares this set against
   tooling/verify/baselines/graph_impls.baseline and refuses any key that
   is not already there. When the last entry goes, "un graph est un graph"
   stops being a claim and becomes a measured fact.

   Modelled on frontend/src/legacy/registry.js (TICKET-0056), which is the
   same shape solving the same problem one level up.
   ```

   ```js
   export const GRAPH_IMPLS = Object.freeze({
     relation_cytoscape: Object.freeze({
       engine: 'cytoscape',
       locus: 'src/world_engine/cockpit/index.html',
       fnPrefix: 'relGraph',
       retiredBy: 'TICKET-0058',
     }),
   });
   ```

2. **New `tooling/verify/baselines/graph_impls.baseline`**, one key per
   line, sole content:
   ```
   relation_cytoscape
   ```

3. **New `tooling/verify/checks/graph_primitive.py`.** Same idiom as
   `import_cycle.py` / `legacy_mount.py`: module-level `FAILURES` list,
   `fail()`, `_report_and_exit(counts)`, `ROOT` via `parents[3]`, stdlib
   only, no DB, no subprocess. Nine rules, each vacuous-proof - a missing
   file, an empty scan or a zero-length collection is a FAILURE, never a
   trivially satisfied comparison.

   - **Rule 1 - GONE (zero dormant code).** These 21 tokens are absent from
     `index.html` as raw substrings, in any context including comments:
     `graphAutoPlace`, `graphRender`, `graphNodeMD`, `_graphMouseMove`,
     `_graphMouseUp`, `_graphMoveSVGNode`, `graphNodeClick`,
     `graphEdgeClick`, `graphCanvasClick`, `graphCreateEdge`,
     `graphPersistPos`, `graphLoad`, `reviewGraphRender`, `GRAPH_W`,
     `GRAPH_H`, `NODE_R`, `DRAG_THRESHOLD`, `graphData`,
     `graphSelectedNodeId`, `_graphDrag`, `_graphPlaced`.
     Comment in the check, verbatim: `A converged implementation left`
     `behind "just in case" is the exact failure this ticket exists to`
     `prevent -- reviewGraphRender was born beside graphRender that way.`
     `Raw-substring, any context: a commented-out body is dormant code.`
     Note that `graphData` is a substring of nothing else in the file and
     `NODE_R` must be matched on a word boundary to avoid colliding with a
     future `NODE_RADIUS`; use `\b` anchors for the four SCREAMING_CASE
     tokens and plain substring for the rest.
   - **Rule 2 - no `<svg` in `index.html`.** After -b and -c, the legacy
     document emits no SVG graph at all. Zero occurrences of `<svg`.
   - **Rule 3 - registry parses, non-empty, monotone shrink** against
     `graph_impls.baseline`. Any key not in the baseline is a failure.
     A missing or empty baseline is a failure.
   - **Rule 4 - every entry declares a well-formed `retiredBy`** matching
     `^TICKET-\d{4}$`, plus non-empty `engine`, `locus` and `fnPrefix`.
   - **Rule 5 - every entry still describes something real.** For each
     entry, its `locus` file exists and contains at least one
     `function <fnPrefix>\w+(` declaration. An entry that describes nothing
     is a failure, so the registry is forced to shrink when its code goes
     rather than rot into a stale list. This is the rule that makes rule 3
     honest.
   - **Rule 6 - engine confinement.** No `cytoscape(` call and no `<svg`
     emission anywhere under `frontend/src/` outside `frontend/src/graph/`.
     Inside `index.html`, every `cytoscape(` occurrence falls within a
     brace-balanced `function <fnPrefix>\w+` body of a registered entry -
     reuse `review_component.py`'s `_braced_function` helper shape
     (`:56-70`).
   - **Rule 7 - the primitive never fetches and never writes.**
     `Graph.svelte` contains no `fetch(`, no `XMLHttpRequest`, and no
     `method:` followed by `'POST'`, `'PUT'` or `'DELETE'`.
   - **Rule 8 - the primitive carries no scoped CSS.** `Graph.svelte`
     contains no `<style` block. Comment verbatim:
     `The component renders inside the legacy iframe document; Svelte`
     `injects scoped CSS into the SHELL's head, where it never reaches the`
     `frame. A <style> block here is CSS that silently does nothing.`
   - **Rule 9 - closed contract vocabulary.** Collect every
     `graph: { ... }` object literal in `index.html` (the slot spec and the
     review descriptors). Every key set is one of
     `consumer`, `mountId`, `extraEdges`. Any other key is a failure.
     Zero specs collected is a failure - the rule must not pass by finding
     nothing.

   PASS message reports the counts: tokens asserted gone, registry entries
   within baseline, entries with a live locus, graph specs validated.

4. **`relation_graph.py` - discharge F.** In
   `tooling/verify/checks/relation_graph.py`:
   - Delete clause 5 (`:192-206`), the `LIEUX_GRAPH_FUNCTIONS` constant
     (`:49-53`) and the `_git_show` helper (`:73-82`), plus the now-unused
     `subprocess` import.
   - Amend the module docstring: replace item 5 with, verbatim:
     ```
     5. (Retired, TICKET-0057.) This check used to assert the Lieux graph
        component was byte-identical to `main` via `git show`. That guard
        was fail-open by construction: on a branch it bit, but once merged
        `main == HEAD` and it passed trivially forever after -- a transient
        branch freeze wearing the costume of a permanent guard. The Lieux
        graph has since converged onto the graph primitive and no longer
        exists in index.html at all; the permanent guarantee now lives in
        `tooling/verify/checks/graph_primitive.py`, which forbids any graph
        implementation outside the registered set.
     ```
   - Clauses 1-4 are UNCHANGED and must still pass: the vendored cytoscape
     file and its GET route, both relation-graph endpoints registered and
     write-free with the structural `connects_to`/`controls` exclusion, and
     write fetches confined to `relGraphSaveEdgePanel`/`relGraphDeleteEdge`.
   - Amend the PASS message to drop the "Lieux graph component untouched"
     clause.

5. **Register the check** wherever the verify runner enumerates checks, in
   the same manner as the existing entries. Confirm by running the full
   verify suite, not by reading the runner.

## Scope OUT

- **Converging the relation / cytoscape graph.** TICKET-0058. This step
  REGISTERS it; it does not touch `relGraph*`, `index.html:1613`, the
  vendored file, or `vite.config.js:14`.
- **Deleting `relation_graph.py` entirely.** Its clauses 1-4 protect
  guarantees this ticket does not supersede - the endpoints' read-only
  status and the structural relation-type exclusion are not graph-rendering
  concerns.
- **A rule about force layout, node counts, performance, or accessibility.**
- **Making rule 9's vocabulary open or configurable.** It is closed on
  purpose; a new key means a new decision.
- **Extending the check to `frontend/src/legacy/` or the pipeline cockpit.**
- **Baselining anything else.** `graph_impls.baseline` has exactly one line
  and must not become a general-purpose exemption file.
- **Touching `page_contract.py`, `review_component.py` or
  `legacy_mount.py`.** Their amendments belong to -b and -c and are already
  landed; if one is red here, that is a defect in the earlier step, to be
  fixed there, not patched here.
- **Doctrine and changelog text.** Brief -e.

## Invariants to defend

- **Structural over disciplinary.** After this step, a second graph engine
  is not "discouraged" - it is a red gate. If a rule as written can be
  satisfied by a graph that should be refused, the rule is wrong.
- **Fail-closed over advisory.** Every rule refuses. None warns.
- **Vacuous-proof.** A rule that scans an empty set, reads a missing file,
  or collects zero items FAILS. Rule 9 in particular must fail on zero
  specs found: a check that passes because it found nothing is the exact
  shape of the flaw F is fixing.
- **A check may not be weakened to go green.** If rule 6's confinement
  fires on something legitimate, that is an ESCALATION to Nia with the
  finding, never a quiet exception list.
- **Module budget and function length** (R1 80 lines, R5 1000 lines /
  40 functions). Nine rules in one file: keep each rule its own small
  function, as `legacy_mount.py` does.

## Done means

- [ ] `frontend/src/graph/registry.js` and
      `tooling/verify/baselines/graph_impls.baseline` exist, the baseline
      containing exactly `relation_cytoscape`.
- [ ] `python tooling/verify/checks/graph_primitive.py` -> PASS, and the
      PASS line reports non-zero counts for tokens asserted gone, registry
      entries, live loci and graph specs validated.
- [ ] Red-test 1: temporarily re-add `function graphRender() {}` to
      `index.html` -> the check FAILS on rule 1. Revert.
- [ ] Red-test 2: temporarily add a second key to `GRAPH_IMPLS` -> FAILS on
      rule 3 (not in baseline). Revert.
- [ ] Red-test 3: temporarily change `relation_cytoscape.fnPrefix` to a
      prefix that matches nothing -> FAILS on rule 5. Revert.
- [ ] Red-test 4: temporarily add `<style>` to `Graph.svelte` -> FAILS on
      rule 8. Revert.
- [ ] Red-test 5: temporarily add `graph: { consumer: 'lieux', bogus: 1 }`
      -> FAILS on rule 9. Revert.
- [ ] Red-test 6: temporarily rename every `graph: {` spec -> FAILS on
      rule 9's zero-collected guard, NOT a pass. Revert.
- [ ] `grep -c 'LIEUX_GRAPH_FUNCTIONS\|_git_show\|subprocess' tooling/verify/checks/relation_graph.py`
      returns `0`.
- [ ] `python tooling/verify/checks/relation_graph.py` -> PASS.
- [ ] Full verify suite green, and `graph_primitive.py` appears in its
      output (proving it is registered, not merely present on disk).
- [ ] Live: the NPC relation graph still works end to end - ego mode,
      global mode, bucket toggles, edge panel save and delete.
- [ ] Live: the Lieux graph and both review previews still work (nothing in
      this step should have changed behaviour at all).
- [ ] `/review-step` and `/close-step` run.

## Docs to update

None in this step - brief -e. Note for -e: this step creates a new
`tooling/verify/baselines/` entry and a new check; CLAUDE.md's check
inventory and ARCHITECTURE_DECISIONS must both record them, and F's finding
(the fail-open clause 5) must be written down rather than silently fixed.
