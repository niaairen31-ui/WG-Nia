---
paths:
  - "src/world_engine/gathering.py"
  - "src/world_engine/encounters.py"
  - "src/world_engine/passages.py"
  - "src/world_engine/cockpit/routes/scene.py"
  - "src/world_engine/cockpit/crud/entities.py"
---

# Gatherings, encounters and passages

## Invariants

- **INV-23** Per-NPC uniqueness: each present NPC belongs to exactly ONE open
  gathering. Per-NPC, NOT per-location (several open gatherings in one
  location are legal). Defended on every join/migrate path. [no check]
- **INV-24** Dissolve-before-create lives in the caller (`enter_location`),
  never inside `generate_gatherings`. [no check]
- **INV-25** Creator-CRUD edits that change a character's
  `current_location_id`, or set an entity's `status` to a non-active value,
  close that entity's open `gathering_member` rows via
  `close_open_memberships` (gatherings are not canon — no `_apply_mutation`,
  no `change_history`). A location change also attaches the entity to the
  destination's live open gathering when the open session holds one there,
  and, after the commit, dissolves any gathering the move left with no
  active member. Roster and co-present reads gate on `entity.status='active'
  AND vital_status='alive'` in addition to `gathering_member.left_at IS
  NULL`. -- enforced by `gathering_lifecycle.py`
- **INV-26** An open gathering with no active member is a defect state:
  dissolved the moment it is emptied, and ignored by the entry guard where
  it survives — a location counts as entered only while one of its open
  gatherings still holds an active member. -- enforced by
  `gathering_lifecycle.py`
- **INV-27** `passage` is written only by `passages.py`, whose `before_flush`
  listener records every placement write; `rencontre.last_at` moves forward
  only, in `encounters.py`. -- enforced by `fact_learning.py`
