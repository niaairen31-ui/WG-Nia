"""G1 check for TICKET-0095 (K1). Created by BRIEF-0095-A with R0;
BRIEF-0095-B adds L0-L6 (the reader); BRIEF-0095-C adds T0-T10 (the
route).

R0 and L0 are stdlib `ast` only — same FAILURES/fail()/`_rel`/`_parse`/
`ROOT = parents[3]` idiom as `day_rewrite.py`. L1-L6 run on a fresh
temp-file SQLite database (`_fresh_engine`, as in
`day_mention_review_store.py` — never Nia's DB), seeded by `_k1_world`.

R0 (the JSON is write-only, G1): the `candidate_ids` / `evidence_fact_ids`
TEXT columns of `day_mention_choice` are an audit copy; their rows live in
`day_mention_choice_candidate` / `day_mention_choice_evidence`. In every
`.py` under `src/world_engine/`:
  (a) no call whose callee name is `loads` carries, anywhere in its
      arguments, an attribute access `.candidate_ids` / `.evidence_fact_ids`;
  (b) no attribute access `DayMentionChoice.candidate_ids` /
      `DayMentionChoice.evidence_fact_ids` exists (no query on the column).
Vacuity: `writes/pipeline.py` must still hold the `json.dumps(record[
"candidate_ids"], ...)` and `json.dumps(record["evidence_fact_ids"], ...)`
calls that write the audit copy — otherwise R0 guards nothing.

L0 (the reader is read-only, C-05): `lore_choices_read.py` holds no
`chat(` call, no `db.add` / `db.add_all` / `db.commit` call, no `CREATOR`
name or attribute, and no name, attribute or keyword `candidate_ids` /
`evidence_fact_ids`.
L1 (`excerpt_key`, C-04): the judge's key on two measured excerpts.
L2 (`is_reviewable`, E2): accepted, and rejected with a chosen entity, only.
L3 (`preselected_scope`, C2): `world` iff a cited fact has a `world` scope.
L4 (`list_pending_choices`, table b1): reviewable, unreviewed choices of
the world only, in `(created_at, id)` order; another world lists nothing.
L5 (the pending rows, tables b2/b4): measured values per row — excerpt
source, evidence (rendered text, R-10), scopes, preselection, "planned".
L6 (C-06): every row's key set is exactly the pending-row family's.
Vacuity: L4 must have listed four rows.

T0 (the route is thin, C-07): `cockpit/routes/lore_choices.py` holds no
`select(` and no `chat(` call, no `CREATOR` name or attribute, and no name,
attribute or keyword `candidate_ids` / `evidence_fact_ids`.
T1-T10 (the review route, table b3) run after L0-L6 on the same database,
through `fastapi.testclient.TestClient(app)` with `world_engine.cockpit.app`
imported after the fresh engine exists and no `with` block (G11's setup):
T1 the pending list; T2 agreed + appellation at `world`; T3 a second review
is 409; T4 a declined / unknown choice is 404; T5 the five 422 bodies write
nothing; T6 a bad scope rolls back; T7 disagreed with no entity; T8
disagreed with an entity whose surface is already known; T9 agreed without
appellation; T10 the list is empty, five reviews exist, and no choice or
rewrite was added or removed.
Vacuity: T1 must have listed four choices.
"""
from __future__ import annotations

import ast
import os
import pathlib
import sys
import tempfile
import time
from types import SimpleNamespace

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

WRITES_PIPELINE_FILE = SRC / "writes" / "pipeline.py"
READER_FILE = SRC / "lore_choices_read.py"
ROUTE_FILE = SRC / "cockpit" / "routes" / "lore_choices.py"

_JSON_COLUMNS = {"candidate_ids", "evidence_fact_ids"}
_READER_WRITES = {"add", "add_all", "commit"}

PENDING_ROW_KEYS = {
    "id", "surface_form", "category", "trigger", "verdict", "verdict_detail", "excerpt", "reason",
    "day", "chosen", "candidates", "excerpt_source", "evidence", "preselected_scope",
}
DAY_KEYS = {"day_number", "character_name", "declaration", "planned"}

FAILURES: list[str] = []
_TREE_CACHE: dict[pathlib.Path, "ast.Module | None"] = {}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _parse(path: pathlib.Path) -> "ast.Module | None":
    if path in _TREE_CACHE:
        return _TREE_CACHE[path]
    if not path.exists():
        fail(f"{_rel(path)}: file not found")
        _TREE_CACHE[path] = None
        return None
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        fail(f"{_rel(path)}: SyntaxError: {exc}")
        tree = None
    _TREE_CACHE[path] = tree
    return tree


def _callee_name(call: ast.Call) -> "str | None":
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _subscript_key(node: ast.AST) -> "str | None":
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
        value = node.slice.value
        return value if isinstance(value, str) else None
    return None


# ── R0 ───────────────────────────────────────────────────────────────────

def check_json_write_only() -> None:
    for path in sorted(SRC.rglob("*.py")):
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _callee_name(node) == "loads":
                for arg in [*node.args, *(kw.value for kw in node.keywords)]:
                    for sub in ast.walk(arg):
                        if isinstance(sub, ast.Attribute) and sub.attr in _JSON_COLUMNS:
                            fail(
                                f"choice_review R0(a): {_rel(path)}:{node.lineno} parses "
                                f".{sub.attr} — the JSON audit copy is never read; use the rows"
                            )
            if (
                isinstance(node, ast.Attribute)
                and node.attr in _JSON_COLUMNS
                and isinstance(node.value, ast.Name)
                and node.value.id == "DayMentionChoice"
            ):
                fail(
                    f"choice_review R0(b): {_rel(path)}:{node.lineno} references "
                    f"DayMentionChoice.{node.attr} — the JSON audit copy is never queried"
                )

    tree = _parse(WRITES_PIPELINE_FILE)
    if tree is None:
        return
    dumped = {
        _subscript_key(node.args[0])
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _callee_name(node) == "dumps" and node.args
    }
    missing = sorted(_JSON_COLUMNS - dumped)
    if missing:
        fail(
            f"choice_review R0 vacuous: {_rel(WRITES_PIPELINE_FILE)} holds no json.dumps(record[...]) "
            f"for {missing!r}"
        )


# ── L0 ───────────────────────────────────────────────────────────────────

def _node_name(node: ast.AST) -> "str | None":
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    if isinstance(node, ast.keyword):
        return node.arg
    return None


def check_reader_read_only() -> None:
    tree = _parse(READER_FILE)
    if tree is None:
        return
    where = _rel(READER_FILE)
    for node in ast.walk(tree):
        line = getattr(node, "lineno", "?")
        if isinstance(node, ast.Call):
            name = _callee_name(node)
            if name == "chat":
                fail(f"choice_review L0: {where}:{line} calls chat( — the reader calls no model")
            if (
                name in _READER_WRITES
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "db"
            ):
                fail(f"choice_review L0: {where}:{line} calls db.{name} — the reader writes nothing")
        named = _node_name(node)
        if named == "CREATOR" and not isinstance(node, ast.keyword):
            fail(f"choice_review L0: {where}:{line} names CREATOR (R-14)")
        if named in _JSON_COLUMNS:
            fail(f"choice_review L0: {where}:{line} names {named} — rows only (G1)")


# ── L1-L6 fixture ────────────────────────────────────────────────────────

def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
    sys.path.insert(0, str(ROOT / "src"))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def _k1_parents(db) -> dict:
    """Worlds, session, batch, four entities, two facts, one pass_play —
    each writer's row added then flushed (R-18's chain)."""
    from world_engine import models, writes

    ids: dict = {}
    for label, active in (("k1", True), ("other", False)):
        world = models.World(name=label, is_active=active)
        db.add(world)
        db.flush()
        ids[label] = world.id
    game_session = models.Session(world_id=ids["k1"], number=1)
    db.add(game_session)
    db.flush()
    batch = writes.write_batch(db, session_id=game_session.id, changed_by="creator")
    db.add(batch)
    db.flush()
    for key, kind, name in (
        ("aldric", "character", "Aldric"), ("varn", "character", "Maelis Varn"),
        ("orn", "character", "Maelis Orn"), ("tavern", "location", "La Taverne"),
    ):
        entity = models.Entity(world_id=ids["k1"], type=kind, name=name)
        db.add(entity)
        db.flush()
        ids[key] = entity.id
    ids["f_varn"] = writes.add_entity_fact(
        db, entity_id=ids["varn"], facet="histoire", content="Elle tient la forge du port.",
        created_by="creator", scope=writes.ScopeChoice("world"),
    ).id
    ids["f_orn"] = writes.add_entity_fact(
        db, entity_id=ids["orn"], facet="histoire", content="Elle chante à la taverne.",
        created_by="creator", scope=writes.ScopeChoice("location", ids["tavern"]),
    ).id
    pass_play = writes.write_pass_play(
        db, batch_id=batch.id, session_id=game_session.id, character_id=ids["aldric"],
        declared_action="Je vais voir Maelis à la forge.",
    )
    db.add(pass_play)
    db.flush()
    ids["pass_play"] = pass_play.id
    return ids


def _k1_world(engine) -> dict:
    """The K1 fixture (BRIEF-0095-B item 4; C reuses it): c2/c3/c4 written
    by a 409 attempt (no rewrite), c1/c5 by the plan (rewrite first), c5
    reviewed, c6 later. Returns every id by name."""
    from sqlmodel import Session

    from world_engine import writes

    with Session(engine) as db:
        ids = _k1_parents(db)
        db.commit()

    def r(**kw) -> dict:
        record = {
            "category": "person", "surface_form": "Maelis", "trigger": "ambiguous",
            "candidate_ids": [ids["varn"], ids["orn"]], "evidence_fact_ids": [ids["f_varn"], ids["f_orn"]],
            "verdict": "accepted", "chosen_entity_id": ids["varn"], "excerpt": "la forge du port",
            "reason": "r", "verdict_detail": None, "attempts": 1,
        }
        record.update(kw)
        return record

    def write(db, records) -> list[str]:
        return [row.id for row in writes.write_day_mention_choices(
            db, world_id=ids["k1"], pass_play_id=ids["pass_play"], records=records,
        )]

    with Session(engine) as db:
        ids["c2"], ids["c3"], ids["c4"] = write(db, [
            r(surface_form="Maelys", trigger="near", candidate_ids=[ids["orn"]],
              evidence_fact_ids=[ids["f_orn"]], chosen_entity_id=ids["orn"], excerpt="à la forge"),
            r(verdict="rejected", chosen_entity_id=ids["orn"], excerpt="boulanger",
              verdict_detail="excerpt not in the chosen candidate's facts"),
            r(verdict="declined", chosen_entity_id=None, excerpt=None),
        ])
        db.commit()
    time.sleep(0.01)
    with Session(engine) as db:
        writes.write_day_rewrite(
            db, world_id=ids["k1"], pass_play_id=ids["pass_play"], generation=1,
            rendered_text="x", resolutions=[],
        )
        ids["c1"], ids["c5"] = write(db, [r(), r(surface_form="Varn")])
        db.commit()
    with Session(engine) as db:
        writes.write_day_mention_review(
            db, world_id=ids["k1"], choice_id=ids["c5"], verdict="agreed", entity_id=ids["varn"],
            appellation_fact_id=None, appellation_scope=None,
        )
        db.commit()
    with Session(engine) as db:
        (ids["c6"],) = write(db, [r(
            trigger="near", candidate_ids=[ids["orn"]], evidence_fact_ids=[ids["f_orn"]],
            chosen_entity_id=ids["orn"], excerpt="chante",
        )])
        db.commit()
    return ids


# ── L1-L3 (pure) ─────────────────────────────────────────────────────────

def check_pure_rules() -> None:
    from world_engine.day_choice import excerpt_key
    from world_engine.lore_choices_read import is_reviewable, preselected_scope

    for given, expected in (("« la forge du port. »", "forge du port"), (" à ", "")):
        if excerpt_key(given) != expected:
            fail(f"L1: excerpt_key({given!r}) = {excerpt_key(given)!r}, expected {expected!r}")
    for verdict, chosen, expected in (
        ("accepted", "x", True), ("rejected", "x", True), ("rejected", None, False),
        ("declined", None, False), ("failed", None, False),
    ):
        got = is_reviewable(SimpleNamespace(verdict=verdict, chosen_entity_id=chosen))
        if got is not expected:
            fail(f"L2: is_reviewable({verdict}, {chosen!r}) = {got!r}, expected {expected!r}")
    world = {"scope_type": "world", "scope_name": None}
    for source, evidence, expected in (
        ("facts", [{"scopes": [world]}], "world"),
        ("facts", [{"scopes": [{"scope_type": "location", "scope_name": "X"}]}], "rencontre"),
        ("facts", [{"scopes": [{"scope_type": "rencontre", "scope_name": "Y"}, world]}], "world"),
        ("declaration", [], "rencontre"),
        ("none", [], "rencontre"),
    ):
        got = preselected_scope(source, evidence)
        if got != expected:
            fail(f"L3: preselected_scope({source!r}, {evidence!r}) = {got!r}, expected {expected!r}")


# ── L4-L6 ────────────────────────────────────────────────────────────────

def _expect(label: str, got, expected) -> None:
    if got != expected:
        fail(f"L5: {label} = {got!r}, expected {expected!r}")


def _check_rows(rows_by_id: dict, ids: dict) -> None:
    varn_orn = ["Maelis Varn", "Maelis Orn"]
    world = {"scope_type": "world", "scope_name": None}
    expected = {
        "c2": dict(planned=False, chosen="Maelis Orn", names=["Maelis Orn"], source="declaration",
                   evidence=[], scope="rencontre"),
        "c3": dict(planned=False, chosen=None, names=varn_orn, source="none", evidence=[],
                   scope="rencontre"),
        "c1": dict(planned=True, chosen="Maelis Varn", names=varn_orn, source="facts", evidence=[
            {"fact_id": ids["f_varn"], "content": "Elle tient la forge du port.", "scopes": [world]},
        ], scope="world"),
        "c6": dict(planned=True, chosen=None, names=["Maelis Orn"], source="facts", evidence=[
            {"fact_id": ids["f_orn"], "content": "Elle chante à La Taverne.",
             "scopes": [{"scope_type": "location", "scope_name": "La Taverne"}]},
        ], scope="rencontre"),
    }
    for key, want in expected.items():
        row = rows_by_id.get(ids[key])
        if row is None:
            continue
        _expect(f"{key}.day", row["day"], {
            "day_number": 1, "character_name": "Aldric",
            "declaration": "Je vais voir Maelis à la forge.", "planned": want["planned"],
        })
        if want["chosen"] is not None:
            _expect(f"{key}.chosen.name", row["chosen"]["name"], want["chosen"])
        _expect(f"{key}.candidates", [c["name"] for c in row["candidates"]], want["names"])
        _expect(f"{key}.excerpt_source", row["excerpt_source"], want["source"])
        _expect(f"{key}.evidence", row["evidence"], want["evidence"])
        _expect(f"{key}.preselected_scope", row["preselected_scope"], want["scope"])
    c3 = rows_by_id.get(ids["c3"])
    if c3 is not None:
        _expect("c3.verdict", c3["verdict"], "rejected")
        _expect("c3.verdict_detail", c3["verdict_detail"], "excerpt not in the chosen candidate's facts")


def check_reader(engine) -> tuple[int, dict]:
    from sqlmodel import Session

    from world_engine.lore_choices_read import list_pending_choices

    ids = _k1_world(engine)
    with Session(engine) as db:
        rows = list_pending_choices(db, ids["k1"])
        other = list_pending_choices(db, ids["other"])
    listed = [row["id"] for row in rows]
    names = {value: key for key, value in ids.items()}
    if listed != [ids["c2"], ids["c3"], ids["c1"], ids["c6"]]:
        fail(f"L4: listed {[names.get(i, i) for i in listed]!r}, expected ['c2', 'c3', 'c1', 'c6']")
    if other != []:
        fail(f"L4: the other world listed {len(other)} row(s)")
    _check_rows({row["id"]: row for row in rows}, ids)
    for row in rows:
        label = names.get(row["id"], row["id"])
        if set(row) != PENDING_ROW_KEYS:
            fail(f"L6: {label} keys {sorted(set(row) ^ PENDING_ROW_KEYS)!r} differ from C-06")
        if set(row["day"]) != DAY_KEYS:
            fail(f"L6: {label} day keys {sorted(row['day'])!r} differ from C-06")
    return len(rows), ids


# ── T0 ───────────────────────────────────────────────────────────────────

def check_route_static() -> None:
    tree = _parse(ROUTE_FILE)
    if tree is None:
        return
    where = _rel(ROUTE_FILE)
    for node in ast.walk(tree):
        line = getattr(node, "lineno", "?")
        if isinstance(node, ast.Call) and _callee_name(node) in ("select", "chat"):
            fail(f"choice_review T0: {where}:{line} calls {_callee_name(node)}( — reads live in the reader")
        named = _node_name(node)
        if named == "CREATOR" and not isinstance(node, ast.keyword):
            fail(f"choice_review T0: {where}:{line} names CREATOR (R-14)")
        if named in _JSON_COLUMNS:
            fail(f"choice_review T0: {where}:{line} names {named} — rows only (G1)")


# ── T1-T10 ───────────────────────────────────────────────────────────────

def _count(db, model) -> int:
    from sqlmodel import func, select

    return db.exec(select(func.count()).select_from(model)).one()


def _reviews(db, choice_id: str) -> list:
    from sqlmodel import select

    from world_engine.models import DayMentionReview

    return list(db.exec(select(DayMentionReview).where(DayMentionReview.choice_id == choice_id)).all())


def _appellation_facts(db, entity_id: str) -> list:
    from sqlmodel import select

    from world_engine.models import Fact, FactParticipant

    return list(db.exec(select(Fact).join(FactParticipant, FactParticipant.fact_id == Fact.id).where(
        FactParticipant.entity_id == entity_id, Fact.facet == "appellation",
    )).all())


def _post(client, choice_id: str, body: dict, status: int, label: str, written=None) -> None:
    resp = client.post(f"/api/lore/choices/{choice_id}/review", json=body)
    if resp.status_code != status:
        fail(f"{label}: {body!r} -> {resp.status_code} {resp.text}, expected {status}")
    elif written is not None and resp.json().get("appellation_written") is not written:
        fail(f"{label}: appellation_written = {resp.json().get('appellation_written')!r}, expected {written!r}")


def _one_review(db, ids: dict, key: str, label: str, **want):
    reviews = _reviews(db, ids[key])
    if len(reviews) != 1:
        fail(f"{label}: {key} has {len(reviews)} review(s), expected 1")
        return None
    review = reviews[0]
    for field, value in want.items():
        if getattr(review, field) != value:
            fail(f"{label}: {key} review.{field} = {getattr(review, field)!r}, expected {value!r}")
    return review


def _check_t2_fact(db, ids: dict, fact_id) -> None:
    from sqlmodel import select

    from world_engine.models import Fact, FactDefault, FactParticipant
    from world_engine.prose_render import fact_text

    fact = db.get(Fact, fact_id) if fact_id else None
    if fact is None:
        fail(f"T2: appellation_fact_id {fact_id!r} names no fact")
        return
    if fact.facet != "appellation" or fact_text(db, fact) != "Maelis":
        fail(f"T2: fact facet {fact.facet!r}, text {fact_text(db, fact)!r}, expected appellation 'Maelis'")
    participants = list(db.exec(select(FactParticipant.entity_id).where(FactParticipant.fact_id == fact.id)).all())
    if participants != [ids["varn"]]:
        fail(f"T2: fact participants {participants!r}, expected [varn]")
    defaults = [(d.scope_type, d.scope_id, d.level) for d in db.exec(
        select(FactDefault).where(FactDefault.fact_id == fact.id)).all()]
    if defaults != [("world", None, "knows")]:
        fail(f"T2: fact_default rows {defaults!r}, expected [('world', None, 'knows')]")


def _check_t1_t4(client, engine, ids: dict) -> int:
    from sqlmodel import Session

    resp = client.get("/api/lore/choices")
    listed = [row["id"] for row in resp.json().get("choices", [])] if resp.status_code == 200 else []
    if resp.status_code != 200 or listed != [ids["c2"], ids["c3"], ids["c1"], ids["c6"]]:
        fail(f"T1: GET -> {resp.status_code}, {len(listed)} choice(s), expected [c2, c3, c1, c6]")
    _post(client, ids["c1"], {"verdict": "agreed", "record_appellation": True, "scope_type": "world"},
          200, "T2", written=True)
    with Session(engine) as db:
        review = _one_review(db, ids, "c1", "T2", verdict="agreed", entity_id=ids["varn"],
                             appellation_scope="world")
        if review is not None:
            _check_t2_fact(db, ids, review.appellation_fact_id)
    _post(client, ids["c1"], {"verdict": "agreed"}, 409, "T3")
    with Session(engine) as db:
        if len(_reviews(db, ids["c1"])) != 1:
            fail("T3: c1 no longer has exactly one review")
    _post(client, ids["c4"], {"verdict": "agreed"}, 404, "T4 (declined)")
    _post(client, "no-such-choice", {"verdict": "agreed"}, 404, "T4 (unknown)")
    return len(listed)


def _check_t5_t9(client, engine, ids: dict) -> None:
    from sqlmodel import Session

    for body in (
        {"verdict": "maybe"}, {"verdict": "agreed", "entity_id": ids["varn"]},
        {"verdict": "disagreed", "entity_id": ids["orn"]},
        {"verdict": "disagreed", "record_appellation": True},
        {"verdict": "disagreed", "entity_id": ids["tavern"]},
    ):
        _post(client, ids["c2"], body, 422, "T5")
    _post(client, ids["c3"], {"verdict": "disagreed", "entity_id": ids["varn"], "record_appellation": True,
                              "scope_type": "nope"}, 422, "T6")
    with Session(engine) as db:
        if _reviews(db, ids["c2"]):
            fail("T5: c2 has a review after five refused bodies")
        if _reviews(db, ids["c3"]):
            fail("T6: c3 has a review after a refused scope")
        held = len(_appellation_facts(db, ids["varn"]))
        if held != 1:
            fail(f"T6: varn holds {held} appellation fact(s), expected 1")
    _post(client, ids["c2"], {"verdict": "disagreed"}, 200, "T7", written=False)
    _post(client, ids["c3"], {"verdict": "disagreed", "entity_id": ids["varn"], "record_appellation": True,
                              "scope_type": "rencontre"}, 200, "T8", written=False)
    _post(client, ids["c6"], {"verdict": "agreed"}, 200, "T9", written=False)
    with Session(engine) as db:
        _one_review(db, ids, "c2", "T7", verdict="disagreed", entity_id=None,
                    appellation_fact_id=None, appellation_scope=None)
        _one_review(db, ids, "c3", "T8", verdict="disagreed", entity_id=ids["varn"], appellation_fact_id=None)
        _one_review(db, ids, "c6", "T9", verdict="agreed", entity_id=ids["orn"], appellation_fact_id=None)


def check_route(engine, ids: dict) -> int:
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from world_engine.cockpit.app import app
    from world_engine.models import DayMentionChoice, DayMentionReview, DayRewrite

    with Session(engine) as db:
        choices_before, rewrites_before = _count(db, DayMentionChoice), _count(db, DayRewrite)
    client = TestClient(app, base_url="http://127.0.0.1")  # origin_guard (BRIEF-0098-A)
    listed = _check_t1_t4(client, engine, ids)
    _check_t5_t9(client, engine, ids)
    resp = client.get("/api/lore/choices")
    if resp.status_code != 200 or resp.json() != {"choices": []}:
        fail(f"T10: GET -> {resp.status_code} {resp.text}, expected an empty choice list")
    with Session(engine) as db:
        counts = (_count(db, DayMentionReview), _count(db, DayMentionChoice), _count(db, DayRewrite))
    if counts != (5, choices_before, rewrites_before):
        fail(f"T10: (reviews, choices, rewrites) = {counts!r}, expected (5, {choices_before}, {rewrites_before})")
    return listed


def main() -> None:
    check_json_write_only()
    check_reader_read_only()
    check_route_static()
    engine = _fresh_engine()
    check_pure_rules()
    listed, ids = check_reader(engine)
    if listed != 4:
        fail(f"vacuity: L4 listed {listed} row(s), expected 4")
    routed = check_route(engine, ids)
    if routed != 4:
        fail(f"vacuity: T1 listed {routed} choice(s), expected 4")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: choice_review — R0 (the JSON is write-only), L0 (the reader is read-only), "
        "L1-L3 (excerpt key, reviewability, preselection), L4-L6 (the pending list, its rows, their shape), "
        "T0-T10 (the review route: thin, table b3, nothing else touched)"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
