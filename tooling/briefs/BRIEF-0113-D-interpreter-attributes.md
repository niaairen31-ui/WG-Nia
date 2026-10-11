<!-- slug: interpreter-attributes -->
# BRIEF 0113-D — "The interpreter reads the states of the world -- an `a` list of coded attributes, a choice by its label, the prompt delivered fragment by fragment"

Lot: LOT-0113-world-state.md (authoritative on conflict)
Depends on: BRIEF-0113-C (C-02, C-04)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0113-C's commit).

- `src/world_engine/condition_interpreter.py:67` -> `TARGET_HINTS_FR: dict[str, str] = {`
- `src/world_engine/condition_interpreter.py:83` -> `CODE_LISTS: dict[str, str] = {"knowledge": "f", "quest_state": "q", "skill_rank_gte": "s"}`
- `src/world_engine/condition_interpreter.py:106` -> `class InterpreterContext:`
- `scripts/seed_pilot.py:1954` -> `CONDITION_INTERPRET_SYSTEM_PROMPT = """\`
- `scripts/seed_pilot.py:2006` -> `CONDITION_INTERPRET_USER_TEMPLATE = """\`
- `scripts/seed_pilot.py:2041` -> `CONDITION_INTERPRET_PROMPT_HEADS = (`
- No `scripts/apply_ticket_0113_condition_prompt.py`, no `tooling/verify/checks/attribute_interpreter.py`; no `CONDITION_INTERPRET_FRAGMENTS` in `scripts/seed_pilot.py`.

## Facts carried

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

### R-19 — fifteen seconds per check [M]
Opened: `tooling/verify/checks/corpus_gate.py:21-28` (per-check timeout,
`TIMEOUT` a failure); `.claude/rules/verify-checks.md` (15 s).
Consequence: the rules are split over three checks -- `attributes.py`
(AA, AC; ~5 s measured), `attribute_conditions.py` (AB; ~7 s),
`attribute_interpreter.py` (AD, AE; ~6 s) -- each wrapping every rule so a
crash is a named failure.

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

## Context

The interpreter (TICKET-0112) still answers « l'état du monde n'est pas encore une condition ». It now sees every attribute of the world in one more coded list, `a` -- the system ones, then the world's, a hidden one included (a creator surface, IE1) -- and writes an `attribute` leaf: a choice by its label, a number by its threshold, an entity by its name. A state the world lacks is still listed, now with « définis-le dans Création › États, puis redemande » -- until E lets the interpreter propose it. The prompt changes as fragments over the 0112 text: the seed derives its text from them, and the delivery script applies them to Nia's current version, keeping any edit she made.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `condition_interpreter.py`: `CODE_LISTS["attribute"] = "a"`, `InterpreterContext.attributes`, `attribute_line`, `encode` writes a choice back as its label, `_attribute_value` reads a label back (case- and accent-blind), the state note, the prompt value `attributes` (C-08);
   - `seed_pilot.py`: the 0112 texts kept as `CONDITION_INTERPRET_SYSTEM_PROMPT_0112` / `..._USER_TEMPLATE_0112`, `CONDITION_INTERPRET_FRAGMENTS`, `with_condition_fragments` (new text first, idempotent), the seed text derived; the head's variables gain `attributes`;
   - creates `scripts/apply_ticket_0113_condition_prompt.py` (b-5);
   - creates check `attribute_interpreter.py` (AD1-AD4); `condition_interpreter.py` (check) NC1's state note and its list of prefixes follow;
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - scripts/apply_ticket_0113_condition_prompt.py
   - scripts/seed_pilot.py
   - src/world_engine/condition_interpreter.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/attribute_interpreter.py
   - tooling/verify/checks/condition_interpreter.py

````diff
diff --git a/scripts/apply_ticket_0113_condition_prompt.py b/scripts/apply_ticket_0113_condition_prompt.py
new file mode 100644
index 0000000..647ee75
--- /dev/null
+++ b/scripts/apply_ticket_0113_condition_prompt.py
@@ -0,0 +1,95 @@
+"""One-shot, idempotent delivery of the TICKET-0113 condition interpreter's
+prompt update onto the live DB (BRIEF-0113-D): the model reads the world's
+attributes -- the `a` list, a new variable `attributes` -- and writes an
+`attribute` leaf.
+
+Like `apply_ticket_0110_link_prompt.py`, it edits the CURRENT version of
+`pt-condition-interpret` fragment by fragment, so an edit the creator made
+in the Prompts tab is kept. The fragments are
+`seed_pilot.CONDITION_INTERPRET_FRAGMENTS` (single source: the seed's text
+is the 0112 text with the same fragments applied). Per fragment: its new
+text present -> already done (looked for first: an old fragment may stand
+inside its own new text); else its old text present -> replaced; neither
+-> reported, to be edited by hand. The head's variables are first set to the
+seed's (`write_prompt_variables`), since a new version may only use
+declared placeholders.
+
+History is sacred: a changed text lands as a new `prompt_version` row
+through `write_prompt_version`, the old one untouched. Touches nothing else.
+Safe to re-run: an already-updated head prints "unchanged".
+
+Run after `migrate_v2_23_attribute_leaves.py`:
+
+    python scripts/apply_ticket_0113_condition_prompt.py
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
+        "apply_ticket_0113_condition_prompt.py refuses to run unless "
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
+from world_engine.models import PromptTemplate  # noqa: E402
+from world_engine.prompt_store import current_prompt  # noqa: E402
+from world_engine.writes import write_prompt_version  # noqa: E402
+from world_engine.writes.prompts import write_prompt_variables  # noqa: E402
+
+HEAD = seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS[0]
+NOTE = "TICKET-0113 BRIEF-0113-D -- the interpreter reads the world's attributes"
+
+
+def apply_fragments(texts: dict[str, str]) -> tuple[dict[str, str], list[str]]:
+    """`texts` (`system_prompt`, `user_template`) with every fragment applied
+    where its old text stands; the fragments found in neither form."""
+    out = dict(texts)
+    missing = []
+    for field, old, new in seed_pilot.CONDITION_INTERPRET_FRAGMENTS:
+        if new in out[field]:
+            continue
+        if old in out[field]:
+            out[field] = out[field].replace(old, new)
+        else:
+            missing.append(f"{field}: {old[:60]}…")
+    return out, missing
+
+
+def main() -> None:
+    with Session(engine) as session:
+        head = session.get(PromptTemplate, HEAD["id"])
+        if head is None:
+            print(f"{HEAD['id']}: head not found -- nothing to do (the seed creates it)")
+            return
+        write_prompt_variables(session, template_id=head.id, variables=HEAD["variables"])
+        current = current_prompt(session, head)
+        texts, missing = apply_fragments({"system_prompt": current.system_prompt,
+                                          "user_template": current.user_template})
+        for line in missing:
+            print(f"{HEAD['id']}: fragment not found, edit by hand -- {line}")
+        if texts == {"system_prompt": current.system_prompt, "user_template": current.user_template}:
+            session.commit()
+            print(f"{HEAD['id']}: unchanged (v{current.version_number})")
+            return
+        version = write_prompt_version(session, template_id=head.id, system_prompt=texts["system_prompt"],
+                                       user_template=texts["user_template"], note=NOTE)
+        session.commit()
+        print(f"{HEAD['id']}: v{current.version_number} -> v{version.version_number}")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/scripts/seed_pilot.py b/scripts/seed_pilot.py
index 20457b6..e14bcd8 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -1951,7 +1951,7 @@ LORE_WRITE_PROMPT_HEADS = (
 # leaf, and the creator confirms before anything reaches the offer
 # (condition_interpreter.interpret). A cost or a reward is never a condition
 # (IA1); what the language cannot say yet is listed, never forced (IF1).
-CONDITION_INTERPRET_SYSTEM_PROMPT = """\
+CONDITION_INTERPRET_SYSTEM_PROMPT_0112 = """\
 Tu traduis en condition la phrase qu'écrit la créatrice d'un monde de jeu \
 de rôle pour une offre de quête. Une condition est un arbre.
 
@@ -2003,7 +2003,7 @@ Réponds UNIQUEMENT avec ce JSON :
 "condition" vaut null si rien de la phrase n'est une condition.\
 """
 
-CONDITION_INTERPRET_USER_TEMPLATE = """\
+CONDITION_INTERPRET_USER_TEMPLATE_0112 = """\
 La condition dit : {role}.
 
 Formes :
@@ -2035,9 +2035,54 @@ Erreurs de ta réponse précédente :
 """
 
 
+# TICKET-0113 (BRIEF-0113-D): the attributes. Each change to the 0112 text is
+# one (field, old fragment, new fragment), applied in order -- the seed's
+# text below and scripts/apply_ticket_0113_condition_prompt.py (which edits
+# the CURRENT version fragment by fragment, so an edit the creator made in
+# the Prompts tab is kept) read this one tuple, so they cannot diverge.
+CONDITION_INTERPRET_FRAGMENTS: tuple[tuple[str, str, str], ...] = (
+    ("system_prompt",
+     'une compétence {"code": "s1"} ; null si la forme n\'a pas de cible ;',
+     'une compétence {"code": "s1"}, un état {"code": "a2"} ; null si la forme n\'a pas de cible ;'),
+    ("system_prompt",
+     '- "value" : une des valeurs de la forme quand elle en a, sinon null.',
+     '- "value" : une des valeurs de la forme quand elle en a, sinon null.\n'
+     'ÉTATS. La forme attribute lit un état de la liste des états : "target" est son code '
+     '{"code": "a2"} ; pour un choix, "value" est un de ses libellés ; pour un nombre, "threshold" '
+     'est le minimum ; pour une entité, "value" est une entité {"name": "...", "kind": "..."}, ou '
+     'null pour « quelqu\'un ». Un état porte sur toute entité à laquelle il s\'applique : son '
+     '"subject" peut être un lieu ou un objet {"name": "...", "kind": "place" | "object"}.'),
+    ("system_prompt",
+     'un fait, une quête ou une compétence absent des listes ne peut pas être une cible.',
+     'un fait, une quête, une compétence ou un état absent des listes ne peut pas être une cible.'),
+    ("system_prompt",
+     "l'état d'une chose (\"state\" : la porte est ouverte)",
+     "un état absent de la liste des états (\"state\" : la porte est ouverte, sans état « ouverte »)"),
+    ("user_template",
+     "Condition actuelle :\n{current}",
+     "États (code — nom, sorte, pour qui) :\n{attributes}\n\nCondition actuelle :\n{current}"),
+)
+
+
+def with_condition_fragments(field: str, text: str) -> str:
+    """`text` with every fragment of `CONDITION_INTERPRET_FRAGMENTS` for
+    `field` applied, in order."""
+    for target, old, new in CONDITION_INTERPRET_FRAGMENTS:
+        if target == field:
+            text = text.replace(old, new)
+    return text
+
+
+CONDITION_INTERPRET_SYSTEM_PROMPT = with_condition_fragments(
+    "system_prompt", CONDITION_INTERPRET_SYSTEM_PROMPT_0112)
+CONDITION_INTERPRET_USER_TEMPLATE = with_condition_fragments(
+    "user_template", CONDITION_INTERPRET_USER_TEMPLATE_0112)
+
+
 # The interpreter's head, one tuple read by the seed and by
 # scripts/apply_ticket_0112_condition_prompt.py (single source, the
-# LORE_WRITE_PROMPT_HEADS precedent).
+# LORE_WRITE_PROMPT_HEADS precedent); its variables by
+# scripts/apply_ticket_0113_condition_prompt.py.
 CONDITION_INTERPRET_PROMPT_HEADS = (
     dict(
         id="pt-condition-interpret",
@@ -2046,8 +2091,8 @@ CONDITION_INTERPRET_PROMPT_HEADS = (
         world_id=None,
         system_prompt=CONDITION_INTERPRET_SYSTEM_PROMPT,
         user_template=CONDITION_INTERPRET_USER_TEMPLATE,
-        variables=["role", "forms", "entities", "tree_entities", "facts", "offers", "skills", "current",
-                   "instruction", "errors"],
+        variables=["role", "forms", "entities", "tree_entities", "facts", "offers", "skills", "attributes",
+                   "current", "instruction", "errors"],
         destination="local",
     ),
 )
diff --git a/src/world_engine/condition_interpreter.py b/src/world_engine/condition_interpreter.py
index ca22b68..4815850 100644
--- a/src/world_engine/condition_interpreter.py
+++ b/src/world_engine/condition_interpreter.py
@@ -5,7 +5,8 @@ conditions series, IA1-IK1 of TICKET-0112).
 The model proposes, code validates, the creator confirms (A1): nothing here
 writes. `interpret` shows the model the language (`form_lines`), the
 entities the instruction names, coded lists of the world's facts (`f`), its
-quest offers (`q`) and skills (`s`), and -- when the creator edits a
+quest offers (`q`), skills (`s`) and attributes (`a`, TICKET-0113: a state
+by its code, a choice by its label), and -- when the creator edits a
 condition (IC1) -- the current tree in the model's own form, its entities
 coded `e`. The model answers that form (C-03): entities by name (or by an
 `e` code), every other target by code, never an id (ID1a). Code reads the
@@ -34,11 +35,12 @@ from typing import Any, Optional
 from sqlmodel import Session, select
 
 from . import model_exchange, prompt_call
+from .attributes import ATTRIBUTE_FORM, AttributeView, world_attributes, world_entity_type_labels
 from .condition_forms import ENTITY_TARGET_TYPES, FORM_VALUES, REQUIREMENT_TYPES, RequirementSpec
 from .condition_text import FORM_PHRASES_FR, VALUE_LABELS_FR
 from .conditions import CONNECTORS, SUBJECT_ROLES, ConditionTree, all_of, check_shape, leaves, node_to_dict
 from .fact_refs import CodedRefs, code_facts, code_refs
-from .lore_resolve import CATEGORIES, near_candidates, resolve_named
+from .lore_resolve import CATEGORIES, near_candidates, normalize_surface, resolve_named
 from .lore_write_draft import MAX_CODED_FACTS, named_entity_ids, world_fact_ids
 from .models import BASE_SKILL_DOMAINS, Entity, FactParticipant, QuestOffer, SkillDefinition
 from .name_index import CREATOR
@@ -76,17 +78,18 @@ TARGET_HINTS_FR: dict[str, str] = {
     "has_debt_to": "un personnage ou une faction, par son nom",
     "no_debt_to": "un personnage ou une faction, par son nom",
     "item_held": "un objet, par son nom ; seuil = la quantité minimale",
-    "attribute": "un état, par son code a ; valeur = un de ses libellés, seuil = le minimum pour un nombre, "
-                 "cible = une entité par son nom (aucune : quelqu'un)",
+    "attribute": "un état, par son code a ; pour un choix, valeur = un de ses libellés ; pour un nombre, "
+                 "seuil = le minimum ; pour une entité, valeur = une entité par son nom, ou null pour "
+                 "« quelqu'un »",
 }
 # The forms whose target is a code, and the list each code comes from.
-CODE_LISTS: dict[str, str] = {"knowledge": "f", "quest_state": "q", "skill_rank_gte": "s"}
+CODE_LISTS: dict[str, str] = {"knowledge": "f", "quest_state": "q", "skill_rank_gte": "s", "attribute": "a"}
 
 # IF1: what the language cannot say yet, by the kind the model gives it, and
 # where it will come from. IA1: a cost or a reward is a term of the offer.
 UNSUPPORTED_NOTES_FR: dict[str, str] = {
-    "state": "« {text} » : l'état du monde (ouvert, détruit, occupé…) n'est pas encore une "
-             "condition ; il arrive avec les attributs (TICKET-0113).",
+    "state": "« {text} » : cet état n'existe pas encore dans ce monde ; définis-le dans Création › États, "
+             "puis redemande.",
     "event": "« {text} » : ce qui s'est passé (tué, repéré, capturé…) n'est pas encore une "
              "condition ; il arrive avec le journal d'événements (TICKET-0114).",
     "time": "« {text} » : le temps (avant le jour N, pendant N tours) n'est pas encore une "
@@ -107,12 +110,13 @@ class InterpreterContext:
     """What the model may see; the coded lists also resolve its answer."""
 
     entity_lines: tuple[str, ...]
-    lists: dict[str, CodedRefs]  # "e", "f", "q", "s"
+    lists: dict[str, CodedRefs]  # "e", "f", "q", "s", "a"
     current: Optional[dict]
+    attributes: dict[str, AttributeView] = field(default_factory=dict)  # key -> view, the `a` list's
 
 
 def _current_ids(tree: Optional[ConditionTree]) -> dict[str, list[str]]:
-    found: dict[str, list[str]] = {"e": [], "f": [], "q": [], "s": []}
+    found: dict[str, list[str]] = {"e": [], "f": [], "q": [], "s": [], "a": []}
     for spec in leaves(tree):
         for entity_id in (spec.subject_entity_id, spec.target_entity_id):
             if entity_id and entity_id not in found["e"]:
@@ -146,15 +150,33 @@ def build_context(db: Session, world_id: str, instruction: str, current: Optiona
             FactParticipant.entity_id == entity_id).order_by(FactParticipant.fact_id)).all()
     fact_ids += world_fact_ids(db, world_id)
     offers = db.exec(select(QuestOffer).where(QuestOffer.world_id == world_id)).all()
+    attributes = {view.key: view for view in world_attributes(db, world_id)}
+    types = {t["type"]: t["label"].lower() for t in world_entity_type_labels(db, world_id)}
     lists = {
         "e": code_refs("e", ((eid, _entity_label(db, eid)) for eid in ids["e"])),
         "f": code_facts(db, list(dict.fromkeys(fact_ids))[:MAX_CODED_FACTS]),
         "q": code_refs("q", sorted(((o.id, o.title) for o in offers), key=lambda pair: pair[1].lower())),
         "s": code_refs("s", _skill_pairs(db, world_id)),
+        "a": code_refs("a", ((key, attribute_line(view, types)) for key, view in attributes.items())),
     }
     lines = tuple(f"- {_entity_label(db, eid)}" for eid in named)
-    return InterpreterContext(entity_lines=lines, lists=lists,
-                              current=encode(current, lists) if current is not None else None)
+    return InterpreterContext(entity_lines=lines, lists=lists, attributes=attributes,
+                              current=encode(current, lists, attributes) if current is not None else None)
+
+
+def attribute_line(view: AttributeView, types: dict[str, str]) -> str:
+    """One attribute as the model reads it in the `a` list (BRIEF-0113-D):
+    its name, its kind and what it compares to, the types it applies to."""
+    holders = "toute entité" if view.holder_types is None else ", ".join(
+        types.get(t, t) for t in view.holder_types)
+    if view.kind == "choice":
+        kind = "choix : " + ", ".join(label for _key, label in view.choices)
+    elif view.kind == "integer":
+        kind = "nombre"
+    else:
+        kind = "une entité : " + ", ".join(types.get(t, t) for t in view.value_types)
+    system = "système ; " if view.system else ""
+    return f"{view.name} ({system}{kind} ; pour : {holders})"
 
 
 # --- the model's form (C-03) ---------------------------------------------------
@@ -163,21 +185,29 @@ def _encode_ref(entity_id: Optional[str], lists: dict[str, CodedRefs]) -> Option
     return {"code": lists["e"].code_of(entity_id)} if entity_id else None
 
 
-def encode(tree: ConditionTree, lists: dict[str, CodedRefs]) -> dict:
+def encode(tree: ConditionTree, lists: dict[str, CodedRefs], attributes: Optional[dict] = None) -> dict:
     """A clean tree in the model's form: entities by `e` code, facts,
-    offers and skills by their code."""
+    offers, skills and attributes by their code; an attribute's choice by
+    its label, its entity value by `e` code (BRIEF-0113-D)."""
     if tree.op != "leaf":
-        out: dict[str, Any] = {"op": tree.op, "children": [encode(c, lists) for c in tree.children]}
+        out: dict[str, Any] = {"op": tree.op, "children": [encode(c, lists, attributes) for c in tree.children]}
         if tree.op == "at_least":
             out["n"] = tree.n
         return out
     spec = tree.leaf
     target = _encode_ref(spec.target_entity_id, lists)
+    value: Any = spec.value
     if spec.type in CODE_LISTS:
         target = {"code": lists[CODE_LISTS[spec.type]].code_of(spec.target_key)}
+    if spec.type == ATTRIBUTE_FORM:
+        view = (attributes or {}).get(spec.target_key)
+        if view is not None and view.kind == "choice":
+            value = dict(view.choices).get(spec.value, spec.value)
+        elif view is not None and view.kind == "entity":
+            value = _encode_ref(spec.target_entity_id, lists)
     return {"op": "leaf", "form": spec.type,
             "subject": spec.subject_role or _encode_ref(spec.subject_entity_id, lists),
-            "target": target, "threshold": spec.threshold, "value": spec.value}
+            "target": target, "threshold": spec.threshold, "value": value}
 
 
 def form_lines() -> str:
@@ -279,9 +309,40 @@ def _leaf(db: Session, world_id: str, raw: dict, ctx: InterpreterContext, readin
             reading.errors.append(f"{where}code inconnu {code!r} (attendu : un code {CODE_LISTS[form]})")
     elif form == "resource":
         out["target_key"] = RESOURCE_KEY
+    if form == ATTRIBUTE_FORM and out["target_key"] is not None:
+        _attribute_value(db, world_id, raw, ctx, reading, where, out)
     return {k: v for k, v in out.items() if v is not None or not k.endswith("_mention")}
 
 
+def _attribute_value(db: Session, world_id: str, raw: dict, ctx: InterpreterContext, reading: Reading,
+                     where: str, out: dict) -> None:
+    """What an `attribute` leaf compares to, by its attribute's kind
+    (BRIEF-0113-D): a choice's label -- or its stored value -- read back to
+    its key; an integer's threshold kept; an entity named (or null: anyone)
+    resolved like any target."""
+    view = ctx.attributes.get(out["target_key"])
+    if view is None:
+        return
+    value = raw.get("value")
+    out["value"] = None
+    if view.kind == "integer":
+        return
+    out["threshold"] = None
+    if view.kind == "entity":
+        if value is not None:
+            if isinstance(value, str):
+                value = {"name": value, "kind": "other"}
+            out["target_entity_id"], out["target_mention"] = _entity(db, world_id, value, ctx, reading, where)
+        return
+    wanted = normalize_surface(str(value or ""))
+    for key, label in view.choices:
+        if value == key or (wanted and normalize_surface(label) == wanted):
+            out["value"] = key
+            return
+    labels = ", ".join(label for _key, label in view.choices)
+    reading.errors.append(f"{where}« {value} » n'est pas un libellé de « {view.name} » (libellés : {labels})")
+
+
 def _read(db: Session, world_id: str, raw: Any, ctx: InterpreterContext, reading: Reading, path: str) -> dict:
     where = f"condition {path} : "
     if not isinstance(raw, dict):
@@ -411,6 +472,7 @@ def prompt_values(ctx: InterpreterContext, role: str, instruction: str, errors:
         "role": ROLE_LABELS_FR[role], "forms": form_lines(), "entities": _lines(ctx.entity_lines),
         "tree_entities": _lines(ctx.lists["e"].lines), "facts": _lines(ctx.lists["f"].lines),
         "offers": _lines(ctx.lists["q"].lines), "skills": _lines(ctx.lists["s"].lines),
+        "attributes": _lines(ctx.lists["a"].lines),
         "current": json.dumps(ctx.current, ensure_ascii=False) if ctx.current is not None else "(aucune)",
         "instruction": instruction.strip(), "errors": _lines(f"- {e}" for e in errors),
     }
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index dc956c0..a3fe621 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19162,6 +19162,32 @@ refused by the writer outright.
 **Rejected.** WI2 (definitions created from the sheet only: the world's
 vocabulary scattered).
 
+## THE INTERPRETER READS THE STATES OF THE WORLD (TICKET-0113) -- AN `a` LIST OF CODED ATTRIBUTES, A CHOICE BY ITS LABEL, THE PROMPT DELIVERED FRAGMENT BY FRAGMENT (BRIEF-0113-d, no schema change)
+
+**ID1a, extended.** The interpreter shows the model every active attribute
+of the world -- the system ones, then the world's, a hidden one included
+(IE1: a creator surface) -- in one more coded list, `a`, through the same
+`fact_refs.code_refs`: each line names the attribute, its kind and what it
+compares to, and the types it applies to. An `attribute` leaf in the
+model's form targets its code; a choice is written by its label (read back
+case- and accent-blind to its key), an integer by its threshold, an entity
+by its name (or null: anyone) -- resolved like any target, an ambiguity
+left to the creator. A label the attribute does not have is an error the
+model gets back once (II1), with the attribute's labels.
+
+**A missing state.** Listed as `state`, it reads « définis-le dans
+Création › États, puis redemande » -- until BRIEF-0113-E lets the
+interpreter propose it.
+
+**Delivery.** `seed_pilot.CONDITION_INTERPRET_FRAGMENTS` holds each change
+to the 0112 text as (field, old, new); the seed's text is the 0112 text
+with them applied, and `apply_ticket_0113_condition_prompt.py` applies them
+to the CURRENT version -- an edit the creator made in the Prompts tab is
+kept, a fragment she rewrote is reported -- after declaring the new
+variable `attributes`. One single source: the two cannot diverge. A new
+text is looked for before its old one, since an old fragment may stand
+inside its new text.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/attribute_interpreter.py b/tooling/verify/checks/attribute_interpreter.py
new file mode 100644
index 0000000..da6b7ea
--- /dev/null
+++ b/tooling/verify/checks/attribute_interpreter.py
@@ -0,0 +1,397 @@
+"""G1 check for TICKET-0113 -- the condition interpreter reads and writes states: the `a` list, the attribute leaf, the prompt delivered fragment by fragment.
+
+The lot adds its pieces brief by brief; this check grows with it (the
+`conditions.py` precedent). Each brief adds its rules here in the same
+commit. The interpreter's own rules stay `condition_interpreter.py`'s
+(TICKET-0112).
+
+AD1 -- the shape (BRIEF-0113-D, static and import). `CODE_LISTS` reads
+   `attribute` from the `a` list; `prompt_values` gives `attributes`; the
+   head's variables are exactly its template's placeholders and
+   `attributes` is one; every fragment of `CONDITION_INTERPRET_FRAGMENTS`
+   stands once in the 0112 text of its field and its new text once in the
+   seed's; the seed's texts are the 0112 texts with the fragments applied;
+   `UNSUPPORTED_NOTES_FR["state"]` sends the creator to « Création ›
+   États »; `apply_ticket_0113_condition_prompt.py` reads the fragments and
+   embeds no prompt text.
+AD2 -- context and form (fixture). `build_context` codes every active
+   attribute -- the system ones, then the world's, a hidden one included --
+   in the `a` list, each line naming its kind, its labels or value types
+   and the types it applies to. A tree of `attribute` leaves -- a choice on
+   the doer, an integer on a fixed place, an entity on a fixed item, the
+   same with anyone, `sys:vital_status` on a fixed character -- encodes to
+   the model's form (a choice by its label, an entity value by `e` code)
+   and reads back, bound and validated, to the same tree.
+AD3 -- interpretation (fixture, `condition_interpreter.chat` stubbed). A
+   choice named by its label in another case, an integer by its threshold,
+   an entity value by its name and a place as subject are `proposed` as the
+   expected leaves; a label the attribute does not have is refused with the
+   attribute's labels, then retried; an entity value two characters bear
+   is `needs_choice` and the pick lands in `target_entity_id`; a missing
+   state listed as `state` gives the note that sends to « Création ›
+   États ».
+AD4 -- delivery (`scripts/apply_ticket_0113_condition_prompt.py`, fixture
+   database). On a head holding the 0112 text and variables, it writes one
+   new version whose text is the seed's and declares `attributes`; a second
+   run prints « unchanged » and writes nothing; on a head whose text lost
+   one fragment, the others are applied and the lost one is reported.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import json
+import os
+import pathlib
+import re
+import subprocess
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SCRIPT = ROOT / "scripts" / "apply_ticket_0113_condition_prompt.py"
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
+    sys.path.insert(0, str(ROOT / "scripts"))
+    return db_path
+
+
+class _Stub:
+    def __init__(self, replies):
+        self.replies, self.messages = list(replies), []
+
+    def __call__(self, messages, **kwargs):
+        self.messages.append(messages)
+        reply = self.replies.pop(0)
+        return reply if isinstance(reply, str) else json.dumps(reply)
+
+
+# --- AD1 -------------------------------------------------------------------------
+
+def check_ad1() -> None:
+    import seed_pilot
+
+    from world_engine import condition_interpreter as ci
+    from world_engine.fact_refs import CodedRefs
+
+    if ci.CODE_LISTS.get("attribute") != "a":
+        fail(f"AD1: CODE_LISTS is {ci.CODE_LISTS}")
+    empty = CodedRefs(codes={}, lines=())
+    ctx = ci.InterpreterContext(entity_lines=(), lists={k: empty for k in "efqsa"}, current=None)
+    keys = set(ci.prompt_values(ctx, "eligibility", "x", []))
+    head = seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS[0]
+    used = set(re.findall(r"\{([a-z_]+)\}", head["user_template"]))
+    if used != set(head["variables"]) or used != keys or "attributes" not in used:
+        fail(f"AD1: variables {sorted(head['variables'])}, template {sorted(used)}, values {sorted(keys)}")
+    fragments = seed_pilot.CONDITION_INTERPRET_FRAGMENTS
+    if not fragments:
+        fail("AD1: CONDITION_INTERPRET_FRAGMENTS is empty")
+    old = {"system_prompt": seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT_0112,
+           "user_template": seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE_0112}
+    new = {"system_prompt": seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT,
+           "user_template": seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE}
+    for field, before, after in fragments:
+        if old[field].count(before) != 1 or new[field].count(after) != 1:
+            fail(f"AD1: the fragment {before[:40]!r} stands {old[field].count(before)} time(s) in the 0112 "
+                 f"{field}, its new text {new[field].count(after)} time(s) in the seed's")
+    for field in old:
+        if seed_pilot.with_condition_fragments(field, old[field]) != new[field]:
+            fail(f"AD1: the seed's {field} is not the 0112 text with the fragments applied")
+    if "Création › États" not in ci.UNSUPPORTED_NOTES_FR["state"]:
+        fail(f"AD1: the state note reads {ci.UNSUPPORTED_NOTES_FR['state']!r}")
+    script = SCRIPT.read_text(encoding="utf-8") if SCRIPT.exists() else ""
+    if "CONDITION_INTERPRET_FRAGMENTS" not in script or "Tu " in script or "ÉTATS." in script:
+        fail("AD1: the delivery script does not read the fragments, or embeds prompt text")
+
+
+# --- fixture ---------------------------------------------------------------------
+
+def _entity(db, world_id: str, kind: str, name: str) -> str:
+    from world_engine.models import Character, Entity, Item, Location
+
+    row = Entity(world_id=world_id, type=kind, name=name)
+    db.add(row)
+    db.flush()
+    db.add({"character": lambda: Character(id=row.id, world_id=world_id, character_type="npc"),
+            "item": lambda: Item(id=row.id), "location": lambda: Location(id=row.id)}[kind]())
+    db.flush()
+    return row.id
+
+
+def _world(engine) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.models import World
+    from world_engine.writes.attributes import ChoiceSpec, DefinitionSpec, write_attribute_definition
+
+    with Session(engine) as db:
+        world = World(name="Interprète AD", is_active=False)
+        db.add(world)
+        db.flush()
+        ids = {"world": world.id}
+        for key, kind, name in (("garde", "character", "Garde Brennar"), ("ysa1", "character", "Ysa"),
+                                ("ysa2", "character", "Ysa"), ("trone", "item", "Trône de fer"),
+                                ("crypte", "location", "Crypte")):
+            ids[key] = _entity(db, world.id, kind, name)
+        for key, spec in (
+            ("maudit", DefinitionSpec(name="Maudit", kind="choice", holder_types=("character", "item"),
+                                      choices=(ChoiceSpec("non"), ChoiceSpec("oui")), default="non")),
+            ("alerte", DefinitionSpec(name="Niveau d'alerte", kind="integer", holder_types=("location",),
+                                      default=0)),
+            ("occupe", DefinitionSpec(name="Occupé par", kind="entity", holder_types=("item",),
+                                      value_types=("character",))),
+            ("marque", DefinitionSpec(name="Marqué", kind="choice", holder_types=("character",),
+                                      choices=(ChoiceSpec("non"), ChoiceSpec("oui")), default="non",
+                                      is_hidden=True)),
+        ):
+            ids[key] = write_attribute_definition(db, world_id=world.id, spec=spec).id
+        db.commit()
+    return ids
+
+
+def _seed_prompt(db) -> None:
+    import seed_pilot
+
+    from world_engine.models import PromptTemplate
+
+    for head in seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS:
+        if db.get(PromptTemplate, head["id"]) is None:
+            seed_pilot.upsert_prompt_template(db, **dict(head))
+    db.commit()
+
+
+def _choice(db, world: str, key: str, label: str) -> str:
+    from world_engine.attributes import attribute_view
+
+    return next(k for k, l in attribute_view(db, world, key).choices if l == label)
+
+
+def _leafd(**kw) -> dict:
+    base = {"op": "leaf", "type": "attribute", "subject_role": "doer", "subject_entity_id": None,
+            "target_entity_id": None, "target_key": None, "threshold": None, "value": None}
+    base.update(kw)
+    if kw.get("subject_entity_id"):
+        base["subject_role"] = None
+    return base
+
+
+def _tree(db, ids) -> dict:
+    oui = _choice(db, ids["world"], ids["maudit"], "oui")
+    return {"op": "all", "children": [
+        _leafd(target_key=ids["maudit"], value=oui),
+        _leafd(subject_entity_id=ids["crypte"], target_key=ids["alerte"], threshold=3),
+        _leafd(subject_entity_id=ids["trone"], target_key=ids["occupe"], target_entity_id=ids["garde"]),
+        _leafd(subject_entity_id=ids["trone"], target_key=ids["occupe"]),
+        _leafd(subject_entity_id=ids["garde"], target_key="sys:vital_status", value="dead"),
+    ]}
+
+
+# --- AD2 -------------------------------------------------------------------------
+
+def check_ad2(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine import condition_interpreter as ci
+    from world_engine.conditions import node_from_dict, node_to_dict
+
+    with Session(engine) as db:
+        tree = node_from_dict(_tree(db, ids))
+        ctx = ci.build_context(db, ids["world"], "Le trône est occupé", tree)
+        coded = list(ctx.lists["a"].codes.values())
+        if coded[:3] != ["sys:vital_status", "sys:status", "sys:magic_status"] \
+                or not {ids["maudit"], ids["alerte"], ids["occupe"], ids["marque"]} <= set(coded):
+            fail(f"AD2: the a list codes {coded}")
+        lines = " | ".join(ctx.lists["a"].lines)
+        for needle in ("Maudit (choix : non, oui ; pour : personnage, objet)", "Niveau d'alerte (nombre",
+                       "Occupé par (une entité : personnage", "État vital (système ; choix : en vie"):
+            if needle not in lines:
+                fail(f"AD2: the a list lacks {needle!r}: {lines}")
+        encoded = ctx.current
+        leaves = encoded["children"] if encoded else []
+        if len(leaves) != 5 or leaves[0]["value"] != "oui" or leaves[2]["value"] != {"code": "e3"} \
+                or leaves[3]["value"] is not None or not str(leaves[0]["target"]["code"]).startswith("a"):
+            fail(f"AD2: the tree encodes as {encoded}")
+        reading = ci.read_answer(db, ids["world"], encoded, ctx)
+        back, errors = ci.validate(db, ids["world"], reading.pending) if not reading.errors else (None,
+                                                                                                    reading.errors)
+        if errors or node_to_dict(back) != node_to_dict(tree):
+            fail(f"AD2: the tree reads back as {node_to_dict(back)} ({errors})")
+
+
+# --- AD3 -------------------------------------------------------------------------
+
+def _run(ci, db, ids, replies, instruction="Le trône est occupé par Ysa"):
+    stub, original = _Stub(replies), ci.chat
+    ci.chat = stub
+    try:
+        return ci.interpret(db, ids["world"], "eligibility", instruction, None, []), stub
+    finally:
+        ci.chat = original
+
+
+def _answer(condition, unsupported=()) -> str:
+    return json.dumps({"condition": condition, "unsupported": list(unsupported)}, ensure_ascii=False)
+
+
+def _ml(code, subject="doer", threshold=None, value=None) -> dict:
+    return {"op": "leaf", "form": "attribute", "subject": subject, "target": {"code": code},
+            "threshold": threshold, "value": value}
+
+
+def check_ad3(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine import condition_interpreter as ci
+    from world_engine.conditions import node_to_dict
+
+    with Session(engine) as db:
+        _seed_prompt(db)
+        ctx = ci.build_context(db, ids["world"], "x", None)
+        code = {key: c for c, key in ctx.lists["a"].codes.items()}
+        oui = _choice(db, ids["world"], ids["maudit"], "oui")
+        answer = {"op": "all", "children": [
+            _ml(code[ids["maudit"]], value="OUI"),
+            _ml(code[ids["alerte"]], subject={"name": "Crypte", "kind": "place"}, threshold=3),
+            _ml(code[ids["occupe"]], subject={"name": "Trône de fer", "kind": "object"},
+                value={"name": "Garde Brennar", "kind": "person"}),
+        ]}
+        result, _ = _run(ci, db, ids, [_answer(answer)])
+        want = {"op": "all", "children": [
+            _leafd(target_key=ids["maudit"], value=oui),
+            _leafd(subject_entity_id=ids["crypte"], target_key=ids["alerte"], threshold=3),
+            _leafd(subject_entity_id=ids["trone"], target_key=ids["occupe"], target_entity_id=ids["garde"])]}
+        if result.outcome != "proposed" or node_to_dict(result.tree) != want:
+            fail(f"AD3: {result.outcome}, {node_to_dict(result.tree)}, {result.errors}")
+        bad = {"op": "all", "children": [_ml(code[ids["maudit"]], value="peut-être")]}
+        good = {"op": "all", "children": [_ml(code[ids["maudit"]], value="oui")]}
+        result, stub = _run(ci, db, ids, [_answer(bad), _answer(good)])
+        second = stub.messages[1][1]["content"] if len(stub.messages) == 2 else ""
+        if result.outcome != "proposed" or not result.retried or "libellés : non, oui" not in second:
+            fail(f"AD3: an unknown label gave {result.outcome}, retried {result.retried}")
+        ysa = {"op": "all", "children": [_ml(code[ids["occupe"]], subject={"name": "Trône de fer",
+                                                                             "kind": "object"},
+                                             value={"name": "Ysa", "kind": "person"})]}
+        result, _ = _run(ci, db, ids, [_answer(ysa)])
+        ref = next((m["ref"] for m in result.mentions if m["status"] == "ambiguous"), None)
+        if result.outcome != "needs_choice" or ref is None:
+            fail(f"AD3: an ambiguous entity value gave {result.outcome}")
+        else:
+            done = ci.resolve(db, ids["world"], result.pending, result.mentions, result.notes, {ref: ids["ysa2"]})
+            leaf = node_to_dict(done.tree)["children"][0] if done.tree else {}
+            if done.outcome != "proposed" or leaf.get("target_entity_id") != ids["ysa2"]:
+                fail(f"AD3: the pick gave {done.outcome}, {leaf}")
+        result, _ = _run(ci, db, ids, [_answer(None, [{"text": "la porte est ouverte", "kind": "state"}])])
+        if not any("Création › États" in n for n in result.notes):
+            fail(f"AD3: a missing state gave the notes {result.notes}")
+
+
+# --- AD4 -------------------------------------------------------------------------
+
+def _run_script(db_path: str) -> subprocess.CompletedProcess:
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    return subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True,
+                          cwd=str(ROOT), timeout=120)
+
+
+def _prompt_db(system_prompt: str) -> str:
+    import seed_pilot
+    from sqlalchemy import create_engine
+    from sqlmodel import Session, SQLModel
+
+    from world_engine.models import PromptTemplate
+    from world_engine.writes.prompts import write_prompt_variables, write_prompt_version
+
+    head = dict(seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS[0])
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "prompt.db")
+    eng = create_engine(f"sqlite:///{db_path}")
+    SQLModel.metadata.create_all(eng)
+    with Session(eng) as db:
+        db.add(PromptTemplate(id=head["id"], name=head["name"], usage=head["usage"], world_id=None,
+                              destination=head["destination"]))
+        db.flush()
+        write_prompt_variables(db, template_id=head["id"],
+                               variables=[v for v in head["variables"] if v != "attributes"])
+        write_prompt_version(db, template_id=head["id"], system_prompt=system_prompt,
+                             user_template=seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE_0112, note="seed v1")
+        db.commit()
+    eng.dispose()
+    return db_path
+
+
+def _current(db_path: str):
+    from sqlalchemy import create_engine
+    from sqlmodel import Session
+
+    from world_engine.models import PromptTemplate, PromptVariable
+    from world_engine.prompt_store import current_prompt
+    from sqlmodel import select
+
+    eng = create_engine(f"sqlite:///{db_path}")
+    with Session(eng) as db:
+        head = db.get(PromptTemplate, "pt-condition-interpret")
+        version = current_prompt(db, head)
+        names = set(db.exec(select(PromptVariable.name)).all())
+        state = (version.version_number, version.system_prompt, version.user_template, names)
+    eng.dispose()
+    return state
+
+
+def check_ad4() -> None:
+    import seed_pilot
+
+    db_path = _prompt_db(seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT_0112)
+    result = _run_script(db_path)
+    number, system, user, names = _current(db_path)
+    if result.returncode != 0 or number != 2 or system != seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT \
+            or user != seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE or "attributes" not in names:
+        fail(f"AD4: exit {result.returncode}, v{number}, seed text {system == seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT}"
+             f"/{user == seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE}: {result.stdout.strip()[-200:]}")
+    again = _run_script(db_path)
+    if again.returncode != 0 or "unchanged" not in again.stdout or _current(db_path)[0] != 2:
+        fail(f"AD4: a second run: {again.stdout.strip()[-200:]}")
+    _field, lost, _new = seed_pilot.CONDITION_INTERPRET_FRAGMENTS[0]
+    edited = seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT_0112.replace(lost, "(retouché à la main)")
+    db_path = _prompt_db(edited)
+    result = _run_script(db_path)
+    number, system, user, _names = _current(db_path)
+    if result.returncode != 0 or number != 2 or "fragment not found" not in result.stdout \
+            or "(retouché à la main)" not in system or "{attributes}" not in user:
+        fail(f"AD4: an edited head gave v{number}: {result.stdout.strip()[-300:]}")
+
+
+def main() -> int:
+    _fresh_db()
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    ids = _world(engine)
+    for name, rule in (("AD1", check_ad1), ("AD2", lambda: check_ad2(engine, ids)),
+                       ("AD3", lambda: check_ad3(engine, ids)), ("AD4", check_ad4)):
+        try:
+            rule()
+        except Exception as exc:  # a crash is that rule's failure, never a pass
+            fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: attribute_interpreter -- the interpreter shows the model every attribute by code, writes "
+          "an attribute leaf by label, threshold or name and reads it back, and its prompt is delivered "
+          "fragment by fragment, keeping the creator's edits")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/condition_interpreter.py b/tooling/verify/checks/condition_interpreter.py
index 7cff513..ed2d63b 100644
--- a/tooling/verify/checks/condition_interpreter.py
+++ b/tooling/verify/checks/condition_interpreter.py
@@ -53,7 +53,7 @@ NC1 -- the interpreter's shape (BRIEF-0112-C; static and import).
    order; every form of `CODE_LISTS` is outside `ENTITY_TARGET_TYPES`;
    `UNSUPPORTED_NOTES_FR` covers exactly state, event, time, cost, reward
    and other -- cost names « Coûts », reward « Récompenses », state
-   TICKET-0113, event TICKET-0114; `ROLE_LABELS_FR` covers
+   « Création › États » (TICKET-0113), event TICKET-0114; `ROLE_LABELS_FR` covers
    `CONDITION_ROLES`; `RESOURCE_KEY` equals the editor's `MONEY_KEY`.
    `condition_interpreter.py` calls `chat` nowhere: `_call` is one return
    of `prompt_call.call_json(..., chat)`; it calls none of `add`, `commit`,
@@ -590,7 +590,7 @@ def _nc1_tables() -> None:
         fail(f"NC1: CODE_LISTS is {ci.CODE_LISTS}")
     notes = ci.UNSUPPORTED_NOTES_FR
     if set(notes) != {"state", "event", "time", "cost", "reward", "other"} or "« Coûts »" not in notes["cost"] \
-            or "« Récompenses »" not in notes["reward"] or "TICKET-0113" not in notes["state"] \
+            or "« Récompenses »" not in notes["reward"] or "Création › États" not in notes["state"] \
             or "TICKET-0114" not in notes["event"]:
         fail(f"NC1: UNSUPPORTED_NOTES_FR reads {notes}")
     if set(ci.ROLE_LABELS_FR) != set(CONDITION_ROLES):
@@ -650,7 +650,7 @@ def _value_keys() -> set[str]:
     from world_engine.fact_refs import CodedRefs
 
     empty = CodedRefs(codes={}, lines=())
-    ctx = ci.InterpreterContext(entity_lines=(), lists={k: empty for k in "efqs"}, current=None)
+    ctx = ci.InterpreterContext(entity_lines=(), lists={k: empty for k in "efqsa"}, current=None)
     return set(ci.prompt_values(ctx, "eligibility", "x", []))
 
 
````

2. Regenerate: `python tooling/glue/gen_decisions_index.py`.
3. Regenerate: `python tooling/glue/gen_file_map.py`.
4. Commit as one commit: `BRIEF-0113-D: the interpreter reads the states of the world -- the a list, the attribute leaf, the prompt by fragments`.

## Scope OUT

- Proposing a missing definition (BRIEF-0113-E).
- A new prompt head or registry entry: `condition_interpret` keeps its head (`prompt_registry.py` unchanged).
- Touching Nia's database: the script runs at the live gate, by her.

## Invariants to defend

**A model never emits an id** -- an attribute by its `a` code, a choice by its label read back by code (AD3). **Prompts are data; an edit of hers is kept** -- the script edits the CURRENT version fragment by fragment through `write_prompt_version`, never rewrites it whole; the seed never touches an existing head (S2) (AD4). **Creator surface only** -- the `a` list includes hidden attributes; no player surface reads it.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain (R-21 aside).
- A named mutation does not turn its rule red.
- `prompt_registry.py` turns red (the head's variables and the template's placeholders disagree).
- A fragment's old text is not found in `CONDITION_INTERPRET_*_0112` (the 0112 text moved since): the fragments are this brief's contract.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run; a check that times out under load and passes when rerun alone (name it).
- `lore_usage.py` U12c red between 20:00 and 24:00 Toronto (`--since` from a local date against UTC rows, R-21): pre-existing on `main`; rerun after midnight or name it. Never fixed here.
- The model the prompt runs on: `AUTHOR_MODEL` by default (IJ1), changed by Nia in Prompts.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/attribute_interpreter.py` -> `PASS: attribute_interpreter -- the interpreter shows the model every attribute by code, writes an attribute leaf by label, threshold or name and reads it back, and its prompt is delivered fragment by fragment, keeping the creator's edits`
- `condition_interpreter.py`, `prompt_registry.py`, `attributes.py`, `attribute_conditions.py`, `knowledge_identity.py`, `name_index.py`, `module_budget.py`, `function_length.py`, `file_map.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`attribute_interpreter.py` exits 1 with the rule named):
  - in `src/world_engine/condition_interpreter.py`, `CODE_LISTS: dict[str, str] = {"knowledge": "f", "quest_state": "q", "skill_rank_gte": "s", "attribute": "a"}` -> `CODE_LISTS: dict[str, str] = {"knowledge": "f", "quest_state": "q", "skill_rank_gte": "s"}` -> `AD1`
  - in `src/world_engine/condition_interpreter.py`, `        kind = "choix : " + ", ".join(label for _key, label in view.choices)` -> `        kind = "choix"` -> `AD2`
  - in `src/world_engine/condition_interpreter.py`, `            value = dict(view.choices).get(spec.value, spec.value)` -> `            value = spec.value` -> `AD2`
  - in `src/world_engine/condition_interpreter.py`, `        if value == key or (wanted and normalize_surface(label) == wanted):` -> `        if value == key:` -> `AD3`
  - in `scripts/apply_ticket_0113_condition_prompt.py`, `        if new in out[field]:` -> `        if False:` -> `AD4`
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 150/150 (outside 20:00-24:00 Toronto, R-21).
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

No schema change. Decision entry « THE INTERPRETER READS THE STATES OF THE WORLD (TICKET-0113) -- AN `a` LIST OF CODED ATTRIBUTES, A CHOICE BY ITS LABEL, THE PROMPT DELIVERED FRAGMENT BY FRAGMENT (BRIEF-0113-d, no schema change) » -- in the diff.
