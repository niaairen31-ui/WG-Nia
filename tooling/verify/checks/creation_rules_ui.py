"""G1 check for TICKET-0126 (BRIEF-0126-E) -- Création > Compétences carries the creation rules and the overrides.

CU1 -- `CompetencesList.svelte` holds `Création de personnage` and
   `creationRulesRecord()`; `CompetencesSheet.svelte` holds `rec.kind ===
   'creation'`, `<CreationRulesFiche`, `<CreationOverrides` exactly twice,
   and `{@render thresholds()}` exactly twice.
CU2 -- `creationRules.svelte.js` holds `'/api/creation-rules', {`,
   `export function creationOverridesBody(`, `export function
   inheritedVisible(`, `export function inheritedMaxRank(`, and imports
   nothing from `competences.svelte.js`; `competences.svelte.js` holds
   `...creationOverridesBody(record)` exactly twice and still
   `...pointsBody(record)` and `...trialsBody(record)` exactly twice each.
CU3 -- `CreationRulesFiche.svelte` holds every label of the rules fiche;
   `CreationOverrides.svelte` names the four override fields and holds both
   warnings verbatim; neither holds `alert(`, `confirm(`, `prompt(`.
CU4 -- the built bundle under `src/world_engine/cockpit/static/assets`
   carries `Création de personnage` and `détenues d'office`.

Static, stdlib only. A missing file, or a bundle with no `.js` asset, is a
FAILURE.
"""
from __future__ import annotations

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
CREATION = ROOT / "frontend" / "src" / "creation"
ASSETS = ROOT / "src" / "world_engine" / "cockpit" / "static" / "assets"

FICHE_LABELS = (
    "Réserve de points",
    "Coût pour atteindre {label(cost.rank)}",
    "Plafond au rang {label(cap.rank)}",
    'placeholder="aucun"',
    "Rang maximal à la création",
    "Compétences qui exigent un maître (au plus)",
    "Compétences visibles à la création par défaut",
    "Descendre une compétence détenue à {label(0)} rend le coût de {label(1)}.",
)
OVERRIDE_FIELDS = ("visible_at_creation", "max_rank_at_creation", "cap_raised_at_creation", "cap_held_at_creation")
VISIBLE_WARNING = "Visible à la création : le joueur lira son nom et sa description tels qu'ils sont écrits."
HELD_WARNING = (
    "Les compétences ouvertes de ce système sont détenues d'office : un plafond plus bas oblige le joueur "
    "à en descendre, et chaque descente lui rend un point."
)
DIALOGS = ("alert(", "confirm(", "prompt(")
BUNDLE_NEEDLES = ("Création de personnage", "détenues d'office")
IMPORT_COMPETENCES_RE = re.compile(r"""from\s+['"]\./competences\.svelte\.js['"]""")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _read(name: str) -> str | None:
    path = CREATION / name
    if not path.exists():
        fail(f"frontend/src/creation/{name} missing")
        return None
    return path.read_text(encoding="utf-8")


def _expect(rule: str, name: str, text: str, needle: str, count: int | None = None) -> None:
    found = text.count(needle)
    if count is None and not found:
        fail(f"{rule} {name} lacks {needle!r}")
    elif count is not None and found != count:
        fail(f"{rule} {name} holds {needle!r} {found} time(s), expected {count}")


def rule_cu1() -> None:
    listing = _read("CompetencesList.svelte")
    if listing is not None:
        for needle in ("Création de personnage", "creationRulesRecord()"):
            _expect("CU1", "CompetencesList.svelte", listing, needle)
    sheet = _read("CompetencesSheet.svelte")
    if sheet is not None:
        for needle in ("rec.kind === 'creation'", "<CreationRulesFiche"):
            _expect("CU1", "CompetencesSheet.svelte", sheet, needle)
        _expect("CU1", "CompetencesSheet.svelte", sheet, "<CreationOverrides", 2)
        _expect("CU1", "CompetencesSheet.svelte", sheet, "{@render thresholds()}", 2)


def rule_cu2() -> None:
    rules = _read("creationRules.svelte.js")
    if rules is not None:
        for needle in ("'/api/creation-rules', {", "export function creationOverridesBody(",
                       "export function inheritedVisible(", "export function inheritedMaxRank("):
            _expect("CU2", "creationRules.svelte.js", rules, needle)
        if IMPORT_COMPETENCES_RE.search(rules):
            fail("CU2 creationRules.svelte.js imports competences.svelte.js")
    state = _read("competences.svelte.js")
    if state is not None:
        for needle in ("...creationOverridesBody(record)", "...pointsBody(record)", "...trialsBody(record)"):
            _expect("CU2", "competences.svelte.js", state, needle, 2)


def rule_cu3() -> None:
    fiche = _read("CreationRulesFiche.svelte")
    if fiche is not None:
        for needle in FICHE_LABELS:
            _expect("CU3", "CreationRulesFiche.svelte", fiche, needle)
    overrides = _read("CreationOverrides.svelte")
    if overrides is not None:
        for needle in OVERRIDE_FIELDS + (VISIBLE_WARNING, HELD_WARNING):
            _expect("CU3", "CreationOverrides.svelte", overrides, needle)
    for name, text in (("CreationRulesFiche.svelte", fiche), ("CreationOverrides.svelte", overrides)):
        for dialog in DIALOGS:
            if text is not None and dialog in text:
                fail(f"CU3 {name} contains {dialog!r}")


def rule_cu4() -> None:
    bundles = sorted(ASSETS.glob("*.js")) if ASSETS.exists() else []
    if not bundles:
        fail("CU4 no .js asset under src/world_engine/cockpit/static/assets")
        return
    text = "\n".join(path.read_text(encoding="utf-8") for path in bundles)
    for needle in BUNDLE_NEEDLES:
        if needle not in text:
            fail(f"CU4 the built bundle lacks {needle!r} -- rebuild the frontend")


def main() -> int:
    for rule in (rule_cu1, rule_cu2, rule_cu3, rule_cu4):
        try:
            rule()
        except Exception as exc:  # noqa: BLE001 -- fail-closed, reported below
            fail(f"{rule.__name__} raised {type(exc).__name__}: {exc}")
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: creation_rules_ui -- the creation rules record and fiche, the overrides on each system and skill "
          "fiche with both warnings, the pinned threshold needles kept, the bundle rebuilt")
    return 0


if __name__ == "__main__":
    sys.exit(main())
