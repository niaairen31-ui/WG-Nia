"""G1 check for TICKET-0092 (BRIEF-0092-A) — the name index (N1c, N2b, N17a).

`src/world_engine/name_index.py` is the one source of every name surface of
a world: active entity names plus `appellation` facts, filtered by the
regime of a `NameScope`. The tokenizer (`prose_tokens.py`) builds its index
on it.

R1 (purity) -- `name_index.py` contains no `db.add(`, `.commit(`, `chat(`.
R2 (world scoping) -- every `select(` call in `name_index.py` sits in a
   method chain carrying a `.where(` whose arguments name `world_id`; zero
   `select(` calls fails.
R3 (regime bijection) -- the `REGIMES` tuple literal equals the key set of
   the `_APPELLATION_RULES` dict literal.
R4 (lazy exclusion) -- no module-level import of `facet_reads` in
   `name_index.py` (the cycle of R-07), and at least one
   `creator_only_fact_ids(` call inside a function body.
R5 (creator confinement) -- across `src/world_engine/**/*.py`, `CREATOR`
   imported from `name_index` (or read as `name_index.CREATOR`) and any
   `NameScope(` call whose regime is the literal `"creator"` occur only in
   `name_index.py`, `lore_query.py`, `lore_mentions_read.py`,
   `writes/facets.py`. Vacuity guard: at least one file parsed.
R6 (explicit scope, BRIEF-0092-b) -- across `src/world_engine/**/*.py`, every
   call whose callee name (a Name, or the last part of an Attribute) is
   `resolve_named` or `near_candidates` passes a `scope=` keyword; every call
   whose callee name is `surfaces` or `name_surfaces` has three positional
   arguments or a `scope=` keyword. Vacuity guard: at least one
   `resolve_named` call found.
F1 (fixture) -- the LOT's "Regimes" case table against `surfaces`, with
   exact set equality on `(source, entity_id, fact_id)`; malformed
   `NameScope`s raise `ValueError`.
F2 (fixture) -- the tokenizer: a creator-only or unscoped appellation is
   never indexed; a scoped one is; an appellation's own text is stored
   plain for other appellations and names its other entities (N15b); a new
   appellation on a character defaults to `rencontre` on it (N14b).

Fixtures run on a fresh temp-file SQLite database
(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import — never
Nia's DB). REPORT-ONLY: the number of fixture `appellation` facts with no
scope. FAILURES list, print FAIL lines, exit 1.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
PKG = SRC / "world_engine"
TARGET = PKG / "name_index.py"
CREATOR_ALLOWED = {
    "src/world_engine/name_index.py",
    "src/world_engine/lore_query.py",
    "src/world_engine/lore_mentions_read.py",
    "src/world_engine/writes/facets.py",
}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _call_name(node: ast.Call):
    func = node.func
    return func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)


def _tree():
    if not TARGET.exists():
        fail("name_index: src/world_engine/name_index.py is missing")
        return None
    return ast.parse(TARGET.read_text(encoding="utf-8"))


# --- R1 / R2 / R3 / R4 --------------------------------------------------------

def check_purity(tree) -> None:
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)]
    if not calls:
        fail("R1: zero calls in name_index.py -- scan is broken")
    for node in calls:
        name = _call_name(node)
        receiver = node.func.value if isinstance(node.func, ast.Attribute) else None
        if name == "add" and isinstance(receiver, ast.Name) and receiver.id == "db":
            fail(f"R1 name_index.py:{node.lineno} calls db.add(")
        if name == "commit" and isinstance(node.func, ast.Attribute):
            fail(f"R1 name_index.py:{node.lineno} calls .commit(")
        if name == "chat":
            fail(f"R1 name_index.py:{node.lineno} calls chat(")


def _chain_where_names(node: ast.Call, parents: dict) -> set[str]:
    """Names in the arguments of every `.where(` of the method chain above `node`."""
    names: set[str] = set()
    current = node
    while True:
        attr = parents.get(id(current))
        if not isinstance(attr, ast.Attribute):
            return names
        call = parents.get(id(attr))
        if not isinstance(call, ast.Call) or call.func is not attr:
            return names
        if attr.attr == "where":
            for arg in list(call.args) + [k.value for k in call.keywords]:
                names |= {n.id for n in ast.walk(arg) if isinstance(n, ast.Name)}
        current = call


def check_world_scoping(tree) -> None:
    parents = {id(child): node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    selects = [n for n in ast.walk(tree)
               if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "select"]
    if not selects:
        fail("R2: zero select( calls in name_index.py -- scan is broken")
    for node in selects:
        if "world_id" not in _chain_where_names(node, parents):
            fail(f"R2 name_index.py:{node.lineno} select( has no .where( naming world_id")


def _module_literal(tree, name: str):
    for node in tree.body:
        targets = [node.target] if isinstance(node, ast.AnnAssign) else getattr(node, "targets", [])
        if any(isinstance(t, ast.Name) and t.id == name for t in targets) and node.value is not None:
            return node.value
    return None


def check_regime_bijection(tree) -> None:
    regimes = _module_literal(tree, "REGIMES")
    rules = _module_literal(tree, "_APPELLATION_RULES")
    if not isinstance(regimes, ast.Tuple) or not isinstance(rules, ast.Dict):
        fail("R3: REGIMES tuple literal or _APPELLATION_RULES dict literal not found")
        return
    listed = [e.value for e in regimes.elts if isinstance(e, ast.Constant)]
    keys = [k.value for k in rules.keys if isinstance(k, ast.Constant)]
    if not listed or len(listed) != len(regimes.elts) or len(keys) != len(rules.keys):
        fail("R3: REGIMES or _APPELLATION_RULES holds a non-literal entry")
    if sorted(listed) != sorted(keys) or len(set(keys)) != len(keys):
        fail(f"R3: REGIMES {listed!r} != _APPELLATION_RULES keys {keys!r}")


def check_lazy_exclusion(tree) -> None:
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("facet_reads"):
            fail(f"R4 name_index.py:{node.lineno} imports facet_reads at module level")
        if isinstance(node, ast.Import) and any(a.name.endswith("facet_reads") for a in node.names):
            fail(f"R4 name_index.py:{node.lineno} imports facet_reads at module level")
    inside = [
        n for fn in ast.walk(tree) if isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef))
        for n in ast.walk(fn) if isinstance(n, ast.Call) and _call_name(n) == "creator_only_fact_ids"
    ]
    if not inside:
        fail("R4: no creator_only_fact_ids( call inside a function body of name_index.py")


# --- R5 -----------------------------------------------------------------------

def _creator_uses(tree) -> list[int]:
    lines = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("name_index"):
            lines += [node.lineno for a in node.names if a.name == "CREATOR"]
        if isinstance(node, ast.Attribute) and node.attr == "CREATOR" \
                and isinstance(node.value, ast.Name) and node.value.id == "name_index":
            lines.append(node.lineno)
        if isinstance(node, ast.Call) and _call_name(node) == "NameScope":
            regime = node.args[0] if node.args else next(
                (k.value for k in node.keywords if k.arg == "regime"), None)
            if isinstance(regime, ast.Constant) and regime.value == "creator":
                lines.append(node.lineno)
    return lines


def check_creator_confinement() -> None:
    files = sorted(PKG.rglob("*.py"))
    if not files:
        fail("R5: zero Python files parsed under src/world_engine -- scan is broken")
        return
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        if rel in CREATOR_ALLOWED:
            continue
        for line in _creator_uses(ast.parse(path.read_text(encoding="utf-8"))):
            fail(f"R5 {rel}:{line} uses the creator name regime outside its allow-list")


# --- R6 -----------------------------------------------------------------------

def check_explicit_scope() -> None:
    resolve_calls = 0
    for path in sorted(PKG.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Call):
                continue
            name = _call_name(node)
            has_scope = any(k.arg == "scope" for k in node.keywords)
            if name == "resolve_named":
                resolve_calls += 1
            if name in ("resolve_named", "near_candidates") and not has_scope:
                fail(f"R6 {rel}:{node.lineno} calls {name}( without scope=")
            if name in ("surfaces", "name_surfaces") and len(node.args) != 3 and not has_scope:
                fail(f"R6 {rel}:{node.lineno} calls {name}( without a scope")
    if not resolve_calls:
        fail("R6: zero resolve_named( calls under src/world_engine -- scan is broken")


# --- fixtures -----------------------------------------------------------------

def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def _world(session, label: str):
    from world_engine.models import Entity, World

    world = World(name=label, is_active=False)
    session.add(world)
    session.flush()

    def entity(kind: str, name: str):
        row = Entity(world_id=world.id, type=kind, name=name)
        session.add(row)
        session.flush()
        return row

    return world, entity


def _appellation(session, owner, content, scope=None):
    from world_engine.writes.facets import add_entity_fact

    return add_entity_fact(session, entity_id=owner.id, facet="appellation", content=content,
                           created_by="check", scope=scope)


def _make_creator_only(session, owner, fact) -> None:
    from world_engine.writes.knowledge import write_knowledge

    write_knowledge(session, entity_id=owner.id, fact_id=fact.id, subject="creator_meta",
                    level="unaware", is_secret=True, changed_by="check")
    session.flush()


def check_regimes(engine) -> None:
    from sqlmodel import Session

    from world_engine.name_index import NameScope, surfaces
    from world_engine.writes.facets import ScopeChoice

    with Session(engine) as session:
        world, entity = _world(session, "F1 World")
        q = entity("character", "Quill")
        a1 = _appellation(session, q, "le Passeur", ScopeChoice("rencontre", q.id))
        a2 = _appellation(session, q, "la Plume", ScopeChoice("none"))
        a3 = _appellation(session, q, "le Veilleur", ScopeChoice("world"))
        _make_creator_only(session, q, a3)
        x = entity("character", "Xander")
        a4 = _appellation(session, x, "le Banni", ScopeChoice("world"))
        x.status = "inactive"
        session.flush()
        name_q = ("name", q.id, None)
        table = [
            ("names_only", NameScope("names_only"), {name_q}),
            ("creator", NameScope("creator"), {name_q, ("appellation", q.id, a1.id),
                                               ("appellation", q.id, a2.id),
                                               ("appellation", q.id, a3.id)}),
            ("prose", NameScope("prose"), {name_q, ("appellation", q.id, a1.id)}),
            ("perceiver", NameScope("perceiver", known_fact_ids=frozenset({a2.id, a3.id})),
             {name_q, ("appellation", q.id, a2.id)}),
            ("prose, exclude Q", NameScope("prose", exclude_entity_id=q.id), set()),
        ]
        for label, scope, expected in table:
            got = {(s.source, s.entity_id, s.fact_id) for s in surfaces(session, world.id, scope)}
            if got != expected:
                fail(f"F1 {label}: {sorted(got, key=str)!r} != {sorted(expected, key=str)!r}")
        if a4.id in {s.fact_id for s in surfaces(session, world.id, NameScope("creator"))}:
            fail("F1: an inactive entity's appellation surfaced")
        session.rollback()
    for args, kwargs in ((("perceiver",), {}), (("creator",), {"known_fact_ids": frozenset()}),
                         (("nope",), {})):
        try:
            NameScope(*args, **kwargs)
        except ValueError:
            continue
        fail(f"F1: NameScope{args!r} {kwargs!r} did not raise ValueError")


def _unchanged_case(engine, label, make_creator_only, scope_choice) -> None:
    from sqlmodel import Session

    from world_engine.prose_tokens import tokenize

    with Session(engine) as session:
        world, entity = _world(session, f"F2 {label}")
        q = entity("character", "Quill")
        fact = _appellation(session, q, "le Masque", scope_choice)
        if make_creator_only:
            _make_creator_only(session, q, fact)
        got = tokenize(session, world_id=world.id, text="Le Masque parle.").text
        if got != "Le Masque parle.":
            fail(f"F2 {label}: {got!r} != 'Le Masque parle.'")
        session.commit()


def check_tokenizer(engine) -> None:
    from sqlmodel import Session, select

    from world_engine.models import FactDefault
    from world_engine.prose_render import entity_token, fact_text
    from world_engine.prose_tokens import tokenize
    from world_engine.writes.facets import ScopeChoice

    _unchanged_case(engine, "(i) creator-only", True, None)
    _unchanged_case(engine, "(ii) unscoped", False, ScopeChoice("none"))
    with Session(engine) as session:
        world, entity = _world(session, "F2 (iii)-(iv)")
        y, q = entity("character", "Yra"), entity("character", "Quill")
        _appellation(session, y, "la reine")
        got = tokenize(session, world_id=world.id, text="la reine arrive.").text
        if got != entity_token(y.id, "Yra") + " arrive.":
            fail(f"F2 (iii): scoped appellation not tokenized: {got!r}")
        own = _appellation(session, q, "la reine")
        y.name = "Ysolde"
        session.flush()
        if fact_text(session, own) != "la reine":
            fail(f"F2 (iv): appellation text not stored plain: {fact_text(session, own)!r}")
        session.commit()
    with Session(engine) as session:
        world, entity = _world(session, "F2 (v)-(vi)")
        q, aldric = entity("character", "Quill"), entity("character", "Aldric")
        fact = _appellation(session, q, "la fille du vieil Aldric")
        aldric.name = "Aldo"
        session.flush()
        if fact_text(session, fact) != "la fille du vieil Aldo":
            fail(f"F2 (v): other entity's name not tokenized: {fact_text(session, fact)!r}")
        rows = session.exec(select(FactDefault).where(FactDefault.fact_id == fact.id)).all()
        if [(r.scope_type, r.scope_id) for r in rows] != [("rencontre", q.id)]:
            fail(f"F2 (vi): defaults {[(r.scope_type, r.scope_id) for r in rows]!r} "
                 f"!= [('rencontre', {q.id!r})]")
        session.commit()


def _report_unscoped(engine) -> None:
    from sqlmodel import Session, select

    from world_engine.models import Fact
    from world_engine.name_index import _scoped_fact_ids

    with Session(engine) as session:
        count = 0
        for world_id in set(session.exec(select(Fact.world_id).where(Fact.facet == "appellation")).all()):
            facts = session.exec(select(Fact).where(Fact.world_id == world_id,
                                                    Fact.facet == "appellation")).all()
            count += len(facts) - len(_scoped_fact_ids(session, world_id, list(facts)))
    print(f"REPORT: fixture appellation facts with no scope: {count}")


def main() -> int:
    tree = _tree()
    if tree is not None:
        check_purity(tree)
        check_world_scoping(tree)
        check_regime_bijection(tree)
        check_lazy_exclusion(tree)
    check_creator_confinement()
    check_explicit_scope()
    engine = _fresh_engine()
    check_regimes(engine)
    check_tokenizer(engine)
    _report_unscoped(engine)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: name_index — pure and world-scoped, regimes in bijection with their rules, "
        "creator-only exclusion imported lazily, the creator regime confined, every resolver "
        "call states its scope, the Regimes "
        "table holds, and the tokenizer indexes only scoped non-creator-only appellations"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
