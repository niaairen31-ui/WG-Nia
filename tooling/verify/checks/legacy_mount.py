"""G1 check: legacy-mount registry integrity (TICKET-0056, BRIEF-0056-a).

`frontend/src/legacy/registry.js` is the ONLY declaration of which legacy
surfaces the built shell still hosts inside the same-origin iframe. This
check is what turns that registry from a comment into a structural gate.
No DB, stdlib only, same FAILURES/_report_and_exit/ROOT idiom as
import_cycle.py. Seven assertions, each vacuous-proof (a missing or empty
input is a FAILURE, never a trivially satisfied comparison):

  1. Registry parses, non-empty.
  2. Monotone shrink against tooling/verify/baselines/legacy_mounts.baseline.
  3. Every entry declares a well-formed `retiredBy` (`^TICKET-\\d{4}$`).
  4. Every `showFn` exists as a top-level function in the legacy document.
  5. Confinement: `contentWindow` / `legacy-frame` tokens occur only in
     legacy/bridge.js and LegacyFrame.svelte.
  6. Exactly one `src="/legacy"` assignment, zero `.src =` reassignments.
  7. Shell-route vocabulary agreement (D-i(1), TICKET-0056 BRIEF-0056-c):
     `_SHELL_ROUTES` in app.py (parsed by AST -- never by regex, same
     discipline as single_canon_write.py) equals `SHELL_ROUTES` in
     frontend/src/lib/router.js (parsed by regex over the array literal),
     compared as ORDERED lists.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRONTEND_SRC = ROOT / "frontend" / "src"
REGISTRY_FILE = FRONTEND_SRC / "legacy" / "registry.js"
BASELINE_FILE = ROOT / "tooling" / "verify" / "baselines" / "legacy_mounts.baseline"
LEGACY_INDEX = ROOT / "src" / "world_engine" / "cockpit" / "index.html"
APP_PY = ROOT / "src" / "world_engine" / "cockpit" / "app.py"
ROUTER_JS = FRONTEND_SRC / "lib" / "router.js"

CONFINED_FILES = {
    FRONTEND_SRC / "legacy" / "bridge.js",
    FRONTEND_SRC / "LegacyFrame.svelte",
}

ENTRY_RE = re.compile(
    r"^\s*(\w+):\s*Object\.freeze\(\{\s*showFn:\s*'([^']*)',\s*retiredBy:\s*'([^']*)'\s*\}\),?\s*$",
    re.MULTILINE,
)
RETIRED_BY_RE = re.compile(r"^TICKET-\d{4}$")
CONTENT_WINDOW_RE = re.compile(r"contentWindow")
LEGACY_FRAME_RE = re.compile(r"legacy-frame")
FRAME_SRC_RE = re.compile(r'src="/legacy"')
SRC_ASSIGN_RE = re.compile(r"\.src\s*=")
SHELL_ROUTES_JS_RE = re.compile(r"export const SHELL_ROUTES\s*=\s*\[(.*?)\]", re.DOTALL)
STRING_LITERAL_RE = re.compile(r'"([^"]*)"')

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(counts: dict | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: legacy_mount — {counts['mounts']} mount(s) within baseline, "
        f"{counts['retiring']} retiring ticket(s), {counts['fns']} legacy fn(s) resolved, "
        f"access confined to bridge, {counts['src_sites']} frame src site, "
        f"{counts['shell_routes']} shell route(s) agreed"
    )
    sys.exit(0)


def _parse_registry() -> dict[str, dict[str, str]] | None:
    if not REGISTRY_FILE.is_file():
        fail(f"{REGISTRY_FILE} does not exist")
        return None
    text = REGISTRY_FILE.read_text(encoding="utf-8")
    entries: dict[str, dict[str, str]] = {}
    for match in ENTRY_RE.finditer(text):
        key, show_fn, retired_by = match.groups()
        entries[key] = {"showFn": show_fn, "retiredBy": retired_by}
    if not entries:
        fail(f"{REGISTRY_FILE}: zero LEGACY_MOUNTS entries parsed")
        return None
    return entries


def _check_monotone_shrink(keys: set[str]) -> bool:
    if not BASELINE_FILE.is_file():
        fail(f"{BASELINE_FILE} does not exist")
        return False
    baseline_keys = {
        line.strip() for line in BASELINE_FILE.read_text(encoding="utf-8").splitlines() if line.strip()
    }
    if not baseline_keys:
        fail(f"{BASELINE_FILE} is empty")
        return False
    ok = True
    for key in sorted(keys):
        if key not in baseline_keys:
            fail(f"legacy mount '{key}' is not in the baseline -- the registry may only SHRINK (TICKET-0056)")
            ok = False
    return ok


def _check_retired_by(entries: dict[str, dict[str, str]]) -> int:
    count = 0
    for key, entry in entries.items():
        retired_by = entry.get("retiredBy", "")
        if not RETIRED_BY_RE.match(retired_by):
            fail(f"legacy mount '{key}': retiredBy {retired_by!r} does not match ^TICKET-\\d{{4}}$")
            continue
        count += 1
    return count


def _check_show_fns(entries: dict[str, dict[str, str]]) -> int:
    if not LEGACY_INDEX.is_file():
        fail(f"{LEGACY_INDEX} does not exist")
        return 0
    text = LEGACY_INDEX.read_text(encoding="utf-8")
    count = 0
    for key, entry in entries.items():
        show_fn = entry["showFn"]
        if not re.search(rf"^function {re.escape(show_fn)}\(", text, re.MULTILINE):
            fail(f"legacy mount '{key}': showFn {show_fn!r} has no top-level function in {LEGACY_INDEX}")
            continue
        count += 1
    return count


def _check_confinement() -> bool:
    if not FRONTEND_SRC.is_dir():
        fail(f"{FRONTEND_SRC} is not a directory")
        return False
    files = [p for p in FRONTEND_SRC.rglob("*") if p.is_file()]
    if not files:
        fail(f"{FRONTEND_SRC} contains no files -- empty scan is a failure")
        return False
    ok = True
    for path in files:
        if path in CONFINED_FILES:
            continue
        text = path.read_text(encoding="utf-8")
        if CONTENT_WINDOW_RE.search(text):
            fail(f"{path}: 'contentWindow' used outside legacy/bridge.js -- confinement violated")
            ok = False
        if LEGACY_FRAME_RE.search(text):
            fail(f"{path}: 'legacy-frame' used outside legacy/bridge.js / LegacyFrame.svelte -- confinement violated")
            ok = False
    return ok


def _check_single_src_site() -> int | None:
    if not FRONTEND_SRC.is_dir():
        fail(f"{FRONTEND_SRC} is not a directory")
        return None
    files = [p for p in FRONTEND_SRC.rglob("*") if p.is_file()]
    if not files:
        fail(f"{FRONTEND_SRC} contains no files -- empty scan is a failure")
        return None
    src_sites = 0
    assign_sites = 0
    for path in files:
        text = path.read_text(encoding="utf-8")
        src_sites += len(FRAME_SRC_RE.findall(text))
        assign_sites += len(SRC_ASSIGN_RE.findall(text))
    if src_sites != 1:
        fail(f"expected exactly one src=\"/legacy\" assignment site, found {src_sites}")
        return None
    if assign_sites != 0:
        fail(f"expected zero '.src =' reassignments, found {assign_sites}")
        return None
    return src_sites


def _parse_app_shell_routes() -> list[str] | None:
    if not APP_PY.is_file():
        fail(f"{APP_PY} does not exist")
        return None
    text = APP_PY.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(APP_PY))
    except SyntaxError as exc:
        fail(f"{APP_PY}: SyntaxError: {exc}")
        return None
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not (isinstance(target, ast.Name) and target.id == "_SHELL_ROUTES"):
            continue
        if not isinstance(node.value, (ast.Tuple, ast.List)):
            continue
        routes = [
            elt.value
            for elt in node.value.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        ]
        if routes:
            return routes
    fail(f"{APP_PY}: _SHELL_ROUTES assignment not found or empty")
    return None


def _parse_router_js_shell_routes() -> list[str] | None:
    if not ROUTER_JS.is_file():
        fail(f"{ROUTER_JS} does not exist")
        return None
    text = ROUTER_JS.read_text(encoding="utf-8")
    match = SHELL_ROUTES_JS_RE.search(text)
    if not match:
        fail(f"{ROUTER_JS}: SHELL_ROUTES array literal not found")
        return None
    routes = STRING_LITERAL_RE.findall(match.group(1))
    if not routes:
        fail(f"{ROUTER_JS}: SHELL_ROUTES parsed to zero entries")
        return None
    return routes


def _check_shell_route_agreement() -> int | None:
    app_routes = _parse_app_shell_routes()
    router_routes = _parse_router_js_shell_routes()
    if app_routes is None or router_routes is None:
        return None
    if app_routes != router_routes:
        fail(
            f"shell route vocabulary diverges -- app.py has {app_routes} , "
            f"router.js has {router_routes}"
        )
        return None
    return len(app_routes)


def main() -> None:
    entries = _parse_registry()
    if entries is None:
        _report_and_exit()
        return

    keys = set(entries.keys())
    shrink_ok = _check_monotone_shrink(keys)
    retiring_count = _check_retired_by(entries)
    fn_count = _check_show_fns(entries)
    confinement_ok = _check_confinement()
    src_sites = _check_single_src_site()
    shell_route_count = _check_shell_route_agreement()

    if (
        FAILURES
        or not shrink_ok
        or not confinement_ok
        or src_sites is None
        or shell_route_count is None
    ):
        _report_and_exit()
        return

    _report_and_exit(
        {
            "mounts": len(entries),
            "retiring": retiring_count,
            "fns": fn_count,
            "src_sites": src_sites,
            "shell_routes": shell_route_count,
        }
    )


if __name__ == "__main__":
    main()
