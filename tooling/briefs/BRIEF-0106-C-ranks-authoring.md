<!-- slug: ranks-authoring -->
# BRIEF 0106-C — "The creator sets the ranks: a ladder per world, thresholds per system and skill"

Lot: LOT-0106-skill-progression.md (authoritative on conflict)
Depends on: BRIEF-0106-A, BRIEF-0106-B
Commit header for decisions: `(BRIEF-0106-c, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0106`, on the tree BRIEF-0106-B left, before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `src/world_engine/models/config.py` defines `class SkillRank(SQLModel, table=True):`; `SkillSystem` and `SkillDefinition` (`models/canon.py`) declare `points_to_rank_1` .. `points_to_rank_5`.
- `src/world_engine/cockpit/crud/skills.py:15` → `from pydantic import BaseModel`; `:56` → `from ...skill_ranks import DEFAULT_RANK, RANKS, RankStep, points_to_next, skill_owners, world_ladder`; `:81` → `    write_skill_rank,`; `:115` → `def list_skill_ranks(db: DbSession = Depends(get_session)) -> list[dict]:`; `:204` → `class SkillSystemWriteBody(BaseModel):`; `:353` → `class SkillDefinitionWriteBody(BaseModel):`; `wc -l` → 494.
- `src/world_engine/writes/config.py:62` → `    SCHEDULE_PHASES,`; `:66` → `from ..zone_rules import require_visitable`; `:414` → `def write_npc_schedule(`; no `upsert_skill_rank` anywhere.
- `tooling/verify/canon_write_policy.txt:42` → `src/world_engine/writes/config.py::write_npc_schedule          npc_schedule`.
- `frontend/src/creation/competences.svelte.js:45` → `export const ASSISTANT_RECORD_ID = 'assistant';`; `:111` → `export async function loadCatalogue() {`; `:223` → `export async function saveCompetenceRecord(record) {`.
- `frontend/src/creation/CompetencesList.svelte:50` → `<div class="lieux-bucket-head">Brouillons</div>`.
- `frontend/src/creation/CompetencesSheet.svelte:85` → `{#if rec && rec.kind === 'assistant'}`; `:139` → `{:else if rec && rec.kind === 'system'}`.
- `frontend/src/creation/Sheet.svelte` → `async function saveCompetenceSheet()` calls `saveCompetenceRecord(creationState.sheetDetail)`.

## Facts carried

### R-14 — Création › Compétences [M]
Opened: `frontend/src/creation/competences.svelte.js:1-251` (record
factories, `loadCatalogue`, `saveCompetenceRecord` routing by `kind`);
`CompetencesList.svelte:1-121`; `CompetencesSheet.svelte:1-182`;
`frontend/src/creation/Sheet.svelte:508-525` (`saveCompetenceSheet`: every
record of the tab goes through `saveCompetenceRecord`, then
`enterViewMode(saved)` and a selection of `saved.id`).
Consequence: a third record kind, `ranks`, needs no shell change.

### R-16 — where a curated-config table lives [M]
Opened: `src/world_engine/models/config.py:1-34` (split out of `canon.py`
for its budget; `conversation_window_config`: absence of a row is legal,
the reader applies defaults and never writes on read);
`src/world_engine/writes/config.py:1-40` (`upsert_*` family, never a
DELETE).
Consequence: `SkillRank` goes to `models/config.py`; `upsert_skill_rank`
to `writes/config.py`; no ladder row is seeded.

### R-09 — sanctioned canon writes [M]
Opened: `tooling/verify/canon_write_policy.txt:1-7` (`[CANON_TABLES]`),
`:24` (`write_skill_tier skill`), the `crud/skills.py` entries;
`tooling/verify/checks/single_canon_write.py:1-60, 180-206`.
Consequence: `write_skill_tier` is renamed `write_skill_rank`;
`write_skill_progress` and `upsert_skill_rank` are new allowed sites;
`skill_rank` joins `[CANON_TABLES]`.

### R-17 — documentation contracts [M]
Opened: `tooling/verify/checks/decisions_index.py:15-40` (strict header:
lowercase brief letter, `(BRIEF-0106-a, schema v2.15)`);
`tooling/standards/ARCHITECTURE_DECISIONS.md` tail (the `---` /
`*Co-built…*` footer stays last); `CLAUDE.md` 37 401 characters of 38 000
(`claude_md_contract.py`); `world-engine-schema.md:3`,
`src/world_engine/schema_version.py:15`.
Consequence: four decision entries above the footer; CLAUDE.md gains one
invariant (+240 characters) and one wording change.

## Contracts

### C-02 — the ladder (`skill_ranks.py`)
Produced by: BRIEF-0106-A   Consumed by: BRIEF-0106-B, C, D
`RANKS = (0..5)`, `MAX_RANK = 5`, `DEFAULT_RANK = 1`, `RANK_MODIFIERS =
(-1, 0, 1, 2, 2, 3)`, `DEFAULT_RANK_LABELS = ("Inexpérimenté", "Initié",
"Apprenti", "Confirmé", "Expert", "Maître")`, `DEFAULT_POINTS_TO_NEXT = (5,
10, 20, 40, 80)`, `TIER_TO_RANK = {-1: 0, 0: 1, 1: 2, 2: 3}`,
`RANK_POINTS_COLUMNS` (index = rank left). `RankStep(rank, label,
points_to_next)` frozen. `rank_modifier(rank) -> int` (`ValueError` outside
0-5). `default_ladder() -> tuple[RankStep, ...]`. `world_ladder(db,
world_id) -> tuple[RankStep, ...]` (six, index = rank; rows over defaults;
never writes). `points_to_next(rank, ladder, *, system=None,
definition=None) -> Optional[int]` (definition's column, else system's,
else the ladder's; None at MAX_RANK). `skill_owners(db, skill_definition_id)
-> (system | None, definition | None)`. `skill_points_to_next(db, *,
world_id, rank, skill_definition_id) -> Optional[int]`.

### C-08 — the ladder's writer and route
Produced by: BRIEF-0106-C   Consumed by: the Compétences UI (C-10)
`writes.upsert_skill_rank(db, *, world_id, rank, label, points_to_next) ->
SkillRank`: `ValueError` before any write on a rank outside 0-5, an empty
label, points at rank 5, or points missing / < 1 below rank 5;
fetch-or-create, never a DELETE; caller commits. `PUT /api/skill-ranks`
body `{"ranks": [{rank, label, points_to_next}] }`: 422 unless each rank
appears exactly once; 422 (rolled back, nothing written) on any invalid
step; serves C-04's ladder.

### C-09 — thresholds on the catalogue routes (family: rank thresholds)
Produced by: BRIEF-0106-C   Consumed by: C-10, C-02
`RankPointsBody`: `points_to_rank_1..5: Optional[int] = Field(None, ge=1)`;
`SkillSystemWriteBody` and `SkillDefinitionWriteBody` extend it. POST and
PUT of `/api/skill-systems` and `/api/skill-definitions` set all five (a
PUT without them clears them); `_skill_system_dict` and
`_skill_definition_dict` serve all five.
Members, re-read after the last: the world's ladder (C-08), a system
(C-09), a skill (C-09); one resolution order (C-02), one input per rank
reached in the UI (C-10).

### C-10 — the Compétences records
Produced by: BRIEF-0106-C   Consumed by: Nia
`competences.svelte.js`: `competencesState.ranks` (C-04, loaded by
`loadCatalogue`); `RANKS_RECORD_ID = 'ranks'`; `RANK_POINT_KEYS`;
`ranksRecord()` (`{kind: 'ranks', persisted: true, id: 'ranks', steps}`);
skill and system records carry the five keys; `inheritedPoints(record, n)`
(a skill: its system's value, then the world's; a system: the world's);
`saveCompetenceRecord` routes `ranks` to a PUT (C-08) and sends
`pointsBody(record)` with a skill and a system. `CompetencesList.svelte`: a
« Rangs » section with « Rangs du monde ». `CompetencesSheet.svelte`: the
`ranks` fiche (six names, five points), and a `thresholds()` block on the
skill and the system fiches (blank = inherited, the inherited value as
placeholder).

## Context

The ladder and the threshold columns exist (A) and the points move ranks (B). Nia wants to set the thresholds in Création › Compétences (W1), with one set of rank names per world (P2) and, at her request, overrides per system and per skill — the most specific winning (O1). This brief gives her the « Rangs du monde » record and the five threshold fields on each system and skill fiche, blank meaning inherited.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`
and the built frontend under `src/world_engine/cockpit/static/`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - adds `upsert_skill_rank` to `writes/config.py` (C-08), exported by `writes`; allow-lists it in `canon_write_policy.txt`;
   - in `cockpit/crud/skills.py`, adds `SkillRankStepBody`, `SkillRanksBody`, `PUT /api/skill-ranks` (C-08), `RankPointsBody` and its two helpers, the five thresholds on both write bodies, both dicts and the four POST/PUT routes (C-09);
   - in `competences.svelte.js`, `CompetencesList.svelte` and `CompetencesSheet.svelte`, the « Rangs du monde » record, the threshold fields and their inherited placeholders (C-10);
   - appends the decision entry above the footer;
   - adds C1-C3 to `skill_progression.py`.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Rebuild the frontend: `cd frontend`, `npm run build`.
4. Commit message: `feat(skills): the creator names the ranks and sets thresholds per world, system and skill (BRIEF-0106-c)`.

````diff
diff --git a/frontend/src/creation/CompetencesList.svelte b/frontend/src/creation/CompetencesList.svelte
index 19d23cd..b648a68 100644
--- a/frontend/src/creation/CompetencesList.svelte
+++ b/frontend/src/creation/CompetencesList.svelte
@@ -6,7 +6,8 @@
      own onSelectRecord (creationSelectRecord, tabs.js), so the fiche opens
      through the one record path intrigues/evenements already use.
 
-     Four sections, top to bottom:
+     Five sections, top to bottom:
+       Rangs            -- the world's ladder, one record (TICKET-0106, C-06).
        Brouillons       -- the assistant entry (H1), then every draft row.
        Systèmes         -- each system is a row of its own (its fiche), its
                            skills indented under it (C1).
@@ -19,8 +20,8 @@
      the same ones). */
   import { creationState } from './state.svelte.js';
   import {
-    competencesState, NO_SYSTEM_LABEL, ASSISTANT_RECORD_ID, groupSkillsBySystem,
-    skillRecord, systemRecord, draftRecord, assistantRecord, addGapDraft,
+    competencesState, NO_SYSTEM_LABEL, ASSISTANT_RECORD_ID, RANKS_RECORD_ID, groupSkillsBySystem,
+    skillRecord, systemRecord, draftRecord, assistantRecord, ranksRecord, addGapDraft,
   } from './competences.svelte.js';
 
   let { onSelect } = $props();
@@ -47,6 +48,14 @@
   }
 </script>
 
+<div class="lieux-bucket-head">Rangs</div>
+<div class="author-list-item {creationState.selectedRecordId === RANKS_RECORD_ID ? 'active' : ''}"
+     role="button" tabindex="0"
+     onclick={() => onSelect(ranksRecord())} onkeydown={(ev) => onKey(ev, ranksRecord())}>
+  <div class="ali-name">Rangs du monde</div>
+  <div class="ali-meta">{competencesState.ranks.map((r) => r.label).join(' → ')}</div>
+</div>
+
 <div class="lieux-bucket-head">Brouillons</div>
 <div class="author-list-item {creationState.selectedRecordId === ASSISTANT_RECORD_ID ? 'active' : ''}"
      role="button" tabindex="0"
diff --git a/frontend/src/creation/CompetencesSheet.svelte b/frontend/src/creation/CompetencesSheet.svelte
index 67f94eb..1f73168 100644
--- a/frontend/src/creation/CompetencesSheet.svelte
+++ b/frontend/src/creation/CompetencesSheet.svelte
@@ -16,14 +16,18 @@
      "Oui" step (it cascades onto player-character skill rows), the system
      delete shows the server's 409 refusal inline.
 
+     TICKET-0106 (BRIEF-0106-C): a skill and a system fiche carry the five
+     rank thresholds (blank = inherited, the inherited value as placeholder);
+     the 'ranks' record edits the world's six rank names and default points.
+
      No scoped <style> block: like every other Creation island, classes
      come from frontend/public/creation.css / shared.css. */
   import { creationState } from './state.svelte.js';
   import { creationRefreshList } from './tabs.js';
   import Modal from './Modal.svelte';
   import {
-    competencesState, COMPETENCES_DOMAINS, NO_SYSTEM_LABEL, generateDraft,
-    discardDraft, deleteSkill, deleteSystem, closeCompetenceSheet,
+    competencesState, COMPETENCES_DOMAINS, NO_SYSTEM_LABEL, RANK_POINT_KEYS, generateDraft,
+    discardDraft, deleteSkill, deleteSystem, closeCompetenceSheet, inheritedPoints,
   } from './competences.svelte.js';
 
   const rec = $derived(creationState.sheetDetail);
@@ -82,7 +86,47 @@
   }
 </script>
 
-{#if rec && rec.kind === 'assistant'}
+{#snippet thresholds()}
+  <div class="field-section">
+    <div style="font-size:12px; color:var(--muted); margin-bottom:4px">
+      Points pour atteindre chaque rang — vide : hérité (valeur grisée).
+    </div>
+    <div class="field-grid">
+      {#each RANK_POINT_KEYS as key, i (key)}
+        <div class="field-row">
+          <label for="competence-f-{key}">Vers {competencesState.ranks[i + 1]?.label ?? `rang ${i + 1}`}</label>
+          <input id="competence-f-{key}" type="number" min="1" step="1"
+            placeholder={String(inheritedPoints(rec, i + 1) ?? '')} value={rec[key] ?? ''}
+            oninput={(e) => { creationState.sheetDetail[key] = e.currentTarget.value === '' ? null : e.currentTarget.value; }}>
+        </div>
+      {/each}
+    </div>
+  </div>
+{/snippet}
+
+{#if rec && rec.kind === 'ranks'}
+  <div class="field-section">
+    <div style="font-size:12px; color:var(--muted); margin-bottom:6px">
+      Le nom de chaque rang dans ce monde et les points qu'il faut pour le quitter.
+      Un système ou une compétence peut remplacer ces points sur sa propre fiche.
+    </div>
+    <div class="field-grid">
+      {#each rec.steps as step, i (step.rank)}
+        <div class="field-row">
+          <label for="rank-f-label-{step.rank}">Rang {step.rank}</label>
+          <input id="rank-f-label-{step.rank}" type="text" bind:value={creationState.sheetDetail.steps[i].label}>
+        </div>
+        <div class="field-row">
+          <label for="rank-f-points-{step.rank}">{step.rank < 5 ? 'Points pour passer au rang suivant' : 'Rang le plus haut'}</label>
+          {#if step.rank < 5}
+            <input id="rank-f-points-{step.rank}" type="number" min="1" step="1"
+              bind:value={creationState.sheetDetail.steps[i].points_to_next}>
+          {/if}
+        </div>
+      {/each}
+    </div>
+  </div>
+{:else if rec && rec.kind === 'assistant'}
   <div class="field-section">
     <div class="field-row">
       <label for="competences-gen-brief">Intention</label>
@@ -136,6 +180,7 @@
       </div>
     </div>
   </div>
+  {@render thresholds()}
 {:else if rec && rec.kind === 'system'}
   {#if rec.persisted}
     <div style="display:flex; justify-content:flex-end; margin-bottom:8px;">
@@ -157,6 +202,7 @@
       <div style="margin-top:8px; font-size:12px; color:var(--muted)">{rec.skill_count} compétence(s) dans ce système.</div>
     {/if}
   </div>
+  {@render thresholds()}
 {/if}
 
 <Modal title={rec && rec.kind === 'system' ? 'Supprimer le système' : 'Supprimer la compétence'}
diff --git a/frontend/src/creation/competences.svelte.js b/frontend/src/creation/competences.svelte.js
index d7f0c3c..ea6df9d 100644
--- a/frontend/src/creation/competences.svelte.js
+++ b/frontend/src/creation/competences.svelte.js
@@ -22,13 +22,20 @@
    of this store, so editing a fiche changes nothing until Save.
    `persisted` is the one fact that decides POST vs PUT, the "Nouvelle"
    title and whether Delete shows -- never sheetIsNew, which a draft opened
-   from the list does not carry. */
+   from the list does not carry.
+
+   TICKET-0106 (BRIEF-0106-C, O1/P2): a skill and a system carry the five
+   optional rank thresholds (`points_to_rank_1..5`, null = inherit), and a
+   third record kind, 'ranks', edits the world's ladder (GET/PUT
+   /api/skill-ranks): each rank's name and the points to leave it. The most
+   specific value wins -- skill, then system, then world. */
 import { serverState } from '../lib/serverState.svelte.js';
 
 export const competencesState = $state({
   draft: [],   // proposed rows awaiting Save: {key, name, base_domain, system_id, description}
   rows: [],    // existing world-scoped skill_definition rows
   systems: [], // existing world-scoped skill_system rows
+  ranks: [],   // the world's ladder: {rank, label, points_to_next}, index = rank
   gaps: [],    // distinct unmatched surface forms, most frequent first
   arbiterFailures: { error: 0, empty: 0 },
   gapsError: '',
@@ -43,6 +50,28 @@ export const COMPETENCES_DOMAINS = ['physical', 'agility', 'perception', 'compos
 export const NO_SYSTEM_LABEL = 'Sans système';
 
 export const ASSISTANT_RECORD_ID = 'assistant';
+export const RANKS_RECORD_ID = 'ranks';
+
+// `points_to_rank_<n>` holds the points to REACH rank n (to leave rank n-1).
+export const RANK_POINT_KEYS = [1, 2, 3, 4, 5].map((n) => `points_to_rank_${n}`);
+
+function rankPoints(row) {
+  const points = {};
+  for (const key of RANK_POINT_KEYS) points[key] = row?.[key] ?? null;
+  return points;
+}
+
+/** The value a blank threshold inherits (O1): for a skill, its system's
+ *  value; then the world's. `n` is the rank reached (1-5). */
+export function inheritedPoints(record, n) {
+  const key = RANK_POINT_KEYS[n - 1];
+  if (record.kind === 'skill' && record.system_id) {
+    const sys = competencesState.systems.find((s) => s.id === record.system_id);
+    if (sys && sys[key] != null) return sys[key];
+  }
+  const step = competencesState.ranks[n - 1];
+  return step ? step.points_to_next : null;
+}
 
 let nextDraftKey = 1;
 
@@ -59,7 +88,7 @@ export function skillRecord(row) {
   return {
     kind: 'skill', persisted: true, id: row.id, draftKey: null,
     name: row.name, base_domain: row.base_domain, system_id: row.system_id ?? null,
-    description: row.description ?? '',
+    description: row.description ?? '', ...rankPoints(row),
   };
 }
 
@@ -67,6 +96,14 @@ export function systemRecord(sys) {
   return {
     kind: 'system', persisted: true, id: sys.id,
     name: sys.name, description: sys.description ?? '', skill_count: sys.skill_count ?? 0,
+    ...rankPoints(sys),
+  };
+}
+
+export function ranksRecord() {
+  return {
+    kind: 'ranks', persisted: true, id: RANKS_RECORD_ID,
+    steps: competencesState.ranks.map((r) => ({ ...r })),
   };
 }
 
@@ -74,7 +111,7 @@ export function draftRecord(d) {
   return {
     kind: 'skill', persisted: false, id: `draft:${d.key}`, draftKey: d.key,
     name: d.name ?? '', base_domain: d.base_domain ?? '', system_id: d.system_id ?? null,
-    description: d.description ?? '',
+    description: d.description ?? '', ...rankPoints(null),
   };
 }
 
@@ -87,11 +124,13 @@ export function assistantRecord() {
  *  (TICKET-0099, G1), a skill otherwise. */
 export function blankRecord(kind) {
   if (kind === 'system') {
-    return { kind: 'system', persisted: false, id: null, name: '', description: '', skill_count: 0 };
+    return {
+      kind: 'system', persisted: false, id: null, name: '', description: '', skill_count: 0, ...rankPoints(null),
+    };
   }
   return {
     kind: 'skill', persisted: false, id: null, draftKey: null,
-    name: '', base_domain: 'physical', system_id: null, description: '',
+    name: '', base_domain: 'physical', system_id: null, description: '', ...rankPoints(null),
   };
 }
 
@@ -99,6 +138,7 @@ export function blankRecord(kind) {
 export function competenceSheetTitle(record) {
   if (!record) return '';
   if (record.kind === 'assistant') return 'Assistant de compétences';
+  if (record.kind === 'ranks') return 'Rangs du monde';
   if (record.kind === 'system') return record.persisted ? record.name : 'Nouveau système';
   return record.persisted ? record.name : 'Nouvelle compétence';
 }
@@ -113,12 +153,14 @@ export async function loadCatalogue() {
     competencesState.draft = [];
     competencesState.draftWorldId = serverState.worldId;
   }
-  const [rows, systems] = await Promise.all([
+  const [rows, systems, ranks] = await Promise.all([
     api('/api/skill-definitions'),
     api('/api/skill-systems'),
+    api('/api/skill-ranks'),
   ]);
   competencesState.rows = rows;
   competencesState.systems = systems;
+  competencesState.ranks = ranks;
   await loadGaps();
 }
 
@@ -189,6 +231,20 @@ export function discardDraft(key) {
 
 /* ── Writes (C-04) ──────────────────────────────────────────────────────── */
 
+/** A threshold input's value: an integer >= 1, or null (inherit). */
+function pointsValue(value) {
+  if (value === null || value === undefined || value === '') return null;
+  const n = Number(value);
+  if (!Number.isInteger(n) || n < 1) throw new Error('Un seuil est un nombre entier de points, au moins 1.');
+  return n;
+}
+
+function pointsBody(record) {
+  const points = {};
+  for (const key of RANK_POINT_KEYS) points[key] = pointsValue(record[key]);
+  return points;
+}
+
 function requireName(record) {
   const name = (record.name || '').trim();
   if (!name) throw new Error('Nom requis.');
@@ -200,7 +256,7 @@ async function saveSkill(record) {
   if (!COMPETENCES_DOMAINS.includes(record.base_domain)) throw new Error('Domaine de base requis.');
   const body = JSON.stringify({
     name, base_domain: record.base_domain, system_id: record.system_id || null,
-    description: record.description || '',
+    description: record.description || '', ...pointsBody(record),
   });
   const saved = record.persisted
     ? await api(`/api/skill-definitions/${record.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body })
@@ -211,18 +267,34 @@ async function saveSkill(record) {
 
 async function saveSystem(record) {
   const name = requireName(record);
-  const body = JSON.stringify({ name, description: record.description || null });
+  const body = JSON.stringify({ name, description: record.description || null, ...pointsBody(record) });
   const saved = record.persisted
     ? await api(`/api/skill-systems/${record.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body })
     : await api('/api/skill-systems', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body });
   return systemRecord(saved);
 }
 
+async function saveRanks(record) {
+  const ranks = record.steps.map((step) => {
+    const label = (step.label || '').trim();
+    if (!label) throw new Error('Chaque rang a un nom.');
+    return { rank: step.rank, label, points_to_next: step.rank < 5 ? pointsValue(step.points_to_next) : null };
+  });
+  if (ranks.some((step) => step.rank < 5 && step.points_to_next === null)) {
+    throw new Error('Chaque rang sauf le dernier demande un nombre de points.');
+  }
+  competencesState.ranks = await api('/api/skill-ranks', {
+    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ranks }),
+  });
+  return ranksRecord();
+}
+
 /** Saves the open fiche's record; returns the saved record (C-01). Throws
  *  Error with a French message on a refused or failed write. */
 export async function saveCompetenceRecord(record) {
   if (record.kind === 'skill') return saveSkill(record);
   if (record.kind === 'system') return saveSystem(record);
+  if (record.kind === 'ranks') return saveRanks(record);
   throw new Error('Rien à enregistrer.');
 }
 
diff --git a/src/world_engine/cockpit/crud/skills.py b/src/world_engine/cockpit/crud/skills.py
index 04fdedf..7e7bab8 100644
--- a/src/world_engine/cockpit/crud/skills.py
+++ b/src/world_engine/cockpit/crud/skills.py
@@ -12,7 +12,7 @@ from datetime import UTC, datetime
 from typing import Any, Optional
 
 from fastapi import APIRouter, Depends, HTTPException, Query
-from pydantic import BaseModel
+from pydantic import BaseModel, Field
 from sqlalchemy import func
 from sqlalchemy.exc import IntegrityError
 from sqlmodel import Session as DbSession, select
@@ -53,7 +53,7 @@ from ...models import (
 )
 from ...prompt_registry import PROMPT_REGISTRY, effective_model
 from ...prompt_store import current_prompt, get_version, list_versions
-from ...skill_ranks import DEFAULT_RANK, RANKS, RankStep, points_to_next, skill_owners, world_ladder
+from ...skill_ranks import DEFAULT_RANK, RANK_POINTS_COLUMNS, RANKS, RankStep, points_to_next, skill_owners, world_ladder
 from ...tick_normalize import _EVENT_TYPES
 from ...writes import (
     KNOWLEDGE_LEVELS,
@@ -78,6 +78,7 @@ from ...writes import (
     write_npc_prices,
     write_prompt_version,
     write_relation,
+    upsert_skill_rank,
     write_skill_rank,
 )
 
@@ -118,6 +119,36 @@ def list_skill_ranks(db: DbSession = Depends(get_session)) -> list[dict]:
     return [_rank_step_dict(step) for step in world_ladder(db, _world_id(db))]
 
 
+class SkillRankStepBody(BaseModel):
+    rank: int
+    label: str
+    points_to_next: Optional[int] = None
+
+
+class SkillRanksBody(BaseModel):
+    ranks: list[SkillRankStepBody]
+
+
+@router.put("/skill-ranks")
+def update_skill_ranks(body: SkillRanksBody, db: DbSession = Depends(get_session)) -> list[dict]:
+    """Creator edit of the active world's ladder (TICKET-0106, BRIEF-0106-C,
+    P2/O1): all six ranks at once, each a name and, below Maître, the points
+    to leave it. Upserts the six `skill_rank` rows in one transaction; 422 on
+    any invalid step, before any write."""
+    world_id = _world_id(db)
+    if sorted(step.rank for step in body.ranks) != list(RANKS):
+        raise HTTPException(422, f"ranks must list each of {RANKS} exactly once")
+    try:
+        for step in body.ranks:
+            upsert_skill_rank(db, world_id=world_id, rank=step.rank, label=step.label,
+                              points_to_next=step.points_to_next)
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(422, str(exc))
+    db.commit()
+    return [_rank_step_dict(step) for step in world_ladder(db, world_id)]
+
+
 @router.get("/skills/player-characters")
 def list_skill_player_characters(db: DbSession = Depends(get_session)) -> list[dict]:
     """Player characters (`character_type = 'player'`), for the Fiche selector."""
@@ -186,6 +217,7 @@ def _skill_system_dict(s: SkillSystem, db: DbSession) -> dict:
         "name": s.name,
         "description": s.description,
         "skill_count": skill_count,
+        **_rank_points(s),
         "updated_at": _iso(s.updated_at),
     }
 
@@ -201,7 +233,27 @@ def list_skill_systems(db: DbSession = Depends(get_session)) -> list[dict]:
     return [_skill_system_dict(s, db) for s in rows]
 
 
-class SkillSystemWriteBody(BaseModel):
+class RankPointsBody(BaseModel):
+    """The five optional rank thresholds of a system or a skill (TICKET-0106,
+    BRIEF-0106-C, O1): a positive count, or None to inherit. A PUT replaces
+    all five, like every other field of its body."""
+    points_to_rank_1: Optional[int] = Field(default=None, ge=1)
+    points_to_rank_2: Optional[int] = Field(default=None, ge=1)
+    points_to_rank_3: Optional[int] = Field(default=None, ge=1)
+    points_to_rank_4: Optional[int] = Field(default=None, ge=1)
+    points_to_rank_5: Optional[int] = Field(default=None, ge=1)
+
+
+def _rank_points(row: Any) -> dict:
+    return {column: getattr(row, column) for column in RANK_POINTS_COLUMNS}
+
+
+def _set_rank_points(row: Any, body: RankPointsBody) -> None:
+    for column in RANK_POINTS_COLUMNS:
+        setattr(row, column, getattr(body, column))
+
+
+class SkillSystemWriteBody(RankPointsBody):
     name: str
     description: Optional[str] = None
 
@@ -221,6 +273,7 @@ def create_skill_system(
         raise HTTPException(422, "name is required")
 
     system = SkillSystem(world_id=world_id, name=name, description=body.description)
+    _set_rank_points(system, body)
     db.add(system)
     try:
         db.commit()
@@ -245,6 +298,7 @@ def update_skill_system(
 
     system.name = name
     system.description = body.description
+    _set_rank_points(system, body)
     system.updated_at = datetime.now(UTC)
     db.add(system)
     try:
@@ -335,6 +389,7 @@ def _skill_definition_dict(d: SkillDefinition) -> dict:
         "base_domain": d.base_domain,
         "system_id": d.system_id,
         "description": d.description,
+        **_rank_points(d),
         "updated_at": _iso(d.updated_at),
     }
 
@@ -350,7 +405,7 @@ def list_skill_definitions(db: DbSession = Depends(get_session)) -> list[dict]:
     return [_skill_definition_dict(d) for d in rows]
 
 
-class SkillDefinitionWriteBody(BaseModel):
+class SkillDefinitionWriteBody(RankPointsBody):
     name: str
     base_domain: str
     system_id: Optional[str] = None
@@ -388,6 +443,7 @@ def create_skill_definition(
         system_id=body.system_id,
         description=body.description,
     )
+    _set_rank_points(definition, body)
     db.add(definition)
     try:
         db.flush()
@@ -447,6 +503,7 @@ def update_skill_definition(
     definition.base_domain = body.base_domain
     definition.system_id = body.system_id
     definition.description = body.description
+    _set_rank_points(definition, body)
     definition.updated_at = datetime.now(UTC)
     db.add(definition)
 
diff --git a/src/world_engine/writes/__init__.py b/src/world_engine/writes/__init__.py
index 0fd3720..e87eccc 100644
--- a/src/world_engine/writes/__init__.py
+++ b/src/world_engine/writes/__init__.py
@@ -56,6 +56,7 @@ from .characters import (
 from .config import (
     upsert_conversation_window_config,
     upsert_location_type,
+    upsert_skill_rank,
     write_location_doors,
     write_location_obstacles,
     write_npc_prices,
diff --git a/src/world_engine/writes/config.py b/src/world_engine/writes/config.py
index 92c6d8b..4999969 100644
--- a/src/world_engine/writes/config.py
+++ b/src/world_engine/writes/config.py
@@ -35,6 +35,11 @@ none of these three functions were baselined.
   curated-config discipline as `write_location_doors`: no `change_history`,
   delete-then-insert inside the caller's transaction. Sparse by decision
   (B1): an empty `rows` list is legal.
+- `upsert_skill_rank(...)`              : upsert-one of a world's
+  `skill_rank` row for one rank (TICKET-0106, BRIEF-0106-C — the rank's
+  name and the default points to leave it). Same curated-config discipline
+  as `upsert_conversation_window_config`: no `change_history`,
+  fetch-or-create, never a DELETE.
 """
 
 from __future__ import annotations
@@ -60,9 +65,11 @@ from ..models import (
     ObstacleVertex,
     Relation,
     SCHEDULE_PHASES,
+    SkillRank,
     World,
     WorldLaw,
 )
+from ..skill_ranks import MAX_RANK, RANKS
 from ..zone_rules import require_visitable
 
 
@@ -524,3 +531,39 @@ def _record_schedule_encounters(
             record_encounter(
                 db, world_id=world_id, a_id=npc_id, b_id=other_id, source="schedule",
             )
+
+
+def upsert_skill_rank(
+    db: Session,
+    *,
+    world_id: str,
+    rank: int,
+    label: str,
+    points_to_next: Optional[int],
+) -> SkillRank:
+    """Upsert the `skill_rank` row of one (world, rank). Caller commits.
+
+    `label` is stripped and must be non-empty; `points_to_next` is a
+    positive integer below MAX_RANK and None at MAX_RANK (the table's own
+    CHECK, raised here as `ValueError` before any write). Fetch-or-create:
+    never a DELETE (TICKET-0106, BRIEF-0106-C).
+    """
+    if rank not in RANKS:
+        raise ValueError(f"upsert_skill_rank: rank {rank!r} is not one of {RANKS}")
+    label = (label or "").strip()
+    if not label:
+        raise ValueError("upsert_skill_rank: label must be a non-empty string")
+    if rank == MAX_RANK and points_to_next is not None:
+        raise ValueError("upsert_skill_rank: the top rank has no next rank")
+    if rank < MAX_RANK and (not isinstance(points_to_next, int) or isinstance(points_to_next, bool)
+                            or points_to_next < 1):
+        raise ValueError(f"upsert_skill_rank: points_to_next must be an integer >= 1, got {points_to_next!r}")
+    row = db.exec(select(SkillRank).where(SkillRank.world_id == world_id, SkillRank.rank == rank)).first()
+    if row is None:
+        row = SkillRank(world_id=world_id, rank=rank, label=label, points_to_next=points_to_next)
+    else:
+        row.label = label
+        row.points_to_next = points_to_next
+        row.updated_at = datetime.now(UTC)
+    db.add(row)
+    return row
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 301933e..ea20b77 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17944,6 +17944,22 @@ single points. Q3, a direct write outside `_apply_mutation`: a third canon
 write path. Y1a, a line-neutral edit of `_appendVerdict`: it would break
 the seal for one function.
 
+
+## THE CREATOR SETS THE RANKS (TICKET-0106) -- A LADDER PER WORLD, THRESHOLDS PER SYSTEM AND SKILL (BRIEF-0106-c, no schema change)
+
+**W1, P2, O1.** Création › Compétences carries a « Rangs du monde » record:
+the six rank names of the world and the points to leave each rank below
+Maître, saved all at once (`PUT /api/skill-ranks`, six
+`writes.upsert_skill_rank` calls, one transaction, 422 before any write on
+an invalid step). A system's and a skill's fiche carry the five thresholds
+(`points_to_rank_<n>`): blank inherits, and shows the inherited value as a
+placeholder -- for a skill, its system's value, then the world's. A PUT of
+a system or a skill replaces its thresholds like every other field of its
+body.
+
+**Rejected.** Labels per system (P1): one ladder per world is simpler to
+edit; reactivates if two systems of one world need different rank names.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index 6e07a71..d8a8e21 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -40,6 +40,8 @@ src/world_engine/writes/config.py::upsert_location_type        location_type_cat
 src/world_engine/writes/config.py::upsert_conversation_window_config conversation_window_config
 # TICKET-0074, BRIEF-0074-a: write_npc_schedule is the 29th site — standing per-phase location default, curated-config family (write_location_doors precedent).
 src/world_engine/writes/config.py::write_npc_schedule          npc_schedule
+# TICKET-0106, BRIEF-0106-C: upsert_skill_rank is the one writer of skill_rank -- a world's rank names and default points, curated-config family (upsert_conversation_window_config precedent), never a DELETE.
+src/world_engine/writes/config.py::upsert_skill_rank           skill_rank
 # TICKET-0101, BRIEF-0101-C: apply_promotion moves the items and discoverable details lying in a location that becomes a zone to its first child (creator CRUD only, behind the S1 confirmation); its characters, schedules and links go through write_character_location, write_npc_schedule and write_relation, allow-listed above.
 src/world_engine/writes/zone_promotion.py::apply_promotion     item discoverable_detail
 # TICKET-0075, BRIEF-0075-b: write_day_plan is the 30th site — its OWN body writes agenda_step_requirement only (it calls write_agenda/write_agenda_step, whose own db.add sites are already allow-listed above; single_canon_write.py is function-scoped, not interprocedural).
diff --git a/tooling/verify/checks/skill_progression.py b/tooling/verify/checks/skill_progression.py
index 14d857a..7cd4bdc 100644
--- a/tooling/verify/checks/skill_progression.py
+++ b/tooling/verify/checks/skill_progression.py
@@ -69,6 +69,25 @@ B4 -- wiring (static). `_apply_mutation` dispatches `skill_progress` to
    names `skill_progress` as auto-applied; `ARCHITECTURE_DECISIONS.md`'s
    "Auto-applied mutations" section names it.
 
+C1 -- the ladder (BRIEF-0106-C, fixture). `upsert_skill_rank` creates one
+   row per (world, rank) and updates it on a second call; it refuses an
+   empty label, points at rank 5, no points or 0 below rank 5, and rank 6,
+   each with `ValueError` before any write. `PUT /api/skill-ranks` refuses a
+   body without each rank exactly once (422) and a body with one invalid step
+   (422, no row written), and with six valid steps serves and stores them.
+C2 -- the thresholds (fixture). `POST /api/skill-systems` and `POST
+   /api/skill-definitions` store `points_to_rank_<n>` and serve them; a PUT
+   without them clears them; a body with 0 is refused by its model. With a
+   system setting rank 2 at 7, a skill of that system setting rank 3 at 3,
+   and the world's ladder renamed, `GET /api/skills` serves the skill's
+   `points_to_next` from the most specific level.
+C3 -- the Compétences UI (static). `CompetencesList.svelte` lists « Rangs
+   du monde » through `ranksRecord()`; `CompetencesSheet.svelte` renders a
+   `ranks` record and the `RANK_POINT_KEYS` inputs with `inheritedPoints`
+   placeholders on both fiches; `competences.svelte.js` PUTs
+   `/api/skill-ranks` and sends `pointsBody(record)` with a skill and with a
+   system; the built bundle carries « Rangs du monde ».
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that examines zero rows is a
 FAILURE.
@@ -599,6 +618,133 @@ def check_b4() -> None:
         fail("B4: the Auto-applied mutations section does not name skill_progress")
 
 
+# --- C1-C3 ---------------------------------------------------------------------
+
+def _c_world(session) -> dict:
+    from sqlmodel import select
+
+    from world_engine.models import Character, Entity, Skill, World
+
+    for world in session.exec(select(World)).all():
+        world.is_active = False
+        session.add(world)
+    world = World(name="Ranks C", is_active=True)
+    session.add(world)
+    session.flush()
+    pc = Entity(world_id=world.id, type="character", name="PC C")
+    session.add(pc)
+    session.flush()
+    session.add(Character(id=pc.id, world_id=world.id, character_type="player"))
+    session.add(Skill(character_id=pc.id, domain="agility", rank=2))
+    session.commit()
+    return {"world": world.id, "pc": pc.id}
+
+
+def check_c1(engine) -> None:
+    from fastapi import HTTPException
+    from sqlmodel import Session, select
+
+    from world_engine.cockpit.crud.skills import SkillRanksBody, update_skill_ranks
+    from world_engine.models import SkillRank
+    from world_engine.writes import upsert_skill_rank
+
+    with Session(engine) as session:
+        ids = _c_world(session)
+        upsert_skill_rank(session, world_id=ids["world"], rank=1, label="Novice", points_to_next=4)
+        session.commit()
+        upsert_skill_rank(session, world_id=ids["world"], rank=1, label="Élève", points_to_next=6)
+        session.commit()
+        rows = session.exec(select(SkillRank).where(SkillRank.world_id == ids["world"])).all()
+        if [(r.rank, r.label, r.points_to_next) for r in rows] != [(1, "Élève", 6)]:
+            fail(f"C1: two upserts left {[(r.rank, r.label, r.points_to_next) for r in rows]}")
+        for rank, label, points in ((2, "  ", 5), (5, "Maître", 3), (3, "x", None), (3, "x", 0), (6, "x", 1)):
+            try:
+                upsert_skill_rank(session, world_id=ids["world"], rank=rank, label=label, points_to_next=points)
+                fail(f"C1: upsert_skill_rank accepted rank {rank}, {label!r}, {points}")
+            except ValueError:
+                pass
+        session.rollback()
+        steps = [{"rank": r, "label": f"R{r}", "points_to_next": None if r == 5 else r + 1} for r in range(6)]
+        for bad in (steps[:5], steps[:5] + [{"rank": 5, "label": "R5", "points_to_next": 9}]):
+            try:
+                update_skill_ranks(SkillRanksBody(ranks=bad), session)
+                fail(f"C1: PUT accepted {bad[-1]}")
+            except HTTPException as exc:
+                if exc.status_code != 422:
+                    fail(f"C1: PUT answered {exc.status_code}")
+        if session.get(SkillRank, rows[0].id).label != "Élève" or len(
+                session.exec(select(SkillRank).where(SkillRank.world_id == ids["world"])).all()) != 1:
+            fail("C1: a refused PUT wrote rows")
+        served = update_skill_ranks(SkillRanksBody(ranks=steps), session)
+        if [(s["label"], s["points_to_next"]) for s in served] != [(f"R{r}", None if r == 5 else r + 1) for r in range(6)]:
+            fail(f"C1: PUT served {served}")
+
+
+def check_c2(engine) -> None:
+    from pydantic import ValidationError
+    from sqlmodel import Session
+
+    from world_engine.cockpit.crud.skills import (
+        SkillDefinitionWriteBody, SkillRanksBody, SkillSystemWriteBody, create_skill_definition,
+        create_skill_system, list_skills, update_skill_ranks, update_skill_system,
+    )
+    from world_engine.models import Skill, SkillSystem
+
+    with Session(engine) as session:
+        ids = _c_world(session)
+        system = create_skill_system(SkillSystemWriteBody(name="Épée", points_to_rank_2=7), session)
+        if system.get("points_to_rank_2") != 7 or system.get("points_to_rank_1") is not None:
+            fail(f"C2: the system was served {system}")
+        cleared = update_skill_system(system["id"], SkillSystemWriteBody(name="Épée"), session)
+        if cleared.get("points_to_rank_2") is not None or session.get(SkillSystem, system["id"]).points_to_rank_2:
+            fail(f"C2: a PUT without thresholds left {cleared}")
+        update_skill_system(system["id"], SkillSystemWriteBody(name="Épée", points_to_rank_2=7), session)
+        for body in (SkillSystemWriteBody, SkillDefinitionWriteBody):
+            try:
+                body(name="x", base_domain="agility", points_to_rank_1=0)
+                fail(f"C2: {body.__name__} accepted 0 points")
+            except ValidationError:
+                pass
+        definition = create_skill_definition(SkillDefinitionWriteBody(
+            name="Rapière", base_domain="agility", system_id=system["id"], points_to_rank_3=3), session)
+        if definition.get("points_to_rank_3") != 3:
+            fail(f"C2: the definition was served {definition}")
+        steps = [{"rank": r, "label": f"N{r}", "points_to_next": 50 + r if r < 5 else None} for r in range(6)]
+        update_skill_ranks(SkillRanksBody(ranks=steps), session)
+        custom = session.exec(__import__("sqlmodel").select(Skill).where(
+            Skill.skill_definition_id == definition["id"])).first()
+        sheet = {row["id"]: row for row in list_skills(character_id=ids["pc"], db=session)}
+        cases = ((1, 7), (2, 3), (3, 53))
+        for rank, want in cases:
+            custom.rank = rank
+            session.add(custom)
+            session.commit()
+            sheet = {row["id"]: row for row in list_skills(character_id=ids["pc"], db=session)}
+            got = sheet[custom.id]
+            if (got["points_to_next"], got["rank_label"]) != (want, f"N{rank}"):
+                fail(f"C2: rank {rank} was served {got['points_to_next']} / {got['rank_label']}, want {want}")
+        if not any(row["definition_name"] is None and row["points_to_next"] == 52 for row in sheet.values()):
+            fail(f"C2: the base agility row (rank 2) does not read the world's 52: {list(sheet.values())}")
+
+
+def check_c3() -> None:
+    root = ROOT / "frontend" / "src" / "creation"
+    listing = (root / "CompetencesList.svelte").read_text(encoding="utf-8")
+    sheet = (root / "CompetencesSheet.svelte").read_text(encoding="utf-8")
+    state = (root / "competences.svelte.js").read_text(encoding="utf-8")
+    if "Rangs du monde" not in listing or "ranksRecord()" not in listing:
+        fail("C3: CompetencesList.svelte does not list the world's ranks")
+    if "rec.kind === 'ranks'" not in sheet or "RANK_POINT_KEYS" not in sheet or "inheritedPoints(" not in sheet \
+            or sheet.count("{@render thresholds()}") != 2:
+        fail("C3: CompetencesSheet.svelte does not render the ranks record and both threshold blocks")
+    if "'/api/skill-ranks', {" not in state or state.count("...pointsBody(record)") != 2:
+        fail("C3: competences.svelte.js does not PUT the ladder and send the thresholds of both records")
+    bundle = "".join(p.read_text(encoding="utf-8") for p in
+                     (ROOT / "src" / "world_engine" / "cockpit" / "static" / "assets").glob("*.js"))
+    if "Rangs du monde" not in bundle:
+        fail("C3: the built bundle does not carry « Rangs du monde »")
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_a1()
@@ -612,6 +758,9 @@ def main() -> int:
     check_b2(engine)
     check_b3(engine)
     check_b4()
+    check_c1(engine)
+    check_c2(engine)
+    check_c3()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -619,7 +768,8 @@ def main() -> int:
     print("PASS: skill_progression -- v2.15 gives a skill a rank (0-5) and points in place of "
           "its tier, keeps every former tier's roll, lets a world, a system and a skill set "
           "the points of each rank, and migrates from v2.14 only; every roll earns a point, "
-          "auto-applied in Play and given at a day step's approval, and a threshold moves the rank")
+          "auto-applied in Play and given at a day step's approval, and a threshold moves the rank; "
+          "the creator names the ranks and sets their points per world, system and skill")
     return 0
 
 
````

## Scope OUT

- Rank names per system (P1, rejected).
- Deleting a `skill_rank` row, or a « reset to the engine default » button: the creator types the default values back.
- The AI skill-catalogue assistant proposing thresholds (`generate_skill_catalogue_draft` is untouched; its drafts start with none).
- Any change to `Sheet.svelte`, `EntityList.svelte` or the Création registry.
- Showing points on the PC fiche or in the day's account (D).
- Every later brief of this lot.

## Invariants to defend

**Creator control is structural:** the ladder and the thresholds are written only by the creator CRUD, through `upsert_skill_rank` and the existing allow-listed skill routes. **UI-visible data never lives in JSON:** every threshold is a column. **Every Création page is a `CREATION_TABS` registry entry:** the new record lives inside the Compétences entry; no page branch is added.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `page_contract.py`, `creation_tab_switch.py`, `creation_island.py` or `single_canon_write.py` fails.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).
- The pre-existing Svelte build warning on `<option value="">` in another Création file.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and the rebuilt `src/world_engine/cockpit/static/` files.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/skill_progression.py` → `PASS: skill_progression -- … the creator names the ranks and sets their points per world, system and skill`.
- `single_canon_write.py`, `page_contract.py`, `creation_tab_switch.py`, `creation_island.py`, `json_ui_boundary.py`, `effect_self_write.py`, `module_budget.py`, `frontend_build_fresh.py`, `decisions_index.py` → `PASS`.
- Mutation tests, each red then reverted: in `update_skill_ranks`, `    if sorted(step.rank for step in body.ranks) != list(RANKS):` → `    if False:` → `C1`; in `_set_rank_points`, `        setattr(row, column, getattr(body, column))` → `        pass` → `C2`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 139/139.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `THE CREATOR SETS THE RANKS (TICKET-0106) -- A LADDER PER WORLD, THRESHOLDS PER SYSTEM AND SKILL (BRIEF-0106-c, no schema change)` — in the diff. CLAUDE.md: nothing.
