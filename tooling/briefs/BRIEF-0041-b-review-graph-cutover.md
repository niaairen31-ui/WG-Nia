# BRIEF - Step "review graph cutover"

## Context
TICKET-0041, step 2 of 3. BRIEF-0041-a extracted the review core and left the
three pre-commit graph functions on their old `region*` names, calling the new
generic cascade transitionally. This step moves them into the component. The
split matters: the region half of the graph - confirmed `sensed_links` resolved
by trimmed lowercase name - is model-shaped and must stay region-side, while the
hierarchy edges, the placement and the SVG emission are consumer-agnostic. The
G1 check is BRIEF-0041-c.

## Mini-RECON (verify before writing a line; report any drift, do not adapt silently)
Anchors taken on live `main` at schema v1.85, BEFORE BRIEF-0041-a landed - all
three will have shifted. Re-locate by name, do not trust the numbers:
- `regionToggleLocGraph:6318`, `regionLocGraphData:6327`, `regionLocGraphRender:6356`.
- The graph pane markup is emitted inside `regionRenderAll` (`:6294-6302` before
  BRIEF-0041-a): the `lieux-graph-head` wrapper, the `region-lieux-graph` div and
  `<svg id="region-lieux-graph-svg" viewBox="0 0 960 480">`.
- `if (regionLocGraphOpen) regionLocGraphRender();` at the tail of
  `regionRenderAll` (`:6315` before BRIEF-0041-a).
- Shared placement helpers: `const NODE_R = 20` at `:9299`, `graphAutoPlace` at
  `:9307`. Both are declared AFTER the region block and are already shared - the
  NPC relation graph calls `graphAutoPlace` at `:9325`. `function` declarations
  hoist; `const NODE_R` does NOT. Confirm the component still only reads
  `NODE_R` from inside a function called on user interaction, never at block
  evaluation time. If that is no longer true, STOP and report - a TDZ error
  here is silent until the graph is opened.
- Confirm `regionReviewDescriptor` (BRIEF-0041-a) exists and currently carries
  `graphExtraEdges: () => []`.

## Scope IN

1. **`reviewToggleGraph(key)`** in the component block, replacing
   `regionToggleLocGraph`: calls `d.onToggleGraph()` then `d.onRender()`.

2. **`reviewGraphData(key)`** in the component block, replacing
   `regionLocGraphData`. Generic half only:
   - `const d = reviewDescriptor(key); const cascade = reviewCascade(d);`
   - nodes: `d.nodes` filtered by `cascade.acceptedIds`, mapped to
     `{ id, name }`;
   - hierarchy edges: for each accepted node with a non-null
     `cascade.effectiveParent[id]`, `{ id: 'h-' + id, entity_a_id: parent,
     entity_b_id: id, kind: 'hierarchy' }` - id prefix `h-` UNCHANGED;
   - extra edges: `d.graphExtraEdges(cascade.acceptedIds, nodeById)`, where
     `nodeById` is a `Map` from node id to the node object;
   - returns `{ nodes, edges: [...hierEdges, ...extraEdges] }`. Hierarchy edges
     FIRST, extras second - the render order decides which line is drawn on top,
     do not reorder.

3. **`reviewGraphRender(key)`** in the component block, replacing
   `regionLocGraphRender`. Body transcribed verbatim from the current function,
   with two substitutions: the SVG is looked up by `d.graphSvgId` instead of the
   hard-coded `'region-lieux-graph-svg'`, and the data comes from
   `reviewGraphData(key)`. Everything else is byte-identical: the early return on
   a missing SVG, `graphAutoPlace(data.nodes)`, the `nodeMap` build, the dashed
   stroke for `kind === 'connection'`, `stroke="var(--muted)" stroke-width="2"
   stroke-linecap="round"`, `r="${NODE_R}"`, `fill="var(--card)"
   stroke="var(--border)" stroke-width="1.5"`, the label at
   `y + NODE_R + 13`, `font-size="11"`, `pointer-events:none;user-select:none`,
   and the single `svg.innerHTML = edgesHTML + nodesHTML` assignment.

4. **`regionReviewDescriptor.graphExtraEdges` filled in** - the region-specific
   half, moved out of the old `regionLocGraphData` unchanged in behaviour.
   Signature `(acceptedIds, nodeById) => [...]`. Keep the BRIEF-0033-d comment
   verbatim above it:

   ```
   /** Pre-commit location graph adapter (C1, BRIEF-0033-d) - draft-fed, no IDs,
    * read-only. Mirrors the intra-region half of _region_resolve_link_target
    * (regions.py) for confirmed connection links: trim+lowercase name match,
    * no DB fallback (nothing committed yet). */
   ```

   Logic, transcribed:
   - build `byName` from the ACCEPTED locations only: trimmed lowercase
     `public.name` -> `local_id`;
   - for each accepted location, for each `sensed_link` with
     `kind === 'connection'` that is confirmed
     (`regionIsLinkConfirmed(regionLinkKey(local_id, idx))`), resolve the trimmed
     lowercase `link.name` through `byName`; skip on empty name, on miss, and on
     self-link;
   - emit `{ id: 'c-' + local_id + '-' + idx, entity_a_id: local_id,
     entity_b_id: targetId, kind: 'connection' }` - id prefix `c-` and the
     `${localId}-${idx}` shape UNCHANGED.

   It reads `regionDraft` and the two `sensed_links` helpers: that is correct and
   deliberate. It is a region-side closure inside the region-side factory, not
   component code.

5. **`regionRenderAll` rewiring**: `onclick="regionToggleLocGraph()"` ->
   `onclick="reviewToggleGraph('region')"`, and the tail
   `if (regionLocGraphOpen) regionLocGraphRender();` ->
   `if (regionLocGraphOpen) reviewGraphRender('region');`. The graph pane markup
   itself - the `lieux-graph-head` wrapper, the toggle label
   `Masquer/Voir le graphe des lieux`, the `Carte des lieux (aperçu pré-commit)`
   caption, the `<svg>` element with its `viewBox`, `width`, `height` and inline
   style - STAYS in `regionRenderAll`, verbatim. The consumer owns its container;
   the component owns only what it draws inside it.

6. **Delete** `regionToggleLocGraph`, `regionLocGraphData`,
   `regionLocGraphRender`. That closes the list of nine.

## Scope OUT
- `tooling/verify/checks/review_component.py`: BRIEF-0041-c.
- Any visual enrichment of the graph. Nodes stay circles of radius `NODE_R`.
  Drawing bounds-scaled rectangles from TICKET-0040's `default_width` /
  `default_height` was explicitly rejected and belongs to no ticket.
- Moving, generalising or touching `graphAutoPlace` / `NODE_R`. They are already
  shared with the NPC relation graph; leave them exactly where they are.
- Moving the graph pane markup into the component.
- Moving `regionLinkKey` / `regionIsLinkConfirmed` / `regionToggleLink` into the
  component. They stay region-side, permanently.
- Any DB fallback for an unresolved link name. Nothing is committed at this
  point; a miss stays a miss, silently, exactly as today.
- Splitting `index.html` (C1, own ticket).

## Invariants to defend
- **`reviewCascade` stays pure.** `reviewGraphData` calls it and passes the
  descriptor; it must not start reading globals to serve the graph.
- **Component blind to region.** `reviewGraphData` and `reviewGraphRender` must
  not contain the token `region` - not in a variable name, not in a DOM id, not
  in a CSS class. The SVG id arrives through `d.graphSvgId`.
- **Rejected entities are absent from the graph**, not greyed. The filter is on
  `cascade.acceptedIds` at data construction, never a post-filter at render.
- **Read-only.** No fetch, no canon read, no canon write anywhere in this path.
  The pre-commit graph is a pure client render over `regionDraft`.
- **No structure without a reader.** `graphExtraEdges` was declared as `() => []`
  in BRIEF-0041-a specifically so this brief could fill it; it now has its
  reader. No further placeholder callback is added.

## Done means
- [ ] `grep -c "regionToggleLocGraph\|regionLocGraphData\|regionLocGraphRender\|regionCascade\|regionIsAccepted\|regionToggleAccept\|regionRenderNotes\|regionRenderLocationNode\|regionRenderTree" src/world_engine/cockpit/index.html` returns 0 - all nine gone.
- [ ] No body of a `function review*` contains the substring `region` (case-sensitive).
- [ ] `grep -n "region-lieux-graph-svg" src/world_engine/cockpit/index.html` returns exactly two lines: the `<svg id=...>` in `regionRenderAll` and the `graphSvgId` field in `regionReviewDescriptor`.
- [ ] `graphAutoPlace` and `NODE_R` are byte-identical to `main`.
- [ ] Live: open the pre-commit graph -> hierarchy edges solid, confirmed connection edges dashed, node labels centred under circles.
- [ ] Live: reject a location while the graph is open -> it disappears from the graph and its hierarchy edge with it, in one re-render.
- [ ] Live: confirm a connection link whose target name matches another accepted location -> a dashed edge appears. Un-confirm it -> the edge disappears.
- [ ] Live: confirm a connection link whose target name matches nothing -> no edge, no error in the console.
- [ ] Live: close and re-open the graph -> renders identically both times.
- [ ] Live: the toggle button label alternates between `Voir le graphe des lieux` and `Masquer le graphe des lieux`.
- [ ] Live: the NPC relation graph (Creation tab) still renders - `graphAutoPlace`'s other consumer is unaffected.
- [ ] Live: commit the region -> response shape unchanged.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update
None in this brief. BRIEF-0041-c carries the whole doc payload.
