"""G1 check for TICKET-0041/BRIEF-0041-c — shared review-tree component.

Re-homed by BRIEF-0058-i (per RECON-SUPPLEMENT-0058's re-scope: this brief
became "review component + Region", not "Review Queue" -- the Review Queue
tab never used this component, RECON confirmed it three ways). The eleven
generics moved off index.html onto frontend/src/creation/review/registry.js;
region (the component's first Svelte consumer) moved onto Region.svelte,
using Review.svelte for its own tree rendering. The room batch generator
stays a legacy consumer, still calling reviewRegister/reviewCascade/... as
bare globals -- reachable via registry.js's installLegacyReviewBridge,
injected onto the legacy window at boot (frontend/src/creation/mount.js).
One implementation, two call surfaces; this check still proves there is
only one.

Fail-closed: a missing file, a component function whose braces do not
balance, or zero rules evaluated is a FAILURE, never a vacuous pass. This
check is the ONLY thing standing between the review component and a silent
re-coupling to region state; a rule that cannot fail is a rule that is not
there.

Rule 6a (index.html / legacy consumer boundary) deviates from a literal
reading of BRIEF-0041-c's "substring `review`, case-sensitive": that literal
form false-positives on pre-existing, unrelated occurrences of the English
word already on `main` — `doApprove`'s "reviewed but not applied" comment,
`doBatchAction`'s `/api/mutations/batch-review` endpoint literal,
`npcAgentLoadBatch`'s "review selects" comment, `renderCard`'s "reviewed
rows" comment. None of those four functions calls a review* symbol.
Matching on a whole-identifier boundary against the exact GENERICS names
instead proves the same "blast radius is exactly the sanctioned consumers"
claim the rule exists for, without breaking on unrelated English prose.

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
MOUNT_FILE = CREATION_SRC / "mount.js"

GONE = ["regionCascade", "regionIsAccepted", "regionToggleAccept",
        "regionRenderNotes", "regionRenderLocationNode", "regionRenderTree",
        "regionToggleLocGraph", "regionLocGraphData", "regionLocGraphRender"]
# TICKET-0057, BRIEF-0057-c: reviewGraphRender is retired, not merely moved --
# the review component no longer knows how a graph is drawn (that's the graph
# primitive's job, reached via a `graph:slot`/`graph:invalidate` dispatch).
RETIRED = ["reviewGraphRender"]
GENERICS = ["reviewCascade", "reviewIsAccepted", "reviewToggleAccept",
            "reviewNotes", "reviewNode", "reviewTree", "reviewOpenSheet",
            "reviewToggleGraph", "reviewGraphData",
            "reviewRegister", "reviewDescriptor"]
# The room batch generator is the sole surviving legacy consumer (BRIEF-0058-j
# moves it onto the Svelte component and closes this list to empty).
CONSUMER_ALLOW_LIST_LEGACY = ["batchRenderAll", "batchReviewDescriptor"]
# Files under frontend/src/creation/ permitted to import from review/registry.js:
# Region.svelte (the sanctioned Svelte consumer, via regionReviewDescriptor),
# Review.svelte (the component's own Svelte-native rendering half, uses
# reviewCascade the same way reviewNode/reviewTree do), and mount.js (installs
# the legacy bridge — infrastructure, not a consumer).
IMPORTER_ALLOW_LIST_SVELTE = {REGION_SVELTE, REVIEW_SVELTE, MOUNT_FILE}
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

    for path in (INDEX_HTML, REGISTRY_FILE, REVIEW_SVELTE, REGION_SVELTE, MOUNT_FILE):
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
    }
    for name in GONE:
        for path, text in scan_texts.items():
            if name in text:
                failures.append(f"rule1: {name!r} still present in {path}")

    # Rule 1b — reviewGraphRender is retired (TICKET-0057), same shape as rule 1.
    rules_evaluated += 1
    for name in RETIRED:
        for path, text in scan_texts.items():
            if name in text:
                failures.append(f"rule1b: {name!r} still present in {path} (retired by TICKET-0057)")

    # Rule 2 — each generic is defined exactly once, in registry.js.
    rules_evaluated += 1
    for name in GENERICS:
        count = len(re.findall(rf"function {re.escape(name)}\(", registry_src))
        if count != 1:
            failures.append(f"rule2: {name!r} defined {count} time(s) in {REGISTRY_FILE}, expected exactly 1")

    # Rule 3 — the component is blind to region.
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

    # Rule 5 — a single descriptor factory, at the Svelte locus, and a
    # single registration call.
    rules_evaluated += 1
    region_src = scan_texts[REGION_SVELTE]
    factory_count = len(re.findall(r"function regionReviewDescriptor\(", region_src))
    if factory_count != 1:
        failures.append(f"rule5: regionReviewDescriptor defined {factory_count} time(s) in {REGION_SVELTE}, expected exactly 1")
    register_count = len(re.findall(r"reviewRegister\('region'", region_src))
    if register_count != 1:
        failures.append(f"rule5: reviewRegister('region' appears {register_count} time(s) in {REGION_SVELTE}, expected exactly 1")

    # Rule 6a — the boundary holds inside index.html: only the legacy room
    # batch generator (and the generics themselves, absent here) may
    # reference a review* symbol.
    rules_evaluated += 1
    all_fn_names = sorted(set(re.findall(r"function\s+(\w+)\s*\(", html)))
    outside_fns = [n for n in all_fn_names if n not in CONSUMER_ALLOW_LIST_LEGACY]
    for name in outside_fns:
        body = _braced_function(html, name)
        if body and _SYMBOL_RE.search(body):
            failures.append(f"rule6a: {name!r} (outside CONSUMER_ALLOW_LIST_LEGACY) "
                             "references a review* symbol in index.html")

    # Rule 6b — the boundary holds on the Svelte side: only Region.svelte
    # (the sanctioned consumer), Review.svelte (the component's own render
    # half) and mount.js (installs the legacy bridge) may import from
    # review/registry.js.
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
          "nine region* names and reviewGraphRender gone across every locus, "
          "eleven review* generics singly-defined in review/registry.js and "
          "region-blind, reviewCascade is a pure one-parameter function keyed "
          "on fallbackParentId, single region descriptor factory in "
          "Region.svelte, boundary holds in index.html (legacy batch "
          "consumer) and via the Svelte import graph (Region.svelte/"
          "Review.svelte/mount.js)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
