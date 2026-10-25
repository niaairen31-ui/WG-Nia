"""G1 check for TICKET-0124 -- nothing stacks in Création's right column: germs are a group of the list, the skill sheet a pane of the sheet.

BRIEF-0124-H's rules (L1, H1; C-14 of LOT-0124), static, stdlib only, no DB:

CL1 -- `Creation.svelte` holds no `creation-pending-strip` and no
   `creation-pending-list`; it holds `id="creation-germ-panel"`, a
   `sheet-pane-bar` with the labels « Fiche » and « Compétences », the sheet
   hidden while a germ is open or the Compétences pane is shown
   (`selectedGermId || creationState.sheetPane === 'competences'`), and the
   skill sheet shown only in its pane with no germ open
   (`sheetPane === 'competences' && !creationState.selectedGermId`).
   Re-pinned by TICKET-0126 (BRIEF-0126-I): `id="creation-pc-draft-panel"`;
   the sheet is hidden by `(creationState.selectedGermId ||
   creationState.selectedPcDraftId || creationState.sheetPane ===
   'competences') ? 'none' : ''`, the skill sheet shown by
   `creationState.sheetPane === 'competences' &&
   !creationState.selectedGermId && !creationState.selectedPcDraftId`.
CL2 -- `tabs.js`' `npc`, `lieux` and `factions` entries declare
   `{ key: 'germPanel', containerId: 'creation-germ-panel' }`, `pj`'s does
   not; `_creationActivateTab` sets `selectedGermId = null` and
   `sheetPane = 'fiche'`; `sheetState.svelte.js`' `selectEntity` sets
   `selectedGermId = null`; `registry.js` holds the `germPanel` entry and
   `mount.js` the `germPanel: GermPanel` key. TICKET-0126: `pj` declares
   `{ key: 'pcDraftPanel', containerId: 'creation-pc-draft-panel' }` and
   `showSubmittedDrafts: true`, `npc`, `lieux` and `factions` neither;
   `_creationActivateTab` and `selectEntity` set `selectedPcDraftId =
   null`; `registry.js` holds the `pcDraftPanel` entry
   (`PcDraftPanel.svelte`) and `mount.js` the `pcDraftPanel: PcDraftPanel`
   key.
CL3 -- `EntityList.svelte` calls `selectGerm(`; `GermPanel.svelte` holds
   `/candidates`, `attachGerm(`, `generatePendingCreation(`,
   `germLinkTarget`, `'JOURNÉE'` and `'BROUILLON'`, and none of `alert(`,
   `confirm(`, `prompt(`.
CL4 -- `creation.css` (comments stripped): the `#creation-pj-skill` rule
   declares `flex: 1` and `min-height: 0` and no `max-height`; a
   `#creation-germ-panel` rule exists.
CL5 -- (TICKET-0126, BRIEF-0126-I) `EntityList.svelte` holds
   `selectPcDraft(` and `Soumis (`; `pcDrafts.svelte.js` holds
   `'/api/pc-drafts'` and no `method:`; `PcDraftPanel.svelte` holds none of
   `alert(`, `confirm(`, `prompt(`, `method:`; `creation.css` (comments
   stripped) holds a `#creation-pc-draft-panel` rule declaring `flex: 1`
   and `min-height: 0`.

The registry walk and the CSS parse are `creation_container_sizing.py`'s,
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
    "creation": CREATION / "Creation.svelte",
    "tabs": CREATION / "tabs.js",
    "sheet_state": CREATION / "sheetState.svelte.js",
    "registry": CREATION / "registry.js",
    "mount": CREATION / "mount.js",
    "list": CREATION / "EntityList.svelte",
    "germ": CREATION / "GermPanel.svelte",
    "pc_drafts": CREATION / "pcDrafts.svelte.js",
    "pc_draft_panel": CREATION / "PcDraftPanel.svelte",
    "css": ROOT / "frontend" / "public" / "creation.css",
}
GERM_ISLAND = "{ key: 'germPanel', containerId: 'creation-germ-panel' }"
PC_DRAFT_ISLAND = "{ key: 'pcDraftPanel', containerId: 'creation-pc-draft-panel' }"
SUBMITTED_FLAG = "showSubmittedDrafts: true"
MAX_HEIGHT_RE = re.compile(r"(^|[;\s])max-height\s*:")

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _needles(label: str, text: str, present: tuple[str, ...], absent: tuple[str, ...] = ()) -> None:
    for needle in present:
        if needle not in text:
            fail(f"{label} lacks {needle!r}")
    for needle in absent:
        if needle in text:
            fail(f"{label} holds {needle!r}")


def check_cl1(src: dict) -> None:
    _needles("CL1 Creation.svelte", src["creation"], (
        'id="creation-germ-panel"', 'id="creation-pc-draft-panel"', 'class="sheet-pane-bar"', ">Fiche<",
        ">Compétences<",
        "(creationState.selectedGermId || creationState.selectedPcDraftId || "
        "creationState.sheetPane === 'competences') ? 'none' : ''",
        "creationState.sheetPane === 'competences' && !creationState.selectedGermId && "
        "!creationState.selectedPcDraftId",
    ), ("creation-pending-strip", "creation-pending-list"))


def check_cl2(src: dict) -> None:
    registry_src = sizing._braced_block(src["tabs"], r"export const CREATION_TABS\s*=\s*\{")
    entries = dict(sizing._top_level_entries(registry_src)) if registry_src else {}
    if not entries:
        fail("CL2 CREATION_TABS parsed to zero entries")
    for key in ("npc", "lieux", "factions"):
        if GERM_ISLAND not in entries.get(key, ""):
            fail(f"CL2 CREATION_TABS.{key} does not declare the germPanel island")
    if "pj" not in entries or GERM_ISLAND in entries["pj"]:
        fail("CL2 CREATION_TABS.pj is missing or declares the germPanel island")
    for key in ("npc", "lieux", "factions"):
        if PC_DRAFT_ISLAND in entries.get(key, "") or SUBMITTED_FLAG in entries.get(key, ""):
            fail(f"CL2 CREATION_TABS.{key} declares the submitted drafts")
    for needle in (PC_DRAFT_ISLAND, SUBMITTED_FLAG):
        if needle not in entries.get("pj", ""):
            fail(f"CL2 CREATION_TABS.pj lacks {needle!r}")
    activate = sizing._braced_block(src["tabs"], r"function _creationActivateTab\(\)\s*\{")
    _needles("CL2 _creationActivateTab", activate,
             ("creationState.selectedGermId = null;", "creationState.selectedPcDraftId = null;",
              "creationState.sheetPane = 'fiche';"))
    select = sizing._braced_block(src["sheet_state"], r"export async function selectEntity\([^)]*\)\s*\{")
    _needles("CL2 selectEntity", select,
             ("creationState.selectedGermId = null;", "creationState.selectedPcDraftId = null;"))
    _needles("CL2 registry.js", src["registry"], (
        "germPanel: Object.freeze({", "component: 'GermPanel.svelte'",
        "pcDraftPanel: Object.freeze({", "component: 'PcDraftPanel.svelte'",
    ))
    _needles("CL2 mount.js", src["mount"], ("germPanel: GermPanel", "pcDraftPanel: PcDraftPanel"))


def check_cl3(src: dict) -> None:
    _needles("CL3 EntityList.svelte", src["list"], ("selectGerm(",))
    _needles("CL3 GermPanel.svelte", src["germ"], (
        "/candidates", "attachGerm(", "generatePendingCreation(", "germLinkTarget", "'JOURNÉE'", "'BROUILLON'",
    ), ("alert(", "confirm(", "prompt("))


def check_cl4(src: dict) -> None:
    text = sizing.CSS_COMMENT_RE.sub("", src["css"])
    rules = {selector.strip(): body for selector, body in sizing.CSS_RULE_RE.findall(text)}
    body = rules.get("#creation-pj-skill")
    if body is None:
        fail("CL4 creation.css has no '#creation-pj-skill' rule")
    else:
        if not sizing.FLEX_ONE_RE.search(body) or not sizing.MIN_HEIGHT_ZERO_RE.search(body):
            fail("CL4 '#creation-pj-skill' does not declare 'flex: 1' and 'min-height: 0'")
        if MAX_HEIGHT_RE.search(body):
            fail("CL4 '#creation-pj-skill' still caps its height")
    if "#creation-germ-panel" not in rules:
        fail("CL4 creation.css has no '#creation-germ-panel' rule")


def check_cl5(src: dict) -> None:
    _needles("CL5 EntityList.svelte", src["list"], ("selectPcDraft(", "Soumis ("))
    _needles("CL5 pcDrafts.svelte.js", src["pc_drafts"], ("'/api/pc-drafts'",), ("method:",))
    _needles("CL5 PcDraftPanel.svelte", src["pc_draft_panel"], (), ("alert(", "confirm(", "prompt(", "method:"))
    text = sizing.CSS_COMMENT_RE.sub("", src["css"])
    rules = {selector.strip(): body for selector, body in sizing.CSS_RULE_RE.findall(text)}
    body = rules.get("#creation-pc-draft-panel")
    if body is None:
        fail("CL5 creation.css has no '#creation-pc-draft-panel' rule")
    elif not sizing.FLEX_ONE_RE.search(body) or not sizing.MIN_HEIGHT_ZERO_RE.search(body):
        fail("CL5 '#creation-pc-draft-panel' does not declare 'flex: 1' and 'min-height: 0'")


def main() -> int:
    src: dict[str, str] = {}
    for key, path in FILES.items():
        if not path.is_file():
            fail(f"{path} does not exist")
            continue
        src[key] = path.read_text(encoding="utf-8")
    if not FAILURES:
        for name, rule in (("CL1", check_cl1), ("CL2", check_cl2), ("CL3", check_cl3), ("CL4", check_cl4),
                           ("CL5", check_cl5)):
            try:
                rule(src)
            except Exception as exc:  # a crash is that rule's failure, never a pass
                fail(f"{name}: crashed -- {type(exc).__name__}: {exc}")
    FAILURES.extend(f"CL2 {msg}" for msg in sizing.FAILURES)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: creation_layout -- no pending strip in the right column; germs are the list's group, "
          "opened alone in the germ panel (npc, lieux, factions) with Rattacher and Créer et lier and no "
          "dialog; the skill sheet is the Compétences pane of the sheet and takes the column; submitted "
          "drafts are the PJ list's Soumis group, opened alone and read only")
    return 0


if __name__ == "__main__":
    sys.exit(main())
