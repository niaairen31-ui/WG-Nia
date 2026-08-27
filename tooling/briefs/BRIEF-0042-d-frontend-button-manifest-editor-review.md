# BRIEF - Step "frontend: batch button + manifest editor + review"

## Context
TICKET-0042, step 4 of 5. The backend generators exist (BRIEF-0042-a/b/c). This
step is the cockpit surface: a "Generer un lot ici" entry point on the Lieux
browse anchored on the current node, the Phase A manifest editor, the Phase B /
Phase C triggers, and the review, wired to the TICKET-0041 generic component via
a batch descriptor. The anchor enters the descriptor as a SYNTHETIC, non-editable
root node (Q1), so O1's distinct root and the "everything reaches the anchor"
tree fall out with no change to the shared component core. The atomic commit is
BRIEF-0042-e; this step calls it.

## Mini-RECON (verify before writing a line; report any drift, do not adapt silently)
Anchors on live `main`, schema v1.85, `index.html` = 11287 lines.
- Lieux browse: `renderLieuxBrowse:6596`; head built at `:6609`
  (`lieux-browse-head`); current node = `lieuxBrowseParentId` (null = root);
  breadcrumb `lieuxBreadcrumb:3143`; descend `lieuxDescend:6574`;
  `lieuxChildrenOf:6560`. The anchor IS `lieuxBrowseParentId` (the location you
  have descended into); at root it is null.
- Review component contract (TICKET-0041), consume verbatim:
  `reviewRegister(key, descriptor):5906`, `reviewCascade:5910`,
  `reviewIsAccepted:5925`, `reviewToggleAccept:5929`, `reviewNode:5946`,
  `reviewTree:5967`, `reviewToggleGraph:5985`, `reviewGraphData:5991`,
  `reviewGraphRender:6009`. Descriptor fields (read `regionReviewDescriptor:6071`
  as the worked example): `key, nodes[{id,name,subtitle,parentId,description,
  notes,extras}], accepted, fallbackParentId, reparentedLabel, graphSvgId,
  graphOpen, onToggleAccept, onToggleGraph, onOpenSheet, onRender,
  graphExtraEdges(acceptedIds, nodeById)`.
- CONFIRM the cascade at `reviewCascade:5910` reads `descriptor.fallbackParentId`
  and reparents an orphan to it ONLY when the fallback is itself accepted and is
  not the node's self. The synthetic anchor (Q1) must therefore be present in
  `nodes` AND accepted, or the reparent short-circuits to null. Verify this and
  build the anchor node accordingly.
- Type-picker affordance to reuse in the manifest editor:
  `_authorLocationTypeOptionLabel:8409`, `_authorOpenTemplateModalFor:8420`,
  `_authorPromptLocationTypeClassification:8430`,
  `_authorClassifyLocationType:8465`; catalog cache `authorLocationTypeCatalog`
  (loaded from `/api/location-types`, `:6662`). Reuse for adding a classified
  type from the manifest editor.
- `page_contract.py` covers the CREATION_TABS registry loader NAMES -- if this
  step adds a sub-tab or a registered loader, keep the name stable and update the
  check's expectations only as the check itself allows.
- `graphAutoPlace:9388`, `NODE_R` constant -- used by `reviewGraphRender`; the
  batch graph reuses them unchanged.

## Scope IN

1. **"Generer un lot ici" button** in `renderLieuxBrowse`'s head block
   (`:6609`, inside `lieux-browse-head`). Enabled only when
   `lieuxBrowseParentId != null` (an anchor is selected); disabled with a
   title tooltip at root ("Descends dans un lieu pour l'utiliser comme ancre").
   On click: open the batch panel with `anchorId = lieuxBrowseParentId` and
   `anchorName` = last breadcrumb segment.

2. **Batch panel state** (module-level, mirroring the `region*` globals but
   prefixed `batch*`): `batchAnchorId`, `batchAnchorName`, `batchManifest`,
   `batchManifestNotes`, `batchManifestSkipped`, `batchDrafts`,
   `batchCoherence` (edges/unresolved/notes), `batchAccepted`,
   `batchConfirmedEdges`, `batchGraphOpen`, `batchCommitResult`. Do NOT reuse the
   `region*` globals -- a batch and a region can never be live at once, but
   separate state keeps the two consumers independent (the S-norme reason 0041
   existed).

3. **Phase A -- count + generate.** A count input (min 3, max 25, default e.g.
   8) and a "Generer le manifeste" button that calls
   `POST /api/room-batch/manifest` (BRIEF-0042-a) with `{anchor_id, count}` and
   stores the result. Render the manifest as an editable table: per row, a name
   input, a one-liner input, a `location_type` datalist (backed by
   `authorLocationTypeCatalog`, labels via `_authorLocationTypeOptionLabel`, with
   a "Gabarit..." button reusing `_authorOpenTemplateModalFor` to add/classify a
   type), and a `parent_room` select whose options are (the anchor name | every
   OTHER manifest room name). Add-row / remove-row controls (S: the creator
   reaches the requested count by editing here). Manifest notes + skipped
   rendered read-only.

4. **Phase B trigger.** A "Generer les fiches" button that posts the edited
   manifest to `POST /api/room-batch/draft` (BRIEF-0042-b) and stores
   `batchDrafts`. Then **Phase C trigger** -- a "Passe de coherence" button that
   posts to `POST /api/room-batch/coherence` (BRIEF-0042-c) and stores
   `batchCoherence`. (Both server routes are thin wrappers over the BRIEF-a/b/c
   functions; if BRIEF-0042-e has not yet added a route module, add these read
   routes there and note the dependency -- REPORT if the route module is absent.)

5. **`batchReviewDescriptor()`** -- the 0041 adapter. Build `nodes` as:
   - ONE synthetic anchor node FIRST: `{id: batchAnchorId, name: batchAnchorName,
     subtitle: '(ancre)', parentId: null, description: '', notes: [], extras: '',
     __anchor: true}`.
   - One node per Phase B room: `{id: local_id, name, subtitle: location_type,
     parentId: (parent_room resolved to a room local_id, else batchAnchorId),
     description, notes, extras: ''}`. A room whose `parent_room` named a now-
     skipped room resolves to `batchAnchorId` here (belt-and-braces with the
     cascade).
   - `accepted`: `batchAccepted`, but the synthetic anchor is ALWAYS accepted --
     seed `batchAccepted[batchAnchorId] = true` and make `onToggleAccept` a no-op
     for the anchor id (Q1: non-toggleable).
   - `fallbackParentId: batchAnchorId`; `reparentedLabel: 'rattache a l'ancre'`.
   - `graphSvgId: 'batch-lieux-graph-svg'`; `graphOpen: batchGraphOpen`.
   - `onToggleAccept(id)`: if `id === batchAnchorId` return (no-op); else flip
     `batchAccepted[id]`. `onToggleGraph`, `onOpenSheet(id)` (open the room's
     Phase B sheet; the anchor id opens the anchor's canon sheet read-only or
     no-op), `onRender: batchRenderAll`.
   - `graphExtraEdges(acceptedIds, nodeById)`: from `batchCoherence.edges`, emit
     `{id, entity_a_id, entity_b_id, kind:'connection'}` for each edge whose BOTH
     endpoints are accepted AND confirmed (`batchConfirmedEdges[edge.id]`),
     mapping to `local_id`/anchor/sibling ids. Default UNCONFIRMED (opt-in,
     mirroring region's link toggles) -- render a confirm/discard toggle per
     supplementary edge in a side panel.

6. **Render `reviewNode` anchor specialness.** In the DESCRIPTOR (not the shared
   component), give the anchor node an `extras`/subtitle that reads as the root
   and rely on `onToggleAccept` no-op for non-editability. Do NOT modify
   `reviewNode`/`reviewTree`/`reviewGraphRender` in the shared component -- Q1 is
   achievable entirely from the descriptor (anchor is a normal always-accepted
   root node). If a visual "distinct root" beyond the subtitle is wanted, add it
   in the batch's own graph-panel CSS, not the shared render. REPORT if the
   shared component turns out to need a change (that would be a scope escalation
   to discuss, not a silent edit).

7. **Commit button** -- "Commiter le lot", posts to
   `POST /api/room-batch/commit` (BRIEF-0042-e) with the accepted rooms, the
   confirmed edges, and the anchor id; renders `batchCommitResult` (committed
   count, unresolved notes, door count, any T1 anchor-bounds note).

## Scope OUT
- The atomic commit route itself (BRIEF-0042-e). This step CALLS it.
- Any change to the shared `review*` component (TICKET-0041 surface). The anchor-
  as-root is descriptor-only (Q1). A shared-component change is out of scope and
  must be reported, not made.
- O2 (bounds-scaled rectangle nodes). Graph nodes stay circles via
  `reviewGraphRender`.
- Reusing the `region*` globals or the region panel markup. Separate state.
- Editing fiche descriptions in the review (the sheet is read + accept/reject +
  edge-confirm; content editing is not in scope).
- Persisting draft/manifest server-side. Everything is client-held until commit.

## Invariants to defend
- **json_ui_boundary** (the named allow-list check): new client-facing routes /
  payloads must stay within the boundary the check enforces. Confirm the batch
  routes' shapes pass it.
- **page_contract** (CREATION_TABS loader names): if a loader is registered, its
  name is covered -- keep it stable.
- **S-norme (no duplication).** The type-picker, the graph render, and the review
  tree are REUSED (0040 affordance, 0041 component), not re-implemented. Any
  copy-paste of `region*` logic is a C2 violation -- extend/reuse instead.
- **Structural exclusion.** The anchor sheet opened in review is a canon read; do
  not surface hidden subculture in the batch UI.

## Done means
- [ ] Descended into an anchor, "Generer un lot ici" is enabled; at root it is
      disabled with the tooltip.
- [ ] Generating a manifest renders an editable table; changing a type via the
      datalist and adding a new classified type both work (reused affordance).
- [ ] Adding rows to reach a higher count, then generating fiches, produces one
      sheet per row.
- [ ] The review tree shows the anchor as a non-toggleable root with every room
      beneath it (directly or transitively); rejecting an internal room
      reparents its children under the anchor with the badge.
- [ ] Toggling the graph shows the spanning tree solid and confirmed
      supplementary edges dashed; the anchor is the visually distinct root.
- [ ] A supplementary edge is unconfirmed by default and only appears in the
      graph once confirmed.
- [ ] `/review-step` and `/close-step` run.

## Docs to update
- CLAUDE.md: register the batch panel + `batchReviewDescriptor` and the new
  routes in the File structure / tab sections (pointer-fresh).
- No schema change.
