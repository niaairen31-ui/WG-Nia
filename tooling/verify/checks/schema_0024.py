"""G1 gate for TICKET-0024 schema.

- BRIEF-0024-a: `npc_goal.prerequisites` is a nullable JSON column.
- BRIEF-0024-d (corrective): `faction_role` exists with the structural
  unique index `idx_faction_role_name` (faction_id, name COLLATE NOCASE);
  `faction.role_capacities` is gone. Static scan: no code path still reads
  or writes `entity.metadata['roles']` for a faction (the JSON source this
  brief replaced) — a fresh schema has no faction rows to check "no faction
  retains a metadata.roles key" against directly, so that invariant is
  verified as "no code writes it anymore".

Builds tables from a fresh temp-file SQLite DB (WORLD_ENGINE_DATABASE_URL
set before any world_engine import) so this check never touches Nia's real
DB, then falls back to a plain in-memory metadata check for the
`npc_goal.prerequisites` column (no DB connection required there).
"""
import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
CRUD = ROOT / "src" / "world_engine" / "cockpit" / "crud.py"
INDEX_HTML = ROOT / "src" / "world_engine" / "cockpit" / "index.html"
sys.path.insert(0, str(SRC))

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    db_path = pathlib.Path(tmp_dir) / "check.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]

    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def check_prerequisites_column() -> None:
    from sqlalchemy import JSON
    from world_engine import models

    columns = models.NpcGoal.__table__.columns
    if "prerequisites" not in columns:
        fail("npc_goal.prerequisites column missing")
        return
    col = columns["prerequisites"]
    if not isinstance(col.type, JSON):
        fail(f"npc_goal.prerequisites is not JSON (got {col.type})")
    if not col.nullable:
        fail("npc_goal.prerequisites must be nullable")


def check_faction_role_schema(engine) -> None:
    from sqlalchemy import inspect, text

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "faction_role" not in tables:
        fail("faction_role table does not exist")
        return

    columns = {c["name"] for c in inspector.get_columns("faction_role")}
    for col in ("id", "world_id", "faction_id", "name", "description", "max_holders", "position", "created_at", "created_by"):
        if col not in columns:
            fail(f"faction_role missing column {col!r}")

    indexes = inspector.get_indexes("faction_role")
    unique_name_idx = next(
        (idx for idx in indexes if idx["unique"] and set(idx["column_names"]) == {"faction_id", "name"}),
        None,
    )
    if unique_name_idx is None:
        fail("faction_role has no UNIQUE(faction_id, name) index")
    elif unique_name_idx["name"] != "idx_faction_role_name":
        fail(f"faction_role's unique (faction_id, name) index is misnamed: {unique_name_idx['name']!r}")

    with engine.connect() as conn:
        ddl = conn.execute(text(
            "SELECT sql FROM sqlite_master WHERE type='index' AND name='idx_faction_role_name'"
        )).scalar()
    if not ddl or "NOCASE" not in ddl.upper():
        fail(f"idx_faction_role_name is not COLLATE NOCASE (DDL: {ddl!r})")

    faction_columns = {c["name"] for c in inspector.get_columns("faction")}
    if "role_capacities" in faction_columns:
        fail("faction.role_capacities column still present — F1 drop not applied")


def check_no_metadata_roles_usage() -> None:
    """Static scan (BRIEF-0024-d): no code path reads/writes a faction's
    `entity.metadata['roles']` anymore — the JSON source this brief
    replaced with `faction_role`."""
    if not CRUD.exists():
        fail(f"{CRUD} not found")
    else:
        src = CRUD.read_text(encoding="utf-8")
        if 'metadata.get("roles")' in src or "metadata_.get(\"roles\")" in src:
            fail("crud.py still reads entity.metadata['roles'] — BRIEF-0024-d not fully applied")
        if "write_faction_role_capacities" in src:
            fail("crud.py still references write_faction_role_capacities (removed by BRIEF-0024-d)")

    if not INDEX_HTML.exists():
        fail(f"{INDEX_HTML} not found")
    else:
        src = INDEX_HTML.read_text(encoding="utf-8")
        if "detail.metadata.roles" in src or "entityData.metadata.roles" in src:
            fail("index.html still merges faction roles into entity.metadata — BRIEF-0024-d not fully applied")
        if "role-capacities" in src or "authorFactionCapacitiesDraft" in src:
            fail("index.html still references the removed role-capacities editor")


def main() -> None:
    # _fresh_engine() imports world_engine.models exactly once, against a
    # clean temp-DB sys.modules state — every subsequent check reuses that
    # same already-loaded module (re-importing it again would redefine
    # SQLAlchemy Table objects against the same metadata singleton and
    # raise InvalidRequestError).
    engine = _fresh_engine()
    check_prerequisites_column()
    check_faction_role_schema(engine)
    check_no_metadata_roles_usage()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)

    print(
        "PASS: npc_goal.prerequisites present; faction_role table + "
        "idx_faction_role_name (COLLATE NOCASE) present; "
        "faction.role_capacities and entity.metadata.roles usage gone"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
