"""G1 check for TICKET-0111 -- the condition language.

The lot adds its pieces brief by brief; this check grows with it (the
`quests.py` and `debts.py` precedent). Each brief adds its rules here in
the same commit.

CA1 -- the forms have one home (BRIEF-0111-A, static, AST). Each of
   `REQUIREMENT_TYPES`, `MODEL_REQUIREMENT_TYPES`, `ENTITY_TARGET_TYPES`,
   `KEY_TARGET_TYPES`, `THRESHOLD_TYPES`, `_EVALUATORS`, `RequirementSpec`,
   `Verdict`, `evaluate_specs` and `_day_reachable_ids` is defined at module
   level in `condition_forms.py`, and each but `Verdict` in no other module
   under `src/` (`resolution.py` and `skill_lexicon.py` declare verdicts of
   their own); no other module defines a function of the same name as one
   of its `_eval_*` evaluators.

CB1 -- the tree's shape (BRIEF-0111-B, import, no DB). `node_from_dict`
   round-trips a tree using every connector through `node_to_dict`, gives a
   leaf that names no subject the role `doer`, and refuses, each with a
   `ConditionShapeError`: an unknown connector, a `not` with two children,
   an `at_least` with n = 0 or n above its children, an `all` with none, a
   leaf naming both a role and an entity, an unknown role, a tree seven
   levels deep, a tree of 61 nodes, a non-integer threshold.
CB2 -- three-valued connectors (import, no DB). `_combine` gives, for every
   pair of child states, what the reference table below gives for `all`,
   `any`, `at_least` 1 and 2; for `not`, each of the three states; and for
   `at_least` 2 of 3, every triple.
CB3 -- evaluation (fixture). A doer, an NPC, a faction giver: a leaf is
   judged on its subject -- the doer, a giver or contact bound to a
   character, a fixed entity; a role bound to nothing or to a faction is
   `unknown` with its French reason and no verdict; `any` of an unknown and
   a met leaf is met, `all` of them unknown, `not` of a met leaf unmet;
   `leaf_verdicts` holds the judged leaves only; each subject's reachable
   set is computed once. `and_path_leaves` keeps only the leaves reached
   through `all`; `flat_leaves` returns the leaves of a flat tree and None
   otherwise.
CB4 -- French (fixture). `FORM_PHRASES_FR` has one phrase per form of
   `REQUIREMENT_TYPES` and `CONNECTOR_HEADS_FR` one head per connector;
   `describe` puts a connector before its children one level deeper;
   `verdict_lines` marks each line, gives a counting leaf its progress and
   an unknown leaf its reason.
CB5 -- the language writes nothing (static, AST). Neither `conditions.py`
   nor `condition_text.py` calls `add`, `commit`, `delete`, `execute` or
   `flush`.

CC1 -- storage (BRIEF-0111-C, import). `condition` and `condition_node`
   carry exactly their contract's columns and CHECK texts; `CONDITION_ROLES`
   and `CONDITION_OPS` are the values those CHECKs quote, in order; no CHECK
   of either table names a form; `models` declares neither
   `AgendaStepRequirement` nor `QuestOfferRequirement`; the code's schema
   version is v2.20 or later; `VALUE_LABELS_FR` labels exactly
   `FORM_VALUES`.
CC2 -- the writer (fixture). `write_condition` stores a tree using every
   connector, a role, a fixed subject and a value; `read_condition` returns
   it equal; a second write replaces it whole (the first nodes gone); None
   removes it. Refused, each with no row written: an unknown form, a
   `quest_state` with no value or an unknown one, a `vital_status` naming a
   target, an `item_held` aimed at a character, a fixed subject that is a
   faction, an eligibility on an agenda step, two owners, a `not` with two
   children.
CC3 -- migration `scripts/migrate_v2_20_conditions.py`, on a v2.19-shaped
   database (both requirement tables in their v2.19 DDL, verbatim below)
   holding an offer's eligibility, two rows of an offer step (one
   `quest_completed`), two rows of an agenda step, and a `session` row
   pointing to a missing world: at v2.18 it refuses and changes nothing; at
   v2.19 both tables are gone, each owner has one `all` of its leaves in the
   rows' order, judged on `doer`, `quest_completed` read as `quest_state`
   `completed`, `foreign_key_check` is empty on the two new tables, the
   orphan is noted, `schema_meta` is the code's version; a second run
   changes nothing.
CC4 -- the forms and the consumers (fixture). `item_held` reads the
   holding, `vital_status` the subject's state, `quest_state` each of its
   values. `evaluate_agenda_step` on a quest's agenda binds the offer's
   giver; the day's NPC (`_account_rendezvous`) is the target of the first
   `relation_gte` reached through `all`, never one under `any`; `blocked_details_fr` says what an
   unmet leaf lacks and, under a `not`, that a leaf must not hold.
CC5 -- the retired tables are gone from the code (static, AST). No module
   under `src/` names `AgendaStepRequirement` or `QuestOfferRequirement`,
   nor uses `agenda_step_requirement` or `quest_offer_requirement` as a
   whole string.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that collects nothing fails.
"""
from __future__ import annotations

import ast
import itertools
import os
import pathlib
import sys
import tempfile
from datetime import UTC, datetime

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
FORMS_FILE = SRC / "condition_forms.py"

FAILURES: list[str] = []

FORM_NAMES = (
    "REQUIREMENT_TYPES", "MODEL_REQUIREMENT_TYPES", "ENTITY_TARGET_TYPES", "KEY_TARGET_TYPES",
    "THRESHOLD_TYPES", "_EVALUATORS", "RequirementSpec", "Verdict", "evaluate_specs", "_day_reachable_ids",
)

# `Verdict` is a common name: `resolution.Verdict` and `skill_lexicon.Verdict`
# are other things. Every other name is the forms' alone.
UNIQUE_NAMES = tuple(n for n in FORM_NAMES if n != "Verdict")


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _top_level_names(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


def _modules() -> dict[pathlib.Path, set[str]]:
    found: dict[pathlib.Path, set[str]] = {}
    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        found[path] = _top_level_names(ast.parse(path.read_text(encoding="utf-8"), filename=str(path)))
    return found


def _fresh_db() -> str:
    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    return db_path


# --- CA1 -----------------------------------------------------------------------

def check_ca1() -> None:
    modules = _modules()
    if FORMS_FILE not in modules:
        fail("CA1: condition_forms.py is missing")
        return
    home = modules[FORMS_FILE]
    for name in FORM_NAMES:
        if name not in home:
            fail(f"CA1: condition_forms.py does not define {name}")
    evaluators = sorted(n for n in home if n.startswith("_eval_"))
    if not evaluators:
        fail("CA1: condition_forms.py defines zero _eval_* functions")
    for path, names in modules.items():
        if path == FORMS_FILE:
            continue
        rel = path.relative_to(SRC.parent).as_posix()
        for name in UNIQUE_NAMES:
            if name in names:
                fail(f"CA1: {rel} defines {name}, which lives in condition_forms.py")
        for name in sorted(n for n in names if n.startswith("_eval_") and n in evaluators):
            fail(f"CA1: {rel} defines the evaluator {name}, which lives in condition_forms.py")


# --- CB1 -----------------------------------------------------------------------

def _leaf(form="has_met", **kw) -> dict:
    return {"op": "leaf", "type": form, **kw}


def check_cb1() -> None:
    from world_engine.conditions import ConditionShapeError, node_from_dict, node_to_dict

    tree = {"op": "all", "children": [
        _leaf(subject_role="doer", target_entity_id="x"),
        {"op": "any", "children": [_leaf(subject_role="giver", target_entity_id="y"),
                                   {"op": "not", "children": [_leaf(subject_entity_id="z", target_entity_id="x")]}]},
        {"op": "at_least", "n": 2, "children": [_leaf(subject_role="contact", target_entity_id=str(i)) for i in range(3)]},
    ]}
    node = node_from_dict(tree)
    back = node_to_dict(node)
    if [c["op"] for c in back["children"]] != ["leaf", "any", "at_least"] or back["children"][2]["n"] != 2:
        fail(f"CB1: the tree does not round-trip: {back}")
    if node_to_dict(node_from_dict(back)) != back:
        fail("CB1: a round-tripped tree changes on a second pass")
    defaulted = node_from_dict(_leaf(target_entity_id="x"))
    if defaulted.leaf.subject_role != "doer" or defaulted.leaf.subject_entity_id is not None:
        fail(f"CB1: a leaf naming no subject is {defaulted.leaf}")

    deep = _leaf(target_entity_id="x")
    for _ in range(6):
        deep = {"op": "all", "children": [deep]}
    refused = {
        "an unknown connector": {"op": "xor", "children": [_leaf()]},
        "a not with two children": {"op": "not", "children": [_leaf(), _leaf()]},
        "at_least n = 0": {"op": "at_least", "n": 0, "children": [_leaf()]},
        "at_least n above its children": {"op": "at_least", "n": 3, "children": [_leaf(), _leaf()]},
        "an empty all": {"op": "all", "children": []},
        "a leaf naming a role and an entity": _leaf(subject_role="doer", subject_entity_id="z"),
        "an unknown role": _leaf(subject_role="witness"),
        "seven levels": deep,
        "61 nodes": {"op": "all", "children": [_leaf() for _ in range(60)]},
        "a non-integer threshold": _leaf("relation_gte", threshold="50"),
    }
    for label, raw in refused.items():
        try:
            node_from_dict(raw)
        except ConditionShapeError:
            continue
        fail(f"CB1: {label} is accepted")


# --- CB2 -----------------------------------------------------------------------

# The reference: three-valued (Kleene) logic, counted -- `need` of the
# children must be met; unmet once even every unknown met could not reach it.
def _reference(op: str, states: tuple[str, ...], n=None) -> str:
    if op == "not":
        return {"met": "unmet", "unmet": "met", "unknown": "unknown"}[states[0]]
    need = {"all": len(states), "any": 1, "at_least": n}[op]
    met, unknown = states.count("met"), states.count("unknown")
    return "met" if met >= need else "unmet" if met + unknown < need else "unknown"


def check_cb2() -> None:
    from world_engine.conditions import ConditionTree, VerdictNode, _combine

    states = ("met", "unmet", "unknown")
    cases = 0
    for op, n, width in (("all", None, 2), ("any", None, 2), ("at_least", 1, 2), ("at_least", 2, 2),
                         ("not", None, 1), ("at_least", 2, 3)):
        for combo in itertools.product(states, repeat=width):
            children = tuple(VerdictNode(state=st, op="leaf") for st in combo)
            node = ConditionTree(op=op, children=tuple(ConditionTree(op="leaf") for _ in combo), n=n)
            got = _combine(node, children)
            want = _reference(op, combo, n)
            cases += 1
            if got != want:
                fail(f"CB2: {op}{'' if n is None else n} of {combo} is {got}, expected {want}")
    if cases != 9 * 4 + 3 + 27:
        fail(f"CB2: walked {cases} cases")


# --- CB3 -----------------------------------------------------------------------

def _cb_world(session) -> dict:
    from world_engine.models import Character, Entity, Faction, Location, Relation, Rencontre, World

    world = World(name="Conditions CB3", is_active=False)
    session.add(world)
    session.flush()
    ids = {"world": world.id}
    for key in ("place", "far"):
        row = Entity(world_id=world.id, type="location", name=key.capitalize())
        session.add(row)
        session.flush()
        session.add(Location(id=row.id))
        ids[key] = row.id
    for key, kind, where in (("pc", "player", "place"), ("npc", "npc", "far"), ("other", "npc", "place")):
        row = Entity(world_id=world.id, type="character", name=key.upper())
        session.add(row)
        session.flush()
        session.add(Character(id=row.id, world_id=world.id, character_type=kind, current_location_id=ids[where]))
        ids[key] = row.id
    faction = Entity(world_id=world.id, type="faction", name="Guilde")
    session.add(faction)
    session.flush()
    session.add(Faction(id=faction.id))
    ids["faction"] = faction.id
    low, high = sorted((ids["pc"], ids["npc"]))
    now = datetime(2026, 1, 1, tzinfo=UTC)
    session.add(Rencontre(world_id=world.id, entity_lo_id=low, entity_hi_id=high, first_at=now, last_at=now,
                          source="visit"))
    session.add(Relation(world_id=world.id, entity_a_id=ids["npc"], entity_b_id=ids["pc"], type="ami",
                         direction="a_to_b", intensity=60, change_history=[]))
    session.commit()
    return ids


def _spec(form, **kw):
    from world_engine.condition_forms import RequirementSpec

    return RequirementSpec(type=form, **kw)


def _cb3_subjects(session, ids, evaluate, Bindings, leaf) -> None:
    from world_engine.models import Character

    pc = session.get(Character, ids["pc"])
    met_npc = leaf(_spec("has_met", target_entity_id=ids["npc"]))
    if evaluate(met_npc, Bindings(doer=pc), session).state != "met":
        fail("CB3: the doer has met the NPC and the leaf is not met")
    giver_met = leaf(_spec("has_met", subject_role="giver", target_entity_id=ids["pc"]))
    if evaluate(giver_met, Bindings(doer=pc, giver_id=ids["npc"]), session).state != "met":
        fail("CB3: a giver bound to the NPC is not judged on the NPC")
    if evaluate(giver_met, Bindings(doer=pc, giver_id=ids["other"]), session).state != "unmet":
        fail("CB3: a giver bound to another character is not judged on him")
    for bindings, label in ((Bindings(doer=pc, giver_id=ids["faction"]), "n'est pas un personnage"),
                            (Bindings(doer=pc), "n'est pas défini ici")):
        verdict = evaluate(giver_met, bindings, session)
        if verdict.state != "unknown" or verdict.verdict is not None or label not in (verdict.reason or ""):
            fail(f"CB3: an unbindable giver gives {verdict.state}, {verdict.reason!r}")
    contact = leaf(_spec("has_met", subject_role="contact", target_entity_id=ids["pc"]))
    if evaluate(contact, Bindings(doer=pc, contact_id=ids["npc"]), session).state != "met":
        fail("CB3: a contact bound to the NPC is not judged on the NPC")
    fixed = leaf(_spec("has_met", subject_role=None, subject_entity_id=ids["npc"], target_entity_id=ids["pc"]))
    if evaluate(fixed, Bindings(doer=pc), session).state != "met":
        fail("CB3: a fixed subject is not judged on its entity")


def _cb3_connectors(session, ids, evaluate, Bindings, leaf, ConditionTree) -> None:
    from world_engine.models import Character

    pc = session.get(Character, ids["pc"])
    met = leaf(_spec("has_met", target_entity_id=ids["npc"]))
    unknown = leaf(_spec("has_met", subject_role="contact", target_entity_id=ids["pc"]))
    bindings = Bindings(doer=pc)
    either = evaluate(ConditionTree(op="any", children=(unknown, met)), bindings, session)
    both = evaluate(ConditionTree(op="all", children=(unknown, met)), bindings, session)
    negated = evaluate(ConditionTree(op="not", children=(met,)), bindings, session)
    if (either.state, both.state, negated.state) != ("met", "unknown", "unmet"):
        fail(f"CB3: any/all/not give {either.state}, {both.state}, {negated.state}")
    if len(both.leaf_verdicts()) != 1 or len(both.leaf_nodes()) != 2:
        fail("CB3: leaf_verdicts holds an unknown leaf, or leaf_nodes misses one")


def _cb3_reachable(session, ids, evaluate, Bindings, leaf, ConditionTree) -> None:
    from world_engine import conditions
    from world_engine.models import Character

    pc = session.get(Character, ids["pc"])
    calls: list[str] = []
    real = conditions._day_reachable_ids

    def counting(origin, db):
        calls.append(origin)
        return real(origin, db)

    reach = [leaf(_spec("location_reachable", target_entity_id=ids[k])) for k in ("place", "far")]
    reach += [leaf(_spec("location_reachable", subject_role="giver", target_entity_id=ids[k])) for k in ("place", "far")]
    conditions._day_reachable_ids = counting
    try:
        verdict = evaluate(ConditionTree(op="all", children=tuple(reach)), Bindings(doer=pc, giver_id=ids["npc"]), session)
    finally:
        conditions._day_reachable_ids = real
    if sorted(calls) != sorted([ids["place"], ids["far"]]):
        fail(f"CB3: the reachable sets were computed for {calls}, once per subject expected")
    if [n.state for n in verdict.leaf_nodes()] != ["met", "unmet", "unmet", "met"]:
        fail(f"CB3: reachability reads {[n.state for n in verdict.leaf_nodes()]}")


def _cb3_paths(ConditionTree, leaf) -> None:
    from world_engine.conditions import all_of, and_path_leaves, flat_leaves

    a, b, c, d, e = (_spec("has_met", target_entity_id=k) for k in "abcde")
    tree = ConditionTree(op="all", children=(
        leaf(a), ConditionTree(op="any", children=(leaf(b), leaf(c))),
        ConditionTree(op="all", children=(leaf(d),)), ConditionTree(op="not", children=(leaf(e),))))
    if and_path_leaves(tree) != (a, d):
        fail(f"CB3: and_path_leaves gives {and_path_leaves(tree)}")
    if flat_leaves(all_of([a, b])) != (a, b) or flat_leaves(tree) is not None:
        fail("CB3: flat_leaves misreads a flat or a nested tree")
    if flat_leaves(None) != () or flat_leaves(leaf(a)) != (a,) or all_of([]) is not None:
        fail("CB3: no condition, or a lone leaf, is not flat")


def check_cb3(engine) -> None:
    from sqlmodel import Session

    from world_engine.conditions import Bindings, ConditionTree, evaluate, leaf

    with Session(engine) as session:
        ids = _cb_world(session)
        _cb3_subjects(session, ids, evaluate, Bindings, leaf)
        _cb3_connectors(session, ids, evaluate, Bindings, leaf, ConditionTree)
        _cb3_reachable(session, ids, evaluate, Bindings, leaf, ConditionTree)
    _cb3_paths(ConditionTree, leaf)


# --- CB4 -----------------------------------------------------------------------

def check_cb4(engine) -> None:
    from sqlmodel import Session, select

    from world_engine import condition_forms, condition_text, conditions
    from world_engine.models import Character, Entity, World

    if set(condition_text.FORM_PHRASES_FR) != set(condition_forms.REQUIREMENT_TYPES):
        fail(f"CB4: FORM_PHRASES_FR covers {sorted(condition_text.FORM_PHRASES_FR)}")
    if set(condition_text.CONNECTOR_HEADS_FR) != set(conditions.CONNECTORS):
        fail(f"CB4: CONNECTOR_HEADS_FR covers {sorted(condition_text.CONNECTOR_HEADS_FR)}")
    with Session(engine) as session:
        world = session.exec(select(World).where(World.name == "Conditions CB3")).one()
        names = {e.name: e.id for e in session.exec(select(Entity).where(Entity.world_id == world.id)).all()}
        pc = session.get(Character, names["PC"])
        tree = conditions.ConditionTree(op="at_least", n=1, children=(
            conditions.leaf(_spec("relation_gte", target_entity_id=names["NPC"], threshold=50)),
            conditions.leaf(_spec("has_met", subject_role="contact", target_entity_id=names["PC"]))))
        lines = condition_text.describe(session, tree)
        if [(l["depth"], l["text"]) for l in lines] != [
                (0, "Au moins 1 de ces conditions :"), (1, "NPC apprécie le personnage à 50 ou plus"),
                (1, "Le contact a rencontré PC")]:
            fail(f"CB4: describe gives {lines}")
        judged = condition_text.verdict_lines(session, conditions.evaluate(tree, conditions.Bindings(doer=pc), session))
        if [(l["mark"], l["progress"]) for l in judged] != [("✓", None), ("✓", "60/50"), ("?", None)]:
            fail(f"CB4: verdict_lines gives {[(l['mark'], l['progress']) for l in judged]}")
        if "n'est pas défini ici" not in judged[2]["text"]:
            fail(f"CB4: an unknown leaf's line does not say why: {judged[2]['text']!r}")


# --- CB5 -----------------------------------------------------------------------

def check_cb5() -> None:
    forbidden = {"add", "commit", "delete", "execute", "flush"}
    for rel in ("conditions.py", "condition_text.py"):
        path = SRC / rel
        tree = ast.parse(path.read_text(encoding="utf-8"))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
        if not calls:
            fail(f"CB5: {rel} makes zero calls")
        for node in calls:
            if isinstance(node.func, ast.Attribute) and node.func.attr in forbidden:
                fail(f"CB5: {rel}:{node.lineno} calls .{node.func.attr}(")


# --- CC1 -----------------------------------------------------------------------

CONDITION_COLUMNS = ("id", "world_id", "role", "quest_offer_id", "quest_offer_step_id", "agenda_step_id", "created_at")
NODE_COLUMNS = ("id", "world_id", "condition_id", "parent_id", "position", "op", "n", "form", "subject_role",
                "subject_entity_id", "target_entity_id", "target_key", "threshold", "value")
CONDITION_CHECKS = {
    "ck_condition_role": "role IN ('eligibility','prerequisite','completion')",
    "ck_condition_owner": "(quest_offer_id IS NOT NULL) + (quest_offer_step_id IS NOT NULL) + "
                          "(agenda_step_id IS NOT NULL) = 1",
    "ck_condition_owner_role": "(quest_offer_id IS NOT NULL) = (role = 'eligibility')",
}
NODE_CHECKS = {
    "ck_condition_node_op": "op IN ('all','any','not','at_least','leaf')",
    "ck_condition_node_leaf": "(op = 'leaf') = (form IS NOT NULL)",
    "ck_condition_node_connector": "op = 'leaf' OR (subject_role IS NULL AND subject_entity_id IS NULL AND "
                                   "target_entity_id IS NULL AND target_key IS NULL AND threshold IS NULL AND "
                                   "value IS NULL)",
    "ck_condition_node_subject": "op <> 'leaf' OR ((subject_role IS NULL) <> (subject_entity_id IS NULL))",
    "ck_condition_node_role": "subject_role IS NULL OR subject_role IN ('doer','giver','contact')",
    "ck_condition_node_n": "(op = 'at_least') = (n IS NOT NULL) AND (n IS NULL OR n >= 1)",
}


def _check_texts(table) -> dict[str, str]:
    from sqlalchemy import CheckConstraint

    return {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}


def check_cc1() -> None:
    import re

    from world_engine import condition_forms, condition_text, models
    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION

    for model, columns, checks in ((models.Condition, CONDITION_COLUMNS, CONDITION_CHECKS),
                                   (models.ConditionNode, NODE_COLUMNS, NODE_CHECKS)):
        found = tuple(c.name for c in model.__table__.columns)
        if found != columns:
            fail(f"CC1: {model.__tablename__} columns are {found}")
        texts = _check_texts(model.__table__)
        if texts != checks:
            fail(f"CC1: {model.__tablename__} CHECKs are {texts}")
        for name, text in texts.items():
            named = set(re.findall(r"'([^']*)'", text)) & set(condition_forms.REQUIREMENT_TYPES)
            if named:
                fail(f"CC1: {name} names the form(s) {sorted(named)}")
    for constant, check in ((models.CONDITION_ROLES, CONDITION_CHECKS["ck_condition_role"]),
                            (models.CONDITION_OPS, NODE_CHECKS["ck_condition_node_op"])):
        if tuple(constant) != tuple(re.findall(r"'([^']*)'", check)):
            fail(f"CC1: {constant} differs from the CHECK {check}")
    for name in ("AgendaStepRequirement", "QuestOfferRequirement"):
        if hasattr(models, name):
            fail(f"CC1: models still declares {name}")
    major, minor = (int(part) for part in EXPECTED_STATIC_SCHEMA_VERSION.lstrip("v").split("."))
    if (major, minor) < (2, 20):
        fail(f"CC1: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")
    labels = {form: tuple(values) for form, values in condition_text.VALUE_LABELS_FR.items()}
    if labels != {form: tuple(values) for form, values in condition_forms.FORM_VALUES.items()}:
        fail(f"CC1: VALUE_LABELS_FR labels {labels}, not FORM_VALUES")


# --- CC2 -----------------------------------------------------------------------

def _cc_world(session) -> dict:
    from world_engine.models import (
        Agenda, AgendaStep, Character, Entity, Faction, Item, ItemHolding, QuestOffer, QuestOfferStep, World,
    )

    world = World(name="Conditions CC", is_active=False)
    session.add(world)
    session.flush()
    ids = {"world": world.id}
    for key, kind in (("pc", "player"), ("npc", "npc"), ("other", "npc")):
        row = Entity(world_id=world.id, type="character", name=key.upper())
        session.add(row)
        session.flush()
        session.add(Character(id=row.id, world_id=world.id, character_type=kind))
        ids[key] = row.id
    for key, kind in (("guild", "faction"), ("fur", "item")):
        row = Entity(world_id=world.id, type=kind, name={"guild": "Guilde", "fur": "Fourrure"}[key])
        session.add(row)
        session.flush()
        session.add(Faction(id=row.id) if kind == "faction" else Item(id=row.id))
        ids[key] = row.id
    session.add(ItemHolding(world_id=world.id, item_id=ids["fur"], holder_entity_id=ids["pc"], quantity=3,
                            change_history=[]))
    offer = QuestOffer(world_id=world.id, giver_entity_id=ids["npc"], title="La fourrure", change_history=[])
    session.add(offer)
    session.flush()
    step = QuestOfferStep(world_id=world.id, offer_id=offer.id, step_order=1, objective="o", cost=1)
    agenda = Agenda(world_id=world.id, owner_entity_id=ids["pc"], title="La fourrure", status="paused",
                    change_history=[])
    session.add(step)
    session.add(agenda)
    session.flush()
    agenda_step = AgendaStep(agenda_id=agenda.id, step_order=1, objective="o", status="active", change_history=[])
    session.add(agenda_step)
    session.commit()
    ids.update(offer=offer.id, offer_step=step.id, agenda=agenda.id, agenda_step=agenda_step.id)
    return ids


def _rows(session) -> tuple[int, int]:
    from sqlmodel import func, select

    from world_engine.models import Condition, ConditionNode

    return (session.exec(select(func.count()).select_from(Condition)).one(),
            session.exec(select(func.count()).select_from(ConditionNode)).one())


def _cc2_round_trip(session, ids) -> None:
    from world_engine.conditions import ConditionTree, all_of, leaf, read_condition
    from world_engine.writes.conditions import write_condition

    tree = ConditionTree(op="all", children=(
        leaf(_spec("item_held", target_entity_id=ids["fur"], threshold=2)),
        ConditionTree(op="any", children=(
            leaf(_spec("has_met", subject_role="giver", target_entity_id=ids["pc"])),
            ConditionTree(op="not", children=(leaf(_spec("vital_status", subject_role=None,
                                                         subject_entity_id=ids["other"], value="dead")),)))),
        ConditionTree(op="at_least", n=1, children=(
            leaf(_spec("quest_state", target_key=ids["offer"], value="failed")),
            leaf(_spec("has_debt_to", subject_role="contact", target_entity_id=ids["guild"]))))))
    write_condition(session, world_id=ids["world"], role="completion", tree=tree, agenda_step_id=ids["agenda_step"])
    session.commit()
    if read_condition(session, role="completion", agenda_step_id=ids["agenda_step"]) != tree:
        fail(f"CC2: the stored tree reads back as {read_condition(session, role='completion', agenda_step_id=ids['agenda_step'])}")
    smaller = all_of([_spec("has_met", target_entity_id=ids["npc"])])
    write_condition(session, world_id=ids["world"], role="completion", tree=smaller, agenda_step_id=ids["agenda_step"])
    session.commit()
    if read_condition(session, role="completion", agenda_step_id=ids["agenda_step"]) != smaller or _rows(session) != (1, 2):
        fail(f"CC2: a second write did not replace the first whole: {_rows(session)}")
    write_condition(session, world_id=ids["world"], role="completion", tree=None, agenda_step_id=ids["agenda_step"])
    session.commit()
    if read_condition(session, role="completion", agenda_step_id=ids["agenda_step"]) is not None or _rows(session) != (0, 0):
        fail("CC2: writing no tree kept a condition")


def _cc2_refusals(session, ids) -> None:
    from world_engine.conditions import ConditionTree, all_of, leaf
    from world_engine.writes.conditions import write_condition

    def one(spec):
        return all_of([spec])

    cases = {
        "an unknown form": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite", one(_spec("owes_a_favour"))),
        "a quest_state with no value": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite",
                                        one(_spec("quest_state", target_key=ids["offer"]))),
        "a quest_state with an unknown value": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite",
                                                one(_spec("quest_state", target_key=ids["offer"], value="won"))),
        "a vital_status naming a target": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite",
                                           one(_spec("vital_status", target_entity_id=ids["npc"], value="dead"))),
        "an item_held aimed at a character": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite",
                                              one(_spec("item_held", target_entity_id=ids["npc"], threshold=1))),
        "a faction as fixed subject": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite",
                                       one(_spec("has_met", subject_role=None, subject_entity_id=ids["guild"],
                                                 target_entity_id=ids["pc"]))),
        "an eligibility on an agenda step": ({"agenda_step_id": ids["agenda_step"]}, "eligibility",
                                             one(_spec("has_met", target_entity_id=ids["npc"]))),
        "two owners": ({"agenda_step_id": ids["agenda_step"], "quest_offer_step_id": ids["offer_step"]},
                       "prerequisite", one(_spec("has_met", target_entity_id=ids["npc"]))),
        "a not with two children": ({"agenda_step_id": ids["agenda_step"]}, "prerequisite", ConditionTree(
            op="not", children=(leaf(_spec("has_met", target_entity_id=ids["npc"])),) * 2)),
    }
    for label, (owner, role, tree) in cases.items():
        before = _rows(session)
        try:
            write_condition(session, world_id=ids["world"], role=role, tree=tree, **owner)
        except ValueError:
            session.rollback()
            if _rows(session) != before:
                fail(f"CC2: refusing {label} wrote rows")
            continue
        session.rollback()
        fail(f"CC2: write_condition accepts {label}")


def check_cc2(engine) -> None:
    from sqlmodel import Session

    with Session(engine) as session:
        ids = _cc_world(session)
        _cc2_round_trip(session, ids)
        _cc2_refusals(session, ids)


# --- CC3 -----------------------------------------------------------------------

MIGRATION = ROOT / "scripts" / "migrate_v2_20_conditions.py"

# Both requirement tables as v2.19 created them (dumped from `main` at 2cdc92c).
_V219_DDL = (
    """CREATE TABLE agenda_step_requirement (
	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, step_id VARCHAR NOT NULL, type VARCHAR NOT NULL,
	target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER, PRIMARY KEY (id),
	CONSTRAINT ck_agenda_step_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed','has_debt_to','no_debt_to')),
	CONSTRAINT ck_agenda_step_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable','has_met','faction_member','has_debt_to','no_debt_to') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)),
	FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(step_id) REFERENCES agenda_step (id),
	FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
    "CREATE UNIQUE INDEX idx_agenda_step_requirement_unique ON agenda_step_requirement "
    "(step_id, type, target_entity_id, target_key)",
    """CREATE TABLE quest_offer_requirement (
	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, offer_id VARCHAR NOT NULL, step_id VARCHAR,
	type VARCHAR NOT NULL, target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER, PRIMARY KEY (id),
	CONSTRAINT ck_quest_offer_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed','has_debt_to','no_debt_to')),
	CONSTRAINT ck_quest_offer_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable','has_met','faction_member','has_debt_to','no_debt_to') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)),
	FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(offer_id) REFERENCES quest_offer (id),
	FOREIGN KEY(step_id) REFERENCES quest_offer_step (id), FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
    "CREATE INDEX idx_quest_offer_requirement_offer ON quest_offer_requirement (offer_id)",
)


def _cc3_seed(db_path: str) -> dict:
    """A second database: the current schema, its condition tables dropped
    and the two v2.19 tables laid back, with rows."""
    import sqlite3

    from sqlalchemy import create_engine
    from sqlmodel import Session, SQLModel

    from world_engine.models import SchemaMeta

    eng = create_engine(f"sqlite:///{db_path}")
    SQLModel.metadata.create_all(eng)
    with Session(eng) as session:
        ids = _cc_world(session)
        session.add(SchemaMeta(id=1, static_version="v2.19"))
        session.commit()
    eng.dispose()
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=OFF")
        conn.execute("DROP TABLE condition_node")
        conn.execute("DROP TABLE condition")
        for statement in _V219_DDL:
            conn.execute(statement)
        w = ids["world"]
        rows = (
            ("quest_offer_requirement", "qor-1", ids["offer"], None, "faction_member", ids["guild"], None, None),
            ("quest_offer_requirement", "qor-2", ids["offer"], ids["offer_step"], "has_met", ids["npc"], None, None),
            ("quest_offer_requirement", "qor-3", ids["offer"], ids["offer_step"], "quest_completed", None,
             ids["offer"], None),
        )
        for _t, rid, offer, step, form, entity, key, threshold in rows:
            conn.execute("INSERT INTO quest_offer_requirement (id, world_id, offer_id, step_id, type, target_entity_id, "
                         "target_key, threshold) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                         (rid, w, offer, step, form, entity, key, threshold))
        for rid, form, entity, threshold in (("asr-b", "relation_gte", ids["npc"], 40),
                                             ("asr-a", "has_met", ids["other"], None)):
            conn.execute("INSERT INTO agenda_step_requirement (id, world_id, step_id, type, target_entity_id, threshold) "
                         "VALUES (?, ?, ?, ?, ?, ?)", (rid, w, ids["agenda_step"], form, entity, threshold))
        conn.execute("INSERT INTO session (id, world_id, number) VALUES ('orphan-session', 'gone-world', 9)")
    return ids


def _cc3_run(db_path: str):
    import subprocess

    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True, text=True,
                          cwd=str(ROOT), timeout=120)


def _cc3_state(db_path: str) -> dict:
    import sqlite3

    with sqlite3.connect(db_path) as conn:
        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        trees = {}
        if "condition_node" in tables:
            for column in ("quest_offer_id", "quest_offer_step_id", "agenda_step_id"):
                for cid, owner, role in conn.execute(f"SELECT id, {column}, role FROM condition WHERE {column} IS NOT NULL"):
                    nodes = conn.execute("SELECT op, form, subject_role, target_entity_id, target_key, threshold, value, "
                                         "parent_id IS NULL FROM condition_node WHERE condition_id = ? "
                                         "ORDER BY parent_id IS NOT NULL, position", (cid,)).fetchall()
                    trees[(column, owner, role)] = nodes
        return {
            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
            "tables": sorted(t for t in tables if t.endswith("requirement") or t.startswith("condition")),
            "trees": trees,
        }


def check_cc3() -> None:
    import sqlite3

    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION

    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "v2_19.db")
    ids = _cc3_seed(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_meta SET static_version = 'v2.18' WHERE id = 1")
    before = _cc3_state(db_path)
    result = _cc3_run(db_path)
    if result.returncode == 0 or _cc3_state(db_path) != before:
        fail("CC3: the migration ran on a v2.18 database or changed it")
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE schema_meta SET static_version = 'v2.19' WHERE id = 1")
    result = _cc3_run(db_path)
    if result.returncode != 0:
        fail(f"CC3: the migration failed: {result.stdout[-400:]} {result.stderr[-400:]}")
        return
    after = _cc3_state(db_path)
    if after["tables"] != ["condition", "condition_node"]:
        fail(f"CC3: the tables are {after['tables']}")
    root = ("all", None, None, None, None, None, None, 1)
    expected = {
        ("quest_offer_id", ids["offer"], "eligibility"): [
            root, ("leaf", "faction_member", "doer", ids["guild"], None, None, None, 0)],
        ("quest_offer_step_id", ids["offer_step"], "prerequisite"): [
            root, ("leaf", "has_met", "doer", ids["npc"], None, None, None, 0),
            ("leaf", "quest_state", "doer", None, ids["offer"], None, "completed", 0)],
        ("agenda_step_id", ids["agenda_step"], "prerequisite"): [
            root, ("leaf", "relation_gte", "doer", ids["npc"], None, 40, None, 0),
            ("leaf", "has_met", "doer", ids["other"], None, None, None, 0)],
    }
    if after["trees"] != expected:
        fail(f"CC3: the trees are {after['trees']}")
    if after["version"] != EXPECTED_STATIC_SCHEMA_VERSION or "Note: session rowid" not in result.stdout:
        fail(f"CC3: schema_meta is {after['version']}, or the orphan session was not noted")
    with sqlite3.connect(db_path) as conn:
        dangling = [r for t in ("condition", "condition_node")
                    for r in conn.execute(f"PRAGMA foreign_key_check({t})").fetchall()]
    if dangling:
        fail(f"CC3: foreign_key_check {dangling}")
    again = _cc3_run(db_path)
    if again.returncode != 0 or _cc3_state(db_path) != after:
        fail(f"CC3: a second run exit {again.returncode} or changed a row")


# --- CC4 -----------------------------------------------------------------------

def _cc4_forms(session, ids) -> None:
    from world_engine.condition_forms import _EVALUATORS
    from world_engine.models import Agenda, Character, Quest

    pc = session.get(Character, ids["pc"])

    def met(form, **kw):
        return _EVALUATORS[form](_spec(form, **kw), pc, session, None).met

    if not met("item_held", target_entity_id=ids["fur"], threshold=3) or met("item_held", target_entity_id=ids["fur"],
                                                                              threshold=4):
        fail("CC4: item_held does not read the holding of 3")
    if not met("vital_status", value="alive") or met("vital_status", value="dead"):
        fail("CC4: vital_status does not read the character's state")
    session.add(Quest(world_id=ids["world"], offer_id=ids["offer"], character_id=ids["pc"], agenda_id=ids["agenda"]))
    session.commit()
    for status, value in (("paused", "open"), ("failed", "failed"), ("abandoned", "abandoned")):
        agenda = session.get(Agenda, ids["agenda"])
        agenda.status = status
        session.add(agenda)
        session.commit()
        others = [v for v in ("open", "completed", "failed", "abandoned") if v != value]
        if not met("quest_state", target_key=ids["offer"], value=value) or any(
                met("quest_state", target_key=ids["offer"], value=v) for v in others):
            fail(f"CC4: quest_state misreads an agenda {status}")
    agenda = session.get(Agenda, ids["agenda"])
    agenda.status = "paused"
    session.add(agenda)
    session.commit()


def _cc4_consumers(session, ids) -> None:
    from world_engine.cockpit.routes.day import _account_rendezvous
    from world_engine.conditions import ConditionTree, leaf
    from world_engine.day_plan import evaluate_agenda_step
    from world_engine.day_resolve import blocked_details_fr
    from world_engine.models import AgendaStep, Character, ProposedMutation
    from world_engine.writes.conditions import write_condition

    pc = session.get(Character, ids["pc"])
    tree = ConditionTree(op="all", children=(
        ConditionTree(op="any", children=(leaf(_spec("relation_gte", target_entity_id=ids["other"], threshold=10)),)),
        leaf(_spec("relation_gte", target_entity_id=ids["npc"], threshold=1)),
        leaf(_spec("has_met", subject_role="giver", target_entity_id=ids["pc"])),
        ConditionTree(op="not", children=(leaf(_spec("item_held", target_entity_id=ids["fur"], threshold=1)),))))
    write_condition(session, world_id=ids["world"], role="prerequisite", tree=tree, agenda_step_id=ids["agenda_step"])
    session.commit()
    evaluated = evaluate_agenda_step(session.get(AgendaStep, ids["agenda_step"]), pc, session)
    giver_leaf = evaluated.verdict.children[2]
    if giver_leaf.state == "unknown" or giver_leaf.verdict is None:
        fail(f"CC4: the quest's giver is not bound: {giver_leaf.reason}")
    applied = ProposedMutation(world_id=ids["world"], mutation_type="agenda_step_change", status="applied",
                               payload={"step_id": ids["agenda_step"]})
    armed = _account_rendezvous([applied], session)
    if armed is None or armed["npc_id"] != ids["npc"]:
        fail(f"CC4: the day's NPC is {armed}, expected the relation_gte reached through all")
    details = blocked_details_fr(evaluated.verdict, session)
    if not any(d.startswith("il ne faut pas que") and "Fourrure" in d for d in details):
        fail(f"CC4: the blocked details miss the negated leaf: {details}")


def check_cc4(engine) -> None:
    from sqlmodel import Session, select

    from world_engine.models import World

    with Session(engine) as session:
        world = session.exec(select(World).where(World.name == "Conditions CC")).one()
        ids = _cc_ids(session, world.id)
        _cc4_forms(session, ids)
        _cc4_consumers(session, ids)


def _cc_ids(session, world_id: str) -> dict:
    from sqlmodel import select

    from world_engine.models import Agenda, AgendaStep, Entity, QuestOffer, QuestOfferStep

    names = {e.name: e.id for e in session.exec(select(Entity).where(Entity.world_id == world_id)).all()}
    offer = session.exec(select(QuestOffer).where(QuestOffer.world_id == world_id)).one()
    agenda = session.exec(select(Agenda).where(Agenda.world_id == world_id)).one()
    return {"world": world_id, "pc": names["PC"], "npc": names["NPC"], "other": names["OTHER"],
            "guild": names["Guilde"], "fur": names["Fourrure"], "offer": offer.id,
            "offer_step": session.exec(select(QuestOfferStep).where(QuestOfferStep.offer_id == offer.id)).one().id,
            "agenda": agenda.id,
            "agenda_step": session.exec(select(AgendaStep).where(AgendaStep.agenda_id == agenda.id)).one().id}


# --- CC5 -----------------------------------------------------------------------

RETIRED_NAMES = {"AgendaStepRequirement", "QuestOfferRequirement"}
RETIRED_TABLES = {"agenda_step_requirement", "quest_offer_requirement"}


def check_cc5() -> None:
    walked = 0
    for path in sorted(SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        walked += 1
        rel = path.relative_to(SRC.parent).as_posix()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            name = (node.id if isinstance(node, ast.Name) else node.attr if isinstance(node, ast.Attribute)
                    else node.name if isinstance(node, ast.alias) else None)
            if name in RETIRED_NAMES:
                fail(f"CC5: {rel}:{getattr(node, 'lineno', '?')} names {name}")
            if isinstance(node, ast.Constant) and node.value in RETIRED_TABLES:
                fail(f"CC5: {rel}:{node.lineno} uses the table name {node.value!r}")
    if not walked:
        fail("CC5: walked zero modules")


def main() -> int:
    _fresh_db()
    check_ca1()
    check_cb1()
    check_cb2()
    from world_engine.db import create_db_and_tables, engine
    create_db_and_tables()
    check_cb3(engine)
    check_cb4(engine)
    check_cb5()
    check_cc1()
    check_cc2(engine)
    check_cc3()
    check_cc4(engine)
    check_cc5()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: conditions -- the requirement forms, their evaluators and their BFS live in "
          "condition_forms.py alone; a condition is a tree of four connectors over those forms, "
          "shape-checked, judged in three values on each leaf's subject, and read back in French "
          "without writing anything; v2.20 stores it as rows, one tree per owner and role, converted "
          "from the two requirement tables it drops; every agenda judges it, binding a quest's giver")
    return 0


if __name__ == "__main__":
    sys.exit(main())
