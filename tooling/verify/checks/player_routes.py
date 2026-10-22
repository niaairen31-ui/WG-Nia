"""G1 check for TICKET-0125 (BRIEF-0125-E) -- the perspective and player routes answer only what everybody knows, refuse a closed world, and journal every question.

PR1 -- profiles: POST "Ana" -> 201 `{id, name}`; POST " ana " -> 409
   `"Ce nom de joueur existe déjà."`; POST "" -> 422; POST 81 characters ->
   422; GET lists exactly the created player profiles (the creator user
   absent).
PR2 -- worlds: with the fixture world closed, GET `/api/joueur/mondes` ->
   `[]`; opened through `update_world(..., open_to_players=True)` -> one
   item with keys exactly `{id, name, description, laws}`.
PR3 -- savoir on a closed world -> 404 `"Monde introuvable."`; an unknown
   profile -> 404 `"Profil introuvable."`; neither journals.
PR4 -- savoir answered (stubbed plan: `public_dossier` on « Hero »; stubbed
   prose) -> 200, answer keys exactly `{verdict, answer, renderer,
   candidates, plan}`; the response text contains neither F2's nor F3's
   text nor `withheld`; one journal row kind `perspective`, step
   `perspective_ask`, outcome `ok`, `asked_by "player:<id>"`, its
   `withheld` equal to `perspective_audit.withheld` for that plan.
PR5 -- creator ask, same plan -> keys exactly `{verdict, answer, renderer,
   candidates, plan, rows, withheld}`, `withheld` non-empty; journal
   `asked_by "creator"`; `perspective: "x"` -> 422 and no row.
PR6 -- ping down -> 503, one `unavailable` row; an unparsable plan -> 502,
   one `parse_error` row.
PR7 -- resolve: a binding to Shade -> 422 `"Choix refusé."`, one
   `perspective_resolve/refused` row; a binding to a Twin -> 200.
PR8 -- static (code tokens, docstrings and comments excluded):
   `routes/lore_perspective.py` and `cockpit/perspective_flow.py` hold no
   `chat(` and no `select(`; `routes/player.py` holds no `chat(` and its
   `select(` calls name only `User`, `World` or `WorldLaw`; none of the three
   holds `World.is_active`, `_world_id(`, `write_usage_event` or an import
   of `lore_selectors`; every route path literal of `player.py` starts with
   `/api/joueur/`.

The world is brief D's PI4 world, built by `perspective_isolation._build_world`
(imported, not copied). `lore_plan.chat`, `lore_render.chat` and
`ollama_client.ping` are swapped and restored in `finally`. Fresh temp-file
SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any world_engine
import) -- never Nia's DB. A case not reached is a FAILURE.
"""
from __future__ import annotations

import ast
import io
import json
import os
import pathlib
import sys
import tempfile
import tokenize

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
COCKPIT = SRC / "world_engine" / "cockpit"
FLOW_MODULES = (COCKPIT / "routes" / "lore_perspective.py", COCKPIT / "perspective_flow.py")
PLAYER_MODULE = COCKPIT / "routes" / "player.py"
FORBIDDEN_ALL = ("World.is_active", "_world_id(", "write_usage_event", "lore_selectors")
SELECT_NAMES = {"User", "World", "WorldLaw"}

PLAYER_KEYS = {"verdict", "answer", "renderer", "candidates", "plan"}
CREATOR_KEYS = PLAYER_KEYS | {"rows", "withheld"}
TAKEN = "Ce nom de joueur existe déjà."
REFUSED = "Choix refusé."
HERO_PLAN = {"mentions": [{"ref": "m1", "surface_form": "Hero", "category": "person"}],
             "calls": [{"selector": "public_dossier", "args": ["m1", "$world"]}]}
TWIN_PLAN = {"mentions": [{"ref": "m1", "surface_form": "Twin", "category": "person"}],
             "calls": [{"selector": "public_dossier", "args": ["m1", "$world"]}]}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from sqlmodel import SQLModel

    import world_engine.models  # noqa: F401 -- registers every table
    from world_engine.db import engine

    SQLModel.metadata.create_all(engine)
    return engine


def _seed_prompts(db) -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    import seed_pilot

    from world_engine.models import PromptTemplate

    heads = [
        dict(id="pt-lore-question-to-plan", world_id=None, name="plan", usage="lore_question_to_plan",
             system_prompt=seed_pilot.LORE_QUESTION_TO_PLAN_SYSTEM_PROMPT,
             user_template=seed_pilot.LORE_QUESTION_TO_PLAN_USER_TEMPLATE,
             variables=["selectors", "question"], destination="local"),
        dict(id="pt-lore-rows-to-prose", world_id=None, name="prose", usage="lore_rows_to_prose",
             system_prompt=seed_pilot.LORE_ROWS_TO_PROSE_SYSTEM_PROMPT,
             user_template=seed_pilot.LORE_ROWS_TO_PROSE_USER_TEMPLATE,
             variables=["question", "rows"], destination="local"),
    ]
    for head in heads:
        if db.get(PromptTemplate, head["id"]) is None:
            seed_pilot.upsert_prompt_template(db, **dict(head))
    db.commit()


class _Stub:
    def __init__(self, replies):
        self.replies, self.messages = list(replies), []

    def __call__(self, messages, **kwargs):
        self.messages.append(messages)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply if isinstance(reply, str) else json.dumps(reply)


def _swap(module, stub):
    original = module.chat
    module.chat = stub
    return original


def _events(engine, attempt: str) -> list:
    from sqlmodel import Session, select

    from world_engine.models import LoreUsageEvent

    with Session(engine) as db:
        return list(db.exec(select(LoreUsageEvent).where(LoreUsageEvent.attempt_id == attempt)).all())


def _all_events(engine) -> int:
    from sqlmodel import Session, select

    from world_engine.models import LoreUsageEvent

    with Session(engine) as db:
        return len(db.exec(select(LoreUsageEvent)).all())


def _attempt(n: int) -> str:
    return f"0c0c0c0c-0000-4000-8000-{n:012d}"


def _one(label: str, engine, attempt: str, step: str, outcome: str, asked_by: str | None = None):
    rows = _events(engine, attempt)
    if len(rows) != 1:
        fail(f"{label}: {len(rows)} journal row(s) under the attempt, expected 1")
        return None
    row = rows[0]
    if (row.kind, row.step, row.outcome) != ("perspective", step, outcome):
        fail(f"{label}: journal row {(row.kind, row.step, row.outcome)}, expected ('perspective', {step!r}, {outcome!r})")
    if asked_by is not None and row.payload.get("asked_by") != asked_by:
        fail(f"{label}: journal asked_by {row.payload.get('asked_by')!r}, expected {asked_by!r}")
    return row


def _routes(engine, ids: dict) -> int:
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from world_engine import lore_plan, lore_render, ollama_client
    from world_engine.cockpit.app import app
    from world_engine.cockpit.routes.creator import WorldUpdateBody, update_world
    from world_engine.cockpit.routes.lore import _deserialize_plan
    from world_engine.models import User
    from world_engine.perspective_audit import withheld

    wid, text = ids["world"], ids["text"]
    reached = 0
    with Session(engine) as db:
        _seed_prompts(db)
        db.add(User(id="user-creator", name="Creator", role="creator"))
        db.commit()
    client = TestClient(app, base_url="http://127.0.0.1")
    original_ping = ollama_client.ping

    def down(*args, **kwargs):
        raise ollama_client.OllamaError("down")

    plan_original = _swap(lore_plan, _Stub([HERO_PLAN, HERO_PLAN, "pas du json"]))
    prose_original = _swap(lore_render, _Stub(["Hero porte une cape.", "Hero porte une cape.",
                                               "Twin.", "Twin."]))
    ollama_client.ping = lambda *a, **k: []
    try:
        # PR1 -- profiles
        ana = client.post("/api/joueur/profils", json={"name": "Ana"})
        dup = client.post("/api/joueur/profils", json={"name": " ana "})
        empty = client.post("/api/joueur/profils", json={"name": ""})
        long_ = client.post("/api/joueur/profils", json={"name": "x" * 81})
        listed = client.get("/api/joueur/profils")
        if ana.status_code != 201 or set(ana.json()) != {"id", "name"} or ana.json().get("name") != "Ana":
            fail(f"PR1: POST Ana -> {ana.status_code} {ana.text[:200]}")
        if dup.status_code != 409 or dup.json().get("detail") != TAKEN:
            fail(f"PR1: POST ' ana ' -> {dup.status_code} {dup.text[:200]}")
        if (empty.status_code, long_.status_code) != (422, 422):
            fail(f"PR1: empty / 81 characters -> {empty.status_code} / {long_.status_code}, expected 422 / 422")
        if listed.status_code != 200 or listed.json() != [ana.json()]:
            fail(f"PR1: GET profils -> {listed.text[:200]}")
        profile = ana.json().get("id", "")
        reached += 1

        # PR3a -- a closed world refuses, unjournaled
        before = _all_events(engine)
        closed = client.post("/api/joueur/savoir/ask",
                             json={"profile_id": profile, "world_id": wid, "question": "Hero ?"})
        if closed.status_code != 404 or closed.json().get("detail") != "Monde introuvable.":
            fail(f"PR3: savoir on a closed world -> {closed.status_code} {closed.text[:200]}")

        # PR2 -- open worlds
        none_open = client.get("/api/joueur/mondes")
        if none_open.status_code != 200 or none_open.json() != []:
            fail(f"PR2: closed world listed -> {none_open.text[:200]}")
        with Session(engine) as db:
            update_world(wid, WorldUpdateBody(name="PI World", description="", tone="",
                                              laws=["La magie a un prix"], open_to_players=True), db)
        opened = client.get("/api/joueur/mondes").json()
        if len(opened) != 1 or set(opened[0]) != {"id", "name", "description", "laws"} \
                or opened[0]["laws"] != ["La magie a un prix"]:
            fail(f"PR2: open worlds -> {opened!r}"[:300])
        reached += 1

        # PR3b -- an unknown profile refuses, unjournaled
        stranger = client.post("/api/joueur/savoir/ask",
                               json={"profile_id": "nobody", "world_id": wid, "question": "Hero ?"})
        if stranger.status_code != 404 or stranger.json().get("detail") != "Profil introuvable.":
            fail(f"PR3: unknown profile -> {stranger.status_code} {stranger.text[:200]}")
        creator_as_player = client.post("/api/joueur/savoir/ask",
                                        json={"profile_id": "user-creator", "world_id": wid, "question": "?"})
        if creator_as_player.status_code != 404:
            fail(f"PR3: the creator user as a profile -> {creator_as_player.status_code}")
        if _all_events(engine) != before:
            fail("PR3: a refused savoir request was journaled")
        reached += 1

        # PR4 -- the player's answer
        answered = client.post("/api/joueur/savoir/ask", json={
            "profile_id": profile, "world_id": wid, "question": "Qui est Hero ?", "attempt_id": _attempt(4)})
        if answered.status_code != 200 or set(answered.json()) != PLAYER_KEYS:
            fail(f"PR4: player ask -> {answered.status_code} keys {sorted(answered.json())}")
        dumped = json.dumps(answered.json(), ensure_ascii=False)
        for key in ("F2", "F3"):
            if text[key] in dumped:
                fail(f"PR4: the player's answer carries {key}'s text")
        if "withheld" in dumped:
            fail("PR4: the player's answer names withheld")
        row = _one("PR4", engine, _attempt(4), "perspective_ask", "ok", f"player:{profile}")
        with Session(engine) as db:
            audit = withheld(_deserialize_plan(HERO_PLAN), wid, db)
        if row is not None and row.payload.get("withheld") != json.loads(json.dumps(audit)):
            fail(f"PR4: journaled withheld {row.payload.get('withheld')!r} != the audit"[:300])
        reached += 1

        # PR5 -- the creator's perspective
        creator = client.post("/api/lore/perspective/ask", json={
            "question": "Qui est Hero ?", "world_id": wid, "perspective": "public", "attempt_id": _attempt(5)})
        body = creator.json()
        if creator.status_code != 200 or set(body) != CREATOR_KEYS or not body.get("withheld"):
            fail(f"PR5: creator ask -> {creator.status_code} keys {sorted(body)}")
        _one("PR5", engine, _attempt(5), "perspective_ask", "ok", "creator")
        unknown = client.post("/api/lore/perspective/ask", json={
            "question": "?", "world_id": wid, "perspective": "x", "attempt_id": _attempt(51)})
        if unknown.status_code != 422 or unknown.json().get("detail") != "Perspective inconnue." \
                or _events(engine, _attempt(51)):
            fail(f"PR5: perspective 'x' -> {unknown.status_code}, {len(_events(engine, _attempt(51)))} row(s)")
        reached += 1

        # PR6 -- planner down, unparsable plan
        ollama_client.ping = down
        unavailable = client.post("/api/joueur/savoir/ask", json={
            "profile_id": profile, "world_id": wid, "question": "?", "attempt_id": _attempt(6)})
        ollama_client.ping = lambda *a, **k: []
        broken = client.post("/api/joueur/savoir/ask", json={
            "profile_id": profile, "world_id": wid, "question": "?", "attempt_id": _attempt(61)})
        if (unavailable.status_code, broken.status_code) != (503, 502):
            fail(f"PR6: statuses {(unavailable.status_code, broken.status_code)}, expected (503, 502)")
        _one("PR6 down", engine, _attempt(6), "perspective_ask", "unavailable")
        _one("PR6 parse", engine, _attempt(61), "perspective_ask", "parse_error")
        reached += 1

        # PR7 -- bindings
        resolve = {"profile_id": profile, "world_id": wid, "plan": TWIN_PLAN, "question": "Qui est Twin ?"}
        refused = client.post("/api/joueur/savoir/resolve",
                              json=dict(resolve, bindings={"m1": ids["shade"]}, attempt_id=_attempt(7)))
        if refused.status_code != 422 or refused.json().get("detail") != REFUSED:
            fail(f"PR7: binding to Shade -> {refused.status_code} {refused.text[:200]}")
        _one("PR7", engine, _attempt(7), "perspective_resolve", "refused")
        twin = client.post("/api/joueur/savoir/resolve",
                           json=dict(resolve, bindings={"m1": ids["twin1"]}, attempt_id=_attempt(71)))
        if twin.status_code != 200 or set(twin.json()) != PLAYER_KEYS:
            fail(f"PR7: binding to a Twin -> {twin.status_code} {twin.text[:200]}")
        reached += 1
    finally:
        ollama_client.ping = original_ping
        lore_plan.chat = plan_original
        lore_render.chat = prose_original
    return reached


def _code(path: pathlib.Path) -> str:
    """The module's code tokens: strings and comments dropped, so a
    docstring that names a forbidden call is not a call."""
    source = path.read_text(encoding="utf-8")
    kept = []
    for tok in tokenize.generate_tokens(io.StringIO(source).readline):
        if tok.type in (tokenize.STRING, tokenize.COMMENT):
            continue
        kept.append(tok.string)
    return " ".join(kept).replace(" (", "(").replace(" . ", ".")


def rule_pr8() -> int:
    reached = 0
    for path in (*FLOW_MODULES, PLAYER_MODULE):
        if not path.exists():
            fail(f"PR8: {path.name} missing")
            continue
        code = _code(path)
        compact = code.replace(" ", "")
        if "chat(" in compact:
            fail(f"PR8: {path.name} calls chat(")
        if path in FLOW_MODULES and "select(" in compact:
            fail(f"PR8: {path.name} calls select(")
        for needle in FORBIDDEN_ALL:
            if needle.replace(" ", "") in compact:
                fail(f"PR8: {path.name} holds {needle}")
        reached += 1
    if PLAYER_MODULE.exists():
        tree = ast.parse(PLAYER_MODULE.read_text(encoding="utf-8"))
        paths = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "select":
                names = {a.id for a in node.args if isinstance(a, ast.Name)}
                if not node.args or len(names) != len(node.args) or names - SELECT_NAMES:
                    fail(f"PR8: player.py select( names {ast.unparse(node)[:80]}")
            if isinstance(node, ast.FunctionDef):
                for deco in node.decorator_list:
                    if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute) \
                            and deco.func.attr in ("get", "post", "put", "delete", "patch") and deco.args:
                        literal = deco.args[0]
                        paths.append(literal.value if isinstance(literal, ast.Constant) else None)
        if not paths:
            fail("PR8: player.py declares no route")
        for route in paths:
            if not isinstance(route, str) or not route.startswith("/api/joueur/"):
                fail(f"PR8: player.py route path {route!r} is not under /api/joueur/")
        reached += 1
    return reached


def main() -> int:
    engine = _fresh_engine()
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    for rule, count, args in ((_routes, 7, None), (rule_pr8, 4, ())):
        reached = 0
        try:
            if args is None:
                from perspective_isolation import _build_world

                reached = rule(engine, _build_world(engine))
            else:
                reached = rule(*args)
        except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
            fail(f"{rule.__name__} raised {type(exc).__name__}: {exc}")
        if reached != count:
            fail(f"{rule.__name__} reached {reached} of its {count} cases")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: player_routes -- profiles, open worlds and public questions for the player; "
          "the creator's perspective with its audit; every question journaled")
    return 0


if __name__ == "__main__":
    sys.exit(main())
