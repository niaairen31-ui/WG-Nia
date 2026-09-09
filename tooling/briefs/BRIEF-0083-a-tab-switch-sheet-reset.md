# BRIEF - Step "tab-switch sheet reset"

TICKET-0083, brief a of a. Frontend only. No schema change, no DB write, no
Python engine code touched except the new verify check.

## Mini-RECON (measured on `main`, schema v1.99 -- unchanged by this brief)

| Fact | Anchor | Tag |
|---|---|---|
| `showCreationSubTab` writes `activeTabKey` before any reset | `frontend/src/creation/tabs.js:457-481`, assignment at `:461` | [M] |
| The per-entry reset call site | `tabs.js:468` | [M] |
| The five tab-enter reset helpers | `tabs.js:391-419` | [M] |
| `onTabEnter` declarations: npc / pj / lieux / factions / objets | `tabs.js:184, 202, 215, 230, 243` | [M] |
| `onTabEnter` declarations: intrigues / evenements | `tabs.js:301, 313` | [M] |
| `onTabEnter` declaration: runtime tab factory | `tabs.js:525` | [M] |
| Sheet's record branches gated on `tabKey` | `frontend/src/creation/Sheet.svelte:612, 615` | [M] |
| The unguarded generic-branch read that throws | `Sheet.svelte:641` (also `:648`, `:649`) | [M] |
| The `creation:sheet-reset` listener that loses its callback | `Sheet.svelte:206-214` | [M] |
| `flushSync(fn)` flushes the pending batch BEFORE running `fn` | `frontend/node_modules/svelte/src/internal/client/reactivity/batch.js:1020-1024` | [M] |
| `creation:selection` listener that nulls `selectedRecordId` | `frontend/src/creation/EntityList.svelte:186-189` | [M] |
| `creationSelectRecord` always passes the CURRENT tab key | `EntityList.svelte:196`, `tabs.js:621-632` | [M] |
| Only writer that CHANGES `activeTabKey` | `tabs.js:461` (`mount.js:120` re-writes the same value) | [M] |
| Module budgets | `tabs.js` 767/1000, `Sheet.svelte` 763/1000 | [M] |
| CLAUDE.md budget headroom | 32788/38000 chars, 100-char line ceiling | [M] |
| Committed bundle is already fresh | rebuild reproduces `index-CmOQTqiy.js` byte-identical | [M] |

Measured blast radius, both directions of the fix, and the full transition
matrix are in `tooling/tickets/TICKET-0083-creation-tab-switch-sheet-reset.md`
("Clarifications resolved"). Do not re-derive them; do re-verify the outcome.

## Context

Opening a record on Intrigues (or Evenements) and then clicking another
Creation sub-tab leaves the editor area frozen on the opened record -- old
sheet, old sidebar list -- while the URL and the sub-tab button both move.
Cause: `activeTabKey` moves before the sheet is cleared, `Sheet.svelte` picks
its render branch off `activeTabKey` but is fed by `sheetType`, and the
resulting inconsistent frame throws inside the very `flushSync` that was
supposed to clear the sheet -- aborting the whole batch. Seven bespoke tabs
never reset the sheet at all. This brief closes the ordering window in the one
dispatcher and makes the mismatch unrenderable rather than fatal.

## STOP conditions

- **S1.** If `showCreationSubTab` in `tabs.js` does not match the RECON anchor
  (`creationState.activeTabKey = tab;` on its own line, followed by the
  crumb comment and `creationState.creationReturnTo = null;`), STOP and report.
  Do not adapt.
- **S2.** If deleting `_entityTabEnterReset` leaves any caller other than
  `_lieuxTabEnterReset` / `_npcTabEnterReset` and the six registry entries
  named in item 4, STOP and report the extra caller. Do not delete it.
- **S3.** If `module_budget.py` reports `tabs.js` or `Sheet.svelte` over 1000
  lines after the edits, STOP and report -- do not extract a module to make
  room in this brief.
- **S4.** If `claude_md_contract.py` fails on the CLAUDE.md addition
  (character budget or the 100-char line ceiling), STOP and report the
  measured numbers. Do not trim unrelated law to make room.
- **S5.** Anything else found in `tabs.js` / `Sheet.svelte` that looks wrong:
  REPORT ONLY. This brief authorizes no other change.

## Scope IN

### Commit 1 -- the ordering fix (`frontend/src/creation/tabs.js`)

1. **Hoist the sheet reset into the dispatcher, before the key move.** In
   `showCreationSubTab`, replace the region from `if (!entry) return;` through
   `creationState.creationReturnTo = null;` with, verbatim:

   ```js
     if (!entry) return;

     // TICKET-0083. The sheet is cleared BEFORE activeTabKey moves, and on
     // EVERY tab change -- not per registry entry, not afterwards. Both
     // halves are load-bearing:
     //
     //   (a) BEFORE. Sheet.svelte's branch chain is SELECTED by one fact and
     //       FED by another (sheetType/sheetDetail). While the two disagree
     //       it renders a record's data through the generic entity branch,
     //       whose registry.types[type] lookup does not resolve for a tab id.
     //       flushSync(fn) flushes the pending batch BEFORE running fn
     //       (svelte/src/internal/client/reactivity/batch.js), so a reset
     //       that runs AFTER the key move is precisely what forces that
     //       inconsistent frame. The throw it raised aborted the batch, and
     //       every DOM update queued in it -- the sheet's AND the sidebar's
     //       -- was dropped: the tab button and URL moved, the editor area
     //       did not.
     //
     //   (b) EVERY. The seven bespoke entries declare onTabEnter: null, so a
     //       per-entry reset means "reset iff this entry remembered to ask"
     //       -- a convention a new entry can silently break. Here it is a
     //       property of the switch itself.
     //
     // These two dispatches are the SINGLE sheet-reset site in the frontend
     // tree; creation_tab_switch.py locks both the uniqueness and the order.
     if (prev !== tab) {
       document.dispatchEvent(new CustomEvent('creation:selection', { detail: { entityId: null, recordId: null } }));
       document.dispatchEvent(new CustomEvent('creation:sheet-reset'));
     }

     creationState.activeTabKey = tab;
     // Any tab change drops the crumb; creationOpenEntityFrom/
     // creationReturnToOrigin re-set it AFTER calling this, which is what
     // makes a manual sub-tab click clear it and a programmatic navigation
     // keep it.
     creationState.creationReturnTo = null;
   ```

   Everything after that line in the function (`if (prev !== tab && ...)`,
   the registry-load branch, `replace('creation', tab)`) is untouched.

2. **Delete three helpers, now redundant.** Remove `_entityTabEnterReset`
   (`tabs.js:391-394`), `_intriguesTabEnterReset` (`:409-413`) and
   `_evenementsTabEnterReset` (`:415-419`) entirely. Their whole body was the
   two dispatches item 1 now owns, plus -- for the latter two --
   `creationState.selectedRecordId = null`, which the hoisted
   `creation:selection` dispatch already produces through
   `EntityList.svelte:186-189`.

3. **Strip the delegated call from the two surviving helpers.**
   `_lieuxTabEnterReset` and `_npcTabEnterReset` keep everything except their
   `_entityTabEnterReset();` first line. Verbatim, replacing `tabs.js:396-407`:

   ```js
   function _lieuxTabEnterReset() {
     onDemandSlotReset(CREATION_TABS.lieux);
     document.dispatchEvent(new CustomEvent('creation:batch-reset'));
   }

   function _npcTabEnterReset() {
     onDemandSlotReset(CREATION_TABS.npc);
     document.dispatchEvent(new CustomEvent('creation:npcagent-reset'));
     document.dispatchEvent(new CustomEvent('creation:linkagent-reset'));
   }
   ```

4. **Null the six `onTabEnter` entries whose helper is gone.** In
   `CREATION_TABS`, set `state: { onTabEnter: null, onWorldSwitch: null },` on
   `pj` (`:202`), `factions` (`:230`), `objets` (`:243`), `intrigues`
   (`:301`), `evenements` (`:313`), and in the runtime tab factory's own
   entry template (`buildRuntimeCreationTabs`, `:525`). `npc` (`:184`) and
   `lieux` (`:215`) keep their helper references unchanged.

5. **Update the file header comment.** The header block's point 3 explains the
   container show/hide adaptation; append one paragraph after it, verbatim:

   ```
      TICKET-0083. `showCreationSubTab` now clears the entity sheet itself,
      before assigning activeTabKey, on every tab change. The five per-entry
      tab-enter resets this module was ported with each re-dispatched
      'creation:selection' + 'creation:sheet-reset'; three of them held
      nothing else and are gone. What survives in _lieuxTabEnterReset /
      _npcTabEnterReset is the state those two tabs own beyond the sheet
      (on-demand slots, the batch panel, the two NPC agent panels) -- an
      entry's onTabEnter is for ITS OWN state now, never for the shared
      sheet.
   ```

### Commit 2 -- the branch-selector fix (`frontend/src/creation/Sheet.svelte`)

6. **Gate the record branches on `type`, and guard the generic branch.**
   Replace `Sheet.svelte:612-619` with, verbatim:

   ```svelte
       {:else if type === 'evenements'}
         <Evenements {legacyDoc} {isNew} event={detail} entities={creationState.entities}
           eventFields={registry.event_fields} onSave={saveSheet} />
       {:else if type === 'intrigues'}
         <Intrigues {isNew} agenda={detail} />
       {:else if tabKey === 'pj' && isNew}
         <PjCreatePanel {legacyDoc} />
       {:else if registry.types[type]}
   ```

   `type` is `creationState.sheetType`, already `$derived` at `:582`.
   `enterViewMode(record, tabId)` / `enterCreateMode(type)` write `sheetType`
   and `sheetDetail` in the same `flushSync` callback, so branch and data can
   no longer disagree -- they are the same write. The `pj` line keeps `tabKey`
   deliberately: `pj` and `npc` share `type === 'character'`, so the tab key is
   the only discriminator, and `character` always resolves in `registry.types`
   -- it is not a crash site.

7. **Give the unresolvable-type case a visible floor.** Replace
   `Sheet.svelte:758-760` (the two closing `{/if}` after the
   `DiscDetailsEditor` block) with, verbatim:

   ```svelte
         {/if}
       {:else}
         <div class="empty">Type inconnu : {type}</div>
       {/if}
     {/if}
   ```

   Fail-visible, not fail-silent: after this brief the only way to reach it is
   a genuinely unknown `sheetType` (a runtime entity type retired while its
   sheet was open), which the creator must see rather than meet as a blank
   panel.

8. **Update the component header comment.** Append to the block that currently
   ends `No scoped <style> block: ...` (`Sheet.svelte:65-66`), before the
   closing `*/`, verbatim:

   ```
      TICKET-0083. The evenements/intrigues branches below are selected by
      `type` (creationState.sheetType), not by `tabKey`: the branch selector
      and the data the branch renders must be the SAME fact, or a tab switch
      can render a record through the generic entity branch and throw on
      registry.types[<tab id>]. `tabKey` survives only where it is genuinely
      the discriminator (pj vs npc, both type 'character') and where it gates
      a sub-editor's visibility, never where it chooses which renderer a
      record gets.
   ```

### Commit 3 -- the lock, the docs, the build

9. **New check: `tooling/verify/checks/creation_tab_switch.py`.** Same idiom as
   `creation_island.py` / `event_tab.py`: module-level `FAILURES` list,
   `fail()`, `_report_and_exit(counts)`, `ROOT` via `parents[3]`, stdlib only,
   no DB, no subprocess, exit 0 on pass / 1 on failure. Every rule
   vacuous-proof: a missing file, a zero-length collection or a zero-count
   scan is a FAILURE, never a trivially satisfied comparison.

   Rules, in this order:

   1. `frontend/src/creation/tabs.js` exists and contains
      `export function showCreationSubTab(tab) {`. Not found -> FAIL.
   2. Inside that function's body (slice from the header offset to the first
      line-initial `}` after it), locate `'creation:sheet-reset'` and
      `creationState.activeTabKey = tab`. Either missing -> FAIL. The reset
      offset must be strictly LESS than the assignment offset, or FAIL.
   3. Count `CustomEvent('creation:sheet-reset'` across every file under
      `frontend/src/`. The count must be exactly 1 and that occurrence must be
      in `creation/tabs.js`. Zero -> FAIL. (Match the DISPATCH form only --
      `Sheet.svelte` legitimately holds an `addEventListener` for the same
      name, and flagging it would be wrong.)
   4. `frontend/src/creation/Sheet.svelte` contains BOTH
      `{:else if type === 'evenements'}` and `{:else if type === 'intrigues'}`,
      and contains NEITHER `{:else if tabKey === 'evenements'}` NOR
      `{:else if tabKey === 'intrigues'}`. Any of the four conditions violated
      -> FAIL. (Match those exact template-branch strings, not bare
      `activeTabKey === 'evenements'`: `Sheet.svelte:321/335/384` read the tab
      key in JS for header/save routing, which stays legal.)
   5. `frontend/src/creation/Sheet.svelte` contains
      `{:else if registry.types[type]}`. Not found -> FAIL.
   6. The identifiers `_entityTabEnterReset`, `_intriguesTabEnterReset` and
      `_evenementsTabEnterReset` appear nowhere in `tabs.js`. Any present ->
      FAIL. Vacuity guard: at least one `onTabEnter:` key must still be found
      in `tabs.js` (npc and lieux keep theirs), or the scan proved nothing ->
      FAIL.

   Module docstring must state, in prose, that rule 2's ordering is the actual
   bug (a reset after the key move is what forced the inconsistent frame) and
   that rule 4 is what stops the frame from being fatal.

10. **CLAUDE.md.** Add one bullet to the existing frontend doctrine block
    (immediately after the `graph_primitive.py` bullet, currently `:320-321`),
    verbatim, wrapped under the 100-character line ceiling:

    ```
    - A Creation sub-tab change clears the entity sheet from the single dispatcher
      (`showCreationSubTab`), BEFORE `activeTabKey` moves and on every change, never per
      registry entry; and `Sheet.svelte` selects its render branch from `sheetType`, the same
      fact that feeds it, never from `activeTabKey` -- enforced by `creation_tab_switch.py`.
    ```

11. **`tooling/standards/ARCHITECTURE_DECISIONS.md`.** Append a new section
    (append-only, never edit an existing one) titled:

    `## THE TAB SWITCH CLEARS THE SHEET BEFORE THE KEY MOVES (BRIEF-0083-a, no schema change)`

    Content: the five-link defect chain with its anchors, the measured
    transition matrix verdict, the two rejected alternatives with their
    measured reasons (per-entry reset kept + assignment moved: fails on the
    seven bespoke tabs; type-gating alone: no crash but the sheet survives
    under a hidden container), and the general rule this establishes -- a
    render branch's SELECTOR and its DATA must be the same fact.

12. **Rebuild and commit the frontend output.** `cd frontend && npm ci &&
    npm run build`, then commit the regenerated
    `src/world_engine/cockpit/static/` in this same commit.
    `frontend_build_fresh.py` and `static_asset_freshness.py` both gate it.

13. **Bump the ticket status.** In
    `tooling/tickets/TICKET-0083-creation-tab-switch-sheet-reset.md`, change
    `status: recon` to `status: exec` in this commit -- and only this commit.
    Reason, load-bearing: `pipeline_state.py` requires EVERY Machine-checkable
    arrow to resolve to an existing file once `status` reaches
    brief/exec/verify/live-gate/done, and `creation_tab_switch.py` does not
    exist until item 9 lands. Bumping earlier would fail the gate; bumping in
    the same commit as the check keeps the ticket gate-green at every point.

## Scope OUT

Named, and each of these was discussed during planning:

- **Every other `activeTabKey` read in `Sheet.svelte`.** The header-sync
  `$effect` (`:321, :335, :347`), `saveSheet`'s evenements routing (`:384`),
  `showGeneratePanel` (`:591-595`), and the `tabKey === 'npc'` sub-editor gates
  (`:700, :732, :738, :748`) all stay exactly as they are. None is a crash
  site; changing them is a behaviour change, and Nia's request is a repair.
- **`EntityList.svelte`'s own `activeTabKey` branches** (`:103, :292, :347,
  :362`). Untouched. Its list recovers as soon as the batch stops aborting --
  measured.
- **De-duplicating the `creation:selection` dispatch.** `creationSelectRecord`
  (`tabs.js:631`), `selectEntity` (`sheetState.svelte.js:119`) and
  `notifySaved` (`:68`) each still dispatch it. Out of scope; only the
  tab-switch site moves.
- **The `pj` / `npc` `type === 'character'` collision.** Resolving it (a real
  discriminator on the sheet instead of a tab-key test) is not this brief.
- **`creationNewEntity` and the dormant `creation:sheet-legacy-active`
  listener** (`tabs.js:551-557`, `Sheet.svelte:257-259`). Dead by current data,
  retained by intent. Do not delete.
- **Extracting anything out of `tabs.js` or `Sheet.svelte`.** Both stay under
  budget after this brief; see STOP S3.
- **Any `.py` file under `src/`.** This brief touches no engine code.
- **Schema, migrations, `world-engine-schema.md`.** Nothing to change.
- **A regression harness in the repo.** The jsdom + Vite harness used for the
  RECON was scratch, not committed. Standing up a frontend test runner is a
  separate ticket, not a rider on a bug fix.

## Invariants to defend

- **"Every Creation page is a `CREATION_TABS` registry entry rendered by the
  generic dispatcher; no page/tab-specific branch exists outside it"**
  (CLAUDE.md, enforced by `page_contract.py`). Item 1 adds NO tab-id literal to
  `showCreationSubTab` -- the hoisted reset is unconditional on the entry.
  Setting six entries' `onTabEnter` to `null` removes per-entry behaviour; it
  does not add a branch.
- **The Creation island seam** (`creation_island.py`, rules 4/5/8/11). No
  container id, no `islands` declaration, no `primaryAction`/`createPanel`
  pairing changes. `mountIsland`'s node-identity no-op is untouched, so no
  island is remounted by this brief and no island loses state on a tab switch.
- **"Inside a `$effect` body, a `$state` binding assigned there must not be
  read afterwards in the same body"** (`effect_self_write.py`). Item 6/7 change
  template conditions only; no `$effect` body is touched.
- **The sheet's single-writer rule** (`state.svelte.js:28-31`: the
  `sheetMode/sheetDetail/sheetIsNew/sheetType` quintet is Sheet.svelte's
  exclusively, set by its own listeners). Item 1 dispatches an EVENT the
  component already owns a listener for; it does not write the quintet from
  `tabs.js`. Do not "simplify" it into a direct assignment.
- **`creationOpenEntityFrom` / `creationReturnToOrigin`** (`tabs.js:581-613`).
  Both call `showCreationSubTab` and then dispatch `creation:select-entity`.
  The hoisted reset runs first, the select overwrites it -- same net result as
  today. The crumb assignment still happens AFTER `showCreationSubTab`, so a
  programmatic navigation keeps its crumb and a manual click clears it. This
  must still hold; `creation_return_nav.py` covers it.

## Done means

Machine-checkable:

- [ ] `python tooling/verify/checks/creation_tab_switch.py` exits 0.
- [ ] The check FAILS when each of these mutations is applied on its own
      (verify by mutating, running, reverting -- all six must fail, none may
      pass):
      (a) move the two hoisted dispatches back below `creationState.activeTabKey = tab`;
      (b) delete the `creation:sheet-reset` dispatch entirely;
      (c) add a second `CustomEvent('creation:sheet-reset'` dispatch in `Sheet.svelte`;
      (d) revert `{:else if type === 'intrigues'}` to `{:else if tabKey === 'intrigues'}`;
      (e) drop the `{:else if registry.types[type]}` guard;
      (f) reintroduce a `function _entityTabEnterReset()` in `tabs.js`.
- [ ] `python tooling/verify/checks/corpus_gate.py` exits 0 (it discovers and
      runs the new check as a sibling; an import failure is a hard failure).
- [ ] `python tooling/verify/run.py --ticket TICKET-0083-creation-tab-switch-sheet-reset`
      exits 0 and reports every arrow resolved.
- [ ] `creation_island.py`, `page_contract.py`, `creation_return_nav.py`,
      `module_budget.py`, `undefined_names.py`, `frontend_build_fresh.py`,
      `static_asset_freshness.py`, `claude_md_contract.py`, `pipeline_state.py`
      all exit 0.
- [ ] `grep -c "_entityTabEnterReset\|_intriguesTabEnterReset\|_evenementsTabEnterReset" frontend/src/creation/tabs.js`
      returns 0.
- [ ] `wc -l frontend/src/creation/tabs.js frontend/src/creation/Sheet.svelte`
      both under 1000.

Live (Nia, in a running cockpit, `$env:WORLD_ENGINE_ENV=prod`):

- [ ] Creation -> Intrigues -> click an intrigue -> click NPC: sidebar shows
      the NPC list, sheet shows "Selectionnez une entite depuis la liste, ou
      creez-en une nouvelle.", header title "Selectionner une entite".
- [ ] Repeat from Intrigues to Lieux, Factions, Objets, Competences, Prompts,
      Review Queue: no frozen content in any of them.
- [ ] Repeat starting from Evenements with an event open.
- [ ] Browser console clean throughout: no
      `Cannot read properties of undefined (reading 'label')`.
- [ ] "+ Nouvelle intrigue" renders the intrigue create panel with header
      "Nouvelle intrigue"; "+ Nouvel evenement" renders the event create panel;
      "+ Nouveau" on NPC / PJ / Factions each render their own panel with the
      correct header.
- [ ] Open an NPC, follow a relation into another tab, use the return crumb:
      the crumb still appears and still returns to the origin entity.

## Docs to update

- `CLAUDE.md` -- one bullet, item 10.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` -- one appended section,
  item 11.
- `world-engine-schema.md` / the schema changelog -- NOT touched. No schema
  change; `schema_version_touched: none` in the ticket.
- `tooling/tickets/TICKET-0083-creation-tab-switch-sheet-reset.md` -- status
  bump only, item 13.
