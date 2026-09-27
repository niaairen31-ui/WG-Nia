"""G1 check for TICKET-0095 (K1). Created by BRIEF-0095-A with R0;
BRIEF-0095-B adds L0-L6 (the reader); BRIEF-0095-C adds T0-T10 (the
route).

Stdlib `ast` only, no DB — same FAILURES/fail()/`_rel`/`_parse`/
`ROOT = parents[3]` idiom as `day_rewrite.py`.

R0 (the JSON is write-only, G1): the `candidate_ids` / `evidence_fact_ids`
TEXT columns of `day_mention_choice` are an audit copy; their rows live in
`day_mention_choice_candidate` / `day_mention_choice_evidence`. In every
`.py` under `src/world_engine/`:
  (a) no call whose callee name is `loads` carries, anywhere in its
      arguments, an attribute access `.candidate_ids` / `.evidence_fact_ids`;
  (b) no attribute access `DayMentionChoice.candidate_ids` /
      `DayMentionChoice.evidence_fact_ids` exists (no query on the column).
Vacuity: `writes/pipeline.py` must still hold the `json.dumps(record[
"candidate_ids"], ...)` and `json.dumps(record["evidence_fact_ids"], ...)`
calls that write the audit copy — otherwise R0 guards nothing.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

WRITES_PIPELINE_FILE = SRC / "writes" / "pipeline.py"

_JSON_COLUMNS = {"candidate_ids", "evidence_fact_ids"}

FAILURES: list[str] = []
_TREE_CACHE: dict[pathlib.Path, "ast.Module | None"] = {}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _parse(path: pathlib.Path) -> "ast.Module | None":
    if path in _TREE_CACHE:
        return _TREE_CACHE[path]
    if not path.exists():
        fail(f"{_rel(path)}: file not found")
        _TREE_CACHE[path] = None
        return None
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        fail(f"{_rel(path)}: SyntaxError: {exc}")
        tree = None
    _TREE_CACHE[path] = tree
    return tree


def _callee_name(call: ast.Call) -> "str | None":
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _subscript_key(node: ast.AST) -> "str | None":
    if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
        value = node.slice.value
        return value if isinstance(value, str) else None
    return None


# ── R0 ───────────────────────────────────────────────────────────────────

def check_json_write_only() -> None:
    for path in sorted(SRC.rglob("*.py")):
        tree = _parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _callee_name(node) == "loads":
                for arg in [*node.args, *(kw.value for kw in node.keywords)]:
                    for sub in ast.walk(arg):
                        if isinstance(sub, ast.Attribute) and sub.attr in _JSON_COLUMNS:
                            fail(
                                f"choice_review R0(a): {_rel(path)}:{node.lineno} parses "
                                f".{sub.attr} — the JSON audit copy is never read; use the rows"
                            )
            if (
                isinstance(node, ast.Attribute)
                and node.attr in _JSON_COLUMNS
                and isinstance(node.value, ast.Name)
                and node.value.id == "DayMentionChoice"
            ):
                fail(
                    f"choice_review R0(b): {_rel(path)}:{node.lineno} references "
                    f"DayMentionChoice.{node.attr} — the JSON audit copy is never queried"
                )

    tree = _parse(WRITES_PIPELINE_FILE)
    if tree is None:
        return
    dumped = {
        _subscript_key(node.args[0])
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and _callee_name(node) == "dumps" and node.args
    }
    missing = sorted(_JSON_COLUMNS - dumped)
    if missing:
        fail(
            f"choice_review R0 vacuous: {_rel(WRITES_PIPELINE_FILE)} holds no json.dumps(record[...]) "
            f"for {missing!r}"
        )


def main() -> None:
    check_json_write_only()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: choice_review — R0")
    sys.exit(0)


if __name__ == "__main__":
    main()
