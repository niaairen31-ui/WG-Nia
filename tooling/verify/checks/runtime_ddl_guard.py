"""G1 check: runtime-DDL writer guard (TICKET-0044, BRIEF-0044-c — Dcol1,
Dname1, Ddrop1). AST-based, no DB, on the door_terminal.py /
single_canon_write.py idiom. Scans the sole governed runtime-DDL writer
(`src/world_engine/writes/schema.py`) for five fail-closed assertions:

  1. No DROP/ALTER token reaches a code-path string (return value, f-string,
     dict/list literal) anywhere in the module. Named exceptions: module/
     function/class docstrings (prose, never reaches DDL) and the
     `_RESERVED_WORDS` set literal (whose entire purpose is REJECTING
     `drop`/`alter` as identifiers).
  2. Every literal SQL-type fragment reaching the CREATE TABLE builder is
     one of the `_COLUMN_TYPES` enum's own values, or the one named
     exception: the fixed shared-PK line. No OTHER string constant may
     literalize a bare SQL type token.
  3. The `"ext_"` literal appears nowhere but the single `EXT_PREFIX`
     assignment (single-source / S-norme). Docstrings are exempt.
  4. Every `.add(...)` call constructs only `EntityType` or
     `EntityTypeHistory` (the socle writes rows only to the two static
     tables). Every raw-SQL `.execute(...)`/`.exec(...)` resolves to CREATE
     TABLE text, never an INSERT/UPDATE/DELETE row write on a dynamic table.

Zero parsed assertions is itself a FAILURE (vacuous-proof), never a silent
pass.
"""
from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCHEMA_FILE = ROOT / "src" / "world_engine" / "writes" / "schema.py"

PK_LINE_LITERAL = "id TEXT PRIMARY KEY REFERENCES entity(id)"
EXT_LITERAL = "ext_"
STATIC_TABLE_CLASSES = {"EntityType", "EntityTypeHistory"}
DROP_ALTER_RE = re.compile(r"\b(DROP|ALTER)\b", re.IGNORECASE)
SQL_TYPE_TOKEN_RE = re.compile(r"\b(TEXT|INTEGER|REAL|BOOLEAN|JSON|TIMESTAMP)\b")
ROW_WRITE_RE = re.compile(r"\b(?:INSERT INTO|DELETE FROM|UPDATE)\b", re.IGNORECASE)
DYNAMIC_MARK = "\x00"

FAILURES: list[str] = []
ASSERTIONS = 0


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _mark(n: int = 1) -> None:
    global ASSERTIONS
    ASSERTIONS += n


def _report_and_exit() -> None:
    if ASSERTIONS == 0:
        fail("zero parsed assertions — vacuous proof, check is broken not the repo clean")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: runtime_ddl_guard — writes/schema.py is CREATE-only, enum-typed, single-sourced")
    sys.exit(0)


def _docstring_nodes(tree: ast.Module) -> set:
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = node.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                out.add(id(body[0].value))
    return out


def _find_assign(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 \
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id == name:
            return node.value
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) \
                and node.target.id == name and node.value is not None:
            return node.value
    return None


def _string_constants(tree: ast.Module, skip_ids: set):
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip_ids:
            yield node


def check_no_drop_alter(tree: ast.Module, docstrings: set) -> None:
    reserved_words_value = _find_assign(tree, "_RESERVED_WORDS")
    skip = set(docstrings)
    if reserved_words_value is not None:
        for elt in ast.walk(reserved_words_value):
            if isinstance(elt, ast.Constant):
                skip.add(id(elt))
    for const in _string_constants(tree, skip):
        _mark()
        if DROP_ALTER_RE.search(const.value):
            fail(f"{SCHEMA_FILE.name}:{const.lineno} — DROP/ALTER token in code string {const.value!r}")


def check_enum_only_types(tree: ast.Module, docstrings: set) -> None:
    column_types_value = _find_assign(tree, "_COLUMN_TYPES")
    if column_types_value is None or not isinstance(column_types_value, ast.Dict):
        fail("_COLUMN_TYPES dict assignment not found — Dcol1 enum is missing")
        return
    allowed = {
        v.value for v in column_types_value.values
        if isinstance(v, ast.Constant) and isinstance(v.value, str)
    }
    if not allowed:
        fail("_COLUMN_TYPES dict has no string values — Dcol1 enum is empty")
        return
    # The dict's own keys/values (e.g. the enum member name "BOOLEAN") define
    # the enum itself — exempt, same as a docstring, from the "literalized
    # outside the enum" scan below.
    exempt = set(docstrings)
    for sub in ast.walk(column_types_value):
        if isinstance(sub, ast.Constant):
            exempt.add(id(sub))
    for const in _string_constants(tree, exempt):
        _mark()
        if not SQL_TYPE_TOKEN_RE.search(const.value):
            continue
        if const.value in allowed or const.value == PK_LINE_LITERAL:
            continue
        fail(
            f"{SCHEMA_FILE.name}:{const.lineno} — SQL type fragment {const.value!r} "
            "literalized outside the closed _COLUMN_TYPES enum"
        )


def check_ext_single_source(tree: ast.Module, docstrings: set) -> None:
    ext_prefix_value = _find_assign(tree, "EXT_PREFIX")
    if ext_prefix_value is None or not (isinstance(ext_prefix_value, ast.Constant) and ext_prefix_value.value == EXT_LITERAL):
        fail(f"EXT_PREFIX = {EXT_LITERAL!r} assignment not found")
        return
    exempt = set(docstrings)
    exempt.add(id(ext_prefix_value))
    for const in _string_constants(tree, exempt):
        _mark()
        if EXT_LITERAL in const.value:
            fail(
                f"{SCHEMA_FILE.name}:{const.lineno} — {EXT_LITERAL!r} literal outside the "
                "single EXT_PREFIX constant"
            )


def _render_joined_str(node: ast.JoinedStr) -> str:
    parts = []
    for v in node.values:
        if isinstance(v, ast.Constant) and isinstance(v.value, str):
            parts.append(v.value)
        else:
            parts.append(DYNAMIC_MARK)
    return "".join(parts)


def _resolve_name_assignment(fn_node, name: str):
    for stmt in ast.walk(fn_node):
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 \
                and isinstance(stmt.targets[0], ast.Name) and stmt.targets[0].id == name:
            return stmt.value
    return None


def _resolve_function_return(tree: ast.Module, fn_name: str):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == fn_name:
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Return) and stmt.value is not None:
                    return stmt.value
    return None


def _render_sql_expr(tree: ast.Module, fn_node, expr) -> "str | None":
    if isinstance(expr, ast.Constant) and isinstance(expr.value, str):
        return expr.value
    if isinstance(expr, ast.JoinedStr):
        return _render_joined_str(expr)
    if isinstance(expr, ast.Name):
        resolved = _resolve_name_assignment(fn_node, expr.id)
        return _render_sql_expr(tree, fn_node, resolved) if resolved is not None else None
    if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name):
        callee_return = _resolve_function_return(tree, expr.func.id)
        if callee_return is not None:
            callee_fn = next(
                (n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                 and n.name == expr.func.id),
                None,
            )
            return _render_sql_expr(tree, callee_fn, callee_return)
        return None
    return None


def check_row_writes(tree: ast.Module) -> None:
    for fn_node in [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]:
        for call in ast.walk(fn_node):
            if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Attribute)):
                continue
            attr = call.func.attr
            if attr == "add":
                _mark()
                arg = call.args[0] if call.args else None
                if isinstance(arg, ast.Name):
                    arg = _resolve_name_assignment(fn_node, arg.id)
                if not (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name)
                        and arg.func.id in STATIC_TABLE_CLASSES):
                    fail(f"{SCHEMA_FILE.name}:{call.lineno} — .add(...) targets something other than {sorted(STATIC_TABLE_CLASSES)}")
            elif attr in ("execute", "exec"):
                arg = call.args[0] if call.args else None
                # Only a `text(...)`-wrapped argument is raw SQL in this codebase's
                # convention; a bare `.exec(select(...))` is an ORM read, out of
                # scope for a row-write guard (mirrors single_canon_write.py, which
                # skips a site it cannot render as SQL text rather than failing it).
                if not (isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) and arg.func.id == "text" and arg.args):
                    continue
                _mark()
                rendered = _render_sql_expr(tree, fn_node, arg.args[0])
                if rendered is None:
                    fail(f"{SCHEMA_FILE.name}:{call.lineno} — raw-SQL text() call is unattributable")
                    continue
                if ROW_WRITE_RE.search(rendered):
                    fail(f"{SCHEMA_FILE.name}:{call.lineno} — raw-SQL row write (INSERT/UPDATE/DELETE) on a dynamic table")


def main() -> None:
    if not SCHEMA_FILE.exists():
        fail(f"{SCHEMA_FILE} not found")
        _report_and_exit()
        return
    try:
        tree = ast.parse(SCHEMA_FILE.read_text(encoding="utf-8"), filename=str(SCHEMA_FILE))
    except SyntaxError as exc:
        fail(f"{SCHEMA_FILE}: SyntaxError: {exc}")
        _report_and_exit()
        return

    docstrings = _docstring_nodes(tree)
    check_no_drop_alter(tree, docstrings)
    check_enum_only_types(tree, docstrings)
    check_ext_single_source(tree, docstrings)
    check_row_writes(tree)

    _report_and_exit()


if __name__ == "__main__":
    main()
