# BRIEF — Step "Modal primitive + artefacts, competences, registre"

Ticket: TICKET-0059. Requires BRIEF-0059-g landed. Reads
SUPPLEMENT-0059-recon-amendments **Amendments 3 and 8**. Cites RECON-0059-a
**M5**, **M7**. Locks: **O1**.

## Context

Three standalone Creation tabs remain untouched, all `archetype: 'bespoke'`
or degenerate-`entity`, each owning its own container and its own legacy
loader:

```
artefacts    1 fn   index.html:5235          container #creation-artefacts   (1399)
competences  12 fns index.html:4245, 4628-4808  container #creation-competences (1406)
registre     6 fns  index.html:4247, 4811-4930  container #creation-registre    (1440)
```

`region` is the precedent to follow exactly (`CREATION_TABS.region`,
`index.html`): `archetype: 'bespoke'`, `loader: null`,
`state.onWorldSwitch: null`, `islands: [{ key: 'region', containerId:
'creation-region' }]`, `primaryAction.handler: () => _islandPrimaryAction('region')`,
and its markup reduced to a single empty div — `index.html:1432` carries the
comment explaining why the container must be **empty by construction**
(Svelte `mount()` appends, it never clears a target's children).

One thing blocks the straight port. `competencesDeleteOpen`
(`index.html:4780`) opens the shared legacy modal with a type-`Oui`-to-confirm
body, a status line and `dismissOnBackdrop: false`, guarding a delete that
irreversibly cascades to every player character's skill row. It is not a
`confirm()`. And `legacy_call.py` rule 4 forbids `Competences.svelte` from
adding a `genericModalOpen` bridge-reach site — correctly, since the seam may
only shrink.

Amendment 3 scheduled `Modal.svelte` for `-l`. Lock **O1** moves it here,
where it gains its first two consumers: `Competences.svelte`, and
`locationType.js`, which already holds the baseline's only two `genericModal*`
records. The legacy `genericModalOpen` / `genericModalClose`
(`index.html:6760`, `6768`) survive for world create (6835) and world delete
(6934) until `-l` deletes them along with the `#generic-modal-backdrop`
markup (7326).

## Scope IN

### Commit 1 — `Modal.svelte`

1. **`frontend/src/creation/Modal.svelte`** — a governed dialog primitive
   reproducing the legacy modal's behaviour exactly. Read `genericModalOpen`
   (`index.html:6760`), `genericModalClose` (6768) and the backdrop markup
   (`index.html:7326-7332`) before writing, including the CSS classes
   `modal-backdrop`, `modal-close` and whatever the inner panel uses.

   Props: `title`, `open`, `dismissOnBackdrop` (default true), and a body
   snippet. Backdrop click closes only when `dismissOnBackdrop` is true and
   the click target is the backdrop itself — the legacy inline handler's
   exact condition. The close button and the backdrop both route through one
   close path.

   **The body is a snippet, not an HTML string.** The legacy modal took
   `bodyHtml` because it had no other option; a Svelte primitive that took a
   string would carry the inline-handler coupling into the new stack.

2. **Migrate `frontend/src/creation/locationType.js`** (lines 46 and 104) off
   `legacyCall('genericModalOpen')` / `legacyCall('genericModalClose')` onto
   `Modal.svelte`. Read the current call sites first: if `locationType.js` is
   a plain module rather than a component, the modal state has to live in
   whichever component owns that flow, and the module returns data rather
   than opening a dialog. State which shape it took in the commit message.

   **Prune the two baseline records** in this commit. Baseline goes 16 -> 14.

3. **No check for `Modal.svelte` in this brief.** The legacy
   `genericModalOpen` is still live with two consumers, so a "one dialog
   implementation" lock cannot pass yet. `-l` lands it when the legacy one
   dies. Do NOT write a check that allow-lists the legacy implementation —
   an allow-list in the same commit as the lock is the escape hatch this
   ticket keeps refusing.

### Commit 2 — artefacts

4. **`frontend/src/creation/Artefacts.svelte`** — port `loadCreationArtefacts`
   (`index.html:5235`) and the `CREATION_ARTEFACTS_NOTICE` constant it
   renders. One function, read-only list, `/api/entities?type=artifact`.

   Preserve the three-state behaviour exactly: rows present -> notice +
   `row-table`; empty response -> notice + `Aucun artefact dans la base.`;
   fetch failure -> notice + `Aucun artefact disponible.` Note that the
   failure branch swallows the error deliberately (`catch (_)`) and still
   shows the notice. Keep that; do not "improve" it into a surfaced error.

5. **Registry.** Add `artefacts` to `CREATION_ISLANDS` and `mount.js`'s
   `COMPONENTS`. In `CREATION_TABS.artefacts`: `loader: null`, keep
   `state.onWorldSwitch: null`, add
   `islands: [{ key: 'artefacts', containerId: 'creation-artefacts' }]`.
   `createPanel` and `primaryAction` stay `null` — preserve the existing
   comment, `enabling artifact creation later = filling this in`.

   Reduce the markup at `index.html:1399-1404` to an empty container with a
   comment matching `#creation-region`'s at 1432.

### Commit 3 — competences

6. **`frontend/src/creation/Competences.svelte`** plus
   **`frontend/src/creation/competences.svelte.js`** for non-render logic —
   port `_competencesWorldReset` (4245), `competencesGenerateDraft` (4628),
   `_competencesDomainOptions` (4656), `competencesRenderDraft` (4662),
   `competencesDiscardDraftRow` (4689), `competencesAcceptDraftRow` (4694),
   `competencesAddManualRow` (4717), `competencesLoadList` (4722),
   `_competencesRenderTable` (4733), `competencesSaveRow` (4758),
   `competencesDeleteOpen` (4780), `competencesDeleteConfirm` (4794).

   The delete dialog consumes `Modal.svelte`. Preserve verbatim: the title
   `Supprimer la compétence`, the two paragraphs including the interpolated
   skill name and the sentence `Elle est irréversible.`, the prompt
   `Tapez Oui pour confirmer.`, the placeholder `Oui`, the button label
   `Supprimer définitivement`, `dismissOnBackdrop: false`, the disabled-until-
   exactly-`Oui` gate (`.trim() !== 'Oui'`), and the in-modal red status line
   that shows the server error without closing the dialog.

7. **Registry.** `loader: null`, `state.onWorldSwitch: null` (the reset moves
   into the component, driven by `serverState.worldId`),
   `islands: [{ key: 'competences', containerId: 'creation-competences' }]`,
   and `primaryAction.handler: () => _islandPrimaryAction('competences')`
   keeping the label `+ Ajouter une compétence`. Reduce the markup at
   `index.html:1406-1439` to an empty container.

### Commit 4 — registre

8. **`frontend/src/creation/Registre.svelte`** — port `_registreWorldReset`
   (4247), `_registrePopulateEntityFilter` (4811), `authorAddLedgerEntry`
   (4830), `registreToggleAddForm` (4868), `loadRegistre` (4873),
   `_registreRenderTable` (4892).

   `authorAddLedgerEntry` is Registre-owned, confirmed by Amendment 8: its
   sole caller is the static button inside the Registre add-form markup. It
   ports here, not with the entity sheet, despite the `author` prefix.

   The two filters (`#registre-filter-entity` select, `#registre-filter-session`
   text input) and the refresh button become component state. Preserve the
   `oninput`-triggered refetch on the session filter — it refetches on every
   keystroke today, and changing that to a debounce is a behaviour change.

9. **Registry.** `loader: null`, `state.onWorldSwitch: null`,
   `islands: [{ key: 'registre', containerId: 'creation-registre' }]`,
   `primaryAction.handler: () => _islandPrimaryAction('registre')` keeping
   `+ Nouvelle entrée`. Reduce the markup at `index.html:1440-1503` to an
   empty container.

### Every commit

10. **Delete each ported function from `index.html`** in the commit that
    replaces it; extend the new island entry's `retiredPrefixes` in
    `registry.js` by name, including the underscore-prefixed helpers and
    `authorAddLedgerEntry`, which no prefix scan for `competences` /
    `registre` / `artefacts` would catch. Add a `BRIEF-0059-h` comment per
    block. Extend `graph_primitive.py`'s `GONE_PLAIN`.

11. **Prune `legacy_calls.baseline`** per commit. Expected net: -2 (the two
    `locationType.js` records in commit 1). If any commit adds a record, it
    has failed — `legacy_call.py` rule 4 will say so.

## Scope OUT

- **Deleting `genericModalOpen` / `genericModalClose` or the
  `#generic-modal-backdrop` markup** (`index.html:6760`, `6768`, `7326`).
  World create (6835) and world delete (6934) still call them. `-l`.
- **A "one dialog implementation" check.** See item 3. `-l`.
- **Migrating world create/delete onto `Modal.svelte`.** They are chrome,
  they need `-l`'s world-CRUD port, and doing them here would leave `-l`
  with a half-moved surface.
- **Replacing the type-`Oui` gate with a `confirm()`.** It guards an
  irreversible cascading delete. The existing `confirm()` calls in
  `RelationsEditor`, `KnowledgeEditor`, `RolesEditor` and `Sheet` are for
  reversible or single-row operations; this is not one of those.
- **Debouncing the registre session filter.** Item 8.
- **Surfacing the artefacts fetch error.** Item 4.
- **`authorAddLedgerEntry`'s write path.** It appends to the ledger through
  an existing route; the ledger is append-only by design and this brief adds
  no edit or delete affordance. The comment at `index.html:4807`
  (`Read-only -- append-only ledger has no edit/delete UI by design`) moves
  with the component.
- **The prompts tab.** `-i`.
- **`role_closed_vocab.py`, `role_capacity_chokepoint.py`.** Backend-only.
  Confirm before assuming; if either greps `index.html`, that is a re-homing
  this brief owns and a deviation to report.
- **Any backend change.** Frontend-only.

## Invariants to defend

- **History is sacred.** The registre is an append-only ledger with no edit
  or delete UI, deliberately. The Svelte port adds neither.
- **Single canon-write authority.** `competencesSaveRow`,
  `competencesAcceptDraftRow`, `competencesDeleteConfirm` and
  `authorAddLedgerEntry` stay on their existing creator-CRUD routes. No new
  endpoint, no coalescing.
- **Model proposes, code judges.** `competencesGenerateDraft` produces draft
  rows the creator accepts one at a time (`competencesAcceptDraftRow`) or
  discards (`competencesDiscardDraftRow`). Nothing in the port may write a
  generated skill definition without that per-row acceptance.
- **The seam only shrinks.** Commit 1 closes two bridge-reach records. No
  commit here may open one; `legacy_call.py` rule 4 enforces it.
- **Assign-then-read is forbidden** (`effect_self_write.py`). Derived lists —
  the domain options, the rendered table rows, the filtered ledger — are
  `$derived`.
- **No structure without a reader (E2).** `Modal.svelte` ships in commit 1
  with two consumers in the same brief. It is not parameterised for the
  world-CRUD consumer that arrives at `-l`.

## Done means

- [ ] `python tooling/verify/checks/legacy_call.py` exits 0 after every
      commit; baseline is 14 records at the end, with both `locationType.js`
      records gone.
- [ ] `python tooling/verify/checks/creation_island.py` exits 0 after every
      commit; scratch: re-add `function competencesLoadList(` and confirm
      rule 7 bites; revert.
- [ ] `python tooling/verify/checks/page_contract.py` exits 0 — the tab
      registry still declares all three tabs and `#ctab-` handling is
      untouched.
- [ ] `grep -c "competencesLoadList\|_registreRenderTable\|loadCreationArtefacts\|authorAddLedgerEntry" src/world_engine/cockpit/index.html`
      returns 0.
- [ ] Each of the three containers is an empty div with an explanatory
      comment, matching `#creation-region` at `index.html:1432`.
- [ ] Live — artefacts: the tab lists artifacts with the notice above them;
      with no artifacts, the empty message shows below the notice.
- [ ] Live — competences: the list renders; `+ Ajouter une compétence` adds a
      manual row; edit and save it; generate a draft, accept one row and
      discard another; the domain select offers the same options as before.
- [ ] Live — competences delete: the modal opens with the same title and
      wording; the button is disabled until exactly `Oui` is typed; clicking
      the backdrop does NOT dismiss it; a server error shows in the modal
      without closing it; a successful delete closes it and refreshes the
      list.
- [ ] Live — the location-type flow that `locationType.js` drives still opens
      and closes its dialog correctly on `Modal.svelte`.
- [ ] Live — registre: the ledger renders; the entity filter and the session
      filter both refetch; `+ Nouvelle entrée` toggles the add form; a credit
      and a debit both post and appear.
- [ ] Live — switch worlds on each of the three tabs; no stale row survives,
      and the competences and registre resets behave as they did under
      `onWorldSwitch`.
- [ ] Live — the primary-action band shows the right label on each tab and
      the dispatcher reaches the right island.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `python tooling/verify/run.py` exits 0.
- [ ] `module_budget.py`, `function_length.py` and `effect_self_write.py`
      pass on every file written.
- [ ] `/review-step` and `/close-step` run per commit.

## Docs to update

None. Brief `-m`, which records the `Modal.svelte` convergence and its lock
once `-l` deletes the legacy implementation.
