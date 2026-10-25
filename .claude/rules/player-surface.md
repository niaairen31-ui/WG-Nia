---
paths:
  - "frontend/src/joueur/**"
  - "src/world_engine/cockpit/routes/player.py"
  - "src/world_engine/cockpit/perspective_flow.py"
  - "src/world_engine/perspective_*.py"
  - "src/world_engine/creation_rules.py"
  - "src/world_engine/creation_lore.py"
  - "src/world_engine/creation_designer.py"
  - "src/world_engine/cockpit/routes/player_creation.py"
---

# The player surface

The player shell is `/jouer`, its own bundle. Its pages call only
`/api/joueur/*`; those routes key on a world (and later a character),
never on `world.is_active`.

## Invariants

- **INV-66** A player surface learns about the world only through the
  public view (`perspective_selectors`, or `perspective_query` for a
  planned question), never a creator selector, the creator name regime,
  a trace, near names or the audit. A skill is in that view only when
  visible at creation (`creation_rules`); the creation rules themselves
  (pool, costs, caps) are game rules, read through `creation_rules`.
  Every perspective question is journaled with what was withheld, and
  every character-designer call with what it read. The perspective
  selectors read `faction_membership` with the `read_public_memberships`
  WHERE triplet, keyed by faction (a third sanctioned reader, INV-03).
  -- enforced by `perspective_isolation.py`, `player_routes.py`,
  `player_shell.py`, `creation_designer.py`, `player_creation.py`
