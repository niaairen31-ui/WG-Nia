<!-- slug: creator-surface -->
# BRIEF 0097-F — "The creator surface writes facts; the worklist lists facts"

Lot: LOT-0097-knowledge-identity.md (authoritative on conflict)
Depends on: E
Commit header for decisions: `(BRIEF-0097-f, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0097` before applying anything. Halt if one has moved.

- `src/world_engine/cockpit/crud/knowledge.py:142` → `@router.get("/worlds/{world_id}/unresolved-subjects")`
- `src/world_engine/cockpit/crud/_shared.py:222` → `{"name": "subject", "label": "Subject", "kind": "text", "required": True},`
- `src/world_engine/subject_resolve.py` → exists; `_SUBJECT_CATEGORIES` frozen (N10a)
- `src/world_engine/lore_mentions_read.py:99` → `def lookup_surface(db: Session, world_id: str, surface: str) -> dict:`
- `frontend/src/creation/tabs.js` → `subjects:` tab labelled `'Sujets'`, island `subjectWorklist`
- `CLAUDE.md` File structure → 80 lines, with the line `lore_*.py, subject_resolve.py`

## Facts carried

### R-12 — the names panel resolver
Opened: `lore_mentions_read.py:55-105`, `lore_resolve.py:143-230`.
Finding: `lookup_surface(db, world_id, surface)` returns `{"surface",
"candidates": [{"id","name","type"}], "near": [{"id","name","type","score"}]}`
over every category under the `creator` regime.
Consequence: F's worklist reuses it (I1); no second resolver.

### R-13 — creator surface
Opened: `frontend/src/creation/{KnowledgeEditor,SubjectWorklist,PendingKnowledgeEditor,QueueCard,PjCreatePanel,LinkAgent,Sheet}.svelte`,
`subjectWorklist.svelte.js`, `pendingDrafts.svelte.js`, `registry.js:542-550`,
`tabs.js:328-336`, `frontend/src/journee/Journee.svelte:151`,
`cockpit/crud/{knowledge,_shared}.py`, `cockpit/routes/{creator,npc_agent}.py`,
`entity_author.py:45-260`, `seed_pilot.py:276-412, 1196-1235`.
Finding: every create path requires a subject; the worklist binds by subject
over `/unresolved-subjects`; the analysis and generation prompts ask for one.
Consequence: F.

## Contracts

### C-08 — `GET /api/worlds/{world_id}/unbound-facts`
Produced by: F   Consumed by: F (frontend)
404 on an unknown world. A list, ordered by `knower_count` desc, fact text,
fact id, of:
```
{"fact_id", "fact", "knower_count",
 "excerpt": {"entity_name", "text"} | None,   # first knower by name; text clipped to 120 + "…"
 "candidates": [{"id","name","type"}], "near": [{"id","name","type","score"}]}
```
Only free facts known by an entity of the world and bound to no participant.

## Context

The creator no longer types a subject (K1): a new row is its content, its fact is born with that sentence. The « Sujets » worklist lists facts no participant binds, read through the names panel's resolver (I1, J1); `subject_resolve.py` goes.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below to a file and run `git apply --check <file>` then `git apply <file>` from the
repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff (it deletes `src/world_engine/subject_resolve.py`). It: creates `unbound_facts.py` and `GET /api/worlds/{id}/unbound-facts` (C-08); removes the Subject field from `KNOWLEDGE_FIELDS`, `_knowledge_dict`, the CRUD body, the PC body, the NPC agent commit, both generators' normalizers; rewords the analysis and PC prompts; rewrites the worklist state and panel and the knowledge, pending, queue, PC and link editors; updates CLAUDE.md (file-structure line, dedup invariant, new identity invariant); retargets `subject_resolution.py` A1/A2 and `name_resolution.py` G4; adds the two prompts to the apply script; adds K8.
2. Rebuild the frontend and commit `static/`.
3. Regenerate the index.
4. Message: `feat(creation): the creator surface writes facts; the worklist lists facts (BRIEF-0097-f)`.

```diff
diff --git a/CLAUDE.md b/CLAUDE.md
index 73a943e..cc4f39a 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -141,8 +141,10 @@ Law only. Rationale, chantier history, and deferred alternatives live in
   pair per window, proportionate to that window. Never deduplicated against
   prior windows (not covered by `_mutation_match_key`).
 - **`new_knowledge` / `status_change` are idempotent facts:** identity-based
-  dedup (`entity_id` + `subject`; `entity_id`) via `_mutation_match_key`,
-  same conversation required.
+  dedup (`entity_id` + `fact_refs.knowledge_key`; `entity_id`) via
+  `_mutation_match_key`, same conversation required.
+- **A `knowledge` row is identified by its fact:** `(entity_id, fact_id)` is unique. A model
+  names a fact only by a code from a `fact_refs.code_facts` list; code resolves it.
 - **Secrets are structurally excluded** from every assembled context — never
   "guarded by instruction". The creator's note on an entity (a `histoire`
   fact whose entity holds a `creator_meta` `is_secret` row) is excluded from
@@ -442,7 +444,7 @@ WG-Nia/
 │   ├── day_narration_guard.py  # T1 judge: name containment + outcome survival, Python-only
 │   ├── day_mutations.py     # day-chain mutation emission: proposer only, never applies (V1)
 │   ├── day_feasibility.py   # feasibility veto: downward-only, clamp_verdict is the safety (Y1)
-│   ├── lore_*.py, subject_resolve.py  # resolver/selectors/plan/names-panel reads; subject<->entity
+│   ├── lore_*.py, unbound_facts.py, fact_refs.py  # Lore reads; unbound facts; fact codes/keys
 │   ├── writes/               # canon-write helpers by domain; schema.py is the DDL authority
 │   ├── prompt_registry.py   # prompt wiring registry; effective_model resolver
 │   ├── prompt_store.py      # prompt_version read accessor (current_prompt et al.)
diff --git a/frontend/src/creation/KnowledgeEditor.svelte b/frontend/src/creation/KnowledgeEditor.svelte
index b54b3f8..41ae9d0 100644
--- a/frontend/src/creation/KnowledgeEditor.svelte
+++ b/frontend/src/creation/KnowledgeEditor.svelte
@@ -14,7 +14,7 @@
   $effect(() => {
     rows = (knowledge || []).map((k) => ({
       id: k.id,
-      subject: k.subject,
+      fact: k.fact_content ?? '',
       level: k.level,
       source: k.source ?? '',
       share_threshold: k.share_threshold,
@@ -33,14 +33,16 @@
      row's own fact, through the routes BRIEF-0082-b already exposes
      (POST/DELETE /api/facts/{fact_id}/participants[/{entity_id}]).
      Two lazily-loaded, world-scoped lists shared by every row: the picker's
-     candidate entities, and the resolver's suggestion per unresolved
-     subject (both come from GET /api/worlds/{world_id}/unresolved-subjects,
-     C-06 -- the same query the residue worklist reads). Loaded once per
-     world, reset when serverState.worldId changes (Registre.svelte's own
-     convention). */
+     candidate entities, and the resolver's suggestion per unbound fact
+     (TICKET-0097: GET /api/worlds/{world_id}/unbound-facts, C-08 -- the
+     same read the « Sujets » worklist shows; a suggestion exists when the
+     resolver found exactly one candidate). Loaded once per world, reset
+     when serverState.worldId changes (Registre.svelte's own convention).
+     A row shows its fact's text read-only (K1): the fact is what is known,
+     the row's content is this entity's version of it. */
   let subjectEntities = $state([]);
   let subjectEntitiesLoaded = false;
-  let subjectSuggestions = $state({}); // subject text -> suggested entity_id
+  let subjectSuggestions = $state({}); // fact_id -> suggested entity_id
   let subjectSuggestionsLoaded = false;
   let pickerSelections = $state({}); // knowledge row id -> chosen entity_id
 
@@ -65,10 +67,10 @@
     if (subjectSuggestionsLoaded || !serverState.worldId) return;
     subjectSuggestionsLoaded = true;
     try {
-      const residue = await api(`/api/worlds/${encodeURIComponent(serverState.worldId)}/unresolved-subjects`);
+      const residue = await api(`/api/worlds/${encodeURIComponent(serverState.worldId)}/unbound-facts`);
       const map = {};
       for (const r of residue) {
-        if (r.resolution && r.resolution.verdict === 'matched') map[r.subject] = r.resolution.entity_id;
+        if (r.candidates.length === 1) map[r.fact_id] = r.candidates[0].id;
       }
       subjectSuggestions = map;
     } catch (_err) { /* suggestion is advisory only */ }
@@ -76,7 +78,7 @@
 
   function pickerValue(row) {
     if (row.id in pickerSelections) return pickerSelections[row.id];
-    return subjectSuggestions[row.subject] || '';
+    return subjectSuggestions[row.fact_id] || '';
   }
 
   async function bindSubject(row) {
@@ -101,7 +103,6 @@
     );
   }
 
-  let newSubject = $state('');
   let newLevel = $state('rumor');
   let newSource = $state('');
   let newShareThreshold = $state(50);
@@ -115,7 +116,6 @@
 
   async function saveRow(row) {
     const body = JSON.stringify({
-      subject: row.subject,
       level: row.level,
       source: row.source || null,
       share_threshold: Number(row.share_threshold),
@@ -133,7 +133,6 @@
 
   async function addRow() {
     const body = JSON.stringify({
-      subject: newSubject,
       level: newLevel,
       source: newSource || null,
       share_threshold: Number(newShareThreshold),
@@ -143,7 +142,6 @@
     });
     const ok = await sheetRequest(legacyDoc, `/api/entities/${encodeURIComponent(entityId)}/knowledge`, 'POST', body, reloadEntity);
     if (ok) {
-      newSubject = '';
       newLevel = 'rumor';
       newSource = '';
       newShareThreshold = 50;
@@ -161,7 +159,7 @@
     {#each rows as row (row.id)}
       <div class="row-card">
         <div class="field-grid">
-          <div class="field-row"><label>Subject</label><input type="text" bind:value={row.subject}></div>
+          <div class="field-row span-2"><label>Fact</label><div>{row.fact}</div></div>
           <div class="field-row"><label>Level</label>
             <select bind:value={row.level}>
               {#each levelOptions as l}
@@ -211,7 +209,6 @@
 
 <div class="row-card">
   <div class="field-grid">
-    <div class="field-row"><label>Subject *</label><input type="text" bind:value={newSubject}></div>
     <div class="field-row"><label>Level *</label>
       <select bind:value={newLevel}>
         {#each levelOptions as l}
@@ -223,9 +220,9 @@
       <input type="number" min="1" max="100" bind:value={newShareThreshold}></div>
     <div class="field-row checkbox"><input type="checkbox" id="kn-new-incorrect" bind:checked={newIncorrect}><label for="kn-new-incorrect">Incorrect</label></div>
     <div class="field-row checkbox"><input type="checkbox" id="kn-new-secret" bind:checked={newSecret}><label for="kn-new-secret">Secret</label></div>
-    <div class="field-row span-2"><label>Content</label><textarea bind:value={newContent}></textarea></div>
+    <div class="field-row span-2"><label>Content *</label><textarea bind:value={newContent}></textarea></div>
   </div>
   <div class="row-card-actions">
-    <button class="btn-send" onclick={addRow}>Add knowledge</button>
+    <button class="btn-send" disabled={!newContent.trim()} onclick={addRow}>Add knowledge</button>
   </div>
 </div>
diff --git a/frontend/src/creation/LinkAgent.svelte b/frontend/src/creation/LinkAgent.svelte
index 5eaebf6..badcd1c 100644
--- a/frontend/src/creation/LinkAgent.svelte
+++ b/frontend/src/creation/LinkAgent.svelte
@@ -157,7 +157,7 @@
               </div>
             {:else if row.kind === 'knowledge'}
               {@const p = row.payload}
-              {@const aboutId = (p.subject || '').replace(/^npc:/, '')}
+              {@const aboutId = (p.subject_entity_ids || [])[0] || ''}
               <div class="linkagent-row {rejected ? 'rejected' : ''}">
                 <span class="badge b-other">knowledge</span>
                 <span style="font-size:11px; color:var(--muted)">{npcName(p.entity_id)} à propos de {npcName(aboutId)}</span>
diff --git a/frontend/src/creation/PendingKnowledgeEditor.svelte b/frontend/src/creation/PendingKnowledgeEditor.svelte
index 2b4641b..69ed36e 100644
--- a/frontend/src/creation/PendingKnowledgeEditor.svelte
+++ b/frontend/src/creation/PendingKnowledgeEditor.svelte
@@ -23,7 +23,6 @@
     {#each pendingDraftsState.knowledge as k, i}
       <div class="row-card">
         <div class="field-grid">
-          <div class="field-row"><label>Subject</label><input type="text" bind:value={k.subject}></div>
           <div class="field-row"><label>Level</label>
             <select bind:value={k.level}>
               {#each levelOptions as l}<option value={l}>{l}</option>{/each}
diff --git a/frontend/src/creation/PjCreatePanel.svelte b/frontend/src/creation/PjCreatePanel.svelte
index 1603a72..c8b5001 100644
--- a/frontend/src/creation/PjCreatePanel.svelte
+++ b/frontend/src/creation/PjCreatePanel.svelte
@@ -190,7 +190,7 @@
         (aucun)
       {:else}
         {#each draftKnowledge as k}
-          <div>{k.subject} ({k.level}) : {k.content}</div>
+          <div>({k.level}) {k.content}</div>
         {/each}
       {/if}
     </div>
diff --git a/frontend/src/creation/QueueCard.svelte b/frontend/src/creation/QueueCard.svelte
index 921aa5e..2d51cb0 100644
--- a/frontend/src/creation/QueueCard.svelte
+++ b/frontend/src/creation/QueueCard.svelte
@@ -78,7 +78,6 @@
       knowledge: k
         ? {
             entityName: mutationEntityName(k.entity_id),
-            subject: k.subject || '',
             level: k.level || '',
             content: k.content || '',
           }
@@ -197,7 +196,7 @@
         <div class="row-card" style="flex-direction:row; align-items:center; gap:10px; flex-wrap:wrap;">
           <span class="badge b-new_knowledge">knowledge</span>
           <span style="font-weight:600;">{resourceLegs.knowledge.entityName}</span>
-          <span style="color:var(--muted); font-size:12px;">{resourceLegs.knowledge.subject} · {resourceLegs.knowledge.level}</span>
+          <span style="color:var(--muted); font-size:12px;">{resourceLegs.knowledge.level}</span>
           {#if resourceLegs.knowledge.content}<span style="font-size:12px;">{resourceLegs.knowledge.content}</span>{/if}
         </div>
       {/if}
diff --git a/frontend/src/creation/Sheet.svelte b/frontend/src/creation/Sheet.svelte
index 9473356..edde031 100644
--- a/frontend/src/creation/Sheet.svelte
+++ b/frontend/src/creation/Sheet.svelte
@@ -500,7 +500,7 @@
             method: 'POST',
             headers: { 'Content-Type': 'application/json' },
             body: JSON.stringify({
-              subject: row.subject, level: row.level, source: null, share_threshold: 50,
+              level: row.level, source: null, share_threshold: 50,
               is_incorrect: false, is_secret: true, content: row.content,
             }),
           });
diff --git a/frontend/src/creation/SubjectWorklist.svelte b/frontend/src/creation/SubjectWorklist.svelte
index 40c2c19..08aca96 100644
--- a/frontend/src/creation/SubjectWorklist.svelte
+++ b/frontend/src/creation/SubjectWorklist.svelte
@@ -1,21 +1,23 @@
 <script>
-  /* TICKET-0088 (BRIEF-0088-b). The subject worklist: every knowledge
-     subject of the active world that no fact_participant binds yet, with a
-     one-action bind per subject. Its CREATION_ISLANDS entry declares
-     origin 'new' -- a surface created as an island, with no legacy
-     predecessor. State and requests live in subjectWorklist.svelte.js;
-     the empty and error states below are part of what the list means. */
+  /* TICKET-0088 (BRIEF-0088-b), re-aimed by TICKET-0097 (BRIEF-0097-f, I1/J1).
+     The « Sujets » worklist: every fact of the active world that someone
+     knows and no fact_participant binds yet, with a one-action bind per
+     fact. A card shows the fact's text, the first knower's version of it
+     and how many entities know it (J1), then the Lore resolver's candidates
+     and near names -- the resolver never picks. Its CREATION_ISLANDS entry
+     declares origin 'new'. State and requests live in
+     subjectWorklist.svelte.js; the empty and error states below are part of
+     what the list means. */
   import { serverState } from '../lib/serverState.svelte.js';
   import {
-    subjectState, loadSubjects, suggestedEntityId, selectedEntityId, selectEntity, bindSubject,
+    subjectState, loadFacts, suggestedEntityId, selectedEntityId, selectEntity, bindFact,
   } from './subjectWorklist.svelte.js';
 
   $effect(() => {
-    loadSubjects(serverState.worldId);
+    loadFacts(serverState.worldId);
   });
 
-  let busy = $derived(subjectState.bindingSubject !== null);
-  let lineTotal = $derived(subjectState.rows.reduce((n, r) => n + r.row_count, 0));
+  let busy = $derived(subjectState.bindingFact !== null);
 
   function entityLabel(id) {
     const e = subjectState.entities.find((x) => x.id === id);
@@ -26,8 +28,8 @@
 <div class="queue-panel">
   <div class="panel-head">
     <h2>Sujets non résolus</h2>
-    <span>{subjectState.rows.length} sujet(s) · {lineTotal} ligne(s)</span>
-    <button class="btn-icon" disabled={busy} onclick={() => loadSubjects(serverState.worldId)} title="Rafraîchir">↻</button>
+    <span>{subjectState.rows.length} fait(s)</span>
+    <button class="btn-icon" disabled={busy} onclick={() => loadFacts(serverState.worldId)} title="Rafraîchir">↻</button>
   </div>
   <div class="queue-body">
     {#if !serverState.worldId}
@@ -37,35 +39,40 @@
     {:else if subjectState.loadError}
       <div class="empty" style="color:var(--red)">Erreur : {subjectState.loadError}</div>
     {:else if subjectState.rows.length === 0}
-      <div class="empty-ok">✓ Aucun sujet non résolu dans ce monde.</div>
+      <div class="empty-ok">✓ Tous les faits connus de ce monde ont un sujet.</div>
     {:else}
-      {#each subjectState.rows as row (row.subject)}
+      {#each subjectState.rows as row (row.fact_id)}
         <div class="row-card">
-          <div><strong>{row.subject}</strong></div>
-          <div style="font-size:12px;">{row.row_count} ligne(s) · {row.fact_ids.length} fait(s)</div>
+          <div><strong>{row.fact}</strong></div>
+          {#if row.excerpt}
+            <div style="font-size:12px;">« {row.excerpt.text} » — {row.excerpt.entity_name}</div>
+          {/if}
+          <div style="font-size:12px; color:var(--muted);">{row.knower_count} personnage(s) le savent</div>
           <div style="font-size:12px;">
             {#if suggestedEntityId(row)}
               Suggestion : {entityLabel(suggestedEntityId(row))}
-            {:else if row.resolution && row.resolution.verdict === 'ambiguous'}
-              Ambigu : {row.resolution.candidate_ids.length} candidat(s)
+            {:else if row.candidates.length > 1}
+              Plusieurs candidats : {row.candidates.map((c) => c.name).join(', ')}
+            {:else if row.near.length > 0}
+              Noms proches : {row.near.map((c) => `${c.name} (${c.score})`).join(', ')}
             {:else}
               Aucune suggestion
             {/if}
           </div>
           <div class="row-card-actions">
             <select value={selectedEntityId(row)} disabled={busy}
-                    onchange={(e) => selectEntity(row.subject, e.target.value)}>
+                    onchange={(e) => selectEntity(row.fact_id, e.target.value)}>
               <option value="">—</option>
               {#each subjectState.entities as ent (ent.id)}
                 <option value={ent.id}>{ent.name} ({ent.type})</option>
               {/each}
             </select>
-            <button class="btn-send" disabled={busy || !selectedEntityId(row)} onclick={() => bindSubject(row)}>
-              {subjectState.bindingSubject === row.subject ? 'Liaison…' : 'Lier'}
+            <button class="btn-send" disabled={busy || !selectedEntityId(row)} onclick={() => bindFact(row)}>
+              {subjectState.bindingFact === row.fact_id ? 'Liaison…' : 'Lier'}
             </button>
           </div>
-          {#if subjectState.bindErrors[row.subject]}
-            <div style="color:var(--red); font-size:12px;">{subjectState.bindErrors[row.subject]}</div>
+          {#if subjectState.bindErrors[row.fact_id]}
+            <div style="color:var(--red); font-size:12px;">{subjectState.bindErrors[row.fact_id]}</div>
           {/if}
         </div>
       {/each}
diff --git a/frontend/src/creation/pendingDrafts.svelte.js b/frontend/src/creation/pendingDrafts.svelte.js
index afabf96..32f093c 100644
--- a/frontend/src/creation/pendingDrafts.svelte.js
+++ b/frontend/src/creation/pendingDrafts.svelte.js
@@ -23,7 +23,7 @@ export function resetPendingDrafts() {
 }
 
 export function knowledgeForCreate() {
-  return pendingDraftsState.knowledge.filter((k) => k.subject && k.content);
+  return pendingDraftsState.knowledge.filter((k) => k.content && k.content.trim());
 }
 
 export function goalsForCreate() {
diff --git a/frontend/src/creation/registry.js b/frontend/src/creation/registry.js
index c16a908..de5b524 100644
--- a/frontend/src/creation/registry.js
+++ b/frontend/src/creation/registry.js
@@ -541,7 +541,8 @@ export const CREATION_ISLANDS = Object.freeze({
   }),
   // TICKET-0088 (BRIEF-0088-b): the unresolved-subject worklist, the first
   // surface created directly as an island -- no legacy predecessor, so no
-  // migratedBy and no retiredPrefixes.
+  // migratedBy and no retiredPrefixes. Since TICKET-0097 it lists unbound
+  // facts (I1/J1); the key and container keep their names.
   subjectWorklist: Object.freeze({
     containerId: 'creation-subjects',
     component: 'SubjectWorklist.svelte',
diff --git a/frontend/src/creation/subjectWorklist.svelte.js b/frontend/src/creation/subjectWorklist.svelte.js
index 370fd7e..8f9a052 100644
--- a/frontend/src/creation/subjectWorklist.svelte.js
+++ b/frontend/src/creation/subjectWorklist.svelte.js
@@ -1,20 +1,18 @@
-/* TICKET-0088 (BRIEF-0088-b). State and requests for the subject worklist
-   (SubjectWorklist.svelte), the first Creation island whose registry entry
-   declares origin 'new'. Same split as queue.svelte.js / Queue.svelte:
-   this module owns the state and every request, the component renders.
+/* TICKET-0088 (BRIEF-0088-b), re-aimed by TICKET-0097 (BRIEF-0097-f, I1/J1).
+   State and requests for the « Sujets » worklist (SubjectWorklist.svelte).
+   Same split as queue.svelte.js / Queue.svelte: this module owns the state
+   and every request, the component renders.
 
-   Rows are GET /api/worlds/{world_id}/unresolved-subjects unchanged: one
-   row per distinct knowledge.subject whose facts carry no fact_participant
-   at all. Binding a subject is one POST /api/facts/{fact_id}/participants
-   per fact, sequential, with no role (decision E1). Each POST is correct
-   on its own; the first failure stops the loop; the reload that always
-   follows leaves a partly bound subject listed with only its unbound
-   facts, so a retry binds the remainder and never duplicates a
-   participant. The route answers 500 on a duplicate (fact, entity) pair,
-   which is why one bind at a time runs and every control stays disabled
-   until the reload that follows it has landed.
+   Rows are GET /api/worlds/{world_id}/unbound-facts unchanged: one row per
+   free fact someone knows and no fact_participant binds, with its text, the
+   first knower's version, the knower count, and the Lore resolver's
+   candidates and near names. Binding is ONE POST
+   /api/facts/{fact_id}/participants with no role (decision E1 of 0088). The
+   reload that always follows drops the bound fact from the list. Only one
+   bind runs at a time, and every control stays disabled until its reload
+   has landed (the route answers 500 on a duplicate (fact, entity) pair).
 
-   loadSubjects() is called from the component's $effect: before its first
+   loadFacts() is called from the component's $effect: before its first
    await it only WRITES subjectState, and the world it compares against is
    a plain module variable, so the effect depends on serverState.worldId
    alone. */
@@ -27,14 +25,14 @@ export const subjectState = $state({
   rows: [],
   entities: [],
   selections: {},
-  bindingSubject: null,
+  bindingFact: null,
   bindErrors: {},
 });
 
 let loadedWorldId = null;
 let loadSeq = 0;
 
-export async function loadSubjects(worldId) {
+export async function loadFacts(worldId) {
   const seq = ++loadSeq;
   if (worldId !== loadedWorldId) {
     loadedWorldId = worldId;
@@ -51,7 +49,7 @@ export async function loadSubjects(worldId) {
   subjectState.loading = true;
   try {
     const [rows, entities] = await Promise.all([
-      api(`/api/worlds/${encodeURIComponent(worldId)}/unresolved-subjects`),
+      api(`/api/worlds/${encodeURIComponent(worldId)}/unbound-facts`),
       api('/api/entities'),
     ]);
     if (seq !== loadSeq) return;
@@ -67,49 +65,42 @@ export async function loadSubjects(worldId) {
   }
 }
 
+/* A suggestion exists only when the resolver found exactly one candidate:
+   the resolver never picks between two. */
 export function suggestedEntityId(row) {
-  const r = row.resolution;
-  if (!r || r.verdict !== 'matched') return '';
-  return subjectState.entities.some((e) => e.id === r.entity_id) ? r.entity_id : '';
+  if (row.candidates.length !== 1) return '';
+  const id = row.candidates[0].id;
+  return subjectState.entities.some((e) => e.id === id) ? id : '';
 }
 
 export function selectedEntityId(row) {
-  const chosen = subjectState.selections[row.subject];
+  const chosen = subjectState.selections[row.fact_id];
   return chosen !== undefined ? chosen : suggestedEntityId(row);
 }
 
-export function selectEntity(subject, entityId) {
-  subjectState.selections = { ...subjectState.selections, [subject]: entityId };
+export function selectEntity(factId, entityId) {
+  subjectState.selections = { ...subjectState.selections, [factId]: entityId };
 }
 
-export async function bindSubject(row) {
+export async function bindFact(row) {
   const entityId = selectedEntityId(row);
-  if (!entityId || subjectState.bindingSubject !== null) return;
+  if (!entityId || subjectState.bindingFact !== null) return;
   const worldId = loadedWorldId;
-  const subject = row.subject;
-  const factIds = Array.from(row.fact_ids);
+  const factId = row.fact_id;
   const errors = { ...subjectState.bindErrors };
-  delete errors[subject];
+  delete errors[factId];
   subjectState.bindErrors = errors;
-  subjectState.bindingSubject = subject;
-  let bound = 0;
+  subjectState.bindingFact = factId;
   try {
-    for (const factId of factIds) {
-      if (serverState.worldId !== worldId) break;
-      await api(`/api/facts/${encodeURIComponent(factId)}/participants`, {
-        method: 'POST',
-        headers: { 'Content-Type': 'application/json' },
-        body: JSON.stringify({ entity_id: entityId }),
-      });
-      bound += 1;
-    }
+    await api(`/api/facts/${encodeURIComponent(factId)}/participants`, {
+      method: 'POST',
+      headers: { 'Content-Type': 'application/json' },
+      body: JSON.stringify({ entity_id: entityId }),
+    });
   } catch (e) {
-    subjectState.bindErrors = {
-      ...subjectState.bindErrors,
-      [subject]: `${bound}/${factIds.length} fait(s) lié(s) avant l'échec : ${e.message}`,
-    };
+    subjectState.bindErrors = { ...subjectState.bindErrors, [factId]: `Échec de la liaison : ${e.message}` };
   } finally {
-    if (serverState.worldId === worldId) await loadSubjects(worldId);
-    subjectState.bindingSubject = null;
+    if (serverState.worldId === worldId) await loadFacts(worldId);
+    subjectState.bindingFact = null;
   }
 }
diff --git a/scripts/apply_ticket_0097_fact_code_prompts.py b/scripts/apply_ticket_0097_fact_code_prompts.py
index 10d1ea5..e368981 100644
--- a/scripts/apply_ticket_0097_fact_code_prompts.py
+++ b/scripts/apply_ticket_0097_fact_code_prompts.py
@@ -8,6 +8,10 @@ live DB: models name facts by code, never by a free-text subject.
   passes on by its briefing code (`source_fact`).
 - `pt-day-plan` (BRIEF-0097-D, D1'a): a `knowledge` requirement's
   `target_key` is the code of a fact from the appended learnable list.
+- `pt-conversation-analysis` (BRIEF-0097-F, M1/N1): no `subject` in any
+  knowledge shape or example, and no `knowledge_change` type.
+- `pt-player-generation` (BRIEF-0097-F, K1): a knowledge item is a level and
+  a content, no subject.
 
 Embeds NO prompt text of its own; it imports each text from
 `scripts/seed_pilot.py` (single source of text). History is sacred: a changed
@@ -66,6 +70,20 @@ _UPDATES: tuple[tuple[str, str, str, list[str], str], ...] = (
         ["character_name", "declaration"],
         "TICKET-0097 BRIEF-0097-D -- a knowledge gate names its fact by code (D1'a)",
     ),
+    (
+        "pt-conversation-analysis",
+        seed_pilot.CONVERSATION_ANALYSIS_SYSTEM_PROMPT,
+        seed_pilot.CONVERSATION_ANALYSIS_USER_TEMPLATE,
+        ["transcript", "injected_context"],
+        "TICKET-0097 BRIEF-0097-F -- no subject, no knowledge_change (M1, N1)",
+    ),
+    (
+        "pt-player-generation",
+        seed_pilot.PLAYER_GENERATION_SYSTEM_PROMPT,
+        seed_pilot.PLAYER_GENERATION_USER_TEMPLATE,
+        ["brief"],
+        "TICKET-0097 BRIEF-0097-F -- a knowledge item has no subject (K1)",
+    ),
 )
 
 
diff --git a/scripts/seed_pilot.py b/scripts/seed_pilot.py
index c957e77..230d792 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -279,7 +279,7 @@ Output: a JSON array only. No prose. No markdown fences. Start with [, end with
 Nothing changed → output exactly: []
 
 Every element must have these EXACT 5 keys — no other keys allowed:
-  "mutation_type"  (string) — relation_change | new_knowledge | knowledge_change | event_creation | status_change | entity_creation | resource_change | goal_change | other
+  "mutation_type"  (string) — relation_change | new_knowledge | event_creation | status_change | entity_creation | resource_change | goal_change | other
   "target_table"   (string) — relation | knowledge | event | entity | character | location | faction | artifact | ledger | npc_goal | other
   "target_id"      (string or null) — id of the row to update; null for a new row
   "payload"        (object) — fields matching the target table (see below)
@@ -287,10 +287,9 @@ Every element must have these EXACT 5 keys — no other keys allowed:
 
 Payload shapes:
   relation_change  → {"entity_a_id":"…","entity_b_id":"…","relation_type":"…","intensity_delta":<signed int>}
-  new_knowledge    → {"entity_id":"…","subject":"…","level":"rumor|partial|knows|…","content":"…","source":"…","subject_entity_id":"…" (OPTIONAL — see rubric below)}
-  knowledge_change → {"entity_id":"…","subject":"…","field":"…","new_value":"…"}
+  new_knowledge    → {"entity_id":"…","level":"rumor|partial|knows|…","content":"…","source":"…","subject_entity_id":"…" (OPTIONAL — see rubric below)}
   event_creation   → {"title":"…","description":"…","type":"social|political|other","involved_entities":[…]}
-  resource_change  → {"entity_id":"char-player","amount":<signed int>,"counterparty_id":"…","reason":"…","knowledge":{"entity_id":"…","subject":"…","level":"…","content":"…","source":"…","is_secret":false} (knowledge is OPTIONAL — only when information changed hands)}
+  resource_change  → {"entity_id":"char-player","amount":<signed int>,"counterparty_id":"…","reason":"…","knowledge":{"entity_id":"…","level":"…","content":"…","source":"…","is_secret":false} (knowledge is OPTIONAL — only when information changed hands)}
   goal_change      → {"action":"complete|abandon|create_short","goal":"…"}
 
 === RELATION_CHANGE SIGN RUBRIC ===
@@ -379,7 +378,7 @@ Transcript :
 [JOUEUR] On dit que des voyageurs disparaissent sur la route ?
 [PNJ] On le dit, oui. Les patrouilles ont doublé depuis un mois. Personne ne sait pourquoi.
 Output:
-[{"mutation_type":"new_knowledge","target_table":"knowledge","target_id":null,"payload":{"entity_id":"char-player","subject":"disparitions_route","level":"rumor","content":"Le PNJ confirme des rumeurs de disparitions et un doublement des patrouilles depuis un mois.","source":"conversation avec le PNJ"},"rationale":"Le PNJ a directement confirmé la rumeur — le joueur dispose maintenant d'une corroboration externe."}]
+[{"mutation_type":"new_knowledge","target_table":"knowledge","target_id":null,"payload":{"entity_id":"char-player","level":"rumor","content":"Le PNJ confirme des rumeurs de disparitions et un doublement des patrouilles depuis un mois.","source":"conversation avec le PNJ"},"rationale":"Le PNJ a directement confirmé la rumeur — le joueur dispose maintenant d'une corroboration externe."}]
 
 === EXEMPLE 3 (fenêtre multi-tours, échange banal → rien à enregistrer) ===
 Transcript :
@@ -399,7 +398,7 @@ Transcript :
 [JOUEUR] Tiens.
 [PNJ] Plaisir de faire affaire.
 Output:
-[{"mutation_type":"resource_change","target_table":"ledger","target_id":null,"payload":{"entity_id":"char-player","amount":-15,"counterparty_id":"npc-b","reason":"achat d'une information sur le Conseil","knowledge":{"entity_id":"char-player","subject":"conseil_secret","level":"rumor","content":"Le Conseil cache l'un de ses propres membres.","source":"acheté au PNJ","is_secret":false}},"rationale":"Le joueur a payé 15 pièces, le PNJ a énoncé le prix et l'information, l'échange s'est conclu dans la scène."}]
+[{"mutation_type":"resource_change","target_table":"ledger","target_id":null,"payload":{"entity_id":"char-player","amount":-15,"counterparty_id":"npc-b","reason":"achat d'une information sur le Conseil","knowledge":{"entity_id":"char-player","level":"rumor","content":"Le Conseil cache l'un de ses propres membres.","source":"acheté au PNJ","is_secret":false}},"rationale":"Le joueur a payé 15 pièces, le PNJ a énoncé le prix et l'information, l'échange s'est conclu dans la scène."}]
 
 === EXEMPLE 5 (un objectif listé est accompli) ===
 NPC CONTEXT (extrait) :
@@ -1215,8 +1214,7 @@ joueur (chaîne).
 - "backstory" : son histoire personnelle, pour la référence du joueur \
 (chaîne).
 - "knowledge" : un tableau de ce que le personnage sait au départ. Chaque \
-élément est un objet { "subject": <chaîne>, "level": <niveau>, \
-"content": <chaîne> }. "level" appartient à cette échelle, du plus faible \
+élément est un objet { "level": <niveau>, "content": <chaîne> }. "level" appartient à cette échelle, du plus faible \
 au plus fort : "unaware", "rumor", "suspicious", "partial", "knows", \
 "fully_understands". Propose 0 à 5 savoirs, jamais davantage.
 
diff --git a/src/world_engine/cockpit/crud/_shared.py b/src/world_engine/cockpit/crud/_shared.py
index b02ae5a..0271576 100644
--- a/src/world_engine/cockpit/crud/_shared.py
+++ b/src/world_engine/cockpit/crud/_shared.py
@@ -219,7 +219,6 @@ KNOWLEDGE_LEVELS_ORDERED = (
 
 
 KNOWLEDGE_FIELDS: list[dict[str, Any]] = [
-    {"name": "subject", "label": "Subject", "kind": "text", "required": True},
     {
         "name": "level", "label": "Level", "kind": "select",
         "options": list(KNOWLEDGE_LEVELS_ORDERED), "default": "rumor", "required": True,
@@ -251,7 +250,6 @@ def _knowledge_dict(k: Knowledge, db: Optional[DbSession] = None) -> dict:
     return {
         "id": k.id,
         "entity_id": k.entity_id,
-        "subject": k.subject,
         "level": k.level,
         "content": knowledge_text(db, k),
         "source": k.source,
diff --git a/src/world_engine/cockpit/crud/knowledge.py b/src/world_engine/cockpit/crud/knowledge.py
index b9ebfb2..a4c1482 100644
--- a/src/world_engine/cockpit/crud/knowledge.py
+++ b/src/world_engine/cockpit/crud/knowledge.py
@@ -53,7 +53,7 @@ from ...models import (
 )
 from ...prompt_registry import PROMPT_REGISTRY, effective_model
 from ...prompt_store import current_prompt, get_version, list_versions
-from ...subject_resolve import unresolved_subjects
+from ...unbound_facts import unbound_facts
 from ...tick_normalize import _EVENT_TYPES
 from ...writes import (
     KNOWLEDGE_LEVELS,
@@ -96,7 +96,6 @@ from ._shared import (
 
 
 class KnowledgeWriteBody(BaseModel):
-    subject: Optional[str] = None
     level: Optional[str] = None
     content: Optional[str] = None
     source: Optional[str] = None
@@ -139,28 +138,14 @@ def list_entity_knowledge(entity_id: str, db: DbSession = Depends(get_session))
     return _list_knowledge(entity_id, db)
 
 
-@router.get("/worlds/{world_id}/unresolved-subjects")
-def list_unresolved_subjects(world_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
-    """Read-only residue worklist (TICKET-0087, BRIEF-0087-d, C-06): one row
-    per distinct `knowledge.subject` in `world_id` whose fact carries no
-    `fact_participant` at all. No write, no side effect, no model call."""
+@router.get("/worlds/{world_id}/unbound-facts")
+def list_unbound_facts(world_id: str, db: DbSession = Depends(get_session)) -> list[dict]:
+    """Read-only worklist (TICKET-0097, I1/J1, C-08): one row per free fact
+    of `world_id` that someone knows and no participant binds. No write, no
+    side effect, no model call."""
     if db.get(World, world_id) is None:
         raise HTTPException(404, f"World {world_id!r} not found")
-    rows = unresolved_subjects(world_id, db)
-    return [
-        {
-            "subject": row["subject"],
-            "fact_ids": list(row["fact_ids"]),
-            "row_count": row["row_count"],
-            "resolution": {
-                "verdict": row["resolution"].verdict,
-                "entity_id": row["resolution"].entity_id,
-                "candidate_ids": list(row["resolution"].candidate_ids),
-                "category": row["resolution"].category,
-            },
-        }
-        for row in rows
-    ]
+    return unbound_facts(world_id, db)
 
 
 def _create_knowledge_core(entity_id: str, body: KnowledgeWriteBody, db: DbSession) -> Knowledge:
@@ -168,11 +153,12 @@ def _create_knowledge_core(entity_id: str, body: KnowledgeWriteBody, db: DbSessi
 
     `body.fact_id`, when present, attaches to that existing fact (404 if it
     does not exist); when absent, `write_knowledge` auto-creates a
-    free-standing fact with `content = subject` (TICKET-0082, BRIEF-0082-b).
+    free-standing fact whose content is the row's text (TICKET-0097, K1/M1),
+    so a row without `fact_id` needs a content.
     """
     _get_entity(db, entity_id)
-    if not body.subject:
-        raise HTTPException(422, "subject is required")
+    if body.fact_id is None and not (body.content or "").strip():
+        raise HTTPException(422, "content is required")
     if body.level not in KNOWLEDGE_LEVELS:
         raise HTTPException(422, f"level must be one of {sorted(KNOWLEDGE_LEVELS)}")
     if body.fact_id is not None and db.get(Fact, body.fact_id) is None:
@@ -181,7 +167,6 @@ def _create_knowledge_core(entity_id: str, body: KnowledgeWriteBody, db: DbSessi
     return write_knowledge(
         db,
         entity_id=entity_id,
-        subject=body.subject,
         level=body.level,
         content=body.content,
         source=body.source,
@@ -208,13 +193,10 @@ def update_knowledge(knowledge_id: str, body: KnowledgeWriteBody, db: DbSession
         raise HTTPException(404, f"Knowledge {knowledge_id!r} not found")
     if body.level is not None and body.level not in KNOWLEDGE_LEVELS:
         raise HTTPException(422, f"level must be one of {sorted(KNOWLEDGE_LEVELS)}")
-    if not body.subject:
-        raise HTTPException(422, "subject is required")
 
     k = write_knowledge(
         db,
         knowledge_id=knowledge_id,
-        subject=body.subject,
         level=body.level or existing.level,
         content=body.content,
         source=body.source,
diff --git a/src/world_engine/cockpit/routes/creator.py b/src/world_engine/cockpit/routes/creator.py
index 1356cf3..b369adc 100644
--- a/src/world_engine/cockpit/routes/creator.py
+++ b/src/world_engine/cockpit/routes/creator.py
@@ -569,7 +569,7 @@ def get_bootstrap(db: Session = Depends(get_session)) -> dict:
 # ── Create-PC path (BRIEF-46) ──────────────────────────────────────────────────
 
 class PlayerKnowledgeItem(BaseModel):
-    subject: str
+    # TICKET-0097 (K1): no subject — the row's content is its fact's text.
     level: str
     content: str
 
@@ -626,7 +626,6 @@ def _write_pc_knowledge(entity_id: str, knowledge_items: Optional[list], db: Ses
         write_knowledge(
             db,
             entity_id=entity_id,
-            subject=item.subject,
             level=level,
             content=item.content,
             source="pc_creation",
diff --git a/src/world_engine/cockpit/routes/npc_agent.py b/src/world_engine/cockpit/routes/npc_agent.py
index 19ad5ed..a47095e 100644
--- a/src/world_engine/cockpit/routes/npc_agent.py
+++ b/src/world_engine/cockpit/routes/npc_agent.py
@@ -221,7 +221,6 @@ def _commit_npc_row(row: NpcBatchRow, batch: NpcBatch, db: Session) -> dict:
 
     for k in (sec.get("knowledge") or []):
         k_body = _crud.KnowledgeWriteBody(
-            subject=k.get("subject"),
             level=k.get("level"),
             content=k.get("content"),
             source=None,
diff --git a/src/world_engine/entity_author.py b/src/world_engine/entity_author.py
index 6089b54..c8d9700 100644
--- a/src/world_engine/entity_author.py
+++ b/src/world_engine/entity_author.py
@@ -52,7 +52,7 @@ _TYPE_FIELDS: dict[str, str] = {
         'public.physical_tier (entier -1..2 : -1 chétif, 0 ordinaire, '
         '1 capable, 2 redoutable) ; public.faction_name (string ou null — '
         "nom exact d'une faction existante, ou null si aucune).\n"
-        'secret.knowledge (tableau d\'objets {"subject","level","content"} — '
+        'secret.knowledge (tableau d\'objets {"level","content"} — '
         'level est un de rumor|suspicious|partial|knows|fully_understands) ; '
         'secret.creator_meta (string ou null — note du créateur sur la '
         "vraie nature ou l'arc prévu du personnage) ; "
@@ -202,7 +202,8 @@ def _normalize_knowledge(raw: Any, notes: list[str]) -> list[dict]:
     """Validate each secret.knowledge row; drop malformed rows, note each drop.
 
     `is_secret` is forced TRUE here in code — the model never sets it
-    (concealment is structural, never instructional).
+    (concealment is structural, never instructional). A row carries no
+    subject (TICKET-0097, M1): its content becomes its fact's text.
     """
     rows: list[dict] = []
     if not isinstance(raw, list):
@@ -210,11 +211,10 @@ def _normalize_knowledge(raw: Any, notes: list[str]) -> list[dict]:
     for item in raw:
         if not isinstance(item, dict):
             continue
-        subject = item.get("subject")
         content = item.get("content")
-        if not subject or not content:
+        if not isinstance(content, str) or not content.strip():
             notes.append(
-                "Une ligne de savoir secret sans sujet ou contenu a été ignorée"
+                "Une ligne de savoir secret sans contenu a été ignorée"
             )
             continue
         level = item.get("level")
@@ -222,7 +222,6 @@ def _normalize_knowledge(raw: Any, notes: list[str]) -> list[dict]:
             level = "rumor"
         rows.append(
             {
-                "subject": subject,
                 "level": level,
                 "content": content,
                 "is_secret": True,
@@ -244,16 +243,13 @@ def _normalize_player_knowledge(raw: Any) -> list[dict]:
     for item in raw:
         if not isinstance(item, dict):
             continue
-        subject = item.get("subject")
         content = item.get("content")
-        if not isinstance(subject, str) or not subject.strip():
-            continue
         if not isinstance(content, str) or not content.strip():
             continue
         level = item.get("level")
         if level not in KNOWLEDGE_LEVELS:
             level = "rumor"
-        rows.append({"subject": subject, "level": level, "content": content})
+        rows.append({"level": level, "content": content})
         if len(rows) >= 5:
             break
     return rows
diff --git a/src/world_engine/subject_resolve.py b/src/world_engine/subject_resolve.py
deleted file mode 100644
index a20942d..0000000
--- a/src/world_engine/subject_resolve.py
+++ /dev/null
@@ -1,113 +0,0 @@
-"""Free-text `knowledge.subject` reconciled against entity names (TICKET-0087,
-BRIEF-0087-a).
-
-This module is the single place a free-text `knowledge.subject` is
-reconciled against entity names; it reuses `lore_resolve`'s rungs and never
-re-implements one; it never calls a model; it never picks between
-candidates.
-"""
-
-from __future__ import annotations
-
-from dataclasses import dataclass
-from typing import Optional
-
-from sqlmodel import Session, select
-
-from .lore_resolve import resolve_named
-from .models import Entity, FactParticipant, Knowledge
-from .name_index import NAMES_ONLY
-
-# Frozen here (N10a): a knowledge subject resolves on names only, among these
-# three categories, whatever the Lore resolver's categories become.
-_SUBJECT_CATEGORIES: tuple[str, ...] = ("faction", "person", "place")
-
-
-@dataclass(frozen=True)
-class SubjectResolution:
-    verdict: str
-    entity_id: Optional[str]
-    candidate_ids: tuple[str, ...]
-    category: Optional[str]
-
-
-def resolve_subject(subject: str, world_id: str, db: Session) -> SubjectResolution:
-    """Walk `_SUBJECT_CATEGORIES` in order, calling
-    `resolve_named(subject, category, world_id, db, scope=NAMES_ONLY)` for
-    each: entity names only, never an appellation (N10a).
-
-    Exactly one distinct `entity_id` across all `matched` categories, and no
-    category `ambiguous` -> `matched`. Two or more distinct matched ids, or
-    any category `ambiguous` -> `ambiguous`, `candidate_ids` the sorted union
-    of every candidate seen. No category matched -> `unmatched`. An empty or
-    whitespace-only `subject` -> `unmatched`, with no rung call made.
-    """
-    if not subject or not subject.strip():
-        return SubjectResolution(verdict="unmatched", entity_id=None, candidate_ids=(), category=None)
-
-    matched_ids: set[str] = set()
-    matched_category: Optional[str] = None
-    any_ambiguous = False
-    seen_candidates: set[str] = set()
-
-    for category in _SUBJECT_CATEGORIES:
-        result = resolve_named(subject, category, world_id, db, scope=NAMES_ONLY)
-        if result.verdict == "ambiguous":
-            any_ambiguous = True
-            seen_candidates.update(result.candidate_ids)
-        elif result.verdict == "matched":
-            matched_ids.add(result.entity_id)
-            matched_category = category
-            seen_candidates.update(result.candidate_ids)
-
-    if any_ambiguous or len(matched_ids) > 1:
-        return SubjectResolution(
-            verdict="ambiguous", entity_id=None,
-            candidate_ids=tuple(sorted(seen_candidates)), category=None,
-        )
-    if len(matched_ids) == 1:
-        entity_id = next(iter(matched_ids))
-        return SubjectResolution(
-            verdict="matched", entity_id=entity_id,
-            candidate_ids=(entity_id,), category=matched_category,
-        )
-    return SubjectResolution(verdict="unmatched", entity_id=None, candidate_ids=(), category=None)
-
-
-def unresolved_subjects(world_id: str, db: Session) -> list[dict]:
-    """One row per distinct `knowledge.subject` in `world_id` whose fact
-    carries no `fact_participant` at all (TICKET-0087, BRIEF-0087-c, C-06).
-
-    `resolve_subject` runs once per distinct subject, never once per row.
-    World scoping and the "no participant at all" filter are both applied
-    in the single `select(...).where(...)` below — an outer join to
-    `fact_participant` so a row with a match (participant_id IS NOT NULL)
-    is excluded in Python, never fetched via a second, unscoped `select(`.
-    Ordered by `row_count` descending, then `subject` ascending.
-    """
-    rows = db.exec(
-        select(Knowledge.subject, Knowledge.fact_id, FactParticipant.id)
-        .join(Entity, Entity.id == Knowledge.entity_id)
-        .outerjoin(FactParticipant, FactParticipant.fact_id == Knowledge.fact_id)
-        .where(Entity.world_id == world_id)
-    ).all()
-
-    grouped: dict[str, dict] = {}
-    for subject, fact_id, participant_id in rows:
-        if participant_id is not None:
-            continue
-        group = grouped.setdefault(subject, {"fact_ids": set(), "row_count": 0})
-        group["fact_ids"].add(fact_id)
-        group["row_count"] += 1
-
-    result = [
-        {
-            "subject": subject,
-            "fact_ids": tuple(sorted(group["fact_ids"])),
-            "row_count": group["row_count"],
-            "resolution": resolve_subject(subject, world_id, db),
-        }
-        for subject, group in grouped.items()
-    ]
-    result.sort(key=lambda entry: (-entry["row_count"], entry["subject"]))
-    return result
diff --git a/src/world_engine/unbound_facts.py b/src/world_engine/unbound_facts.py
new file mode 100644
index 0000000..afca6e9
--- /dev/null
+++ b/src/world_engine/unbound_facts.py
@@ -0,0 +1,73 @@
+"""Facts nobody is attached to (TICKET-0097, decisions I1 and J1) — the read
+behind Creation's « Sujets » panel.
+
+One row per free fact (no `relation_id` / `event_id` / `world_law_id`: a
+typed fact takes no participant) that a `knowledge` row of the world knows
+and that carries no `fact_participant` at all. Each row shows the fact's
+text, the version of its first knower by name (J1), how many entities know
+it, and the Lore resolver's reading of the fact's text
+(`lore_mentions_read.lookup_surface`: names and appellations of every
+category, the partial rung, near names) — the creator binds, the resolver
+never picks. Read-only: no `db.add`, no commit, no model call.
+
+Replaces `subject_resolve.py` (N10a fired with Q1b): there is no subject
+left to resolve, and one name resolver serves the whole tool.
+"""
+
+from __future__ import annotations
+
+from sqlmodel import Session, select
+
+from .lore_mentions_read import lookup_surface
+from .models import Entity, Fact, FactParticipant, Knowledge
+from .prose_render import fact_texts, knowledge_texts
+
+EXCERPT_CHARS = 120
+
+
+def _clip(text: str) -> str:
+    return text if len(text) <= EXCERPT_CHARS else text[:EXCERPT_CHARS].rstrip() + "…"
+
+
+def _unbound_rows(world_id: str, db: Session) -> dict[str, list[tuple[Knowledge, Entity]]]:
+    """fact id -> its (knowledge row, knower) pairs, for every free fact of
+    `world_id` known by someone and bound to no participant."""
+    rows = db.exec(
+        select(Knowledge, Entity, FactParticipant.id)
+        .join(Entity, Entity.id == Knowledge.entity_id)
+        .join(Fact, Fact.id == Knowledge.fact_id)
+        .outerjoin(FactParticipant, FactParticipant.fact_id == Knowledge.fact_id)
+        .where(
+            Entity.world_id == world_id,
+            Fact.relation_id.is_(None), Fact.event_id.is_(None), Fact.world_law_id.is_(None),
+        )
+    ).all()
+    grouped: dict[str, list[tuple[Knowledge, Entity]]] = {}
+    for knowledge, knower, participant_id in rows:
+        if participant_id is None:
+            grouped.setdefault(knowledge.fact_id, []).append((knowledge, knower))
+    return grouped
+
+
+def unbound_facts(world_id: str, db: Session) -> list[dict]:
+    """C-08. Ordered by knower count descending, then fact text."""
+    grouped = _unbound_rows(world_id, db)
+    facts = [db.get(Fact, fact_id) for fact_id in grouped]
+    result = []
+    for fact, text in zip(facts, fact_texts(db, facts)):
+        knowers = sorted(grouped[fact.id], key=lambda pair: (pair[1].name.casefold(), pair[1].id))
+        first_row, first_knower = knowers[0]
+        first_text = knowledge_texts(db, [first_row])[0]
+        lookup = lookup_surface(db, world_id, text)
+        result.append({
+            "fact_id": fact.id,
+            "fact": text,
+            "knower_count": len(knowers),
+            "excerpt": (
+                {"entity_name": first_knower.name, "text": _clip(first_text)} if first_text else None
+            ),
+            "candidates": lookup["candidates"],
+            "near": lookup["near"],
+        })
+    result.sort(key=lambda row: (-row["knower_count"], row["fact"].casefold(), row["fact_id"]))
+    return result
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 76643ec..c4f149c 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17172,6 +17172,33 @@ the fact.
 holds a row on the fact of every hidden detail in it; a detail no approved
 discovery has linked to a fact is, by construction, not known yet.
 
+## THE CREATOR SURFACE WRITES FACTS (TICKET-0097) -- NO SUBJECT FIELD, AND THE WORKLIST LISTS FACTS (BRIEF-0097-f, no schema change)
+
+**K1 -- the Subject field is gone.** The sheet's knowledge editor, the
+pending-knowledge editor of a new NPC, the PC creation draft and the NPC
+group agent's commit no longer send a `subject`. A new row is its content;
+its fact is born with that sentence (M1). An existing row shows its fact's
+text read-only. Attaching a character to an existing fact is the lore
+writing path's job, the next ticket.
+
+**Generators stop asking for one.** `secret.knowledge` (entity generation)
+and `knowledge` (PC generation) are `{level, content}`; the conversation
+analysis prompt loses `subject` from every knowledge shape and example, and
+loses `knowledge_change` from its type list (N1).
+
+**I1 -- one resolver.** `subject_resolve.py` is deleted (N10a's condition,
+"the Q1b ticket opens", fired). `unbound_facts.py` lists the free facts
+someone knows and no participant binds, and reads each fact's text through
+`lore_mentions_read.lookup_surface` -- the names panel's resolver: names
+and appellations, every category, the partial rung, near names. It never
+picks: a suggestion is preselected only for a single candidate.
+`GET /api/worlds/{id}/unbound-facts` replaces `/unresolved-subjects`.
+
+**J1 -- a card is a fact.** The « Sujets » tab keeps its name and place; a
+card shows the fact's text, its first knower's version (by name), how many
+know it, then the candidates or near names. Binding is one participant
+POST, since a card is one fact.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/knowledge_identity.py b/tooling/verify/checks/knowledge_identity.py
index ed7b31c..8d6f430 100644
--- a/tooling/verify/checks/knowledge_identity.py
+++ b/tooling/verify/checks/knowledge_identity.py
@@ -70,6 +70,13 @@ K7 -- aboutness is the fact's participants (G1, H1):
       fact's `about_entity_ids`;
    d. a signpost cluster is silent once the player knows the fact of every
       hidden detail in it, and speaks while one detail has no fact yet.
+K8 -- the creator surface (K1, I1, J1, C-08):
+   a. `unbound_facts` lists a known free fact without participant with its
+      text, first knower's version, knower count and the resolver's single
+      candidate for a name; a bound fact and a typed fact are not listed;
+   b. the creator CRUD creates a row without `subject` (the fact carries
+      the content) and refuses a create with neither content nor fact_id;
+      the knowledge dict carries no `subject` key.
 
 Fresh temp-file SQLite databases (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB.
@@ -93,15 +100,9 @@ FAILURES: list[str] = []
 
 _SUBJECT_CENSUS: dict[str, int] = {
     "src/world_engine/analyzer_transcript.py": 3,
-    "src/world_engine/cockpit/crud/_shared.py": 3,
-    "src/world_engine/cockpit/crud/knowledge.py": 8,
     "src/world_engine/cockpit/crud/locations.py": 7,
     "src/world_engine/cockpit/play_discovery.py": 3,
-    "src/world_engine/cockpit/routes/creator.py": 2,
-    "src/world_engine/cockpit/routes/npc_agent.py": 2,
-    "src/world_engine/entity_author.py": 4,
     "src/world_engine/models/canon_knowledge.py": 1,
-    "src/world_engine/subject_resolve.py": 4,
     "src/world_engine/writes/knowledge.py": 8,
 }
 
@@ -707,6 +708,48 @@ def rule_k7(engine) -> None:
         session.rollback()
 
 
+def _k8(session, ids) -> None:
+    from fastapi import HTTPException
+
+    from world_engine.cockpit.crud._shared import _knowledge_dict
+    from world_engine.cockpit.crud.knowledge import KnowledgeWriteBody, _create_knowledge_core
+    from world_engine.unbound_facts import unbound_facts
+    from world_engine.writes import attach_participants, write_knowledge
+    from world_engine.models import Fact
+
+    named = write_knowledge(session, entity_id=ids["ana"], content="Bel", level="knows")
+    write_knowledge(session, entity_id=ids["bel"], fact_id=named.fact_id, content="Elle", level="rumor")
+    bound = write_knowledge(session, entity_id=ids["ana"], content="Lié.", level="knows")
+    attach_participants(session, fact=session.get(Fact, bound.fact_id), entity_ids=[ids["bel"]])
+    session.flush()
+    rows = unbound_facts(ids["w"], session)
+    listed = {r["fact_id"]: r for r in rows}
+    row = listed.get(named.fact_id)
+    if row is None or bound.fact_id in listed:
+        fail(f"K8a unbound facts are {sorted(listed)!r}")
+    elif (row["fact"], row["knower_count"], row["excerpt"], [c["id"] for c in row["candidates"]]) != (
+            "Bel", 2, {"entity_name": "Ana", "text": "Bel"}, [ids["bel"]]):
+        fail(f"K8a row is {row!r}")
+    made = _create_knowledge_core(ids["bel"], KnowledgeWriteBody(level="knows", content="Il neige."), session)
+    session.flush()
+    if session.get(Fact, made.fact_id).content_raw != "Il neige." or "subject" in _knowledge_dict(made, session):
+        fail("K8b the CRUD create does not give the fact the row's content, or the dict has a subject")
+    try:
+        _create_knowledge_core(ids["bel"], KnowledgeWriteBody(level="knows"), session)
+        fail("K8b a create with neither content nor fact_id was accepted")
+    except HTTPException as exc:
+        if exc.status_code != 422:
+            fail(f"K8b refusal status is {exc.status_code}")
+
+
+def rule_k8(engine) -> None:
+    from sqlmodel import Session
+
+    with Session(engine) as session:
+        _k8(session, _k4_world(session))
+        session.rollback()
+
+
 def rule_k4(engine) -> None:
     from sqlmodel import Session
 
@@ -759,6 +802,7 @@ def main() -> int:
     rule_k5(engine)
     rule_k6(engine)
     rule_k7(engine)
+    rule_k8(engine)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
diff --git a/tooling/verify/checks/name_resolution.py b/tooling/verify/checks/name_resolution.py
index 4e973e5..e68e183 100644
--- a/tooling/verify/checks/name_resolution.py
+++ b/tooling/verify/checks/name_resolution.py
@@ -15,8 +15,9 @@ G2 (fixture) -- the LOT's "Near" table through `near_candidates`: "Maelys"
 G3 (fixture) -- the day chain sees the perceiver regime: a PC who knows the
    appellation "la reine" of an NPC resolves it via `named_exact`; a PC who
    does not leaves it unmatched.
-G4 (fixture) -- `resolve_subject("la reine", ...)` stays unmatched with that
-   appellation present (names only, N10a).
+G4 (fixture) -- the unbound-facts worklist resolver (`lookup_surface`,
+   TICKET-0097, I1 -- N10a's frozen names-only subject resolver is gone)
+   reads "la reine" as that appellation's owner.
 G5 (fixture) -- a tokenizer generator mention "Varn" next to "Maelis Varn"
    stays unresolved: no partial rung outside `creator`.
 G6 (static) -- the LOT's "Categories after C" table through
@@ -188,7 +189,7 @@ def check_g3_g4(engine) -> None:
     from world_engine.day_concordance import concord
     from world_engine.day_extract import Mention
     from world_engine.models import Character, Location
-    from world_engine.subject_resolve import resolve_subject
+    from world_engine.lore_mentions_read import lookup_surface
     from world_engine.writes.facets import ScopeChoice
     from world_engine.writes.knowledge import write_knowledge
 
@@ -207,7 +208,7 @@ def check_g3_g4(engine) -> None:
         pc_p, npc_y = character("Pell", "player"), character("Ysolde", "npc")
         pc_q = character("Quill", "player")
         fact = _appellation(session, npc_y, "la reine", ScopeChoice("none"))
-        write_knowledge(session, entity_id=pc_p.id, fact_id=fact.id, subject="la reine",
+        write_knowledge(session, entity_id=pc_p.id, fact_id=fact.id,
                         level="knows", is_secret=False, changed_by="check")
         session.flush()
         mention = Mention(category="person", surface_form="la reine", kind="named")
@@ -218,9 +219,9 @@ def check_g3_g4(engine) -> None:
         got = concord([mention], pc_q, session)
         if got.matched or got.cast or got.ambiguous or len(got.unmatched) != 1:
             fail(f"G3 unknowing PC: 'la reine' not unmatched: {got!r}")
-        subject = resolve_subject("la reine", world.id, session)
-        if subject.verdict != "unmatched":
-            fail(f"G4: resolve_subject('la reine') is {subject.verdict!r}, not 'unmatched'")
+        found = [c["id"] for c in lookup_surface(session, world.id, "la reine")["candidates"]]
+        if found != [npc_y.id]:
+            fail(f"G4: the worklist resolver reads 'la reine' as {found!r}, not [{npc_y.id!r}] (I1)")
         session.rollback()
 
 
@@ -484,8 +485,8 @@ def main() -> int:
         return 1
     print("PASS: name_resolution — exact names resolve, appellations and partial names resolve "
           "for the creator only, near names score and order as the lot's table, the day chain "
-          "sees only the appellations its character knows, subjects and tokenizer mentions "
-          "stay on names, objects and every other type are nameable categories, near names reach "
+          "sees only the appellations its character knows, the worklist reads appellations, "
+          "tokenizer mentions stay on names, objects and every other type are nameable categories, near names reach "
           "the Lore answer and the names panel, and the panel records a missed name as an "
           "appellation")
     return 0
diff --git a/tooling/verify/checks/subject_resolution.py b/tooling/verify/checks/subject_resolution.py
index 83b3b69..1660ccd 100644
--- a/tooling/verify/checks/subject_resolution.py
+++ b/tooling/verify/checks/subject_resolution.py
@@ -11,20 +11,18 @@ this check never touches Nia's real DB. `FAILURES` list, print FAIL lines,
 `sys.exit(1)`; every assertion below always collects at least one concrete
 item before judging it — never a silent, vacuous pass.
 
-Four assertions:
-  A1 (AST, purity): `subject_resolve.py` contains no `chat(` call and no
+Four assertions (A1/A2 retargeted at TICKET-0097, BRIEF-0097-f: the
+subject resolver is gone, I1; the worklist that replaced it is held to the
+same purity):
+  A1 (AST, purity): `unbound_facts.py` contains no `chat(` call and no
      `db.add(`.
-  A2 (AST, no re-implemented rung): `subject_resolve.py` reaches canon
-     ONLY through `lore_resolve.resolve_named` — every `select(` found
-     directly in the module (there should be none; C-01/BRIEF-0087-a's
-     contract is that it delegates every candidate lookup rather than
-     querying itself) must be world-constrained among its `.where(`
-     arguments, in the shape `lore_isolation.py`'s R2 already uses for
-     `lore_selectors.py`. When — as the current, correct state — zero
-     `select(` calls exist, the module must instead show at least one call
-     to `resolve_named(` and zero `db.exec(`/`text(` calls, so the
-     assertion always has something concrete to point at rather than
-     trusting an empty scan.
+  A2 (AST, no re-implemented rung): every `select(` in `unbound_facts.py`
+     is world-constrained among its `.where(` arguments, in the shape
+     `lore_isolation.py`'s R2 uses for `lore_selectors.py`; and names are
+     reached ONLY through `lore_mentions_read.lookup_surface` — at least one
+     `lookup_surface(` call, zero `resolve_named(` / `near_candidates(` /
+     `surfaces(` calls and zero `text(` calls, so the assertion always has
+     something concrete to point at.
   A3 (behavioural, refusal): a `subject_entity_id` naming an active entity
      of a DIFFERENT world is refused at apply — a non-`None` error string,
      zero `fact_participant` rows written. Healed with an in-world id:
@@ -45,7 +43,7 @@ import tempfile
 
 ROOT = pathlib.Path(__file__).resolve().parents[3]
 SRC = ROOT / "src"
-SUBJECT_RESOLVE_FILE = SRC / "world_engine" / "subject_resolve.py"
+UNBOUND_FACTS_FILE = SRC / "world_engine" / "unbound_facts.py"
 
 FAILURES: list[str] = []
 
@@ -85,7 +83,7 @@ def _fresh_engine():
 
 
 def check_a1_purity() -> None:
-    tree = _parse(SUBJECT_RESOLVE_FILE)
+    tree = _parse(UNBOUND_FACTS_FILE)
     if tree is None:
         return
     hits: set[str] = set()
@@ -102,80 +100,47 @@ def check_a1_purity() -> None:
             hits.add("chat(")
     if hits:
         fail(
-            f"subject_resolution A1: {_rel(SUBJECT_RESOLVE_FILE)} contains "
+            f"subject_resolution A1: {_rel(UNBOUND_FACTS_FILE)} contains "
             f"forbidden call(s) {sorted(hits)!r} — must stay pure and read-only"
         )
 
 
+def _where_of(tree: ast.AST, node: ast.Call) -> "ast.Call | None":
+    for parent in ast.walk(tree):
+        if (isinstance(parent, ast.Call) and isinstance(parent.func, ast.Attribute)
+                and parent.func.attr == "where"
+                and any(sub is node for sub in ast.walk(parent.func.value))):
+            return parent
+    return None
+
+
 def check_a2_no_reimplemented_rung() -> None:
-    tree = _parse(SUBJECT_RESOLVE_FILE)
+    tree = _parse(UNBOUND_FACTS_FILE)
     if tree is None:
         return
-    select_calls = [
-        node for node in ast.walk(tree)
-        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "select"
-    ]
-
-    if select_calls:
-        for node in select_calls:
-            where_call = None
-            for parent in ast.walk(tree):
-                if not isinstance(parent, ast.Call):
-                    continue
-                if not (isinstance(parent.func, ast.Attribute) and parent.func.attr == "where"):
-                    continue
-                if any(sub is node for sub in ast.walk(parent.func.value)):
-                    where_call = parent
-                    break
-            if where_call is None:
-                fail(
-                    f"subject_resolution A2: {_rel(SUBJECT_RESOLVE_FILE)}:{node.lineno} "
-                    "— select( with no .where( call"
-                )
-                continue
-            names_in_where = {
-                sub.id if isinstance(sub, ast.Name) else sub.attr
-                for sub in ast.walk(where_call)
-                if isinstance(sub, (ast.Name, ast.Attribute))
-            }
-            if "world_id" not in names_in_where and "Entity" not in names_in_where:
-                fail(
-                    f"subject_resolution A2: {_rel(SUBJECT_RESOLVE_FILE)}:{node.lineno} — "
-                    "select(...).where(...) references neither world_id nor a join to "
-                    "Entity — not world-scoped at construction"
-                )
-        return
-
-    # The correct, current state: subject_resolve.py re-implements no rung of
-    # its own — it never calls select( directly at all. Assert THAT
-    # concretely (at least one resolve_named( call, zero raw db.exec(/text(
-    # bypasses) rather than treating an empty select( scan as a silent pass.
-    resolve_named_calls = [
-        node for node in ast.walk(tree)
-        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "resolve_named"
-    ]
-    if not resolve_named_calls:
-        fail(
-            f"subject_resolution A2: {_rel(SUBJECT_RESOLVE_FILE)} contains zero select( "
-            "and zero resolve_named( calls — vacuous, the resolver reaches canon through neither path"
-        )
-    bypass_hits: set[str] = set()
-    for node in ast.walk(tree):
-        if not isinstance(node, ast.Call):
+    rel = _rel(UNBOUND_FACTS_FILE)
+    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
+    names = [node.func.id for node in calls if isinstance(node.func, ast.Name)]
+    for node in calls:
+        if not (isinstance(node.func, ast.Name) and node.func.id == "select"):
             continue
-        func = node.func
-        if (
-            isinstance(func, ast.Attribute) and func.attr == "exec"
-            and isinstance(func.value, ast.Name) and func.value.id == "db"
-        ):
-            bypass_hits.add("db.exec(")
-        elif isinstance(func, ast.Name) and func.id == "text":
-            bypass_hits.add("text(")
-    if bypass_hits:
-        fail(
-            f"subject_resolution A2: {_rel(SUBJECT_RESOLVE_FILE)} reaches canon through "
-            f"{sorted(bypass_hits)!r} instead of lore_resolve.resolve_named — a re-implemented rung"
-        )
+        where_call = _where_of(tree, node)
+        if where_call is None:
+            fail(f"subject_resolution A2: {rel}:{node.lineno} — select( with no .where( call")
+            continue
+        names_in_where = {
+            sub.id if isinstance(sub, ast.Name) else sub.attr
+            for sub in ast.walk(where_call) if isinstance(sub, (ast.Name, ast.Attribute))
+        }
+        if "world_id" not in names_in_where:
+            fail(f"subject_resolution A2: {rel}:{node.lineno} — select(...).where(...) is not "
+                 "world-scoped at construction")
+    if "lookup_surface" not in names:
+        fail(f"subject_resolution A2: {rel} never calls lookup_surface( — vacuous, names are "
+             "reached through no resolver")
+    direct = sorted({n for n in names if n in ("resolve_named", "near_candidates", "surfaces", "text")})
+    if direct:
+        fail(f"subject_resolution A2: {rel} calls {direct!r} directly — a re-implemented rung")
 
 
 def check_behavioural(engine) -> None:
@@ -280,7 +245,7 @@ def main() -> int:
             print(f"FAIL: {msg}")
         return 1
     print(
-        "PASS: subject_resolution — subject_resolve.py stays pure and "
+        "PASS: subject_resolution — unbound_facts.py stays pure and "
         "re-implements no rung; _mutation_apply_new_knowledge refuses a "
         "cross-world subject_entity_id and writes nothing, applies an "
         "in-world one idempotently"
```

## Scope OUT

- Attaching an entity to an existing fact from the editors (K2, rejected; the writing path).
- Renaming the tab (J3, rejected).
- A short fact title (C3, rejected).
- `seed_test.py`, `test_context.py`, `apply_ticket_0087_subject_participants.py` (R-15).
- Every later brief of the lot: BRIEF-0097-G.

## Invariants to defend

**Creator-direct create helpers never commit in their core** — `_create_knowledge_core` still adds only. **PC knowledge is written `is_secret=False`**; **`_normalize_knowledge` is NPC-only and forces `is_secret=True`** — both kept. Every Création surface mounts through `CREATION_ISLANDS` — the island keeps its key, origin and container. **UI-visible data never lives in JSON** — the worklist is computed.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold (line numbers may drift by a few lines; the quoted text must match).
- `git apply --check` of the embedded diff fails on a file this brief names.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `claude_md_contract.py` fails on the File-structure budget after the diff.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `knowledge_identity.py` K3 fails only on counts, with every reported file named in this brief's diff: re-run the census (see Done means) and report the table.
- `frontend_build_fresh.py` fails only on `.build-manifest.json` timestamps: rebuild once and commit what the build writes.

REPORT-ONLY:
- Any other file still naming `subject` in a comment or docstring.
- Timing of the corpus run.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat` of the commit lists exactly the files of the embedded diff, plus `src/world_engine/cockpit/static/` (rebuilt), plus `tooling/standards/DECISIONS_INDEX.md` (regenerated).
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/knowledge_identity.py` → `PASS`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/subject_resolution.py` → `PASS`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/claude_md_contract.py` → `PASS`.
- `git grep -n subject_resolve -- src` → no output.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → `PASS: corpus_gate — 126 check(s) discovered, 126 executed, 126 passed`.
- `/review-step` then `/close-step` ran on the commit.

Census re-run (for the K3 ADAPT above): the census function is `census()` in
`knowledge_identity.py`; print it with
`WORLD_ENGINE_ENV=test python -c "import sys; sys.path.insert(0,'tooling/verify/checks'); import knowledge_identity as k; print(k.census())"`.

## Docs to update

Decision entry `THE CREATOR SURFACE WRITES FACTS … (BRIEF-0097-f, no schema change)`; CLAUDE.md (in the diff).
