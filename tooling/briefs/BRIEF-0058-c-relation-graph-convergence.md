# BRIEF — Step "relation graph converges; cytoscape leaves"

Ticket: TICKET-0058. Relies on RECON-0058-a M1, M2, M3, M8. Requires
BRIEF-0058-b landed.

## Context

`frontend/src/graph/registry.js:16` declares
`relation_cytoscape: { retiredBy: 'TICKET-0058' }`. This is the step that
honours it. Bloc C2 is locked: the force layout is implemented on the
primitive's existing SVG renderer and the 435 KB vendored engine
(`src/world_engine/cockpit/vendor/cytoscape-3.34.0.min.js`) leaves the tree.
Two engines behind one API would have preserved the divergence the lock
exists to end.

TICKET-0057 recorded that its contract was frozen without ever exercising a
force layout, and named this step as where `force` arrives with its consumer
(ARCHITECTURE_DECISIONS, section B3). That axis is added here, by its
reader, not in advance.

**This step is necessarily one commit.** `relation_graph.py` clause 1
asserts the vendored asset exists and a route serves it; clause 4 collects
`function relGraph\w+` bodies and fails vacuously on zero. `graph_primitive.py`
rule 5 asserts a live entry's prefix is present at its locus. Deleting the
functions, deleting the vendor, removing the registry entry and re-homing
the check cannot be separated without leaving the branch red between
commits. Size is not a reason to split what atomicity forbids splitting.

**Gate.** If RECON-0058-a M1 returned REFUTED, do not execute this brief.
STOP and return to Nia.

## Scope IN

1. **`frontend/src/graph/Graph.svelte` - add force placement.** `autoPlace`
   (`Graph.svelte:34`) is today the single placement strategy: stored
   coordinates when present, circular fallback when null. Add a second
   strategy, selected by a new prop `layout` whose only two values are
   `'positional'` (default, current behaviour) and `'force'`. Under
   `'force'`, node coordinates are computed by the simulation, stored
   coordinates are ignored, and `onMoveNode` is not honoured even if
   supplied - a force layout has no persisted positions to write.

   Implement the simulation in the exact form RECON-0058-a M1(b) measured
   as viable: fixed iteration count, no library, no animation loop unless
   M1 recorded one as necessary. Copy the working parameters from the
   result file; do not re-tune by feel.

   The `layout` prop is the FIRST boolean-shaped axis in this contract, and
   it is admitted only because two consumers now set it differently. Record
   that in a comment referencing TICKET-0057 E1.

2. **`frontend/src/graph/Graph.svelte` - zoom and pan.** Required by M2 as
   `PORT`. Implement as an SVG `viewBox` transform driven by wheel and
   drag-on-canvas, present only when `layout === 'force'` unless M2 reports
   the positional consumers need it too. No new dependency.

3. **`frontend/src/graph/consumers/relations.js` - new consumer.** Follows
   the shape of `consumers/lieux.js` exactly: a private `api()` helper, a
   default export with `chrome`, `load`, and the callbacks the surface
   actually uses. Specifically:
   - `load(meta)` calls `GET /api/relation-graph`
     (`cockpit/crud/relations.py:271`) when `meta.mode === 'global'`, and
     `GET /api/characters/{id}/relation-graph` (`relations.py:211`) when
     `meta.mode === 'ego'`. Both endpoints are read-only and unchanged.
   - `onDeleteEdge` calls the pre-existing `DELETE /api/relations/{id}`.
   - Edge-panel save calls the pre-existing relation CRUD endpoint.
   - **No new endpoint, no widened endpoint, no write from ego mode.** Ego
     mode supplies no write callback at all, so the primitive renders it
     display-only by construction - the same guarantee `relation_graph.py`
     clause 4 defends today, now enforced by the absence of a callback
     rather than by a grep over function bodies.

4. **Mode, buckets, info card, edge panel.** Per M2's classification:
   - Ego/global switching and the four strength buckets (1-25, 26-50,
     51-75, 76-100) are consumer-level filtering and chrome, expressed
     through `graph/mount.js`'s generic `chrome` descriptor
     (`mount.js:62-73`) extended as needed - never inside `Graph.svelte`,
     whose prop contract carries no titles or filter state.
   - Double-click-to-recentre is an ego-mode remount with a new `meta.id`.
   - The info card and edge panel are consumer-owned DOM beside the mount
     target, not primitive concerns.
   Anything M2 marked `DROP` is dropped ONLY if Nia approved that specific
   row. An unapproved `DROP` is an escalation, not a decision.

5. **`index.html` - swap the slot and delete the implementation.**
   - `CREATION_TABS.npc`'s slot (`index.html:4287-4289`) loses
     `loader: relGraphLoad, onSelect: relGraphOnSelect` and gains
     `graph: { consumer: 'relations' }`, matching the closed vocabulary
     `graph_primitive.py` rule 9 already enforces
     (`consumer`/`mountId`/`extraEdges` only). `display: 'on_demand'` and
     `toggleLabel` are unchanged - `page_contract.py` asserts them.
   - Delete all fifteen `relGraph*` functions (`index.html:10478..10820`).
   - Delete `#relgraph-canvas`, `#relgraph-info-card`, `#relgraph-help`,
     the four `.relgraph-bucket` checkboxes and the two mode buttons
     (`index.html:1301-1327`), which are now consumer-rendered.
   - **Preserve untouched** the `npcAgentToggle()` / `linkAgentToggle()`
     launchers and the `#npcagent-panel` / `#linkagent-panel` containers
     (`index.html:1303-1318`) per M8: they belong to TICKET-0059's link
     agent, not to the graph. If M8 reported that preserving them is
     impossible without editing those functions, STOP and escalate.
   - Delete the `<script src="/vendor/cytoscape-...">` tag.

6. **Delete the vendored engine.** Remove
   `src/world_engine/cockpit/vendor/cytoscape-3.34.0.min.js`. If it is the
   only whitelisted asset, remove `_VENDOR_WHITELIST`, the
   `GET /vendor/{filename}` route (`cockpit/app.py:235-239`), `_VENDOR_DIR`
   and the now-empty directory. If any other asset remains, leave the route
   and remove only the whitelist entry.

7. **`frontend/src/graph/registry.js` - remove the entry.** `GRAPH_IMPLS`
   becomes an empty frozen object, with its explanatory comment retained
   and one sentence appended recording that the last implementation
   converged at TICKET-0058.

8. **`tooling/verify/baselines/graph_impls.retired` - append one record**,
   in the form brief -b defined:
   `relation_cytoscape|relGraph|src/world_engine/cockpit/index.html`

9. **`graph_primitive.py` - extend the GONE list.** Add every `relGraph*`
   identifier and every deleted module-level `let/const` belonging to it
   (the `_relGraph*` state, mode and bucket variables) to `GONE_PLAIN`.
   Also add `cytoscape` as a token that must not appear in `index.html` in
   any context.

10. **`relation_graph.py` - re-home, in this commit.** Clause 1 (vendored
    asset + route) is deleted and replaced by an assertion that no vendored
    graph engine exists and no route serves one. Clause 4 (`relGraph*` write
    confinement) is deleted and replaced by an assertion over
    `frontend/src/graph/consumers/relations.js`: every non-GET `fetch` in
    that file targets only `/api/entities/{id}/relations` or
    `/api/relations/{id}`, and zero collected fetches is a failure. Clauses
    2 and 3 - the two read-only endpoints exist in `crud/relations.py` and
    both exclude `type IN ('connects_to','controls')` in the WHERE clause -
    are unchanged; they are backend guarantees and this ticket is
    frontend-only. Update the module docstring to record what moved and why.

## Scope OUT

- **Migrating any Creation panel to Svelte.** That seam is brief -d. This
  step uses the `graph:slot` channel that already exists.
- **The NPC agent and link agent** (`npcAgent*`, `linkAgent*`). TICKET-0059.
  Their launchers survive this step byte-untouched.
- **The Lieux and review consumers.** Converged at TICKET-0057; not
  re-opened, not re-tuned, not "harmonised" with the new consumer.
- **`graph_spec_for(entity_type)`.** Named deferral from TICKET-0057 D2; it
  stays deferred - no entity type declares a graph, so it would still be
  structure without a reader (E2).
- **Any backend change.** No new endpoint, no widened endpoint, no schema
  touch. If the migration appears to require one, that is an escalation
  (TICKET-0058 cross-cutting rule 2).
- **Retiring `creation` from the legacy mount registry.** TICKET-0059.
- **Re-tuning the force parameters by eye.** They come from M1.

## Invariants to defend

- **One graph, structurally.** After this step the graph registry is empty.
  A second engine becomes constructible only by defeating a fail-closed
  check. This is the step that turns the claim into the measured fact.
- **The primitive never fetches and never writes** (`graph_primitive.py`
  rule 7). The simulation is placement; every call stays in the consumer.
- **No scoped CSS in the primitive** (rule 8). The component renders inside
  the legacy iframe; Svelte injects scoped CSS into the shell's head.
- **No `<svg` outside `frontend/src/graph/`** (rule 6). Zoom/pan controls
  rendered as chrome must not be SVG icons.
- **Ego mode stays permanently display-only** - now by callback absence
  rather than by grep.
- **Fail-closed guards never lapse.** `relation_graph.py` is re-homed in
  this commit, not after it.

## Done means

- [ ] `grep -c relGraph src/world_engine/cockpit/index.html` returns 0.
- [ ] `grep -ci cytoscape src/world_engine/cockpit/index.html` returns 0.
- [ ] `src/world_engine/cockpit/vendor/` contains no cytoscape asset.
- [ ] `frontend/src/graph/registry.js` declares zero entries.
- [ ] `graph_impls.retired` contains exactly one record.
- [ ] `python tooling/verify/checks/graph_primitive.py` exits 0 and reports
      0 live, 1 retired.
- [ ] `python tooling/verify/checks/relation_graph.py` exits 0.
- [ ] `python tooling/verify/checks/page_contract.py` exits 0 (the NPC slot
      still declares `display: 'on_demand'`).
- [ ] Live: NPC tab -> "Voir le graphe" opens the graph; global mode renders
      the full graph; each of the four bucket checkboxes visibly filters;
      wheel zooms and canvas-drag pans; double-clicking a node switches to
      that node's ego view; the info card populates on node click.
- [ ] Live: in global mode, an edge is saved and an edge is deleted, and
      both survive a reload.
- [ ] Live: in ego mode, no control offers to modify a relation.
- [ ] Live: "Agent PNJ" and "Agent liens" still open their panels.
- [ ] `npm run build` succeeds and `frontend_build_fresh.py` passes.
- [ ] `/review-step` and `/close-step` run; ONE commit.

## Docs to update

- `world-engine-schema.md`: no entry. No schema change.
- `ARCHITECTURE_DECISIONS.md`: no entry here - the whole ticket's decisions
  are written once, in brief -l. Do not pre-write it.
