# BRIEF — Step "Review Queue + pre-commit review component"

Ticket: TICKET-0058. Requires BRIEF-0058-d landed.

## Context

The review component is already a governed generic: `reviewRegister(key,
descriptor)` (`index.html:6151`), a pure `reviewCascade` (`6155`), and a
fail-closed check `review_component.py` that forbids a second
implementation. TICKET-0057 cited it as the precedent the graph primitive
was modelled on. Migrating it is therefore not a redesign - it is moving a
component that already has the right shape, and keeping its check biting.

Its descriptors carry the `graph: { ... }` specs at `index.html:6310` and
`7025` that feed the `review` graph consumer
(`frontend/src/graph/consumers/review.js`), and the preview data crosses the
seam through `reviewGraphData` (`index.html:6236`,
`frontend/src/legacy/bridge.js:122`). When the component becomes a Svelte
island, that bridge hop becomes unnecessary: the draft state and the graph
consumer end up on the same side.

## Scope IN

1. **`frontend/src/creation/Review.svelte` + `review/registry.js`.** Port
   the component, its registry and the cascade. `reviewCascade` stays PURE -
   it takes state and returns state; it performs no DOM work and no fetch.
   That purity is what `review_component.py` asserts and it must survive
   the move intact.

2. **Descriptors move with their surfaces.** The Review Queue tab's own
   descriptor moves here. Region's and the room batch's descriptors move in
   brief -j; until then they keep registering through the legacy path, which
   means `reviewRegister` must be reachable from both sides for one brief.
   State that explicitly, and name brief -j as where it ends.

3. **The `graph` spec keeps its closed vocabulary.** `graph_primitive.py`
   rule 9 collects every `graph: { ... }` spec and permits only
   `consumer` / `mountId` / `extraEdges`. When a descriptor moves into
   Svelte, rule 9's collection locus moves with it - amend the rule to
   collect from both `index.html` and `frontend/src/creation/`, with zero
   collected across both still a failure.

4. **`reviewGraphData` and the bridge hop.** Once a descriptor's draft state
   lives in Svelte, its preview data no longer crosses the frame boundary.
   Remove the `reviewGraphData` export from `legacy/bridge.js` ONLY when no
   legacy descriptor remains - i.e. in brief -j, not here. If any remains,
   the export stays and the consumer keeps both paths, with a comment naming
   the brief that closes it.

5. **Re-home `review_component.py` and `review_root_fallback.py`** in this
   commit, onto the new locus, guarantees unchanged, zero-collected a
   failure.

6. **Batch review of mutations.** The batch/mutation review cluster the
   workstream map located wedged inside the Play scene code (Active project,
   A2) is a Creation concern. Move only the part the Review Queue tab
   renders. Anything reachable only from Play is REPORT ONLY: list it, do
   not move it.

## Scope OUT

- **Changing cascade semantics.** Not one rule about what approving a parent
  does to its children.
- **Region and room-batch descriptors.** Brief -j.
- **`room_batch_report_only.py`'s guarantee** - the room batch stays
  report-only; nothing here gives it a write path.
- **Touching `_apply_mutation` or any mutation gating.** Backend, and out of
  scope by cross-cutting rule 2.
- **Play-side code.** Play is a legacy mount until its own ticket.

## Invariants to defend

- **`proposed_mutation` is the sole gate to canon for AI-proposed changes.**
- **Model proposes, code judges** - the queue approves; it does not author.
- **History is sacred** - approval is append-only; no silent delete.
- **One review component, structurally** - a second implementation must stay
  unconstructible across the move.

## Done means

- [ ] `python tooling/verify/checks/review_component.py` and
      `review_root_fallback.py` exit 0 at the new locus, and both are proven
      to still bite on a scratch mutation.
- [ ] `python tooling/verify/checks/graph_primitive.py` exits 0, rule 9
      collecting specs from both loci.
- [ ] `python tooling/verify/checks/room_batch_report_only.py` exits 0.
- [ ] Live: open the Review Queue, expand a batch, approve a parent and
      confirm the cascade behaves exactly as before, reject a child, commit
      the batch, and confirm the result in the world.
- [ ] Live: the pre-commit graph preview still renders for region generation
      and for the room batch generator.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

None. Brief -l.
