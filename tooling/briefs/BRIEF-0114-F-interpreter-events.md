<!-- slug: interpreter-events -->
# BRIEF 0114-F — "The condition interpreter reads the world's event types and sortes and writes an event leaf -- the `t` list, roles and sortes by name"

Lot: LOT-0114-event-journal.md (authoritative on conflict)
Depends on: BRIEF-0114-E (C-08)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0114-E's commit).

- `src/world_engine/condition_interpreter.py:98` -> `CODE_LISTS: dict[str, str] = {"knowledge": "f", "quest_state": "q", "skill_rank_gte": "s", "attribute": "a"}`
- `src/world_engine/condition_interpreter.py:121` -> `class InterpreterContext:`
- `scripts/seed_pilot.py:2043` -> `CONDITION_INTERPRET_FRAGMENTS: tuple[tuple[str, str, str], ...] = (`
- `scripts/apply_ticket_0113_condition_prompt.py` -> `def apply_fragments(` and `HEAD = seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS[0]`
- No `src/world_engine/interpreter_events.py`, no `scripts/apply_ticket_0114_condition_prompt.py`, no `tooling/verify/checks/event_interpreter.py`.

## Facts carried

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

### R-14 — fifteen seconds per check [M]
Opened: `tooling/verify/checks/corpus_gate.py` (per-check subprocess,
timeout a failure), `.claude/rules/verify-checks.md`.
Consequence: six checks, each measured on the replay: `event_journal.py`
4.8 s, `event_writes.py` 1.9 s, `event_contexts.py` 6.3 s,
`event_conditions.py` 1.4 s, `event_interpreter.py` 4.1 s,
`event_analyzer.py` 6.7 s.

## Contracts

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

## Context

R1: the interpreter sees the world's event types as one more coded list, `t`, each line its roles and what they take, and the sortes by name; it writes the `event` leaf with the type's code, the role by name, the place by name, the window and the filters. Roles and sortes are read back by their normalized name, an unknown one an error naming the right ones (retried once, II1); an ambiguous witness waits for the creator's pick. Three prompt fragments, delivered by a script reusing the 0113 delivery.

## Scope IN

The embedded diff is the prototype's commit for this brief, replayed on a clean `main` and verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `interpreter_events.py` (new, C-09): `event_type_line`, `encode_event`, `read_event`, `filters_waiting`, `bind_filters`;
   - `condition_interpreter.py`: `CODE_LISTS["event"] = "t"`, `InterpreterContext.event_types/sortes`, the `t` list in `build_context`, `encode` and `_leaf` for the event leaf, `waiting`/`bind` for a filter's pick, `_tree` with `since`/`filters`, the prompt values `event_types` and `sortes`, the event note pointing to « Vocabulaire du monde »; `conditions.filters_from` made public;
   - `seed_pilot.py`: three fragments appended to `CONDITION_INTERPRET_FRAGMENTS` (« ÉVÉNEMENTS. », the unsupported `event`, the two lists), the head's variables gain `event_types`, `sortes`; `scripts/apply_ticket_0114_condition_prompt.py` (new: imports `HEAD`, `apply_fragments` from the 0113 script);
   - `checks/condition_interpreter.py` NC1/NC3f follow the note; creates check `event_interpreter.py` (EI1-EI4);
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - scripts/apply_ticket_0114_condition_prompt.py
   - scripts/seed_pilot.py
   - src/world_engine/condition_interpreter.py
   - src/world_engine/conditions.py
   - src/world_engine/interpreter_events.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/condition_interpreter.py
   - tooling/verify/checks/event_interpreter.py

````diff
diff --git a/scripts/apply_ticket_0114_condition_prompt.py b/scripts/apply_ticket_0114_condition_prompt.py
new file mode 100644
index 0000000..cdcae38
--- /dev/null
+++ b/scripts/apply_ticket_0114_condition_prompt.py
@@ -0,0 +1,75 @@
+"""One-shot, idempotent delivery of the TICKET-0114 condition interpreter's
+prompt update onto the live DB (BRIEF-0114-F): the model reads the world's
+event types -- the `t` list, a new variable `event_types` -- and its sortes
+(`sortes`), and writes an `event` leaf.
+
+The same delivery as `apply_ticket_0113_condition_prompt.py`, whose
+`apply_fragments` it imports (never a second copy): the CURRENT version of
+`pt-condition-interpret` is edited fragment by fragment from
+`seed_pilot.CONDITION_INTERPRET_FRAGMENTS`, so an edit the creator made in
+the Prompts tab is kept; a fragment found in neither form is reported, to
+be edited by hand. The head's variables are first set to the seed's.
+
+History is sacred: a changed text lands as a new `prompt_version` row
+through `write_prompt_version`, the old one untouched. Touches nothing else.
+Safe to re-run: an already-updated head prints "unchanged".
+
+Run after `migrate_v2_25_event_columns.py`:
+
+    python scripts/apply_ticket_0114_condition_prompt.py
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
+        "apply_ticket_0114_condition_prompt.py refuses to run unless "
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
+from apply_ticket_0113_condition_prompt import HEAD, apply_fragments  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+from world_engine.models import PromptTemplate  # noqa: E402
+from world_engine.prompt_store import current_prompt  # noqa: E402
+from world_engine.writes import write_prompt_version  # noqa: E402
+from world_engine.writes.prompts import write_prompt_variables  # noqa: E402
+
+NOTE = "TICKET-0114 BRIEF-0114-F -- the interpreter reads the world's event types and sortes"
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
index 32dfb33..eac2142 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -2080,6 +2080,30 @@ CONDITION_INTERPRET_FRAGMENTS: tuple[tuple[str, str, str], ...] = (
     ("user_template",
      "Entités que la phrase nomme :\n{entities}",
      "Types d'entité (clé — nom) :\n{entity_types}\n\nEntités que la phrase nomme :\n{entities}"),
+    # TICKET-0114 (BRIEF-0114-F, R1): the event types (`t`) and the sortes;
+    # the `event` form. Each old text stands once in the 0112 text, touched
+    # by no other fragment.
+    ("system_prompt",
+     "CONNECTEURS. {",
+     "ÉVÉNEMENTS. La forme event compte les événements que le sujet a vécus : \"target\" est le code "
+     "d'un type de la liste des types d'événements {\"code\": \"t1\"} ; \"value\" est le nom du rôle "
+     "que le sujet y tient, ou null pour n'importe lequel ; \"threshold\" est le nombre minimal (les "
+     "quantités s'additionnent ; 1 par défaut) ; \"place\" est le lieu où l'événement a eu lieu, ou ce "
+     "qu'il contient, {\"name\": \"...\", \"kind\": \"place\"}, ou null ; \"since\" vaut \"always\" "
+     "(depuis toujours, par défaut), \"quest\" (depuis l'acceptation de la quête) ou \"step\" (depuis "
+     "le début de l'étape) ; \"with\" précise les autres rôles, chacun tenu par une sorte de la liste "
+     "des sortes {\"role\": \"victime\", \"sorte\": \"Loup\"} ou par une entité {\"role\": "
+     "\"victime\", \"name\": \"Brakk\", \"kind\": \"person\"}. « A tué 3 loups depuis le début de "
+     "l'étape » : {\"op\": \"leaf\", \"form\": \"event\", \"subject\": \"doer\", \"target\": "
+     "{\"code\": \"t1\"}, \"value\": \"tueur\", \"threshold\": 3, \"place\": null, \"since\": "
+     "\"step\", \"with\": [{\"role\": \"victime\", \"sorte\": \"Loup\"}]}.\n\nCONNECTEURS. {"),
+    ("system_prompt",
+     "ce qui s'est passé (\"event\" : tuer, être repéré), ",
+     "un événement qu'aucun type de la liste ne dit (\"event\"), "),
+    ("user_template",
+     "Compétences (code — nom) :\n{skills}",
+     "Compétences (code — nom) :\n{skills}\n\nTypes d'événements (code — nom, rôles) :\n{event_types}"
+     "\n\nSortes :\n{sortes}"),
 )
 
 
@@ -2112,7 +2136,7 @@ CONDITION_INTERPRET_PROMPT_HEADS = (
         system_prompt=CONDITION_INTERPRET_SYSTEM_PROMPT,
         user_template=CONDITION_INTERPRET_USER_TEMPLATE,
         variables=["role", "forms", "entity_types", "entities", "tree_entities", "facts", "offers", "skills",
-                   "attributes", "current", "instruction", "errors"],
+                   "event_types", "sortes", "attributes", "current", "instruction", "errors"],
         destination="local",
     ),
 )
diff --git a/src/world_engine/condition_interpreter.py b/src/world_engine/condition_interpreter.py
index 89d0766..77d9b86 100644
--- a/src/world_engine/condition_interpreter.py
+++ b/src/world_engine/condition_interpreter.py
@@ -6,7 +6,8 @@ The model proposes, code validates, the creator confirms (A1): nothing here
 writes. `interpret` shows the model the language (`form_lines`), the
 entities the instruction names, coded lists of the world's facts (`f`), its
 quest offers (`q`), skills (`s`) and attributes (`a`, TICKET-0113: a state
-by its code, a choice by its label), and -- when the creator edits a
+by its code, a choice by its label), its event types (`t`, TICKET-0114,
+with their roles; its sortes by name -- `interpreter_events`), and -- when the creator edits a
 condition (IC1) -- the current tree in the model's own form, its entities
 coded `e`. The model answers that form (C-03): entities by name (or by an
 `e` code), every other target by code, never an id (ID1a). Code reads the
@@ -48,8 +49,20 @@ from .attribute_proposals import (
 from .attributes import ATTRIBUTE_FORM, AttributeView, world_attributes, world_entity_type_labels
 from .condition_forms import ENTITY_TARGET_TYPES, FORM_VALUES, REQUIREMENT_TYPES, RequirementSpec
 from .condition_text import FORM_PHRASES_FR, VALUE_LABELS_FR
-from .conditions import CONNECTORS, SUBJECT_ROLES, ConditionTree, all_of, check_shape, leaves, node_to_dict
+from .conditions import (
+    CONNECTORS,
+    EVENT_FORM,
+    SUBJECT_ROLES,
+    ConditionTree,
+    all_of,
+    check_shape,
+    filters_from,
+    leaves,
+    node_to_dict,
+)
+from .event_vocab import EventTypeView, world_event_types, world_sortes
 from .fact_refs import CodedRefs, code_facts, code_refs
+from .interpreter_events import bind_filters, encode_event, event_type_line, filters_waiting, read_event
 from .lore_resolve import CATEGORIES, near_candidates, normalize_surface, resolve_named
 from .lore_write_draft import MAX_CODED_FACTS, named_entity_ids, world_fact_ids
 from .models import BASE_SKILL_DOMAINS, Entity, FactParticipant, QuestOffer, SkillDefinition
@@ -92,18 +105,20 @@ TARGET_HINTS_FR: dict[str, str] = {
     "attribute": "un état, par son code a ; pour un choix, valeur = un de ses libellés ; pour un nombre, "
                  "seuil = le minimum ; pour une entité, valeur = une entité par son nom, ou null pour "
                  "« quelqu'un »",
-    "event": "un type d'événement, par son nom ; seuil = le nombre minimal (quantités additionnées)",
+    "event": "un type d'événement, par son code t ; valeur = le rôle du sujet, par son nom, ou null pour "
+             "n'importe lequel ; seuil = le nombre minimal (quantités additionnées) ; et place, since, with",
 }
 # The forms whose target is a code, and the list each code comes from.
-CODE_LISTS: dict[str, str] = {"knowledge": "f", "quest_state": "q", "skill_rank_gte": "s", "attribute": "a"}
+CODE_LISTS: dict[str, str] = {"knowledge": "f", "quest_state": "q", "skill_rank_gte": "s", "attribute": "a",
+                              "event": "t"}
 
 # IF1: what the language cannot say yet, by the kind the model gives it, and
 # where it will come from. IA1: a cost or a reward is a term of the offer.
 UNSUPPORTED_NOTES_FR: dict[str, str] = {
     "state": "« {text} » : cet état n'existe pas encore dans ce monde ; définis-le dans Création › États, "
              "puis redemande.",
-    "event": "« {text} » : ce qui s'est passé (tué, repéré, capturé…) n'est pas encore une "
-             "condition ; il arrive avec le journal d'événements (TICKET-0114).",
+    "event": "« {text} » : aucun type d'événement de ce monde ne le dit encore ; définis-le dans "
+             "Création › Vocabulaire du monde, puis redemande.",
     "time": "« {text} » : le temps (avant le jour N, pendant N tours) n'est pas encore une "
             "condition ; aucun ticket ne l'a encore.",
     "cost": "« {text} » : c'est un coût, pas une condition : ajoute-le dans « Coûts » de l'offre.",
@@ -122,16 +137,18 @@ class InterpreterContext:
     """What the model may see; the coded lists also resolve its answer."""
 
     entity_lines: tuple[str, ...]
-    lists: dict[str, CodedRefs]  # "e", "f", "q", "s", "a"
+    lists: dict[str, CodedRefs]  # "e", "f", "q", "s", "a", "t"
     current: Optional[dict]
     attributes: dict[str, AttributeView] = field(default_factory=dict)  # key -> view, the `a` list's
     type_lines: tuple[str, ...] = ()  # the types a proposed definition may name (BRIEF-0113-E)
+    event_types: dict[str, EventTypeView] = field(default_factory=dict)  # id -> view, the `t` list's (0114)
+    sortes: dict[str, str] = field(default_factory=dict)  # id -> name (TICKET-0114)
 
 
 def _current_ids(tree: Optional[ConditionTree]) -> dict[str, list[str]]:
-    found: dict[str, list[str]] = {"e": [], "f": [], "q": [], "s": [], "a": []}
+    found: dict[str, list[str]] = {"e": [], "f": [], "q": [], "s": [], "a": [], "t": []}
     for spec in leaves(tree):
-        for entity_id in (spec.subject_entity_id, spec.target_entity_id):
+        for entity_id in (spec.subject_entity_id, spec.target_entity_id, *(f.entity_id for f in spec.filters)):
             if entity_id and entity_id not in found["e"]:
                 found["e"].append(entity_id)
         if spec.type in CODE_LISTS and spec.target_key:
@@ -167,17 +184,22 @@ def build_context(db: Session, world_id: str, instruction: str, current: Optiona
     attributes = {view.key: view for view in world_attributes(db, world_id)}
     attributes.update(unsaved_views(unsaved))  # the draft's proposed ones (BRIEF-0113-E)
     types = {t["type"]: t["label"] for t in world_entity_type_labels(db, world_id)}
+    event_types = {view.id: view for view in world_event_types(db, world_id)}
     lists = {
         "e": code_refs("e", ((eid, _entity_label(db, eid)) for eid in ids["e"])),
         "f": code_facts(db, list(dict.fromkeys(fact_ids))[:MAX_CODED_FACTS]),
         "q": code_refs("q", sorted(((o.id, o.title) for o in offers), key=lambda pair: pair[1].lower())),
         "s": code_refs("s", _skill_pairs(db, world_id)),
         "a": code_refs("a", ((key, attribute_line(view, types)) for key, view in attributes.items())),
+        "t": code_refs("t", ((tid, event_type_line(view, types)) for tid, view in event_types.items())),
     }
+    sortes = {s.id: s.name for s in world_sortes(db, world_id)}
     lines = tuple(f"- {_entity_label(db, eid)}" for eid in named)
     return InterpreterContext(entity_lines=lines, lists=lists, attributes=attributes,
                               type_lines=tuple(f"{t} — {label}" for t, label in types.items()),
-                              current=encode(current, lists, attributes) if current is not None else None)
+                              event_types=event_types, sortes=sortes,
+                              current=encode(current, lists, attributes, event_types, sortes)
+                              if current is not None else None)
 
 
 def attribute_line(view: AttributeView, types: dict[str, str]) -> str:
@@ -201,12 +223,15 @@ def _encode_ref(entity_id: Optional[str], lists: dict[str, CodedRefs]) -> Option
     return {"code": lists["e"].code_of(entity_id)} if entity_id else None
 
 
-def encode(tree: ConditionTree, lists: dict[str, CodedRefs], attributes: Optional[dict] = None) -> dict:
+def encode(tree: ConditionTree, lists: dict[str, CodedRefs], attributes: Optional[dict] = None,
+           event_types: Optional[dict] = None, sortes: Optional[dict] = None) -> dict:
     """A clean tree in the model's form: entities by `e` code, facts,
-    offers, skills and attributes by their code; an attribute's choice by
-    its label, its entity value by `e` code (BRIEF-0113-D)."""
+    offers, skills, attributes and event types by their code; an
+    attribute's choice by its label, its entity value by `e` code
+    (BRIEF-0113-D); an event's roles and sortes by name (TICKET-0114)."""
     if tree.op != "leaf":
-        out: dict[str, Any] = {"op": tree.op, "children": [encode(c, lists, attributes) for c in tree.children]}
+        out: dict[str, Any] = {"op": tree.op, "children": [encode(c, lists, attributes, event_types, sortes)
+                                                           for c in tree.children]}
         if tree.op == "at_least":
             out["n"] = tree.n
         return out
@@ -221,9 +246,13 @@ def encode(tree: ConditionTree, lists: dict[str, CodedRefs], attributes: Optiona
             value = dict(view.choices).get(spec.value, spec.value)
         elif view is not None and view.kind == "entity":
             value = _encode_ref(spec.target_entity_id, lists)
-    return {"op": "leaf", "form": spec.type,
-            "subject": spec.subject_role or _encode_ref(spec.subject_entity_id, lists),
-            "target": target, "threshold": spec.threshold, "value": value}
+    out = {"op": "leaf", "form": spec.type,
+           "subject": spec.subject_role or _encode_ref(spec.subject_entity_id, lists),
+           "target": target, "threshold": spec.threshold, "value": value}
+    if spec.type == EVENT_FORM:
+        return encode_event(spec, out, (event_types or {}).get(spec.target_key), sortes or {},
+                            lambda entity_id: _encode_ref(entity_id, lists))
+    return out
 
 
 def form_lines() -> str:
@@ -335,6 +364,9 @@ def _leaf(db: Session, world_id: str, raw: dict, ctx: InterpreterContext, readin
         out["target_key"] = RESOURCE_KEY
     if form == ATTRIBUTE_FORM and out["target_key"] is not None:
         _attribute_value(db, world_id, raw, ctx, reading, where, out)
+    if form == EVENT_FORM:
+        read_event(raw, out, ctx.event_types.get(out["target_key"]), ctx.sortes,
+                   lambda entity, at: _entity(db, world_id, entity, ctx, reading, at), reading.errors, where)
     return {k: v for k, v in out.items() if v is not None or not k.endswith("_mention")}
 
 
@@ -403,7 +435,7 @@ def waiting(pending: Optional[dict]) -> bool:
     if pending is None:
         return False
     if pending.get("op") == "leaf":
-        return "subject_mention" in pending or "target_mention" in pending
+        return "subject_mention" in pending or "target_mention" in pending or filters_waiting(pending)
     return any(waiting(child) for child in pending.get("children", []))
 
 
@@ -414,16 +446,18 @@ def bind(pending: dict, mentions: list[dict], bindings: dict[str, str]) -> dict:
     by_ref = {m["ref"]: m for m in mentions}
     if pending.get("op") != "leaf":
         return {**pending, "children": [bind(c, mentions, bindings) for c in pending.get("children", [])]}
-    out = dict(pending)
-    for side in ("subject", "target"):
-        ref = out.pop(f"{side}_mention", None)
-        if ref is None:
-            continue
+    def picked(ref: str) -> str:
         pick = bindings.get(ref)
         if pick not in {c["entity_id"] for c in by_ref.get(ref, {}).get("choices", [])}:
             raise ValueError(f"« {by_ref.get(ref, {}).get('name', ref)} » : choisis un des noms proposés")
-        out[f"{side}_entity_id"] = pick
-    return out
+        return pick
+
+    out = dict(pending)
+    for side in ("subject", "target"):
+        ref = out.pop(f"{side}_mention", None)
+        if ref is not None:
+            out[f"{side}_entity_id"] = picked(ref)
+    return bind_filters(out, picked)  # an event leaf's filters (TICKET-0114)
 
 
 def _tree(raw: dict) -> ConditionTree:
@@ -431,7 +465,8 @@ def _tree(raw: dict) -> ConditionTree:
         return ConditionTree(op="leaf", leaf=RequirementSpec(
             type=raw["type"], subject_role=raw.get("subject_role"), subject_entity_id=raw.get("subject_entity_id"),
             target_entity_id=raw.get("target_entity_id"), target_key=raw.get("target_key"),
-            threshold=raw.get("threshold"), value=raw.get("value")))
+            threshold=raw.get("threshold"), value=raw.get("value"), since=raw.get("since"),
+            filters=filters_from(raw.get("filters"))))
     return ConditionTree(op=raw["op"], n=raw.get("n"), children=tuple(_tree(c) for c in raw.get("children", [])))
 
 
@@ -504,6 +539,9 @@ def prompt_values(ctx: InterpreterContext, role: str, instruction: str, errors:
         "tree_entities": _lines(ctx.lists["e"].lines), "facts": _lines(ctx.lists["f"].lines),
         "offers": _lines(ctx.lists["q"].lines), "skills": _lines(ctx.lists["s"].lines),
         "attributes": _lines(ctx.lists["a"].lines), "entity_types": _lines(ctx.type_lines),
+        # TICKET-0114 (BRIEF-0114-F): the event types and the sortes.
+        "event_types": _lines(ctx.lists["t"].lines if "t" in ctx.lists else ()),
+        "sortes": ", ".join(ctx.sortes.values()) or "(aucune)",
         "current": json.dumps(ctx.current, ensure_ascii=False) if ctx.current is not None else "(aucune)",
         "instruction": instruction.strip(), "errors": _lines(f"- {e}" for e in errors),
     }
diff --git a/src/world_engine/conditions.py b/src/world_engine/conditions.py
index 802f8cb..ae0bebe 100644
--- a/src/world_engine/conditions.py
+++ b/src/world_engine/conditions.py
@@ -311,7 +311,7 @@ def node_from_dict(raw: object) -> Optional[ConditionTree]:
     return node
 
 
-def _filters_from(raw: object) -> tuple[EventFilter, ...]:
+def filters_from(raw: object) -> tuple[EventFilter, ...]:
     if raw is None or raw == []:
         return ()
     if not isinstance(raw, list) or not all(isinstance(f, dict) for f in raw):
@@ -341,7 +341,7 @@ def _from_dict(raw: object) -> ConditionTree:
             threshold=threshold,
             value=_blank(raw.get("value")),
             since=_blank(raw.get("since")),
-            filters=_filters_from(raw.get("filters")),
+            filters=filters_from(raw.get("filters")),
         )
         return ConditionTree(op="leaf", leaf=spec)
     if op not in CONNECTORS:
diff --git a/src/world_engine/interpreter_events.py b/src/world_engine/interpreter_events.py
new file mode 100644
index 0000000..cfc7276
--- /dev/null
+++ b/src/world_engine/interpreter_events.py
@@ -0,0 +1,136 @@
+"""The condition interpreter's `event` leaves (TICKET-0114, BRIEF-0114-F;
+decision R1 of the conditions series).
+
+The model reads the world's event types as a coded list (`t`), each with
+its roles, and its sortes by name; it writes an `event` leaf with the
+type's code as `target`, the subject's role by name as `value` (null: any),
+a `place` named like any entity, a window `since` and, in `with`, the other
+roles each filled by a sorte (by name) or an entity (by name). Code reads
+it back here: a role or a sorte by its normalized name, an unknown one an
+error listing the right ones; an entity through the interpreter's own
+resolver (`resolve_entity`), so an ambiguous name waits for the creator's
+pick like any other -- a filter's pick is kept as `entity_mention` until
+`bind_filters`.
+
+- `event_type_line(view, types)` : one type as the `t` list shows it.
+- `encode_event(spec, out, ...)` : a clean event leaf in the model's form.
+- `read_event(raw, out, ...)`    : the model's event leaf read back.
+- `filters_waiting(leaf)`        : a filter still waits for a pick.
+- `bind_filters(leaf, ...)`      : the creator's picks applied.
+
+Writes nothing.
+"""
+
+from __future__ import annotations
+
+from typing import Any, Callable, Optional
+
+from .event_vocab import EventTypeView
+from .lore_resolve import normalize_surface
+from .models import CONDITION_WINDOWS
+
+# The model's `since`, by the value the language stores (F1).
+EVENT_WINDOW_DEFAULT = "always"
+
+
+def event_type_line(view: EventTypeView, types: dict[str, str]) -> str:
+    """« Tuer (rôles : tueur — personnage ; victime — personnage ou une
+    sorte ; compte une quantité) »: what the model needs to write a leaf."""
+    roles = []
+    for role in view.active_roles():
+        takes = [types.get(t, t).lower() for t in role.entity_types]
+        if role.accepts_sorte:
+            takes.append("une sorte")
+        roles.append(f"{role.name} — {' ou '.join(takes) or 'rien'}")
+    quantity = " ; compte une quantité" if view.counts_quantity else ""
+    return f"{view.name} (rôles : {' ; '.join(roles) or 'aucun'}{quantity})"
+
+
+def _role_by_name(view: EventTypeView, name: Any):
+    wanted = normalize_surface(str(name or ""))
+    return next((r for r in view.active_roles() if wanted and normalize_surface(r.name) == wanted), None)
+
+
+def _role_names(view: EventTypeView) -> str:
+    return ", ".join(r.name for r in view.active_roles()) or "aucun"
+
+
+def encode_event(spec, out: dict, view: Optional[EventTypeView], sortes: dict[str, str],
+                 encode_ref: Callable[[Optional[str]], Optional[dict]]) -> dict:
+    """`out` (the generic leaf, its `target` the type's code) completed: the
+    role by name, the place, the window and the filters by role name."""
+    names = {r.id: r.name for r in view.roles} if view is not None else {}
+    out["value"] = names.get(spec.value, spec.value) if spec.value else None
+    out["place"] = encode_ref(spec.target_entity_id)
+    out["since"] = spec.since or EVENT_WINDOW_DEFAULT
+    out["with"] = [{"role": names.get(f.role_id, f.role_id),
+                    **({"sorte": sortes.get(f.sorte_id, f.sorte_id)} if f.sorte_id else encode_ref(f.entity_id) or {})}
+                   for f in spec.filters]
+    return out
+
+
+ResolveEntity = Callable[[Any, str], tuple[Optional[str], Optional[str]]]
+
+
+def read_event(raw: dict, out: dict, view: Optional[EventTypeView], sortes: dict[str, str],
+               resolve_entity: ResolveEntity, errors: list[str], where: str) -> None:
+    """The rest of an `event` leaf, read into `out` (the generic leaf, its
+    `target_key` the type's id or None): `value` a role's id, the place
+    (`target_entity_id`, or `target_mention` while a pick waits), `since`
+    and `filters`. Every problem is appended to `errors`."""
+    out["since"] = raw.get("since") or EVENT_WINDOW_DEFAULT
+    if out["since"] not in CONDITION_WINDOWS:
+        errors.append(f"{where}fenêtre inconnue {out['since']!r} (attendu : {', '.join(CONDITION_WINDOWS)})")
+    out["value"], out["filters"] = None, []
+    place = raw.get("place")
+    if isinstance(place, str):
+        place = {"name": place, "kind": "place"}
+    if place:
+        out["target_entity_id"], out["target_mention"] = resolve_entity(place, where)
+    if view is None:
+        return
+    if raw.get("value") not in (None, ""):
+        role = _role_by_name(view, raw["value"])
+        if role is None:
+            errors.append(f"{where}« {raw['value']} » n'est pas un rôle de « {view.name} » "
+                          f"(rôles : {_role_names(view)})")
+        else:
+            out["value"] = role.id
+    by_name = {normalize_surface(name): sid for sid, name in sortes.items()}
+    for item in raw.get("with") if isinstance(raw.get("with"), list) else []:
+        role = _role_by_name(view, item.get("role")) if isinstance(item, dict) else None
+        if role is None:
+            errors.append(f"{where}« {item.get('role') if isinstance(item, dict) else item} » n'est pas un rôle "
+                          f"de « {view.name} » (rôles : {_role_names(view)})")
+            continue
+        entry: dict[str, Any] = {"role_id": role.id, "entity_id": None, "sorte_id": None}
+        if item.get("sorte") is not None:
+            entry["sorte_id"] = by_name.get(normalize_surface(str(item["sorte"])))
+            if entry["sorte_id"] is None:
+                known = ", ".join(sortes.values()) or "aucune"
+                errors.append(f"{where}« {item['sorte']} » n'est pas une sorte de ce monde (sortes : {known})")
+                continue
+        else:
+            entity = {k: item[k] for k in ("name", "kind", "code") if k in item}
+            entry["entity_id"], mention = resolve_entity(entity, where)
+            if mention is not None:
+                entry["entity_mention"] = mention
+        out["filters"].append(entry)
+
+
+def filters_waiting(leaf: dict) -> bool:
+    return any("entity_mention" in f for f in leaf.get("filters") or [])
+
+
+def bind_filters(leaf: dict, pick: Callable[[str], str]) -> dict:
+    """`leaf` with each filter's waiting name replaced by `pick(ref)`."""
+    if not leaf.get("filters"):
+        return leaf
+    filters = []
+    for f in leaf["filters"]:
+        f = dict(f)
+        ref = f.pop("entity_mention", None)
+        if ref is not None:
+            f["entity_id"] = pick(ref)
+        filters.append(f)
+    return {**leaf, "filters": filters}
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 49c32ce..00e6610 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -19411,6 +19411,27 @@ step has a « Échouée quand » editor. A non-event leaf's dict is unchanged:
 **Rejected.** A window on every form (only events have dates), a failure
 that closes the quest by itself (the creator stays the judge, as M1).
 
+## THE CONDITION INTERPRETER READS THE WORLD'S EVENT TYPES AND WRITES AN EVENT LEAF (TICKET-0114) -- THE `t` LIST (BRIEF-0114-f, no schema change)
+
+**R1, reading.** The model sees the world's active event types as a coded
+list `t`, each line its roles, what each takes (entity types, « une
+sorte ») and whether it counts a quantity; the sortes by name. It writes an
+`event` leaf with the type's code, the subject's role by NAME (null: any),
+a `place` named like any entity, `since` and, in `with`, each other role
+filled by a sorte or an entity, both by name. Code reads it back
+(`interpreter_events.py`): a role or a sorte by its normalized name -- an
+unknown one is an error naming the right ones, sent back to the model once
+(II1) --, an entity through the interpreter's resolver, so an ambiguous
+witness waits for the creator's pick like any name. Roles and sortes are
+read by name, not code: the lists are short, the names are the creator's
+words, and the type's code already scopes the roles.
+
+**Prompt.** Three fragments of `CONDITION_INTERPRET_FRAGMENTS` (the
+paragraph « ÉVÉNEMENTS. », the two lists in the message, « event » no
+longer unsupported when a type says it), delivered by
+`apply_ticket_0114_condition_prompt.py`, which reuses the 0113 delivery.
+What no type says stays a note pointing to « Vocabulaire du monde ».
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/condition_interpreter.py b/tooling/verify/checks/condition_interpreter.py
index 71cad02..bd4f84a 100644
--- a/tooling/verify/checks/condition_interpreter.py
+++ b/tooling/verify/checks/condition_interpreter.py
@@ -53,7 +53,8 @@ NC1 -- the interpreter's shape (BRIEF-0112-C; static and import).
    order; every form of `CODE_LISTS` is outside `ENTITY_TARGET_TYPES`;
    `UNSUPPORTED_NOTES_FR` covers exactly state, event, time, cost, reward
    and other -- cost names « Coûts », reward « Récompenses », state
-   « Création › États » (TICKET-0113), event TICKET-0114; `ROLE_LABELS_FR` covers
+   « Création › États » (TICKET-0113), event « Vocabulaire du monde »
+   (TICKET-0114); `ROLE_LABELS_FR` covers
    `CONDITION_ROLES`; `RESOURCE_KEY` equals the editor's `MONEY_KEY`.
    `condition_interpreter.py` calls `chat` nowhere: `_call` is one return
    of `prompt_call.call_json(..., chat)`; it calls none of `add`, `commit`,
@@ -83,7 +84,7 @@ NC3 -- interpretation (fixture, `condition_interpreter.chat` stubbed).
    e. a name two characters carry -> `needs_choice` with both; `resolve`
       with one -> `proposed` on it; with a third id -> `ValueError`;
    f. a cost only -> `refused`, the « Coûts » note, no error; a condition
-      and an event -> `proposed` with the TICKET-0114 note;
+      and an event -> `proposed` with the « Vocabulaire du monde » note;
    g. `OllamaError` and an unparsable reply propagate;
    h. a current tree reaches the message in the model's form.
 NC4 -- the interpreter writes nothing (fixture). Across NC3, the counts of
@@ -593,7 +594,7 @@ def _nc1_tables() -> None:
     notes = ci.UNSUPPORTED_NOTES_FR
     if set(notes) != {"state", "event", "time", "cost", "reward", "other"} or "« Coûts »" not in notes["cost"] \
             or "« Récompenses »" not in notes["reward"] or "Création › États" not in notes["state"] \
-            or "TICKET-0114" not in notes["event"]:
+            or "Vocabulaire du monde" not in notes["event"]:
         fail(f"NC1: UNSUPPORTED_NOTES_FR reads {notes}")
     if set(ci.ROLE_LABELS_FR) != set(CONDITION_ROLES):
         fail("NC1: ROLE_LABELS_FR does not cover CONDITION_ROLES")
@@ -853,7 +854,7 @@ def _nc3_unsupported(ci, session, ids) -> None:
     if result.outcome != "refused" or result.errors or not any("« Coûts »" in n for n in result.notes):
         fail(f"NC3f: a cost only gave {result.outcome}, {result.errors}, {result.notes}")
     result, _, _ = _run(ci, session, ids, [_answer(FURS, [{"text": "sans être repéré", "kind": "event"}])])
-    if result.outcome != "proposed" or not any("TICKET-0114" in n for n in result.notes):
+    if result.outcome != "proposed" or not any("Vocabulaire du monde" in n for n in result.notes):
         fail(f"NC3f: a condition and an event gave {result.outcome}, {result.notes}")
 
 
diff --git a/tooling/verify/checks/event_interpreter.py b/tooling/verify/checks/event_interpreter.py
new file mode 100644
index 0000000..08afded
--- /dev/null
+++ b/tooling/verify/checks/event_interpreter.py
@@ -0,0 +1,326 @@
+"""G1 check for TICKET-0114 -- the condition interpreter reads the world's event types and sortes and writes an event leaf.
+
+BRIEF-0114-F's rules.
+
+EI1 -- the prompt (static and import). `CODE_LISTS["event"]` is `t`; the
+   head declares `event_types` and `sortes`, its template uses exactly its
+   variables and `prompt_values` gives exactly those; the seed's system
+   prompt holds the « ÉVÉNEMENTS. » paragraph and no longer calls « ce qui
+   s'est passé » unsupported; the event note names « Vocabulaire du monde »;
+   `apply_ticket_0114_condition_prompt.py` imports `apply_fragments` from
+   the 0113 script and embeds no prompt text.
+EI2 -- context and round trip (fixture). The `t` list shows each active
+   type with its roles, what each takes and whether it counts a quantity;
+   the prompt's `sortes` names the world's sortes. A current tree holding
+   an event leaf -- a role, a place, `since` step, a sorte filter and an
+   entity filter -- encodes with the role and the sorte by name, the place
+   and the entity by `e` code, and reads back (`read_answer`, `validate`)
+   to the same tree.
+EI3 -- reading (fixture). An unknown role, an unknown sorte and an unknown
+   window are each an error naming the right ones; a filter naming an
+   ambiguous person waits (`needs_choice`) and the creator's pick binds it.
+EI4 -- interpret and delivery (fixture, stubbed model). A model answer
+   with an event leaf is `proposed` as the tree it says, the message
+   carrying the `t` list. On a head holding the 0113 text and variables,
+   the delivery script writes one new version equal to the seed's, its
+   variables the seed's; a second run is unchanged.
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
+SCRIPT = ROOT / "scripts" / "apply_ticket_0114_condition_prompt.py"
+EVENT_FRAGMENT_MARKS = ("ÉVÉNEMENTS.", "{event_types}", "qu'aucun type de la liste")
+
+FAILURES: list[str] = []
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _fresh_db() -> None:
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
+    sys.path.insert(0, str(ROOT / "scripts"))
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
+# --- EI1 -----------------------------------------------------------------------
+
+def check_ei1() -> None:
+    import seed_pilot
+
+    from world_engine import condition_interpreter as ci
+    from world_engine.fact_refs import CodedRefs
+
+    if ci.CODE_LISTS.get("event") != "t":
+        fail(f"EI1: CODE_LISTS is {ci.CODE_LISTS}")
+    head = seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS[0]
+    used = set(re.findall(r"\{([a-z_]+)\}", head["user_template"]))
+    empty = CodedRefs(codes={}, lines=())
+    keys = set(ci.prompt_values(ci.InterpreterContext(entity_lines=(), lists={k: empty for k in "efqsat"},
+                                                      current=None), "eligibility", "x", []))
+    if not {"event_types", "sortes"} <= used or used != set(head["variables"]) or used != keys:
+        fail(f"EI1: variables {sorted(head['variables'])}, template {sorted(used)}, values {sorted(keys)}")
+    system = seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT
+    if "ÉVÉNEMENTS. La forme event" not in system or "ce qui s'est passé" in system:
+        fail("EI1: the seed's system prompt does not teach the event form, or still calls it unsupported")
+    if "Vocabulaire du monde" not in ci.UNSUPPORTED_NOTES_FR["event"]:
+        fail(f"EI1: the event note reads {ci.UNSUPPORTED_NOTES_FR['event']!r}")
+    script = SCRIPT.read_text(encoding="utf-8") if SCRIPT.exists() else ""
+    if "from apply_ticket_0113_condition_prompt import HEAD, apply_fragments" not in script \
+            or "Tu " in script or "ÉVÉNEMENTS." in script:
+        fail("EI1: the delivery script does not reuse the 0113 delivery, or embeds prompt text")
+
+
+# --- fixture -------------------------------------------------------------------
+
+def _world(engine) -> dict:
+    import seed_pilot
+    from sqlmodel import Session
+
+    from world_engine.event_vocab import type_view
+    from world_engine.models import Character, Entity, Location, PromptTemplate, World
+    from world_engine.writes.event_types import EventTypeSpec, RoleSpec, write_event_type, write_sorte
+
+    with Session(engine) as db:
+        world = World(name="Interprète EI", is_active=False)
+        db.add(world)
+        db.flush()
+        ids = {"world": world.id}
+        for key, kind, name in (("foret", "location", "Forêt"), ("brakk", "character", "Brakk"),
+                                ("ysa1", "character", "Ysa"), ("ysa2", "character", "Ysa")):
+            row = Entity(world_id=world.id, type=kind, name=name)
+            db.add(row)
+            db.flush()
+            ids[key] = row.id
+            db.add(Location(id=row.id) if kind == "location" else Character(id=row.id, world_id=world.id,
+                                                                            character_type="npc"))
+        ids["loup"] = write_sorte(db, world_id=world.id, name="Loup").id
+        ids["ours"] = write_sorte(db, world_id=world.id, name="Ours").id
+        chasse = write_event_type(db, world_id=world.id, spec=EventTypeSpec(
+            name="Chasse", counts_quantity=True,
+            roles=(RoleSpec("Chasseur", ("character",)), RoleSpec("Proie", ("character",), accepts_sorte=True),
+                   RoleSpec("Témoin", ("character",)))))
+        ids["chasse"] = chasse.id
+        view = type_view(db, chasse.id)
+        ids["chasseur"], ids["proie"], ids["temoin"] = (r.id for r in view.roles)
+        for head in seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS:
+            if db.get(PromptTemplate, head["id"]) is None:
+                seed_pilot.upsert_prompt_template(db, **dict(head))
+        db.commit()
+    return ids
+
+
+def _leaf(ids: dict, **kw) -> dict:
+    base = {"op": "leaf", "type": "event", "subject_role": "doer", "subject_entity_id": None,
+            "target_entity_id": ids["foret"], "target_key": ids["chasse"], "threshold": 3,
+            "value": ids["chasseur"], "since": "step",
+            "filters": [{"role_id": ids["proie"], "entity_id": None, "sorte_id": ids["loup"]},
+                        {"role_id": ids["temoin"], "entity_id": ids["brakk"], "sorte_id": None}]}
+    base.update(kw)
+    return base
+
+
+def _model_leaf(**kw) -> dict:
+    base = {"op": "leaf", "form": "event", "subject": "doer", "target": {"code": "t1"}, "value": "chasseur",
+            "threshold": 3, "place": {"name": "Forêt", "kind": "place"}, "since": "step",
+            "with": [{"role": "proie", "sorte": "loup"}, {"role": "Témoin", "name": "Brakk", "kind": "person"}]}
+    base.update(kw)
+    return base
+
+
+# --- EI2 -----------------------------------------------------------------------
+
+def check_ei2(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine import condition_interpreter as ci
+    from world_engine.conditions import node_from_dict, node_to_dict
+
+    with Session(engine) as db:
+        tree = node_from_dict({"op": "all", "children": [_leaf(ids)]})
+        ctx = ci.build_context(db, ids["world"], "Il a chassé", tree)
+        lines = " | ".join(ctx.lists["t"].lines)
+        want = "t1 — Chasse (rôles : Chasseur — personnage ; Proie — personnage ou une sorte ; Témoin — " \
+               "personnage ; compte une quantité)"
+        if want not in lines:
+            fail(f"EI2: the t list reads {lines!r}")
+        if ci.prompt_values(ctx, "completion", "x", [])["sortes"] != "Loup, Ours":
+            fail(f"EI2: sortes reads {ci.prompt_values(ctx, 'completion', 'x', [])['sortes']!r}")
+        leaf = ctx.current["children"][0] if ctx.current else {}
+        if leaf.get("value") != "Chasseur" or leaf.get("since") != "step" or leaf.get("target") != {"code": "t1"} \
+                or leaf.get("with", [{}])[0] != {"role": "Proie", "sorte": "Loup"} \
+                or "code" not in (leaf.get("with") or [{}, {}])[1] or "code" not in (leaf.get("place") or {}):
+            fail(f"EI2: the leaf encodes as {leaf}")
+        reading = ci.read_answer(db, ids["world"], ctx.current, ctx)
+        back, errors = ci.validate(db, ids["world"], reading.pending) if not reading.errors \
+            else (None, reading.errors)
+        if errors or node_to_dict(back) != node_to_dict(tree):
+            fail(f"EI2: the tree reads back as {node_to_dict(back)} ({errors})")
+
+
+# --- EI3 -----------------------------------------------------------------------
+
+def check_ei3(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine import condition_interpreter as ci
+    from world_engine.conditions import node_to_dict
+
+    with Session(engine) as db:
+        ctx = ci.build_context(db, ids["world"], "x", None)
+        for what, raw, needle in (
+            ("an unknown role", _model_leaf(value="pisteur"), "rôles : Chasseur, Proie, Témoin"),
+            ("an unknown sorte", _model_leaf(**{"with": [{"role": "proie", "sorte": "dragon"}]}),
+             "sortes : Loup, Ours"),
+            ("an unknown window", _model_leaf(since="jadis"), "fenêtre inconnue"),
+        ):
+            reading = ci.read_answer(db, ids["world"], {"op": "all", "children": [raw]}, ctx)
+            if not any(needle in e for e in reading.errors):
+                fail(f"EI3: {what} gave {reading.errors}")
+        raw = _model_leaf(**{"with": [{"role": "témoin", "name": "Ysa", "kind": "person"}]})
+        stub, original = _Stub([{"condition": {"op": "all", "children": [raw]}, "unsupported": []}]), ci.chat
+        ci.chat = stub
+        try:
+            result = ci.interpret(db, ids["world"], "completion", "Ysa l'a vu", None, [])
+        finally:
+            ci.chat = original
+        ysa = next((m for m in result.mentions if m["name"] == "Ysa"), None)
+        if result.outcome != "needs_choice" or ysa is None or ysa["status"] != "ambiguous":
+            fail(f"EI3: an ambiguous witness gave {result.outcome}, {result.mentions}")
+            return
+        bound = ci.resolve(db, ids["world"], result.pending, result.mentions, [], {ysa["ref"]: ids["ysa2"]})
+        leaf = node_to_dict(bound.tree)["children"][0] if bound.tree else {}
+        if bound.outcome != "proposed" or leaf.get("filters") != [
+                {"role_id": ids["temoin"], "entity_id": ids["ysa2"], "sorte_id": None}]:
+            fail(f"EI3: the pick gave {bound.outcome}, {leaf}, {bound.errors}")
+
+
+# --- EI4 -----------------------------------------------------------------------
+
+def check_ei4(engine, ids: dict) -> None:
+    from sqlmodel import Session
+
+    from world_engine import condition_interpreter as ci
+    from world_engine.conditions import node_to_dict
+
+    with Session(engine) as db:
+        stub, original = _Stub([{"condition": {"op": "all", "children": [_model_leaf()]},
+                                 "unsupported": []}]), ci.chat
+        ci.chat = stub
+        try:
+            result = ci.interpret(db, ids["world"], "completion", "A chassé 3 loups devant Brakk", None, [])
+        finally:
+            ci.chat = original
+        got = node_to_dict(result.tree)
+        if result.outcome != "proposed" or got != {"op": "all", "children": [_leaf(ids)]}:
+            fail(f"EI4: interpret gave {result.outcome}, {got}, {result.errors}")
+        sent = json.dumps(stub.messages, ensure_ascii=False)
+        if "t1 — Chasse" not in sent or "Loup, Ours" not in sent:
+            fail("EI4: the message does not carry the t list and the sortes")
+    _check_delivery()
+
+
+def _prompt_db() -> str:
+    import seed_pilot
+    from sqlalchemy import create_engine
+    from sqlmodel import Session, SQLModel
+
+    from world_engine.models import PromptTemplate
+    from world_engine.writes.prompts import write_prompt_variables, write_prompt_version
+
+    head = seed_pilot.CONDITION_INTERPRET_PROMPT_HEADS[0]
+    texts = {"system_prompt": seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT_0112,
+             "user_template": seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE_0112}
+    for field, old, new in seed_pilot.CONDITION_INTERPRET_FRAGMENTS:
+        if not any(mark in new for mark in EVENT_FRAGMENT_MARKS):
+            texts[field] = texts[field].replace(old, new)
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "prompt.db")
+    eng = create_engine(f"sqlite:///{db_path}")
+    SQLModel.metadata.create_all(eng)
+    with Session(eng) as db:
+        db.add(PromptTemplate(id=head["id"], name=head["name"], usage=head["usage"], world_id=None,
+                              destination=head["destination"]))
+        db.flush()
+        write_prompt_variables(db, template_id=head["id"], variables=[
+            v for v in head["variables"] if v not in ("event_types", "sortes")])
+        write_prompt_version(db, template_id=head["id"], note="0113", **texts)
+        db.commit()
+    eng.dispose()
+    return db_path
+
+
+def _check_delivery() -> None:
+    import seed_pilot
+    from sqlalchemy import create_engine
+    from sqlmodel import Session, select
+
+    from world_engine.models import PromptTemplate, PromptVariable
+    from world_engine.prompt_store import current_prompt
+
+    db_path = _prompt_db()
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    runs = [subprocess.run([sys.executable, str(SCRIPT)], env=env, capture_output=True, text=True,
+                           cwd=str(ROOT), timeout=60) for _ in range(2)]
+    eng = create_engine(f"sqlite:///{db_path}")
+    with Session(eng) as db:
+        version = current_prompt(db, db.get(PromptTemplate, "pt-condition-interpret"))
+        names = set(db.exec(select(PromptVariable.name)).all())
+        state = (version.version_number, version.system_prompt, version.user_template)
+    eng.dispose()
+    if runs[0].returncode != 0 or state != (2, seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT,
+                                            seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE) \
+            or not {"event_types", "sortes"} <= names:
+        fail(f"EI4: the delivery gave v{state[0]}, seed text {state[1:] == (seed_pilot.CONDITION_INTERPRET_SYSTEM_PROMPT, seed_pilot.CONDITION_INTERPRET_USER_TEMPLATE)}: "
+             f"{runs[0].stdout.strip()[-200:]} {runs[0].stderr.strip()[-200:]}")
+    if runs[1].returncode != 0 or "unchanged" not in runs[1].stdout:
+        fail(f"EI4: a second run: {runs[1].stdout.strip()[-200:]}")
+
+
+def main() -> int:
+    _fresh_db()
+    from world_engine.db import create_db_and_tables, engine
+
+    create_db_and_tables()
+    check_ei1()
+    ids = _world(engine)
+    for check in (check_ei2, check_ei3, check_ei4):
+        try:
+            check(engine, ids)
+        except Exception as exc:  # a crash is a failure, never a pass
+            fail(f"{check.__name__}: crashed: {type(exc).__name__}: {exc}")
+    for msg in FAILURES:
+        print(f"FAIL: {msg}")
+    if FAILURES:
+        return 1
+    print("PASS: event_interpreter -- the interpreter shows the model the world's event types with their roles "
+          "and its sortes, writes an event leaf by role, place, window and filters and reads it back, waits for "
+          "a pick on an ambiguous name, and its prompt is delivered fragment by fragment")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
````

2. Deliver the prompt on Nia's database after the merge: `python scripts/apply_ticket_0114_condition_prompt.py` (after `migrate_v2_25_event_columns.py`).
3. Regenerate the module map and the decisions index: `python tooling/glue/gen_file_map.py`, `python tooling/glue/gen_decisions_index.py`.
4. Run the checks below, then the full corpus.

## Scope OUT

- Proposing a missing type or sorte -- G (this brief's model answer may only name what exists).
- Play's analyzer -- H.
- Every later brief of this lot: BRIEF-0114-G, BRIEF-0114-H.

## Invariants to defend

INV-19 (`prompt_registry.py`): no new prompt usage; the template is the same head. INV-48 (`prompt_version.py`): the delivery appends a version, never edits one. INV-01: the creator-only facts stay visible to the interpreter, a creator surface (IE1) -- nothing here reaches a player.

## Decision rights

STOP:
- `attribute_interpreter.py` AD1 or AD4 fails on the new fragments: a fragment touches another's text.
- A Mini-RECON anchor that does not hold.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- A check other than this brief's own fails on a line count or a docstring count this diff moved (`file_map.py`, `decisions_index.py`): regenerate `FILE_MAP.md` / `DECISIONS_INDEX.md` and rerun.

REPORT-ONLY:
- Svelte a11y warnings during a build (pre-existing), npm's `EBADENGINE` notice.
- Log lines a check prints before its verdict (`[skip] …`, `[overhearing] …`): the analyzer's own logging.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`, `tooling/standards/FILE_MAP.md`.
- `python tooling/verify/checks/event_interpreter.py` -> `PASS`.
- `python tooling/verify/checks/condition_interpreter.py` -> `PASS`.
- `python tooling/verify/checks/attribute_interpreter.py` -> `PASS`.
- `python tooling/verify/checks/event_conditions.py` -> `PASS`.
- `python tooling/verify/checks/corpus_gate.py` -> every check passes (155 on the prototype).
- Each named mutation below, applied alone, turns its check red on its rule, then is reverted:
  - **EI1** -- `condition_interpreter.py` `UNSUPPORTED_NOTES_FR["event"]`: « définis-le dans Création › Vocabulaire du monde » -> « définis-le d'abord »
  - **EI2** -- `interpreter_events.py` `event_type_line`: `if role.accepts_sorte:` -> `if False:`; or `encode_event`: `out["since"] = spec.since or …` -> `out["since"] = EVENT_WINDOW_DEFAULT`
  - **EI3** -- `condition_interpreter.py` `bind`: `return bind_filters(out, picked)` -> `return out`
  - **EI4** -- `apply_ticket_0114_condition_prompt.py`: its `write_prompt_variables(…)` line -> `pass`
- `/review-step` then `/close-step`, in the same turn.

## Docs to update

ARCHITECTURE_DECISIONS (in the diff); FILE_MAP and DECISIONS_INDEX regenerated.
