"""G1 check: every field the creator-CRUD registry declares is a column of
the model it writes (TICKET-0102, BRIEF-0102-a).

TICKET-0091 dropped `faction.goals` (schema v2.06, the goals became `visee`
facts) but `ENTITY_TYPE_REGISTRY["faction"]` kept a `goals` field. The form
kept rendering it, the create silently discarded what was typed in it, and
`_extension_dict`'s `getattr(ext, "goals")` raised: every faction create,
read and update answered 500, while the corpus stayed green because no
check read a faction.

Two volets, each vacuous-proof:

  a. Extension volet -- for every `ENTITY_TYPE_REGISTRY` entry, every
     `field["name"]` is a column of `spec["model"].__table__`.
  b. Base volet -- every `ENTITY_BASE_FIELDS` `field["name"]` is a column of
     `Entity.__table__` (`_apply_base_fields` sets them by name).

Zero registry types, zero extension fields or zero base fields collected is
a FAIL: a registry that parses to nothing proves nothing.

Import-only: no table is created and no row is read. The database URL is
pointed at a throwaway path first because importing `world_engine.db`
resolves it fail-closed.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report(counts: dict[str, int]) -> int:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        f"PASS: registry_model_columns -- {counts['types']} registry type(s), "
        f"{counts['ext']} extension field(s), {counts['base']} base field(s), "
        "each a column of its model"
    )
    return 0


def main() -> int:
    tmp_dir = tempfile.mkdtemp()
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
    sys.path.insert(0, str(SRC))
    try:
        from world_engine.cockpit.crud.entities import ENTITY_BASE_FIELDS, ENTITY_TYPE_REGISTRY
        from world_engine.models import Entity
    except Exception as exc:  # noqa: BLE001 - a broken import is a FAIL
        fail(f"world_engine.cockpit.crud.entities failed to import: {exc}")
        return _report({})

    counts = {"types": 0, "ext": 0, "base": 0}

    for type_name, spec in ENTITY_TYPE_REGISTRY.items():
        counts["types"] += 1
        model = spec["model"]
        columns = set(model.__table__.columns.keys())
        for field in spec["fields"]:
            counts["ext"] += 1
            if field["name"] not in columns:
                fail(
                    f"ENTITY_TYPE_REGISTRY[{type_name!r}] declares field {field['name']!r}, "
                    f"which is not a column of {model.__name__} ({model.__tablename__}); "
                    "the create discards it and every read of that type raises"
                )

    entity_columns = set(Entity.__table__.columns.keys())
    for field in ENTITY_BASE_FIELDS:
        counts["base"] += 1
        if field["name"] not in entity_columns:
            fail(f"ENTITY_BASE_FIELDS declares field {field['name']!r}, which is not a column of Entity")

    if counts["types"] == 0:
        fail("zero ENTITY_TYPE_REGISTRY types collected -- a rule that passes on nothing proves nothing")
    if counts["ext"] == 0:
        fail("zero extension fields collected -- a rule that passes on nothing proves nothing")
    if counts["base"] == 0:
        fail("zero ENTITY_BASE_FIELDS collected -- a rule that passes on nothing proves nothing")

    return _report(counts)


if __name__ == "__main__":
    sys.exit(main())
