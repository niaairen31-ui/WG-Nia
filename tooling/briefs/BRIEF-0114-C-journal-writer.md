<!-- slug: journal-writer -->
# BRIEF 0114-C — "The journal's writer -- an event with its participants by role, its fact and who learns it; one writer for the sheet and for an approved proposal, typed or not"

Lot: LOT-0114-event-journal.md (authoritative on conflict)
Depends on: BRIEF-0114-A (C-01, C-02, C-03)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0114-B's commit).

- `src/world_engine/writes/events.py:23` -> `def write_event(` with keyword `involved_entities`
- `src/world_engine/cockpit/crud/_shared.py:302` -> `EVENT_FIELDS: list[dict[str, Any]] = [`
- `src/world_engine/cockpit/mutations.py:693` -> `def _mutation_apply_event_creation(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:`
- `src/world_engine/models/canon_event.py` -> `class EventParticipant` (A's)
- No `src/world_engine/event_payloads.py`, no `tooling/verify/checks/event_writes.py`.

## Facts carried

### R-04 — the event writers and the applier
Opened: `src/world_engine/writes/events.py:23` (`write_event(db, *,
world_id, title, description, type, knowledge_status, involved_entities,
location_id, mutation_id)`, no fact written), `write_event_update` (the
creator's correction); `src/world_engine/cockpit/mutations.py`
`_mutation_apply_event_creation` (calls `write_event` from the payload);
`src/world_engine/cockpit/routes/mutations.py:598`
(`_approve_apply_and_commit`: `with db.begin_nested()`, an applier's
error string raises, the savepoint rolls back, canon clean);
`tooling/verify/canon_write_policy.txt:85-86` (both writers write
`event`).
Consequence: C rewrites both writers on a spec (C-05), the applier reads
a payload into it (C-06); H's proposed type is written inside that same
savepoint.

### R-05 — facts, their defaults and who knows them
Opened: `src/world_engine/models/canon_knowledge.py:87` (`Fact`, `:107`
`event_id`, at most one owner, `idx_fact_event`), `:164` (`FactDefault`:
`scope_type IN ('world','faction','location','rencontre')`, `scope_id`
NULL for `world`), `:199` (`Knowledge`); `src/world_engine/facets.py:79`
(facet `evenement`, monde, typed); `src/world_engine/writes/facts.py:75`
(`create_fact`), `:163` (`update_typed_fact_content`, kind `correction`),
`:204` (`create_fact_default`); `src/world_engine/knowledge_resolve.py:253`
(`resolve_known_for_entity`, 0105: own rows, then scopes in contact);
`src/world_engine/writes/knowledge.py:72` (`KNOWLEDGE_LEVEL_LADDER`).
Consequence: an event's fact is facet `evenement`, its text « title —
description »; a type's scopes are written as `fact_default` rows; the
models read through `resolve_known_for_entity` (Q1); a scope's level is
on the ladder, never `unaware`.

### R-13 — the canon-write policy and the hard-delete list
Opened: `tooling/verify/canon_write_policy.txt` (header line 4 lists the
canon tables; one line per writer and table);
`tooling/verify/checks/single_canon_write.py` (docstring: the closed list
of hard deletes, INV-12; an unattributable assignment is a failure).
Consequence: A, C, E add their writers and tables; the full-replace
deletes (`fact_default` of an event, a type's scopes, a node's filters)
are named in the docstring.

## Contracts

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

### C-05 — `writes.events` (the journal's one writer)
Produced by: BRIEF-0114-C   Consumed by: D, E, H
`ParticipantSpec(role_id, entity_id=None, sorte_id=None, secret=None)`,
`EventScopeSpec(scope_type, scope_id, level)`, `EventSpec(type_id, title,
description=None, location_id=None, quantity=None, participants=(),
scopes=None (the type's), session_id=None, batch_id=None)`;
`event_fact_text(title, description) -> str` (« title — description »);
`clean_event(db, world_id, spec, event=None)`; `write_event(db, *,
world_id, spec, created_by) -> Event` (the event, its participants, ONE
fact `evenement`, the scopes, each participant entity's knowledge at
`knows`, secret as said, never for a player character); `event_fact(db,
event_id)`; `write_event_update(db, *, event, spec, changed_by)` (type
and participants kept; participants added; text rewritten as a
`correction`; scopes replaced whole).

### C-06 — an `event_creation` payload
Produced by: BRIEF-0114-C (H adds `new_type`, `sorte_name`)   Consumed by: H
`event_payloads.spec_from_payload(db, world_id, payload, *,
session_id=None, batch_id=None) -> EventSpec`; `provenance(db, mut) ->
(session_id, batch_id)`. Typed: `type_id`, `participants` [{role_id,
entity_id | sorte_id, secret}], `quantity`, `location_id`. Untyped: `type`
(a category), `involved_entities`, `knowledge_status` -- typed by its
domain (`ensure_domain_type`), its entities in « Impliqué », a `world`
scope at `knows` when `public`/`confirmed`. H: `new_type` (a definition,
C-10's `type_definition` form) instead of `type_id`, participants naming
its roles by `role`; `sorte_name` for a sorte the world lacks -- written in
the applier's savepoint, a same-named one used.

## Context

An event is written once, by one writer, from the journal's sheet and from an approved `event_creation` (D1): its participants by role (V1), its quantity, its place, the session and day it came from (E1), and its FACT (K-a) -- the participants know it at `knows`, secret each as said (X1), a player character never (INV-07); the type's scopes become the fact's defaults (W1). An untyped payload -- the tick's until TICKET-0119 -- is typed by its domain (N1) and keeps its former meaning (O1).

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `writes/events.py` rewritten (C-05): specs, `clean_event`, `write_event`, `event_fact`, `write_event_update`;
   - `event_payloads.py` (new, C-06): `provenance`, `spec_from_payload` (typed and untyped);
   - `cockpit/mutations.py` `_mutation_apply_event_creation` through `spec_from_payload` and `write_event`;
   - `cockpit/crud/events.py` (`EventBody`, `_event_dict`, create/update), `cockpit/crud/_shared.py` (`EVENT_FIELDS` = title, description, location_id; `EVENT_TYPE_LABELS_FR`, `EVENT_KNOWLEDGE_STATUSES` removed);
   - frontend: `eventDraft.svelte.js` (`eventDraftBody`), `Evenements.svelte` (type, quantity, participants per role with their secret, scopes), `Sheet.svelte`;
   - `canon_write_policy.txt` and the `single_canon_write.py` docstring (an event's `fact_default` replaced whole); creates check `event_writes.py` (EC1-EC6);
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - frontend/src/creation/Evenements.svelte
   - frontend/src/creation/Sheet.svelte
   - frontend/src/creation/eventDraft.svelte.js
   - src/world_engine/cockpit/crud/__init__.py
   - src/world_engine/cockpit/crud/_shared.py
   - src/world_engine/cockpit/crud/events.py
   - src/world_engine/cockpit/mutations.py
   - src/world_engine/event_payloads.py
   - src/world_engine/writes/__init__.py
   - src/world_engine/writes/events.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/canon_write_policy.txt
   - tooling/verify/checks/event_writes.py
   - tooling/verify/checks/single_canon_write.py

````diff
diff --git a/frontend/src/creation/Evenements.svelte b/frontend/src/creation/Evenements.svelte
index 1bdf691..58b9582 100644
--- a/frontend/src/creation/Evenements.svelte
+++ b/frontend/src/creation/Evenements.svelte
@@ -1,43 +1,37 @@
 <script>
-  /* TICKET-0058 (BRIEF-0058-j, per RECON-SUPPLEMENT-0058's -j re-scope).
-     Faithful port of renderEventSheet/evenementsRenderCreatePanel/
-     evenementsSave/evenementsSubmitCreate/evenementsGenerateDraft/
-     _evenementsRenderChips/evenementsAddChip/evenementsRemoveChip
-     (index.html, now deleted) -- evenements' bespoke, non-entity sheet
-     (`event` is not an ENTITY_TYPE_REGISTRY row, so it never used
-     authorRenderSheet's registry.types[type] shape; `authorRegistry.
-     event_fields` -- now Sheet.svelte's own `registry.event_fields`, the
-     SAME GET /api/entity-types response -- feeds the shared field engine
-     directly through <Field>, not through the now-deleted
-     'creation:field-render'/'creation:field-read' reverse-bridge brief -f
-     stood up for this exact gap.
-
-     Rendered by Sheet.svelte inside its own 'view' mode when
-     creationState.activeTabKey === 'evenements', with the SAME isNew/event
-     shape every other entity type's fields already use -- this component
-     only differs in field source (registry.event_fields, not
-     registry.types[type].fields) and save target (/api/events, not
-     /api/entities). The header Save button (view mode) and this
-     component's own inline "+ Créer l'événement" button (create mode) both
-     call the SAME onSave prop -- Sheet.svelte's saveEventSheet, exactly
-     mirroring how the generic entity sheet's header Save button and
-     Constructeur-style creates share one submit path.
-
-     Two writes only, no delete anywhere (C3 -- event is history, retraction
-     is knowledge_status='secret'): POST /api/events (create) and
-     PUT /api/events/{id} (save), both inside onSave.
-
-     No scoped <style> block: like every other Creation island, this
-     renders inside the legacy iframe document. */
-  import { eventDraftState, resetEventDraft, setEventDraftFromEvent, setEventDraftFromIds, addEventChip, removeEventChip } from './eventDraft.svelte.js';
+  /* TICKET-0058 (BRIEF-0058-j); rewritten by TICKET-0114 (BRIEF-0114-C) as
+     the event journal's sheet. Its plain fields (title, description, place)
+     come from `registry.event_fields` through <Field>; the rest is its own:
+     the event's type (one of the world's, fixed once written), its quantity
+     when the type counts, its participants role by role -- an entity of a
+     type the role accepts or a sorte, each entity keeping the event secret
+     or not (X1, never a player character), a participant once written
+     staying -- and who learns it besides them: the type's scopes by
+     default, or the creator's own (W1). The types and sortes come from the
+     shared vocabulary store (eventVocab.svelte.js).
+
+     Rendered by Sheet.svelte in 'view' mode on the « Événements » tab;
+     saved through its saveEventSheet (POST /api/events, PUT
+     /api/events/{id}). No delete anywhere (C3 -- an event is history; a
+     retraction empties its scopes). No scoped <style> block. */
+  import { serverState } from '../lib/serverState.svelte.js';
+  import {
+    eventDraftState, resetEventDraft, setEventDraftFromEvent, setEventDraftFromGenerated, addParticipant,
+    removeParticipant,
+  } from './eventDraft.svelte.js';
+  import { vocabState, loadVocabulary } from './eventVocab.svelte.js';
   import Field from './Field.svelte';
 
-  let { legacyDoc, isNew, event, entities, eventFields, onSave } = $props();
+  let { legacyDoc, isNew, event, entities, playerCharIds, eventFields, onSave } = $props();
 
   let genStatus = $state('');
   let genNotes = $state([]);
   let genBrief = $state('');
 
+  $effect(() => {
+    loadVocabulary(serverState.worldId);
+  });
+
   $effect(() => {
     void isNew;
     void (event && event.id);
@@ -48,25 +42,45 @@
     genBrief = '';
   });
 
-  const candidates = $derived((entities || []).filter((e) => !eventDraftState.involved.some((c) => c.id === e.id)));
+  const SCOPE_TYPES = [
+    { value: 'world', label: 'tout le monde' }, { value: 'location', label: 'ceux qui passent au lieu' },
+    { value: 'rencontre', label: 'ceux qui ont rencontré' }, { value: 'faction', label: 'les membres de la faction' },
+  ];
+
+  let type = $derived(vocabState.types.find((t) => t.id === eventDraftState.typeId) || null);
+  let roles = $derived(type ? type.roles.filter((r) => r.status === 'active') : []);
+  let activeSortes = $derived(vocabState.sortes.filter((s) => s.status === 'active'));
+  let levelLabels = $derived(Object.fromEntries(vocabState.levels.map((l) => [l.value, l.label])));
 
-  function onChipAdd(ev) {
-    const id = ev.currentTarget.value;
-    if (!id) return;
-    const entity = (entities || []).find((e) => e.id === id);
-    if (entity) addEventChip(entity);
+  function candidates(role) {
+    return (entities || []).filter((e) => role.entity_types.includes(e.type));
+  }
+
+  function onAdd(role, ev) {
+    const value = ev.currentTarget.value;
     ev.currentTarget.value = '';
+    if (!value) return;
+    const [kind, id] = value.split(':');
+    const name = kind === 'sorte' ? (activeSortes.find((s) => s.id === id) || {}).name
+      : ((entities || []).find((e) => e.id === id) || {}).name;
+    addParticipant(role, kind, id, name, type && type.participants_secret);
+  }
+
+  function scopeTargets(scopeType) {
+    if (scopeType === 'location') return (entities || []).filter((e) => e.type === 'location');
+    if (scopeType === 'faction') return (entities || []).filter((e) => e.type === 'faction');
+    return entities || [];
+  }
+
+  function typeScopeLine(t) {
+    if (!t || !t.scopes.length) return 'les participants seulement';
+    return t.scopes.map((s) => `${s.kind}${s.role ? ' ' + s.role : ''} (${levelLabels[s.level] || s.level})`).join(' · ');
   }
 
-  /** evenements' AI assistant (BRIEF-0022-b) -- pre-fills the create shell
-   *  from a one-shot POST /api/events/generate; a second click overwrites,
-   *  same F2 precedent as the entity GeneratePanel. The currently chosen
-   *  location_id (if any) is sent as an authoritative pre-selection. */
   async function generate() {
     const brief = genBrief.trim();
     if (!brief) { genStatus = 'Intention requise.'; return; }
     const locationId = legacyDoc.getElementById('event-f-location_id')?.value || null;
-
     genStatus = 'Génération…';
     let result;
     try {
@@ -84,15 +98,11 @@
       genStatus = (result && result.error) || 'Échec de la génération.';
       return;
     }
-
     const setVal = (id, v) => { const el = legacyDoc.getElementById(id); if (el) el.value = v ?? ''; };
     setVal('event-f-title', result.title);
     setVal('event-f-description', result.description);
-    setVal('event-f-type', result.type);
     if (result.location_id) setVal('event-f-location_id', result.location_id);
-
-    setEventDraftFromIds(result.involved_entities, entities || []);
-
+    setEventDraftFromGenerated(result, vocabState.types, entities || []);
     genNotes = result.notes || [];
     genStatus = "Brouillon généré — relisez et éditez avant d'accepter.";
   }
@@ -124,26 +134,77 @@
   {/each}
 </div></div>
 
-<div class="field-section"><div class="field-section-title">Entités impliquées</div>
-  <div id="evenements-chips">
-    {#if eventDraftState.involved.length === 0}
-      <div class="empty">Aucune entité impliquée.</div>
+<div class="field-section"><div class="field-section-title">Type</div>
+  <select id="event-f-type_id" bind:value={eventDraftState.typeId} disabled={!isNew}>
+    <option value="">— choisir un type —</option>
+    {#each vocabState.types.filter((t) => t.status === 'active' || t.id === eventDraftState.typeId) as t (t.id)}
+      <option value={t.id}>{t.name} ({t.domain_label})</option>
+    {/each}
+  </select>
+  {#if !isNew}<span style="color:var(--muted); font-size:12px;"> Le type d'un événement ne change pas.</span>{/if}
+  {#if type && type.counts_quantity}
+    <label style="display:block; margin-top:6px">Quantité
+      <input id="event-f-quantity" type="number" min="1" style="width:90px" bind:value={eventDraftState.quantity}>
+    </label>
+  {/if}
+</div>
+
+{#if type}
+  <div class="field-section"><div class="field-section-title">Participants</div>
+    {#each roles as role (role.id)}
+      <div style="margin:4px 0">
+        <strong>{role.name}</strong>
+        {#each eventDraftState.participants as p, i (i)}
+          {#if p.role_id === role.id}
+            <span class="badge b-other" style="display:inline-flex; align-items:center; gap:5px; margin:2px">
+              {p.sorte_id ? 'sorte : ' : ''}{p.name || '« inconnu »'}
+              {#if p.entity_id && !(playerCharIds && playerCharIds.has(p.entity_id))}
+                <label title="Il garde le secret"><input type="checkbox" bind:checked={p.secret}> secret</label>
+              {/if}
+              {#if !p.saved}
+                <button class="btn-icon" style="padding:0 2px" title="Retirer" onclick={() => removeParticipant(i)}>✕</button>
+              {/if}
+            </span>
+          {/if}
+        {/each}
+        <select onchange={(ev) => onAdd(role, ev)}>
+          <option value="">— ajouter —</option>
+          {#each candidates(role) as e (e.id)}<option value={'entity:' + e.id}>{e.name}</option>{/each}
+          {#if role.accepts_sorte}
+            {#each activeSortes as s (s.id)}<option value={'sorte:' + s.id}>sorte : {s.name}</option>{/each}
+          {/if}
+        </select>
+      </div>
+    {/each}
+  </div>
+
+  <div class="field-section"><div class="field-section-title">Qui l'apprend, en plus des participants</div>
+    <label><input type="checkbox" bind:checked={eventDraftState.customScopes}> Choisir pour cet événement</label>
+    {#if !eventDraftState.customScopes}
+      <div style="color:var(--muted); font-size:12px;">Celle du type : {typeScopeLine(type)}</div>
     {:else}
-      {#each eventDraftState.involved as c, i}
-        <span class="badge b-other" style="display:inline-flex; align-items:center; gap:5px; margin:2px">
-          {c.name ? c.name : `« entité inconnue » (${(c.id || '').slice(0, 8)})`}
-          <button class="btn-icon" style="padding:0 2px" title="Retirer" onclick={() => removeEventChip(i)}>✕</button>
-        </span>
+      {#each eventDraftState.scopes as scope, k (k)}
+        <div style="display:flex; gap:6px; align-items:center; margin:2px 0">
+          <select bind:value={scope.scope_type} onchange={() => (scope.scope_id = null)}>
+            {#each SCOPE_TYPES as st (st.value)}<option value={st.value}>{st.label}</option>{/each}
+          </select>
+          {#if scope.scope_type !== 'world'}
+            <select bind:value={scope.scope_id}>
+              <option value={null}>— choisir —</option>
+              {#each scopeTargets(scope.scope_type) as e (e.id)}<option value={e.id}>{e.name}</option>{/each}
+            </select>
+          {/if}
+          <select bind:value={scope.level}>
+            {#each vocabState.levels as l (l.value)}<option value={l.value}>{l.label}</option>{/each}
+          </select>
+          <button class="btn-icon" title="Retirer" onclick={() => eventDraftState.scopes.splice(k, 1)}>✕</button>
+        </div>
       {/each}
+      {#if !eventDraftState.scopes.length}<div style="color:var(--muted); font-size:12px;">Personne d'autre.</div>{/if}
+      <button onclick={() => eventDraftState.scopes.push({ scope_type: 'world', scope_id: null, level: 'knows' })}>+ portée</button>
     {/if}
   </div>
-  <select onchange={onChipAdd}>
-    <option value="">— ajouter une entité —</option>
-    {#each candidates as e (e.id)}
-      <option value={e.id}>{e.name}</option>
-    {/each}
-  </select>
-</div>
+{/if}
 
 {#if !isNew}
   <div class="field-section"><span style="color:var(--muted); font-size:12px;">Enregistré : {event.recorded_at || ''}</span></div>
diff --git a/frontend/src/creation/Sheet.svelte b/frontend/src/creation/Sheet.svelte
index b2f8b87..3062eb9 100644
--- a/frontend/src/creation/Sheet.svelte
+++ b/frontend/src/creation/Sheet.svelte
@@ -100,7 +100,7 @@
   import PendingGoalsEditor from './PendingGoalsEditor.svelte';
   import { resetGeneratePanel, applyGeneratedDraft } from './generatePanel.svelte.js';
   import GeneratePanel from './GeneratePanel.svelte';
-  import { resetEventDraft, eventDraftState } from './eventDraft.svelte.js';
+  import { resetEventDraft, eventDraftState, eventDraftBody } from './eventDraft.svelte.js';
   import Evenements from './Evenements.svelte';
   import Intrigues from './Intrigues.svelte';
   import CompetencesSheet from './CompetencesSheet.svelte';
@@ -551,7 +551,13 @@
       if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = 'Titre requis.'; }
       return;
     }
-    body.involved_entities = eventDraftState.involved.map((c) => c.id);
+    // TICKET-0114 (BRIEF-0114-C): the type, quantity, participants and
+    // scopes the journal sheet edits itself.
+    if (!eventDraftState.typeId) {
+      if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = 'Type requis.'; }
+      return;
+    }
+    Object.assign(body, eventDraftBody());
 
     if (statusEl) { statusEl.className = 'author-status'; statusEl.textContent = isNewSave ? '…' : 'Saving…'; }
     try {
@@ -716,7 +722,7 @@
       <div class="empty"><span class="spin">⟳</span></div>
     {:else if type === 'evenements'}
       <Evenements {legacyDoc} {isNew} event={detail} entities={creationState.entities}
-        eventFields={registry.event_fields} onSave={saveSheet} />
+        playerCharIds={creationState.playerCharIds} eventFields={registry.event_fields} onSave={saveSheet} />
     {:else if type === 'intrigues'}
       <Intrigues {isNew} agenda={detail} />
     {:else if type === 'competences'}
diff --git a/frontend/src/creation/eventDraft.svelte.js b/frontend/src/creation/eventDraft.svelte.js
index d4e59c2..37f52b9 100644
--- a/frontend/src/creation/eventDraft.svelte.js
+++ b/frontend/src/creation/eventDraft.svelte.js
@@ -1,35 +1,79 @@
-/* TICKET-0058 (BRIEF-0058-j). Shared involved_entities chip-editor draft
-   for the Événements sheet -- was the evenementsInvolvedDraft global
-   (index.html, now deleted). A module-level store, not Evenements.svelte-
-   local state, for the same reason generatePanelState is module-level
-   (generatePanel.svelte.js): Sheet.svelte's header/save code needs to read
-   and reset it too, and a plain <Evenements> instance does not remount on
-   every selection change (it renders the same component, new props). */
-export const eventDraftState = $state({ involved: [] }); // [{id, name}]
+/* TICKET-0058 (BRIEF-0058-j); rewritten by TICKET-0114 (BRIEF-0114-C). The
+   journal sheet's draft beyond its plain fields: the event's type, its
+   quantity, its participants by role -- an entity or a sorte, each entity
+   keeping it secret or not (X1) -- and who learns it besides them (its
+   scopes: the type's when `customScopes` is off, W1). A module-level store,
+   not Evenements.svelte-local state, because Sheet.svelte's save reads it
+   too and a plain <Evenements> instance does not remount on every
+   selection change. A participant already written (`saved`) stays: an
+   event's participants are never taken away. */
+export const eventDraftState = $state({
+  typeId: '',
+  quantity: null,
+  participants: [], // {role_id, entity_id, sorte_id, name, secret, saved}
+  customScopes: false,
+  scopes: [], // {scope_type, scope_id, level}
+});
 
 export function resetEventDraft() {
-  eventDraftState.involved = [];
+  eventDraftState.typeId = '';
+  eventDraftState.quantity = null;
+  eventDraftState.participants = [];
+  eventDraftState.customScopes = false;
+  eventDraftState.scopes = [];
 }
 
 export function setEventDraftFromEvent(event) {
-  eventDraftState.involved = (event.involved_entities || []).map((c) => ({ id: c.id, name: c.name }));
+  eventDraftState.typeId = event.type_id || '';
+  eventDraftState.quantity = event.quantity ?? null;
+  eventDraftState.participants = (event.participants || []).map((p) => ({
+    role_id: p.role_id, entity_id: p.entity_id, sorte_id: p.sorte_id, name: p.name, secret: !!p.secret, saved: true,
+  }));
+  eventDraftState.customScopes = true;
+  eventDraftState.scopes = (event.scopes || []).map((s) => ({ scope_type: s.scope_type, scope_id: s.scope_id, level: s.level }));
 }
 
-/** Prefill from the AI draft-generate response, which carries a flat id
- *  list (not {id, name} pairs) -- resolved against the already-loaded
- *  entity list, same as the legacy evenementsGenerateDraft did. */
-export function setEventDraftFromIds(ids, entities) {
-  eventDraftState.involved = (ids || []).map((id) => {
+/** Prefill from the AI draft (POST /api/events/generate): its former
+ *  category picks the world's type of that domain, its entities fill the
+ *  type's first role when the role accepts them. */
+export function setEventDraftFromGenerated(result, types, entities) {
+  const type = types.find((t) => t.status === 'active' && t.domain === result.type);
+  eventDraftState.typeId = type ? type.id : eventDraftState.typeId;
+  const role = type ? type.roles.find((r) => r.status === 'active') : null;
+  eventDraftState.participants = [];
+  if (!role) return;
+  for (const id of result.involved_entities || []) {
     const entity = entities.find((e) => e.id === id);
-    return { id, name: entity ? entity.name : null };
-  });
+    if (entity && role.entity_types.includes(entity.type)) {
+      eventDraftState.participants.push({ role_id: role.id, entity_id: id, sorte_id: null, name: entity.name,
+                                         secret: !!type.participants_secret, saved: false });
+    }
+  }
 }
 
-export function addEventChip(entity) {
-  if (eventDraftState.involved.some((c) => c.id === entity.id)) return;
-  eventDraftState.involved.push({ id: entity.id, name: entity.name });
+export function addParticipant(role, kind, id, name, defaultSecret) {
+  const same = (p) => p.role_id === role.id && (kind === 'entity' ? p.entity_id === id : p.sorte_id === id);
+  if (eventDraftState.participants.some(same)) return;
+  eventDraftState.participants.push({ role_id: role.id, entity_id: kind === 'entity' ? id : null,
+                                      sorte_id: kind === 'sorte' ? id : null, name, secret: !!defaultSecret,
+                                      saved: false });
 }
 
-export function removeEventChip(i) {
-  eventDraftState.involved.splice(i, 1);
+export function removeParticipant(i) {
+  if (eventDraftState.participants[i] && !eventDraftState.participants[i].saved) {
+    eventDraftState.participants.splice(i, 1);
+  }
+}
+
+/** The request body's draft part (`EventBody`, beside the plain fields). */
+export function eventDraftBody() {
+  return {
+    type_id: eventDraftState.typeId,
+    quantity: eventDraftState.quantity === null || eventDraftState.quantity === '' ? null
+      : Number(eventDraftState.quantity),
+    participants: eventDraftState.participants.map((p) => ({
+      role_id: p.role_id, entity_id: p.entity_id, sorte_id: p.sorte_id, secret: p.entity_id ? !!p.secret : null,
+    })),
+    scopes: eventDraftState.customScopes ? eventDraftState.scopes.map((s) => ({ ...s })) : null,
+  };
 }
diff --git a/src/world_engine/cockpit/crud/__init__.py b/src/world_engine/cockpit/crud/__init__.py
index 8ca24c0..4a8121e 100644
--- a/src/world_engine/cockpit/crud/__init__.py
+++ b/src/world_engine/cockpit/crud/__init__.py
@@ -38,10 +38,10 @@ Deletion policy:
   `_apply_mutation`'s `resource_change` branch, BRIEF-19, which reuses the
   same helper).
 - `event` rows: **no delete, ever** (TICKET-0022, C3) — an event either
-  happened or did not; `event` is history. Retraction is
-  `knowledge_status = 'secret'`, which structurally excludes the row from
-  all four readers (`context.py`, `tick.py` x2, the play routes' return-visit
-  delta). Mirrors `ledger`'s append-only policy above.
+  happened or did not; `event` is history. Since TICKET-0114 (BRIEF-0114-C)
+  who knows it is its fact's knowledge and scopes: a retraction removes its
+  scopes (no one learns it any more), never the row. Mirrors `ledger`'s
+  append-only policy above.
 
 Author edits to `relation` are state-setting, not delta accumulation —
 but still append the previous state to `change_history` first (history is
@@ -168,13 +168,8 @@ from .agendas import (
 )
 from .events import (
     EVENT_FIELDS,
-    EVENT_KNOWLEDGE_STATUSES,
-    EVENT_TYPE_LABELS_FR,
-    EventCreateBody,
-    EventUpdateBody,
+    EventBody,
     _event_dict,
-    _validate_event_involved,
-    _validate_event_location,
     create_event,
     get_event,
     list_events,
diff --git a/src/world_engine/cockpit/crud/_shared.py b/src/world_engine/cockpit/crud/_shared.py
index f2fb5a2..285ddb8 100644
--- a/src/world_engine/cockpit/crud/_shared.py
+++ b/src/world_engine/cockpit/crud/_shared.py
@@ -20,9 +20,9 @@ a brief. The set, and why each entry is here:
   knowledge lookup, extracted to keep the serializer a flat dict.
 - `KNOWLEDGE_LEVELS_ORDERED`, `KNOWLEDGE_FIELDS`, `_knowledge_dict`,
   `_list_knowledge` — same reasoning, for `knowledge.py`.
-- `EVENT_TYPE_LABELS_FR`, `EVENT_KNOWLEDGE_STATUSES`, `EVENT_FIELDS` —
-  `EVENT_FIELDS` is built from the other two, which `events.py` also uses
-  for its own validation; kept together as one source of truth.
+- `EVENT_FIELDS` — the journal sheet's plain fields (since TICKET-0114,
+  BRIEF-0114-C: the former categories and `knowledge_status` are gone, a
+  type and its scopes say what they said).
 - `_validate_entity_ref`, `_coerce_field` (BRIEF-0046-e) — the generic
   field-coercion pair, re-homed here so both `entities.py` (static
   `ENTITY_TYPE_REGISTRY` CRUD) and the new `entity_runtime.py` (governed
@@ -285,28 +285,12 @@ def _list_knowledge(entity_id: str, db: DbSession) -> list[dict]:
     return [_knowledge_dict(k, db) for k in rows]
 
 
-EVENT_TYPE_LABELS_FR: dict[str, str] = {
-    "political": "politique",
-    "military":  "militaire",
-    "criminal":  "criminel",
-    "social":    "social",
-    "mystery":   "mystère",
-    "magical":   "magique",
-    "other":     "autre",
-}
-
-
-EVENT_KNOWLEDGE_STATUSES = ("secret", "public", "confirmed")
-
-
+# The journal's plain fields (TICKET-0114, BRIEF-0114-C): the type, the
+# quantity, the participants and the scopes are the journal sheet's own
+# editors (`Evenements.svelte`), never generic fields.
 EVENT_FIELDS: list[dict[str, Any]] = [
     {"name": "title", "label": "Titre", "kind": "text", "required": True},
     {"name": "description", "label": "Description", "kind": "textarea"},
-    {"name": "type", "label": "Type", "kind": "datalist",
-     "options": list(EVENT_TYPE_LABELS_FR.keys())},
-    {"name": "knowledge_status", "label": "Statut de connaissance",
-     "kind": "select", "options": list(EVENT_KNOWLEDGE_STATUSES),
-     "default": "secret", "required": True},
     {"name": "location_id", "label": "Lieu", "kind": "entity_ref",
      "ref_type": "location"},
 ]
diff --git a/src/world_engine/cockpit/crud/events.py b/src/world_engine/cockpit/crud/events.py
index 62ce270..d9e9804 100644
--- a/src/world_engine/cockpit/crud/events.py
+++ b/src/world_engine/cockpit/crud/events.py
@@ -1,157 +1,131 @@
-"""Author CRUD — events (TICKET-0022): no-delete-ever history rows.
-
-Split out of `cockpit/crud.py` (TICKET-0027, BRIEF-0027-d) — pure move,
-no logic change.
+"""Author CRUD — the event journal (TICKET-0022; rewritten by TICKET-0114,
+BRIEF-0114-C): no-delete-ever history rows.
+
+An event is one happening of one of the world's event types: its title and
+description, its place, its quantity when its type counts, its participants
+by role (an entity or a sorte, each entity keeping it secret or not, X1),
+and who learns it besides them (its fact's scopes, the type's by default,
+W1). `POST /api/events` writes one, `PUT /api/events/{id}` corrects one --
+its type stays and no participant is taken away -- both through
+`writes.events`; every refusal is a 422.
+
+`_event_dict` is what the journal shows: the participants with their role
+and their secret (read from their own knowledge row), the scopes with what
+they name.
 """
 
 from __future__ import annotations
 
-import json
-from datetime import UTC, datetime
 from typing import Optional
 
-from fastapi import APIRouter, Depends, HTTPException, Query
-from pydantic import BaseModel
-from sqlalchemy.exc import IntegrityError
+from fastapi import Depends, HTTPException
+from pydantic import BaseModel, Field
 from sqlmodel import Session as DbSession, select
 
 from ...db import get_session
-from ...entity_author import generate_npc_goals
-from ...gathering import close_open_memberships
-from ...ledger import get_balance, list_entries
-from ...ollama_client import OllamaError, ping
-from ...models import (
-    Agenda,
-    AgendaStep,
-    BASE_SKILL_DOMAINS,
-    Character,
-    DiscoverableDetail,
-    Entity,
-    Event,
-    EventEntity,
-    Faction,
-    FactionMembership,
-    FactionRole,
-    GoalAgendaLink,
-    GoalPrerequisite,
-    Item,
-    Knowledge,
-    Ledger,
-    Location,
-    NpcPrice,
-    PromptTemplate,
-    PromptVariable,
-    ProposedMutation,
-    Relation,
-    Skill,
-    SkillDefinition,
-)
-from ...prompt_registry import PROMPT_REGISTRY, effective_model
-from ...prompt_store import current_prompt, get_version, list_versions
-from ...tick_normalize import _EVENT_TYPES
-from ...writes import (
-    KNOWLEDGE_LEVELS,
-    NPC_GOAL_HORIZONS,
-    NPC_GOAL_PREREQUISITE_TYPES,
-    PromptValidationError,
-    detach_goal_agenda_link,
-    write_agenda,
-    write_agenda_status,
-    write_agenda_step,
-    write_agenda_step_status,
+from ...event_vocab import DOMAIN_LABELS_FR, type_view
+from ...models import Entity, Event, EventParticipant, EventSorte, FactDefault, Knowledge
+from ...writes.events import (
+    EventScopeSpec,
+    EventSpec,
+    ParticipantSpec,
+    event_fact,
     write_event,
     write_event_update,
-    write_faction_role,
-    write_goal_agenda_link,
-    write_knowledge,
-    write_ledger_entry,
-    write_membership,
-    write_npc_goal,
-    write_npc_goal_prerequisites,
-    write_npc_goal_status,
-    write_npc_prices,
-    write_prompt_version,
-    write_relation,
-    write_skill_rank,
 )
 
 from ._router import router
-from ._shared import (
-    EVENT_FIELDS,
-    EVENT_KNOWLEDGE_STATUSES,
-    EVENT_TYPE_LABELS_FR,
-    _iso,
-    _world_id,
-)
+from ._shared import EVENT_FIELDS, _iso, _world_id
+
+CHANGED_BY = "creator_crud"
+
+
+def _name(db: DbSession, entity_id: Optional[str]) -> Optional[str]:
+    entity = db.get(Entity, entity_id) if entity_id else None
+    return entity.name if entity is not None else None
+
+
+def _participants(db: DbSession, event: Event, fact_id: Optional[str], roles: dict) -> list[dict]:
+    rows = db.exec(select(EventParticipant).where(EventParticipant.event_id == event.id)
+                   .order_by(EventParticipant.position, EventParticipant.id)).all()
+    out = []
+    for row in rows:
+        secret = None
+        if row.entity_id and fact_id:
+            known = db.exec(select(Knowledge).where(Knowledge.entity_id == row.entity_id,
+                                                    Knowledge.fact_id == fact_id)).first()
+            secret = known.is_secret if known is not None else None
+        sorte = db.get(EventSorte, row.sorte_id) if row.sorte_id else None
+        out.append({"role_id": row.role_id, "role_name": roles.get(row.role_id), "entity_id": row.entity_id,
+                    "sorte_id": row.sorte_id, "name": sorte.name if sorte else _name(db, row.entity_id),
+                    "secret": secret})
+    return out
 
 
 def _event_dict(event: Event, db: DbSession) -> dict:
-    location = db.get(Entity, event.location_id) if event.location_id else None
-    involved = []
-    links = db.exec(select(EventEntity).where(EventEntity.event_id == event.id)).all()
-    for link in links:
-        target = db.get(Entity, link.entity_id)
-        involved.append({"id": link.entity_id, "name": target.name if target is not None else None})
+    view = type_view(db, event.type_id)
+    fact = event_fact(db, event.id)
+    scopes = db.exec(select(FactDefault).where(FactDefault.fact_id == fact.id)).all() if fact else []
     return {
         "id": event.id,
         "title": event.title,
         "description": event.description,
-        "type": event.type,
-        "type_label": EVENT_TYPE_LABELS_FR.get(event.type, event.type),
-        "knowledge_status": event.knowledge_status,
+        "type_id": event.type_id,
+        "type_name": view.name if view else None,
+        "type_label": f"{view.name} ({DOMAIN_LABELS_FR[view.domain]})" if view else None,
+        "quantity": event.quantity,
         "location_id": event.location_id,
-        "location_name": location.name if location is not None else None,
-        "involved_entities": involved,
+        "location_name": _name(db, event.location_id),
+        "participants": _participants(db, event, fact.id if fact else None,
+                                      {r.id: r.name for r in view.roles} if view else {}),
+        "scopes": [{"scope_type": s.scope_type, "scope_id": s.scope_id, "scope_name": _name(db, s.scope_id),
+                    "level": s.level} for s in scopes],
+        "fact_id": fact.id if fact else None,
+        "session_id": event.session_id,
+        "batch_id": event.batch_id,
         "recorded_at": _iso(event.recorded_at),
     }
 
 
-def _validate_event_location(db: DbSession, world_id: str, location_id: Optional[str]) -> Optional[str]:
-    """Reuses the exact predicate at app.py:1575-1583 (event_creation branch)
-    — active `location` entity in the active world. 422 on anything else:
-    the creator's picker cannot produce a bad id, so a bad id is a bug, not
-    a typo."""
-    if not location_id:
-        return None
-    target = db.get(Entity, location_id)
-    if (
-        target is None
-        or target.type != "location"
-        or target.status != "active"
-        or target.world_id != world_id
-    ):
-        raise HTTPException(422, f"location_id {location_id!r} is not an active location in this world")
-    return location_id
-
-
-def _validate_event_involved(db: DbSession, world_id: str, ids: Optional[list]) -> Optional[list]:
-    if not ids:
-        return None
-    out = []
-    for entity_id in ids:
-        target = db.get(Entity, entity_id)
-        if target is None or target.world_id != world_id:
-            raise HTTPException(422, f"involved_entities: {entity_id!r} is not a valid entity id in this world")
-        out.append(entity_id)
-    return out
+class ParticipantBody(BaseModel):
+    role_id: str
+    entity_id: Optional[str] = None
+    sorte_id: Optional[str] = None
+    secret: Optional[bool] = None
 
 
-class EventCreateBody(BaseModel):
-    title: str
-    description: Optional[str] = None
-    type: Optional[str] = None
-    knowledge_status: str = "secret"
-    location_id: Optional[str] = None
-    involved_entities: Optional[list[str]] = None
+class EventScopeBody(BaseModel):
+    scope_type: str
+    scope_id: Optional[str] = None
+    level: str = "knows"
 
 
-class EventUpdateBody(BaseModel):
+class EventBody(BaseModel):
     title: str
     description: Optional[str] = None
-    type: Optional[str] = None
-    knowledge_status: str
+    type_id: str
     location_id: Optional[str] = None
-    involved_entities: Optional[list[str]] = None
+    quantity: Optional[int] = None
+    participants: list[ParticipantBody] = Field(default_factory=list)
+    # None: the type's scopes (W1); a list, even empty: exactly these.
+    scopes: Optional[list[EventScopeBody]] = None
+
+
+def event_spec(body: EventBody) -> EventSpec:
+    return EventSpec(
+        type_id=body.type_id, title=body.title, description=body.description, location_id=body.location_id,
+        quantity=body.quantity,
+        participants=tuple(ParticipantSpec(p.role_id, p.entity_id, p.sorte_id, p.secret) for p in body.participants),
+        scopes=None if body.scopes is None else tuple(EventScopeSpec(s.scope_type, s.scope_id, s.level)
+                                                       for s in body.scopes),
+    )
+
+
+def _event(db: DbSession, event_id: str) -> Event:
+    event = db.get(Event, event_id)
+    if event is None or event.world_id != _world_id(db):
+        raise HTTPException(404, f"Event {event_id!r} not found")
+    return event
 
 
 @router.get("/events")
@@ -165,60 +139,32 @@ def list_events(db: DbSession = Depends(get_session)) -> list[dict]:
 
 @router.get("/events/{event_id}")
 def get_event(event_id: str, db: DbSession = Depends(get_session)) -> dict:
-    event = db.get(Event, event_id)
-    if event is None or event.world_id != _world_id(db):
-        raise HTTPException(404, f"Event {event_id!r} not found")
-    return _event_dict(event, db)
+    return _event_dict(_event(db, event_id), db)
 
 
 @router.post("/events", status_code=201)
-def create_event(body: EventCreateBody, db: DbSession = Depends(get_session)) -> dict:
-    world_id = _world_id(db)
-    if not body.title or not body.title.strip():
-        raise HTTPException(422, "title is required")
-    if body.knowledge_status not in EVENT_KNOWLEDGE_STATUSES:
-        raise HTTPException(422, f"knowledge_status must be one of {EVENT_KNOWLEDGE_STATUSES}")
-    location_id = _validate_event_location(db, world_id, body.location_id)
-    involved = _validate_event_involved(db, world_id, body.involved_entities)
-
-    event = write_event(
-        db,
-        world_id=world_id,
-        title=body.title.strip(),
-        description=body.description,
-        type=body.type,
-        knowledge_status=body.knowledge_status,
-        involved_entities=involved,
-        location_id=location_id,
-    )
+def create_event(body: EventBody, db: DbSession = Depends(get_session)) -> dict:
+    try:
+        event = write_event(db, world_id=_world_id(db), spec=event_spec(body), created_by=CHANGED_BY)
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(422, str(exc)) from exc
     db.commit()
     db.refresh(event)
     return _event_dict(event, db)
 
 
 @router.put("/events/{event_id}")
-def update_event(event_id: str, body: EventUpdateBody, db: DbSession = Depends(get_session)) -> dict:
-    event = db.get(Event, event_id)
-    if event is None or event.world_id != _world_id(db):
-        raise HTTPException(404, f"Event {event_id!r} not found")
-    world_id = _world_id(db)
-    if not body.title or not body.title.strip():
-        raise HTTPException(422, "title is required")
-    if body.knowledge_status not in EVENT_KNOWLEDGE_STATUSES:
-        raise HTTPException(422, f"knowledge_status must be one of {EVENT_KNOWLEDGE_STATUSES}")
-    location_id = _validate_event_location(db, world_id, body.location_id)
-    involved = _validate_event_involved(db, world_id, body.involved_entities)
-
-    event = write_event_update(
-        db,
-        event=event,
-        title=body.title.strip(),
-        description=body.description,
-        type=body.type,
-        knowledge_status=body.knowledge_status,
-        involved_entities=involved,
-        location_id=location_id,
-    )
+def update_event(event_id: str, body: EventBody, db: DbSession = Depends(get_session)) -> dict:
+    event = _event(db, event_id)
+    try:
+        write_event_update(db, event=event, spec=event_spec(body), changed_by=CHANGED_BY)
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(422, str(exc)) from exc
     db.commit()
     db.refresh(event)
     return _event_dict(event, db)
+
+
+__all__ = ["EVENT_FIELDS", "EventBody", "_event_dict", "create_event", "get_event", "list_events", "update_event"]
diff --git a/src/world_engine/cockpit/mutations.py b/src/world_engine/cockpit/mutations.py
index 120f22d..012a4c7 100644
--- a/src/world_engine/cockpit/mutations.py
+++ b/src/world_engine/cockpit/mutations.py
@@ -31,6 +31,7 @@ from typing import Any, Optional
 
 from sqlmodel import Session, select
 
+from ..event_payloads import provenance, spec_from_payload
 from ..fact_refs import find_held, knowledge_key
 from ..gathering import close_open_memberships
 from ..ledger import get_balance as _get_balance
@@ -691,41 +692,19 @@ def _mutation_apply_npc_move(mut: ProposedMutation, payload: dict, db: Session)
 # ── event_creation (TICKET-0017, BRIEF-0017-a) ──────────────────────────────
 
 def _mutation_apply_event_creation(mut: ProposedMutation, payload: dict, db: Session) -> Optional[str]:
-    """Tolerant of BOTH payload generations — the scope-level tick's closed
-    shape and the analyzer's minimal conversation-sourced shape.
-    knowledge_status clamped to secret|public|confirmed (defense in depth).
-    A present location_id must resolve to an ACTIVE location entity of this
-    world, else "Needs attention", nothing written."""
-    title = payload.get("title")
-    if not title:
+    """Since TICKET-0114 (BRIEF-0114-C): the payload -- typed (the play
+    analyzer) or untyped (the world tick, earlier proposals) -- is read into
+    an `EventSpec` (`event_payloads.spec_from_payload`) and written by the
+    journal's one writer, its fact, scopes and participants' knowledge with
+    it. Any refusal of the writer is "Needs attention", nothing written."""
+    if not payload.get("title"):
         return "event_creation: payload must contain title"
-
-    knowledge_status = payload.get("knowledge_status")
-    if knowledge_status not in ("secret", "public", "confirmed"):
-        knowledge_status = "secret"
-
-    location_id = payload.get("location_id")
-    if location_id:
-        location_entity = db.get(Entity, location_id)
-        if (
-            location_entity is None
-            or location_entity.type != "location"
-            or location_entity.status != "active"
-            or location_entity.world_id != mut.world_id
-        ):
-            return f"event_creation: location {location_id!r} is not an active location in this world"
-
-    write_event(
-        db,
-        world_id=mut.world_id,
-        title=str(title),
-        description=payload.get("description"),
-        type=payload.get("type"),
-        knowledge_status=knowledge_status,
-        involved_entities=payload.get("involved_entities"),
-        location_id=location_id,
-        mutation_id=mut.id,
-    )
+    session_id, batch_id = provenance(db, mut)
+    try:
+        spec = spec_from_payload(db, mut.world_id, payload, session_id=session_id, batch_id=batch_id)
+        write_event(db, world_id=mut.world_id, spec=spec, created_by=f"mutation:{mut.id}")
+    except ValueError as exc:
+        return f"event_creation: {exc}"
     return None
 
 
diff --git a/src/world_engine/event_payloads.py b/src/world_engine/event_payloads.py
new file mode 100644
index 0000000..c066d48
--- /dev/null
+++ b/src/world_engine/event_payloads.py
@@ -0,0 +1,93 @@
+"""A model's event proposal, read into the journal's spec (TICKET-0114,
+BRIEF-0114-C; decisions D1, E1, I2, N1 and O1 of the conditions series).
+
+`_apply_mutation`'s `event_creation` branch applies what the creator
+approved through `writes.events.write_event`; this module turns the
+proposal's payload into that writer's `EventSpec`. Two payload shapes:
+
+- typed (the play analyzer since BRIEF-0114-H): `type_id`, `participants`
+  (`role_id` with an `entity_id` or a `sorte_id`, and `secret`),
+  `quantity`, `location_id`. Its scopes are its type's (W1).
+- untyped (the world tick until TICKET-0119, and every proposal written
+  before): `type` (a former category), `involved_entities`,
+  `knowledge_status`, `location_id`. It is typed by its domain
+  (`writes.event_types.ensure_domain_type`, N1), its entities take the one
+  role « Impliqué » when that role accepts their type (an entity it does
+  not accept is left out, never forced), and it is known by everyone at
+  `knows` when `public` or `confirmed`, by its participants only when
+  `secret` -- the meaning `knowledge_status` had (O1).
+
+Where it happened in time (E1): `provenance` reads the session of the
+mutation's conversation, or the session and day of its declared action; a
+tick proposal has neither.
+
+Reads, and writes only through `ensure_domain_type` (an untyped proposal
+whose domain has no type yet makes it, inside the applier's savepoint).
+"""
+
+from __future__ import annotations
+
+from typing import Optional
+
+from sqlmodel import Session
+
+from .event_vocab import role_accepts, type_view
+from .models import Conversation, Entity, PassPlay, ProposedMutation
+from .writes.event_types import ensure_domain_type
+from .writes.events import EventScopeSpec, EventSpec, ParticipantSpec
+
+PUBLIC_STATUSES: tuple[str, ...] = ("public", "confirmed")
+PUBLIC_LEVEL = "knows"
+
+
+def provenance(db: Session, mut: ProposedMutation) -> tuple[Optional[str], Optional[str]]:
+    """(session_id, batch_id) of the mutation's source, when it has one."""
+    if mut.conversation_id:
+        conversation = db.get(Conversation, mut.conversation_id)
+        return (conversation.session_id if conversation is not None else None), None
+    if mut.pass_play_id:
+        pass_play = db.get(PassPlay, mut.pass_play_id)
+        if pass_play is not None:
+            return pass_play.session_id, pass_play.batch_id
+    return None, None
+
+
+def _typed(payload: dict) -> EventSpec:
+    participants = tuple(
+        ParticipantSpec(role_id=str(p.get("role_id") or ""), entity_id=p.get("entity_id") or None,
+                        sorte_id=p.get("sorte_id") or None,
+                        secret=p.get("secret") if isinstance(p.get("secret"), bool) else None)
+        for p in (payload.get("participants") or []) if isinstance(p, dict)
+    )
+    quantity = payload.get("quantity")
+    return EventSpec(
+        type_id=str(payload.get("type_id")), title=str(payload.get("title") or ""),
+        description=payload.get("description"), location_id=payload.get("location_id") or None,
+        quantity=quantity if isinstance(quantity, int) and not isinstance(quantity, bool) else None,
+        participants=participants,
+    )
+
+
+def _untyped(db: Session, world_id: str, payload: dict) -> EventSpec:
+    event_type = ensure_domain_type(db, world_id=world_id, domain=payload.get("type"))
+    view = type_view(db, event_type.id)
+    role = view.active_roles()[0]
+    participants = []
+    for entity_id in payload.get("involved_entities") or []:
+        entity = db.get(Entity, entity_id) if isinstance(entity_id, str) else None
+        if entity is not None and entity.world_id == world_id and role_accepts(role, entity.type) \
+                and all(p.entity_id != entity.id for p in participants):
+            participants.append(ParticipantSpec(role_id=role.id, entity_id=entity.id))
+    public = payload.get("knowledge_status") in PUBLIC_STATUSES
+    return EventSpec(
+        type_id=event_type.id, title=str(payload.get("title") or ""), description=payload.get("description"),
+        location_id=payload.get("location_id") or None, participants=tuple(participants),
+        scopes=(EventScopeSpec("world", None, PUBLIC_LEVEL),) if public else (),
+    )
+
+
+def spec_from_payload(db: Session, world_id: str, payload: dict, *, session_id: Optional[str] = None,
+                      batch_id: Optional[str] = None) -> EventSpec:
+    """The `EventSpec` of one `event_creation` payload, typed or not."""
+    spec = _typed(payload) if payload.get("type_id") else _untyped(db, world_id, payload)
+    return EventSpec(**{**spec.__dict__, "session_id": session_id, "batch_id": batch_id})
diff --git a/src/world_engine/writes/__init__.py b/src/world_engine/writes/__init__.py
index 70c5442..f94e864 100644
--- a/src/world_engine/writes/__init__.py
+++ b/src/world_engine/writes/__init__.py
@@ -34,7 +34,10 @@ Layout, by canon domain:
                           `world_law`, `obstacle`/`obstacle_vertex`).
     goals_agendas.py    — `npc_goal`/`goal_prerequisite`/`agenda`/
                           `agenda_step`/`goal_agenda_link`.
-    events.py           — `event`.
+    events.py           — the event journal: `event`, `event_participant`,
+                          its fact, scopes and participants' knowledge:
+                          `clean_event`, `write_event`, `write_event_update`
+                          (TICKET-0114, BRIEF-0114-C).
     prompts.py          — `prompt_version`/`prompt_variable` (non-canon;
                           moved for module hygiene, not policy).
     pipeline.py         — `batch`/`pass_play` (TICKET-0075, BRIEF-0075-a).
@@ -98,7 +101,7 @@ from .config import (
     write_npc_schedule,
     write_world_laws,
 )
-from .events import write_event, write_event_update
+from .events import EventScopeSpec, EventSpec, ParticipantSpec, clean_event, event_fact_text, write_event, write_event_update
 from .facts import (
     attach_participants,
     create_fact,
diff --git a/src/world_engine/writes/events.py b/src/world_engine/writes/events.py
index 619fd55..5516f63 100644
--- a/src/world_engine/writes/events.py
+++ b/src/world_engine/writes/events.py
@@ -1,98 +1,325 @@
-"""`event` canon-write chokepoints (TICKET-0028, BRIEF-0028-b — decomposed
-from `writes.py`). Pure moves, no logic change — neither function was
-baselined.
-
-- `write_event(...)`        : insert one `event` row. The ONLY place
-  `Event(` is constructed in gameplay code (TICKET-0017, BRIEF-0017-a).
-- `write_event_update(...)`  : creator-CRUD-only writer for an existing
-  `event` row (TICKET-0022, BRIEF-0022-a). `_apply_mutation` never calls
-  this. Together `write_event` and `write_event_update` are the complete
-  set of `event` writers.
+"""`event` canon-write chokepoint -- the event journal (TICKET-0114,
+BRIEF-0114-C; decisions F1, D1, E1, K-a, V1, W1 and X1 of the conditions
+series). The one writer of `event` and `event_participant`.
+
+- `clean_event(db, world_id, spec, event=None)` : an event as it will be
+  written, or `ValueError`. Its type is the world's (active, for a new
+  event); its title is not empty; its place an active location of the
+  world; a quantity only when its type counts, at least 1; each participant
+  fills an active role of its type with an entity of a type the role
+  accepts, or a sorte when the role accepts one, never twice the same; a
+  participant's `secret` is its own (X1), the type's default when unsaid,
+  and always False for a player character (INV-07). Its scopes are the
+  type's when unsaid (W1): `location` its place, `world`, `rencontre` each
+  entity in the role, `faction` each faction in the role -- the highest
+  level kept per scope. On an existing event (a correction), the type
+  stays, and no participant is taken away. Writes nothing.
+- `write_event(db, *, world_id, spec, created_by)` : the event, its
+  participants, its fact (`fact.event_id`, facet `evenement`, its title then
+  its description -- `event_fact_text`), the fact's scopes
+  (`fact_default`) and one `knowledge` row at `knows` for each character
+  taking part (K-a), secret as said. Returns the event, flushed.
+- `write_event_update(db, *, event, spec, changed_by)` : a correction from
+  the journal -- title, description, place, quantity; a participant added;
+  a participant's secret changed (his knowledge row); the scopes replaced
+  whole. The fact's text is rewritten as a `correction` when it changed.
+
+The two producers -- the creator's journal (`cockpit/crud/events.py`) and
+`_apply_mutation`'s `event_creation` (a model's proposal, reviewed by the
+creator, D1) -- both call `write_event`; `event_payloads.py` turns a
+proposal's payload into an `EventSpec`. None of these functions commits.
 """
 
 from __future__ import annotations
 
+from dataclasses import dataclass, replace
 from typing import Optional
 
 from sqlalchemy import text
-from sqlmodel import Session
-
-from ..models import Event, EventEntity
-
-
-def write_event(
-    db: Session,
-    *,
-    world_id: str,
-    title: str,
-    description: Optional[str] = None,
-    type: Optional[str] = None,
-    knowledge_status: Optional[str] = None,
-    involved_entities: Optional[list] = None,
-    location_id: Optional[str] = None,
-    mutation_id: Optional[str] = None,
-) -> Event:
-    """Insert one `event` row. Caller adds nothing else — this function
-    calls `db.add`. Both producers — the scope-level tick call and the
-    analyzer's dormant conversation-sourced channel — route through
-    `_apply_mutation`'s `event_creation` branch, which calls this.
-
-    `knowledge_status=None` lets the column's `server_default` 'secret'
-    apply — the analyzer's minimal payload shape carries no status.
-    `occurred_at` stays None (in-fiction time unknown); `recorded_at` is the
-    row's own `_created_ts` default. `session_id`/`batch_id` stay None:
-    neither a play-session artifact nor a pass-play batch — the mutation
-    row's `tick_id`/`conversation_id` is the provenance anchor.
-    `mutation_id` is accepted only for call-site symmetry with the other
-    `_apply_mutation` writers (no `change_history` column on this table) and
-    is not otherwise used here. `involved_entities` (TICKET-0025,
-    BRIEF-0025-c: relationalized) inserts `event_entity` rows after the
-    event row — a fresh event has no prior rows to replace.
-    """
-    del mutation_id
-    event = Event(
-        world_id=world_id,
-        title=title,
-        description=description,
-        type=type,
-        location_id=location_id,
-    )
-    if knowledge_status is not None:
-        event.knowledge_status = knowledge_status
+from sqlmodel import Session, select
+
+from ..event_vocab import EventTypeView, role_accepts, type_view
+from ..models import (
+    Character,
+    Entity,
+    Event,
+    EventParticipant,
+    EventSorte,
+    Fact,
+    Knowledge,
+)
+from .facts import create_fact, create_fact_default, update_typed_fact_content
+from .knowledge import knowledge_level_rank, write_knowledge
+
+# K-a: what a participant holds of the event, and from where.
+PARTICIPANT_LEVEL = "knows"
+EVENT_SOURCE = "evenement"
+MAX_TITLE_CHARS = 200
+# The fact_default scope types an event's scope may name (`fact_default`'s CHECK).
+SCOPE_TYPES: tuple[str, ...] = ("world", "location", "rencontre", "faction")
+SCOPE_LEVELS: tuple[str, ...] = ("rumor", "suspicious", "partial", "knows", "fully_understands")
+
+
+@dataclass(frozen=True)
+class ParticipantSpec:
+    """One participant: a role of the type, an entity or a sorte, and for an
+    entity whether he keeps the event secret (None: the type's default)."""
+    role_id: str
+    entity_id: Optional[str] = None
+    sorte_id: Optional[str] = None
+    secret: Optional[bool] = None
+
+
+@dataclass(frozen=True)
+class EventScopeSpec:
+    """One concrete scope of an event's fact: a `fact_default` row."""
+    scope_type: str
+    scope_id: Optional[str]
+    level: str
+
+
+@dataclass(frozen=True)
+class EventSpec:
+    type_id: str
+    title: str
+    description: Optional[str] = None
+    location_id: Optional[str] = None
+    quantity: Optional[int] = None
+    participants: tuple[ParticipantSpec, ...] = ()
+    scopes: Optional[tuple[EventScopeSpec, ...]] = None  # None: the type's (W1)
+    session_id: Optional[str] = None
+    batch_id: Optional[str] = None
+
+
+def event_fact_text(title: str, description: Optional[str]) -> str:
+    """The text of an event's fact: its title, then its description."""
+    description = (description or "").strip()
+    return f"{title} — {description}" if description else title
+
+
+# --- cleaning ------------------------------------------------------------------
+
+def _clean_type(db: Session, world_id: str, type_id: str, event: Optional[Event]) -> EventTypeView:
+    view = type_view(db, type_id)
+    if view is None or view.world_id != world_id:
+        raise ValueError(f"unknown event type {type_id!r}")
+    if event is not None and event.type_id != type_id:
+        raise ValueError("an event's type does not change; write another event")
+    if event is None and view.status != "active":
+        raise ValueError(f"« {view.name} » is retired")
+    return view
+
+
+def _clean_location(db: Session, world_id: str, location_id: Optional[str]) -> Optional[str]:
+    if not location_id:
+        return None
+    place = db.get(Entity, location_id)
+    if place is None or place.type != "location" or place.status != "active" or place.world_id != world_id:
+        raise ValueError(f"{location_id!r} is not an active location of this world")
+    return location_id
+
+
+def _clean_quantity(view: EventTypeView, quantity: object) -> Optional[int]:
+    if quantity is None:
+        return None
+    if not view.counts_quantity:
+        raise ValueError(f"« {view.name} » counts no quantity")
+    if not isinstance(quantity, int) or isinstance(quantity, bool) or quantity < 1:
+        raise ValueError("a quantity is an integer of 1 or more")
+    return quantity
+
+
+def _is_player(db: Session, entity_id: str) -> bool:
+    character = db.get(Character, entity_id)
+    return character is not None and character.character_type == "player"
+
+
+def _clean_participant(db: Session, world_id: str, view: EventTypeView, p: ParticipantSpec) -> ParticipantSpec:
+    role = view.role(p.role_id)
+    if role is None or role.status != "active":
+        raise ValueError(f"{p.role_id!r} is no role of « {view.name} »")
+    if (p.entity_id is None) == (p.sorte_id is None):
+        raise ValueError(f"the role « {role.name} » is filled by an entity or a sorte, exactly one")
+    if p.sorte_id is not None:
+        sorte = db.get(EventSorte, p.sorte_id)
+        if sorte is None or sorte.world_id != world_id or sorte.status != "active":
+            raise ValueError(f"unknown sorte {p.sorte_id!r}")
+        if not role.accepts_sorte:
+            raise ValueError(f"the role « {role.name} » takes no sorte")
+        return ParticipantSpec(role_id=role.id, sorte_id=sorte.id)
+    entity = db.get(Entity, p.entity_id)
+    if entity is None or entity.world_id != world_id:
+        raise ValueError(f"unknown entity {p.entity_id!r}")
+    if not role_accepts(role, entity.type):
+        raise ValueError(f"the role « {role.name} » takes no {entity.type}")
+    secret = view.participants_secret if p.secret is None else bool(p.secret)
+    return ParticipantSpec(role_id=role.id, entity_id=entity.id, secret=False if _is_player(db, entity.id) else secret)
+
+
+def _key(p: ParticipantSpec) -> tuple:
+    return (p.role_id, p.entity_id, p.sorte_id)
+
+
+def _clean_participants(db: Session, world_id: str, view: EventTypeView, participants) -> tuple[ParticipantSpec, ...]:
+    cleaned = tuple(_clean_participant(db, world_id, view, p) for p in participants)
+    keys = [_key(p) for p in cleaned]
+    if len(set(keys)) != len(keys):
+        raise ValueError("a participant is named twice in one role")
+    return cleaned
+
+
+def _type_scopes(db: Session, view: EventTypeView, location_id: Optional[str],
+                 participants: tuple[ParticipantSpec, ...]) -> tuple[EventScopeSpec, ...]:
+    """The type's scopes made concrete for one event (W1)."""
+    found: list[EventScopeSpec] = []
+    for scope in view.scopes:
+        if scope.kind == "world":
+            found.append(EventScopeSpec("world", None, scope.level))
+        elif scope.kind == "location" and location_id:
+            found.append(EventScopeSpec("location", location_id, scope.level))
+        elif scope.kind in ("rencontre", "faction"):
+            for p in participants:
+                entity = db.get(Entity, p.entity_id) if p.entity_id else None
+                if p.role_id == scope.role_id and entity is not None and (
+                        scope.kind == "rencontre" or entity.type == "faction"):
+                    found.append(EventScopeSpec(scope.kind, entity.id, scope.level))
+    return _merged(found)
+
+
+def _merged(scopes) -> tuple[EventScopeSpec, ...]:
+    """One scope per (type, id), the highest level kept."""
+    best: dict[tuple, EventScopeSpec] = {}
+    for scope in scopes:
+        key = (scope.scope_type, scope.scope_id)
+        if key not in best or knowledge_level_rank(scope.level) > knowledge_level_rank(best[key].level):
+            best[key] = scope
+    return tuple(best.values())
+
+
+_SCOPE_ENTITY_TYPE = {"location": "location", "faction": "faction"}
+
+
+def _clean_scope(db: Session, world_id: str, scope: EventScopeSpec) -> EventScopeSpec:
+    if scope.scope_type not in SCOPE_TYPES:
+        raise ValueError(f"unknown scope {scope.scope_type!r}")
+    if scope.level not in SCOPE_LEVELS:
+        raise ValueError(f"a scope's level is one the knower holds, not {scope.level!r}")
+    if scope.scope_type == "world":
+        if scope.scope_id is not None:
+            raise ValueError("a world scope names nothing")
+        return scope
+    entity = db.get(Entity, scope.scope_id) if scope.scope_id else None
+    wanted = _SCOPE_ENTITY_TYPE.get(scope.scope_type)
+    if entity is None or entity.world_id != world_id or (wanted and entity.type != wanted):
+        raise ValueError(f"a {scope.scope_type} scope names {scope.scope_id!r}, not one of this world")
+    return scope
+
+
+def clean_event(db: Session, world_id: str, spec: EventSpec, event: Optional[Event] = None) -> EventSpec:
+    """`spec` as it will be written, its scopes made concrete; raises
+    `ValueError` on any violation. Writes nothing."""
+    view = _clean_type(db, world_id, spec.type_id, event)
+    title = " ".join(str(spec.title or "").split())
+    if not title:
+        raise ValueError("an event needs a title")
+    if len(title) > MAX_TITLE_CHARS:
+        raise ValueError(f"an event's title has at most {MAX_TITLE_CHARS} characters")
+    location_id = _clean_location(db, world_id, spec.location_id)
+    participants = _clean_participants(db, world_id, view, spec.participants)
+    if event is not None:
+        kept = {(p.role_id, p.entity_id, p.sorte_id) for p in participants}
+        for row in _participant_rows(db, event.id):
+            if (row.role_id, row.entity_id, row.sorte_id) not in kept:
+                raise ValueError("a participant stays: an event's participants are never taken away")
+    if spec.scopes is None:
+        scopes = _type_scopes(db, view, location_id, participants)
+    else:
+        scopes = _merged(_clean_scope(db, world_id, s) for s in spec.scopes)
+    description = (spec.description or "").strip() or None
+    return replace(spec, title=title, description=description, location_id=location_id,
+                   quantity=_clean_quantity(view, spec.quantity), participants=participants, scopes=scopes)
+
+
+# --- writing -------------------------------------------------------------------
+
+def _participant_rows(db: Session, event_id: str) -> list[EventParticipant]:
+    return list(db.exec(select(EventParticipant).where(EventParticipant.event_id == event_id)
+                        .order_by(EventParticipant.position, EventParticipant.id)).all())
+
+
+def _knows(db: Session, entity_id: str, fact_id: str, secret: bool, changed_by: str) -> None:
+    """K-a: a character taking part knows the event -- his row written at
+    `knows`, or raised to it, his `is_secret` set as said (X1)."""
+    if db.get(Character, entity_id) is None:
+        return
+    row = db.exec(select(Knowledge).where(Knowledge.entity_id == entity_id, Knowledge.fact_id == fact_id)).first()
+    if row is None:
+        write_knowledge(db, entity_id=entity_id, fact_id=fact_id, level=PARTICIPANT_LEVEL, is_secret=secret,
+                        source=EVENT_SOURCE, changed_by=changed_by)
+        return
+    level = row.level if knowledge_level_rank(row.level) >= knowledge_level_rank(PARTICIPANT_LEVEL) \
+        else PARTICIPANT_LEVEL
+    write_knowledge(db, knowledge_id=row.id, level=level, content=row.content_raw, source=row.source,
+                    is_incorrect=row.is_incorrect, is_secret=secret, share_threshold=row.share_threshold,
+                    session_id=row.session_id, changed_by=changed_by)
+
+
+def _add_participants(db: Session, event: Event, participants, fact_id: str, changed_by: str) -> None:
+    rows = _participant_rows(db, event.id)
+    have = {(r.role_id, r.entity_id, r.sorte_id) for r in rows}
+    position = len(rows)
+    for p in participants:
+        if _key(p) not in have:
+            db.add(EventParticipant(world_id=event.world_id, event_id=event.id, role_id=p.role_id,
+                                    entity_id=p.entity_id, sorte_id=p.sorte_id, position=position))
+            position += 1
+        if p.entity_id is not None:
+            _knows(db, p.entity_id, fact_id, bool(p.secret), changed_by)
+
+
+def _write_scopes(db: Session, world_id: str, fact_id: str, scopes, created_by: str) -> None:
+    """The fact's scopes replaced whole (the full-replace shape)."""
+    db.execute(text("DELETE FROM fact_default WHERE fact_id = :fid"), {"fid": fact_id})
+    for scope in scopes:
+        create_fact_default(db, world_id=world_id, fact_id=fact_id, scope_type=scope.scope_type,
+                            scope_id=scope.scope_id, level=scope.level, created_by=created_by)
+
+
+def write_event(db: Session, *, world_id: str, spec: EventSpec, created_by: str) -> Event:
+    """C-01: the event, its participants, its fact, the fact's scopes and
+    the participants' knowledge, from a cleaned spec."""
+    clean = clean_event(db, world_id, spec)
+    event = Event(world_id=world_id, type_id=clean.type_id, title=clean.title, description=clean.description,
+                  location_id=clean.location_id, quantity=clean.quantity, session_id=clean.session_id,
+                  batch_id=clean.batch_id)
     db.add(event)
-    for entity_id in (involved_entities or []):
-        db.add(EventEntity(event_id=event.id, entity_id=entity_id))
+    db.flush()
+    fact = create_fact(db, world_id=world_id, content=event_fact_text(clean.title, clean.description),
+                       created_by=created_by, facet="evenement", event_id=event.id)
+    db.flush()
+    _add_participants(db, event, clean.participants, fact.id, created_by)
+    _write_scopes(db, world_id, fact.id, clean.scopes, created_by)
+    db.flush()
     return event
 
 
-def write_event_update(
-    db: Session,
-    *,
-    event: Event,
-    title: str,
-    description: Optional[str] = None,
-    type: Optional[str] = None,
-    knowledge_status: str,
-    involved_entities: Optional[list] = None,
-    location_id: Optional[str] = None,
-) -> Event:
-    """Creator-CRUD-only writer for an existing `event` row (TICKET-0022,
-    BRIEF-0022-a). Sets exactly the six fields listed above and calls
-    `db.add`. Does NOT touch `recorded_at`, `occurred_at`,
-    `has_magic_impact`, `consequences`, `session_id`, `batch_id` — those
-    keep whatever they had. No `change_history` append: the table has no
-    such column — a known, accepted gap, not an oversight.
-    `involved_entities` (TICKET-0025, BRIEF-0025-c: relationalized)
-    full-replaces this event's `event_entity` rows — the chips editor's
-    replace contract.
-    """
-    event.title = title
-    event.description = description
-    event.type = type
-    event.knowledge_status = knowledge_status
-    event.location_id = location_id
+def event_fact(db: Session, event_id: str) -> Optional[Fact]:
+    return db.exec(select(Fact).where(Fact.event_id == event_id)).first()
+
+
+def write_event_update(db: Session, *, event: Event, spec: EventSpec, changed_by: str) -> Event:
+    """C-02: a creator's correction of one event, from the journal."""
+    clean = clean_event(db, event.world_id, spec, event)
+    event.title, event.description = clean.title, clean.description
+    event.location_id, event.quantity = clean.location_id, clean.quantity
     db.add(event)
-    db.execute(text("DELETE FROM event_entity WHERE event_id = :event_id"), {"event_id": event.id})
-    for entity_id in (involved_entities or []):
-        db.add(EventEntity(event_id=event.id, entity_id=entity_id))
+    fact = event_fact(db, event.id)
+    if fact is None:
+        raise ValueError(f"event {event.id!r} has no fact")
+    content = event_fact_text(clean.title, clean.description)
+    if fact.content_raw != content:
+        update_typed_fact_content(db, fact=fact, content=content, changed_by=changed_by, kind="correction")
+    _add_participants(db, event, clean.participants, fact.id, changed_by)
+    _write_scopes(db, event.world_id, fact.id, clean.scopes, changed_by)
+    db.flush()
     return event
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 86cec9a..15235ae 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19306,6 +19306,44 @@ cards.
 sortes need another), T2 (types inside the « Événements » tab: the
 vocabulary split from the states it sits beside).
 
+## AN EVENT IS WRITTEN WITH ITS PARTICIPANTS, ITS FACT AND WHO LEARNS IT (TICKET-0114) -- ONE WRITER FOR THE JOURNAL AND FOR AN APPROVED PROPOSAL, TYPED OR NOT (BRIEF-0114-c, no schema change)
+
+**One writer.** `writes/events.py` writes an event and everything that
+makes it known: its participants by role (`event_participant`, V1), its fact
+(`fact.event_id`, facet `evenement`, its title then its description), the
+fact's scopes (`fact_default`: the type's made concrete -- its place, the
+world, the acquaintances of a role's entity, a faction filling a role --
+unless the event says its own, W1) and one `knowledge` row at `knows` for
+each character taking part (K-a). The creator's journal
+(`cockpit/crud/events.py`) and `_apply_mutation`'s `event_creation` both
+call it; `event_payloads.py` turns a proposal's payload into its spec.
+
+**X1: secrecy belongs to each participant.** The type gives the default; each
+character's own knowledge row carries his `is_secret`, so one participant
+may speak of what the others keep. A player character's row is never
+secret (INV-07). Who learns an event is a separate matter (its scopes):
+a secret pact may still be seen by whoever passes through the tavern.
+
+**A correction keeps what happened.** The journal corrects an event's
+title, description, place and quantity -- its fact's text rewritten as a
+`correction`, the former text in its history --, adds a participant, sets
+a participant's secret, and replaces its scopes whole (`_write_scopes`,
+named in `single_canon_write.py`). Its type does not change and no
+participant is taken away: write another event. A retraction empties its
+scopes; the row is never deleted (C3).
+
+**The untyped proposal (N1, O1).** The world tick, and every proposal
+written before, still sends a former category, `involved_entities` and a
+`knowledge_status`: it is typed by its domain (`ensure_domain_type`, made
+for the world when missing), its entities take the role « Impliqué » when
+it accepts them, and `public`/`confirmed` means known by everyone at
+`knows`, `secret` by its participants only -- the meaning the column had.
+TICKET-0119 makes the tick propose typed events.
+
+**E1.** An event keeps the session, and the day, it was proposed in (the
+mutation's conversation or declared action): the calendar of TICKET-0120
+will place every event on it without guessing.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index 8e89818..d736dc1 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -92,6 +92,9 @@ src/world_engine/writes/event_types.py::set_sorte_status       event_sorte
 src/world_engine/writes/schema.py::create_entity_type          entity_type entity_type_history
 src/world_engine/writes/events.py::write_event                 event
 src/world_engine/writes/events.py::write_event_update           event
+# TICKET-0114, BRIEF-0114-C: the journal -- _add_participants adds an event's participants (never takes one away; their knowledge goes through write_knowledge, allow-listed above), _write_scopes replaces an event's fact's scopes whole (the full-replace shape; each row through create_fact_default). Creator CRUD and _apply_mutation's event_creation.
+src/world_engine/writes/events.py::_add_participants           event_participant
+src/world_engine/writes/events.py::_write_scopes               fact_default
 src/world_engine/writes/goals_agendas.py::write_agenda         agenda
 src/world_engine/writes/goals_agendas.py::write_agenda_step    agenda_step
 src/world_engine/writes/goals_agendas.py::write_agenda_step_status agenda_step
diff --git a/tooling/verify/checks/event_writes.py b/tooling/verify/checks/event_writes.py
new file mode 100644
index 0000000..a612e64
--- /dev/null
+++ b/tooling/verify/checks/event_writes.py
@@ -0,0 +1,445 @@
+"""G1 check for TICKET-0114 -- the event journal's writer: an event, its participants by role, its fact, who learns it.
+
+BRIEF-0114-C's rules (`event_journal.py` holds BRIEF-0114-A/B's).
+
+EC1 -- the writer (fixture). `write_event` writes « Brakk tue 3 loups dans
+   la Forêt » (type « Tuer », counting; Brakk as `tueur`, the sorte « Loup »
+   as `victime`): one event row with its type and quantity, two
+   participants in order, one fact on it with facet `evenement` and the
+   text « title — description », the type's `location` scope made the
+   Forêt at `rumor` (its `rencontre` scope on the victim makes nothing: a
+   sorte has met no one), and Brakk's knowledge row at `knows`, not
+   secret. A « Pacte » (participants secret by default, a `faction` scope
+   on its role) between an NPC, the PC and a faction: the NPC's row is
+   secret, the PC's never (INV-07), even asked; the faction is a scope at
+   `knows`, and holds no knowledge row. A spec's own `scopes` replace the
+   type's; an empty tuple means no one.
+EC2 -- refusals (fixture), each with no row written: an unknown type, a
+   retired type, an empty title, a place that is not a location, a quantity
+   on a type that counts none, a quantity of 0, a role of another type, an
+   entity of a type the role does not accept, a sorte in a role that takes
+   none, a role filled by both an entity and a sorte, one participant twice
+   in one role, an unknown scope, a `world` scope naming an entity, a
+   `faction` scope naming a character.
+EC3 -- a correction (fixture). `write_event_update` rewrites the title: the
+   fact's text follows, its history holds the former text with the kind
+   `correction`; a participant added gets his knowledge row; a participant
+   made secret has his row secret; the scopes are replaced whole; taking a
+   participant away, or changing the type, is refused with no row changed.
+EC4 -- the approved proposal (fixture, `_apply_mutation`). A typed
+   `event_creation` payload writes its event, typed, with its participants;
+   an untyped one (`type: 'social'`, `involved_entities`, `knowledge_status:
+   'public'`) is typed « Social » (made for the world), its entities take
+   the role « Impliqué », and its fact has a `world` scope at `knows`; a
+   `secret` one has none. A payload whose role is unknown returns an
+   `event_creation:` error and writes no event.
+EC5 -- the routes (fixture, route functions). `create_event` answers the
+   event with its type, participants (role, name, secret) and scopes;
+   `update_event` corrects it; a refusal answers 422 and writes nothing; an
+   unknown event is 404.
+EC6 -- the sheet (static). `EVENT_FIELDS` names `title`, `description`,
+   `location_id` and nothing else; `crud/events.py` and
+   `cockpit/mutations.py`'s `event_creation` applier name no
+   `knowledge_status` and no `EventEntity`; `Evenements.svelte` renders the
+   type select `event-f-type_id`, the quantity, each role's participants with
+   their secret, and the scopes; `Sheet.svelte` sends `eventDraftBody()`;
+   `eventDraft.svelte.js` exports `eventDraftBody` and never removes a
+   `saved` participant.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import ast
+import os
+import pathlib
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+FRONT = ROOT / "frontend" / "src" / "creation"
+
+FAILURES: list[str] = []
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _fresh_db() -> None:
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
+
+
+def _fixture(engine) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.models import Character, Entity, Faction, Location, World
+    from world_engine.writes.event_types import (
+        EventTypeSpec, RoleSpec, ScopeSpec, set_event_type_status, write_event_type, write_sorte,
+    )
+
+    with Session(engine) as db:
+        world = World(name="Journal", is_active=True)
+        db.add(world)
+        db.flush()
+        ids = {"world": world.id}
+        for key, kind, name in (("brakk", "character", "Brakk"), ("ysa", "character", "Ysa"),
+                                ("mira", "character", "Mira"), ("foret", "location", "Forêt"),
+                                ("guilde", "faction", "Guilde")):
+            entity = Entity(world_id=world.id, type=kind, name=name)
+            db.add(entity)
+            db.flush()
+            ids[key] = entity.id
+            if kind == "character":
+                db.add(Character(id=entity.id, world_id=world.id,
+                                 character_type="player" if key == "mira" else "npc"))
+            elif kind == "location":
+                db.add(Location(id=entity.id))
+            else:
+                db.add(Faction(id=entity.id))
+        ids["loup"] = write_sorte(db, world_id=world.id, name="Loup").id
+        tuer = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
+            name="Tuer", domain="military", counts_quantity=True,
+            roles=(RoleSpec("tueur", ("character",)), RoleSpec("victime", ("character",), accepts_sorte=True)),
+            scopes=(ScopeSpec("location", level="rumor"), ScopeSpec("rencontre", role="victime"))))
+        pacte = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
+            name="Pacte", domain="political", participants_secret=True,
+            roles=(RoleSpec("partie", ("character", "faction")),),
+            scopes=(ScopeSpec("faction", role="partie"),)))
+        vieux = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
+            name="Vieux", roles=(RoleSpec("x", ("character",)),)))
+        set_event_type_status(db, world_id=world.id, type_id=vieux.id, status="retired")
+        db.flush()
+        from world_engine.event_vocab import type_view
+        ids["tuer"], ids["pacte"], ids["vieux"] = tuer.id, pacte.id, vieux.id
+        tv, pv = type_view(db, tuer.id), type_view(db, pacte.id)
+        ids["tueur"], ids["victime"], ids["partie"] = tv.roles[0].id, tv.roles[1].id, pv.roles[0].id
+        db.commit()
+    return ids
+
+
+def _counts(db) -> tuple[int, ...]:
+    from sqlmodel import func, select
+
+    from world_engine import models
+
+    return tuple(db.exec(select(func.count()).select_from(m)).one() for m in (
+        models.Event, models.EventParticipant, models.Fact, models.FactDefault, models.Knowledge))
+
+
+def _refused(db, label: str, rule: str, call) -> None:
+    before = _counts(db)
+    try:
+        call()
+    except ValueError:
+        db.rollback()
+        if _counts(db) != before:
+            fail(f"{rule}: {label} was refused after writing a row")
+        return
+    db.rollback()
+    fail(f"{rule}: {label} was accepted")
+
+
+def _knowledge(db, entity_id: str, fact_id: str):
+    from sqlmodel import select
+
+    from world_engine.models import Knowledge
+
+    return db.exec(select(Knowledge).where(Knowledge.entity_id == entity_id, Knowledge.fact_id == fact_id)).first()
+
+
+def _scopes(db, fact_id: str) -> list:
+    from sqlmodel import select
+
+    from world_engine.models import FactDefault
+
+    return sorted((r.scope_type, r.scope_id, r.level) for r in db.exec(
+        select(FactDefault).where(FactDefault.fact_id == fact_id)).all())
+
+
+def _hunt(ids, **fields):
+    from world_engine.writes.events import EventSpec, ParticipantSpec
+
+    base = dict(type_id=ids["tuer"], title="Brakk tue 3 loups", description="Dans la Forêt.",
+                location_id=ids["foret"], quantity=3,
+                participants=(ParticipantSpec(ids["tueur"], entity_id=ids["brakk"]),
+                              ParticipantSpec(ids["victime"], sorte_id=ids["loup"])))
+    base.update(fields)
+    return EventSpec(**base)
+
+
+def check_ec1(engine, ids: dict) -> dict:
+    from sqlmodel import Session, select
+
+    from world_engine.models import EventParticipant
+    from world_engine.writes.events import EventScopeSpec, EventSpec, ParticipantSpec, event_fact, write_event
+
+    made = {}
+    with Session(engine) as db:
+        hunt = write_event(db, world_id=ids["world"], spec=_hunt(ids), created_by="check")
+        db.commit()
+        made["hunt"] = hunt.id
+        rows = db.exec(select(EventParticipant).where(EventParticipant.event_id == hunt.id)
+                       .order_by(EventParticipant.position)).all()
+        if (hunt.type_id, hunt.quantity) != (ids["tuer"], 3) or \
+                [(r.role_id, r.entity_id, r.sorte_id) for r in rows] != [
+                    (ids["tueur"], ids["brakk"], None), (ids["victime"], None, ids["loup"])]:
+            fail(f"EC1: the hunt reads {hunt.type_id}/{hunt.quantity} with {[(r.entity_id, r.sorte_id) for r in rows]}")
+        fact = event_fact(db, hunt.id)
+        if fact is None or fact.facet != "evenement" or fact.content_raw != "Brakk tue 3 loups — Dans la Forêt.":
+            fail(f"EC1: the hunt's fact is {fact and (fact.facet, fact.content_raw)}")
+        if fact and _scopes(db, fact.id) != [("location", ids["foret"], "rumor")]:
+            fail(f"EC1: the hunt's scopes are {_scopes(db, fact.id)}")
+        known = _knowledge(db, ids["brakk"], fact.id) if fact else None
+        if known is None or known.level != "knows" or known.is_secret:
+            fail(f"EC1: Brakk holds {known and (known.level, known.is_secret)}")
+        pact = write_event(db, world_id=ids["world"], created_by="check", spec=EventSpec(
+            type_id=ids["pacte"], title="Le pacte",
+            participants=(ParticipantSpec(ids["partie"], entity_id=ids["ysa"]),
+                          ParticipantSpec(ids["partie"], entity_id=ids["mira"], secret=True),
+                          ParticipantSpec(ids["partie"], entity_id=ids["guilde"]))))
+        db.commit()
+        made["pact"] = pact.id
+        pf = event_fact(db, pact.id)
+        ysa, mira, guilde = (_knowledge(db, ids[k], pf.id) for k in ("ysa", "mira", "guilde"))
+        if ysa is None or not ysa.is_secret or mira is None or mira.is_secret or guilde is not None:
+            fail(f"EC1: the pact's knowledge is ysa {ysa and ysa.is_secret}, mira {mira and mira.is_secret}, "
+                 f"guilde {guilde}")
+        if _scopes(db, pf.id) != [("faction", ids["guilde"], "knows")]:
+            fail(f"EC1: the pact's scopes are {_scopes(db, pf.id)}")
+        own = write_event(db, world_id=ids["world"], created_by="check", spec=_hunt(
+            ids, title="Une chasse", scopes=(EventScopeSpec("world", None, "rumor"),)))
+        none = write_event(db, world_id=ids["world"], created_by="check", spec=_hunt(ids, title="Une autre", scopes=()))
+        db.commit()
+        if _scopes(db, event_fact(db, own.id).id) != [("world", None, "rumor")] or \
+                _scopes(db, event_fact(db, none.id).id):
+            fail("EC1: a spec's own scopes did not replace the type's")
+    return made
+
+
+def check_ec2(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.writes.events import EventScopeSpec, ParticipantSpec, write_event
+
+    tueur, victime, partie = ids["tueur"], ids["victime"], ids["partie"]
+    cases = {
+        "an unknown type": _hunt(ids, type_id="nope"),
+        "a retired type": _hunt(ids, type_id=ids["vieux"], quantity=None, participants=()),
+        "an empty title": _hunt(ids, title="  "),
+        "a place that is not a location": _hunt(ids, location_id=ids["brakk"]),
+        "a quantity on a type that counts none": _hunt(ids, type_id=ids["pacte"], participants=()),
+        "a quantity of 0": _hunt(ids, quantity=0),
+        "a role of another type": _hunt(ids, participants=(ParticipantSpec(partie, entity_id=ids["brakk"]),)),
+        "an entity the role does not accept": _hunt(ids, participants=(ParticipantSpec(tueur, entity_id=ids["foret"]),)),
+        "a sorte in a role that takes none": _hunt(ids, participants=(ParticipantSpec(tueur, sorte_id=ids["loup"]),)),
+        "an entity and a sorte at once": _hunt(ids, participants=(
+            ParticipantSpec(victime, entity_id=ids["ysa"], sorte_id=ids["loup"]),)),
+        "one participant twice": _hunt(ids, participants=(ParticipantSpec(tueur, entity_id=ids["brakk"]),
+                                                          ParticipantSpec(tueur, entity_id=ids["brakk"]))),
+        "an unknown scope": _hunt(ids, scopes=(EventScopeSpec("planet", None, "knows"),)),
+        "a world scope naming an entity": _hunt(ids, scopes=(EventScopeSpec("world", ids["brakk"], "knows"),)),
+        "a faction scope naming a character": _hunt(ids, scopes=(EventScopeSpec("faction", ids["brakk"], "knows"),)),
+    }
+    with Session(engine) as db:
+        for label, spec in cases.items():
+            _refused(db, label, "EC2", lambda spec=spec: write_event(db, world_id=ids["world"], spec=spec,
+                                                                     created_by="check"))
+
+
+def check_ec3(engine, ids: dict, made: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.models import Event
+    from world_engine.writes.events import EventScopeSpec, ParticipantSpec, event_fact, write_event_update
+
+    with Session(engine) as db:
+        hunt = db.get(Event, made["hunt"])
+        kept = (ParticipantSpec(ids["tueur"], entity_id=ids["brakk"], secret=True),
+                ParticipantSpec(ids["victime"], sorte_id=ids["loup"]))
+        write_event_update(db, event=hunt, changed_by="check", spec=_hunt(
+            ids, title="Brakk tue 4 loups", quantity=4,
+            participants=kept + (ParticipantSpec(ids["tueur"], entity_id=ids["ysa"]),),
+            scopes=(EventScopeSpec("world", None, "rumor"),)))
+        db.commit()
+        fact = event_fact(db, hunt.id)
+        history = fact.change_history or []
+        if fact.content_raw != "Brakk tue 4 loups — Dans la Forêt." or not history or \
+                history[-1].get("kind") != "correction" or history[-1].get("content") != "Brakk tue 3 loups — Dans la Forêt.":
+            fail(f"EC3: the corrected fact reads {fact.content_raw!r}, history {history[-1:]}")
+        brakk, ysa = _knowledge(db, ids["brakk"], fact.id), _knowledge(db, ids["ysa"], fact.id)
+        if brakk is None or not brakk.is_secret or ysa is None:
+            fail(f"EC3: after the correction Brakk is secret {brakk and brakk.is_secret}, Ysa holds {ysa}")
+        if _scopes(db, fact.id) != [("world", None, "rumor")]:
+            fail(f"EC3: the scopes are {_scopes(db, fact.id)}")
+        for label, spec in {
+            "taking a participant away": _hunt(ids, participants=kept[:1]),
+            "changing the type": _hunt(ids, type_id=ids["pacte"], quantity=None, participants=()),
+        }.items():
+            _refused(db, label, "EC3", lambda spec=spec: write_event_update(db, event=db.get(Event, made["hunt"]),
+                                                                            spec=spec, changed_by="check"))
+
+
+def _mutation(db, world_id: str, payload: dict):
+    from world_engine.models import ProposedMutation
+
+    mut = ProposedMutation(world_id=world_id, source_type="world_tick", tick_id="t", mutation_type="event_creation",
+                           target_table="event", payload=payload, status="approved")
+    db.add(mut)
+    db.flush()
+    return mut
+
+
+def check_ec4(engine, ids: dict) -> None:
+    from sqlmodel import Session, func, select
+
+    from world_engine.cockpit.routes.mutations import _apply_mutation
+    from world_engine.event_vocab import DOMAIN_ROLE_FR, type_view
+    from world_engine.models import Event, EventParticipant
+    from world_engine.writes.events import event_fact
+
+    world = ids["world"]
+    with Session(engine) as db:
+        typed = _mutation(db, world, {"title": "Ysa tue un loup", "type_id": ids["tuer"], "quantity": 1,
+                                      "participants": [{"role_id": ids["tueur"], "entity_id": ids["ysa"]},
+                                                       {"role_id": ids["victime"], "sorte_id": ids["loup"]}]})
+        error = _apply_mutation(typed, db)
+        db.commit()
+        event = db.exec(select(Event).where(Event.title == "Ysa tue un loup")).first()
+        if error or event is None or event.type_id != ids["tuer"] or db.exec(select(func.count()).select_from(
+                EventParticipant).where(EventParticipant.event_id == event.id)).one() != 2:
+            fail(f"EC4: a typed payload gave {error!r}, event {event}")
+        public = _mutation(db, world, {"title": "La fête", "type": "social", "knowledge_status": "public",
+                                       "involved_entities": [ids["brakk"], ids["guilde"]]})
+        secret = _mutation(db, world, {"title": "Le complot", "type": "social", "knowledge_status": "secret",
+                                       "involved_entities": [ids["brakk"]]})
+        errors = (_apply_mutation(public, db), _apply_mutation(secret, db))
+        db.commit()
+        fete = db.exec(select(Event).where(Event.title == "La fête")).first()
+        complot = db.exec(select(Event).where(Event.title == "Le complot")).first()
+        view = type_view(db, fete.type_id) if fete else None
+        roles = {p.entity_id: p.role_id for p in db.exec(select(EventParticipant).where(
+            EventParticipant.event_id == (fete.id if fete else "")))}
+        if any(errors) or view is None or view.name != "Social" or [r.name for r in view.roles] != [DOMAIN_ROLE_FR] \
+                or set(roles) != {ids["brakk"], ids["guilde"]}:
+            fail(f"EC4: untyped payloads gave {errors}, type {view and view.name}, participants {roles}")
+        if fete and _scopes(db, event_fact(db, fete.id).id) != [("world", None, "knows")]:
+            fail("EC4: a public untyped payload's fact has no world scope at knows")
+        if complot and _scopes(db, event_fact(db, complot.id).id):
+            fail("EC4: a secret untyped payload's fact has scopes")
+        before = db.exec(select(func.count()).select_from(Event)).one()
+        bad = _mutation(db, world, {"title": "X", "type_id": ids["tuer"],
+                                    "participants": [{"role_id": "nope", "entity_id": ids["ysa"]}]})
+        with db.begin_nested():
+            answer = _apply_mutation(bad, db)
+        if not (answer or "").startswith("event_creation:"):
+            fail(f"EC4: an unknown role answered {answer!r}")
+        db.rollback()
+        if db.exec(select(func.count()).select_from(Event)).one() != before:
+            fail("EC4: an unknown role wrote an event")
+
+
+def check_ec5(engine, ids: dict) -> None:
+    from fastapi import HTTPException
+    from sqlmodel import Session, func, select
+
+    from world_engine.cockpit.crud import events as routes
+    from world_engine.models import Event
+
+    with Session(engine) as db:
+        body = routes.EventBody(title="Mira croise un loup", type_id=ids["tuer"], location_id=ids["foret"], quantity=1,
+                                participants=[routes.ParticipantBody(role_id=ids["tueur"], entity_id=ids["mira"]),
+                                              routes.ParticipantBody(role_id=ids["victime"], sorte_id=ids["loup"])])
+        made = routes.create_event(body, db)
+        names = [(p["role_name"], p["name"], p["secret"]) for p in made["participants"]]
+        if made["type_name"] != "Tuer" or names != [("tueur", "Mira", False), ("victime", "Loup", None)] \
+                or [s["scope_type"] for s in made["scopes"]] != ["location"]:
+            fail(f"EC5: create_event answered {made['type_name']}, {names}, {made['scopes']}")
+        body.title = "Mira chasse un loup"
+        if routes.update_event(made["id"], body, db)["title"] != "Mira chasse un loup":
+            fail("EC5: update_event did not correct the title")
+        before = db.exec(select(func.count()).select_from(Event)).one()
+        for label, call in (("a refused event", lambda: routes.create_event(routes.EventBody(
+                title=" ", type_id=ids["tuer"]), db)),
+                            ("an unknown event", lambda: routes.get_event("nope", db))):
+            try:
+                call()
+                fail(f"EC5: {label} was answered")
+            except HTTPException as exc:
+                want = 404 if "unknown" in label else 422
+                if exc.status_code != want:
+                    fail(f"EC5: {label} answered {exc.status_code}")
+        if db.exec(select(func.count()).select_from(Event)).one() != before:
+            fail("EC5: a refused event wrote a row")
+
+
+def _function_source(path: pathlib.Path, name: str) -> str:
+    tree = ast.parse(path.read_text(encoding="utf-8"))
+    for node in ast.walk(tree):
+        if isinstance(node, ast.FunctionDef) and node.name == name:
+            return ast.get_source_segment(path.read_text(encoding="utf-8"), node) or ""
+    return ""
+
+
+def check_ec6() -> None:
+    from world_engine.cockpit.crud._shared import EVENT_FIELDS
+
+    if [f["name"] for f in EVENT_FIELDS] != ["title", "description", "location_id"]:
+        fail(f"EC6: EVENT_FIELDS names {[f['name'] for f in EVENT_FIELDS]}")
+    crud = (SRC / "cockpit" / "crud" / "events.py").read_text(encoding="utf-8")
+    applier = _function_source(SRC / "cockpit" / "mutations.py", "_mutation_apply_event_creation")
+    if not applier:
+        fail("EC6: _mutation_apply_event_creation is missing")
+    for name, text in (("crud/events.py", crud), ("the event_creation applier", applier)):
+        for needle in ("knowledge_status", "EventEntity"):
+            if needle in text:
+                fail(f"EC6: {name} names {needle}")
+    needles = {
+        "Evenements.svelte": ('id="event-f-type_id"', 'id="event-f-quantity"', "bind:checked={p.secret}",
+                              "eventDraftState.scopes", "role.accepts_sorte"),
+        "Sheet.svelte": ("eventDraftBody()",),
+        "eventDraft.svelte.js": ("export function eventDraftBody", "!eventDraftState.participants[i].saved"),
+    }
+    for name, wanted in needles.items():
+        path = FRONT / name
+        text = path.read_text(encoding="utf-8") if path.exists() else ""
+        for needle in wanted:
+            if needle not in text:
+                fail(f"EC6: {name} lacks {needle}")
+
+
+def main() -> int:
+    _fresh_db()
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    ids = _fixture(engine)
+    state: dict = {}
+
+    def ec1() -> None:
+        state.update(check_ec1(engine, ids))
+
+    rules = (("EC1", ec1), ("EC2", lambda: check_ec2(engine, ids)), ("EC3", lambda: check_ec3(engine, ids, state)),
+             ("EC4", lambda: check_ec4(engine, ids)), ("EC5", lambda: check_ec5(engine, ids)), ("EC6", check_ec6))
+    for name, rule in rules:
+        try:
+            rule()
+        except Exception as exc:  # a crash is that rule's failure, never a pass
+            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: event_writes -- an event is written with its type, its participants by role, its fact, the "
+          "type's scopes made concrete and its participants' knowledge, secret each as said; a correction "
+          "keeps its type and its participants; an approved proposal, typed or not, is written the same way")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/single_canon_write.py b/tooling/verify/checks/single_canon_write.py
index dd49b48..7b46125 100644
--- a/tooling/verify/checks/single_canon_write.py
+++ b/tooling/verify/checks/single_canon_write.py
@@ -85,15 +85,20 @@ single-row correction): `write_npc_prices`, `write_world_laws`,
 `writes/attributes.py::_write_types` (TICKET-0113, BRIEF-0113-A: an
 attribute definition's entity types) and `writes/event_types.py::_write_roles`
 / `_write_scopes` (TICKET-0114, BRIEF-0114-A: a role's entity types, an
-event type's scopes -- never a role itself, retired instead) each
+event type's scopes -- never a role itself, retired instead) and
+`writes/events.py::_write_scopes` (TICKET-0114, BRIEF-0114-C: an event's
+fact's scopes, from the journal or an approved proposal) each
 `DELETE FROM` their table(s) scoped to one parent (NPC / world / location /
-location / offer / definition / role / type) then re-insert the submitted set, in one
+location / offer / definition / role / type / fact) then re-insert the submitted set, in one
 transaction — creator-CRUD and world-bootstrap only (`set_npc_prices`,
 `create_world`, `set_location_geometry`, `set_location_doors`,
-`save_offer`, the attribute definition routes, the event type routes;
+`save_offer`, the attribute definition routes, the event type routes,
+the journal's routes and `_apply_mutation`'s `event_creation`;
 `location_subculture` and
 its writer were dropped in schema v2.06, TICKET-0091, BRIEF-0091-I), never
-reachable from any AI or play path. These
+reachable from any AI or play path -- but `writes/events.py::_write_scopes`,
+which `_apply_mutation`'s `event_creation` reaches after the creator's
+approval, writing a new fact's scopes. These
 tables carry no `change_history` by design (metadata-config category);
 the full-replace IS their write shape. No table may take a foreign key on
 `door.id` — enforced by `door_terminal.py`. `cockpit/spatial_doors.py`
````

2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
4. Run the checks below, then the full corpus.

## Scope OUT

- The readers (D): the MJ, the tick and the return delta still read `knowledge_status` after this brief; the column stays until v2.25.
- The tick's producer of typed events, Lore declaring events (U1), the event review card (Y2) -- TICKET-0119.
- Removing a participant from an event: the journal corrects and adds, never removes.
- Every later brief of this lot: BRIEF-0114-D, BRIEF-0114-E, BRIEF-0114-F, BRIEF-0114-G, BRIEF-0114-H.

## Invariants to defend

INV-07: a PC participant's knowledge row is never secret, even when asked -- `_clean_participant` forces it (EC1). INV-16/INV-17: one knowledge row per (entity, fact), raised never duplicated. INV-08/INV-12: the full-replace of an event's scopes is a named delete. INV-10: the fact's text change appends its history (`correction`).

## Decision rights

STOP:
- A CRUD or applier path would write an event without going through `write_event` / `write_event_update`.
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
- `python tooling/verify/checks/event_writes.py` -> `PASS`.
- `python tooling/verify/checks/event_journal.py` -> `PASS`.
- `python tooling/verify/checks/single_canon_write.py` -> `PASS`.
- `python tooling/verify/checks/fact_facets.py` -> `PASS`.
- `python tooling/verify/checks/knowledge_identity.py` -> `PASS`.
- `python tooling/verify/checks/frontend_build_fresh.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (152 on the prototype).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **EC1** -- `writes/events.py` `_clean_participant`: `secret=False if _is_player(db, entity.id) else secret)` -> `secret=secret)`
  - **EC2** -- `writes/events.py` `_clean_participants`: `if len(set(keys)) != len(keys):` -> `if False:`
  - **EC3** -- `writes/events.py` `write_event_update`: `kind="correction"` -> `kind="changement"`
  - **EC4** -- `event_payloads.py`: `PUBLIC_STATUSES = ("public", "confirmed")` -> `("confirmed",)`
  - **EC5** -- `cockpit/crud/events.py`: the unknown event's `HTTPException(404, …)` -> `HTTPException(400, …)`
  - **EC6** -- `cockpit/crud/_shared.py` `EVENT_FIELDS`: add `{"name": "type", "label": "Type", "kind": "text"}`
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated.
