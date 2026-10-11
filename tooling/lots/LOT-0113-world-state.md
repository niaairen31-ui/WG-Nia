# LOT — TICKET-0113 "The state of the world: attributes a creator defines, one value per entity with its history, read by one condition form and proposed by the interpreter"

## Objective and cut

What the canon could not say -- the door is open, the bridge destroyed, the
throne occupied by Ysa -- becomes an ATTRIBUTE the creator defines in her
world (B1, G1 of the series): a definition per idea, with its kind (WA3:
`choice`, `integer`, `entity`), the entity types it applies to (WB2), a
default read for an entity holding no value (WC1), and a history row per
change, `correction` or `changement`, her choice every time (WD1). The
states the canon already keeps -- `character.vital_status`, `entity.status`,
`location.magic_status` -- are SYSTEM attributes, read in place (WE1, G3).

A condition reads any attribute through one form, `attribute` (WG1), on any
entity the attribute applies to; the form `vital_status` is retired into it
(v2.23). A hidden attribute (WH1) is never written out to a player
(INV-62). The creator defines and values attributes in Création › États and
on every sheet (WI1); nothing in use is taken away (WJ2). The interpreter
reads the world's attributes in one more coded list (`a`) and, when one is
missing, proposes its definition with the condition (WK2): she confirms
both together, a name near an existing attribute's offers that one, and the
offer's « Enregistrer » writes the definition and the condition in one
transaction, by the same writers (WN2).

The lot stops before: any assembler reading attributes (WL1 -- the MJ
context's injection of the non-hidden states is TICKET-0114's first point);
who witnessed a change (WH3, TICKET-0114); adding a missing label to an
existing attribute from the interpreter (deferred); `item.condition` (WF1);
any change to Play, `legacy.html`, the day chain's model forms
(`MODEL_REQUIREMENT_TYPES`), the Lore panel.

## Briefs in this lot

- **A — the store, v2.22** (schema v2.22,
  `BRIEF-0113-A-attribute-store.md`): `models/canon_attribute.py` (five
  tables), `attributes.py` (reads, system attributes), `writes/attributes.py`
  (the one writer), `migrate_v2_22_attributes.py`, the world cascade, the
  canon-write policy, the schema docs; check `attributes.py` (AA1-AA7).
- **B — the condition form, v2.23** (schema v2.23,
  `BRIEF-0113-B-attribute-form.md`): `attribute` replaces `vital_status` in
  `condition_forms.py`; any-entity subject, `unknown` off its types, the
  hidden verdict (`seen_by`, INV-62 in CLAUDE.md); French text; the writer's
  `_clean_attribute`; the editor's choices and row;
  `migrate_v2_23_attribute_leaves.py`; check `attribute_conditions.py`
  (AB1-AB5); `conditions.py`, `quests.py`, `day_plan.py`,
  `condition_interpreter.py` follow the vocabulary.
- **C — Création** (no schema change, `BRIEF-0113-C-states-ui.md`): routes
  `cockpit/routes/attributes.py`; the « États » tab, the sheet's panel, the
  shared `AttributeDefinitionForm`; near names confirmed
  (`lore_resolve.near_ratio` extracted, `attributes.near_attributes`);
  AC1-AC3 in `attributes.py`.
- **D — the interpreter reads the states** (no schema change,
  `BRIEF-0113-D-interpreter-attributes.md`): the `a` list, the `attribute`
  leaf in the model's form, a label read back; the prompt as fragments
  (`seed_pilot.CONDITION_INTERPRET_FRAGMENTS`) and
  `apply_ticket_0113_condition_prompt.py`; check `attribute_interpreter.py`
  (AD1-AD4).
- **E — the interpreter proposes a missing state** (no schema change,
  `BRIEF-0113-E-proposed-attributes.md`): `attribute_proposals.py`; the
  model's `define` block; the proposal card (same form as C), near names
  picked; unsaved definitions in the offer draft, written by the offer's
  save (WN2); the journal's `definitions`; AE1-AE3 in
  `attribute_interpreter.py`.

## Dependency graph

Strictly sequential, A -> B -> C -> D -> E.

- B reads A's views (`view_of`, `current_value`, `applies_to`, C-02) and
  its migration refuses below v2.22 (A's).
- C writes through A's writer (C-03), lists B's `in_condition` (a leaf of
  form `attribute`, C-04), and its sheet panel uses A's `entity_states`.
- D codes A's `world_attributes` (C-02) and writes B's leaf (C-04).
- E reuses C's `AttributeDefinitionForm` and `definition_spec` (C-06), C's
  `near_attributes` (C-07), D's context and fragments (C-08), A's
  `clean_definition` / `write_attribute_definition` (C-03), B's
  `clean_leaf` (C-04).
- Textual chaining makes the order strict anyway: every brief appends to
  `tooling/standards/ARCHITECTURE_DECISIONS.md`; A, C extend
  `tooling/verify/checks/attributes.py`; D, E
  `tooling/verify/checks/attribute_interpreter.py`; B, D, E
  `condition_interpreter.py` (module and check); B and E
  `questRequirements.js`; D and E `seed_pilot.py`.

## RECON

Opened on `main` at `d9230a7` (merge of PR #144, `ticket/0117`), schema
v2.21, next id `0113` (Nia's). Then prototyped on a copy (branch
`proto/0113`): `main` ran the full corpus green (147/147,
`WORLD_ENGINE_ENV=test`, before 20:00 Toronto: R-21); every brief's commit
ran it green, the new checks counted; every named mutation of every brief
turns its check red on its rule. The migrations and the prompt script ran
on a read-only copy of Nia's production database (R-04). Findings tagged
[M] were measured. Line numbers are `main`'s.

### R-01 — the canon already keeps three states, and an item's wear [M]
Opened: `src/world_engine/models/canon.py:117` (`Entity`), `:126` (`type`),
`:133` (`status`), `:143` (`Character`), `:168` (`vital_status`), `:206`
(`Location`), `:215` (`magic_status`), `:549` (`Item`), `:554`
(`condition`). Vocabularies: `src/world_engine/cockpit/crud/entities.py:117`
(`ENTITY_STATUSES`), `:128` (`ENTITY_TYPE_REGISTRY`), `:139`
(`vital_status` select), `:157` (`magic_status` select) -- no CHECK on any.
Consequence: three system attributes, `sys:vital_status`, `sys:status`,
`sys:magic_status`, read in place, their values the creator forms' (AA4
keeps them equal); never copied (G3), never written by the attribute
writer. `item.condition` untouched (WF1).

### R-02 — the entity types of a world [M]
Opened: `src/world_engine/models/canon.py:870-890` (`EntityType`:
`world_id`, `slug` unique per world NOCASE, `status` in
`active` / `retired` / `quarantined`); the built-in four are
`ENTITY_TYPE_REGISTRY`'s keys (`cockpit/crud/entities.py:128`), a runtime
type's entities carry its slug in `entity.type`.
Consequence: a definition's types are the built-in four then the world's
active runtime types (`attributes.world_entity_types`); AA4 keeps the
built-in list equal to the registry.

### R-03 — a change is `correction` or `changement` since TICKET-0105 [M]
Opened: `src/world_engine/writes/facts.py:38` (the docstring's two
meanings), `:56` (`FACT_CHANGE_KINDS = ("correction", "changement")`),
`:61-62` (refusal); `src/world_engine/cockpit/crud/facets.py:45`
(`kind: Literal["correction", "changement"]`, required).
Consequence: `ATTRIBUTE_CHANGE_KINDS` is the same pair in the same order
(AA1), required on every value write, never defaulted -- the panel
preselects neither (AC3).

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

### R-13 — Création's registries [M]
Opened: `frontend/src/creation/tabs.js:198` (`CREATION_TABS`), `:352-358`
(`dettes`, the last entry); `frontend/src/creation/registry.js:48`
(`CREATION_ISLANDS`, `origin` `migration` / `new`); `frontend/src/creation/mount.js:27`;
`frontend/src/creation/Creation.svelte:253` (one container per tab);
`frontend/public/creation.css:311` (container sizing);
`frontend/src/creation/Sheet.svelte:94` (child editors imported).
`.claude/rules/frontend.md` INV-49, INV-50, INV-54, INV-55.
Consequence: États is one `CREATION_TABS` entry and one island of origin
`new`, its container sized in `creation.css`; the sheet's panel is a child
of `Sheet.svelte`, never an island.

### R-14 — the canon-write gate names every table and every site [M]
Opened: `tooling/verify/canon_write_policy.txt:1-8` (`[CANON_TABLES]`),
`:65-66` (an allowed site with its reason); `tooling/verify/checks/single_canon_write.py:81`
(the docstring naming each full-replace writer).
Consequence: the five tables join `CANON_TABLES`; the writer's five sites
are allowed with their reason; `_write_types` is named full-replace.

### R-15 — deleting a world deletes its rows [M]
Opened: `src/world_engine/writes/worlds.py:66-77`
(`_DIRECT_WORLD_SCOPED_DELETES`); `tooling/verify/checks/world_cascade.py:67`
(`_FIXTURE`, one row per world-scoped table).
Consequence: every table carries `world_id` (`attribute_value`,
`attribute_change` too: a direct delete, no subquery); the five join the
list and the fixture.

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

### R-17 — the `subject` census [M]
Opened: `tooling/verify/checks/knowledge_identity.py:31-33` (K3: every
`subject` reference in `src/world_engine`, counted per file, equals
`_SUBJECT_CENSUS`), `:109-119`.
Consequence: the side of a definition's types is named `holder` (and
`holder_types`, the parameter `holder`), not `subject` -- a word K3 would
count in four new files. The condition leaf's `subject` is untouched.

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

### R-21 — a pre-existing evening failure [M]
Opened: `tooling/verify/checks/lore_usage.py:888-891` (U12c builds
`--since` from `date.today()`, local, against UTC `created_at`).
Measured: red on `main` from 20:00 to 24:00 Toronto, green otherwise.
Consequence: REPORT-ONLY in every brief; carried forward in the ticket.

### R-22 — an unjudged leaf's reason reaches the player [M]
Added by AMENDMENT-0113-01 (Claude Code's `/review-step` on BRIEF-0113-B).
Opened (after BRIEF-0113-B's diff): `src/world_engine/condition_forms.py`
(`attribute_unjudged`: the reason names the attribute);
`src/world_engine/conditions.py` (`_evaluate_leaf`: an unjudged leaf has no
verdict and carries the reason; `VerdictNode.seen_by`: hides a judged leaf
whose `verdict.hidden`); `src/world_engine/condition_text.py:195-196`
(`_verdict_lines` appends « (reason) »); `src/world_engine/day_resolve.py:336-339`
(`_blocked` the same).
Consequence: a hidden attribute's unjudged reason is
`HIDDEN_STATE_REASON_FR`; AB4 covers the path.

### R-23 — every arrow of a briefed ticket must resolve [M]
Added by AMENDMENT-0113-01.
Opened: `tooling/verify/checks/pipeline_state.py:30-34` (docstring: a
ticket at `brief` or later needs every Machine-checkable arrow to resolve),
`:119-120` (the failure).
Consequence: red from A to C on the arrows to checks a later brief
creates; REPORT-ONLY there, green from D.

## Contract sheet

### C-01 — the five tables (v2.22)
Produced by: BRIEF-0113-A   Consumed by: BRIEF-0113-B to E (through C-02, C-03)
`attribute_definition (id, world_id FK, name, kind, default_integer,
is_hidden, status, created_at, updated_at)`: CHECK kind in
`choice|integer|entity`; CHECK `kind = 'integer' OR default_integer IS
NULL`; CHECK status in `active|retired`; unique
`idx_attribute_definition_name (world_id, name COLLATE NOCASE)`.
`attribute_definition_type (id, world_id, definition_id FK, side,
entity_type)`: CHECK side in `holder|value`; unique (definition_id, side,
entity_type).
`attribute_choice (id, world_id, definition_id FK, label, position,
is_default, status)`: CHECK `is_default = 0 OR status = 'active'`; unique
(definition_id, label NOCASE); partial unique: one default per definition.
`attribute_value (id, world_id, definition_id FK, entity_id FK, choice_id
FK, integer_value, entity_value_id FK, updated_at)`: CHECK at most one of
the three set; unique (definition_id, entity_id); index on entity_id.
`attribute_change (id, world_id, value_id FK, kind, changed_by,
before_choice_id, before_integer, before_entity_id, after_choice_id,
after_integer, after_entity_id, changed_at)`: CHECK kind in
`correction|changement`; INSERT-only.
Constants (`models`): `ATTRIBUTE_KINDS`, `ATTRIBUTE_TYPE_SIDES =
("holder", "value")`, `ATTRIBUTE_STATUSES`, `ATTRIBUTE_CHANGE_KINDS =
("correction", "changement")`.

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

Amended by AMENDMENT-0113-01 (produced by BRIEF-0113-B):
`condition_forms.HIDDEN_STATE_REASON_FR = "c'est un état encore caché"`
(moved from `conditions.py`, which re-exports it by import);
`attribute_unjudged(req, holder, db)` returns it when the attribute is
hidden and does not apply to the holder's type; « cet état n'existe plus »
when the attribute is gone (names nothing either way).

### C-05 — `migrate_v2_23_attribute_leaves.py`
Produced by: BRIEF-0113-B   Consumed by: Nia (live gate)
Refuses below v2.22. Every leaf of form `vital_status` -> form
`attribute`, `target_key` `sys:vital_status`, subject and value kept;
refused (nothing written) when one carries a target, a threshold, or a
value outside the four. Converges `schema_meta` to v2.23. Idempotent.

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

### C-07 — the nearness rule
Produced by: BRIEF-0113-C   Consumed by: C, E
`lore_resolve.near_ratio(target, text) -> Optional[float]` (`target`
already normalized; ratio >= `NEAR_RATIO` or a shared 3+ token);
`near_score(ratio) -> int` (half up). `near_in_surfaces` unchanged in
behaviour (TICKET-0094's Near table still its reference).

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

## Gate output

(a) Property trace -- property -> finding -> declaring file opened.

- three canon states, no CHECK on their values; an item's `condition` -> R-01 -> `src/world_engine/models/canon.py:117-215,549-554`; `src/world_engine/cockpit/crud/entities.py:117-157`
- a world's entity types, slug and status -> R-02 -> `src/world_engine/models/canon.py:870-890`
- the change kinds' pair and order -> R-03 -> `src/world_engine/writes/facts.py:38,56-62`; `src/world_engine/cockpit/crud/facets.py:45`
- a leaf's columns, the connector CHECK, no form CHECK -> R-04 -> `src/world_engine/models/config.py:157-189`
- zero `vital_status` leaves in production -> R-04 -> measured on the copy (2026-10-10)
- the twelve forms, their groups, `NO_TARGET_TYPES`, `VITAL_STATUSES`, `FORM_VALUES`, the evaluator map -> R-05 -> `src/world_engine/condition_forms.py:68-120,329,372`
- `seen_by` and `_seen_subject`; `_subject` returns a character -> R-06 -> `src/world_engine/conditions.py:81-136,326-378`
- one phrase per form; `HIDDEN_FACT_FR`; `leaf_text`'s viewer -> R-07 -> `src/world_engine/condition_text.py:32-68,105`
- blocked details, the player's detail -> R-07 -> `src/world_engine/day_resolve.py:262-298`
- `clean_leaf` and its helpers; `write_condition` -> R-08 -> `src/world_engine/writes/conditions.py:53-171`
- `editor_choices`, `condition_view`; the row's helpers -> R-09 -> `src/world_engine/quest_reads.py:61,122`; `frontend/src/creation/questRequirements.js:15-118`
- the near threshold and scoring -> R-10 -> `src/world_engine/lore_resolve.py:50-51,73,178-`
- the interpreter's lists, context, reading, settling -> R-11 -> `src/world_engine/condition_interpreter.py:67-466`
- the seed's S2 and the prompt head -> R-11 -> `scripts/seed_pilot.py:132,1954,2006,2041,3047`
- the fragment-wise delivery precedent -> R-11 -> `scripts/apply_ticket_0110_link_prompt.py`
- the interpreter routes, the journal's keys and moves, `saved_as_proposed` -> R-12 -> `src/world_engine/cockpit/routes/conditions.py:51-151`; `src/world_engine/writes/condition_drafts.py:34-114`
- the offer save's order, `_mark_drafts` -> R-12 -> `src/world_engine/cockpit/routes/quests.py:53-156`
- tab and island registries, containers, sizing -> R-13 -> `frontend/src/creation/tabs.js:198,352-358`; `frontend/src/creation/registry.js:48`; `frontend/src/creation/Creation.svelte:253`; `frontend/public/creation.css:311`
- canon tables and allowed sites -> R-14 -> `tooling/verify/canon_write_policy.txt:1-8,65-66`; `tooling/verify/checks/single_canon_write.py:81`
- the world cascade's list and fixture -> R-15 -> `src/world_engine/writes/worlds.py:66-77`; `tooling/verify/checks/world_cascade.py:67`
- three version places; a migration's convergence -> R-16 -> `src/world_engine/schema_version.py:15`; `world-engine-schema.md:3`; `world-engine-schema-changelog.md:16`; `scripts/migrate_v2_21_condition_draft.py:54,133-145`
- K3's census -> R-17 -> `tooling/verify/checks/knowledge_identity.py:31-33,109-119`
- `day_plan.py`'s literal vocabulary -> R-18 -> `tooling/verify/checks/day_plan.py:8,162-166,202`
- the per-check timeout -> R-19 -> `tooling/verify/checks/corpus_gate.py:21-28`
- the root invariants after 0117 -> R-20 -> `CLAUDE.md:223`
- U12c's local date -> R-21 -> `tooling/verify/checks/lore_usage.py:888-891`
- an unjudged leaf's reason reaches the player (AMENDMENT-0113-01) -> R-22 -> `src/world_engine/condition_text.py:195-196`; `src/world_engine/day_resolve.py:336-339`
- every arrow of a briefed ticket resolves (AMENDMENT-0113-01) -> R-23 -> `tooling/verify/checks/pipeline_state.py:30-34,119-120`

(b) Case tables.

b-1 -- `clean_definition` (C-03). Evaluated top to bottom; the first row
that applies raises.

| case                                                                 | result                      |
|----------------------------------------------------------------------|-----------------------------|
| kind not in `ATTRIBUTE_KINDS`                                        | ValueError                  |
| holder or value types not a list, or a type not one of the world's   | ValueError                  |
| no holder type                                                       | ValueError                  |
| `entity` kind without value types, or another kind with some         | ValueError                  |
| a non-`choice` kind with labels                                      | ValueError                  |
| `choice`: an empty label, a label twice (normalized), fewer than two, a default not one of them | ValueError |
| empty name, or past 80 characters                                    | ValueError                  |
| name equal (normalized) to a system attribute's or another definition's of the world (retired included) | ValueError |
| `integer` without an integer default                                 | ValueError                  |
| `entity` with a default                                              | ValueError                  |
| update: kind changed while a value or a leaf holds it                | ValueError (WJ2)            |
| update: a holder type dropped that an entity holding a value has     | ValueError (WJ2)            |
| update: a value type dropped that a value names                      | ValueError (WJ2)            |
| update: a label dropped that a value or a leaf holds                 | ValueError (WJ2)            |
| new definition whose choices carry an id                             | ValueError                  |
| otherwise                                                            | the clean spec (default: the label as written in the list) |

A label dropped and held by nothing is retired, never deleted.

b-2 -- an `attribute` leaf's verdict (C-04).

| subject                                     | attribute                       | verdict                    | player (`seen_by`)     |
|---------------------------------------------|---------------------------------|----------------------------|------------------------|
| unbound role / missing entity               | --                              | unknown, why in French     | `?`                    |
| entity of a type it does not apply to       | visible                         | unknown « n'a pas l'état » | `?` and that reason    |
| entity of a type it does not apply to       | hidden (AMENDMENT-0113-01)      | unknown `HIDDEN_STATE_REASON_FR` | `?`; neither name nor label anywhere |
| any                                         | gone (no row: never retired while named, WJ2) | unknown « n'existe plus »  | `?`      |
| applies                                     | choice                          | met iff state = value      | as is, unless hidden   |
| applies                                     | integer                         | met iff state >= threshold | as is, unless hidden   |
| applies                                     | entity, target set              | met iff state = target     | as is, unless hidden   |
| applies                                     | entity, no target               | met iff a value is set     | as is, unless hidden   |
| any                                         | hidden                          | as above                   | `?`, « état encore caché », even for the doer |

An entity with no value reads the default (WC1).

b-3 -- `migrate_v2_23_attribute_leaves.py` (C-05).

| database                                         | result                                             |
|--------------------------------------------------|----------------------------------------------------|
| below v2.22                                      | refused, nothing written                           |
| a `vital_status` leaf with a target / threshold / value outside the four | refused, nothing written   |
| `vital_status` leaves, all convertible           | converted, `schema_meta` -> v2.23                  |
| none (production)                                | 0 converted, `schema_meta` -> v2.23                |
| already v2.23                                    | unchanged                                          |

b-4 -- the state routes (C-06).

| route                  | case                                                  | status / answer                        |
|------------------------|-------------------------------------------------------|----------------------------------------|
| any                    | no active world                                       | 400                                    |
| POST / PUT definition  | a near name, not `confirm_near`, name new or changed  | 200 `{saved: false, near}`, no write   |
| POST / PUT definition  | `clean_definition` refuses                            | 422, rolled back                       |
| PUT definition         | unknown id or another world's                         | 404                                    |
| POST / PUT definition  | otherwise                                             | 200 `{saved: true, attribute}`         |
| status                 | unknown, or retiring one a leaf names                 | 422                                    |
| GET / PUT states       | unknown entity or another world's                     | 404                                    |
| PUT states             | a `sys:` key                                          | 422 `SYSTEM_READ_ONLY`                 |
| PUT states             | a writer refusal (kind missing, value of another type)| 422                                    |
| PUT states             | otherwise (unchanged: nothing written)                | 200 `entity_states`                    |

b-5 -- `apply_ticket_0113_condition_prompt.py`, per fragment (C-08).

| current version holds   | action                                  |
|-------------------------|-----------------------------------------|
| the new text            | already done (looked for first)         |
| the old text            | replaced                                |
| neither                 | reported « edit by hand », others go on |

No change -> « unchanged », nothing written; a change -> one new
`prompt_version` through `write_prompt_version`; the head's variables set
to the seed's first (`write_prompt_variables`). No head -> nothing done.

b-6 -- a proposal carrying a definition (C-09, C-10).

| case                                                                | outcome / status                                  |
|---------------------------------------------------------------------|---------------------------------------------------|
| `define` entry refused by `clean_definition`                        | error, retried once (II1)                         |
| `define` name equal to one already in the draft                     | error « déjà proposé, utilise son code »          |
| a new definition near an existing or unsaved attribute              | needs_choice, the card lists the near ones        |
| resolve: pick `new`                                                 | kept as proposed                                  |
| resolve: pick an existing key, labels fit                           | leaves moved to it, entry kept `adopted`          |
| resolve: pick an existing key lacking a label                       | refused, the attribute's labels named             |
| resolve: pick outside the near list                                 | 422                                               |
| decision `inserted`: definitions ≠ the proposed ones                | 422 « ni plus ni moins »                          |
| decision `inserted`: a retouched definition no longer fits the tree | 422 « La condition ne tient plus »                |
| an unsaved definition that no longer cleans (any route)             | 422 « Un état proposé ne tient plus »             |
| offer save: a tree names one the body lacks                         | 422, nothing written                              |
| offer save: an unsaved definition no tree names                     | not written                                       |
| offer save: otherwise                                               | definitions then offer, one commit; drafts marked |

(c) Enumerations.

1. Who names the form `vital_status` or its constants on `main`
   (`git grep -n "vital_status\|VITAL_STATUSES\|NO_TARGET_TYPES" d9230a7 --
   src tooling/verify frontend/src`, outside the `character` column, the
   creator form and the archived tickets / lots / briefs):
   ```
   src/world_engine/condition_forms.py:71,88,91,99,384
   src/world_engine/condition_interpreter.py:79
   src/world_engine/condition_text.py:44,50
   src/world_engine/day_resolve.py:279
   src/world_engine/writes/conditions.py:33,94
   frontend/src/creation/questRequirements.js:11,27
   tooling/verify/checks/condition_interpreter.py:427,738
   tooling/verify/checks/conditions.py:582,616,810
   tooling/verify/checks/day_plan.py:16,209,375-395
   tooling/verify/checks/quests.py:14,75,111,161,807
   ```
   B's diff edits each.
2. World-scoped tables after A: the five join the end of
   `_DIRECT_WORLD_SCOPED_DELETES` -- `attribute_definition`,
   `attribute_definition_type`, `attribute_choice`, `attribute_value`,
   `attribute_change` -- and `world_cascade.py`'s `_FIXTURE`, one row each.
3. New Python modules: `models/canon_attribute.py`, `attributes.py`,
   `writes/attributes.py` (A); `cockpit/routes/attributes.py` (C);
   `attribute_proposals.py` (E); scripts `migrate_v2_22_attributes.py` (A),
   `migrate_v2_23_attribute_leaves.py` (B),
   `apply_ticket_0113_condition_prompt.py` (D). Each has a docstring
   (`file_map.py`); FILE_MAP.md regenerated by each brief.
4. New checks: `attributes.py` (A), `attribute_conditions.py` (B),
   `attribute_interpreter.py` (D). Corpus 147 on `main` -> 148 (A) -> 149
   (B) -> 150 (D, E).

(d) The family contracts C-02 / C-03 (one reader, one writer for five
tables) were written before their members and re-read after E
(`materialize` writes through `write_attribute_definition`;
`clean_unsaved` cleans through `clean_definition`). ✓

(e) Gates and the modules that satisfy them.

- `attributes.py` (proposed, AA, AC): `models/canon_attribute.py`,
  `attributes.py`, `writes/attributes.py`, `migrate_v2_22_attributes.py`
  (A); `cockpit/routes/attributes.py`, the Svelte files, `lore_resolve.py`
  (C).
- `attribute_conditions.py` (proposed, AB): `condition_forms.py`,
  `conditions.py`, `condition_text.py`, `day_resolve.py`,
  `writes/conditions.py`, `quest_reads.py`,
  `migrate_v2_23_attribute_leaves.py`, the editor row (B).
- `attribute_interpreter.py` (proposed, AD, AE):
  `condition_interpreter.py`, `seed_pilot.py`,
  `apply_ticket_0113_condition_prompt.py` (D); `attribute_proposals.py`,
  `routes/conditions.py`, `routes/quests.py`, `condition_drafts.py`, the
  editor files (E).
- `single_canon_write.py` (passed): the five tables canon, five sites
  allowed, `_write_types` named full-replace (A).
- `world_cascade.py` (passed): the five in the delete list and fixture (A).
- `knowledge_identity.py` (passed): no new `subject` reference (R-17).
- `day_plan.py`, `conditions.py`, `quests.py`, `condition_interpreter.py`
  (passed): their vocabulary rules follow `vital_status` -> `attribute`
  (B); NC1's state note, NE1's needles (D, E).
- `claude_md_contract.py` (passed): INV-62, one new id, its marker naming
  two existing checks (B).
- `schema_partition.py`, `schema_version_agreement.py` (passed): A and B
  move the three places together.
- `json_ui_boundary.py` (passed): no JSON column; `condition_draft.payload`
  (already allowlisted) gains a key, read by no surface.
- `prompt_registry.py` (passed): no new usage; the head's variables are the
  seed's.
- `page_contract.py`, `creation_island.py`, `creation_container_sizing.py`,
  `effect_self_write.py`, `frontend_build_fresh.py` (passed): États is a
  registry entry and an island of origin `new`, its container sized; the
  sheet's panel and the card are children; builds committed (B, C, E).
- `module_budget.py`, `function_length.py` (passed): the largest module,
  `condition_interpreter.py`, is 639 lines and 32 functions (nested
  counted); `writes/attributes.py` 375 lines.
- `file_map.py`, `decisions_index.py` (passed): regenerated by each brief.

## Amendments

- AMENDMENT-0113-01 (BRIEF-0113-B in flight): an unholdable hidden attribute's
  reason names nothing (R-22, C-04, b-2); `pipeline_state.py` red from A to C
  is expected (R-23).
