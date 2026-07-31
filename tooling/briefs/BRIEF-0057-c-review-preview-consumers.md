# BRIEF — Step "review pre-commit preview: second and third consumers"

## Context

The primitive now has one consumer. One consumer proves nothing: it is the
second and third that test whether the contract's shape is right rather
than merely sufficient for the case it was extracted from. This step
converges the review pre-commit preview - the second SVG implementation
found during RECON and absent from the original workstream map - which
carries TWO consumers at once, region generation and the room batch
generator.

The duplication being removed is measured: `reviewGraphRender`
(`index.html:6249-6273`) already calls `graphAutoPlace` from the Lieux
implementation (`index.html:6254`) and then re-emits its own SVG. Placement
was already shared; only rendering had diverged. After this step, nothing
is duplicated and nothing is dormant.

## Scope IN

1. **Carry forward brief -b's sequencing constraint.** If BRIEF-0057-b
   landed with `NODE_R` and `graphAutoPlace` still present behind a
   `// TICKET-0057: removed by BRIEF-0057-c` marker, remove them here.
   `index.html` must contain neither after this step. Neither commit is
   offered for verify alone; -b and -c are pushed together.

2. **The declaration seam (locked decision D2), review side.** The review
   descriptor contract (documented at `index.html:6130-6145`) drops
   `graphSvgId` and `graphExtraEdges` and gains a single `graph` spec.
   Update the contract comment verbatim to:

   ```
    *   graphOpen         bool, graph pane currently open
    *   graph             { consumer, mountId, extraEdges(acceptedIds, nodeById) }
    *                     -- the graph primitive's declaration site for this
    *                     descriptor (TICKET-0057). `mountId` is the id of a
    *                     STABLE empty div the consumer re-emits on every
    *                     render; the shell mounts the primitive into it.
    *                     No descriptor names a drawing surface any more:
    *                     the review component does not know how a graph is
    *                     drawn.

   Do NOT write the literal token `<`+`svg` anywhere in this comment or
   elsewhere in index.html: BRIEF-0057-d's lock rule 2 asserts that token
   is absent from the file entirely, comments included.
   ```

   `region` (`index.html:6326-6355`) and `batch` (`index.html:7030-7043`)
   descriptors are updated accordingly: `graphSvgId: '...'` and
   `graphExtraEdges: (...) => ...` become
   `graph: { consumer: 'review', mountId: 'region-graph-mount', extraEdges: (...) => ... }`
   and `... mountId: 'batch-graph-mount' ...`. The extraEdges bodies are
   moved verbatim, not rewritten.

3. **`reviewGraphData` STAYS.** It is the descriptor -> `{nodes, edges}`
   adapter (`index.html:6231-6247`): cascade-aware node filtering,
   hierarchy edge derivation, plus the consumer's `extraEdges`. That is
   review-component logic, not graph-rendering logic, and it belongs on the
   consumer side of the seam - the primitive receives data, it does not
   derive it. Only its call to `d.graphExtraEdges(...)` becomes
   `d.graph.extraEdges(...)`.

4. **`reviewGraphRender` is DELETED** (`index.html:6249-6273`). Its two
   call sites, `index.html:6699` (`regionRenderAll`) and `index.html:7158`
   (`batchRenderAll`), are replaced by a dispatch on the legacy document,
   using the same event vocabulary brief -b established:

   ```js
   if (regionLocGraphOpen) {
     document.dispatchEvent(new CustomEvent('graph:slot', {
       detail: { consumer: 'review', containerId: 'region-graph-mount', open: true, key: 'region' },
     }));
   }
   ```
   and the batch equivalent with `'batch-graph-mount'` / `key: 'batch'`.

   `reviewToggleGraph` (`index.html:6225-6229`) is UNCHANGED: it flips the
   descriptor's open state and calls `onRender`, and the render is what
   dispatches. One signal path, not two.

5. **Stable mount containers.** `index.html:6681-6684` and `7140-7143`
   currently emit a `<div>` wrapping an `<svg>`. Each becomes a wrapper
   holding a bare, empty mount div:

   ```html
   <div id="region-lieux-graph" style="display:${regionLocGraphOpen ? 'block' : 'none'}; margin-top:8px;">
     <div class="lieux-graph-head"><span>Carte des lieux (aperçu pré-commit)</span></div>
     <div id="region-graph-mount"></div>
   </div>
   ```

   and the batch equivalent, preserving its existing head text
   `Carte du lot (aperçu pré-commit)`.

   Because these panels re-emit their markup on every render, the mount
   node's identity does not survive (BRIEF-0057-a M8). `mountGraph` was
   built in brief -b to detect exactly that and re-mount; verify here that
   it does, and that the previous instance is torn down rather than
   orphaned. If M8 reported the node identity DOES survive, `mountGraph`
   must no-op on the second dispatch instead - implement whichever branch
   M8's verdict supports, and say which in the delivery note.

6. **New `frontend/src/graph/consumers/review.js`.** Unlike the Lieux
   consumer, this one FETCHES NOTHING - the data is derived in the legacy
   document from in-memory drafts. It reads its `{nodes, edges}` by calling
   `reviewGraphData(key)` on the legacy window through `bridge.js`, sets
   `dashedKinds: ['connection']` (preserving the dashed styling at
   `index.html:6259`), and supplies NO callbacks - the pre-commit preview
   is read-only: no drag, no connect, no edge deletion. This is the
   consumer that proves the callback-presence contract: three props left
   null, three interactions structurally off.

   `bridge.js` gains no new token; the existing `callLegacy` mechanism
   (`bridge.js:24-31`) is what reaches `reviewGraphData`.

7. **`review_component.py` amendment** (`tooling/verify/checks/review_component.py`).
   Written against BRIEF-0057-a M5's recorded output:
   - `reviewGraphRender` is removed from `GENERICS` (`:38-41`) and added to
     a new `RETIRED` list asserted absent from `index.html`, in the same
     shape as the existing `GONE` rule (`:85-89`), with a comment naming
     TICKET-0057 and the reason (the review component no longer knows how a
     graph is drawn).
   - `GENERICS` keeps `reviewToggleGraph` and `reviewGraphData`; both are
     still single-defined and still region-blind.
   - If M5 reported rule 6 also fires because a new name references a
     `review*` symbol, add that name to `CONSUMER_ALLOW_LIST` (`:42-50`)
     with a comment, exactly as TICKET-0042 did for the room batch. Do not
     relax the rule itself.
   - Update the PASS message's count wording so it stays truthful.
   Everything else in that file: REPORT ONLY.

8. **Build.** Regenerate and commit `src/world_engine/cockpit/static/` per
   BRIEF-0057-a M6.

## Scope OUT

- **The relation / cytoscape graph.** Still TICKET-0058. Untouched.
- **The lock check.** Brief -d. `graph_primitive.py` and
  `graph_impls.baseline` are not created here, not even partially.
- **`relation_graph.py` clause 5.** Still expected red on this branch.
  Do not touch it. Brief -d replaces it.
- **`reviewCascade`, `reviewNode`, `reviewTree`, `reviewOpenSheet`,
  `reviewNotes`, `reviewIsAccepted`, `reviewToggleAccept`,
  `reviewRegister`, `reviewDescriptor`.** The accept/reject component is
  not being refactored. Only the graph slot moves.
- **Making the pre-commit preview editable.** It is read-only by design
  (nothing is committed yet, the nodes have no entity ids). Do not supply
  `onConnect`/`onDeleteEdge`/`onMoveNode` "for symmetry".
- **Adding a third review consumer, or generalising the descriptor further.**
- **The region factions panel, the link toggles, `regionRenderLinkToggles`,
  `_sheetEntityOptions`.** Out of scope even though they sit adjacent.
- **`traits.py` / `graph_spec_for`.** Locked deferral D1.
- **Any backend, schema or `crud/` change.** Frontend only.

## Invariants to defend

- **The review component stays region-blind** (`review_component.py`
  rule 3). No `region` / `REGION_` token may enter any `review*` body. The
  new `graph` spec is supplied BY the descriptor, so the component reads
  `d.graph.*` and never names a consumer.
- **`reviewCascade` stays pure** (rule 4): no DOM, no registry access, one
  parameter, `fallbackParentId` honoured. This step must not drag any
  mounting concern into it.
- **The boundary holds in both directions** (rule 6). If new glue needs to
  name a `review*` symbol, it is added to the allow-list explicitly - never
  by weakening the matcher.
- **No structure without a reader (E2).** `dashedKinds` is now set by a
  real consumer; `mountId` is read by real code. Any contract key still set
  by nobody after this step must be deleted, not kept "for later".
- **Zero dormant code.** After this step `index.html` contains no
  graph-rendering code at all except the baselined `relGraph*` set.

## Done means

- [ ] `grep -c 'reviewGraphRender\|graphSvgId\|graphExtraEdges\|graphAutoPlace\|NODE_R' src/world_engine/cockpit/index.html`
      returns `0`.
- [ ] `grep -n 'reviewGraphData' src/world_engine/cockpit/index.html` shows
      the function still defined exactly once, plus its call from
      `frontend/src/graph/consumers/review.js` via the bridge.
- [ ] `grep -c '<svg' src/world_engine/cockpit/index.html` returns `0`.
- [ ] `frontend/src/graph/consumers/review.js` exists and contains no
      `fetch(`.
- [ ] `python tooling/verify/checks/review_component.py` -> PASS.
- [ ] `python tooling/verify/checks/page_contract.py` -> PASS.
- [ ] `python tooling/verify/checks/legacy_mount.py` -> PASS.
- [ ] `python tooling/verify/checks/frontend_build_fresh.py` -> PASS.
- [ ] `python tooling/verify/checks/relation_graph.py` -> still FAIL on
      clause 5 only.
- [ ] Live: Creation > Region generation, generate a draft, "Voir le graphe
      des lieux" -> the preview renders; hierarchy edges solid; a confirmed
      connection link renders DASHED.
- [ ] Live: toggle a node from accepted to rejected -> the preview updates
      and the rejected node's children re-attach per the cascade fallback.
- [ ] Live: toggle the graph closed then open again three times -> exactly
      one canvas, no orphaned instance, no console error.
- [ ] Live: room batch panel > "Voir le graphe" -> the preview renders
      against the synthetic anchor; the anchor is present and
      non-toggleable.
- [ ] Live: in both previews, dragging a node does nothing and clicking an
      edge does nothing (read-only by construction, not by disabled UI).
- [ ] Live: commit a region -> the Lieux graph refreshes (brief -b's path
      still works after this step).
- [ ] `/review-step` and `/close-step` run.

## Docs to update

None in this step - brief -e. Note for -e: CLAUDE.md:59's sentence listing
the twelve review generics becomes inaccurate the moment
`reviewGraphRender` is retired. That correction is -e's, and it must not be
forgotten; it is listed in -e Scope IN 1.
