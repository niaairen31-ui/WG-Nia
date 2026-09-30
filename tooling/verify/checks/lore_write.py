"""G1 check for TICKET-0098 -- the lore writing path.

The lot adds its modules brief by brief; this check grows with it. Each
brief adds its files to `_LORE_WRITE_FILES` and its rules below in the same
commit (the `knowledge_identity.py` K3 census precedent, TICKET-0097).

L0 -- census. The files of the lore writing path that exist under
   `src/world_engine` (the glob `_CENSUS_GLOBS`) equal `_LORE_WRITE_FILES`
   exactly: a new module is red until a brief names it, a named module that
   is missing is red.

Fresh temp-file SQLite database for any fixture rule
(`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) -- never
Nia's DB.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

FAILURES: list[str] = []

_CENSUS_GLOBS = ("lore_write*.py", "writes/lore_entries.py", "cockpit/routes/lore_write*.py")
_LORE_WRITE_FILES: frozenset[str] = frozenset()


def fail(msg: str) -> None:
    FAILURES.append(msg)


def check_l0() -> None:
    found = {
        path.relative_to(SRC).as_posix()
        for pattern in _CENSUS_GLOBS for path in SRC.glob(pattern)
    }
    for extra in sorted(found - _LORE_WRITE_FILES):
        fail(f"L0: {extra} exists but no brief named it in _LORE_WRITE_FILES")
    for missing in sorted(_LORE_WRITE_FILES - found):
        fail(f"L0: {missing} is named in _LORE_WRITE_FILES but does not exist")


def main() -> int:
    check_l0()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(f"PASS: lore_write -- census of {len(_LORE_WRITE_FILES)} module(s) holds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
