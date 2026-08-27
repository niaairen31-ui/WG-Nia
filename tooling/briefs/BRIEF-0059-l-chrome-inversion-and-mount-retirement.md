# BRIEF — Step "chrome inversion + world CRUD + mount retirement"

Ticket: TICKET-0059. Requires BRIEF-0059-k landed. Reads
SUPPLEMENT-0059-recon-amendments **Amendments 2, 3, 4 and 7**. Cites
RECON-0059-a **M6**, **M7**.

**Anchor convention.** Every line number below is indicative, read from a
tarball of `main` this session. Your working tree is ahead of it. **Locate by
function name; verify every line locally before acting on it.**

This is the largest and most delicate brief of the ticket. It is the one that
retires the `creation` legacy mount, and `legacy_call.py` rule 7 will refuse
that retirement until every `TICKET-0059` baseline record is gone. The
ordering below is therefore not a preference; it is what the guards permit.

## Context

Every Creation *pane* is Svelte. What remains is the **chrome**: the tab
registry and factory, the sub-tab dispatcher, the shell band, the return-crumb
navigation, the pending-creation cards, world CRUD, and the shared modal.

The baseline entering this brief carries twelve `TICKET-0059` records, all
chrome-owned:

```
App.svelte::showCreationSubTab            Sheet.svelte::creationRefreshList (x3)
Header.svelte::worldCreateOpen            Region.svelte::creationRefreshList
Header.svelte::worldDeleteOpen            RoomBatch.svelte::creationRefreshList
EntityList.svelte::creationSelectRecord   Sheet.svelte::loadPendingCreations
FactionRoster.svelte::creationOpenEntityFrom
npcAgent.svelte.js::linkAgentToggle
```

Two records stay past this ticket: `App.svelte::showFn` and
`Header.svelte::activateWorld`, both `TICKET-0061`, because Play is still
legacy and reads them.

`activateWorld` is the subtle one. It is chrome by M6's inventory, but Play
depends on it, so it **cannot** be deleted here. World *create* and *delete*
can; world *activation* cannot. Do not conflate them.

## Scope IN

### Commit 1 — `tabs.js` and the tab factory (lock D1)

1. **`frontend/src/creation/tabs.js`** — the tab registry, fed by the same
   `authorRegistry` fetch `_buildRuntimeCreationTabs` reads today.

   **It stays a factory.** TICKET-0046's runtime entity types inject their
   tabs at boot; `tabs.js` must not become a frozen literal list. Port
   `_buildRuntimeCreationTabs`, `refreshCreationTabs` and `creationInit`'s
   registry-reading half.

2. **`frontend/src/creation/Creation.svelte`** — the shell: the tab bar,
   `showCreationSubTab`, `_creationActivateTab`, `renderCreationShell`
   (the band with the title and the `primaryAction` button),
   `_creationRunWorldSwitchResets`, `_renderOnDemandToggles`.

   `App.svelte` stops calling `showCreationTab` through the bridge and drives
   `Creation.svelte` directly. **Prune `App.svelte::showCreationSubTab` and
   delete the `showCreationTab` export from `bridge.js`** in this commit.

   The `route:subtab` continuous sync (TICKET-0058 lock E1) moves with the
   dispatcher. `SHELL_ROUTES` and `app.py`'s `_SHELL_ROUTES` keep their
   current shape — `/creation/{sub_tab}`, no new segment.
   `legacy_mount.py`'s route-agreement rule must still pass unchanged.

3. **Re-home `page_contract.py`** (Amendment 7 names the second check too).
   Its assertions move from `index.html` onto `tabs.js` and
   `Creation.svelte`, preserving every guarantee: `TAB_KEYS` all present,
   every entry declares `primaryAction`, no tab-id literal inside the
   dispatcher or the activator, the factory still builds runtime tabs, and
   no static `#ctab-` outside the frozen `TAB_KEYS`.

4. **Re-home `creation_island.py` rules 4/5/9/10/11** onto `tabs.js` and
   `Creation.svelte`. **Rule 7's retired-prefix scan against `index.html`
   stays** — it is what proves the deletions, and it is still needed until
   the file is gone.

### Commit 2 — navigation and pending creations

5. Port `creationRefreshList`, `creationSelectRecord`,
   `creationOpenEntityFrom`, `creationResolveEntityTab`,
   `creationReturnToOrigin`, `creationRenderReturnControl`,
   `creationNewEntity`, `creationSaveDispatch`, `loadPendingCreations`,
   `renderPendingCreationCard`, and the `creationReturnTo` module state.

   `creationRefreshList`'s job is dispatching `island:slot` per declared
   island. Once the chrome is Svelte and the islands are its children, that
   dispatch is no longer a cross-document event — it becomes ordinary parent
   -> child reactivity. **Do not port the CustomEvent dispatch into Svelte
   and keep talking to yourself across an event bus.** State in the commit
   message which mechanism replaced it.

   **Prune seven baseline records** here: three `Sheet.svelte`, one
   `Region.svelte`, one `RoomBatch.svelte` (all `creationRefreshList`),
   `EntityList.svelte::creationSelectRecord`,
   `FactionRoster.svelte::creationOpenEntityFrom`, and
   `Sheet.svelte::loadPendingCreations`.

6. **Re-home `creation_return_nav.py`.** It asserts `creationReturnTo` is
   declared exactly once and the single-slot return crumb is wired correctly;
   it already reads `FactionRoster.svelte` as well as `index.html`. Both
   halves move to the Svelte side.

### Commit 3 — world CRUD and the modal seal (Amendments 3 and 4)

7. **`frontend/src/creation/WorldCreate.svelte`** and
   **`frontend/src/creation/WorldDelete.svelte`** (or one component with two
   dialogs — say which and why). Port `worldCreateOpen`, `worldCreateSubmit`,
   `worldGenerateDraft`, `worldApplyDraft`, `worldDeleteOpen`,
   `worldDeleteConfirm`. Both consume `Modal.svelte`.

   **Prune `Header.svelte::worldCreateOpen` and
   `Header.svelte::worldDeleteOpen`**; delete both exports from `bridge.js`.

8. **`loadWorldSelector` ports; `activateWorld` does not.** The selector is a
   Creation-side read. `activateWorld` is read by Play and stays legacy with
   its `TICKET-0061` baseline record intact. If porting the selector turns
   out to require porting the activation, STOP and report — that is a
   TICKET-0061 boundary question, not a judgement call for this brief.

9. **Delete `genericModalOpen`, `genericModalClose` and the
   `#generic-modal-backdrop` markup** now that their last consumers are gone.
   Census first: `_obsLoadProposals` was falsely reported as a consumer in a
   previous exchange (the report was wrong — an end-of-file span bug swallowed
   the backdrop's own inline `onclick`). **Run the census yourself** and
   report what you find; if a real Observation consumer exists, STOP.

10. **Land `modal_primitive.py`** — fail-closed, asserting one dialog
    implementation under `frontend/src/`: no file other than `Modal.svelte`
    may construct a backdrop-plus-panel dialog. Vacuity guard on the **scan**
    (zero `.svelte` files, or `Modal.svelte` absent -> FAIL), following
    `location_tree.py` and `effect_self_write.py`. **No allow-list.** This is
    the lock BRIEF-0059-h deliberately withheld until the legacy
    implementation died.

### Commit 4 — mount retirement

11. **Port `showCreationView`** and remove `creation` from `LEGACY_MOUNTS`
    (`frontend/src/legacy/registry.js`); shrink
    `tooling/verify/baselines/legacy_mounts.baseline` to `observation` and
    `play`.

    `legacy_call.py` rule 7 gates this: it fails if any `TICKET-0059` record
    remains. **Prune `npcAgent.svelte.js::linkAgentToggle`** — the last one —
    by porting `npcAgentToggle` and `linkAgentToggle` and the two agent
    launcher buttons and badges into the Svelte chrome, alongside every other
    `#ctab-` and shell-band control.

12. **Delete the entire Creation markup region from `index.html`** — the
    `#creation-view` container, the `#ctab-*` buttons, the shell band, and
    every emptied pane container. Play and Observation markup stay.

13. **Verify `legacy_mount.py` passes** with `creation` gone, including its
    shell-route agreement rule and its confinement assertion.

## Scope OUT

- **`activateWorld` and `showSurface`.** Both `TICKET-0061`. Play reads them.
- **Play and Observation markup, code, or checks.** `observation_surface.py`
  is TICKET-0060's.
- **Deleting `index.html`.** TICKET-0061. This brief removes the Creation
  region from it; the file survives hosting Play and Observation.
- **Adding a record to `legacy_mounts.baseline` or `legacy_calls.baseline`.**
  Both may only shrink.
- **An allow-list in `modal_primitive.py`.** Item 10.
- **A new route segment for record ids.** `/creation/{sub_tab}` keeps its
  shape; a deep-link-to-record route is a separate design decision.
- **Doc updates.** `-m`.
- **Any backend change** beyond leaving `app.py`'s `_SHELL_ROUTES` as it is.

## Invariants to defend

- **Structural over disciplinary.** Rule 7 is what orders this brief. Do not
  work around it by pruning a record before its site actually closes —
  `legacy_call.py` rule 4 will catch that on the next run, and doing it
  deliberately would be defeating a guard rather than satisfying it.
- **The dynamic tab factory survives.** Item 1. This is TICKET-0046's
  guarantee and the highest-value thing in the whole workstream: creating
  entity types from the UI depends on it. A frozen tab list would pass every
  check listed here and silently kill the feature the migration exists to
  serve. Verify it live with a runtime type, not just with a green check.
- **Fail-closed guards never lapse.** Every re-homed check lands in the same
  commit as the move it guards. No commit in this brief may leave a guarantee
  unasserted, even briefly.
- **One dialog, structurally.** Item 10, landed only once the legacy
  implementation is gone.
- **History is sacred.** World delete keeps whatever confirmation gate it has
  today; do not weaken it while moving it onto `Modal.svelte`.
- **Assign-then-read is forbidden** (`effect_self_write.py`).
- **Frontend-only.**

## Done means

- [ ] `legacy_calls.baseline` contains exactly two records, both
      `TICKET-0061`: `App.svelte::showFn` and `Header.svelte::activateWorld`.
- [ ] `legacy_mounts.baseline` contains exactly `observation` and `play`;
      `LEGACY_MOUNTS` no longer declares `creation`.
- [ ] Scratch: restore one `TICKET-0059` record to `legacy_calls.baseline`
      with `creation` already removed from `LEGACY_MOUNTS`; rule 7 must bite;
      revert.
- [ ] `python tooling/verify/checks/modal_primitive.py` exits 0; scratch:
      add a second backdrop-plus-panel dialog to any component; it must bite;
      revert. Scratch: point its scan at an empty directory; it must bite,
      never pass.
- [ ] `page_contract.py`, `creation_island.py`, `creation_return_nav.py`,
      `legacy_mount.py`, `location_tree.py`, `effect_self_write.py`,
      `graph_primitive.py`, `review_component.py` all exit 0 after **every**
      commit.
- [ ] `page_contract.py` reads `tabs.js` and `Creation.svelte`, not
      `index.html`; scratch: add a tab-id literal to the ported dispatcher and
      confirm it bites; revert.
- [ ] `creation_island.py` rule 7 still scans `index.html` for retired
      prefixes and still bites when one is restored.
- [ ] `grep -c "creation-view\|ctab-\|showCreationSubTab\|creationRefreshList\|genericModalOpen\|worldCreateOpen" src/world_engine/cockpit/index.html`
      returns 0.
- [ ] The commit-3 census for `genericModal*` consumers is recorded in the
      commit message.
- [ ] Live: all fourteen sub-tabs open, render and save.
- [ ] Live: **create a new entity type through Constructeur**; its tab
      appears without a reload and is usable. Reload; it is still there. This
      is the factory guarantee and no check substitutes for it.
- [ ] Live: deep-link `/creation/<sub_tab>` cold-loads onto the right tab for
      every tab; browser Back leaves Creation rather than walking sub-tabs;
      switching tabs updates the URL.
- [ ] Live: the return crumb — open an entity from the faction roster, then
      return; the crumb takes you back to the roster.
- [ ] Live: pending creation cards render and resolve.
- [ ] Live: create a world; generate and apply a draft; the new world appears
      in the selector and can be activated. Delete a world through its
      confirmation gate.
- [ ] Live: switch worlds; every tab resets.
- [ ] Live: Play and Observation both still open and work — the mount
      retirement must not disturb them.
- [ ] Live: both agent panels still toggle and show their badges from the
      Svelte chrome.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `python tooling/verify/run.py` exits 0.
- [ ] `module_budget.py` and `function_length.py` pass on every file written.
- [ ] `/review-step` and `/close-step` run per commit.

## Docs to update

None in this brief. `-m` writes them all, once the mount is actually retired.
