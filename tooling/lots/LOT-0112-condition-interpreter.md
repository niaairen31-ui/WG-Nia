# LOT — TICKET-0112 "The condition interpreter: a sentence in French becomes a condition tree the creator confirms, journaled for its acceptance rate"

## Objective and cut

The creator writes a condition of a quest offer in French -- « le joueur
possède 15 fourrures de loup ou est membre de la Guilde » -- and gets it
back as a tree she reads in French, inserts into her offer draft or
discards (A1 of the series: the model proposes, code validates, she
confirms). Nested conditions, read-only since TICKET-0111 (T1), are now
written and edited this way (IC1: the current tree goes to the model with
her instruction).

The model never emits an id (ID1a): entities by name, resolved by the
name index under the creator regime (an ambiguity waits for her pick);
facts, quest offers and skills by a code from a list it is shown -- one
coded-list structure, `fact_refs.CodedRefs`, generalized from the fact
list. Code reads the answer back, validates every leaf with the writer's
own rules and keeps every error; one more call carries them to the model
(II1). What the language cannot say yet is listed with where it will come
from (IF1); a cost or a reward is never a condition (IA1).

Every proposal is journaled in `condition_draft` (v2.21, IH1): its
outcome moves one way to `inserted` / `discarded`, then `saved` when the
offer that holds it is saved, with whether it was saved as proposed -- the
acceptance rate of D1 is a query on relational columns.

The lot stops before: costs and rewards from a sentence (IA2) and a whole
offer from one (IA3); a dry-run verdict in the confirmation (IG2); states,
events and time as forms (0113, 0114); the dashboard (0115); any change to
the Lore panel's behaviour, the day chain, the model's four day-plan forms,
`legacy.html`.

## Briefs in this lot

- **A — one coded list, one templated JSON call** (no schema change,
  `BRIEF-0112-A-coded-refs-prompt-call.md`): `CodedFacts` becomes
  `CodedRefs` with `code_refs(prefix, pairs)` (six importers renamed);
  `lore_write_draft._call`'s body moves verbatim to
  `prompt_call.call_json(..., chat)`; `_world_facts` becomes the public
  `world_fact_ids`; check `condition_interpreter.py` created (NA1, NA2).
- **B — the journal, v2.21** (schema v2.21,
  `BRIEF-0112-B-condition-draft-journal.md`): `condition_draft`, its writer
  `writes/condition_drafts.py`, `migrate_v2_21_condition_draft.py`, the
  JSON allowlist, the schema docs; `conditions.py` CC3's table filter
  narrowed (NB1-NB3).
- **C — the interpreter** (no schema change,
  `BRIEF-0112-C-condition-interpreter.md`): `condition_interpreter.py`
  (context, the model's form, reading back, validation, retry, resolve),
  the `condition_interpret` prompt head and registry entry, its delivery
  script; the interpreter added to `name_index.py`'s R5 allow-list and
  `knowledge_identity.py`'s K3 census (NC1-NC4).
- **D — the routes and the save marking** (no schema change,
  `BRIEF-0112-D-interpreter-routes.md`): `cockpit/routes/conditions.py`
  (interpret, resolve, decision), mounted; the offer body names each
  inserted proposal and saving marks it (ND1-ND3).
- **E — the editor** (no schema change,
  `BRIEF-0112-E-interpreter-editor.md`): `ConditionInterpreter.svelte` and
  its state module under every `ConditionEditor`; the drafts carry
  `draftId`; the save sends it; the bundle rebuilt (NE1).

## Dependency graph

Strictly sequential, A -> B -> C -> D -> E.

- C imports A's `CodedRefs`, `code_refs` (C-01) and `prompt_call.call_json`
  (C-02), and `lore_write_draft.world_fact_ids`.
- D writes B's `condition_draft` through B's writer (C-07) with C's
  `Interpretation.payload` (C-04), whose keys are B's `PAYLOAD_KEYS`.
- E calls D's routes (C-06) and sends D's offer-body fields (C-08).
- B before C is a choice, not a dependency: C does not import B. It keeps
  the schema change early and lets C's NC4 count `condition_draft`.
- Textual chaining makes the order strict anyway: every brief extends
  `tooling/verify/checks/condition_interpreter.py` and appends to
  `tooling/standards/ARCHITECTURE_DECISIONS.md`; A and C edit `CLAUDE.md`.

## RECON

Opened on `main` at `c317053` (merge of PR #142, `ticket/0111`), schema
v2.20, `python tooling/glue/next_id.py` -> `0112`. Then prototyped on a copy
(branch `proto/0112`): `main` ran the full corpus green (144/144,
`WORLD_ENGINE_ENV=test`); every brief's commit ran it green (145/145 from
A on, the new check counted); every named mutation of every brief turns
`condition_interpreter.py` red on its rule. Findings tagged [M] were
measured. Line numbers are `main`'s.

### R-01 — the coded fact list [M]
Opened: `src/world_engine/fact_refs.py:32` (`CODE_PREFIX = "f"`),
`:78-93` (`CodedFacts`: `codes`, `lines`, `resolve` tolerating case,
spaces and brackets, `code_of`), `:96-110` (`code_facts`: ids in order,
first occurrence wins, a missing fact skipped, line `f<n> — <text>`).
Importers (enumeration (c) 1): `lore_write_draft.py:31`, `tick_context.py:40`,
`tick_normalize.py:27`, `tick.py:26`, `day_plan.py:38`,
`analyzer_transcript.py:65`; `tooling/verify/checks/knowledge_identity.py:50`
names it in its docstring (its code imports `code_facts` only, `:485`).
Consequence: A renames the class to `CodedRefs` in `fact_refs.py` and its
six importers, adds `code_refs(prefix, pairs)`, and `code_facts` returns
`code_refs("f", ...)` -- same codes, same lines (NA1). No new module.

### R-02 — the Lore draft's model call, and who stubs it [M]
Opened: `src/world_engine/lore_write_draft.py:28` (`from . import llm_parse,
model_exchange, prompt_load`), `:35` (`from .ollama_client import chat`),
`:115-131` (`_call`: `prompt_load.load`, `{name}` replacement,
`model_exchange.begin`, `chat(..., model=spec.model, format="json")`, raw
output kept before `llm_parse.extract_object`).
`tooling/verify/checks/lore_write.py:510` (`original = lwd.chat`, then the
stub assigned to `lwd.chat`), `tooling/verify/checks/lore_usage.py:453-456`
(`_swap(module, stub)`: `module.chat = stub`, applied to `lwd`).
`src/world_engine/prompt_registry.py:278-291` (both Lore writing usages'
call site `src/world_engine/lore_write_draft.py:_call`);
`tooling/verify/checks/prompt_registry.py` rule 2 (docstring `:6-7`, each
`path:function` resolves to a file with that `def`).
Consequence: the shared call takes the client as a parameter and each
caller passes the `chat` it imported, looked up at call time -- the stubs
keep reaching the call; `_call` stays in `lore_write_draft.py` (the
registry's call site) as one `return` of `prompt_call.call_json(...)`.

### R-03 — the prompt loader is fenced to the prompt tables [M]
Opened: `src/world_engine/prompt_load.py:35-43` (`RenderSpec`: plain
strings, `version_id`, `version_number`), `:50-72` (`load`: active head,
current version, `effective_model(template, _author_model())`);
`tooling/verify/checks/lore_isolation.py:671-700` (R15: every `select(` in
`prompt_load.py` names only `PromptTemplate`/`PromptVersion`).
Consequence: the JSON call lives in its own module, `prompt_call.py`, not in
`prompt_load.py`; it calls `prompt_load.load` and adds no `select(`.

### R-04 — one model exchange, and its failure [M]
Opened: `src/world_engine/model_exchange.py:25-37` (`ModelExchange`,
`to_record`), `:40-55` (`begin`: appends when the caller keeps a list),
`:58-64` (`fail`: records the error on the last exchange without one).
Consequence: the interpreter and its route keep exchanges the same way;
`fail` is the route's on `OllamaError` / `LlmParseError` (D).

### R-05 — the Lore draft's context [M]
Opened: `src/world_engine/lore_write_draft.py:43` (`MAX_CODED_FACTS = 200`),
`:68-76` (`named_entity_ids`: the tokenizer's entity tokens, in order),
`:79-85` (`_world_facts`: facts with no participant, relation, event or
law), `:88-102` (`draft_context`: named entities' facts, then world facts,
creator-only excluded via `creator_only_fact_ids`, capped).
`src/world_engine/facet_reads.py:44-55` (`_creator_only_select`: a stored
`unaware`, `is_secret` row of one of the fact's own participants), `:58-63`.
Consequence: C reuses `named_entity_ids`, `MAX_CODED_FACTS` and the world
facts (made public as `world_fact_ids` in A) but builds its own list, with
the current tree's facts first and creator-only facts kept (IE1).

### R-06 — the tree's dict form and shape [M]
Opened: `src/world_engine/conditions.py:42` (`CONNECTORS`), `:46`
(`SUBJECT_ROLES`), `:156-162` (`all_of`), `:165-171` (`leaves`, depth
first), `:187-197` (`flat_leaves`: none, one leaf, or `all` of leaves),
`:225-237` (`_LEAF_KEYS`, `node_to_dict`), `:244-284` (`node_from_dict`: a
leaf naming no subject is `doer`), `:287-323` (`check_shape`: arity,
subject exactly one of role/entity, depth 6, 60 nodes).
Consequence: the proposal is a `ConditionTree`; the route answers its dict
form; a lone leaf is proposed as `all` of it, the shape the list editor
sends back (`conditionBody`, R-14), so an unchanged insert saves as
proposed.

### R-07 — the writer's validation, the judge of a proposal [M]
Opened: `src/world_engine/writes/conditions.py:53-60`
(`_TARGET_ENTITY_TYPE`), `:62-78` (`_clean_target_key`: `knowledge` a fact
of the world, `skill_rank_gte` a base domain or a definition of the world,
`quest_state` an offer of the world, `resource` a label never resolved),
`:81-133` (subject, target, threshold -- 1 to 5 for a rank -- and value),
`:136-148` (`clean_leaf`: one `ValueError`, the first found, prefixed by
`where`), `:151-162` (`clean_condition`: shape, then every leaf).
Consequence: C validates leaf by leaf with `clean_leaf` to keep every error
(II1), then `clean_condition` for the stored form. `resource`'s key is the
editor's constant (R-14).

### R-08 — the forms and their French [M]
Opened: `src/world_engine/condition_forms.py:68-72` (`REQUIREMENT_TYPES`,
twelve), `:81-89` (`ENTITY_TARGET_TYPES`, `KEY_TARGET_TYPES`,
`THRESHOLD_TYPES`), `:92-99` (`NO_TARGET_TYPES`, `VITAL_STATUSES`,
`QUEST_STATES`, `FORM_VALUES`), `:103-117` (`RequirementSpec`);
`src/world_engine/condition_text.py:32-45` (`FORM_PHRASES_FR`), `:49-52`
(`VALUE_LABELS_FR`), `:122-128` (`describe`).
Consequence: the prompt's form lines are generated from these; a hint per
form (`TARGET_HINTS_FR`) is kept equal to `REQUIREMENT_TYPES` by NC1.

### R-09 — name resolution never picks [M]
Opened: `src/world_engine/lore_resolve.py:38-43` (`_CATEGORY_ENTITY_TYPE`,
`CATEGORIES`: person, place, faction, object, other), `:143-174`
(`resolve_named`: `matched` / `ambiguous` with candidates / `unmatched`),
`:217-` (`near_candidates`: display only, creator regime);
`src/world_engine/name_index.py:60` (`CREATOR`).
`src/world_engine/lore_write_draft.py:147-171` (0098's precedent: an
unmatched name retried as `other`, near names shown).
Consequence: C resolves the model's names the same way; ambiguous, or
unmatched with near names, waits for her pick (`needs_choice`); unmatched
with none is an error.

### R-10 — a name surface is an entity's [M]
Opened: `src/world_engine/name_index.py:65-71` (`NameSurface`: `entity_id`,
`entity_type`, `source`, `fact_id`). Importers (enumeration (c) 2): eight.
Consequence: ID1b rejected -- offers and skills are not entities.

### R-11 — the offer API and the editor [M]
Opened: `src/world_engine/cockpit/routes/quests.py:51-58` (`OfferStepBody`),
`:72-84` (`OfferBody`), `:116-137` (`_save_offer`: `node_from_dict` and
`write_quest_offer` inside one `try`, `ValueError` -> rollback and 422, then
`commit`); `src/world_engine/quest_reads.py:61-67` (`condition_view`: tree,
flat rows or None, French lines), `:98-101` (`world_offers`).
`frontend/src/creation/ConditionEditor.svelte:10` (props `cond, choices,
emptyLabel, addLabel`), its locked branch (lines, « Effacer »);
`frontend/src/creation/QuestOffers.svelte:137,160,162` (three
`ConditionEditor`s); `frontend/src/creation/questRequirements.js:32`
(`MONEY_KEY = 'monnaie'`), `:98-109` (`conditionDraft(view)`), `:111-113`
(`blankCondition`), `conditionBody` (locked tree, `all` of the rows, or
null); `frontend/src/creation/questOffers.svelte.js:118-131` (`draftBody`);
`frontend/src/creation/sheetRequest.svelte.js:30-35` (`api`: throws an
`Error` carrying `detail`).
Consequence: nothing new writes an offer; the proposal's view is
`condition_view`'s shape, so `conditionDraft(view)` inserts it; the save
carries one draft id per condition.

### R-12 — the Lore journal is closed by its CHECKs [M]
Opened: `src/world_engine/models/pipeline.py:363-421` (`lore_usage_event`:
`kind` / `step` CHECK on two kinds, outcome CHECK, `payload` JSON, no
`world_id`, `world_ref` + `world_name`); `src/world_engine/lore_usage.py:34-41`
(`attempt_id`: the panel's UUID in canonical form, or a fresh one -- « a
journal id never fails the creator's request »);
`scripts/migrate_v2_13_lore_usage.py` (refuse when behind, idempotent,
zero-row post-check, `schema_meta` converged).
Consequence: IH2 would rebuild a CHECKed table; B creates its own table on
the same posture and reuses `attempt_id` and the migration's shape.

### R-13 — every JSON column is named and justified [M]
Opened: `tooling/verify/checks/json_ui_boundary.py:43-114`
(`JSON_COLUMN_ALLOWLIST`, ending with `LoreUsageEvent.payload`/`.model_calls`
`:112-113`; volet c fails on an unlisted JSON column).
Consequence: B adds `ConditionDraft.payload` and `.model_calls` with their
justification; the dashboard's rate reads relational columns only.

### R-14 — the canon-write gate attributes a write by its expression [M]
Opened: `tooling/verify/checks/single_canon_write.py:359-397` (`resolve`:
a name, a call, `.get(Model, …)`, a chained query, a subscript; not a
conditional expression), docstring `:9-12` and its implementation (an
unattributable site fails).
Consequence: the journal's writer assigns `db.get(ConditionDraft, …)` on a
statement of its own (a `x if y else None` is unattributable).

### R-15 — a check filters the condition tables by prefix [M]
Opened: `tooling/verify/checks/conditions.py:727-746` (`_cc3_state`:
`t.endswith("requirement") or t.startswith("condition")`, `:742`), its
CC3 expectation (exactly `condition`, `condition_node`).
Consequence: `condition_draft` turns CC3 red; B narrows the filter to the
two names, a one-line change named in its Scope IN.

### R-16 — the schema version moves in three places [M]
Opened: `src/world_engine/schema_version.py` (`EXPECTED_STATIC_SCHEMA_VERSION
= "v2.20"`); `world-engine-schema.md:3`; `world-engine-schema-changelog.md:14`
(newest first, `schema_partition.py`); `schema_version_agreement.py`.
Consequence: B bumps all three to v2.21 and documents the table after
`lore_usage_event` (`world-engine-schema.md:1204-1248`).

### R-17 — prompts are seeded from one tuple and delivered by a script [M]
Opened: `scripts/seed_pilot.py:132-187` (`upsert_prompt_template`: a head
created with its v1 text, never touched again -- S2), `:1847-1942`
(`LORE_STATEMENT_TO_PROPOSAL_*`, `LORE_WRITE_PROMPT_HEADS`), `:2934-2935`
(the seed loop); `scripts/apply_ticket_0098_lore_write_prompts.py` (reads
the tuple, embeds no text); `tooling/verify/checks/prompt_registry.py`
rule 1 (seeded usages == registry keys).
Consequence: C adds `CONDITION_INTERPRET_PROMPT_HEADS`, its seed loop,
`apply_ticket_0112_condition_prompt.py` and the registry entry together.

### R-18 — routes are mounted by name, guarded globally [M]
Opened: `src/world_engine/cockpit/app.py:56-70` (route imports), `:125`
(`app.middleware("http")(origin_guard)`: every POST), `:126-144`
(`include_router`); `src/world_engine/cockpit/crud/_shared.py:57-61`
(`_world_id`: 400 when no world is active).
Consequence: D mounts one router; no per-route guard.

### R-19 — the model's failures [M]
Opened: `src/world_engine/ollama_client.py:39` (`OllamaError(RuntimeError)`);
`src/world_engine/llm_parse.py:21` (`LlmParseError(ValueError)`);
`src/world_engine/lore_write_draft.py:44-48` (`WRITE_UNAVAILABLE_MESSAGE`).
Consequence: the route catches both before anything else and journals
them; `LlmParseError` is a `ValueError`, so the route never wraps the
interpreter in a bare `except ValueError`.

### R-20 — skills and offers of a world [M]
Opened: `src/world_engine/models/canon.py:594` (`BASE_SKILL_DOMAINS`),
`:633-655` (`SkillDefinition`: `world_id`, `name`, `base_domain`);
`src/world_engine/models/config.py:130` (`CONDITION_ROLES`).
Consequence: the `s` list is the four domains then the world's
definitions by name; `condition_draft.role` quotes `CONDITION_ROLES`.

### R-21 — CLAUDE.md budgets, measured in characters [M]
Opened: `tooling/verify/checks/claude_md_contract.py:69-71`
(`TOTAL_CHAR_BUDGET = 38_000` on `len(text)`, `MAX_LINE_LENGTH = 100`,
`FILE_STRUCTURE_LINE_BUDGET = 80`); `CLAUDE.md` on `main`: 37 180
characters (37 839 bytes -- the handover's figure), File structure at 80
lines; `:461` (`day_plan.py, condition*.py`), `:473` (`prompt_store.py,
prompt_load.py`). No rule requires every module to be listed (the check's
implementation reads the section's length, its archaeology patterns and
pointer freshness only).
Consequence: A folds `prompt_call.py` into line 473, C extends line 461's
comment; no line added.

### R-22 — two allow-lists name who may use the creator regime and a `subject` [M]
Opened: `tooling/verify/checks/name_index.py:17-22` (R5: `CREATOR` and a
`"creator"` `NameScope` only in the listed files) and `:55-61`
(`CREATOR_ALLOWED`: `name_index.py`, `lore_query.py`,
`lore_mentions_read.py`, `writes/facets.py`, `lore_write_draft.py`);
`tooling/verify/checks/knowledge_identity.py:31-35` (K3: every `subject`
reference -- an attribute, a `"subject"` constant, a `subject=` keyword or
parameter -- counted per file against `_SUBJECT_CENSUS`, « a new reference
is red until someone decides it belongs ») and `:109-116` (four files; the
`zone_promotion.py` entry added by TICKET-0101 with its reason).
Consequence: C adds `condition_interpreter.py` to both, each with its
reason -- the creator regime is ID1a's, the leaf's `subject` key is C-03's
(three references: the reader's `raw.get("subject")`, `encode`'s key, the
`("subject", "target")` pair of `bind`). Found by the prototype's corpus,
not by reading: both lists are decisions, and this lot makes them.

## Contract sheet

### C-01 — `fact_refs.CodedRefs`, `code_refs`, `code_facts`
Produced by: BRIEF-0112-A   Consumed by: BRIEF-0112-C (and the six renamed importers)
Signature: `CodedRefs(codes: dict[str, str], lines: tuple[str, ...])`;
`CodedRefs.resolve(code: object) -> Optional[str]`;
`CodedRefs.code_of(target_id: str) -> Optional[str]`;
`code_refs(prefix: str, pairs: Iterable[tuple[str, str]]) -> CodedRefs`;
`code_facts(db, fact_ids: Iterable[str]) -> CodedRefs`.
Return shape: codes `<prefix><n>`, n from 1, positional; line
`<prefix><n> — <label>`.
Error and empty cases: an empty id is skipped; a repeated id keeps its
first code; `resolve` returns None for a non-string, a code the list did
not show, a code of another prefix; tolerates case, spaces, brackets.
`code_facts` skips an id with no `fact` row. No exception.

### C-02 — `prompt_call.call_json`
Produced by: BRIEF-0112-A   Consumed by: `lore_write_draft._call`, BRIEF-0112-C
Signature: `call_json(db, usage: str, values: dict[str, str], exchanges:
Optional[list[ModelExchange]], chat: Callable[..., str]) -> dict`.
Return shape: the parsed JSON object (`llm_parse.extract_object`).
Error and empty cases: `LlmParseError` on a missing prompt head or an
unparsable reply; whatever `chat` raises (`OllamaError`) propagates. When
`exchanges` is a list, one `ModelExchange` is appended before the call and
its `raw_output` set before parsing.

### C-03 — the model's form of a condition (the answer)
Produced by: BRIEF-0112-C (prompt and reader)   Consumed by: BRIEF-0112-C
Answer: `{"condition": <node> | null, "unsupported": [{"text": str, "kind":
"state" | "event" | "time" | "cost" | "reward" | "other"}]}`.
Node: `{"op": "all" | "any" | "not" | "at_least", "n": int (at_least only),
"children": [<node>, ...]}` or a leaf `{"op": "leaf", "form": <a form of
REQUIREMENT_TYPES>, "subject": "doer" | "giver" | "contact" | {"name",
"kind"} | {"code": "e<n>"}, "target": {"name", "kind"} | {"code": "<e|f|q|s><n>"}
| null, "threshold": int | null, "value": str | null}`.
Targets by form: b-3. A bare string subject that is not a role reads as a
person's name; a bare string target of an entity form as a name of kind
`other`. A missing subject is `doer`. The current tree (IC1) is shown in
this form (`encode`), its entities coded `e`.

### C-04 — `condition_interpreter`: `interpret`, `resolve`, `Interpretation`
Produced by: BRIEF-0112-C   Consumed by: BRIEF-0112-D
Signatures: `interpret(db, world_id: str, role: str, instruction: str,
current: Optional[ConditionTree], exchanges=None) -> Interpretation`;
`resolve(db, world_id: str, pending: dict, mentions: list[dict], notes:
list[str], bindings: dict[str, str]) -> Interpretation`.
`Interpretation(outcome, tree, pending, mentions, notes, errors, retried)`:
`outcome` in `proposed` | `needs_choice` | `refused`; `tree` the clean
`ConditionTree` when `proposed` (a lone leaf as `all` of it), else None;
`pending` the dict form of the read tree, its waiting leaves carrying
`subject_mention` / `target_mention`; `mentions` `[{ref, name, kind,
status: matched | ambiguous | unmatched, entity_id, choices: [{entity_id,
name, type[, score]}]}]`; `notes` French lines (IF1, IA1); `errors` French
or writer messages. `Interpretation.payload(current, bindings=None) ->
dict` with exactly `writes.condition_drafts.PAYLOAD_KEYS` (C-07).
Error cases: `interpret` lets `OllamaError` and `LlmParseError` propagate;
`resolve` raises `ValueError` when a waiting mention has no pick or one
outside its choices. Neither writes. Outcomes: b-1.
Constants: `INTERPRET_USAGE = "condition_interpret"`,
`INTERPRET_UNAVAILABLE_MESSAGE`, `RESOURCE_KEY = "monnaie"`.

### C-05 — the prompt `condition_interpret`
Produced by: BRIEF-0112-C   Consumed by: BRIEF-0112-C, the delivery script
Head: `seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS`, one head, id
`pt-condition-interpret`, usage `condition_interpret`, `world_id` None,
`destination` `local`. Variables, exactly: `role, forms, entities,
tree_entities, facts, offers, skills, current, instruction, errors` --
the keys of `condition_interpreter.prompt_values`. Registry:
`PROMPT_REGISTRY["condition_interpret"]` authoring, not world-scoped,
dry-run capable, call site `src/world_engine/condition_interpreter.py:_call`,
default `_author_model`.

### C-06 — the routes
Produced by: BRIEF-0112-D   Consumed by: BRIEF-0112-E
`POST /api/conditions/interpret` body `{instruction: str, role: str,
current: dict | null, attempt_id: str | null}`;
`POST /api/conditions/drafts/{draft_id}/resolve` body `{bindings: {ref:
entity_id}}`; `POST /api/conditions/drafts/{draft_id}/decision` body
`{decision: "inserted" | "discarded"}`.
Answer (all three): `{draft_id, outcome, view: {tree, flat, lines} | null,
mentions: [the mentions waiting for a pick: not matched, with choices],
notes: [str], errors: [str]}` -- `view` is `quest_reads.condition_view` of
the proposed tree; the decision's answer carries `draft_id` and the new
`outcome` with empty lists.
Statuses: b-5.

### C-07 — `condition_draft` and its writer
Produced by: BRIEF-0112-B   Consumed by: BRIEF-0112-D
Table (v2.21): `id, attempt_id, world_ref, world_name, role, instruction,
outcome, retried, offer_ref, saved_as_proposed, payload, model_calls,
created_at, decided_at`; CHECKs `ck_condition_draft_role` (role in
`CONDITION_ROLES`), `ck_condition_draft_outcome` (the eight outcomes),
`ck_condition_draft_saved` (`offer_ref` and `saved_as_proposed` set exactly
on `saved`); indexes `idx_condition_draft_attempt (attempt_id,
created_at)`, `idx_condition_draft_world (world_ref, created_at)`; no
`world_id`, no FK. `models.CONDITION_DRAFT_OUTCOMES` in CHECK order.
Writer (`writes/condition_drafts.py`): `FIRST_OUTCOMES`,
`CONDITION_DRAFT_MOVES` (b-2), `PAYLOAD_KEYS = {current, pending, mentions,
bindings, proposed, notes, errors}`;
`write_condition_draft(db, *, attempt_id, world_id, role, instruction,
outcome, payload, model_calls, retried=False) -> ConditionDraft`;
`move_condition_draft(db, draft, outcome, payload=None) -> ConditionDraft`;
`mark_draft_saved(db, *, world_id, draft_id, offer_id, tree) -> bool`.
Error cases: `ValueError` before any row for an empty attempt / world /
instruction, an unknown role, a first outcome outside `FIRST_OUTCOMES`, a
payload without exactly `PAYLOAD_KEYS`, a non-list `model_calls`, a move
outside b-2 (and any move to `saved`). `mark_draft_saved` never raises:
b-4. None commits.

### C-08 — the offer body's draft ids
Produced by: BRIEF-0112-D   Consumed by: BRIEF-0112-E
`OfferBody.eligibility_draft_id: Optional[str]`;
`OfferStepBody.prerequisite_draft_id`, `.completion_draft_id:
Optional[str]`. `routes/quests._mark_drafts(body, offer_id, world_id, db)`,
called by `_save_offer` after `write_quest_offer` and before `commit`: for
each given id, the condition as written
(`node_to_dict(clean_condition(node_from_dict(raw)))`) goes to
`mark_draft_saved`. Frontend: a condition draft carries `draftId` (null by
default, the inserted proposal's id), sent as those three fields.

## Gate output

(a) Property trace -- one line per property the lot asserts about code
that exists today: property -> finding -> declaring file opened.

- `CodedFacts`' shape, `resolve` tolerance, `code_facts` ordering and skip -> R-01 -> `src/world_engine/fact_refs.py:32,78-110`
- the six importers of `CodedFacts` -> R-01 -> enumeration (c) 1
- `_call`'s body and imports -> R-02 -> `src/world_engine/lore_write_draft.py:28,35,115-131`
- checks replace `lwd.chat` -> R-02 -> `tooling/verify/checks/lore_write.py:510`; `tooling/verify/checks/lore_usage.py:453-456`
- the registry names `lore_write_draft.py:_call`; rule 2 needs the `def` -> R-02 -> `src/world_engine/prompt_registry.py:278-291`; `tooling/verify/checks/prompt_registry.py` (rule 2's implementation)
- R15 fences `prompt_load.py`'s selects -> R-03 -> `tooling/verify/checks/lore_isolation.py:671-700`
- `RenderSpec` and `load` -> R-03 -> `src/world_engine/prompt_load.py:35-72`
- `begin`, `fail`, `to_record` -> R-04 -> `src/world_engine/model_exchange.py:25-64`
- `MAX_CODED_FACTS`, `named_entity_ids`, `_world_facts`, `draft_context` excludes creator-only -> R-05 -> `src/world_engine/lore_write_draft.py:43,68-102`
- what « creator-only » means -> R-05 -> `src/world_engine/facet_reads.py:44-63`
- connectors, roles, `all_of`, `leaves`, `flat_leaves`, the dict form, the shape -> R-06 -> `src/world_engine/conditions.py:42,46,156-197,225-323`
- `clean_leaf` stops at the first error; per-form target rules; `clean_condition` -> R-07 -> `src/world_engine/writes/conditions.py:53-162`
- the twelve forms, their groups, values; `RequirementSpec` -> R-08 -> `src/world_engine/condition_forms.py:68-117`
- one phrase per form; value labels; `describe` -> R-08 -> `src/world_engine/condition_text.py:32-52,122-128`
- `resolve_named`'s three verdicts; `near_candidates` display only; categories -> R-09 -> `src/world_engine/lore_resolve.py:38-43,143-174,217-`
- a name surface carries an entity id; eight importers -> R-10 -> `src/world_engine/name_index.py:65-71`; enumeration (c) 2
- the offer bodies, `_save_offer`'s order, `condition_view`'s shape -> R-11 -> `src/world_engine/cockpit/routes/quests.py:51-137`; `src/world_engine/quest_reads.py:61-67,98-101`
- the editor's props, drafts, `MONEY_KEY`, `draftBody`, `api` -> R-11 -> `frontend/src/creation/ConditionEditor.svelte:10`; `frontend/src/creation/questRequirements.js:32,98-113`; `frontend/src/creation/questOffers.svelte.js:118-131`; `frontend/src/creation/sheetRequest.svelte.js:30-35`
- `lore_usage_event`'s CHECKs and posture; `attempt_id` -> R-12 -> `src/world_engine/models/pipeline.py:363-421`; `src/world_engine/lore_usage.py:34-41`
- the JSON allowlist rule -> R-13 -> `tooling/verify/checks/json_ui_boundary.py:43-114`
- write-site attribution -> R-14 -> `tooling/verify/checks/single_canon_write.py:359-397`
- CC3's prefix filter -> R-15 -> `tooling/verify/checks/conditions.py:727-746`
- the three version places -> R-16 -> `src/world_engine/schema_version.py`; `world-engine-schema.md:3`; `world-engine-schema-changelog.md:14`
- the seed's S2 and the single-source head tuple; rule 1 -> R-17 -> `scripts/seed_pilot.py:132-187,1921-1942,2934`; `tooling/verify/checks/prompt_registry.py`
- the router mounting and the global origin guard; `_world_id` -> R-18 -> `src/world_engine/cockpit/app.py:56-70,125-144`; `src/world_engine/cockpit/crud/_shared.py:57-61`
- `OllamaError`, `LlmParseError` is a `ValueError` -> R-19 -> `src/world_engine/ollama_client.py:39`; `src/world_engine/llm_parse.py:21`
- base domains, skill definitions, condition roles -> R-20 -> `src/world_engine/models/canon.py:594,633-655`; `src/world_engine/models/config.py:130`
- CLAUDE.md budgets in characters; the two tree lines -> R-21 -> `tooling/verify/checks/claude_md_contract.py:69-71`; `CLAUDE.md:461,473`
- R5's creator allow-list; K3's subject census -> R-22 -> `tooling/verify/checks/name_index.py:17-22,55-61`; `tooling/verify/checks/knowledge_identity.py:31-35,109-116`

(b) Case tables.

b-1 -- the outcome of a proposal (C-04, `_settle` then `interpret`'s retry).
Evaluated top to bottom; the first row that applies decides.

| read answer                                               | outcome        | errors shown                 | second call (II1)       |
|-----------------------------------------------------------|----------------|------------------------------|-------------------------|
| a reading error (form, connector, code, subject, shape)   | refused        | the reading errors (+ names) | yes, on the first answer |
| only unknown names with no near name                      | refused        | « aucun nom ne correspond »  | no                      |
| `condition` null, unsupported listed                      | refused        | none (the notes say why)     | no                      |
| `condition` null, nothing listed                          | refused        | `NOTHING_PROPOSED_FR`        | no                      |
| a name ambiguous, or unknown with near names              | needs_choice   | none                         | no                      |
| every name matched, a leaf refused by `clean_leaf`        | refused        | every leaf's error           | yes, on the first answer |
| every name matched, every leaf clean                      | proposed       | none                         | no                      |

A second answer is settled by the same table and never retried. `resolve`
on a `needs_choice`: every waiting mention picked within its choices ->
validated -> `proposed` or `refused` (no call); a pick missing or outside
-> `ValueError`.

b-2 -- the moves of `condition_draft.outcome` (C-07).

| from \ to     | proposed | refused | inserted | discarded | saved            |
|---------------|----------|---------|----------|-----------|------------------|
| needs_choice  | yes      | yes     | --       | yes       | --               |
| proposed      | --       | --      | yes      | yes       | --               |
| inserted      | --       | --      | --       | --        | `mark_draft_saved` only |
| refused, unavailable, parse_error, discarded, saved | -- | -- | -- | -- | -- |

First outcomes: proposed, needs_choice, refused, unavailable, parse_error.
Every outcome of `CONDITION_DRAFT_OUTCOMES` is a first outcome or reached
by a move (NB1).

b-3 -- a leaf's target in the model's form (C-03), per form.

| form                | target in the answer                    | stored as                     | threshold | value |
|---------------------|-----------------------------------------|-------------------------------|-----------|-------|
| knowledge           | `{"code": "f<n>"}`                      | `target_key` = fact id        | --        | --    |
| relation_gte        | an entity name / `e` code               | `target_entity_id`            | yes       | --    |
| resource            | null (ignored)                          | `target_key` = `monnaie`      | yes       | --    |
| location_reachable  | an entity name / `e` code               | `target_entity_id`            | --        | --    |
| has_met             | an entity name / `e` code               | `target_entity_id`            | --        | --    |
| faction_member      | an entity name / `e` code               | `target_entity_id` (faction)  | --        | --    |
| skill_rank_gte      | `{"code": "s<n>"}`                      | `target_key` = domain or id   | 1-5       | --    |
| quest_state         | `{"code": "q<n>"}`                      | `target_key` = offer id       | --        | yes   |
| has_debt_to         | an entity name / `e` code               | `target_entity_id`            | --        | --    |
| no_debt_to          | an entity name / `e` code               | `target_entity_id`            | --        | --    |
| item_held           | an entity name / `e` code               | `target_entity_id` (item)     | yes       | --    |
| vital_status        | null                                    | none                          | --        | yes   |

The entity type each entity form accepts is `clean_leaf`'s
(`_TARGET_ENTITY_TYPE`); a wrong type is a `clean_leaf` error (b-1 row 6).

b-4 -- `mark_draft_saved` (C-07, C-08).

| draft id         | draft's world | draft's outcome | result | row                                  |
|------------------|---------------|-----------------|--------|--------------------------------------|
| None / empty     | --            | --              | False  | unchanged                            |
| unknown          | --            | --              | False  | --                                   |
| known            | another       | any             | False  | unchanged                            |
| known            | this          | not `inserted`  | False  | unchanged                            |
| known            | this          | `inserted`      | True   | `saved`, `offer_ref`, `saved_as_proposed = (tree == payload.proposed)`, `decided_at` |

b-5 -- the routes' statuses (C-06).

| route     | case                                                         | status | journal                          |
|-----------|--------------------------------------------------------------|--------|----------------------------------|
| interpret | no active world                                              | 400    | none                             |
| interpret | empty sentence, unknown role, current tree that does not hold | 422    | none                             |
| interpret | `OllamaError`                                                | 503 `INTERPRET_UNAVAILABLE_MESSAGE` | `unavailable`, the call's error |
| interpret | `LlmParseError`                                              | 502 `PARSE_ERROR_MESSAGE` | `parse_error`, the raw reply  |
| interpret | otherwise                                                    | 200    | the b-1 outcome, `retried`        |
| resolve   | unknown draft or another world's                             | 404    | none                             |
| resolve   | draft not `needs_choice`                                     | 409    | unchanged                        |
| resolve   | a pick missing or outside its choices                        | 422    | unchanged                        |
| resolve   | otherwise                                                    | 200    | moved, payload with `bindings`    |
| decision  | unknown draft or another world's                             | 404    | none                             |
| decision  | decision not `inserted` / `discarded`                        | 422    | unchanged                        |
| decision  | move outside b-2                                             | 409    | unchanged                        |
| decision  | otherwise                                                    | 200    | moved                            |

(c) Enumerations.

1. `grep -rn "CodedFacts\|code_facts" --include=*.py src tooling scripts`
   (outside `fact_refs.py`):
   ```
   src/world_engine/lore_write_draft.py:31:from .fact_refs import CodedFacts, code_facts
   src/world_engine/tick_context.py:40:from .fact_refs import CodedFacts, code_facts
   src/world_engine/tick_normalize.py:27:from .fact_refs import CodedFacts
   src/world_engine/tick.py:26:from .fact_refs import CodedFacts, knowledge_key
   src/world_engine/day_plan.py:38:from .fact_refs import CodedFacts, code_facts
   src/world_engine/analyzer_transcript.py:65:from .fact_refs import CodedFacts, code_facts, find_held, knowledge_key
   tooling/verify/checks/knowledge_identity.py:50:   a. `code_facts` / `CodedFacts` on the `_CODE_CASES` table;
   tooling/verify/checks/knowledge_identity.py:485:    from world_engine.fact_refs import code_facts
   ```
   (plus each importer's annotation uses, all renamed by A's diff).
2. `grep -rln "from .name_index import\|from ..name_index import" src`:
   ```
   src/world_engine/day_choice.py
   src/world_engine/day_concordance.py
   src/world_engine/lore_mentions_read.py
   src/world_engine/lore_query.py
   src/world_engine/lore_resolve.py
   src/world_engine/lore_write_draft.py
   src/world_engine/prose_tokens.py
   src/world_engine/writes/facets.py
   ```
3. Who names `lore_usage_event` outside its own check:
   `src/world_engine/models/__init__.py:124,187`,
   `src/world_engine/models/pipeline.py`, `src/world_engine/writes/lore_usage.py`,
   `tooling/verify/checks/json_ui_boundary.py:112-113`,
   `scripts/migrate_v2_13_lore_usage.py`, `scripts/export_lore_usage.py`.
   B follows the same footprint: models, writer, allowlist, migration (no
   export script: the reader is 0115's dashboard).
4. Tables named `condition%` after B, by the prototype's `sqlite_master`:
   `condition`, `condition_draft`, `condition_node` -- the reason for R-15.

(d) The family contracts C-01 (one coded list for three kinds of
target) and C-07 (one writer for every move) were written before their
members and re-read after the last (`code_refs` callers in C;
`write_condition_draft`, `move_condition_draft`, `mark_draft_saved` used
by D). ✓

(e) Gates and the modules that satisfy them.

- `condition_interpreter.py` (proposed, NA-NE): satisfied by
  `fact_refs.py`, `prompt_call.py`, `lore_write_draft.py` (A);
  `models/pipeline.py`, `writes/condition_drafts.py`,
  `migrate_v2_21_condition_draft.py`, `json_ui_boundary.py` (B);
  `condition_interpreter.py`, `seed_pilot.py`, `prompt_registry.py`,
  `apply_ticket_0112_condition_prompt.py`, the two allow-list entries (C); `cockpit/routes/conditions.py`,
  `cockpit/routes/quests.py`, `cockpit/app.py` (D); the five frontend files
  and the built bundle (E). NC1 forbids `chat(` and any write in
  `condition_interpreter.py`: the module calls the model only through
  `prompt_call.call_json` and validates through `clean_leaf` /
  `clean_condition`, which write nothing.
- `single_canon_write.py` (passed): `writes/condition_drafts.py` assigns
  every row it adds from a constructor or a `db.get` statement (R-14);
  `condition_draft` is not a canon table.
- `json_ui_boundary.py` (passed): the two JSON columns are allowlisted by B.
- `world_cascade.py` (passed): no `world_id` column -- out of the cascade
  by construction.
- `conditions.py` (passed): CC3's filter narrowed by B (R-15).
- `prompt_registry.py` (passed): `condition_interpret` seeded and
  registered in the same commit (C); `lore_write_draft.py:_call` still
  exists (A).
- `lore_isolation.py` (passed): `prompt_call.py` is neither a pipeline nor
  a panel file and holds no `select(`; `lore_write_draft.py` stays a panel
  file importing no pipeline module.
- `lore_write.py`, `lore_usage.py` (passed): their stubs replace
  `lore_write_draft.chat`, which `_call` still passes (R-02).
- `claude_md_contract.py` (passed): two lines edited, no line added,
  every line at most 100 characters.
- `schema_partition.py`, `schema_version_agreement.py` (passed): B moves
  the three version places together.
- `frontend_build_fresh.py`, `creation_island.py` (passed): E rebuilds;
  `ConditionInterpreter.svelte` is a child of `ConditionEditor.svelte`,
  never an island.
- `decisions_index.py` (passed): each brief appends one entry above the
  footer and regenerates the index.
- `name_index.py`, `knowledge_identity.py` (passed): C adds
  `condition_interpreter.py` to R5's allow-list and K3's census (R-22).
- `module_budget.py`, `function_length.py` (passed): the largest new
  module, `condition_interpreter.py`, is 473 lines and 26 functions
  (nested ones counted); its longest function 28 lines.

## Amendments

(none)
