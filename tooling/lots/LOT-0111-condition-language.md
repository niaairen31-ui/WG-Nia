# LOT — TICKET-0111 "The condition language: a tree of four connectors over the requirement forms, one language for every agenda"

## Objective and cut

A condition becomes a tree (A1, I1): its leaves are the requirement forms,
its inner nodes four connectors -- `all`, `any`, `not`, `at_least` -- so a
creator writes « any of », « none of », « at least 2 of 3 » without a
ticket. Every leaf names its subject (P1): the character who acts, the
offer's giver, its contact, or one fixed character. A verdict has three
states (R1): `met`, `unmet`, `unknown`; a gate passes on `met` only.

The tree is stored as rows (O-a): `condition` (one per owner and role) and
`condition_node` (one per node). They replace `agenda_step_requirement`
and `quest_offer_requirement`; v2.20 converts every row into a leaf of
`all`. No CHECK names a form any more: the vocabulary is the writer's, so a
new form is code, never a table rebuild. Twelve forms (S1): `quest_state`
replaces `quest_completed`; `item_held` and `vital_status` are new.

A quest step gains a completion condition (M1): « objectif atteint quand »,
shown in Journée and in « Déclarer accomplie », never acted on. The offer
editor edits a flat condition as a list and shows a nested one read-only
(T1); the API carries trees.

The lot stops before: the interpreter in natural language (TICKET-0112),
world state attributes (0113), the event journal and failure conditions
(0114, N1), the creator dashboard (0115), rank trials (0116), the NPC goal
gate `goal_prerequisite` (GP1, its own ticket), any change to the day-chain
prompts or the model's four forms, any auto-completion (M2), and
`legacy.html`.

## Briefs in this lot

- **A — the forms get their own module** (no schema change,
  `BRIEF-0111-A-condition-forms.md`): a pure move of the forms, their
  evaluators and their BFS from `day_plan.py` to `condition_forms.py`;
  every importer and the checks that read the moved source retargeted;
  check `conditions.py` created (CA1).
- **B — the language** (no schema change, `BRIEF-0111-B-condition-tree.md`):
  `conditions.py` (the tree, its shape, its dict form, three-valued
  evaluation on each leaf's subject) and `condition_text.py` (the tree and
  its verdict in French); `RequirementSpec` gains its subject and value
  (CB1-CB5).
- **C — storage, v2.20, every agenda** (schema v2.20,
  `BRIEF-0111-C-condition-storage.md`): `condition`, `condition_node`, the
  writer `writes/conditions.py`, the reader, `migrate_v2_20_conditions.py`;
  the twelve forms; day plans, offers and accepted quests store and judge
  trees; the old migrations keep their DDL frozen; the editor mirrors the
  new forms (CC1-CC5).
- **D — completion and the surfaces** (no schema change,
  `BRIEF-0111-D-condition-surfaces.md`): a step's completion, copied at
  acceptance, judged and shown; the offer API in trees; the editor's
  condition lists with a subject per row, nested conditions read-only;
  Journée and the recap show the objective's lines (CD1-CD3).

## Dependency graph

Strictly sequential, A -> B -> C -> D.

- B imports A's `condition_forms` (`_EVALUATORS`, `RequirementSpec`,
  `_day_reachable_ids`); kept in `day_plan.py`, B's import would cycle
  (C imports B back into `day_plan`) -- the reason A exists (R-02).
- C stores B's `ConditionTree`, judges with B's `evaluate`, renders with
  B's `condition_text`.
- D reads C's storage and C-09's view, reuses B's `describe` /
  `verdict_lines`.
- Textual chaining makes the order strict anyway: every brief extends
  `tooling/verify/checks/conditions.py` and appends to
  `tooling/standards/ARCHITECTURE_DECISIONS.md`; C and D rebuild `static/`.
- Two placements are forced by gates, not by taste: the new forms land in
  C, not B, because `quests.py` QC1 binds the editor's mirror to
  `REQUIREMENT_TYPES` in the same commit and a form must be storable
  before it is offered; the API switches to trees in D with the editor,
  because the frontend sends the API's shape (C keeps the flat lists, R-20).

## RECON

Opened on `main` at `2cdc92c` (merge of PR #141, `ticket/0110`), schema
v2.19, `python tooling/glue/next_id.py` -> `0111`. Then prototyped on a copy
(branch `proto/0111`): `main` ran the full corpus green (143/143,
`WORLD_ENGINE_ENV=test`); every brief's commit ran it green (144/144 from A
on); every named mutation of every brief turns `conditions.py` red. Findings
tagged [M] were measured. Line numbers are `main`'s.

### R-01 — the requirement vocabulary: ten forms, four for the model, three shape groups [M]
Opened: `src/world_engine/day_plan.py:87-104` (`REQUIREMENT_TYPES`, ten
forms; `MODEL_REQUIREMENT_TYPES` `:96`, the model's four;
`ENTITY_TARGET_TYPES` `:100`, `KEY_TARGET_TYPES` `:103`, `THRESHOLD_TYPES`
`:104`), `:375-386` (`_EVALUATORS`, one evaluator per form, uniform
signature `(req, character, db, reachable_ids) -> Verdict`), `:585-602`
(`_validate_requirement`: the model's parser refuses any form outside its
four).
Finding: a form is a name, a target kind (entity or key), an optional
threshold, an evaluator judging ONE character, and a French detail
(`day_resolve._BLOCKED_DETAIL_FR`, R-12). Every evaluator takes the judged
character as a parameter: none reads « the player » by itself.
Consequence: a leaf can judge any character (P1) without touching an
evaluator; the model keeps its four forms (I1: its plans become `all` of
them).

### R-02 — the forms live in `day_plan.py`, which `writes/` imports [M]
Opened: `src/world_engine/day_plan.py:119-148` (`RequirementSpec`,
`PlanStep`, `Verdict`), `:168-441` (the evaluators, `_EVALUATORS`,
`_day_reachable_ids`, `evaluate_specs`); `src/world_engine/writes/goals_agendas.py:46-53`
(`from ..day_plan import ENTITY_TARGET_TYPES, …, PlanStep, RequirementSpec`);
`src/world_engine/condition_forms.py` does not exist.
Finding: `writes/goals_agendas.py` imports FROM `day_plan.py` (the docstring
at `day_plan.py:196-202` names the cycle importing back would create).
Consequence: the tree module must sit below `day_plan.py`; the forms move
first (A) so `conditions.py` imports them and `day_plan.py` imports
`conditions.py`.

### R-03 — who imports the moved names, and which checks read the moved source [M]
Opened (enumeration, pasted in the gate output (c)): every
`from …day_plan import` of a moved name under `src/` and
`tooling/verify/checks/`; the checks that parse `day_plan.py`'s source:
`tooling/verify/checks/day_plan.py:173` (`DAY_PLAN_FILE`), R1
`check_evaluator_bijection` `:295`, R10 `check_no_traversal_reuse` `:533`,
R25 `check_verdict_type_field` `:972`; `tooling/verify/checks/known_reachability.py:327`
(`DOCUMENTED_MODULES` lists `world_engine/day_plan.py` as a `connects_to`
reader; `:349-361` fails on an undocumented module spelling the literal).
Finding: three rules of `day_plan.py` and one of `known_reachability.py`
read the moved source by file; five checks import moved names.
Consequence: A retargets them, unchanged in meaning; the census document
`tooling/tickets/connects-to-readers-TICKET-0082.md:63` (row 12) gets a
note, its row untouched.

### R-04 — two tables carry the requirements, with CHECKs that name every form [M]
Opened: `src/world_engine/models/config.py:106-159` (`AgendaStepRequirement`:
`step_id`, `type`, `target_entity_id`, `target_key`, `threshold`;
`ck_agenda_step_requirement_type` `:135-138`, `_shape` `:139-146`, unique
index `:147-150`); `src/world_engine/models/quests.py:88-118`
(`QuestOfferRequirement`: `offer_id`, `step_id` NULL for eligibility, the
same two CHECK texts byte for byte).
Finding: a list, implicitly `all`; a new form widened both CHECKs, a table
rebuild each time (v2.17, v2.19). No row carries a subject or a value.
Consequence: O-a replaces both with `condition` / `condition_node`; no CHECK
names a form (C-06).

### R-05 — what reads and writes the two tables [M]
Opened (enumeration, gate output (c)): writers --
`writes/goals_agendas.py:736` (`write_day_plan`), `writes/quests.py:144`
(`DELETE FROM quest_offer_requirement`), `:157`, `:164` (offer),
`:222` (`accept_quest`); readers -- `day_plan.py:449-471`
(`evaluate_agenda_step`), `writes/quests.py:169-176` (`offer_requirements`),
`quest_reads.py:73,76` (`offer_dict`), `cockpit/routes/day.py:300-307`,
`day_mutations.py:155-160`; the cascade `writes/worlds.py:70,77`.
Consequence: C rewires exactly these; nothing else touches the tables.

### R-06 — a requirement row means more than a gate in two places [M]
Opened: `src/world_engine/cockpit/routes/day.py:274-311`
(`_account_rendezvous`: the first `relation_gte` row of the active step
names the day's NPC, `:300-307`); `src/world_engine/day_mutations.py:147-176`
(`_emit_knowledge_change`: a COMPLETED step deepens every `knowledge` row
it carried, `:155-160`).
Finding: both read « the step's rows of type X ».
Consequence: Q1 -- both read the leaves reached through `all` only
(`and_path_leaves`, C-03); a `knowledge` leaf deepens only when judged on
`doer` (a fact someone else must know is not the player's to deepen).

### R-07 — evaluation judges one character and returns a flat list [M]
Opened: `src/world_engine/day_plan.py:150-158` (`EvaluatedStep(step,
verdicts)`, `met` = all), `:419-440` (`evaluate_specs`: one reachable set
per call, only when a `location_reachable` is present), `:443-471`;
`src/world_engine/cockpit/routes/day.py:552-576` (`_finalize_plan`:
anchoring, then `EvaluatedStep(step=step, verdicts=tuple(evaluate_requirements(step,
character, db)))` `:558`, the blocked text `:575`); `src/world_engine/day_resolve.py:220,315`
(`canon_ids` from `evaluated.step.requirements`), `:248,324`
(`requirement_verdicts=evaluated.verdicts`).
Finding: consumers read `EvaluatedStep.met`, `.verdicts` (a tuple of
`Verdict`) and `.step.requirements`.
Consequence: C-07 keeps `met` and `verdicts` (the judged leaves, as a
property) so the narration and the budget cut read the same names; the
requirements list becomes `prerequisite`, a tree.

### R-08 — the day plan's anchoring and code resolution walk the requirements [M]
Opened: `src/world_engine/day_plan.py:536-565` (`anchor_requirements`:
drops unanchored `knowledge` requirements, never steps, reports each),
`:604-623` (`_validate_step`: `requires` list -> `requirements`),
`:656-668` (`_resolve_knowledge_codes`); `tooling/verify/checks/knowledge_identity.py:649-655`
(K6b reads `steps[0].requirements`).
Consequence: C maps and drops leaves on the tree (`map_leaves`,
`drop_leaves`, C-03); K6b reads the tree's leaves.

### R-09 — the cleaner of a requirement lives in `writes/goals_agendas.py` [M]
Opened: `src/world_engine/writes/goals_agendas.py:604-612`
(`_TARGET_ENTITY_TYPE`), `:614-630` (`_clean_target_key`), `:633-678`
(`_clean_requirement`: form known, target in the world and of the right
type, threshold positive, `skill_rank_gte` at most 5; returns row kwargs),
`:681-691` (`_clean_plan_steps`), `:694-738` (`write_day_plan`); its
callers `writes/quests.py:68,134,210`.
Consequence: C moves it to `writes/conditions.py` as `clean_leaf` (returns
a `RequirementSpec`), widened to subjects, values and no-target forms
(C-06).

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

### R-13 — the data the new forms read already exists [M]
Opened: `src/world_engine/models/canon.py:549-558` (`Item`: an entity
extension; `condition` `'intact'`), `:570-586` (`ItemHolding`: one row per
item and holder, `quantity >= 0`, absence reads 0); `:143-170`
(`Character.vital_status`, default `'alive'`, no CHECK);
`src/world_engine/cockpit/crud/entities.py:139-140` (the creator form's
`vital_status` options `alive, dead, missing, unknown`);
`src/world_engine/quest_reads.py:41-48` (`QUEST_STATE_LABELS`: a quest's
state is its agenda's, `active`/`paused` both « en cours »).
Consequence: S1 -- `item_held` (an item entity, a quantity),
`vital_status` (no target, a value among the four) and `quest_state` (an
offer, a value among `open`, `completed`, `failed`, `abandoned`) need no
new data; `quest_completed` becomes `quest_state` `completed`.

### R-14 — UI-visible data is relational by law [M]
Opened: `CLAUDE.md:347-348` (« UI-visible data never lives in JSON »);
`tooling/verify/checks/json_ui_boundary.py:43-80` (`JSON_COLUMN_ALLOWLIST`:
every JSON column named and justified; no durable canon content among
them).
Consequence: O-a -- the tree is rows; no JSON column is added.

### R-15 — the canon-write gate is function-scoped and table-listed [M]
Opened: `tooling/verify/canon_write_policy.txt:1-10` (`[CANON_TABLES]`,
both requirement tables listed), `:53-58` (`write_day_plan`,
`write_quest_offer`, `accept_quest` allowed to write them);
`tooling/verify/checks/single_canon_write.py:49-90` (section 2: the named
full-replace deletes, `write_quest_offer` among them).
Consequence: C lists `condition`, `condition_node` and the three functions
of `writes/conditions.py` that write them; the three callers lose their
requirement-table entries.

### R-16 — the world cascade lists the tables by name [M]
Opened: `src/world_engine/writes/worlds.py:65-81`
(`_DIRECT_WORLD_SCOPED_DELETES`, both requirement tables, order free under
FK deferral); `tooling/verify/checks/world_cascade.py:120-121,195-197` (a
fixture row per table; W3 fails on a cascaded table without one and on a
fixture row for a table not cascaded).
Consequence: C swaps the two names for `condition`, `condition_node`, and
the fixtures likewise.

### R-17 — three old migrations build the requirement tables from the models [M]
Opened: `scripts/migrate_v1_94_agenda_step_plan.py:103,108`
(`_ensure_table(models.AgendaStepRequirement)`); `scripts/migrate_v2_17_quests.py:63,110`
(`_NEW_MODELS` holds `models.QuestOfferRequirement`, the rebuild uses
`models.AgendaStepRequirement` -- read at import time);
`scripts/migrate_v2_19_debts.py:73-76` (`_REQUIREMENT_MODELS`, at import
time); `tooling/verify/checks/quests.py:202-240` (QA2 runs v2.17 on a
v2.16 database), `tooling/verify/checks/debts.py:320-366` (DA2 runs v2.19).
Finding: removing the models breaks those scripts at import.
Consequence: each keeps its table's DDL frozen as it created it (the
0109 lesson: a historical script must not read a model that changed);
QA2 and DA2 compare to the frozen shape.

### R-18 — the checks pinned to the old tables or vocabulary [M]
Opened: `tooling/verify/checks/day_plan.py:192-200`
(`EXPECTED_REQUIREMENT_TYPES`), R2 `:334-348`, R3 `:351-378` (the two
CHECK texts), R6 `:451` (`AgendaStepRequirement` among the positional
wall's names), R16 `:756-761`; `tooling/verify/checks/quests.py:105,108`
(`CREATOR_FORMS`, `QUEST_TABLES`), QA1 `:150-188`, QA3 `:389-441`, QB
`:489-640` (fixtures built on `requirements=`, lists, `QuestOfferRequirement`);
`tooling/verify/checks/debts.py:258` (the version pinned `v2.19`), `:265`
(the debt forms last), `:356`, `:494-525`; `tooling/verify/checks/knowledge_identity.py:214-230`
(a v2.08 database built from the current metadata);
`tooling/verify/checks/quest_rewards.py:501,727` (`eligibility=[]`).
Consequence: C rewrites each to the same meaning on the new storage; no
rule is dropped without its replacement.

### R-19 — a third condition language: `goal_prerequisite` [M]
Opened: `src/world_engine/models/canon.py:419-445` (`GoalPrerequisite`:
an NPC goal's completion gate, `type IN ('relation_gte')`, its own CHECK);
`src/world_engine/writes/goals_agendas.py:81-130`
(`write_npc_goal_prerequisites`).
Consequence: GP1 -- left out of this lot; `day_plan.py` R2 judges only
the `ck_condition*` CHECKs.

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

### R-21 — the CLAUDE.md file tree has no room for a new line [M]
Opened: `CLAUDE.md:461` (`day_plan.py # … requirement evaluators, its own
BFS`); `tooling/verify/checks/claude_md_contract.py` (File structure at
most 80 lines -- it is at 80; 100 characters per line; 38 000 characters).
Consequence: A and B fold the new modules into `day_plan.py`'s line
(`day_plan.py, condition*.py`), within 100 characters.

### R-22 — the subject census counts `subject=` keywords [M]
Opened: `tooling/verify/checks/knowledge_identity.py:31-35,109-116,833-838`
(K3: `.subject`, `"subject"`, `subject=` and a `subject` parameter, counted
per file, equal to `_SUBJECT_CENSUS`).
Consequence: the French phrases fill `{who}`, never `subject=`; the leaf's
fields are `subject_role` and `subject_entity_id` (no census change).

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

## Contract sheet

### C-01 — the leaf, `condition_forms.RequirementSpec`
Produced by: BRIEF-0111-A (moved), BRIEF-0111-B (widened)   Consumed by: B, C, D
Signature: frozen dataclass
`RequirementSpec(type: str, target_entity_id: Optional[str] = None,
target_key: Optional[str] = None, threshold: Optional[int] = None,
subject_role: Optional[str] = "doer", subject_entity_id: Optional[str] = None,
value: Optional[str] = None)`.
Return shape: n/a. Exactly one of `subject_role` / `subject_entity_id` is
set once cleaned; `subject_role` in `("doer", "giver", "contact")`.
Error and empty cases: none at construction; `writes.conditions.clean_leaf`
refuses (C-06).

### C-02 — the form family (`condition_forms`)
Produced by: BRIEF-0111-A (ten forms, moved), BRIEF-0111-C (twelve)   Consumed by: B, C, D
Family contract, written before its members: a form is
1. its name in `REQUIREMENT_TYPES` (order: the model's four, the creator's
   four, the debt two, then `item_held`, `vital_status`);
2. exactly one target group: `ENTITY_TARGET_TYPES` (`target_entity_id`, of
   the type `_TARGET_ENTITY_TYPE` names, `None` = any), `KEY_TARGET_TYPES`
   (`target_key`, resolved by `_clean_target_key`) or `NO_TARGET_TYPES`
   (neither, refused if given);
3. `THRESHOLD_TYPES` membership (a positive integer; `skill_rank_gte` at
   most 5);
4. `FORM_VALUES[form]` when it compares to a value (the value must be one
   of them);
5. an evaluator in `_EVALUATORS`, `(req, character, db, reachable_ids) ->
   Verdict` (`type` first), judging the character it is given;
6. a player-facing detail in `day_resolve._BLOCKED_DETAIL_FR`;
7. a creator-facing phrase in `condition_text.FORM_PHRASES_FR`, and a
   label per value in `condition_text.VALUE_LABELS_FR`;
8. a line in `frontend/src/creation/questRequirements.js`'s
   `REQUIREMENT_FORMS` (`column` `entity`/`key`/`none`, `threshold`,
   `values: true` when 4 applies).
The twelve members (C): `knowledge` (key: a fact), `relation_gte`
(entity, threshold), `resource` (key: a label, threshold), `location_reachable`
(entity), `has_met` (entity), `faction_member` (entity: a faction),
`skill_rank_gte` (key: a skill, threshold 1-5), `quest_state` (key: an
offer, value among `QUEST_STATES = ("open", "completed", "failed",
"abandoned")`), `has_debt_to`, `no_debt_to` (entity: a character or a
faction), `item_held` (entity: an item, threshold), `vital_status` (no
target, value among `VITAL_STATUSES = ("alive", "dead", "missing",
"unknown")`). `MODEL_REQUIREMENT_TYPES` stays the model's four.

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

### C-06 — storage: `condition`, `condition_node`, `writes/conditions.py`, `read_condition`
Produced by: BRIEF-0111-C   Consumed by: C, D
Tables (exact columns and CHECKs in BRIEF-0111-C's diff, checked by CC1):
`condition(id, world_id, role, quest_offer_id, quest_offer_step_id,
agenda_step_id, created_at)` -- role in `CONDITION_ROLES =
("eligibility", "prerequisite", "completion")`; exactly one owner; an
offer owns its `eligibility`, a step a `prerequisite` or `completion`; one
per owner and role (three unique indexes). `condition_node(id, world_id,
condition_id, parent_id, position, op, n, form, subject_role,
subject_entity_id, target_entity_id, target_key, threshold, value)` -- op
in `CONDITION_OPS`; a leaf has a form, a connector nothing of a leaf's;
a leaf exactly one subject; `n` iff `at_least`, `n >= 1`. No CHECK names a
form.
Signatures: `clean_leaf(db, world_id, req, where="") -> RequirementSpec`;
`clean_condition(db, world_id, tree, where="") -> Optional[ConditionTree]`;
`write_condition(db, *, world_id, role, tree, **owner) ->
Optional[Condition]` (owner: exactly one of `quest_offer_id=`,
`quest_offer_step_id=`, `agenda_step_id=`; replaces that owner's role
whole; None removes it); `delete_offer_conditions(db, offer_id)`;
`conditions.read_condition(db, *, role, **owner) ->
Optional[ConditionTree]` (children by `position`).
Error and empty cases: every refusal is a `ValueError` before any row --
an unknown form, a subject that is neither a role nor a character of the
world, a target missing, outside the world or of the wrong type, a target
on a no-target form, a threshold out of range, a missing or unknown value,
an ill-shaped tree, a role its owner cannot hold, zero or two owners.
None of these functions commits.

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

### C-10 — migration v2.20
Produced by: BRIEF-0111-C   Consumed by: Nia (live gate)
Behaviour: refuses below v2.19 before any change; creates the two tables
when missing; converts every row of both old tables into one `condition`
per owner and role -- `all` of its leaves in `rowid` order, `subject_role
= 'doer'`, `quest_completed` -> `quest_state` / `completed` -- then drops
both tables, in one raw transaction; post-checks (no old table, leaves =
rows form by form, one root per condition, `foreign_key_check` empty on the
two tables it writes; an orphan elsewhere noted, never blocking); converges
`schema_meta`; a second run does nothing. Prints `Migration v2.20 applied.`

## Gate output

(a) Property trace -- one line per property the lot asserts about code
that exists today: property -> finding -> declaring file opened.

- the ten forms, the model's four, the three shape groups -> R-01 -> `src/world_engine/day_plan.py:87-104`
- one evaluator per form, its signature, judging the character given -> R-01 -> `src/world_engine/day_plan.py:168-386`
- the model's parser refuses other forms -> R-01 -> `src/world_engine/day_plan.py:585-602`
- `writes/goals_agendas.py` imports from `day_plan.py` -> R-02 -> `src/world_engine/writes/goals_agendas.py:46-53`
- the checks reading `day_plan.py`'s source by file -> R-03 -> `tooling/verify/checks/day_plan.py:173,295,533,972`; `tooling/verify/checks/known_reachability.py:327`
- both requirement tables, their columns, CHECKs, index -> R-04 -> `src/world_engine/models/config.py:106-159`; `src/world_engine/models/quests.py:88-118`
- the writers and readers of the two tables -> R-05 -> enumeration (c) 2
- the day's NPC from the first `relation_gte` row -> R-06 -> `src/world_engine/cockpit/routes/day.py:300-307`
- a completed step deepens its `knowledge` rows -> R-06 -> `src/world_engine/day_mutations.py:147-176`
- `EvaluatedStep` and its consumers -> R-07 -> `src/world_engine/day_plan.py:150-158`; `src/world_engine/cockpit/routes/day.py:552-576`; `src/world_engine/day_resolve.py:208-251,286-326`
- the anchoring and code resolution -> R-08 -> `src/world_engine/day_plan.py:536-565,604-668`
- `_clean_requirement`'s rules -> R-09 -> `src/world_engine/writes/goals_agendas.py:604-678`
- the offer writer's validation, full replace, acceptance, eligibility -> R-10 -> `src/world_engine/writes/quests.py:57-227`
- the offer API's bodies and its 422 -> R-11 -> `src/world_engine/cockpit/routes/quests.py:50-137`
- the editor's form lines and QC1's pattern -> R-11 -> `frontend/src/creation/questRequirements.js:11-58`; `tooling/verify/checks/quests.py:790-808`
- the blocked details, one per form, fail-closed -> R-12 -> `src/world_engine/day_resolve.py:256-283`; `tooling/verify/checks/day_narration.py:652-676`
- `item_holding`, `Item`, `vital_status` and its options, the quest state labels -> R-13 -> `src/world_engine/models/canon.py:143-170,549-586`; `src/world_engine/cockpit/crud/entities.py:139-140`; `src/world_engine/quest_reads.py:41-48`
- UI-visible data is relational -> R-14 -> `CLAUDE.md:347-348`; `tooling/verify/checks/json_ui_boundary.py:43-80`
- the canon-write policy's tables and sites -> R-15 -> `tooling/verify/canon_write_policy.txt:1-10,53-58`
- the cascade's table list and its fixtures -> R-16 -> `src/world_engine/writes/worlds.py:65-81`; `tooling/verify/checks/world_cascade.py:120-121,195-197`
- the old migrations read the models at import -> R-17 -> `scripts/migrate_v1_94_agenda_step_plan.py:103-108`; `scripts/migrate_v2_17_quests.py:63,110`; `scripts/migrate_v2_19_debts.py:73-76`
- the checks pinned to the old storage -> R-18 -> the files and lines of R-18
- `goal_prerequisite`'s own CHECK -> R-19 -> `src/world_engine/models/canon.py:419-445`
- a `knowledge` verdict's label is the fact's text; its detail writes it -> R-23 -> `src/world_engine/day_plan.py:173-192`; `src/world_engine/day_resolve.py:256-283`
- the player surfaces and the narration that write details -> R-23 -> `src/world_engine/quest_reads.py:143-155`; `src/world_engine/cockpit/day_reconcile_apply.py:74`; `src/world_engine/day_resolve.py:426`
- a blocked step's lead per unmet `knowledge` verdict -> R-23 -> `src/world_engine/day_mutations.py:225-272`
- B3 anchors the model's gates only -> R-23 -> `src/world_engine/day_plan.py:536-565`
- a fact's resolved level -> R-23 -> `src/world_engine/knowledge_resolve.py:248-250`
- the editor sends the API's shape; `_steps_view` feeds Journée and the recap -> R-20 -> `frontend/src/creation/questOffers.svelte.js:118-151`; `src/world_engine/quest_reads.py:143-155`; `src/world_engine/quest_settlement_view.py:89-106`
- the File structure at 80 lines -> R-21 -> `tooling/verify/checks/claude_md_contract.py`
- the subject census -> R-22 -> `tooling/verify/checks/knowledge_identity.py:31-35,833-838`

(b) Case tables.

b-1 -- three-valued connectors (C-04). `need`: all = every child, any = 1,
at_least = n. met >= need -> met; met + unknown < need -> unmet; else
unknown. `not` swaps met and unmet, keeps unknown.

| children (2)        | all     | any     | at_least 1 | at_least 2 |
|---------------------|---------|---------|------------|------------|
| met, met            | met     | met     | met        | met        |
| met, unmet          | unmet   | met     | met        | unmet      |
| met, unknown        | unknown | met     | met        | unknown    |
| unmet, met          | unmet   | met     | met        | unmet      |
| unmet, unmet        | unmet   | unmet   | unmet      | unmet      |
| unmet, unknown      | unmet   | unknown | unknown    | unmet      |
| unknown, met        | unknown | met     | met        | unknown    |
| unknown, unmet      | unmet   | unknown | unknown    | unmet      |
| unknown, unknown    | unknown | unknown | unknown    | unknown    |

`not`: met -> unmet, unmet -> met, unknown -> unknown. `at_least 2` of 3
children: all 27 triples by the same rule (CB2 walks them).

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

b-3 -- the twelve forms' arguments (C-02, `clean_leaf`).

| form               | target                       | threshold | value          |
|--------------------|------------------------------|-----------|----------------|
| knowledge          | key: a fact of the world     | --        | --             |
| relation_gte       | entity: any of the world     | >= 1      | --             |
| resource           | key: a label                 | >= 1      | --             |
| location_reachable | entity: any of the world     | --        | --             |
| has_met            | entity: any of the world     | --        | --             |
| faction_member     | entity: a faction            | --        | --             |
| skill_rank_gte     | key: a domain or a skill     | 1 to 5    | --             |
| quest_state        | key: an offer of the world   | --        | QUEST_STATES   |
| has_debt_to        | entity: character or faction | --        | --             |
| no_debt_to         | entity: character or faction | --        | --             |
| item_held          | entity: an item              | >= 1      | --             |
| vital_status       | none (refused if given)      | --        | VITAL_STATUSES |

A threshold or a value on a form that takes none is dropped (the old
cleaner's rule for the threshold); a target on `vital_status` is refused.

b-4 -- Q1, the leaves a step cannot be met without (C-03, R-06).

| tree                                    | `and_path_leaves`      |
|-----------------------------------------|------------------------|
| None                                    | ()                     |
| leaf a                                  | (a,)                   |
| all(a, b)                               | (a, b)                 |
| all(a, any(b, c), all(d), not(e))       | (a, d)                 |
| any(a, b)                               | ()                     |
| at_least 1 (a)                          | ()                     |

The day's NPC: the target of the first `relation_gte` among them; the
deepened facts: their `knowledge` leaves judged on `doer`.

b-5 -- migration v2.20, one row to one leaf (C-10).

| old row                                            | owner column          | role         | leaf                                  |
|----------------------------------------------------|-----------------------|--------------|---------------------------------------|
| `quest_offer_requirement`, `step_id` NULL           | `quest_offer_id`      | eligibility  | same form and arguments, `doer`        |
| `quest_offer_requirement`, `step_id` set            | `quest_offer_step_id` | prerequisite | same, `doer`                           |
| `agenda_step_requirement`                           | `agenda_step_id`      | prerequisite | same, `doer`                           |
| any of them with `type = 'quest_completed'`         | as above              | as above     | `quest_state`, value `completed`       |

One `all` root per owner and role; leaves in the rows' `rowid` order.

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

(c) Enumerations, pasted (run on `main` at `2cdc92c`).

1. The importers of the names A moves (`grep -rn -A12 "from \(\.\|\.\.\|\.\.\.\|world_engine\.\)day_plan import" src tooling scripts`, condensed to the moved names):
```
src/world_engine/day_resolve.py:69-76       Verdict as RequirementVerdict
src/world_engine/writes/quests.py:30        RequirementSpec, evaluate_specs (+ MAX_PLAN_STEPS, PlanStep: stay)
src/world_engine/writes/goals_agendas.py:46 ENTITY_TARGET_TYPES, KEY_TARGET_TYPES, REQUIREMENT_TYPES, THRESHOLD_TYPES, RequirementSpec (+ PlanStep: stays)
src/world_engine/cockpit/routes/quests.py:34 RequirementSpec (+ PlanStep: stays)
tooling/verify/checks/quests.py:151,329,411,490,514,539,791   day_plan.REQUIREMENT_TYPES/MODEL_…/ENTITY_…/KEY_…/THRESHOLD_…, RequirementSpec, evaluate_specs
tooling/verify/checks/debts.py:263,481,491,687                 day_plan.REQUIREMENT_TYPES/…/_EVALUATORS, RequirementSpec, evaluate_specs
tooling/verify/checks/knowledge_identity.py:662               RequirementSpec, _eval_knowledge
tooling/verify/checks/day_narration.py:676                    REQUIREMENT_TYPES
(src/world_engine/quest_reads.py, cockpit/routes/day.py, day_feasibility.py, cockpit/day_reconcile_apply.py: day_plan names that stay)
```
2. The readers and writers of the two tables (`grep -rn "AgendaStepRequirement\|QuestOfferRequirement\|agenda_step_requirement\|quest_offer_requirement" --include=*.py src`, comments dropped):
```
src/world_engine/day_plan.py:55,456              AgendaStepRequirement (import; evaluate_agenda_step)
src/world_engine/writes/goals_agendas.py:58,736  AgendaStepRequirement (import; write_day_plan)
src/world_engine/writes/quests.py:36,43,144,157,164,171-174,222   both (write_quest_offer, offer_requirements, accept_quest)
src/world_engine/cockpit/routes/day.py:67,301-304  AgendaStepRequirement (the day's NPC)
src/world_engine/day_mutations.py:87,156-158      AgendaStepRequirement (knowledge deepening)
src/world_engine/writes/worlds.py:70,77           both (the cascade)
src/world_engine/models/__init__.py, models/config.py, models/quests.py   the declarations
```
3. The scripts reading the two models (`grep -rln "AgendaStepRequirement\|QuestOfferRequirement" scripts`):
```
scripts/migrate_v1_94_agenda_step_plan.py
scripts/migrate_v2_17_quests.py
scripts/migrate_v2_19_debts.py
```
4. The checks naming the old storage (`grep -ln "agenda_step_requirement\|AgendaStepRequirement\|quest_offer_requirement\|QuestOfferRequirement\|REQUIREMENT_TYPES\|_EVALUATORS\|RequirementSpec\|evaluate_specs\|evaluate_requirements" tooling/verify/checks/*.py`):
```
day_feasibility.py  day_narration.py  day_plan.py  debts.py  knowledge_identity.py  quests.py  world_cascade.py
(and, found by running the corpus: quest_rewards.py builds offers with eligibility=[];
 known_reachability.py lists day_plan.py as a connects_to module)
```
`day_feasibility.py` only forbids those names in the veto (R5): untouched.

(d) Family contract C-02 written before its members, re-read after the
last (`vital_status`): every member has its eight parts -- the editor
line's `column: 'none'` and `values: true` were added to the family
(points 2, 4, 8) when the re-read found `vital_status` fitting neither
`entity` nor `key`. ✓

(e) Gates, proposed and passed, each with the module that satisfies it.

- `conditions.py` CA1 (proposed) -> `src/world_engine/condition_forms.py` (BRIEF-0111-A); the check forbids the moved names anywhere else -- `Verdict` excepted, a common name (`resolution.py`, `skill_lexicon.py`).
- `conditions.py` CB1-CB5 (proposed) -> `src/world_engine/conditions.py`, `src/world_engine/condition_text.py` (BRIEF-0111-B); CB5 forbids `add`/`commit`/`delete`/`execute`/`flush` calls there -- the writer is therefore its own module, `writes/conditions.py` (C).
- `conditions.py` CC1-CC5 (proposed) -> `src/world_engine/models/config.py`, `src/world_engine/writes/conditions.py`, `scripts/migrate_v2_20_conditions.py`, the rewired readers (BRIEF-0111-C).
- `conditions.py` CD4 (proposed, AMENDMENT-0111-01) -> `src/world_engine/conditions.py` (`seen_by`, `blocking_verdicts`), `src/world_engine/condition_text.py` (`known_to`, `HIDDEN_FACT_FR`), `src/world_engine/day_resolve.py` (`player_detail_fr`), `src/world_engine/quest_reads.py` (BRIEF-0111-D); `known_to` is a read through `knowledge_resolve`, which CB5 allows (no write call).
- `conditions.py` CD1-CD3 (proposed) -> `src/world_engine/quest_reads.py`, `src/world_engine/cockpit/routes/quests.py`, `frontend/src/creation/ConditionEditor.svelte` and the editor files, `frontend/src/journee/QuestPanel.svelte`, `SettlementRecap.svelte` (BRIEF-0111-D).
- `day_plan.py` R1, R10, R25 (passed, retargeted) -> `condition_forms.py` (A); R2, R3, R6, R16 (passed, rewritten) -> `condition_forms.py`'s groups and the `ck_condition*` CHECKs of `models/config.py` (C).
- `quests.py`, `debts.py`, `quest_rewards.py`, `knowledge_identity.py`, `world_cascade.py` (passed, adapted in C) -> the same modules as before, on the new storage; QA2 and DA2 -> the frozen DDL of the old migrations.
- `known_reachability.py` (passed) -> `condition_forms.py` documented as row 12's home (A).
- `single_canon_write.py` (passed) -> `writes/conditions.py`'s three writers in `canon_write_policy.txt` (C).
- `json_ui_boundary.py` (passed) -> no JSON column is added (C).
- `schema_version_agreement.py`, `schema_partition.py` (passed) -> `schema_version.py` v2.20, `world-engine-schema.md`, its changelog (C).
- `claude_md_contract.py` (passed) -> one line of File structure, unchanged count (A, B).
- `decisions_index.py` (passed) -> one record per brief, headers `(BRIEF-0111-x, …)`.
- `frontend_build_fresh.py`, `creation_island.py`, `page_contract.py` (passed) -> `static/` rebuilt (C, D); `ConditionEditor.svelte` is a child component, never an island.
- `module_budget.py`, `function_length.py`, `import_cycle.py`, `undefined_names.py` (passed) -> every new module under 1000 lines and 40 functions, every function under 80 lines, no cycle (`conditions.py` imports `condition_forms.py`, never `day_plan.py`).

## Amendments

- **AMENDMENT-0111-01** (2026-10-08, BRIEF-0111-D in flight): a player
  surface wrote out the fact of an unmet `knowledge` leaf (R-23). Nia: A1,
  V2. R-23 added; C-04, C-05, C-07, C-08, C-09 amended; table b-6 added;
  CD4 added to `conditions.py`. BRIEF-0111-D regenerated; A, B, C untouched.
