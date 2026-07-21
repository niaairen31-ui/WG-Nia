"""G1 check: region NPC-machinery retirement (TICKET-0037, BRIEF-0037-d,
A1). Fail-closed token scan, stdlib only, on the door_terminal.py idiom: a
missing target file is a FAILURE, never a vacuous pass.

Two assertions:
  a. `region_author.py` and `cockpit/routes/regions.py` carry none of the
     retired NPC-machinery tokens; `region_author.py` additionally carries
     zero case-insensitive "npc" substrings at all — region generation is
     factions/locations only from TICKET-0037 onward.
  b. `prompt_registry.py` carries no `region_manifest_topup` token — the
     retired usage's registry entry is gone.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src" / "world_engine"

REGION_AUTHOR = SRC / "region_author.py"
REGIONS_ROUTE = SRC / "cockpit" / "routes" / "regions.py"
PROMPT_REGISTRY = SRC / "prompt_registry.py"

FORBIDDEN_TOKENS = (
    "MIN_NPCS_PER_FACTION",
    "MIN_FACTIONLESS",
    "_run_npc_topup",
    "_npc_deficits",
    "_draft_npcs",
    "_draft_one_npc",
    "_compose_npc_brief",
    "_commit_region_npcs",
    "region_manifest_topup",
)

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _read(path: pathlib.Path) -> str | None:
    if not path.exists():
        fail(f"{path} does not exist — scan is broken, not the repo clean")
        return None
    return path.read_text(encoding="utf-8")


def check_forbidden_tokens(path: pathlib.Path) -> None:
    text = _read(path)
    if text is None:
        return
    rel = path.relative_to(ROOT).as_posix()
    for token in FORBIDDEN_TOKENS:
        if token in text:
            fail(f"{rel} still contains retired token {token!r}")


def check_no_npc_substring(path: pathlib.Path) -> None:
    text = _read(path)
    if text is None:
        return
    rel = path.relative_to(ROOT).as_posix()
    if "npc" in text.lower():
        fail(f"{rel} still contains an 'npc' substring — region generation is factions/locations only")


def check_prompt_registry_topup() -> None:
    text = _read(PROMPT_REGISTRY)
    if text is None:
        return
    if "region_manifest_topup" in text:
        fail("src/world_engine/prompt_registry.py still references region_manifest_topup")


def main() -> int:
    check_forbidden_tokens(REGION_AUTHOR)
    check_forbidden_tokens(REGIONS_ROUTE)
    check_no_npc_substring(REGION_AUTHOR)
    check_prompt_registry_topup()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: region_npc_retirement — region_author.py/regions.py clean of "
        "retired NPC tokens, prompt_registry.py clean of region_manifest_topup"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
