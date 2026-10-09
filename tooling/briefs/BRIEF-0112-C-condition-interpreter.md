<!-- slug: condition-interpreter -->
# BRIEF 0112-C — "The condition interpreter: a sentence becomes a tree the creator confirms -- the model proposes, code reads it back and validates every leaf"

Lot: LOT-0112-condition-interpreter.md (authoritative on conflict)
Depends on: BRIEF-0112-A (C-01, C-02), BRIEF-0112-B (order)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0112-B's commit).

- `src/world_engine/condition_forms.py:68` -> `REQUIREMENT_TYPES: tuple[str, ...] = (`
- `src/world_engine/writes/conditions.py:136` -> `def clean_leaf(db: Session, world_id: str, req: RequirementSpec, where: str = "") -> RequirementSpec:`
- `src/world_engine/writes/conditions.py:151` -> `def clean_condition(`
- `src/world_engine/lore_resolve.py:143` -> `def resolve_named(surface_form: str, category: str, world_id: str, db: Session, *,`
- `src/world_engine/lore_write_draft.py:79` -> `def world_fact_ids(db: Session, world_id: str) -> list[str]:`
- `src/world_engine/fact_refs.py:99` -> `def code_refs(prefix: str, pairs: Iterable[tuple[str, str]]) -> CodedRefs:`
- `src/world_engine/prompt_call.py:27` -> `def call_json(`
- `scripts/seed_pilot.py:1921` -> `LORE_WRITE_PROMPT_HEADS = (`
- `src/world_engine/prompt_registry.py:285` -> `"lore_statement_to_proposal": PromptSpec(`
- `tooling/verify/checks/name_index.py:55` -> `CREATOR_ALLOWED = {`
- `tooling/verify/checks/knowledge_identity.py:115` -> `"src/world_engine/writes/zone_promotion.py": 3,`
- `CLAUDE.md:461` -> `│   ├── day_plan.py, condition*.py  # day-plan emission + budget cut; conditions: forms, tree, text`
- No `src/world_engine/condition_interpreter.py`, no `scripts/apply_ticket_0112_condition_prompt.py`, no `condition_interpret` usage exist.

## Facts carried

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

### R-17 — prompts are seeded from one tuple and delivered by a script [M]
Opened: `scripts/seed_pilot.py:132-187` (`upsert_prompt_template`: a head
created with its v1 text, never touched again -- S2), `:1847-1942`
(`LORE_STATEMENT_TO_PROPOSAL_*`, `LORE_WRITE_PROMPT_HEADS`), `:2934-2935`
(the seed loop); `scripts/apply_ticket_0098_lore_write_prompts.py` (reads
the tuple, embeds no text); `tooling/verify/checks/prompt_registry.py`
rule 1 (seeded usages == registry keys).
Consequence: C adds `CONDITION_INTERPRET_PROMPT_HEADS`, its seed loop,
`apply_ticket_0112_condition_prompt.py` and the registry entry together.

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

### Case tables

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

## Contracts

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

## Context

The language exists (TICKET-0111), the coded list and the JSON call are shared (A), the journal waits (B). This brief writes the interpreter itself: what the model is shown, the form it answers in, how code reads that answer back without ever taking an id from it, validates every leaf with the writer's own rules, asks once more with the errors, and leaves an ambiguous name to the creator. It writes nothing; the routes (D) and the editor (E) come next.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md` and `src/world_engine/cockpit/static/` are not in the
diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - creates `src/world_engine/condition_interpreter.py` (C-03, C-04): `build_context`, `encode`, `form_lines`, `read_answer`, `waiting`, `bind`, `validate`, `prompt_values`, `interpret`, `resolve`, `Interpretation`, the constants `INTERPRET_USAGE`, `INTERPRET_UNAVAILABLE_MESSAGE`, `RESOURCE_KEY`, `ROLE_LABELS_FR`, `TARGET_HINTS_FR`, `CODE_LISTS`, `UNSUPPORTED_NOTES_FR`; its `_call` is `prompt_call.call_json` with its own `chat` (b-1, b-3);
   - `scripts/seed_pilot.py`: the `CONDITION_INTERPRET_*` prompt text and `CONDITION_INTERPRET_PROMPT_HEADS` (C-05), seeded after the Lore writing heads;
   - creates `scripts/apply_ticket_0112_condition_prompt.py` (the 0098 delivery script's shape: reads the tuple, embeds no text);
   - `prompt_registry.py`: the `condition_interpret` entry (C-05);
   - `tooling/verify/checks/name_index.py` (R5's `CREATOR_ALLOWED`) and `tooling/verify/checks/knowledge_identity.py` (K3's `_SUBJECT_CENSUS`, 3): the interpreter added, each with its reason (R-22);
   - `CLAUDE.md` line 461's comment names the interpreter (no line added);
   - adds NC1-NC4 to `condition_interpreter.py` (the check);
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - CLAUDE.md
   - scripts/apply_ticket_0112_condition_prompt.py
   - scripts/seed_pilot.py
   - src/world_engine/condition_interpreter.py
   - src/world_engine/prompt_registry.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/condition_interpreter.py
   - tooling/verify/checks/knowledge_identity.py
   - tooling/verify/checks/name_index.py

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index 32b54f2..317c9a7 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -458,7 +458,7 @@ WG-Nia/
 │   ├── observation_*.py     # observed-lane socle/engine/runner/reads/writes; per-NPC window
 │   ├── resolution.py, ledger.py  # physical-action dice resolution (2d6 bands); ledger read helpers
 │   ├── skill_lexicon.py     # action lexicon: judge/record; Play calls it, never clamps inline
-│   ├── day_plan.py, condition*.py  # day-plan emission + budget cut; conditions: forms, tree, text
+│   ├── day_plan.py, condition*.py  # day plan + cut; condition forms, tree, text, interpreter
 │   ├── day_extract.py       # day extraction: 3 passes (place/person/faction), never sees registry
 │   ├── day_concordance.py   # day mention resolution: matching rungs, germ emission; never authors
 │   ├── day_rewrite.py       # declaration rewrite: render/resolutions/load_latest, no model call
diff --git a/scripts/apply_ticket_0112_condition_prompt.py b/scripts/apply_ticket_0112_condition_prompt.py
new file mode 100644
index 0000000..78bc524
--- /dev/null
+++ b/scripts/apply_ticket_0112_condition_prompt.py
@@ -0,0 +1,59 @@
+"""One-shot, idempotent delivery of the TICKET-0112 condition interpreter's
+prompt head onto the live DB (BRIEF-0112-C).
+
+Same CREATE-HEAD pattern as apply_ticket_0094_mention_choice_seed.py: it
+embeds NO prompt text and NO head fields -- both come from
+seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS (single source) -- and relies on
+upsert_prompt_template's idempotence (S2): a first run reports the head
+`created`, a second run `existing`, and an existing head's text is never
+touched.
+
+Touches nothing else: no canon row, no other template.
+
+Safe to re-run.
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+from pathlib import Path
+
+_env = os.environ.get("WORLD_ENGINE_ENV")
+if _env not in ("prod", "test"):
+    print(
+        "apply_ticket_0112_condition_prompt.py refuses to run unless "
+        f"WORLD_ENGINE_ENV is 'prod' or 'test' (got: {_env or 'unset'})."
+    )
+    sys.exit(1)
+
+SRC = Path(__file__).resolve().parent.parent / "src"
+sys.path.insert(0, str(SRC))
+sys.path.insert(0, str(Path(__file__).resolve().parent))
+
+from sqlmodel import Session  # noqa: E402
+
+import seed_pilot  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+
+
+def main() -> None:
+    with Session(engine) as session:
+        before_created = len(seed_pilot._created)
+        before_updated = len(seed_pilot._updated)
+        before_existing = len(seed_pilot._existing)
+
+        for entry in seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS:
+            seed_pilot.upsert_prompt_template(session, **entry)
+        session.commit()
+
+        for table, id_ in seed_pilot._created[before_created:]:
+            print(f"created  {table}/{id_}")
+        for table, id_ in seed_pilot._updated[before_updated:]:
+            print(f"updated  {table}/{id_}")
+        for table, id_ in seed_pilot._existing[before_existing:]:
+            print(f"existing {table}/{id_}")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/scripts/seed_pilot.py b/scripts/seed_pilot.py
index eef826b..20457b6 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -1942,6 +1942,117 @@ LORE_WRITE_PROMPT_HEADS = (
 )
 
 
+# ----- prompt template: the condition interpreter (TICKET-0112, BRIEF-0112-C) --
+# usage = "condition_interpret". world_id = NULL. One call (and one more,
+# carrying code's errors, II1): turns the creator's sentence into a
+# condition tree for one condition of a quest offer. The model names
+# entities by name (or by an e code of the current tree) and facts, quests
+# and skills by code only; code resolves every reference, validates every
+# leaf, and the creator confirms before anything reaches the offer
+# (condition_interpreter.interpret). A cost or a reward is never a condition
+# (IA1); what the language cannot say yet is listed, never forced (IF1).
+CONDITION_INTERPRET_SYSTEM_PROMPT = """\
+Tu traduis en condition la phrase qu'écrit la créatrice d'un monde de jeu \
+de rôle pour une offre de quête. Une condition est un arbre.
+
+FEUILLES. Une feuille est une forme du langage, prise dans la liste des \
+formes, avec :
+- "form" : le nom de la forme ;
+- "subject" : sur qui elle porte -- "doer" (le personnage qui agit, par \
+défaut), "giver" (le donneur de l'offre), "contact" (le contact d'une \
+faction donneuse), ou un personnage précis {"name": "...", "kind": \
+"person"} ;
+- "target" : sa cible, comme la forme l'indique -- une entité par son nom \
+{"name": "...", "kind": "person" | "place" | "faction" | "object" | \
+"other"}, une entité de la condition actuelle par son code {"code": "e1"}, \
+un fait {"code": "f3"}, une quête {"code": "q2"}, une compétence \
+{"code": "s1"} ; null si la forme n'a pas de cible ;
+- "threshold" : un entier quand la forme a un seuil, sinon null ;
+- "value" : une des valeurs de la forme quand elle en a, sinon null.
+N'invente jamais un code : un fait, une quête ou une compétence absent des \
+listes ne peut pas être une cible.
+
+CONNECTEURS. {"op": "all", "children": [...]} (toutes), {"op": "any", \
+"children": [...]} (au moins une), {"op": "not", "children": [une seule]} \
+(pas ceci), {"op": "at_least", "n": 2, "children": [...]} (au moins n). \
+Une feuille s'écrit {"op": "leaf", "form": ..., "subject": ..., \
+"target": ..., "threshold": ..., "value": ...}.
+
+CE QUI N'EST PAS UNE CONDITION. Ce que le personnage apporte, paie ou \
+donne est un coût ("cost") ; ce qu'il reçoit est une récompense \
+("reward") : ne les traduis jamais en condition. « Le joueur apporte 15 \
+fourrures » est un coût ; « le joueur possède 15 fourrures » est une \
+condition item_held. Ce que les formes ne savent pas dire -- l'état d'une \
+chose ("state" : la porte est ouverte), ce qui s'est passé ("event" : \
+tuer, être repéré), le temps ("time" : avant le jour 5), ou autre chose \
+("other") -- va dans "unsupported", avec le passage de la phrase. Traduis \
+le reste.
+
+CONDITION ACTUELLE. Si une condition actuelle est donnée, la phrase la \
+modifie : rends la condition entière, modifiée. Sinon, rends la condition \
+que la phrase décrit.
+
+ERREURS. Si des erreurs sont données, ta réponse précédente a été refusée \
+pour ces raisons : corrige-la.
+
+Réponds UNIQUEMENT avec ce JSON :
+{"condition": {"op": "all", "children": [{"op": "leaf", "form": \
+"item_held", "subject": "doer", "target": {"name": "fourrure de loup", \
+"kind": "object"}, "threshold": 15, "value": null}]},
+ "unsupported": [{"text": "...", "kind": "event"}]}
+"condition" vaut null si rien de la phrase n'est une condition.\
+"""
+
+CONDITION_INTERPRET_USER_TEMPLATE = """\
+La condition dit : {role}.
+
+Formes :
+{forms}
+
+Entités que la phrase nomme :
+{entities}
+
+Entités de la condition actuelle (code — nom) :
+{tree_entities}
+
+Faits (code — texte) :
+{facts}
+
+Quêtes (code — titre) :
+{offers}
+
+Compétences (code — nom) :
+{skills}
+
+Condition actuelle :
+{current}
+
+Phrase de la créatrice :
+{instruction}
+
+Erreurs de ta réponse précédente :
+{errors}\
+"""
+
+
+# The interpreter's head, one tuple read by the seed and by
+# scripts/apply_ticket_0112_condition_prompt.py (single source, the
+# LORE_WRITE_PROMPT_HEADS precedent).
+CONDITION_INTERPRET_PROMPT_HEADS = (
+    dict(
+        id="pt-condition-interpret",
+        name="Interprète de conditions — phrase vers condition",
+        usage="condition_interpret",
+        world_id=None,
+        system_prompt=CONDITION_INTERPRET_SYSTEM_PROMPT,
+        user_template=CONDITION_INTERPRET_USER_TEMPLATE,
+        variables=["role", "forms", "entities", "tree_entities", "facts", "offers", "skills", "current",
+                   "instruction", "errors"],
+        destination="local",
+    ),
+)
+
+
 # ----- day chain prompt text (TICKET-0075; hoisted to module level, TICKET-0076) -----
 # ----- prompt template: day plan emission (TICKET-0075, BRIEF-0075-b) ---
 # usage = "day_plan". world_id = NULL. ONE call (F1): the model proposes
@@ -2933,6 +3044,8 @@ def seed(session: Session) -> None:
     # ----- prompt templates: lore writing (TICKET-0098, BRIEF-0098-D) --
     for entry in LORE_WRITE_PROMPT_HEADS:
         upsert_prompt_template(session, **entry)
+    for entry in CONDITION_INTERPRET_PROMPT_HEADS:
+        upsert_prompt_template(session, **entry)
 
     # ----- prompt template: world tick — off-screen NPC advancement ----------
     # (TICKET-0014/BRIEF-0014-a). usage = "world_tick". world_id = NULL.
diff --git a/src/world_engine/condition_interpreter.py b/src/world_engine/condition_interpreter.py
new file mode 100644
index 0000000..e79e535
--- /dev/null
+++ b/src/world_engine/condition_interpreter.py
@@ -0,0 +1,473 @@
+"""The condition interpreter: a sentence in French -> a condition tree the
+creator confirms (TICKET-0112, BRIEF-0112-C; decisions A1 and T1 of the
+conditions series, IA1-IK1 of TICKET-0112).
+
+The model proposes, code validates, the creator confirms (A1): nothing here
+writes. `interpret` shows the model the language (`form_lines`), the
+entities the instruction names, coded lists of the world's facts (`f`), its
+quest offers (`q`) and skills (`s`), and -- when the creator edits a
+condition (IC1) -- the current tree in the model's own form, its entities
+coded `e`. The model answers that form (C-03): entities by name (or by an
+`e` code), every other target by code, never an id (ID1a). Code reads the
+answer back (`read_answer`): codes through their list, names through
+`lore_resolve.resolve_named` under the creator regime -- an ambiguous name,
+or an unknown one with near names, waits for the creator's pick
+(`needs_choice`, 0092: the tool never picks); then every leaf through
+`writes.conditions.clean_leaf`, each error kept. Errors other than an
+unknown name send the model one more call carrying them (II1); a second
+failure is `refused`, the errors shown. What the language cannot say yet is
+listed by the model as `unsupported` and shown as a note naming where it
+will come from (IF1); a cost or a reward is never a condition (IA1).
+
+The creator-only facts are shown to the model (IE1: a surface of the
+creator; a condition on a secret is legitimate). `OllamaError` and
+`LlmParseError` propagate: the route answers `INTERPRET_UNAVAILABLE_MESSAGE`
+or a parse error and journals it (K1 of TICKET-0098).
+"""
+
+from __future__ import annotations
+
+import json
+from dataclasses import dataclass, field
+from typing import Any, Optional
+
+from sqlmodel import Session, select
+
+from . import model_exchange, prompt_call
+from .condition_forms import ENTITY_TARGET_TYPES, FORM_VALUES, REQUIREMENT_TYPES, RequirementSpec
+from .condition_text import FORM_PHRASES_FR, VALUE_LABELS_FR
+from .conditions import CONNECTORS, SUBJECT_ROLES, ConditionTree, all_of, check_shape, leaves, node_to_dict
+from .fact_refs import CodedRefs, code_facts, code_refs
+from .lore_resolve import CATEGORIES, near_candidates, resolve_named
+from .lore_write_draft import MAX_CODED_FACTS, named_entity_ids, world_fact_ids
+from .models import BASE_SKILL_DOMAINS, Entity, FactParticipant, QuestOffer, SkillDefinition
+from .name_index import CREATOR
+from .ollama_client import chat
+from .writes.conditions import clean_condition, clean_leaf
+
+INTERPRET_USAGE = "condition_interpret"
+INTERPRET_UNAVAILABLE_MESSAGE = (
+    "Le modèle local (Ollama) est indisponible : aucune condition n'a pu être "
+    "proposée et rien n'a changé dans l'offre. Ta phrase est conservée ; relance "
+    "quand Ollama est démarré."
+)
+# `resource`'s key is a label: one currency per world. Mirrors
+# `frontend/src/creation/questRequirements.js` MONEY_KEY (NC1 keeps them equal).
+RESOURCE_KEY = "monnaie"
+
+ROLE_LABELS_FR: dict[str, str] = {
+    "eligibility": "à qui l'offre est proposée",
+    "prerequisite": "ce qu'il faut pour tenter l'étape",
+    "completion": "quand l'objectif de l'étape est atteint",
+}
+
+# What each form takes as its target, in the model's form (C-03). One line
+# per form of `REQUIREMENT_TYPES` (NC1): a new form is shown to the model
+# the day it exists, or this check is red.
+TARGET_HINTS_FR: dict[str, str] = {
+    "knowledge": "un fait, par son code f",
+    "relation_gte": "un personnage, par son nom ; seuil = l'appréciation minimale",
+    "resource": "aucune cible ; seuil = la somme minimale",
+    "location_reachable": "un lieu, par son nom",
+    "has_met": "un personnage ou une entité, par son nom",
+    "faction_member": "une faction, par son nom",
+    "skill_rank_gte": "une compétence, par son code s ; seuil = le rang de 1 à 5",
+    "quest_state": "une quête, par son code q ; valeur = son état",
+    "has_debt_to": "un personnage ou une faction, par son nom",
+    "no_debt_to": "un personnage ou une faction, par son nom",
+    "item_held": "un objet, par son nom ; seuil = la quantité minimale",
+    "vital_status": "aucune cible ; valeur = l'état vital",
+}
+# The forms whose target is a code, and the list each code comes from.
+CODE_LISTS: dict[str, str] = {"knowledge": "f", "quest_state": "q", "skill_rank_gte": "s"}
+
+# IF1: what the language cannot say yet, by the kind the model gives it, and
+# where it will come from. IA1: a cost or a reward is a term of the offer.
+UNSUPPORTED_NOTES_FR: dict[str, str] = {
+    "state": "« {text} » : l'état du monde (ouvert, détruit, occupé…) n'est pas encore une "
+             "condition ; il arrive avec les attributs (TICKET-0113).",
+    "event": "« {text} » : ce qui s'est passé (tué, repéré, capturé…) n'est pas encore une "
+             "condition ; il arrive avec le journal d'événements (TICKET-0114).",
+    "time": "« {text} » : le temps (avant le jour N, pendant N tours) n'est pas encore une "
+            "condition ; aucun ticket ne l'a encore.",
+    "cost": "« {text} » : c'est un coût, pas une condition : ajoute-le dans « Coûts » de l'offre.",
+    "reward": "« {text} » : c'est une récompense, pas une condition : ajoute-la dans « Récompenses » "
+              "de l'offre.",
+    "other": "« {text} » : cette forme de condition n'existe pas encore.",
+}
+NOTHING_PROPOSED_FR = "Le modèle n'a proposé aucune condition."
+UNKNOWN_NAME_FR = "« {name} » : aucun nom de ce monde ne correspond."
+
+
+# --- context -------------------------------------------------------------------
+
+@dataclass(frozen=True)
+class InterpreterContext:
+    """What the model may see; the coded lists also resolve its answer."""
+
+    entity_lines: tuple[str, ...]
+    lists: dict[str, CodedRefs]  # "e", "f", "q", "s"
+    current: Optional[dict]
+
+
+def _current_ids(tree: Optional[ConditionTree]) -> dict[str, list[str]]:
+    found: dict[str, list[str]] = {"e": [], "f": [], "q": [], "s": []}
+    for spec in leaves(tree):
+        for entity_id in (spec.subject_entity_id, spec.target_entity_id):
+            if entity_id and entity_id not in found["e"]:
+                found["e"].append(entity_id)
+        if spec.type in CODE_LISTS and spec.target_key:
+            found[CODE_LISTS[spec.type]].append(spec.target_key)
+    return found
+
+
+def _entity_label(db: Session, entity_id: str) -> str:
+    entity = db.get(Entity, entity_id)
+    return f"{entity.name} ({entity.type})" if entity is not None else entity_id
+
+
+def _skill_pairs(db: Session, world_id: str) -> list[tuple[str, str]]:
+    definitions = db.exec(select(SkillDefinition).where(SkillDefinition.world_id == world_id)).all()
+    return [(d, d) for d in BASE_SKILL_DOMAINS] + sorted(
+        ((d.id, d.name) for d in definitions), key=lambda pair: pair[1].lower())
+
+
+def build_context(db: Session, world_id: str, instruction: str, current: Optional[ConditionTree]) -> InterpreterContext:
+    """IE1: the facts of the current tree, then of the entities the
+    instruction names, then the world-level facts, creator-only facts
+    included, capped at `MAX_CODED_FACTS`; every offer and skill of the
+    world; the current tree's entities coded `e`."""
+    ids = _current_ids(current)
+    named = named_entity_ids(db, world_id, instruction)
+    fact_ids = list(ids["f"])
+    for entity_id in named:
+        fact_ids += db.exec(select(FactParticipant.fact_id).where(
+            FactParticipant.entity_id == entity_id).order_by(FactParticipant.fact_id)).all()
+    fact_ids += world_fact_ids(db, world_id)
+    offers = db.exec(select(QuestOffer).where(QuestOffer.world_id == world_id)).all()
+    lists = {
+        "e": code_refs("e", ((eid, _entity_label(db, eid)) for eid in ids["e"])),
+        "f": code_facts(db, list(dict.fromkeys(fact_ids))[:MAX_CODED_FACTS]),
+        "q": code_refs("q", sorted(((o.id, o.title) for o in offers), key=lambda pair: pair[1].lower())),
+        "s": code_refs("s", _skill_pairs(db, world_id)),
+    }
+    lines = tuple(f"- {_entity_label(db, eid)}" for eid in named)
+    return InterpreterContext(entity_lines=lines, lists=lists,
+                              current=encode(current, lists) if current is not None else None)
+
+
+# --- the model's form (C-03) ---------------------------------------------------
+
+def _encode_ref(entity_id: Optional[str], lists: dict[str, CodedRefs]) -> Optional[dict]:
+    return {"code": lists["e"].code_of(entity_id)} if entity_id else None
+
+
+def encode(tree: ConditionTree, lists: dict[str, CodedRefs]) -> dict:
+    """A clean tree in the model's form: entities by `e` code, facts,
+    offers and skills by their code."""
+    if tree.op != "leaf":
+        out: dict[str, Any] = {"op": tree.op, "children": [encode(c, lists) for c in tree.children]}
+        if tree.op == "at_least":
+            out["n"] = tree.n
+        return out
+    spec = tree.leaf
+    target = _encode_ref(spec.target_entity_id, lists)
+    if spec.type in CODE_LISTS:
+        target = {"code": lists[CODE_LISTS[spec.type]].code_of(spec.target_key)}
+    return {"op": "leaf", "form": spec.type,
+            "subject": spec.subject_role or _encode_ref(spec.subject_entity_id, lists),
+            "target": target, "threshold": spec.threshold, "value": spec.value}
+
+
+def form_lines() -> str:
+    """The language for the prompt: one line per form, its French phrase,
+    its target and, for a form that compares to a value, its values."""
+    lines = []
+    for form in REQUIREMENT_TYPES:
+        line = f"- {form} : {FORM_PHRASES_FR[form]} — cible : {TARGET_HINTS_FR[form]}"
+        if form in FORM_VALUES:
+            line += " ; valeurs : " + ", ".join(
+                f"{value} ({VALUE_LABELS_FR[form][value]})" for value in FORM_VALUES[form])
+        lines.append(line)
+    return "\n".join(lines)
+
+
+# --- reading the answer --------------------------------------------------------
+
+@dataclass
+class Reading:
+    """The model's tree as code read it: `pending` is the dict form of
+    `conditions.node_to_dict` whose leaves may also carry `subject_mention`
+    / `target_mention` (a name still to pick); `mentions` the names it
+    used; `errors` what refuses it, `name_errors` the unknown names."""
+
+    pending: Optional[dict] = None
+    mentions: list[dict] = field(default_factory=list)
+    errors: list[str] = field(default_factory=list)
+    name_errors: list[str] = field(default_factory=list)
+
+
+def _mention(db: Session, world_id: str, raw: dict, reading: Reading) -> Optional[str]:
+    """The ref of the mention `raw` names (`{"name", "kind"}`), recorded once."""
+    name = str(raw.get("name") or "").strip()
+    kind = raw.get("kind") if raw.get("kind") in CATEGORIES else "other"
+    for mention in reading.mentions:
+        if mention["name"].lower() == name.lower() and mention["kind"] == kind:
+            return mention["ref"]
+    mention: dict[str, Any] = {"ref": f"m{len(reading.mentions) + 1}", "name": name, "kind": kind,
+                               "entity_id": None, "choices": []}
+    found = resolve_named(name, kind, world_id, db, scope=CREATOR)
+    if found.verdict == "unmatched" and kind != "other":
+        found = resolve_named(name, "other", world_id, db, scope=CREATOR)
+    if found.verdict == "matched":
+        mention.update(status="matched", entity_id=found.entity_id)
+    elif found.verdict == "ambiguous":
+        mention.update(status="ambiguous", choices=[
+            {"entity_id": e.id, "name": e.name, "type": e.type}
+            for e in (db.get(Entity, cid) for cid in found.candidate_ids)])
+    else:
+        mention.update(status="unmatched", choices=[
+            {"entity_id": c.entity_id, "name": c.name, "type": c.entity_type, "score": c.score}
+            for c in near_candidates(name, world_id, db, scope=CREATOR)])
+        if not mention["choices"]:
+            reading.name_errors.append(UNKNOWN_NAME_FR.format(name=name))
+    reading.mentions.append(mention)
+    return mention["ref"]
+
+
+def _entity(db: Session, world_id: str, raw: Any, ctx: InterpreterContext, reading: Reading,
+            where: str) -> tuple[Optional[str], Optional[str]]:
+    """An entity reference -> (entity id, mention ref); an error noted."""
+    if isinstance(raw, dict) and raw.get("code") is not None:
+        entity_id = ctx.lists["e"].resolve(raw["code"])
+        if entity_id is None:
+            reading.errors.append(f"{where}code inconnu {raw['code']!r} (une entité se nomme par son nom)")
+        return entity_id, None
+    if isinstance(raw, dict) and str(raw.get("name") or "").strip():
+        ref = _mention(db, world_id, raw, reading)
+        mention = next(m for m in reading.mentions if m["ref"] == ref)
+        return (mention["entity_id"], None) if mention["status"] == "matched" else (None, ref)
+    reading.errors.append(f"{where}une entité attendue, reçu {raw!r}")
+    return None, None
+
+
+def _leaf(db: Session, world_id: str, raw: dict, ctx: InterpreterContext, reading: Reading, where: str) -> dict:
+    form = raw.get("form")
+    out: dict[str, Any] = {"op": "leaf", "type": form, "subject_role": None, "subject_entity_id": None,
+                           "target_entity_id": None, "target_key": None, "threshold": raw.get("threshold"),
+                           "value": raw.get("value")}
+    if form not in REQUIREMENT_TYPES:
+        reading.errors.append(f"{where}forme inconnue {form!r}")
+        return out
+    subject = raw.get("subject") or "doer"
+    if isinstance(subject, str) and subject in SUBJECT_ROLES:
+        out["subject_role"] = subject
+    else:
+        if isinstance(subject, str):  # a bare name: a person
+            subject = {"name": subject, "kind": "person"}
+        out["subject_entity_id"], out["subject_mention"] = _entity(db, world_id, subject, ctx, reading, where)
+    target = raw.get("target")
+    if isinstance(target, str) and form in ENTITY_TARGET_TYPES:  # a bare name
+        target = {"name": target, "kind": "other"}
+    if form in ENTITY_TARGET_TYPES:
+        out["target_entity_id"], out["target_mention"] = _entity(db, world_id, target, ctx, reading, where)
+    elif form in CODE_LISTS:
+        code = target.get("code") if isinstance(target, dict) else target
+        out["target_key"] = ctx.lists[CODE_LISTS[form]].resolve(code)
+        if out["target_key"] is None:
+            reading.errors.append(f"{where}code inconnu {code!r} (attendu : un code {CODE_LISTS[form]})")
+    elif form == "resource":
+        out["target_key"] = RESOURCE_KEY
+    return {k: v for k, v in out.items() if v is not None or not k.endswith("_mention")}
+
+
+def _read(db: Session, world_id: str, raw: Any, ctx: InterpreterContext, reading: Reading, path: str) -> dict:
+    where = f"condition {path} : "
+    if not isinstance(raw, dict):
+        reading.errors.append(f"{where}un objet attendu, reçu {raw!r}")
+        return {"op": "all", "children": []}
+    if raw.get("op") == "leaf":
+        return _leaf(db, world_id, raw, ctx, reading, where)
+    if raw.get("op") not in CONNECTORS:
+        reading.errors.append(f"{where}connecteur inconnu {raw.get('op')!r}")
+        return {"op": "all", "children": []}
+    children = raw.get("children") if isinstance(raw.get("children"), list) else []
+    out: dict[str, Any] = {"op": raw["op"], "children": [
+        _read(db, world_id, child, ctx, reading, f"{path}.{i}") for i, child in enumerate(children, start=1)]}
+    if raw["op"] == "at_least":
+        out["n"] = raw.get("n")
+    return out
+
+
+def read_answer(db: Session, world_id: str, raw: Any, ctx: InterpreterContext) -> Reading:
+    """The model's `condition` read back: codes and names resolved, nothing
+    validated yet. None reads as no tree."""
+    reading = Reading()
+    if raw is not None:
+        reading.pending = _read(db, world_id, raw, ctx, reading, "1")
+    return reading
+
+
+# --- validation ----------------------------------------------------------------
+
+def waiting(pending: Optional[dict]) -> bool:
+    """A leaf of `pending` still waits for a name to be picked."""
+    if pending is None:
+        return False
+    if pending.get("op") == "leaf":
+        return "subject_mention" in pending or "target_mention" in pending
+    return any(waiting(child) for child in pending.get("children", []))
+
+
+def bind(pending: dict, mentions: list[dict], bindings: dict[str, str]) -> dict:
+    """`pending` with every waiting name replaced by the creator's pick.
+    `ValueError` when a waiting mention has no pick or a pick outside its
+    choices."""
+    by_ref = {m["ref"]: m for m in mentions}
+    if pending.get("op") != "leaf":
+        return {**pending, "children": [bind(c, mentions, bindings) for c in pending.get("children", [])]}
+    out = dict(pending)
+    for side in ("subject", "target"):
+        ref = out.pop(f"{side}_mention", None)
+        if ref is None:
+            continue
+        pick = bindings.get(ref)
+        if pick not in {c["entity_id"] for c in by_ref.get(ref, {}).get("choices", [])}:
+            raise ValueError(f"« {by_ref.get(ref, {}).get('name', ref)} » : choisis un des noms proposés")
+        out[f"{side}_entity_id"] = pick
+    return out
+
+
+def _tree(raw: dict) -> ConditionTree:
+    if raw.get("op") == "leaf":
+        return ConditionTree(op="leaf", leaf=RequirementSpec(
+            type=raw["type"], subject_role=raw.get("subject_role"), subject_entity_id=raw.get("subject_entity_id"),
+            target_entity_id=raw.get("target_entity_id"), target_key=raw.get("target_key"),
+            threshold=raw.get("threshold"), value=raw.get("value")))
+    return ConditionTree(op=raw["op"], n=raw.get("n"), children=tuple(_tree(c) for c in raw.get("children", [])))
+
+
+def validate(db: Session, world_id: str, pending: dict) -> tuple[Optional[ConditionTree], list[str]]:
+    """A bound tree checked whole: its shape, then every leaf on its own
+    (`clean_leaf`), so every error is reported at once. (tree, []) or
+    (None, errors)."""
+    try:
+        tree = _tree(pending)
+        check_shape(tree)
+    except (ValueError, KeyError, TypeError) as exc:
+        return None, [f"forme de l'arbre : {exc}"]
+    errors = []
+    for index, spec in enumerate(leaves(tree), start=1):
+        try:
+            clean_leaf(db, world_id, spec, where=f"condition {index} ({spec.type}) : ")
+        except ValueError as exc:
+            errors.append(str(exc))
+    if errors:
+        return None, errors
+    clean = clean_condition(db, world_id, tree)
+    # A lone leaf is proposed as the editor's list sends it back: `all` of it
+    # (`conditions.flat_leaves`, T1), so an unchanged insert saves as proposed.
+    return (all_of(leaves(clean)) if clean.op == "leaf" else clean), []
+
+
+# --- interpretation ------------------------------------------------------------
+
+@dataclass
+class Interpretation:
+    """What `interpret` and `resolve` give the route (C-04)."""
+
+    outcome: str  # proposed | needs_choice | refused
+    tree: Optional[ConditionTree]
+    pending: Optional[dict]
+    mentions: list[dict]
+    notes: list[str]
+    errors: list[str]
+    retried: bool = False
+
+    def payload(self, current: Optional[ConditionTree], bindings: Optional[dict] = None) -> dict:
+        """The journal's payload (`writes.condition_drafts.PAYLOAD_KEYS`)."""
+        return {"current": node_to_dict(current), "pending": self.pending, "mentions": self.mentions,
+                "bindings": bindings or {}, "proposed": node_to_dict(self.tree),
+                "notes": self.notes, "errors": self.errors}
+
+
+Exchanges = Optional[list[model_exchange.ModelExchange]]
+
+
+def _call(db: Session, values: dict[str, str], exchanges: Exchanges) -> dict:
+    """One model call, through `prompt_call.call_json` with this module's
+    `chat`."""
+    return prompt_call.call_json(db, INTERPRET_USAGE, values, exchanges, chat)
+
+
+def _lines(lines) -> str:
+    return "\n".join(lines) or "(aucun)"
+
+
+def prompt_values(ctx: InterpreterContext, role: str, instruction: str, errors: list[str]) -> dict[str, str]:
+    """The prompt's variables (C-05)."""
+    return {
+        "role": ROLE_LABELS_FR[role], "forms": form_lines(), "entities": _lines(ctx.entity_lines),
+        "tree_entities": _lines(ctx.lists["e"].lines), "facts": _lines(ctx.lists["f"].lines),
+        "offers": _lines(ctx.lists["q"].lines), "skills": _lines(ctx.lists["s"].lines),
+        "current": json.dumps(ctx.current, ensure_ascii=False) if ctx.current is not None else "(aucune)",
+        "instruction": instruction.strip(), "errors": _lines(f"- {e}" for e in errors),
+    }
+
+
+def _notes(raw: Any) -> list[str]:
+    notes = []
+    for item in raw if isinstance(raw, list) else []:
+        if isinstance(item, dict) and str(item.get("text") or "").strip():
+            kind = item.get("kind") if item.get("kind") in UNSUPPORTED_NOTES_FR else "other"
+            notes.append(UNSUPPORTED_NOTES_FR[kind].format(text=str(item["text"]).strip()))
+    return notes
+
+
+def _settle(db: Session, world_id: str, reading: Reading, notes: list[str], retried: bool) -> Interpretation:
+    def done(outcome, tree=None, errors=()):
+        return Interpretation(outcome, tree, reading.pending, reading.mentions, notes, list(errors), retried)
+
+    if reading.errors or reading.name_errors:
+        return done("refused", errors=reading.errors + reading.name_errors)
+    if reading.pending is None:
+        return done("refused", errors=[] if notes else [NOTHING_PROPOSED_FR])
+    if waiting(reading.pending):
+        return done("needs_choice")
+    tree, errors = validate(db, world_id, reading.pending)
+    return done("proposed", tree) if tree is not None else done("refused", errors=errors)
+
+
+def interpret(
+    db: Session, world_id: str, role: str, instruction: str, current: Optional[ConditionTree],
+    exchanges: Exchanges = None,
+) -> Interpretation:
+    """II1: one call, and one more carrying the errors when code refused the
+    first answer for anything but an unknown name. `OllamaError` and
+    `LlmParseError` propagate."""
+    ctx = build_context(db, world_id, instruction, current)
+    parsed = _call(db, prompt_values(ctx, role, instruction, []), exchanges)
+    result = _settle(db, world_id, read_answer(db, world_id, parsed.get("condition"), ctx),
+                     _notes(parsed.get("unsupported")), retried=False)
+    if result.outcome == "refused" and _retryable(result):
+        parsed = _call(db, prompt_values(ctx, role, instruction, result.errors), exchanges)
+        result = _settle(db, world_id, read_answer(db, world_id, parsed.get("condition"), ctx),
+                         _notes(parsed.get("unsupported")), retried=True)
+    return result
+
+
+def _retryable(result: Interpretation) -> bool:
+    """II1: an error the model may fix -- not an unknown name, not an
+    answer with no condition at all."""
+    names = {UNKNOWN_NAME_FR.format(name=m["name"]) for m in result.mentions if m["status"] == "unmatched"}
+    return any(e not in names and e != NOTHING_PROPOSED_FR for e in result.errors)
+
+
+def resolve(db: Session, world_id: str, pending: dict, mentions: list[dict], notes: list[str],
+            bindings: dict[str, str]) -> Interpretation:
+    """The creator's picks applied to a `needs_choice` proposal; no model
+    call. `ValueError` when a pick is missing or outside its choices."""
+    bound = bind(pending, mentions, bindings)
+    tree, errors = validate(db, world_id, bound)
+    outcome = "proposed" if tree is not None else "refused"
+    return Interpretation(outcome, tree, bound, mentions, list(notes), errors)
diff --git a/src/world_engine/prompt_registry.py b/src/world_engine/prompt_registry.py
index b2a1ae8..e28186d 100644
--- a/src/world_engine/prompt_registry.py
+++ b/src/world_engine/prompt_registry.py
@@ -289,6 +289,15 @@ PROMPT_REGISTRY: dict[str, PromptSpec] = {
         call_sites=("src/world_engine/lore_write_draft.py:_call",),
         default_model=_author_model,
     ),
+    # TICKET-0112 (BRIEF-0112-C): the condition interpreter, a creator tool
+    # (IJ1: the authoring model by default, overridable per template).
+    "condition_interpret": PromptSpec(
+        surface="authoring",
+        world_scoped=False,
+        dry_run_capable=True,
+        call_sites=("src/world_engine/condition_interpreter.py:_call",),
+        default_model=_author_model,
+    ),
     "world_tick": PromptSpec(
         surface="play",
         world_scoped=False,
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index bf2b723..0d9ff2b 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18567,6 +18567,51 @@ cascade. `writes/condition_drafts.py` is its one writer.
 CHECKs, and an acceptance counted inside JSON. IH3 (an export only): D1
 would not be measurable.
 
+## THE CONDITION INTERPRETER: A SENTENCE BECOMES A TREE THE CREATOR CONFIRMS (TICKET-0112) -- THE MODEL PROPOSES, CODE READS IT BACK AND VALIDATES EVERY LEAF (BRIEF-0112-c, no schema change)
+
+**IA1.** The interpreter writes conditions only -- an offer's eligibility,
+a step's prerequisite or completion. A cost (« apporte 15 fourrures ») or a
+reward is never translated into a condition: the model lists it as
+unsupported and the creator reads « ajoute-le dans Coûts ». Rejected: IA2
+(terms too: a second judge, `TermSpec`; reactivation: the journal shows
+the creator typing costs into the interpreter) and IA3 (a whole offer from
+one sentence, after IA2).
+
+**IC1.** Editing a condition, the model receives the current tree in its
+own form -- entities by an `e` code, facts, offers and skills by code --
+with the instruction, and answers the whole tree. Rejected: IC2 (always
+rewrite from a full sentence).
+
+**ID1a, IE1.** The model sees the language (one line per form: its French
+phrase, its target, its values), the entities the instruction names, and
+coded lists: the current tree's facts, then the named entities' facts
+(creator-only facts included: a condition on a secret is legitimate),
+then the world-level facts, capped like the Lore writing panel; every
+quest offer (`q`); the base domains and the world's skills (`s`). Code
+reads the answer back: codes through their list, names through
+`lore_resolve.resolve_named` under the creator regime. An ambiguous name,
+or an unknown one with near names, waits for the creator's pick
+(`needs_choice`); an unknown name with none is an error. Rejected: IE2
+(creator-only facts hidden: no condition on a secret).
+
+**II1.** Every leaf is validated on its own by `writes.conditions.clean_leaf`,
+every error kept. When code refuses the model's answer for anything but an
+unknown name, the model is asked once more with the errors; a second
+refusal is `refused`, the errors shown, nothing insertable. Rejected: II2
+(no second call). Distinct from Y8a (TICKET-0094): nothing is written here,
+and the creator remains the judge.
+
+**IF1.** What the forms cannot say yet -- a state, an event, time, other --
+is listed by the model and shown as a note naming where it will come from
+(TICKET-0113, TICKET-0114); the rest is proposed. Rejected: IF2 (all or
+nothing).
+
+**IJ1.** One prompt, `condition_interpret`, an authoring usage: the
+authoring model by default, the creator's per-template override otherwise.
+`OllamaError` and a reply that does not parse propagate to the route. The
+interpreter writes nothing: `condition_interpreter.py` calls no model
+directly (its `_call` is `prompt_call.call_json`) and no write.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/condition_interpreter.py b/tooling/verify/checks/condition_interpreter.py
index c0845b1..e81864a 100644
--- a/tooling/verify/checks/condition_interpreter.py
+++ b/tooling/verify/checks/condition_interpreter.py
@@ -48,6 +48,48 @@ NB3 -- migration `scripts/migrate_v2_21_condition_draft.py` on a database
    and sets `schema_meta` to the code's version; a second run says nothing
    to do; a row written through the writer reads back its JSON.
 
+NC1 -- the interpreter's shape (BRIEF-0112-C; static and import).
+   `TARGET_HINTS_FR` has one hint per form of `REQUIREMENT_TYPES`, in
+   order; every form of `CODE_LISTS` is outside `ENTITY_TARGET_TYPES`;
+   `UNSUPPORTED_NOTES_FR` covers exactly state, event, time, cost, reward
+   and other -- cost names « Coûts », reward « Récompenses », state
+   TICKET-0113, event TICKET-0114; `ROLE_LABELS_FR` covers
+   `CONDITION_ROLES`; `RESOURCE_KEY` equals the editor's `MONEY_KEY`.
+   `condition_interpreter.py` calls `chat` nowhere: `_call` is one return
+   of `prompt_call.call_json(..., chat)`; it calls none of `add`, `commit`,
+   `delete`, `execute`, `flush`, and imports neither `cockpit` nor
+   `writes.condition_drafts` nor `write_condition`. `PROMPT_REGISTRY`'s
+   `condition_interpret` is an authoring usage called at
+   `condition_interpreter.py:_call`; `CONDITION_INTERPRET_PROMPT_HEADS` is
+   one head of that usage whose variables are exactly its template's and
+   `prompt_values`' keys; the delivery script reads that tuple and embeds
+   no text.
+NC2 -- context and form (fixture). `build_context` codes the current
+   tree's fact first, then a fact of an entity the instruction names (a
+   creator-only one included, IE1), then a world-level fact; every offer
+   (`q`); the four base domains then the world's skill (`s`); the current
+   tree's entities (`e`); and lists the named entity. A clean tree using
+   every connector, a fixed subject, a code target of each list, an entity
+   target, `resource` and `vital_status` encodes to the model's form and
+   reads back, bound and validated, to the same tree. `form_lines` has one
+   line per form carrying its phrase.
+NC3 -- interpretation (fixture, `condition_interpreter.chat` stubbed).
+   a. a nested answer -> `proposed`, the expected tree, one exchange; a
+      lone leaf -> `all` of it (what the list editor sends back);
+   b. an unknown code, then a good answer -> `proposed`, `retried`, two
+      exchanges, the second message carrying the error;
+   c. two bad answers -> `refused` with errors, `retried`;
+   d. an unknown name with no near name -> `refused`, one exchange;
+   e. a name two characters carry -> `needs_choice` with both; `resolve`
+      with one -> `proposed` on it; with a third id -> `ValueError`;
+   f. a cost only -> `refused`, the « Coûts » note, no error; a condition
+      and an event -> `proposed` with the TICKET-0114 note;
+   g. `OllamaError` and an unparsable reply propagate;
+   h. a current tree reaches the message in the model's form.
+NC4 -- the interpreter writes nothing (fixture). Across NC3, the counts of
+   `condition`, `condition_node`, `fact`, `entity`, `knowledge` and
+   `condition_draft` do not move.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
@@ -494,6 +536,331 @@ def check_nb3() -> None:
     eng.dispose()
 
 
+# --- NC1 -----------------------------------------------------------------------
+
+def _nc1_tables() -> None:
+    from world_engine import condition_interpreter as ci
+    from world_engine.condition_forms import ENTITY_TARGET_TYPES, REQUIREMENT_TYPES
+    from world_engine.models import CONDITION_ROLES
+
+    if tuple(ci.TARGET_HINTS_FR) != REQUIREMENT_TYPES:
+        fail(f"NC1: TARGET_HINTS_FR covers {tuple(ci.TARGET_HINTS_FR)}")
+    if not ci.CODE_LISTS or set(ci.CODE_LISTS) & set(ENTITY_TARGET_TYPES) \
+            or not set(ci.CODE_LISTS) <= set(REQUIREMENT_TYPES):
+        fail(f"NC1: CODE_LISTS is {ci.CODE_LISTS}")
+    notes = ci.UNSUPPORTED_NOTES_FR
+    if set(notes) != {"state", "event", "time", "cost", "reward", "other"} or "« Coûts »" not in notes["cost"] \
+            or "« Récompenses »" not in notes["reward"] or "TICKET-0113" not in notes["state"] \
+            or "TICKET-0114" not in notes["event"]:
+        fail(f"NC1: UNSUPPORTED_NOTES_FR reads {notes}")
+    if set(ci.ROLE_LABELS_FR) != set(CONDITION_ROLES):
+        fail("NC1: ROLE_LABELS_FR does not cover CONDITION_ROLES")
+    js = (ROOT / "frontend" / "src" / "creation" / "questRequirements.js").read_text(encoding="utf-8")
+    found = re.findall(r"export const MONEY_KEY = '([^']+)';", js)
+    if found != [ci.RESOURCE_KEY]:
+        fail(f"NC1: RESOURCE_KEY {ci.RESOURCE_KEY!r} vs the editor's MONEY_KEY {found}")
+
+
+def _nc1_module() -> None:
+    tree = _parse(SRC / "condition_interpreter.py")
+    chats = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Call) and _callee(n) == "chat"]
+    if chats:
+        fail(f"NC1: condition_interpreter.py calls chat( at {chats}")
+    call = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_call"), None)
+    body = [n for n in call.body if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))] if call else []
+    if not (len(body) == 1 and isinstance(body[0], ast.Return) and isinstance(body[0].value, ast.Call)
+            and _callee(body[0].value) == "call_json" and isinstance(body[0].value.args[-1], ast.Name)
+            and body[0].value.args[-1].id == "chat"):
+        fail("NC1: condition_interpreter._call is not one return of prompt_call.call_json(..., chat)")
+    writes = {_callee(n) for n in ast.walk(tree) if isinstance(n, ast.Call)} & _WRITE_CALLS
+    if writes:
+        fail(f"NC1: condition_interpreter.py calls {sorted(writes)}")
+    imported = _imported(tree)
+    bad = {m for m in imported if "cockpit" in m or "condition_drafts" in m} | ({"write_condition"} & imported)
+    if bad:
+        fail(f"NC1: condition_interpreter.py imports {sorted(bad)}")
+
+
+def _nc1_prompt() -> None:
+    from world_engine import condition_interpreter as ci
+    from world_engine.prompt_registry import PROMPT_REGISTRY
+
+    sys.path.insert(0, str(ROOT / "scripts"))
+    import seed_pilot
+
+    spec = PROMPT_REGISTRY.get(ci.INTERPRET_USAGE)
+    if spec is None or spec.surface != "authoring" \
+            or spec.call_sites != ("src/world_engine/condition_interpreter.py:_call",):
+        fail(f"NC1: PROMPT_REGISTRY[{ci.INTERPRET_USAGE!r}] is {spec}")
+    heads = seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS
+    if [h["usage"] for h in heads] != [ci.INTERPRET_USAGE]:
+        fail(f"NC1: CONDITION_INTERPRET_PROMPT_HEADS carries {[h['usage'] for h in heads]}")
+        return
+    used = set(re.findall(r"\{([a-z_]+)\}", heads[0]["user_template"]))
+    if used != set(heads[0]["variables"]) or used != _value_keys():
+        fail(f"NC1: the head declares {sorted(heads[0]['variables'])}, its template uses {sorted(used)}, "
+             f"prompt_values gives {sorted(_value_keys())}")
+    script = (ROOT / "scripts" / "apply_ticket_0112_condition_prompt.py").read_text(encoding="utf-8")
+    if "CONDITION_INTERPRET_PROMPT_HEADS" not in script or "Tu " in script:
+        fail("NC1: the delivery script does not read the single source, or embeds text")
+
+
+def _value_keys() -> set[str]:
+    from world_engine import condition_interpreter as ci
+    from world_engine.fact_refs import CodedRefs
+
+    empty = CodedRefs(codes={}, lines=())
+    ctx = ci.InterpreterContext(entity_lines=(), lists={k: empty for k in "efqs"}, current=None)
+    return set(ci.prompt_values(ctx, "eligibility", "x", []))
+
+
+def check_nc1() -> None:
+    _nc1_tables()
+    _nc1_module()
+    _nc1_prompt()
+
+
+# --- NC2-NC4 fixture -----------------------------------------------------------
+
+def _entity(session, world_id: str, kind: str, name: str) -> str:
+    from world_engine.models import Character, Entity, Faction, Item, Location
+
+    row = Entity(world_id=world_id, type=kind, name=name)
+    session.add(row)
+    session.flush()
+    extra = {"character": lambda: Character(id=row.id, world_id=world_id, character_type="npc"),
+             "faction": lambda: Faction(id=row.id), "item": lambda: Item(id=row.id),
+             "location": lambda: Location(id=row.id)}[kind]()
+    session.add(extra)
+    session.flush()
+    return row.id
+
+
+def _nc_world(session) -> dict:
+    from world_engine.models import Knowledge, QuestOffer, SkillDefinition, World
+    from world_engine.writes.facts import attach_participants, create_fact
+
+    world = World(name="Interprète NC", is_active=False)
+    session.add(world)
+    session.flush()
+    ids = {"world": world.id}
+    for key, kind, name in (("pc", "character", "Aube"), ("garde", "character", "Garde Brennar"),
+                            ("mira1", "character", "Mira"), ("mira2", "character", "Mira"),
+                            ("guild", "faction", "Guilde des chasseurs"), ("fur", "item", "Fourrure de loup"),
+                            ("tower", "location", "Tour Nord")):
+        ids[key] = _entity(session, world.id, kind, name)
+    for key, content, owner in (("f_garde", "Garde Brennar a perdu son frère", "garde"),
+                                ("f_secret", "Garde Brennar vole la Guilde", "garde"),
+                                ("f_world", "Les loups descendent l'hiver", None),
+                                ("f_tree", "La Tour Nord est hantée", "tower")):
+        fact = create_fact(session, world_id=world.id, content=content, created_by="check", facet="information")
+        session.flush()
+        if owner:
+            attach_participants(session, fact=fact, entity_ids=[ids[owner]])
+        ids[key] = fact.id
+    session.add(Knowledge(entity_id=ids["garde"], fact_id=ids["f_secret"], level="unaware", is_secret=True))
+    offer = QuestOffer(world_id=world.id, giver_entity_id=ids["garde"], title="Les fourrures", change_history=[])
+    skill = SkillDefinition(world_id=world.id, name="Pistage", base_domain="perception")
+    session.add(offer)
+    session.add(skill)
+    session.commit()
+    ids.update(offer=offer.id, skill=skill.id)
+    return ids
+
+
+def _seed_interpret_prompt(session) -> None:
+    sys.path.insert(0, str(ROOT / "scripts"))
+    import seed_pilot
+    from world_engine.models import PromptTemplate
+
+    for head in seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS:
+        if session.get(PromptTemplate, head["id"]) is None:
+            seed_pilot.upsert_prompt_template(session, **dict(head))
+    session.commit()
+
+
+def _leafd(form, **kw) -> dict:
+    base = {"op": "leaf", "type": form, "subject_role": "doer", "subject_entity_id": None,
+            "target_entity_id": None, "target_key": None, "threshold": None, "value": None}
+    base.update(kw)
+    return base
+
+
+def _full_tree(ids) -> dict:
+    return {"op": "all", "children": [
+        _leafd("knowledge", target_key=ids["f_tree"]),
+        {"op": "any", "children": [
+            _leafd("quest_state", target_key=ids["offer"], value="completed"),
+            _leafd("skill_rank_gte", target_key=ids["skill"], threshold=2)]},
+        {"op": "not", "children": [_leafd("faction_member", target_entity_id=ids["guild"])]},
+        {"op": "at_least", "n": 1, "children": [
+            _leafd("resource", target_key="monnaie", threshold=30),
+            _leafd("vital_status", subject_role=None, subject_entity_id=ids["garde"], value="alive"),
+            _leafd("location_reachable", target_entity_id=ids["tower"])]},
+    ]}
+
+
+# --- NC2 -----------------------------------------------------------------------
+
+def check_nc2(engine, ids) -> None:
+    from sqlmodel import Session
+
+    from world_engine import condition_interpreter as ci
+    from world_engine.condition_forms import REQUIREMENT_TYPES
+    from world_engine.condition_text import FORM_PHRASES_FR
+    from world_engine.conditions import node_from_dict, node_to_dict
+
+    with Session(engine) as session:
+        tree = node_from_dict(_full_tree(ids))
+        ctx = ci.build_context(session, ids["world"], "Garde Brennar doit être en vie", tree)
+        facts = list(ctx.lists["f"].codes.values())
+        if facts[:1] != [ids["f_tree"]] or not {ids["f_garde"], ids["f_secret"], ids["f_world"]} <= set(facts) \
+                or facts.index(ids["f_garde"]) > facts.index(ids["f_world"]):
+            fail(f"NC2: the coded facts are {facts}")
+        skills = list(ctx.lists["s"].codes.values())
+        if skills != ["physical", "agility", "perception", "composure", ids["skill"]] \
+                or list(ctx.lists["q"].codes.values()) != [ids["offer"]]:
+            fail(f"NC2: skills {skills}, offers {ctx.lists['q'].codes}")
+        if set(ctx.lists["e"].codes.values()) != {ids["guild"], ids["garde"], ids["tower"]} \
+                or ctx.entity_lines != ("- Garde Brennar (character)",):
+            fail(f"NC2: tree entities {ctx.lists['e'].lines}, named {ctx.entity_lines}")
+        reading = ci.read_answer(session, ids["world"], ctx.current, ctx)
+        back, errors = ci.validate(session, ids["world"], reading.pending) if reading.pending else (None, ["none"])
+        if errors or reading.errors or node_to_dict(back) != node_to_dict(tree):
+            fail(f"NC2: the round trip gave {node_to_dict(back)} with {errors or reading.errors}")
+    lines = ci.form_lines().splitlines()
+    if len(lines) != len(REQUIREMENT_TYPES) or any(FORM_PHRASES_FR[f] not in l for f, l in zip(REQUIREMENT_TYPES, lines)):
+        fail("NC2: form_lines is not one line per form with its phrase")
+
+
+# --- NC3 -----------------------------------------------------------------------
+
+def _answer(condition, unsupported=()) -> str:
+    return json.dumps({"condition": condition, "unsupported": list(unsupported)}, ensure_ascii=False)
+
+
+def _ml(form, subject="doer", target=None, threshold=None, value=None) -> dict:
+    return {"op": "leaf", "form": form, "subject": subject, "target": target, "threshold": threshold,
+            "value": value}
+
+
+FURS = _ml("item_held", target={"name": "fourrure de loup", "kind": "object"}, threshold=15)
+GUILD = _ml("faction_member", target={"name": "Guilde des chasseurs", "kind": "faction"})
+
+
+def _run(ci, session, ids, replies, current=None, instruction="Le joueur a 15 fourrures ou est de la Guilde"):
+    stub, original = _Stub(replies), ci.chat
+    ci.chat = stub
+    try:
+        exchanges: list = []
+        result = ci.interpret(session, ids["world"], "eligibility", instruction, current, exchanges)
+        return result, exchanges, stub
+    finally:
+        ci.chat = original
+
+
+def _nc3_proposed(ci, session, ids) -> None:
+    from world_engine.conditions import node_to_dict
+
+    result, exchanges, _ = _run(ci, session, ids, [_answer({"op": "any", "children": [FURS, GUILD]})])
+    want = {"op": "any", "children": [_leafd("item_held", target_entity_id=ids["fur"], threshold=15),
+                                      _leafd("faction_member", target_entity_id=ids["guild"])]}
+    if result.outcome != "proposed" or node_to_dict(result.tree) != want or len(exchanges) != 1 or result.retried:
+        fail(f"NC3a: {result.outcome}, {node_to_dict(result.tree)}, {len(exchanges)} exchange(s)")
+    result, _, _ = _run(ci, session, ids, [_answer(FURS)])
+    if node_to_dict(result.tree) != {"op": "all", "children": [want["children"][0]]}:
+        fail(f"NC3a: a lone leaf is proposed as {node_to_dict(result.tree)}, not `all` of it")
+    bad = _ml("knowledge", target={"code": "f99"})
+    result, exchanges, stub = _run(ci, session, ids, [_answer({"op": "all", "children": [bad]}),
+                                                      _answer({"op": "all", "children": [FURS]})])
+    second = stub.messages[1][1]["content"] if len(stub.messages) == 2 else ""
+    if result.outcome != "proposed" or not result.retried or len(exchanges) != 2 or "f99" not in second:
+        fail(f"NC3b: {result.outcome}, retried {result.retried}, {len(exchanges)} exchange(s)")
+    result, exchanges, _ = _run(ci, session, ids, [_answer(bad), _answer(bad)])
+    if result.outcome != "refused" or not result.errors or not result.retried or len(exchanges) != 2:
+        fail(f"NC3c: {result.outcome}, {result.errors}, {len(exchanges)} exchange(s)")
+    unknown = _ml("has_met", target={"name": "Zorglub", "kind": "person"})
+    result, exchanges, _ = _run(ci, session, ids, [_answer(unknown)])
+    if result.outcome != "refused" or len(exchanges) != 1 or not any("Zorglub" in e for e in result.errors):
+        fail(f"NC3d: {result.outcome}, {result.errors}, {len(exchanges)} exchange(s)")
+
+
+def _nc3_choice(ci, session, ids) -> None:
+    from world_engine.conditions import node_to_dict
+
+    mira = _ml("has_met", target={"name": "Mira", "kind": "person"})
+    result, _, _ = _run(ci, session, ids, [_answer({"op": "all", "children": [mira, FURS]})])
+    choices = sorted(c["entity_id"] for m in result.mentions for c in m["choices"])
+    if result.outcome != "needs_choice" or choices != sorted([ids["mira1"], ids["mira2"]]):
+        fail(f"NC3e: {result.outcome}, choices {choices}")
+        return
+    ref = next(m["ref"] for m in result.mentions if m["status"] == "ambiguous")
+    done = ci.resolve(session, ids["world"], result.pending, result.mentions, result.notes, {ref: ids["mira2"]})
+    leaf = node_to_dict(done.tree)["children"][0] if done.tree else {}
+    if done.outcome != "proposed" or leaf.get("target_entity_id") != ids["mira2"]:
+        fail(f"NC3e: resolve gave {done.outcome}, {leaf}")
+    try:
+        ci.resolve(session, ids["world"], result.pending, result.mentions, result.notes, {ref: ids["garde"]})
+        fail("NC3e: resolve accepted a pick outside the choices")
+    except ValueError:
+        pass
+
+
+def _nc3_unsupported(ci, session, ids) -> None:
+    result, _, _ = _run(ci, session, ids, [_answer(None, [{"text": "apporte 15 fourrures", "kind": "cost"}])])
+    if result.outcome != "refused" or result.errors or not any("« Coûts »" in n for n in result.notes):
+        fail(f"NC3f: a cost only gave {result.outcome}, {result.errors}, {result.notes}")
+    result, _, _ = _run(ci, session, ids, [_answer(FURS, [{"text": "sans être repéré", "kind": "event"}])])
+    if result.outcome != "proposed" or not any("TICKET-0114" in n for n in result.notes):
+        fail(f"NC3f: a condition and an event gave {result.outcome}, {result.notes}")
+
+
+def _nc3_failures(ci, session, ids) -> None:
+    from world_engine.conditions import node_from_dict
+    from world_engine.llm_parse import LlmParseError
+    from world_engine.ollama_client import OllamaError
+
+    for label, reply, error in (("Ollama down", OllamaError("down"), OllamaError),
+                                ("an unparsable reply", "pas du json", LlmParseError)):
+        try:
+            _run(ci, session, ids, [reply])
+            fail(f"NC3g: {label} did not propagate")
+        except error:
+            pass
+    current = node_from_dict({"op": "all", "children": [_leafd("faction_member", target_entity_id=ids["guild"])]})
+    _, _, stub = _run(ci, session, ids, [_answer(GUILD)], current=current, instruction="ajoute : ou 15 fourrures")
+    message = stub.messages[0][1]["content"] if stub.messages else ""
+    if '"code": "e1"' not in message or "Guilde des chasseurs (faction)" not in message:
+        fail("NC3h: the current tree did not reach the message in the model's form")
+
+
+def _counts(session) -> dict:
+    from sqlmodel import func, select
+
+    from world_engine.models import Condition, ConditionDraft, ConditionNode, Entity, Fact, Knowledge
+
+    return {m.__name__: session.exec(select(func.count()).select_from(m)).one()
+            for m in (Condition, ConditionNode, Fact, Entity, Knowledge, ConditionDraft)}
+
+
+def check_nc3_nc4(engine, ids) -> None:
+    from sqlmodel import Session
+
+    from world_engine import condition_interpreter as ci
+
+    with Session(engine) as session:
+        _seed_interpret_prompt(session)
+        before = _counts(session)
+        _nc3_proposed(ci, session, ids)
+        _nc3_choice(ci, session, ids)
+        _nc3_unsupported(ci, session, ids)
+        _nc3_failures(ci, session, ids)
+        session.commit()
+        after = _counts(session)
+    if after != before:
+        fail(f"NC4: the interpreter wrote rows: {before} -> {after}")
+
+
 def main() -> int:
     db_path = _fresh_db()
     from world_engine.db import create_db_and_tables, engine
@@ -503,13 +870,22 @@ def main() -> int:
     check_nb1()
     check_nb2(engine, db_path)
     check_nb3()
+    check_nc1()
+    from sqlmodel import Session
+    with Session(engine) as session:
+        nc_ids = _nc_world(session)
+    check_nc2(engine, nc_ids)
+    check_nc3_nc4(engine, nc_ids)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
         return 1
     print("PASS: condition_interpreter -- one coded list names facts, quest offers and skills by code; "
           "one templated JSON call serves the creator's authoring tools; v2.21 journals every proposal "
-          "of the interpreter, outside any world, its outcome moving one way to « saved »")
+          "of the interpreter, outside any world, its outcome moving one way to « saved »; the "
+          "interpreter shows the model the language and coded lists, reads its answer back through codes "
+          "and the name index, validates every leaf, asks once more with the errors, leaves a name to "
+          "the creator, never writes a condition, and sends a cost back to the offer's terms")
     return 0
 
 
diff --git a/tooling/verify/checks/knowledge_identity.py b/tooling/verify/checks/knowledge_identity.py
index 8400fd9..b1cf9b4 100644
--- a/tooling/verify/checks/knowledge_identity.py
+++ b/tooling/verify/checks/knowledge_identity.py
@@ -113,6 +113,9 @@ _SUBJECT_CENSUS: dict[str, int] = {
     # TICKET-0101, BRIEF-0101-C: `discoverable_detail.subject`, the label a
     # promotion lists for a detail it moves -- never a knowledge key.
     "src/world_engine/writes/zone_promotion.py": 3,
+    # TICKET-0112, BRIEF-0112-C: a condition leaf's `subject` in the model's
+    # form (C-03) -- whom the leaf judges, never a knowledge key.
+    "src/world_engine/condition_interpreter.py": 3,
 }
 
 A = "11111111-1111-1111-1111-111111111111"
diff --git a/tooling/verify/checks/name_index.py b/tooling/verify/checks/name_index.py
index 6e060ab..06aeabb 100644
--- a/tooling/verify/checks/name_index.py
+++ b/tooling/verify/checks/name_index.py
@@ -19,7 +19,9 @@ R5 (creator confinement) -- across `src/world_engine/**/*.py`, `CREATOR`
    `NameScope(` call whose regime is the literal `"creator"` occur only in
    `name_index.py`, `lore_query.py`, `lore_mentions_read.py`,
    `writes/facets.py`, `lore_write_draft.py` (the writing panel resolves the
-   names of the creator's own statement, TICKET-0098, BRIEF-0098-D).
+   names of the creator's own statement, TICKET-0098, BRIEF-0098-D),
+   `condition_interpreter.py` (the names of her condition, TICKET-0112,
+   BRIEF-0112-C).
    Vacuity guard: at least one file parsed.
 R6 (explicit scope, BRIEF-0092-b) -- across `src/world_engine/**/*.py`, every
    call whose callee name (a Name, or the last part of an Attribute) is
@@ -58,6 +60,9 @@ CREATOR_ALLOWED = {
     "src/world_engine/lore_mentions_read.py",
     "src/world_engine/writes/facets.py",
     "src/world_engine/lore_write_draft.py",
+    # TICKET-0112 (BRIEF-0112-C, ID1a): the condition interpreter resolves the
+    # names of the creator's own sentence, a surface of the creator's.
+    "src/world_engine/condition_interpreter.py",
 }
 
 FAILURES: list[str] = []
````

2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit as one commit: `BRIEF-0112-C: the condition interpreter`.
4. Do not run the delivery script on Nia's database: she runs it at the live gate.

## Scope OUT

- Costs and rewards as output (IA2), a whole offer (IA3): the interpreter answers conditions only.
- A dry-run verdict on a character (IG2).
- New forms, states, events or time (0113, 0114): `TARGET_HINTS_FR` follows `REQUIREMENT_TYPES` as it is.
- Any write: no `db.add`, no `commit`, no call to `write_condition` or to the journal's writer (NC1, NC4).
- Hiding creator-only facts from the model (IE2, rejected).
- A model-side name resolution or a pick by the tool among homonyms (0092: the creator picks).
- Changing the Lore panel's prompts or `draft_context` (its creator-only exclusion stays).
- The routes, the journal's use, the editor (BRIEF-0112-D, E).

## Invariants to defend

**A model never emits an id** -- every target is a name resolved by `name_index` or a code resolved by its list; a code the list did not show is an error (NC3 b-c). **Creator control is structural** -- the interpreter writes nothing; it proposes a tree the creator inserts (NC4). **Secrets** -- the creator-only facts reach the model and, through D, the creator's journal: a creator surface only (IE1); no player surface reads anything this brief produces. **Name resolution never picks** -- ambiguity goes up with its candidates (NC3 e). **Prompts are data** -- the text lives in `prompt_template` / `prompt_version`, seeded once (S2), the model per template (`effective_model`).

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- A named mutation does not turn its rule red.
- `name_index.py` or `knowledge_identity.py` turns red for a file other than `condition_interpreter.py`.
- The interpreter would need to import `cockpit` or a writer to work.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `CREATOR_ALLOWED` or `_SUBJECT_CENSUS` gained entries since: add the interpreter's line next to theirs, same reason text.

REPORT-ONLY:
- Timing of the corpus run; a check that times out under load and passes when rerun alone (name it).
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.
- The model the prompt runs on: `AUTHOR_MODEL` by default (IJ1), changed by Nia in Prompts.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/condition_interpreter.py` -> `PASS: condition_interpreter -- one coded list names facts, quest offers and skills by code; one templated JSON call serves the creator's authoring tools; v2.21 journals every proposal of the interpreter, outside any world, its outcome moving one way to « saved »; the interpreter shows the model the language and coded lists, reads its answer back through codes and the name index, validates every leaf, asks once more with the errors, leaves a name to the creator, never writes a condition, and sends a cost back to the offer's terms`
- `name_index.py`, `knowledge_identity.py`, `prompt_registry.py`, `prompt_model_write.py`, `prompt_version.py`, `lore_write.py`, `lore_isolation.py`, `conditions.py`, `claude_md_contract.py`, `module_budget.py`, `function_length.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`condition_interpreter.py` exits 1 with the rule named):
  - in `src/world_engine/condition_interpreter.py`, `    return any(e not in names and e != NOTHING_PROPOSED_FR for e in result.errors)` -> `    return False` -> `NC3`
  - in `src/world_engine/condition_interpreter.py`, `ajoute-le dans « Coûts » de l'offre.` -> `ajoute-le dans les coûts de l'offre.` -> `NC1`
  - in `src/world_engine/condition_interpreter.py`, `    fact_ids = list(ids["f"])` -> `    fact_ids = []` -> `NC2`
  - in `src/world_engine/condition_interpreter.py`, `    return (all_of(leaves(clean)) if clean.op == "leaf" else clean), []` -> `    return clean, []` -> `NC3`
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 145/145.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry « THE CONDITION INTERPRETER: A SENTENCE BECOMES A TREE THE CREATOR CONFIRMS (TICKET-0112) -- THE MODEL PROPOSES, CODE READS IT BACK AND VALIDATES EVERY LEAF (BRIEF-0112-c, no schema change) » -- in the diff. `CLAUDE.md` line 461 -- in the diff. No schema change.
