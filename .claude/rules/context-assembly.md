---
paths:
  - "src/world_engine/context*.py"
  - "src/world_engine/cockpit/play*.py"
  - "src/world_engine/scene_format.py"
---

# Context assembly and play

## Invariants

- **INV-35** Constraint gating is structural: gagged/restrained/blindfolded
  effects are enforced in Python before any model call (`_stream` in
  `app.py`). Blindfolded exclusion is a data exclusion in
  `assemble_mj_context`, never a "don't describe" prompt. [no check]
- **INV-36** The condition ladder is monotone for engine writes:
  `unharmed -> bruised -> injured -> neutralized` — forward only by
  violent-verdict code; backward only by creator CRUD. [no check]
- **INV-37** A frozen scene yields no model calls: `scene_state.frozen =
  True` -> `/say` short-circuits with a fixed MJ message. Only the creator
  panel unfreezes. [no check]
- **INV-38** A PC is excluded from NPC co-presence by construction: the
  `H_COMPANY` query in `assemble_npc_context` carries
  `Character.character_type != "player"`. Do not widen this filter, and do
  not repoint it at NPC-to-NPC observation without a decision. [no check]
- **INV-39** `_npc_dialogue_system_prompt(system_prompt, context)` in
  `cockpit/play.py` is the single npc_dialogue system-prompt construction:
  every live call site and the Prompts tab's preview call it — never an
  inline concatenation. [no check]
- **INV-40** Affinity tiers are resolved in code (`context.py`'s
  `_affinity_tier`); prompt templates never carry the tier table. [no check]
