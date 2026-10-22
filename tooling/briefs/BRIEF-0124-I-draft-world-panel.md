<!-- slug: draft-world-panel -->
# BRIEF 0124-I — "What the world adds, on the sheet -- « Ce que le monde ajoute » in create mode: states, links, same-as, entities to create, sent with the create (A2, G2, H1) (no schema change)"

Lot: LOT-0124-world-premise.md (authoritative on conflict)
Depends on: BRIEF-0124-E (the create body, C-09), BRIEF-0124-G (`draft["world"]`, C-13), BRIEF-0124-H (`germLinkTarget`, `attachGerm`, C-14)

## Anchors to confirm (Mini-RECON)

Halt if any has moved since `main` at `386c01a` (TICKET-0116 merged; AMENDMENT-0124-01 re-based the lot) plus BRIEF-0124-A to H.

- `frontend/src/creation/pendingDrafts.svelte.js:15-45` -> `pendingDraftsState = $state({ knowledge, goals, carrure })`, `resetPendingDrafts()`, `carrureForCreate()`, `knowledgeForCreate()`, `goalsForCreate()`.
- `frontend/src/creation/generatePanel.svelte.js:133-139` -> `export function applyGeneratedDraft(legacyDoc, entityType, result) {` dispatching to `applyLocationDraft`, `applyFactionDraft`, `applyCharacterDraft`, then setting `generatePanelState.status` and `.notes`.
- `frontend/src/creation/Sheet.svelte:98` -> `import { resetPendingDrafts, knowledgeForCreate, goalsForCreate, carrureForCreate } from './pendingDrafts.svelte.js';`; `:117` imports `getPendingCreationMutationId`; `:585-612` -> `submitEntity` building the body with `...(isNewSave && type === 'character' && carrureForCreate() ? { carrure: carrureForCreate() } : {}),` as its last spread; `:815-823` -> the `{#if isNew && type === 'character' && tabKey === 'npc'}` block closing with `{/if}` before `{#if !isNew && ['character', 'faction', 'location', 'item'].includes(type)}`.
- `frontend/src/creation/tabs.js` -> `export async function attachGerm(` (BRIEF-0124-H); `state.svelte.js` -> `germLinkTarget: null` (BRIEF-0124-H).
- `Sheet.svelte` is under 1000 lines (890 on `main`).
- No `frontend/src/creation/DraftWorldPanel.svelte`, no `tooling/verify/checks/draft_panel.py`.

## Facts carried

### R-30 — the entity list and the sheet [M]
Opened: `frontend/src/creation/EntityList.svelte:307-388` (modes `loading, error, flat, lieux, record`); `Sheet.svelte:585-612` (`submitEntity`: the create body `entity, extension, facets, mutation_id, confirm_promotion, link_to, carrure`), `:693` (`isNew`), `:815-823` (the « créés à l'acceptation » knowledge and goals sections, `isNew && type === 'character' && tabKey === 'npc'`), `:832-836` (« États », `!isNew`, `<StatesPanel entityId={detail.id} />`); `pendingDrafts.svelte.js:15-45` (`pendingDraftsState`, `resetPendingDrafts`, `carrureForCreate`, ...); `generatePanel.svelte.js:57-92` (`applyCharacterDraft` fills `pendingDraftsState`), `:133-139` (`applyGeneratedDraft`); `sheetState.svelte.js:109` (`selectEntity`); file sizes: `Sheet.svelte` 890, `EntityList.svelte` 388 lines (frontend cap 1000).
Consequence: the draft's world block rides `pendingDraftsState` and a new component; `Sheet.svelte` gains one import, one section and three body keys.

## Contracts

### C-09 — the create's world extras
Produced by: BRIEF-0124-E   Consumed by: BRIEF-0124-F, I
`EntityWriteBody` gains `states: list[dict] = []` (`{"key": definition_id, "value": choice_id | int | entity_id | None}`), `relations: list[dict] = []` (`{"other_entity_id", "type", "notes": str | None}`), `germs: list[dict] = []` (`{"name", "entity_type", "concept", "link_type"}`). Honoured on create only; a non-empty list on `PUT` is a 422.
`cockpit/crud/entity_extras.py::write_create_extras(db, entity, body) -> dict` runs after `_create_entity_core` and before the route's commit; returns `{"states": n, "relations": n, "germs": [mutation_id, ...]}` and the route adds it to its response under `"world_extras"`. A `ValueError` from a writer, an unknown or system state key, a relation to an entity outside the world or to itself, a non-social type, or a germ type outside `("character", "location", "faction")` is a 422, nothing written (the route rolls back).
- states: `write_attribute_value(db, world_id=entity.world_id, definition_id=key, entity_id=entity.id, value=value, kind="correction", changed_by="creator_crud")`.
- relations: `write_oriented_relations(db, world_id=..., entity_a_id=entity.id, entity_b_id=other_entity_id, type=type, value=50, direction="a_to_b", visible_to_b=False, notes=notes, changed_by="creator_crud")`.
- germs: one `ProposedMutation(world_id=entity.world_id, source_type="creation", mutation_type="entity_creation", status="approved", proposed_by="creator_draft", payload={...C-10 draft germ...}, rationale="coché dans le brouillon de " + entity.name, creator_notes="en attente de réalisation — onglet Création")` each; no FK set (R-20). A germ whose name collides with an active entity, or with an open germ (`_germ_blocked` of `day_concordance.py`, imported), is skipped and named in the response under `"germs_skipped"`.
- `proposal_producers.PRODUCERS["creator_draft"] = ("creator", "Création — germe coché dans un brouillon")`; `PRODUCER_KINDS = ("model", "engine", "auto", "creator")`.

### C-13 — the draft's world block
Produced by: BRIEF-0124-G   Consumed by: BRIEF-0124-I
`draft_world.py`:
- `WORLD_FIELDS: dict[str, str]` for `character`, `location`, `faction` (verbatim in BRIEF-0124-G), appended to `_TYPE_FIELDS[entity_type]` inside `_entity_draft_call`.
- `known_names_block(db, world_id, entity_type, candidate_ids=()) -> str`: « Entités existantes que tu peux nommer (nom exact) : » then one `- {name} ({type label})` line per entity: `candidate_ids` first (in order), then active characters (non-player) by name, then factions by name, then locations by name, skipping repeats, at most `MAX_KNOWN_NAMES = 60` lines; `""` when none.
- `resolve_world_block(db, world_id, entity_type, public_in, draft_name, notes) -> dict` returns `{"states": [...], "links": [...], "same_as": {...} | None, "to_create": [...]}` -- the rules and the shapes are BRIEF-0124-G's case table (Gate (b), table 3).
- `generate_entity_draft(entity_type, brief, db, *, candidate_ids=())` sets `result["draft"]["world"]` (always present, possibly empty lists and `None`).

### C-14 — frontend state for germs, panes and the draft's world block
Produced by: BRIEF-0124-H (germ, panes), BRIEF-0124-I (world draft)   Consumed by: BRIEF-0124-H, I
- `creationState.selectedGermId: null | string`, `creationState.sheetPane: 'fiche' | 'competences'` (default `'fiche'`), `creationState.germLinkTarget: null | { entity_id, name }` (set by « Créer et lier », consumed and cleared by `applyGeneratedDraft`). `selectEntity` and `_creationActivateTab` set `selectedGermId = null`; `_creationActivateTab` sets `sheetPane = 'fiche'` and `germLinkTarget = null`.
- `tabs.js` exports `selectGerm(mutationId)`, `loadGermCandidates(mutationId)`, `attachGerm(mutationId, entityId)`.
- `germPanel` island (`GermPanel.svelte`, container `creation-germ-panel`), declared by `npc`, `lieux`, `factions`.
- `pendingDraftsState.world = { states: [], links: [], sameAs: null, toCreate: [] }`, each list item carrying `checked: boolean`; `resetPendingDrafts` resets it; `worldExtrasForCreate() -> { states, relations, germs }` in the C-09 shapes (checked items only).

## Context

The draft now answers the world (brief G) and the create accepts what Nia
keeps (brief E). This brief is the section between them: she sees each
proposed state, link and entity to create, keeps or drops each one, and the
create carries the kept ones. A « peut-être la même personne » on a germ's
draft is one click from « Rattacher ».

## Scope IN

1. `pendingDrafts.svelte.js`: `pendingDraftsState` gains `world: { states: [], links: [], sameAs: null, toCreate: [] }`; `resetPendingDrafts` resets it; new `export function worldExtrasForCreate()` returning `{ states, relations, germs }` per C-09 from the checked items only: a state -> `{ key, value }`; a link with a non-empty trimmed `type` -> `{ other_entity_id: entity_id, type, notes: note || null }` (a link without a type is not sent); an entity to create -> `{ name, entity_type, concept, link_type }`.
2. `generatePanel.svelte.js`, `applyGeneratedDraft`: after the type's apply, `pendingDraftsState.world` is set from `result.draft.world` (absent -> the empty shape): `states` and `links` each `checked: true`, `toCreate` each `checked: false` (I1: Nia ticks), `sameAs` as given. Then, when `creationState.germLinkTarget` is set, a link `{ entity_id, name, type: '', note: '', checked: true }` is added unless that entity is already linked, and `germLinkTarget` is cleared. `pendingDraftsState` and `creationState` imported where not already.
3. New `frontend/src/creation/DraftWorldPanel.svelte` (no scoped `<style>`; `field-row`, `row-card`, `btn-ghost` classes):
   - « États » -- one row per state: a checkbox bound to `checked`, its name, its label;
   - « Liens » -- one row per link: checkbox, name, a text input bound to `type` (placeholder « élève, rival… », a muted « type requis » when empty), the note;
   - when `sameAs` is set: « Peut-être la même personne que {name}. », and when `getPendingCreationMutationId()` is set, a « Rattacher à {name} » button calling `attachGerm(mutationId, sameAs.entity_id)`, then showing « Rattaché — cette fiche n'est plus nécessaire. » or the error;
   - « À créer ensuite » -- one row per entity to create: checkbox (unchecked by default), name, type, concept, link, and the hint « Coché : un germe l'attend dans « En attente », lié à cette fiche. »;
   - nothing rendered when all four are empty.
4. `Sheet.svelte`: `import DraftWorldPanel from './DraftWorldPanel.svelte';` beside the other panel imports; `worldExtrasForCreate` added to the `:98` import; after the `{/if}` that closes the `:815-823` block, insert
   ```svelte
   {#if isNew && ['character', 'location', 'faction'].includes(type)}
     <div class="field-section"><div class="field-section-title">Ce que le monde ajoute</div>
       <div id="author-world-draft"><DraftWorldPanel /></div>
     </div>
   {/if}
   ```
   In `submitEntity`, after the `carrure` spread: `...(isNewSave && ['character', 'location', 'faction'].includes(type) ? worldExtrasForCreate() : {}),`. After a successful create, when `detail.world_extras?.germs_skipped?.length`, the status element reads « Germe(s) déjà présent(s) : {names} ».
5. Rebuild and commit `src/world_engine/cockpit/static/`.
6. New check `tooling/verify/checks/draft_panel.py` (static, stdlib). Docstring first sentence « G1 check for TICKET-0124 -- the sheet shows what the world adds to a draft and sends what the creator kept. » Rules:
   - **DP1** -- `pendingDrafts.svelte.js` holds `world:` in its state, resets it in `resetPendingDrafts`, exports `worldExtrasForCreate` returning `states`, `relations`, `germs`; `generatePanel.svelte.js`' `applyGeneratedDraft` assigns `pendingDraftsState.world`, sets `toCreate` items `checked: false`, and clears `germLinkTarget`.
   - **DP2** -- `Sheet.svelte` imports `DraftWorldPanel`, renders `<DraftWorldPanel` inside `isNew && ['character', 'location', 'faction'].includes(type)`, spreads `worldExtrasForCreate()` in `submitEntity`; still holds `<StatesPanel entityId={detail.id}` (AC3); `DraftWorldPanel.svelte` holds `attachGerm(` and `getPendingCreationMutationId(`, and none of `alert(`, `confirm(`, `prompt(`.
   A missing file or an empty match is a FAILURE. One `PASS: draft_panel -- ...` line.

## Scope OUT

- The draft's content and its judgment (brief G); the server's writes (brief E).
- Editing a state's value in the panel (keep or drop only; the value is changed after the create in « États »).
- Proposing extras on an existing entity's sheet (create only, C-09).
- The germ panel (brief H).

## Invariants to defend

- **INV-07** -- untouched: knowledge rows keep their own path.
- « Model proposes, code judges » -- the panel shows only what `draft["world"]` resolved; it never sends a name, only ids and the kept germ fields.
- The no-dialog rule -- no `alert`, `confirm`, `prompt` in the new component.

## Decision rights

STOP: a Mini-RECON anchor that does not hold; `Sheet.svelte` would pass 1000 lines; a check reading `Sheet.svelte` (R-29) goes red.
ADAPT: `applyGeneratedDraft`'s three branches return early -> set the world block before the dispatch instead, report.
REPORT-ONLY: wording Nia may want to tune.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/draft_panel.py` -> `PASS`.
- [ ] Named mutations, each turning its rule red, then reverted: default `toCreate` to `checked: true` -> DP1; drop the `worldExtrasForCreate()` spread -> DP2.
- [ ] `attributes.py`, `creation_tab_switch.py`, `page_contract.py`, `npc_skills.py`, `faction_roster_panel.py`, `static_asset_freshness.py`, `module_budget.py` -> `PASS`.
- [ ] Live (Nia): a generated NPC sheet shows « Ce que le monde ajoute » with « Esprit lié »; saving writes the state; a ticked entity to create appears in « En attente » with its link.
- [ ] `/review-step` then `/close-step`.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: `## WHAT THE WORLD ADDS, ON THE SHEET (TICKET-0124) -- DraftWorldPanel.svelte (BRIEF-0124-I, no schema change)` -- keep-or-drop, entities to create unticked by default (I1), the same-as button.
