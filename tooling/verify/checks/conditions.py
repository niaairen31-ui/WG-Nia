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
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: conditions -- the requirement forms, their evaluators and their BFS live in "
          "condition_forms.py alone; a condition is a tree of four connectors over those forms, "
          "shape-checked, judged in three values on each leaf's subject, and read back in French "
          "without writing anything")
    return 0


if __name__ == "__main__":
    sys.exit(main())
