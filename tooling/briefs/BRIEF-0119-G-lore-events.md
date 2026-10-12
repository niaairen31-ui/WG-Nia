<!-- slug: lore-events -->
# BRIEF 0119-G — "Lore declares events -- in the writing panel's proposal, and by a button straight to the journal (no schema change)"

Lot: LOT-0119-event-producers.md (authoritative on conflict)
Depends on: BRIEF-0119-A (C-01), C (C-04, C-05), D (C-06)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0119-F's commit).

- `src/world_engine/lore_write_draft.py` -> `def _values(context: DraftContext, statement: str, answers: str = "") -> dict[str, str]:`
- `src/world_engine/lore_write_apply.py` -> `class _Writer:` with no `event` method
- `src/world_engine/models/pipeline.py` -> `LORE_ENTRY_ROW_TABLES` naming `event` (BRIEF-0119-A's)
- `tooling/verify/checks/lore_write.py` -> `    want = {"/api/lore/write/questions", "/api/lore/write/draft", "/api/lore/write/commit",` (F1b, five paths)
- `frontend/src/creation/EventEditor.svelte` -> props with no `canPrefill` (BRIEF-0119-D's)
- No `scripts/apply_ticket_0119_lore_prompt.py`, no `tooling/verify/checks/event_lore.py`.

## Facts carried

### R-09 — Lore's writing path [M]
Opened: `src/world_engine/lore_write_draft.py` (:124 `_values`, :248
`draft_proposal`); `src/world_engine/lore_write_apply.py` (:178 `validate`
refuses a proposal writing no fact, membership or control; :202 `_Writer`;
:323 `apply_proposal`); `src/world_engine/models/pipeline.py` (:326
`LORE_ENTRY_ROW_TABLES`, :350 its CHECK: seven tables); `src/world_engine/
lore_write_read.py:36` (`_label` maps the seven); `scripts/seed_pilot.py`
(:1910 / :1957 the proposal prompt, :1978 `LORE_WRITE_PROMPT_HEADS`, :1996
its variables); `tooling/verify/checks/lore_write.py:651` (F1b pins the
panel's calls); CLAUDE.md INV-57 (every row recorded).
Consequence: A widens `lore_entry_row`; G records every row an event wrote.

## Contracts

### C-01 — v2.26
Produced by: BRIEF-0119-A   Consumed by: B-G
`event_type_effect` (`world_id`, `type_id`, `role_id`, `definition_id` XOR
`system_key`, `mode` in `EVENT_EFFECT_MODES = ("set", "add")`, exactly one of
`choice_id` / `system_value` / `integer_value` / `value_role_id`, `add` only
with `integer_value`, `position`; indexes `idx_event_type_effect_type`,
`idx_event_type_effect_definition`); `attribute_change.event_id` (FK
`event`, `idx_attribute_change_event`); `LORE_ENTRY_ROW_TABLES` gains
`event`, `event_participant`, `attribute_value`, `attribute_change`.

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

### C-09 — Lore's events
Produced by: BRIEF-0119-G   Consumed by: (none)
Draft item: `{ref v1.., type_id | None, type_name, new_type?, title,
description, quantity, location_ref, participants [{role_id | None, role,
entity_ref | sorte_id, secret}], state_changes [{entity_ref, attribute,
mode, value}]}`; proposal item: the same without `new_type`, plus
`scopes [{scope_type, scope_ref, level}]` when the creator chose them.
Seed: `LORE_PROPOSAL_VARIABLES`, `LORE_PROPOSAL_FRAGMENTS_0119`.

## Context

Nia declares what happened in Lore. U1: the writing panel's proposal also holds events -- typed, by role, on the statement's entities -- edited in the shared editor and written at commit through the journal's writer, every row recorded (INV-57). G3: a button declares one event straight to the journal. A type the world lacks is created from its card before the commit, as in the interpreter.

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `lore_write_draft.py`: the vocabulary in the prompt's values; `_event_type`, `_event_participant`, `_event` read the model's events fail-closed, changes pre-filled on the world's entities by ref;
   - `lore_write_apply.py`: `_validate_event` (a `new_type` refuses), `_event_payload`, `_Writer.event` through `spec_from_payload` and `record_event`, every row recorded once; `lore_write_read.py` labels an event's rows;
   - frontend: `EventEditor.svelte` `canPrefill`; `eventDraft.svelte.js` `eventBodyFrom`; `writePanel.svelte.js` (the events as editor drafts by ref, `eventEntities`, `createProposedType`, `declareState`, `openDeclare`, `saveDeclared`, the events in the proposal and its blockers); `WritePanel.svelte` (the events' cards, the proposed type's form, « Déclarer un événement »);
   - `scripts/seed_pilot.py`: the proposal prompt's events, `LORE_PROPOSAL_VARIABLES`, `LORE_PROPOSAL_FRAGMENTS_0119`; `scripts/apply_ticket_0119_lore_prompt.py` (new);
   - `lore_write.py` F1b allows `/api/event-types` and `/api/events`; `event_editor.py` EY3 follows `eventBodyFrom`; creates check `event_lore.py` (EL1-EL4); appends the decision entry above the footer.
   The files it touches, exactly:
   - frontend/src/creation/EventEditor.svelte
   - frontend/src/creation/eventDraft.svelte.js
   - frontend/src/lore/WritePanel.svelte
   - frontend/src/lore/writePanel.svelte.js
   - scripts/apply_ticket_0119_lore_prompt.py
   - scripts/seed_pilot.py
   - src/world_engine/lore_write_apply.py
   - src/world_engine/lore_write_draft.py
   - src/world_engine/lore_write_read.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/event_editor.py
   - tooling/verify/checks/event_lore.py
   - tooling/verify/checks/lore_write.py

````diff
diff --git a/frontend/src/creation/EventEditor.svelte b/frontend/src/creation/EventEditor.svelte
index b39987d..de5f190 100644
--- a/frontend/src/creation/EventEditor.svelte
+++ b/frontend/src/creation/EventEditor.svelte
@@ -17,7 +17,9 @@
      dropped, and new ones added -- an entity, a state that applies to it, a
      value of the state's kind (an integer set or added, D3). `withChanges`
      off (a correction from the journal) hides them: a correction changes no
-     state.
+     state. `canPrefill` off (Lore, whose entities are the statement's refs
+     until the commit) hides « Pré-remplir »: Lore's draft arrives
+     pre-filled.
 
      `entities` are the world's ({id, name, type}); `playerCharIds` a Set of
      the player characters' ids. The types, sortes, levels and states come
@@ -28,6 +30,7 @@
 
   let {
     draft, entities = [], playerCharIds = null, typeFixed = false, withText = false, withChanges = true,
+    canPrefill = true,
   } = $props();
 
   let prefillError = $state('');
@@ -264,7 +267,7 @@
     {/each}
     {#if !draft.changes.length}<div style="color:var(--muted); font-size:12px;">Aucun état ne change.</div>{/if}
     <div style="display:flex; gap:6px; margin-top:4px">
-      {#if !draft.newType && draft.typeId}<button onclick={prefill}>Pré-remplir depuis le type</button>{/if}
+      {#if canPrefill && !draft.newType && draft.typeId}<button onclick={prefill}>Pré-remplir depuis le type</button>{/if}
       <button onclick={addChange}>+ changement</button>
     </div>
     {#if prefillError}<div style="font-size:12px; color:var(--muted)">{prefillError}</div>{/if}
diff --git a/frontend/src/creation/eventDraft.svelte.js b/frontend/src/creation/eventDraft.svelte.js
index e70598f..8a29a84 100644
--- a/frontend/src/creation/eventDraft.svelte.js
+++ b/frontend/src/creation/eventDraft.svelte.js
@@ -111,21 +111,25 @@ function changesBody(draft) {
                    value: c.value === '' ? null : c.value }));
 }
 
-/** The request body's draft part (`EventBody`, beside the plain fields).
- *  A correction carries no change: the event already made them. */
-export function eventDraftBody(isNew = true) {
+/** A draft's body for POST /api/events (`EventBody`, beside the plain
+ *  fields). A correction carries no change: the event already made them. */
+export function eventBodyFrom(draft, isNew = true) {
   return {
-    type_id: eventDraftState.typeId,
-    quantity: eventDraftState.quantity === null || eventDraftState.quantity === '' ? null
-      : Number(eventDraftState.quantity),
-    participants: eventDraftState.participants.map((p) => ({
+    type_id: draft.typeId,
+    quantity: draft.quantity === null || draft.quantity === '' ? null : Number(draft.quantity),
+    participants: draft.participants.map((p) => ({
       role_id: p.role_id, entity_id: p.entity_id, sorte_id: p.sorte_id, secret: p.entity_id ? !!p.secret : null,
     })),
-    scopes: eventDraftState.customScopes ? eventDraftState.scopes.map((s) => ({ ...s })) : null,
-    state_changes: isNew ? changesBody(eventDraftState) : [],
+    scopes: draft.customScopes ? draft.scopes.map((s) => ({ ...s })) : null,
+    state_changes: isNew ? changesBody(draft) : [],
   };
 }
 
+/** The journal sheet's draft part, from its store. */
+export function eventDraftBody(isNew = true) {
+  return eventBodyFrom(eventDraftState, isNew);
+}
+
 /** A typed `event_creation` payload as a draft the review card edits. */
 export function draftFromPayload(payload, nameOf) {
   const p = payload || {};
diff --git a/frontend/src/lore/WritePanel.svelte b/frontend/src/lore/WritePanel.svelte
index 4e65f6d..19a71f6 100644
--- a/frontend/src/lore/WritePanel.svelte
+++ b/frontend/src/lore/WritePanel.svelte
@@ -3,14 +3,23 @@
      shell: the creator writes lore in prose, answers at most one round of
      questions, corrects the proposal and commits it. A second bounded
      reopening of the shell's read-only lock (H1); the consultation view is
-     untouched. Every entity is chosen from a list. */
+     untouched. Every entity is chosen from a list.
+
+     TICKET-0119 (BRIEF-0119-G, U1, G3): the proposal's events, each in the
+     shared EventEditor on the statement's entities (by ref), a proposed type
+     created from its card first; and « Déclarer un événement », one event
+     written straight to the journal. */
   import { serverState } from '../lib/serverState.svelte.js';
   import {
     writeState, ENTITY_TYPES, SCOPE_TYPES, LEVELS, reloadForWorld, askQuestions, makeDraft,
     pickExisting, refLabel, liveRefs, scopeOptions, scopeValue, pickScope, setScopeType,
     addKnower, addDefault, removeAt, blockers,
     commit, restart, loadEntries, worldEntity,
+    eventEntities, createProposedType, declareState, openDeclare, saveDeclared,
   } from './writePanel.svelte.js';
+  import { vocabState } from '../creation/eventVocab.svelte.js';
+  import EventEditor from '../creation/EventEditor.svelte';
+  import EventTypeForm from '../creation/EventTypeForm.svelte';
 
   let { visible = false } = $props();
 
@@ -54,11 +63,23 @@
       disabled={writeState.busy || writeState.stage !== 'text'}
     ></textarea>
     {#if writeState.stage === 'text'}
-      <div>
+      <div class="row">
         <button disabled={writeState.busy || !writeState.statement.trim()} onclick={() => askQuestions()}>
           {writeState.busy ? '⟳ Lecture…' : 'Proposer des faits'}
         </button>
+        <button disabled={writeState.busy || declareState.open} onclick={() => openDeclare()}>Déclarer un événement</button>
       </div>
+      {#if declareState.saved}<div class="muted">{declareState.saved}</div>{/if}
+      {#if declareState.open && declareState.draft}
+        <div class="card">
+          <EventEditor draft={declareState.draft} entities={writeState.entities || []} withText={true} />
+          {#if declareState.error}<div class="r-err">{declareState.error}</div>{/if}
+          <div class="row">
+            <button disabled={declareState.busy} onclick={() => saveDeclared()}>Écrire l'événement</button>
+            <button onclick={() => { declareState.open = false; declareState.draft = null; }}>Annuler</button>
+          </div>
+        </div>
+      {/if}
     {/if}
 
     {#if writeState.stage === 'questions'}
@@ -196,6 +217,22 @@
         {/each}
       {/if}
 
+      {#if (draft.events || []).length}
+        <h3>Événements</h3>
+        {#each draft.events as ev, ei (ev.ref)}
+          <div class="card">
+            <div class="row"><strong>{ev.title}</strong>
+              <button onclick={() => removeAt(draft.events, ei)}>Retirer</button></div>
+            {#if ev.newType && ev.typeEdit}
+              <div class="muted">Type proposé — crée-le avant d'écrire :</div>
+              <EventTypeForm draft={ev.typeEdit} vocab={vocabState} />
+              <button disabled={writeState.busy} onclick={() => createProposedType(ev)}>Créer ce type</button>
+            {/if}
+            <EventEditor draft={ev} entities={eventEntities()} withText={true} canPrefill={false} />
+          </div>
+        {/each}
+      {/if}
+
       {#each blocking as b, i (i)}<div class="r-err">{b}</div>{/each}
       <div class="row">
         <button disabled={writeState.busy || blocking.length > 0} onclick={() => commit()}>
diff --git a/frontend/src/lore/writePanel.svelte.js b/frontend/src/lore/writePanel.svelte.js
index 47677c5..a231d39 100644
--- a/frontend/src/lore/writePanel.svelte.js
+++ b/frontend/src/lore/writePanel.svelte.js
@@ -16,8 +16,20 @@
    TICKET-0103 (BRIEF-0103-D): `attemptId` names one use of the panel, from
    the text to its commit, for the usage journal. A fresh one comes with
    every blank state (a new text, a world change); every request of the use
-   carries it. */
+   carries it.
+
+   TICKET-0119 (BRIEF-0119-G, U1, G3): the draft's EVENTS are edited in the
+   shared EventEditor, on drafts whose entity ids are the statement's refs
+   (`eventEntities`: the entities kept, by ref) -- mapped back to refs in
+   the proposal, made ids by the server at commit. A type the model
+   proposed is created from its card first (`createProposedType`, POST
+   /api/event-types), its participants then bound to its roles by name.
+   « Déclarer un événement » (`declareState`) writes one event straight to
+   the journal (POST /api/events), with the world's entities. */
 import { api } from '../creation/sheetRequest.svelte.js';
+import { serverState } from '../lib/serverState.svelte.js';
+import { blankEventDraft, eventBodyFrom } from '../creation/eventDraft.svelte.js';
+import { typeBody, typeDraft, loadVocabulary, vocabState } from '../creation/eventVocab.svelte.js';
 
 export const ENTITY_TYPES = Object.freeze([
   { value: 'character', label: 'personnage' },
@@ -45,6 +57,9 @@ function blank() {
   };
 }
 
+/* G3: one event declared straight to the journal, no statement. */
+export const declareState = $state({ open: false, draft: null, busy: false, error: '', saved: '' });
+
 export const writeState = $state(blank());
 
 export function reloadForWorld() {
@@ -98,11 +113,75 @@ async function draftNow() {
     else if (entity.status === 'ambiguous') entity.decision = '';
     else entity.decision = entity.type ? 'create' : '';
   }
+  draft.events = (draft.events || []).map((item) => loreEventDraft(item, draft));
+  if (draft.events.length) await loadVocabulary(serverState.worldId);
   writeState.draft = draft;
   writeState.result = null;
   writeState.stage = 'draft';
 }
 
+/* An event of the draft as the shared editor's draft: its entity ids are
+   the statement's refs. */
+function loreEventDraft(item, draft) {
+  const named = (ref) => ((draft.entities || []).find((e) => e.ref === ref) || {}).name || ref;
+  return {
+    ...blankEventDraft(), ref: item.ref, typeId: item.type_id || '', newType: item.new_type || null,
+    typeEdit: item.new_type ? typeDraft(item.new_type) : null, quantity: item.quantity ?? null,
+    participants: (item.participants || []).map((p) => ({
+      role_id: p.role_id, role: p.role, entity_id: p.entity_ref, sorte_id: p.sorte_id, sorte_name: null,
+      name: p.entity_ref ? named(p.entity_ref) : '', secret: p.secret, saved: false,
+    })),
+    changes: (item.state_changes || []).map((c) => ({ entity_id: c.entity_ref, attribute: c.attribute,
+                                                     mode: c.mode, value: c.value })),
+    title: item.title || '', description: item.description || '', locationId: item.location_ref || null,
+  };
+}
+
+/** The statement's kept entities, by ref, for the event editor. */
+export function eventEntities() {
+  return liveRefs().map((e) => ({ id: e.ref, name: refLabel(e.ref), type: e.type }));
+}
+
+/** A proposed type, created as the creator edited it; the event then names
+ *  its roles by id. */
+export function createProposedType(event) {
+  return run(async () => {
+    const saved = await post('/api/event-types', typeBody(event.typeEdit, true));
+    await loadVocabulary(serverState.worldId);
+    const type = vocabState.types.find((t) => t.id === saved.type.id);
+    const byName = Object.fromEntries((type ? type.roles : []).map((r) => [r.name, r.id]));
+    event.typeId = saved.type.id;
+    event.newType = null;
+    event.typeEdit = null;
+    event.participants = event.participants.filter((p) => byName[p.role]).map((p) => ({ ...p, role_id: byName[p.role] }));
+  });
+}
+
+export function openDeclare() {
+  return run(async () => {
+    await loadWorldEntities();
+    await loadVocabulary(serverState.worldId);
+    Object.assign(declareState, { open: true, draft: blankEventDraft(), error: '', saved: '' });
+  });
+}
+
+export async function saveDeclared() {
+  const draft = declareState.draft;
+  if (!draft || !draft.typeId || !draft.title.trim()) { declareState.error = 'Un titre et un type sont requis.'; return; }
+  declareState.busy = true;
+  declareState.error = '';
+  try {
+    const body = { title: draft.title, description: draft.description || null, location_id: draft.locationId || null,
+                   ...eventBodyFrom(draft, true) };
+    const saved = await post('/api/events', body);
+    Object.assign(declareState, { open: false, draft: null, saved: `Événement écrit : ${saved.title}` });
+  } catch (e) {
+    declareState.error = e.message;
+  } finally {
+    declareState.busy = false;
+  }
+}
+
 export function makeDraft() {
   return run(draftNow);
 }
@@ -212,12 +291,36 @@ export function blockers() {
       if (d.scope_type !== 'world' && !d.scope_ref) out.push('Une portée ne nomme pas son entité.');
     }
   }
-  if (!draft.facts.length && !draft.memberships.length && !draft.controls.length) {
+  for (const ev of draft.events || []) {
+    if (ev.newType) out.push(`Crée le type « ${ev.newType.name} » ou retire l'événement « ${ev.title} ».`);
+    else if (!ev.typeId) out.push(`Choisis le type de l'événement « ${ev.title} ».`);
+  }
+  if (!draft.facts.length && !draft.memberships.length && !draft.controls.length && !(draft.events || []).length) {
     out.push('La proposition n’écrit rien.');
   }
   return out;
 }
 
+function eventProposal(ev, keep) {
+  const out = {
+    ref: ev.ref, type_id: ev.typeId, title: ev.title, description: ev.description || null,
+    quantity: ev.quantity === null || ev.quantity === '' ? null : Number(ev.quantity),
+    location_ref: keep(ev.locationId) ? ev.locationId : null,
+    participants: ev.participants.filter((p) => !p.entity_id || keep(p.entity_id)).map((p) => ({
+      role_id: p.role_id, role: p.role, entity_ref: p.entity_id || null, sorte_id: p.sorte_id || null,
+      secret: p.entity_id && typeof p.secret === 'boolean' ? p.secret : null,
+    })),
+    state_changes: ev.changes.filter((c) => c.entity_id && c.attribute && keep(c.entity_id)).map((c) => ({
+      entity_ref: c.entity_id, attribute: c.attribute, mode: c.mode || 'set', value: c.value === '' ? null : c.value,
+    })),
+  };
+  if (ev.customScopes) {
+    out.scopes = ev.scopes.filter((sc) => sc.scope_type === 'world' || keep(sc.scope_id))
+      .map((sc) => ({ scope_type: sc.scope_type, scope_ref: sc.scope_type === 'world' ? null : sc.scope_id, level: sc.level }));
+  }
+  return out;
+}
+
 function toProposal() {
   const draft = writeState.draft;
   const dropped = new Set(draft.entities.filter((e) => e.decision === 'text').map((e) => e.ref));
@@ -247,6 +350,7 @@ function toProposal() {
     questions: writeState.questions.join('\n') || null, entities, facts,
     memberships: draft.memberships.filter((m) => keep(m.entity_ref) && keep(m.faction_ref)),
     controls: draft.controls.filter((c) => keep(c.owner_ref) && keep(c.location_ref)),
+    events: (draft.events || []).map((ev) => eventProposal(ev, keep)),
   };
 }
 
diff --git a/scripts/apply_ticket_0119_lore_prompt.py b/scripts/apply_ticket_0119_lore_prompt.py
new file mode 100644
index 0000000..d6393bb
--- /dev/null
+++ b/scripts/apply_ticket_0119_lore_prompt.py
@@ -0,0 +1,99 @@
+"""One-shot, idempotent delivery of the TICKET-0119 Lore proposal prompt
+update onto the live DB (BRIEF-0119-G, U1): the lore writing call reads the
+world's event types -- the `t` list, a new variable `event_types` -- and
+its sortes (`sortes`), and may return events, or a type the world lacks.
+
+Like `apply_ticket_0119_tick_prompt.py`, it edits the CURRENT version of
+`pt-lore-statement-to-proposal` fragment by fragment, so an edit the
+creator made in the Prompts tab is kept. The fragments are
+`seed_pilot.LORE_PROPOSAL_FRAGMENTS_0119` (single source: the seed's texts
+hold each new fragment). Per fragment: its new text present ->
+already done (looked for first: an old fragment may stand inside its own
+new text); else its old text present -> replaced; neither -> reported, to
+be edited by hand. The head's variables are first set to the seed's
+(`write_prompt_variables`), since a new version may only use declared
+placeholders.
+
+History is sacred: a changed text lands as a new `prompt_version` row
+through `write_prompt_version`, the old one untouched. Touches nothing else.
+Safe to re-run: an already-updated head prints "unchanged".
+
+Run after `migrate_v2_26_event_effects.py`:
+
+    python scripts/apply_ticket_0119_lore_prompt.py
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+from pathlib import Path
+
+_env = os.environ.get("WORLD_ENGINE_ENV")
+if _env not in ("prod", "test"):
+    print(
+        "apply_ticket_0119_lore_prompt.py refuses to run unless "
+        f"WORLD_ENGINE_ENV is 'prod' or 'test' (got: {_env or 'unset'})."
+    )
+    sys.exit(1)
+
+SRC = Path(__file__).resolve().parent.parent / "src"
+sys.path.insert(0, str(SRC))
+sys.path.insert(0, str(Path(__file__).resolve().parent))
+
+from sqlmodel import Session  # noqa: E402
+
+import seed_pilot  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+from world_engine.models import PromptTemplate  # noqa: E402
+from world_engine.prompt_store import current_prompt  # noqa: E402
+from world_engine.writes import write_prompt_version  # noqa: E402
+from world_engine.writes.prompts import write_prompt_variables  # noqa: E402
+
+HEAD_ID = "pt-lore-statement-to-proposal"
+NOTE = "TICKET-0119 BRIEF-0119-G -- Lore declares events by type, role and ref (U1)"
+
+
+def apply_fragments(texts: dict[str, str]) -> tuple[dict[str, str], list[str]]:
+    """`texts` with every fragment applied where its old text stands; the
+    fragments found in neither form."""
+    out = dict(texts)
+    missing = []
+    for field, old, new in seed_pilot.LORE_PROPOSAL_FRAGMENTS_0119:
+        if new in out[field]:
+            continue
+        if old in out[field]:
+            out[field] = out[field].replace(old, new)
+        else:
+            missing.append(f"{field}: {old[:60]}…")
+    return out, missing
+
+
+def main() -> None:
+    # A fragment's text holds characters a Windows console cannot encode; a
+    # report line must never crash the delivery.
+    sys.stdout.reconfigure(errors="replace")
+    with Session(engine) as session:
+        head = session.get(PromptTemplate, HEAD_ID)
+        if head is None:
+            print(f"{HEAD_ID}: head not found -- nothing to do (the seed creates it)")
+            return
+        write_prompt_variables(session, template_id=head.id,
+                               variables=list(seed_pilot.LORE_PROPOSAL_VARIABLES))
+        current = current_prompt(session, head)
+        texts, missing = apply_fragments({"system_prompt": current.system_prompt,
+                                          "user_template": current.user_template})
+        for line in missing:
+            print(f"{HEAD_ID}: fragment not found, edit by hand -- {line}")
+        if texts == {"system_prompt": current.system_prompt, "user_template": current.user_template}:
+            session.commit()
+            print(f"{HEAD_ID}: unchanged (v{current.version_number})")
+            return
+        version = write_prompt_version(session, template_id=head.id, system_prompt=texts["system_prompt"],
+                                       user_template=texts["user_template"], note=NOTE)
+        session.commit()
+        print(f"{HEAD_ID}: v{current.version_number} -> v{version.version_number}")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/scripts/seed_pilot.py b/scripts/seed_pilot.py
index 415fda4..1660afb 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -2005,13 +2005,26 @@ entrent dans une faction ({"entity_ref", "faction_ref"}) ; "controls" \
 liste qui possède ou dirige un lieu ({"owner_ref", "location_ref"}). La \
 possession s'écrit aussi comme un fait de facette "statut".
 
+ÉVÉNEMENTS. Quand le texte dit qu'il S'EST PASSÉ quelque chose (un \
+combat, une mort, un pacte, un incendie), liste-le dans "events" : \
+"event_type" est le code d'un type de la liste des types d'événements \
+("t2") ; "participants" nomme chaque participant par le rôle qu'il tient : \
+{"role": "...", "ref": "e1"} pour une entité, {"role": "...", "sorte": \
+"Loup"} pour une sorte de la liste ; "quantity" seulement si le type se \
+compte ; "place_ref" le lieu ; "title" et "description" en une phrase. \
+Si aucun type ne dit ce qui s'est passé, propose-le dans "new_type" \
+({"name": "...", "domain": "military|political|magical|criminal|social|mystery|other", \
+"roles": [{"name": "...", "for": ["character"], "sorte": false}], \
+"quantity": false}) sans "event_type" : la créatrice le crée avant \
+d'écrire.
+
 Suis les réponses de la créatrice à la lettre. Réponds UNIQUEMENT avec ce \
 JSON :
 {"entities": [{"ref": "e1", "name": "...", "category": "person"}],
  "facts": [{"action": "create", "content": "...", "facet": "preference",
    "participants": ["e1"], "defaults": [{"scope_type": "rencontre",
    "scope_ref": "e1"}], "knowers": []}],
- "memberships": [], "controls": []}\
+ "memberships": [], "controls": [], "events": []}\
 """
 
 LORE_STATEMENT_TO_PROPOSAL_USER_TEMPLATE = """\
@@ -2024,6 +2037,12 @@ Entités connues que le texte nomme :
 Faits déjà connus (code — texte) :
 {facts}
 
+Types d'événements (code — nom, rôles) :
+{event_types}
+
+Sortes :
+{sortes}
+
 Texte de la créatrice :
 {statement}
 
@@ -2032,6 +2051,28 @@ Réponses de la créatrice aux questions :
 """
 
 
+# TICKET-0119 (BRIEF-0119-G, U1): the proposal call reads the world's event
+# types and sortes and may return events. The texts above hold each new
+# fragment; scripts/apply_ticket_0119_lore_prompt.py applies the same
+# (field, old, new) triples to the CURRENT version of the proposal head, so
+# an edit the creator made in the Prompts tab is kept (event_lore.py keeps
+# the triples and the texts above equal).
+LORE_PROPOSAL_VARIABLES: tuple[str, ...] = ("facets", "entities", "facts", "statement", "answers", "event_types",
+                                            "sortes")
+LORE_PROPOSAL_FRAGMENTS_0119: tuple[tuple[str, str, str], ...] = (
+    ("system_prompt",
+     "Suis les réponses de la créatrice à la lettre. Réponds UNIQUEMENT avec ce JSON :",
+     LORE_STATEMENT_TO_PROPOSAL_SYSTEM_PROMPT[
+         LORE_STATEMENT_TO_PROPOSAL_SYSTEM_PROMPT.index("ÉVÉNEMENTS."):
+         LORE_STATEMENT_TO_PROPOSAL_SYSTEM_PROMPT.index("Suis les réponses de la créatrice")]
+     + "Suis les réponses de la créatrice à la lettre. Réponds UNIQUEMENT avec ce JSON :"),
+    ("system_prompt", ' "memberships": [], "controls": []}', ' "memberships": [], "controls": [], "events": []}'),
+    ("user_template", "{facts}\n\nTexte de la créatrice :",
+     "{facts}\n\nTypes d'événements (code — nom, rôles) :\n{event_types}\n\nSortes :\n{sortes}\n\n"
+     "Texte de la créatrice :"),
+)
+
+
 # The lore writing heads, one tuple read by the seed and by
 # scripts/apply_ticket_0098_lore_write_prompts.py (single source, the
 # DAY_PROMPT_HEADS precedent).
@@ -2053,7 +2094,7 @@ LORE_WRITE_PROMPT_HEADS = (
         world_id=None,
         system_prompt=LORE_STATEMENT_TO_PROPOSAL_SYSTEM_PROMPT,
         user_template=LORE_STATEMENT_TO_PROPOSAL_USER_TEMPLATE,
-        variables=["facets", "entities", "facts", "statement", "answers"],
+        variables=list(LORE_PROPOSAL_VARIABLES),
         destination="local",
     ),
 )
diff --git a/src/world_engine/lore_write_apply.py b/src/world_engine/lore_write_apply.py
index 7e1cc65..2c39624 100644
--- a/src/world_engine/lore_write_apply.py
+++ b/src/world_engine/lore_write_apply.py
@@ -16,6 +16,16 @@ Entities are created through a callable the caller injects
 (`create_entity(name, type) -> Entity`, flushed): the commit-free creation
 core lives with the creator CRUD, which this module does not import.
 Every id in a proposal is re-read here against the proposal's world.
+
+TICKET-0119 (BRIEF-0119-G, U1): a proposal may hold EVENTS, each naming
+the entities of the statement by their ref -- its participants, its place,
+its scopes, the entities its changes name and an entity a change's value
+names. They are written after everything else, each through the journal's
+one writer (`event_payloads.spec_from_payload`, `writes.events.record_event`:
+its fact, its participants' knowledge, its changes), and every row it wrote
+is recorded against the entry. A type the world lacks is created from the
+panel before the commit, never here: an event still carrying `new_type` is
+refused. A refused event refuses the whole proposal (INV-57).
 """
 
 from __future__ import annotations
@@ -25,6 +35,7 @@ from typing import Any, Callable, Optional
 
 from sqlmodel import Session, select
 
+from .event_payloads import spec_from_payload
 from .facets import DESCRIPTIVE_FACETS, FACETS
 from .fact_refs import find_held
 from .models import Entity, Fact, FactDefault, FactionMembership, FactParticipant, Relation
@@ -33,6 +44,7 @@ from .writes.facts import FACT_CHANGE_KINDS
 from .writes.facts import attach_participants, create_fact_default
 from .writes.factions import write_membership
 from .writes.knowledge import KNOWLEDGE_LEVEL_LADDER, write_knowledge
+from .writes.events import record_event
 from .writes.lore_entries import record_entry_row, write_lore_entry
 from .writes.relations import write_relation
 
@@ -194,11 +206,36 @@ def validate(db: Session, world_id: str, proposal: dict) -> dict[str, dict]:
     for item in _list(proposal, "controls"):
         _entity_ref(refs, item.get("owner_ref"), "Possession")
         _entity_ref(refs, item.get("location_ref"), "Possession", "location")
-    if not (fact_refs or proposal.get("memberships") or proposal.get("controls")):
+    for item in _list(proposal, "events"):
+        _validate_event(refs, item)
+    if not (fact_refs or proposal.get("memberships") or proposal.get("controls") or proposal.get("events")):
         raise ProposalError("La proposition n'écrit rien.")
     return refs
 
 
+def _validate_event(refs: dict[str, dict], item: dict) -> None:
+    where = f"Événement {item.get('ref') or '?'}"
+    if item.get("new_type") is not None:
+        raise ProposalError(f"{where} : crée d'abord le type proposé.")
+    if not isinstance(item.get("type_id"), str) or not item["type_id"]:
+        raise ProposalError(f"{where} : choisis son type.")
+    _text(item, "title", where)
+    for p in item.get("participants") or []:
+        if not isinstance(p, dict):
+            raise ProposalError(f"{where} : un participant doit être un objet.")
+        if p.get("entity_ref") is not None:
+            _entity_ref(refs, p["entity_ref"], where)
+    if item.get("location_ref") is not None:
+        _entity_ref(refs, item["location_ref"], where, "location")
+    for change in item.get("state_changes") or []:
+        if not isinstance(change, dict):
+            raise ProposalError(f"{where} : un changement doit être un objet.")
+        _entity_ref(refs, change.get("entity_ref"), where)
+    for scope in item.get("scopes") or []:
+        if isinstance(scope, dict) and scope.get("scope_ref") is not None:
+            _entity_ref(refs, scope["scope_ref"], where)
+
+
 class _Writer:
     """Applies one validated proposal; every written row is recorded."""
 
@@ -292,6 +329,16 @@ class _Writer:
             self.add_defaults(fact, self.scopes(item))
         self.knowers(fact, item)
 
+    def event(self, item: dict) -> None:
+        """U1: one event through the journal's writer, every row recorded."""
+        spec = spec_from_payload(self.db, self.world_id, _event_payload(item, self.ids))
+        written = record_event(self.db, world_id=self.world_id, spec=spec, created_by=CREATED_BY)
+        seen: set[tuple[str, str]] = set()
+        for table, row_id, action in written.rows:
+            if (table, row_id) not in seen:
+                seen.add((table, row_id))
+                self.record(table, row_id, action)
+
     def membership(self, item: dict) -> None:
         entity_id, faction_id = self.ids[item["entity_ref"]], self.ids[item["faction_ref"]]
         held = self.db.exec(select(FactionMembership).where(
@@ -320,6 +367,31 @@ class _Writer:
         self.record("relation", row.id)
 
 
+def _event_payload(item: dict, ids: dict[str, str]) -> dict:
+    """An event of the proposal as a typed `event_creation` payload, its refs
+    made ids."""
+    def value(raw: Any) -> Any:
+        return ids.get(raw, raw) if isinstance(raw, str) else raw
+
+    payload = {
+        "title": item["title"], "description": item.get("description"), "type_id": item["type_id"],
+        "quantity": item.get("quantity"),
+        "location_id": ids[item["location_ref"]] if item.get("location_ref") else None,
+        "participants": [{"role_id": p.get("role_id"), "role": p.get("role"),
+                          "entity_id": ids[p["entity_ref"]] if p.get("entity_ref") else None,
+                          "sorte_id": p.get("sorte_id"), "secret": p.get("secret")}
+                         for p in item.get("participants") or []],
+        "state_changes": [{"entity_id": ids[c["entity_ref"]], "attribute": c.get("attribute"),
+                           "mode": c.get("mode") or "set", "value": value(c.get("value"))}
+                          for c in item.get("state_changes") or []],
+    }
+    if isinstance(item.get("scopes"), list):
+        payload["scopes"] = [{"scope_type": s.get("scope_type"), "level": s.get("level") or "knows",
+                              "scope_id": ids[s["scope_ref"]] if s.get("scope_ref") else None}
+                             for s in item["scopes"] if isinstance(s, dict)]
+    return payload
+
+
 def apply_proposal(
     db: Session, world_id: str, proposal: dict,
     create_entity: Callable[[str, str], Entity],
@@ -340,6 +412,8 @@ def apply_proposal(
             writer.membership(item)
         for item in _list(proposal, "controls"):
             writer.control(item)
+        for item in _list(proposal, "events"):
+            writer.event(item)
     except ProposalError:
         raise
     except ValueError as exc:
diff --git a/src/world_engine/lore_write_draft.py b/src/world_engine/lore_write_draft.py
index 4c542a3..812e5a7 100644
--- a/src/world_engine/lore_write_draft.py
+++ b/src/world_engine/lore_write_draft.py
@@ -16,6 +16,17 @@ writes what the creator confirmed.
 
 Ollama down surfaces as `ollama_client.OllamaError` to the route, which
 answers `WRITE_UNAVAILABLE_MESSAGE` (K1: no fallback extractor).
+
+TICKET-0119 (BRIEF-0119-G, U1, G3): the proposal call also sees the world's
+event types (the coded `t` list, `event_analysis.analysis_vocabulary`) and
+its sortes, and may return EVENTS: a type by code, participants by role --
+an entity of the statement by its ref, or a sorte by name -- a quantity, a
+place by ref; or a type the world lacks (`new_type`), which the panel offers
+to create before the commit. Code reads each fail-closed (`_event`): an
+unknown code drops the event with a note, a role the type lacks or a sorte
+the world lacks drops that participant with a note. A known type's effects
+pre-fill the event's changes on the entities the statement names that the
+world already has (M-c).
 """
 
 from __future__ import annotations
@@ -26,15 +37,19 @@ from typing import Any, Optional
 from sqlmodel import Session, select
 
 from . import model_exchange, prompt_call
+from .event_analysis import AnalysisVocabulary, analysis_vocabulary
+from .event_changes import type_changes
+from .event_proposals import type_definition, type_spec
 from .facet_reads import creator_only_fact_ids
 from .facets import FACETS
 from .fact_refs import CodedRefs, code_facts
-from .lore_resolve import near_candidates, resolve_named
+from .lore_resolve import near_candidates, normalize_surface, resolve_named
 from .models import Entity, Fact, FactParticipant
 from .name_index import CREATOR
 from .ollama_client import chat
 from .prose_render import TOKEN_RE
 from .prose_tokens import tokenize
+from .writes.event_types import clean_event_type
 from .writes.knowledge import KNOWLEDGE_LEVEL_LADDER
 
 QUESTIONS_USAGE = "lore_statement_questions"
@@ -121,14 +136,18 @@ def _call(db: Session, usage: str, values: dict[str, str], exchanges: Exchanges)
     return prompt_call.call_json(db, usage, values, exchanges, chat)
 
 
-def _values(context: DraftContext, statement: str, answers: str = "") -> dict[str, str]:
-    return {
+def _values(context: DraftContext, statement: str, answers: str = "",
+            vocab: Optional[AnalysisVocabulary] = None) -> dict[str, str]:
+    values = {
         "statement": statement.strip(),
         "answers": answers.strip() or "(aucune réponse)",
         "entities": "\n".join(context.entity_lines) or "(aucune entité connue nommée)",
         "facts": "\n".join(context.coded.lines) or "(aucun fait connu)",
         "facets": _facet_lines(),
     }
+    if vocab is not None:
+        values.update(vocab.prompt_values())
+    return values
 
 
 def draft_questions(
@@ -238,6 +257,86 @@ def _pairs(raw: Any, keys: tuple[str, str], known: set[str]) -> list[dict]:
     return out
 
 
+def _event_type(db: Session, world_id: str, raw: dict, vocab: AnalysisVocabulary, notes: list[str]):
+    """(type id or None, type name, {role name key: (role id or None, name)},
+    counts quantity, new type definition or None), or None to drop."""
+    code = raw.get("event_type")
+    if code not in (None, "") and not isinstance(code, dict):
+        type_id = vocab.codes.resolve(code)
+        if type_id is None:
+            notes.append(f"Un événement de type inconnu ({code!r}) a été ignoré.")
+            return None
+        view = vocab.types[type_id]
+        roles = {normalize_surface(r.name): (r.id, r.name) for r in view.active_roles()}
+        return type_id, view.name, roles, view.counts_quantity, None
+    if not isinstance(raw.get("new_type"), dict):
+        notes.append("Un événement sans type a été ignoré.")
+        return None
+    try:
+        clean = clean_event_type(db, world_id, type_spec(raw["new_type"]))
+    except ValueError as exc:
+        notes.append(f"Un type d'événement proposé a été refusé ({exc}).")
+        return None
+    roles = {normalize_surface(r.name): (None, r.name) for r in clean.roles}
+    return None, clean.name, roles, clean.counts_quantity, type_definition(clean)
+
+
+def _event_participant(raw: Any, roles: dict, by_ref: dict, vocab: AnalysisVocabulary,
+                       notes: list[str]) -> Optional[dict]:
+    if not isinstance(raw, dict):
+        return None
+    role = roles.get(normalize_surface(str(raw.get("role") or "")))
+    if role is None:
+        notes.append(f"Un participant d'un rôle inconnu ({raw.get('role')!r}) a été ignoré.")
+        return None
+    out = {"role_id": role[0], "role": role[1], "entity_ref": None, "sorte_id": None, "secret": None}
+    if str(raw.get("sorte") or "").strip():
+        name = normalize_surface(str(raw["sorte"]))
+        out["sorte_id"] = next((sid for sid, s in vocab.sortes.items() if normalize_surface(s) == name), None)
+        if out["sorte_id"] is None:
+            notes.append(f"La sorte « {raw['sorte']} » n'existe pas : crée-la dans Vocabulaire du monde.")
+            return None
+        return out
+    if raw.get("ref") not in by_ref:
+        return None
+    out["entity_ref"] = raw["ref"]
+    return out
+
+
+def _event(db: Session, world_id: str, raw: Any, vocab: AnalysisVocabulary, by_ref: dict,
+           notes: list[str]) -> Optional[dict]:
+    """One event of the model, read fail-closed (see the module docstring)."""
+    if not isinstance(raw, dict):
+        return None
+    found = _event_type(db, world_id, raw, vocab, notes)
+    if found is None:
+        return None
+    type_id, type_name, roles, counts, definition = found
+    participants = [p for p in (_event_participant(r, roles, by_ref, vocab, notes)
+                                for r in _as_list(raw.get("participants"))) if p is not None]
+    quantity = raw.get("quantity")
+    item: dict[str, Any] = {
+        "type_id": type_id, "type_name": type_name,
+        "title": str(raw.get("title") or "").strip() or type_name,
+        "description": str(raw.get("description") or "").strip() or None,
+        "quantity": quantity if counts and isinstance(quantity, int) and not isinstance(quantity, bool)
+        and quantity >= 1 else None,
+        "location_ref": raw.get("place_ref") if raw.get("place_ref") in by_ref else None,
+        "participants": participants, "state_changes": [],
+    }
+    if definition is not None:
+        item["new_type"] = definition
+        return item
+    known = {by_ref[p["entity_ref"]]["entity_id"]: p["entity_ref"] for p in participants
+             if p["entity_ref"] and by_ref[p["entity_ref"]].get("entity_id")}
+    changes = type_changes(db, world_id, vocab.types[type_id],
+                           [(p["role_id"], by_ref[p["entity_ref"]].get("entity_id")) for p in participants
+                            if p["entity_ref"]])
+    item["state_changes"] = [{"entity_ref": known[c["entity_id"]], "attribute": c["attribute"],
+                              "mode": c["mode"], "value": known.get(c["value"], c["value"])} for c in changes]
+    return item
+
+
 def _preset_kind(db: Session, fact_id: str) -> str:
     """The rewrite kind preselected for a fact's facet (TICKET-0105, H1)."""
     fact = db.get(Fact, fact_id)
@@ -254,7 +353,8 @@ def draft_proposal(
     an id or dropped with a note. `OllamaError` and `LlmParseError`
     propagate. `exchanges`: see `_call` (TICKET-0103, C-03)."""
     context = draft_context(db, world_id, statement)
-    parsed = _call(db, PROPOSAL_USAGE, _values(context, statement, answers), exchanges)
+    vocab = analysis_vocabulary(db, world_id)
+    parsed = _call(db, PROPOSAL_USAGE, _values(context, statement, answers, vocab), exchanges)
     notes: list[str] = []
     entities = [e for e in (_entity(db, world_id, raw, notes)
                             for raw in _as_list(parsed.get("entities"))) if e is not None]
@@ -269,11 +369,17 @@ def draft_proposal(
         fact["ref"] = f"f{index}"
         if fact["action"] == "rewrite":
             fact["kind"] = _preset_kind(db, fact["fact_id"])
+    by_ref = {e["ref"]: e for e in entities}
+    events = [e for e in (_event(db, world_id, raw, vocab, by_ref, notes)
+                          for raw in _as_list(parsed.get("events"))) if e is not None]
+    for index, event in enumerate(events, start=1):
+        event["ref"] = f"v{index}"
     return {
         "statement": statement.strip(), "answers": answers.strip() or None,
         "entities": entities, "facts": facts,
         "memberships": _pairs(parsed.get("memberships"), ("entity_ref", "faction_ref"), seen),
         "controls": _pairs(parsed.get("controls"), ("owner_ref", "location_ref"), seen),
+        "events": events,
         "notes": notes,
         "facets": [{"name": name, "label": spec.label} for name, spec in FACETS.items()
                    if spec.granularity != "typed"],
diff --git a/src/world_engine/lore_write_read.py b/src/world_engine/lore_write_read.py
index 100db8f..d71fe95 100644
--- a/src/world_engine/lore_write_read.py
+++ b/src/world_engine/lore_write_read.py
@@ -2,7 +2,8 @@
 
 The panel's history view: the world's `lore_entry` rows, newest first, each
 with what it wrote, labelled for the creator (an entity's current name, a
-fact's rendered text, who knows which fact, a membership, a possession).
+fact's rendered text, who knows which fact, a membership, a possession;
+since TICKET-0119 an event, its participants and the states it changed).
 A row whose target was deleted since is labelled as such, never dropped.
 Reads only.
 """
@@ -13,9 +14,10 @@ from typing import Optional
 
 from sqlmodel import Session, select
 
+from .attributes import attribute_view, raw_of, value_label
 from .models import (
-    Entity, Fact, FactDefault, FactionMembership, FactParticipant, Knowledge, LoreEntry,
-    LoreEntryRow, Relation,
+    AttributeChange, AttributeValue, Entity, Event, EventParticipant, Fact, FactDefault, FactionMembership,
+    FactParticipant, Knowledge, LoreEntry, LoreEntryRow, Relation,
 )
 from .prose_render import fact_text
 
@@ -33,10 +35,31 @@ def _fact_label(db: Session, fact_id: str) -> str:
     return fact_text(db, fact) if fact is not None else _DELETED
 
 
+def _event_label(db: Session, table: str, target) -> str:
+    """TICKET-0119 (U1): an event, a participant, a state it set."""
+    if table == "event":
+        return target.title
+    if table == "event_participant":
+        event = db.get(Event, target.event_id)
+        who = _name(db, target.entity_id) if target.entity_id else "une sorte"
+        return f"{who} — {event.title if event else _DELETED}"
+    value = target if table == "attribute_value" else db.get(AttributeValue, target.value_id)
+    view = attribute_view(db, value.world_id, value.definition_id) if value is not None else None
+    if view is None:
+        return _DELETED
+    if table == "attribute_value":
+        raw = raw_of(value)
+    else:
+        raw = next((v for v in (target.after_choice_id, target.after_integer, target.after_entity_id)
+                    if v is not None), None)
+    return f"{_name(db, value.entity_id)} : {view.name} -> {value_label(db, view, raw)}"
+
+
 def _label(db: Session, row: LoreEntryRow) -> str:
     model = {"entity": Entity, "fact": Fact, "fact_participant": FactParticipant,
              "fact_default": FactDefault, "knowledge": Knowledge, "relation": Relation,
-             "faction_membership": FactionMembership}[row.row_table]
+             "faction_membership": FactionMembership, "event": Event, "event_participant": EventParticipant,
+             "attribute_value": AttributeValue, "attribute_change": AttributeChange}[row.row_table]
     target = db.get(model, row.row_id)
     if target is None:
         return _DELETED
@@ -54,6 +77,8 @@ def _label(db: Session, row: LoreEntryRow) -> str:
         flags = "".join((" (secret)" if target.is_secret else "",
                          " (croyance fausse)" if target.is_incorrect else ""))
         return f"{_name(db, target.entity_id)} [{target.level}]{flags} — {_fact_label(db, target.fact_id)}"
+    if row.row_table in ("event", "event_participant", "attribute_value", "attribute_change"):
+        return _event_label(db, row.row_table, target)
     if row.row_table == "relation":
         return f"{_name(db, target.entity_a_id)} possède {_name(db, target.entity_b_id)}"
     return f"{_name(db, target.entity_id)} membre de {_name(db, target.faction_id)}"
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 825915f..85c016b 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19631,6 +19631,41 @@ days.
 **Replay.** `resolve_day` already refuses while the standing agenda holds a
 proposed step change (BB1), so a day is never proposed twice.
 
+## LORE DECLARES EVENTS -- IN THE WRITING PANEL'S PROPOSAL, AND BY A BUTTON STRAIGHT TO THE JOURNAL (TICKET-0119) -- U1, G3 (BRIEF-0119-g, no schema change)
+
+**U1 in the panel.** The lore writing call reads the world's event types
+(the coded `t` list) and its sortes, and may return events: a type by code,
+participants by role -- an entity of the statement by its ref, a sorte by
+name --, a quantity, a place by ref. `lore_write_draft._event` reads each
+fail-closed: an unknown code drops the event, an unknown role or a sorte the
+world lacks drops that participant, each with a note. A known type's
+effects pre-fill the event's changes on the entities the world already has
+(M-c). The panel edits each event in the shared `EventEditor`, its entities
+being the statement's refs until the commit (so its « Pré-remplir » is
+hidden: the draft arrives pre-filled).
+
+**A proposed type.** When no type fits, the model proposes one; the panel
+shows it in `EventTypeForm` and creates it with « Créer ce type » (the
+vocabulary's routes) before the commit -- the interpreter's rule (0114, G).
+An event still carrying `new_type` refuses the proposal: the commit never
+writes vocabulary.
+
+**The commit.** Events are written after the entities, facts, memberships
+and controls, each through the journal's one writer (`spec_from_payload`,
+`record_event`), its refs made ids; every row it wrote is recorded against
+the entry (INV-57: `lore_entry_row` names `event`, `event_participant`,
+`attribute_value`, `attribute_change` since v2.26). One refused event
+refuses the whole proposal. The history labels an event by its title, a
+state by « entité : état -> valeur ».
+
+**G3.** « Déclarer un événement » opens the editor on a blank event with
+the world's entities and writes it straight to the journal (`POST
+/api/events`): no statement, no lore entry -- the journal is its record.
+
+**Prompt.** Three fragments of `LORE_PROPOSAL_FRAGMENTS_0119`, delivered by
+`apply_ticket_0119_lore_prompt.py` fragment by fragment: the creator's
+edits are kept.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/event_editor.py b/tooling/verify/checks/event_editor.py
index 09cf8e2..9871f7a 100644
--- a/tooling/verify/checks/event_editor.py
+++ b/tooling/verify/checks/event_editor.py
@@ -178,7 +178,7 @@ def check_ey3() -> None:
         "QueueCard.svelte": ("<EventEditor", "payloadFromDraft(eventDraft"),
         "eventDraft.svelte.js": ("export function draftFromPayload", "export function payloadFromDraft",
                                  "export async function prefilledChanges", "'/api/events/changes'",
-                                 "state_changes: isNew ? changesBody(eventDraftState) : []"),
+                                 "state_changes: isNew ? changesBody(draft) : []"),
     }
     for name, needles in wanted.items():
         path = FRONT / name
diff --git a/tooling/verify/checks/event_lore.py b/tooling/verify/checks/event_lore.py
new file mode 100644
index 0000000..1455f97
--- /dev/null
+++ b/tooling/verify/checks/event_lore.py
@@ -0,0 +1,390 @@
+"""G1 check for TICKET-0119 -- Lore declares events: in the writing panel's proposal, and by a button straight to the journal.
+
+BRIEF-0119-G's rules (U1, G3 and M-c of the conditions series).
+
+EL1 -- the prompt (static and fixture). The seed's Lore proposal texts hold
+   each new fragment of `LORE_PROPOSAL_FRAGMENTS_0119` exactly once; the
+   proposal head's variables (`LORE_PROPOSAL_VARIABLES`, the head of
+   `LORE_WRITE_PROMPT_HEADS`) are exactly its user template's placeholders,
+   `event_types` and `sortes` among them. `apply_ticket_0119_lore_prompt.py`,
+   on a head holding the former texts and variables, writes one version
+   equal to the seed's with its variables; a second run is unchanged; on a
+   head the creator edited where a fragment stood, her edit is kept and the
+   fragment reported.
+EL2 -- the draft (fixture, the model call replaced). `draft_proposal`
+   reads an event naming « Ouvrir » by code: its type, its participants by
+   role -- a matched entity by its ref, a sorte of the world by id --, its
+   place by ref, and its changes pre-filled on the matched door, by ref; an
+   event proposing a type keeps `new_type`, its roles by name; an unknown
+   code, an unknown role and a sorte the world lacks each leave a note, the
+   event or the participant dropped.
+EL3 -- the commit (fixture). A proposal creating « Cave » and holding an
+   event whose participant, place and change name it by ref writes the
+   event with « Cave »'s new id in its role and as its place, sets its
+   « Ouvert » as a `changement` naming the event, and records the `event`,
+   its `fact`, its `event_participant`, the `attribute_value` and the
+   `attribute_change` against the entry; `list_entries` labels the event by
+   its title. An event still carrying `new_type`, and an event whose change
+   the writer refuses, each refuse the whole proposal: nothing is written.
+EL4 -- the panel (static). `WritePanel.svelte` renders `<EventEditor` for
+   the draft's events with `canPrefill={false}`, a proposed type's
+   `<EventTypeForm` and « Créer ce type », and the « Déclarer un événement »
+   button; `writePanel.svelte.js` exports `eventEntities`,
+   `createProposedType`, `openDeclare` and `saveDeclared`, sends the events
+   in the proposal (`events:`) and saves a declared event with
+   `eventBodyFrom(`.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import json
+import os
+import pathlib
+import re
+import subprocess
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SCRIPT = ROOT / "scripts" / "apply_ticket_0119_lore_prompt.py"
+LORE = ROOT / "frontend" / "src" / "lore"
+HEAD = "pt-lore-statement-to-proposal"
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
+    sys.path.insert(0, str(ROOT / "scripts"))
+
+
+# --- EL1 -----------------------------------------------------------------------
+
+def _texts() -> dict[str, str]:
+    import seed_pilot
+
+    return {"system_prompt": seed_pilot.LORE_STATEMENT_TO_PROPOSAL_SYSTEM_PROMPT,
+            "user_template": seed_pilot.LORE_STATEMENT_TO_PROPOSAL_USER_TEMPLATE}
+
+
+def _former_texts() -> dict[str, str]:
+    import seed_pilot
+
+    texts = _texts()
+    for field, old, new in seed_pilot.LORE_PROPOSAL_FRAGMENTS_0119:
+        texts[field] = texts[field].replace(new, old)
+    return texts
+
+
+def _prompt_db(texts: dict[str, str]) -> str:
+    from sqlalchemy import create_engine
+    from sqlmodel import Session, SQLModel
+
+    from world_engine.models import PromptTemplate
+    from world_engine.writes.prompts import write_prompt_variables, write_prompt_version
+
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "prompt.db")
+    eng = create_engine(f"sqlite:///{db_path}")
+    SQLModel.metadata.create_all(eng)
+    with Session(eng) as db:
+        db.add(PromptTemplate(id=HEAD, name="lore", usage="lore_statement_to_proposal", world_id=None,
+                              destination="local"))
+        db.flush()
+        write_prompt_variables(db, template_id=HEAD, variables=["facets", "entities", "facts", "statement",
+                                                                 "answers"])
+        write_prompt_version(db, template_id=HEAD, note="former", **texts)
+        db.commit()
+    eng.dispose()
+    return db_path
+
+
+def _run(db_path: str):
+    from sqlalchemy import create_engine
+    from sqlmodel import Session, select
+
+    from world_engine.models import PromptTemplate, PromptVariable
+    from world_engine.prompt_store import current_prompt
+
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    result = subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True,
+                            cwd=str(ROOT), timeout=60)
+    eng = create_engine(f"sqlite:///{db_path}")
+    with Session(eng) as db:
+        version = current_prompt(db, db.get(PromptTemplate, HEAD))
+        state = (version.version_number, version.system_prompt, version.user_template,
+                 set(db.exec(select(PromptVariable.name)).all()))
+    eng.dispose()
+    return result, state
+
+
+def check_el1() -> None:
+    import seed_pilot
+
+    texts = _texts()
+    fragments = seed_pilot.LORE_PROPOSAL_FRAGMENTS_0119
+    if not fragments:
+        fail("EL1: LORE_PROPOSAL_FRAGMENTS_0119 is empty")
+    for field, _old, new in fragments:
+        if texts[field].count(new) != 1:
+            fail(f"EL1: the fragment {new[:40]!r} stands {texts[field].count(new)} time(s) in the seed's {field}")
+    used = set(re.findall(r"\{([a-z_]+)\}", texts["user_template"]))
+    head = next((h for h in seed_pilot.LORE_WRITE_PROMPT_HEADS if h["id"] == HEAD), {})
+    if used != set(seed_pilot.LORE_PROPOSAL_VARIABLES) or set(head.get("variables", [])) != used \
+            or not {"event_types", "sortes"} <= used:
+        fail(f"EL1: variables {seed_pilot.LORE_PROPOSAL_VARIABLES}, head {head.get('variables')}, "
+             f"template {sorted(used)}")
+    seed = (texts["system_prompt"], texts["user_template"])
+    result, state = _run(_prompt_db(_former_texts()))
+    if result.returncode != 0 or state[0] != 2 or state[1:3] != seed \
+            or state[3] != set(seed_pilot.LORE_PROPOSAL_VARIABLES):
+        fail(f"EL1: the delivery gave v{state[0]}, seed text {state[1:3] == seed}, variables {state[3]}: "
+             f"{result.stdout.strip()[-200:]} {result.stderr.strip()[-300:]}")
+    db_path = _prompt_db(_former_texts())
+    _run(db_path)
+    again, state = _run(db_path)
+    if again.returncode != 0 or "unchanged" not in again.stdout or state[0] != 2:
+        fail(f"EL1: a second run: {again.stdout.strip()[-200:]}")
+    edited = _former_texts()
+    field, lost, _new = fragments[-1]
+    edited[field] = edited[field].replace(lost, "(retouché à la main)")
+    result, state = _run(_prompt_db(edited))
+    if result.returncode != 0 or "fragment not found" not in result.stdout or "(retouché à la main)" not in state[2]:
+        fail(f"EL1: an edited head gave v{state[0]}: {result.stdout.strip()[-300:]}")
+
+
+# --- fixture -------------------------------------------------------------------
+
+def _world(engine) -> dict:
+    from sqlmodel import Session
+
+    import seed_pilot
+    from world_engine.attributes import attribute_view
+    from world_engine.event_vocab import type_view
+    from world_engine.models import Character, Entity, Location, PromptTemplate, World
+    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec, write_attribute_definition
+    from world_engine.writes.event_types import EffectSpec, EventTypeSpec, RoleSpec, write_event_type, write_sorte
+
+    with Session(engine) as db:
+        for head in seed_pilot.LORE_WRITE_PROMPT_HEADS:
+            if db.get(PromptTemplate, head["id"]) is None:
+                seed_pilot.upsert_prompt_template(db, **dict(head))
+        world = World(name="Lore EL", is_active=True)
+        db.add(world)
+        db.flush()
+        ids = {"world": world.id}
+        for key, kind, name in (("millys", "character", "Millys"), ("porte", "location", "Porte Noire")):
+            row = Entity(world_id=world.id, type=kind, name=name)
+            db.add(row)
+            db.flush()
+            ids[key] = row.id
+            db.add(Character(id=row.id, world_id=world.id, character_type="npc") if kind == "character"
+                   else Location(id=row.id))
+        ouvert = write_attribute_definition(db, world_id=world.id, spec=DefinitionSpec(
+            name="Ouvert", kind="choice", holder_types=("location",),
+            choices=(ChoiceSpec("non"), ChoiceSpec("oui")), default="non"))
+        db.flush()
+        ids["ouvert"] = ouvert.id
+        ids["oui"] = {label: key for key, label in attribute_view(db, world.id, ouvert.id).choices}["oui"]
+        ouvrir = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
+            name="Ouvrir", roles=(RoleSpec("Ouvreur", ("character",)),
+                                  RoleSpec("Cible", ("location",), accepts_sorte=True)),
+            effects=(EffectSpec("Cible", ouvert.id, ids["oui"]),)))
+        ids["ouvrir"] = ouvrir.id
+        ids["ombre"] = write_sorte(db, world_id=world.id, name="Ombre").id
+        for role in type_view(db, ouvrir.id).roles:
+            ids[role.name] = role.id
+        db.commit()
+    return ids
+
+
+class _Stub:
+    def __init__(self, replies: list) -> None:
+        self.replies = list(replies)
+
+    def __call__(self, messages, **_kwargs):
+        return json.dumps(self.replies.pop(0))
+
+
+def check_el2(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine import lore_write_draft as lwd
+    from world_engine.event_analysis import analysis_vocabulary
+
+    with Session(engine) as db:
+        code = analysis_vocabulary(db, ids["world"]).codes.code_of(ids["ouvrir"])
+        reply = {"entities": [{"ref": "e1", "name": "Millys", "category": "person"},
+                              {"ref": "e2", "name": "Porte Noire", "category": "place"}],
+                 "facts": [], "memberships": [], "controls": [],
+                 "events": [
+                     {"event_type": code, "title": "Millys ouvre la Porte Noire", "place_ref": "e2",
+                      "participants": [{"role": "Ouvreur", "ref": "e1"}, {"role": "Cible", "ref": "e2"},
+                                       {"role": "Cible", "sorte": "Ombre"}, {"role": "Témoin", "ref": "e1"},
+                                       {"role": "Cible", "sorte": "Brume"}]},
+                     {"new_type": {"name": "Sceller", "roles": [{"name": "Scelleur", "for": ["character"]}]},
+                      "title": "Le sceau", "participants": [{"role": "Scelleur", "ref": "e1"}]},
+                     {"event_type": "t99", "title": "Rien"}]}
+        original = lwd.chat
+        lwd.chat = _Stub([reply])
+        try:
+            draft = lwd.draft_proposal(db, ids["world"], "Millys ouvre la Porte Noire.")
+        finally:
+            lwd.chat = original
+    events = draft.get("events", [])
+    first = events[0] if events else {}
+    got = (first.get("type_id"), first.get("location_ref"),
+           [(p["role_id"], p["entity_ref"], p["sorte_id"]) for p in first.get("participants", [])],
+           first.get("state_changes"))
+    want = (ids["ouvrir"], "e2", [(ids["Ouvreur"], "e1", None), (ids["Cible"], "e2", None),
+                                  (ids["Cible"], None, ids["ombre"])],
+            [{"entity_ref": "e2", "attribute": ids["ouvert"], "mode": "set", "value": ids["oui"]}])
+    if len(events) != 2 or got != want:
+        fail(f"EL2: the draft's events are {len(events)}, the first {got}")
+    second = events[1] if len(events) > 1 else {}
+    if not second.get("new_type") or [p["role"] for p in second.get("participants", [])] != ["Scelleur"]:
+        fail(f"EL2: a proposed type's event is {second}")
+    notes = " | ".join(draft.get("notes", []))
+    for needle in ("t99", "Témoin", "Brume"):
+        if needle not in notes:
+            fail(f"EL2: no note names {needle}: {notes}")
+
+
+def _counts(db) -> tuple[int, ...]:
+    from sqlmodel import func, select
+
+    from world_engine.models import AttributeChange, Entity, Event, LoreEntry
+
+    return tuple(db.exec(select(func.count()).select_from(m)).one() for m in (Entity, Event, AttributeChange,
+                                                                              LoreEntry))
+
+
+def _creator(db):
+    from world_engine.models import Entity, Location
+
+    def create(name: str, entity_type: str):
+        entity = Entity(world_id=_creator.world, type=entity_type, name=name)
+        db.add(entity)
+        db.flush()
+        if entity_type == "location":
+            db.add(Location(id=entity.id))
+            db.flush()
+        return entity
+    return create
+
+
+def _proposal(ids: dict, **event) -> dict:
+    base = {"ref": "v1", "type_id": ids["ouvrir"], "title": "Millys ouvre la Cave", "location_ref": "e2",
+            "participants": [{"role_id": ids["Ouvreur"], "entity_ref": "e1"},
+                             {"role_id": ids["Cible"], "entity_ref": "e2"}],
+            "state_changes": [{"entity_ref": "e2", "attribute": ids["ouvert"], "value": ids["oui"]}]}
+    base.update(event)
+    return {"statement": "Millys ouvre la Cave.", "entities": [
+        {"ref": "e1", "action": "existing", "entity_id": ids["millys"]},
+        {"ref": "e2", "action": "create", "name": "Cave", "type": "location"}],
+        "facts": [], "memberships": [], "controls": [], "events": [base]}
+
+
+def check_el3(engine, ids: dict) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine import lore_write_apply as lwa
+    from world_engine.attributes import attribute_view, current_value
+    from world_engine.lore_write_read import list_entries
+    from world_engine.models import AttributeChange, Entity, Event, EventParticipant, LoreEntryRow
+
+    _creator.world = ids["world"]
+    with Session(engine) as db:
+        result = lwa.apply_proposal(db, ids["world"], _proposal(ids), _creator(db))
+        db.commit()
+        cave = db.exec(select(Entity).where(Entity.name == "Cave")).first()
+        event = db.exec(select(Event).where(Event.title == "Millys ouvre la Cave")).first()
+        roles = {(p.role_id, p.entity_id) for p in db.exec(select(EventParticipant).where(
+            EventParticipant.event_id == (event.id if event else "")))}
+        state = current_value(db, attribute_view(db, ids["world"], ids["ouvert"]), cave) if cave else None
+        change = db.exec(select(AttributeChange).where(AttributeChange.event_id == (event.id if event else ""))).first()
+        if event is None or cave is None or event.location_id != cave.id \
+                or roles != {(ids["Ouvreur"], ids["millys"]), (ids["Cible"], cave.id)} \
+                or state is None or state.raw != ids["oui"] or change is None or change.kind != "changement":
+            fail(f"EL3: the commit wrote event {event}, roles {roles}, state {state}, change {change}")
+        tables = set(db.exec(select(LoreEntryRow.row_table).where(LoreEntryRow.entry_id == result.entry_id)).all())
+        if not {"event", "fact", "event_participant", "attribute_value", "attribute_change"} <= tables:
+            fail(f"EL3: the entry records {sorted(tables)}")
+        labels = [r["label"] for e in list_entries(db, ids["world"]) for r in e["rows"] if r["row_table"] == "event"]
+        if labels != ["Millys ouvre la Cave"]:
+            fail(f"EL3: the history labels the event {labels}")
+        for label, bad in (("a proposed type", _proposal(ids, title="Autre", new_type={"name": "Sceller"})),
+                           ("a refused change", _proposal(ids, title="Autre", state_changes=[
+                               {"entity_ref": "e1", "attribute": ids["ouvert"], "value": ids["oui"]}]))):
+            before = _counts(db)
+            try:
+                lwa.apply_proposal(db, ids["world"], bad, _creator(db))
+                fail(f"EL3: {label} was not refused")
+            except lwa.ProposalError:
+                pass
+            db.rollback()
+            if _counts(db) != before:
+                fail(f"EL3: {label} was refused but wrote rows")
+
+
+def check_el4() -> None:
+    wanted = {
+        "WritePanel.svelte": ("<EventEditor draft={ev}", "canPrefill={false}", "<EventTypeForm",
+                              "Créer ce type", "Déclarer un événement"),
+        "writePanel.svelte.js": ("export function eventEntities", "export function createProposedType",
+                                 "export function openDeclare", "export async function saveDeclared",
+                                 "events: (draft.events || [])", "eventBodyFrom(draft, true)"),
+    }
+    for name, needles in wanted.items():
+        path = LORE / name
+        text = path.read_text(encoding="utf-8") if path.exists() else ""
+        if not text:
+            fail(f"EL4: {name} is missing")
+        for needle in needles:
+            if needle not in text:
+                fail(f"EL4: {name} lacks {needle}")
+
+
+def main() -> int:
+    _fresh_db()
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    try:
+        check_el1()
+    except Exception as exc:  # a crash is a failure, never a pass
+        fail(f"EL1: crashed -- {type(exc).__name__}: {exc}")
+    try:
+        ids = _world(engine)
+    except Exception as exc:  # a crash is a failure, never a pass
+        fail(f"EL2-EL3: the fixture crashed -- {type(exc).__name__}: {exc}")
+        ids = None
+    for name, rule in (("EL2", check_el2), ("EL3", check_el3)):
+        if ids is None:
+            break
+        try:
+            rule(engine, ids)
+        except Exception as exc:  # a crash is a failure, never a pass
+            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
+    check_el4()
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: event_lore -- Lore's proposal reads the world's event types and declares events by type, role and "
+          "ref, its changes pre-filled; a proposed type is created before the commit; the commit writes each event "
+          "through the journal's writer, every row recorded, all or nothing; a button declares one straight to "
+          "the journal")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/lore_write.py b/tooling/verify/checks/lore_write.py
index 7e6d7ff..46f879c 100644
--- a/tooling/verify/checks/lore_write.py
+++ b/tooling/verify/checks/lore_write.py
@@ -77,7 +77,9 @@ F1 -- panel (BRIEF-0098-F), static:
       it only under `loreTab === 'write'`;
    b. `frontend/src/lore/writePanel.svelte.js` calls exactly the paths
       `/api/lore/write/questions`, `/api/lore/write/draft`,
-      `/api/lore/write/commit`, `/api/lore/write/entries` and `/api/entities`;
+      `/api/lore/write/commit`, `/api/lore/write/entries`, `/api/entities`,
+      and since TICKET-0119 `/api/event-types` (a proposed type, created
+      before the commit) and `/api/events` (« Déclarer un événement »);
    c. `WritePanel.svelte` lists the facets it offers from `draft.facets`
       (served from `FACETS`), never from a literal list, and offers no free
       text field for an entity id.
@@ -648,8 +650,10 @@ def check_f1() -> None:
         fail("F1a: Lore.svelte does not render WritePanel under the 'write' tab")
     state = (lore / "writePanel.svelte.js").read_text(encoding="utf-8")
     paths = set(re.findall(r"'(/api/[a-z/_-]+)'", state))
+    # TICKET-0119 (BRIEF-0119-G): a proposed type is created before the
+    # commit, and « Déclarer un événement » writes to the journal.
     want = {"/api/lore/write/questions", "/api/lore/write/draft", "/api/lore/write/commit",
-            "/api/lore/write/entries", "/api/entities"}
+            "/api/lore/write/entries", "/api/entities", "/api/event-types", "/api/events"}
     if paths != want:
         fail(f"F1b: writePanel.svelte.js calls {sorted(paths)}")
     panel = (lore / "WritePanel.svelte").read_text(encoding="utf-8")
````

2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
4. Run the checks below, then the full corpus.

## Scope OUT

- The commit writing vocabulary (a type or a sorte): the panel creates a type first; a sorte the world lacks is noted.
- A lore entry for « Déclarer un événement » (the journal is its record).
- Undoing an entry's rows (M2 of 0098).

## Invariants to defend

INV-57: a statement commits whole or not at all, every row recorded in `lore_entry_row` -- an event's `event`, `fact`, `event_participant`, `fact_default`, `knowledge`, `attribute_value`, `attribute_change` (EL3). INV-22: a type is named by a code from a coded list. INV-01: the draft's context keeps excluding creator-only facts (unchanged). INV-07: a PC participant's knowledge stays unsecret (the writer). INV-48: the prompt changes by a new version, the creator's edits kept.

## Decision rights

STOP:
- The commit would create an event type or a sorte.
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
- `python tooling/verify/checks/event_lore.py` -> `PASS`.
- `python tooling/verify/checks/lore_write.py` -> `PASS`.
- `python tooling/verify/checks/lore_usage.py` -> `PASS`.
- `python tooling/verify/checks/condition_interpreter.py` -> `PASS`.
- `python tooling/verify/checks/event_editor.py` -> `PASS`.
- `python tooling/verify/checks/frontend_build_fresh.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (162 on the prototype).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **EL1** -- `scripts/seed_pilot.py LORE_WRITE_PROMPT_HEADS`: `        variables=list(LORE_PROPOSAL_VARIABLES),` -> `        variables=["facets", "entities", "facts", "statement", "answers"],`
  - **EL2** -- `lore_write_draft.py _event_participant`: `        if out["sorte_id"] is None:` -> `        if False:`
  - **EL3** -- `lore_write_apply.py _validate_event`: `        raise ProposalError(f"{where} : crée d'abord le type proposé.")` -> `        pass`
  - **EL4** -- `frontend/src/lore/WritePanel.svelte`: ` canPrefill={false} />` -> ` />`
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated; the static build rebuilt.
