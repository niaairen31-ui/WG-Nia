"""G1 check for TICKET-0126 (BRIEF-0126-I) -- the creator lists and reads the submitted character drafts of her active world, and writes nothing.

Fixture: two worlds (W1 active, W2 not), one player profile per world
(`writes/users.create_player_profile`), and three drafts written through
`writes/pc_drafts.py`: a submitted one in W1, one still `draft` in W1 (a
second profile), a submitted one in W2.

SD1 -- `GET /api/pc-drafts` lists exactly W1's submitted draft, with the
   keys `id`, `name`, `player_name`, `submitted_at`.
SD2 -- `GET /api/pc-drafts/{id}` answers W1's submitted draft with the keys
   `draft`, `player_name`, `verdict`, `skill_names`, `ranks`;
   `skill_names` covers every `start_sheet` line of W1; `ranks` holds six
   labels; W2's draft -> 404 `Brouillon introuvable.`
SD3 -- static (code tokens only): `routes/pc_drafts.py` holds no `db.add(`,
   `.commit(`, `.flush(`, `@router.post`, `@router.put`, `@router.delete`;
   `cockpit/app.py` holds `app.include_router(_routes_pc_drafts.router)`.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A case not reached is a FAILURE.
"""
from __future__ import annotations

import io
import os
import pathlib
import sys
import tempfile
import tokenize

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
ROUTE_MODULE = SRC / "world_engine" / "cockpit" / "routes" / "pc_drafts.py"
APP_PY = SRC / "world_engine" / "cockpit" / "app.py"
LIST_KEYS = {"id", "name", "player_name", "submitted_at"}
DETAIL_KEYS = {"draft", "player_name", "verdict", "skill_names", "ranks"}
FORBIDDEN = ("db.add(", ".commit(", ".flush(", "@router.post", "@router.put", "@router.delete")
INCLUDE_LINE = "app.include_router(_routes_pc_drafts.router)"

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


def _build(engine) -> dict:
    from sqlmodel import Session

    from world_engine.models import World
    from world_engine.writes.pc_drafts import open_draft, save_player_draft, submit_draft
    from world_engine.writes.users import create_player_profile

    ids: dict = {}
    with Session(engine) as db:
        w1 = World(name="W1", is_active=True, open_to_players=True)
        w2 = World(name="W2", is_active=False, open_to_players=True)
        db.add(w1)
        db.add(w2)
        db.flush()
        ana = create_player_profile(db, "Ana")
        bea = create_player_profile(db, "Bea")
        db.flush()

        def draft(world, user, name, *, submit):
            d = open_draft(db, world_id=world.id, user_id=user.id)
            save_player_draft(db, d, name=name, story="Une histoire.", start_location_id=None, skills=[],
                              sketches=[], memberships=[], knowledge=[])
            if submit:
                submit_draft(db, d, ())
            return d.id

        ids["w1_submitted"] = draft(w1, ana, "Ilan", submit=True)
        ids["w1_draft"] = draft(w1, bea, "Brouillon", submit=False)
        ids["w2_submitted"] = draft(w2, ana, "Ailleurs", submit=True)
        db.commit()
        ids["w1"] = w1.id
    return ids


def rule_sd1(client, ids: dict) -> int:
    resp = client.get("/api/pc-drafts")
    if resp.status_code != 200:
        fail(f"SD1 GET /api/pc-drafts answered {resp.status_code}: {resp.text[:200]}")
        return 0
    rows = resp.json()
    if [r.get("id") for r in rows] != [ids["w1_submitted"]]:
        fail(f"SD1 listed {[r.get('id') for r in rows]!r}, expected only W1's submitted draft")
    if any(set(r) != LIST_KEYS for r in rows):
        fail(f"SD1 row keys {[sorted(r) for r in rows]}")
    if rows and (rows[0].get("player_name") != "Ana" or not rows[0].get("submitted_at")):
        fail(f"SD1 row {rows[0]!r}")
    return 1


def rule_sd2(engine, client, ids: dict) -> int:
    from sqlmodel import Session

    from world_engine.creation_rules import start_sheet

    resp = client.get(f"/api/pc-drafts/{ids['w1_submitted']}")
    if resp.status_code != 200:
        fail(f"SD2 detail answered {resp.status_code}: {resp.text[:200]}")
        return 0
    body = resp.json()
    if set(body) != DETAIL_KEYS:
        fail(f"SD2 detail keys {sorted(body)}")
    with Session(engine) as db:
        keys = {line.skill_key for line in start_sheet(db, ids["w1"])}
    if not keys or set(body.get("skill_names", {})) != keys:
        fail(f"SD2 skill_names {sorted(body.get('skill_names', {}))} != start sheet {sorted(keys)}")
    if len(body.get("ranks", [])) != 6:
        fail(f"SD2 ranks {body.get('ranks')!r}")
    if body.get("draft", {}).get("id") != ids["w1_submitted"]:
        fail("SD2 the detail answers another draft")
    other = client.get(f"/api/pc-drafts/{ids['w2_submitted']}")
    if other.status_code != 404 or other.json().get("detail") != "Brouillon introuvable.":
        fail(f"SD2 another world's draft answered {other.status_code}: {other.text[:200]}")
    return 1


def _code(path: pathlib.Path) -> str:
    """The module's code tokens: strings and comments dropped."""
    return "".join(tok.string for tok in tokenize.generate_tokens(io.StringIO(path.read_text(encoding="utf-8")).readline)
                   if tok.type not in (tokenize.STRING, tokenize.COMMENT))


def rule_sd3() -> int:
    if not ROUTE_MODULE.exists() or not APP_PY.exists():
        fail("SD3 routes/pc_drafts.py or cockpit/app.py missing")
        return 0
    code = _code(ROUTE_MODULE)
    for needle in FORBIDDEN:
        if needle in code:
            fail(f"SD3 routes/pc_drafts.py holds {needle}")
    if INCLUDE_LINE not in APP_PY.read_text(encoding="utf-8"):
        fail(f"SD3 cockpit/app.py lacks {INCLUDE_LINE}")
    return 1


def main() -> int:
    engine = _fresh_engine()
    from fastapi.testclient import TestClient

    from world_engine.cockpit.app import app

    plan = [("SD3", rule_sd3)]
    try:
        ids = _build(engine)
        client = TestClient(app, base_url="http://127.0.0.1")
        plan = [("SD1", lambda: rule_sd1(client, ids)), ("SD2", lambda: rule_sd2(engine, client, ids))] + plan
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"fixture raised {type(exc).__name__}: {exc}")
    reached = 0
    for name, rule in plan:
        try:
            got = rule()
        except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
            fail(f"{name} raised {type(exc).__name__}: {exc}")
            got = 0
        if got != 1:
            fail(f"{name} was not reached")
        reached += got
    if reached != 3:
        fail(f"{reached} of 3 rules reached")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: submitted_drafts -- the active world's submitted drafts listed and read whole, "
          "another world's refused, the creator's routes read only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
