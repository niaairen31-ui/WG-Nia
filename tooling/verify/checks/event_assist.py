"""G1 check for TICKET-0022/BRIEF-0022-b — AI event-draft assistant.

Asserts the standalone-sibling-generator shape is intact:
1. `generate_event_draft` exists in event_author.py (relocated from
   entity_author.py at TICKET-0028/BRIEF-0028-d) and its body contains none
   of `writes.`, `session.add`, `db.add`, `.commit(` — generate-and-return
   only, no canon write.
2. The returned dict literal in `generate_event_draft`'s success path has no
   `knowledge_status` key (I2 — the model must never decide what the world
   knows).
3. The `pt-event-draft` prompt template upsert exists in seed_pilot.py with
   usage="event_generation".
4. `POST /api/events/generate` is registered in the cockpit app.
5. `build_world_roster` filters `is_public` in its `where(...)` call and
   selects no `internal_name` (J3 — query-construction exclusion, never a
   post-filter).

No DB, stdlib `ast` only. Exit 0 on pass, 1 on failure.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
EVENT_AUTHOR = ROOT / "src" / "world_engine" / "event_author.py"
SEED_PILOT = ROOT / "scripts" / "seed_pilot.py"
APP_PY = ROOT / "src" / "world_engine" / "cockpit" / "routes" / "creator.py"

FORBIDDEN_SUBSTRINGS = ("writes.", "session.add", "db.add", ".commit(")


def _function_source(path: pathlib.Path, name: str, *, strip_docstring: bool = False) -> str | None:
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            src = ast.get_source_segment(text, node)
            if strip_docstring and src is not None:
                doc = ast.get_docstring(node)
                if doc:
                    doc_node = node.body[0]
                    doc_src = ast.get_source_segment(text, doc_node)
                    if doc_src:
                        src = src.replace(doc_src, "", 1)
            return src
    return None


def main() -> int:
    failures: list[str] = []

    body = _function_source(EVENT_AUTHOR, "generate_event_draft")
    if body is None:
        failures.append("generate_event_draft not found in event_author.py")
    else:
        for token in FORBIDDEN_SUBSTRINGS:
            if token in body:
                failures.append(
                    f"generate_event_draft's body contains {token!r} — "
                    "must be generate-and-return only, no canon write"
                )

    code_body = _function_source(EVENT_AUTHOR, "generate_event_draft", strip_docstring=True)
    if code_body is not None and "knowledge_status" in code_body:
        failures.append(
            "generate_event_draft's code (outside its docstring) references "
            "'knowledge_status' — must be structurally absent from the model "
            "contract, never read from `parsed` nor written to the returned dict (I2)"
        )

    roster_full = _function_source(EVENT_AUTHOR, "build_world_roster")
    roster_code = _function_source(EVENT_AUTHOR, "build_world_roster", strip_docstring=True)
    if roster_full is None:
        failures.append("build_world_roster not found in event_author.py")
    else:
        if "is_public" not in roster_full:
            failures.append("build_world_roster does not filter is_public")
        elif not re.search(r"\.where\([^)]*is_public", roster_full, re.DOTALL):
            failures.append(
                "build_world_roster's is_public filter is not in the where(...) "
                "clause — must be query construction, not a Python post-filter (J3)"
            )
        if roster_code and "internal_name" in roster_code:
            failures.append("build_world_roster references internal_name — must never be selected")

    seed_src = SEED_PILOT.read_text(encoding="utf-8")
    if '"pt-event-draft"' not in seed_src:
        failures.append("pt-event-draft upsert not found in seed_pilot.py")
    else:
        start = seed_src.index('"pt-event-draft"')
        end = seed_src.find("\n    )", start)
        window = seed_src[start:end if end != -1 else start + 1000]
        if 'usage="event_generation"' not in window:
            failures.append("pt-event-draft upsert does not set usage=\"event_generation\"")

    app_src = APP_PY.read_text(encoding="utf-8")
    if '@router.post("/api/events/generate")' not in app_src:
        failures.append("POST /api/events/generate route not registered in app.py")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(
        "PASS: event_assist — generate_event_draft writes no canon and never "
        "surfaces knowledge_status, build_world_roster filters is_public in SQL, "
        "pt-event-draft seeded, /api/events/generate registered"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
