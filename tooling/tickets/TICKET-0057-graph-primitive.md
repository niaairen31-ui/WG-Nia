---
id: TICKET-0057
title: Governed graph primitive - contract, SVG convergence, fail-closed lock
type: feature
status: exec
created: 2026-07-30
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
brief_ids: [BRIEF-0057-a, BRIEF-0057-b, BRIEF-0057-c, BRIEF-0057-d, BRIEF-0057-e]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"Un graph devrait etre un graph." Third ticket of the index-split chain
(0055 -> 0061). Define the graph primitive: one component, a declared
contract separating legitimate parametrization from accidental divergence,
proven on real consumers, then locked fail-closed so a second graph engine
cannot reappear at the next feature.

Locked in the design conversation: `A1, B3, C1, D2, E1`, plus:
- "je ne veux pas de code qui dors a la fin de l'implantation"
- F explicit (the `relation_graph.py` clause-5 fail-open is fixed here)
- G: `graphAutoPlace` enters the primitive.

## Clarifications resolved (intake)

**A1 - the pilot renders as an in-frame island.** The shell mounts the
Svelte component into the legacy iframe's document through an export of
`frontend/src/legacy/bridge.js`. Rejected: reordering after TICKET-0058
(defeats the locked strategy of proving the primitive BEFORE broad
migration, and inflates 0058); lock-without-pilot (freezes a contract
nothing validated); vanilla convergence in place (writes code that
TICKET-0059 throws away).

Forced by RECON: a shell-side graph pane is not constructible. All four
graph surfaces live inside Creation, and TICKET-0056 deferred continuous
route sync to TICKET-0058 - the shell cannot know which sub-tab is active.

**B3 - the pilot is the two SVG implementations, giving three consumers.**
The canonical Lieux graph (`index.html:10464..10639`) and the review
pre-commit preview (`index.html:6231..6273`, consumed by region AND room
batch). Rationale: a primitive with one consumer proves nothing - the
second consumer is what tests whether the axes are right, and the review
preview supplies two for free. These two are also the REAL measured
duplication: they already share `graphAutoPlace` and diverge only in SVG
emission. And they carry no cytoscape dependency and no scoped-CSS problem
(both are attribute-styled).

Accepted cost, recorded: B3 never exercises a force layout, so the contract
is frozen without it. That is precisely why E1 applies.

**C1 - the lock lands inside this ticket, with a shrinking baseline.**
`tooling/verify/checks/graph_primitive.py` plus
`tooling/verify/baselines/graph_impls.baseline`, one entry per
not-yet-converged implementation carrying a `retiredBy`, monotone shrink,
fail-closed, vacuous-proof. Exact decalque of `legacy_mount.py`'s registry
idiom (TICKET-0056). The guarantee is measurable during the transition
instead of promised for later.

**Zero dormant code (creator constraint, structural not disciplinary).**
At close, no converged implementation survives anywhere in `index.html` -
not behind a flag, not unreferenced, not commented out. Enforced by the
lock's GONE rule, which asserts the absence of 13 function names, 4
constants and 4 globals as raw substrings. RECON confirms this is
attainable: every use of `GRAPH_W`, `GRAPH_H`, `NODE_R`, `DRAG_THRESHOLD`,
`graphData`, `graphSelectedNodeId`, `_graphDrag`, `_graphPlaced` sits
inside the 13 functions being deleted.

Note on why this rule matters more than usual: `undefined_names.py` runs
pyflakes over `src/` and covers Python only. There is NO automated
safety net for a dangling JS reference in `index.html`. The GONE rule is
that net.

**D2 - the declaration seam is the existing slot descriptor, not
`traits.py`.** `CREATION_TABS` slots already carry a declarative descriptor
(`index.html:4287`, `4313`) asserted by `page_contract.py:169-184`, and the
review descriptor already carries `graphSvgId`/`graphOpen`/`graphExtraEdges`
(`index.html:6135-6141`). Both have live readers. `traits.py:200-209`
(`ext_columns_for`/`form_fields_for`) has none: no entity type declares a
graph today, so `graph_spec_for(entity_type)` would be structure without a
reader (E2). Named deferral, logged in ARCHITECTURE_DECISIONS.

**E1 - the axis vocabulary is evidence-derived, minimal.** Only what the
three pilot consumers actually exercise. An axis nobody sets is a lie in
the contract and is how a leaky union type is born. The vocabulary grows
with its readers - `force` arrives with cytoscape at TICKET-0058.

RECON collapsed one candidate axis outright: `graphAutoPlace` already
handles BOTH stored coordinates and null-coordinate fallback in one
function (`index.html:10464-10477`). Lieux nodes carry `coord_x`; review
draft nodes never do. So `placement` is not an axis - it is one strategy
whose behaviour is data-driven. This is a direct consequence of G.

**F - explicit.** `relation_graph.py`'s clause 5 asserts the twelve Lieux
functions are byte-identical to `main` via `git show`. On a branch it
bites; once merged, `main == HEAD` and it passes trivially. It is a
transient branch freeze wearing the costume of a permanent guard -
fail-open by construction after merge. This ticket does not merely delete
it: it REPLACES it with the primitive lock, which holds permanently, and
records the finding.

**G - `graphAutoPlace` enters the primitive** as its single placement
strategy, not a neighbouring utility. It is already shared by two of the
three consumers; leaving it outside would keep half the convergence
unfinished.

**Danger class note.** Empty, but not vacuous: the Lieux consumer triggers
canon writes (create `connects_to`, delete relation, persist coordinates).
Every one goes through a pre-existing sanctioned endpoint, unchanged. The
primitive itself performs no fetch and no write - that is an invariant of
the contract, and rule 7 of the lock.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] The 13 converged names (`graphAutoPlace`, `graphRender`,
      `graphNodeMD`, `_graphMouseMove`, `_graphMouseUp`, `_graphMoveSVGNode`,
      `graphNodeClick`, `graphEdgeClick`, `graphCanvasClick`,
      `graphCreateEdge`, `graphPersistPos`, `graphLoad`, `reviewGraphRender`)
      are absent from `index.html` as raw substrings, any context
      -> verify/checks/graph_primitive.py
- [ ] The 4 constants (`GRAPH_W`, `GRAPH_H`, `NODE_R`, `DRAG_THRESHOLD`) and
      4 globals (`graphData`, `graphSelectedNodeId`, `_graphDrag`,
      `_graphPlaced`) are absent from `index.html`
      -> verify/checks/graph_primitive.py
- [ ] `frontend/src/graph/registry.js` parses non-empty, shrinks monotonically
      against `tooling/verify/baselines/graph_impls.baseline`, every entry
      declares `retiredBy` matching `^TICKET-\d{4}$`, and every entry's
      declared locus still physically contains its implementation
      -> verify/checks/graph_primitive.py
- [ ] No `cytoscape(` construction and no graph `<svg>` emission anywhere
      under `frontend/src/` outside `frontend/src/graph/`; inside
      `index.html`, `cytoscape(` occurs only within a baselined entry's
      functions -> verify/checks/graph_primitive.py
- [ ] Every `graph: { ... }` spec in `index.html` sets only keys from the
      declared contract -> verify/checks/graph_primitive.py
- [ ] `Graph.svelte` contains no `fetch(`, no `method: 'POST'|'PUT'|'DELETE'`,
      and no `<style>` block -> verify/checks/graph_primitive.py
- [ ] `graph_primitive.py` is vacuous-proof: missing file, empty scan, or
      zero rules evaluated is a FAILURE -> self-asserting
- [ ] `relation_graph.py` no longer contains `LIEUX_GRAPH_FUNCTIONS` or a
      `git show` call; its remaining clauses (vendor route, ego + global
      endpoints read-only with structural `connects_to`/`controls`
      exclusion, write fetches confined to the two sanctioned edge-panel
      writers) still pass -> verify/checks/relation_graph.py
- [ ] `review_component.py` passes with `reviewGraphRender` retired from
      GENERICS and asserted absent -> verify/checks/review_component.py
- [ ] `page_contract.py` still asserts the Lieux slot declares
      `display: 'on_demand'` -> verify/checks/page_contract.py
- [ ] `legacy_mount.py` unchanged and green: `contentWindow` /
      `legacy-frame` tokens still confined to `bridge.js` /
      `LegacyFrame.svelte` -> verify/checks/legacy_mount.py
- [ ] `frontend_build_fresh.py` green on a fresh `npm run build`
      -> verify/checks/frontend_build_fresh.py
- [ ] `decisions_index.py` green after the new ARCHITECTURE_DECISIONS
      section header -> verify/checks/decisions_index.py
- [ ] Full-tree verify green (module budget, function length, import cycle,
      no-print, json_ui_boundary included)

### Live  ->  human gate (Nia)

- [ ] Creation > Lieux > "Voir le graphe": the map renders, nodes sit at
      their stored positions, null-coordinate nodes on the deterministic
      circle.
- [ ] Drag a node inside the frame: it moves, the incident edges follow,
      the position persists across a reload.
- [ ] Click a node then a second: a `connects_to` link is created; the
      duplicate refusal still holds (clicking an already-linked pair does
      nothing).
- [ ] Click an edge: confirmation prompt, then the link is deleted and the
      graph refreshes.
- [ ] Click empty canvas with a node selected: the selection clears.
- [ ] Save a location from the author sheet while the Lieux tab is active:
      the graph refreshes on its own.
- [ ] Commit a region, then a room batch: the Lieux graph refreshes in both
      cases.
- [ ] Creation > Region generation > "Voir le graphe des lieux": the
      pre-commit preview renders, hierarchy edges solid, confirmed
      connection edges dashed; toggling accept/reject on a node updates the
      preview; the toggle button label flips.
- [ ] Room batch panel > "Voir le graphe": same, against the synthetic
      anchor.
- [ ] Browser Back / Forward across surfaces still routes through the shell,
      no legacy re-boot.
- [ ] NPC relation graph (cytoscape) still works, untouched, ego and global
      modes, buckets, edge panel save/delete.
