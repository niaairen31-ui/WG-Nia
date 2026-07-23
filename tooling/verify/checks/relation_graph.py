"""G1 check for TICKET-0023/BRIEF-0023-b, amended by TICKET-0033/BRIEF-0033-e
— NPC relation ego + global graph.

Asserts the machine-checkable acceptance criteria that route here:
1. A vendored cytoscape file exists under cockpit/vendor/ and a GET route
   serves it (BRIEF-0023-a groundwork, re-verified here as this is the
   ticket's own gate).
2. `GET /api/characters/{entity_id}/relation-graph` (ego) and
   `GET /api/relation-graph` (global, BRIEF-0033-e) are both registered in
   crud/relations.py, and both handler bodies contain no write call
   (read-only, permanently).
3. Both handlers' relation queries exclude `type IN ('connects_to',
   'controls')` in the WHERE clause itself (G1 — structural, never
   post-filtered).
4. Amended by BRIEF-0033-e's locked E1, rescoped by BRIEF-0043-a: the graph
   fetch/render/display path (every relGraph* function except the two
   sanctioned global-mode edge-panel writers) contains no write fetch. The
   relGraph* JS section is collected by function name — every
   `function relGraph\\w+(...) { ... }` in index.html, brace-balanced — not
   a comment-anchored slice (that anchor pair drifted after TICKET-0041 to
   also contain unrelated npcAgent*/linkAgent* functions). Any
   POST/PUT/DELETE fetch anywhere in that collected set exists ONLY inside
   `relGraphSaveEdgePanel`/`relGraphDeleteEdge`, and every fetch inside
   those two targets ONLY the pre-existing sanctioned relation CRUD
   endpoints (`/api/entities/{id}/relations`, `/api/relations/{id}`) — no
   new write surface, ego mode stays permanently display-only.
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
CONTEXT_PY = ROOT / "src" / "world_engine" / "context.py"
APP_PY = COCKPIT / "app.py"
CRUD_PY = COCKPIT / "crud" / "relations.py"
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

    # 2 & 3. The relation-graph endpoints (ego + global): registered,
    # write-free, exclude connects_to/controls in their own WHERE clause —
    # either inline or via the shared `_RELATION_GRAPH_EXCLUDED_TYPES`
    # constant both handlers reuse (BRIEF-0033-e's `_relation_graph_nodes`/
    # `_relation_graph_edges` refactor).
    crud_src = CRUD_PY.read_text(encoding="utf-8") if CRUD_PY.exists() else ""
    excl_const_m = re.search(r"_RELATION_GRAPH_EXCLUDED_TYPES\s*=\s*\(([^)]*)\)", crud_src)
    if excl_const_m:
        if "connects_to" not in excl_const_m.group(1) or "controls" not in excl_const_m.group(1):
            failures.append("_RELATION_GRAPH_EXCLUDED_TYPES does not exclude both connects_to and controls")
    else:
        # Not a local tuple literal — accept an (aliased or bare) import of
        # RELATION_GRAPH_EXCLUDED_TYPES from context.py, and resolve the
        # actual tuple contents there instead of failing outright.
        import_m = re.search(
            r"from\s+\S*context\s+import\s+RELATION_GRAPH_EXCLUDED_TYPES(?:\s+as\s+\w+)?",
            crud_src,
        )
        if not import_m:
            failures.append(
                "_RELATION_GRAPH_EXCLUDED_TYPES constant not found in crud/relations.py "
                "(neither a local tuple literal nor an import from context.py)"
            )
        else:
            context_src = CONTEXT_PY.read_text(encoding="utf-8") if CONTEXT_PY.exists() else ""
            context_const_m = re.search(r"RELATION_GRAPH_EXCLUDED_TYPES\s*=\s*\(([^)]*)\)", context_src)
            if not context_const_m:
                failures.append(
                    "RELATION_GRAPH_EXCLUDED_TYPES imported from context.py but not defined there"
                )
            elif "connects_to" not in context_const_m.group(1) or "controls" not in context_const_m.group(1):
                failures.append(
                    "context.py's RELATION_GRAPH_EXCLUDED_TYPES does not exclude both "
                    "connects_to and controls"
                )

    ROUTES = {
        "ego": r"""@router\.get\(\s*["']/characters/\{entity_id\}/relation-graph["']\s*\)\s*def\s+\w+\([^)]*\)[^:]*:""",
        "global": r"""@router\.get\(\s*["']/relation-graph["']\s*\)\s*def\s+\w+\([^)]*\)[^:]*:""",
    }
    for label, pattern in ROUTES.items():
        route_m = re.search(pattern, crud_src)
        if not route_m:
            failures.append(f"the {label} relation-graph GET route is not registered in crud/relations.py")
            continue
        start = route_m.end()
        next_def = re.search(r"\n(?:@router\.|def )", crud_src[start:])
        body = crud_src[start: start + next_def.start()] if next_def else crud_src[start:]
        if re.search(r"\bdb\.add\(|\bwrite_[a-z_]+\(", body):
            failures.append(
                f"{label} relation-graph handler contains a write call (db.add/write_*) "
                "— must be read-only (permanently)"
            )
        uses_shared_constant = "not_in(_RELATION_GRAPH_EXCLUDED_TYPES)" in body
        uses_inline_literal = "not_in" in body and "connects_to" in body and "controls" in body
        if not (uses_shared_constant or uses_inline_literal):
            failures.append(
                f"{label} relation-graph handler's relation query does not exclude "
                "connects_to/controls in its WHERE clause (G1)"
            )

    # 4. Amended by BRIEF-0033-e (locked E1): write fetches are confined to
    # the two sanctioned global-mode edge-panel writers, and those writers
    # call only the pre-existing sanctioned relation CRUD endpoints.
    html_src = INDEX_HTML.read_text(encoding="utf-8") if INDEX_HTML.exists() else ""
    relgraph_fn_names = sorted(set(re.findall(r"function\s+(relGraph\w+)\(", html_src)))
    if not relgraph_fn_names:
        failures.append("no relGraph\\w+ functions found in index.html")
    else:
        relgraph_src = "\n".join(
            _braced_function(html_src, name) for name in relgraph_fn_names
        )
        WRITE_FNS = ("relGraphSaveEdgePanel", "relGraphDeleteEdge")
        SANCTIONED_URL_RE = re.compile(r"/api/(entities/\$\{[^}]*\}/relations|relations/\$\{[^}]*\})")

        for fn in WRITE_FNS:
            body = _braced_function(html_src, fn)
            if not body:
                failures.append(f"{fn}() not found (BRIEF-0033-e sanctioned writer missing)")
                continue
            for m in re.finditer(r"api\(\s*`([^`]*)`", body):
                if not SANCTIONED_URL_RE.search(m.group(1)):
                    failures.append(f"{fn}() calls an unsanctioned endpoint {m.group(1)!r}")

        for method in ("POST", "PUT", "DELETE"):
            total = len(re.findall(rf"""method:\s*['"]{method}['"]""", relgraph_src))
            confined = sum(
                len(re.findall(rf"""method:\s*['"]{method}['"]""", _braced_function(html_src, fn) or ""))
                for fn in WRITE_FNS
            )
            if total != confined:
                failures.append(
                    f"{total - confined} {method} fetch(es) found in relGraph* JS outside "
                    f"{'/'.join(WRITE_FNS)} — the display/fetch path must stay read-only (E1)"
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
        "PASS: relation_graph — vendor route present, ego + global relation-graph "
        "endpoints read-only with structural connects_to/controls exclusion, write "
        "fetches confined to the sanctioned global-mode edge-panel writers, "
        "Lieux graph component untouched"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
