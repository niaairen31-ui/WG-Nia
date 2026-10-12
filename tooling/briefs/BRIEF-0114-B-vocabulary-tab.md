<!-- slug: vocabulary-tab -->
# BRIEF 0114-B — "« Vocabulaire du monde » -- the states, the event types and the sortes in one Création tab, a near name asked before it is written"

Lot: LOT-0114-event-journal.md (authoritative on conflict)
Depends on: BRIEF-0114-A (C-02, C-03)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0114-A's commit).

- `frontend/src/creation/tabs.js:361` -> `  etats: {`
- `frontend/src/creation/registry.js:572` -> `  states: Object.freeze({`
- `frontend/src/creation/mount.js:49` -> its `COMPONENTS` line ends `questOffers: QuestOffers, debts: Debts, states: States };`
- `src/world_engine/writes/event_types.py` -> `def write_event_type(` (A's), `def write_sorte(`
- No `src/world_engine/cockpit/routes/event_types.py`, no `frontend/src/creation/Vocabulary.svelte`.

## Facts carried

### R-09 — the vocabulary helpers TICKET-0113 left
Opened: `src/world_engine/lore_resolve.py:73` (`normalize_surface`:
case- and accent-blind), `:186` (`near_ratio`);
`src/world_engine/attributes.py:129` (`world_entity_types`), `:274`
(`near_attributes`, the near-name precedent).
Consequence: a type's or sorte's name is compared with
`normalize_surface` in Python (SQLite's `lower()` is not accent-blind),
near names by `near_ratio`.

### R-10 — Création's registries
Opened: `frontend/src/creation/tabs.js:333` (`evenements`), `:361`
(`etats`), `registry.js:572` (island `states`), `mount.js:49`
(`COMPONENTS`); `.claude/rules/frontend.md` (INV-49, INV-50, INV-54).
Consequence: B replaces `etats` by `vocabulaire` (island `vocabulary`,
origin `new`), sized in `creation.css`; `evenements` stays, now the
journal.

## Contracts

### C-02 — `event_vocab` (reads)
Produced by: BRIEF-0114-A   Consumed by: B-H
`DOMAIN_LABELS_FR`, `DOMAIN_ROLE_FR = "Impliqué"`, `EVENT_FORM = "event"`;
`RoleView(id, name, position, entity_types, accepts_sorte, status)`,
`ScopeView(kind, role_id, level)`, `EventTypeView(id, world_id, name,
domain, counts_quantity, in_chronicle, participants_secret, status, roles,
scopes)` with `role(role_id)` and `active_roles()`;
`role_accepts(role, entity_type) -> bool`; `type_view(db, type_id) ->
Optional[EventTypeView]`; `world_event_types(db, world_id,
include_retired=False)`; `world_sortes(db, world_id,
include_retired=False) -> list[EventSorte]`; `near_event_types` /
`near_sortes(db, world_id, name, exclude_id=None) ->
tuple[NearName(id, name, score)]` (retired included, best first). Writes
nothing (EA7).

### C-03 — `writes.event_types` (the vocabulary's one writer)
Produced by: BRIEF-0114-A   Consumed by: B, C, G, H
`RoleSpec(name, entity_types=(), accepts_sorte=False, id=None)`,
`ScopeSpec(kind, role=None (a role's NAME), level="knows")`,
`EventTypeSpec(name, domain="other", roles=(), counts_quantity=False,
in_chronicle=True, participants_secret=False, scopes=())`;
`clean_event_type(db, world_id, spec, type_id=None) -> EventTypeSpec`
(`ValueError`, writes nothing); `write_event_type(db, *, world_id, spec,
type_id=None) -> EventType` (flushed; on an existing type nothing in use
is taken away, an unused role is retired); `set_event_type_status`;
`clean_sorte_name(db, world_id, name, sorte_id=None) -> str`;
`write_sorte(db, *, world_id, name, sorte_id=None) -> EventSorte`;
`set_sorte_status`; `ensure_domain_type(db, *, world_id, domain) ->
EventType` (the world's type of that domain's label, or made with one
role « Impliqué » accepting every entity type).

### C-04 — the vocabulary's routes and form
Produced by: BRIEF-0114-B   Consumed by: G
`GET /api/event-vocabulary` -> `{types: [type_dict], sortes: [{id, name,
status}], entity_types, domains: [{value, label}], scope_kinds, levels}`;
`POST /api/event-types`, `PUT /api/event-types/{id}` (`EventTypeBody`:
name, domain, roles [{name, entity_types, accepts_sorte, id}],
counts_quantity, in_chronicle, participants_secret, scopes [{kind, role,
level}], `confirm_near`) -> `{saved: false, near: [{id, name, score}]}`
or `{saved: true, type: type_dict}`; 422 on a refusal;
`POST /api/event-sortes` (`{name, confirm_near}`) -> `{saved, sorte}` or
`{saved: false, near}`; `.../status`. Frontend:
`eventVocab.svelte.js` `typeDraft(type)`, `typeBody(draft, confirmNear)`,
`vocabState`, `loadVocabulary(worldId)`; `EventTypeForm.svelte` props
`{draft, vocab}`.

## Context

T3: the world's vocabulary -- the states of TICKET-0113, the event types, the sortes -- is one Création tab, « Vocabulaire du monde »; « Événements » stays, and becomes the journal in C. A name near another's (« Tuers » beside « Tuer ») answers `saved: false` with the near ones, as 0113's states do: the creator opens the existing one or creates anyway. `EventTypeForm` is written to be reused by G's card.

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `cockpit/routes/event_types.py` (new, C-04), registered in `cockpit/app.py`: `GET /api/event-vocabulary`, `POST`/`PUT /api/event-types`, `.../status`, the same for `/api/event-sortes`; `event_type_spec(body)`, `type_dict`;
   - frontend: `Vocabulary.svelte` (États, Types d'événements, Sortes), `EventTypes.svelte`, `EventTypeForm.svelte`, `Sortes.svelte`, `eventVocab.svelte.js`; `tabs.js`'s `etats` entry becomes `vocabulaire` (island `vocabulary`), `registry.js` declares `vocabulary` (origin `new`, TICKET-0114) in place of `states`, `mount.js` maps it, `Creation.svelte` its container, `frontend/public/creation.css` sizes `#creation-vocabulaire` (INV-54);
   - `checks/attributes.py` AC3 retargeted on the new tab; EB1-EB2 added to `checks/event_journal.py`;
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - frontend/public/creation.css
   - frontend/src/creation/Creation.svelte
   - frontend/src/creation/EventTypeForm.svelte
   - frontend/src/creation/EventTypes.svelte
   - frontend/src/creation/Sortes.svelte
   - frontend/src/creation/States.svelte
   - frontend/src/creation/Vocabulary.svelte
   - frontend/src/creation/eventVocab.svelte.js
   - frontend/src/creation/mount.js
   - frontend/src/creation/registry.js
   - frontend/src/creation/tabs.js
   - src/world_engine/cockpit/app.py
   - src/world_engine/cockpit/routes/event_types.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/attributes.py
   - tooling/verify/checks/event_journal.py

````diff
diff --git a/frontend/public/creation.css b/frontend/public/creation.css
index 5056a20..e663234 100644
--- a/frontend/public/creation.css
+++ b/frontend/public/creation.css
@@ -311,7 +311,7 @@ input.notes::placeholder { color: var(--muted); }
 #creation-subjects    { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
 #creation-quetes      { flex: 1; min-height: 0; overflow: auto; }
 #creation-dettes      { flex: 1; min-height: 0; overflow: auto; }
-#creation-etats       { flex: 1; min-height: 0; overflow: auto; }
+#creation-vocabulaire { flex: 1; min-height: 0; overflow: auto; }
 
 /* ── Région review tree (BRIEF-36) ───────────────────────────────────────── */
 .review-node   { border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; margin: 6px 0; }
diff --git a/frontend/src/creation/Creation.svelte b/frontend/src/creation/Creation.svelte
index 81fa26a..05a16d6 100644
--- a/frontend/src/creation/Creation.svelte
+++ b/frontend/src/creation/Creation.svelte
@@ -253,8 +253,9 @@
   <div id="creation-quetes" style:display={containerVisible('creation-quetes') ? '' : 'none'}></div>
   <!-- ── Dettes sub-tab -- Svelte island (TICKET-0110): empty by construction ── -->
   <div id="creation-dettes" style:display={containerVisible('creation-dettes') ? '' : 'none'}></div>
-  <!-- ── États sub-tab -- Svelte island (TICKET-0113): empty by construction ── -->
-  <div id="creation-etats" style:display={containerVisible('creation-etats') ? '' : 'none'}></div>
+  <!-- ── Vocabulaire du monde sub-tab -- Svelte island (TICKET-0113 « États »,
+       TICKET-0114 its event types and sortes): empty by construction ── -->
+  <div id="creation-vocabulaire" style:display={containerVisible('creation-vocabulaire') ? '' : 'none'}></div>
   <div id="creation-subjects" style:display={containerVisible('creation-subjects') ? '' : 'none'}></div>
 
   <!-- ── Review Queue sub-tab -- Svelte island: empty by construction ── -->
diff --git a/frontend/src/creation/EventTypeForm.svelte b/frontend/src/creation/EventTypeForm.svelte
new file mode 100644
index 0000000..89900e3
--- /dev/null
+++ b/frontend/src/creation/EventTypeForm.svelte
@@ -0,0 +1,99 @@
+<script>
+  /* TICKET-0114 (BRIEF-0114-B, B1, C1, D1, W1, X1). One event type as the
+     creator edits it: its name and domain; whether it counts a quantity,
+     enters the chronicle the models read, and whether its participants keep
+     it secret by default; its roles in order -- each accepting entity types
+     and, or, a sorte; who learns it besides its participants, each at a
+     level. `draft` is a `typeDraft` owned by the caller -- the « Vocabulaire
+     du monde » tab, or a proposal card (BRIEF-0114-G/H); `vocab` the
+     vocabulary lists (`vocabState`). The server refuses taking away what is
+     in use. */
+  let { draft, vocab } = $props();
+
+  function toggle(list, type) {
+    const at = list.indexOf(type);
+    if (at >= 0) list.splice(at, 1);
+    else list.push(type);
+  }
+
+  function addRole() {
+    draft.roles.push({ id: null, name: '', entity_types: ['character'], accepts_sorte: false });
+  }
+
+  function addScope() {
+    draft.scopes.push({ kind: 'location', role: null, level: 'knows' });
+  }
+
+  const withRole = (kind) => kind === 'rencontre' || kind === 'faction';
+</script>
+
+<div class="etype-form">
+  <label>Nom <input type="text" bind:value={draft.name} placeholder="Tuer, Repérer, Pacte…"></label>
+  <label>Domaine
+    <select bind:value={draft.domain}>
+      {#each vocab.domains as d (d.value)}<option value={d.value}>{d.label}</option>{/each}
+    </select>
+  </label>
+  <label class="etype-check"><input type="checkbox" bind:checked={draft.counts_quantity}>
+    Compte une quantité (« 3 loups »)</label>
+  <label class="etype-check"><input type="checkbox" bind:checked={draft.in_chronicle}>
+    Entre dans la chronique que lisent le MJ et le monde</label>
+  <label class="etype-check"><input type="checkbox" bind:checked={draft.participants_secret}>
+    Par défaut, les participants gardent le secret</label>
+
+  <div class="etype-block">
+    <span>Rôles</span>
+    {#each draft.roles as role, k (k)}
+      <div class="etype-role">
+        <div class="etype-line">
+          <input type="text" bind:value={role.name} placeholder="tueur, victime, lieu…">
+          <button class="btn-icon" title="Retirer le rôle" onclick={() => draft.roles.splice(k, 1)}>✕</button>
+        </div>
+        <div class="etype-types">
+          {#each vocab.entityTypes as t (t.type)}
+            <label class="etype-check"><input type="checkbox" checked={role.entity_types.includes(t.type)}
+                   onchange={() => toggle(role.entity_types, t.type)}> {t.label}</label>
+          {/each}
+          <label class="etype-check"><input type="checkbox" bind:checked={role.accepts_sorte}> une sorte</label>
+        </div>
+      </div>
+    {/each}
+    <button onclick={addRole}>+ rôle</button>
+  </div>
+
+  <div class="etype-block">
+    <span>Qui l'apprend, en plus des participants</span>
+    {#each draft.scopes as scope, k (k)}
+      <div class="etype-line">
+        <select bind:value={scope.kind}>
+          {#each vocab.scopeKinds as s (s.value)}<option value={s.value}>{s.label}</option>{/each}
+        </select>
+        {#if withRole(scope.kind)}
+          <select bind:value={scope.role}>
+            <option value={null}>— rôle —</option>
+            {#each draft.roles as role, r (r)}<option value={role.name}>{role.name}</option>{/each}
+          </select>
+        {/if}
+        <select bind:value={scope.level}>
+          {#each vocab.levels as l (l.value)}<option value={l.value}>{l.label}</option>{/each}
+        </select>
+        <button class="btn-icon" title="Retirer" onclick={() => draft.scopes.splice(k, 1)}>✕</button>
+      </div>
+    {/each}
+    {#if !draft.scopes.length}<div class="etype-hint">Personne d'autre que les participants.</div>{/if}
+    <button onclick={addScope}>+ portée</button>
+  </div>
+</div>
+
+<style>
+  .etype-form label { display: block; margin: 4px 0; }
+  .etype-form input[type="text"] { width: 100%; box-sizing: border-box; }
+  .etype-block { margin: 8px 0; }
+  .etype-block > span { display: block; font-size: 12px; color: var(--muted); }
+  .etype-role { border-left: 2px solid var(--border, #444); padding-left: 6px; margin: 4px 0; }
+  .etype-line { display: flex; gap: 6px; align-items: center; margin: 2px 0; }
+  .etype-line input[type="text"] { flex: 1; }
+  .etype-types { display: flex; flex-wrap: wrap; }
+  .etype-check { display: inline-flex !important; gap: 4px; align-items: center; margin-right: 10px !important; }
+  .etype-hint { font-size: 12px; color: var(--muted); }
+</style>
diff --git a/frontend/src/creation/EventTypes.svelte b/frontend/src/creation/EventTypes.svelte
new file mode 100644
index 0000000..7e271e8
--- /dev/null
+++ b/frontend/src/creation/EventTypes.svelte
@@ -0,0 +1,121 @@
+<script>
+  /* TICKET-0114 (BRIEF-0114-B, B1, C1, W1, T3). The event types of the
+     world, in « Vocabulaire du monde »: each with its domain, its roles and
+     the types they accept, who learns it, how many events it has; one type
+     written or saved through EventTypeForm. A name near another type's is
+     not saved until the creator picks: open the existing one, or create
+     anyway. A type is retired (refused while a condition names it) or
+     restored, never deleted. State and requests live in
+     eventVocab.svelte.js. */
+  import { serverState } from '../lib/serverState.svelte.js';
+  import EventTypeForm from './EventTypeForm.svelte';
+  import {
+    vocabState, newTypeDraft, editType, saveTypeDraft, setVocabStatus,
+  } from './eventVocab.svelte.js';
+
+  /** The section's « + Nouveau » (Vocabulary.svelte routes it here). */
+  export function primaryAction() {
+    newTypeDraft();
+  }
+
+  let typeLabels = $derived(Object.fromEntries(vocabState.entityTypes.map((t) => [t.type, t.label])));
+  let scopeLabels = $derived(Object.fromEntries(vocabState.scopeKinds.map((s) => [s.value, s.label])));
+  let levelLabels = $derived(Object.fromEntries(vocabState.levels.map((l) => [l.value, l.label])));
+
+  function roleLine(role) {
+    const accepts = role.entity_types.map((t) => typeLabels[t] || t);
+    if (role.accepts_sorte) accepts.push('une sorte');
+    return `${role.name} (${accepts.join(', ')})`;
+  }
+
+  function scopeLine(scope) {
+    return `${scopeLabels[scope.kind] || scope.kind}${scope.role ? ' ' + scope.role : ''} : ${levelLabels[scope.level] || scope.level}`;
+  }
+
+  function openNear(id) {
+    const found = vocabState.types.find((t) => t.id === id);
+    if (found) editType(found);
+  }
+</script>
+
+<div class="vocab-pane">
+  <div class="queue-panel vocab-list">
+    <div class="panel-head">
+      <h2>Types d'événements</h2>
+      <span>{vocabState.types.length}</span>
+    </div>
+    <div class="queue-body">
+      {#if !serverState.worldId}
+        <div class="empty">Aucun monde actif.</div>
+      {:else if vocabState.loadError}
+        <div class="empty" style="color:var(--red)">Erreur : {vocabState.loadError}</div>
+      {:else if !vocabState.types.length}
+        <div class="empty">Aucun type d'événement. « + Nouveau » en crée un.</div>
+      {:else}
+        {#each vocabState.types as type (type.id)}
+          <div class="row-card" class:closed={type.status !== 'active'}>
+            <div class="vocab-head">
+              <strong>{type.name}</strong>
+              <span class="badge b-other">{type.domain_label}</span>
+              {#if type.counts_quantity}<span class="badge b-other">quantité</span>{/if}
+              {#if type.in_chronicle}<span class="badge b-other">chronique</span>{/if}
+              {#if type.participants_secret}<span class="badge b-other">secret</span>{/if}
+              {#if type.status !== 'active'}<span class="badge b-other">retiré</span>{/if}
+              <span class="muted">{type.events} événement(s)</span>
+            </div>
+            <div class="muted">Rôles : {type.roles.filter((r) => r.status === 'active').map(roleLine).join(' · ')}</div>
+            <div class="muted">Apprennent : {type.scopes.length ? type.scopes.map(scopeLine).join(' · ') : 'les participants seulement'}</div>
+            <div class="inline">
+              <button onclick={() => editType(type)}>Modifier</button>
+              {#if type.status === 'active'}
+                <button disabled={type.in_condition} title={type.in_condition ? 'Une condition le nomme' : ''}
+                        onclick={() => setVocabStatus(serverState.worldId, 'type', type.id, 'retired')}>Retirer</button>
+              {:else}
+                <button onclick={() => setVocabStatus(serverState.worldId, 'type', type.id, 'active')}>Rétablir</button>
+              {/if}
+            </div>
+            {#if vocabState.actionError?.id === type.id}<div class="r-err">{vocabState.actionError.message}</div>{/if}
+          </div>
+        {/each}
+      {/if}
+    </div>
+  </div>
+
+  {#if vocabState.typeDraft}
+    <div class="queue-panel vocab-editor">
+      <div class="panel-head"><h2>{vocabState.typeDraft.id ? 'Modifier le type' : 'Nouveau type'}</h2></div>
+      <div class="queue-body">
+        <EventTypeForm draft={vocabState.typeDraft} vocab={vocabState} />
+        {#if vocabState.near.length}
+          <div class="near">
+            <div>Ce nom ressemble à :</div>
+            {#each vocabState.near as n (n.id)}
+              <button onclick={() => openNear(n.id)}>{n.name} — {n.score} %</button>
+            {/each}
+            <button class="btn-send" onclick={() => saveTypeDraft(serverState.worldId, true)}>Créer quand même</button>
+          </div>
+        {/if}
+        {#if vocabState.saveError}<div class="r-err">{vocabState.saveError}</div>{/if}
+        <div style="margin-top:10px">
+          <button class="btn-send" disabled={vocabState.saving} onclick={() => saveTypeDraft(serverState.worldId, false)}>
+            {vocabState.saving ? 'Enregistrement…' : '💾 Enregistrer'}
+          </button>
+          <button onclick={() => (vocabState.typeDraft = null)}>Annuler</button>
+        </div>
+      </div>
+    </div>
+  {/if}
+</div>
+
+<style>
+  .vocab-pane { display: flex; gap: 12px; align-items: flex-start; }
+  .vocab-list { flex: 1; }
+  .vocab-editor { flex: 0 0 460px; }
+  .vocab-head { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
+  .vocab-head .badge { width: auto; }
+  .inline { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-top: 4px; }
+  .row-card.closed { opacity: 0.6; }
+  .muted { color: var(--muted); font-size: 12px; }
+  .r-err { color: var(--red); }
+  .near { margin-top: 10px; display: flex; flex-direction: column; gap: 4px; }
+</style>
diff --git a/frontend/src/creation/Sortes.svelte b/frontend/src/creation/Sortes.svelte
new file mode 100644
index 0000000..db4d339
--- /dev/null
+++ b/frontend/src/creation/Sortes.svelte
@@ -0,0 +1,90 @@
+<script>
+  /* TICKET-0114 (BRIEF-0114-B, D1, T3). The sortes of the world, in
+     « Vocabulaire du monde »: the anonymous kinds -- « loup », « bandit » --
+     a role accepting a sorte is filled by, with the event's quantity. One
+     sorte added or renamed at a time; a name near another's waits for the
+     creator's pick; a sorte is retired (refused while a condition names
+     it) or restored, never deleted. State and requests live in
+     eventVocab.svelte.js. */
+  import { serverState } from '../lib/serverState.svelte.js';
+  import {
+    vocabState, newSorteDraft, editSorte, saveSorteDraft, setVocabStatus,
+  } from './eventVocab.svelte.js';
+
+  /** The section's « + Nouveau » (Vocabulary.svelte routes it here). */
+  export function primaryAction() {
+    newSorteDraft();
+  }
+
+  function openNear(id) {
+    const found = vocabState.sortes.find((s) => s.id === id);
+    if (found) editSorte(found);
+  }
+</script>
+
+<div class="vocab-pane">
+  <div class="queue-panel vocab-list">
+    <div class="panel-head">
+      <h2>Sortes</h2>
+      <span>{vocabState.sortes.length}</span>
+    </div>
+    <div class="queue-body">
+      {#if !serverState.worldId}
+        <div class="empty">Aucun monde actif.</div>
+      {:else if !vocabState.sortes.length}
+        <div class="empty">Aucune sorte. Une sorte compte ce qui n'a pas de nom : « 3 loups ».</div>
+      {:else}
+        {#each vocabState.sortes as sorte (sorte.id)}
+          <div class="row-card sorte-row" class:closed={sorte.status !== 'active'}>
+            <strong>{sorte.name}</strong>
+            {#if sorte.status !== 'active'}<span class="badge b-other">retirée</span>{/if}
+            <button onclick={() => editSorte(sorte)}>Renommer</button>
+            {#if sorte.status === 'active'}
+              <button onclick={() => setVocabStatus(serverState.worldId, 'sorte', sorte.id, 'retired')}>Retirer</button>
+            {:else}
+              <button onclick={() => setVocabStatus(serverState.worldId, 'sorte', sorte.id, 'active')}>Rétablir</button>
+            {/if}
+            {#if vocabState.actionError?.id === sorte.id}<div class="r-err">{vocabState.actionError.message}</div>{/if}
+          </div>
+        {/each}
+      {/if}
+    </div>
+  </div>
+
+  {#if vocabState.sorteDraft}
+    <div class="queue-panel vocab-editor">
+      <div class="panel-head"><h2>{vocabState.sorteDraft.id ? 'Renommer la sorte' : 'Nouvelle sorte'}</h2></div>
+      <div class="queue-body">
+        <label>Nom <input type="text" bind:value={vocabState.sorteDraft.name} placeholder="loup, bandit…"></label>
+        {#if vocabState.near.length}
+          <div class="near">
+            <div>Ce nom ressemble à :</div>
+            {#each vocabState.near as n (n.id)}
+              <button onclick={() => openNear(n.id)}>{n.name} — {n.score} %</button>
+            {/each}
+            <button class="btn-send" onclick={() => saveSorteDraft(serverState.worldId, true)}>Créer quand même</button>
+          </div>
+        {/if}
+        {#if vocabState.saveError}<div class="r-err">{vocabState.saveError}</div>{/if}
+        <div style="margin-top:10px">
+          <button class="btn-send" disabled={vocabState.saving} onclick={() => saveSorteDraft(serverState.worldId, false)}>
+            {vocabState.saving ? 'Enregistrement…' : '💾 Enregistrer'}
+          </button>
+          <button onclick={() => (vocabState.sorteDraft = null)}>Annuler</button>
+        </div>
+      </div>
+    </div>
+  {/if}
+</div>
+
+<style>
+  .vocab-pane { display: flex; gap: 12px; align-items: flex-start; }
+  .vocab-list { flex: 1; }
+  .vocab-editor { flex: 0 0 360px; }
+  .sorte-row { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
+  .sorte-row .badge { width: auto; }
+  .row-card.closed { opacity: 0.6; }
+  .r-err { color: var(--red); }
+  .near { margin-top: 10px; display: flex; flex-direction: column; gap: 4px; }
+  label input[type="text"] { width: 100%; box-sizing: border-box; }
+</style>
diff --git a/frontend/src/creation/States.svelte b/frontend/src/creation/States.svelte
index 200dc66..d448895 100644
--- a/frontend/src/creation/States.svelte
+++ b/frontend/src/creation/States.svelte
@@ -5,8 +5,9 @@
      AttributeDefinitionForm. A name near another attribute's is not saved
      until the creator picks: open the existing one, or create anyway. A
      definition is retired (refused while a condition names it) or
-     restored, never deleted. Its CREATION_ISLANDS entry declares origin
-     'new'. State and requests live in attributes.svelte.js. */
+     restored, never deleted. Since TICKET-0114 (BRIEF-0114-B, T3) a section
+     of the « Vocabulaire du monde » island (Vocabulary.svelte), no longer an
+     island of its own. State and requests live in attributes.svelte.js. */
   import { serverState } from '../lib/serverState.svelte.js';
   import AttributeDefinitionForm from './AttributeDefinitionForm.svelte';
   import {
diff --git a/frontend/src/creation/Vocabulary.svelte b/frontend/src/creation/Vocabulary.svelte
new file mode 100644
index 0000000..57a061e
--- /dev/null
+++ b/frontend/src/creation/Vocabulary.svelte
@@ -0,0 +1,52 @@
+<script>
+  /* TICKET-0114 (BRIEF-0114-B, T3). The « Vocabulaire du monde » island:
+     what the world can say grows by data, and the creator keeps it in one
+     place -- its states (States.svelte, TICKET-0113, unchanged), its event
+     types (EventTypes.svelte) and its sortes (Sortes.svelte), one section
+     shown at a time. The tab's « + Nouveau » goes to the section shown. Its
+     CREATION_ISLANDS entry declares origin 'new'. */
+  import { serverState } from '../lib/serverState.svelte.js';
+  import States from './States.svelte';
+  import EventTypes from './EventTypes.svelte';
+  import Sortes from './Sortes.svelte';
+  import { loadVocabulary, vocabState } from './eventVocab.svelte.js';
+
+  const SECTIONS = [
+    { key: 'states', label: 'États' },
+    { key: 'types', label: "Types d'événements" },
+    { key: 'sortes', label: 'Sortes' },
+  ];
+  let section = $state('states');
+  let refs = $state({ states: null, types: null, sortes: null });
+
+  $effect(() => {
+    vocabState.typeDraft = null;
+    vocabState.sorteDraft = null;
+    loadVocabulary(serverState.worldId);
+  });
+
+  /** The tab's « + Nouveau » (creation_island.py rule 11). */
+  export function primaryAction() {
+    refs[section]?.primaryAction();
+  }
+</script>
+
+<div class="vocabulary">
+  <div class="vocab-sections">
+    {#each SECTIONS as s (s.key)}
+      <button class:active={section === s.key} onclick={() => (section = s.key)}>{s.label}</button>
+    {/each}
+  </div>
+  {#if section === 'states'}
+    <States bind:this={refs.states} />
+  {:else if section === 'types'}
+    <EventTypes bind:this={refs.types} />
+  {:else}
+    <Sortes bind:this={refs.sortes} />
+  {/if}
+</div>
+
+<style>
+  .vocab-sections { display: flex; gap: 6px; margin-bottom: 10px; }
+  .vocab-sections button.active { font-weight: 600; border-bottom: 2px solid var(--accent, #c9a14a); }
+</style>
diff --git a/frontend/src/creation/eventVocab.svelte.js b/frontend/src/creation/eventVocab.svelte.js
new file mode 100644
index 0000000..9267eeb
--- /dev/null
+++ b/frontend/src/creation/eventVocab.svelte.js
@@ -0,0 +1,150 @@
+/* TICKET-0114 (BRIEF-0114-B, B1, C1, D1, W1). State and requests of the
+   event vocabulary in « Vocabulaire du monde »: the world's event types and
+   its sortes (GET /api/event-vocabulary), with what a type may name --
+   entity types, domains, scope kinds, levels. One type draft, written whole
+   (POST/PUT /api/event-types); one sorte draft (POST/PUT /api/event-sortes);
+   retire and restore (…/status, a type refused while a condition names it).
+   A name near another's comes back `saved: false` with the near ones: the
+   creator opens the existing one or creates anyway (`confirm_near`).
+   `typeDraft` / `typeBody` are shared with the journal's sheet and the
+   interpreter's and analyzer's proposal cards (BRIEF-0114-C/G/H). */
+import { api } from './sheetRequest.svelte.js';
+
+export const vocabState = $state({
+  types: [],
+  sortes: [],
+  entityTypes: [],
+  domains: [],
+  scopeKinds: [],
+  levels: [],
+  loadError: '',
+  typeDraft: null, // typeDraft(), plus `id` when it edits one
+  sorteDraft: null, // { id, name }
+  near: [],
+  saving: false,
+  saveError: '',
+  actionError: null, // { id, message }
+});
+
+/** A type as the form edits it, from a type (or blank). */
+export function typeDraft(type) {
+  if (!type) {
+    return { id: null, name: '', domain: 'other', counts_quantity: false, in_chronicle: true,
+             participants_secret: false, roles: [{ id: null, name: '', entity_types: ['character'], accepts_sorte: false }],
+             scopes: [] };
+  }
+  return {
+    id: type.id || null, name: type.name, domain: type.domain, counts_quantity: !!type.counts_quantity,
+    in_chronicle: type.in_chronicle !== false, participants_secret: !!type.participants_secret,
+    roles: (type.roles || []).filter((r) => r.status !== 'retired').map((r) => ({
+      id: r.id || null, name: r.name, entity_types: [...(r.entity_types || [])], accepts_sorte: !!r.accepts_sorte,
+    })),
+    scopes: (type.scopes || []).map((s) => ({ kind: s.kind, role: s.role || null, level: s.level })),
+  };
+}
+
+/** The request body of a type draft (`EventTypeBody`). */
+export function typeBody(draft, confirmNear) {
+  return {
+    name: draft.name, domain: draft.domain, counts_quantity: draft.counts_quantity,
+    in_chronicle: draft.in_chronicle, participants_secret: draft.participants_secret,
+    roles: draft.roles.map((r) => ({ id: r.id || null, name: r.name, entity_types: r.entity_types,
+                                     accepts_sorte: r.accepts_sorte })),
+    scopes: draft.scopes.map((s) => ({ kind: s.kind, role: ['rencontre', 'faction'].includes(s.kind) ? s.role : null,
+                                       level: s.level })),
+    confirm_near: !!confirmNear,
+  };
+}
+
+function clearEdit() {
+  vocabState.saveError = '';
+  vocabState.near = [];
+}
+
+export function newTypeDraft() {
+  clearEdit();
+  vocabState.sorteDraft = null;
+  vocabState.typeDraft = typeDraft(null);
+}
+
+export function editType(type) {
+  clearEdit();
+  vocabState.sorteDraft = null;
+  vocabState.typeDraft = typeDraft(type);
+}
+
+export function newSorteDraft() {
+  clearEdit();
+  vocabState.typeDraft = null;
+  vocabState.sorteDraft = { id: null, name: '' };
+}
+
+export function editSorte(sorte) {
+  clearEdit();
+  vocabState.typeDraft = null;
+  vocabState.sorteDraft = { id: sorte.id, name: sorte.name };
+}
+
+export async function loadVocabulary(worldId) {
+  if (!worldId) { vocabState.types = []; vocabState.sortes = []; return; }
+  vocabState.loadError = '';
+  try {
+    const data = await api('/api/event-vocabulary');
+    vocabState.types = data.types;
+    vocabState.sortes = data.sortes;
+    vocabState.entityTypes = data.entity_types;
+    vocabState.domains = data.domains;
+    vocabState.scopeKinds = data.scope_kinds;
+    vocabState.levels = data.levels;
+  } catch (e) {
+    vocabState.loadError = e.message;
+  }
+}
+
+async function save(path, method, body, worldId) {
+  vocabState.saving = true;
+  vocabState.saveError = '';
+  try {
+    const result = await api(path, { method, headers: { 'Content-Type': 'application/json' },
+                                     body: JSON.stringify(body) });
+    if (!result.saved) {
+      vocabState.near = result.near;
+      return;
+    }
+    vocabState.typeDraft = null;
+    vocabState.sorteDraft = null;
+    vocabState.near = [];
+    await loadVocabulary(worldId);
+  } catch (e) {
+    vocabState.saveError = e.message;
+  } finally {
+    vocabState.saving = false;
+  }
+}
+
+export async function saveTypeDraft(worldId, confirmNear) {
+  const draft = vocabState.typeDraft;
+  if (!draft) return;
+  const path = draft.id ? '/api/event-types/' + encodeURIComponent(draft.id) : '/api/event-types';
+  await save(path, draft.id ? 'PUT' : 'POST', typeBody(draft, confirmNear), worldId);
+}
+
+export async function saveSorteDraft(worldId, confirmNear) {
+  const draft = vocabState.sorteDraft;
+  if (!draft) return;
+  const path = draft.id ? '/api/event-sortes/' + encodeURIComponent(draft.id) : '/api/event-sortes';
+  await save(path, draft.id ? 'PUT' : 'POST', { name: draft.name, confirm_near: !!confirmNear }, worldId);
+}
+
+export async function setVocabStatus(worldId, kind, id, status) {
+  vocabState.actionError = null;
+  const base = kind === 'type' ? '/api/event-types/' : '/api/event-sortes/';
+  try {
+    await api(base + encodeURIComponent(id) + '/status', {
+      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }),
+    });
+    await loadVocabulary(worldId);
+  } catch (e) {
+    vocabState.actionError = { id, message: e.message };
+  }
+}
diff --git a/frontend/src/creation/mount.js b/frontend/src/creation/mount.js
index f677fd3..72b2fb0 100644
--- a/frontend/src/creation/mount.js
+++ b/frontend/src/creation/mount.js
@@ -44,9 +44,9 @@ import QueueBatchBar from './QueueBatchBar.svelte';
 import SubjectWorklist from './SubjectWorklist.svelte';
 import QuestOffers from './QuestOffers.svelte';
 import Debts from './Debts.svelte';
-import States from './States.svelte';
+import Vocabulary from './Vocabulary.svelte';
 
-const COMPONENTS = { constructeur: Constructeur, entityList: EntityList, entitySheet: Sheet, region: Region, batch: RoomBatch, npcAgent: NpcAgent, linkAgent: LinkAgent, artefacts: Artefacts, registre: Registre, prompts: Prompts, pjSkillFiche: PjSkillFiche, queueFilters: QueueFilters, queue: Queue, queueBatchBar: QueueBatchBar, subjectWorklist: SubjectWorklist, questOffers: QuestOffers, debts: Debts, states: States };
+const COMPONENTS = { constructeur: Constructeur, entityList: EntityList, entitySheet: Sheet, region: Region, batch: RoomBatch, npcAgent: NpcAgent, linkAgent: LinkAgent, artefacts: Artefacts, registre: Registre, prompts: Prompts, pjSkillFiche: PjSkillFiche, queueFilters: QueueFilters, queue: Queue, queueBatchBar: QueueBatchBar, subjectWorklist: SubjectWorklist, questOffers: QuestOffers, debts: Debts, vocabulary: Vocabulary };
 
 const live = {}; // key -> { node, instance }
 
diff --git a/frontend/src/creation/registry.js b/frontend/src/creation/registry.js
index 1e5a294..a5335bd 100644
--- a/frontend/src/creation/registry.js
+++ b/frontend/src/creation/registry.js
@@ -567,12 +567,14 @@ export const CREATION_ISLANDS = Object.freeze({
     origin: 'new',
     createdBy: 'TICKET-0110',
   }),
-  // TICKET-0113 (BRIEF-0113-C, WI1): the attributes of the world -- the
-  // state of the world -- created directly as an island, no legacy predecessor.
-  states: Object.freeze({
-    containerId: 'creation-etats',
-    component: 'States.svelte',
+  // TICKET-0114 (BRIEF-0114-B, T3): the world's vocabulary -- its states
+  // (TICKET-0113's « États » island, now a section of this one), its event
+  // types and its sortes -- created directly as an island, no legacy
+  // predecessor.
+  vocabulary: Object.freeze({
+    containerId: 'creation-vocabulaire',
+    component: 'Vocabulary.svelte',
     origin: 'new',
-    createdBy: 'TICKET-0113',
+    createdBy: 'TICKET-0114',
   }),
 });
diff --git a/frontend/src/creation/tabs.js b/frontend/src/creation/tabs.js
index 6aaf81b..a2af20e 100644
--- a/frontend/src/creation/tabs.js
+++ b/frontend/src/creation/tabs.js
@@ -358,14 +358,16 @@ export const CREATION_TABS = {
     islands: [{ key: 'debts', containerId: 'creation-dettes' }],
     primaryAction: { label: '+ Nouvelle dette', handler: () => triggerPrimaryAction('debts') },
   },
-  etats: {
-    label: 'États',
+  // TICKET-0114 (BRIEF-0114-B, T3): the world's vocabulary in one tab --
+  // its states (TICKET-0113's « États »), its event types, its sortes.
+  vocabulaire: {
+    label: 'Vocabulaire du monde',
     archetype: 'bespoke',
-    containers: ['creation-etats'],
+    containers: ['creation-vocabulaire'],
     loader: null,
     state: { onTabEnter: null, onWorldSwitch: null },
-    islands: [{ key: 'states', containerId: 'creation-etats' }],
-    primaryAction: { label: '+ Nouvel état', handler: () => triggerPrimaryAction('states') },
+    islands: [{ key: 'vocabulary', containerId: 'creation-vocabulaire' }],
+    primaryAction: { label: '+ Nouveau', handler: () => triggerPrimaryAction('vocabulary') },
   },
   subjects: {
     label: 'Sujets',
diff --git a/src/world_engine/cockpit/app.py b/src/world_engine/cockpit/app.py
index dc67fca..4c79b49 100644
--- a/src/world_engine/cockpit/app.py
+++ b/src/world_engine/cockpit/app.py
@@ -59,6 +59,7 @@ from .routes import conditions as _routes_conditions
 from .routes import creator as _routes_creator
 from .routes import day as _routes_day
 from .routes import debts as _routes_debts
+from .routes import event_types as _routes_event_types
 from .routes import link_agent as _routes_link_agent
 from .routes import lore as _routes_lore
 from .routes import lore_mentions as _routes_lore_mentions
@@ -146,6 +147,7 @@ app.include_router(_routes_quests.router)
 app.include_router(_routes_conditions.router)
 app.include_router(_routes_debts.router)
 app.include_router(_routes_attributes.router)
+app.include_router(_routes_event_types.router)
 
 app.mount("/static", _FreshnessAwareStaticFiles(directory=_STATIC_DIR), name="static")
 
diff --git a/src/world_engine/cockpit/routes/event_types.py b/src/world_engine/cockpit/routes/event_types.py
new file mode 100644
index 0000000..fd874c1
--- /dev/null
+++ b/src/world_engine/cockpit/routes/event_types.py
@@ -0,0 +1,246 @@
+"""The event journal's vocabulary routes (TICKET-0114, BRIEF-0114-B;
+decisions B1, C1, D1, T3 and W1 of the conditions series) -- creator CRUD, a
+sanctioned canon-write path:
+
+    GET  /api/event-vocabulary            the active world's event types
+                                          (the retired included), its sortes,
+                                          and what a type may name: entity
+                                          types, domains, scope kinds, levels
+    POST /api/event-types                 define one type
+    PUT  /api/event-types/{id}            save one
+    POST /api/event-types/{id}/status     retire or restore one
+    POST /api/event-sortes                add one sorte
+    PUT  /api/event-sortes/{id}           rename one
+    POST /api/event-sortes/{id}/status    retire or restore one
+
+A name near another type's or sorte's (`event_vocab.near_event_types`,
+`near_sortes`) is not written until the creator confirms it
+(`confirm_near`): the answer is `{"saved": false, "near": [...]}` and she
+opens the existing one or creates anyway -- never « Tuer » twice unseen
+(the WK2 rule of TICKET-0113).
+
+Every rule lives in `writes/event_types.py`; what is shown, in
+`event_vocab.py`. This module parses, maps a refusal to 422, and commits once.
+"""
+
+from __future__ import annotations
+
+from typing import Optional
+
+from fastapi import APIRouter, Depends, HTTPException
+from pydantic import BaseModel, Field
+from sqlmodel import Session, func, select
+
+from ...attributes import world_entity_type_labels
+from ...db import get_session
+from ...event_vocab import (
+    DOMAIN_LABELS_FR,
+    EVENT_FORM,
+    EventTypeView,
+    near_event_types,
+    near_sortes,
+    type_view,
+    world_event_types,
+    world_sortes,
+)
+from ...models import EVENT_DOMAINS, EVENT_SCOPE_KINDS, ConditionNode, Event, EventSorte, EventType
+from ...writes.event_types import (
+    EventTypeSpec,
+    RoleSpec,
+    ScopeSpec,
+    set_event_type_status,
+    set_sorte_status,
+    write_event_type,
+    write_sorte,
+)
+from .. import crud as _crud
+
+router = APIRouter()
+
+# W1: the scope kinds and the levels a scope may give, in French, in order.
+SCOPE_LABELS_FR: dict[str, str] = {
+    "location": "ceux qui passent au lieu de l'événement", "world": "tout le monde",
+    "rencontre": "ceux qui ont rencontré", "faction": "les membres de la faction",
+}
+LEVEL_LABELS_FR: dict[str, str] = {
+    "rumor": "une rumeur", "suspicious": "un soupçon", "partial": "en partie", "knows": "le savent",
+    "fully_understands": "le comprennent pleinement",
+}
+
+
+class RoleBody(BaseModel):
+    name: str
+    entity_types: list[str] = Field(default_factory=list)
+    accepts_sorte: bool = False
+    id: Optional[str] = None
+
+
+class ScopeBody(BaseModel):
+    kind: str
+    role: Optional[str] = None
+    level: str = "knows"
+
+
+class EventTypeBody(BaseModel):
+    name: str
+    domain: str = "other"
+    roles: list[RoleBody] = Field(default_factory=list)
+    counts_quantity: bool = False
+    in_chronicle: bool = True
+    participants_secret: bool = False
+    scopes: list[ScopeBody] = Field(default_factory=list)
+    confirm_near: bool = False
+
+
+class SorteBody(BaseModel):
+    name: str
+    confirm_near: bool = False
+
+
+class StatusBody(BaseModel):
+    status: str
+
+
+def event_type_spec(body: EventTypeBody) -> EventTypeSpec:
+    """The writer's spec of a request body (shared with the interpreter's
+    and the analyzer's proposals, BRIEF-0114-G/H)."""
+    return EventTypeSpec(
+        name=body.name, domain=body.domain,
+        roles=tuple(RoleSpec(r.name, tuple(r.entity_types), r.accepts_sorte, r.id) for r in body.roles),
+        counts_quantity=body.counts_quantity, in_chronicle=body.in_chronicle,
+        participants_secret=body.participants_secret,
+        scopes=tuple(ScopeSpec(s.kind, s.role, s.level) for s in body.scopes),
+    )
+
+
+def _in_condition(db: Session, type_id: str) -> bool:
+    return db.exec(select(ConditionNode.id).where(
+        ConditionNode.form == EVENT_FORM, ConditionNode.target_key == type_id)).first() is not None
+
+
+def type_dict(db: Session, view: EventTypeView) -> dict:
+    """One type as the « Vocabulaire du monde » tab and the journal show it."""
+    names = {r.id: r.name for r in view.roles}
+    events = db.exec(select(func.count()).select_from(Event).where(Event.type_id == view.id)).one()
+    return {
+        "id": view.id, "name": view.name, "domain": view.domain, "domain_label": DOMAIN_LABELS_FR[view.domain],
+        "counts_quantity": view.counts_quantity, "in_chronicle": view.in_chronicle,
+        "participants_secret": view.participants_secret, "status": view.status,
+        "roles": [{"id": r.id, "name": r.name, "entity_types": list(r.entity_types),
+                   "accepts_sorte": r.accepts_sorte, "status": r.status} for r in view.roles],
+        "scopes": [{"kind": s.kind, "role": names.get(s.role_id), "level": s.level} for s in view.scopes],
+        "in_condition": _in_condition(db, view.id), "events": events,
+    }
+
+
+def sorte_dict(sorte: EventSorte) -> dict:
+    return {"id": sorte.id, "name": sorte.name, "status": sorte.status}
+
+
+def _near(found) -> list[dict]:
+    return [{"id": n.id, "name": n.name, "score": n.score} for n in found]
+
+
+@router.get("/api/event-vocabulary")
+def event_vocabulary(db: Session = Depends(get_session)) -> dict:
+    world_id = _crud._world_id(db)
+    return {
+        "types": [type_dict(db, v) for v in world_event_types(db, world_id, include_retired=True)],
+        "sortes": [sorte_dict(s) for s in world_sortes(db, world_id, include_retired=True)],
+        "entity_types": world_entity_type_labels(db, world_id),
+        "domains": [{"value": d, "label": DOMAIN_LABELS_FR[d]} for d in EVENT_DOMAINS],
+        "scope_kinds": [{"value": k, "label": SCOPE_LABELS_FR[k]} for k in EVENT_SCOPE_KINDS],
+        "levels": [{"value": v, "label": label} for v, label in LEVEL_LABELS_FR.items()],
+    }
+
+
+def _save_type(body: EventTypeBody, type_id: Optional[str], db: Session) -> dict:
+    world_id = _crud._world_id(db)
+    if not body.confirm_near:
+        near = _near(near_event_types(db, world_id, body.name, exclude_id=type_id))
+        renamed = type_id is None or db.get(EventType, type_id).name != body.name
+        if near and renamed:
+            return {"saved": False, "near": near}
+    try:
+        row = write_event_type(db, world_id=world_id, spec=event_type_spec(body), type_id=type_id)
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=422, detail=str(exc)) from exc
+    db.commit()
+    return {"saved": True, "type": type_dict(db, type_view(db, row.id))}
+
+
+def _type(db: Session, type_id: str) -> EventType:
+    row = db.get(EventType, type_id)
+    if row is None or row.world_id != _crud._world_id(db):
+        raise HTTPException(status_code=404, detail=f"event type {type_id!r} not found")
+    return row
+
+
+@router.post("/api/event-types")
+def create_event_type(body: EventTypeBody, db: Session = Depends(get_session)) -> dict:
+    return _save_type(body, None, db)
+
+
+@router.put("/api/event-types/{type_id}")
+def save_event_type(type_id: str, body: EventTypeBody, db: Session = Depends(get_session)) -> dict:
+    _type(db, type_id)
+    return _save_type(body, type_id, db)
+
+
+@router.post("/api/event-types/{type_id}/status")
+def event_type_status(type_id: str, body: StatusBody, db: Session = Depends(get_session)) -> dict:
+    row = _type(db, type_id)
+    try:
+        set_event_type_status(db, world_id=row.world_id, type_id=type_id, status=body.status)
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=422, detail=str(exc)) from exc
+    db.commit()
+    return type_dict(db, type_view(db, type_id))
+
+
+def _save_sorte(body: SorteBody, sorte_id: Optional[str], db: Session) -> dict:
+    world_id = _crud._world_id(db)
+    if not body.confirm_near:
+        near = _near(near_sortes(db, world_id, body.name, exclude_id=sorte_id))
+        renamed = sorte_id is None or db.get(EventSorte, sorte_id).name != body.name
+        if near and renamed:
+            return {"saved": False, "near": near}
+    try:
+        row = write_sorte(db, world_id=world_id, name=body.name, sorte_id=sorte_id)
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=422, detail=str(exc)) from exc
+    db.commit()
+    return {"saved": True, "sorte": sorte_dict(row)}
+
+
+def _sorte(db: Session, sorte_id: str) -> EventSorte:
+    row = db.get(EventSorte, sorte_id)
+    if row is None or row.world_id != _crud._world_id(db):
+        raise HTTPException(status_code=404, detail=f"sorte {sorte_id!r} not found")
+    return row
+
+
+@router.post("/api/event-sortes")
+def create_sorte(body: SorteBody, db: Session = Depends(get_session)) -> dict:
+    return _save_sorte(body, None, db)
+
+
+@router.put("/api/event-sortes/{sorte_id}")
+def save_sorte(sorte_id: str, body: SorteBody, db: Session = Depends(get_session)) -> dict:
+    _sorte(db, sorte_id)
+    return _save_sorte(body, sorte_id, db)
+
+
+@router.post("/api/event-sortes/{sorte_id}/status")
+def sorte_status(sorte_id: str, body: StatusBody, db: Session = Depends(get_session)) -> dict:
+    row = _sorte(db, sorte_id)
+    try:
+        set_sorte_status(db, world_id=row.world_id, sorte_id=sorte_id, status=body.status)
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=422, detail=str(exc)) from exc
+    db.commit()
+    return sorte_dict(db.get(EventSorte, sorte_id))
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 7506215..86cec9a 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19281,6 +19281,31 @@ of BRIEF-0114-D reads them. v2.24 moves `schema_meta` to v2.24 only: v2.25
 universal roles), D2 (an entity standing for a species: it pollutes the
 NPC lists and `name_index`), D3 (named entities only), W2 (three scopes).
 
+## THE WORLD'S VOCABULARY LIVES IN ONE CRÉATION TAB (TICKET-0114) -- STATES, EVENT TYPES AND SORTES SIDE BY SIDE, A NEAR NAME PICKED BEFORE IT IS WRITTEN (BRIEF-0114-b, no schema change)
+
+**T3.** What a world can say grows by data, so the creator keeps it in one
+place: the « Vocabulaire du monde » tab (`tabs.js` `vocabulaire`, the
+`vocabulary` island, `Vocabulary.svelte`) shows one section at a time --
+its states (TICKET-0113's `States.svelte`, unchanged, no longer an island of
+its own), its event types (`EventTypes.svelte`, one type edited through
+`EventTypeForm.svelte`) and its sortes (`Sortes.svelte`). The tab's
+« + Nouveau » goes to the section shown. The « Événements » tab keeps the
+journal itself (BRIEF-0114-C).
+
+**The routes** (`cockpit/routes/event_types.py`, creator CRUD):
+`GET /api/event-vocabulary` and the type and sorte writes, each refusal a
+422 and one commit. A name near another type's or sorte's answers
+`saved: false` with the near ones until the creator confirms
+(`confirm_near`) -- the WK2 rule of TICKET-0113: she opens the existing one
+or creates anyway, the tool never picks. A type or a sorte is retired or
+restored, never deleted. `event_type_spec` / `typeDraft` / `typeBody` are
+shared with the journal and with the interpreter's and analyzer's proposal
+cards.
+
+**Rejected.** T1 (a tab of its own for event types: the bar grows, the
+sortes need another), T2 (types inside the « Événements » tab: the
+vocabulary split from the states it sits beside).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/attributes.py b/tooling/verify/checks/attributes.py
index 651ed03..4140b37 100644
--- a/tooling/verify/checks/attributes.py
+++ b/tooling/verify/checks/attributes.py
@@ -69,10 +69,9 @@ AC2 -- nearness (fixture). `near_attributes` finds « Maudite » for
    vitale », never an attribute it excludes, nothing for « Porte rouge »;
    `lore_resolve.near_in_surfaces` and `near_attributes` both score through
    `near_ratio` (static).
-AC3 -- the Création surfaces (static). `tabs.js`'s `etats` entry mounts
-   the `states` island in `creation-etats` and routes « + Nouvel état »
-   through `triggerPrimaryAction('states')`; `registry.js` declares
-   `states` as origin 'new', created by TICKET-0113; `States.svelte` exports
+AC3 -- the Création surfaces (static). `Vocabulary.svelte` renders the
+   states section (since TICKET-0114, T3: its tab and island are
+   `event_journal.py` EB2's); `States.svelte` exports
    `primaryAction` and renders `<AttributeDefinitionForm`;
    `attributes.svelte.js` exports `definitionDraft` and `definitionBody`
    and sends `confirm_near`; `Sheet.svelte` renders `<StatesPanel` for a
@@ -663,16 +662,11 @@ def check_ac3() -> None:
             return ""
         return path.read_text(encoding="utf-8")
 
-    tabs = read("tabs.js")
-    entry = re.search(r"\n  etats: \{(.*?)\n  \},", tabs, re.S)
-    body = entry.group(1) if entry else ""
-    for needle in ("{ key: 'states', containerId: 'creation-etats' }", "triggerPrimaryAction('states')"):
-        if needle not in body:
-            fail(f"AC3: tabs.js's etats entry lacks {needle}")
-    registry = read("registry.js")
-    island = re.search(r"\n  states: Object\.freeze\(\{(.*?)\}\),", registry, re.S)
-    if not island or "origin: 'new'" not in island.group(1) or "createdBy: 'TICKET-0113'" not in island.group(1):
-        fail("AC3: registry.js does not declare the states island as new, TICKET-0113")
+    # Since TICKET-0114 (BRIEF-0114-B, T3) the states are a section of the
+    # « Vocabulaire du monde » island, whose own entry `event_journal.py`
+    # (EB2) holds; here: the island renders States.svelte.
+    if "<States bind:this={refs.states}" not in read("Vocabulary.svelte"):
+        fail("AC3: Vocabulary.svelte does not render the states section")
     states = read("States.svelte")
     for needle in ("export function primaryAction", "<AttributeDefinitionForm"):
         if needle not in states:
diff --git a/tooling/verify/checks/event_journal.py b/tooling/verify/checks/event_journal.py
index fbb5f00..b3e9c09 100644
--- a/tooling/verify/checks/event_journal.py
+++ b/tooling/verify/checks/event_journal.py
@@ -51,6 +51,29 @@ EA6 -- migration `scripts/migrate_v2_24_event_journal.py`, on a v2.23
    `schema_meta` to v2.24; a second run writes nothing.
 EA7 -- the reader writes nothing (static, AST). `event_vocab.py` calls no
    `add`, `commit`, `delete`, `execute` or `flush`.
+EB1 -- the routes (BRIEF-0114-B, route functions on the EA world made
+   active). `event_vocabulary` lists the types (the retired included, each
+   with `in_condition` and its count of events), the sortes, the world's
+   entity types, the seven domains, the four scope kinds and five levels
+   (never `unaware`). A new type named near another (« Tuers » beside
+   « Tuer ») answers `saved: false` with the near one and writes nothing;
+   `confirm_near` writes it; saving a type under its own name asks nothing;
+   a refused type answers 422 and writes nothing; a type is retired then
+   restored. A sorte near another (« Loups ») asks, `confirm_near` writes
+   it, and an unknown sorte answers 404.
+EB2 -- the Création surfaces (static). `tabs.js` has no `etats` entry; its
+   `vocabulaire` entry mounts the `vocabulary` island in
+   `creation-vocabulaire` and routes « + Nouveau » through
+   `triggerPrimaryAction('vocabulary')`; `registry.js` declares
+   `vocabulary` as origin 'new', created by TICKET-0114, and no `states`
+   island; `mount.js` maps `vocabulary` to `Vocabulary`; `creation.css`
+   sizes `#creation-vocabulaire`; `Vocabulary.svelte` exports
+   `primaryAction` and renders `<States`, `<EventTypes` and `<Sortes`;
+   `EventTypes.svelte` and `Sortes.svelte` export `primaryAction`;
+   `EventTypes.svelte` renders `<EventTypeForm`, which offers the three
+   flags, a role's entity types and its sorte, and the scopes;
+   `eventVocab.svelte.js` exports `typeDraft` and `typeBody` and sends
+   `confirm_near`.
 
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
@@ -577,6 +600,112 @@ def check_ea7() -> None:
             fail(f"EA7: event_vocab.py calls .{call.func.attr} on line {call.lineno}")
 
 
+# --- EB1 -------------------------------------------------------------------------
+
+def check_eb1(engine, ids: dict) -> None:
+    from fastapi import HTTPException
+    from sqlmodel import Session, func, select
+
+    from world_engine.cockpit.routes import event_types as routes
+    from world_engine.models import EventSorte, EventType, World
+
+    def count(db, model) -> int:
+        return db.exec(select(func.count()).select_from(model)).one()
+
+    with Session(engine) as db:
+        db.get(World, ids["world"]).is_active = True
+        db.commit()
+        listed = routes.event_vocabulary(db)
+        if not listed["types"] or not all("in_condition" in t and "events" in t for t in listed["types"]):
+            fail(f"EB1: event_vocabulary lists types {listed['types'][:1]}")
+        shape = (len(listed["domains"]), len(listed["scope_kinds"]), [l["value"] for l in listed["levels"]])
+        if shape != (7, 4, ["rumor", "suspicious", "partial", "knows", "fully_understands"]) \
+                or not listed["entity_types"]:
+            fail(f"EB1: event_vocabulary's lists are {shape}")
+        before = count(db, EventType)
+        body = routes.EventTypeBody(name="Tuers", roles=[routes.RoleBody(name="x", entity_types=["character"])])
+        asked = routes.create_event_type(body, db)
+        if asked.get("saved") is not False or "Tuer" not in [n["name"] for n in asked.get("near", [])] \
+                or count(db, EventType) != before:
+            fail(f"EB1: a near type name answered {asked}")
+        body.confirm_near = True
+        made = routes.create_event_type(body, db)
+        if made.get("saved") is not True or count(db, EventType) != before + 1:
+            fail(f"EB1: confirm_near answered {made}")
+        type_id = made["type"]["id"]
+        roles = [routes.RoleBody(name="x", entity_types=["character"], id=made["type"]["roles"][0]["id"])]
+        same = routes.save_event_type(type_id, routes.EventTypeBody(name="Tuers", roles=roles), db)
+        if same.get("saved") is not True:
+            fail(f"EB1: saving a type under its own name answered {same}")
+        try:
+            routes.create_event_type(routes.EventTypeBody(name="Vide", confirm_near=True), db)
+            fail("EB1: a type with no role was accepted")
+        except HTTPException as exc:
+            if exc.status_code != 422 or count(db, EventType) != before + 1:
+                fail(f"EB1: a type with no role answered {exc.status_code}")
+        retired = routes.event_type_status(type_id, routes.StatusBody(status="retired"), db)["status"]
+        restored = routes.event_type_status(type_id, routes.StatusBody(status="active"), db)["status"]
+        if (retired, restored) != ("retired", "active"):
+            fail(f"EB1: a type was {retired} then {restored}")
+        sortes = count(db, EventSorte)
+        asked = routes.create_sorte(routes.SorteBody(name="Loups"), db)
+        if asked.get("saved") is not False or count(db, EventSorte) != sortes:
+            fail(f"EB1: a near sorte answered {asked}")
+        if routes.create_sorte(routes.SorteBody(name="Loups", confirm_near=True), db).get("saved") is not True:
+            fail("EB1: confirm_near did not write the sorte")
+        try:
+            routes.save_sorte("nope", routes.SorteBody(name="x"), db)
+            fail("EB1: an unknown sorte was saved")
+        except HTTPException as exc:
+            if exc.status_code != 404:
+                fail(f"EB1: an unknown sorte answered {exc.status_code}")
+
+
+# --- EB2 -------------------------------------------------------------------------
+
+def check_eb2() -> None:
+    front = ROOT / "frontend" / "src" / "creation"
+
+    def read(path: pathlib.Path) -> str:
+        if not path.exists():
+            fail(f"EB2: {path.name} is missing")
+            return ""
+        return path.read_text(encoding="utf-8")
+
+    tabs = read(front / "tabs.js")
+    if re.search(r"\n  etats: \{", tabs):
+        fail("EB2: tabs.js still has an etats entry")
+    entry = re.search(r"\n  vocabulaire: \{(.*?)\n  \},", tabs, re.S)
+    body = entry.group(1) if entry else ""
+    for needle in ("{ key: 'vocabulary', containerId: 'creation-vocabulaire' }",
+                   "triggerPrimaryAction('vocabulary')", "label: 'Vocabulaire du monde'"):
+        if needle not in body:
+            fail(f"EB2: tabs.js's vocabulaire entry lacks {needle}")
+    registry = read(front / "registry.js")
+    island = re.search(r"\n  vocabulary: Object\.freeze\(\{(.*?)\}\),", registry, re.S)
+    if not island or "origin: 'new'" not in island.group(1) or "createdBy: 'TICKET-0114'" not in island.group(1):
+        fail("EB2: registry.js does not declare the vocabulary island as new, TICKET-0114")
+    if re.search(r"\n  states: Object\.freeze", registry):
+        fail("EB2: registry.js still declares a states island")
+    if "vocabulary: Vocabulary" not in read(front / "mount.js"):
+        fail("EB2: mount.js does not map vocabulary to Vocabulary")
+    if "#creation-vocabulaire" not in read(ROOT / "frontend" / "public" / "creation.css"):
+        fail("EB2: creation.css does not size #creation-vocabulaire")
+    needles = {
+        "Vocabulary.svelte": ("export function primaryAction", "<States", "<EventTypes", "<Sortes"),
+        "EventTypes.svelte": ("export function primaryAction", "<EventTypeForm"),
+        "Sortes.svelte": ("export function primaryAction",),
+        "EventTypeForm.svelte": ("draft.counts_quantity", "draft.in_chronicle", "draft.participants_secret",
+                                 "role.entity_types", "role.accepts_sorte", "draft.scopes"),
+        "eventVocab.svelte.js": ("export function typeDraft", "export function typeBody", "confirm_near"),
+    }
+    for name, wanted in needles.items():
+        text = read(front / name)
+        for needle in wanted:
+            if needle not in text:
+                fail(f"EB2: {name} lacks {needle}")
+
+
 def main() -> int:
     _fresh_db()
     from world_engine.db import create_db_and_tables, engine
@@ -591,7 +720,7 @@ def main() -> int:
     rules = (
         ("EA1", check_ea1), ("EA2", ea2), ("EA3", lambda: check_ea3(engine, ids, state["tuer"])),
         ("EA4", lambda: check_ea4(engine, ids)), ("EA5", lambda: check_ea5(engine, ids)),
-        ("EA6", check_ea6), ("EA7", check_ea7),
+        ("EA6", check_ea6), ("EA7", check_ea7), ("EB1", lambda: check_eb1(engine, ids)), ("EB2", check_eb2),
     )
     for name, rule in rules:
         try:
@@ -604,7 +733,8 @@ def main() -> int:
         return 1
     print("PASS: event_journal -- v2.24 keeps a world's event types with their roles, the entity types each "
           "accepts, who learns them, and its sortes; nothing in use is taken away; every earlier event is "
-          "typed by its category, its links become participants and it gets its fact")
+          "typed by its category, its links become participants and it gets its fact; Création keeps the "
+          "vocabulary in one tab and asks before a near name")
     return 0
 
 
````

2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
4. Run the checks below, then the full corpus.

## Scope OUT

- The journal sheet (C), the condition editor's event row (E), the interpreter's card (G).
- Renaming the `States.svelte` component or its routes (`routes/attributes.py`): it is mounted inside the new tab as it is.
- Every later brief of this lot: BRIEF-0114-C, BRIEF-0114-D, BRIEF-0114-E, BRIEF-0114-F, BRIEF-0114-G, BRIEF-0114-H.

## Invariants to defend

INV-49, INV-50, INV-53, INV-54 (`page_contract.py`, `creation_island.py`, `creation_tab_switch.py`, `creation_container_sizing.py`): the tab is a `CREATION_TABS` entry, its island declared and mounted through `mount.js` alone, its container sized. INV-55 (`effect_self_write.py`).

## Decision rights

STOP:
- A Création check (`page_contract.py`, `creation_island.py`, `creation_container_sizing.py`) demands a shape the diff does not give.
- A Mini-RECON anchor that does not hold.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `npm run build` names a different asset hash than the prototype's: commit what it builds (`frontend_build_fresh.py` judges the manifest, not the name).
- A check other than this brief's own fails on a line count or a docstring count this diff moved (`file_map.py`, `decisions_index.py`): regenerate `FILE_MAP.md` / `DECISIONS_INDEX.md` and rerun.

REPORT-ONLY:
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.
- Log lines a check prints before its verdict (`[skip] …`, `[overhearing] …`): the analyzer's own logging.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/`.
- `python tooling/verify/checks/event_journal.py` -> `PASS`.
- `python tooling/verify/checks/attributes.py` -> `PASS`.
- `python tooling/verify/checks/page_contract.py` -> `PASS`.
- `python tooling/verify/checks/creation_island.py` -> `PASS`.
- `python tooling/verify/checks/creation_container_sizing.py` -> `PASS`.
- `python tooling/verify/checks/creation_tab_switch.py` -> `PASS`.
- `python tooling/verify/checks/frontend_build_fresh.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (151 on the prototype).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **EB1** -- `cockpit/routes/event_types.py` `_save_type`: `if near and renamed:` -> `if False:`
  - **EB2** -- `frontend/src/creation/mount.js`: drop `, vocabulary: Vocabulary` from `COMPONENTS`
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated.
