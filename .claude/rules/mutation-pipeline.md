---
paths:
  - "src/world_engine/analyzer*.py"
  - "src/world_engine/tick*.py"
  - "src/world_engine/observation_*.py"
  - "src/world_engine/day_mutations.py"
  - "src/world_engine/cockpit/mutations.py"
  - "src/world_engine/cockpit/routes/mutations.py"
  - "src/world_engine/writes/knowledge.py"
---

# The mutation pipeline: proposers and appliers

## Invariants

- **INV-28** `relation_change` is owned by window analysis (`analyze_window`,
  `proposed_by='local_ai_window'`): at most one `relation_change` per NPC
  pair per window, proportionate to that window. Never deduplicated against
  prior windows (not covered by `_mutation_match_key`). [no check]
- **INV-29** `new_knowledge` / `status_change` are idempotent facts:
  identity-based dedup (`entity_id` + `fact_refs.knowledge_key`; `entity_id`)
  via `_mutation_match_key`, same conversation required. [no check]
- **INV-30** `relation_change`'s `entity_a_id`/`entity_b_id` come from the
  model's payload. Missing -> skip and log (`_normalize_to_schema` returns
  `None`); never attributed via a conversation-level default. [no check]
- **INV-31** Knowledge levels never decrease through the mutation pipeline:
  `unaware < rumor < suspicious < partial < knows < fully_understands` is
  monotone for every `knowledge_change` apply (`_apply_mutation`'s "level
  already >= proposed" guard). `analyze_overhearing` also caps acquired or
  upgraded levels at `knows` in code; `analyze_window` has no structural
  cap. Downgrades, forgetting and `is_incorrect` correction are creator CRUD
  only. [no check]
- **INV-32** `new_knowledge`'s `subject_entity_id` is untrusted payload
  input, re-validated against an active entity of the mutation's own world
  at apply, and never part of a dedup key. [no check]
- **INV-33** `resource_change` writes two canon tables (`ledger` + optional
  `knowledge`) inside one `_apply_mutation` SAVEPOINT — the single sanctioned
  exception to one-branch-one-table. Its money leg accumulates (never
  deduped) and targets the player only; its knowledge leg is idempotent,
  guarded at apply time. [no check]
- **INV-34** Tick-sourced `proposed_mutation` rows have
  `source_type='world_tick'`, `proposed_by='local_ai_tick'`, NULL
  `pass_play_id`/`conversation_id`, and a mandatory `tick_id` (one UUID per
  `run_world_tick`). `_find_applied_duplicate`'s tick branch
  (`cockpit/routes/mutations.py`) is canon-existence-based, never a
  `tick_id`-scoped history comparison, and is never extended to
  `relation_change`. [no check]
