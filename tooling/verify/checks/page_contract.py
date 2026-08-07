"""G1 check for TICKET-0005 (BRIEF-0005-a/b/c) — Création page-contract
structural gate. Exit 0 on pass, 1 on failure; prints one line per failure.

TICKET-0058/BRIEF-0058-k: under A1 every target this check greps used to
live in index.html.

Re-anchored (TICKET-0059, BRIEF-0059-l commit 1, D1): the CREATION_TABS
registry, the generic dispatcher (showCreationSubTab/_creationActivateTab)
and the runtime-tab factory (buildRuntimeCreationTabs/creationInit) all
moved to frontend/src/creation/tabs.js; the tab bar moved to
frontend/src/creation/Creation.svelte, where it is a SINGLE reactive
`{#each}` over CREATION_TABS for both static and runtime entries alike —
there is no longer a separate "hand-authored static button" vs "factory
-inserted button" distinction to police, so rule 6 (below) is re-expressed
as "no literal id=\"ctab-<slug>\" HTML string outside the templated each
block" rather than "no #ctab-<slug> outside TAB_KEYS in static markup".
Everything else keeps its original assertion, re-targeted onto the new
file.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
INDEX_HTML = ROOT / "src" / "world_engine" / "cockpit" / "index.html"
CREATION_SRC = ROOT / "frontend" / "src" / "creation"
TABS_JS = CREATION_SRC / "tabs.js"
CREATION_SVELTE = CREATION_SRC / "Creation.svelte"
REGISTRE_SVELTE = CREATION_SRC / "Registre.svelte"

TAB_KEYS = [
    "npc", "pj", "lieux", "factions", "objets",
    "competences", "region", "constructeur", "artefacts", "registre", "intrigues", "evenements", "queue", "prompts",
]


def _braced_block(text: str, start_pattern: str) -> str:
    """Return the full `{ ... }` block whose opening brace follows the first
    match of start_pattern, matching braces to find the end. Empty string if
    the pattern or a balanced close isn't found."""
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


def _registry_keys(registry_src: str) -> list[str]:
    """Every top-level CREATION_TABS key, in source order — walks entry by
    balanced-brace entry so a nested key never gets mistaken for a sibling."""
    keys = []
    idx = 0
    n = len(registry_src)
    key_re = re.compile(r"(\w+)\s*:\s*\{")
    while idx < n:
        m = key_re.search(registry_src, idx)
        if not m:
            break
        keys.append(m.group(1))
        brace_start = registry_src.find("{", m.end() - 1)
        depth = 0
        end = brace_start
        for i in range(brace_start, n):
            if registry_src[i] == "{":
                depth += 1
            elif registry_src[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break
        idx = end + 1
    return keys


def _has_nonempty_islands(entry_src: str) -> bool:
    """True if this entry declares a non-empty `islands: [...]` list."""
    m = re.search(r"islands\s*:\s*\[", entry_src)
    if not m:
        return False
    block = _bracket_block(entry_src, m.end() - 1)
    return bool(block[1:-1].strip())


def main() -> int:
    tabs_js = TABS_JS.read_text(encoding="utf-8") if TABS_JS.is_file() else ""
    creation_svelte = CREATION_SVELTE.read_text(encoding="utf-8") if CREATION_SVELTE.is_file() else ""
    html = INDEX_HTML.read_text(encoding="utf-8") if INDEX_HTML.is_file() else ""
    failures = []

    if not tabs_js:
        failures.append(f"{TABS_JS} does not exist or is empty")
    if not creation_svelte:
        failures.append(f"{CREATION_SVELTE} does not exist or is empty")

    registry_src = _braced_block(tabs_js, r"export const CREATION_TABS\s*=\s*\{") if tabs_js else ""
    if not registry_src:
        failures.append(f"CREATION_TABS registry literal not found in {TABS_JS}")
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

    dispatcher_src = _braced_block(tabs_js, r"export function showCreationSubTab\(tab\)\s*")
    if not dispatcher_src:
        failures.append(f"showCreationSubTab(tab) function body not found in {TABS_JS}")
    else:
        for key in TAB_KEYS:
            if re.search(rf"""['"]{key}['"]""", dispatcher_src):
                failures.append(
                    f"showCreationSubTab body contains the tab-id literal '{key}' "
                    "— all per-tab variation must live in CREATION_TABS data"
                )

    activate_src = _braced_block(tabs_js, r"function _creationActivateTab\(\)\s*")
    if not activate_src:
        failures.append(f"_creationActivateTab() function body not found in {TABS_JS}")
    else:
        for key in TAB_KEYS:
            if re.search(rf"""['"]{key}['"]""", activate_src):
                failures.append(
                    f"_creationActivateTab body contains the tab-id literal '{key}' "
                    "— on_demand handling must read slot data only (BRIEF-0023-a)"
                )

    # TICKET-0046/BRIEF-0046-d (E1): runtime Creation tabs may ONLY exist via
    # the single boot/refresh factory — mechanism-only, never a live-type
    # enumeration (no-DB doctrine holds).
    factory_src = _braced_block(tabs_js, r"export function buildRuntimeCreationTabs\([^)]*\)\s*")
    if not factory_src:
        failures.append(f"buildRuntimeCreationTabs() function body not found in {TABS_JS}")

    init_src = _braced_block(tabs_js, r"export async function creationInit\(\)\s*")
    if not init_src:
        failures.append(f"creationInit() function body not found in {TABS_JS}")
    elif "buildRuntimeCreationTabs(" not in init_src:
        failures.append(
            "creationInit() does not call buildRuntimeCreationTabs() — the "
            "factory must run on every Création boot (BRIEF-0046-d)"
        )

    # BRIEF-0046-d E1, re-expressed for the reactive tab bar (BRIEF-0059-l):
    # Creation.svelte renders EVERY tab button (static and runtime alike)
    # through one `{#each}` over CREATION_TABS — there is no longer a
    # "static markup" surface a runtime tab could leak into outside the
    # factory, since there is no hand-authored button at all. The residual
    # risk this rule polices is a literal id="ctab-<slug>" string sitting
    # OUTSIDE that each block (e.g. a stray hardcoded button); every match
    # found must be the dynamic `id={'ctab-' + key}` expression, never a
    # quoted literal.
    for m in re.finditer(r"""id=["']ctab-([a-zA-Z0-9_-]+)["']""", creation_svelte):
        slug = m.group(1)
        failures.append(
            f"Creation.svelte hand-authors a literal id=\"ctab-{slug}\" — every tab "
            "button must come from the CREATION_TABS {#each}, never a static id "
            "attribute (BRIEF-0046-d E1)"
        )
    if "{#each" not in creation_svelte or "ctab-" not in creation_svelte:
        failures.append(
            "Creation.svelte does not render the tab bar via a {#each} over "
            "CREATION_TABS keyed onto 'ctab-' ids"
        )

    # TICKET-0023/BRIEF-0023-a: on-demand slot contract (F1) — the entry
    # contract comment documents `display`, and any slot named 'graph' (the
    # Lieux reader now, the NPC reader once BRIEF-0023-b lands) declares it.
    contract_comment_m = re.search(
        r"// CREATION_TABS entry contract.*?export const CREATION_TABS", tabs_js, re.S
    )
    if not contract_comment_m or "display" not in contract_comment_m.group(0) \
            or "on_demand" not in contract_comment_m.group(0):
        failures.append(
            "CREATION_TABS entry-contract comment does not document the "
            f"'display' slot field (BRIEF-0023-a F1) in {TABS_JS}"
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

    if "currentCreationSubTab === 'pj'" in html or "currentCreationSubTab === 'pj'" in tabs_js:
        failures.append(
            "\"currentCreationSubTab === 'pj'\" still present — PJ must have no "
            "hardcoded tab-name branch outside the registry (BRIEF-0005-b)"
        )

    for identifier in ("pjCreateOpen", "pjCreateNew"):
        if re.search(rf"\b{identifier}\b", html) or re.search(rf"\b{identifier}\b", tabs_js):
            failures.append(
                f"'{identifier}' still present — PJ's parallel create machinery "
                "must be fully removed (BRIEF-0005-b)"
            )

    # "Ajouter une compétence" lives in CREATION_TABS.competences'
    # primaryAction label (tabs.js) now, not index.html — scan the whole
    # frontend/src/creation/ tree (not just tabs.js) so an in-body control
    # added to Competences.svelte would still be caught as a duplicate.
    occurrences = 0
    if CREATION_SRC.is_dir():
        for path in CREATION_SRC.rglob("*"):
            if path.is_file() and path.suffix in (".js", ".svelte"):
                occurrences += path.read_text(encoding="utf-8").count("Ajouter une compétence")
    if occurrences == 0:
        failures.append(
            f"'Ajouter une compétence' not found anywhere under {CREATION_SRC} — expected "
            "once, in the registry's primaryAction label"
        )
    elif occurrences > 1:
        failures.append(
            f"'Ajouter une compétence' appears {occurrences} times under {CREATION_SRC} — "
            "expected exactly once (the registry's primaryAction label); an in-body "
            "control must not exist (BRIEF-0005-c)"
        )

    # TICKET-0059 (BRIEF-0059-h commit 4): the add-form moved off static
    # markup onto Registre.svelte's own {#if addFormOpen} — collapsed by
    # construction (the node doesn't exist until toggled) is a STRONGER
    # form of BRIEF-0005-c's "collapsed by default" than the legacy
    # `hidden` attribute ever was; the assertion re-anchors onto the
    # component's own initial state instead of index.html markup.
    registre_svelte = REGISTRE_SVELTE.read_text(encoding="utf-8") if REGISTRE_SVELTE.is_file() else ""
    if "addFormOpen = $state(false)" not in registre_svelte:
        failures.append(
            f"{REGISTRE_SVELTE} does not initialize addFormOpen to false — "
            "the add-form must be collapsed by default (BRIEF-0005-c)"
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

    if "creation-intrigues" in html or "creation-intrigues" in creation_svelte:
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

    migrated_count = 0
    legacy_count = 0
    if registry_src:
        for key in _registry_keys(registry_src):
            entry_src = _entry_block(registry_src, key)
            if _has_nonempty_islands(entry_src):
                migrated_count += 1
            else:
                legacy_count += 1

    print(
        "PASS: page_contract — CREATION_TABS registry, generic dispatcher, "
        "no duplicate Lieux create button, PJ on the entity archetype, "
        "standard shell + primaryAction on every entry; "
        f"{migrated_count} of {migrated_count + legacy_count} CREATION_TABS "
        f"entries have migrated at least one mount point, {legacy_count} "
        "still render entirely from legacy code"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
