<!-- slug: draft-world-vocabulary -->
# BRIEF 0124-G — "The draft fills what the world asks -- `draft_world.py`: the names it may cite, the fields it fills, and the code that judges its states, links, same-as and entities to create (A2, G2) (no schema change)"

Lot: LOT-0124-world-premise.md (authoritative on conflict)
Depends on: BRIEF-0124-B (the creator premise with `entity_type`), BRIEF-0124-C (`_entity_draft_call` reads through `premised_prompt`), BRIEF-0124-F (`germ_candidates`, C-11)

## Anchors to confirm (Mini-RECON)

Halt if any has moved since `main` at `386c01a` (TICKET-0116 merged; AMENDMENT-0124-01 re-based the lot) plus BRIEF-0124-A to F.

- `src/world_engine/entity_author.py` -> `_TYPE_FIELDS` (R-15) with keys `character`, `location`, `faction`, each ending with `_MENTIONS_FIELD`; `_entity_draft_call(entity_type: str, brief: str, db: Session) -> dict` replacing `{type_fields}` with `_TYPE_FIELDS[entity_type]` and reading its version through `premised_prompt(db, template, entity_type=entity_type)` (BRIEF-0124-C); `generate_entity_draft(entity_type: str, brief: str, db: Session) -> dict`; `chat` imported at module top from `.ollama_client`; the file's size within 1000 lines / 40 functions (913/33 on `main`).
- `src/world_engine/cockpit/routes/creator.py` -> `_generate_draft_with_l1(entity_type: str, brief: str, db: Session) -> dict`; `generate_creation_draft` uses `_open_germ` and returns `"candidates"` (BRIEF-0124-F); `germ_candidates(db, mut)` exists.
- `src/world_engine/cockpit/crud/entity_extras.py` -> `GERM_TYPES = ("character", "location", "faction")` (BRIEF-0124-E).
- `src/world_engine/attributes.py:190`, `:200` (R-22); `src/world_engine/lore_resolve.py:73` -> `def normalize_surface(text: str) -> str:`; `src/world_engine/relation_orientation.py:39` -> `def is_social(`.
- No `src/world_engine/draft_world.py`, no `tooling/verify/checks/draft_world.py`.

## Facts carried

### R-15 — the entity generator [M]
Opened: `src/world_engine/entity_author.py:40-104` (`_TYPE_FIELDS` for `character`, `location`, `faction`), `:106-120` (`_MENTIONS_FIELD` appended to each), `:167-169` (`_world_id`: `select(World)).first()` -- the first world, not the active one), `:440-481` (`_entity_draft_call`: `current_prompt`, replaces `{entity_type}`, `{type_fields}`, `{brief}`; parses `public`, `secret`, `mentions`), `:537-568` (`_entity_character_draft`), `:570-600` (`generate_entity_draft(entity_type, brief, db)` -> `{"ok", "draft", "notes"}`, `draft["mentions"]` added last); `:837-880` (`generate_npc_goals`); file size 913 lines, 33 functions (Gate (c)).
Finding: the draft call carries no world content. `_world_id` reads the first `World` row, whichever is active -- a defect outside this lot's decisions (report-only, drafting decision 12).
Consequence: brief C swaps the two render calls; brief G appends the world fields and the citable names to `{type_fields}` and resolves the answer in a new module (`entity_author.py` has 87 lines of budget; the resolver goes to `draft_world.py`).

### R-16 — the germ routes [M]
Opened: `src/world_engine/cockpit/routes/creator.py:63-94` (`_generate_draft_with_l1(entity_type, brief, db)`), `:121` (`_ENTITY_CREATION_TYPES = frozenset({"character", "location", "faction"})`), `:123-127` (`_ENTITY_CREATION_INTROS`), `:130-152` (`_compose_entity_creation_brief(payload)`: name, concept, `anchor` written as prose), `:155-189` (`list_pending_creations`: `entity_creation`, `approved`, no `created_entity_id`; item `{mutation_id, source: "tick" if tick_id else "conversation", proposed_at, name, concept, anchor, entity_type}`), `:191-220` (`generate_creation_draft`); file size 753 lines, 26 functions.
Finding: a Journée germ is labelled « CONVERSATION »; its `anchor` (a location id, R-17) is written into the brief as prose.
Consequence: brief F labels the source from the row (C-11) and composes the place by name (C-10).

### R-22 — the world's states [M]
Opened: `src/world_engine/models/canon_attribute.py:51-123` (`AttributeDefinition`: `name`, `kind` in `choice|integer|entity`, `default_integer`, `is_hidden`, `status`; `AttributeDefinitionType`: `side` `holder|value`, `entity_type`; `AttributeChoice`: `label`, `position`, `is_default`, `status`); `attributes.py:59` (`BUILTIN_ENTITY_TYPES = ("character", "location", "faction", "item")`), `:65-67` (`BUILTIN_TYPE_LABELS_FR = {"character": "Personnage", "location": "Lieu", "faction": "Faction", "item": "Objet"}`), `:83` (`SYSTEM_ATTRIBUTES`), `:97-111` (`AttributeView`: `key, name, kind, system, hidden, status, holder_types, value_types, choices, default`; `choices` are `(key, label)` pairs), `:190-201` (`world_attributes(db, world_id)`: system views first, then active definitions by name; `applies_to(view, entity_type)`: `holder_types is None or entity_type in holder_types`); `writes/attributes.py:72-88` (`ChoiceSpec(label, id=None)`; `DefinitionSpec(name, kind, holder_types, value_types=(), choices=(), default=None, is_hidden=False)`), `:265-283` (`write_attribute_definition(db, *, world_id, spec, definition_id=None)`: `clean_definition`, then the row, its types and choices, flushed), `:349-388` (`write_attribute_value(db, *, world_id, definition_id, entity_id, value, kind, changed_by, event_id=None)`: validates holder type and value, flushes, never commits, returns None when unchanged); `cockpit/routes/attributes.py:57` (`CHANGED_BY = "creator_crud"`), `:188-200` (`set_state` refuses a system key with 422).
Finding: a system attribute (`sys:` key) is read from canon columns and never written here.
Consequence: the premise lists non-system, active definitions that apply to the type; the create writes them with `write_attribute_value(..., kind="correction", changed_by="creator_crud")`.

### R-24 — social relations [M]
Opened: `src/world_engine/writes/relations.py:412-440` (`write_oriented_relations(db, *, world_id, entity_a_id, entity_b_id, type, value, direction, visible_to_b=False, notes=None, changed_by, mode="set", relation_id=None) -> list[Relation]`, adds rows, never commits); `cockpit/crud/relations.py:126-152` (`_create_social_relation`: 409 when the perceiver already feels something toward the target; `value` 50 by default; `direction="mutual" if reciprocal else "a_to_b"`; commits); `relation_orientation.py:39-43` (`is_social(t)`: `t not in RELATION_GRAPH_EXCLUDED_TYPES`).
Consequence: the create writes a draft's links with `write_oriented_relations` directly (no commit), social types only; a new entity has no relation yet, so the 409 case cannot arise.

## Contracts

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

### C-13 — the draft's world block
Produced by: BRIEF-0124-G   Consumed by: BRIEF-0124-I
`draft_world.py`:
- `WORLD_FIELDS: dict[str, str]` for `character`, `location`, `faction` (verbatim in BRIEF-0124-G), appended to `_TYPE_FIELDS[entity_type]` inside `_entity_draft_call`.
- `known_names_block(db, world_id, entity_type, candidate_ids=()) -> str`: « Entités existantes que tu peux nommer (nom exact) : » then one `- {name} ({type label})` line per entity: `candidate_ids` first (in order), then active characters (non-player) by name, then factions by name, then locations by name, skipping repeats, at most `MAX_KNOWN_NAMES = 60` lines; `""` when none.
- `resolve_world_block(db, world_id, entity_type, public_in, draft_name, notes) -> dict` returns `{"states": [...], "links": [...], "same_as": {...} | None, "to_create": [...]}` -- the rules and the shapes are BRIEF-0124-G's case table (Gate (b), table 3).
- `generate_entity_draft(entity_type, brief, db, *, candidate_ids=())` sets `result["draft"]["world"]` (always present, possibly empty lists and `None`).

## Context

The creator premise now tells the model which states a character of this
world carries (brief B). This brief makes the draft answer them -- and name
the links, the possible same person and the entities it calls for -- and
makes code, not the model, decide what each answer means: a label matched,
a name resolved, an unknown name turned into an entity to create (G2).

## Scope IN

1. New module `src/world_engine/draft_world.py`, docstring first sentence « What a draft adds from its world -- the names it may cite, the fields it fills, and code's judgment of its answer (TICKET-0124, BRIEF-0124-G; A2, G2). » Read-only. It declares:
   - `MAX_KNOWN_NAMES = 60`, `MAX_DRAFT_GERMS = 3`, `TO_CREATE_TYPES = ("character", "location", "faction")`.
   - `WORLD_FIELDS`, verbatim:
     ```python
     _STATES = ('public.states (tableau d\'objets {"state","value"} — un par état listé dans le cadre '
                'du monde pour ce type ; state = nom exact de l\'état ; value = un des libellés '
                'proposés, un entier, ou le nom exact d\'une entité)')
     _LINKS = ('public.links (tableau d\'objets {"name","type","note"} — liens avec une entité '
               'EXISTANTE de la liste ci-dessous ; name = nom exact ; type = la nature du lien vue '
               'depuis cette entité, ex. élève, rival, protecteur)')
     _SAME_AS = ('public.same_as (string ou null — nom exact d\'un personnage de la liste qui '
                 'pourrait être cette même personne, sinon null)')
     _TO_CREATE = ('public.to_create (tableau d\'objets {"name","entity_type","concept","link"} — au '
                   'plus 3 entités qui n\'existent pas encore et que cette fiche appelle ; '
                   'entity_type parmi character|location|faction ; link = la nature du lien)')
     WORLD_FIELDS: dict[str, str] = {
         "character": " ;\n".join((_STATES, _LINKS, _SAME_AS, _TO_CREATE)) + ".",
         "location": " ;\n".join((_STATES, _LINKS, _TO_CREATE)) + ".",
         "faction": " ;\n".join((_STATES, _LINKS, _TO_CREATE)) + ".",
     }
     ```
   - `active_world_id(db) -> Optional[str]` (`World.is_active == True`).
   - `known_names_block(db, world_id, entity_type, candidate_ids=()) -> str` per C-13 (the type label of each line is `BUILTIN_TYPE_LABELS_FR[type].lower()`).
   - `resolve_world_block(db, world_id, entity_type, public_in, draft_name, notes) -> dict` per C-13, applying every row of LOT Gate (b) table 3, in this order: states, links, same_as, to_create (the derived ones first, then the model's, deduplicated by casefolded name, cut to `MAX_DRAFT_GERMS`). Shapes: a state `{"key", "name", "kind", "value", "label"}`; a link `{"entity_id", "name", "type", "note"}`; `same_as` `{"entity_id", "name"}` or `None`; an entity to create `{"name", "entity_type", "concept", "link_type"}`. Non-list or non-dict inputs are ignored without a note. Every drop appends one French note to `notes`.
2. `entity_author.py`:
   - `_entity_draft_call(entity_type, brief, db, candidate_ids=())`: `world_id = draft_world.active_world_id(db)`; the `{type_fields}` value becomes `_TYPE_FIELDS[entity_type] + "\n" + draft_world.WORLD_FIELDS[entity_type]`, followed by `"\n" + block` when `block = draft_world.known_names_block(db, world_id, entity_type, candidate_ids)` is non-empty; the success dict gains `"world_id": world_id`.
   - `generate_entity_draft(entity_type, brief, db, *, candidate_ids=())`: passes `candidate_ids`; after the type's draft, `result["draft"]["world"] = draft_world.resolve_world_block(db, call_result["world_id"], entity_type, public_in, result["draft"]["public"].get("name") or "", result["notes"])` when `world_id`, else `{"states": [], "links": [], "same_as": None, "to_create": []}`.
   - `from . import draft_world` added to the imports. No other change: the module stays under its budget (Done means).
3. `cockpit/routes/creator.py`:
   - `_generate_draft_with_l1(entity_type, brief, db, candidate_ids=())` passes `candidate_ids` to `_generate_entity_draft`.
   - `generate_creation_draft`: `candidates = germ_candidates(db, mut)`; calls `_generate_draft_with_l1(entity_type, brief, db, tuple(c["entity_id"] for c in candidates))`; then, when the payload holds `origin_entity_id` naming an active entity and a non-empty `link_type`, and the draft succeeded, prepends `{"entity_id", "name", "type": link_type, "note": ""}` to `result["draft"]["world"]["links"]` unless that entity is already linked; returns `"candidates": candidates` (BRIEF-0124-F) unchanged.
4. New check `tooling/verify/checks/draft_world.py` (fixture idiom). Docstring first sentence « G1 check for TICKET-0124 -- a draft fills the states its world asks for, and code decides what each answer names. » Rules:
   - **DW1** -- `resolve_world_block` over a fixture world (`Rang` choice F/E, `Esprit lié` entity holder character value character, `Alerte` integer holder location, a character `Renard`, a character `Maître Oren`, a faction `Secte du Phoenix`): one input per row of table 3, each giving exactly that row's output and, for a drop, one note; the derived-then-model order and the cap of three.
   - **DW2** -- `known_names_block` lists the candidate ids first, then characters (no player character), factions, locations, by name, no repeat, at most 60 lines; `""` for a world with no entity.
   - **DW3** -- `generate_entity_draft("character", "un professeur d'escrime", db, candidate_ids=(oren,))` with `entity_author.chat` replaced by a stub that records its messages and answers a JSON whose `public` holds `states` (`Rang`: `e`), `links` (`Maître Oren`, `élève`), `same_as` `Maître Oren`, `to_create` (`Ombre`): the recorded user message holds `public.states (` and `- Maître Oren (personnage)` as the first name line; the recorded system message holds `=== CADRE DU MONDE ===` and `- Rang (un parmi : F, E` (the template seeded through `upsert_prompt_template`, BRIEF-0124-D); `draft["world"]` resolves `Rang` to `E`'s id, the link and `same_as` to Oren, `Ombre` to an entity to create. `generate_creation_draft` on a `creation` germ whose payload holds `origin_entity_id` (Kaelen) and `link_type` `frère`: its draft's first link is Kaelen, `frère`.
   - The literal `TO_CREATE_TYPES` equals `entity_extras.GERM_TYPES` and `routes/creator._ENTITY_CREATION_TYPES` (as a set).
   Each rule fails on zero items. One `PASS: draft_world -- ...` line.

## Scope OUT

- The sheet's rendering of `draft["world"]` and what it sends (brief I).
- `player_generation`, `skill_catalogue`, `npc_goal_generation`: they receive the premise (brief C) but no world block.
- Creating an entity from `to_create` at draft time (G2 is a germ at save, brief E).
- Fixing `_world_id` (R-15, report-only): the new code reads the active world through `draft_world.active_world_id`.
- `same_as` acting on its own: the sheet offers it, Nia decides (brief I).

## Invariants to defend

- « Model proposes, code judges » (CLAUDE.md working rules) -- every id in `draft["world"]` comes from a `select` on the world's rows, never from the model.
- **INV-22** -- the draft names entities by exact name; code resolves them; no fact code is involved.
- **INV-08** -- nothing here writes; the create does (brief E).
- **INV-01** -- the known-names block lists names only; the creator regime may see every entity (creator surface).

## Decision rights

STOP: a Mini-RECON anchor that does not hold; `entity_author.py` would pass 1000 lines or 40 functions (move more into `draft_world.py` is not authorized without an amendment).
ADAPT: a draft type's result lacks `notes` -> create the list, report.
REPORT-ONLY: a field you think the model should also fill.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/draft_world.py` -> `PASS`.
- [ ] Named mutations, each turning its rule red, then reverted: accept a choice label the world does not hold -> DW1; list player characters in the block -> DW2; stop prepending the origin link -> DW3.
- [ ] `module_budget.py`, `function_length.py`, `world_premise.py`, `germ_attach.py` -> `PASS`.
- [ ] `/review-step` then `/close-step`.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: `## THE DRAFT FILLS WHAT THE WORLD ASKS (TICKET-0124) -- draft_world.py, its case table (BRIEF-0124-G, no schema change)` -- A2, G2, the derived entities to create, the caps. `FILE_MAP.md` regenerated.
