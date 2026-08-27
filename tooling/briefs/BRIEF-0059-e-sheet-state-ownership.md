# BRIEF — Step "entity sheet: state ownership"

Ticket: TICKET-0059. Requires BRIEF-0059-d landed. Reads
SUPPLEMENT-0059-recon-amendments **Amendment 3** — which re-scoped this brief.
Cites RECON-0059-a **M2**, **M3**, **M6**.

**Re-scope notice.** This brief was originally chained as "residual
`legacyCall` sites outside Sheet; baseline -> 0". That target is not
reachable here: several of those sites call **chrome**, not sheet code, and
chrome cannot die before it inverts. Amendment 3 re-scopes this brief to the
sheet's own state, and moves the chrome-owned records to `-l`.

## Context

After `-c` and `-d`, `Sheet.svelte` renders every field section itself. What
remains is not rendering — it is **state**. Seven legacy functions still own
facts about the sheet that the sheet displays:

```
Sheet.svelte:167  legacyCall('_authorResetCreateDrafts')
Sheet.svelte:415  legacyCall('_authorGetPendingCreationMutationId')
Sheet.svelte:465  legacyCall('_authorConsumePendingCreationMutationId')
Sheet.svelte:475  legacyCall('_authorNotifySaved')
EntityList.svelte:168      selectEntity(id)        -> authorSelectEntity
graph/consumers/relations.js:214  getSelectedCharacterId() -> authorGetSelectedEntityId
index.html:1353   <button id="author-delete-btn" onclick="authorDelete()">
```

`authorEntityId` is a bare `let` at the legacy script's top level — never a
`window` property, which is why `bridge.js` needed a one-line
`authorGetSelectedEntityId` accessor at all (`bridge.js`'s own note,
TICKET-0058/BRIEF-0058-c). The selected entity is currently a legacy global
that three separate Svelte modules ask the legacy document about.

This brief moves that fact to where it is read. After it, `Sheet.svelte` has
**zero** bridge-reach sites of its own, and the only remaining Creation-side
records in the baseline call chrome functions that `-l` deletes.

`authorDelete` is a special case worth naming: M3 found it has no Svelte
caller at all. Its only caller is the static header button at
`index.html:1353`. It is legacy calling legacy — invisible to the seal — but
it operates on the sheet's selected entity, so it moves with the state that
selects it.

## Scope IN

1. **`frontend/src/creation/sheetState.svelte.js`** — a rune-based store
   owning:
   - the selected entity id and the loaded detail,
   - the create-draft lifecycle currently held by `_authorResetCreateDrafts`
     (`index.html:5912`),
   - the pending-creation mutation id currently held by
     `_authorGetPendingCreationMutationId` (6581) and
     `_authorConsumePendingCreationMutationId` (6587).

   The consume semantics are load-bearing and must be preserved exactly:
   the getter reads without clearing, the consumer reads **and clears**. Read
   both bodies before porting; do not infer the contract from the names.

2. **Port `authorSelectEntity` (`index.html:6422`) into the store.** It is
   the sheet's loader: it fetches the entity detail and drives every section.
   `EntityList.svelte:168` stops calling `bridge.js`'s `selectEntity(id)` and
   sets store state directly.

   `bridge.js`'s `selectEntity` export is deleted in the same commit. So is
   `getSelectedCharacterId`, once item 3 lands.

3. **`graph/consumers/relations.js:214` reads the store**, not the bridge.
   The relations graph's ego mode needs the currently-selected character at
   load time; it now reads `sheetState`. Import direction is
   `graph/consumers/ -> creation/sheetState.svelte.js`. If `graph_primitive.py`
   or `import_cycle.py` forbids that edge, STOP and escalate — do not invert
   the dependency by having the sheet push into the graph consumer, which
   would give the graph two sources of truth for selection.

4. **Port `_authorNotifySaved` (`index.html:6451`)** into the store's save
   path. Read its body: it is the sheet's post-save notification hook and may
   have consumers beyond the sheet. If M3's "no caller outside Sheet" no
   longer holds at execution time, STOP.

5. **Port `authorDelete` (`index.html:6592`) into `Sheet.svelte`** and move
   the `#author-delete-btn` button out of the static legacy markup
   (`index.html:1353`) into the component. Its sibling controls
   `#author-save-btn` (`onclick="creationSaveDispatch()"`, line 1352) and
   `#author-return-btn` (`onclick="creationReturnToOrigin()"`, 1349) are
   **chrome** and stay — they call chrome functions that die at `-l`.

   Moving one button out of a three-button header is deliberate and not a
   half-measure: the header band belongs to the chrome, and `-l` takes the
   rest of it. Do not restructure the header here.

   The confirmation text stays verbatim:
   `Set this entity to inactive (soft delete)? Relations and knowledge are
   preserved, and this is reversible.`

6. **Delete every ported legacy function from `index.html`** in the commit
   that replaces it, and extend
   `CREATION_ISLANDS.entitySheet.retiredPrefixes` with each identifier by
   name. Add a `BRIEF-0059-e` comment above the block.

7. **Prune `legacy_calls.baseline`** of every record closed, in the commit
   that closes it. Expected: the four `Sheet.svelte` `_author*` records, the
   `EntityList.svelte::authorSelectEntity` record, and the
   `relations.js::authorGetSelectedEntityId` record — six records, plus the
   two `bridge.js` exports deleted.

8. **Three commits**: (a) the store plus the create-draft and pending-mutation
   lifecycle; (b) selection — `authorSelectEntity`, `EntityList`,
   `relations.js`, and the two bridge exports; (c) `authorDelete` and the
   button move.

## Scope OUT

- **`creationRefreshList`** — four call sites (`Sheet.svelte:393`, `:474`,
  `Region.svelte:311`, `RoomBatch.svelte:246`). It is chrome
  (`index.html:4432`): it dispatches `island:slot` for every island the
  active tab declares, and still-legacy tabs depend on it. It dies at `-l`.
  Those four records stay in the baseline. **Do not reimplement it
  Svelte-side here** — a second dispatcher racing the legacy one is exactly
  the two-authorities failure this workstream exists to end.
- **`creationSelectRecord`** (`EntityList.svelte:172`) and
  **`creationOpenEntityFrom`** (`FactionRoster.svelte:58`) — chrome
  navigation, guarded by `creation_return_nav.py`. Brief `-l`.
- **`genericModalOpen` / `genericModalClose`** (`locationType.js:46`, `:104`)
  — a shared modal primitive at `index.html:8326`/`8334` with markup at
  `8892-8898` and three further legacy consumers: `competences` (`4752`),
  world create (`8401`), world delete (`8500`). It becomes `Modal.svelte` at
  `-l`, when its legacy consumers die. Touching it here would strand three
  legacy call sites against a Svelte component.
- **`creationSaveDispatch`, `creationReturnToOrigin`,
  `creationResolveEntityTab`, `creationRenderReturnControl`.** Chrome, `-l`.
- **`showSurface`, `activateWorldViaLegacy`, `openWorldCreate`,
  `openWorldDelete`, `showCreationTab`** in `bridge.js`. Not sheet state.
  `-l` and TICKET-0061.
- **Emptying the baseline.** It will not empty here, by design (Amendment 3).
  A commit that claims it did is wrong.
- **Restructuring the sheet header band** (`index.html:1348-1360`) beyond
  moving the one delete button. `-l`.
- **Introducing a global Creation store.** This store owns the entity sheet,
  nothing else. A store that also holds the active tab, the world id, or the
  entity list is `-l`'s design decision, made with the chrome in front of it.
  Building it speculatively here is structure without a reader (E2).
- **Any backend change.** Frontend-only (cross-cutting rule 2).

## Invariants to defend

- **Single canon-write authority.** The soft-delete path stays on
  `POST /api/entities/{id}/delete`. It does not become a DELETE, and it does
  not gain a hard-delete sibling.
- **History is sacred.** `authorDelete` is a soft delete that preserves
  relations and knowledge. Its confirmation text says so and must not be
  softened or shortened.
- **One authority per fact.** After this brief, exactly one module knows
  which entity is selected. The failure mode to refuse is a store that
  mirrors a legacy global rather than replacing it — if `authorEntityId`
  still exists in `index.html` after commit (b), the brief has not landed.
- **Fail-closed guards never lapse.** `legacy_call.py`,
  `creation_island.py` and `graph_primitive.py` pass after each of the three
  commits.
- **No structure without a reader (E2).** Every field on the store has a
  named consumer in this same brief.

## Done means

- [ ] `python tooling/verify/checks/legacy_call.py` exits 0 after each
      commit; `Sheet.svelte` contributes **zero** records at the end, and the
      remaining `TICKET-0059` records are exactly the chrome-owned ones
      enumerated in Scope OUT.
- [ ] `grep -c "authorEntityId\|authorSelectEntity\|authorGetSelectedEntityId\|_authorNotifySaved\|_authorResetCreateDrafts\|authorDelete" src/world_engine/cockpit/index.html`
      returns 0.
- [ ] `grep -c "selectEntity\|getSelectedCharacterId" frontend/src/legacy/bridge.js`
      returns 0.
- [ ] `python tooling/verify/checks/creation_island.py` exits 0; scratch
      mutation: re-add `function authorSelectEntity(` and confirm rule 7
      bites; revert.
- [ ] Live: click an entity in the list; the sheet loads it. Click another;
      the sheet swaps. Confirm no stale field survives the swap.
- [ ] Live: open the relation graph in ego mode with an NPC selected;
      confirm it centres on that NPC — this proves `relations.js` reads the
      store correctly.
- [ ] Live: start creating a new entity, fill draft fields, switch tabs and
      come back; confirm the create-draft reset behaves exactly as before
      (compare against `main` if the expected behaviour is unclear — do not
      guess).
- [ ] Live: create an entity through the pending-creation path and confirm
      the pending mutation id is consumed exactly once — a second save must
      not re-attach it.
- [ ] Live: soft-delete an entity; confirm the confirmation text is
      unchanged, the entity goes inactive, and its relations and knowledge
      still exist on reload.
- [ ] Live: confirm Save and Return still work from the sheet header —
      they are still legacy and must be untouched.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `python tooling/verify/run.py` exits 0.
- [ ] `module_budget.py` and `function_length.py` pass on every file written.
- [ ] `/review-step` and `/close-step` run per commit.

## Docs to update

None. Brief `-m`.
