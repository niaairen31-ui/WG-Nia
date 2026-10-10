---
paths:
  - "src/world_engine/ollama_client.py"
  - "src/world_engine/cockpit/play*.py"
  - "src/world_engine/analyzer*.py"
  - "scripts/talk.py"
---

# Local model notes

Default game model for NPC dialogue and analysis:
**`huihui_ai/qwen3-abliterated:8b-v2`** via Ollama; authoring model:
`llama3.1:8b`. Per-template overrides exist (`prompt_template.model`,
cockpit Prompts tab, live dropdown from `GET /api/ollama/models`); NULL
resolves to the registry's `default_model` at read time, so env overrides
show through. `prompt_registry.effective_model` is the sole resolver.

- **Abliterated** = refusal mechanisms removed; maximally compliant,
  including to a player pushing for reveals. This makes it the strictest
  test of concealed knowledge: if secrets hold here, they hold anywhere.
  The creator checkpoint remains the real safety net.
- **Thinking mode:** Qwen3 emits `<think>...</think>` before answering;
  `ollama_client.strip_think()` handles all malformed variants. Policies by
  call site:
  - **NPC dialogue** (`talk.py`): `/no_think` in the user message.
  - **NPC dialogue** (cockpit `/say`, NPC phase): `chat_stream` +
    `_StreamThinkFilter`; thinking on, filtered before any token is
    yielded; reply buffered, never raw to the player.
  - **MJ narration** (`/say`, MJ phase): `chat_stream` + `/no_think` +
    filter as backstop; narration prose only streams to the player.
  - **MJ interpretation** (`/say`, phase 0): `chat()` + `/no_think` +
    `format="json"`; fallback to `dialogue` on any error — a
    misclassification must never break a turn.
  - **MJ arbitration** (`/say`, physical turns): `chat()` +
    `format="json"` + `/no_think`; falls back to
    `("physical", None, None, False)` on any failure.
  - **NPC initiative vote:** `chat()` + `format="json"` + `/no_think`;
    failure is silent.
  - **NPC initiative act:** `chat()` + `format="json"`, **no** `/no_think`
    (thinking helps the two-field contract `act_text`/`move`); falls back
    to `_NPC_INITIATIVE_ACT_FALLBACK` if the template isn't seeded; any
    error -> silent skip.
  - **Conversation analysis** (`analyzer.py`): thinking enabled;
    `strip_think` before JSON parsing.
- **French quality:** multilingual but not idiomatic-Mistral-grade;
  acceptable for validating logic. If narrative quality disappoints, that's
  a model-selection signal, not a code defect.
