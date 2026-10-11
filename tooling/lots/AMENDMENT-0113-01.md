# AMENDMENT-0113-01 — a hidden attribute its subject cannot hold is unknown without its name

Ticket: TICKET-0113 "The state of the world"   Lot: LOT-0113-world-state.md
Brief in flight: BRIEF-0113-B (applied, not committed, on `ticket/0113`)
Trigger: Claude Code's `/review-step` on BRIEF-0113-B -- VIOLATION, INV-62
Decision: Nia, 2026-10-11 -- the fix below (it enforces WH1 / INV-62 as
locked; no new design choice)

## What deviated

BRIEF-0113-B's `attribute_unjudged` returns « <entity> n'a pas l'état
« <attribute> » » when the leaf's subject is of a type the attribute does
not apply to, whatever `view.hidden`. `_evaluate_leaf` turns it into an
`unknown` leaf with no verdict and that reason; `VerdictNode.seen_by`
hides only a JUDGED leaf whose verdict is hidden, so the reason passes
through, and `condition_text._verdict_lines` and `day_resolve._blocked`
append « (reason) » to the player's line. Reachable: a hidden attribute
that applies to locations only, on a role-bound subject (`doer`, `giver`,
`contact`) that is a character -- roles are not type-checked by the writer.
The player reads the hidden attribute's name: INV-62 broken. AB4 covered a
hidden attribute that applies, not this path.

A lot defect: b-2's row « entity of a type it does not apply to » showed
`?` for the player and did not say the REASON is written out too. Claude
Code stopped where it should.

A second lot defect, found in the same run: `pipeline_state.py` requires
every Machine-checkable arrow of a briefed ticket to resolve to a file.
TICKET-0113 links `attribute_conditions.py` (created by B) and
`attribute_interpreter.py` (created by D), so the corpus is red on
`pipeline_state.py` from A until D. The briefs said « green ».

## Decisions

- **The reason of an unholdable hidden attribute names nothing.**
  `attribute_unjudged` returns `HIDDEN_STATE_REASON_FR` (« c'est un état
  encore caché ») when the attribute is hidden. The constant moves from
  `conditions.py` to `condition_forms.py` (`conditions.py` imports
  `condition_forms`, never the reverse) and `conditions.py` imports it: one
  text, one place. The creator's surfaces read the same reason; the leaf's
  own line still names the attribute for her (`describe`, `verdict_lines`
  without a viewer).
- **`pipeline_state.py` red until D is expected.** BRIEF-0113-B and
  BRIEF-0113-C: REPORT-ONLY, when its only failure is the arrow to
  `attribute_interpreter.py` (B: and nothing else). Green from D on. No
  file is created early to silence it.

## Added finding (verbatim; the lot header carries the same text)

### R-22 — an unjudged leaf's reason reaches the player [M]
Added by AMENDMENT-0113-01 (Claude Code's `/review-step` on BRIEF-0113-B).
Opened (after BRIEF-0113-B's diff): `src/world_engine/condition_forms.py`
(`attribute_unjudged`: the reason names the attribute);
`src/world_engine/conditions.py` (`_evaluate_leaf`: an unjudged leaf has no
verdict and carries the reason; `VerdictNode.seen_by`: hides a judged leaf
whose `verdict.hidden`); `src/world_engine/condition_text.py:195-196`
(`_verdict_lines` appends « (reason) »); `src/world_engine/day_resolve.py:336-339`
(`_blocked` the same).
Consequence: a hidden attribute's unjudged reason is
`HIDDEN_STATE_REASON_FR`; AB4 covers the path.

### R-23 — every arrow of a briefed ticket must resolve [M]
Added by AMENDMENT-0113-01.
Opened: `tooling/verify/checks/pipeline_state.py:30-34` (docstring: a
ticket at `brief` or later needs every Machine-checkable arrow to resolve),
`:119-120` (the failure).
Consequence: red from A to C on the arrows to checks a later brief
creates; REPORT-ONLY there, green from D.

## Amended contract (verbatim; the lot header carries the same text)

### C-04 — the `attribute` leaf (stored form) and its verdict
Amended by AMENDMENT-0113-01 (produced by BRIEF-0113-B):
`condition_forms.HIDDEN_STATE_REASON_FR = "c'est un état encore caché"`
(moved from `conditions.py`, which re-exports it by import);
`attribute_unjudged(req, holder, db)` returns it when the attribute is
hidden and does not apply to the holder's type; « cet état n'existe plus »
when the attribute is gone (names nothing either way).

## Amended case table

b-2 -- the row « entity of a type it does not apply to » reads:

| subject                                     | attribute                       | verdict                    | player (`seen_by`)     |
|---------------------------------------------|---------------------------------|----------------------------|------------------------|
| entity of a type it does not apply to       | visible                         | unknown « n'a pas l'état » | `?` and that reason    |
| entity of a type it does not apply to       | hidden                          | unknown `HIDDEN_STATE_REASON_FR` | `?`, « état encore caché »; neither name nor label anywhere |

## The change (apply on top of BRIEF-0113-B's applied diff)

Save the block below to a file, then from the repository root, with
BRIEF-0113-B's diff applied and not committed: `git apply --check <file>`,
`git apply <file>`. Then continue BRIEF-0113-B from its Scope IN step 2
(build, regenerate, ONE commit holding both): the commit message stays
BRIEF-0113-B's. The files it touches, exactly:
- src/world_engine/condition_forms.py
- src/world_engine/conditions.py
- tooling/verify/checks/attribute_conditions.py

````diff
diff --git a/src/world_engine/condition_forms.py b/src/world_engine/condition_forms.py
index 1894360..04fe467 100644
--- a/src/world_engine/condition_forms.py
+++ b/src/world_engine/condition_forms.py
@@ -353,15 +353,27 @@ def _attribute_wanted(db: Session, req: RequirementSpec, view: AttributeView) ->
     return value_label(db, view, req.target_entity_id) if req.target_entity_id else "quelqu'un"
 
 
+# WH1 (TICKET-0113): why a leaf on a hidden attribute shows `?` to a player,
+# even about himself (`conditions.VerdictNode.seen_by`) -- and why it is
+# `unknown` when its subject cannot hold it (`attribute_unjudged`): never
+# its name, which a player surface would write out (INV-62,
+# AMENDMENT-0113-01).
+HIDDEN_STATE_REASON_FR = "c'est un état encore caché"
+
+
 def attribute_unjudged(req: RequirementSpec, holder, db: Session) -> Optional[str]:
     """Why an `attribute` leaf cannot be judged on `holder` (its subject) --
     the attribute is gone, or does not apply to its type -- in French; None
-    when it can. `conditions._evaluate_leaf` makes such a leaf `unknown`."""
+    when it can. `conditions._evaluate_leaf` makes such a leaf `unknown`,
+    and every surface writes this reason out: a hidden attribute's is
+    `HIDDEN_STATE_REASON_FR`, which names nothing (INV-62)."""
     view = view_of(db, req.target_key)
     entity = db.get(Entity, holder.id)
     if view is None or entity is None:
         return "cet état n'existe plus"
     if not applies_to(view, entity.type):
+        if view.hidden:
+            return HIDDEN_STATE_REASON_FR
         return f"{entity.name} n'a pas l'état « {view.name} »"
     return None
 
diff --git a/src/world_engine/conditions.py b/src/world_engine/conditions.py
index cddf913..27f6596 100644
--- a/src/world_engine/conditions.py
+++ b/src/world_engine/conditions.py
@@ -40,6 +40,7 @@ from sqlmodel import Session, select
 from .condition_forms import (
     _EVALUATORS,
     ANY_SUBJECT_TYPES,
+    HIDDEN_STATE_REASON_FR,
     RequirementSpec,
     Verdict,
     _day_reachable_ids,
@@ -137,9 +138,6 @@ class VerdictNode:
 
 # V2 (AMENDMENT-0111-01): why a leaf about someone else shows `?` to a player.
 UNSEEN_REASON_FR = "le personnage ne peut pas le vérifier"
-# WH1 (TICKET-0113): why a leaf on a hidden attribute shows `?` to a player,
-# even about himself.
-HIDDEN_STATE_REASON_FR = "c'est un état encore caché"
 
 
 def _seen_subject(spec: Optional[RequirementSpec], viewer_id: str) -> bool:
diff --git a/tooling/verify/checks/attribute_conditions.py b/tooling/verify/checks/attribute_conditions.py
index df79f8c..3dfcf28 100644
--- a/tooling/verify/checks/attribute_conditions.py
+++ b/tooling/verify/checks/attribute_conditions.py
@@ -33,7 +33,10 @@ AB4 -- what a player may read (WH1, fixture). A leaf on a hidden attribute
    `blocked_details_fr` and `player_detail_fr` read
    `HIDDEN_STATE_DETAIL_FR`; the creator's `verdict_lines` writes its name
    and value; a leaf on a visible attribute about the PC shows its value
-   and its mark to him.
+   and its mark to him. A hidden attribute his character cannot hold (it
+   applies to locations only), judged on him through `doer`, is `unknown`
+   with `HIDDEN_STATE_REASON_FR`: its name and its label are in none of his
+   `verdict_lines` nor `blocked_details_fr` (AMENDMENT-0113-01).
 AB5 -- migration `scripts/migrate_v2_23_attribute_leaves.py`, on a v2.22
    database holding a `vital_status` leaf (the form as v2.22 stored it):
    at v2.21 it refuses and changes nothing; with a leaf whose value is not
@@ -378,6 +381,28 @@ def check_ab4(engine, ids: dict) -> None:
         shown = verdict_lines(db, visible, viewer_id=pc.id)
         if shown[-1]["mark"] != "✓" or "Maudit" not in shown[-1]["text"]:
             fail(f"AB4: the player reads a visible leaf about himself as {shown}")
+        _ab4_unholdable(db, world, pc)
+
+
+def _ab4_unholdable(db, world: str, pc) -> None:
+    """AMENDMENT-0113-01: a hidden attribute the subject cannot hold."""
+    from world_engine.condition_text import verdict_lines
+    from world_engine.conditions import HIDDEN_STATE_REASON_FR, Bindings, all_of, evaluate
+    from world_engine.day_resolve import blocked_details_fr
+    from world_engine.writes.attributes import write_attribute_definition
+
+    haunted = write_attribute_definition(db, world_id=world, spec=_spec(
+        name="Hanté", holder_types=("location",), choices=("non", "oui"), default="non", is_hidden=True)).id
+    oui = _choice(db, world, haunted, "oui")
+    tree = evaluate(all_of([_leaf(target_key=haunted, value=oui)]), Bindings(doer=pc), db)
+    leaf = tree.children[0]
+    if leaf.state != "unknown" or leaf.reason != HIDDEN_STATE_REASON_FR:
+        fail(f"AB4: an unholdable hidden leaf is {leaf.state} because {leaf.reason!r}")
+    said = " ".join(line["text"] for line in verdict_lines(db, tree, viewer_id=pc.id))
+    said += " " + " ".join(blocked_details_fr(tree, db, pc.id))
+    if "Hanté" in said or "oui" in said:
+        fail(f"AB4: the player reads an unholdable hidden leaf as {said!r}")
+    db.rollback()
 
 
 # --- AB5 -------------------------------------------------------------------------
````

## Touched briefs

- **BRIEF-0113-B** -- not regenerated: this file is its complement. Its
  Done means gain:
  - `attribute_conditions.py` -> PASS (same line).
  - Mutation: in `src/world_engine/condition_forms.py`,
    `        if view.hidden:` -> `        if False:` -> `AB4` (red, then
    reverted). The six earlier mutations still red.
  - `corpus_gate.py`: every check green but `pipeline_state.py`, whose only
    failure is the arrow to `attribute_interpreter.py` (R-23).
- **BRIEF-0113-C** -- unchanged; REPORT-ONLY gains R-23's line (the same
  single `pipeline_state.py` failure). Its diff touches none of the three
  files: it applies unchanged (measured).
- **BRIEF-0113-D, -E** -- unchanged; their diffs apply on top (measured);
  the corpus is green there, `pipeline_state.py` included (measured with
  the ticket in place).
- **BRIEF-0113-A** -- already committed; its « corpus green » was wrong by
  R-23 alone.
- **TICKET-0113** -- one amendment-log row.

## Gate checks re-run

(a) the property trace gains R-22, R-23; (b) b-2 amended; prototype
re-run: `attribute_conditions.py` PASS at B with the change, the new
mutation red; `conditions.py`, `quests.py`, `day_plan.py`,
`condition_interpreter.py`, `attributes.py` PASS at B; the change applied
on the prototype's last commit, `attribute_conditions.py` PASS and
`pipeline_state.py` PASS with TICKET-0113 in `tooling/tickets`.
