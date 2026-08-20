"""G1 check: the bridge-reach seam (TICKET-0059, BRIEF-0059-b).

TICKET-0059 (BRIEF-0059-b). The bridge-reach seam: an enumerated,
MONOTONICALLY SHRINKING list of the sites where a Svelte module still
reaches into the legacy window through callLegacy -- by ANY of
bridge.js's exports, not only legacyCall. RECON-0059-a M1 found that
counting the string `legacyCall(` misses eight narrow-named wrappers
over the same primitive; rule2 therefore derives the reaching surface
from bridge.js rather than hardcoding it. The set may only lose
records. Every record bearing TICKET-0059 must be gone before
`creation` may leave LEGACY_MOUNTS -- rule7 enforces that ordering
structurally, not by brief sequencing.

Prune protocol: the brief that closes a bridge-reach site deletes its
baseline record in the same commit. Closing without pruning leaves a
`stale:` line; pruning without closing FAILS rule4 on the next run.
Neither direction drifts silently.

Nine rules, each named in its own failure message:

  rule1 (scan is real)              -- vacuous-proof file collection.
  rule2 (surface is derived)        -- reaching exports parsed out of
                                        bridge.js, never hardcoded.
  rule3 (census)                    -- every call site of a reaching
                                        export, across frontend/src/
                                        minus bridge.js; a legacyCall(
                                        first argument that isn't a
                                        plain string literal is itself
                                        a FAIL.
  rule4 (subset)                    -- every observed site has a
                                        matching baseline record.
  rule5 (monotone shrink)           -- observed <= baseline, per
                                        (path, fn); extra baseline
                                        records print as `stale:`.
  rule6 (primitive confinement)     -- callLegacy defined once,
                                        unexported, in bridge.js;
                                        legacyCall defined once,
                                        exported, in bridge.js.
  rule7 (terminal ordering)         -- a TICKET-0059 record survives
                                        only while LEGACY_MOUNTS still
                                        declares `creation`.
  rule8 (ticket vocabulary)         -- every baseline retiredBy field
                                        matches ^TICKET-\\d{4}$.
  rule9 (mount-door confinement)    -- TICKET-0059 (BRIEF-0059-l amendment).
                                        `legacyDocument` importable only by
                                        frontend/src/creation/mount.js,
                                        frontend/src/graph/mount.js and
                                        frontend/src/App.svelte.
                                        SUPPLEMENT-0059 Amendment 2 excluded
                                        it from rule2/rule3's census
                                        on the reasoning that the coupling was
                                        "already governed by creation_island.py
                                        and legacy_mount.py" -- a full door
                                        census (this ticket) found neither
                                        check mentions it, and one real
                                        violation (npcAgent.svelte.js
                                        reaching linkAgent's own DOM through
                                        the mount door). This rule is the
                                        missing guard, landed in the same
                                        commit as the violation's fix.
                                        `legacyContainer` retired at
                                        TICKET-0065 (BRIEF-0065-b): the graph
                                        mount seam moved fully onto the shell
                                        document, and bridge.js no longer
                                        exports the name at all, so there is
                                        no door left to confine (No structure
                                        without a reader) -- dropped from
                                        MOUNT_DOOR_ALLOWED accordingly.

No DB, stdlib only, same FAILURES/_report_and_exit/ROOT idiom as
legacy_mount.py.
"""
from __future__ import annotations

import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRONTEND_SRC = ROOT / "frontend" / "src"
BRIDGE_FILE = FRONTEND_SRC / "legacy" / "bridge.js"
REGISTRY_FILE = FRONTEND_SRC / "legacy" / "registry.js"
BASELINE_FILE = ROOT / "tooling" / "verify" / "baselines" / "legacy_calls.baseline"

RETIRED_BY_RE = re.compile(r"^TICKET-\d{4}$")
FUNC_DEF_RE = re.compile(
    r"(?P<export>export\s+)?(?P<async>async\s+)?function\s+(?P<name>[A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{"
)
CALL_LEGACY_ARG_RE = re.compile(r"callLegacy\s*\(\s*([^,)]*)")
IMPORT_LINE_RE = re.compile(
    r"^.*\bimport\b.*from\s*['\"][^'\"]*legacy/bridge(\.js)?['\"].*$", re.MULTILINE
)
LEGACY_CALL_CALL_RE = re.compile(r"\blegacyCall\s*\(")
LEGACY_CALL_STRING_ARG_RE = re.compile(r"\blegacyCall\s*\(\s*(['\"])((?:(?!\1).)*)\1")
MOUNTS_CREATION_RE = re.compile(r"^\s*creation:\s*Object\.freeze\(", re.MULTILINE)

GRAPH_MOUNT_FILE = FRONTEND_SRC / "graph" / "mount.js"
CREATION_MOUNT_FILE = FRONTEND_SRC / "creation" / "mount.js"
APP_SVELTE_FILE = FRONTEND_SRC / "App.svelte"
MOUNT_DOOR_ALLOWED = {
    "legacyDocument": {CREATION_MOUNT_FILE, GRAPH_MOUNT_FILE, APP_SVELTE_FILE},
}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(counts: dict | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: legacy_call — {counts['observed']} bridge-reach site(s) observed, "
        f"{counts['baseline']} baselined, {counts['stale']} stale, "
        f"{counts['exports']} reaching export(s) derived"
    )
    sys.exit(0)


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _extract_balanced(text: str, open_brace_idx: int) -> str:
    depth = 0
    i = open_brace_idx
    n = len(text)
    while i < n:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[open_brace_idx + 1 : i]
        i += 1
    return text[open_brace_idx + 1 :]


def _collect_frontend_files() -> list[Path]:
    if not FRONTEND_SRC.is_dir():
        fail(f"{FRONTEND_SRC} is not a directory")
        return []
    files = sorted(
        p
        for p in FRONTEND_SRC.rglob("*")
        if p.is_file() and p.suffix in (".svelte", ".js")
    )
    if not files:
        fail("rule1: vacuous scan -- zero .svelte/.js files under frontend/src/")
        return []
    if BRIDGE_FILE not in files:
        fail(f"rule1: {BRIDGE_FILE} is absent from the collection")
    return files


def _derive_reaching_surface() -> dict[str, str | None]:
    """Parse bridge.js; return {export_name: constant_target_or_None}.

    None means the export's target is per-call-site (a dynamic
    passthrough, e.g. legacyCall itself) -- derived, not assumed, by
    noticing the export forwards its OWN first parameter into
    callLegacy(...) rather than a literal or a property access.
    """
    if not BRIDGE_FILE.is_file():
        fail(f"rule2: {BRIDGE_FILE} does not exist")
        return {}
    raw = BRIDGE_FILE.read_text(encoding="utf-8")
    text = _strip_comments(raw)

    reaching: dict[str, str | None] = {}
    for m in FUNC_DEF_RE.finditer(text):
        if not m.group("export"):
            continue
        name = m.group("name")
        first_param = None
        paren_start = text.index("(", m.start("name"))
        paren_end = text.index(")", paren_start)
        params_text = text[paren_start + 1 : paren_end].strip()
        if params_text:
            first_param = re.split(r"[,\s]", params_text)[0].lstrip(".")
        open_brace = text.index("{", paren_end)
        body = _extract_balanced(text, open_brace)
        call_m = CALL_LEGACY_ARG_RE.search(body)
        if not call_m:
            continue  # does not reach callLegacy -- not part of the surface
        arg0 = call_m.group(1).strip()
        str_m = re.match(r"^(['\"])(.*)\1$", arg0)
        if str_m:
            reaching[name] = str_m.group(2)
        elif first_param and arg0 == first_param:
            reaching[name] = None  # dynamic passthrough, e.g. legacyCall
        elif "." in arg0:
            reaching[name] = arg0.rsplit(".", 1)[-1]
        else:
            reaching[name] = arg0

    if not reaching:
        fail("rule2: derived reaching-export set is empty -- bridge.js parse produced nothing")
    return reaching


def _census(files: list[Path], reaching: dict[str, str | None]) -> list[tuple[str, str]]:
    """Return observed (relpath, legacy_fn) sites across files, excluding bridge.js."""
    observed: list[tuple[str, str]] = []
    dynamic_names = {name for name, target in reaching.items() if target is None}
    constant_names = {name: target for name, target in reaching.items() if target is not None}

    for path in files:
        if path == BRIDGE_FILE:
            continue
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        text = _strip_comments(text)
        text = IMPORT_LINE_RE.sub("", text)

        for name in dynamic_names:
            # Today the sole dynamic export is legacyCall; scoped by name
            # so a future dynamic wrapper is picked up the same way.
            total = len(LEGACY_CALL_CALL_RE.findall(text)) if name == "legacyCall" else len(
                re.findall(rf"\b{re.escape(name)}\s*\(", text)
            )
            if name == "legacyCall":
                literal_matches = list(LEGACY_CALL_STRING_ARG_RE.finditer(text))
                if len(literal_matches) != total:
                    fail(
                        f"rule3: {rel} calls legacyCall(...) with a first argument that "
                        "is not a plain string literal -- a computed legacy function name "
                        "defeats the census"
                    )
                    continue
                for lm in literal_matches:
                    observed.append((rel, lm.group(2)))
            else:
                # No other dynamic export exists today; if bridge.js grows
                # one, its call sites are uncensusable by name alone and
                # must be added to this branch deliberately.
                fail(
                    f"rule3: {rel} reaches dynamic export {name!r}, which this check "
                    "does not yet know how to resolve a target for"
                )

        for name, target in constant_names.items():
            for _ in re.finditer(rf"\b{re.escape(name)}\b", text):
                observed.append((rel, target))

    return observed


def _load_baseline() -> list[tuple[str, str, str]] | None:
    if not BASELINE_FILE.is_file():
        fail(f"{BASELINE_FILE} does not exist")
        return None
    lines = [
        line for line in BASELINE_FILE.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    if not lines:
        fail(f"{BASELINE_FILE} is empty")
        return None
    records: list[tuple[str, str, str]] = []
    for line in lines:
        parts = line.split("::")
        if len(parts) != 3:
            fail(f"rule8: malformed baseline record {line!r} -- expected path::fn::TICKET-NNNN")
            continue
        path, fn, retired_by = parts
        if not RETIRED_BY_RE.match(retired_by):
            fail(f"rule8: baseline record {line!r} has retiredBy {retired_by!r}, not ^TICKET-\\d{{4}}$")
            continue
        records.append((path, fn, retired_by))
    return records


def _check_subset_and_shrink(
    observed: list[tuple[str, str]], baseline: list[tuple[str, str, str]]
) -> None:
    observed_counts = Counter(observed)
    baseline_counts: Counter[tuple[str, str]] = Counter()
    baseline_lines: dict[tuple[str, str], str] = {}
    for path, fn, retired_by in baseline:
        key = (path, fn)
        baseline_counts[key] += 1
        baseline_lines[key] = f"{path}::{fn}::{retired_by}"

    for key, count in observed_counts.items():
        if baseline_counts.get(key, 0) < count:
            path, fn = key
            fail(f"rule4: new bridge-reach site {path}::{fn} -- the seam may only shrink")

    for key, base_count in baseline_counts.items():
        surplus = base_count - observed_counts.get(key, 0)
        for _ in range(max(surplus, 0)):
            print(f"stale: {baseline_lines[key]}")


def _check_terminal_ordering(baseline: list[tuple[str, str, str]]) -> None:
    has_0059 = any(retired_by == "TICKET-0059" for _, _, retired_by in baseline)
    if not has_0059:
        return
    if not REGISTRY_FILE.is_file():
        fail(f"rule7: {REGISTRY_FILE} does not exist")
        return
    text = REGISTRY_FILE.read_text(encoding="utf-8")
    if not MOUNTS_CREATION_RE.search(text):
        n = sum(1 for _, _, r in baseline if r == "TICKET-0059")
        fail(
            f"rule7: creation mount retired with {n} TICKET-0059 bridge-reach site(s) still open"
        )


def _check_confinement() -> None:
    if not BRIDGE_FILE.is_file():
        return
    all_files = [
        p for p in FRONTEND_SRC.rglob("*") if p.is_file() and p.suffix in (".svelte", ".js")
    ]
    call_legacy_defs: list[tuple[Path, bool]] = []
    legacy_call_defs: list[tuple[Path, bool]] = []
    for path in all_files:
        text = _strip_comments(path.read_text(encoding="utf-8"))
        for m in FUNC_DEF_RE.finditer(text):
            name = m.group("name")
            exported = bool(m.group("export"))
            if name == "callLegacy":
                call_legacy_defs.append((path, exported))
            elif name == "legacyCall":
                legacy_call_defs.append((path, exported))

    if len(call_legacy_defs) != 1:
        fail(f"rule6: callLegacy is defined {len(call_legacy_defs)} time(s) in the tree, expected exactly 1")
    else:
        path, exported = call_legacy_defs[0]
        if path != BRIDGE_FILE:
            fail(f"rule6: callLegacy is defined in {path}, not {BRIDGE_FILE}")
        if exported:
            fail("rule6: callLegacy is exported -- it must stay private to bridge.js")

    if len(legacy_call_defs) != 1:
        fail(f"rule6: legacyCall is defined {len(legacy_call_defs)} time(s) in the tree, expected exactly 1")
    else:
        path, exported = legacy_call_defs[0]
        if path != BRIDGE_FILE:
            fail(f"rule6: legacyCall is defined in {path}, not {BRIDGE_FILE}")
        if not exported:
            fail("rule6: legacyCall is not exported")


def _check_mount_door_confinement(files: list[Path]) -> int:
    """rule9: legacyContainer/legacyDocument importable only by the
    sanctioned mount-seam files (plus App.svelte for legacyDocument).
    Vacuity-proof: zero importers found for a name (even among the
    allowed set) is a broken scan, not a pass -- these two names are
    used by the mount seam today, so a clean scan always finds at least
    one importer of each."""
    confined = 0
    for name, allowed in MOUNT_DOOR_ALLOWED.items():
        import_re = re.compile(
            rf"import\s*\{{[^}}]*\b{re.escape(name)}\b[^}}]*\}}\s*from\s*"
            r"""['"][^'"]*legacy/bridge(\.js)?['"]"""
        )
        importers: set[Path] = set()
        for path in files:
            if path == BRIDGE_FILE:
                continue
            text = _strip_comments(path.read_text(encoding="utf-8"))
            if import_re.search(text):
                importers.add(path)
        if not importers:
            fail(f"rule9: zero importer(s) of {name!r} found -- broken scan, not a pass")
            continue
        ok = True
        for path in sorted(importers):
            if path not in allowed:
                allowed_list = ", ".join(sorted(p.relative_to(ROOT).as_posix() for p in allowed))
                fail(
                    f"rule9: {path.relative_to(ROOT).as_posix()} imports {name!r} from "
                    f"legacy/bridge.js -- confined to {allowed_list}"
                )
                ok = False
        if ok:
            confined += 1
    return confined


def main() -> None:
    files = _collect_frontend_files()
    reaching = _derive_reaching_surface() if not FAILURES else {}
    baseline = _load_baseline()

    if not files or not reaching or baseline is None:
        _report_and_exit()
        return

    observed = _census(files, reaching)
    _check_subset_and_shrink(observed, baseline)
    _check_terminal_ordering(baseline)
    _check_confinement()
    door_confined = _check_mount_door_confinement(files)

    if door_confined != len(MOUNT_DOOR_ALLOWED):
        _report_and_exit()
        return

    _report_and_exit(
        {
            "observed": len(observed),
            "baseline": len(baseline),
            "stale": max(len(baseline) - len(observed), 0),
            "exports": len(reaching),
        }
    )


if __name__ == "__main__":
    main()
