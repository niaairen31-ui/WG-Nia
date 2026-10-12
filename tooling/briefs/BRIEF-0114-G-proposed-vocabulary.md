<!-- slug: proposed-vocabulary -->
# BRIEF 0114-G — "The interpreter proposes a missing event type or sorte -- created from its card, then bound to the leaf"

Lot: LOT-0114-event-journal.md (authoritative on conflict)
Depends on: BRIEF-0114-F (C-09), BRIEF-0114-B (C-04)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0114-F's commit).

- `src/world_engine/writes/condition_drafts.py:47` -> `PAYLOAD_KEYS: frozenset[str] = frozenset({`, its keys ending `"definitions",`
- `src/world_engine/condition_interpreter.py:636` -> `def resolve(db: Session, world_id: str, pending: dict, mentions: list[dict], notes: list[str],`
- `src/world_engine/interpreter_events.py:75` -> `def read_event(raw: dict, out: dict, view: Optional[EventTypeView], sortes: dict[str, str],`
- `frontend/src/creation/EventTypeForm.svelte` -> `let { draft, vocab } = $props();`
- No `src/world_engine/event_proposals.py`.

## Facts carried

### R-09 — the vocabulary helpers TICKET-0113 left
Opened: `src/world_engine/lore_resolve.py:73` (`normalize_surface`:
case- and accent-blind), `:186` (`near_ratio`);
`src/world_engine/attributes.py:129` (`world_entity_types`), `:274`
(`near_attributes`, the near-name precedent).
Consequence: a type's or sorte's name is compared with
`normalize_surface` in Python (SQLite's `lower()` is not accent-blind),
near names by `near_ratio`.

### R-11 — the interpreter and its prompt (0112, 0113)
Opened: `src/world_engine/condition_interpreter.py` (`TARGET_HINTS_FR`,
`CODE_LISTS`, `InterpreterContext`, `build_context`, `encode`, `_leaf`,
`bind`, `validate`, `Interpretation`, `resolve`, `:570` `interpret`);
`scripts/seed_pilot.py` (`CONDITION_INTERPRET_FRAGMENTS`,
`with_condition_fragments`, the 0112 texts, `:132`
`upsert_prompt_template`, S2); `scripts/apply_ticket_0113_condition_prompt.py`
(`apply_fragments`, `HEAD`); `src/world_engine/writes/condition_drafts.py`
(`PAYLOAD_KEYS`, exact); `tooling/verify/checks/attribute_interpreter.py`
AD1 (each fragment's old text once in the 0112 text, none touching
another).
Consequence: F adds three fragments whose old texts stand once in the
0112 text; the 0113 delivery applies them too (it reads the one tuple),
F's script reuses its `apply_fragments`. G adds `vocabulary` to
`PAYLOAD_KEYS`.

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

### C-09 — the interpreter's `t` list and the leaf in the model's form
Produced by: BRIEF-0114-F   Consumed by: G, H
`CODE_LISTS["event"] = "t"`; `InterpreterContext.event_types` (id ->
view), `.sortes` (id -> name); `interpreter_events.event_type_line(view,
types)` (« Chasse (rôles : Chasseur — personnage ; Proie — personnage ou
une sorte ; compte une quantité) »), `encode_event`, `read_event`,
`filters_waiting`, `bind_filters`. Model leaf: `{"op": "leaf", "form":
"event", "subject", "target": {"code": "t1"}, "value": a role's name |
null, "threshold", "place": {"name", "kind"} | null, "since", "with":
[{"role", "sorte"} | {"role", "name", "kind"} | {"role", "code"}]}`.
Prompt variables `event_types`, `sortes`; three fragments of
`CONDITION_INTERPRET_FRAGMENTS`.

### C-10 — proposed types and sortes
Produced by: BRIEF-0114-G   Consumed by: H
`event_proposals.type_spec(raw) -> EventTypeSpec` (model form: name,
domain (unknown -> `other`), roles [{name, for, sorte}], quantity,
chronicle, secret); `type_definition(spec) -> dict` (`typeDraft`'s
form); `read_vocabulary(db, world_id, types_raw, sortes_raw) ->
Vocabulary(proposals [{ref v1.. | o1.., kind, definition, near}], refs,
errors)` -- a name the world has binds silently; `bind_vocabulary(db,
world_id, pending, bindings) -> (pending, errors)` (`ValueError` on a
missing or foreign pick); `vocab_waiting(leaf)`. Pending leaf keys
`type_define`, `role_name`, a filter's `sorte_define` / `role_name`.
`Interpretation.vocabulary`; `PAYLOAD_KEYS` gains `vocabulary`;
`resolve(..., vocabulary=())`; the route answers `vocabulary`.

## Context

R1's second half: when the sentence speaks of an event no type says, or of a sorte the world lacks, the model proposes it and its leaf names it by ref; the proposal waits. The creator uses a near one, or creates the proposed one -- a type retouched in B's `EventTypeForm` -- through B's routes; « Appliquer les choix » binds each ref to the id she chose and only then reads the leaf's role names on that type. Drafting decision of the lot: created at once from the card, not with the offer's save as 0113's states are -- the vocabulary is the world's.

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `event_proposals.py` (new, C-10): `Vocabulary`, `type_spec`, `type_definition`, `read_vocabulary`, `bind_vocabulary`, `vocab_waiting`;
   - `interpreter_events.read_event`: a proposed type keeps `role_name`; a filter's `sorte` may be `{"define": ref}` (`sorte_define`, or the existing id);
   - `condition_interpreter.py`: `Reading.vocab`, a `{"define"}` target on an event leaf, `read_answer(…, vocab)`, `waiting` with `vocab_waiting`, `Interpretation.vocabulary` (in the payload), `_answer` reads `define_events`/`define_sortes`, `resolve(…, vocabulary)` binds before names;
   - `writes/condition_drafts.PAYLOAD_KEYS` gains `vocabulary`; `cockpit/routes/conditions.py` answers and resolves it;
   - `seed_pilot.py`: F's unsupported fragment names `define_events`, one fragment « NOUVEAU TYPE D'ÉVÉNEMENT. » before « CONDITION ACTUELLE. »;
   - frontend: `conditionInterpreter.svelte.js` (`vocab` cards, `createVocab` through `/api/event-types` and `/api/event-sortes`, picks as bindings), `ConditionInterpreter.svelte` (the card, `EventTypeForm`), `questOffers.svelte.js` (`reloadChoices` after a creation);
   - `checks/condition_interpreter.py` NB2's payload fixture; EI5-EI7 added to `checks/event_interpreter.py`;
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - frontend/src/creation/ConditionInterpreter.svelte
   - frontend/src/creation/conditionInterpreter.svelte.js
   - frontend/src/creation/questOffers.svelte.js
   - scripts/seed_pilot.py
   - src/world_engine/cockpit/routes/conditions.py
   - src/world_engine/condition_interpreter.py
   - src/world_engine/event_proposals.py
   - src/world_engine/interpreter_events.py
   - src/world_engine/writes/condition_drafts.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/condition_interpreter.py
   - tooling/verify/checks/event_interpreter.py

````diff
diff --git a/frontend/src/creation/ConditionInterpreter.svelte b/frontend/src/creation/ConditionInterpreter.svelte
index f6dd68e..4ad0b43 100644
--- a/frontend/src/creation/ConditionInterpreter.svelte
+++ b/frontend/src/creation/ConditionInterpreter.svelte
@@ -5,10 +5,16 @@
      requests live in conditionInterpreter.svelte.js.
      TICKET-0113 (BRIEF-0113-E, WK2): a state the world lacks comes as a
      card -- use the near existing one, or create this one, retouched in
-     AttributeDefinitionForm -- confirmed with « Insérer ». */
+     AttributeDefinitionForm -- confirmed with « Insérer ».
+     TICKET-0114 (BRIEF-0114-G, R1): an event type or a sorte the world
+     lacks comes as a card too -- use the near one, or create this one now,
+     a type retouched in EventTypeForm. */
   import AttributeDefinitionForm from './AttributeDefinitionForm.svelte';
+  import EventTypeForm from './EventTypeForm.svelte';
+  import { loadVocabulary, vocabState } from './eventVocab.svelte.js';
+  import { serverState } from '../lib/serverState.svelte.js';
   import {
-    interpreterState, askInterpreter, pickNames, insertProposal, discardProposal,
+    interpreterState, askInterpreter, pickNames, insertProposal, discardProposal, createVocab,
   } from './conditionInterpreter.svelte.js';
 
   let { cond, role, unsaved = [], types = [] } = $props();
@@ -16,7 +22,13 @@
   const s = $state(interpreterState());
   let proposal = $derived(s.proposal);
   let picked = $derived(proposal
-    ? proposal.mentions.every((m) => s.picks[m.ref]) && s.cards.every((c) => c.pick) : false);
+    ? proposal.mentions.every((m) => s.picks[m.ref]) && s.cards.every((c) => c.pick)
+      && s.vocab.every((c) => c.pick) : false);
+
+  // EventTypeForm reads the world's entity types and domains.
+  $effect(() => {
+    if (s.vocab.some((c) => c.kind === 'type') && !vocabState.domains.length) loadVocabulary(serverState.worldId);
+  });
 </script>
 
 {#if !s.open}
@@ -65,6 +77,36 @@
             {/if}
           </div>
         {/each}
+        {#each s.vocab as card (card.ref)}
+          <div class="card">
+            <strong>{card.kind === 'type' ? 'Type d’événement' : 'Sorte'} à créer : {card.draft.name}</strong>
+            {#if card.pick}
+              <div class="muted">✓ {card.choice === 'new' ? 'créé' : 'existant'}</div>
+            {:else}
+              {#if card.near.length}
+                <div class="muted">Ce nom ressemble à {card.kind === 'type' ? 'un type' : 'une sorte'} du monde :</div>
+                {#each card.near as n (n.id)}
+                  <label class="pick"><input type="radio" bind:group={card.choice} value={n.id}
+                         onchange={() => { card.pick = n.id; }}> Utiliser « {n.name} » — {n.score} %</label>
+                {/each}
+                <label class="pick"><input type="radio" bind:group={card.choice} value="new">
+                  Créer « {card.draft.name} »</label>
+              {/if}
+              {#if card.choice === 'new'}
+                {#if card.kind === 'type'}
+                  {#if vocabState.domains.length}<EventTypeForm draft={card.draft} vocab={vocabState} />{/if}
+                  <div class="muted">Garde le nom des rôles : la condition les nomme.</div>
+                {:else}
+                  <input type="text" bind:value={card.draft.name}>
+                {/if}
+                <button disabled={card.busy || !card.draft.name.trim()} onclick={() => createVocab(card)}>
+                  Créer {card.kind === 'type' ? 'ce type' : 'cette sorte'}
+                </button>
+              {/if}
+              {#if card.error}<p class="err">{card.error}</p>{/if}
+            {/if}
+          </div>
+        {/each}
         {#each proposal.notes as note, i (i)}<p class="muted">{note}</p>{/each}
         {#each proposal.errors as error, i (i)}<p class="err">{error}</p>{/each}
         <div class="inline">
diff --git a/frontend/src/creation/conditionInterpreter.svelte.js b/frontend/src/creation/conditionInterpreter.svelte.js
index fce24a7..aa017b1 100644
--- a/frontend/src/creation/conditionInterpreter.svelte.js
+++ b/frontend/src/creation/conditionInterpreter.svelte.js
@@ -12,14 +12,22 @@
    creates she may retouch (AttributeDefinitionForm) before « Insérer »,
    which confirms the definitions with the condition and adds them to the
    offer draft's `unsaved` list -- the offer's save writes them. Every
-   request carries that list. */
+   request carries that list.
+   TICKET-0114 (BRIEF-0114-G, R1): a proposal may also carry the event
+   types and sortes it proposes (`vocabulary`). Each is a card: the creator
+   uses a near one, or creates this one -- retouched in EventTypeForm --
+   through the vocabulary's own routes; « Appliquer les choix » then binds
+   each ref to the id she chose. Created at once: the vocabulary belongs to
+   the world, not to the offer. */
 import { api } from './sheetRequest.svelte.js';
 import { conditionBody, conditionDraft } from './questRequirements.js';
 import { definitionBody, specDraft } from './attributes.svelte.js';
+import { typeBody, typeDraft } from './eventVocab.svelte.js';
+import { reloadChoices } from './questOffers.svelte.js';
 
 export function interpreterState() {
   return { open: false, instruction: '', attemptId: crypto.randomUUID(), busy: false, error: '',
-           proposal: null, picks: {}, cards: [] };
+           proposal: null, picks: {}, cards: [], vocab: [] };
 }
 
 async function post(path, body) {
@@ -38,6 +46,33 @@ function cardsOf(proposal) {
   }));
 }
 
+/** One card per proposed event type or sorte (TICKET-0114): its near
+    names, the creator's choice (`new` or a near id), its draft, and once
+    chosen or created the id it binds to (`pick`). */
+function vocabCardsOf(proposal) {
+  return (proposal?.vocabulary || []).map((v) => ({
+    ref: v.ref, kind: v.kind, near: v.near || [], choice: (v.near || []).length ? '' : 'new', pick: '',
+    draft: v.kind === 'type' ? typeDraft(v.definition) : { name: v.definition.name }, error: '', busy: false,
+  }));
+}
+
+/** Create the card's type or sorte now (`confirm_near`: she saw the near ones). */
+export async function createVocab(card) {
+  card.busy = true;
+  card.error = '';
+  try {
+    const result = card.kind === 'type'
+      ? await post('/api/event-types', typeBody(card.draft, true))
+      : await post('/api/event-sortes', { name: card.draft.name, confirm_near: true });
+    card.pick = card.kind === 'type' ? result.type.id : result.sorte.id;
+    await reloadChoices(); // the editor's lists now hold it
+  } catch (e) {
+    card.error = e.message;
+  } finally {
+    card.busy = false;
+  }
+}
+
 async function run(state, request) {
   state.busy = true;
   state.error = '';
@@ -45,6 +80,7 @@ async function run(state, request) {
     state.proposal = await request();
     state.picks = {};
     state.cards = cardsOf(state.proposal);
+    state.vocab = vocabCardsOf(state.proposal);
   } catch (e) {
     state.error = e.message;
   } finally {
@@ -65,6 +101,7 @@ export function askInterpreter(state, cond, role, unsaved) {
 export function pickNames(state, unsaved) {
   const bindings = { ...state.picks };
   for (const card of state.cards) if (card.near.length) bindings[card.ref] = card.pick;
+  for (const card of state.vocab) bindings[card.ref] = card.pick;
   return run(state, () => post('/api/conditions/drafts/' + state.proposal.draft_id + '/resolve',
                                { bindings, unsaved_attributes: unsavedBody(unsaved) }));
 }
@@ -88,6 +125,7 @@ export async function insertProposal(state, cond, unsaved) {
   Object.assign(cond, conditionDraft(proposal.view), { draftId: proposal.draft_id });
   state.proposal = null;
   state.cards = [];
+  state.vocab = [];
   state.instruction = '';
   state.open = false;
 }
@@ -101,4 +139,5 @@ export async function discardProposal(state) {
   }
   state.proposal = null;
   state.cards = [];
+  state.vocab = [];
 }
diff --git a/frontend/src/creation/questOffers.svelte.js b/frontend/src/creation/questOffers.svelte.js
index 9b35fcd..19e3b18 100644
--- a/frontend/src/creation/questOffers.svelte.js
+++ b/frontend/src/creation/questOffers.svelte.js
@@ -124,6 +124,16 @@ export async function loadOffers(worldId) {
   }
 }
 
+/** The editor's picker lists again -- TICKET-0114 (BRIEF-0114-G): after the
+    interpreter's card created an event type or a sorte. */
+export async function reloadChoices() {
+  try {
+    questOffersState.choices = await api('/api/quest-offers/choices');
+  } catch (e) {
+    questOffersState.loadError = e.message;
+  }
+}
+
 function draftBody(draft) {
   return {
     giver_entity_id: draft.giver_entity_id, contact_entity_id: draft.contact_entity_id || null,
diff --git a/scripts/seed_pilot.py b/scripts/seed_pilot.py
index eac2142..f39d471 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -2099,11 +2099,27 @@ CONDITION_INTERPRET_FRAGMENTS: tuple[tuple[str, str, str], ...] = (
      "\"step\", \"with\": [{\"role\": \"victime\", \"sorte\": \"Loup\"}]}.\n\nCONNECTEURS. {"),
     ("system_prompt",
      "ce qui s'est passé (\"event\" : tuer, être repéré), ",
-     "un événement qu'aucun type de la liste ne dit (\"event\"), "),
+     "un événement que tu ne sais ni lire dans la liste des types ni proposer dans \"define_events\" "
+     "(\"event\"), "),
     ("user_template",
      "Compétences (code — nom) :\n{skills}",
      "Compétences (code — nom) :\n{skills}\n\nTypes d'événements (code — nom, rôles) :\n{event_types}"
      "\n\nSortes :\n{sortes}"),
+    # TICKET-0114 (BRIEF-0114-G, R1): a type or a sorte the lists lack is
+    # proposed; the creator creates it from the card, or picks a near one.
+    ("system_prompt",
+     "CONDITION ACTUELLE.",
+     "NOUVEAU TYPE D'ÉVÉNEMENT. Si la phrase parle d'un événement qu'aucun type de la liste ne dit, "
+     "propose-le dans \"define_events\" : {\"ref\": \"v1\", \"name\": \"Tuer\", \"domain\": "
+     "\"military\" | \"political\" | \"magical\" | \"criminal\" | \"social\" | \"mystery\" | \"other\", "
+     "\"roles\": [{\"name\": \"tueur\", \"for\": [les types d'entité qu'il accepte, par leur clé], "
+     "\"sorte\": false}, {\"name\": \"victime\", \"for\": [\"character\"], \"sorte\": true}], "
+     "\"quantity\": true s'il se compte (« 3 loups »), sinon false}. La feuille le nomme par "
+     "{\"define\": \"v1\"} comme cible, et ses rôles par leur nom. Une sorte absente de la liste des "
+     "sortes se propose dans \"define_sortes\" : {\"ref\": \"o1\", \"name\": \"Loup\"}, et se nomme "
+     "dans \"with\" par {\"role\": \"victime\", \"sorte\": {\"define\": \"o1\"}}. Ne propose jamais "
+     "un type ou une sorte que les listes contiennent déjà : utilise son code ou son nom.\n\n"
+     "CONDITION ACTUELLE."),
 )
 
 
diff --git a/src/world_engine/cockpit/routes/conditions.py b/src/world_engine/cockpit/routes/conditions.py
index e2a6a8c..5e6848c 100644
--- a/src/world_engine/cockpit/routes/conditions.py
+++ b/src/world_engine/cockpit/routes/conditions.py
@@ -15,6 +15,11 @@ request, the creator picks between a near existing attribute and a new one
 (`resolve`), and confirms each definition -- retouched in the card or not --
 with `inserted`; the offer's save writes them (`routes/quests.py`).
 
+Since TICKET-0114 (BRIEF-0114-G, R1), a proposal may carry the event types
+and sortes it proposes (`vocabulary`). The creator creates each through
+the vocabulary's own routes (`routes/event_types.py`) -- or picks a near
+one -- and `resolve` binds its ref to that id.
+
 Every model call lives in `condition_interpreter`, every journal write in
 `writes/condition_drafts.py`; this module parses, maps a refusal to its
 status code, and commits once per request. Every proposal that reached the
@@ -109,7 +114,7 @@ def _answer(draft: ConditionDraft, result: Optional[_interpreter.Interpretation]
     attributes the answer proposes, each with the attributes near it."""
     if result is None:
         return {"draft_id": draft.id, "outcome": draft.outcome, "view": None, "mentions": [], "notes": [],
-                "errors": [], "definitions": []}
+                "errors": [], "definitions": [], "vocabulary": []}
     views = unsaved_views(tuple(unsaved) + tuple(
         UnsavedAttribute(ref=d["ref"], spec=spec_from_dict(d["definition"]))
         for d in result.definitions if not d.get("adopted")))
@@ -118,6 +123,7 @@ def _answer(draft: ConditionDraft, result: Optional[_interpreter.Interpretation]
         "view": condition_view(db, result.tree, views) if result.tree is not None else None,
         "mentions": [m for m in result.mentions if m["status"] != "matched" and m["choices"]],
         "notes": result.notes, "errors": result.errors, "definitions": result.definitions,
+        "vocabulary": result.vocabulary,
     }
 
 
@@ -174,7 +180,7 @@ def resolve(draft_id: str, body: ResolveBody, db: Session = Depends(get_session)
     try:
         result = _interpreter.resolve(db, draft.world_ref, stored["pending"], stored["mentions"],
                                       stored["notes"], body.bindings, tuple(stored.get("definitions") or ()),
-                                      unsaved)
+                                      unsaved, tuple(stored.get("vocabulary") or ()))
     except ValueError as exc:
         raise HTTPException(status_code=422, detail=str(exc)) from exc
     move_condition_draft(db, draft, result.outcome,
diff --git a/src/world_engine/condition_interpreter.py b/src/world_engine/condition_interpreter.py
index 77d9b86..3a799cc 100644
--- a/src/world_engine/condition_interpreter.py
+++ b/src/world_engine/condition_interpreter.py
@@ -60,6 +60,7 @@ from .conditions import (
     leaves,
     node_to_dict,
 )
+from .event_proposals import Vocabulary, bind_vocabulary, read_vocabulary, vocab_waiting
 from .event_vocab import EventTypeView, world_event_types, world_sortes
 from .fact_refs import CodedRefs, code_facts, code_refs
 from .interpreter_events import bind_filters, encode_event, event_type_line, filters_waiting, read_event
@@ -282,6 +283,7 @@ class Reading:
     errors: list[str] = field(default_factory=list)
     name_errors: list[str] = field(default_factory=list)
     defined: dict[str, str] = field(default_factory=dict)  # the model's `define` ref -> `new:<ref>` (E)
+    vocab: Optional[Vocabulary] = None  # the event types and sortes it proposes (TICKET-0114, G)
 
 
 def _mention(db: Session, world_id: str, raw: dict, reading: Reading) -> Optional[str]:
@@ -349,13 +351,23 @@ def _leaf(db: Session, world_id: str, raw: dict, ctx: InterpreterContext, readin
         if target["key"] is None:
             reading.errors.append(f"{where}état proposé inconnu {raw['target']['define']!r} (attendu : un "
                                   "ref de « define »)")
+    # TICKET-0114 (BRIEF-0114-G): a type the model proposes -- or one the
+    # world has under that very name.
+    proposed_type = form == EVENT_FORM and isinstance(target, dict) and "define" in target
+    if proposed_type:
+        found = reading.vocab.target(target["define"]) if reading.vocab is not None else None
+        if found is None:
+            reading.errors.append(f"{where}type proposé inconnu {target['define']!r} (attendu : un ref de "
+                                  "« define_events »)")
+        else:
+            out["target_key" if found[0] == "id" else "type_define"] = found[1]
     if isinstance(target, str) and form in ENTITY_TARGET_TYPES:  # a bare name
         target = {"name": target, "kind": "other"}
     if form in ENTITY_TARGET_TYPES:
         out["target_entity_id"], out["target_mention"] = _entity(db, world_id, target, ctx, reading, where)
     elif form == ATTRIBUTE_FORM and isinstance(target, dict) and "key" in target:
         out["target_key"] = target["key"]
-    elif form in CODE_LISTS:
+    elif form in CODE_LISTS and not proposed_type:
         code = target.get("code") if isinstance(target, dict) else target
         out["target_key"] = ctx.lists[CODE_LISTS[form]].resolve(code)
         if out["target_key"] is None:
@@ -366,7 +378,8 @@ def _leaf(db: Session, world_id: str, raw: dict, ctx: InterpreterContext, readin
         _attribute_value(db, world_id, raw, ctx, reading, where, out)
     if form == EVENT_FORM:
         read_event(raw, out, ctx.event_types.get(out["target_key"]), ctx.sortes,
-                   lambda entity, at: _entity(db, world_id, entity, ctx, reading, at), reading.errors, where)
+                   lambda entity, at: _entity(db, world_id, entity, ctx, reading, at), reading.errors, where,
+                   reading.vocab)
     return {k: v for k, v in out.items() if v is not None or not k.endswith("_mention")}
 
 
@@ -418,11 +431,12 @@ def _read(db: Session, world_id: str, raw: Any, ctx: InterpreterContext, reading
 
 
 def read_answer(db: Session, world_id: str, raw: Any, ctx: InterpreterContext,
-                defined: Optional[dict[str, str]] = None) -> Reading:
+                defined: Optional[dict[str, str]] = None, vocab: Optional[Vocabulary] = None) -> Reading:
     """The model's `condition` read back: codes and names resolved, nothing
     validated yet. None reads as no tree. `defined`: the model's `define`
-    refs, already read (`attribute_proposals.read_definitions`)."""
-    reading = Reading(defined=dict(defined or {}))
+    refs, already read (`attribute_proposals.read_definitions`); `vocab`
+    its proposed event types and sortes (`event_proposals.read_vocabulary`)."""
+    reading = Reading(defined=dict(defined or {}), vocab=vocab)
     if raw is not None:
         reading.pending = _read(db, world_id, raw, ctx, reading, "1")
     return reading
@@ -435,7 +449,8 @@ def waiting(pending: Optional[dict]) -> bool:
     if pending is None:
         return False
     if pending.get("op") == "leaf":
-        return "subject_mention" in pending or "target_mention" in pending or filters_waiting(pending)
+        return "subject_mention" in pending or "target_mention" in pending or filters_waiting(pending) \
+            or vocab_waiting(pending)
     return any(waiting(child) for child in pending.get("children", []))
 
 
@@ -511,12 +526,16 @@ class Interpretation:
     # BRIEF-0113-E: the attributes this answer proposes -- `{ref, definition,
     # near}`, `near` the attributes whose name is near (the creator picks).
     definitions: list[dict] = field(default_factory=list)
+    # TICKET-0114 (BRIEF-0114-G): the event types and sortes it proposes --
+    # `{ref, kind, definition, near}` (`event_proposals`).
+    vocabulary: list[dict] = field(default_factory=list)
 
     def payload(self, current: Optional[ConditionTree], bindings: Optional[dict] = None) -> dict:
         """The journal's payload (`writes.condition_drafts.PAYLOAD_KEYS`)."""
         return {"current": node_to_dict(current), "pending": self.pending, "mentions": self.mentions,
                 "bindings": bindings or {}, "proposed": node_to_dict(self.tree),
-                "notes": self.notes, "errors": self.errors, "definitions": self.definitions}
+                "notes": self.notes, "errors": self.errors, "definitions": self.definitions,
+                "vocabulary": self.vocabulary}
 
 
 Exchanges = Optional[list[model_exchange.ModelExchange]]
@@ -562,7 +581,7 @@ def _settle(db: Session, world_id: str, reading: Reading, notes: list[str], retr
 
     def done(outcome, tree=None, errors=()):
         return Interpretation(outcome, tree, reading.pending, reading.mentions, notes, list(errors), retried,
-                              proposals.entries())
+                              proposals.entries(), reading.vocab.proposals if reading.vocab else [])
 
     if reading.errors or reading.name_errors:
         return done("refused", errors=reading.errors + reading.name_errors)
@@ -601,8 +620,9 @@ def _answer(db: Session, world_id: str, parsed: dict, ctx: InterpreterContext, u
     taken = {item.ref for item in unsaved}
     new, defined, errors = read_definitions(db, world_id, parsed.get("define"), taken, list(unsaved))
     ctx.attributes.update(unsaved_views(new))
-    reading = read_answer(db, world_id, parsed.get("condition"), ctx, defined)
-    reading.errors[:0] = errors
+    vocab = read_vocabulary(db, world_id, parsed.get("define_events"), parsed.get("define_sortes"))
+    reading = read_answer(db, world_id, parsed.get("condition"), ctx, defined, vocab)
+    reading.errors[:0] = errors + vocab.errors
     proposals = Proposals(unsaved=unsaved, new=new, near=near_existing(db, world_id, new, list(unsaved)))
     return _settle(db, world_id, reading, _notes(parsed.get("unsupported")), retried, proposals)
 
@@ -634,15 +654,20 @@ def _retryable(result: Interpretation) -> bool:
 
 
 def resolve(db: Session, world_id: str, pending: dict, mentions: list[dict], notes: list[str],
-            bindings: dict[str, str], definitions: tuple = (), unsaved: tuple = ()) -> Interpretation:
+            bindings: dict[str, str], definitions: tuple = (), unsaved: tuple = (),
+            vocabulary: tuple = ()) -> Interpretation:
     """The creator's picks applied to a `needs_choice` proposal; no model
     call. `ValueError` when a pick is missing or outside its choices. A
     proposed attribute near another (BRIEF-0113-E, WK2) is picked by its
     ref: `new` keeps it, an existing key moves its leaves there (`adopt`) --
     a label that attribute does not have refuses the proposal. The adopted
-    one stays in `definitions`, marked `adopted` with its key."""
+    one stays in `definitions`, marked `adopted` with its key. A proposed
+    event type or sorte (TICKET-0114, BRIEF-0114-G) is bound to the one the
+    creator created or picked, by its ref; the leaf's role names are then
+    read on that type."""
+    pending, errors = bind_vocabulary(db, world_id, pending, bindings)
     bound = bind(pending, mentions, bindings)
-    new, errors, adopted = [], [], []
+    new, adopted = [], []
     for entry in definitions:
         pick = bindings.get(entry["ref"])
         if entry.get("adopted"):
@@ -666,7 +691,7 @@ def resolve(db: Session, world_id: str, pending: dict, mentions: list[dict], not
     # An adopted proposal stays in the journal with the key it went to
     # (the dashboard of TICKET-0115 counts them); no card shows it.
     return Interpretation(outcome, tree, bound, mentions, list(notes), errors, False,
-                          proposals.entries() + adopted)
+                          proposals.entries() + adopted, list(vocabulary))
 
 
 def confirm(db: Session, world_id: str, proposed: Optional[dict], unsaved: tuple,
diff --git a/src/world_engine/event_proposals.py b/src/world_engine/event_proposals.py
new file mode 100644
index 0000000..6235865
--- /dev/null
+++ b/src/world_engine/event_proposals.py
@@ -0,0 +1,184 @@
+"""The event types and sortes a model proposes (TICKET-0114, BRIEF-0114-G;
+decisions R1 and I2 of the conditions series).
+
+When a sentence -- the creator's, to the condition interpreter; or a
+scene's, to Play's analyzer (BRIEF-0114-H) -- speaks of an event no type of
+the world says, or of a sorte the world lacks, the model proposes it in its
+answer's `define_events` / `define_sortes` blocks and names it by its ref.
+Code reads each proposal here, cleaned by the writer's own rules
+(`writes.event_types.clean_event_type`, `clean_sorte_name`), refs renamed
+`v1`, `v2`, … (types) and `o1`, … (sortes), each with the world's near names
+(the creator picks one or creates; the tool never picks). A proposal whose
+name IS one the world has is no proposal: it names that type or sorte.
+
+Nothing is written here. The creator creates a proposal from its card
+through the vocabulary's own routes (`routes/event_types.py`), or picks a
+near one; her pick binds the ref to that id (`bind_vocabulary`), and only
+then are the leaf's role names read against the type she chose.
+
+- `read_vocabulary(...)`  : the two blocks -> proposals, the model's refs
+  mapped, the errors.
+- `bind_vocabulary(...)`  : a pending tree with each ref replaced by the
+  id the creator picked, its role names resolved.
+- `vocab_waiting(leaf)`   : a leaf still names a proposal.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass, field
+from typing import Any, Optional
+
+from sqlmodel import Session
+
+from .event_vocab import (
+    EventTypeView,
+    near_event_types,
+    near_sortes,
+    type_view,
+    world_event_types,
+    world_sortes,
+)
+from .lore_resolve import normalize_surface
+from .models import EVENT_DOMAINS, EventSorte
+from .writes.event_types import EventTypeSpec, RoleSpec, clean_event_type, clean_sorte_name
+
+TYPE_PREFIX, SORTE_PREFIX = "v", "o"
+
+
+@dataclass
+class Vocabulary:
+    """What `read_vocabulary` read: `proposals` (`{ref, kind, definition,
+    near}`, kind `type` or `sorte`), `refs` the model's ref -> `("id", id)`
+    for a name the world has, or `("ref", our ref)`; `errors`."""
+
+    proposals: list[dict] = field(default_factory=list)
+    refs: dict[str, tuple[str, str]] = field(default_factory=dict)
+    errors: list[str] = field(default_factory=list)
+
+    def target(self, model_ref: Any) -> Optional[tuple[str, str]]:
+        return self.refs.get(str(model_ref))
+
+
+def type_spec(raw: dict) -> EventTypeSpec:
+    """A type in the model's form -> the writer's spec. An unknown domain
+    reads as `other`: the creator retouches it in the card."""
+    roles = tuple(RoleSpec(name=str(r.get("name") or ""), entity_types=tuple(r.get("for") or ()),
+                           accepts_sorte=bool(r.get("sorte"))) for r in raw.get("roles") or [] if isinstance(r, dict))
+    domain = raw.get("domain") if raw.get("domain") in EVENT_DOMAINS else "other"
+    return EventTypeSpec(name=str(raw.get("name") or ""), domain=domain, roles=roles,
+                         counts_quantity=bool(raw.get("quantity")), in_chronicle=raw.get("chronicle") is not False,
+                         participants_secret=bool(raw.get("secret")))
+
+
+def type_definition(spec: EventTypeSpec) -> dict:
+    """A clean spec as the card's form reads it (`eventVocab.typeDraft`)."""
+    return {"name": spec.name, "domain": spec.domain, "counts_quantity": spec.counts_quantity,
+            "in_chronicle": spec.in_chronicle, "participants_secret": spec.participants_secret,
+            "roles": [{"name": r.name, "entity_types": list(r.entity_types), "accepts_sorte": r.accepts_sorte}
+                      for r in spec.roles], "scopes": []}
+
+
+def _near(found) -> list[dict]:
+    return [{"id": n.id, "name": n.name, "score": n.score} for n in found]
+
+
+def _existing(rows, name: str) -> Optional[str]:
+    key = normalize_surface(name)
+    return next((row_id for row_id, row_name in rows if key and normalize_surface(row_name) == key), None)
+
+
+def read_vocabulary(db: Session, world_id: str, types_raw: Any, sortes_raw: Any, where: str = "") -> Vocabulary:
+    """The model's `define_events` and `define_sortes` blocks read."""
+    vocab = Vocabulary()
+    known_types = [(v.id, v.name) for v in world_event_types(db, world_id)]
+    known_sortes = [(s.id, s.name) for s in world_sortes(db, world_id)]
+    for kind, raws, prefix in (("type", types_raw, TYPE_PREFIX), ("sorte", sortes_raw, SORTE_PREFIX)):
+        for raw in raws if isinstance(raws, list) else []:
+            if not isinstance(raw, dict) or raw.get("ref") is None:
+                vocab.errors.append(f"{where}une proposition sans « ref » : {raw!r}")
+                continue
+            name = str(raw.get("name") or "")
+            same = _existing(known_types if kind == "type" else known_sortes, name)
+            if same is not None:
+                vocab.refs[str(raw["ref"])] = ("id", same)
+                continue
+            try:
+                if kind == "type":
+                    definition = type_definition(clean_event_type(db, world_id, type_spec(raw)))
+                    near = _near(near_event_types(db, world_id, definition["name"]))
+                else:
+                    definition = {"name": clean_sorte_name(db, world_id, name)}
+                    near = _near(near_sortes(db, world_id, definition["name"]))
+            except ValueError as exc:
+                vocab.errors.append(f"{where}{'type' if kind == 'type' else 'sorte'} proposé « {name} » : {exc}")
+                continue
+            ref = f"{prefix}{sum(p['kind'] == kind for p in vocab.proposals) + 1}"
+            vocab.proposals.append({"ref": ref, "kind": kind, "definition": definition, "near": near})
+            vocab.refs[str(raw["ref"])] = ("ref", ref)
+    return vocab
+
+
+def vocab_waiting(leaf: dict) -> bool:
+    return "type_define" in leaf or any("sorte_define" in f for f in leaf.get("filters") or [])
+
+
+def _role_id(view: EventTypeView, name: Any) -> Optional[str]:
+    key = normalize_surface(str(name or ""))
+    return next((r.id for r in view.active_roles() if key and normalize_surface(r.name) == key), None)
+
+
+def _bound(db: Session, world_id: str, kind: str, ref: str, bindings: dict[str, str]) -> str:
+    pick = bindings.get(ref)
+    if kind == "type":
+        view = type_view(db, pick) if pick else None
+        if view is None or view.world_id != world_id or view.status != "active":
+            raise ValueError(f"« {ref} » : crée le type proposé, ou choisis un type existant")
+        return view.id
+    sorte = db.get(EventSorte, pick) if pick else None
+    if sorte is None or sorte.world_id != world_id or sorte.status != "active":
+        raise ValueError(f"« {ref} » : crée la sorte proposée, ou choisis une sorte existante")
+    return sorte.id
+
+
+def _bind_leaf(db: Session, world_id: str, leaf: dict, bindings: dict[str, str], errors: list[str]) -> dict:
+    out = dict(leaf)
+    if "type_define" in out:
+        out["target_key"] = _bound(db, world_id, "type", out.pop("type_define"), bindings)
+    view = type_view(db, out["target_key"]) if out.get("target_key") else None
+    names = ", ".join(r.name for r in view.active_roles()) if view else ""
+    if "role_name" in out:
+        name = out.pop("role_name")
+        out["value"] = _role_id(view, name) if view and name not in (None, "") else None
+        if name not in (None, "") and out["value"] is None:
+            errors.append(f"« {name} » n'est pas un rôle de « {view.name if view else '?'} » (rôles : {names})")
+    filters = []
+    for f in out.get("filters") or []:
+        f = dict(f)
+        if "sorte_define" in f:
+            f["sorte_id"] = _bound(db, world_id, "sorte", f.pop("sorte_define"), bindings)
+        if "role_name" in f:
+            name = f.pop("role_name")
+            f["role_id"] = _role_id(view, name) if view else None
+            if f["role_id"] is None:
+                errors.append(f"« {name} » n'est pas un rôle de « {view.name if view else '?'} » (rôles : {names})")
+        filters.append(f)
+    out["filters"] = filters
+    return out
+
+
+def bind_vocabulary(db: Session, world_id: str, pending: dict, bindings: dict[str, str]) -> tuple[dict, list[str]]:
+    """`pending` with every proposal ref replaced by the creator's pick and
+    the role names of the type it names resolved. `ValueError` when a ref
+    has no pick, or a pick that is no active type or sorte of the world;
+    an unknown role name is an error of the list returned."""
+    errors: list[str] = []
+
+    def walk(node: dict) -> dict:
+        if node.get("op") != "leaf":
+            return {**node, "children": [walk(c) for c in node.get("children", [])]}
+        if "type_define" not in node and "role_name" not in node and not any(
+                "sorte_define" in f or "role_name" in f for f in node.get("filters") or []):
+            return node
+        return _bind_leaf(db, world_id, node, bindings, errors)
+
+    return walk(pending), errors
diff --git a/src/world_engine/interpreter_events.py b/src/world_engine/interpreter_events.py
index cfc7276..b5d31f6 100644
--- a/src/world_engine/interpreter_events.py
+++ b/src/world_engine/interpreter_events.py
@@ -10,7 +10,10 @@ it back here: a role or a sorte by its normalized name, an unknown one an
 error listing the right ones; an entity through the interpreter's own
 resolver (`resolve_entity`), so an ambiguous name waits for the creator's
 pick like any other -- a filter's pick is kept as `entity_mention` until
-`bind_filters`.
+`bind_filters`. Since BRIEF-0114-G, a type or a sorte the model proposes
+(`event_proposals`) is named by its ref: the leaf keeps `type_define`, its
+role names (`role_name`) and a filter's `sorte_define` until the creator
+picks (`event_proposals.bind_vocabulary`).
 
 - `event_type_line(view, types)` : one type as the `t` list shows it.
 - `encode_event(spec, out, ...)` : a clean event leaf in the model's form.
@@ -72,12 +75,22 @@ def encode_event(spec, out: dict, view: Optional[EventTypeView], sortes: dict[st
 ResolveEntity = Callable[[Any, str], tuple[Optional[str], Optional[str]]]
 
 
+def _define_ref(value: Any, vocab, errors: list[str], where: str) -> Optional[tuple[str, str]]:
+    """A `{"define": ref}` the model wrote, through its vocabulary's refs."""
+    found = vocab.target(value.get("define")) if vocab is not None else None
+    if found is None:
+        errors.append(f"{where}proposition inconnue {value.get('define')!r} (attendu : un ref de "
+                      "« define_events » ou « define_sortes »)")
+    return found
+
+
 def read_event(raw: dict, out: dict, view: Optional[EventTypeView], sortes: dict[str, str],
-               resolve_entity: ResolveEntity, errors: list[str], where: str) -> None:
+               resolve_entity: ResolveEntity, errors: list[str], where: str, vocab=None) -> None:
     """The rest of an `event` leaf, read into `out` (the generic leaf, its
-    `target_key` the type's id or None): `value` a role's id, the place
-    (`target_entity_id`, or `target_mention` while a pick waits), `since`
-    and `filters`. Every problem is appended to `errors`."""
+    `target_key` the type's id or None, `type_define` a proposed type's
+    ref): `value` a role's id -- its name while the type is a proposal --,
+    the place (`target_entity_id`, or `target_mention` while a pick waits),
+    `since` and `filters`. Every problem is appended to `errors`."""
     out["since"] = raw.get("since") or EVENT_WINDOW_DEFAULT
     if out["since"] not in CONDITION_WINDOWS:
         errors.append(f"{where}fenêtre inconnue {out['since']!r} (attendu : {', '.join(CONDITION_WINDOWS)})")
@@ -87,9 +100,12 @@ def read_event(raw: dict, out: dict, view: Optional[EventTypeView], sortes: dict
         place = {"name": place, "kind": "place"}
     if place:
         out["target_entity_id"], out["target_mention"] = resolve_entity(place, where)
-    if view is None:
+    pending = view is None and "type_define" in out
+    if view is None and not pending:
         return
-    if raw.get("value") not in (None, ""):
+    if pending and raw.get("value") not in (None, ""):
+        out["role_name"] = str(raw["value"])
+    elif raw.get("value") not in (None, ""):
         role = _role_by_name(view, raw["value"])
         if role is None:
             errors.append(f"{where}« {raw['value']} » n'est pas un rôle de « {view.name} » "
@@ -98,13 +114,20 @@ def read_event(raw: dict, out: dict, view: Optional[EventTypeView], sortes: dict
             out["value"] = role.id
     by_name = {normalize_surface(name): sid for sid, name in sortes.items()}
     for item in raw.get("with") if isinstance(raw.get("with"), list) else []:
-        role = _role_by_name(view, item.get("role")) if isinstance(item, dict) else None
-        if role is None:
+        role = _role_by_name(view, item.get("role")) if isinstance(item, dict) and view is not None else None
+        if role is None and not (pending and isinstance(item, dict) and item.get("role")):
             errors.append(f"{where}« {item.get('role') if isinstance(item, dict) else item} » n'est pas un rôle "
-                          f"de « {view.name} » (rôles : {_role_names(view)})")
+                          f"de « {view.name if view else '?'} » (rôles : {_role_names(view) if view else '?'})")
             continue
-        entry: dict[str, Any] = {"role_id": role.id, "entity_id": None, "sorte_id": None}
-        if item.get("sorte") is not None:
+        entry: dict[str, Any] = {"role_id": role.id if role else None, "entity_id": None, "sorte_id": None}
+        if role is None:
+            entry["role_name"] = str(item["role"])
+        if isinstance(item.get("sorte"), dict):
+            found = _define_ref(item["sorte"], vocab, errors, where)
+            if found is None:
+                continue
+            entry["sorte_id" if found[0] == "id" else "sorte_define"] = found[1]
+        elif item.get("sorte") is not None:
             entry["sorte_id"] = by_name.get(normalize_surface(str(item["sorte"])))
             if entry["sorte_id"] is None:
                 known = ", ".join(sortes.values()) or "aucune"
diff --git a/src/world_engine/writes/condition_drafts.py b/src/world_engine/writes/condition_drafts.py
index c0aa8a7..94cf8ff 100644
--- a/src/world_engine/writes/condition_drafts.py
+++ b/src/world_engine/writes/condition_drafts.py
@@ -43,9 +43,11 @@ CONDITION_DRAFT_MOVES: dict[str, tuple[str, ...]] = {
 # errors shown to the creator; since TICKET-0113 (BRIEF-0113-E) the
 # attributes it proposed (`definitions`: `{ref, definition, near}`, and
 # once inserted `confirmed`, the definition as the creator confirmed it --
-# the dashboard of TICKET-0115 compares the two).
+# the dashboard of TICKET-0115 compares the two); since TICKET-0114
+# (BRIEF-0114-G) the event types and sortes it proposed (`vocabulary`:
+# `{ref, kind, definition, near}`, `event_proposals`).
 PAYLOAD_KEYS: frozenset[str] = frozenset({
-    "current", "pending", "mentions", "bindings", "proposed", "notes", "errors", "definitions",
+    "current", "pending", "mentions", "bindings", "proposed", "notes", "errors", "definitions", "vocabulary",
 })
 WORLD_NAME_UNKNOWN = "(monde introuvable)"
 
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 00e6610..01bab8d 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19432,6 +19432,28 @@ longer unsupported when a type says it), delivered by
 `apply_ticket_0114_condition_prompt.py`, which reuses the 0113 delivery.
 What no type says stays a note pointing to « Vocabulaire du monde ».
 
+## THE INTERPRETER PROPOSES A MISSING EVENT TYPE OR SORTE, CREATED FROM ITS CARD (TICKET-0114) -- `define_events`, `define_sortes` (BRIEF-0114-g, no schema change)
+
+**R1, proposing.** When the sentence speaks of an event no type says, or of
+a sorte the world lacks, the model proposes it (`define_events`,
+`define_sortes`) and its leaf names it by ref. Code reads each proposal
+through the writer's own cleaning (`event_proposals.py`), with the world's
+near names; a proposal whose name the world already has is no proposal --
+it names that type or sorte. The proposal waits (`needs_choice`); the
+journal keeps it (`vocabulary`). Nothing is written by the interpreter.
+
+**Created at once, from the card (drafting decision of the lot).** The
+creator uses a near type or sorte, or creates the proposed one -- a type
+retouched in `EventTypeForm`, the very form of « Vocabulaire du monde » --
+through the vocabulary's own routes; « Appliquer les choix » binds each ref
+to the id she chose and only then reads the leaf's role names on that
+type. Unlike a proposed state (0113, WN2: written with the offer's save),
+a type is created when she says so: the vocabulary is the world's, used by
+the journal, Play and the tick, not a term of one offer -- and binding a
+ref to a real id keeps one validation path (`clean_leaf`), with no unsaved
+type to carry through the offer's save. A type created for a proposal she
+then discards stays in the vocabulary, where she can retire it.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/condition_interpreter.py b/tooling/verify/checks/condition_interpreter.py
index bd4f84a..e3fcfaa 100644
--- a/tooling/verify/checks/condition_interpreter.py
+++ b/tooling/verify/checks/condition_interpreter.py
@@ -396,7 +396,7 @@ def check_nb1() -> None:
 
 def _payload(**over) -> dict:
     base = {"current": None, "pending": None, "mentions": [], "bindings": {}, "proposed": None,
-            "notes": [], "errors": [], "definitions": []}
+            "notes": [], "errors": [], "definitions": [], "vocabulary": []}  # vocabulary: TICKET-0114
     base.update(over)
     return base
 
diff --git a/tooling/verify/checks/event_interpreter.py b/tooling/verify/checks/event_interpreter.py
index 08afded..f195e0a 100644
--- a/tooling/verify/checks/event_interpreter.py
+++ b/tooling/verify/checks/event_interpreter.py
@@ -1,6 +1,6 @@
 """G1 check for TICKET-0114 -- the condition interpreter reads the world's event types and sortes and writes an event leaf.
 
-BRIEF-0114-F's rules.
+BRIEF-0114-F's rules (EI1-EI4), then BRIEF-0114-G's (EI5-EI7).
 
 EI1 -- the prompt (static and import). `CODE_LISTS["event"]` is `t`; the
    head declares `event_types` and `sortes`, its template uses exactly its
@@ -24,6 +24,23 @@ EI4 -- interpret and delivery (fixture, stubbed model). A model answer
    carrying the `t` list. On a head holding the 0113 text and variables,
    the delivery script writes one new version equal to the seed's, its
    variables the seed's; a second run is unchanged.
+EI5 -- proposals (fixture, stubbed model). An answer proposing a type in
+   `define_events` and two sortes in `define_sortes`, its leaf naming them
+   by ref, waits (`needs_choice`) with two proposals -- the type `v1` with
+   its cleaned definition and the types whose name is near, the sorte
+   `o1` --, the sorte the world already has (« loup ») bound silently to
+   it; nothing is written. A proposal the writer refuses (a role of an
+   unknown entity type) is an error; a leaf naming an unknown ref is one.
+EI6 -- binding (fixture). Once the creator created the type and the sorte,
+   `resolve` with their ids gives the tree, the role names read on the
+   type; a ref without a pick, or a pick that is no type of the world, is a
+   `ValueError`; a near type picked whose roles lack the leaf's is
+   `refused`, the error naming its roles. Through the routes, the journal
+   keeps the proposals (`vocabulary`) and `resolve` reads them back.
+EI7 -- the card (static). `ConditionInterpreter.svelte` shows a card per
+   proposal with `EventTypeForm` and `createVocab`;
+   `conditionInterpreter.svelte.js` creates through `/api/event-types` and
+   `/api/event-sortes` and sends each card's pick as a binding.
 
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
@@ -40,7 +57,7 @@ import tempfile
 
 ROOT = pathlib.Path(__file__).resolve().parents[3]
 SCRIPT = ROOT / "scripts" / "apply_ticket_0114_condition_prompt.py"
-EVENT_FRAGMENT_MARKS = ("ÉVÉNEMENTS.", "{event_types}", "qu'aucun type de la liste")
+EVENT_FRAGMENT_MARKS = ("ÉVÉNEMENTS.", "{event_types}", "define_events")
 
 FAILURES: list[str] = []
 
@@ -300,6 +317,149 @@ def _check_delivery() -> None:
         fail(f"EI4: a second run: {runs[1].stdout.strip()[-200:]}")
 
 
+# --- EI5 / EI6 -----------------------------------------------------------------
+
+def _proposing_answer(**leaf) -> dict:
+    raw = _model_leaf(target={"define": "d1"}, value="piégeur", place=None,
+                      **{"with": [{"role": "proie", "sorte": {"define": "s1"}}]})
+    raw.update(leaf)
+    return {"condition": {"op": "all", "children": [raw]}, "unsupported": [],
+            "define_events": [{"ref": "d1", "name": "Chasses", "domain": "nope", "quantity": True,
+                               "roles": [{"name": "Piégeur", "for": ["character"]},
+                                         {"name": "Proie", "for": ["character"], "sorte": True}]}],
+            "define_sortes": [{"ref": "s1", "name": "Lapin"}, {"ref": "s2", "name": "loup"}]}
+
+
+def _interpret(ci, db, ids, answer):
+    stub, original = _Stub([answer, answer]), ci.chat
+    ci.chat = stub
+    try:
+        return ci.interpret(db, ids["world"], "completion", "A piégé des lapins", None, [])
+    finally:
+        ci.chat = original
+
+
+def check_ei5(engine, ids: dict) -> None:
+    from sqlmodel import Session, func, select
+
+    from world_engine import condition_interpreter as ci
+    from world_engine.models import EventSorte, EventType
+
+    with Session(engine) as db:
+        before = (db.exec(select(func.count()).select_from(EventType)).one(),
+                  db.exec(select(func.count()).select_from(EventSorte)).one())
+        result = _interpret(ci, db, ids, _proposing_answer(**{"with": [
+            {"role": "proie", "sorte": {"define": "s1"}}, {"role": "Piégeur", "sorte": {"define": "s2"}}]}))
+        kinds = [(v["ref"], v["kind"]) for v in result.vocabulary]
+        piege = result.vocabulary[0] if result.vocabulary else {}
+        if result.outcome != "needs_choice" or kinds != [("v1", "type"), ("o1", "sorte")] \
+                or piege.get("definition", {}).get("domain") != "other" \
+                or [r["name"] for r in piege.get("definition", {}).get("roles", [])] != ["Piégeur", "Proie"] \
+                or "Chasse" not in [n["name"] for n in piege.get("near", [])]:
+            fail(f"EI5: the proposals read {result.outcome}, {result.vocabulary}, {result.errors}")
+        leaf = result.pending["children"][0] if result.pending else {}
+        if leaf.get("type_define") != "v1" or leaf.get("role_name") != "piégeur" \
+                or [f.get("sorte_define") or f.get("sorte_id") for f in leaf.get("filters", [])] != ["o1", ids["loup"]]:
+            fail(f"EI5: the pending leaf is {leaf}")
+        after = (db.exec(select(func.count()).select_from(EventType)).one(),
+                 db.exec(select(func.count()).select_from(EventSorte)).one())
+        if after != before:
+            fail(f"EI5: reading the proposals wrote {before} -> {after}")
+        bad = _proposing_answer()
+        bad["define_events"][0]["roles"][0]["for"] = ["dragon"]
+        refused = _interpret(ci, db, ids, bad)
+        if refused.outcome != "refused" or not any("Chasses" in e for e in refused.errors):
+            fail(f"EI5: a broken proposal gave {refused.outcome}, {refused.errors}")
+        unknown = _interpret(ci, db, ids, _proposing_answer(target={"define": "d9"}))
+        if not any("d9" in e for e in unknown.errors):
+            fail(f"EI5: an unknown ref gave {unknown.errors}")
+        db.rollback()
+
+
+def check_ei6(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine import condition_interpreter as ci
+    from world_engine.conditions import node_to_dict
+    from world_engine.event_vocab import type_view
+    from world_engine.writes.event_types import EventTypeSpec, RoleSpec, write_event_type, write_sorte
+
+    with Session(engine) as db:
+        result = _interpret(ci, db, ids, _proposing_answer())
+        created = write_event_type(db, world_id=ids["world"], spec=EventTypeSpec(
+            name="Chasses", counts_quantity=True,
+            roles=(RoleSpec("Piégeur", ("character",)), RoleSpec("Proie", ("character",), accepts_sorte=True))))
+        lapin = write_sorte(db, world_id=ids["world"], name="Lapin").id
+        roles = {r.name: r.id for r in type_view(db, created.id).roles}
+        args = (db, ids["world"], result.pending, result.mentions, [])
+        bound = ci.resolve(*args, {"v1": created.id, "o1": lapin}, (), (), tuple(result.vocabulary))
+        leaf = node_to_dict(bound.tree)["children"][0] if bound.tree else {}
+        if bound.outcome != "proposed" or leaf.get("target_key") != created.id or leaf.get("value") != roles["Piégeur"] \
+                or leaf.get("filters") != [{"role_id": roles["Proie"], "entity_id": None, "sorte_id": lapin}]:
+            fail(f"EI6: binding gave {bound.outcome}, {leaf}, {bound.errors}")
+        for what, picks in (("no pick", {"o1": lapin}), ("a foreign pick", {"v1": ids["loup"], "o1": lapin})):
+            try:
+                ci.resolve(*args, picks, (), (), tuple(result.vocabulary))
+                fail(f"EI6: {what} was accepted")
+            except ValueError:
+                pass
+        near = ci.resolve(*args, {"v1": ids["chasse"], "o1": lapin}, (), (), tuple(result.vocabulary))
+        if near.outcome != "refused" or not any("Chasseur, Proie, Témoin" in e for e in near.errors):
+            fail(f"EI6: a near type without the role gave {near.outcome}, {near.errors}")
+        db.rollback()
+    _check_routes(engine, ids)
+
+
+def _check_routes(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine import condition_interpreter as ci
+    from world_engine.cockpit.routes import conditions as routes
+    from world_engine.models import ConditionDraft, World
+    from world_engine.writes.event_types import EventTypeSpec, RoleSpec, write_event_type, write_sorte
+
+    with Session(engine) as db:
+        world = db.get(World, ids["world"])
+        world.is_active = True
+        db.add(world)
+        db.commit()
+        stub, original = _Stub([_proposing_answer()]), ci.chat
+        ci.chat = stub
+        try:
+            answer = routes.interpret(routes.InterpretBody(instruction="A piégé des lapins", role="completion"),
+                                      db=db)
+        finally:
+            ci.chat = original
+        stored = db.get(ConditionDraft, answer["draft_id"]).payload.get("vocabulary") or []
+        if [v["ref"] for v in answer.get("vocabulary", [])] != ["v1", "o1"] or len(stored) != 2:
+            fail(f"EI6: the route answered {answer.get('vocabulary')}, the journal keeps {stored}")
+            return
+        created = write_event_type(db, world_id=ids["world"], spec=EventTypeSpec(
+            name="Chasses", roles=(RoleSpec("Piégeur", ("character",)),
+                                            RoleSpec("Proie", ("character",), accepts_sorte=True)))).id
+        lapin = write_sorte(db, world_id=ids["world"], name="Lapin").id
+        db.commit()
+        bound = routes.resolve(answer["draft_id"], routes.ResolveBody(bindings={"v1": created, "o1": lapin}), db=db)
+        if bound["outcome"] != "proposed" or not bound["view"]:
+            fail(f"EI6: the resolve route gave {bound['outcome']}, {bound['errors']}")
+
+
+# --- EI7 -----------------------------------------------------------------------
+
+def check_ei7() -> None:
+    front = ROOT / "frontend" / "src" / "creation"
+    wants = {
+        "ConditionInterpreter.svelte": ("<EventTypeForm", "createVocab(card)", "s.vocab"),
+        "conditionInterpreter.svelte.js": ("'/api/event-types'", "'/api/event-sortes'",
+                                           "for (const card of state.vocab) bindings[card.ref] = card.pick;"),
+    }
+    for name, needles in wants.items():
+        text = (front / name).read_text(encoding="utf-8") if (front / name).exists() else ""
+        for needle in needles:
+            if needle not in text:
+                fail(f"EI7: {name} lacks {needle!r}")
+
+
 def main() -> int:
     _fresh_db()
     from world_engine.db import create_db_and_tables, engine
@@ -307,18 +467,20 @@ def main() -> int:
     create_db_and_tables()
     check_ei1()
     ids = _world(engine)
-    for check in (check_ei2, check_ei3, check_ei4):
+    for check in (check_ei2, check_ei3, check_ei4, check_ei5, check_ei6):
         try:
             check(engine, ids)
         except Exception as exc:  # a crash is a failure, never a pass
             fail(f"{check.__name__}: crashed: {type(exc).__name__}: {exc}")
+    check_ei7()
     for msg in FAILURES:
         print(f"FAIL: {msg}")
     if FAILURES:
         return 1
     print("PASS: event_interpreter -- the interpreter shows the model the world's event types with their roles "
           "and its sortes, writes an event leaf by role, place, window and filters and reads it back, waits for "
-          "a pick on an ambiguous name, and its prompt is delivered fragment by fragment")
+          "a pick on an ambiguous name, proposes a missing type or sorte the creator creates or picks -- nothing "
+          "written before -- and its prompt is delivered fragment by fragment")
     return 0
 
 
````

2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. The prompt changes again: F's script delivers G's fragments too (`apply_ticket_0114_condition_prompt.py`, after the merge).
4. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
5. Run the checks below, then the full corpus.

## Scope OUT

- Writing a proposed type with the offer's save (0113's WN2 path) -- rejected in this lot (drafting decision).
- Play's analyzer -- H.
- Every later brief of this lot: BRIEF-0114-H.

## Invariants to defend

INV-08: the interpreter writes nothing; a type or sorte is written only by B's routes on the creator's click, through C-03's writer (EI5 counts rows). INV-48: the prompt is re-delivered as a new version.

## Decision rights

STOP:
- A path would write a proposed type or sorte without the creator's click on the card.
- A Mini-RECON anchor that does not hold.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `npm run build` names a different asset hash than the prototype's: commit what it builds (`frontend_build_fresh.py` judges the manifest, not the name).
- A check other than this brief's own fails on a line count or a docstring count this diff moved (`file_map.py`, `decisions_index.py`): regenerate `FILE_MAP.md` / `DECISIONS_INDEX.md` and rerun.

REPORT-ONLY:
- A type created from a card and then the proposal discarded: the type stays (accepted).
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.
- Log lines a check prints before its verdict (`[skip] …`, `[overhearing] …`): the analyzer's own logging.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/`.
- `python tooling/verify/checks/event_interpreter.py` -> `PASS`.
- `python tooling/verify/checks/condition_interpreter.py` -> `PASS`.
- `python tooling/verify/checks/attribute_interpreter.py` -> `PASS`.
- `python tooling/verify/checks/effect_self_write.py` -> `PASS`.
- `python tooling/verify/checks/frontend_build_fresh.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (155 on the prototype).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **EI5** -- `event_proposals.py` `read_vocabulary`: `if same is not None:` -> `if False:`; or `condition_interpreter.waiting`: `or vocab_waiting(pending)` -> `or False`
  - **EI6** -- `event_proposals.py` `_bind_leaf`: `out["value"] = _role_id(view, name) if …` -> `out["value"] = None`; or `Interpretation.payload`: `"vocabulary": self.vocabulary` -> `"vocabulary": []`
  - **EI7** -- `ConditionInterpreter.svelte`: `onclick={() => createVocab(card)}` -> `onclick={() => {}}`
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated.
