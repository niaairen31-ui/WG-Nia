<!-- slug: proposed-attributes -->
# BRIEF 0113-E — "The interpreter proposes a state the world lacks -- the definition and the condition confirmed together, a near name picked, both written by the offer's save"

Lot: LOT-0113-world-state.md (authoritative on conflict)
Depends on: BRIEF-0113-D (C-03, C-06, C-07, C-08)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0113-D's commit).

- `src/world_engine/condition_interpreter.py:438` -> `class Interpretation:`
- `src/world_engine/condition_interpreter.py:490` -> `def _settle(db: Session, world_id: str, reading: Reading, notes: list[str], retried: bool) -> Interpretation:`
- `src/world_engine/condition_interpreter.py:504` -> `def interpret(`
- `src/world_engine/cockpit/routes/quests.py:124` -> `def _save_offer(body: OfferBody, offer: Optional[QuestOffer], world_id: str, db: Session) -> dict:`
- `src/world_engine/cockpit/routes/quests.py:145` -> `def _mark_drafts(body: OfferBody, offer_id: str, world_id: str, db: Session) -> None:`
- `src/world_engine/writes/condition_drafts.py:44` -> `PAYLOAD_KEYS: frozenset[str] = frozenset({`
- `src/world_engine/writes/condition_drafts.py:100` -> `def mark_draft_saved(`
- `src/world_engine/writes/conditions.py:166` -> `def clean_leaf(db: Session, world_id: str, req: RequirementSpec, where: str = "") -> RequirementSpec:`
- `scripts/seed_pilot.py:2043` -> `CONDITION_INTERPRET_FRAGMENTS: tuple[tuple[str, str, str], ...] = (`
- `frontend/src/creation/questOffers.svelte.js:119` -> `function draftBody(draft) {`
- No `src/world_engine/attribute_proposals.py` exists.

## Facts carried

### R-08 — the writer's validation [M]
Opened: `src/world_engine/writes/conditions.py:53` (`_TARGET_ENTITY_TYPE`),
`:62` (`_clean_target_key`), `:81-92` (`_clean_subject`: a fixed subject is
a character of the world; a `NO_TARGET_TYPES` form takes no target),
`:127` (`_clean_value`), `:136` (`clean_leaf`), `:151` (`clean_condition`),
`:171` (`write_condition`).
Consequence: `clean_leaf` sends an `attribute` leaf to `_clean_attribute`
(an active attribute of the world, a subject it applies to, a value by
kind); E adds an `unsaved` parameter so a proposal names a definition not
written yet -- `write_condition` passes none.

### R-10 — one nearness rule [M]
Opened: `src/world_engine/lore_resolve.py:50-51` (`NEAR_RATIO = 0.8`,
`NEAR_LIMIT`), `:73` (`normalize_surface`), `:178` (`NearCandidate`),
`:186-` (`near_in_surfaces`: `difflib` ratio or a shared 3+ token, score
rounded half up -- TICKET-0094's Near table).
Consequence: C extracts the rule unchanged as `near_ratio` / `near_score`
(`near_in_surfaces` reads them); `attributes.near_attributes` scores names
with it. « maudite » beside « Maudit » scores 92 [M]. Names are compared
for identity through `normalize_surface` (case and accents aside).

### R-11 — the interpreter and its prompt [M]
Opened: `src/world_engine/condition_interpreter.py:67` (`TARGET_HINTS_FR`),
`:82` (`CODE_LISTS`), `:105` (`InterpreterContext`), `:135`
(`build_context`), `:165` (`encode`), `:254` (`_leaf`), `:350`
(`validate`), `:376` (`Interpretation`), `:407` (`prompt_values`), `:427`
(`_settle`), `:441` (`interpret`), `:466` (`resolve`);
`scripts/seed_pilot.py:132` (`upsert_prompt_template`, S2: a head's text
never touched once a version exists), `:1954`, `:2006`, `:2041`
(`CONDITION_INTERPRET_*`), `:3047` (the seed loop);
`scripts/apply_ticket_0110_link_prompt.py` (the precedent: fragments
applied to the CURRENT version, an edited one kept).
Consequence: `a` joins `CODE_LISTS`; the prompt changes as
`(field, old, new)` fragments over the 0112 text -- the seed derives its
text from them, the delivery script applies them to Nia's current version.

### R-12 — the interpreter's routes, journal and the offer's save [M]
Opened: `src/world_engine/cockpit/routes/conditions.py:51-64` (bodies),
`:79` (`_answer`), `:104` (`interpret`), `:134` (`resolve`), `:151`
(`decision`); `src/world_engine/writes/condition_drafts.py:34`
(`CONDITION_DRAFT_MOVES`), `:44` (`PAYLOAD_KEYS`), `:85`
(`move_condition_draft`), `:100-114` (`mark_draft_saved`,
`saved_as_proposed` compares the saved tree with `payload.proposed`);
`src/world_engine/cockpit/routes/quests.py:53-64` (`OfferStepBody`, draft
ids), `:78-92` (`OfferBody`), `:124-139` (`_save_offer`: parse, write,
`_mark_drafts`, one commit), `:145-156` (`_mark_drafts`).
Consequence: WN2 lands in `_save_offer` -- the proposed definitions a
condition names are written first, in its transaction, the trees rewritten
to their ids; `saved_as_proposed` compares with the proposal rewritten the
same way (`proposed_as_saved`).

## Contracts

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

### C-08 — the interpreter's `a` list, the leaf in the model's form, the prompt
Produced by: BRIEF-0113-D   Consumed by: BRIEF-0113-E
`CODE_LISTS["attribute"] = "a"`; `InterpreterContext.attributes: dict[key,
AttributeView]`; `attribute_line(view, types) -> str` (« name (système ;
choix : l1, l2 ; pour : personnage) »). An `attribute` leaf in the model's
form: `"target": {"code": "a<n>"}`; a choice -> `"value"` one of its
labels (read back case- and accent-blind to its key, or its key itself);
an integer -> `"threshold"`; an entity -> `"value"` a name, an `e` code, or
null (anyone). A label it lacks is an error, retried once (II1), naming
its labels. `encode` writes a stored choice back as its label.
Prompt: variable `attributes` added; `seed_pilot.CONDITION_INTERPRET_FRAGMENTS:
tuple[(field, old, new)]`, `with_condition_fragments(texts)`;
`apply_ticket_0113_condition_prompt.py`: b-5.

### C-09 — a proposed attribute (unsaved)
Produced by: BRIEF-0113-E   Consumed by: BRIEF-0113-E (routes, editor)
Model's answer gains `"define": [{"ref", "name", "kind", "for": [types],
"value_types": [types], "choices": [labels], "default", "hidden"}]`; a leaf
names one by `"target": {"define": "<ref>"}`. Types by key or French name.
`attribute_proposals`: `UNSAVED_PREFIX = "new:"`, `UnsavedAttribute(ref,
spec)`, `unsaved_key`, `is_unsaved`, `unsaved_view(s)`, `spec_dict`,
`spec_from_dict`, `clean_unsaved(db, world_id, raw) -> list` (each by
`clean_definition`; a ref or a name twice refused), `read_definitions`,
`near_existing`, `adopt`, `rewrite`, `materialize`.
Interpreter: `interpret(..., unsaved=())`, `resolve(..., definitions=(),
unsaved=())` (a near proposal picked by its ref: `new` or an existing
key), `confirm(db, world_id, proposed, unsaved, edited)`;
`Interpretation.definitions: [{ref, definition, near}]` (an adopted one
kept, marked `adopted`). `clean_leaf` / `clean_condition` take
`unsaved: dict[key, AttributeView]`; `write_condition` passes none.
`condition_text.describe` / `leaf_text`, `quest_reads.condition_view(db,
tree, unsaved=None)` name an unsaved attribute; `editor_choices` gains
`entity_types`.
Routes: `InterpretBody`, `ResolveBody`, `DecisionBody` gain
`unsaved_attributes: [UnsavedBody]`; `DecisionBody.definitions:
[UnsavedBody]` (on `inserted`, every proposed one, retouched or not,
exactly); the answer gains `definitions`. Statuses: b-6.

### C-10 — the offer's save writes them (WN2)
Produced by: BRIEF-0113-E   Consumed by: the editor
`OfferBody.unsaved_attributes: [UnsavedBody]`. `_save_offer`:
`materialize(db, world_id, raw, trees)` writes every definition a tree
names (sorted by key), in the offer's transaction, before
`write_quest_offer`, and returns the trees rewritten (`new:` keys -> ids,
labels -> choice ids); one no tree names is not written; a tree naming
one the body lacks -> `ValueError` -> 422, nothing written.
`writes.condition_drafts.PAYLOAD_KEYS` gains `definitions`;
`mark_draft_saved(..., proposed_as_saved=None)`: the proposal rewritten
the same way before comparing. Frontend: `questOffers` draft
`unsavedAttributes`, sent as `unsaved_attributes`.

## Context

WK2, in Nia's words: when a state is missing, the interpreter proposes to create it -- she does not leave the interpreter for another tab. The model proposes the definition in its answer's `define` block and the condition names it; code cleans it with the writer's own rules; she reads it as a card, retouches it in the same form as Création › États, and confirms both with « Insérer ». A proposed name near an existing attribute's (or another proposal's) waits for her pick -- use the existing one, or create -- the tool never picks. WN2: until « Enregistrer », the definition lives in the offer draft; the offer's save writes it, in the same transaction and by the same writer, then the conditions rewritten to its id. A definition no condition names any more is not written.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - creates `attribute_proposals.py` (C-09);
   - `condition_interpreter.py`: `Proposals`, `_answer`, `interpret(..., unsaved)`, `resolve(..., definitions, unsaved)` (an adopted one kept, marked `adopted`), `confirm`, `{"define": ref}` targets, the `entity_types` prompt value, `Interpretation.definitions`;
   - `writes/conditions.py`: `clean_leaf` / `clean_condition` take `unsaved` (`write_condition` passes none); `condition_text.py` and `quest_reads.py` name an unsaved attribute; `editor_choices` gains `entity_types`;
   - `writes/condition_drafts.py`: `PAYLOAD_KEYS` gains `definitions`; `mark_draft_saved(..., proposed_as_saved)`;
   - routes: `routes/attributes.py` `UnsavedBody`; `routes/conditions.py` (`unsaved_attributes` on the three bodies, `DecisionBody.definitions`, `_confirmed`, the answer's `definitions`); `routes/quests.py` (`OfferBody.unsaved_attributes`, `_save_offer` materializes first, `_mark_drafts(trees, as_saved)`) (C-10, b-6);
   - `seed_pilot.py`: E's fragments (the state note rewritten, the NOUVEL ÉTAT paragraph, the JSON example's `define`, the `entity_types` block); the head's variables gain `entity_types`;
   - frontend: `questRequirements.js` (`withUnsaved`), `ConditionEditor.svelte`, `QuestOffers.svelte`, `questOffers.svelte.js` (`unsavedAttributes`, sent as `unsaved_attributes`), `conditionInterpreter.svelte.js` (cards, picks, insert with definitions), `ConditionInterpreter.svelte` (the card, the near radios, `AttributeDefinitionForm`), `attributes.svelte.js` (`specDraft`);
   - adds AE1-AE3 to check `attribute_interpreter.py`; `condition_interpreter.py` (check) gets a `_payload` helper and NE1's needles follow;
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - frontend/src/creation/ConditionEditor.svelte
   - frontend/src/creation/ConditionInterpreter.svelte
   - frontend/src/creation/QuestOffers.svelte
   - frontend/src/creation/attributes.svelte.js
   - frontend/src/creation/conditionInterpreter.svelte.js
   - frontend/src/creation/questOffers.svelte.js
   - frontend/src/creation/questRequirements.js
   - scripts/seed_pilot.py
   - src/world_engine/attribute_proposals.py
   - src/world_engine/cockpit/routes/attributes.py
   - src/world_engine/cockpit/routes/conditions.py
   - src/world_engine/cockpit/routes/quests.py
   - src/world_engine/condition_interpreter.py
   - src/world_engine/condition_text.py
   - src/world_engine/quest_reads.py
   - src/world_engine/writes/condition_drafts.py
   - src/world_engine/writes/conditions.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/attribute_interpreter.py
   - tooling/verify/checks/condition_interpreter.py

````diff
diff --git a/frontend/src/creation/ConditionEditor.svelte b/frontend/src/creation/ConditionEditor.svelte
index 4c3acab..d118447 100644
--- a/frontend/src/creation/ConditionEditor.svelte
+++ b/frontend/src/creation/ConditionEditor.svelte
@@ -5,12 +5,17 @@
      unchanged. `cond` is a draft object owned by questOffersState
      (conditionDraft in questRequirements.js). TICKET-0112 (BRIEF-0112-E,
      IB1, T1): both are also written and edited in French, through the
-     interpreter under the condition; `role` is the condition's. */
+     interpreter under the condition; `role` is the condition's.
+     TICKET-0113 (BRIEF-0113-E, WN2): `unsaved`, the offer draft's proposed
+     attributes, is listed with the rows' attributes and goes to the
+     interpreter, which adds the ones the creator confirms. */
   import QuestRequirementRow from './QuestRequirementRow.svelte';
   import ConditionInterpreter from './ConditionInterpreter.svelte';
-  import { blankRequirement } from './questRequirements.js';
+  import { blankRequirement, withUnsaved } from './questRequirements.js';
 
-  let { cond, choices, role, emptyLabel, addLabel } = $props();
+  let { cond, choices, role, emptyLabel, addLabel, unsaved = [] } = $props();
+
+  let rowChoices = $derived(withUnsaved(choices, unsaved));
 
   function clearLocked() {
     cond.locked = null;
@@ -29,11 +34,11 @@
 {:else}
   {#if cond.list.length === 0 && emptyLabel}<p class="muted">{emptyLabel}</p>{/if}
   {#each cond.list as req, i (i)}
-    <QuestRequirementRow {req} {choices} onremove={() => cond.list.splice(i, 1)} />
+    <QuestRequirementRow {req} choices={rowChoices} onremove={() => cond.list.splice(i, 1)} />
   {/each}
   <button onclick={() => cond.list.push(blankRequirement())}>{addLabel}</button>
 {/if}
-<ConditionInterpreter {cond} {role} />
+<ConditionInterpreter {cond} {role} {unsaved} types={choices?.entity_types || []} />
 
 <style>
   .cond-locked { border-left: 2px solid var(--border); padding: 2px 0 4px 8px; margin: 3px 0; }
diff --git a/frontend/src/creation/ConditionInterpreter.svelte b/frontend/src/creation/ConditionInterpreter.svelte
index e74b84f..f6dd68e 100644
--- a/frontend/src/creation/ConditionInterpreter.svelte
+++ b/frontend/src/creation/ConditionInterpreter.svelte
@@ -2,16 +2,21 @@
   /* TICKET-0112 (BRIEF-0112-E, IB1). « Écrire en langage naturel » under one
      condition of the offer editor: a sentence, then the proposal read back
      in French -- inserted into the draft or discarded by the creator. The
-     requests live in conditionInterpreter.svelte.js. */
+     requests live in conditionInterpreter.svelte.js.
+     TICKET-0113 (BRIEF-0113-E, WK2): a state the world lacks comes as a
+     card -- use the near existing one, or create this one, retouched in
+     AttributeDefinitionForm -- confirmed with « Insérer ». */
+  import AttributeDefinitionForm from './AttributeDefinitionForm.svelte';
   import {
     interpreterState, askInterpreter, pickNames, insertProposal, discardProposal,
   } from './conditionInterpreter.svelte.js';
 
-  let { cond, role } = $props();
+  let { cond, role, unsaved = [], types = [] } = $props();
 
   const s = $state(interpreterState());
   let proposal = $derived(s.proposal);
-  let picked = $derived(proposal ? proposal.mentions.every((m) => s.picks[m.ref]) : false);
+  let picked = $derived(proposal
+    ? proposal.mentions.every((m) => s.picks[m.ref]) && s.cards.every((c) => c.pick) : false);
 </script>
 
 {#if !s.open}
@@ -21,7 +26,7 @@
     <textarea rows="2" placeholder="Ex. : le joueur possède 15 fourrures de loup ou est membre de la Guilde"
               bind:value={s.instruction}></textarea>
     <div class="inline">
-      <button disabled={s.busy || !s.instruction.trim()} onclick={() => askInterpreter(s, cond, role)}>
+      <button disabled={s.busy || !s.instruction.trim()} onclick={() => askInterpreter(s, cond, role, unsaved)}>
         {proposal ? 'Reformuler' : 'Proposer'}
       </button>
       <button class="link" onclick={() => { s.open = false; }}>Fermer</button>
@@ -43,14 +48,31 @@
             </select>
           </label>
         {/each}
+        {#each s.cards as card (card.ref)}
+          <div class="card">
+            <strong>État à créer : {card.draft.name}</strong>
+            {#if card.near.length}
+              <div class="muted">Ce nom ressemble à un état existant :</div>
+              {#each card.near as n (n.key)}
+                <label class="pick"><input type="radio" bind:group={card.pick} value={n.key}>
+                  Utiliser « {n.name} »{n.system ? ' (système)' : ''} — {n.score} %</label>
+              {/each}
+              <label class="pick"><input type="radio" bind:group={card.pick} value="new">
+                Créer « {card.draft.name} »</label>
+            {/if}
+            {#if card.pick === 'new'}
+              <AttributeDefinitionForm draft={card.draft} {types} />
+            {/if}
+          </div>
+        {/each}
         {#each proposal.notes as note, i (i)}<p class="muted">{note}</p>{/each}
         {#each proposal.errors as error, i (i)}<p class="err">{error}</p>{/each}
         <div class="inline">
           {#if proposal.outcome === 'needs_choice'}
-            <button disabled={s.busy || !picked} onclick={() => pickNames(s)}>Appliquer les choix</button>
+            <button disabled={s.busy || !picked} onclick={() => pickNames(s, unsaved)}>Appliquer les choix</button>
           {/if}
           {#if proposal.outcome === 'proposed'}
-            <button onclick={() => insertProposal(s, cond)}>Insérer dans l'offre</button>
+            <button onclick={() => insertProposal(s, cond, unsaved)}>Insérer dans l'offre</button>
           {/if}
           <button onclick={() => discardProposal(s)}>Écarter</button>
         </div>
@@ -67,4 +89,6 @@
   .link { background: none; border: none; color: var(--accent, inherit); cursor: pointer; padding: 0; }
   .muted { color: var(--muted); font-size: 12px; }
   .err { color: var(--danger, #c33); font-size: 12px; }
+  .card { border: 1px solid var(--border); border-radius: 6px; padding: 6px 8px; margin: 6px 0; }
+  .pick { display: block; margin: 2px 0; }
 </style>
diff --git a/frontend/src/creation/QuestOffers.svelte b/frontend/src/creation/QuestOffers.svelte
index 3b3f56d..14b0713 100644
--- a/frontend/src/creation/QuestOffers.svelte
+++ b/frontend/src/creation/QuestOffers.svelte
@@ -134,7 +134,7 @@
         </div>
 
         <h4>Proposée à qui remplit</h4>
-        <ConditionEditor cond={draft.eligibility} {choices} role="eligibility" emptyLabel="Tout le monde." addLabel="+ condition" />
+        <ConditionEditor cond={draft.eligibility} {choices} unsaved={draft.unsavedAttributes} role="eligibility" emptyLabel="Tout le monde." addLabel="+ condition" />
 
         <h4>Étapes</h4>
         {#each draft.steps as step, i (i)}
@@ -157,9 +157,9 @@
                       onclick={() => draft.steps.splice(i, 1)}>✕</button>
             </div>
             <div class="muted">Prérequis</div>
-            <ConditionEditor cond={step.prerequisite} {choices} role="prerequisite" addLabel="+ prérequis de l'étape" />
+            <ConditionEditor cond={step.prerequisite} {choices} unsaved={draft.unsavedAttributes} role="prerequisite" addLabel="+ prérequis de l'étape" />
             <div class="muted">Objectif atteint quand</div>
-            <ConditionEditor cond={step.completion} {choices} role="completion"
+            <ConditionEditor cond={step.completion} {choices} unsaved={draft.unsavedAttributes} role="completion"
                              emptyLabel="Rien de vérifiable : c'est vous qui le déclarez." addLabel="+ condition d'objectif" />
           </div>
         {/each}
diff --git a/frontend/src/creation/attributes.svelte.js b/frontend/src/creation/attributes.svelte.js
index c7cdacb..36957a1 100644
--- a/frontend/src/creation/attributes.svelte.js
+++ b/frontend/src/creation/attributes.svelte.js
@@ -37,6 +37,18 @@ export function definitionDraft(attr) {
   };
 }
 
+/** A definition draft from a definition in the request body's shape -- the
+    interpreter's proposal (BRIEF-0113-E). */
+export function specDraft(def) {
+  return {
+    key: null, name: def.name, kind: def.kind, holder_types: [...(def.holder_types || [])],
+    value_types: [...(def.value_types || [])],
+    choices: (def.choices || []).map((c) => ({ id: null, label: c.label })),
+    defaultLabel: def.kind === 'choice' ? def.default : '', defaultInteger: def.kind === 'integer' ? def.default : 0,
+    is_hidden: !!def.is_hidden,
+  };
+}
+
 /** The request body of a definition draft (`DefinitionBody`). */
 export function definitionBody(draft, confirmNear) {
   return {
diff --git a/frontend/src/creation/conditionInterpreter.svelte.js b/frontend/src/creation/conditionInterpreter.svelte.js
index 47ff319..fce24a7 100644
--- a/frontend/src/creation/conditionInterpreter.svelte.js
+++ b/frontend/src/creation/conditionInterpreter.svelte.js
@@ -5,25 +5,46 @@
    Nothing reaches the offer before her « Enregistrer »: an inserted
    proposal replaces the condition draft (`conditionDraft`) and leaves its
    id on it (`cond.draftId`), which the save sends back (IH1). One attempt
-   id per editor, kept across reformulations. */
+   id per editor, kept across reformulations.
+   TICKET-0113 (BRIEF-0113-E, WK2, WN2): a proposal may carry the
+   attributes it proposes. Each is a card: when its name is near another
+   attribute's, the creator uses that one or creates this one; the one she
+   creates she may retouch (AttributeDefinitionForm) before « Insérer »,
+   which confirms the definitions with the condition and adds them to the
+   offer draft's `unsaved` list -- the offer's save writes them. Every
+   request carries that list. */
 import { api } from './sheetRequest.svelte.js';
 import { conditionBody, conditionDraft } from './questRequirements.js';
+import { definitionBody, specDraft } from './attributes.svelte.js';
 
 export function interpreterState() {
   return { open: false, instruction: '', attemptId: crypto.randomUUID(), busy: false, error: '',
-           proposal: null, picks: {} };
+           proposal: null, picks: {}, cards: [] };
 }
 
 async function post(path, body) {
   return api(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
 }
 
+function unsavedBody(unsaved) {
+  return (unsaved || []).map((u) => ({ ref: u.ref, definition: u.definition }));
+}
+
+/** One card per proposed attribute: its near attributes, the creator's pick
+    (`new` when nothing is near), its definition as a form draft. */
+function cardsOf(proposal) {
+  return (proposal?.definitions || []).filter((d) => !d.adopted).map((d) => ({
+    ref: d.ref, near: d.near || [], pick: (d.near || []).length ? '' : 'new', draft: specDraft(d.definition),
+  }));
+}
+
 async function run(state, request) {
   state.busy = true;
   state.error = '';
   try {
     state.proposal = await request();
     state.picks = {};
+    state.cards = cardsOf(state.proposal);
   } catch (e) {
     state.error = e.message;
   } finally {
@@ -32,33 +53,41 @@ async function run(state, request) {
 }
 
 /** A proposal for `cond` from the sentence; the current condition goes along (IC1). */
-export function askInterpreter(state, cond, role) {
+export function askInterpreter(state, cond, role, unsaved) {
   return run(state, () => post('/api/conditions/interpret', {
     instruction: state.instruction, role, current: conditionBody(cond), attempt_id: state.attemptId,
+    unsaved_attributes: unsavedBody(unsaved),
   }));
 }
 
-/** The names the creator picked, one per waiting mention. */
-export function pickNames(state) {
+/** The names the creator picked, one per waiting mention, and her pick for
+    each proposed attribute near another (WK2). */
+export function pickNames(state, unsaved) {
+  const bindings = { ...state.picks };
+  for (const card of state.cards) if (card.near.length) bindings[card.ref] = card.pick;
   return run(state, () => post('/api/conditions/drafts/' + state.proposal.draft_id + '/resolve',
-                               { bindings: state.picks }));
+                               { bindings, unsaved_attributes: unsavedBody(unsaved) }));
 }
 
-async function decide(state, decision) {
-  await post('/api/conditions/drafts/' + state.proposal.draft_id + '/decision', { decision });
+async function decide(state, decision, body) {
+  await post('/api/conditions/drafts/' + state.proposal.draft_id + '/decision', { decision, ...(body || {}) });
 }
 
-/** Insert the proposal into the condition draft (a flat one as rows, a nested one locked). */
-export async function insertProposal(state, cond) {
+/** Insert the proposal into the condition draft (a flat one as rows, a
+    nested one locked), with the attributes it proposes as confirmed. */
+export async function insertProposal(state, cond, unsaved) {
   const proposal = state.proposal;
+  const definitions = state.cards.map((c) => ({ ref: c.ref, definition: definitionBody(c.draft, false) }));
   try {
-    await decide(state, 'inserted');
+    await decide(state, 'inserted', { definitions, unsaved_attributes: unsavedBody(unsaved) });
   } catch (e) {
     state.error = e.message;
     return;
   }
+  for (const d of definitions) unsaved.push(d);
   Object.assign(cond, conditionDraft(proposal.view), { draftId: proposal.draft_id });
   state.proposal = null;
+  state.cards = [];
   state.instruction = '';
   state.open = false;
 }
@@ -71,4 +100,5 @@ export async function discardProposal(state) {
     state.error = e.message;
   }
   state.proposal = null;
+  state.cards = [];
 }
diff --git a/frontend/src/creation/questOffers.svelte.js b/frontend/src/creation/questOffers.svelte.js
index 048138c..146a7e9 100644
--- a/frontend/src/creation/questOffers.svelte.js
+++ b/frontend/src/creation/questOffers.svelte.js
@@ -7,7 +7,10 @@
    TICKET-0111 (BRIEF-0111-D): every condition -- the eligibility, each
    step's prerequisite and completion -- is a condition draft, sent as a
    tree (conditionBody). Since TICKET-0112 (BRIEF-0112-E, IH1): with the id
-   of the interpreter's proposal inserted into it, which the save marks. */
+   of the interpreter's proposal inserted into it, which the save marks.
+   Since TICKET-0113 (BRIEF-0113-E, WN2): `unsavedAttributes`, the
+   attributes the interpreter proposed and the creator confirmed, sent with
+   the save, which writes those a condition names. */
 import { api } from './sheetRequest.svelte.js';
 import { blankCondition, conditionBody, conditionDraft } from './questRequirements.js';
 import { blankTerm, termBody } from './questTerms.js';
@@ -33,7 +36,7 @@ export function newDraft() {
   questOffersState.saveError = '';
   questOffersState.draft = {
     id: null, giver_entity_id: '', contact_entity_id: '', title: '', summary: '', repeatable: false, status: 'open',
-    eligibility: blankCondition(), steps: [blankStep()], terms: [],
+    eligibility: blankCondition(), steps: [blankStep()], terms: [], unsavedAttributes: [],
   };
   refreshValue();
 }
@@ -54,6 +57,7 @@ export function editOffer(offer) {
       item_id: t.item_id || '', fact_id: t.fact_id || '', skill_key: t.skill_key || '', amount: t.amount,
       level: t.level || '',
     })),
+    unsavedAttributes: [],
   };
   questOffersState.value = offer.value || null;
 }
@@ -129,6 +133,7 @@ function draftBody(draft) {
       prerequisite_draft_id: s.prerequisite.draftId || null, completion_draft_id: s.completion.draftId || null,
     })),
     terms: draft.terms.map(termBody),
+    unsaved_attributes: draft.unsavedAttributes.map((u) => ({ ref: u.ref, definition: u.definition })),
   };
 }
 
diff --git a/frontend/src/creation/questRequirements.js b/frontend/src/creation/questRequirements.js
index 1daad89..92f5e5e 100644
--- a/frontend/src/creation/questRequirements.js
+++ b/frontend/src/creation/questRequirements.js
@@ -64,6 +64,21 @@ export function attributeOf(key, choices) {
   return (choices?.attributes || []).find((a) => a.key === key) || null;
 }
 
+/** TICKET-0113 (BRIEF-0113-E, WN2): the editor's choices with the draft's
+    unsaved attributes -- those the interpreter proposed and the creator
+    confirmed -- listed as `new:<ref>`, their labels as their own keys,
+    until the offer's save writes them. */
+export function withUnsaved(choices, unsaved) {
+  if (!choices || !unsaved?.length) return choices;
+  const extra = unsaved.map((u) => ({
+    key: 'new:' + u.ref, name: u.definition.name + ' (à créer)', kind: u.definition.kind, system: false,
+    hidden: !!u.definition.is_hidden, holder_types: u.definition.holder_types,
+    value_types: u.definition.value_types || [],
+    choices: (u.definition.choices || []).map((c) => ({ value: c.label, label: c.label })),
+  }));
+  return { ...choices, attributes: [...(choices.attributes || []), ...extra] };
+}
+
 /** TICKET-0113: what an `entity` attribute's value may name. */
 export function attributeTargets(attr, choices) {
   return (choices?.entities || []).filter((e) => attr.value_types.includes(e.type))
diff --git a/scripts/seed_pilot.py b/scripts/seed_pilot.py
index e14bcd8..32dfb33 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -2056,19 +2056,39 @@ CONDITION_INTERPRET_FRAGMENTS: tuple[tuple[str, str, str], ...] = (
      'un fait, une quête ou une compétence absent des listes ne peut pas être une cible.',
      'un fait, une quête, une compétence ou un état absent des listes ne peut pas être une cible.'),
     ("system_prompt",
-     "l'état d'une chose (\"state\" : la porte est ouverte)",
-     "un état absent de la liste des états (\"state\" : la porte est ouverte, sans état « ouverte »)"),
+     "l'état d'une chose (\"state\" : la porte est ouverte), ",
+     "un état que tu ne sais ni lire dans la liste des états ni proposer dans \"define\" (\"state\"), "),
     ("user_template",
      "Condition actuelle :\n{current}",
      "États (code — nom, sorte, pour qui) :\n{attributes}\n\nCondition actuelle :\n{current}"),
+    # BRIEF-0113-E (WK2): a state the list lacks is proposed in `define`.
+    # No fragment's old or new text may be touched by another's -- the
+    # delivery script finds each new text to know it is applied.
+    ("system_prompt",
+     "CE QUI N'EST PAS UNE CONDITION.",
+     "NOUVEL ÉTAT. Si la phrase parle d'un état absent de la liste des états, propose-le dans "
+     "\"define\" : {\"ref\": \"d1\", \"name\": \"Ouverte\", \"kind\": \"choice\" | \"integer\" | "
+     "\"entity\", \"for\": [les types d'entité auxquels il s'applique, par leur clé], \"choices\": "
+     "[\"non\", \"oui\"] (pour un choix), \"default\": un de ses libellés, un entier, ou null pour une "
+     "entité, \"value_types\": [les types qu'une entité peut nommer] (pour une entité), \"hidden\": "
+     "false}. La feuille le nomme par {\"define\": \"d1\"} comme cible. Ne propose jamais un état que "
+     "la liste contient déjà, même sous un autre nom proche : utilise son code.\n\n"
+     "CE QUI N'EST PAS UNE CONDITION."),
+    ("system_prompt",
+     ' "unsupported": [{"text": "...", "kind": "event"}]}',
+     ' "unsupported": [{"text": "...", "kind": "event"}],\n "define": []}'),
+    ("user_template",
+     "Entités que la phrase nomme :\n{entities}",
+     "Types d'entité (clé — nom) :\n{entity_types}\n\nEntités que la phrase nomme :\n{entities}"),
 )
 
 
 def with_condition_fragments(field: str, text: str) -> str:
     """`text` with every fragment of `CONDITION_INTERPRET_FRAGMENTS` for
-    `field` applied, in order."""
+    `field` applied, in order -- a fragment whose new text already stands is
+    skipped (an old fragment may stand inside its own new text)."""
     for target, old, new in CONDITION_INTERPRET_FRAGMENTS:
-        if target == field:
+        if target == field and new not in text:
             text = text.replace(old, new)
     return text
 
@@ -2091,8 +2111,8 @@ CONDITION_INTERPRET_PROMPT_HEADS = (
         world_id=None,
         system_prompt=CONDITION_INTERPRET_SYSTEM_PROMPT,
         user_template=CONDITION_INTERPRET_USER_TEMPLATE,
-        variables=["role", "forms", "entities", "tree_entities", "facts", "offers", "skills", "attributes",
-                   "current", "instruction", "errors"],
+        variables=["role", "forms", "entity_types", "entities", "tree_entities", "facts", "offers", "skills",
+                   "attributes", "current", "instruction", "errors"],
         destination="local",
     ),
 )
diff --git a/src/world_engine/attribute_proposals.py b/src/world_engine/attribute_proposals.py
new file mode 100644
index 0000000..e3d9f60
--- /dev/null
+++ b/src/world_engine/attribute_proposals.py
@@ -0,0 +1,277 @@
+"""The attributes the interpreter proposes (TICKET-0113, BRIEF-0113-E;
+decisions WK2 and WN2 of the conditions series).
+
+When the creator's sentence names a state her world does not define yet,
+the model proposes its definition in its answer's `define` block and the
+condition names it there. Until her « Enregistrer », such a definition is
+UNSAVED: it lives in the offer's draft, keyed `new:<ref>` (`n1`, `n2`, …),
+and every condition naming it is validated against it by the writer's own
+rules (`writes.conditions.clean_leaf(..., unsaved=...)`, the definition by
+`writes.attributes.clean_definition`). On the save (WN2), `materialize`
+writes each definition a condition still names -- through
+`write_attribute_definition`, in the offer's transaction -- and rewrites
+the conditions to its id, a label to its choice's id. A definition no
+condition names any more is not written.
+
+- `unsaved_view(p)`         : an `UnsavedAttribute` as an `AttributeView`
+  (its choices keyed by their label).
+- `clean_unsaved(...)`      : the draft's definitions as the client sends
+  them, cleaned.
+- `read_definitions(...)`   : the model's `define` block -> new unsaved
+  definitions with fresh refs, the model's refs mapped, and the errors.
+- `near_existing(...)`      : for each new definition, the attributes whose
+  name is near (`attributes.near_attributes`, and the other unsaved ones) --
+  the creator picks one or creates (WK2); the tool never picks.
+- `adopt(...)`              : a pick of an existing attribute -- the leaves
+  naming `new:<ref>` rewritten to it, a label to its choice's key.
+- `materialize(...)`        : the save's half (WN2).
+
+Writes nothing except through `materialize`, which calls the writer and
+never commits.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Any, Optional
+
+from sqlmodel import Session
+
+from .attributes import (
+    ATTRIBUTE_FORM,
+    AttributeView,
+    attribute_view,
+    near_attributes,
+    world_entity_type_labels,
+)
+from .lore_resolve import near_ratio, near_score, normalize_surface
+from .writes.attributes import ChoiceSpec, DefinitionSpec, clean_definition, write_attribute_definition
+
+UNSAVED_PREFIX = "new:"
+
+
+@dataclass(frozen=True)
+class UnsavedAttribute:
+    ref: str
+    spec: DefinitionSpec
+
+
+def unsaved_key(ref: str) -> str:
+    return UNSAVED_PREFIX + ref
+
+
+def is_unsaved(key: Optional[str]) -> bool:
+    return bool(key) and key.startswith(UNSAVED_PREFIX)
+
+
+def unsaved_view(item: UnsavedAttribute) -> AttributeView:
+    spec = item.spec
+    return AttributeView(
+        key=unsaved_key(item.ref), name=spec.name, kind=spec.kind, system=False, hidden=spec.is_hidden,
+        status="active", holder_types=tuple(spec.holder_types), value_types=tuple(spec.value_types),
+        choices=tuple((c.label, c.label) for c in spec.choices), default=spec.default,
+    )
+
+
+def unsaved_views(items) -> dict[str, AttributeView]:
+    return {unsaved_key(item.ref): unsaved_view(item) for item in items}
+
+
+def spec_dict(spec: DefinitionSpec) -> dict:
+    """A definition in the request body's shape (`routes.attributes.DefinitionBody`)."""
+    return {"name": spec.name, "kind": spec.kind, "holder_types": list(spec.holder_types),
+            "value_types": list(spec.value_types), "choices": [{"label": c.label} for c in spec.choices],
+            "default": spec.default, "is_hidden": spec.is_hidden}
+
+
+def spec_from_dict(raw: Any) -> DefinitionSpec:
+    if not isinstance(raw, dict):
+        raise ValueError(f"a definition is an object, got {raw!r}")
+    return DefinitionSpec(
+        name=raw.get("name") or "", kind=raw.get("kind") or "",
+        holder_types=tuple(raw.get("holder_types") or ()), value_types=tuple(raw.get("value_types") or ()),
+        choices=tuple(ChoiceSpec(str(c.get("label") if isinstance(c, dict) else c)) for c in raw.get("choices") or ()),
+        default=raw.get("default"), is_hidden=bool(raw.get("is_hidden")),
+    )
+
+
+def clean_unsaved(db: Session, world_id: str, raw: Any) -> list[UnsavedAttribute]:
+    """The draft's unsaved definitions, as the client sends them
+    (`[{ref, definition}]`), each cleaned by `clean_definition`; two with
+    one name, or a ref used twice, are refused. `ValueError` names the
+    first problem."""
+    items: list[UnsavedAttribute] = []
+    names: set[str] = set()
+    for entry in raw or []:
+        ref = str((entry or {}).get("ref") or "")
+        if not ref or any(i.ref == ref for i in items):
+            raise ValueError(f"an unsaved attribute needs a ref of its own, got {ref!r}")
+        try:
+            spec = clean_definition(db, world_id, spec_from_dict(entry.get("definition")))
+        except ValueError as exc:
+            raise ValueError(f"« {(entry.get('definition') or {}).get('name')} » : {exc}") from exc
+        if normalize_surface(spec.name) in names:
+            raise ValueError(f"« {spec.name} » is proposed twice")
+        names.add(normalize_surface(spec.name))
+        items.append(UnsavedAttribute(ref=ref, spec=spec))
+    return items
+
+
+# --- the model's `define` block (C-12) --------------------------------------------
+
+def _types(raw: Any, labels: dict[str, str]) -> tuple[str, ...]:
+    """Entity types the model named, by key or by French name."""
+    by_name = {normalize_surface(label): key for key, label in labels.items()}
+    out = []
+    for item in raw if isinstance(raw, list) else []:
+        text = str(item or "")
+        key = text if text in labels else by_name.get(normalize_surface(text))
+        if key is None:
+            raise ValueError(f"unknown entity type {text!r}")
+        out.append(key)
+    return tuple(out)
+
+
+def _model_spec(raw: dict, labels: dict[str, str]) -> DefinitionSpec:
+    choices = raw.get("choices") if isinstance(raw.get("choices"), list) else []
+    return DefinitionSpec(
+        name=str(raw.get("name") or ""), kind=str(raw.get("kind") or ""),
+        holder_types=_types(raw.get("for"), labels), value_types=_types(raw.get("value_types"), labels),
+        choices=tuple(ChoiceSpec(str(c)) for c in choices), default=raw.get("default"),
+        is_hidden=bool(raw.get("hidden")),
+    )
+
+
+def read_definitions(db: Session, world_id: str, raw: Any, taken: set[str],
+                     others: list[UnsavedAttribute]) -> tuple[list[UnsavedAttribute], dict[str, str], list[str]]:
+    """The model's `define` block: each definition cleaned by
+    `clean_definition` and given a fresh ref (`n<k>`, past every ref of
+    `taken`); returns the new definitions, the model's ref -> `new:<ref>`,
+    and the errors in French (a definition refused, one already in the
+    draft's)."""
+    labels = {t["type"]: t["label"] for t in world_entity_type_labels(db, world_id)}
+    new: list[UnsavedAttribute] = []
+    refs: dict[str, str] = {}
+    errors: list[str] = []
+    names = {normalize_surface(o.spec.name) for o in others}
+    for raw_def in raw if isinstance(raw, list) else []:
+        if not isinstance(raw_def, dict):
+            errors.append(f"état proposé : un objet attendu, reçu {raw_def!r}")
+            continue
+        name = str(raw_def.get("name") or "").strip()
+        try:
+            spec = clean_definition(db, world_id, _model_spec(raw_def, labels))
+        except ValueError as exc:
+            errors.append(f"état proposé « {name} » : {exc}")
+            continue
+        if normalize_surface(spec.name) in names:
+            errors.append(f"état proposé « {name} » : il est déjà proposé, utilise son code")
+            continue
+        names.add(normalize_surface(spec.name))
+        k = 1
+        while f"n{k}" in taken:
+            k += 1
+        taken.add(f"n{k}")
+        new.append(UnsavedAttribute(ref=f"n{k}", spec=spec))
+        refs[str(raw_def.get("ref") or name)] = unsaved_key(f"n{k}")
+    return new, refs, errors
+
+
+def near_existing(db: Session, world_id: str, new: list[UnsavedAttribute],
+                  others: list[UnsavedAttribute]) -> dict[str, list[dict]]:
+    """For each new definition whose name is near another attribute's -- a
+    saved one, or one already in the draft -- the near ones, best first
+    (`{key, name, system, score}`). WK2: never a duplicate « Maudit » /
+    « maudite » unseen."""
+    out: dict[str, list[dict]] = {}
+    for item in new:
+        near = [{"key": n.key, "name": n.name, "system": n.system, "score": n.score}
+                for n in near_attributes(db, world_id, item.spec.name)]
+        target = normalize_surface(item.spec.name)
+        for other in others:
+            ratio = near_ratio(target, other.spec.name)
+            if ratio is not None:
+                near.append({"key": unsaved_key(other.ref), "name": other.spec.name, "system": False,
+                             "score": near_score(ratio)})
+        if near:
+            out[item.ref] = sorted(near, key=lambda n: (-n["score"], n["name"].casefold()))
+    return out
+
+
+def adopt(db: Session, world_id: str, tree: Optional[dict], ref: str, key: str,
+          views: dict[str, AttributeView]) -> Optional[dict]:
+    """`tree` (dict form) with every leaf on `new:<ref>` moved to the
+    existing attribute `key` -- a label read back to its choice's key
+    (case- and accent-blind). `ValueError` when a label is not one of its."""
+    view = views.get(key) or attribute_view(db, world_id, key)
+    if view is None:
+        raise ValueError(f"unknown attribute {key!r}")
+    by_label = {normalize_surface(label): choice for choice, label in view.choices}
+
+    def move(node: dict) -> dict:
+        if node.get("op") != "leaf":
+            return {**node, "children": [move(c) for c in node.get("children", [])]}
+        if node.get("target_key") != unsaved_key(ref):
+            return node
+        out = {**node, "target_key": key}
+        if view.kind == "choice" and node.get("value") is not None:
+            choice = by_label.get(normalize_surface(str(node["value"])))
+            if choice is None:
+                labels = ", ".join(label for _c, label in view.choices)
+                raise ValueError(f"« {node['value']} » n'est pas un libellé de « {view.name} » (libellés : {labels})")
+            out["value"] = choice
+        return out
+
+    return move(tree) if tree is not None else None
+
+
+# --- the save (WN2) ----------------------------------------------------------------
+
+def _named(tree: Optional[dict], found: set[str]) -> None:
+    if not tree:
+        return
+    if tree.get("op") == "leaf":
+        if tree.get("type") == ATTRIBUTE_FORM and is_unsaved(tree.get("target_key")):
+            found.add(tree["target_key"])
+        return
+    for child in tree.get("children", []):
+        _named(child, found)
+
+
+def rewrite(tree: Optional[dict], keys: dict[str, str], labels: dict[tuple[str, str], str]) -> Optional[dict]:
+    """`tree` with each `new:` key replaced by its written id and each of
+    its labels by its choice's id."""
+    if tree is None:
+        return None
+    if tree.get("op") != "leaf":
+        return {**tree, "children": [rewrite(c, keys, labels) for c in tree.get("children", [])]}
+    key = tree.get("target_key")
+    if tree.get("type") != ATTRIBUTE_FORM or key not in keys:
+        return tree
+    out = {**tree, "target_key": keys[key]}
+    if tree.get("value") is not None:
+        out["value"] = labels.get((key, tree["value"]), tree["value"])
+    return out
+
+
+def materialize(db: Session, world_id: str, raw: Any, trees: list[Optional[dict]]
+                ) -> tuple[list[Optional[dict]], dict[str, str], dict[tuple[str, str], str]]:
+    """WN2: write every unsaved definition one of `trees` names, in the
+    caller's transaction, and return the trees rewritten to the written ids,
+    with the key and label maps. A definition no tree names is not written.
+    `ValueError` for a tree naming a definition the body does not carry."""
+    items = {unsaved_key(i.ref): i for i in clean_unsaved(db, world_id, raw)}
+    named: set[str] = set()
+    for tree in trees:
+        _named(tree, named)
+    missing = sorted(named - set(items))
+    if missing:
+        raise ValueError(f"a condition names an unsaved attribute the offer does not carry: {missing}")
+    keys: dict[str, str] = {}
+    labels: dict[tuple[str, str], str] = {}
+    for key in sorted(named):
+        definition = write_attribute_definition(db, world_id=world_id, spec=items[key].spec)
+        keys[key] = definition.id
+        for choice, label in attribute_view(db, world_id, definition.id).choices:
+            labels[(key, label)] = choice
+    return [rewrite(tree, keys, labels) for tree in trees], keys, labels
diff --git a/src/world_engine/cockpit/routes/attributes.py b/src/world_engine/cockpit/routes/attributes.py
index e0f3558..254b816 100644
--- a/src/world_engine/cockpit/routes/attributes.py
+++ b/src/world_engine/cockpit/routes/attributes.py
@@ -74,6 +74,13 @@ class DefinitionBody(BaseModel):
     confirm_near: bool = False
 
 
+class UnsavedBody(BaseModel):
+    """BRIEF-0113-E (WN2): an attribute the interpreter proposed, in the
+    offer's draft until the offer's save writes it (`routes/quests.py`)."""
+    ref: str
+    definition: DefinitionBody
+
+
 class StatusBody(BaseModel):
     status: str
 
diff --git a/src/world_engine/cockpit/routes/conditions.py b/src/world_engine/cockpit/routes/conditions.py
index 9e340b9..e2a6a8c 100644
--- a/src/world_engine/cockpit/routes/conditions.py
+++ b/src/world_engine/cockpit/routes/conditions.py
@@ -9,6 +9,12 @@ conditions series:
     POST /api/conditions/drafts/{draft_id}/resolve    the names she picked
     POST /api/conditions/drafts/{draft_id}/decision   inserted | discarded
 
+Since TICKET-0113 (BRIEF-0113-E, WK2, WN2), a proposal may carry the
+attributes it proposes: the editor sends the draft's unsaved ones with each
+request, the creator picks between a near existing attribute and a new one
+(`resolve`), and confirms each definition -- retouched in the card or not --
+with `inserted`; the offer's save writes them (`routes/quests.py`).
+
 Every model call lives in `condition_interpreter`, every journal write in
 `writes/condition_drafts.py`; this module parses, maps a refusal to its
 status code, and commits once per request. Every proposal that reached the
@@ -35,7 +41,9 @@ from ...lore_usage import attempt_id as _attempt_id
 from ...models import CONDITION_ROLES, ConditionDraft
 from ...ollama_client import OllamaError
 from ...quest_reads import condition_view
+from ...attribute_proposals import UnsavedAttribute, clean_unsaved, spec_dict, spec_from_dict, unsaved_views
 from ...writes.conditions import clean_condition
+from .attributes import UnsavedBody
 from ...writes.condition_drafts import move_condition_draft, write_condition_draft
 from .. import crud as _crud
 
@@ -55,44 +63,68 @@ class InterpretBody(BaseModel):
     # `conditions.node_to_dict`; null when the creator starts from nothing.
     current: Optional[dict] = None
     attempt_id: Optional[str] = None
+    # The offer draft's unsaved attributes: the model sees them, the leaves
+    # may name them (BRIEF-0113-E).
+    unsaved_attributes: list[UnsavedBody] = Field(default_factory=list)
 
 
 class ResolveBody(BaseModel):
+    # A name's ref -> its entity id; a proposed attribute's ref -> `new` or
+    # the key of the attribute it is near (BRIEF-0113-E, WK2).
     bindings: dict[str, str] = Field(default_factory=dict)
+    unsaved_attributes: list[UnsavedBody] = Field(default_factory=list)
 
 
 class DecisionBody(BaseModel):
     decision: str
+    # On `inserted` (BRIEF-0113-E): the proposed attributes as the creator
+    # confirmed them -- retouched or not -- and the draft's other unsaved ones.
+    definitions: list[UnsavedBody] = Field(default_factory=list)
+    unsaved_attributes: list[UnsavedBody] = Field(default_factory=list)
+
 
+def _unsaved(db: Session, world_id: str, items: list[UnsavedBody]) -> tuple:
+    """The draft's unsaved attributes, cleaned; 422 when one does not hold."""
+    try:
+        return tuple(clean_unsaved(db, world_id, [i.model_dump() for i in items]))
+    except ValueError as exc:
+        raise HTTPException(status_code=422, detail=f"Un état proposé ne tient plus : {exc}") from exc
 
-def _current(body: InterpretBody, world_id: str, db: Session):
+
+def _current(body: InterpretBody, world_id: str, db: Session, unsaved: tuple):
     if not body.instruction.strip():
         raise HTTPException(status_code=422, detail="Écris d'abord la condition en une phrase.")
     if body.role not in CONDITION_ROLES:
         raise HTTPException(status_code=422, detail=f"unknown condition role {body.role!r}")
     try:
-        return clean_condition(db, world_id, node_from_dict(body.current), where="current: ")
+        return clean_condition(db, world_id, node_from_dict(body.current), where="current: ",
+                               unsaved=unsaved_views(unsaved))
     except ValueError as exc:
         raise HTTPException(status_code=422, detail=f"La condition actuelle ne tient pas : {exc}") from exc
 
 
-def _answer(draft: ConditionDraft, result: Optional[_interpreter.Interpretation], db: Session) -> dict:
-    """C-06: what the editor shows."""
+def _answer(draft: ConditionDraft, result: Optional[_interpreter.Interpretation], db: Session,
+            unsaved: tuple = ()) -> dict:
+    """C-06: what the editor shows; since TICKET-0113 (BRIEF-0113-E) the
+    attributes the answer proposes, each with the attributes near it."""
     if result is None:
         return {"draft_id": draft.id, "outcome": draft.outcome, "view": None, "mentions": [], "notes": [],
-                "errors": []}
+                "errors": [], "definitions": []}
+    views = unsaved_views(tuple(unsaved) + tuple(
+        UnsavedAttribute(ref=d["ref"], spec=spec_from_dict(d["definition"]))
+        for d in result.definitions if not d.get("adopted")))
     return {
         "draft_id": draft.id, "outcome": result.outcome,
-        "view": condition_view(db, result.tree) if result.tree is not None else None,
+        "view": condition_view(db, result.tree, views) if result.tree is not None else None,
         "mentions": [m for m in result.mentions if m["status"] != "matched" and m["choices"]],
-        "notes": result.notes, "errors": result.errors,
+        "notes": result.notes, "errors": result.errors, "definitions": result.definitions,
     }
 
 
 def _failed(db: Session, body: InterpretBody, world_id: str, current, outcome: str,
             exchanges: list, exc: Exception) -> None:
     model_exchange.fail(exchanges, exc)
-    empty = _interpreter.Interpretation(outcome, None, None, [], [], [])
+    empty = _interpreter.Interpretation(outcome, None, None, [], [], [], False, [])
     write_condition_draft(
         db, attempt_id=_attempt_id(body.attempt_id), world_id=world_id, role=body.role,
         instruction=body.instruction, outcome=outcome, payload=empty.payload(current),
@@ -104,10 +136,11 @@ def _failed(db: Session, body: InterpretBody, world_id: str, current, outcome: s
 @router.post("/api/conditions/interpret")
 def interpret(body: InterpretBody, db: Session = Depends(get_session)) -> dict:
     world_id = _crud._world_id(db)
-    current = _current(body, world_id, db)
+    unsaved = _unsaved(db, world_id, body.unsaved_attributes)
+    current = _current(body, world_id, db, unsaved)
     exchanges: list[model_exchange.ModelExchange] = []
     try:
-        result = _interpreter.interpret(db, world_id, body.role, body.instruction, current, exchanges)
+        result = _interpreter.interpret(db, world_id, body.role, body.instruction, current, exchanges, unsaved)
     except OllamaError as exc:
         _failed(db, body, world_id, current, "unavailable", exchanges, exc)
         raise HTTPException(status_code=503, detail=_interpreter.INTERPRET_UNAVAILABLE_MESSAGE) from exc
@@ -120,7 +153,7 @@ def interpret(body: InterpretBody, db: Session = Depends(get_session)) -> dict:
         payload=result.payload(current), model_calls=[e.to_record() for e in exchanges],
     )
     db.commit()
-    return _answer(draft, result, db)
+    return _answer(draft, result, db, unsaved)
 
 
 def _draft(db: Session, draft_id: str) -> ConditionDraft:
@@ -137,15 +170,17 @@ def resolve(draft_id: str, body: ResolveBody, db: Session = Depends(get_session)
     if draft.outcome != "needs_choice":
         raise HTTPException(status_code=409, detail=f"a {draft.outcome!r} proposal has no name to pick")
     stored = draft.payload
+    unsaved = _unsaved(db, draft.world_ref, body.unsaved_attributes)
     try:
         result = _interpreter.resolve(db, draft.world_ref, stored["pending"], stored["mentions"],
-                                      stored["notes"], body.bindings)
+                                      stored["notes"], body.bindings, tuple(stored.get("definitions") or ()),
+                                      unsaved)
     except ValueError as exc:
         raise HTTPException(status_code=422, detail=str(exc)) from exc
     move_condition_draft(db, draft, result.outcome,
                          result.payload(node_from_dict(stored["current"]), body.bindings))
     db.commit()
-    return _answer(draft, result, db)
+    return _answer(draft, result, db, unsaved)
 
 
 @router.post("/api/conditions/drafts/{draft_id}/decision")
@@ -153,9 +188,33 @@ def decide(draft_id: str, body: DecisionBody, db: Session = Depends(get_session)
     draft = _draft(db, draft_id)
     if body.decision not in DECISIONS:
         raise HTTPException(status_code=422, detail=f"unknown decision {body.decision!r}")
+    payload = _confirmed(db, draft, body) if body.decision == "inserted" else None
     try:
-        move_condition_draft(db, draft, body.decision)
+        move_condition_draft(db, draft, body.decision, payload)
     except ValueError as exc:
         raise HTTPException(status_code=409, detail=str(exc)) from exc
     db.commit()
     return _answer(draft, None, db)
+
+
+def _confirmed(db: Session, draft: ConditionDraft, body: DecisionBody) -> Optional[dict]:
+    """BRIEF-0113-E: on `inserted`, the proposed attributes as the creator
+    confirmed them -- each must be one the proposal holds -- checked with
+    the proposed tree; 422 when the tree no longer holds. The journal keeps
+    each definition's `confirmed` form beside its proposed one."""
+    stored = draft.payload.get("definitions") or []
+    proposed = {d["ref"]: d for d in stored if not d.get("adopted")}
+    if not body.definitions and not proposed:
+        return None
+    if {d.ref for d in body.definitions} != set(proposed):
+        raise HTTPException(status_code=422, detail="Confirme chaque état proposé, ni plus ni moins.")
+    unsaved = _unsaved(db, draft.world_ref, body.unsaved_attributes + body.definitions)
+    edited = tuple(u for u in unsaved if u.ref in proposed)
+    tree, errors = _interpreter.confirm(db, draft.world_ref, draft.payload.get("proposed"),
+                                        tuple(u for u in unsaved if u.ref not in proposed), edited)
+    if tree is None:
+        raise HTTPException(status_code=422, detail="La condition ne tient plus : " + " ; ".join(errors))
+    payload = dict(draft.payload)
+    payload["definitions"] = [{**proposed[u.ref], "confirmed": spec_dict(u.spec)} for u in edited] + [
+        d for d in stored if d.get("adopted")]
+    return payload
diff --git a/src/world_engine/cockpit/routes/quests.py b/src/world_engine/cockpit/routes/quests.py
index 22825b0..7b2ba76 100644
--- a/src/world_engine/cockpit/routes/quests.py
+++ b/src/world_engine/cockpit/routes/quests.py
@@ -41,10 +41,12 @@ from ...writes import (
     TermSpec, abandon_quest, accept_quest, settle_quest, settle_quest_on_credit, upsert_quest_economy,
     write_quest_offer,
 )
+from ...attribute_proposals import materialize, rewrite
 from ...writes.condition_drafts import mark_draft_saved
 from ...writes.conditions import clean_condition
 from ...writes.quest_terms import ECONOMY_COLUMNS
 from .. import crud as _crud
+from .attributes import UnsavedBody
 from .day import _resolve_player_character
 
 router = APIRouter()
@@ -90,6 +92,9 @@ class OfferBody(BaseModel):
     terms: Optional[list[TermBody]] = None
     # TICKET-0112 (IH1): the interpreter's proposal inserted into the eligibility.
     eligibility_draft_id: Optional[str] = None
+    # TICKET-0113 (BRIEF-0113-E, WN2): the attributes the interpreter proposed
+    # and the creator confirmed; the save writes those a condition names.
+    unsaved_attributes: list[UnsavedBody] = Field(default_factory=list)
 
 
 class ValueBody(BaseModel):
@@ -123,37 +128,44 @@ class CreditBody(BaseModel):
 
 def _save_offer(body: OfferBody, offer: Optional[QuestOffer], world_id: str, db: Session) -> dict:
     try:
+        # WN2 (TICKET-0113): the proposed attributes a condition names are
+        # written first, in this transaction, and the conditions rewritten
+        # to their ids.
+        trees, keys, labels = materialize(
+            db, world_id, [u.model_dump() for u in body.unsaved_attributes],
+            [body.eligibility] + [t for s in body.steps for t in (s.prerequisite, s.completion)])
         steps = [PlanStep(objective=s.objective, cost=s.cost, domain=s.domain or None,
-                          prerequisite=node_from_dict(s.prerequisite), completion=node_from_dict(s.completion))
-                 for s in body.steps]
+                          prerequisite=node_from_dict(trees[1 + 2 * i]), completion=node_from_dict(trees[2 + 2 * i]))
+                 for i, s in enumerate(body.steps)]
         offer = write_quest_offer(
             db, world_id=world_id, offer=offer, giver_entity_id=body.giver_entity_id, title=body.title,
             summary=body.summary, repeatable=body.repeatable, status=body.status,
-            eligibility=node_from_dict(body.eligibility), steps=steps,
+            eligibility=node_from_dict(trees[0]), steps=steps,
             terms=None if body.terms is None else [_term(t) for t in body.terms],
             contact_entity_id=body.contact_entity_id or None,
         )
     except ValueError as exc:
         db.rollback()
         raise HTTPException(status_code=422, detail=str(exc)) from exc
-    _mark_drafts(body, offer.id, world_id, db)
+    _mark_drafts(body, trees, offer.id, world_id, db, lambda proposed: rewrite(proposed, keys, labels))
     db.commit()
     db.refresh(offer)
     return quest_reads.offer_dict(offer, db)
 
 
-def _mark_drafts(body: OfferBody, offer_id: str, world_id: str, db: Session) -> None:
+def _mark_drafts(body: OfferBody, trees: list, offer_id: str, world_id: str, db: Session, as_saved) -> None:
     """IH1: each inserted proposal is `saved` with the offer, in its
     transaction, compared with the condition as written (its clean dict
-    form). A draft that cannot be marked is skipped: the journal never fails
-    the creator's save."""
-    pairs = [(body.eligibility_draft_id, body.eligibility)] + [
-        pair for step in body.steps
-        for pair in ((step.prerequisite_draft_id, step.prerequisite), (step.completion_draft_id, step.completion))]
-    for draft_id, raw in pairs:
+    form) -- the proposal's unsaved attributes rewritten to the ids the save
+    wrote (`as_saved`, TICKET-0113). A draft that cannot be marked is
+    skipped: the journal never fails the creator's save."""
+    ids = [body.eligibility_draft_id] + [
+        d for step in body.steps for d in (step.prerequisite_draft_id, step.completion_draft_id)]
+    for draft_id, raw in zip(ids, trees):
         if draft_id:
             tree = node_to_dict(clean_condition(db, world_id, node_from_dict(raw)))
-            mark_draft_saved(db, world_id=world_id, draft_id=draft_id, offer_id=offer_id, tree=tree)
+            mark_draft_saved(db, world_id=world_id, draft_id=draft_id, offer_id=offer_id, tree=tree,
+                             proposed_as_saved=as_saved)
 
 
 @router.get("/api/quest-offers")
diff --git a/src/world_engine/condition_interpreter.py b/src/world_engine/condition_interpreter.py
index 4815850..6106336 100644
--- a/src/world_engine/condition_interpreter.py
+++ b/src/world_engine/condition_interpreter.py
@@ -35,6 +35,16 @@ from typing import Any, Optional
 from sqlmodel import Session, select
 
 from . import model_exchange, prompt_call
+from .attribute_proposals import (
+    adopt,
+    is_unsaved,
+    near_existing,
+    read_definitions,
+    spec_dict,
+    spec_from_dict,
+    unsaved_views,
+    UnsavedAttribute,
+)
 from .attributes import ATTRIBUTE_FORM, AttributeView, world_attributes, world_entity_type_labels
 from .condition_forms import ENTITY_TARGET_TYPES, FORM_VALUES, REQUIREMENT_TYPES, RequirementSpec
 from .condition_text import FORM_PHRASES_FR, VALUE_LABELS_FR
@@ -113,6 +123,7 @@ class InterpreterContext:
     lists: dict[str, CodedRefs]  # "e", "f", "q", "s", "a"
     current: Optional[dict]
     attributes: dict[str, AttributeView] = field(default_factory=dict)  # key -> view, the `a` list's
+    type_lines: tuple[str, ...] = ()  # the types a proposed definition may name (BRIEF-0113-E)
 
 
 def _current_ids(tree: Optional[ConditionTree]) -> dict[str, list[str]]:
@@ -137,7 +148,8 @@ def _skill_pairs(db: Session, world_id: str) -> list[tuple[str, str]]:
         ((d.id, d.name) for d in definitions), key=lambda pair: pair[1].lower())
 
 
-def build_context(db: Session, world_id: str, instruction: str, current: Optional[ConditionTree]) -> InterpreterContext:
+def build_context(db: Session, world_id: str, instruction: str, current: Optional[ConditionTree],
+                  unsaved: tuple = ()) -> InterpreterContext:
     """IE1: the facts of the current tree, then of the entities the
     instruction names, then the world-level facts, creator-only facts
     included, capped at `MAX_CODED_FACTS`; every offer and skill of the
@@ -151,7 +163,8 @@ def build_context(db: Session, world_id: str, instruction: str, current: Optiona
     fact_ids += world_fact_ids(db, world_id)
     offers = db.exec(select(QuestOffer).where(QuestOffer.world_id == world_id)).all()
     attributes = {view.key: view for view in world_attributes(db, world_id)}
-    types = {t["type"]: t["label"].lower() for t in world_entity_type_labels(db, world_id)}
+    attributes.update(unsaved_views(unsaved))  # the draft's proposed ones (BRIEF-0113-E)
+    types = {t["type"]: t["label"] for t in world_entity_type_labels(db, world_id)}
     lists = {
         "e": code_refs("e", ((eid, _entity_label(db, eid)) for eid in ids["e"])),
         "f": code_facts(db, list(dict.fromkeys(fact_ids))[:MAX_CODED_FACTS]),
@@ -161,6 +174,7 @@ def build_context(db: Session, world_id: str, instruction: str, current: Optiona
     }
     lines = tuple(f"- {_entity_label(db, eid)}" for eid in named)
     return InterpreterContext(entity_lines=lines, lists=lists, attributes=attributes,
+                              type_lines=tuple(f"{t} — {label}" for t, label in types.items()),
                               current=encode(current, lists, attributes) if current is not None else None)
 
 
@@ -168,15 +182,15 @@ def attribute_line(view: AttributeView, types: dict[str, str]) -> str:
     """One attribute as the model reads it in the `a` list (BRIEF-0113-D):
     its name, its kind and what it compares to, the types it applies to."""
     holders = "toute entité" if view.holder_types is None else ", ".join(
-        types.get(t, t) for t in view.holder_types)
+        types.get(t, t).lower() for t in view.holder_types)
     if view.kind == "choice":
         kind = "choix : " + ", ".join(label for _key, label in view.choices)
     elif view.kind == "integer":
         kind = "nombre"
     else:
-        kind = "une entité : " + ", ".join(types.get(t, t) for t in view.value_types)
-    system = "système ; " if view.system else ""
-    return f"{view.name} ({system}{kind} ; pour : {holders})"
+        kind = "une entité : " + ", ".join(types.get(t, t).lower() for t in view.value_types)
+    status = "système ; " if view.system else "à créer, proposé ; " if is_unsaved(view.key) else ""
+    return f"{view.name} ({status}{kind} ; pour : {holders})"
 
 
 # --- the model's form (C-03) ---------------------------------------------------
@@ -236,6 +250,7 @@ class Reading:
     mentions: list[dict] = field(default_factory=list)
     errors: list[str] = field(default_factory=list)
     name_errors: list[str] = field(default_factory=list)
+    defined: dict[str, str] = field(default_factory=dict)  # the model's `define` ref -> `new:<ref>` (E)
 
 
 def _mention(db: Session, world_id: str, raw: dict, reading: Reading) -> Optional[str]:
@@ -298,10 +313,17 @@ def _leaf(db: Session, world_id: str, raw: dict, ctx: InterpreterContext, readin
             subject = {"name": subject, "kind": "person"}
         out["subject_entity_id"], out["subject_mention"] = _entity(db, world_id, subject, ctx, reading, where)
     target = raw.get("target")
+    if form == ATTRIBUTE_FORM and isinstance(target, dict) and "define" in target:
+        target = {"key": reading.defined.get(str(target["define"]))}
+        if target["key"] is None:
+            reading.errors.append(f"{where}état proposé inconnu {raw['target']['define']!r} (attendu : un "
+                                  "ref de « define »)")
     if isinstance(target, str) and form in ENTITY_TARGET_TYPES:  # a bare name
         target = {"name": target, "kind": "other"}
     if form in ENTITY_TARGET_TYPES:
         out["target_entity_id"], out["target_mention"] = _entity(db, world_id, target, ctx, reading, where)
+    elif form == ATTRIBUTE_FORM and isinstance(target, dict) and "key" in target:
+        out["target_key"] = target["key"]
     elif form in CODE_LISTS:
         code = target.get("code") if isinstance(target, dict) else target
         out["target_key"] = ctx.lists[CODE_LISTS[form]].resolve(code)
@@ -361,10 +383,12 @@ def _read(db: Session, world_id: str, raw: Any, ctx: InterpreterContext, reading
     return out
 
 
-def read_answer(db: Session, world_id: str, raw: Any, ctx: InterpreterContext) -> Reading:
+def read_answer(db: Session, world_id: str, raw: Any, ctx: InterpreterContext,
+                defined: Optional[dict[str, str]] = None) -> Reading:
     """The model's `condition` read back: codes and names resolved, nothing
-    validated yet. None reads as no tree."""
-    reading = Reading()
+    validated yet. None reads as no tree. `defined`: the model's `define`
+    refs, already read (`attribute_proposals.read_definitions`)."""
+    reading = Reading(defined=dict(defined or {}))
     if raw is not None:
         reading.pending = _read(db, world_id, raw, ctx, reading, "1")
     return reading
@@ -409,10 +433,12 @@ def _tree(raw: dict) -> ConditionTree:
     return ConditionTree(op=raw["op"], n=raw.get("n"), children=tuple(_tree(c) for c in raw.get("children", [])))
 
 
-def validate(db: Session, world_id: str, pending: dict) -> tuple[Optional[ConditionTree], list[str]]:
+def validate(db: Session, world_id: str, pending: dict,
+             unsaved: Optional[dict] = None) -> tuple[Optional[ConditionTree], list[str]]:
     """A bound tree checked whole: its shape, then every leaf on its own
     (`clean_leaf`), so every error is reported at once. (tree, []) or
-    (None, errors)."""
+    (None, errors). `unsaved`: the proposed attributes' views, by `new:`
+    key (BRIEF-0113-E)."""
     try:
         tree = _tree(pending)
         check_shape(tree)
@@ -421,12 +447,12 @@ def validate(db: Session, world_id: str, pending: dict) -> tuple[Optional[Condit
     errors = []
     for index, spec in enumerate(leaves(tree), start=1):
         try:
-            clean_leaf(db, world_id, spec, where=f"condition {index} ({spec.type}) : ")
+            clean_leaf(db, world_id, spec, where=f"condition {index} ({spec.type}) : ", unsaved=unsaved)
         except ValueError as exc:
             errors.append(str(exc))
     if errors:
         return None, errors
-    clean = clean_condition(db, world_id, tree)
+    clean = clean_condition(db, world_id, tree, unsaved=unsaved)
     # A lone leaf is proposed as the editor's list sends it back: `all` of it
     # (`conditions.flat_leaves`, T1), so an unchanged insert saves as proposed.
     return (all_of(leaves(clean)) if clean.op == "leaf" else clean), []
@@ -445,12 +471,15 @@ class Interpretation:
     notes: list[str]
     errors: list[str]
     retried: bool = False
+    # BRIEF-0113-E: the attributes this answer proposes -- `{ref, definition,
+    # near}`, `near` the attributes whose name is near (the creator picks).
+    definitions: list[dict] = field(default_factory=list)
 
     def payload(self, current: Optional[ConditionTree], bindings: Optional[dict] = None) -> dict:
         """The journal's payload (`writes.condition_drafts.PAYLOAD_KEYS`)."""
         return {"current": node_to_dict(current), "pending": self.pending, "mentions": self.mentions,
                 "bindings": bindings or {}, "proposed": node_to_dict(self.tree),
-                "notes": self.notes, "errors": self.errors}
+                "notes": self.notes, "errors": self.errors, "definitions": self.definitions}
 
 
 Exchanges = Optional[list[model_exchange.ModelExchange]]
@@ -472,7 +501,7 @@ def prompt_values(ctx: InterpreterContext, role: str, instruction: str, errors:
         "role": ROLE_LABELS_FR[role], "forms": form_lines(), "entities": _lines(ctx.entity_lines),
         "tree_entities": _lines(ctx.lists["e"].lines), "facts": _lines(ctx.lists["f"].lines),
         "offers": _lines(ctx.lists["q"].lines), "skills": _lines(ctx.lists["s"].lines),
-        "attributes": _lines(ctx.lists["a"].lines),
+        "attributes": _lines(ctx.lists["a"].lines), "entity_types": _lines(ctx.type_lines),
         "current": json.dumps(ctx.current, ensure_ascii=False) if ctx.current is not None else "(aucune)",
         "instruction": instruction.strip(), "errors": _lines(f"- {e}" for e in errors),
     }
@@ -487,9 +516,13 @@ def _notes(raw: Any) -> list[str]:
     return notes
 
 
-def _settle(db: Session, world_id: str, reading: Reading, notes: list[str], retried: bool) -> Interpretation:
+def _settle(db: Session, world_id: str, reading: Reading, notes: list[str], retried: bool,
+            proposals: Optional[Proposals] = None) -> Interpretation:
+    proposals = proposals or Proposals()
+
     def done(outcome, tree=None, errors=()):
-        return Interpretation(outcome, tree, reading.pending, reading.mentions, notes, list(errors), retried)
+        return Interpretation(outcome, tree, reading.pending, reading.mentions, notes, list(errors), retried,
+                              proposals.entries())
 
     if reading.errors or reading.name_errors:
         return done("refused", errors=reading.errors + reading.name_errors)
@@ -497,25 +530,59 @@ def _settle(db: Session, world_id: str, reading: Reading, notes: list[str], retr
         return done("refused", errors=[] if notes else [NOTHING_PROPOSED_FR])
     if waiting(reading.pending):
         return done("needs_choice")
-    tree, errors = validate(db, world_id, reading.pending)
-    return done("proposed", tree) if tree is not None else done("refused", errors=errors)
+    tree, errors = validate(db, world_id, reading.pending, proposals.views())
+    if tree is None:
+        return done("refused", errors=errors)
+    return done("needs_choice" if proposals.near else "proposed", tree)
+
+
+@dataclass
+class Proposals:
+    """BRIEF-0113-E: the draft's unsaved attributes (`unsaved`), those this
+    answer proposes (`new`), and, for each new one, the attributes whose
+    name is near (`near`, by ref)."""
+
+    unsaved: tuple = ()
+    new: list = field(default_factory=list)
+    near: dict[str, list[dict]] = field(default_factory=dict)
+
+    def views(self) -> dict[str, AttributeView]:
+        return unsaved_views(tuple(self.unsaved) + tuple(self.new))
+
+    def entries(self) -> list[dict]:
+        return [{"ref": item.ref, "definition": spec_dict(item.spec), "near": self.near.get(item.ref, [])}
+                for item in self.new]
+
+
+def _answer(db: Session, world_id: str, parsed: dict, ctx: InterpreterContext, unsaved: tuple,
+            retried: bool) -> Interpretation:
+    """One answer read and settled: its `define` block first (the new
+    attributes join the context), then its condition."""
+    taken = {item.ref for item in unsaved}
+    new, defined, errors = read_definitions(db, world_id, parsed.get("define"), taken, list(unsaved))
+    ctx.attributes.update(unsaved_views(new))
+    reading = read_answer(db, world_id, parsed.get("condition"), ctx, defined)
+    reading.errors[:0] = errors
+    proposals = Proposals(unsaved=unsaved, new=new, near=near_existing(db, world_id, new, list(unsaved)))
+    return _settle(db, world_id, reading, _notes(parsed.get("unsupported")), retried, proposals)
 
 
 def interpret(
     db: Session, world_id: str, role: str, instruction: str, current: Optional[ConditionTree],
-    exchanges: Exchanges = None,
+    exchanges: Exchanges = None, unsaved: tuple = (),
 ) -> Interpretation:
     """II1: one call, and one more carrying the errors when code refused the
     first answer for anything but an unknown name. `OllamaError` and
-    `LlmParseError` propagate."""
-    ctx = build_context(db, world_id, instruction, current)
+    `LlmParseError` propagate. `unsaved`: the offer draft's proposed
+    attributes not saved yet (BRIEF-0113-E, WN2), shown to the model and
+    named by its leaves."""
+    ctx = build_context(db, world_id, instruction, current, unsaved)
     parsed = _call(db, prompt_values(ctx, role, instruction, []), exchanges)
-    result = _settle(db, world_id, read_answer(db, world_id, parsed.get("condition"), ctx),
-                     _notes(parsed.get("unsupported")), retried=False)
+    result = _answer(db, world_id, parsed, ctx, unsaved, retried=False)
     if result.outcome == "refused" and _retryable(result):
+        ctx = build_context(db, world_id, instruction, current, unsaved)
         parsed = _call(db, prompt_values(ctx, role, instruction, result.errors), exchanges)
-        result = _settle(db, world_id, read_answer(db, world_id, parsed.get("condition"), ctx),
-                         _notes(parsed.get("unsupported")), retried=True)
+        result = _answer(db, world_id, parsed, ctx, unsaved, retried=True)
     return result
 
 
@@ -527,10 +594,46 @@ def _retryable(result: Interpretation) -> bool:
 
 
 def resolve(db: Session, world_id: str, pending: dict, mentions: list[dict], notes: list[str],
-            bindings: dict[str, str]) -> Interpretation:
+            bindings: dict[str, str], definitions: tuple = (), unsaved: tuple = ()) -> Interpretation:
     """The creator's picks applied to a `needs_choice` proposal; no model
-    call. `ValueError` when a pick is missing or outside its choices."""
+    call. `ValueError` when a pick is missing or outside its choices. A
+    proposed attribute near another (BRIEF-0113-E, WK2) is picked by its
+    ref: `new` keeps it, an existing key moves its leaves there (`adopt`) --
+    a label that attribute does not have refuses the proposal. The adopted
+    one stays in `definitions`, marked `adopted` with its key."""
     bound = bind(pending, mentions, bindings)
-    tree, errors = validate(db, world_id, bound)
+    new, errors, adopted = [], [], []
+    for entry in definitions:
+        pick = bindings.get(entry["ref"])
+        if entry.get("adopted"):
+            adopted.append(entry)
+            continue
+        if entry.get("near") and pick != "new":
+            if pick not in {n["key"] for n in entry["near"]}:
+                raise ValueError(f"« {entry['definition']['name']} » : choisis un état existant ou « créer »")
+            try:
+                bound = adopt(db, world_id, bound, entry["ref"], pick, unsaved_views(unsaved))
+            except ValueError as exc:
+                errors.append(str(exc))
+            adopted.append({**entry, "adopted": pick})
+            continue
+        new.append(UnsavedAttribute(ref=entry["ref"], spec=spec_from_dict(entry["definition"])))
+    proposals = Proposals(unsaved=unsaved, new=new)
+    tree = None
+    if not errors:
+        tree, errors = validate(db, world_id, bound, proposals.views())
     outcome = "proposed" if tree is not None else "refused"
-    return Interpretation(outcome, tree, bound, mentions, list(notes), errors)
+    # An adopted proposal stays in the journal with the key it went to
+    # (the dashboard of TICKET-0115 counts them); no card shows it.
+    return Interpretation(outcome, tree, bound, mentions, list(notes), errors, False,
+                          proposals.entries() + adopted)
+
+
+def confirm(db: Session, world_id: str, proposed: Optional[dict], unsaved: tuple,
+            edited: tuple) -> tuple[Optional[ConditionTree], list[str]]:
+    """BRIEF-0113-E: the proposed tree checked again against the definitions
+    as the creator confirmed them (`edited`, perhaps retouched in the card)
+    and the draft's other unsaved ones. (tree, []) or (None, errors)."""
+    if proposed is None:
+        return None, []
+    return validate(db, world_id, proposed, unsaved_views(tuple(unsaved) + tuple(edited)))
diff --git a/src/world_engine/condition_text.py b/src/world_engine/condition_text.py
index ba9323a..b6de4eb 100644
--- a/src/world_engine/condition_text.py
+++ b/src/world_engine/condition_text.py
@@ -87,7 +87,13 @@ def _entity_name(db: Session, entity_id: Optional[str]) -> str:
     return entity.name if entity is not None else str(entity_id)
 
 
-def _target(db: Session, spec: RequirementSpec) -> str:
+def _view(db: Session, key: Optional[str], unsaved: Optional[dict]):
+    """The attribute `key` names -- an unsaved one the interpreter proposed
+    (TICKET-0113, BRIEF-0113-E), else a stored one."""
+    return (unsaved or {}).get(key) or view_of(db, key)
+
+
+def _target(db: Session, spec: RequirementSpec, unsaved: Optional[dict] = None) -> str:
     if spec.target_entity_id and spec.type != ATTRIBUTE_FORM:
         return _entity_name(db, spec.target_entity_id)
     if spec.type == "knowledge":
@@ -99,7 +105,7 @@ def _target(db: Session, spec: RequirementSpec) -> str:
         offer = db.get(QuestOffer, spec.target_key) if spec.target_key else None
         return offer.title if offer is not None else str(spec.target_key)
     if spec.type == ATTRIBUTE_FORM:
-        view = view_of(db, spec.target_key)
+        view = _view(db, spec.target_key, unsaved)
         return view.name if view is not None else str(spec.target_key)
     return str(spec.target_key or "")
 
@@ -110,7 +116,8 @@ def _subject(db: Session, spec: RequirementSpec) -> str:
     return _entity_name(db, spec.subject_entity_id)
 
 
-def leaf_text(db: Session, spec: RequirementSpec, viewer_id: Optional[str] = None) -> str:
+def leaf_text(db: Session, spec: RequirementSpec, viewer_id: Optional[str] = None,
+              unsaved: Optional[dict] = None) -> str:
     """One leaf in French. With `viewer_id` (a player surface), a fact the
     viewer does not know is not written out (A1)."""
     phrase = FORM_PHRASES_FR.get(spec.type)
@@ -120,8 +127,9 @@ def leaf_text(db: Session, spec: RequirementSpec, viewer_id: Optional[str] = Non
         phrase = HIDDEN_FACT_FR
     if spec.type == ATTRIBUTE_FORM and viewer_id is not None and _hidden(db, spec):
         phrase = HIDDEN_STATE_FR
-    value = _value(db, spec)
-    text = phrase.format(who=_subject(db, spec), target=_target(db, spec), threshold=spec.threshold, value=value)
+    value = _value(db, spec, unsaved)
+    text = phrase.format(who=_subject(db, spec), target=_target(db, spec, unsaved), threshold=spec.threshold,
+                         value=value)
     return text[0].upper() + text[1:]
 
 
@@ -130,12 +138,12 @@ def _hidden(db: Session, spec: RequirementSpec) -> bool:
     return view is None or view.hidden
 
 
-def _value(db: Session, spec: RequirementSpec) -> object:
+def _value(db: Session, spec: RequirementSpec, unsaved: Optional[dict] = None) -> object:
     """The French of what a leaf compares to: a form's value label, or an
     attribute's label, « N ou plus », an entity or « quelqu'un »."""
     if spec.type != ATTRIBUTE_FORM:
         return VALUE_LABELS_FR.get(spec.type, {}).get(spec.value, spec.value)
-    view = view_of(db, spec.target_key)
+    view = _view(db, spec.target_key, unsaved)
     if view is None:
         return spec.value or spec.threshold or ""
     if view.kind == "choice":
@@ -149,22 +157,23 @@ def _head(op: str, n: Optional[int]) -> str:
     return CONNECTOR_HEADS_FR[op].format(n=n)
 
 
-def describe(db: Session, node: Optional[ConditionTree]) -> list[dict]:
+def describe(db: Session, node: Optional[ConditionTree], unsaved: Optional[dict] = None) -> list[dict]:
     """The tree as lines: `{"depth", "text"}`, a connector before its
-    children. [] for no condition."""
+    children. [] for no condition. `unsaved`: the attributes the
+    interpreter proposed, by their `new:` key (BRIEF-0113-E)."""
     lines: list[dict] = []
     if node is not None:
-        _describe(db, node, 0, lines)
+        _describe(db, node, 0, lines, unsaved)
     return lines
 
 
-def _describe(db: Session, node: ConditionTree, depth: int, lines: list[dict]) -> None:
+def _describe(db: Session, node: ConditionTree, depth: int, lines: list[dict], unsaved: Optional[dict]) -> None:
     if node.op == "leaf":
-        lines.append({"depth": depth, "text": leaf_text(db, node.leaf)})
+        lines.append({"depth": depth, "text": leaf_text(db, node.leaf, unsaved=unsaved)})
         return
     lines.append({"depth": depth, "text": _head(node.op, node.n)})
     for child in node.children:
-        _describe(db, child, depth + 1, lines)
+        _describe(db, child, depth + 1, lines, unsaved)
 
 
 def _progress(verdict_node: VerdictNode, viewer_id: Optional[str] = None) -> Optional[str]:
diff --git a/src/world_engine/quest_reads.py b/src/world_engine/quest_reads.py
index 598c9b0..0d9e8ed 100644
--- a/src/world_engine/quest_reads.py
+++ b/src/world_engine/quest_reads.py
@@ -17,7 +17,7 @@ from typing import Optional
 
 from sqlmodel import Session, select
 
-from .attributes import AttributeView, world_attributes
+from .attributes import AttributeView, world_attributes, world_entity_type_labels
 from .condition_forms import FORM_VALUES
 from .condition_text import VALUE_LABELS_FR, describe, verdict_lines
 from .conditions import evaluate, flat_leaves, node_to_dict, read_condition
@@ -59,13 +59,15 @@ def _requirement_dict(req) -> dict:
             "subject_entity_id": req.subject_entity_id, "value": req.value}
 
 
-def condition_view(db: Session, tree) -> dict:
+def condition_view(db: Session, tree, unsaved: Optional[dict] = None) -> dict:
     """One condition as the editor reads it (TICKET-0111, T1): the tree
     itself, its leaves when it is flat (the list the editor edits; None when
-    it is not -- shown, sent back unchanged), and its French lines."""
+    it is not -- shown, sent back unchanged), and its French lines -- an
+    unsaved attribute the interpreter proposed named by `unsaved`
+    (TICKET-0113, BRIEF-0113-E)."""
     flat = flat_leaves(tree)
     return {"tree": node_to_dict(tree), "flat": None if flat is None else [_requirement_dict(r) for r in flat],
-            "lines": describe(db, tree)}
+            "lines": describe(db, tree, unsaved)}
 
 
 def _name(db: Session, entity_id: Optional[str]) -> Optional[str]:
@@ -153,6 +155,8 @@ def editor_choices(world_id: str, db: Session) -> dict:
         # read, and every active entity -- a leaf's fixed subject, an entity
         # value.
         "attributes": [attribute_choice(view) for view in world_attributes(db, world_id)],
+        # TICKET-0113 (BRIEF-0113-E): the types a proposed definition may name.
+        "entity_types": world_entity_type_labels(db, world_id),
         "entities": sorted(({"id": e.id, "name": e.name, "type": e.type} for e in db.exec(select(Entity).where(
             Entity.world_id == world_id, Entity.status == "active")).all()),
             key=lambda d: (d["name"].lower(), d["id"])),
diff --git a/src/world_engine/writes/condition_drafts.py b/src/world_engine/writes/condition_drafts.py
index 38d3635..c0aa8a7 100644
--- a/src/world_engine/writes/condition_drafts.py
+++ b/src/world_engine/writes/condition_drafts.py
@@ -22,7 +22,7 @@ fails as a `ValueError` naming the field rather than as an `IntegrityError`.
 from __future__ import annotations
 
 from datetime import UTC, datetime
-from typing import Any, Optional
+from typing import Any, Callable, Optional
 
 from fastapi.encoders import jsonable_encoder
 from sqlmodel import Session
@@ -40,9 +40,12 @@ CONDITION_DRAFT_MOVES: dict[str, tuple[str, ...]] = {
 # of `conditions.node_to_dict`, or None), the model's tree as code read it
 # with names still to pick (`pending`), the names it mentions and the picks
 # made, the tree code validated (`proposed`, dict form), the notes and the
-# errors shown to the creator.
+# errors shown to the creator; since TICKET-0113 (BRIEF-0113-E) the
+# attributes it proposed (`definitions`: `{ref, definition, near}`, and
+# once inserted `confirmed`, the definition as the creator confirmed it --
+# the dashboard of TICKET-0115 compares the two).
 PAYLOAD_KEYS: frozenset[str] = frozenset({
-    "current", "pending", "mentions", "bindings", "proposed", "notes", "errors",
+    "current", "pending", "mentions", "bindings", "proposed", "notes", "errors", "definitions",
 })
 WORLD_NAME_UNKNOWN = "(monde introuvable)"
 
@@ -99,11 +102,15 @@ def move_condition_draft(
 
 def mark_draft_saved(
     db: Session, *, world_id: str, draft_id: Optional[str], offer_id: str, tree: Optional[dict],
+    proposed_as_saved: Optional[Callable[[Optional[dict]], Optional[dict]]] = None,
 ) -> bool:
     """The offer `offer_id` was saved holding `tree` (dict form) where the
     creator inserted `draft_id`. True when the draft was marked; False --
     and nothing written -- when there is no such draft in `world_id`, or it
-    is not `inserted`."""
+    is not `inserted`. `proposed_as_saved` (TICKET-0113, BRIEF-0113-E): the
+    proposed tree as the save rewrote it -- its unsaved attributes' keys
+    and labels to the ids written -- so « as proposed » compares like with
+    like."""
     if not draft_id:
         return False
     draft = db.get(ConditionDraft, draft_id)
@@ -111,7 +118,10 @@ def mark_draft_saved(
         return False
     draft.outcome = "saved"
     draft.offer_ref = offer_id
-    draft.saved_as_proposed = jsonable_encoder(tree) == draft.payload.get("proposed")
+    proposed = draft.payload.get("proposed")
+    if proposed_as_saved is not None:
+        proposed = proposed_as_saved(proposed)
+    draft.saved_as_proposed = jsonable_encoder(tree) == proposed
     draft.decided_at = datetime.now(UTC)
     db.add(draft)
     return True
diff --git a/src/world_engine/writes/conditions.py b/src/world_engine/writes/conditions.py
index 0994987..6d7e645 100644
--- a/src/world_engine/writes/conditions.py
+++ b/src/world_engine/writes/conditions.py
@@ -131,14 +131,18 @@ def _clean_value(where: str, req: RequirementSpec) -> Optional[str]:
     return req.value
 
 
-def _clean_attribute(db: Session, world_id: str, where: str, req: RequirementSpec) -> RequirementSpec:
+def _clean_attribute(db: Session, world_id: str, where: str, req: RequirementSpec,
+                     unsaved: Optional[dict] = None) -> RequirementSpec:
     """An `attribute` leaf (TICKET-0113, WG1): `target_key` an active
     attribute of the world -- a definition or a system key --, a fixed
     subject of a type it applies to; a `choice` compares to one of its
     choices (`value`), an `integer` to `threshold` (any integer), an
     `entity` to `target_entity_id` -- an entity of a type its value may
-    name -- or, with none, to anyone."""
-    view = attribute_view(db, world_id, req.target_key)
+    name -- or, with none, to anyone. `unsaved` (TICKET-0113, BRIEF-0113-E):
+    the attributes the interpreter proposed and the creator has not saved
+    yet, by their `new:` key -- validated by the same rules, never written
+    by `write_condition`, which passes none."""
+    view = (unsaved or {}).get(req.target_key) or attribute_view(db, world_id, req.target_key)
     if view is None or view.status != "active":
         raise ValueError(f"{where}unknown attribute {req.target_key!r}")
     if req.subject_entity_id is not None and not applies_to(view, db.get(Entity, req.subject_entity_id).type):
@@ -163,7 +167,8 @@ def _clean_attribute(db: Session, world_id: str, where: str, req: RequirementSpe
     )
 
 
-def clean_leaf(db: Session, world_id: str, req: RequirementSpec, where: str = "") -> RequirementSpec:
+def clean_leaf(db: Session, world_id: str, req: RequirementSpec, where: str = "",
+               unsaved: Optional[dict] = None) -> RequirementSpec:
     """One leaf as it will be stored: the arguments its form uses, nothing
     else. `where` prefixes every error (« write_day_plan: step 2 »).
     Raises `ValueError` on any violation."""
@@ -171,7 +176,7 @@ def clean_leaf(db: Session, world_id: str, req: RequirementSpec, where: str = ""
         raise ValueError(f"{where}unknown requirement type {req.type!r}")
     _clean_subject(db, world_id, where, req)
     if req.type == ATTRIBUTE_FORM:
-        return _clean_attribute(db, world_id, where, req)
+        return _clean_attribute(db, world_id, where, req, unsaved)
     target_entity_id, target_key = _clean_target(db, world_id, where, req)
     return RequirementSpec(
         type=req.type, subject_role=req.subject_role, subject_entity_id=req.subject_entity_id,
@@ -181,7 +186,7 @@ def clean_leaf(db: Session, world_id: str, req: RequirementSpec, where: str = ""
 
 
 def clean_condition(
-    db: Session, world_id: str, tree: Optional[ConditionTree], where: str = "",
+    db: Session, world_id: str, tree: Optional[ConditionTree], where: str = "", unsaved: Optional[dict] = None,
 ) -> Optional[ConditionTree]:
     """A whole tree, shape first then every leaf, before any write. None is
     no condition. Raises `ValueError` (a `ConditionShapeError` is one)."""
@@ -191,13 +196,15 @@ def clean_condition(
         check_shape(tree)
     except ValueError as exc:
         raise ValueError(f"{where}{exc}") from exc
-    return _clean_tree(db, world_id, tree, where)
+    return _clean_tree(db, world_id, tree, where, unsaved)
 
 
-def _clean_tree(db: Session, world_id: str, tree: ConditionTree, where: str) -> ConditionTree:
+def _clean_tree(db: Session, world_id: str, tree: ConditionTree, where: str,
+                unsaved: Optional[dict] = None) -> ConditionTree:
     if tree.op == "leaf":
-        return ConditionTree(op="leaf", leaf=clean_leaf(db, world_id, tree.leaf, where))
-    return ConditionTree(op=tree.op, n=tree.n, children=tuple(_clean_tree(db, world_id, c, where) for c in tree.children))
+        return ConditionTree(op="leaf", leaf=clean_leaf(db, world_id, tree.leaf, where, unsaved))
+    return ConditionTree(op=tree.op, n=tree.n,
+                         children=tuple(_clean_tree(db, world_id, c, where, unsaved) for c in tree.children))
 
 
 def write_condition(db: Session, *, world_id: str, role: str, tree: Optional[ConditionTree], **owner) -> Optional[Condition]:
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index a3fe621..8a247db 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19188,6 +19188,43 @@ variable `attributes`. One single source: the two cannot diverge. A new
 text is looked for before its old one, since an old fragment may stand
 inside its new text.
 
+## THE INTERPRETER PROPOSES A STATE THE WORLD LACKS (TICKET-0113) -- THE DEFINITION AND THE CONDITION CONFIRMED TOGETHER, A NEAR NAME PICKED, BOTH WRITTEN BY THE OFFER'S SAVE (BRIEF-0113-e, no schema change)
+
+**WK2.** A state the `a` list lacks is no longer a dead end: the model
+proposes its definition in its answer's `define` block (name, kind, the
+types it applies to, labels and default, an entity's value types, hidden
+or not) and the condition names it `{"define": ...}`. Code cleans it with
+the writer's own `clean_definition`; refused, it goes back to the model once
+with its error (II1). The definition joins the condition's proposal as a
+card the creator reads, retouches in the same `AttributeDefinitionForm` as
+Création › États, and confirms with « Insérer » -- the condition checked
+again against what she confirmed. Never a duplicate unseen: a proposed
+name near an existing attribute's or another proposal's
+(`attributes.near_attributes`, `lore_resolve.near_ratio`) makes the
+proposal `needs_choice`; she uses the existing one -- the leaves move onto
+it, a label read back to its choice, refused if it has no such label -- or
+creates this one. The tool never picks (0092).
+
+**WN2.** Until « Enregistrer », a proposed definition is UNSAVED: it lives
+in the offer draft (`unsaved_attributes`), keyed `new:<ref>`, sent with
+every interpreter request -- the model sees it, a later sentence may name
+it -- and every condition naming it is validated against it by
+`clean_leaf(..., unsaved=...)`; `write_condition` passes none, so no `new:`
+key is ever stored. The offer's save (`attribute_proposals.materialize`)
+writes each definition a condition still names through
+`write_attribute_definition`, in the offer's transaction, before the
+conditions, rewritten to the ids written; one no condition names is not
+written. The journal keeps each proposal (`definitions`: proposed, and
+`confirmed` or `adopted`), and « saved as proposed » compares the saved
+tree with the proposal rewritten the same way.
+
+**Rejected.** WK1 (the interpreter only names the missing state and sends
+the creator to États; reactivation: none -- A1 of the series). WN1 (« Insérer »
+writes the definition at once: two transactions, an abandoned offer
+leaving a definition behind). Adding a missing label to an existing
+attribute from the interpreter: deferred (reactivation: the journal shows
+proposals refused because the existing attribute lacks the label).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/attribute_interpreter.py b/tooling/verify/checks/attribute_interpreter.py
index da6b7ea..c9c17d6 100644
--- a/tooling/verify/checks/attribute_interpreter.py
+++ b/tooling/verify/checks/attribute_interpreter.py
@@ -36,6 +36,34 @@ AD4 -- delivery (`scripts/apply_ticket_0113_condition_prompt.py`, fixture
    run prints « unchanged » and writes nothing; on a head whose text lost
    one fragment, the others are applied and the lost one is reported.
 
+AE1 -- the shape (BRIEF-0113-E, static and import). The journal's
+   `PAYLOAD_KEYS` hold `definitions`; the head declares `entity_types`;
+   applying every fragment to the seed's texts changes nothing (no fragment
+   touches another's); `write_condition` cleans its tree with no unsaved
+   attribute; the offer body carries `unsaved_attributes`; the editor sends
+   them (`questOffers.svelte.js`), passes them to every condition
+   (`QuestOffers.svelte`) and the interpreter (`ConditionEditor.svelte`),
+   whose card renders `<AttributeDefinitionForm` and sends the confirmed
+   `definitions` with `inserted`.
+AE2 -- proposing (fixture, `condition_interpreter.chat` stubbed). An answer
+   defining « Ouverte » (a choice for places) whose leaf names it by
+   `{"define": ...}` is `proposed`, the leaf on `new:n1` with its label, the
+   definition listed with no near attribute and named in the French lines;
+   a definition « maudite » is `needs_choice` with « Maudit » near; picking
+   « Maudit » moves the leaf onto it, its label read back to its choice,
+   the proposal kept as `adopted` with its key;
+   picking `new` keeps the definition; a definition the writer refuses is
+   refused, then retried with its error; a draft's unsaved attribute is
+   listed in `a` and named by its code.
+AE3 -- confirming and saving (route functions). `inserted` with the
+   definition retouched keeps both forms in the journal (`confirmed`);
+   with a definition whose labels no longer hold the leaf, 422 and nothing
+   moves. Saving the offer with the unsaved attribute writes it once, the
+   condition stored on its id and its choice's id, the draft `saved` as
+   proposed; an unsaved attribute no condition names is not written; a
+   condition naming one the body does not carry answers 422 and writes
+   nothing.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
@@ -371,6 +399,210 @@ def check_ad4() -> None:
         fail(f"AD4: an edited head gave v{number}: {result.stdout.strip()[-300:]}")
 
 
+# --- AE1 -------------------------------------------------------------------------
+
+def check_ae1() -> None:
+    import ast
+
+    import seed_pilot
+
+    from world_engine.cockpit.routes.quests import OfferBody
+    from world_engine.writes.condition_drafts import PAYLOAD_KEYS
+
+    if "definitions" not in PAYLOAD_KEYS:
+        fail(f"AE1: PAYLOAD_KEYS is {sorted(PAYLOAD_KEYS)}")
+    if "entity_types" not in seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS[0]["variables"]:
+        fail("AE1: the head does not declare entity_types")
+    for field, text in (("system_prompt", seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT),
+                        ("user_template", seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE)):
+        if seed_pilot.with_condition_fragments(field, text) != text:
+            fail(f"AE1: applying the fragments to the seed's {field} changes it: one fragment touches another")
+    tree = ast.parse((ROOT / "src" / "world_engine" / "writes" / "conditions.py").read_text(encoding="utf-8"))
+    write = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "write_condition"), None)
+    calls = [c for c in ast.walk(write) if isinstance(c, ast.Call) and getattr(c.func, "id", "") == "clean_condition"] \
+        if write else []
+    if len(calls) != 1 or calls[0].keywords:
+        fail("AE1: write_condition does not clean its tree with no unsaved attribute")
+    if "unsaved_attributes" not in OfferBody.model_fields:
+        fail("AE1: OfferBody carries no unsaved_attributes")
+    front = ROOT / "frontend" / "src" / "creation"
+    needles = {
+        "questOffers.svelte.js": ("unsaved_attributes: draft.unsavedAttributes",),
+        "QuestOffers.svelte": ("unsaved={draft.unsavedAttributes}",),
+        "ConditionEditor.svelte": ("<ConditionInterpreter {cond} {role} {unsaved}", "withUnsaved(choices, unsaved)"),
+        "ConditionInterpreter.svelte": ("<AttributeDefinitionForm",),
+        "conditionInterpreter.svelte.js": ("decide(state, 'inserted', { definitions",),
+    }
+    for name, wanted in needles.items():
+        text = (front / name).read_text(encoding="utf-8") if (front / name).exists() else ""
+        for needle in wanted:
+            if needle not in text:
+                fail(f"AE1: {name} lacks {needle}")
+    if (front / "QuestOffers.svelte").read_text(encoding="utf-8").count("unsaved={draft.unsavedAttributes}") != 3:
+        fail("AE1: QuestOffers.svelte does not pass the unsaved attributes to its three conditions")
+
+
+# --- AE2 -------------------------------------------------------------------------
+
+def _define(ref, name, kind="choice", for_=("location",), choices=("non", "oui"), default="non"):
+    return {"ref": ref, "name": name, "kind": kind, "for": list(for_), "choices": list(choices),
+            "default": default, "hidden": False}
+
+
+def _parsed(condition, define=()) -> str:
+    return json.dumps({"condition": condition, "unsupported": [], "define": list(define)}, ensure_ascii=False)
+
+
+def _open_leaf():
+    return {"op": "leaf", "form": "attribute", "subject": {"name": "Crypte", "kind": "place"},
+            "target": {"define": "d1"}, "threshold": None, "value": "oui"}
+
+
+def check_ae2(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine import condition_interpreter as ci
+    from world_engine.attribute_proposals import UnsavedAttribute
+    from world_engine.conditions import node_to_dict
+    from world_engine.quest_reads import condition_view
+    from world_engine.attribute_proposals import unsaved_views, spec_from_dict
+    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec
+
+    with Session(engine) as db:
+        _seed_prompt(db)
+        result, _ = _run(ci, db, ids, [_parsed({"op": "all", "children": [_open_leaf()]},
+                                                [_define("d1", "Ouverte")])])
+        leaf = node_to_dict(result.tree)["children"][0] if result.tree else {}
+        defs = result.definitions
+        if result.outcome != "proposed" or leaf.get("target_key") != "new:n1" or leaf.get("value") != "oui" \
+                or len(defs) != 1 or defs[0]["near"] or defs[0]["definition"]["name"] != "Ouverte":
+            fail(f"AE2: a defined state gave {result.outcome}, {leaf}, {defs}, {result.errors}")
+        else:
+            views = unsaved_views([UnsavedAttribute(ref=d["ref"], spec=spec_from_dict(d["definition"])) for d in defs])
+            lines = " ".join(l["text"] for l in condition_view(db, result.tree, views)["lines"])
+            if "Ouverte : oui" not in lines:
+                fail(f"AE2: the French lines read {lines!r}")
+        cursed = {"op": "leaf", "form": "attribute", "subject": "doer", "target": {"define": "d1"},
+                  "threshold": None, "value": "oui"}
+        near_answer = _parsed({"op": "all", "children": [cursed]},
+                              [_define("d1", "maudite", for_=("character",))])
+        result, _ = _run(ci, db, ids, [near_answer])
+        near = result.definitions[0]["near"] if result.definitions else []
+        if result.outcome != "needs_choice" or ids["maudit"] not in [n["key"] for n in near]:
+            fail(f"AE2: a near name gave {result.outcome}, near {near}")
+        else:
+            oui = _choice(db, ids["world"], ids["maudit"], "oui")
+            used = ci.resolve(db, ids["world"], result.pending, result.mentions, result.notes,
+                              {"n1": ids["maudit"]}, tuple(result.definitions))
+            moved = node_to_dict(used.tree)["children"][0] if used.tree else {}
+            if used.outcome != "proposed" or (moved.get("target_key"), moved.get("value")) != (ids["maudit"], oui) \
+                    or [d.get("adopted") for d in used.definitions] != [ids["maudit"]]:
+                fail(f"AE2: picking Maudit gave {used.outcome}, {moved}, {used.definitions}")
+            kept = ci.resolve(db, ids["world"], result.pending, result.mentions, result.notes, {"n1": "new"},
+                              tuple(result.definitions))
+            if kept.outcome != "proposed" or len(kept.definitions) != 1:
+                fail(f"AE2: creating it gave {kept.outcome}, {kept.definitions}")
+        bad = _parsed({"op": "all", "children": [_open_leaf()]}, [_define("d1", "Ouverte", choices=("oui",),
+                                                                           default="oui")])
+        good = _parsed({"op": "all", "children": [_open_leaf()]}, [_define("d1", "Ouverte")])
+        result, stub = _run(ci, db, ids, [bad, good])
+        second = stub.messages[1][1]["content"] if len(stub.messages) == 2 else ""
+        if result.outcome != "proposed" or not result.retried or "at least two labels" not in second:
+            fail(f"AE2: a refused definition gave {result.outcome}, retried {result.retried}")
+        unsaved = (UnsavedAttribute(ref="n1", spec=DefinitionSpec(
+            name="Brisé", kind="choice", holder_types=("item",), choices=(ChoiceSpec("non"), ChoiceSpec("oui")),
+            default="non")),)
+        ctx = ci.build_context(db, ids["world"], "x", None, unsaved)
+        code = next((c for c, key in ctx.lists["a"].codes.items() if key == "new:n1"), None)
+        broken = {"op": "leaf", "form": "attribute", "subject": {"name": "Trône de fer", "kind": "object"},
+                  "target": {"code": code}, "threshold": None, "value": "oui"}
+        stub, original = _Stub([_parsed({"op": "all", "children": [broken]})]), ci.chat
+        ci.chat = stub
+        try:
+            result = ci.interpret(db, ids["world"], "eligibility", "Le trône est brisé", None, [], unsaved)
+        finally:
+            ci.chat = original
+        leaf = node_to_dict(result.tree)["children"][0] if result.tree else {}
+        if code is None or "à créer" not in " ".join(ctx.lists["a"].lines) or result.outcome != "proposed" \
+                or leaf.get("target_key") != "new:n1":
+            fail(f"AE2: a draft's unsaved attribute gave {code}, {result.outcome}, {leaf}, {result.errors}")
+
+
+# --- AE3 -------------------------------------------------------------------------
+
+def check_ae3(engine, ids: dict) -> None:
+    from fastapi import HTTPException
+    from sqlmodel import Session, func, select
+
+    from world_engine import condition_interpreter as ci
+    from world_engine.cockpit.routes import attributes as attr_routes
+    from world_engine.cockpit.routes import conditions as routes
+    from world_engine.cockpit.routes import quests
+    from world_engine.models import AttributeDefinition, ConditionDraft, ConditionNode, World
+
+    def unsaved(ref, name, labels=("non", "oui")):
+        return attr_routes.UnsavedBody(ref=ref, definition=attr_routes.DefinitionBody(
+            name=name, kind="choice", holder_types=["location"], default=labels[0],
+            choices=[attr_routes.ChoiceBody(label=l) for l in labels]))
+
+    def count(model) -> int:
+        return db.exec(select(func.count()).select_from(model)).one()
+
+    with Session(engine) as db:
+        _seed_prompt(db)
+        db.get(World, ids["world"]).is_active = True
+        db.commit()
+        stub, original = _Stub([_parsed({"op": "all", "children": [_open_leaf()]}, [_define("d1", "Ouverte")])]), ci.chat
+        ci.chat = stub
+        try:
+            answer = routes.interpret(routes.InterpretBody(instruction="La crypte est ouverte", role="eligibility"),
+                                      db=db)
+        finally:
+            ci.chat = original
+        draft_id = answer["draft_id"]
+        try:
+            routes.decide(draft_id, routes.DecisionBody(decision="inserted", definitions=[
+                unsaved("n1", "Ouverte", ("fermée", "ouverte"))]), db=db)
+            fail("AE3: a definition whose labels no longer hold the leaf was accepted")
+        except HTTPException as exc:
+            if exc.status_code != 422 or db.get(ConditionDraft, draft_id).outcome != "proposed":
+                fail(f"AE3: a broken confirmation answered {exc.status_code}")
+        routes.decide(draft_id, routes.DecisionBody(decision="inserted", definitions=[unsaved("n1", "Ouvert")]),
+                      db=db)
+        stored = db.get(ConditionDraft, draft_id).payload["definitions"][0]
+        if stored["definition"]["name"] != "Ouverte" or stored.get("confirmed", {}).get("name") != "Ouvert":
+            fail(f"AE3: the journal keeps {stored}")
+        before = (count(AttributeDefinition), count(ConditionNode))
+        tree = answer["view"]["tree"]
+        step = [quests.OfferStepBody(objective="Entrer", cost=1)]
+        orphan = quests.OfferBody(giver_entity_id=ids["garde"], title="Orpheline", eligibility={
+            "op": "all", "children": [{**tree["children"][0], "target_key": "new:n9"}]},
+            unsaved_attributes=[unsaved("n1", "Ouvert")], steps=step)
+        try:
+            quests.create_offer(orphan, db=db)
+            fail("AE3: a condition naming an attribute the body does not carry was saved")
+        except HTTPException as exc:
+            if exc.status_code != 422 or (count(AttributeDefinition), count(ConditionNode)) != before:
+                fail(f"AE3: an orphan key answered {exc.status_code} or wrote rows")
+        body = quests.OfferBody(giver_entity_id=ids["garde"], title="La crypte", eligibility=tree,
+                                eligibility_draft_id=draft_id, steps=step,
+                                unsaved_attributes=[unsaved("n1", "Ouvert"), unsaved("n2", "Inutile")])
+        saved = quests.create_offer(body, db=db)
+        made = db.exec(select(AttributeDefinition).where(AttributeDefinition.name == "Ouvert")).all()
+        if len(made) != 1 or db.exec(select(AttributeDefinition).where(AttributeDefinition.name == "Inutile")).first():
+            fail(f"AE3: the save wrote {[d.name for d in made]} (and Inutile?)")
+        else:
+            leaf = saved["eligibility"]["tree"]["children"][0]
+            oui = _choice(db, ids["world"], made[0].id, "oui")
+            if (leaf["target_key"], leaf["value"]) != (made[0].id, oui):
+                fail(f"AE3: the saved leaf is {leaf}")
+        draft = db.get(ConditionDraft, draft_id)
+        if (draft.outcome, draft.saved_as_proposed) != ("saved", True):
+            fail(f"AE3: the draft reads {draft.outcome}, {draft.saved_as_proposed}")
+        db.get(World, ids["world"]).is_active = False
+        db.commit()
+
+
 def main() -> int:
     _fresh_db()
     from world_engine.db import create_db_and_tables, engine
@@ -378,7 +610,9 @@ def main() -> int:
     create_db_and_tables()
     ids = _world(engine)
     for name, rule in (("AD1", check_ad1), ("AD2", lambda: check_ad2(engine, ids)),
-                       ("AD3", lambda: check_ad3(engine, ids)), ("AD4", check_ad4)):
+                       ("AD3", lambda: check_ad3(engine, ids)), ("AD4", check_ad4),
+                       ("AE1", check_ae1), ("AE2", lambda: check_ae2(engine, ids)),
+                       ("AE3", lambda: check_ae3(engine, ids))):
         try:
             rule()
         except Exception as exc:  # a crash is that rule's failure, never a pass
@@ -388,8 +622,9 @@ def main() -> int:
             print(f"FAIL: {msg}")
         return 1
     print("PASS: attribute_interpreter -- the interpreter shows the model every attribute by code, writes "
-          "an attribute leaf by label, threshold or name and reads it back, and its prompt is delivered "
-          "fragment by fragment, keeping the creator's edits")
+          "an attribute leaf by label, threshold or name and reads it back, proposes a missing state the "
+          "creator confirms -- a near one picked, never duplicated -- written with the offer's save, and its "
+          "prompt is delivered fragment by fragment, keeping the creator's edits")
     return 0
 
 
diff --git a/tooling/verify/checks/condition_interpreter.py b/tooling/verify/checks/condition_interpreter.py
index ed2d63b..18b1c2d 100644
--- a/tooling/verify/checks/condition_interpreter.py
+++ b/tooling/verify/checks/condition_interpreter.py
@@ -118,7 +118,9 @@ ND3 -- saving the offer (fixture). An offer saved with its eligibility as
    the save whole and the `proposed` draft unmoved.
 
 NE1 -- the editor (BRIEF-0112-E; static). `ConditionEditor.svelte` renders
-   `<ConditionInterpreter {cond} {role} />`; `QuestOffers.svelte` passes
+   `<ConditionInterpreter {cond} {role}` (with the draft's unsaved
+   attributes since TICKET-0113, `attribute_interpreter.py` AE1);
+   `QuestOffers.svelte` passes
    `role="eligibility"`, `"prerequisite"` and `"completion"`, one each.
    `conditionInterpreter.svelte.js` POSTs `/api/conditions/interpret` with
    `current: conditionBody(cond)` and `attempt_id: state.attemptId`,
@@ -393,7 +395,7 @@ def check_nb1() -> None:
 
 def _payload(**over) -> dict:
     base = {"current": None, "pending": None, "mentions": [], "bindings": {}, "proposed": None,
-            "notes": [], "errors": []}
+            "notes": [], "errors": [], "definitions": []}
     base.update(over)
     return base
 
@@ -1143,7 +1145,7 @@ def _front(name: str) -> str:
 
 def check_ne1() -> None:
     editor = _front("ConditionEditor.svelte")
-    if "<ConditionInterpreter {cond} {role} />" not in editor:
+    if "<ConditionInterpreter {cond} {role} " not in editor:
         fail("NE1: ConditionEditor.svelte does not render the interpreter with its role")
     offers = _front("QuestOffers.svelte")
     for role in ("eligibility", "prerequisite", "completion"):
@@ -1151,11 +1153,11 @@ def check_ne1() -> None:
             fail(f"NE1: QuestOffers.svelte does not pass role={role!r} to one ConditionEditor")
     state = _front("conditionInterpreter.svelte.js")
     for needle in ("'/api/conditions/interpret'", "current: conditionBody(cond)", "attempt_id: state.attemptId",
-                   "'/resolve'", "bindings: state.picks", "'/decision'", "decide(state, 'discarded')"):
+                   "'/resolve'", "{ ...state.picks }", "'/decision'", "decide(state, 'discarded')"):
         if needle not in state:
             fail(f"NE1: conditionInterpreter.svelte.js lacks {needle!r}")
     body = state[state.find("export async function insertProposal"):]
-    inserted, assigned = body.find("decide(state, 'inserted')"), body.find(
+    inserted, assigned = body.find("decide(state, 'inserted'"), body.find(
         "Object.assign(cond, conditionDraft(proposal.view), { draftId: proposal.draft_id })")
     if inserted < 0 or assigned < 0 or assigned < inserted:
         fail("NE1: insertProposal does not record `inserted` before it fills the condition")
````

2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. Regenerate: `python tooling/glue/gen_decisions_index.py`.
4. Regenerate: `python tooling/glue/gen_file_map.py`.
5. Commit as one commit: `BRIEF-0113-E: the interpreter proposes a missing state -- confirmed with its condition, written by the offer's save`.

## Scope OUT

- Writing a definition at « Insérer » (WN1, rejected): only the offer's save writes.
- Adding a missing label to an existing attribute from the interpreter (deferred; the proposal is refused with its labels).
- Proposing a value for an entity (the panel's job, C).
- The acceptance-rate dashboard reading `definitions` (TICKET-0115).

## Invariants to defend

**Creator control is structural** -- nothing is written before « Enregistrer »; the save writes the definitions and the offer in one transaction through `write_attribute_definition` and `write_quest_offer` (AE3). **One validation** -- a proposed definition is cleaned by `clean_definition`, a leaf naming it by `clean_leaf(..., unsaved=...)`; `write_condition` never stores a `new:` key. **Name resolution never picks** -- a near attribute waits for her pick (AE2). **The journal never fails her save** (`_mark_drafts`). **One mount mechanism** -- the card is a child of `ConditionInterpreter.svelte`; the form is C's.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain (R-21 aside).
- A named mutation does not turn its rule red.
- A `new:` key would reach `condition_node` (any check or manual test showing one).
- `creation_island.py`, `page_contract.py` or `effect_self_write.py` turns red.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `npm run build` names a different asset hash than the prototype's: commit what it builds (`frontend_build_fresh.py` judges the manifest, not the name).

REPORT-ONLY:
- Timing of the corpus run; a check that times out under load and passes when rerun alone (name it).
- `lore_usage.py` U12c red between 20:00 and 24:00 Toronto (`--since` from a local date against UTC rows, R-21): pre-existing on `main`; rerun after midnight or name it. Never fixed here.
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.
- A `condition_draft` row of TICKET-0112 has no `definitions` key: readers use `.get("definitions") or []`; never backfill the journal.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/attribute_interpreter.py` -> `PASS: attribute_interpreter -- the interpreter shows the model every attribute by code, writes an attribute leaf by label, threshold or name and reads it back, proposes a missing state the creator confirms -- a near one picked, never duplicated -- written with the offer's save, and its prompt is delivered fragment by fragment, keeping the creator's edits`
- `condition_interpreter.py`, `conditions.py`, `quests.py`, `attributes.py`, `attribute_conditions.py`, `creation_island.py`, `page_contract.py`, `effect_self_write.py`, `frontend_build_fresh.py`, `module_budget.py`, `function_length.py`, `file_map.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`attribute_interpreter.py` exits 1 with the rule named):
  - in `frontend/src/creation/questOffers.svelte.js`, `    unsaved_attributes: draft.unsavedAttributes.map((u) => ({ ref: u.ref, definition: u.definition })),` -> `(removed)` -> `AE1`
  - in `src/world_engine/attribute_proposals.py`, `        if near:` -> `        if False:` -> `AE2`
  - in `src/world_engine/condition_interpreter.py`, `                bound = adopt(db, world_id, bound, entry["ref"], pick, unsaved_views(unsaved))` -> `                pass` -> `AE2`
  - in `src/world_engine/cockpit/routes/quests.py`, `                             proposed_as_saved=as_saved)` -> `                             proposed_as_saved=None)` -> `AE3`
  - in `src/world_engine/attribute_proposals.py`, `    for key in sorted(named):` -> `    for key in sorted(items):` -> `AE3`
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 150/150 (outside 20:00-24:00 Toronto, R-21).
- Live, by Nia, after the three scripts (TICKET-0113, Live): the ticket's live criteria.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

No schema change (`condition_draft.payload` gains a key, JSON already allowlisted). Decision entry « THE INTERPRETER PROPOSES A STATE THE WORLD LACKS (TICKET-0113) -- THE DEFINITION AND THE CONDITION CONFIRMED TOGETHER, A NEAR NAME PICKED, BOTH WRITTEN BY THE OFFER'S SAVE (BRIEF-0113-e, no schema change) » -- in the diff.
