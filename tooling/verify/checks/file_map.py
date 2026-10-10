"""G1 check for TICKET-0117 (BRIEF-0117-d, B1) -- the module map is generated
and never stale.

`tooling/standards/FILE_MAP.md` lists every Python module of
`src/world_engine`, `scripts`, `tooling/glue` and `tooling/verify` with the
first sentence of its docstring. It replaces the hand-kept tree CLAUDE.md held.
The renderer is imported from `tooling/glue/gen_file_map.py`, never a
second copy.

FM1 -- docstrings. Every non-empty module in those four trees has a module
   docstring. A new module without one is red until it says what it is.
FM2 -- scope. Each of the four trees yields at least one module (a scan
   that collects nothing is a FAILURE).
FM3 -- freshness. The committed map equals a fresh render, line for line
   (line endings ignored). Fix: `python tooling/glue/gen_file_map.py`.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "tooling" / "glue"))
import gen_file_map  # noqa: E402

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def main() -> int:
    groups, missing = gen_file_map.collect()
    for rel in missing:
        fail(f"FM1: {rel} has no module docstring")
    for scope in gen_file_map.SCOPES:
        if not any(d == scope or d.startswith(scope + "/") for d in groups):
            fail(f"FM2: zero modules collected under {scope}")
    if not gen_file_map.FILE_MAP.exists():
        fail("FM3: tooling/standards/FILE_MAP.md not found -- run gen_file_map.py")
    elif not missing:
        committed = gen_file_map.FILE_MAP.read_text(encoding="utf-8").splitlines()
        fresh = gen_file_map.render(groups).splitlines()
        if committed != fresh:
            changed = sorted(set(committed) ^ set(fresh))[:5]
            fail(f"FM3: FILE_MAP.md is stale -- run gen_file_map.py; first differing lines: {changed}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    count = sum(len(v) for v in groups.values())
    print(f"PASS: file_map -- {count} modules, each with a docstring, and FILE_MAP.md is fresh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
