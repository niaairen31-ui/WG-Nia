"""G1 check for TICKET-0093 — day narration beats. Deterministic: no DB, no
model. Builds `FactSheet`/`StepFact`/`NamedRef` directly.

BRIEF-0093-A creates this file with the judge baseline cases (A1-A3);
BRIEF-0093-B adds the code-repair cases; BRIEF-0093-C adds the
beat-assembly and band-label cases. Each brief adds its cases as new
functions called from `main()`.

Vacuity-guarded: zero executed cases is a FAILURE. FAILURES list, print
FAIL lines, exit 1; one PASS line on success.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from world_engine.day_narration_guard import judge_narration  # noqa: E402
from world_engine.day_resolve import FactSheet, NamedRef, StepFact  # noqa: E402

FAILURES: list[str] = []
EXECUTED: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fact_sheet(
    npcs: tuple[NamedRef, ...] = (), authorised: frozenset[str] = frozenset({"Mini"}),
) -> FactSheet:
    return FactSheet(
        world_id="w", day_number=1, character_name="Mini",
        steps=(StepFact(objective="attendre", band="success", dice=(4, 4), modifier=0, total=8),),
        npcs=npcs, locations=(), role_hints=(), authorised_names=authorised,
    )


# --- BRIEF-0093-A: judge baseline --------------------------------------------

def check_judge_baseline() -> None:
    EXECUTED.append("A1")
    v = judge_narration("[RÉUSSITE] Malheureusement, Mini attend la Reine.", _fact_sheet())
    if v.passed is not False or v.offending_words != ("Malheureusement", "Reine"):
        fail(f"A1: passed={v.passed} offending_words={v.offending_words!r} reason={v.reason!r}")

    EXECUTED.append("A2")
    fs = _fact_sheet(npcs=(NamedRef("x", "Lorian"),), authorised=frozenset({"Mini", "Lorian"}))
    v = judge_narration("[RÉUSSITE] Mini attend Lorian.", fs)
    if v.passed is not True:
        fail(f"A2: passed={v.passed} reason={v.reason!r}")

    EXECUTED.append("A3")
    v = judge_narration("[réussite] mini attend.", _fact_sheet())
    if v.passed is not False or v.reason != "anti-vacuity: zero names extracted from the prose":
        fail(f"A3: passed={v.passed} reason={v.reason!r}")


def main() -> int:
    check_judge_baseline()
    if not EXECUTED:
        fail("vacuity: zero cases executed")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(f"PASS: day_narration_beats — {len(EXECUTED)} cases executed ({', '.join(EXECUTED)})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
