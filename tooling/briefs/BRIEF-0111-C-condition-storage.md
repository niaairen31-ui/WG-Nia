<!-- slug: condition-storage -->
# BRIEF 0111-C — "A condition is stored as rows, one tree per owner (v2.20); twelve forms; one language for every agenda"

Lot: LOT-0111-condition-language.md (authoritative on conflict)
Depends on: BRIEF-0111-B

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0111-B's commit).

- `src/world_engine/models/config.py:131` -> `class AgendaStepRequirement(SQLModel, table=True):`
- `src/world_engine/models/config.py:137` -> `name="ck_agenda_step_requirement_type",`
- `src/world_engine/models/quests.py:92` -> `class QuestOfferRequirement(SQLModel, table=True):`
- `src/world_engine/writes/goals_agendas.py:633` -> `def _clean_requirement(db: Session, world_id: str, step_index: int, req: RequirementSpec) -> dict:`
- `src/world_engine/writes/goals_agendas.py:694` -> `def write_day_plan(`
- `src/world_engine/writes/quests.py:200` -> `def accept_quest(db: Session, *, offer: QuestOffer, character: Character) -> Quest:`
- `src/world_engine/cockpit/routes/day.py:303` -> `AgendaStepRequirement.type == "relation_gte",`
- `src/world_engine/day_mutations.py:158` -> `AgendaStepRequirement.type == "knowledge",`
- `src/world_engine/writes/worlds.py:70` -> `"agenda", "agenda_step_requirement", "conversation_window_config",`
- `tooling/verify/canon_write_policy.txt:7` -> `npc_schedule agenda_step_requirement fact fact_participant fact_default`
- `src/world_engine/schema_version.py:15` -> `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.19"`
- `src/world_engine/conditions.py:252` -> `def evaluate(node: Optional[ConditionTree], bindings: Bindings, db: Session) -> Optional[VerdictNode]:`
- `scripts/migrate_v2_19_debts.py:73` -> `_REQUIREMENT_MODELS = {`
- No `scripts/migrate_v2_20_conditions.py` exists.
- No `src/world_engine/writes/conditions.py` exists.

## Facts carried

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

## Contracts

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

### C-08 — what a condition still lacks, `day_resolve.blocked_details_fr`
Produced by: BRIEF-0111-C   Consumed by: C, D
Signature: `blocked_details_fr(verdict: Optional[VerdictNode], db) ->
list[str]`.
Return shape: [] when met or None; else, walking the tree: an unmet leaf
-> `requirement_detail_fr(verdict)`; an unknown leaf -> its reason; under
a `not`, a MET leaf -> « il ne faut pas que : <leaf_text, first letter
lowered> ».

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

## Context

The language exists (B). This brief stores it (O-a: rows, never JSON, R-14), migrates the two requirement tables into it and drops them (v2.20, C-10), and rewires every reader and writer (R-05) so that day plans, quest offers and accepted quests all store and judge a tree (I1). The forms become twelve (S1). The offer API keeps its flat lists here (R-20): D switches it to trees together with the editor.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md` and `src/world_engine/cockpit/static/` are not in the
diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - declares `condition` and `condition_node` in `models/config.py` (C-06), retires the two requirement models, bumps `schema_version.py` to v2.20, and documents both in `world-engine-schema.md` and its changelog;
   - creates `src/world_engine/writes/conditions.py` (`clean_leaf`, `clean_condition`, `write_condition`, `delete_offer_conditions`) and `read_condition` in `conditions.py`; moves `_clean_requirement`'s rules into `clean_leaf` (R-09);
   - creates `scripts/migrate_v2_20_conditions.py` (C-10, b-5) and freezes the dropped tables' DDL in the three old migrations that built them (R-17);
   - adds `item_held`, `vital_status` and `quest_state` (replacing `quest_completed`) to `condition_forms.py`, their French in `condition_text.py` and `day_resolve.py`, and their lines in `frontend/src/creation/questRequirements.js` (C-02, b-3);
   - rewires `day_plan.py` (C-07), `writes/goals_agendas.py`, `writes/quests.py`, `quest_reads.py`, `routes/quests.py`, `routes/day.py` and `day_mutations.py` (Q1, b-4), `day_reconcile_apply.py` and `day_resolve.py` (C-08), `writes/worlds.py` (the cascade);
   - updates `canon_write_policy.txt`, `single_canon_write.py`, `world_cascade.py`, `day_plan.py`, `quests.py`, `debts.py`, `quest_rewards.py`, `knowledge_identity.py` to the same meaning on the new storage (R-18), and adds CC1-CC5 to `conditions.py`;
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - frontend/src/creation/QuestRequirementRow.svelte
   - frontend/src/creation/questRequirements.js
   - scripts/migrate_v1_94_agenda_step_plan.py
   - scripts/migrate_v2_17_quests.py
   - scripts/migrate_v2_19_debts.py
   - scripts/migrate_v2_20_conditions.py
   - src/world_engine/cockpit/day_reconcile_apply.py
   - src/world_engine/cockpit/routes/day.py
   - src/world_engine/cockpit/routes/quests.py
   - src/world_engine/condition_forms.py
   - src/world_engine/condition_text.py
   - src/world_engine/conditions.py
   - src/world_engine/day_mutations.py
   - src/world_engine/day_plan.py
   - src/world_engine/day_resolve.py
   - src/world_engine/models/__init__.py
   - src/world_engine/models/canon.py
   - src/world_engine/models/config.py
   - src/world_engine/models/quests.py
   - src/world_engine/quest_reads.py
   - src/world_engine/schema_version.py
   - src/world_engine/writes/__init__.py
   - src/world_engine/writes/conditions.py
   - src/world_engine/writes/goals_agendas.py
   - src/world_engine/writes/quests.py
   - src/world_engine/writes/worlds.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/canon_write_policy.txt
   - tooling/verify/checks/conditions.py
   - tooling/verify/checks/day_plan.py
   - tooling/verify/checks/debts.py
   - tooling/verify/checks/knowledge_identity.py
   - tooling/verify/checks/quest_rewards.py
   - tooling/verify/checks/quests.py
   - tooling/verify/checks/single_canon_write.py
   - tooling/verify/checks/world_cascade.py
   - world-engine-schema-changelog.md
   - world-engine-schema.md
2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. On the TEST database only (`WORLD_ENGINE_ENV=test`): `python scripts/migrate_v2_20_conditions.py` -> `Migration v2.20 applied.`; a second run -> `Schema already in place.` and `Migration v2.20 applied.` again. Never run it with `WORLD_ENGINE_ENV=prod`: that is Nia's live gate.
4. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
5. Commit message: `feat(conditions): conditions are stored as trees (v2.20), one language for every agenda, twelve forms (BRIEF-0111-c)`.

````diff
diff --git a/frontend/src/creation/QuestRequirementRow.svelte b/frontend/src/creation/QuestRequirementRow.svelte
index 3cab2b1..5d0b8ce 100644
--- a/frontend/src/creation/QuestRequirementRow.svelte
+++ b/frontend/src/creation/QuestRequirementRow.svelte
@@ -2,18 +2,20 @@
   /* TICKET-0108 (BRIEF-0108-C). One requirement of a quest offer: its form,
      its target from the matching picker list, its threshold when the form
      takes one. `req` is a draft object owned by questOffersState. */
-  import { REQUIREMENT_FORMS, targetOptions } from './questRequirements.js';
+  import { REQUIREMENT_FORMS, targetOptions, valueOptions } from './questRequirements.js';
 
   let { req, choices, onremove } = $props();
 
   let form = $derived(REQUIREMENT_FORMS[req.type]);
   let options = $derived(targetOptions(req.type, choices));
+  let values = $derived(valueOptions(req.type, choices));
 
   function setType(type) {
     req.type = type;
     req.target_entity_id = '';
     req.target_key = '';
     req.threshold = REQUIREMENT_FORMS[type].threshold ? 1 : null;
+    req.value = '';
   }
 
   function setTarget(value) {
@@ -28,7 +30,7 @@
       <option value={type}>{f.label}</option>
     {/each}
   </select>
-  {#if form.list !== 'money'}
+  {#if form.list !== 'money' && form.column !== 'none'}
     <select value={form.column === 'entity' ? req.target_entity_id : req.target_key}
             onchange={(e) => setTarget(e.target.value)}>
       <option value="">—</option>
@@ -37,6 +39,14 @@
       {/each}
     </select>
   {/if}
+  {#if form.values}
+    <select value={req.value ?? ''} onchange={(e) => { req.value = e.target.value; }}>
+      <option value="">—</option>
+      {#each values as v (v.value)}
+        <option value={v.value}>{v.label}</option>
+      {/each}
+    </select>
+  {/if}
   {#if form.threshold}
     <input type="number" min="1" max={req.type === 'skill_rank_gte' ? 5 : undefined}
            style="width:70px" value={req.threshold ?? ''}
diff --git a/frontend/src/creation/questRequirements.js b/frontend/src/creation/questRequirements.js
index c64079c..f3ea6bd 100644
--- a/frontend/src/creation/questRequirements.js
+++ b/frontend/src/creation/questRequirements.js
@@ -6,7 +6,11 @@
    `ENTITY_TARGET_TYPES`, `KEY_TARGET_TYPES` and `THRESHOLD_TYPES` across
    the network boundary -- kept equal by `quests.py` (QC1), never by hand
    alone. TICKET-0110 (BRIEF-0110-A): the two debt forms, whose target is
-   a creditor -- a character or a faction (the `givers` list). */
+   a creditor -- a character or a faction (the `givers` list).
+   TICKET-0111 (BRIEF-0111-C): `quest_state` replaces `quest_completed`;
+   `item_held` and `vital_status` are new. `column: 'none'` is a form with
+   no target (`NO_TARGET_TYPES`); `values: true` a form that compares to a
+   value, its choices in `choices.form_values[form]`. */
 
 export const REQUIREMENT_FORMS = {
   knowledge: { label: 'Connaît le fait', list: 'facts', column: 'key', threshold: false },
@@ -16,9 +20,11 @@ export const REQUIREMENT_FORMS = {
   has_met: { label: 'A rencontré', list: 'characters', column: 'entity', threshold: false },
   faction_member: { label: 'Est membre de', list: 'factions', column: 'entity', threshold: false },
   skill_rank_gte: { label: 'Compétence au rang (≥)', list: 'skills', column: 'key', threshold: true },
-  quest_completed: { label: 'A accompli la quête', list: 'offers', column: 'key', threshold: false },
+  quest_state: { label: 'Quête dans l’état', list: 'offers', column: 'key', threshold: false, values: true },
   has_debt_to: { label: 'A une dette envers', list: 'givers', column: 'entity', threshold: false },
   no_debt_to: { label: 'N’a aucune dette envers', list: 'givers', column: 'entity', threshold: false },
+  item_held: { label: 'Possède au moins (objet)', list: 'items', column: 'entity', threshold: true },
+  vital_status: { label: 'Est dans l’état', list: 'none', column: 'none', threshold: false, values: true },
 };
 
 // `resource`'s key is a label: one currency per world (the ledger has no
@@ -28,7 +34,7 @@ export const MONEY_KEY = 'monnaie';
 export const STEP_DOMAINS = ['physical', 'agility', 'perception', 'composure'];
 
 export function blankRequirement() {
-  return { type: 'has_met', target_entity_id: '', target_key: '', threshold: null };
+  return { type: 'has_met', target_entity_id: '', target_key: '', threshold: null, value: '' };
 }
 
 /** The (value, label) options of a form's picker, from the editor's choices. */
@@ -42,10 +48,16 @@ export function targetOptions(form, choices) {
     case 'locations': return choices.locations.map((c) => ({ value: c.id, label: c.name }));
     case 'factions': return choices.factions.map((c) => ({ value: c.id, label: c.name }));
     case 'givers': return choices.givers.map((c) => ({ value: c.id, label: c.name }));
+    case 'items': return choices.items.map((c) => ({ value: c.id, label: c.name }));
     default: return [];
   }
 }
 
+/** The (value, label) options of a form that compares to a value. */
+export function valueOptions(form, choices) {
+  return (choices?.form_values?.[form] || []).map((v) => ({ value: v.value, label: v.label }));
+}
+
 /** The request body of one requirement row: only the columns its form uses. */
 export function requirementBody(req) {
   const form = REQUIREMENT_FORMS[req.type];
@@ -54,5 +66,6 @@ export function requirementBody(req) {
     target_entity_id: form.column === 'entity' ? (req.target_entity_id || null) : null,
     target_key: form.list === 'money' ? MONEY_KEY : form.column === 'key' ? (req.target_key || null) : null,
     threshold: form.threshold ? (req.threshold === '' || req.threshold === null ? null : Number(req.threshold)) : null,
+    value: form.values ? (req.value || null) : null,
   };
 }
diff --git a/scripts/migrate_v1_94_agenda_step_plan.py b/scripts/migrate_v1_94_agenda_step_plan.py
index 3b52885..d4cc578 100644
--- a/scripts/migrate_v1_94_agenda_step_plan.py
+++ b/scripts/migrate_v1_94_agenda_step_plan.py
@@ -41,15 +41,30 @@ if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
 
 from sqlalchemy import inspect, text  # noqa: E402
 
-from world_engine import models  # noqa: E402
 from world_engine.db import engine  # noqa: E402
 
-
-def _ensure_table(model: type) -> bool:
+# `agenda_step_requirement` as v1.94 created it, frozen: TICKET-0111
+# (BRIEF-0111-C) dropped the table and its model at v2.20.
+_REQUIREMENT_DDL = (
+    """CREATE TABLE agenda_step_requirement (
+	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, step_id VARCHAR NOT NULL,
+	type VARCHAR NOT NULL, target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER,
+	PRIMARY KEY (id),
+	CONSTRAINT ck_agenda_step_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable')),
+	CONSTRAINT ck_agenda_step_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource') OR threshold IS NOT NULL)),
+	FOREIGN KEY(world_id) REFERENCES world (id),
+	FOREIGN KEY(step_id) REFERENCES agenda_step (id),
+	FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
+    "CREATE UNIQUE INDEX idx_agenda_step_requirement_unique ON agenda_step_requirement (step_id, type, target_entity_id, target_key)",
+)
+
+
+def _ensure_table() -> bool:
     inspector = inspect(engine)
-    if model.__tablename__ in inspector.get_table_names():
+    if "agenda_step_requirement" in inspector.get_table_names():
         return False
-    model.__table__.create(engine)
+    with engine.begin() as conn:
+        conn.execute(text(_REQUIREMENT_DDL[0]))
     return True
 
 
@@ -58,14 +73,12 @@ def _index_names(tablename: str) -> set[str]:
     return {ix["name"] for ix in inspector.get_indexes(tablename)}
 
 
-def _ensure_indexes(model: type) -> list[str]:
-    applied: list[str] = []
-    existing = _index_names(model.__tablename__)
-    for index in model.__table__.indexes:
-        if index.name not in existing:
-            index.create(engine)
-            applied.append(index.name)
-    return applied
+def _ensure_indexes() -> list[str]:
+    if "idx_agenda_step_requirement_unique" in _index_names("agenda_step_requirement"):
+        return []
+    with engine.begin() as conn:
+        conn.execute(text(_REQUIREMENT_DDL[1]))
+    return ["idx_agenda_step_requirement_unique"]
 
 
 def _agenda_step_columns() -> set[str]:
@@ -100,12 +113,12 @@ def main() -> None:
             "Post-check failed: agenda_step.cost/domain still missing after ALTER TABLE."
         )
 
-    created = _ensure_table(models.AgendaStepRequirement)
+    created = _ensure_table()
     print(
         f"Schema: {'created table' if created else 'table already present'} "
         "`agenda_step_requirement`"
     )
-    applied = _ensure_indexes(models.AgendaStepRequirement)
+    applied = _ensure_indexes()
     if applied:
         print(f"Schema: created index(es) on `agenda_step_requirement`: {', '.join(applied)}")
     else:
diff --git a/scripts/migrate_v2_17_quests.py b/scripts/migrate_v2_17_quests.py
index ded26fb..893a0af 100644
--- a/scripts/migrate_v2_17_quests.py
+++ b/scripts/migrate_v2_17_quests.py
@@ -57,10 +57,49 @@ from world_engine.db import engine  # noqa: E402
 from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402
 
 _PREVIOUS_VERSION = "v2.16"
+
+
+class _Retired:
+    """A table the code no longer declares -- TICKET-0111 (BRIEF-0111-C)
+    dropped it at v2.20, its rows converted into `condition` trees. Its DDL
+    is frozen here as this migration created it, so the migration still
+    runs on the database it was written for."""
+
+    def __init__(self, name: str, ddl: tuple[str, ...]) -> None:
+        self.__tablename__ = name
+        self.ddl = ddl
+
+
+_AGENDA_STEP_REQUIREMENT = _Retired("agenda_step_requirement", (
+    """CREATE TABLE agenda_step_requirement (
+	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, step_id VARCHAR NOT NULL,
+	type VARCHAR NOT NULL, target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER,
+	PRIMARY KEY (id),
+	CONSTRAINT ck_agenda_step_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed')),
+	CONSTRAINT ck_agenda_step_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable','has_met','faction_member') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)),
+	FOREIGN KEY(world_id) REFERENCES world (id),
+	FOREIGN KEY(step_id) REFERENCES agenda_step (id),
+	FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
+    "CREATE UNIQUE INDEX idx_agenda_step_requirement_unique ON agenda_step_requirement (step_id, type, target_entity_id, target_key)",
+))
+
+_QUEST_OFFER_REQUIREMENT = _Retired("quest_offer_requirement", (
+    """CREATE TABLE quest_offer_requirement (
+	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, offer_id VARCHAR NOT NULL, step_id VARCHAR,
+	type VARCHAR NOT NULL, target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER,
+	PRIMARY KEY (id),
+	CONSTRAINT ck_quest_offer_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed')),
+	CONSTRAINT ck_quest_offer_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable','has_met','faction_member') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)),
+	FOREIGN KEY(world_id) REFERENCES world (id),
+	FOREIGN KEY(offer_id) REFERENCES quest_offer (id),
+	FOREIGN KEY(step_id) REFERENCES quest_offer_step (id),
+	FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
+    "CREATE INDEX idx_quest_offer_requirement_offer ON quest_offer_requirement (offer_id)",
+))
 _REQUIREMENT_COLUMNS = "id, world_id, step_id, type, target_entity_id, target_key, threshold"
 _NEW_FORMS = ("has_met", "faction_member", "skill_rank_gte", "quest_completed")
 # Parents first: an offer before its steps, its steps before its requirements.
-_NEW_MODELS = (models.QuestOffer, models.QuestOfferStep, models.QuestOfferRequirement, models.Quest)
+_NEW_MODELS = (models.QuestOffer, models.QuestOfferStep, _QUEST_OFFER_REQUIREMENT, models.Quest)
 # The tables this migration writes: the only ones its foreign-key post-check judges.
 _TOUCHED_TABLES = ("agenda_step_requirement",) + tuple(m.__tablename__ for m in _NEW_MODELS)
 
@@ -95,6 +134,10 @@ def _row_count(table: str) -> int:
 
 
 def _create_from_model(cursor, model) -> None:
+    if isinstance(model, _Retired):
+        for statement in model.ddl:
+            cursor.execute(statement)
+        return
     cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
     for index in model.__table__.indexes:
         cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))
@@ -107,7 +150,7 @@ def _rebuild_requirements(cursor) -> None:
     ).fetchall():
         cursor.execute(f"DROP INDEX {index_name}")
     cursor.execute("ALTER TABLE agenda_step_requirement RENAME TO agenda_step_requirement_old")
-    _create_from_model(cursor, models.AgendaStepRequirement)
+    _create_from_model(cursor, _AGENDA_STEP_REQUIREMENT)
     cursor.execute(
         f"INSERT INTO agenda_step_requirement ({_REQUIREMENT_COLUMNS}) "
         f"SELECT {_REQUIREMENT_COLUMNS} FROM agenda_step_requirement_old"
diff --git a/scripts/migrate_v2_19_debts.py b/scripts/migrate_v2_19_debts.py
index c6bb13f..6d57242 100644
--- a/scripts/migrate_v2_19_debts.py
+++ b/scripts/migrate_v2_19_debts.py
@@ -70,9 +70,43 @@ _REQUIREMENT_COLUMNS = {
     "agenda_step_requirement": "id, world_id, step_id, type, target_entity_id, target_key, threshold",
     "quest_offer_requirement": "id, world_id, offer_id, step_id, type, target_entity_id, target_key, threshold",
 }
+class _Retired:
+    """A table the code no longer declares -- TICKET-0111 (BRIEF-0111-C)
+    dropped it at v2.20, its rows converted into `condition` trees. Its DDL
+    is frozen here as this migration created it, so the migration still
+    runs on the database it was written for."""
+
+    def __init__(self, name: str, ddl: tuple[str, ...]) -> None:
+        self.__tablename__ = name
+        self.ddl = ddl
+
+
 _REQUIREMENT_MODELS = {
-    "agenda_step_requirement": models.AgendaStepRequirement,
-    "quest_offer_requirement": models.QuestOfferRequirement,
+    "agenda_step_requirement": _Retired("agenda_step_requirement", (
+    """CREATE TABLE agenda_step_requirement (
+	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, step_id VARCHAR NOT NULL,
+	type VARCHAR NOT NULL, target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER,
+	PRIMARY KEY (id),
+	CONSTRAINT ck_agenda_step_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed','has_debt_to','no_debt_to')),
+	CONSTRAINT ck_agenda_step_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable','has_met','faction_member','has_debt_to','no_debt_to') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)),
+	FOREIGN KEY(world_id) REFERENCES world (id),
+	FOREIGN KEY(step_id) REFERENCES agenda_step (id),
+	FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
+    "CREATE UNIQUE INDEX idx_agenda_step_requirement_unique ON agenda_step_requirement (step_id, type, target_entity_id, target_key)",
+    )),
+    "quest_offer_requirement": _Retired("quest_offer_requirement", (
+    """CREATE TABLE quest_offer_requirement (
+	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, offer_id VARCHAR NOT NULL, step_id VARCHAR,
+	type VARCHAR NOT NULL, target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER,
+	PRIMARY KEY (id),
+	CONSTRAINT ck_quest_offer_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed','has_debt_to','no_debt_to')),
+	CONSTRAINT ck_quest_offer_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable','has_met','faction_member','has_debt_to','no_debt_to') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)),
+	FOREIGN KEY(world_id) REFERENCES world (id),
+	FOREIGN KEY(offer_id) REFERENCES quest_offer (id),
+	FOREIGN KEY(step_id) REFERENCES quest_offer_step (id),
+	FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
+    "CREATE INDEX idx_quest_offer_requirement_offer ON quest_offer_requirement (offer_id)",
+    )),
 }
 _ECONOMY_COLUMNS = ("id, world_id, rate_money, rate_relation, rate_fact, rate_skill, band_low_pct, "
                     "band_high_pct, updated_at")
@@ -116,6 +150,10 @@ def _row_counts() -> dict[str, int]:
 
 
 def _create_from_model(cursor, model) -> None:
+    if isinstance(model, _Retired):
+        for statement in model.ddl:
+            cursor.execute(statement)
+        return
     cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
     for index in model.__table__.indexes:
         cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))
diff --git a/scripts/migrate_v2_20_conditions.py b/scripts/migrate_v2_20_conditions.py
new file mode 100644
index 0000000..81fe9d7
--- /dev/null
+++ b/scripts/migrate_v2_20_conditions.py
@@ -0,0 +1,244 @@
+"""Migration v2.20 — the condition language (TICKET-0111, BRIEF-0111-C,
+decisions A1, I1, O-a, S1).
+
+1. Create. `condition` and `condition_node`, from their models, when
+   missing.
+2. Convert. Every requirement row becomes a leaf of a tree, one tree per
+   owner: an offer's eligibility (a `quest_offer_requirement` row with no
+   step), an offer step's prerequisite (one with a step), an agenda step's
+   prerequisite (an `agenda_step_requirement` row). Each tree is `all` of its
+   leaves -- the meaning a list of requirements always had -- in the rows'
+   insertion order (`rowid`). Every leaf judges the one who acts
+   (`subject_role = 'doer'`, what every evaluator did). A `quest_completed`
+   row becomes `quest_state` with the value `completed` (S1: one form for a
+   quest's state); every other form keeps its name and arguments.
+3. Drop. `agenda_step_requirement` and `quest_offer_requirement`, once their
+   rows are converted, in the same transaction.
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.19 (the migrations are sequential), before any change.
+
+Idempotent: the tables are created only when missing; the conversion and
+the drop run only while an old table still exists. A second run finds
+nothing to do.
+
+Post-checks, before `schema_meta` converges: neither old table remains;
+the leaves written equal the rows read, form by form (`quest_completed`
+counted as `quest_state`); every condition has exactly one root;
+`PRAGMA foreign_key_check` is empty on the two tables this migration writes.
+A dangling reference elsewhere predates it: it is listed, never a reason to
+stop (AMENDMENT-0107-01).
+
+Run from the project root:
+
+    python scripts/migrate_v2_20_conditions.py
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+import uuid
+from collections import Counter
+from datetime import UTC, datetime
+from pathlib import Path
+
+SRC = Path(__file__).resolve().parent.parent / "src"
+sys.path.insert(0, str(SRC))
+
+_env = os.environ.get("WORLD_ENGINE_ENV")
+if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
+    print(
+        "migrate_v2_20_conditions.py refuses to run without WORLD_ENGINE_ENV "
+        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
+        f"{_env or 'unset'}.",
+        file=sys.stderr,
+    )
+    sys.exit(1)
+
+from sqlalchemy import inspect, text  # noqa: E402
+from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402
+from sqlmodel import Session  # noqa: E402
+
+from world_engine import models  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402
+
+_PREVIOUS_VERSION = "v2.19"
+_OLD_TABLES = ("agenda_step_requirement", "quest_offer_requirement")
+# Parents first: a condition before its nodes.
+_NEW_MODELS = (models.Condition, models.ConditionNode)
+_TOUCHED_TABLES = ("condition", "condition_node")
+_RENAMED_FORMS = {"quest_completed": ("quest_state", "completed")}
+
+
+def _version_key(version: str) -> tuple[int, int]:
+    major, minor = version.lstrip("v").split(".")
+    return int(major), int(minor)
+
+
+def _refuse() -> None:
+    with engine.connect() as conn:
+        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
+    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
+        found = row[0] if row is not None else "no schema_meta row"
+        raise SystemExit(
+            f"Migration v2.20 refused: the database is at {found!r}; run the migrations "
+            f"up to {_PREVIOUS_VERSION} first."
+        )
+
+
+def _create_from_model(cursor, model) -> None:
+    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
+    for index in model.__table__.indexes:
+        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))
+
+
+def _read_groups(cursor, present: set[str]) -> list[tuple[str, str, str, str, list[tuple]]]:
+    """(world_id, owner column, owner id, role, rows) per tree to write; a
+    row is (type, target_entity_id, target_key, threshold)."""
+    groups: dict[tuple[str, str, str], list[tuple]] = {}
+    worlds: dict[tuple[str, str, str], str] = {}
+    selects = []
+    if "quest_offer_requirement" in present:
+        selects.append(
+            "SELECT world_id, CASE WHEN step_id IS NULL THEN 'quest_offer_id' ELSE 'quest_offer_step_id' END, "
+            "COALESCE(step_id, offer_id), CASE WHEN step_id IS NULL THEN 'eligibility' ELSE 'prerequisite' END, "
+            "type, target_entity_id, target_key, threshold FROM quest_offer_requirement ORDER BY rowid"
+        )
+    if "agenda_step_requirement" in present:
+        selects.append(
+            "SELECT world_id, 'agenda_step_id', step_id, 'prerequisite', type, target_entity_id, target_key, "
+            "threshold FROM agenda_step_requirement ORDER BY rowid"
+        )
+    for select in selects:
+        for world_id, column, owner_id, role, *leaf in cursor.execute(select).fetchall():
+            key = (column, owner_id, role)
+            groups.setdefault(key, []).append(tuple(leaf))
+            worlds[key] = world_id
+    return [(worlds[key], *key, rows) for key, rows in groups.items()]
+
+
+def _write_tree(cursor, world_id: str, column: str, owner_id: str, role: str, rows: list[tuple]) -> None:
+    condition_id, root_id = str(uuid.uuid4()), str(uuid.uuid4())
+    cursor.execute(
+        f"INSERT INTO condition (id, world_id, role, {column}, created_at) VALUES (?, ?, ?, ?, ?)",
+        (condition_id, world_id, role, owner_id, datetime.now(UTC).isoformat(" ")),
+    )
+    cursor.execute(
+        "INSERT INTO condition_node (id, world_id, condition_id, parent_id, position, op) "
+        "VALUES (?, ?, ?, NULL, 0, 'all')", (root_id, world_id, condition_id),
+    )
+    for position, (form, target_entity_id, target_key, threshold) in enumerate(rows):
+        form, value = _RENAMED_FORMS.get(form, (form, None))
+        cursor.execute(
+            "INSERT INTO condition_node (id, world_id, condition_id, parent_id, position, op, form, subject_role, "
+            "target_entity_id, target_key, threshold, value) VALUES (?, ?, ?, ?, ?, 'leaf', ?, 'doer', ?, ?, ?, ?)",
+            (str(uuid.uuid4()), world_id, condition_id, root_id, position, form, target_entity_id, target_key,
+             threshold, value),
+        )
+
+
+def _old_forms(cursor, present: set[str]) -> Counter:
+    counts: Counter = Counter()
+    for table in present & set(_OLD_TABLES):
+        for (form,) in cursor.execute(f"SELECT type FROM {table}").fetchall():
+            counts[_RENAMED_FORMS.get(form, (form, None))[0]] += 1
+    return counts
+
+
+def _apply() -> tuple[list[str], Counter]:
+    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
+    PRAGMAs must land before any transaction exists)."""
+    existing = set(inspect(engine).get_table_names())
+    present = existing & set(_OLD_TABLES)
+    missing = [model for model in _NEW_MODELS if model.__tablename__ not in existing]
+    if not (present or missing):
+        return [], Counter()
+    applied: list[str] = []
+    raw = engine.raw_connection()
+    try:
+        cursor = raw.cursor()
+        cursor.execute("PRAGMA foreign_keys=OFF")
+        cursor.execute("PRAGMA legacy_alter_table=ON")
+        cursor.execute("BEGIN")
+        for model in missing:
+            _create_from_model(cursor, model)
+            applied.append(f"{model.__tablename__} created")
+        read = _old_forms(cursor, present)
+        groups = _read_groups(cursor, present)
+        for world_id, column, owner_id, role, rows in groups:
+            _write_tree(cursor, world_id, column, owner_id, role, rows)
+        if present:
+            applied.append(f"{len(groups)} condition(s) written from {sum(read.values())} requirement row(s)")
+        for table in sorted(present):
+            cursor.execute(f"DROP TABLE {table}")
+            applied.append(f"{table} dropped")
+        cursor.execute("COMMIT")
+        cursor.execute("PRAGMA legacy_alter_table=OFF")
+        cursor.execute("PRAGMA foreign_keys=ON")
+        cursor.close()
+    except Exception:
+        raw.rollback()
+        raise
+    finally:
+        raw.close()
+    return applied, read
+
+
+def _post_checks(read: Counter) -> None:
+    tables = set(inspect(engine).get_table_names())
+    left = sorted(tables & set(_OLD_TABLES))
+    missing = [m.__tablename__ for m in _NEW_MODELS if m.__tablename__ not in tables]
+    if left or missing:
+        raise SystemExit(f"Migration v2.20 aborted, post-check failed: still present {left}, missing {missing}.")
+    with engine.connect() as conn:
+        written = Counter(dict(conn.execute(text(
+            "SELECT form, COUNT(*) FROM condition_node WHERE op = 'leaf' GROUP BY form")).fetchall()))
+        roots = conn.execute(text(
+            "SELECT c.id FROM condition c LEFT JOIN condition_node n ON n.condition_id = c.id AND n.parent_id IS NULL "
+            "GROUP BY c.id HAVING COUNT(n.id) <> 1")).fetchall()
+        dangling = [row for table in _TOUCHED_TABLES
+                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
+        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
+                     if row[0] not in _TOUCHED_TABLES]
+    if read and written != read:
+        raise SystemExit(f"Migration v2.20 aborted, post-check failed: leaves {dict(written)} for rows {dict(read)}.")
+    if roots:
+        raise SystemExit(f"Migration v2.20 aborted, post-check failed: {len(roots)} condition(s) without one root.")
+    if dangling:
+        raise SystemExit(f"Migration v2.20 aborted, post-check failed: foreign_key_check {dangling}.")
+    for table, rowid, parent, _fk in elsewhere:
+        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
+    print(f"Post-check: old tables gone; leaves by form {dict(sorted(written.items()))}; one root per condition.")
+
+
+def _converge_schema_meta() -> None:
+    with Session(engine) as session:
+        row = session.get(models.SchemaMeta, 1)
+        if row is None:
+            session.add(models.SchemaMeta(id=1, static_version=EXPECTED_STATIC_SCHEMA_VERSION))
+            print(f"Row: seeded schema_meta.id=1 at {EXPECTED_STATIC_SCHEMA_VERSION!r}")
+        elif row.static_version != EXPECTED_STATIC_SCHEMA_VERSION:
+            previous = row.static_version
+            row.static_version = EXPECTED_STATIC_SCHEMA_VERSION
+            row.updated_at = datetime.now(UTC)
+            session.add(row)
+            print(f"Row: updated schema_meta.id=1: {previous!r} -> {EXPECTED_STATIC_SCHEMA_VERSION!r}")
+        else:
+            print(f"Row: schema_meta.id=1 already at {EXPECTED_STATIC_SCHEMA_VERSION!r} — nothing to do")
+        session.commit()
+
+
+def main() -> None:
+    print("Migration v2.20 — the condition language: requirement rows become condition trees")
+    _refuse()
+    applied, read = _apply()
+    print("Applied: " + ", ".join(applied) + "." if applied else "Schema already in place.")
+    _post_checks(read)
+    _converge_schema_meta()
+    print("\nMigration v2.20 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/world_engine/cockpit/day_reconcile_apply.py b/src/world_engine/cockpit/day_reconcile_apply.py
index 4c544a8..4b4dd24 100644
--- a/src/world_engine/cockpit/day_reconcile_apply.py
+++ b/src/world_engine/cockpit/day_reconcile_apply.py
@@ -30,7 +30,7 @@ from .. import day_plans, day_rewrite
 from ..day_concordance import ConcordanceResult
 from ..day_plan import emit_plan, evaluate_agenda_step
 from ..day_reconcile import Reconciliation, plan_action, reconcile
-from ..day_resolve import requirement_detail_fr
+from ..day_resolve import blocked_details_fr
 from ..llm_parse import LlmParseError
 from ..models import Agenda, AgendaStep, Character, PassPlay
 from ..writes import next_day_rewrite_generation, write_agenda_status, write_day_rewrite
@@ -71,7 +71,7 @@ def _refuse_unstarted_plan(character: Character, agenda: Agenda, db: Session) ->
             ),
         )
     evaluated = evaluate_agenda_step(pending_step, character, db)
-    unmet = [requirement_detail_fr(v) for v in evaluated.verdicts if not v.met]
+    unmet = blocked_details_fr(evaluated.verdict, db)
     detail = "; ".join(unmet) if unmet else (
         "aucun prerequis non satisfait - le veto de faisabilite a juge l'action elle-meme irrealisable"
     )
diff --git a/src/world_engine/cockpit/routes/day.py b/src/world_engine/cockpit/routes/day.py
index 3b73439..12130bb 100644
--- a/src/world_engine/cockpit/routes/day.py
+++ b/src/world_engine/cockpit/routes/day.py
@@ -41,6 +41,7 @@ from ...day_mutations import emit_mutations
 # `rewrite` here is day_narration's late-delta prose rewrite -- unrelated to
 # the day_rewrite MODULE imported above (declaration rewrite, BRIEF-0081-b);
 # aliased to keep the two "rewrite" concepts from colliding on one name.
+from ...conditions import Bindings, and_path_leaves, read_condition
 from ...day_narration import detect_late_delta, narrate, rewrite as rewrite_narration
 from ...day_narration_guard import JudgeVerdict, judge_narration, lowercase_offending_words
 from ...day_plan import (
@@ -64,7 +65,6 @@ from ...prompt_coverage import DAY_CHAIN_USAGES, missing_usages
 from ...models import (
     Agenda,
     AgendaStep,
-    AgendaStepRequirement,
     Batch,
     Character,
     DayRewrite,
@@ -296,13 +296,13 @@ def _account_rendezvous(mutations: list[ProposedMutation], db: Session) -> Optio
     if active_step is None:
         return None
 
+    # Q1 (TICKET-0111): the day's NPC is the target of the first
+    # `relation_gte` the step cannot be met without -- reached through `all`.
     npc_id, npc_name = None, None
-    for req in db.exec(
-        select(AgendaStepRequirement).where(
-            AgendaStepRequirement.step_id == active_step.id,
-            AgendaStepRequirement.type == "relation_gte",
-        )
-    ).all():
+    prerequisite = read_condition(db, role="prerequisite", agenda_step_id=active_step.id)
+    for req in and_path_leaves(prerequisite):
+        if req.type != "relation_gte":
+            continue
         target = db.get(Entity, req.target_entity_id) if req.target_entity_id else None
         if target is not None:
             npc_id, npc_name = target.id, target.name
@@ -551,11 +551,12 @@ def _finalize_plan(
 ) -> dict:
     # BRIEF-0078-a, Scope IN item 7: anchoring runs BEFORE evaluate_requirements
     # so a dropped requirement never reaches evaluate_requirements or
-    # agenda_step_requirement (E2 — reporting, never refusing: /plan still
+    # the step's stored condition (E2 — reporting, never refusing: /plan still
     # returns 200 and writes the plan exactly as it does today).
     anchored_steps, dropped_report = anchor_requirements(raw_steps, character, db)
+    bindings = Bindings(doer=character)
     evaluated_steps = [
-        EvaluatedStep(step=step, verdicts=tuple(evaluate_requirements(step, character, db)))
+        EvaluatedStep(step=step, verdict=evaluate_requirements(step, bindings, db))
         for step in anchored_steps
     ]
     budget_result = budget_cut(evaluated_steps, DAY_BUDGET_SLOTS)
diff --git a/src/world_engine/cockpit/routes/quests.py b/src/world_engine/cockpit/routes/quests.py
index d805dfb..5f7fb89 100644
--- a/src/world_engine/cockpit/routes/quests.py
+++ b/src/world_engine/cockpit/routes/quests.py
@@ -32,6 +32,7 @@ from sqlmodel import Session, select
 
 from ... import quest_reads
 from ...condition_forms import RequirementSpec
+from ...conditions import all_of
 from ...day_plan import PlanStep
 from ...db import get_session
 from ...models import Quest, QuestEconomy, QuestOffer
@@ -53,6 +54,11 @@ class RequirementBody(BaseModel):
     target_entity_id: Optional[str] = None
     target_key: Optional[str] = None
     threshold: Optional[int] = None
+    # TICKET-0111 (P1, S1): the leaf's subject (a role, else one entity) and
+    # the value of a form that compares to one.
+    subject_role: Optional[str] = None
+    subject_entity_id: Optional[str] = None
+    value: Optional[str] = None
 
 
 class OfferStepBody(BaseModel):
@@ -118,18 +124,21 @@ class CreditBody(BaseModel):
 
 
 def _spec(req: RequirementBody) -> RequirementSpec:
+    subject_entity_id = req.subject_entity_id or None
     return RequirementSpec(type=req.type, target_entity_id=req.target_entity_id or None,
-                           target_key=req.target_key or None, threshold=req.threshold)
+                           target_key=req.target_key or None, threshold=req.threshold,
+                           subject_role=req.subject_role or (None if subject_entity_id else "doer"),
+                           subject_entity_id=subject_entity_id, value=req.value or None)
 
 
 def _save_offer(body: OfferBody, offer: Optional[QuestOffer], world_id: str, db: Session) -> dict:
     steps = [PlanStep(objective=s.objective, cost=s.cost, domain=s.domain or None,
-                      requirements=tuple(_spec(r) for r in s.requirements)) for s in body.steps]
+                      prerequisite=all_of(_spec(r) for r in s.requirements)) for s in body.steps]
     try:
         offer = write_quest_offer(
             db, world_id=world_id, offer=offer, giver_entity_id=body.giver_entity_id, title=body.title,
             summary=body.summary, repeatable=body.repeatable, status=body.status,
-            eligibility=[_spec(r) for r in body.eligibility], steps=steps,
+            eligibility=all_of(_spec(r) for r in body.eligibility), steps=steps,
             terms=None if body.terms is None else [_term(t) for t in body.terms],
             contact_entity_id=body.contact_entity_id or None,
         )
diff --git a/src/world_engine/condition_forms.py b/src/world_engine/condition_forms.py
index 55ffafe..e2b13bf 100644
--- a/src/world_engine/condition_forms.py
+++ b/src/world_engine/condition_forms.py
@@ -45,6 +45,7 @@ from .models import (
     Entity,
     Fact,
     FactionMembership,
+    ItemHolding,
     Knowledge,
     Ledger,
     Quest,
@@ -60,11 +61,14 @@ from .skill_access import held_rank, skill_label
 # Eight forms since v2.17 (TICKET-0108, BRIEF-0108-A, C-01): the four the
 # day-plan model may emit, then four only the creator authors (quest offers).
 # Ten since v2.19 (TICKET-0110, BRIEF-0110-A, G1): `has_debt_to` and
-# `no_debt_to`, creator only as well.
+# `no_debt_to`, creator only as well. Twelve since v2.20 (TICKET-0111,
+# BRIEF-0111-C, S1): `quest_state` replaces `quest_completed` (a quest in
+# any of its four states, `completed` among them), `item_held` and
+# `vital_status` read data the canon already keeps.
 REQUIREMENT_TYPES: tuple[str, ...] = (
     "knowledge", "relation_gte", "resource", "location_reachable",
-    "has_met", "faction_member", "skill_rank_gte", "quest_completed",
-    "has_debt_to", "no_debt_to",
+    "has_met", "faction_member", "skill_rank_gte", "quest_state",
+    "has_debt_to", "no_debt_to", "item_held", "vital_status",
 )
 
 # What `emit_plan`'s parser accepts from the model (TICKET-0108): the four
@@ -75,10 +79,24 @@ MODEL_REQUIREMENT_TYPES: tuple[str, ...] = ("knowledge", "relation_gte", "resour
 # The shape of each form, the three groups of the `*_requirement_shape`
 # CHECK (C-01): which column names its target, and which need a threshold.
 ENTITY_TARGET_TYPES: tuple[str, ...] = (
-    "relation_gte", "location_reachable", "has_met", "faction_member", "has_debt_to", "no_debt_to",
+    "relation_gte", "location_reachable", "has_met", "faction_member", "has_debt_to", "no_debt_to", "item_held",
 )
-KEY_TARGET_TYPES: tuple[str, ...] = ("knowledge", "resource", "skill_rank_gte", "quest_completed")
-THRESHOLD_TYPES: tuple[str, ...] = ("relation_gte", "resource", "skill_rank_gte")
+KEY_TARGET_TYPES: tuple[str, ...] = ("knowledge", "resource", "skill_rank_gte", "quest_state")
+THRESHOLD_TYPES: tuple[str, ...] = ("relation_gte", "resource", "skill_rank_gte", "item_held")
+# v2.20: a form with no target judges its subject alone; a form with a
+# value compares to one of its own closed set.
+NO_TARGET_TYPES: tuple[str, ...] = ("vital_status",)
+# `character.vital_status` has no CHECK: its values are the creator form's
+# (`cockpit/crud/entities.py`, the character fields' `vital_status` select).
+VITAL_STATUSES: tuple[str, ...] = ("alive", "dead", "missing", "unknown")
+# A quest's state is its agenda's (M1 of TICKET-0108); `open` is `active` or
+# `paused`, the player's « en cours ».
+QUEST_STATES: tuple[str, ...] = ("open", "completed", "failed", "abandoned")
+QUEST_STATE_AGENDA_STATUSES: dict[str, tuple[str, ...]] = {
+    "open": ("active", "paused"), "completed": ("completed",), "failed": ("failed",),
+    "abandoned": ("abandoned",),
+}
+FORM_VALUES: dict[str, tuple[str, ...]] = {"vital_status": VITAL_STATUSES, "quest_state": QUEST_STATES}
 
 
 @dataclass(frozen=True)
@@ -266,29 +284,59 @@ def _eval_skill_rank_gte(req: RequirementSpec, character: Character, db: Session
     )
 
 
-def _eval_quest_completed(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
-    """`target_key` is a quest offer id: met iff a quest the character took
-    from that offer has its agenda `completed` (M1: a quest's state is its
-    agenda's)."""
+def _eval_quest_state(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """`target_key` is a quest offer id, `value` one of `QUEST_STATES`: met
+    iff a quest the character took from that offer is in that state (M1: a
+    quest's state is its agenda's). A repeatable offer may have several:
+    one is enough."""
     del reachable_ids
+    statuses = QUEST_STATE_AGENDA_STATUSES.get(req.value or "", ())
     row = db.exec(
         select(Quest.id)
         .join(Agenda, Agenda.id == Quest.agenda_id)
         .where(
             Quest.character_id == character.id, Quest.offer_id == req.target_key,
-            Agenda.status == "completed",
+            Agenda.status.in_(statuses),
         )
     ).first()
     met = row is not None
     offer = db.get(QuestOffer, req.target_key) if req.target_key else None
     label = offer.title if offer is not None else str(req.target_key)
-    reason = f"quest {label!r} completed" if met else f"prerequisite not met — quest {label!r} not completed"
+    reason = (f"quest {label!r} is {req.value}" if met
+              else f"prerequisite not met — quest {label!r} is not {req.value}")
     return Verdict(
-        type=req.type, met=met, current=("completed" if met else "not completed"), required=req.target_key,
+        type=req.type, met=met, current=(req.value if met else f"not {req.value}"), required=req.target_key,
         reason=reason, required_label=label,
     )
 
 
+def _eval_item_held(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """`target_entity_id` is an item: met iff the character holds at least
+    `threshold` of it (`item_holding`, one row per item and holder; no row
+    reads 0)."""
+    del reachable_ids
+    held = db.exec(select(ItemHolding.quantity).where(
+        ItemHolding.item_id == req.target_entity_id, ItemHolding.holder_entity_id == character.id,
+    )).first() or 0
+    threshold = req.threshold or 0
+    met = held >= threshold
+    name = _entity_name(db, req.target_entity_id)
+    reason = (f"holds {held} {name}, meets requires >= {threshold}" if met
+              else f"prerequisite not met — holds {held} {name}, requires >= {threshold}")
+    return Verdict(type=req.type, met=met, current=held, required=threshold, reason=reason, required_label=name)
+
+
+def _eval_vital_status(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """No target: the subject's own `vital_status` equals `value`."""
+    del reachable_ids
+    met = character.vital_status == req.value
+    name = _entity_name(db, character.id)
+    reason = (f"{name} is {req.value}" if met
+              else f"prerequisite not met — {name} is {character.vital_status}, not {req.value}")
+    return Verdict(type=req.type, met=met, current=character.vital_status, required=req.value, reason=reason,
+                   required_label=name)
+
+
 def _open_debt(db: Session, debtor_id: str, creditor_id: Optional[str]) -> bool:
     return db.exec(select(Debt.id).where(
         Debt.debtor_entity_id == debtor_id, Debt.creditor_entity_id == creditor_id, Debt.status == "open",
@@ -329,9 +377,11 @@ _EVALUATORS: dict[str, Callable[[RequirementSpec, Character, Session, object], V
     "has_met": _eval_has_met,
     "faction_member": _eval_faction_member,
     "skill_rank_gte": _eval_skill_rank_gte,
-    "quest_completed": _eval_quest_completed,
+    "quest_state": _eval_quest_state,
     "has_debt_to": _eval_has_debt_to,
     "no_debt_to": _eval_no_debt_to,
+    "item_held": _eval_item_held,
+    "vital_status": _eval_vital_status,
 }
 
 
diff --git a/src/world_engine/condition_text.py b/src/world_engine/condition_text.py
index b610096..d92e03b 100644
--- a/src/world_engine/condition_text.py
+++ b/src/world_engine/condition_text.py
@@ -31,9 +31,18 @@ FORM_PHRASES_FR: dict[str, str] = {
     "has_met": "{who} a rencontré {target}",
     "faction_member": "{who} est membre de {target}",
     "skill_rank_gte": "{who} a « {target} » au rang {threshold} ou plus",
-    "quest_completed": "{who} a accompli la quête « {target} »",
+    "quest_state": "la quête « {target} » de {who} est {value}",
     "has_debt_to": "{who} a une dette envers {target}",
     "no_debt_to": "{who} n'a aucune dette envers {target}",
+    "item_held": "{who} possède au moins {threshold} × « {target} »",
+    "vital_status": "{who} est {value}",
+}
+
+# The French of a form's value (`condition_forms.FORM_VALUES`), one label per
+# value, kept equal to it by `conditions.py` CC.
+VALUE_LABELS_FR: dict[str, dict[str, str]] = {
+    "vital_status": {"alive": "en vie", "dead": "mort", "missing": "disparu", "unknown": "d'état inconnu"},
+    "quest_state": {"open": "en cours", "completed": "accomplie", "failed": "échouée", "abandoned": "abandonnée"},
 }
 
 CONNECTOR_HEADS_FR: dict[str, str] = {
@@ -61,7 +70,7 @@ def _target(db: Session, spec: RequirementSpec) -> str:
         return fact_text(db, fact) if fact is not None else str(spec.target_key)
     if spec.type == "skill_rank_gte":
         return skill_label(db, spec.target_key)
-    if spec.type == "quest_completed":
+    if spec.type == "quest_state":
         offer = db.get(QuestOffer, spec.target_key) if spec.target_key else None
         return offer.title if offer is not None else str(spec.target_key)
     return str(spec.target_key or "")
@@ -77,8 +86,8 @@ def leaf_text(db: Session, spec: RequirementSpec) -> str:
     phrase = FORM_PHRASES_FR.get(spec.type)
     if phrase is None:
         raise ValueError(f"condition_text: unknown requirement type {spec.type!r}")
-    text = phrase.format(who=_subject(db, spec), target=_target(db, spec),
-                         threshold=spec.threshold, value=spec.value)
+    value = VALUE_LABELS_FR.get(spec.type, {}).get(spec.value, spec.value)
+    text = phrase.format(who=_subject(db, spec), target=_target(db, spec), threshold=spec.threshold, value=value)
     return text[0].upper() + text[1:]
 
 
diff --git a/src/world_engine/conditions.py b/src/world_engine/conditions.py
index 1ffa4ce..31579ba 100644
--- a/src/world_engine/conditions.py
+++ b/src/world_engine/conditions.py
@@ -18,8 +18,9 @@ A verdict has three states (R1): `met`, `unmet`, `unknown`. The connectors
 follow Kleene's three-valued logic, so an `unknown` leaf can still be
 outweighed (`any` with a met sibling is met). A gate passes only on `met`.
 
-This module is pure apart from the evaluators it calls: it reads the canon
-through them and writes nothing. Storage is `writes/conditions.py`.
+This module writes nothing: it reads the canon through the evaluators and
+reads a stored tree back (`read_condition`). Its writer is
+`writes/conditions.py`.
 """
 
 from __future__ import annotations
@@ -27,10 +28,10 @@ from __future__ import annotations
 from dataclasses import dataclass
 from typing import Optional
 
-from sqlmodel import Session
+from sqlmodel import Session, select
 
 from .condition_forms import _EVALUATORS, RequirementSpec, Verdict, _day_reachable_ids
-from .models import Character, Entity
+from .models import Character, Condition, ConditionNode, Entity
 
 # The four connectors, then the leaf.
 CONNECTORS: tuple[str, ...] = ("all", "any", "not", "at_least")
@@ -146,6 +147,29 @@ def flat_leaves(node: Optional[ConditionTree]) -> Optional[tuple[RequirementSpec
     return None
 
 
+def map_leaves(tree: Optional[ConditionTree], fn) -> Optional[ConditionTree]:
+    """The same tree with `fn(spec) -> spec` applied to every leaf."""
+    if tree is None:
+        return None
+    if tree.op == "leaf":
+        return ConditionTree(op="leaf", leaf=fn(tree.leaf))
+    return ConditionTree(op=tree.op, n=tree.n, children=tuple(map_leaves(c, fn) for c in tree.children))
+
+
+def drop_leaves(tree: Optional[ConditionTree], drop) -> Optional[ConditionTree]:
+    """The tree without the leaves `drop(spec)` is true for. A connector left
+    with no child goes too; an `at_least` keeps `n` at most its remaining
+    children; no tree is left when the root goes."""
+    if tree is None:
+        return None
+    if tree.op == "leaf":
+        return None if drop(tree.leaf) else tree
+    children = tuple(kept for kept in (drop_leaves(c, drop) for c in tree.children) if kept is not None)
+    if not children:
+        return None
+    n = min(tree.n, len(children)) if tree.op == "at_least" else None
+    return ConditionTree(op=tree.op, n=n, children=children)
+
 # --- the dict form (what the API carries) --------------------------------------
 
 _LEAF_KEYS = ("type", "subject_role", "subject_entity_id", "target_entity_id", "target_key", "threshold", "value")
@@ -315,3 +339,47 @@ def _evaluate_leaf(spec: RequirementSpec, bindings: Bindings, db: Session, reach
         ids = reachable[character.id]
     verdict = evaluator(spec, character, db, ids)
     return VerdictNode(state="met" if verdict.met else "unmet", op="leaf", spec=spec, verdict=verdict)
+
+
+# --- reading a stored tree -----------------------------------------------------
+
+# The three owners a `condition` row may have (TICKET-0111, BRIEF-0111-C).
+OWNER_COLUMNS: tuple[str, ...] = ("quest_offer_id", "quest_offer_step_id", "agenda_step_id")
+
+
+def owner_of(owner: dict) -> tuple[str, str]:
+    given = [(column, value) for column, value in owner.items() if column in OWNER_COLUMNS and value]
+    if len(given) != 1 or set(owner) - set(OWNER_COLUMNS):
+        raise ValueError(f"a condition has exactly one owner among {OWNER_COLUMNS}, got {owner}")
+    return given[0]
+
+
+def stored_condition(db: Session, role: str, column: str, owner_id: str) -> Optional[Condition]:
+    return db.exec(select(Condition).where(getattr(Condition, column) == owner_id, Condition.role == role)).first()
+
+
+def read_condition(db: Session, *, role: str, **owner) -> Optional[ConditionTree]:
+    """The stored tree of one owner for one role, or None."""
+    column, owner_id = owner_of(owner)
+    condition = stored_condition(db, role, column, owner_id)
+    if condition is None:
+        return None
+    nodes = db.exec(select(ConditionNode).where(ConditionNode.condition_id == condition.id)).all()
+    children: dict[Optional[str], list[ConditionNode]] = {}
+    for node in nodes:
+        children.setdefault(node.parent_id, []).append(node)
+    roots = children.get(None, [])
+    if len(roots) != 1:
+        raise ValueError(f"condition {condition.id!r} has {len(roots)} roots")
+    return _build(roots[0], children)
+
+
+def _build(node: ConditionNode, children: dict) -> ConditionTree:
+    if node.op == "leaf":
+        return ConditionTree(op="leaf", leaf=RequirementSpec(
+            type=node.form, subject_role=node.subject_role, subject_entity_id=node.subject_entity_id,
+            target_entity_id=node.target_entity_id, target_key=node.target_key, threshold=node.threshold,
+            value=node.value,
+        ))
+    kids = sorted(children.get(node.id, []), key=lambda n: n.position)
+    return ConditionTree(op=node.op, n=node.n, children=tuple(_build(k, children) for k in kids))
diff --git a/src/world_engine/day_mutations.py b/src/world_engine/day_mutations.py
index dcab7fb..c842a2b 100644
--- a/src/world_engine/day_mutations.py
+++ b/src/world_engine/day_mutations.py
@@ -21,7 +21,7 @@ The delta contract (BRIEF-0075-e-amendment-1): it travels on the
 (`_apply_completion_effects`, `cockpit/mutations.py`, TICKET-0024/
 BRIEF-0024-c) — `relation_delta`, `ledger_transfer`, `role_change`, at most
 `_MAX_EFFECTS`. This module never invents an effect: there is no per-step
-reward column anywhere on `AgendaStep`/`AgendaStepRequirement` to compute
+reward column anywhere on `AgendaStep` or its condition to compute
 one from (a `resource`-type requirement carries no counterparty entity at
 all, so a `ledger_transfer` cannot even be well-formed from it; a
 `relation_gte`-type requirement carries no `relation_type` and no delta
@@ -46,8 +46,8 @@ documented no-op so the dispatch is a literal bijection with the constant
 `day_concordance.py`'s job).
 
 The armed rendezvous (I1, corrected by BRIEF-0075-e-amendment-1): not
-detected by inventing a marker. `AgendaStepRequirement` already has a
-`knowledge` requirement type (`_eval_knowledge`, `day_plan.py`) gating a
+detected by inventing a marker. A step's prerequisite already has a
+`knowledge` form (`_eval_knowledge`, `condition_forms.py`) gating a
 step on the player ALREADY holding a `Knowledge` row on its fact — meaning that
 row must already exist for the step to have been attemptable at all. This
 module treats successfully completing such a step as Nia's "a contact
@@ -83,8 +83,9 @@ from typing import Callable, Optional
 
 from sqlmodel import Session, select
 
+from .conditions import and_path_leaves, read_condition
 from .day_resolve import BLOCKED_BAND, StepOutcome, outcome_line
-from .models import AgendaStepRequirement, Character, Fact, PassPlay, ProposedMutation
+from .models import Character, Fact, PassPlay, ProposedMutation
 from .prose_render import fact_text
 
 EMITTED_MUTATION_TYPES: tuple[str, ...] = (
@@ -149,15 +150,16 @@ def _emit_knowledge_change(
 ) -> list[ProposedMutation]:
     """The rendezvous half (see module docstring): deepen every `knowledge`
     -type precondition this COMPLETED step already carried. Emits nothing
-    on `fail`, and nothing for a step with no `knowledge` requirement."""
+    on `fail`, and nothing for a step with no `knowledge` requirement.
+    Since TICKET-0111 (Q1): the `knowledge` leaves of the step's
+    prerequisite the step cannot be met without (reached through `all`),
+    and judged on the one who acts -- a fact someone else must know is not
+    his to deepen."""
     if _step_action(outcome) != "complete":
         return []
-    requirements = db.exec(
-        select(AgendaStepRequirement).where(
-            AgendaStepRequirement.step_id == outcome.agenda_step_id,
-            AgendaStepRequirement.type == "knowledge",
-        )
-    ).all()
+    prerequisite = read_condition(db, role="prerequisite", agenda_step_id=outcome.agenda_step_id)
+    requirements = [req for req in and_path_leaves(prerequisite)
+                    if req.type == "knowledge" and req.subject_role == "doer"]
     mutations: list[ProposedMutation] = []
     for req in requirements:
         label = _fact_label(req.target_key, db)
@@ -231,7 +233,7 @@ def _emit_new_knowledge(
     `knowledge` verdict, on the fact `v.required` names (TICKET-0097: the
     lead attaches the character to that very fact, which opens the gate
     once approved; the fact already carries its participants). Does NOT
-    re-query `AgendaStepRequirement`: `Verdict.type` (BRIEF-0078-a) already
+    re-read the step's condition: `Verdict.type` (BRIEF-0078-a) already
     makes the verdicts self-describing, and re-deriving the same fact from a
     second source would be a second authority for it."""
     if outcome.band != BLOCKED_BAND:
diff --git a/src/world_engine/day_plan.py b/src/world_engine/day_plan.py
index 3e7d498..f969023 100644
--- a/src/world_engine/day_plan.py
+++ b/src/world_engine/day_plan.py
@@ -18,24 +18,35 @@ PLAYER, never a position of an NPC.
 from __future__ import annotations
 
 import logging
-from dataclasses import dataclass, field, replace
+from dataclasses import dataclass, replace
 from typing import Optional
 
 from sqlmodel import Session, select
 
 from . import llm_parse, ollama_client
-from .condition_forms import MODEL_REQUIREMENT_TYPES, RequirementSpec, Verdict, evaluate_specs
+from .condition_forms import MODEL_REQUIREMENT_TYPES, RequirementSpec, Verdict
+from .conditions import (
+    Bindings,
+    ConditionTree,
+    VerdictNode,
+    all_of,
+    drop_leaves,
+    evaluate,
+    map_leaves,
+    read_condition,
+)
 from .fact_refs import CodedFacts, code_facts
 from .models import (
     BASE_SKILL_DOMAINS,
     SCHEDULE_PHASES,
     AgendaStep,
-    AgendaStepRequirement,
     Character,
     Entity,
     Fact,
     Knowledge,
     PromptTemplate,
+    Quest,
+    QuestOffer,
 )
 from .prompt_registry import effective_model
 from .prompt_store import current_prompt
@@ -64,20 +75,30 @@ DAY_PLAN_OPTIONS: dict = {"repeat_penalty": 1.1, "repeat_last_n": 128}
 
 @dataclass(frozen=True)
 class PlanStep:
+    """One step of a plan. Its `prerequisite` is a condition tree
+    (TICKET-0111, I1) -- `all` of the model's leaves for a day plan, any
+    tree for a quest step; None when nothing gates it."""
     objective: str
     cost: Optional[int]
     domain: Optional[str]
-    requirements: tuple[RequirementSpec, ...] = field(default_factory=tuple)
+    prerequisite: Optional[ConditionTree] = None
 
 
 @dataclass(frozen=True)
 class EvaluatedStep:
+    """A step and its judged prerequisite (None: nothing gates it). It is
+    `met` only when the verdict is (R1: `unknown` does not pass);
+    `verdicts` are the judged leaves, in order, for the day's narration."""
     step: PlanStep
-    verdicts: tuple[Verdict, ...]
+    verdict: Optional[VerdictNode] = None
 
     @property
     def met(self) -> bool:
-        return all(v.met for v in self.verdicts)
+        return self.verdict is None or self.verdict.met
+
+    @property
+    def verdicts(self) -> tuple[Verdict, ...]:
+        return () if self.verdict is None else self.verdict.leaf_verdicts()
 
 
 @dataclass(frozen=True)
@@ -88,10 +109,20 @@ class BudgetResult:
     first_excluded_index: Optional[int]
 
 
-def evaluate_requirements(step: PlanStep, character: Character, db: Session) -> list[Verdict]:
-    """Judge every requirement on `step` (`evaluate_specs` on its
-    requirements)."""
-    return evaluate_specs(step.requirements, character, db)
+def evaluate_requirements(step: PlanStep, bindings: Bindings, db: Session) -> Optional[VerdictNode]:
+    """Judge `step`'s prerequisite (`conditions.evaluate`); None when the
+    step has none."""
+    return evaluate(step.prerequisite, bindings, db)
+
+
+def plan_bindings(agenda_id: Optional[str], character: Character, db: Session) -> Bindings:
+    """What a step's roles name (P1): the character acts; when the agenda is
+    a quest's, its offer's giver and contact."""
+    quest = db.exec(select(Quest).where(Quest.agenda_id == agenda_id)).first() if agenda_id else None
+    offer = db.get(QuestOffer, quest.offer_id) if quest is not None else None
+    if offer is None:
+        return Bindings(doer=character)
+    return Bindings(doer=character, giver_id=offer.giver_entity_id, contact_id=offer.contact_entity_id)
 
 
 def evaluate_agenda_step(agenda_step: AgendaStep, character: Character, db: Session) -> EvaluatedStep:
@@ -99,24 +130,17 @@ def evaluate_agenda_step(agenda_step: AgendaStep, character: Character, db: Sess
     `character`'s current state (TICKET-0080, BRIEF-0080-b). Carved out of
     `day_resolve._load_evaluated_steps` unchanged so that the day chain's
     resolve walk and `_finalize_continue`'s refusal path share ONE
-    evaluation, rather than growing a second copy that can drift."""
-    requirement_rows = db.exec(
-        select(AgendaStepRequirement).where(AgendaStepRequirement.step_id == agenda_step.id)
-    ).all()
+    evaluation, rather than growing a second copy that can drift. Since
+    TICKET-0111 the prerequisite is the step's stored condition, its roles
+    bound by `plan_bindings`."""
     plan_step = PlanStep(
         objective=agenda_step.objective,
         cost=agenda_step.cost,
         domain=agenda_step.domain,
-        requirements=tuple(
-            RequirementSpec(
-                type=r.type, target_entity_id=r.target_entity_id,
-                target_key=r.target_key, threshold=r.threshold,
-            )
-            for r in requirement_rows
-        ),
+        prerequisite=read_condition(db, role="prerequisite", agenda_step_id=agenda_step.id),
     )
-    verdicts = tuple(evaluate_requirements(plan_step, character, db))
-    return EvaluatedStep(step=plan_step, verdicts=verdicts)
+    bindings = plan_bindings(agenda_step.agenda_id, character, db)
+    return EvaluatedStep(step=plan_step, verdict=evaluate_requirements(plan_step, bindings, db))
 
 
 def budget_cut(steps: list[EvaluatedStep], budget: int) -> BudgetResult:
@@ -194,19 +218,14 @@ def anchor_requirements(
     dropped: list[dict] = []
     anchored_steps: list[PlanStep] = []
     for step_index, step in enumerate(steps):
-        kept_requirements = []
-        for req in step.requirements:
-            if req.type == "knowledge" and req.target_key not in anchorable:
-                dropped.append({
-                    "step_index": step_index, "objective": step.objective, "target_key": req.target_key,
-                })
-                _log.info(
-                    "day_plan: dropped unanchored knowledge requirement %r on step %d",
-                    req.target_key, step_index,
-                )
-                continue
-            kept_requirements.append(req)
-        anchored_steps.append(replace(step, requirements=tuple(kept_requirements)))
+        def unanchored(req: RequirementSpec) -> bool:
+            if req.type != "knowledge" or req.target_key in anchorable:
+                return False
+            dropped.append({"step_index": step_index, "objective": step.objective, "target_key": req.target_key})
+            _log.info("day_plan: dropped unanchored knowledge requirement %r on step %d", req.target_key, step_index)
+            return True
+
+        anchored_steps.append(replace(step, prerequisite=drop_leaves(step.prerequisite, unanchored)))
     return anchored_steps, dropped
 
 
@@ -269,7 +288,7 @@ def _validate_step(raw: object) -> PlanStep:
     if not isinstance(raw_requires, list):
         raise llm_parse.LlmParseError("day_plan: step 'requires' must be a list")
     requirements = tuple(_validate_requirement(item) for item in raw_requires)
-    return PlanStep(objective=objective.strip(), cost=cost, domain=domain, requirements=requirements)
+    return PlanStep(objective=objective.strip(), cost=cost, domain=domain, prerequisite=all_of(requirements))
 
 
 def learnable_facts(character: Character, db: Session) -> CodedFacts:
@@ -305,15 +324,12 @@ def _resolve_knowledge_codes(steps: list[PlanStep], learnable: CodedFacts) -> li
     """Each `knowledge` requirement's code becomes its fact id; a code the
     list did not show is kept as emitted, for `anchor_requirements` to drop
     and report."""
-    resolved_steps = []
-    for step in steps:
-        requirements = tuple(
-            replace(req, target_key=learnable.resolve(req.target_key) or req.target_key)
-            if req.type == "knowledge" else req
-            for req in step.requirements
-        )
-        resolved_steps.append(replace(step, requirements=requirements))
-    return resolved_steps
+    def resolve(req: RequirementSpec) -> RequirementSpec:
+        if req.type != "knowledge":
+            return req
+        return replace(req, target_key=learnable.resolve(req.target_key) or req.target_key)
+
+    return [replace(step, prerequisite=map_leaves(step.prerequisite, resolve)) for step in steps]
 
 
 def emit_plan(
diff --git a/src/world_engine/day_resolve.py b/src/world_engine/day_resolve.py
index 29af960..cfe728a 100644
--- a/src/world_engine/day_resolve.py
+++ b/src/world_engine/day_resolve.py
@@ -4,7 +4,7 @@ corrected by BRIEF-0075-d-amendment-1, decision V1).
 
 Scope IN item 1 (step resolution): `resolve_steps` re-evaluates the
 character's active `Agenda` (the "plan" — every REMAINING `agenda_step`
-row plus its `agenda_step_requirement` rows) EVERY call, through the SAME
+row plus its prerequisite, a `condition` tree since TICKET-0111) EVERY call, through the SAME
 `evaluate_requirements`/`budget_cut` pair `day_plan.py` uses at emission
 time. This is deliberate: a REPLAY (Scope IN item 5) re-derives
 requirement verdicts against current world state and may re-roll a step
@@ -48,7 +48,7 @@ contains no `randint` call of its own (R1). The truncation logic itself
 or `randint` in its body (R2) — everything it needs (the band, already
 decided by `resolve_physical`) is precomputed by its impure caller.
 
-There is no "opposed NPC" concept on an `agenda_step`/`agenda_step_requirement`
+There is no "opposed NPC" concept on an `agenda_step` or its condition
 (unlike the live Play physical branch, `play_physical.py`) — a day-plan step
 names no opposing character. D2 (NPC opposition tier) therefore resolves to
 a constant: `npc_tier` is always 0 for a day step. This is not an
@@ -67,6 +67,8 @@ from typing import Optional
 from sqlmodel import Session, select
 
 from .condition_forms import Verdict as RequirementVerdict
+from .condition_text import leaf_text
+from .conditions import VerdictNode, leaves
 from .day_concordance import ConcordanceResult
 from .day_plan import (
     DAY_BUDGET_SLOTS,
@@ -217,7 +219,7 @@ def _roll_included_steps(
     rolled: list[_RolledStep] = []
     for agenda_step, evaluated in zip(ordered_steps, included):
         canon_ids = tuple(sorted({
-            r.target_entity_id for r in evaluated.step.requirements if r.target_entity_id
+            r.target_entity_id for r in leaves(evaluated.step.prerequisite) if r.target_entity_id
         }))
         if evaluated.step.domain is None:
             verdict = None
@@ -262,14 +264,19 @@ _BLOCKED_DETAIL_FR: dict[str, str] = {
     "resource": "il ne dispose pas des moyens nécessaires",
     "relation_gte": "ses appuis ne sont pas encore assez solides pour cela",
     "location_reachable": "l'endroit n'est pas accessible depuis là où il se trouve",
-    # TICKET-0108 (BRIEF-0108-A): the four creator-only forms.
+    # TICKET-0108 (BRIEF-0108-A): three of its four creator-only forms (the
+    # fourth, `quest_completed`, became `quest_state`, TICKET-0111).
     "has_met": "il n'a encore jamais rencontré {required}",
     "faction_member": "il n'appartient pas à {required}",
     "skill_rank_gte": "sa maîtrise de « {required} » ne suffit pas encore",
-    "quest_completed": "il doit d'abord mener à bien « {required} »",
     # TICKET-0110 (BRIEF-0110-A): the two debt forms.
     "has_debt_to": "il ne doit rien à {required}",
     "no_debt_to": "il a encore une dette envers {required}",
+    # TICKET-0111 (BRIEF-0111-C, S1): `quest_state` replaces `quest_completed`;
+    # the label names the quest and the state it must be in.
+    "quest_state": "la quête « {required} » n'en est pas là",
+    "item_held": "il n'a pas assez de « {required} »",
+    "vital_status": "{required} n'est pas dans l'état voulu",
 }
 
 
@@ -283,6 +290,35 @@ def requirement_detail_fr(verdict: RequirementVerdict) -> str:
     return template.format(required=getattr(verdict, "required_label", None) or verdict.required)
 
 
+def blocked_details_fr(verdict: Optional[VerdictNode], db: Session) -> list[str]:
+    """What a judged condition still lacks, in player-facing French
+    (TICKET-0111): an unmet leaf's `requirement_detail_fr`, an unknown
+    leaf's reason, and -- under a `not` -- a leaf that holds when it must
+    not. [] when the condition is met or absent."""
+    if verdict is None or verdict.met:
+        return []
+    details: list[str] = []
+    _blocked(verdict, db, False, details)
+    return details
+
+
+def _blocked(node: VerdictNode, db: Session, negated: bool, details: list[str]) -> None:
+    if node.op == "not":
+        _blocked(node.children[0], db, not negated, details)
+        return
+    if node.op != "leaf":
+        for child in node.children:
+            _blocked(child, db, negated, details)
+        return
+    if node.state == "unknown":
+        details.append(node.reason or "une condition ne peut pas être vérifiée")
+    elif node.state == "unmet" and not negated:
+        details.append(requirement_detail_fr(node.verdict))
+    elif node.state == "met" and negated:
+        text = leaf_text(db, node.spec)
+        details.append(f"il ne faut pas que : {text[0].lower()}{text[1:]}")
+
+
 def _append_blocked_step(
     ordered_steps: list[AgendaStep],
     evaluated_steps: list[EvaluatedStep],
@@ -312,7 +348,7 @@ def _append_blocked_step(
     agenda_step = ordered_steps[first_excluded]
     evaluated = evaluated_steps[first_excluded]
     canon_ids = tuple(sorted({
-        r.target_entity_id for r in evaluated.step.requirements if r.target_entity_id
+        r.target_entity_id for r in leaves(evaluated.step.prerequisite) if r.target_entity_id
     }))
     outcomes.append(StepOutcome(
         agenda_step_id=agenda_step.id,
diff --git a/src/world_engine/models/__init__.py b/src/world_engine/models/__init__.py
index 1eff21b..eeb1f08 100644
--- a/src/world_engine/models/__init__.py
+++ b/src/world_engine/models/__init__.py
@@ -29,7 +29,7 @@ Layout, by stratum:
                         friends, TICKET-0051); telemetry, never canon —
                         absent from canon_write_policy.txt's [CANON_TABLES].
     quests.py        — quest offers and accepted quests (QuestOffer,
-                        QuestOfferStep, QuestOfferRequirement, Quest;
+                        QuestOfferStep, Quest;
                         TICKET-0108, schema v2.17), their terms and a
                         world's quest economy (QuestOfferTerm, QuestTerm,
                         QuestEconomy; TICKET-0109, v2.18), and debts
@@ -86,7 +86,15 @@ from .canon_faction import (
     FactionRole,
 )
 from .canon_knowledge import Fact, FactDefault, FactParticipant, Knowledge, Relation
-from .config import AgendaStep, AgendaStepRequirement, ConversationWindowConfig, SkillRank
+from .config import (
+    CONDITION_OPS,
+    CONDITION_ROLES,
+    AgendaStep,
+    Condition,
+    ConditionNode,
+    ConversationWindowConfig,
+    SkillRank,
+)
 from .schedule import SCHEDULE_PHASES, NpcSchedule
 from .ephemeral import (
     ENCOUNTER_SOURCES,
@@ -141,7 +149,6 @@ from .quests import (
     Quest,
     QuestEconomy,
     QuestOffer,
-    QuestOfferRequirement,
     QuestOfferStep,
     QuestOfferTerm,
     QuestTerm,
@@ -211,11 +218,13 @@ __all__ = [
     "UnresolvedMention",
     "Agenda",
     "AgendaStep",
-    "AgendaStepRequirement",
+    "Condition",
+    "ConditionNode",
+    "CONDITION_OPS",
+    "CONDITION_ROLES",
     "QUEST_OFFER_STATUSES",
     "Quest",
     "QuestOffer",
-    "QuestOfferRequirement",
     "QuestOfferStep",
     "QUEST_TERM_CURRENCIES",
     "QUEST_TERM_DIRECTIONS",
diff --git a/src/world_engine/models/canon.py b/src/world_engine/models/canon.py
index 9bd65ec..46fed67 100644
--- a/src/world_engine/models/canon.py
+++ b/src/world_engine/models/canon.py
@@ -815,8 +815,8 @@ class Agenda(SQLModel, table=True):
     )
 
 
-# `AgendaStep` and `agenda_step_requirement` (schema v1.94, TICKET-0075,
-# BRIEF-0075-b) live in `models/config.py` — see the header comment above.
+# `AgendaStep` (schema v1.94, TICKET-0075, BRIEF-0075-b) and its `condition`
+# (v2.20, TICKET-0111) live in `models/config.py` — see the header comment above.
 
 
 # -----------------------------------------------------------------------------
diff --git a/src/world_engine/models/config.py b/src/world_engine/models/config.py
index f6d3547..6bdd127 100644
--- a/src/world_engine/models/config.py
+++ b/src/world_engine/models/config.py
@@ -1,5 +1,6 @@
 """Conversation-window curated config (TICKET-0050, BRIEF-0050-a); `AgendaStep`
-and `agenda_step_requirement` (TICKET-0075, BRIEF-0075-b).
+(TICKET-0075, BRIEF-0075-b); `condition` and `condition_node` (TICKET-0111,
+BRIEF-0111-C), which replaced `agenda_step_requirement`.
 
 Split out of `canon.py` (974/1000 lines at TICKET-0050, again at exactly
 1000/1000 by TICKET-0075 — no headroom for a new table,
@@ -7,8 +8,8 @@ Split out of `canon.py` (974/1000 lines at TICKET-0050, again at exactly
 to a different stratum: `AgendaStep` is the same `agenda`/`agenda_step`
 family as `Agenda` (still in `canon.py`) — only its FILE moved, not its
 identity, and every existing `from ..models import AgendaStep` import is
-unaffected (resolved through `models/__init__.py`). `agenda_step_requirement`
-is canon curated-config, same family as `location_type_catalog` / `world_law`
+unaffected (resolved through `models/__init__.py`). `condition` / `condition_node`
+are canon curated-config, same family as `location_type_catalog` / `world_law`
 (metadata-config category, no `change_history`). `skill_rank` (TICKET-0106,
 BRIEF-0106-A) is the same curated-config family, placed here for the same
 module budget.
@@ -104,59 +105,90 @@ class AgendaStep(SQLModel, table=True):
 
 
 # -----------------------------------------------------------------------------
-# agenda_step_requirement  (day-plan precondition gate, schema v1.94,
-# TICKET-0075, BRIEF-0075-b). `goal_prerequisite` shape precedent (same
-# id/world_id/type/target_entity_id/threshold spine), widened to a closed
-# vocabulary and a `target_key` column for the forms that gate on a string
-# (knowledge fact id since TICKET-0097, resource tag, skill key, quest offer
-# id) rather than an entity. Eight forms since v2.17 (TICKET-0108,
-# BRIEF-0108-A): the four the day-plan model may emit, plus `has_met`,
-# `faction_member`, `skill_rank_gte` and `quest_completed`, authored by the
-# creator only (`condition_forms.MODEL_REQUIREMENT_TYPES`). Ten since v2.19
-# (TICKET-0110, BRIEF-0110-A, G1): `has_debt_to` and `no_debt_to`, an open
-# debt toward the target entity or none, creator only too.
+# condition / condition_node  (the condition language, schema v2.20,
+# TICKET-0111, BRIEF-0111-C -- decisions A1, I1, O-a, M1 and P1). They replace
+# `agenda_step_requirement` and `quest_offer_requirement` (v1.94 / v2.17).
 #
-# The per-type shape CHECK is the structural guarantee that an ill-formed row
-# cannot exist; its three groups are `condition_forms.ENTITY_TARGET_TYPES`,
-# `KEY_TARGET_TYPES` and `THRESHOLD_TYPES`. `quest_offer_requirement`
-# (models/quests.py) carries the same two CHECK texts, byte for byte
-# (`quests.py` check, QA1). Curated plan metadata, same family as
-# `npc_schedule` — no `change_history`.
+# A `condition` is ONE tree, owned by exactly one of an offer (its
+# eligibility), an offer step or an agenda step (its prerequisite or, M1, its
+# completion -- shown, never acting). At most one condition per owner and
+# role. Its nodes are rows (O-a: never JSON, the UI reads them): a connector
+# (`all`, `any`, `not`, `at_least` with `n`) or a leaf carrying one form of
+# `condition_forms.REQUIREMENT_TYPES` and its arguments; `parent_id` and
+# `position` give the tree its shape, the root has no parent.
 #
-# THE POSITIONAL WALL: `location_reachable`'s target lives HERE, on the
-# requirement row, never on `agenda_step` — a requirement states "the player
-# must be able to reach L", a precondition on the player, never a position of
-# an NPC. See BRIEF-0074-a-amendment-1.
+# The form vocabulary is a code-plane property (the `entity_trait.trait_key`
+# precedent): no CHECK lists the forms -- a new form is code, never a table
+# rebuild. `writes.conditions.write_condition` is the one writer and refuses
+# an unknown form, an ill-shaped tree or a target outside the world, before
+# any row; `conditions.py` (CC) holds it to that. What a CHECK can say without
+# naming a form, it says: a node is a connector or a leaf; a leaf names
+# exactly one subject; a connector carries no argument; `at_least` has n >= 1.
+# Curated plan metadata, the requirement rows' family: no `change_history`
+# (an offer snapshots itself; a save replaces its conditions whole).
 # -----------------------------------------------------------------------------
-class AgendaStepRequirement(SQLModel, table=True):
-    __tablename__ = "agenda_step_requirement"
+CONDITION_ROLES: tuple[str, ...] = ("eligibility", "prerequisite", "completion")
+CONDITION_OPS: tuple[str, ...] = ("all", "any", "not", "at_least", "leaf")
+
+
+class Condition(SQLModel, table=True):
+    __tablename__ = "condition"
+    __table_args__ = (
+        CheckConstraint("role IN ('eligibility','prerequisite','completion')", name="ck_condition_role"),
+        CheckConstraint(
+            "(quest_offer_id IS NOT NULL) + (quest_offer_step_id IS NOT NULL) + (agenda_step_id IS NOT NULL) = 1",
+            name="ck_condition_owner",
+        ),
+        CheckConstraint("(quest_offer_id IS NOT NULL) = (role = 'eligibility')", name="ck_condition_owner_role"),
+        Index("idx_condition_offer", "quest_offer_id", "role", unique=True),
+        Index("idx_condition_offer_step", "quest_offer_step_id", "role", unique=True),
+        Index("idx_condition_agenda_step", "agenda_step_id", "role", unique=True),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    role: str
+    quest_offer_id: Optional[str] = Field(default=None, foreign_key="quest_offer.id")
+    quest_offer_step_id: Optional[str] = Field(default=None, foreign_key="quest_offer_step.id")
+    agenda_step_id: Optional[str] = Field(default=None, foreign_key="agenda_step.id")
+    created_at: datetime = _created_ts()
+
+
+class ConditionNode(SQLModel, table=True):
+    __tablename__ = "condition_node"
     __table_args__ = (
+        CheckConstraint("op IN ('all','any','not','at_least','leaf')", name="ck_condition_node_op"),
+        CheckConstraint("(op = 'leaf') = (form IS NOT NULL)", name="ck_condition_node_leaf"),
         CheckConstraint(
-            "type IN ('knowledge','relation_gte','resource','location_reachable',"
-            "'has_met','faction_member','skill_rank_gte','quest_completed','has_debt_to','no_debt_to')",
-            name="ck_agenda_step_requirement_type",
+            "op = 'leaf' OR (subject_role IS NULL AND subject_entity_id IS NULL AND target_entity_id IS NULL "
+            "AND target_key IS NULL AND threshold IS NULL AND value IS NULL)",
+            name="ck_condition_node_connector",
         ),
         CheckConstraint(
-            "(type NOT IN ('relation_gte','location_reachable','has_met','faction_member','has_debt_to','no_debt_to') "
-            "OR target_entity_id IS NOT NULL) "
-            "AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') "
-            "OR target_key IS NOT NULL) "
-            "AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)",
-            name="ck_agenda_step_requirement_shape",
+            "op <> 'leaf' OR ((subject_role IS NULL) <> (subject_entity_id IS NULL))",
+            name="ck_condition_node_subject",
         ),
-        Index(
-            "idx_agenda_step_requirement_unique", "step_id", "type",
-            "target_entity_id", "target_key", unique=True,
+        CheckConstraint(
+            "subject_role IS NULL OR subject_role IN ('doer','giver','contact')", name="ck_condition_node_role",
         ),
+        CheckConstraint("(op = 'at_least') = (n IS NOT NULL) AND (n IS NULL OR n >= 1)", name="ck_condition_node_n"),
+        Index("idx_condition_node_condition", "condition_id", "parent_id", "position"),
     )
 
     id: str = Field(default_factory=_uuid, primary_key=True)
     world_id: str = Field(foreign_key="world.id", nullable=False)
-    step_id: str = Field(foreign_key="agenda_step.id", nullable=False)
-    type: str
+    condition_id: str = Field(foreign_key="condition.id", nullable=False)
+    parent_id: Optional[str] = Field(default=None, foreign_key="condition_node.id")
+    position: int = Field(default=0, sa_column_kwargs={"server_default": text("0")})
+    op: str
+    n: Optional[int] = None
+    form: Optional[str] = None
+    subject_role: Optional[str] = None
+    subject_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
     target_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
     target_key: Optional[str] = None
     threshold: Optional[int] = None
+    value: Optional[str] = None
 
 
 # -----------------------------------------------------------------------------
diff --git a/src/world_engine/models/quests.py b/src/world_engine/models/quests.py
index c29354f..bccaa39 100644
--- a/src/world_engine/models/quests.py
+++ b/src/world_engine/models/quests.py
@@ -8,9 +8,9 @@ steps and their requirements into a new `agenda` of the player, born
 `paused` (A1); `quest` links that agenda to the offer it came from. A
 quest's state is its agenda's status, never a second column (M1).
 
-The requirement vocabulary is `agenda_step_requirement`'s, not a second
-language (B1): `quest_offer_requirement` carries the same two CHECK texts,
-byte for byte, and `condition_forms.evaluate_specs` judges both.
+The requirement vocabulary is the condition language's, not a second one
+(B1, then I1 of TICKET-0111): an offer's eligibility and each step's
+conditions are `condition` trees (models/config.py), like an agenda step's.
 
 Offers are curated content: their steps and requirements are replaced
 whole when the creator saves an offer (the `npc_price` full-replace
@@ -85,39 +85,6 @@ class QuestOfferStep(SQLModel, table=True):
     domain: Optional[str] = None  # a base skill domain, or NULL: no roll
 
 
-# -----------------------------------------------------------------------------
-# quest_offer_requirement  (eligibility when step_id is NULL; else a step's
-# requirement). Same vocabulary and CHECK texts as agenda_step_requirement.
-# -----------------------------------------------------------------------------
-class QuestOfferRequirement(SQLModel, table=True):
-    __tablename__ = "quest_offer_requirement"
-    __table_args__ = (
-        CheckConstraint(
-            "type IN ('knowledge','relation_gte','resource','location_reachable',"
-            "'has_met','faction_member','skill_rank_gte','quest_completed','has_debt_to','no_debt_to')",
-            name="ck_quest_offer_requirement_type",
-        ),
-        CheckConstraint(
-            "(type NOT IN ('relation_gte','location_reachable','has_met','faction_member','has_debt_to','no_debt_to') "
-            "OR target_entity_id IS NOT NULL) "
-            "AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') "
-            "OR target_key IS NOT NULL) "
-            "AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)",
-            name="ck_quest_offer_requirement_shape",
-        ),
-        Index("idx_quest_offer_requirement_offer", "offer_id"),
-    )
-
-    id: str = Field(default_factory=_uuid, primary_key=True)
-    world_id: str = Field(foreign_key="world.id", nullable=False)
-    offer_id: str = Field(foreign_key="quest_offer.id", nullable=False)
-    step_id: Optional[str] = Field(default=None, foreign_key="quest_offer_step.id")
-    type: str
-    target_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
-    target_key: Optional[str] = None
-    threshold: Optional[int] = None
-
-
 # -----------------------------------------------------------------------------
 # quest  (an offer a character accepted: the link to its agenda). The
 # quest's state is `agenda.status` (M1); `settled_at` (v2.18, TICKET-0109,
diff --git a/src/world_engine/quest_reads.py b/src/world_engine/quest_reads.py
index 8b4fd0b..22a666d 100644
--- a/src/world_engine/quest_reads.py
+++ b/src/world_engine/quest_reads.py
@@ -17,7 +17,10 @@ from typing import Optional
 
 from sqlmodel import Session, select
 
-from .day_resolve import requirement_detail_fr
+from .condition_forms import FORM_VALUES
+from .condition_text import VALUE_LABELS_FR
+from .conditions import flat_leaves, read_condition
+from .day_resolve import blocked_details_fr
 from .day_plan import evaluate_agenda_step
 from .models import (
     BASE_SKILL_DOMAINS,
@@ -37,7 +40,7 @@ from .prose_render import fact_texts
 from .quest_value import offer_value, value_dict, world_rates
 from .quest_wording import term_dict, term_line
 from .writes.quest_terms import FACT_REWARD_LEVELS, offer_terms, quest_terms
-from .writes.quests import QUEST_GIVER_TYPES, acceptance_refusal, offer_requirements
+from .writes.quests import QUEST_GIVER_TYPES, acceptance_refusal
 
 # M1: the agenda's status, as the player reads it.
 QUEST_STATE_LABELS: dict[str, str] = {
@@ -51,7 +54,18 @@ QUEST_STATE_LABELS: dict[str, str] = {
 
 def _requirement_dict(req) -> dict:
     return {"type": req.type, "target_entity_id": req.target_entity_id, "target_key": req.target_key,
-            "threshold": req.threshold}
+            "threshold": req.threshold, "subject_role": req.subject_role,
+            "subject_entity_id": req.subject_entity_id, "value": req.value}
+
+
+def _requirement_list(tree) -> list[dict]:
+    """A flat condition as the editor's list (T1). Until the surfaces read
+    trees (BRIEF-0111-D), every stored condition is flat: nothing else can
+    be written."""
+    flat = flat_leaves(tree)
+    if flat is None:
+        raise ValueError("a nested condition cannot be read as a list")
+    return [_requirement_dict(r) for r in flat]
 
 
 def _name(db: Session, entity_id: Optional[str]) -> Optional[str]:
@@ -70,10 +84,10 @@ def offer_dict(offer: QuestOffer, db: Session) -> dict:
         # TICKET-0110 (X1): a faction giver's contact.
         "contact_entity_id": offer.contact_entity_id, "contact_name": _name(db, offer.contact_entity_id),
         "title": offer.title, "summary": offer.summary, "repeatable": offer.repeatable, "status": offer.status,
-        "eligibility": [_requirement_dict(r) for r in offer_requirements(db, offer.id, None)],
+        "eligibility": _requirement_list(read_condition(db, role="eligibility", quest_offer_id=offer.id)),
         "steps": [{
             "objective": step.objective, "cost": step.cost, "domain": step.domain,
-            "requirements": [_requirement_dict(r) for r in offer_requirements(db, offer.id, step.id)],
+            "requirements": _requirement_list(read_condition(db, role="prerequisite", quest_offer_step_id=step.id)),
         } for step in steps],
         # TICKET-0109 (B1, C1): the costs and rewards, and their indicative value.
         "terms": [term_dict(db, t, offer.giver_entity_id) for t in terms],
@@ -109,7 +123,8 @@ def editor_choices(world_id: str, db: Session) -> dict:
     """What the offer editor's pickers list: givers, characters, locations,
     factions, facts (their text), skills (base domains, then definitions),
     offers; items with their value, the fact reward levels and the world's
-    rates (TICKET-0109); each faction's members (TICKET-0110, X1)."""
+    rates (TICKET-0109); each faction's members (TICKET-0110, X1); the
+    values a form compares to (TICKET-0111)."""
     facts = db.exec(select(Fact).where(Fact.world_id == world_id)).all()
     definitions = db.exec(select(SkillDefinition).where(SkillDefinition.world_id == world_id)).all()
     characters = _named(db, world_id, "character")
@@ -129,6 +144,9 @@ def editor_choices(world_id: str, db: Session) -> dict:
         "fact_levels": list(FACT_REWARD_LEVELS),
         "rates": world_rates(db, world_id),
         "members": faction_members(world_id, db),
+        # TICKET-0111 (S1): the values a form compares to, in French.
+        "form_values": {form: [{"value": value, "label": VALUE_LABELS_FR[form][value]} for value in values]
+                        for form, values in FORM_VALUES.items()},
     }
 
 
@@ -148,7 +166,7 @@ def _steps_view(agenda: Agenda, character: Character, db: Session) -> list[dict]
         blocked: list[str] = []
         if step.status == "active":
             evaluated = evaluate_agenda_step(step, character, db)
-            blocked = [requirement_detail_fr(v) for v in evaluated.verdicts if not v.met]
+            blocked = blocked_details_fr(evaluated.verdict, db)
         view.append({"order": step.step_order, "objective": step.objective, "status": step.status,
                      "outcome": step.outcome, "blocked": blocked})
     return view
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index b5b206c..373d733 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.19"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.20"
diff --git a/src/world_engine/writes/__init__.py b/src/world_engine/writes/__init__.py
index 7b72934..8d40198 100644
--- a/src/world_engine/writes/__init__.py
+++ b/src/world_engine/writes/__init__.py
@@ -52,10 +52,13 @@ Layout, by canon domain:
                           `clean_terms`, `write_offer_terms`,
                           `copy_terms_to_quest`, `upsert_quest_economy`
                           (TICKET-0109, BRIEF-0109-B).
-    quests.py           — `quest_offer`/`quest_offer_step`/
-                          `quest_offer_requirement`/`quest`:
+    quests.py           — `quest_offer`/`quest_offer_step`/`quest`:
                           `write_quest_offer`, `accept_quest`,
                           `abandon_quest` (TICKET-0108, BRIEF-0108-B).
+    conditions.py       — `condition`/`condition_node`: `clean_leaf`,
+                          `clean_condition`, `write_condition`,
+                          `delete_offer_conditions` (TICKET-0111,
+                          BRIEF-0111-C).
     worlds.py           — `delete_world_cascade` (the sole delete-side
                           helper, wildcard-allowed in canon_write_policy.txt).
 
@@ -151,9 +154,10 @@ from .quests import (
     abandon_refusal,
     accept_quest,
     acceptance_refusal,
-    offer_requirements,
+    offer_bindings,
     write_quest_offer,
 )
+from .conditions import clean_condition, clean_leaf, delete_offer_conditions, write_condition
 from .pipeline import (
     BATCH_RESOLVED_STATUS,
     BATCH_STATUSES,
diff --git a/src/world_engine/writes/conditions.py b/src/world_engine/writes/conditions.py
new file mode 100644
index 0000000..43d804f
--- /dev/null
+++ b/src/world_engine/writes/conditions.py
@@ -0,0 +1,221 @@
+"""The condition writer and reader (TICKET-0111, BRIEF-0111-C, decisions O-a
+and I1): one `condition` row per owner and role, its tree as
+`condition_node` rows.
+
+- `clean_leaf(...)`        : one leaf against its form -- the form is known,
+  its subject is a role or a character of the world, its target exists in
+  the world and is of the right kind, its threshold and value are in
+  range. Moved here from `goals_agendas._clean_requirement` (TICKET-0108,
+  C-01) and widened to subjects and values.
+- `clean_condition(...)`   : a whole tree, shape (`conditions.check_shape`)
+  then every leaf; returns the tree as it will be stored.
+- `write_condition(...)`   : replace one owner's condition for one role
+  whole (no tree: none is kept), after cleaning it. Its reader is
+  `conditions.read_condition`.
+- `delete_offer_conditions(...)` : every condition of an offer and of its
+  steps, before `write_quest_offer` replaces them.
+
+The form vocabulary is a code-plane property (no CHECK names a form): this
+module is the one writer of both tables (`single_canon_write.py`), and it
+refuses before any row. None of these functions commits.
+"""
+
+from __future__ import annotations
+
+from typing import Optional
+
+from sqlalchemy import text
+from sqlmodel import Session
+
+from ..condition_forms import (
+    ENTITY_TARGET_TYPES,
+    FORM_VALUES,
+    NO_TARGET_TYPES,
+    REQUIREMENT_TYPES,
+    THRESHOLD_TYPES,
+    RequirementSpec,
+)
+from ..conditions import SUBJECT_ROLES, ConditionTree, check_shape, owner_of, stored_condition
+from ..models import (
+    BASE_SKILL_DOMAINS,
+    CONDITION_ROLES,
+    Condition,
+    ConditionNode,
+    Entity,
+    Fact,
+    QuestOffer,
+    SkillDefinition,
+)
+
+# The entity type each entity-targeted form must name (TICKET-0108, C-01);
+# `None` accepts any entity of the world -- the two model-emitted forms keep
+# the check they always had, so a day plan is refused for nothing new.
+_TARGET_ENTITY_TYPE: dict[str, Optional[tuple[str, ...]]] = {
+    "relation_gte": None, "location_reachable": None, "has_met": None, "faction_member": ("faction",),
+    # TICKET-0110 (G1): a debt's creditor, a character or a faction (J1).
+    "has_debt_to": ("character", "faction"), "no_debt_to": ("character", "faction"),
+    # TICKET-0111 (S1): an item held in quantity (`item_holding`).
+    "item_held": ("item",),
+}
+
+
+def _clean_target_key(db: Session, world_id: str, req: RequirementSpec) -> Optional[str]:
+    """The error for a key-targeted form whose key names nothing in
+    `world_id`, or None. `resource`'s key is a label (one currency per
+    world), never resolved."""
+    if req.type == "knowledge":
+        fact = db.get(Fact, req.target_key)
+        return None if fact is not None and fact.world_id == world_id else f"unknown fact {req.target_key!r}"
+    if req.type == "skill_rank_gte":
+        if req.target_key in BASE_SKILL_DOMAINS:
+            return None
+        definition = db.get(SkillDefinition, req.target_key)
+        ok = definition is not None and definition.world_id == world_id
+        return None if ok else f"unknown skill {req.target_key!r}"
+    if req.type == "quest_state":
+        offer = db.get(QuestOffer, req.target_key)
+        return None if offer is not None and offer.world_id == world_id else f"unknown quest offer {req.target_key!r}"
+    return None
+
+
+def _clean_subject(db: Session, world_id: str, where: str, req: RequirementSpec) -> None:
+    if (req.subject_role is None) == (req.subject_entity_id is None):
+        raise ValueError(f"{where}requirement type {req.type!r} names exactly one subject: a role or an entity")
+    if req.subject_role is not None:
+        if req.subject_role not in SUBJECT_ROLES:
+            raise ValueError(f"{where}unknown subject role {req.subject_role!r}")
+        return
+    subject = db.get(Entity, req.subject_entity_id)
+    if subject is None or subject.world_id != world_id or subject.type != "character":
+        raise ValueError(f"{where}subject {req.subject_entity_id!r} is not a character of this world")
+
+
+def _clean_target(db: Session, world_id: str, where: str, req: RequirementSpec) -> tuple[Optional[str], Optional[str]]:
+    if req.type in NO_TARGET_TYPES:
+        if req.target_entity_id or req.target_key:
+            raise ValueError(f"{where}requirement type {req.type!r} judges its subject alone and takes no target")
+        return None, None
+    if req.type in ENTITY_TARGET_TYPES:
+        if not req.target_entity_id:
+            raise ValueError(f"{where}requirement type {req.type!r} needs a target_entity_id")
+        target = db.get(Entity, req.target_entity_id)
+        wanted = _TARGET_ENTITY_TYPE[req.type]
+        if target is None or target.world_id != world_id or (wanted is not None and target.type not in wanted):
+            raise ValueError(f"{where}unknown target entity {req.target_entity_id!r}")
+        return req.target_entity_id, None
+    if not req.target_key:
+        raise ValueError(f"{where}requirement type {req.type!r} needs a target_key")
+    error = _clean_target_key(db, world_id, req)
+    if error is not None:
+        raise ValueError(f"{where}requirement type {req.type!r}: {error}")
+    return None, req.target_key
+
+
+def _clean_threshold(where: str, req: RequirementSpec) -> Optional[int]:
+    if req.type not in THRESHOLD_TYPES:
+        return None
+    threshold, top = req.threshold, (5 if req.type == "skill_rank_gte" else None)
+    if (not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 1
+            or (top is not None and threshold > top)):
+        raise ValueError(
+            f"{where}requirement type {req.type!r} needs a positive integer threshold"
+            + (f" of at most {top}" if top is not None else "")
+        )
+    return threshold
+
+
+def _clean_value(where: str, req: RequirementSpec) -> Optional[str]:
+    allowed = FORM_VALUES.get(req.type)
+    if allowed is None:
+        return None
+    if req.value not in allowed:
+        raise ValueError(f"{where}requirement type {req.type!r} needs a value among {allowed}, got {req.value!r}")
+    return req.value
+
+
+def clean_leaf(db: Session, world_id: str, req: RequirementSpec, where: str = "") -> RequirementSpec:
+    """One leaf as it will be stored: the arguments its form uses, nothing
+    else. `where` prefixes every error (« write_day_plan: step 2 »).
+    Raises `ValueError` on any violation."""
+    if req.type not in REQUIREMENT_TYPES:
+        raise ValueError(f"{where}unknown requirement type {req.type!r}")
+    _clean_subject(db, world_id, where, req)
+    target_entity_id, target_key = _clean_target(db, world_id, where, req)
+    return RequirementSpec(
+        type=req.type, subject_role=req.subject_role, subject_entity_id=req.subject_entity_id,
+        target_entity_id=target_entity_id, target_key=target_key,
+        threshold=_clean_threshold(where, req), value=_clean_value(where, req),
+    )
+
+
+def clean_condition(
+    db: Session, world_id: str, tree: Optional[ConditionTree], where: str = "",
+) -> Optional[ConditionTree]:
+    """A whole tree, shape first then every leaf, before any write. None is
+    no condition. Raises `ValueError` (a `ConditionShapeError` is one)."""
+    if tree is None:
+        return None
+    try:
+        check_shape(tree)
+    except ValueError as exc:
+        raise ValueError(f"{where}{exc}") from exc
+    return _clean_tree(db, world_id, tree, where)
+
+
+def _clean_tree(db: Session, world_id: str, tree: ConditionTree, where: str) -> ConditionTree:
+    if tree.op == "leaf":
+        return ConditionTree(op="leaf", leaf=clean_leaf(db, world_id, tree.leaf, where))
+    return ConditionTree(op=tree.op, n=tree.n, children=tuple(_clean_tree(db, world_id, c, where) for c in tree.children))
+
+
+def write_condition(db: Session, *, world_id: str, role: str, tree: Optional[ConditionTree], **owner) -> Optional[Condition]:
+    """Replace the condition `role` of one owner (`quest_offer_id=`,
+    `quest_offer_step_id=` or `agenda_step_id=`) whole: the tree is cleaned,
+    the previous condition and its nodes removed, the new one written. No
+    tree: none is kept. Returns the new `condition` row, or None."""
+    column, owner_id = owner_of(owner)
+    if role not in CONDITION_ROLES or (column == "quest_offer_id") != (role == "eligibility"):
+        raise ValueError(f"a {column} owner cannot hold a {role!r} condition")
+    clean = clean_condition(db, world_id, tree)
+    previous = stored_condition(db, role, column, owner_id)
+    if previous is not None:
+        db.execute(text("DELETE FROM condition_node WHERE condition_id = :cid"), {"cid": previous.id})
+        db.execute(text("DELETE FROM condition WHERE id = :cid"), {"cid": previous.id})
+        db.expunge(previous)
+    if clean is None:
+        return None
+    condition = Condition(world_id=world_id, role=role, **{column: owner_id})
+    db.add(condition)
+    db.flush()
+    _write_node(db, world_id, condition.id, clean, None, 0)
+    return condition
+
+
+def _write_node(db: Session, world_id: str, condition_id: str, tree: ConditionTree,
+                parent_id: Optional[str], position: int) -> None:
+    spec = tree.leaf
+    row = ConditionNode(
+        world_id=world_id, condition_id=condition_id, parent_id=parent_id, position=position, op=tree.op,
+        n=tree.n if tree.op == "at_least" else None,
+        form=spec.type if spec else None,
+        subject_role=spec.subject_role if spec else None,
+        subject_entity_id=spec.subject_entity_id if spec else None,
+        target_entity_id=spec.target_entity_id if spec else None,
+        target_key=spec.target_key if spec else None,
+        threshold=spec.threshold if spec else None,
+        value=spec.value if spec else None,
+    )
+    db.add(row)
+    db.flush()
+    for index, child in enumerate(tree.children):
+        _write_node(db, world_id, condition_id, child, row.id, index)
+
+
+def delete_offer_conditions(db: Session, offer_id: str) -> None:
+    """Every condition of an offer -- its eligibility and its steps' -- with
+    their nodes: `write_quest_offer` replaces them whole (its full-replace
+    shape, TICKET-0108)."""
+    owned = ("SELECT id FROM condition WHERE quest_offer_id = :oid OR quest_offer_step_id IN "
+             "(SELECT id FROM quest_offer_step WHERE offer_id = :oid)")
+    db.execute(text(f"DELETE FROM condition_node WHERE condition_id IN ({owned})"), {"oid": offer_id})
+    db.execute(text(f"DELETE FROM condition WHERE id IN ({owned})"), {"oid": offer_id})
diff --git a/src/world_engine/writes/goals_agendas.py b/src/world_engine/writes/goals_agendas.py
index 231584e..e660d35 100644
--- a/src/world_engine/writes/goals_agendas.py
+++ b/src/world_engine/writes/goals_agendas.py
@@ -43,27 +43,16 @@ from sqlalchemy import text
 from sqlalchemy.orm import attributes as sa_attrs
 from sqlmodel import Session, select
 
-from ..condition_forms import (
-    ENTITY_TARGET_TYPES,
-    KEY_TARGET_TYPES,
-    REQUIREMENT_TYPES,
-    THRESHOLD_TYPES,
-    RequirementSpec,
-)
 from ..day_plan import PlanStep
 from ..models import (
-    BASE_SKILL_DOMAINS,
     Agenda,
     AgendaStep,
-    AgendaStepRequirement,
     Entity,
-    Fact,
     GoalAgendaLink,
     GoalPrerequisite,
     NpcGoal,
-    QuestOffer,
-    SkillDefinition,
 )
+from .conditions import clean_condition, write_condition
 
 # npc_goal.horizon enum (world-engine-schema.md v1.69): short | long.
 NPC_GOAL_HORIZONS = frozenset({"short", "long"})
@@ -601,93 +590,16 @@ def write_agenda_status(
     return agenda
 
 
-# The entity type each entity-targeted form must name (TICKET-0108, C-01);
-# `None` accepts any entity of the world -- the two model-emitted forms keep
-# the check they always had, so a day plan is refused for nothing new.
-_TARGET_ENTITY_TYPE: dict[str, Optional[tuple[str, ...]]] = {
-    "relation_gte": None, "location_reachable": None, "has_met": None, "faction_member": ("faction",),
-    # TICKET-0110 (G1): a debt's creditor, a character or a faction (J1).
-    "has_debt_to": ("character", "faction"), "no_debt_to": ("character", "faction"),
-}
-
-
-def _clean_target_key(db: Session, world_id: str, req: RequirementSpec) -> Optional[str]:
-    """The error for a key-targeted form whose key names nothing in
-    `world_id`, or None. `resource`'s key is a label (one currency per
-    world), never resolved."""
-    if req.type == "knowledge":
-        fact = db.get(Fact, req.target_key)
-        return None if fact is not None and fact.world_id == world_id else f"unknown fact {req.target_key!r}"
-    if req.type == "skill_rank_gte":
-        if req.target_key in BASE_SKILL_DOMAINS:
-            return None
-        definition = db.get(SkillDefinition, req.target_key)
-        ok = definition is not None and definition.world_id == world_id
-        return None if ok else f"unknown skill {req.target_key!r}"
-    if req.type == "quest_completed":
-        offer = db.get(QuestOffer, req.target_key)
-        return None if offer is not None and offer.world_id == world_id else f"unknown quest offer {req.target_key!r}"
-    return None
-
-
-def _clean_requirement(db: Session, world_id: str, step_index: int, req: RequirementSpec) -> dict:
-    """Validate one requirement against the per-type shape (the
-    `*_requirement_shape` CHECK, duplicated here as a readable `ValueError`
-    rather than a bare `IntegrityError`; its groups are `day_plan`'s
-    `ENTITY_TARGET_TYPES`/`KEY_TARGET_TYPES`/`THRESHOLD_TYPES`), check that
-    its target exists in `world_id`, and resolve it into the exact kwargs a
-    requirement row needs. Raises on any violation. Shared by
-    `write_day_plan` and the quest writers (`writes/quests.py`, C-03)."""
-    if req.type not in REQUIREMENT_TYPES:
-        raise ValueError(f"write_day_plan: unknown requirement type {req.type!r}")
-
-    entity_gated = req.type in ENTITY_TARGET_TYPES
-    if entity_gated:
-        if not req.target_entity_id:
-            raise ValueError(
-                f"write_day_plan: step {step_index} requirement type {req.type!r} needs a target_entity_id"
-            )
-        target = db.get(Entity, req.target_entity_id)
-        wanted = _TARGET_ENTITY_TYPE[req.type]
-        if target is None or target.world_id != world_id or (wanted is not None and target.type not in wanted):
-            raise ValueError(f"write_day_plan: unknown target entity {req.target_entity_id!r}")
-    else:
-        if not req.target_key:
-            raise ValueError(f"write_day_plan: step {step_index} requirement type {req.type!r} needs a target_key")
-        error = _clean_target_key(db, world_id, req)
-        if error is not None:
-            raise ValueError(f"write_day_plan: step {step_index} requirement type {req.type!r}: {error}")
-
-    threshold = req.threshold
-    if req.type in THRESHOLD_TYPES:
-        top = 5 if req.type == "skill_rank_gte" else None
-        if (not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 1
-                or (top is not None and threshold > top)):
-            raise ValueError(
-                f"write_day_plan: step {step_index} requirement type {req.type!r} needs a positive integer threshold"
-                + (f" of at most {top}" if top is not None else "")
-            )
-    else:
-        threshold = None
-
-    return {
-        "type": req.type,
-        "target_entity_id": req.target_entity_id if entity_gated else None,
-        "target_key": None if entity_gated else req.target_key,
-        "threshold": threshold,
-    }
-
-
-def _clean_plan_steps(db: Session, world_id: str, steps: list[PlanStep]) -> list[tuple[PlanStep, list[dict]]]:
+def _clean_plan_steps(db: Session, world_id: str, steps: list[PlanStep]) -> list[tuple[PlanStep, object]]:
     """All-or-nothing pre-validation for `write_day_plan` (Scope IN item 5):
-    every step and every requirement is checked before `write_day_plan`
-    constructs its first row."""
-    clean: list[tuple[PlanStep, list[dict]]] = []
+    every step and its whole prerequisite (`clean_condition`, TICKET-0111)
+    are checked before `write_day_plan` constructs its first row."""
+    clean: list[tuple[PlanStep, object]] = []
     for step_index, step in enumerate(steps):
         if not isinstance(step.cost, int) or isinstance(step.cost, bool) or not (1 <= step.cost <= 4):
             raise ValueError(f"write_day_plan: step {step_index} has invalid cost {step.cost!r}")
-        clean_requirements = [_clean_requirement(db, world_id, step_index, req) for req in step.requirements]
-        clean.append((step, clean_requirements))
+        where = f"write_day_plan: step {step_index}: "
+        clean.append((step, clean_condition(db, world_id, step.prerequisite, where)))
     return clean
 
 
@@ -703,7 +615,8 @@ def write_day_plan(
     """Persist one full day plan (TICKET-0075, BRIEF-0075-b): one `agenda`
     owned by the player (via `write_agenda` — its ACTIVE-owner and
     one-active-agenda guards apply unchanged, S3), its `agenda_step` rows in
-    order with `cost`/`domain`, and their `agenda_step_requirement` rows.
+    order with `cost`/`domain`, and their prerequisites (a `condition` each,
+    `write_condition`, TICKET-0111).
 
     All-or-nothing (Scope IN item 5): `_clean_plan_steps` validates every
     step and every requirement BEFORE any row is constructed — mirrors
@@ -722,7 +635,7 @@ def write_day_plan(
     clean_steps = _clean_plan_steps(db, world_id, steps)
 
     agenda = write_agenda(db, world_id=world_id, owner_entity_id=owner_entity_id, title=title)
-    for step_index, (step, clean_requirements) in enumerate(clean_steps):
+    for step_index, (step, prerequisite) in enumerate(clean_steps):
         agenda_step = write_agenda_step(
             db,
             agenda_id=agenda.id,
@@ -732,7 +645,7 @@ def write_day_plan(
             cost=step.cost,
             domain=step.domain,
         )
-        for clean in clean_requirements:
-            db.add(AgendaStepRequirement(world_id=world_id, step_id=agenda_step.id, **clean))
+        db.flush()
+        write_condition(db, world_id=world_id, role="prerequisite", tree=prerequisite, agenda_step_id=agenda_step.id)
 
     return agenda
diff --git a/src/world_engine/writes/quests.py b/src/world_engine/writes/quests.py
index 17ebf4f..61431b2 100644
--- a/src/world_engine/writes/quests.py
+++ b/src/world_engine/writes/quests.py
@@ -2,20 +2,20 @@
 contract C-03).
 
 - `write_quest_offer(...)` : create or save one offer, all or nothing. Its
-  steps and requirements are replaced whole (the `write_npc_prices`
+  steps and conditions are replaced whole (the `write_npc_prices`
   full-replace shape, `DELETE FROM` scoped to the offer, then the submitted
   set); the offer row snapshots its previous state into `change_history`.
 - `accept_quest(...)`      : the player takes an offer (B1, A1): one agenda
   born `paused` through `write_agenda`, its steps (the first `active`, the
-  creator-agenda precedent) and their requirements copied from the offer,
+  creator-agenda precedent) and their conditions copied from the offer,
   the `quest` row, and its own copy of the offer's terms (TICKET-0109, B1). Eligibility and L1 are judged HERE, so no caller can
   skip them.
 - `abandon_quest(...)`     : N1, the quest's agenda to `abandoned` through
   `write_agenda_status`; nothing is deleted.
 
-Every requirement goes through `goals_agendas._clean_requirement`, the same
-shape and target checks as a day plan's (B1: one language). None of these
-functions commits.
+Every condition goes through `conditions.clean_condition`, the same checks
+as a day plan's (B1, then I1 of TICKET-0111: one language), and is written
+by `conditions.write_condition`. None of these functions commits.
 """
 
 from __future__ import annotations
@@ -27,25 +27,24 @@ from sqlalchemy import text
 from sqlalchemy.orm import attributes as sa_attrs
 from sqlmodel import Session, select
 
-from ..condition_forms import RequirementSpec, evaluate_specs
+from ..conditions import Bindings, ConditionTree, evaluate, leaves, read_condition
 from ..day_plan import MAX_PLAN_STEPS, PlanStep
 from ..models import (
     BASE_SKILL_DOMAINS,
     QUEST_OFFER_STATUSES,
     Agenda,
     AgendaStep,
-    AgendaStepRequirement,
     Character,
     Entity,
     PassPlay,
     ProposedMutation,
     Quest,
     QuestOffer,
-    QuestOfferRequirement,
     QuestOfferStep,
 )
 from .debts import is_active_member
-from .goals_agendas import _clean_requirement, write_agenda, write_agenda_status, write_agenda_step
+from .conditions import clean_condition, delete_offer_conditions, write_condition
+from .goals_agendas import write_agenda, write_agenda_status, write_agenda_step
 from .quest_terms import TERM_COLUMNS, TermSpec, clean_terms, copy_terms_to_quest, offer_terms, write_offer_terms
 
 # An offer is given by a character or a faction of the world (H1).
@@ -55,10 +54,10 @@ QUEST_GIVER_TYPES: tuple[str, ...] = ("character", "faction")
 OPEN_QUEST_STATUSES: tuple[str, ...] = ("active", "paused")
 
 
-def _clean_offer_steps(db: Session, world_id: str, steps: list[PlanStep]) -> list[tuple[PlanStep, list[dict]]]:
+def _clean_offer_steps(db: Session, world_id: str, steps: list[PlanStep]) -> list[tuple[PlanStep, object]]:
     if not 1 <= len(steps) <= MAX_PLAN_STEPS:
         raise ValueError(f"write_quest_offer: an offer has 1 to {MAX_PLAN_STEPS} steps, got {len(steps)}")
-    clean: list[tuple[PlanStep, list[dict]]] = []
+    clean: list[tuple[PlanStep, object]] = []
     for index, step in enumerate(steps):
         if not isinstance(step.objective, str) or not step.objective.strip():
             raise ValueError(f"write_quest_offer: step {index} needs an objective")
@@ -66,7 +65,7 @@ def _clean_offer_steps(db: Session, world_id: str, steps: list[PlanStep]) -> lis
             raise ValueError(f"write_quest_offer: step {index} has invalid cost {step.cost!r}")
         if step.domain is not None and step.domain not in BASE_SKILL_DOMAINS:
             raise ValueError(f"write_quest_offer: step {index} has invalid domain {step.domain!r}")
-        clean.append((step, [_clean_requirement(db, world_id, index, req) for req in step.requirements]))
+        clean.append((step, clean_condition(db, world_id, step.prerequisite, f"write_quest_offer: step {index}: ")))
     return clean
 
 
@@ -112,14 +111,14 @@ def write_quest_offer(
     summary: Optional[str],
     repeatable: bool,
     status: str,
-    eligibility: list[RequirementSpec],
+    eligibility: Optional[ConditionTree],
     steps: list[PlanStep],
     terms: Optional[list[TermSpec]] = None,
     contact_entity_id: Optional[str] = None,
 ) -> QuestOffer:
     """Create (`offer` None) or save one offer (C-03). Everything is
-    validated before the first write; a `quest_completed` requirement on the
-    offer itself is refused (it could never be met). `terms` (TICKET-0109,
+    validated before the first write; a `quest_state` leaf naming the offer
+    itself is refused (a quest cannot wait on its own state). `terms` (TICKET-0109,
     B1) replaces the offer's costs and rewards whole; None keeps them, each
     re-validated against the giver, who may have changed.
     `contact_entity_id` (TICKET-0110, X1) is written as given."""
@@ -129,10 +128,10 @@ def write_quest_offer(
         raise ValueError(f"write_quest_offer: status must be one of {QUEST_OFFER_STATUSES}, got {status!r}")
     _check_giver(db, world_id, giver_entity_id)
     _check_contact(db, world_id, giver_entity_id, contact_entity_id or None)
-    every = list(eligibility) + [req for step in steps for req in step.requirements]
-    if offer is not None and any(r.type == "quest_completed" and r.target_key == offer.id for r in every):
-        raise ValueError("write_quest_offer: an offer cannot require its own completion")
-    clean_eligibility = [_clean_requirement(db, world_id, -1, req) for req in eligibility]
+    every = list(leaves(eligibility)) + [req for step in steps for req in leaves(step.prerequisite)]
+    if offer is not None and any(r.type == "quest_state" and r.target_key == offer.id for r in every):
+        raise ValueError("write_quest_offer: an offer cannot require its own state")
+    clean_eligibility = clean_condition(db, world_id, eligibility, "write_quest_offer: eligibility: ")
     clean_steps = _clean_offer_steps(db, world_id, steps)
     if terms is None:
         terms = [TermSpec(**{c: getattr(t, c) for c in TERM_COLUMNS}) for t in offer_terms(db, offer.id)] if offer else []
@@ -142,7 +141,7 @@ def write_quest_offer(
         offer = QuestOffer(world_id=world_id, giver_entity_id=giver_entity_id, title=title.strip(), change_history=[])
     else:
         _snapshot(offer)
-        db.execute(text("DELETE FROM quest_offer_requirement WHERE offer_id = :oid"), {"oid": offer.id})
+        delete_offer_conditions(db, offer.id)
         db.execute(text("DELETE FROM quest_offer_step WHERE offer_id = :oid"), {"oid": offer.id})
     offer.giver_entity_id = giver_entity_id
     offer.contact_entity_id = contact_entity_id or None
@@ -154,27 +153,21 @@ def write_quest_offer(
     db.add(offer)
     db.flush()
 
-    for clean in clean_eligibility:
-        db.add(QuestOfferRequirement(world_id=world_id, offer_id=offer.id, step_id=None, **clean))
-    for order, (step, clean_requirements) in enumerate(clean_steps, start=1):
+    write_condition(db, world_id=world_id, role="eligibility", tree=clean_eligibility, quest_offer_id=offer.id)
+    for order, (step, prerequisite) in enumerate(clean_steps, start=1):
         row = QuestOfferStep(world_id=world_id, offer_id=offer.id, step_order=order,
                              objective=step.objective.strip(), cost=step.cost, domain=step.domain)
         db.add(row)
         db.flush()
-        for clean in clean_requirements:
-            db.add(QuestOfferRequirement(world_id=world_id, offer_id=offer.id, step_id=row.id, **clean))
+        write_condition(db, world_id=world_id, role="prerequisite", tree=prerequisite, quest_offer_step_id=row.id)
     write_offer_terms(db, world_id=world_id, offer_id=offer.id, clean=clean_term_rows)
     return offer
 
 
-def offer_requirements(db: Session, offer_id: str, step_id: Optional[str]) -> tuple[RequirementSpec, ...]:
-    """An offer's eligibility (`step_id` None) or one step's requirements."""
-    condition = (QuestOfferRequirement.step_id.is_(None) if step_id is None
-                 else QuestOfferRequirement.step_id == step_id)
-    rows = db.exec(select(QuestOfferRequirement).where(
-        QuestOfferRequirement.offer_id == offer_id, condition).order_by(QuestOfferRequirement.id)).all()
-    return tuple(RequirementSpec(type=r.type, target_entity_id=r.target_entity_id, target_key=r.target_key,
-                                 threshold=r.threshold) for r in rows)
+def offer_bindings(offer: QuestOffer, character: Character) -> Bindings:
+    """What an offer's roles name for `character` (P1): he acts; the giver
+    and the contact are the offer's."""
+    return Bindings(doer=character, giver_id=offer.giver_entity_id, contact_id=offer.contact_entity_id)
 
 
 def acceptance_refusal(db: Session, offer: QuestOffer, character: Character) -> Optional[str]:
@@ -191,9 +184,12 @@ def acceptance_refusal(db: Session, offer: QuestOffer, character: Character) ->
         return "quête déjà acceptée"
     if any(status in OPEN_QUEST_STATUSES for status in taken):
         return "quête déjà en cours"
-    unmet = [v for v in evaluate_specs(offer_requirements(db, offer.id, None), character, db) if not v.met]
-    if unmet:
-        return "; ".join(v.reason for v in unmet)
+    eligibility = evaluate(read_condition(db, role="eligibility", quest_offer_id=offer.id),
+                           offer_bindings(offer, character), db)
+    if eligibility is not None and not eligibility.met:
+        unmet = [node.verdict.reason if node.verdict else (node.reason or "") for node in eligibility.leaf_nodes()
+                 if not node.met]
+        return "; ".join(unmet) or "conditions non remplies"
     return None
 
 
@@ -208,19 +204,17 @@ def accept_quest(db: Session, *, offer: QuestOffer, character: Character) -> Que
                     .order_by(QuestOfferStep.step_order)).all()
     if not steps:
         raise ValueError("accept_quest: the offer has no step")
-    copied = [(step, [_clean_requirement(db, offer.world_id, step.step_order, req)
-                      for req in offer_requirements(db, offer.id, step.id)]) for step in steps]
+    copied = [(step, read_condition(db, role="prerequisite", quest_offer_step_id=step.id)) for step in steps]
 
     agenda = write_agenda(db, world_id=offer.world_id, owner_entity_id=character.id, title=offer.title,
                           status="paused")
     db.flush()
-    for step, clean_requirements in copied:
+    for step, prerequisite in copied:
         row = write_agenda_step(db, agenda_id=agenda.id, step_order=step.step_order, objective=step.objective,
                                 status="active" if step.step_order == 1 else "pending",
                                 cost=step.cost, domain=step.domain)
         db.flush()
-        for clean in clean_requirements:
-            db.add(AgendaStepRequirement(world_id=offer.world_id, step_id=row.id, **clean))
+        write_condition(db, world_id=offer.world_id, role="prerequisite", tree=prerequisite, agenda_step_id=row.id)
     quest = Quest(world_id=offer.world_id, offer_id=offer.id, character_id=character.id, agenda_id=agenda.id)
     db.add(quest)
     db.flush()
diff --git a/src/world_engine/writes/worlds.py b/src/world_engine/writes/worlds.py
index 9d39897..3c93563 100644
--- a/src/world_engine/writes/worlds.py
+++ b/src/world_engine/writes/worlds.py
@@ -67,14 +67,14 @@ _DIRECT_WORLD_SCOPED_DELETES: tuple[str, ...] = (
     "faction_membership", "relation", "character", "discoverable_detail",
     "proposed_mutation", "ledger", "event", "gathering", "conversation",
     "session", "skill_definition", "entity",
-    "agenda", "agenda_step_requirement", "conversation_window_config",
+    "agenda", "condition", "condition_node", "conversation_window_config",
     "day_mention_choice", "day_mention_resolution", "day_mention_review",
     "day_rewrite", "door", "fact", "fact_default", "fact_participant",
     "faction_role", "goal_agenda_link", "goal_prerequisite",
     "location_type_catalog", "lore_entry", "npc_goal", "npc_price",
     "npc_schedule", "observation_run", "obstacle", "passage", "rencontre",
     "skill_rank", "skill_resolution", "skill_system", "unresolved_mention", "visit",
-    "world_law", "quest", "quest_offer", "quest_offer_requirement", "quest_offer_step",
+    "world_law", "quest", "quest_offer", "quest_offer_step",
     "item_holding", "quest_offer_term", "quest_term", "quest_economy",
     "debt", "debt_term",
 )
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 606fdcf..340a405 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18415,6 +18415,60 @@ of a counting form (« 60/50 »). One phrase per form (`FORM_PHRASES_FR`).
 **Rejected.** A fourth verdict state for « not applicable »: a leaf whose
 subject cannot be bound is unknown, and a gate treats it as not met.
 
+## A CONDITION IS STORED AS ROWS, ONE TREE PER OWNER (TICKET-0111) -- THE TWO REQUIREMENT TABLES BECOME `condition`, TWELVE FORMS (BRIEF-0111-c, schema v2.20)
+
+**O-a.** A condition is stored as rows, never JSON (CLAUDE.md: UI-visible
+data is relational): `condition`, one per owner and role -- an offer's
+`eligibility`, an offer step's or an agenda step's `prerequisite`, or its
+`completion` (M1, shown, never acted on) -- and `condition_node`, one row per
+node (`parent_id`, `position`). The nodes' foreign keys give the cascade of
+a world and « who cites X » for free. `agenda_step_requirement` and
+`quest_offer_requirement` are dropped; v2.20 turned each owner's rows into
+`all` of its leaves, in the rows' order, judged on `doer`.
+
+**No CHECK names a form.** The vocabulary is a code-plane property (the
+`entity_trait.trait_key` precedent): a new form is code, never a table
+rebuild (v2.17 and v2.19 each rebuilt two tables to widen one CHECK).
+`writes.conditions` is the one writer (`single_canon_write.py`) and refuses
+an unknown form, an ill-shaped tree, a subject that is not a character of
+the world, a target outside it, a missing value -- before any row. What a
+CHECK can say without naming a form, it says.
+
+**I1.** One language for every agenda. Day plans, offers and accepted
+quests all store and judge a tree: `PlanStep.prerequisite`,
+`EvaluatedStep.verdict` (`met` only when the verdict is), `evaluate_agenda_step`
+binding an offer's giver and contact (`plan_bindings`), acceptance judging
+the eligibility with the same bindings. The model still emits a flat list of
+its four forms; it becomes `all` of them.
+
+**Q1.** What a requirement row used to mean beyond gating keeps meaning
+it, read on the leaves reached through `all` only: the day's NPC is the
+first such `relation_gte`'s target; a completed step deepens the `knowledge`
+leaves judged on the one who acts. A leaf under `any`, `not` or `at_least`
+is not guaranteed and counts for neither.
+
+**S1.** `quest_state` (an offer's quest `open`, `completed`, `failed` or
+`abandoned`) replaces `quest_completed` -- one form for a quest's state;
+`item_held` (at least N of an item, `item_holding`) and `vital_status` (the
+subject's own state) read data the canon already keeps. `vital_status`'s
+values are the creator form's: the column has no CHECK.
+
+**The day's French.** `blocked_details_fr` says what a judged condition
+still lacks: an unmet leaf's detail, an unknown leaf's reason, and under a
+`not` that a leaf must not hold.
+
+**Old migrations.** v1.94, v2.17 and v2.19 created or rebuilt the dropped
+tables from their models; each now carries that table's DDL, frozen as it
+created it (`_Retired`), so it still runs on the database it was written
+for.
+
+**Rejected.** O-b (the tree as JSON, an exception in `json_ui_boundary.py`):
+the first JSON exception for durable canon content, with no foreign keys.
+A CHECK listing the forms on `condition_node`: a table rebuild per form.
+GP1: `goal_prerequisite` (an NPC goal's completion gate, one form) is a
+third language left out of this ticket; its own ticket, once this one is
+stable.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index e1a5b06..f62b0ba 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -4,8 +4,8 @@ knowledge ledger item skill skill_definition skill_system discoverable_detail
 event artifact npc_goal agenda agenda_step goal_agenda_link
 npc_price world_law obstacle obstacle_vertex door
 location_type_catalog entity_type entity_type_history conversation_window_config
-npc_schedule agenda_step_requirement fact fact_participant fact_default
-skill_rank quest_offer quest_offer_step quest_offer_requirement quest
+npc_schedule condition condition_node fact fact_participant fact_default
+skill_rank quest_offer quest_offer_step quest
 item_holding quest_offer_term quest_term quest_economy
 debt debt_term
 
@@ -50,12 +50,14 @@ src/world_engine/writes/config.py::upsert_skill_rank           skill_rank
 src/world_engine/writes/zone_promotion.py::apply_promotion     discoverable_detail
 # TICKET-0109, BRIEF-0109-A: write_holding is the one writer of item_holding -- set or move how many of an item an entity holds; apply_promotion now moves a place's items through it.
 src/world_engine/writes/items.py::write_holding                item_holding
-# TICKET-0075, BRIEF-0075-b: write_day_plan is the 30th site — its OWN body writes agenda_step_requirement only (it calls write_agenda/write_agenda_step, whose own db.add sites are already allow-listed above; single_canon_write.py is function-scoped, not interprocedural).
-src/world_engine/writes/goals_agendas.py::write_day_plan       agenda_step_requirement
 # TICKET-0108, BRIEF-0108-B: write_quest_offer creates or saves one quest offer -- its steps and requirements replaced whole (the write_npc_prices full-replace shape), the offer row snapshotted; creator CRUD only.
-src/world_engine/writes/quests.py::write_quest_offer           quest_offer quest_offer_step quest_offer_requirement
-# TICKET-0108, BRIEF-0108-B: accept_quest writes the quest row and copies the offer's step requirements; its agenda and steps go through write_agenda/write_agenda_step, allow-listed above (the write_day_plan precedent).
-src/world_engine/writes/quests.py::accept_quest                agenda_step_requirement quest
+src/world_engine/writes/quests.py::write_quest_offer           quest_offer quest_offer_step
+# TICKET-0108, BRIEF-0108-B: accept_quest writes the quest row; its agenda and steps go through write_agenda/write_agenda_step, allow-listed above, and since TICKET-0111 its steps' conditions through write_condition.
+src/world_engine/writes/quests.py::accept_quest                quest
+# TICKET-0111, BRIEF-0111-C: the condition language's one writer -- write_condition replaces one owner's condition whole (the full-replace shape), _write_node writes its nodes, delete_offer_conditions clears an offer's before write_quest_offer replaces them. Every caller (write_day_plan, write_quest_offer, accept_quest) calls them, never the tables.
+src/world_engine/writes/conditions.py::write_condition         condition condition_node
+src/world_engine/writes/conditions.py::_write_node             condition_node
+src/world_engine/writes/conditions.py::delete_offer_conditions condition condition_node
 # TICKET-0109, BRIEF-0109-B: write_offer_terms replaces an offer's costs and rewards whole (write_quest_offer's full-replace shape); copy_terms_to_quest gives an accepted quest its own copy; upsert_quest_economy sets a world's rates (curated config, upsert-one).
 src/world_engine/writes/quest_terms.py::write_offer_terms      quest_offer_term
 src/world_engine/writes/quest_terms.py::copy_terms_to_quest    quest_term
diff --git a/tooling/verify/checks/conditions.py b/tooling/verify/checks/conditions.py
index d41f4a4..d7fe7bd 100644
--- a/tooling/verify/checks/conditions.py
+++ b/tooling/verify/checks/conditions.py
@@ -42,6 +42,42 @@ CB5 -- the language writes nothing (static, AST). Neither `conditions.py`
    nor `condition_text.py` calls `add`, `commit`, `delete`, `execute` or
    `flush`.
 
+CC1 -- storage (BRIEF-0111-C, import). `condition` and `condition_node`
+   carry exactly their contract's columns and CHECK texts; `CONDITION_ROLES`
+   and `CONDITION_OPS` are the values those CHECKs quote, in order; no CHECK
+   of either table names a form; `models` declares neither
+   `AgendaStepRequirement` nor `QuestOfferRequirement`; the code's schema
+   version is v2.20 or later; `VALUE_LABELS_FR` labels exactly
+   `FORM_VALUES`.
+CC2 -- the writer (fixture). `write_condition` stores a tree using every
+   connector, a role, a fixed subject and a value; `read_condition` returns
+   it equal; a second write replaces it whole (the first nodes gone); None
+   removes it. Refused, each with no row written: an unknown form, a
+   `quest_state` with no value or an unknown one, a `vital_status` naming a
+   target, an `item_held` aimed at a character, a fixed subject that is a
+   faction, an eligibility on an agenda step, two owners, a `not` with two
+   children.
+CC3 -- migration `scripts/migrate_v2_20_conditions.py`, on a v2.19-shaped
+   database (both requirement tables in their v2.19 DDL, verbatim below)
+   holding an offer's eligibility, two rows of an offer step (one
+   `quest_completed`), two rows of an agenda step, and a `session` row
+   pointing to a missing world: at v2.18 it refuses and changes nothing; at
+   v2.19 both tables are gone, each owner has one `all` of its leaves in the
+   rows' order, judged on `doer`, `quest_completed` read as `quest_state`
+   `completed`, `foreign_key_check` is empty on the two new tables, the
+   orphan is noted, `schema_meta` is the code's version; a second run
+   changes nothing.
+CC4 -- the forms and the consumers (fixture). `item_held` reads the
+   holding, `vital_status` the subject's state, `quest_state` each of its
+   values. `evaluate_agenda_step` on a quest's agenda binds the offer's
+   giver; the day's NPC (`_account_rendezvous`) is the target of the first
+   `relation_gte` reached through `all`, never one under `any`; `blocked_details_fr` says what an
+   unmet leaf lacks and, under a `not`, that a leaf must not hold.
+CC5 -- the retired tables are gone from the code (static, AST). No module
+   under `src/` names `AgendaStepRequirement` or `QuestOfferRequirement`,
+   nor uses `agenda_step_requirement` or `quest_offer_requirement` as a
+   whole string.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
@@ -390,6 +426,452 @@ def check_cb5() -> None:
                 fail(f"CB5: {rel}:{node.lineno} calls .{node.func.attr}(")
 
 
+# --- CC1 -----------------------------------------------------------------------
+
+CONDITION_COLUMNS = ("id", "world_id", "role", "quest_offer_id", "quest_offer_step_id", "agenda_step_id", "created_at")
+NODE_COLUMNS = ("id", "world_id", "condition_id", "parent_id", "position", "op", "n", "form", "subject_role",
+                "subject_entity_id", "target_entity_id", "target_key", "threshold", "value")
+CONDITION_CHECKS = {
+    "ck_condition_role": "role IN ('eligibility','prerequisite','completion')",
+    "ck_condition_owner": "(quest_offer_id IS NOT NULL) + (quest_offer_step_id IS NOT NULL) + "
+                          "(agenda_step_id IS NOT NULL) = 1",
+    "ck_condition_owner_role": "(quest_offer_id IS NOT NULL) = (role = 'eligibility')",
+}
+NODE_CHECKS = {
+    "ck_condition_node_op": "op IN ('all','any','not','at_least','leaf')",
+    "ck_condition_node_leaf": "(op = 'leaf') = (form IS NOT NULL)",
+    "ck_condition_node_connector": "op = 'leaf' OR (subject_role IS NULL AND subject_entity_id IS NULL AND "
+                                   "target_entity_id IS NULL AND target_key IS NULL AND threshold IS NULL AND "
+                                   "value IS NULL)",
+    "ck_condition_node_subject": "op <> 'leaf' OR ((subject_role IS NULL) <> (subject_entity_id IS NULL))",
+    "ck_condition_node_role": "subject_role IS NULL OR subject_role IN ('doer','giver','contact')",
+    "ck_condition_node_n": "(op = 'at_least') = (n IS NOT NULL) AND (n IS NULL OR n >= 1)",
+}
+
+
+def _check_texts(table) -> dict[str, str]:
+    from sqlalchemy import CheckConstraint
+
+    return {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}
+
+
+def check_cc1() -> None:
+    import re
+
+    from world_engine import condition_forms, condition_text, models
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+
+    for model, columns, checks in ((models.Condition, CONDITION_COLUMNS, CONDITION_CHECKS),
+                                   (models.ConditionNode, NODE_COLUMNS, NODE_CHECKS)):
+        found = tuple(c.name for c in model.__table__.columns)
+        if found != columns:
+            fail(f"CC1: {model.__tablename__} columns are {found}")
+        texts = _check_texts(model.__table__)
+        if texts != checks:
+            fail(f"CC1: {model.__tablename__} CHECKs are {texts}")
+        for name, text in texts.items():
+            named = set(re.findall(r"'([^']*)'", text)) & set(condition_forms.REQUIREMENT_TYPES)
+            if named:
+                fail(f"CC1: {name} names the form(s) {sorted(named)}")
+    for constant, check in ((models.CONDITION_ROLES, CONDITION_CHECKS["ck_condition_role"]),
+                            (models.CONDITION_OPS, NODE_CHECKS["ck_condition_node_op"])):
+        if tuple(constant) != tuple(re.findall(r"'([^']*)'", check)):
+            fail(f"CC1: {constant} differs from the CHECK {check}")
+    for name in ("AgendaStepRequirement", "QuestOfferRequirement"):
+        if hasattr(models, name):
+            fail(f"CC1: models still declares {name}")
+    major, minor = (int(part) for part in EXPECTED_STATIC_SCHEMA_VERSION.lstrip("v").split("."))
+    if (major, minor) < (2, 20):
+        fail(f"CC1: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")
+    labels = {form: tuple(values) for form, values in condition_text.VALUE_LABELS_FR.items()}
+    if labels != {form: tuple(values) for form, values in condition_forms.FORM_VALUES.items()}:
+        fail(f"CC1: VALUE_LABELS_FR labels {labels}, not FORM_VALUES")
+
+
+# --- CC2 -----------------------------------------------------------------------
+
+def _cc_world(session) -> dict:
+    from world_engine.models import (
+        Agenda, AgendaStep, Character, Entity, Faction, Item, ItemHolding, QuestOffer, QuestOfferStep, World,
+    )
+
+    world = World(name="Conditions CC", is_active=False)
+    session.add(world)
+    session.flush()
+    ids = {"world": world.id}
+    for key, kind in (("pc", "player"), ("npc", "npc"), ("other", "npc")):
+        row = Entity(world_id=world.id, type="character", name=key.upper())
+        session.add(row)
+        session.flush()
+        session.add(Character(id=row.id, world_id=world.id, character_type=kind))
+        ids[key] = row.id
+    for key, kind in (("guild", "faction"), ("fur", "item")):
+        row = Entity(world_id=world.id, type=kind, name={"guild": "Guilde", "fur": "Fourrure"}[key])
+        session.add(row)
+        session.flush()
+        session.add(Faction(id=row.id) if kind == "faction" else Item(id=row.id))
+        ids[key] = row.id
+    session.add(ItemHolding(world_id=world.id, item_id=ids["fur"], holder_entity_id=ids["pc"], quantity=3,
+                            change_history=[]))
+    offer = QuestOffer(world_id=world.id, giver_entity_id=ids["npc"], title="La fourrure", change_history=[])
+    session.add(offer)
+    session.flush()
+    step = QuestOfferStep(world_id=world.id, offer_id=offer.id, step_order=1, objective="o", cost=1)
+    agenda = Agenda(world_id=world.id, owner_entity_id=ids["pc"], title="La fourrure", status="paused",
+                    change_history=[])
+    session.add(step)
+    session.add(agenda)
+    session.flush()
+    agenda_step = AgendaStep(agenda_id=agenda.id, step_order=1, objective="o", status="active", change_history=[])
+    session.add(agenda_step)
+    session.commit()
+    ids.update(offer=offer.id, offer_step=step.id, agenda=agenda.id, agenda_step=agenda_step.id)
+    return ids
+
+
+def _rows(session) -> tuple[int, int]:
+    from sqlmodel import func, select
+
+    from world_engine.models import Condition, ConditionNode
+
+    return (session.exec(select(func.count()).select_from(Condition)).one(),
+            session.exec(select(func.count()).select_from(ConditionNode)).one())
+
+
+def _cc2_round_trip(session, ids) -> None:
+    from world_engine.conditions import ConditionTree, all_of, leaf, read_condition
+    from world_engine.writes.conditions import write_condition
+
+    tree = ConditionTree(op="all", children=(
+        leaf(_spec("item_held", target_entity_id=ids["fur"], threshold=2)),
+        ConditionTree(op="any", children=(
+            leaf(_spec("has_met", subject_role="giver", target_entity_id=ids["pc"])),
+            ConditionTree(op="not", children=(leaf(_spec("vital_status", subject_role=None,
+                                                         subject_entity_id=ids["other"], value="dead")),)))),
+        ConditionTree(op="at_least", n=1, children=(
+            leaf(_spec("quest_state", target_key=ids["offer"], value="failed")),
+            leaf(_spec("has_debt_to", subject_role="contact", target_entity_id=ids["guild"]))))))
+    write_condition(session, world_id=ids["world"], role="completion", tree=tree, agenda_step_id=ids["agenda_step"])
+    session.commit()
+    if read_condition(session, role="completion", agenda_step_id=ids["agenda_step"]) != tree:
+        fail(f"CC2: the stored tree reads back as {read_condition(session, role='completion', agenda_step_id=ids['agenda_step'])}")
+    smaller = all_of([_spec("has_met", target_entity_id=ids["npc"])])
+    write_condition(session, world_id=ids["world"], role="completion", tree=smaller, agenda_step_id=ids["agenda_step"])
+    session.commit()
+    if read_condition(session, role="completion", agenda_step_id=ids["agenda_step"]) != smaller or _rows(session) != (1, 2):
+        fail(f"CC2: a second write did not replace the first whole: {_rows(session)}")
+    write_condition(session, world_id=ids["world"], role="completion", tree=None, agenda_step_id=ids["agenda_step"])
+    session.commit()
+    if read_condition(session, role="completion", agenda_step_id=ids["agenda_step"]) is not None or _rows(session) != (0, 0):
+        fail("CC2: writing no tree kept a condition")
+
+
+def _cc2_refusals(session, ids) -> None:
+    from world_engine.conditions import ConditionTree, all_of, leaf
+    from world_engine.writes.conditions import write_condition
+
+    def one(spec):
+        return all_of([spec])
+
+    cases = {
+        "an unknown form": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite", one(_spec("owes_a_favour"))),
+        "a quest_state with no value": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite",
+                                        one(_spec("quest_state", target_key=ids["offer"]))),
+        "a quest_state with an unknown value": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite",
+                                                one(_spec("quest_state", target_key=ids["offer"], value="won"))),
+        "a vital_status naming a target": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite",
+                                           one(_spec("vital_status", target_entity_id=ids["npc"], value="dead"))),
+        "an item_held aimed at a character": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite",
+                                              one(_spec("item_held", target_entity_id=ids["npc"], threshold=1))),
+        "a faction as fixed subject": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite",
+                                       one(_spec("has_met", subject_role=None, subject_entity_id=ids["guild"],
+                                                 target_entity_id=ids["pc"]))),
+        "an eligibility on an agenda step": ({"agenda_step_id": ids["agenda_step"]}, "eligibility",
+                                             one(_spec("has_met", target_entity_id=ids["npc"]))),
+        "two owners": ({"agenda_step_id": ids["agenda_step"], "quest_offer_step_id": ids["offer_step"]},
+                       "prerequisite", one(_spec("has_met", target_entity_id=ids["npc"]))),
+        "a not with two children": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite", ConditionTree(
+            op="not", children=(leaf(_spec("has_met", target_entity_id=ids["npc"])),) * 2)),
+    }
+    for label, (owner, role, tree) in cases.items():
+        before = _rows(session)
+        try:
+            write_condition(session, world_id=ids["world"], role=role, tree=tree, **owner)
+        except ValueError:
+            session.rollback()
+            if _rows(session) != before:
+                fail(f"CC2: refusing {label} wrote rows")
+            continue
+        session.rollback()
+        fail(f"CC2: write_condition accepts {label}")
+
+
+def check_cc2(engine) -> None:
+    from sqlmodel import Session
+
+    with Session(engine) as session:
+        ids = _cc_world(session)
+        _cc2_round_trip(session, ids)
+        _cc2_refusals(session, ids)
+
+
+# --- CC3 -----------------------------------------------------------------------
+
+MIGRATION = ROOT / "scripts" / "migrate_v2_20_conditions.py"
+
+# Both requirement tables as v2.19 created them (dumped from `main` at 2cdc92c).
+_V219_DDL = (
+    """CREATE TABLE agenda_step_requirement (
+	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, step_id VARCHAR NOT NULL, type VARCHAR NOT NULL,
+	target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER, PRIMARY KEY (id),
+	CONSTRAINT ck_agenda_step_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed','has_debt_to','no_debt_to')),
+	CONSTRAINT ck_agenda_step_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable','has_met','faction_member','has_debt_to','no_debt_to') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)),
+	FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(step_id) REFERENCES agenda_step (id),
+	FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
+    "CREATE UNIQUE INDEX idx_agenda_step_requirement_unique ON agenda_step_requirement "
+    "(step_id, type, target_entity_id, target_key)",
+    """CREATE TABLE quest_offer_requirement (
+	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, offer_id VARCHAR NOT NULL, step_id VARCHAR,
+	type VARCHAR NOT NULL, target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER, PRIMARY KEY (id),
+	CONSTRAINT ck_quest_offer_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed','has_debt_to','no_debt_to')),
+	CONSTRAINT ck_quest_offer_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable','has_met','faction_member','has_debt_to','no_debt_to') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)),
+	FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(offer_id) REFERENCES quest_offer (id),
+	FOREIGN KEY(step_id) REFERENCES quest_offer_step (id), FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
+    "CREATE INDEX idx_quest_offer_requirement_offer ON quest_offer_requirement (offer_id)",
+)
+
+
+def _cc3_seed(db_path: str) -> dict:
+    """A second database: the current schema, its condition tables dropped
+    and the two v2.19 tables laid back, with rows."""
+    import sqlite3
+
+    from sqlalchemy import create_engine
+    from sqlmodel import Session, SQLModel
+
+    from world_engine.models import SchemaMeta
+
+    eng = create_engine(f"sqlite:///{db_path}")
+    SQLModel.metadata.create_all(eng)
+    with Session(eng) as session:
+        ids = _cc_world(session)
+        session.add(SchemaMeta(id=1, static_version="v2.19"))
+        session.commit()
+    eng.dispose()
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("PRAGMA foreign_keys=OFF")
+        conn.execute("DROP TABLE condition_node")
+        conn.execute("DROP TABLE condition")
+        for statement in _V219_DDL:
+            conn.execute(statement)
+        w = ids["world"]
+        rows = (
+            ("quest_offer_requirement", "qor-1", ids["offer"], None, "faction_member", ids["guild"], None, None),
+            ("quest_offer_requirement", "qor-2", ids["offer"], ids["offer_step"], "has_met", ids["npc"], None, None),
+            ("quest_offer_requirement", "qor-3", ids["offer"], ids["offer_step"], "quest_completed", None,
+             ids["offer"], None),
+        )
+        for _t, rid, offer, step, form, entity, key, threshold in rows:
+            conn.execute("INSERT INTO quest_offer_requirement (id, world_id, offer_id, step_id, type, target_entity_id, "
+                         "target_key, threshold) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
+                         (rid, w, offer, step, form, entity, key, threshold))
+        for rid, form, entity, threshold in (("asr-b", "relation_gte", ids["npc"], 40),
+                                             ("asr-a", "has_met", ids["other"], None)):
+            conn.execute("INSERT INTO agenda_step_requirement (id, world_id, step_id, type, target_entity_id, threshold) "
+                         "VALUES (?, ?, ?, ?, ?, ?)", (rid, w, ids["agenda_step"], form, entity, threshold))
+        conn.execute("INSERT INTO session (id, world_id, number) VALUES ('orphan-session', 'gone-world', 9)")
+    return ids
+
+
+def _cc3_run(db_path: str):
+    import subprocess
+
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True, text=True,
+                          cwd=str(ROOT), timeout=120)
+
+
+def _cc3_state(db_path: str) -> dict:
+    import sqlite3
+
+    with sqlite3.connect(db_path) as conn:
+        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
+        trees = {}
+        if "condition_node" in tables:
+            for column in ("quest_offer_id", "quest_offer_step_id", "agenda_step_id"):
+                for cid, owner, role in conn.execute(f"SELECT id, {column}, role FROM condition WHERE {column} IS NOT NULL"):
+                    nodes = conn.execute("SELECT op, form, subject_role, target_entity_id, target_key, threshold, value, "
+                                         "parent_id IS NULL FROM condition_node WHERE condition_id = ? "
+                                         "ORDER BY parent_id IS NOT NULL, position", (cid,)).fetchall()
+                    trees[(column, owner, role)] = nodes
+        return {
+            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
+            "tables": sorted(t for t in tables if t.endswith("requirement") or t.startswith("condition")),
+            "trees": trees,
+        }
+
+
+def check_cc3() -> None:
+    import sqlite3
+
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "v2_19.db")
+    ids = _cc3_seed(db_path)
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("UPDATE schema_meta SET static_version = 'v2.18' WHERE id = 1")
+    before = _cc3_state(db_path)
+    result = _cc3_run(db_path)
+    if result.returncode == 0 or _cc3_state(db_path) != before:
+        fail("CC3: the migration ran on a v2.18 database or changed it")
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("UPDATE schema_meta SET static_version = 'v2.19' WHERE id = 1")
+    result = _cc3_run(db_path)
+    if result.returncode != 0:
+        fail(f"CC3: the migration failed: {result.stdout[-400:]} {result.stderr[-400:]}")
+        return
+    after = _cc3_state(db_path)
+    if after["tables"] != ["condition", "condition_node"]:
+        fail(f"CC3: the tables are {after['tables']}")
+    root = ("all", None, None, None, None, None, None, 1)
+    expected = {
+        ("quest_offer_id", ids["offer"], "eligibility"): [
+            root, ("leaf", "faction_member", "doer", ids["guild"], None, None, None, 0)],
+        ("quest_offer_step_id", ids["offer_step"], "prerequisite"): [
+            root, ("leaf", "has_met", "doer", ids["npc"], None, None, None, 0),
+            ("leaf", "quest_state", "doer", None, ids["offer"], None, "completed", 0)],
+        ("agenda_step_id", ids["agenda_step"], "prerequisite"): [
+            root, ("leaf", "relation_gte", "doer", ids["npc"], None, 40, None, 0),
+            ("leaf", "has_met", "doer", ids["other"], None, None, None, 0)],
+    }
+    if after["trees"] != expected:
+        fail(f"CC3: the trees are {after['trees']}")
+    if after["version"] != EXPECTED_STATIC_SCHEMA_VERSION or "Note: session rowid" not in result.stdout:
+        fail(f"CC3: schema_meta is {after['version']}, or the orphan session was not noted")
+    with sqlite3.connect(db_path) as conn:
+        dangling = [r for t in ("condition", "condition_node")
+                    for r in conn.execute(f"PRAGMA foreign_key_check({t})").fetchall()]
+    if dangling:
+        fail(f"CC3: foreign_key_check {dangling}")
+    again = _cc3_run(db_path)
+    if again.returncode != 0 or _cc3_state(db_path) != after:
+        fail(f"CC3: a second run exit {again.returncode} or changed a row")
+
+
+# --- CC4 -----------------------------------------------------------------------
+
+def _cc4_forms(session, ids) -> None:
+    from world_engine.condition_forms import _EVALUATORS
+    from world_engine.models import Agenda, Character, Quest
+
+    pc = session.get(Character, ids["pc"])
+
+    def met(form, **kw):
+        return _EVALUATORS[form](_spec(form, **kw), pc, session, None).met
+
+    if not met("item_held", target_entity_id=ids["fur"], threshold=3) or met("item_held", target_entity_id=ids["fur"],
+                                                                              threshold=4):
+        fail("CC4: item_held does not read the holding of 3")
+    if not met("vital_status", value="alive") or met("vital_status", value="dead"):
+        fail("CC4: vital_status does not read the character's state")
+    session.add(Quest(world_id=ids["world"], offer_id=ids["offer"], character_id=ids["pc"], agenda_id=ids["agenda"]))
+    session.commit()
+    for status, value in (("paused", "open"), ("failed", "failed"), ("abandoned", "abandoned")):
+        agenda = session.get(Agenda, ids["agenda"])
+        agenda.status = status
+        session.add(agenda)
+        session.commit()
+        others = [v for v in ("open", "completed", "failed", "abandoned") if v != value]
+        if not met("quest_state", target_key=ids["offer"], value=value) or any(
+                met("quest_state", target_key=ids["offer"], value=v) for v in others):
+            fail(f"CC4: quest_state misreads an agenda {status}")
+    agenda = session.get(Agenda, ids["agenda"])
+    agenda.status = "paused"
+    session.add(agenda)
+    session.commit()
+
+
+def _cc4_consumers(session, ids) -> None:
+    from world_engine.cockpit.routes.day import _account_rendezvous
+    from world_engine.conditions import ConditionTree, leaf
+    from world_engine.day_plan import evaluate_agenda_step
+    from world_engine.day_resolve import blocked_details_fr
+    from world_engine.models import AgendaStep, Character, ProposedMutation
+    from world_engine.writes.conditions import write_condition
+
+    pc = session.get(Character, ids["pc"])
+    tree = ConditionTree(op="all", children=(
+        ConditionTree(op="any", children=(leaf(_spec("relation_gte", target_entity_id=ids["other"], threshold=10)),)),
+        leaf(_spec("relation_gte", target_entity_id=ids["npc"], threshold=1)),
+        leaf(_spec("has_met", subject_role="giver", target_entity_id=ids["pc"])),
+        ConditionTree(op="not", children=(leaf(_spec("item_held", target_entity_id=ids["fur"], threshold=1)),))))
+    write_condition(session, world_id=ids["world"], role="prerequisite", tree=tree, agenda_step_id=ids["agenda_step"])
+    session.commit()
+    evaluated = evaluate_agenda_step(session.get(AgendaStep, ids["agenda_step"]), pc, session)
+    giver_leaf = evaluated.verdict.children[2]
+    if giver_leaf.state == "unknown" or giver_leaf.verdict is None:
+        fail(f"CC4: the quest's giver is not bound: {giver_leaf.reason}")
+    applied = ProposedMutation(world_id=ids["world"], mutation_type="agenda_step_change", status="applied",
+                               payload={"step_id": ids["agenda_step"]})
+    armed = _account_rendezvous([applied], session)
+    if armed is None or armed["npc_id"] != ids["npc"]:
+        fail(f"CC4: the day's NPC is {armed}, expected the relation_gte reached through all")
+    details = blocked_details_fr(evaluated.verdict, session)
+    if not any(d.startswith("il ne faut pas que") and "Fourrure" in d for d in details):
+        fail(f"CC4: the blocked details miss the negated leaf: {details}")
+
+
+def check_cc4(engine) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine.models import World
+
+    with Session(engine) as session:
+        world = session.exec(select(World).where(World.name == "Conditions CC")).one()
+        ids = _cc_ids(session, world.id)
+        _cc4_forms(session, ids)
+        _cc4_consumers(session, ids)
+
+
+def _cc_ids(session, world_id: str) -> dict:
+    from sqlmodel import select
+
+    from world_engine.models import Agenda, AgendaStep, Entity, QuestOffer, QuestOfferStep
+
+    names = {e.name: e.id for e in session.exec(select(Entity).where(Entity.world_id == world_id)).all()}
+    offer = session.exec(select(QuestOffer).where(QuestOffer.world_id == world_id)).one()
+    agenda = session.exec(select(Agenda).where(Agenda.world_id == world_id)).one()
+    return {"world": world_id, "pc": names["PC"], "npc": names["NPC"], "other": names["OTHER"],
+            "guild": names["Guilde"], "fur": names["Fourrure"], "offer": offer.id,
+            "offer_step": session.exec(select(QuestOfferStep).where(QuestOfferStep.offer_id == offer.id)).one().id,
+            "agenda": agenda.id,
+            "agenda_step": session.exec(select(AgendaStep).where(AgendaStep.agenda_id == agenda.id)).one().id}
+
+
+# --- CC5 -----------------------------------------------------------------------
+
+RETIRED_NAMES = {"AgendaStepRequirement", "QuestOfferRequirement"}
+RETIRED_TABLES = {"agenda_step_requirement", "quest_offer_requirement"}
+
+
+def check_cc5() -> None:
+    walked = 0
+    for path in sorted(SRC.rglob("*.py")):
+        if "__pycache__" in path.parts:
+            continue
+        walked += 1
+        rel = path.relative_to(SRC.parent).as_posix()
+        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
+            name = (node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute)
+                    else node.name if isinstance(node, ast.alias) else None)
+            if name in RETIRED_NAMES:
+                fail(f"CC5: {rel}:{getattr(node, 'lineno', '?')} names {name}")
+            if isinstance(node, ast.Constant) and node.value in RETIRED_TABLES:
+                fail(f"CC5: {rel}:{node.lineno} uses the table name {node.value!r}")
+    if not walked:
+        fail("CC5: walked zero modules")
+
+
 def main() -> int:
     _fresh_db()
     check_ca1()
@@ -400,6 +882,11 @@ def main() -> int:
     check_cb3(engine)
     check_cb4(engine)
     check_cb5()
+    check_cc1()
+    check_cc2(engine)
+    check_cc3()
+    check_cc4(engine)
+    check_cc5()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -407,7 +894,8 @@ def main() -> int:
     print("PASS: conditions -- the requirement forms, their evaluators and their BFS live in "
           "condition_forms.py alone; a condition is a tree of four connectors over those forms, "
           "shape-checked, judged in three values on each leaf's subject, and read back in French "
-          "without writing anything")
+          "without writing anything; v2.20 stores it as rows, one tree per owner and role, converted "
+          "from the two requirement tables it drops; every agenda judges it, binding a quest's giver")
     return 0
 
 
diff --git a/tooling/verify/checks/day_plan.py b/tooling/verify/checks/day_plan.py
index 14dcd64..0cfde64 100644
--- a/tooling/verify/checks/day_plan.py
+++ b/tooling/verify/checks/day_plan.py
@@ -4,20 +4,26 @@ BRIEF-0075-b). Stdlib `ast` and text only, no DB — same FAILURES/fail()/
 
 R1 (evaluator bijection, `_SOURCE_LOOKUPS` precedent): `_EVALUATORS`' key set
 equals `REQUIREMENT_TYPES` exactly, in both directions.
-R2 (type vocabulary): `agenda_step_requirement`'s `type` CHECK
-(`ck_agenda_step_requirement_type`) quotes exactly `REQUIREMENT_TYPES`'s
-values (eight since TICKET-0108).
-R3 (shape CHECK): `ck_agenda_step_requirement_shape` exists and its
-expression mentions every (type, column) pair from the per-type shape rule
-(eleven since TICKET-0108).
+R2 (type vocabulary): `REQUIREMENT_TYPES` (`condition_forms.py`) is exactly
+`EXPECTED_REQUIREMENT_TYPES` (twelve since TICKET-0111), and no
+`ck_condition*` CheckConstraint quotes a form (`goal_prerequisite`'s own
+CHECK is another language, TICKET-0111's GP1): since v2.20 the
+vocabulary is a code-plane property (TICKET-0111, BRIEF-0111-C), held by
+`writes.conditions`, never a SQL CHECK. (`agenda_step_requirement`'s type
+CHECK, which this rule read until v2.19, is gone with its table.)
+R3 (shape groups): every (form, argument) pair of the per-form shape rule
+is in its group constant of `condition_forms.py` -- `ENTITY_TARGET_TYPES`,
+`KEY_TARGET_TYPES`, `THRESHOLD_TYPES`, `NO_TARGET_TYPES` -- the constants
+the writer checks (the retired `ck_agenda_step_requirement_shape` until
+v2.19).
 R4 (budget derivation): `DAY_BUDGET_SLOTS` is a `len(...)` derivation, never
 a numeric literal.
 R5 (P2 / positional read exclusion): `day_plan.py` contains no reference to
 `current_phase`, and no `select(` against `NpcSchedule`.
 R6 (the positional wall, BRIEF-0074-a-amendment-1 — the single most important
 check in this brief): `Agenda`/`AgendaStep` declare no location-named field,
-and `schedule_reads.py` references neither `Agenda`, `AgendaStep` nor
-`AgendaStepRequirement`.
+and `schedule_reads.py` references none of `Agenda`, `AgendaStep`,
+`Condition`, `ConditionNode` (`AgendaStepRequirement` until v2.19).
 R7 (purity): `budget_cut`'s body contains no `db`, `select(`, `chat(`,
 `datetime`, or `randint`.
 R8 (parse + registry wiring): `emit_plan` routes through `llm_parse`, and
@@ -66,7 +72,8 @@ R15 (brief R5): the S3 refusal from -b (`_guard_no_active_agenda`, "already
 holds an active agenda") is gone from `routes/day.py`, and `plan_day` calls
 `_load_standing_agenda` — the reconciliation path is wired where the
 refusal used to be.
-R16 (brief R6): `day_reconcile.py` references neither `AgendaStepRequirement`
+R16 (brief R6): `day_reconcile.py` references none of `Condition`,
+`ConditionNode`, `read_condition` (`AgendaStepRequirement` until v2.19),
 nor `.cost` — it classifies intent, nothing else.
 R17 (brief R7): any `ProposedMutation(` constructed by the reconciliation
 path carries a `rationale` kwarg. Deliberately NOT vacuity-guarded to
@@ -186,17 +193,20 @@ GOALS_AGENDAS_FILE = SRC / "writes" / "goals_agendas.py"
 MUTATIONS_FILE = SRC / "cockpit" / "mutations.py"
 SEED_PILOT_FILE = ROOT / "scripts" / "seed_pilot.py"
 
-# AgendaStep/AgendaStepRequirement live in config.py, not canon.py (module_budget
-# headroom, TICKET-0075/BRIEF-0075-b) — Agenda stays in canon.py.
+# AgendaStep and the condition tables live in config.py, not canon.py
+# (module_budget headroom, TICKET-0075/BRIEF-0075-b) — Agenda stays in canon.py.
 _MODEL_FILES = (CANON_FILE, CONFIG_FILE)
 
 # Eight forms since v2.17 (TICKET-0108, BRIEF-0108-A): the model's four, then
 # the creator's four. Which ones the model may emit is `quests.py`'s QA1.
 EXPECTED_REQUIREMENT_TYPES = (
     "knowledge", "relation_gte", "resource", "location_reachable",
-    "has_met", "faction_member", "skill_rank_gte", "quest_completed",
+    "has_met", "faction_member", "skill_rank_gte", "quest_state",
     # TICKET-0110 (BRIEF-0110-A, G1): ten since v2.19.
     "has_debt_to", "no_debt_to",
+    # TICKET-0111 (BRIEF-0111-C, S1): twelve since v2.20; `quest_state`
+    # replaced `quest_completed`.
+    "item_held", "vital_status",
 )
 EXPECTED_RECONCILE_VERDICTS = ("continue", "modify", "replace")
 EXPECTED_PLAN_ACTIONS = ("continue", "modify", "replace", "resume")
@@ -335,47 +345,56 @@ def _all_check_constraints() -> dict[str, str]:
 
 
 def check_type_constraint() -> None:
+    """R2."""
+    tree = _parse(CONDITION_FORMS_FILE)
+    if tree is None:
+        return
+    forms = _tuple_assign(tree, "REQUIREMENT_TYPES")
+    values = tuple(e.value for e in forms.elts if isinstance(e, ast.Constant)) if forms is not None else ()
+    if values != EXPECTED_REQUIREMENT_TYPES:
+        fail(f"day_plan R2: REQUIREMENT_TYPES is {values!r}, expected {EXPECTED_REQUIREMENT_TYPES!r}")
     constraints = _all_check_constraints()
     if not constraints:
         fail("day_plan: zero CheckConstraint declarations located across canon.py/config.py")
         return
-    expr = constraints.get("ck_agenda_step_requirement_type")
-    if expr is None:
-        fail("day_plan: CheckConstraint 'ck_agenda_step_requirement_type' not found in canon.py/config.py")
-        return
-    quoted = set(re.findall(r"'([^']*)'", expr))
-    if quoted != set(EXPECTED_REQUIREMENT_TYPES):
-        fail(
-            f"day_plan R2: ck_agenda_step_requirement_type quotes {sorted(quoted)!r}, "
-            f"expected {sorted(EXPECTED_REQUIREMENT_TYPES)!r}"
-        )
+    condition_checks = {name: expr for name, expr in constraints.items() if name.startswith("ck_condition")}
+    if not condition_checks:
+        fail("day_plan R2: zero ck_condition* CheckConstraint located in config.py")
+    for name, expr in condition_checks.items():
+        named = set(re.findall(r"'([^']*)'", expr)) & set(EXPECTED_REQUIREMENT_TYPES)
+        if named:
+            fail(f"day_plan R2: {name} quotes the form(s) {sorted(named)!r} — the vocabulary is code-plane")
 
 
 def check_shape_constraint() -> None:
-    constraints = _all_check_constraints()
-    expr = constraints.get("ck_agenda_step_requirement_shape")
-    if expr is None:
-        fail("day_plan: CheckConstraint 'ck_agenda_step_requirement_shape' not found in canon.py/config.py")
+    """R3."""
+    tree = _parse(CONDITION_FORMS_FILE)
+    if tree is None:
         return
-
+    groups = {}
+    for name in ("ENTITY_TARGET_TYPES", "KEY_TARGET_TYPES", "THRESHOLD_TYPES", "NO_TARGET_TYPES"):
+        node = _tuple_assign(tree, name)
+        if node is None:
+            fail(f"day_plan R3: {_rel(CONDITION_FORMS_FILE)}: {name} not found")
+            return
+        groups[name] = {e.value for e in node.elts if isinstance(e, ast.Constant)}
     required_pairs = [
-        ("relation_gte", "target_entity_id"),
-        ("location_reachable", "target_entity_id"),
-        ("knowledge", "target_key"),
-        ("resource", "target_key"),
-        ("relation_gte", "threshold"),
-        ("resource", "threshold"),
-        ("has_met", "target_entity_id"),
-        ("faction_member", "target_entity_id"),
-        ("skill_rank_gte", "target_key"),
-        ("quest_completed", "target_key"),
-        ("skill_rank_gte", "threshold"),
-        ("has_debt_to", "target_entity_id"),
-        ("no_debt_to", "target_entity_id"),
+        ("relation_gte", "ENTITY_TARGET_TYPES"), ("location_reachable", "ENTITY_TARGET_TYPES"),
+        ("has_met", "ENTITY_TARGET_TYPES"), ("faction_member", "ENTITY_TARGET_TYPES"),
+        ("has_debt_to", "ENTITY_TARGET_TYPES"), ("no_debt_to", "ENTITY_TARGET_TYPES"),
+        ("item_held", "ENTITY_TARGET_TYPES"),
+        ("knowledge", "KEY_TARGET_TYPES"), ("resource", "KEY_TARGET_TYPES"),
+        ("skill_rank_gte", "KEY_TARGET_TYPES"), ("quest_state", "KEY_TARGET_TYPES"),
+        ("relation_gte", "THRESHOLD_TYPES"), ("resource", "THRESHOLD_TYPES"),
+        ("skill_rank_gte", "THRESHOLD_TYPES"), ("item_held", "THRESHOLD_TYPES"),
+        ("vital_status", "NO_TARGET_TYPES"),
     ]
-    missing = [pair for pair in required_pairs if pair[0] not in expr or pair[1] not in expr]
+    missing = [pair for pair in required_pairs if pair[0] not in groups[pair[1]]]
     if missing:
-        fail(f"day_plan R3: ck_agenda_step_requirement_shape missing condition(s) {missing!r}")
+        fail(f"day_plan R3: the shape groups miss {missing!r}")
+    targets = groups["ENTITY_TARGET_TYPES"] | groups["KEY_TARGET_TYPES"] | groups["NO_TARGET_TYPES"]
+    if targets != set(EXPECTED_REQUIREMENT_TYPES):
+        fail(f"day_plan R3: the target groups cover {sorted(targets)!r}, not every form")
 
 
 def check_budget_derivation() -> None:
@@ -448,7 +467,7 @@ def check_positional_wall() -> None:
     # comments and any string literal that merely mentions the word.
     schedule_reads_tree = _parse(SCHEDULE_READS_FILE)
     if schedule_reads_tree is not None:
-        forbidden_names = {"Agenda", "AgendaStep", "AgendaStepRequirement"}
+        forbidden_names = {"Agenda", "AgendaStep", "Condition", "ConditionNode"}
         for node in ast.walk(schedule_reads_tree):
             if isinstance(node, ast.ImportFrom):
                 for alias in node.names:
@@ -757,8 +776,8 @@ def check_reconcile_no_cost_or_requirement_reads() -> None:
     if tree is None:
         return
     for node in ast.walk(tree):
-        if isinstance(node, ast.Name) and node.id == "AgendaStepRequirement":
-            fail(f"day_plan R16: {_rel(DAY_RECONCILE_FILE)}:{node.lineno} — references AgendaStepRequirement")
+        if isinstance(node, ast.Name) and node.id in {"Condition", "ConditionNode", "read_condition"}:
+            fail(f"day_plan R16: {_rel(DAY_RECONCILE_FILE)}:{node.lineno} — references {node.id}")
         if isinstance(node, ast.Attribute) and node.attr == "cost":
             fail(f"day_plan R16: {_rel(DAY_RECONCILE_FILE)}:{node.lineno} — references .cost")
 
diff --git a/tooling/verify/checks/debts.py b/tooling/verify/checks/debts.py
index 56ccdec..f99848b 100644
--- a/tooling/verify/checks/debts.py
+++ b/tooling/verify/checks/debts.py
@@ -10,8 +10,10 @@ DA1 -- schema and vocabulary (BRIEF-0110-A, import and static).
       values those CHECKs quote, in order; `quest_offer` has
       `contact_entity_id` and `quest_economy` `debt_fact_relation` and
       `debt_skill_relation`; `DEFAULT_RATES` gives them 10 and 20 and
-      `ECONOMY_COLUMNS` lists them; the code's schema version is v2.19.
-   b. `condition_forms.REQUIREMENT_TYPES` ends with `has_debt_to`, `no_debt_to`;
+      `ECONOMY_COLUMNS` lists them; the code's schema version is v2.19 or
+      later (TICKET-0111 moved it to v2.20).
+   b. `condition_forms.REQUIREMENT_TYPES` holds `has_debt_to`, `no_debt_to`,
+      in that order (last until TICKET-0111 added two forms after them);
       both are in `ENTITY_TARGET_TYPES`, neither in `THRESHOLD_TYPES` nor
       `MODEL_REQUIREMENT_TYPES`; each has an evaluator and a French blocked
       detail; `questRequirements.js` offers both on the `givers` list.
@@ -35,7 +37,8 @@ DA3 -- the evaluators (fixture). With an OPEN debt of the character toward
    debt toward another creditor and a debt the character is OWED count for
    nothing. A faction creditor is judged like a character.
    `requirement_detail_fr` names the creditor in both forms.
-   `_clean_requirement` accepts a character and a faction as target and
+   `writes.conditions.clean_leaf` (`_clean_requirement` until TICKET-0111)
+   accepts a character and a faction as target and
    refuses a location.
 
 DB1 -- writing a debt (BRIEF-0110-B, fixture). `create_debt` refuses, each
@@ -255,15 +258,17 @@ def check_da1a() -> None:
             fail(f"DA1a: quest_economy has no {name}")
         if DEFAULT_RATES.get(name) != default or name not in ECONOMY_COLUMNS:
             fail(f"DA1a: {name} is not a default {default} economy column")
-    if EXPECTED_STATIC_SCHEMA_VERSION != "v2.19":
-        fail(f"DA1a: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")
+    major, minor = (int(part) for part in EXPECTED_STATIC_SCHEMA_VERSION.lstrip("v").split("."))
+    if (major, minor) < (2, 19):
+        fail(f"DA1a: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}, older than v2.19")
 
 
 def check_da1b() -> None:
     from world_engine import condition_forms, day_resolve
 
-    if tuple(condition_forms.REQUIREMENT_TYPES[-2:]) != DEBT_FORMS:
-        fail(f"DA1b: REQUIREMENT_TYPES ends with {condition_forms.REQUIREMENT_TYPES[-2:]}")
+    types = tuple(condition_forms.REQUIREMENT_TYPES)
+    if not set(DEBT_FORMS) <= set(types) or types.index("no_debt_to") != types.index("has_debt_to") + 1:
+        fail(f"DA1b: REQUIREMENT_TYPES lacks the two debt forms in order: {types}")
     for form in DEBT_FORMS:
         if form not in condition_forms.ENTITY_TARGET_TYPES:
             fail(f"DA1b: {form} is not an entity-target form")
@@ -353,7 +358,7 @@ def _seed_v218(db_path: str) -> dict:
         ids["model_shapes"] = {t: _shape(conn, t) for t in CHANGED_TABLES + ("debt", "debt_term")}
         conn.execute("PRAGMA foreign_keys=OFF")
         for table in ("debt_term", "debt") + CHANGED_TABLES:
-            conn.execute(f"DROP TABLE {table}")
+            conn.execute(f"DROP TABLE IF EXISTS {table}")
         for statement in _V218_DDL:
             conn.execute(statement)
         w, p, s = ids["world"], ids["person"], ids["step"]
@@ -491,7 +496,7 @@ def check_da3(engine) -> None:
     from world_engine.condition_forms import RequirementSpec, evaluate_specs
     from world_engine.day_resolve import requirement_detail_fr
     from world_engine.models import Character
-    from world_engine.writes.goals_agendas import _clean_requirement
+    from world_engine.writes.conditions import clean_leaf
 
     with Session(engine) as session:
         ids = _da3_world(session)
@@ -517,12 +522,12 @@ def check_da3(engine) -> None:
         for target, ok in (("npc", True), ("guild", True), ("place", False)):
             for form in DEBT_FORMS:
                 try:
-                    _clean_requirement(session, ids["world"], 0, RequirementSpec(type=form, target_entity_id=ids[target]))
+                    clean_leaf(session, ids["world"], RequirementSpec(type=form, target_entity_id=ids[target]))
                     accepted = True
                 except ValueError:
                     accepted = False
                 if accepted != ok:
-                    fail(f"DA3: _clean_requirement {'refuses' if ok else 'accepts'} {form} toward {target}")
+                    fail(f"DA3: clean_leaf {'refuses' if ok else 'accepts'} {form} toward {target}")
 
 
 # --- DB --------------------------------------------------------------------------
@@ -785,7 +790,7 @@ def _db4_quest(session, ids, giver, terms, title, contact=None):
     from world_engine.writes import accept_quest, write_quest_offer
 
     offer = write_quest_offer(session, world_id=ids["world"], offer=None, giver_entity_id=ids[giver], title=title,
-                              summary=None, repeatable=True, status="open", eligibility=[],
+                              summary=None, repeatable=True, status="open", eligibility=None,
                               steps=[PlanStep(objective="Chasser", cost=1, domain=None)], terms=terms,
                               contact_entity_id=ids[contact] if contact else None)
     session.flush()
diff --git a/tooling/verify/checks/knowledge_identity.py b/tooling/verify/checks/knowledge_identity.py
index ef833b5..8d7c995 100644
--- a/tooling/verify/checks/knowledge_identity.py
+++ b/tooling/verify/checks/knowledge_identity.py
@@ -125,6 +125,13 @@ _V2_08_DETAIL = (
     "CREATE TABLE discoverable_detail (id TEXT PRIMARY KEY, world_id TEXT NOT NULL, "
     "location_id TEXT NOT NULL, subject TEXT NOT NULL, content TEXT NOT NULL)"
 )
+# The table v2.09 rewrites the gates of, at v2.08: the current metadata no
+# longer has it (TICKET-0111 dropped it at v2.20, BRIEF-0111-C).
+_V2_08_REQUIREMENT = (
+    "CREATE TABLE agenda_step_requirement (id VARCHAR NOT NULL PRIMARY KEY, world_id VARCHAR NOT NULL "
+    "REFERENCES world (id), step_id VARCHAR NOT NULL REFERENCES agenda_step (id), type VARCHAR NOT NULL, "
+    "target_entity_id VARCHAR REFERENCES entity (id), target_key VARCHAR, threshold INTEGER)"
+)
 
 _ROWS: tuple[tuple[str, dict], ...] = (
     ("world", {"id": "w1", "name": "W"}),
@@ -213,8 +220,9 @@ def _insert(cursor, rows) -> None:
 
 def _v2_08_database() -> sqlite3.Connection:
     """A second database, built from the current metadata, then taken back
-    to the v2.08 shape: without the two objects v2.09 creates, and with the
-    `knowledge.subject` column and index v2.10 drops."""
+    to the v2.08 shape: without the two objects v2.09 creates, with the
+    `knowledge.subject` column and index v2.10 drops, and with the
+    `agenda_step_requirement` table v2.20 drops."""
     from sqlalchemy import create_engine
     from sqlmodel import SQLModel
 
@@ -226,6 +234,7 @@ def _v2_08_database() -> sqlite3.Connection:
     conn.execute("CREATE INDEX idx_knowledge_subject ON knowledge(subject)")
     conn.execute("DROP TABLE discoverable_detail")
     conn.execute(_V2_08_DETAIL)
+    conn.execute(_V2_08_REQUIREMENT)
     _insert(conn.cursor(), _ROWS)
     return conn
 
@@ -646,13 +655,15 @@ def _k6_plan(session, day) -> None:
         steps = emit_plan("déclaration", character, session)
     finally:
         ollama_client.chat = original
-    keys = [req.target_key for req in steps[0].requirements]
+    from world_engine.conditions import leaves
+
+    keys = [req.target_key for req in leaves(steps[0].prerequisite)]
     if not sent or "f2 — Le port ferme." not in sent[0] or keys != [day["port"], "f9"]:
         fail(f"K6b emit_plan sent {sent[:1]!r} and returned keys {keys!r}")
     anchored, dropped = anchor_requirements(steps, character, session)
-    if [r.target_key for r in anchored[0].requirements] != [day["port"]] \
-            or [d["target_key"] for d in dropped] != ["f9"]:
-        fail(f"K6b anchoring kept {anchored[0].requirements!r}, dropped {dropped!r}")
+    kept = leaves(anchored[0].prerequisite)
+    if [r.target_key for r in kept] != [day["port"]] or [d["target_key"] for d in dropped] != ["f9"]:
+        fail(f"K6b anchoring kept {kept!r}, dropped {dropped!r}")
 
 
 def _k6_verdicts(session, day) -> None:
diff --git a/tooling/verify/checks/quest_rewards.py b/tooling/verify/checks/quest_rewards.py
index ef2c4a0..2963b03 100644
--- a/tooling/verify/checks/quest_rewards.py
+++ b/tooling/verify/checks/quest_rewards.py
@@ -498,7 +498,7 @@ def _offer(ids: dict, **over) -> dict:
     from world_engine.day_plan import PlanStep
 
     base = dict(world_id=ids["world"], offer=None, giver_entity_id=ids["npc"], title="La fourrure",
-                summary=None, repeatable=False, status="open", eligibility=[],
+                summary=None, repeatable=False, status="open", eligibility=None,
                 steps=[PlanStep(objective="Chasser", cost=1, domain=None)])
     base.update(over)
     return base
@@ -724,7 +724,7 @@ def _rc_quest(session, ids, terms, title: str):
     from world_engine.writes import accept_quest, write_quest_offer
 
     offer = write_quest_offer(session, world_id=ids["world"], offer=None, giver_entity_id=ids["npc"], title=title,
-                              summary=None, repeatable=True, status="open", eligibility=[],
+                              summary=None, repeatable=True, status="open", eligibility=None,
                               steps=[PlanStep(objective="Chasser", cost=1, domain=None)], terms=terms)
     session.flush()
     quest = accept_quest(session, offer=offer, character=session.get(Character, ids["pc"]))
diff --git a/tooling/verify/checks/quests.py b/tooling/verify/checks/quests.py
index f684e70..64e7ff7 100644
--- a/tooling/verify/checks/quests.py
+++ b/tooling/verify/checks/quests.py
@@ -5,15 +5,15 @@ The lot adds its pieces brief by brief; this check grows with it (the
 `npc_skills.py` precedent, TICKET-0107). Each brief adds its rules here in
 the same commit.
 
-QA1 -- vocabulary (BRIEF-0108-A, static and import). `day_plan.REQUIREMENT_
-   TYPES` holds the eight forms, then TICKET-0110's two debt forms; `MODEL_REQUIREMENT_TYPES` is exactly the
-   model's four and a subset of it; `ENTITY_TARGET_TYPES` and
-   `KEY_TARGET_TYPES` partition it and `THRESHOLD_TYPES` is inside it; the
-   three `type NOT IN (...)` groups of `ck_agenda_step_requirement_shape`
-   are, in order, those three constants; `quest_offer_requirement`'s two
-   CHECK texts equal `agenda_step_requirement`'s; `day_plan.
-   _validate_requirement` (the model's parser) accepts each model form and
-   refuses each creator form.
+QA1 -- vocabulary (BRIEF-0108-A, static and import; since TICKET-0111 the
+   forms are `condition_forms`', no table carries their CHECK).
+   `REQUIREMENT_TYPES` holds the model's four forms, the creator's four
+   (`quest_state` in place of `quest_completed` since v2.20), TICKET-0110's
+   two debt forms and TICKET-0111's two (`conditions.py` owns those);
+   `MODEL_REQUIREMENT_TYPES` is exactly the model's four;
+   `ENTITY_TARGET_TYPES`, `KEY_TARGET_TYPES` and `NO_TARGET_TYPES` partition
+   it and `THRESHOLD_TYPES` is inside it; `day_plan._validate_requirement`
+   (the model's parser) accepts each model form and refuses every other.
 QA2 -- migration `scripts/migrate_v2_17_quests.py`, on a v2.16-shaped
    database (`agenda_step_requirement` in its v2.16 DDL, verbatim below, no
    quest table), holding one requirement row and a `session` row pointing
@@ -31,8 +31,9 @@ QA3 -- the evaluators (fixture). `relation_gte` reads what the target feels
    `faction_member` an active membership, secret included, a left one not;
    `skill_rank_gte` a base domain without a row at Initié, a definition
    without a row as not held, a row at its rank; `quest_completed` a quest
-   whose agenda is `completed`, not `paused`. `requirement_detail_fr` names
-   the target of each new form. `_clean_requirement` refuses a
+   whose agenda is `completed`, not `paused` (`quest_state` with the value
+   `completed` since v2.20). `requirement_detail_fr` names
+   the target of each new form. `writes.conditions.clean_leaf` refuses a
    `faction_member` aimed at a character, a `skill_rank_gte` threshold of
    6, an unknown skill, an unknown quest offer, and accepts each form well
    aimed.
@@ -40,14 +41,14 @@ QA3 -- the evaluators (fixture). `relation_gte` reads what the target feels
 QB1 -- the offer writer (BRIEF-0108-B, fixture). `write_quest_offer` refuses
    a location as giver, an empty title, a status `draft`, no step, a cost of
    5, a domain `magic`, a `faction_member` aimed at a character, and an
-   offer requiring its own completion -- each with no row written. A valid
-   offer writes its eligibility and its steps with their requirements;
-   saving it again replaces its steps and requirements whole (the old rows
+   offer requiring its own state -- each with no row written. A valid
+   offer writes its eligibility and its steps with their conditions;
+   saving it again replaces its steps and conditions whole (the old rows
    gone) and appends one `change_history` entry.
 QB2 -- acceptance (fixture, B1, A1, L1). An unmet eligibility refuses with
    no agenda written. Met: one agenda, `paused`, titled as the offer, the
    player's active plan still `active`; its steps copied in order, the first
-   `active`, the others `pending`, with their requirements; one `quest` row.
+   `active`, the others `pending`, with their conditions; one `quest` row.
    The same non-repeatable offer is refused a second time; a repeatable one
    is refused while its quest is open, accepted again once it is
    `completed`; a `closed` offer is refused. `available_offers` lists
@@ -71,7 +72,8 @@ QC1 -- the editor's mirror (BRIEF-0108-C, static). `frontend/src/creation/
    questRequirements.js`'s `REQUIREMENT_FORMS` has exactly the keys of
    `condition_forms.REQUIREMENT_TYPES`; its forms with `column: 'entity'` are
    `ENTITY_TARGET_TYPES`, with `column: 'key'` `KEY_TARGET_TYPES`, with
-   `threshold: true` `THRESHOLD_TYPES`.
+   `column: 'none'` `NO_TARGET_TYPES`, with `threshold: true`
+   `THRESHOLD_TYPES`, with `values: true` the keys of `FORM_VALUES`.
 QC2 -- the « Quêtes » tab (static). `tabs.js`'s `quetes` entry mounts the
    `questOffers` island in `creation-quetes` and routes « + Nouvelle quête »
    through `triggerPrimaryAction('questOffers')`; `QuestOffers.svelte`
@@ -102,10 +104,20 @@ MIGRATION = ROOT / "scripts" / "migrate_v2_17_quests.py"
 FAILURES: list[str] = []
 
 MODEL_FORMS = ("knowledge", "relation_gte", "resource", "location_reachable")
-CREATOR_FORMS = ("has_met", "faction_member", "skill_rank_gte", "quest_completed")
+CREATOR_FORMS = ("has_met", "faction_member", "skill_rank_gte", "quest_state")
 # TICKET-0110 (BRIEF-0110-A, G1): two more creator-only forms; `debts.py` owns them.
 DEBT_FORMS = ("has_debt_to", "no_debt_to")
+# TICKET-0111 (BRIEF-0111-C, S1): two more; `conditions.py` owns them.
+CONDITION_FORMS = ("item_held", "vital_status")
+# QA2 runs the v2.17 migration: the forms it added, the tables it created.
+V217_FORMS = ("has_met", "faction_member", "skill_rank_gte", "quest_completed")
 QUEST_TABLES = ("quest_offer", "quest_offer_step", "quest_offer_requirement", "quest")
+# The table v2.17 created that v2.20 dropped: its shape as v2.17 wrote it.
+V217_OFFER_REQUIREMENT_SHAPE = [
+    ("id", "VARCHAR", 1, None), ("offer_id", "VARCHAR", 1, None), ("step_id", "VARCHAR", 0, None),
+    ("target_entity_id", "VARCHAR", 0, None), ("target_key", "VARCHAR", 0, None),
+    ("threshold", "INTEGER", 0, None), ("type", "VARCHAR", 1, None), ("world_id", "VARCHAR", 1, None),
+]
 
 # `agenda_step_requirement` as v2.16 created it (dumped from `main` at 4b06dde).
 _V216_DDL = (
@@ -137,49 +149,26 @@ def _fresh_db() -> str:
 
 # --- QA1 -----------------------------------------------------------------------
 
-def _check_texts(table) -> dict[str, str]:
-    from sqlalchemy import CheckConstraint
-
-    return {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}
-
-
-def _shape_groups(shape: str) -> list[tuple[str, ...]]:
-    return [tuple(re.findall(r"'([^']*)'", group)) for group in re.findall(r"type NOT IN \(([^)]*)\)", shape)]
-
-
 def check_qa1() -> None:
     from world_engine import condition_forms, day_plan, llm_parse
-    from world_engine.models import AgendaStepRequirement, QuestOfferRequirement
 
     types = condition_forms.REQUIREMENT_TYPES
-    if tuple(types) != MODEL_FORMS + CREATOR_FORMS + DEBT_FORMS:
+    if tuple(types) != MODEL_FORMS + CREATOR_FORMS + DEBT_FORMS + CONDITION_FORMS:
         fail(f"QA1: REQUIREMENT_TYPES is {types}")
     if tuple(condition_forms.MODEL_REQUIREMENT_TYPES) != MODEL_FORMS or not set(MODEL_FORMS) <= set(types):
         fail(f"QA1: MODEL_REQUIREMENT_TYPES is {condition_forms.MODEL_REQUIREMENT_TYPES}")
-    entity, key, threshold = (set(condition_forms.ENTITY_TARGET_TYPES), set(condition_forms.KEY_TARGET_TYPES),
-                              set(condition_forms.THRESHOLD_TYPES))
-    if entity & key or entity | key != set(types) or not threshold or not threshold <= set(types):
-        fail(f"QA1: the shape groups do not partition the vocabulary: {entity}, {key}, {threshold}")
-
-    agenda = _check_texts(AgendaStepRequirement.__table__)
-    offer = _check_texts(QuestOfferRequirement.__table__)
-    shape = agenda.get("ck_agenda_step_requirement_shape", "")
-    groups = _shape_groups(shape)
-    expected = [tuple(condition_forms.ENTITY_TARGET_TYPES), tuple(condition_forms.KEY_TARGET_TYPES), tuple(condition_forms.THRESHOLD_TYPES)]
-    if groups != expected:
-        fail(f"QA1: the shape CHECK groups are {groups}, expected {expected}")
-    pairs = (("ck_agenda_step_requirement_type", "ck_quest_offer_requirement_type"),
-             ("ck_agenda_step_requirement_shape", "ck_quest_offer_requirement_shape"))
-    for agenda_name, offer_name in pairs:
-        if not agenda.get(agenda_name) or agenda.get(agenda_name) != offer.get(offer_name):
-            fail(f"QA1: {offer_name} differs from {agenda_name}")
+    entity, key, none = (set(condition_forms.ENTITY_TARGET_TYPES), set(condition_forms.KEY_TARGET_TYPES),
+                         set(condition_forms.NO_TARGET_TYPES))
+    threshold = set(condition_forms.THRESHOLD_TYPES)
+    if entity & key or (entity | key) & none or entity | key | none != set(types) or not threshold <= set(types):
+        fail(f"QA1: the shape groups do not partition the vocabulary: {entity}, {key}, {none}, {threshold}")
 
     for form in MODEL_FORMS:
         try:
             day_plan._validate_requirement({"type": form, "target_key": "k", "threshold": 1})
         except llm_parse.LlmParseError as exc:
             fail(f"QA1: the model's parser refuses {form!r}: {exc}")
-    for form in CREATOR_FORMS + DEBT_FORMS:
+    for form in CREATOR_FORMS + DEBT_FORMS + CONDITION_FORMS:
         try:
             day_plan._validate_requirement({"type": form, "target_key": "k", "threshold": 1})
         except llm_parse.LlmParseError:
@@ -226,10 +215,11 @@ def _seed_v216(db_path: str) -> dict:
         session.commit()
     engine.dispose()
     with sqlite3.connect(db_path) as conn:
-        ids["model_shapes"] = {t: _shape(conn, t) for t in QUEST_TABLES}
+        ids["model_shapes"] = {t: _shape(conn, t) for t in QUEST_TABLES if t != "quest_offer_requirement"}
+        ids["model_shapes"]["quest_offer_requirement"] = V217_OFFER_REQUIREMENT_SHAPE
         conn.execute("PRAGMA foreign_keys=OFF")
         for table in QUEST_TABLES[::-1] + ("agenda_step_requirement",):
-            conn.execute(f"DROP TABLE {table}")
+            conn.execute(f"DROP TABLE IF EXISTS {table}")
         for statement in _V216_DDL:
             conn.execute(statement)
         conn.execute(
@@ -270,7 +260,7 @@ def check_qa2(db_path: str) -> None:
     after = _state(db_path)
     if after["requirements"] != before["requirements"] or not after["requirements"]:
         fail(f"QA2b: the requirement rows are {after['requirements']}")
-    absent = [form for form in CREATOR_FORMS if f"'{form}'" not in after["check"]]
+    absent = [form for form in V217_FORMS if f"'{form}'" not in after["check"]]
     if absent:
         fail(f"QA2b: the stored CHECK lacks {absent}")
     if after["quest_tables"] != ids["model_shapes"]:
@@ -398,48 +388,50 @@ def _qa3_quest(session, ids, pc) -> None:
     session.add(Quest(world_id=ids["world"], offer_id=offer.id, character_id=ids["pc"], agenda_id=agenda.id))
     session.commit()
     ids["offer"] = offer.id
-    if _verdict(session, pc, "quest_completed", target_key=offer.id).met:
-        fail("QA3: quest_completed is met by a paused quest")
+    if _verdict(session, pc, "quest_state", target_key=offer.id, value="completed").met:
+        fail("QA3: quest_state completed is met by a paused quest")
+    if not _verdict(session, pc, "quest_state", target_key=offer.id, value="open").met:
+        fail("QA3: quest_state open is unmet by a paused quest")
     agenda.status = "completed"
     session.add(agenda)
     session.commit()
-    if not _verdict(session, pc, "quest_completed", target_key=offer.id).met:
-        fail("QA3: quest_completed is unmet by a completed quest")
+    if not _verdict(session, pc, "quest_state", target_key=offer.id, value="completed").met:
+        fail("QA3: quest_state completed is unmet by a completed quest")
 
 
 def _qa3_wording_and_cleaning(session, ids, pc) -> None:
     from world_engine.condition_forms import RequirementSpec
     from world_engine.day_resolve import requirement_detail_fr
-    from world_engine.writes.goals_agendas import _clean_requirement
+    from world_engine.writes.conditions import clean_leaf
 
     targets = {
         "has_met": {"target_entity_id": ids["npc"]},
         "faction_member": {"target_entity_id": ids["faction"]},
         "skill_rank_gte": {"target_key": ids["definition"], "threshold": 2},
-        "quest_completed": {"target_key": ids["offer"]},
+        "quest_state": {"target_key": ids["offer"], "value": "failed"},
     }
     names = {"has_met": "NPC", "faction_member": "Guilde", "skill_rank_gte": "Herboristerie",
-             "quest_completed": "La fourrure"}
+             "quest_state": "La fourrure"}
     for form, target in targets.items():
         text = requirement_detail_fr(_verdict(session, pc, form, **target))
         if names[form] not in text:
             fail(f"QA3: requirement_detail_fr for {form!r} is {text!r}")
         try:
-            _clean_requirement(session, ids["world"], 0, RequirementSpec(type=form, **target))
+            clean_leaf(session, ids["world"], RequirementSpec(type=form, **target))
         except ValueError as exc:
-            fail(f"QA3: _clean_requirement refuses a well-aimed {form!r}: {exc}")
+            fail(f"QA3: clean_leaf refuses a well-aimed {form!r}: {exc}")
     refused = (
         RequirementSpec(type="faction_member", target_entity_id=ids["npc"]),
         RequirementSpec(type="skill_rank_gte", target_key="agility", threshold=6),
         RequirementSpec(type="skill_rank_gte", target_key="no-such-skill", threshold=1),
-        RequirementSpec(type="quest_completed", target_key="no-such-offer"),
+        RequirementSpec(type="quest_state", target_key="no-such-offer", value="completed"),
     )
     for spec in refused:
         try:
-            _clean_requirement(session, ids["world"], 0, spec)
+            clean_leaf(session, ids["world"], spec)
         except ValueError:
             continue
-        fail(f"QA3: _clean_requirement accepts {spec}")
+        fail(f"QA3: clean_leaf accepts {spec}")
 
 
 def check_qa3(engine) -> None:
@@ -488,16 +480,18 @@ def _qb_world(session) -> dict:
 
 def _offer_kwargs(ids: dict, **over) -> dict:
     from world_engine.condition_forms import RequirementSpec
+    from world_engine.conditions import all_of
     from world_engine.day_plan import PlanStep
 
     steps = [
         PlanStep(objective="Traquer le loup", cost=2, domain="perception",
-                 requirements=(RequirementSpec(type="has_met", target_entity_id=ids["npc"]),)),
+                 prerequisite=all_of([RequirementSpec(type="has_met", target_entity_id=ids["npc"])])),
         PlanStep(objective="Rapporter la fourrure", cost=1, domain=None),
     ]
     base = dict(world_id=ids["world"], offer=None, giver_entity_id=ids["npc"], title="La fourrure",
                 summary="Le chasseur veut la fourrure.", repeatable=False, status="open",
-                eligibility=[RequirementSpec(type="faction_member", target_entity_id=ids["guild"])], steps=steps)
+                eligibility=all_of([RequirementSpec(type="faction_member", target_entity_id=ids["guild"])]),
+                steps=steps)
     base.update(over)
     return base
 
@@ -505,14 +499,15 @@ def _offer_kwargs(ids: dict, **over) -> dict:
 def _counts(session) -> tuple:
     from sqlmodel import func, select
 
-    from world_engine.models import Agenda, Quest, QuestOffer, QuestOfferRequirement, QuestOfferStep
+    from world_engine.models import Agenda, Condition, ConditionNode, Quest, QuestOffer, QuestOfferStep
 
     return tuple(session.exec(select(func.count()).select_from(m)).one()
-                 for m in (QuestOffer, QuestOfferStep, QuestOfferRequirement, Quest, Agenda))
+                 for m in (QuestOffer, QuestOfferStep, Condition, ConditionNode, Quest, Agenda))
 
 
 def _qb1_refusals(session, ids) -> None:
     from world_engine.condition_forms import RequirementSpec
+    from world_engine.conditions import all_of
     from world_engine.day_plan import PlanStep
     from world_engine.writes import write_quest_offer
 
@@ -520,7 +515,7 @@ def _qb1_refusals(session, ids) -> None:
         {"giver_entity_id": ids["place"]}, {"title": "  "}, {"status": "draft"}, {"steps": []},
         {"steps": [PlanStep(objective="o", cost=5, domain=None)]},
         {"steps": [PlanStep(objective="o", cost=1, domain="magic")]},
-        {"eligibility": [RequirementSpec(type="faction_member", target_entity_id=ids["npc"])]},
+        {"eligibility": all_of([RequirementSpec(type="faction_member", target_entity_id=ids["npc"])])},
     )
     for over in bad:
         before = _counts(session)
@@ -539,22 +534,25 @@ def check_qb1(session, ids) -> None:
     from sqlmodel import select
 
     from world_engine.condition_forms import RequirementSpec
+    from world_engine.conditions import all_of, leaves, read_condition
     from world_engine.day_plan import PlanStep
-    from world_engine.models import QuestOfferRequirement, QuestOfferStep
+    from world_engine.models import QuestOfferStep
     from world_engine.writes import write_quest_offer
 
     _qb1_refusals(session, ids)
     offer = write_quest_offer(session, **_offer_kwargs(ids))
     session.commit()
     ids["offer"] = offer.id
-    steps = session.exec(select(QuestOfferStep).where(QuestOfferStep.offer_id == offer.id)).all()
-    reqs = session.exec(select(QuestOfferRequirement).where(QuestOfferRequirement.offer_id == offer.id)).all()
-    if [s.step_order for s in sorted(steps, key=lambda s: s.step_order)] != [1, 2] or len(reqs) != 2:
+    steps = sorted(session.exec(select(QuestOfferStep).where(QuestOfferStep.offer_id == offer.id)).all(),
+                   key=lambda s: s.step_order)
+    reqs = list(leaves(read_condition(session, role="eligibility", quest_offer_id=offer.id)))
+    reqs += [r for s in steps for r in leaves(read_condition(session, role="prerequisite", quest_offer_step_id=s.id))]
+    if [s.step_order for s in steps] != [1, 2] or len(reqs) != 2:
         fail(f"QB1: a new offer wrote {len(steps)} step(s), {len(reqs)} requirement(s)")
     try:
-        write_quest_offer(session, **_offer_kwargs(ids, offer=offer, eligibility=[
-            RequirementSpec(type="quest_completed", target_key=offer.id)]))
-        fail("QB1: an offer requiring its own completion was saved")
+        write_quest_offer(session, **_offer_kwargs(ids, offer=offer, eligibility=all_of([
+            RequirementSpec(type="quest_state", target_key=offer.id, value="completed")])))
+        fail("QB1: an offer requiring its own state was saved")
     except ValueError:
         session.rollback()
     old_ids = {s.id for s in steps}
@@ -585,7 +583,8 @@ def _accept_refused(session, offer, pc, label: str) -> None:
 def _qb2_accepted(session, ids, quest) -> None:
     from sqlmodel import select
 
-    from world_engine.models import Agenda, AgendaStep, AgendaStepRequirement
+    from world_engine.conditions import leaves, read_condition
+    from world_engine.models import Agenda, AgendaStep
 
     agenda = session.get(Agenda, quest.agenda_id)
     if agenda is None or agenda.status != "paused" or agenda.title != "La fourrure":
@@ -598,7 +597,7 @@ def _qb2_accepted(session, ids, quest) -> None:
     if [(s.objective, s.status, s.cost) for s in steps] != [
             ("Traquer le loup", "active", 2), ("Rapporter la fourrure", "pending", 1)]:
         fail(f"QB2: the copied steps are {[(s.objective, s.status, s.cost) for s in steps]}")
-    reqs = session.exec(select(AgendaStepRequirement).where(AgendaStepRequirement.step_id == steps[0].id)).all()
+    reqs = leaves(read_condition(session, role="prerequisite", agenda_step_id=steps[0].id))
     if [(r.type, r.target_entity_id) for r in reqs] != [("has_met", ids["npc"])]:
         fail(f"QB2: the copied requirements are {[(r.type, r.target_entity_id) for r in reqs]}")
 
@@ -630,7 +629,7 @@ def check_qb2(session, ids) -> None:
         fail("QB2: an offer already taken is still available")
     _accept_refused(session, offer, pc, "a non-repeatable offer taken twice")
 
-    errand = write_quest_offer(session, **_offer_kwargs(ids, title="Bois", repeatable=True, eligibility=[]))
+    errand = write_quest_offer(session, **_offer_kwargs(ids, title="Bois", repeatable=True, eligibility=None))
     session.commit()
     first = accept_quest(session, offer=errand, character=pc)
     session.commit()
@@ -641,7 +640,7 @@ def check_qb2(session, ids) -> None:
     session.commit()
     accept_quest(session, offer=errand, character=pc)
     session.commit()
-    closed = write_quest_offer(session, **_offer_kwargs(ids, title="Fermée", status="closed", eligibility=[]))
+    closed = write_quest_offer(session, **_offer_kwargs(ids, title="Fermée", status="closed", eligibility=None))
     session.commit()
     _accept_refused(session, closed, pc, "a closed offer")
 
@@ -794,16 +793,20 @@ def check_qc1() -> None:
     from world_engine import condition_forms
 
     text = _read("creation/questRequirements.js")
-    forms = dict(re.findall(r"^\s+(\w+): \{ label: '[^']*', list: '\w+', (column: '\w+', threshold: \w+) \},$",
-                            text, re.M))
+    forms = dict(re.findall(
+        r"^\s+(\w+): \{ label: '[^']*', list: '\w+', (column: '\w+', threshold: \w+(?:, values: true)?) \},$",
+        text, re.M))
     if not forms:
         fail("QC1: REQUIREMENT_FORMS holds zero forms")
         return
     if list(forms) != list(condition_forms.REQUIREMENT_TYPES):
         fail(f"QC1: REQUIREMENT_FORMS keys {list(forms)} != REQUIREMENT_TYPES")
     groups = {
-        "column: 'entity'": tuple(condition_forms.ENTITY_TARGET_TYPES), "column: 'key'": tuple(condition_forms.KEY_TARGET_TYPES),
+        "column: 'entity'": tuple(condition_forms.ENTITY_TARGET_TYPES),
+        "column: 'key'": tuple(condition_forms.KEY_TARGET_TYPES),
+        "column: 'none'": tuple(condition_forms.NO_TARGET_TYPES),
         "threshold: true": tuple(condition_forms.THRESHOLD_TYPES),
+        "values: true": tuple(f for f in condition_forms.REQUIREMENT_TYPES if f in condition_forms.FORM_VALUES),
     }
     for marker, expected in groups.items():
         found = tuple(form for form, spec in forms.items() if marker in spec)
diff --git a/tooling/verify/checks/single_canon_write.py b/tooling/verify/checks/single_canon_write.py
index ea54b1d..7fbc654 100644
--- a/tooling/verify/checks/single_canon_write.py
+++ b/tooling/verify/checks/single_canon_write.py
@@ -78,7 +78,9 @@ holds the role) — creator-CRUD-only, never reachable from any AI or play
 path. Full-replace config deletes (whole-set replace, not
 single-row correction): `write_npc_prices`, `write_world_laws`,
 `write_location_obstacles`, `write_location_doors`, `write_quest_offer`
-(TICKET-0108, BRIEF-0108-B: an offer's steps and requirements) and
+(TICKET-0108, BRIEF-0108-B: an offer's steps; its conditions through
+`delete_offer_conditions`, TICKET-0111, BRIEF-0111-C), `write_condition`
+(TICKET-0111: one owner's condition and its nodes) and
 `write_offer_terms` (TICKET-0109, BRIEF-0109-B: an offer's terms) each
 `DELETE FROM` their table(s) scoped to one parent (NPC / world / location /
 location / offer) then re-insert the submitted set, in one transaction —
diff --git a/tooling/verify/checks/world_cascade.py b/tooling/verify/checks/world_cascade.py
index f09a961..654dfe0 100644
--- a/tooling/verify/checks/world_cascade.py
+++ b/tooling/verify/checks/world_cascade.py
@@ -117,8 +117,10 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
                 "title": "t"}),
     ("agenda_step", {"id": "ags-{w}", "agenda_id": "ag-{w}", "step_order": 1,
                      "objective": "o"}),
-    ("agenda_step_requirement", {"id": "agr-{w}", "world_id": "{w}", "step_id": "ags-{w}",
-                                 "type": "knowledge", "target_key": "k"}),
+    # TICKET-0111 (BRIEF-0111-C): an agenda step's prerequisite, one leaf.
+    ("condition", {"id": "cnd-{w}", "world_id": "{w}", "role": "prerequisite", "agenda_step_id": "ags-{w}"}),
+    ("condition_node", {"id": "cnn-{w}", "world_id": "{w}", "condition_id": "cnd-{w}", "op": "leaf",
+                        "form": "knowledge", "subject_role": "doer", "target_key": "k"}),
     ("batch", {"id": "bat-{w}", "session_id": "ses-{w}"}),
     ("door", {"id": "door-{w}", "world_id": "{w}", "location_id": "{w}-loc",
               "target_location_id": "{w}-loc", "x": 0.0, "y": 0.0}),
@@ -192,9 +194,6 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
                      "title": "q"}),
     ("quest_offer_step", {"id": "qos-{w}", "world_id": "{w}", "offer_id": "qo-{w}",
                           "step_order": 1, "objective": "o", "cost": 1}),
-    ("quest_offer_requirement", {"id": "qor-{w}", "world_id": "{w}", "offer_id": "qo-{w}",
-                                 "step_id": "qos-{w}", "type": "has_met",
-                                 "target_entity_id": "{w}-char"}),
     ("quest", {"id": "qu-{w}", "world_id": "{w}", "offer_id": "qo-{w}",
                "character_id": "{w}-char", "agenda_id": "ag-{w}"}),
     ("item_holding", {"id": "ih-{w}", "world_id": "{w}", "item_id": "{w}-item",
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index 37316eb..8919741 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,16 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.20** — TICKET-0111, BRIEF-0111-C: the condition language. `condition`
+  (one per owner and role: an offer's eligibility, an offer step's or an
+  agenda step's prerequisite or completion) and `condition_node` (a tree of
+  `all`/`any`/`not`/`at_least` connectors over leaves carrying one form, its
+  subject, target, threshold and value) are added; `agenda_step_requirement`
+  and `quest_offer_requirement` are dropped, every row converted into a leaf
+  of `all`, in its insertion order, judged on the one who acts.
+  `quest_completed` becomes `quest_state` with the value `completed`; the
+  forms `item_held` and `vital_status` are new. No CHECK names a form any
+  more: the vocabulary is the writer's (`writes.conditions`).
 - **v2.19** — TICKET-0110, BRIEF-0110-A: debts. `debt` (debtor, creditor,
   a faction creditor's contact, origin, reason, secrecy, its fact, status
   open/settled/forgiven -- never deleted) and `debt_term` (money, items, a
diff --git a/world-engine-schema.md b/world-engine-schema.md
index 5fef23a..c00110e 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.19
+Current schema version: v2.20
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -2199,8 +2199,8 @@ metadata. NULL for every pre-v1.94 (NPC) step — no backfill; populated only
 by the day-plan chain. `cost` = day-budget slots consumed (1-4); `domain` =
 the `resolve_physical` domain, or NULL when the step needs no roll. No
 location column here or ever (the positional wall,
-BRIEF-0074-a-amendment-1) — `agenda_step_requirement`'s `location_reachable`
-rows carry a location on the REQUIREMENT, never on the step.
+BRIEF-0074-a-amendment-1) — a `location_reachable` leaf of its `condition`
+(v2.20) carries a location on the CONDITION, never on the step.
 
 ```sql
 CREATE TABLE agenda_step (
@@ -2227,63 +2227,84 @@ CREATE UNIQUE INDEX idx_agenda_step_one_active
 
 -----
 
-### `agenda_step_requirement`
-
-Day-plan precondition gate on one `agenda_step` (schema v1.94, TICKET-0075,
-BRIEF-0075-b). `goal_prerequisite` shape precedent, widened to a closed
-vocabulary and a `target_key` column for the forms that gate on a string
-(a knowledge fact id since v2.09, TICKET-0097; a resource label; a skill
-key; a quest offer id) rather than an entity. Eight forms since v2.17
-(TICKET-0108, BRIEF-0108-A): `knowledge`, `relation_gte`, `resource`,
-`location_reachable` -- the four the day-plan model may emit
-(`day_plan.MODEL_REQUIREMENT_TYPES`) -- and `has_met`, `faction_member`,
-`skill_rank_gte`, `quest_completed`, authored by the creator only, on a
-quest offer. The per-type shape CHECK is the structural guarantee that an
-ill-formed row cannot exist: `relation_gte`/`location_reachable`/`has_met`/
-`faction_member` require `target_entity_id` NOT NULL;
-`knowledge`/`resource`/`skill_rank_gte`/`quest_completed` require
-`target_key` NOT NULL; `relation_gte`/`resource`/`skill_rank_gte` require
-`threshold` NOT NULL. Meanings: `relation_gte` reads what the TARGET feels
-toward the character (the social row target -> character, v2.17);
-`resource` is the character's money (one currency per world, `target_key`
-a label); `has_met` an encounter row of the pair; `faction_member` an
-active membership of the target faction; `skill_rank_gte` the rank held in
-a base domain or a skill definition (`target_key`), `threshold` 1-5;
-`quest_completed` a quest taken from the offer `target_key` whose agenda is
-`completed`. Ten forms since v2.19 (TICKET-0110, BRIEF-0110-A, G1):
-`has_debt_to` and `no_debt_to`, creator only, with `target_entity_id` the
-creditor (a character or a faction) -- the character is the debtor of at
-least one OPEN `debt` toward it, or of none; existence only, no threshold.
-Curated plan metadata, same family as `npc_schedule` -- no
-`change_history`. THE POSITIONAL WALL: `location_reachable`'s target lives
-HERE, never on `agenda_step` -- a requirement states "the player must be
-able to reach L", a precondition on the player, never a position of an NPC
-(see BRIEF-0074-a-amendment-1). Written by `writes.write_day_plan` and the
-quest acceptance; read by `day_plan.evaluate_specs`.
-
-```sql
-CREATE TABLE agenda_step_requirement (
-  id                TEXT PRIMARY KEY,
-  world_id          TEXT NOT NULL REFERENCES world(id),
-  step_id           TEXT NOT NULL REFERENCES agenda_step(id),
-  type              TEXT NOT NULL
-                      CHECK (type IN ('knowledge','relation_gte','resource','location_reachable',
-                                      'has_met','faction_member','skill_rank_gte','quest_completed',
-                                      'has_debt_to','no_debt_to')),
-  target_entity_id  TEXT REFERENCES entity(id),
-  target_key        TEXT,
-  threshold         INTEGER,
-  CHECK (
-    (type NOT IN ('relation_gte','location_reachable','has_met','faction_member',
-                  'has_debt_to','no_debt_to')
-       OR target_entity_id IS NOT NULL)
-    AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed')
-       OR target_key IS NOT NULL)
-    AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)
-  )
+### `condition`
+
+One condition, owned by exactly one of an offer (its eligibility), an offer
+step or an agenda step (its prerequisite, or its completion) -- schema
+v2.20, TICKET-0111, BRIEF-0111-C (decisions A1, I1, O-a). It replaced
+`agenda_step_requirement` (v1.94) and `quest_offer_requirement` (v2.17): the
+migration turned each owner's rows into one tree, `all` of them. At most one
+condition per owner and role. `completion` (M1) is shown in Journée and in
+« Déclarer accomplie », never acted on by the engine. Curated plan metadata,
+the requirement rows' family: no `change_history`; a save replaces a
+condition whole. Written only by `writes.conditions.write_condition` (and
+`delete_offer_conditions` before an offer is saved); read by
+`conditions.read_condition`.
+
+```sql
+CREATE TABLE condition (
+  id                   TEXT PRIMARY KEY,
+  world_id             TEXT NOT NULL REFERENCES world(id),
+  role                 TEXT NOT NULL CHECK (role IN ('eligibility','prerequisite','completion')),
+  quest_offer_id       TEXT REFERENCES quest_offer(id),
+  quest_offer_step_id  TEXT REFERENCES quest_offer_step(id),
+  agenda_step_id       TEXT REFERENCES agenda_step(id),
+  created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
+  CHECK ((quest_offer_id IS NOT NULL) + (quest_offer_step_id IS NOT NULL) + (agenda_step_id IS NOT NULL) = 1),
+  CHECK ((quest_offer_id IS NOT NULL) = (role = 'eligibility'))
 );
-CREATE UNIQUE INDEX idx_agenda_step_requirement_unique
-  ON agenda_step_requirement(step_id, type, target_entity_id, target_key);
+CREATE UNIQUE INDEX idx_condition_offer ON condition(quest_offer_id, role);
+CREATE UNIQUE INDEX idx_condition_offer_step ON condition(quest_offer_step_id, role);
+CREATE UNIQUE INDEX idx_condition_agenda_step ON condition(agenda_step_id, role);
+```
+
+-----
+
+### `condition_node`
+
+One node of a condition's tree (v2.20, O-a: rows, never JSON). A connector
+-- `all`, `any`, `not` (one child), `at_least` (`n` of its children) -- or
+a leaf carrying one form (`condition_forms.REQUIREMENT_TYPES`) and its
+arguments: its subject (a role bound when judged -- `doer`, `giver`,
+`contact` -- or one character, P1), its target (an entity or a key), a
+threshold, a value. `parent_id` and `position` give the tree its shape; the
+root has no parent. No CHECK names a form: the vocabulary is a code-plane
+property (the `entity_trait.trait_key` precedent), held by the one writer,
+which refuses an unknown form, a target outside the world or an ill-shaped
+tree before any row. Meanings of the forms: `relation_gte` reads what the
+TARGET feels toward the subject; `resource` the subject's money (one
+currency per world, `target_key` a label); `has_met` an encounter row;
+`faction_member` an active membership; `skill_rank_gte` a rank held (1-5);
+`quest_state` a quest taken from the offer `target_key` whose agenda is in
+`value` (`open`, `completed`, `failed`, `abandoned`); `has_debt_to` /
+`no_debt_to` an open debt toward the target or none; `item_held` at least
+`threshold` of the item held; `vital_status` the subject's own
+`vital_status` equal to `value`. THE POSITIONAL WALL holds:
+`location_reachable`'s target lives on the leaf, never on `agenda_step`.
+
+```sql
+CREATE TABLE condition_node (
+  id                 TEXT PRIMARY KEY,
+  world_id           TEXT NOT NULL REFERENCES world(id),
+  condition_id       TEXT NOT NULL REFERENCES condition(id),
+  parent_id          TEXT REFERENCES condition_node(id),
+  position           INTEGER NOT NULL DEFAULT 0,
+  op                 TEXT NOT NULL CHECK (op IN ('all','any','not','at_least','leaf')),
+  n                  INTEGER,
+  form               TEXT,
+  subject_role       TEXT CHECK (subject_role IS NULL OR subject_role IN ('doer','giver','contact')),
+  subject_entity_id  TEXT REFERENCES entity(id),
+  target_entity_id   TEXT REFERENCES entity(id),
+  target_key         TEXT,
+  threshold          INTEGER,
+  value              TEXT,
+  CHECK ((op = 'leaf') = (form IS NOT NULL)),
+  CHECK (op = 'leaf' OR (subject_role IS NULL AND subject_entity_id IS NULL AND target_entity_id IS NULL
+                         AND target_key IS NULL AND threshold IS NULL AND value IS NULL)),
+  CHECK (op <> 'leaf' OR ((subject_role IS NULL) <> (subject_entity_id IS NULL))),
+  CHECK ((op = 'at_least') = (n IS NOT NULL) AND (n IS NULL OR n >= 1))
+);
+CREATE INDEX idx_condition_node_condition ON condition_node(condition_id, parent_id, position);
 ```
 
 -----
@@ -2295,7 +2316,7 @@ The giver is a character or a faction of the world (H1). `status`: `open`
 (proposed to whoever is eligible) or `closed` (proposed to no one); an
 offer is never deleted. `repeatable` (L1): a repeatable offer may be
 accepted again once the last quest taken from it is over; any other offer
-once per character. Its steps and requirements are replaced whole on save
+once per character. Its steps and conditions are replaced whole on save
 (the `npc_price` full-replace precedent); the offer row keeps a
 `change_history`. Written only by `writes.write_quest_offer`.
 `contact_entity_id` (v2.19, TICKET-0110, X1): when the giver is a faction,
@@ -2324,7 +2345,8 @@ CREATE INDEX idx_quest_offer_world ON quest_offer(world_id);
 ### `quest_offer_step`
 
 One step of an offer, in order (v2.17). Copied to `agenda_step` when the
-offer is accepted: `cost` and `domain` mean what they mean there.
+offer is accepted, with its conditions: `cost` and `domain` mean what they
+mean there.
 
 ```sql
 CREATE TABLE quest_offer_step (
@@ -2341,32 +2363,6 @@ CREATE UNIQUE INDEX idx_quest_offer_step_order ON quest_offer_step(offer_id, ste
 
 -----
 
-### `quest_offer_requirement`
-
-A requirement of an offer (v2.17): with no `step_id`, an ELIGIBILITY
-requirement -- the offer is proposed only to a character who meets all of
-them; with a `step_id`, a requirement of that step, copied to
-`agenda_step_requirement` on acceptance. The vocabulary is
-`agenda_step_requirement`'s, never a second one (B1): its two CHECK texts
-are that table's, byte for byte (checked by `quests.py`).
-
-```sql
-CREATE TABLE quest_offer_requirement (
-  id                TEXT PRIMARY KEY,
-  world_id          TEXT NOT NULL REFERENCES world(id),
-  offer_id          TEXT NOT NULL REFERENCES quest_offer(id),
-  step_id           TEXT REFERENCES quest_offer_step(id),
-  type              TEXT NOT NULL,      -- agenda_step_requirement's type CHECK
-  target_entity_id  TEXT REFERENCES entity(id),
-  target_key        TEXT,
-  threshold         INTEGER
-  -- agenda_step_requirement's shape CHECK
-);
-CREATE INDEX idx_quest_offer_requirement_offer ON quest_offer_requirement(offer_id);
-```
-
------
-
 ### `quest`
 
 An offer a character accepted (v2.17, B1): the link to the agenda the
````

## Scope OUT

- Running the migration on the production database (Nia's live gate, after her backup).
- The `completion` role on any surface: the table accepts it (C-06); D writes and shows it.
- The offer API's shape (D): `OfferBody` keeps its flat lists here.
- A CHECK naming a form on `condition_node` (rejected: a table rebuild per form).
- `goal_prerequisite` and its writer (GP1).
- The interpreter in natural language (TICKET-0112), world state attributes (0113), the event journal, failure conditions and absence conditions (0114, N1), the creator dashboard (0115), rank trials (0116).
- `goal_prerequisite`, the NPC goal's gate (GP1: its own ticket).
- Any change to the day-chain prompts or to the model's four forms (`MODEL_REQUIREMENT_TYPES`).
- A completion that acts on its own (M2); a visual tree editor (T2).
- Any change to `legacy.html` or Play.
- BRIEF-0111-D.

## Invariants to defend

**UI-visible data never lives in JSON** -- the tree is rows; no JSON column is added (`json_ui_boundary.py`). **Two canon-write paths** -- `writes.conditions` is the only writer of the two tables, listed in `canon_write_policy.txt`; its full-replace delete is named in `single_canon_write.py`. **History is sacred** -- the migration converts every row before it drops a table, and its post-check counts leaves against rows form by form; an offer keeps its `change_history`. **The app refuses to boot on a schema mismatch** -- `schema_version.py`, `world-engine-schema.md` and the migration agree on v2.20. **Commit before touching any canon-writing path**: this brief touches the creator CRUD of offers and the day plan's writer -- start from a clean, committed tree.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- A named mutation does not turn its rule red.
- The migration's post-check fails on the test database, or a second run changes anything.
- Any finding that would make the migration drop a table before its rows are converted.
- A CHECK of `condition` or `condition_node` would need to name a form.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `npm run build` names a different asset hash than the prototype's: commit what it builds (`frontend_build_fresh.py` judges the manifest, not the name).

REPORT-ONLY:
- The migration's « Note: » lines for orphans in tables it does not write (AMENDMENT-0107-01: never blocking).
- `pyflakes` reporting `VetoVerdict` imported but unused in `routes/day.py` (pre-existing).
- Svelte a11y warnings during the build (pre-existing), npm's `EBADENGINE` notice.
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run every check with `WORLD_ENGINE_ENV=test`).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and `src/world_engine/cockpit/static/`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/conditions.py` -> `PASS: conditions -- the requirement forms, their evaluators and their BFS live in condition_forms.py alone; a condition is a tree of four connectors over those forms, shape-checked, judged in three values on each leaf's subject, and read back in French without writing anything; v2.20 stores it as rows, one tree per owner and role, converted from the two requirement tables it drops; every agenda judges it, binding a quest's giver`
- `day_plan.py`, `quests.py`, `debts.py`, `quest_rewards.py`, `knowledge_identity.py`, `day_narration.py`, `world_cascade.py`, `single_canon_write.py`, `json_ui_boundary.py`, `schema_version_agreement.py`, `frontend_build_fresh.py`, `module_budget.py`, `function_length.py`, `import_cycle.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`conditions.py` exits 1 with the rule named):
  - in `src/world_engine/models/config.py`, `CONDITION_OPS: tuple[str, ...] = ("all", "any", "not", "at_least", "leaf")` -> `CONDITION_OPS: tuple[str, ...] = ("all", "any", "not", "at_least", "none", "leaf")` -> `CC1`
  - in `src/world_engine/writes/conditions.py`, `    if subject is None or subject.world_id != world_id or subject.type != "character":` -> `    if subject is None or subject.world_id != world_id:` -> `CC2`
  - in `scripts/migrate_v2_20_conditions.py`, `_RENAMED_FORMS = {"quest_completed": ("quest_state", "completed")}` -> `_RENAMED_FORMS = {}` -> `CC3`
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 144/144.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `A CONDITION IS STORED AS ROWS, ONE TREE PER OWNER (TICKET-0111) -- THE TWO REQUIREMENT TABLES BECOME `condition`, TWELVE FORMS (BRIEF-0111-c, schema v2.20)` -- in the diff. `world-engine-schema.md` (header v2.20, the two tables, the two dropped) and `world-engine-schema-changelog.md` (v2.20 entry) -- in the diff.
