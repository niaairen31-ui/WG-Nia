# BRIEF — Step "link agent island"

Ticket: TICKET-0059. Requires BRIEF-0059-f landed. Reads
SUPPLEMENT-0059-recon-amendments **Amendment 1**. Cites RECON-0059-a **M4**,
**M5**, **M7**.

## Context

`-f` extracted `LocationTree.svelte` and proved it on the NPC agent, whose
picker is a single-select radio over one selected root. This brief ports the
link agent — 27 functions at `index.html:7217-7615` — whose picker is a
multi-select checkbox over a `Set`, with ancestor inheritance
(`_linkAgentIsChecked`, 7283: a node renders checked when it is in the set
**or** any ancestor is).

That difference is the whole reason RECON-0059-a M4 fired this ticket's Stop
rule. Amendment 1's answer was that the difference lives at the row, not in
the traversal. **This brief is where that answer is tested.** If
`LocationTree.svelte` needs a single new prop, a `mode` flag, or an `{#if}` to
accommodate the second consumer, the seam was drawn in the wrong place and
that is a finding worth reporting loudly, not a small edit to slip in.

The link agent also carries a coherence pass the NPC agent has no equivalent
of: `linkAgentRunCoherence` (7569), `_linkAgentFindingHtml` (7553),
`linkAgentApplyFinding` (7583). It is genuinely link-specific and does not
generalise.

## Scope IN

### Commit 1 — the launcher

1. **`frontend/src/creation/LinkAgent.svelte`** plus
   **`frontend/src/creation/linkAgent.svelte.js`** for non-render logic.
   Commit 1 ports `linkAgentReset` (7217), `linkAgentCheckOpenBatch` (7238),
   `linkAgentRenderLauncher` (7264), `_linkAgentIsChecked` (7283),
   `_linkAgentTreeHtml` (7294), `linkAgentToggleLocation` (7308),
   `_linkAgentPaintLauncher` (7315), `linkAgentPreviewRoster` (7334),
   `linkAgentLaunch` (7351).

2. **Consume `LocationTree.svelte` with a checkbox snippet.**
   `_linkAgentTreeHtml` is deleted, not ported. The snippet renders only the
   `<input type="checkbox">`, with `checked` computed by the ported
   `isCheckedLocation(id)` — the ancestor-walking predicate from 7283, moved
   into `linkAgent.svelte.js` unchanged in behaviour.

   **The checked set stays a `Set`.** `linkAgentCheckedRoots` is a `Set`
   today and the ancestor walk depends on `.has()`. In Svelte 5, a `$state`
   `Set` is reactive but mutation must be visible: prefer reassignment
   (`checkedRoots = new Set(checkedRoots)` after add/delete) or
   `SvelteSet`. Whichever is chosen, verify live that toggling a parent
   immediately repaints its descendants — the ancestor predicate means a
   single toggle changes the rendered state of an arbitrary number of rows,
   and this is precisely where a missed reactivity edge would show up.

3. **`LocationTree.svelte` must not change.** If it does, STOP and report
   before continuing: state exactly which prop or branch the second consumer
   required and why the row snippet could not carry it. Amendment 1's whole
   claim is that it will not need to.

   The one legitimate exception: if the tree currently hardcodes something
   the NPC agent happened not to exercise (for example a `name` attribute
   that only radios need), removing that hardcode is a correction, not an
   accommodation. Say which of the two it is in the commit message.

### Commit 2 — run loop, review, coherence

4. Port the remainder: `linkAgentRunLoop` (7375), `linkAgentPause` (7400),
   `linkAgentRetry` (7405), `linkAgentLoadBatch` (7412), `_linkAgentNpcName`
   (7440), `_linkAgentGroupRows` (7442), `_linkAgentRelationRowHtml` (7456),
   `_linkAgentKnowledgeRowHtml` (7478), `_linkAgentNoLinksRowHtml` (7502),
   `_linkAgentPairGroupHtml` (7510), `linkAgentEditField` (7523),
   `linkAgentToggleReject` (7537), `_linkAgentFindingHtml` (7553),
   `linkAgentRunCoherence` (7569), `linkAgentApplyFinding` (7583),
   `linkAgentCommit` (7599), `_linkAgentPaintReview` (7615).

   The run loop's termination protocol is preserved exactly as written: it
   reads `result.done` and updates `linkAgentBatch.pairs_done` per iteration.
   Do not align it with the NPC agent's error-string protocol, and do not
   align the NPC agent's with this one. `-f` recorded that divergence as a
   backend-contract difference and a named deferral; it stays deferred.

### Both commits

5. **Register the island.** Add `linkAgent` to `CREATION_ISLANDS`
   (`registry.js`) and to `COMPONENTS` in `mount.js`. Add
   `{ key: 'linkAgent', containerId: 'linkagent-panel' }` to the npc tab's
   `islands` list in `CREATION_TABS`. `loader: null`, `onWorldSwitch: null`;
   world-state reset driven by `serverState.worldId`.

6. **The toggle button and badge stay legacy.** `linkAgentToggle` (7252) and
   the `#linkagent-launcher-btn` / `#linkagent-badge` markup
   (`index.html:1304`) are chrome and retire at `-l`, the same line `-f` drew
   for the NPC agent. The badge is component -> legacy via a component-owned
   `CustomEvent` on `legacyDoc`, following `Constructeur.svelte`'s precedent;
   do not add a relay to `mount.js`.

7. **Finish the relgraph slot's `onOpen`.** `-f` reduced it to
   `() => { linkAgentCheckOpenBatch(); }`. That function is deleted here and
   the island performs the check on mount, so the handler's remaining body
   goes. If the slot descriptor then requires an `onOpen`, set it to `null`
   explicitly rather than leaving an empty arrow — an empty handler reads as
   an oversight to the next reader.

8. **Move the `.linkagent-*` CSS block** (`index.html:1000-1012`) into the
   Svelte components now that both consumers are Svelte. `linkagent-loc-node`
   and `linkagent-loc-children` go to `LocationTree.svelte`; the remaining
   classes (`linkagent-pair-group`, `linkagent-row`, `linkagent-row.rejected`,
   `linkagent-finding`, `linkagent-finding.finding-rejected`,
   `linkagent-warn-banner`, and the `.linkagent-row input[...]` rules) go to
   whichever component uses them — `NpcAgent.svelte` and `LinkAgent.svelte`
   both use `linkagent-row` and `linkagent-pair-group`, so those two belong
   in `LocationTree.svelte`'s sibling or in a shared stylesheet, not
   duplicated.

   **If duplication is the only option, do not duplicate — REPORT and stop
   at step 8**, leaving the CSS in `index.html` for `-l`. Two copies of a
   rule set that was explicitly authored as shared (`index.html:1000`
   documents the sharing) would be the exact failure this ticket keeps
   refusing.

   `#linkagent-badge, #npcagent-badge` (line 1001) stays in `index.html` —
   those elements are legacy chrome until `-l`.

9. **Delete every ported function from `index.html`** in the commit that
   replaces it; extend the new island entry's `retiredPrefixes` with every
   deleted identifier by name, including the ten underscore-prefixed helpers.
   Add a `BRIEF-0059-g` comment. Extend `graph_primitive.py`'s `GONE_PLAIN`.

10. **Prune `legacy_calls.baseline`** of anything closed; planning RECON
    expects none, and the commit message says so either way.

## Scope OUT

- **Changing `LocationTree.svelte`.** See item 3. Any change is a finding
  first and an edit second.
- **Converging the two run loops, the two review painters, or the two
  launchers.** The traversal was the shared thing; M4 established that, and
  `-f` established the backend-contract divergence in the loops. A shared
  `AgentPanel` base is not this ticket's design decision and would need its
  own decision block.
- **The coherence pass.** `linkAgentRunCoherence` / `_linkAgentFindingHtml` /
  `linkAgentApplyFinding` are link-specific. Port them as they are; do not
  generalise them into something the NPC agent could later consume.
- **The string-matched termination in the NPC agent.** Named deferral from
  `-f`. Not reopened here.
- **The governed review component.** `review_component.py`'s permitted-
  importer list must not grow. Confirm the link agent's painters are flat
  pair -> row groups, not the hierarchical cascade the component governs; if
  they are a cascade, STOP.
- **`link_agent_strata.py`.** Backend-only (`src/**/*.py`, `writes/`) per M7.
  No re-homing.
- **`npcAgentToggle` / `linkAgentToggle` and their buttons.** Chrome, `-l`.
- **Any backend change.** Frontend-only.

## Invariants to defend

- **One tree, structurally.** After this brief, `location_tree.py` guards two
  consumers with genuinely different interaction models over one traversal.
  That is the pass-2 guarantee: a third picker cannot appear without
  defeating a fail-closed check.
- **Model proposes, code judges.** Link generation writes into a batch;
  commit and reject stay on the existing `/api/link-batches/...` routes.
  Nothing here writes canon directly.
- **Assign-then-read is forbidden** (`effect_self_write.py`). The checked-set
  derivations — which rows render checked, the pair groupings — are
  `$derived`, never `$state` written inside an `$effect`.
- **Exclusion is structural.** Whatever the link agent's review surface hides
  today it hides by what the endpoint returns, not by a client-side filter.
  Do not add one.
- **Fail-closed guards never lapse.** `legacy_call.py`, `creation_island.py`,
  `graph_primitive.py`, `location_tree.py`, `effect_self_write.py` and
  `review_component.py` all pass after each commit.

## Done means

- [ ] `python tooling/verify/checks/location_tree.py` exits 0 with two
      consumers present.
- [ ] `git diff --stat` for both commits shows `LocationTree.svelte`
      **unchanged**, or the commit message states exactly what changed and
      why the row snippet could not carry it.
- [ ] `grep -c "linkAgent" src/world_engine/cockpit/index.html` returns only
      the counts attributable to `linkAgentToggle` and the button markup;
      enumerate the survivors in the commit message.
- [ ] `python tooling/verify/checks/creation_island.py` exits 0; scratch:
      re-add `function linkAgentLaunch(` and confirm rule 7 bites; revert.
- [ ] `python tooling/verify/checks/effect_self_write.py` exits 0.
- [ ] `python tooling/verify/checks/review_component.py` exits 0 with its
      permitted-importer list **unchanged**.
- [ ] Live: open the npc tab, click "Agent liens"; the tree renders
      identically to before, same indentation and dashed guides.
- [ ] Live: check a parent location; every descendant row immediately renders
      checked without a reload — the ancestor-inheritance predicate under
      Svelte reactivity.
- [ ] Live: uncheck it; descendants revert. Check two siblings; both hold.
- [ ] Live: Prévisualiser shows the NPC count, pair count and name list;
      Lancer is disabled until a preview exists, exactly as today.
- [ ] Live: launch a batch; pairs render grouped; edit a relation field and a
      knowledge field; reject a row and restore it; a pair with no links
      renders its own row.
- [ ] Live: pause mid-run and retry; the loop resumes and `pairs_done`
      advances.
- [ ] Live: run the coherence pass; findings render; apply one; the warn
      banner behaves as before.
- [ ] Live: commit the batch; the relations and knowledge appear on the NPC
      sheets. Open the relation graph and confirm the new edges are there.
- [ ] Live: the NPC agent (migrated in `-f`) still works end to end, and
      "Générer les liens" still hands off correctly now that both sides are
      Svelte.
- [ ] Live: both badges still appear when open batches exist; opening the
      relation graph no longer throws now that both `*CheckOpenBatch`
      functions are gone from the slot handler.
- [ ] Live: switch worlds; neither agent retains a stale batch.
- [ ] Live: visual diff of the tree, pair groups, rejected-row styling,
      findings and warn banner against `main` before this brief — the CSS
      move (item 8) must be invisible.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `python tooling/verify/run.py` exits 0.
- [ ] `module_budget.py` and `function_length.py` pass on every file written.
- [ ] `/review-step` and `/close-step` run per commit.

## Docs to update

None. Brief `-m`.
