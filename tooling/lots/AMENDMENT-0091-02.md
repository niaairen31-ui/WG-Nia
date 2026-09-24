# AMENDMENT-0091-02 — incomplete subculture enumeration; anchor drift after E

Ticket: TICKET-0091   Lot: LOT-0091-lore-as-facts.md   Brief in flight: H
(stopped at Mini-RECON, nothing modified)

## What deviated

1. **R-12's reader list was a negative claim without a pasted enumeration**
   — the defect protocol §1 step 1 forbids. It missed a reader
   (`cockpit/play_physical.py::_build_establishment_narration`,
   `:725-734`, allow-listed and `is_hidden = FALSE`), two
   `subculture_rows` payload sites (`cockpit/crud/entity_geometry.py:113,
   :143`, module extracted by TICKET-0089), the re-export in
   `cockpit/crud/__init__.py`, import-only references in eleven crud
   modules and `routes/mutations.py`, the `_SAFE_SUBCULTURE_KEYS` imports
   in `play_physical.py:20` and `routes/mutations.py:45`, and the seed
   writer `scripts/seed_pilot.py::ensure_location_subculture`.
2. **Anchor drift after BRIEF-0091-E (924825c)**, same content shifted:
   `creator.py` `faction.goals` `:78` -> `:80`, `generate_agenda` `:281` ->
   `:284`, owner block `:309-315` -> `:312-318`; `crud/entities.py`
   `"description"` `:246` -> `:237`, `_location_subculture_rows` `:266-273`
   -> `:257-264`, `subculture_rows` `:517` -> `:507`, `:805` -> `:812`.

Invariant touched: the hidden subculture trap (`is_hidden = FALSE` at query
construction). It holds after the switch: a hidden custom migrates with no
`location` default (C-18) and `facts_of(..., notorious_at_location=…)`
returns only facts carrying one.

## Corrected finding

R-12 carries a line naming this amendment. The complete enumeration
(models excluded) is pasted in the header's gate (c), under "Every
reference to the subculture table".

## Downstream briefs

- **H** (regenerated):
  - anchors updated to the drifted lines, with drift defined as same
    content shifted;
  - item 2 extended to `entity_geometry.py` (`:28`, `:113`, `:143`) and the
    `crud/__init__.py` re-export;
  - new item 2b switches `play_physical.py:725-734` to `coutume` facts
    notorious at the location, aspect in `_SAFE_SUBCULTURE_KEYS`, which is
    the same read as G item 4;
  - one new Done means (visible custom present, hidden absent);
  - the STOP now references the amended enumeration.
- **I** (regenerated):
  - the anchor lists exactly the references expected to remain after G and
    H;
  - item 3 removes the export, the import-only lines and the policy/doc
    lines, and rewrites the seed's subculture writer as `coutume` facts;
  - item 4 switches the remaining `_SAFE_SUBCULTURE_KEYS` imports to
    `FACETS["coutume"].aspects` and keeps `"description"` in
    `traits.py:160`'s collision set.

## Gate checks re-run

- (a) The R-12 property trace now points to the pasted enumeration.
- (c) The enumeration is pasted.
- (e) `lore_as_facts.py` R2 (`LocationSubculture` absent from `src/`) is
  satisfiable only with I's extended item 3. That item now lists every site.
  `scripts/` is outside R2's scope, but the seed is switched anyway so that
  it runs after v2.06.
