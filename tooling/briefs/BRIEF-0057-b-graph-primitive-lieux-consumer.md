# BRIEF — Step "graph primitive + Lieux consumer, legacy implementation deleted"

## Context

BRIEF-0057-a confirmed the island mount is constructible. This step builds
the primitive and converges its FIRST consumer, the canonical Lieux
adjacency editor (`index.html:10464..10639`, 12 functions / 165 lines).

The 12 legacy functions, 4 constants and 4 globals are DELETED in this same
step, not left behind a flag. That is the creator's locked constraint - no
dormant code at ticket close - and BRIEF-0057-a's M7 confirmed every use of
those symbols sits inside the deleted set. There is no automated safety net
for a dangling JS reference (`undefined_names.py` covers Python only), so
the deletion list below is exhaustive by construction and re-asserted by
brief -d's GONE rule.

## Scope IN

1. **`frontend/src/legacy/bridge.js` gains one export.**

   ```js
   /* TICKET-0057. The graph primitive renders as an ISLAND inside the
      legacy document (Creation is a legacy mount until TICKET-0059, and
      TICKET-0056 deferred continuous route sync to TICKET-0058 -- the
      shell cannot know which sub-tab is active, so a shell-side graph
      pane is not constructible). This export hands out a node from the
      legacy document; the `contentWindow` token stays confined to this
      file, so legacy_mount.py assertion 5 is unchanged. */
   export function legacyContainer(id) {
     const el = legacyWindow().document.getElementById(id);
     if (!el) {
       throw new Error(`legacy/bridge: no element #${id} in the legacy document`);
     }
     return el;
   }

   export function legacyDocument() {
     return legacyWindow().document;
   }
   ```

   No other change to `bridge.js`. Do NOT widen `CONFINED_FILES` in
   `legacy_mount.py:38-41`.

2. **New `frontend/src/graph/Graph.svelte` - the primitive.**

   Header comment, verbatim:

   ```
   TICKET-0057. THE graph. One component, one engine, one contract.

   The primitive NEVER fetches and NEVER writes. It renders nodes and
   edges and reports interactions through callbacks. Every network call
   belongs to a consumer -- which keeps canon writes on the consumer side
   of the seam, where the sanctioned endpoints already are.

   Capability is declared by the PRESENCE of a callback, not by a boolean
   axis: no `onMoveNode` means no drag, no `onConnect` means no
   select-to-connect, no `onDeleteEdge` means edges are not clickable.
   Booleans would have had to be invented in pairs nothing sets
   independently; a callback is evidenced by its consumer or it is absent.

   No `<style>` block. This component renders INSIDE the legacy iframe
   document, and Svelte's scoped CSS is injected into the shell's head,
   where it would never reach. Styling is by SVG attributes referencing
   the legacy CSS variables, plus legacy class names.
   ```

   Props, exactly this set and no other:

   ```js
   let {
     nodes = [],          // [{ id, name, coord_x?, coord_y? }]
     edges = [],          // [{ id, entity_a_id, entity_b_id, kind? }]
     dashedKinds = [],    // edge `kind` values rendered dashed
     onConnect = null,    // (aId, bId) -> void|Promise
     onDeleteEdge = null, // (edgeId) -> void|Promise
     onMoveNode = null,   // (nodeId, x, y) -> void|Promise
   } = $props();
   ```

   Constants, moved here from `index.html:10454-10457` unchanged:
   `GRAPH_W = 960`, `GRAPH_H = 480`, `NODE_R = 20`, `DRAG_THRESHOLD = 5`.

   `autoPlace(nodes)` - the primitive's single placement strategy (locked
   decision G). Logic transcribed from `graphAutoPlace`
   (`index.html:10464-10477`) without behavioural change: a node with a
   non-null `coord_x` keeps `{x: coord_x, y: coord_y}`; null-coordinate
   nodes are laid on a circle of radius `min(cx,cy)*0.72` centred on
   `(GRAPH_W/2, GRAPH_H/2)`, ordered by sorted id, with the single-node
   case placed dead centre. This is why `placement` is NOT an axis: one
   strategy already covers both consumers, and which branch runs is
   decided by the data.

   Rendering, transcribed from `graphRender` (`index.html:10479-10511`):
   edges as `<line>` with `stroke="var(--muted)"`, `stroke-width="2"`,
   `stroke-linecap="round"`, plus `stroke-dasharray="4"` when
   `dashedKinds.includes(edge.kind)`; nodes as `<g>` holding a `<circle>`
   `r={NODE_R}` `fill="var(--card)"` `stroke="var(--border)"`
   `stroke-width="1.5"`, and a `<text>` at `y + NODE_R + 13`,
   `text-anchor="middle"`, `fill="var(--text)"`, `font-size="11"`,
   `style="pointer-events:none;user-select:none"`. Selected node:
   `fill`/`stroke` become `var(--accent)` and `stroke-width` 2.5. Node
   cursor `grab` only when `onMoveNode` is set; edge cursor `pointer` only
   when `onDeleteEdge` is set.

   Selection and connection, transcribed from `graphNodeClick`
   (`index.html:10568-10584`): selection is INTERNAL component state, not
   a prop. First click selects; second click on the same node deselects;
   second click on a different node calls `onConnect(A, B)` unless an edge
   already joins the pair in either direction (the undirected dedup at
   `index.html:10577-10581` is preserved, verbatim in behaviour); a click
   on empty canvas clears the selection.

   Drag, transcribed from `graphNodeMD`/`_graphMouseMove`/`_graphMouseUp`/
   `_graphMoveSVGNode` (`index.html:10513-10566`): threshold
   `DRAG_THRESHOLD` before a press counts as a move; incident edge
   endpoints follow the dragged node live; on release, if it moved,
   `onMoveNode(nodeId, x, y)` is called. **Listeners for `mousemove` and
   `mouseup` are registered on the host confirmed by BRIEF-0057-a M2(b)**
   - `node.ownerDocument.defaultView` - never on the bare `window`.
   Register on press, remove on release. If M1 reported that Svelte's
   delegated events do not cross the frame boundary, use the exact working
   form M1 recorded.

   Empty state: when `nodes` is empty, render the centred muted placeholder
   text rather than a blank canvas.

3. **New `frontend/src/graph/consumers/lieux.js`** - fetch and writes, all
   against PRE-EXISTING endpoints, no new API surface:
   - load: `GET /api/locations/graph` -> `{ nodes, edges }`
   - `onConnect(a, b)`: `POST /api/entities/{a}/relations`, body
     `{ other_entity_id: b, type: 'connects_to' }`, then reload.
   - `onDeleteEdge(id)`: a confirm prompt with the exact existing wording
     `Supprimer cette connexion ?`, then
     `DELETE /api/relations/{id}`, then reload.
   - `onMoveNode(id, x, y)`: `GET /api/entities/{id}`, merge
     `coord_x: Math.round(x)`, `coord_y: Math.round(y)` into `extension`,
     then `PUT /api/entities/{id}` with `{ entity, extension }`. The
     two-scalar-column shape is deliberate and must not become a JSON
     read-merge-write (TICKET-0025, BRIEF-0025-b); the comment at
     `index.html:10612-10613` is carried over.
   - Errors: surface into the graph area as the existing red message did
     (`index.html:10637`), never a silent `catch`.
   - `dashedKinds`: `[]` for this consumer.

4. **New `frontend/src/graph/mount.js`** - the mount/teardown registry.
   - `mountGraph(containerId, consumerKey)` mounts a `Graph` into
     `legacyContainer(containerId)`.
   - Idempotent per `containerId`, and re-mounts when the live node is no
     longer the node it mounted into (the review panels re-emit their
     markup - see BRIEF-0057-a M8; brief -c depends on this behaviour, so
     build it here).
   - `unmountGraph(containerId)` tears down.
   - A second mount into a container that already holds a live instance is
     refused with a thrown error, never silently doubled.

5. **The legacy -> shell signal.** One direction of control, no function
   installed on the legacy window, no name collision. Legacy dispatches
   CustomEvents on its own `document`; `mount.js` listens via
   `legacyDocument()`.

   - `_onDemandSlotToggle` (`index.html:4120-4132`): replace the
     `if (slot.loader) slot.loader();` branch so that a slot declaring
     `graph` dispatches instead:
     ```js
     if (st.open && !st.loaded) {
       st.loaded = true;
       if (slot.graph) {
         document.dispatchEvent(new CustomEvent('graph:slot', {
           detail: { consumer: slot.graph.consumer, containerId: slot.containerId, open: true },
         }));
       } else if (slot.loader) {
         slot.loader();
       }
     }
     ```
     `loader` support stays - the `pj` tab's `fiche` slot
     (`index.html:4300`) still uses it.
   - The three post-write refresh sites, `index.html:6718`, `7094`, `9675`,
     currently `if (currentCreationSubTab === 'lieux') graphLoad();`,
     become:
     ```js
     if (currentCreationSubTab === 'lieux') {
       document.dispatchEvent(new CustomEvent('graph:invalidate', { detail: { consumer: 'lieux' } }));
     }
     ```
     The `currentCreationSubTab` guard is preserved exactly - behaviour
     unchanged.

6. **The declaration seam (locked decision D2).**
   `CREATION_TABS.lieux.slots[0]` (`index.html:4313-4314`) becomes:
   ```js
   slots: [{ id: 'graph', containerId: 'creation-lieux-graph', loader: null, onSelect: null,
             display: 'on_demand', toggleLabel: 'Voir le graphe',
             graph: { consumer: 'lieux' } }],
   ```
   `display: 'on_demand'` is preserved verbatim - `page_contract.py:169-174`
   asserts it.

7. **`page_contract.py`.** If BRIEF-0057-a M4 reported the slot parser
   FAILS on a nested object, apply the narrow fix it identified, in a
   SEPARATE commit, and change nothing else in that file. If M4 reported
   PASS, touch `page_contract.py` not at all. Anything else found in that
   file: REPORT ONLY.

8. **Markup.** `index.html:1277-1288` (`#creation-lieux-graph`) collapses
   to a bare mount container - the head bar, the refresh button, the
   `<svg id="lieux-graph-svg">` and the help paragraph are all re-emitted
   by the island:
   ```html
   <!-- TICKET-0057: mount point for the graph primitive (island rendered
        by the shell into this legacy document). Empty by construction --
        chrome, canvas and help text all belong to Graph.svelte and its
        Lieux consumer. -->
   <div id="creation-lieux-graph" style="display:none"></div>
   ```
   The island re-emits the head bar using the legacy classes
   `lieux-graph-head` and `btn-icon` (confirmed applicable by
   BRIEF-0057-a M3c), the refresh control, and the help sentence verbatim:
   `Cliquez un nœud pour le sélectionner, puis un second pour le connecter. Glissez pour repositionner. Cliquez un lien pour le supprimer.`

9. **Deletions - exhaustive, this is the zero-dormant-code clause.**
   Remove from `index.html`:
   - the 12 functions `graphAutoPlace`, `graphRender`, `graphNodeMD`,
     `_graphMouseMove`, `_graphMouseUp`, `_graphMoveSVGNode`,
     `graphNodeClick`, `graphEdgeClick`, `graphCanvasClick`,
     `graphCreateEdge`, `graphPersistPos`, `graphLoad`
     (`index.html:10464..10639`);
   - the section banner comment at `index.html:10449-10452`;
   - the constants `GRAPH_W`, `GRAPH_H`, `NODE_R`, `DRAG_THRESHOLD`
     (`10454-10457`);
   - the globals `graphData`, `graphSelectedNodeId`, `_graphDrag`,
     `_graphPlaced` (`10459-10462`);
   - the inline handlers at `1280` (`graphLoad()`) and `1284`
     (`graphCanvasClick(event)`), with the markup that carried them.

   `NODE_R` is still referenced by `reviewGraphRender` at
   `index.html:6266-6267`. Brief -c deletes that function. **Sequencing
   constraint: this brief must therefore keep `NODE_R` alive OR land
   together with -c.** Resolution: this brief deletes `NODE_R` and
   `graphAutoPlace`, and -c's changes to `reviewGraphRender` are folded
   forward - see -c Scope IN 1, which is written to be landed in the same
   push. If -b and -c are landed as separate commits, -b's commit must
   leave `NODE_R` and `graphAutoPlace` in place with a
   `// TICKET-0057: removed by BRIEF-0057-c` marker, and -c removes them.
   **Both commits must be pushed together; the branch is not offered for
   verify between them.**

10. **Build.** Run the command sequence BRIEF-0057-a M6 recorded, so that
    `frontend/src/world_engine/cockpit/static/` is regenerated and
    committed, `frontend_build_fresh.py` is green, and the boot guard
    (`app.py:208-220`) is satisfied.

## Scope OUT

Named temptations, each already discussed and deliberately deferred:

- **The relation / cytoscape graph.** Not converged here. `relGraph*`
  (`index.html:10672..10994`), the vendored cytoscape file, `index.html:1613`
  and `vite.config.js:14`'s `external: ['cytoscape']` are all untouched.
  It converges at TICKET-0058 and is registered as a baseline entry by
  brief -d.
- **The review pre-commit preview.** Brief -c. Do not convert
  `reviewGraphRender` here.
- **The lock check.** `graph_primitive.py` and `graph_impls.baseline` are
  brief -d. Do not write a partial version here.
- **`relation_graph.py`'s clause 5.** It WILL go red on this branch the
  moment the Lieux functions are deleted - that is expected and correct.
  Do not delete, disable, skip or weaken it here. Brief -d replaces it.
  Report the red; do not act on it.
- **`traits.py` / `graph_spec_for(entity_type)`.** Locked deferral (D1).
  No trait is added, `ext_columns_for`/`form_fields_for` are untouched.
- **Force layout, `directed`, `weighted`, `temporal`, `persistsPositions`,
  `editable` booleans.** E1: no axis is added that no pilot consumer sets.
- **Continuous route sync / URL <-> sub-tab.** TICKET-0058's named
  deferral (TICKET-0056). The graph does not read or write the URL.
- **Any new API endpoint, any change to `crud/`, `routes/`, `writes/`, or
  the schema.** Frontend only. A migration that appears to need a backend
  change is an ESCALATION, not a silent edit.
- **Widening `legacy_mount.py`'s `CONFINED_FILES`.** The design avoids
  needing it; if it appears necessary, that is an escalation.
- **Migrating any other Creation sub-tab, panel or handler.** 0058/0059.
- **Renaming `index.html`.** TICKET-0061's named deferral.
- **A shared "island" abstraction for future non-graph surfaces.** Build
  exactly the mount this ticket needs.

## Invariants to defend

- **Single canon-write authority (S-norme).** The Lieux consumer creates a
  `connects_to` relation, deletes a relation, and persists coordinates. All
  three go through the pre-existing sanctioned routes, unchanged and
  unwidened. The primitive itself performs no fetch and no write - that is
  the invariant most at risk here, because "let the component just save it"
  is the obvious shortcut. It is forbidden.
- **No JSON storage for UI-visible data.** `coord_x`/`coord_y` are two
  scalar columns, not a JSON blob (TICKET-0024/0025). The PUT shape is
  preserved exactly.
- **Confinement (TICKET-0056).** `contentWindow` / `legacy-frame` tokens
  stay inside `bridge.js` and `LegacyFrame.svelte`. `legacyContainer` is
  how everything else reaches the legacy DOM.
- **One iframe, one src.** No `.src =` reassignment anywhere
  (`legacy_mount.py` assertion 6).
- **Fail-closed over advisory.** `legacyContainer` throws on a missing
  node; `mountGraph` throws on a double mount; a failed graph load renders
  a visible red message. No `catch (_) {}`.
- **No structure without a reader (E2).** Every prop of the primitive is
  set by a real consumer in this brief or in -c. If a prop ends up set by
  nobody, delete the prop.

## Done means

- [ ] `frontend/src/graph/Graph.svelte`, `frontend/src/graph/mount.js` and
      `frontend/src/graph/consumers/lieux.js` exist.
- [ ] `grep -c 'function graphAutoPlace\|function graphRender\|function graphNodeMD\|function _graphMouseMove\|function _graphMouseUp\|function _graphMoveSVGNode\|function graphNodeClick\|function graphEdgeClick\|function graphCanvasClick\|function graphCreateEdge\|function graphPersistPos\|function graphLoad' src/world_engine/cockpit/index.html`
      returns `0`.
- [ ] `grep -c 'GRAPH_W\|GRAPH_H\|DRAG_THRESHOLD\|graphData\|graphSelectedNodeId\|_graphDrag\|_graphPlaced' src/world_engine/cockpit/index.html`
      returns `0`.
- [ ] `grep -n 'lieux-graph-svg' src/world_engine/cockpit/index.html`
      returns nothing.
- [ ] `grep -c 'contentWindow' frontend/src/graph/*.js frontend/src/graph/**/*.js frontend/src/graph/*.svelte`
      returns `0`.
- [ ] `grep -n 'graph:' src/world_engine/cockpit/index.html` shows the
      `graph: { consumer: 'lieux' }` spec on the Lieux slot.
- [ ] `npm run build` run; `src/world_engine/cockpit/static/` committed.
- [ ] `python tooling/verify/checks/frontend_build_fresh.py` -> PASS.
- [ ] `python tooling/verify/checks/legacy_mount.py` -> PASS.
- [ ] `python tooling/verify/checks/page_contract.py` -> PASS.
- [ ] `python tooling/verify/checks/relation_graph.py` -> FAIL, and the
      failure is EXACTLY on clause 5 (Lieux functions not found). Any other
      clause failing is a defect in this step, not the expected red.
- [ ] Live: Creation > Lieux > "Voir le graphe" renders the map; stored
      positions honoured; null-coordinate nodes on the circle.
- [ ] Live: press-move-release on a node moves it, incident edges follow,
      the position survives a page reload.
- [ ] Live: node, then second node -> a `connects_to` link appears; the
      same pair again -> nothing happens.
- [ ] Live: click an edge -> `Supprimer cette connexion ?` -> deleted,
      graph refreshed.
- [ ] Live: click empty canvas with a node selected -> selection clears.
- [ ] Live: save a location from the author sheet with Lieux active -> the
      graph refreshes by itself.
- [ ] Live: commit a region, then a room batch -> the graph refreshes in
      both cases.
- [ ] Live: toggling "Voir le graphe" off and on twice does not double the
      canvas or throw.
- [ ] Live: the NPC relation graph still works (ego + global, buckets,
      edge panel).
- [ ] `/review-step` and `/close-step` run (engine-adjacent code touched).

## Docs to update

None in this step. CLAUDE.md, ARCHITECTURE_DECISIONS.md and CHANGELOG.md
are brief -e, so the doctrine text lands once, describing the finished
shape, rather than being rewritten three times.
