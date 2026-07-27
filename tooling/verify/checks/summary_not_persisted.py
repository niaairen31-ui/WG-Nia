"""G1 check for TICKET-0050 (BRIEF-0050-d) — the conversation summary is
never persisted (C1, standard idiom, vacuous-proof).

`conversation_window.py` is read + compute only: no function in it may
INSERT/UPDATE a `ConversationMessage` or any canon row. Grep-guard (module
source text) for the write-shaped tokens that would indicate a persistence
attempt. Vacuous-proof (negative direction): injecting a stub
`ConversationMessage(...)` write into a scratch copy of the module must
FAIL, proving the scan is actually wired to catch it.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
MODULE = ROOT / "src" / "world_engine" / "conversation_window.py"

FORBIDDEN_TOKENS = (
    "ConversationMessage(",
    "session.add(",
    "db.add(",
    ".commit(",
)

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _scan(text: str) -> list[str]:
    return [token for token in FORBIDDEN_TOKENS if token in text]


def check_module_is_clean() -> None:
    if not MODULE.exists():
        fail(f"{MODULE} not found")
        return
    hits = _scan(MODULE.read_text(encoding="utf-8"))
    for token in hits:
        fail(f"conversation_window.py contains forbidden write token {token!r} — module must be read+compute only")


def check_scan_actually_catches_a_write() -> None:
    """Vacuous-proof, negative direction: a module WITH a stub write must
    be flagged by the same scan, never silently pass."""
    poisoned = MODULE.read_text(encoding="utf-8") + "\n\ndb.add(ConversationMessage(content='x'))\n"
    hits = _scan(poisoned)
    if not hits:
        fail("vacuous-proof: injecting a stub ConversationMessage(...) write was not detected by the scan")


def main() -> int:
    check_module_is_clean()
    check_scan_actually_catches_a_write()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1

    print(
        "PASS: summary_not_persisted — conversation_window.py carries no "
        "canon-write token (C1: the summary is compute-only, never persisted)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
