# LOT — TICKET-0099 "Compétences on the shared list and fiche"

## Objective and cut

Nia's Compétences tab stops showing its system form and its catalogue once it
holds three systems. The cause is a missing container rule (R-01); the ask is
a tab that looks and behaves like every other Création record tab: the list on
the left, one fiche on the right.

The lot first closes the defect class for every single-container tab (A: a
check, and the Registre/Sujets fixes), then moves Compétences onto the shared
editor area as a record tab (B: B1, C1, D2 + H1, E1, R1), then adds the
« + Ajouter un système » shell button (C: G1).

It stops before hiding covered gaps (carried forward), before any change to
the gaps endpoint or the skill endpoints (none is needed, R-15), and before
any generic list-and-fiche component (B3).

## Briefs in this lot

- **A — container sizing** (no schema change): `creation_container_sizing.py`
  (new check, C-08); `#creation-registre`, `#creation-subjects` and a
  transient `#creation-competences` rule in `frontend/public/creation.css`;
  the CLAUDE.md invariant; the decision entry.
- **B — the record tab** (no schema change): `CompetencesList.svelte`,
  `CompetencesSheet.svelte` (new); `competences.svelte.js` rewritten around
  C-01..C-05; `EntityList.svelte` and `Sheet.svelte` gain the competences
  branch; `CREATION_TABS.competences` moves to the editor area; the island
  registry transfer (R1); `Competences.svelte`, its container and its CSS rule
  deleted; `page_contract.py` and `creation_tab_switch.py` extended.
- **C — the add-system button** (no schema change): `secondaryAction` (C-07)
  in `tabs.js`, `Creation.svelte`, `mount.js`, `Sheet.svelte`; system create
  in `competences.svelte.js`; `creation_island.py` rule 11b and
  `page_contract.py` extended.

## Dependency graph

Strictly sequential, A → B → C.

- **A before B: an order imposed by the ticket file, not by the code.** The
  ticket's Machine arrow to `creation_container_sizing.py` must resolve from
  `brief` status on (`pipeline_state.py`, R-18), so the check exists from the
  first brief. Written that early, it must pass on `main`'s tabs, where
  Compétences still owns `#creation-competences` — hence A's transient rule,
  which B deletes with the container. An executor who finds B independent of
  A is not finding a defect.
- C consumes B's C-06 (`blankRecord`, `Sheet.primaryAction`) and B's
  `CREATION_TABS.competences` entry.
- Textual chaining makes the order strict anyway: every brief appends to
  `tooling/standards/ARCHITECTURE_DECISIONS.md`, and B and C both extend
  `page_contract.py`.

## RECON

Opened on `main` at `5784471` (merge of PR #129, `ticket/0098`): corpus
128/128 green, `npm run build` byte-reproducible (only the manifest's
`built_at` moves). Then prototyped on a copy (branch `proto/0099`): every
brief's commit ran the full corpus green (129/129 from A on), the three diffs
replayed in order on a clean worktree reproduce the prototype byte for byte
(generated files regenerated, not diffed), and the tab was driven end to end
in headless Chromium against a scratch database (three systems, two gaps,
forty-two skills). Last, this ticket, this header and the three briefs were
deposited on `main`, each brief's diff was extracted from its own fence and
applied in order: the tree equals the prototype's, and `run.py --ticket
TICKET-0099-competences-list-sheet` is green (13/13 arrows). Findings tagged
[M] were measured, [I] inferred from code read in full.

### R-01 — the height chain's last link [M]
Opened: `frontend/public/shared.css:41` (`.app-view { flex: 1; min-height: 0;
display: flex; flex-direction: column; overflow: hidden; }`);
`frontend/public/creation.css:323-333` (the per-container rules);
`frontend/src/creation/Creation.svelte:235-236` (`#creation-competences`).
Finding: every tab container is a child of `.app-view`. A container with no
rule takes its content's height; `.app-view` clips it and nothing scrolls.
`#creation-competences` has no rule. `Competences.svelte:210-390` stacks four
sections in one column, each system a three-field form (~150 px).
Consequence: the reported symptom. F1 names the rule; B removes the container.

### R-02 — which containers lack a rule [M]
Opened: `frontend/src/creation/tabs.js:188-365` (every `containers:` list);
`frontend/public/creation.css:323-333`.
Finding: 15 entries; `lieux` holds two containers, the other 14 one each.
Three single containers have no rule (enumeration E1, gate (c)):
`creation-competences` (`tabs.js:263`), `creation-registre` (`:300`),
`creation-subjects` (`:331`).
Consequence: A fixes all three; the check makes a fourth impossible.

### R-03 — the queue-panel shape [M]
Opened: `frontend/public/shared.css:81-93` (`.queue-panel { flex: 1;
min-height: 0; display: flex; flex-direction: column; }`, `.queue-body { flex:
1; min-height: 0; overflow-y: auto; … }`); `Queue.svelte:30`,
`Prompts.svelte:206`, `Registre.svelte:138`, `SubjectWorklist.svelte:28` (each
renders `<div class="queue-panel">` at its root); `creation.css:332-333`
(`#creation-queue`/`#creation-prompts { flex: 1; min-height: 0; display: flex;
flex-direction: column; overflow: hidden; }`).
Consequence: Registre and Sujets take that exact rule (a fixed header, a
scrolling body). A's transient Compétences rule scrolls the whole container
instead (`overflow-y: auto`, the `#creation-region` shape, `creation.css:330`),
because its stacked sections are not a queue-body.

### R-04 — what already guards the chain [M]
Opened: `tooling/verify/checks/shell_height_chain.py:71-130` (implementation).
Finding: rule 1 bans `100vh`; rule 2 checks `:global(#app)` and
`.shell-layout` in `App.svelte`. Nothing examines a tab container.
Consequence: `creation_container_sizing.py` (C-08) is new, not an extension.

### R-05 — CSS placement and the build [M]
Opened: `tooling/verify/checks/stylesheet_partition.py:321-336` (rule 2
implementation: a top-level selector in two sheets fails), `:385-400` (rule 6:
`static/creation.css` must byte-match `frontend/public/creation.css`);
`frontend/vite.config.js:1-18` (`outDir: '../src/world_engine/cockpit/static'`,
`emptyOutDir: true`); `frontend/package.json` (`build`: `vite build && node
scripts/write-manifest.mjs`).
Finding: the source of truth is `frontend/public/creation.css`; `npm run build`
copies it into `static/` (measured on the prototype); the three new selectors
are unique.
Consequence: every brief edits `frontend/public/` only and rebuilds.

### R-06 — the record-tab precedent [M]
Opened: `tabs.js:306-326` (`intrigues`, `evenements`: `archetype: 'entity'`,
`containers: ['creation-editor-area']`, `islands: [entityList, entitySheet]`,
`primaryAction` → `triggerPrimaryAction('entitySheet')`); `tabs.js:650-662`
(`creationSelectRecord(tabId, record)`: sets `selectedRecordId = record.id`,
dispatches `'creation:record-detail'` `{record, tabId}` then
`'creation:selection'` `{entityId: null, recordId}`); `tabs.js:675-680`
(`loadPendingCreations` empties the strip for an entry with no `type`).
Finding: a non-entity table already lives on the shared list and fiche twice.
Consequence: B1 is the third instance of an existing shape, not a new one.

### R-07 — the shared list [M]
Opened: `frontend/src/creation/EntityList.svelte` (whole, 377 lines):
`:129-140` (`loadEvents`: `recordsReady = false; mode = 'record'`, fetch,
error → `mode = 'error'`), `:159-176` (`activateTab`, a branch per record tab),
`:186-189` (`'creation:selection'` listener writes `selectedRecordId`),
`:195-197` (`onSelectRecord` → `creationSelectRecord(activeTabKey, record)`),
`:347-377` (record branches gated on `activeTabKey`).
Consequence: B adds a `competences` branch of the same shape and renders a
child component rather than growing this file.

### R-08 — the shared fiche [M]
Opened: `frontend/src/creation/Sheet.svelte` (whole, 762 lines): `:122-129`
(`EMPTY_BODY_BY_TAB`/`EMPTY_TITLE_BY_TAB`, text keyed by tab),
`:180-185` (`enterCreateMode` sets `sheetDetail = {}`), `:205-213`
(`primaryAction()`), `:215-223` (`'creation:sheet-reset'` listener),
`:275-277` (`'creation:record-detail'` → `enterViewMode(record, tabId)`, so
`sheetType` is the tab id), `:310-370` (header effect: title, status, Save),
`:392-393` (`saveSheet`, first line routes evenements), `:437-470`
(`saveEventSheet`'s tail: `creationRefreshList()`, `flushSync(enterViewMode)`,
`'creation:selection'`, status), `:605-633` (branch chain; `{:else if type ===
'intrigues'}` at `:617`).
Consequence: B adds one branch, one save route, one header branch, two text
entries; the fiche body lives in `CompetencesSheet.svelte`.

### R-09 — the branch invariant [M]
Opened: `CLAUDE.md:360-363`; `tooling/verify/checks/creation_tab_switch.py:
171-185` (rule 4 implementation: `{:else if type === 'evenements'}` and
`'intrigues'` present, the `tabKey` forms absent).
Finding: the fiche's render branch is chosen by `sheetType`, never by
`activeTabKey`. An empty fiche has `sheetType = null` (`Sheet.svelte:160-164`,
`:215-223`).
Consequence: H1 — the assistant is a list record, never the empty fiche. B
adds `competences` to rule 4.

### R-10 — the sheet quintet's owner [M]
Opened: `frontend/src/creation/state.svelte.js:25-31` (the quintet
`sheetMode/sheetDetail/sheetIsNew/sheetType/sheetErrorMessage` is Sheet's
alone, "never written from outside"); `intrigues.svelte.js:41-46, 117-121`
(writes `sheetDetail`/`sheetIsNew`/`selectedRecordId` from a module anyway).
Consequence: C-05 — closing a record is an event Sheet listens to; the fiche
edits its record's fields in place but never assigns the quintet. B adds that
sentence to the header of `state.svelte.js`.

### R-11 — the island registry [M]
Opened: `frontend/src/creation/registry.js:18-23` (header: "Nothing is removed
once added"), `:80-284` (`entitySheet`, `origin: 'migration'`,
`retiredPrefixes` ending `'pcApplyDraft',` at `:282`), `:376-393`
(`competences`: container `creation-competences`, component
`Competences.svelte`, 13 retired prefixes);
`tooling/verify/checks/creation_island.py:711-733` (rule 7: every prefix of a
migration entry absent from `legacy.html`), rules 4/5/12 (container exists,
declared by a tab, bound in `mount.js`).
Finding: no check enforces the header's non-removal sentence (enumeration E3).
With B1 the `competences` entry has no container; rules 4, 5 and 12 would fail.
Consequence: R1 — the entry goes, its 13 prefixes move into `entitySheet`,
the header names the exception.

### R-12 — the mount seam [M]
Opened: `frontend/src/creation/mount.js:38` (`import Competences`), `:47`
(`COMPONENTS`), `:130-149` (`triggerPrimaryAction(key)` calls
`instance.primaryAction()`); `tabs.js:78-91` (`setMountActions`, local
`triggerPrimaryAction(key)`); `creation_island.py:734-790` (rule 8: one
definition, imported only by `Creation.svelte`; `action_count` must be 8,
`:1420`), `:889-944` (rule 11: the primary key is read by
`triggerPrimaryAction\(\s*'…'\s*\)` — ONE literal — and the component must
`export function primaryAction(`).
Consequence: G1 passes the variant through the existing function (C-06);
rule 11's one-literal regex keeps matching the primary call; rule 11b is new.

### R-13 — the page contract [M]
Opened: `tooling/verify/checks/page_contract.py:46-49` (`TAB_KEYS` includes
`competences`), `:179-183` (every entry has `primaryAction`), `:297-316`
("Ajouter une compétence" exactly once under `frontend/src/creation/`),
`:331-366` (Intrigues/Événements must be `archetype: 'entity'` on
`creation-editor-area`; `creation-intrigues` must not exist); `Creation.svelte:
91-114` (the shell band renders one primary button).
Consequence: B adds the Compétences twin of `:331-366`; C adds the
`secondaryAction` assertions and the one-occurrence rule for « Ajouter un
système ».

### R-14 — what the tab does today [M]
Opened: `frontend/src/creation/Competences.svelte` (whole, 413 lines);
`competences.svelte.js` (whole, 208 lines).
Finding: systems CRUD with a 409 refusal shown in a dialog; the assistant
(`POST /api/skill-definitions/generate`, drafts REPLACE the current ones,
`:90`); drafts accepted one by one; gaps read-only, a click prefills a draft
with no domain (`:69-71`); skill delete behind « Tapez Oui » (cascade onto PC
skill rows). Two `Modal.svelte` instances (`:392-413`).
Consequence: every behaviour survives in B, re-homed (C-01..C-05); the dialog
texts are kept verbatim.

### R-15 — the endpoints [M]
Opened: `src/world_engine/cockpit/crud/skills.py:157-318` (skill systems and
gaps), `:309-470` (skill definitions).
Finding: GET lists; POST/PUT return the saved row (`_skill_system_dict` with
`skill_count`; `_skill_definition_dict`); 409 on a duplicate name and on
deleting a system with skills; 422 on an empty name or a bad `base_domain`.
Consequence: frontend-only ticket; every save returns what the fiche shows next.

### R-16 — the two tables [M]
Opened: `src/world_engine/models/canon.py:581-630` (`SkillSystem`,
`SkillDefinition`).
Finding: `id` is a `str` uuid on both; unique `(world_id, name)` indexes on
both (`idx_skill_system_world_name`, `idx_skill_definition_world_name`).
Consequence: record ids never collide with the synthetic `draft:<n>` and
`assistant` ids (C-01).

### R-17 — the dialog primitive [M]
Opened: `tooling/verify/checks/modal_primitive.py:1-40` and its scan;
`frontend/src/creation/Modal.svelte:22` (`{ title, open, dismissOnBackdrop,
onClose, body }`).
Consequence: `CompetencesSheet.svelte` reuses `Modal.svelte`; no file builds
its own backdrop.

### R-18 — ticket arrows [M]
Opened: `tooling/verify/checks/pipeline_state.py:108-114` (from `brief` status
on, every Machine arrow must resolve to a file under `tooling/verify/checks/`);
`tooling/verify/run.py:10-23` (`LINK`, `machine_checks`).
Consequence: A creates `creation_container_sizing.py` (dependency graph).

### R-19 — CLAUDE.md [M]
Opened: `CLAUDE.md:20-23` (Stack: "an editor plus a system-grouped
catalogue"), `:129` (Invariants heading), `:360-365`;
`tooling/verify/checks/claude_md_contract.py:1-40` (38 000-character budget,
100-character lines, no `TICKET-`/`BRIEF-` in Invariants). File at 36 280
characters.
Consequence: A adds a three-line invariant; B rewords line 22.

### R-20 — the decision registry [M]
Opened: `tooling/verify/checks/decisions_index.py:14-40` (strict header
pattern for new entries; index must equal a regeneration);
`tooling/glue/gen_decisions_index.py:46-53`; the archive's footer
(`---` / `*Co-built with Claude, June 2026.*`).
Consequence: each brief inserts its entry above the footer and regenerates
`DECISIONS_INDEX.md`.

## Contract sheet

### C-01 — the competences record (family)
Produced by: B   Consumed by: B (list, fiche, save), C
Built only by the factories of `frontend/src/creation/competences.svelte.js`;
always a fresh object, never a row of `competencesState`.
- **skill**: `{ kind: 'skill', persisted, id, draftKey, name, base_domain,
  system_id, description }`. `skillRecord(row)` → `persisted: true`, `id` =
  the uuid, `draftKey: null`. `draftRecord(d)` → `persisted: false`,
  `id: 'draft:<key>'`, `draftKey: d.key`. `blankRecord()` → `persisted:
  false`, `id: null`, `draftKey: null`, `base_domain: 'physical'`.
- **system**: `{ kind: 'system', persisted, id, name, description,
  skill_count }`. `systemRecord(sys)` → `persisted: true`. `blankRecord(
  'system')` (C) → `persisted: false`, `id: null`, `skill_count: 0`.
- **assistant**: `{ kind: 'assistant', persisted: false, id: 'assistant' }`
  from `assistantRecord()`; `ASSISTANT_RECORD_ID = 'assistant'`.
- `persisted` alone decides POST vs PUT, the « Nouvelle/Nouveau » title and
  whether Supprimer shows. `id` is the list identity (`selectedRecordId`).
- `competenceSheetTitle(record)`: assistant → `'Assistant de compétences'`;
  system → name, or `'Nouveau système'`; skill → name, or `'Nouvelle
  compétence'`; `null` → `''`.

### C-02 — the catalogue load
Produced by: B   Consumed by: B (`EntityList.svelte`)
`competencesState = { draft, rows, systems, gaps, arbiterFailures, gapsError,
draftWorldId }`. `loadCatalogue()`: when `draftWorldId !== serverState.worldId`,
empties `draft` and records the world; fetches `/api/skill-definitions` and
`/api/skill-systems` together (throws `Error` on either failure); then
`loadGaps()`, which never throws (its error lands in `gapsError`).
`groupSkillsBySystem(rows, systems)` unchanged (systems by name, always;
trailing no-system group only when non-empty).

### C-03 — drafts
Produced by: B   Consumed by: B
A draft row is `{ key, name, base_domain, system_id, description }`; `key` is a
module counter. `generateDraft(brief)` → `{ok: false, error}` |
`{ok: true, notes}`, REPLACING `draft`. `addGapDraft(surfaceForm)` pushes
`{name: surfaceForm, base_domain: '', system_id: null, description: ''}` and
returns its C-01 record. `discardDraft(key)` removes it.

### C-04 — writes
Produced by: B (skill POST/PUT, system PUT), C (system POST)   Consumed by: B, C
`saveCompetenceRecord(record)` → the saved C-01 record, or throws `Error`:
`'Nom requis.'` (blank name, both kinds), `'Domaine de base requis.'` (skill
whose `base_domain` is not one of `COMPETENCES_DOMAINS`), `'Rien à
enregistrer.'` (any other kind), or the server's `detail`. A skill with a
`draftKey` is removed from `draft` once saved. `deleteSkill(id)`,
`deleteSystem(id)`: DELETE, no reload (the caller refreshes the list).

### C-05 — closing a record
Produced by: B   Consumed by: B (`CompetencesSheet.svelte`)
`closeCompetenceSheet()` dispatches `'creation:record-closed'` (no detail),
then `'creation:selection'` `{entityId: null, recordId: null}` on `document`.
`Sheet.svelte`'s listener sets, under `flushSync`, `sheetMode = 'empty'`,
`sheetDetail = null`, `sheetIsNew = false`, `sheetType = null`.

### C-06 — opening a blank record
Produced by: B (no variant), C (variant)   Consumed by: B, C
`Sheet.svelte`'s `export function primaryAction(variant)`: after
`enterCreateMode(...)`, when `creationState.sheetType === 'competences'`,
`sheetDetail = blankRecord(variant)`. `mount.js`'s
`triggerPrimaryAction(key, variant)` calls `instance.primaryAction(variant)`;
`tabs.js`'s local wrapper forwards both arguments.

### C-07 — `secondaryAction`
Produced by: C   Consumed by: C (`Creation.svelte`, `creation_island.py`,
`page_contract.py`)
A `CREATION_TABS` field `{ label, handler }`, optional. `handler` calls
`triggerPrimaryAction('<key>', '<variant>')` with two string literals, `<key>`
equal to the entry's own routed `primaryAction` key. The shell band renders it
as `<button class="btn-send" id="creation-shell-secondary-action">`, just
before the primary button, only when the entry also has a `primaryAction`.
Compétences: `{ label: '+ Ajouter un système', handler: () =>
triggerPrimaryAction('entitySheet', 'system') }`.

### C-08 — `creation_container_sizing.py`
Produced by: A   Consumed by: B, C (must stay green)
For every `CREATION_TABS` entry whose `containers` list holds exactly one id X,
`frontend/public/creation.css` (comments stripped) holds a rule whose selector
is exactly `#X` declaring `flex: 1` and `min-height: 0`. Entries with two or
more containers are counted, not examined. Zero entries, zero single-container
entries, or an entry with no parseable `containers` is a FAIL.

## Gate output

### (a) Property trace
| property asserted by the lot | finding | declaring file opened |
|---|---|---|
| `.app-view` clips its overflow | R-01 | `frontend/public/shared.css:41` |
| three single containers have no rule | R-02 | `frontend/public/creation.css:323-333`, `tabs.js` |
| `.queue-panel`/`.queue-body` scroll shape | R-03 | `frontend/public/shared.css:81-93` |
| nothing checks a tab container today | R-04 | `shell_height_chain.py` (implementation) |
| `static/creation.css` must equal the public copy | R-05 | `stylesheet_partition.py:385-400` |
| the build copies `public/` into `static/` | R-05 | `frontend/vite.config.js`, prototype build |
| record-detail sets `sheetType` to the tab id | R-06, R-08 | `tabs.js:650-662`, `Sheet.svelte:275-277` |
| `enterCreateMode` leaves `sheetDetail = {}` | R-08 | `Sheet.svelte:180-185` |
| the render branch comes from `sheetType` | R-09 | `CLAUDE.md:360-363`, `creation_tab_switch.py:171-185` |
| an empty fiche has `sheetType = null` | R-09 | `Sheet.svelte:160-164, 215-223` |
| Sheet owns the quintet | R-10 | `state.svelte.js:25-31` |
| rule 7 proves prefixes gone from `legacy.html` | R-11 | `creation_island.py:711-733` |
| no check enforces registry non-removal | R-11, E3 | `creation_island.py` (whole) |
| rule 11 reads ONE literal key | R-12 | `creation_island.py:889-944` |
| `action_count` must equal 8 | R-12 | `creation_island.py:1420` |
| « Ajouter une compétence » exactly once | R-13 | `page_contract.py:297-316` |
| POST/PUT return the saved row, 409s | R-15 | `crud/skills.py:157-470` |
| ids are uuid strings; names unique per world | R-16 | `models/canon.py:581-630` |
| Modal props | R-17 | `Modal.svelte:22` |
| arrows must resolve from `brief` status | R-18 | `pipeline_state.py:108-114` |
| CLAUDE.md budgets and Invariants ban | R-19 | `claude_md_contract.py:1-40` |
| decision header pattern | R-20 | `decisions_index.py:14-40` |

Presupposition sweep: no brief says "follow the convention" without naming the
file and lines; every "same shape as" names its source (`loadEvents`,
`saveEventSheet`, `#creation-queue`, `Competences.svelte:392-413`).

### (b) Case tables

**C-08 over today's registry** (after B):
| entry | containers | examined | rule |
|---|---|---|---|
| npc, pj, factions, objets, intrigues, evenements, competences | `creation-editor-area` | yes | `creation.css:326` |
| lieux | editor-area + `batch-panel-wrap` | no (counted) | — |
| region / constructeur / artefacts | own | yes | `:329-331` |
| registre / subjects | own | yes | added by A |
| queue / prompts | own | yes | `:332-333` |
On `main` + A: competences is `creation-competences`, sized by A's transient
rule; B deletes both.

**C-01 × save/delete/title:**
| record | persisted | Save | title | Supprimer | Retirer |
|---|---|---|---|---|---|
| skill from a row | true | PUT | name | yes | no |
| skill blank | false | POST | Nouvelle compétence | no | no |
| skill draft | false | POST, then draft removed | Nouvelle compétence | no | yes |
| system from a row | true | PUT | name | yes (409 inline if skills) | no |
| system blank (C) | false | POST | Nouveau système | no | no |
| assistant | false | hidden | Assistant de compétences | no | no |

**List sections:** Brouillons (always: assistant row + 0..n drafts); Systèmes
(iff ≥1 system; each system row then its skills indented); Sans système (iff
≥1 skill without a live system); « Aucune compétence propre à ce monde. »
(iff neither of the two); Trous du lexique (always: error, empty text, or
rows); arbiter-failure line (iff either count > 0).

**Rule 11b:**
| secondaryAction | primaryAction | verdict |
|---|---|---|
| absent | any | not examined |
| `triggerPrimaryAction('k', 'v')` | `triggerPrimaryAction('k')` | pass |
| two literals, other key | routed | FAIL (second route) |
| one literal | routed | FAIL (no variant) |
| two literals | null / not routed | FAIL |
| zero paired in the registry | — | FAIL (vacuous) |

### (c) Enumerations

E1 — `creation_container_sizing.py` on `main` + the check alone:
```
FAIL: CREATION_TABS.competences: creation.css has no '#creation-competences' rule — the container takes its content's height and nothing scrolls
FAIL: CREATION_TABS.registre: creation.css has no '#creation-registre' rule — the container takes its content's height and nothing scrolls
FAIL: CREATION_TABS.subjects: creation.css has no '#creation-subjects' rule — the container takes its content's height and nothing scrolls
```
After A and after C: `PASS … 14 single-container entr(y/ies) … 1
multi-container entr(y/ies) not examined`.

E2 — every reference to `creation-competences` outside built assets, on `main`:
```
frontend/src/creation/tabs.js
frontend/src/creation/Creation.svelte
frontend/src/creation/registry.js
```
(B removes all three; A adds, B removes, the CSS rule.)

E3 — `grep -n -i "baseline\|ledger" tooling/verify/checks/creation_island.py`
matches nothing about the island registry; `tooling/verify/baselines/` holds
`decisions_headers.baseline, graph_impls.baseline, graph_impls.retired,
legacy_calls.baseline, legacy_mounts.baseline` — no island baseline.

E4 — « Ajouter un système » under `frontend/src/creation/` after C: one
occurrence, `tabs.js` (the prototype's first draft also had it in a
`competences.svelte.js` comment; the new rule caught it).

E5 — the 13 prefixes moved by R1, verbatim from `registry.js:385-391`:
`_competencesWorldReset, competencesGenerateDraft, _competencesDomainOptions,
competencesRenderDraft, competencesDiscardDraftRow, competencesAcceptDraftRow,
competencesAddManualRow, competencesLoadList, _competencesRenderTable,
competencesSaveRow, competencesDeleteOpen, competencesDeleteConfirm,
COMPETENCES_DOMAINS`.

### (d) Families
✓ C-01 (record kinds) written before the list, the fiche and the save; re-read
after C added `blankRecord('system')`. ✓ C-04 (writes) re-read after C's
system POST.

### (e) Gates and the module that satisfies each
| gate | status | satisfied by |
|---|---|---|
| `creation_container_sizing.py` | proposed (A) | `frontend/public/creation.css` rules |
| `page_contract.py` competences block | proposed (B) | `tabs.js` entry, `Creation.svelte` without the container |
| `creation_tab_switch.py` rule 4 | extended (B) | `Sheet.svelte`'s `type === 'competences'` branch |
| `creation_island.py` rules 4/5/7/12 | passed (B) | `registry.js` transfer, `mount.js` |
| `creation_island.py` rule 11b | proposed (C) | `tabs.js` `secondaryAction` |
| `page_contract.py` secondaryAction | proposed (C) | `tabs.js`, `Creation.svelte` |
| `stylesheet_partition.py` | passed | public edits + rebuild; only existing classes applied |
| `modal_primitive.py` | passed | `CompetencesSheet.svelte` uses `Modal.svelte` |
| `effect_self_write.py` | passed | no new `$effect` writes-then-reads |
| `module_budget.py` | passed | `Sheet.svelte` 821, `EntityList.svelte` 401 lines (cap 1000) |
| `frontend_build_fresh.py` | passed | `npm run build` per brief |
| `claude_md_contract.py` | passed | 3 lines added (A), 1 reworded (B) |
| `decisions_index.py` | passed | regeneration per brief |

## Amendments
