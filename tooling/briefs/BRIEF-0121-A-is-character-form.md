<!-- slug: is-character-form -->
# BRIEF 0121-A — "The form `is_character`: a quest offered to one character only (E3a, no schema change)"

Lot: LOT-0121-journee-quest-designer.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any has moved since `main` at `301d178`.

- `src/world_engine/condition_forms.py:81` -> `REQUIREMENT_TYPES: tuple[str, ...] = (` whose last line is `    "has_debt_to", "no_debt_to", "item_held", "attribute", "event",`
- `src/world_engine/condition_forms.py:94` -> `ENTITY_TARGET_TYPES` ending `"has_debt_to", "no_debt_to", "item_held",`
- `src/world_engine/condition_forms.py:525` -> `_EVALUATORS` whose last entry is `"event": _eval_event,`
- `src/world_engine/condition_text.py:34` -> `FORM_PHRASES_FR` whose last entry is `"event"`
- `src/world_engine/day_resolve.py:262` -> `_BLOCKED_DETAIL_FR` whose last entry is `"event"`
- `src/world_engine/condition_interpreter.py:94` -> `TARGET_HINTS_FR` whose last entry is `"event"`
- `src/world_engine/writes/conditions.py:59` -> `_TARGET_ENTITY_TYPE` ending with `"item_held": ("item",),`; `:231` `def clean_leaf(` calling `_clean_subject` then `_clean_target`
- `frontend/src/creation/questRequirements.js:21` -> `REQUIREMENT_FORMS` whose last entry is `event:`
- `tooling/verify/checks/quests.py:114` -> `CONDITION_FORMS = ("item_held", "attribute", "event")`
- `tooling/verify/checks/day_plan.py:202` -> `EXPECTED_REQUIREMENT_TYPES` ending `"item_held", "attribute", "event",`
- No `tooling/verify/checks/character_form.py`.

## Facts carried

### R-01 — the condition vocabulary [M]
Opened: `src/world_engine/condition_forms.py:81-91` (`REQUIREMENT_TYPES`), `:94-96` (`ENTITY_TARGET_TYPES`), `:97` (`KEY_TARGET_TYPES`), `:525-539` (`_EVALUATORS`), `:265-279` (`_eval_has_met`), `:148-170` (`Verdict`).
Finding: thirteen forms, in this order: `knowledge, relation_gte, resource, location_reachable, has_met, faction_member, skill_rank_gte, quest_state, has_debt_to, no_debt_to, item_held, attribute, event`. `ENTITY_TARGET_TYPES` is `relation_gte, location_reachable, has_met, faction_member, has_debt_to, no_debt_to, item_held`, in that order. Every evaluator has the signature `(req, character, db, reachable_ids) -> Verdict`; `Verdict(type, met, current, required, reason, required_label=None, hidden=False, events=())`, `type` first.
Consequence: `is_character` is appended LAST to both tuples, so every order-sensitive mirror keeps its order (R-03).

### R-02 — the per-form homes outside `condition_forms.py` [M]
Opened: `condition_text.py:34-49` (`FORM_PHRASES_FR`), `day_resolve.py:262-285` (`_BLOCKED_DETAIL_FR`), `condition_interpreter.py:94-112` (`TARGET_HINTS_FR`), `writes/conditions.py:59-65` (`_TARGET_ENTITY_TYPE`), `frontend/src/creation/questRequirements.js:1-60` (header: `list` is a key of `GET /api/quest-offers/choices`; `REQUIREMENT_FORMS` at `:21-35`; `STEP_DOMAINS = ['physical', 'agility', 'perception', 'composure']`), `models/config.py:166-183` (`ConditionNode`'s seven CHECKs).
Finding: each is a dict keyed by form. No CHECK names a form: the node CHECKs are `ck_condition_node_op`, `_leaf`, `_connector`, `_subject`, `_role` (`doer`, `giver`, `contact`), `_n`, `_since` (pasted in Gate (c)).
Consequence: a new form is code only, no migration.

### R-03 — the checks that pin the vocabulary [M]
Opened: `tooling/verify/checks/quests.py:105-114` (`MODEL_FORMS`, `CREATOR_FORMS`, `DEBT_FORMS`, `CONDITION_FORMS`), `:155-165` (QA1: `REQUIREMENT_TYPES == MODEL_FORMS + CREATOR_FORMS + DEBT_FORMS + CONDITION_FORMS`; the shape groups partition it), `:797-818` (QC1: `REQUIREMENT_FORMS` keys equal `REQUIREMENT_TYPES` in order, each group in order); `day_plan.py:202-212` (`EXPECTED_REQUIREMENT_TYPES`), `:313-336` (R1: `_EVALUATORS` keys == `REQUIREMENT_TYPES`); `condition_interpreter.py:586-592` (`TARGET_HINTS_FR` keys == `REQUIREMENT_TYPES` in order), `:752-775` (one `form_lines` line per form); `conditions.py:426` (`FORM_PHRASES_FR` key set == `REQUIREMENT_TYPES`).
Finding: two checks hold a literal copy of the tuple (`quests.py` `CONDITION_FORMS`, `day_plan.py` `EXPECTED_REQUIREMENT_TYPES`); the others derive from it.
Consequence: brief A extends the two literal copies; the derived ones go green by A's own additions.

### R-04 — cleaning a leaf [M]
Opened: `writes/conditions.py:87-97` (`_clean_subject`), `:100-110` (`_clean_target`), `:231-248` (`clean_leaf`).
Finding: `_clean_subject` checks one subject (a role of `SUBJECT_ROLES`, or a character of the world unless the form is in `ANY_SUBJECT_TYPES`); `_clean_target` checks an entity target's type against `_TARGET_ENTITY_TYPE[form]` (None: any entity). No form restricts its subject today.
Consequence: `is_character` needs one new rule in `clean_leaf`: its subject is the role `doer`.

### R-23 — judging and describing a tree [M]
Opened: `conditions.py:86` (`Bindings`), `:211` (`all_of(specs)`), `:397` (`evaluate(node, bindings, db) -> Optional[VerdictNode]`), `:512` (`read_condition(db, *, role, **owner)`); `condition_text.py:194` (`describe(db, node, unsaved=None) -> list[dict]`, lines `{"depth", "text"}`); `cockpit/routes/day.py` `_finalize_plan` (`Bindings(doer=character)`).
Finding: a tree is judged with `evaluate(tree, Bindings(doer=<character>), db)` and read in French with `describe(db, tree)`; `all_of` of an empty list is None (no condition).
Consequence: A's check judges and describes an `is_character` leaf through these, never through a copy.

### R-24 — how a DB-backed check builds its fixture [M]
Opened: `tooling/verify/checks/mutation_reviews.py:77-82` (`_fresh_db`), `:269-276` (`main`); `.claude/rules/verify-checks.md`.
Finding: `_fresh_db()` points `WORLD_ENGINE_DATABASE_URL` at a temp file and defaults `WORLD_ENGINE_ENV=test` before any `world_engine` import; `main` then imports `world_engine.models` (registering every table) and runs `SQLModel.metadata.create_all(engine)`; rows go through the real writers; failures collect in `FAILURES`; 15 s per check under `corpus_gate.py`.
Consequence: every new DB-backed check of this lot follows these two functions; a table missing from `create_all` means its model is not exported from `models/__init__.py`.


## Contracts

### C-01 — the form `is_character`
Produced by: BRIEF-0121-A   Consumed by: BRIEF-0121-F
`condition_forms.REQUIREMENT_TYPES` ends `..., "event", "is_character"`; `ENTITY_TARGET_TYPES` ends `..., "item_held", "is_character"`. A leaf `RequirementSpec(type="is_character", subject_role="doer", target_entity_id=<character id>)`. Evaluator `_eval_is_character(req, character, db, reachable_ids) -> Verdict(type="is_character", met=character.id == req.target_entity_id, current=character.id, required=req.target_entity_id, reason=..., required_label=<target name>)`. `clean_leaf` refuses an `is_character` leaf whose subject is not the role `doer` (« is_character judges the one who acts »); its target is a `character` of the world. French: `FORM_PHRASES_FR["is_character"] = "{who} est {target}"`; `_BLOCKED_DETAIL_FR["is_character"] = "cette quête est réservée à {required}"`; `TARGET_HINTS_FR["is_character"] = "un personnage, par son nom (le seul à qui l'offre est proposée)"`; `REQUIREMENT_FORMS.is_character = { label: 'Est le personnage', list: 'characters', column: 'entity', threshold: false }`.
Error and empty cases: a fixed subject or another role -> `ValueError`; an unknown or non-character target -> `ValueError` (existing `_clean_target` message).


## Context

E3a: the creator ticks « Quête unique » on a proposed offer to keep it for
the character whose day gave it birth. The eligibility is a condition, and
the language has no « is this character » leaf; this brief adds that form
everywhere the vocabulary lives. The card that ticks it is BRIEF-0121-F.

## Scope IN

1. `condition_forms.py`: append `"is_character"` LAST to `REQUIREMENT_TYPES`
   and LAST to `ENTITY_TARGET_TYPES`; extend the comment above
   `REQUIREMENT_TYPES` with one line « TICKET-0121 (BRIEF-0121-A, E3a):
   `is_character` -- the one who acts is this character. ». Add
   `_eval_is_character` after `_eval_event`, with C-01's signature and
   `Verdict`: `met = character.id == req.target_entity_id`;
   `reason = f"is {name}"` when met, else
   `f"prerequisite not met — is not {name}"` (`name` from `_entity_name`);
   `current=character.id`, `required=req.target_entity_id`,
   `required_label=name`. Add `"is_character": _eval_is_character,` last in
   `_EVALUATORS`.
2. `condition_text.py`: `FORM_PHRASES_FR["is_character"] = "{who} est {target}"`, last.
3. `day_resolve.py`: `_BLOCKED_DETAIL_FR["is_character"] = "cette quête est réservée à {required}"`, last, with a comment `# TICKET-0121 (BRIEF-0121-A, E3a).`
4. `condition_interpreter.py`: `TARGET_HINTS_FR["is_character"] = "un personnage, par son nom (le seul à qui l'offre est proposée)"`, last.
5. `writes/conditions.py`: `_TARGET_ENTITY_TYPE["is_character"] = ("character",)`; in `clean_leaf`, after `_clean_subject` and before the form branches:
   `if req.type == "is_character" and req.subject_role != "doer": raise ValueError(f"{where}is_character judges the one who acts (subject: doer)")`.
6. `frontend/src/creation/questRequirements.js`: append
   `  is_character: { label: 'Est le personnage', list: 'characters', column: 'entity', threshold: false },`
   last in `REQUIREMENT_FORMS` (the exact line shape QC1 parses); add one
   sentence to the header comment: « TICKET-0121 (BRIEF-0121-A, E3a):
   `is_character` -- the offer is for this character only. ». Rebuild the
   frontend and commit the build output.
7. `tooling/verify/checks/quests.py`: `CONDITION_FORMS = ("item_held", "attribute", "event", "is_character")`, the comment above it gaining « TICKET-0121 (BRIEF-0121-A, E3a): `is_character`; `character_form.py` owns it. ».
8. `tooling/verify/checks/day_plan.py`: `EXPECTED_REQUIREMENT_TYPES` gains `"is_character",` after `"event",`, with the comment `# TICKET-0121 (BRIEF-0121-A, E3a): fourteen.`
9. New check `tooling/verify/checks/character_form.py`, its first docstring
   sentence its FILE_MAP line (`.claude/rules/verify-checks.md`):
   - **CF1** `is_character` is the last member of `REQUIREMENT_TYPES` and of `ENTITY_TARGET_TYPES`, not in `MODEL_REQUIREMENT_TYPES`, not in `ANY_SUBJECT_TYPES`, `KEY_TARGET_TYPES`, `THRESHOLD_TYPES`, `FORM_VALUES`; a key of `_EVALUATORS`, `FORM_PHRASES_FR`, `_BLOCKED_DETAIL_FR`, `TARGET_HINTS_FR`, `_TARGET_ENTITY_TYPE` (value `("character",)`).
   - **CF2** (fresh temp-file SQLite fixture, `WORLD_ENGINE_DATABASE_URL` set before any import; rows through the real writers): a world, two characters P and Q; `evaluate(all_of([is_character doer -> P]), Bindings(doer=P), db)` is met, with `Bindings(doer=Q)` not met; `describe(db, <that tree>)` holds a line containing « est » and P's name.
   - **CF3** (same fixture): `clean_leaf` refuses `is_character` with `subject_role="giver"`, with a fixed subject entity, and with a target that is a location; accepts doer -> P.
   - **CF4** `write_condition` of an eligibility `all(is_character doer -> P)` on an offer, read back by `read_condition`, gives the same leaf.
10. `tooling/standards/ARCHITECTURE_DECISIONS.md`: one entry above the footer (`---` / `*Co-built…*`):
    `## A QUEST FOR ONE CHARACTER IS A LEAF (TICKET-0121) -- THE FORM is_character (BRIEF-0121-a, no schema change)` (the header form `decisions_index.py` enforces: a lowercase brief letter) -- E3a, why a form and not a column (one language for eligibility, I1 of the series; a new primitive is code, no table rebuild, R-02), the subject restricted to `doer`. Regenerate `DECISIONS_INDEX.md` and `FILE_MAP.md`.

## Scope OUT

- The « Quête unique » box and anything in the review card: BRIEF-0121-F.
- `MODEL_REQUIREMENT_TYPES` (the planner keeps its four forms, S1 of 0111).
- Any other new form; any change to `seen_by`'s rules.
- Every later brief of this lot (B to G).

## Invariants to defend

- **INV-62** -- a player surface shows a condition only as its character may
  know it. `is_character`'s subject is always the doer, so the player reads
  his own name; no new hidden case, `seen_by` unchanged.
- **INV-20** -- nothing JSON: the leaf is a `condition_node` row.

## Decision rights

STOP:
- an anchor above does not hold;
- a check other than the two of R-03 holds a literal copy of the form tuple
  (it would mean R-03's enumeration missed one).
ADAPT:
- a third derived check (one that reads `REQUIREMENT_TYPES` rather than
  copying it) goes red only because it counts forms: fix its count, report.
- QC1's parse regex rejects the new JS line because of spacing: match the
  existing lines' spacing exactly, report.
REPORT-ONLY:
- any other per-form dict found outside R-02's list.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/run.py --ticket TICKET-0121` -> `character_form.py` PASS (CF1-CF4); `quests.py`, `day_plan.py`, `conditions.py`, `condition_interpreter.py`, `attribute_conditions.py`, `event_conditions.py` PASS.
- [ ] Named mutations, each turning its rule red then reverted: remove `"is_character"` from `ENTITY_TARGET_TYPES` (CF1); make `_eval_is_character` return `met=True` always (CF2); drop the doer rule in `clean_leaf` (CF3).
- [ ] `frontend_build_fresh.py` PASS with the rebuilt output committed.
- [ ] `/review-step` then `/close-step` on the commit.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` entry (Scope IN 10); `DECISIONS_INDEX.md`, `FILE_MAP.md` regenerated.
- No schema change, no CLAUDE.md change.
