"""G1 check for TICKET-0051, BRIEF-0051-f — the Observation cockpit surface.

TICKET-0060 (BRIEF-0060-b commit 5) re-homes every rule from
`cockpit/index.html` onto the shell-native Svelte surface
(`frontend/src/observation/*`) the migration moved it to. Every assertion
below is preserved from the pre-migration version, none softened -- only
the anchor moves.

Static/text checks only (no DB, no server). `json_ui_boundary.py` is
invoked as a subprocess for Rule 5 rather than reimplemented here.

Rules:
  1. `App.svelte` mounts `<Observation active={...}>` deriving its
     visibility from the current surface, and 'observation' is absent
     from `LEGACY_MOUNTS` -- the surface is shell-native, not a legacy
     mount.
  2. No TAB_KEYS entry (page_contract.py) and no CREATION_TABS entry named
     'observation' — the surface did not leak into the Creation registry.
  3. The transcript block derives its badge class from `beat.outcome`,
     references all four outcome values in `OBS_OUTCOME_LABEL`, and
     'degraded'/'silence' resolve to DIFFERENT CSS classes in shared.css
     (class bodies compared, not just literal presence of both strings).
  4. The run-detail block references the pinned parameter fields and the
     template pinning fields — the L columns have a reader.
  5. json_ui_boundary still passes.
  6. No route in cockpit/routes/observation.py writes an observation_* row
     directly (no Observation* identifier, no db.add(...) call at all) —
     every write there goes through observation_runner.py.
  7. runBeats() (TICKET-0053) drives the multi-beat sequence client-side,
     reusing the existing /step route, carrying the in-flight
     guard/interrupt/closure-exit, never re-deriving the stop rule, and
     cockpit/routes/observation.py declares no batch-step route.
  8. No {@html} anywhere under frontend/src/observation/ -- E1 (BRIEF-0060-b)
     made scoped styles (D1) possible, and {@html} would silently break
     .r-err's coloring.
  9. Vacuous-proof guard: fewer than 4 renderer blocks, fewer than 4
     outcome literals, is a FAILURE, not a pass.
"""
from __future__ import annotations

import ast
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
OBSERVATION_DIR = ROOT / "frontend" / "src" / "observation"
OBSERVATION_COMPONENT = OBSERVATION_DIR / "Observation.svelte"
OBSERVATION_STATE_JS = OBSERVATION_DIR / "observation.svelte.js"
APP_SVELTE = ROOT / "frontend" / "src" / "App.svelte"
LEGACY_REGISTRY = ROOT / "frontend" / "src" / "legacy" / "registry.js"
ROUTES_FILE = SRC / "world_engine" / "cockpit" / "routes" / "observation.py"
PAGE_CONTRACT = ROOT / "tooling" / "verify" / "checks" / "page_contract.py"
# TICKET-0063 (BRIEF-0063-a) moved the Badges section -- .b-silence and
# .b-degraded included -- out of index.html's inline <style> into
# shared.css; TICKET-0060 (BRIEF-0060-b) then moved Observation's own
# markup out of index.html entirely, so shared.css is now the ONLY place
# Rule 3 needs to look for these two classes.
SHARED_CSS = ROOT / "frontend" / "public" / "shared.css"
CREATION_TABS_FILE = ROOT / "frontend" / "src" / "creation" / "tabs.js"

FAILURES: list[str] = []
_outcome_literals_found: set[str] = set()
_renderer_blocks_found = 0


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _braced_block(text: str, start_pattern: str) -> str:
    """Brace-balanced block following the first match of start_pattern —
    mirrors page_contract.py's helper of the same name."""
    m = re.search(start_pattern, text)
    if not m:
        return ""
    brace_start = text.find("{", m.end() - 1)
    if brace_start == -1:
        return ""
    depth = 0
    for i in range(brace_start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[brace_start:i + 1]
    return ""


def _marked_block(text: str, start_marker: str, end_marker: str) -> str:
    """Text between one literal HTML comment marker pair (Observation.svelte
    uses <!-- render:X --> ... <!-- /render:X --> to delimit each of its
    four render regions -- a Svelte template has no JS function body to
    brace-match against, so these markers are the anchor instead)."""
    start = text.find(start_marker)
    if start == -1:
        return ""
    start += len(start_marker)
    end = text.find(end_marker, start)
    if end == -1:
        return ""
    return text[start:end]


# ── Rule 1 ────────────────────────────────────────────────────────────────


def check_rule1_shell_mount() -> None:
    global _renderer_blocks_found
    if not APP_SVELTE.is_file():
        fail(f"Rule 1: {APP_SVELTE} not found")
        return
    app_text = APP_SVELTE.read_text(encoding="utf-8")
    if "import Observation from './observation/Observation.svelte'" not in app_text:
        fail("Rule 1: App.svelte does not import Observation.svelte")
    mount_match = re.search(r"<Observation\s+active=\{[^}]*\}", app_text)
    if not mount_match:
        fail("Rule 1: App.svelte does not mount <Observation active={...}>")
    else:
        _renderer_blocks_found += 1

    if not LEGACY_REGISTRY.is_file():
        fail(f"Rule 1: {LEGACY_REGISTRY} not found")
        return
    registry_text = LEGACY_REGISTRY.read_text(encoding="utf-8")
    if re.search(r"(?:^|[{,\s])observation\s*:\s*Object\.freeze\(", registry_text, re.MULTILINE):
        fail("Rule 1: LEGACY_MOUNTS still declares 'observation' — the surface must be shell-native, not a legacy mount")


# ── Rule 2 ────────────────────────────────────────────────────────────────


def check_rule2_no_creation_leak() -> None:
    tab_keys_src = PAGE_CONTRACT.read_text(encoding="utf-8")
    m = re.search(r"TAB_KEYS\s*=\s*\[(.*?)\]", tab_keys_src, re.S)
    if not m:
        fail("Rule 2: could not find TAB_KEYS in page_contract.py")
    elif re.search(r"""['"]observation['"]""", m.group(1)):
        fail("Rule 2: page_contract.py's TAB_KEYS includes 'observation' — must stay a mode-tab, not a Creation sub-tab")

    tabs_js_src = CREATION_TABS_FILE.read_text(encoding="utf-8")
    registry_src = _braced_block(tabs_js_src, r"export const CREATION_TABS\s*=\s*\{")
    if not registry_src:
        fail("Rule 2: CREATION_TABS registry literal not found in frontend/src/creation/tabs.js")
    elif re.search(r"(?:^|[{,\s])observation\s*:\s*\{", registry_src):
        fail("Rule 2: CREATION_TABS has an 'observation' entry — the surface leaked into the Creation registry")


# ── Rule 3 ────────────────────────────────────────────────────────────────


def check_rule3_outcome_distinction(component_text: str, state_js_text: str) -> None:
    global _renderer_blocks_found
    body = _marked_block(component_text, "<!-- render:transcript -->", "<!-- /render:transcript -->")
    if not body:
        fail("Rule 3: <!-- render:transcript --> block not found in Observation.svelte")
        return
    _renderer_blocks_found += 1

    label_block = _braced_block(state_js_text, r"OBS_OUTCOME_LABEL\s*=\s*Object\.freeze\(")
    for literal in ("acted", "silence", "degraded", "event"):
        if f"{literal}:" in label_block or f"'{literal}'" in label_block:
            _outcome_literals_found.add(literal)
    if len(_outcome_literals_found) < 4:
        fail(f"Rule 3: expected 4 outcome literals in OBS_OUTCOME_LABEL, found {sorted(_outcome_literals_found)}")

    if "b-{b.outcome}" not in body:
        fail("Rule 3: the transcript block does not derive its badge class from beat.outcome")

    if not SHARED_CSS.is_file():
        fail(f"Rule 3: {SHARED_CSS} not found")
        return
    css_text = SHARED_CSS.read_text(encoding="utf-8")
    silence_css = _braced_block(css_text, r"\.b-silence\s*")
    degraded_css = _braced_block(css_text, r"\.b-degraded\s*")
    if not silence_css or not degraded_css:
        fail("Rule 3: .b-silence or .b-degraded CSS class not found")
    elif silence_css == degraded_css:
        fail("Rule 3: .b-silence and .b-degraded resolve to the IDENTICAL class body — not visually distinct")


# ── Rule 4 ────────────────────────────────────────────────────────────────


def check_rule4_run_detail_reader(component_text: str) -> None:
    global _renderer_blocks_found
    body = _marked_block(component_text, "<!-- render:run-detail -->", "<!-- /render:run-detail -->")
    if not body:
        fail("Rule 4: <!-- render:run-detail --> block not found in Observation.svelte")
        return
    _renderer_blocks_found += 1
    for needle in ("cooldown_beats", "debt_weight", "propensity_mode", "templates", "template_id", "version"):
        if needle not in body:
            fail(f"Rule 4: the run-detail block does not reference {needle!r} — an L column has no reader")


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


# ── Rule 7 ────────────────────────────────────────────────────────────────


def check_rule7_sequence_client_side(state_js_text: str) -> None:
    global _renderer_blocks_found
    body = _braced_block(state_js_text, r"export async function runBeats\(\)\s*")
    if not body:
        fail("Rule 7a: runBeats() function body not found")
        return
    _renderer_blocks_found += 1

    if "/step" not in body:
        fail("Rule 7b: runBeats() does not reuse the existing /step route")

    for needle in ("sequenceRunning", "sequenceAbort", "!== 'running'"):
        if needle not in body:
            fail(f"Rule 7c: runBeats() does not reference {needle!r}")

    for forbidden in ("max_beats", "quiescence"):
        if forbidden in body:
            fail(f"Rule 7d: runBeats() re-derives the stop rule — found {forbidden!r}")

    routes_src = ROUTES_FILE.read_text(encoding="utf-8")
    if '"/steps"' in routes_src or "'/steps'" in routes_src:
        fail("Rule 7e: routes/observation.py declares a '/steps' path literal — batch route detected")
    tree = ast.parse(routes_src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for stmt in node.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    if stmt.target.id in ("count", "n", "beats"):
                        fail(f"Rule 7e: {node.name} declares a field named {stmt.target.id!r} — batch-count field detected")


# ── Rule 8 ────────────────────────────────────────────────────────────────


def check_rule8_no_at_html() -> None:
    if not OBSERVATION_DIR.is_dir():
        fail(f"Rule 8: {OBSERVATION_DIR} is not a directory")
        return
    files = sorted(p for p in OBSERVATION_DIR.rglob("*") if p.is_file())
    if not files:
        fail(f"Rule 8: vacuous scan — {OBSERVATION_DIR} contains no files")
        return
    for path in files:
        if "{@html" in path.read_text(encoding="utf-8"):
            fail(f"Rule 8: {path.relative_to(ROOT)} contains {{@html — forbidden (E1/D1)")


def main() -> int:
    if not OBSERVATION_COMPONENT.exists():
        fail(f"{OBSERVATION_COMPONENT} not found")
    if not OBSERVATION_STATE_JS.exists():
        fail(f"{OBSERVATION_STATE_JS} not found")
    if not ROUTES_FILE.exists():
        fail(f"{ROUTES_FILE} not found")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1

    component_text = OBSERVATION_COMPONENT.read_text(encoding="utf-8")
    state_js_text = OBSERVATION_STATE_JS.read_text(encoding="utf-8")

    check_rule1_shell_mount()
    check_rule2_no_creation_leak()
    check_rule3_outcome_distinction(component_text, state_js_text)
    check_rule4_run_detail_reader(component_text)
    check_rule5_json_ui_boundary()
    check_rule6_no_direct_write()
    check_rule7_sequence_client_side(state_js_text)
    check_rule8_no_at_html()

    if _renderer_blocks_found < 4 or len(_outcome_literals_found) < 4:
        fail(
            f"Vacuous-proof guard: {_renderer_blocks_found} renderer block(s), "
            f"{len(_outcome_literals_found)} outcome literal(s) collected"
        )

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        f"PASS: observation_surface — {_renderer_blocks_found} renderer function(s) verified, "
        f"{len(_outcome_literals_found)} outcome literal(s) collected"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
