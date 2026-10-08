<!-- slug: condition-tree -->
# BRIEF 0111-B — "A condition is a tree of four connectors over the forms; each leaf names its subject; a verdict has three states"

Lot: LOT-0111-condition-language.md (authoritative on conflict)
Depends on: BRIEF-0111-A

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0111-A's commit).

- `src/world_engine/condition_forms.py:85` -> `class RequirementSpec:`
- `src/world_engine/condition_forms.py:94` -> `class Verdict:`
- `src/world_engine/condition_forms.py:316` -> `_EVALUATORS: dict[str, Callable[[RequirementSpec, Character, Session, object], Verdict]] = {`
- `src/world_engine/condition_forms.py:330` -> `def _day_reachable_ids(origin_location_id: str, db: Session) -> frozenset[str]:`
- `tooling/verify/checks/conditions.py:67` -> `def check_ca1() -> None:`
- `tooling/verify/checks/knowledge_identity.py:33` -> ``subject` parameter), counted per file, equal `_SUBJECT_CENSUS` exactly.`
- `CLAUDE.md:461` -> `│   ├── day_plan.py, condition_forms.py  # day-plan emission + budget cut; requirement forms, BFS`
- No `src/world_engine/conditions.py` exists.
- No `src/world_engine/condition_text.py` exists.

## Facts carried

### R-01 — the requirement vocabulary: ten forms, four for the model, three shape groups [M]
Opened: `src/world_engine/day_plan.py:87-104` (`REQUIREMENT_TYPES`, ten
forms; `MODEL_REQUIREMENT_TYPES` `:96`, the model's four;
`ENTITY_TARGET_TYPES` `:100`, `KEY_TARGET_TYPES` `:103`, `THRESHOLD_TYPES`
`:104`), `:375-386` (`_EVALUATORS`, one evaluator per form, uniform
signature `(req, character, db, reachable_ids) -> Verdict`), `:585-602`
(`_validate_requirement`: the model's parser refuses any form outside its
four).
Finding: a form is a name, a target kind (entity or key), an optional
threshold, an evaluator judging ONE character, and a French detail
(`day_resolve._BLOCKED_DETAIL_FR`, R-12). Every evaluator takes the judged
character as a parameter: none reads « the player » by itself.
Consequence: a leaf can judge any character (P1) without touching an
evaluator; the model keeps its four forms (I1: its plans become `all` of
them).

### R-07 — evaluation judges one character and returns a flat list [M]
Opened: `src/world_engine/day_plan.py:150-158` (`EvaluatedStep(step,
verdicts)`, `met` = all), `:419-440` (`evaluate_specs`: one reachable set
per call, only when a `location_reachable` is present), `:443-471`;
`src/world_engine/cockpit/routes/day.py:552-576` (`_finalize_plan`:
anchoring, then `EvaluatedStep(step=step, verdicts=tuple(evaluate_requirements(step,
character, db)))` `:558`, the blocked text `:575`); `src/world_engine/day_resolve.py:220,315`
(`canon_ids` from `evaluated.step.requirements`), `:248,324`
(`requirement_verdicts=evaluated.verdicts`).
Finding: consumers read `EvaluatedStep.met`, `.verdicts` (a tuple of
`Verdict`) and `.step.requirements`.
Consequence: C-07 keeps `met` and `verdicts` (the judged leaves, as a
property) so the narration and the budget cut read the same names; the
requirements list becomes `prerequisite`, a tree.

### R-21 — the CLAUDE.md file tree has no room for a new line [M]
Opened: `CLAUDE.md:461` (`day_plan.py # … requirement evaluators, its own
BFS`); `tooling/verify/checks/claude_md_contract.py` (File structure at
most 80 lines -- it is at 80; 100 characters per line; 38 000 characters).
Consequence: A and B fold the new modules into `day_plan.py`'s line
(`day_plan.py, condition*.py`), within 100 characters.

### R-22 — the subject census counts `subject=` keywords [M]
Opened: `tooling/verify/checks/knowledge_identity.py:31-35,109-116,833-838`
(K3: `.subject`, `"subject"`, `subject=` and a `subject` parameter, counted
per file, equal to `_SUBJECT_CENSUS`).
Consequence: the French phrases fill `{who}`, never `subject=`; the leaf's
fields are `subject_role` and `subject_entity_id` (no census change).

### Case tables

b-1 -- three-valued connectors (C-04). `need`: all = every child, any = 1,
at_least = n. met >= need -> met; met + unknown < need -> unmet; else
unknown. `not` swaps met and unmet, keeps unknown.

| children (2)        | all     | any     | at_least 1 | at_least 2 |
|---------------------|---------|---------|------------|------------|
| met, met            | met     | met     | met        | met        |
| met, unmet          | unmet   | met     | met        | unmet      |
| met, unknown        | unknown | met     | met        | unknown    |
| unmet, met          | unmet   | met     | met        | unmet      |
| unmet, unmet        | unmet   | unmet   | unmet      | unmet      |
| unmet, unknown      | unmet   | unknown | unknown    | unmet      |
| unknown, met        | unknown | met     | met        | unknown    |
| unknown, unmet      | unmet   | unknown | unknown    | unmet      |
| unknown, unknown    | unknown | unknown | unknown    | unknown    |

`not`: met -> unmet, unmet -> met, unknown -> unknown. `at_least 2` of 3
children: all 27 triples by the same rule (CB2 walks them).

b-2 -- a leaf's subject (C-04).

| subject                   | bound to               | judged on        | state if not judged                    |
|---------------------------|------------------------|------------------|----------------------------------------|
| role `doer`               | `bindings.doer`        | that character   | --                                     |
| role `giver`              | a character            | that character   | --                                     |
| role `giver`              | a faction              | --               | unknown, « le donneur n'est pas un personnage » |
| role `giver` / `contact`  | nothing (None)         | --               | unknown, « … n'est pas défini ici »    |
| role `contact`            | a character            | that character   | --                                     |
| `subject_entity_id`       | a character            | that character   | --                                     |
| `subject_entity_id`       | not a character        | --               | unknown, « X n'est pas un personnage » (refused at write, C-06) |

Where the roles are bound: a day plan -> `doer` only (the player); an
offer's eligibility and a quest's agenda -> `doer`, the offer's giver, its
contact (`offer_bindings`, `plan_bindings`).

## Contracts

### C-01 — the leaf, `condition_forms.RequirementSpec`
Produced by: BRIEF-0111-A (moved), BRIEF-0111-B (widened)   Consumed by: B, C, D
Signature: frozen dataclass
`RequirementSpec(type: str, target_entity_id: Optional[str] = None,
target_key: Optional[str] = None, threshold: Optional[int] = None,
subject_role: Optional[str] = "doer", subject_entity_id: Optional[str] = None,
value: Optional[str] = None)`.
Return shape: n/a. Exactly one of `subject_role` / `subject_entity_id` is
set once cleaned; `subject_role` in `("doer", "giver", "contact")`.
Error and empty cases: none at construction; `writes.conditions.clean_leaf`
refuses (C-06).

### C-03 — the tree, `conditions.ConditionTree`
Produced by: BRIEF-0111-B (map/drop: BRIEF-0111-C)   Consumed by: C, D
Signature: frozen dataclass `ConditionTree(op: str, children:
tuple[ConditionTree, ...] = (), n: Optional[int] = None, leaf:
Optional[RequirementSpec] = None)`; `CONNECTORS = ("all", "any", "not",
"at_least")`; helpers `leaf(spec)`, `all_of(specs) -> Optional[tree]`
(None for no specs), `leaves(tree)` (depth first), `and_path_leaves(tree)`
(through `all` only), `flat_leaves(tree)` (`()` for None, the leaves of a
lone leaf or of `all` of leaves, else None), `map_leaves(tree, fn)`,
`drop_leaves(tree, drop)` (a connector left childless goes; `at_least`
keeps `n <= children`; None when the root goes).
Shape (`check_shape`, raises `ConditionShapeError(ValueError)`): a leaf
has a form and no children and exactly one subject (a known role or an
entity); a connector has at least one child; `not` exactly one;
`at_least` an integer `n` from 1 to its children; only `at_least` has `n`;
depth at most `MAX_DEPTH = 6`, nodes at most `MAX_NODES = 60`.
Dict form: a leaf `{"op": "leaf", "type", "subject_role",
"subject_entity_id", "target_entity_id", "target_key", "threshold",
"value"}`; a connector `{"op", "children": [...]}` plus `"n"` for
`at_least`. `node_from_dict(None)` is None; a leaf naming no subject is
`doer`; `""` reads as None; a non-integer threshold is refused.

### C-04 — evaluation, `conditions.evaluate`
Produced by: BRIEF-0111-B   Consumed by: C, D
Signature: `evaluate(tree: Optional[ConditionTree], bindings: Bindings,
db) -> Optional[VerdictNode]`; `Bindings(doer: Character, giver_id:
Optional[str] = None, contact_id: Optional[str] = None)`.
Return shape: `VerdictNode(state, op, children, n, spec, verdict, reason)`
-- `state` in `("met", "unmet", "unknown")`; a leaf carries its `spec`
and either its `Verdict` (judged) or its French `reason` (`unknown`);
`.met`; `.leaf_nodes()`; `.leaf_verdicts()` (judged leaves only).
Error and empty cases: None for no condition (the caller treats it as
met); a role bound to nothing -> `unknown` « … n'est pas défini ici »; a
subject that is not a character -> `unknown` « … n'est pas un personnage »;
an unknown form raises `ValueError`. Connectors per table b-1. One
reachable set per subject per call.

### C-05 — the French of a tree, `condition_text`
Produced by: BRIEF-0111-B (new forms: BRIEF-0111-C)   Consumed by: C, D
Signature: `describe(db, tree) -> list[dict]` (`{"depth", "text"}`, a
connector's head before its children one level deeper; [] for None);
`verdict_lines(db, verdict) -> list[dict]` (`{"depth", "text", "state",
"mark", "progress"}`, `mark` in ✓ ✗ ?, `progress` `"current/required"`
when both are integers, an unknown leaf's text ending with its reason);
`leaf_text(db, spec) -> str`. `FORM_PHRASES_FR` (one per form, `{who}`
`{target}` `{threshold}` `{value}`), `CONNECTOR_HEADS_FR` (one per
connector), `SUBJECT_LABELS_FR`, `VALUE_LABELS_FR` (one label per
`FORM_VALUES` value).
Error and empty cases: `leaf_text` raises `ValueError` on an unknown form.

## Context

The forms live in `condition_forms.py` (A). This brief adds the language itself, pure and without storage: the tree and its dict form (C-03), its three-valued evaluation on each leaf's subject (C-04, P1, R1) and its French (C-05). Nothing reads it yet: C stores it and wires every agenda to it.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md` is not in the
diff: regenerate it as listed.

1. Apply the embedded diff. It:
   - widens `RequirementSpec` with `subject_role` (default `doer`), `subject_entity_id` and `value` (C-01) -- every existing construction still judges the player;
   - creates `src/world_engine/conditions.py` (C-03, C-04) and `src/world_engine/condition_text.py` (C-05), neither of which writes anything;
   - adds CB1-CB5 to `conditions.py`;
   - updates CLAUDE.md's File structure line to `condition*.py`;
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - CLAUDE.md
   - src/world_engine/condition_forms.py
   - src/world_engine/condition_text.py
   - src/world_engine/conditions.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/checks/conditions.py
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(conditions): a condition is a tree of four connectors, judged in three values on each leaf's subject, read back in French (BRIEF-0111-b)`.

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index 0c96a0f..74e3cc5 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -458,7 +458,7 @@ WG-Nia/
 │   ├── observation_*.py     # observed-lane socle/engine/runner/reads/writes; per-NPC window
 │   ├── resolution.py, ledger.py  # physical-action dice resolution (2d6 bands); ledger read helpers
 │   ├── skill_lexicon.py     # action lexicon: judge/record; Play calls it, never clamps inline
-│   ├── day_plan.py, condition_forms.py  # day-plan emission + budget cut; requirement forms, BFS
+│   ├── day_plan.py, condition*.py  # day-plan emission + budget cut; conditions: forms, tree, text
 │   ├── day_extract.py       # day extraction: 3 passes (place/person/faction), never sees registry
 │   ├── day_concordance.py   # day mention resolution: matching rungs, germ emission; never authors
 │   ├── day_rewrite.py       # declaration rewrite: render/resolutions/load_latest, no model call
diff --git a/src/world_engine/condition_forms.py b/src/world_engine/condition_forms.py
index b431359..55ffafe 100644
--- a/src/world_engine/condition_forms.py
+++ b/src/world_engine/condition_forms.py
@@ -83,10 +83,18 @@ THRESHOLD_TYPES: tuple[str, ...] = ("relation_gte", "resource", "skill_rank_gte"
 
 @dataclass(frozen=True)
 class RequirementSpec:
+    """One form with its arguments: a leaf of the condition language. Its
+    SUBJECT (TICKET-0111, P1) is a role bound when the condition is judged
+    (`conditions.SUBJECT_ROLES`, `doer` by default: the character who acts)
+    or one fixed entity; `value` is the state a form compares to, for the
+    forms that take one."""
     type: str
     target_entity_id: Optional[str] = None
     target_key: Optional[str] = None
     threshold: Optional[int] = None
+    subject_role: Optional[str] = "doer"
+    subject_entity_id: Optional[str] = None
+    value: Optional[str] = None
 
 
 
diff --git a/src/world_engine/condition_text.py b/src/world_engine/condition_text.py
new file mode 100644
index 0000000..b610096
--- /dev/null
+++ b/src/world_engine/condition_text.py
@@ -0,0 +1,137 @@
+"""A condition in French, for the creator and the player (TICKET-0111,
+BRIEF-0111-B, decision T1).
+
+`describe` reads a tree back as indented lines (a connector heads its
+children); `verdict_lines` does the same for a judged tree, each line with
+its state and, for a form that counts, its progress (« 3/15 »). Both are
+read by the surfaces; neither decides anything. Every phrase comes from
+`FORM_PHRASES_FR`, one per form, kept equal to `REQUIREMENT_TYPES` by
+`conditions.py` CB4.
+"""
+
+from __future__ import annotations
+
+from typing import Optional
+
+from sqlmodel import Session
+
+from .condition_forms import RequirementSpec
+from .conditions import ConditionTree, VerdictNode
+from .models import Entity, Fact, QuestOffer
+from .prose_render import fact_text
+from .skill_access import skill_label
+
+# One phrase per form: {who} (the leaf's subject), {target}, {threshold} and
+# {value} are filled in; a phrase names only what its form uses.
+FORM_PHRASES_FR: dict[str, str] = {
+    "knowledge": "{who} connaît « {target} »",
+    "relation_gte": "{target} apprécie {who} à {threshold} ou plus",
+    "resource": "{who} possède au moins {threshold} en monnaie",
+    "location_reachable": "{who} peut atteindre {target}",
+    "has_met": "{who} a rencontré {target}",
+    "faction_member": "{who} est membre de {target}",
+    "skill_rank_gte": "{who} a « {target} » au rang {threshold} ou plus",
+    "quest_completed": "{who} a accompli la quête « {target} »",
+    "has_debt_to": "{who} a une dette envers {target}",
+    "no_debt_to": "{who} n'a aucune dette envers {target}",
+}
+
+CONNECTOR_HEADS_FR: dict[str, str] = {
+    "all": "Toutes ces conditions :",
+    "any": "Au moins une de ces conditions :",
+    "not": "Pas ceci :",
+    "at_least": "Au moins {n} de ces conditions :",
+}
+
+SUBJECT_LABELS_FR: dict[str, str] = {"doer": "le personnage", "giver": "le donneur", "contact": "le contact"}
+
+STATE_MARKS: dict[str, str] = {"met": "✓", "unmet": "✗", "unknown": "?"}
+
+
+def _entity_name(db: Session, entity_id: Optional[str]) -> str:
+    entity = db.get(Entity, entity_id) if entity_id else None
+    return entity.name if entity is not None else str(entity_id)
+
+
+def _target(db: Session, spec: RequirementSpec) -> str:
+    if spec.target_entity_id:
+        return _entity_name(db, spec.target_entity_id)
+    if spec.type == "knowledge":
+        fact = db.get(Fact, spec.target_key) if spec.target_key else None
+        return fact_text(db, fact) if fact is not None else str(spec.target_key)
+    if spec.type == "skill_rank_gte":
+        return skill_label(db, spec.target_key)
+    if spec.type == "quest_completed":
+        offer = db.get(QuestOffer, spec.target_key) if spec.target_key else None
+        return offer.title if offer is not None else str(spec.target_key)
+    return str(spec.target_key or "")
+
+
+def _subject(db: Session, spec: RequirementSpec) -> str:
+    if spec.subject_role is not None:
+        return SUBJECT_LABELS_FR.get(spec.subject_role, spec.subject_role)
+    return _entity_name(db, spec.subject_entity_id)
+
+
+def leaf_text(db: Session, spec: RequirementSpec) -> str:
+    phrase = FORM_PHRASES_FR.get(spec.type)
+    if phrase is None:
+        raise ValueError(f"condition_text: unknown requirement type {spec.type!r}")
+    text = phrase.format(who=_subject(db, spec), target=_target(db, spec),
+                         threshold=spec.threshold, value=spec.value)
+    return text[0].upper() + text[1:]
+
+
+def _head(op: str, n: Optional[int]) -> str:
+    return CONNECTOR_HEADS_FR[op].format(n=n)
+
+
+def describe(db: Session, node: Optional[ConditionTree]) -> list[dict]:
+    """The tree as lines: `{"depth", "text"}`, a connector before its
+    children. [] for no condition."""
+    lines: list[dict] = []
+    if node is not None:
+        _describe(db, node, 0, lines)
+    return lines
+
+
+def _describe(db: Session, node: ConditionTree, depth: int, lines: list[dict]) -> None:
+    if node.op == "leaf":
+        lines.append({"depth": depth, "text": leaf_text(db, node.leaf)})
+        return
+    lines.append({"depth": depth, "text": _head(node.op, node.n)})
+    for child in node.children:
+        _describe(db, child, depth + 1, lines)
+
+
+def _progress(verdict_node: VerdictNode) -> Optional[str]:
+    verdict = verdict_node.verdict
+    if verdict is None:
+        return None
+    current, required = verdict.current, verdict.required
+    if isinstance(current, int) and isinstance(required, int) and not isinstance(current, bool):
+        return f"{current}/{required}"
+    return None
+
+
+def verdict_lines(db: Session, verdict: Optional[VerdictNode]) -> list[dict]:
+    """A judged tree as lines: `{"depth", "text", "state", "mark",
+    "progress"}`; an `unknown` leaf's text ends with why."""
+    lines: list[dict] = []
+    if verdict is not None:
+        _verdict_lines(db, verdict, 0, lines)
+    return lines
+
+
+def _verdict_lines(db: Session, node: VerdictNode, depth: int, lines: list[dict]) -> None:
+    if node.op == "leaf":
+        text = leaf_text(db, node.spec)
+        if node.state == "unknown" and node.reason:
+            text = f"{text} ({node.reason})"
+        lines.append({"depth": depth, "text": text, "state": node.state, "mark": STATE_MARKS[node.state],
+                      "progress": _progress(node)})
+        return
+    lines.append({"depth": depth, "text": _head(node.op, node.n), "state": node.state,
+                  "mark": STATE_MARKS[node.state], "progress": None})
+    for child in node.children:
+        _verdict_lines(db, child, depth + 1, lines)
diff --git a/src/world_engine/conditions.py b/src/world_engine/conditions.py
new file mode 100644
index 0000000..1ffa4ce
--- /dev/null
+++ b/src/world_engine/conditions.py
@@ -0,0 +1,317 @@
+"""The condition language (TICKET-0111, BRIEF-0111-B, decisions A1, I1, P1,
+R1 and S1 of the series).
+
+A condition is a tree. Its leaves are the requirement forms of
+`condition_forms.py` (a `RequirementSpec` each); its inner nodes are four
+connectors: `all`, `any`, `not` (exactly one child) and `at_least` (`n` of
+its children). The vocabulary grows by adding forms, never by adding
+connectors.
+
+Every leaf names its SUBJECT (P1): a role bound when the condition is
+evaluated -- `doer`, the character who acts (the player for a quest or a day
+plan), `giver`, the offer's giver, `contact`, a faction giver's contact --
+or one fixed entity (`subject_entity_id`). A form judges a character; a
+subject that is not one, or a role nothing binds, makes the leaf
+`unknown`, never `met`.
+
+A verdict has three states (R1): `met`, `unmet`, `unknown`. The connectors
+follow Kleene's three-valued logic, so an `unknown` leaf can still be
+outweighed (`any` with a met sibling is met). A gate passes only on `met`.
+
+This module is pure apart from the evaluators it calls: it reads the canon
+through them and writes nothing. Storage is `writes/conditions.py`.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Optional
+
+from sqlmodel import Session
+
+from .condition_forms import _EVALUATORS, RequirementSpec, Verdict, _day_reachable_ids
+from .models import Character, Entity
+
+# The four connectors, then the leaf.
+CONNECTORS: tuple[str, ...] = ("all", "any", "not", "at_least")
+NODE_OPS: tuple[str, ...] = CONNECTORS + ("leaf",)
+
+# P1: the roles a leaf's subject may name, bound at evaluation.
+SUBJECT_ROLES: tuple[str, ...] = ("doer", "giver", "contact")
+
+# R1: a verdict's three states.
+VERDICT_STATES: tuple[str, ...] = ("met", "unmet", "unknown")
+
+# Bounds on a tree, so a condition stays readable and cheap to judge.
+MAX_DEPTH = 6
+MAX_NODES = 60
+
+
+class ConditionShapeError(ValueError):
+    """A tree that breaks the language's shape (an unknown connector, a
+    `not` with two children, an `at_least` asking for more than it has...).
+    Its message is the reason, in English, for the creator's 422."""
+
+
+@dataclass(frozen=True)
+class ConditionTree:
+    """A condition, or any of its subtrees: a connector with its children,
+    or a leaf carrying one form. (The stored rows are `models.ConditionNode`.)"""
+    op: str
+    children: tuple["ConditionTree", ...] = ()
+    n: Optional[int] = None
+    leaf: Optional[RequirementSpec] = None
+
+
+@dataclass(frozen=True)
+class Bindings:
+    """What the roles name when a condition is judged (P1)."""
+    doer: Character
+    giver_id: Optional[str] = None
+    contact_id: Optional[str] = None
+
+
+@dataclass(frozen=True)
+class VerdictNode:
+    state: str
+    op: str
+    children: tuple["VerdictNode", ...] = ()
+    n: Optional[int] = None
+    spec: Optional[RequirementSpec] = None
+    verdict: Optional[Verdict] = None
+    reason: Optional[str] = None  # why a leaf is `unknown`, in French
+
+    @property
+    def met(self) -> bool:
+        return self.state == "met"
+
+    def leaf_nodes(self) -> tuple["VerdictNode", ...]:
+        if self.op == "leaf":
+            return (self,)
+        return tuple(leaf for child in self.children for leaf in child.leaf_nodes())
+
+    def leaf_verdicts(self) -> tuple[Verdict, ...]:
+        """The verdicts of the leaves that were judged, in order; an
+        `unknown` leaf has none."""
+        return tuple(node.verdict for node in self.leaf_nodes() if node.verdict is not None)
+
+
+# --- building ------------------------------------------------------------------
+
+def leaf(spec: RequirementSpec) -> ConditionTree:
+    return ConditionTree(op="leaf", leaf=spec)
+
+
+def all_of(specs) -> Optional[ConditionTree]:
+    """A flat list as a tree: `all` of its leaves, or None when it is empty
+    (no condition)."""
+    specs = tuple(specs)
+    if not specs:
+        return None
+    return ConditionTree(op="all", children=tuple(leaf(s) for s in specs))
+
+
+def leaves(node: Optional[ConditionTree]) -> tuple[RequirementSpec, ...]:
+    """Every leaf, in order (depth first)."""
+    if node is None:
+        return ()
+    if node.op == "leaf":
+        return (node.leaf,)
+    return tuple(spec for child in node.children for spec in leaves(child))
+
+
+def and_path_leaves(node: Optional[ConditionTree]) -> tuple[RequirementSpec, ...]:
+    """The leaves the condition cannot be met without: those reached from
+    the root through `all` nodes only (Q1). A leaf under `any`, `not` or
+    `at_least` is not guaranteed and is left out."""
+    if node is None:
+        return ()
+    if node.op == "leaf":
+        return (node.leaf,)
+    if node.op != "all":
+        return ()
+    return tuple(spec for child in node.children for spec in and_path_leaves(child))
+
+
+def flat_leaves(node: Optional[ConditionTree]) -> Optional[tuple[RequirementSpec, ...]]:
+    """The leaves of a FLAT condition -- none, one leaf, or `all` of leaves --
+    or None when the tree is not flat (T1: only a flat condition is edited
+    as a list)."""
+    if node is None:
+        return ()
+    if node.op == "leaf":
+        return (node.leaf,)
+    if node.op == "all" and all(child.op == "leaf" for child in node.children):
+        return tuple(child.leaf for child in node.children)
+    return None
+
+
+# --- the dict form (what the API carries) --------------------------------------
+
+_LEAF_KEYS = ("type", "subject_role", "subject_entity_id", "target_entity_id", "target_key", "threshold", "value")
+
+
+def node_to_dict(node: Optional[ConditionTree]) -> Optional[dict]:
+    if node is None:
+        return None
+    if node.op == "leaf":
+        spec = node.leaf
+        return {"op": "leaf", **{key: getattr(spec, key) for key in _LEAF_KEYS}}
+    out: dict = {"op": node.op, "children": [node_to_dict(child) for child in node.children]}
+    if node.op == "at_least":
+        out["n"] = node.n
+    return out
+
+
+def _blank(value):
+    return None if value == "" else value
+
+
+def node_from_dict(raw: object) -> Optional[ConditionTree]:
+    """A request's tree, shape-checked (`check_shape`). None (or no body)
+    is no condition. Raises `ConditionShapeError`."""
+    if raw is None:
+        return None
+    node = _from_dict(raw)
+    check_shape(node)
+    return node
+
+
+def _from_dict(raw: object) -> ConditionTree:
+    if not isinstance(raw, dict):
+        raise ConditionShapeError(f"a condition node must be an object, got {raw!r}")
+    op = raw.get("op")
+    if op == "leaf":
+        threshold = raw.get("threshold")
+        if threshold is not None and (not isinstance(threshold, int) or isinstance(threshold, bool)):
+            raise ConditionShapeError(f"a leaf's threshold must be an integer, got {threshold!r}")
+        subject_entity_id = _blank(raw.get("subject_entity_id"))
+        subject_role = _blank(raw.get("subject_role"))
+        if subject_role is None and subject_entity_id is None:
+            subject_role = "doer"  # a leaf that names no subject judges the one who acts
+        spec = RequirementSpec(
+            type=raw.get("type"),
+            subject_role=subject_role,
+            subject_entity_id=subject_entity_id,
+            target_entity_id=_blank(raw.get("target_entity_id")),
+            target_key=_blank(raw.get("target_key")),
+            threshold=threshold,
+            value=_blank(raw.get("value")),
+        )
+        return ConditionTree(op="leaf", leaf=spec)
+    if op not in CONNECTORS:
+        raise ConditionShapeError(f"unknown condition connector {op!r}")
+    children = raw.get("children")
+    if not isinstance(children, list):
+        raise ConditionShapeError(f"a {op!r} node needs a list of children")
+    n = raw.get("n") if op == "at_least" else None
+    return ConditionTree(op=op, children=tuple(_from_dict(child) for child in children), n=n)
+
+
+# --- shape ---------------------------------------------------------------------
+
+def check_shape(node: ConditionTree) -> None:
+    """The language's shape, form-blind: connectors and their arity, a
+    leaf's subject (one role or one entity, never both), depth and size.
+    Whether a FORM is known and its target exists is the writer's check
+    (`writes.conditions.clean_condition`). Raises `ConditionShapeError`."""
+    count = _check_node(node, depth=1)
+    if count > MAX_NODES:
+        raise ConditionShapeError(f"a condition has at most {MAX_NODES} nodes, got {count}")
+
+
+def _check_node(node: ConditionTree, depth: int) -> int:
+    if depth > MAX_DEPTH:
+        raise ConditionShapeError(f"a condition is at most {MAX_DEPTH} levels deep")
+    if node.op == "leaf":
+        if node.leaf is None or node.children:
+            raise ConditionShapeError("a leaf carries a form and no children")
+        spec = node.leaf
+        if (spec.subject_role is None) == (spec.subject_entity_id is None):
+            raise ConditionShapeError("a leaf names exactly one subject: a role or an entity")
+        if spec.subject_role is not None and spec.subject_role not in SUBJECT_ROLES:
+            raise ConditionShapeError(f"unknown subject role {spec.subject_role!r}")
+        return 1
+    if node.op not in CONNECTORS or node.leaf is not None:
+        raise ConditionShapeError(f"unknown condition connector {node.op!r}")
+    if not node.children:
+        raise ConditionShapeError(f"a {node.op!r} node needs at least one child")
+    if node.op == "not" and len(node.children) != 1:
+        raise ConditionShapeError("a 'not' node has exactly one child")
+    if node.op == "at_least":
+        n = node.n
+        if not isinstance(n, int) or isinstance(n, bool) or not 1 <= n <= len(node.children):
+            raise ConditionShapeError(f"'at_least' needs n between 1 and its {len(node.children)} children, got {n!r}")
+    elif node.n is not None:
+        raise ConditionShapeError(f"only 'at_least' carries n, not {node.op!r}")
+    return 1 + sum(_check_node(child, depth + 1) for child in node.children)
+
+
+# --- evaluation ----------------------------------------------------------------
+
+def evaluate(node: Optional[ConditionTree], bindings: Bindings, db: Session) -> Optional[VerdictNode]:
+    """Judge `node` against the canon (R1). None for no condition -- the
+    caller treats it as met. Each subject's reachable set is computed at
+    most once, and only for a `location_reachable` leaf."""
+    if node is None:
+        return None
+    return _evaluate(node, bindings, db, {})
+
+
+def _evaluate(node: ConditionTree, bindings: Bindings, db: Session, reachable: dict) -> VerdictNode:
+    if node.op == "leaf":
+        return _evaluate_leaf(node.leaf, bindings, db, reachable)
+    children = tuple(_evaluate(child, bindings, db, reachable) for child in node.children)
+    return VerdictNode(state=_combine(node, children), op=node.op, children=children, n=node.n)
+
+
+def _combine(node: ConditionTree, children: tuple[VerdictNode, ...]) -> str:
+    met = sum(1 for c in children if c.state == "met")
+    unknown = sum(1 for c in children if c.state == "unknown")
+    total = len(children)
+    if node.op == "not":
+        return {"met": "unmet", "unmet": "met"}.get(children[0].state, "unknown")
+    need = {"all": total, "any": 1, "at_least": node.n}[node.op]
+    if met >= need:
+        return "met"
+    if met + unknown < need:
+        return "unmet"
+    return "unknown"
+
+
+_ROLE_LABELS_FR = {"giver": "le donneur", "contact": "le contact"}
+
+
+def _subject(spec: RequirementSpec, bindings: Bindings, db: Session) -> tuple[Optional[Character], Optional[str]]:
+    """The character a leaf judges, or None and why (in French)."""
+    if spec.subject_role == "doer":
+        return bindings.doer, None
+    if spec.subject_role is not None:
+        entity_id = bindings.giver_id if spec.subject_role == "giver" else bindings.contact_id
+        label = _ROLE_LABELS_FR[spec.subject_role]
+        if entity_id is None:
+            return None, f"{label} n'est pas défini ici"
+    else:
+        entity_id = spec.subject_entity_id
+        entity = db.get(Entity, entity_id)
+        label = entity.name if entity is not None else "le sujet"
+    character = db.get(Character, entity_id)
+    if character is None:
+        return None, f"{label} n'est pas un personnage"
+    return character, None
+
+
+def _evaluate_leaf(spec: RequirementSpec, bindings: Bindings, db: Session, reachable: dict) -> VerdictNode:
+    evaluator = _EVALUATORS.get(spec.type)
+    if evaluator is None:
+        raise ValueError(f"unknown requirement type {spec.type!r}")
+    character, why = _subject(spec, bindings, db)
+    if character is None:
+        return VerdictNode(state="unknown", op="leaf", spec=spec, reason=why)
+    ids = None
+    if spec.type == "location_reachable":
+        if character.id not in reachable:
+            reachable[character.id] = _day_reachable_ids(character.current_location_id, db)
+        ids = reachable[character.id]
+    verdict = evaluator(spec, character, db, ids)
+    return VerdictNode(state="met" if verdict.met else "unmet", op="leaf", spec=spec, verdict=verdict)
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index f3c707f..606fdcf 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18379,6 +18379,42 @@ is re-exported from `day_plan.py`, so each lives in one place
 `condition_forms.py`; `known_reachability.py` documents it in place of
 `day_plan.py` as a `connects_to` reader (row 12 of the census, unchanged).
 
+## A CONDITION IS A TREE OF FOUR CONNECTORS OVER THE FORMS (TICKET-0111) -- EACH LEAF NAMES ITS SUBJECT, A VERDICT HAS THREE STATES (BRIEF-0111-b, no schema change)
+
+**A1, I1.** A condition is a tree (`conditions.ConditionTree`, each node the
+root of its own subtree): its leaves
+are the requirement forms (`RequirementSpec`), its inner nodes `all`,
+`any`, `not` (one child) and `at_least` (`n` of its children). The
+vocabulary grows by forms, never by connectors. A tree is at most six
+levels and sixty nodes deep (`MAX_DEPTH`, `MAX_NODES`); `check_shape` holds
+the language's shape, form-blind -- whether a form is known and its target
+exists stays the writer's check.
+
+**P1.** Every leaf names its subject: a role bound at evaluation --
+`doer`, the character who acts; `giver`, an offer's giver; `contact`, a
+faction giver's contact -- or one fixed entity (`subject_entity_id`).
+`RequirementSpec` gains `subject_role` (default `doer`, so every existing
+construction still judges the player), `subject_entity_id` and `value`.
+A form judges a character: a role nothing binds, or a subject that is not a
+character, makes the leaf `unknown` with its French reason.
+
+**R1.** A verdict (`VerdictNode`) is `met`, `unmet` or `unknown`; the
+connectors follow Kleene's three-valued logic, so an `unknown` leaf can be
+outweighed (`any` with a met sibling is met). A gate passes only on `met`.
+Each subject's reachable set is computed once per evaluation.
+
+**Q1, T1.** `and_path_leaves` gives the leaves a condition cannot be met
+without (reached through `all` only) -- what the day's NPC and the deepened
+facts will read; `flat_leaves` gives the leaves of a flat tree (none, one,
+or `all` of leaves) and None otherwise -- what a list editor can show.
+
+**French.** `condition_text.describe` reads a tree back as indented lines;
+`verdict_lines` reads a judged tree with a mark per line and the progress
+of a counting form (« 60/50 »). One phrase per form (`FORM_PHRASES_FR`).
+
+**Rejected.** A fourth verdict state for « not applicable »: a leaf whose
+subject cannot be bound is unknown, and a gate treats it as not met.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/conditions.py b/tooling/verify/checks/conditions.py
index 5327524..d41f4a4 100644
--- a/tooling/verify/checks/conditions.py
+++ b/tooling/verify/checks/conditions.py
@@ -13,13 +13,47 @@ CA1 -- the forms have one home (BRIEF-0111-A, static, AST). Each of
    their own); no other module defines a function of the same name as one
    of its `_eval_*` evaluators.
 
-A rule that collects nothing fails.
+CB1 -- the tree's shape (BRIEF-0111-B, import, no DB). `node_from_dict`
+   round-trips a tree using every connector through `node_to_dict`, gives a
+   leaf that names no subject the role `doer`, and refuses, each with a
+   `ConditionShapeError`: an unknown connector, a `not` with two children,
+   an `at_least` with n = 0 or n above its children, an `all` with none, a
+   leaf naming both a role and an entity, an unknown role, a tree seven
+   levels deep, a tree of 61 nodes, a non-integer threshold.
+CB2 -- three-valued connectors (import, no DB). `_combine` gives, for every
+   pair of child states, what the reference table below gives for `all`,
+   `any`, `at_least` 1 and 2; for `not`, each of the three states; and for
+   `at_least` 2 of 3, every triple.
+CB3 -- evaluation (fixture). A doer, an NPC, a faction giver: a leaf is
+   judged on its subject -- the doer, a giver or contact bound to a
+   character, a fixed entity; a role bound to nothing or to a faction is
+   `unknown` with its French reason and no verdict; `any` of an unknown and
+   a met leaf is met, `all` of them unknown, `not` of a met leaf unmet;
+   `leaf_verdicts` holds the judged leaves only; each subject's reachable
+   set is computed once. `and_path_leaves` keeps only the leaves reached
+   through `all`; `flat_leaves` returns the leaves of a flat tree and None
+   otherwise.
+CB4 -- French (fixture). `FORM_PHRASES_FR` has one phrase per form of
+   `REQUIREMENT_TYPES` and `CONNECTOR_HEADS_FR` one head per connector;
+   `describe` puts a connector before its children one level deeper;
+   `verdict_lines` marks each line, gives a counting leaf its progress and
+   an unknown leaf its reason.
+CB5 -- the language writes nothing (static, AST). Neither `conditions.py`
+   nor `condition_text.py` calls `add`, `commit`, `delete`, `execute` or
+   `flush`.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
 from __future__ import annotations
 
 import ast
+import itertools
+import os
 import pathlib
 import sys
+import tempfile
+from datetime import UTC, datetime
 
 ROOT = pathlib.Path(__file__).resolve().parents[3]
 SRC = ROOT / "src" / "world_engine"
@@ -62,6 +96,14 @@ def _modules() -> dict[pathlib.Path, set[str]]:
     return found
 
 
+def _fresh_db() -> str:
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
+    return db_path
+
+
 # --- CA1 -----------------------------------------------------------------------
 
 def check_ca1() -> None:
@@ -87,14 +129,285 @@ def check_ca1() -> None:
             fail(f"CA1: {rel} defines the evaluator {name}, which lives in condition_forms.py")
 
 
+# --- CB1 -----------------------------------------------------------------------
+
+def _leaf(form="has_met", **kw) -> dict:
+    return {"op": "leaf", "type": form, **kw}
+
+
+def check_cb1() -> None:
+    from world_engine.conditions import ConditionShapeError, node_from_dict, node_to_dict
+
+    tree = {"op": "all", "children": [
+        _leaf(subject_role="doer", target_entity_id="x"),
+        {"op": "any", "children": [_leaf(subject_role="giver", target_entity_id="y"),
+                                   {"op": "not", "children": [_leaf(subject_entity_id="z", target_entity_id="x")]}]},
+        {"op": "at_least", "n": 2, "children": [_leaf(subject_role="contact", target_entity_id=str(i)) for i in range(3)]},
+    ]}
+    node = node_from_dict(tree)
+    back = node_to_dict(node)
+    if [c["op"] for c in back["children"]] != ["leaf", "any", "at_least"] or back["children"][2]["n"] != 2:
+        fail(f"CB1: the tree does not round-trip: {back}")
+    if node_to_dict(node_from_dict(back)) != back:
+        fail("CB1: a round-tripped tree changes on a second pass")
+    defaulted = node_from_dict(_leaf(target_entity_id="x"))
+    if defaulted.leaf.subject_role != "doer" or defaulted.leaf.subject_entity_id is not None:
+        fail(f"CB1: a leaf naming no subject is {defaulted.leaf}")
+
+    deep = _leaf(target_entity_id="x")
+    for _ in range(6):
+        deep = {"op": "all", "children": [deep]}
+    refused = {
+        "an unknown connector": {"op": "xor", "children": [_leaf()]},
+        "a not with two children": {"op": "not", "children": [_leaf(), _leaf()]},
+        "at_least n = 0": {"op": "at_least", "n": 0, "children": [_leaf()]},
+        "at_least n above its children": {"op": "at_least", "n": 3, "children": [_leaf(), _leaf()]},
+        "an empty all": {"op": "all", "children": []},
+        "a leaf naming a role and an entity": _leaf(subject_role="doer", subject_entity_id="z"),
+        "an unknown role": _leaf(subject_role="witness"),
+        "seven levels": deep,
+        "61 nodes": {"op": "all", "children": [_leaf() for _ in range(60)]},
+        "a non-integer threshold": _leaf("relation_gte", threshold="50"),
+    }
+    for label, raw in refused.items():
+        try:
+            node_from_dict(raw)
+        except ConditionShapeError:
+            continue
+        fail(f"CB1: {label} is accepted")
+
+
+# --- CB2 -----------------------------------------------------------------------
+
+# The reference: three-valued (Kleene) logic, counted -- `need` of the
+# children must be met; unmet once even every unknown met could not reach it.
+def _reference(op: str, states: tuple[str, ...], n=None) -> str:
+    if op == "not":
+        return {"met": "unmet", "unmet": "met", "unknown": "unknown"}[states[0]]
+    need = {"all": len(states), "any": 1, "at_least": n}[op]
+    met, unknown = states.count("met"), states.count("unknown")
+    return "met" if met >= need else "unmet" if met + unknown < need else "unknown"
+
+
+def check_cb2() -> None:
+    from world_engine.conditions import ConditionTree, VerdictNode, _combine
+
+    states = ("met", "unmet", "unknown")
+    cases = 0
+    for op, n, width in (("all", None, 2), ("any", None, 2), ("at_least", 1, 2), ("at_least", 2, 2),
+                         ("not", None, 1), ("at_least", 2, 3)):
+        for combo in itertools.product(states, repeat=width):
+            children = tuple(VerdictNode(state=st, op="leaf") for st in combo)
+            node = ConditionTree(op=op, children=tuple(ConditionTree(op="leaf") for _ in combo), n=n)
+            got = _combine(node, children)
+            want = _reference(op, combo, n)
+            cases += 1
+            if got != want:
+                fail(f"CB2: {op}{'' if n is None else n} of {combo} is {got}, expected {want}")
+    if cases != 9 * 4 + 3 + 27:
+        fail(f"CB2: walked {cases} cases")
+
+
+# --- CB3 -----------------------------------------------------------------------
+
+def _cb_world(session) -> dict:
+    from world_engine.models import Character, Entity, Faction, Location, Relation, Rencontre, World
+
+    world = World(name="Conditions CB3", is_active=False)
+    session.add(world)
+    session.flush()
+    ids = {"world": world.id}
+    for key in ("place", "far"):
+        row = Entity(world_id=world.id, type="location", name=key.capitalize())
+        session.add(row)
+        session.flush()
+        session.add(Location(id=row.id))
+        ids[key] = row.id
+    for key, kind, where in (("pc", "player", "place"), ("npc", "npc", "far"), ("other", "npc", "place")):
+        row = Entity(world_id=world.id, type="character", name=key.upper())
+        session.add(row)
+        session.flush()
+        session.add(Character(id=row.id, world_id=world.id, character_type=kind, current_location_id=ids[where]))
+        ids[key] = row.id
+    faction = Entity(world_id=world.id, type="faction", name="Guilde")
+    session.add(faction)
+    session.flush()
+    session.add(Faction(id=faction.id))
+    ids["faction"] = faction.id
+    low, high = sorted((ids["pc"], ids["npc"]))
+    now = datetime(2026, 1, 1, tzinfo=UTC)
+    session.add(Rencontre(world_id=world.id, entity_lo_id=low, entity_hi_id=high, first_at=now, last_at=now,
+                          source="visit"))
+    session.add(Relation(world_id=world.id, entity_a_id=ids["npc"], entity_b_id=ids["pc"], type="ami",
+                         direction="a_to_b", intensity=60, change_history=[]))
+    session.commit()
+    return ids
+
+
+def _spec(form, **kw):
+    from world_engine.condition_forms import RequirementSpec
+
+    return RequirementSpec(type=form, **kw)
+
+
+def _cb3_subjects(session, ids, evaluate, Bindings, leaf) -> None:
+    from world_engine.models import Character
+
+    pc = session.get(Character, ids["pc"])
+    met_npc = leaf(_spec("has_met", target_entity_id=ids["npc"]))
+    if evaluate(met_npc, Bindings(doer=pc), session).state != "met":
+        fail("CB3: the doer has met the NPC and the leaf is not met")
+    giver_met = leaf(_spec("has_met", subject_role="giver", target_entity_id=ids["pc"]))
+    if evaluate(giver_met, Bindings(doer=pc, giver_id=ids["npc"]), session).state != "met":
+        fail("CB3: a giver bound to the NPC is not judged on the NPC")
+    if evaluate(giver_met, Bindings(doer=pc, giver_id=ids["other"]), session).state != "unmet":
+        fail("CB3: a giver bound to another character is not judged on him")
+    for bindings, label in ((Bindings(doer=pc, giver_id=ids["faction"]), "n'est pas un personnage"),
+                            (Bindings(doer=pc), "n'est pas défini ici")):
+        verdict = evaluate(giver_met, bindings, session)
+        if verdict.state != "unknown" or verdict.verdict is not None or label not in (verdict.reason or ""):
+            fail(f"CB3: an unbindable giver gives {verdict.state}, {verdict.reason!r}")
+    contact = leaf(_spec("has_met", subject_role="contact", target_entity_id=ids["pc"]))
+    if evaluate(contact, Bindings(doer=pc, contact_id=ids["npc"]), session).state != "met":
+        fail("CB3: a contact bound to the NPC is not judged on the NPC")
+    fixed = leaf(_spec("has_met", subject_role=None, subject_entity_id=ids["npc"], target_entity_id=ids["pc"]))
+    if evaluate(fixed, Bindings(doer=pc), session).state != "met":
+        fail("CB3: a fixed subject is not judged on its entity")
+
+
+def _cb3_connectors(session, ids, evaluate, Bindings, leaf, ConditionTree) -> None:
+    from world_engine.models import Character
+
+    pc = session.get(Character, ids["pc"])
+    met = leaf(_spec("has_met", target_entity_id=ids["npc"]))
+    unknown = leaf(_spec("has_met", subject_role="contact", target_entity_id=ids["pc"]))
+    bindings = Bindings(doer=pc)
+    either = evaluate(ConditionTree(op="any", children=(unknown, met)), bindings, session)
+    both = evaluate(ConditionTree(op="all", children=(unknown, met)), bindings, session)
+    negated = evaluate(ConditionTree(op="not", children=(met,)), bindings, session)
+    if (either.state, both.state, negated.state) != ("met", "unknown", "unmet"):
+        fail(f"CB3: any/all/not give {either.state}, {both.state}, {negated.state}")
+    if len(both.leaf_verdicts()) != 1 or len(both.leaf_nodes()) != 2:
+        fail("CB3: leaf_verdicts holds an unknown leaf, or leaf_nodes misses one")
+
+
+def _cb3_reachable(session, ids, evaluate, Bindings, leaf, ConditionTree) -> None:
+    from world_engine import conditions
+    from world_engine.models import Character
+
+    pc = session.get(Character, ids["pc"])
+    calls: list[str] = []
+    real = conditions._day_reachable_ids
+
+    def counting(origin, db):
+        calls.append(origin)
+        return real(origin, db)
+
+    reach = [leaf(_spec("location_reachable", target_entity_id=ids[k])) for k in ("place", "far")]
+    reach += [leaf(_spec("location_reachable", subject_role="giver", target_entity_id=ids[k])) for k in ("place", "far")]
+    conditions._day_reachable_ids = counting
+    try:
+        verdict = evaluate(ConditionTree(op="all", children=tuple(reach)), Bindings(doer=pc, giver_id=ids["npc"]), session)
+    finally:
+        conditions._day_reachable_ids = real
+    if sorted(calls) != sorted([ids["place"], ids["far"]]):
+        fail(f"CB3: the reachable sets were computed for {calls}, once per subject expected")
+    if [n.state for n in verdict.leaf_nodes()] != ["met", "unmet", "unmet", "met"]:
+        fail(f"CB3: reachability reads {[n.state for n in verdict.leaf_nodes()]}")
+
+
+def _cb3_paths(ConditionTree, leaf) -> None:
+    from world_engine.conditions import all_of, and_path_leaves, flat_leaves
+
+    a, b, c, d, e = (_spec("has_met", target_entity_id=k) for k in "abcde")
+    tree = ConditionTree(op="all", children=(
+        leaf(a), ConditionTree(op="any", children=(leaf(b), leaf(c))),
+        ConditionTree(op="all", children=(leaf(d),)), ConditionTree(op="not", children=(leaf(e),))))
+    if and_path_leaves(tree) != (a, d):
+        fail(f"CB3: and_path_leaves gives {and_path_leaves(tree)}")
+    if flat_leaves(all_of([a, b])) != (a, b) or flat_leaves(tree) is not None:
+        fail("CB3: flat_leaves misreads a flat or a nested tree")
+    if flat_leaves(None) != () or flat_leaves(leaf(a)) != (a,) or all_of([]) is not None:
+        fail("CB3: no condition, or a lone leaf, is not flat")
+
+
+def check_cb3(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.conditions import Bindings, ConditionTree, evaluate, leaf
+
+    with Session(engine) as session:
+        ids = _cb_world(session)
+        _cb3_subjects(session, ids, evaluate, Bindings, leaf)
+        _cb3_connectors(session, ids, evaluate, Bindings, leaf, ConditionTree)
+        _cb3_reachable(session, ids, evaluate, Bindings, leaf, ConditionTree)
+    _cb3_paths(ConditionTree, leaf)
+
+
+# --- CB4 -----------------------------------------------------------------------
+
+def check_cb4(engine) -> None:
+    from sqlmodel import Session, select
+
+    from world_engine import condition_forms, condition_text, conditions
+    from world_engine.models import Character, Entity, World
+
+    if set(condition_text.FORM_PHRASES_FR) != set(condition_forms.REQUIREMENT_TYPES):
+        fail(f"CB4: FORM_PHRASES_FR covers {sorted(condition_text.FORM_PHRASES_FR)}")
+    if set(condition_text.CONNECTOR_HEADS_FR) != set(conditions.CONNECTORS):
+        fail(f"CB4: CONNECTOR_HEADS_FR covers {sorted(condition_text.CONNECTOR_HEADS_FR)}")
+    with Session(engine) as session:
+        world = session.exec(select(World).where(World.name == "Conditions CB3")).one()
+        names = {e.name: e.id for e in session.exec(select(Entity).where(Entity.world_id == world.id)).all()}
+        pc = session.get(Character, names["PC"])
+        tree = conditions.ConditionTree(op="at_least", n=1, children=(
+            conditions.leaf(_spec("relation_gte", target_entity_id=names["NPC"], threshold=50)),
+            conditions.leaf(_spec("has_met", subject_role="contact", target_entity_id=names["PC"]))))
+        lines = condition_text.describe(session, tree)
+        if [(l["depth"], l["text"]) for l in lines] != [
+                (0, "Au moins 1 de ces conditions :"), (1, "NPC apprécie le personnage à 50 ou plus"),
+                (1, "Le contact a rencontré PC")]:
+            fail(f"CB4: describe gives {lines}")
+        judged = condition_text.verdict_lines(session, conditions.evaluate(tree, conditions.Bindings(doer=pc), session))
+        if [(l["mark"], l["progress"]) for l in judged] != [("✓", None), ("✓", "60/50"), ("?", None)]:
+            fail(f"CB4: verdict_lines gives {[(l['mark'], l['progress']) for l in judged]}")
+        if "n'est pas défini ici" not in judged[2]["text"]:
+            fail(f"CB4: an unknown leaf's line does not say why: {judged[2]['text']!r}")
+
+
+# --- CB5 -----------------------------------------------------------------------
+
+def check_cb5() -> None:
+    forbidden = {"add", "commit", "delete", "execute", "flush"}
+    for rel in ("conditions.py", "condition_text.py"):
+        path = SRC / rel
+        tree = ast.parse(path.read_text(encoding="utf-8"))
+        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
+        if not calls:
+            fail(f"CB5: {rel} makes zero calls")
+        for node in calls:
+            if isinstance(node.func, ast.Attribute) and node.func.attr in forbidden:
+                fail(f"CB5: {rel}:{node.lineno} calls .{node.func.attr}(")
+
+
 def main() -> int:
+    _fresh_db()
     check_ca1()
+    check_cb1()
+    check_cb2()
+    from world_engine.db import create_db_and_tables, engine
+    create_db_and_tables()
+    check_cb3(engine)
+    check_cb4(engine)
+    check_cb5()
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
         return 1
     print("PASS: conditions -- the requirement forms, their evaluators and their BFS live in "
-          "condition_forms.py alone")
+          "condition_forms.py alone; a condition is a tree of four connectors over those forms, "
+          "shape-checked, judged in three values on each leaf's subject, and read back in French "
+          "without writing anything")
     return 0
 
 
````

## Scope OUT

- Storing a tree, any table or migration, any new form (C).
- Any caller of `evaluate`, `describe` or `verdict_lines` outside the check (C, D).
- A fourth verdict state (R1 is three).
- The interpreter in natural language (TICKET-0112), world state attributes (0113), the event journal, failure conditions and absence conditions (0114, N1), the creator dashboard (0115), rank trials (0116).
- `goal_prerequisite`, the NPC goal's gate (GP1: its own ticket).
- Any change to the day-chain prompts or to the model's four forms (`MODEL_REQUIREMENT_TYPES`).
- A completion that acts on its own (M2); a visual tree editor (T2).
- Any change to `legacy.html` or Play.
- Every later brief of this lot.

## Invariants to defend

**Secrets are structurally excluded** -- the French of a leaf names a fact through `prose_render.fact_text`, never through a model; nothing here assembles a prompt. `conditions.py` and `condition_text.py` make no write call (CB5).

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- A named mutation does not turn its rule red.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run every check with `WORLD_ENGINE_ENV=test`).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/conditions.py` -> `PASS: conditions -- the requirement forms, their evaluators and their BFS live in condition_forms.py alone; a condition is a tree of four connectors over those forms, shape-checked, judged in three values on each leaf's subject, and read back in French without writing anything`
- `claude_md_contract.py`, `knowledge_identity.py`, `module_budget.py`, `function_length.py`, `import_cycle.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`conditions.py` exits 1 with the rule named):
  - in `src/world_engine/conditions.py`, `    if met + unknown < need:` -> `    if met < need:` -> `CB2`
  - in `src/world_engine/condition_text.py`, `    "not": "Pas ceci :",` -> `(removed)` -> `CB4`
  - in `src/world_engine/conditions.py`, before the line `    return _evaluate(node, bindings, db, {})`, insert the line `    db.flush()` -> `CB5`
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 144/144.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `A CONDITION IS A TREE OF FOUR CONNECTORS OVER THE FORMS (TICKET-0111) -- EACH LEAF NAMES ITS SUBJECT, A VERDICT HAS THREE STATES (BRIEF-0111-b, no schema change)` -- in the diff. No schema change.
