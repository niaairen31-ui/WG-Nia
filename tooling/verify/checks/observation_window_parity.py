"""G1 check for TICKET-0052 (BRIEF-0052-c) — the shared context-window
seam stays structurally single, and the observed lane actually consumes
it (H1 excluded from the MJ narration).

Briefs -a and -b built the seam and wired the observed lane onto it, but
nothing PREVENTED the divergence TICKET-0052 exists to close from
reappearing — a future change could add a second cap somewhere, or route
the MJ narration through the seam, and every check that existed before
this one would stay green. This check makes that structural rather than
disciplinary (stdlib `ast` only, no DB; the same idiom as
`import_cycle.py` and `single_canon_write.py`).

Rules:
  1. `src/world_engine/conversation_window.py` no longer exists, and no
     bare `conversation_window` identifier survives under `src/`,
     `scripts/`, or `tooling/` (the `conversation_window_config` /
     `load_conversation_window_config` / `upsert_conversation_window_config`
     substrings are permitted and excluded from the match).
  2. `split_verbatim_tail`, `line_word_count`, `summarize_older_lines`, and
     `format_summary_note` are DEFINED only in `context_window.py` — a
     second implementation anywhere else under `src/` fails.
  3. The observed lane actually consumes the seam:
     `resolve_observation_transcript` is referenced in
     `observation_runner.py`, and `observation_window.py` imports from
     `context_window`.
  4. H1, structurally: `_generate_mj_narration` contains no reference to
     `resolve_observation_transcript`, and no call site passes it a
     windowed resolution.
  5. `observation_window.py` imports no `cockpit` module.

Plus a played-lane round-trip assertion (item 2, BRIEF-0052-c): for a
fixed synthetic 12-message history, `_lines_to_played(_played_to_lines(h))
== h` — the machine-checkable form of "byte-identical played lane".

Every rule is vacuous-proof: finding zero candidates to check is a
FAILURE, not a pass (the `function_length.py`/TICKET-0038 lesson).
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
THIS_FILE = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(SRC))

_SEAM_MODULE = SRC / "world_engine" / "context_window.py"
_OBSERVATION_WINDOW_MODULE = SRC / "world_engine" / "observation_window.py"
_OBSERVATION_RUNNER_MODULE = SRC / "world_engine" / "observation_runner.py"
_OLD_MODULE = SRC / "world_engine" / "conversation_window.py"

_BARE_CONVERSATION_WINDOW_RE = re.compile(r"conversation_window(?!_config)")
# scripts/measure_conversation_window.py's OWN filename is a historical
# naming collision, not a reference to the deleted module — BRIEF-0052-a's
# Scope OUT explicitly protects this script's name ("do not rewrite it
# beyond the import path"), so its self-mentions (run instructions, its
# own temp-db filename) are exempt from Rule 1's scan.
_RULE1_EXEMPT = {ROOT / "scripts" / "measure_conversation_window.py"}
_WINDOW_PRIMITIVES = {
    "split_verbatim_tail", "line_word_count", "summarize_older_lines", "format_summary_note",
}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit() -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: observation_window_parity — single window implementation, observed "
        "lane consumes the shared seam, MJ narration structurally excluded (H1), "
        "played-lane round-trip holds"
    )
    sys.exit(0)


def _scan_roots() -> list[pathlib.Path]:
    return [SRC, ROOT / "scripts", ROOT / "tooling"]


# ── Rule 1 ────────────────────────────────────────────────────────────────


def check_rule1_old_module_gone() -> None:
    if _OLD_MODULE.exists():
        fail(f"Rule 1: {_OLD_MODULE} still exists — must be renamed to context_window.py")

    files_scanned = 0
    for root in _scan_roots():
        for path in sorted(root.rglob("*.py")):
            if path == THIS_FILE or path in _RULE1_EXEMPT:
                continue
            files_scanned += 1
            text = path.read_text(encoding="utf-8")
            for m in _BARE_CONVERSATION_WINDOW_RE.finditer(text):
                line_no = text.count("\n", 0, m.start()) + 1
                fail(f"Rule 1: bare 'conversation_window' reference at {path.relative_to(ROOT)}:{line_no}")
    if files_scanned == 0:
        fail("Rule 1: vacuous-proof — zero .py files scanned under src/, scripts/, tooling/")


# ── Rule 2 ────────────────────────────────────────────────────────────────


def check_rule2_single_implementation() -> None:
    found_in_seam: set[str] = set()
    files_scanned = 0
    for path in sorted(SRC.rglob("*.py")):
        files_scanned += 1
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            fail(f"Rule 2: {path.relative_to(ROOT)}: SyntaxError: {exc}")
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in _WINDOW_PRIMITIVES:
                if path == _SEAM_MODULE:
                    found_in_seam.add(node.name)
                else:
                    fail(
                        f"Rule 2: {node.name} defined outside context_window.py at "
                        f"{path.relative_to(ROOT)}:{node.lineno}"
                    )
    missing = _WINDOW_PRIMITIVES - found_in_seam
    if missing:
        fail(f"Rule 2: vacuous-proof — {sorted(missing)} not found defined in context_window.py at all")
    if files_scanned == 0:
        fail("Rule 2: vacuous-proof — zero .py files scanned under src/")


# ── Rule 3 ────────────────────────────────────────────────────────────────


def check_rule3_observed_lane_consumes_seam() -> None:
    runner_text = _OBSERVATION_RUNNER_MODULE.read_text(encoding="utf-8")
    if "resolve_observation_transcript" not in runner_text:
        fail("Rule 3: observation_runner.py does not reference resolve_observation_transcript")

    window_text = _OBSERVATION_WINDOW_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(window_text, filename=str(_OBSERVATION_WINDOW_MODULE))
    imports_context_window = any(
        isinstance(node, ast.ImportFrom) and node.module and node.module.endswith("context_window")
        for node in ast.walk(tree)
    )
    if not imports_context_window:
        fail("Rule 3: observation_window.py does not import from context_window")


# ── Rule 4 ────────────────────────────────────────────────────────────────


def check_rule4_h1_mj_excluded() -> None:
    text = _OBSERVATION_RUNNER_MODULE.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(_OBSERVATION_RUNNER_MODULE))

    func = next(
        (n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_generate_mj_narration"),
        None,
    )
    if func is None:
        fail("Rule 4: vacuous-proof — _generate_mj_narration function not found in observation_runner.py")
        return
    for node in ast.walk(func):
        if isinstance(node, ast.Name) and node.id == "resolve_observation_transcript":
            fail(f"Rule 4: _generate_mj_narration references resolve_observation_transcript at line {node.lineno}")

    call_found = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "_generate_mj_narration":
            call_found = True
            for arg in node.args:
                seg = ast.get_source_segment(text, arg) or ""
                if "windowed_transcripts" in seg or "resolve_observation_transcript" in seg:
                    fail(
                        f"Rule 4: _generate_mj_narration call at line {node.lineno} "
                        f"passes a windowed resolution ({seg!r})"
                    )
    if not call_found:
        fail("Rule 4: vacuous-proof — no call site of _generate_mj_narration found")


# ── Rule 5 ────────────────────────────────────────────────────────────────


def check_rule5_no_cockpit_import() -> None:
    tree = ast.parse(_OBSERVATION_WINDOW_MODULE.read_text(encoding="utf-8"), filename=str(_OBSERVATION_WINDOW_MODULE))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and "cockpit" in node.module:
            fail(f"Rule 5: observation_window.py imports from cockpit module {node.module!r} at line {node.lineno}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if "cockpit" in alias.name:
                    fail(f"Rule 5: observation_window.py imports cockpit module {alias.name!r} at line {node.lineno}")


# ── Played-lane round-trip (item 2) ─────────────────────────────────────


def check_played_roundtrip() -> None:
    from world_engine.context_window import _lines_to_played, _played_to_lines

    history = [{"role": "user" if i % 2 == 0 else "assistant", "content": f"line {i}"} for i in range(12)]
    result = _lines_to_played(_played_to_lines(history))
    if result != history:
        fail(f"Round-trip: _lines_to_played(_played_to_lines(h)) != h — got {result!r}")


def main() -> int:
    check_rule1_old_module_gone()
    check_rule2_single_implementation()
    check_rule3_observed_lane_consumes_seam()
    check_rule4_h1_mj_excluded()
    check_rule5_no_cockpit_import()
    check_played_roundtrip()
    _report_and_exit()
    return 0  # pragma: no cover — _report_and_exit always sys.exit()s


if __name__ == "__main__":
    main()
