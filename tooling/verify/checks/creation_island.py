"""G1 check: the Creation island-mount seam (TICKET-0058, BRIEF-0058-d,
amended by BRIEF-0058-e; re-anchored by TICKET-0059, BRIEF-0059-l commit 1,
D1).

Migrated surfaces become Svelte islands mounted into containers Creation
owns. Without a lock, "mount into the owning container" is a convention a
second brief can quietly break -- a second `svelteMount` call site, a
legacy loader left wired beside a mounted island (RECON-0058-a M5's
destruction mode), or a primary-action button silently pointing at nothing.
This check is what makes the seam constructible only one way.

BRIEF-0058-e amendment: `#creation-editor-area` holds TWO mount points
migrating across two briefs (`#author-entity-list` here, `#author-main` in
-f), so a `CREATION_TABS` entry's field became a LIST --
`islands: [{ key, containerId }, ...]` -- an entry may declare several,
landing across briefs, and MULTIPLE entries may declare the SAME key (one
shared component can serve many tabs sharing one container; rule 5 is
many-to-many, not a strict bijection). The old singular `island: { key }`
field, and its "island XOR legacy, never both" partition, are WITHDRAWN --
false by design for an entry that has migrated its list but not its sheet.
Rule 11 is restated around the pairing that actually matters: an entry's
`primaryAction` and `createPanel` must be on the same side (both legacy,
or both routed through the mounted component) -- a mixed pair is the real
half-migration smell.

BRIEF-0059-l commit 1 amendment: Creation no longer lives inside the legacy
iframe, so containerId resolution (rule 4) and the CREATION_TABS registry
(rule 5, rule 9) re-anchor onto frontend/src/creation/Creation.svelte and
tabs.js respectively. The 'island:slot'/'island:action' CustomEvent bus
(rule 8) is GONE entirely -- Creation.svelte's own containers and the
mounted islands are now the same document, so mount.js exposes
`activateIsland`/`triggerPrimaryAction` as plain functions instead; rule 8
is re-expressed as confinement of THOSE two identifiers (defined once in
mount.js, invoked only from tabs.js) plus a vacuity-proof assertion that
the old event names are gone from the entire frontend tree -- a residual
'island:slot' dispatch would mean the migration only partly happened.

Same idiom as graph_primitive.py / legacy_mount.py: module-level FAILURES
list, fail(), _report_and_exit(counts), ROOT via parents[3], stdlib only,
no DB, no subprocess. Each rule vacuous-proof -- a missing file, an empty
scan or a zero-length collection is a FAILURE, never a trivially satisfied
comparison.

  1. `frontend/src/creation/registry.js` parses and is non-empty.
  2. Every entry declares a well-formed `migratedBy` (`^TICKET-\\d{4}$`),
     a non-empty `containerId`, a non-empty `component`, and a non-empty
     `retiredPrefixes` list of non-empty strings.
  3. Every declared `component` file exists under `frontend/src/creation/`.
  4. Every declared `containerId` exists as an element id in
     Creation.svelte.
  5. Many-to-many: every registry key is declared by AT LEAST ONE
     `islands: [{ key, containerId }]` entry in tabs.js's CREATION_TABS
     (with a matching containerId), and every such declaration in tabs.js
     resolves to a registry key. Zero collected on either side is a
     failure.
  6. `svelteMount`/`mount(` from `svelte` is called on a Creation-owned
     target in exactly one file: `frontend/src/creation/mount.js`
     (`frontend/src/graph/mount.js` excepted by name, and only that
     file) -- the no-second-mechanism rule.
  7. The migrated surface's legacy functions are gone: for every registry
     entry, EVERY prefix in its `retiredPrefixes` matches zero
     `function <prefix>...(` declarations in index.html, in any context
     (comments included). Still index.html -- retiredPrefixes name
     functions each island's OWN brief retired well before this ticket's
     chrome inversion; unrelated to what commit 1 moved.
  8. `activateIsland` and `triggerPrimaryAction` (frontend/src/creation/
     mount.js) are each defined exactly once, there, and invoked
     (identifier followed by `(`) only from tabs.js. The retired
     'island:slot'/'island:action' CustomEvent names appear nowhere under
     frontend/src/ -- a survivor would mean the old bus and the new direct
     calls both exist, exactly the "kept just in case" smell this whole
     file polices.
  9. Every CREATION_TABS entry (tabs.js) declaring a non-empty `islands`
     list also declares `loader: null` and `state.onWorldSwitch: null`.
     Zero entries collected is a failure.
  10. `creationRefreshList` (tabs.js) unconditionally activates every
      island its active entry declares, and `_creationActivateTab` calls
      it unconditionally. A real nesting-depth proof needs a JS parser
      this checker doesn't have, so this uses the WEAKER form the brief
      allows: no identifier matching `loaded|mounted|_once` occurs
      anywhere in either function's own body.
  11. Pairing, not partition: for every CREATION_TABS entry whose
      `primaryAction` is not null, `primaryAction.handler` and
      `createPanel` must be on the SAME side -- either
      `primaryAction.handler` calls `triggerPrimaryAction(` (a direct
      function reference fails that side) AND `createPanel` is `null` or
      absent, with the component `export function primaryAction`; OR
      `primaryAction.handler` does NOT call `triggerPrimaryAction(` AND
      `createPanel` is present and not `null`. A mixed pair -- one side
      island-routed, the other still legacy -- is a failure. Zero
      non-null-`primaryAction` entries collected is a failure.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRONTEND_SRC = ROOT / "frontend" / "src"
CREATION_SRC = FRONTEND_SRC / "creation"
REGISTRY_FILE = CREATION_SRC / "registry.js"
MOUNT_FILE = CREATION_SRC / "mount.js"
TABS_FILE = CREATION_SRC / "tabs.js"
CREATION_SVELTE_FILE = CREATION_SRC / "Creation.svelte"
GRAPH_MOUNT_FILE = FRONTEND_SRC / "graph" / "mount.js"
INDEX_HTML = ROOT / "src" / "world_engine" / "cockpit" / "index.html"

ENTRY_RE = re.compile(
    r"(\w+):\s*Object\.freeze\(\{\s*"
    r"containerId:\s*'([^']*)',\s*"
    r"component:\s*'([^']*)',\s*"
    r"migratedBy:\s*'([^']*)',\s*"
    r"retiredPrefixes:\s*\[([^\]]*)\],?\s*"
    r"\}\)",
)
MIGRATED_BY_RE = re.compile(r"^TICKET-\d{4}$")
SVELTE_MOUNT_CALL_RE = re.compile(r"\bsvelteMount\(")
DISQUALIFYING_IDENT_RE = re.compile(r"\b(loaded|mounted|_once)\b")
ISLAND_DECL_RE = re.compile(r"""\{\s*key:\s*'([^']*)'\s*,\s*containerId:\s*'([^']*)'\s*\}""")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(counts: dict | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: creation_island — {counts['islands']} island(s) registered, "
        f"{counts['retired']} retired legacy prefix set(s) confirmed gone, "
        f"{counts['events']} mount-action identifier(s) confined, "
        f"{counts['primary_actions']} island primaryAction(s) wired"
    )
    sys.exit(0)


def _braced_block(text: str, start_pattern: str) -> str:
    """Return the full `{ ... }` block whose opening brace follows the
    first match of start_pattern, brace-balanced. Empty string if the
    pattern or a balanced close isn't found."""
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
    return _braced_block(registry_src, rf"(?:^|[{{,\s]){re.escape(key)}\s*:\s*\{{")


def _top_level_keys(braced_obj_src: str) -> list[str]:
    """Identifier keys of every `key: { ... }` entry sitting directly at
    depth 1 inside a `{ ... }` object literal (brace-balanced, so a nested
    entry's own keys are never picked up)."""
    if not braced_obj_src.startswith("{"):
        return []
    inner = braced_obj_src[1:-1]
    keys: list[str] = []
    depth = 0
    i = 0
    n = len(inner)
    while i < n:
        ch = inner[i]
        if ch == "{":
            depth += 1
            i += 1
            continue
        if ch == "}":
            depth -= 1
            i += 1
            continue
        if depth == 0:
            m = re.match(r"\s*(\w+)\s*:\s*(?=\{)", inner[i:])
            if m:
                keys.append(m.group(1))
                i += m.end()
                continue
        i += 1
    return keys


def _braced_function(text: str, name: str) -> str:
    """Return `function NAME(...) { ... }`'s full source (export/async
    optional), brace-balanced."""
    m = re.search(rf"(?:export\s+)?(?:async\s+)?function {re.escape(name)}\([^)]*\)\s*\{{", text)
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


def _parse_registry() -> dict[str, dict[str, object]] | None:
    if not REGISTRY_FILE.is_file():
        fail(f"{REGISTRY_FILE} does not exist")
        return None
    text = REGISTRY_FILE.read_text(encoding="utf-8")
    entries: dict[str, dict[str, object]] = {}
    for key, container_id, component, migrated_by, prefixes_src in ENTRY_RE.findall(text):
        entries[key] = {
            "containerId": container_id,
            "component": component,
            "migratedBy": migrated_by,
            "retiredPrefixes": re.findall(r"'([^']*)'", prefixes_src),
        }
    if not entries:
        fail(f"{REGISTRY_FILE}: zero CREATION_ISLANDS entries parsed")
        return None
    return entries


def _rule2_shape(entries: dict[str, dict[str, object]]) -> int:
    count = 0
    for key, entry in entries.items():
        if not MIGRATED_BY_RE.match(entry.get("migratedBy", "")):
            fail(f"creation island {key!r}: migratedBy {entry.get('migratedBy')!r} does not match ^TICKET-\\d{{4}}$")
            continue
        if not (entry.get("containerId") and entry.get("component")):
            fail(f"creation island {key!r}: containerId/component must both be non-empty")
            continue
        prefixes = entry.get("retiredPrefixes") or []
        if not prefixes or any(not p for p in prefixes):
            fail(f"creation island {key!r}: retiredPrefixes must be a non-empty list of non-empty strings")
            continue
        count += 1
    return count


def _rule3_component_exists(entries: dict[str, dict[str, object]]) -> bool:
    ok = True
    for key, entry in entries.items():
        path = CREATION_SRC / entry["component"]
        if not path.is_file():
            fail(f"creation island {key!r}: component {entry['component']!r} does not exist under {CREATION_SRC}")
            ok = False
    return ok


def _rule4_container_exists(creation_svelte_src: str, entries: dict[str, dict[str, object]]) -> bool:
    ok = True
    for key, entry in entries.items():
        container_id = entry["containerId"]
        if not re.search(rf"""id=["']{re.escape(container_id)}["']""", creation_svelte_src):
            fail(f"creation island {key!r}: containerId {container_id!r} has no matching element id in {CREATION_SVELTE_FILE}")
            ok = False
    return ok


def _rule5_many_to_many(tabs_src: str, entries: dict[str, dict[str, object]]) -> bool:
    tabs_registry_src = _braced_block(tabs_src, r"export const CREATION_TABS\s*=\s*\{")
    if not tabs_registry_src:
        fail(f"{TABS_FILE}: CREATION_TABS registry literal not found")
        return False
    decls = ISLAND_DECL_RE.findall(tabs_registry_src)
    if not decls:
        fail(f"{TABS_FILE}: zero 'islands: [{{ key, containerId }}]' declarations found in CREATION_TABS")
        return False
    ok = True
    declared_keys: set[str] = set()
    for key, container_id in decls:
        declared_keys.add(key)
        entry = entries.get(key)
        if not entry:
            fail(f"{TABS_FILE} declares island key {key!r} with no matching entry in {REGISTRY_FILE}")
            ok = False
            continue
        if entry["containerId"] != container_id:
            fail(
                f"{TABS_FILE} declares island key {key!r} with containerId {container_id!r} "
                f"but {REGISTRY_FILE} says containerId {entry['containerId']!r} — inconsistent seam"
            )
            ok = False
    for key in sorted(set(entries.keys()) - declared_keys):
        fail(f"creation island {key!r} is registered but no CREATION_TABS entry declares it in 'islands'")
        ok = False
    return ok


def _rule6_single_mechanism() -> bool:
    if not FRONTEND_SRC.is_dir():
        fail(f"{FRONTEND_SRC} is not a directory")
        return False
    files = [p for p in FRONTEND_SRC.rglob("*") if p.is_file()]
    if not files:
        fail(f"{FRONTEND_SRC} contains no files -- empty scan is a failure")
        return False
    allowed = {MOUNT_FILE, GRAPH_MOUNT_FILE}
    ok = True
    mount_js_calls = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        calls = len(SVELTE_MOUNT_CALL_RE.findall(text))
        if calls and path not in allowed:
            fail(f"{path}: 'svelteMount(' called outside frontend/src/creation/mount.js (and graph/mount.js) -- a second mount mechanism")
            ok = False
        if path == MOUNT_FILE:
            mount_js_calls = calls
    if mount_js_calls == 0:
        fail(f"{MOUNT_FILE}: zero 'svelteMount(' calls -- the island mount seam does not exist")
        ok = False
    return ok


def _rule7_retired_gone(html: str, entries: dict[str, dict[str, object]]) -> int:
    count = 0
    for key, entry in entries.items():
        prefixes = entry["retiredPrefixes"]
        entry_ok = True
        for prefix in prefixes:
            pattern = re.compile(rf"function {re.escape(prefix)}\w*\(")
            if pattern.search(html):
                fail(f"creation island {key!r}: a 'function {prefix}...(' declaration remains in {INDEX_HTML} -- "
                     "a converged implementation kept 'just in case'")
                entry_ok = False
        if entry_ok:
            count += 1
    return count


def _rule8_mount_action_confinement(mount_src: str, tabs_src: str) -> int:
    """activateIsland/triggerPrimaryAction (mount.js) are defined exactly
    once each, and imported by exactly one file: Creation.svelte, which
    wires them into tabs.js via setMountActions (a late-bound seam, not a
    static top-level import — tabs.js cannot import mount.js directly
    without cycling back through every island component that imports a
    navigation function FROM tabs.js; see tabs.js's own header comment).
    tabs.js's actual invocation points are the internal
    _activateIslandImpl(/_triggerPrimaryActionImpl( wrappers `
    setMountActions` populates. The retired island:slot/island:action
    CustomEvent bus (dispatchEvent/addEventListener call sites specifically
    — a prose mention in a comment is not a survivor) is gone from the
    whole frontend tree."""
    if not FRONTEND_SRC.is_dir():
        fail(f"{FRONTEND_SRC} is not a directory")
        return 0
    files = [p for p in FRONTEND_SRC.rglob("*") if p.is_file()]
    if not files:
        fail(f"{FRONTEND_SRC} contains no files -- empty scan is a failure")
        return 0

    confined = 0

    # activateIsland/triggerPrimaryAction: defined once in mount.js each,
    # imported only by Creation.svelte (which wires them into tabs.js via
    # setMountActions).
    for name in ("activateIsland", "triggerPrimaryAction"):
        def_re = re.compile(rf"export function {name}\(")
        import_re = re.compile(rf"import\s*\{{[^}}]*\b{name}\b[^}}]*\}}\s*from\s*['\"]\./mount\.js['\"]")
        ok = True

        def_count = len(def_re.findall(mount_src))
        if def_count != 1:
            fail(f"{MOUNT_FILE}: 'export function {name}(' found {def_count} time(s), expected exactly 1")
            ok = False

        importers: list[Path] = []
        for path in files:
            if path == MOUNT_FILE:
                continue
            text = path.read_text(encoding="utf-8")
            if import_re.search(text):
                importers.append(path)
        if importers != [CREATION_SVELTE_FILE]:
            fail(
                f"{name} (from {MOUNT_FILE}) is imported by {[str(p) for p in importers]} -- "
                f"confined to exactly [{CREATION_SVELTE_FILE}]"
            )
            ok = False

        if ok:
            confined += 1

    # tabs.js's own late-bound invocation points exist.
    for impl_call in ("_activateIslandImpl(", "_triggerPrimaryActionImpl("):
        if impl_call not in tabs_src:
            fail(f"{TABS_FILE}: no {impl_call} call found -- the setMountActions seam is not wired to an actual invocation")
        else:
            confined += 1

    # setMountActions itself: exported once from tabs.js, called exactly
    # once, from Creation.svelte.
    if "export function setMountActions(" not in tabs_src:
        fail(f"{TABS_FILE}: no 'export function setMountActions(' found")
    else:
        confined += 1
    creation_svelte_src = CREATION_SVELTE_FILE.read_text(encoding="utf-8") if CREATION_SVELTE_FILE.is_file() else ""
    setter_call_sites = [p for p in files if "setMountActions(" in p.read_text(encoding="utf-8") and p != TABS_FILE]
    if setter_call_sites != [CREATION_SVELTE_FILE]:
        fail(f"setMountActions( is called from {[str(p) for p in setter_call_sites]} -- confined to exactly [{CREATION_SVELTE_FILE}]")
    else:
        confined += 1

    dispatch_re_tmpl = r"dispatchEvent\(\s*new\s+CustomEvent\(\s*['\"]{event}['\"]"
    listen_re_tmpl = r"addEventListener\(\s*['\"]{event}['\"]"
    for event in ("island:slot", "island:action"):
        dispatch_re = re.compile(dispatch_re_tmpl.format(event=re.escape(event)))
        listen_re = re.compile(listen_re_tmpl.format(event=re.escape(event)))
        survivors = 0
        for path in files:
            text = path.read_text(encoding="utf-8")
            if dispatch_re.search(text):
                fail(f"{path}: still dispatches '{event}' -- the old CustomEvent bus must be fully gone (BRIEF-0059-l)")
                survivors += 1
            if listen_re.search(text):
                fail(f"{path}: still listens for '{event}' -- the old CustomEvent bus must be fully gone (BRIEF-0059-l)")
                survivors += 1
        html_text = INDEX_HTML.read_text(encoding="utf-8") if INDEX_HTML.is_file() else ""
        if dispatch_re.search(html_text):
            fail(f"{INDEX_HTML}: still dispatches '{event}'")
            survivors += 1
        if listen_re.search(html_text):
            fail(f"{INDEX_HTML}: still listens for '{event}'")
            survivors += 1
        if survivors == 0:
            confined += 1

    return confined


def _rule9_state_nulls(tabs_src: str, entries: dict[str, dict[str, object]]) -> bool:
    tabs_registry_src = _braced_block(tabs_src, r"export const CREATION_TABS\s*=\s*\{")
    if not tabs_registry_src:
        fail(f"{TABS_FILE}: CREATION_TABS registry literal not found")
        return False
    if not ISLAND_DECL_RE.search(tabs_registry_src):
        fail("rule9: zero island-declaring CREATION_TABS entries collected -- a rule that passes on nothing is the flaw this fixes")
        return False
    ok = True
    checked = 0
    for entry_name in _top_level_keys(tabs_registry_src):
        entry_src = _entry_block(tabs_registry_src, entry_name)
        m = re.search(r"islands\s*:\s*\[", entry_src)
        if not m:
            continue
        array_end = entry_src.find("]", m.end())
        islands_src = entry_src[m.end():array_end] if array_end != -1 else ""
        if not ISLAND_DECL_RE.findall("[" + islands_src + "]"):
            continue
        checked += 1
        if not re.search(r"\bloader\s*:\s*null\b", entry_src):
            fail(f"CREATION_TABS.{entry_name}: declares 'islands' but not 'loader: null'")
            ok = False
        state_src = _braced_block(entry_src, r"state\s*:\s*\{")
        if not state_src or not re.search(r"\bonWorldSwitch\s*:\s*null\b", state_src):
            fail(f"CREATION_TABS.{entry_name}: declares 'islands' but not 'state.onWorldSwitch: null'")
            ok = False
    if checked == 0:
        fail("rule9: zero entries with a non-empty 'islands' array collected -- a rule that passes on nothing is the flaw this fixes")
        ok = False
    return ok


def _rule10_unconditional_dispatch(tabs_src: str) -> bool:
    activate_body = _braced_function(tabs_src, "_creationActivateTab")
    if not activate_body:
        fail(f"{TABS_FILE}: _creationActivateTab() function body not found")
        return False
    if "creationRefreshList(" not in activate_body:
        fail(f"{TABS_FILE}: _creationActivateTab() does not call creationRefreshList()")
        return False
    hit = DISQUALIFYING_IDENT_RE.search(activate_body)
    if hit:
        fail(f"{TABS_FILE}: _creationActivateTab() contains {hit.group(0)!r} -- the list-refresh "
             "call must be unconditional, never behind a first-time/loaded gate")
        return False

    refresh_body = _braced_function(tabs_src, "creationRefreshList")
    if not refresh_body:
        fail(f"{TABS_FILE}: creationRefreshList() function body not found")
        return False
    if "activateIslandFor(" not in refresh_body:
        fail(f"{TABS_FILE}: creationRefreshList() does not activate every declared island unconditionally")
        return False
    hit = DISQUALIFYING_IDENT_RE.search(refresh_body)
    if hit:
        fail(f"{TABS_FILE}: creationRefreshList() contains {hit.group(0)!r} -- island activation "
             "must be unconditional, never behind a first-time/loaded gate")
        return False
    return True


def _rule11_pairing(tabs_src: str, entries: dict[str, dict[str, object]]) -> int:
    tabs_registry_src = _braced_block(tabs_src, r"export const CREATION_TABS\s*=\s*\{")
    if not tabs_registry_src:
        fail(f"{TABS_FILE}: CREATION_TABS registry literal not found")
        return 0
    count = 0
    for entry_name in _top_level_keys(tabs_registry_src):
        entry_src = _entry_block(tabs_registry_src, entry_name)
        pa_src = _braced_block(entry_src, r"primaryAction\s*:\s*\{")
        if not pa_src:
            if re.search(r"\bprimaryAction\s*:\s*null\b", entry_src):
                continue
            fail(f"CREATION_TABS.{entry_name}: 'primaryAction' is neither null nor an object literal")
            continue

        is_island_routed = "triggerPrimaryAction(" in pa_src
        has_create_panel_field = re.search(r"\bcreatePanel\s*:", entry_src) is not None
        create_panel_null_src = re.search(r"\bcreatePanel\s*:\s*null\b", entry_src)
        create_panel_is_null_or_absent = (not has_create_panel_field) or bool(create_panel_null_src)

        if is_island_routed and not create_panel_is_null_or_absent:
            fail(
                f"CREATION_TABS.{entry_name}: primaryAction routes through triggerPrimaryAction "
                "but createPanel is neither null nor absent — mixed pair (list migrated, sheet not)"
            )
            continue
        if not is_island_routed and create_panel_is_null_or_absent and has_create_panel_field:
            fail(
                f"CREATION_TABS.{entry_name}: createPanel is null but primaryAction is not routed "
                "through triggerPrimaryAction — mixed pair"
            )
            continue

        if is_island_routed:
            key_m = re.search(r"""triggerPrimaryAction\(\s*['"]([^'"]+)['"]\s*\)""", pa_src)
            if not key_m:
                fail(f"CREATION_TABS.{entry_name}: primaryAction.handler calls triggerPrimaryAction( "
                     "with no literal key argument — cannot verify its component")
                continue
            key = key_m.group(1)
            entry = entries.get(key)
            if not entry:
                fail(f"CREATION_TABS.{entry_name}: triggerPrimaryAction({key!r}) has no matching registry entry")
                continue
            component_path = CREATION_SRC / entry["component"]
            if not component_path.is_file():
                fail(f"creation island {key!r}: component {entry['component']!r} does not exist -- cannot verify primaryAction export")
                continue
            component_text = component_path.read_text(encoding="utf-8")
            if not re.search(r"export\s+(async\s+)?function\s+primaryAction\s*\(", component_text):
                fail(f"{component_path}: does not declare 'export function primaryAction' but "
                     f"CREATION_TABS.{entry_name} wires a non-null primaryAction to it")
                continue
        count += 1
    if count == 0:
        fail("rule11: zero non-null primaryAction(s) collected -- a rule that passes on nothing is the flaw this fixes")
    return count


def main() -> None:
    if not TABS_FILE.is_file():
        fail(f"{TABS_FILE} does not exist")
        _report_and_exit()
        return
    if not CREATION_SVELTE_FILE.is_file():
        fail(f"{CREATION_SVELTE_FILE} does not exist")
        _report_and_exit()
        return
    if not MOUNT_FILE.is_file():
        fail(f"{MOUNT_FILE} does not exist")
        _report_and_exit()
        return
    tabs_src = TABS_FILE.read_text(encoding="utf-8")
    mount_src = MOUNT_FILE.read_text(encoding="utf-8")
    creation_svelte_src = CREATION_SVELTE_FILE.read_text(encoding="utf-8")
    html = INDEX_HTML.read_text(encoding="utf-8") if INDEX_HTML.is_file() else ""
    if not tabs_src.strip() or not creation_svelte_src.strip():
        fail(f"{TABS_FILE} or {CREATION_SVELTE_FILE} is empty")
        _report_and_exit()
        return

    entries = _parse_registry()
    if entries is None:
        _report_and_exit()
        return

    shape_count = _rule2_shape(entries)
    component_ok = _rule3_component_exists(entries)
    container_ok = _rule4_container_exists(creation_svelte_src, entries)
    bijection_ok = _rule5_many_to_many(tabs_src, entries)
    mechanism_ok = _rule6_single_mechanism()
    retired_count = _rule7_retired_gone(html, entries)
    action_count = _rule8_mount_action_confinement(mount_src, tabs_src)
    state_ok = _rule9_state_nulls(tabs_src, entries)
    dispatch_ok = _rule10_unconditional_dispatch(tabs_src)
    primary_action_count = _rule11_pairing(tabs_src, entries)

    if (
        FAILURES
        or shape_count != len(entries)
        or not component_ok
        or not container_ok
        or not bijection_ok
        or not mechanism_ok
        or retired_count != len(entries)
        or action_count != 8
        or not state_ok
        or not dispatch_ok
    ):
        _report_and_exit()
        return

    _report_and_exit(
        {
            "islands": len(entries),
            "retired": retired_count,
            "events": action_count,
            "primary_actions": primary_action_count,
        }
    )


if __name__ == "__main__":
    main()
