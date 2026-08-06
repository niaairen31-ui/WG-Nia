"""G1 check: the graph primitive convergence lock (TICKET-0057, BRIEF-0057-d;
amended BRIEF-0058-b to prove convergence, not just presence).

Two of three graph implementations converged onto `Graph.svelte`
(TICKET-0057). Without a lock, that is a refactor: a third could stay
forever and a fourth could be born at the next feature, exactly as
`reviewGraphRender` was born beside `graphRender`. This check makes a
second graph engine constructible only by defeating a fail-closed gate.

Same idiom as import_cycle.py / legacy_mount.py: module-level FAILURES
list, fail(), _report_and_exit(counts), ROOT via parents[3], stdlib only,
no DB, no subprocess. Ten rules, each vacuous-proof — a missing file, an
empty scan or a zero-length collection is a FAILURE, never a trivially
satisfied comparison.

  1. GONE — zero dormant code: every retired token (GONE_PLAIN/GONE_WORD/
     GONE_CASE_INSENSITIVE) absent from index.html, any context, comments
     included. A converged implementation left behind "just in case" is
     the exact failure this ticket exists to prevent -- reviewGraphRender
     was born beside graphRender that way, and TICKET-0058 (BRIEF-0058-c)
     grew the list again with the relGraph* cluster and its vendored
     engine. Raw-substring, any context: a commented-out body is dormant
     code.
  2. No `<svg` anywhere in index.html — the legacy document emits no SVG
     graph at all after -b/-c.
  3. `frontend/src/graph/registry.js` parses, monotone shrink against
     graph_impls.baseline (the baseline itself must be non-empty — it
     never shrinks, it is the ceiling). An EMPTY registry is no longer a
     failure by itself (BRIEF-0058-b): the set of retired keys is
     `baseline - live`, and rule 5b ranges over exactly that set.
  4. Every registry entry declares a well-formed retiredBy
     (`^TICKET-\\d{4}$`) plus non-empty engine/locus/fnPrefix.
  5. Every LIVE registry entry's locus still contains at least one
     `function <fnPrefix>\\w+(` declaration — the rule that keeps rule 3
     honest instead of rotting into a stale list.
  5b. Every RETIRED key (baseline - live) is proven gone, not just
      removed from the registry: its fnPrefix/locus are read from
      `graph_impls.retired` (append-only — a key enters it in the same
      commit that removes it from registry.js, never removed after), and
      that locus must contain ZERO occurrences of the prefix in ANY
      context, comments included — a converged implementation kept "just
      in case" is the exact failure this rule exists to catch. Vacuous-
      proof both ways: zero live entries plus zero retired records proven
      is a FAILURE (nothing was ever registered, so nothing is proven); a
      retired record naming a locus file that doesn't exist is a FAILURE;
      a malformed record line is a FAILURE.
  6. Engine confinement: no `cytoscape(` call and no `<svg` emission
     anywhere under frontend/src/ outside frontend/src/graph/; inside
     index.html, cytoscape( occurs only within a baselined entry's own
     function bodies.
  7. The primitive (Graph.svelte) never fetches and never writes.
  8. The primitive carries no scoped CSS. The component renders inside
     the legacy iframe document; Svelte injects scoped CSS into the
     SHELL's head, where it never reaches the frame. A <style> block here
     is CSS that silently does nothing.
  9. Closed contract vocabulary: every `graph: { ... }` spec sets only
     consumer/mountId/extraEdges. Amended by BRIEF-0058-i: a descriptor's
     `graph` spec can now live in index.html (region's stayed there through
     BRIEF-0058-h; the room batch generator's still does, until BRIEF-0058-j)
     OR under frontend/src/creation/ (region's own spec, moved onto
     Region.svelte by BRIEF-0058-i) -- this rule collects from both loci and
     sums them. Zero specs collected across BOTH is a failure — the rule
     must not pass by finding nothing.
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
RETIRED_FILE = ROOT / "tooling" / "verify" / "baselines" / "graph_impls.retired"
INDEX_HTML = ROOT / "src" / "world_engine" / "cockpit" / "index.html"
GRAPH_SVELTE = GRAPH_SRC / "Graph.svelte"

GONE_PLAIN = [
    "graphAutoPlace", "graphRender", "graphNodeMD", "_graphMouseMove",
    "_graphMouseUp", "_graphMoveSVGNode", "graphNodeClick", "graphEdgeClick",
    "graphCanvasClick", "graphCreateEdge", "graphPersistPos", "graphLoad",
    "reviewGraphRender", "graphData", "graphSelectedNodeId", "_graphDrag",
    "_graphPlaced",
    # TICKET-0058 (BRIEF-0058-c): the fifteen relGraph* functions plus their
    # underscore-prefixed helpers and module-level state, all converged
    # onto the graph primitive (frontend/src/graph/consumers/relations.js).
    "relGraphLoad", "relGraphOnSelect", "relGraphFetch", "relGraphFetchGlobal",
    "relGraphToggleMode", "relGraphToggleLinkMode", "relGraphRenderCanvas",
    "relGraphGlobalNodeTap", "relGraphGlobalNodeDblTap", "relGraphEdgeTap",
    "relGraphBucketToggle", "relGraphRenderInfoCard", "relGraphOpenEdgePanel",
    "relGraphSaveEdgePanel", "relGraphDeleteEdge",
    "_relGraphBucket", "_relGraphRenderEmptyState", "_relGraphUpdateModeUI",
    "_relGraphApplyBucketVisibility", "_relGraphReset",
    "relGraphData", "relGraphCy", "relGraphBucketState", "relGraphMode",
    "relGraphLinkArmed", "relGraphLinkSourceId", "_relGraphEdgePanelCtx",
    "RELGRAPH_BUCKET_COLORS",
    # TICKET-0059 (BRIEF-0059-f commit 2): the NPC agent launcher's twelve
    # functions plus its tree renderer, converged onto
    # frontend/src/creation/NpcAgent.svelte + npcAgent.svelte.js
    # (LocationTree.svelte's first consumer), plus the four launcher-only
    # state variables that became fully unreferenced once those functions
    # were gone.
    "npcAgentReset", "npcAgentCheckOpenBatch", "npcAgentRenderLauncher",
    "_npcAgentTreeHtml", "npcAgentSelectRoot", "npcAgentPreviewRoot",
    "npcAgentAddLine", "npcAgentRemoveLine", "npcAgentEditLine",
    "_npcAgentLineTotal", "_npcAgentLineRowHtml", "_npcAgentPaintLauncher",
    "npcAgentLaunch",
    "npcAgentLocations", "npcAgentSelectedRoot", "npcAgentGroupBrief",
    "npcAgentLines",
    # TICKET-0059 (BRIEF-0059-f commit 3): the NPC agent's run-loop/review
    # functions, converged onto the same island, plus the review-only state
    # variables that became fully unreferenced once those functions were
    # gone. npcAgentOpen/npcAgentToggle are the two survivors (chrome) and
    # stay off this list.
    "_npcAgentRefreshRows", "npcAgentRunOne", "npcAgentRunLoop",
    "npcAgentPause", "npcAgentRetryRun", "npcAgentLoadBatch",
    "_npcAgentGroupRows", "_npcAgentRowHtml", "_npcAgentGroupHtml",
    "npcAgentEditField", "npcAgentToggleReject", "npcAgentCommit",
    "npcAgentAbandon", "npcAgentGenerateLinks", "_npcAgentPaintReview",
    "npcAgentOpenBatchId", "npcAgentPreview", "npcAgentBatch",
    "npcAgentRows", "npcAgentLoopRunning", "npcAgentFailedRun",
    "npcAgentCommitResult", "npcAgentLinkHandoffMsg",
    # TICKET-0059 (BRIEF-0059-g commit 1): the link agent launcher's nine
    # functions, converged onto frontend/src/creation/LinkAgent.svelte +
    # linkAgent.svelte.js (LocationTree.svelte's second consumer), plus the
    # three launcher-only state variables that became fully unreferenced
    # once those functions were gone.
    "linkAgentReset", "linkAgentCheckOpenBatch", "linkAgentRenderLauncher",
    "_linkAgentIsChecked", "_linkAgentTreeHtml", "linkAgentToggleLocation",
    "_linkAgentPaintLauncher", "linkAgentPreviewRoster", "linkAgentLaunch",
    "linkAgentLocations", "linkAgentCheckedRoots", "linkAgentPreview",
    # TICKET-0059 (BRIEF-0059-g commit 2): the link agent's run-loop/review/
    # coherence functions, converged onto the same island, plus the
    # review-only state variables that became fully unreferenced once those
    # functions were gone. linkAgentOpen/linkAgentToggle are the two
    # survivors (chrome) and stay off this list.
    "linkAgentRunLoop", "linkAgentPause", "linkAgentRetry",
    "linkAgentLoadBatch", "_linkAgentNpcName", "_linkAgentGroupRows",
    "_linkAgentRelationRowHtml", "_linkAgentKnowledgeRowHtml",
    "_linkAgentNoLinksRowHtml", "_linkAgentPairGroupHtml",
    "linkAgentEditField", "linkAgentToggleReject", "_linkAgentFindingHtml",
    "linkAgentRunCoherence", "linkAgentApplyFinding", "linkAgentCommit",
    "_linkAgentPaintReview",
    "linkAgentOpenBatchId", "linkAgentBatch", "linkAgentRows",
    "linkAgentNpcNames", "linkAgentLoopRunning", "linkAgentFailedPair",
    "linkAgentCommitResult",
    # TICKET-0059 (BRIEF-0059-h commit 2): the Artefacts tab, converged onto
    # frontend/src/creation/Artefacts.svelte.
    "loadCreationArtefacts", "CREATION_ARTEFACTS_NOTICE",
    # TICKET-0059 (BRIEF-0059-h commit 3): the Compétences tab, converged
    # onto frontend/src/creation/Competences.svelte + competences.svelte.js.
    "_competencesWorldReset", "competencesGenerateDraft",
    "_competencesDomainOptions", "competencesRenderDraft",
    "competencesDiscardDraftRow", "competencesAcceptDraftRow",
    "competencesAddManualRow", "competencesLoadList",
    "_competencesRenderTable", "competencesSaveRow",
    "competencesDeleteOpen", "competencesDeleteConfirm",
    "competencesDraft", "COMPETENCES_DOMAINS",
    # TICKET-0059 (BRIEF-0059-h commit 4): the Registre tab, converged onto
    # frontend/src/creation/Registre.svelte.
    "_registreWorldReset", "_registrePopulateEntityFilter",
    "authorAddLedgerEntry", "registreToggleAddForm", "loadRegistre",
    "_registreRenderTable", "_registreEntitiesLoaded",
    # TICKET-0059 (BRIEF-0059-i commit 1): the Prompts tab's world-reset/
    # edit-state-reset pair, its Ollama model fetch, its list loader, its
    # usage-card renderer, its detail selector, its model-selector renderer
    # and change handler, its read-only body renderer, and the parked
    # D-0050 conversation-window panel's load/render/patch trio, converged
    # onto frontend/src/creation/Prompts.svelte + prompts.svelte.js +
    # ConversationWindowConfig.svelte. _promptsRenderList/_promptsRenderDetail/
    # _promptsExtractTokens/_promptsHighlightTokens stay off this list for
    # now -- each still has a live (if unreachable) caller among the
    # not-yet-ported edit-mode/history functions; commit 2/3 add them once
    # those callers are gone too.
    "_promptsResetEditState", "_promptsWorldReset", "_promptsFetchOllamaModels",
    "promptsLoadList", "_promptsRenderUsageCard", "promptsSelectDetail",
    "cwLoadConfig", "_cwRenderConfig", "cwPatchField",
    "_promptsRenderModelSelector", "promptsChangeModel", "_promptsRenderReadBodies",
    # TICKET-0059 (BRIEF-0059-i commit 2): the shared X1 dirty guard, the
    # edit-mode body renderer and its enter/cancel/input handlers, the
    # token-scan (also the drift-detection reader, now that
    # _promptsRenderDetail's own copy is already gone), and save, converged
    # onto the same Prompts.svelte + prompts.svelte.js. _promptsRefreshDetail
    # stays off this list -- promptsRestoreVersion (commit 3) still calls
    # it; commit 3 adds it once that caller is gone too.
    # _promptsRenderList/_promptsRenderDetail/_promptsHighlightTokens are
    # unaffected by this commit and stay off for the same reason as commit
    # 1's note above.
    "_promptsConfirmDiscard", "_promptsRenderEditBodies", "promptsEnterEditMode",
    "promptsCancelEdit", "promptsEditInput", "_promptsUpdateEditHint",
    "promptsSaveEdit", "_promptsExtractTokens",
    # TICKET-0059 (BRIEF-0059-i commit 3, final): the history section
    # (render, toggle, load, list-render, version-select, version-detail-
    # render, restore) and the assembled-preview functions (panel render,
    # entity-selector populate, run), converged onto the same
    # Prompts.svelte + prompts.svelte.js. Also closing out the deferred
    # names from commits 1/2, now that their last remaining (unreachable)
    # callers are gone too: _promptsRefreshDetail (promptsRestoreVersion),
    # _promptsRenderList/_promptsRenderDetail/_promptsHighlightTokens
    # (the history/preview functions removed in this same commit). Every
    # promptsX/cwX module-level `let` is gone as well -- the whole Prompts
    # module in index.html is retired.
    "_promptsRenderHistorySection", "promptsToggleHistory", "_promptsLoadHistory",
    "_promptsRenderHistoryList", "promptsSelectHistoryVersion",
    "_promptsRenderHistoryVersionDetail", "promptsRestoreVersion",
    "_promptsRenderPreviewPanel", "_promptsPopulateEntitySelectors",
    "promptsRunAssembledPreview", "_promptsRefreshDetail", "_promptsRenderList",
    "_promptsRenderDetail", "_promptsHighlightTokens",
    # TICKET-0059 (BRIEF-0059-j): intrigues -- list fetch, bespoke sheet
    # (fetch, detail rendering, step/link row renderers, status/step/link
    # mutations, commit 1) and create panel + AI draft assistant (commit 2),
    # converged onto frontend/src/creation/Intrigues.svelte +
    # intrigues.svelte.js. _intriguesTabEnterReset stays off this list --
    # it is chrome-callback shaped (state.onTabEnter) and survives
    # unmigrated, the same way its twin _evenementsTabEnterReset did.
    "loadAgendasList", "renderAgendaSheet", "_intriguesRenderStep",
    "_intriguesRenderLinkedGoal", "_intriguesRefreshSelection",
    "intriguesSetAgendaStatus", "intriguesDetachLink", "intriguesStepStatus",
    "intriguesAgendas", "_intriguesPopulateOwnerSelect",
    "intriguesRenderCreatePanel", "intriguesGenerateDraft", "intriguesSubmitCreate",
]
GONE_WORD = ["GRAPH_W", "GRAPH_H", "NODE_R", "DRAG_THRESHOLD"]
# TICKET-0058 (BRIEF-0058-c): the vendored engine itself must be gone from
# index.html in ANY context (comments included) — case-insensitive, since
# GONE_PLAIN is case-sensitive and a "Cytoscape"/"CYTOSCAPE" stray mention
# would otherwise slip through it.
GONE_CASE_INSENSITIVE = ["cytoscape"]

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
GRAPH_IMPLS_DECL_RE = re.compile(r"GRAPH_IMPLS\s*=\s*Object\.freeze\(")
BLOCK_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
RETIRED_RECORD_RE = re.compile(r"^([^|]+)\|([^|]+)\|([^|]+)$")

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
        f"{counts['specs']} graph spec(s) validated, "
        f"{counts['live']} live graph impl(s), {counts['retired']} retired graph impl(s) proven absent"
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
    for token in GONE_CASE_INSENSITIVE:
        if token in html.lower():
            fail(f"rule1: retired token {token!r} still present in index.html (case-insensitive)")
    return len(GONE_PLAIN) + len(GONE_WORD) + len(GONE_CASE_INSENSITIVE)


def _rule2_no_svg(html: str) -> bool:
    count = len(SVG_TAG_RE.findall(html))
    if count:
        fail(f"rule2: {count} '<svg' occurrence(s) remain in index.html — the legacy document must emit no SVG graph")
        return False
    return True


def _graph_impls_body(text: str) -> str | None:
    """Return the raw source text inside `GRAPH_IMPLS = Object.freeze({ ... })`,
    brace-balanced, or None if the declaration itself cannot be located."""
    m = GRAPH_IMPLS_DECL_RE.search(text)
    if not m:
        return None
    start = text.find("{", m.end() - 1)
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start + 1:i]
    return None


def _parse_registry() -> dict[str, dict[str, str]] | None:
    """None only on a structural failure: the file is missing, the
    GRAPH_IMPLS declaration cannot be found, or the declaration's body is
    non-empty yet nothing in it parses into the expected entry shape (BRIEF
    -0058-b's "declares something unreadable" case). A body that is empty
    (whitespace/comments only) is NOT a failure — it returns {}, because an
    empty registry is exactly what full convergence looks like; rule 5b is
    what proves that emptiness is earned, not accidental."""
    if not REGISTRY_FILE.is_file():
        fail(f"{REGISTRY_FILE} does not exist")
        return None
    text = REGISTRY_FILE.read_text(encoding="utf-8")
    body = _graph_impls_body(text)
    if body is None:
        fail(f"{REGISTRY_FILE}: GRAPH_IMPLS = Object.freeze({{...}}) declaration not found")
        return None
    entries: dict[str, dict[str, str]] = {}
    for key, engine, locus, fn_prefix, retired_by in ENTRY_RE.findall(text):
        entries[key] = {"engine": engine, "locus": locus, "fnPrefix": fn_prefix, "retiredBy": retired_by}
    if not entries and BLOCK_COMMENT_RE.sub("", body).strip():
        fail(f"{REGISTRY_FILE}: GRAPH_IMPLS body is non-empty but no entry parsed into the expected shape")
        return None
    return entries


def _load_baseline() -> set[str] | None:
    if not BASELINE_FILE.is_file():
        fail(f"{BASELINE_FILE} does not exist")
        return None
    baseline_keys = {
        line.strip() for line in BASELINE_FILE.read_text(encoding="utf-8").splitlines() if line.strip()
    }
    if not baseline_keys:
        fail(f"{BASELINE_FILE} is empty")
        return None
    return baseline_keys


def _rule3_shrink(keys: set[str], baseline_keys: set[str]) -> bool:
    ok = True
    for key in sorted(keys):
        if key not in baseline_keys:
            fail(f"graph impl {key!r} is not in the baseline — the registry may only SHRINK (TICKET-0057)")
            ok = False
    return ok


def _parse_retired() -> dict[str, tuple[str, str]] | None:
    """Every well-formed, locus-existing record in graph_impls.retired, keyed
    by its retired key. None only if the file itself is missing — the
    append-only ledger must always exist once any convergence has happened.
    A malformed line or a record naming a locus file that no longer exists
    is a per-record FAILURE (recorded via fail()), not a structural abort:
    other records still get checked."""
    if not RETIRED_FILE.is_file():
        fail(f"{RETIRED_FILE} does not exist")
        return None
    records: dict[str, tuple[str, str]] = {}
    for raw_line in RETIRED_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        m = RETIRED_RECORD_RE.match(line)
        if not m:
            fail(f"{RETIRED_FILE}: malformed record {raw_line!r} — expected <key>|<fnPrefix>|<locus>")
            continue
        key, fn_prefix, locus_rel = (part.strip() for part in m.groups())
        locus = ROOT / locus_rel
        if not locus.is_file():
            fail(f"{RETIRED_FILE}: record {key!r} names locus {locus_rel!r} which does not exist")
            continue
        records[key] = (fn_prefix, locus_rel)
    return records


def _rule5b_retired_absent(retired_keys: set[str], records: dict[str, tuple[str, str]]) -> int:
    count = 0
    for key in sorted(retired_keys):
        if key not in records:
            fail(f"retired graph impl {key!r} is not proven absent — no record in {RETIRED_FILE.name}")
            continue
        fn_prefix, locus_rel = records[key]
        text = (ROOT / locus_rel).read_text(encoding="utf-8")
        if fn_prefix in text:
            fail(f"retired graph impl {key!r}: prefix {fn_prefix!r} still present in {locus_rel!r} — "
                 "a converged implementation kept 'just in case'")
            continue
        count += 1
    return count


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


def _top_level_keys(body: str) -> set[str]:
    """Keys immediately inside `body`, never descending into a nested
    object/array/call — an `extraEdges` arrow function's own object
    literals (id/entity_a_id/...) must not count as contract keys. Block
    comments are stripped first: prose like "connection links: trim+..."
    would otherwise false-positive as a key at depth 0."""
    body = BLOCK_COMMENT_RE.sub("", body)
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


def _rule9_closed_vocab_locus(text: str, locus: Path) -> int:
    allowed = {"consumer", "mountId", "extraEdges"}
    count = 0
    for m in GRAPH_SPEC_RE.finditer(text):
        start = m.end() - 1
        depth = 0
        end = None
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end is None:
            fail(f"rule9: a 'graph: {{' spec in {locus} has unbalanced braces")
            continue
        body = text[start + 1:end]
        extra = _top_level_keys(body) - allowed
        if extra:
            fail(f"rule9: graph spec in {locus} sets non-contract key(s) {sorted(extra)} — closed "
                 f"vocabulary is {sorted(allowed)}")
            continue
        count += 1
    return count


def _rule9_closed_vocab(html: str) -> int:
    # BRIEF-0058-i: collect from index.html (batch's spec, still legacy) AND
    # frontend/src/creation/ (region's spec, moved onto Region.svelte) —
    # zero collected across BOTH loci is the failure, not zero in either one.
    count = _rule9_closed_vocab_locus(html, INDEX_HTML)
    if FRONTEND_SRC.is_dir():
        for path in sorted(FRONTEND_SRC.rglob("*")):
            if not path.is_file() or path == INDEX_HTML:
                continue
            text = path.read_text(encoding="utf-8")
            count += _rule9_closed_vocab_locus(text, path)
    if count == 0:
        fail("rule9: zero 'graph: {...}' specs collected across index.html and frontend/src/creation/ "
             "— a rule that passes on nothing is the flaw this fixes")
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
    baseline_keys: set[str] | None = None
    shrink_ok = False
    retired_by_count = 0
    locus_count = 0
    confinement_ok = False
    retired_proven_count = 0
    if entries is not None:
        baseline_keys = _load_baseline()
    if entries is not None and baseline_keys is not None:
        shrink_ok = _rule3_shrink(set(entries.keys()), baseline_keys)
        retired_by_count = _rule4_retired_by(entries)
        locus_count = _rule5_live_locus(entries)
        confinement_ok = _rule6_engine_confinement(html, entries)

        retired_keys = baseline_keys - set(entries.keys())
        retired_records = _parse_retired()
        if retired_records is not None:
            retired_proven_count = _rule5b_retired_absent(retired_keys, retired_records)
            if not entries and retired_proven_count == 0:
                fail(
                    "rule5b: zero live graph impl(s) and zero retired graph impl(s) proven absent — "
                    "nothing was ever registered, so nothing is proven converged"
                )

    primitive_ok = _rule7_no_fetch_write()
    css_ok = _rule8_no_scoped_css()
    spec_count = _rule9_closed_vocab(html)

    if (
        FAILURES
        or entries is None
        or baseline_keys is None
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
            "registry": retired_by_count,
            "loci": locus_count,
            "specs": spec_count,
            "live": len(entries),
            "retired": retired_proven_count,
        }
    )


if __name__ == "__main__":
    main()
