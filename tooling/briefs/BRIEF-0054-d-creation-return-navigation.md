# BRIEF — Step "Creation surface: cross-tab entity navigation with return"

## Context

The Creation surface is a list+detail shell driven by `CREATION_TABS`
(`index.html:4253`); there is no notion of open entity tabs, and
`showCreationSubTab` (`index.html:4439`) resets the selected entity on every
tab change via `state.onTabEnter` (`_entityTabEnterReset`,
`index.html:4135-4146`). BRIEF-0054-c gave the faction sheet a grouped roster;
opening a member's sheet from it, and coming back, is decision F2a: double-click
navigates to the member's real editable sheet in its own sub-tab, and a
contextual return control comes back to the faction. One slot, not a stack —
nothing reads a depth greater than one today. The house idiom already exists:
`<- Lieu` (`index.html:1087`).

This step lands in the monolithic `index.html` (decision S1). The split is
Nia's next chantier and must not be pre-empted here.

## Scope IN

1. **One module-level state slot.** Next to `currentCreationSubTab`
   (`index.html:1624`), add:

   ```
   /** Single-slot return crumb (TICKET-0054, decision F2a): where a
    *  programmatic cross-tab entity navigation came FROM. Never a stack —
    *  no reader needs a depth greater than one, and the day one does, this
    *  becomes an array with no other change. Shape: {tabId, entityId}. */
   let creationReturnTo = null;
   ```

2. **`showCreationSubTab` clears the crumb, unconditionally.** Add exactly one
   line, immediately after `currentCreationSubTab = tab;`
   (`index.html:4445`):

   ```
   creationReturnTo = null;  // any tab change drops the crumb; the two
                             // navigation helpers below re-set it AFTER
                             // calling this, which is what makes a manual
                             // sub-tab click clear it and a programmatic
                             // navigation keep it.
   ```

   The function's signature does NOT change and gains no `programmatic` flag.
   The manual-versus-programmatic distinction is expressed purely by call
   ORDER in the two helpers below — the sub-tab buttons
   (`index.html:1211-1224`) call `showCreationSubTab(tab)` with one argument
   and must keep working untouched.

3. **`creationResolveEntityTab(entityId, entityType)`.** Returns the sub-tab id
   that owns an entity, or `null`. Resolution:
   - `entityType === 'character'`: `playerCharIds.has(entityId) ? 'pj' : 'npc'`.
     This is the ONE place a tab id is hardcoded, and it is unavoidable: `npc`
     and `pj` both declare `type: 'character'` and are separated only by
     `entityFilter` against `playerCharIds` (`index.html:4262`, `4273`).
     Carry that reason as a comment, verbatim:

     > `npc` and `pj` both declare type 'character'; `playerCharIds` is the
     > only discriminator the registry exposes, so this pair is resolved by
     > name here rather than by a registry lookup.

   - otherwise: the first `CREATION_TABS` entry with
     `archetype === 'entity'` and `entry.type === entityType`. No other
     hardcoded ids — the doctrine of "no tab-id literals in the dispatcher"
     (`index.html:4438`) holds everywhere else.

4. **`creationOpenEntityFrom(entityId, entityType)`** — async. In order:
   1. `const tab = creationResolveEntityTab(entityId, entityType);`
      if `null`, write `#author-status` with class `author-status err` and
      text `Aucun onglet ne gère ce type d'entité.`, then return. Navigate
      nowhere.
   2. Capture the origin BEFORE moving:
      `const origin = authorEntityId ? { tabId: currentCreationSubTab, entityId: authorEntityId } : null;`
   3. `showCreationSubTab(tab);` — this clears the crumb and runs the target
      tab's `onTabEnter` reset.
   4. Guard: `if (currentCreationSubTab !== tab) return;` — `showCreationSubTab`
      early-returns into `creationInit()` when the registry is not yet loaded
      (`index.html:4474`); in that case abort silently rather than leaving a
      crumb pointing at a tab we never reached.
   5. `creationReturnTo = origin;` — AFTER, deliberately.
   6. `await authorSelectEntity(entityId);`
   7. `creationRenderReturnControl();`

5. **`creationReturnToOrigin()`** — async. In order:
   1. `const back = creationReturnTo; if (!back) return;`
   2. `showCreationSubTab(back.tabId);` — clears the crumb, which is correct:
      returning consumes it.
   3. `if (currentCreationSubTab !== back.tabId) return;`
   4. `await authorSelectEntity(back.entityId);`
   5. `creationRenderReturnControl();`

6. **The return control.** A static button in the sheet panel head, immediately
   after `<h2 id="author-sheet-title">` (`index.html:1365`), mirroring the
   `<- Lieu` precedent (`index.html:1087`):

   ```
   <button class="btn-ghost" id="author-return-btn" onclick="creationReturnToOrigin()"
           style="display:none" title="Retour à l'entité d'origine"></button>
   ```

   `creationRenderReturnControl()` toggles it: hidden when `creationReturnTo`
   is null; otherwise visible with text `<- ` plus the origin entity's name
   looked up in `authorAllEntities` by id, falling back to the origin tab's
   `CREATION_TABS[...].label` when the id does not resolve. The name goes
   through `esc()` and is set via `textContent`, not `innerHTML`.

   Call `creationRenderReturnControl()` at the end of `authorSelectEntity`
   (`index.html:9117-9127`) and at the end of `_entityTabEnterReset`
   (`index.html:4135-4146`). Both call sites are generic — every entity tab
   inherits the control, not just factions.

7. **World switch drops the crumb.** In `_creationRunWorldSwitchResets`
   (`index.html:4504`), add `creationReturnTo = null;` before the per-entry
   `onWorldSwitch` loop. A crumb pointing at an entity of the previous world
   must never survive.

8. **Roster rows become navigable.** In `authorRenderFactionRoster`
   (BRIEF-0054-c), each member row gains
   `ondblclick="creationOpenEntityFrom('<esc entity_id>', 'character')"`,
   `style="cursor:pointer"` on the row container, and
   `title="Double-cliquer pour ouvrir la fiche"`. The `Changer` button and the
   role-edit controls added in BRIEF-0054-c must call
   `event.stopPropagation()` so an action click never also navigates.
   Single click on a row does nothing — navigation is double-click only.

9. **New check `tooling/verify/checks/creation_return_nav.py`.** Anchored from
   `import_cycle.py`'s idiom (`FAILURES`, `_report_and_exit`, `ROOT` via
   `parents[3]`). Text scan of `src/world_engine/cockpit/index.html`, no DB.
   **Collect by function name, never by comment-anchored section slice**
   (TICKET-0043 lesson). Assertions:
   - `creationReturnTo` is declared exactly once at module level
   - `showCreationSubTab` assigns `creationReturnTo = null`
   - inside `creationOpenEntityFrom`, the assignment `creationReturnTo = origin`
     appears AFTER the `showCreationSubTab(` call (index comparison) — the
     ordering IS the mechanism, and reversing it silently breaks the whole
     feature while leaving it looking correct
   - `creationOpenEntityFrom` contains the `currentCreationSubTab !== ` guard
   - `creationResolveEntityTab` references `playerCharIds`
   - `_creationRunWorldSwitchResets` assigns `creationReturnTo = null`
   - `creationReturnTo` is never `.push(`ed onto (it is a slot, not a stack)
   - `authorRenderFactionRoster` contains `ondblclick`

   **Vacuous-proof guard, mandatory:** missing file, or zero assertions
   evaluated because a named function could not be located, is a FAILURE.

## Scope OUT

- **No stack.** `creationReturnTo` holds one origin. No array, no depth, no
  breadcrumb trail. Faction -> NPC -> other faction leaves one crumb, the most
  recent, and that is the decided behaviour (F2a), not a limitation to work
  around.
- **No multi-entity tab bar (F3).** No openable/closable entity tabs, no tab
  strip, no per-entity state retention. This was explicitly refused and is
  coupled to the `index.html` split.
- **No URL, hash, or `history.pushState` integration.** Browser back/forward
  are untouched.
- **No navigation from anywhere other than the faction roster** in this step —
  not from the relation graph, not from the character sheet's Appartenances
  list, not from the Lieux browse. The helpers are generic on purpose so those
  are one-line additions later, but adding them now is out of scope.
- **No change to `showCreationSubTab`'s signature**, no `programmatic` flag, no
  second dispatcher.
- **No modification of `_entityTabEnterReset`'s existing resets** — only the
  appended `creationRenderReturnControl()` call.
- **No modularisation of `index.html`.** No new `<script src>`, no build step.
- **No keyboard shortcut** (Escape, Alt+Left) for the return.

## Invariants to defend

- **Structural over disciplinary.** The manual-click-clears rule is enforced by
  one unconditional assignment inside the dispatcher plus call ordering in the
  helpers — not by remembering to clear the crumb at each call site. The check's
  ordering assertion is what keeps it that way.
- **No structure without a reader.** One slot, because one level of return is
  all anything reads. A stack would be structure with no consumer.
- **Fail-closed over advisory.** Both helpers verify the target tab actually
  activated before selecting, and abort leaving no crumb rather than leaving a
  crumb that points somewhere unreachable.
- **No canon write.** This step writes nothing to the database and touches no
  route. If the executor finds itself adding a fetch, the step has gone out of
  scope.
- **Registry-driven dispatch.** The single hardcoded `npc` / `pj` pair is
  documented in place with its reason. No other tab id is written as a literal
  in the new code.

## Done means

- [ ] Double-click on a member of a faction opens that member's EDITABLE sheet;
      the sub-tab bar shows `NPC` active for an NPC and `Personnage joueur`
      active for a PC
- [ ] The return control appears in the sheet header reading `<- <faction name>`
      and lands back on the faction with its grouped roster loaded
- [ ] After returning, the control is hidden again (the crumb was consumed)
- [ ] Clicking any sub-tab manually while a crumb is pending hides the control;
      no stale return survives
- [ ] Switching worlds while a crumb is pending hides the control
- [ ] Clicking `Changer` on a roster row does NOT navigate
- [ ] Single click on a roster row does nothing
- [ ] The control also appears when navigating from a faction to a member and
      is absent on any sheet reached by normal list selection
- [ ] `python tooling/verify/checks/creation_return_nav.py` exits 0, and exits
      non-zero when the `creationReturnTo = origin` assignment is temporarily
      moved above the `showCreationSubTab(` call
- [ ] Full `/verify` run green; `/review-step` and `/close-step` run

## Docs to update

- `world-engine-schema-changelog.md`: "Schema: none".
- `ARCHITECTURE_DECISIONS.md`: new section
  `## CREATION NAVIGATION — single-slot return crumb (BRIEF-0054-d, no schema change)`
  recording F2a, why the crumb is a slot and not a stack, the call-ordering
  mechanism (and that reversing the order is the failure mode the check
  guards), the documented `npc`/`pj` exception to registry-driven resolution,
  and the explicit refusal of F3 pending the `index.html` split.
- `DECISIONS_INDEX.md`: one row for the new section.
- `CLAUDE.md`: no change.
