"""G1 gate: the H1 partial-application strip exists ONLY inside the
`goal_change complete` path — the project's one sanctioned exception to
all-or-nothing mutation apply (TICKET-0024, BRIEF-0024-c). No other
branch of `_apply_mutation` may strip an effect.

No DB, plain text scan of `app.py`.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
APP = ROOT / "src" / "world_engine" / "cockpit" / "app.py"

HELPER = "_h1_strip_satisfied_prerequisite_deltas"


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

    if src.count(f"def {HELPER}(") != 1:
        fail(f"expected exactly 1 definition of {HELPER}")

    call_positions = [
        m.start() for m in re.finditer(re.escape(HELPER) + r"\(", src)
    ]
    def_position = src.find(f"def {HELPER}(") + len("def ")
    call_sites = [p for p in call_positions if p != def_position]
    if len(call_sites) != 1:
        fail(f"expected exactly 1 call site for {HELPER}, found {len(call_sites)}")

    branch = _goal_change_branch(src)
    branch_start = src.find(branch)
    branch_end = branch_start + len(branch)
    if not (branch_start <= call_sites[0] < branch_end):
        fail(f"{HELPER} is called outside the goal_change branch")

    if "H1 (TICKET-0024)" not in src:
        fail("missing the H1 verbatim comment at the strip site")
    if "stripped: relation_delta on prerequisite pair" not in src:
        fail("missing the H1 strip note format")

    print("PASS: H1 strip is defined once and called exactly once, inside the goal_change branch")
    sys.exit(0)


if __name__ == "__main__":
    main()
