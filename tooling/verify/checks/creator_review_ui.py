"""G1 check for TICKET-0129 -- the creator's review section and the player's returned and accepted states are wired.

BRIEF-0129-F's rule, static, stdlib only, no DB:

CU1 -- `PcDraftPanel.svelte` holds `<PcReviewSection` and `import
   PcReviewSection`, not `La revue de la créatrice arrive avec un prochain
   ticket`, and none of `alert(`, `confirm(`, `prompt(`, `method:`;
   `PcReviewSection.svelte` holds `Enregistrer la revue`, `Préparer le lot`,
   `Générer`, `Renvoyer au joueur`, `Approuver`, `Rattacher`, `Écarter`,
   `Prêt à approuver.`, and none of `fetch(`, `alert(`, `confirm(`,
   `prompt(`; `pcReview.svelte.js` holds the literals `/api/pc-reviews/`,
   `/lots`, `/renvoyer`, `/approuver`, `/api/npc-batches/`, `/run-next`,
   `entityListActivationTick += 1`, `loadSubmittedDrafts(` and an import
   from `./sheetRequest.svelte.js`; a built asset under
   `src/world_engine/cockpit/static/assets` carries `Renvoyer au joueur`.

A missing file, or a rule that collected nothing, is a FAILURE.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CREATION = ROOT / "frontend" / "src" / "creation"
PANEL = CREATION / "PcDraftPanel.svelte"
SECTION = CREATION / "PcReviewSection.svelte"
STORE = CREATION / "pcReview.svelte.js"
ASSETS = ROOT / "src" / "world_engine" / "cockpit" / "static" / "assets"
DIALOGS = ("alert(", "confirm(", "prompt(")
OLD_NOTICE = "La revue de la créatrice arrive avec un prochain ticket"
SECTION_LABELS = ("Enregistrer la revue", "Préparer le lot", "Générer", "Renvoyer au joueur", "Approuver",
                  "Rattacher", "Écarter", "Prêt à approuver.")
STORE_LITERALS = ("/api/pc-reviews/", "/lots", "/renvoyer", "/approuver", "/api/npc-batches/", "/run-next",
                  "entityListActivationTick += 1", "loadSubmittedDrafts(")
SHEET_IMPORT = re.compile(r"""import\s*\{[^}]*\}\s*from\s*['"]\./sheetRequest\.svelte\.js['"]""")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _read(path: Path) -> str | None:
    if not path.is_file():
        fail(f"CU1 {path.relative_to(ROOT)} missing")
        return None
    return path.read_text(encoding="utf-8")


def rule_cu1() -> int:
    panel, section, store = _read(PANEL), _read(SECTION), _read(STORE)
    if panel is None or section is None or store is None:
        return 0
    for needle in ("<PcReviewSection", "import PcReviewSection"):
        if needle not in panel:
            fail(f"CU1 PcDraftPanel.svelte lacks {needle}")
    if OLD_NOTICE in panel:
        fail("CU1 PcDraftPanel.svelte still holds the old review notice")
    for needle in DIALOGS + ("method:",):
        if needle in panel:
            fail(f"CU1 PcDraftPanel.svelte holds {needle}")
    for label in SECTION_LABELS:
        if label not in section:
            fail(f"CU1 PcReviewSection.svelte lacks « {label} »")
    for needle in ("fetch(",) + DIALOGS:
        if needle in section:
            fail(f"CU1 PcReviewSection.svelte holds {needle}")
    for literal in STORE_LITERALS:
        if literal not in store:
            fail(f"CU1 pcReview.svelte.js lacks {literal}")
    if not SHEET_IMPORT.search(store):
        fail("CU1 pcReview.svelte.js does not import from ./sheetRequest.svelte.js")
    assets = [p for p in ASSETS.glob("*") if p.is_file()] if ASSETS.is_dir() else []
    if not assets:
        fail(f"CU1 no built asset under {ASSETS.relative_to(ROOT)}")
    elif not any("Renvoyer au joueur" in p.read_text(encoding="utf-8", errors="ignore") for p in assets):
        fail("CU1 no built asset carries « Renvoyer au joueur » -- rebuild the frontend")
    return 1


def main() -> int:
    reached = rule_cu1()
    if reached != 1:
        fail("CU1 was not reached")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: creator_review_ui -- the review section sits in the creator's draft panel, its store writes "
          "through api, no dialog, the build carries it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
