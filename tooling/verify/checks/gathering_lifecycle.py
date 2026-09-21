"""Structural gate for the gathering lifecycle (TICKET-0089, BRIEF-0089-g).

Briefs A, C and D of this lot put three verbs in place to stop a manually
relocated NPC from leaving a stale, unjoinable gathering behind: the entry
guard that ignores gatherings with no active member (a shell left by a
membership close, which would otherwise freeze a location for the rest of
the session because nothing dissolved it), the dissolve that closes a shell
the moment it forms, and the arrival that attaches a manually relocated NPC
to the destination's live gathering immediately, without waiting for a
fresh entry. Each of the three is a single call site that a later refactor
could quietly drop without any existing gate noticing. This check makes the
arrangement structural.

Rule 1: `routes/scene.py` declares `_live_gatherings`, and `enter_scene`'s
own body calls it and does not call `_open_gatherings` directly.
Rule 2: `_live_gatherings`'s own body calls `_active_members` — the roster
predicate is not re-expressed inline.
Rule 3: `gathering.py` declares both `dissolve_emptied` and
`attach_on_arrival`.
Rule 4: `migrate_npc` calls `dissolve_emptied` and contains no
`status = "dissolved"` assignment of its own (that responsibility belongs
to `dissolve_emptied` alone).
Rule 5: `crud/entities.py`'s `update_entity` calls `close_open_memberships`,
`dissolve_emptied` and `attach_on_arrival`.
Rule 6: `attach_on_arrival`'s own body does not call `_get_or_open_session`
— a manual arrival never opens a session on the NPC's behalf.

Every rule is vacuous-proof: a target file that does not parse, a function
that is not found, or a rule that collected zero call names is a FAILURE
with a message naming the file and the symbol — never a silent pass.

No DB, stdlib `ast` only.
"""
from __future__ import annotations

import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
SCENE_FILE = SRC / "world_engine" / "cockpit" / "routes" / "scene.py"
GATHERING_FILE = SRC / "world_engine" / "gathering.py"
CRUD_FILE = SRC / "world_engine" / "cockpit" / "crud" / "entities.py"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _parse(path: pathlib.Path):
    if not path.exists():
        fail(f"{path}: not found")
        return None
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        fail(f"{path}: SyntaxError: {exc}")
        return None


def _find_function(tree: ast.AST, name: str) -> ast.FunctionDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            return node
    return None


def _call_names(func: ast.FunctionDef) -> set[str]:
    return {
        node.func.id
        for node in ast.walk(func)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }


def check_enter_scene_uses_live_gatherings() -> None:
    tree = _parse(SCENE_FILE)
    if tree is None:
        return
    rel = SCENE_FILE.relative_to(ROOT).as_posix()

    live = _find_function(tree, "_live_gatherings")
    if live is None:
        fail(f"{rel}: _live_gatherings not found")
        return

    enter = _find_function(tree, "enter_scene")
    if enter is None:
        fail(f"{rel}: enter_scene not found")
        return

    calls = _call_names(enter)
    if not calls:
        fail(f"{rel}: enter_scene collected zero call names")
        return
    if "_live_gatherings" not in calls:
        fail(f"{rel}: enter_scene does not call _live_gatherings")
    if "_open_gatherings" in calls:
        fail(f"{rel}: enter_scene calls _open_gatherings directly; must go through _live_gatherings")


def check_live_gatherings_uses_active_members() -> None:
    tree = _parse(SCENE_FILE)
    if tree is None:
        return
    rel = SCENE_FILE.relative_to(ROOT).as_posix()

    live = _find_function(tree, "_live_gatherings")
    if live is None:
        fail(f"{rel}: _live_gatherings not found")
        return

    calls = _call_names(live)
    if not calls:
        fail(f"{rel}: _live_gatherings collected zero call names")
        return
    if "_active_members" not in calls:
        fail(f"{rel}: _live_gatherings does not call _active_members; roster predicate re-expressed")


def check_gathering_declares_verbs() -> None:
    tree = _parse(GATHERING_FILE)
    if tree is None:
        return
    rel = GATHERING_FILE.relative_to(ROOT).as_posix()

    for name in ("dissolve_emptied", "attach_on_arrival"):
        if _find_function(tree, name) is None:
            fail(f"{rel}: {name} not found")


def check_migrate_npc_delegates_dissolve() -> None:
    tree = _parse(GATHERING_FILE)
    if tree is None:
        return
    rel = GATHERING_FILE.relative_to(ROOT).as_posix()

    func = _find_function(tree, "migrate_npc")
    if func is None:
        fail(f"{rel}: migrate_npc not found")
        return

    calls = _call_names(func)
    if not calls:
        fail(f"{rel}: migrate_npc collected zero call names")
        return
    if "dissolve_emptied" not in calls:
        fail(f"{rel}: migrate_npc does not call dissolve_emptied")

    for node in ast.walk(func):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Attribute) and t.attr == "status" for t in node.targets
        ) and isinstance(node.value, ast.Constant) and node.value.value == "dissolved":
            fail(
                f"{rel}:{node.lineno} — migrate_npc assigns status = 'dissolved' itself; "
                "dissolution must route through dissolve_emptied alone"
            )


def check_update_entity_wires_all_three() -> None:
    tree = _parse(CRUD_FILE)
    if tree is None:
        return
    rel = CRUD_FILE.relative_to(ROOT).as_posix()

    func = _find_function(tree, "update_entity")
    if func is None:
        fail(f"{rel}: update_entity not found")
        return

    calls = _call_names(func)
    if not calls:
        fail(f"{rel}: update_entity collected zero call names")
        return
    for name in ("close_open_memberships", "dissolve_emptied", "attach_on_arrival"):
        if name not in calls:
            fail(f"{rel}: update_entity does not call {name}")


def check_attach_on_arrival_never_opens_session() -> None:
    tree = _parse(GATHERING_FILE)
    if tree is None:
        return
    rel = GATHERING_FILE.relative_to(ROOT).as_posix()

    func = _find_function(tree, "attach_on_arrival")
    if func is None:
        fail(f"{rel}: attach_on_arrival not found")
        return

    for node in ast.walk(func):
        if isinstance(node, ast.Name) and node.id == "_get_or_open_session":
            fail(f"{rel}:{node.lineno} — attach_on_arrival calls _get_or_open_session; a manual arrival must never open a session")
        if isinstance(node, ast.Attribute) and node.attr == "_get_or_open_session":
            fail(f"{rel}:{node.lineno} — attach_on_arrival calls _get_or_open_session; a manual arrival must never open a session")


def main() -> None:
    check_enter_scene_uses_live_gatherings()
    check_live_gatherings_uses_active_members()
    check_gathering_declares_verbs()
    check_migrate_npc_delegates_dissolve()
    check_update_entity_wires_all_three()
    check_attach_on_arrival_never_opens_session()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)
    print(
        "PASS: gathering_lifecycle — entry guard, dissolve and arrival wired "
        "(6 rules across scene.py, gathering.py, crud/entities.py)"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
