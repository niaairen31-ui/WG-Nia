<!-- slug: event-editor -->
# BRIEF 0119-D — "One event editor for the journal, the review card and Lore; the card approves what the creator edited (no schema change)"

Lot: LOT-0119-event-producers.md (authoritative on conflict)
Depends on: BRIEF-0119-C (C-04, C-05)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0119-C's commit).

- `frontend/src/creation/QueueCard.svelte` -> `  function eventSummary(m) {` (read-only)
- `frontend/src/creation/eventDraft.svelte.js` -> `export const eventDraftState = $state({` and `export function eventDraftBody() {`
- `frontend/src/creation/Sheet.svelte` -> `    Object.assign(body, eventDraftBody());`
- `tooling/verify/checks/event_writes.py` -> `        "Evenements.svelte": ('id="event-f-type_id"',` (EC6)
- `src/world_engine/event_payloads.py` -> `def _typed(` reading no `scopes`
- No `frontend/src/creation/EventEditor.svelte`, no `tooling/verify/checks/event_editor.py`.

## Facts carried

### R-04 — the journal's writer and the applier [M]
Opened: `src/world_engine/writes/events.py` (`EventSpec` :82;
`clean_event` :218; `_knows` :250 and `_add_participants` :267 return
nothing; `write_event` :288 returns the event; `write_event_update` :310);
`src/world_engine/event_payloads.py` (`_typed` :88 reads `type_id` /
`new_type`, participants, quantity, place -- no scopes, no changes;
`spec_from_payload` :132); `src/world_engine/cockpit/mutations.py:694`
(`_mutation_apply_event_creation` -> `write_event`);
`src/world_engine/cockpit/routes/mutations.py:597`
(`_approve_apply_and_commit`: one savepoint, an applier's error string rolls
it back).
Consequence: C writes the changes inside `write_event` (one writer, F1) and
returns every row (`record_event`) for Lore; D reads a card's `scopes`.

### R-06 — the review card and the journal's sheet [M]
Opened: `frontend/src/creation/QueueCard.svelte` (:26 the payload edited as
JSON; :112 `eventSummary`, read-only); `frontend/src/creation/
eventDraft.svelte.js` (:10 a module store; :69 `eventDraftBody()`);
`frontend/src/creation/Evenements.svelte` (type, quantity, participants,
scopes inline); `frontend/src/creation/Sheet.svelte:560`
(`Object.assign(body, eventDraftBody())`); `tooling/verify/checks/
event_writes.py:403` (EC6 pins the sheet's markup in `Evenements.svelte`);
`tooling/verify/checks/event_analyzer.py:332` (EH4 pins `eventSummary` and
the proposed type's badge).
Consequence: D moves the sheet's editing into `EventEditor.svelte` and
retargets EC6 there; the card keeps `eventSummary` for reviewed cards.

## Contracts

### C-03 — the vocabulary's routes
Produced by: BRIEF-0119-B   Consumed by: D, G
`EffectBody(role, attribute, mode="set", value: int | str | None)`;
`EventTypeBody.effects`; `type_dict(...)["effects"]` = `[{role (name),
attribute, mode, value (a role's NAME for an entity state)}]`;
`event_vocabulary(...)["states"]` = `[state_dict]` for the two
`EFFECT_SYSTEM_KEYS` and the world's active definitions: `{key, name, kind,
system, holder_types (None: all), value_types, choices [{value, label}]}`.
Frontend: `vocabState.states`; `typeDraft` / `typeBody` carry `effects`.

### C-04 — an event's changes (the journal's writer)
Produced by: BRIEF-0119-C   Consumed by: D-G
`writes.events.StateChangeSpec(entity_id, attribute, value, mode="set")`;
`EventSpec.changes` (default `()`); `WrittenEvent(event, fact, rows [(table,
id, "created" | "updated")], system_changes [{entity_id, attribute, before,
after}])`; `record_event(db, *, world_id, spec, created_by) ->
WrittenEvent`; `write_event` = `record_event(...).event`. Cleaning (all or
nothing): an active state an event may change, an entity of the world it
applies to (a vital state on a character), a value of its kind (`add` on an
integer; an entity value of a type the state names, or None), one state of
one entity once, never a location made active again; a correction
(`write_event_update`) carrying a change is refused. A definition's change:
`write_attribute_value(kind="changement", event_id=event.id)`, `add` summed
on the current value. `writes.entity_states.write_system_state(db, *,
world_id, entity_id, key, value) -> (before, after) | None` --
`SYSTEM_STATE_KEYS`; closes the seats of an entity leaving `active` or a
character leaving `alive`.

### C-05 — pre-fill and payload keys
Produced by: BRIEF-0119-C (D adds `scopes`)   Consumed by: D-G
`event_changes.type_changes(db, world_id, view, [(role_id, entity_id)]) ->
[{entity_id, attribute, mode, value}]` (each entity in the effect's role;
an entity state takes the first entity of its value role, or is left out);
`change_line(db, world_id, change) -> str | None` (« Porte : Ouvert ->
oui », « Garnison : Alerte +1 »); `payload_changes(raw) ->
tuple[StateChangeSpec]`. A typed `event_creation` payload carries
`state_changes`; the applier adds `applied_changes` (the system changes) to
an approved payload; D: `scopes` `[{scope_type, scope_id, level}]` (a list,
even empty, replaces the type's).

### C-06 — the editor
Produced by: BRIEF-0119-D   Consumed by: G
`POST /api/events/changes` (`ChangesBody(type_id, participants
[{role_id, entity_id}], changes [StateChangeBody])`) -> `{prefilled: [...,
line], described: [..., line]}`, reads only; `EventBody.state_changes`.
`EventEditor.svelte` props `{draft, entities, playerCharIds, typeFixed,
withText, withChanges, canPrefill (G)}`; a draft `{typeId, newType,
quantity, participants [{role_id, role, entity_id, sorte_id, sorte_name,
name, secret, saved}], customScopes, scopes, changes, title, description,
locationId}`; `eventDraft.svelte.js`: `blankEventDraft`, `addParticipantTo`,
`removeParticipantFrom`, `prefilledChanges`, `eventDraftBody(isNew)`,
`eventBodyFrom(draft, isNew)` (G), `draftFromPayload`, `payloadFromDraft`.

## Context

The journal's sheet edits an event; the review card shows a typed proposal read-only and corrects it only in raw JSON (Y1 of 0114). H1 makes ONE editor of the sheet's markup, shared by the journal, the card (Y2: a typed proposal is edited and approved as edited) and Lore (G). It also shows and edits what the event changes (M-c), pre-filled through one read route.

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `frontend/src/creation/EventEditor.svelte` (new, C-06): type, text and place (`withText`), quantity, participants and their secret (never offered for a PC), scopes, changes and « Pré-remplir depuis le type »;
   - `eventDraft.svelte.js` rewritten on one draft shape (`blankEventDraft`, `addParticipantTo`, `removeParticipantFrom`, `prefilledChanges`, `draftFromPayload`, `payloadFromDraft`, `eventDraftBody(isNew)`); `Evenements.svelte` renders the editor; `Sheet.svelte` sends `eventDraftBody(isNewSave)`;
   - `QueueCard.svelte`: a typed proposal in review renders the editor and approves `payloadFromDraft`; the raw payload behind « Voir le JSON »; `queue.svelte.js` keeps the world's entities;
   - `cockpit/crud/events.py`: `ChangesBody`, `POST /api/events/changes`; `event_payloads.py` reads a card's `scopes`;
   - `event_writes.py` EC6 scans `EventEditor.svelte` for the sheet's markup; creates check `event_editor.py` (EY1-EY3); appends the decision entry above the footer.
   The files it touches, exactly:
   - frontend/src/creation/Evenements.svelte
   - frontend/src/creation/EventEditor.svelte
   - frontend/src/creation/QueueCard.svelte
   - frontend/src/creation/Sheet.svelte
   - frontend/src/creation/eventDraft.svelte.js
   - frontend/src/creation/queue.svelte.js
   - src/world_engine/cockpit/crud/events.py
   - src/world_engine/event_payloads.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/event_editor.py
   - tooling/verify/checks/event_writes.py

````diff
diff --git a/frontend/src/creation/Evenements.svelte b/frontend/src/creation/Evenements.svelte
index 58b9582..ed11f3c 100644
--- a/frontend/src/creation/Evenements.svelte
+++ b/frontend/src/creation/Evenements.svelte
@@ -10,17 +10,22 @@
      default, or the creator's own (W1). The types and sortes come from the
      shared vocabulary store (eventVocab.svelte.js).
 
+     TICKET-0119 (BRIEF-0119-D, H1): everything past the plain fields is the
+     shared EventEditor.svelte, the same the review card and Lore render; a
+     new event also says what it changes in the world (M-c), a correction
+     does not.
+
      Rendered by Sheet.svelte in 'view' mode on the « Événements » tab;
      saved through its saveEventSheet (POST /api/events, PUT
      /api/events/{id}). No delete anywhere (C3 -- an event is history; a
      retraction empties its scopes). No scoped <style> block. */
   import { serverState } from '../lib/serverState.svelte.js';
   import {
-    eventDraftState, resetEventDraft, setEventDraftFromEvent, setEventDraftFromGenerated, addParticipant,
-    removeParticipant,
+    eventDraftState, resetEventDraft, setEventDraftFromEvent, setEventDraftFromGenerated,
   } from './eventDraft.svelte.js';
   import { vocabState, loadVocabulary } from './eventVocab.svelte.js';
   import Field from './Field.svelte';
+  import EventEditor from './EventEditor.svelte';
 
   let { legacyDoc, isNew, event, entities, playerCharIds, eventFields, onSave } = $props();
 
@@ -42,41 +47,6 @@
     genBrief = '';
   });
 
-  const SCOPE_TYPES = [
-    { value: 'world', label: 'tout le monde' }, { value: 'location', label: 'ceux qui passent au lieu' },
-    { value: 'rencontre', label: 'ceux qui ont rencontré' }, { value: 'faction', label: 'les membres de la faction' },
-  ];
-
-  let type = $derived(vocabState.types.find((t) => t.id === eventDraftState.typeId) || null);
-  let roles = $derived(type ? type.roles.filter((r) => r.status === 'active') : []);
-  let activeSortes = $derived(vocabState.sortes.filter((s) => s.status === 'active'));
-  let levelLabels = $derived(Object.fromEntries(vocabState.levels.map((l) => [l.value, l.label])));
-
-  function candidates(role) {
-    return (entities || []).filter((e) => role.entity_types.includes(e.type));
-  }
-
-  function onAdd(role, ev) {
-    const value = ev.currentTarget.value;
-    ev.currentTarget.value = '';
-    if (!value) return;
-    const [kind, id] = value.split(':');
-    const name = kind === 'sorte' ? (activeSortes.find((s) => s.id === id) || {}).name
-      : ((entities || []).find((e) => e.id === id) || {}).name;
-    addParticipant(role, kind, id, name, type && type.participants_secret);
-  }
-
-  function scopeTargets(scopeType) {
-    if (scopeType === 'location') return (entities || []).filter((e) => e.type === 'location');
-    if (scopeType === 'faction') return (entities || []).filter((e) => e.type === 'faction');
-    return entities || [];
-  }
-
-  function typeScopeLine(t) {
-    if (!t || !t.scopes.length) return 'les participants seulement';
-    return t.scopes.map((s) => `${s.kind}${s.role ? ' ' + s.role : ''} (${levelLabels[s.level] || s.level})`).join(' · ');
-  }
-
   async function generate() {
     const brief = genBrief.trim();
     if (!brief) { genStatus = 'Intention requise.'; return; }
@@ -134,77 +104,7 @@
   {/each}
 </div></div>
 
-<div class="field-section"><div class="field-section-title">Type</div>
-  <select id="event-f-type_id" bind:value={eventDraftState.typeId} disabled={!isNew}>
-    <option value="">— choisir un type —</option>
-    {#each vocabState.types.filter((t) => t.status === 'active' || t.id === eventDraftState.typeId) as t (t.id)}
-      <option value={t.id}>{t.name} ({t.domain_label})</option>
-    {/each}
-  </select>
-  {#if !isNew}<span style="color:var(--muted); font-size:12px;"> Le type d'un événement ne change pas.</span>{/if}
-  {#if type && type.counts_quantity}
-    <label style="display:block; margin-top:6px">Quantité
-      <input id="event-f-quantity" type="number" min="1" style="width:90px" bind:value={eventDraftState.quantity}>
-    </label>
-  {/if}
-</div>
-
-{#if type}
-  <div class="field-section"><div class="field-section-title">Participants</div>
-    {#each roles as role (role.id)}
-      <div style="margin:4px 0">
-        <strong>{role.name}</strong>
-        {#each eventDraftState.participants as p, i (i)}
-          {#if p.role_id === role.id}
-            <span class="badge b-other" style="display:inline-flex; align-items:center; gap:5px; margin:2px">
-              {p.sorte_id ? 'sorte : ' : ''}{p.name || '« inconnu »'}
-              {#if p.entity_id && !(playerCharIds && playerCharIds.has(p.entity_id))}
-                <label title="Il garde le secret"><input type="checkbox" bind:checked={p.secret}> secret</label>
-              {/if}
-              {#if !p.saved}
-                <button class="btn-icon" style="padding:0 2px" title="Retirer" onclick={() => removeParticipant(i)}>✕</button>
-              {/if}
-            </span>
-          {/if}
-        {/each}
-        <select onchange={(ev) => onAdd(role, ev)}>
-          <option value="">— ajouter —</option>
-          {#each candidates(role) as e (e.id)}<option value={'entity:' + e.id}>{e.name}</option>{/each}
-          {#if role.accepts_sorte}
-            {#each activeSortes as s (s.id)}<option value={'sorte:' + s.id}>sorte : {s.name}</option>{/each}
-          {/if}
-        </select>
-      </div>
-    {/each}
-  </div>
-
-  <div class="field-section"><div class="field-section-title">Qui l'apprend, en plus des participants</div>
-    <label><input type="checkbox" bind:checked={eventDraftState.customScopes}> Choisir pour cet événement</label>
-    {#if !eventDraftState.customScopes}
-      <div style="color:var(--muted); font-size:12px;">Celle du type : {typeScopeLine(type)}</div>
-    {:else}
-      {#each eventDraftState.scopes as scope, k (k)}
-        <div style="display:flex; gap:6px; align-items:center; margin:2px 0">
-          <select bind:value={scope.scope_type} onchange={() => (scope.scope_id = null)}>
-            {#each SCOPE_TYPES as st (st.value)}<option value={st.value}>{st.label}</option>{/each}
-          </select>
-          {#if scope.scope_type !== 'world'}
-            <select bind:value={scope.scope_id}>
-              <option value={null}>— choisir —</option>
-              {#each scopeTargets(scope.scope_type) as e (e.id)}<option value={e.id}>{e.name}</option>{/each}
-            </select>
-          {/if}
-          <select bind:value={scope.level}>
-            {#each vocabState.levels as l (l.value)}<option value={l.value}>{l.label}</option>{/each}
-          </select>
-          <button class="btn-icon" title="Retirer" onclick={() => eventDraftState.scopes.splice(k, 1)}>✕</button>
-        </div>
-      {/each}
-      {#if !eventDraftState.scopes.length}<div style="color:var(--muted); font-size:12px;">Personne d'autre.</div>{/if}
-      <button onclick={() => eventDraftState.scopes.push({ scope_type: 'world', scope_id: null, level: 'knows' })}>+ portée</button>
-    {/if}
-  </div>
-{/if}
+<EventEditor draft={eventDraftState} {entities} {playerCharIds} typeFixed={!isNew} withChanges={isNew} />
 
 {#if !isNew}
   <div class="field-section"><span style="color:var(--muted); font-size:12px;">Enregistré : {event.recorded_at || ''}</span></div>
diff --git a/frontend/src/creation/EventEditor.svelte b/frontend/src/creation/EventEditor.svelte
new file mode 100644
index 0000000..b39987d
--- /dev/null
+++ b/frontend/src/creation/EventEditor.svelte
@@ -0,0 +1,272 @@
+<script>
+  /* TICKET-0119 (BRIEF-0119-D; decisions H1, Y2 and M-c of the conditions
+     series). The ONE event editor: the journal's sheet (Evenements.svelte),
+     the review card of a proposed event (QueueCard.svelte) and Lore's events
+     (BRIEF-0119-G) render it on a draft of eventDraft.svelte.js's shape.
+
+     What it edits: the event's type (one of the world's, unless `typeFixed`;
+     a type proposed with the event, `draft.newType`, shows its roles and
+     stays as proposed), with `withText` its title, description and place;
+     its quantity when the type counts; its participants role by role -- an
+     entity of a type the role accepts, or a sorte (a new one by name on a
+     card) -- each entity keeping the event secret or not (X1; never a player
+     character, INV-07: no box is offered, and the server forces it); who
+     learns it besides them (the type's scopes, or its own, W1); and what it
+     changes in the world (`draft.changes`, M-c): pre-filled from the type's
+     effects (« Pré-remplir », POST /api/events/changes), each kept, edited or
+     dropped, and new ones added -- an entity, a state that applies to it, a
+     value of the state's kind (an integer set or added, D3). `withChanges`
+     off (a correction from the journal) hides them: a correction changes no
+     state.
+
+     `entities` are the world's ({id, name, type}); `playerCharIds` a Set of
+     the player characters' ids. The types, sortes, levels and states come
+     from the shared vocabulary store (eventVocab.svelte.js). No scoped
+     <style> block: it renders inside the Creation iframe document too. */
+  import { vocabState } from './eventVocab.svelte.js';
+  import { addParticipantTo, removeParticipantFrom, prefilledChanges } from './eventDraft.svelte.js';
+
+  let {
+    draft, entities = [], playerCharIds = null, typeFixed = false, withText = false, withChanges = true,
+  } = $props();
+
+  let prefillError = $state('');
+
+  const SCOPE_TYPES = [
+    { value: 'world', label: 'tout le monde' }, { value: 'location', label: 'ceux qui passent au lieu' },
+    { value: 'rencontre', label: 'ceux qui ont rencontré' }, { value: 'faction', label: 'les membres de la faction' },
+  ];
+
+  let type = $derived(vocabState.types.find((t) => t.id === draft.typeId) || null);
+  let roles = $derived(draft.newType
+    ? (draft.newType.roles || []).map((r) => ({ id: null, name: r.name, entity_types: r.entity_types || [],
+                                               accepts_sorte: !!r.accepts_sorte, status: 'active' }))
+    : (type ? type.roles.filter((r) => r.status === 'active') : []));
+  let counts = $derived(draft.newType ? !!draft.newType.counts_quantity : !!(type && type.counts_quantity));
+  let defaultSecret = $derived(draft.newType ? !!draft.newType.participants_secret
+    : !!(type && type.participants_secret));
+  let activeSortes = $derived(vocabState.sortes.filter((s) => s.status === 'active'));
+  let levelLabels = $derived(Object.fromEntries(vocabState.levels.map((l) => [l.value, l.label])));
+  let places = $derived((entities || []).filter((e) => e.type === 'location'));
+
+  const inRole = (p, role) => (role.id ? p.role_id === role.id : !p.role_id && p.role === role.name);
+  const isPlayer = (id) => !!(playerCharIds && playerCharIds.has && playerCharIds.has(id));
+
+  function nameOf(id) {
+    const e = (entities || []).find((x) => x.id === id);
+    return e ? e.name : id;
+  }
+
+  function candidates(role) {
+    return (entities || []).filter((e) => role.entity_types.includes(e.type));
+  }
+
+  function onAdd(role, ev) {
+    const value = ev.currentTarget.value;
+    ev.currentTarget.value = '';
+    if (!value) return;
+    const [kind, id] = value.split(':');
+    const name = kind === 'sorte' ? (activeSortes.find((s) => s.id === id) || {}).name : nameOf(id);
+    addParticipantTo(draft, role, kind, id, name, defaultSecret);
+  }
+
+  function onType() {
+    // A new type keeps the participants whose role it has, by name.
+    const next = vocabState.types.find((t) => t.id === draft.typeId);
+    const byName = Object.fromEntries((next ? next.roles : []).filter((r) => r.status === 'active')
+      .map((r) => [r.name, r]));
+    draft.participants = draft.participants.filter((p) => byName[p.role]).map((p) => ({
+      ...p, role_id: byName[p.role].id,
+    }));
+  }
+
+  function scopeTargets(scopeType) {
+    if (scopeType === 'location') return places;
+    if (scopeType === 'faction') return (entities || []).filter((e) => e.type === 'faction');
+    return entities || [];
+  }
+
+  function typeScopeLine() {
+    if (!type || !type.scopes.length) return 'les participants seulement';
+    return type.scopes.map((s) => `${s.kind}${s.role ? ' ' + s.role : ''} (${levelLabels[s.level] || s.level})`).join(' · ');
+  }
+
+  // --- what it changes in the world (M-c) ---
+  function stateOf(key) {
+    return (vocabState.states || []).find((s) => s.key === key) || null;
+  }
+
+  function statesFor(entityId) {
+    const e = (entities || []).find((x) => x.id === entityId);
+    return (vocabState.states || []).filter((s) => e && (s.holder_types === null || s.holder_types.includes(e.type)));
+  }
+
+  function valueEntities(state) {
+    return (entities || []).filter((e) => state.value_types.includes(e.type));
+  }
+
+  function changeLine(c) {
+    const state = stateOf(c.attribute);
+    if (!state) return '';
+    if (c.mode === 'add') return `${state.name} ${c.value >= 0 ? '+' : ''}${c.value}`;
+    if (state.kind === 'choice') return `${state.name} -> ${(state.choices.find((x) => x.value === c.value) || {}).label || c.value}`;
+    if (state.kind === 'entity') return `${state.name} -> ${c.value ? nameOf(c.value) : '(aucun)'}`;
+    return `${state.name} -> ${c.value}`;
+  }
+
+  async function prefill() {
+    prefillError = '';
+    try {
+      const found = await prefilledChanges(draft);
+      const have = new Set(draft.changes.map((c) => `${c.entity_id}|${c.attribute}`));
+      for (const c of found) if (!have.has(`${c.entity_id}|${c.attribute}`)) draft.changes.push(c);
+      if (!found.length) prefillError = "Le type ne change rien pour ces participants.";
+    } catch (e) {
+      prefillError = e.message;
+    }
+  }
+
+  function addChange() {
+    draft.changes.push({ entity_id: '', attribute: '', mode: 'set', value: null });
+  }
+
+  function onChangeState(c) {
+    const state = stateOf(c.attribute);
+    c.mode = 'set';
+    c.value = state && state.kind === 'choice' && state.choices.length ? state.choices[0].value
+      : state && state.kind === 'integer' ? 0 : null;
+  }
+</script>
+
+{#if withText}
+  <div class="field-section"><div class="field-section-title">Événement</div>
+    <label style="display:block">Titre <input type="text" style="width:100%" bind:value={draft.title}></label>
+    <label style="display:block">Description
+      <textarea rows="2" style="width:100%; resize:vertical" bind:value={draft.description}></textarea></label>
+    <label style="display:block">Lieu
+      <select bind:value={draft.locationId}>
+        <option value={null}>— aucun —</option>
+        {#each places as e (e.id)}<option value={e.id}>{e.name}</option>{/each}
+      </select>
+    </label>
+  </div>
+{/if}
+
+<div class="field-section"><div class="field-section-title">Type</div>
+  {#if draft.newType}
+    <strong>{draft.newType.name}</strong>
+    <span class="badge b-other">nouveau type — validé avec l'événement</span>
+  {:else}
+    <select id="event-f-type_id" bind:value={draft.typeId} disabled={typeFixed} onchange={onType}>
+      <option value="">— choisir un type —</option>
+      {#each vocabState.types.filter((t) => t.status === 'active' || t.id === draft.typeId) as t (t.id)}
+        <option value={t.id}>{t.name} ({t.domain_label})</option>
+      {/each}
+    </select>
+    {#if typeFixed}<span style="color:var(--muted); font-size:12px;"> Le type d'un événement ne change pas.</span>{/if}
+  {/if}
+  {#if counts}
+    <label style="display:block; margin-top:6px">Quantité
+      <input id="event-f-quantity" type="number" min="1" style="width:90px" bind:value={draft.quantity}>
+    </label>
+  {/if}
+</div>
+
+{#if roles.length}
+  <div class="field-section"><div class="field-section-title">Participants</div>
+    {#each roles as role (role.id || role.name)}
+      <div style="margin:4px 0">
+        <strong>{role.name}</strong>
+        {#each draft.participants as p, i (i)}
+          {#if inRole(p, role)}
+            <span class="badge b-other" style="display:inline-flex; align-items:center; gap:5px; margin:2px">
+              {p.sorte_id || p.sorte_name ? 'sorte : ' : ''}{p.name || p.sorte_name || '« inconnu »'}
+              {#if !p.sorte_id && !p.sorte_name && p.entity_id && !isPlayer(p.entity_id)}
+                <label title="Il garde le secret"><input type="checkbox" bind:checked={p.secret}> secret</label>
+              {/if}
+              {#if !p.saved}
+                <button class="btn-icon" style="padding:0 2px" title="Retirer" onclick={() => removeParticipantFrom(draft, i)}>✕</button>
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
+    <label><input type="checkbox" bind:checked={draft.customScopes}> Choisir pour cet événement</label>
+    {#if !draft.customScopes}
+      <div style="color:var(--muted); font-size:12px;">Celle du type : {typeScopeLine()}</div>
+    {:else}
+      {#each draft.scopes as scope, k (k)}
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
+          <button class="btn-icon" title="Retirer" onclick={() => draft.scopes.splice(k, 1)}>✕</button>
+        </div>
+      {/each}
+      {#if !draft.scopes.length}<div style="color:var(--muted); font-size:12px;">Personne d'autre.</div>{/if}
+      <button onclick={() => draft.scopes.push({ scope_type: 'world', scope_id: null, level: 'knows' })}>+ portée</button>
+    {/if}
+  </div>
+{/if}
+
+{#if withChanges && (roles.length || draft.changes.length)}
+  <div class="field-section"><div class="field-section-title">Ce qu'il change dans le monde</div>
+    {#each draft.changes as c, k (k)}
+      {@const state = stateOf(c.attribute)}
+      <div style="display:flex; gap:6px; align-items:center; flex-wrap:wrap; margin:2px 0">
+        <select bind:value={c.entity_id}>
+          <option value="">— entité —</option>
+          {#each entities || [] as e (e.id)}<option value={e.id}>{e.name}</option>{/each}
+        </select>
+        <select bind:value={c.attribute} onchange={() => onChangeState(c)}>
+          <option value="">— état —</option>
+          {#each statesFor(c.entity_id) as s (s.key)}<option value={s.key}>{s.name}</option>{/each}
+        </select>
+        {#if state && state.kind === 'choice'}
+          <select bind:value={c.value}>
+            {#each state.choices as x (x.value)}<option value={x.value}>{x.label}</option>{/each}
+          </select>
+        {:else if state && state.kind === 'integer'}
+          <select bind:value={c.mode}>
+            <option value="set">devient</option>
+            <option value="add">augmente de</option>
+          </select>
+          <input type="number" style="width:70px" bind:value={c.value}>
+        {:else if state && state.kind === 'entity'}
+          <select bind:value={c.value}>
+            <option value={null}>— personne —</option>
+            {#each valueEntities(state) as e (e.id)}<option value={e.id}>{e.name}</option>{/each}
+          </select>
+        {/if}
+        <span style="font-size:12px; color:var(--muted)">{changeLine(c)}</span>
+        <button class="btn-icon" title="Retirer" onclick={() => draft.changes.splice(k, 1)}>✕</button>
+      </div>
+    {/each}
+    {#if !draft.changes.length}<div style="color:var(--muted); font-size:12px;">Aucun état ne change.</div>{/if}
+    <div style="display:flex; gap:6px; margin-top:4px">
+      {#if !draft.newType && draft.typeId}<button onclick={prefill}>Pré-remplir depuis le type</button>{/if}
+      <button onclick={addChange}>+ changement</button>
+    </div>
+    {#if prefillError}<div style="font-size:12px; color:var(--muted)">{prefillError}</div>{/if}
+  </div>
+{/if}
diff --git a/frontend/src/creation/QueueCard.svelte b/frontend/src/creation/QueueCard.svelte
index 5a1f776..c18a0e1 100644
--- a/frontend/src/creation/QueueCard.svelte
+++ b/frontend/src/creation/QueueCard.svelte
@@ -12,7 +12,12 @@
      resync -- the same one-shot-seed reasoning RoleRow.svelte's own
      header describes, just without that component's resync effect
      because this card never needs one. */
-  import { mutationEntityName, mutationAgendaName, mutationDayInfo, shortId, approveMutation, rejectMutation, toggleSelected } from './queue.svelte.js';
+  import { mutationEntityName, mutationAgendaName, mutationDayInfo, shortId, approveMutation, rejectMutation, toggleSelected, queueState } from './queue.svelte.js';
+  import { draftFromPayload, payloadFromDraft } from './eventDraft.svelte.js';
+  import { vocabState, loadVocabulary } from './eventVocab.svelte.js';
+  import { creationState } from './state.svelte.js';
+  import { serverState } from '../lib/serverState.svelte.js';
+  import EventEditor from './EventEditor.svelte';
 
   let { mutation, selected } = $props();
 
@@ -31,6 +36,21 @@
 
   let editable = $derived(mutation.status === 'proposed');
 
+  /* TICKET-0119 (BRIEF-0119-D, Y2): a typed event proposal still in review is
+     edited in the shared EventEditor -- its type, text, participants and
+     their secret, quantity, scopes, and what it changes in the world -- and
+     approved as edited (`payloadFromDraft`). Seeded once, like payloadText:
+     the card never resyncs from the prop. An untyped proposal keeps its
+     payload. */
+  const typedEvent = mutation.mutation_type === 'event_creation' && mutation.status === 'proposed'
+    && !!(mutation.payload && mutation.payload.type_name);
+  let eventDraft = $state(typedEvent ? draftFromPayload(mutation.payload, mutationEntityName) : null);
+  let showJson = $state(!typedEvent);
+
+  $effect(() => {
+    if (typedEvent) loadVocabulary(serverState.worldId);
+  });
+
   function fmtDate(iso) {
     if (!iso) return '—';
     try {
@@ -135,6 +155,7 @@
   }
 
   async function onApprove() {
+    if (eventDraft) payloadText = JSON.stringify(payloadFromDraft(eventDraft, mutation.payload, vocabState.types), null, 2);
     // Validate JSON before sending -- saves a round trip.
     try {
       JSON.parse(payloadText);
@@ -225,7 +246,12 @@
     </div>
   {/if}
 
-  {#if eventLegs}
+  {#if eventDraft && editable}
+    <div class="card-fields" style="margin-bottom:8px;">
+      <EventEditor draft={eventDraft} entities={queueState.entities} playerCharIds={creationState.playerCharIds}
+                   withText={true} />
+    </div>
+  {:else if eventLegs}
     <div class="card-fields" style="margin-bottom:8px;">
       <div class="field-label">Événement</div>
       <div class="row-card" style="flex-direction:row; align-items:center; gap:10px; flex-wrap:wrap;">
@@ -266,10 +292,14 @@
   {/if}
 
   <div class="card-fields">
-    <div>
-      <div class="field-label">Payload</div>
-      <textarea class="payload" rows="5" spellcheck="false" readonly={!editable} bind:value={payloadText}></textarea>
-    </div>
+    {#if showJson}
+      <div>
+        <div class="field-label">Payload</div>
+        <textarea class="payload" rows="5" spellcheck="false" readonly={!editable || !!eventDraft} bind:value={payloadText}></textarea>
+      </div>
+    {:else}
+      <button class="btn-icon" style="font-size:12px" onclick={() => (showJson = true)}>Voir le JSON</button>
+    {/if}
     <div>
       <div class="field-label">Creator notes</div>
       <input class="notes" type="text" placeholder={editable ? 'optional note…' : ''} readonly={!editable} bind:value={notesText}>
diff --git a/frontend/src/creation/Sheet.svelte b/frontend/src/creation/Sheet.svelte
index 3062eb9..b2716ab 100644
--- a/frontend/src/creation/Sheet.svelte
+++ b/frontend/src/creation/Sheet.svelte
@@ -557,7 +557,8 @@
       if (statusEl) { statusEl.className = 'author-status err'; statusEl.textContent = 'Type requis.'; }
       return;
     }
-    Object.assign(body, eventDraftBody());
+    // TICKET-0119 (BRIEF-0119-D): a new event carries its changes; a correction none.
+    Object.assign(body, eventDraftBody(isNewSave));
 
     if (statusEl) { statusEl.className = 'author-status'; statusEl.textContent = isNewSave ? '…' : 'Saving…'; }
     try {
diff --git a/frontend/src/creation/eventDraft.svelte.js b/frontend/src/creation/eventDraft.svelte.js
index 37f52b9..e70598f 100644
--- a/frontend/src/creation/eventDraft.svelte.js
+++ b/frontend/src/creation/eventDraft.svelte.js
@@ -6,31 +6,43 @@
    not Evenements.svelte-local state, because Sheet.svelte's save reads it
    too and a plain <Evenements> instance does not remount on every
    selection change. A participant already written (`saved`) stays: an
-   event's participants are never taken away. */
-export const eventDraftState = $state({
-  typeId: '',
-  quantity: null,
-  participants: [], // {role_id, entity_id, sorte_id, name, secret, saved}
-  customScopes: false,
-  scopes: [], // {scope_type, scope_id, level}
-});
+   event's participants are never taken away.
+
+   TICKET-0119 (BRIEF-0119-D, H1, Y2, M-c): one draft SHAPE for every event
+   editor -- the journal's sheet (this store), the review card of a
+   proposed event, Lore's events -- rendered by EventEditor.svelte. Beyond
+   the above it carries `changes` (what the event changes in the world,
+   pre-filled from its type's effects through POST /api/events/changes) and,
+   for a card, `newType` (a type proposed with the event: its participants
+   name its roles by `role`, no id yet) and its own `title`, `description`,
+   `locationId`. `draftFromPayload` / `payloadFromDraft` read a typed
+   `event_creation` payload into a draft and back, so the card approves
+   what the creator edited. */
+import { api } from './sheetRequest.svelte.js';
+
+export function blankEventDraft() {
+  return {
+    typeId: '', newType: null, quantity: null, participants: [], customScopes: false, scopes: [], changes: [],
+    title: '', description: '', locationId: null,
+  };
+}
+
+export const eventDraftState = $state(blankEventDraft());
 
 export function resetEventDraft() {
-  eventDraftState.typeId = '';
-  eventDraftState.quantity = null;
-  eventDraftState.participants = [];
-  eventDraftState.customScopes = false;
-  eventDraftState.scopes = [];
+  Object.assign(eventDraftState, blankEventDraft());
 }
 
 export function setEventDraftFromEvent(event) {
   eventDraftState.typeId = event.type_id || '';
   eventDraftState.quantity = event.quantity ?? null;
   eventDraftState.participants = (event.participants || []).map((p) => ({
-    role_id: p.role_id, entity_id: p.entity_id, sorte_id: p.sorte_id, name: p.name, secret: !!p.secret, saved: true,
+    role_id: p.role_id, role: p.role_name || '', entity_id: p.entity_id, sorte_id: p.sorte_id, sorte_name: null,
+    name: p.name, secret: !!p.secret, saved: true,
   }));
   eventDraftState.customScopes = true;
   eventDraftState.scopes = (event.scopes || []).map((s) => ({ scope_type: s.scope_type, scope_id: s.scope_id, level: s.level }));
+  eventDraftState.changes = [];
 }
 
 /** Prefill from the AI draft (POST /api/events/generate): its former
@@ -45,28 +57,63 @@ export function setEventDraftFromGenerated(result, types, entities) {
   for (const id of result.involved_entities || []) {
     const entity = entities.find((e) => e.id === id);
     if (entity && role.entity_types.includes(entity.type)) {
-      eventDraftState.participants.push({ role_id: role.id, entity_id: id, sorte_id: null, name: entity.name,
+      eventDraftState.participants.push({ role_id: role.id, role: role.name, entity_id: id, sorte_id: null,
+                                         sorte_name: null, name: entity.name,
                                          secret: !!type.participants_secret, saved: false });
     }
   }
 }
 
+/** A participant fills `role` (a type's role, or a proposed type's, whose
+ *  `id` is null): an entity or a sorte (`kind`), once per role. */
+export function addParticipantTo(draft, role, kind, id, name, defaultSecret) {
+  const inRole = (p) => (role.id ? p.role_id === role.id : !p.role_id && p.role === role.name);
+  const same = (p) => inRole(p) && (kind === 'entity' ? p.entity_id === id
+    : (id ? p.sorte_id === id : p.sorte_name === name));
+  if (draft.participants.some(same)) return;
+  draft.participants.push({ role_id: role.id || null, role: role.name, entity_id: kind === 'entity' ? id : null,
+                            sorte_id: kind === 'sorte' ? id : null, sorte_name: kind === 'sorte' && !id ? name : null,
+                            name, secret: !!defaultSecret, saved: false });
+}
+
+export function removeParticipantFrom(draft, i) {
+  if (draft.participants[i] && !draft.participants[i].saved) {
+    draft.participants.splice(i, 1);
+  }
+}
+
 export function addParticipant(role, kind, id, name, defaultSecret) {
-  const same = (p) => p.role_id === role.id && (kind === 'entity' ? p.entity_id === id : p.sorte_id === id);
-  if (eventDraftState.participants.some(same)) return;
-  eventDraftState.participants.push({ role_id: role.id, entity_id: kind === 'entity' ? id : null,
-                                      sorte_id: kind === 'sorte' ? id : null, name, secret: !!defaultSecret,
-                                      saved: false });
+  addParticipantTo(eventDraftState, role, kind, id, name, defaultSecret);
 }
 
 export function removeParticipant(i) {
-  if (eventDraftState.participants[i] && !eventDraftState.participants[i].saved) {
-    eventDraftState.participants.splice(i, 1);
-  }
+  removeParticipantFrom(eventDraftState, i);
 }
 
-/** The request body's draft part (`EventBody`, beside the plain fields). */
-export function eventDraftBody() {
+/** The changes the type's effects pre-fill on the draft's participants
+ *  (POST /api/events/changes), each with its French `line`. */
+export async function prefilledChanges(draft) {
+  if (!draft.typeId) return [];
+  const data = await api('/api/events/changes', {
+    method: 'POST', headers: { 'Content-Type': 'application/json' },
+    body: JSON.stringify({
+      type_id: draft.typeId,
+      participants: draft.participants.filter((p) => p.role_id && p.entity_id)
+        .map((p) => ({ role_id: p.role_id, entity_id: p.entity_id })),
+    }),
+  });
+  return data.prefilled.map((c) => ({ entity_id: c.entity_id, attribute: c.attribute, mode: c.mode, value: c.value }));
+}
+
+function changesBody(draft) {
+  return (draft.changes || []).filter((c) => c.entity_id && c.attribute)
+    .map((c) => ({ entity_id: c.entity_id, attribute: c.attribute, mode: c.mode || 'set',
+                   value: c.value === '' ? null : c.value }));
+}
+
+/** The request body's draft part (`EventBody`, beside the plain fields).
+ *  A correction carries no change: the event already made them. */
+export function eventDraftBody(isNew = true) {
   return {
     type_id: eventDraftState.typeId,
     quantity: eventDraftState.quantity === null || eventDraftState.quantity === '' ? null
@@ -75,5 +122,48 @@ export function eventDraftBody() {
       role_id: p.role_id, entity_id: p.entity_id, sorte_id: p.sorte_id, secret: p.entity_id ? !!p.secret : null,
     })),
     scopes: eventDraftState.customScopes ? eventDraftState.scopes.map((s) => ({ ...s })) : null,
+    state_changes: isNew ? changesBody(eventDraftState) : [],
+  };
+}
+
+/** A typed `event_creation` payload as a draft the review card edits. */
+export function draftFromPayload(payload, nameOf) {
+  const p = payload || {};
+  return {
+    ...blankEventDraft(),
+    typeId: p.type_id || '',
+    newType: p.new_type && typeof p.new_type === 'object' ? p.new_type : null,
+    quantity: p.quantity ?? null,
+    participants: (p.participants || []).map((x) => ({
+      role_id: x.role_id || null, role: x.role || '', entity_id: x.entity_id || null, sorte_id: x.sorte_id || null,
+      sorte_name: x.sorte_name || null, name: x.entity_id ? nameOf(x.entity_id) : (x.sorte_name || ''),
+      secret: typeof x.secret === 'boolean' ? x.secret : null, saved: false,
+    })),
+    customScopes: Array.isArray(p.scopes),
+    scopes: Array.isArray(p.scopes) ? p.scopes.map((s) => ({ ...s })) : [],
+    changes: (p.state_changes || []).map((c) => ({ ...c })),
+    title: p.title || '', description: p.description || '', locationId: p.location_id || null,
+  };
+}
+
+/** The payload the card approves: the proposal's own keys, the draft's edits
+ *  over them (`type_name` follows the type picked). */
+export function payloadFromDraft(draft, payload, types) {
+  const type = (types || []).find((t) => t.id === draft.typeId);
+  const out = {
+    ...(payload || {}),
+    title: draft.title, description: draft.description || null, location_id: draft.locationId || null,
+    type_id: draft.newType ? null : draft.typeId,
+    type_name: draft.newType ? draft.newType.name : (type ? type.name : (payload || {}).type_name),
+    quantity: draft.quantity === null || draft.quantity === '' ? null : Number(draft.quantity),
+    participants: draft.participants.map((p) => ({
+      role_id: p.role_id, role: p.role, entity_id: p.entity_id, sorte_id: p.sorte_id, sorte_name: p.sorte_name,
+      secret: p.entity_id && typeof p.secret === 'boolean' ? p.secret : null,
+    })),
+    state_changes: changesBody(draft),
   };
+  if (draft.customScopes) out.scopes = draft.scopes.map((s) => ({ ...s }));
+  else delete out.scopes;
+  if (!draft.newType) delete out.new_type;
+  return out;
 }
diff --git a/frontend/src/creation/queue.svelte.js b/frontend/src/creation/queue.svelte.js
index f852b19..fae70fe 100644
--- a/frontend/src/creation/queue.svelte.js
+++ b/frontend/src/creation/queue.svelte.js
@@ -48,6 +48,9 @@ export const queueState = $state({
   loadError: '',
   selectedIds: new Set(),
   batchVerdict: null, // {cls, msg} | null
+  // TICKET-0119 (BRIEF-0119-D, Y2): the world's entities ({id, name, type}),
+  // for the event editor of a proposed event's card.
+  entities: [],
 });
 
 async function api(path, options) {
@@ -80,6 +83,7 @@ export async function loadMutationEntityNames() {
   try {
     const rows = await api('/api/entities');
     _mutationEntityNames = new Map(rows.map((e) => [e.id, e.name]));
+    queueState.entities = rows.filter((e) => e.status === 'active');
   } catch (_err) {
     _mutationEntityNames = new Map();
   }
diff --git a/src/world_engine/cockpit/crud/events.py b/src/world_engine/cockpit/crud/events.py
index 07e9268..7d1330f 100644
--- a/src/world_engine/cockpit/crud/events.py
+++ b/src/world_engine/cockpit/crud/events.py
@@ -9,7 +9,10 @@ W1). `POST /api/events` writes one, `PUT /api/events/{id}` corrects one --
 its type stays and no participant is taken away -- both through
 `writes.events`; every refusal is a 422. Since TICKET-0119 (BRIEF-0119-C,
 M-c) a new event carries its `state_changes` -- what it changes in the
-world, written with it, all or none; a correction carries none.
+world, written with it, all or none; a correction carries none. `POST
+/api/events/changes` is the shared event editor's read (BRIEF-0119-D): the
+changes a type's effects pre-fill on given participants, each with its
+French line, and the French of the changes a card already holds.
 
 `_event_dict` is what the journal shows: the participants with their role
 and their secret (read from their own knowledge row), the scopes with what
@@ -25,6 +28,7 @@ from pydantic import BaseModel, Field
 from sqlmodel import Session as DbSession, select
 
 from ...db import get_session
+from ...event_changes import change_line, type_changes
 from ...event_vocab import DOMAIN_LABELS_FR, type_view
 from ...models import Entity, Event, EventParticipant, EventSorte, FactDefault, Knowledge
 from ...writes.events import (
@@ -124,6 +128,14 @@ class EventBody(BaseModel):
     state_changes: list[StateChangeBody] = Field(default_factory=list)
 
 
+class ChangesBody(BaseModel):
+    """The editor's question: a type and its participants (role id, entity
+    id), and the changes it already holds."""
+    type_id: Optional[str] = None
+    participants: list[ParticipantBody] = Field(default_factory=list)
+    changes: list[StateChangeBody] = Field(default_factory=list)
+
+
 def event_spec(body: EventBody) -> EventSpec:
     return EventSpec(
         type_id=body.type_id, title=body.title, description=body.description, location_id=body.location_id,
@@ -156,6 +168,21 @@ def get_event(event_id: str, db: DbSession = Depends(get_session)) -> dict:
     return _event_dict(_event(db, event_id), db)
 
 
+@router.post("/events/changes")
+def event_changes(body: ChangesBody, db: DbSession = Depends(get_session)) -> dict:
+    """`prefilled`: the changes the type's effects make on the participants
+    (none without a type); `described`: the changes given, each with its
+    French `line` (None when it names nothing of this world). Reads only."""
+    world_id = _world_id(db)
+    view = type_view(db, body.type_id) if body.type_id else None
+    if view is not None and view.world_id != world_id:
+        raise HTTPException(404, f"Event type {body.type_id!r} not found")
+    prefilled = type_changes(db, world_id, view, [(p.role_id, p.entity_id) for p in body.participants])
+    given = [c.model_dump() for c in body.changes]
+    return {"prefilled": [dict(c, line=change_line(db, world_id, c)) for c in prefilled],
+            "described": [dict(c, line=change_line(db, world_id, c)) for c in given]}
+
+
 @router.post("/events", status_code=201)
 def create_event(body: EventBody, db: DbSession = Depends(get_session)) -> dict:
     try:
@@ -181,4 +208,5 @@ def update_event(event_id: str, body: EventBody, db: DbSession = Depends(get_ses
     return _event_dict(event, db)
 
 
-__all__ = ["EVENT_FIELDS", "EventBody", "_event_dict", "create_event", "get_event", "list_events", "update_event"]
+__all__ = ["EVENT_FIELDS", "EventBody", "_event_dict", "create_event", "event_changes", "get_event", "list_events",
+           "update_event"]
diff --git a/src/world_engine/event_payloads.py b/src/world_engine/event_payloads.py
index e8b6bd8..1b2d662 100644
--- a/src/world_engine/event_payloads.py
+++ b/src/world_engine/event_payloads.py
@@ -16,7 +16,9 @@ proposal's payload into that writer's `EventSpec`. Two payload shapes:
   applier's savepoint: refused, nothing is written. Since TICKET-0119 a
   typed payload carries its `state_changes` (M-c) -- pre-filled from its
   type's effects, edited by the creator on the card -- read by
-  `event_changes.payload_changes` for the writer to clean.
+  `event_changes.payload_changes` for the writer to clean; and, edited on
+  the review card (Y2, BRIEF-0119-D), its own `scopes` -- a list, even
+  empty, replaces the type's.
 - untyped (the world tick until TICKET-0119, and every proposal written
   before): `type` (a former category), `involved_entities`,
   `knowledge_status`, `location_id`. It is typed by its domain
@@ -107,11 +109,16 @@ def _typed(db: Session, world_id: str, payload: dict) -> EventSpec:
             role_id=str(role_id), entity_id=p.get("entity_id") or None, sorte_id=sorte_id,
             secret=p.get("secret") if isinstance(p.get("secret"), bool) else None))
     quantity = payload.get("quantity")
+    scopes = None
+    if isinstance(payload.get("scopes"), list):
+        scopes = tuple(EventScopeSpec(str(s.get("scope_type") or ""), s.get("scope_id") or None,
+                                      str(s.get("level") or "knows"))
+                       for s in payload["scopes"] if isinstance(s, dict))
     return EventSpec(
         type_id=str(type_id), title=str(payload.get("title") or ""),
         description=payload.get("description"), location_id=payload.get("location_id") or None,
         quantity=quantity if isinstance(quantity, int) and not isinstance(quantity, bool) else None,
-        participants=tuple(participants), changes=payload_changes(payload.get("state_changes")),
+        participants=tuple(participants), scopes=scopes, changes=payload_changes(payload.get("state_changes")),
     )
 
 
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index b1ed3a9..9e45119 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19558,6 +19558,30 @@ event made.
 **`record_event`.** The journal's writer returns every row it wrote, for
 Lore to record them (INV-57); `write_event` stays its thin form.
 
+## ONE EVENT EDITOR FOR THE JOURNAL, THE REVIEW CARD AND LORE; THE CARD APPROVES WHAT THE CREATOR EDITED (TICKET-0119) -- `EventEditor.svelte` (BRIEF-0119-d, no schema change)
+
+**H1.** `EventEditor.svelte` is the one editor of an event: its type, its
+text and place (on a card), its quantity, its participants role by role
+with their secret, who learns it, and what it changes in the world. The
+journal's sheet, the review card and Lore render it on one draft shape
+(`eventDraft.svelte.js`). A player character is offered no secret box
+(INV-07; the writer forces it anyway). A correction from the journal hides
+the changes: a correction changes no state.
+
+**Y2.** A typed `event_creation` still in review is edited on its card and
+approved as edited (`payloadFromDraft`): type, title, description, place,
+participants and their secret, quantity, its own scopes (a list, even
+empty, replaces the type's -- `event_payloads` reads `scopes` since this
+brief) and its changes. A type proposed with the event (I2) keeps its
+definition; its participants name its roles by name. The raw payload stays
+one click away. An untyped proposal keeps its payload: the tick's typed
+producer is BRIEF-0119-E.
+
+**Pre-fill.** `POST /api/events/changes` makes the type's effects concrete
+on the draft's participants (`event_changes.type_changes`, the one
+pre-fill) and puts each change in French; the editor's « Pré-remplir »
+merges them into the draft's changes. It reads only.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/event_editor.py b/tooling/verify/checks/event_editor.py
new file mode 100644
index 0000000..09cf8e2
--- /dev/null
+++ b/tooling/verify/checks/event_editor.py
@@ -0,0 +1,216 @@
+"""G1 check for TICKET-0119 -- one event editor for the journal, the review card and Lore; the card approves what the creator edited.
+
+BRIEF-0119-D's rules (H1 and Y2 of the conditions series).
+
+EY1 -- the editor's read (fixture, route function). `event_changes` answers
+   `prefilled`: « Ouvrir »'s effect made concrete on the door in its role
+   Cible, with its French `line` (« Porte : Ouvert -> oui »); `described`:
+   each change given, with its line, None for one naming nothing of the
+   world; a type of another world answers 404. It writes nothing.
+EY2 -- the card's payload (fixture, `_apply_mutation`). A typed
+   `event_creation` payload whose `scopes` is an empty list writes the event
+   with no scope (not its type's `world` scope); one with its own scope
+   writes that one; one with no `scopes` key writes its type's; one whose
+   participant carries `secret: true` writes that participant's knowledge
+   secret.
+EY3 -- the surfaces (static). `EventEditor.svelte` edits `draft.changes`
+   (its « Pré-remplir » calls `prefilledChanges`), offers a participant's
+   secret only when `!isPlayer(`, and keeps `draft.newType`'s roles;
+   `Evenements.svelte` renders `<EventEditor` with `withChanges={isNew}`;
+   `QueueCard.svelte` renders `<EventEditor` for a typed proposal and
+   approves `payloadFromDraft(`; `eventDraft.svelte.js` exports
+   `draftFromPayload`, `payloadFromDraft` and `prefilledChanges`, which posts
+   to `/api/events/changes`, and `eventDraftBody` sends `state_changes`
+   only for a new event.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import os
+import pathlib
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
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
+    from world_engine.attributes import attribute_view
+    from world_engine.event_vocab import type_view
+    from world_engine.models import Character, Entity, Location, World
+    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec, write_attribute_definition
+    from world_engine.writes.event_types import EffectSpec, EventTypeSpec, RoleSpec, ScopeSpec, write_event_type
+
+    with Session(engine) as db:
+        other = World(name="Ailleurs", is_active=False)
+        world = World(name="Éditeur", is_active=True)
+        db.add_all([other, world])
+        db.flush()
+        ids = {"world": world.id, "other": other.id}
+        for key, kind, name in (("millys", "character", "Millys"), ("ivo", "character", "Ivo"),
+                                ("porte", "location", "Porte"), ("cour", "location", "Cour")):
+            entity = Entity(world_id=world.id, type=kind, name=name)
+            db.add(entity)
+            db.flush()
+            ids[key] = entity.id
+            db.add(Character(id=entity.id, world_id=world.id, character_type="npc") if kind == "character"
+                   else Location(id=entity.id))
+        ouvert = write_attribute_definition(db, world_id=world.id, spec=DefinitionSpec(
+            name="Ouvert", kind="choice", holder_types=("location",),
+            choices=(ChoiceSpec("non"), ChoiceSpec("oui")), default="non"))
+        db.flush()
+        ids["ouvert"] = ouvert.id
+        ids["oui"] = {label: key for key, label in attribute_view(db, world.id, ouvert.id).choices}["oui"]
+        ouvrir = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
+            name="Ouvrir", roles=(RoleSpec("Ouvreur", ("character",)), RoleSpec("Cible", ("location",))),
+            scopes=(ScopeSpec("world"),), effects=(EffectSpec("Cible", ouvert.id, ids["oui"]),)))
+        foreign = write_event_type(db, world_id=other.id, spec=EventTypeSpec(
+            name="Ailleurs", roles=(RoleSpec("Qui", ("character",)),)))
+        db.flush()
+        ids["ouvrir"], ids["foreign"] = ouvrir.id, foreign.id
+        for role in type_view(db, ouvrir.id).roles:
+            ids[role.name] = role.id
+        db.commit()
+    return ids
+
+
+def check_ey1(engine, ids: dict) -> None:
+    from fastapi import HTTPException
+    from sqlmodel import Session, func, select
+
+    from world_engine.cockpit.crud import events as crud
+    from world_engine.models import AttributeChange, Event
+
+    with Session(engine) as db:
+        before = (db.exec(select(func.count()).select_from(Event)).one(),
+                  db.exec(select(func.count()).select_from(AttributeChange)).one())
+        body = crud.ChangesBody(type_id=ids["ouvrir"], participants=[
+            {"role_id": ids["Ouvreur"], "entity_id": ids["millys"]}, {"role_id": ids["Cible"], "entity_id": ids["porte"]}],
+            changes=[{"entity_id": ids["cour"], "attribute": ids["ouvert"], "value": ids["oui"]},
+                     {"entity_id": "nobody", "attribute": ids["ouvert"], "value": ids["oui"]}])
+        answer = crud.event_changes(body, db)
+        want = {"prefilled": [{"entity_id": ids["porte"], "attribute": ids["ouvert"], "mode": "set",
+                               "value": ids["oui"], "line": "Porte : Ouvert -> oui"}],
+                "described": [{"entity_id": ids["cour"], "attribute": ids["ouvert"], "mode": "set",
+                               "value": ids["oui"], "line": "Cour : Ouvert -> oui"},
+                              {"entity_id": "nobody", "attribute": ids["ouvert"], "mode": "set",
+                               "value": ids["oui"], "line": None}]}
+        if answer != want:
+            fail(f"EY1: event_changes answered {answer}")
+        try:
+            crud.event_changes(crud.ChangesBody(type_id=ids["foreign"]), db)
+            fail("EY1: a type of another world was answered")
+        except HTTPException as exc:
+            if exc.status_code != 404:
+                fail(f"EY1: a type of another world answered {exc.status_code}")
+        after = (db.exec(select(func.count()).select_from(Event)).one(),
+                 db.exec(select(func.count()).select_from(AttributeChange)).one())
+        if after != before:
+            fail("EY1: event_changes wrote rows")
+
+
+def check_ey2(engine, ids: dict) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.cockpit.routes.mutations import _apply_mutation
+    from world_engine.models import Event, FactDefault, Knowledge, ProposedMutation
+    from world_engine.writes.events import event_fact
+
+    base = {"type_id": ids["ouvrir"], "participants": [{"role_id": ids["Ouvreur"], "entity_id": ids["millys"]}]}
+    cases = (
+        ("Sans portée", {"scopes": []}, []),
+        ("Portée propre", {"scopes": [{"scope_type": "location", "scope_id": ids["cour"], "level": "rumor"}]},
+         [("location", ids["cour"], "rumor")]),
+        ("Celle du type", {}, [("world", None, "knows")]),
+    )
+    with Session(engine) as db:
+        for title, extra, want in cases:
+            mut = ProposedMutation(world_id=ids["world"], source_type="world_tick", tick_id="t",
+                                   mutation_type="event_creation", target_table="event",
+                                   payload={"title": title, **base, **extra}, status="approved")
+            db.add(mut)
+            db.flush()
+            error = _apply_mutation(mut, db)
+            db.commit()
+            event = db.exec(select(Event).where(Event.title == title)).first()
+            fact = event_fact(db, event.id) if event else None
+            got = sorted((d.scope_type, d.scope_id, d.level) for d in db.exec(
+                select(FactDefault).where(FactDefault.fact_id == (fact.id if fact else ""))))
+            if error or got != want:
+                fail(f"EY2: « {title} » gave {error!r}, scopes {got}")
+        secret = ProposedMutation(world_id=ids["world"], source_type="world_tick", tick_id="t",
+                                  mutation_type="event_creation", target_table="event", status="approved",
+                                  payload={"title": "En secret", "type_id": ids["ouvrir"], "participants": [
+                                      {"role_id": ids["Ouvreur"], "entity_id": ids["ivo"], "secret": True}]})
+        db.add(secret)
+        db.flush()
+        error = _apply_mutation(secret, db)
+        db.commit()
+        event = db.exec(select(Event).where(Event.title == "En secret")).first()
+        row = db.exec(select(Knowledge).where(Knowledge.entity_id == ids["ivo"], Knowledge.fact_id == (
+            event_fact(db, event.id).id if event else ""))).first()
+        if error or row is None or not row.is_secret:
+            fail(f"EY2: a participant's secret on the card gave {error!r}, row {row and row.is_secret}")
+
+
+def check_ey3() -> None:
+    wanted = {
+        "EventEditor.svelte": ("draft.changes", "prefilledChanges(draft)", "!isPlayer(", "draft.newType.roles"),
+        "Evenements.svelte": ("<EventEditor", "withChanges={isNew}"),
+        "QueueCard.svelte": ("<EventEditor", "payloadFromDraft(eventDraft"),
+        "eventDraft.svelte.js": ("export function draftFromPayload", "export function payloadFromDraft",
+                                 "export async function prefilledChanges", "'/api/events/changes'",
+                                 "state_changes: isNew ? changesBody(eventDraftState) : []"),
+    }
+    for name, needles in wanted.items():
+        path = FRONT / name
+        if not path.exists():
+            fail(f"EY3: {name} is missing")
+            continue
+        text = path.read_text(encoding="utf-8")
+        for needle in needles:
+            if needle not in text:
+                fail(f"EY3: {name} lacks {needle}")
+
+
+def main() -> int:
+    _fresh_db()
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    ids = _fixture(engine)
+    rules = (("EY1", lambda: check_ey1(engine, ids)), ("EY2", lambda: check_ey2(engine, ids)), ("EY3", check_ey3))
+    for name, rule in rules:
+        try:
+            rule()
+        except Exception as exc:  # a crash is that rule's failure, never a pass
+            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: event_editor -- one editor for the journal, the review card and Lore; it pre-fills an event's "
+          "changes from its type; the card approves its edits, scopes and secrets included")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/event_writes.py b/tooling/verify/checks/event_writes.py
index a612e64..b6f8a86 100644
--- a/tooling/verify/checks/event_writes.py
+++ b/tooling/verify/checks/event_writes.py
@@ -41,10 +41,11 @@ EC6 -- the sheet (static). `EVENT_FIELDS` names `title`, `description`,
    `location_id` and nothing else; `crud/events.py` and
    `cockpit/mutations.py`'s `event_creation` applier name no
    `knowledge_status` and no `EventEntity`; `Evenements.svelte` renders the
+   shared `EventEditor.svelte` on its draft (TICKET-0119), which renders the
    type select `event-f-type_id`, the quantity, each role's participants with
-   their secret, and the scopes; `Sheet.svelte` sends `eventDraftBody()`;
-   `eventDraft.svelte.js` exports `eventDraftBody` and never removes a
-   `saved` participant.
+   their secret, and the scopes; `Sheet.svelte` sends
+   `eventDraftBody(isNewSave)`; `eventDraft.svelte.js` exports
+   `eventDraftBody` and never removes a `saved` participant.
 
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
@@ -399,11 +400,14 @@ def check_ec6() -> None:
         for needle in ("knowledge_status", "EventEntity"):
             if needle in text:
                 fail(f"EC6: {name} names {needle}")
+    # TICKET-0119 (BRIEF-0119-D): the sheet's editing moved into the shared
+    # EventEditor.svelte, which Evenements.svelte renders on its draft.
     needles = {
-        "Evenements.svelte": ('id="event-f-type_id"', 'id="event-f-quantity"', "bind:checked={p.secret}",
-                              "eventDraftState.scopes", "role.accepts_sorte"),
-        "Sheet.svelte": ("eventDraftBody()",),
-        "eventDraft.svelte.js": ("export function eventDraftBody", "!eventDraftState.participants[i].saved"),
+        "Evenements.svelte": ("<EventEditor draft={eventDraftState}",),
+        "EventEditor.svelte": ('id="event-f-type_id"', 'id="event-f-quantity"', "bind:checked={p.secret}",
+                               "draft.scopes", "role.accepts_sorte"),
+        "Sheet.svelte": ("eventDraftBody(isNewSave)",),
+        "eventDraft.svelte.js": ("export function eventDraftBody", "!draft.participants[i].saved"),
     }
     for name, wanted in needles.items():
         path = FRONT / name
````

2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
4. Run the checks below, then the full corpus.

## Scope OUT

- Editing a proposed type's definition on the card (it is approved as proposed, I2).
- An untyped proposal's editor (it keeps its payload; the tick's typed items are BRIEF-0119-E).
- Lore's events -- BRIEF-0119-G.
- Every later brief of this lot: BRIEF-0119-E, F, G.

## Invariants to defend

INV-07: a player character is offered no secret box, and `writes/events._clean_participant` forces it anyway (EC1 still guards). INV-49/INV-50/INV-53: `EventEditor` is a component rendered inside existing islands, no tab and no island added (`creation_island.py`, `page_contract.py`). INV-55: the card's `$effect` assigns no `$state` it reads. Canon is still written only on approval (`_apply_mutation`) or by the journal's route.

## Decision rights

STOP:
- The card would write canon itself instead of approving a payload through `/api/mutations/{id}/approve`.
- A Mini-RECON anchor that does not hold.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `npm run build` names a different asset hash than the prototype's: commit what it builds (`frontend_build_fresh.py` judges the manifest, not the name).
- A check other than this brief's own fails on a line count or a docstring count this diff moved (`file_map.py`, `decisions_index.py`): regenerate `FILE_MAP.md` / `DECISIONS_INDEX.md` and rerun.

REPORT-ONLY:
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.
- Log lines a check prints before its verdict (`[skip] …`, a Starlette deprecation warning).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/`.
- `python tooling/verify/checks/event_editor.py` -> `PASS`.
- `python tooling/verify/checks/event_writes.py` -> `PASS`.
- `python tooling/verify/checks/event_analyzer.py` -> `PASS`.
- `python tooling/verify/checks/frontend_build_fresh.py` -> `PASS`.
- `python tooling/verify/checks/creation_island.py` -> `PASS`.
- `python tooling/verify/checks/page_contract.py` -> `PASS`.
- `python tooling/verify/checks/effect_self_write.py` -> `PASS`.
- `python tooling/verify/checks/module_budget.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (159 on the prototype).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **EY1** -- `cockpit/crud/events.py event_changes`: `    if view is not None and view.world_id != world_id:` -> `    if False:`
  - **EY2** -- `event_payloads.py _typed`: `    if isinstance(payload.get("scopes"), list):` -> `    if False:`
  - **EY3** -- `frontend/src/creation/eventDraft.svelte.js eventDraftBody`: `    state_changes: isNew ? changesBody(eventDraftState) : [],` -> `    state_changes: changesBody(eventDraftState),`
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated; the static build rebuilt.
