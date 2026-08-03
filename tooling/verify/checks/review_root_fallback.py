"""G1 regression guard for TICKET-0043/BRIEF-0043-c's review-tree root-fallback fix.

Re-homed twice: BRIEF-0058-i moved `reviewTree` off index.html onto
frontend/src/creation/review/registry.js's string-render half; BRIEF-0058-j
retired that string-render half entirely once its last caller (the room
batch generator) converged onto RoomBatch.svelte, leaving Review.svelte's
own `const roots = $derived(...)` line as the sole surviving instance of
this fix. This check follows it there. The guarantee itself (the fix, and
what regresses it) is unchanged.

Review.svelte's `const roots = ...` line builds its root-node list from
`cascade.effectiveParent` (the fallback-aware map `reviewCascade` computes
— a rejected root's children fall back to `null`, i.e. top-level, when
their fallback target is also rejected), never from the raw, non-fallback-
aware `n.parentId` — a node whose fallback resolves to `null` would
otherwise vanish from the tree (the original TICKET-0043 bug).

This check asserts the file's `const roots = ...` line references
`cascade.effectiveParent` and never falls back to a bare `n.parentId ==
null` filter.

No DB, plain text/regex, same style as relation_graph.py's braced-function
scans. Exit 0 on pass, 1 on failure.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
REVIEW_SVELTE = ROOT / "frontend" / "src" / "creation" / "Review.svelte"


def main() -> int:
    failures: list[str] = []

    review_src = REVIEW_SVELTE.read_text(encoding="utf-8") if REVIEW_SVELTE.exists() else ""
    if not review_src.strip():
        failures.append(f"{REVIEW_SVELTE} does not exist or is empty")
    else:
        roots_line_m = re.search(r"const roots = .*?;", review_src)
        if not roots_line_m:
            failures.append(f"{REVIEW_SVELTE}: 'const roots = ...' line not found")
        else:
            roots_line = roots_line_m.group(0)
            if "cascade.effectiveParent" not in roots_line:
                failures.append(
                    f"{REVIEW_SVELTE}: 'const roots = ...' line does not reference "
                    "cascade.effectiveParent (root-fallback regression, TICKET-0043)"
                )
            if re.search(r"n\.parentId\s*==\s*null", roots_line):
                failures.append(
                    f"{REVIEW_SVELTE}: 'const roots = ...' line uses a bare "
                    "n.parentId == null filter instead of cascade.effectiveParent "
                    "(root-fallback regression, TICKET-0043)"
                )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(
        "PASS: review_root_fallback — Review.svelte's roots filter uses "
        "cascade.effectiveParent, not a bare n.parentId == null check"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
