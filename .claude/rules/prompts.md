---
paths:
  - "src/world_engine/prompt_*.py"
  - "src/world_engine/writes/prompts.py"
  - "src/world_engine/cockpit/crud/prompts.py"
  - "src/world_engine/cockpit/routes/prompts.py"
  - "scripts/seed_pilot.py"
---

# Prompts

## Invariants

- **INV-47** `prompt_template.model` is written ONLY via `PATCH
  /api/prompts/{id}/model`, validated fail-closed against live Ollama.
  -- enforced by `prompt_model_write.py`
- **INV-48** Prompt text lives ONLY in the append-only `prompt_version`
  table, never UPDATE/DELETE. -- enforced by `prompt_version.py`
