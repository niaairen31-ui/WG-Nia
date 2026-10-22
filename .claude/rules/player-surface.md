---
paths:
  - "frontend/src/joueur/**"
  - "src/world_engine/cockpit/routes/player.py"
  - "src/world_engine/cockpit/perspective_flow.py"
  - "src/world_engine/perspective_*.py"
---

# The player surface

The player shell is `/jouer`, its own bundle. Its pages call only
`/api/joueur/*`; those routes key on a world (and later a character),
never on `world.is_active`.

## Invariants

- **INV-66** A player surface learns about the world only through a
  perspective (`perspective_query`), never a creator selector, the
  creator name regime, a trace, near names or the audit; every
  perspective question is journaled with what was withheld. The
  perspective selectors read `faction_membership` with the
  `read_public_memberships` WHERE triplet, keyed by faction (a third
  sanctioned reader, INV-03). -- enforced by `perspective_isolation.py`,
  `player_routes.py`, `player_shell.py`
