"""G1 check for TICKET-0021/BRIEF-0021-b — AI agenda-draft assistant.

Asserts the standalone-sibling-generator shape is intact:
1. `generate_agenda_draft` exists in event_author.py (relocated from
   entity_author.py at TICKET-0028/BRIEF-0028-d) and its body contains none
   of `writes.`, `session.add`, `db.add`, `.commit(` — generate-and-return
   only, no canon write.
2. The `pt-agenda-draft` prompt template upsert exists in seed_pilot.py with
   usage="agenda_generation" and the exact four variables.
3. `POST /api/agendas/generate` is registered in the cockpit app.

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

EXPECTED_VARIABLES = ["owner_kind", "owner_name", "owner_context", "brief"]


def _function_source(path: pathlib.Path, name: str) -> str | None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return ast.get_source_segment(path.read_text(encoding="utf-8"), node)
    return None


def main() -> int:
    failures: list[str] = []

    body = _function_source(EVENT_AUTHOR, "generate_agenda_draft")
    if body is None:
        failures.append("generate_agenda_draft not found in event_author.py")
    else:
        for token in FORBIDDEN_SUBSTRINGS:
            if token in body:
                failures.append(
                    f"generate_agenda_draft's body contains {token!r} — "
                    "must be generate-and-return only, no canon write"
                )

    seed_src = SEED_PILOT.read_text(encoding="utf-8")
    if '"pt-agenda-draft"' not in seed_src:
        failures.append("pt-agenda-draft upsert not found in seed_pilot.py")
    else:
        # Slice from the id literal to the next upsert_prompt_template(...)'s
        # closing paren-on-its-own-line, mirroring the existing checks' loose
        # windowed-text approach (no full Python call-arg parser needed).
        start = seed_src.index('"pt-agenda-draft"')
        end = seed_src.find("\n    )", start)
        window = seed_src[start:end if end != -1 else start + 1000]
        if 'usage="agenda_generation"' not in window:
            failures.append(
                "pt-agenda-draft upsert does not set usage=\"agenda_generation\""
            )
        var_pattern = r"variables\s*=\s*\[\s*" + r"\s*,\s*".join(
            rf'["\']{name}["\']' for name in EXPECTED_VARIABLES
        ) + r"\s*\]"
        if not re.search(var_pattern, window):
            failures.append(
                f"pt-agenda-draft upsert does not set variables={EXPECTED_VARIABLES!r}"
            )

    app_src = APP_PY.read_text(encoding="utf-8")
    if '@router.post("/api/agendas/generate")' not in app_src:
        failures.append("POST /api/agendas/generate route not registered in routes/creator.py")

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(
        "PASS: agenda_assist — generate_agenda_draft writes no canon, "
        "pt-agenda-draft seeded with the exact contract, /api/agendas/generate registered"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
