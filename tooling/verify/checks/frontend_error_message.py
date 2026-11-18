"""G1 check: a failed request's body becomes text only through frontend/src/lib/errorMessage.js (TICKET-0131, BRIEF-0131-a).

FastAPI answers `detail` as a string, as an object (`{message, ...}`,
`{failures: [...]}`) or, for a validation error, as a list of `{loc, msg}`.
A site that builds an `Error` from `detail` itself renders an object or a
list as "[object Object]", or drops the server's reason. One function reads
it for the creator's shell; this check holds that rule (INV-69).

- FE1 -- `frontend/src/lib/errorMessage.js` exists and holds
  `export function errorMessage(body, fallback)`.
- FE2 -- no line of a `.js` / `.svelte` under `frontend/src`, outside
  `frontend/src/joueur/` (the player shell keeps its own `call()`: PSH3
  keeps its imports inside its folder) and outside `lib/errorMessage.js`,
  matches `\\.detail\\s*\\|\\|`, `typeof\\s+\\w+\\.detail\\s*===` or
  `String\\(\\s*\\w+\\.detail`. Each hit is a FAIL naming file and line;
  zero files scanned is a FAILURE.
- FE3 -- every file outside `lib/` whose text holds `errorMessage(` imports
  `errorMessage` by a specifier ending `lib/errorMessage.js`; zero such
  files is a FAILURE.
- FE4 -- behaviour, run under Node (absent Node is a FAILURE, never a
  skip): the module, imported by its `file://` URL, answers the eight rows
  of CASES exactly, and no result holds "[object Object]".
"""
from __future__ import annotations

import json
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
FRONTEND_SRC = ROOT / "frontend" / "src"
MODULE = FRONTEND_SRC / "lib" / "errorMessage.js"
JOUEUR = FRONTEND_SRC / "joueur"

FAILURES: list[str] = []

EXPORT_SIGNATURE = "export function errorMessage(body, fallback)"
FORBIDDEN = [
    re.compile(r"\.detail\s*\|\|"),
    re.compile(r"typeof\s+\w+\.detail\s*==="),
    re.compile(r"String\(\s*\w+\.detail"),
]
IMPORT_RE = re.compile(
    r"import\s*\{[^}]*\berrorMessage\b[^}]*\}\s*from\s*['\"]([^'\"]+)['\"]"
)

# (body, fallback, expected) -- the lot's gate (b) table, verbatim.
CASES = [
    ({"detail": "Le nom est requis."}, "fb", "Le nom est requis."),
    (
        {"detail": {"message": "day narration rejected by judge: x", "reason": "x",
                    "offending_words": [], "prose": "p"}},
        "fb",
        "day narration rejected by judge: x",
    ),
    (
        {"detail": [{"type": "missing", "loc": ["body", "declared_action"],
                     "msg": "Field required", "input": {}}]},
        "fb",
        "declared_action : Field required",
    ),
    ({"detail": {"failures": ["a", "b"]}}, "fb", "a ; b"),
    ({"detail": {"weird": 1}}, '{"detail":{"weird":1}}', '{"detail":{"weird":1}}'),
    (None, "/api/x -> 500", "/api/x -> 500"),
    ({"detail": ""}, "fb", "fb"),
    ({"detail": [{"foo": 1}]}, "fb", "fb"),
]


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _sources() -> list[pathlib.Path]:
    return sorted(
        p for p in FRONTEND_SRC.rglob("*")
        if p.is_file() and p.suffix in (".js", ".svelte")
        and JOUEUR not in p.parents
    )


def rule_fe1() -> None:
    if not MODULE.is_file():
        fail(f"FE1: {MODULE.relative_to(ROOT).as_posix()} is missing")
        return
    if EXPORT_SIGNATURE not in MODULE.read_text(encoding="utf-8"):
        fail(f"FE1: lib/errorMessage.js does not hold `{EXPORT_SIGNATURE}`")


def rule_fe2(files: list[pathlib.Path]) -> int:
    scanned = 0
    for path in files:
        if path == MODULE:
            continue
        scanned += 1
        rel = path.relative_to(FRONTEND_SRC).as_posix()
        for no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if any(rx.search(line) for rx in FORBIDDEN):
                fail(f"FE2: {rel}:{no} reads `detail` into a message itself: {line.strip()}")
    if scanned == 0:
        fail("FE2: zero .js / .svelte files scanned under frontend/src")
    return scanned


def rule_fe3(files: list[pathlib.Path]) -> int:
    callers = 0
    for path in files:
        if path.parent == MODULE.parent:
            continue
        text = path.read_text(encoding="utf-8")
        if "errorMessage(" not in text:
            continue
        callers += 1
        specs = IMPORT_RE.findall(text)
        if not any(s.endswith("lib/errorMessage.js") for s in specs):
            rel = path.relative_to(FRONTEND_SRC).as_posix()
            fail(f"FE3: {rel} calls errorMessage( without importing it from lib/errorMessage.js")
    if callers == 0:
        fail("FE3: zero files call errorMessage( outside lib/")
    return callers


def rule_fe4() -> None:
    node = shutil.which("node")
    if node is None:
        fail("FE4: node is not on PATH; the behaviour cannot be proven")
        return
    if not MODULE.is_file():
        fail("FE4: lib/errorMessage.js is missing")
        return
    rows = [[body, fallback] for body, fallback, _ in CASES]
    script = (
        f"import {{ errorMessage }} from {json.dumps(MODULE.as_uri())};\n"
        f"const rows = {json.dumps(rows)};\n"
        "console.log(JSON.stringify(rows.map(([b, f]) => errorMessage(b, f))));\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        probe = pathlib.Path(tmp) / "probe.mjs"
        probe.write_text(script, encoding="utf-8")
        try:
            run = subprocess.run([node, str(probe)], capture_output=True, text=True, timeout=10)
        except subprocess.TimeoutExpired:
            fail("FE4: node did not answer within 10 seconds")
            return
    if run.returncode != 0:
        fail(f"FE4: node exited {run.returncode}: {run.stderr.strip()[:300]}")
        return
    try:
        results = json.loads(run.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        fail(f"FE4: unparsable node output: {run.stdout.strip()[:300]!r}")
        return
    if not isinstance(results, list) or len(results) != len(CASES):
        fail(f"FE4: expected {len(CASES)} results, got {results!r}")
        return
    for index, ((body, fallback, expected), got) in enumerate(zip(CASES, results), 1):
        if "[object Object]" in str(got):
            fail(f"FE4: row {index} ({json.dumps(body)}) holds [object Object]: {got!r}")
        elif got != expected:
            fail(f"FE4: row {index} ({json.dumps(body)}, {fallback!r}) -> {got!r}, expected {expected!r}")


def main() -> None:
    files = _sources()
    rule_fe1()
    scanned = rule_fe2(files)
    callers = rule_fe3(files)
    rule_fe4()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: frontend_error_message -- {scanned} file(s) scanned outside joueur/, "
        f"none reads `detail` itself; {callers} caller(s) import errorMessage from "
        f"lib/errorMessage.js; {len(CASES)} behaviour row(s) answered under Node"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
