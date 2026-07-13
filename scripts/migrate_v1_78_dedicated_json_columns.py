"""Migration to schema v1.78 — dedicated JSON columns relationalized/typed
(TICKET-0025, BRIEF-0025-b).

Second corrective step of TICKET-0025: `character.secrets` becomes plain
TEXT (no reader ever consumed structure, B1); `location.coordinates`
becomes two REAL columns `coord_x`/`coord_y` (A1); `location.subculture`
becomes the relational `location_subculture` table, whose `is_hidden` flag
makes the secret slice structurally excluded instead of cohabiting with
public keys in one blob (C1); `world.fundamental_laws` becomes the
position-ordered `world_law` table (D1).

In ONE transaction:
  a. Add `character.secrets` stays TEXT (data rewrite only, no DDL type
     change needed on SQLite); add `location.coord_x` / `coord_y`; create
     `location_subculture` + unique index; create `world_law` + unique
     index.
  b. `character.secrets`: JSON dicts/lists rewritten as
     `json.dumps(value, ensure_ascii=False, indent=2)` text; JSON strings
     unquoted to their inner text; NULL stays NULL.
  c. `location_subculture` rows from each subculture dict: key `hidden` ->
     `is_hidden = 1`; every other key -> `is_hidden = 0`; values coerced to
     str. Then drop `location.subculture`.
  d. `coord_x` / `coord_y` from `coordinates.x` / `.y`; drop
     `location.coordinates`.
  e. `world_law` rows: existing `fundamental_laws` string split on
     newlines (list values: one row per item), positions in order; drop
     `world.fundamental_laws`.
  f. SQLite >= 3.35 guard for the three DROP COLUMNs.

Read-only validation pass BEFORE any write, fail-closed:
  - any `location.subculture` that is non-NULL and not a flat dict of
    string/number values aborts, listing location ids.
  - any `location.coordinates` that is not NULL and not `{"x": num, "y":
    num}` aborts, listing location ids.
  - any `world.fundamental_laws` that is not NULL, not a string, and not a
    list of strings aborts, listing world ids.

Idempotent: safe to re-run — skips entirely once `location_subculture`
exists (the whole migration is one transaction, so a completed run is
all-or-nothing).

Run from the project root:
    python scripts/migrate_v1_78_dedicated_json_columns.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from numbers import Real
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402

MIN_SQLITE_VERSION = (3, 35)


def _load_locations(conn) -> list[dict]:
    rows = conn.execute(text(
        "SELECT location.id AS id, entity.name AS name, location.subculture AS subculture, "
        "location.coordinates AS coordinates FROM location "
        "JOIN entity ON entity.id = location.id"
    )).mappings().all()
    out = []
    for row in rows:
        subculture = json.loads(row["subculture"]) if row["subculture"] else None
        coordinates = json.loads(row["coordinates"]) if row["coordinates"] else None
        out.append({
            "id": row["id"], "name": row["name"],
            "subculture": subculture, "coordinates": coordinates,
        })
    return out


def _load_characters(conn) -> list[dict]:
    rows = conn.execute(text("SELECT id, secrets FROM character")).mappings().all()
    out = []
    for row in rows:
        raw_value = json.loads(row["secrets"]) if row["secrets"] is not None else None
        out.append({"id": row["id"], "raw_value": raw_value, "had_secrets": row["secrets"] is not None})
    return out


def _load_worlds(conn) -> list[dict]:
    rows = conn.execute(text("SELECT id, name, fundamental_laws FROM world")).mappings().all()
    out = []
    for row in rows:
        laws = json.loads(row["fundamental_laws"]) if row["fundamental_laws"] else None
        out.append({"id": row["id"], "name": row["name"], "fundamental_laws": laws})
    return out


def _validate(locations: list[dict], worlds: list[dict]) -> list[str]:
    problems: list[str] = []
    for loc in locations:
        subculture = loc["subculture"]
        if subculture is not None:
            if not isinstance(subculture, dict) or not all(
                isinstance(k, str) and isinstance(v, (str, Real)) and not isinstance(v, bool)
                for k, v in subculture.items()
            ):
                problems.append(f"{loc['id']} ({loc['name']!r}): subculture is not a flat string/number dict")
        coordinates = loc["coordinates"]
        if coordinates is not None:
            if (
                not isinstance(coordinates, dict)
                or set(coordinates) != {"x", "y"}
                or not all(isinstance(v, Real) and not isinstance(v, bool) for v in coordinates.values())
            ):
                problems.append(f"{loc['id']} ({loc['name']!r}): coordinates is not {{'x': num, 'y': num}}")
    for world in worlds:
        laws = world["fundamental_laws"]
        if laws is not None:
            if isinstance(laws, str):
                continue
            if isinstance(laws, list) and all(isinstance(item, str) for item in laws):
                continue
            problems.append(f"{world['id']} ({world['name']!r}): fundamental_laws is neither a string nor a list of strings")
    return problems


def _add_columns(conn) -> None:
    conn.execute(text("ALTER TABLE location ADD COLUMN coord_x REAL"))
    conn.execute(text("ALTER TABLE location ADD COLUMN coord_y REAL"))
    conn.execute(text("""
        CREATE TABLE location_subculture (
          id          TEXT PRIMARY KEY,
          world_id    TEXT NOT NULL REFERENCES world(id),
          location_id TEXT NOT NULL REFERENCES entity(id),
          key         TEXT NOT NULL,
          value       TEXT NOT NULL,
          is_hidden   BOOLEAN NOT NULL DEFAULT 0
        )
    """))
    conn.execute(text(
        "CREATE UNIQUE INDEX idx_location_subculture_key "
        "ON location_subculture(location_id, key COLLATE NOCASE)"
    ))
    conn.execute(text("""
        CREATE TABLE world_law (
          id       TEXT PRIMARY KEY,
          world_id TEXT NOT NULL REFERENCES world(id),
          position INTEGER NOT NULL DEFAULT 0,
          text     TEXT NOT NULL
        )
    """))
    conn.execute(text(
        "CREATE UNIQUE INDEX idx_world_law_position ON world_law(world_id, position)"
    ))


def _rewrite_secrets(conn, characters: list[dict]) -> int:
    rewritten = 0
    for char in characters:
        if not char["had_secrets"]:
            continue
        value = char["raw_value"]
        if isinstance(value, (dict, list)):
            new_text = json.dumps(value, ensure_ascii=False, indent=2)
        elif isinstance(value, str):
            new_text = value
        elif value is None:
            new_text = None
        else:
            new_text = str(value)
        conn.execute(text(
            "UPDATE character SET secrets = :secrets WHERE id = :id"
        ), {"secrets": new_text, "id": char["id"]})
        rewritten += 1
    return rewritten


def _insert_subculture_and_coords(conn, locations: list[dict]) -> tuple[int, int]:
    subculture_rows = 0
    coords_set = 0
    for loc in locations:
        world_id = conn.execute(text(
            "SELECT world_id FROM entity WHERE id = :id"
        ), {"id": loc["id"]}).scalar_one()
        if loc["subculture"]:
            for key, value in loc["subculture"].items():
                conn.execute(text(
                    "INSERT INTO location_subculture (id, world_id, location_id, key, value, is_hidden) "
                    "VALUES (:id, :world_id, :location_id, :key, :value, :is_hidden)"
                ), {
                    "id": str(uuid.uuid4()),
                    "world_id": world_id,
                    "location_id": loc["id"],
                    "key": key,
                    "value": str(value),
                    "is_hidden": 1 if key == "hidden" else 0,
                })
                subculture_rows += 1
        if loc["coordinates"]:
            conn.execute(text(
                "UPDATE location SET coord_x = :x, coord_y = :y WHERE id = :id"
            ), {
                "x": loc["coordinates"]["x"],
                "y": loc["coordinates"]["y"],
                "id": loc["id"],
            })
            coords_set += 1
    return subculture_rows, coords_set


def _insert_world_laws(conn, worlds: list[dict]) -> int:
    inserted = 0
    for world in worlds:
        laws = world["fundamental_laws"]
        if not laws:
            continue
        items = laws.splitlines() if isinstance(laws, str) else laws
        items = [item.strip() for item in items if item and item.strip()]
        for position, law in enumerate(items):
            conn.execute(text(
                "INSERT INTO world_law (id, world_id, position, text) "
                "VALUES (:id, :world_id, :position, :text)"
            ), {
                "id": str(uuid.uuid4()),
                "world_id": world["id"],
                "position": position,
                "text": law,
            })
            inserted += 1
    return inserted


def _drop_columns(conn) -> None:
    conn.execute(text("ALTER TABLE location DROP COLUMN subculture"))
    conn.execute(text("ALTER TABLE location DROP COLUMN coordinates"))
    conn.execute(text("ALTER TABLE world DROP COLUMN fundamental_laws"))


def main() -> None:
    inspector = inspect(engine)
    if "location_subculture" in inspector.get_table_names():
        print("Table 'location_subculture' already exists — migration already applied, skipping.")
        return

    if sqlite3.sqlite_version_info < MIN_SQLITE_VERSION:
        raise SystemExit(
            f"SQLite {'.'.join(map(str, MIN_SQLITE_VERSION))}+ is required for "
            f"ALTER TABLE ... DROP COLUMN (found {sqlite3.sqlite_version}). "
            "Upgrade SQLite, then re-run this migration — aborting, nothing written."
        )

    with engine.connect() as conn:
        locations = _load_locations(conn)
        characters = _load_characters(conn)
        worlds = _load_worlds(conn)

    problems = _validate(locations, worlds)
    if problems:
        raise SystemExit(
            "Migration aborted — unexpected content found, nothing written:\n"
            + "\n".join(f"  - {p}" for p in problems)
            + "\nResolve in the live UI, then re-run."
        )

    with engine.begin() as conn:
        _add_columns(conn)
        rewritten = _rewrite_secrets(conn, characters)
        subculture_rows, coords_set = _insert_subculture_and_coords(conn, locations)
        laws_inserted = _insert_world_laws(conn, worlds)
        _drop_columns(conn)

    print(
        f"Migration v1.78 applied: location.coord_x/coord_y + location_subculture + "
        f"world_law tables created, {rewritten} character.secrets value(s) rewritten "
        f"to plain text, {subculture_rows} subculture row(s) inserted across "
        f"{len({l['id'] for l in locations if l['subculture']})} location(s), "
        f"{coords_set} location(s) got coord_x/coord_y, {laws_inserted} world_law "
        f"row(s) inserted, location.subculture/coordinates and "
        f"world.fundamental_laws columns dropped."
    )


if __name__ == "__main__":
    main()
