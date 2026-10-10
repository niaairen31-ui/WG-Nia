---
paths:
  - "src/world_engine/skill*.py"
  - "src/world_engine/cockpit/crud/skills.py"
---

# Skills and skill definitions

## Invariants

- **INV-41** Custom skill lookups filter `skill_definition_id`, by
  construction: a base-domain `skill` lookup includes `AND
  skill_definition_id IS NULL`. A custom skill resolves via its
  `skill_definition.base_domain` — never its own `domain` column — and that
  resolved `base_domain` is what every base-domain-keyed downstream branch
  keys off. An NPC holds only the rows it was given; Play's roll reads both
  sides through `skill_access` (NPC: skill, else base domain, else Initié).
  -- enforced by `npc_skills.py`
- **INV-42** A `skill_definition` delete always succeeds (no `ON DELETE
  RESTRICT`, no `change_history` snapshot): dependent PC `skill` rows, then
  the definition, in one transaction. The type-"Oui" modal is the sole
  safeguard — a named exception to "history is sacred", scoped to one row.
  [no check]
- **INV-43** A new open `skill_definition` backfills a default-rank `skill`
  row onto every existing PC of its world, in the create's own transaction.
  A `requires_master` skill is held only once taught (`POST /api/skills`),
  and `skill_access` locks it in Play until then. Renaming touches no `skill`
  row (FK-by-id); re-basing (`base_domain` change) updates `domain` on every
  dependent `skill` row in the same write. [no check]
- **INV-44** A `skill_definition.name` never equals a base-domain literal
  (`physical`/`agility`/`perception`/`composure`, case-insensitive): both
  write paths (creator CRUD and `_normalize_skill_catalogue`) reject or drop
  it. [no check]
- **INV-45** A `skill_definition` may carry a `system_id`, the body of rules
  it belongs to; NULL = unaffiliated. `DELETE /api/skill-systems` refuses
  while any skill is attached, unlike `DELETE /api/skill-definitions`, which
  deletes its dependents. [no check]
- **INV-46** `GET /api/skill-gaps` is read-only. It surfaces distinct
  `unmatched` `skill_resolution.surface_form` rows for the active world; the
  two arbiter-failure sentinels (`__arbiter_error__`, `__arbiter_empty__`)
  are excluded from `gaps` and reported in `arbiter_failures`. [no check]
