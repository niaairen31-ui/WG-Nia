---
paths:
  - "src/world_engine/active_pc.py"
  - "src/world_engine/writes/active_pc.py"
  - "src/world_engine/cockpit/routes/active_pc.py"
  - "src/world_engine/cockpit/routes/day.py"
  - "src/world_engine/day_*.py"
  - "src/world_engine/cockpit/day_*.py"
---

# The active player character and the day chain

A world may hold several player characters. The creator's cockpit acts
for one of them, the active PC; a player acts for his own.

## Invariants

- **INV-70** A creator surface's player character comes from one
  resolver, `active_pc.resolve_active_pc`: the world's `active_pc_id`
  when it names an active player character of the world, else the
  world's only one. Several and none chosen is a refusal, never a pick.
  -- enforced by `pc_resolution.py`
- **INV-71** The day chain takes its world and its character from the
  day (`batch -> session -> world`, `pass_play.character_id`), never
  from the active world nor the active player character; the premise,
  the extraction, the feasibility and the presence rung receive that
  world. -- enforced by `day_chain_world.py`
