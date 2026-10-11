<!-- slug: attribute-form -->
# BRIEF 0113-B — "A condition reads the state of the world -- one form, `attribute`, on any entity it applies to; `vital_status` becomes a system attribute; a hidden one never reaches a player (schema v2.23)"

Lot: LOT-0113-world-state.md (authoritative on conflict)
Depends on: BRIEF-0113-A (C-01, C-02)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0113-A's commit).

- `src/world_engine/schema_version.py:15` -> `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.22"`
- `src/world_engine/condition_forms.py:68` -> `REQUIREMENT_TYPES: tuple[str, ...] = (`
- `src/world_engine/condition_forms.py:88` -> `NO_TARGET_TYPES: tuple[str, ...] = ("vital_status",)`
- `src/world_engine/condition_forms.py:91` -> `VITAL_STATUSES: tuple[str, ...] = ("alive", "dead", "missing", "unknown")`
- `src/world_engine/conditions.py:81` -> `class VerdictNode:`
- `src/world_engine/conditions.py:359` -> `def _subject(spec: RequirementSpec, bindings: Bindings, db: Session) -> tuple[Optional[Character], Optional[str]]:`
- `src/world_engine/condition_text.py:44` -> `"vital_status": "{who} est {value}",`
- `src/world_engine/day_resolve.py:279` -> `"vital_status": "{required} n'est pas dans l'état voulu",`
- `src/world_engine/writes/conditions.py:136` -> `def clean_leaf(db: Session, world_id: str, req: RequirementSpec, where: str = "") -> RequirementSpec:`
- `src/world_engine/quest_reads.py:122` -> `def editor_choices(world_id: str, db: Session) -> dict:`
- `CLAUDE.md:223` -> `- **INV-22** A model names a fact only by a code from a`
- No `scripts/migrate_v2_23_attribute_leaves.py`, no `tooling/verify/checks/attribute_conditions.py`; no `INV-62` in `CLAUDE.md` or `.claude/rules/`.

## Facts carried

### R-04 — a condition leaf, and what production holds [M]
Opened: `src/world_engine/models/config.py:157-189` (`ConditionNode`: a
connector carries no `target_key` / `threshold` / `value` (CHECK `:164`);
a leaf's `form` is free text -- no CHECK on the vocabulary -- `target_key`
`:189`). Measured 2026-10-10 on a read-only copy of Nia's database
(`schema_meta` v2.21): `SELECT count(*) FROM condition_node WHERE form =
'vital_status'` -> 0; `pt-condition-interpret` at version 1, unedited.
Consequence: v2.23 is data-only (no DDL): `migrate_v2_23_attribute_leaves.py`
moves any `vital_status` leaf to `attribute` / `sys:vital_status`, keeping
subject and value, and refuses a leaf it cannot convert (a target, a
threshold, a value outside the four). On production it converts nothing.
The prompt script edits version 1 into version 2.

### R-05 — the forms [M]
Opened: `src/world_engine/condition_forms.py:68` (`REQUIREMENT_TYPES`,
twelve, `vital_status` last), `:77` (`MODEL_REQUIREMENT_TYPES`), `:81-85`
(`ENTITY_TARGET_TYPES`, `KEY_TARGET_TYPES`, `THRESHOLD_TYPES`), `:88`
(`NO_TARGET_TYPES = ("vital_status",)`), `:91` (`VITAL_STATUSES`), `:94`
(`QUEST_STATES`), `:99` (`FORM_VALUES`), `:103` (`RequirementSpec`), `:120`
(`Verdict`), `:329` (`_eval_vital_status`), `:372` (`_EVALUATORS`).
Consequence: `attribute` takes `vital_status`'s place (still twelve), is a
`KEY_TARGET_TYPES` form (its `target_key` an attribute key), and
`NO_TARGET_TYPES` / `VITAL_STATUSES` go; `FORM_VALUES` keeps `quest_state`.
`MODEL_REQUIREMENT_TYPES` is untouched: the day plan's model never emits it.

### R-06 — evaluation judges a character; the player's view [M]
Opened: `src/world_engine/conditions.py:81` (`VerdictNode`), `:113-136`
(`seen_by`, `_seen_subject`: a leaf about someone else reads `?`), `:326`
(`evaluate`), `:359` (`_subject`: a role or an entity, as a `Character`),
`:378` (`_evaluate_leaf`). AMENDMENT-0111-01 (A1, V2) is the law
`seen_by` enforces.
Consequence: a form of `ANY_SUBJECT_TYPES` takes any entity as subject;
one the attribute does not apply to, or an attribute gone, is `unknown`
(`attribute_unjudged`); `Verdict.hidden` makes `seen_by` read `?` even for
the doer. A1, V2 and WH1 become one invariant, INV-62.

### R-07 — the French of a leaf, on the creator's and the player's side [M]
Opened: `src/world_engine/condition_text.py:32` (`FORM_PHRASES_FR`, `:44`
`vital_status`), `:49-50` (`VALUE_LABELS_FR`), `:68` (`HIDDEN_FACT_FR`),
`:105` (`leaf_text(db, spec, viewer_id)`); `src/world_engine/day_resolve.py:262`
(`_BLOCKED_DETAIL_FR`, `:279` `vital_status`), `:283`
(`requirement_detail_fr`), `:298` (`player_detail_fr`).
Consequence: one phrase `"{who} — {target} : {value}"`, the value a label,
« N ou plus », an entity or « quelqu'un »; `HIDDEN_STATE_FR` and
`HIDDEN_STATE_DETAIL_FR` for a player.

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

### R-09 — the offer editor's choices and row [M]
Opened: `src/world_engine/quest_reads.py:61` (`condition_view`), `:122`
(`editor_choices`); `frontend/src/creation/questRequirements.js:15`
(`REQUIREMENT_FORMS`), `:39` (`SUBJECT_ROLES`), `:45-77`
(`blankRequirement`, `subjectOptions`, `targetOptions`, `valueOptions`,
`requirementBody`), `:99-118` (`conditionDraft`, `blankCondition`,
`conditionBody`); `frontend/src/creation/QuestRequirementRow.svelte`.
Consequence: `editor_choices` gains `attributes` (`attribute_choice`) and
`entities` (every active entity: a fixed subject, an entity value); the
row's controls follow the attribute's kind.

### R-16 — the schema version moves in three places; a migration converges [M]
Opened: `src/world_engine/schema_version.py:15` (`"v2.21"`);
`world-engine-schema.md:3`; `world-engine-schema-changelog.md:16`;
`scripts/migrate_v2_21_condition_draft.py:54` (`_PREVIOUS_VERSION`),
`:133-145` (`_converge_schema_meta` writes the CODE's version).
Consequence: two versions in one lot. Each migration converges
`schema_meta` to ITS OWN version (v2.22, v2.23), not the code's: a
database migrated by v2.22 alone stays refused by the boot guard
(measured: « schema_meta says DB is at 'v2.22', code expects 'v2.23' »)
until v2.23 has run.

### R-18 — `day_plan.py` reads the vocabulary as literals [M]
Opened: `tooling/verify/checks/day_plan.py:8`, `:202`
(`EXPECTED_REQUIREMENT_TYPES`, twelve), `:162-166` (AST rules on string
constants).
Consequence: `"attribute"` is written as a literal in
`REQUIREMENT_TYPES`, `KEY_TARGET_TYPES`, `ANY_SUBJECT_TYPES`, never through
`ATTRIBUTE_FORM` (AB1 keeps the constant equal); B updates
`EXPECTED_REQUIREMENT_TYPES`.

### R-19 — fifteen seconds per check [M]
Opened: `tooling/verify/checks/corpus_gate.py:21-28` (per-check timeout,
`TIMEOUT` a failure); `.claude/rules/verify-checks.md` (15 s).
Consequence: the rules are split over three checks -- `attributes.py`
(AA, AC; ~5 s measured), `attribute_conditions.py` (AB; ~7 s),
`attribute_interpreter.py` (AD, AE; ~6 s) -- each wrapping every rule so a
crash is a named failure.

### R-20 — CLAUDE.md after TICKET-0117 [M]
Opened: `CLAUDE.md:223` (INV-22, the last root invariant before
`## Path-scoped rules`); `tooling/verify/checks/claude_md_contract.py`
(budgets, 100-character lines, invariant ids and markers).
Consequence: B adds INV-62 after INV-22 (the next free id; INV-61 is the
highest used), ending `-- enforced by conditions.py, attribute_conditions.py`.

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

### C-04 — the `attribute` leaf (stored form) and its verdict
Produced by: BRIEF-0113-B   Consumed by: C, D, E
`condition_node.form = "attribute"`, `target_key` a definition id or a
`sys:` key; subject a role or any entity of the world (a fixed subject of
a type the attribute applies to); by kind: `choice` -> `value` = a choice
key (a choice id, or a system value); `integer` -> `threshold` (any
integer, met at « N or more »); `entity` -> `target_entity_id` (an entity
of a value type) or None (« quelqu'un »: met when any is set). Every other
field None. `condition_forms`: `ANY_SUBJECT_TYPES = ("attribute",)`,
`attribute_unjudged(req, holder, db) -> Optional[str]`,
`Verdict.hidden: bool`. `conditions`: `HIDDEN_STATE_REASON_FR`;
`condition_text`: `FORM_PHRASES_FR["attribute"] = "{who} — {target} :
{value}"`, `HIDDEN_STATE_FR`; `day_resolve`: `HIDDEN_STATE_DETAIL_FR =
"quelque chose de caché l'en empêche encore"`. `writes.conditions.clean_leaf`
-> `_clean_attribute`. `quest_reads.editor_choices(...)["attributes"]`
(`attribute_choice(view)`: `{key, name, kind, system, hidden,
holder_types, value_types, choices: [{value, label}]}`) and `["entities"]`
(`[{id, name, type}]`, active, by name). Verdicts: b-2.

### C-05 — `migrate_v2_23_attribute_leaves.py`
Produced by: BRIEF-0113-B   Consumed by: Nia (live gate)
Refuses below v2.22. Every leaf of form `vital_status` -> form
`attribute`, `target_key` `sys:vital_status`, subject and value kept;
refused (nothing written) when one carries a target, a threshold, or a
value outside the four. Converges `schema_meta` to v2.23. Idempotent.

## Context

Attributes exist (A); now a condition reads them. One form, `attribute`, judges any entity the attribute applies to -- « le pont est détruit » judges the bridge -- by label, threshold or entity. `vital_status` stops being a form of its own: it is the system attribute `sys:vital_status`, and its leaves (none in production, measured) are converted. A hidden attribute never reaches a player, not even about his own character: INV-62 joins A1 and V2 of AMENDMENT-0111-01 with WH1.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`, `src/world_engine/cockpit/static/` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `condition_forms.py`: `attribute` replaces `vital_status` (still twelve forms), joins `KEY_TARGET_TYPES`; `ANY_SUBJECT_TYPES`; `NO_TARGET_TYPES` and `VITAL_STATUSES` removed, `FORM_VALUES` keeps `quest_state`; `_eval_attribute`, `attribute_unjudged`, `Verdict.hidden` (C-04);
   - `conditions.py`: any entity as subject for `ANY_SUBJECT_TYPES`, `unknown` off its types, `seen_by` hides a hidden verdict (`HIDDEN_STATE_REASON_FR`);
   - `condition_text.py`, `day_resolve.py`: the attribute phrase, `HIDDEN_STATE_FR`, `HIDDEN_STATE_DETAIL_FR`; `writes/conditions.py`: `_clean_attribute`, subject any entity; `quest_reads.py`: `attributes`, `entities`, `attribute_choice`; `attributes.view_of`; `condition_interpreter.py`'s hint for the form;
   - the editor: `questRequirements.js` (the `attribute` form, `attributeOf`, `attributeTargets`, `subjectOptions(choices, req)`), `QuestRequirementRow.svelte` (kind-specific controls);
   - creates `scripts/migrate_v2_23_attribute_leaves.py` (C-05, b-3) and bumps the version to v2.23 (data only: no DDL) in the three places;
   - adds INV-62 to `CLAUDE.md` after INV-22 (R-20);
   - creates check `attribute_conditions.py` (AB1-AB5); `attributes.py`, `conditions.py`, `quests.py`, `day_plan.py`, `condition_interpreter.py` follow the vocabulary (enumeration (c) 1 of the lot);
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - CLAUDE.md
   - frontend/src/creation/QuestRequirementRow.svelte
   - frontend/src/creation/questRequirements.js
   - scripts/migrate_v2_23_attribute_leaves.py
   - src/world_engine/attributes.py
   - src/world_engine/condition_forms.py
   - src/world_engine/condition_interpreter.py
   - src/world_engine/condition_text.py
   - src/world_engine/conditions.py
   - src/world_engine/day_resolve.py
   - src/world_engine/quest_reads.py
   - src/world_engine/schema_version.py
   - src/world_engine/writes/conditions.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/attribute_conditions.py
   - tooling/verify/checks/attributes.py
   - tooling/verify/checks/condition_interpreter.py
   - tooling/verify/checks/conditions.py
   - tooling/verify/checks/day_plan.py
   - tooling/verify/checks/quests.py
   - world-engine-schema-changelog.md
   - world-engine-schema.md

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index 804db36..44e1491 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -222,6 +222,11 @@ listed in `tooling/verify/baselines/invariant_ids.retired`. Each ends with
   `zone_map_links.py`
 - **INV-22** A model names a fact only by a code from a
   `fact_refs.code_facts` list; code resolves it. [no check]
+- **INV-62** A player surface shows a condition only as its character may
+  know it (`VerdictNode.seen_by`, `viewer_id`): a leaf about someone else or
+  on a hidden attribute reads `?`; a fact he does not know and a hidden
+  attribute are never written out (`HIDDEN_FACT_FR`, `HIDDEN_STATE_FR`).
+  -- enforced by `conditions.py`, `attribute_conditions.py`
 
 ## Path-scoped rules
 
diff --git a/frontend/src/creation/QuestRequirementRow.svelte b/frontend/src/creation/QuestRequirementRow.svelte
index f357611..c24eec4 100644
--- a/frontend/src/creation/QuestRequirementRow.svelte
+++ b/frontend/src/creation/QuestRequirementRow.svelte
@@ -3,14 +3,17 @@
      its target from the matching picker list, its threshold when the form
      takes one. `req` is a draft object owned by questOffersState.
      TICKET-0111: its subject first (P1), its value when the form compares
-     to one. */
-  import { REQUIREMENT_FORMS, subjectOptions, targetOptions, valueOptions } from './questRequirements.js';
+     to one. TICKET-0113: an `attribute` compares to what its attribute's
+     kind takes -- a label, an integer (« ou plus »), or an entity (or anyone). */
+  import { REQUIREMENT_FORMS, attributeOf, attributeTargets, subjectOptions, targetOptions,
+           valueOptions } from './questRequirements.js';
 
   let { req, choices, onremove } = $props();
 
   let form = $derived(REQUIREMENT_FORMS[req.type]);
   let options = $derived(targetOptions(req.type, choices));
   let values = $derived(valueOptions(req.type, choices));
+  let attr = $derived(req.type === 'attribute' ? attributeOf(req.target_key, choices) : null);
 
   function setType(type) {
     req.type = type;
@@ -23,13 +26,19 @@
   function setTarget(value) {
     if (form.column === 'entity') req.target_entity_id = value;
     else req.target_key = value;
+    if (req.type === 'attribute') {
+      const next = attributeOf(value, choices);
+      req.value = '';
+      req.target_entity_id = '';
+      req.threshold = next && next.kind === 'integer' ? 1 : null;
+    }
   }
 </script>
 
 <div class="quest-req">
   <select value={req.subject || 'role:doer'} title="Qui la condition juge"
           onchange={(e) => { req.subject = e.target.value; }}>
-    {#each subjectOptions(choices) as o (o.value)}
+    {#each subjectOptions(choices, req) as o (o.value)}
       <option value={o.value}>{o.label}</option>
     {/each}
   </select>
@@ -38,7 +47,7 @@
       <option value={type}>{f.label}</option>
     {/each}
   </select>
-  {#if form.list !== 'money' && form.column !== 'none'}
+  {#if form.list !== 'money'}
     <select value={form.column === 'entity' ? req.target_entity_id : req.target_key}
             onchange={(e) => setTarget(e.target.value)}>
       <option value="">—</option>
@@ -55,6 +64,25 @@
       {/each}
     </select>
   {/if}
+  {#if attr && attr.kind === 'choice'}
+    <select value={req.value ?? ''} onchange={(e) => { req.value = e.target.value; }}>
+      <option value="">—</option>
+      {#each attr.choices as c (c.value)}
+        <option value={c.value}>{c.label}</option>
+      {/each}
+    </select>
+  {:else if attr && attr.kind === 'integer'}
+    <input type="number" style="width:70px" title="ou plus" value={req.threshold ?? ''}
+           oninput={(e) => { req.threshold = e.target.value === '' ? null : Number(e.target.value); }}>
+    <span class="quest-req-hint">ou plus</span>
+  {:else if attr && attr.kind === 'entity'}
+    <select value={req.target_entity_id ?? ''} onchange={(e) => { req.target_entity_id = e.target.value; }}>
+      <option value="">— quelqu’un —</option>
+      {#each attributeTargets(attr, choices) as o (o.value)}
+        <option value={o.value}>{o.label}</option>
+      {/each}
+    </select>
+  {/if}
   {#if form.threshold}
     <input type="number" min="1" max={req.type === 'skill_rank_gte' ? 5 : undefined}
            style="width:70px" value={req.threshold ?? ''}
@@ -66,4 +94,5 @@
 <style>
   .quest-req { display: flex; gap: 6px; align-items: center; flex-wrap: wrap; margin: 3px 0; }
   .quest-req select { max-width: 260px; }
+  .quest-req-hint { font-size: 12px; opacity: 0.7; }
 </style>
diff --git a/frontend/src/creation/questRequirements.js b/frontend/src/creation/questRequirements.js
index 2040194..1daad89 100644
--- a/frontend/src/creation/questRequirements.js
+++ b/frontend/src/creation/questRequirements.js
@@ -8,9 +8,11 @@
    alone. TICKET-0110 (BRIEF-0110-A): the two debt forms, whose target is
    a creditor -- a character or a faction (the `givers` list).
    TICKET-0111 (BRIEF-0111-C): `quest_state` replaces `quest_completed`;
-   `item_held` and `vital_status` are new. `column: 'none'` is a form with
-   no target (`NO_TARGET_TYPES`); `values: true` a form that compares to a
-   value, its choices in `choices.form_values[form]`. */
+   `item_held` is new; `values: true` a form that compares to a value, its
+   choices in `choices.form_values[form]`. TICKET-0113 (BRIEF-0113-B):
+   `attribute` replaces `vital_status` -- its key is an attribute of
+   `choices.attributes`, and what it compares to depends on that
+   attribute's kind (`attributeOf`): a label, a threshold, or an entity. */
 
 export const REQUIREMENT_FORMS = {
   knowledge: { label: 'Connaît le fait', list: 'facts', column: 'key', threshold: false },
@@ -24,7 +26,7 @@ export const REQUIREMENT_FORMS = {
   has_debt_to: { label: 'A une dette envers', list: 'givers', column: 'entity', threshold: false },
   no_debt_to: { label: 'N’a aucune dette envers', list: 'givers', column: 'entity', threshold: false },
   item_held: { label: 'Possède au moins (objet)', list: 'items', column: 'entity', threshold: true },
-  vital_status: { label: 'Est dans l’état', list: 'none', column: 'none', threshold: false, values: true },
+  attribute: { label: 'Est dans l’état', list: 'attributes', column: 'key', threshold: false },
 };
 
 // `resource`'s key is a label: one currency per world (the ledger has no
@@ -46,10 +48,26 @@ export function blankRequirement() {
   return { type: 'has_met', subject: 'role:doer', target_entity_id: '', target_key: '', threshold: null, value: '' };
 }
 
-/** The subject options: the three roles, then every character. */
-export function subjectOptions(choices) {
+/** The subject options: the three roles, then every character -- or, for
+    an `attribute` (TICKET-0113), every entity of a type it applies to. */
+export function subjectOptions(choices, req) {
   const roles = Object.entries(SUBJECT_ROLES).map(([role, label]) => ({ value: 'role:' + role, label }));
-  return roles.concat((choices?.characters || []).map((c) => ({ value: 'entity:' + c.id, label: c.name })));
+  const attr = req?.type === 'attribute' ? attributeOf(req.target_key, choices) : null;
+  const people = attr
+    ? (choices?.entities || []).filter((e) => !attr.holder_types || attr.holder_types.includes(e.type))
+    : choices?.characters || [];
+  return roles.concat(people.map((c) => ({ value: 'entity:' + c.id, label: c.name })));
+}
+
+/** TICKET-0113: the attribute a row names, from `choices.attributes`. */
+export function attributeOf(key, choices) {
+  return (choices?.attributes || []).find((a) => a.key === key) || null;
+}
+
+/** TICKET-0113: what an `entity` attribute's value may name. */
+export function attributeTargets(attr, choices) {
+  return (choices?.entities || []).filter((e) => attr.value_types.includes(e.type))
+    .map((e) => ({ value: e.id, label: e.name }));
 }
 
 /** The (value, label) options of a form's picker, from the editor's choices. */
@@ -64,6 +82,7 @@ export function targetOptions(form, choices) {
     case 'factions': return choices.factions.map((c) => ({ value: c.id, label: c.name }));
     case 'givers': return choices.givers.map((c) => ({ value: c.id, label: c.name }));
     case 'items': return choices.items.map((c) => ({ value: c.id, label: c.name }));
+    case 'attributes': return (choices.attributes || []).map((a) => ({ value: a.key, label: a.name }));
     default: return [];
   }
 }
@@ -73,10 +92,22 @@ export function valueOptions(form, choices) {
   return (choices?.form_values?.[form] || []).map((v) => ({ value: v.value, label: v.label }));
 }
 
-/** The request body of one requirement row: only the columns its form uses. */
+/** The request body of one requirement row: only the columns its form uses.
+    An `attribute` row sends its label, threshold or entity as set: the row
+    clears the two its attribute's kind does not use (TICKET-0113). */
 export function requirementBody(req) {
   const form = REQUIREMENT_FORMS[req.type];
   const [kind, id] = (req.subject || 'role:doer').split(':');
+  if (req.type === 'attribute') {
+    return {
+      op: 'leaf', type: req.type,
+      subject_role: kind === 'role' ? id : null, subject_entity_id: kind === 'entity' ? id : null,
+      target_entity_id: req.target_entity_id || null, target_key: req.target_key || null,
+      threshold: req.threshold === '' || req.threshold === null || req.threshold === undefined
+        ? null : Number(req.threshold),
+      value: req.value || null,
+    };
+  }
   return {
     op: 'leaf',
     type: req.type,
diff --git a/scripts/migrate_v2_23_attribute_leaves.py b/scripts/migrate_v2_23_attribute_leaves.py
new file mode 100644
index 0000000..fb8a26a
--- /dev/null
+++ b/scripts/migrate_v2_23_attribute_leaves.py
@@ -0,0 +1,134 @@
+"""Migration v2.23 — the `vital_status` form becomes an `attribute` leaf
+(TICKET-0113, BRIEF-0113-B; decisions WE1 and WG1 of the conditions series).
+
+No table changes. Every `condition_node` leaf of the retired form
+`vital_status` becomes a leaf of the form `attribute` reading the system
+attribute `sys:vital_status`: `form = 'attribute'`, `target_key =
+'sys:vital_status'`; its subject and its `value` (`alive`, `dead`,
+`missing`, `unknown` -- the system attribute's choices) are kept. The
+column `character.vital_status` is untouched: the system attribute reads it
+in place (G3 of the series).
+
+Measured before this lot was written: the production database held no such
+leaf (2026-10-10). The conversion still runs, on any database.
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.22, and refuses -- changing nothing -- when a `vital_status` leaf
+carries a value outside the system attribute's choices or a target.
+
+Idempotent: a second run finds no `vital_status` leaf.
+
+Post-check, before `schema_meta` moves to v2.23: no leaf of the form
+`vital_status` remains.
+
+Run from the project root, after `migrate_v2_22_attributes.py`:
+
+    python scripts/migrate_v2_23_attribute_leaves.py
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+from datetime import UTC, datetime
+from pathlib import Path
+
+SRC = Path(__file__).resolve().parent.parent / "src"
+sys.path.insert(0, str(SRC))
+
+_env = os.environ.get("WORLD_ENGINE_ENV")
+if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
+    print(
+        "migrate_v2_23_attribute_leaves.py refuses to run without WORLD_ENGINE_ENV "
+        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
+        f"{_env or 'unset'}.",
+        file=sys.stderr,
+    )
+    sys.exit(1)
+
+from sqlalchemy import text  # noqa: E402
+from sqlmodel import Session  # noqa: E402
+
+from world_engine import models  # noqa: E402
+from world_engine.attributes import ATTRIBUTE_FORM, system_attribute  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+
+_PREVIOUS_VERSION = "v2.22"
+_THIS_VERSION = "v2.23"
+_RETIRED_FORM = "vital_status"
+_SYSTEM_KEY = "sys:vital_status"
+
+
+def _version_key(version: str) -> tuple[int, int]:
+    major, minor = version.lstrip("v").split(".")
+    return int(major), int(minor)
+
+
+def _refuse_if_behind() -> None:
+    with engine.connect() as conn:
+        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
+    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
+        found = row[0] if row is not None else "no schema_meta row"
+        raise SystemExit(
+            f"Migration v2.23 refused: the database is at {found!r}; run the migrations "
+            f"up to {_PREVIOUS_VERSION} first."
+        )
+
+
+def _convert() -> int:
+    allowed = {value for value, _label in system_attribute(_SYSTEM_KEY).values}
+    with engine.begin() as conn:
+        rows = conn.execute(text(
+            "SELECT id, value, target_key, target_entity_id, threshold FROM condition_node WHERE form = :form"
+        ), {"form": _RETIRED_FORM}).all()
+        for node_id, value, target_key, target_entity_id, threshold in rows:
+            if value not in allowed or target_key or target_entity_id or threshold is not None:
+                raise SystemExit(
+                    f"Migration v2.23 refused: leaf {node_id!r} ({value!r}, {target_key!r}, "
+                    f"{target_entity_id!r}, {threshold!r}) is not a vital_status leaf this migration "
+                    "can convert. Nothing was changed."
+                )
+        conn.execute(text(
+            "UPDATE condition_node SET form = :form, target_key = :key WHERE form = :retired"
+        ), {"form": ATTRIBUTE_FORM, "key": _SYSTEM_KEY, "retired": _RETIRED_FORM})
+    return len(rows)
+
+
+def _post_checks() -> None:
+    with engine.connect() as conn:
+        left = conn.execute(text("SELECT COUNT(*) FROM condition_node WHERE form = :form"),
+                            {"form": _RETIRED_FORM}).scalar()
+    if left:
+        raise SystemExit(f"Migration v2.23 aborted, post-check failed: {left} vital_status leaf(s) remain.")
+    print("Post-check: no vital_status leaf remains.")
+
+
+def _converge_schema_meta() -> None:
+    with Session(engine) as session:
+        row = session.get(models.SchemaMeta, 1)
+        if _version_key(row.static_version) < _version_key(_THIS_VERSION):
+            previous = row.static_version
+            row.static_version = _THIS_VERSION
+            row.updated_at = datetime.now(UTC)
+            session.add(row)
+            print(f"Row: updated schema_meta.id=1: {previous!r} -> {_THIS_VERSION!r}")
+        else:
+            print(f"Row: schema_meta.id=1 already at {row.static_version!r} — nothing to do")
+        session.commit()
+
+
+def main() -> None:
+    print("Migration v2.23 — vital_status leaves become attribute leaves")
+    _refuse_if_behind()
+    converted = _convert()
+    if converted:
+        print(f"Converted: {converted} vital_status leaf(s) -> attribute {_SYSTEM_KEY}.")
+    else:
+        print("No vital_status leaf — nothing to convert.")
+    _post_checks()
+    _converge_schema_meta()
+    print("\nMigration v2.23 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/src/world_engine/attributes.py b/src/world_engine/attributes.py
index 62c12ba..120be25 100644
--- a/src/world_engine/attributes.py
+++ b/src/world_engine/attributes.py
@@ -11,6 +11,8 @@ read the same way here:
   (its kind, its types, its choices, its default), or None.
 - `world_attributes(db, world_id)`    : the system attributes, then the
   world's definitions by name.
+- `view_of(db, key)`                  : the attribute a stored condition leaf
+  names, whatever its world (BRIEF-0113-B).
 - `current_value(db, view, entity)`   : an entity's `StateValue` -- its own
   value, or the default when it holds none (WC1: nothing is written on read).
 - `world_entity_types(db, world_id)`  : the entity types a definition may
@@ -162,6 +164,17 @@ def attribute_view(db: Session, world_id: str, key: Optional[str]) -> Optional[A
     return _definition_view(db, definition)
 
 
+def view_of(db: Session, key: Optional[str]) -> Optional[AttributeView]:
+    """The attribute a stored condition leaf names -- a system key, or a
+    definition of whatever world it belongs to -- or None. For readers that
+    hold a leaf the writer already validated (BRIEF-0113-B)."""
+    spec = system_attribute(key)
+    if spec is not None:
+        return _system_view(spec)
+    definition = db.get(AttributeDefinition, key) if key else None
+    return _definition_view(db, definition) if definition is not None else None
+
+
 def world_attributes(db: Session, world_id: str, include_retired: bool = False) -> tuple[AttributeView, ...]:
     """Every attribute of the world: the system ones, then its definitions
     by name (the retired ones only on request)."""
diff --git a/src/world_engine/condition_forms.py b/src/world_engine/condition_forms.py
index e2b13bf..1894360 100644
--- a/src/world_engine/condition_forms.py
+++ b/src/world_engine/condition_forms.py
@@ -38,6 +38,7 @@ from typing import Callable, Optional
 
 from sqlmodel import Session, func, select
 
+from .attributes import AttributeView, applies_to, current_value, value_label, view_of
 from .models import (
     Agenda,
     Character,
@@ -64,11 +65,15 @@ from .skill_access import held_rank, skill_label
 # `no_debt_to`, creator only as well. Twelve since v2.20 (TICKET-0111,
 # BRIEF-0111-C, S1): `quest_state` replaces `quest_completed` (a quest in
 # any of its four states, `completed` among them), `item_held` and
-# `vital_status` read data the canon already keeps.
+# `vital_status` read data the canon already keeps. Since v2.23
+# (TICKET-0113, BRIEF-0113-B, WE1, WG1): `attribute` reads one attribute of
+# its subject -- a world's definition or a system attribute, `vital_status`
+# among them -- and replaces the `vital_status` form (`attributes.ATTRIBUTE_FORM`
+# names it there, `attribute_conditions.py` AB1 keeps the two equal).
 REQUIREMENT_TYPES: tuple[str, ...] = (
     "knowledge", "relation_gte", "resource", "location_reachable",
     "has_met", "faction_member", "skill_rank_gte", "quest_state",
-    "has_debt_to", "no_debt_to", "item_held", "vital_status",
+    "has_debt_to", "no_debt_to", "item_held", "attribute",
 )
 
 # What `emit_plan`'s parser accepts from the model (TICKET-0108): the four
@@ -81,14 +86,12 @@ MODEL_REQUIREMENT_TYPES: tuple[str, ...] = ("knowledge", "relation_gte", "resour
 ENTITY_TARGET_TYPES: tuple[str, ...] = (
     "relation_gte", "location_reachable", "has_met", "faction_member", "has_debt_to", "no_debt_to", "item_held",
 )
-KEY_TARGET_TYPES: tuple[str, ...] = ("knowledge", "resource", "skill_rank_gte", "quest_state")
+KEY_TARGET_TYPES: tuple[str, ...] = ("knowledge", "resource", "skill_rank_gte", "quest_state", "attribute")
 THRESHOLD_TYPES: tuple[str, ...] = ("relation_gte", "resource", "skill_rank_gte", "item_held")
-# v2.20: a form with no target judges its subject alone; a form with a
-# value compares to one of its own closed set.
-NO_TARGET_TYPES: tuple[str, ...] = ("vital_status",)
-# `character.vital_status` has no CHECK: its values are the creator form's
-# (`cockpit/crud/entities.py`, the character fields' `vital_status` select).
-VITAL_STATUSES: tuple[str, ...] = ("alive", "dead", "missing", "unknown")
+# v2.23 (TICKET-0113, WG1): the forms whose subject may be any entity of
+# the world -- an attribute applies to the types its definition names; every
+# other form judges a character.
+ANY_SUBJECT_TYPES: tuple[str, ...] = ("attribute",)
 # A quest's state is its agenda's (M1 of TICKET-0108); `open` is `active` or
 # `paused`, the player's « en cours ».
 QUEST_STATES: tuple[str, ...] = ("open", "completed", "failed", "abandoned")
@@ -96,7 +99,10 @@ QUEST_STATE_AGENDA_STATUSES: dict[str, tuple[str, ...]] = {
     "open": ("active", "paused"), "completed": ("completed",), "failed": ("failed",),
     "abandoned": ("abandoned",),
 }
-FORM_VALUES: dict[str, tuple[str, ...]] = {"vital_status": VITAL_STATUSES, "quest_state": QUEST_STATES}
+# A form whose `value` is one of a closed set. An `attribute` leaf's value is
+# one of its definition's choices: its writer checks it against the
+# definition, never a set here.
+FORM_VALUES: dict[str, tuple[str, ...]] = {"quest_state": QUEST_STATES}
 
 
 @dataclass(frozen=True)
@@ -129,6 +135,9 @@ class Verdict:
     # TICKET-0097: the player-facing text of `required` when it is an id
     # (a `knowledge` gate's fact); None when `required` is already readable.
     required_label: Optional[str] = None
+    # TICKET-0113 (BRIEF-0113-B, WH1): the leaf reads a hidden attribute --
+    # never written out, nor its state shown, on a player surface.
+    hidden: bool = False
 
 
 
@@ -326,15 +335,60 @@ def _eval_item_held(req: RequirementSpec, character: Character, db: Session, rea
     return Verdict(type=req.type, met=met, current=held, required=threshold, reason=reason, required_label=name)
 
 
-def _eval_vital_status(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
-    """No target: the subject's own `vital_status` equals `value`."""
+def _attribute_required(db: Session, req: RequirementSpec, view: AttributeView) -> object:
+    if view.kind == "choice":
+        return req.value
+    if view.kind == "integer":
+        return req.threshold
+    return req.target_entity_id
+
+
+def _attribute_wanted(db: Session, req: RequirementSpec, view: AttributeView) -> str:
+    """What the leaf asks, in French: a label, « N ou plus », an entity's
+    name, or « quelqu'un » for an `entity` kind that must only be set."""
+    if view.kind == "choice":
+        return value_label(db, view, req.value)
+    if view.kind == "integer":
+        return f"{req.threshold} ou plus"
+    return value_label(db, view, req.target_entity_id) if req.target_entity_id else "quelqu'un"
+
+
+def attribute_unjudged(req: RequirementSpec, holder, db: Session) -> Optional[str]:
+    """Why an `attribute` leaf cannot be judged on `holder` (its subject) --
+    the attribute is gone, or does not apply to its type -- in French; None
+    when it can. `conditions._evaluate_leaf` makes such a leaf `unknown`."""
+    view = view_of(db, req.target_key)
+    entity = db.get(Entity, holder.id)
+    if view is None or entity is None:
+        return "cet état n'existe plus"
+    if not applies_to(view, entity.type):
+        return f"{entity.name} n'a pas l'état « {view.name} »"
+    return None
+
+
+def _eval_attribute(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """`target_key` names an attribute (a definition id or `sys:<name>`);
+    its subject is any entity it applies to (`ANY_SUBJECT_TYPES`). A
+    `choice` is met when the state is the leaf's `value`, an `integer` when
+    it is at least `threshold`, an `entity` when it is `target_entity_id` --
+    or, with no target, when it names anyone. An entity with no value reads
+    the default (WC1). The caller checks `attribute_unjudged` first."""
     del reachable_ids
-    met = character.vital_status == req.value
-    name = _entity_name(db, character.id)
-    reason = (f"{name} is {req.value}" if met
-              else f"prerequisite not met — {name} is {character.vital_status}, not {req.value}")
-    return Verdict(type=req.type, met=met, current=character.vital_status, required=req.value, reason=reason,
-                   required_label=name)
+    view = view_of(db, req.target_key)
+    entity = db.get(Entity, character.id)
+    state = current_value(db, view, entity)
+    if view.kind == "choice":
+        met = state.raw == req.value
+    elif view.kind == "integer":
+        met = isinstance(state.raw, int) and state.raw >= (req.threshold or 0)
+    else:
+        met = state.raw is not None if req.target_entity_id is None else state.raw == req.target_entity_id
+    wanted = _attribute_wanted(db, req, view)
+    current = state.raw if view.kind == "integer" else state.label
+    reason = (f"{entity.name}: {view.name} is {state.label}" if met
+              else f"prerequisite not met — {entity.name}: {view.name} is {state.label}, not {wanted}")
+    return Verdict(type=req.type, met=met, current=current, required=_attribute_required(db, req, view),
+                   reason=reason, required_label=f"{entity.name} — {view.name} : {wanted}", hidden=view.hidden)
 
 
 def _open_debt(db: Session, debtor_id: str, creditor_id: Optional[str]) -> bool:
@@ -381,7 +435,7 @@ _EVALUATORS: dict[str, Callable[[RequirementSpec, Character, Session, object], V
     "has_debt_to": _eval_has_debt_to,
     "no_debt_to": _eval_no_debt_to,
     "item_held": _eval_item_held,
-    "vital_status": _eval_vital_status,
+    "attribute": _eval_attribute,
 }
 
 
diff --git a/src/world_engine/condition_interpreter.py b/src/world_engine/condition_interpreter.py
index e79e535..ca22b68 100644
--- a/src/world_engine/condition_interpreter.py
+++ b/src/world_engine/condition_interpreter.py
@@ -76,7 +76,8 @@ TARGET_HINTS_FR: dict[str, str] = {
     "has_debt_to": "un personnage ou une faction, par son nom",
     "no_debt_to": "un personnage ou une faction, par son nom",
     "item_held": "un objet, par son nom ; seuil = la quantité minimale",
-    "vital_status": "aucune cible ; valeur = l'état vital",
+    "attribute": "un état, par son code a ; valeur = un de ses libellés, seuil = le minimum pour un nombre, "
+                 "cible = une entité par son nom (aucune : quelqu'un)",
 }
 # The forms whose target is a code, and the list each code comes from.
 CODE_LISTS: dict[str, str] = {"knowledge": "f", "quest_state": "q", "skill_rank_gte": "s"}
diff --git a/src/world_engine/condition_text.py b/src/world_engine/condition_text.py
index d239b7d..ba9323a 100644
--- a/src/world_engine/condition_text.py
+++ b/src/world_engine/condition_text.py
@@ -9,9 +9,10 @@ read by the surfaces; neither decides anything. Every phrase comes from
 `conditions.py` CB4.
 
 A player surface passes its character as `viewer_id` (AMENDMENT-0111-01):
-a fact he does not know is never written out (A1, `HIDDEN_FACT_FR`), a leaf
-about someone else shows `?` (V2, `VerdictNode.seen_by`), and no line
-counts another's regard toward him. The creator reads every line whole.
+a fact he does not know is never written out (A1, `HIDDEN_FACT_FR`), nor a
+hidden attribute (WH1 of TICKET-0113, `HIDDEN_STATE_FR`), a leaf about
+someone else shows `?` (V2, `VerdictNode.seen_by`), and no line counts
+another's regard toward him. The creator reads every line whole.
 """
 
 from __future__ import annotations
@@ -20,6 +21,7 @@ from typing import Optional
 
 from sqlmodel import Session
 
+from .attributes import ATTRIBUTE_FORM, value_label, view_of
 from .condition_forms import RequirementSpec
 from .conditions import ConditionTree, VerdictNode
 from .knowledge_resolve import resolve_knowledge_level
@@ -41,13 +43,12 @@ FORM_PHRASES_FR: dict[str, str] = {
     "has_debt_to": "{who} a une dette envers {target}",
     "no_debt_to": "{who} n'a aucune dette envers {target}",
     "item_held": "{who} possède au moins {threshold} × « {target} »",
-    "vital_status": "{who} est {value}",
+    "attribute": "{who} — {target} : {value}",
 }
 
 # The French of a form's value (`condition_forms.FORM_VALUES`), one label per
 # value, kept equal to it by `conditions.py` CC.
 VALUE_LABELS_FR: dict[str, dict[str, str]] = {
-    "vital_status": {"alive": "en vie", "dead": "mort", "missing": "disparu", "unknown": "d'état inconnu"},
     "quest_state": {"open": "en cours", "completed": "accomplie", "failed": "échouée", "abandoned": "abandonnée"},
 }
 
@@ -67,6 +68,10 @@ STATE_MARKS: dict[str, str] = {"met": "✓", "unmet": "✗", "unknown": "?"}
 # still to learn.
 HIDDEN_FACT_FR = "{who} connaît un fait encore caché"
 
+# WH1 (TICKET-0113): what a player reads in place of a leaf on a hidden
+# attribute -- its name and its value are never written out.
+HIDDEN_STATE_FR = "{who} est dans un état encore caché"
+
 # Forms whose progress a player never sees: the count is another's regard.
 HIDDEN_PROGRESS_FORMS: tuple[str, ...] = ("relation_gte",)
 
@@ -83,7 +88,7 @@ def _entity_name(db: Session, entity_id: Optional[str]) -> str:
 
 
 def _target(db: Session, spec: RequirementSpec) -> str:
-    if spec.target_entity_id:
+    if spec.target_entity_id and spec.type != ATTRIBUTE_FORM:
         return _entity_name(db, spec.target_entity_id)
     if spec.type == "knowledge":
         fact = db.get(Fact, spec.target_key) if spec.target_key else None
@@ -93,6 +98,9 @@ def _target(db: Session, spec: RequirementSpec) -> str:
     if spec.type == "quest_state":
         offer = db.get(QuestOffer, spec.target_key) if spec.target_key else None
         return offer.title if offer is not None else str(spec.target_key)
+    if spec.type == ATTRIBUTE_FORM:
+        view = view_of(db, spec.target_key)
+        return view.name if view is not None else str(spec.target_key)
     return str(spec.target_key or "")
 
 
@@ -110,11 +118,33 @@ def leaf_text(db: Session, spec: RequirementSpec, viewer_id: Optional[str] = Non
         raise ValueError(f"condition_text: unknown requirement type {spec.type!r}")
     if spec.type == "knowledge" and viewer_id is not None and not known_to(db, viewer_id, spec.target_key):
         phrase = HIDDEN_FACT_FR
-    value = VALUE_LABELS_FR.get(spec.type, {}).get(spec.value, spec.value)
+    if spec.type == ATTRIBUTE_FORM and viewer_id is not None and _hidden(db, spec):
+        phrase = HIDDEN_STATE_FR
+    value = _value(db, spec)
     text = phrase.format(who=_subject(db, spec), target=_target(db, spec), threshold=spec.threshold, value=value)
     return text[0].upper() + text[1:]
 
 
+def _hidden(db: Session, spec: RequirementSpec) -> bool:
+    view = view_of(db, spec.target_key)
+    return view is None or view.hidden
+
+
+def _value(db: Session, spec: RequirementSpec) -> object:
+    """The French of what a leaf compares to: a form's value label, or an
+    attribute's label, « N ou plus », an entity or « quelqu'un »."""
+    if spec.type != ATTRIBUTE_FORM:
+        return VALUE_LABELS_FR.get(spec.type, {}).get(spec.value, spec.value)
+    view = view_of(db, spec.target_key)
+    if view is None:
+        return spec.value or spec.threshold or ""
+    if view.kind == "choice":
+        return value_label(db, view, spec.value)
+    if view.kind == "integer":
+        return f"{spec.threshold} ou plus"
+    return value_label(db, view, spec.target_entity_id) if spec.target_entity_id else "quelqu'un"
+
+
 def _head(op: str, n: Optional[int]) -> str:
     return CONNECTOR_HEADS_FR[op].format(n=n)
 
diff --git a/src/world_engine/conditions.py b/src/world_engine/conditions.py
index 4a3685b..cddf913 100644
--- a/src/world_engine/conditions.py
+++ b/src/world_engine/conditions.py
@@ -12,7 +12,8 @@ evaluated -- `doer`, the character who acts (the player for a quest or a day
 plan), `giver`, the offer's giver, `contact`, a faction giver's contact --
 or one fixed entity (`subject_entity_id`). A form judges a character; a
 subject that is not one, or a role nothing binds, makes the leaf
-`unknown`, never `met`.
+`unknown`, never `met`. An `attribute` leaf (TICKET-0113) judges any entity
+its attribute applies to; an entity it does not apply to is `unknown`.
 
 A verdict has three states (R1): `met`, `unmet`, `unknown`. The connectors
 follow Kleene's three-valued logic, so an `unknown` leaf can still be
@@ -21,7 +22,8 @@ outweighed (`any` with a met sibling is met). A gate passes only on `met`.
 A player sees a verdict only as his character could (AMENDMENT-0111-01,
 V2): `VerdictNode.seen_by` turns every judged leaf about someone else -- the
 giver, the contact, another character -- into `unknown`, and recombines the
-connectors from what is left. The creator's surfaces read the verdict whole.
+connectors from what is left. A leaf on a hidden attribute (TICKET-0113,
+WH1) is `unknown` to him even about himself. The creator's surfaces read the verdict whole.
 
 This module writes nothing: it reads the canon through the evaluators and
 reads a stored tree back (`read_condition`). Its writer is
@@ -35,7 +37,14 @@ from typing import Optional
 
 from sqlmodel import Session, select
 
-from .condition_forms import _EVALUATORS, RequirementSpec, Verdict, _day_reachable_ids
+from .condition_forms import (
+    _EVALUATORS,
+    ANY_SUBJECT_TYPES,
+    RequirementSpec,
+    Verdict,
+    _day_reachable_ids,
+    attribute_unjudged,
+)
 from .models import Character, Condition, ConditionNode, Entity
 
 # The four connectors, then the leaf.
@@ -117,6 +126,8 @@ class VerdictNode:
         and every connector is recombined from what is left, so no head
         line betrays a hidden leaf."""
         if self.op == "leaf":
+            if self.verdict is not None and self.verdict.hidden:
+                return replace(self, state="unknown", verdict=None, reason=HIDDEN_STATE_REASON_FR)
             if self.verdict is None or _seen_subject(self.spec, viewer_id):
                 return self
             return replace(self, state="unknown", verdict=None, reason=UNSEEN_REASON_FR)
@@ -126,6 +137,9 @@ class VerdictNode:
 
 # V2 (AMENDMENT-0111-01): why a leaf about someone else shows `?` to a player.
 UNSEEN_REASON_FR = "le personnage ne peut pas le vérifier"
+# WH1 (TICKET-0113): why a leaf on a hidden attribute shows `?` to a player,
+# even about himself.
+HIDDEN_STATE_REASON_FR = "c'est un état encore caché"
 
 
 def _seen_subject(spec: Optional[RequirementSpec], viewer_id: str) -> bool:
@@ -356,8 +370,9 @@ def _combine(node: ConditionTree, children: tuple[VerdictNode, ...]) -> str:
 _ROLE_LABELS_FR = {"giver": "le donneur", "contact": "le contact"}
 
 
-def _subject(spec: RequirementSpec, bindings: Bindings, db: Session) -> tuple[Optional[Character], Optional[str]]:
-    """The character a leaf judges, or None and why (in French)."""
+def _subject(spec: RequirementSpec, bindings: Bindings, db: Session) -> tuple[Optional[object], Optional[str]]:
+    """The character a leaf judges -- any entity for a form of
+    `ANY_SUBJECT_TYPES` (TICKET-0113) -- or None and why (in French)."""
     if spec.subject_role == "doer":
         return bindings.doer, None
     if spec.subject_role is not None:
@@ -369,6 +384,9 @@ def _subject(spec: RequirementSpec, bindings: Bindings, db: Session) -> tuple[Op
         entity_id = spec.subject_entity_id
         entity = db.get(Entity, entity_id)
         label = entity.name if entity is not None else "le sujet"
+    if spec.type in ANY_SUBJECT_TYPES:
+        entity = db.get(Entity, entity_id)
+        return (entity, None) if entity is not None else (None, f"{label} n'existe pas")
     character = db.get(Character, entity_id)
     if character is None:
         return None, f"{label} n'est pas un personnage"
@@ -380,6 +398,9 @@ def _evaluate_leaf(spec: RequirementSpec, bindings: Bindings, db: Session, reach
     if evaluator is None:
         raise ValueError(f"unknown requirement type {spec.type!r}")
     character, why = _subject(spec, bindings, db)
+    if character is not None and spec.type in ANY_SUBJECT_TYPES:
+        why = attribute_unjudged(spec, character, db)
+        character = None if why else character
     if character is None:
         return VerdictNode(state="unknown", op="leaf", spec=spec, reason=why)
     ids = None
diff --git a/src/world_engine/day_resolve.py b/src/world_engine/day_resolve.py
index 7478071..6c55626 100644
--- a/src/world_engine/day_resolve.py
+++ b/src/world_engine/day_resolve.py
@@ -276,7 +276,9 @@ _BLOCKED_DETAIL_FR: dict[str, str] = {
     # the label names the quest and the state it must be in.
     "quest_state": "la quête « {required} » n'en est pas là",
     "item_held": "il n'a pas assez de « {required} »",
-    "vital_status": "{required} n'est pas dans l'état voulu",
+    # TICKET-0113 (BRIEF-0113-B, WG1): `attribute` replaces `vital_status`;
+    # its label names the subject, the attribute and the wanted state.
+    "attribute": "« {required} » n'est pas encore le cas",
 }
 
 
@@ -293,13 +295,19 @@ def requirement_detail_fr(verdict: RequirementVerdict) -> str:
 # A1 (AMENDMENT-0111-01): what the player and the narration read for a fact
 # his character does not know, in place of `_BLOCKED_DETAIL_FR["knowledge"]`.
 HIDDEN_KNOWLEDGE_DETAIL_FR = "il lui manque encore un fait à découvrir"
+# WH1 (TICKET-0113): what the player and the narration read for a leaf on a
+# hidden attribute, in place of `_BLOCKED_DETAIL_FR["attribute"]`.
+HIDDEN_STATE_DETAIL_FR = "quelque chose de caché l'en empêche encore"
 
 
 def player_detail_fr(verdict: RequirementVerdict, viewer_id: str, db: Session) -> str:
     """`requirement_detail_fr` as the character `viewer_id` may read it
-    (A1): a `knowledge` leaf names its fact only when he knows it."""
+    (A1): a `knowledge` leaf names its fact only when he knows it; a leaf on
+    a hidden attribute never names it (WH1, TICKET-0113)."""
     if verdict.type == "knowledge" and not known_to(db, viewer_id, verdict.required):
         return HIDDEN_KNOWLEDGE_DETAIL_FR
+    if verdict.hidden:
+        return HIDDEN_STATE_DETAIL_FR
     return requirement_detail_fr(verdict)
 
 
diff --git a/src/world_engine/quest_reads.py b/src/world_engine/quest_reads.py
index 7bb2bfa..598c9b0 100644
--- a/src/world_engine/quest_reads.py
+++ b/src/world_engine/quest_reads.py
@@ -17,6 +17,7 @@ from typing import Optional
 
 from sqlmodel import Session, select
 
+from .attributes import AttributeView, world_attributes
 from .condition_forms import FORM_VALUES
 from .condition_text import VALUE_LABELS_FR, describe, verdict_lines
 from .conditions import evaluate, flat_leaves, node_to_dict, read_condition
@@ -124,7 +125,8 @@ def editor_choices(world_id: str, db: Session) -> dict:
     factions, facts (their text), skills (base domains, then definitions),
     offers; items with their value, the fact reward levels and the world's
     rates (TICKET-0109); each faction's members (TICKET-0110, X1); the
-    values a form compares to (TICKET-0111)."""
+    values a form compares to (TICKET-0111); the world's attributes and its
+    active entities (TICKET-0113)."""
     facts = db.exec(select(Fact).where(Fact.world_id == world_id)).all()
     definitions = db.exec(select(SkillDefinition).where(SkillDefinition.world_id == world_id)).all()
     characters = _named(db, world_id, "character")
@@ -147,6 +149,23 @@ def editor_choices(world_id: str, db: Session) -> dict:
         # TICKET-0111 (S1): the values a form compares to, in French.
         "form_values": {form: [{"value": value, "label": VALUE_LABELS_FR[form][value]} for value in values]
                         for form, values in FORM_VALUES.items()},
+        # TICKET-0113 (BRIEF-0113-B): the attributes an `attribute` leaf may
+        # read, and every active entity -- a leaf's fixed subject, an entity
+        # value.
+        "attributes": [attribute_choice(view) for view in world_attributes(db, world_id)],
+        "entities": sorted(({"id": e.id, "name": e.name, "type": e.type} for e in db.exec(select(Entity).where(
+            Entity.world_id == world_id, Entity.status == "active")).all()),
+            key=lambda d: (d["name"].lower(), d["id"])),
+    }
+
+
+def attribute_choice(view: AttributeView) -> dict:
+    """One attribute as the condition editor lists it (TICKET-0113)."""
+    return {
+        "key": view.key, "name": view.name, "kind": view.kind, "system": view.system, "hidden": view.hidden,
+        "holder_types": list(view.holder_types) if view.holder_types is not None else None,
+        "value_types": list(view.value_types),
+        "choices": [{"value": key, "label": label} for key, label in view.choices],
     }
 
 
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index 46cdf6c..4034795 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.22"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.23"
diff --git a/src/world_engine/writes/conditions.py b/src/world_engine/writes/conditions.py
index 43d804f..0994987 100644
--- a/src/world_engine/writes/conditions.py
+++ b/src/world_engine/writes/conditions.py
@@ -3,9 +3,9 @@ and I1): one `condition` row per owner and role, its tree as
 `condition_node` rows.
 
 - `clean_leaf(...)`        : one leaf against its form -- the form is known,
-  its subject is a role or a character of the world, its target exists in
-  the world and is of the right kind, its threshold and value are in
-  range. Moved here from `goals_agendas._clean_requirement` (TICKET-0108,
+  its subject is a role or a character of the world (any entity an
+  `attribute` applies to, TICKET-0113), its target exists in the world and
+  is of the right kind, its threshold and value are in range. Moved here from `goals_agendas._clean_requirement` (TICKET-0108,
   C-01) and widened to subjects and values.
 - `clean_condition(...)`   : a whole tree, shape (`conditions.check_shape`)
   then every leaf; returns the tree as it will be stored.
@@ -27,10 +27,11 @@ from typing import Optional
 from sqlalchemy import text
 from sqlmodel import Session
 
+from ..attributes import ATTRIBUTE_FORM, applies_to, attribute_view
 from ..condition_forms import (
+    ANY_SUBJECT_TYPES,
     ENTITY_TARGET_TYPES,
     FORM_VALUES,
-    NO_TARGET_TYPES,
     REQUIREMENT_TYPES,
     THRESHOLD_TYPES,
     RequirementSpec,
@@ -86,15 +87,12 @@ def _clean_subject(db: Session, world_id: str, where: str, req: RequirementSpec)
             raise ValueError(f"{where}unknown subject role {req.subject_role!r}")
         return
     subject = db.get(Entity, req.subject_entity_id)
-    if subject is None or subject.world_id != world_id or subject.type != "character":
-        raise ValueError(f"{where}subject {req.subject_entity_id!r} is not a character of this world")
+    wanted = None if req.type in ANY_SUBJECT_TYPES else "character"
+    if subject is None or subject.world_id != world_id or (wanted is not None and subject.type != wanted):
+        raise ValueError(f"{where}subject {req.subject_entity_id!r} is not {'a ' + wanted if wanted else 'an entity'} of this world")
 
 
 def _clean_target(db: Session, world_id: str, where: str, req: RequirementSpec) -> tuple[Optional[str], Optional[str]]:
-    if req.type in NO_TARGET_TYPES:
-        if req.target_entity_id or req.target_key:
-            raise ValueError(f"{where}requirement type {req.type!r} judges its subject alone and takes no target")
-        return None, None
     if req.type in ENTITY_TARGET_TYPES:
         if not req.target_entity_id:
             raise ValueError(f"{where}requirement type {req.type!r} needs a target_entity_id")
@@ -133,6 +131,38 @@ def _clean_value(where: str, req: RequirementSpec) -> Optional[str]:
     return req.value
 
 
+def _clean_attribute(db: Session, world_id: str, where: str, req: RequirementSpec) -> RequirementSpec:
+    """An `attribute` leaf (TICKET-0113, WG1): `target_key` an active
+    attribute of the world -- a definition or a system key --, a fixed
+    subject of a type it applies to; a `choice` compares to one of its
+    choices (`value`), an `integer` to `threshold` (any integer), an
+    `entity` to `target_entity_id` -- an entity of a type its value may
+    name -- or, with none, to anyone."""
+    view = attribute_view(db, world_id, req.target_key)
+    if view is None or view.status != "active":
+        raise ValueError(f"{where}unknown attribute {req.target_key!r}")
+    if req.subject_entity_id is not None and not applies_to(view, db.get(Entity, req.subject_entity_id).type):
+        raise ValueError(f"{where}attribute {view.name!r} does not apply to {req.subject_entity_id!r}")
+    value = threshold = target = None
+    if view.kind == "choice":
+        if req.value not in dict(view.choices):
+            raise ValueError(f"{where}attribute {view.name!r} needs one of its labels, got {req.value!r}")
+        value = req.value
+    elif view.kind == "integer":
+        if not isinstance(req.threshold, int) or isinstance(req.threshold, bool):
+            raise ValueError(f"{where}attribute {view.name!r} needs an integer threshold")
+        threshold = req.threshold
+    elif req.target_entity_id is not None:
+        entity = db.get(Entity, req.target_entity_id)
+        if entity is None or entity.world_id != world_id or entity.type not in view.value_types:
+            raise ValueError(f"{where}attribute {view.name!r} cannot name {req.target_entity_id!r}")
+        target = req.target_entity_id
+    return RequirementSpec(
+        type=req.type, subject_role=req.subject_role, subject_entity_id=req.subject_entity_id,
+        target_entity_id=target, target_key=req.target_key, threshold=threshold, value=value,
+    )
+
+
 def clean_leaf(db: Session, world_id: str, req: RequirementSpec, where: str = "") -> RequirementSpec:
     """One leaf as it will be stored: the arguments its form uses, nothing
     else. `where` prefixes every error (« write_day_plan: step 2 »).
@@ -140,6 +170,8 @@ def clean_leaf(db: Session, world_id: str, req: RequirementSpec, where: str = ""
     if req.type not in REQUIREMENT_TYPES:
         raise ValueError(f"{where}unknown requirement type {req.type!r}")
     _clean_subject(db, world_id, where, req)
+    if req.type == ATTRIBUTE_FORM:
+        return _clean_attribute(db, world_id, where, req)
     target_entity_id, target_key = _clean_target(db, world_id, where, req)
     return RequirementSpec(
         type=req.type, subject_role=req.subject_role, subject_entity_id=req.subject_entity_id,
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 7a2fa4e..87d5690 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19098,6 +19098,43 @@ current value its last row), WE2 (the `vital_status` form kept beside the
 attribute form), WE3 (no system attribute: « détruit » defined twice), WJ1
 (retiring silently breaks conditions), WJ3 (a hard delete).
 
+## A CONDITION READS THE STATE OF THE WORLD (TICKET-0113) -- ONE FORM, `attribute`, ON ANY ENTITY IT APPLIES TO; `vital_status` BECOMES ONE OF ITS SYSTEM ATTRIBUTES (BRIEF-0113-b, schema v2.23)
+
+**WG1.** One form reads every attribute: `attribute`, its `target_key` a
+definition id or a system key. A `choice` compares to one of its labels
+(`value`), an `integer` to a threshold (`threshold`, « N or more », any
+integer), an `entity` to an entity (`target_entity_id`) -- or, with none,
+to anyone. Its subject is any entity the attribute applies to
+(`condition_forms.ANY_SUBJECT_TYPES`): « le pont est détruit » judges the
+bridge. A subject the attribute does not apply to, or a role bound to such
+an entity, makes the leaf `unknown`, never `unmet`. The vocabulary grows by
+data -- a new state is a definition, never a form.
+
+**WE1.** The form `vital_status` is retired: `migrate_v2_23_attribute_leaves.py`
+turns its leaves into `attribute` leaves on `sys:vital_status`, subject and
+value kept (measured on the production database before the lot: none),
+refusing a leaf it cannot convert. The column stays where it is (G3).
+`NO_TARGET_TYPES` and `VITAL_STATUSES` go with it; `FORM_VALUES` keeps
+`quest_state` alone.
+
+**WH1, INV-62.** A leaf on a hidden attribute is `unknown` to a player even
+about his own character (`VerdictNode.seen_by`), written « … est dans un
+état encore caché » (`HIDDEN_STATE_FR`), « quelque chose de caché l'en
+empêche encore » in a blocked step (`HIDDEN_STATE_DETAIL_FR`): neither its
+name nor its value reaches him. `Verdict.hidden` carries it to
+`player_detail_fr`. AMENDMENT-0111-01's A1 and V2 and this rule are one
+invariant, INV-62, in CLAUDE.md.
+
+**The editor.** The offer editor's row lists the world's attributes
+(`editor_choices.attributes`) and, for an attribute, every active entity of
+a type it applies to as a fixed subject (`editor_choices.entities`); what
+it compares to follows the attribute's kind.
+
+**Rejected.** WG2 (two forms, `attribute_is` and `attribute_gte`: the
+vocabulary grows by code), WH2 (V2 alone: « Le personnage est maudit » would
+tell the player), WH3 (a visible attribute readable on others; reactivation:
+TICKET-0114's journal knows who witnessed it, V1's condition).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/attribute_conditions.py b/tooling/verify/checks/attribute_conditions.py
new file mode 100644
index 0000000..df79f8c
--- /dev/null
+++ b/tooling/verify/checks/attribute_conditions.py
@@ -0,0 +1,475 @@
+"""G1 check for TICKET-0113 -- the attribute condition form: a leaf reads any attribute of any entity it applies to, and a player never reads a hidden one.
+
+The lot adds its pieces brief by brief; this check grows with it (the
+`conditions.py` precedent). Each brief adds its rules here in the same
+commit. The attributes themselves are `attributes.py`'s (BRIEF-0113-A).
+
+AB1 -- the form (BRIEF-0113-B, import). `attributes.ATTRIBUTE_FORM` is in
+   `REQUIREMENT_TYPES`, `KEY_TARGET_TYPES` and `ANY_SUBJECT_TYPES`, has an
+   evaluator, a French phrase, a blocked-step detail and an interpreter
+   hint; `vital_status` is in none of them, nor in `FORM_VALUES`; the code's
+   schema version is v2.23 or later.
+AB2 -- the leaf writer (fixture). `write_condition` stores, and
+   `read_condition` returns equal, `attribute` leaves on a world's choice
+   (on the doer), integer (« 3 or more », on a fixed location) and entity
+   definitions (an entity, and anyone, on a fixed item) and on
+   `sys:vital_status` (a fixed character). Refused, each with no row
+   written: an unknown attribute, a retired one, a label of another
+   attribute, an integer leaf with no threshold, an entity value of a type
+   the attribute does not name, a fixed subject of a type it does not apply
+   to. Once a leaf names a definition: retiring it, changing its kind,
+   dropping its label or the type of the leaf's fixed subject are refused
+   (WJ2). `editor_choices` lists every attribute (`key`, `kind`,
+   `choices`) and every active entity with its type.
+AB3 -- evaluation (fixture). On the doer: a choice leaf reads the default
+   before any value, then the value; an integer leaf is met at or above its
+   threshold; an entity leaf is met by the entity named, an empty-target
+   leaf by anyone, and unmet while the value is empty. A leaf whose fixed
+   subject the attribute does not apply to, or `sys:vital_status` on a
+   faction giver, is `unknown` with its French reason, no verdict.
+AB4 -- what a player may read (WH1, fixture). A leaf on a hidden attribute
+   about the PC himself reads `HIDDEN_STATE_FR` and `?` in the PC's
+   `verdict_lines`, its name and label in none of his lines;
+   `blocked_details_fr` and `player_detail_fr` read
+   `HIDDEN_STATE_DETAIL_FR`; the creator's `verdict_lines` writes its name
+   and value; a leaf on a visible attribute about the PC shows its value
+   and its mark to him.
+AB5 -- migration `scripts/migrate_v2_23_attribute_leaves.py`, on a v2.22
+   database holding a `vital_status` leaf (the form as v2.22 stored it):
+   at v2.21 it refuses and changes nothing; with a leaf whose value is not
+   a vital status it refuses and changes nothing; at v2.22 the leaf is an
+   `attribute` leaf on `sys:vital_status`, its subject and value kept,
+   `schema_meta` v2.23; a second run converts nothing.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import os
+import pathlib
+import sqlite3
+import subprocess
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+MIGRATION_V2_23 = ROOT / "scripts" / "migrate_v2_23_attribute_leaves.py"
+
+FAILURES: list[str] = []
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _fresh_db() -> str:
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
+    return db_path
+
+
+def _version_key(version: str) -> tuple[int, int]:
+    major, minor = version.lstrip("v").split(".")
+    return int(major), int(minor)
+
+
+def _count(db, model) -> int:
+    from sqlmodel import func, select
+
+    return db.exec(select(func.count()).select_from(model)).one()
+
+
+def _refused(db, label: str, rule: str, call) -> None:
+    from world_engine import models
+
+    tables = (models.AttributeDefinition, models.AttributeDefinitionType, models.AttributeChoice,
+              models.Condition, models.ConditionNode)
+    before = tuple(_count(db, m) for m in tables)
+    try:
+        call()
+    except ValueError:
+        db.rollback()
+        if tuple(_count(db, m) for m in tables) != before:
+            fail(f"{rule}: {label} was refused after writing a row")
+        return
+    db.rollback()
+    fail(f"{rule}: {label} was accepted")
+
+
+def _spec(**fields):
+    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec
+
+    base = dict(name="Maudit", kind="choice", holder_types=("character", "item"),
+                choices=(ChoiceSpec("non"), ChoiceSpec("oui")), default="non")
+    base.update(fields)
+    if "choices" in fields and fields["choices"] and isinstance(fields["choices"][0], str):
+        base["choices"] = tuple(ChoiceSpec(c) for c in fields["choices"])
+    return DefinitionSpec(**base)
+
+
+def _run_migration(path: pathlib.Path, db_path: str) -> subprocess.CompletedProcess:
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    return subprocess.run([sys.executable, str(path)], env=env, capture_output=True, text=True,
+                          cwd=str(ROOT), timeout=120)
+
+
+# --- AB1 -------------------------------------------------------------------------
+
+def check_ab1() -> None:
+    from world_engine import condition_forms, condition_interpreter, condition_text, day_resolve
+    from world_engine.attributes import ATTRIBUTE_FORM
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+
+    homes = {
+        "REQUIREMENT_TYPES": condition_forms.REQUIREMENT_TYPES,
+        "KEY_TARGET_TYPES": condition_forms.KEY_TARGET_TYPES,
+        "ANY_SUBJECT_TYPES": condition_forms.ANY_SUBJECT_TYPES,
+        "_EVALUATORS": tuple(condition_forms._EVALUATORS),
+        "FORM_PHRASES_FR": tuple(condition_text.FORM_PHRASES_FR),
+        "_BLOCKED_DETAIL_FR": tuple(day_resolve._BLOCKED_DETAIL_FR),
+        "TARGET_HINTS_FR": tuple(condition_interpreter.TARGET_HINTS_FR),
+    }
+    for name, forms in homes.items():
+        if ATTRIBUTE_FORM not in forms:
+            fail(f"AB1: {name} lacks {ATTRIBUTE_FORM!r}")
+        if "vital_status" in forms:
+            fail(f"AB1: {name} still names the vital_status form")
+    if "vital_status" in condition_forms.FORM_VALUES or "vital_status" in condition_text.VALUE_LABELS_FR:
+        fail("AB1: FORM_VALUES or VALUE_LABELS_FR still names vital_status")
+    if _version_key(EXPECTED_STATIC_SCHEMA_VERSION) < (2, 23):
+        fail(f"AB1: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")
+
+
+# --- AB fixture ----------------------------------------------------------------
+
+def _ab_world(engine) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.models import Agenda, AgendaStep, Character, Entity, Faction, Item, Location, World
+    from world_engine.writes.attributes import write_attribute_definition
+
+    with Session(engine) as db:
+        world = World(name="Attributs AB", is_active=False)
+        db.add(world)
+        db.flush()
+        ids = {"world": world.id}
+        for key, kind, name in (("pc", "character", "Millys"), ("npc", "character", "Ysa"),
+                                ("guilde", "faction", "Guilde"), ("trone", "item", "Trône"),
+                                ("crypte", "location", "Crypte")):
+            entity = Entity(world_id=world.id, type=kind, name=name)
+            db.add(entity)
+            db.flush()
+            ids[key] = entity.id
+            if kind == "character":
+                db.add(Character(id=entity.id, world_id=world.id,
+                                 character_type="player" if key == "pc" else "npc"))
+            else:
+                db.add({"faction": Faction, "item": Item, "location": Location}[kind](id=entity.id))
+        agenda = Agenda(world_id=world.id, owner_entity_id=ids["pc"], title="A", change_history=[])
+        db.add(agenda)
+        db.flush()
+        step = AgendaStep(agenda_id=agenda.id, step_order=1, objective="o", status="active", change_history=[])
+        db.add(step)
+        db.flush()
+        ids["step"] = step.id
+        for key, spec in (
+            ("maudit", _spec(name="Maudit", holder_types=("character", "faction"))),
+            ("secret", _spec(name="Marqué", holder_types=("character",), choices=("non", "oui"), default="non",
+                             is_hidden=True)),
+            ("alerte", _spec(name="Alerte", kind="integer", holder_types=("location",), choices=(), default=0)),
+            ("occupe", _spec(name="Occupé par", kind="entity", holder_types=("item",),
+                             value_types=("character",), choices=(), default=None)),
+            ("vieux", _spec(name="Vieux", holder_types=("character",))),
+        ):
+            ids[key] = write_attribute_definition(db, world_id=world.id, spec=spec).id
+        db.commit()
+    return ids
+
+
+def _leaf(**kw):
+    from world_engine.condition_forms import RequirementSpec
+
+    base = {"type": "attribute", "subject_role": "doer"}
+    base.update(kw)
+    if base.get("subject_entity_id"):
+        base["subject_role"] = None
+    return RequirementSpec(**base)
+
+
+def _choice(db, world, key, label):
+    from world_engine.attributes import attribute_view
+
+    return next(k for k, l in attribute_view(db, world, key).choices if l == label)
+
+
+def _ab_tree(db, ids):
+    from world_engine.conditions import all_of
+
+    return all_of([
+        _leaf(target_key=ids["maudit"], value=_choice(db, ids["world"], ids["maudit"], "oui")),
+        _leaf(subject_entity_id=ids["crypte"], target_key=ids["alerte"], threshold=3),
+        _leaf(subject_entity_id=ids["trone"], target_key=ids["occupe"], target_entity_id=ids["npc"]),
+        _leaf(subject_entity_id=ids["trone"], target_key=ids["occupe"]),
+        _leaf(subject_entity_id=ids["npc"], target_key="sys:vital_status", value="alive"),
+    ])
+
+
+def _condition_rows(db) -> tuple[int, int]:
+    from world_engine.models import Condition, ConditionNode
+
+    return _count(db, Condition), _count(db, ConditionNode)
+
+
+def check_ab2(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.conditions import all_of, read_condition
+    from world_engine.quest_reads import editor_choices
+    from world_engine.writes.attributes import ChoiceSpec, set_attribute_status, write_attribute_definition
+    from world_engine.writes.conditions import write_condition
+
+    with Session(engine) as db:
+        world = ids["world"]
+        tree = _ab_tree(db, ids)
+        write_condition(db, world_id=world, role="completion", tree=tree, agenda_step_id=ids["step"])
+        db.commit()
+        if read_condition(db, role="completion", agenda_step_id=ids["step"]) != tree:
+            fail("AB2: the attribute leaves do not read back equal")
+        set_attribute_status(db, world_id=world, definition_id=ids["vieux"], status="retired")
+        db.commit()
+
+        def write(spec):
+            return lambda: write_condition(db, world_id=world, role="prerequisite", tree=all_of([spec]),
+                                           agenda_step_id=ids["step"])
+
+        cases = {
+            "an unknown attribute": _leaf(target_key="sys:humeur", value="x"),
+            "a retired attribute": _leaf(target_key=ids["vieux"], value=_choice(db, world, ids["vieux"], "oui")),
+            "a label of another attribute": _leaf(target_key=ids["secret"],
+                                                  value=_choice(db, world, ids["maudit"], "oui")),
+            "an integer leaf with no threshold": _leaf(subject_entity_id=ids["crypte"], target_key=ids["alerte"]),
+            "an entity value of a type it does not name": _leaf(subject_entity_id=ids["trone"],
+                                                                target_key=ids["occupe"],
+                                                                target_entity_id=ids["guilde"]),
+            "a fixed subject it does not apply to": _leaf(subject_entity_id=ids["crypte"], target_key=ids["maudit"],
+                                                          value=_choice(db, world, ids["maudit"], "oui")),
+        }
+        for label, spec in cases.items():
+            before = _condition_rows(db)
+            try:
+                write(spec)()
+            except ValueError:
+                db.rollback()
+                if _condition_rows(db) != before:
+                    fail(f"AB2: refusing {label} wrote rows")
+                continue
+            db.rollback()
+            fail(f"AB2: write_condition accepts {label}")
+        oui = _choice(db, world, ids["maudit"], "oui")
+        non = _choice(db, world, ids["maudit"], "non")
+        in_use = {
+            "retiring a definition a leaf names": lambda: set_attribute_status(
+                db, world_id=world, definition_id=ids["maudit"], status="retired"),
+            "changing a named definition's kind": lambda: write_attribute_definition(
+                db, world_id=world, definition_id=ids["maudit"], spec=_spec(
+                    name="Maudit", kind="integer", holder_types=("character", "faction"), choices=(), default=0)),
+            "dropping a label a leaf holds": lambda: write_attribute_definition(
+                db, world_id=world, definition_id=ids["maudit"], spec=_spec(
+                    name="Maudit", holder_types=("character", "faction"),
+                    choices=(ChoiceSpec("non", id=non), ChoiceSpec("peut-être")), default="non")),
+            "dropping the type of a leaf's fixed subject": lambda: write_attribute_definition(
+                db, world_id=world, definition_id=ids["alerte"], spec=_spec(
+                    name="Alerte", kind="integer", holder_types=("faction",), choices=(), default=0)),
+        }
+        del oui
+        for label, call in in_use.items():
+            _refused(db, label, "AB2", call)
+        choices = editor_choices(world, db)
+        keys = {a["key"]: a for a in choices.get("attributes", [])}
+        if not {ids["maudit"], ids["alerte"], "sys:vital_status"} <= set(keys) \
+                or keys[ids["alerte"]]["kind"] != "integer" or not keys[ids["maudit"]]["choices"]:
+            fail(f"AB2: editor_choices lists attributes {sorted(keys)}")
+        types = {e["id"]: e["type"] for e in choices.get("entities", [])}
+        if types.get(ids["trone"]) != "item" or types.get(ids["crypte"]) != "location":
+            fail(f"AB2: editor_choices lists entities {types}")
+
+
+def check_ab3(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.conditions import Bindings, evaluate, leaf
+    from world_engine.models import Character
+    from world_engine.writes.attributes import write_attribute_value
+
+    with Session(engine) as db:
+        world = ids["world"]
+        pc = db.get(Character, ids["pc"])
+        oui, non = (_choice(db, world, ids["maudit"], label) for label in ("oui", "non"))
+
+        def state(spec, **bind):
+            return evaluate(leaf(spec), Bindings(doer=pc, **bind), db)
+
+        if state(_leaf(target_key=ids["maudit"], value=non)).state != "met" \
+                or state(_leaf(target_key=ids["maudit"], value=oui)).state != "unmet":
+            fail("AB3: a choice leaf does not read the default before any value")
+        write_attribute_value(db, world_id=world, definition_id=ids["maudit"], entity_id=ids["pc"], value=oui,
+                              kind="changement", changed_by="creator_crud")
+        db.commit()
+        if state(_leaf(target_key=ids["maudit"], value=oui)).state != "met":
+            fail("AB3: a choice leaf does not read the value")
+        alert = _leaf(subject_entity_id=ids["crypte"], target_key=ids["alerte"], threshold=3)
+        if state(alert).state != "unmet":
+            fail("AB3: an integer leaf is met below its threshold")
+        write_attribute_value(db, world_id=world, definition_id=ids["alerte"], entity_id=ids["crypte"], value=3,
+                              kind="changement", changed_by="creator_crud")
+        db.commit()
+        if state(alert).state != "met":
+            fail("AB3: an integer leaf is not met at its threshold")
+        named = _leaf(subject_entity_id=ids["trone"], target_key=ids["occupe"], target_entity_id=ids["npc"])
+        anyone = _leaf(subject_entity_id=ids["trone"], target_key=ids["occupe"])
+        if state(named).state != "unmet" or state(anyone).state != "unmet":
+            fail("AB3: an empty entity value meets a leaf")
+        write_attribute_value(db, world_id=world, definition_id=ids["occupe"], entity_id=ids["trone"],
+                              value=ids["npc"], kind="changement", changed_by="creator_crud")
+        db.commit()
+        if state(named).state != "met" or state(anyone).state != "met":
+            fail("AB3: the entity named does not meet its leaves")
+        for label, node in {
+            "a subject the attribute does not apply to": state(_leaf(
+                subject_entity_id=ids["crypte"], target_key=ids["maudit"], value=oui)),
+            "sys:vital_status on a faction giver": state(_leaf(
+                subject_role="giver", target_key="sys:vital_status", value="alive"), giver_id=ids["guilde"]),
+        }.items():
+            if node.state != "unknown" or node.verdict is not None or "n'a pas l'état" not in (node.reason or ""):
+                fail(f"AB3: {label} is {node.state} ({node.reason!r})")
+
+
+def check_ab4(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine.condition_text import HIDDEN_STATE_FR, verdict_lines
+    from world_engine.conditions import Bindings, all_of, evaluate
+    from world_engine.day_resolve import HIDDEN_STATE_DETAIL_FR, blocked_details_fr, player_detail_fr
+    from world_engine.models import Character
+
+    with Session(engine) as db:
+        world = ids["world"]
+        pc = db.get(Character, ids["pc"])
+        oui = _choice(db, world, ids["secret"], "oui")
+        hidden = evaluate(all_of([_leaf(target_key=ids["secret"], value=oui)]), Bindings(doer=pc), db)
+        lines = verdict_lines(db, hidden, viewer_id=pc.id)
+        texts = " ".join(line["text"] for line in lines)
+        want = HIDDEN_STATE_FR.format(who="le personnage")
+        if not lines or lines[-1]["mark"] != "?" or want[1:] not in texts or "Marqué" in texts:
+            fail(f"AB4: the player reads the hidden leaf as {lines}")
+        creator = " ".join(line["text"] for line in verdict_lines(db, hidden))
+        if "Marqué" not in creator or "oui" not in creator:
+            fail(f"AB4: the creator reads the hidden leaf as {creator!r}")
+        if blocked_details_fr(hidden, db, pc.id) == [] or "Marqué" in " ".join(blocked_details_fr(hidden, db, pc.id)):
+            fail(f"AB4: blocked_details_fr reads {blocked_details_fr(hidden, db, pc.id)}")
+        verdict = hidden.leaf_verdicts()[0]
+        if player_detail_fr(verdict, pc.id, db) != HIDDEN_STATE_DETAIL_FR:
+            fail(f"AB4: player_detail_fr reads {player_detail_fr(verdict, pc.id, db)!r}")
+        maudit_oui = _choice(db, world, ids["maudit"], "oui")
+        visible = evaluate(all_of([_leaf(target_key=ids["maudit"], value=maudit_oui)]), Bindings(doer=pc), db)
+        shown = verdict_lines(db, visible, viewer_id=pc.id)
+        if shown[-1]["mark"] != "✓" or "Maudit" not in shown[-1]["text"]:
+            fail(f"AB4: the player reads a visible leaf about himself as {shown}")
+
+
+# --- AB5 -------------------------------------------------------------------------
+
+def _v222_db_with_leaf(value: str) -> str:
+    from sqlalchemy import create_engine
+    from sqlmodel import Session, SQLModel
+
+    from world_engine.models import Agenda, AgendaStep, Character, Condition, Entity, SchemaMeta, World
+
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "leaves.db")
+    eng = create_engine(f"sqlite:///{db_path}")
+    SQLModel.metadata.create_all(eng)
+    with Session(eng) as db:
+        db.add(SchemaMeta(id=1, static_version="v2.22"))
+        world = World(name="v2.22", is_active=False)
+        db.add(world)
+        db.flush()
+        npc = Entity(world_id=world.id, type="character", name="Garde")
+        db.add(npc)
+        db.flush()
+        db.add(Character(id=npc.id, world_id=world.id, character_type="npc"))
+        agenda = Agenda(world_id=world.id, owner_entity_id=npc.id, title="A", change_history=[])
+        db.add(agenda)
+        db.flush()
+        step = AgendaStep(agenda_id=agenda.id, step_order=1, objective="o", change_history=[])
+        db.add(step)
+        db.flush()
+        condition = Condition(world_id=world.id, role="prerequisite", agenda_step_id=step.id)
+        db.add(condition)
+        db.commit()
+        world_id, condition_id, npc_id = world.id, condition.id, npc.id
+    eng.dispose()
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("INSERT INTO condition_node (id, world_id, condition_id, position, op, form, subject_entity_id, "
+                     "value) VALUES ('leaf-v222', ?, ?, 0, 'leaf', 'vital_status', ?, ?)",
+                     (world_id, condition_id, npc_id, value))
+    return db_path
+
+
+def _leaf_row(db_path: str) -> tuple:
+    with sqlite3.connect(db_path) as conn:
+        row = conn.execute("SELECT form, target_key, subject_entity_id IS NOT NULL, value FROM condition_node "
+                           "WHERE id = 'leaf-v222'").fetchone()
+        version = conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0]
+    return row, version
+
+
+def check_ab5() -> None:
+    db_path = _v222_db_with_leaf("dead")
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("UPDATE schema_meta SET static_version = 'v2.21' WHERE id = 1")
+    result = _run_migration(MIGRATION_V2_23, db_path)
+    if result.returncode == 0 or _leaf_row(db_path)[0][0] != "vital_status":
+        fail(f"AB5: v2.21 was not refused (exit {result.returncode})")
+    bad = _v222_db_with_leaf("asleep")
+    result = _run_migration(MIGRATION_V2_23, bad)
+    if result.returncode == 0 or _leaf_row(bad) != (("vital_status", None, 1, "asleep"), "v2.22"):
+        fail(f"AB5: a leaf that is no vital status was not refused: {_leaf_row(bad)}")
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("UPDATE schema_meta SET static_version = 'v2.22' WHERE id = 1")
+    result = _run_migration(MIGRATION_V2_23, db_path)
+    if result.returncode != 0 or _leaf_row(db_path) != (("attribute", "sys:vital_status", 1, "dead"), "v2.23"):
+        fail(f"AB5: exit {result.returncode}, the leaf is {_leaf_row(db_path)}: {result.stderr.strip()[-200:]}")
+    again = _run_migration(MIGRATION_V2_23, db_path)
+    if again.returncode != 0 or "nothing to convert" not in again.stdout:
+        fail(f"AB5: a second run exit {again.returncode}: {again.stdout.strip()[-200:]}")
+
+
+
+def main() -> int:
+    _fresh_db()
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    ab = _ab_world(engine)
+    for name, rule in (("AB1", check_ab1), ("AB2", lambda: check_ab2(engine, ab)),
+                       ("AB3", lambda: check_ab3(engine, ab)), ("AB4", lambda: check_ab4(engine, ab)),
+                       ("AB5", check_ab5)):
+        try:
+            rule()
+        except Exception as exc:  # a crash is that rule's failure, never a pass
+            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: attribute_conditions -- the attribute form reads a world's attribute or a system one on any "
+          "entity it applies to, replaces vital_status (v2.23), keeps every attribute it names in use, and "
+          "never shows a hidden one to a player")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/attributes.py b/tooling/verify/checks/attributes.py
index 25781d9..397eb1b 100644
--- a/tooling/verify/checks/attributes.py
+++ b/tooling/verify/checks/attributes.py
@@ -1,8 +1,8 @@
 """G1 check for TICKET-0113 -- the state of the world: a world's attributes, one value per entity, its history kept.
 
-The lot adds its pieces brief by brief; this check grows with it (the
-`conditions.py` precedent). Each brief adds its rules here in the same
-commit.
+BRIEF-0113-A's rules; the attribute condition form has its own check,
+`attribute_conditions.py` (BRIEF-0113-B), so each stays inside the
+corpus's per-check time budget.
 
 AA1 -- storage (BRIEF-0113-A, import). The five attribute tables carry
    exactly their contract's columns, CHECK names and index names; no column
diff --git a/tooling/verify/checks/condition_interpreter.py b/tooling/verify/checks/condition_interpreter.py
index 7a94540..7cff513 100644
--- a/tooling/verify/checks/condition_interpreter.py
+++ b/tooling/verify/checks/condition_interpreter.py
@@ -70,7 +70,7 @@ NC2 -- context and form (fixture). `build_context` codes the current
    (`q`); the four base domains then the world's skill (`s`); the current
    tree's entities (`e`); and lists the named entity. A clean tree using
    every connector, a fixed subject, a code target of each list, an entity
-   target, `resource` and `vital_status` encodes to the model's form and
+   target, `resource` and a fixed subject encodes to the model's form and
    reads back, bound and validated, to the same tree. `form_lines` has one
    line per form carrying its phrase.
 NC3 -- interpretation (fixture, `condition_interpreter.chat` stubbed).
@@ -735,7 +735,7 @@ def _full_tree(ids) -> dict:
         {"op": "not", "children": [_leafd("faction_member", target_entity_id=ids["guild"])]},
         {"op": "at_least", "n": 1, "children": [
             _leafd("resource", target_key="monnaie", threshold=30),
-            _leafd("vital_status", subject_role=None, subject_entity_id=ids["garde"], value="alive"),
+            _leafd("has_met", subject_role=None, subject_entity_id=ids["garde"], target_entity_id=ids["tower"]),
             _leafd("location_reachable", target_entity_id=ids["tower"])]},
     ]}
 
diff --git a/tooling/verify/checks/conditions.py b/tooling/verify/checks/conditions.py
index 846bb4c..3598872 100644
--- a/tooling/verify/checks/conditions.py
+++ b/tooling/verify/checks/conditions.py
@@ -53,10 +53,10 @@ CC2 -- the writer (fixture). `write_condition` stores a tree using every
    connector, a role, a fixed subject and a value; `read_condition` returns
    it equal; a second write replaces it whole (the first nodes gone); None
    removes it. Refused, each with no row written: an unknown form, a
-   `quest_state` with no value or an unknown one, a `vital_status` naming a
-   target, an `item_held` aimed at a character, a fixed subject that is a
-   faction, an eligibility on an agenda step, two owners, a `not` with two
-   children.
+   `quest_state` with no value or an unknown one, an `attribute` with a
+   label it does not have, an `item_held` aimed at a character, a fixed
+   subject that is a faction, an eligibility on an agenda step, two owners,
+   a `not` with two children.
 CC3 -- migration `scripts/migrate_v2_20_conditions.py`, on a v2.19-shaped
    database (both requirement tables in their v2.19 DDL, verbatim below)
    holding an offer's eligibility, two rows of an offer step (one
@@ -68,7 +68,8 @@ CC3 -- migration `scripts/migrate_v2_20_conditions.py`, on a v2.19-shaped
    orphan is noted, `schema_meta` is the code's version; a second run
    changes nothing.
 CC4 -- the forms and the consumers (fixture). `item_held` reads the
-   holding, `vital_status` the subject's state, `quest_state` each of its
+   holding, the `sys:vital_status` attribute the subject's state,
+   `quest_state` each of its
    values. `evaluate_agenda_step` on a quest's agenda binds the offer's
    giver; the day's NPC (`_account_rendezvous`) is the target of the first
    `relation_gte` reached through `all`, never one under `any`; `blocked_details_fr` says what an
@@ -579,8 +580,9 @@ def _cc2_round_trip(session, ids) -> None:
         leaf(_spec("item_held", target_entity_id=ids["fur"], threshold=2)),
         ConditionTree(op="any", children=(
             leaf(_spec("has_met", subject_role="giver", target_entity_id=ids["pc"])),
-            ConditionTree(op="not", children=(leaf(_spec("vital_status", subject_role=None,
-                                                         subject_entity_id=ids["other"], value="dead")),)))),
+            ConditionTree(op="not", children=(leaf(_spec("attribute", subject_role=None,
+                                                         subject_entity_id=ids["other"],
+                                                         target_key="sys:vital_status", value="dead")),)))),
         ConditionTree(op="at_least", n=1, children=(
             leaf(_spec("quest_state", target_key=ids["offer"], value="failed")),
             leaf(_spec("has_debt_to", subject_role="contact", target_entity_id=ids["guild"]))))))
@@ -612,8 +614,9 @@ def _cc2_refusals(session, ids) -> None:
                                         one(_spec("quest_state", target_key=ids["offer"]))),
         "a quest_state with an unknown value": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite",
                                                 one(_spec("quest_state", target_key=ids["offer"], value="won"))),
-        "a vital_status naming a target": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite",
-                                           one(_spec("vital_status", target_entity_id=ids["npc"], value="dead"))),
+        "an attribute with a label it does not have": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite",
+                                                       one(_spec("attribute", target_key="sys:vital_status",
+                                                                 value="asleep"))),
         "an item_held aimed at a character": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite",
                                               one(_spec("item_held", target_entity_id=ids["npc"], threshold=1))),
         "a faction as fixed subject": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite",
@@ -807,8 +810,9 @@ def _cc4_forms(session, ids) -> None:
     if not met("item_held", target_entity_id=ids["fur"], threshold=3) or met("item_held", target_entity_id=ids["fur"],
                                                                               threshold=4):
         fail("CC4: item_held does not read the holding of 3")
-    if not met("vital_status", value="alive") or met("vital_status", value="dead"):
-        fail("CC4: vital_status does not read the character's state")
+    if not met("attribute", target_key="sys:vital_status", value="alive") \
+            or met("attribute", target_key="sys:vital_status", value="dead"):
+        fail("CC4: the vital_status attribute does not read the character's state")
     session.add(Quest(world_id=ids["world"], offer_id=ids["offer"], character_id=ids["pc"], agenda_id=ids["agenda"]))
     session.commit()
     for status, value in (("paused", "open"), ("failed", "failed"), ("abandoned", "abandoned")):
diff --git a/tooling/verify/checks/day_plan.py b/tooling/verify/checks/day_plan.py
index 0cfde64..88ccc5e 100644
--- a/tooling/verify/checks/day_plan.py
+++ b/tooling/verify/checks/day_plan.py
@@ -13,7 +13,7 @@ vocabulary is a code-plane property (TICKET-0111, BRIEF-0111-C), held by
 CHECK, which this rule read until v2.19, is gone with its table.)
 R3 (shape groups): every (form, argument) pair of the per-form shape rule
 is in its group constant of `condition_forms.py` -- `ENTITY_TARGET_TYPES`,
-`KEY_TARGET_TYPES`, `THRESHOLD_TYPES`, `NO_TARGET_TYPES` -- the constants
+`KEY_TARGET_TYPES`, `THRESHOLD_TYPES` -- the constants
 the writer checks (the retired `ck_agenda_step_requirement_shape` until
 v2.19).
 R4 (budget derivation): `DAY_BUDGET_SLOTS` is a `len(...)` derivation, never
@@ -205,8 +205,9 @@ EXPECTED_REQUIREMENT_TYPES = (
     # TICKET-0110 (BRIEF-0110-A, G1): ten since v2.19.
     "has_debt_to", "no_debt_to",
     # TICKET-0111 (BRIEF-0111-C, S1): twelve since v2.20; `quest_state`
-    # replaced `quest_completed`.
-    "item_held", "vital_status",
+    # replaced `quest_completed`. TICKET-0113 (BRIEF-0113-B, WG1): `attribute`
+    # replaced `vital_status` at v2.23.
+    "item_held", "attribute",
 )
 EXPECTED_RECONCILE_VERDICTS = ("continue", "modify", "replace")
 EXPECTED_PLAN_ACTIONS = ("continue", "modify", "replace", "resume")
@@ -372,7 +373,7 @@ def check_shape_constraint() -> None:
     if tree is None:
         return
     groups = {}
-    for name in ("ENTITY_TARGET_TYPES", "KEY_TARGET_TYPES", "THRESHOLD_TYPES", "NO_TARGET_TYPES"):
+    for name in ("ENTITY_TARGET_TYPES", "KEY_TARGET_TYPES", "THRESHOLD_TYPES"):
         node = _tuple_assign(tree, name)
         if node is None:
             fail(f"day_plan R3: {_rel(CONDITION_FORMS_FILE)}: {name} not found")
@@ -385,14 +386,14 @@ def check_shape_constraint() -> None:
         ("item_held", "ENTITY_TARGET_TYPES"),
         ("knowledge", "KEY_TARGET_TYPES"), ("resource", "KEY_TARGET_TYPES"),
         ("skill_rank_gte", "KEY_TARGET_TYPES"), ("quest_state", "KEY_TARGET_TYPES"),
+        ("attribute", "KEY_TARGET_TYPES"),
         ("relation_gte", "THRESHOLD_TYPES"), ("resource", "THRESHOLD_TYPES"),
         ("skill_rank_gte", "THRESHOLD_TYPES"), ("item_held", "THRESHOLD_TYPES"),
-        ("vital_status", "NO_TARGET_TYPES"),
     ]
     missing = [pair for pair in required_pairs if pair[0] not in groups[pair[1]]]
     if missing:
         fail(f"day_plan R3: the shape groups miss {missing!r}")
-    targets = groups["ENTITY_TARGET_TYPES"] | groups["KEY_TARGET_TYPES"] | groups["NO_TARGET_TYPES"]
+    targets = groups["ENTITY_TARGET_TYPES"] | groups["KEY_TARGET_TYPES"]
     if targets != set(EXPECTED_REQUIREMENT_TYPES):
         fail(f"day_plan R3: the target groups cover {sorted(targets)!r}, not every form")
 
diff --git a/tooling/verify/checks/quests.py b/tooling/verify/checks/quests.py
index 64e7ff7..44dd274 100644
--- a/tooling/verify/checks/quests.py
+++ b/tooling/verify/checks/quests.py
@@ -9,10 +9,11 @@ QA1 -- vocabulary (BRIEF-0108-A, static and import; since TICKET-0111 the
    forms are `condition_forms`', no table carries their CHECK).
    `REQUIREMENT_TYPES` holds the model's four forms, the creator's four
    (`quest_state` in place of `quest_completed` since v2.20), TICKET-0110's
-   two debt forms and TICKET-0111's two (`conditions.py` owns those);
-   `MODEL_REQUIREMENT_TYPES` is exactly the model's four;
-   `ENTITY_TARGET_TYPES`, `KEY_TARGET_TYPES` and `NO_TARGET_TYPES` partition
-   it and `THRESHOLD_TYPES` is inside it; `day_plan._validate_requirement`
+   two debt forms, TICKET-0111's `item_held` (`conditions.py` owns it) and
+   TICKET-0113's `attribute` in place of `vital_status` (`attributes.py`
+   owns it); `MODEL_REQUIREMENT_TYPES` is exactly the model's four;
+   `ENTITY_TARGET_TYPES` and `KEY_TARGET_TYPES` partition it and
+   `THRESHOLD_TYPES` is inside it; `day_plan._validate_requirement`
    (the model's parser) accepts each model form and refuses every other.
 QA2 -- migration `scripts/migrate_v2_17_quests.py`, on a v2.16-shaped
    database (`agenda_step_requirement` in its v2.16 DDL, verbatim below, no
@@ -72,8 +73,7 @@ QC1 -- the editor's mirror (BRIEF-0108-C, static). `frontend/src/creation/
    questRequirements.js`'s `REQUIREMENT_FORMS` has exactly the keys of
    `condition_forms.REQUIREMENT_TYPES`; its forms with `column: 'entity'` are
    `ENTITY_TARGET_TYPES`, with `column: 'key'` `KEY_TARGET_TYPES`, with
-   `column: 'none'` `NO_TARGET_TYPES`, with `threshold: true`
-   `THRESHOLD_TYPES`, with `values: true` the keys of `FORM_VALUES`.
+   `threshold: true` `THRESHOLD_TYPES`, with `values: true` the keys of `FORM_VALUES`.
 QC2 -- the « Quêtes » tab (static). `tabs.js`'s `quetes` entry mounts the
    `questOffers` island in `creation-quetes` and routes « + Nouvelle quête »
    through `triggerPrimaryAction('questOffers')`; `QuestOffers.svelte`
@@ -108,7 +108,9 @@ CREATOR_FORMS = ("has_met", "faction_member", "skill_rank_gte", "quest_state")
 # TICKET-0110 (BRIEF-0110-A, G1): two more creator-only forms; `debts.py` owns them.
 DEBT_FORMS = ("has_debt_to", "no_debt_to")
 # TICKET-0111 (BRIEF-0111-C, S1): two more; `conditions.py` owns them.
-CONDITION_FORMS = ("item_held", "vital_status")
+# TICKET-0113 (BRIEF-0113-B, WG1): `attribute` replaces `vital_status`;
+# `attributes.py` owns it.
+CONDITION_FORMS = ("item_held", "attribute")
 # QA2 runs the v2.17 migration: the forms it added, the tables it created.
 V217_FORMS = ("has_met", "faction_member", "skill_rank_gte", "quest_completed")
 QUEST_TABLES = ("quest_offer", "quest_offer_step", "quest_offer_requirement", "quest")
@@ -157,11 +159,10 @@ def check_qa1() -> None:
         fail(f"QA1: REQUIREMENT_TYPES is {types}")
     if tuple(condition_forms.MODEL_REQUIREMENT_TYPES) != MODEL_FORMS or not set(MODEL_FORMS) <= set(types):
         fail(f"QA1: MODEL_REQUIREMENT_TYPES is {condition_forms.MODEL_REQUIREMENT_TYPES}")
-    entity, key, none = (set(condition_forms.ENTITY_TARGET_TYPES), set(condition_forms.KEY_TARGET_TYPES),
-                         set(condition_forms.NO_TARGET_TYPES))
+    entity, key = set(condition_forms.ENTITY_TARGET_TYPES), set(condition_forms.KEY_TARGET_TYPES)
     threshold = set(condition_forms.THRESHOLD_TYPES)
-    if entity & key or (entity | key) & none or entity | key | none != set(types) or not threshold <= set(types):
-        fail(f"QA1: the shape groups do not partition the vocabulary: {entity}, {key}, {none}, {threshold}")
+    if entity & key or entity | key != set(types) or not threshold <= set(types):
+        fail(f"QA1: the shape groups do not partition the vocabulary: {entity}, {key}, {threshold}")
 
     for form in MODEL_FORMS:
         try:
@@ -804,7 +805,6 @@ def check_qc1() -> None:
     groups = {
         "column: 'entity'": tuple(condition_forms.ENTITY_TARGET_TYPES),
         "column: 'key'": tuple(condition_forms.KEY_TARGET_TYPES),
-        "column: 'none'": tuple(condition_forms.NO_TARGET_TYPES),
         "threshold: true": tuple(condition_forms.THRESHOLD_TYPES),
         "values: true": tuple(f for f in condition_forms.REQUIREMENT_TYPES if f in condition_forms.FORM_VALUES),
     }
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index 0e27a28..806a3b7 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,15 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.23** — TICKET-0113, BRIEF-0113-B: no table change. The condition
+  form `vital_status` is retired: its leaves become `attribute` leaves
+  reading the system attribute `sys:vital_status` (`target_key`), subject
+  and `value` kept. `attribute` reads one attribute of its subject -- any
+  entity the attribute applies to -- and compares it to a label (`value`),
+  an integer (`threshold`, « or more ») or an entity (`target_entity_id`, or
+  none for anyone). `migrate_v2_23_attribute_leaves.py` converts the
+  leaves, refuses a database older than v2.22 and moves `schema_meta` to
+  v2.23.
 - **v2.22** — TICKET-0113, BRIEF-0113-A: the state of the world.
   `attribute_definition` (a world's attribute: its name, its kind --
   `choice`, `integer` or `entity` --, its default, hidden or not, active or
diff --git a/world-engine-schema.md b/world-engine-schema.md
index 6bf1446..c10a9ff 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.22
+Current schema version: v2.23
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -2325,7 +2325,8 @@ One node of a condition's tree (v2.20, O-a: rows, never JSON). A connector
 -- `all`, `any`, `not` (one child), `at_least` (`n` of its children) -- or
 a leaf carrying one form (`condition_forms.REQUIREMENT_TYPES`) and its
 arguments: its subject (a role bound when judged -- `doer`, `giver`,
-`contact` -- or one character, P1), its target (an entity or a key), a
+`contact` -- or one character, P1; any entity for `attribute`, v2.23), its
+target (an entity or a key), a
 threshold, a value. `parent_id` and `position` give the tree its shape; the
 root has no parent. No CHECK names a form: the vocabulary is a code-plane
 property (the `entity_trait.trait_key` precedent), held by the one writer,
@@ -2337,8 +2338,11 @@ currency per world, `target_key` a label); `has_met` an encounter row;
 `quest_state` a quest taken from the offer `target_key` whose agenda is in
 `value` (`open`, `completed`, `failed`, `abandoned`); `has_debt_to` /
 `no_debt_to` an open debt toward the target or none; `item_held` at least
-`threshold` of the item held; `vital_status` the subject's own
-`vital_status` equal to `value`. THE POSITIONAL WALL holds:
+`threshold` of the item held; `attribute` (v2.23, replacing
+`vital_status`) one attribute of its subject, `target_key` a definition id
+or a system key (`sys:vital_status`, `sys:status`, `sys:magic_status`):
+equal to the choice `value`, at least `threshold` for an integer, equal to
+`target_entity_id` for an entity -- or set, with none. THE POSITIONAL WALL holds:
 `location_reachable`'s target lives on the leaf, never on `agenda_step`.
 
 ```sql
````

2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. Regenerate: `python tooling/glue/gen_decisions_index.py`.
4. Regenerate: `python tooling/glue/gen_file_map.py`.
5. Commit as one commit: `BRIEF-0113-B: the attribute condition form -- any entity, system attributes, hidden from the player (schema v2.23)`.

## Scope OUT

- `MODEL_REQUIREMENT_TYPES` and the day plan's model forms (unchanged: four).
- The `character.vital_status` column, its creator field, its writer (G3).
- Création's États tab and sheet panel (BRIEF-0113-C); the interpreter's `a` list (BRIEF-0113-D).
- Any assembler reading attributes (WL1); a visible attribute readable by a player about others (WH3).

## Invariants to defend

**INV-62 (new)** -- a player surface shows a leaf on a hidden attribute as `?`, never its name nor its value, even about his own character (AB4, `conditions.py`). **Schema is authoritative** -- the three version places move together; v2.23 has no DDL. **History is sacred / no silent loss** -- the migration refuses a leaf it cannot convert rather than dropping it (AB5). **A gate passes only on `met`** -- an attribute that does not apply, or is gone, is `unknown` (AB3). **The built frontend is committed and fresh** (`frontend_build_fresh.py`).

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain (R-21 aside).
- A named mutation does not turn its rule red.
- `day_plan.py`, `quests.py` or `conditions.py` turns red on a rule the diff does not edit.
- `claude_md_contract.py` refuses INV-62 for a budget reason: STOP (escalate -- CLAUDE.md is TICKET-0117's).

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- An invariant id above INV-61 was taken since (another ticket): take the next free id, update the two places this diff names INV-62 (`CLAUDE.md`, the decision entry), report it.
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
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/attribute_conditions.py` -> `PASS: attribute_conditions -- the attribute form reads a world's attribute or a system one on any entity it applies to, replaces vital_status (v2.23), keeps every attribute it names in use, and never shows a hidden one to a player`
- `attributes.py`, `conditions.py`, `quests.py`, `day_plan.py`, `condition_interpreter.py`, `claude_md_contract.py`, `schema_version_agreement.py`, `schema_partition.py`, `frontend_build_fresh.py`, `file_map.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`attribute_conditions.py` exits 1 with the rule named):
  - in `src/world_engine/day_resolve.py`, `    "attribute": "« {required} » n'est pas encore le cas",` -> `    "vital_status": "« {required} » n'est pas encore le cas",` -> `AB1`
  - in `src/world_engine/writes/conditions.py`, `    if view is None or view.status != "active":` -> `    if view is None:` -> `AB2`
  - in `src/world_engine/quest_reads.py`, `        "attributes": [attribute_choice(view) for view in world_attributes(db, world_id)],` -> `        "attributes": [],` -> `AB2`
  - in `src/world_engine/conditions.py`, `        why = attribute_unjudged(spec, character, db)` -> `        why = None` -> `AB3`
  - in `src/world_engine/conditions.py`, `            if self.verdict is not None and self.verdict.hidden:` -> `            if False:` -> `AB4`
  - in `scripts/migrate_v2_23_attribute_leaves.py`, `            "UPDATE condition_node SET form = :form, target_key = :key WHERE form = :retired"` -> `            "UPDATE condition_node SET form = :form WHERE form = :retired AND :key IS NOT NULL"` -> `AB5`
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 149/149 (outside 20:00-24:00 Toronto, R-21).
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Schema v2.23 (data only): `world-engine-schema.md` (header, `condition_node`'s forms) and the changelog -- in the diff. `CLAUDE.md`: INV-62 -- in the diff. Decision entry « A CONDITION READS THE STATE OF THE WORLD (TICKET-0113) -- ONE FORM, `attribute`, ON ANY ENTITY IT APPLIES TO; `vital_status` BECOMES ONE OF ITS SYSTEM ATTRIBUTES (BRIEF-0113-b, schema v2.23) » -- in the diff.
