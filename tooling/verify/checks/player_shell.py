"""G1 check for TICKET-0125 -- the Lore perspective tab and the player shell are wired and confined.

PSH1 -- static (BRIEF-0125-F): `frontend/src/lore/Lore.svelte` holds
   `loreTab === 'perspective'`, the tab button's `(loreTab = 'perspective')`
   and `<PerspectivePanel`;
   `frontend/src/lore/perspective.svelte.js` posts to
   `/api/lore/perspective/ask` and `/api/lore/perspective/resolve` and sends
   `attempt_id`; `frontend/src/lore/PerspectivePanel.svelte` holds the five
   French reason labels (`réservé à la créatrice`, `pas public`, `entité non
   publique`, `appartenance secrète`, `faction non publique`) and `Rien n'a
   été retenu.`, and none of `alert(`, `confirm(`, `prompt(`.

A missing file is a FAILURE.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
LORE = ROOT / "frontend" / "src" / "lore"

REASON_LABELS = ("réservé à la créatrice", "pas public", "entité non publique",
                 "appartenance secrète", "faction non publique")
DIALOGS = ("alert(", "confirm(", "prompt(")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _read(path: pathlib.Path) -> str | None:
    if not path.exists():
        fail(f"{path.relative_to(ROOT)} missing")
        return None
    return path.read_text(encoding="utf-8")


def rule_psh1() -> None:
    lore = _read(LORE / "Lore.svelte")
    if lore is not None:
        for needle in ("loreTab === 'perspective'", "(loreTab = 'perspective')", "<PerspectivePanel"):
            if needle not in lore:
                fail(f"PSH1: Lore.svelte lacks {needle}")
    state = _read(LORE / "perspective.svelte.js")
    if state is not None:
        for needle in ("'/api/lore/perspective/ask'", "'/api/lore/perspective/resolve'", "attempt_id"):
            if needle not in state:
                fail(f"PSH1: perspective.svelte.js lacks {needle}")
    panel = _read(LORE / "PerspectivePanel.svelte")
    if panel is not None:
        for needle in (*REASON_LABELS, "Rien n'a été retenu."):
            if needle not in panel:
                fail(f"PSH1: PerspectivePanel.svelte lacks {needle!r}")
        for needle in DIALOGS:
            if needle in panel:
                fail(f"PSH1: PerspectivePanel.svelte calls {needle}")


def main() -> int:
    try:
        rule_psh1()
    except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
        fail(f"rule_psh1 raised {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: player_shell -- the Lore perspective tab is wired")
    return 0


if __name__ == "__main__":
    sys.exit(main())
