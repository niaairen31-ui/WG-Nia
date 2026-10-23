<!-- slug: creation-germs-and-panes -->
# BRIEF 0124-H — "Nothing stacks in Création -- germs as a group of the list, the germ panel (Générer, Rattacher, Créer et lier), the sheet's « Fiche | Compétences » panes (L1, H1) (no schema change)"

Lot: LOT-0124-world-premise.md (authoritative on conflict)
Depends on: BRIEF-0124-F (the pending item, `candidates`, `attach`, C-11)

## Anchors to confirm (Mini-RECON)

Halt if any has moved since `main` at `386c01a` (TICKET-0116 merged; AMENDMENT-0124-01 re-based the lot) plus BRIEF-0124-A to G.

- `frontend/src/creation/Creation.svelte:178-232` -> `.right-col` holding, in order, the comment and `#creation-pending-strip` (`:182-212`), the `.transcript-panel` with `#author-main` (`:214-225`), `#creation-pj-skill` (`:231`).
- `frontend/public/creation.css:303-304` -> `#creation-pj-skill    { flex-shrink: 0; border-top: 2px solid var(--border);` / `  display: flex; flex-direction: column; max-height: 45%; overflow: hidden; }`.
- `frontend/src/creation/tabs.js:205`, `:225`, `:238`, `:254` -> the `islands:` lines of `npc`, `pj`, `lieux`, `factions` (R-27); `:497` -> `function _creationActivateTab() {`; `:752` -> `export async function generatePendingCreation(mutationId) {`.
- `frontend/src/creation/state.svelte.js:84-88` -> `selectedEntityId`, `selectedRecordId`, `pendingCreations`, `pendingCreationsLoading`, `pendingCreationsError`.
- `frontend/src/creation/sheetState.svelte.js:109` -> `export async function selectEntity(legacyDoc, id) {` whose first line sets `creationState.sheetMode = 'loading'`.
- `frontend/src/creation/registry.js` -> last entry `dashboard` (`:583-588`); `mount.js:48` -> `import Dashboard from './Dashboard.svelte';`, `:50` -> `const COMPONENTS = { ... dashboard: Dashboard };`; `:95` -> islands mount with `props: { legacyDoc: node.ownerDocument }`.
- `frontend/src/creation/EntityList.svelte:311-328` -> the `flat` branch (the npc backfill card, then `genericRows()`); `:329` -> `{:else if mode === 'lieux'}`.
- `grep -rln "creation-pending-strip\|creation-pending-list\|showPendingCreations\|generatePendingCreation\|EntityList.svelte" tooling/verify/checks/` prints nothing; `npc_skills.py:598` holds the needles `key: 'pjSkillFiche'` and `id: 'fiche', containerId: 'creation-pj-skill'`.
- No `frontend/src/creation/GermPanel.svelte`, no `tooling/verify/checks/creation_layout.py`.

## Facts carried

### R-27 — the Création right column [M]
Opened: `frontend/src/creation/Creation.svelte:164-232` (`#creation-editor-area`: the sidebar with `#author-entity-list`; `.right-col` holding `#creation-pending-strip` `:182-212`, the sheet `.transcript-panel` `:214-225` with `#author-main`, and `#creation-pj-skill` `:231`); `frontend/public/creation.css:280-284` (`.right-col` flex column), `:302-304` (`#creation-pj-skill { flex-shrink: 0; border-top: 2px solid var(--border); display: flex; flex-direction: column; max-height: 45%; overflow: hidden; }`); `frontend/public/shared.css:61-67` (`.transcript-panel { flex: 1; min-height: 0; ... }`); `frontend/src/creation/tabs.js:199-218` (`npc`: islands `entityList, entitySheet, npcAgent, linkAgent, pjSkillFiche`; `showPendingCreations: true`; slot `{ id: 'fiche', containerId: 'creation-pj-skill' }`), `:219-231` (`pj`), `:232-247` (`lieux`), `:248-260` (`factions`), `:451-461` (`containerVisible`), `:497-509` (`_creationActivateTab` loads or clears the pending list), `:730-749` (`loadPendingCreations`), `:752-768` (`generatePendingCreation`); `state.svelte.js:84-88` (`selectedEntityId`, `selectedRecordId`, `pendingCreations*`).
Finding: three blocks share one column; the skill sheet never shrinks and takes up to 45 %.
Consequence: L1 (brief H).

### R-28 — the island registry [M]
Opened: `frontend/src/creation/registry.js:481-490` (`pjSkillFiche`, origin `migration`), `:574-588` (`vocabulary`, `dashboard`: origin `new`, `createdBy`); `mount.js:50` (`COMPONENTS`); `tooling/verify/checks/creation_island.py:164` (`NEW_ALLOWED = {"containerId", "component", "origin", "createdBy"}`), `:52-131` (docstring of rule 2: a `new` entry has exactly those fields, `createdBy` matching `^TICKET-\d{4}$`; rule 4: every `containerId` is an element id of `Creation.svelte`; rule 5: every registry key is declared by an `islands` entry and back; rule 13: `Creation.svelte` imports and mounts no component).
Consequence: the germ panel and the world sheet are `new` islands (`germPanel`, `worldSheet`), each in `COMPONENTS`, each declared by the tabs that show it.

### R-29 — checks that read the frontend files this lot edits [M]
Opened: `grep -rln` over `tooling/verify/checks/` for each id and file (Gate (c)); `npc_skills.py:598-604` (shifted 24 lines by TICKET-0116, AMENDMENT-0124-01; C2: `tabs.js`'s `npc` entry contains `key: 'pjSkillFiche'` and `id: 'fiche', containerId: 'creation-pj-skill'`); `attributes.py:680` (AC3: `Sheet.svelte` contains `<StatesPanel entityId={detail.id}`); `creation_tab_switch.py:44-50` (rules 4-5 on `Sheet.svelte`'s branches); `creation_container_sizing.py:16-24` (a single-container entry's `#id` rule declares `flex: 1` and `min-height: 0`); `event_journal.py:678` (regex `\n  vocabulaire: \{(.*?)\n  \},`).
Finding: `creation-pending-strip`, `creation-pending-list`, `showPendingCreations`, `generatePendingCreation`, `EntityList.svelte` and `author-states` are read by no check.
Consequence: brief H keeps both C2 needles and the `<StatesPanel` line; the `monde` entry is a single-container entry (sizing rule applies); the `vocabulaire` entry is not edited.

### R-30 — the entity list and the sheet [M]
Opened: `frontend/src/creation/EntityList.svelte:307-388` (modes `loading, error, flat, lieux, record`); `Sheet.svelte:585-612` (`submitEntity`: the create body `entity, extension, facets, mutation_id, confirm_promotion, link_to, carrure`), `:693` (`isNew`), `:815-823` (the « créés à l'acceptation » knowledge and goals sections, `isNew && type === 'character' && tabKey === 'npc'`), `:832-836` (« États », `!isNew`, `<StatesPanel entityId={detail.id} />`); `pendingDrafts.svelte.js:15-45` (`pendingDraftsState`, `resetPendingDrafts`, `carrureForCreate`, ...); `generatePanel.svelte.js:57-92` (`applyCharacterDraft` fills `pendingDraftsState`), `:133-139` (`applyGeneratedDraft`); `sheetState.svelte.js:109` (`selectEntity`); file sizes: `Sheet.svelte` 890, `EntityList.svelte` 388 lines (frontend cap 1000).
Consequence: the draft's world block rides `pendingDraftsState` and a new component; `Sheet.svelte` gains one import, one section and three body keys.

## Contracts

### C-11 — the germ routes and the pending item
Produced by: BRIEF-0124-F   Consumed by: BRIEF-0124-G, H
- Pending item (`GET /api/creations/pending`): today's keys, with `source` one of `"tick"` (`tick_id`), `"journee"` (`pass_play_id`), `"creation"` (`source_type == "creation"`), `"conversation"` (otherwise), plus `"anchor_name"`, `"source_sentence"`, `"origin_entity_id"`, `"origin_name"`, `"link_type"` (each `None` when absent).
- `germ_candidates(db, mut) -> list[dict]` in `cockpit/routes/creator.py`: for a `character` germ, the active non-player characters whose `current_location_id` is the germ's location (`candidate_location_id`, or for a `creation` germ the origin character's `current_location_id`) or one of its `_location_neighbours`, ordered by name, at most `MAX_GERM_CANDIDATES = 12`; each `{"entity_id", "name", "location_name", "reason"}`, `reason` « au même lieu » or « lieu voisin ». Any other type, or no location: `[]`.
- `GET /api/creations/{mutation_id}/candidates` -> `{"mutation_id", "candidates": [...]}`; 409 when the row is not an approved, unrealized `entity_creation`.
- `POST /api/creations/{mutation_id}/attach` body `{"entity_id"}` -> `{"ok": True, "mutation_id", "entity_id", "name"}`. Guards: the germ as above (409); the entity active, in the germ's world, of the germ's `entity_type` (422). Sets `target_table="entity"`, `target_id=entity_id`, `creator_notes` += « rattaché à une entité existante : {name} », then `_link_entity_creation(mutation_id, entity_id, db)` (which applies and commits); its failure is a 409 with its error.
- `generate_creation_draft` returns the germ's candidates as `"candidates"` (BRIEF-0124-F); BRIEF-0124-G passes their ids to the draft (C-13) and prepends a `creation` germ's origin link.

### C-14 — frontend state for germs, panes and the draft's world block
Produced by: BRIEF-0124-H (germ, panes), BRIEF-0124-I (world draft)   Consumed by: BRIEF-0124-H, I
- `creationState.selectedGermId: null | string`, `creationState.sheetPane: 'fiche' | 'competences'` (default `'fiche'`), `creationState.germLinkTarget: null | { entity_id, name }` (set by « Créer et lier », consumed and cleared by `applyGeneratedDraft`). `selectEntity` and `_creationActivateTab` set `selectedGermId = null`; `_creationActivateTab` sets `sheetPane = 'fiche'` and `germLinkTarget = null`.
- `tabs.js` exports `selectGerm(mutationId)`, `loadGermCandidates(mutationId)`, `attachGerm(mutationId, entityId)`.
- `germPanel` island (`GermPanel.svelte`, container `creation-germ-panel`), declared by `npc`, `lieux`, `factions`.
- `pendingDraftsState.world = { states: [], links: [], sameAs: null, toCreate: [] }`, each list item carrying `checked: boolean`; `resetPendingDrafts` resets it; `worldExtrasForCreate() -> { states, relations, germs }` in the C-09 shapes (checked items only).

## Context

Nia: « les germes, la création et les compétences s'empilent et je vois mal
le texte ». Three blocks share one column (R-27). L1 puts the germs in the
list (as 0099 did for the skills' gaps and drafts), opens one in a panel of
its own, and makes the skill sheet a pane of the sheet. The germ panel is
where H1 lives: « Rattacher » and « Créer et lier ».

## Scope IN

1. `state.svelte.js`: after `pendingCreationsError: ''`, add `selectedGermId: null`, `sheetPane: 'fiche'`, `germLinkTarget: null` with the comment « TICKET-0124 (BRIEF-0124-H, L1/H1): the open germ, the sheet's pane, and the character a « Créer et lier » prepared (C-14). »; the file's header comment lists them.
2. `tabs.js`:
   - the `islands:` arrays of `npc`, `lieux`, `factions` gain `{ key: 'germPanel', containerId: 'creation-germ-panel' }` (last); `pj`'s does not;
   - `_creationActivateTab` sets `creationState.selectedGermId = null; creationState.sheetPane = 'fiche'; creationState.germLinkTarget = null;` as its first lines after the `entry` guard;
   - `generatePendingCreation(mutationId)`: after the `result.ok === false` guard, `creationState.selectedGermId = null; creationState.sheetPane = 'fiche';` before the two dispatches;
   - new exports `selectGerm(mutationId)` (sets `selectedGermId`), `loadGermCandidates(mutationId)` (`api(\`/api/creations/${encodeURIComponent(mutationId)}/candidates\`)` -> its `candidates`), `attachGerm(mutationId, entityId)` (POST `/attach` with `{ entity_id: entityId }`; on success `selectedGermId = null`, `await loadPendingCreations()`, `creationRefreshList()`; returns the response; an error rethrows).
3. `sheetState.svelte.js`, `selectEntity`: first line `creationState.selectedGermId = null;`.
4. `registry.js`: append `germPanel: Object.freeze({ containerId: 'creation-germ-panel', component: 'GermPanel.svelte', origin: 'new', createdBy: 'TICKET-0124' })` with the comment « TICKET-0124 (BRIEF-0124-H, L1/H1): one germ, opened from the list -- created directly as an island, no legacy predecessor. » `mount.js`: `import GermPanel from './GermPanel.svelte';` after `Dashboard`'s, and `germPanel: GermPanel` appended to `COMPONENTS`.
5. New `frontend/src/creation/GermPanel.svelte` (no scoped `<style>`, like `EntityList.svelte`; reuses `row-card`, `badge b-other`, `btn-send`, `btn-ghost`, `field-section`, `field-section-title`). It reads the germ `creationState.pendingCreations.find(g => g.mutation_id === creationState.selectedGermId)` and shows:
   - its name, a badge from `{ tick: 'TICK', journee: 'JOURNÉE', creation: 'BROUILLON', conversation: 'CONVERSATION' }[germ.source]`, its concept, « Lieu : {anchor_name} » when present, « Mentionné ainsi : « {source_sentence} » » when present, « Lié à {origin_name} ({link_type}) » when present; « type inconnu » when `entity_type` is null;
   - a « Générer la fiche » button (`generatePendingCreation(germ.mutation_id)`) when `entity_type` is set;
   - for a `character` germ, a section « C'est quelqu'un qui existe ? »: the candidates loaded by `loadGermCandidates` each time `selectedGermId` changes (name, location, reason), each with « Rattacher » (`attachGerm`) and « Créer et lier » (sets `creationState.germLinkTarget = { entity_id, name }` then `generatePendingCreation`); below them a `<select>` over `creationState.entities` filtered to `type === 'character'` and not in `creationState.playerCharIds`, by name, with the same two buttons; a status line for an error; no `alert`, `confirm` or `prompt`;
   - « Aucun germe sélectionné. » when the germ is not found.
6. `EntityList.svelte`: in the `flat` branch (before the npc backfill card) and the `lieux` branch (first), when `CREATION_TABS[creationState.activeTabKey]?.showPendingCreations` and `creationState.pendingCreations.length`, a group headed « En attente ({n}) »: one `author-list-item` per germ (`active` when it is `selectedGermId`), its name and `{source label} · germe`, `onclick={() => selectGerm(g.mutation_id)}`; `CREATION_TABS` and `selectGerm` imported from `./tabs.js`.
7. `Creation.svelte`:
   - delete `:179-212` (the strip's comment and `#creation-pending-strip`);
   - first child of `.right-col`: the pane bar, shown when `activeEntry?.islands?.some(i => i.key === 'pjSkillFiche')`: `<div class="sheet-pane-bar">` with two `<button class="creation-sub-tab" class:active={creationState.sheetPane === X} onclick={() => { creationState.sheetPane = X; }}>` labelled « Fiche » and « Compétences »;
   - then `<div id="creation-germ-panel" style:display={creationState.selectedGermId ? '' : 'none'}></div>` (empty by construction, the island renders);
   - the `.transcript-panel` gains `style:display={(creationState.selectedGermId || creationState.sheetPane === 'competences') ? 'none' : ''}`;
   - `#creation-pj-skill`'s display becomes `containerVisible('creation-pj-skill') && creationState.sheetPane === 'competences' && !creationState.selectedGermId`.
   The file still imports and mounts no component (rule 13).
8. `frontend/public/creation.css`: `#creation-pj-skill` becomes `{ flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }`; new `#creation-germ-panel { flex: 1; min-height: 0; overflow-y: auto; padding: 16px 20px; }` and `.sheet-pane-bar { flex-shrink: 0; display: flex; gap: 4px; padding: 6px 14px; border-bottom: 1px solid var(--border); background: var(--panel); }` beside the « Création content areas » rules. Rebuild (`cd frontend`, `npm ci`, `npm run build`) and commit `src/world_engine/cockpit/static/`.
9. New check `tooling/verify/checks/creation_layout.py` (static, stdlib, the `creation_container_sizing.py` idiom). Docstring first sentence « G1 check for TICKET-0124 -- nothing stacks in Création's right column: germs are a group of the list, the skill sheet a pane of the sheet. » Rules:
   - **CL1** -- `Creation.svelte` holds no `creation-pending-strip` and no `creation-pending-list`; holds `id="creation-germ-panel"`, the `.sheet-pane-bar` with both labels, and the two display expressions of item 7 (`selectedGermId`, `sheetPane === 'competences'`).
   - **CL2** -- `tabs.js`' `npc`, `lieux`, `factions` entries hold `{ key: 'germPanel', containerId: 'creation-germ-panel' }`, `pj`'s does not; `_creationActivateTab` sets `selectedGermId = null` and `sheetPane = 'fiche'`; `sheetState.svelte.js`' `selectEntity` sets `selectedGermId = null`; `registry.js` holds the `germPanel` entry, `mount.js` the `germPanel: GermPanel` key.
   - **CL3** -- `EntityList.svelte` calls `selectGerm(`; `GermPanel.svelte` holds `/candidates`, `attachGerm(`, `generatePendingCreation(`, `germLinkTarget`, `'JOURNÉE'`, `'BROUILLON'`, and none of `alert(`, `confirm(`, `prompt(`.
   - **CL4** -- `creation.css` (comments stripped): the `#creation-pj-skill` rule declares `flex: 1` and `min-height: 0` and no `max-height`; a `#creation-germ-panel` rule exists.
   A missing file or an empty match is a FAILURE. One `PASS: creation_layout -- ...` line.

## Scope OUT

- The draft's « Ce que le monde ajoute » section and the `germLinkTarget` consumer (brief I).
- The « États » section: it stays inside the Fiche (`Sheet.svelte:832-836`, AC3); no third pane (drafting decision 4).
- `PjSkillFiche.svelte` itself and its slot declaration (C2's needles unchanged).
- The Review Queue, Lieux' graph slot, the agents' panels.
- Any backend change.

## Invariants to defend

- creation_island rules 2, 4, 5, 13 -- the new island is `new` with exactly four fields, its container is an id of `Creation.svelte`, it is declared by tabs, `Creation.svelte` mounts nothing itself.
- stylesheet_partition rule 2 -- the two new selectors exist nowhere else; rule 6 -- the built copies are rebuilt.
- No dialog (the browser rules of this project's sessions): « Rattacher » acts without `confirm`.

## Decision rights

STOP: a Mini-RECON anchor that does not hold; any check other than those of R-29 reads a file this brief edits and goes red; `npm run build` fails for a reason not caused by this brief.
ADAPT: `creation_island.py` requires another registry field for a `new` entry than R-28 records -> follow the check, report; an EntityList branch differs from `:311-329` by a few lines -> place the group at the top of each branch anyway, report.
REPORT-ONLY: visual details (spacing, colour) Nia may want to tune.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/creation_layout.py` -> `PASS`.
- [ ] Named mutations, each turning its rule red, then reverted: restore the strip -> CL1; remove `germPanel` from `factions` -> CL2; add an `alert(` to `GermPanel.svelte` -> CL3; put `max-height: 45%` back -> CL4.
- [ ] `creation_island.py`, `creation_container_sizing.py`, `npc_skills.py`, `attributes.py`, `creation_tab_switch.py`, `page_contract.py`, `stylesheet_partition.py`, `static_asset_freshness.py`, `module_budget.py` -> `PASS`.
- [ ] Live (Nia): the NPC tab shows « En attente » in the list; a germ opens in the right column alone; « Fiche » / « Compétences » switch the column; nothing is cut.
- [ ] `/review-step` then `/close-step`.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: `## NOTHING STACKS IN CRÉATION (TICKET-0124) -- germs in the list, the germ panel, the sheet's panes (BRIEF-0124-H, no schema change)` -- L1, the « États » section kept in the Fiche, H1's two actions. `.claude/rules/frontend.md` only if its registry notes name the strip (they do not on `main`).
