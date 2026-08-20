"""G1 check: static asset freshness policy (TICKET-0066, BRIEF-0066-a).

Bare `StaticFiles` emits `etag` + `last-modified` but no `Cache-Control`,
which lets a browser apply HEURISTIC freshness and reuse `shared.css` /
`creation.css` without ever contacting the server -- invisible in the
Network panel, and how a post-TICKET-0059 bundle came to render against
pre-TICKET-0063 stylesheets. `_serve_shell` had the same gap on the shell
document itself, where a stale copy names a hashed bundle that
`emptyOutDir: true` already deleted -- a blank page, not a stale render.
This check holds the fix structurally: same FAILURES/_report_and_exit/ROOT
idiom as shell_height_chain.py / legacy_mount.py, stdlib only, no DB, no
subprocess, AST reads of app.py's constants (never regex -- same discipline
as legacy_mount.py / single_canon_write.py). Four assertions, each
vacuous-proof:

  1. rule1 -- the mount is policy-bearing. `app.mount("/static", ...)`'s
     second positional argument must be a call to
     `_FreshnessAwareStaticFiles`. A bare `StaticFiles(...)` there, or no
     `/static` mount at all, is a FAILURE.
  2. rule2 -- the policy constants exist and are coherent.
     `_REVALIDATE_CACHE_CONTROL` must contain "no-cache",
     `_IMMUTABLE_CACHE_CONTROL` must contain "immutable", and
     `_IMMUTABLE_ASSET_PREFIX` must name a directory that actually exists
     under `_STATIC_DIR` -- so the prefix cannot silently drift to a typo
     that classifies every asset as revalidating. Missing or non-string
     constants are a FAILURE.
  3. rule3 -- the partition is exhaustive and both classes are inhabited.
     Every file under `_STATIC_DIR` is classified by whether its first path
     segment equals `_IMMUTABLE_ASSET_PREFIX`. Zero files walked, zero
     immutable files, or zero revalidating files are each their own
     FAILURE -- a partition with a dead branch proves nothing about the
     branch that is dead.
  4. rule4 -- HTML routes carry the directive. Every function registered
     with `response_class=HTMLResponse` (the `@app.get(...)` decorator form
     and the `app.add_api_route(...)` loop form over `_SHELL_ROUTES`) must
     construct its `HTMLResponse` with a `headers=` dict containing a
     `cache-control` key. `_SHELL_ROUTES` must be non-empty and its
     registering loop found. Zero HTML routes found is a FAILURE.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
APP_PY = ROOT / "src" / "world_engine" / "cockpit" / "app.py"
STATIC_DIR = ROOT / "src" / "world_engine" / "cockpit" / "static"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(counts: dict | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: static_asset_freshness — mount is policy-bearing, "
        f"{counts['immutable']} immutable file(s) / {counts['revalidate']} revalidating file(s), "
        f"{counts['routes']} HTML route(s) covered"
    )
    sys.exit(0)


def _parse_module(path: Path) -> ast.Module | None:
    text = path.read_text(encoding="utf-8")
    try:
        return ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        fail(f"{path}: SyntaxError: {exc}")
        return None


def _call_func_name(call: ast.Call) -> str | None:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _check_mount_policy_bearing(tree: ast.Module) -> bool:
    mount_call = None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "mount"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "app"
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "/static"
        ):
            mount_call = node
            break

    if mount_call is None:
        fail(f"{APP_PY}: no app.mount(\"/static\", ...) call found")
        return False

    if len(mount_call.args) < 2 or not isinstance(mount_call.args[1], ast.Call):
        fail(f"{APP_PY}: app.mount(\"/static\", ...) second argument is not a constructor call")
        return False

    ctor_name = _call_func_name(mount_call.args[1])
    if ctor_name == "StaticFiles":
        fail(f"{APP_PY}: /static mount uses bare StaticFiles(...) -- no freshness policy")
        return False
    if ctor_name != "_FreshnessAwareStaticFiles":
        fail(
            f"{APP_PY}: /static mount second argument is {ctor_name!r}, "
            "expected _FreshnessAwareStaticFiles(...)"
        )
        return False
    return True


def _read_string_constant(tree: ast.Module, name: str) -> str | None:
    value = None
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            value = node.value.value
    return value


def _check_policy_constants(tree: ast.Module) -> str | None:
    """Returns the immutable-prefix value on success (used by rule3 too)."""
    prefix = _read_string_constant(tree, "_IMMUTABLE_ASSET_PREFIX")
    immutable_cc = _read_string_constant(tree, "_IMMUTABLE_CACHE_CONTROL")
    revalidate_cc = _read_string_constant(tree, "_REVALIDATE_CACHE_CONTROL")

    if prefix is None:
        fail(f"{APP_PY}: _IMMUTABLE_ASSET_PREFIX is missing or not a string constant")
    elif not (STATIC_DIR / prefix).is_dir():
        fail(f"{APP_PY}: _IMMUTABLE_ASSET_PREFIX {prefix!r} does not name a directory under {STATIC_DIR}")

    if immutable_cc is None:
        fail(f"{APP_PY}: _IMMUTABLE_CACHE_CONTROL is missing or not a string constant")
    elif "immutable" not in immutable_cc:
        fail(f"{APP_PY}: _IMMUTABLE_CACHE_CONTROL {immutable_cc!r} does not contain 'immutable'")

    if revalidate_cc is None:
        fail(f"{APP_PY}: _REVALIDATE_CACHE_CONTROL is missing or not a string constant")
    elif "no-cache" not in revalidate_cc:
        fail(f"{APP_PY}: _REVALIDATE_CACHE_CONTROL {revalidate_cc!r} does not contain 'no-cache'")

    return prefix


def _check_partition(prefix: str | None) -> tuple[int, int] | None:
    if prefix is None:
        return None
    if not STATIC_DIR.is_dir():
        fail(f"{STATIC_DIR} does not exist")
        return None

    files = [p for p in STATIC_DIR.rglob("*") if p.is_file()]
    if not files:
        fail(f"{STATIC_DIR}: zero files found -- empty scan is a failure")
        return None

    immutable = 0
    revalidate = 0
    for path in files:
        head = path.relative_to(STATIC_DIR).parts[0]
        if head == prefix:
            immutable += 1
        else:
            revalidate += 1

    ok = True
    if immutable == 0:
        fail(f"{STATIC_DIR}: zero files classify as immutable under {prefix!r} -- a dead branch proves nothing")
        ok = False
    if revalidate == 0:
        fail(f"{STATIC_DIR}: zero files classify as revalidating -- a dead branch proves nothing")
        ok = False
    return (immutable, revalidate) if ok else None


def _keyword_is_html_response_class(keywords: list[ast.keyword]) -> bool:
    return any(
        kw.arg == "response_class" and isinstance(kw.value, ast.Name) and kw.value.id == "HTMLResponse"
        for kw in keywords
    )


def _decorator_is_html_route(dec: ast.expr) -> bool:
    return (
        isinstance(dec, ast.Call)
        and isinstance(dec.func, ast.Attribute)
        and isinstance(dec.func.value, ast.Name)
        and dec.func.value.id == "app"
        and _keyword_is_html_response_class(dec.keywords)
    )


def _find_decorator_routes(tree: ast.Module) -> list[ast.FunctionDef]:
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and any(_decorator_is_html_route(d) for d in node.decorator_list)
    ]


def _read_shell_routes(tree: ast.Module) -> list[str] | None:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "_SHELL_ROUTES"
            and isinstance(node.value, (ast.Tuple, ast.List))
        ):
            routes = [
                elt.value for elt in node.value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]
            return routes or None
    return None


def _find_loop_registered_route_func(tree: ast.Module) -> str | None:
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.For)
            and isinstance(node.target, ast.Name)
            and isinstance(node.iter, ast.Name)
            and node.iter.id == "_SHELL_ROUTES"
        ):
            continue
        loop_var = node.target.id
        for stmt in ast.walk(node):
            if not (
                isinstance(stmt, ast.Call)
                and isinstance(stmt.func, ast.Attribute)
                and stmt.func.attr == "add_api_route"
                and isinstance(stmt.func.value, ast.Name)
                and stmt.func.value.id == "app"
                and _keyword_is_html_response_class(stmt.keywords)
            ):
                continue
            if (
                len(stmt.args) >= 2
                and isinstance(stmt.args[0], ast.Name)
                and stmt.args[0].id == loop_var
                and isinstance(stmt.args[1], ast.Name)
            ):
                return stmt.args[1].id
    return None


def _find_function_def(tree: ast.Module, name: str) -> ast.FunctionDef | None:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _function_returns_cache_control(func_def: ast.FunctionDef) -> bool:
    for node in ast.walk(func_def):
        if not isinstance(node, ast.Call):
            continue
        if _call_func_name(node) != "HTMLResponse":
            continue
        for kw in node.keywords:
            if kw.arg == "headers" and isinstance(kw.value, ast.Dict):
                for key in kw.value.keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str) and key.value.lower() == "cache-control":
                        return True
    return False


def _check_html_routes(tree: ast.Module) -> int | None:
    shell_routes = _read_shell_routes(tree)
    if not shell_routes:
        fail(f"{APP_PY}: _SHELL_ROUTES is missing or empty")
        return None

    covered = 0

    decorator_routes = _find_decorator_routes(tree)
    if not decorator_routes:
        fail(f"{APP_PY}: no decorator-form HTML route (response_class=HTMLResponse) found")
    for func_def in decorator_routes:
        if _function_returns_cache_control(func_def):
            covered += 1
        else:
            fail(
                f"{APP_PY}: route function {func_def.name!r} does not return "
                "HTMLResponse(..., headers={'cache-control': ...})"
            )

    loop_func_name = _find_loop_registered_route_func(tree)
    if loop_func_name is None:
        fail(
            f"{APP_PY}: no loop-form registration "
            "(`for ... in _SHELL_ROUTES: app.add_api_route(..., response_class=HTMLResponse)`) found"
        )
    else:
        func_def = _find_function_def(tree, loop_func_name)
        if func_def is None:
            fail(f"{APP_PY}: loop-registered route function {loop_func_name!r} not found at module level")
        elif _function_returns_cache_control(func_def):
            covered += len(shell_routes)
        else:
            fail(
                f"{APP_PY}: route function {loop_func_name!r} does not return "
                "HTMLResponse(..., headers={'cache-control': ...})"
            )

    if not decorator_routes or loop_func_name is None:
        return None
    return covered if covered > 0 else None


def main() -> None:
    if not APP_PY.is_file():
        fail(f"{APP_PY} does not exist")
        _report_and_exit()
        return

    tree = _parse_module(APP_PY)
    if tree is None:
        _report_and_exit()
        return

    mount_ok = _check_mount_policy_bearing(tree)
    prefix = _check_policy_constants(tree)
    partition = _check_partition(prefix)
    routes_covered = _check_html_routes(tree)

    if FAILURES or not mount_ok or partition is None or routes_covered is None:
        _report_and_exit()
        return

    immutable, revalidate = partition
    _report_and_exit({"immutable": immutable, "revalidate": revalidate, "routes": routes_covered})


if __name__ == "__main__":
    main()
