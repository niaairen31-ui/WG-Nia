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
(As executed, the two identifiers are imported only by Creation.svelte
and wired into tabs.js through setMountActions -- see rule 8.)

TICKET-0088 amendment (BRIEF-0088-a): the registry is parsed from
comment-stripped text with free field order; every entry declares its
`origin` ('migration' or 'new') with a closed field set per origin; rule 7
covers migration entries only and fails closed on a missing legacy.html;
rules 12 and 13 close the COMPONENTS-agreement and direct-render gaps.

Same idiom as graph_primitive.py / legacy_mount.py: module-level FAILURES
list, fail(), _report_and_exit(counts), ROOT via parents[3], stdlib only,
no DB, no subprocess. Each rule vacuous-proof -- a missing file, an empty
scan or a zero-length collection is a FAILURE, never a trivially satisfied
comparison.

  1. `frontend/src/creation/registry.js` parses (comment-stripped, free
     field order) and is non-empty.
  2. Every entry declares its `origin` (`'migration'` or `'new'`) and a
     closed, per-origin field set: migration requires `containerId`,
     `component`, `migratedBy` (`^TICKET-\\d{4}$`) and a non-empty
     `retiredPrefixes` list of identifier-shaped strings; new requires
     `containerId`, `component`, `createdBy` (`^TICKET-\\d{4}$`) and
     forbids `migratedBy`/`retiredPrefixes`. Any other field name, a
     missing required field, or a malformed value is a FAILURE naming the
     entry and the field.
  3. Every declared `component` file exists under `frontend/src/creation/`.
  4. Every declared `containerId` exists as an element id in
     Creation.svelte.
  5. Many-to-many: every registry key is declared by AT LEAST ONE
     `islands: [{ key, containerId }]` entry in tabs.js's CREATION_TABS
     (with a matching containerId), and every such declaration in tabs.js
     resolves to a registry key. Zero collected on either side is a
     failure.
  6. `svelteMount(` is called on a Creation-owned target in exactly one
     file: `frontend/src/creation/mount.js` (`frontend/src/graph/mount.js`
     excepted by name, and only that file) -- the no-second-mechanism rule.
     D-0088-rule6-alias: a bare `mount(`/`hydrate(` alias imported from
     `svelte` is not itself scanned for here; reactivate if a second
     import of `mount`/`hydrate` from `'svelte'` appears anywhere under
     frontend/src besides main.js, creation/mount.js and graph/mount.js.
  7. For every MIGRATION-origin entry, EVERY prefix in its
     `retiredPrefixes` matches zero `function <prefix>...(` declarations
     in legacy.html, in any context (comments included). Zero migration
     entries is a failure; an absent legacy.html while migration entries
     exist is a failure -- their absence cannot be proven, never a silent
     pass. `new`-origin entries are never examined by this rule.
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
      D-0088-rule11-unrouted: a non-routed `primaryAction` object with no
      `createPanel` field at all passes unchecked; reactivate if
      `grep -n "createPanel" frontend/src/creation/tabs.js` ever shows a
      `primaryAction: {` site with no accompanying `createPanel` field.
  12. Every registry key has a matching `COMPONENTS` entry in mount.js,
      whose value is the default import of `'./' + component`; every
      `.svelte` default import in mount.js is used by some `COMPONENTS`
      value, and no `.svelte` import is anything but a single default
      import.
  13. `Creation.svelte` imports and mounts no component itself: no dynamic
      `import(`, no static `.svelte` import, no `mount`/`hydrate` import
      from `'svelte'` in its script; no uppercase, dotted,
      `svelte:component` or `svelte:self` tag in its markup. Every
      Creation surface mounts through mount.js's `mountIsland`/
      `activateIsland` alone.
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
LEGACY_HTML = ROOT / "src" / "world_engine" / "cockpit" / "legacy.html"

TICKET_RE = re.compile(r"^TICKET-\d{4}$")
PREFIX_IDENT_RE = re.compile(r"^[A-Za-z_$][A-Za-z0-9_$]*$")
SVELTE_MOUNT_CALL_RE = re.compile(r"\bsvelteMount\(")
DISQUALIFYING_IDENT_RE = re.compile(r"\b(loaded|mounted|_once)\b")
ISLAND_DECL_RE = re.compile(r"""\{\s*key:\s*'([^']*)'\s*,\s*containerId:\s*'([^']*)'\s*\}""")

CREATION_ISLANDS_OPEN_RE = re.compile(
    r"export\s+const\s+CREATION_ISLANDS\s*=\s*Object\s*\.\s*freeze\s*\(\s*\{"
)
TOP_ITEM_RE = re.compile(r"^\s*(\w+)\s*:\s*(.*)$", re.DOTALL)
FREEZE_VALUE_RE = re.compile(r"^\s*Object\s*\.\s*freeze\s*\(\s*\{", re.DOTALL)
FIELD_ITEM_RE = re.compile(r"^\s*(\w+)\s*:\s*(.*)$", re.DOTALL)
SINGLE_QUOTED_RE = re.compile(r"^'([^'\\\n]*)'$")

MIGRATION_ALLOWED = {"containerId", "component", "origin", "migratedBy", "retiredPrefixes"}
NEW_ALLOWED = {"containerId", "component", "origin", "createdBy"}

DEFAULT_IMPORT_RE = re.compile(r"^import\s+([A-Za-z_$][\w$]*)\s+from\s*['\"]", re.DOTALL)
SPECIFIER_RE = re.compile(r"""['"]([^'"]*)['"]$""")
SVELTE_NAMED_IMPORT_RE = re.compile(r"import\s*\{([^}]*)\}\s*from\s*['\"]svelte['\"]", re.DOTALL)
TAG_RE = re.compile(r"<([A-Za-z][A-Za-z0-9:._-]*)")
REGEX_PREV_CHARS = set("(,=:[!&|?{};+")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(counts: dict | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: creation_island — {counts['islands']} island(s) registered "
        f"({counts['migration']} migration, {counts['new']} new), "
        f"{counts['retired']} retired legacy prefix set(s) confirmed gone, "
        f"{counts['bindings']} component binding(s) agreed, "
        f"{counts['events']} mount-action identifier(s) confined, "
        f"{counts['primary_actions']} island primaryAction(s) wired, "
        f"Creation.svelte mounts no component"
    )
    sys.exit(0)


# --------------------------------------------------------------------------
# C-02: comment stripper
# --------------------------------------------------------------------------

def _strip_js_comments(text: str, fail, label: str) -> str | None:
    out: list[str] = []
    i = 0
    n = len(text)
    last_sig = ""
    while i < n:
        ch = text[i]

        if ch == "/" and i + 1 < n and text[i + 1] == "/":
            nl = text.find("\n", i)
            i = n if nl == -1 else nl
            continue

        if ch == "/" and i + 1 < n and text[i + 1] == "*":
            end = text.find("*/", i + 2)
            if end == -1:
                fail(f"{label}: unterminated /* comment")
                return None
            out.append("\n" * text.count("\n", i, end))
            i = end + 2
            continue

        if ch in ("'", '"'):
            j, closed = i + 1, False
            buf = [ch]
            while j < n:
                c = text[j]
                if c == "\\" and j + 1 < n:
                    buf.append(c); buf.append(text[j + 1]); j += 2
                    continue
                if c == "\n":
                    fail(f"{label}: unterminated {ch} string")
                    return None
                buf.append(c); j += 1
                if c == ch:
                    closed = True
                    break
            if not closed:
                fail(f"{label}: unterminated {ch} string")
                return None
            out.append("".join(buf))
            last_sig = ch
            i = j
            continue

        if ch == "`":
            j, closed = i + 1, False
            buf = ["`"]
            while j < n:
                c = text[j]
                if c == "\\" and j + 1 < n:
                    buf.append(c); buf.append(text[j + 1]); j += 2
                    continue
                buf.append(c); j += 1
                if c == "`":
                    closed = True
                    break
            if not closed:
                fail(f"{label}: unterminated ` string")
                return None
            out.append("".join(buf))
            last_sig = "`"
            i = j
            continue

        if ch == "/":
            prev = last_sig if last_sig else None
            if prev is None or prev in REGEX_PREV_CHARS:
                j, closed, in_class = i + 1, False, False
                buf = ["/"]
                while j < n:
                    c = text[j]
                    if c == "\n":
                        break
                    if c == "\\" and j + 1 < n:
                        buf.append(c); buf.append(text[j + 1]); j += 2
                        continue
                    buf.append(c)
                    if c == "[":
                        in_class = True
                    elif c == "]":
                        in_class = False
                    elif c == "/" and not in_class:
                        closed = True
                        j += 1
                        break
                    j += 1
                if not closed:
                    fail(f"{label}: unterminated regex literal")
                    return None
                out.append("".join(buf))
                last_sig = "/"
                i = j
                continue
            out.append(ch)
            last_sig = ch
            i += 1
            continue

        out.append(ch)
        if not ch.isspace():
            last_sig = ch
        i += 1

    return "".join(out)


# --------------------------------------------------------------------------
# Brace / comma helpers, string-aware
# --------------------------------------------------------------------------

def _skip_string(s: str, i: int) -> int | None:
    quote = s[i]
    j, n = i + 1, len(s)
    while j < n:
        c = s[j]
        if c == "\\" and j + 1 < n:
            j += 2
            continue
        if c == quote:
            return j + 1
        j += 1
    return None


def _match_brace(s: str, open_idx: int) -> int | None:
    depth, i, n = 0, open_idx, len(s)
    while i < n:
        c = s[i]
        if c in ("'", '"', "`"):
            nxt = _skip_string(s, i)
            if nxt is None:
                return None
            i = nxt
            continue
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return None


def _split_top_level_commas(s: str) -> list[str]:
    items: list[str] = []
    depth, start, i, n = 0, 0, 0, len(s)
    while i < n:
        c = s[i]
        if c in ("'", '"', "`"):
            nxt = _skip_string(s, i)
            if nxt is None:
                break
            i = nxt
            continue
        if c in "{[(":
            depth += 1
        elif c in "}])":
            depth -= 1
        elif c == "," and depth == 0:
            items.append(s[start:i])
            start = i + 1
        i += 1
    items.append(s[start:])
    return items


def _find_import_statements(text: str) -> list[str]:
    """Each is a line-initial `import` (leading whitespace allowed) not
    immediately followed by `(`, up to and including the first quoted
    module specifier that follows."""
    stmts = []
    for m in re.finditer(r"^[ \t]*(import\b)", text, re.MULTILINE):
        start = m.start(1)
        j = m.end(1)
        while j < len(text) and text[j] in " \t":
            j += 1
        if j < len(text) and text[j] == "(":
            continue
        qm = re.search(r"['\"]", text[start:])
        if not qm:
            continue
        q_start = start + qm.start()
        end_idx = _skip_string(text, q_start)
        if end_idx is None:
            continue
        stmts.append(text[start:end_idx])
    return stmts


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


# --------------------------------------------------------------------------
# C-01: the CREATION_ISLANDS grammar (rule 1) and per-origin shape (rule 2)
# --------------------------------------------------------------------------

def _parse_string_field_value(value: str) -> str | None:
    m = SINGLE_QUOTED_RE.match(value.strip())
    return m.group(1) if m else None


def _parse_array_field_value(value: str) -> list[str] | None:
    v = value.strip()
    if not (v.startswith("[") and v.endswith("]")):
        return None
    items = _split_top_level_commas(v[1:-1])
    result: list[str] = []
    for idx, raw in enumerate(items):
        piece = raw.strip()
        if piece == "":
            if idx == len(items) - 1:
                continue
            return None
        s = _parse_string_field_value(piece)
        if s is None:
            return None
        result.append(s)
    return result


def _rule1_parse_entry_value(key: str, value: str, fail) -> dict[str, object] | None:
    m = FREEZE_VALUE_RE.match(value)
    if not m:
        fail(f"creation island {key!r}: value is not Object.freeze({{ ... }})")
        return None
    open_idx = m.end() - 1
    close_idx = _match_brace(value, open_idx)
    if close_idx is None:
        fail(f"creation island {key!r}: Object.freeze({{ ... }}) is not brace-balanced")
        return None
    if not re.match(r"^\s*\)\s*$", value[close_idx + 1:], re.DOTALL):
        fail(f"creation island {key!r}: value is not Object.freeze({{ ... }})")
        return None

    fields: dict[str, object] = {}
    raw_fields = _split_top_level_commas(value[open_idx + 1:close_idx])
    for idx, raw in enumerate(raw_fields):
        piece = raw.strip()
        if piece == "":
            if idx == len(raw_fields) - 1:
                continue
            fail(f"creation island {key!r}: empty field between commas")
            return None
        fm = FIELD_ITEM_RE.match(piece)
        if not fm:
            fail(f"creation island {key!r}: malformed field {piece[:60]!r}")
            return None
        fname, fvalue = fm.group(1), fm.group(2).strip()
        if fname in fields:
            fail(f"creation island {key!r}: field {fname!r} repeated")
            return None
        s = _parse_string_field_value(fvalue)
        if s is not None:
            fields[fname] = s
            continue
        arr = _parse_array_field_value(fvalue)
        if arr is not None:
            fields[fname] = arr
            continue
        fail(f"creation island {key!r}: field {fname!r} value {fvalue[:60]!r} is not a valid string or string array")
        return None
    return fields


def _rule1_parse_registry(text: str, fail) -> tuple[dict[str, dict[str, object]], int]:
    """Grammar of C-01 rule 1. Returns (entries, declared_count); entries
    holds only items whose Object.freeze({ fields }) body and every field
    parsed to a valid shape -- rule 2 checks the per-origin closed field
    set on top of this. A structural fault records a FAILURE naming the
    offending item."""
    opens = list(CREATION_ISLANDS_OPEN_RE.finditer(text))
    if len(opens) != 1:
        fail(f"{REGISTRY_FILE}: expected exactly one CREATION_ISLANDS declaration, found {len(opens)}")
        return {}, 0
    open_idx = opens[0].end() - 1
    close_idx = _match_brace(text, open_idx)
    if close_idx is None:
        fail(f"{REGISTRY_FILE}: CREATION_ISLANDS literal is not brace-balanced")
        return {}, 0

    raw_items = _split_top_level_commas(text[open_idx + 1:close_idx])
    entries: dict[str, dict[str, object]] = {}
    declared = 0
    for idx, raw in enumerate(raw_items):
        item = raw.strip()
        if item == "":
            if idx == len(raw_items) - 1:
                continue
            fail(f"{REGISTRY_FILE}: empty entry between commas")
            continue
        m = TOP_ITEM_RE.match(item)
        if not m:
            fail(f"{REGISTRY_FILE}: malformed entry {item[:60]!r}")
            continue
        key, value = m.group(1), m.group(2)
        declared += 1
        if key in entries:
            fail(f"creation island {key!r}: duplicate top-level key")
            continue
        fields = _rule1_parse_entry_value(key, value, fail)
        if fields is None:
            continue
        entries[key] = fields
    if declared == 0:
        fail(f"{REGISTRY_FILE}: zero CREATION_ISLANDS entries declared")
    return entries, declared


def _rule2_shape(entries: dict[str, dict[str, object]], fail) -> dict[str, dict[str, object]]:
    """C-01's per-origin field-set table. Returns the conforming entries,
    in source order, each carrying a validated `origin`."""
    conforming: dict[str, dict[str, object]] = {}
    for key, fields in entries.items():
        origin = fields.get("origin")
        if origin not in ("migration", "new"):
            fail(f"creation island {key!r}: origin {origin!r} must be 'migration' or 'new'")
            continue
        allowed = MIGRATION_ALLOWED if origin == "migration" else NEW_ALLOWED
        ok = True
        for name in sorted(set(fields.keys()) - allowed):
            fail(f"creation island {key!r}: field {name!r} is not allowed for origin {origin!r}")
            ok = False
        for name in sorted(allowed - set(fields.keys())):
            fail(f"creation island {key!r}: missing required field {name!r} for origin {origin!r}")
            ok = False
        if not ok:
            continue
        if not (isinstance(fields.get("containerId"), str) and fields["containerId"]):
            fail(f"creation island {key!r}: containerId must be a non-empty string")
            ok = False
        if not (isinstance(fields.get("component"), str) and fields["component"]):
            fail(f"creation island {key!r}: component must be a non-empty string")
            ok = False
        if origin == "migration":
            migrated_by = fields.get("migratedBy")
            if not (isinstance(migrated_by, str) and TICKET_RE.match(migrated_by)):
                fail(f"creation island {key!r}: migratedBy {migrated_by!r} does not match ^TICKET-\\d{{4}}$")
                ok = False
            prefixes = fields.get("retiredPrefixes")
            if not isinstance(prefixes, list) or not prefixes:
                fail(f"creation island {key!r}: retiredPrefixes must be a non-empty array")
                ok = False
            else:
                for p in prefixes:
                    if not PREFIX_IDENT_RE.match(p):
                        fail(f"creation island {key!r}: retiredPrefixes item {p!r} is not identifier-shaped")
                        ok = False
        else:
            created_by = fields.get("createdBy")
            if not (isinstance(created_by, str) and TICKET_RE.match(created_by)):
                fail(f"creation island {key!r}: createdBy {created_by!r} does not match ^TICKET-\\d{{4}}$")
                ok = False
        if ok:
            conforming[key] = fields
    return conforming


# --------------------------------------------------------------------------
# Rules 3-11 (unchanged shapes, consuming the C-01 mapping)
# --------------------------------------------------------------------------

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


def _rule7_retired_gone(html: str | None, entries: dict[str, dict[str, object]], fail) -> tuple[int, int]:
    migration_entries = {k: e for k, e in entries.items() if e.get("origin") == "migration"}
    migration_count = len(migration_entries)
    if migration_count == 0:
        fail(f"{REGISTRY_FILE}: zero migration-origin entries -- the retired-prefix ledger has nothing to prove")
        return 0, 0
    if html is None:
        fail(f"{LEGACY_HTML} does not exist -- cannot prove {migration_count} migration entries' retired prefixes are gone")
        return migration_count, 0
    retired_count = 0
    for key, entry in migration_entries.items():
        entry_ok = True
        for prefix in entry["retiredPrefixes"]:
            pattern = re.compile(rf"function {re.escape(prefix)}\w*\(")
            if pattern.search(html):
                fail(f"creation island {key!r}: a 'function {prefix}...(' declaration remains in {LEGACY_HTML} -- "
                     "a converged implementation kept 'just in case'")
                entry_ok = False
        if entry_ok:
            retired_count += 1
    return migration_count, retired_count


def _rule8_mount_action_confinement(mount_src: str, tabs_src: str, html: str | None) -> int:
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

    for impl_call in ("_activateIslandImpl(", "_triggerPrimaryActionImpl("):
        if impl_call not in tabs_src:
            fail(f"{TABS_FILE}: no {impl_call} call found -- the setMountActions seam is not wired to an actual invocation")
        else:
            confined += 1

    if "export function setMountActions(" not in tabs_src:
        fail(f"{TABS_FILE}: no 'export function setMountActions(' found")
    else:
        confined += 1
    setter_call_sites = [p for p in files if "setMountActions(" in p.read_text(encoding="utf-8") and p != TABS_FILE]
    if setter_call_sites != [CREATION_SVELTE_FILE]:
        fail(f"setMountActions( is called from {[str(p) for p in setter_call_sites]} -- confined to exactly [{CREATION_SVELTE_FILE}]")
    else:
        confined += 1

    dispatch_re_tmpl = r"dispatchEvent\(\s*new\s+CustomEvent\(\s*['\"]{event}['\"]"
    listen_re_tmpl = r"addEventListener\(\s*['\"]{event}['\"]"
    html_text = html or ""
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
        if dispatch_re.search(html_text):
            fail(f"{LEGACY_HTML}: still dispatches '{event}'")
            survivors += 1
        if listen_re.search(html_text):
            fail(f"{LEGACY_HTML}: still listens for '{event}'")
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


# --------------------------------------------------------------------------
# C-03: rule 12, COMPONENTS agreement
# --------------------------------------------------------------------------

def _rule12_component_bindings(mount_src: str, entries: dict[str, dict[str, object]], fail) -> int:
    imports = _find_import_statements(mount_src)
    if not imports:
        fail(f"{MOUNT_FILE}: zero import statements found")
        return 0

    svelte_default_imports: dict[str, str] = {}
    for stmt in imports:
        spec_m = SPECIFIER_RE.search(stmt)
        if not spec_m:
            continue
        specifier = spec_m.group(1)
        if not specifier.endswith(".svelte"):
            continue
        dm = DEFAULT_IMPORT_RE.match(stmt)
        if not dm:
            fail(f"{MOUNT_FILE}: import of {specifier!r} is not a single default import")
            continue
        svelte_default_imports[dm.group(1)] = specifier

    comp_open_matches = list(re.finditer(r"const\s+COMPONENTS\s*=\s*\{", mount_src))
    if len(comp_open_matches) != 1:
        fail(f"{MOUNT_FILE}: expected exactly one 'const COMPONENTS = {{ ... }}', found {len(comp_open_matches)}")
        return 0
    comp_block = _braced_block(mount_src, r"const\s+COMPONENTS\s*=\s*\{")
    if not comp_block:
        fail(f"{MOUNT_FILE}: COMPONENTS literal is not brace-balanced")
        return 0
    components: dict[str, str] = {}
    comp_items = _split_top_level_commas(comp_block[1:-1])
    for idx, raw in enumerate(comp_items):
        piece = raw.strip()
        if piece == "":
            if idx == len(comp_items) - 1:
                continue
            fail(f"{MOUNT_FILE}: empty COMPONENTS entry")
            continue
        m = re.match(r"^(\w+)\s*:\s*([A-Za-z_$][\w$]*)$", piece)
        if not m:
            fail(f"{MOUNT_FILE}: malformed COMPONENTS entry {piece[:60]!r}")
            continue
        key, ident = m.group(1), m.group(2)
        if key in components:
            fail(f"{MOUNT_FILE}: COMPONENTS key {key!r} repeated")
            continue
        components[key] = ident
    if not components:
        fail(f"{MOUNT_FILE}: COMPONENTS is empty")
        return 0

    comp_keys = set(components.keys())
    entry_keys = set(entries.keys())
    for missing in sorted(entry_keys - comp_keys):
        fail(f"{MOUNT_FILE}: COMPONENTS is missing key {missing!r}")
    for extra in sorted(comp_keys - entry_keys):
        fail(f"{MOUNT_FILE}: COMPONENTS has extra key {extra!r} with no registry entry")

    used_identifiers: set[str] = set()
    binding_count = 0
    for key in sorted(comp_keys & entry_keys):
        ident = components[key]
        expected_specifier = "./" + entries[key]["component"]
        actual_specifier = svelte_default_imports.get(ident)
        if actual_specifier != expected_specifier:
            fail(
                f"{MOUNT_FILE}: COMPONENTS.{key} = {ident} but the default import of "
                f"{ident!r} is {actual_specifier!r}, expected {expected_specifier!r}"
            )
            continue
        used_identifiers.add(ident)
        binding_count += 1

    for ident, specifier in svelte_default_imports.items():
        if ident not in used_identifiers:
            fail(f"{MOUNT_FILE}: default import {ident!r} of {specifier!r} is never used by COMPONENTS")

    return binding_count


# --------------------------------------------------------------------------
# C-04: rule 13, Creation.svelte mounts no component
# --------------------------------------------------------------------------

def _rule13_creation_mounts_nothing(creation_src: str, fail) -> int | None:
    buf: list[str] = []
    i, n = 0, len(creation_src)
    while i < n:
        if creation_src[i:i + 4] == "<!--":
            end = creation_src.find("-->", i + 4)
            if end == -1:
                fail(f"{CREATION_SVELTE_FILE}: unterminated HTML comment")
                return None
            buf.append("\n" * creation_src.count("\n", i, end + 3))
            i = end + 3
            continue
        buf.append(creation_src[i])
        i += 1
    src = "".join(buf)

    script_blocks = re.findall(r"<script[^>]*>(.*?)</script>", src, re.DOTALL)
    if not script_blocks:
        fail(f"{CREATION_SVELTE_FILE}: zero <script> blocks found")
        return None

    ok = True
    import_count = 0
    for block in script_blocks:
        stripped = _strip_js_comments(block, fail, str(CREATION_SVELTE_FILE))
        if stripped is None:
            return None
        for _m in re.finditer(r"\bimport\s*\(", stripped):
            fail(f"{CREATION_SVELTE_FILE}: dynamic import( found -- Creation.svelte mounts no component directly")
            ok = False
        for stmt in _find_import_statements(stripped):
            import_count += 1
            spec_m = SPECIFIER_RE.search(stmt)
            specifier = spec_m.group(1) if spec_m else ""
            if specifier.endswith(".svelte"):
                fail(f"{CREATION_SVELTE_FILE}: static import of {specifier!r} -- Creation.svelte mounts no component directly")
                ok = False
            svelte_m = SVELTE_NAMED_IMPORT_RE.search(stmt)
            if svelte_m:
                for clause_name in svelte_m.group(1).split(","):
                    name = clause_name.strip().split(" as ")[0].strip()
                    if name in ("mount", "hydrate"):
                        fail(f"{CREATION_SVELTE_FILE}: imports {name!r} from 'svelte' -- Creation.svelte mounts no component directly")
                        ok = False

    if import_count == 0:
        fail(f"{CREATION_SVELTE_FILE}: zero imports found across its <script> blocks")
        return None

    markup = re.sub(r"<script[^>]*>.*?</script>", "", src, flags=re.DOTALL)
    markup = re.sub(r"<style[^>]*>.*?</style>", "", markup, flags=re.DOTALL)
    tags = TAG_RE.findall(markup)
    if not tags:
        fail(f"{CREATION_SVELTE_FILE}: zero tags found in markup")
        return None
    for tag in tags:
        if tag[0].isupper() or "." in tag or tag in ("svelte:component", "svelte:self"):
            fail(f"{CREATION_SVELTE_FILE}: markup renders <{tag}> -- Creation.svelte mounts no component directly")
            ok = False

    return len(tags) if ok else None


# --------------------------------------------------------------------------
# Self-test (K1): reads no file, runs before main() touches the filesystem.
# --------------------------------------------------------------------------

def _st_expect(cond: bool, label: str, detail: object) -> None:
    if not cond:
        fail(f"self-test: {label}: {detail!r}")


def _st_expect_fail(msgs: list[str], label: str, needle: str) -> None:
    if not any(needle in m for m in msgs):
        fail(f"self-test: {label}: expected a message naming {needle!r}, got {msgs!r}")


def _st_expect_pass(msgs: list[str], label: str) -> None:
    if msgs:
        fail(f"self-test: {label}: expected no failure, got {msgs!r}")


def _st_parse_registry(js_body: str) -> tuple[dict[str, dict[str, object]], list[str]]:
    msgs: list[str] = []
    text = f"export const CREATION_ISLANDS = Object.freeze({{\n{js_body}\n}});\n"
    stripped = _strip_js_comments(text, msgs.append, "selftest")
    if stripped is None:
        return {}, msgs
    raw, _declared = _rule1_parse_registry(stripped, msgs.append)
    return _rule2_shape(raw, msgs.append), msgs


_ST_VALID_MIXED = """
  b: Object.freeze({
    // a comment with an apostrophe's here
    migratedBy: 'TICKET-0001',
    containerId: 'c-b',
    retiredPrefixes: ['fooBar', 'bazQux'],
    origin: 'migration',
    component: 'B.svelte',
  }),
  a: Object.freeze({
    createdBy: 'TICKET-0002',
    origin: 'new',
    component: 'A.svelte',
    containerId: 'c-a',
  }),
"""


def _selftest_registry_valid() -> None:
    entries, msgs = _st_parse_registry(_ST_VALID_MIXED)
    _st_expect_pass(msgs, "registry: valid mixed origins")
    _st_expect(
        entries.get("b", {}).get("retiredPrefixes") == ["fooBar", "bazQux"],
        "registry: prefix list exact", entries.get("b"),
    )
    _st_expect(set(entries) == {"a", "b"}, "registry: both entries conform", entries)


def _selftest_registry_origin_faults() -> None:
    _, msgs = _st_parse_registry(
        "x: Object.freeze({ containerId: 'c', component: 'X.svelte', origin: 'new', retiredPrefixes: ['a'] }),"
    )
    _st_expect_fail(msgs, "registry: new with retiredPrefixes", "retiredPrefixes")

    _, msgs = _st_parse_registry(
        "x: Object.freeze({ containerId: 'c', component: 'X.svelte', origin: 'new', createdBy: 'TICKET-0003', migratedBy: 'TICKET-0004' }),"
    )
    _st_expect_fail(msgs, "registry: new with migratedBy", "migratedBy")

    _, msgs = _st_parse_registry(
        "x: Object.freeze({ containerId: 'c', component: 'X.svelte', migratedBy: 'TICKET-0001', retiredPrefixes: ['a'] }),"
    )
    _st_expect_fail(msgs, "registry: origin removed", "origin")

    _, msgs = _st_parse_registry(
        "x: Object.freeze({ containerId: 'c', component: 'X.svelte', origin: 'bogus', migratedBy: 'TICKET-0001', retiredPrefixes: ['a'] }),"
    )
    _st_expect_fail(msgs, "registry: origin unknown value", "origin")

    _, msgs = _st_parse_registry(
        "x: Object.freeze({ containerId: 'c', component: 'X.svelte', origin: 'migration', migratedBy: 'TICKET-0001', retiredPrefixes: [] }),"
    )
    _st_expect_fail(msgs, "registry: empty retiredPrefixes", "retiredPrefixes")


def _selftest_registry_field_faults() -> None:
    _, msgs = _st_parse_registry(
        'x: Object.freeze({ containerId: \'c\', component: \'X.svelte\', origin: \'migration\', migratedBy: \'TICKET-0001\', retiredPrefixes: ["a"] }),'
    )
    _st_expect_fail(msgs, "registry: double-quoted prefix", "retiredPrefixes")

    _, msgs = _st_parse_registry(
        "x: Object.freeze({ containerId: 'c', component: 'X.svelte', origin: 'migration', migratedBy: 'TICKET-0001', retiredPrefixes: ['1bad'] }),"
    )
    _st_expect_fail(msgs, "registry: prefix not identifier-shaped", "identifier-shaped")

    _, msgs = _st_parse_registry(
        "x: Object.freeze({ containerId: 'c', component: 'X.svelte', origin: 'migration', migratedBy: 'TICKET-0001', retiredPrefixes: ['a'], bogus: 'z' }),"
    )
    _st_expect_fail(msgs, "registry: unknown field", "bogus")

    _, msgs = _st_parse_registry(
        "x: Object.freeze({ containerId: 'c', component: 'X.svelte', origin: 'migration', migratedBy: someIdent, retiredPrefixes: ['a'] }),"
    )
    _st_expect_fail(msgs, "registry: value is a bare identifier", "migratedBy")

    _, msgs = _st_parse_registry(
        "x: Object.freeze({ containerId: 'c', component: 'X.svelte', origin: 'new', createdBy: 'T-88' }),"
    )
    _st_expect_fail(msgs, "registry: createdBy bad ticket format", "createdBy")


def _selftest_registry_structural_faults() -> None:
    _, msgs = _st_parse_registry(
        "dup: Object.freeze({ containerId: 'c', component: 'X.svelte', origin: 'new', createdBy: 'TICKET-0001' }),"
        "dup: Object.freeze({ containerId: 'd', component: 'Y.svelte', origin: 'new', createdBy: 'TICKET-0002' }),"
    )
    _st_expect_fail(msgs, "registry: duplicate top-level key", "duplicate")

    _, msgs = _st_parse_registry(
        "x: { containerId: 'c', component: 'X.svelte', origin: 'new', createdBy: 'TICKET-0001' },"
    )
    _st_expect_fail(msgs, "registry: not wrapped in Object.freeze", "Object.freeze")

    msgs = []
    result = _strip_js_comments("const x = 'unterminated;\n", msgs.append, "selftest")
    _st_expect(result is None, "stripper: unterminated string returns None", result)
    _st_expect_fail(msgs, "stripper: unterminated string message", "selftest")


def _selftest_rule7() -> None:
    entries = {"x": {"origin": "migration", "retiredPrefixes": ["fooBar"]}}

    msgs: list[str] = []
    mc, rc = _rule7_retired_gone("function fooBarBaz(", entries, msgs.append)
    _st_expect_fail(msgs, "rule7: surviving function", "fooBar")
    _st_expect((mc, rc) == (1, 0), "rule7: surviving counts", (mc, rc))

    msgs = []
    mc, rc = _rule7_retired_gone("nothing here", entries, msgs.append)
    _st_expect_pass(msgs, "rule7: clean document")
    _st_expect((mc, rc) == (1, 1), "rule7: clean counts", (mc, rc))

    msgs = []
    _rule7_retired_gone(None, entries, msgs.append)
    _st_expect_fail(msgs, "rule7: html is None", str(LEGACY_HTML))

    msgs = []
    _rule7_retired_gone("anything", {"y": {"origin": "new"}}, msgs.append)
    _st_expect_fail(msgs, "rule7: new-only registry", "zero migration")


_ST_MOUNT_VALID = (
    "import { mount as svelteMount } from 'svelte';\n"
    "import Foo from './Foo.svelte';\n"
    "import Bar from './Bar.svelte';\n"
    "const RX = /[a-z]/g;\n"
    "const COMPONENTS = { foo: Foo, bar: Bar };\n"
)
_ST_ENTRIES_FOOBAR = {"foo": {"component": "Foo.svelte"}, "bar": {"component": "Bar.svelte"}}


def _selftest_rule12() -> None:
    stripped = _strip_js_comments(_ST_MOUNT_VALID, lambda _m: None, "selftest")
    msgs: list[str] = []
    count = _rule12_component_bindings(stripped, _ST_ENTRIES_FOOBAR, msgs.append)
    _st_expect_pass(msgs, "rule12: valid mount with regex literal")
    _st_expect(count == 2, "rule12: valid binding count", count)

    msgs = []
    _rule12_component_bindings(stripped, {**_ST_ENTRIES_FOOBAR, "baz": {"component": "Baz.svelte"}}, msgs.append)
    _st_expect_fail(msgs, "rule12: missing key", "baz")

    variants = {
        "rule12: extra key": (
            "const COMPONENTS = { foo: Foo, bar: Bar, baz: Foo };", _ST_ENTRIES_FOOBAR, "baz",
        ),
        "rule12: value not an imported identifier": (
            "const COMPONENTS = { foo: 'Foo', bar: Bar };", _ST_ENTRIES_FOOBAR, "foo",
        ),
        "rule12: path mismatch": (
            "const COMPONENTS = { foo: Bar, bar: Bar };", _ST_ENTRIES_FOOBAR, "foo",
        ),
    }
    for label, (replacement, entries, needle) in variants.items():
        src = _ST_MOUNT_VALID.replace("const COMPONENTS = { foo: Foo, bar: Bar };", replacement)
        stripped_variant = _strip_js_comments(src, lambda _m: None, "selftest")
        msgs = []
        _rule12_component_bindings(stripped_variant, entries, msgs.append)
        _st_expect_fail(msgs, label, needle)

    src_unused = _ST_MOUNT_VALID + "import Unused from './Unused.svelte';\n"
    stripped_unused = _strip_js_comments(src_unused, lambda _m: None, "selftest")
    msgs = []
    _rule12_component_bindings(stripped_unused, _ST_ENTRIES_FOOBAR, msgs.append)
    _st_expect_fail(msgs, "rule12: unused .svelte import", "Unused")

    src_commented = _ST_MOUNT_VALID + "// import Ghost from './Ghost.svelte';\n"
    stripped_commented = _strip_js_comments(src_commented, lambda _m: None, "selftest")
    msgs = []
    _rule12_component_bindings(stripped_commented, _ST_ENTRIES_FOOBAR, msgs.append)
    _st_expect_pass(msgs, "rule12: import mentioned only in a comment")


_ST_SVELTE_VALID = (
    "<script>\n"
    "  import { onMount } from 'svelte';\n"
    "  import { CREATION_TABS } from './tabs.js';\n"
    "</script>\n"
    '<div class="x"><button>Hi</button></div>\n'
)


def _selftest_rule13_valid() -> None:
    msgs: list[str] = []
    n = _rule13_creation_mounts_nothing(_ST_SVELTE_VALID, msgs.append)
    _st_expect_pass(msgs, "rule13: valid document")
    _st_expect(n == 2, "rule13: tag count", n)


def _selftest_rule13_faults() -> None:
    cases = {
        "rule13: .svelte import": (
            "import { CREATION_TABS } from './tabs.js';",
            "import { CREATION_TABS } from './tabs.js';\n  import Foo from './Foo.svelte';",
            None, "Foo.svelte",
        ),
        "rule13: dynamic import(": (
            "import { onMount } from 'svelte';",
            "import { onMount } from 'svelte';\n  const p = import('./x.js');",
            None, "import(",
        ),
        "rule13: mount import from svelte": (
            "import { onMount } from 'svelte';",
            "import { onMount, mount } from 'svelte';",
            None, "mount",
        ),
        "rule13: uppercase tag": (None, None, '<Foo />\n<div class="x">', "Foo"),
        "rule13: svelte:component tag": (None, None, '<svelte:component this={X} />\n<div class="x">', "svelte:component"),
        "rule13: dotted tag": (None, None, '<lib.Foo />\n<div class="x">', "lib.Foo"),
    }
    for label, (old_script, new_script, old_markup_needle, needle) in cases.items():
        src = _ST_SVELTE_VALID
        if old_script is not None:
            src = src.replace(old_script, new_script)
        if old_markup_needle is not None:
            src = src.replace('<div class="x">', old_markup_needle)
        msgs: list[str] = []
        result = _rule13_creation_mounts_nothing(src, msgs.append)
        _st_expect_fail(msgs, label, needle)
        _st_expect(result is None, f"{label}: returns None", result)

    commented = _ST_SVELTE_VALID.replace(
        "</script>", "  // import Foo from './Foo.svelte';\n</script>",
    ).replace(
        '<div class="x">', '<!-- <Foo /> --><div class="x">',
    )
    msgs = []
    _rule13_creation_mounts_nothing(commented, msgs.append)
    _st_expect_pass(msgs, "rule13: mentions only inside comments")


def _run_self_tests() -> None:
    _selftest_registry_valid()
    _selftest_registry_origin_faults()
    _selftest_registry_field_faults()
    _selftest_registry_structural_faults()
    _selftest_rule7()
    _selftest_rule12()
    _selftest_rule13_valid()
    _selftest_rule13_faults()


def main() -> None:
    _run_self_tests()

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
    html = LEGACY_HTML.read_text(encoding="utf-8") if LEGACY_HTML.is_file() else None
    if not tabs_src.strip() or not creation_svelte_src.strip():
        fail(f"{TABS_FILE} or {CREATION_SVELTE_FILE} is empty")
        _report_and_exit()
        return

    if not REGISTRY_FILE.is_file():
        fail(f"{REGISTRY_FILE} does not exist")
        _report_and_exit()
        return
    registry_text = REGISTRY_FILE.read_text(encoding="utf-8")
    stripped_registry = _strip_js_comments(registry_text, fail, str(REGISTRY_FILE))
    if stripped_registry is None:
        _report_and_exit()
        return

    raw_entries, declared = _rule1_parse_registry(stripped_registry, fail)
    entries = _rule2_shape(raw_entries, fail)

    component_ok = _rule3_component_exists(entries)
    container_ok = _rule4_container_exists(creation_svelte_src, entries)
    bijection_ok = _rule5_many_to_many(tabs_src, entries)
    mechanism_ok = _rule6_single_mechanism()
    migration_count, retired_count = _rule7_retired_gone(html, entries, fail)
    action_count = _rule8_mount_action_confinement(mount_src, tabs_src, html)
    state_ok = _rule9_state_nulls(tabs_src, entries)
    dispatch_ok = _rule10_unconditional_dispatch(tabs_src)
    primary_action_count = _rule11_pairing(tabs_src, entries)
    stripped_mount = _strip_js_comments(mount_src, fail, str(MOUNT_FILE))
    binding_count = _rule12_component_bindings(stripped_mount, entries, fail) if stripped_mount is not None else 0
    tag_count = _rule13_creation_mounts_nothing(creation_svelte_src, fail)

    if (
        FAILURES
        or len(entries) != declared
        or not component_ok
        or not container_ok
        or not bijection_ok
        or not mechanism_ok
        or migration_count < 1
        or retired_count != migration_count
        or action_count != 8
        or not state_ok
        or not dispatch_ok
        or binding_count != len(entries)
        or tag_count is None
    ):
        _report_and_exit()
        return

    _report_and_exit(
        {
            "islands": len(entries),
            "migration": migration_count,
            "new": len(entries) - migration_count,
            "retired": retired_count,
            "bindings": binding_count,
            "events": action_count,
            "primary_actions": primary_action_count,
        }
    )


if __name__ == "__main__":
    main()
