<!-- slug: event-conditions -->
# BRIEF 0114-E — "A condition counts the events its subject lived -- the `event` form, its windows and filters; a quest step says when it has failed"

Lot: LOT-0114-event-journal.md (authoritative on conflict)
Depends on: BRIEF-0114-D (the model without `event_entity`), BRIEF-0114-C (C-05)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0114-D's commit).

- `src/world_engine/condition_forms.py:73` -> `REQUIREMENT_TYPES: tuple[str, ...] = (`, its last form `"attribute"`
- `src/world_engine/conditions.py:83` -> `class Bindings:`
- `src/world_engine/writes/quests.py:58` -> `def _clean_offer_steps(db: Session, world_id: str, steps: list[PlanStep]) -> list[tuple[PlanStep, object, object]]:`
- `src/world_engine/day_plan.py:77` -> `class PlanStep:`
- `src/world_engine/quest_reads.py:184` -> `def _steps_view(agenda: Agenda, character: Character, db: Session) -> list[dict]:`
- `src/world_engine/models/config.py` -> `CONDITION_WINDOWS` and `class ConditionNodeFilter` (A's)
- No `tooling/verify/checks/event_conditions.py`.

## Facts carried

### R-07 — conditions: roles, nodes, the draft journal
Opened: `src/world_engine/models/config.py:130` (`CONDITION_ROLES =
("eligibility", "prerequisite", "completion")`), `:157` (`ConditionNode`),
`:71` (`AgendaStep`, no start time); `src/world_engine/models/pipeline.py:451`
(`ConditionDraft`, its own role CHECK);
`src/world_engine/conditions.py:430` (`read_condition`);
`src/world_engine/writes/conditions.py:210` (`write_condition`, the one
writer).
Consequence: A adds `failure` to both role CHECKs (rebuilding
`condition` and `condition_draft`), `condition_node.since` (CHECK on
`CONDITION_WINDOWS`), `condition_node_filter`, `agenda_step.started_at`.

### R-08 — quests carry their conditions
Opened: `src/world_engine/writes/quests.py:58` (`_clean_offer_steps`),
`:201` (`accept_quest` copies each step's conditions);
`src/world_engine/writes/goals_agendas.py:289` (`write_agenda_step`), `:324`
(`write_agenda_step_status`); `src/world_engine/quest_reads.py:125`
(`editor_choices`), `_steps_view` (completion shown, never acting);
`src/world_engine/day_plan.py` `PlanStep`, `plan_bindings`.
Consequence: E adds `failure` beside `completion` on every path, sets
`started_at` where a step becomes active, binds `quest_since` from the
quest's acceptance.

### R-14 — fifteen seconds per check [M]
Opened: `tooling/verify/checks/corpus_gate.py` (per-check subprocess,
timeout a failure), `.claude/rules/verify-checks.md`.
Consequence: six checks, each measured on the replay: `event_journal.py`
4.8 s, `event_writes.py` 1.9 s, `event_contexts.py` 6.3 s,
`event_conditions.py` 1.4 s, `event_interpreter.py` 4.1 s,
`event_analyzer.py` 6.7 s.

## Contracts

### C-01 — the vocabulary's tables (v2.24)
Produced by: BRIEF-0114-A   Consumed by: B-H
`event_type` (`world_id`, `name` unique per world, `domain` in
`EVENT_DOMAINS`, `counts_quantity`, `in_chronicle`, `participants_secret`,
`status` in `EVENT_VOCAB_STATUSES = ("active", "retired")`);
`event_type_role` (`type_id`, `name` unique per type, `position`,
`accepts_sorte`, `status`); `event_type_role_type` (`role_id`,
`entity_type`); `event_type_scope` (`type_id`, `kind` in
`EVENT_SCOPE_KINDS = ("location", "world", "rencontre", "faction")`,
`role_id` for `rencontre`/`faction`, `level` on the ladder);
`event_sorte` (`world_id`, `name` unique per world, `status`);
`event_participant` (`event_id`, `role_id`, `entity_id` XOR `sorte_id`,
`position`); `condition_node_filter` (`node_id`, `role_id`, `entity_id`
XOR `sorte_id`, `position`). Columns: `event.type_id`, `event.quantity`
(1 or more), `agenda_step.started_at`, `condition_node.since` (in
`CONDITION_WINDOWS = ("always", "quest", "step")`); `CONDITION_ROLES` ends
with `failure`.

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

### C-08 — the `event` leaf and the `failure` role
Produced by: BRIEF-0114-E   Consumed by: F, G
Stored: `form = "event"`, `target_key` an active event type, `value` the
subject's role (None: any), `threshold` (1 or more, 1 when unsaid),
`target_entity_id` a location (it or under it) or None, `since` in
`CONDITION_WINDOWS` (`always` when unsaid), filters
(`condition_node_filter`) on other roles, never one role twice. An
eligibility refuses `quest`/`step`. `condition_forms.EventFilter(role_id,
entity_id=None, sorte_id=None)`, `RequirementSpec.since`, `.filters`,
`Verdict.events: tuple[(fact_id, qty)]`, `counted_events`,
`evaluate_event(req, taker, db, since_at)`; `conditions.Bindings.quest_since`,
`.step_since`, `for_step(bindings, step)`, `known_event_facts(db,
verdict, viewer_id)`, `VerdictNode.seen_by(viewer_id, known=None)`,
`filters_from(raw)`; `node_to_dict` writes `since` and `filters` on an
event leaf only. `PlanStep.failure`; offer and quest views carry
`failure` / `failure_met`. `editor_choices` adds `event_types` [{id, name,
counts_quantity, roles [{id, name, entity_types, accepts_sorte}]}] and
`sortes` [{id, name}].

## Context

G1: one form, `event`, counts the events of one type its subject took part in -- in a role or any, at a place or under it, filtered on other roles by an entity or a sorte, quantities added -- since always, the quest's acceptance or the step's start (F1). A player recounts only the events whose fact his character knows (V1 for events). H1: a quest step may carry a `failure` condition, shown in Journée and flagged when met, never acting -- the creator decides, as for completion (M1).

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `condition_forms.py`: `event` in `REQUIREMENT_TYPES`, `KEY_TARGET_TYPES`, `THRESHOLD_TYPES`, `ANY_SUBJECT_TYPES`; `EventFilter`, `RequirementSpec.since/filters`, `Verdict.events`; `_places_within`, `counted_events`, `evaluate_event`, `_eval_event` (C-08);
   - `conditions.py`: `Bindings.quest_since/step_since`, `for_step`, `known_event_facts`, `seen_by(viewer_id, known)` with `_seen_event`, `EVENT_FORM`, `filters_from`, the window in `_evaluate_leaf`, filters read and written (`node_to_dict` writes `since`/`filters` on an event leaf only);
   - `writes/conditions.py`: `_clean_event`, `_clean_filter`; an eligibility refuses `quest`/`step`; nodes' `since` and filters written, deleted with them; the policy file;
   - `started_at` set where a step becomes active: `writes/goals_agendas.py` (`write_agenda_step`, `write_agenda_step_status`), `cockpit/crud/agendas.py`;
   - the `failure` role carried: `day_plan.PlanStep.failure`, `plan_bindings` (`quest_since`), `writes/quests.py` (offer steps, `accept_quest`), `quest_reads.py` (`failure`, `failure_met`, the editor's `event_types` and `sortes`), `cockpit/routes/quests.py` (`OfferStepBody.failure`, `failure_draft_id`);
   - French: `condition_text.py` (`FORM_PHRASES_FR["event"]`, `SINCE_LABELS_FR`, the details), `day_resolve.py` (`_BLOCKED_DETAIL_FR["event"]`, known facts into `seen_by`); `condition_interpreter.TARGET_HINTS_FR["event"]`;
   - frontend: `questRequirements.js` (`REQUIREMENT_FORMS.event`, `EVENT_WINDOWS`, `eventTypeOf`, `fillerOptions`, the body and the draft), `QuestRequirementRow.svelte` (role, count, place, window, filters), `QuestOffers.svelte` and `questOffers.svelte.js` (« Échouée quand »), `journee/QuestPanel.svelte` (the failure lines);
   - checks follow the vocabulary: `quests.py` (QA1), `day_plan.py` (R3), `attribute_interpreter.py` (AE1: four conditions); creates check `event_conditions.py` (EE1-EE6);
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - frontend/src/creation/QuestOffers.svelte
   - frontend/src/creation/QuestRequirementRow.svelte
   - frontend/src/creation/questOffers.svelte.js
   - frontend/src/creation/questRequirements.js
   - frontend/src/journee/QuestPanel.svelte
   - src/world_engine/cockpit/crud/agendas.py
   - src/world_engine/cockpit/routes/quests.py
   - src/world_engine/condition_forms.py
   - src/world_engine/condition_interpreter.py
   - src/world_engine/condition_text.py
   - src/world_engine/conditions.py
   - src/world_engine/day_plan.py
   - src/world_engine/day_resolve.py
   - src/world_engine/quest_reads.py
   - src/world_engine/writes/conditions.py
   - src/world_engine/writes/goals_agendas.py
   - src/world_engine/writes/quests.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/canon_write_policy.txt
   - tooling/verify/checks/attribute_interpreter.py
   - tooling/verify/checks/day_plan.py
   - tooling/verify/checks/event_conditions.py
   - tooling/verify/checks/quests.py

````diff
diff --git a/frontend/src/creation/QuestOffers.svelte b/frontend/src/creation/QuestOffers.svelte
index 14b0713..35860d3 100644
--- a/frontend/src/creation/QuestOffers.svelte
+++ b/frontend/src/creation/QuestOffers.svelte
@@ -161,6 +161,9 @@
             <div class="muted">Objectif atteint quand</div>
             <ConditionEditor cond={step.completion} {choices} unsaved={draft.unsavedAttributes} role="completion"
                              emptyLabel="Rien de vérifiable : c'est vous qui le déclarez." addLabel="+ condition d'objectif" />
+            <div class="muted">Échouée quand (affiché, n'agit jamais)</div>
+            <ConditionEditor cond={step.failure} {choices} unsaved={draft.unsavedAttributes} role="failure"
+                             emptyLabel="Aucune condition d'échec." addLabel="+ condition d'échec" />
           </div>
         {/each}
         <button onclick={() => draft.steps.push(blankStep())}>+ étape</button>
diff --git a/frontend/src/creation/QuestRequirementRow.svelte b/frontend/src/creation/QuestRequirementRow.svelte
index c24eec4..a20b6b5 100644
--- a/frontend/src/creation/QuestRequirementRow.svelte
+++ b/frontend/src/creation/QuestRequirementRow.svelte
@@ -4,9 +4,11 @@
      takes one. `req` is a draft object owned by questOffersState.
      TICKET-0111: its subject first (P1), its value when the form compares
      to one. TICKET-0113: an `attribute` compares to what its attribute's
-     kind takes -- a label, an integer (« ou plus »), or an entity (or anyone). */
-  import { REQUIREMENT_FORMS, attributeOf, attributeTargets, subjectOptions, targetOptions,
-           valueOptions } from './questRequirements.js';
+     kind takes -- a label, an integer (« ou plus »), or an entity (or anyone).
+     TICKET-0114 (BRIEF-0114-E): an `event` takes the subject's role (or any),
+     a count, a place, a window, and filters on the type's other roles. */
+  import { EVENT_WINDOWS, REQUIREMENT_FORMS, attributeOf, attributeTargets, eventTypeOf, fillerOptions,
+           subjectOptions, targetOptions, valueOptions } from './questRequirements.js';
 
   let { req, choices, onremove } = $props();
 
@@ -14,6 +16,15 @@
   let options = $derived(targetOptions(req.type, choices));
   let values = $derived(valueOptions(req.type, choices));
   let attr = $derived(req.type === 'attribute' ? attributeOf(req.target_key, choices) : null);
+  let evType = $derived(req.type === 'event' ? eventTypeOf(req.target_key, choices) : null);
+
+  function roleOf(roleId) {
+    return evType?.roles.find((r) => r.id === roleId) || null;
+  }
+
+  function addFilter() {
+    req.filters = [...(req.filters || []), { role_id: '', filler: '' }];
+  }
 
   function setType(type) {
     req.type = type;
@@ -21,6 +32,8 @@
     req.target_key = '';
     req.threshold = REQUIREMENT_FORMS[type].threshold ? 1 : null;
     req.value = '';
+    req.since = 'always';
+    req.filters = [];
   }
 
   function setTarget(value) {
@@ -32,6 +45,10 @@
       req.target_entity_id = '';
       req.threshold = next && next.kind === 'integer' ? 1 : null;
     }
+    if (req.type === 'event') {
+      req.value = '';
+      req.filters = [];
+    }
   }
 </script>
 
@@ -83,16 +100,66 @@
       {/each}
     </select>
   {/if}
+  {#if evType}
+    <select value={req.value ?? ''} title="Son rôle dans l’événement"
+            onchange={(e) => { req.value = e.target.value; }}>
+      <option value="">— n’importe quel rôle —</option>
+      {#each evType.roles as r (r.id)}
+        <option value={r.id}>{r.name}</option>
+      {/each}
+    </select>
+  {/if}
   {#if form.threshold}
     <input type="number" min="1" max={req.type === 'skill_rank_gte' ? 5 : undefined}
            style="width:70px" value={req.threshold ?? ''}
            oninput={(e) => { req.threshold = e.target.value === '' ? null : Number(e.target.value); }}>
+    {#if req.type === 'event'}<span class="quest-req-hint">fois ou plus</span>{/if}
+  {/if}
+  {#if req.type === 'event'}
+    <select value={req.target_entity_id ?? ''} title="Où"
+            onchange={(e) => { req.target_entity_id = e.target.value; }}>
+      <option value="">— n’importe où —</option>
+      {#each choices?.locations || [] as l (l.id)}
+        <option value={l.id}>{l.name}</option>
+      {/each}
+    </select>
+    <select value={req.since || 'always'} title="Depuis quand"
+            onchange={(e) => { req.since = e.target.value; }}>
+      {#each Object.entries(EVENT_WINDOWS) as [since, label] (since)}
+        <option value={since}>{label}</option>
+      {/each}
+    </select>
   {/if}
   <button class="btn-icon" title="Retirer" onclick={() => onremove()}>✕</button>
 </div>
+{#if evType}
+  <div class="quest-req-filters">
+    {#each req.filters || [] as f, i (i)}
+      <div class="quest-req">
+        <span class="quest-req-hint">avec</span>
+        <select value={f.role_id} onchange={(e) => { f.role_id = e.target.value; f.filler = ''; }}>
+          <option value="">— rôle —</option>
+          {#each evType.roles.filter((r) => r.id !== req.value) as r (r.id)}
+            <option value={r.id}>{r.name}</option>
+          {/each}
+        </select>
+        <select value={f.filler} onchange={(e) => { f.filler = e.target.value; }}>
+          <option value="">—</option>
+          {#each fillerOptions(roleOf(f.role_id), choices) as o (o.value)}
+            <option value={o.value}>{o.label}</option>
+          {/each}
+        </select>
+        <button class="btn-icon" title="Retirer le filtre"
+                onclick={() => { req.filters = req.filters.filter((_, j) => j !== i); }}>✕</button>
+      </div>
+    {/each}
+    <button class="btn-ghost" onclick={addFilter}>+ filtrer sur un autre rôle</button>
+  </div>
+{/if}
 
 <style>
   .quest-req { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin: 3px 0; }
   .quest-req select { max-width: 260px; }
   .quest-req-hint { font-size: 12px; opacity: 0.7; }
+  .quest-req-filters { margin-left: 24px; }
 </style>
diff --git a/frontend/src/creation/questOffers.svelte.js b/frontend/src/creation/questOffers.svelte.js
index 146a7e9..9b35fcd 100644
--- a/frontend/src/creation/questOffers.svelte.js
+++ b/frontend/src/creation/questOffers.svelte.js
@@ -10,7 +10,9 @@
    of the interpreter's proposal inserted into it, which the save marks.
    Since TICKET-0113 (BRIEF-0113-E, WN2): `unsavedAttributes`, the
    attributes the interpreter proposed and the creator confirmed, sent with
-   the save, which writes those a condition names. */
+   the save, which writes those a condition names. Since TICKET-0114
+   (BRIEF-0114-E, H1): each step's failure condition, shown on the quest
+   and never acting. */
 import { api } from './sheetRequest.svelte.js';
 import { blankCondition, conditionBody, conditionDraft } from './questRequirements.js';
 import { blankTerm, termBody } from './questTerms.js';
@@ -29,7 +31,8 @@ export const questOffersState = $state({
 });
 
 export function blankStep() {
-  return { objective: '', cost: 1, domain: '', prerequisite: blankCondition(), completion: blankCondition() };
+  return { objective: '', cost: 1, domain: '', prerequisite: blankCondition(), completion: blankCondition(),
+           failure: blankCondition() };
 }
 
 export function newDraft() {
@@ -51,6 +54,7 @@ export function editOffer(offer) {
     steps: offer.steps.map((s) => ({
       objective: s.objective, cost: s.cost, domain: s.domain || '',
       prerequisite: conditionDraft(s.prerequisite), completion: conditionDraft(s.completion),
+      failure: conditionDraft(s.failure),
     })),
     terms: (offer.terms || []).map((t) => ({
       direction: t.direction, currency: t.currency, counterparty_entity_id: t.counterparty_entity_id || '',
@@ -131,6 +135,7 @@ function draftBody(draft) {
       objective: s.objective, cost: Number(s.cost), domain: s.domain || null,
       prerequisite: conditionBody(s.prerequisite), completion: conditionBody(s.completion),
       prerequisite_draft_id: s.prerequisite.draftId || null, completion_draft_id: s.completion.draftId || null,
+      failure: conditionBody(s.failure), failure_draft_id: s.failure.draftId || null,
     })),
     terms: draft.terms.map(termBody),
     unsaved_attributes: draft.unsavedAttributes.map((u) => ({ ref: u.ref, definition: u.definition })),
diff --git a/frontend/src/creation/questRequirements.js b/frontend/src/creation/questRequirements.js
index 92f5e5e..73c1e5c 100644
--- a/frontend/src/creation/questRequirements.js
+++ b/frontend/src/creation/questRequirements.js
@@ -12,7 +12,11 @@
    choices in `choices.form_values[form]`. TICKET-0113 (BRIEF-0113-B):
    `attribute` replaces `vital_status` -- its key is an attribute of
    `choices.attributes`, and what it compares to depends on that
-   attribute's kind (`attributeOf`): a label, a threshold, or an entity. */
+   attribute's kind (`attributeOf`): a label, a threshold, or an entity.
+   TICKET-0114 (BRIEF-0114-E, G1): `event` counts the events of one type
+   its subject took part in -- its key an event type of
+   `choices.event_types`, its value the subject's role (empty: any), its
+   entity the place, plus a window (`since`) and filters on other roles. */
 
 export const REQUIREMENT_FORMS = {
   knowledge: { label: 'Connaît le fait', list: 'facts', column: 'key', threshold: false },
@@ -27,6 +31,15 @@ export const REQUIREMENT_FORMS = {
   no_debt_to: { label: 'N’a aucune dette envers', list: 'givers', column: 'entity', threshold: false },
   item_held: { label: 'Possède au moins (objet)', list: 'items', column: 'entity', threshold: true },
   attribute: { label: 'Est dans l’état', list: 'attributes', column: 'key', threshold: false },
+  event: { label: 'A vécu l’événement', list: 'eventTypes', column: 'key', threshold: true },
+};
+
+// TICKET-0114 (F1): an `event` leaf's window. Mirrors
+// `models.CONDITION_WINDOWS` (kept equal by `event_conditions.py`).
+export const EVENT_WINDOWS = {
+  always: 'depuis toujours',
+  quest: 'depuis l’acceptation de la quête',
+  step: 'depuis le début de l’étape',
 };
 
 // `resource`'s key is a label: one currency per world (the ledger has no
@@ -45,7 +58,24 @@ export const SUBJECT_ROLES = {
 };
 
 export function blankRequirement() {
-  return { type: 'has_met', subject: 'role:doer', target_entity_id: '', target_key: '', threshold: null, value: '' };
+  return { type: 'has_met', subject: 'role:doer', target_entity_id: '', target_key: '', threshold: null, value: '',
+           since: 'always', filters: [] };
+}
+
+/** TICKET-0114: the event type a row names, from `choices.event_types`. */
+export function eventTypeOf(key, choices) {
+  return (choices?.event_types || []).find((t) => t.id === key) || null;
+}
+
+/** TICKET-0114: what may fill a filter on `role` -- the entities of a type
+    it accepts, then the sortes when it takes one (`sorte:<id>`). */
+export function fillerOptions(role, choices) {
+  if (!role) return [];
+  const people = (choices?.entities || []).filter((e) => role.entity_types.includes(e.type))
+    .map((e) => ({ value: 'entity:' + e.id, label: e.name }));
+  const sortes = role.accepts_sorte
+    ? (choices?.sortes || []).map((s) => ({ value: 'sorte:' + s.id, label: s.name + ' (sorte)' })) : [];
+  return people.concat(sortes);
 }
 
 /** The subject options: the three roles, then every character -- or, for
@@ -98,6 +128,7 @@ export function targetOptions(form, choices) {
     case 'givers': return choices.givers.map((c) => ({ value: c.id, label: c.name }));
     case 'items': return choices.items.map((c) => ({ value: c.id, label: c.name }));
     case 'attributes': return (choices.attributes || []).map((a) => ({ value: a.key, label: a.name }));
+    case 'eventTypes': return (choices.event_types || []).map((t) => ({ value: t.id, label: t.name }));
     default: return [];
   }
 }
@@ -123,6 +154,20 @@ export function requirementBody(req) {
       value: req.value || null,
     };
   }
+  if (req.type === 'event') {
+    return {
+      op: 'leaf', type: req.type,
+      subject_role: kind === 'role' ? id : null, subject_entity_id: kind === 'entity' ? id : null,
+      target_entity_id: req.target_entity_id || null, target_key: req.target_key || null,
+      threshold: req.threshold === '' || req.threshold === null || req.threshold === undefined
+        ? null : Number(req.threshold),
+      value: req.value || null, since: req.since || 'always',
+      filters: (req.filters || []).filter((f) => f.role_id && f.filler).map((f) => {
+        const [fk, fid] = f.filler.split(':');
+        return { role_id: f.role_id, entity_id: fk === 'entity' ? fid : null, sorte_id: fk === 'sorte' ? fid : null };
+      }),
+    };
+  }
   return {
     op: 'leaf',
     type: req.type,
@@ -149,6 +194,10 @@ export function conditionDraft(view) {
       ...r,
       subject: r.subject_entity_id ? 'entity:' + r.subject_entity_id : 'role:' + (r.subject_role || 'doer'),
       target_entity_id: r.target_entity_id || '', target_key: r.target_key || '', value: r.value || '',
+      since: r.since || 'always',
+      filters: (r.filters || []).map((f) => ({
+        role_id: f.role_id, filler: f.entity_id ? 'entity:' + f.entity_id : f.sorte_id ? 'sorte:' + f.sorte_id : '',
+      })),
     })),
     locked: null,
     lines: [],
diff --git a/frontend/src/journee/QuestPanel.svelte b/frontend/src/journee/QuestPanel.svelte
index fd8b811..71b085d 100644
--- a/frontend/src/journee/QuestPanel.svelte
+++ b/frontend/src/journee/QuestPanel.svelte
@@ -8,7 +8,9 @@
      recap (SettlementRecap) and settles from it (D1). TICKET-0111
      (BRIEF-0111-D, M1): the active step shows where its objective stands,
      each line of its completion condition marked ✓, ✗ or ?, with its
-     progress (« 3/15 ») -- shown, never acted on. */
+     progress (« 3/15 ») -- shown, never acted on. TICKET-0114 (BRIEF-0114-E,
+     H1): its failure condition the same way; met, it is flagged, the
+     creator decides. */
   import { questState, loadQuests, acceptOffer, abandonQuest, openSettlement } from './quests.svelte.js';
   import SettlementRecap from './SettlementRecap.svelte';
 
@@ -69,6 +71,16 @@
                   {/each}
                 </div>
               {/if}
+              {#if step.status === 'active' && step.failure?.length}
+                <div class="objective">
+                  <span class="muted">{step.failure_met ? 'Échouée — à vous de trancher' : 'Échoue si'} :</span>
+                  {#each step.failure as line, i (i)}
+                    <div class={'cl-' + line.state} style={'padding-left:' + line.depth * 14 + 'px'}>
+                      {line.mark} {line.text}{#if line.progress} — {line.progress}{/if}
+                    </div>
+                  {/each}
+                </div>
+              {/if}
             </li>
           {/each}
         </ol>
diff --git a/src/world_engine/cockpit/crud/agendas.py b/src/world_engine/cockpit/crud/agendas.py
index 1357ce5..56d4877 100644
--- a/src/world_engine/cockpit/crud/agendas.py
+++ b/src/world_engine/cockpit/crud/agendas.py
@@ -253,6 +253,8 @@ def update_agenda_step(step_id: str, body: AgendaStepPatchBody, db: DbSession =
             # Manual reactivation must respect the partial unique index — the
             # creator completes or fails the current active step first;
             # deactivate is not a thing. The IntegrityError surfaces as a 409.
+            if step.status != "active":
+                step.started_at = datetime.now(UTC)  # TICKET-0114 (BRIEF-0114-E, F1)
             step.status = "active"
             step.updated_at = datetime.now(UTC)
             db.add(step)
diff --git a/src/world_engine/cockpit/routes/quests.py b/src/world_engine/cockpit/routes/quests.py
index 7b2ba76..0bf6dbf 100644
--- a/src/world_engine/cockpit/routes/quests.py
+++ b/src/world_engine/cockpit/routes/quests.py
@@ -60,10 +60,13 @@ class OfferStepBody(BaseModel):
     # `conditions.node_to_dict`; null is none.
     prerequisite: Optional[dict] = None
     completion: Optional[dict] = None
+    # TICKET-0114 (H1): when the step has failed -- shown, never acting.
+    failure: Optional[dict] = None
     # TICKET-0112 (IH1): the interpreter's proposal the creator inserted into
     # each condition, if any; saving marks it `saved` (`mark_draft_saved`).
     prerequisite_draft_id: Optional[str] = None
     completion_draft_id: Optional[str] = None
+    failure_draft_id: Optional[str] = None
 
 
 class TermBody(BaseModel):
@@ -133,9 +136,10 @@ def _save_offer(body: OfferBody, offer: Optional[QuestOffer], world_id: str, db:
         # to their ids.
         trees, keys, labels = materialize(
             db, world_id, [u.model_dump() for u in body.unsaved_attributes],
-            [body.eligibility] + [t for s in body.steps for t in (s.prerequisite, s.completion)])
+            [body.eligibility] + [t for s in body.steps for t in (s.prerequisite, s.completion, s.failure)])
         steps = [PlanStep(objective=s.objective, cost=s.cost, domain=s.domain or None,
-                          prerequisite=node_from_dict(trees[1 + 2 * i]), completion=node_from_dict(trees[2 + 2 * i]))
+                          prerequisite=node_from_dict(trees[1 + 3 * i]), completion=node_from_dict(trees[2 + 3 * i]),
+                          failure=node_from_dict(trees[3 + 3 * i]))
                  for i, s in enumerate(body.steps)]
         offer = write_quest_offer(
             db, world_id=world_id, offer=offer, giver_entity_id=body.giver_entity_id, title=body.title,
@@ -160,7 +164,8 @@ def _mark_drafts(body: OfferBody, trees: list, offer_id: str, world_id: str, db:
     wrote (`as_saved`, TICKET-0113). A draft that cannot be marked is
     skipped: the journal never fails the creator's save."""
     ids = [body.eligibility_draft_id] + [
-        d for step in body.steps for d in (step.prerequisite_draft_id, step.completion_draft_id)]
+        d for step in body.steps for d in (step.prerequisite_draft_id, step.completion_draft_id,
+                                           step.failure_draft_id)]
     for draft_id, raw in zip(ids, trees):
         if draft_id:
             tree = node_to_dict(clean_condition(db, world_id, node_from_dict(raw)))
diff --git a/src/world_engine/condition_forms.py b/src/world_engine/condition_forms.py
index eab6130..6583cea 100644
--- a/src/world_engine/condition_forms.py
+++ b/src/world_engine/condition_forms.py
@@ -44,11 +44,15 @@ from .models import (
     Character,
     Debt,
     Entity,
+    Event,
+    EventParticipant,
+    EventType,
     Fact,
     FactionMembership,
     ItemHolding,
     Knowledge,
     Ledger,
+    Location,
     Quest,
     QuestOffer,
     Relation,
@@ -69,11 +73,15 @@ from .skill_access import held_rank, skill_label
 # (TICKET-0113, BRIEF-0113-B, WE1, WG1): `attribute` reads one attribute of
 # its subject -- a world's definition or a system attribute, `vital_status`
 # among them -- and replaces the `vital_status` form (`attributes.ATTRIBUTE_FORM`
-# names it there, `attribute_conditions.py` AB1 keeps the two equal).
+# names it there, `attribute_conditions.py` AB1 keeps the two equal). Since
+# v2.24 (TICKET-0114, BRIEF-0114-E, G1): `event` counts what happened --
+# the events of one type its subject took part in, in one role or any, with
+# filters on the other roles and a place, since a window (F1);
+# `event_vocab.EVENT_FORM` names it there.
 REQUIREMENT_TYPES: tuple[str, ...] = (
     "knowledge", "relation_gte", "resource", "location_reachable",
     "has_met", "faction_member", "skill_rank_gte", "quest_state",
-    "has_debt_to", "no_debt_to", "item_held", "attribute",
+    "has_debt_to", "no_debt_to", "item_held", "attribute", "event",
 )
 
 # What `emit_plan`'s parser accepts from the model (TICKET-0108): the four
@@ -86,12 +94,12 @@ MODEL_REQUIREMENT_TYPES: tuple[str, ...] = ("knowledge", "relation_gte", "resour
 ENTITY_TARGET_TYPES: tuple[str, ...] = (
     "relation_gte", "location_reachable", "has_met", "faction_member", "has_debt_to", "no_debt_to", "item_held",
 )
-KEY_TARGET_TYPES: tuple[str, ...] = ("knowledge", "resource", "skill_rank_gte", "quest_state", "attribute")
-THRESHOLD_TYPES: tuple[str, ...] = ("relation_gte", "resource", "skill_rank_gte", "item_held")
+KEY_TARGET_TYPES: tuple[str, ...] = ("knowledge", "resource", "skill_rank_gte", "quest_state", "attribute", "event")
+THRESHOLD_TYPES: tuple[str, ...] = ("relation_gte", "resource", "skill_rank_gte", "item_held", "event")
 # v2.23 (TICKET-0113, WG1): the forms whose subject may be any entity of
 # the world -- an attribute applies to the types its definition names; every
 # other form judges a character.
-ANY_SUBJECT_TYPES: tuple[str, ...] = ("attribute",)
+ANY_SUBJECT_TYPES: tuple[str, ...] = ("attribute", "event")
 # A quest's state is its agenda's (M1 of TICKET-0108); `open` is `active` or
 # `paused`, the player's « en cours ».
 QUEST_STATES: tuple[str, ...] = ("open", "completed", "failed", "abandoned")
@@ -105,6 +113,15 @@ QUEST_STATE_AGENDA_STATUSES: dict[str, tuple[str, ...]] = {
 FORM_VALUES: dict[str, tuple[str, ...]] = {"quest_state": QUEST_STATES}
 
 
+@dataclass(frozen=True)
+class EventFilter:
+    """An `event` leaf's filter on one other role of its type (TICKET-0114):
+    an entity or a sorte fills it (`condition_node_filter`)."""
+    role_id: str
+    entity_id: Optional[str] = None
+    sorte_id: Optional[str] = None
+
+
 @dataclass(frozen=True)
 class RequirementSpec:
     """One form with its arguments: a leaf of the condition language. Its
@@ -119,6 +136,12 @@ class RequirementSpec:
     subject_role: Optional[str] = "doer"
     subject_entity_id: Optional[str] = None
     value: Optional[str] = None
+    # `event` (TICKET-0114): since when it counts (`models.CONDITION_WINDOWS`)
+    # and its filters on the other roles; `value` is the subject's role id
+    # (None: any role), `target_key` the type, `target_entity_id` a place,
+    # `threshold` how many.
+    since: Optional[str] = None
+    filters: tuple[EventFilter, ...] = ()
 
 
 
@@ -138,6 +161,10 @@ class Verdict:
     # TICKET-0113 (BRIEF-0113-B, WH1): the leaf reads a hidden attribute --
     # never written out, nor its state shown, on a player surface.
     hidden: bool = False
+    # TICKET-0114 (BRIEF-0114-E): an `event` leaf's counted events, as
+    # (fact id, quantity) -- a player surface recounts the ones its viewer
+    # knows (`conditions.VerdictNode.seen_by`).
+    events: tuple = ()
 
 
 
@@ -435,6 +462,66 @@ def _eval_no_debt_to(req: RequirementSpec, character: Character, db: Session, re
     )
 
 
+def _places_within(db: Session, place_id: str) -> set[str]:
+    """`place_id` and every location under it (`parent_location_id`), its own
+    cycle-safe reader: « à Ombreval » counts an event in a house of it."""
+    found, frontier = {place_id}, [place_id]
+    while frontier:
+        children = db.exec(select(Location.id).where(Location.parent_location_id.in_(frontier))).all()
+        frontier = [c for c in children if c not in found]
+        found.update(frontier)
+    return found
+
+
+def counted_events(db: Session, req: RequirementSpec, subject_id: str, since_at) -> list[tuple]:
+    """The (event id, fact id, quantity) an `event` leaf counts for its
+    subject: events of the type `target_key` the subject took part in -- in
+    the role `value`, or any --, each filter's role filled as it says, at the
+    place `target_entity_id` or under it, recorded at or after `since_at`."""
+    query = (select(Event.id, Fact.id, Event.quantity).join(Fact, Fact.event_id == Event.id)
+             .where(Event.type_id == req.target_key))
+    taking_part = select(EventParticipant.event_id).where(EventParticipant.entity_id == subject_id)
+    if req.value:
+        taking_part = taking_part.where(EventParticipant.role_id == req.value)
+    query = query.where(Event.id.in_(taking_part))
+    for f in req.filters:
+        filled = select(EventParticipant.event_id).where(EventParticipant.role_id == f.role_id)
+        filled = filled.where(EventParticipant.entity_id == f.entity_id) if f.entity_id else filled.where(
+            EventParticipant.sorte_id == f.sorte_id)
+        query = query.where(Event.id.in_(filled))
+    if req.target_entity_id:
+        query = query.where(Event.location_id.in_(_places_within(db, req.target_entity_id)))
+    if since_at is not None:
+        query = query.where(Event.recorded_at >= since_at)
+    return list(db.exec(query).all())
+
+
+def evaluate_event(req: RequirementSpec, taker, db: Session, since_at) -> Verdict:
+    """TICKET-0114 (G1, F1): met when the counted events add up to
+    `threshold` (an event's quantity, 1 when it has none). Its subject
+    (`taker`) is any entity -- a faction takes part too. The caller resolves `since_at`
+    from the leaf's window (`conditions._evaluate_leaf`)."""
+    rows = counted_events(db, req, taker.id, since_at)
+    total = sum(quantity or 1 for _event, _fact, quantity in rows)
+    need = req.threshold or 1
+    event_type = db.get(EventType, req.target_key)
+    name = event_type.name if event_type is not None else str(req.target_key)
+    entity = db.get(Entity, taker.id)
+    who = entity.name if entity is not None else taker.id
+    met = total >= need
+    reason = (f"{who}: {total} « {name} », meets requires >= {need}" if met
+              else f"prerequisite not met — {who}: {total} « {name} », requires >= {need}")
+    return Verdict(type=req.type, met=met, current=total, required=need, reason=reason,
+                   required_label=f"{name} ({need})", events=tuple((fact, quantity or 1) for _e, fact, quantity in rows))
+
+
+def _eval_event(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """The table's entry for `event` (no window: every event counts);
+    `conditions._evaluate_leaf` calls `evaluate_event` with its window."""
+    del reachable_ids
+    return evaluate_event(req, character, db, None)
+
+
 _EVALUATORS: dict[str, Callable[[RequirementSpec, Character, Session, object], Verdict]] = {
     "knowledge": _eval_knowledge,
     "relation_gte": _eval_relation_gte,
@@ -448,6 +535,7 @@ _EVALUATORS: dict[str, Callable[[RequirementSpec, Character, Session, object], V
     "no_debt_to": _eval_no_debt_to,
     "item_held": _eval_item_held,
     "attribute": _eval_attribute,
+    "event": _eval_event,
 }
 
 
diff --git a/src/world_engine/condition_interpreter.py b/src/world_engine/condition_interpreter.py
index 991447b..89d0766 100644
--- a/src/world_engine/condition_interpreter.py
+++ b/src/world_engine/condition_interpreter.py
@@ -92,6 +92,7 @@ TARGET_HINTS_FR: dict[str, str] = {
     "attribute": "un état, par son code a ; pour un choix, valeur = un de ses libellés ; pour un nombre, "
                  "seuil = le minimum ; pour une entité, valeur = une entité par son nom, ou null pour "
                  "« quelqu'un »",
+    "event": "un type d'événement, par son nom ; seuil = le nombre minimal (quantités additionnées)",
 }
 # The forms whose target is a code, and the list each code comes from.
 CODE_LISTS: dict[str, str] = {"knowledge": "f", "quest_state": "q", "skill_rank_gte": "s", "attribute": "a"}
diff --git a/src/world_engine/condition_text.py b/src/world_engine/condition_text.py
index b6de4eb..7415bbc 100644
--- a/src/world_engine/condition_text.py
+++ b/src/world_engine/condition_text.py
@@ -23,9 +23,9 @@ from sqlmodel import Session
 
 from .attributes import ATTRIBUTE_FORM, value_label, view_of
 from .condition_forms import RequirementSpec
-from .conditions import ConditionTree, VerdictNode
+from .conditions import ConditionTree, VerdictNode, known_event_facts
 from .knowledge_resolve import resolve_knowledge_level
-from .models import Entity, Fact, QuestOffer
+from .models import Entity, EventSorte, EventType, EventTypeRole, Fact, QuestOffer
 from .prose_render import fact_text
 from .skill_access import skill_label
 
@@ -44,6 +44,14 @@ FORM_PHRASES_FR: dict[str, str] = {
     "no_debt_to": "{who} n'a aucune dette envers {target}",
     "item_held": "{who} possède au moins {threshold} × « {target} »",
     "attribute": "{who} — {target} : {value}",
+    # TICKET-0114 (G1): what happened, counted; `_event_text` adds its
+    # filters, its place and its window.
+    "event": "{who} a vécu « {target} » {value}, au moins {threshold} fois",
+}
+
+# F1 (TICKET-0114): an `event` leaf's window, in French.
+SINCE_LABELS_FR: dict[str, str] = {
+    "always": "", "quest": "depuis l'acceptation de la quête", "step": "depuis le début de l'étape",
 }
 
 # The French of a form's value (`condition_forms.FORM_VALUES`), one label per
@@ -107,6 +115,9 @@ def _target(db: Session, spec: RequirementSpec, unsaved: Optional[dict] = None)
     if spec.type == ATTRIBUTE_FORM:
         view = _view(db, spec.target_key, unsaved)
         return view.name if view is not None else str(spec.target_key)
+    if spec.type == "event":
+        event_type = db.get(EventType, spec.target_key) if spec.target_key else None
+        return event_type.name if event_type is not None else str(spec.target_key)
     return str(spec.target_key or "")
 
 
@@ -130,9 +141,30 @@ def leaf_text(db: Session, spec: RequirementSpec, viewer_id: Optional[str] = Non
     value = _value(db, spec, unsaved)
     text = phrase.format(who=_subject(db, spec), target=_target(db, spec, unsaved), threshold=spec.threshold,
                          value=value)
+    if spec.type == "event":
+        text += _event_details(db, spec)
     return text[0].upper() + text[1:]
 
 
+def _role_name(db: Session, role_id: Optional[str]) -> str:
+    role = db.get(EventTypeRole, role_id) if role_id else None
+    return role.name if role is not None else str(role_id)
+
+
+def _event_details(db: Session, spec: RequirementSpec) -> str:
+    """An `event` leaf's filters (« victime : loup »), place and window."""
+    parts = []
+    for f in spec.filters:
+        sorte = db.get(EventSorte, f.sorte_id) if f.sorte_id else None
+        parts.append(f"{_role_name(db, f.role_id)} : {sorte.name if sorte else _entity_name(db, f.entity_id)}")
+    if spec.target_entity_id:
+        parts.append(f"à {_entity_name(db, spec.target_entity_id)} ou dedans")
+    since = SINCE_LABELS_FR.get(spec.since or "always", "")
+    if since:
+        parts.append(since)
+    return (" (" + ", ".join(parts) + ")") if parts else ""
+
+
 def _hidden(db: Session, spec: RequirementSpec) -> bool:
     view = view_of(db, spec.target_key)
     return view is None or view.hidden
@@ -141,6 +173,8 @@ def _hidden(db: Session, spec: RequirementSpec) -> bool:
 def _value(db: Session, spec: RequirementSpec, unsaved: Optional[dict] = None) -> object:
     """The French of what a leaf compares to: a form's value label, or an
     attribute's label, « N ou plus », an entity or « quelqu'un »."""
+    if spec.type == "event":
+        return f"comme {_role_name(db, spec.value)}" if spec.value else "à un titre ou un autre"
     if spec.type != ATTRIBUTE_FORM:
         return VALUE_LABELS_FR.get(spec.type, {}).get(spec.value, spec.value)
     view = _view(db, spec.target_key, unsaved)
@@ -193,7 +227,8 @@ def verdict_lines(db: Session, verdict: Optional[VerdictNode], viewer_id: Option
     leaf is written as he may read it (A1)."""
     lines: list[dict] = []
     if verdict is not None:
-        seen = verdict.seen_by(viewer_id) if viewer_id is not None else verdict
+        seen = verdict.seen_by(viewer_id, known_event_facts(db, verdict, viewer_id)) \
+            if viewer_id is not None else verdict
         _verdict_lines(db, seen, 0, lines, viewer_id)
     return lines
 
diff --git a/src/world_engine/conditions.py b/src/world_engine/conditions.py
index 27f6596..802f8cb 100644
--- a/src/world_engine/conditions.py
+++ b/src/world_engine/conditions.py
@@ -33,6 +33,7 @@ reads a stored tree back (`read_condition`). Its writer is
 from __future__ import annotations
 
 from dataclasses import dataclass, replace
+from datetime import datetime
 from typing import Optional
 
 from sqlmodel import Session, select
@@ -41,12 +42,14 @@ from .condition_forms import (
     _EVALUATORS,
     ANY_SUBJECT_TYPES,
     HIDDEN_STATE_REASON_FR,
+    EventFilter,
     RequirementSpec,
     Verdict,
     _day_reachable_ids,
     attribute_unjudged,
+    evaluate_event,
 )
-from .models import Character, Condition, ConditionNode, Entity
+from .models import Character, Condition, ConditionNode, ConditionNodeFilter, Entity
 
 # The four connectors, then the leaf.
 CONNECTORS: tuple[str, ...] = ("all", "any", "not", "at_least")
@@ -81,10 +84,14 @@ class ConditionTree:
 
 @dataclass(frozen=True)
 class Bindings:
-    """What the roles name when a condition is judged (P1)."""
+    """What the roles name when a condition is judged (P1), and since when an
+    `event` leaf counts (TICKET-0114, F1): its quest's acceptance, its
+    step's start (the acceptance for a step activated before v2.24)."""
     doer: Character
     giver_id: Optional[str] = None
     contact_id: Optional[str] = None
+    quest_since: Optional[datetime] = None
+    step_since: Optional[datetime] = None
 
 
 @dataclass(frozen=True)
@@ -120,24 +127,60 @@ class VerdictNode:
         _blocking(self, False, found)
         return tuple(found)
 
-    def seen_by(self, viewer_id: str) -> "VerdictNode":
+    def seen_by(self, viewer_id: str, known: Optional[frozenset] = None) -> "VerdictNode":
         """This verdict as the character `viewer_id` could know it (V2): a
         judged leaf whose subject is not him becomes `unknown` -- he cannot
         see whether the giver knows a fact or whether another is alive --
         and every connector is recombined from what is left, so no head
-        line betrays a hidden leaf."""
+        line betrays a hidden leaf. An `event` leaf (TICKET-0114, V1 for
+        events) is recounted from the events whose fact he knows (`known`,
+        `known_event_facts`), about himself or anyone: what he
+        never learned neither counts nor shows; with no `known`, it is
+        `unknown`."""
         if self.op == "leaf":
             if self.verdict is not None and self.verdict.hidden:
                 return replace(self, state="unknown", verdict=None, reason=HIDDEN_STATE_REASON_FR)
+            if self.verdict is not None and self.spec is not None and self.spec.type == EVENT_FORM:
+                return _seen_event(self, known)
             if self.verdict is None or _seen_subject(self.spec, viewer_id):
                 return self
             return replace(self, state="unknown", verdict=None, reason=UNSEEN_REASON_FR)
-        children = tuple(child.seen_by(viewer_id) for child in self.children)
+        children = tuple(child.seen_by(viewer_id, known) for child in self.children)
         return replace(self, state=_combine(self, children), children=children)
 
 
+def for_step(bindings: "Bindings", step) -> "Bindings":
+    """The bindings of one agenda step (TICKET-0114, F1): its start, or its
+    quest's acceptance for a step activated before v2.24 (decision 1 of the
+    lot)."""
+    return replace(bindings, step_since=getattr(step, "started_at", None) or bindings.quest_since)
+
+
+def known_event_facts(db: Session, verdict: Optional["VerdictNode"], viewer_id: str) -> Optional[frozenset]:
+    """What `seen_by` needs to recount an `event` leaf for `viewer_id`: the
+    facts he resolves above `unaware` (0105) -- read only when the verdict
+    holds an event leaf; None otherwise."""
+    if verdict is None or not any(n.spec is not None and n.spec.type == EVENT_FORM for n in verdict.leaf_nodes()):
+        return None
+    from .knowledge_resolve import resolve_known_for_entity
+
+    return frozenset(resolve_known_for_entity(db, viewer_id))
+
+
 # V2 (AMENDMENT-0111-01): why a leaf about someone else shows `?` to a player.
 UNSEEN_REASON_FR = "le personnage ne peut pas le vérifier"
+EVENT_FORM = "event"  # `event_vocab.EVENT_FORM` (EE1 keeps them equal)
+
+
+def _seen_event(node: "VerdictNode", known: Optional[frozenset]) -> "VerdictNode":
+    if known is None:
+        return replace(node, state="unknown", verdict=None, reason=UNSEEN_REASON_FR)
+    verdict = node.verdict
+    seen = tuple((fact, quantity) for fact, quantity in verdict.events if fact in known)
+    total = sum(quantity for _fact, quantity in seen)
+    met = total >= (verdict.required or 1)
+    return replace(node, state="met" if met else "unmet",
+                   verdict=replace(verdict, met=met, current=total, events=seen))
 
 
 def _seen_subject(spec: Optional[RequirementSpec], viewer_id: str) -> bool:
@@ -242,7 +285,12 @@ def node_to_dict(node: Optional[ConditionTree]) -> Optional[dict]:
         return None
     if node.op == "leaf":
         spec = node.leaf
-        return {"op": "leaf", **{key: getattr(spec, key) for key in _LEAF_KEYS}}
+        out = {"op": "leaf", **{key: getattr(spec, key) for key in _LEAF_KEYS}}
+        if spec.type == EVENT_FORM:  # TICKET-0114: only an event leaf has a window and filters
+            out["since"] = spec.since
+            out["filters"] = [{"role_id": f.role_id, "entity_id": f.entity_id, "sorte_id": f.sorte_id}
+                              for f in spec.filters]
+        return out
     out: dict = {"op": node.op, "children": [node_to_dict(child) for child in node.children]}
     if node.op == "at_least":
         out["n"] = node.n
@@ -263,6 +311,15 @@ def node_from_dict(raw: object) -> Optional[ConditionTree]:
     return node
 
 
+def _filters_from(raw: object) -> tuple[EventFilter, ...]:
+    if raw is None or raw == []:
+        return ()
+    if not isinstance(raw, list) or not all(isinstance(f, dict) for f in raw):
+        raise ConditionShapeError(f"a leaf's filters are a list of objects, got {raw!r}")
+    return tuple(EventFilter(role_id=str(f.get("role_id") or ""), entity_id=_blank(f.get("entity_id")),
+                             sorte_id=_blank(f.get("sorte_id"))) for f in raw)
+
+
 def _from_dict(raw: object) -> ConditionTree:
     if not isinstance(raw, dict):
         raise ConditionShapeError(f"a condition node must be an object, got {raw!r}")
@@ -283,6 +340,8 @@ def _from_dict(raw: object) -> ConditionTree:
             target_key=_blank(raw.get("target_key")),
             threshold=threshold,
             value=_blank(raw.get("value")),
+            since=_blank(raw.get("since")),
+            filters=_filters_from(raw.get("filters")),
         )
         return ConditionTree(op="leaf", leaf=spec)
     if op not in CONNECTORS:
@@ -391,11 +450,28 @@ def _subject(spec: RequirementSpec, bindings: Bindings, db: Session) -> tuple[Op
     return character, None
 
 
+_SINCE_UNBOUND_FR = {"quest": "aucune quête acceptée ne le date ici", "step": "aucune étape en cours ne le date ici"}
+
+
+def _since(spec: RequirementSpec, bindings: Bindings) -> tuple[Optional[datetime], Optional[str]]:
+    """F1: when an `event` leaf starts counting, or why it cannot (French)."""
+    if spec.since in (None, "always"):
+        return None, None
+    at = bindings.quest_since if spec.since == "quest" else (bindings.step_since or bindings.quest_since)
+    return (at, None) if at is not None else (None, _SINCE_UNBOUND_FR[spec.since])
+
+
 def _evaluate_leaf(spec: RequirementSpec, bindings: Bindings, db: Session, reachable: dict) -> VerdictNode:
     evaluator = _EVALUATORS.get(spec.type)
     if evaluator is None:
         raise ValueError(f"unknown requirement type {spec.type!r}")
     character, why = _subject(spec, bindings, db)
+    if character is not None and spec.type == EVENT_FORM:
+        since_at, why = _since(spec, bindings)
+        if why is None:
+            verdict = evaluate_event(spec, character, db, since_at)
+            return VerdictNode(state="met" if verdict.met else "unmet", op="leaf", spec=spec, verdict=verdict)
+        character = None
     if character is not None and spec.type in ANY_SUBJECT_TYPES:
         why = attribute_unjudged(spec, character, db)
         character = None if why else character
@@ -440,15 +516,20 @@ def read_condition(db: Session, *, role: str, **owner) -> Optional[ConditionTree
     roots = children.get(None, [])
     if len(roots) != 1:
         raise ValueError(f"condition {condition.id!r} has {len(roots)} roots")
-    return _build(roots[0], children)
+    filters: dict[str, list[ConditionNodeFilter]] = {}
+    for row in db.exec(select(ConditionNodeFilter).where(ConditionNodeFilter.node_id.in_([n.id for n in nodes]))
+                       .order_by(ConditionNodeFilter.position)).all():
+        filters.setdefault(row.node_id, []).append(row)
+    return _build(roots[0], children, filters)
 
 
-def _build(node: ConditionNode, children: dict) -> ConditionTree:
+def _build(node: ConditionNode, children: dict, filters: dict) -> ConditionTree:
     if node.op == "leaf":
         return ConditionTree(op="leaf", leaf=RequirementSpec(
             type=node.form, subject_role=node.subject_role, subject_entity_id=node.subject_entity_id,
             target_entity_id=node.target_entity_id, target_key=node.target_key, threshold=node.threshold,
-            value=node.value,
+            value=node.value, since=node.since,
+            filters=tuple(EventFilter(f.role_id, f.entity_id, f.sorte_id) for f in filters.get(node.id, [])),
         ))
     kids = sorted(children.get(node.id, []), key=lambda n: n.position)
-    return ConditionTree(op=node.op, n=node.n, children=tuple(_build(k, children) for k in kids))
+    return ConditionTree(op=node.op, n=node.n, children=tuple(_build(k, children, filters) for k in kids))
diff --git a/src/world_engine/day_plan.py b/src/world_engine/day_plan.py
index bcf3eb8..0e81261 100644
--- a/src/world_engine/day_plan.py
+++ b/src/world_engine/day_plan.py
@@ -32,6 +32,7 @@ from .conditions import (
     all_of,
     drop_leaves,
     evaluate,
+    for_step,
     map_leaves,
     read_condition,
 )
@@ -79,12 +80,14 @@ class PlanStep:
     (TICKET-0111, I1) -- `all` of the model's leaves for a day plan, any
     tree for a quest step; None when nothing gates it. `completion` (M1,
     BRIEF-0111-D) says when a quest step's objective is reached: shown,
-    never acted on; a day plan has none."""
+    never acted on; a day plan has none. `failure` (TICKET-0114, H1) says
+    when it has failed, shown likewise, never acting."""
     objective: str
     cost: Optional[int]
     domain: Optional[str]
     prerequisite: Optional[ConditionTree] = None
     completion: Optional[ConditionTree] = None
+    failure: Optional[ConditionTree] = None
 
 
 @dataclass(frozen=True)
@@ -131,7 +134,9 @@ def plan_bindings(agenda_id: Optional[str], character: Character, db: Session) -
     offer = db.get(QuestOffer, quest.offer_id) if quest is not None else None
     if offer is None:
         return Bindings(doer=character)
-    return Bindings(doer=character, giver_id=offer.giver_entity_id, contact_id=offer.contact_entity_id)
+    # TICKET-0114 (F1): an `event` leaf may count since the quest's acceptance.
+    return Bindings(doer=character, giver_id=offer.giver_entity_id, contact_id=offer.contact_entity_id,
+                    quest_since=quest.accepted_at)
 
 
 def evaluate_agenda_step(agenda_step: AgendaStep, character: Character, db: Session) -> EvaluatedStep:
@@ -148,7 +153,7 @@ def evaluate_agenda_step(agenda_step: AgendaStep, character: Character, db: Sess
         domain=agenda_step.domain,
         prerequisite=read_condition(db, role="prerequisite", agenda_step_id=agenda_step.id),
     )
-    bindings = plan_bindings(agenda_step.agenda_id, character, db)
+    bindings = for_step(plan_bindings(agenda_step.agenda_id, character, db), agenda_step)
     return EvaluatedStep(step=plan_step, verdict=evaluate_requirements(plan_step, bindings, db))
 
 
diff --git a/src/world_engine/day_resolve.py b/src/world_engine/day_resolve.py
index 6c55626..7e7566f 100644
--- a/src/world_engine/day_resolve.py
+++ b/src/world_engine/day_resolve.py
@@ -68,7 +68,7 @@ from sqlmodel import Session, select
 
 from .condition_forms import Verdict as RequirementVerdict
 from .condition_text import known_to, leaf_text
-from .conditions import VerdictNode, leaves
+from .conditions import VerdictNode, known_event_facts, leaves
 from .day_concordance import ConcordanceResult
 from .day_plan import (
     DAY_BUDGET_SLOTS,
@@ -279,6 +279,8 @@ _BLOCKED_DETAIL_FR: dict[str, str] = {
     # TICKET-0113 (BRIEF-0113-B, WG1): `attribute` replaces `vital_status`;
     # its label names the subject, the attribute and the wanted state.
     "attribute": "« {required} » n'est pas encore le cas",
+    # TICKET-0114 (BRIEF-0114-E, G1): its label names the type and the count.
+    "event": "il n'a pas encore vécu assez de « {required} »",
 }
 
 
@@ -321,7 +323,7 @@ def blocked_details_fr(verdict: Optional[VerdictNode], db: Session, viewer_id: s
     if verdict is None or verdict.met:
         return []
     details: list[str] = []
-    _blocked(verdict.seen_by(viewer_id), db, viewer_id, False, details)
+    _blocked(verdict.seen_by(viewer_id, known_event_facts(db, verdict, viewer_id)), db, viewer_id, False, details)
     return details
 
 
diff --git a/src/world_engine/quest_reads.py b/src/world_engine/quest_reads.py
index 0d9e8ed..ba6775b 100644
--- a/src/world_engine/quest_reads.py
+++ b/src/world_engine/quest_reads.py
@@ -20,9 +20,10 @@ from sqlmodel import Session, select
 from .attributes import AttributeView, world_attributes, world_entity_type_labels
 from .condition_forms import FORM_VALUES
 from .condition_text import VALUE_LABELS_FR, describe, verdict_lines
-from .conditions import evaluate, flat_leaves, node_to_dict, read_condition
+from .conditions import EVENT_FORM, evaluate, flat_leaves, for_step, known_event_facts, node_to_dict, read_condition
 from .day_resolve import blocked_details_fr
 from .day_plan import evaluate_agenda_step, plan_bindings
+from .event_vocab import world_event_types, world_sortes
 from .models import (
     BASE_SKILL_DOMAINS,
     Agenda,
@@ -54,9 +55,14 @@ QUEST_STATE_LABELS: dict[str, str] = {
 
 
 def _requirement_dict(req) -> dict:
-    return {"type": req.type, "target_entity_id": req.target_entity_id, "target_key": req.target_key,
-            "threshold": req.threshold, "subject_role": req.subject_role,
-            "subject_entity_id": req.subject_entity_id, "value": req.value}
+    out = {"type": req.type, "target_entity_id": req.target_entity_id, "target_key": req.target_key,
+           "threshold": req.threshold, "subject_role": req.subject_role,
+           "subject_entity_id": req.subject_entity_id, "value": req.value}
+    if req.type == EVENT_FORM:  # TICKET-0114 (BRIEF-0114-E): an `event` leaf's window and filters
+        out["since"] = req.since
+        out["filters"] = [{"role_id": f.role_id, "entity_id": f.entity_id, "sorte_id": f.sorte_id}
+                          for f in req.filters]
+    return out
 
 
 def condition_view(db: Session, tree, unsaved: Optional[dict] = None) -> dict:
@@ -91,6 +97,7 @@ def offer_dict(offer: QuestOffer, db: Session) -> dict:
             "objective": step.objective, "cost": step.cost, "domain": step.domain,
             "prerequisite": condition_view(db, read_condition(db, role="prerequisite", quest_offer_step_id=step.id)),
             "completion": condition_view(db, read_condition(db, role="completion", quest_offer_step_id=step.id)),
+            "failure": condition_view(db, read_condition(db, role="failure", quest_offer_step_id=step.id)),
         } for step in steps],
         # TICKET-0109 (B1, C1): the costs and rewards, and their indicative value.
         "terms": [term_dict(db, t, offer.giver_entity_id) for t in terms],
@@ -160,6 +167,13 @@ def editor_choices(world_id: str, db: Session) -> dict:
         "entities": sorted(({"id": e.id, "name": e.name, "type": e.type} for e in db.exec(select(Entity).where(
             Entity.world_id == world_id, Entity.status == "active")).all()),
             key=lambda d: (d["name"].lower(), d["id"])),
+        # TICKET-0114 (BRIEF-0114-E): the event types an `event` leaf may
+        # count, with their active roles, and the sortes a filter may name.
+        "event_types": [{"id": v.id, "name": v.name, "counts_quantity": v.counts_quantity,
+                         "roles": [{"id": r.id, "name": r.name, "entity_types": list(r.entity_types),
+                                    "accepts_sorte": r.accepts_sorte} for r in v.active_roles()]}
+                        for v in world_event_types(db, world_id)],
+        "sortes": [{"id": s.id, "name": s.name} for s in world_sortes(db, world_id)],
     }
 
 
@@ -196,12 +210,20 @@ def _steps_view(agenda: Agenda, character: Character, db: Session) -> list[dict]
         if step.status == "active":
             evaluated = evaluate_agenda_step(step, character, db)
             blocked = blocked_details_fr(evaluated.verdict, db, character.id)
-        completion = evaluate(read_condition(db, role="completion", agenda_step_id=step.id), bindings, db)
-        seen = completion.seen_by(character.id) if completion is not None else None
+        step_bindings = for_step(bindings, step)
+        completion = evaluate(read_condition(db, role="completion", agenda_step_id=step.id), step_bindings, db)
+        seen = completion.seen_by(character.id, known_event_facts(db, completion, character.id)) \
+            if completion is not None else None
+        # TICKET-0114 (H1): when the step has failed -- shown, never acting.
+        failure = evaluate(read_condition(db, role="failure", agenda_step_id=step.id), step_bindings, db)
+        failed = failure.seen_by(character.id, known_event_facts(db, failure, character.id)) \
+            if failure is not None else None
         view.append({"order": step.step_order, "objective": step.objective, "status": step.status,
                      "outcome": step.outcome, "blocked": blocked,
                      "completion": verdict_lines(db, completion, character.id),
-                     "completion_met": seen.met if seen is not None else None})
+                     "completion_met": seen.met if seen is not None else None,
+                     "failure": verdict_lines(db, failure, character.id),
+                     "failure_met": failed.met if failed is not None else None})
     return view
 
 
diff --git a/src/world_engine/writes/conditions.py b/src/world_engine/writes/conditions.py
index 6d7e645..017ff6c 100644
--- a/src/world_engine/writes/conditions.py
+++ b/src/world_engine/writes/conditions.py
@@ -34,15 +34,20 @@ from ..condition_forms import (
     FORM_VALUES,
     REQUIREMENT_TYPES,
     THRESHOLD_TYPES,
+    EventFilter,
     RequirementSpec,
 )
-from ..conditions import SUBJECT_ROLES, ConditionTree, check_shape, owner_of, stored_condition
+from ..conditions import SUBJECT_ROLES, ConditionTree, check_shape, leaves, owner_of, stored_condition
+from ..event_vocab import EVENT_FORM, role_accepts, type_view
 from ..models import (
     BASE_SKILL_DOMAINS,
     CONDITION_ROLES,
+    CONDITION_WINDOWS,
     Condition,
     ConditionNode,
+    ConditionNodeFilter,
     Entity,
+    EventSorte,
     Fact,
     QuestOffer,
     SkillDefinition,
@@ -167,6 +172,62 @@ def _clean_attribute(db: Session, world_id: str, where: str, req: RequirementSpe
     )
 
 
+def _clean_filter(db: Session, world_id: str, where: str, view, f: EventFilter) -> EventFilter:
+    role = view.role(f.role_id)
+    if role is None or role.status != "active":
+        raise ValueError(f"{where}{f.role_id!r} is no role of « {view.name} »")
+    if (f.entity_id is None) == (f.sorte_id is None):
+        raise ValueError(f"{where}the filter on « {role.name} » names an entity or a sorte, exactly one")
+    if f.sorte_id is not None:
+        sorte = db.get(EventSorte, f.sorte_id)
+        if sorte is None or sorte.world_id != world_id or not role.accepts_sorte:
+            raise ValueError(f"{where}the role « {role.name} » takes no sorte {f.sorte_id!r}")
+        return EventFilter(role.id, sorte_id=sorte.id)
+    entity = db.get(Entity, f.entity_id)
+    if entity is None or entity.world_id != world_id or not role_accepts(role, entity.type):
+        raise ValueError(f"{where}the role « {role.name} » takes no {f.entity_id!r}")
+    return EventFilter(role.id, entity_id=entity.id)
+
+
+def _clean_event(db: Session, world_id: str, where: str, req: RequirementSpec) -> RequirementSpec:
+    """An `event` leaf (TICKET-0114, G1, F1): `target_key` an active event
+    type of the world; `value` the subject's role (an active role of it) or
+    None for any; a fixed subject of a type that role accepts; `threshold`
+    how many (1 or more, 1 when unsaid); `since` one of
+    `CONDITION_WINDOWS` (`always` when unsaid); `target_entity_id` a
+    location of the world or none; each filter one other active role,
+    filled by an entity it accepts or a sorte, never twice the same role."""
+    view = type_view(db, req.target_key)
+    if view is None or view.world_id != world_id or view.status != "active":
+        raise ValueError(f"{where}unknown event type {req.target_key!r}")
+    role = view.role(req.value) if req.value else None
+    if req.value and (role is None or role.status != "active"):
+        raise ValueError(f"{where}{req.value!r} is no role of « {view.name} »")
+    if role is not None and req.subject_entity_id is not None and not role_accepts(
+            role, db.get(Entity, req.subject_entity_id).type):
+        raise ValueError(f"{where}the role « {role.name} » takes no {req.subject_entity_id!r}")
+    threshold = 1 if req.threshold is None else req.threshold
+    if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 1:
+        raise ValueError(f"{where}an event leaf counts 1 or more, got {req.threshold!r}")
+    since = req.since or "always"
+    if since not in CONDITION_WINDOWS:
+        raise ValueError(f"{where}unknown window {req.since!r}")
+    place = req.target_entity_id
+    if place is not None:
+        entity = db.get(Entity, place)
+        if entity is None or entity.world_id != world_id or entity.type != "location":
+            raise ValueError(f"{where}{place!r} is not a location of this world")
+    filters = tuple(_clean_filter(db, world_id, where, view, f) for f in req.filters)
+    roles = [f.role_id for f in filters] + ([role.id] if role else [])
+    if len(set(roles)) != len(roles):
+        raise ValueError(f"{where}a role of « {view.name} » is named twice")
+    return RequirementSpec(
+        type=req.type, subject_role=req.subject_role, subject_entity_id=req.subject_entity_id,
+        target_entity_id=place, target_key=view.id, threshold=threshold, value=role.id if role else None,
+        since=since, filters=filters,
+    )
+
+
 def clean_leaf(db: Session, world_id: str, req: RequirementSpec, where: str = "",
                unsaved: Optional[dict] = None) -> RequirementSpec:
     """One leaf as it will be stored: the arguments its form uses, nothing
@@ -177,6 +238,8 @@ def clean_leaf(db: Session, world_id: str, req: RequirementSpec, where: str = ""
     _clean_subject(db, world_id, where, req)
     if req.type == ATTRIBUTE_FORM:
         return _clean_attribute(db, world_id, where, req, unsaved)
+    if req.type == EVENT_FORM:
+        return _clean_event(db, world_id, where, req)
     target_entity_id, target_key = _clean_target(db, world_id, where, req)
     return RequirementSpec(
         type=req.type, subject_role=req.subject_role, subject_entity_id=req.subject_entity_id,
@@ -216,8 +279,12 @@ def write_condition(db: Session, *, world_id: str, role: str, tree: Optional[Con
     if role not in CONDITION_ROLES or (column == "quest_offer_id") != (role == "eligibility"):
         raise ValueError(f"a {column} owner cannot hold a {role!r} condition")
     clean = clean_condition(db, world_id, tree)
+    if role == "eligibility" and any(leaf.since in ("quest", "step") for leaf in leaves(clean)):
+        raise ValueError("an eligibility counts no event since a quest or a step: none is taken yet")
     previous = stored_condition(db, role, column, owner_id)
     if previous is not None:
+        db.execute(text("DELETE FROM condition_node_filter WHERE node_id IN "
+                        "(SELECT id FROM condition_node WHERE condition_id = :cid)"), {"cid": previous.id})
         db.execute(text("DELETE FROM condition_node WHERE condition_id = :cid"), {"cid": previous.id})
         db.execute(text("DELETE FROM condition WHERE id = :cid"), {"cid": previous.id})
         db.expunge(previous)
@@ -243,9 +310,13 @@ def _write_node(db: Session, world_id: str, condition_id: str, tree: ConditionTr
         target_key=spec.target_key if spec else None,
         threshold=spec.threshold if spec else None,
         value=spec.value if spec else None,
+        since=spec.since if spec else None,
     )
     db.add(row)
     db.flush()
+    for index, f in enumerate(spec.filters if spec else ()):
+        db.add(ConditionNodeFilter(world_id=world_id, node_id=row.id, role_id=f.role_id, entity_id=f.entity_id,
+                                   sorte_id=f.sorte_id, position=index))
     for index, child in enumerate(tree.children):
         _write_node(db, world_id, condition_id, child, row.id, index)
 
@@ -256,5 +327,7 @@ def delete_offer_conditions(db: Session, offer_id: str) -> None:
     shape, TICKET-0108)."""
     owned = ("SELECT id FROM condition WHERE quest_offer_id = :oid OR quest_offer_step_id IN "
              "(SELECT id FROM quest_offer_step WHERE offer_id = :oid)")
+    db.execute(text(f"DELETE FROM condition_node_filter WHERE node_id IN (SELECT id FROM condition_node "
+                    f"WHERE condition_id IN ({owned}))"), {"oid": offer_id})
     db.execute(text(f"DELETE FROM condition_node WHERE condition_id IN ({owned})"), {"oid": offer_id})
     db.execute(text(f"DELETE FROM condition WHERE id IN ({owned})"), {"oid": offer_id})
diff --git a/src/world_engine/writes/goals_agendas.py b/src/world_engine/writes/goals_agendas.py
index e660d35..1c959ee 100644
--- a/src/world_engine/writes/goals_agendas.py
+++ b/src/world_engine/writes/goals_agendas.py
@@ -316,6 +316,8 @@ def write_agenda_step(
         cost=cost,
         domain=domain,
         change_history=[],
+        # TICKET-0114 (BRIEF-0114-E, F1): when it became active.
+        started_at=datetime.now(UTC) if status == "active" else None,
     )
     db.add(step)
     return step
@@ -355,6 +357,8 @@ def write_agenda_step_status(
     history.append(entry)
     step.change_history = history
     sa_attrs.flag_modified(step, "change_history")
+    if status == "active" and step.status != "active":
+        step.started_at = datetime.now(UTC)  # TICKET-0114 (BRIEF-0114-E, F1)
     step.status = status
     if outcome is not None:
         step.outcome = outcome
diff --git a/src/world_engine/writes/quests.py b/src/world_engine/writes/quests.py
index 0c2f221..12383cf 100644
--- a/src/world_engine/writes/quests.py
+++ b/src/world_engine/writes/quests.py
@@ -55,10 +55,10 @@ QUEST_GIVER_TYPES: tuple[str, ...] = ("character", "faction")
 OPEN_QUEST_STATUSES: tuple[str, ...] = ("active", "paused")
 
 
-def _clean_offer_steps(db: Session, world_id: str, steps: list[PlanStep]) -> list[tuple[PlanStep, object, object]]:
+def _clean_offer_steps(db: Session, world_id: str, steps: list[PlanStep]) -> list[tuple]:
     if not 1 <= len(steps) <= MAX_PLAN_STEPS:
         raise ValueError(f"write_quest_offer: an offer has 1 to {MAX_PLAN_STEPS} steps, got {len(steps)}")
-    clean: list[tuple[PlanStep, object, object]] = []
+    clean: list[tuple] = []
     for index, step in enumerate(steps):
         if not isinstance(step.objective, str) or not step.objective.strip():
             raise ValueError(f"write_quest_offer: step {index} needs an objective")
@@ -68,7 +68,8 @@ def _clean_offer_steps(db: Session, world_id: str, steps: list[PlanStep]) -> lis
             raise ValueError(f"write_quest_offer: step {index} has invalid domain {step.domain!r}")
         where = f"write_quest_offer: step {index}: "
         clean.append((step, clean_condition(db, world_id, step.prerequisite, where),
-                      clean_condition(db, world_id, step.completion, where)))
+                      clean_condition(db, world_id, step.completion, where),
+                      clean_condition(db, world_id, step.failure, where)))
     return clean
 
 
@@ -131,8 +132,8 @@ def write_quest_offer(
         raise ValueError(f"write_quest_offer: status must be one of {QUEST_OFFER_STATUSES}, got {status!r}")
     _check_giver(db, world_id, giver_entity_id)
     _check_contact(db, world_id, giver_entity_id, contact_entity_id or None)
-    every = list(leaves(eligibility)) + [req for step in steps
-                                         for req in leaves(step.prerequisite) + leaves(step.completion)]
+    every = list(leaves(eligibility)) + [req for step in steps for req in leaves(step.prerequisite)
+                                         + leaves(step.completion) + leaves(step.failure)]
     if offer is not None and any(r.type == "quest_state" and r.target_key == offer.id for r in every):
         raise ValueError("write_quest_offer: an offer cannot require its own state")
     clean_eligibility = clean_condition(db, world_id, eligibility, "write_quest_offer: eligibility: ")
@@ -158,13 +159,14 @@ def write_quest_offer(
     db.flush()
 
     write_condition(db, world_id=world_id, role="eligibility", tree=clean_eligibility, quest_offer_id=offer.id)
-    for order, (step, prerequisite, completion) in enumerate(clean_steps, start=1):
+    for order, (step, prerequisite, completion, failure) in enumerate(clean_steps, start=1):
         row = QuestOfferStep(world_id=world_id, offer_id=offer.id, step_order=order,
                              objective=step.objective.strip(), cost=step.cost, domain=step.domain)
         db.add(row)
         db.flush()
         write_condition(db, world_id=world_id, role="prerequisite", tree=prerequisite, quest_offer_step_id=row.id)
         write_condition(db, world_id=world_id, role="completion", tree=completion, quest_offer_step_id=row.id)
+        write_condition(db, world_id=world_id, role="failure", tree=failure, quest_offer_step_id=row.id)
     write_offer_terms(db, world_id=world_id, offer_id=offer.id, clean=clean_term_rows)
     return offer
 
@@ -210,7 +212,7 @@ def accept_quest(db: Session, *, offer: QuestOffer, character: Character) -> Que
     if not steps:
         raise ValueError("accept_quest: the offer has no step")
     copied = [(step, {role: read_condition(db, role=role, quest_offer_step_id=step.id)
-                      for role in ("prerequisite", "completion")}) for step in steps]
+                      for role in ("prerequisite", "completion", "failure")}) for step in steps]
 
     agenda = write_agenda(db, world_id=offer.world_id, owner_entity_id=character.id, title=offer.title,
                           status="paused")
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index def2460..49c32ce 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19375,6 +19375,42 @@ and refuses when a link has no participant twin.
 the MJ would not remember that the player killed the wolf), L2 (keep the
 columns dormant).
 
+## A CONDITION COUNTS THE EVENTS ITS SUBJECT LIVED, AND A QUEST STEP SAYS WHEN IT HAS FAILED (TICKET-0114) -- THE `event` FORM AND THE `failure` ROLE (BRIEF-0114-e, no schema change)
+
+**G1.** One form, `event`: the events of one type (`target_key`) its
+subject took part in -- in one role (`value`) or any --, each filter's
+other role filled by an entity or a sorte (`condition_node_filter`, several
+per leaf), at a place or anywhere under it (`target_entity_id`, the
+parent chain), added up by quantity (an event without one counts 1) and
+met at `threshold` (1 by default). Its subject may be any entity: a
+faction takes part too. Code counts; the model never does.
+
+**F1.** A leaf counts `always`, since its quest's acceptance (`quest`) or
+since its step began (`step`: `agenda_step.started_at`, set when a step
+becomes active, its quest's acceptance for a step activated before
+v2.24). An eligibility has no quest yet: a `quest` or `step` window is
+refused there; judged without one, the leaf is `unknown`.
+
+**V1 for events.** A player surface recounts an event leaf from the events
+whose fact the character knows (`known_event_facts`, the 0105 resolver):
+what he never learned neither counts nor shows -- Brakk's secret hunt is
+met for the canon and « 0 » for Mira. Unlike other leaves, an event leaf
+about someone else is still recounted: the events are facts he may know.
+
+**H1.** A quest step may carry a `failure` condition, written with the
+offer and copied on acceptance like the others. Journée shows it, marked
+like the completion, and flags it when met; nothing acts on it -- the
+creator decides, as for completion. Only `quest_reads.py` and
+`writes/quests.py` read or write one (`event_conditions.py` EE5).
+
+**Editor.** The offer editor edits an event leaf in the list (type, role or
+any, count, place, window, filters on the type's other roles) and every
+step has a « Échouée quand » editor. A non-event leaf's dict is unchanged:
+`since` and `filters` appear on an event leaf only.
+
+**Rejected.** A window on every form (only events have dates), a failure
+that closes the quest by itself (the creator stays the judge, as M1).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index d736dc1..e7b545e 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -56,10 +56,10 @@ src/world_engine/writes/items.py::write_holding                item_holding
 src/world_engine/writes/quests.py::write_quest_offer           quest_offer quest_offer_step
 # TICKET-0108, BRIEF-0108-B: accept_quest writes the quest row; its agenda and steps go through write_agenda/write_agenda_step, allow-listed above, and since TICKET-0111 its steps' conditions through write_condition.
 src/world_engine/writes/quests.py::accept_quest                quest
-# TICKET-0111, BRIEF-0111-C: the condition language's one writer -- write_condition replaces one owner's condition whole (the full-replace shape), _write_node writes its nodes, delete_offer_conditions clears an offer's before write_quest_offer replaces them. Every caller (write_day_plan, write_quest_offer, accept_quest) calls them, never the tables.
-src/world_engine/writes/conditions.py::write_condition         condition condition_node
-src/world_engine/writes/conditions.py::_write_node             condition_node
-src/world_engine/writes/conditions.py::delete_offer_conditions condition condition_node
+# TICKET-0111, BRIEF-0111-C: the condition language's one writer (TICKET-0114, BRIEF-0114-E: and of an event leaf's condition_node_filter rows) -- write_condition replaces one owner's condition whole (the full-replace shape), _write_node writes its nodes, delete_offer_conditions clears an offer's before write_quest_offer replaces them. Every caller (write_day_plan, write_quest_offer, accept_quest) calls them, never the tables.
+src/world_engine/writes/conditions.py::write_condition         condition condition_node condition_node_filter
+src/world_engine/writes/conditions.py::_write_node             condition_node condition_node_filter
+src/world_engine/writes/conditions.py::delete_offer_conditions condition condition_node condition_node_filter
 # TICKET-0109, BRIEF-0109-B: write_offer_terms replaces an offer's costs and rewards whole (write_quest_offer's full-replace shape); copy_terms_to_quest gives an accepted quest its own copy; upsert_quest_economy sets a world's rates (curated config, upsert-one).
 src/world_engine/writes/quest_terms.py::write_offer_terms      quest_offer_term
 src/world_engine/writes/quest_terms.py::copy_terms_to_quest    quest_term
diff --git a/tooling/verify/checks/attribute_interpreter.py b/tooling/verify/checks/attribute_interpreter.py
index c9c17d6..42ff486 100644
--- a/tooling/verify/checks/attribute_interpreter.py
+++ b/tooling/verify/checks/attribute_interpreter.py
@@ -438,8 +438,9 @@ def check_ae1() -> None:
         for needle in wanted:
             if needle not in text:
                 fail(f"AE1: {name} lacks {needle}")
-    if (front / "QuestOffers.svelte").read_text(encoding="utf-8").count("unsaved={draft.unsavedAttributes}") != 3:
-        fail("AE1: QuestOffers.svelte does not pass the unsaved attributes to its three conditions")
+    if (front / "QuestOffers.svelte").read_text(encoding="utf-8").count("unsaved={draft.unsavedAttributes}") != 4:
+        # TICKET-0114 (BRIEF-0114-E, H1): a step's failure is the fourth.
+        fail("AE1: QuestOffers.svelte does not pass the unsaved attributes to its four conditions")
 
 
 # --- AE2 -------------------------------------------------------------------------
diff --git a/tooling/verify/checks/day_plan.py b/tooling/verify/checks/day_plan.py
index 88ccc5e..0a1f9fb 100644
--- a/tooling/verify/checks/day_plan.py
+++ b/tooling/verify/checks/day_plan.py
@@ -206,8 +206,8 @@ EXPECTED_REQUIREMENT_TYPES = (
     "has_debt_to", "no_debt_to",
     # TICKET-0111 (BRIEF-0111-C, S1): twelve since v2.20; `quest_state`
     # replaced `quest_completed`. TICKET-0113 (BRIEF-0113-B, WG1): `attribute`
-    # replaced `vital_status` at v2.23.
-    "item_held", "attribute",
+    # replaced `vital_status` at v2.23. TICKET-0114 (BRIEF-0114-E, G1): `event`.
+    "item_held", "attribute", "event",
 )
 EXPECTED_RECONCILE_VERDICTS = ("continue", "modify", "replace")
 EXPECTED_PLAN_ACTIONS = ("continue", "modify", "replace", "resume")
@@ -386,7 +386,7 @@ def check_shape_constraint() -> None:
         ("item_held", "ENTITY_TARGET_TYPES"),
         ("knowledge", "KEY_TARGET_TYPES"), ("resource", "KEY_TARGET_TYPES"),
         ("skill_rank_gte", "KEY_TARGET_TYPES"), ("quest_state", "KEY_TARGET_TYPES"),
-        ("attribute", "KEY_TARGET_TYPES"),
+        ("attribute", "KEY_TARGET_TYPES"), ("event", "KEY_TARGET_TYPES"),
         ("relation_gte", "THRESHOLD_TYPES"), ("resource", "THRESHOLD_TYPES"),
         ("skill_rank_gte", "THRESHOLD_TYPES"), ("item_held", "THRESHOLD_TYPES"),
     ]
diff --git a/tooling/verify/checks/event_conditions.py b/tooling/verify/checks/event_conditions.py
new file mode 100644
index 0000000..1bf12f4
--- /dev/null
+++ b/tooling/verify/checks/event_conditions.py
@@ -0,0 +1,392 @@
+"""G1 check for TICKET-0114 -- a condition counts the events its subject lived, and a quest step says when it has failed.
+
+BRIEF-0114-E's rules.
+
+EE1 -- vocabulary and mirrors (static and import). `event` is in
+   `REQUIREMENT_TYPES`, `KEY_TARGET_TYPES`, `THRESHOLD_TYPES` and
+   `ANY_SUBJECT_TYPES`, never in `MODEL_REQUIREMENT_TYPES`;
+   `conditions.EVENT_FORM` equals `event_vocab.EVENT_FORM`; the
+   interpreter's `TARGET_HINTS_FR` and `condition_text.FORM_PHRASES_FR`
+   have an `event` line; `SINCE_LABELS_FR` and the editor's
+   `EVENT_WINDOWS` (`frontend/src/creation/questRequirements.js`) each hold
+   exactly `models.CONDITION_WINDOWS`; `CONDITION_ROLES` holds `failure`.
+EE2 -- the writer (fixture). `clean_leaf` keeps an `event` leaf with its
+   type, its role, 1 when no count is said and `always` when no window is,
+   and refuses: an unknown type, a role of another type, a role that does
+   not take the fixed subject's type, a place that is no location, a
+   filter's role named twice, a sorte on a role that takes none, an
+   unknown window. `write_condition` then `read_condition` give back its
+   window and its filters; an eligibility with a `quest` window is refused.
+EE3 -- counting (fixture). Mira hunted three wolves in the Clairière (under
+   the Forêt), two in the Ville, four bears in the Forêt; Brakk seven
+   wolves, secretly; Mira fought one duel. « Chasse, chasseur, proie =
+   loup » counts 5 for Mira (5 met, 6 not), 3 at the Forêt (its Clairière
+   counts), 9 with any role and no filter, 7 for Brakk; a `Duel` with no
+   quantity counts 1. Since the quest (accepted between the first two
+   hunts) it counts 6; since the step (started after the second) 4; a
+   step never started counts from the quest; with no quest, a `quest`
+   window is `unknown`.
+EE4 -- what a player sees (fixture). The leaf « Brakk a chassé un loup »
+   is met for the canon and unmet for Mira, who never learned it, counting
+   0; Mira's own hunts recount to 5 from the facts she knows
+   (`known_event_facts`); with no known facts the leaf is `unknown`.
+EE5 -- failure and step start (fixture and static). An offer step's
+   `failure` condition is written, copied on acceptance to the agenda step,
+   whose `started_at` is set; activating a pending step sets its own;
+   `quest_reads.player_quests` shows the failure lines and `failure_met`.
+   Only `quest_reads.py` and `writes/quests.py` read or write a `failure`
+   condition -- nothing acts on it.
+EE6 -- the editor (static). `REQUIREMENT_FORMS.event` lists `eventTypes`;
+   `QuestRequirementRow.svelte` edits the role, the place, the window and
+   the filters; `QuestOffers.svelte` has a `failure` editor;
+   `questOffers.svelte.js` sends `failure` and `failure_draft_id`;
+   Journée's `QuestPanel.svelte` shows `failure_met`; the editor's choices
+   carry `event_types` and `sortes`.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import os
+import pathlib
+import re
+import sys
+import tempfile
+from datetime import UTC, datetime, timedelta
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+FRONT = ROOT / "frontend" / "src"
+
+FAILURES: list[str] = []
+NOW = datetime.now(UTC)
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
+def _read(path: pathlib.Path) -> str:
+    try:
+        return path.read_text(encoding="utf-8")
+    except OSError as exc:
+        fail(f"cannot read {path}: {exc}")
+        return ""
+
+
+# --- EE1 -----------------------------------------------------------------------
+
+def check_ee1() -> None:
+    from world_engine import condition_forms, condition_interpreter, condition_text, conditions, event_vocab
+    from world_engine.models import CONDITION_ROLES, CONDITION_WINDOWS
+
+    for group in ("REQUIREMENT_TYPES", "KEY_TARGET_TYPES", "THRESHOLD_TYPES", "ANY_SUBJECT_TYPES"):
+        if "event" not in getattr(condition_forms, group):
+            fail(f"EE1: `event` is not in {group}")
+    if "event" in condition_forms.MODEL_REQUIREMENT_TYPES:
+        fail("EE1: the model's day plan may emit `event`")
+    if conditions.EVENT_FORM != event_vocab.EVENT_FORM or conditions.EVENT_FORM != "event":
+        fail(f"EE1: EVENT_FORM is {conditions.EVENT_FORM!r} / {event_vocab.EVENT_FORM!r}")
+    if "event" not in condition_interpreter.TARGET_HINTS_FR or "event" not in condition_text.FORM_PHRASES_FR:
+        fail("EE1: the interpreter's hints or the French phrases have no `event` line")
+    if tuple(condition_text.SINCE_LABELS_FR) != tuple(CONDITION_WINDOWS):
+        fail(f"EE1: SINCE_LABELS_FR is {tuple(condition_text.SINCE_LABELS_FR)}, windows {CONDITION_WINDOWS}")
+    js = _read(FRONT / "creation" / "questRequirements.js")
+    block = re.search(r"export const EVENT_WINDOWS = \{(.*?)\};", js, re.S)
+    keys = tuple(re.findall(r"^\s*(\w+):", block.group(1), re.M)) if block else ()
+    if keys != tuple(CONDITION_WINDOWS):
+        fail(f"EE1: the editor's EVENT_WINDOWS are {keys}, windows {CONDITION_WINDOWS}")
+    if "failure" not in CONDITION_ROLES:
+        fail(f"EE1: CONDITION_ROLES is {CONDITION_ROLES}")
+
+
+# --- fixture -------------------------------------------------------------------
+
+def _fixture(engine) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.event_vocab import type_view
+    from world_engine.models import Character, Entity, Location, World
+    from world_engine.writes.event_types import EventTypeSpec, RoleSpec, write_event_type, write_sorte
+    from world_engine.writes.events import EventScopeSpec, EventSpec, ParticipantSpec, write_event
+
+    with Session(engine) as db:
+        world = World(name="Chasses", is_active=True)
+        db.add(world)
+        db.flush()
+        ids = {"world": world.id}
+        for key, kind, name in (("foret", "location", "Forêt"), ("clairiere", "location", "Clairière"),
+                                ("ville", "location", "Ville"), ("mira", "character", "Mira"),
+                                ("brakk", "character", "Brakk"), ("odo", "character", "Odo")):
+            entity = Entity(world_id=world.id, type=kind, name=name)
+            db.add(entity)
+            db.flush()
+            ids[key] = entity.id
+        db.add(Location(id=ids["foret"]))
+        db.add(Location(id=ids["ville"]))
+        db.flush()
+        db.add(Location(id=ids["clairiere"], parent_location_id=ids["foret"]))
+        for key in ("mira", "brakk", "odo"):
+            db.add(Character(id=ids[key], world_id=world.id, character_type="player" if key == "mira" else "npc",
+                             current_location_id=ids["ville"]))
+        ids["loup"] = write_sorte(db, world_id=world.id, name="Loup").id
+        ids["ours"] = write_sorte(db, world_id=world.id, name="Ours").id
+        chasse = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
+            name="Chasse", counts_quantity=True,
+            roles=(RoleSpec("Chasseur", ("character",)), RoleSpec("Proie", ("character",), accepts_sorte=True))))
+        duel = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
+            name="Duel", roles=(RoleSpec("Adversaire", ("character",)),)))
+        autre = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
+            name="Fête", roles=(RoleSpec("Invité", ("location",)),)))
+        ids.update(chasse=chasse.id, duel=duel.id, fete=autre.id)
+        view = type_view(db, chasse.id)
+        ids["chasseur"], ids["proie"] = view.roles[0].id, view.roles[1].id
+        ids["adversaire"] = type_view(db, duel.id).roles[0].id
+        ids["invite"] = type_view(db, autre.id).roles[0].id
+        hunts = (
+            ("mira", "loup", 3, "clairiere", 10), ("mira", "loup", 2, "ville", 5), ("mira", "ours", 4, "foret", 1),
+            ("brakk", "loup", 7, "foret", 3),
+        )
+        for who, prey, qty, place, hours in hunts:
+            event = write_event(db, world_id=world.id, created_by="check", spec=EventSpec(
+                type_id=chasse.id, title=f"{who} chasse", quantity=qty, location_id=ids[place], scopes=(),
+                participants=(ParticipantSpec(ids["chasseur"], entity_id=ids[who], secret=who == "brakk"),
+                              ParticipantSpec(ids["proie"], sorte_id=ids[prey]))))
+            event.recorded_at = NOW - timedelta(hours=hours)
+            db.add(event)
+        write_event(db, world_id=world.id, created_by="check", spec=EventSpec(
+            type_id=duel.id, title="Un duel", scopes=(),
+            participants=(ParticipantSpec(ids["adversaire"], entity_id=ids["mira"]),)))
+        db.commit()
+    return ids
+
+
+def _leaf(ids: dict, **kw):
+    from world_engine.condition_forms import EventFilter, RequirementSpec
+
+    filters = tuple(EventFilter(*f) if isinstance(f, tuple) else f for f in kw.pop("filters", ()))
+    base = dict(type="event", subject_role="doer", subject_entity_id=None, target_entity_id=None,
+                target_key=ids["chasse"], threshold=None, value=ids["chasseur"], since=None, filters=filters)
+    base.update(kw)
+    return RequirementSpec(**base)
+
+
+def _wolf(ids: dict) -> tuple:
+    return ((ids["proie"], None, ids["loup"]),)
+
+
+# --- EE2 -----------------------------------------------------------------------
+
+def check_ee2(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.conditions import ConditionTree, read_condition
+    from world_engine.models import Agenda, AgendaStep, QuestOffer
+    from world_engine.writes.conditions import clean_leaf, write_condition
+
+    with Session(engine) as db:
+        kept = clean_leaf(db, ids["world"], _leaf(ids, filters=_wolf(ids)))
+        if (kept.threshold, kept.since, kept.value, len(kept.filters)) != (1, "always", ids["chasseur"], 1):
+            fail(f"EE2: a plain event leaf is kept as {kept}")
+        refused = {
+            "an unknown type": _leaf(ids, target_key="nope"),
+            "a role of another type": _leaf(ids, value=ids["adversaire"]),
+            "a role that does not take the subject": _leaf(ids, target_key=ids["fete"], value=ids["invite"],
+                                                            subject_role=None, subject_entity_id=ids["mira"]),
+            "a place that is no location": _leaf(ids, target_entity_id=ids["odo"]),
+            "a role named twice": _leaf(ids, filters=((ids["chasseur"], ids["odo"], None),)),
+            "a sorte on a role that takes none": _leaf(ids, value=None, filters=((ids["chasseur"], None,
+                                                                                  ids["loup"]),)),
+            "an unknown window": _leaf(ids, since="forever"),
+        }
+        for what, req in refused.items():
+            try:
+                clean_leaf(db, ids["world"], req)
+                fail(f"EE2: clean_leaf accepts {what}")
+            except ValueError:
+                pass
+        agenda = Agenda(world_id=ids["world"], owner_entity_id=ids["mira"], title="t", status="paused")
+        db.add(agenda)
+        db.flush()
+        step = AgendaStep(agenda_id=agenda.id, step_order=1, objective="o", status="pending")
+        db.add(step)
+        db.flush()
+        tree = ConditionTree(op="leaf", leaf=_leaf(ids, since="step", threshold=2, filters=_wolf(ids)))
+        write_condition(db, world_id=ids["world"], role="completion", tree=tree, agenda_step_id=step.id)
+        back = read_condition(db, role="completion", agenda_step_id=step.id)
+        leaf = back.leaf if back is not None and back.op == "leaf" else (back.children[0].leaf if back else None)
+        if leaf is None or leaf.since != "step" or [(f.role_id, f.sorte_id) for f in leaf.filters] != [
+                (ids["proie"], ids["loup"])]:
+            fail(f"EE2: the stored leaf reads back as {leaf}")
+        offer = QuestOffer(world_id=ids["world"], giver_entity_id=ids["odo"], title="o", change_history=[])
+        db.add(offer)
+        db.flush()
+        try:
+            write_condition(db, world_id=ids["world"], role="eligibility", quest_offer_id=offer.id,
+                            tree=ConditionTree(op="leaf", leaf=_leaf(ids, since="quest")))
+            fail("EE2: an eligibility counting since the quest is accepted")
+        except ValueError:
+            pass
+        db.rollback()
+
+
+# --- EE3 / EE4 -----------------------------------------------------------------
+
+def _judge(db, ids: dict, req, **bind):
+    from world_engine.conditions import Bindings, ConditionTree, evaluate
+    from world_engine.models import Character
+
+    doer = db.get(Character, ids["mira"])
+    return evaluate(ConditionTree(op="leaf", leaf=req), Bindings(doer=doer, giver_id=ids["brakk"], **bind), db)
+
+
+def check_ee3(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    cases = (
+        ("wolves", dict(threshold=5, filters=_wolf(ids)), {}, ("met", 5)),
+        ("six wolves", dict(threshold=6, filters=_wolf(ids)), {}, ("unmet", 5)),
+        ("wolves at the Forêt", dict(threshold=1, filters=_wolf(ids), target_entity_id=ids["foret"]), {},
+         ("met", 3)),
+        ("any role", dict(threshold=1, value=None), {}, ("met", 9)),
+        ("Brakk's wolves", dict(threshold=1, subject_role="giver", filters=_wolf(ids)), {}, ("met", 7)),
+        ("a duel", dict(threshold=1, target_key=ids["duel"], value=None), {}, ("met", 1)),
+        ("since the quest", dict(threshold=1, since="quest"), {"quest_since": NOW - timedelta(hours=6)},
+         ("met", 6)),
+        ("since the step", dict(threshold=1, since="step"),
+         {"quest_since": NOW - timedelta(hours=6), "step_since": NOW - timedelta(hours=2)}, ("met", 4)),
+        ("a step never started", dict(threshold=1, since="step"), {"quest_since": NOW - timedelta(hours=6)},
+         ("met", 6)),
+    )
+    with Session(engine) as db:
+        for what, kw, bind, (state, count) in cases:
+            node = _judge(db, ids, _leaf(ids, **kw), **bind)
+            got = (node.state, node.verdict.current if node.verdict else None)
+            if got != (state, count):
+                fail(f"EE3: {what} judges {got}, not {(state, count)}")
+        node = _judge(db, ids, _leaf(ids, threshold=1, since="quest"))
+        if node.state != "unknown":
+            fail(f"EE3: a `quest` window with no quest judges {node.state}")
+
+
+def check_ee4(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.conditions import known_event_facts
+
+    with Session(engine) as db:
+        brakk = _judge(db, ids, _leaf(ids, threshold=1, subject_role="giver", filters=_wolf(ids)))
+        seen = brakk.seen_by(ids["mira"], known_event_facts(db, brakk, ids["mira"]))
+        if brakk.state != "met" or seen.state != "unmet" or seen.verdict.current != 0:
+            fail(f"EE4: Brakk's secret hunt reads {brakk.state} then {seen.state} for Mira")
+        own = _judge(db, ids, _leaf(ids, threshold=5, filters=_wolf(ids)))
+        mine = own.seen_by(ids["mira"], known_event_facts(db, own, ids["mira"]))
+        if mine.state != "met" or mine.verdict.current != 5:
+            fail(f"EE4: Mira's own hunts recount to {mine.state} {mine.verdict and mine.verdict.current}")
+        if own.seen_by(ids["mira"]).state != "unknown":
+            fail("EE4: with no known facts, an event leaf is not `unknown`")
+
+
+# --- EE5 -----------------------------------------------------------------------
+
+def check_ee5(engine, ids: dict) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.conditions import ConditionTree, node_to_dict, read_condition
+    from world_engine.day_plan import PlanStep
+    from world_engine.models import AgendaStep, Character
+    from world_engine.quest_reads import player_quests
+    from world_engine.writes.goals_agendas import write_agenda_step_status
+    from world_engine.writes.quests import accept_quest, write_quest_offer
+
+    failure = ConditionTree(op="leaf", leaf=_leaf(ids, threshold=1, target_key=ids["duel"], value=None,
+                                                  since="step"))
+    with Session(engine) as db:
+        offer = write_quest_offer(
+            db, world_id=ids["world"], offer=None, giver_entity_id=ids["odo"], title="La chasse",
+            summary=None, repeatable=False, status="open", eligibility=None,
+            steps=[PlanStep("Chasser", 1, None, failure=failure), PlanStep("Rentrer", 1, None)])
+        db.flush()
+        quest = accept_quest(db, offer=offer, character=db.get(Character, ids["mira"]))
+        db.commit()
+        steps = db.exec(select(AgendaStep).where(AgendaStep.agenda_id == quest.agenda_id)
+                        .order_by(AgendaStep.step_order)).all()
+        copied = read_condition(db, role="failure", agenda_step_id=steps[0].id)
+        stored = node_to_dict(copied) if copied is not None else {}
+        stored = stored["children"][0] if "children" in stored else stored
+        if stored.get("since") != "step":
+            fail(f"EE5: the accepted step's failure is {copied}")
+        if steps[0].started_at is None or steps[1].started_at is not None:
+            fail(f"EE5: started_at is {steps[0].started_at} / {steps[1].started_at}")
+        view = player_quests(db.get(Character, ids["mira"]), db)
+        first = view[0]["steps"][0] if view else {}
+        if not first.get("failure") or first.get("failure_met") is not False:
+            fail(f"EE5: Journée shows the failure as {first.get('failure')}, met {first.get('failure_met')}")
+        write_agenda_step_status(db, step=steps[0], status="completed")
+        db.refresh(steps[1])
+        if steps[1].status == "active" and steps[1].started_at is None:
+            fail("EE5: the next step became active without a start")
+        if steps[1].status != "active":
+            write_agenda_step_status(db, step=steps[1], status="active")
+            if steps[1].started_at is None:
+                fail("EE5: activating a pending step leaves started_at empty")
+        db.rollback()
+    readers = sorted(str(p.relative_to(SRC)) for p in SRC.rglob("*.py")
+                     if re.search(r"role=\"failure\"", p.read_text(encoding="utf-8")))
+    if readers != ["quest_reads.py", "writes/quests.py"]:
+        fail(f"EE5: a failure condition is read or written by {readers}")
+
+
+# --- EE6 -----------------------------------------------------------------------
+
+def check_ee6() -> None:
+    wants = {
+        FRONT / "creation" / "questRequirements.js": (
+            "event: { label: 'A vécu l’événement', list: 'eventTypes', column: 'key', threshold: true }",),
+        FRONT / "creation" / "QuestRequirementRow.svelte": ("fillerOptions", "EVENT_WINDOWS", "req.since",
+                                                           "req.filters", "n’importe quel rôle"),
+        FRONT / "creation" / "QuestOffers.svelte": ('role="failure"',),
+        FRONT / "creation" / "questOffers.svelte.js": ("failure: conditionBody(s.failure)", "failure_draft_id"),
+        FRONT / "journee" / "QuestPanel.svelte": ("step.failure_met",),
+        SRC / "quest_reads.py": ('"event_types":', '"sortes":'),
+    }
+    for path, needles in wants.items():
+        text = _read(path)
+        for needle in needles:
+            if needle not in text:
+                fail(f"EE6: {path.name} lacks {needle!r}")
+
+
+def main() -> int:
+    _fresh_db()
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    check_ee1()
+    ids = _fixture(engine)
+    for check in (check_ee2, check_ee3, check_ee4, check_ee5):
+        try:
+            check(engine, ids)
+        except Exception as exc:  # a crash is a failure, never a pass
+            fail(f"{check.__name__}: crashed: {type(exc).__name__}: {exc}")
+    check_ee6()
+    for msg in FAILURES:
+        print(f"FAIL: {msg}")
+    if FAILURES:
+        return 1
+    print("PASS: event_conditions -- a condition counts the events its subject lived, by type, role, place, "
+          "window and filters, summing quantities; a player counts only those he knows; a quest step says "
+          "when it has failed, shown and never acting; the offer editor writes both")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/quests.py b/tooling/verify/checks/quests.py
index 44dd274..2865e04 100644
--- a/tooling/verify/checks/quests.py
+++ b/tooling/verify/checks/quests.py
@@ -11,7 +11,7 @@ QA1 -- vocabulary (BRIEF-0108-A, static and import; since TICKET-0111 the
    (`quest_state` in place of `quest_completed` since v2.20), TICKET-0110's
    two debt forms, TICKET-0111's `item_held` (`conditions.py` owns it) and
    TICKET-0113's `attribute` in place of `vital_status` (`attributes.py`
-   owns it); `MODEL_REQUIREMENT_TYPES` is exactly the model's four;
+   owns it), TICKET-0114's `event` (`event_conditions.py` owns it); `MODEL_REQUIREMENT_TYPES` is exactly the model's four;
    `ENTITY_TARGET_TYPES` and `KEY_TARGET_TYPES` partition it and
    `THRESHOLD_TYPES` is inside it; `day_plan._validate_requirement`
    (the model's parser) accepts each model form and refuses every other.
@@ -110,7 +110,8 @@ DEBT_FORMS = ("has_debt_to", "no_debt_to")
 # TICKET-0111 (BRIEF-0111-C, S1): two more; `conditions.py` owns them.
 # TICKET-0113 (BRIEF-0113-B, WG1): `attribute` replaces `vital_status`;
 # `attributes.py` owns it.
-CONDITION_FORMS = ("item_held", "attribute")
+# TICKET-0114 (BRIEF-0114-E, G1): `event`; `event_conditions.py` owns it.
+CONDITION_FORMS = ("item_held", "attribute", "event")
 # QA2 runs the v2.17 migration: the forms it added, the tables it created.
 V217_FORMS = ("has_met", "faction_member", "skill_rank_gte", "quest_completed")
 QUEST_TABLES = ("quest_offer", "quest_offer_step", "quest_offer_requirement", "quest")
````

2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
4. Run the checks below, then the full corpus.

## Scope OUT

- The interpreter writing an event leaf (F) or proposing a type (G).
- A failure that closes the quest by itself (rejected: the creator stays the judge).
- Time windows by day number (« avant le jour N ») -- TICKET-0120.
- The model's day-plan forms (`MODEL_REQUIREMENT_TYPES`) stay four.
- Every later brief of this lot: BRIEF-0114-F, BRIEF-0114-G, BRIEF-0114-H.

## Invariants to defend

INV-62 and INV-01: a player surface shows an event leaf only as his character may know it -- recounted over the facts he knows, `unknown` without them, an event he never learned neither counted nor named (EE4). INV-08/INV-12: a node's filters are deleted with it, a named full-replace.

## Decision rights

STOP:
- A player surface would show an event count not recounted through `known_event_facts`.
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
- `python tooling/verify/checks/event_conditions.py` -> `PASS`.
- `python tooling/verify/checks/conditions.py` -> `PASS`.
- `python tooling/verify/checks/quests.py` -> `PASS`.
- `python tooling/verify/checks/attribute_conditions.py` -> `PASS`.
- `python tooling/verify/checks/attribute_interpreter.py` -> `PASS`.
- `python tooling/verify/checks/condition_interpreter.py` -> `PASS`.
- `python tooling/verify/checks/day_plan.py` -> `PASS`.
- `python tooling/verify/checks/day_narration.py` -> `PASS`.
- `python tooling/verify/checks/knowledge_identity.py` -> `PASS`.
- `python tooling/verify/checks/frontend_build_fresh.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (154 on the prototype).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **EE1** -- `condition_text.py` `SINCE_LABELS_FR`: drop its `"step"` entry
  - **EE2** -- `writes/conditions.py` `_clean_event`: `if len(set(roles)) != len(roles):` -> `if False:`
  - **EE3** -- `condition_forms.py` `evaluate_event`: `sum(quantity or 1 for …)` -> `sum(1 for …)`; or `counted_events`: `Event.location_id.in_(_places_within(…))` -> `Event.location_id == req.target_entity_id`
  - **EE4** -- `conditions.py` `_seen_event`: `for fact, quantity in verdict.events if fact in known)` -> `for fact, quantity in verdict.events)`
  - **EE5** -- `writes/quests.py` `accept_quest`: `("prerequisite", "completion", "failure")` -> `("prerequisite", "completion")`; or `writes/goals_agendas.py` `write_agenda_step`: `started_at=… if status == "active" else None` -> `started_at=None`
  - **EE6** -- `journee/QuestPanel.svelte`: `{step.failure_met ? 'Échouée — à vous de trancher' : 'Échoue si'}` -> `Échoue si`
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated.
