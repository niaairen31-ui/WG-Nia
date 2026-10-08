<!-- slug: condition-surfaces -->
# BRIEF 0111-D — "A quest step says when its objective is reached -- shown, never acted on; the editor speaks trees"

Lot: LOT-0111-condition-language.md (authoritative on conflict)
Depends on: BRIEF-0111-C

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0111-C's commit).

- `src/world_engine/quest_reads.py:76` -> `def offer_dict(offer: QuestOffer, db: Session) -> dict:`
- `src/world_engine/quest_reads.py:161` -> `def _steps_view(agenda: Agenda, character: Character, db: Session) -> list[dict]:`
- `src/world_engine/cockpit/routes/quests.py:82` -> `class OfferBody(BaseModel):`
- `src/world_engine/writes/quests.py:196` -> `def accept_quest(db: Session, *, offer: QuestOffer, character: Character) -> Quest:`
- `src/world_engine/day_plan.py:77` -> `class PlanStep:`
- `frontend/src/creation/questOffers.svelte.js:119` -> `function draftBody(draft) {`
- `frontend/src/creation/questRequirements.js:15` -> `export const REQUIREMENT_FORMS = {`
- `frontend/src/journee/QuestPanel.svelte:1` -> `<script>`
- `frontend/src/journee/SettlementRecap.svelte:1` -> `<script>`
- `src/world_engine/models/config.py:130` -> `CONDITION_ROLES: tuple[str, ...] = ("eligibility", "prerequisite", "completion")`
- No `frontend/src/creation/ConditionEditor.svelte` exists.

## Facts carried

### R-10 — the offer writer, acceptance and eligibility [M]
Opened: `src/world_engine/writes/quests.py:57-69` (`_clean_offer_steps`),
`:104-166` (`write_quest_offer`: all validated before the first write, its
own completion refused `:131-133`, full replace `:141-145`), `:179-196`
(`acceptance_refusal`: `evaluate_specs` on the eligibility rows, reasons
joined), `:199-227` (`accept_quest`: steps and their requirements copied,
re-cleaned); `src/world_engine/models/quests.py:39-67` (`QuestOffer`:
`giver_entity_id`, `contact_entity_id`).
Consequence: eligibility is judged with the offer's bindings (P1:
`giver`, `contact`); acceptance copies each step's conditions; the
self-reference check reads every leaf.

### R-11 — the offer API, the editor and its mirror [M]
Opened: `src/world_engine/cockpit/routes/quests.py:50-56` (`RequirementBody`),
`:57-62` (`OfferStepBody.requirements`), `:83` (`OfferBody.eligibility`, a
list), `:119-137` (`_spec`, `_save_offer`: a `ValueError` is a 422);
`src/world_engine/quest_reads.py:52-56` (`_requirement_dict`), `:62-81`
(`offer_dict`), `:108-132` (`editor_choices`, `items` among the lists);
`frontend/src/creation/questRequirements.js:11-22` (`REQUIREMENT_FORMS`,
one line per form), `:30-32`, `:50-58` (`requirementBody`);
`frontend/src/creation/QuestRequirementRow.svelte`;
`frontend/src/creation/questOffers.svelte.js:26-28,38-56,118-129`;
`frontend/src/creation/QuestOffers.svelte:132-163`;
`tooling/verify/checks/quests.py:790-808` (QC1 parses each form line).
Consequence: C mirrors the new forms in the same one-line shape (a
`values: true` flag, a `column: 'none'`); D switches the API and the
editor to trees together.

### R-12 — the player's French for a blocked step [M]
Opened: `src/world_engine/day_resolve.py:256-283` (`_BLOCKED_DETAIL_FR`,
one template per form; `requirement_detail_fr` fails closed on an unknown
form); `src/world_engine/cockpit/day_reconcile_apply.py:74`,
`src/world_engine/quest_reads.py:151` (both join the unmet verdicts'
details); `tooling/verify/checks/day_narration.py:652-676` (R15: the dict's
keys are `REQUIREMENT_TYPES`, both directions).
Consequence: C adds `blocked_details_fr(verdict, db)` (C-08) for both
readers; the three new forms get a detail.

### R-20 — the editor saves the whole offer; Journée reads `_steps_view` [M]
Opened: `frontend/src/creation/questOffers.svelte.js:118-151`
(`draftBody`, `saveDraft`: the API's shape, sent whole);
`src/world_engine/quest_reads.py:143-155` (`_steps_view`, read by
`player_quests` and by `quest_settlement_view.settlement_context`
`src/world_engine/quest_settlement_view.py:89-106`);
`frontend/src/journee/QuestPanel.svelte:53-62`,
`frontend/src/journee/SettlementRecap.svelte:38-43`.
Consequence: C keeps the API's flat lists (the editor unchanged but for
the new forms); D changes the API and the editor together, and both
Journée surfaces read the steps' completion from `_steps_view`.

### R-23 — a player surface writes out the fact of an unmet `knowledge` gate [M]
Added by AMENDMENT-0111-01 (Claude Code's STOP on BRIEF-0111-D, trigger D1-a).
Opened: `src/world_engine/day_plan.py:173-192` (`_eval_knowledge`: the
verdict's `required_label` is `fact_text`, met iff the character holds a
row), `src/world_engine/day_resolve.py:256-283` (`_BLOCKED_DETAIL_FR`
`:261` writes `{required}`, the label, for `knowledge`), `:426` (the
narration's `blocked_detail`, from every unmet verdict);
`src/world_engine/quest_reads.py:143-155` (`_steps_view` `:151`, Journée's
quest panel and `settlement_context`); `src/world_engine/cockpit/day_reconcile_apply.py:74`
(the 422 a standing plan answers); `src/world_engine/day_mutations.py:225-272`
(`_emit_new_knowledge` `:240`: a lead per unmet `knowledge` verdict);
`src/world_engine/day_plan.py:536` (`anchor_requirements`: B3 anchors only
the MODEL's gates); `src/world_engine/knowledge_resolve.py:248`
(`resolve_knowledge_level`); `CLAUDE.md:148` (« Secrets are structurally
excluded »).
Finding: a `knowledge` gate is shown to the player precisely when his
character does not know the fact, and its line writes the fact out. A day
plan's gates are anchored to facts others hold openly (B3); a quest's are
written by the creator, unanchored -- a secret or the creator's note can be
one. The path exists since TICKET-0108 (quest steps judged in Journée);
BRIEF-0111-D's completion lines add a second; the day's narration receives
the same text as model context. Since BRIEF-0111-C a step's verdicts are
every judged leaf: a leaf under a `not` or about the giver also reaches the
narration and `_emit_new_knowledge`.
Consequence: A1 -- every player surface writes a fact out only when the
character resolves it above `unaware`; V2 -- a judged leaf about someone
else reads `?` there; a blocked step names and teaches only the leaves that
hold it back for its doer (C-04, C-05, C-07, C-08, C-09 amended in D).

### Case tables

b-2 -- a leaf's subject (C-04).

| subject                   | bound to               | judged on        | state if not judged                    |
|---------------------------|------------------------|------------------|----------------------------------------|
| role `doer`               | `bindings.doer`        | that character   | --                                     |
| role `giver`              | a character            | that character   | --                                     |
| role `giver`              | a faction              | --               | unknown, « le donneur n'est pas un personnage » |
| role `giver` / `contact`  | nothing (None)         | --               | unknown, « … n'est pas défini ici »    |
| role `contact`            | a character            | that character   | --                                     |
| `subject_entity_id`       | a character            | that character   | --                                     |
| `subject_entity_id`       | not a character        | --               | unknown, « X n'est pas un personnage » (refused at write, C-06) |

Where the roles are bound: a day plan -> `doer` only (the player); an
offer's eligibility and a quest's agenda -> `doer`, the offer's giver, its
contact (`offer_bindings`, `plan_bindings`).

b-6 -- what a player reads of a leaf (AMENDMENT-0111-01, C-04, C-05, C-08).

| leaf                                         | creator          | player (`viewer_id` = the doer)                 |
|----------------------------------------------|------------------|-------------------------------------------------|
| on `doer`, any form but the two below       | text, mark, count | same                                           |
| on `doer`, `knowledge`, fact known           | the fact's text   | same                                           |
| on `doer`, `knowledge`, fact not known       | the fact's text   | « … connaît un fait encore caché »; detail « il lui manque encore un fait à découvrir » |
| on `doer`, `relation_gte`                    | mark, « 40/50 »   | mark, no count                                 |
| on `giver` / `contact` / a named character  | its state         | `?` « (le personnage ne peut pas le vérifier) », no count; a `knowledge` one hides its fact as above |
| a role bound to nothing                       | `?` and why      | same                                           |
| a connector                                   | its state         | recombined from what the player sees (b-1)    |

A blocked step (narration, lead): only the unmet leaves on `doer` under no
`not`.

## Contracts

### C-03 — the tree, `conditions.ConditionTree`
Produced by: BRIEF-0111-B (map/drop: BRIEF-0111-C)   Consumed by: C, D
Signature: frozen dataclass `ConditionTree(op: str, children:
tuple[ConditionTree, ...] = (), n: Optional[int] = None, leaf:
Optional[RequirementSpec] = None)`; `CONNECTORS = ("all", "any", "not",
"at_least")`; helpers `leaf(spec)`, `all_of(specs) -> Optional[tree]`
(None for no specs), `leaves(tree)` (depth first), `and_path_leaves(tree)`
(through `all` only), `flat_leaves(tree)` (`()` for None, the leaves of a
lone leaf or of `all` of leaves, else None), `map_leaves(tree, fn)`,
`drop_leaves(tree, drop)` (a connector left childless goes; `at_least`
keeps `n <= children`; None when the root goes).
Shape (`check_shape`, raises `ConditionShapeError(ValueError)`): a leaf
has a form and no children and exactly one subject (a known role or an
entity); a connector has at least one child; `not` exactly one;
`at_least` an integer `n` from 1 to its children; only `at_least` has `n`;
depth at most `MAX_DEPTH = 6`, nodes at most `MAX_NODES = 60`.
Dict form: a leaf `{"op": "leaf", "type", "subject_role",
"subject_entity_id", "target_entity_id", "target_key", "threshold",
"value"}`; a connector `{"op", "children": [...]}` plus `"n"` for
`at_least`. `node_from_dict(None)` is None; a leaf naming no subject is
`doer`; `""` reads as None; a non-integer threshold is refused.

### C-04 — evaluation, `conditions.evaluate`
Produced by: BRIEF-0111-B   Consumed by: C, D
Signature: `evaluate(tree: Optional[ConditionTree], bindings: Bindings,
db) -> Optional[VerdictNode]`; `Bindings(doer: Character, giver_id:
Optional[str] = None, contact_id: Optional[str] = None)`.
Return shape: `VerdictNode(state, op, children, n, spec, verdict, reason)`
-- `state` in `("met", "unmet", "unknown")`; a leaf carries its `spec`
and either its `Verdict` (judged) or its French `reason` (`unknown`);
`.met`; `.leaf_nodes()`; `.leaf_verdicts()` (judged leaves only).
Error and empty cases: None for no condition (the caller treats it as
met); a role bound to nothing -> `unknown` « … n'est pas défini ici »; a
subject that is not a character -> `unknown` « … n'est pas un personnage »;
an unknown form raises `ValueError`. Connectors per table b-1. One
reachable set per subject per call.
Amended by AMENDMENT-0111-01 (produced by BRIEF-0111-D):
`VerdictNode.seen_by(viewer_id) -> VerdictNode` -- a judged leaf whose
subject is neither `doer` nor `viewer_id` becomes `unknown`, no verdict,
reason `UNSEEN_REASON_FR` (« le personnage ne peut pas le vérifier »);
every connector recombined from its seen children (table b-6).
`VerdictNode.blocking_verdicts() -> tuple[Verdict, ...]` -- the verdicts
of the judged leaves on `doer` that are unmet and under no `not`, in order.

### C-05 — the French of a tree, `condition_text`
Produced by: BRIEF-0111-B (new forms: BRIEF-0111-C)   Consumed by: C, D
Signature: `describe(db, tree) -> list[dict]` (`{"depth", "text"}`, a
connector's head before its children one level deeper; [] for None);
`verdict_lines(db, verdict) -> list[dict]` (`{"depth", "text", "state",
"mark", "progress"}`, `mark` in ✓ ✗ ?, `progress` `"current/required"`
when both are integers, an unknown leaf's text ending with its reason);
`leaf_text(db, spec) -> str`. `FORM_PHRASES_FR` (one per form, `{who}`
`{target}` `{threshold}` `{value}`), `CONNECTOR_HEADS_FR` (one per
connector), `SUBJECT_LABELS_FR`, `VALUE_LABELS_FR` (one label per
`FORM_VALUES` value).
Error and empty cases: `leaf_text` raises `ValueError` on an unknown form.
Amended by AMENDMENT-0111-01 (produced by BRIEF-0111-D): `leaf_text(db,
spec, viewer_id=None)` and `verdict_lines(db, verdict, viewer_id=None)`.
With `viewer_id` (a player surface): the verdict is first `seen_by` him;
a `knowledge` leaf whose fact `known_to(db, viewer_id, fact_id)` denies
(`resolve_knowledge_level` is `unaware`) reads `HIDDEN_FACT_FR` («
{who} connaît un fait encore caché »); a form in `HIDDEN_PROGRESS_FORMS`
(`relation_gte`) has no progress. Without it (the creator): unchanged.

### C-07 — the plan step and its evaluation (`day_plan`)
Produced by: BRIEF-0111-C (`completion`: BRIEF-0111-D)   Consumed by: C, D
Signature: `PlanStep(objective, cost, domain, prerequisite:
Optional[ConditionTree] = None, completion: Optional[ConditionTree] =
None)`; `EvaluatedStep(step, verdict: Optional[VerdictNode] = None)` with
`.met` (None or `verdict.met`) and `.verdicts` (`verdict.leaf_verdicts()`);
`evaluate_requirements(step, bindings, db) -> Optional[VerdictNode]`;
`plan_bindings(agenda_id, character, db) -> Bindings` (the character; and,
for a quest's agenda, its offer's giver and contact);
`evaluate_agenda_step(agenda_step, character, db) -> EvaluatedStep` (the
stored prerequisite, judged with `plan_bindings`).
Error and empty cases: a model's plan step without requirements has no
prerequisite and is met.
Amended by AMENDMENT-0111-01 (produced by BRIEF-0111-D):
`EvaluatedStep.blocking` (`verdict.blocking_verdicts()`, () for none) --
what a `StepOutcome`'s `requirement_verdicts` holds, for the narration and
`_emit_new_knowledge`.

### C-08 — what a condition still lacks, `day_resolve.blocked_details_fr`
Produced by: BRIEF-0111-C   Consumed by: C, D
Signature: `blocked_details_fr(verdict: Optional[VerdictNode], db) ->
list[str]`.
Return shape: [] when met or None; else, walking the tree: an unmet leaf
-> `requirement_detail_fr(verdict)`; an unknown leaf -> its reason; under
a `not`, a MET leaf -> « il ne faut pas que : <leaf_text, first letter
lowered> ».
Amended by AMENDMENT-0111-01 (produced by BRIEF-0111-D):
`blocked_details_fr(verdict, db, viewer_id) -> list[str]` -- [] when met or
None; else walking `verdict.seen_by(viewer_id)`: an unmet leaf ->
`player_detail_fr(verdict, viewer_id, db)`; an unknown leaf -> its
`leaf_text(…, viewer_id)`, first letter lowered, then « (reason) »; under a
`not`, a MET leaf -> « il ne faut pas que : <leaf_text(…, viewer_id)> ».
`player_detail_fr(verdict, viewer_id, db) -> str` --
`HIDDEN_KNOWLEDGE_DETAIL_FR` (« il lui manque encore un fait à découvrir »)
for a `knowledge` verdict whose fact the viewer does not know, else
`requirement_detail_fr(verdict)`. Every caller is a player surface:
`quest_reads._steps_view`, `day_reconcile_apply`'s refusal; the narration's
`blocked_detail` calls `player_detail_fr` on the step's `blocking`.

### C-09 — what the surfaces read and send (`quest_reads`, `routes/quests`)
Produced by: BRIEF-0111-D   Consumed by: D (frontend)
Signature: `quest_reads.condition_view(db, tree) -> {"tree":
node_to_dict(tree), "flat": [leaf dict] | None, "lines": describe(...)}`
(`flat` None when the tree is not flat; a leaf dict carries `type`,
`target_entity_id`, `target_key`, `threshold`, `subject_role`,
`subject_entity_id`, `value`). `offer_dict`: `"eligibility"` a view; each
step `"prerequisite"` and `"completion"` views (no `"requirements"`).
`OfferBody.eligibility`, `OfferStepBody.prerequisite` / `.completion`:
`Optional[dict]` trees (C-03's dict form); a malformed tree -> 422, no row.
`_steps_view` adds `"completion": verdict_lines(...)` (every step) and
`"completion_met": bool | None`. Amended by AMENDMENT-0111-01: both as
the character may read them -- `verdict_lines(db, completion, character.id)`
and `completion.seen_by(character.id).met`; `"blocked"` is
`blocked_details_fr(..., character.id)`. `editor_choices` adds `"form_values":
{form: [{"value", "label"}]}`. No payload carries `agenda_id` or `step_id`.

## Context

Every agenda stores and judges a tree (C), and the storage already accepts a step's `completion` (C-06). This brief gives it a meaning on the surfaces (M1): « objectif atteint quand » on an offer step, copied at acceptance, judged and shown in Journée and in « Déclarer accomplie », never acted on. The offer API carries trees; the editor edits a flat condition as rows, each naming its subject, and shows a nested one read-only (T1).

Regenerated by AMENDMENT-0111-01 (Claude Code's STOP, trigger D1-a, R-23): every player surface reads a condition as the character may know it -- a fact he does not know is never written out (A1), a leaf about someone else reads « ? » (V2) -- and a blocked step names and teaches only the leaves that hold it back for its doer. If the earlier BRIEF-0111-D is applied but not committed in your working tree, first set it aside: `git stash push --include-untracked -m "BRIEF-0111-D before AMENDMENT-0111-01"` (keep the stash; never drop it), then confirm `git status` is clean.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md` and `src/world_engine/cockpit/static/` are not in the
diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `PlanStep.completion` (C-07); `write_quest_offer` and `accept_quest` write and copy each step's `completion`;
   - `quest_reads.condition_view`, `offer_dict`'s three views, `_steps_view`'s `completion` and `completion_met`, `editor_choices`'s `form_values` (C-09);
   - `routes/quests.py`: the bodies take trees; a malformed tree is a 422 with nothing written;
   - creates `frontend/src/creation/ConditionEditor.svelte` (a child component, never an island) and adapts the offer editor's files, `QuestPanel.svelte` and `SettlementRecap.svelte`;
   - AMENDMENT-0111-01 (C-04, C-05, C-07, C-08, b-6): `VerdictNode.seen_by` and `blocking_verdicts` in `conditions.py`; `known_to`, `HIDDEN_FACT_FR`, `HIDDEN_PROGRESS_FORMS` and a `viewer_id` on `leaf_text` / `verdict_lines` in `condition_text.py`; `player_detail_fr` and a `viewer_id` on `blocked_details_fr` in `day_resolve.py`, whose outcomes and narration read `EvaluatedStep.blocking` (`day_plan.py`); `quest_reads._steps_view` and `day_reconcile_apply.py` pass the character;
   - adds CD1-CD4 to `conditions.py` (CC4 passes the viewer);
   - appends the decision entry above the footer, with its AMENDMENT-0111-01 paragraph.
   The files it touches, exactly:
   - frontend/src/creation/ConditionEditor.svelte
   - frontend/src/creation/QuestOffers.svelte
   - frontend/src/creation/QuestRequirementRow.svelte
   - frontend/src/creation/questOffers.svelte.js
   - frontend/src/creation/questRequirements.js
   - frontend/src/journee/QuestPanel.svelte
   - frontend/src/journee/SettlementRecap.svelte
   - src/world_engine/cockpit/day_reconcile_apply.py
   - src/world_engine/cockpit/routes/quests.py
   - src/world_engine/condition_text.py
   - src/world_engine/conditions.py
   - src/world_engine/day_plan.py
   - src/world_engine/day_resolve.py
   - src/world_engine/quest_reads.py
   - src/world_engine/writes/quests.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/conditions.py
2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. Answer the escalation with Nia's words: `echo "A1, V2 -- AMENDMENT-0111-01" | python tooling/glue/question_response.py answer tooling/questions/QUESTION-TICKET-0111.md` (skip it if its `## Response` is already filled), and include the file in the commit.
4. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
5. Commit message: `feat(conditions): a quest step says when its objective is reached, shown and never acted on; the offer editor speaks trees (BRIEF-0111-d)`.

````diff
diff --git a/frontend/src/creation/ConditionEditor.svelte b/frontend/src/creation/ConditionEditor.svelte
new file mode 100644
index 0000000..8007b6a
--- /dev/null
+++ b/frontend/src/creation/ConditionEditor.svelte
@@ -0,0 +1,37 @@
+<script>
+  /* TICKET-0111 (BRIEF-0111-D, T1). One condition of a quest offer: a flat
+     condition is edited as a list of requirement rows (`all` of them); a
+     nested one is shown by its French lines, read-only, and saved back
+     unchanged -- the interpreter will edit it. `cond` is a draft object
+     owned by questOffersState (conditionDraft in questRequirements.js). */
+  import QuestRequirementRow from './QuestRequirementRow.svelte';
+  import { blankRequirement } from './questRequirements.js';
+
+  let { cond, choices, emptyLabel, addLabel } = $props();
+
+  function clearLocked() {
+    cond.locked = null;
+    cond.lines = [];
+  }
+</script>
+
+{#if cond.locked}
+  <div class="cond-locked">
+    {#each cond.lines as line, i (i)}
+      <div style={'padding-left:' + line.depth * 14 + 'px'}>{line.text}</div>
+    {/each}
+    <p class="muted">Condition imbriquée : elle se modifiera par l'interprète en langage naturel.</p>
+    <button onclick={() => clearLocked()}>Effacer cette condition</button>
+  </div>
+{:else}
+  {#if cond.list.length === 0 && emptyLabel}<p class="muted">{emptyLabel}</p>{/if}
+  {#each cond.list as req, i (i)}
+    <QuestRequirementRow {req} {choices} onremove={() => cond.list.splice(i, 1)} />
+  {/each}
+  <button onclick={() => cond.list.push(blankRequirement())}>{addLabel}</button>
+{/if}
+
+<style>
+  .cond-locked { border-left: 2px solid var(--border); padding: 2px 0 4px 8px; margin: 3px 0; }
+  .muted { color: var(--muted); font-size: 12px; }
+</style>
diff --git a/frontend/src/creation/QuestOffers.svelte b/frontend/src/creation/QuestOffers.svelte
index 440f493..8fa4faa 100644
--- a/frontend/src/creation/QuestOffers.svelte
+++ b/frontend/src/creation/QuestOffers.svelte
@@ -2,15 +2,16 @@
   /* TICKET-0108 (BRIEF-0108-C, E1). The « Quêtes » island: the world's
      quest offers and one offer's editor -- giver, title, summary,
      « répétable », open/closed, the conditions that decide who it is
-     offered to, and its steps with what each needs. Its CREATION_ISLANDS
+     offered to, and its steps with what each needs and -- TICKET-0111
+     (M1) -- when its objective is reached. Its CREATION_ISLANDS
      entry declares origin 'new'. Saving sends the whole offer; an accepted
      quest keeps its own copy (writes/quests.py). State and requests live in
      questOffers.svelte.js. */
   import { serverState } from '../lib/serverState.svelte.js';
-  import QuestRequirementRow from './QuestRequirementRow.svelte';
+  import ConditionEditor from './ConditionEditor.svelte';
   import QuestTermRow from './QuestTermRow.svelte';
   import {
-    questOffersState, loadOffers, newDraft, editOffer, saveDraft, blankStep, addRequirement,
+    questOffersState, loadOffers, newDraft, editOffer, saveDraft, blankStep,
     addTerm, refreshValue, saveEconomy,
   } from './questOffers.svelte.js';
   import { TERM_DIRECTIONS } from './questTerms.js';
@@ -133,11 +134,7 @@
         </div>
 
         <h4>Proposée à qui remplit</h4>
-        {#if draft.eligibility.length === 0}<p class="muted">Tout le monde.</p>{/if}
-        {#each draft.eligibility as req, i (i)}
-          <QuestRequirementRow {req} {choices} onremove={() => draft.eligibility.splice(i, 1)} />
-        {/each}
-        <button onclick={() => addRequirement(draft.eligibility)}>+ condition</button>
+        <ConditionEditor cond={draft.eligibility} {choices} emptyLabel="Tout le monde." addLabel="+ condition" />
 
         <h4>Étapes</h4>
         {#each draft.steps as step, i (i)}
@@ -159,10 +156,11 @@
               <button class="btn-icon" title="Retirer l'étape" disabled={draft.steps.length === 1}
                       onclick={() => draft.steps.splice(i, 1)}>✕</button>
             </div>
-            {#each step.requirements as req, j (j)}
-              <QuestRequirementRow {req} {choices} onremove={() => step.requirements.splice(j, 1)} />
-            {/each}
-            <button onclick={() => addRequirement(step.requirements)}>+ prérequis de l'étape</button>
+            <div class="muted">Prérequis</div>
+            <ConditionEditor cond={step.prerequisite} {choices} addLabel="+ prérequis de l'étape" />
+            <div class="muted">Objectif atteint quand</div>
+            <ConditionEditor cond={step.completion} {choices}
+                             emptyLabel="Rien de vérifiable : c'est vous qui le déclarez." addLabel="+ condition d'objectif" />
           </div>
         {/each}
         <button onclick={() => draft.steps.push(blankStep())}>+ étape</button>
diff --git a/frontend/src/creation/QuestRequirementRow.svelte b/frontend/src/creation/QuestRequirementRow.svelte
index 5d0b8ce..f357611 100644
--- a/frontend/src/creation/QuestRequirementRow.svelte
+++ b/frontend/src/creation/QuestRequirementRow.svelte
@@ -1,8 +1,10 @@
 <script>
   /* TICKET-0108 (BRIEF-0108-C). One requirement of a quest offer: its form,
      its target from the matching picker list, its threshold when the form
-     takes one. `req` is a draft object owned by questOffersState. */
-  import { REQUIREMENT_FORMS, targetOptions, valueOptions } from './questRequirements.js';
+     takes one. `req` is a draft object owned by questOffersState.
+     TICKET-0111: its subject first (P1), its value when the form compares
+     to one. */
+  import { REQUIREMENT_FORMS, subjectOptions, targetOptions, valueOptions } from './questRequirements.js';
 
   let { req, choices, onremove } = $props();
 
@@ -25,6 +27,12 @@
 </script>
 
 <div class="quest-req">
+  <select value={req.subject || 'role:doer'} title="Qui la condition juge"
+          onchange={(e) => { req.subject = e.target.value; }}>
+    {#each subjectOptions(choices) as o (o.value)}
+      <option value={o.value}>{o.label}</option>
+    {/each}
+  </select>
   <select value={req.type} onchange={(e) => setType(e.target.value)}>
     {#each Object.entries(REQUIREMENT_FORMS) as [type, f] (type)}
       <option value={type}>{f.label}</option>
diff --git a/frontend/src/creation/questOffers.svelte.js b/frontend/src/creation/questOffers.svelte.js
index 464efbc..5200e59 100644
--- a/frontend/src/creation/questOffers.svelte.js
+++ b/frontend/src/creation/questOffers.svelte.js
@@ -3,9 +3,12 @@
    one draft being edited. Saving sends the whole offer (PUT replaces its
    steps and requirements, writes/quests.py::write_quest_offer). Since
    TICKET-0109 (BRIEF-0109-D): its costs and rewards, their live indicative
-   value (POST /api/quest-offers/value), and the world's rates. */
+   value (POST /api/quest-offers/value), and the world's rates. Since
+   TICKET-0111 (BRIEF-0111-D): every condition -- the eligibility, each
+   step's prerequisite and completion -- is a condition draft, sent as a
+   tree (conditionBody). */
 import { api } from './sheetRequest.svelte.js';
-import { blankRequirement, requirementBody } from './questRequirements.js';
+import { blankCondition, conditionBody, conditionDraft } from './questRequirements.js';
 import { blankTerm, termBody } from './questTerms.js';
 
 export const questOffersState = $state({
@@ -13,7 +16,7 @@ export const questOffersState = $state({
   choices: null,
   loading: false,
   loadError: '',
-  draft: null, // { id|null, giver_entity_id, contact_entity_id, title, summary, repeatable, status, eligibility, steps }
+  draft: null, // { id|null, giver_entity_id, contact_entity_id, title, summary, repeatable, status, eligibility, steps, terms }
   saving: false,
   saveError: '',
   value: null, // the draft's indicative value (cost, reward, ratio_pct, verdict_label)
@@ -22,14 +25,14 @@ export const questOffersState = $state({
 });
 
 export function blankStep() {
-  return { objective: '', cost: 1, domain: '', requirements: [] };
+  return { objective: '', cost: 1, domain: '', prerequisite: blankCondition(), completion: blankCondition() };
 }
 
 export function newDraft() {
   questOffersState.saveError = '';
   questOffersState.draft = {
     id: null, giver_entity_id: '', contact_entity_id: '', title: '', summary: '', repeatable: false, status: 'open',
-    eligibility: [], steps: [blankStep()], terms: [],
+    eligibility: blankCondition(), steps: [blankStep()], terms: [],
   };
   refreshValue();
 }
@@ -40,10 +43,10 @@ export function editOffer(offer) {
     id: offer.id, giver_entity_id: offer.giver_entity_id, contact_entity_id: offer.contact_entity_id || '',
     title: offer.title, summary: offer.summary || '',
     repeatable: offer.repeatable, status: offer.status,
-    eligibility: offer.eligibility.map((r) => ({ ...r, target_entity_id: r.target_entity_id || '', target_key: r.target_key || '' })),
+    eligibility: conditionDraft(offer.eligibility),
     steps: offer.steps.map((s) => ({
       objective: s.objective, cost: s.cost, domain: s.domain || '',
-      requirements: s.requirements.map((r) => ({ ...r, target_entity_id: r.target_entity_id || '', target_key: r.target_key || '' })),
+      prerequisite: conditionDraft(s.prerequisite), completion: conditionDraft(s.completion),
     })),
     terms: (offer.terms || []).map((t) => ({
       direction: t.direction, currency: t.currency, counterparty_entity_id: t.counterparty_entity_id || '',
@@ -96,10 +99,6 @@ export async function saveEconomy(stored) {
   }
 }
 
-export function addRequirement(list) {
-  list.push(blankRequirement());
-}
-
 export async function loadOffers(worldId) {
   if (!worldId) { questOffersState.offers = []; questOffersState.choices = null; return; }
   questOffersState.loading = true;
@@ -121,10 +120,10 @@ function draftBody(draft) {
     giver_entity_id: draft.giver_entity_id, contact_entity_id: draft.contact_entity_id || null,
     title: draft.title, summary: draft.summary || null,
     repeatable: draft.repeatable, status: draft.status,
-    eligibility: draft.eligibility.map(requirementBody),
+    eligibility: conditionBody(draft.eligibility),
     steps: draft.steps.map((s) => ({
       objective: s.objective, cost: Number(s.cost), domain: s.domain || null,
-      requirements: s.requirements.map(requirementBody),
+      prerequisite: conditionBody(s.prerequisite), completion: conditionBody(s.completion),
     })),
     terms: draft.terms.map(termBody),
   };
diff --git a/frontend/src/creation/questRequirements.js b/frontend/src/creation/questRequirements.js
index f3ea6bd..0aa10d7 100644
--- a/frontend/src/creation/questRequirements.js
+++ b/frontend/src/creation/questRequirements.js
@@ -33,8 +33,23 @@ export const MONEY_KEY = 'monnaie';
 
 export const STEP_DOMAINS = ['physical', 'agility', 'perception', 'composure'];
 
+// TICKET-0111 (BRIEF-0111-D, P1): who a requirement judges -- a role bound
+// when it is judged, or one character (`entity:<id>`). Mirrors
+// `conditions.SUBJECT_ROLES` (kept equal by `conditions.py` CD1).
+export const SUBJECT_ROLES = {
+  doer: 'Le personnage',
+  giver: 'Le donneur',
+  contact: 'Le contact',
+};
+
 export function blankRequirement() {
-  return { type: 'has_met', target_entity_id: '', target_key: '', threshold: null, value: '' };
+  return { type: 'has_met', subject: 'role:doer', target_entity_id: '', target_key: '', threshold: null, value: '' };
+}
+
+/** The subject options: the three roles, then every character. */
+export function subjectOptions(choices) {
+  const roles = Object.entries(SUBJECT_ROLES).map(([role, label]) => ({ value: 'role:' + role, label }));
+  return roles.concat((choices?.characters || []).map((c) => ({ value: 'entity:' + c.id, label: c.name })));
 }
 
 /** The (value, label) options of a form's picker, from the editor's choices. */
@@ -61,11 +76,45 @@ export function valueOptions(form, choices) {
 /** The request body of one requirement row: only the columns its form uses. */
 export function requirementBody(req) {
   const form = REQUIREMENT_FORMS[req.type];
+  const [kind, id] = (req.subject || 'role:doer').split(':');
   return {
+    op: 'leaf',
     type: req.type,
+    subject_role: kind === 'role' ? id : null,
+    subject_entity_id: kind === 'entity' ? id : null,
     target_entity_id: form.column === 'entity' ? (req.target_entity_id || null) : null,
     target_key: form.list === 'money' ? MONEY_KEY : form.column === 'key' ? (req.target_key || null) : null,
     threshold: form.threshold ? (req.threshold === '' || req.threshold === null ? null : Number(req.threshold)) : null,
     value: form.values ? (req.value || null) : null,
   };
 }
+
+/* TICKET-0111 (BRIEF-0111-D, T1). A condition in the editor: `list`, the
+   rows of a flat condition (`all` of its leaves), or `locked`, a nested
+   tree shown read-only by its French `lines` and sent back unchanged --
+   only the interpreter will edit those. */
+
+/** The editor's draft of one condition, from the server's view (`quest_reads.condition_view`). */
+export function conditionDraft(view) {
+  if (view && !view.flat) return { list: [], locked: view.tree, lines: view.lines || [] };
+  return {
+    list: (view?.flat || []).map((r) => ({
+      ...r,
+      subject: r.subject_entity_id ? 'entity:' + r.subject_entity_id : 'role:' + (r.subject_role || 'doer'),
+      target_entity_id: r.target_entity_id || '', target_key: r.target_key || '', value: r.value || '',
+    })),
+    locked: null,
+    lines: [],
+  };
+}
+
+export function blankCondition() {
+  return { list: [], locked: null, lines: [] };
+}
+
+/** The tree a condition draft sends: the locked tree, `all` of the rows, or null. */
+export function conditionBody(cond) {
+  if (cond.locked) return cond.locked;
+  if (!cond.list.length) return null;
+  return { op: 'all', children: cond.list.map(requirementBody) };
+}
diff --git a/frontend/src/journee/QuestPanel.svelte b/frontend/src/journee/QuestPanel.svelte
index 87f23dd..fd8b811 100644
--- a/frontend/src/journee/QuestPanel.svelte
+++ b/frontend/src/journee/QuestPanel.svelte
@@ -5,7 +5,10 @@
      A quest is shown by its title and objectives; the plan behind it is
      never named here. TICKET-0109 (BRIEF-0109-D): each offer and quest
      lists its costs and rewards; « Déclarer accomplie » opens the measured
-     recap (SettlementRecap) and settles from it (D1). */
+     recap (SettlementRecap) and settles from it (D1). TICKET-0111
+     (BRIEF-0111-D, M1): the active step shows where its objective stands,
+     each line of its completion condition marked ✓, ✗ or ?, with its
+     progress (« 3/15 ») -- shown, never acted on. */
   import { questState, loadQuests, acceptOffer, abandonQuest, openSettlement } from './quests.svelte.js';
   import SettlementRecap from './SettlementRecap.svelte';
 
@@ -56,6 +59,16 @@
               {step.objective}
               {#if step.status === 'completed'} ✓{/if}
               {#each step.blocked as reason}<div class="muted">Il manque : {reason}</div>{/each}
+              {#if step.status === 'active' && step.completion?.length}
+                <div class="objective">
+                  <span class="muted">Objectif{step.completion_met ? ' atteint' : ''} :</span>
+                  {#each step.completion as line, i (i)}
+                    <div class={'cl-' + line.state} style={'padding-left:' + line.depth * 14 + 'px'}>
+                      {line.mark} {line.text}{#if line.progress} — {line.progress}{/if}
+                    </div>
+                  {/each}
+                </div>
+              {/if}
             </li>
           {/each}
         </ol>
@@ -85,4 +98,7 @@
   .step-completed, .step-failed { color: var(--muted); }
   .over { opacity: 0.7; }
   .terms { margin: 2px 0 6px 18px; padding: 0; font-size: 12px; }
+  .objective { font-weight: normal; font-size: 12px; margin: 2px 0; }
+  .cl-met { color: var(--green); }
+  .cl-unmet { color: var(--muted); }
 </style>
diff --git a/frontend/src/journee/SettlementRecap.svelte b/frontend/src/journee/SettlementRecap.svelte
index fd8c617..a6fecda 100644
--- a/frontend/src/journee/SettlementRecap.svelte
+++ b/frontend/src/journee/SettlementRecap.svelte
@@ -7,7 +7,9 @@
      quest is named by its quest_id only. TICKET-0110 (A2): when coins or
      items are all that is lacking, « Régler à crédit » shows what would be
      owed to whom -- a faction creditor's member to pick, its contact
-     preselected -- and settles with the rest as debts. */
+     preselected -- and settles with the rest as debts. TICKET-0111 (M1):
+     each step's completion condition, judged line by line -- measured, never
+     a verdict: Nia still decides. */
   import { questState, settleQuest, settleOnCredit } from './quests.svelte.js';
   import { loadJourneeDebts } from './debts.svelte.js';
 
@@ -38,7 +40,13 @@
     <h5>Étapes</h5>
     <ol>
       {#each ctx.steps as step (step.order)}
-        <li>{step.objective} — {step.status}{#if step.outcome} <span class="muted">({step.outcome})</span>{/if}</li>
+        <li>{step.objective} — {step.status}{#if step.outcome} <span class="muted">({step.outcome})</span>{/if}
+          {#each step.completion || [] as line, i (i)}
+            <div class="muted" style={'padding-left:' + line.depth * 14 + 'px'}>
+              {line.mark} {line.text}{#if line.progress} — {line.progress}{/if}
+            </div>
+          {/each}
+        </li>
       {/each}
     </ol>
 
diff --git a/src/world_engine/cockpit/day_reconcile_apply.py b/src/world_engine/cockpit/day_reconcile_apply.py
index 4b4dd24..715e643 100644
--- a/src/world_engine/cockpit/day_reconcile_apply.py
+++ b/src/world_engine/cockpit/day_reconcile_apply.py
@@ -71,7 +71,7 @@ def _refuse_unstarted_plan(character: Character, agenda: Agenda, db: Session) ->
             ),
         )
     evaluated = evaluate_agenda_step(pending_step, character, db)
-    unmet = blocked_details_fr(evaluated.verdict, db)
+    unmet = blocked_details_fr(evaluated.verdict, db, character.id)
     detail = "; ".join(unmet) if unmet else (
         "aucun prerequis non satisfait - le veto de faisabilite a juge l'action elle-meme irrealisable"
     )
diff --git a/src/world_engine/cockpit/routes/quests.py b/src/world_engine/cockpit/routes/quests.py
index 5f7fb89..71e2385 100644
--- a/src/world_engine/cockpit/routes/quests.py
+++ b/src/world_engine/cockpit/routes/quests.py
@@ -31,8 +31,7 @@ from pydantic import BaseModel, Field
 from sqlmodel import Session, select
 
 from ... import quest_reads
-from ...condition_forms import RequirementSpec
-from ...conditions import all_of
+from ...conditions import node_from_dict
 from ...day_plan import PlanStep
 from ...db import get_session
 from ...models import Quest, QuestEconomy, QuestOffer
@@ -49,23 +48,14 @@ from .day import _resolve_player_character
 router = APIRouter()
 
 
-class RequirementBody(BaseModel):
-    type: str
-    target_entity_id: Optional[str] = None
-    target_key: Optional[str] = None
-    threshold: Optional[int] = None
-    # TICKET-0111 (P1, S1): the leaf's subject (a role, else one entity) and
-    # the value of a form that compares to one.
-    subject_role: Optional[str] = None
-    subject_entity_id: Optional[str] = None
-    value: Optional[str] = None
-
-
 class OfferStepBody(BaseModel):
     objective: str
     cost: int
     domain: Optional[str] = None
-    requirements: list[RequirementBody] = Field(default_factory=list)
+    # TICKET-0111 (I1, M1): a step's conditions are trees in the dict form of
+    # `conditions.node_to_dict`; null is none.
+    prerequisite: Optional[dict] = None
+    completion: Optional[dict] = None
 
 
 class TermBody(BaseModel):
@@ -87,7 +77,7 @@ class OfferBody(BaseModel):
     summary: Optional[str] = None
     repeatable: bool = False
     status: str = "open"
-    eligibility: list[RequirementBody] = Field(default_factory=list)
+    eligibility: Optional[dict] = None
     steps: list[OfferStepBody] = Field(default_factory=list)
     # TICKET-0109 (B1): the offer's costs and rewards, replaced whole; absent
     # (None) keeps the stored ones.
@@ -123,22 +113,15 @@ class CreditBody(BaseModel):
     contacts: dict[str, str] = Field(default_factory=dict)
 
 
-def _spec(req: RequirementBody) -> RequirementSpec:
-    subject_entity_id = req.subject_entity_id or None
-    return RequirementSpec(type=req.type, target_entity_id=req.target_entity_id or None,
-                           target_key=req.target_key or None, threshold=req.threshold,
-                           subject_role=req.subject_role or (None if subject_entity_id else "doer"),
-                           subject_entity_id=subject_entity_id, value=req.value or None)
-
-
 def _save_offer(body: OfferBody, offer: Optional[QuestOffer], world_id: str, db: Session) -> dict:
-    steps = [PlanStep(objective=s.objective, cost=s.cost, domain=s.domain or None,
-                      prerequisite=all_of(_spec(r) for r in s.requirements)) for s in body.steps]
     try:
+        steps = [PlanStep(objective=s.objective, cost=s.cost, domain=s.domain or None,
+                          prerequisite=node_from_dict(s.prerequisite), completion=node_from_dict(s.completion))
+                 for s in body.steps]
         offer = write_quest_offer(
             db, world_id=world_id, offer=offer, giver_entity_id=body.giver_entity_id, title=body.title,
             summary=body.summary, repeatable=body.repeatable, status=body.status,
-            eligibility=all_of(_spec(r) for r in body.eligibility), steps=steps,
+            eligibility=node_from_dict(body.eligibility), steps=steps,
             terms=None if body.terms is None else [_term(t) for t in body.terms],
             contact_entity_id=body.contact_entity_id or None,
         )
diff --git a/src/world_engine/condition_text.py b/src/world_engine/condition_text.py
index d92e03b..d239b7d 100644
--- a/src/world_engine/condition_text.py
+++ b/src/world_engine/condition_text.py
@@ -7,6 +7,11 @@ its state and, for a form that counts, its progress (« 3/15 »). Both are
 read by the surfaces; neither decides anything. Every phrase comes from
 `FORM_PHRASES_FR`, one per form, kept equal to `REQUIREMENT_TYPES` by
 `conditions.py` CB4.
+
+A player surface passes its character as `viewer_id` (AMENDMENT-0111-01):
+a fact he does not know is never written out (A1, `HIDDEN_FACT_FR`), a leaf
+about someone else shows `?` (V2, `VerdictNode.seen_by`), and no line
+counts another's regard toward him. The creator reads every line whole.
 """
 
 from __future__ import annotations
@@ -17,6 +22,7 @@ from sqlmodel import Session
 
 from .condition_forms import RequirementSpec
 from .conditions import ConditionTree, VerdictNode
+from .knowledge_resolve import resolve_knowledge_level
 from .models import Entity, Fact, QuestOffer
 from .prose_render import fact_text
 from .skill_access import skill_label
@@ -56,6 +62,20 @@ SUBJECT_LABELS_FR: dict[str, str] = {"doer": "le personnage", "giver": "le donne
 
 STATE_MARKS: dict[str, str] = {"met": "✓", "unmet": "✗", "unknown": "?"}
 
+# A1 (AMENDMENT-0111-01): what a player reads in place of a fact his
+# character does not know -- a secret, the creator's note, or simply a fact
+# still to learn.
+HIDDEN_FACT_FR = "{who} connaît un fait encore caché"
+
+# Forms whose progress a player never sees: the count is another's regard.
+HIDDEN_PROGRESS_FORMS: tuple[str, ...] = ("relation_gte",)
+
+
+def known_to(db: Session, viewer_id: str, fact_id: Optional[str]) -> bool:
+    """A1: the viewer resolves the fact above `unaware` (stored row, scope
+    defaults and contacts, `knowledge_resolve`)."""
+    return bool(fact_id) and resolve_knowledge_level(db, viewer_id, fact_id) != "unaware"
+
 
 def _entity_name(db: Session, entity_id: Optional[str]) -> str:
     entity = db.get(Entity, entity_id) if entity_id else None
@@ -82,10 +102,14 @@ def _subject(db: Session, spec: RequirementSpec) -> str:
     return _entity_name(db, spec.subject_entity_id)
 
 
-def leaf_text(db: Session, spec: RequirementSpec) -> str:
+def leaf_text(db: Session, spec: RequirementSpec, viewer_id: Optional[str] = None) -> str:
+    """One leaf in French. With `viewer_id` (a player surface), a fact the
+    viewer does not know is not written out (A1)."""
     phrase = FORM_PHRASES_FR.get(spec.type)
     if phrase is None:
         raise ValueError(f"condition_text: unknown requirement type {spec.type!r}")
+    if spec.type == "knowledge" and viewer_id is not None and not known_to(db, viewer_id, spec.target_key):
+        phrase = HIDDEN_FACT_FR
     value = VALUE_LABELS_FR.get(spec.type, {}).get(spec.value, spec.value)
     text = phrase.format(who=_subject(db, spec), target=_target(db, spec), threshold=spec.threshold, value=value)
     return text[0].upper() + text[1:]
@@ -113,9 +137,9 @@ def _describe(db: Session, node: ConditionTree, depth: int, lines: list[dict]) -
         _describe(db, child, depth + 1, lines)
 
 
-def _progress(verdict_node: VerdictNode) -> Optional[str]:
+def _progress(verdict_node: VerdictNode, viewer_id: Optional[str] = None) -> Optional[str]:
     verdict = verdict_node.verdict
-    if verdict is None:
+    if verdict is None or (viewer_id is not None and verdict.type in HIDDEN_PROGRESS_FORMS):
         return None
     current, required = verdict.current, verdict.required
     if isinstance(current, int) and isinstance(required, int) and not isinstance(current, bool):
@@ -123,24 +147,27 @@ def _progress(verdict_node: VerdictNode) -> Optional[str]:
     return None
 
 
-def verdict_lines(db: Session, verdict: Optional[VerdictNode]) -> list[dict]:
+def verdict_lines(db: Session, verdict: Optional[VerdictNode], viewer_id: Optional[str] = None) -> list[dict]:
     """A judged tree as lines: `{"depth", "text", "state", "mark",
-    "progress"}`; an `unknown` leaf's text ends with why."""
+    "progress"}`; an `unknown` leaf's text ends with why. With `viewer_id`
+    (a player surface), the verdict is first `seen_by` him (V2) and every
+    leaf is written as he may read it (A1)."""
     lines: list[dict] = []
     if verdict is not None:
-        _verdict_lines(db, verdict, 0, lines)
+        seen = verdict.seen_by(viewer_id) if viewer_id is not None else verdict
+        _verdict_lines(db, seen, 0, lines, viewer_id)
     return lines
 
 
-def _verdict_lines(db: Session, node: VerdictNode, depth: int, lines: list[dict]) -> None:
+def _verdict_lines(db: Session, node: VerdictNode, depth: int, lines: list[dict], viewer_id: Optional[str]) -> None:
     if node.op == "leaf":
-        text = leaf_text(db, node.spec)
+        text = leaf_text(db, node.spec, viewer_id)
         if node.state == "unknown" and node.reason:
             text = f"{text} ({node.reason})"
         lines.append({"depth": depth, "text": text, "state": node.state, "mark": STATE_MARKS[node.state],
-                      "progress": _progress(node)})
+                      "progress": _progress(node, viewer_id)})
         return
     lines.append({"depth": depth, "text": _head(node.op, node.n), "state": node.state,
                   "mark": STATE_MARKS[node.state], "progress": None})
     for child in node.children:
-        _verdict_lines(db, child, depth + 1, lines)
+        _verdict_lines(db, child, depth + 1, lines, viewer_id)
diff --git a/src/world_engine/conditions.py b/src/world_engine/conditions.py
index 31579ba..4a3685b 100644
--- a/src/world_engine/conditions.py
+++ b/src/world_engine/conditions.py
@@ -18,6 +18,11 @@ A verdict has three states (R1): `met`, `unmet`, `unknown`. The connectors
 follow Kleene's three-valued logic, so an `unknown` leaf can still be
 outweighed (`any` with a met sibling is met). A gate passes only on `met`.
 
+A player sees a verdict only as his character could (AMENDMENT-0111-01,
+V2): `VerdictNode.seen_by` turns every judged leaf about someone else -- the
+giver, the contact, another character -- into `unknown`, and recombines the
+connectors from what is left. The creator's surfaces read the verdict whole.
+
 This module writes nothing: it reads the canon through the evaluators and
 reads a stored tree back (`read_condition`). Its writer is
 `writes/conditions.py`.
@@ -25,7 +30,7 @@ reads a stored tree back (`read_condition`). Its writer is
 
 from __future__ import annotations
 
-from dataclasses import dataclass
+from dataclasses import dataclass, replace
 from typing import Optional
 
 from sqlmodel import Session, select
@@ -96,6 +101,51 @@ class VerdictNode:
         `unknown` leaf has none."""
         return tuple(node.verdict for node in self.leaf_nodes() if node.verdict is not None)
 
+    def blocking_verdicts(self) -> tuple[Verdict, ...]:
+        """The verdicts of the leaves that hold this condition back for the
+        one who acts (AMENDMENT-0111-01): judged on `doer`, unmet, and not
+        under a `not` (an unmet leaf under a `not` is what the condition
+        wants). What a blocked day step names and teaches reads these only."""
+        found: list[Verdict] = []
+        _blocking(self, False, found)
+        return tuple(found)
+
+    def seen_by(self, viewer_id: str) -> "VerdictNode":
+        """This verdict as the character `viewer_id` could know it (V2): a
+        judged leaf whose subject is not him becomes `unknown` -- he cannot
+        see whether the giver knows a fact or whether another is alive --
+        and every connector is recombined from what is left, so no head
+        line betrays a hidden leaf."""
+        if self.op == "leaf":
+            if self.verdict is None or _seen_subject(self.spec, viewer_id):
+                return self
+            return replace(self, state="unknown", verdict=None, reason=UNSEEN_REASON_FR)
+        children = tuple(child.seen_by(viewer_id) for child in self.children)
+        return replace(self, state=_combine(self, children), children=children)
+
+
+# V2 (AMENDMENT-0111-01): why a leaf about someone else shows `?` to a player.
+UNSEEN_REASON_FR = "le personnage ne peut pas le vérifier"
+
+
+def _seen_subject(spec: Optional[RequirementSpec], viewer_id: str) -> bool:
+    """A leaf is about the viewer when it judges `doer` (the viewer, on
+    every player surface) or names him as its fixed subject."""
+    if spec is None:
+        return False
+    return spec.subject_role == "doer" or (spec.subject_entity_id is not None and spec.subject_entity_id == viewer_id)
+
+
+def _blocking(node: "VerdictNode", negated: bool, found: list) -> None:
+    if node.op == "not":
+        _blocking(node.children[0], not negated, found)
+    elif node.op != "leaf":
+        for child in node.children:
+            _blocking(child, negated, found)
+    elif (not negated and node.state == "unmet" and node.verdict is not None
+          and node.spec is not None and node.spec.subject_role == "doer"):
+        found.append(node.verdict)
+
 
 # --- building ------------------------------------------------------------------
 
diff --git a/src/world_engine/day_plan.py b/src/world_engine/day_plan.py
index f969023..3b8dfef 100644
--- a/src/world_engine/day_plan.py
+++ b/src/world_engine/day_plan.py
@@ -77,18 +77,23 @@ DAY_PLAN_OPTIONS: dict = {"repeat_penalty": 1.1, "repeat_last_n": 128}
 class PlanStep:
     """One step of a plan. Its `prerequisite` is a condition tree
     (TICKET-0111, I1) -- `all` of the model's leaves for a day plan, any
-    tree for a quest step; None when nothing gates it."""
+    tree for a quest step; None when nothing gates it. `completion` (M1,
+    BRIEF-0111-D) says when a quest step's objective is reached: shown,
+    never acted on; a day plan has none."""
     objective: str
     cost: Optional[int]
     domain: Optional[str]
     prerequisite: Optional[ConditionTree] = None
+    completion: Optional[ConditionTree] = None
 
 
 @dataclass(frozen=True)
 class EvaluatedStep:
     """A step and its judged prerequisite (None: nothing gates it). It is
     `met` only when the verdict is (R1: `unknown` does not pass);
-    `verdicts` are the judged leaves, in order, for the day's narration."""
+    `verdicts` are the judged leaves, in order; `blocking` the ones that hold
+    the step back for its doer (AMENDMENT-0111-01) -- what a blocked step
+    names to the narration and teaches."""
     step: PlanStep
     verdict: Optional[VerdictNode] = None
 
@@ -100,6 +105,10 @@ class EvaluatedStep:
     def verdicts(self) -> tuple[Verdict, ...]:
         return () if self.verdict is None else self.verdict.leaf_verdicts()
 
+    @property
+    def blocking(self) -> tuple[Verdict, ...]:
+        return () if self.verdict is None else self.verdict.blocking_verdicts()
+
 
 @dataclass(frozen=True)
 class BudgetResult:
diff --git a/src/world_engine/day_resolve.py b/src/world_engine/day_resolve.py
index cfe728a..7478071 100644
--- a/src/world_engine/day_resolve.py
+++ b/src/world_engine/day_resolve.py
@@ -67,7 +67,7 @@ from typing import Optional
 from sqlmodel import Session, select
 
 from .condition_forms import Verdict as RequirementVerdict
-from .condition_text import leaf_text
+from .condition_text import known_to, leaf_text
 from .conditions import VerdictNode, leaves
 from .day_concordance import ConcordanceResult
 from .day_plan import (
@@ -247,7 +247,7 @@ def _truncate_on_failure(rolled: list[_RolledStep]) -> list[StepOutcome]:
             domain=item.evaluated.step.domain,
             verdict=item.verdict,
             band=item.band,
-            requirement_verdicts=item.evaluated.verdicts,
+            requirement_verdicts=item.evaluated.blocking,
             canon_ids=item.canon_ids,
         ))
         if item.band == "failure":
@@ -290,32 +290,49 @@ def requirement_detail_fr(verdict: RequirementVerdict) -> str:
     return template.format(required=getattr(verdict, "required_label", None) or verdict.required)
 
 
-def blocked_details_fr(verdict: Optional[VerdictNode], db: Session) -> list[str]:
-    """What a judged condition still lacks, in player-facing French
-    (TICKET-0111): an unmet leaf's `requirement_detail_fr`, an unknown
-    leaf's reason, and -- under a `not` -- a leaf that holds when it must
-    not. [] when the condition is met or absent."""
+# A1 (AMENDMENT-0111-01): what the player and the narration read for a fact
+# his character does not know, in place of `_BLOCKED_DETAIL_FR["knowledge"]`.
+HIDDEN_KNOWLEDGE_DETAIL_FR = "il lui manque encore un fait à découvrir"
+
+
+def player_detail_fr(verdict: RequirementVerdict, viewer_id: str, db: Session) -> str:
+    """`requirement_detail_fr` as the character `viewer_id` may read it
+    (A1): a `knowledge` leaf names its fact only when he knows it."""
+    if verdict.type == "knowledge" and not known_to(db, viewer_id, verdict.required):
+        return HIDDEN_KNOWLEDGE_DETAIL_FR
+    return requirement_detail_fr(verdict)
+
+
+def blocked_details_fr(verdict: Optional[VerdictNode], db: Session, viewer_id: str) -> list[str]:
+    """What a judged condition still lacks, in player-facing French, as the
+    character `viewer_id` may read it (TICKET-0111, AMENDMENT-0111-01): the
+    verdict is first `seen_by` him (V2); then an unmet leaf's
+    `player_detail_fr` (A1), an unknown leaf's text and reason, and -- under
+    a `not` -- a leaf that holds when it must not. [] when the condition is
+    met or absent."""
     if verdict is None or verdict.met:
         return []
     details: list[str] = []
-    _blocked(verdict, db, False, details)
+    _blocked(verdict.seen_by(viewer_id), db, viewer_id, False, details)
     return details
 
 
-def _blocked(node: VerdictNode, db: Session, negated: bool, details: list[str]) -> None:
+def _blocked(node: VerdictNode, db: Session, viewer_id: str, negated: bool, details: list[str]) -> None:
     if node.op == "not":
-        _blocked(node.children[0], db, not negated, details)
+        _blocked(node.children[0], db, viewer_id, not negated, details)
         return
     if node.op != "leaf":
         for child in node.children:
-            _blocked(child, db, negated, details)
+            _blocked(child, db, viewer_id, negated, details)
         return
     if node.state == "unknown":
-        details.append(node.reason or "une condition ne peut pas être vérifiée")
+        text = leaf_text(db, node.spec, viewer_id)
+        reason = node.reason or "une condition ne peut pas être vérifiée"
+        details.append(f"{text[0].lower()}{text[1:]} ({reason})")
     elif node.state == "unmet" and not negated:
-        details.append(requirement_detail_fr(node.verdict))
+        details.append(player_detail_fr(node.verdict, viewer_id, db))
     elif node.state == "met" and negated:
-        text = leaf_text(db, node.spec)
+        text = leaf_text(db, node.spec, viewer_id)
         details.append(f"il ne faut pas que : {text[0].lower()}{text[1:]}")
 
 
@@ -357,7 +374,7 @@ def _append_blocked_step(
         domain=evaluated.step.domain,
         verdict=None,
         band=BLOCKED_BAND,
-        requirement_verdicts=evaluated.verdicts,
+        requirement_verdicts=evaluated.blocking,
         canon_ids=canon_ids,
     ))
 
@@ -459,7 +476,7 @@ def freeze_facts(
             modifier=o.verdict.modifier if o.verdict is not None else None,
             total=o.verdict.total if o.verdict is not None else None,
             blocked_detail=(
-                " ; ".join(requirement_detail_fr(v) for v in o.requirement_verdicts if not v.met)
+                " ; ".join(player_detail_fr(v, character.id, db) for v in o.requirement_verdicts if not v.met)
                 if o.band == BLOCKED_BAND else None
             ),
         )
diff --git a/src/world_engine/quest_reads.py b/src/world_engine/quest_reads.py
index 22a666d..7bb2bfa 100644
--- a/src/world_engine/quest_reads.py
+++ b/src/world_engine/quest_reads.py
@@ -18,10 +18,10 @@ from typing import Optional
 from sqlmodel import Session, select
 
 from .condition_forms import FORM_VALUES
-from .condition_text import VALUE_LABELS_FR
-from .conditions import flat_leaves, read_condition
+from .condition_text import VALUE_LABELS_FR, describe, verdict_lines
+from .conditions import evaluate, flat_leaves, node_to_dict, read_condition
 from .day_resolve import blocked_details_fr
-from .day_plan import evaluate_agenda_step
+from .day_plan import evaluate_agenda_step, plan_bindings
 from .models import (
     BASE_SKILL_DOMAINS,
     Agenda,
@@ -58,14 +58,13 @@ def _requirement_dict(req) -> dict:
             "subject_entity_id": req.subject_entity_id, "value": req.value}
 
 
-def _requirement_list(tree) -> list[dict]:
-    """A flat condition as the editor's list (T1). Until the surfaces read
-    trees (BRIEF-0111-D), every stored condition is flat: nothing else can
-    be written."""
+def condition_view(db: Session, tree) -> dict:
+    """One condition as the editor reads it (TICKET-0111, T1): the tree
+    itself, its leaves when it is flat (the list the editor edits; None when
+    it is not -- shown, sent back unchanged), and its French lines."""
     flat = flat_leaves(tree)
-    if flat is None:
-        raise ValueError("a nested condition cannot be read as a list")
-    return [_requirement_dict(r) for r in flat]
+    return {"tree": node_to_dict(tree), "flat": None if flat is None else [_requirement_dict(r) for r in flat],
+            "lines": describe(db, tree)}
 
 
 def _name(db: Session, entity_id: Optional[str]) -> Optional[str]:
@@ -84,10 +83,11 @@ def offer_dict(offer: QuestOffer, db: Session) -> dict:
         # TICKET-0110 (X1): a faction giver's contact.
         "contact_entity_id": offer.contact_entity_id, "contact_name": _name(db, offer.contact_entity_id),
         "title": offer.title, "summary": offer.summary, "repeatable": offer.repeatable, "status": offer.status,
-        "eligibility": _requirement_list(read_condition(db, role="eligibility", quest_offer_id=offer.id)),
+        "eligibility": condition_view(db, read_condition(db, role="eligibility", quest_offer_id=offer.id)),
         "steps": [{
             "objective": step.objective, "cost": step.cost, "domain": step.domain,
-            "requirements": _requirement_list(read_condition(db, role="prerequisite", quest_offer_step_id=step.id)),
+            "prerequisite": condition_view(db, read_condition(db, role="prerequisite", quest_offer_step_id=step.id)),
+            "completion": condition_view(db, read_condition(db, role="completion", quest_offer_step_id=step.id)),
         } for step in steps],
         # TICKET-0109 (B1, C1): the costs and rewards, and their indicative value.
         "terms": [term_dict(db, t, offer.giver_entity_id) for t in terms],
@@ -159,16 +159,26 @@ def available_offers(character: Character, db: Session) -> list[QuestOffer]:
 
 
 def _steps_view(agenda: Agenda, character: Character, db: Session) -> list[dict]:
+    """Each step: what the active one still needs, and -- M1 (TICKET-0111) --
+    where its objective stands, every line of its completion condition
+    judged (« 3/15 »); [] when it has none. Shown, never acted on. A player
+    surface: every line is as the character may read it (AMENDMENT-0111-01,
+    A1 and V2), `completion_met` included."""
     steps = db.exec(select(AgendaStep).where(AgendaStep.agenda_id == agenda.id)
                     .order_by(AgendaStep.step_order)).all()
+    bindings = plan_bindings(agenda.id, character, db)
     view = []
     for step in steps:
         blocked: list[str] = []
         if step.status == "active":
             evaluated = evaluate_agenda_step(step, character, db)
-            blocked = blocked_details_fr(evaluated.verdict, db)
+            blocked = blocked_details_fr(evaluated.verdict, db, character.id)
+        completion = evaluate(read_condition(db, role="completion", agenda_step_id=step.id), bindings, db)
+        seen = completion.seen_by(character.id) if completion is not None else None
         view.append({"order": step.step_order, "objective": step.objective, "status": step.status,
-                     "outcome": step.outcome, "blocked": blocked})
+                     "outcome": step.outcome, "blocked": blocked,
+                     "completion": verdict_lines(db, completion, character.id),
+                     "completion_met": seen.met if seen is not None else None})
     return view
 
 
diff --git a/src/world_engine/writes/quests.py b/src/world_engine/writes/quests.py
index 61431b2..0c2f221 100644
--- a/src/world_engine/writes/quests.py
+++ b/src/world_engine/writes/quests.py
@@ -7,7 +7,8 @@ contract C-03).
   set); the offer row snapshots its previous state into `change_history`.
 - `accept_quest(...)`      : the player takes an offer (B1, A1): one agenda
   born `paused` through `write_agenda`, its steps (the first `active`, the
-  creator-agenda precedent) and their conditions copied from the offer,
+  creator-agenda precedent) and their conditions -- prerequisite and, since
+  BRIEF-0111-D, completion (M1) -- copied from the offer,
   the `quest` row, and its own copy of the offer's terms (TICKET-0109, B1). Eligibility and L1 are judged HERE, so no caller can
   skip them.
 - `abandon_quest(...)`     : N1, the quest's agenda to `abandoned` through
@@ -54,10 +55,10 @@ QUEST_GIVER_TYPES: tuple[str, ...] = ("character", "faction")
 OPEN_QUEST_STATUSES: tuple[str, ...] = ("active", "paused")
 
 
-def _clean_offer_steps(db: Session, world_id: str, steps: list[PlanStep]) -> list[tuple[PlanStep, object]]:
+def _clean_offer_steps(db: Session, world_id: str, steps: list[PlanStep]) -> list[tuple[PlanStep, object, object]]:
     if not 1 <= len(steps) <= MAX_PLAN_STEPS:
         raise ValueError(f"write_quest_offer: an offer has 1 to {MAX_PLAN_STEPS} steps, got {len(steps)}")
-    clean: list[tuple[PlanStep, object]] = []
+    clean: list[tuple[PlanStep, object, object]] = []
     for index, step in enumerate(steps):
         if not isinstance(step.objective, str) or not step.objective.strip():
             raise ValueError(f"write_quest_offer: step {index} needs an objective")
@@ -65,7 +66,9 @@ def _clean_offer_steps(db: Session, world_id: str, steps: list[PlanStep]) -> lis
             raise ValueError(f"write_quest_offer: step {index} has invalid cost {step.cost!r}")
         if step.domain is not None and step.domain not in BASE_SKILL_DOMAINS:
             raise ValueError(f"write_quest_offer: step {index} has invalid domain {step.domain!r}")
-        clean.append((step, clean_condition(db, world_id, step.prerequisite, f"write_quest_offer: step {index}: ")))
+        where = f"write_quest_offer: step {index}: "
+        clean.append((step, clean_condition(db, world_id, step.prerequisite, where),
+                      clean_condition(db, world_id, step.completion, where)))
     return clean
 
 
@@ -128,7 +131,8 @@ def write_quest_offer(
         raise ValueError(f"write_quest_offer: status must be one of {QUEST_OFFER_STATUSES}, got {status!r}")
     _check_giver(db, world_id, giver_entity_id)
     _check_contact(db, world_id, giver_entity_id, contact_entity_id or None)
-    every = list(leaves(eligibility)) + [req for step in steps for req in leaves(step.prerequisite)]
+    every = list(leaves(eligibility)) + [req for step in steps
+                                         for req in leaves(step.prerequisite) + leaves(step.completion)]
     if offer is not None and any(r.type == "quest_state" and r.target_key == offer.id for r in every):
         raise ValueError("write_quest_offer: an offer cannot require its own state")
     clean_eligibility = clean_condition(db, world_id, eligibility, "write_quest_offer: eligibility: ")
@@ -154,12 +158,13 @@ def write_quest_offer(
     db.flush()
 
     write_condition(db, world_id=world_id, role="eligibility", tree=clean_eligibility, quest_offer_id=offer.id)
-    for order, (step, prerequisite) in enumerate(clean_steps, start=1):
+    for order, (step, prerequisite, completion) in enumerate(clean_steps, start=1):
         row = QuestOfferStep(world_id=world_id, offer_id=offer.id, step_order=order,
                              objective=step.objective.strip(), cost=step.cost, domain=step.domain)
         db.add(row)
         db.flush()
         write_condition(db, world_id=world_id, role="prerequisite", tree=prerequisite, quest_offer_step_id=row.id)
+        write_condition(db, world_id=world_id, role="completion", tree=completion, quest_offer_step_id=row.id)
     write_offer_terms(db, world_id=world_id, offer_id=offer.id, clean=clean_term_rows)
     return offer
 
@@ -204,17 +209,19 @@ def accept_quest(db: Session, *, offer: QuestOffer, character: Character) -> Que
                     .order_by(QuestOfferStep.step_order)).all()
     if not steps:
         raise ValueError("accept_quest: the offer has no step")
-    copied = [(step, read_condition(db, role="prerequisite", quest_offer_step_id=step.id)) for step in steps]
+    copied = [(step, {role: read_condition(db, role=role, quest_offer_step_id=step.id)
+                      for role in ("prerequisite", "completion")}) for step in steps]
 
     agenda = write_agenda(db, world_id=offer.world_id, owner_entity_id=character.id, title=offer.title,
                           status="paused")
     db.flush()
-    for step, prerequisite in copied:
+    for step, conditions in copied:
         row = write_agenda_step(db, agenda_id=agenda.id, step_order=step.step_order, objective=step.objective,
                                 status="active" if step.step_order == 1 else "pending",
                                 cost=step.cost, domain=step.domain)
         db.flush()
-        write_condition(db, world_id=offer.world_id, role="prerequisite", tree=prerequisite, agenda_step_id=row.id)
+        for role, tree in conditions.items():
+            write_condition(db, world_id=offer.world_id, role=role, tree=tree, agenda_step_id=row.id)
     quest = Quest(world_id=offer.world_id, offer_id=offer.id, character_id=character.id, agenda_id=agenda.id)
     db.add(quest)
     db.flush()
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 340a405..6fa0e00 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18469,6 +18469,58 @@ GP1: `goal_prerequisite` (an NPC goal's completion gate, one form) is a
 third language left out of this ticket; its own ticket, once this one is
 stable.
 
+## A QUEST STEP SAYS WHEN ITS OBJECTIVE IS REACHED (TICKET-0111) -- SHOWN, NEVER ACTED ON; THE EDITOR SPEAKS TREES (BRIEF-0111-d, no schema change)
+
+**M1.** An offer step gains a `completion` condition beside its
+prerequisite: « objectif atteint quand ». It is copied to the agenda step at
+acceptance, judged on the quest's bindings, and shown -- in Journée under
+the active step, each line marked ✓, ✗ or ? with its progress (« 3/5 »),
+and in the recap of « Déclarer accomplie » for every step. It never moves a
+step nor settles a quest: Nia still declares (F1 of the series, G1 of
+0109). Rejected: M2 (completing on its own when the condition is met;
+reactivation: Nia confirming what the condition already says, measured on
+the dashboard once it exists).
+
+**The API speaks trees.** `POST`/`PUT /api/quest-offers` take each
+condition -- the eligibility, a step's prerequisite and completion -- as a
+tree in `conditions.node_to_dict`'s dict form; a malformed one answers 422
+with nothing written. `offer_dict` returns each condition as a view: the
+tree, its rows when it is flat, its French lines.
+
+**T1.** The editor edits a flat condition as a list of rows (`all` of
+them), each row naming its subject first (P1: the character, the giver,
+the contact, or one character) and, for a form that takes one, its value.
+A nested condition is shown by its lines, read-only, saved back unchanged,
+and can be cleared: the interpreter (TICKET-0112) will write and edit those.
+
+**Rejected.** T2 (a visual tree editor): much frontend for what the
+interpreter will do in prose.
+
+**What a player may read (AMENDMENT-0111-01, A1, V2).** A condition shown
+on a player surface -- Journée's quest panel, « Déclarer accomplie », the
+refusal of a standing plan, a blocked step's line in the day's narration --
+is read as the character may know it, never as the canon holds it.
+A1: a fact he does not resolve above `unaware` (`knowledge_resolve`) is
+never written out -- a secret, the creator's note, a fact still to learn
+read « un fait encore caché » (`condition_text.HIDDEN_FACT_FR`,
+`day_resolve.HIDDEN_KNOWLEDGE_DETAIL_FR`). V2: a judged leaf about someone
+else -- the giver, the contact, a named character -- reads `?`
+(`VerdictNode.seen_by`), and every head line is recombined from what is
+left, so « Objectif atteint » never rests on a hidden leaf; the count of a
+`relation_gte` (another's regard toward him) is never shown. A leaf about
+the character himself is shown as it stands, its target named. The
+creator's surfaces read the verdict whole. The fact text had reached the
+player since TICKET-0108 through a blocked step's « ce qui manque »; the
+amendment closes that path too. A blocked step names to the narration,
+and teaches through its lead, only the leaves that hold it back for its
+doer (`blocking_verdicts`): never a leaf under a `not`, never one about
+the giver. Rejected: A2 (the fact as player-visible: the secrets
+invariant); A3 (no `knowledge` leaf in a completion: it leaves 0108's path
+open and loses « apprends X »); V1 (the canon's state as a quest tracker:
+the character may not have seen it; reactivation: the event journal of
+TICKET-0114 says who witnessed what -- « tue le loup géant » is tracked
+from then).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/conditions.py b/tooling/verify/checks/conditions.py
index d7fe7bd..e1f990b 100644
--- a/tooling/verify/checks/conditions.py
+++ b/tooling/verify/checks/conditions.py
@@ -78,6 +78,39 @@ CC5 -- the retired tables are gone from the code (static, AST). No module
    nor uses `agenda_step_requirement` or `quest_offer_requirement` as a
    whole string.
 
+CD1 -- the editor (BRIEF-0111-D, static). `questRequirements.js`'s
+   `SUBJECT_ROLES` has exactly the keys of `conditions.SUBJECT_ROLES`, in
+   order; `requirementBody` sends `op: 'leaf'`, `subject_role`,
+   `subject_entity_id` and `value`; `conditionBody` sends the locked tree,
+   else `op: 'all'` of the rows, else null. `ConditionEditor.svelte` renders
+   `<QuestRequirementRow` for a list and `cond.lines` for a locked tree;
+   `QuestOffers.svelte` renders `<ConditionEditor` for the eligibility, the
+   prerequisite and the completion; `questOffers.svelte.js` sends
+   `eligibility`, `prerequisite` and `completion` through `conditionBody`.
+CD2 -- the offer API and what Journée reads (fixture and route functions).
+   `create_offer` takes a nested eligibility and a step's completion;
+   `offer_dict` gives the nested one `flat: null` and its French lines, a
+   flat one its rows; a malformed tree answers 422 with no row written.
+   Accepting copies both conditions of each step to the agenda; the active
+   step's `completion` lines in `journee_payload` carry a mark and a
+   progress, `completion_met` its verdict; `settlement_context` shows them
+   too; no payload carries `agenda_id` or `step_id`.
+CD3 -- Journée (static). `QuestPanel.svelte` shows the active step's
+   `step.completion` lines with their mark and progress;
+   `SettlementRecap.svelte` shows every step's `step.completion`.
+CD4 -- what a player may read (AMENDMENT-0111-01, A1 and V2; fixture). A
+   fact the PC does not know -- held by an NPC as a secret -- is never
+   written out on a player surface: not in `verdict_lines` with the PC as
+   viewer (it reads `HIDDEN_FACT_FR`), not in `blocked_details_fr` (it
+   reads `HIDDEN_KNOWLEDGE_DETAIL_FR`), not in `player_detail_fr`; the
+   creator's `verdict_lines` still writes it; once the PC knows it, the
+   player's line writes it too. A leaf about the giver reads `?` with no
+   progress, a `relation_gte` leaf shows no count, and a head line never
+   reads met over a hidden leaf; `_steps_view`'s `completion_met` is the
+   seen verdict's. `blocking_verdicts` keeps only the unmet leaves on the
+   doer outside a `not`: a negated leaf and a leaf on the giver never reach
+   a blocked step's narration or its lead.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
@@ -816,7 +849,7 @@ def _cc4_consumers(session, ids) -> None:
     armed = _account_rendezvous([applied], session)
     if armed is None or armed["npc_id"] != ids["npc"]:
         fail(f"CC4: the day's NPC is {armed}, expected the relation_gte reached through all")
-    details = blocked_details_fr(evaluated.verdict, session)
+    details = blocked_details_fr(evaluated.verdict, session, ids["pc"])
     if not any(d.startswith("il ne faut pas que") and "Fourrure" in d for d in details):
         fail(f"CC4: the blocked details miss the negated leaf: {details}")
 
@@ -872,6 +905,231 @@ def check_cc5() -> None:
         fail("CC5: walked zero modules")
 
 
+# --- CD1 -----------------------------------------------------------------------
+
+FRONTEND = ROOT / "frontend" / "src"
+
+
+def _front(rel: str) -> str:
+    path = FRONTEND / rel
+    if not path.exists():
+        fail(f"CD: {rel} is missing")
+        return ""
+    return path.read_text(encoding="utf-8")
+
+
+def check_cd1() -> None:
+    import re
+
+    from world_engine.conditions import SUBJECT_ROLES
+
+    req = _front("creation/questRequirements.js")
+    block = re.search(r"export const SUBJECT_ROLES = \{(.*?)\};", req, re.S)
+    keys = tuple(re.findall(r"^\s+(\w+): '", block.group(1), re.M)) if block else ()
+    if keys != SUBJECT_ROLES:
+        fail(f"CD1: SUBJECT_ROLES in questRequirements.js is {keys}")
+    for needle in ("op: 'leaf',", "subject_role: kind === 'role' ? id : null,",
+                   "subject_entity_id: kind === 'entity' ? id : null,", "value: form.values ? (req.value || null) : null,",
+                   "if (cond.locked) return cond.locked;", "return { op: 'all', children: cond.list.map(requirementBody) };"):
+        if needle not in req:
+            fail(f"CD1: questRequirements.js lacks {needle!r}")
+    editor = _front("creation/ConditionEditor.svelte")
+    for needle in ("<QuestRequirementRow", "{#each cond.lines as line", "{#if cond.locked}"):
+        if needle not in editor:
+            fail(f"CD1: ConditionEditor.svelte lacks {needle!r}")
+    offers = _front("creation/QuestOffers.svelte")
+    for needle in ("<ConditionEditor cond={draft.eligibility}", "<ConditionEditor cond={step.prerequisite}",
+                   "<ConditionEditor cond={step.completion}"):
+        if needle not in offers:
+            fail(f"CD1: QuestOffers.svelte lacks {needle!r}")
+    state = _front("creation/questOffers.svelte.js")
+    for needle in ("eligibility: conditionBody(draft.eligibility),",
+                   "prerequisite: conditionBody(s.prerequisite), completion: conditionBody(s.completion),"):
+        if needle not in state:
+            fail(f"CD1: questOffers.svelte.js lacks {needle!r}")
+
+
+# --- CD2 -----------------------------------------------------------------------
+
+def _keys(value) -> set:
+    if isinstance(value, dict):
+        return set(value) | set().union(*(_keys(v) for v in value.values()))
+    if isinstance(value, list):
+        return set().union(*(_keys(v) for v in value)) if value else set()
+    return set()
+
+
+def _cd2_offer(session, ids, routes):
+    from fastapi import HTTPException
+    from sqlmodel import select
+
+    from world_engine.models import QuestOffer, World
+
+    for world in session.exec(select(World).where(World.is_active == True)).all():  # noqa: E712
+        world.is_active = False
+        session.add(world)
+    ours = session.get(World, ids["world"])
+    ours.is_active = True
+    session.add(ours)
+    session.commit()
+    met = {"op": "leaf", "type": "has_met", "subject_role": "doer", "target_entity_id": ids["npc"]}
+    furs = {"op": "leaf", "type": "item_held", "subject_role": "doer", "target_entity_id": ids["fur"], "threshold": 5}
+    body = routes.OfferBody(giver_entity_id=ids["npc"], title="Cinq fourrures",
+                            eligibility={"op": "any", "children": [met, {"op": "not", "children": [furs]}]},
+                            steps=[routes.OfferStepBody(objective="Rapporter", cost=1,
+                                                        completion={"op": "all", "children": [furs]})])
+    view = routes.create_offer(body, db=session)
+    if view["eligibility"]["flat"] is not None or [l["depth"] for l in view["eligibility"]["lines"]] != [0, 1, 1, 2]:
+        fail(f"CD2: a nested eligibility reads {view['eligibility']}")
+    step = view["steps"][0]
+    if step["completion"]["flat"] != [{"type": "item_held", "target_entity_id": ids["fur"], "target_key": None,
+                                        "threshold": 5, "subject_role": "doer", "subject_entity_id": None,
+                                        "value": None}] or step["prerequisite"]["tree"] is not None:
+        fail(f"CD2: a flat completion reads {step['completion']}, the empty prerequisite {step['prerequisite']}")
+    before = _rows(session)
+    bad = routes.OfferBody(giver_entity_id=ids["npc"], title="Mal formée",
+                           eligibility={"op": "not", "children": [met, met]},
+                           steps=[routes.OfferStepBody(objective="o", cost=1)])
+    try:
+        routes.create_offer(bad, db=session)
+        fail("CD2: a malformed tree was saved")
+    except HTTPException as exc:
+        if exc.status_code != 422 or _rows(session) != before:
+            fail(f"CD2: a malformed tree answered {exc.status_code} or wrote rows")
+    return session.get(QuestOffer, view["id"])
+
+
+def check_cd2(engine) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.cockpit.routes import quests as routes
+    from world_engine.conditions import read_condition
+    from world_engine.models import AgendaStep, Character, Quest, World
+    from world_engine.quest_reads import journee_payload
+    from world_engine.quest_settlement_view import settlement_context
+    from world_engine.writes import accept_quest
+
+    with Session(engine) as session:
+        world = session.exec(select(World).where(World.name == "Conditions CC")).one()
+        ids = _cc_ids(session, world.id)
+        offer = _cd2_offer(session, ids, routes)
+        quest = accept_quest(session, offer=offer, character=session.get(Character, ids["pc"]))
+        session.commit()
+        step = session.exec(select(AgendaStep).where(AgendaStep.agenda_id == quest.agenda_id)).one()
+        if read_condition(session, role="completion", agenda_step_id=step.id) is None:
+            fail("CD2: accepting did not copy the step's completion")
+        payload = journee_payload(session.get(Character, ids["pc"]), session)
+        ours = next((q for q in payload["quests"] if q["quest_id"] == quest.id), None)
+        lines = ours["steps"][0]["completion"] if ours else []
+        if [(l["mark"], l["progress"]) for l in lines] != [("✗", None), ("✗", "3/5")] \
+                or ours["steps"][0]["completion_met"] is not False:
+            fail(f"CD2: the active step's completion reads {lines}")
+        context = settlement_context(session, session.get(Quest, quest.id))
+        if context["steps"][0]["completion"] != lines:
+            fail("CD2: « déclarer accomplie » does not show the completion lines")
+        leaked = {"agenda_id", "step_id"} & (_keys(payload) | _keys(context))
+        if leaked:
+            fail(f"CD2: a payload carries {sorted(leaked)}")
+
+
+# --- CD4 -----------------------------------------------------------------------
+
+SECRET_TEXT = "Le trésor dort sous le puits"
+
+
+def _cd4_fact(session, ids, content: str) -> str:
+    from world_engine.models import Knowledge
+    from world_engine.writes.facts import create_fact
+
+    fact = create_fact(session, world_id=ids["world"], content=content, created_by="check", facet="information")
+    session.flush()
+    session.add(Knowledge(entity_id=ids["npc"], fact_id=fact.id, level="knows", is_secret=True))
+    session.commit()
+    return fact.id
+
+
+def _cd4_reading(session, ids, fact_id) -> None:
+    from world_engine.condition_text import HIDDEN_FACT_FR, verdict_lines
+    from world_engine.conditions import Bindings, ConditionTree, evaluate, leaf
+    from world_engine.day_resolve import HIDDEN_KNOWLEDGE_DETAIL_FR, blocked_details_fr, player_detail_fr
+    from world_engine.models import Character, Knowledge
+
+    pc = session.get(Character, ids["pc"])
+    tree = ConditionTree(op="all", children=(
+        leaf(_spec("knowledge", target_key=fact_id)),
+        leaf(_spec("has_met", subject_role="giver", target_entity_id=ids["npc"])),
+        leaf(_spec("relation_gte", target_entity_id=ids["npc"], threshold=1))))
+    verdict = evaluate(tree, Bindings(doer=pc, giver_id=ids["npc"]), session)
+    lines = verdict_lines(session, verdict, ids["pc"])
+    texts = " | ".join(line["text"] for line in lines)
+    hidden = HIDDEN_FACT_FR.format(who="le personnage")
+    if "trésor" in texts or hidden[1:] not in texts:
+        fail(f"CD4: the player's lines write out an unknown fact: {texts}")
+    if "trésor" not in " | ".join(line["text"] for line in verdict_lines(session, verdict)):
+        fail("CD4: the creator's lines no longer write the fact")
+    if [(line["mark"], line["progress"]) for line in lines[2:]] != [("?", None), ("✗", None)]:
+        fail(f"CD4: the giver's leaf or the regard shows through: {lines[2:]}")
+    details = blocked_details_fr(verdict, session, ids["pc"])
+    if any("trésor" in d for d in details) or HIDDEN_KNOWLEDGE_DETAIL_FR not in details:
+        fail(f"CD4: the blocked details write out an unknown fact: {details}")
+    if "trésor" in player_detail_fr(verdict.children[0].verdict, ids["pc"], session):
+        fail("CD4: player_detail_fr writes out an unknown fact")
+    session.add(Knowledge(entity_id=ids["pc"], fact_id=fact_id, level="knows", is_secret=False))
+    session.commit()
+    known = evaluate(tree, Bindings(doer=pc, giver_id=ids["npc"]), session)
+    if "trésor" not in verdict_lines(session, known, ids["pc"])[1]["text"]:
+        fail("CD4: a fact the PC knows is hidden from him")
+    giver_only = ConditionTree(op="all", children=(
+        leaf(_spec("has_met", subject_role="giver", target_entity_id=ids["npc"])),))
+    seen = evaluate(giver_only, Bindings(doer=pc, giver_id=ids["npc"]), session).seen_by(ids["pc"])
+    if seen.state != "unknown":
+        fail(f"CD4: a head line over a hidden leaf reads {seen.state}")
+
+
+def _cd4_blocking(session, ids, fact_id) -> None:
+    from world_engine.conditions import Bindings, ConditionTree, evaluate, leaf
+    from world_engine.models import Character
+
+    other = _cd4_fact(session, ids, "La clé est rouillée")
+    tree = ConditionTree(op="all", children=(
+        ConditionTree(op="not", children=(leaf(_spec("knowledge", target_key=other)),)),
+        leaf(_spec("knowledge", subject_role="giver", target_key=other)),
+        leaf(_spec("knowledge", target_key=other)),
+        leaf(_spec("knowledge", target_key=fact_id))))
+    pc = session.get(Character, ids["pc"])
+    verdict = evaluate(tree, Bindings(doer=pc, giver_id=ids["other"]), session)
+    blocking = [v.required for v in verdict.blocking_verdicts()]
+    if blocking != [other]:
+        fail(f"CD4: blocking_verdicts keeps {blocking}, expected only the doer's unmet leaf outside the not")
+
+
+def check_cd4(engine) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.models import Entity, World
+
+    with Session(engine) as session:
+        world = session.exec(select(World).where(World.name == "Conditions CC")).one()
+        names = {e.name: e.id for e in session.exec(select(Entity).where(Entity.world_id == world.id)).all()}
+        ids = {"world": world.id, "pc": names["PC"], "npc": names["NPC"], "other": names["OTHER"]}
+        fact_id = _cd4_fact(session, ids, SECRET_TEXT)
+        _cd4_reading(session, ids, fact_id)
+        _cd4_blocking(session, ids, fact_id)
+
+
+# --- CD3 -----------------------------------------------------------------------
+
+def check_cd3() -> None:
+    panel = _front("journee/QuestPanel.svelte")
+    for needle in ("{#if step.status === 'active' && step.completion?.length}", "{#each step.completion as line",
+                   "{line.mark} {line.text}{#if line.progress} — {line.progress}{/if}"):
+        if needle not in panel:
+            fail(f"CD3: QuestPanel.svelte lacks {needle!r}")
+    recap = _front("journee/SettlementRecap.svelte")
+    if "{#each step.completion || [] as line" not in recap:
+        fail("CD3: SettlementRecap.svelte does not show the steps' completion")
+
+
 def main() -> int:
     _fresh_db()
     check_ca1()
@@ -887,6 +1145,10 @@ def main() -> int:
     check_cc3()
     check_cc4(engine)
     check_cc5()
+    check_cd1()
+    check_cd2(engine)
+    check_cd3()
+    check_cd4(engine)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -895,7 +1157,10 @@ def main() -> int:
           "condition_forms.py alone; a condition is a tree of four connectors over those forms, "
           "shape-checked, judged in three values on each leaf's subject, and read back in French "
           "without writing anything; v2.20 stores it as rows, one tree per owner and role, converted "
-          "from the two requirement tables it drops; every agenda judges it, binding a quest's giver")
+          "from the two requirement tables it drops; every agenda judges it, binding a quest's giver; "
+          "the offer editor edits a flat one as a list and shows a nested one; Journée and « déclarer "
+          "accomplie » show each step's completion, never acting on it; a player reads neither a fact his "
+          "character does not know nor a leaf about someone else")
     return 0
 
 
````

## Scope OUT

- Completing a step or settling a quest because its completion is met (M2).
- Editing a nested condition anywhere (T1: the interpreter, TICKET-0112, will).
- A completion on the quest itself rather than on its steps; a failure condition (N1).
- Any table, migration or check other than `conditions.py`.
- The interpreter in natural language (TICKET-0112), world state attributes (0113), the event journal, failure conditions and absence conditions (0114, N1), the creator dashboard (0115), rank trials (0116).
- `goal_prerequisite`, the NPC goal's gate (GP1: its own ticket).
- Any change to the day-chain prompts or to the model's four forms (`MODEL_REQUIREMENT_TYPES`).
- A completion that acts on its own (M2); a visual tree editor (T2).
- Any change to `legacy.html` or Play.

## Invariants to defend

**Secrets are structurally excluded** -- no player surface and no narration context writes out a fact the character does not resolve above `unaware`; the filter is in code (`known_to`, `seen_by`), never an instruction (CD4). **Creator control is structural** -- a met completion moves nothing; only « Déclarer accomplie » settles (CD2). **The player never sees an agenda** -- no payload carries `agenda_id` or `step_id` (C-09). **One mount mechanism** -- `ConditionEditor.svelte` is a child of `QuestOffers.svelte`, never registered in `registry.js` (`creation_island.py`). **Play is sealed** -- `legacy.html` is untouched.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- A named mutation does not turn its rule red.
- `creation_island.py` or `page_contract.py` turns red.
- A player surface other than those C-08 names renders a condition: report where.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `npm run build` names a different asset hash than the prototype's: commit what it builds (`frontend_build_fresh.py` judges the manifest, not the name).
- `git stash push` finds nothing to stash (the earlier BRIEF-0111-D was not applied): go on.

REPORT-ONLY:
- Svelte a11y warnings during the build (pre-existing), npm's `EBADENGINE` notice.
- The stash `BRIEF-0111-D before AMENDMENT-0111-01`: name it in the report, keep it.
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run every check with `WORLD_ENGINE_ENV=test`).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and `src/world_engine/cockpit/static/`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/conditions.py` -> `PASS: conditions -- the requirement forms, their evaluators and their BFS live in condition_forms.py alone; a condition is a tree of four connectors over those forms, shape-checked, judged in three values on each leaf's subject, and read back in French without writing anything; v2.20 stores it as rows, one tree per owner and role, converted from the two requirement tables it drops; every agenda judges it, binding a quest's giver; the offer editor edits a flat one as a list and shows a nested one; Journée and « déclarer accomplie » show each step's completion, never acting on it; a player reads neither a fact his character does not know nor a leaf about someone else`
- `quests.py`, `quest_rewards.py`, `debts.py`, `creation_island.py`, `page_contract.py`, `frontend_build_fresh.py`, `module_budget.py`, `function_length.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`conditions.py` exits 1 with the rule named):
  - in `frontend/src/creation/questRequirements.js`, `  contact: 'Le contact',` -> `(removed)` -> `CD1`
  - in `src/world_engine/quest_reads.py`, `"completion_met": seen.met if seen is not None else None` -> `"completion_met": None` -> `CD2`
  - in `frontend/src/journee/QuestPanel.svelte`, `{line.mark} {line.text}{#if line.progress} — {line.progress}{/if}` -> `{line.mark} {line.text}` -> `CD3`
  - in `src/world_engine/condition_text.py`, `    if spec.type == "knowledge" and viewer_id is not None and not known_to(db, viewer_id, spec.target_key):` -> `    if False:` -> `CD4`
  - in `src/world_engine/conditions.py`, `            if self.verdict is None or _seen_subject(self.spec, viewer_id):` -> `            if True:` -> `CD4`
  - in `src/world_engine/day_resolve.py`, `    if verdict.type == "knowledge" and not known_to(db, viewer_id, verdict.required):` -> `    if False:` -> `CD4`
  - in `src/world_engine/conditions.py`, `          and node.spec is not None and node.spec.subject_role == "doer"):` -> `          and node.spec is not None):` -> `CD4`
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 144/144.
- The commit also carries `tooling/questions/QUESTION-TICKET-0111.md` with its `## Response` filled (A1, V2).
- The escalation's own case, live in the corpus's fixture: CD4 shows a secret fact of an NPC never written on the player's lines, and written once the PC knows it.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `A QUEST STEP SAYS WHEN ITS OBJECTIVE IS REACHED (TICKET-0111) -- SHOWN, NEVER ACTED ON; THE EDITOR SPEAKS TREES (BRIEF-0111-d, no schema change)` -- in the diff, with its « What a player may read (AMENDMENT-0111-01, A1, V2) » paragraph. No schema change.
