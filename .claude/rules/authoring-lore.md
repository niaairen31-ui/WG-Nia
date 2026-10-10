---
paths:
  - "src/world_engine/region_author.py"
  - "src/world_engine/cockpit/routes/regions.py"
  - "src/world_engine/lore_*.py"
  - "src/world_engine/writes/lore_entries.py"
  - "src/world_engine/writes/lore_usage.py"
  - "src/world_engine/cockpit/routes/lore*.py"
  - "scripts/export_lore_usage.py"
---

# Region generation and the Lore surface

## Invariants

- **INV-56** Region generation writes no canon; its commit is atomic; its
  resolution is server-authoritative. `generate_region_draft` proposes
  factions and locations only. `POST /api/regions/commit` is the single
  write point: entities, skeleton (`parent_location_id`, faction roles via
  `write_faction_role`) and creator-confirmed links commit in one
  transaction, all-or-nothing, via the commit-free cores and
  `write_relation`. No model-emitted id reaches a canon row; the
  accept/reject cascade and link targets are re-derived server-side from raw
  client state; rejected, uncommitted, unresolved or self-referential
  targets write nothing. [no check]
- **INV-57** A lore statement commits whole or not at all, through
  `lore_write_apply.apply_proposal`. No model-emitted id reaches a canon
  row: facts by code, entities by name, both resolved in code and confirmed
  by the creator; every row written is recorded in `lore_entry_row`.
  -- enforced by `lore_write.py`
- **INV-58** The lore renderer receives rows, never a `Session`, and only
  the `answered` verdict reaches a model — every empty verdict is rendered
  by code, so an absence is never explained by a model. [no check]
- **INV-59** The Lore usage journal (`lore_usage_event`) is written only
  through `lore_usage` and read only by `scripts/export_lore_usage.py`; no
  prompt, play or creator path reads it back, and it has no `world_id`, so
  it outlives its world. -- enforced by `lore_usage.py`
