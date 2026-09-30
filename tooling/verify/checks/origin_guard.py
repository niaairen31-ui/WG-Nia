"""G1 check for TICKET-0098 (BRIEF-0098-A, decision I1) -- the origin guard.

O1 -- verdict table. `cockpit/origin_guard.py::verdict` returns the refusal
   message or None for every row of `_CASES` (method x Host x Origin).
O2 -- wiring. `cockpit/app.py` registers `origin_guard` with
   `app.middleware("http")` exactly once, and nothing else in
   `src/world_engine` calls `verdict` or `origin_guard` (one gate, one site).
O3 -- live. Through `TestClient(app)`: a POST from a non-local Host answers
   403 with `REFUSED_MESSAGE`; the same POST from a non-local Origin answers
   403; a GET from a non-local Host is not a 403; a POST from the local host
   with no Origin reaches the route (not a 403).
O4 -- every `TestClient(app` construction in `tooling/verify/checks/` that
   is followed in the same file by a write call (`.post(`, `.put(`,
   `.patch(`, `.delete(` on a client) passes `base_url="http://127.0.0.1"`.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. A rule that locates zero items is a
FAILURE.
"""
from __future__ import annotations

import ast
import os
import pathlib
import re
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"
CHECKS = ROOT / "tooling" / "verify" / "checks"
GUARD = SRC / "cockpit" / "origin_guard.py"
APP = SRC / "cockpit" / "app.py"

FAILURES: list[str] = []

_REFUSED = "refused"
# (method, host, origin, expected) -- expected is None (proceeds) or _REFUSED.
_CASES = (
    ("GET", "evil.example", None, None),
    ("GET", "127.0.0.1:8000", "https://evil.example", None),
    ("POST", "127.0.0.1:8000", None, None),
    ("POST", "localhost:8001", None, None),
    ("POST", "[::1]:8000", None, None),
    ("POST", "127.0.0.1:8000", "http://127.0.0.1:8000", None),
    ("POST", "127.0.0.1:8000", "http://localhost:5173", None),
    ("PUT", "127.0.0.1", "http://127.0.0.1", None),
    ("POST", "evil.example", None, _REFUSED),
    ("POST", "evil.example:8000", "http://evil.example:8000", _REFUSED),
    ("POST", None, None, _REFUSED),
    ("POST", "testserver", None, _REFUSED),
    ("POST", "127.0.0.1:8000", "https://evil.example", _REFUSED),
    ("POST", "127.0.0.1:8000", "null", _REFUSED),
    ("POST", "127.0.0.1:8000", "file://127.0.0.1", _REFUSED),
    ("PATCH", "127.0.0.1.evil.example", None, _REFUSED),
    ("DELETE", "localhost.evil.example:8000", None, _REFUSED),
    ("delete", "evil.example", None, _REFUSED),
)
_WRITE_CALL = re.compile(r"\bclient\.(post|put|patch|delete)\(")
_LOCAL_BASE = 'base_url="http://127.0.0.1"'


def fail(msg: str) -> None:
    FAILURES.append(msg)


def check_o1(guard_mod) -> None:
    for method, host, origin, expected in _CASES:
        got = guard_mod.verdict(method, host, origin)
        want = guard_mod.REFUSED_MESSAGE if expected == _REFUSED else None
        if got != want:
            fail(f"O1: verdict({method!r}, {host!r}, {origin!r}) = {got!r}, expected {want!r}")


def _is_middleware_registration(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Call)
        and isinstance(node.func.func, ast.Attribute)
        and node.func.func.attr == "middleware"
        and isinstance(node.func.func.value, ast.Name) and node.func.func.value.id == "app"
        and [a.value for a in node.func.args if isinstance(a, ast.Constant)] == ["http"]
        and len(node.args) == 1 and isinstance(node.args[0], ast.Name)
        and node.args[0].id == "origin_guard"
    )


def check_o2() -> None:
    tree = ast.parse(APP.read_text(encoding="utf-8"))
    regs = [n for n in ast.walk(tree) if _is_middleware_registration(n)]
    if len(regs) != 1:
        fail(f"O2: cockpit/app.py registers origin_guard {len(regs)} time(s), expected 1")
    scanned = 0
    for path in SRC.rglob("*.py"):
        if path in (GUARD, APP):
            continue
        scanned += 1
        text = path.read_text(encoding="utf-8")
        if re.search(r"\b(verdict|origin_guard)\(", text) and "origin_guard" in text:
            fail(f"O2: {path.relative_to(ROOT).as_posix()} calls the origin guard")
    if scanned == 0:
        fail("O2: scanned zero modules under src/world_engine")


def check_o3(guard_mod) -> None:
    from fastapi.testclient import TestClient
    from world_engine.cockpit.app import app

    far = TestClient(app, base_url="http://evil.example")
    resp = far.post("/api/lore/ask", json={"question": "x"})
    if resp.status_code != 403 or resp.json().get("detail") != guard_mod.REFUSED_MESSAGE:
        fail(f"O3: non-local Host POST answered {resp.status_code} {resp.text[:120]!r}")
    near = TestClient(app, base_url="http://127.0.0.1")
    resp = near.post("/api/lore/ask", json={"question": "x"},
                     headers={"origin": "https://evil.example"})
    if resp.status_code != 403:
        fail(f"O3: non-local Origin POST answered {resp.status_code}, expected 403")
    resp = far.get("/api/worlds")
    if resp.status_code == 403:
        fail("O3: a GET from a non-local Host was refused")
    resp = near.post("/api/lore/resolve", json={})
    if resp.status_code == 403:
        fail("O3: a local POST with no Origin was refused")


def check_o4() -> None:
    constructions = 0
    for path in sorted(CHECKS.glob("*.py")):
        if path.name == pathlib.Path(__file__).name:
            continue
        text = path.read_text(encoding="utf-8")
        if not _WRITE_CALL.search(text):
            continue
        for line in text.splitlines():
            if re.search(r"=\s*TestClient\(app\b", line):
                constructions += 1
                if _LOCAL_BASE not in line:
                    fail(f"O4: {path.name}: a writing TestClient lacks {_LOCAL_BASE}: {line.strip()}")
    if constructions == 0:
        fail("O4: found zero writing TestClient constructions")


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="origin_guard_")
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{tmp}/x.db"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(ROOT / "src"))
    from world_engine.cockpit import origin_guard as guard_mod
    from world_engine.db import create_db_and_tables

    create_db_and_tables()
    check_o1(guard_mod)
    check_o2()
    check_o3(guard_mod)
    check_o4()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: origin_guard -- writes from a non-local Host or Origin are refused; reads and "
          "local writes pass; one registration; every writing test client is local")
    return 0


if __name__ == "__main__":
    sys.exit(main())
