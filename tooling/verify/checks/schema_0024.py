"""G1 gate for TICKET-0024 schema: `faction.role_capacities` and
`npc_goal.prerequisites` are nullable JSON columns (BRIEF-0024-a; shared
with BRIEF-0024-c, which reads `role_capacities` on the AI path).

Imports `world_engine.models` for its in-memory SQLAlchemy table metadata
— no DB connection required.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import JSON  # noqa: E402

from world_engine import models  # noqa: E402


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def _check_column(table_name: str, columns, column_name: str) -> None:
    if column_name not in columns:
        fail(f"{table_name}.{column_name} column missing")
    col = columns[column_name]
    if not isinstance(col.type, JSON):
        fail(f"{table_name}.{column_name} is not JSON (got {col.type})")
    if not col.nullable:
        fail(f"{table_name}.{column_name} must be nullable")


def main():
    _check_column("faction", models.Faction.__table__.columns, "role_capacities")
    _check_column("npc_goal", models.NpcGoal.__table__.columns, "prerequisites")
    print("PASS: faction.role_capacities and npc_goal.prerequisites present, nullable JSON")
    sys.exit(0)


if __name__ == "__main__":
    main()
