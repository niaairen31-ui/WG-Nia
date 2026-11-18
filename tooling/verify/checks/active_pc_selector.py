"""G1 check for TICKET-0128 (BRIEF-0128-C) -- the cockpit header carries the « PJ actif » selector.

AS1 -- `frontend/src/Header.svelte` imports `ActivePcSelector` from
   `./ActivePcSelector.svelte` and holds `<ActivePcSelector />` after
   `id="world-selector"`.
AS2 -- `frontend/src/ActivePcSelector.svelte` holds `id="active-pc-selector"`,
   `Choisissez le PJ actif`, `Aucun PJ`, `chooseActivePc(` and
   `loadActivePc(`.
AS3 -- `frontend/src/lib/activePc.svelte.js` holds `'/api/active-pc'`,
   `method: 'PUT'`, `character_id`, `refreshServerState()`,
   `handleWorldChanged()`, imports `api` from
   `../creation/sheetRequest.svelte.js`, and holds no `fetch(` and no
   `detail` (INV-69: every request goes through `api`).
AS4 -- `frontend/src/journee/Journee.svelte` holds `void serverState.playerId;`
   (a new active PC reloads the days, the quests and the debts).
AS5 -- a built asset under `src/world_engine/cockpit/static/assets` carries
   `Choisissez le PJ actif`.

Static: file reads only, no DB. A missing file is a FAILURE.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
FRONTEND = ROOT / "frontend" / "src"
HEADER = FRONTEND / "Header.svelte"
SELECTOR = FRONTEND / "ActivePcSelector.svelte"
STORE = FRONTEND / "lib" / "activePc.svelte.js"
JOURNEE = FRONTEND / "journee" / "Journee.svelte"
ASSETS = ROOT / "src" / "world_engine" / "cockpit" / "static" / "assets"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _read(path: pathlib.Path, rule: str) -> str | None:
    if not path.exists():
        fail(f"{rule} {path.relative_to(ROOT)} is missing")
        return None
    return path.read_text(encoding="utf-8")


def rule_as1() -> None:
    text = _read(HEADER, "AS1")
    if text is None:
        return
    if not re.search(r"import\s+ActivePcSelector\s+from\s+'\./ActivePcSelector\.svelte'", text):
        fail("AS1 Header.svelte does not import ActivePcSelector from ./ActivePcSelector.svelte")
    world = text.find('id="world-selector"')
    tag = text.find("<ActivePcSelector />")
    if world < 0 or tag < 0 or tag < world:
        fail("AS1 Header.svelte holds no <ActivePcSelector /> after id=\"world-selector\"")


def rule_as2() -> None:
    text = _read(SELECTOR, "AS2")
    if text is None:
        return
    for needle in ('id="active-pc-selector"', "Choisissez le PJ actif", "Aucun PJ",
                   "chooseActivePc(", "loadActivePc("):
        if needle not in text:
            fail(f"AS2 ActivePcSelector.svelte lacks {needle!r}")


def rule_as3() -> None:
    text = _read(STORE, "AS3")
    if text is None:
        return
    for needle in ("'/api/active-pc'", "method: 'PUT'", "character_id", "refreshServerState()",
                   "handleWorldChanged()"):
        if needle not in text:
            fail(f"AS3 activePc.svelte.js lacks {needle!r}")
    if not re.search(r"import\s*\{[^}]*\bapi\b[^}]*\}\s*from\s*'\.\./creation/sheetRequest\.svelte\.js'", text):
        fail("AS3 activePc.svelte.js does not import api from ../creation/sheetRequest.svelte.js")
    for banned in ("fetch(", "detail"):
        if banned in text:
            fail(f"AS3 activePc.svelte.js holds {banned!r} (INV-69: requests go through api)")


def rule_as4() -> None:
    text = _read(JOURNEE, "AS4")
    if text is not None and "void serverState.playerId;" not in text:
        fail("AS4 Journee.svelte lacks 'void serverState.playerId;'")


def rule_as5() -> None:
    if not ASSETS.is_dir():
        fail(f"AS5 {ASSETS.relative_to(ROOT)} is missing")
        return
    assets = list(ASSETS.glob("*.js"))
    if not assets:
        fail("AS5 no built asset to read")
        return
    if not any("Choisissez le PJ actif" in a.read_text(encoding="utf-8", errors="replace") for a in assets):
        fail("AS5 no built asset carries 'Choisissez le PJ actif'")


def main() -> int:
    rule_as1()
    rule_as2()
    rule_as3()
    rule_as4()
    rule_as5()
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: active_pc_selector -- AS1-AS5: the header mounts the « PJ actif » selector after the "
          "world; it reads and sets /api/active-pc through api, then refreshes the shell and Création; "
          "Journée reloads on a new PC; the build carries it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
