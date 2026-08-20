"""G1 check: shell height chain integrity (TICKET-0065, BRIEF-0065-a).

TICKET-0059 inserted `#app` and `.shell-layout` between the shell's
full-height `html`/`body` (shared.css:11) and every surface's own
`flex:1; min-height:0` ladder. Before this ticket neither wrapper carried a
height or a flex context, so Creation's chain resolved against an
auto-height ancestor and `.conv-list` never became scrollable; Play and
Observation were unaffected only because `LegacyFrame.svelte` sized its
iframe off a second, independent `100vh` calc. This check holds "one height
authority" structurally, same FAILURES/_report_and_exit/ROOT idiom as
legacy_mount.py / import_cycle.py, stdlib only, no DB, no subprocess. Two
rules, both vacuous-proof:

  1. rule1 — zero `100vh` literals anywhere under frontend/src,
     frontend/public, frontend/index.html (comments included). An empty
     scan (zero files visited) is a FAILURE, not a pass.
  2. rule2 — the chain is declared: `frontend/src/App.svelte` contains a
     `:global(#app)` rule and a `.shell-layout` rule, each declaring
     `display: flex`, `flex-direction: column` and `min-height: 0`. A
     missing App.svelte, a missing rule, or a rule missing any of the three
     declarations is a FAILURE.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "frontend"
FRONTEND_SRC = FRONTEND / "src"
FRONTEND_PUBLIC = FRONTEND / "public"
FRONTEND_INDEX = FRONTEND / "index.html"
APP_SVELTE = FRONTEND_SRC / "App.svelte"

VH100_RE = re.compile(r"100vh")
CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
CSS_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")

REQUIRED_DECLS = ("display:\\s*flex", "flex-direction:\\s*column", "min-height:\\s*0")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(counts: dict | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: shell_height_chain — {counts['scanned']} file(s) scanned, "
        f"zero 100vh literal(s), shell chain declared on #app and .shell-layout"
    )
    sys.exit(0)


def _collect_scan_targets() -> list[Path]:
    files: list[Path] = []
    for base in (FRONTEND_SRC, FRONTEND_PUBLIC):
        if base.is_dir():
            files.extend(p for p in base.rglob("*") if p.is_file())
    if FRONTEND_INDEX.is_file():
        files.append(FRONTEND_INDEX)
    return files


def _check_no_100vh() -> int | None:
    files = _collect_scan_targets()
    if not files:
        fail("zero files scanned under frontend/src, frontend/public, frontend/index.html -- empty scan is a failure")
        return None
    ok = True
    for path in files:
        text = path.read_text(encoding="utf-8", errors="ignore")
        if VH100_RE.search(text):
            fail(f"{path}: '100vh' literal found -- the shell must own exactly one height authority")
            ok = False
    return len(files) if ok else None


def _rule_has_all_decls(body: str) -> bool:
    return all(re.search(pattern, body) for pattern in REQUIRED_DECLS)


def _check_chain_declared() -> bool:
    if not APP_SVELTE.is_file():
        fail(f"{APP_SVELTE} does not exist")
        return False
    text = CSS_COMMENT_RE.sub("", APP_SVELTE.read_text(encoding="utf-8"))

    app_body = None
    shell_body = None
    for selector, body in CSS_RULE_RE.findall(text):
        selector = selector.strip()
        if selector == ":global(#app)":
            app_body = body
        elif selector == ".shell-layout":
            shell_body = body

    ok = True
    if app_body is None:
        fail(f"{APP_SVELTE}: no ':global(#app)' rule found")
        ok = False
    elif not _rule_has_all_decls(app_body):
        fail(f"{APP_SVELTE}: ':global(#app)' rule is missing one of display:flex / flex-direction:column / min-height:0")
        ok = False

    if shell_body is None:
        fail(f"{APP_SVELTE}: no '.shell-layout' rule found")
        ok = False
    elif not _rule_has_all_decls(shell_body):
        fail(f"{APP_SVELTE}: '.shell-layout' rule is missing one of display:flex / flex-direction:column / min-height:0")
        ok = False

    return ok


def main() -> None:
    scanned = _check_no_100vh()
    chain_ok = _check_chain_declared()

    if FAILURES or scanned is None or not chain_ok:
        _report_and_exit()
        return

    _report_and_exit({"scanned": scanned})


if __name__ == "__main__":
    main()
