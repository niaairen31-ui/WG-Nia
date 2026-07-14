"""G1 gate: the H1 partial-application strip exists ONLY inside the
`goal_change complete` path — the project's one sanctioned exception to
all-or-nothing mutation apply (TICKET-0024, BRIEF-0024-c). No other
branch of `_apply_mutation` may strip an effect.

Retargeted (TICKET-0027, BRIEF-0027-c amendment, "check-anchor
relocation"): `_apply_mutation`'s `goal_change complete` logic now lives in
`_mutation_goal_change_close` in `cockpit/mutations.py` — this check
follows the relocation. Assertions unchanged: same strings, same call
requirements, same counts. Only the location anchors (file, containing
function) moved.

No DB, plain text scan of `mutations.py`.
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
TARGET = ROOT / "src" / "world_engine" / "cockpit" / "mutations.py"

HELPER = "_h1_strip_satisfied_prerequisite_deltas"
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

    if src.count(f"def {HELPER}(") != 1:
        fail(f"expected exactly 1 definition of {HELPER}")

    call_positions = [
        m.start() for m in re.finditer(re.escape(HELPER) + r"\(", src)
    ]
    def_position = src.find(f"def {HELPER}(") + len("def ")
    call_sites = [p for p in call_positions if p != def_position]
    if len(call_sites) != 1:
        fail(f"expected exactly 1 call site for {HELPER}, found {len(call_sites)}")

    branch = _goal_change_close_branch(src)
    branch_start = src.find(branch)
    branch_end = branch_start + len(branch)
    if not (branch_start <= call_sites[0] < branch_end):
        fail(f"{HELPER} is called outside {CONTAINING_FUNCTION}")

    if "H1 (TICKET-0024)" not in src:
        fail("missing the H1 verbatim comment at the strip site")
    if "stripped: relation_delta on prerequisite pair" not in src:
        fail("missing the H1 strip note format")

    print(f"PASS: H1 strip is defined once and called exactly once, inside {CONTAINING_FUNCTION}")
    sys.exit(0)


if __name__ == "__main__":
    main()
