"""G1 check for TICKET-0124 -- the sheet shows what the world adds to a draft and sends what the creator kept.

BRIEF-0124-I's rules (C-09, C-14 of LOT-0124), static, stdlib only, no DB:

DP1 -- `pendingDrafts.svelte.js` holds `world:` in its state, resets
   `pendingDraftsState.world` in `resetPendingDrafts`, and exports
   `worldExtrasForCreate` returning `states`, `relations` and `germs`;
   `generatePanel.svelte.js`' `applyGeneratedDraft` (with the helper it
   calls) assigns `pendingDraftsState.world`, sets the `toCreate` items
   `checked: false` (I1) and clears `germLinkTarget`.
DP2 -- `Sheet.svelte` imports `DraftWorldPanel`, renders `<DraftWorldPanel`
   inside `{#if isNew && ['character', 'location', 'faction'].includes(type)}`,
   and spreads `worldExtrasForCreate()` in `submitEntity`; it still holds
   `<StatesPanel entityId={detail.id}` (AC3). `DraftWorldPanel.svelte` holds
   `attachGerm(` and `getPendingCreationMutationId(`, and none of `alert(`,
   `confirm(`, `prompt(`.

Function bodies are cut by `creation_container_sizing.py`'s brace walk,
imported. A missing file or an empty match is a FAILURE.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import creation_container_sizing as sizing  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
CREATION = ROOT / "frontend" / "src" / "creation"
FILES = {
    "drafts": CREATION / "pendingDrafts.svelte.js",
    "generate": CREATION / "generatePanel.svelte.js",
    "sheet": CREATION / "Sheet.svelte",
    "panel": CREATION / "DraftWorldPanel.svelte",
}
WORLD_IF = "{#if isNew && ['character', 'location', 'faction'].includes(type)}"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _needles(label: str, text: str, present: tuple[str, ...], absent: tuple[str, ...] = ()) -> None:
    if not text:
        fail(f"{label}: nothing to read")
        return
    for needle in present:
        if needle not in text:
            fail(f"{label} lacks {needle!r}")
    for needle in absent:
        if needle in text:
            fail(f"{label} holds {needle!r}")


def _body(text: str, signature: str) -> str:
    return sizing._braced_block(text, signature)


def check_dp1(src: dict) -> None:
    state = _body(src["drafts"], r"export const pendingDraftsState\s*=\s*\$state\(\{")
    _needles("DP1 pendingDraftsState", state, ("world:",))
    _needles("DP1 resetPendingDrafts", _body(src["drafts"], r"export function resetPendingDrafts\(\)\s*\{"),
             ("pendingDraftsState.world =",))
    extras = _body(src["drafts"], r"export function worldExtrasForCreate\(\)\s*\{")
    _needles("DP1 worldExtrasForCreate", extras, ("states:", "relations:", "germs:"))
    apply = _body(src["generate"], r"export function applyGeneratedDraft\([^)]*\)\s*\{")
    _needles("DP1 applyGeneratedDraft", apply, ())
    helpers = re.findall(r"\b(\w+)\(result\)", apply)
    text = apply + "".join(_body(src["generate"], rf"function {name}\([^)]*\)\s*\{{") for name in helpers)
    _needles("DP1 applyGeneratedDraft and its helpers", text, (
        "pendingDraftsState.world =", "checked: false", "creationState.germLinkTarget = null",
    ))
    to_create = re.search(r"toCreate:[^\n]*", text)
    if not to_create or "checked: false" not in to_create.group(0):
        fail("DP1 the entities to create are not left unticked (checked: false)")


def check_dp2(src: dict) -> None:
    sheet = src["sheet"]
    _needles("DP2 Sheet.svelte", sheet, (
        "import DraftWorldPanel from './DraftWorldPanel.svelte';", WORLD_IF,
        "<StatesPanel entityId={detail.id}",
    ))
    block = sheet.split(WORLD_IF, 1)[1].split("{/if}", 1)[0] if WORLD_IF in sheet else ""
    if "<DraftWorldPanel" not in block:
        fail("DP2 <DraftWorldPanel is not rendered inside the create-mode world block")
    submit = _body(sheet, r"async function submitEntity\([^)]*\)\s*\{")
    _needles("DP2 submitEntity", submit, ("worldExtrasForCreate()",))
    _needles("DP2 DraftWorldPanel.svelte", src["panel"], ("attachGerm(", "getPendingCreationMutationId("),
             ("alert(", "confirm(", "prompt("))


def main() -> int:
    src: dict[str, str] = {}
    for key, path in FILES.items():
        if not path.is_file():
            fail(f"{path} does not exist")
            continue
        src[key] = path.read_text(encoding="utf-8")
    if not FAILURES:
        for name, rule in (("DP1", check_dp1), ("DP2", check_dp2)):
            try:
                rule(src)
            except Exception as exc:  # a crash is that rule's failure, never a pass
                fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: draft_panel -- a new sheet shows the draft's world block (states and links kept, entities "
          "to create unticked, the same-person attach) and its create sends the kept ones")
    return 0


if __name__ == "__main__":
    sys.exit(main())
