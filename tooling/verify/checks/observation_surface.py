"""G1 check for TICKET-0051, BRIEF-0051-f — the Observation cockpit surface.

Static/AST checks only (index.html text + the observation routes module's
AST) — no DB, no server. `json_ui_boundary.py` is invoked as a subprocess for
Rule 5 rather than reimplemented here.

Rules:
  1. index.html declares the Observation mode-tab and its view-switch
     function, satisfying the mini-RECON's mode-tab contract (show/hide the
     three top-level views, toggle the three mode-tab buttons).
  2. No TAB_KEYS entry (page_contract.py) and no CREATION_TABS entry named
     'observation' — the surface did not leak into the Creation registry.
  3. The transcript renderer references all four outcome values; 'degraded'
     and 'silence' resolve to DIFFERENT CSS classes (class bodies compared,
     not just literal presence of both strings).
  4. The run detail renderer references the pinned parameter fields and the
     template pinning fields — the L columns have a reader.
  5. json_ui_boundary still passes.
  6. No route in cockpit/routes/observation.py writes an observation_* row
     directly (no Observation* identifier, no db.add(...) call at all) —
     every write there goes through observation_runner.py.
  7. Vacuous-proof guard: fewer than 4 outcome literals or zero renderer
     functions found is a FAILURE, not a pass.
"""
from __future__ import annotations

import ast
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
INDEX_HTML = SRC / "world_engine" / "cockpit" / "index.html"
ROUTES_FILE = SRC / "world_engine" / "cockpit" / "routes" / "observation.py"
PAGE_CONTRACT = ROOT / "tooling" / "verify" / "checks" / "page_contract.py"

FAILURES: list[str] = []
_outcome_literals_found: set[str] = set()
_renderer_functions_found = 0


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _braced_block(html: str, start_pattern: str) -> str:
    """Brace-balanced block following the first match of start_pattern —
    mirrors page_contract.py's helper of the same name."""
    m = re.search(start_pattern, html)
    if not m:
        return ""
    brace_start = html.find("{", m.end() - 1)
    if brace_start == -1:
        return ""
    depth = 0
    for i in range(brace_start, len(html)):
        if html[i] == "{":
            depth += 1
        elif html[i] == "}":
            depth -= 1
            if depth == 0:
                return html[brace_start:i + 1]
    return ""


# ── Rule 1 ────────────────────────────────────────────────────────────────


def check_rule1_mode_tab(html: str) -> None:
    global _renderer_functions_found
    if 'id="mode-tab-observation"' not in html:
        fail("Rule 1: no #mode-tab-observation button in index.html")
    if 'onclick="showObservationView()"' not in html:
        fail("Rule 1: #mode-tab-observation does not call showObservationView()")

    body = _braced_block(html, r"function showObservationView\(\)\s*")
    if not body:
        fail("Rule 1: showObservationView() function body not found")
        return
    _renderer_functions_found += 1
    for needle in (
        "play-view", "creation-view", "observation-view",
        "mode-tab-play", "mode-tab-creation", "mode-tab-observation",
    ):
        if needle not in body:
            fail(f"Rule 1: showObservationView() does not reference {needle!r} — contract incomplete")


# ── Rule 2 ────────────────────────────────────────────────────────────────


def check_rule2_no_creation_leak(html: str) -> None:
    tab_keys_src = PAGE_CONTRACT.read_text(encoding="utf-8")
    m = re.search(r"TAB_KEYS\s*=\s*\[(.*?)\]", tab_keys_src, re.S)
    if not m:
        fail("Rule 2: could not find TAB_KEYS in page_contract.py")
    elif re.search(r"""['"]observation['"]""", m.group(1)):
        fail("Rule 2: page_contract.py's TAB_KEYS includes 'observation' — must stay a mode-tab, not a Creation sub-tab")

    registry_src = _braced_block(html, r"const CREATION_TABS\s*=\s*\{")
    if not registry_src:
        fail("Rule 2: CREATION_TABS registry literal not found in index.html")
    elif re.search(r"(?:^|[{,\s])observation\s*:\s*\{", registry_src):
        fail("Rule 2: CREATION_TABS has an 'observation' entry — the surface leaked into the Creation registry")


# ── Rule 3 ────────────────────────────────────────────────────────────────


def check_rule3_outcome_distinction(html: str) -> None:
    global _renderer_functions_found
    body = _braced_block(html, r"function _obsRenderTranscript\(beats\)\s*")
    if not body:
        fail("Rule 3: _obsRenderTranscript(beats) function body not found")
        return
    _renderer_functions_found += 1

    label_block = _braced_block(html, r"OBS_OUTCOME_LABEL\s*=\s*\{")
    for literal in ("acted", "silence", "degraded", "event"):
        if f"{literal}:" in label_block or f"'{literal}'" in label_block:
            _outcome_literals_found.add(literal)
    if len(_outcome_literals_found) < 4:
        fail(f"Rule 3: expected 4 outcome literals in OBS_OUTCOME_LABEL, found {sorted(_outcome_literals_found)}")

    if "b-${esc(b.outcome)}" not in body and "b-${esc(" not in body:
        fail("Rule 3: _obsRenderTranscript does not derive its badge class from beat.outcome")

    silence_css = _braced_block(html, r"\.b-silence\s*")
    degraded_css = _braced_block(html, r"\.b-degraded\s*")
    if not silence_css or not degraded_css:
        fail("Rule 3: .b-silence or .b-degraded CSS class not found")
    elif silence_css == degraded_css:
        fail("Rule 3: .b-silence and .b-degraded resolve to the IDENTICAL class body — not visually distinct")


# ── Rule 4 ────────────────────────────────────────────────────────────────


def check_rule4_run_detail_reader(html: str) -> None:
    global _renderer_functions_found
    body = _braced_block(html, r"function _obsRenderRunDetail\(run\)\s*")
    if not body:
        fail("Rule 4: _obsRenderRunDetail(run) function body not found")
        return
    _renderer_functions_found += 1
    for needle in ("cooldown_beats", "debt_weight", "propensity_mode", "templates", "template_id", "version"):
        if needle not in body:
            fail(f"Rule 4: _obsRenderRunDetail does not reference {needle!r} — an L column has no reader")


# ── Rule 5 ────────────────────────────────────────────────────────────────


def check_rule5_json_ui_boundary() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "tooling" / "verify" / "checks" / "json_ui_boundary.py")],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        fail(f"Rule 5: json_ui_boundary failed: {(result.stdout or result.stderr).strip().splitlines()[-1:]}")


# ── Rule 6 ────────────────────────────────────────────────────────────────

_OBSERVATION_CLASSES = {
    "ObservationRun", "ObservationRunTemplate", "ObservationBeat",
    "ObservationIntent", "ObservationMutationLink",
}


def check_rule6_no_direct_write() -> None:
    tree = ast.parse(ROUTES_FILE.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in _OBSERVATION_CLASSES:
            fail(f"Rule 6: {ROUTES_FILE.name} references model identifier {node.id!r} directly at line {node.lineno}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "add":
            fail(f"Rule 6: {ROUTES_FILE.name} calls db.add(...) directly at line {node.lineno} — writes must go through the runner")


def main() -> int:
    if not INDEX_HTML.exists():
        fail(f"{INDEX_HTML} not found")
    if not ROUTES_FILE.exists():
        fail(f"{ROUTES_FILE} not found")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1

    html = INDEX_HTML.read_text(encoding="utf-8")
    check_rule1_mode_tab(html)
    check_rule2_no_creation_leak(html)
    check_rule3_outcome_distinction(html)
    check_rule4_run_detail_reader(html)
    check_rule5_json_ui_boundary()
    check_rule6_no_direct_write()

    if _renderer_functions_found < 3 or len(_outcome_literals_found) < 4:
        fail(
            f"Vacuous-proof guard: {_renderer_functions_found} renderer function(s), "
            f"{len(_outcome_literals_found)} outcome literal(s) collected"
        )

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        f"PASS: observation_surface — {_renderer_functions_found} renderer function(s) verified, "
        f"{len(_outcome_literals_found)} outcome literal(s) collected"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
