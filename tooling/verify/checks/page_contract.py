"""G1 check for TICKET-0005 (BRIEF-0005-a/b/c) — Création page-contract
structural gate. Exit 0 on pass, 1 on failure; prints one line per failure.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
INDEX_HTML = ROOT / "src" / "world_engine" / "cockpit" / "index.html"

TAB_KEYS = [
    "npc", "pj", "lieux", "factions", "objets",
    "competences", "region", "artefacts", "registre", "queue",
]


def _braced_block(html: str, start_pattern: str) -> str:
    """Return the full `{ ... }` block whose opening brace follows the first
    match of start_pattern, matching braces to find the end. Empty string if
    the pattern or a balanced close isn't found."""
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


def main() -> int:
    html = INDEX_HTML.read_text(encoding="utf-8")
    failures = []

    registry_src = _braced_block(html, r"const CREATION_TABS\s*=\s*\{")
    if not registry_src:
        failures.append("CREATION_TABS registry literal not found in index.html")
    else:
        for key in TAB_KEYS:
            if not re.search(rf"(?:^|[{{,\s]){key}\s*:\s*\{{", registry_src):
                failures.append(f"CREATION_TABS is missing an entry for '{key}'")

    dispatcher_src = _braced_block(html, r"function showCreationSubTab\(tab\)\s*")
    if not dispatcher_src:
        failures.append("showCreationSubTab(tab) function body not found in index.html")
    else:
        for key in TAB_KEYS:
            if re.search(rf"""['"]{key}['"]""", dispatcher_src):
                failures.append(
                    f"showCreationSubTab body contains the tab-id literal '{key}' "
                    "— all per-tab variation must live in CREATION_TABS data"
                )

    if "Ajouter un lieu" in html:
        failures.append(
            "'Ajouter un lieu' string still present — Lieux must create only "
            "through the standard + Nouveau control (H1)"
        )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print("PASS: page_contract — CREATION_TABS registry, generic dispatcher, no duplicate Lieux create button")
    return 0


if __name__ == "__main__":
    sys.exit(main())
