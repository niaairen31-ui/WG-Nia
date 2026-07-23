"""G1 check for TICKET-0042 (BRIEF-0042-e): `room_batch_author.py` writes NO
canon. Fail-closed token scan, stdlib only: a missing target file is a
FAILURE, never a vacuous pass.

The generation module (Phase A manifest, Phase B fiches, Phase C coherence)
is ephemeral by construction -- every draft/edge stays client-held until the
atomic commit route (`cockpit/routes/room_batch.py::commit_room_batch`,
BRIEF-0042-e), the SOLE canon-write path for a batch. This check asserts the
generation module carries none of the four literal canon-write tokens named
in the ticket's acceptance criterion. `single_canon_write.py`'s AST-based
sweep already proves zero canon writes across all of `src/` (including this
module); this check is the narrower, human-legible confirmation the ticket
names by file.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
ROOM_BATCH_AUTHOR = ROOT / "src" / "world_engine" / "room_batch_author.py"

FORBIDDEN_TOKENS = (
    "_apply_mutation",
    "write_relation",
    "_create_entity_core",
    "db.commit(",
)

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def main() -> int:
    if not ROOM_BATCH_AUTHOR.exists():
        fail(f"{ROOM_BATCH_AUTHOR} does not exist — scan is broken, not the repo clean")
    else:
        text = ROOM_BATCH_AUTHOR.read_text(encoding="utf-8")
        for token in FORBIDDEN_TOKENS:
            if token in text:
                fail(f"room_batch_author.py contains forbidden canon-write token {token!r}")

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: room_batch_report_only — room_batch_author.py carries none of "
        "_apply_mutation/write_relation/_create_entity_core/db.commit("
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
