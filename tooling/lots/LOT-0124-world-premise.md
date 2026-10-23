# LOT — TICKET-0124 "Every generator knows the world it writes for -- the world premise (description, tone, laws, the world's states), a germ attached to an existing character, a Création page that no longer stacks"

`main` at `246e89b` (PR #150, TICKET-0121 merged), schema v2.28 -- re-based by AMENDMENT-0124-01 onto `386c01a` (PR #151, TICKET-0116 merged), schema v2.29.

## Objective and cut

An entity a day (or any surface) asks for is drafted by a model that has
never been told what world it is in: the entity generator receives a type,
a field list and one sentence (R-15), the play prompts never see the
world's laws (R-14, R-07), and a Journée germ reaches the generator with a
location UUID where its place should be (R-17). This lot gives every
generator that writes fiction one **world premise** -- the description, a
new **tone** field (v2.30), the fundamental laws (public: true everywhere, known to
all, observable -- decision D2), and, for the creator surfaces, the world's
skill systems and the **states** (TICKET-0113 attributes) an entity of the
type being drafted carries (A2). The premise enters every template through
one placeholder, `{world_premise}`, delivered as a new `prompt_version`
of each template (P1), filled by one accessor, and a cockpit edit that drops
it is refused (P1-g). The world's description, tone and laws become
editable on a « Monde » page (W1).

The entity draft proposes a value for each state, links to existing
entities, « peut-être la même personne que », and the entities it calls for
that do not exist yet; ticking one of those at save writes a germ that
keeps its sentence and the link it was born with (I1). A germ can be
**attached** to an existing character instead of creating one (H1), and the
« Créations en attente » strip, the sheet and the skill sheet stop stacking
in one column (L1): germs become a group of the list, the skill sheet a
pane of the sheet.

The lot stops before: a law hidden from the players (its own ticket, D2);
the model recognising an existing character in play (H2, deferred,
measured); law history (W2, deferred); a structured world bible (B3); states
derived from the laws' text (A3); the two report-only defects of R-15 and
R-17.

## Briefs in this lot

- **A** `world-tone-sheet-api` -- v2.30: `world.tone`; `GET`/`PUT /api/worlds/{world_id}` (name, description, tone, laws); the create body's `tone`.
- **B** `world-premise-assembler` -- `world_premise.py` (the premise, its two regimes, `fill`, `missing_premise`); `PromptSpec.premise`/`premise_reason` on all 47 usages; `prompt_store.premised_prompt`; `prompt_call.call_json` fills it; INV-64 (no schema change).
- **C** `premise-render-sites` -- every render site of a creator or player usage reads its text through `premised_prompt`; the sites that stay on `current_prompt` are a closed list (no schema change, no behavior change).
- **D** `premise-prompt-versions` -- the seed adds the placeholder and the variable; `apply_ticket_0124_world_premise.py` delivers one new version per template onto the live DB; the edit and restore routes refuse a text without it (P1-g) (no schema change).
- **E** `create-with-world-extras` -- the create body's `states`, `relations` and `germs`, written in the create's own transaction (S1, I1); the `creator_draft` producer (no schema change).
- **F** `germ-attach-and-sources` -- a Journée germ keeps its sentence and its place's name (E1); the pending list names its source; `candidates` and `attach` (H1); the « Germes » metric and the H2 and W2 deferrals (no schema change).
- **G** `draft-world-vocabulary` -- `draft_world.py`: the names a draft may cite, the fields it fills, and the code that judges its states, links, `same_as` and `to_create` (A2, G2) (no schema change).
- **H** `creation-germs-and-panes` -- germs as a group of the entity list, the `germPanel` island (Générer, Rattacher, Créer et lier), the sheet's « Fiche | Compétences » panes; the strip is gone (L1) (no schema change).
- **I** `draft-world-panel` -- the sheet's « Ce que le monde ajoute » section in create mode: states, links, same-as, entities to create, sent with the create (no schema change).
- **J** `world-sheet-page` -- the « Monde » tab and its `worldSheet` island; the tone field in the world-create modal (no schema change).

## Dependency graph

- A depends on nothing in this lot.
- B depends on A (`World.tone`, C-01).
- C depends on B (`premised_prompt`, C-05).
- D depends on B (`regime_of`, `missing_premise`, C-04) and C (every site fills the placeholder before any text carries it -- delivering text before C would send a literal `{world_premise}` to the model).
- E depends on nothing in this lot.
- F depends on E (the `creation` source label of C-11 reads E's germ rows).
- G depends on B (the creator premise with `entity_type`), C (`entity_author` reads through `premised_prompt`) and F (`germ_candidates`, C-11).
- H depends on F (the routes and the pending item shape, C-11).
- I depends on E (the create body, C-09) and G (the draft's `world` block, C-13).
- J depends on A (C-02).
- **Execution order A, B, C, D, E, F, G, H, I, J.** E's position after D, and J's at the end, are choices for a single linear branch, not dependencies.

## RECON

Every finding was opened on `main` at `246e89b`, in the file that declares
what is claimed. `[M]` measured.

### R-01 — the `world` row and its writers [M]
Opened: `src/world_engine/models/canon.py:63-88` (`class World`); `tooling/verify/canon_write_policy.txt:2` (`[CANON_TABLES]` names `world`), `:133-140` (the four sanctioned `world` sites).
Finding: `World` declares `id, name, description: Optional[str], is_active, current_phase, created_at, updated_at`; no `tone`. `world` is a canon table; its sanctioned write sites are `cockpit/routes/creator.py::activate_world`, `::create_world`, `::_activate_world_core`, `::set_world_phase`.
Consequence: `tone` is a new nullable column (v2.30, AMENDMENT-0124-01); the new `PUT` route is a fifth sanctioned site, named in the policy file.

### R-02 — the laws and their writer [M]
Opened: `models/canon.py:91-110` (`class WorldLaw`: `id, world_id, position, text_` mapped to column `text`; unique `(world_id, position)`); `writes/config.py:109-130` (`write_world_laws`); `tooling/verify/checks/single_canon_write.py:78-79`; `models/canon_knowledge.py:108` (`fact.world_law_id`, FK to `world_law.id`).
Finding: `write_world_laws(db, *, world, laws, changed_by)` strips empties, raw-`DELETE`s every row of the world, then adds one row per law at its list position; the caller commits. It is a named full-replace config delete. No writer passes `world_law_id=` to anything (enumeration in Gate (c)), so no fact points at a law today.
Consequence: the `PUT` route reuses `write_world_laws` unchanged; the day a fact points at a law, a full replace fails on the FK -- brief A's STOP, and W2's reactivation condition.

### R-03 — the world routes [M]
Opened: `src/world_engine/cockpit/routes/creator.py:227` (`POST /api/worlds/generate`), `:380-386` (`list_worlds` -> `id, name, is_active`), `:389` (`activate_world`), `:408-411` (`WorldCreateBody(name, description="", fundamental_laws="")`), `:414-442` (`create_world`: `World(name, description)`, `write_world_laws(..., laws=body.fundamental_laws.splitlines(), changed_by="creator")`, deactivate others, activate, one commit, `{"ok": True, "world_id"}` or `{"ok": False, "error"}`), `:464` (`DELETE /api/worlds/{world_id}`), `:502-506` (`_active_world_row`, 400 without an active world); the `@router` lines of the file (Gate (c)).
Finding: no route reads or edits one existing world.
Consequence: brief A adds `GET` and `PUT /api/worlds/{world_id}` (C-02) and `tone` to the create body.

### R-04 — schema version, documentation and migration pattern [M]
Amended (AMENDMENT-0124-01): TICKET-0116 took v2.29 after this lot was planned; the figures below are re-measured on `386c01a`.
Opened: `src/world_engine/schema_version.py:15` (`EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.29"`); `world-engine-schema.md:3` (`Current schema version: v2.29`), `:22-46` (the `world` block, unchanged by 0116), `:48-56` (the `world_law` note: « No editing UI beyond the create form this phase — editing an existing world's laws is a future ticket. »); `world-engine-schema-changelog.md:14-21` (newest entry v2.29, TICKET-0116); `scripts/migrate_v2_29_rank_trials.py:72-73` (`_PREVIOUS_VERSION = "v2.28"`, `_THIS_VERSION = "v2.29"`), `:109-113` (refuses an older database), `:161-167` (`ADD COLUMN` statements built only for absent columns), `:244` (`schema_meta`); `scripts/migrate_v2_28_quest_requests.py:1-60` (header: refuses an older database, idempotent, one raw transaction with `foreign_keys` set, post-check, then `schema_meta`); `scripts/migrate_v2_27_mutation_reviews.py:116` (`cursor.execute("ALTER TABLE proposed_mutation ADD COLUMN original_payload JSON")`).
Finding: a column is added by `ALTER TABLE ... ADD COLUMN` inside the migration's raw transaction, after an inspector check that it is absent. The next free version is v2.30.
Consequence: `migrate_v2_30_world_tone.py` follows the v2.28 header and the v2.27 `ADD COLUMN` line, refusing a database older than v2.29; the `world_law` note is rewritten (this ticket is that future ticket).

### R-05 — the prompt registry [M]
Amended (AMENDMENT-0124-01): TICKET-0116 added a 47th usage, `quest_trial` (`prompt_registry.py:318-325`, call site `quest_designer.py:_design_call`).
Opened: `src/world_engine/prompt_registry.py:54-60` (`@dataclass(frozen=True) class PromptSpec: surface, world_scoped, dry_run_capable, call_sites, default_model`), `:62-417` (47 entries, listed in Gate (c)); `tooling/verify/checks/prompt_registry.py:130-132` (`required_fields = ("surface", "world_scoped", "dry_run_capable", "call_sites", "default_model")`, each asserted present).
Finding: the check requires five fields and forbids none; a field without a default makes every entry declare it, or the module fails to import.
Consequence: `premise: str` (no default) and `premise_reason: str = ""` are appended to `PromptSpec`; all 47 entries declare `premise` (C-03).

### R-06 — the read accessor [M]
Opened: `src/world_engine/prompt_store.py:1-60` (`current_prompt(db, template) -> PromptVersion`, the highest `version_number` row, RuntimeError on none; `get_version`, `list_versions`; `__all__`); `models/pipeline.py:795-811` (shifted 14 lines by TICKET-0116, AMENDMENT-0124-01; `PromptVersion`: `id, prompt_template_id, version_number, system_prompt, user_template, note, created_at`); `tooling/verify/checks/prompt_version.py:53-68` (`ALLOWED_FILES` for rule 2: `models/pipeline.py`, `models/__init__.py`, `prompt_store.py`, `writes/prompts.py`, the migration script), `:112-114` (an import alias or a `Name` node `PromptVersion` elsewhere fails).
Finding: `current_prompt` returns the ORM row itself; mutating its text would be an ORM change on an append-only table (INV-48).
Consequence: `premised_prompt` returns a frozen dataclass of plain values, never the row, and lives in `prompt_store.py` (the only module besides models and writes allowed to name `PromptVersion`); `world_premise.py` never names `PromptVersion`.

### R-07 — every `current_prompt(` call, with its usage [M]
Opened: every module listed (Gate (c): the AST enumeration of every function calling `current_prompt(` under `src/`, pasted with its usage, resolved by opening the loader each function calls).
Finding: 53 calls (`grep -rn "current_prompt(" --include=*.py src/world_engine | grep -v "def current_prompt\|prompt_store.py" | wc -l` -> 53). 34 render a creator or player usage's text; 19, in 18 functions, do not (a `none` usage, a version-number read, or the Prompts tab's editor). The full table is C-07.
Consequence: brief C replaces exactly the 34 render calls; a check holds the remaining 19 to a closed list of 18 functions.

### R-08 — `prompt_call.call_json` [M]
Opened: `src/world_engine/prompt_call.py:27-44`; `tooling/verify/checks/condition_interpreter.py:15-23` (NA2), `:270-295` (its implementation); the callers (`lore_write_draft.py:136`, `quest_designer.py:91` (`quest_subject`), `:101` (`_design_call(..., usage=DESIGN_USAGE, ...)`: `quest_design`, or since TICKET-0116 `quest_trial`), `condition_interpreter.py:550`) -- re-measured by AMENDMENT-0124-01.
Finding: `call_json(db, usage, values, exchanges, chat)` loads `prompt_load.load(db, usage)`, replaces each `{key}` of `values` in the user template only, records the exchange with `spec.system_prompt` and the filled user message, calls `chat`. NA2 (implementation): `prompt_call.py` declares `call_json`; imports nothing whose name contains `ollama_client` or `cockpit`; calls none of `_WRITE_CALLS` (`add`, `commit`, `delete`, `execute`, `flush`).
Consequence: `call_json` fills `{world_premise}` in both texts through `world_premise.fill` (a read-only module, neither client nor cockpit); its five creator usages (`lore_statement_questions`, `lore_statement_to_proposal`, `quest_subject`, `quest_design`, `quest_trial`) need no other change.

### R-09 — `prompt_load.load` stays text-only [M]
Opened: `src/world_engine/prompt_load.py:1-71` (docstring: « It owns that `Session` and nothing else: no canon table ... only `PromptTemplate` and `PromptVersion` (`lore_isolation.py` R15) »; `load` returns `RenderSpec(system_prompt, user_template, model, version_id, version_number)`).
Finding: `prompt_load` is shared by consultation (`lore_question_to_plan`, `lore_rows_to_prose`) and writing.
Consequence: `prompt_load.py` is not touched; the premise is filled one level up, in `call_json` (R-08).

### R-10 — checks that stub or pin `current_prompt` [M]
Opened: `grep -rn "current_prompt" tooling/verify/checks/*.py` (Gate (c)).
Finding: one check replaces it in a module: `day_choice.py:242` (`day_choice.current_prompt = lambda db, t: t`). The others import it to read a fixture head, or name it in a docstring. `day_prompt_delivery.py` R7 asserts `prompt_coverage.missing_usages` references `current_prompt`.
Consequence: `day_choice.py` (usage `day_mention_choice`, `none`) and `prompt_coverage.py` stay on `current_prompt`; both are in C-07's closed list.

### R-11 — the prompt write path and its edit routes [M]
Opened: `src/world_engine/writes/prompts.py:1-117` (`_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")`; `PromptValidationError(offending)`; `write_prompt_version(db, *, template_id, system_prompt, user_template, note=None)`: every placeholder must be a `prompt_variable` of the head, else raises, nothing written; `write_prompt_variables` full-replace); `cockpit/crud/prompts.py:245-270` (`update_prompt_text`), `:273-304` (`restore_prompt_version`), each catching `PromptValidationError` into `HTTPException(422, "Undeclared placeholder(s): ...")`.
Finding: the only two cockpit paths that write prompt text are those two routes.
Consequence: P1-g is enforced in those two routes (C-08), before `write_prompt_version`.

### R-12 — existing checks write premise-usage versions without the placeholder [M]
Amended (AMENDMENT-0124-02): `prompt_version.py` rule 7 also calls the two guarded routes, `update_prompt_text` and `restore_prompt_version` (`:278-296`), on its `npc_dialogue` fixture head (`:246`); it is the only check that calls them (`grep -rn "update_prompt_text\|restore_prompt_version" tooling/verify/checks/` -> `prompt_version.py` only). Under P1-g its texts without `{world_premise}` are refused. Decision K1: its fixture head's usage becomes `conversation_summary` (a `none` usage); the guard stays tested by WP4.
Opened: `tooling/verify/checks/prompt_version.py:246-264` (head `usage="npc_dialogue"`, `write_prompt_version` with plain text); `event_tick.py:94-98` (`world_tick_events`, the « former » text); `event_lore.py:99-104` (`lore_statement_to_proposal`, the « former » text); `knowledge_identity.py:634-640` (`day_plan`, `system_prompt="sys"`; shifted by TICKET-0116, AMENDMENT-0124-01); `observation_runner.py:140-160` (`observation_intent`, `npc_initiative_act`, « pas de placeholder ici »).
Finding: five checks write, through `write_prompt_version`, a version of a creator or player usage that carries no `{world_premise}`.
Consequence: P1-g cannot live in `write_prompt_version` without turning five checks red for a legitimate fixture; it lives in the two routes (R-11). Flagged to Nia (drafting decision 2).

### R-13 — the seed and its delivery precedent [M]
Amended (AMENDMENT-0124-01): TICKET-0116 added `QUEST_TRIAL_PROMPT_HEADS` (`seed_pilot.py:2551`, head `pt-quest-trial`, usage `quest_trial`, seeded by the loop at `:3594-3595`) and shifted every line after `:2487` by 77; the head count is 47.
Opened: `scripts/seed_pilot.py:132-185` (`upsert_prompt_template`: a virgin head gets its variables then v1 via `write_prompt_version`; an existing head never gets text again (S2), its variables are full-replaced on every run); the 31 `upsert_prompt_template(` calls and the four head tuples `LORE_WRITE_PROMPT_HEADS` (`:2079`), `CONDITION_INTERPRET_PROMPT_HEADS` (`:2304`), `QUEST_DESIGNER_PROMPT_HEADS` (`:2464`), `QUEST_TRIAL_PROMPT_HEADS` (`:2551`), `DAY_PROMPT_HEADS` (`:2969`), each seeded through `upsert_prompt_template(session, **entry)` (`:3588-3595`, `:3767`) -- 47 heads, pasted in Gate (c); `:1437-1440` (`REGION_MANIFEST_USER_TEMPLATE` opens with `{world_description}{world_fundamental_laws}`); `scripts/apply_ticket_0121_select_prompt.py:1-95` (env guard, `Session(engine)`, `current_prompt`, one `write_prompt_version` per changed head with a `NOTE`, « unchanged » on a re-run).
Finding: `event_tick.py` ET1 and `event_lore.py` EL1 run the 0119 delivery scripts and assert the delivered text equals the seed constants verbatim (`event_tick.py:125-140`, `event_lore.py:130-148`).
Consequence: the seed constants are not edited; the placeholder is added by `upsert_prompt_template` itself through `seed_pilot.premised_texts` (C-08), so ET1/EL1 keep comparing against unchanged constants. The delivery script prepends the placeholder to each live head's current text.

### R-14 — the region generator already reads the world [M]
Opened: `src/world_engine/region_author.py:43-45` (`_active_world`), `:233-251` (reads `world.description` and the `WorldLaw` rows, renders `world_description` = « Contexte du monde : ... » and `world_fundamental_laws` = « Lois fondamentales du monde (contraintes absolues) : ... », replaces both in the user template).
Finding: this is the only generator that reads the laws (`grep` of `WorldLaw` readers outside models and writes, Gate (c)).
Consequence: once the premise reaches `region_manifest`, the two old values would repeat it; brief C replaces both with `""` (the placeholders stay declared, so a live text that still holds them renders nothing).

### R-15 — the entity generator [M]
Opened: `src/world_engine/entity_author.py:40-104` (`_TYPE_FIELDS` for `character`, `location`, `faction`), `:106-120` (`_MENTIONS_FIELD` appended to each), `:167-169` (`_world_id`: `select(World)).first()` -- the first world, not the active one), `:440-481` (`_entity_draft_call`: `current_prompt`, replaces `{entity_type}`, `{type_fields}`, `{brief}`; parses `public`, `secret`, `mentions`), `:537-568` (`_entity_character_draft`), `:570-600` (`generate_entity_draft(entity_type, brief, db)` -> `{"ok", "draft", "notes"}`, `draft["mentions"]` added last); `:837-880` (`generate_npc_goals`); file size 913 lines, 33 functions (Gate (c)).
Finding: the draft call carries no world content. `_world_id` reads the first `World` row, whichever is active -- a defect outside this lot's decisions (report-only, drafting decision 12).
Consequence: brief C swaps the two render calls; brief G appends the world fields and the citable names to `{type_fields}` and resolves the answer in a new module (`entity_author.py` has 87 lines of budget; the resolver goes to `draft_world.py`).

### R-16 — the germ routes [M]
Opened: `src/world_engine/cockpit/routes/creator.py:63-94` (`_generate_draft_with_l1(entity_type, brief, db)`), `:121` (`_ENTITY_CREATION_TYPES = frozenset({"character", "location", "faction"})`), `:123-127` (`_ENTITY_CREATION_INTROS`), `:130-152` (`_compose_entity_creation_brief(payload)`: name, concept, `anchor` written as prose), `:155-189` (`list_pending_creations`: `entity_creation`, `approved`, no `created_entity_id`; item `{mutation_id, source: "tick" if tick_id else "conversation", proposed_at, name, concept, anchor, entity_type}`), `:191-220` (`generate_creation_draft`); file size 753 lines, 26 functions.
Finding: a Journée germ is labelled « CONVERSATION »; its `anchor` (a location id, R-17) is written into the brief as prose.
Consequence: brief F labels the source from the row (C-11) and composes the place by name (C-10).

### R-17 — the Journée germ [M]
Opened: `src/world_engine/day_concordance.py:463-522` (`emit_germs(unmatched, pass_play, db)`: the payload at `:502-511` is `entity_type, name, concept="Rôle à pourvoir : {name}.", anchor=candidate_location_id, role_hint, surface_form, kind, candidate_location_id`; `source_type="pass_play"`, `proposed_by="local_ai"`, `status="proposed"`); `day_extract.py:42-46` (`Mention`: `category, surface_form, kind, role_hint` -- no sentence); `models/pipeline.py:80` (`PassPlay.declared_action: str`); `cockpit/routes/day.py:455-474` (the caller).
Finding: the declaration is on the pass-play; the mention carries only its words. `routes/day.py:470-471` pairs `person_unmatched` with `germs` by `zip`, while `emit_germs` skips blocked candidates and truncates over its quota -- the pairing shifts when a germ is skipped (report-only, drafting decision 12).
Consequence: `emit_germs` adds `source_sentence` (the declaration's sentence holding the surface form) and `anchor_name` (C-10).

### R-18 — why an existing character was missed [M]
Opened: `src/world_engine/day_concordance.py:218-243` (`_rung_occupation`: an inferred person's `role_hint` keywords against the descriptions of reachable NPCs' standing goals); `day_choice.py:94-116` (`choice_requests`: « Cast and inferred mentions never produce a request »).
Finding: « professeur d'escrime » shares no keyword with « maître des épées »; the model arbitration never sees an inferred mention.
Consequence: H1 handles it on the creator side; H2 (opening the arbitration to inferred mentions) is deferred with a metric (C-12).

### R-19 — the entity create path [M]
Opened: `src/world_engine/cockpit/crud/entities.py:382-404` (`EntityWriteBody`: `entity, extension, mutation_id, facets, mentions, confirm_promotion, link_to, carrure`), `:558-573` (`_create_entity_core`), `:702-723` (`_link_entity_creation(mutation_id, entity_id, db)`: guards -- exists, `entity_creation`, `approved`, no `created_entity_id`; reassigns the payload with `created_entity_id`, status `applied`, `applied_at`, commits), `:729-775` (`create_entity`: `_create_entity_core`, one commit, `dissolve_emptied(...)`, then the response, then `_link_entity_creation` when `mutation_id`); file size 905 lines, 26 functions.
Finding: the core never commits (INV-18); the route owns the single commit.
Consequence: brief E writes the extras between the core and that commit, from a new module (`entity_extras.py`); `entities.py` gains only the three body fields and one call.

### R-20 — a proposal row [M]
Opened: `src/world_engine/models/pipeline.py:99-150` (`ProposedMutation`: no CHECK in `__table_args__`; `source_type: str  # pass_play | conversation | world_tick`, « exactly one of these is set » as a comment; `tick_id` for a tick, which sets neither FK; `target_table`, `target_id` free text; `payload` JSON NOT NULL; `status` default `proposed`; `creator_notes`; `proposed_by` default `local_ai`); every `source_type="..."` written under `src/` (Gate (c)).
Finding: nothing enforces one source; a tick row sets no FK at all.
Consequence: a germ ticked in a draft is `source_type="creation"`, no FK (the tick precedent). An attached germ records its entity in `target_table="entity"`, `target_id` -- relational, so the metric reads no JSON (R-26).

### R-21 — the producer registry [M]
Opened: `src/world_engine/proposal_producers.py:1-45` (`PRODUCERS`, `LEGACY_PRODUCERS`, `PRODUCER_KINDS = ("model", "engine", "auto")`); `tooling/verify/checks/proposal_producers.py:1-30` (PP1: every `proposed_by` written equals `PRODUCERS`' keys; PP2: kinds in `PRODUCER_KINDS`), `:129-150` (`check_pp3`: for a site whose kind is `engine` or `model`, a `status=` keyword other than the constant `"proposed"` fails; another kind is skipped; it also fails with zero reviewed sites or zero `auto` modules); `dashboard_export.py:80` (the only other reader of a kind).
Finding: a germ born `approved` cannot be of kind `model` or `engine` (PP3).
Consequence: a fourth kind, `creator` (the creator ticked it), and the producer `creator_draft` (C-09). PP3 is unchanged.

### R-22 — the world's states [M]
Opened: `src/world_engine/models/canon_attribute.py:51-123` (`AttributeDefinition`: `name`, `kind` in `choice|integer|entity`, `default_integer`, `is_hidden`, `status`; `AttributeDefinitionType`: `side` `holder|value`, `entity_type`; `AttributeChoice`: `label`, `position`, `is_default`, `status`); `attributes.py:59` (`BUILTIN_ENTITY_TYPES = ("character", "location", "faction", "item")`), `:65-67` (`BUILTIN_TYPE_LABELS_FR = {"character": "Personnage", "location": "Lieu", "faction": "Faction", "item": "Objet"}`), `:83` (`SYSTEM_ATTRIBUTES`), `:97-111` (`AttributeView`: `key, name, kind, system, hidden, status, holder_types, value_types, choices, default`; `choices` are `(key, label)` pairs), `:190-201` (`world_attributes(db, world_id)`: system views first, then active definitions by name; `applies_to(view, entity_type)`: `holder_types is None or entity_type in holder_types`); `writes/attributes.py:72-88` (`ChoiceSpec(label, id=None)`; `DefinitionSpec(name, kind, holder_types, value_types=(), choices=(), default=None, is_hidden=False)`), `:265-283` (`write_attribute_definition(db, *, world_id, spec, definition_id=None)`: `clean_definition`, then the row, its types and choices, flushed), `:349-388` (`write_attribute_value(db, *, world_id, definition_id, entity_id, value, kind, changed_by, event_id=None)`: validates holder type and value, flushes, never commits, returns None when unchanged); `cockpit/routes/attributes.py:57` (`CHANGED_BY = "creator_crud"`), `:188-200` (`set_state` refuses a system key with 422).
Finding: a system attribute (`sys:` key) is read from canon columns and never written here.
Consequence: the premise lists non-system, active definitions that apply to the type; the create writes them with `write_attribute_value(..., kind="correction", changed_by="creator_crud")`.

### R-23 — skill systems [M]
Opened: `src/world_engine/models/canon.py:591-617` (`SkillSystem`: `world_id, name, description`; TICKET-0116 added `trial_to_rank_1..5` at `:610-615`, AMENDMENT-0124-01).
Consequence: the creator premise names the world's systems by `name`, ordered by name.

### R-24 — social relations [M]
Opened: `src/world_engine/writes/relations.py:412-440` (`write_oriented_relations(db, *, world_id, entity_a_id, entity_b_id, type, value, direction, visible_to_b=False, notes=None, changed_by, mode="set", relation_id=None) -> list[Relation]`, adds rows, never commits); `cockpit/crud/relations.py:126-152` (`_create_social_relation`: 409 when the perceiver already feels something toward the target; `value` 50 by default; `direction="mutual" if reciprocal else "a_to_b"`; commits); `relation_orientation.py:39-43` (`is_social(t)`: `t not in RELATION_GRAPH_EXCLUDED_TYPES`).
Consequence: the create writes a draft's links with `write_oriented_relations` directly (no commit), social types only; a new entity has no relation yet, so the 409 case cannot arise.

### R-25 — a location's neighbours, a character's place [M]
Opened: `src/world_engine/cockpit/play.py:853-880` (`_location_neighbours(location_id, db) -> list[tuple[str, str]]`: active locations joined by `connects_to`); CLAUDE.md INV-06 (its sole gameplay reader of `connects_to`); `models/canon.py:143-170` (`class Character`: `id` primary key and FK to `entity.id` (`:158`), `world_id`, `character_type` `player | npc` (`:163`), `current_location_id` (`:165`), indexed).
Consequence: `germ_candidates` imports it rather than reading `connects_to` itself.

### R-26 — the dashboard registries [M]
Opened: `src/world_engine/dashboard_deferrals.py:30-49` (`Deferral(code, ticket, deferred_fr, condition_fr, source, anchor, metric=None, status="open", follow_up=None)`; `_T0121 = "tooling/tickets/TICKET-0121-journee-quest-designer.md"`), `:150-170` (the last entries, `P1` of TICKET-0121); `dashboard_metrics.py:39-74` (`Scope`, `Row(group, label, value, of=None)`, `Metric(key, title, question, watches, dated, compute)`, `_in_worlds`, `_dated`), `:299-323` (`METRICS`, last `quest_requests`); `tooling/verify/checks/dashboard_registry.py:90-116` (`check_db1`: `(code, ticket)` unique; every text non-empty; the source exists and holds the anchor exactly once, whitespace folded; `metric` None, `EXPORT` or a `METRICS` key), `:124-140` (`check_db2`: unique keys; `dashboard_metrics.py` and the route module use no attribute `payload`, `original_payload`, `model_calls` and no `text(` call); `json_ui_boundary.py:44-48` (the payload exemption and its anchor sentence « First structured UI consumer must relationalize. »).
Consequence: the « Germes » metric counts by `status`, `source_type` and `target_table` only; the H2 and W2 anchors live in the ticket file; the exemption's comment line gains the pending-creation card, its anchor sentence untouched.

### R-27 — the Création right column [M]
Opened: `frontend/src/creation/Creation.svelte:164-232` (`#creation-editor-area`: the sidebar with `#author-entity-list`; `.right-col` holding `#creation-pending-strip` `:182-212`, the sheet `.transcript-panel` `:214-225` with `#author-main`, and `#creation-pj-skill` `:231`); `frontend/public/creation.css:280-284` (`.right-col` flex column), `:302-304` (`#creation-pj-skill { flex-shrink: 0; border-top: 2px solid var(--border); display: flex; flex-direction: column; max-height: 45%; overflow: hidden; }`); `frontend/public/shared.css:61-67` (`.transcript-panel { flex: 1; min-height: 0; ... }`); `frontend/src/creation/tabs.js:199-218` (`npc`: islands `entityList, entitySheet, npcAgent, linkAgent, pjSkillFiche`; `showPendingCreations: true`; slot `{ id: 'fiche', containerId: 'creation-pj-skill' }`), `:219-231` (`pj`), `:232-247` (`lieux`), `:248-260` (`factions`), `:451-461` (`containerVisible`), `:497-509` (`_creationActivateTab` loads or clears the pending list), `:730-749` (`loadPendingCreations`), `:752-768` (`generatePendingCreation`); `state.svelte.js:84-88` (`selectedEntityId`, `selectedRecordId`, `pendingCreations*`).
Finding: three blocks share one column; the skill sheet never shrinks and takes up to 45 %.
Consequence: L1 (brief H).

### R-28 — the island registry [M]
Opened: `frontend/src/creation/registry.js:481-490` (`pjSkillFiche`, origin `migration`), `:574-588` (`vocabulary`, `dashboard`: origin `new`, `createdBy`); `mount.js:50` (`COMPONENTS`); `tooling/verify/checks/creation_island.py:164` (`NEW_ALLOWED = {"containerId", "component", "origin", "createdBy"}`), `:52-131` (docstring of rule 2: a `new` entry has exactly those fields, `createdBy` matching `^TICKET-\d{4}$`; rule 4: every `containerId` is an element id of `Creation.svelte`; rule 5: every registry key is declared by an `islands` entry and back; rule 13: `Creation.svelte` imports and mounts no component).
Consequence: the germ panel and the world sheet are `new` islands (`germPanel`, `worldSheet`), each in `COMPONENTS`, each declared by the tabs that show it.

### R-29 — checks that read the frontend files this lot edits [M]
Opened: `grep -rln` over `tooling/verify/checks/` for each id and file (Gate (c)); `npc_skills.py:598-604` (shifted 24 lines by TICKET-0116, AMENDMENT-0124-01; C2: `tabs.js`'s `npc` entry contains `key: 'pjSkillFiche'` and `id: 'fiche', containerId: 'creation-pj-skill'`); `attributes.py:680` (AC3: `Sheet.svelte` contains `<StatesPanel entityId={detail.id}`); `creation_tab_switch.py:44-50` (rules 4-5 on `Sheet.svelte`'s branches); `creation_container_sizing.py:16-24` (a single-container entry's `#id` rule declares `flex: 1` and `min-height: 0`); `event_journal.py:678` (regex `\n  vocabulaire: \{(.*?)\n  \},`).
Finding: `creation-pending-strip`, `creation-pending-list`, `showPendingCreations`, `generatePendingCreation`, `EntityList.svelte` and `author-states` are read by no check.
Consequence: brief H keeps both C2 needles and the `<StatesPanel` line; the `monde` entry is a single-container entry (sizing rule applies); the `vocabulaire` entry is not edited.

### R-30 — the entity list and the sheet [M]
Opened: `frontend/src/creation/EntityList.svelte:307-388` (modes `loading, error, flat, lieux, record`); `Sheet.svelte:585-612` (`submitEntity`: the create body `entity, extension, facets, mutation_id, confirm_promotion, link_to, carrure`), `:693` (`isNew`), `:815-823` (the « créés à l'acceptation » knowledge and goals sections, `isNew && type === 'character' && tabKey === 'npc'`), `:832-836` (« États », `!isNew`, `<StatesPanel entityId={detail.id} />`); `pendingDrafts.svelte.js:15-45` (`pendingDraftsState`, `resetPendingDrafts`, `carrureForCreate`, ...); `generatePanel.svelte.js:57-92` (`applyCharacterDraft` fills `pendingDraftsState`), `:133-139` (`applyGeneratedDraft`); `sheetState.svelte.js:109` (`selectEntity`); file sizes: `Sheet.svelte` 890, `EntityList.svelte` 388 lines (frontend cap 1000).
Consequence: the draft's world block rides `pendingDraftsState` and a new component; `Sheet.svelte` gains one import, one section and three body keys.

### R-31 — the world-create modal [M]
Opened: `frontend/src/creation/WorldCrud.svelte:38-51` (name, description, laws fields); `worldCrud.svelte.js:34-36` (`createName`, `createDescription`, `createLaws`), `:66-71` (reset), `:95-100` (AI draft fill), `:107-125` (`worldCreateSubmit` posts `name, description, fundamental_laws`).
Consequence: brief J adds `createTone` beside them.

### R-32 — the Création tab registry [M]
Opened: `frontend/src/creation/tabs.js` (keys in order: `npc, pj, lieux, factions, objets, competences, region, constructeur, artefacts, registre, intrigues, evenements, quetes, dettes, vocabulaire, subjects, suivi, queue, prompts`), `:363-371` (`vocabulaire`: `archetype: 'bespoke'`, one container, one island, a `primaryAction`), `:383-391` (`suivi`: `primaryAction: null`); `frontend/public/creation.css:314-315` (`#creation-vocabulaire`, `#creation-suivi` `{ flex: 1; min-height: 0; overflow: auto; }`).
Consequence: `monde` is inserted after `vocabulaire`, shaped like `suivi`.

### R-33 — invariants and rule files [M]
Opened: CLAUDE.md and `.claude/rules/*.md` (highest id INV-63, `mutation-pipeline.md:48`); `.claude/rules/prompts.md` (front matter `paths:` `src/world_engine/prompt_*.py`, `writes/prompts.py`, `cockpit/crud/prompts.py`; INV-47, INV-48); `context-assembly.md` (INV-39: `_npc_dialogue_system_prompt` is the single npc_dialogue construction).
Consequence: the new invariant is INV-64, in `prompts.md`, which gains the path `src/world_engine/world_premise.py`.

## Contract sheet

Families first: C-03 (the regime family) is written before C-04 and C-07;
C-09/C-10/C-11 (the germ family) before C-13. Both re-read after their last
member.

### C-01 — `world.tone`
Produced by: BRIEF-0124-A   Consumed by: BRIEF-0124-B, J
Model: `World.tone: Optional[str] = None`, declared after `description`. DDL: `tone TEXT` (nullable, no default). Schema v2.30 (AMENDMENT-0124-01: v2.29 is TICKET-0116's).

### C-02 — one world, read and edited
Produced by: BRIEF-0124-A   Consumed by: BRIEF-0124-J
`GET /api/worlds/{world_id}` -> `{"id", "name", "description", "tone", "laws": [str, ...], "is_active"}` (`description`/`tone` as stored, `None` allowed; `laws` the `WorldLaw.text_` values by `position`). 404 unknown id.
`PUT /api/worlds/{world_id}` body `WorldUpdateBody(name: str, description: str = "", tone: str = "", laws: list[str] = [])` -> the same shape as GET. Writes `name` (stripped; empty -> 422 « Le nom est requis. »), `description` and `tone` (stripped; empty -> `None`), `updated_at`, then `write_world_laws(db, world=world, laws=body.laws, changed_by="creator")`; one commit. 404 unknown id. Does not touch `is_active` or `current_phase`. Any world, active or not.
`WorldCreateBody` gains `tone: str = ""`; `create_world` writes it (stripped; empty -> `None`).

### C-03 — the premise regime of every usage
Produced by: BRIEF-0124-B   Consumed by: BRIEF-0124-C, D
`PromptSpec` gains, after `default_model`: `premise: str` (no default) and `premise_reason: str = ""`. `premise` is one of `PREMISE_REGIMES = ("creator", "player", "none")` (declared in `world_premise.py`); `premise_reason` is non-empty exactly when `premise == "none"`.
- `creator` (14): `entity_generation`, `player_generation`, `skill_catalogue`, `npc_goal_generation`, `agenda_generation`, `event_generation`, `region_manifest`, `room_batch_manifest`, `npc_link_pair`, `lore_statement_questions`, `lore_statement_to_proposal`, `quest_subject`, `quest_design`, `quest_trial` (AMENDMENT-0124-01: TICKET-0116's rank-trial designer, the nature of `quest_design`).
- `player` (15): `npc_dialogue`, `npc_initiative_act`, `player_narration`, `mj_interpretation`, `mj_arbitration`, `mj_establishment`, `mj_gathering`, `mj_initiative`, `observation_intent`, `observation_narration`, `world_tick`, `world_tick_events`, `day_plan`, `day_narration`, `day_rewrite`.
- `none` (18), with its reason, verbatim:
  - `world_generation` -- "Drafts the world itself: there is no premise yet."
  - `room_batch_coherence` -- "Judges a staged batch against canon; writes no fiction."
  - `npc_link_coherence` -- "Judges staged links against canon; writes no fiction."
  - `npc_batch_placement` -- "Assigns given character lines to given places; writes no fiction."
  - `lore_question_to_plan` -- "Plans selectors from a question; carries no world content."
  - `lore_rows_to_prose` -- "Renders canon rows as they stand; must add nothing to them."
  - `condition_interpret` -- "Translates the creator's sentence into a condition tree."
  - `mj_speaker_selection` -- "Picks one speaker among a given roster."
  - `conversation_analysis` -- "Classifies a transcript into proposals."
  - `overhearing_classification` -- "Classifies what was overheard into proposals."
  - `conversation_summary` -- "Compresses a transcript."
  - `day_extract_place`, `day_extract_person`, `day_extract_faction` -- "Extracts mentions; already framed by world_frame."
  - `day_feasibility` -- "Vetoes steps; already framed by world_frame."
  - `day_reconcile` -- "Routes a declaration to an open plan."
  - `day_plan_select` -- "Routes a declaration to an open plan."
  - `day_mention_choice` -- "Picks one candidate among the code's."

### C-04 — `world_premise.py`
Produced by: BRIEF-0124-B   Consumed by: BRIEF-0124-C, D, G
Module `src/world_engine/world_premise.py`, read-only (no `add`, `commit`, `delete`, `execute`, `flush`; never names `PromptVersion`).
- `PLACEHOLDER = "{world_premise}"`; `VARIABLE = "world_premise"`; `PREMISE_REGIMES = ("creator", "player", "none")`.
- `regime_of(usage: str) -> str`: `PROMPT_REGISTRY[usage].premise`; `"none"` for a usage the registry does not hold.
- `world_premise(db: Session, regime: str, *, entity_type: Optional[str] = None) -> str`. The active world (`World.is_active == True`); none, or `regime == "none"` -> `""`. Otherwise the block below, each line present only when its content is non-empty, the whole block `""` when nothing but the name would show; a non-empty block ends with `"\n\n"`:
  ```
  === CADRE DU MONDE ===
  Monde : {world.name}
  {world.description}
  Ton et style : {world.tone}
  Lois fondamentales — vraies partout, connues de tous et observables :
  - {law 1}
  - {law 2}
  Systèmes de compétences : {name 1} ; {name 2}
  États que porte chaque {type label} de ce monde — propose une valeur pour chacun :
  - {name} (un parmi : {label 1}, {label 2} ; par défaut {default label})
  - {name} (un entier ; par défaut {default})
  - {name} (une entité : {value type labels})
  === FIN DU CADRE ===
  ```
  `regime == "player"`: name, description, tone and laws only. `regime == "creator"`: also the skill systems (`SkillSystem.name` of the world, by name); and, only when `entity_type` is given, the states: every view of `attributes.world_attributes(db, world.id)` with `not view.system`, `view.status == "active"` and `applies_to(view, entity_type)`, in that order; a hidden one ends with ` — caché du joueur`; a `choice` without default omits `; par défaut ...`; an `integer` with `default None` omits it. `{type label}` is `BUILTIN_TYPE_LABELS_FR[entity_type].lower()`, else `entity_type`. A value type label is `BUILTIN_TYPE_LABELS_FR.get(t, t).lower()`, joined with `, `. The States header and lines appear only when at least one state applies.
- `fill(text: str, db: Session, usage: str, *, entity_type: Optional[str] = None) -> str`: `text` unchanged when it does not hold `PLACEHOLDER` (no query is run); otherwise every occurrence replaced by `world_premise(db, regime_of(usage), entity_type=entity_type)` (`""` for a `none` usage).
- `missing_premise(usage: str, system_prompt: str, user_template: str) -> Optional[str]`: for a `creator` or `player` usage, the French refusal « Le cadre du monde {world_premise} est obligatoire pour ce prompt. » when neither text holds `PLACEHOLDER`; for a `none` usage, « Ce prompt ne reçoit pas le cadre du monde : retirez {world_premise}. » when either text holds it; else `None`.

### C-05 — `prompt_store.premised_prompt`
Produced by: BRIEF-0124-B   Consumed by: BRIEF-0124-C
`@dataclass(frozen=True) class PremisedPrompt: id: str; version_number: int; system_prompt: str; user_template: str`.
`premised_prompt(db: Session, template: PromptTemplate, *, entity_type: Optional[str] = None) -> PremisedPrompt`: `version = current_prompt(db, template)`; both texts through `world_premise.fill(text, db, template.usage, entity_type=entity_type)` (imported inside the function body); `id`, `version_number` copied. Same RuntimeError as `current_prompt` on a versionless head. Added to `__all__`.

### C-06 — `call_json` fills the premise
Produced by: BRIEF-0124-B   Consumed by: nothing in this lot (behavior of four usages)
After `spec = prompt_load.load(db, usage)`: `system_prompt = fill(spec.system_prompt, db, usage)`; the user message starts from `fill(spec.user_template, db, usage)` and then replaces `values` as today; `model_exchange.begin` and `chat` receive the filled `system_prompt`. `fill` imported as `from .world_premise import fill`.

### C-07 — the render sites
Produced by: BRIEF-0124-C   Consumed by: the check of C (WP3)
Each `current_prompt(db, X)` below becomes `premised_prompt(db, X)` (same arguments; the two `entity_author` sites add `entity_type=`), nothing else on the line:
| file:line (main) | function | usage |
|---|---|---|
| `entity_author.py:451` | `_entity_draft_call` | entity_generation (`entity_type=entity_type`) |
| `entity_author.py:692` | `_player_draft_call` | player_generation |
| `entity_author.py:810` | `generate_skill_catalogue_draft` | skill_catalogue |
| `entity_author.py:866` | `generate_npc_goals` | npc_goal_generation (`entity_type="character"`) |
| `event_author.py:80` | `generate_agenda_draft` | agenda_generation |
| `event_author.py:176` | `_event_draft_call` | event_generation |
| `region_author.py:245` | `generate_region_manifest` | region_manifest |
| `room_batch_author.py:345` | `generate_room_batch_manifest` | room_batch_manifest |
| `link_author.py:363` | `_render_pair_messages` | npc_link_pair |
| `cockpit/play.py:204` | `_say_load_prompts` | player_narration |
| `cockpit/play.py:205` | `_say_load_prompts` | mj_interpretation |
| `cockpit/play.py:578` | `_say_npc_generation` | npc_dialogue |
| `cockpit/play_initiative.py:109` | `_say_initiative_context` | npc_dialogue |
| `cockpit/play_initiative.py:120` | `_say_initiative_context` | npc_initiative_act |
| `cockpit/play_initiative.py:501` | `_initiative_vote_call` | mj_initiative |
| `cockpit/play_physical.py:120` | `_say_physical_roster_and_arbiter` | mj_arbitration |
| `cockpit/play_physical.py:207` | `_say_physical_npc_reaction` | npc_dialogue |
| `cockpit/play_physical.py:702` | `_build_establishment_narration` | mj_establishment |
| `cockpit/routes/play.py:111` | `start_conversation` | npc_dialogue |
| `cockpit/routes/prompts.py:61` | `preview_prompt_npc_dialogue` | npc_dialogue |
| `cockpit/routes/prompts.py:100` | `preview_prompt_player_narration` | player_narration |
| `cockpit/routes/scene.py:215` | `_scene_join_already_member` | npc_dialogue |
| `cockpit/routes/scene.py:253` | `_scene_join_resolve_and_create` | mj_interpretation |
| `cockpit/routes/scene.py:291` | `_scene_join_create_for_gathering` | npc_dialogue |
| `gathering.py:105` | `_request_partition` | mj_gathering |
| `observation_engine.py:102` | `_observation_intent_messages` | observation_intent |
| `observation_runner.py:343` | `_generate_act_line` | npc_dialogue |
| `observation_runner.py:347` | `_generate_act_line` | npc_initiative_act |
| `observation_runner.py:401` | `_generate_mj_narration` | observation_narration |
| `tick.py:329` | `_tick_call_scope_model` | world_tick_events |
| `tick.py:490` | `run_world_tick` | world_tick |
| `day_plan.py:369` | `emit_plan` | day_plan |
| `day_narration.py:158` | `narrate` | day_narration |
| `day_narration.py:185` | `rewrite` | day_rewrite |

That is 34 rows, one per call. The closed list that stays on `current_prompt`, by `path::function` (`STAYS`):
`analyzer_transcript.py::_window_call_model` (conversation_analysis), `analyzer_transcript.py::_overhearing_classify` (overhearing_classification), `cockpit/crud/prompts.py::_prompt_row_summary` (version number only), `cockpit/crud/prompts.py::get_prompt_detail` (the editor shows the raw text), `context_window.py::summarize_older_lines` (conversation_summary), `day_choice.py::_ask` (day_mention_choice), `day_extract.py::_extract` (day_extract_*), `day_feasibility.py::veto` (day_feasibility), `day_plan_select.py::select_plan` (day_plan_select), `day_reconcile.py::reconcile` (day_reconcile), `entity_author.py::generate_world_draft` (world_generation), `link_context.py::render_coherence_messages` (npc_link_coherence), `npc_group_author.py::_run_placement_call` (npc_batch_placement), `observation_runner.py::_pin_templates` (version numbers only), `prompt_coverage.py::missing_usages` (coverage), `prompt_load.py::load` (filled by `call_json`, C-06), `room_batch_author.py::propose_batch_coherence` (room_batch_coherence), `cockpit/play_initiative.py::_select_group_speaker` (mj_speaker_selection).
`region_author.py:248-249`: `world_description` and `world_fundamental_laws` are replaced with `""` (the premise carries both); the reads of `world.description` and `WorldLaw` at `:233-242` are removed.

### C-08 — the texts, the seed, the delivery, the guard
Produced by: BRIEF-0124-D   Consumed by: nothing in this lot
- `seed_pilot.premised_texts(usage: str, system_prompt: str, user_template: str, variables: Optional[list[str]]) -> tuple[str, str, Optional[list[str]]]`: for a `creator`/`player` usage, `system_prompt` prefixed with `PLACEHOLDER` unless either text already holds it, and `VARIABLE` appended to `variables` (a copy; `[VARIABLE]` when `None`) unless present; a `none` usage returns its arguments unchanged. `upsert_prompt_template` resolves `usage = head_fields.get("usage")` and passes its texts and variables through `premised_texts` before both writes (virgin head) and before the variables write (existing head). The seed constants are not edited.
- `REGION_MANIFEST_USER_TEMPLATE` (`seed_pilot.py:1437-1440`): its leading `{world_description}{world_fundamental_laws}` is removed; the head's `variables` keep both names (C-07: the code still replaces them, with `""`).
- `scripts/apply_ticket_0124_world_premise.py`: env guard (the 0121 script's), one `Session(engine)`; for each `PROMPT_REGISTRY` usage whose regime is not `none`, every active `PromptTemplate` of that usage: its variables gain `world_premise` (`write_prompt_variables`, the existing list plus it, when absent); its current text, when neither field holds `PLACEHOLDER`, gets `PLACEHOLDER` prefixed to `system_prompt` as one `write_prompt_version(..., note=NOTE)`, `NOTE = "TICKET-0124 BRIEF-0124-D -- the world premise (P1)"`; one commit; prints `{id}: vN -> vN+1` or `{id}: unchanged (vN)`. Idempotent. Writes nothing else.
- P1-g: `update_prompt_text` and `restore_prompt_version` call `missing_premise(row.usage, system, user)` before `write_prompt_version`; a non-None answer raises `HTTPException(422, <that text>)`, nothing written.

### C-09 — the create's world extras
Produced by: BRIEF-0124-E   Consumed by: BRIEF-0124-F, I
`EntityWriteBody` gains `states: list[dict] = []` (`{"key": definition_id, "value": choice_id | int | entity_id | None}`), `relations: list[dict] = []` (`{"other_entity_id", "type", "notes": str | None}`), `germs: list[dict] = []` (`{"name", "entity_type", "concept", "link_type"}`). Honoured on create only; a non-empty list on `PUT` is a 422.
`cockpit/crud/entity_extras.py::write_create_extras(db, entity, body) -> dict` runs after `_create_entity_core` and before the route's commit; returns `{"states": n, "relations": n, "germs": [mutation_id, ...]}` and the route adds it to its response under `"world_extras"`. A `ValueError` from a writer, an unknown or system state key, a relation to an entity outside the world or to itself, a non-social type, or a germ type outside `("character", "location", "faction")` is a 422, nothing written (the route rolls back).
- states: `write_attribute_value(db, world_id=entity.world_id, definition_id=key, entity_id=entity.id, value=value, kind="correction", changed_by="creator_crud")`.
- relations: `write_oriented_relations(db, world_id=..., entity_a_id=entity.id, entity_b_id=other_entity_id, type=type, value=50, direction="a_to_b", visible_to_b=False, notes=notes, changed_by="creator_crud")`.
- germs: one `ProposedMutation(world_id=entity.world_id, source_type="creation", mutation_type="entity_creation", status="approved", proposed_by="creator_draft", payload={...C-10 draft germ...}, rationale="coché dans le brouillon de " + entity.name, creator_notes="en attente de réalisation — onglet Création")` each; no FK set (R-20). A germ whose name collides with an active entity, or with an open germ (`_germ_blocked` of `day_concordance.py`, imported), is skipped and named in the response under `"germs_skipped"`.
- `proposal_producers.PRODUCERS["creator_draft"] = ("creator", "Création — germe coché dans un brouillon")`; `PRODUCER_KINDS = ("model", "engine", "auto", "creator")`.

### C-10 — the germ payloads and the brief composed from them
Produced by: BRIEF-0124-E (draft germs), BRIEF-0124-F (Journée germs, compose)   Consumed by: BRIEF-0124-F, G, H
- Draft germ payload: `{"entity_type", "name", "concept", "origin_entity_id", "link_type"}`.
- Journée germ payload: today's keys (R-17) plus `"source_sentence"` (the sentence of `pass_play.declared_action` that holds `mention.surface_form`, compared through `lore_resolve.normalize_surface`; the whole declaration, truncated to 300 characters, when none holds it) and `"anchor_name"` (`Entity.name` of `candidate_location_id`, or `None`).
- `_compose_entity_creation_brief(payload, db)` writes, in order: the intro sentence (unchanged); the concept (unchanged); `"Lieu : {anchor_name}."` when `anchor_name`, else — when `anchor` equals `candidate_location_id` (a Journée germ born before this lot) — `"Lieu : {that entity's name}."`, else the `anchor` prose (a tick germ, unchanged); `"Mentionné ainsi : « {source_sentence} »."` when present; `"Lié à {origin name} ({link_type})."` when `origin_entity_id` resolves.

### C-11 — the germ routes and the pending item
Produced by: BRIEF-0124-F   Consumed by: BRIEF-0124-G, H
- Pending item (`GET /api/creations/pending`): today's keys, with `source` one of `"tick"` (`tick_id`), `"journee"` (`pass_play_id`), `"creation"` (`source_type == "creation"`), `"conversation"` (otherwise), plus `"anchor_name"`, `"source_sentence"`, `"origin_entity_id"`, `"origin_name"`, `"link_type"` (each `None` when absent).
- `germ_candidates(db, mut) -> list[dict]` in `cockpit/routes/creator.py`: for a `character` germ, the active non-player characters whose `current_location_id` is the germ's location (`candidate_location_id`, or for a `creation` germ the origin character's `current_location_id`) or one of its `_location_neighbours`, ordered by name, at most `MAX_GERM_CANDIDATES = 12`; each `{"entity_id", "name", "location_name", "reason"}`, `reason` « au même lieu » or « lieu voisin ». Any other type, or no location: `[]`.
- `GET /api/creations/{mutation_id}/candidates` -> `{"mutation_id", "candidates": [...]}`; 409 when the row is not an approved, unrealized `entity_creation`.
- `POST /api/creations/{mutation_id}/attach` body `{"entity_id"}` -> `{"ok": True, "mutation_id", "entity_id", "name"}`. Guards: the germ as above (409); the entity active, in the germ's world, of the germ's `entity_type` (422). Sets `target_table="entity"`, `target_id=entity_id`, `creator_notes` += « rattaché à une entité existante : {name} », then `_link_entity_creation(mutation_id, entity_id, db)` (which applies and commits); its failure is a 409 with its error.
- `generate_creation_draft` returns the germ's candidates as `"candidates"` (BRIEF-0124-F); BRIEF-0124-G passes their ids to the draft (C-13) and prepends a `creation` germ's origin link.

### C-12 — the « Germes » metric and two deferrals
Produced by: BRIEF-0124-F   Consumed by: nothing in this lot
- `Metric("germs", "Germes de création", "Que deviennent les germes, et combien rejoignent une fiche existante ?", ("H2",), True, _germs)`, appended to `METRICS`. Rows over `entity_creation` rows in scope (`_in_worlds(ProposedMutation.world_id)`, `_dated(ProposedMutation.proposed_at)`), grouped by source label (`"Journée"`: `source_type == "pass_play"`; `"Tick"`: `"world_tick"`; `"Brouillon"`: `"creation"`; `"Conversation"`: otherwise): `Row(group, "Proposés", n_proposed, n)`, `Row(group, "En attente de réalisation", n_approved, n)`, `Row(group, "Réalisés en nouvelle fiche", n_applied_new, n)` (`applied`, `target_table` NULL), `Row(group, "Rattachés à une fiche existante", n_attached, n)` (`applied`, `target_table == "entity"`), `Row(group, "Rejetés", n_rejected, n)`; a group with `n == 0` is omitted. Note: « Ce que deviennent les germes ; H2 regarde les germes de Journée rattachés. »
- `_T0124 = "tooling/tickets/TICKET-0124-world-premise.md"`; `Deferral("H2", "TICKET-0124", "Le modèle reconnaît en jeu un personnage existant derrière un rôle.", "Des germes de Journée que Nia rattache à une fiche existante.", _T0124, "H2 (the model recognises an existing character in play; reactivation: Journée germs the creator attaches to an existing character)", metric="germs")`; `Deferral("W2", "TICKET-0124", "Garder l'historique des lois du monde.", "Un writer passe world_law_id= à un fait.", _T0124, "W2 (law history; reactivation: a writer passes world_law_id= to a fact)")`.

### C-13 — the draft's world block
Produced by: BRIEF-0124-G   Consumed by: BRIEF-0124-I
`draft_world.py`:
- `WORLD_FIELDS: dict[str, str]` for `character`, `location`, `faction` (verbatim in BRIEF-0124-G), appended to `_TYPE_FIELDS[entity_type]` inside `_entity_draft_call`.
- `known_names_block(db, world_id, entity_type, candidate_ids=()) -> str`: « Entités existantes que tu peux nommer (nom exact) : » then one `- {name} ({type label})` line per entity: `candidate_ids` first (in order), then active characters (non-player) by name, then factions by name, then locations by name, skipping repeats, at most `MAX_KNOWN_NAMES = 60` lines; `""` when none.
- `resolve_world_block(db, world_id, entity_type, public_in, draft_name, notes) -> dict` returns `{"states": [...], "links": [...], "same_as": {...} | None, "to_create": [...]}` -- the rules and the shapes are BRIEF-0124-G's case table (Gate (b), table 3).
- `generate_entity_draft(entity_type, brief, db, *, candidate_ids=())` sets `result["draft"]["world"]` (always present, possibly empty lists and `None`).

### C-14 — frontend state for germs, panes and the draft's world block
Produced by: BRIEF-0124-H (germ, panes), BRIEF-0124-I (world draft)   Consumed by: BRIEF-0124-H, I
- `creationState.selectedGermId: null | string`, `creationState.sheetPane: 'fiche' | 'competences'` (default `'fiche'`), `creationState.germLinkTarget: null | { entity_id, name }` (set by « Créer et lier », consumed and cleared by `applyGeneratedDraft`). `selectEntity` and `_creationActivateTab` set `selectedGermId = null`; `_creationActivateTab` sets `sheetPane = 'fiche'` and `germLinkTarget = null`.
- `tabs.js` exports `selectGerm(mutationId)`, `loadGermCandidates(mutationId)`, `attachGerm(mutationId, entityId)`.
- `germPanel` island (`GermPanel.svelte`, container `creation-germ-panel`), declared by `npc`, `lieux`, `factions`.
- `pendingDraftsState.world = { states: [], links: [], sameAs: null, toCreate: [] }`, each list item carrying `checked: boolean`; `resetPendingDrafts` resets it; `worldExtrasForCreate() -> { states, relations, germs }` in the C-09 shapes (checked items only).

### C-15 — the « Monde » page
Produced by: BRIEF-0124-J   Consumed by: nothing in this lot
`CREATION_TABS.monde = { label: 'Monde', archetype: 'bespoke', containers: ['creation-monde'], loader: null, state: { onTabEnter: null, onWorldSwitch: null }, islands: [{ key: 'worldSheet', containerId: 'creation-monde' }], primaryAction: null }`, inserted after `vocabulaire`; registry `worldSheet` (`WorldSheet.svelte`, origin `new`, `createdBy: 'TICKET-0124'`); `#creation-monde { flex: 1; min-height: 0; overflow: auto; }`.

## Gate output

### (a) Property trace

| property asserted | finding | declaring file opened |
|---|---|---|
| `World` has no `tone`; its columns | R-01 | `models/canon.py:63-88` |
| `world` is canon; its four sanctioned sites | R-01 | `canon_write_policy.txt:2, :133-140` |
| `write_world_laws` signature, raw delete, no commit | R-02 | `writes/config.py:109-130` |
| `fact.world_law_id` is an FK to `world_law` | R-02 | `models/canon_knowledge.py:108` |
| no world GET/PUT; `WorldCreateBody` fields | R-03 | `routes/creator.py` (`@router` lines), `:408-411` |
| schema version v2.29 in code and doc (AMENDMENT-0124-01) | R-04 | `schema_version.py:15`, `world-engine-schema.md:3` |
| migration `ADD COLUMN` form | R-04 | `migrate_v2_27_mutation_reviews.py:116` |
| `PromptSpec` five fields, frozen | R-05 | `prompt_registry.py:54-60` |
| the registry check asserts five fields, forbids none | R-05 | `checks/prompt_registry.py:130-132` |
| `current_prompt` returns the ORM row | R-06 | `prompt_store.py:19-36` |
| `PromptVersion` may be named only in four places | R-06 | `checks/prompt_version.py` (rule 2 implementation) |
| the 53 `current_prompt(` calls and their usages | R-07 | each module (Gate (c)) |
| `call_json` body; NA2's import and call bans | R-08 | `prompt_call.py:27-44`; `checks/condition_interpreter.py:270-295` |
| `prompt_load` touches only prompt tables | R-09 | `prompt_load.py:1-71` |
| `day_choice` stubs `current_prompt` | R-10 | `checks/day_choice.py:242` |
| placeholder validation in `write_prompt_version` | R-11 | `writes/prompts.py:44-117` |
| the two edit routes and their 422 | R-11 | `cockpit/crud/prompts.py:245-304` |
| five checks write premise usages without placeholder | R-12 | the five check files, lines cited |
| `upsert_prompt_template` S2 and variables full replace | R-13 | `seed_pilot.py:132-185` |
| ET1/EL1 compare delivered text to constants | R-13 | `checks/event_tick.py:125-140`, `checks/event_lore.py:130-148` |
| region reads description and laws | R-14 | `region_author.py:233-251` |
| `_TYPE_FIELDS`, `_entity_draft_call`, `_world_id` | R-15 | `entity_author.py` lines cited |
| pending item shape, source label rule | R-16 | `routes/creator.py:155-189` |
| Journée germ payload; `Mention` fields; `declared_action` | R-17 | `day_concordance.py:502-511`, `day_extract.py:42-46`, `models/pipeline.py:80` |
| occupation rung; inferred mentions excluded from choice | R-18 | `day_concordance.py:218-243`, `day_choice.py:94-116` |
| `EntityWriteBody` fields; create commit order; link guards | R-19 | `crud/entities.py:382-404, :702-775` |
| `proposed_mutation` has no CHECK; tick sets no FK | R-20 | `models/pipeline.py:99-150` |
| PP3 forbids an approved `model`/`engine` row | R-21 | `checks/proposal_producers.py` (PP3 implementation) |
| attribute models; `AttributeView`; `write_attribute_value` | R-22 | `models/canon_attribute.py:51-123`, `attributes.py:88-104, :190-201`, `writes/attributes.py:349-388` |
| `SkillSystem.name` | R-23 | `models/canon.py:591-611` |
| `write_oriented_relations` adds, never commits | R-24 | `writes/relations.py:412-440` |
| `_location_neighbours` signature | R-25 | `cockpit/play.py:853-880` |
| `Deferral`, `Metric`, `Row` shapes; DB1/DB2 | R-26 | `dashboard_deferrals.py:30-49`, `dashboard_metrics.py:39-74`, `checks/dashboard_registry.py` (DB1/DB2 implementation `:90-140`) |
| right column structure and CSS | R-27 | `Creation.svelte:164-232`, `creation.css:280-304`, `shared.css:61-67` |
| `new` island field set; container rule; no direct mount | R-28 | `checks/creation_island.py` (rules 2, 4, 5, 13 implementation) |
| C2 and AC3 needles | R-29 | `checks/npc_skills.py:574-580`, `checks/attributes.py:680` |
| create body in `submitEntity`; create-mode sections | R-30 | `Sheet.svelte:585-612, :815-836` |
| world-create modal fields | R-31 | `WorldCrud.svelte:38-51`, `worldCrud.svelte.js:107-125` |
| tab keys and the `suivi` shape | R-32 | `tabs.js:363-391`, `creation.css:314-315` |
| next invariant id INV-64 | R-33 | CLAUDE.md and `.claude/rules/*.md` |

Presuppositions: no brief says « follow the existing convention » without naming its file and pattern; each « as in X » names X with lines.

### (b) Case tables

**1. `fill` by regime and text (C-04).**
| usage regime | text holds `{world_premise}` | active world | result |
|---|---|---|---|
| creator | no | any | text unchanged, no query |
| creator | yes | none | placeholder -> `""` |
| creator | yes | yes, nothing but a name | `""` |
| creator | yes | yes, content | creator block (+ states when `entity_type`) |
| player | yes | yes, content | player block (no skill systems, no states) |
| player | yes | yes, a hidden state applies | player block, the state absent |
| none | yes | yes | placeholder -> `""` (the guard refuses such a text at the routes) |
| unknown usage | yes | yes | treated as `none` |

**2. P1-g at the two routes (C-08).**
| regime | system holds | user holds | answer |
|---|---|---|---|
| creator/player | yes | — | written |
| creator/player | no | yes | written |
| creator/player | no | no | 422 « Le cadre du monde ... est obligatoire ... » |
| none | no | no | written |
| none | yes or — | — or yes | 422 « Ce prompt ne reçoit pas le cadre du monde ... » |
A restore of a pre-0124 version of a creator/player head falls on row 3.

**3. The draft's world block (C-13; BRIEF-0124-G applies it).**
| input | condition | output |
|---|---|---|
| `states[i].state` | names (casefold) an applicable active non-system definition, first time | kept |
| same | names none, or a second time | dropped, note « État inconnu ou répété ignoré : … » |
| value, `choice` | equals an active label through `normalize_surface` | `value` = choice id, `label` = the label |
| value, `choice` | no label matches | dropped, note |
| value, `integer` | an `int`, or a string of an int | `value` = int |
| value, `integer` | anything else | dropped, note |
| value, `entity` | names (casefold) an active entity of the world whose type is a value type | `value` = id, `label` = name |
| value, `entity` | names none, a value type in `character|location|faction` exists | `to_create` gains `{name: value, entity_type: that type, concept: "{state} de {draft name}", link_type: state name}` |
| value, `entity` | names none, no such value type | dropped, note |
| `links[i]` | names an active entity of the world (not the draft), `type` non-empty and `is_social` | kept `{entity_id, name, type, note}` |
| same | `type` empty or not social | dropped, note |
| same | names no entity | `to_create` gains `{name, entity_type: "character", concept: note, link_type: type}` |
| `same_as` | `entity_type == "character"` and names an active non-player character | `{entity_id, name}` |
| same | otherwise | `None` (a non-empty unresolved name is noted) |
| `to_create[i]` | non-empty name, type in the three, name free | kept (after the derived ones, deduplicated by casefold) |
| same | name of an active entity | dropped, note « existe déjà : … » |
| `to_create` | more than `MAX_DRAFT_GERMS = 3` | first three kept, note |

**4. Pending item `source` (C-11).**
| `tick_id` | `pass_play_id` | `source_type` | `source` |
|---|---|---|---|
| set | — | any | tick |
| — | set | any | journee |
| — | — | creation | creation |
| — | — | other | conversation |

**5. `attach` guards (C-11).**
| germ row | entity | answer |
|---|---|---|
| missing, not `entity_creation`, not `approved`, or realized | — | 409 |
| valid | missing, inactive, other world, other type | 422 |
| valid | valid | 200, `applied`, `target_table="entity"` |

### (c) Enumerations

`@router` lines of `cockpit/routes/creator.py` (R-03):
```
$ grep -n "@router\.\(put\|patch\|post\|get\|delete\)(\"/api/worlds" src/world_engine/cockpit/routes/*.py
src/world_engine/cockpit/routes/creator.py:227:@router.post("/api/worlds/generate")
src/world_engine/cockpit/routes/creator.py:380:@router.get("/api/worlds")
src/world_engine/cockpit/routes/creator.py:389:@router.post("/api/worlds/{world_id}/activate")
src/world_engine/cockpit/routes/creator.py:414:@router.post("/api/worlds")
src/world_engine/cockpit/routes/creator.py:464:@router.delete("/api/worlds/{world_id}")
```

No writer passes `world_law_id=` (R-02):
```
$ grep -rn "world_law_id=" src scripts --include=*.py | grep -v "world_law_id=world_law_id\|def \|Optional"
(no output)
```

`WorldLaw` readers outside models and writes (R-14):
```
$ grep -rn "WorldLaw\|world_law\b\|world_laws\|read_world_laws" src --include=*.py | grep -v "^src/world_engine/models"
src/world_engine/region_author.py:37:from .models import PromptTemplate, World, WorldLaw
src/world_engine/region_author.py:236:        select(WorldLaw).where(WorldLaw.world_id == world.id).order_by(WorldLaw.position)
src/world_engine/writes/worlds.py:76:    "world_law", "quest", "quest_offer", "quest_offer_step",
src/world_engine/writes/config.py:9..127 (write_world_laws)
src/world_engine/writes/__init__.py:34, :104
src/world_engine/writes/facts.py:35, :149
src/world_engine/facets.py:7
src/world_engine/cockpit/routes/mutations.py:83, :93 (imports)
src/world_engine/cockpit/routes/creator.py:50, :427 (create_world)
```

The 47 registry usages (R-05) and their seeded heads (R-13), each seeded exactly once (re-listed on `386c01a`, AMENDMENT-0124-01):
```
npc_dialogue pt-npc-dialogue | npc_initiative_act pt-npc-initiative-act | player_narration pt-mj-narration
mj_interpretation pt-mj-interpretation | mj_arbitration pt-mj-arbiter | mj_establishment pt-mj-establishment
mj_gathering pt-mj-gathering | mj_speaker_selection pt-mj-speaker | mj_initiative pt-mj-initiative
observation_intent pt-observation-intent | observation_narration pt-observation-narration
conversation_analysis pt-conversation-analysis | overhearing_classification pt-overhearing-classification
entity_generation pt-entity-generation | world_generation pt-world-generation | player_generation pt-player-generation
skill_catalogue pt-skill-catalogue | npc_goal_generation pt-npc-goals | agenda_generation pt-agenda-draft
event_generation pt-event-draft | region_manifest pt-region-manifest | room_batch_manifest pt-room-batch-manifest
room_batch_coherence pt-room-batch-coherence | npc_link_pair pt-npc-link-pair | npc_link_coherence pt-npc-link-coherence
npc_batch_placement pt-npc-batch-placement | lore_question_to_plan pt-lore-question-to-plan
lore_rows_to_prose pt-lore-rows-to-prose | lore_statement_questions pt-lore-statement-questions
lore_statement_to_proposal pt-lore-statement-to-proposal | condition_interpret pt-condition-interpret
quest_subject pt-quest-subject | quest_design pt-quest-design | quest_trial pt-quest-trial (TICKET-0116)
world_tick pt-world-tick
world_tick_events pt-world-tick-events | day_plan pt-day-plan | day_extract_place pt-day-extract-place
day_extract_person pt-day-extract-person | day_extract_faction pt-day-extract-faction | day_narration pt-day-narration
day_rewrite pt-day-rewrite | day_feasibility pt-day-feasibility | day_reconcile pt-day-reconcile
day_plan_select pt-day-plan-select | day_mention_choice pt-day-mention-choice | conversation_summary pt-conversation-summary
```

Every function calling `current_prompt(` under `src/` (R-07), AST walk, with its usage (resolved from the loader each function calls):
```
analyzer_transcript.py:_window_call_model:[575]            conversation_analysis
analyzer_transcript.py:_overhearing_classify:[705]         overhearing_classification
cockpit/crud/prompts.py:_prompt_row_summary:[112]          (version number)
cockpit/crud/prompts.py:get_prompt_detail:[166]            (editor text)
cockpit/play.py:_say_load_prompts:[204, 205]               player_narration, mj_interpretation
cockpit/play.py:_say_npc_generation:[578]                  npc_dialogue
cockpit/play_initiative.py:_say_initiative_context:[109, 120]  npc_dialogue, npc_initiative_act
cockpit/play_initiative.py:_select_group_speaker:[305]     mj_speaker_selection
cockpit/play_initiative.py:_initiative_vote_call:[501]     mj_initiative
cockpit/play_physical.py:_say_physical_roster_and_arbiter:[120]  mj_arbitration
cockpit/play_physical.py:_say_physical_npc_reaction:[207]  npc_dialogue
cockpit/play_physical.py:_build_establishment_narration:[702]  mj_establishment
cockpit/routes/play.py:start_conversation:[111]            npc_dialogue
cockpit/routes/prompts.py:preview_prompt_npc_dialogue:[61] npc_dialogue
cockpit/routes/prompts.py:preview_prompt_player_narration:[100]  player_narration
cockpit/routes/scene.py:_scene_join_already_member:[215]   npc_dialogue
cockpit/routes/scene.py:_scene_join_resolve_and_create:[253]  mj_interpretation
cockpit/routes/scene.py:_scene_join_create_for_gathering:[291]  npc_dialogue
context_window.py:summarize_older_lines:[207]              conversation_summary
day_choice.py:_ask:[227]                                   day_mention_choice
day_extract.py:_extract:[109]                              day_extract_*
day_feasibility.py:veto:[189]                              day_feasibility
day_narration.py:narrate:[158]                             day_narration
day_narration.py:rewrite:[185]                             day_rewrite
day_plan.py:emit_plan:[369]                                day_plan
day_plan_select.py:select_plan:[113]                       day_plan_select
day_reconcile.py:reconcile:[136]                           day_reconcile
entity_author.py:_entity_draft_call:[451]                  entity_generation
entity_author.py:generate_world_draft:[626]                world_generation
entity_author.py:_player_draft_call:[692]                  player_generation
entity_author.py:generate_skill_catalogue_draft:[810]      skill_catalogue
entity_author.py:generate_npc_goals:[866]                  npc_goal_generation
event_author.py:generate_agenda_draft:[80]                 agenda_generation
event_author.py:_event_draft_call:[176]                    event_generation
gathering.py:_request_partition:[105]                      mj_gathering
link_author.py:_render_pair_messages:[363]                 npc_link_pair
link_context.py:render_coherence_messages:[161]            npc_link_coherence
npc_group_author.py:_run_placement_call:[136]              npc_batch_placement
observation_engine.py:_observation_intent_messages:[102]   observation_intent
observation_runner.py:_pin_templates:[183, 188]            (version numbers)
observation_runner.py:_generate_act_line:[343, 347]        npc_dialogue, npc_initiative_act
observation_runner.py:_generate_mj_narration:[401]         observation_narration
prompt_coverage.py:missing_usages:[66]                     (coverage)
prompt_load.py:load:[65]                                   (call_json's usages)
region_author.py:generate_region_manifest:[245]           region_manifest
room_batch_author.py:generate_room_batch_manifest:[345]   room_batch_manifest
room_batch_author.py:propose_batch_coherence:[700]        room_batch_coherence
tick.py:_tick_call_scope_model:[329]                       world_tick_events
tick.py:run_world_tick:[490]                               world_tick
```
Count: 53 call lines. 34 swapped (C-07's table). 19 kept, in the 18 functions of `STAYS` (`_pin_templates` holds two). 34 + 19 = 53.

`current_prompt` in the checks (R-10):
```
attribute_interpreter.py:366,372  day_choice.py:28,239,242,252  day_prompt_delivery.py:33,418-432
event_analyzer.py:106,113  event_interpreter.py:299,307  event_lore.py:115,122  event_tick.py:109,116
lore_usage.py:406,421  prompt_model_write.py:154  prompt_version.py:6,241,258,260,299  scene_join_target.py:64
```

`source_type="..."` written under `src/` (R-20): `conversation` (analyzer_transcript ×3, play_discovery, play_stream, skill_progress), `pass_play` (day_concordance, day_events, day_mutations ×3, quest_designer), `world_tick` (tick ×2); `tick` is a ledger source (`cockpit/mutations.py:201-208`), not a proposal's.

Checks that read the frontend files and ids of briefs H, I, J (R-29):
```
creation-pending-strip  -> (none)        creation-pending-list -> (none)
creation-pj-skill       -> npc_skills.py  author-states         -> (none)
pjSkillFiche            -> npc_skills.py  EntityList.svelte     -> (none)
Creation.svelte         -> page_contract.py, creation_island.py
Sheet.svelte            -> faction_roster_panel.py, page_contract.py, npc_skills.py, npc_schedule.py,
                           event_tab.py, attributes.py, event_writes.py, skill_progression.py,
                           creation_tab_switch.py
creation.css            -> static_asset_freshness.py, graph_primitive.py, stylesheet_partition.py,
                           event_journal.py, creation_container_sizing.py
showPendingCreations    -> (none)        generatePendingCreation -> (none)
PjSkillFiche            -> npc_skills.py, graph_primitive.py, skill_progression.py
```

Module sizes (budget 1000 lines / 40 functions; frontend 1000 lines): `cockpit/routes/creator.py` 753/26, `entity_author.py` 913/33, `cockpit/crud/entities.py` 905/26, `cockpit/play.py` 961/27, `day_concordance.py` 522/16, `cockpit/crud/prompts.py` 409/14, `dashboard_metrics.py` 339/20, `prompt_store.py` 60, `prompt_call.py` 44, `region_author.py` 354/15; `Sheet.svelte` 890, `EntityList.svelte` 388.

### (d) Families
C-03 written before C-04, C-07, C-08 and re-read after C-08: the three regimes, the 14/15/18 partition (47, AMENDMENT-0124-01), the reason strings, the routes' two answers all agree. C-09, C-10, C-11 written before C-13 and re-read after it: the `to_create` shape of C-13 (`name, entity_type, concept, link_type`) is C-09's germ body shape, and C-10's draft payload adds only `origin_entity_id`, set by the create. ✓

### (e) Gates and the modules that satisfy them
- **WS1-WS3** (`world_sheet.py`, A): satisfied by `migrate_v2_30_world_tone.py`, `models/canon.py`, `routes/creator.py::get_world/update_world`; needs nothing the check forbids.
- **WP1-WP2** (`world_premise.py`, B): `prompt_registry.py`, `world_premise.py`, `prompt_store.py`, `prompt_call.py`. NA2 (passed): `prompt_call.py` imports `world_premise` -- neither `ollama_client` nor `cockpit` -- and calls no write. prompt_version rule 2 (passed): `world_premise.py` never names `PromptVersion`; `PremisedPrompt` is a plain dataclass in `prompt_store.py`.
- **WP3** (`world_premise.py`, C): the 34 swapped sites and the `STAYS` list; day_choice's stub (passed) keeps working because `day_choice.py` stays.
- **WP4** (`world_premise.py`, D): `seed_pilot.py::premised_texts/upsert_prompt_template`, the delivery script, `crud/prompts.py`. ET1/EL1 (passed): constants untouched. The five R-12 checks (passed): `write_prompt_version` unchanged.
- **EX1-EX3** (`world_extras.py`, E): `entity_extras.py`, `entities.py`, `proposal_producers.py`. PP1-PP3 (passed): `creator_draft` listed, kind `creator`, not `model`/`engine`. `single_canon_write.py` (passed): `entity_extras.py` writes `attribute_value`/`attribute_change` and `relation` only through `write_attribute_value` and `write_oriented_relations` (each already a sanctioned site), and `proposed_mutation` (not canon).
- **GA1-GA4** (`germ_attach.py`, F): `day_concordance.py`, `routes/creator.py`, `dashboard_metrics.py`, `dashboard_deferrals.py`. DB1 (passed): both anchors written into the ticket once. DB2 (passed): `_germs` reads `status`, `source_type`, `target_table`, `world_id`, `proposed_at`, `mutation_type` only.
- **DW1-DW3** (`draft_world.py` check, G): `draft_world.py`, `entity_author.py`, `routes/creator.py`.
- **CL1-CL3** (`creation_layout.py`, H): `Creation.svelte`, `EntityList.svelte`, `GermPanel.svelte`, `tabs.js`, `registry.js`, `mount.js`, `creation.css`. C2, AC3, creation_island 2/4/5/13, creation_container_sizing (passed) as listed in R-29.
- **DP1-DP2** (`draft_panel.py`, I): `DraftWorldPanel.svelte`, `pendingDrafts.svelte.js`, `generatePanel.svelte.js`, `Sheet.svelte`.
- **WG1** (`world_sheet.py`, J, extending A's check): `WorldSheet.svelte`, `tabs.js`, `registry.js`, `mount.js`, `creation.css`, `WorldCrud.svelte`, `worldCrud.svelte.js`.
- **The frontend build** (`static_asset_freshness.py`, passed): H, I and J each rebuild and commit `src/world_engine/cockpit/static/`.
- **`pipeline_state.py`** (passed through `corpus_gate.py`; AMENDMENT-0124-01): while TICKET-0124's status is in `ARROW_FLOOR_STATUSES` (`brief`, `exec`, ..., `pipeline_state.py:54`), every Machine-checkable arrow must name an existing check (`:113-120`). `world_premise.py` (B), `world_extras.py` (E), `germ_attach.py` (F), `draft_world.py` (G), `creation_layout.py` (H) and `draft_panel.py` (I) exist only once their brief lands, so `corpus_gate.py` cannot pass before brief I. No brief before J names `corpus_gate.py` in its Done means; C and D name the checks they can turn red; J runs the whole corpus.

## Amendments

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
| AMENDMENT-0124-02 | D (implemented, uncommitted) | R-12 missed `prompt_version.py` rule 7's route calls, which P1-g now refuses (K1: its fixture usage becomes `conversation_summary`) | D only |
| AMENDMENT-0124-01 | A (stopped at Mini-RECON, nothing written) | TICKET-0116 merged first: v2.29 taken (-> v2.30), a 47th usage `quest_trial` (-> `creator`), lines shifted in five anchor files; `corpus_gate.py` unsatisfiable before brief I (pipeline_state arrows) | A, B, C, D (substance); E-J (base commit and shifted anchors) |
