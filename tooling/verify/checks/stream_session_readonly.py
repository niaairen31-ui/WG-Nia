"""G1 check: the Play stream's request session is read-only (TICKET-0072,
BRIEF-0072-d).

BRIEF-0072-a put the SQLite carrier in WAL, which stops a reader from
blocking a writer. It does not stop the second failure mode WAL was hiding:
the request session bound at `routes/play.py:171` is pinned to a read
snapshot taken at `play.py:143` and held open for the whole SSE response.
Under WAL, a pinned transaction that then attempts to WRITE, after any other
connection has committed, fails instantly with `SQLITE_BUSY_SNAPSHOT` --
reported as the same "database is locked" text, and immune to
`busy_timeout`. Two sites wrote on that session before this brief:
`play_stream.py:110` (`_perform_travel`) and `play.py:390`
(`_join_gathering`, via a nested-session call site owned by the caller --
`_join_gathering` itself keeps its original signature and its other two
callers; see BRIEF-0072-d's decision H1). Both now run on a session of
their own. This check is what turns "the request session is read-only for
the life of a stream" from a fact about two call sites into a structural
property of the four Play modules.

AST only -- never regex, same discipline as `legacy_mount.py` and
`single_canon_write.py`. No DB, no import of application code, no
subprocess.

**Declared module set** (a module-level tuple, so the scope is declared
rather than inferred): the four Play modules --
`src/world_engine/cockpit/{play,play_stream,play_physical,play_initiative}.py`
-- plus every module they hand a session to --
`src/world_engine/{context,context_window,analyzer,gathering,prompt_store,scene_format}.py`.
A named module missing from disk is a FAILURE. `scene_format` joined the set
in TICKET-0073/BRIEF-0073-a, a verbatim relocation of three read-only
formatters (`active_signposts`, `format_inventory_line`,
`format_item_list_for_interpretation`) out of `context.py` -- same
relocation-not-broadening precedent as `models.py` -> `models/` and
`play_stream.py` -> `play_initiative.py`; the moved code has zero writers,
so the set grows by exactly the new module, nothing else.

**WRITERS** -- every function defined anywhere in the declared set whose
body calls `.add(`, `.delete(`, `.merge(`, `.commit(` or `.flush(` on a
receiver that is genuinely SQLAlchemy-Session-typed -- a parameter
annotated `Session`, or a `with Session(engine) as X:` binding, same
discipline as `single_canon_write.py::collect_functions`'s `session_params`
-- transitively closed by name over calls between functions in the declared
set: a function that calls a writer is itself a writer, to a fixed point.
(A blind "any receiver" match was tried first and rejected: it flags a
plain `some_set.add(...)` -- `_location_neighbours`'s `seen.add(...)` and
`_resolve_join_target`'s `candidates.add(...)` are both ordinary Python
`set.add()`, not ORM writes, and a naive match marks both functions, and
everything that calls them, as false-positive writers.) `_scene_response ->
_get_or_open_session` is the shape the transitive closure exists for;
`analyzer.py` and `gathering.py` are why the declared set reaches past the
four Play modules (`_analyze_window`, `_analyze_overhearing`, `migrate_npc`
all write, and are all called from the stream -- always on a nested session
today, never on `ctx.db`).

**REQUEST-SESSION EXPRESSIONS**, resolved only within the four Play
modules: the attribute `ctx.db`, plus every local name bound to it by a
direct assignment (`db = ctx.db`) inside the function being walked.
Function-local -- never propagated across a function boundary, even when
that boundary is a parameter literally named `db`.

Six rules:

  1. **No direct write.** Any `<req>.add/.delete/.merge/.commit/.flush(...)`
     where `<req>` is a request-session expression is a FAILURE.
  2. **No write by delegation.** Any call site in the four Play modules
     passing a request-session expression to a callee in WRITERS is a
     FAILURE. This is the rule that would have caught `play.py:390` and
     `play_stream.py:110` in their pre-fix form.
  3. **Unresolvable callee is a failure, not a pass.** A request-session
     expression passed to a callee whose defining module cannot be resolved
     -- through the caller module's own `import` statements -- to a module
     in the declared set is a FAILURE. The declared set grows deliberately,
     in a ticket; fail-closed on the unknown is the point, since the
     alternative is a green that means "I could not see."
  4. **No attribute assignment on the request session's conversation.** Any
     `ctx.conv.<attr> = ...`, or the same through a local name bound to
     `ctx.conv`, is a FAILURE. SQLAlchemy's autoflush (measured `True` on
     this session -- see the TICKET-0072 RECON) turns such an assignment
     into an implicit UPDATE on the pinned transaction at the next query --
     a write with no call site, invisible to rule1 and rule2. Measured zero
     occurrences today; this rule ships green and freezes the property.
  5. **Vacuity guards, four of them.** Every declared module must exist and
     parse; WRITERS must be non-empty; the alias map must be non-empty
     (expected 8 -- the resolved count is reported, never hard-coded); and
     the count of call sites passing a request-session expression to any
     callee must be non-zero. Each empty result means the walker stopped
     seeing the code, not that the code is clean -- each is a FAILURE.
  6. **No exemption mechanism.** No allowlist, no skip list, no
     comment-directive escape -- asserted by construction: this module
     defines no such constant, checked by scanning its own source.

**The stated limit**, in the "proves X, not Y" voice already used in this
corpus: this proves no request-session write inside the declared module
set; a call chain leaving that set is caught by rule3 as a failure, never
waved through. The check does not resolve the whole program -- it refuses
to guess about what it cannot see.

One implementation per rule; no overlap with `sqlite_concurrency.py` --
engine posture there, session ownership here.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

# (short_name, path) -- short_name is what a relative `from ..X import ...`
# or `from . import X as ...` resolves to.
DECLARED_MODULES: tuple[tuple[str, Path], ...] = (
    ("play", SRC / "world_engine" / "cockpit" / "play.py"),
    ("play_stream", SRC / "world_engine" / "cockpit" / "play_stream.py"),
    ("play_physical", SRC / "world_engine" / "cockpit" / "play_physical.py"),
    ("play_initiative", SRC / "world_engine" / "cockpit" / "play_initiative.py"),
    ("context", SRC / "world_engine" / "context.py"),
    ("context_window", SRC / "world_engine" / "context_window.py"),
    ("analyzer", SRC / "world_engine" / "analyzer.py"),
    ("gathering", SRC / "world_engine" / "gathering.py"),
    ("prompt_store", SRC / "world_engine" / "prompt_store.py"),
    ("scene_format", SRC / "world_engine" / "scene_format.py"),
)
DECLARED_NAMES = {name for name, _ in DECLARED_MODULES}
PLAY_MODULES = ("play", "play_stream", "play_physical", "play_initiative")

WRITE_METHODS = {"add", "delete", "merge", "commit", "flush"}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit(counts: dict | None = None) -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        f"PASS: stream_session_readonly — {counts['modules']} module(s) declared, "
        f"{counts['writers']} writer(s) (transitive), {counts['aliases']} alias(es), "
        f"{counts['call_sites']} request-session call site(s), "
        f"zero writes on the request session"
    )
    sys.exit(0)


def _rule6_no_exemption_mechanism() -> None:
    """This module defines no allowlist/skip-list/exemption constant --
    checked by scanning its own source, so the assertion cannot silently
    rot if one is added later."""
    own_source = Path(__file__).read_text(encoding="utf-8")
    forbidden = ("ALLOWLIST", "ALLOW_LIST", "EXEMPT", "SKIP_LIST", "# noqa: stream_session")
    for token in forbidden:
        # Skip matches inside this very function's own string literals by
        # only scanning the module docstring onward is impractical to
        # separate reliably by regex-free means; instead we assert the
        # token never appears as an identifier definition. A plain
        # substring check is intentionally strict here: a truly clean file
        # has zero occurrences of any of these tokens outside this
        # function's own tuple of forbidden strings.
        occurrences = own_source.count(token)
        # Each forbidden token appears exactly once: right here, as a
        # string literal inside `forbidden`. More than one occurrence means
        # an exemption construct was added elsewhere in the file.
        if occurrences > 1:
            fail(f"{Path(__file__).name}: forbidden exemption token {token!r} found outside this guard")


class _ModuleInfo:
    __slots__ = ("short_name", "path", "tree", "functions", "direct_name_to_origin", "submodule_alias_to_module")

    def __init__(self, short_name: str, path: Path, tree: ast.Module) -> None:
        self.short_name = short_name
        self.path = path
        self.tree = tree
        self.functions: dict[str, ast.FunctionDef] = {}
        self.direct_name_to_origin: dict[str, tuple[str, str]] = {}
        self.submodule_alias_to_module: dict[str, str] = {}


def _load_modules() -> dict[str, _ModuleInfo] | None:
    modules: dict[str, _ModuleInfo] = {}
    for short_name, path in DECLARED_MODULES:
        if not path.is_file():
            fail(f"{path} does not exist (declared module {short_name!r})")
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            fail(f"{path}: cannot parse ({exc})")
            continue
        modules[short_name] = _ModuleInfo(short_name, path, tree)
    if len(modules) != len(DECLARED_MODULES):
        return None

    for info in modules.values():
        for node in ast.walk(info.tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                info.functions[node.name] = node
            elif isinstance(node, ast.ImportFrom):
                if node.level >= 1 and node.module is None:
                    # from . import X [as Y]  -- submodule import.
                    for alias in node.names:
                        if alias.name in DECLARED_NAMES:
                            local = alias.asname or alias.name
                            info.submodule_alias_to_module[local] = alias.name
                elif node.level >= 1 and node.module in DECLARED_NAMES:
                    # from ..module import a, b as c
                    for alias in node.names:
                        local = alias.asname or alias.name
                        info.direct_name_to_origin[local] = (node.module, alias.name)
    return modules


def _session_typed_names(fnode: ast.AST) -> set[str]:
    """Names that are genuinely SQLAlchemy-Session-typed within `fnode`:
    parameters annotated `Session` (same discipline as
    `single_canon_write.py::collect_functions`'s `session_params`), plus
    `with Session(engine) as X:` bindings. Deliberately narrower than "any
    receiver" -- a bare receiver-name match would also catch a plain
    `some_set.add(...)`, which is not an ORM write."""
    names: set[str] = set()
    if isinstance(fnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = list(fnode.args.posonlyargs) + list(fnode.args.args) + list(fnode.args.kwonlyargs)
        for a in args:
            if isinstance(a.annotation, ast.Name) and a.annotation.id == "Session":
                names.add(a.arg)
    for sub in ast.walk(fnode):
        if isinstance(sub, ast.With):
            for item in sub.items:
                cexpr = item.context_expr
                if (
                    isinstance(item.optional_vars, ast.Name)
                    and isinstance(cexpr, ast.Call)
                    and isinstance(cexpr.func, ast.Name)
                    and cexpr.func.id == "Session"
                ):
                    names.add(item.optional_vars.id)
    return names


def _function_calls_write_method(node: ast.AST) -> bool:
    session_names = _session_typed_names(node)
    for sub in ast.walk(node):
        if (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Attribute)
            and sub.func.attr in WRITE_METHODS
            and isinstance(sub.func.value, ast.Name)
            and sub.func.value.id in session_names
        ):
            return True
    return False


def _call_target_name(call: ast.Call) -> str | None:
    if isinstance(call.func, ast.Name):
        return call.func.id
    if isinstance(call.func, ast.Attribute):
        return call.func.attr
    return None


def _compute_writers(modules: dict[str, _ModuleInfo]) -> set[tuple[str, str]]:
    writers: set[tuple[str, str]] = set()
    for info in modules.values():
        for fname, fnode in info.functions.items():
            if _function_calls_write_method(fnode):
                writers.add((info.short_name, fname))

    writer_names = {fname for _mod, fname in writers}
    changed = True
    while changed:
        changed = False
        for info in modules.values():
            for fname, fnode in info.functions.items():
                if (info.short_name, fname) in writers:
                    continue
                for sub in ast.walk(fnode):
                    if isinstance(sub, ast.Call):
                        target = _call_target_name(sub)
                        if target is not None and target in writer_names:
                            writers.add((info.short_name, fname))
                            writer_names.add(fname)
                            changed = True
                            break
    return writers


def _is_ctx_db(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "db"
        and isinstance(node.value, ast.Name)
        and node.value.id == "ctx"
    )


def _is_ctx_conv(node: ast.AST) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "conv"
        and isinstance(node.value, ast.Name)
        and node.value.id == "ctx"
    )


def _local_aliases_in_function(fnode: ast.AST, *, of_predicate) -> set[str]:
    """Names locally assigned (`x = <expr>`) where `<expr>` satisfies
    `of_predicate`, anywhere in `fnode`'s body. Function-local by
    construction -- `fnode` is walked in isolation, never across a call
    boundary."""
    aliases: set[str] = set()
    for sub in ast.walk(fnode):
        if (
            isinstance(sub, ast.Assign)
            and len(sub.targets) == 1
            and isinstance(sub.targets[0], ast.Name)
            and of_predicate(sub.value)
        ):
            aliases.add(sub.targets[0].id)
    return aliases


def _resolve_callee(call: ast.Call, info: "_ModuleInfo") -> tuple[str, str] | None:
    """Resolve a Call's target to (origin_module_short, real_name) using
    `info`'s own import statements, or a same-module function definition.
    Returns None if unresolvable."""
    func = call.func
    if isinstance(func, ast.Name):
        if func.id in info.direct_name_to_origin:
            return info.direct_name_to_origin[func.id]
        if func.id in info.functions:
            return (info.short_name, func.id)
        return None
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        recv = func.value.id
        if recv in info.submodule_alias_to_module:
            return (info.submodule_alias_to_module[recv], func.attr)
        if recv == "ctx":
            # ctx.db.method(...) etc -- not a callee-resolution case; the
            # receiver IS the request session, handled by rule1, never rule3.
            return None
        return None
    return None


def _check_four_modules(modules: dict[str, _ModuleInfo], writers: set[tuple[str, str]]) -> dict:
    writer_names = {fname for _mod, fname in writers}
    total_aliases = 0
    total_call_sites = 0

    for mod_name in PLAY_MODULES:
        info = modules[mod_name]
        for fname, fnode in info.functions.items():
            db_aliases = _local_aliases_in_function(fnode, of_predicate=_is_ctx_db)
            conv_aliases = _local_aliases_in_function(fnode, of_predicate=_is_ctx_conv)
            total_aliases += len(db_aliases)

            def is_request_session_expr(node: ast.AST) -> bool:
                if _is_ctx_db(node):
                    return True
                if isinstance(node, ast.Name) and node.id in db_aliases:
                    return True
                return False

            def is_ctx_conv_expr(node: ast.AST) -> bool:
                if _is_ctx_conv(node):
                    return True
                if isinstance(node, ast.Name) and node.id in conv_aliases:
                    return True
                return False

            for sub in ast.walk(fnode):
                # rule4 -- no ctx.conv.<attr> = ... assignment.
                if isinstance(sub, ast.Assign):
                    for target in sub.targets:
                        if isinstance(target, ast.Attribute) and is_ctx_conv_expr(target.value):
                            fail(
                                f"{info.path}:{sub.lineno}: assignment to "
                                f"ctx.conv.{target.attr} (rule4) -- autoflush would emit "
                                f"an invisible UPDATE on the pinned request session"
                            )

                if not isinstance(sub, ast.Call):
                    continue

                # rule1 -- direct write on the request session.
                if (
                    isinstance(sub.func, ast.Attribute)
                    and sub.func.attr in WRITE_METHODS
                    and is_request_session_expr(sub.func.value)
                ):
                    fail(
                        f"{info.path}:{sub.lineno}: direct .{sub.func.attr}() on the "
                        f"request session (rule1)"
                    )
                    continue

                # rule2/rule3 -- passing the request session to a callee.
                args = list(sub.args) + [kw.value for kw in sub.keywords]
                if not any(is_request_session_expr(a) for a in args):
                    continue

                total_call_sites += 1
                resolved = _resolve_callee(sub, info)
                callee_repr = _call_target_name(sub) or "<unknown>"
                if resolved is None:
                    fail(
                        f"{info.path}:{sub.lineno}: request-session expression passed to "
                        f"unresolvable callee {callee_repr!r} (rule3) -- the declared module "
                        f"set does not account for this call"
                    )
                    continue
                origin_module, real_name = resolved
                if origin_module not in DECLARED_NAMES:
                    fail(
                        f"{info.path}:{sub.lineno}: request-session expression passed to "
                        f"{callee_repr!r}, resolved outside the declared module set "
                        f"({origin_module!r}) (rule3)"
                    )
                    continue
                if real_name in writer_names:
                    fail(
                        f"{info.path}:{sub.lineno}: request-session expression passed to "
                        f"writer {callee_repr!r} (rule2)"
                    )

    return {"aliases": total_aliases, "call_sites": total_call_sites}


def main() -> None:
    _rule6_no_exemption_mechanism()

    modules = _load_modules()
    if modules is None:
        _report_and_exit()
        return

    writers = _compute_writers(modules)
    if not writers:
        fail("WRITERS set is empty across the declared module set (rule5 vacuity guard)")
        _report_and_exit()
        return

    stats = _check_four_modules(modules, writers)

    if stats["aliases"] == 0:
        fail("alias map is empty across the four Play modules (rule5 vacuity guard)")
    if stats["call_sites"] == 0:
        fail("zero request-session call sites found across the four Play modules (rule5 vacuity guard)")

    if FAILURES:
        _report_and_exit()
        return

    _report_and_exit(
        {
            "modules": len(DECLARED_MODULES),
            "writers": len(writers),
            "aliases": stats["aliases"],
            "call_sites": stats["call_sites"],
        }
    )


if __name__ == "__main__":
    main()
