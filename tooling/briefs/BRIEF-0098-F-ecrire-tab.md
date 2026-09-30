<!-- slug: ecrire-tab -->
# BRIEF 0098-F — "The Écrire tab: write, clarify, correct, commit"

Lot: LOT-0098-lore-writing.md (authoritative on conflict)
Depends on: BRIEF-0098-E (C-06)
Commit header for decisions: `(BRIEF-0098-f, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0098`, on the tree the previous brief left, before applying anything. Halt if one has moved.

- `frontend/src/lore/Lore.svelte:15` → the `TICKET-0095 (K1): …` comment line closing the header comment; `:18` → `  import ChoiceReviewPanel from './ChoiceReviewPanel.svelte';`; `:96` → the `Noms à lier` tab button, then `  </div>`
- `src/world_engine/cockpit/routes/lore_write.py:60`, `:72`, `:93` → the three POST routes of C-06; `GET /api/lore/write/entries` below them
- `frontend/src/creation/sheetRequest.svelte.js:30` → `export async function api(path, options) {`
- `tooling/verify/checks/lore_write.py:101` → `    "lore_write_read.py", "cockpit/routes/lore_write.py",`
- `frontend/src/lore/WritePanel.svelte`, `frontend/src/lore/writePanel.svelte.js` → do not exist

## Facts carried

### R-17 — the Lore shell [M]
Opened: `frontend/src/lore/Lore.svelte` (whole, 218 lines; tabs at 94-101);
`frontend/src/lore/namesPanel.svelte.js:1-60`;
`frontend/src/creation/sheetRequest.svelte.js:30-35` (`api`);
`src/world_engine/cockpit/crud/entities.py:474-483` (`GET /api/entities`);
`src/world_engine/lore_mentions_read.py:30-33` (`active_world_id`).
Finding: two tabs (`question`, `names`); panels keep state in a
`*.svelte.js` module; `api()` throws `Error(detail)`; `/api/entities` lists
the active world's entities with `type`, `name`, `status`.
Consequence: F adds a third tab and a state module in the same shape.

## Contracts

### C-05 — the draft
Produced by: D   Consumed by: E, F
- `lore_write_draft`: `QUESTIONS_USAGE = "lore_statement_questions"`,
  `PROPOSAL_USAGE = "lore_statement_to_proposal"`, `MAX_QUESTIONS = 3`,
  `MAX_CODED_FACTS = 200`, `WRITE_UNAVAILABLE_MESSAGE` (French),
  `CATEGORY_TYPE`.
- `draft_context(db, world_id, statement) -> DraftContext(entity_lines,
  coded)`; `draft_questions(db, world_id, statement) -> list[str]`;
  `draft_proposal(db, world_id, statement, answers="") -> dict` with keys
  `statement, answers, entities, facts, memberships, controls, notes,
  facets`. Each entity carries `status`: `matched` (`action: existing`,
  `entity_id`, `name`, `type`), `ambiguous` (`action: null`, `candidates`
  [{entity_id,name,type}]) or `new` (`action: create`, `type` from the
  category or null, `near` [{entity_id,name,type,score}]). Facts follow
  C-02 with `fact_id` resolved from the model's `code`. `facets` =
  [{name, label}] of the non-typed `FACETS`. `OllamaError` and
  `LlmParseError` propagate.
- Prompt variables: questions `statement, entities, facts`; proposal
  `facets, entities, facts, statement, answers`.

### C-06 — the writing routes (family)
Produced by: E   Consumed by: F
- `POST /api/lore/write/questions` `{statement}` -> `{"questions": [...]}`.
- `POST /api/lore/write/draft` `{statement, answers?}` -> C-05's draft.
- `POST /api/lore/write/commit` `{proposal}` -> `{"ok": true, "entry_id",
  "written", "skipped"}`; 422 `{detail}` on a refused proposal (rolled
  back).
- `GET /api/lore/write/entries` -> `{"entries": [{id, statement, questions,
  answers, created_at, rows: [{row_table, action, label}]}]}` (newest 50).
- Common: 400 with no active world; 422 on an empty statement; 503 with
  `WRITE_UNAVAILABLE_MESSAGE` when Ollama is down; 502 on an unparseable
  model reply; 403 from C-01 for a non-local writer.

## Context

The creator's surface: a third tab in the Lore shell. Every entity is chosen from a list; the commit button stays disabled while a name is undecided.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`src/world_engine/cockpit/static/`,
`tooling/standards/DECISIONS_INDEX.md`) are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It: creates `frontend/src/lore/writePanel.svelte.js` and `frontend/src/lore/WritePanel.svelte`; adds the « Écrire » tab to `Lore.svelte`; extends `lore_write.py` (F1); appends the decision entry.
2. Rebuild and stage the static output: `cd frontend && npm ci && npm run build` (writes `src/world_engine/cockpit/static/`).
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Commit message: `feat(lore): the Écrire tab — write, clarify, correct, commit (BRIEF-0098-f)`.

````diff
diff --git a/frontend/src/lore/Lore.svelte b/frontend/src/lore/Lore.svelte
index ec73d3a..13d9e97 100644
--- a/frontend/src/lore/Lore.svelte
+++ b/frontend/src/lore/Lore.svelte
@@ -12,10 +12,13 @@
      TICKET-0092 (BRIEF-0092-e): on an unknown_entity verdict, each unmatched
      name offers a link to that tab with the name pre-filled (openLookup); the
      question view still writes nothing -- the link only opens the panel.
-     TICKET-0095 (K1): the same tab hosts the model-choice review (ChoiceReviewPanel.svelte). */
+     TICKET-0095 (K1): the same tab hosts the model-choice review (ChoiceReviewPanel.svelte).
+     TICKET-0098 (BRIEF-0098-F, H1): the "Écrire" tab hosts the writing panel (WritePanel.svelte),
+     a second bounded reopening; the question view still writes nothing. */
   import { serverState } from '../lib/serverState.svelte.js';
   import NamesPanel from './NamesPanel.svelte';
   import ChoiceReviewPanel from './ChoiceReviewPanel.svelte';
+  import WritePanel from './WritePanel.svelte';
   import { openLookup } from './namesPanel.svelte.js';
   import {
     loreState, askLore, selectCandidate, allAmbiguitiesResolved, confirmResolution,
@@ -94,7 +97,11 @@
   <div class="lore-tabs">
     <button class:active={loreTab === 'question'} onclick={() => (loreTab = 'question')}>Question</button>
     <button class:active={loreTab === 'names'} onclick={() => (loreTab = 'names')}>Noms à lier</button>
+    <button class:active={loreTab === 'write'} onclick={() => (loreTab = 'write')}>Écrire</button>
   </div>
+  {#if loreTab === 'write'}
+    <WritePanel visible={active} />
+  {/if}
   {#if loreTab === 'names'}
     <NamesPanel visible={active} />
     <ChoiceReviewPanel visible={active} />
diff --git a/frontend/src/lore/WritePanel.svelte b/frontend/src/lore/WritePanel.svelte
new file mode 100644
index 0000000..7ecfbab
--- /dev/null
+++ b/frontend/src/lore/WritePanel.svelte
@@ -0,0 +1,232 @@
+<script>
+  /* TICKET-0098 (BRIEF-0098-F). The writing panel ("Écrire") of the Lore
+     shell: the creator writes lore in prose, answers at most one round of
+     questions, corrects the proposal and commits it. A second bounded
+     reopening of the shell's read-only lock (H1); the consultation view is
+     untouched. Every entity is chosen from a list. */
+  import { serverState } from '../lib/serverState.svelte.js';
+  import {
+    writeState, ENTITY_TYPES, SCOPE_TYPES, LEVELS, reloadForWorld, askQuestions, makeDraft,
+    pickExisting, refLabel, liveRefs, scopeRefs, addKnower, addDefault, removeAt, blockers,
+    commit, restart, loadEntries, worldEntity,
+  } from './writePanel.svelte.js';
+
+  let { visible = false } = $props();
+
+  const ACTION_LABEL = Object.freeze({
+    create: 'Fait nouveau', existing: 'Fait existant — ajouts', rewrite: 'Fait existant — réécrit',
+  });
+  const STATUS_LABEL = Object.freeze({
+    matched: 'connue', ambiguous: 'plusieurs possibles', new: 'nouvelle',
+  });
+
+  let blocking = $derived(writeState.stage === 'draft' ? blockers() : []);
+
+  $effect(() => {
+    void serverState.worldId;
+    reloadForWorld();
+  });
+
+  // Declared after the reset above, so a world change clears then reloads.
+  $effect(() => {
+    void serverState.worldId;
+    if (visible) loadEntries().catch(() => {});
+  });
+</script>
+
+<div class="queue-panel" id="lore-write-panel">
+  <div class="panel-head">
+    <h2>Lore — écrire</h2>
+    {#if writeState.stage !== 'text'}
+      <button disabled={writeState.busy} onclick={() => restart()}>Recommencer</button>
+    {/if}
+  </div>
+  <div class="queue-body">
+    {#if writeState.error}
+      <div class="r-err">{writeState.error}</div>
+    {/if}
+
+    <textarea
+      bind:value={writeState.statement}
+      rows="5"
+      placeholder="Ex : la reine possède le manoir et déteste qu'on lui coupe la parole."
+      disabled={writeState.busy || writeState.stage !== 'text'}
+    ></textarea>
+    {#if writeState.stage === 'text'}
+      <div>
+        <button disabled={writeState.busy || !writeState.statement.trim()} onclick={() => askQuestions()}>
+          {writeState.busy ? '⟳ Lecture…' : 'Proposer des faits'}
+        </button>
+      </div>
+    {/if}
+
+    {#if writeState.stage === 'questions'}
+      <div class="write-questions">
+        <strong>Quelques précisions :</strong>
+        <ol>
+          {#each writeState.questions as question, i (i)}<li>{question}</li>{/each}
+        </ol>
+        <textarea bind:value={writeState.answers} rows="3" placeholder="Tes réponses (facultatif)"
+          disabled={writeState.busy}></textarea>
+        <div class="row">
+          <button disabled={writeState.busy} onclick={() => makeDraft()}>
+            {writeState.busy ? '⟳ Rédaction…' : 'Rédiger la proposition'}
+          </button>
+          <button disabled={writeState.busy} onclick={() => { writeState.answers = ''; makeDraft(); }}>
+            Passer
+          </button>
+        </div>
+      </div>
+    {/if}
+
+    {#if writeState.stage === 'draft' && writeState.draft}
+      {@const draft = writeState.draft}
+      {#each draft.notes as note, i (i)}<div class="muted">{note}</div>{/each}
+
+      <h3>Entités</h3>
+      {#each draft.entities as entity (entity.ref)}
+        <div class="card">
+          <strong>« {entity.name} »</strong>
+          <span class="muted">{STATUS_LABEL[entity.status] || ''}</span>
+          {#if entity.decision === 'existing'}
+            → {worldEntity(entity.entity_id)?.name || entity.name}
+          {/if}
+          <div class="row">
+            <select value={entity.decision === 'existing' ? entity.entity_id : ''}
+              onchange={(e) => pickExisting(entity, e.currentTarget.value)}>
+              <option value="">— rattacher à une entité existante —</option>
+              {#each entity.candidates || [] as c (c.entity_id)}
+                <option value={c.entity_id}>{c.name} ({c.type}) — candidat</option>
+              {/each}
+              {#each entity.near || [] as c (c.entity_id)}
+                <option value={c.entity_id}>{c.name} ({c.type}) — proche {c.score}</option>
+              {/each}
+              {#each writeState.entities || [] as c (c.id)}
+                <option value={c.id}>{c.name} ({c.type})</option>
+              {/each}
+            </select>
+            <label><input type="radio" checked={entity.decision === 'create'}
+              onchange={() => { entity.decision = 'create'; entity.action = 'create'; entity.entity_id = undefined; }} />
+              Créer</label>
+            {#if entity.decision === 'create'}
+              <select bind:value={entity.type}>
+                <option value={null}>— type —</option>
+                {#each ENTITY_TYPES as t (t.value)}<option value={t.value}>{t.label}</option>{/each}
+              </select>
+            {/if}
+            <label><input type="radio" checked={entity.decision === 'text'}
+              onchange={() => (entity.decision = 'text')} /> Garder en texte</label>
+          </div>
+        </div>
+      {/each}
+
+      <h3>Faits</h3>
+      {#each draft.facts as fact, fi (fact.ref)}
+        <div class="card">
+          <div class="row"><strong>{ACTION_LABEL[fact.action]}</strong>
+            <button onclick={() => removeAt(draft.facts, fi)}>Retirer</button></div>
+          {#if fact.action !== 'existing'}
+            <textarea bind:value={fact.content} rows="2"></textarea>
+          {/if}
+          {#if fact.action === 'create'}
+            <select bind:value={fact.facet}>
+              {#each draft.facets as f (f.name)}<option value={f.name}>{f.label}</option>{/each}
+            </select>
+          {/if}
+          <div class="row">Concerne :
+            {#each fact.participants as ref, pi (ref)}
+              <span class="chip">{refLabel(ref)} <button onclick={() => removeAt(fact.participants, pi)}>×</button></span>
+            {:else}<span class="muted">le monde entier</span>{/each}
+          </div>
+          <div>Qui le sait par défaut :</div>
+          {#each fact.defaults as scope, si (si)}
+            <div class="row">
+              <select bind:value={scope.scope_type}>
+                {#each SCOPE_TYPES as s (s.value)}<option value={s.value}>{s.label}</option>{/each}
+              </select>
+              {#if scope.scope_type !== 'world'}
+                <select bind:value={scope.scope_ref}>
+                  <option value={undefined}>— choisir —</option>
+                  {#each scopeRefs(scope.scope_type) as e (e.ref)}<option value={e.ref}>{refLabel(e.ref)}</option>{/each}
+                </select>
+              {/if}
+              <button onclick={() => removeAt(fact.defaults, si)}>×</button>
+            </div>
+          {/each}
+          <button onclick={() => addDefault(fact)}>+ portée</button>
+          <div>Qui le sait précisément :</div>
+          {#each fact.knowers as knower, ki (knower.entity_ref)}
+            <div class="row">
+              {refLabel(knower.entity_ref)}
+              <select bind:value={knower.level}>
+                {#each LEVELS as l (l)}<option value={l}>{l}</option>{/each}
+              </select>
+              <label><input type="checkbox" bind:checked={knower.is_secret} /> secret</label>
+              <label><input type="checkbox" bind:checked={knower.is_incorrect} /> croyance fausse</label>
+              <button onclick={() => removeAt(fact.knowers, ki)}>×</button>
+            </div>
+          {/each}
+          <select value="" onchange={(e) => { addKnower(fact, e.currentTarget.value); e.currentTarget.value = ''; }}>
+            <option value="">+ ajouter une personne qui le sait…</option>
+            {#each (writeState.entities || []).filter((e) => e.type === 'character') as c (c.id)}
+              <option value={c.id}>{c.name}</option>
+            {/each}
+          </select>
+        </div>
+      {/each}
+
+      {#if draft.memberships.length || draft.controls.length}
+        <h3>Appartenances et possessions</h3>
+        {#each draft.memberships as m, mi (mi)}
+          <div class="row">{refLabel(m.entity_ref)} entre dans {refLabel(m.faction_ref)}
+            <button onclick={() => removeAt(draft.memberships, mi)}>×</button></div>
+        {/each}
+        {#each draft.controls as c, ci (ci)}
+          <div class="row">{refLabel(c.owner_ref)} possède {refLabel(c.location_ref)}
+            <button onclick={() => removeAt(draft.controls, ci)}>×</button></div>
+        {/each}
+      {/if}
+
+      {#each blocking as b, i (i)}<div class="r-err">{b}</div>{/each}
+      <div class="row">
+        <button disabled={writeState.busy || blocking.length > 0} onclick={() => commit()}>
+          {writeState.busy ? '⟳ Écriture…' : 'Écrire dans le monde'}
+        </button>
+        <button disabled={writeState.busy} onclick={() => makeDraft()}>Relancer la proposition</button>
+      </div>
+      <span class="muted">{liveRefs().length} entité(s) retenue(s)</span>
+    {/if}
+
+    {#if writeState.stage === 'done' && writeState.result}
+      <div class="card">
+        <strong>Écrit.</strong>
+        {#each Object.entries(writeState.result.written) as [key, n] (key)}<div>{key} : {n}</div>{/each}
+        {#each writeState.result.skipped as s, i (i)}<div class="muted">déjà présent : {s}</div>{/each}
+      </div>
+    {/if}
+
+    <details class="write-history">
+      <summary>Histoires écrites ({writeState.entries.length})</summary>
+      {#each writeState.entries as entry (entry.id)}
+        <div class="card">
+          <p class="statement">{entry.statement}</p>
+          {#if entry.answers}<p class="muted">Réponses : {entry.answers}</p>{/if}
+          <ul>
+            {#each entry.rows as row, i (i)}<li>{row.row_table} ({row.action}) — {row.label}</li>{/each}
+          </ul>
+        </div>
+      {/each}
+    </details>
+  </div>
+</div>
+
+<style>
+  .r-err { color: var(--red); }
+  .muted { color: var(--muted); font-size: 12px; }
+  textarea { width: 100%; box-sizing: border-box; font: inherit; }
+  .row { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; margin: 4px 0; }
+  .card { border-top: 1px solid var(--border); padding: 8px 0; display: flex; flex-direction: column; gap: 4px; }
+  .chip { border: 1px solid var(--border); border-radius: 10px; padding: 0 6px; }
+  .statement { white-space: pre-wrap; margin: 0; }
+  h3 { margin: 12px 0 4px; font-size: 13px; }
+</style>
diff --git a/frontend/src/lore/writePanel.svelte.js b/frontend/src/lore/writePanel.svelte.js
new file mode 100644
index 0000000..cc2753d
--- /dev/null
+++ b/frontend/src/lore/writePanel.svelte.js
@@ -0,0 +1,218 @@
+/* TICKET-0098 (BRIEF-0098-F). Non-render state + API calls for the Lore
+   shell's writing panel ("Écrire"), same shape as namesPanel.svelte.js: a
+   $state object WritePanel.svelte renders, plus the functions that mutate it.
+
+   Flow (J3): the creator's text -> at most one round of questions -> a
+   draft (C-05) she corrects -> a proposal (C-02) committed in one request.
+   Every entity is picked from a list, never typed from memory (K1 of 0095):
+   an ambiguous or new name offers the world's entities; "garder en texte"
+   drops the entity and declares the name as a mention, so the tokenizer
+   records it in "Noms à lier". */
+import { api } from '../creation/sheetRequest.svelte.js';
+
+export const ENTITY_TYPES = Object.freeze([
+  { value: 'character', label: 'personnage' },
+  { value: 'location', label: 'lieu' },
+  { value: 'faction', label: 'faction' },
+  { value: 'item', label: 'objet' },
+]);
+export const SCOPE_TYPES = Object.freeze([
+  { value: 'world', label: 'Tout le monde' },
+  { value: 'faction', label: 'Les membres de la faction' },
+  { value: 'location', label: 'Ceux qui sont dans le lieu' },
+  { value: 'rencontre', label: 'Ceux qui ont rencontré' },
+]);
+export const LEVELS = Object.freeze(['rumor', 'suspicious', 'partial', 'knows', 'fully_understands']);
+const SCOPE_ENTITY_TYPE = Object.freeze({ faction: 'faction', location: 'location' });
+const TYPE_CATEGORY = Object.freeze({
+  location: 'place', character: 'person', faction: 'faction', item: 'object',
+});
+
+function blank() {
+  return {
+    stage: 'text', statement: '', answers: '', questions: [], draft: null,
+    busy: false, error: '', result: null, entities: null, entries: [], pick: {},
+  };
+}
+
+export const writeState = $state(blank());
+
+export function reloadForWorld() {
+  Object.assign(writeState, blank());
+}
+
+const post = (path, body) => api(path, {
+  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
+});
+
+async function run(task) {
+  writeState.busy = true;
+  writeState.error = '';
+  try {
+    await task();
+  } catch (e) {
+    writeState.error = e.message;
+  } finally {
+    writeState.busy = false;
+  }
+}
+
+export async function loadWorldEntities() {
+  if (writeState.entities) return;
+  const rows = await api('/api/entities');
+  writeState.entities = rows.filter((e) => e.status === 'active');
+}
+
+export function askQuestions() {
+  return run(async () => {
+    const body = await post('/api/lore/write/questions', { statement: writeState.statement });
+    writeState.questions = body.questions;
+    if (body.questions.length === 0) {
+      await draftNow();
+    } else {
+      writeState.stage = 'questions';
+    }
+  });
+}
+
+async function draftNow() {
+  await loadWorldEntities();
+  const draft = await post('/api/lore/write/draft', {
+    statement: writeState.statement, answers: writeState.answers,
+  });
+  for (const entity of draft.entities) {
+    if (entity.status === 'matched') entity.decision = 'existing';
+    else if (entity.status === 'ambiguous') entity.decision = '';
+    else entity.decision = entity.type ? 'create' : '';
+  }
+  writeState.draft = draft;
+  writeState.result = null;
+  writeState.stage = 'draft';
+}
+
+export function makeDraft() {
+  return run(draftNow);
+}
+
+export function worldEntity(id) {
+  return (writeState.entities || []).find((e) => e.id === id);
+}
+
+export function pickExisting(entity, entityId) {
+  const picked = worldEntity(entityId);
+  if (!picked) return;
+  Object.assign(entity, {
+    decision: 'existing', action: 'existing', entity_id: picked.id, type: picked.type,
+  });
+}
+
+export function refLabel(ref) {
+  const entity = (writeState.draft?.entities || []).find((e) => e.ref === ref);
+  if (!entity) return ref;
+  if (entity.decision === 'existing') return worldEntity(entity.entity_id)?.name || entity.name;
+  return entity.name;
+}
+
+export function liveRefs(type) {
+  return (writeState.draft?.entities || []).filter((e) => e.decision
+    && e.decision !== 'text' && (!type || e.type === type));
+}
+
+export function scopeRefs(scopeType) {
+  return liveRefs(SCOPE_ENTITY_TYPE[scopeType]);
+}
+
+export function addKnower(fact, entityId) {
+  const picked = worldEntity(entityId);
+  if (!picked) return;
+  const draft = writeState.draft;
+  let entity = draft.entities.find((e) => e.decision === 'existing' && e.entity_id === picked.id);
+  if (!entity) {
+    entity = {
+      ref: `k${draft.entities.length + 1}`, name: picked.name, type: picked.type,
+      status: 'matched', decision: 'existing', action: 'existing', entity_id: picked.id,
+    };
+    draft.entities.push(entity);
+  }
+  if (!fact.knowers.some((k) => k.entity_ref === entity.ref)) {
+    fact.knowers.push({ entity_ref: entity.ref, level: 'knows', is_secret: false, is_incorrect: false });
+  }
+}
+
+export function addDefault(fact) {
+  fact.defaults.push({ scope_type: 'world' });
+}
+
+export function removeAt(list, index) {
+  list.splice(index, 1);
+}
+
+export function blockers() {
+  const draft = writeState.draft;
+  if (!draft) return ['Aucune proposition.'];
+  const out = [];
+  for (const e of draft.entities) {
+    if (!e.decision) out.push(`Choisis quoi faire de « ${e.name} ».`);
+    if (e.decision === 'create' && !e.type) out.push(`Choisis le type de « ${e.name} ».`);
+  }
+  for (const f of draft.facts) {
+    for (const d of f.defaults) {
+      if (d.scope_type !== 'world' && !d.scope_ref) out.push('Une portée ne nomme pas son entité.');
+    }
+  }
+  if (!draft.facts.length && !draft.memberships.length && !draft.controls.length) {
+    out.push('La proposition n’écrit rien.');
+  }
+  return out;
+}
+
+function toProposal() {
+  const draft = writeState.draft;
+  const dropped = new Set(draft.entities.filter((e) => e.decision === 'text').map((e) => e.ref));
+  const mentions = draft.entities.filter((e) => dropped.has(e.ref))
+    .map((e) => ({ name: e.name, category: TYPE_CATEGORY[e.type] || e.category || 'other' }));
+  const keep = (ref) => ref && !dropped.has(ref);
+  const entities = draft.entities.filter((e) => !dropped.has(e.ref)).map((e) => (
+    e.decision === 'existing'
+      ? { ref: e.ref, action: 'existing', entity_id: e.entity_id }
+      : { ref: e.ref, action: 'create', name: e.name, type: e.type }));
+  const facts = draft.facts.map((f) => {
+    const out = {
+      ref: f.ref, action: f.action,
+      participants: f.participants.filter(keep),
+      defaults: f.defaults.filter((d) => d.scope_type === 'world' || keep(d.scope_ref))
+        .map((d) => (d.scope_type === 'world' ? { scope_type: 'world' } : { ...d })),
+      knowers: f.knowers.filter((k) => keep(k.entity_ref)).map((k) => ({ ...k })),
+    };
+    if (f.action !== 'create') out.fact_id = f.fact_id;
+    if (f.action !== 'existing') out.content = f.content;
+    if (f.action === 'create') Object.assign(out, { facet: f.facet, aspect: f.aspect, mentions });
+    return out;
+  });
+  return {
+    statement: draft.statement, answers: draft.answers,
+    questions: writeState.questions.join('\n') || null, entities, facts,
+    memberships: draft.memberships.filter((m) => keep(m.entity_ref) && keep(m.faction_ref)),
+    controls: draft.controls.filter((c) => keep(c.owner_ref) && keep(c.location_ref)),
+  };
+}
+
+export function commit() {
+  return run(async () => {
+    const body = await post('/api/lore/write/commit', { proposal: toProposal() });
+    writeState.result = body;
+    writeState.stage = 'done';
+    writeState.entities = null;
+    await loadEntries();
+  });
+}
+
+export function restart() {
+  const entries = writeState.entries;
+  Object.assign(writeState, blank(), { entries });
+}
+
+export async function loadEntries() {
+  const body = await api('/api/lore/write/entries');
+  writeState.entries = body.entries;
+}
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 7bda50f..8e2d1d1 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17337,6 +17337,25 @@ was deleted since is labelled, never dropped.
 **Rejected.** H2 (the panel in Création): reactivates if the panel ever
 needs a consultation module to work.
 
+## THE WRITING PANEL -- EVERY ENTITY FROM A LIST (TICKET-0098) -- THE ÉCRIRE TAB (BRIEF-0098-f, no schema change)
+
+**H1 + J3.** The Lore shell gains a third tab, « Écrire ». The creator
+writes, gets at most one round of questions (she may answer or skip), then
+corrects the draft: every entity is chosen from a list -- a candidate, a
+near name, any active entity of the world -- or created with a type, or kept
+as text; every fact's text, facet (offered from the draft's `facets`,
+served from `FACETS`), participants, default scopes and knowers (level,
+secret, false belief) are editable; memberships and possessions can be
+removed. The commit button stays disabled while a name is undecided.
+
+**C1 -- a name kept as text** leaves the proposal and is declared as a
+mention of every new fact, so the tokenizer records it in « Noms à lier ».
+
+**M1.** « Histoires écrites » lists what each committed story produced.
+
+**Rejected.** A free field for an entity id or an unlisted name: the
+creator never recalls names (K1 of TICKET-0095).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/lore_write.py b/tooling/verify/checks/lore_write.py
index 1cf1b8a..56ba09c 100644
--- a/tooling/verify/checks/lore_write.py
+++ b/tooling/verify/checks/lore_write.py
@@ -69,6 +69,15 @@ E1 -- routes (BRIEF-0098-E), through `TestClient(app, base_url=...)` on the
       row count.
 E2 -- thin route. `cockpit/routes/lore_write.py` contains no `select(` and
    no `chat(`, and exactly one `.commit(` -- inside `write_commit`.
+F1 -- panel (BRIEF-0098-F), static:
+   a. `frontend/src/lore/Lore.svelte` imports `WritePanel.svelte` and renders
+      it only under `loreTab === 'write'`;
+   b. `frontend/src/lore/writePanel.svelte.js` calls exactly the paths
+      `/api/lore/write/questions`, `/api/lore/write/draft`,
+      `/api/lore/write/commit`, `/api/lore/write/entries` and `/api/entities`;
+   c. `WritePanel.svelte` lists the facets it offers from `draft.facets`
+      (served from `FACETS`), never from a literal list, and offers no free
+      text field for an entity id.
 C2 -- purity. `lore_write_apply.py` and `writes/lore_entries.py` contain no
    `chat(`, no `.commit(`, and import neither `ollama_client` nor any
    `cockpit` module; `lore_write_draft.py` contains no `db.add(`, no
@@ -606,6 +615,25 @@ def check_e2() -> None:
         fail(f"E2: commits in {[name for name, _ in commits]}, expected only write_commit")
 
 
+def check_f1() -> None:
+    lore = (ROOT / "frontend" / "src" / "lore")
+    shell = (lore / "Lore.svelte").read_text(encoding="utf-8")
+    if "import WritePanel from './WritePanel.svelte';" not in shell or \
+            "{#if loreTab === 'write'}\n    <WritePanel" not in shell:
+        fail("F1a: Lore.svelte does not render WritePanel under the 'write' tab")
+    state = (lore / "writePanel.svelte.js").read_text(encoding="utf-8")
+    paths = set(re.findall(r"'(/api/[a-z/_-]+)'", state))
+    want = {"/api/lore/write/questions", "/api/lore/write/draft", "/api/lore/write/commit",
+            "/api/lore/write/entries", "/api/entities"}
+    if paths != want:
+        fail(f"F1b: writePanel.svelte.js calls {sorted(paths)}")
+    panel = (lore / "WritePanel.svelte").read_text(encoding="utf-8")
+    if "draft.facets" not in panel or re.search(r"'(aversion|preference|coutume)'", panel):
+        fail("F1c: WritePanel.svelte does not take its facets from the draft")
+    if "entity_id" in re.sub(r"entity\.entity_id|c\.entity_id|entity_id\)", "", panel):
+        fail("F1c: WritePanel.svelte exposes an entity id outside a picker")
+
+
 def check_d2() -> None:
     import re as _re
 
@@ -643,6 +671,7 @@ def main() -> int:
     check_d2()
     check_e1()
     check_e2()
+    check_f1()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -651,7 +680,8 @@ def main() -> int:
           "v2.11 declares the source record and migrates from v2.10 only; a proposal "
           "writes all or nothing, each row recorded, existing rows skipped; the draft "
           "names things by name and code only and resolves both in code; the routes are "
-          "thin, guarded, and write only on commit")
+          "thin, guarded, and write only on commit; the panel lives in the Lore shell's "
+          "'Écrire' tab")
     return 0
 
 
````

## Scope OUT

- Any change to the question view or the « Noms à lier » tab.
- Editing or undoing a past story from the history (M2).
- A free text field for an entity id or an unlisted name.
- Styling beyond the shell's existing CSS variables.
- Every later brief of the lot: none — this is the last brief.

## Invariants to defend

None of CLAUDE.md's invariants is threatened by the component; the writing panel only calls C-06. **Every Création surface is a `CREATION_ISLANDS` entry** does not apply: this is the Lore shell, governed by `lore_isolation.py`.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold (line numbers may drift by a few lines; the quoted text must match).
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `npm run build` fails, or `frontend_build_fresh.py` stays red after the rebuild.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `npm run build` prints a Svelte warning located in `WritePanel.svelte`: report it verbatim; fix only if it is an a11y label warning (add the label), otherwise leave it.

REPORT-ONLY:
- Timing of the corpus run.
- Any Starlette/httpx deprecation warning printed by a check.
- Any Svelte warning printed for a file this brief does not touch.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and the files under `src/world_engine/cockpit/static/`.
- `lore_write.py` → `PASS … the panel lives in the Lore shell's 'Écrire' tab`.
- `frontend_build_fresh.py`, `module_budget.py` → `PASS`.
- `python -m tooling.verify.run --ticket TICKET-0098-lore-writing` → `"green": true`.
- `corpus_gate.py` → 128/128.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `THE WRITING PANEL -- EVERY ENTITY FROM A LIST (TICKET-0098) … (BRIEF-0098-f, no schema change)`. This is the last brief: after it the ticket goes to `/verify` and the live gate.
