# BRIEF — Step "entity list sidebar + return navigation"

Ticket: TICKET-0058. Relies on RECON-0058-a M4, M5, M6, M7. Requires
BRIEF-0058-d landed.

## Context

`#creation-editor-area` (`index.html:1331`) is one container serving every
entity-archetype tab: a sidebar list (`#author-entity-list`,
`index.html:1337`) and a detail pane (`#author-main`, `index.html:1364`).
Under A1 the unit of migration is the container, not the tab - which is why
this one step serves NPC, PJ, Lieux, Factions, Objets, Intrigues, Evenements
and every runtime type at once.

The list migrates before the sheet because it is the smaller half, it owns
the selection state the sheet reads, and it carries the return-navigation
crumb that `creation_return_nav.py` guards. Migrating the sheet first would
have meant a Svelte sheet reading a legacy selection - a state boundary
crossing the seam in the wrong direction for one whole brief.

## Scope IN

1. **`frontend/src/creation/EntityList.svelte`.** Faithful port of
   `creationRenderEntityList` (`index.html:7321`), `authorRenderEntityList`
   (`7355`), `authorLoadEntityList` (`7473`) and `renderLieuxBrowse` (`7409`).
   Behaviour preserved exactly:
   - The default flat renderer selects rows from the loaded entity set using
     the active entry's `type` / `entityFilter`; Lieux uses its own
     hierarchical browse renderer.
   - The NPC-only "Générer les buts manquants" utility control
     (`index.html:7336-7341`) remains a secondary in-body control, NOT a
     second `primaryAction` - the standard shell still renders exactly one.
     It continues to call the legacy `npcGoalsBackfillAll` (`10111`) through
     the reverse-direction CustomEvent established in brief -d until brief
     -j migrates it.
   - Selecting a row publishes the selection; it does not render the sheet.

2. **`frontend/src/creation/state.svelte.js` - the Creation store.** The
   ONLY new shared state this ticket introduces. It holds: the active tab
   key, the loaded entity set, the selected entity id, and the return crumb.
   It is a MIRROR of what the legacy document already decides about the
   active tab - never a second authority. Deliberate contrast with the 175
   legacy globals: one store, one owner per field, each field read by a
   named consumer in this commit or absent (E2).

3. **Return navigation.** Port `creationOpenEntityFrom` (`index.html:9359`),
   `creationReturnToOrigin` (`9380`) and `creationRenderReturnControl`
   (`9392`). The crumb's semantics are load-bearing and must not drift: a
   manual sub-tab click CLEARS it, a programmatic navigation KEEPS it - the
   asymmetry `showCreationSubTab` implements by nulling `creationReturnTo`
   before the helpers re-set it (`index.html:4467-4471`). Under A1 the
   dispatcher is still legacy, so the store subscribes to the same clearing
   signal rather than re-deriving the rule.

4. **`index.html`.** `#author-entity-list` becomes a mount container.
   Register the island in `frontend/src/creation/registry.js` with its
   `retiredPrefix`. Delete the four ported functions and the three
   navigation helpers. `_creationActivateTab`'s call to
   `(entry.listLoader || authorLoadEntityList)()` (`index.html:4437`) becomes
   the `island:slot` dispatch for entries declaring `island`; entries not yet
   migrated keep the legacy call. State the branch as a shape check on the
   entry's own data - never a tab-id check (`page_contract.py` forbids tab-id
   literals in that function).

5. **`creation_return_nav.py` - re-home in this commit.** Re-anchor every
   assertion onto the new locus, preserving the guarantee itself unchanged.
   Zero collected call sites is a failure.

## Scope OUT

- **The sheet / detail pane.** Brief -f. `#author-main` is untouched here
  and continues to render from legacy `authorRenderSheet`.
- **`npcGoalsBackfillAll`, `regionCommit`, `batchCommit`, the faction roster
  rows.** Brief -j.
- **The "Créations en attente" strip** (`loadPendingCreations`,
  `index.html:7937`). It is registry-driven chrome owned by
  `_creationActivateTab`; it moves with the sheet in brief -f.
- **Changing what an entity list SHOWS.** No new column, no new sort, no
  "while we're here" improvement. A port is a port.
- **Retiring `creation` from the legacy mount registry.** TICKET-0059.

## Invariants to defend

- **JSON storage for UI-visible data is prohibited** - the store holds
  fetched rows in memory; nothing new is persisted.
- **No structure without a reader.** Every store field has a named reader in
  this commit.
- **Fail-closed guards never lapse** - `creation_return_nav.py` is re-homed
  here, not later.

## Done means

- [ ] `python tooling/verify/checks/creation_return_nav.py` exits 0 at the
      new locus; on a scratch copy with the crumb-clearing removed, it exits 1.
- [ ] `python tooling/verify/checks/creation_island.py` exits 0, 2 islands.
- [ ] `python tooling/verify/checks/page_contract.py` exits 0.
- [ ] Live: every entity tab lists its own records and no others; Lieux
      still browses hierarchically; a runtime type created in Constructeur
      lists correctly.
- [ ] Live: opening an entity from another surface shows the return control;
      clicking it returns to the origin; clicking a sub-tab manually removes
      the control.
- [ ] Live: switching worlds empties and reloads the list.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

None. Brief -l writes the ticket's decisions once.
