"""G1 check: the location-tree convergence lock (TICKET-0059, BRIEF-0059-f,
per SUPPLEMENT-0059-recon-amendments Amendment 1).

RECON-0059-a M4 found `_npcAgentTreeHtml`/`_linkAgentTreeHtml` share one
traversal (root detection, sort, recursion, the `linkagent-loc-node`/
`linkagent-loc-children` classes) despite diverging at the row control.
Amendment 1 extracts that traversal into `frontend/src/creation/
LocationTree.svelte`, landed BEFORE either agent migrates (this brief's
commit 1) and consumed by both (npcAgent here, linkAgent at `-g`). Without
a lock, a second consumer could just as easily grow its own copy of the
traversal instead of importing the primitive -- exactly the accidental
divergence (`_npcAgentTreeHtml` literally emits the `linkagent-*` classes,
copy-paste evidence per the ticket's own C1 note) this workstream exists to
end.

The rule: no `.svelte` file other than `LocationTree.svelte` may contain
BOTH the token `linkagent-loc-node` AND a self-recursive render (a
`{#snippet NAME(...)}` block that calls `{@render NAME(`  on itself, or a
`<svelte:self` usage). Either alone is fine -- a file may reuse the CSS
class without recursing (a static leaf), or recurse over something
unrelated to the location tree; it is the COMBINATION that reproduces this
primitive.

Same idiom as effect_self_write.py: module-level FAILURES list, fail(),
_report_and_exit(), ROOT via parents[3], stdlib only, no DB, no subprocess,
textual brace/tag-balance scanning rather than a real Svelte parser (this
project has none). Zero findings is the GOAL state, not a vacuity signal --
the vacuity guard sits on the SCAN, exactly as the brief specifies: zero
`.svelte` files collected, or `LocationTree.svelte` itself absent, is a
FAILURE, never a trivially-satisfied "nothing to check."
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRONTEND_SRC = ROOT / "frontend" / "src"
LOCATION_TREE_FILE = FRONTEND_SRC / "creation" / "LocationTree.svelte"

TOKEN = "linkagent-loc-node"

SNIPPET_DECL_RE = re.compile(r"\{#snippet\s+(\w+)\(")
BLOCK_OPEN_RE = re.compile(r"\{#\w+")
BLOCK_CLOSE_RE = re.compile(r"\{/\w+\}")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(scanned: int | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: location_tree — {scanned} .svelte file(s) scanned, "
        f"LocationTree.svelte confirmed present, 0 duplicate recursive "
        f"location-tree renderer(s) found"
    )
    sys.exit(0)


def _snippet_body(text: str, decl_start: int) -> str:
    """`decl_start` indexes the `{` of a `{#snippet NAME(...)}` opening tag.
    Returns the block-balanced source between that tag's own closing `}`
    and its matching `{/snippet}` (any nested `{#...}` block, of any kind,
    increments depth; any `{/...}` decrements it)."""
    open_end = text.index("}", decl_start) + 1
    depth = 1
    i = open_end
    n = len(text)
    while i < n and depth > 0:
        om = BLOCK_OPEN_RE.match(text, i)
        if om:
            depth += 1
            i = om.end()
            continue
        cm = BLOCK_CLOSE_RE.match(text, i)
        if cm:
            depth -= 1
            if depth == 0:
                return text[open_end:cm.start()]
            i = cm.end()
            continue
        i += 1
    return text[open_end:i]


def _self_recursive(text: str) -> bool:
    if "<svelte:self" in text:
        return True
    for m in SNIPPET_DECL_RE.finditer(text):
        name = m.group(1)
        body = _snippet_body(text, m.start())
        if re.search(rf"\{{@render\s+{re.escape(name)}\(", body):
            return True
    return False


def main() -> None:
    if not FRONTEND_SRC.is_dir():
        fail(f"vacuous scan: {FRONTEND_SRC} is not a directory")
        _report_and_exit()
        return

    svelte_files = sorted(FRONTEND_SRC.rglob("*.svelte"))
    if not svelte_files:
        fail("vacuous scan: zero .svelte files under frontend/src/")
        _report_and_exit()
        return

    if not LOCATION_TREE_FILE.is_file():
        fail(f"{LOCATION_TREE_FILE} does not exist — the location-tree primitive is absent")
        _report_and_exit()
        return

    for path in svelte_files:
        if path == LOCATION_TREE_FILE:
            continue
        text = path.read_text(encoding="utf-8")
        if TOKEN in text and _self_recursive(text):
            rel = path.relative_to(ROOT).as_posix()
            fail(
                f"{rel}: contains {TOKEN!r} and a self-recursive render — "
                "a second location-tree renderer"
            )

    _report_and_exit(len(svelte_files))


if __name__ == "__main__":
    main()
