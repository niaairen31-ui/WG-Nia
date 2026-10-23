<!-- slug: create-with-world-extras -->
# BRIEF 0124-E — "A create carries what the world adds -- states, links and ticked germs in the create's own transaction; the `creator_draft` producer (S1, I1) (no schema change)"

Lot: LOT-0124-world-premise.md (authoritative on conflict)
Depends on: nothing in this lot (its position after D is a choice for one linear branch)

## Anchors to confirm (Mini-RECON)

Halt if any has moved since `main` at `386c01a` (TICKET-0116 merged; AMENDMENT-0124-01 re-based the lot).

- `src/world_engine/cockpit/crud/entities.py:382-404` -> `class EntityWriteBody` with `entity, extension, mutation_id, facets, mentions, confirm_promotion, link_to, carrure` and no `states`, `relations`, `germs`; `:729-730` -> `@router.post("/entities", status_code=201)` over `def create_entity(body: EntityWriteBody, db: DbSession = Depends(get_session)) -> dict:` whose body opens `try:` / `entity = _create_entity_core(body, db)` / `db.commit()` / `dissolve_emptied(...)` / `except IntegrityError:`; `:778` -> `def update_entity(`.
- `src/world_engine/writes/attributes.py:349` -> `def write_attribute_value(` (keyword-only `world_id, definition_id, entity_id, value, kind, changed_by, event_id=None`); `src/world_engine/attributes.py:125` -> `def system_attribute(key)`.
- `src/world_engine/writes/relations.py:412` -> `def write_oriented_relations(` (R-24's keywords); `src/world_engine/relation_orientation.py:39` -> `def is_social(`.
- `src/world_engine/day_concordance.py:430` -> `def _germ_blocked(name: str, world_id: Optional[str], db: Session) -> Optional[str]:`.
- `src/world_engine/proposal_producers.py:16-32` -> `PRODUCERS` (8 live entries) and `PRODUCER_KINDS = ("model", "engine", "auto")`.
- No `src/world_engine/cockpit/crud/entity_extras.py`, no `tooling/verify/checks/world_extras.py`.

## Facts carried

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

### R-24 — social relations [M]
Opened: `src/world_engine/writes/relations.py:412-440` (`write_oriented_relations(db, *, world_id, entity_a_id, entity_b_id, type, value, direction, visible_to_b=False, notes=None, changed_by, mode="set", relation_id=None) -> list[Relation]`, adds rows, never commits); `cockpit/crud/relations.py:126-152` (`_create_social_relation`: 409 when the perceiver already feels something toward the target; `value` 50 by default; `direction="mutual" if reciprocal else "a_to_b"`; commits); `relation_orientation.py:39-43` (`is_social(t)`: `t not in RELATION_GRAPH_EXCLUDED_TYPES`).
Consequence: the create writes a draft's links with `write_oriented_relations` directly (no commit), social types only; a new entity has no relation yet, so the 409 case cannot arise.

## Contracts

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

## Context

The draft (brief G) will propose a value for each state, links to existing
entities, and entities that do not exist yet; the sheet (brief I) will send
the ones Nia keeps. This brief is the server side: one create, one
transaction, everything or nothing (S1), and a ticked germ that lands
approved in « Créations en attente » with its origin and link (I1).

## Scope IN

1. `cockpit/crud/entities.py`, `EntityWriteBody`: append, with the comment « TICKET-0124 (BRIEF-0124-E, S1/I1): what the world adds on create only -- C-09 of LOT-0124 », `states: list[dict] = []`, `relations: list[dict] = []`, `germs: list[dict] = []`.
2. New module `src/world_engine/cockpit/crud/entity_extras.py`, docstring first sentence « A create's world extras -- the states, links and germs a draft proposed and the creator kept, written in the create's own transaction (TICKET-0124, BRIEF-0124-E). » It declares `GERM_TYPES = ("character", "location", "faction")` and `write_create_extras(db, entity, body) -> dict` per C-09, raising `ValueError` (French message) for each refusal C-09 lists; it never commits, never rolls back. A state whose key is a system key (`system_attribute(key) is not None`) is refused « Un état système ne s'écrit pas ici : {key} ». A relation's `type` is stripped; empty or `not is_social(type)` is refused. Germ `name` and `concept` stripped; an empty name is refused. Germ payload exactly `{"entity_type", "name", "concept", "origin_entity_id": entity.id, "link_type"}` (`link_type` stripped, `None` when empty). Returns `{"states": n, "relations": n, "germs": [ids], "germs_skipped": [{"name", "reason"}]}`.
3. `create_entity`: right after `entity = _create_entity_core(body, db)`, `extras = write_create_extras(db, entity, body)`; the existing `except IntegrityError:` is preceded by `except ValueError as exc: db.rollback(); raise HTTPException(422, str(exc))`; after the response dict is built (before the `mutation_id` linkage), `result["world_extras"] = extras`. `update_entity`: when any of `body.states`, `body.relations`, `body.germs` is non-empty, `HTTPException(422, "Les ajouts du monde ne s'écrivent qu'à la création.")` before any write.
4. `proposal_producers.py`: `PRODUCERS["creator_draft"] = ("creator", "Création — germe coché dans un brouillon")`; `PRODUCER_KINDS = ("model", "engine", "auto", "creator")`; the docstring's kinds sentence gains « `creator`, the creator wrote it herself, approved at once (TICKET-0124, I1) ».
5. New check `tooling/verify/checks/world_extras.py` (`.claude/rules/verify-checks.md` idiom, fresh temp-file SQLite, route functions called directly). Docstring first sentence « G1 check for TICKET-0124 -- a create carries the states, links and germs the creator kept, all in one transaction or none. » Fixture: an active world, a character `Maître Oren`, a choice state `Rang` (holder character, `F`/`E`, default `F`), an entity state `Esprit lié` (holder character, value character), a character `Renard` (to be the value). Rules:
   - **EX1** -- `create_entity` of a character `Kaelen` with `states=[{key: Rang, value: <E id>}, {key: Esprit lié, value: Renard.id}]`, `relations=[{other_entity_id: Oren.id, type: "élève", notes: "n"}]`, `germs=[{name: "Ombre", entity_type: "character", concept: "c", link_type: "frère"}, {name: "Maître Oren", entity_type: "character", concept: "", link_type: ""}]`: two `attribute_value` rows for Kaelen and two `attribute_change` rows `kind="correction"`, `changed_by="creator_crud"`; one `relation` Kaelen -> Oren of type `élève`; one `proposed_mutation` `entity_creation`, `approved`, `source_type="creation"`, `proposed_by="creator_draft"`, `pass_play_id`, `conversation_id`, `tick_id` all NULL, payload keys exactly C-10's draft germ with `origin_entity_id` Kaelen's id; `world_extras.germs_skipped` names `Maître Oren`.
   - **EX2** -- each of: a state key `sys:vital_status`; a relation of type `connects_to`; a relation to a character of a second, inactive world; a germ of type `item` -- answers 422, and afterwards no entity of that request's name, no `attribute_value`, `relation` or `proposed_mutation` row was added.
   - **EX3** -- `update_entity` with a non-empty `states` answers 422 and writes nothing; an existing create without the three keys behaves as before (one entity, `world_extras` all zero).
   Each rule fails on zero items. One `PASS: world_extras -- ...` line.

## Scope OUT

- The draft that proposes these extras (brief G) and the sheet that sends them (brief I).
- `same_as` (brief F's `attach`, brief I's button): a create never attaches.
- A review round for the ticked germ: the creator's tick is the approval; no `mutation_review` row is written (`review_recording.py` RD5 holds `record_review` to `cockpit/routes/mutations.py`).
- Germ realization, candidates, labels (brief F).
- Relations of a non-social type (geographic links have their own route, R-24).

## Invariants to defend

- **INV-08** -- `attribute_value`/`attribute_change` and `relation` rows are written only through `write_attribute_value` and `write_oriented_relations`, already sanctioned sites; `entity_extras.py` writes no canon row directly (`single_canon_write.py` must stay green without a policy change).
- **INV-14** -- `creator_draft` is named in `PRODUCERS`; PP3 holds because its kind is `creator`, not `model`/`engine`.
- **INV-18** -- `write_create_extras` never commits; `create_entity` keeps its single commit.
- **INV-10** -- `write_oriented_relations` appends history itself; nothing else edits a relation.
- **INV-11** -- commit before touching `create_entity`.

## Decision rights

STOP: a Mini-RECON anchor that does not hold; `single_canon_write.py` attributes a write in `entity_extras.py` to a canon table; PP1-PP3 fail for a reason other than the new producer's absence before step 4.
ADAPT: `write_oriented_relations` returns a list -> count its length, report; `create_entity`'s `try` holds more statements than the anchor shows -> insert after `_create_entity_core` regardless, report.
REPORT-ONLY: a draft field you think the create should also accept.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/world_extras.py` -> `PASS`.
- [ ] Named mutations, each turning its rule red, then reverted: write the germ with `status="proposed"` -> EX1; move `write_create_extras` after `db.commit()` -> EX2; drop the 422 in `update_entity` -> EX3.
- [ ] `proposal_producers.py`, `single_canon_write.py`, `review_recording.py`, `module_budget.py`, `function_length.py` -> `PASS`.
- [ ] `/review-step` then `/close-step`.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: `## A CREATE CARRIES WHAT THE WORLD ADDS (TICKET-0124) -- states, links and ticked germs in one transaction; the creator_draft producer (BRIEF-0124-E, no schema change)` -- S1, I1, the `creator` kind and why no review round, `source_type="creation"` with no FK (the tick precedent). `FILE_MAP.md` regenerated.
