"""G1 check for TICKET-0023/BRIEF-0023-b — NPC relation ego-graph.

Asserts the ticket's machine-checkable acceptance criteria that route here:
1. A vendored cytoscape file exists under cockpit/vendor/ and a GET route
   serves it (BRIEF-0023-a groundwork, re-verified here as this is the
   ticket's own gate).
2. `GET /api/characters/{entity_id}/relation-graph` is registered in
   crud.py and its handler body contains no write call (E1 — display-only,
   permanently).
3. That handler's relation query excludes `type IN ('connects_to',
   'controls')` in the WHERE clause itself (G1 — structural, never
   post-filtered).
4. No `fetch` with method POST/PUT/DELETE anywhere in the relGraph* JS
   code path (E1).
5. The Lieux graph component (graphLoad/graphRender/drag/edge handlers) is
   byte-identical to `main` — this ticket must not touch it (RECON finding
   4's contrast between the NPC graph and the Lieux SVG editor).

No DB, plain text/regex + one git subprocess call. Exit 0 on pass, 1 on
failure.
"""
from __future__ import annotations

import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
COCKPIT = ROOT / "src" / "world_engine" / "cockpit"
APP_PY = COCKPIT / "app.py"
CRUD_PY = COCKPIT / "crud.py"
INDEX_HTML = COCKPIT / "index.html"
VENDOR_DIR = COCKPIT / "vendor"

LIEUX_GRAPH_FUNCTIONS = [
    "graphAutoPlace", "graphRender", "graphNodeMD", "_graphMouseMove",
    "_graphMouseUp", "_graphMoveSVGNode", "graphNodeClick", "graphEdgeClick",
    "graphCanvasClick", "graphCreateEdge", "graphPersistPos", "graphLoad",
]


def _braced_function(text: str, name: str) -> str:
    """Return `function NAME(...) { ... }`'s full source, brace-balanced."""
    m = re.search(rf"function {re.escape(name)}\([^)]*\)\s*\{{", text)
    if not m:
        return ""
    start = text.find("{", m.end() - 1)
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.start():i + 1]
    return ""


def _git_show(ref: str, path: pathlib.Path) -> str | None:
    rel = path.relative_to(ROOT).as_posix()
    try:
        out = subprocess.run(
            ["git", "show", f"{ref}:{rel}"],
            cwd=ROOT, capture_output=True, check=True,
        )
        return out.stdout.decode("utf-8")
    except (subprocess.CalledProcessError, OSError, UnicodeDecodeError):
        return None


def main() -> int:
    failures: list[str] = []

    # 1. Vendored cytoscape file + serving route (BRIEF-0023-a).
    vendor_files = list(VENDOR_DIR.glob("cytoscape*.min.js")) if VENDOR_DIR.is_dir() else []
    if not vendor_files:
        failures.append("no cytoscape*.min.js file found under cockpit/vendor/")
    app_src = APP_PY.read_text(encoding="utf-8") if APP_PY.exists() else ""
    if not re.search(r"""@app\.get\(\s*["']/vendor/\{filename\}["']""", app_src):
        failures.append("no GET /vendor/{filename} route registered in app.py")

    # 2 & 3. The relation-graph endpoint: registered, write-free, excludes
    # connects_to/controls in its own WHERE clause.
    crud_src = CRUD_PY.read_text(encoding="utf-8") if CRUD_PY.exists() else ""
    route_m = re.search(
        r"""@router\.get\(\s*["']/characters/\{entity_id\}/relation-graph["']\s*\)\s*"""
        r"""def\s+\w+\([^)]*\)[^:]*:""",
        crud_src,
    )
    if not route_m:
        failures.append("GET /characters/{entity_id}/relation-graph is not registered in crud.py")
    else:
        start = route_m.end()
        next_def = re.search(r"\n(?:@router\.|def )", crud_src[start:])
        body = crud_src[start: start + next_def.start()] if next_def else crud_src[start:]
        if re.search(r"\bdb\.add\(|\bwrite_[a-z_]+\(", body):
            failures.append(
                "relation-graph handler contains a write call (db.add/write_*) "
                "— must be read-only (E1)"
            )
        if "not_in" not in body or "connects_to" not in body or "controls" not in body:
            failures.append(
                "relation-graph handler's relation query does not exclude "
                "connects_to/controls in its WHERE clause (G1)"
            )

    # 4. No POST/PUT/DELETE fetch anywhere in the relGraph* JS code path.
    html_src = INDEX_HTML.read_text(encoding="utf-8") if INDEX_HTML.exists() else ""
    section_m = re.search(
        r"NPC relation ego-graph.*?(?=Generic modal \(BRIEF-41\))", html_src, re.S
    )
    if not section_m:
        failures.append("NPC relation ego-graph JS section not found in index.html")
    else:
        relgraph_src = section_m.group(0)
        for method in ("POST", "PUT", "DELETE"):
            if re.search(rf"""method:\s*['"]{method}['"]""", relgraph_src):
                failures.append(
                    f"relGraph* code path contains a {method} fetch — must be display-only (E1)"
                )

    # 5. Lieux graph component byte-identical to main.
    main_html = _git_show("main", INDEX_HTML) or _git_show("origin/main", INDEX_HTML)
    if main_html is None:
        failures.append(
            "could not read index.html from 'main'/'origin/main' via git — "
            "cannot verify the Lieux graph component is untouched"
        )
    else:
        for fn in LIEUX_GRAPH_FUNCTIONS:
            here = _braced_function(html_src, fn)
            there = _braced_function(main_html, fn)
            if not here or not there:
                failures.append(f"Lieux graph function {fn}() not found (current or main)")
            elif here != there:
                failures.append(f"Lieux graph function {fn}() differs from main — must stay byte-untouched")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(
        "PASS: relation_graph — vendor route present, relation-graph endpoint "
        "read-only with structural connects_to/controls exclusion, no write "
        "fetch in relGraph* JS, Lieux graph component untouched"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
