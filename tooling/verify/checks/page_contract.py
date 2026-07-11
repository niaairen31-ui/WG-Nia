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
    "competences", "region", "artefacts", "registre", "intrigues", "evenements", "queue", "prompts",
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


def _entry_block(registry_src: str, key: str) -> str:
    """Return one CREATION_TABS entry's own `{ ... }` block by its tab key."""
    return _braced_block(registry_src, rf"(?:^|[{{,\s]){key}\s*:\s*\{{")


def _bracket_block(text: str, start_idx: int, open_ch: str = "[", close_ch: str = "]") -> str:
    """Return the full bracketed block starting at text[start_idx] (which
    must be open_ch), matching brackets to find the balanced close."""
    depth = 0
    for i in range(start_idx, len(text)):
        if text[i] == open_ch:
            depth += 1
        elif text[i] == close_ch:
            depth -= 1
            if depth == 0:
                return text[start_idx:i + 1]
    return ""


def _slot_objects(entry_src: str) -> list[str]:
    """Return each individual `{ ... }` slot object in an entry's `slots`
    array, brace-balanced (robust to single- or multi-line formatting)."""
    m = re.search(r"slots\s*:\s*\[", entry_src)
    if not m:
        return []
    array_src = _bracket_block(entry_src, m.end() - 1)
    objs = []
    depth = 0
    start = None
    for i, ch in enumerate(array_src):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                objs.append(array_src[start:i + 1])
                start = None
    return objs


def _slot_by_container(entry_src: str, container_id: str) -> str:
    """Return the slot object declaring this containerId, or '' if none."""
    for obj in _slot_objects(entry_src):
        if re.search(rf"""containerId\s*:\s*['"]{re.escape(container_id)}['"]""", obj):
            return obj
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
                continue
            entry_src = _entry_block(registry_src, key)
            if not re.search(r"\bprimaryAction\s*:", entry_src):
                failures.append(
                    f"CREATION_TABS.{key} has no 'primaryAction' key "
                    "(required — value may be null, BRIEF-0005-c)"
                )

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

    activate_src = _braced_block(html, r"function _creationActivateTab\(\)\s*")
    if not activate_src:
        failures.append("_creationActivateTab() function body not found in index.html")
    else:
        for key in TAB_KEYS:
            if re.search(rf"""['"]{key}['"]""", activate_src):
                failures.append(
                    f"_creationActivateTab body contains the tab-id literal '{key}' "
                    "— on_demand handling must read slot data only (BRIEF-0023-a)"
                )

    # TICKET-0023/BRIEF-0023-a: on-demand slot contract (F1) — the entry
    # contract comment documents `display`, and any slot named 'graph' (the
    # Lieux reader now, the NPC reader once BRIEF-0023-b lands) declares it.
    contract_comment_m = re.search(
        r"// CREATION_TABS entry contract.*?const CREATION_TABS", html, re.S
    )
    if not contract_comment_m or "display" not in contract_comment_m.group(0) \
            or "on_demand" not in contract_comment_m.group(0):
        failures.append(
            "CREATION_TABS entry-contract comment does not document the "
            "'display' slot field (BRIEF-0023-a F1)"
        )

    if registry_src:
        lieux_src = _entry_block(registry_src, "lieux")
        lieux_graph_slot = _slot_by_container(lieux_src, "creation-lieux-graph") if lieux_src else ""
        if not lieux_graph_slot:
            failures.append("CREATION_TABS.lieux has no slot with containerId 'creation-lieux-graph'")
        elif not re.search(r"""display\s*:\s*['"]on_demand['"]""", lieux_graph_slot):
            failures.append(
                "CREATION_TABS.lieux's graph slot does not declare display: 'on_demand' (BRIEF-0023-a)"
            )

        # npc's relation-graph slot only exists from BRIEF-0023-b onward —
        # this assertion is inert until then and starts enforcing once the
        # slot is declared, with no further edit to this check required.
        npc_src = _entry_block(registry_src, "npc")
        npc_graph_slot = _slot_by_container(npc_src, "creation-npc-relgraph") if npc_src else ""
        if npc_graph_slot and not re.search(r"""display\s*:\s*['"]on_demand['"]""", npc_graph_slot):
            failures.append(
                "CREATION_TABS.npc's relation-graph slot does not declare display: 'on_demand' (BRIEF-0023-b)"
            )

    if "Ajouter un lieu" in html:
        failures.append(
            "'Ajouter un lieu' string still present — Lieux must create only "
            "through the standard + Nouveau control (H1)"
        )

    if "currentCreationSubTab === 'pj'" in html:
        failures.append(
            "\"currentCreationSubTab === 'pj'\" still present — PJ must have no "
            "hardcoded tab-name branch outside the registry (BRIEF-0005-b)"
        )

    for identifier in ("pjCreateOpen", "pjCreateNew"):
        if re.search(rf"\b{identifier}\b", html):
            failures.append(
                f"'{identifier}' still present — PJ's parallel create machinery "
                "must be fully removed (BRIEF-0005-b)"
            )

    occurrences = html.count("Ajouter une compétence")
    if occurrences == 0:
        failures.append("'Ajouter une compétence' not found anywhere — expected once, in the registry's primaryAction label")
    elif occurrences > 1:
        failures.append(
            f"'Ajouter une compétence' appears {occurrences} times — expected exactly once "
            "(the registry's primaryAction label); an in-body control must not exist (BRIEF-0005-c)"
        )

    if 'id="registre-add-form" hidden' not in html:
        failures.append(
            "#registre-add-form is not collapsed by default in static markup "
            "(expected the 'hidden' attribute — BRIEF-0005-c)"
        )

    # TICKET-0021/BRIEF-0021-a: Intrigues migrated onto the entity archetype's
    # shared list+detail shell via the sheetRenderer seam — no bespoke
    # container of its own anymore.
    if registry_src:
        intrigues_src = _entry_block(registry_src, "intrigues")
        if intrigues_src:
            if not re.search(r"""archetype\s*:\s*['"]entity['"]""", intrigues_src):
                failures.append(
                    "CREATION_TABS.intrigues is not archetype: 'entity' (BRIEF-0021-a)"
                )
            if not re.search(r"""containers\s*:\s*\[\s*['"]creation-editor-area['"]\s*\]""", intrigues_src):
                failures.append(
                    "CREATION_TABS.intrigues does not have "
                    "containers: ['creation-editor-area'] (BRIEF-0021-a)"
                )

    if "creation-intrigues" in html:
        failures.append(
            "element id 'creation-intrigues' still present — Intrigues must render "
            "only through the shared creation-editor-area shell (BRIEF-0021-a)"
        )

    # TICKET-0022/BRIEF-0022-a: Événements — third non-entity reader of the
    # entity archetype's shared list+detail shell via the sheetRenderer seam.
    if registry_src:
        evenements_src = _entry_block(registry_src, "evenements")
        if evenements_src:
            if not re.search(r"""archetype\s*:\s*['"]entity['"]""", evenements_src):
                failures.append(
                    "CREATION_TABS.evenements is not archetype: 'entity' (BRIEF-0022-a)"
                )
            if not re.search(r"""containers\s*:\s*\[\s*['"]creation-editor-area['"]\s*\]""", evenements_src):
                failures.append(
                    "CREATION_TABS.evenements does not have "
                    "containers: ['creation-editor-area'] (BRIEF-0022-a)"
                )

    if failures:
        for f in failures:
            print(f"FAIL: {f}")
        return 1

    print(
        "PASS: page_contract — CREATION_TABS registry, generic dispatcher, "
        "no duplicate Lieux create button, PJ on the entity archetype, "
        "standard shell + primaryAction on every entry"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
