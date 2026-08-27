# BRIEF — Step "Review Queue"

Ticket: TICKET-0059. Requires BRIEF-0059-j landed. Reads
SUPPLEMENT-0059-recon-amendments **Amendment 4**. Cites RECON-0059-a **M5**,
**M7**.

**Anchor convention.** Every line number below is indicative, read from a
tarball of `main` this session. Your working tree is ahead of it. **Locate by
function name; verify every line locally before acting on it.**

## Context

The Review Queue is the creator's approval surface for AI-proposed mutations —
the human half of "model proposes, code judges." It is the last standalone
Creation tab still legacy: `archetype: 'bespoke'`, `loader: loadQueue`,
container `#creation-queue`, plus a `filters` slot whose loader is
`loadTickControls` and which renders into `#creation-shell-extra`.

Two RECON corrections govern this brief.

**Amendment 4 refuted the interleaving claim.** `Active project.md` A2 asserted
the queue cluster was wedged inside Play scene code. RECON-0059-a M5 measured
it: it is not. The `_renderScene` / `_renderTargetSelector` /
`_renderJoinCandidates` / `_renderTravelCandidates` / `_renderSceneState`
functions in that line region are Play, and the queue functions sit after them
as a contiguous cluster. There is no function-body interleaving to unpick.
Confirm this in your own tree before porting; if you find a queue function
called from Play, STOP.

**The Queue does not consume the governed review component, and must not
start.** `loadQueue` renders flat cards — `mutations.map(renderCard)`.
`reviewRegister` / `reviewCascade` / `Review.svelte` govern *hierarchical
proposal cascades*, and their only two consumers are `Region.svelte` and
`RoomBatch.svelte`. `review_component.py`'s permitted-importer list must come
out of this brief **unchanged**. If the port starts to look like it wants a
cascade, that is a design question for another ticket, not an edit here.

A caller-census caveat, standing since the `observationOpenPrompt` escalation:
**run your census across all three surfaces**, Play and Observation included.
RECON-0059-a M5's "no cross-read" claim was a two-surface search and has
already been shown incomplete once.

## Scope IN

### Commit 1 — filters slot and mutation name caches

1. **`frontend/src/creation/QueueFilters.svelte`** — port `loadTickControls`
   and whatever `currentFilter` state it drives. The slot descriptor's
   `loader` becomes `null`; register the component as an island on
   `#creation-shell-extra`.

   `currentFilter` is read by `loadQueue` (the `approved` / `proposed` /
   other branches). Since the filters and the queue body are two separate
   containers, the filter value crosses between them: put it in a module-level
   rune store (`frontend/src/creation/queue.svelte.js`), not in either
   component, and have both read it. One authority for one fact.

2. Port `_loadMutationEntityNames`, `_mutationEntityName`,
   `_loadMutationAgendaNames`, `_mutationAgendaName` into
   `queue.svelte.js`. These are name-resolution caches loaded in parallel
   before the queue renders (`Promise.all` in `loadQueue`). Preserve that:
   both caches resolve before any card renders, or cards show ids instead of
   names.

### Commit 2 — queue body and cards

3. **`frontend/src/creation/Queue.svelte`** — port `loadQueue`, `renderCard`
   and every card-rendering helper it reaches, including
   `_renderResourceChangeLegs` and `_renderAgendaProvenanceSummary`. Locate
   `renderCard` by name and follow its call graph; do not assume the helper
   list above is complete.

   Preserve verbatim, because they are the surface's meaning and not
   decoration:

   - the healthy-empty state for the `approved` filter — the green
     `✓ Empty — no apply errors or duplicate blocks.` block with its second
     line `This is the normal, healthy state.` An empty "Needs attention"
     queue is the *good* outcome and must not render as a generic "no
     results" message.
   - the generic empty state for every other filter,
     `No "<filter>" proposals.`
   - the error branch rendering the server message in red inside the body.

4. Port `showResult`, `lockCard`, `unlockCard`, `markCardDone`. Despite their
   generic names, M5 confirmed all four are queue-private by caller trace.
   **Re-confirm that trace in your tree** before deleting them — a
   generically-named global is exactly the kind of thing another surface
   reaches for.

### Commit 3 — batch bar and verdict

5. Port `renderBatchBar`, `toggleSelectAll`, `updateBatchBar`,
   `doBatchAction`, `showBatchVerdict` and the batch-selection state.
   Locate them by name; the batch cluster's membership is defined by what
   `renderBatchBar`'s markup calls, not by a prefix.

   The batch bar renders into `#creation-shell-batch-bar` — a *third*
   container, distinct from both the queue body and the filters slot
   (BRIEF-0005-c relocated it there). Preserve that placement. It shows only
   when `currentFilter === 'proposed'`; preserve that condition.

6. **Registry.** `loader: null`, `state.onWorldSwitch: null`, keep
   `primaryAction: null` with its comment
   (`append-only by design — rows never created here`). Declare the islands
   this brief mounts — the queue body, the filters slot, and the batch bar if
   it is a separate mount point rather than part of one component's subtree.
   Reduce `#creation-queue`'s markup to an empty container with a comment
   matching `#creation-region`'s.

### Every commit

7. **Delete each ported function from `index.html`** in the commit that
   replaces it. Extend `retiredPrefixes` **by name** — `loadQueue`,
   `renderCard`, `showResult`, `lockCard`, `unlockCard`, `markCardDone`,
   `toggleSelectAll`, `doBatchAction` and the `_render*` / `_mutation*` /
   `_loadMutation*` helpers share no usable prefix. Add a `BRIEF-0059-k`
   comment. Extend `graph_primitive.py`'s `GONE_PLAIN`.

8. **Prune `legacy_calls.baseline`** of anything closed; add nothing.
   Expected net: 0.

## Scope OUT

- **World CRUD.** Amendment 4 moved `world*`, `loadWorldSelector` and
  `activateWorld` to `-l`, where they land with the chrome and
  `Modal.svelte`.
- **The chrome.** All `creation*` navigation helpers stay. `-l`.
- **Making the Queue consume `reviewRegister`.** See Context.
  `review_component.py`'s allow-list must not grow.
- **Changing what the approve/reject endpoints do**, or batching two calls
  into one. `doBatchAction` iterates today; if it iterates, it keeps
  iterating.
- **Adding a confirmation to batch reject.** It has none today. Adding one is
  a UX decision, not a migration.
- **Touching Play's `_renderScene` family.** Adjacent in the file, unrelated
  in ownership.
- **`observation_surface.py` and anything `observation*`.** TICKET-0060.
- **Any backend change.** Frontend-only.

## Invariants to defend

- **Model proposes, code judges.** This surface *is* that invariant's user
  interface. Every approve, reject and batch action stays on its existing
  `/api/mutations/...` route. Nothing here may apply a mutation directly, and
  no client-side path may mark a proposal applied without the server saying
  so.
- **History is sacred.** The queue is append-only by design — `primaryAction`
  is `null` for that reason. The port adds no create path and no delete path.
- **Exclusion is structural.** Whatever the queue does not show, it does not
  show because the endpoint filtered it (`?status=`). Do not add a
  client-side filter, and do not fetch a wider set and narrow it in the
  component.
- **The healthy-empty state stays distinct.** Item 3. Collapsing it into a
  generic empty message would make a good state look like a null result.
- **Assign-then-read is forbidden** (`effect_self_write.py`). The card list,
  the selected-ids set and the batch counts are `$derived`.
- **The seam only shrinks.**

## Done means

- [ ] `legacy_call.py`, `creation_island.py`, `page_contract.py`,
      `effect_self_write.py` exit 0 after every commit.
- [ ] `python tooling/verify/checks/review_component.py` exits 0 with its
      permitted-importer list **byte-unchanged**.
- [ ] The commit message for commit 2 records the three-surface caller census
      for `showResult`, `lockCard`, `unlockCard`, `markCardDone` and the
      queue cluster as a whole.
- [ ] `grep -c "loadQueue\|renderBatchBar\|showBatchVerdict\|loadTickControls\|doBatchAction" src/world_engine/cockpit/index.html`
      returns 0.
- [ ] `#creation-queue` is an empty div with an explanatory comment.
- [ ] Live: open the Review Queue with proposals pending; cards render with
      entity and agenda **names**, not ids.
- [ ] Live: approve one proposal and reject another; both leave the list and
      the world reflects the approved one.
- [ ] Live: switch the filter to "Needs attention" with nothing pending; the
      green healthy-empty block renders, not a generic empty message.
- [ ] Live: switch to another filter with nothing pending; the generic empty
      message renders.
- [ ] Live: on the `proposed` filter the batch bar appears in the shell band;
      on every other filter it does not.
- [ ] Live: select all, then none; the count updates; batch-approve two
      proposals; the verdict panel shows the result.
- [ ] Live: a resource_change proposal shows its money and knowledge legs; an
      agenda-linked proposal shows its provenance summary.
- [ ] Live: trigger a server error on an approve (e.g. approve a proposal
      already applied in another tab); the error renders in red without
      blanking the queue.
- [ ] Live: switch worlds; the queue reloads for the new world with no stale
      card.
- [ ] Live: Play's scene rendering is unaffected — open Play and run a scene.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `python tooling/verify/run.py` exits 0.
- [ ] `module_budget.py` and `function_length.py` pass on every file written.
- [ ] `/review-step` and `/close-step` run per commit.

## Docs to update

None. Brief `-m`, which also corrects `Active project.md` A2's interleaving
claim.
