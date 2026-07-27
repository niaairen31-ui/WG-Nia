"""G1 check: no scripts/*.py reaches the engine without an env resolvable
at import time (TICKET-0049, BRIEF-0049-d).

AST-only, same discipline as `import_cycle.py` — never imports or executes
a script that might touch a DB. For every `scripts/*.py` that imports
`world_engine.db` (naming `engine` / `create_db_and_tables`, or
`from world_engine import db`), this check requires that, lexically BEFORE
that import in module top-level order, the script either:

  (a) sets `os.environ["WORLD_ENGINE_ENV"]` or
      `os.environ["WORLD_ENGINE_DATABASE_URL"]` explicitly, or
  (b) carries a fail-closed guard: reads `os.environ.get("WORLD_ENGINE_ENV")`
      and calls `sys.exit` before the import.

Scripts that don't import the engine are out of scope (skipped, not
failed). `KNOWN_OPERATOR_SCRIPT_ALLOW` below is the single declared
exception set (TICKET-0049 escalation, `tooling/questions/
QUESTION-TICKET-0049.md`, Nia 2026-07-27, option A): one-shot migrations,
one-shot ticket-apply scripts, and standing operator tools that predate
this ticket and are no longer in active use — allow-listed rather than
retrofitted, by Nia's explicit call. Extending this list requires the same
judgment call, not a rubber stamp.

Vacuous-proof: zero `scripts/*.py` found, or zero engine-importing scripts
found, is a FAILURE, never a silent pass.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"

_MIGRATION_RATIONALE = (
    "one-time historical migration, already applied, no longer run "
    "(TICKET-0049 escalation, Nia 2026-07-27: not in active use)"
)
_TICKET_APPLY_RATIONALE = (
    "one-shot historical ticket-apply script, already applied, no longer run "
    "(TICKET-0049 escalation, Nia 2026-07-27: not in active use)"
)
_OPERATOR_RATIONALE = (
    "operator-run tool, gated by env export at the shell, not a test harness "
    "(TICKET-0049 escalation, Nia 2026-07-27: not in active use)"
)

KNOWN_OPERATOR_SCRIPT_ALLOW: dict[str, str] = {
    "seed_pilot.py": (
        "creator-run pilot seed against prod, gated by operator, not a "
        "test harness"
    ),
    "analyze_conversation.py": _OPERATOR_RATIONALE,
    "backup.py": _OPERATOR_RATIONALE,
    "init_db.py": _OPERATOR_RATIONALE,
    "preview_tick_context.py": _OPERATOR_RATIONALE,
    "rollback_quarantine.py": _OPERATOR_RATIONALE,
    "seed_trait_keys.py": _OPERATOR_RATIONALE,
    "talk.py": _OPERATOR_RATIONALE,
    "apply_ticket_0012_prompt_rewrite.py": _TICKET_APPLY_RATIONALE,
    "apply_ticket_0013_prompt_updates.py": _TICKET_APPLY_RATIONALE,
    "apply_ticket_0014_prompt_updates.py": _TICKET_APPLY_RATIONALE,
    "apply_ticket_0015_prompt_updates.py": _TICKET_APPLY_RATIONALE,
    "apply_ticket_0016_prompt_updates.py": _TICKET_APPLY_RATIONALE,
    "apply_ticket_0017_prompt_updates.py": _TICKET_APPLY_RATIONALE,
    "apply_ticket_0018_prompt_updates.py": _TICKET_APPLY_RATIONALE,
    "apply_ticket_0019_prompt_updates.py": _TICKET_APPLY_RATIONALE,
    "apply_ticket_0020_prompt_updates.py": _TICKET_APPLY_RATIONALE,
    "apply_ticket_0024_prompt_updates.py": _TICKET_APPLY_RATIONALE,
    "migrate_v1_8_gatherings.py": _MIGRATION_RATIONALE,
    "migrate_v1_16_knowledge_history.py": _MIGRATION_RATIONALE,
    "migrate_v1_21_window_analysis.py": _MIGRATION_RATIONALE,
    "migrate_v1_24.py": _MIGRATION_RATIONALE,
    "migrate_v1_26.py": _MIGRATION_RATIONALE,
    "migrate_v1_30.py": _MIGRATION_RATIONALE,
    "migrate_v1_31_ledger.py": _MIGRATION_RATIONALE,
    "migrate_v1_38_faction_structure.py": _MIGRATION_RATIONALE,
    "migrate_v1_39_faction_membership.py": _MIGRATION_RATIONALE,
    "migrate_v1_40_drop_character_faction_id.py": _MIGRATION_RATIONALE,
    "migrate_v1_41_cover_role.py": _MIGRATION_RATIONALE,
    "migrate_v1_44_aversion.py": _MIGRATION_RATIONALE,
    "migrate_v1_54.py": _MIGRATION_RATIONALE,
    "migrate_v1_57.py": _MIGRATION_RATIONALE,
    "migrate_v1_63.py": _MIGRATION_RATIONALE,
    "migrate_v1_65_pc_skill_backfill.py": _MIGRATION_RATIONALE,
    "migrate_v1_67_prompt_model.py": _MIGRATION_RATIONALE,
    "migrate_v1_68_prompt_version.py": _MIGRATION_RATIONALE,
    "migrate_v1_69_npc_goal.py": _MIGRATION_RATIONALE,
    "migrate_v1_70_tick_id.py": _MIGRATION_RATIONALE,
    "migrate_v1_71_visit.py": _MIGRATION_RATIONALE,
    "migrate_v1_72_agenda.py": _MIGRATION_RATIONALE,
    "migrate_v1_73_goal_agenda_link.py": _MIGRATION_RATIONALE,
    "migrate_v1_74_completion_mechanics.py": _MIGRATION_RATIONALE,
    "migrate_v1_76_faction_role_table.py": _MIGRATION_RATIONALE,
    "migrate_v1_77_metadata_extraction.py": _MIGRATION_RATIONALE,
    "migrate_v1_78_dedicated_json_columns.py": _MIGRATION_RATIONALE,
    "migrate_v1_79_structured_editor_tables.py": _MIGRATION_RATIONALE,
    "migrate_v1_80_obstacle_geometry.py": _MIGRATION_RATIONALE,
    "migrate_v1_81_door_geometry.py": _MIGRATION_RATIONALE,
    "migrate_v1_82_link_batch.py": _MIGRATION_RATIONALE,
    "migrate_v1_83_npc_batch.py": _MIGRATION_RATIONALE,
    "migrate_v1_84_location_type_catalog.py": _MIGRATION_RATIONALE,
    "migrate_v1_85_location_type_templates.py": _MIGRATION_RATIONALE,
    "migrate_v1_86_schema_meta.py": _MIGRATION_RATIONALE,
    "migrate_v1_87_entity_type.py": _MIGRATION_RATIONALE,
    "migrate_v1_88_entity_trait.py": _MIGRATION_RATIONALE,
}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _report_and_exit() -> None:
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print("PASS: env_guard — every non-allow-listed script guards the engine import")
    sys.exit(0)


def _imports_engine(node: ast.stmt) -> bool:
    if isinstance(node, ast.ImportFrom):
        if node.module == "world_engine.db" and any(
            a.name in ("engine", "create_db_and_tables", "*") for a in node.names
        ):
            return True
        if node.module == "world_engine" and any(a.name == "db" for a in node.names):
            return True
    if isinstance(node, ast.Import):
        if any(a.name == "world_engine.db" for a in node.names):
            return True
    return False


def _sets_env_var(node: ast.stmt) -> bool:
    if not isinstance(node, ast.Assign):
        return False
    for target in node.targets:
        if (
            isinstance(target, ast.Subscript)
            and isinstance(target.value, ast.Attribute)
            and target.value.attr == "environ"
            and isinstance(target.value.value, ast.Name)
            and target.value.value.id == "os"
        ):
            key = target.slice
            if isinstance(key, ast.Constant) and key.value in (
                "WORLD_ENGINE_ENV",
                "WORLD_ENGINE_DATABASE_URL",
            ):
                return True
    return False


def _reads_env_get(node: ast.stmt) -> bool:
    if not isinstance(node, ast.Assign):
        return False
    value = node.value
    return (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Attribute)
        and value.func.attr == "get"
        and isinstance(value.func.value, ast.Attribute)
        and value.func.value.attr == "environ"
        and isinstance(value.func.value.value, ast.Name)
        and value.func.value.value.id == "os"
        and len(value.args) >= 1
        and isinstance(value.args[0], ast.Constant)
        and value.args[0].value == "WORLD_ENGINE_ENV"
    )


def _calls_sys_exit(node: ast.stmt) -> bool:
    for sub in ast.walk(node):
        if (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Attribute)
            and sub.func.attr == "exit"
            and isinstance(sub.func.value, ast.Name)
            and sub.func.value.id == "sys"
        ):
            return True
    return False


def _has_guard(prefix: list[ast.stmt]) -> bool:
    has_env_get = any(_reads_env_get(stmt) for stmt in prefix)
    has_exit = any(_calls_sys_exit(stmt) for stmt in prefix)
    return has_env_get and has_exit


def main() -> None:
    py_files = sorted(SCRIPTS.glob("*.py"))
    if not py_files:
        fail("zero scripts/*.py files found — parse is broken, not the repo clean")
        _report_and_exit()
        return

    engine_importing_count = 0

    for path in py_files:
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError as exc:
            fail(f"{path.name}: SyntaxError: {exc}")
            continue

        import_index = next(
            (i for i, node in enumerate(tree.body) if _imports_engine(node)), None
        )
        if import_index is None:
            continue  # out of scope: doesn't import the engine

        engine_importing_count += 1

        if path.name in KNOWN_OPERATOR_SCRIPT_ALLOW:
            continue

        prefix = tree.body[:import_index]
        if any(_sets_env_var(stmt) for stmt in prefix):
            continue
        if _has_guard(prefix):
            continue

        fail(
            f"{path.name}: imports the engine at line "
            f"{tree.body[import_index].lineno} with no env set and no "
            "fail-closed guard before it"
        )

    if engine_importing_count == 0:
        fail("zero engine-importing scripts found under scripts/ — check is vacuous")

    _report_and_exit()


if __name__ == "__main__":
    main()
