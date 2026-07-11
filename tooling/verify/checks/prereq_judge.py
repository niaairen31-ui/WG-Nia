"""G1 gate: `_apply_mutation`'s `goal_change complete` branch rejects when
a `relation_gte` prerequisite is unmet, with an error string carrying the
current and required values (G1, TICKET-0024, BRIEF-0024-b).

No DB, plain text scan of `app.py`.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
APP = ROOT / "src" / "world_engine" / "cockpit" / "app.py"


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def _goal_change_branch(src: str) -> str:
    fn_start = src.find("def _apply_mutation(")
    if fn_start == -1:
        fail("_apply_mutation not found")
    next_def = re.search(r"\ndef \w", src[fn_start + 1:])
    fn_end = fn_start + 1 + next_def.start() if next_def else len(src)
    fn_body = src[fn_start:fn_end]

    start = fn_body.find('elif mut.mutation_type == "goal_change":')
    if start == -1:
        fail("goal_change branch not found in _apply_mutation")
    later_branches = [
        m.start() for m in re.finditer(r'\n    elif mut\.mutation_type == "', fn_body)
        if m.start() > start
    ]
    end = later_branches[0] if later_branches else len(fn_body)
    return fn_body[start:end]


def main():
    if not APP.exists():
        fail(f"{APP} not found")
    src = APP.read_text(encoding="utf-8")
    branch = _goal_change_branch(src)

    if 'action == "complete" and goal.prerequisites' not in branch:
        fail("no complete-only prerequisite gate found in the goal_change branch")
    if "relation_gte" not in branch:
        fail("goal_change branch does not reference relation_gte")
    if "prerequisite not met" not in branch:
        fail("no 'prerequisite not met' reject message in the goal_change branch")
    if "requires >=" not in branch:
        fail("reject message does not carry the required value")
    if "unknown prerequisite type" not in branch:
        fail("no fail-closed reject for an unrecognised prerequisite type")

    print("PASS: goal_change complete rejects an unmet relation_gte prerequisite with current/required values")
    sys.exit(0)


if __name__ == "__main__":
    main()
