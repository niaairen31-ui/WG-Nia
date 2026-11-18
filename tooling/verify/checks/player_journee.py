"""G1 check for TICKET-0128 (BRIEF-0128-G) -- the player declares his day and reads only what the creator published (INV-66, D1, E1).

PJ1 -- shape. On an open world with Ana's PC, `GET /api/joueur/journee`
   -> exactly `{character_id, can_declare, days}`, each day exactly
   `{day_number, declared_action, state, text}`; a profile with no
   character -> `{character_id: None, can_declare: False, days: []}`; a
   closed world -> 404 « Monde introuvable. »; an unknown profile -> 404
   « Profil introuvable. ».
PJ2 -- states, the lot's (b) table row by row: Ana's days set raw to
   `submitted` (en_cours), `flagged` (en_attente), `abandoned`
   (abandonnee), `resolved` + published (publiee, « Publié »), `resolved`
   unpublished (en_attente); only the published day carries a text. The
   response holds « Publié » and neither the narrator's « Narrateur secret »
   nor « Pas encore », nor the flagged day's failure reason, nor a
   proposal's rationale of those days.
PJ3 -- declare, `day_declare.missing_usages` and `day_declare.enqueue_day`
   (a recorder) swapped: with an unpublished day -> `POST
   /api/joueur/journee/declarer` 409 `DAY_IN_PROGRESS`; once published and
   the rest abandoned -> 201, a `submitted` day of Ana in the open world
   though another world is active, its batch id recorded; a profile with
   no character -> 404 « Personnage introuvable. »; an empty declaration
   -> 422.
PJ4 -- static, code tokens: `routes/player_day.py` holds no `chat(`,
   `World.is_active`, `_world_id(`, `final_result`, `write_usage_event` or
   `lore_selectors`; every route path literal starts with `/api/joueur/`;
   `creation_check.py` holds no `world_has_pc`; `joueur/day.svelte.js`
   holds `/api/joueur/journee` and `/api/joueur/journee/declarer`;
   `WorldPage.svelte` holds `<PlayerDay />`; a built asset carries « Ma
   journée »; `.claude/rules/player-surface.md` holds
   `pass_play.published_text`.

Swapped names are restored in `finally`. A rule not reached is a FAILURE.
Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import, through `day_runs.py`'s fixture) -- never Nia's DB.
"""
from __future__ import annotations

import ast
import pathlib
import sys
from datetime import UTC, datetime, timedelta

import day_chain_world as dcw  # the sibling check: its code-token reader
import day_runs as dr  # the sibling check: its fresh engine and day fixture

ROOT = pathlib.Path(__file__).resolve().parents[3]
PACKAGE = ROOT / "src" / "world_engine"
ROUTE = PACKAGE / "cockpit" / "routes" / "player_day.py"
JOUEUR = ROOT / "frontend" / "src" / "joueur"
ASSETS = PACKAGE / "cockpit" / "static" / "assets"
RULE = ROOT / ".claude" / "rules" / "player-surface.md"
BANNED = ("chat(", "World.is_active", "_world_id(", "final_result", "write_usage_event", "lore_selectors")
TOP_KEYS = {"character_id", "can_declare", "days"}
DAY_KEYS = {"day_number", "declared_action", "state", "text"}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fixture(db) -> dict:
    from world_engine.models import Character, Entity, User, World

    active = World(name="Active", is_active=True)
    open_world = World(name="Ouvert", is_active=False, open_to_players=True)
    closed = World(name="Fermé", is_active=False, open_to_players=False)
    for row in (active, open_world, closed):
        db.add(row)
    ana = User(name="Ana", role="player")
    bob = User(name="Bob", role="player")
    db.add(ana)
    db.add(bob)
    db.commit()
    entity = Entity(world_id=open_world.id, type="character", name="Kael", status="active")
    db.add(entity)
    db.flush()
    db.add(Character(id=entity.id, world_id=open_world.id, character_type="player", user_id=ana.id))
    db.commit()
    return {"active": active.id, "open": open_world.id, "closed": closed.id, "ana": ana.id, "bob": bob.id,
            "kael": entity.id}


def _get(client, ids: dict, profile: str, world: str):
    return client.get("/api/joueur/journee", params={"profile_id": ids[profile], "world_id": ids[world]})


# --- PJ1 -----------------------------------------------------------------------

def rule_pj1(client, db, ids: dict) -> int:
    reached = 0
    dr._day(db, ids["open"], ids["kael"], status="submitted")

    reached += 1
    resp = _get(client, ids, "ana", "open")
    body = resp.json() if resp.status_code == 200 else {}
    if resp.status_code != 200 or set(body) != TOP_KEYS or body.get("character_id") != ids["kael"] \
            or not body.get("days") or any(set(d) != DAY_KEYS for d in body["days"]):
        fail(f"PJ1: Ana's journee -> {resp.status_code} {resp.text[:200]}")

    reached += 1
    resp = _get(client, ids, "bob", "open")
    if resp.status_code != 200 or resp.json() != {"character_id": None, "can_declare": False, "days": []}:
        fail(f"PJ1: no character -> {resp.status_code} {resp.text}")

    reached += 1
    resp = _get(client, ids, "ana", "closed")
    if resp.status_code != 404 or resp.json().get("detail") != "Monde introuvable.":
        fail(f"PJ1: a closed world -> {resp.status_code} {resp.text}")

    reached += 1
    resp = client.get("/api/joueur/journee", params={"profile_id": "nobody", "world_id": ids["open"]})
    if resp.status_code != 404 or resp.json().get("detail") != "Profil introuvable.":
        fail(f"PJ1: an unknown profile -> {resp.status_code} {resp.text}")
    _clear(db)
    return reached


def _clear(db) -> None:
    """Every day of the fixture leaves the way: abandoned."""
    from sqlmodel import select

    from world_engine.models import PassPlay

    db.rollback()
    for row in db.exec(select(PassPlay).where(PassPlay.published_at.is_(None))).all():
        row.status = "abandoned"
        db.add(row)
    db.commit()


# --- PJ2 -----------------------------------------------------------------------

def rule_pj2(client, db, ids: dict) -> int:
    from world_engine.models import Batch, ProposedMutation
    from world_engine.writes.day_runs import write_day_run_failure

    base = datetime.now(UTC)
    rows = (("submitted", None, "en_cours"), ("flagged", None, "en_attente"), ("abandoned", None, "abandonnee"),
            ("resolved", "Narrateur secret", "publiee"), ("resolved", "Pas encore", "en_attente"))
    expected = []
    for i, (status, narrator, state) in enumerate(rows):
        batch_id = dr._day(db, ids["open"], ids["kael"], status=status)
        batch = db.get(Batch, batch_id)
        batch.final_result = narrator
        db.add(batch)
        db.commit()
        pass_play = dr._pass_play(db, batch_id)
        pass_play.submitted_at = base + timedelta(minutes=i)
        if state == "publiee":
            pass_play.published_text = "Publié"
            pass_play.published_at = base
        db.add(pass_play)
        db.add(ProposedMutation(world_id=ids["open"], source_type="pass_play", pass_play_id=pass_play.id,
                                mutation_type="knowledge_change", payload={}, status="proposed",
                                proposed_by="local_ai", rationale=f"Raison cachée {i}"))
        db.commit()
        if status == "flagged":
            write_day_run_failure(db, pass_play=dr._pass_play(db, batch_id), world_id=ids["open"], stage="plan",
                                  code="crashed", reason="Raison d'échec cachée")
            db.commit()
        expected.append((state, "Publié" if state == "publiee" else None))

    resp = _get(client, ids, "ana", "open")
    body = resp.json() if resp.status_code == 200 else {}
    got = [(d["state"], d["text"]) for d in body.get("days", [])]
    if got[:5] != list(reversed(expected)):
        fail(f"PJ2: states read {got!r}, expected {list(reversed(expected))!r}")
    text_ = resp.text
    if "Publié" not in text_:
        fail("PJ2: the published text is missing")
    for hidden in ("Narrateur secret", "Pas encore", "Raison d'échec cachée", "Raison cachée"):
        if hidden in text_:
            fail(f"PJ2: the player reads {hidden!r}")
    if body.get("can_declare") is not False:
        fail("PJ2: can_declare with unpublished days")
    return len(rows)


# --- PJ3 -----------------------------------------------------------------------

def rule_pj3(client, db, ids: dict) -> int:
    from sqlmodel import select

    from world_engine.cockpit import day_declare
    from world_engine.day_run_reads import DAY_IN_PROGRESS
    from world_engine.models import Batch, PassPlay
    from world_engine.models import Session as GameSession

    recorded: list[str] = []
    originals = (day_declare.missing_usages, day_declare.enqueue_day)
    day_declare.missing_usages = lambda *a, **k: []
    day_declare.enqueue_day = recorded.append
    payload = {"profile_id": ids["ana"], "world_id": ids["open"], "declared_action": "Je pars au marché."}
    reached = 0
    try:
        reached += 1
        resp = client.post("/api/joueur/journee/declarer", json=payload)
        if resp.status_code != 409 or resp.json().get("detail") != DAY_IN_PROGRESS or recorded:
            fail(f"PJ3: with an unpublished day -> {resp.status_code} {resp.text}")

        reached += 1
        _clear(db)
        resp = client.post("/api/joueur/journee/declarer", json=payload)
        if resp.status_code != 201 or len(recorded) != 1:
            fail(f"PJ3: declare -> {resp.status_code} {resp.text}, recorded {recorded!r}")
        else:
            db.rollback()
            row = db.exec(select(PassPlay, GameSession.world_id).join(Batch, Batch.id == PassPlay.batch_id)
                          .join(GameSession, GameSession.id == Batch.session_id)
                          .where(Batch.id == recorded[0])).first()
            if row is None or row[0].status != "submitted" or row[0].character_id != ids["kael"] \
                    or row[1] != ids["open"]:
                fail(f"PJ3: the declared day reads {row!r}")
            if set(resp.json()) != TOP_KEYS or resp.json()["can_declare"] is not False:
                fail(f"PJ3: the answer is {resp.json()!r}")

        reached += 1
        resp = client.post("/api/joueur/journee/declarer", json={**payload, "profile_id": ids["bob"]})
        if resp.status_code != 404 or resp.json().get("detail") != "Personnage introuvable.":
            fail(f"PJ3: no character -> {resp.status_code} {resp.text}")

        reached += 1
        _clear(db)
        recorded.clear()
        resp = client.post("/api/joueur/journee/declarer", json={**payload, "declared_action": "  "})
        if resp.status_code != 422 or recorded:
            fail(f"PJ3: an empty declaration -> {resp.status_code}, recorded {recorded!r}")
    finally:
        day_declare.missing_usages, day_declare.enqueue_day = originals
    return reached


# --- PJ4 -----------------------------------------------------------------------

def rule_pj4() -> int:
    source = ROUTE.read_text(encoding="utf-8")
    code = dcw._code_only(source)
    for token in BANNED:
        if token in code:
            fail(f"PJ4: routes/player_day.py holds {token!r}")
    paths = [d.args[0].value for n in ast.walk(ast.parse(source)) if isinstance(n, ast.FunctionDef)
             for d in n.decorator_list if isinstance(d, ast.Call) and d.args
             and isinstance(d.args[0], ast.Constant) and isinstance(d.args[0].value, str)]
    if len(paths) != 2 or not all(p.startswith("/api/joueur/") for p in paths):
        fail(f"PJ4: route paths are {paths!r}")
    if "world_has_pc" in (PACKAGE / "creation_check.py").read_text(encoding="utf-8"):
        fail("PJ4: creation_check.py still names world_has_pc")
    day_js = (JOUEUR / "day.svelte.js").read_text(encoding="utf-8")
    for url in ("/api/joueur/journee", "/api/joueur/journee/declarer"):
        if url not in day_js:
            fail(f"PJ4: day.svelte.js lacks {url}")
    if "<PlayerDay />" not in (JOUEUR / "WorldPage.svelte").read_text(encoding="utf-8"):
        fail("PJ4: WorldPage.svelte lacks <PlayerDay />")
    built = "".join(p.read_text(encoding="utf-8", errors="replace") for p in ASSETS.glob("*.js"))
    if "Ma journée" not in built:
        fail("PJ4: no built asset carries « Ma journée »")
    if "pass_play.published_text" not in RULE.read_text(encoding="utf-8"):
        fail("PJ4: player-surface.md does not name pass_play.published_text")
    return 1


def main() -> int:
    expected = {"PJ1": 4, "PJ2": 5, "PJ3": 4, "PJ4": 1}
    reached: dict[str, int] = {}
    try:
        reached["PJ4"] = rule_pj4()
    except Exception as exc:  # noqa: BLE001 -- fail-closed
        fail(f"PJ4 raised {type(exc).__name__}: {exc}")
    engine = dr._fresh_engine()
    from fastapi.testclient import TestClient
    from sqlmodel import Session

    from world_engine.cockpit.app import app

    try:
        with Session(engine) as db:
            ids = _fixture(db)
            client = TestClient(app, base_url="http://127.0.0.1")
            reached["PJ1"] = rule_pj1(client, db, ids)
            reached["PJ2"] = rule_pj2(client, db, ids)
            reached["PJ3"] = rule_pj3(client, db, ids)
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"raised {type(exc).__name__}: {exc}")
    finally:
        dr._drain()
    for rule, count in expected.items():
        if reached.get(rule, 0) != count:
            fail(f"{rule} reached {reached.get(rule, 0)} of its {count} rows")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: player_journee -- PJ1-PJ4: the player's day keyed on his world and profile, its states, "
          "only the published narrative; he declares once his last day is published")
    return 0


if __name__ == "__main__":
    sys.exit(main())
