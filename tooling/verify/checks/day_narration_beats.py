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

from world_engine.day_narration_guard import judge_narration, lowercase_offending_words  # noqa: E402
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


# --- BRIEF-0093-B: code repair (C-01, lot table b2) --------------------------

def check_code_repair() -> None:
    EXECUTED.append("B1")
    got = lowercase_offending_words(
        "[RÉUSSITE] Malheureusement, Mini attend la Reine. La Reine sourit.", ("Malheureusement", "Reine"),
    )
    want = "[RÉUSSITE] malheureusement, Mini attend la reine. La reine sourit."
    if got != want:
        fail(f"B1: got {got!r}, want {want!r}")

    EXECUTED.append("B2")
    got = lowercase_offending_words("[RÉUSSITE] RÉUSSITE pour Mini.", ("RÉUSSITE",))
    if got != "[RÉUSSITE] réussite pour Mini.":
        fail(f"B2: marker span must stay untouched, got {got!r}")

    EXECUTED.append("B3")
    got = lowercase_offending_words("Les Reines passent.", ("Reine",))
    if got != "Les Reines passent.":
        fail(f"B3: a longer token must stay untouched, got {got!r}")

    EXECUTED.append("B4")
    p = "[RÉUSSITE] Mini attend la Reine."
    if lowercase_offending_words(p, ()) is not p:
        fail("B4: empty words must return the prose object unchanged")

    EXECUTED.append("B5")
    fs = _fact_sheet()
    prose = "[RÉUSSITE] Malheureusement, Mini attend la Reine."
    v = judge_narration(prose, fs)
    if v.passed or not v.offending_words:
        fail(f"B5: A1's prose must fail on containment first, got passed={v.passed} reason={v.reason!r}")
    else:
        v = judge_narration(lowercase_offending_words(prose, v.offending_words), fs)
        if v.passed is not True:
            fail(f"B5: repaired prose must pass the judge, got reason={v.reason!r}")


def main() -> int:
    check_judge_baseline()
    check_code_repair()
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
