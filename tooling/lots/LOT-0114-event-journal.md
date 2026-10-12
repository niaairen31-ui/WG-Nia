# LOT — TICKET-0114 "The event journal: what happens in a world is one of its own event types -- with roles, sortes and who learns it -- read by the models by what is known, counted by one condition form, proposed by the interpreter and by Play"

## Objective and cut

`event` becomes the world's one journal (F1, C1 of the series). What
happens is an EVENT TYPE the creator defines as data in her world (B1):
its name, its domain (the seven former categories), its roles -- each
accepting entity types and, or, an anonymous SORTE of the world (C1, D1:
« un loup ») --, whether it counts a quantity, enters the chronicle the
models read, and whether its participants keep it secret by default (X1);
who learns it besides its participants (W1: `location`, `world`,
`rencontre` of a role, `faction` of a role, each at a level). The three
lists live in one Création tab, « Vocabulaire du monde », beside the
states of TICKET-0113 (T3); the « Événements » tab becomes the journal.

An event is written with its type, its participants by role (V1:
`event_participant` replaces `event_entity`), its quantity, its place, the
session and day it came from (E1), and its FACT (K-a): the participants
know it at `knows` -- secret each as said, a player character never
(INV-07) --, the type's scopes are made concrete on the fact. v2.24 types
every earlier event by its category (N1, O1); v2.25 drops the columns
nobody reads any more (L1).

The models read the journal by what is KNOWN (Q1): Play's MJ the
chronicle events the player knows (the 0105 resolver), the tick what
everyone knows; only an `in_chronicle` type is told to a model. The MJ
sees the states a player may see (WL1, TICKET-0113's carried point).

A condition counts the events its subject lived through one form, `event`
(G1): by type, role, place (or under it), window (F1: `always`, since the
quest, since the step) and filters on the other roles, quantities added.
A player counts only what his character knows (V1 for events). A quest
step may say when it has FAILED (H1): shown, never acting. The
interpreter reads the event types and sortes and writes the leaf (R1);
when one is missing it proposes it, and the creator creates it from the
card (G). Play's analyzer proposes typed events and may propose their
type, approved with the event (I2, H).

The lot stops before: the Journée and tick producers of typed events, a
type's effects pre-filling state changes (M-c), Lore declaring events
(U1), the event review card (Y2) -- all TICKET-0119, the next ticket; the
calendar (`occurred_at`'s successor, « avant le jour N ») -- TICKET-0120,
after 0116 (P1); absence conditions as their own form (« sans être
repéré » is `not` over an `event` leaf already); any dashboard metric
(0115).

## Briefs in this lot

- **A — the vocabulary, v2.24** (schema v2.24,
  `BRIEF-0114-A-event-vocabulary.md`): `models/canon_event.py` (six
  tables) and `condition_node_filter`; `event.type_id`, `event.quantity`,
  `agenda_step.started_at`, `condition_node.since`, the `failure` role;
  `event_vocab.py` (reads), `writes/event_types.py` (the one writer of the
  vocabulary); `migrate_v2_24_event_journal.py` (types every event, its
  links become participants, its fact); check `event_journal.py`
  (EA1-EA7).
- **B — « Vocabulaire du monde »** (no schema change,
  `BRIEF-0114-B-vocabulary-tab.md`): routes `cockpit/routes/event_types.py`;
  the tab grouping États, Types d'événements and Sortes; the shared
  `EventTypeForm`; near names asked; EB1-EB2 in `event_journal.py`.
- **C — the journal's writer and sheet** (no schema change,
  `BRIEF-0114-C-journal-writer.md`): `writes/events.py` rewritten
  (participants, fact, scopes, knowledge); `event_payloads.py`; the
  `event_creation` applier; the journal sheet; check `event_writes.py`
  (EC1-EC6).
- **D — the readers, v2.25** (schema v2.25,
  `BRIEF-0114-D-journal-readers.md`): `event_reads.py`; the MJ context,
  the return-visit delta and the tick read by what is known; WL1
  (`attributes.perceived_states`); `event` loses five columns,
  `event_entity` dropped (`migrate_v2_25_event_columns.py`); check
  `event_contexts.py` (ED1-ED4).
- **E — the `event` form and the `failure` role** (no schema change,
  `BRIEF-0114-E-event-conditions.md`): the form, its windows and
  filters, the player's recount; `started_at` written; a step's failure
  condition carried, shown in Journée; the editor; check
  `event_conditions.py` (EE1-EE6).
- **F — the interpreter reads the event types** (no schema change,
  `BRIEF-0114-F-interpreter-events.md`): the `t` list, the leaf in the
  model's form (`interpreter_events.py`); three prompt fragments and
  `apply_ticket_0114_condition_prompt.py`; check `event_interpreter.py`
  (EI1-EI4).
- **G — the interpreter proposes a type or a sorte** (no schema change,
  `BRIEF-0114-G-proposed-vocabulary.md`): `event_proposals.py`; the
  journal's `vocabulary`; the card creates through B's routes;
  EI5-EI7 in `event_interpreter.py`.
- **H — Play's analyzer proposes typed events** (no schema change,
  `BRIEF-0114-H-analyzer-events.md`): `event_analysis.py`; the applier
  writes a proposed type and sorte with the event; the queue card; three
  prompt fragments and `apply_ticket_0114_analysis_prompt.py`; check
  `event_analyzer.py` (EH1-EH4).

## Dependency graph

Strictly sequential, A -> B -> C -> D -> E -> F -> G -> H.

- B reads and writes through A (C-02, C-03). C writes events of A's
  types (C-02) and its applier types an untyped payload through A's
  `ensure_domain_type` (C-03). D reads C's facts and participants (C-05)
  and its migration imports A's `_backfill`. E counts C's events (C-05)
  through the columns A added (C-01) and reads D's model (no
  `event_entity`). F encodes E's leaf (C-08). G binds F's pending leaf
  (C-09) and creates through B's routes (C-04). H reuses F's
  `event_type_line` (C-09), G's `type_spec` / `type_definition` (C-10)
  and C's applier (C-06).
- Textual chaining makes the order strict anyway: every brief appends to
  `tooling/standards/ARCHITECTURE_DECISIONS.md` above its footer; A and B
  `event_journal.py`; F and G `event_interpreter.py`; E, F, G
  `condition_interpreter.py`; F and H `seed_pilot.py`.
- **Order by decision, not dependency:** D before E is the series' order
  (« les contextes d'abord ») -- E needs only D's model change.

## RECON

Opened on `main` at `b16d91e` (merge of PR #145, `ticket/0113`), schema
v2.23, next id `0114` (Nia's). `main` ran the full corpus green: 150/150
(`WORLD_ENGINE_ENV=test`). Then prototyped on a branch (`proto/0114`):
each brief's commit ran its checks and the full corpus green, and every
named mutation of every brief turned its check red on its rule. The lot
was then replayed from these diffs onto a clean `main` (branch
`replay/0114`): every diff applied with `git apply --check`, the
generated files regenerated, the frontend rebuilt to the same source hash,
and the full corpus ran green: 156/156. Production was measured by Nia on a
read-only copy (R-02). Findings tagged [M] were measured. Line numbers are
`main`'s.

### R-01 — `event` and `event_entity` [M]
Opened: `src/world_engine/models/canon.py:479` (`Event`: `session_id`,
`batch_id`, `title`, `description`, `type` free text, `knowledge_status`
default `'secret'`, `location_id`, `has_magic_impact`, `consequences`
JSON, `occurred_at`, `recorded_at`; one index `idx_event_world`), `:510`
(`EventEntity`: `event_id`, `entity_id`, unique `idx_event_entity_unique`).
Consequence: A adds `type_id` and `quantity` (nullable at v2.24, so the
migration can fill them); D rebuilds `event` without `type`,
`knowledge_status`, `has_magic_impact`, `consequences`, `occurred_at`,
`type_id` NOT NULL, and drops `event_entity` once every link has its
`event_participant` twin.

### R-02 — production holds four events, none with a fact [M]
Measured by Nia on her database (2026-10-11): four events -- `military`,
`other`, `political` with `knowledge_status = 'secret'`, `social` with
`'public'` --; each carries `consequences` = the JSON `null` (never SQL
NULL), no `has_magic_impact`, no `occurred_at`; zero `fact` rows with an
`event_id`.
Consequence: N1 (the type required) types them by their category, which
the migration makes as « Militaire », « Autre », « Politique »,
« Social », each with one role « Impliqué »; O1: the public one gets a
`world` scope at `knows`, the secret ones none. Nothing in the dropped
columns is lost (L1).

### R-03 — the seven categories [M]
Opened: `src/world_engine/tick_normalize.py:67` (`_EVENT_TYPES`:
`political`, `magical`, `criminal`, `military`, `social`, `mystery`,
`other`), `:445` (an unknown one reads `other`).
Consequence: they become a type's DOMAIN (`EVENT_DOMAINS`, EA1 keeps the
two equal); French labels `DOMAIN_LABELS_FR`.

### R-04 — the event writers and the applier
Opened: `src/world_engine/writes/events.py:23` (`write_event(db, *,
world_id, title, description, type, knowledge_status, involved_entities,
location_id, mutation_id)`, no fact written), `write_event_update` (the
creator's correction); `src/world_engine/cockpit/mutations.py`
`_mutation_apply_event_creation` (calls `write_event` from the payload);
`src/world_engine/cockpit/routes/mutations.py:598`
(`_approve_apply_and_commit`: `with db.begin_nested()`, an applier's
error string raises, the savepoint rolls back, canon clean);
`tooling/verify/canon_write_policy.txt:85-86` (both writers write
`event`).
Consequence: C rewrites both writers on a spec (C-05), the applier reads
a payload into it (C-06); H's proposed type is written inside that same
savepoint.

### R-05 — facts, their defaults and who knows them
Opened: `src/world_engine/models/canon_knowledge.py:87` (`Fact`, `:107`
`event_id`, at most one owner, `idx_fact_event`), `:164` (`FactDefault`:
`scope_type IN ('world','faction','location','rencontre')`, `scope_id`
NULL for `world`), `:199` (`Knowledge`); `src/world_engine/facets.py:79`
(facet `evenement`, monde, typed); `src/world_engine/writes/facts.py:75`
(`create_fact`), `:163` (`update_typed_fact_content`, kind `correction`),
`:204` (`create_fact_default`); `src/world_engine/knowledge_resolve.py:253`
(`resolve_known_for_entity`, 0105: own rows, then scopes in contact);
`src/world_engine/writes/knowledge.py:72` (`KNOWLEDGE_LEVEL_LADDER`).
Consequence: an event's fact is facet `evenement`, its text « title —
description »; a type's scopes are written as `fact_default` rows; the
models read through `resolve_known_for_entity` (Q1); a scope's level is
on the ladder, never `unaware`.

### R-06 — who reads `knowledge_status` [M]
Opened: `src/world_engine/context.py:701` (`_mj_context_public_events`,
`:709` filters `public`/`confirmed`), `src/world_engine/tick_context.py:622`
and `:725` (location and faction briefings),
`src/world_engine/cockpit/play_physical.py:601` (`_compute_return_delta`,
its filter at `:661`); `tooling/verify/checks/visit_delta.py` (its rule 2
pins the return delta's query).
Consequence: D replaces each with `event_reads` (C-07) and retargets
`visit_delta.py` rule 2; ED4 forbids any reader of the dropped columns.
The tick still WRITES the untyped shape (`tick_normalize.py:447-481`,
`knowledge_status` in its payload): C-06 reads it; its typed producer is
TICKET-0119.

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

### R-09 — the vocabulary helpers TICKET-0113 left
Opened: `src/world_engine/lore_resolve.py:73` (`normalize_surface`:
case- and accent-blind), `:186` (`near_ratio`);
`src/world_engine/attributes.py:129` (`world_entity_types`), `:274`
(`near_attributes`, the near-name precedent).
Consequence: a type's or sorte's name is compared with
`normalize_surface` in Python (SQLite's `lower()` is not accent-blind),
near names by `near_ratio`.

### R-10 — Création's registries
Opened: `frontend/src/creation/tabs.js:333` (`evenements`), `:361`
(`etats`), `registry.js:572` (island `states`), `mount.js:49`
(`COMPONENTS`); `.claude/rules/frontend.md` (INV-49, INV-50, INV-54).
Consequence: B replaces `etats` by `vocabulaire` (island `vocabulary`,
origin `new`), sized in `creation.css`; `evenements` stays, now the
journal.

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

### R-12 — Play's analysis [M]
Opened: `src/world_engine/analyzer_transcript.py:308`
(`_build_payload_event_creation`, untyped), `_apply_type_guards`,
`_normalize_to_schema`, `_window_call_model` (`str.replace` of
`{transcript}`, `{injected_context}`), `analyze_transcript`;
`scripts/seed_pilot.py:276` / `:414` (`CONVERSATION_ANALYSIS_*`, literal
constants); `tooling/verify/checks/prompt_lean.py` (reads them as literal
constants by AST: exactly 5 `=== EXEMPLE`, four rubric headers);
`scripts/apply_ticket_0097_fact_code_prompts.py` (re-delivers the seed's
whole analysis text with its own variable list).
Consequence: H edits the literal texts in place and keeps the fragments
beside them (EH1 keeps them equal); the 0097 script reads the seed's
variable list, so a re-run never lands a placeholder undeclared.

### R-13 — the canon-write policy and the hard-delete list
Opened: `tooling/verify/canon_write_policy.txt` (header line 4 lists the
canon tables; one line per writer and table);
`tooling/verify/checks/single_canon_write.py` (docstring: the closed list
of hard deletes, INV-12; an unattributable assignment is a failure).
Consequence: A, C, E add their writers and tables; the full-replace
deletes (`fact_default` of an event, a type's scopes, a node's filters)
are named in the docstring.

### R-14 — fifteen seconds per check [M]
Opened: `tooling/verify/checks/corpus_gate.py` (per-check subprocess,
timeout a failure), `.claude/rules/verify-checks.md`.
Consequence: six checks, each measured on the replay: `event_journal.py`
4.8 s, `event_writes.py` 1.9 s, `event_contexts.py` 6.3 s,
`event_conditions.py` 1.4 s, `event_interpreter.py` 4.1 s,
`event_analyzer.py` 6.7 s.

## Contract sheet

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

### C-02 — `event_vocab` (reads)
Produced by: BRIEF-0114-A   Consumed by: B-H
`DOMAIN_LABELS_FR`, `DOMAIN_ROLE_FR = "Impliqué"`, `EVENT_FORM = "event"`;
`RoleView(id, name, position, entity_types, accepts_sorte, status)`,
`ScopeView(kind, role_id, level)`, `EventTypeView(id, world_id, name,
domain, counts_quantity, in_chronicle, participants_secret, status, roles,
scopes)` with `role(role_id)` and `active_roles()`;
`role_accepts(role, entity_type) -> bool`; `type_view(db, type_id) ->
Optional[EventTypeView]`; `world_event_types(db, world_id,
include_retired=False)`; `world_sortes(db, world_id,
include_retired=False) -> list[EventSorte]`; `near_event_types` /
`near_sortes(db, world_id, name, exclude_id=None) ->
tuple[NearName(id, name, score)]` (retired included, best first). Writes
nothing (EA7).

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

### C-06 — an `event_creation` payload
Produced by: BRIEF-0114-C (H adds `new_type`, `sorte_name`)   Consumed by: H
`event_payloads.spec_from_payload(db, world_id, payload, *,
session_id=None, batch_id=None) -> EventSpec`; `provenance(db, mut) ->
(session_id, batch_id)`. Typed: `type_id`, `participants` [{role_id,
entity_id | sorte_id, secret}], `quantity`, `location_id`. Untyped: `type`
(a category), `involved_entities`, `knowledge_status` -- typed by its
domain (`ensure_domain_type`), its entities in « Impliqué », a `world`
scope at `knows` when `public`/`confirmed`. H: `new_type` (a definition,
C-10's `type_definition` form) instead of `type_id`, participants naming
its roles by `role`; `sorte_name` for a sorte the world lacks -- written in
the applier's savepoint, a same-named one used.

### C-07 — `event_reads` and WL1
Produced by: BRIEF-0114-D   Consumed by: E
`known_chronicle_events(db, knower_id, world_id, *, location_id=None,
since=None) -> list[Event]` (newest first, `in_chronicle` types only,
through `resolve_known_for_entity`); `public_chronicle_events(db,
world_id, *, location_id=None, participant_id=None, limit=None)` (a
`world` scope on the fact); `attributes.perceived_states(db, world_id,
entity) -> str` (« Ouvert : oui · … », non-hidden, non-system).

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

### C-11 — the analyzer's typed proposal
Produced by: BRIEF-0114-H   Consumed by: (TICKET-0119)
`event_analysis.AnalysisVocabulary(codes, types, sortes)` with
`prompt_values()`; `analysis_vocabulary(db, world_id)`;
`typed_payload(db, world_id, payload, vocab) -> Optional[dict]` -- None
drops it; a payload naming no type is returned unchanged; otherwise
`{title, description, type_id | None, type_name, participants [{role_id |
None, role, entity_id, sorte_id, sorte_name, secret}], quantity,
location_id, new_type?}`. Seed: `CONVERSATION_ANALYSIS_VARIABLES`,
`CONVERSATION_ANALYSIS_FRAGMENTS_0114`.

## Gate output

(a) Property trace:
- `event` columns and `event_entity`'s index -> R-01 -> `models/canon.py`.
- production's four events, their JSON-null `consequences`, no fact ->
  R-02 -> Nia's measurement (read-only copy).
- the seven categories -> R-03 -> `tick_normalize.py:67`.
- the writers' signatures, the savepoint's rollback -> R-04 ->
  `writes/events.py`, `cockpit/routes/mutations.py:598`.
- `fact.event_id`, `fact_default.scope_type`'s CHECK, facet `evenement`,
  the resolver -> R-05 -> `models/canon_knowledge.py`, `facets.py`,
  `knowledge_resolve.py`.
- the readers of `knowledge_status` -> R-06 -> `context.py`,
  `tick_context.py`, `play_physical.py`, `visit_delta.py`.
- `CONDITION_ROLES` and `condition_draft`'s own role CHECK -> R-07 ->
  `models/config.py:130`, `models/pipeline.py:451`.
- `accept_quest` copies conditions by role -> R-08 -> `writes/quests.py:201`.
- `normalize_surface` accent-blind, `near_ratio` -> R-09 ->
  `lore_resolve.py`.
- the `etats` entry and the `states` island -> R-10 -> `tabs.js`,
  `registry.js`.
- `PAYLOAD_KEYS` exact, the fragments' AD1 rule -> R-11 ->
  `writes/condition_drafts.py`, `checks/attribute_interpreter.py`.
- `prompt_lean` reads literal constants -> R-12 ->
  `checks/prompt_lean.py`.
- the hard-delete list -> R-13 -> `checks/single_canon_write.py`.

(b) Case tables:
- Who learns an event (K-a, W1, X1, INV-07):

  | who | row | secret |
  |---|---|---|
  | an entity participant | `knowledge` at `knows` | its own, else the type's default |
  | a player character participant | `knowledge` at `knows` | never |
  | a sorte participant | none | -- |
  | a faction participant | none (a `faction` scope reaches its members) | -- |
  | a type scope `location` | `fact_default` on the event's place | -- |
  | `world` | `fact_default` world | -- |
  | `rencontre`(role) | one per entity filling the role | -- |
  | `faction`(role) | one per faction filling the role | -- |

- An `event` leaf's window (F1):

  | since | role of the condition | counts from |
  |---|---|---|
  | `always` | any | the first event |
  | `quest` | eligibility | refused at write |
  | `quest` | prerequisite, completion, failure | the quest's `accepted_at`; no quest: `unknown` |
  | `step` | eligibility | refused at write |
  | `step` | prerequisite, completion, failure | `started_at`, else `accepted_at`; neither: `unknown` |

- An event leaf on a player surface (V1 for events): the canon count is
  replaced by the count over the facts he knows, whoever the subject;
  no known facts given -> `unknown`.
- An analyzer `event_creation` (H):

  | payload | outcome |
  |---|---|
  | no `event_type`, no `new_type` | unchanged (untyped) |
  | a known code | typed |
  | an unknown code | dropped |
  | `new_type` refused by the writer | dropped |
  | `new_type` named as an existing type | that type |
  | a participant of no role / wrong entity | left out |

(c) Enumerations:
- 150 checks on `main` (`corpus_gate.py`: « 150 check(s) discovered, 150
  executed, 150 passed »); 156 on the replay (« 156 … 156 passed »).
- `knowledge_status` on `main` (`git grep -n knowledge_status -- src/`):
  code -- `cockpit/crud/_shared.py:307`, `cockpit/crud/events.py:101-218`,
  `cockpit/mutations.py:696-724`, `cockpit/play_physical.py:661`,
  `context.py:709`, `models/canon.py:490`, `tick_context.py:622`, `:725`,
  `tick_normalize.py:447-481` (the tick's payload), `writes/events.py:30-92`;
  comments only -- `cockpit/crud/__init__.py:42`, `cockpit/legacy.html:2490`,
  `cockpit/static/shared.css:165`, `context.py:771-787`,
  `event_author.py:263`; the built bundle. C rewrites the writers, the
  sheet and the applier; D the readers and the model; the tick's payload
  stays (read by C-06, typed in 0119). ED4 forbids the attribute on any
  object under `src/`.

(d) C-01..C-11 written before the briefs, re-read after H. ✓

(e) Modules per gate:
- `event_journal.py`, `event_writes.py`, `event_contexts.py`,
  `event_conditions.py`, `event_interpreter.py`, `event_analyzer.py`: each
  satisfied by the brief that creates it; each under 15 s (R-14).
- Gates merely passed: `single_canon_write.py` (A, C, E policy lines,
  the named full-replace deletes); `json_ui_boundary.py` (no JSON column
  added; the `proposed_mutation.payload` and `condition_draft.payload`
  JSON already allowed); `claude_md_contract.py` (no CLAUDE.md change);
  `frontend_build_fresh.py` (each frontend brief rebuilds); `prompt_lean.py`
  (H keeps 5 examples and the four headers); `attribute_interpreter.py`
  AD1/AD4 (F's fragments keep its rule; its script delivers them too);
  `quests.py` QA1/QC1, `day_plan.py` R3, `day_narration.py` R15 (E adds
  `event` to their lists).

## Amendments

(none)
