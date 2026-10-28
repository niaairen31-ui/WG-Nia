---
paths:
  - "src/world_engine/creation_rules.py"
  - "src/world_engine/creation_check.py"
  - "src/world_engine/writes/creation_rules.py"
  - "src/world_engine/writes/pc_drafts.py"
  - "src/world_engine/pc_draft_reads.py"
  - "src/world_engine/cockpit/routes/player_creation.py"
  - "src/world_engine/pc_review_reads.py"
  - "src/world_engine/cockpit/routes/pc_review.py"
  - "src/world_engine/cockpit/pc_approval.py"
  - "src/world_engine/writes/player_characters.py"
---

# Character creation

A world's creation rules live in one `creation_rules` row (a missing row
is every default); a system and a skill override visibility and the
maximum rank, a system caps its raised and held skills. Costs are per
step; lowering a held skill to Inexpérimenté gives back the Initié cost.

The creator reviews a submitted draft beside the player's version,
prepares one NPC batch per group of people to create, returns the draft
with a note or approves it in one transaction.

## Invariants

- **INV-67** A character-creation skill sheet -- the player's, the
  designer's, the one submitted -- is judged only by
  `creation_check.check_creation`, over the rules read by
  `creation_rules`; no other module computes a sheet's cost or
  verdict. A draft is submitted only when `creation_check.check_draft`
  finds nothing, and no draft row reaches canon before the creator
  approves it.
  -- enforced by `creation_budget.py`, `player_creation.py`
- **INV-68** A drafted character reaches canon only through
  `pc_approval.approve_draft`: one transaction, refused unless
  `check_review` and `review_blockers` find nothing; the review never
  edits the player's version (`pc_draft_reads.py` names no review
  column), and a review batch is written only by the approval.
  -- enforced by `draft_approval.py`, `creator_review.py`
