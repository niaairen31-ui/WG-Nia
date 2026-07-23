"""G1 check for TICKET-0041/BRIEF-0041-c — shared review-tree component.

Fail-closed: a missing index.html, a component function whose braces do not
balance, or zero rules evaluated is a FAILURE, never a vacuous pass. This
check is the ONLY thing standing between the review component and a silent
re-coupling to region state; a rule that cannot fail is a rule that is not
there.

Rule 6 deviates from a literal reading of BRIEF-0041-c's "substring `review`,
case-sensitive": that literal form false-positives on pre-existing, unrelated
occurrences of the English word already on `main` — `doApprove`'s "reviewed
but not applied" comment, `doBatchAction`'s `/api/mutations/batch-review`
endpoint literal, `npcAgentLoadBatch`'s "review selects" comment,
`renderCard`'s "reviewed rows" comment. None of those four functions calls a
review* symbol. Matching on a whole-identifier boundary against the exact
GENERICS names instead proves the same "blast radius is exactly the four
sanctioned consumers" claim the rule exists for, without breaking on
unrelated English prose. Confirmed against the real file: the whole-identifier
matcher yields exactly CONSUMER_ALLOW_LIST and nothing else.

No DB, no subprocess, stdlib only. Exit 0 on pass / 1 on failure.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
INDEX_HTML = ROOT / "src" / "world_engine" / "cockpit" / "index.html"

GONE = ["regionCascade", "regionIsAccepted", "regionToggleAccept",
        "regionRenderNotes", "regionRenderLocationNode", "regionRenderTree",
        "regionToggleLocGraph", "regionLocGraphData", "regionLocGraphRender"]
GENERICS = ["reviewCascade", "reviewIsAccepted", "reviewToggleAccept",
            "reviewNotes", "reviewNode", "reviewTree", "reviewOpenSheet",
            "reviewToggleGraph", "reviewGraphData", "reviewGraphRender",
            "reviewRegister", "reviewDescriptor"]
CONSUMER_ALLOW_LIST = ["regionRenderAll", "regionReviewDescriptor",
                       "regionRenderFactionsPanel", "_sheetEntityOptions"]
FORBIDDEN_IN_COMPONENT = ("region", "REGION_")

_SYMBOL_RE = re.compile(r"\b(?:" + "|".join(re.escape(n) for n in GENERICS) + r")\b")


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
    rules_evaluated = 0

    if not INDEX_HTML.exists() or not INDEX_HTML.is_file():
        print(f"FAIL: {INDEX_HTML} not found")
        return 1
    html = INDEX_HTML.read_text(encoding="utf-8")
    if not html.strip():
        print(f"FAIL: {INDEX_HTML} is empty")
        return 1

    # Rule 1 — the nine region* review names are gone, anywhere, any context.
    rules_evaluated += 1
    for name in GONE:
        if name in html:
            failures.append(f"rule1: {name!r} still present in index.html")

    # Rule 2 — each generic is defined exactly once.
    rules_evaluated += 1
    for name in GENERICS:
        count = len(re.findall(rf"function {re.escape(name)}\(", html))
        if count != 1:
            failures.append(f"rule2: {name!r} defined {count} time(s), expected exactly 1")

    # Rule 3 — the component is blind to region.
    rules_evaluated += 1
    bodies: dict[str, str] = {}
    for name in GENERICS:
        body = _braced_function(html, name)
        bodies[name] = body
        if not body:
            failures.append(f"rule3/rule7: _braced_function returned empty for {name!r} "
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
    sig_m = re.search(r"function reviewCascade\(([^)]*)\)", html)
    if not sig_m:
        failures.append("rule4: reviewCascade signature not found")
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

    # Rule 5 — a single descriptor factory.
    rules_evaluated += 1
    factory_count = len(re.findall(r"function regionReviewDescriptor\(", html))
    if factory_count != 1:
        failures.append(f"rule5: regionReviewDescriptor defined {factory_count} time(s), expected exactly 1")
    register_count = len(re.findall(r"reviewRegister\('region'", html))
    if register_count != 1:
        failures.append(f"rule5: reviewRegister('region' appears {register_count} time(s), expected exactly 1")

    # Rule 6 — the boundary holds in the other direction (see module docstring
    # for why this matches whole review* identifiers, not the raw substring).
    rules_evaluated += 1
    all_fn_names = sorted(set(re.findall(r"function\s+(\w+)\s*\(", html)))
    outside_fns = [n for n in all_fn_names if n not in GENERICS and n not in CONSUMER_ALLOW_LIST]
    for name in outside_fns:
        body = _braced_function(html, name)
        if body and _SYMBOL_RE.search(body):
            failures.append(f"rule6: {name!r} (outside the component, not in CONSUMER_ALLOW_LIST) "
                             "references a review* symbol")

    # Rule 7 — fail-closed and anti-vacuous.
    if rules_evaluated == 0:
        print("FAIL: zero rules evaluated — check is broken, not the repo clean")
        return 1

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(f"PASS: review_component — {rules_evaluated} rules evaluated, "
          "nine region* names gone, twelve review* generics singly-defined and "
          "region-blind, reviewCascade is a pure one-parameter function keyed on "
          "fallbackParentId, single region descriptor factory, boundary holds "
          "in both directions")
    return 0


if __name__ == "__main__":
    sys.exit(main())
