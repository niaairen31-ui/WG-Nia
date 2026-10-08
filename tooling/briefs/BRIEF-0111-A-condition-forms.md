<!-- slug: condition-forms -->
# BRIEF 0111-A — "The requirement forms get their own module: a pure move out of day_plan.py"

Lot: LOT-0111-condition-language.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any has moved (on `main` at `2cdc92c` or later).

- `src/world_engine/day_plan.py:87` -> `REQUIREMENT_TYPES: tuple[str, ...] = (`
- `src/world_engine/day_plan.py:120` -> `class RequirementSpec:`
- `src/world_engine/day_plan.py:136` -> `class Verdict:`
- `src/world_engine/day_plan.py:173` -> `def _eval_knowledge(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:`
- `src/world_engine/day_plan.py:375` -> `_EVALUATORS: dict[str, Callable[[RequirementSpec, Character, Session, object], Verdict]] = {`
- `src/world_engine/day_plan.py:389` -> `def _day_reachable_ids(origin_location_id: str, db: Session) -> frozenset[str]:`
- `src/world_engine/day_plan.py:419` -> `def evaluate_specs(`
- `src/world_engine/writes/goals_agendas.py:46` -> `from ..day_plan import (`
- `src/world_engine/day_resolve.py:74` -> `Verdict as RequirementVerdict,`
- `tooling/verify/checks/day_plan.py:173` -> `DAY_PLAN_FILE = SRC / "day_plan.py"`
- `tooling/verify/checks/known_reachability.py:327` -> `"world_engine/day_plan.py",`
- `CLAUDE.md:461` -> `│   ├── day_plan.py          # day-plan emission + budget cut: requirement evaluators, its own BFS`
- No `src/world_engine/condition_forms.py` exists.
- No `tooling/verify/checks/conditions.py` exists.

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

### R-02 — the forms live in `day_plan.py`, which `writes/` imports [M]
Opened: `src/world_engine/day_plan.py:119-148` (`RequirementSpec`,
`PlanStep`, `Verdict`), `:168-441` (the evaluators, `_EVALUATORS`,
`_day_reachable_ids`, `evaluate_specs`); `src/world_engine/writes/goals_agendas.py:46-53`
(`from ..day_plan import ENTITY_TARGET_TYPES, …, PlanStep, RequirementSpec`);
`src/world_engine/condition_forms.py` does not exist.
Finding: `writes/goals_agendas.py` imports FROM `day_plan.py` (the docstring
at `day_plan.py:196-202` names the cycle importing back would create).
Consequence: the tree module must sit below `day_plan.py`; the forms move
first (A) so `conditions.py` imports them and `day_plan.py` imports
`conditions.py`.

### R-03 — who imports the moved names, and which checks read the moved source [M]
Opened (enumeration, pasted in the gate output (c)): every
`from …day_plan import` of a moved name under `src/` and
`tooling/verify/checks/`; the checks that parse `day_plan.py`'s source:
`tooling/verify/checks/day_plan.py:173` (`DAY_PLAN_FILE`), R1
`check_evaluator_bijection` `:295`, R10 `check_no_traversal_reuse` `:533`,
R25 `check_verdict_type_field` `:972`; `tooling/verify/checks/known_reachability.py:327`
(`DOCUMENTED_MODULES` lists `world_engine/day_plan.py` as a `connects_to`
reader; `:349-361` fails on an undocumented module spelling the literal).
Finding: three rules of `day_plan.py` and one of `known_reachability.py`
read the moved source by file; five checks import moved names.
Consequence: A retargets them, unchanged in meaning; the census document
`tooling/tickets/connects-to-readers-TICKET-0082.md:63` (row 12) gets a
note, its row untouched.

### R-21 — the CLAUDE.md file tree has no room for a new line [M]
Opened: `CLAUDE.md:461` (`day_plan.py # … requirement evaluators, its own
BFS`); `tooling/verify/checks/claude_md_contract.py` (File structure at
most 80 lines -- it is at 80; 100 characters per line; 38 000 characters).
Consequence: A and B fold the new modules into `day_plan.py`'s line
(`day_plan.py, condition*.py`), within 100 characters.

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

### C-02 — the form family (`condition_forms`)
Produced by: BRIEF-0111-A (ten forms, moved), BRIEF-0111-C (twelve)   Consumed by: B, C, D
Family contract, written before its members: a form is
1. its name in `REQUIREMENT_TYPES` (order: the model's four, the creator's
   four, the debt two, then `item_held`, `vital_status`);
2. exactly one target group: `ENTITY_TARGET_TYPES` (`target_entity_id`, of
   the type `_TARGET_ENTITY_TYPE` names, `None` = any), `KEY_TARGET_TYPES`
   (`target_key`, resolved by `_clean_target_key`) or `NO_TARGET_TYPES`
   (neither, refused if given);
3. `THRESHOLD_TYPES` membership (a positive integer; `skill_rank_gte` at
   most 5);
4. `FORM_VALUES[form]` when it compares to a value (the value must be one
   of them);
5. an evaluator in `_EVALUATORS`, `(req, character, db, reachable_ids) ->
   Verdict` (`type` first), judging the character it is given;
6. a player-facing detail in `day_resolve._BLOCKED_DETAIL_FR`;
7. a creator-facing phrase in `condition_text.FORM_PHRASES_FR`, and a
   label per value in `condition_text.VALUE_LABELS_FR`;
8. a line in `frontend/src/creation/questRequirements.js`'s
   `REQUIREMENT_FORMS` (`column` `entity`/`key`/`none`, `threshold`,
   `values: true` when 4 applies).
The twelve members (C): `knowledge` (key: a fact), `relation_gte`
(entity, threshold), `resource` (key: a label, threshold), `location_reachable`
(entity), `has_met` (entity), `faction_member` (entity: a faction),
`skill_rank_gte` (key: a skill, threshold 1-5), `quest_state` (key: an
offer, value among `QUEST_STATES = ("open", "completed", "failed",
"abandoned")`), `has_debt_to`, `no_debt_to` (entity: a character or a
faction), `item_held` (entity: an item, threshold), `vital_status` (no
target, value among `VITAL_STATUSES = ("alive", "dead", "missing",
"unknown")`). `MODEL_REQUIREMENT_TYPES` stays the model's four.

## Context

TICKET-0111 turns the flat list of requirements into a language of conditions. The tree (B) needs the forms and `day_plan.py` will need the tree (C): kept in `day_plan.py`, the forms would make the two modules import each other (R-02). This brief moves them, unchanged, to `condition_forms.py`, and creates the check `conditions.py` that grows brief after brief. No behaviour changes.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. `tooling/standards/DECISIONS_INDEX.md` is not in the
diff: regenerate it as listed.

1. Apply the embedded diff. It:
   - creates `src/world_engine/condition_forms.py` with the moved names of C-01 and C-02 (ten forms), `_entity_name`, `_open_debt`, `_day_reachable_ids` and `evaluate_specs`, unchanged;
   - removes them from `day_plan.py`; every importer of a moved name names the new home (enumeration (c) 1 of the lot); nothing is re-exported from `day_plan.py`;
   - retargets `day_plan.py` R1, R10, R25 and `known_reachability.py` to the new file, and the five checks that import moved names;
   - notes the move in `tooling/tickets/connects-to-readers-TICKET-0082.md` (row 12 untouched) and folds the module into `day_plan.py`'s line of CLAUDE.md's File structure;
   - creates `tooling/verify/checks/conditions.py` with CA1;
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - CLAUDE.md
   - src/world_engine/cockpit/routes/quests.py
   - src/world_engine/condition_forms.py
   - src/world_engine/day_plan.py
   - src/world_engine/day_resolve.py
   - src/world_engine/models/config.py
   - src/world_engine/models/quests.py
   - src/world_engine/writes/goals_agendas.py
   - src/world_engine/writes/quests.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/tickets/connects-to-readers-TICKET-0082.md
   - tooling/verify/checks/conditions.py
   - tooling/verify/checks/day_narration.py
   - tooling/verify/checks/day_plan.py
   - tooling/verify/checks/debts.py
   - tooling/verify/checks/knowledge_identity.py
   - tooling/verify/checks/known_reachability.py
   - tooling/verify/checks/quests.py
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `refactor(conditions): the requirement forms move to condition_forms.py, unchanged (BRIEF-0111-a)`.

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index 8069681..0c96a0f 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -458,7 +458,7 @@ WG-Nia/
 │   ├── observation_*.py     # observed-lane socle/engine/runner/reads/writes; per-NPC window
 │   ├── resolution.py, ledger.py  # physical-action dice resolution (2d6 bands); ledger read helpers
 │   ├── skill_lexicon.py     # action lexicon: judge/record; Play calls it, never clamps inline
-│   ├── day_plan.py          # day-plan emission + budget cut: requirement evaluators, its own BFS
+│   ├── day_plan.py, condition_forms.py  # day-plan emission + budget cut; requirement forms, BFS
 │   ├── day_extract.py       # day extraction: 3 passes (place/person/faction), never sees registry
 │   ├── day_concordance.py   # day mention resolution: matching rungs, germ emission; never authors
 │   ├── day_rewrite.py       # declaration rewrite: render/resolutions/load_latest, no model call
diff --git a/src/world_engine/cockpit/routes/quests.py b/src/world_engine/cockpit/routes/quests.py
index b33d98b..d805dfb 100644
--- a/src/world_engine/cockpit/routes/quests.py
+++ b/src/world_engine/cockpit/routes/quests.py
@@ -31,7 +31,8 @@ from pydantic import BaseModel, Field
 from sqlmodel import Session, select
 
 from ... import quest_reads
-from ...day_plan import PlanStep, RequirementSpec
+from ...condition_forms import RequirementSpec
+from ...day_plan import PlanStep
 from ...db import get_session
 from ...models import Quest, QuestEconomy, QuestOffer
 from ...quest_value import DEFAULT_RATES, offer_value, value_dict, world_rates
diff --git a/src/world_engine/condition_forms.py b/src/world_engine/condition_forms.py
new file mode 100644
index 0000000..b431359
--- /dev/null
+++ b/src/world_engine/condition_forms.py
@@ -0,0 +1,381 @@
+"""The requirement forms: the leaves of the condition language, each with
+its evaluator (TICKET-0111, BRIEF-0111-A -- a pure move out of `day_plan.py`,
+which keeps the plan emission and the budget cut; decisions S1 of TICKET-0075,
+C-01 of TICKET-0108, G1 of TICKET-0110 unchanged).
+
+Every form judges ONE character against the canon and returns a `Verdict`;
+`_EVALUATORS` maps each form of `REQUIREMENT_TYPES` to its evaluator, and
+`evaluate_specs` judges a flat list of them. This module writes nothing.
+
+`_day_reachable_ids` is a NEW, day-local `connects_to` BFS reader, not a
+reuse of an existing one. The original brief instructed "reuse the existing
+traversal; do not write a second one" — that instruction was wrong: it
+contradicted decision D1 (BRIEF-19), standing project doctrine that each new
+`connects_to` consumer gets its OWN reader (a real dedup opportunity is
+REPORTED, never acted on). Claude Code escalated under the brief's own STOP
+condition rather than guess; Nia's correction is
+`tooling/briefs/BRIEF-0075-b-amendment-1-location-reachable-reader.md`. Per
+that amendment's count, this is roughly the SEVENTH independent
+`connects_to` reader in the tree — `_location_neighbours`
+(`cockpit/play.py:854`, direct neighbours only) and `_reachable_locations`
+(`tick_context.py:405`, interval-hop-bounded, origin EXCLUDED) are the two
+closest siblings, and `_day_reachable_ids` is deliberately NOT shared with
+either: unbounded (a day has no meaningful hop radius) and origin-INCLUSIVE
+(the player is already there, which satisfies reachability) — a concrete
+shape difference, not only a doctrinal one.
+
+`_day_reachable_ids` proves a path exists in the `connects_to` graph; it does
+NOT prove the Play surface's door/travel gate would let the player walk it
+today. Harmless now (the day chain resolves travel abstractly — Play is
+sealed, TICKET-0061), and worth a fresh look only if a future ticket ever
+routes a day step through Play.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Callable, Optional
+
+from sqlmodel import Session, func, select
+
+from .models import (
+    Agenda,
+    Character,
+    Debt,
+    Entity,
+    Fact,
+    FactionMembership,
+    Knowledge,
+    Ledger,
+    Quest,
+    QuestOffer,
+    Relation,
+    Rencontre,
+)
+from .prose_render import fact_text
+from .relation_orientation import is_social
+from .skill_access import held_rank, skill_label
+
+# S1: the closed requirement vocabulary, each form with a named evaluator.
+# Eight forms since v2.17 (TICKET-0108, BRIEF-0108-A, C-01): the four the
+# day-plan model may emit, then four only the creator authors (quest offers).
+# Ten since v2.19 (TICKET-0110, BRIEF-0110-A, G1): `has_debt_to` and
+# `no_debt_to`, creator only as well.
+REQUIREMENT_TYPES: tuple[str, ...] = (
+    "knowledge", "relation_gte", "resource", "location_reachable",
+    "has_met", "faction_member", "skill_rank_gte", "quest_completed",
+    "has_debt_to", "no_debt_to",
+)
+
+# What `emit_plan`'s parser accepts from the model (TICKET-0108): the four
+# forms it always could. A creator-only form in a model's plan is a parse
+# failure, never a row.
+MODEL_REQUIREMENT_TYPES: tuple[str, ...] = ("knowledge", "relation_gte", "resource", "location_reachable")
+
+# The shape of each form, the three groups of the `*_requirement_shape`
+# CHECK (C-01): which column names its target, and which need a threshold.
+ENTITY_TARGET_TYPES: tuple[str, ...] = (
+    "relation_gte", "location_reachable", "has_met", "faction_member", "has_debt_to", "no_debt_to",
+)
+KEY_TARGET_TYPES: tuple[str, ...] = ("knowledge", "resource", "skill_rank_gte", "quest_completed")
+THRESHOLD_TYPES: tuple[str, ...] = ("relation_gte", "resource", "skill_rank_gte")
+
+
+@dataclass(frozen=True)
+class RequirementSpec:
+    type: str
+    target_entity_id: Optional[str] = None
+    target_key: Optional[str] = None
+    threshold: Optional[int] = None
+
+
+
+@dataclass(frozen=True)
+class Verdict:
+    # `type` FIRST (BRIEF-0078-a, Scope IN item 3): a positional
+    # `Verdict(...)` construction anywhere in the tree now fails loudly
+    # (wrong type in the wrong slot) rather than silently shifting fields.
+    type: str
+    met: bool
+    current: object
+    required: object
+    reason: str
+    # TICKET-0097: the player-facing text of `required` when it is an id
+    # (a `knowledge` gate's fact); None when `required` is already readable.
+    required_label: Optional[str] = None
+
+
+
+# ── requirement evaluators (S1) ──────────────────────────────────────────────
+# Uniform 4-arg signature (`_SOURCE_LOOKUPS` precedent, schedule_reads.py):
+# every evaluator accepts `reachable_ids`, even the three that ignore it —
+# keeps `_EVALUATORS` directly callable without a special case.
+
+def _eval_knowledge(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """`target_key` is a fact id (TICKET-0097, D1'a): met iff the character
+    holds a row on that fact."""
+    del reachable_ids
+    row = db.exec(
+        select(Knowledge).where(
+            Knowledge.entity_id == character.id, Knowledge.fact_id == req.target_key,
+        )
+    ).first()
+    met = row is not None
+    fact = db.get(Fact, req.target_key) if req.target_key else None
+    label = fact_text(db, fact) if fact is not None else req.target_key
+    reason = (
+        f"knowledge {label!r} already held" if met
+        else f"prerequisite not met — knowledge {label!r} not held"
+    )
+    return Verdict(
+        type=req.type, met=met, current=("held" if met else "unheld"), required=req.target_key, reason=reason,
+        required_label=label,
+    )
+
+
+def _eval_relation_gte(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """What the TARGET feels toward the character (TICKET-0108, B-dir): the
+    social row `entity_a = target`, `entity_b = character`, `is_social`;
+    0 when there is none. A deliberate duplicate of
+    `writes.relations._find_perceived_relation`'s query (perceiver = the
+    target), not an import: writes/goals_agendas.py imports FROM this module,
+    so importing FROM writes/ here would cycle the package. The reverse row
+    (the character's own feeling) and the structural types are never read."""
+    del reachable_ids
+    rows = db.exec(
+        select(Relation).where(
+            Relation.entity_a_id == req.target_entity_id, Relation.entity_b_id == character.id,
+        )
+    ).all()
+    rel = next((row for row in rows if is_social(row.type)), None)
+    current = rel.intensity if rel else 0
+    threshold = req.threshold or 0
+    met = current >= threshold
+    target = db.get(Entity, req.target_entity_id)
+    target_name = target.name if target else req.target_entity_id
+    reason = (
+        f"relation of {target_name} toward the character is {current}, meets requires >= {threshold}" if met
+        else f"prerequisite not met — relation of {target_name} toward the character is {current}, "
+        f"requires >= {threshold}"
+    )
+    return Verdict(
+        type=req.type, met=met, current=current, required=threshold, reason=reason,
+        required_label=target_name,
+    )
+
+
+def _eval_resource(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """Money: the character's ledger balance. A world has one currency (the
+    `ledger` has no currency column), so `target_key` is a label and is not
+    read; an object is never a `resource` (TICKET-0108, E1: objects held in
+    quantity come with `item_holding`)."""
+    del reachable_ids
+    total = db.exec(select(func.sum(Ledger.amount)).where(Ledger.entity_id == character.id)).first() or 0
+    threshold = req.threshold or 0
+    met = total >= threshold
+    reason = (
+        f"resource {req.target_key!r} balance is {total}, meets requires >= {threshold}" if met
+        else f"prerequisite not met — resource {req.target_key!r} balance is {total}, requires >= {threshold}"
+    )
+    return Verdict(type=req.type, met=met, current=total, required=threshold, reason=reason)
+
+
+def _eval_location_reachable(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    ids = reachable_ids or frozenset()
+    met = req.target_entity_id in ids
+    target = db.get(Entity, req.target_entity_id)
+    target_name = target.name if target else req.target_entity_id
+    reason = (
+        f"{target_name} is reachable" if met
+        else f"prerequisite not met — {target_name} is not reachable from the current location"
+    )
+    return Verdict(
+        type=req.type, met=met, current=character.current_location_id,
+        required=req.target_entity_id, reason=reason,
+    )
+
+
+def _entity_name(db: Session, entity_id: Optional[str]) -> str:
+    entity = db.get(Entity, entity_id) if entity_id else None
+    return entity.name if entity is not None else str(entity_id)
+
+
+def _eval_has_met(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """The character and the target have an encounter row (`rencontre`, one
+    row per unordered pair, `entity_lo_id < entity_hi_id`)."""
+    del reachable_ids
+    low, high = sorted((character.id, req.target_entity_id))
+    row = db.exec(
+        select(Rencontre).where(Rencontre.entity_lo_id == low, Rencontre.entity_hi_id == high)
+    ).first()
+    met = row is not None
+    name = _entity_name(db, req.target_entity_id)
+    reason = f"has met {name}" if met else f"prerequisite not met — has not met {name}"
+    return Verdict(
+        type=req.type, met=met, current=("met" if met else "not met"), required=req.target_entity_id,
+        reason=reason, required_label=name,
+    )
+
+
+def _eval_faction_member(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """The character holds an ACTIVE membership (`left_at IS NULL`) of the
+    target faction. A secret membership counts: it is the character's own
+    (the `tick_context` self-briefing precedent); secrecy hides it from
+    others, not from the gate."""
+    del reachable_ids
+    row = db.exec(
+        select(FactionMembership).where(
+            FactionMembership.entity_id == character.id,
+            FactionMembership.faction_id == req.target_entity_id,
+            FactionMembership.left_at.is_(None),
+        )
+    ).first()
+    met = row is not None
+    name = _entity_name(db, req.target_entity_id)
+    reason = f"member of {name}" if met else f"prerequisite not met — not a member of {name}"
+    return Verdict(
+        type=req.type, met=met, current=("member" if met else "not a member"), required=req.target_entity_id,
+        reason=reason, required_label=name,
+    )
+
+
+def _eval_skill_rank_gte(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """`target_key` is a base domain or a skill definition id; the rank held
+    is `skill_access.held_rank` (a missing base row is Initié, a missing
+    definition row is not held)."""
+    del reachable_ids
+    rank = held_rank(db, character.id, req.target_key)
+    threshold = req.threshold or 0
+    met = rank is not None and rank >= threshold
+    label = skill_label(db, req.target_key)
+    current = rank if rank is not None else "not held"
+    reason = (
+        f"skill {label!r} at rank {rank}, meets requires >= {threshold}" if met
+        else f"prerequisite not met — skill {label!r} is {current}, requires rank >= {threshold}"
+    )
+    return Verdict(
+        type=req.type, met=met, current=current, required=threshold, reason=reason, required_label=label,
+    )
+
+
+def _eval_quest_completed(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """`target_key` is a quest offer id: met iff a quest the character took
+    from that offer has its agenda `completed` (M1: a quest's state is its
+    agenda's)."""
+    del reachable_ids
+    row = db.exec(
+        select(Quest.id)
+        .join(Agenda, Agenda.id == Quest.agenda_id)
+        .where(
+            Quest.character_id == character.id, Quest.offer_id == req.target_key,
+            Agenda.status == "completed",
+        )
+    ).first()
+    met = row is not None
+    offer = db.get(QuestOffer, req.target_key) if req.target_key else None
+    label = offer.title if offer is not None else str(req.target_key)
+    reason = f"quest {label!r} completed" if met else f"prerequisite not met — quest {label!r} not completed"
+    return Verdict(
+        type=req.type, met=met, current=("completed" if met else "not completed"), required=req.target_key,
+        reason=reason, required_label=label,
+    )
+
+
+def _open_debt(db: Session, debtor_id: str, creditor_id: Optional[str]) -> bool:
+    return db.exec(select(Debt.id).where(
+        Debt.debtor_entity_id == debtor_id, Debt.creditor_entity_id == creditor_id, Debt.status == "open",
+    )).first() is not None
+
+
+def _eval_has_debt_to(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """TICKET-0110 (G1): the character owes the target (a character or a
+    faction) at least one OPEN debt -- one he is the debtor of; existence
+    only, no amount. A settled or forgiven debt is not owed."""
+    del reachable_ids
+    met = _open_debt(db, character.id, req.target_entity_id)
+    name = _entity_name(db, req.target_entity_id)
+    reason = f"owes {name}" if met else f"prerequisite not met — owes {name} nothing"
+    return Verdict(
+        type=req.type, met=met, current=("owes" if met else "owes nothing"), required=req.target_entity_id,
+        reason=reason, required_label=name,
+    )
+
+
+def _eval_no_debt_to(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """TICKET-0110 (G1): the exact negation of `has_debt_to`."""
+    del reachable_ids
+    owes = _open_debt(db, character.id, req.target_entity_id)
+    name = _entity_name(db, req.target_entity_id)
+    reason = f"prerequisite not met — still owes {name}" if owes else f"owes {name} nothing"
+    return Verdict(
+        type=req.type, met=not owes, current=("owes" if owes else "owes nothing"), required=req.target_entity_id,
+        reason=reason, required_label=name,
+    )
+
+
+_EVALUATORS: dict[str, Callable[[RequirementSpec, Character, Session, object], Verdict]] = {
+    "knowledge": _eval_knowledge,
+    "relation_gte": _eval_relation_gte,
+    "resource": _eval_resource,
+    "location_reachable": _eval_location_reachable,
+    "has_met": _eval_has_met,
+    "faction_member": _eval_faction_member,
+    "skill_rank_gte": _eval_skill_rank_gte,
+    "quest_completed": _eval_quest_completed,
+    "has_debt_to": _eval_has_debt_to,
+    "no_debt_to": _eval_no_debt_to,
+}
+
+
+def _day_reachable_ids(origin_location_id: str, db: Session) -> frozenset[str]:
+    """A NEW, day-local `connects_to` BFS reader (decision D1, BRIEF-19) —
+    see the module docstring for the escalation this corrects. Unbounded
+    (the origin's whole connected component of ACTIVE locations), origin
+    INCLUDED, both `connects_to` column orders. Returns bare ids —
+    `evaluate_requirements` needs membership only, nothing else."""
+    visited: set[str] = {origin_location_id}
+    frontier = [origin_location_id]
+    while frontier:
+        next_frontier: list[str] = []
+        for loc_id in frontier:
+            rows = db.exec(
+                select(Relation).where(
+                    Relation.type == "connects_to",
+                    (Relation.entity_a_id == loc_id) | (Relation.entity_b_id == loc_id),
+                )
+            ).all()
+            for rel in rows:
+                other_id = rel.entity_b_id if rel.entity_a_id == loc_id else rel.entity_a_id
+                if other_id in visited:
+                    continue
+                other = db.get(Entity, other_id)
+                if other is None or other.type != "location" or other.status != "active":
+                    continue
+                visited.add(other_id)
+                next_frontier.append(other_id)
+        frontier = next_frontier
+    return frozenset(visited)
+
+
+def evaluate_specs(
+    requirements: tuple[RequirementSpec, ...], character: Character, db: Session,
+) -> list[Verdict]:
+    """Judge each requirement against `character`'s current state (C-02).
+    Dispatches through `_EVALUATORS`; an unknown `type` raises fail-closed —
+    it cannot happen through the DB (the CHECK forbids it), the branch exists
+    so that widening `REQUIREMENT_TYPES` without adding an evaluator fails
+    loudly. Shared by a step (`evaluate_requirements`) and a quest offer's
+    eligibility (`quest_reads`), so both are one judgment.
+
+    `_day_reachable_ids` is computed AT MOST ONCE per call, only if a
+    `location_reachable` requirement is present — never per requirement."""
+    needs_reachable = any(r.type == "location_reachable" for r in requirements)
+    reachable_ids = _day_reachable_ids(character.current_location_id, db) if needs_reachable else None
+
+    verdicts: list[Verdict] = []
+    for req in requirements:
+        evaluator = _EVALUATORS.get(req.type)
+        if evaluator is None:
+            raise ValueError(f"unknown requirement type {req.type!r}")
+        verdicts.append(evaluator(req, character, db, reachable_ids))
+    return verdicts
diff --git a/src/world_engine/day_plan.py b/src/world_engine/day_plan.py
index 680db1c..3e7d498 100644
--- a/src/world_engine/day_plan.py
+++ b/src/world_engine/day_plan.py
@@ -3,74 +3,43 @@ plan-emission-and-budget step; decisions F1, M1, P2, S1, H1).
 
 One model call (`emit_plan`) turns a player's day declaration into a full,
 ordered step list — the model PROPOSES. Everything downstream is Python: the
-named requirement evaluators judge each step's preconditions, and
-`budget_cut` (pure, sequential, not a knapsack) decides how much of the plan
-happens today against `DAY_BUDGET_SLOTS`. This module authors no prose and
-emits no `proposed_mutation` — persistence is `writes.write_day_plan`.
+named requirement evaluators (`condition_forms.py` since TICKET-0111,
+BRIEF-0111-A) judge each step's preconditions, and `budget_cut` (pure,
+sequential, not a knapsack) decides how much of the plan happens today
+against `DAY_BUDGET_SLOTS`. This module authors no prose and emits no
+`proposed_mutation` — persistence is `writes.write_day_plan`.
 
 THE POSITIONAL WALL (BRIEF-0074-a-amendment-1) holds here too: no function in
 this module reads the world's stored day-cycle phase (P2 — every day gets
 the full budget), and `location_reachable`'s target is a precondition on the
 PLAYER, never a position of an NPC.
-
-`_day_reachable_ids` is a NEW, day-local `connects_to` BFS reader, not a
-reuse of an existing one. The original brief instructed "reuse the existing
-traversal; do not write a second one" — that instruction was wrong: it
-contradicted decision D1 (BRIEF-19), standing project doctrine that each new
-`connects_to` consumer gets its OWN reader (a real dedup opportunity is
-REPORTED, never acted on). Claude Code escalated under the brief's own STOP
-condition rather than guess; Nia's correction is
-`tooling/briefs/BRIEF-0075-b-amendment-1-location-reachable-reader.md`. Per
-that amendment's count, this is roughly the SEVENTH independent
-`connects_to` reader in the tree — `_location_neighbours`
-(`cockpit/play.py:854`, direct neighbours only) and `_reachable_locations`
-(`tick_context.py:405`, interval-hop-bounded, origin EXCLUDED) are the two
-closest siblings, and `_day_reachable_ids` is deliberately NOT shared with
-either: unbounded (a day has no meaningful hop radius) and origin-INCLUSIVE
-(the player is already there, which satisfies reachability) — a concrete
-shape difference, not only a doctrinal one.
-
-`_day_reachable_ids` proves a path exists in the `connects_to` graph; it does
-NOT prove the Play surface's door/travel gate would let the player walk it
-today. Harmless now (the day chain resolves travel abstractly — Play is
-sealed, TICKET-0061), and worth a fresh look only if a future ticket ever
-routes a day step through Play.
 """
 
 from __future__ import annotations
 
 import logging
 from dataclasses import dataclass, field, replace
-from typing import Callable, Optional
+from typing import Optional
 
-from sqlmodel import Session, func, select
+from sqlmodel import Session, select
 
 from . import llm_parse, ollama_client
+from .condition_forms import MODEL_REQUIREMENT_TYPES, RequirementSpec, Verdict, evaluate_specs
 from .fact_refs import CodedFacts, code_facts
 from .models import (
     BASE_SKILL_DOMAINS,
     SCHEDULE_PHASES,
-    Agenda,
     AgendaStep,
     AgendaStepRequirement,
     Character,
-    Debt,
     Entity,
     Fact,
-    FactionMembership,
     Knowledge,
-    Ledger,
     PromptTemplate,
-    Quest,
-    QuestOffer,
-    Relation,
-    Rencontre,
 )
 from .prompt_registry import effective_model
 from .prompt_store import current_prompt
-from .prose_render import fact_text, fact_texts
-from .relation_orientation import is_social
-from .skill_access import held_rank, skill_label
+from .prose_render import fact_texts
 
 _log = logging.getLogger(__name__)
 
@@ -79,29 +48,6 @@ _log = logging.getLogger(__name__)
 # as a literal.
 DAY_BUDGET_SLOTS: int = len(SCHEDULE_PHASES)
 
-# S1: the closed requirement vocabulary, each form with a named evaluator.
-# Eight forms since v2.17 (TICKET-0108, BRIEF-0108-A, C-01): the four the
-# day-plan model may emit, then four only the creator authors (quest offers).
-# Ten since v2.19 (TICKET-0110, BRIEF-0110-A, G1): `has_debt_to` and
-# `no_debt_to`, creator only as well.
-REQUIREMENT_TYPES: tuple[str, ...] = (
-    "knowledge", "relation_gte", "resource", "location_reachable",
-    "has_met", "faction_member", "skill_rank_gte", "quest_completed",
-    "has_debt_to", "no_debt_to",
-)
-
-# What `emit_plan`'s parser accepts from the model (TICKET-0108): the four
-# forms it always could. A creator-only form in a model's plan is a parse
-# failure, never a row.
-MODEL_REQUIREMENT_TYPES: tuple[str, ...] = ("knowledge", "relation_gte", "resource", "location_reachable")
-
-# The shape of each form, the three groups of the `*_requirement_shape`
-# CHECK (C-01): which column names its target, and which need a threshold.
-ENTITY_TARGET_TYPES: tuple[str, ...] = (
-    "relation_gte", "location_reachable", "has_met", "faction_member", "has_debt_to", "no_debt_to",
-)
-KEY_TARGET_TYPES: tuple[str, ...] = ("knowledge", "resource", "skill_rank_gte", "quest_completed")
-THRESHOLD_TYPES: tuple[str, ...] = ("relation_gte", "resource", "skill_rank_gte")
 
 # Emission bound (Scope IN item 4). Anything beyond is truncated with a
 # reported count (logged), not silently dropped.
@@ -116,14 +62,6 @@ MAX_LEARNABLE_FACTS_SHOWN: int = 40
 DAY_PLAN_OPTIONS: dict = {"repeat_penalty": 1.1, "repeat_last_n": 128}
 
 
-@dataclass(frozen=True)
-class RequirementSpec:
-    type: str
-    target_entity_id: Optional[str] = None
-    target_key: Optional[str] = None
-    threshold: Optional[int] = None
-
-
 @dataclass(frozen=True)
 class PlanStep:
     objective: str
@@ -132,21 +70,6 @@ class PlanStep:
     requirements: tuple[RequirementSpec, ...] = field(default_factory=tuple)
 
 
-@dataclass(frozen=True)
-class Verdict:
-    # `type` FIRST (BRIEF-0078-a, Scope IN item 3): a positional
-    # `Verdict(...)` construction anywhere in the tree now fails loudly
-    # (wrong type in the wrong slot) rather than silently shifting fields.
-    type: str
-    met: bool
-    current: object
-    required: object
-    reason: str
-    # TICKET-0097: the player-facing text of `required` when it is an id
-    # (a `knowledge` gate's fact); None when `required` is already readable.
-    required_label: Optional[str] = None
-
-
 @dataclass(frozen=True)
 class EvaluatedStep:
     step: PlanStep
@@ -165,281 +88,6 @@ class BudgetResult:
     first_excluded_index: Optional[int]
 
 
-# ── requirement evaluators (S1) ──────────────────────────────────────────────
-# Uniform 4-arg signature (`_SOURCE_LOOKUPS` precedent, schedule_reads.py):
-# every evaluator accepts `reachable_ids`, even the three that ignore it —
-# keeps `_EVALUATORS` directly callable without a special case.
-
-def _eval_knowledge(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
-    """`target_key` is a fact id (TICKET-0097, D1'a): met iff the character
-    holds a row on that fact."""
-    del reachable_ids
-    row = db.exec(
-        select(Knowledge).where(
-            Knowledge.entity_id == character.id, Knowledge.fact_id == req.target_key,
-        )
-    ).first()
-    met = row is not None
-    fact = db.get(Fact, req.target_key) if req.target_key else None
-    label = fact_text(db, fact) if fact is not None else req.target_key
-    reason = (
-        f"knowledge {label!r} already held" if met
-        else f"prerequisite not met — knowledge {label!r} not held"
-    )
-    return Verdict(
-        type=req.type, met=met, current=("held" if met else "unheld"), required=req.target_key, reason=reason,
-        required_label=label,
-    )
-
-
-def _eval_relation_gte(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
-    """What the TARGET feels toward the character (TICKET-0108, B-dir): the
-    social row `entity_a = target`, `entity_b = character`, `is_social`;
-    0 when there is none. A deliberate duplicate of
-    `writes.relations._find_perceived_relation`'s query (perceiver = the
-    target), not an import: writes/goals_agendas.py imports FROM this module,
-    so importing FROM writes/ here would cycle the package. The reverse row
-    (the character's own feeling) and the structural types are never read."""
-    del reachable_ids
-    rows = db.exec(
-        select(Relation).where(
-            Relation.entity_a_id == req.target_entity_id, Relation.entity_b_id == character.id,
-        )
-    ).all()
-    rel = next((row for row in rows if is_social(row.type)), None)
-    current = rel.intensity if rel else 0
-    threshold = req.threshold or 0
-    met = current >= threshold
-    target = db.get(Entity, req.target_entity_id)
-    target_name = target.name if target else req.target_entity_id
-    reason = (
-        f"relation of {target_name} toward the character is {current}, meets requires >= {threshold}" if met
-        else f"prerequisite not met — relation of {target_name} toward the character is {current}, "
-        f"requires >= {threshold}"
-    )
-    return Verdict(
-        type=req.type, met=met, current=current, required=threshold, reason=reason,
-        required_label=target_name,
-    )
-
-
-def _eval_resource(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
-    """Money: the character's ledger balance. A world has one currency (the
-    `ledger` has no currency column), so `target_key` is a label and is not
-    read; an object is never a `resource` (TICKET-0108, E1: objects held in
-    quantity come with `item_holding`)."""
-    del reachable_ids
-    total = db.exec(select(func.sum(Ledger.amount)).where(Ledger.entity_id == character.id)).first() or 0
-    threshold = req.threshold or 0
-    met = total >= threshold
-    reason = (
-        f"resource {req.target_key!r} balance is {total}, meets requires >= {threshold}" if met
-        else f"prerequisite not met — resource {req.target_key!r} balance is {total}, requires >= {threshold}"
-    )
-    return Verdict(type=req.type, met=met, current=total, required=threshold, reason=reason)
-
-
-def _eval_location_reachable(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
-    ids = reachable_ids or frozenset()
-    met = req.target_entity_id in ids
-    target = db.get(Entity, req.target_entity_id)
-    target_name = target.name if target else req.target_entity_id
-    reason = (
-        f"{target_name} is reachable" if met
-        else f"prerequisite not met — {target_name} is not reachable from the current location"
-    )
-    return Verdict(
-        type=req.type, met=met, current=character.current_location_id,
-        required=req.target_entity_id, reason=reason,
-    )
-
-
-def _entity_name(db: Session, entity_id: Optional[str]) -> str:
-    entity = db.get(Entity, entity_id) if entity_id else None
-    return entity.name if entity is not None else str(entity_id)
-
-
-def _eval_has_met(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
-    """The character and the target have an encounter row (`rencontre`, one
-    row per unordered pair, `entity_lo_id < entity_hi_id`)."""
-    del reachable_ids
-    low, high = sorted((character.id, req.target_entity_id))
-    row = db.exec(
-        select(Rencontre).where(Rencontre.entity_lo_id == low, Rencontre.entity_hi_id == high)
-    ).first()
-    met = row is not None
-    name = _entity_name(db, req.target_entity_id)
-    reason = f"has met {name}" if met else f"prerequisite not met — has not met {name}"
-    return Verdict(
-        type=req.type, met=met, current=("met" if met else "not met"), required=req.target_entity_id,
-        reason=reason, required_label=name,
-    )
-
-
-def _eval_faction_member(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
-    """The character holds an ACTIVE membership (`left_at IS NULL`) of the
-    target faction. A secret membership counts: it is the character's own
-    (the `tick_context` self-briefing precedent); secrecy hides it from
-    others, not from the gate."""
-    del reachable_ids
-    row = db.exec(
-        select(FactionMembership).where(
-            FactionMembership.entity_id == character.id,
-            FactionMembership.faction_id == req.target_entity_id,
-            FactionMembership.left_at.is_(None),
-        )
-    ).first()
-    met = row is not None
-    name = _entity_name(db, req.target_entity_id)
-    reason = f"member of {name}" if met else f"prerequisite not met — not a member of {name}"
-    return Verdict(
-        type=req.type, met=met, current=("member" if met else "not a member"), required=req.target_entity_id,
-        reason=reason, required_label=name,
-    )
-
-
-def _eval_skill_rank_gte(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
-    """`target_key` is a base domain or a skill definition id; the rank held
-    is `skill_access.held_rank` (a missing base row is Initié, a missing
-    definition row is not held)."""
-    del reachable_ids
-    rank = held_rank(db, character.id, req.target_key)
-    threshold = req.threshold or 0
-    met = rank is not None and rank >= threshold
-    label = skill_label(db, req.target_key)
-    current = rank if rank is not None else "not held"
-    reason = (
-        f"skill {label!r} at rank {rank}, meets requires >= {threshold}" if met
-        else f"prerequisite not met — skill {label!r} is {current}, requires rank >= {threshold}"
-    )
-    return Verdict(
-        type=req.type, met=met, current=current, required=threshold, reason=reason, required_label=label,
-    )
-
-
-def _eval_quest_completed(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
-    """`target_key` is a quest offer id: met iff a quest the character took
-    from that offer has its agenda `completed` (M1: a quest's state is its
-    agenda's)."""
-    del reachable_ids
-    row = db.exec(
-        select(Quest.id)
-        .join(Agenda, Agenda.id == Quest.agenda_id)
-        .where(
-            Quest.character_id == character.id, Quest.offer_id == req.target_key,
-            Agenda.status == "completed",
-        )
-    ).first()
-    met = row is not None
-    offer = db.get(QuestOffer, req.target_key) if req.target_key else None
-    label = offer.title if offer is not None else str(req.target_key)
-    reason = f"quest {label!r} completed" if met else f"prerequisite not met — quest {label!r} not completed"
-    return Verdict(
-        type=req.type, met=met, current=("completed" if met else "not completed"), required=req.target_key,
-        reason=reason, required_label=label,
-    )
-
-
-def _open_debt(db: Session, debtor_id: str, creditor_id: Optional[str]) -> bool:
-    return db.exec(select(Debt.id).where(
-        Debt.debtor_entity_id == debtor_id, Debt.creditor_entity_id == creditor_id, Debt.status == "open",
-    )).first() is not None
-
-
-def _eval_has_debt_to(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
-    """TICKET-0110 (G1): the character owes the target (a character or a
-    faction) at least one OPEN debt -- one he is the debtor of; existence
-    only, no amount. A settled or forgiven debt is not owed."""
-    del reachable_ids
-    met = _open_debt(db, character.id, req.target_entity_id)
-    name = _entity_name(db, req.target_entity_id)
-    reason = f"owes {name}" if met else f"prerequisite not met — owes {name} nothing"
-    return Verdict(
-        type=req.type, met=met, current=("owes" if met else "owes nothing"), required=req.target_entity_id,
-        reason=reason, required_label=name,
-    )
-
-
-def _eval_no_debt_to(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
-    """TICKET-0110 (G1): the exact negation of `has_debt_to`."""
-    del reachable_ids
-    owes = _open_debt(db, character.id, req.target_entity_id)
-    name = _entity_name(db, req.target_entity_id)
-    reason = f"prerequisite not met — still owes {name}" if owes else f"owes {name} nothing"
-    return Verdict(
-        type=req.type, met=not owes, current=("owes" if owes else "owes nothing"), required=req.target_entity_id,
-        reason=reason, required_label=name,
-    )
-
-
-_EVALUATORS: dict[str, Callable[[RequirementSpec, Character, Session, object], Verdict]] = {
-    "knowledge": _eval_knowledge,
-    "relation_gte": _eval_relation_gte,
-    "resource": _eval_resource,
-    "location_reachable": _eval_location_reachable,
-    "has_met": _eval_has_met,
-    "faction_member": _eval_faction_member,
-    "skill_rank_gte": _eval_skill_rank_gte,
-    "quest_completed": _eval_quest_completed,
-    "has_debt_to": _eval_has_debt_to,
-    "no_debt_to": _eval_no_debt_to,
-}
-
-
-def _day_reachable_ids(origin_location_id: str, db: Session) -> frozenset[str]:
-    """A NEW, day-local `connects_to` BFS reader (decision D1, BRIEF-19) —
-    see the module docstring for the escalation this corrects. Unbounded
-    (the origin's whole connected component of ACTIVE locations), origin
-    INCLUDED, both `connects_to` column orders. Returns bare ids —
-    `evaluate_requirements` needs membership only, nothing else."""
-    visited: set[str] = {origin_location_id}
-    frontier = [origin_location_id]
-    while frontier:
-        next_frontier: list[str] = []
-        for loc_id in frontier:
-            rows = db.exec(
-                select(Relation).where(
-                    Relation.type == "connects_to",
-                    (Relation.entity_a_id == loc_id) | (Relation.entity_b_id == loc_id),
-                )
-            ).all()
-            for rel in rows:
-                other_id = rel.entity_b_id if rel.entity_a_id == loc_id else rel.entity_a_id
-                if other_id in visited:
-                    continue
-                other = db.get(Entity, other_id)
-                if other is None or other.type != "location" or other.status != "active":
-                    continue
-                visited.add(other_id)
-                next_frontier.append(other_id)
-        frontier = next_frontier
-    return frozenset(visited)
-
-
-def evaluate_specs(
-    requirements: tuple[RequirementSpec, ...], character: Character, db: Session,
-) -> list[Verdict]:
-    """Judge each requirement against `character`'s current state (C-02).
-    Dispatches through `_EVALUATORS`; an unknown `type` raises fail-closed —
-    it cannot happen through the DB (the CHECK forbids it), the branch exists
-    so that widening `REQUIREMENT_TYPES` without adding an evaluator fails
-    loudly. Shared by a step (`evaluate_requirements`) and a quest offer's
-    eligibility (`quest_reads`), so both are one judgment.
-
-    `_day_reachable_ids` is computed AT MOST ONCE per call, only if a
-    `location_reachable` requirement is present — never per requirement."""
-    needs_reachable = any(r.type == "location_reachable" for r in requirements)
-    reachable_ids = _day_reachable_ids(character.current_location_id, db) if needs_reachable else None
-
-    verdicts: list[Verdict] = []
-    for req in requirements:
-        evaluator = _EVALUATORS.get(req.type)
-        if evaluator is None:
-            raise ValueError(f"unknown requirement type {req.type!r}")
-        verdicts.append(evaluator(req, character, db, reachable_ids))
-    return verdicts
-
-
 def evaluate_requirements(step: PlanStep, character: Character, db: Session) -> list[Verdict]:
     """Judge every requirement on `step` (`evaluate_specs` on its
     requirements)."""
diff --git a/src/world_engine/day_resolve.py b/src/world_engine/day_resolve.py
index 9c41d3b..29af960 100644
--- a/src/world_engine/day_resolve.py
+++ b/src/world_engine/day_resolve.py
@@ -66,12 +66,12 @@ from typing import Optional
 
 from sqlmodel import Session, select
 
+from .condition_forms import Verdict as RequirementVerdict
 from .day_concordance import ConcordanceResult
 from .day_plan import (
     DAY_BUDGET_SLOTS,
     BudgetResult,
     EvaluatedStep,
-    Verdict as RequirementVerdict,
     budget_cut,
     evaluate_agenda_step,
 )
diff --git a/src/world_engine/models/config.py b/src/world_engine/models/config.py
index 5f8fbd5..f6d3547 100644
--- a/src/world_engine/models/config.py
+++ b/src/world_engine/models/config.py
@@ -112,12 +112,12 @@ class AgendaStep(SQLModel, table=True):
 # id) rather than an entity. Eight forms since v2.17 (TICKET-0108,
 # BRIEF-0108-A): the four the day-plan model may emit, plus `has_met`,
 # `faction_member`, `skill_rank_gte` and `quest_completed`, authored by the
-# creator only (`day_plan.MODEL_REQUIREMENT_TYPES`). Ten since v2.19
+# creator only (`condition_forms.MODEL_REQUIREMENT_TYPES`). Ten since v2.19
 # (TICKET-0110, BRIEF-0110-A, G1): `has_debt_to` and `no_debt_to`, an open
 # debt toward the target entity or none, creator only too.
 #
 # The per-type shape CHECK is the structural guarantee that an ill-formed row
-# cannot exist; its three groups are `day_plan.ENTITY_TARGET_TYPES`,
+# cannot exist; its three groups are `condition_forms.ENTITY_TARGET_TYPES`,
 # `KEY_TARGET_TYPES` and `THRESHOLD_TYPES`. `quest_offer_requirement`
 # (models/quests.py) carries the same two CHECK texts, byte for byte
 # (`quests.py` check, QA1). Curated plan metadata, same family as
diff --git a/src/world_engine/models/quests.py b/src/world_engine/models/quests.py
index 8536864..c29354f 100644
--- a/src/world_engine/models/quests.py
+++ b/src/world_engine/models/quests.py
@@ -10,7 +10,7 @@ quest's state is its agenda's status, never a second column (M1).
 
 The requirement vocabulary is `agenda_step_requirement`'s, not a second
 language (B1): `quest_offer_requirement` carries the same two CHECK texts,
-byte for byte, and `day_plan.evaluate_specs` judges both.
+byte for byte, and `condition_forms.evaluate_specs` judges both.
 
 Offers are curated content: their steps and requirements are replaced
 whole when the creator saves an offer (the `npc_price` full-replace
diff --git a/src/world_engine/writes/goals_agendas.py b/src/world_engine/writes/goals_agendas.py
index 932f9e8..231584e 100644
--- a/src/world_engine/writes/goals_agendas.py
+++ b/src/world_engine/writes/goals_agendas.py
@@ -43,14 +43,14 @@ from sqlalchemy import text
 from sqlalchemy.orm import attributes as sa_attrs
 from sqlmodel import Session, select
 
-from ..day_plan import (
+from ..condition_forms import (
     ENTITY_TARGET_TYPES,
     KEY_TARGET_TYPES,
     REQUIREMENT_TYPES,
     THRESHOLD_TYPES,
-    PlanStep,
     RequirementSpec,
 )
+from ..day_plan import PlanStep
 from ..models import (
     BASE_SKILL_DOMAINS,
     Agenda,
diff --git a/src/world_engine/writes/quests.py b/src/world_engine/writes/quests.py
index ec7062e..17ebf4f 100644
--- a/src/world_engine/writes/quests.py
+++ b/src/world_engine/writes/quests.py
@@ -27,7 +27,8 @@ from sqlalchemy import text
 from sqlalchemy.orm import attributes as sa_attrs
 from sqlmodel import Session, select
 
-from ..day_plan import MAX_PLAN_STEPS, PlanStep, RequirementSpec, evaluate_specs
+from ..condition_forms import RequirementSpec, evaluate_specs
+from ..day_plan import MAX_PLAN_STEPS, PlanStep
 from ..models import (
     BASE_SKILL_DOMAINS,
     QUEST_OFFER_STATUSES,
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 5309ace..f3c707f 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18357,6 +18357,28 @@ whom, a faction's member to pick (its contact preselected), secrecy, and
 stored rows only and would show less than the player knows.
 
 
+## THE REQUIREMENT FORMS GET THEIR OWN MODULE (TICKET-0111) -- `condition_forms.py`, A PURE MOVE OUT OF `day_plan.py` (BRIEF-0111-a, no schema change)
+
+**Why.** TICKET-0111 turns the flat list of requirements into a language of
+conditions (A1 of the series, I1: one language for every agenda). Its
+leaves are the ten requirement forms; their evaluators are what the tree
+evaluates. `day_plan.py` will need the tree for its steps and the tree will
+need the forms: kept in `day_plan.py`, the forms would make the two modules
+import each other.
+
+**What moved, unchanged.** `REQUIREMENT_TYPES`, `MODEL_REQUIREMENT_TYPES`,
+the three shape groups, `RequirementSpec`, `Verdict`, the ten `_eval_*`
+evaluators and `_EVALUATORS`, `_entity_name`, `_open_debt`,
+`_day_reachable_ids` (with its D1 history) and `evaluate_specs`.
+`day_plan.py` keeps the plan: `PlanStep`, `EvaluatedStep`, the budget cut,
+the anchoring and the emission. Every importer names the new home; no name
+is re-exported from `day_plan.py`, so each lives in one place
+(`conditions.py` CA1).
+
+**Checks retargeted, not changed.** `day_plan.py` R1, R10 and R25 read
+`condition_forms.py`; `known_reachability.py` documents it in place of
+`day_plan.py` as a `connects_to` reader (row 12 of the census, unchanged).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/tickets/connects-to-readers-TICKET-0082.md b/tooling/tickets/connects-to-readers-TICKET-0082.md
index e4537ba..47e09a9 100644
--- a/tooling/tickets/connects-to-readers-TICKET-0082.md
+++ b/tooling/tickets/connects-to-readers-TICKET-0082.md
@@ -121,3 +121,7 @@ producing a mechanical verdict (E2), explicitly deferred by this ticket.
 Recorded here, per `BRIEF-0082-d-amendment-1-public-floor-reader.md`'s
 instruction, as the reactivation condition for a successor ticket — not
 implemented, not widened, here.
+
+**Note (TICKET-0111, BRIEF-0111-A).** Row 12's `_day_reachable_ids` moved, unchanged,
+from `day_plan.py` to `condition_forms.py`, with the evaluator it feeds
+(`_eval_location_reachable`). Its classification and its D1 standing are unchanged.
diff --git a/tooling/verify/checks/conditions.py b/tooling/verify/checks/conditions.py
new file mode 100644
index 0000000..5327524
--- /dev/null
+++ b/tooling/verify/checks/conditions.py
@@ -0,0 +1,102 @@
+"""G1 check for TICKET-0111 -- the condition language.
+
+The lot adds its pieces brief by brief; this check grows with it (the
+`quests.py` and `debts.py` precedent). Each brief adds its rules here in
+the same commit.
+
+CA1 -- the forms have one home (BRIEF-0111-A, static, AST). Each of
+   `REQUIREMENT_TYPES`, `MODEL_REQUIREMENT_TYPES`, `ENTITY_TARGET_TYPES`,
+   `KEY_TARGET_TYPES`, `THRESHOLD_TYPES`, `_EVALUATORS`, `RequirementSpec`,
+   `Verdict`, `evaluate_specs` and `_day_reachable_ids` is defined at module
+   level in `condition_forms.py`, and each but `Verdict` in no other module
+   under `src/` (`resolution.py` and `skill_lexicon.py` declare verdicts of
+   their own); no other module defines a function of the same name as one
+   of its `_eval_*` evaluators.
+
+A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import ast
+import pathlib
+import sys
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+SRC = ROOT / "src" / "world_engine"
+FORMS_FILE = SRC / "condition_forms.py"
+
+FAILURES: list[str] = []
+
+FORM_NAMES = (
+    "REQUIREMENT_TYPES", "MODEL_REQUIREMENT_TYPES", "ENTITY_TARGET_TYPES", "KEY_TARGET_TYPES",
+    "THRESHOLD_TYPES", "_EVALUATORS", "RequirementSpec", "Verdict", "evaluate_specs", "_day_reachable_ids",
+)
+
+# `Verdict` is a common name: `resolution.Verdict` and `skill_lexicon.Verdict`
+# are other things. Every other name is the forms' alone.
+UNIQUE_NAMES = tuple(n for n in FORM_NAMES if n != "Verdict")
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _top_level_names(tree: ast.Module) -> set[str]:
+    names: set[str] = set()
+    for node in tree.body:
+        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
+            names.add(node.name)
+        elif isinstance(node, ast.Assign):
+            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
+        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
+            names.add(node.target.id)
+    return names
+
+
+def _modules() -> dict[pathlib.Path, set[str]]:
+    found: dict[pathlib.Path, set[str]] = {}
+    for path in sorted(SRC.rglob("*.py")):
+        if "__pycache__" in path.parts:
+            continue
+        found[path] = _top_level_names(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
+    return found
+
+
+# --- CA1 -----------------------------------------------------------------------
+
+def check_ca1() -> None:
+    modules = _modules()
+    if FORMS_FILE not in modules:
+        fail("CA1: condition_forms.py is missing")
+        return
+    home = modules[FORMS_FILE]
+    for name in FORM_NAMES:
+        if name not in home:
+            fail(f"CA1: condition_forms.py does not define {name}")
+    evaluators = sorted(n for n in home if n.startswith("_eval_"))
+    if not evaluators:
+        fail("CA1: condition_forms.py defines zero _eval_* functions")
+    for path, names in modules.items():
+        if path == FORMS_FILE:
+            continue
+        rel = path.relative_to(SRC.parent).as_posix()
+        for name in UNIQUE_NAMES:
+            if name in names:
+                fail(f"CA1: {rel} defines {name}, which lives in condition_forms.py")
+        for name in sorted(n for n in names if n.startswith("_eval_") and n in evaluators):
+            fail(f"CA1: {rel} defines the evaluator {name}, which lives in condition_forms.py")
+
+
+def main() -> int:
+    check_ca1()
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: conditions -- the requirement forms, their evaluators and their BFS live in "
+          "condition_forms.py alone")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/day_narration.py b/tooling/verify/checks/day_narration.py
index f55c155..da57a1b 100644
--- a/tooling/verify/checks/day_narration.py
+++ b/tooling/verify/checks/day_narration.py
@@ -649,7 +649,7 @@ def check_judge_rejects_empty_fact_sheet() -> None:
 
 def check_blocked_detail_fr_bijection() -> None:
     """R15 (BRIEF-0078-b item 3): _BLOCKED_DETAIL_FR's key set equals
-    day_plan.REQUIREMENT_TYPES in both directions, and
+    condition_forms.REQUIREMENT_TYPES in both directions, and
     requirement_detail_fr raises on an unknown type."""
     tree = _parse(DAY_RESOLVE_FILE)
     if tree is None:
@@ -673,7 +673,7 @@ def check_blocked_detail_fr_bijection() -> None:
         return
 
     sys.path.insert(0, str(ROOT / "src"))
-    from world_engine.day_plan import REQUIREMENT_TYPES  # noqa: E402
+    from world_engine.condition_forms import REQUIREMENT_TYPES  # noqa: E402
 
     if keys != set(REQUIREMENT_TYPES):
         fail(
diff --git a/tooling/verify/checks/day_plan.py b/tooling/verify/checks/day_plan.py
index 2c94c96..14dcd64 100644
--- a/tooling/verify/checks/day_plan.py
+++ b/tooling/verify/checks/day_plan.py
@@ -171,6 +171,9 @@ ROOT = pathlib.Path(__file__).resolve().parents[3]
 SRC = ROOT / "src" / "world_engine"
 
 DAY_PLAN_FILE = SRC / "day_plan.py"
+# TICKET-0111 (BRIEF-0111-A): the forms, their evaluators and the BFS moved
+# here, unchanged; R1 and R10 look where they now live.
+CONDITION_FORMS_FILE = SRC / "condition_forms.py"
 DAY_RECONCILE_FILE = SRC / "day_reconcile.py"
 DAY_PLAN_SELECT_FILE = SRC / "day_plan_select.py"
 CANON_FILE = SRC / "models" / "canon.py"
@@ -293,25 +296,25 @@ def _check_constraint_texts(tree: ast.AST) -> dict[str, str]:
 
 
 def check_evaluator_bijection() -> None:
-    tree = _parse(DAY_PLAN_FILE)
+    tree = _parse(CONDITION_FORMS_FILE)
     if tree is None:
         return
     req_tuple = _tuple_assign(tree, "REQUIREMENT_TYPES")
     if req_tuple is None:
-        fail(f"{_rel(DAY_PLAN_FILE)}: REQUIREMENT_TYPES tuple not found")
+        fail(f"{_rel(CONDITION_FORMS_FILE)}: REQUIREMENT_TYPES tuple not found")
         return
     req_types = {e.value for e in req_tuple.elts if isinstance(e, ast.Constant)}
     if not req_types:
-        fail(f"{_rel(DAY_PLAN_FILE)}: REQUIREMENT_TYPES located but holds zero values")
+        fail(f"{_rel(CONDITION_FORMS_FILE)}: REQUIREMENT_TYPES located but holds zero values")
         return
 
     evaluators = _named_dict(tree, "_EVALUATORS")
     if evaluators is None:
-        fail(f"{_rel(DAY_PLAN_FILE)}: _EVALUATORS dict literal not found")
+        fail(f"{_rel(CONDITION_FORMS_FILE)}: _EVALUATORS dict literal not found")
         return
     evaluator_keys = {k.value for k in evaluators.keys if isinstance(k, ast.Constant)}
     if not evaluator_keys:
-        fail(f"{_rel(DAY_PLAN_FILE)}: _EVALUATORS located but holds zero keys")
+        fail(f"{_rel(CONDITION_FORMS_FILE)}: _EVALUATORS located but holds zero keys")
         return
 
     missing = req_types - evaluator_keys
@@ -531,12 +534,13 @@ def check_bounds_constants() -> None:
 
 
 def check_no_traversal_reuse() -> None:
-    """R10 (BRIEF-0075-b-amendment-1): `day_plan.py` declares its OWN
+    """R10 (BRIEF-0075-b-amendment-1): `condition_forms.py` (since TICKET-0111;
+    `day_plan.py` before) declares its OWN
     `connects_to` BFS rather than importing a sibling reader — decision D1
     (BRIEF-19) made structural for this consumer. Do NOT turn this into a
     check that day_plan.py REUSES an existing traversal — that was the
     superseded instruction the amendment corrected."""
-    tree = _parse(DAY_PLAN_FILE)
+    tree = _parse(CONDITION_FORMS_FILE)
     if tree is None:
         return
 
@@ -546,26 +550,26 @@ def check_no_traversal_reuse() -> None:
             for alias in node.names:
                 if alias.name in forbidden:
                     fail(
-                        f"{_rel(DAY_PLAN_FILE)}: imports {alias.name!r} — decision D1 forbids "
+                        f"{_rel(CONDITION_FORMS_FILE)}: imports {alias.name!r} — decision D1 forbids "
                         "reusing a sibling connects_to reader"
                     )
         if isinstance(node, ast.Name) and node.id in forbidden:
-            fail(f"{_rel(DAY_PLAN_FILE)}: references {node.id!r} — decision D1 forbids reusing a sibling reader")
+            fail(f"{_rel(CONDITION_FORMS_FILE)}: references {node.id!r} — decision D1 forbids reusing a sibling reader")
 
     func = _find_function(tree, "_day_reachable_ids")
     if func is None:
-        fail(f"{_rel(DAY_PLAN_FILE)}: _day_reachable_ids not found — day_plan.py must declare its own BFS (D1)")
+        fail(f"{_rel(CONDITION_FORMS_FILE)}: _day_reachable_ids not found — condition_forms.py must declare its own BFS (D1)")
         return
 
     has_loop = any(isinstance(n, (ast.While, ast.For)) for n in ast.walk(func))
     if not has_loop:
-        fail(f"{_rel(DAY_PLAN_FILE)}: _day_reachable_ids contains no loop — not a real traversal")
+        fail(f"{_rel(CONDITION_FORMS_FILE)}: _day_reachable_ids contains no loop — not a real traversal")
 
     references_connects_to = any(
         isinstance(n, ast.Constant) and n.value == "connects_to" for n in ast.walk(func)
     )
     if not references_connects_to:
-        fail(f"{_rel(DAY_PLAN_FILE)}: _day_reachable_ids does not reference 'connects_to'")
+        fail(f"{_rel(CONDITION_FORMS_FILE)}: _day_reachable_ids does not reference 'connects_to'")
 
 
 # --- BRIEF-0075-f (reconciliation and closure), as corrected by AMENDMENT 1 ---
@@ -971,21 +975,21 @@ def check_select_reads_only() -> None:
 
 def check_verdict_type_field() -> None:
     """R25 (BRIEF-0078-a item 3): Verdict's field list starts with `type`,
-    and all four `Verdict(` constructions in day_plan.py pass a `type=`
+    and all four `Verdict(` constructions in condition_forms.py (day_plan.py before TICKET-0111) pass a `type=`
     keyword. Zero constructions collected is a FAILURE."""
-    tree = _parse(DAY_PLAN_FILE)
+    tree = _parse(CONDITION_FORMS_FILE)
     if tree is None:
         return
     cls = _find_class(tree, "Verdict")
     if cls is None:
-        fail(f"day_plan R25: {_rel(DAY_PLAN_FILE)}: Verdict class not found")
+        fail(f"day_plan R25: {_rel(CONDITION_FORMS_FILE)}: Verdict class not found")
         return
     field_names = [
         node.target.id for node in cls.body
         if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
     ]
     if not field_names:
-        fail(f"day_plan R25: {_rel(DAY_PLAN_FILE)}: Verdict declares zero annotated fields")
+        fail(f"day_plan R25: {_rel(CONDITION_FORMS_FILE)}: Verdict declares zero annotated fields")
         return
     if field_names[0] != "type":
         fail(f"day_plan R25: Verdict's first field is {field_names[0]!r}, expected 'type'")
@@ -996,9 +1000,9 @@ def check_verdict_type_field() -> None:
             constructions += 1
             kw_names = {kw.arg for kw in node.keywords}
             if "type" not in kw_names:
-                fail(f"day_plan R25: {_rel(DAY_PLAN_FILE)}:{node.lineno} — Verdict(...) missing type= keyword")
+                fail(f"day_plan R25: {_rel(CONDITION_FORMS_FILE)}:{node.lineno} — Verdict(...) missing type= keyword")
     if constructions == 0:
-        fail(f"day_plan R25: zero Verdict(...) constructions located in {_rel(DAY_PLAN_FILE)} — vacuous")
+        fail(f"day_plan R25: zero Verdict(...) constructions located in {_rel(CONDITION_FORMS_FILE)} — vacuous")
 
 
 def check_anchoring_readers() -> None:
diff --git a/tooling/verify/checks/debts.py b/tooling/verify/checks/debts.py
index 0237f63..56ccdec 100644
--- a/tooling/verify/checks/debts.py
+++ b/tooling/verify/checks/debts.py
@@ -11,7 +11,7 @@ DA1 -- schema and vocabulary (BRIEF-0110-A, import and static).
       `contact_entity_id` and `quest_economy` `debt_fact_relation` and
       `debt_skill_relation`; `DEFAULT_RATES` gives them 10 and 20 and
       `ECONOMY_COLUMNS` lists them; the code's schema version is v2.19.
-   b. `day_plan.REQUIREMENT_TYPES` ends with `has_debt_to`, `no_debt_to`;
+   b. `condition_forms.REQUIREMENT_TYPES` ends with `has_debt_to`, `no_debt_to`;
       both are in `ENTITY_TARGET_TYPES`, neither in `THRESHOLD_TYPES` nor
       `MODEL_REQUIREMENT_TYPES`; each has an evaluator and a French blocked
       detail; `questRequirements.js` offers both on the `givers` list.
@@ -260,16 +260,16 @@ def check_da1a() -> None:
 
 
 def check_da1b() -> None:
-    from world_engine import day_plan, day_resolve
+    from world_engine import condition_forms, day_resolve
 
-    if tuple(day_plan.REQUIREMENT_TYPES[-2:]) != DEBT_FORMS:
-        fail(f"DA1b: REQUIREMENT_TYPES ends with {day_plan.REQUIREMENT_TYPES[-2:]}")
+    if tuple(condition_forms.REQUIREMENT_TYPES[-2:]) != DEBT_FORMS:
+        fail(f"DA1b: REQUIREMENT_TYPES ends with {condition_forms.REQUIREMENT_TYPES[-2:]}")
     for form in DEBT_FORMS:
-        if form not in day_plan.ENTITY_TARGET_TYPES:
+        if form not in condition_forms.ENTITY_TARGET_TYPES:
             fail(f"DA1b: {form} is not an entity-target form")
-        if form in day_plan.THRESHOLD_TYPES or form in day_plan.MODEL_REQUIREMENT_TYPES:
+        if form in condition_forms.THRESHOLD_TYPES or form in condition_forms.MODEL_REQUIREMENT_TYPES:
             fail(f"DA1b: {form} takes a threshold or is offered to the model")
-        if form not in day_plan._EVALUATORS or form not in day_resolve._BLOCKED_DETAIL_FR:
+        if form not in condition_forms._EVALUATORS or form not in day_resolve._BLOCKED_DETAIL_FR:
             fail(f"DA1b: {form} has no evaluator or no French detail")
     text = _read("creation/questRequirements.js")
     for form in DEBT_FORMS:
@@ -478,7 +478,7 @@ def _debt(session, ids: dict, debtor: str, creditor: str, status: str = "open")
 
 
 def _verdicts(session, pc, target: str) -> tuple[bool, bool]:
-    from world_engine.day_plan import RequirementSpec, evaluate_specs
+    from world_engine.condition_forms import RequirementSpec, evaluate_specs
 
     has, none = evaluate_specs((RequirementSpec(type="has_debt_to", target_entity_id=target),
                                 RequirementSpec(type="no_debt_to", target_entity_id=target)), pc, session)
@@ -488,7 +488,7 @@ def _verdicts(session, pc, target: str) -> tuple[bool, bool]:
 def check_da3(engine) -> None:
     from sqlmodel import Session
 
-    from world_engine.day_plan import RequirementSpec, evaluate_specs
+    from world_engine.condition_forms import RequirementSpec, evaluate_specs
     from world_engine.day_resolve import requirement_detail_fr
     from world_engine.models import Character
     from world_engine.writes.goals_agendas import _clean_requirement
@@ -684,7 +684,7 @@ def _regard(session, ids, who="npc") -> int:
 
 
 def check_db2(session, ids) -> None:
-    from world_engine.day_plan import RequirementSpec, evaluate_specs
+    from world_engine.condition_forms import RequirementSpec, evaluate_specs
     from world_engine.ledger import get_balance
     from world_engine.holdings import held_quantity
     from sqlmodel import select
diff --git a/tooling/verify/checks/knowledge_identity.py b/tooling/verify/checks/knowledge_identity.py
index 6890477..ef833b5 100644
--- a/tooling/verify/checks/knowledge_identity.py
+++ b/tooling/verify/checks/knowledge_identity.py
@@ -659,7 +659,7 @@ def _k6_verdicts(session, day) -> None:
     from types import SimpleNamespace
 
     from world_engine.day_mutations import _emit_new_knowledge
-    from world_engine.day_plan import RequirementSpec, _eval_knowledge
+    from world_engine.condition_forms import RequirementSpec, _eval_knowledge
     from world_engine.day_resolve import BLOCKED_BAND, requirement_detail_fr
     from world_engine.models import Character
 
diff --git a/tooling/verify/checks/known_reachability.py b/tooling/verify/checks/known_reachability.py
index fc1a381..5575886 100644
--- a/tooling/verify/checks/known_reachability.py
+++ b/tooling/verify/checks/known_reachability.py
@@ -324,7 +324,9 @@ DOCUMENTED_MODULES = frozenset({
     "world_engine/cockpit/crud/locations.py",
     "world_engine/cockpit/play.py",
     "world_engine/cockpit/routes/regions.py",
-    "world_engine/day_plan.py",
+    # TICKET-0111, BRIEF-0111-A: row 12's `_day_reachable_ids` moved, unchanged,
+    # from day_plan.py, which no longer spells the literal.
+    "world_engine/condition_forms.py",
     "world_engine/spatial_author.py",
     "world_engine/context.py",
     "world_engine/cockpit/crud/_shared.py",
diff --git a/tooling/verify/checks/quests.py b/tooling/verify/checks/quests.py
index afcd2de..f684e70 100644
--- a/tooling/verify/checks/quests.py
+++ b/tooling/verify/checks/quests.py
@@ -69,7 +69,7 @@ QB4 -- what the player sees (fixture and static). `journee_payload` and the
 
 QC1 -- the editor's mirror (BRIEF-0108-C, static). `frontend/src/creation/
    questRequirements.js`'s `REQUIREMENT_FORMS` has exactly the keys of
-   `day_plan.REQUIREMENT_TYPES`; its forms with `column: 'entity'` are
+   `condition_forms.REQUIREMENT_TYPES`; its forms with `column: 'entity'` are
    `ENTITY_TARGET_TYPES`, with `column: 'key'` `KEY_TARGET_TYPES`, with
    `threshold: true` `THRESHOLD_TYPES`.
 QC2 -- the « Quêtes » tab (static). `tabs.js`'s `quetes` entry mounts the
@@ -148,16 +148,16 @@ def _shape_groups(shape: str) -> list[tuple[str, ...]]:
 
 
 def check_qa1() -> None:
-    from world_engine import day_plan, llm_parse
+    from world_engine import condition_forms, day_plan, llm_parse
     from world_engine.models import AgendaStepRequirement, QuestOfferRequirement
 
-    types = day_plan.REQUIREMENT_TYPES
+    types = condition_forms.REQUIREMENT_TYPES
     if tuple(types) != MODEL_FORMS + CREATOR_FORMS + DEBT_FORMS:
         fail(f"QA1: REQUIREMENT_TYPES is {types}")
-    if tuple(day_plan.MODEL_REQUIREMENT_TYPES) != MODEL_FORMS or not set(MODEL_FORMS) <= set(types):
-        fail(f"QA1: MODEL_REQUIREMENT_TYPES is {day_plan.MODEL_REQUIREMENT_TYPES}")
-    entity, key, threshold = (set(day_plan.ENTITY_TARGET_TYPES), set(day_plan.KEY_TARGET_TYPES),
-                              set(day_plan.THRESHOLD_TYPES))
+    if tuple(condition_forms.MODEL_REQUIREMENT_TYPES) != MODEL_FORMS or not set(MODEL_FORMS) <= set(types):
+        fail(f"QA1: MODEL_REQUIREMENT_TYPES is {condition_forms.MODEL_REQUIREMENT_TYPES}")
+    entity, key, threshold = (set(condition_forms.ENTITY_TARGET_TYPES), set(condition_forms.KEY_TARGET_TYPES),
+                              set(condition_forms.THRESHOLD_TYPES))
     if entity & key or entity | key != set(types) or not threshold or not threshold <= set(types):
         fail(f"QA1: the shape groups do not partition the vocabulary: {entity}, {key}, {threshold}")
 
@@ -165,7 +165,7 @@ def check_qa1() -> None:
     offer = _check_texts(QuestOfferRequirement.__table__)
     shape = agenda.get("ck_agenda_step_requirement_shape", "")
     groups = _shape_groups(shape)
-    expected = [tuple(day_plan.ENTITY_TARGET_TYPES), tuple(day_plan.KEY_TARGET_TYPES), tuple(day_plan.THRESHOLD_TYPES)]
+    expected = [tuple(condition_forms.ENTITY_TARGET_TYPES), tuple(condition_forms.KEY_TARGET_TYPES), tuple(condition_forms.THRESHOLD_TYPES)]
     if groups != expected:
         fail(f"QA1: the shape CHECK groups are {groups}, expected {expected}")
     pairs = (("ck_agenda_step_requirement_type", "ck_quest_offer_requirement_type"),
@@ -326,7 +326,7 @@ def _qa3_world(session) -> dict:
 
 
 def _verdict(session, character, form: str, **target):
-    from world_engine.day_plan import RequirementSpec, evaluate_specs
+    from world_engine.condition_forms import RequirementSpec, evaluate_specs
 
     return evaluate_specs((RequirementSpec(type=form, **target),), character, session)[0]
 
@@ -408,7 +408,7 @@ def _qa3_quest(session, ids, pc) -> None:
 
 
 def _qa3_wording_and_cleaning(session, ids, pc) -> None:
-    from world_engine.day_plan import RequirementSpec
+    from world_engine.condition_forms import RequirementSpec
     from world_engine.day_resolve import requirement_detail_fr
     from world_engine.writes.goals_agendas import _clean_requirement
 
@@ -487,7 +487,8 @@ def _qb_world(session) -> dict:
 
 
 def _offer_kwargs(ids: dict, **over) -> dict:
-    from world_engine.day_plan import PlanStep, RequirementSpec
+    from world_engine.condition_forms import RequirementSpec
+    from world_engine.day_plan import PlanStep
 
     steps = [
         PlanStep(objective="Traquer le loup", cost=2, domain="perception",
@@ -511,7 +512,8 @@ def _counts(session) -> tuple:
 
 
 def _qb1_refusals(session, ids) -> None:
-    from world_engine.day_plan import PlanStep, RequirementSpec
+    from world_engine.condition_forms import RequirementSpec
+    from world_engine.day_plan import PlanStep
     from world_engine.writes import write_quest_offer
 
     bad = (
@@ -536,7 +538,8 @@ def _qb1_refusals(session, ids) -> None:
 def check_qb1(session, ids) -> None:
     from sqlmodel import select
 
-    from world_engine.day_plan import PlanStep, RequirementSpec
+    from world_engine.condition_forms import RequirementSpec
+    from world_engine.day_plan import PlanStep
     from world_engine.models import QuestOfferRequirement, QuestOfferStep
     from world_engine.writes import write_quest_offer
 
@@ -788,7 +791,7 @@ def _read(rel: str) -> str:
 
 
 def check_qc1() -> None:
-    from world_engine import day_plan
+    from world_engine import condition_forms
 
     text = _read("creation/questRequirements.js")
     forms = dict(re.findall(r"^\s+(\w+): \{ label: '[^']*', list: '\w+', (column: '\w+', threshold: \w+) \},$",
@@ -796,11 +799,11 @@ def check_qc1() -> None:
     if not forms:
         fail("QC1: REQUIREMENT_FORMS holds zero forms")
         return
-    if list(forms) != list(day_plan.REQUIREMENT_TYPES):
+    if list(forms) != list(condition_forms.REQUIREMENT_TYPES):
         fail(f"QC1: REQUIREMENT_FORMS keys {list(forms)} != REQUIREMENT_TYPES")
     groups = {
-        "column: 'entity'": tuple(day_plan.ENTITY_TARGET_TYPES), "column: 'key'": tuple(day_plan.KEY_TARGET_TYPES),
-        "threshold: true": tuple(day_plan.THRESHOLD_TYPES),
+        "column: 'entity'": tuple(condition_forms.ENTITY_TARGET_TYPES), "column: 'key'": tuple(condition_forms.KEY_TARGET_TYPES),
+        "threshold: true": tuple(condition_forms.THRESHOLD_TYPES),
     }
     for marker, expected in groups.items():
         found = tuple(form for form, spec in forms.items() if marker in spec)
````

## Scope OUT

- Any change of behaviour: a moved line differs from its original only by its file.
- `RequirementSpec`'s new fields, the tree, any new form (B, C).
- Any table, migration or frontend file.
- The interpreter in natural language (TICKET-0112), world state attributes (0113), the event journal, failure conditions and absence conditions (0114, N1), the creator dashboard (0115), rank trials (0116).
- `goal_prerequisite`, the NPC goal's gate (GP1: its own ticket).
- Any change to the day-chain prompts or to the model's four forms (`MODEL_REQUIREMENT_TYPES`).
- A completion that acts on its own (M2); a visual tree editor (T2).
- Any change to `legacy.html` or Play.
- Every later brief of this lot.

## Invariants to defend

None is threatened by a pure move. `connects_to` readers: `_day_reachable_ids` keeps its own BFS and its D1 docstring (one reader per consumer); `known_reachability.py` documents it at its new home.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- A named mutation does not turn its rule red.
- A moved line would need a change other than its imports to keep the corpus green.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- `git diff -M` showing the moved block as a rename-with-changes: expected, the imports differ.
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run every check with `WORLD_ENGINE_ENV=test`).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/conditions.py` -> `PASS: conditions -- the requirement forms, their evaluators and their BFS live in condition_forms.py alone`
- `day_plan.py`, `known_reachability.py`, `quests.py`, `debts.py`, `knowledge_identity.py`, `day_narration.py`, `claude_md_contract.py`, `module_budget.py`, `import_cycle.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`conditions.py` exits 1 with the rule named):
  - in `src/world_engine/condition_forms.py`, `def _day_reachable_ids(origin_location_id: str, db: Session) -> frozenset[str]:` -> `def _day_reachable_ids_moved(origin_location_id: str, db: Session) -> frozenset[str]:` -> `CA1`
  - in `src/world_engine/day_plan.py`, after the line `MAX_PLAN_STEPS = 12`, insert the line `REQUIREMENT_TYPES: tuple[str, ...] = ()` -> `CA1`
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 144/144 (143 on `main` plus `conditions.py`).
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `THE REQUIREMENT FORMS GET THEIR OWN MODULE (TICKET-0111) -- `condition_forms.py`, A PURE MOVE OUT OF `day_plan.py` (BRIEF-0111-a, no schema change)` -- in the diff. CLAUDE.md's File structure line -- in the diff. No schema change.
