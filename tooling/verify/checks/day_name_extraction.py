"""G1 check: permanent regression guard for sentence-aware name extraction
(TICKET-0079, BRIEF-0079-a). Deterministic, no DB — imports
`world_engine.day_narration_guard.extract_names` via the same `ROOT`/`src`
path bootstrap the other unit checks use (e.g. `geometry_unit.py`,
`placement_unit.py`). Every case is a hard assert; one summary PASS line on
success. Vacuity-guarded: a run of zero golden cases is a FAILURE, not a
pass.

Golden cases are exact-set-equality assertions, not containment. Brief
Scope IN item 6's original wording used containment ("no returned run
contains X"), which measured out to be a vacuous check for G1: on the
brief's original G1 prose, containment held for the target implementation,
for a sentence-split-only revert, AND for the fully pre-brief (unfixed)
`extract_names` alike — none of the golden cases distinguished a correct
implementation from a broken one, contradicting the brief's own stated
goal ("a check that cannot fail is the outcome to avoid"). Corrected
in-session with Nia: G1's prose is now the live-observed shape from the
ticket (capitalized "Serviteurs"/"Dirigeants"), and every case asserts the
exact returned set, so each case has a named mutation it demonstrably
kills. See the per-case comments below and the BRIEF-0079-a execution
notes for the measured mutation outputs.

Stop condition: if the `extract_names` import fails, this check must fail
loudly (ImportError, uncaught) — never fall back to an AST or regex
approximation of the golden cases, which would reintroduce the exact
vacuity this file exists to remove.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from world_engine.day_narration_guard import extract_names  # noqa: E402

FAILURES: list[str] = []
EXECUTED: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def assert_exact(label: str, prose: str, expected: set[str]) -> None:
    EXECUTED.append(label)
    result = set(extract_names(prose))
    if result != expected:
        fail(f"{label}: expected exactly {sorted(expected)}, got {sorted(result)}")


def check_g1_sentence_break() -> None:
    # Kills BOTH the sentence-split revert (would fuse "Serviteurs Sans
    # Dirigeants" into one run) and the edge-strip revert (would keep
    # "Sans Dirigeants" as its own run instead of stripping to
    # "Dirigeants"). The live-observed reproduction from TICKET-0079.
    assert_exact(
        "G1 sentence break",
        "[BLOQUÉ] Kaela croise les Serviteurs. Sans Dirigeants pour la retenir, elle repart.",
        {"Kaela", "Serviteurs", "Dirigeants"},
    )


def check_g2_edge_strip() -> None:
    # Kills the edge-strip revert: without stripping, "Les Serviteurs"
    # survives as one run instead of "Serviteurs".
    assert_exact(
        "G2 edge strip",
        "Les Serviteurs la renvoient.",
        {"Serviteurs"},
    )


def check_g3_no_position_gating() -> None:
    # Proves no position-gating regression: both sentence-initial
    # capitalized names survive as their own runs.
    assert_exact(
        "G3 no position gating",
        "Lorian entre. Kaela le suit.",
        {"Lorian", "Kaela"},
    )


def check_g4_non_vacuity() -> None:
    # Non-vacuity: single names, a connector-bridged two-word name, and a
    # place name whose "au"/"aux" bridge word is NOT in _CONNECTORS
    # (measured, out of scope to widen) so it splits into two candidates —
    # both still individually authorised via _authorised_words.
    assert_exact(
        "G4 non-vacuity",
        "Kaela parle a Joran Vey au Marche aux Cendres.",
        {"Kaela", "Joran Vey", "Marche", "Cendres"},
    )


def check_g5_connector_interior() -> None:
    # Proves an interior connector survives edge-stripping untouched.
    assert_exact(
        "G5 connector interior",
        "Joran de Vey ecoute.",
        {"Joran de Vey"},
    )


CASES = [
    check_g1_sentence_break,
    check_g2_edge_strip,
    check_g3_no_position_gating,
    check_g4_non_vacuity,
    check_g5_connector_interior,
]


def main() -> None:
    for case in CASES:
        case()

    if not EXECUTED:
        fail("vacuity: zero golden cases executed")

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)

    print(f"PASS: day_name_extraction — all {len(EXECUTED)} golden cases hold (G1-G5)")
    sys.exit(0)


if __name__ == "__main__":
    main()
