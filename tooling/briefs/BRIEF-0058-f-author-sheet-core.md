# BRIEF — Step "entity sheet: core render/read/save"

Ticket: TICKET-0058. Relies on RECON-0058-a M4, M6, M7. Requires
BRIEF-0058-e landed.

## Context

`authorRenderSheet` (`index.html:7582`) is the shared detail pane for every
entity-archetype tab, static and runtime alike. With `authorRenderField`
(`7497`), `authorReadField` (`7567`) and `_authorSaveSubmit` (`9562`) it is
the field engine that TICKET-0046's `ExtColumnSpec` / `ext_columns_for` /
`form_fields_for` feed. It is also the single largest reason this workstream
exists: authoring-form complexity is what the framework was chosen for.

This brief takes the CORE only - render fields from the server-declared
spec, read them back, save. The sub-editors that hang off the sheet
(geometry, doors, roles, memberships, pricing, subcultures, ledger, items)
are brief -g, and the AI draft path is brief -h. Splitting there is not
arbitrary: the core is the part every tab needs, and it is testable alone
against a type with no sub-editors.

## Scope IN

1. **`frontend/src/creation/Sheet.svelte` + `Field.svelte`.** Port the field
   engine. The field set comes from the server registry
   (`GET /api/entity-types`, TICKET-0046's `form_fields_for`), never from a
   hardcoded per-type list - a column added to a runtime type must appear
   with no frontend edit. Preserve exactly:
   - Per-field rendering by declared type, including the location-type
     classification control and template-modal entry points the sheet
     currently reaches.
   - Read-back semantics: `authorReadField`'s coercion rules move verbatim.
     A silent type change here is a canon corruption with no visible symptom.
   - Save via the existing creator-CRUD endpoints only, unchanged and
     unwidened.
   - Create mode (`authorRenderSheet({}, true, <type>)`) as invoked by every
     entry's `createPanel` and by `_buildRuntimeCreationTabs`
     (`index.html:7263`).

2. **The "Créations en attente" strip.** Move `loadPendingCreations`
   (`index.html:7937`) with the sheet. It stays a registry field
   (`showPendingCreations`), not a tab-id branch (`index.html:4448-4455`).

3. **`index.html`.** `#author-main` becomes a mount container; register the
   island. `entry.createPanel` for migrated entries dispatches through the
   island channel. Delete the ported functions. Runtime tab injection
   (`_buildRuntimeCreationTabs`) must keep producing working entries -
   its `createPanel: () => authorRenderSheet({}, true, slug)` becomes the
   island equivalent, still built by the single factory, never per-type.

4. **`_authorSaveSubmit`'s callers.** `evenementsSave` (`5274`),
   `evenementsSubmitCreate`, `regionCommit` (`6687`) and `batchCommit`
   (`7061`) reach the save path. Until brief -j migrates them, they call it
   through the reverse-direction CustomEvent from brief -d. Enumerate each
   surviving legacy caller in a comment; brief -j deletes the bridge when the
   last one goes.

## Scope OUT

- **Sub-editors**: geometry, doors, roles, memberships, pricing, subculture,
  ledger, items, pending knowledge/goals panels. Brief -g. They keep
  rendering from legacy code into the sheet's slots this step preserves.
- **The AI generate/draft path** (`authorRenderGeneratePanel` `7771`,
  `authorGenerateEntity` `7785`, `authorApply*Draft`). Brief -h.
- **Any new field type, validation rule, or form-state library.** The port
  is a port. If the state model proves inadequate, that is a finding for
  Nia, not a library choice made mid-brief.
- **Widening or adding any endpoint.**
- **`graph_spec_for(entity_type)`.** Still deferred (TICKET-0057 D2).

## Invariants to defend

- **Model proposes, code judges** - the sheet writes only what the creator
  submitted; no field is auto-filled from a model in this step.
- **Single canon-write authority** - creator CRUD direct authority only.
  `single_canon_write.py` must still pass.
- **JSON storage for UI-visible data is prohibited** - `json_ui_boundary.py`
  must still pass; no field may be round-tripped through a JSON blob for
  convenience.
- **Exclusion is structural** - the sheet renders what the server sent; it
  never filters secrets client-side.
- **No structure without a reader** - no prop, no store field, no spec key
  without a consumer in this commit.

## Done means

- [ ] `python tooling/verify/checks/json_ui_boundary.py` exits 0.
- [ ] `python tooling/verify/checks/single_canon_write.py` exits 0.
- [ ] `python tooling/verify/checks/trait_ext_columns.py` and
      `dynamic_ext_crud.py` exit 0.
- [ ] `python tooling/verify/checks/creation_island.py` exits 0, 3 islands.
- [ ] Live: for a character, a location, a faction and a runtime type -
      open an existing record, edit at least three field kinds, save, reload
      the page, confirm persistence.
- [ ] Live: "+ Nouveau" creates a record of each of those four types.
- [ ] Live: a runtime type created in the same session gets a working sheet
      with its declared ext columns.
- [ ] Live: the "Créations en attente" strip appears on exactly the tabs
      that declare `showPendingCreations` and on no others.
- [ ] Live: Evenements and Region still save through the bridged legacy
      path.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

None. Brief -l.
