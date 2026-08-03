"""G1 check for TICKET-0041/BRIEF-0041-c — shared review-tree component.

Closed by BRIEF-0058-j (per RECON-SUPPLEMENT-0058's -j scope): this brief
converged the room batch generator -- the component's second and last
legacy consumer -- onto RoomBatch.svelte, so CONSUMER_ALLOW_LIST_LEGACY
below is now empty and rule 6a's boundary holds against EVERY function in
index.html, not an allow-listed one. The string-building render half
(reviewNode/reviewTree/reviewOpenSheet/reviewToggleGraph/reviewIsAccepted/
reviewToggleAccept/reviewNotes) and installLegacyReviewBridge are retired
along with their last caller -- GENERICS below shrinks to the four names
that still have a real reader: reviewCascade/reviewRegister/
reviewDescriptor/reviewGraphData.

Fail-closed: a missing file, a component function whose braces do not
balance, or zero rules evaluated is a FAILURE, never a vacuous pass. This
check is the ONLY thing standing between the review component and a silent
re-coupling to a consumer's own state; a rule that cannot fail is a rule
that is not there.

Rule 6a (index.html boundary) deviates from a literal reading of
BRIEF-0041-c's "substring `review`, case-sensitive": that literal form
false-positives on pre-existing, unrelated occurrences of the English word
already on `main` — `doApprove`'s "reviewed but not applied" comment,
`doBatchAction`'s `/api/mutations/batch-review` endpoint literal,
`npcAgentLoadBatch`'s "review selects" comment, `renderCard`'s "reviewed
rows" comment. Matching on a whole-identifier boundary against the exact
GENERICS names instead proves the same "the component has no legacy
consumer left" claim the rule exists for, without breaking on unrelated
English prose.

Rule 6b (Svelte-side boundary) uses the ES-module import graph instead of
identifier scanning: unlike index.html's global script scope, `import`
statements make "who can reach the generics" explicit and total, so the
rule is "which files import from review/registry.js", not "which function
bodies mention a review* name".

No DB, no subprocess, stdlib only. Exit 0 on pass / 1 on failure.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
INDEX_HTML = ROOT / "src" / "world_engine" / "cockpit" / "index.html"
FRONTEND_SRC = ROOT / "frontend" / "src"
CREATION_SRC = FRONTEND_SRC / "creation"
REGISTRY_FILE = CREATION_SRC / "review" / "registry.js"
REVIEW_SVELTE = CREATION_SRC / "Review.svelte"
REGION_SVELTE = CREATION_SRC / "Region.svelte"
ROOM_BATCH_SVELTE = CREATION_SRC / "RoomBatch.svelte"
GRAPH_REVIEW_CONSUMER = FRONTEND_SRC / "graph" / "consumers" / "review.js"

GONE = ["regionCascade", "regionIsAccepted", "regionToggleAccept",
        "regionRenderNotes", "regionRenderLocationNode", "regionRenderTree",
        "regionToggleLocGraph", "regionLocGraphData", "regionLocGraphRender"]
# TICKET-0057, BRIEF-0057-c: reviewGraphRender is retired, not merely moved --
# the review component no longer knows how a graph is drawn (that's the graph
# primitive's job, reached via a `graph:slot`/`graph:invalidate` dispatch).
# TICKET-0058, BRIEF-0058-j: the string-render half retires the same way,
# once its last caller (the room batch generator) converges.
RETIRED = ["reviewGraphRender", "reviewNode", "reviewTree", "reviewOpenSheet",
           "reviewToggleGraph", "reviewIsAccepted", "reviewToggleAccept",
           "reviewNotes", "installLegacyReviewBridge"]
GENERICS = ["reviewCascade", "reviewRegister", "reviewDescriptor", "reviewGraphData"]
# No legacy consumer survives BRIEF-0058-j -- both Region.svelte and
# RoomBatch.svelte are Svelte-native, so this stays empty. Kept as a named
# list (not deleted) so rule 6a's intent -- "the boundary holds against
# every index.html function, none allow-listed" -- reads the same way rule
# 6a's docstring paragraph describes it.
CONSUMER_ALLOW_LIST_LEGACY: list[str] = []
# Files under frontend/src/ permitted to import from review/registry.js:
# Region.svelte and RoomBatch.svelte (the two sanctioned Svelte consumers,
# via their own reviewRegister call), Review.svelte (the component's own
# Svelte-native rendering half, uses reviewCascade the same way both
# consumers' descriptors are read), and the graph primitive's review
# consumer (reads reviewGraphData directly, TICKET-0057/BRIEF-0058-j).
IMPORTER_ALLOW_LIST_SVELTE = {REGION_SVELTE, ROOM_BATCH_SVELTE, REVIEW_SVELTE, GRAPH_REVIEW_CONSUMER}
FORBIDDEN_IN_COMPONENT = ("region", "REGION_")

_SYMBOL_RE = re.compile(r"\b(?:" + "|".join(re.escape(n) for n in GENERICS) + r")\b")
IMPORT_RE = re.compile(r"""['"][^'"]*review/registry\.js['"]""")


def _braced_function(text: str, name: str) -> str:
    """Return `[export ]function NAME(...) { ... }`'s full source, brace-balanced."""
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
    rules_evaluated = 0

    for path in (INDEX_HTML, REGISTRY_FILE, REVIEW_SVELTE, REGION_SVELTE, ROOM_BATCH_SVELTE):
        if not path.exists() or not path.is_file():
            print(f"FAIL: {path} not found")
            return 1

    html = INDEX_HTML.read_text(encoding="utf-8")
    registry_src = REGISTRY_FILE.read_text(encoding="utf-8")
    if not html.strip():
        print(f"FAIL: {INDEX_HTML} is empty")
        return 1
    if not registry_src.strip():
        print(f"FAIL: {REGISTRY_FILE} is empty")
        return 1

    # Rule 1 — the nine region* review names (TICKET-0041 vintage) are gone,
    # anywhere, any context, across every locus this check knows about.
    rules_evaluated += 1
    scan_texts = {
        INDEX_HTML: html,
        REGISTRY_FILE: registry_src,
        REVIEW_SVELTE: REVIEW_SVELTE.read_text(encoding="utf-8"),
        REGION_SVELTE: REGION_SVELTE.read_text(encoding="utf-8"),
        ROOM_BATCH_SVELTE: ROOM_BATCH_SVELTE.read_text(encoding="utf-8"),
    }
    for name in GONE:
        for path, text in scan_texts.items():
            if name in text:
                failures.append(f"rule1: {name!r} still present in {path}")

    # Rule 1b — reviewGraphRender/the string-render half/the legacy bridge
    # installer are retired (TICKET-0057, TICKET-0058/BRIEF-0058-j), same
    # shape as rule 1.
    rules_evaluated += 1
    for name in RETIRED:
        for path, text in scan_texts.items():
            if name in text:
                failures.append(f"rule1b: {name!r} still present in {path} (retired)")

    # Rule 2 — each generic is defined exactly once, in registry.js.
    rules_evaluated += 1
    for name in GENERICS:
        count = len(re.findall(rf"function {re.escape(name)}\(", registry_src))
        if count != 1:
            failures.append(f"rule2: {name!r} defined {count} time(s) in {REGISTRY_FILE}, expected exactly 1")

    # Rule 3 — the component is blind to any one consumer's own state.
    rules_evaluated += 1
    bodies: dict[str, str] = {}
    for name in GENERICS:
        body = _braced_function(registry_src, name)
        bodies[name] = body
        if not body:
            failures.append(f"rule3/rule7: _braced_function returned empty for {name!r} in {REGISTRY_FILE} "
                             "(unbalanced braces or matched only in a comment)")
            continue
        for token in FORBIDDEN_IN_COMPONENT:
            if token in body:
                is_css = f'"{token}' in body or f"'{token}" in body or f"-{token}" in body.lower()
                failures.append(
                    f"rule3: {name!r} body contains forbidden token {token!r}"
                    + (" (a CSS class name or DOM id counts)" if is_css else "")
                )

    # Rule 4 — the fallback rule is a parameter, not a constant.
    rules_evaluated += 1
    cascade_body = bodies.get("reviewCascade", "")
    sig_m = re.search(r"function reviewCascade\(([^)]*)\)", registry_src)
    if not sig_m:
        failures.append(f"rule4: reviewCascade signature not found in {REGISTRY_FILE}")
    else:
        params = [p.strip() for p in sig_m.group(1).split(",") if p.strip()]
        if len(params) != 1:
            failures.append(f"rule4: reviewCascade takes {len(params)} parameter(s), expected exactly 1")
    if cascade_body:
        if "fallbackParentId" not in cascade_body:
            failures.append("rule4: reviewCascade body does not reference fallbackParentId")
        for forbidden in ("document.", "getElementById", "reviewDescriptor("):
            if forbidden in cascade_body:
                failures.append(f"rule4: reviewCascade body contains {forbidden!r} (must touch no DOM/registry)")

    # Rule 5 — a single descriptor factory per Svelte consumer, and a single
    # registration call each.
    rules_evaluated += 1
    for consumer_path, key, factory_name in (
        (REGION_SVELTE, "region", "regionReviewDescriptor"),
        (ROOM_BATCH_SVELTE, "batch", "batchReviewDescriptor"),
    ):
        consumer_src = scan_texts[consumer_path]
        factory_count = len(re.findall(rf"function {re.escape(factory_name)}\(", consumer_src))
        if factory_count != 1:
            failures.append(f"rule5: {factory_name} defined {factory_count} time(s) in {consumer_path}, expected exactly 1")
        register_count = len(re.findall(rf"reviewRegister\('{key}'", consumer_src))
        if register_count != 1:
            failures.append(f"rule5: reviewRegister('{key}' appears {register_count} time(s) in {consumer_path}, expected exactly 1")

    # Rule 6a — the boundary holds inside index.html: no function may
    # reference a review* symbol any more (CONSUMER_ALLOW_LIST_LEGACY is
    # empty since BRIEF-0058-j -- both consumers are Svelte-native).
    rules_evaluated += 1
    all_fn_names = sorted(set(re.findall(r"function\s+(\w+)\s*\(", html)))
    outside_fns = [n for n in all_fn_names if n not in CONSUMER_ALLOW_LIST_LEGACY]
    for name in outside_fns:
        body = _braced_function(html, name)
        if body and _SYMBOL_RE.search(body):
            failures.append(f"rule6a: {name!r} references a review* symbol in index.html "
                             "-- no legacy consumer should reach the review component any more")

    # Rule 6b — the boundary holds on the Svelte side: only the sanctioned
    # consumers/renderer/graph-consumer may import from review/registry.js.
    rules_evaluated += 1
    if not FRONTEND_SRC.is_dir():
        failures.append(f"rule6b: {FRONTEND_SRC} is not a directory")
    else:
        all_files = [p for p in FRONTEND_SRC.rglob("*") if p.is_file() and p != REGISTRY_FILE]
        if not all_files:
            failures.append("rule6b: zero files collected under frontend/src -- empty scan is a failure")
        importers = set()
        for path in all_files:
            text = path.read_text(encoding="utf-8")
            if IMPORT_RE.search(text):
                importers.add(path)
        if not importers:
            failures.append(f"rule6b: zero files import from {REGISTRY_FILE} -- a rule that passes on nothing is the flaw this fixes")
        extra = importers - IMPORTER_ALLOW_LIST_SVELTE
        for path in sorted(extra):
            failures.append(f"rule6b: {path} imports from {REGISTRY_FILE} but is not in the allow-list "
                             f"({sorted(p.name for p in IMPORTER_ALLOW_LIST_SVELTE)})")

    # Rule 7 — fail-closed and anti-vacuous.
    if rules_evaluated == 0:
        print("FAIL: zero rules evaluated — check is broken, not the repo clean")
        return 1

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(f"PASS: review_component — {rules_evaluated} rules evaluated, "
          "nine region* names, reviewGraphRender and the retired string-render "
          "half all gone across every locus, four review* generics "
          "singly-defined in review/registry.js and consumer-blind, "
          "reviewCascade is a pure one-parameter function keyed on "
          "fallbackParentId, single descriptor factory per Svelte consumer "
          "(Region.svelte/RoomBatch.svelte), boundary holds in index.html "
          "(zero legacy consumers) and via the Svelte import graph")
    return 0


if __name__ == "__main__":
    sys.exit(main())
