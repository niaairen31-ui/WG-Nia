"""Structural gate for the day-chain prompt delivery and coverage guard
(TICKET-0076, BRIEF-0076-a). Stdlib `ast` and text only, no DB — same
FAILURES/fail()/`_parse`/`_rel` idiom as `day_feasibility.py`.

R1: the 14 named `DAY_*` constants are module-level in `seed_pilot.py`, and
`seed()` contains no `Assign` to any of them.
R2: `DAY_PROMPT_HEADS` is module-level with exactly 8 entries, each a
`dict(...)` call carrying exactly the 8 required keys; the 8 `id` values
match the anchors from the brief's mini-RECON.
R3: `seed()` contains no `upsert_prompt_template` call whose `usage` starts
with `day_` — the loop over `DAY_PROMPT_HEADS` is the only seeding path.
R4: in `apply_ticket_0076_day_prompt_seed.py`, the only `str` constant longer
than 200 characters is the module docstring, and the file assigns no `DAY_*`
name.
R5: `prompt_coverage.py` contains no string literal equal to any
`PROMPT_REGISTRY` key except those inside the `DEGRADING_USAGES` assignment.
R6: recompute the exempt set by AST — for each `src/world_engine/day_*.py`
file carrying at least one day-chain usage (per `PROMPT_REGISTRY`), find its
"no active prompt_template" message(s) and classify the file as `Raise` or
`Return`. The `Return`-classified usages MUST equal `DEGRADING_USAGES`, and
the `Raise`-classified usages MUST equal `set(DAY_CHAIN_USAGES)`. This is the
rule that keeps the exemption honest — it does not merely restate R5.
R7: `missing_usages`'s body references `current_prompt` (E2 depth, via the
sole `prompt_version` read accessor — `prompt_version.py`'s allowlist bars a
direct `PromptVersion` reference from this module) and `PromptTemplate.is_active`.
R8: in `declare_day`, the `missing_usages` call appears strictly before the
`write_batch` call — compare statement positions, not mere co-presence.
R9: vacuity guard — any rule above that collected zero items is a FAILURE in
its own right, so a broken parse cannot silently report green.
"""

from __future__ import annotations

import ast
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

SEED_FILE = ROOT / "scripts" / "seed_pilot.py"
ONE_SHOT_FILE = ROOT / "scripts" / "apply_ticket_0076_day_prompt_seed.py"
COVERAGE_FILE = SRC / "prompt_coverage.py"
DAY_ROUTE_FILE = SRC / "cockpit" / "routes" / "day.py"
PROMPT_REGISTRY_FILE = SRC / "prompt_registry.py"

DAY_CONSTANTS = (
    "DAY_PLAN_SYSTEM_PROMPT", "DAY_PLAN_USER_TEMPLATE",
    "DAY_EXTRACT_PLACE_SYSTEM_PROMPT", "DAY_EXTRACT_PERSON_SYSTEM_PROMPT",
    "DAY_EXTRACT_FACTION_SYSTEM_PROMPT", "DAY_EXTRACT_USER_TEMPLATE",
    "DAY_NARRATION_SYSTEM_PROMPT", "DAY_NARRATION_USER_TEMPLATE",
    "DAY_REWRITE_SYSTEM_PROMPT", "DAY_REWRITE_USER_TEMPLATE",
    "DAY_FEASIBILITY_SYSTEM_PROMPT", "DAY_FEASIBILITY_USER_TEMPLATE",
    "DAY_RECONCILE_SYSTEM_PROMPT", "DAY_RECONCILE_USER_TEMPLATE",
)
REQUIRED_HEAD_KEYS = {
    "id", "name", "usage", "world_id", "system_prompt", "user_template",
    "variables", "destination",
}
EXPECTED_HEAD_IDS = {
    "pt-day-plan", "pt-day-extract-place", "pt-day-extract-person",
    "pt-day-extract-faction", "pt-day-narration", "pt-day-rewrite",
    "pt-day-feasibility", "pt-day-reconcile",
}
DEGRADING_USAGES = frozenset({"day_feasibility"})

FAILURES: list[str] = []
_ITEM_COUNTS: dict[str, int] = {}
_TREE_CACHE: dict[pathlib.Path, "ast.Module | None"] = {}
_SOURCE_CACHE: dict[pathlib.Path, str] = {}


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _rel(path: pathlib.Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _record(rule: str, count: int) -> None:
    _ITEM_COUNTS[rule] = _ITEM_COUNTS.get(rule, 0) + count


def _source(path: pathlib.Path) -> str:
    if path not in _SOURCE_CACHE:
        _SOURCE_CACHE[path] = path.read_text(encoding="utf-8")
    return _SOURCE_CACHE[path]


def _parse(path: pathlib.Path) -> "ast.Module | None":
    if path in _TREE_CACHE:
        return _TREE_CACHE[path]
    if not path.exists():
        fail(f"{_rel(path)}: file not found")
        _TREE_CACHE[path] = None
        return None
    try:
        tree = ast.parse(_source(path), filename=str(path))
    except SyntaxError as exc:
        fail(f"{_rel(path)}: SyntaxError: {exc}")
        tree = None
    _TREE_CACHE[path] = tree
    return tree


def _find_function(tree: ast.AST, name: str) -> "ast.FunctionDef | None":
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def check_constants_hoisted() -> None:
    """R1."""
    tree = _parse(SEED_FILE)
    if tree is None:
        return
    module_level = {
        node.targets[0].id
        for node in tree.body
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
    }
    found = [name for name in DAY_CONSTANTS if name in module_level]
    _record("R1", len(found))
    missing = set(DAY_CONSTANTS) - module_level
    for name in sorted(missing):
        fail(f"day_prompt_delivery R1: {_rel(SEED_FILE)}: {name!r} is not module-level")

    seed_fn = _find_function(tree, "seed")
    if seed_fn is None:
        fail(f"day_prompt_delivery R1: {_rel(SEED_FILE)}: seed() not found")
        return
    for node in ast.walk(seed_fn):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in DAY_CONSTANTS:
                    fail(
                        f"day_prompt_delivery R1: {_rel(SEED_FILE)}:{node.lineno} — "
                        f"seed() still assigns {target.id!r}"
                    )


def _dict_call_keys(node: ast.expr) -> "set[str] | None":
    if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "dict"):
        return None
    if node.args:
        return None
    return {kw.arg for kw in node.keywords if kw.arg is not None}


def check_day_prompt_heads() -> None:
    """R2."""
    tree = _parse(SEED_FILE)
    if tree is None:
        return
    heads_node = None
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            if node.targets[0].id == "DAY_PROMPT_HEADS":
                heads_node = node.value
                break
    if heads_node is None:
        fail(f"day_prompt_delivery R2: {_rel(SEED_FILE)}: DAY_PROMPT_HEADS is not module-level")
        return
    if not isinstance(heads_node, ast.Tuple):
        fail(f"day_prompt_delivery R2: {_rel(SEED_FILE)}: DAY_PROMPT_HEADS is not a tuple literal")
        return
    _record("R2", len(heads_node.elts))
    if len(heads_node.elts) != 8:
        fail(f"day_prompt_delivery R2: {_rel(SEED_FILE)}: DAY_PROMPT_HEADS has {len(heads_node.elts)} entries, expected 8")

    ids_found: set[str] = set()
    for elt in heads_node.elts:
        keys = _dict_call_keys(elt)
        if keys is None:
            fail(f"day_prompt_delivery R2: {_rel(SEED_FILE)}:{elt.lineno} — DAY_PROMPT_HEADS entry is not a dict(...) call")
            continue
        if keys != REQUIRED_HEAD_KEYS:
            fail(
                f"day_prompt_delivery R2: {_rel(SEED_FILE)}:{elt.lineno} — entry keys {sorted(keys)} "
                f"!= required {sorted(REQUIRED_HEAD_KEYS)}"
            )
            continue
        id_kw = next(kw.value for kw in elt.keywords if kw.arg == "id")
        if isinstance(id_kw, ast.Constant) and isinstance(id_kw.value, str):
            ids_found.add(id_kw.value)

    if ids_found != EXPECTED_HEAD_IDS:
        fail(
            f"day_prompt_delivery R2: {_rel(SEED_FILE)}: DAY_PROMPT_HEADS ids {sorted(ids_found)} "
            f"!= expected {sorted(EXPECTED_HEAD_IDS)}"
        )


def check_seed_loop_only() -> None:
    """R3."""
    tree = _parse(SEED_FILE)
    if tree is None:
        return
    seed_fn = _find_function(tree, "seed")
    if seed_fn is None:
        fail(f"day_prompt_delivery R3: {_rel(SEED_FILE)}: seed() not found")
        return
    found_any = 0
    for node in ast.walk(seed_fn):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "upsert_prompt_template":
            found_any += 1
            usage_kw = next((kw for kw in node.keywords if kw.arg == "usage"), None)
            if usage_kw is not None and isinstance(usage_kw.value, ast.Constant) and isinstance(usage_kw.value.value, str):
                if usage_kw.value.value.startswith("day_"):
                    fail(
                        f"day_prompt_delivery R3: {_rel(SEED_FILE)}:{node.lineno} — literal "
                        f"upsert_prompt_template(usage={usage_kw.value.value!r}) call inside seed()"
                    )
    _record("R3", found_any)


def check_one_shot_embeds_nothing() -> None:
    """R4."""
    tree = _parse(ONE_SHOT_FILE)
    if tree is None:
        return
    docstring_node = None
    if tree.body and isinstance(tree.body[0], ast.Expr) and isinstance(tree.body[0].value, ast.Constant) and isinstance(tree.body[0].value.value, str):
        docstring_node = tree.body[0].value

    long_strings = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and len(node.value) > 200:
            if node is docstring_node:
                continue
            long_strings += 1
            fail(
                f"day_prompt_delivery R4: {_rel(ONE_SHOT_FILE)}:{node.lineno} — string constant "
                f"of {len(node.value)} chars besides the module docstring"
            )
    _record("R4", 1 if docstring_node is not None else 0)
    if docstring_node is None:
        fail(f"day_prompt_delivery R4: {_rel(ONE_SHOT_FILE)}: module has no docstring")

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in DAY_CONSTANTS:
                    fail(f"day_prompt_delivery R4: {_rel(ONE_SHOT_FILE)}:{node.lineno} — assigns {target.id!r}")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for arg in node.args.args + node.args.kwonlyargs:
                if arg.arg in DAY_CONSTANTS:
                    fail(f"day_prompt_delivery R4: {_rel(ONE_SHOT_FILE)}:{node.lineno} — parameter named {arg.arg!r}")


def _registry_dict_node(tree: ast.Module) -> "ast.Dict | None":
    for node in ast.walk(tree):
        target_name = None
        value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name, value = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name, value = node.target.id, node.value
        if target_name == "PROMPT_REGISTRY" and isinstance(value, ast.Dict):
            return value
    return None


def _registry_usages() -> "dict[str, tuple[str, ...]] | None":
    """usage -> call_sites tuple, read statically from prompt_registry.py."""
    tree = _parse(PROMPT_REGISTRY_FILE)
    if tree is None:
        return None
    reg = _registry_dict_node(tree)
    if reg is None:
        fail(f"day_prompt_delivery: {_rel(PROMPT_REGISTRY_FILE)}: PROMPT_REGISTRY dict not found")
        return None
    result: dict[str, tuple[str, ...]] = {}
    for key, value in zip(reg.keys, reg.values):
        if not (isinstance(key, ast.Constant) and isinstance(key.value, str)):
            continue
        if not isinstance(value, ast.Call):
            continue
        call_sites_kw = next((kw for kw in value.keywords if kw.arg == "call_sites"), None)
        if call_sites_kw is None or not isinstance(call_sites_kw.value, ast.Tuple):
            continue
        sites = tuple(
            elt.value for elt in call_sites_kw.value.elts
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
        )
        result[key.value] = sites
    return result


def check_coverage_no_literal_usages() -> None:
    """R5."""
    registry = _registry_usages()
    if registry is None:
        return
    registry_keys = set(registry.keys())

    tree = _parse(COVERAGE_FILE)
    if tree is None:
        return

    allowed_ids: set[int] = set()
    for node in tree.body:
        target_name = None
        value = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            target_name, value = node.targets[0].id, node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_name, value = node.target.id, node.value
        if target_name == "DEGRADING_USAGES" and value is not None:
            for sub in ast.walk(value):
                allowed_ids.add(id(sub))

    found_any = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            found_any += 1
            if node.value in registry_keys and id(node) not in allowed_ids:
                fail(
                    f"day_prompt_delivery R5: {_rel(COVERAGE_FILE)}:{node.lineno} — literal "
                    f"{node.value!r} equals a PROMPT_REGISTRY key outside DEGRADING_USAGES"
                )
    _record("R5", found_any)


_DAY_FILE_RE = re.compile(r"^src/world_engine/day_[a-z_]+\.py$")


def check_exemption_matches_code() -> None:
    """R6."""
    registry = _registry_usages()
    if registry is None:
        return

    # usage -> file, restricted to day_*.py call sites.
    usage_to_file: dict[str, pathlib.Path] = {}
    for usage, sites in registry.items():
        for site in sites:
            rel_path = site.split(":", 1)[0]
            if _DAY_FILE_RE.match(rel_path):
                usage_to_file[usage] = ROOT / rel_path
                break

    _record("R6-usages", len(usage_to_file))
    if not usage_to_file:
        fail("day_prompt_delivery R6: no day-chain usage resolved to a day_*.py call site — vacuous")
        return

    files_to_usages: dict[pathlib.Path, set[str]] = {}
    for usage, path in usage_to_file.items():
        files_to_usages.setdefault(path, set()).add(usage)

    raise_usages: set[str] = set()
    return_usages: set[str] = set()
    for path, usages in files_to_usages.items():
        tree = _parse(path)
        if tree is None:
            continue
        source = _source(path)
        has_raise = False
        has_return = False
        for node in ast.walk(tree):
            if isinstance(node, (ast.Raise, ast.Return)):
                segment = ast.get_source_segment(source, node) or ""
                if "no active prompt_template" in segment:
                    if isinstance(node, ast.Raise):
                        has_raise = True
                    else:
                        has_return = True
        if has_raise:
            raise_usages |= usages
        if has_return:
            return_usages |= usages
        if not has_raise and not has_return:
            fail(f"day_prompt_delivery R6: {_rel(path)}: no 'no active prompt_template' Raise/Return found")

    _record("R6-raise", len(raise_usages))
    _record("R6-return", len(return_usages))

    if return_usages != DEGRADING_USAGES:
        fail(
            f"day_prompt_delivery R6: Return-classified usages {sorted(return_usages)} "
            f"!= DEGRADING_USAGES {sorted(DEGRADING_USAGES)}"
        )
    expected_raise = set(usage_to_file.keys()) - DEGRADING_USAGES
    if raise_usages != expected_raise:
        fail(
            f"day_prompt_delivery R6: Raise-classified usages {sorted(raise_usages)} "
            f"!= expected {sorted(expected_raise)}"
        )


def check_missing_usages_depth() -> None:
    """R7."""
    tree = _parse(COVERAGE_FILE)
    if tree is None:
        return
    fn = _find_function(tree, "missing_usages")
    if fn is None:
        fail(f"day_prompt_delivery R7: {_rel(COVERAGE_FILE)}: missing_usages not found")
        return
    references_current_prompt = False
    references_is_active = False
    found_any = 0
    for node in ast.walk(fn):
        if isinstance(node, ast.Name):
            found_any += 1
            if node.id == "current_prompt":
                references_current_prompt = True
        if isinstance(node, ast.Attribute):
            found_any += 1
            if node.attr == "is_active":
                references_is_active = True
    _record("R7", found_any)
    if not references_current_prompt:
        fail(f"day_prompt_delivery R7: {_rel(COVERAGE_FILE)}: missing_usages never references current_prompt")
    if not references_is_active:
        fail(f"day_prompt_delivery R7: {_rel(COVERAGE_FILE)}: missing_usages never references .is_active")


def check_guard_before_write_batch() -> None:
    """R8. Call ORDER inside declare_day, not merely presence."""
    tree = _parse(DAY_ROUTE_FILE)
    if tree is None:
        return
    fn = _find_function(tree, "declare_day")
    if fn is None:
        fail(f"day_prompt_delivery R8: {_rel(DAY_ROUTE_FILE)}: declare_day not found")
        return
    missing_line = None
    write_batch_line = None
    for node in ast.walk(fn):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)):
            continue
        if node.func.id == "missing_usages" and missing_line is None:
            missing_line = node.lineno
        if node.func.id == "write_batch" and write_batch_line is None:
            write_batch_line = node.lineno
    _record("R8", int(missing_line is not None) + int(write_batch_line is not None))
    if missing_line is None:
        fail(f"day_prompt_delivery R8: {_rel(DAY_ROUTE_FILE)}: declare_day does not call missing_usages(")
        return
    if write_batch_line is None:
        fail(f"day_prompt_delivery R8: {_rel(DAY_ROUTE_FILE)}: declare_day does not call write_batch(")
        return
    if not (missing_line < write_batch_line):
        fail(
            f"day_prompt_delivery R8: {_rel(DAY_ROUTE_FILE)}: missing_usages( at line {missing_line} "
            f"does not come before write_batch( at line {write_batch_line}"
        )


def check_vacuity() -> None:
    """R9."""
    for rule, count in _ITEM_COUNTS.items():
        if count == 0:
            fail(f"day_prompt_delivery R9: rule {rule} collected zero items — vacuous")


def main() -> None:
    check_constants_hoisted()
    check_day_prompt_heads()
    check_seed_loop_only()
    check_one_shot_embeds_nothing()
    check_coverage_no_literal_usages()
    check_exemption_matches_code()
    check_missing_usages_depth()
    check_guard_before_write_batch()
    check_vacuity()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: day_prompt_delivery — the 14 DAY_* constants are module-level, DAY_PROMPT_HEADS "
        "is the single seeding source, the one-shot embeds no text, prompt_coverage derives "
        "usages with no literal restatement, the day_feasibility exemption matches the code's "
        "actual Raise/Return shape, missing_usages checks E2 depth, and the guard runs before "
        "write_batch"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
