<!-- slug: states-ui -->
# BRIEF 0113-C — "The creator defines the states of her world in Création -- an « États » tab, a panel on every sheet, a near name confirmed before it is written"

Lot: LOT-0113-world-state.md (authoritative on conflict)
Depends on: BRIEF-0113-B (C-02, C-03, C-04)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0113-B's commit).

- `frontend/src/creation/Creation.svelte:253` -> `<div id="creation-quetes" style:display={containerVisible('creation-quetes') ? '' : 'none'}></div>`
- `frontend/src/creation/tabs.js:358` -> `islands: [{ key: 'debts', containerId: 'creation-dettes' }],`
- `frontend/src/creation/Sheet.svelte:94` -> `import PricingEditor from './PricingEditor.svelte';`
- `frontend/public/creation.css:311` -> `#creation-subjects    { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }`
- `src/world_engine/lore_resolve.py:178` -> `class NearCandidate:`
- `src/world_engine/lore_resolve.py:186` -> `def near_in_surfaces(surface_form: str, name_surfaces: Sequence[NameSurface], *,`
- `src/world_engine/cockpit/app.py:143` -> `app.include_router(_routes_lore_write.router)`
- No `src/world_engine/cockpit/routes/attributes.py`, no `frontend/src/creation/States.svelte`, `StatesPanel.svelte`, `AttributeDefinitionForm.svelte`, `attributes.svelte.js`; no `etats` key in `CREATION_TABS`, no `states` key in `CREATION_ISLANDS`.

## Facts carried

### R-03 — a change is `correction` or `changement` since TICKET-0105 [M]
Opened: `src/world_engine/writes/facts.py:38` (the docstring's two
meanings), `:56` (`FACT_CHANGE_KINDS = ("correction", "changement")`),
`:61-62` (refusal); `src/world_engine/cockpit/crud/facets.py:45`
(`kind: Literal["correction", "changement"]`, required).
Consequence: `ATTRIBUTE_CHANGE_KINDS` is the same pair in the same order
(AA1), required on every value write, never defaulted -- the panel
preselects neither (AC3).

### R-10 — one nearness rule [M]
Opened: `src/world_engine/lore_resolve.py:50-51` (`NEAR_RATIO = 0.8`,
`NEAR_LIMIT`), `:73` (`normalize_surface`), `:178` (`NearCandidate`),
`:186-` (`near_in_surfaces`: `difflib` ratio or a shared 3+ token, score
rounded half up -- TICKET-0094's Near table).
Consequence: C extracts the rule unchanged as `near_ratio` / `near_score`
(`near_in_surfaces` reads them); `attributes.near_attributes` scores names
with it. « maudite » beside « Maudit » scores 92 [M]. Names are compared
for identity through `normalize_surface` (case and accents aside).

### R-13 — Création's registries [M]
Opened: `frontend/src/creation/tabs.js:198` (`CREATION_TABS`), `:352-358`
(`dettes`, the last entry); `frontend/src/creation/registry.js:48`
(`CREATION_ISLANDS`, `origin` `migration` / `new`); `frontend/src/creation/mount.js:27`;
`frontend/src/creation/Creation.svelte:253` (one container per tab);
`frontend/public/creation.css:311` (container sizing);
`frontend/src/creation/Sheet.svelte:94` (child editors imported).
`.claude/rules/frontend.md` INV-49, INV-50, INV-54, INV-55.
Consequence: États is one `CREATION_TABS` entry and one island of origin
`new`, its container sized in `creation.css`; the sheet's panel is a child
of `Sheet.svelte`, never an island.

## Contracts

### C-02 — `attributes` (reads)
Produced by: BRIEF-0113-A (C adds the last four)   Consumed by: B, C, D, E
`ATTRIBUTE_FORM = "attribute"`; `BUILTIN_ENTITY_TYPES`; `SYSTEM_ATTRIBUTES`
(`sys:vital_status` on characters, `sys:status` on every entity,
`sys:magic_status` on locations; each `(stored value, French label)`).
`AttributeView(key, name, kind, system, hidden, status, holder_types
(None: every type), value_types, choices ((key, label), ...), default)`;
`StateValue(raw, label, is_default)`.
`attribute_view(db, world_id, key) -> Optional[AttributeView]`;
`view_of(db, key)` (any world, for a stored leaf -- B);
`world_attributes(db, world_id, include_retired=False)` (system first,
then the world's by name); `applies_to(view, entity_type) -> bool`;
`value_label(db, view, raw) -> str`; `current_value(db, view, entity) ->
StateValue` (the default when the entity holds none; writes nothing).
C: `world_entity_type_labels(db, world_id) -> [{type, label}]`;
`near_attributes(db, world_id, name, exclude_key=None) ->
tuple[NearAttribute(key, name, system, score)]` (retired included, best
first); `entity_states(db, world_id, entity) -> [{key, name, kind, system,
hidden, raw, label, is_default, choices, value_types, history}]` (history
newest first, `[]` for a system attribute).

### C-03 — `writes.attributes` (the one writer)
Produced by: BRIEF-0113-A   Consumed by: C (routes), E (proposals, save)
`ChoiceSpec(label, id=None)`; `DefinitionSpec(name, kind, holder_types,
value_types=(), choices=(), default=None, is_hidden=False)` -- `default` a
choice's LABEL, an integer, or None.
`clean_definition(db, world_id, spec, definition_id=None) ->
DefinitionSpec`: writes nothing; case b-1.
`write_attribute_definition(db, *, world_id, spec, definition_id=None) ->
AttributeDefinition` (flushed; types replaced whole; a dropped label
retired, a named retired one revived).
`set_attribute_status(db, *, world_id, definition_id, status)`: retiring
refused while a leaf of form `attribute` names it.
`write_attribute_value(db, *, world_id, definition_id, entity_id, value,
kind, changed_by) -> Optional[AttributeChange]`: `value` a choice id, an
integer or an entity id (None: none); unchanged -> None, nothing written;
`before` is the stored value or the default.
Error cases: `ValueError` naming the problem; none commits; a system key is
never accepted (no row holds it).

### C-06 — the routes of the state of the world
Produced by: BRIEF-0113-C   Consumed by: the frontend (C), E (`UnsavedBody`, `definition_spec`)
`GET /api/attributes` -> `{attributes: [attribute_dict], entity_types:
[{type, label}]}` (retired included). `attribute_dict`: `attribute_choice`'s
keys plus `status`, `default`, `in_condition`.
`POST /api/attributes`, `PUT /api/attributes/{id}` body `DefinitionBody
{name, kind, holder_types, value_types, choices: [{label, id?}], default,
is_hidden, confirm_near}` -> `{saved: true, attribute}` or `{saved: false,
near: [{key, name, system, score}]}`.
`POST /api/attributes/{id}/status` body `{status}` -> `attribute_dict`.
`GET /api/entities/{id}/states` -> `entity_states`;
`PUT /api/entities/{id}/states/{key}` body `ValueBody {value, kind}` ->
`entity_states`. `definition_spec(body) -> DefinitionSpec`;
E adds `UnsavedBody {ref, definition: DefinitionBody}`. Statuses: b-4.

### C-07 — the nearness rule
Produced by: BRIEF-0113-C   Consumed by: C, E
`lore_resolve.near_ratio(target, text) -> Optional[float]` (`target`
already normalized; ratio >= `NEAR_RATIO` or a shared 3+ token);
`near_score(ratio) -> int` (half up). `near_in_surfaces` unchanged in
behaviour (TICKET-0094's Near table still its reference).

## Context

The store (A) and the form (B) exist; the creator still has no hands on them. Création › États lists the world's attributes, the three system ones first, and defines, saves, retires or restores one through one form -- the same form the interpreter's card will reuse (E). Every saved sheet gets an « États » panel: each attribute that applies, its value or « (défaut) », its history; a change asks « correction » or « changement », neither preselected. A new name near an existing one is not written until she confirms: never « Maudit » and « maudite » unseen.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `lore_resolve.py`: `near_ratio` and `near_score` extracted from `near_in_surfaces`, unchanged in behaviour (C-07);
   - `attributes.py`: `BUILTIN_TYPE_LABELS_FR`, `world_entity_type_labels`, `NearAttribute`, `near_attributes`, `entity_states` (C-02);
   - creates `cockpit/routes/attributes.py` (C-06, b-4) and mounts it in `cockpit/app.py`;
   - frontend: creates `attributes.svelte.js`, `AttributeDefinitionForm.svelte`, `States.svelte` (an island, origin `new`), `StatesPanel.svelte` (a child of `Sheet.svelte`); `tabs.js` (`etats`), `registry.js` (`states`), `mount.js`, `Creation.svelte` (`creation-etats`), `frontend/public/creation.css` (its sizing, INV-54), `Sheet.svelte` (the panel for a saved entity);
   - adds AC1-AC3 to check `attributes.py`;
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - frontend/public/creation.css
   - frontend/src/creation/AttributeDefinitionForm.svelte
   - frontend/src/creation/Creation.svelte
   - frontend/src/creation/Sheet.svelte
   - frontend/src/creation/States.svelte
   - frontend/src/creation/StatesPanel.svelte
   - frontend/src/creation/attributes.svelte.js
   - frontend/src/creation/mount.js
   - frontend/src/creation/registry.js
   - frontend/src/creation/tabs.js
   - src/world_engine/attributes.py
   - src/world_engine/cockpit/app.py
   - src/world_engine/cockpit/routes/attributes.py
   - src/world_engine/lore_resolve.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/attributes.py

````diff
diff --git a/frontend/public/creation.css b/frontend/public/creation.css
index 30e1fe4..5056a20 100644
--- a/frontend/public/creation.css
+++ b/frontend/public/creation.css
@@ -311,6 +311,7 @@ input.notes::placeholder { color: var(--muted); }
 #creation-subjects    { flex: 1; min-height: 0; display: flex; flex-direction: column; overflow: hidden; }
 #creation-quetes      { flex: 1; min-height: 0; overflow: auto; }
 #creation-dettes      { flex: 1; min-height: 0; overflow: auto; }
+#creation-etats       { flex: 1; min-height: 0; overflow: auto; }
 
 /* ── Région review tree (BRIEF-36) ───────────────────────────────────────── */
 .review-node   { border: 1px solid var(--border); border-radius: 6px; padding: 8px 10px; margin: 6px 0; }
diff --git a/frontend/src/creation/AttributeDefinitionForm.svelte b/frontend/src/creation/AttributeDefinitionForm.svelte
new file mode 100644
index 0000000..9a8b64b
--- /dev/null
+++ b/frontend/src/creation/AttributeDefinitionForm.svelte
@@ -0,0 +1,83 @@
+<script>
+  /* TICKET-0113 (BRIEF-0113-C, WA3, WB2, WC1, WH1). One attribute
+     definition as the creator edits it: its name, its kind (a choice among
+     labels, an integer, another entity), the entity types it applies to,
+     for an entity the types its value may name, its labels and default, and
+     whether it is hidden from the player (off by default). `draft` is a
+     `definitionDraft` owned by the caller -- the « États » island, or the
+     interpreter's proposal card (BRIEF-0113-E); `types` the world's
+     `{type, label}` list. A kind is fixed once the attribute is in use: the
+     server refuses the change (WJ2). */
+  let { draft, types } = $props();
+  const group = 'attr-default-' + Math.random().toString(36).slice(2);
+
+  function toggle(list, type) {
+    const at = list.indexOf(type);
+    if (at >= 0) list.splice(at, 1);
+    else list.push(type);
+  }
+
+  function removeChoice(k) {
+    const [gone] = draft.choices.splice(k, 1);
+    if (gone && gone.label === draft.defaultLabel) draft.defaultLabel = draft.choices[0]?.label || '';
+  }
+</script>
+
+<div class="attr-form">
+  <label>Nom <input type="text" bind:value={draft.name} placeholder="Maudit, Ouvert, Occupé par…"></label>
+  <label>Sorte
+    <select bind:value={draft.kind}>
+      <option value="choice">Un choix parmi des libellés</option>
+      <option value="integer">Un nombre entier</option>
+      <option value="entity">Une autre entité</option>
+    </select>
+  </label>
+  <div class="attr-types">
+    <span>S'applique à</span>
+    {#each types as t (t.type)}
+      <label class="attr-check"><input type="checkbox" checked={draft.holder_types.includes(t.type)}
+             onchange={() => toggle(draft.holder_types, t.type)}> {t.label}</label>
+    {/each}
+  </div>
+  {#if draft.kind === 'entity'}
+    <div class="attr-types">
+      <span>Peut nommer</span>
+      {#each types as t (t.type)}
+        <label class="attr-check"><input type="checkbox" checked={draft.value_types.includes(t.type)}
+               onchange={() => toggle(draft.value_types, t.type)}> {t.label}</label>
+      {/each}
+    </div>
+    <div class="attr-hint">Par défaut : aucune.</div>
+  {:else if draft.kind === 'integer'}
+    <label>Valeur par défaut <input type="number" bind:value={draft.defaultInteger} style="width:90px"></label>
+  {:else}
+    <div class="attr-choices">
+      <span>Libellés (le défaut est coché)</span>
+      {#each draft.choices as c, k (k)}
+        <div class="attr-choice">
+          <input type="radio" name={group} checked={c.label === draft.defaultLabel}
+                 onchange={() => (draft.defaultLabel = c.label)} title="Valeur par défaut">
+          <input type="text" value={c.label} oninput={(e) => {
+            if (draft.defaultLabel === c.label) draft.defaultLabel = e.target.value;
+            c.label = e.target.value;
+          }}>
+          <button class="btn-icon" title="Retirer" onclick={() => removeChoice(k)}>✕</button>
+        </div>
+      {/each}
+      <button onclick={() => draft.choices.push({ id: null, label: '' })}>+ libellé</button>
+    </div>
+  {/if}
+  <label class="attr-check"><input type="checkbox" bind:checked={draft.is_hidden}>
+    Caché au joueur (une condition sur cet état ne le montre jamais)</label>
+</div>
+
+<style>
+  .attr-form label { display: block; margin: 4px 0; }
+  .attr-form input[type="text"] { width: 100%; box-sizing: border-box; }
+  .attr-types, .attr-choices { margin: 6px 0; }
+  .attr-types > span, .attr-choices > span { display: block; font-size: 12px; color: var(--muted); }
+  .attr-check { display: inline-flex !important; gap: 4px; align-items: center; margin-right: 10px !important; }
+  .attr-choice { display: flex; gap: 6px; align-items: center; margin: 2px 0; }
+  .attr-choice input[type="text"] { flex: 1; }
+  .attr-hint { font-size: 12px; color: var(--muted); }
+</style>
diff --git a/frontend/src/creation/Creation.svelte b/frontend/src/creation/Creation.svelte
index b974531..81fa26a 100644
--- a/frontend/src/creation/Creation.svelte
+++ b/frontend/src/creation/Creation.svelte
@@ -253,6 +253,8 @@
   <div id="creation-quetes" style:display={containerVisible('creation-quetes') ? '' : 'none'}></div>
   <!-- ── Dettes sub-tab -- Svelte island (TICKET-0110): empty by construction ── -->
   <div id="creation-dettes" style:display={containerVisible('creation-dettes') ? '' : 'none'}></div>
+  <!-- ── États sub-tab -- Svelte island (TICKET-0113): empty by construction ── -->
+  <div id="creation-etats" style:display={containerVisible('creation-etats') ? '' : 'none'}></div>
   <div id="creation-subjects" style:display={containerVisible('creation-subjects') ? '' : 'none'}></div>
 
   <!-- ── Review Queue sub-tab -- Svelte island: empty by construction ── -->
diff --git a/frontend/src/creation/Sheet.svelte b/frontend/src/creation/Sheet.svelte
index 1d479ba..b2f8b87 100644
--- a/frontend/src/creation/Sheet.svelte
+++ b/frontend/src/creation/Sheet.svelte
@@ -94,6 +94,7 @@
   import PricingEditor from './PricingEditor.svelte';
   import LedgerPanel from './LedgerPanel.svelte';
   import ItemsPanel from './ItemsPanel.svelte';
+  import StatesPanel from './StatesPanel.svelte';
   import { resetPendingDrafts, knowledgeForCreate, goalsForCreate, carrureForCreate } from './pendingDrafts.svelte.js';
   import PendingKnowledgeEditor from './PendingKnowledgeEditor.svelte';
   import PendingGoalsEditor from './PendingGoalsEditor.svelte';
@@ -821,6 +822,12 @@
         </div>
       {/if}
 
+      {#if !isNew}
+        <div class="field-section"><div class="field-section-title">États</div>
+          <div id="author-states"><StatesPanel entityId={detail.id} /></div>
+        </div>
+      {/if}
+
       {#if !isNew && type === 'character'}
         <div class="field-section"><div class="field-section-title">Appartenances</div>
           <MembershipsPanel entityId={detail.id} {legacyDoc} />
diff --git a/frontend/src/creation/States.svelte b/frontend/src/creation/States.svelte
new file mode 100644
index 0000000..200dc66
--- /dev/null
+++ b/frontend/src/creation/States.svelte
@@ -0,0 +1,125 @@
+<script>
+  /* TICKET-0113 (BRIEF-0113-C, WI1, WJ2, WK2). The « États » island: the
+     attributes of the world -- the system ones first, read where they live
+     and never edited here -- and one definition written or saved through
+     AttributeDefinitionForm. A name near another attribute's is not saved
+     until the creator picks: open the existing one, or create anyway. A
+     definition is retired (refused while a condition names it) or
+     restored, never deleted. Its CREATION_ISLANDS entry declares origin
+     'new'. State and requests live in attributes.svelte.js. */
+  import { serverState } from '../lib/serverState.svelte.js';
+  import AttributeDefinitionForm from './AttributeDefinitionForm.svelte';
+  import {
+    statesState, loadAttributes, newAttributeDraft, editAttribute, saveAttributeDraft, setAttributeStatus,
+  } from './attributes.svelte.js';
+
+  $effect(() => {
+    statesState.draft = null;
+    loadAttributes(serverState.worldId);
+  });
+
+  /** The tab's « + Nouvel état » (creation_island.py rule 11). */
+  export function primaryAction() {
+    newAttributeDraft();
+  }
+
+  const KINDS = { choice: 'choix', integer: 'nombre', entity: 'entité' };
+
+  let typeLabels = $derived(Object.fromEntries(statesState.entityTypes.map((t) => [t.type, t.label])));
+
+  function typesOf(list) {
+    return list === null ? 'toute entité' : list.map((t) => typeLabels[t] || t).join(', ');
+  }
+
+  function openNear(key) {
+    const attr = statesState.attributes.find((a) => a.key === key);
+    if (attr && !attr.system) editAttribute(attr);
+    else statesState.draft = null;
+  }
+</script>
+
+<div class="states">
+  <div class="queue-panel state-list">
+    <div class="panel-head">
+      <h2>États du monde</h2>
+      <span>{statesState.attributes.length}</span>
+      <button class="btn-icon" onclick={() => loadAttributes(serverState.worldId)} title="Rafraîchir">↻</button>
+    </div>
+    <div class="queue-body">
+      {#if !serverState.worldId}
+        <div class="empty">Aucun monde actif.</div>
+      {:else if statesState.loadError}
+        <div class="empty" style="color:var(--red)">Erreur : {statesState.loadError}</div>
+      {:else}
+        {#each statesState.attributes as attr (attr.key)}
+          <div class="row-card" class:closed={attr.status !== 'active'}>
+            <div class="state-head">
+              <strong>{attr.name}</strong>
+              <span class="badge b-other">{KINDS[attr.kind]}</span>
+              {#if attr.system}<span class="badge b-other">système</span>{/if}
+              {#if attr.hidden}<span class="badge b-other">caché</span>{/if}
+              {#if attr.status !== 'active'}<span class="badge b-other">retiré</span>{/if}
+            </div>
+            <div class="muted">S'applique à : {typesOf(attr.holder_types)}
+              {#if attr.kind === 'entity'} · nomme : {typesOf(attr.value_types)}{/if}</div>
+            {#if attr.choices.length}
+              <div class="muted">{attr.choices.map((c) => c.label + (c.value === attr.default ? ' (défaut)' : '')).join(' · ')}</div>
+            {:else if attr.kind === 'integer'}
+              <div class="muted">Défaut : {attr.default}</div>
+            {/if}
+            {#if !attr.system}
+              <div class="inline">
+                <button onclick={() => editAttribute(attr)}>Modifier</button>
+                {#if attr.status === 'active'}
+                  <button disabled={attr.in_condition} title={attr.in_condition ? 'Une condition le nomme' : ''}
+                          onclick={() => setAttributeStatus(serverState.worldId, attr.key, 'retired')}>Retirer</button>
+                {:else}
+                  <button onclick={() => setAttributeStatus(serverState.worldId, attr.key, 'active')}>Rétablir</button>
+                {/if}
+              </div>
+            {/if}
+            {#if statesState.actionError?.key === attr.key}<div class="r-err">{statesState.actionError.message}</div>{/if}
+          </div>
+        {/each}
+      {/if}
+    </div>
+  </div>
+
+  {#if statesState.draft}
+    <div class="queue-panel state-editor">
+      <div class="panel-head"><h2>{statesState.draft.key ? 'Modifier l’état' : 'Nouvel état'}</h2></div>
+      <div class="queue-body">
+        <AttributeDefinitionForm draft={statesState.draft} types={statesState.entityTypes} />
+        {#if statesState.near.length}
+          <div class="near">
+            <div>Ce nom ressemble à :</div>
+            {#each statesState.near as n (n.key)}
+              <button onclick={() => openNear(n.key)}>{n.name}{n.system ? ' (système)' : ''} — {n.score} %</button>
+            {/each}
+            <button class="btn-send" onclick={() => saveAttributeDraft(serverState.worldId, true)}>Créer quand même</button>
+          </div>
+        {/if}
+        {#if statesState.saveError}<div class="r-err">{statesState.saveError}</div>{/if}
+        <div style="margin-top:10px">
+          <button class="btn-send" disabled={statesState.saving} onclick={() => saveAttributeDraft(serverState.worldId, false)}>
+            {statesState.saving ? 'Enregistrement…' : '💾 Enregistrer'}
+          </button>
+          <button onclick={() => (statesState.draft = null)}>Annuler</button>
+        </div>
+      </div>
+    </div>
+  {/if}
+</div>
+
+<style>
+  .states { display: flex; gap: 12px; align-items: flex-start; }
+  .state-list { flex: 1; }
+  .state-editor { flex: 0 0 420px; }
+  .state-head { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }
+  .state-head .badge { width: auto; }
+  .inline { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin-top: 4px; }
+  .row-card.closed { opacity: 0.6; }
+  .muted { color: var(--muted); font-size: 12px; }
+  .r-err { color: var(--red); }
+  .near { margin-top: 10px; display: flex; flex-direction: column; gap: 4px; }
+</style>
diff --git a/frontend/src/creation/StatesPanel.svelte b/frontend/src/creation/StatesPanel.svelte
new file mode 100644
index 0000000..42d95a9
--- /dev/null
+++ b/frontend/src/creation/StatesPanel.svelte
@@ -0,0 +1,116 @@
+<script>
+  /* TICKET-0113 (BRIEF-0113-C, WC1, WD1, WE1). An entity's states on its
+     sheet: every attribute that applies to its type -- the system ones
+     read-only (their own fields on the sheet keep them) --, its value or
+     « (défaut) », and its history. A value is changed through PUT
+     /api/entities/{id}/states/{key}, and the creator says each time whether
+     it is a correction (it was always so) or a change (the world changed):
+     neither is preselected (WD1). */
+  import { api } from './sheetRequest.svelte.js';
+
+  let { entityId } = $props();
+
+  let states = $state([]);
+  let entities = $state([]);
+  let loadError = $state('');
+  let editing = $state(null); // { key, value, kind }
+  let saveError = $state('');
+  let open = $state({});
+
+  async function load() {
+    try {
+      const rows = await api(`/api/entities/${encodeURIComponent(entityId)}/states`);
+      states = rows;
+      if (rows.some((s) => s.kind === 'entity')) {
+        entities = (await api('/api/quest-offers/choices')).entities || [];
+      }
+      loadError = '';
+    } catch (e) {
+      loadError = e.message;
+    }
+  }
+
+  $effect(() => {
+    if (entityId) load();
+  });
+
+  function edit(state) {
+    saveError = '';
+    editing = { key: state.key, value: state.raw ?? '', kind: '' };
+  }
+
+  async function save(state) {
+    if (!editing.kind) { saveError = 'Choisis : correction ou changement.'; return; }
+    const value = state.kind === 'integer' ? Number(editing.value) : editing.value || null;
+    try {
+      states = await api(`/api/entities/${encodeURIComponent(entityId)}/states/${encodeURIComponent(state.key)}`, {
+        method: 'PUT', headers: { 'Content-Type': 'application/json' },
+        body: JSON.stringify({ value, kind: editing.kind }),
+      });
+      editing = null;
+      saveError = '';
+    } catch (e) {
+      saveError = e.message;
+    }
+  }
+</script>
+
+{#if loadError}
+  <div class="r-err">{loadError}</div>
+{:else if states.length === 0}
+  <div class="muted">Aucun état ne s'applique à cette entité. Création › États pour en définir.</div>
+{:else}
+  {#each states as state (state.key)}
+    <div class="state-row">
+      <strong>{state.name}</strong>
+      {#if state.hidden}<span class="badge b-other">caché</span>{/if}
+      <span>{state.label}</span>
+      {#if state.is_default}<span class="muted">(défaut)</span>{/if}
+      {#if state.system}
+        <span class="muted">— système, modifiable dans les champs de la fiche</span>
+      {:else if editing?.key === state.key}
+        <div class="state-edit">
+          {#if state.kind === 'choice'}
+            <select bind:value={editing.value}>
+              {#each state.choices as c (c.value)}<option value={c.value}>{c.label}</option>{/each}
+            </select>
+          {:else if state.kind === 'integer'}
+            <input type="number" bind:value={editing.value} style="width:90px">
+          {:else}
+            <select bind:value={editing.value}>
+              <option value="">— aucune —</option>
+              {#each entities.filter((e) => state.value_types.includes(e.type)) as e (e.id)}
+                <option value={e.id}>{e.name}</option>
+              {/each}
+            </select>
+          {/if}
+          <label><input type="radio" bind:group={editing.kind} value="correction"> Correction</label>
+          <label><input type="radio" bind:group={editing.kind} value="changement"> Changement</label>
+          <button class="btn-send" onclick={() => save(state)}>OK</button>
+          <button onclick={() => { editing = null; saveError = ''; }}>Annuler</button>
+          {#if saveError}<div class="r-err">{saveError}</div>{/if}
+        </div>
+      {:else}
+        <button onclick={() => edit(state)}>Modifier</button>
+      {/if}
+      {#if state.history.length}
+        <button class="btn-icon" title="Historique" onclick={() => (open[state.key] = !open[state.key])}>🕘</button>
+      {/if}
+      {#if open[state.key]}
+        <ul class="state-history">
+          {#each state.history as h, i (i)}
+            <li>{h.changed_at.slice(0, 16).replace('T', ' ')} — {h.kind} : {h.before} → {h.after}</li>
+          {/each}
+        </ul>
+      {/if}
+    </div>
+  {/each}
+{/if}
+
+<style>
+  .state-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; margin: 4px 0; }
+  .state-edit { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; width: 100%; }
+  .state-history { width: 100%; margin: 2px 0 4px 18px; padding: 0; font-size: 12px; }
+  .muted { color: var(--muted); font-size: 12px; }
+  .r-err { color: var(--red); width: 100%; }
+</style>
diff --git a/frontend/src/creation/attributes.svelte.js b/frontend/src/creation/attributes.svelte.js
new file mode 100644
index 0000000..c7cdacb
--- /dev/null
+++ b/frontend/src/creation/attributes.svelte.js
@@ -0,0 +1,111 @@
+/* TICKET-0113 (BRIEF-0113-C, WI1). State and requests of the « États »
+   island (States.svelte): every attribute of the world -- the system ones
+   first, read-only -- and the types a definition may name; one definition
+   draft, written whole (POST/PUT /api/attributes); retire and restore (POST
+   …/status, refused while a condition names it, WJ2). A name near another
+   attribute's comes back `saved: false` with the near ones: the creator
+   opens the existing one or creates anyway (`confirm_near`, WK2).
+   `definitionDraft` / `definitionBody` are shared with the interpreter's
+   proposal card (BRIEF-0113-E). */
+import { api } from './sheetRequest.svelte.js';
+
+export const statesState = $state({
+  attributes: [],
+  entityTypes: [],
+  loadError: '',
+  draft: null, // definitionDraft(), plus `key` when it edits one
+  near: [], // the attributes near the draft's name, after a refused save
+  saving: false,
+  saveError: '',
+  actionError: '', // a refused retire, by key: { key, message }
+});
+
+/** A definition as the form edits it, from an attribute (or blank). */
+export function definitionDraft(attr) {
+  if (!attr) {
+    return { key: null, name: '', kind: 'choice', holder_types: [], value_types: [],
+             choices: [{ id: null, label: 'non' }, { id: null, label: 'oui' }], defaultLabel: 'non',
+             defaultInteger: 0, is_hidden: false };
+  }
+  const def = (attr.choices || []).find((c) => c.value === attr.default);
+  return {
+    key: attr.key, name: attr.name, kind: attr.kind, holder_types: [...(attr.holder_types || [])],
+    value_types: [...(attr.value_types || [])],
+    choices: (attr.choices || []).map((c) => ({ id: c.value, label: c.label })),
+    defaultLabel: def ? def.label : '', defaultInteger: attr.kind === 'integer' ? attr.default : 0,
+    is_hidden: !!attr.hidden,
+  };
+}
+
+/** The request body of a definition draft (`DefinitionBody`). */
+export function definitionBody(draft, confirmNear) {
+  return {
+    name: draft.name, kind: draft.kind, holder_types: draft.holder_types,
+    value_types: draft.kind === 'entity' ? draft.value_types : [],
+    choices: draft.kind === 'choice' ? draft.choices.map((c) => ({ id: c.id || null, label: c.label })) : [],
+    default: draft.kind === 'choice' ? draft.defaultLabel
+      : draft.kind === 'integer' ? Number(draft.defaultInteger) : null,
+    is_hidden: draft.is_hidden, confirm_near: !!confirmNear,
+  };
+}
+
+export function newAttributeDraft() {
+  statesState.saveError = '';
+  statesState.near = [];
+  statesState.draft = definitionDraft(null);
+}
+
+export function editAttribute(attr) {
+  statesState.saveError = '';
+  statesState.near = [];
+  statesState.draft = definitionDraft(attr);
+}
+
+export async function loadAttributes(worldId) {
+  if (!worldId) { statesState.attributes = []; statesState.entityTypes = []; return; }
+  statesState.loadError = '';
+  try {
+    const data = await api('/api/attributes');
+    statesState.attributes = data.attributes;
+    statesState.entityTypes = data.entity_types;
+  } catch (e) {
+    statesState.loadError = e.message;
+  }
+}
+
+export async function saveAttributeDraft(worldId, confirmNear) {
+  const draft = statesState.draft;
+  if (!draft) return;
+  statesState.saving = true;
+  statesState.saveError = '';
+  try {
+    const path = draft.key ? '/api/attributes/' + encodeURIComponent(draft.key) : '/api/attributes';
+    const result = await api(path, {
+      method: draft.key ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' },
+      body: JSON.stringify(definitionBody(draft, confirmNear)),
+    });
+    if (!result.saved) {
+      statesState.near = result.near;
+      return;
+    }
+    statesState.draft = null;
+    statesState.near = [];
+    await loadAttributes(worldId);
+  } catch (e) {
+    statesState.saveError = e.message;
+  } finally {
+    statesState.saving = false;
+  }
+}
+
+export async function setAttributeStatus(worldId, key, status) {
+  statesState.actionError = '';
+  try {
+    await api('/api/attributes/' + encodeURIComponent(key) + '/status', {
+      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status }),
+    });
+    await loadAttributes(worldId);
+  } catch (e) {
+    statesState.actionError = { key, message: e.message };
+  }
+}
diff --git a/frontend/src/creation/mount.js b/frontend/src/creation/mount.js
index 55aba56..f677fd3 100644
--- a/frontend/src/creation/mount.js
+++ b/frontend/src/creation/mount.js
@@ -44,8 +44,9 @@ import QueueBatchBar from './QueueBatchBar.svelte';
 import SubjectWorklist from './SubjectWorklist.svelte';
 import QuestOffers from './QuestOffers.svelte';
 import Debts from './Debts.svelte';
+import States from './States.svelte';
 
-const COMPONENTS = { constructeur: Constructeur, entityList: EntityList, entitySheet: Sheet, region: Region, batch: RoomBatch, npcAgent: NpcAgent, linkAgent: LinkAgent, artefacts: Artefacts, registre: Registre, prompts: Prompts, pjSkillFiche: PjSkillFiche, queueFilters: QueueFilters, queue: Queue, queueBatchBar: QueueBatchBar, subjectWorklist: SubjectWorklist, questOffers: QuestOffers, debts: Debts };
+const COMPONENTS = { constructeur: Constructeur, entityList: EntityList, entitySheet: Sheet, region: Region, batch: RoomBatch, npcAgent: NpcAgent, linkAgent: LinkAgent, artefacts: Artefacts, registre: Registre, prompts: Prompts, pjSkillFiche: PjSkillFiche, queueFilters: QueueFilters, queue: Queue, queueBatchBar: QueueBatchBar, subjectWorklist: SubjectWorklist, questOffers: QuestOffers, debts: Debts, states: States };
 
 const live = {}; // key -> { node, instance }
 
diff --git a/frontend/src/creation/registry.js b/frontend/src/creation/registry.js
index 337d20c..1e5a294 100644
--- a/frontend/src/creation/registry.js
+++ b/frontend/src/creation/registry.js
@@ -567,4 +567,12 @@ export const CREATION_ISLANDS = Object.freeze({
     origin: 'new',
     createdBy: 'TICKET-0110',
   }),
+  // TICKET-0113 (BRIEF-0113-C, WI1): the attributes of the world -- the
+  // state of the world -- created directly as an island, no legacy predecessor.
+  states: Object.freeze({
+    containerId: 'creation-etats',
+    component: 'States.svelte',
+    origin: 'new',
+    createdBy: 'TICKET-0113',
+  }),
 });
diff --git a/frontend/src/creation/tabs.js b/frontend/src/creation/tabs.js
index 68cf084..6aaf81b 100644
--- a/frontend/src/creation/tabs.js
+++ b/frontend/src/creation/tabs.js
@@ -358,6 +358,15 @@ export const CREATION_TABS = {
     islands: [{ key: 'debts', containerId: 'creation-dettes' }],
     primaryAction: { label: '+ Nouvelle dette', handler: () => triggerPrimaryAction('debts') },
   },
+  etats: {
+    label: 'États',
+    archetype: 'bespoke',
+    containers: ['creation-etats'],
+    loader: null,
+    state: { onTabEnter: null, onWorldSwitch: null },
+    islands: [{ key: 'states', containerId: 'creation-etats' }],
+    primaryAction: { label: '+ Nouvel état', handler: () => triggerPrimaryAction('states') },
+  },
   subjects: {
     label: 'Sujets',
     archetype: 'bespoke',
diff --git a/src/world_engine/attributes.py b/src/world_engine/attributes.py
index 120be25..507d05c 100644
--- a/src/world_engine/attributes.py
+++ b/src/world_engine/attributes.py
@@ -17,6 +17,10 @@ read the same way here:
   value, or the default when it holds none (WC1: nothing is written on read).
 - `world_entity_types(db, world_id)`  : the entity types a definition may
   name (WB2): the built-in four, then the world's active runtime types.
+- `near_attributes(db, world_id, name)` : the attributes whose name is near
+  a new one, for the creator to pick (BRIEF-0113-C, WK2).
+- `entity_states(db, world_id, entity)` : what an entity's sheet shows --
+  every attribute that applies to it, its value, its history.
 
 The vocabularies of the system attributes are the creator forms'
 (`cockpit/crud/entities.py`: `ENTITY_STATUSES`, the character's
@@ -32,7 +36,9 @@ from typing import Optional, Union
 
 from sqlmodel import Session, select
 
+from .lore_resolve import near_ratio, near_score, normalize_surface
 from .models import (
+    AttributeChange,
     AttributeChoice,
     AttributeDefinition,
     AttributeDefinitionType,
@@ -54,6 +60,12 @@ BUILTIN_ENTITY_TYPES: tuple[str, ...] = ("character", "location", "faction", "it
 
 SYSTEM_PREFIX = "sys:"
 
+# The French name of each built-in type, as the creator's « États » tab
+# lists them (a runtime type shows its `entity_type.name`).
+BUILTIN_TYPE_LABELS_FR: dict[str, str] = {
+    "character": "Personnage", "location": "Lieu", "faction": "Faction", "item": "Objet",
+}
+
 RawValue = Union[str, int, None]
 
 
@@ -242,3 +254,73 @@ def current_value(db: Session, view: AttributeView, entity: Entity) -> StateValu
         return StateValue(raw=view.default, label=value_label(db, view, view.default), is_default=True)
     raw = raw_of(row)
     return StateValue(raw=raw, label=value_label(db, view, raw), is_default=False)
+
+
+def world_entity_type_labels(db: Session, world_id: str) -> list[dict]:
+    """`world_entity_types` with each type's French name (BRIEF-0113-C)."""
+    names = dict(db.exec(select(EntityType.slug, EntityType.name).where(EntityType.world_id == world_id)).all())
+    return [{"type": t, "label": BUILTIN_TYPE_LABELS_FR.get(t) or names.get(t, t)}
+            for t in world_entity_types(db, world_id)]
+
+
+@dataclass(frozen=True)
+class NearAttribute:
+    key: str
+    name: str
+    system: bool
+    score: int
+
+
+def near_attributes(db: Session, world_id: str, name: str, exclude_key: Optional[str] = None) -> tuple[NearAttribute, ...]:
+    """The attributes whose name is near `name` (`lore_resolve.near_ratio`):
+    the system ones and the world's definitions, retired included, best
+    first. For display: the creator picks (WK2, never a duplicate « Maudit »
+    / « maudite »), the tool never does (0092)."""
+    target = normalize_surface(name or "")
+    if not target:
+        return ()
+    found = []
+    for view in world_attributes(db, world_id, include_retired=True):
+        if view.key == exclude_key:
+            continue
+        ratio = near_ratio(target, view.name)
+        if ratio is not None:
+            found.append(NearAttribute(view.key, view.name, view.system, near_score(ratio)))
+    return tuple(sorted(found, key=lambda n: (-n.score, n.name.casefold(), n.key)))
+
+
+def entity_states(db: Session, world_id: str, entity: Entity) -> list[dict]:
+    """Every active attribute that applies to `entity`, as its sheet shows it
+    (BRIEF-0113-C): the system ones first, then the world's by name, each
+    with its current value, its choices and its history, newest first."""
+    states = []
+    for view in world_attributes(db, world_id):
+        if not applies_to(view, entity.type):
+            continue
+        value = current_value(db, view, entity)
+        states.append({
+            "key": view.key, "name": view.name, "kind": view.kind, "system": view.system, "hidden": view.hidden,
+            "raw": value.raw, "label": value.label, "is_default": value.is_default,
+            "choices": [{"value": key, "label": label} for key, label in view.choices],
+            "value_types": list(view.value_types),
+            "history": [] if view.system else _history(db, view, entity.id),
+        })
+    return states
+
+
+def _history(db: Session, view: AttributeView, entity_id: str) -> list[dict]:
+    row = stored_value(db, view.key, entity_id)
+    if row is None:
+        return []
+    changes = db.exec(select(AttributeChange).where(AttributeChange.value_id == row.id)
+                      .order_by(AttributeChange.changed_at.desc(), AttributeChange.id)).all()
+    return [{
+        "kind": c.kind, "changed_by": c.changed_by, "changed_at": c.changed_at.isoformat(),
+        "before": value_label(db, view, _change_raw(c, "before", view.kind)),
+        "after": value_label(db, view, _change_raw(c, "after", view.kind)),
+    } for c in changes]
+
+
+def _change_raw(change: AttributeChange, side: str, kind: str) -> RawValue:
+    column = {"choice": "choice_id", "integer": "integer", "entity": "entity_id"}[kind]
+    return getattr(change, f"{side}_{column}")
diff --git a/src/world_engine/cockpit/app.py b/src/world_engine/cockpit/app.py
index 457d8cd..dc67fca 100644
--- a/src/world_engine/cockpit/app.py
+++ b/src/world_engine/cockpit/app.py
@@ -54,6 +54,7 @@ from ..models import LinkBatch, LinkBatchRow, NpcBatch, NpcBatchRow, SchemaMeta
 from ..schema_version import EXPECTED_STATIC_SCHEMA_VERSION
 from . import crud as _crud
 from .origin_guard import origin_guard
+from .routes import attributes as _routes_attributes
 from .routes import conditions as _routes_conditions
 from .routes import creator as _routes_creator
 from .routes import day as _routes_day
@@ -144,6 +145,7 @@ app.include_router(_routes_lore_write.router)
 app.include_router(_routes_quests.router)
 app.include_router(_routes_conditions.router)
 app.include_router(_routes_debts.router)
+app.include_router(_routes_attributes.router)
 
 app.mount("/static", _FreshnessAwareStaticFiles(directory=_STATIC_DIR), name="static")
 
diff --git a/src/world_engine/cockpit/routes/attributes.py b/src/world_engine/cockpit/routes/attributes.py
new file mode 100644
index 0000000..e0f3558
--- /dev/null
+++ b/src/world_engine/cockpit/routes/attributes.py
@@ -0,0 +1,193 @@
+"""The state of the world's routes (TICKET-0113, BRIEF-0113-C; decisions
+WA3, WB2, WD1, WI1, WJ2 and WK2 of the conditions series) -- creator CRUD, a
+sanctioned canon-write path:
+
+    GET  /api/attributes                     every attribute of the active
+                                             world (system ones first, the
+                                             retired included) and the types
+                                             a definition may name
+    POST /api/attributes                     define one
+    PUT  /api/attributes/{id}                save one
+    POST /api/attributes/{id}/status         retire or restore one
+    GET  /api/entities/{id}/states           what the entity's sheet shows
+    PUT  /api/entities/{id}/states/{key}     set its value, `correction` or
+                                             `changement` (WD1)
+
+A name near another attribute's (`attributes.near_attributes`) is not
+written until the creator confirms it (`confirm_near`): the answer is
+`{"saved": false, "near": [...]}` and she picks the existing one or creates
+anyway -- never a duplicate « Maudit » / « maudite » unseen (WK2). A system
+attribute is never written here: its field on the sheet keeps it.
+
+Every rule lives in `writes/attributes.py`; what is shown, in
+`attributes.py`. This module parses, maps a refusal to 422, and commits once.
+"""
+
+from __future__ import annotations
+
+from typing import Optional, Union
+
+from fastapi import APIRouter, Depends, HTTPException
+from pydantic import BaseModel, Field
+from sqlmodel import Session, select
+
+from ...attributes import (
+    ATTRIBUTE_FORM,
+    AttributeView,
+    attribute_view,
+    entity_states,
+    near_attributes,
+    system_attribute,
+    world_attributes,
+    world_entity_type_labels,
+)
+from ...db import get_session
+from ...models import AttributeDefinition, ConditionNode, Entity
+from ...writes.attributes import (
+    ChoiceSpec,
+    DefinitionSpec,
+    set_attribute_status,
+    write_attribute_definition,
+    write_attribute_value,
+)
+from .. import crud as _crud
+
+router = APIRouter()
+
+CHANGED_BY = "creator_crud"
+SYSTEM_READ_ONLY = "Un état système se modifie dans les champs de la fiche."
+
+
+class ChoiceBody(BaseModel):
+    label: str
+    id: Optional[str] = None
+
+
+class DefinitionBody(BaseModel):
+    name: str
+    kind: str
+    holder_types: list[str] = Field(default_factory=list)
+    value_types: list[str] = Field(default_factory=list)
+    choices: list[ChoiceBody] = Field(default_factory=list)
+    default: Union[int, str, None] = None
+    is_hidden: bool = False
+    confirm_near: bool = False
+
+
+class StatusBody(BaseModel):
+    status: str
+
+
+class ValueBody(BaseModel):
+    value: Union[int, str, None] = None
+    kind: str
+
+
+def definition_spec(body: DefinitionBody) -> DefinitionSpec:
+    """The writer's spec of a request body (shared with BRIEF-0113-E's
+    offer save)."""
+    return DefinitionSpec(
+        name=body.name, kind=body.kind, holder_types=tuple(body.holder_types),
+        value_types=tuple(body.value_types), choices=tuple(ChoiceSpec(c.label, c.id) for c in body.choices),
+        default=body.default, is_hidden=body.is_hidden,
+    )
+
+
+def _in_use(db: Session, key: str) -> bool:
+    return db.exec(select(ConditionNode.id).where(
+        ConditionNode.form == ATTRIBUTE_FORM, ConditionNode.target_key == key)).first() is not None
+
+
+def attribute_dict(db: Session, view: AttributeView) -> dict:
+    return {
+        "key": view.key, "name": view.name, "kind": view.kind, "system": view.system, "hidden": view.hidden,
+        "status": view.status,
+        "holder_types": list(view.holder_types) if view.holder_types is not None else None,
+        "value_types": list(view.value_types),
+        "choices": [{"value": key, "label": label} for key, label in view.choices],
+        "default": view.default, "in_condition": _in_use(db, view.key),
+    }
+
+
+def _near(db: Session, world_id: str, name: str, exclude: Optional[str]) -> list[dict]:
+    return [{"key": n.key, "name": n.name, "system": n.system, "score": n.score}
+            for n in near_attributes(db, world_id, name, exclude_key=exclude)]
+
+
+@router.get("/api/attributes")
+def list_attributes(db: Session = Depends(get_session)) -> dict:
+    world_id = _crud._world_id(db)
+    return {
+        "attributes": [attribute_dict(db, v) for v in world_attributes(db, world_id, include_retired=True)],
+        "entity_types": world_entity_type_labels(db, world_id),
+    }
+
+
+def _save(body: DefinitionBody, definition_id: Optional[str], db: Session) -> dict:
+    world_id = _crud._world_id(db)
+    if not body.confirm_near:
+        near = _near(db, world_id, body.name, definition_id)
+        renamed = definition_id is None or db.get(AttributeDefinition, definition_id).name != body.name
+        if near and renamed:
+            return {"saved": False, "near": near}
+    try:
+        definition = write_attribute_definition(db, world_id=world_id, spec=definition_spec(body),
+                                                definition_id=definition_id)
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=422, detail=str(exc)) from exc
+    db.commit()
+    return {"saved": True, "attribute": attribute_dict(db, attribute_view(db, world_id, definition.id))}
+
+
+@router.post("/api/attributes")
+def create_attribute(body: DefinitionBody, db: Session = Depends(get_session)) -> dict:
+    return _save(body, None, db)
+
+
+@router.put("/api/attributes/{definition_id}")
+def save_attribute(definition_id: str, body: DefinitionBody, db: Session = Depends(get_session)) -> dict:
+    definition = db.get(AttributeDefinition, definition_id)
+    if definition is None or definition.world_id != _crud._world_id(db):
+        raise HTTPException(status_code=404, detail=f"attribute {definition_id!r} not found")
+    return _save(body, definition_id, db)
+
+
+@router.post("/api/attributes/{definition_id}/status")
+def attribute_status(definition_id: str, body: StatusBody, db: Session = Depends(get_session)) -> dict:
+    world_id = _crud._world_id(db)
+    try:
+        set_attribute_status(db, world_id=world_id, definition_id=definition_id, status=body.status)
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=422, detail=str(exc)) from exc
+    db.commit()
+    return attribute_dict(db, attribute_view(db, world_id, definition_id))
+
+
+def _entity(db: Session, entity_id: str) -> Entity:
+    entity = db.get(Entity, entity_id)
+    if entity is None or entity.world_id != _crud._world_id(db):
+        raise HTTPException(status_code=404, detail=f"entity {entity_id!r} not found")
+    return entity
+
+
+@router.get("/api/entities/{entity_id}/states")
+def get_states(entity_id: str, db: Session = Depends(get_session)) -> list[dict]:
+    entity = _entity(db, entity_id)
+    return entity_states(db, entity.world_id, entity)
+
+
+@router.put("/api/entities/{entity_id}/states/{key}")
+def set_state(entity_id: str, key: str, body: ValueBody, db: Session = Depends(get_session)) -> list[dict]:
+    entity = _entity(db, entity_id)
+    if system_attribute(key) is not None:
+        raise HTTPException(status_code=422, detail=SYSTEM_READ_ONLY)
+    try:
+        write_attribute_value(db, world_id=entity.world_id, definition_id=key, entity_id=entity.id,
+                              value=body.value, kind=body.kind, changed_by=CHANGED_BY)
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=422, detail=str(exc)) from exc
+    db.commit()
+    return entity_states(db, entity.world_id, entity)
diff --git a/src/world_engine/lore_resolve.py b/src/world_engine/lore_resolve.py
index a2819c8..655c162 100644
--- a/src/world_engine/lore_resolve.py
+++ b/src/world_engine/lore_resolve.py
@@ -183,6 +183,24 @@ class NearCandidate:
     score: int         # 0-100, ratio * 100 rounded half up
 
 
+def near_ratio(target: str, text: str) -> Optional[float]:
+    """How near `text` is to `target` (already `normalize_surface`d): a
+    `difflib` ratio >= `NEAR_RATIO` or a shared 3+ token qualifies, and the
+    ratio is returned; None otherwise. The one nearness rule, read by
+    `near_in_surfaces` and by `attributes.near_attributes` (TICKET-0113)."""
+    key = normalize_surface(text)
+    ratio = difflib.SequenceMatcher(None, target, key).ratio()
+    shared = {t for t in target.split() if len(t) >= 3} & {t for t in key.split() if len(t) >= 3}
+    return ratio if ratio >= NEAR_RATIO or shared else None
+
+
+def near_score(ratio: float) -> int:
+    """A ratio as a 0-100 score, rounded half up -- not `round()`: banker's
+    rounding would score 0.625 as 62, and TICKET-0094's Near table (La Reine
+    Grise, 63) is the acceptance reference."""
+    return int(ratio * 100 + 0.5)
+
+
 def near_in_surfaces(surface_form: str, name_surfaces: Sequence[NameSurface], *,
                      exclude_ids: frozenset[str] = frozenset()) -> tuple[NearCandidate, ...]:
     """Names close to `surface_form` among `name_surfaces` (C-03,
@@ -192,22 +210,17 @@ def near_in_surfaces(surface_form: str, name_surfaces: Sequence[NameSurface], *,
     target = normalize_surface(surface_form)
     if not target:
         return ()
-    long_target = {t for t in target.split() if len(t) >= 3}
     best: dict[str, tuple[float, NameSurface]] = {}
     for s in name_surfaces:
         if s.entity_id in exclude_ids:
             continue
-        key = normalize_surface(s.text)
-        ratio = difflib.SequenceMatcher(None, target, key).ratio()
-        shared = long_target & {t for t in key.split() if len(t) >= 3}
-        if ratio < NEAR_RATIO and not shared:
+        ratio = near_ratio(target, s.text)
+        if ratio is None:
             continue
         if s.entity_id not in best or ratio > best[s.entity_id][0]:
             best[s.entity_id] = (ratio, s)
-    # Half-up, not `round()`: banker's rounding would score 0.625 as 62, and
-    # the lot's Near table (La Reine Grise, 63) is the acceptance reference.
     found = [
-        NearCandidate(s.entity_id, s.entity_name, s.entity_type, s.text, int(ratio * 100 + 0.5))
+        NearCandidate(s.entity_id, s.entity_name, s.entity_type, s.text, near_score(ratio))
         for ratio, s in best.values()
     ]
     found.sort(key=lambda c: (-c.score, c.name.casefold(), c.entity_id))
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 87d5690..dc956c0 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19135,6 +19135,33 @@ vocabulary grows by code), WH2 (V2 alone: « Le personnage est maudit » would
 tell the player), WH3 (a visible attribute readable on others; reactivation:
 TICKET-0114's journal knows who witnessed it, V1's condition).
 
+## THE CREATOR DEFINES THE STATES OF HER WORLD IN CRÉATION (TICKET-0113) -- AN « ÉTATS » TAB, A PANEL ON EVERY SHEET, A NEAR NAME CONFIRMED BEFORE IT IS WRITTEN (BRIEF-0113-c, no schema change)
+
+**WI1.** Création › États lists the world's attributes -- the three system
+ones first, read-only -- and writes one through `AttributeDefinitionForm`
+(name, kind, the types it applies to, an entity's value types, labels and
+default, hidden or not), the one form the interpreter's proposal card
+reuses (BRIEF-0113-E). A definition is retired, refused while a condition
+names it, or restored (WJ2). Every saved entity's sheet carries an
+« États » panel: each attribute that applies to its type, its value or
+« (défaut) », its history; a system attribute is read there and edited in
+its own field. Routes: `cockpit/routes/attributes.py`.
+
+**WD1 at the surface.** Changing a value asks « correction » or
+« changement » every time; neither is preselected, and a change without
+one is not sent.
+
+**WK2 in Création.** A new name near another attribute's
+(`attributes.near_attributes`, scored by `lore_resolve.near_ratio` -- the
+one nearness rule, extracted from `near_in_surfaces` unchanged) is not
+written: the answer is `saved: false` with the near ones, and the creator
+opens the existing one or creates anyway (`confirm_near`). « maudite »
+beside « Maudit » scores 92. An exact duplicate, case and accents aside, is
+refused by the writer outright.
+
+**Rejected.** WI2 (definitions created from the sheet only: the world's
+vocabulary scattered).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/attributes.py b/tooling/verify/checks/attributes.py
index 397eb1b..651ed03 100644
--- a/tooling/verify/checks/attributes.py
+++ b/tooling/verify/checks/attributes.py
@@ -1,6 +1,7 @@
 """G1 check for TICKET-0113 -- the state of the world: a world's attributes, one value per entity, its history kept.
 
-BRIEF-0113-A's rules; the attribute condition form has its own check,
+BRIEF-0113-A's rules, then BRIEF-0113-C's (the Création surfaces); the
+attribute condition form has its own check,
 `attribute_conditions.py` (BRIEF-0113-B), so each stays inside the
 corpus's per-check time budget.
 
@@ -51,6 +52,32 @@ AA6 -- migration `scripts/migrate_v2_22_attributes.py`, on a database
    nothing to do.
 AA7 -- the reader writes nothing (static, AST). `attributes.py` calls no
    `add`, `commit`, `delete`, `execute` or `flush`.
+AC1 -- the routes (BRIEF-0113-C, route functions on the AA world made
+   active). `list_attributes` lists the system attributes first, the
+   retired ones too, each with `in_condition`, and the world's types with
+   their French names (a runtime type by its name). A new name near
+   another's (« Maudit » beside « Maudite ») answers `saved: false` with the
+   near one and writes nothing; `confirm_near` writes it; saving a
+   definition under its own name asks nothing. `get_states` lists the
+   system attributes then the world's that apply to the entity, with value,
+   `is_default` and history; `set_state` writes a change of the kind given
+   and answers the states with its history line (before, after, kind); a
+   system key, an unknown kind or a refused value answer 422 and write
+   nothing.
+AC2 -- nearness (fixture). `near_attributes` finds « Maudite » for
+   « maudit » (score 92 or more) and the system « État vital » for « etat
+   vitale », never an attribute it excludes, nothing for « Porte rouge »;
+   `lore_resolve.near_in_surfaces` and `near_attributes` both score through
+   `near_ratio` (static).
+AC3 -- the Création surfaces (static). `tabs.js`'s `etats` entry mounts
+   the `states` island in `creation-etats` and routes « + Nouvel état »
+   through `triggerPrimaryAction('states')`; `registry.js` declares
+   `states` as origin 'new', created by TICKET-0113; `States.svelte` exports
+   `primaryAction` and renders `<AttributeDefinitionForm`;
+   `attributes.svelte.js` exports `definitionDraft` and `definitionBody`
+   and sends `confirm_near`; `Sheet.svelte` renders `<StatesPanel` for a
+   saved entity; `StatesPanel.svelte` sends the change's `kind`, offers
+   `correction` and `changement`, and preselects neither.
 
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
@@ -531,6 +558,137 @@ def check_aa7() -> None:
             fail(f"AA7: attributes.py calls .{call.func.attr} on line {call.lineno}")
 
 
+# --- AC1 -------------------------------------------------------------------------
+
+def check_ac1(engine, ids: dict, defs: dict) -> None:
+    from fastapi import HTTPException
+    from sqlmodel import Session
+
+    from world_engine.cockpit.routes import attributes as routes
+    from world_engine.models import AttributeChange, AttributeDefinition, World
+
+    with Session(engine) as db:
+        db.get(World, ids["world"]).is_active = True
+        db.commit()
+        listed = routes.list_attributes(db)
+        keys = [a["key"] for a in listed["attributes"]]
+        if keys[:3] != ["sys:vital_status", "sys:status", "sys:magic_status"] or not all(
+                "in_condition" in a for a in listed["attributes"]):
+            fail(f"AC1: list_attributes lists {keys}")
+        labels = {t["type"]: t["label"] for t in listed["entity_types"]}
+        if labels.get("character") != "Personnage" or labels.get("navire") != "navire" or "epave" in labels:
+            fail(f"AC1: the entity types read {labels}")
+        before = _count(db, AttributeDefinition)
+        body = routes.DefinitionBody(name="Maudit", kind="choice", holder_types=["character"],
+                                     choices=[routes.ChoiceBody(label="non"), routes.ChoiceBody(label="oui")],
+                                     default="non")
+        asked = routes.create_attribute(body, db)
+        if asked.get("saved") is not False or "Maudite" not in [n["name"] for n in asked.get("near", [])] \
+                or _count(db, AttributeDefinition) != before:
+            fail(f"AC1: a near name answered {asked}")
+        body.confirm_near = True
+        made = routes.create_attribute(body, db)
+        if made.get("saved") is not True or _count(db, AttributeDefinition) != before + 1:
+            fail(f"AC1: confirm_near answered {made}")
+        same = routes.save_attribute(made["attribute"]["key"], routes.DefinitionBody(
+            name="Maudit", kind="choice", holder_types=["character"], default="oui",
+            choices=[routes.ChoiceBody(label=c["label"], id=c["value"]) for c in made["attribute"]["choices"]]), db)
+        if same.get("saved") is not True:
+            fail(f"AC1: saving a definition under its own name answered {same}")
+        states = routes.get_states(ids["garde"], db)
+        names = [st["name"] for st in states]
+        if names[:2] != ["État vital", "Statut"] or "Maudit" not in names or "Niveau d'alerte" in names:
+            fail(f"AC1: get_states lists {names}")
+        key = made["attribute"]["key"]
+        non = next(c["value"] for c in made["attribute"]["choices"] if c["label"] == "non")
+        after = routes.set_state(ids["garde"], key, routes.ValueBody(value=non, kind="changement"), db)
+        row = next(st for st in after if st["key"] == key)
+        line = row["history"][0] if len(row["history"]) == 1 else {}
+        if row["label"] != "non" or row["is_default"] \
+                or (line.get("kind"), line.get("before"), line.get("after")) != ("changement", "oui", "non"):
+            fail(f"AC1: set_state answered {row}")
+        changes = _count(db, AttributeChange)
+        for label, call in {
+            "a system key": lambda: routes.set_state(ids["garde"], "sys:vital_status",
+                                                     routes.ValueBody(value="dead", kind="correction"), db),
+            "an unknown kind": lambda: routes.set_state(ids["garde"], key, routes.ValueBody(value=non, kind="x"), db),
+            "a refused value": lambda: routes.set_state(ids["garde"], key, routes.ValueBody(value="z",
+                                                                                           kind="correction"), db),
+        }.items():
+            try:
+                call()
+                fail(f"AC1: set_state accepts {label}")
+            except HTTPException as exc:
+                if exc.status_code != 422 or _count(db, AttributeChange) != changes:
+                    fail(f"AC1: {label} answered {exc.status_code} or wrote a change")
+        db.get(World, ids["world"]).is_active = False
+        db.commit()
+
+
+# --- AC2 -------------------------------------------------------------------------
+
+def check_ac2(engine, ids: dict, defs: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.attributes import near_attributes
+
+    with Session(engine) as db:
+        world = ids["world"]
+        found = {n.name: n.score for n in near_attributes(db, world, "maudit")}
+        if found.get("Maudite", 0) < 92:
+            fail(f"AC2: « maudit » finds {found}")
+        if "État vital" not in {n.name for n in near_attributes(db, world, "etat vitale")}:
+            fail("AC2: « etat vitale » does not find the system « État vital »")
+        if any(n.key == defs["maudit"] for n in near_attributes(db, world, "maudit", exclude_key=defs["maudit"])):
+            fail("AC2: an excluded attribute is listed")
+        if near_attributes(db, world, "Porte rouge"):
+            fail("AC2: « Porte rouge » finds a near attribute")
+    for rel in ("lore_resolve.py", "attributes.py"):
+        text = (SRC / rel).read_text(encoding="utf-8")
+        if "near_ratio(" not in text:
+            fail(f"AC2: {rel} does not score through near_ratio")
+    if (SRC / "attributes.py").read_text(encoding="utf-8").count("SequenceMatcher"):
+        fail("AC2: attributes.py scores nearness on its own")
+
+
+# --- AC3 -------------------------------------------------------------------------
+
+def check_ac3() -> None:
+    front = ROOT / "frontend" / "src" / "creation"
+
+    def read(name: str) -> str:
+        path = front / name
+        if not path.exists():
+            fail(f"AC3: {name} is missing")
+            return ""
+        return path.read_text(encoding="utf-8")
+
+    tabs = read("tabs.js")
+    entry = re.search(r"\n  etats: \{(.*?)\n  \},", tabs, re.S)
+    body = entry.group(1) if entry else ""
+    for needle in ("{ key: 'states', containerId: 'creation-etats' }", "triggerPrimaryAction('states')"):
+        if needle not in body:
+            fail(f"AC3: tabs.js's etats entry lacks {needle}")
+    registry = read("registry.js")
+    island = re.search(r"\n  states: Object\.freeze\(\{(.*?)\}\),", registry, re.S)
+    if not island or "origin: 'new'" not in island.group(1) or "createdBy: 'TICKET-0113'" not in island.group(1):
+        fail("AC3: registry.js does not declare the states island as new, TICKET-0113")
+    states = read("States.svelte")
+    for needle in ("export function primaryAction", "<AttributeDefinitionForm"):
+        if needle not in states:
+            fail(f"AC3: States.svelte lacks {needle}")
+    module = read("attributes.svelte.js")
+    for needle in ("export function definitionDraft", "export function definitionBody", "confirm_near"):
+        if needle not in module:
+            fail(f"AC3: attributes.svelte.js lacks {needle}")
+    if "<StatesPanel entityId={detail.id}" not in read("Sheet.svelte"):
+        fail("AC3: Sheet.svelte does not render the states panel")
+    panel = read("StatesPanel.svelte")
+    for needle in ("kind: editing.kind", 'value="correction"', 'value="changement"', "kind: '' }"):
+        if needle not in panel:
+            fail(f"AC3: StatesPanel.svelte lacks {needle}")
+
+
 def main() -> int:
     _fresh_db()
     from world_engine.db import create_db_and_tables, engine
@@ -542,6 +700,8 @@ def main() -> int:
         ("AA1", check_aa1), ("AA2", lambda: check_aa2(engine, ids, defs)),
         ("AA3", lambda: check_aa3(engine, ids, defs)), ("AA4", lambda: check_aa4(engine, ids)),
         ("AA5", lambda: check_aa5(engine, ids, defs)), ("AA6", check_aa6), ("AA7", check_aa7),
+        ("AC1", lambda: check_ac1(engine, ids, defs)), ("AC2", lambda: check_ac2(engine, ids, defs)),
+        ("AC3", check_ac3),
     )
     for name, rule in rules:
         try:
@@ -554,7 +714,8 @@ def main() -> int:
         return 1
     print("PASS: attributes -- v2.22 keeps a world's attributes, one value per entity of the types each "
           "names, its history row by row; the system attributes read the canon's own columns; nothing in "
-          "use is taken away")
+          "use is taken away; Création defines them, asks before a near name, and sets an entity's "
+          "value as a correction or a change")
     return 0
 
 
````

2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. Regenerate: `python tooling/glue/gen_decisions_index.py`.
4. Regenerate: `python tooling/glue/gen_file_map.py`.
5. Commit as one commit: `BRIEF-0113-C: Création -- the États tab, the states panel on every sheet, near names confirmed`.

## Scope OUT

- Editing a system attribute in the panel: its own field on the sheet keeps it (WE1).
- The interpreter (BRIEF-0113-D, E); the condition editor's row (done in B).
- A state on a new (unsaved) sheet: the panel shows on saved entities only.
- Any player surface; `legacy.html`.

## Invariants to defend

**One registry, one mount mechanism** -- États is a `CREATION_TABS` entry and a `CREATION_ISLANDS` entry of origin `new`; the panel and the form are children (INV-49, INV-50: `page_contract.py`, `creation_island.py`). **A container is sized** (INV-54). **An effect never reads what it wrote** (INV-55, `effect_self_write.py`). **Creator control** -- every write is a route over `writes/attributes.py`, one commit; a near name waits for her (AC1). **History** -- the change kind is hers, never preselected (AC3).

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain (R-21 aside).
- A named mutation does not turn its rule red.
- `page_contract.py`, `creation_island.py`, `creation_container_sizing.py` or `effect_self_write.py` turns red.
- TICKET-0094's Near table (`lore_resolve` checks) changes a score after the extraction.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- Another tab was added after `dettes` since: add `etats` after it, keep its order, report it.
- `npm run build` names a different asset hash than the prototype's: commit what it builds (`frontend_build_fresh.py` judges the manifest, not the name).

REPORT-ONLY:
- Timing of the corpus run; a check that times out under load and passes when rerun alone (name it).
- `lore_usage.py` U12c red between 20:00 and 24:00 Toronto (`--since` from a local date against UTC rows, R-21): pre-existing on `main`; rerun after midnight or name it. Never fixed here.
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/attributes.py` -> `PASS: attributes -- v2.22 keeps a world's attributes, one value per entity of the types each names, its history row by row; the system attributes read the canon's own columns; nothing in use is taken away; Création defines them, asks before a near name, and sets an entity's value as a correction or a change`
- `page_contract.py`, `creation_island.py`, `creation_container_sizing.py`, `effect_self_write.py`, `frontend_build_fresh.py`, `attribute_conditions.py`, `name_index.py`, `name_resolution.py`, `subject_resolution.py`, `day_choice.py`, `file_map.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`attributes.py` exits 1 with the rule named):
  - in `src/world_engine/cockpit/routes/attributes.py`, `        if near and renamed:` -> `        if False:` -> `AC1`
  - in `src/world_engine/attributes.py`, `            "history": [] if view.system else _history(db, view, entity.id),` -> `            "history": [],` -> `AC1`
  - in `src/world_engine/attributes.py`, `        if view.key == exclude_key:` -> `        if False:` -> `AC2`
  - in `frontend/src/creation/Sheet.svelte`, `<StatesPanel entityId={detail.id} />` -> `<div></div>` -> `AC3`
  - in `frontend/src/creation/StatesPanel.svelte`, `    editing = { key: state.key, value: state.raw ?? '', kind: '' };` -> `    editing = { key: state.key, value: state.raw ?? '', kind: 'correction' };` -> `AC3`
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 149/149 (outside 20:00-24:00 Toronto, R-21).
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

No schema change. Decision entry « THE CREATOR DEFINES THE STATES OF HER WORLD IN CRÉATION (TICKET-0113) -- AN « ÉTATS » TAB, A PANEL ON EVERY SHEET, A NEAR NAME CONFIRMED BEFORE IT IS WRITTEN (BRIEF-0113-c, no schema change) » -- in the diff.
