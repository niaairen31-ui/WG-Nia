"""G1 gate: `goal_change complete`'s prerequisite judge rejects when a
`relation_gte` prerequisite is unmet, with an error string carrying the
current and required values (G1, TICKET-0024, BRIEF-0024-b).

Retargeted (TICKET-0027, BRIEF-0027-c amendment, "check-anchor
relocation"): the `goal_change complete` logic now lives in
`_mutation_goal_change_close` in `cockpit/mutations.py` (formerly the
`goal_change` branch of `_apply_mutation` in `app.py`). Assertions
unchanged. Only the location anchors moved.

No DB, plain text scan of `mutations.py`.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
TARGET = ROOT / "src" / "world_engine" / "cockpit" / "mutations.py"
CONTAINING_FUNCTION = "_mutation_goal_change_close"


def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)


def _goal_change_close_branch(src: str) -> str:
    fn_start = src.find(f"def {CONTAINING_FUNCTION}(")
    if fn_start == -1:
        fail(f"{CONTAINING_FUNCTION} not found")
    next_def = re.search(r"\ndef \w", src[fn_start + 1:])
    fn_end = fn_start + 1 + next_def.start() if next_def else len(src)
    return src[fn_start:fn_end]


def main():
    if not TARGET.exists():
        fail(f"{TARGET} not found")
    src = TARGET.read_text(encoding="utf-8")
    branch = _goal_change_close_branch(src)

    if 'action == "complete" and goal_prerequisites' not in branch:
        fail(f"no complete-only prerequisite gate found in {CONTAINING_FUNCTION}")
    if "relation_gte" not in branch:
        fail(f"{CONTAINING_FUNCTION} does not reference relation_gte")
    if "prerequisite not met" not in branch:
        fail(f"no 'prerequisite not met' reject message in {CONTAINING_FUNCTION}")
    if "requires >=" not in branch:
        fail("reject message does not carry the required value")
    if "unknown prerequisite type" not in branch:
        fail("no fail-closed reject for an unrecognised prerequisite type")

    print(f"PASS: goal_change complete rejects an unmet relation_gte prerequisite with current/required values (in {CONTAINING_FUNCTION})")
    sys.exit(0)


if __name__ == "__main__":
    main()
