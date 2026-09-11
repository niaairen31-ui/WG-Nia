"""G1 check for TICKET-0084 (BRIEF-0084-a) — `skill_system` table shape.

DB-backed, self-contained fresh temp-file SQLite fixture (same idiom as
fact_spine.py / trait_registry_projection.py), so this check never touches
Nia's real DB. Zero columns/constraints collected on any volet is a FAIL,
never a vacuous pass (known_reachability.py rule).

Four assertions:
  1. `skill_system` exists with exactly the columns `id, world_id, name,
     description, created_at, updated_at` — no extras.
  2. `skill_definition.system_id` exists and is nullable.
  3. `BASE_SKILL_DOMAINS` has exactly four members.
  4. `ck_skill_definition_base_domain`'s constraint text still names exactly
     `physical`, `agility`, `perception`, `composure`.
"""
from __future__ import annotations

import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []

EXPECTED_SKILL_SYSTEM_COLUMNS = {
    "id", "world_id", "name", "description", "created_at", "updated_at",
}
EXPECTED_BASE_DOMAINS = {"physical", "agility", "perception", "composure"}


def fail(msg: str) -> None:
    FAILURES.append(msg)


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


def _check_skill_system_columns(inspector) -> None:
    cols = {c["name"] for c in inspector.get_columns("skill_system")}
    if not cols:
        fail("vacuous-proof: zero columns collected on skill_system — table missing or check is broken")
        return
    missing = EXPECTED_SKILL_SYSTEM_COLUMNS - cols
    extra = cols - EXPECTED_SKILL_SYSTEM_COLUMNS
    if missing:
        fail(f"skill_system is missing column(s): {sorted(missing)}")
    if extra:
        fail(f"skill_system carries unexpected column(s): {sorted(extra)}")


def _check_system_id_column(inspector) -> None:
    cols = {c["name"]: c for c in inspector.get_columns("skill_definition")}
    if not cols:
        fail("vacuous-proof: zero columns collected on skill_definition — check is broken")
        return
    if "system_id" not in cols:
        fail("skill_definition.system_id is missing")
        return
    if not cols["system_id"]["nullable"]:
        fail("skill_definition.system_id must be nullable")


def _check_base_domains() -> None:
    from world_engine.models import BASE_SKILL_DOMAINS

    domains = set(BASE_SKILL_DOMAINS)
    if not domains:
        fail("vacuous-proof: BASE_SKILL_DOMAINS is empty")
        return
    if domains != EXPECTED_BASE_DOMAINS:
        fail(
            f"BASE_SKILL_DOMAINS must be exactly {sorted(EXPECTED_BASE_DOMAINS)}, "
            f"got {sorted(domains)}"
        )


def _check_base_domain_constraint(inspector) -> None:
    constraints = inspector.get_check_constraints("skill_definition")
    if not constraints:
        fail("vacuous-proof: zero CHECK constraints collected on skill_definition")
        return
    named = [c for c in constraints if c["name"] == "ck_skill_definition_base_domain"]
    if not named:
        fail("ck_skill_definition_base_domain constraint not found on skill_definition")
        return
    sqltext = named[0]["sqltext"] or ""
    literals = set(re.findall(r"'([^']+)'", sqltext))
    if not literals:
        fail(f"vacuous-proof: zero literals parsed from ck_skill_definition_base_domain: {sqltext!r}")
        return
    if literals != EXPECTED_BASE_DOMAINS:
        fail(
            f"ck_skill_definition_base_domain must name exactly {sorted(EXPECTED_BASE_DOMAINS)}, "
            f"found {sorted(literals)}: {sqltext!r}"
        )


def main() -> int:
    engine = _fresh_engine()
    from sqlalchemy import inspect

    inspector = inspect(engine)

    _check_skill_system_columns(inspector)
    _check_system_id_column(inspector)
    _check_base_domains()
    _check_base_domain_constraint(inspector)

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: skill_system_shape — skill_system table shape matches, "
        "skill_definition.system_id exists and is nullable, "
        "BASE_SKILL_DOMAINS is exactly four, and "
        "ck_skill_definition_base_domain names all four"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
