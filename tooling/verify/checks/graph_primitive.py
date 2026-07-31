"""G1 check: the graph primitive convergence lock (TICKET-0057, BRIEF-0057-d).

Two of three graph implementations converged onto `Graph.svelte`
(TICKET-0057). Without a lock, that is a refactor: a third could stay
forever and a fourth could be born at the next feature, exactly as
`reviewGraphRender` was born beside `graphRender`. This check makes a
second graph engine constructible only by defeating a fail-closed gate.

Same idiom as import_cycle.py / legacy_mount.py: module-level FAILURES
list, fail(), _report_and_exit(counts), ROOT via parents[3], stdlib only,
no DB, no subprocess. Nine rules, each vacuous-proof — a missing file, an
empty scan or a zero-length collection is a FAILURE, never a trivially
satisfied comparison.

  1. GONE — zero dormant code: 21 retired tokens absent from index.html,
     any context, comments included. A converged implementation left
     behind "just in case" is the exact failure this ticket exists to
     prevent -- reviewGraphRender was born beside graphRender that way.
     Raw-substring, any context: a commented-out body is dormant code.
  2. No `<svg` anywhere in index.html — the legacy document emits no SVG
     graph at all after -b/-c.
  3. `frontend/src/graph/registry.js` parses, non-empty, monotone shrink
     against graph_impls.baseline.
  4. Every registry entry declares a well-formed retiredBy
     (`^TICKET-\\d{4}$`) plus non-empty engine/locus/fnPrefix.
  5. Every registry entry's locus still contains at least one
     `function <fnPrefix>\\w+(` declaration — the rule that keeps rule 3
     honest instead of rotting into a stale list.
  6. Engine confinement: no `cytoscape(` call and no `<svg` emission
     anywhere under frontend/src/ outside frontend/src/graph/; inside
     index.html, cytoscape( occurs only within a baselined entry's own
     function bodies.
  7. The primitive (Graph.svelte) never fetches and never writes.
  8. The primitive carries no scoped CSS. The component renders inside
     the legacy iframe document; Svelte injects scoped CSS into the
     SHELL's head, where it never reaches the frame. A <style> block here
     is CSS that silently does nothing.
  9. Closed contract vocabulary: every `graph: { ... }` spec in
     index.html sets only consumer/mountId/extraEdges. Zero specs
     collected is a failure — the rule must not pass by finding nothing.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRONTEND_SRC = ROOT / "frontend" / "src"
GRAPH_SRC = FRONTEND_SRC / "graph"
REGISTRY_FILE = GRAPH_SRC / "registry.js"
BASELINE_FILE = ROOT / "tooling" / "verify" / "baselines" / "graph_impls.baseline"
INDEX_HTML = ROOT / "src" / "world_engine" / "cockpit" / "index.html"
GRAPH_SVELTE = GRAPH_SRC / "Graph.svelte"

GONE_PLAIN = [
    "graphAutoPlace", "graphRender", "graphNodeMD", "_graphMouseMove",
    "_graphMouseUp", "_graphMoveSVGNode", "graphNodeClick", "graphEdgeClick",
    "graphCanvasClick", "graphCreateEdge", "graphPersistPos", "graphLoad",
    "reviewGraphRender", "graphData", "graphSelectedNodeId", "_graphDrag",
    "_graphPlaced",
]
GONE_WORD = ["GRAPH_W", "GRAPH_H", "NODE_R", "DRAG_THRESHOLD"]

ENTRY_RE = re.compile(
    r"(\w+):\s*Object\.freeze\(\{\s*"
    r"engine:\s*'([^']*)',\s*"
    r"locus:\s*'([^']*)',\s*"
    r"fnPrefix:\s*'([^']*)',\s*"
    r"retiredBy:\s*'([^']*)',?\s*"
    r"\}\)",
)
RETIRED_BY_RE = re.compile(r"^TICKET-\d{4}$")
CYTOSCAPE_CALL_RE = re.compile(r"cytoscape\(")
SVG_TAG_RE = re.compile(r"<svg")
GRAPH_SPEC_RE = re.compile(r"\bgraph:\s*\{")
FETCH_RE = re.compile(r"\bfetch\(|XMLHttpRequest")
WRITE_METHOD_RE = re.compile(r"""method:\s*['"](POST|PUT|DELETE)['"]""")
STYLE_TAG_RE = re.compile(r"<style")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(counts: dict | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: graph_primitive — {counts['gone']} retired token(s) confirmed absent, "
        f"{counts['registry']} registry entry(ies) within baseline, "
        f"{counts['loci']} entry(ies) with a live locus, "
        f"{counts['specs']} graph spec(s) validated"
    )
    sys.exit(0)


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


def _braced_bodies(text: str, prefix: str) -> list[str]:
    """All `function <prefix>\\w+(...) { ... }` bodies, brace-balanced."""
    names = sorted(set(re.findall(rf"function ({re.escape(prefix)}\w+)\(", text)))
    return [b for name in names if (b := _braced_function(text, name))]


def _rule1_gone(html: str) -> int:
    for token in GONE_PLAIN:
        if token in html:
            fail(f"rule1: retired token {token!r} still present in index.html")
    for token in GONE_WORD:
        if re.search(rf"\b{re.escape(token)}\b", html):
            fail(f"rule1: retired token {token!r} still present in index.html")
    return len(GONE_PLAIN) + len(GONE_WORD)


def _rule2_no_svg(html: str) -> bool:
    count = len(SVG_TAG_RE.findall(html))
    if count:
        fail(f"rule2: {count} '<svg' occurrence(s) remain in index.html — the legacy document must emit no SVG graph")
        return False
    return True


def _parse_registry() -> dict[str, dict[str, str]] | None:
    if not REGISTRY_FILE.is_file():
        fail(f"{REGISTRY_FILE} does not exist")
        return None
    text = REGISTRY_FILE.read_text(encoding="utf-8")
    entries: dict[str, dict[str, str]] = {}
    for key, engine, locus, fn_prefix, retired_by in ENTRY_RE.findall(text):
        entries[key] = {"engine": engine, "locus": locus, "fnPrefix": fn_prefix, "retiredBy": retired_by}
    if not entries:
        fail(f"{REGISTRY_FILE}: zero GRAPH_IMPLS entries parsed")
        return None
    return entries


def _rule3_shrink(keys: set[str]) -> bool:
    if not BASELINE_FILE.is_file():
        fail(f"{BASELINE_FILE} does not exist")
        return False
    baseline_keys = {
        line.strip() for line in BASELINE_FILE.read_text(encoding="utf-8").splitlines() if line.strip()
    }
    if not baseline_keys:
        fail(f"{BASELINE_FILE} is empty")
        return False
    ok = True
    for key in sorted(keys):
        if key not in baseline_keys:
            fail(f"graph impl {key!r} is not in the baseline — the registry may only SHRINK (TICKET-0057)")
            ok = False
    return ok


def _rule4_retired_by(entries: dict[str, dict[str, str]]) -> int:
    count = 0
    for key, entry in entries.items():
        if not RETIRED_BY_RE.match(entry.get("retiredBy", "")):
            fail(f"graph impl {key!r}: retiredBy {entry.get('retiredBy')!r} does not match ^TICKET-\\d{{4}}$")
            continue
        if not (entry.get("engine") and entry.get("locus") and entry.get("fnPrefix")):
            fail(f"graph impl {key!r}: engine/locus/fnPrefix must all be non-empty")
            continue
        count += 1
    return count


def _rule5_live_locus(entries: dict[str, dict[str, str]]) -> int:
    count = 0
    for key, entry in entries.items():
        locus = ROOT / entry["locus"]
        if not locus.is_file():
            fail(f"graph impl {key!r}: locus {entry['locus']!r} does not exist")
            continue
        text = locus.read_text(encoding="utf-8")
        if not re.search(rf"function {re.escape(entry['fnPrefix'])}\w+\(", text):
            fail(f"graph impl {key!r}: no function matching {entry['fnPrefix']!r} in {entry['locus']!r} — "
                 "the registry must shrink when its code goes")
            continue
        count += 1
    return count


def _rule6_engine_confinement(html: str, entries: dict[str, dict[str, str]]) -> bool:
    if not FRONTEND_SRC.is_dir():
        fail(f"{FRONTEND_SRC} is not a directory")
        return False
    files = [p for p in FRONTEND_SRC.rglob("*") if p.is_file()]
    if not files:
        fail(f"{FRONTEND_SRC} contains no files — empty scan is a failure")
        return False
    ok = True
    for path in files:
        if GRAPH_SRC in path.parents:
            continue
        text = path.read_text(encoding="utf-8")
        if CYTOSCAPE_CALL_RE.search(text):
            fail(f"{path}: 'cytoscape(' used outside frontend/src/graph/ — engine confinement violated")
            ok = False
        if SVG_TAG_RE.search(text):
            fail(f"{path}: '<svg' emitted outside frontend/src/graph/ — engine confinement violated")
            ok = False

    allowed_bodies = "\n".join(
        body
        for entry in entries.values()
        for body in _braced_bodies(html, entry["fnPrefix"])
    )
    allowed_calls = len(CYTOSCAPE_CALL_RE.findall(allowed_bodies))
    total_calls = len(CYTOSCAPE_CALL_RE.findall(html))
    if total_calls != allowed_calls:
        fail(f"rule6: {total_calls - allowed_calls} 'cytoscape(' call(s) in index.html fall outside "
             "a registered entry's function body")
        ok = False
    return ok


def _rule7_no_fetch_write() -> bool:
    if not GRAPH_SVELTE.is_file():
        fail(f"{GRAPH_SVELTE} does not exist")
        return False
    text = GRAPH_SVELTE.read_text(encoding="utf-8")
    ok = True
    if FETCH_RE.search(text):
        fail("rule7: Graph.svelte contains fetch(/XMLHttpRequest — the primitive must never fetch")
        ok = False
    if WRITE_METHOD_RE.search(text):
        fail("rule7: Graph.svelte contains a POST/PUT/DELETE method literal — the primitive must never write")
        ok = False
    return ok


def _rule8_no_scoped_css() -> bool:
    if not GRAPH_SVELTE.is_file():
        fail(f"{GRAPH_SVELTE} does not exist")
        return False
    if STYLE_TAG_RE.search(GRAPH_SVELTE.read_text(encoding="utf-8")):
        fail("rule8: Graph.svelte contains a <style> block — Svelte's scoped CSS never reaches the legacy frame")
        return False
    return True


_KEY_RE = re.compile(r"(\w+)\s*:")
_BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)


def _top_level_keys(body: str) -> set[str]:
    """Keys immediately inside `body`, never descending into a nested
    object/array/call — an `extraEdges` arrow function's own object
    literals (id/entity_a_id/...) must not count as contract keys. Block
    comments are stripped first: prose like "connection links: trim+..."
    would otherwise false-positive as a key at depth 0."""
    body = _BLOCK_COMMENT_RE.sub("", body)
    keys: set[str] = set()
    depth = 0
    i = 0
    while i < len(body):
        c = body[i]
        if c in "{([":
            depth += 1
            i += 1
            continue
        if c in "})]":
            depth -= 1
            i += 1
            continue
        if depth == 0:
            m = _KEY_RE.match(body, i)
            if m:
                keys.add(m.group(1))
                i = m.end()
                continue
        i += 1
    return keys


def _rule9_closed_vocab(html: str) -> int:
    allowed = {"consumer", "mountId", "extraEdges"}
    count = 0
    for m in GRAPH_SPEC_RE.finditer(html):
        start = m.end() - 1
        depth = 0
        end = None
        for i in range(start, len(html)):
            if html[i] == "{":
                depth += 1
            elif html[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end is None:
            fail("rule9: a 'graph: {' spec has unbalanced braces")
            continue
        body = html[start + 1:end]
        extra = _top_level_keys(body) - allowed
        if extra:
            fail(f"rule9: graph spec sets non-contract key(s) {sorted(extra)} — closed vocabulary is "
                 f"{sorted(allowed)}")
            continue
        count += 1
    if count == 0:
        fail("rule9: zero 'graph: {...}' specs collected — a rule that passes on nothing is the flaw this fixes")
    return count


def main() -> None:
    if not INDEX_HTML.is_file():
        fail(f"{INDEX_HTML} does not exist")
        _report_and_exit()
        return
    html = INDEX_HTML.read_text(encoding="utf-8")
    if not html.strip():
        fail(f"{INDEX_HTML} is empty")
        _report_and_exit()
        return

    gone_count = _rule1_gone(html)
    svg_ok = _rule2_no_svg(html)

    entries = _parse_registry()
    shrink_ok = False
    retired_count = 0
    locus_count = 0
    confinement_ok = False
    if entries is not None:
        shrink_ok = _rule3_shrink(set(entries.keys()))
        retired_count = _rule4_retired_by(entries)
        locus_count = _rule5_live_locus(entries)
        confinement_ok = _rule6_engine_confinement(html, entries)

    primitive_ok = _rule7_no_fetch_write()
    css_ok = _rule8_no_scoped_css()
    spec_count = _rule9_closed_vocab(html)

    if (
        FAILURES
        or entries is None
        or not svg_ok
        or not shrink_ok
        or not confinement_ok
        or not primitive_ok
        or not css_ok
    ):
        _report_and_exit()
        return

    _report_and_exit(
        {
            "gone": gone_count,
            "registry": retired_count,
            "loci": locus_count,
            "specs": spec_count,
        }
    )


if __name__ == "__main__":
    main()
