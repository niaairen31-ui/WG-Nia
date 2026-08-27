# BRIEF — Step "LocationTree primitive + NPC agent island"

Ticket: TICKET-0059. Requires BRIEF-0059-e landed (see Precondition). Reads
SUPPLEMENT-0059-recon-amendments **Amendment 1**. Cites RECON-0059-a **M4**,
**M5**, **M7**.

## Precondition (verify before starting)

Planning RECON against `main` this session found BRIEF-0059-e's outputs
**absent**: `authorSelectEntity` (`index.html:6202`), `authorDelete` (6372),
`_authorNotifySaved` (6231), `_authorResetCreateDrafts` (5907),
`_authorGetPendingCreationMutationId` (6361), `authorGetSelectedEntityId`
(3236) and the `authorEntityId` global (3229) are all still present; there is
no `sheetState.svelte.js`; `registry.js` carries `BRIEF-0059-c` and `-d`
comments but no `-e`; and `legacy_calls.baseline` still holds the six records
`-e` was to prune.

This brief does not depend on `-e`'s outputs and can execute against either
state. But confirm at the top of execution whether `-e` landed. **If it did
not, say so in the commit message and do not silently absorb any part of its
scope.**

## Context

The npc tab hosts two AI agent panels toggled from the Creation chrome band:
`#npcagent-panel` (`index.html:1308`) and `#linkagent-panel` (1311), behind
buttons at 1303 and 1304. The NPC agent is 29 functions,
`index.html:6730-7146`.

RECON-0059-a M4 fired this ticket's Stop rule on the two panels' location
pickers, and Amendment 1 resolved it. Confirmed again this session at
`index.html:6798` and `7294`: the two traversals are byte-identical modulo the
locations variable read (`npcAgentLocations` / `linkAgentLocations`) and the
`<label>` contents. Both emit `<div class="linkagent-loc-node">` and
`<div class="linkagent-loc-children">`, and the stylesheet says so out loud at
`index.html:1000`: the npc agent "reuses every `.linkagent-*` class
wholesale."

What differs is the row control and its checked state — radio over a single
`npcAgentSelectedRoot` versus checkbox over a `Set` with ancestor inheritance
(`_linkAgentIsChecked`, 7283). That difference lives at the row, so the
component takes a snippet for the row control and owns everything above it.

## Scope IN

### Commit 1 — `LocationTree.svelte`

1. **`frontend/src/creation/LocationTree.svelte`.** Props: `locations` (the
   flat array) and a `row` snippet. The component owns, and the consumers no
   longer express:

   - the `known` id set, derived from `locations`;
   - root selection: `parentId == null` matches a location with no
     `parent_location_id` **or** whose parent is not in `known` — the orphan-
     root rule, preserved exactly;
   - `.sort((a, b) => a.name.localeCompare(b.name))`;
   - recursion into children;
   - the `linkagent-loc-node` / `linkagent-loc-children` wrapper divs and the
     `<label>` element and the location name text.

   The consumer's `row` snippet receives the location object and renders
   **only the `<input>`**. Everything around it belongs to the tree.

   **No `mode` prop, and no `isChecked` prop.** Amendment 1 specified an
   `isChecked(node)` predicate alongside the snippet; this brief narrows that
   — once the snippet renders the input, the input owns its own `checked`
   attribute and a separate predicate prop is a second expression of the same
   fact. State this narrowing in the component's header comment so the
   divergence from the Supplement is legible rather than looking like drift.

   The legacy `esc()` calls disappear: Svelte escapes text interpolation.

   Empty case: the legacy renderers return `''` from `_*TreeHtml(null)` and
   each caller substitutes its own empty message. The component keeps that
   shape — it renders nothing when there are no roots, and the consumer
   supplies the empty text. Do not move the empty message into the tree; the
   two agents word it differently.

2. **`tooling/verify/checks/location_tree.py`** — fail-closed, asserting
   exactly one recursive location-tree renderer exists under `frontend/src/`.
   The rule: no file other than `LocationTree.svelte` may contain both the
   token `linkagent-loc-node` and a self-recursive render. Vacuity guard on
   the **scan** (zero `.svelte` files collected, or `LocationTree.svelte`
   absent -> FAIL), following `effect_self_write.py`'s precedent from
   TICKET-0062 — zero findings is the goal state here, not a vacuous pass.

   The check ships in commit 1, before either consumer exists, and is
   therefore satisfied by one component and zero consumers. That is
   deliberate: it is the pass-2 lock, and it must be standing before `-g`
   ports the second agent.

### Commits 2-3 — the NPC agent island

3. **`frontend/src/creation/NpcAgent.svelte`** plus
   **`frontend/src/creation/npcAgent.svelte.js`** for non-render logic —
   a faithful port of all 29 functions at `index.html:6730-7146`. Split
   across two commits: **(2)** launcher — `npcAgentReset` (6730),
   `npcAgentCheckOpenBatch` (6754), `npcAgentRenderLauncher` (6780),
   `_npcAgentTreeHtml` (6798), `npcAgentSelectRoot` (6812),
   `npcAgentPreviewRoot` (6818), `npcAgentAddLine` (6830),
   `npcAgentRemoveLine` (6835), `npcAgentEditLine` (6840),
   `_npcAgentLineTotal` (6845), `_npcAgentLineRowHtml` (6849),
   `_npcAgentPaintLauncher` (6870), `npcAgentLaunch` (6899); **(3)** run loop
   and review — the remainder through `_npcAgentPaintReview` (7146).

4. **The launcher consumes `LocationTree.svelte`** with a radio snippet:
   `name="npcagent-root"`, `checked` when the location id equals the selected
   root, `onchange` setting it. `_npcAgentTreeHtml` is deleted, not ported.

5. **Register the island.** Add `npcAgent` to `CREATION_ISLANDS`
   (`frontend/src/creation/registry.js`) and to `COMPONENTS` in
   `frontend/src/creation/mount.js`. Add
   `{ key: 'npcAgent', containerId: 'npcagent-panel' }` to the npc tab's
   `islands` list in `CREATION_TABS` (`index.html`, npc entry). Per the
   island vocabulary, the entry declares `loader: null` and
   `onWorldSwitch: null`; world-state reset is driven by
   `serverState.worldId`.

   Mounting into a container that is `display:none` until toggled is fine —
   the island mounts on tab entry via the existing `island:slot` dispatch
   from `creationRefreshList` (`index.html:4438`), and
   `npcAgentToggle`'s call to `npcAgentRenderLauncher()` becomes unnecessary.

6. **The toggle button and badge stay legacy.** `npcAgentToggle` (6768) and
   the `#npcagent-launcher-btn` / `#npcagent-badge` markup (1303) are chrome
   and retire at `-l` — the same line `-e` drew when it moved one of three
   sheet-header buttons and left the other two.

   `npcAgentToggle` keeps flipping the panel's `display`. The badge is
   component -> legacy, which `mount.js:11-21` explicitly states is not its
   concern: use a component-owned `CustomEvent` on the `legacyDoc` prop with
   a listener in `index.html`, exactly as `Constructeur.svelte` already does
   for its tab-bar refresh. Do not add a badge relay to `mount.js`.

7. **Amend the relgraph slot's `onOpen`.** The npc tab's `slots[0].onOpen`
   currently reads `() => { npcAgentCheckOpenBatch(); linkAgentCheckOpenBatch(); }`.
   `npcAgentCheckOpenBatch` is deleted by this brief; the island performs the
   same check on mount. Drop the npc half of that call and leave
   `linkAgentCheckOpenBatch()` — `-g` drops the rest.

8. **Delete every ported function from `index.html`** in the commit that
   replaces it, and extend the new island entry's `retiredPrefixes` in
   `registry.js` with every deleted identifier, including the four
   underscore-prefixed helpers that a bare `npcAgent` prefix scan would still
   catch but which must be listed by name for the record. Add a
   `BRIEF-0059-f` comment in the style of the existing `-c` / `-d` blocks.

9. **Prune `legacy_calls.baseline`** of any record this brief closes. Planning
   RECON expects **none** — the agents are legacy-to-legacy today and appear
   nowhere in the baseline. If a record does close, prune it in the same
   commit; if none does, say so in the commit message rather than leaving the
   reader to infer it.

10. **Extend `graph_primitive.py`'s `GONE_PLAIN` list** with this brief's
    deleted identifiers, per M7's note that it is a data list extended per
    migrating brief.

## Scope OUT

- **The link agent.** All 27 functions at `index.html:7217-7615` stay legacy.
  `-g` ports them and is the brief that proves the `LocationTree` lock holds
  against a genuinely different interaction model. Porting both here would
  make that proof unobservable.
- **Converging the two run loops.** They look alike and are not: the NPC loop
  detects completion by catching an error and string-matching
  `'already fully generated'` (`index.html:6944`, `6961`), while the link loop
  reads a `result.done` flag (7391). That is a difference in the **backend
  contract**, and unifying it would need a backend change — out of scope
  (cross-cutting rule 2). Amendment 1's convergence covers the traversal and
  nothing else.
- **Fixing the string-matched termination.** REPORT it: a backend message
  edit silently breaks the run loop. Record it for a named deferral; do not
  fix it inside a migration brief.
- **The governed review component.** The agents do not use `reviewRegister`,
  and `review_component.py`'s permitted-importer list must not grow.
  Confirmed this session: the agent painters are flat group -> row editors
  (`_npcAgentGroupRows` 7010, `_npcAgentRowHtml` 7019, `_npcAgentGroupHtml`
  7057), not the hierarchical cascade the review component governs. Confirm
  that reading before porting; if the shape turns out to be a cascade, STOP —
  a third bespoke reviewer landing in Svelte is the divergence this
  workstream exists to end.
- **`npc_agent_strata.py`, `npc_batch_count_contract.py`,
  `npc_batch_purge.py`.** All three scan `src/**/*.py` and `writes/` only
  (M7). No re-homing. Do not spend effort on them.
- **The `.linkagent-*` CSS block** (`index.html:1000-1012`). It is shared by
  both agents; moving it while one consumer is still legacy would strand it.
  `-g` or `-l`.
- **Any backend change.** Frontend-only.

## Invariants to defend

- **One graph is a graph, one tree is a tree.** `location_tree.py` is this
  brief's pass-2 lock, landed with the primitive and before its second
  consumer — the same sequencing `graph_primitive.py` used in TICKET-0057.
- **Model proposes, code judges.** The agent generates drafts into a batch;
  nothing here may write canon directly. Every commit/reject path stays on
  the existing `/api/npc-batches/...` routes.
- **No structure without a reader (E2).** `LocationTree.svelte` ships in
  commit 1 with its check and gains its first consumer in commit 2 of the
  same brief. It does not ship speculatively parameterised for a third
  consumer that does not exist.
- **Assign-then-read is forbidden** (`effect_self_write.py`, TICKET-0062).
  The launcher's derived lists — the tree's `known` set, the line totals —
  are `$derived`, not `$state` written inside an `$effect`.
- **Fail-closed guards never lapse.** `legacy_call.py`, `creation_island.py`,
  `graph_primitive.py`, `location_tree.py` and `effect_self_write.py` all
  pass after each of the three commits.

## Done means

- [ ] `python tooling/verify/checks/location_tree.py` exits 0 after commit 1.
- [ ] Scratch A: copy `LocationTree.svelte`'s recursion into a second
      component; the check exits non-zero; revert.
- [ ] Scratch B: point the check's scan at an empty directory; exits non-zero
      naming the vacuity guard, never 0; restore.
- [ ] `grep -c "npcAgent" src/world_engine/cockpit/index.html` returns only
      the counts attributable to `npcAgentToggle`, the button markup and the
      slot `onOpen` — enumerate the surviving occurrences in the commit
      message so the residue is deliberate rather than assumed.
- [ ] `python tooling/verify/checks/creation_island.py` exits 0; scratch:
      re-add `function npcAgentLaunch(` and confirm rule 7 bites; revert.
- [ ] `python tooling/verify/checks/effect_self_write.py` exits 0.
- [ ] Live: open the npc tab, click "Agent PNJ"; the location tree renders
      with the same indentation and dashed guide as before.
- [ ] Live: select a root; press Prévisualiser; the preview counts appear.
      Add a line, edit its count and description, remove it; the total
      updates.
- [ ] Live: launch a batch; the review surface renders rows grouped by line;
      edit a name, a description, a `physical_tier`, a faction, a location,
      a long goal and short goals; reject a row and restore it.
- [ ] Live: pause mid-run and retry; the loop resumes.
- [ ] Live: commit the batch; the NPCs appear in the entity list. Then run a
      second batch and abandon it.
- [ ] Live: "Générer les liens" from the NPC agent still hands off to the
      link agent, which is still legacy.
- [ ] Live: leave the npc tab and return; the panel state resets exactly as
      before. Switch worlds; no stale batch survives.
- [ ] Live: the `#npcagent-badge` still appears when an open batch exists.
- [ ] Live: open the relation graph from the npc tab; the link agent's
      open-batch check still fires (item 7 left it in place).
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `python tooling/verify/run.py` exits 0.
- [ ] `module_budget.py` and `function_length.py` pass on every file written.
- [ ] `/review-step` and `/close-step` run per commit.

## Docs to update

None. Brief `-m`, which also records the `location_tree.py` lock and the
string-matched-termination deferral in `ARCHITECTURE_DECISIONS.md`.
