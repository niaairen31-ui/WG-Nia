"""G1 check for TICKET-0023/BRIEF-0023-b, amended by TICKET-0033/BRIEF-0033-e
— NPC relation ego + global graph. Re-homed by TICKET-0058/BRIEF-0058-c: the
graph itself converged onto the primitive (frontend/src/graph/Graph.svelte),
so clauses 1 and 4 no longer have a legacy-document JS cluster to inspect —
they now assert the OPPOSITE of what they used to, and against a different
file.

Asserts the machine-checkable acceptance criteria that route here:
1. Amended by BRIEF-0058-c: no vendored graph engine exists under
   cockpit/vendor/ (the directory itself is gone) and no `/vendor/{filename}`
   route is registered in app.py — the engine converged onto the primitive's
   own SVG renderer; a second engine sneaking back in is exactly what
   graph_primitive.py's rule 6 (engine confinement) and this clause both
   exist to catch, from two different angles.
2. `GET /api/characters/{entity_id}/relation-graph` (ego) and
   `GET /api/relation-graph` (global, BRIEF-0033-e) are both registered in
   crud/relations.py, and both handler bodies contain no write call
   (read-only, permanently).
3. Both handlers' relation queries exclude `type IN ('connects_to',
   'controls')` in the WHERE clause itself (G1 — structural, never
   post-filtered).
4. Re-homed by BRIEF-0058-c: the fetch/render/display path used to live in
   index.html's relGraph* cluster; it now lives entirely in
   frontend/src/graph/consumers/relations.js, the sole consumer with a
   write capability for this graph (ego mode supplies none — permanently
   display-only by callback absence, not by grep, per graph_primitive.py's
   rule 7's confinement of the primitive itself). Every non-GET `fetch(`
   in that one file targets only the pre-existing sanctioned relation CRUD
   endpoints (`/api/entities/{id}/relations`, `/api/relations/{id}`); zero
   collected fetches is a failure (a rule that passes on nothing finding
   nothing is the flaw BRIEF-0058-b's vacuous-proof guards exist to catch).
5. (Retired, TICKET-0057.) This check used to assert the Lieux graph
   component was byte-identical to `main` via `git show`. That guard
   was fail-open by construction: on a branch it bit, but once merged
   `main == HEAD` and it passed trivially forever after -- a transient
   branch freeze wearing the costume of a permanent guard. The Lieux
   graph has since converged onto the graph primitive and no longer
   exists in index.html at all; the permanent guarantee now lives in
   `tooling/verify/checks/graph_primitive.py`, which forbids any graph
   implementation outside the registered set.

No DB, plain text/regex, stdlib only. Exit 0 on pass, 1 on failure.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
COCKPIT = ROOT / "src" / "world_engine" / "cockpit"
CRUD_PY = COCKPIT / "crud" / "relations.py"
CONTEXT_PY = ROOT / "src" / "world_engine" / "context.py"
APP_PY = COCKPIT / "app.py"
VENDOR_DIR = COCKPIT / "vendor"
RELATIONS_CONSUMER = ROOT / "frontend" / "src" / "graph" / "consumers" / "relations.js"

SANCTIONED_URL_RE = re.compile(r"/api/(entities/\$\{[^}]*\}/relations|relations/\$\{[^}]*\})")
# The consumer's own `api()` wrapper is the one place a raw `fetch(` call
# exists; every write call site is `api(\`URL\`, { method: '...', ... })`,
# so that is what this check inspects (mirrors the pre-BRIEF-0058-c check's
# `api(\`...\`` scan over the legacy relGraph* writer bodies).
WRITE_CALL_RE = re.compile(r"api\(\s*`([^`]*)`\s*,\s*\{[\s\S]*?method:\s*['\"](POST|PUT|DELETE)['\"]")


def main() -> int:
    failures: list[str] = []

    # 1. Amended BRIEF-0058-c: no vendored graph engine, no serving route.
    if VENDOR_DIR.is_dir():
        failures.append(f"{VENDOR_DIR} still exists — the vendored graph engine must be fully removed")
    app_src = APP_PY.read_text(encoding="utf-8") if APP_PY.exists() else ""
    if re.search(r"""@app\.get\(\s*["']/vendor/\{filename\}["']""", app_src):
        failures.append("a GET /vendor/{filename} route is still registered in app.py")

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

    # 4. Re-homed BRIEF-0058-c: every non-GET fetch in the relations
    # consumer targets only the pre-existing sanctioned relation CRUD
    # endpoints. Zero collected fetches is a failure — the consumer must
    # actually have a write path for this rule to mean anything.
    if not RELATIONS_CONSUMER.is_file():
        failures.append(f"{RELATIONS_CONSUMER} does not exist")
    else:
        consumer_src = RELATIONS_CONSUMER.read_text(encoding="utf-8")
        write_calls = WRITE_CALL_RE.findall(consumer_src)
        if not write_calls:
            failures.append(
                f"no POST/PUT/DELETE api(...) call found in {RELATIONS_CONSUMER} — "
                "a rule that passes on nothing is the flaw this fixes"
            )
        for url, _method in write_calls:
            if not SANCTIONED_URL_RE.search(url):
                failures.append(f"{RELATIONS_CONSUMER}: unsanctioned write endpoint {url!r}")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(
        "PASS: relation_graph — no vendored graph engine or /vendor route remains, ego + global "
        "relation-graph endpoints read-only with structural connects_to/controls exclusion, write "
        "fetches in the relations consumer confined to the sanctioned relation CRUD endpoints"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
