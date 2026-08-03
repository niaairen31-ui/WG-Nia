"""G1 regression guard for TICKET-0043/BRIEF-0043-c's review-tree root-fallback fix.

Re-homed by BRIEF-0058-i: `reviewTree` moved off index.html onto
frontend/src/creation/review/registry.js (the review component's string-
render half, kept for the room batch generator's continued legacy use
until BRIEF-0058-j) -- this check follows it there. The guarantee itself
(the fix, and what regresses it) is unchanged.

`reviewTree` (frontend/src/creation/review/registry.js) builds
`childrenByParent` from `cascade.effectiveParent`
(the fallback-aware map `reviewCascade` computes — a rejected root's children
fall back to `null`, i.e. top-level, when their fallback target is also
rejected) but used to filter its `roots` list from the raw, non-fallback-aware
`n.parentId` instead — a node whose fallback resolves to `null` was excluded
from both structures and vanished from the tree. The one-line fix makes
`roots` use the same `cascade.effectiveParent` map `childrenByParent` already
uses.

This check asserts `reviewTree`'s `const roots = ...` line references
`cascade.effectiveParent`, scoped to that specific line inside `reviewTree`'s
body only — `parentId` legitimately appears elsewhere in the function's
sibling, `reviewNode` (the `reparented` line), which this check must not flag.

No DB, plain text/regex, same style as relation_graph.py's braced-function
scans. Exit 0 on pass, 1 on failure.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
REGISTRY_FILE = ROOT / "frontend" / "src" / "creation" / "review" / "registry.js"


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


def main() -> int:
    failures: list[str] = []

    registry_src = REGISTRY_FILE.read_text(encoding="utf-8") if REGISTRY_FILE.exists() else ""
    review_tree_src = _braced_function(registry_src, "reviewTree")
    if not review_tree_src:
        failures.append(f"reviewTree() not found in {REGISTRY_FILE}")
    else:
        roots_line_m = re.search(r"const roots = .*?;", review_tree_src)
        if not roots_line_m:
            failures.append("reviewTree()'s 'const roots = ...' line not found")
        else:
            roots_line = roots_line_m.group(0)
            if "cascade.effectiveParent" not in roots_line:
                failures.append(
                    "reviewTree()'s 'const roots = ...' line does not reference "
                    "cascade.effectiveParent (root-fallback regression, TICKET-0043)"
                )
            if re.search(r"n\.parentId\s*==\s*null", roots_line):
                failures.append(
                    "reviewTree()'s 'const roots = ...' line uses a bare "
                    "n.parentId == null filter instead of cascade.effectiveParent "
                    "(root-fallback regression, TICKET-0043)"
                )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(
        "PASS: review_root_fallback — reviewTree()'s roots filter uses "
        "cascade.effectiveParent, not a bare n.parentId == null check"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
