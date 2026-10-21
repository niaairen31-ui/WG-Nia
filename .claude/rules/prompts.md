---
paths:
  - "src/world_engine/prompt_*.py"
  - "src/world_engine/writes/prompts.py"
  - "src/world_engine/cockpit/crud/prompts.py"
  - "src/world_engine/cockpit/routes/prompts.py"
  - "scripts/seed_pilot.py"
  - "src/world_engine/world_premise.py"
---

# Prompts

## Invariants

- **INV-47** `prompt_template.model` is written ONLY via `PATCH
  /api/prompts/{id}/model`, validated fail-closed against live Ollama.
  -- enforced by `prompt_model_write.py`
- **INV-48** Prompt text lives ONLY in the append-only `prompt_version`
  table, never UPDATE/DELETE. -- enforced by `prompt_version.py`
- **INV-65** A world's premise reaches a model only through `{world_premise}`,
  filled by `world_premise.fill` (via `prompt_store.premised_prompt` or
  `prompt_call.call_json`), in the regime its usage declares
  (`PromptSpec.premise`). The `player` regime carries the world's name,
  description, tone and laws only -- never a skill system, never a state.
  -- enforced by `world_premise.py`
