"""G1 check for TICKET-0091 (BRIEF-0091-J) — identity tokens (F1).

A name written into new canon prose is stored as an identity token
`[[e:<entity id>|<name>]]` and rendered to the entity's current name at
read time (`prose_render.py`); `prose_tokens.py` poses the tokens and
`writes/mentions.py` records the names it could not resolve.

R1 (tokens) -- the identifier `content_raw` (the stored, unrendered text of
   `fact` / `knowledge`) appears only in `src/world_engine/models/
   canon_knowledge.py`, `src/world_engine/writes/*.py`,
   `src/world_engine/prose_render.py`, `src/world_engine/knowledge_resolve.py`
   and `scripts/migrate_*.py`, across `src/` and `scripts/`. Comments and
   strings are not identifiers. Vacuity guard: it must be found in the model
   module and in `prose_render.py`.
R2 (fixture) -- `render`: a token becomes the entity's current name; after
   a rename, the new name (a social relation's lien fact renders the renamed
   endpoint); a token whose entity row is gone falls back to its stored
   name; text without tokens is returned unchanged; `None` stays `None`.
R3 (fixture) -- C-14's case table against `tokenize`, plus the write paths:
   a descriptive fact naming two same-named NPCs creates exactly one
   `ambigu` `unresolved_mention` row.
R4 (AST) -- `prose_tokens.py` contains no `chat(` call and imports nothing
   from `ollama_client`: token posing never calls a model.

Fixtures run on a fresh temp-file SQLite database
(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import — never
Nia's DB). REPORT-ONLY: the number of `unresolved_mention` rows the fixture
run created. FAILURES list, print FAIL lines, exit 1.
"""
from __future__ import annotations

import ast
import io
import os
import pathlib
import sys
import tempfile
import tokenize as pytokenize

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
PKG = SRC / "world_engine"
SCRIPTS = ROOT / "scripts"
IDENT = "content_raw"
REQUIRED_HITS = ("src/world_engine/models/canon_knowledge.py", "src/world_engine/prose_render.py")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _allowed(rel: str) -> bool:
    if rel in ("src/world_engine/models/canon_knowledge.py", "src/world_engine/prose_render.py",
               "src/world_engine/knowledge_resolve.py"):
        return True
    if rel.startswith("src/world_engine/writes/") and rel.count("/") == 3:
        return True
    return rel.startswith("scripts/migrate_") and rel.count("/") == 1


# --- R1 -----------------------------------------------------------------------

def check_raw_perimeter() -> None:
    files = sorted(SRC.rglob("*.py")) + sorted(SCRIPTS.glob("*.py"))
    if not files:
        fail("R1: zero Python files examined -- scan is broken")
        return
    hits: set[str] = set()
    for path in files:
        rel = _rel(path)
        source = path.read_text(encoding="utf-8")
        for tok in pytokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == pytokenize.NAME and tok.string == IDENT:
                hits.add(rel)
                if not _allowed(rel):
                    fail(f"R1 {rel}:{tok.start[0]} reads raw stored text ({IDENT}) outside the allow-list")
    for rel in REQUIRED_HITS:
        if rel not in hits:
            fail(f"R1: {IDENT} not found in {rel} -- scan is broken or the model moved")


# --- R4 -----------------------------------------------------------------------

def check_no_model_call() -> None:
    path = PKG / "prose_tokens.py"
    if not path.exists():
        fail("R4: src/world_engine/prose_tokens.py is missing")
        return
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if name == "chat":
                fail(f"R4 prose_tokens.py:{node.lineno} calls chat(")
        if isinstance(node, ast.ImportFrom) and (node.module or "").endswith("ollama_client"):
            fail(f"R4 prose_tokens.py:{node.lineno} imports ollama_client")


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


def check_render(engine) -> None:
    from sqlmodel import Session

    from world_engine.prose_render import entity_token, fact_text, render, render_many
    from world_engine.writes.relations import lien_fact_of, write_relation

    with Session(engine) as session:
        world, entity = _world(session, "R2 World")
        maelis, gone = entity("character", "Maelis"), entity("character", "Oren")
        text = f"{entity_token(maelis.id, 'Maelis')} sert {entity_token(gone.id, 'Oren|]')}."
        if render(session, text) != "Maelis sert Oren.":
            fail(f"R2: token render {render(session, text)!r}")
        maelis.name = "Maelis la Rousse"
        session.flush()
        if render(session, text) != "Maelis la Rousse sert Oren.":
            fail(f"R2: renamed entity not rendered: {render(session, text)!r}")
        session.delete(gone)
        session.flush()
        if render(session, text) != "Maelis la Rousse sert Oren.":
            fail(f"R2: deleted entity does not fall back to its stored name: {render(session, text)!r}")
        if render_many(session, ["sans nom", None]) != ["sans nom", None]:
            fail("R2: plain text / None not returned unchanged")

        bran = entity("character", "Bran")
        rel = write_relation(session, mode="set", world_id=world.id, entity_a_id=maelis.id,
                             entity_b_id=bran.id, type="ally", value=60)
        session.flush()
        lien = lien_fact_of(session, rel)
        bran.name = "Bran le Vieux"
        session.flush()
        if lien is None or "Bran le Vieux" not in fact_text(session, lien):
            fail("R2: renaming an endpoint does not change the rendered lien fact")
        session.rollback()


# C-14 case table: (label, text, mentions, expected text template, expected
# unresolved as (surface, reason, category)). `{X}` in the template is X's token.
def _cases(ids: dict) -> list:
    return [
        ("unique name", "Maelis tient le bar.", None, "{maelis} tient le bar.", ()),
        ("whole words only", "Maelisande passe.", None, "Maelisande passe.", ()),
        ("case and accents folded", "MAÉLIS rit.", None, "{maelis} rit.", ()),
        ("longest match first", "Au Dernier Verre, Verre dort.", None,
         "Au {dernier}, {verre} dort.", ()),
        ("article carried by the name", "Le Dernier Verre ferme.", None, "{dernier} ferme.", ()),
        ("appellation", "La Rousse arrive.", None, "{maelis} arrive.", ()),
        ("same-named -> ambigu", "Garrick attend.", None, "Garrick attend.",
         (("Garrick", "ambigu", "person"),)),
        ("inside a token is skipped", "{maelis} et Maelis.", None, "{maelis} et {maelis}.", ()),
        ("mention unknown -> inconnu", "Ysolde passe.", [{"name": "Ysolde", "category": "person"}],
         "Ysolde passe.", (("Ysolde", "inconnu", "person"),)),
        ("mention overlapping an index match skipped", "Capitaine Bran parle.",
         [{"name": "Capitaine Bran", "category": "person"}], "Capitaine {bran} parle.", ()),
        ("mention resolved by resolve_named", "Valmont Jean arrive.",
         [{"name": "Valmont Jean", "category": "person"}], "{jean} arrive.", ()),
        ("mention absent from text ignored", "Rien.", [{"name": "Ysolde", "category": "person"}],
         "Rien.", ()),
        ("mention covered by the index", "Garrick attend.",
         [{"name": "Garrick", "category": "person"}], "Garrick attend.",
         (("Garrick", "ambigu", "person"),)),
    ]


def check_tokenize(engine) -> None:
    from sqlmodel import Session, select

    from world_engine.models import UnresolvedMention
    from world_engine.prose_render import entity_token
    from world_engine.prose_tokens import tokenize
    from world_engine.writes.facets import add_entity_fact

    with Session(engine) as session:
        world, entity = _world(session, "R3 World")
        maelis, bran = entity("character", "Maelis"), entity("character", "Bran")
        dernier, verre = entity("location", "Le Dernier Verre"), entity("character", "Verre")
        jean = entity("character", "Jean Valmont")
        entity("character", "Garrick")
        entity("character", "Garrick")
        add_entity_fact(session, entity_id=maelis.id, facet="appellation", content="la Rousse",
                        created_by="check")
        tokens = {"maelis": entity_token(maelis.id, "Maelis"), "bran": entity_token(bran.id, "Bran"),
                  "dernier": entity_token(dernier.id, "Le Dernier Verre"),
                  "verre": entity_token(verre.id, "Verre"),
                  "jean": entity_token(jean.id, "Jean Valmont")}
        for label, text, mentions, template, expected in _cases(tokens):
            result = tokenize(session, world_id=world.id, text=text.format(**tokens), mentions=mentions)
            if result.text != template.format(**tokens):
                fail(f"R3 {label}: {result.text!r} != {template.format(**tokens)!r}")
            got = tuple((u.surface, u.reason, u.category) for u in result.unresolved)
            if got != expected:
                fail(f"R3 {label}: unresolved {got!r} != {expected!r}")

        fact = add_entity_fact(session, entity_id=maelis.id, facet="histoire",
                               content="A servi Garrick et Maelis.", created_by="check")
        session.flush()
        rows = session.exec(select(UnresolvedMention).where(UnresolvedMention.fact_id == fact.id)).all()
        if [(r.surface, r.reason) for r in rows] != [("Garrick", "ambigu")]:
            fail(f"R3: two same-named NPCs gave {[(r.surface, r.reason) for r in rows]!r}, "
                 "expected one ambigu row")
        session.commit()


def main() -> int:
    check_raw_perimeter()
    check_no_model_call()
    engine = _fresh_engine()
    check_render(engine)
    check_tokenize(engine)

    from sqlmodel import Session, func, select

    from world_engine.models import UnresolvedMention

    with Session(engine) as session:
        created = session.exec(select(func.count(UnresolvedMention.id))).one()
    print(f"REPORT: unresolved_mention rows created by the fixture run: {created}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: identity_tokens — content_raw read only in the allow-list, render follows "
        "renames and falls back on deleted entities, C-14's case table holds, two "
        "same-named NPCs give one ambigu row, and token posing calls no model"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
