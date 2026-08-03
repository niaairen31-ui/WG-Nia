"""G1 check: the Creation island-mount seam (TICKET-0058, BRIEF-0058-d,
amended by BRIEF-0058-e).

Bloc A1 keeps `CREATION_TABS`, the dispatcher and the tab bar legacy for
this ticket and the next; migrated surfaces become Svelte islands mounted
into the legacy containers they already own. Without a lock, "mount into
the legacy container" is a convention a second brief can quietly break --
a second `svelteMount` call site, a legacy loader left wired beside a
mounted island (RECON-0058-a M5's destruction mode), or a primary-action
button silently pointing at nothing. This check is what makes the seam
constructible only one way.

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
  4. Every declared `containerId` exists as an element id in index.html.
  5. Many-to-many: every registry key is declared by AT LEAST ONE
     `islands: [{ key, containerId }]` entry in index.html's CREATION_TABS
     (with a matching containerId), and every such declaration in
     index.html resolves to a registry key. Zero collected on either side
     is a failure.
  6. `svelteMount`/`mount(` from `svelte` is called on a legacy-document
     target in exactly one file: `frontend/src/creation/mount.js`
     (`frontend/src/graph/mount.js` excepted by name, and only that
     file) -- the no-second-mechanism rule.
  7. The migrated surface's legacy functions are gone: for every registry
     entry, EVERY prefix in its `retiredPrefixes` matches zero
     `function <prefix>...(` declarations in index.html, in any context
     (comments included).
  8. `island:slot` and `island:action` are each dispatched only from
     index.html and listened for only in `frontend/src/creation/mount.js`.
  9. Every CREATION_TABS entry declaring a non-empty `islands` list also
     declares `loader: null` and `state.onWorldSwitch: null`. Zero entries
     collected is a failure.
  10. The `island:slot` dispatch inside `_creationActivateTab` is
      unconditional. A real nesting-depth proof needs a JS parser this
      checker doesn't have, so this uses the WEAKER form the brief allows:
      no identifier matching `loaded|mounted|_once` occurs anywhere in
      `_creationActivateTab`'s own body -- the function is small and
      single-purpose (page_contract.py already forbids tab-id branching in
      it), so a stray one of those identifiers appearing anywhere in it
      would already be a smuggled-back first-time gate, not noise from an
      unrelated concern.
  11. Pairing, not partition: for every CREATION_TABS entry whose
      `primaryAction` is not null, `primaryAction.handler` and
      `createPanel` must be on the SAME side -- either
      `primaryAction.handler` calls `_islandPrimaryAction(` (a direct
      function reference fails that side) AND `createPanel` is `null` or
      absent, with the component `export function primaryAction`; OR
      `primaryAction.handler` does NOT call `_islandPrimaryAction(` AND
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
        f"{counts['events']} event channel(s) confined, "
        f"{counts['primary_actions']} island primaryAction(s) wired"
    )
    sys.exit(0)


def _braced_block(html: str, start_pattern: str) -> str:
    """Return the full `{ ... }` block whose opening brace follows the
    first match of start_pattern, brace-balanced. Empty string if the
    pattern or a balanced close isn't found."""
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
            # Lookahead only -- the opening '{' itself is left for the next
            # loop iteration's own depth += 1 branch to consume, otherwise
            # the very next nested 'key: {' (e.g. an entry's own 'state: {')
            # would be mis-seen at depth 0 too and picked up as a second
            # top-level key.
            m = re.match(r"\s*(\w+)\s*:\s*(?=\{)", inner[i:])
            if m:
                keys.append(m.group(1))
                i += m.end()
                continue
        i += 1
    return keys


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


def _rule4_container_exists(html: str, entries: dict[str, dict[str, object]]) -> bool:
    ok = True
    for key, entry in entries.items():
        container_id = entry["containerId"]
        if not re.search(rf"""id=["']{re.escape(container_id)}["']""", html):
            fail(f"creation island {key!r}: containerId {container_id!r} has no matching element id in {INDEX_HTML}")
            ok = False
    return ok


def _rule5_many_to_many(html: str, entries: dict[str, dict[str, object]]) -> bool:
    tabs_src = _braced_block(html, r"const CREATION_TABS\s*=\s*\{")
    if not tabs_src:
        fail(f"{INDEX_HTML}: CREATION_TABS registry literal not found")
        return False
    decls = ISLAND_DECL_RE.findall(tabs_src)
    if not decls:
        fail(f"{INDEX_HTML}: zero 'islands: [{{ key, containerId }}]' declarations found in CREATION_TABS")
        return False
    ok = True
    declared_keys: set[str] = set()
    for key, container_id in decls:
        declared_keys.add(key)
        entry = entries.get(key)
        if not entry:
            fail(f"index.html declares island key {key!r} with no matching entry in {REGISTRY_FILE}")
            ok = False
            continue
        if entry["containerId"] != container_id:
            fail(
                f"index.html declares island key {key!r} with containerId {container_id!r} "
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


def _rule8_event_confinement() -> int:
    if not FRONTEND_SRC.is_dir():
        fail(f"{FRONTEND_SRC} is not a directory")
        return 0
    if not INDEX_HTML.is_file():
        fail(f"{INDEX_HTML} does not exist")
        return 0
    html = INDEX_HTML.read_text(encoding="utf-8")
    files = [p for p in FRONTEND_SRC.rglob("*") if p.is_file()]
    if not files:
        fail(f"{FRONTEND_SRC} contains no files -- empty scan is a failure")
        return 0

    confined = 0
    for event in ("island:slot", "island:action"):
        dispatch_re = re.compile(rf"dispatchEvent\(new CustomEvent\('{re.escape(event)}'")
        listen_re = re.compile(rf"addEventListener\('{re.escape(event)}'")
        ok = True

        if not dispatch_re.search(html):
            fail(f"{INDEX_HTML}: zero '{event}' dispatch site(s) -- expected at least one")
            ok = False

        for path in files:
            if dispatch_re.search(path.read_text(encoding="utf-8")):
                fail(f"{path}: dispatches '{event}' -- must be dispatched only from {INDEX_HTML}")
                ok = False

        if listen_re.search(html):
            fail(f"{INDEX_HTML}: listens for '{event}' -- must be listened for only in {MOUNT_FILE}")
            ok = False

        mount_listens = 0
        for path in files:
            matches = len(listen_re.findall(path.read_text(encoding="utf-8")))
            if not matches:
                continue
            if path == MOUNT_FILE:
                mount_listens += matches
            else:
                fail(f"{path}: listens for '{event}' -- must be listened for only in {MOUNT_FILE}")
                ok = False
        if mount_listens == 0:
            fail(f"{MOUNT_FILE}: zero '{event}' listener(s) -- expected at least one")
            ok = False

        if ok:
            confined += 1
    return confined


def _rule9_state_nulls(html: str, entries: dict[str, dict[str, object]]) -> bool:
    tabs_src = _braced_block(html, r"const CREATION_TABS\s*=\s*\{")
    if not tabs_src:
        fail(f"{INDEX_HTML}: CREATION_TABS registry literal not found")
        return False
    if not ISLAND_DECL_RE.search(tabs_src):
        fail("rule9: zero island-declaring CREATION_TABS entries collected -- a rule that passes on nothing is the flaw this fixes")
        return False
    # Walk every top-level CREATION_TABS entry, checking any whose own
    # 'islands' array is non-empty (registry KEYS don't map 1:1 to entry
    # NAMES any more under the many-to-many amendment).
    ok = True
    checked = 0
    for entry_name in _top_level_keys(tabs_src):
        entry_src = _entry_block(tabs_src, entry_name)
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


def _rule10_unconditional_dispatch(html: str) -> bool:
    activate_body = _braced_function(html, "_creationActivateTab")
    if not activate_body:
        fail(f"{INDEX_HTML}: _creationActivateTab() function body not found")
        return False
    # BRIEF-0058-e: the dispatch itself lives in creationRefreshList() so
    # the sidebar's manual refresh button can re-run it too; the proof
    # this check makes is that _creationActivateTab calls that function
    # unconditionally, and that function's own body is where the
    # unconditional 'island:slot' dispatch must live.
    if "creationRefreshList(" not in activate_body:
        fail(f"{INDEX_HTML}: _creationActivateTab() does not call creationRefreshList()")
        return False
    hit = DISQUALIFYING_IDENT_RE.search(activate_body)
    if hit:
        fail(f"{INDEX_HTML}: _creationActivateTab() contains {hit.group(0)!r} -- the list-refresh "
             "call must be unconditional, never behind a first-time/loaded gate")
        return False

    refresh_body = _braced_function(html, "creationRefreshList")
    if not refresh_body:
        fail(f"{INDEX_HTML}: creationRefreshList() function body not found")
        return False
    if "island:slot" not in refresh_body:
        fail(f"{INDEX_HTML}: creationRefreshList() does not dispatch 'island:slot'")
        return False
    hit = DISQUALIFYING_IDENT_RE.search(refresh_body)
    if hit:
        fail(f"{INDEX_HTML}: creationRefreshList() contains {hit.group(0)!r} -- the 'island:slot' "
             "dispatch must be unconditional, never behind a first-time/loaded gate")
        return False
    return True


def _rule11_pairing(html: str, entries: dict[str, dict[str, object]]) -> int:
    tabs_src = _braced_block(html, r"const CREATION_TABS\s*=\s*\{")
    if not tabs_src:
        fail(f"{INDEX_HTML}: CREATION_TABS registry literal not found")
        return 0
    count = 0
    for entry_name in _top_level_keys(tabs_src):
        entry_src = _entry_block(tabs_src, entry_name)
        pa_src = _braced_block(entry_src, r"primaryAction\s*:\s*\{")
        if not pa_src:
            if re.search(r"\bprimaryAction\s*:\s*null\b", entry_src):
                continue
            fail(f"CREATION_TABS.{entry_name}: 'primaryAction' is neither null nor an object literal")
            continue

        is_island_routed = "_islandPrimaryAction(" in pa_src
        has_create_panel_field = re.search(r"\bcreatePanel\s*:", entry_src) is not None
        create_panel_null_src = re.search(r"\bcreatePanel\s*:\s*null\b", entry_src)
        create_panel_is_null_or_absent = (not has_create_panel_field) or bool(create_panel_null_src)

        if is_island_routed and not create_panel_is_null_or_absent:
            fail(
                f"CREATION_TABS.{entry_name}: primaryAction routes through _islandPrimaryAction "
                "but createPanel is neither null nor absent — mixed pair (list migrated, sheet not)"
            )
            continue
        if not is_island_routed and create_panel_is_null_or_absent and has_create_panel_field:
            fail(
                f"CREATION_TABS.{entry_name}: createPanel is null but primaryAction is not routed "
                "through _islandPrimaryAction — mixed pair"
            )
            continue

        if is_island_routed:
            key_m = re.search(r"""_islandPrimaryAction\(\s*['"]([^'"]+)['"]\s*\)""", pa_src)
            if not key_m:
                fail(f"CREATION_TABS.{entry_name}: primaryAction.handler calls _islandPrimaryAction( "
                     "with no literal key argument — cannot verify its component")
                continue
            key = key_m.group(1)
            entry = entries.get(key)
            if not entry:
                fail(f"CREATION_TABS.{entry_name}: _islandPrimaryAction({key!r}) has no matching registry entry")
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
    if not INDEX_HTML.is_file():
        fail(f"{INDEX_HTML} does not exist")
        _report_and_exit()
        return
    html = INDEX_HTML.read_text(encoding="utf-8")
    if not html.strip():
        fail(f"{INDEX_HTML} is empty")
        _report_and_exit()
        return

    entries = _parse_registry()
    if entries is None:
        _report_and_exit()
        return

    shape_count = _rule2_shape(entries)
    component_ok = _rule3_component_exists(entries)
    container_ok = _rule4_container_exists(html, entries)
    bijection_ok = _rule5_many_to_many(html, entries)
    mechanism_ok = _rule6_single_mechanism()
    retired_count = _rule7_retired_gone(html, entries)
    event_count = _rule8_event_confinement()
    state_ok = _rule9_state_nulls(html, entries)
    dispatch_ok = _rule10_unconditional_dispatch(html)
    primary_action_count = _rule11_pairing(html, entries)

    if (
        FAILURES
        or shape_count != len(entries)
        or not component_ok
        or not container_ok
        or not bijection_ok
        or not mechanism_ok
        or retired_count != len(entries)
        or event_count != 2
        or not state_ok
        or not dispatch_ok
    ):
        _report_and_exit()
        return

    _report_and_exit(
        {
            "islands": len(entries),
            "retired": retired_count,
            "events": event_count,
            "primary_actions": primary_action_count,
        }
    )


if __name__ == "__main__":
    main()
