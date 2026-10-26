"""G1 check for TICKET-0129 -- the creator's review section and the player's returned and accepted states are wired.

BRIEF-0129-F's rule and BRIEF-0129-G's two, static, stdlib only, no DB:

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
CU2 -- the player's states. `joueur/CharacterCreation.svelte` holds
   `status === 'submitted'`, `Renvoyé par la créatrice.`, `creator_note`,
   `a été accepté dans ce monde.`; `joueur/character.svelte.js` holds
   `character_name`; a built asset carries `Renvoyé par la créatrice.`.
CU3 -- K1-b. `PjSkillFiche.svelte` holds `<PjProfileField` directly inside
   an `{#if characterType === 'player' ...}` block (the test already reads
   elsewhere in the fiche, so its mere presence proves nothing); `PjProfileField.svelte` holds `Joueur`,
   `Créatrice`, and none of `alert(`, `confirm(`, `prompt(`, `fetch(`;
   `pcProfiles.svelte.js` holds `/api/pc-profiles`.

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
JOUEUR = ROOT / "frontend" / "src" / "joueur"
PLAYER_SCREEN = JOUEUR / "CharacterCreation.svelte"
PLAYER_STORE = JOUEUR / "character.svelte.js"
FICHE = CREATION / "PjSkillFiche.svelte"
PROFILE_FIELD = CREATION / "PjProfileField.svelte"
PROFILE_STORE = CREATION / "pcProfiles.svelte.js"
PLAYER_SCREEN_NEEDLES = ("status === 'submitted'", "Renvoyé par la créatrice.", "creator_note",
                         "a été accepté dans ce monde.")
DIALOGS = ("alert(", "confirm(", "prompt(")
OLD_NOTICE = "La revue de la créatrice arrive avec un prochain ticket"
SECTION_LABELS = ("Enregistrer la revue", "Préparer le lot", "Générer", "Renvoyer au joueur", "Approuver",
                  "Rattacher", "Écarter", "Prêt à approuver.")
STORE_LITERALS = ("/api/pc-reviews/", "/lots", "/renvoyer", "/approuver", "/api/npc-batches/", "/run-next",
                  "entityListActivationTick += 1", "loadSubmittedDrafts(")
PROFILE_GATE = re.compile(r"\{#if characterType === 'player'[^}]*\}\s*<PjProfileField")
SHEET_IMPORT = re.compile(r"""import\s*\{[^}]*\}\s*from\s*['"]\./sheetRequest\.svelte\.js['"]""")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _read(path: Path, rule: str = "CU1") -> str | None:
    if not path.is_file():
        fail(f"{rule} {path.relative_to(ROOT)} missing")
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


def _assets() -> list[Path]:
    return [p for p in ASSETS.glob("*") if p.is_file()] if ASSETS.is_dir() else []


def rule_cu2() -> int:
    screen, store = _read(PLAYER_SCREEN, "CU2"), _read(PLAYER_STORE, "CU2")
    if screen is None or store is None:
        return 0
    for needle in PLAYER_SCREEN_NEEDLES:
        if needle not in screen:
            fail(f"CU2 CharacterCreation.svelte lacks {needle}")
    if "character_name" not in store:
        fail("CU2 character.svelte.js lacks character_name")
    assets = _assets()
    if not assets:
        fail(f"CU2 no built asset under {ASSETS.relative_to(ROOT)}")
    elif not any("Renvoyé par la créatrice." in p.read_text(encoding="utf-8", errors="ignore") for p in assets):
        fail("CU2 no built asset carries « Renvoyé par la créatrice. » -- rebuild the frontend")
    return 1


def rule_cu3() -> int:
    fiche, field, store = _read(FICHE, "CU3"), _read(PROFILE_FIELD, "CU3"), _read(PROFILE_STORE, "CU3")
    if fiche is None or field is None or store is None:
        return 0
    if "<PjProfileField" not in fiche:
        fail("CU3 PjSkillFiche.svelte lacks <PjProfileField")
    elif not PROFILE_GATE.search(fiche):
        fail("CU3 <PjProfileField is not gated by characterType === 'player'")
    for label in ("Joueur", "Créatrice"):
        if label not in field:
            fail(f"CU3 PjProfileField.svelte lacks « {label} »")
    for needle in DIALOGS + ("fetch(",):
        if needle in field:
            fail(f"CU3 PjProfileField.svelte holds {needle}")
    if "/api/pc-profiles" not in store:
        fail("CU3 pcProfiles.svelte.js lacks /api/pc-profiles")
    return 1


def main() -> int:
    for name, rule in (("CU1", rule_cu1), ("CU2", rule_cu2), ("CU3", rule_cu3)):
        if rule() != 1:
            fail(f"{name} was not reached")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: creator_review_ui -- the review section sits in the creator's draft panel, its store writes "
          "through api, no dialog, the build carries it; the player's returned and accepted states; the "
          "« Joueur » field on a player character's skill pane")
    return 0


if __name__ == "__main__":
    sys.exit(main())
