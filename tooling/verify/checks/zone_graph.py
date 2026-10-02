"""G1 check for TICKET-0101 (BRIEF-0101-F) — the Lieux graph's three modes.

DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
DATABASE_URL set BEFORE any world_engine import), driven through
`GET /api/locations/graph` with `TestClient(app, base_url=...)`, plus a
text read of the three frontend files the mode switch lives in. Zero
outcomes in any assertion is a FAIL.

Fixture: zone D (top level) with children D1 (visitable) and D2 (a nested
zone, child D2a); visitable T; D1-T `connects_to`, D-T `borde`, D2-D
`borde`.

Five assertions:
  a. `mode=visitable` (and the default): nodes are the visitable locations
     only (D1, D2a, T), edges `connects_to` only (D1-T), no node carries `r`.
  b. `mode=zones`: nodes D and D2 only; D carries `r` = 30, D2 none; the
     one edge is D2-D, `kind` `borde`.
  c. `mode=ego&center=D`: D (with `r`), D1 and D2; edges among them only
     (D2-D); `center=T` answers no node and `empty_text`
     « Ouvrez une zone. ».
  d. An unknown mode is a 422.
  e. Frontend: `Graph.svelte` draws each circle with `radiusOf(node)` and
     shows `{emptyText}`; `mount.js` passes `emptyText`; `consumers/lieux.js`
     declares the three mode buttons, `dashedKinds: ['borde']` and an Ego
     double-click.

Named mutations: drop the `e.id not in zones` filter of `visitable` -> (a);
give every zone `r` -> (b); keep `T` as an ego centre -> (c); revert the
circle to `r={NODE_R}` -> (e).
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
FRONT = ROOT / "frontend" / "src" / "graph"

FAILURES: list[str] = []
COUNTS: dict[str, int] = {}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _ok(cond: bool, msg: str) -> int:
    if not cond:
        fail(msg)
        return 0
    return 1


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    db_path = pathlib.Path(tmp_dir) / "check.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]

    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def _seed(engine) -> dict[str, str]:
    from sqlmodel import Session

    from world_engine.models import Entity, Location, World
    from world_engine.spatial_author import link_locations

    ids: dict[str, str] = {}
    with Session(engine) as db:
        world = World(name="Graph check", is_active=True)
        db.add(world)
        db.commit()
        for label, parent in (("D", None), ("D1", "D"), ("D2", "D"), ("D2a", "D2"), ("T", None)):
            entity = Entity(world_id=world.id, type="location", name=f"Lieu {label}")
            db.add(entity)
            db.flush()
            db.add(Location(id=entity.id, parent_location_id=ids.get(parent) if parent else None))
            db.commit()
            ids[label] = entity.id
        for a, b in (("D1", "T"), ("D", "T"), ("D2", "D")):
            link_locations(db, world_id=world.id, entity_a_id=ids[a], entity_b_id=ids[b], changed_by="check")
        db.commit()
    return ids


def _names(data, ids) -> set[str]:
    back = {v: k for k, v in ids.items()}
    return {back.get(n["id"], n["id"]) for n in data["nodes"]}


def _edges(data, ids) -> set[tuple[str, str, str]]:
    back = {v: k for k, v in ids.items()}
    return {(*sorted((back[e["entity_a_id"]], back[e["entity_b_id"]])), e["kind"]) for e in data["edges"]}


def check_routes(client, ids) -> None:
    for query in ("", "?mode=visitable"):
        data = client.get(f"/api/locations/graph{query}").json()
        n = _ok(_names(data, ids) == {"D1", "D2a", "T"}, f"(a) visitable nodes {_names(data, ids)}")
        n += _ok(_edges(data, ids) == {("D1", "T", "connects_to")}, f"(a) visitable edges {_edges(data, ids)}")
        n += _ok(all("r" not in node for node in data["nodes"]), "(a) a visitable node carries r")
        COUNTS["a"] = COUNTS.get("a", 0) + n
    data = client.get("/api/locations/graph?mode=zones").json()
    radii = {node["id"]: node.get("r") for node in data["nodes"]}
    n = _ok(_names(data, ids) == {"D", "D2"}, f"(b) zone nodes {_names(data, ids)}")
    n += _ok(radii.get(ids["D"]) == 30 and radii.get(ids["D2"]) is None, f"(b) radii {radii}")
    n += _ok(_edges(data, ids) == {("D", "D2", "borde")}, f"(b) zone edges {_edges(data, ids)}")
    COUNTS["b"] = n
    data = client.get(f"/api/locations/graph?mode=ego&center={ids['D']}").json()
    n = _ok(_names(data, ids) == {"D", "D1", "D2"}, f"(c) ego nodes {_names(data, ids)}")
    n += _ok(_edges(data, ids) == {("D", "D2", "borde")}, f"(c) ego edges {_edges(data, ids)}")
    n += _ok(any(node["id"] == ids["D"] and node.get("r") == 30 for node in data["nodes"]), "(c) ego centre not larger")
    data = client.get(f"/api/locations/graph?mode=ego&center={ids['T']}").json()
    n += _ok(data["nodes"] == [] and data.get("empty_text") == "Ouvrez une zone.", f"(c) non-zone centre: {data}")
    COUNTS["c"] = n
    resp = client.get("/api/locations/graph?mode=carte")
    COUNTS["d"] = _ok(resp.status_code == 422, f"(d) unknown mode answered {resp.status_code}")


def check_frontend() -> None:
    graph = (FRONT / "Graph.svelte").read_text(encoding="utf-8")
    mount = (FRONT / "mount.js").read_text(encoding="utf-8")
    lieux = (FRONT / "consumers" / "lieux.js").read_text(encoding="utf-8")
    n = _ok("r={radiusOf(node)}" in graph and "r={NODE_R}" not in graph, "(e) Graph.svelte circles ignore node.r")
    n += _ok("{emptyText}" in graph, "(e) Graph.svelte does not show emptyText")
    n += _ok("emptyText: data.emptyText" in mount, "(e) mount.js does not pass emptyText")
    for needle in ("'visitable'", "'zones'", "'ego'", "dashedKinds: ['borde']", "onNodeDblClick"):
        n += _ok(needle in lieux, f"(e) consumers/lieux.js lacks {needle}")
    COUNTS["e"] = n


def main() -> int:
    engine = _fresh_engine()
    from fastapi.testclient import TestClient

    from world_engine.cockpit.app import app

    ids = _seed(engine)
    check_routes(TestClient(app, base_url="http://127.0.0.1"), ids)
    check_frontend()

    for key in ("a", "b", "c", "d", "e"):
        if not COUNTS.get(key):
            fail(f"({key}) vacuous-proof: zero outcomes examined")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: zone_graph — "
        f"(a) visitable mode [{COUNTS['a']}], (b) zones mode, top-level radius [{COUNTS['b']}], "
        f"(c) ego mode [{COUNTS['c']}], (d) unknown mode refused [{COUNTS['d']}], "
        f"(e) primitive radius + empty text, three mode buttons [{COUNTS['e']}]"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
