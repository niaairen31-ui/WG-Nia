# BRIEF 0092-C — "every category on the creator surfaces"

Lot: LOT-0092-names.md (authoritative on conflict)
Depends on: B

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a
few lines is drift, not a STOP — note it and proceed; different content is
always a STOP.

- `lore_resolve.py` holds `_CATEGORY_ENTITY_TYPE: dict[str, tuple[str, ...]]`
  with three keys and `category_of_type -> Optional[str]` (B).
- `lore_plan.py:23` `_MENTION_CATEGORIES = ("place", "person", "faction")`.
- `scripts/seed_pilot.py:1737-1742`: the two sentences quoted in R-15.
- `scripts/seed_pilot.py:2754-2762`: head `"pt-lore-question-to-plan"`,
  variables `["selectors", "question"]`.
- `scripts/apply_ticket_0087_subject_prompt.py` exists (the precedent).
- `subject_resolve.py` walks `_SUBJECT_CATEGORIES` (B), not the map.
- `writes/pipeline.py:44`, `entity_author.py:106`, `models/pipeline.py:179`
  still hold three categories (untouched here).

## Facts carried

### R-14 — the planner's category vocabulary
Opened: `src/world_engine/lore_plan.py:1-70`;
`tooling/verify/checks/lore_isolation.py:445-476` [M].
Finding: `_MENTION_CATEGORIES = ("place", "person", "faction")` (`:23`),
kept independent of `lore_resolve` on purpose (`:18-22`); `_coerce_mention`
rejects any other category (`:58-62`). R9 compares the literals of
`_MENTION_CATEGORIES` with the key set of the dict literal assigned to
`_CATEGORY_ENTITY_TYPE` in `lore_resolve.py`, whatever its values
(`_named_dict`, `:144-153`).
Consequence: C edits both literals together; R9 needs no change.
### R-15 — the planner prompt
Opened: `scripts/seed_pilot.py:1725-1765, 2750-2764`;
`scripts/apply_ticket_0087_subject_prompt.py:1-70`;
`src/world_engine/prompt_registry.py:246-259` [M].
Finding: `LORE_QUESTION_TO_PLAN_SYSTEM_PROMPT` (`:1734-1757`) says, at
`:1737-1739`, "(des lieux, des personnages ou des factions)" and, at
`:1741-1742`, "Chaque mention identifiée porte une catégorie parmi
EXACTEMENT trois : \"place\", \"person\", \"faction\". Il n'y a pas de
quatrième catégorie." The head is `"pt-lore-question-to-plan"`, variables
`["selectors", "question"]` (`:2754-2762`). Precedent for a live update:
`apply_ticket_0087_subject_prompt.py` refuses to run unless
`WORLD_ENGINE_ENV` is prod or test, imports the text from `seed_pilot`, and
appends a `prompt_version` through `write_prompt_version` only when the text
differs (idempotent).
Consequence: C edits the seed text verbatim and ships the same kind of
script. `danger_class: db_write`.
### R-16 — entity types and categories
Opened: `src/world_engine/models/canon.py:117-137, 482-560`;
`cockpit/crud/entities.py:123-200, 475-483, 636-650` [M];
`grep -rn '"artifact"' src` [M].
Finding: `entity.type` is free text with no CHECK. The creator CRUD registry
declares `character`, `location`, `faction`, `item`
(`ENTITY_TYPE_REGISTRY`, `:123-200`). A runtime entity is created with
`entity.type = <slug>` (`:648`). `event` is its own table with a `title`
(`canon.py:482-500`), not an entity, and cannot carry a fact participant.
`artifact` extends `entity` (`canon.py:527-546`) but no writer sets
`entity.type = "artifact"` (grep: `writes/worlds.py:33` deletion order,
`analyzer_transcript.py:96` only). `GET /api/entities` without `type`
returns every entity of the active world (`:475-483`).
Consequence: `object` claims `item`; `other` is every type no other category
claims. Events stay out (N6c, named deferral).
### R-18 — closed category sets this lot leaves alone
Opened: enumeration E6; `writes/pipeline.py:40-46`;
`entity_author.py:96-120`; `day_extract.py:40-47`;
`models/pipeline.py:175-200` [M].
Finding: `writes/pipeline.py:44` (day-mention writer), the
`day_mention_resolution` CHECK (`models/pipeline.py:179`), `day_extract`'s
`Mention.category` (`:43`), and the generator mention vocabulary
(`entity_author.py:99-106`) each hold the three categories.
Consequence: all stay (N6a; generator prompts are out of scope). The
tokenizer's index covers every entity type anyway (R-01).

## Contracts

### C-07 — categories (`lore_resolve.py`, `lore_plan.py`)
Produced by: B (three categories), widened by C   Consumed by: B, C, D, E
After B:
```python
_CATEGORY_ENTITY_TYPE: dict[str, tuple[str, ...]] = {
    "place": ("location",), "person": ("character",), "faction": ("faction",),
}
def category_of_type(entity_type: str) -> Optional[str]   # None when no category claims the type
```
After C:
```python
_CATEGORY_ENTITY_TYPE: dict[str, tuple[str, ...]] = {
    "place": ("location",), "person": ("character",), "faction": ("faction",),
    "object": ("item",), "other": (),
}
OTHER_CATEGORY = "other"
CATEGORIES: tuple[str, ...] = tuple(_CATEGORY_ENTITY_TYPE)
def category_of_type(entity_type: str) -> str   # the claiming category, else "other"
```
`validate_binding(entity_id, category, world_id, db)`: for `other`, the
entity's type is claimed by no other category; otherwise its type is in the
category's tuple; always active and in `world_id`; unknown category ->
`False`.
`lore_plan._MENTION_CATEGORIES = ("place", "person", "faction", "object", "other")`
after C (R9 parity with the dict keys).

## Context

B made names resolvable through the index but kept three categories. B4
makes every entity nameable on the creator's surfaces: objects and
runtime-type entities. The day chain keeps three categories (N6a).

## Scope IN

1. `lore_resolve.py`: `_CATEGORY_ENTITY_TYPE`, `OTHER_CATEGORY`,
   `CATEGORIES`, `category_of_type` exactly as C-07 "After C".
   `validate_binding` for `"other"`: the entity's type is not in the union
   of the other categories' tuples (`Entity.type.notin_(...)` inside the
   same world-scoped `.where(`).
2. `lore_plan.py:23`: `_MENTION_CATEGORIES = ("place", "person", "faction",
   "object", "other")`; update the comment at `:18-22` and the one at
   `:61`.
3. `scripts/seed_pilot.py`, `LORE_QUESTION_TO_PLAN_SYSTEM_PROMPT`, verbatim
   replacements (keep the `\` line continuations of the literal):
   - "(des lieux, des personnages ou des factions)" becomes
     "(des lieux, des personnages, des factions, des objets ou d'autres
     choses nommées du monde)".
   - "Chaque mention identifiée porte une catégorie parmi EXACTEMENT trois :
     \"place\", \"person\", \"faction\". Il n'y a pas de quatrième
     catégorie." becomes "Chaque mention identifiée porte une catégorie
     parmi EXACTEMENT cinq : \"place\" (un lieu), \"person\" (un
     personnage), \"faction\" (une faction), \"object\" (un objet) et
     \"other\" (toute autre chose nommée du monde). Il n'y a pas de sixième
     catégorie."
   No other change to the prompt; no example added.
4. New script `scripts/apply_ticket_0092_lore_plan_prompt.py`, a copy of
   `scripts/apply_ticket_0087_subject_prompt.py`'s structure (env guard,
   `seed_pilot` import, idempotent compare, `write_prompt_version`, one
   commit) with `_HEAD_ID = "pt-lore-question-to-plan"`, the two
   `LORE_QUESTION_TO_PLAN_*` constants, and the note
   `"TICKET-0092 BRIEF-0092-c -- five mention categories"`. Its docstring
   says what it touches and that it is safe to re-run.
5. `tooling/verify/checks/name_resolution.py`: add
   - G6: the "Categories after C" table of LOT Gate output (b) through
     `category_of_type`, including a runtime slug `"golem"`.
   - G7: an `item` entity "Épée de Kar" resolves with
     `resolve_named("l'épée de Kar", "object", ..., scope=CREATOR)`; an
     entity of type `"golem"` named "Gardien" resolves under `"other"` and
     not under `"person"`; `validate_binding` agrees on both and returns
     `False` for `"object"` on the golem.
   - G8: `lore_plan._MENTION_CATEGORIES` equals `lore_resolve.CATEGORIES`
     (belt and braces over R9).
6. `ARCHITECTURE_DECISIONS.md`: append
   `## EVERY CATEGORY IS NAMEABLE ON THE CREATOR SURFACES (TICKET-0092) -- OBJECT AND OTHER (BRIEF-0092-c, no schema change)`
   naming what stays three-category (R-18) and N6c; regenerate the index.

## Scope OUT

- Running the apply script on Nia's DB (Nia runs it; see Done means).
- Generator `mentions` vocabulary, `day_extract`, `writes/pipeline.py`,
  the `day_mention_resolution` CHECK (N6a, R-18).
- Events as entities (N6c).
- Frontend category labels (E).

## Invariants to defend

- "All templated model calls resolve through `prompt_registry.effective_model`":
  no new usage is added; the prompt changes only as a new version of an
  existing head.
- "History is sacred": the script appends a `prompt_version`, never edits
  one.

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold.
- `write_prompt_version` rejects the new text (a `{placeholder}` outside the
  head's variables).

ADAPT:
- `lore_isolation.py` R9 reports the dict literal missing because it now has
  tuple values: it reads keys only (R-14); if it still fails, report the
  exact message and STOP.

REPORT-ONLY:
- None.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] PASS: `name_resolution.py`, `lore_isolation.py`, `lore_resolve.py`,
      `name_index.py`, `prompt_registry.py`, `decisions_index.py`,
      `module_budget.py` (with `WORLD_ENGINE_ENV=test`).
- [ ] `WORLD_ENGINE_ENV=test python scripts/apply_ticket_0092_lore_plan_prompt.py`
      on a test DB prints `v<n> -> v<n+1>`, and a second run prints
      `unchanged`.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

`ARCHITECTURE_DECISIONS.md` + `DECISIONS_INDEX.md` (Scope IN 6). Nia runs
the apply script on prod before the live gate.
