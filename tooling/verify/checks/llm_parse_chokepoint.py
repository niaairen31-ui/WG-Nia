"""G1 check: single LLM-parse chokepoint (TICKET-0027 R2, BRIEF-0027-a).

`json.loads` may appear in `src/` only:
  a. inside `src/world_engine/llm_parse.py` (the sanctioned chokepoint,
     created at TICKET-0027 stage e — doesn't exist yet), or
  b. at a site named in PERMANENT_ALLOW below (non-model JSON: Ollama
     transport envelopes, request bodies already destined for a 422 on
     bad input) — each entry carries a one-line reason, or
  c. at a site in a file named in TRANSITION_ALLOW below, up to that
     file's recorded `max_sites` — model-output parse sites that stage e
     migrates onto `llm_parse.py`. Counts may only shrink; this check
     never rewrites the list. The moment `llm_parse.py` exists in the
     tree, a non-empty TRANSITION_ALLOW is itself a failure — the
     migration is supposed to have emptied it by then.

A `json.loads` site matching none of the above is a FAILURE. Zero parsed
sites found in `src/` at all is a FAILURE (vacuous-pass guard: the known
sites must be seen, proving the scanner works — R2 always has *some* JSON
parsing, even post-migration, so this guard never trips legitimately).

No DB, stdlib `ast` only.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
LLM_PARSE_FILE = SRC / "world_engine" / "llm_parse.py"

# Non-model JSON. Site key is "relative/path.py::enclosing_qualname"
# (module scope if the call isn't inside any function). One reason each.
PERMANENT_ALLOW: dict[str, str] = {
    "src/world_engine/cockpit/routes/mutations.py::approve_mutation":
        "creator-edited proposed_mutation.payload from the review form, not model output",
    "src/world_engine/cockpit/crud/entities.py::_coerce_field":
        "creator CRUD request-body field decode, fail-closed 422 on bad input",
    "src/world_engine/ollama_client.py::ping":
        "Ollama /api/tags transport envelope — transport-only per CLAUDE.md",
    "src/world_engine/ollama_client.py::chat":
        "Ollama /api/chat transport envelope — transport-only per CLAUDE.md",
    "src/world_engine/ollama_client.py::chat_stream":
        "Ollama streaming NDJSON transport envelope — transport-only per CLAUDE.md",
}

# Model-output parse sites TICKET-0027 stage e migrated onto llm_parse.py.
# Emptied at stage e (BRIEF-0027-e): every site now goes through the
# chokepoint. Left in place, empty, as the enforcement anchor described
# in the module docstring above — a future transition reuses this shape.
TRANSITION_ALLOW: dict[str, int] = {}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit() -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: llm_parse_chokepoint — every json.loads site is the chokepoint, "
        "a named permanent site, or within its transition allowance"
    )
    sys.exit(0)


def _enclosing_qualname(tree: ast.Module, target: ast.AST) -> str:
    """Dotted path of the innermost function containing `target`, or ''
    for module scope — mirrors the function-grain attribution convention
    used by single_canon_write.py's ALLOWED_SITES."""
    best = ""

    def visit(node: ast.AST, prefix: str) -> None:
        nonlocal best
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualname = f"{prefix}.{child.name}" if prefix else child.name
                if child.lineno <= target.lineno <= (child.end_lineno or child.lineno):
                    best = qualname
                    visit(child, qualname)
                else:
                    visit(child, prefix)
            elif isinstance(child, ast.ClassDef):
                visit(child, f"{prefix}.{child.name}" if prefix else child.name)
            else:
                visit(child, prefix)

    visit(tree, "")
    return best


def _json_loads_sites(path: pathlib.Path) -> list[dict]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        fail(f"{path}: SyntaxError: {exc}")
        return []
    rel = path.relative_to(ROOT).as_posix()
    sites = []
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "loads"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "json"
        ):
            sites.append({"file": rel, "line": node.lineno, "qualname": _enclosing_qualname(tree, node)})
    return sites


def main() -> None:
    if LLM_PARSE_FILE.exists() and TRANSITION_ALLOW:
        fail(
            "src/world_engine/llm_parse.py exists but TRANSITION_ALLOW is non-empty "
            "— stage e must empty it as sites migrate onto the chokepoint"
        )

    py_files = sorted(SRC.rglob("*.py"))
    if not py_files:
        fail("zero .py files found under src/ — parse is broken, not the repo clean")
        _report_and_exit()
        return

    all_sites: list[dict] = []
    for path in py_files:
        all_sites.extend(_json_loads_sites(path))

    if not all_sites:
        fail("zero json.loads sites found under src/ — parse is broken, not the repo clean")
        _report_and_exit()
        return

    transition_counts: dict[str, int] = {}
    for site in all_sites:
        if site["file"] == "src/world_engine/llm_parse.py":
            continue
        key = f"{site['file']}::{site['qualname']}"
        if key in PERMANENT_ALLOW:
            continue
        if site["file"] in TRANSITION_ALLOW:
            transition_counts[site["file"]] = transition_counts.get(site["file"], 0) + 1
            continue
        fail(f"{key} (line {site['line']}) — json.loads site in neither PERMANENT_ALLOW nor TRANSITION_ALLOW")

    for rel, max_sites in TRANSITION_ALLOW.items():
        count = transition_counts.get(rel, 0)
        if count > max_sites:
            fail(f"{rel} has {count} transition json.loads site(s), past its allowance of {max_sites}")

    _report_and_exit()


if __name__ == "__main__":
    main()
