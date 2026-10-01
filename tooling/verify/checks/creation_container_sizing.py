"""G1 check: every single-container Création tab sizes its container
(TICKET-0099, BRIEF-0099-a).

`.app-view` (shared.css) is a `display:flex; flex-direction:column;
overflow:hidden` column. A tab container with no rule of its own takes
its content's height, so once the content outgrows the window it is
clipped and nothing scrolls -- the Compétences tab lost its system form
and its catalogue this way at three systems, and Registre and Sujets
carried the same latent defect. `shell_height_chain.py` holds the chain
down to the shell only; this check holds its last link, per tab.

Same idiom as shell_height_chain.py: module-level FAILURES, fail(),
_report_and_exit(counts), ROOT via parents[3], stdlib only, no DB, no
subprocess. Vacuous-proof: a missing file, a registry that parses to zero
entries, or zero single-container entries is a FAILURE.

  1. `frontend/src/creation/tabs.js` holds an `export const CREATION_TABS`
     literal; every top-level entry's `containers: [...]` parses to string
     ids. An entry with no parseable `containers` list is a FAILURE.
  2. For every entry whose `containers` list holds EXACTLY ONE id X,
     `frontend/public/creation.css` (comments stripped) holds a rule whose
     selector is exactly `#X` and whose body declares both `flex: 1` and
     `min-height: 0`. A missing rule, or a rule missing either
     declaration, is a FAILURE naming the entry and the id.

Entries with two or more containers (today: `lieux`, whose second
container is a panel stacked under the editor area) are not examined:
which of their containers takes the remaining height is that entry's own
layout decision, not a property of the tab. They are counted in the PASS
line so the exclusion is visible, never silent.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TABS_FILE = ROOT / "frontend" / "src" / "creation" / "tabs.js"
CREATION_CSS = ROOT / "frontend" / "public" / "creation.css"

CSS_COMMENT_RE = re.compile(r"/\*.*?\*/", re.DOTALL)
CSS_RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}")
CONTAINERS_RE = re.compile(r"\bcontainers\s*:\s*\[([^\]]*)\]")
ID_RE = re.compile(r"""['"]([^'"]+)['"]""")
FLEX_ONE_RE = re.compile(r"(^|[;\s])flex\s*:\s*1\s*(;|$)")
MIN_HEIGHT_ZERO_RE = re.compile(r"(^|[;\s])min-height\s*:\s*0\s*(;|$)")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(counts: dict | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: creation_container_sizing — {counts['single']} single-container "
        f"entr(y/ies) size their container (flex: 1; min-height: 0); "
        f"{counts['multi']} multi-container entr(y/ies) not examined"
    )
    sys.exit(0)


def _braced_block(text: str, start_pattern: str) -> str:
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


def _top_level_entries(registry_src: str) -> list[tuple[str, str]]:
    """(key, entry source) for every top-level entry, walked brace by brace
    so a nested object never passes for a sibling entry."""
    inner = registry_src[1:-1]
    entries = []
    key_re = re.compile(r"(\w+)\s*:\s*\{")
    idx, n = 0, len(inner)
    while idx < n:
        m = key_re.search(inner, idx)
        if not m:
            break
        brace_start = inner.find("{", m.end() - 1)
        depth, end = 0, -1
        for i in range(brace_start, n):
            if inner[i] == "{":
                depth += 1
            elif inner[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        if end == -1:
            fail(f"{TABS_FILE}: CREATION_TABS entry {m.group(1)!r} has no balanced closing brace")
            break
        entries.append((m.group(1), inner[brace_start:end + 1]))
        idx = end + 1
    return entries


def _css_rules() -> dict[str, str]:
    text = CSS_COMMENT_RE.sub("", CREATION_CSS.read_text(encoding="utf-8"))
    rules: dict[str, str] = {}
    for selector, body in CSS_RULE_RE.findall(text):
        rules[selector.strip()] = body
    return rules


def main() -> None:
    if not TABS_FILE.is_file():
        fail(f"{TABS_FILE} does not exist")
        _report_and_exit()
    if not CREATION_CSS.is_file():
        fail(f"{CREATION_CSS} does not exist")
        _report_and_exit()

    registry_src = _braced_block(TABS_FILE.read_text(encoding="utf-8"), r"export const CREATION_TABS\s*=\s*\{")
    if not registry_src:
        fail(f"{TABS_FILE}: 'export const CREATION_TABS = {{' literal not found")
        _report_and_exit()

    entries = _top_level_entries(registry_src)
    if not entries:
        fail(f"{TABS_FILE}: CREATION_TABS parsed to zero entries")
        _report_and_exit()

    rules = _css_rules()
    single = multi = 0
    for key, entry_src in entries:
        m = CONTAINERS_RE.search(entry_src)
        ids = ID_RE.findall(m.group(1)) if m else []
        if not ids:
            fail(f"CREATION_TABS.{key}: no parseable 'containers: [...]' list")
            continue
        if len(ids) > 1:
            multi += 1
            continue
        single += 1
        container = ids[0]
        body = rules.get(f"#{container}")
        if body is None:
            fail(f"CREATION_TABS.{key}: {CREATION_CSS.name} has no '#{container}' rule — "
                 "the container takes its content's height and nothing scrolls")
            continue
        if not FLEX_ONE_RE.search(body):
            fail(f"CREATION_TABS.{key}: '#{container}' does not declare 'flex: 1'")
        if not MIN_HEIGHT_ZERO_RE.search(body):
            fail(f"CREATION_TABS.{key}: '#{container}' does not declare 'min-height: 0'")

    if single == 0:
        fail("zero single-container CREATION_TABS entries collected — the scan proved nothing")
    _report_and_exit({"single": single, "multi": multi})


if __name__ == "__main__":
    main()
