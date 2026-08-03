# BRIEF — Step "continuous route sync + tab-mechanism contract"

Ticket: TICKET-0058. Requires BRIEF-0058-j landed.

## Context

TICKET-0056 made the URL authoritative on ENTRY only, and named the reason:
continuous synchronization would have required the legacy document to call
out to the shell, i.e. an edit to `index.html`, which that ticket refused
(`frontend/src/App.svelte:11-16`; ARCHITECTURE_DECISIONS). The deferral named
this ticket. It is owed here.

Under A1 the legacy document keeps the Creation tab bar for this ticket and
the next, so without sync a deep link degrades on the first click: the user
lands on `/creation/lieux`, clicks "Factions", and the address bar still says
`lieux`. Back and reload then lie.

The mechanism is not new. `graph:slot` (`index.html:4118-4122`) and
`island:slot` (brief -d) already establish one-way legacy -> shell
CustomEvent signalling, with the shell as the only listener and no function
installed on the legacy window. This is a third use of that same channel,
not a new direction of control.

## Scope IN

1. **`index.html` - dispatch, and nothing more.** At the end of
   `showCreationSubTab(tab)` (`index.html:4463`), after the tab has actually
   changed, dispatch
   `document.dispatchEvent(new CustomEvent('route:subtab', { detail: { tab } }))`.
   The legacy document does not touch `history`, does not know the shell's
   route vocabulary, and does not read `location`. Add no tab-id literal -
   `page_contract.py` forbids them in this function and in
   `_creationActivateTab`.

2. **`frontend/src/lib/router.js` - add `replace(surface, subTab)`.** It
   calls `history.replaceState` and dispatches NO `popstate`. This is the
   whole difference from `navigate()` (`router.js:29-33`) and it is
   load-bearing twice over: `pushState` per sub-tab click would make the
   browser Back button walk backwards through sub-tabs one at a time, and
   dispatching `popstate` would re-enter `applyRoute` and drive the legacy
   document from a signal the legacy document just emitted. Say both reasons
   in the comment.

3. **`frontend/src/App.svelte` - listen and replace.** In `onLegacyReady()`,
   register one listener on the legacy document for `route:subtab` that
   calls `replace('creation', detail.tab)` and updates `currentSurface`.
   Guard against re-entrancy: a replacement triggered by the legacy document
   must never call back into `showCreationTab`. Replace the TICKET-0056
   comment at `App.svelte:11-16` with a short statement of what now holds -
   do not leave a comment describing a deferral that has been discharged.

4. **`SHELL_ROUTES` is unchanged.** `/creation/{sub_tab}` already exists in
   both `frontend/src/lib/router.js:10` and `_SHELL_ROUTES`
   (`cockpit/app.py:257`); `legacy_mount.py` assertion 7 compares them as
   ordered lists and must keep passing untouched. The server still never
   learns the tab vocabulary: `{sub_tab}` stays opaque server-side, which is
   what keeps a runtime entity type (TICKET-0046) deep-linkable with no
   backend change.

5. **`page_contract.py` - amend, do not re-home.** Under A1 every target this
   check greps still lives in `index.html`: `CREATION_TABS`
   (`index.html:4274`), `showCreationSubTab`, `_creationActivateTab`,
   `_buildRuntimeCreationTabs` (`7263`), `creationInit` (`7308`) and the
   `#ctab-` markup rule. Nothing moved, so nothing is re-anchored.

   **Correction (BRIEF-0058-e amendment).** The singular `island: { key }`
   field, and the "island XOR legacy, never both" partition this item
   originally specified, are WITHDRAWN — false by design once a container
   holds more than one mount point migrating across separate briefs
   (`#creation-editor-area` holds both `#author-entity-list`, migrated by
   -e, and `#author-main`, migrated by this ticket's later brief). The
   field is now a LIST, `islands: [{ key, containerId }, ...]`, and a
   registry key may be declared by MULTIPLE entries (many-to-many, not a
   bijection) — `creation_island.py` already carries this as of -e, rules 5
   and 9. Do not re-add a partition assertion to `page_contract.py`; either
   assert `creation_island.py` rule 11's pairing (an entry's
   `primaryAction` and `createPanel` must be on the same side — both
   legacy, or both routed through the mounted component) at this new
   locus, or defer to `creation_island.py` and say so explicitly in this
   check's own docstring rather than duplicating the assertion.

6. **Record the count.** Extend `page_contract.py`'s pass line to report how
   many `CREATION_TABS` entries have migrated at least one mount point
   (declare a non-empty `islands`) versus how many render entirely from
   legacy code, so the residual is visible in every verify run until
   TICKET-0059 closes it — counted per ENTRY, not per mount point (an
   entry with both a migrated list and a still-legacy sheet counts once,
   on the "islands" side).

## Scope OUT

- **Sub-tab sync for Play or Observation.** Neither has sub-tabs in the
  shell vocabulary; inventing one would be a route contract change with no
  reader.
- **Moving the tab bar, the dispatcher, or `CREATION_TABS` into Svelte.**
  TICKET-0059 at the earliest.
- **Making the shell the authority on the active sub-tab.** It mirrors; the
  legacy dispatcher decides, exactly as `serverState` mirrors the server
  (`frontend/src/lib/serverState.svelte.js:1-6`).
- **`pushState` per sub-tab.** Explicitly forbidden above.
- **Renaming `index.html`.** Named deferral to TICKET-0061.

## Invariants to defend

- **One direction of control.** No function installed on the legacy window;
  the legacy document signals, the shell listens.
- **`contentWindow` confinement** (`legacy_mount.py` assertion 5) - the new
  listener uses `legacyDocument()` from the bridge, adding no token.
- **The server never learns the tab vocabulary.**
- **Fail-closed over advisory** - the new partition assertion refuses rather
  than warns.

## Done means

- [ ] `python tooling/verify/checks/legacy_mount.py` exits 0.
- [ ] `python tooling/verify/checks/page_contract.py` exits 0 and its pass
      line reports the island/legacy split.
- [ ] On a scratch copy where one entry declares both `island` and a legacy
      `createPanel`, `page_contract.py` exits 1.
- [ ] Live: deep-link `/creation/factions`; the Factions tab opens.
- [ ] Live: click three different sub-tabs in turn; the address bar tracks
      each one.
- [ ] Live: after those three clicks, pressing Back once returns to whatever
      preceded Creation - not to the previous sub-tab.
- [ ] Live: reload on `/creation/<a runtime type slug>` opens that tab.
- [ ] Live: deep-link an unknown sub-tab; the existing `npc` fallback still
      applies (`frontend/src/legacy/bridge.js:94`).
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

None here. Brief -l records the discharged deferral.
