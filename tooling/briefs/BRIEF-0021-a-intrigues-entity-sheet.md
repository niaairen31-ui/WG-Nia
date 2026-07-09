# BRIEF — Step "Intrigues joins the entity archetype (sheetRenderer seam)"

## Context

TICKET-0018 shipped the Intrigues tab as a bespoke registry citizen: its own
container `#creation-intrigues` (index.html:1378-1413), a flat "registre
shape" card list with a collapsible add-form (index.html:3801+). Nia wants
the page to render like her entity pages — the shared `creation-editor-area`
list+detail shell — through the page contract, not through visual accident.
Agendas are not `entity` rows (`agenda`/`agenda_step`/`goal_agenda_link`,
models.py:902-1010), which makes Intrigues the SECOND concrete non-entity
reader of the shell: by minimal-first this finally justifies generalizing
the one hardcoded piece of the shell, the detail-pane renderer. Locked: A1.

## Scope IN

1. **Contract seam `sheetRenderer`** — in the `CREATION_TABS` entry-contract
   comment (index.html, above the const), add exactly this line to the
   entity-archetype-only section:
   ```
   //   sheetRenderer: fn|null (null = authorRenderSheet; renders the
   //                 detail pane for a selected record of this tab)
   ```
   The entity selection path (`authorSelectEntity`) resolves the renderer as
   `(entry.sheetRenderer || authorRenderSheet)` instead of calling
   `authorRenderSheet` directly. Every existing entity tab keeps
   `sheetRenderer` absent/null — zero behaviour change for them.

2. **Generic record selection helper** — add `creationSelectRecord(tabId,
   record)`: looks up the registry entry, invokes
   `(entry.sheetRenderer || authorRenderSheet)` with the record, and marks
   the clicked list row selected (same visual state the entity list uses).
   `authorSelectEntity` keeps its entity-specific fetch/shape logic but
   delegates final rendering through the same resolution — one renderer
   seam, two data shapes, no second dispatcher.

3. **Registry entry rewrite** — `intrigues` becomes:
   ```js
   intrigues: {
     label: 'Intrigues',
     archetype: 'entity',
     containers: ['creation-editor-area'],
     loader: null,
     state: { onTabEnter: _intriguesTabEnterReset, onWorldSwitch: _intriguesWorldReset },
     listLoader: loadAgendasList,
     listRenderer: renderIntriguesListRows,
     sheetRenderer: renderAgendaSheet,
     createPanel: intriguesRenderCreatePanel,
     primaryAction: { label: '+ Nouvelle intrigue', handler: creationNewEntity },
   }
   ```
   `type` is deliberately absent — the tab has no entity type; `listLoader`
   fully replaces the default. Confirm the dispatcher and
   `creationNewEntity` only require `createPanel` (the BRIEF-0005-a shape
   check), not `type`; if any generic path dereferences `entry.type`
   unconditionally, guard it with the same shape-check style (presence
   check), never a tab-id literal.

4. **`loadAgendasList()`** — fetches `/api/agendas` (unchanged endpoint),
   caches rows in a tab-scoped variable (e.g. `intriguesAgendas`), then
   hands them to the generic list container. On fetch failure renders the
   same `.empty` error card the current `loadIntrigues` shows.

5. **`renderIntriguesListRows(agendas)`** — list-pane rows: title (strong),
   owner name muted, owner badge (`personnelle`/`faction`), status badge.
   Row click -> `creationSelectRecord('intrigues', agenda)`. Ordering is
   the API's (active first, newest first) — do not re-sort client-side.

6. **`renderAgendaSheet(agenda)`** — detail pane carrying today's full
   capability set, re-parented from `_intriguesRenderList`:
   - header: title, owner badge + owner name, status badge, and the status
     actions (⏸ abandon with the existing linked-goal `confirm(...)` text
     verbatim, ▶ reactivate) wired to the existing
     `intriguesSetAgendaStatus`;
   - steps section reusing `_intriguesRenderStep` unchanged (✓/✗/▶ via
     `intriguesStepStatus`);
   - linked-goals section reusing `_intriguesRenderLinkedGoal` unchanged
     (detach via `intriguesDetachLink`).
   After any successful status/detach action: re-fetch the agenda list,
   re-render the sheet for the same agenda id (fresh data), keep selection.

7. **`intriguesRenderCreatePanel()`** — the create form moves from the
   collapsible `#intrigues-add-form` into the detail pane (the PJ/NPC
   idiom): owner select (reuse `_intriguesPopulateOwnerSelect`, drop the
   `dataset.loaded` guard so it repopulates per render), title input, five
   step inputs (2 required, 3 optional), « + Créer l'intrigue » calling the
   existing `intriguesSubmitCreate` (adjusted for the new element ids if
   any change; keep ids identical where possible so the submit function is
   untouched). Include an empty placeholder `<div id="agenda-gen-panel">
   </div>` as the FIRST child of the panel — BRIEF-0021-b fills it; this
   brief ships it empty.
   On successful create: refresh list, select the new agenda's sheet.

8. **Demolition** — remove `#creation-intrigues` container and
   `#intrigues-add-form` markup, `intriguesToggleAddForm`, `loadIntrigues`,
   `_intriguesRenderList`. `_intriguesWorldReset` is rewritten to clear the
   agenda cache and selection state; add `_intriguesTabEnterReset` clearing
   selection (the `_entityTabEnterReset` precedent).

9. **`verify/checks/page_contract.py`** — extend, don't relax: if the check
   enumerates permitted entry keys, add `sheetRenderer`; assert the
   `showCreationSubTab` purity rule still holds; assert no
   `creation-intrigues` id survives.

## Scope OUT

- **Editing expansion** — no title edit, no step add/reorder/delete after
  creation, no `visibility_trace` editing. The API surface (PATCH status
  endpoints only) is frozen; the sheet exposes exactly today's actions.
- **A3** — no data-source abstraction for the other bespoke tabs
  (Compétences, Registre, Région, Review Queue, Artefacts). `sheetRenderer`
  is the whole generalization; reactivate A3 only on a third concrete case.
- **The AI panel** — BRIEF-0021-b. Only the empty placeholder div ships
  here.
- **Backend** — zero change to crud.py, writes.py, models.py, or any
  endpoint.
- **C2** — no linked-goal suggestions anywhere.

## Invariants to defend

- **Page contract purity** (TICKET-0005): every Création page renders from
  the registry; `showCreationSubTab` stays a pure lookup — the new seam
  must not reintroduce a tab-id conditional anywhere, including in
  `creationSelectRecord`.
- **G1 state contract**: both `onTabEnter` and `onWorldSwitch` must reset
  ALL state this tab owns (agenda cache, selection, create-form draft).
- **Single canon-write paths**: untouched — this brief writes no canon and
  changes no write code.

## Done means

- [ ] Intrigues tab shows list left / detail right inside
      `creation-editor-area`, visually consistent with the NPC tab
- [ ] Clicking an agenda renders its sheet; ✓/✗/▶ on steps, ⏸/▶ on the
      agenda, and link detach all behave exactly as before the migration
      (including the linked-goal confirm text)
- [ ] "+ Nouvelle intrigue" renders the create panel in the detail pane;
      creating with 2 steps succeeds; step 1 is active; the new agenda's
      sheet is selected
- [ ] Switching the active world clears list, selection, and form
- [ ] `python tooling/verify/run.py` (page_contract check) passes; grep
      confirms no `creation-intrigues` remains
- [ ] /review-step and /close-step run (cockpit code touched)

## Docs to update

- ARCHITECTURE_DECISIONS.md: append a "sheetRenderer seam (TICKET-0021,
  A1)" subsection under the CRÉATION PAGE CONTRACT section — second
  concrete reader justification, A3 explicitly deferred.
- CLAUDE.md: only if it enumerates the entry-contract keys (check; if not,
  no change).
- No schema change; no changelog entry.
