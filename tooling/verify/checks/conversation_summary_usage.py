"""G1 check for TICKET-0050 (BRIEF-0050-c) — `conversation_summary` prompt
usage wiring (standard idiom, vacuous-proof).

No DB required for the registry half (pure import + attribute assertions);
the seeded-row half is a source-text scan of scripts/seed_pilot.py, mirroring
the event_assist.py / prompt_registry.py precedent rather than spinning up a
DB, since the seed's upsert shape is what's being asserted, not runtime
behavior.

Two assertions:
1. `"conversation_summary"` is a key in `PROMPT_REGISTRY` with
   `default_model is _author_model` and `world_scoped is True`.
2. A `pt-conversation-summary` `upsert_prompt_template(...)` call exists in
   `scripts/seed_pilot.py` with `usage="conversation_summary"`.
Either absent -> FAIL (never a silent pass).
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
SEED_PILOT = ROOT / "scripts" / "seed_pilot.py"

sys.path.insert(0, str(SRC))

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def check_registry() -> None:
    from world_engine import prompt_registry

    entry = prompt_registry.PROMPT_REGISTRY.get("conversation_summary")
    if entry is None:
        fail("PROMPT_REGISTRY has no 'conversation_summary' entry")
        return
    if entry.default_model is not prompt_registry._author_model:
        fail("PROMPT_REGISTRY['conversation_summary'].default_model is not _author_model")
    if entry.world_scoped is not True:
        fail("PROMPT_REGISTRY['conversation_summary'].world_scoped is not True")
    if not entry.call_sites:
        fail("PROMPT_REGISTRY['conversation_summary'].call_sites is empty")


def check_seeded_row() -> None:
    seed_src = SEED_PILOT.read_text(encoding="utf-8")
    if '"pt-conversation-summary"' not in seed_src:
        fail("pt-conversation-summary upsert not found in seed_pilot.py")
        return
    start = seed_src.index('"pt-conversation-summary"')
    end = seed_src.find("\n    )", start)
    window = seed_src[start:end if end != -1 else start + 1000]
    if 'usage="conversation_summary"' not in window:
        fail("pt-conversation-summary upsert does not set usage=\"conversation_summary\"")
    if "model=" in window:
        fail("pt-conversation-summary upsert sets a model= override — seed must leave model NULL")


def main() -> int:
    check_registry()
    check_seeded_row()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1

    print(
        "PASS: conversation_summary_usage — PROMPT_REGISTRY entry "
        "(default_model=_author_model, world_scoped=True) and pt-conversation-summary "
        "seeded with usage='conversation_summary'"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
