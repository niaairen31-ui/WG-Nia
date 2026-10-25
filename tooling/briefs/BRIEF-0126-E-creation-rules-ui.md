<!-- slug: creation-rules-ui -->
# BRIEF 0126-E — "Création > Compétences: the creation rules and the overrides"

Lot: LOT-0126-character-creation.md (authoritative on conflict)
Depends on: BRIEF-0126-C

## Anchors to confirm (Mini-RECON)

- `frontend/src/creation/CompetencesList.svelte:50-56` holds the « Rangs »
  head and the `Rangs du monde` item opened by `onSelect(ranksRecord())`.
- `frontend/src/creation/CompetencesSheet.svelte` branches on `rec.kind ===
  'ranks'` (:121), `'assistant'` (:150), `'skill'` (:167), `'system'`
  (:209), and holds `{@render thresholds()}` exactly twice.
- `frontend/src/creation/competences.svelte.js` holds `...pointsBody(record)`
  and `...trialsBody(record)` exactly twice each, `saveCompetenceRecord` at
  :332-338 dispatching `skill`, `system`, `ranks`, and
  `requires_master: !!record.requires_master` in `saveSkill`.
- `GET /api/creation-rules` and `PUT /api/creation-rules` answer C-06's
  shape; `/api/skill-systems` and `/api/skill-definitions` rows carry the
  override fields (brief C).

Halt if any anchor has moved.

## Facts carried

### R-32 -- the Compétences tab
Opened: `frontend/src/creation/CompetencesList.svelte` (130 lines),
`CompetencesSheet.svelte` (253), `competences.svelte.js` (361),
`Sheet.svelte:108, 420-425, 505-525`;
`tooling/verify/checks/rank_trials.py:1040-1070`,
`skill_progression.py:738-752`, `npc_skills.py:600-610`.
Finding: the list's first section is « Rangs » with one record, `Rangs du
monde`, opened by `onSelect(ranksRecord())` (:50-56); the sheet branches on
`rec.kind` (`ranks`, `assistant`, `skill`, `system`) and renders the
`thresholds` snippet once per skill and once per system;
`competences.svelte.js` builds records (`skillRecord`, `systemRecord`,
`ranksRecord`, `draftRecord`, `blankRecord`), titles them
(`competenceSheetTitle`) and saves them (`saveCompetenceRecord`, :332-338)
through `saveSkill`, `saveSystem`, `saveRanks`; `Sheet.svelte` imports
`blankRecord, competenceSheetTitle, saveCompetenceRecord` (:108). Checks
pin: TF1 -- `...trialsBody(record)` and `...pointsBody(record)` each exactly
twice in `competences.svelte.js`; TF2 -- `{@render thresholds()}` exactly
twice in the sheet; C3 -- `Rangs du monde` and `ranksRecord()` in the list,
`rec.kind === 'ranks'` in the sheet, `'/api/skill-ranks', {` in the state;
C2 of `npc_skills.py` -- `bind:checked={creationState.sheetDetail.requires_master}`
in the sheet and `requires_master: !!record.requires_master` in the state.
Consequence: E adds a `creation` record kind, its own component and state
file, and new override fields sent through a new spread
(`...creationOverridesBody(record)`), never through `pointsBody` or
`trialsBody` and never through a third `{@render thresholds()}`; every
needle above survives.
### R-38 -- frontend files the checks read
Opened: the enumeration (c)-5.
Finding: `CompetencesSheet.svelte`, `CompetencesList.svelte` and
`competences.svelte.js` are read by `npc_skills.py`, `rank_trials.py`,
`skill_progression.py`, `page_contract.py` (a comment) and
`graph_primitive.py` (a comment); `Creation.svelte`, `tabs.js`,
`EntityList.svelte`, `registry.js`, `mount.js`, `state.svelte.js` are read
by `creation_layout.py`, `creation_island.py`, `creation_container_sizing.py`,
`page_contract.py`, `creation_tab_switch.py`, `npc_skills.py` and others
listed in (c)-5. No check reads a file under `frontend/src/joueur/` but
`player_shell.py`.
Consequence: no file is moved or renamed in this lot; E and I keep every
pinned needle (R-32, R-33) and re-pin CL1 deliberately (I).
### R-40 -- module budgets of the files this lot edits
Opened: `ast` count and `wc -l` at `fb8557a`;
`tooling/verify/checks/module_budget.py:1-60`.
Finding: caps 1000 physical lines and 40 top-level functions plus methods
for `src/**/*.py`, 1000 lines for `frontend/src/**/*.svelte|js`.
`models/canon.py` 964; `crud/skills.py` 667 lines / 23; `models/pipeline.py`
813; `perspective_selectors.py` 281; `perspective_audit.py` 128;
`lore_render.py` 340; `world_premise.py` 131; `prompt_call.py` 47;
`prompt_registry.py` 488; `writes/worlds.py` 168; `cockpit/app.py` 343 /
12; `routes/player.py` 129; `tabs.js` 890; `EntityList.svelte` 413;
`registry.js` 604; `Creation.svelte` 250; `CompetencesSheet.svelte` 253;
`competences.svelte.js` 361; `joueur.svelte.js` 168; `WorldPage.svelte` 83.
Consequence: `canon.py` cannot take B's columns before A; every other edit
stays far under its cap; `tabs.js` takes at most 15 lines; new logic goes
to new modules.

## Contracts

### C-06 -- the creator's rules routes and the override fields
Produced by: C   Consumed by: E
In `cockpit/crud/skills.py`, on the shared `/api` router:
- `GET /api/creation-rules` -> `rules_dict(world_creation_rules(db,
  world_id))` for the active world (`_world_id`).
- `PUT /api/creation-rules`, body `CreationRulesBody{pool: int, costs:
  list[CreationCostBody{rank: int, cost: int}], caps:
  list[CreationCapBody{rank: int, cap: Optional[int]}], max_rank: int,
  max_master_skills: int, skills_visible: bool}`: costs must list ranks
  1..5 exactly once and caps ranks 0, 2, 3, 4, 5 exactly once (422 `Chaque
  rang est donné une fois.` otherwise), then `write_creation_rules`, commit,
  return the GET shape; `ValueError` -> rollback, 422 with its message.
- `rules_dict(rules) -> dict` lives in `creation_rules.py` (C-03's module):
  `{"pool": int, "costs": [{"rank": 1..5, "cost": int}], "caps": [{"rank":
  r, "cap": int | None} for r in CREATION_CAP_RANKS], "max_rank": int,
  "max_master_skills": int, "skills_visible": bool}`.
- `SkillSystemWriteBody` gains `visible_at_creation: Optional[bool] = None`,
  `max_rank_at_creation: Optional[int] = Field(default=None, ge=1, le=5)`,
  `cap_raised_at_creation: Optional[int] = Field(default=None, ge=0)`,
  `cap_held_at_creation: Optional[int] = Field(default=None, ge=0)`;
  `SkillDefinitionWriteBody` gains the first two. `create_skill_system`,
  `update_skill_system`, `create_skill_definition`,
  `update_skill_definition` set them (a PUT replaces them like every other
  field); `_skill_system_dict` and `_skill_definition_dict` return them.

## Context

The rules and overrides exist and are served (C). This step lets Nia set
them where she sets ranks (X1): a « Création de personnage » record beside
« Rangs du monde », and the override fields on each system and skill sheet,
with the two warnings she accepted (a visible skill's description is read
by the player; a held cap on a system of open skills forces descents).

## Scope IN

1. New `frontend/src/creation/creationRules.svelte.js` (no import of
   `competences.svelte.js`):
   - `export const CREATION_RECORD_ID = 'creation';`
   - `export const creationRulesState = $state({ rules: null });`
   - `export async function loadCreationRules()` -- `GET
     /api/creation-rules` into `creationRulesState.rules`.
   - `export function creationRulesRecord()` -- `{ kind: 'creation',
     persisted: true, id: CREATION_RECORD_ID, ...a deep copy of the rules }`.
   - `export async function saveCreationRules(record)` -- `PUT
     '/api/creation-rules', {` with C-06's body built from the record
     (integers parsed; an empty cap is `null`; a non-integer throws `Error('Un
     coût, un plafond ou la réserve est un nombre entier, au moins 0.')`),
     stores the answer, returns `creationRulesRecord()`.
   - `export function creationOverrides(row)` -- `{visible_at_creation,
     max_rank_at_creation, cap_raised_at_creation, cap_held_at_creation}`
     read from `row` (`null` when absent).
   - `export function creationOverridesBody(record)` -- the same four keys
     for a system record, the first two for a skill record, `null` for
     blanks, integers parsed.
   - `export function inheritedVisible(record, systems, rules)` and
     `inheritedMaxRank(record, systems, rules)` -- the value a blank
     override inherits: a skill reads its system's value when set, then the
     world's `skills_visible` / `max_rank`; a system reads the world's.
2. New `frontend/src/creation/CreationRulesFiche.svelte`, bound to
   `creationState.sheetDetail` (as `CompetencesSheet.svelte` binds its
   records), with these labels verbatim: `Réserve de points`; one input per
   rank 1-5 `Coût pour atteindre {label}`; one input per rank 0, 2, 3, 4, 5
   `Plafond au rang {label}` (placeholder `aucun`); a select `Rang maximal à
   la création` over ranks 1-5; `Compétences qui exigent un maître (au
   plus)`; a checkbox `Compétences visibles à la création par défaut`; and
   the note `Descendre une compétence détenue à {label 0} rend le coût de
   {label 1}.` `{label n}` is `competencesState.ranks[n].label`, passed in
   as a prop (`ranks`), so the file imports nothing from
   `competences.svelte.js`.
3. New `frontend/src/creation/CreationOverrides.svelte`, props `record`,
   `systems`, `ranks`, `rules`; binds `creationState.sheetDetail`: a select
   `Visible à la création` (`hérité (oui|non)` from `inheritedVisible`,
   `Oui`, `Non`); a select `Rang maximal à la création` (`hérité ({label})`
   from `inheritedMaxRank`, then ranks 1-5); for a system record, two
   inputs `Au plus N compétences montées au-dessus de {label 1}` and `Au
   plus N compétences détenues` (blank = no cap). Two warnings, verbatim,
   in the muted style of the sheet's notes: when the record's effective
   visibility is yes, `Visible à la création : le joueur lira son nom et sa
   description tels qu'ils sont écrits.`; on a system record whose held cap
   is set, `Les compétences ouvertes de ce système sont détenues d'office :
   un plafond plus bas oblige le joueur à en descendre, et chaque descente
   lui rend un point.`
4. `CompetencesList.svelte`: under the « Rangs » head, after `Rangs du
   monde`, an item `Création de personnage` (meta `Réserve {pool} · au plus
   {max_master_skills} compétence(s) à maître`) opened by
   `onSelect(creationRulesRecord())`, active when `selectedRecordId ===
   CREATION_RECORD_ID`.
5. `CompetencesSheet.svelte`: a branch `{:else if rec && rec.kind ===
   'creation'}` rendering `<CreationRulesFiche ranks={competencesState.ranks} />`;
   in the `skill` and `system` branches, right after their `{@render
   thresholds()}`, `<CreationOverrides record={rec}
   systems={competencesState.systems} ranks={competencesState.ranks}
   rules={creationRulesState.rules} />`. `{@render thresholds()}` stays
   exactly twice.
6. `competences.svelte.js`: `loadCatalogue` also awaits
   `loadCreationRules()`; `skillRecord`, `systemRecord`, `draftRecord`,
   `blankRecord` spread `...creationOverrides(row)` (null for drafts and
   blanks); `saveSkill` and `saveSystem` bodies add
   `...creationOverridesBody(record)` (exactly two occurrences);
   `saveCompetenceRecord` dispatches `creation` to `saveCreationRules`;
   `competenceSheetTitle` answers `Création de personnage` for it. Every
   needle of R-32 stays.
7. Rebuild (`npm run build` in `frontend/`) and commit the built output.
8. New check `tooling/verify/checks/creation_rules_ui.py` (first sentence:
   « G1 check for TICKET-0126 (BRIEF-0126-E) -- Création > Compétences
   carries the creation rules and the overrides. »), static, stdlib:
   - **CU1** `CompetencesList.svelte` holds `Création de personnage` and
     `creationRulesRecord()`; `CompetencesSheet.svelte` holds `rec.kind ===
     'creation'`, `<CreationRulesFiche`, `<CreationOverrides` twice, and
     `{@render thresholds()}` exactly twice.
   - **CU2** `creationRules.svelte.js` holds `'/api/creation-rules', {`,
     `export function creationOverridesBody(`, `export function
     inheritedVisible(`, `export function inheritedMaxRank(`, and no import
     of `competences.svelte.js`; `competences.svelte.js` holds
     `...creationOverridesBody(record)` exactly twice and still
     `...pointsBody(record)` and `...trialsBody(record)` exactly twice each.
   - **CU3** `CreationRulesFiche.svelte` holds every label of Scope IN 2;
     `CreationOverrides.svelte` names the four override fields and holds
     both warnings verbatim; neither holds `alert(`, `confirm(`,
     `prompt(`.
   - **CU4** the built bundle under `src/world_engine/cockpit/static/assets`
     carries `Création de personnage` and `détenues d'office`.
9. Commits: (1) items 1-6 with the build; (2) the check.

## Scope OUT

- The player's screen (H) and the submitted drafts (I).
- Editing a world's rules from the Monde page.
- A preview of a creation sheet in Création.
- Any change to the ranks record, the thresholds or the trials.

## Invariants to defend

- INV-49 / INV-50: no new tab, no new island -- both components are
  children of `CompetencesSheet.svelte`, mounted through its existing
  island.
- INV-54: the Compétences tab's container sizing is untouched.
- The pinned needles of TF1, TF2, C3 and C2 (R-32).

## Decision rights

STOP:
- An anchor does not hold.
- Keeping a pinned needle of R-32 would require a different design than
  Scope IN (e.g. a third thresholds render).

ADAPT:
- `Sheet.svelte`'s save path needs a kind it does not route: it routes
  through `saveCompetenceRecord` (R-32), so no change; if it filters kinds,
  add `creation` there and report.
- A label exceeds the fiche width: wrap it, keep the text.

REPORT-ONLY:
- Worlds whose ladder renames ranks: every label comes from the ladder.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/creation_rules_ui.py` PASS (CU1-CU4).
- [ ] Named mutations, each turning its rule red, then reverted: CU1 --
      remove the `creation` branch; CU2 -- send the overrides inside
      `pointsBody`; CU3 -- change the held-cap warning's wording; CU4 --
      skip the rebuild.
- [ ] `rank_trials.py`, `skill_progression.py`, `npc_skills.py`,
      `frontend_build_fresh.py`, `page_contract.py`, `creation_island.py`,
      `corpus_gate.py` PASS.
- [ ] Live: open « Création de personnage », change the pool, a cost and the
      Inexpérimenté cap, save, reopen: values held; on a system set
      « Visible à la création » to `Non`, save, reopen: held.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- None beyond the code: the rule file of C already describes the rules.
