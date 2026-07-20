# BRIEF — Step "Region review: pre-commit location graph (on demand)" (BRIEF-0033-d)

## Context

The Lieux tab already has an SVG location graph (`graphAutoPlace`
`index.html:8959`, `graphRender` `index.html:8974`, `graphLoad`
`index.html:9125`, consts `GRAPH_W`/`GRAPH_H`/`NODE_R`/`DRAG_THRESHOLD`
`index.html:8949-8952`) with an on_demand toggle slot (BRIEF-0023-a
contract, slot declared at `index.html:4023`, panel markup
`index.html:1253-1263`, `.lieux-graph-head` CSS class `index.html:984`).
Locked C1: the region REVIEW screen gets a pre-commit view of the drafted
structure — hidden by default, opened only on demand — reusing the
existing renderer's visual language, fed by the draft instead of the DB.
The Région tab is a bespoke archetype (`regionRenderAll`, `index.html:6217`),
so the shell slot mechanism does not apply; a local toggle is specified
instead. Read-only: draft entities have no IDs, so no edge creation and no
position persistence pre-commit.

Backend confirmed-link resolution (`_region_resolve_link_target`,
`src/world_engine/cockpit/routes/regions.py:101-132`) matches a
`sensed_links` target intra-region first: exact string, trimmed and
lowercased, against committed names, before falling back to a DB scan.
Pre-commit there is no DB fallback (nothing committed yet) — the client
adapter mirrors only the intra-region half: trim + lowercase match of
`link.name` against draft location names.

## Scope IN

1. In `regionRenderAll` (`index.html:6217`), insert between the
   skipped-notes block (ends `index.html:6238`) and the tree/factions
   flex columns (starts `index.html:6239`): a toggle button
   "Voir le graphe des lieux" (btn-icon style, mirroring the shell's
   on_demand toggle look) and an initially-hidden container
   `<div id="region-lieux-graph" style="display:none">` holding an SVG
   with the same id-namespaced structure as `lieux-graph-svg`
   (`index.html:1259`) — new id `region-lieux-graph-svg`, same
   viewBox/height, `.lieux-graph-head` class reused for the header row.
2. State: `let regionLocGraphOpen = false;` (declared alongside
   `regionAccepted`/`regionConfirmedLinks`, `index.html:5746-5747`),
   toggled by the button (label flips to "Masquer le graphe des lieux").
   Reset to `false` by `regionRestart()` (`index.html:6041-6051`) and by
   `_regionWorldReset()` (`index.html:3936-3943`) alongside the existing
   region state resets.
3. Adapter `regionLocGraphData()`: nodes = draft locations
   (`regionDraft.locations`) whose `local_id` passes `regionIsAccepted`
   (`index.html:5758`), shaped `{ id: local_id, name: draft.public.name }`
   for `graphAutoPlace`; hierarchy edges from `regionCascade().effectiveParent`
   (`index.html:5784-5806` — reuse the cascade helper as-is, do NOT
   reimplement the fallback-to-root logic; skip entries whose
   `effectiveParent` is `null`); connection edges from CONFIRMED
   `sensed_links` (`regionIsLinkConfirmed`, `index.html:5774`) of kind
   `connection` on each accepted location's `draft.secret.sensed_links`,
   whose `link.name` resolves by trim+lowercase match to another accepted
   draft location's name (mirroring the intra-region half of
   `_region_resolve_link_target`, `regions.py:101-132` — see Context);
   unresolved or self-referential names simply produce no edge (the
   existing link-toggle UI, `regionRenderLinkToggles`, is untouched).
   Visually distinguish hierarchy edges (solid, existing `graphRender`
   style) from confirmed connections (dashed, e.g. `stroke-dasharray="4"`).
4. Renderer `regionLocGraphRender()`: reuse `graphAutoPlace` (`index.html:8959`)
   for layout; draw with the same node/edge SVG markup as `graphRender`
   (`index.html:8974-9006`) into `#region-lieux-graph-svg`, but with NO
   handlers wired for edge creation, edge deletion, or position
   persistence (`graphCreateEdge`, `graphEdgeClick`'s delete path,
   `graphPersistPos` are not called, and no `onmousedown`/`onclick` are
   attached to nodes or edges). Static layout — node drag is omitted
   entirely.
5. Refresh triggers while open: accept/reject toggles
   (`regionToggleAccept`, `index.html:5762`), link confirm toggles
   (`regionToggleLink`, `index.html:5778`), and sheet closes already
   funnel through `regionRenderAll()` — call `regionLocGraphRender()` at
   the end of `regionRenderAll()` when `regionLocGraphOpen` is true. When
   closed: render nothing (leave the container's `innerHTML` empty), zero
   cost.

## Scope OUT

- No post-commit change to the Lieux tab graph (already refreshes after
  commit, `regionCommit`, `index.html:6269`).
- No edge editing, no node position persistence, no draft mutation from
  the graph — strictly a viewport.
- No cytoscape here: the location graph stays on the existing SVG path.
- No NPC graph anywhere in the review (D2 — NAMED DEFERRAL, next ticket).
- No extraction/refactor of `graphRender` into shared helpers beyond what
  reuse strictly requires; if `graphAutoPlace` needs a parameter, add the
  parameter — do not restructure the module.

## Invariants to defend

- No structure without a reader: no new backend endpoint, no new draft
  keys — the adapter reads only existing draft/cascade state.
- Exclusion structural: nothing secret is rendered (location secret fields
  never enter the adapter).

## Done means

- [ ] Live: in a review with >= 4 locations (one root, one child, one
      confirmed connection link), the graph is NOT visible on arrival;
      opening it shows accepted locations, hierarchy edges solid,
      confirmed connection dashed; rejecting a location while open removes
      it and re-parents its children per cascade; closing hides it;
      "Recommencer" resets to closed.
- [ ] Live: Lieux tab graph behavior unchanged (open, create an edge,
      drag a node — all still work).
- [ ] `/review-step` and `/close-step` run.
- [ ] All verify checks pass.

## Docs to update

- ARCHITECTURE_DECISIONS.md, TICKET-0033 section: C1 recorded —
  pre-commit location graph is an on-demand, read-only viewport over the
  draft cascade; SVG renderer reused; no persistence pre-commit.
