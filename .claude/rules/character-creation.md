---
paths:
  - "src/world_engine/creation_rules.py"
  - "src/world_engine/creation_check.py"
  - "src/world_engine/writes/creation_rules.py"
---

# Character creation

A world's creation rules live in one `creation_rules` row (a missing row
is every default); a system and a skill override visibility and the
maximum rank, a system caps its raised and held skills. Costs are per
step; lowering a held skill to Inexpérimenté gives back the Initié cost.

## Invariants

- **INV-67** A character-creation skill sheet -- the player's, the
  designer's, the one submitted -- is judged only by
  `creation_check.check_creation`, over the rules read by
  `creation_rules`; no other module reads a rank's creation cost.
  -- enforced by `creation_budget.py`
