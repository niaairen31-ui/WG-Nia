<!-- slug: competences-record-tab -->
# BRIEF 0099-B — "Compétences on the shared list and fiche"

Lot: LOT-0099-competences-list-sheet.md (authoritative on conflict)
Depends on: BRIEF-0099-A (C-08 must stay green; its transient `#creation-competences` rule is deleted here)
Commit header for decisions: `(BRIEF-0099-b, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0099`, on the tree BRIEF-0099-A left, before applying anything. Halt if one has moved.

- `frontend/src/creation/Competences.svelte` → exists, 413 lines; `frontend/src/creation/CompetencesList.svelte` and `CompetencesSheet.svelte` → do not exist
- `frontend/src/creation/tabs.js:260-268` → the `competences:` entry with `archetype: 'bespoke'`, `containers: ['creation-competences']`, `islands: [{ key: 'competences', containerId: 'creation-competences' }]`, `primaryAction: { label: '+ Ajouter une compétence', handler: () => triggerPrimaryAction('competences') }`
- `frontend/src/creation/registry.js:23` → `   Nothing is removed once added, whichever the origin.`; `:282` → `      'pcApplyDraft',` (last prefix of `entitySheet`); `:379` → `  competences: Object.freeze({`
- `frontend/src/creation/mount.js:38` → `import Competences from './Competences.svelte';`; `:47` → the `COMPONENTS` line containing ` competences: Competences,`
- `frontend/src/creation/Creation.svelte:236` → `  <div id="creation-competences" style:display={containerVisible('creation-competences') ? '' : 'none'}></div>`
- `frontend/public/creation.css:336` → `#creation-competences { flex: 1; min-height: 0; overflow-y: auto; }`
- `frontend/src/creation/Sheet.svelte:101` → `  import Intrigues from './Intrigues.svelte';`; `:205` → `  export function primaryAction() {`; `:275` → `  legacyDoc.addEventListener('creation:record-detail', (ev) => {`; `:392-393` → `  async function saveSheet() {` then the `evenements` route; `:617` → `    {:else if type === 'intrigues'}`
- `frontend/src/creation/EntityList.svelte:57` → `  import { loadAgendas } from './intrigues.svelte.js';`; `:159` → `  function activateTab(tabKey) {`
- `frontend/src/creation/state.svelte.js:28-31` → the quintet sentence ending `never written from outside that component).`
- `tooling/verify/checks/creation_tab_switch.py:73` → `RETIRED_IDENTS = (...)`; `:171` → `def _rule4_type_gated(sheet_src: str) -> bool:`
- `tooling/verify/checks/page_contract.py:300` → `    # added to Competences.svelte would still be caught as a duplicate.`; `:368` → `    if failures:`
- `CLAUDE.md:22` → `  Creation's Compétences tab reads \`skill_system\`: an editor plus a system-grouped catalogue;`

## Facts carried

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

### R-19 — CLAUDE.md [M]
Opened: `CLAUDE.md:20-23` (Stack: "an editor plus a system-grouped
catalogue"), `:129` (Invariants heading), `:360-365`;
`tooling/verify/checks/claude_md_contract.py:1-40` (38 000-character budget,
100-character lines, no `TICKET-`/`BRIEF-` in Invariants). File at 36 280
characters.
Consequence: A adds a three-line invariant; B rewords line 22.

## Contracts

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
*(This brief lands the no-variant half: `primaryAction()` and
`blankRecord()`. BRIEF-0099-C adds the parameter.)*

## Context

After A, the Compétences tab scrolls again but is still a single column of inline forms (R-14). Nia locked B1: the tab becomes the fourth record tab on the shared editor area (R-06), with the list grouped by system (C1), drafts, the assistant and gaps as list sections (D2 + H1), and the shell's Save button (E1).

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed. The deletion
of `Competences.svelte` is not in the diff either (item 2).

1. Apply the embedded diff. It:
   - rewrites `frontend/src/creation/competences.svelte.js` around C-01..C-05 (the factories, `loadCatalogue`, drafts, `saveCompetenceRecord`, deletes, `closeCompetenceSheet`);
   - creates `frontend/src/creation/CompetencesList.svelte` (the four list sections) and `frontend/src/creation/CompetencesSheet.svelte` (the fiche for each `kind`, the two `Modal.svelte` dialogs with R-14's texts);
   - `EntityList.svelte`: `loadCompetenceRecords` (the `loadEvents` shape), the `competences` branch in `activateTab`, the record branch rendering `<CompetencesList onSelect={onSelectRecord} />`;
   - `Sheet.svelte`: the `type === 'competences'` render branch, the `'creation:record-closed'` listener (C-05), the header-effect branch and `saveCompetenceSheet` (both selected by `sheetType`), `blankRecord()` after `enterCreateMode` in `primaryAction`, the two empty-state texts;
   - `tabs.js`: `CREATION_TABS.competences` as an `archetype: 'entity'` record tab on `creation-editor-area` with the `entityList`/`entitySheet` islands, `createPanel: null`, primary action routed to `'entitySheet'`;
   - `registry.js`: the `competences` entry removed, its 13 prefixes appended to `entitySheet` (E5), the header's named exception (R1);
   - `mount.js`: the `Competences` import and `COMPONENTS` key removed; `Creation.svelte`: the `#creation-competences` container removed; `frontend/public/creation.css`: A's transient `#creation-competences` rule removed;
   - `state.svelte.js`: the sentence on in-place record edits and `'creation:record-closed'`;
   - `page_contract.py`: the Compétences twin of the Intrigues/Événements assertions; `creation_tab_switch.py`: rule 4 over `RECORD_TABS = ("evenements", "intrigues", "competences")`;
   - `CLAUDE.md:22` reworded; the decision entry above the footer.
2. Delete the old component: `git rm frontend/src/creation/Competences.svelte`.
3. Rebuild and stage the static output: `cd frontend && npm ci && npm run build`.
4. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
5. Named mutations, each run then restored with `git checkout -- <file>` before committing:
   - in `Sheet.svelte`, change `{:else if type === 'competences'}` to `{:else if tabKey === 'competences'}` → `creation_tab_switch.py` prints both `missing "{:else if type === 'competences'}"` and `stale "{:else if tabKey === 'competences'}"` and exits 1;
   - in `tabs.js`, change the competences entry's `archetype: 'entity'` to `archetype: 'bespoke'` → `page_contract.py` prints `FAIL: CREATION_TABS.competences is not archetype: 'entity' (BRIEF-0099-b)`.
6. Commit message: `feat(creation): Compétences on the shared list and fiche (BRIEF-0099-b)`.

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index 9751f7b..ca0d0b2 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -19,7 +19,7 @@ and `world-engine-schema-changelog.md` — never here.
   alone stays legacy (`/legacy`, one governed iframe, `cockpit/legacy.html`), sealed rather than
   migrated by TICKET-0061, until its own ticket (TICKET-0069). No new dependency without a
   decision.
-  Creation's Compétences tab reads `skill_system`: an editor plus a system-grouped catalogue;
+  Creation's Compétences tab reads `skill_system`: a list grouped by system beside one fiche;
   `Sans système` is a rendered group, never a stored row (TICKET-0084).
 - Local models via Ollama; Claude API reserved for heavy lore-coherence work.
 - Runtime: Windows / PowerShell — `.venv\Scripts\Activate.ps1`,
diff --git a/frontend/public/creation.css b/frontend/public/creation.css
index dc17cbd..13269c0 100644
--- a/frontend/public/creation.css
+++ b/frontend/public/creation.css
@@ -333,7 +333,6 @@ input.notes::placeholder { color: var(--muted); }
 #creation-prompts     { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
 #creation-registre    { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
 #creation-subjects    { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
-#creation-competences { flex: 1; min-height: 0; overflow-y: auto; }
 
 /* ── Région review tree (BRIEF-36) ───────────────────────────────────────── */
 .review-node   { border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; margin: 6px 0; }
diff --git a/frontend/src/creation/CompetencesList.svelte b/frontend/src/creation/CompetencesList.svelte
new file mode 100644
index 0000000..19d23cd
--- /dev/null
+++ b/frontend/src/creation/CompetencesList.svelte
@@ -0,0 +1,121 @@
+<script>
+  /* TICKET-0099 (BRIEF-0099-b, C1 + D2 + H1). The Compétences list, rendered
+     by EntityList.svelte in its record mode inside #author-entity-list --
+     the same sidebar every entity tab uses. It never opens a fiche itself:
+     every click hands a C-01 record to `onSelect`, which is EntityList's
+     own onSelectRecord (creationSelectRecord, tabs.js), so the fiche opens
+     through the one record path intrigues/evenements already use.
+
+     Four sections, top to bottom:
+       Brouillons       -- the assistant entry (H1), then every draft row.
+       Systèmes         -- each system is a row of its own (its fiche), its
+                           skills indented under it (C1).
+       Sans système     -- skills with no live system, only when non-empty.
+       Trous du lexique -- read-only gaps (BRIEF-0084-d); a click creates a
+                           draft named after the gap and opens it.
+
+     No scoped <style> block: every class here is already styled by
+     frontend/public/creation.css / shared.css (EntityList.svelte applies
+     the same ones). */
+  import { creationState } from './state.svelte.js';
+  import {
+    competencesState, NO_SYSTEM_LABEL, ASSISTANT_RECORD_ID, groupSkillsBySystem,
+    skillRecord, systemRecord, draftRecord, assistantRecord, addGapDraft,
+  } from './competences.svelte.js';
+
+  let { onSelect } = $props();
+
+  const groups = $derived(groupSkillsBySystem(competencesState.rows, competencesState.systems));
+  const systemGroups = $derived(groups.filter((g) => g.system));
+  const unassigned = $derived(groups.find((g) => !g.system));
+
+  function onKey(ev, record) {
+    if (ev.key === 'Enter') onSelect(record);
+  }
+
+  function openGap(surfaceForm) {
+    onSelect(addGapDraft(surfaceForm));
+  }
+
+  function fmtDate(iso) {
+    if (!iso) return '—';
+    try {
+      return new Date(iso).toLocaleString(undefined, { dateStyle: 'short', timeStyle: 'short' });
+    } catch {
+      return iso;
+    }
+  }
+</script>
+
+<div class="lieux-bucket-head">Brouillons</div>
+<div class="author-list-item {creationState.selectedRecordId === ASSISTANT_RECORD_ID ? 'active' : ''}"
+     role="button" tabindex="0"
+     onclick={() => onSelect(assistantRecord())} onkeydown={(ev) => onKey(ev, assistantRecord())}>
+  <div class="ali-name">✦ Générer avec l'assistant</div>
+  <div class="ali-meta">Proposer des compétences à partir d'une intention</div>
+</div>
+{#each competencesState.draft as d (d.key)}
+  <div class="author-list-item {creationState.selectedRecordId === `draft:${d.key}` ? 'active' : ''}"
+       role="button" tabindex="0"
+       onclick={() => onSelect(draftRecord(d))} onkeydown={(ev) => onKey(ev, draftRecord(d))}>
+    <div class="ali-name">{d.name || '(sans nom)'}</div>
+    <div class="ali-meta"><span class="badge b-other">brouillon</span> {d.base_domain || '— domaine —'}</div>
+  </div>
+{/each}
+
+{#if systemGroups.length}
+  <div class="lieux-bucket-head">Systèmes</div>
+  {#each systemGroups as group (group.system.id)}
+    <div class="author-list-item {creationState.selectedRecordId === group.system.id ? 'active' : ''}"
+         role="button" tabindex="0"
+         onclick={() => onSelect(systemRecord(group.system))} onkeydown={(ev) => onKey(ev, systemRecord(group.system))}>
+      <div class="ali-name" style="font-weight:600">{group.system.name}</div>
+      <div class="ali-meta">Système · {group.system.skill_count} compétence(s)</div>
+    </div>
+    {#each group.skills as row (row.id)}
+      <div class="author-list-item {creationState.selectedRecordId === row.id ? 'active' : ''}"
+           style="padding-left:28px" role="button" tabindex="0"
+           onclick={() => onSelect(skillRecord(row))} onkeydown={(ev) => onKey(ev, skillRecord(row))}>
+        <div class="ali-name">{row.name}</div>
+        <div class="ali-meta">{row.base_domain}</div>
+      </div>
+    {/each}
+  {/each}
+{/if}
+
+{#if unassigned}
+  <div class="lieux-bucket-head">{NO_SYSTEM_LABEL}</div>
+  {#each unassigned.skills as row (row.id)}
+    <div class="author-list-item {creationState.selectedRecordId === row.id ? 'active' : ''}"
+         role="button" tabindex="0"
+         onclick={() => onSelect(skillRecord(row))} onkeydown={(ev) => onKey(ev, skillRecord(row))}>
+      <div class="ali-name">{row.name}</div>
+      <div class="ali-meta">{row.base_domain}</div>
+    </div>
+  {/each}
+{/if}
+
+{#if !systemGroups.length && !unassigned}
+  <div class="empty">Aucune compétence propre à ce monde.</div>
+{/if}
+
+<div class="lieux-bucket-head">Trous du lexique</div>
+{#if competencesState.gapsError}
+  <div class="empty">{competencesState.gapsError}</div>
+{:else if competencesState.gaps.length === 0}
+  <div class="empty">Aucun trou détecté.</div>
+{:else}
+  {#each competencesState.gaps as gap (gap.surface_form)}
+    <div class="author-list-item" role="button" tabindex="0"
+         onclick={() => openGap(gap.surface_form)}
+         onkeydown={(ev) => { if (ev.key === 'Enter') openGap(gap.surface_form); }}>
+      <div class="ali-name">{gap.surface_form}</div>
+      <div class="ali-meta">{gap.count} occurrence(s) · {fmtDate(gap.last_seen)}</div>
+    </div>
+  {/each}
+{/if}
+{#if competencesState.arbiterFailures.error > 0 || competencesState.arbiterFailures.empty > 0}
+  <div style="padding:6px 14px; font-size:11px; color:var(--muted)">
+    Échecs de l'arbitre (hors lexique) : {competencesState.arbiterFailures.error} erreur(s), {competencesState.arbiterFailures.empty} réponse(s) vide(s)
+  </div>
+{/if}
diff --git a/frontend/src/creation/CompetencesSheet.svelte b/frontend/src/creation/CompetencesSheet.svelte
new file mode 100644
index 0000000..67f94eb
--- /dev/null
+++ b/frontend/src/creation/CompetencesSheet.svelte
@@ -0,0 +1,182 @@
+<script>
+  /* TICKET-0099 (BRIEF-0099-b, B1 + E1). The Compétences fiche, rendered
+     by Sheet.svelte under `type === 'competences'` inside #author-main --
+     the same fiche area every entity tab uses. Sheet.svelte selects this
+     branch from sheetType (CLAUDE.md, creation_tab_switch.py); THIS
+     component then reads the record's own `kind` (C-01), a field of the
+     same sheetDetail that feeds it, never activeTabKey.
+
+     Every input binds straight to creationState.sheetDetail, a fresh C-01
+     record the list built for this fiche: nothing reaches the catalogue
+     until the shell's Save button, which Sheet.svelte's saveSheet routes to
+     saveCompetenceRecord (competences.svelte.js). Delete and "Retirer du
+     brouillon" are this fiche's own buttons, as Delete is on the entity
+     fiche. The two dialogs are Modal.svelte instances, unchanged from the
+     former Competences.svelte (lock O1): the skill delete keeps its type
+     "Oui" step (it cascades onto player-character skill rows), the system
+     delete shows the server's 409 refusal inline.
+
+     No scoped <style> block: like every other Creation island, classes
+     come from frontend/public/creation.css / shared.css. */
+  import { creationState } from './state.svelte.js';
+  import { creationRefreshList } from './tabs.js';
+  import Modal from './Modal.svelte';
+  import {
+    competencesState, COMPETENCES_DOMAINS, NO_SYSTEM_LABEL, generateDraft,
+    discardDraft, deleteSkill, deleteSystem, closeCompetenceSheet,
+  } from './competences.svelte.js';
+
+  const rec = $derived(creationState.sheetDetail);
+
+  let genBrief = $state('');
+  let genStatus = $state('');
+  let genNotes = $state([]);
+
+  let deleteOpen = $state(false);
+  let deleteConfirmText = $state('');
+  let deleteStatus = $state('');
+
+  async function onGenerate() {
+    const brief = genBrief.trim();
+    if (!brief) { genStatus = 'Intention requise.'; return; }
+    genStatus = 'Génération…';
+    genNotes = [];
+    try {
+      const result = await generateDraft(brief);
+      if (!result.ok) { genStatus = result.error; return; }
+      genNotes = result.notes;
+      genStatus = competencesState.draft.length
+        ? 'Brouillon généré — ouvrez chaque proposition dans la liste, relisez-la, puis enregistrez-la.'
+        : 'Aucune compétence proposée.';
+    } catch (err) {
+      genStatus = err.message;
+    }
+  }
+
+  function onDiscardDraft() {
+    discardDraft(rec.draftKey);
+    closeCompetenceSheet();
+  }
+
+  function openDelete() {
+    deleteConfirmText = '';
+    deleteStatus = '';
+    deleteOpen = true;
+  }
+
+  function closeDelete() {
+    deleteOpen = false;
+  }
+
+  async function confirmDelete() {
+    deleteStatus = '…';
+    try {
+      if (rec.kind === 'system') await deleteSystem(rec.id);
+      else await deleteSkill(rec.id);
+      deleteOpen = false;
+      closeCompetenceSheet();
+      creationRefreshList();
+    } catch (err) {
+      deleteStatus = err.message;
+    }
+  }
+</script>
+
+{#if rec && rec.kind === 'assistant'}
+  <div class="field-section">
+    <div class="field-row">
+      <label for="competences-gen-brief">Intention</label>
+      <textarea id="competences-gen-brief" rows="3" bind:value={genBrief}
+        placeholder="Ex. un monde maritime où la navigation et le troc comptent autant que le combat"></textarea>
+    </div>
+    <div style="display:flex; gap:10px; align-items:center; margin-top:6px">
+      <button class="btn-send" onclick={onGenerate}>Générer le brouillon</button>
+      <span class="author-status">{genStatus}</span>
+    </div>
+    {#if genNotes.length}
+      <div style="margin-top:8px; font-size:12px; color:var(--muted)">Notes de l'assistant :
+        {#each genNotes as n}<div>• {n}</div>{/each}
+      </div>
+    {/if}
+  </div>
+{:else if rec && rec.kind === 'skill'}
+  <div style="display:flex; justify-content:flex-end; gap:8px; margin-bottom:8px;">
+    {#if rec.draftKey != null}
+      <button class="btn-ghost" onclick={onDiscardDraft}>Retirer du brouillon</button>
+    {/if}
+    {#if rec.persisted}
+      <button class="btn-end" onclick={openDelete}>Supprimer</button>
+    {/if}
+  </div>
+  <div class="field-section">
+    <div class="field-grid">
+      <div class="field-row">
+        <label for="competence-f-name">Nom</label>
+        <input id="competence-f-name" type="text" bind:value={creationState.sheetDetail.name}>
+      </div>
+      <div class="field-row">
+        <label for="competence-f-domain">Domaine de base</label>
+        <select id="competence-f-domain" bind:value={creationState.sheetDetail.base_domain}>
+          {#if !COMPETENCES_DOMAINS.includes(rec.base_domain)}<option value="">— domaine —</option>{/if}
+          {#each COMPETENCES_DOMAINS as d}<option value={d}>{d}</option>{/each}
+        </select>
+      </div>
+      <div class="field-row">
+        <label for="competence-f-system">Système</label>
+        <select id="competence-f-system" onchange={(e) => { creationState.sheetDetail.system_id = e.currentTarget.value || null; }}>
+          <option value="" selected={!rec.system_id}>{NO_SYSTEM_LABEL}</option>
+          {#each competencesState.systems as sys (sys.id)}
+            <option value={sys.id} selected={rec.system_id === sys.id}>{sys.name}</option>
+          {/each}
+        </select>
+      </div>
+      <div class="field-row" style="grid-column:1/-1">
+        <label for="competence-f-description">Description</label>
+        <textarea id="competence-f-description" rows="3" bind:value={creationState.sheetDetail.description}></textarea>
+      </div>
+    </div>
+  </div>
+{:else if rec && rec.kind === 'system'}
+  {#if rec.persisted}
+    <div style="display:flex; justify-content:flex-end; margin-bottom:8px;">
+      <button class="btn-end" onclick={openDelete}>Supprimer</button>
+    </div>
+  {/if}
+  <div class="field-section">
+    <div class="field-grid">
+      <div class="field-row">
+        <label for="system-f-name">Nom</label>
+        <input id="system-f-name" type="text" bind:value={creationState.sheetDetail.name}>
+      </div>
+      <div class="field-row" style="grid-column:1/-1">
+        <label for="system-f-description">Description</label>
+        <textarea id="system-f-description" rows="3" bind:value={creationState.sheetDetail.description}></textarea>
+      </div>
+    </div>
+    {#if rec.persisted}
+      <div style="margin-top:8px; font-size:12px; color:var(--muted)">{rec.skill_count} compétence(s) dans ce système.</div>
+    {/if}
+  </div>
+{/if}
+
+<Modal title={rec && rec.kind === 'system' ? 'Supprimer le système' : 'Supprimer la compétence'}
+       open={deleteOpen} dismissOnBackdrop={false} onClose={closeDelete}>
+  {#snippet body()}
+    {#if rec && rec.kind === 'system'}
+      <p>Cette action supprime définitivement le système « {rec.name} ».
+      Un système qui contient encore des compétences ne peut pas être supprimé —
+      détachez-les ou supprimez-les d'abord.</p>
+      <div style="color:var(--red); margin-top:6px;">{deleteStatus}</div>
+      <button class="btn-send" style="margin-top:8px" onclick={confirmDelete}>Supprimer</button>
+    {:else if rec}
+      <p>Cette action supprime définitivement la compétence « {rec.name} » et,
+      pour chaque personnage joueur qui la possède, sa ligne de compétence
+      correspondante. Elle est irréversible.</p>
+      <p>Tapez Oui pour confirmer.</p>
+      <input type="text" placeholder="Oui" bind:value={deleteConfirmText}>
+      <div style="color:var(--red); margin-top:6px;">{deleteStatus}</div>
+      <button class="btn-send" style="margin-top:8px" disabled={deleteConfirmText.trim() !== 'Oui'}
+        onclick={confirmDelete}>Supprimer définitivement</button>
+    {/if}
+  {/snippet}
+</Modal>
diff --git a/frontend/src/creation/Creation.svelte b/frontend/src/creation/Creation.svelte
index e689432..6f23b27 100644
--- a/frontend/src/creation/Creation.svelte
+++ b/frontend/src/creation/Creation.svelte
@@ -232,9 +232,6 @@
        construction ── -->
   <div id="creation-artefacts" style:display={containerVisible('creation-artefacts') ? '' : 'none'}></div>
 
-  <!-- ── Compétences sub-tab -- Svelte island: empty by construction ── -->
-  <div id="creation-competences" style:display={containerVisible('creation-competences') ? '' : 'none'}></div>
-
   <!-- ── Région sub-tab -- Svelte island: generation + review + atomic
        commit ── -->
   <div id="creation-region" style:display={containerVisible('creation-region') ? '' : 'none'}></div>
diff --git a/frontend/src/creation/EntityList.svelte b/frontend/src/creation/EntityList.svelte
index 79801d5..a6ff40d 100644
--- a/frontend/src/creation/EntityList.svelte
+++ b/frontend/src/creation/EntityList.svelte
@@ -55,6 +55,8 @@
   import { selectEntity } from './sheetState.svelte.js';
   import { openRoomBatch } from './roomBatch.svelte.js';
   import { loadAgendas } from './intrigues.svelte.js';
+  import { loadCatalogue } from './competences.svelte.js';
+  import CompetencesList from './CompetencesList.svelte';
 
   let { legacyDoc } = $props();
 
@@ -156,6 +158,22 @@
     recordsReady = true;
   }
 
+  /** competences' own list fetch (TICKET-0099, BRIEF-0099-b) -- same shape
+   *  as loadEvents/loadAgendaRecords above; the rows land in
+   *  competencesState and CompetencesList.svelte renders them. */
+  async function loadCompetenceRecords() {
+    recordsReady = false;
+    mode = 'record';
+    try {
+      await loadCatalogue();
+    } catch (err) {
+      errorMessage = err.message;
+      mode = 'error';
+      return;
+    }
+    recordsReady = true;
+  }
+
   function activateTab(tabKey) {
     const isNewActivation = tabKey !== previousTabKey;
     previousTabKey = tabKey;
@@ -167,6 +185,10 @@
       loadAgendaRecords();
       return;
     }
+    if (tabKey === 'competences') {
+      loadCompetenceRecords();
+      return;
+    }
     if (tabKey === 'lieux' && isNewActivation) {
       lieuxParentId = null;
       lieuxBreadcrumb = [];
@@ -374,4 +396,6 @@
       </div>
     {/each}
   {/if}
+{:else if mode === 'record' && creationState.activeTabKey === 'competences'}
+  <CompetencesList onSelect={onSelectRecord} />
 {/if}
diff --git a/frontend/src/creation/Sheet.svelte b/frontend/src/creation/Sheet.svelte
index edde031..fee1389 100644
--- a/frontend/src/creation/Sheet.svelte
+++ b/frontend/src/creation/Sheet.svelte
@@ -99,6 +99,8 @@
   import { resetEventDraft, eventDraftState } from './eventDraft.svelte.js';
   import Evenements from './Evenements.svelte';
   import Intrigues from './Intrigues.svelte';
+  import CompetencesSheet from './CompetencesSheet.svelte';
+  import { blankRecord, competenceSheetTitle, saveCompetenceRecord } from './competences.svelte.js';
   import PjCreatePanel from './PjCreatePanel.svelte';
   import RelationsEditor from './RelationsEditor.svelte';
   import KnowledgeEditor from './KnowledgeEditor.svelte';
@@ -122,10 +124,12 @@
   const EMPTY_BODY_BY_TAB = {
     intrigues: 'Sélectionnez une intrigue depuis la liste, ou créez-en une nouvelle.',
     evenements: 'Sélectionnez un événement depuis la liste, ou créez-en un nouveau.',
+    competences: 'Sélectionnez une compétence ou un système dans la liste, ou créez-en une nouvelle.',
   };
   const EMPTY_TITLE_BY_TAB = {
     intrigues: 'Sélectionner une intrigue',
     evenements: 'Sélectionner un événement',
+    competences: 'Sélectionner une compétence',
   };
 
   let registry = $state(null);
@@ -210,6 +214,10 @@
     resetGeneratePanel();
     resetEventDraft();
     enterCreateMode(resolveTypeForTab(creationState.activeTabKey));
+    // TICKET-0099 (BRIEF-0099-b): a competences fiche always holds a whole
+    // C-01 record, never enterCreateMode's bare {} -- selected by the
+    // sheetType just written, the same fact that picks the render branch.
+    if (creationState.sheetType === 'competences') creationState.sheetDetail = blankRecord();
   }
 
   legacyDoc.addEventListener('creation:sheet-reset', () => {
@@ -276,6 +284,19 @@
     flushSync(() => { enterViewMode(ev.detail.record, ev.detail.tabId); });
   });
 
+  // TICKET-0099 (BRIEF-0099-b, C-05): a record that stops existing -- a
+  // deleted skill or system, a discarded draft -- closes its fiche.
+  // Dispatched by competences.svelte.js's closeCompetenceSheet; the reset
+  // itself stays here, with the rest of the quintet's writes.
+  legacyDoc.addEventListener('creation:record-closed', () => {
+    flushSync(() => {
+      creationState.sheetMode = 'empty';
+      creationState.sheetDetail = null;
+      creationState.sheetIsNew = false;
+      creationState.sheetType = null;
+    });
+  });
+
   // #author-save-btn's onclick (creationSaveDispatch) dispatches this for
   // every tab with no saveHandler of its own.
   legacyDoc.addEventListener('creation:sheet-save', () => { saveSheet(); });
@@ -359,6 +380,17 @@
       if (saveBtn) saveBtn.style.display = 'none';
       return;
     }
+    // competences (TICKET-0099, BRIEF-0099-b): no ENTITY_TYPE_REGISTRY row
+    // either; the title comes from the record (C-01). Save shows for every
+    // record but the assistant -- it is the create AND the update submit
+    // (E1), like the entity fiche's own.
+    if (creationState.sheetType === 'competences') {
+      const record = creationState.sheetDetail;
+      if (titleEl) titleEl.textContent = competenceSheetTitle(record);
+      if (statusEl) { statusEl.className = 'author-status'; statusEl.textContent = ''; }
+      if (saveBtn) saveBtn.style.display = record && record.kind === 'assistant' ? 'none' : '';
+      return;
+    }
     if (!registry) return;
     const type = creationState.sheetType;
     const typeInfo = registry.types[type];
@@ -390,6 +422,7 @@
   });
 
   async function saveSheet() {
+    if (creationState.sheetType === 'competences') { await saveCompetenceSheet(); return; }
     if (creationState.activeTabKey === 'evenements') { await saveEventSheet(); return; }
     if (!registry) return;
     const statusEl = legacyDoc.getElementById('author-status');
@@ -426,6 +459,25 @@
     await submitEntity(isNewSave, type, entityData, extData);
   }
 
+  /** competences' save (TICKET-0099, BRIEF-0099-b): the header Save button
+   *  for every competences record (E1). saveCompetenceRecord owns the
+   *  write and its validation; this owns the fiche's chrome, the same tail
+   *  saveEventSheet runs below. */
+  async function saveCompetenceSheet() {
+    const statusEl = legacyDoc.getElementById('author-status');
+    if (statusEl) { statusEl.className = 'author-status'; statusEl.textContent = '…'; }
+    try {
+      const saved = await saveCompetenceRecord(creationState.sheetDetail);
+      creationRefreshList();
+      flushSync(() => { enterViewMode(saved, 'competences'); });
+      legacyDoc.dispatchEvent(new CustomEvent('creation:selection', { detail: { entityId: null, recordId: saved.id } }));
+      const st = legacyDoc.getElementById('author-status');
+      if (st) { st.className = 'author-status ok'; st.textContent = 'Enregistré.'; }
+    } catch (e) {
+      if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = e.message; }
+    }
+  }
+
   /** evenements' save (BRIEF-0058-j) -- one function for both the header
    *  Save button (view mode, PUT) and <Evenements>'s own inline "+ Créer
    *  l'événement" button (create mode, POST), unlike the legacy pair
@@ -616,6 +668,8 @@
         eventFields={registry.event_fields} onSave={saveSheet} />
     {:else if type === 'intrigues'}
       <Intrigues {isNew} agenda={detail} />
+    {:else if type === 'competences'}
+      <CompetencesSheet />
     {:else if tabKey === 'pj' && isNew}
       <PjCreatePanel {legacyDoc} />
     {:else if registry.types[type]}
diff --git a/frontend/src/creation/competences.svelte.js b/frontend/src/creation/competences.svelte.js
index 1b595f1..8788976 100644
--- a/frontend/src/creation/competences.svelte.js
+++ b/frontend/src/creation/competences.svelte.js
@@ -8,45 +8,44 @@
    individually (creator-CRUD POST), never a bulk silent write -- Model
    proposes, code judges.
 
-   competencesDeleteOpen/competencesDeleteConfirm are NOT here: the delete
-   confirmation is a dialog (Modal.svelte, lock O1), and a plain module
-   cannot own dialog state (same rule locationType.js's own split follows,
-   commit 1) -- that state lives in Competences.svelte itself.
-
-   TICKET-0084 (BRIEF-0084-b): `skill_system` reader. `systems` is fetched
-   once alongside `rows` (world load/switch) and re-fetched after any
-   write that can change a system's `skill_count` -- a system write
-   itself, or a skill-definition write that attaches/detaches a system.
-   Grouping the catalogue by system happens in the component
-   (groupSkillsBySystem below), from these two flat lists -- never a
-   nested endpoint response (json_ui_boundary).
-
-   TICKET-0084 (BRIEF-0084-d): the read-only gaps reader. `gaps` and
-   `arbiterFailures` follow the exact same shape as `systems` above --
-   fetched once alongside rows/systems (world load/switch), never written
-   to by this view. No re-fetch-after-write wiring: skill_resolution is
-   append-only telemetry the catalogue write path never changes, so
-   nothing here invalidates it (a stale gap simply stops recurring on the
-   next live Play turn -- history is never rewritten). */
+   TICKET-0084 (BRIEF-0084-b): `skill_system` reader. Grouping the
+   catalogue by system happens client-side (groupSkillsBySystem below),
+   from two flat lists -- never a nested endpoint response
+   (json_ui_boundary). BRIEF-0084-d: the read-only gaps reader, fetched
+   alongside, never written to by this view.
+
+   TICKET-0099 (BRIEF-0099-b, B1): the tab lives on the shared editor area
+   now -- EntityList.svelte renders CompetencesList.svelte in its record
+   mode, Sheet.svelte renders CompetencesSheet.svelte under
+   `type === 'competences'`. Everything the list hands to the sheet is a
+   RECORD (C-01): a fresh object built by the factories below, never a row
+   of this store, so editing a fiche changes nothing until Save.
+   `persisted` is the one fact that decides POST vs PUT, the "Nouvelle"
+   title and whether Delete shows -- never sheetIsNew, which a draft opened
+   from the list does not carry. */
+import { serverState } from '../lib/serverState.svelte.js';
+
 export const competencesState = $state({
-  draft: [],   // AI-proposed rows awaiting individual accept/discard
+  draft: [],   // proposed rows awaiting Save: {key, name, base_domain, system_id, description}
   rows: [],    // existing world-scoped skill_definition rows
   systems: [], // existing world-scoped skill_system rows
   gaps: [],    // distinct unmatched surface forms, most frequent first
   arbiterFailures: { error: 0, empty: 0 },
-  loading: true,
-  loadError: '',
-  systemsError: '',
   gapsError: '',
+  draftWorldId: null, // the world `draft` belongs to; a world switch empties it
 });
 
 export const COMPETENCES_DOMAINS = ['physical', 'agility', 'perception', 'composure'];
 
 // Exact label, both as the ungrouped catalogue's group header and as the
-// skill-definition form's no-system dropdown option (BRIEF-0084-b Scope IN
-// items 3-4) -- one literal, never retyped.
+// skill fiche's no-system dropdown option (BRIEF-0084-b Scope IN items
+// 3-4) -- one literal, never retyped.
 export const NO_SYSTEM_LABEL = 'Sans système';
 
+export const ASSISTANT_RECORD_ID = 'assistant';
+
+let nextDraftKey = 1;
+
 async function api(path, options) {
   const res = await fetch(path, options);
   const data = await res.json().catch(() => ({ detail: res.statusText }));
@@ -54,96 +53,69 @@ async function api(path, options) {
   return data;
 }
 
-export function resetCompetences() {
-  competencesState.draft = [];
-}
+/* ── C-01 record factories ─────────────────────────────────────────────── */
 
-export function addManualRow() {
-  competencesState.draft.push({ name: '', base_domain: 'physical', system_id: null, description: '' });
+export function skillRecord(row) {
+  return {
+    kind: 'skill', persisted: true, id: row.id, draftKey: null,
+    name: row.name, base_domain: row.base_domain, system_id: row.system_id ?? null,
+    description: row.description ?? '',
+  };
 }
 
-/** Item 4 (BRIEF-0084-d): a gap click opens the same create form, name
- *  prefilled from surface_form, base_domain and system_id left unset --
- *  unlike addManualRow's 'physical' default, Nia must choose deliberately.
- *  Creates nothing; the row only lands in skill_definition on Accepter. */
-export function addGapDraftRow(surfaceForm) {
-  competencesState.draft.push({ name: surfaceForm, base_domain: '', system_id: null, description: '' });
+export function systemRecord(sys) {
+  return {
+    kind: 'system', persisted: true, id: sys.id,
+    name: sys.name, description: sys.description ?? '', skill_count: sys.skill_count ?? 0,
+  };
 }
 
-export function discardDraftRow(i) {
-  competencesState.draft.splice(i, 1);
+export function draftRecord(d) {
+  return {
+    kind: 'skill', persisted: false, id: `draft:${d.key}`, draftKey: d.key,
+    name: d.name ?? '', base_domain: d.base_domain ?? '', system_id: d.system_id ?? null,
+    description: d.description ?? '',
+  };
 }
 
-/** Returns {ok, error} | {ok:true, notes} -- the draft itself lands in
- *  competencesState.draft directly, same shape competencesRenderDraft's
- *  caller relied on. */
-export async function generateDraft(brief) {
-  const result = await api('/api/skill-definitions/generate', {
-    method: 'POST',
-    headers: { 'Content-Type': 'application/json' },
-    body: JSON.stringify({ brief }),
-  });
-  if (!result.ok) return { ok: false, error: result.error };
-  // The assistant proposes {name, base_domain, description} only -- it
-  // knows nothing of skill_system. Default every proposed row to no
-  // system, same as a manual row.
-  competencesState.draft = (result.draft.skills || []).map((s) => ({ ...s, system_id: s.system_id ?? null }));
-  return { ok: true, notes: result.notes || [] };
+export function assistantRecord() {
+  return { kind: 'assistant', persisted: false, id: ASSISTANT_RECORD_ID };
 }
 
-export async function acceptDraftRow(i) {
-  const row = competencesState.draft[i];
-  await api('/api/skill-definitions', {
-    method: 'POST',
-    headers: { 'Content-Type': 'application/json' },
-    body: JSON.stringify({
-      name: row.name.trim(),
-      base_domain: row.base_domain,
-      system_id: row.system_id || null,
-      description: row.description || '',
-    }),
-  });
-  competencesState.draft.splice(i, 1);
-  await loadList();
-  await loadSystems();
-}
-
-export async function loadList() {
-  competencesState.loading = true;
-  competencesState.loadError = '';
-  try {
-    competencesState.rows = await api('/api/skill-definitions');
-  } catch (e) {
-    competencesState.loadError = e.message;
-  } finally {
-    competencesState.loading = false;
-  }
+/** The blank record the shell's primary action opens (Sheet.svelte's
+ *  primaryAction). */
+export function blankRecord() {
+  return {
+    kind: 'skill', persisted: false, id: null, draftKey: null,
+    name: '', base_domain: 'physical', system_id: null, description: '',
+  };
 }
 
-export async function saveRow(id, name, base_domain, system_id, description) {
-  await api(`/api/skill-definitions/${id}`, {
-    method: 'PUT',
-    headers: { 'Content-Type': 'application/json' },
-    body: JSON.stringify({ name, base_domain, system_id: system_id || null, description }),
-  });
-  await loadSystems();
+/** The fiche title, read by Sheet.svelte's header effect. */
+export function competenceSheetTitle(record) {
+  if (!record) return '';
+  if (record.kind === 'assistant') return 'Assistant de compétences';
+  if (record.kind === 'system') return record.persisted ? record.name : 'Nouveau système';
+  return record.persisted ? record.name : 'Nouvelle compétence';
 }
 
-/** D2-delete-cascade: dependent PC `skill` rows then the definition, in one
- *  transaction. No separate history snapshot (locked decision). */
-export async function deleteDefinition(id) {
-  await api(`/api/skill-definitions/${id}`, { method: 'DELETE' });
-  await loadList();
-  await loadSystems();
-}
+/* ── Loading (C-02) ─────────────────────────────────────────────────────── */
 
-export async function loadSystems() {
-  competencesState.systemsError = '';
-  try {
-    competencesState.systems = await api('/api/skill-systems');
-  } catch (e) {
-    competencesState.systemsError = e.message;
+/** EntityList.svelte's record-mode fetch for this tab. Throws when the
+ *  catalogue itself cannot load; the gaps reader keeps its own error field
+ *  so a telemetry failure never blanks the list. */
+export async function loadCatalogue() {
+  if (competencesState.draftWorldId !== serverState.worldId) {
+    competencesState.draft = [];
+    competencesState.draftWorldId = serverState.worldId;
   }
+  const [rows, systems] = await Promise.all([
+    api('/api/skill-definitions'),
+    api('/api/skill-systems'),
+  ]);
+  competencesState.rows = rows;
+  competencesState.systems = systems;
+  await loadGaps();
 }
 
 /** Read-only: GET /api/skill-gaps only, never a write (BRIEF-0084-d). */
@@ -158,33 +130,6 @@ export async function loadGaps() {
   }
 }
 
-export async function createSystem(name, description) {
-  await api('/api/skill-systems', {
-    method: 'POST',
-    headers: { 'Content-Type': 'application/json' },
-    body: JSON.stringify({ name, description: description || null }),
-  });
-  await loadSystems();
-}
-
-export async function saveSystem(id, name, description) {
-  await api(`/api/skill-systems/${id}`, {
-    method: 'PUT',
-    headers: { 'Content-Type': 'application/json' },
-    body: JSON.stringify({ name, description: description || null }),
-  });
-  await loadSystems();
-}
-
-/** D2b-delete-refuse: the server is fail-closed while any skill_definition
- *  still carries this system_id (409) -- no optimistic removal here, the
- *  row is dropped from the list only once loadSystems() re-fetches after a
- *  confirmed success. */
-export async function deleteSystem(id) {
-  await api(`/api/skill-systems/${id}`, { method: 'DELETE' });
-  await loadSystems();
-}
-
 /** Groups the flat skill-definition list under the flat system list,
  *  client-side (json_ui_boundary: no nested endpoint response). System
  *  groups are ordered by name and always rendered, even with zero skills
@@ -206,3 +151,95 @@ export function groupSkillsBySystem(rows, systems) {
   if (unassigned.length) groups.push({ system: null, skills: unassigned });
   return groups;
 }
+
+/* ── Drafts (C-03) ──────────────────────────────────────────────────────── */
+
+/** Returns {ok:false, error} | {ok:true, notes}. The proposed rows REPLACE
+ *  the current drafts (unchanged since BRIEF-0059-h); each gets a key. The
+ *  assistant knows nothing of skill_system: every row starts with none. */
+export async function generateDraft(brief) {
+  const result = await api('/api/skill-definitions/generate', {
+    method: 'POST',
+    headers: { 'Content-Type': 'application/json' },
+    body: JSON.stringify({ brief }),
+  });
+  if (!result.ok) return { ok: false, error: result.error };
+  competencesState.draft = (result.draft.skills || []).map((s) => ({
+    ...s, key: nextDraftKey++, system_id: s.system_id ?? null,
+  }));
+  return { ok: true, notes: result.notes || [] };
+}
+
+/** A gap click (BRIEF-0084-d item 4): name prefilled from surface_form,
+ *  base_domain and system_id left unset -- Nia chooses deliberately.
+ *  Creates nothing; returns the draft's record for the caller to open. */
+export function addGapDraft(surfaceForm) {
+  const d = { key: nextDraftKey++, name: surfaceForm, base_domain: '', system_id: null, description: '' };
+  competencesState.draft.push(d);
+  return draftRecord(d);
+}
+
+export function discardDraft(key) {
+  competencesState.draft = competencesState.draft.filter((d) => d.key !== key);
+}
+
+/* ── Writes (C-04) ──────────────────────────────────────────────────────── */
+
+function requireName(record) {
+  const name = (record.name || '').trim();
+  if (!name) throw new Error('Nom requis.');
+  return name;
+}
+
+async function saveSkill(record) {
+  const name = requireName(record);
+  if (!COMPETENCES_DOMAINS.includes(record.base_domain)) throw new Error('Domaine de base requis.');
+  const body = JSON.stringify({
+    name, base_domain: record.base_domain, system_id: record.system_id || null,
+    description: record.description || '',
+  });
+  const saved = record.persisted
+    ? await api(`/api/skill-definitions/${record.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body })
+    : await api('/api/skill-definitions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body });
+  if (record.draftKey != null) discardDraft(record.draftKey);
+  return skillRecord(saved);
+}
+
+async function saveSystem(record) {
+  const name = requireName(record);
+  const body = JSON.stringify({ name, description: record.description || null });
+  const saved = await api(`/api/skill-systems/${record.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body });
+  return systemRecord(saved);
+}
+
+/** Saves the open fiche's record; returns the saved record (C-01). Throws
+ *  Error with a French message on a refused or failed write. */
+export async function saveCompetenceRecord(record) {
+  if (record.kind === 'skill') return saveSkill(record);
+  if (record.kind === 'system') return saveSystem(record);
+  throw new Error('Rien à enregistrer.');
+}
+
+/** D2-delete-cascade: dependent PC `skill` rows then the definition, in one
+ *  transaction, server-side. No separate history snapshot (locked). */
+export async function deleteSkill(id) {
+  await api(`/api/skill-definitions/${id}`, { method: 'DELETE' });
+}
+
+/** D2b-delete-refuse: the server is fail-closed (409) while any
+ *  skill_definition still carries this system_id. */
+export async function deleteSystem(id) {
+  await api(`/api/skill-systems/${id}`, { method: 'DELETE' });
+}
+
+/** Back to the empty fiche after a delete or a discarded draft (C-05).
+ *  Sheet.svelte owns the sheet quintet (state.svelte.js), so this only
+ *  signals: 'creation:record-closed' is Sheet's own listener, and
+ *  'creation:selection' with no id is EntityList's -- the same two-event
+ *  shape creationSelectRecord (tabs.js) uses to open a record.
+ *  'creation:sheet-reset' is not reused: its dispatch is confined to
+ *  tabs.js (creation_tab_switch.py rule 3). */
+export function closeCompetenceSheet() {
+  document.dispatchEvent(new CustomEvent('creation:record-closed'));
+  document.dispatchEvent(new CustomEvent('creation:selection', { detail: { entityId: null, recordId: null } }));
+}
diff --git a/frontend/src/creation/mount.js b/frontend/src/creation/mount.js
index 68faa37..3a83c05 100644
--- a/frontend/src/creation/mount.js
+++ b/frontend/src/creation/mount.js
@@ -35,7 +35,6 @@ import RoomBatch from './RoomBatch.svelte';
 import NpcAgent from './NpcAgent.svelte';
 import LinkAgent from './LinkAgent.svelte';
 import Artefacts from './Artefacts.svelte';
-import Competences from './Competences.svelte';
 import Registre from './Registre.svelte';
 import Prompts from './Prompts.svelte';
 import PjSkillFiche from './PjSkillFiche.svelte';
@@ -44,7 +43,7 @@ import Queue from './Queue.svelte';
 import QueueBatchBar from './QueueBatchBar.svelte';
 import SubjectWorklist from './SubjectWorklist.svelte';
 
-const COMPONENTS = { constructeur: Constructeur, entityList: EntityList, entitySheet: Sheet, region: Region, batch: RoomBatch, npcAgent: NpcAgent, linkAgent: LinkAgent, artefacts: Artefacts, competences: Competences, registre: Registre, prompts: Prompts, pjSkillFiche: PjSkillFiche, queueFilters: QueueFilters, queue: Queue, queueBatchBar: QueueBatchBar, subjectWorklist: SubjectWorklist };
+const COMPONENTS = { constructeur: Constructeur, entityList: EntityList, entitySheet: Sheet, region: Region, batch: RoomBatch, npcAgent: NpcAgent, linkAgent: LinkAgent, artefacts: Artefacts, registre: Registre, prompts: Prompts, pjSkillFiche: PjSkillFiche, queueFilters: QueueFilters, queue: Queue, queueBatchBar: QueueBatchBar, subjectWorklist: SubjectWorklist };
 
 const live = {}; // key -> { node, instance }
 
diff --git a/frontend/src/creation/registry.js b/frontend/src/creation/registry.js
index de5b524..6f23028 100644
--- a/frontend/src/creation/registry.js
+++ b/frontend/src/creation/registry.js
@@ -20,7 +20,11 @@
    surfaces that were CREATED as islands, with no legacy predecessor.
    Each entry declares its `origin` -- 'migration' for a surface that
    moved (the ledger described above), 'new' for one that did not.
-   Nothing is removed once added, whichever the origin.
+   Nothing is removed once added, whichever the origin -- with one named
+   exception (TICKET-0099, R1): a surface ABSORBED into another island's
+   component leaves no container to mount, so its entry is removed and its
+   ledger line MOVES, whole, into the absorbing entry's retiredPrefixes
+   (rule 7 keeps proving every prefix gone). Nothing is ever dropped.
 
    tooling/verify/checks/creation_island.py parses this literal
    (comments ignored, field order free) and cross-references every
@@ -280,6 +284,18 @@ export const CREATION_ISLANDS = Object.freeze({
       'pcRenderDraftKnowledge',
       'pcGenerateDraft',
       'pcApplyDraft',
+      // TICKET-0099 (BRIEF-0099-b, R1): the Compétences tab's own ledger
+      // line, moved here whole when the tab was absorbed into this fiche
+      // (CompetencesSheet.svelte) and the shared list -- ported by
+      // BRIEF-0059-h commit 3, first recorded under its own `competences`
+      // entry, which no longer has a container to mount.
+      '_competencesWorldReset', 'competencesGenerateDraft',
+      '_competencesDomainOptions', 'competencesRenderDraft',
+      'competencesDiscardDraftRow', 'competencesAcceptDraftRow',
+      'competencesAddManualRow', 'competencesLoadList',
+      '_competencesRenderTable', 'competencesSaveRow',
+      'competencesDeleteOpen', 'competencesDeleteConfirm',
+      'COMPETENCES_DOMAINS',
     ],
   }),
   // BRIEF-0058-i (per RECON-SUPPLEMENT-0058's re-scope): region generation
@@ -374,23 +390,9 @@ export const CREATION_ISLANDS = Object.freeze({
     retiredPrefixes: ['loadCreationArtefacts', 'CREATION_ARTEFACTS_NOTICE'],
   }),
   // BRIEF-0059-h commit 3: the Compétences tab -- ported to
-  // Competences.svelte + competences.svelte.js, Modal.svelte's second
-  // consumer (delete-confirmation dialog, lock O1).
-  competences: Object.freeze({
-    containerId: 'creation-competences',
-    component: 'Competences.svelte',
-    origin: 'migration',
-    migratedBy: 'TICKET-0059',
-    retiredPrefixes: [
-      '_competencesWorldReset', 'competencesGenerateDraft',
-      '_competencesDomainOptions', 'competencesRenderDraft',
-      'competencesDiscardDraftRow', 'competencesAcceptDraftRow',
-      'competencesAddManualRow', 'competencesLoadList',
-      '_competencesRenderTable', 'competencesSaveRow',
-      'competencesDeleteOpen', 'competencesDeleteConfirm',
-      'COMPETENCES_DOMAINS',
-    ],
-  }),
+  // Competences.svelte + competences.svelte.js. Absorbed into entitySheet/
+  // entityList by TICKET-0099 (R1): its ledger line lives in entitySheet
+  // above.
   // BRIEF-0059-h commit 4: the Registre (global ledger) tab -- ported
   // wholesale to Registre.svelte. authorAddLedgerEntry closes here, not
   // with the entity sheet's own read-only LedgerPanel.svelte (RECON-0059-a
diff --git a/frontend/src/creation/state.svelte.js b/frontend/src/creation/state.svelte.js
index bbe068e..0b36950 100644
--- a/frontend/src/creation/state.svelte.js
+++ b/frontend/src/creation/state.svelte.js
@@ -29,6 +29,10 @@
    quintet, which Sheet.svelte owns exclusively (set by its own
    'creation:sheet-*' listeners and its exported primaryAction/saveSheet,
    never written from outside that component).
+   TICKET-0099: a record fiche (CompetencesSheet.svelte) edits the fields
+   OF its record in place (sheetDetail.name, ...); assigning the quintet
+   stays Sheet.svelte's alone -- closing a record goes through its
+   'creation:record-closed' listener.
 
    TICKET-0059 (BRIEF-0059-l commit 1) additions, now that Creation.svelte
    drives the chrome directly instead of index.html: tabsVersion (bumped by
diff --git a/frontend/src/creation/tabs.js b/frontend/src/creation/tabs.js
index 98b3662..92c3169 100644
--- a/frontend/src/creation/tabs.js
+++ b/frontend/src/creation/tabs.js
@@ -259,12 +259,13 @@ export const CREATION_TABS = {
   },
   competences: {
     label: 'Compétences',
-    archetype: 'bespoke',
-    containers: ['creation-competences'],
+    archetype: 'entity', // non-entity records on the shared list + fiche, as intrigues/evenements (TICKET-0099)
+    containers: ['creation-editor-area'],
     loader: null,
     state: { onTabEnter: null, onWorldSwitch: null },
-    islands: [{ key: 'competences', containerId: 'creation-competences' }],
-    primaryAction: { label: '+ Ajouter une compétence', handler: () => triggerPrimaryAction('competences') },
+    islands: [{ key: 'entityList', containerId: 'author-entity-list' }, { key: 'entitySheet', containerId: 'author-main' }],
+    createPanel: null,
+    primaryAction: { label: '+ Ajouter une compétence', handler: () => triggerPrimaryAction('entitySheet') },
   },
   region: {
     label: 'Région',
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 883d4ac..017f9df 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17372,6 +17372,38 @@ until it moves onto the shared editor area.
 batch panel stacks under the editor area) decides its own split; the check
 counts it in its PASS line instead of guessing.
 
+## COMPÉTENCES MOVES ONTO THE SHARED LIST AND FICHE (TICKET-0099) -- A FOURTH RECORD TAB (BRIEF-0099-b, no schema change)
+
+**B1.** The Compétences tab is an `archetype: 'entity'` record tab on
+`#creation-editor-area`, the fourth after Intrigues and Événements: the
+entity list (`EntityList.svelte`, record mode) renders
+`CompetencesList.svelte`, the entity fiche (`Sheet.svelte`, `type ===
+'competences'`) renders `CompetencesSheet.svelte`. The tab's own container
+and `Competences.svelte` are gone. Chosen over a copy of the layout's CSS
+classes (B2: the same look by discipline, two lists that drift) and over a
+generic list-and-fiche component (B3: no second reader yet).
+
+**C1 + D2 + H1 -- the list.** Brouillons (the assistant entry, then every
+draft), Systèmes (each system a row of its own, its skills indented under
+it), Sans système, Trous du lexique. A gap click creates a draft and opens
+it. The assistant is a list entry, never the empty fiche: an empty fiche has
+no `sheetType`, and a branch chosen by `activeTabKey` is what CLAUDE.md
+forbids (the TICKET-0083 freeze).
+
+**C-01 -- one record per fiche.** Every row the list hands to the fiche is a
+fresh record (`kind`, `persisted`, `id`, ...): editing changes nothing until
+Save. `persisted` alone decides POST or PUT, the « Nouvelle » title and
+whether Supprimer shows -- a draft opened from the list is not
+`sheetIsNew`. Drafts survive a tab switch and empty on a world switch.
+
+**E1.** The shell's Save button saves every record but the assistant; the
+fiche carries Supprimer (and « Retirer du brouillon » on a draft).
+
+**R1 -- the island registry.** The `competences` entry had no container
+left to mount. Its ledger line moved whole into `entitySheet`'s
+`retiredPrefixes`, and the registry header names the exception: an
+absorbed surface moves its line, it never drops it.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/creation_tab_switch.py b/tooling/verify/checks/creation_tab_switch.py
index 6c39061..fa9aefc 100644
--- a/tooling/verify/checks/creation_tab_switch.py
+++ b/tooling/verify/checks/creation_tab_switch.py
@@ -41,12 +41,11 @@ FAILURE, never a trivially satisfied comparison.
      Sheet.svelte legitimately holds an addEventListener for the same
      name) occurs exactly once across every file under frontend/src/,
      and that occurrence is in creation/tabs.js. Zero -> FAIL.
-  4. `frontend/src/creation/Sheet.svelte` contains BOTH
-     `{:else if type === 'evenements'}` and
-     `{:else if type === 'intrigues'}`, and contains NEITHER
-     `{:else if tabKey === 'evenements'}` NOR
-     `{:else if tabKey === 'intrigues'}`. Any of the four conditions
-     violated -> FAIL.
+  4. `frontend/src/creation/Sheet.svelte` contains
+     `{:else if type === '<tab>'}` and NOT `{:else if tabKey === '<tab>'}`
+     for every record tab in RECORD_TABS -- `evenements`, `intrigues`, and
+     `competences` (TICKET-0099, BRIEF-0099-b). Any condition violated ->
+     FAIL.
   5. `frontend/src/creation/Sheet.svelte` contains
      `{:else if registry.types[type]}`. Not found -> FAIL.
   6. The identifiers `_entityTabEnterReset`, `_intriguesTabEnterReset`
@@ -71,6 +70,7 @@ DISPATCHER_HEADER_RE = re.compile(r"export function showCreationSubTab\(tab\)\s*
 LINE_INITIAL_CLOSE_RE = re.compile(r"^\}", re.MULTILINE)
 DISPATCH_RE = re.compile(r"CustomEvent\('creation:sheet-reset'")
 RETIRED_IDENTS = ("_entityTabEnterReset", "_intriguesTabEnterReset", "_evenementsTabEnterReset")
+RECORD_TABS = ("evenements", "intrigues", "competences")
 
 FAILURES: list[str] = []
 
@@ -170,18 +170,13 @@ def _rule3_single_dispatch_site() -> bool:
 
 def _rule4_type_gated(sheet_src: str) -> bool:
     ok = True
-    if "{:else if type === 'evenements'}" not in sheet_src:
-        fail(f"{SHEET_FILE}: missing \"{{:else if type === 'evenements'}}\" branch")
-        ok = False
-    if "{:else if type === 'intrigues'}" not in sheet_src:
-        fail(f"{SHEET_FILE}: missing \"{{:else if type === 'intrigues'}}\" branch")
-        ok = False
-    if "{:else if tabKey === 'evenements'}" in sheet_src:
-        fail(f"{SHEET_FILE}: stale \"{{:else if tabKey === 'evenements'}}\" branch still present")
-        ok = False
-    if "{:else if tabKey === 'intrigues'}" in sheet_src:
-        fail(f"{SHEET_FILE}: stale \"{{:else if tabKey === 'intrigues'}}\" branch still present")
-        ok = False
+    for tab in RECORD_TABS:
+        if f"{{:else if type === '{tab}'}}" not in sheet_src:
+            fail(f"{SHEET_FILE}: missing \"{{:else if type === '{tab}'}}\" branch")
+            ok = False
+        if f"{{:else if tabKey === '{tab}'}}" in sheet_src:
+            fail(f"{SHEET_FILE}: stale \"{{:else if tabKey === '{tab}'}}\" branch still present")
+            ok = False
     return ok
 
 
diff --git a/tooling/verify/checks/page_contract.py b/tooling/verify/checks/page_contract.py
index e07aa2a..e9dae35 100644
--- a/tooling/verify/checks/page_contract.py
+++ b/tooling/verify/checks/page_contract.py
@@ -297,7 +297,8 @@ def main() -> int:
     # "Ajouter une compétence" lives in CREATION_TABS.competences'
     # primaryAction label (tabs.js) now, not index.html — scan the whole
     # frontend/src/creation/ tree (not just tabs.js) so an in-body control
-    # added to Competences.svelte would still be caught as a duplicate.
+    # added to CompetencesList.svelte/CompetencesSheet.svelte would still be
+    # caught as a duplicate.
     occurrences = 0
     if CREATION_SRC.is_dir():
         for path in CREATION_SRC.rglob("*"):
@@ -365,6 +366,27 @@ def main() -> int:
                     "containers: ['creation-editor-area'] (BRIEF-0022-a)"
                 )
 
+    # TICKET-0099/BRIEF-0099-b (B1): Compétences — fourth non-entity reader
+    # of the shared list+detail shell, the same shape as Intrigues/Événements.
+    if registry_src:
+        competences_src = _entry_block(registry_src, "competences")
+        if competences_src:
+            if not re.search(r"""archetype\s*:\s*['"]entity['"]""", competences_src):
+                failures.append(
+                    "CREATION_TABS.competences is not archetype: 'entity' (BRIEF-0099-b)"
+                )
+            if not re.search(r"""containers\s*:\s*\[\s*['"]creation-editor-area['"]\s*\]""", competences_src):
+                failures.append(
+                    "CREATION_TABS.competences does not have "
+                    "containers: ['creation-editor-area'] (BRIEF-0099-b)"
+                )
+
+    if "creation-competences" in html or "creation-competences" in creation_svelte:
+        failures.append(
+            "element id 'creation-competences' still present — Compétences must render "
+            "only through the shared creation-editor-area shell (BRIEF-0099-b)"
+        )
+
     if failures:
         for f in failures:
             print(f"FAIL: {f}")
````

## Scope OUT

- « + Ajouter un système » and any `secondaryAction` field: BRIEF-0099-C. Between B and C no new system can be created from the tab; existing systems are opened, edited and deleted here.
- Hiding a gap once its skill exists (carried forward in the ticket).
- Any change to `crud/skills.py` or `routes/creator.py`: the endpoints already return what the fiche needs (R-15).
- A generic list-and-fiche component (B3), or any change to how Intrigues/Événements render.
- Keeping edits to a draft that is left without saving (the entity fiche's own rule); changing « Save »'s label.
- Styling beyond classes already defined in `shared.css`/`creation.css` and inline styles in the existing idiom.
- BRIEF-0099-C.

## Invariants to defend

- **`Sheet.svelte` selects its render branch from `sheetType`, never from `activeTabKey`** (CLAUDE.md, `creation_tab_switch.py`). The competences branch, save route and header branch all read `sheetType`; `CompetencesSheet.svelte` then reads its record's `kind`, a field of the same `sheetDetail`. Any `tabKey === 'competences'` render gate is a STOP.
- **The sheet reset dispatch lives only in `showCreationSubTab`** (rule 3): C-05 uses its own event, never `'creation:sheet-reset'`.
- **Every Création surface mounts as a `CREATION_ISLANDS` entry through `mount.js` alone** (`creation_island.py`): the two new components are children of `EntityList.svelte` and `Sheet.svelte`, never islands; R1's transfer keeps rule 7's proof.
- **Every Création page is a `CREATION_TABS` entry** (`page_contract.py`): no in-body « Ajouter une compétence » control.
- **Model proposes, code judges**: the assistant's rows stay drafts until the creator saves each one.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold (line numbers may drift by a few lines; the quoted text must match).
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- A named mutation of item 5 does not fail as stated.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `npm run build` fails, or prints an error (not a warning) for any file.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `npm run build` prints a Svelte a11y warning located in `CompetencesList.svelte` or `CompetencesSheet.svelte`: report it verbatim; fix only if it is a missing label association or a missing keyboard handler on a clickable row (add it), otherwise leave it.

REPORT-ONLY:
- Timing of the corpus run.
- Any Svelte warning printed for a file this brief does not touch (`Sheet.svelte`'s `legacyDoc` capture warnings and `EntityList.svelte`'s a11y warnings exist on `main`).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus the deleted `frontend/src/creation/Competences.svelte`, `tooling/standards/DECISIONS_INDEX.md` and files under `src/world_engine/cockpit/static/`.
- `grep -rn "creation-competences" frontend/src CLAUDE.md frontend/public` → no output.
- `page_contract.py`, `creation_tab_switch.py`, `creation_island.py` (`… 14 retired legacy prefix set(s) confirmed gone …`), `creation_container_sizing.py` (14 single-container entries), `modal_primitive.py`, `stylesheet_partition.py`, `effect_self_write.py`, `module_budget.py`, `frontend_build_fresh.py`, `claude_md_contract.py`, `decisions_index.py` → `PASS`.
- Both named mutations of item 5 failed as stated.
- `corpus_gate.py` → 129/129.
- Live, on a test world with three systems: list left, fiche right; a system and a skill each open, edit and save; « + Ajouter une compétence » creates a skill; a gap click opens a draft; a skill delete asks « Oui ».
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `COMPÉTENCES MOVES ONTO THE SHARED LIST AND FICHE (TICKET-0099) -- A FOURTH RECORD TAB (BRIEF-0099-b, no schema change)`, `CLAUDE.md:22`, the header of `registry.js` and of `state.svelte.js` — all in the diff.
