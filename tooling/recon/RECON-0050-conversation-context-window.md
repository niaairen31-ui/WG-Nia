# RECON-0050 — conversation context window (sliding summary + K-verbatim + scene tail)

Branch: `main`. Schema: v1.88. Tarball: fresh (`codeload.github.com`, this session).
Report-only. All findings carry `file:line` anchors.

## Motivating problem

After ~8-10 turns the `huihui_ai/qwen3-abliterated:8b` NPC re-emits a near-identical
paragraph (same content, minor lexical noise) and the scene stops progressing. Diagnosis:
attention collapse from an uncapped raw history block, plus scene context stranded at the
prompt head where the history buries it.

## Turn assembly (the saturation site)

- `_say_persist_and_build_history` (`cockpit/play.py:113`) builds `npc_history` from **every**
  `player`/`npc` row with **no truncation** (`cockpit/play.py:145-149`). This is the growing
  block.
- `_say_npc_generation` (`cockpit/play.py:545`) assembles
  `npc_msg_list = [{"role":"system", ...}, *ctx.npc_history]` (`cockpit/play.py:577`) and streams
  via `ollama_client.chat_stream(..., NPC_DIALOGUE_OPTIONS)`. The full history sits between the
  system message and the current line, untouched.
- `npc_reaction` / possession-refusal paths append one-shot suffixes onto `npc_msg_list[0]`
  (`cockpit/play.py:578-593`) — any move of the message-list construction must preserve these.
- Seed NPC in a plain conversation reuses the **frozen** system prompt captured at conversation
  start (`injected_context["system_prompt"]`, `cockpit/play.py:138`, reused `:565`). Other
  responders get a fresh `assemble_npc_context` + `_npc_dialogue_system_prompt`
  (`cockpit/play.py:772` -> `f"{system_prompt}\n\n{context}"`).

## Why the scene "fait moyen de sens" (D2 target)

- Scene-bearing sections all render at the prompt **head**: `_npc_context_setting`
  (`context.py:267`), `_npc_context_perception` (`context.py:334`), `_npc_context_company`
  (`context.py:383`). Assembled by `assemble_npc_context` (`context.py:460`). At 8-10 turns they
  are buried behind the history block. Re-injecting a compact scene tail after the verbatim window
  is the cheapest grounding lever.

## Configurable-model requirement — already solved by existing infra

- `PromptTemplate.model` override column (`models/pipeline.py:184`), resolved by
  `effective_model(template, default)` (`prompt_registry.py:42`): NULL = code default, non-NULL =
  creator override.
- Creator write path already exists: `PATCH /api/prompts/{id}/model` (CLAUDE.md:302), backed by
  the `model` write in `cockpit/crud/prompts.py:327`, validated fail-closed against the live
  registry.
- Every usage carries a `PROMPT_REGISTRY` entry (`prompt_registry.py`) with a `default_model`
  callable — `_author_model` -> `llama3.1:8b` (`entity_author.py:39`), `_game_model` ->
  `ollama_client.DEFAULT_MODEL` (`ollama_client.py:22`). A new `conversation_summary` usage with
  `default_model=_author_model` becomes creator-editable exactly like the others, with zero
  bespoke config work.
- No `conversation_summary` usage exists today (`prompt_registry.py`, `scripts/seed_pilot.py`).
- Non-streaming call available: `ollama_client.chat(...)` (`ollama_client.py:88`).

## Existing window pass (orthogonal, non-colliding)

- `analyze_window` (`analyzer.py:894`) walks turns since `conv.last_analyzed_turn`
  (`models/ephemeral.py:113`) and emits `proposed_mutation` rows (Tier 4 knowledge propagation).
  Triggered on conversation end (`cockpit/routes/play.py:202`) and explicit analyze
  (`cockpit/routes/play.py:607`). The C1 summary is a **prompt-compression artifact**, never
  canon, no `proposed_mutation`, no shared state — fully orthogonal.

## Config surface for I2 (creator-tunable budget / K)

- No key-value settings table exists (`models/*.py`). The in-doctrine pattern for world-scoped
  curated config is a **dedicated relational table** written via a curated-config chokepoint.
- Curated-config family: `write_npc_prices`, `write_location_subculture`, `write_world_laws`,
  `write_location_obstacles`, `write_location_doors` (all `writes/config.py`), plus the upsert-one
  `upsert_location_type` (`writes/config.py:339`). Per CLAUDE.md:276 these carry **no
  `change_history`** (metadata-config category), are **creator-CRUD / bootstrap only**, never
  reachable from AI or play paths.
- Their tables ARE listed in `[CANON_TABLES]` (`tooling/verify/canon_write_policy.txt`:
  `npc_price location_subculture world_law obstacle obstacle_vertex door location_type_catalog`
  ...) and their writers are registered in `[ALLOWED_SITES]`. So a new config table must be added
  to `[CANON_TABLES]` and its writer to `[ALLOWED_SITES]`, or `single_canon_write.py`
  (`tooling/verify/checks/single_canon_write.py:425`) fails.
- UI-visible config must be relational, not JSON — `json_ui_boundary` (CLAUDE.md:327).
- A new physical table must be a **static model table** or the boot guard rejects it:
  `schema_reconcile.unaccounted_tables` (CLAUDE.md:328).

## Load-bearing constraint — module budget

- Cap = 40 functions / 1000 physical lines (`tooling/verify/checks/module_budget.py:31-32`).
- Current sizes: `cockpit/play.py` = **990** (10 headroom), `analyzer.py` = 941,
  `context.py` = 902 (98 headroom), `models/canon.py` = **974** (26 headroom),
  `models/ephemeral.py` = 258, `models/pipeline.py` = 235.
- Consequence: the window/summary logic CANNOT grow `play.py`; it lands in a **new module**
  `src/world_engine/conversation_window.py` (G1), and `play.py`'s inline message-list
  construction is replaced by a call (net line delta ~0). The new config model class should NOT
  be added to the near-cap `canon.py`.

## Anti-repetition lever (K2)

- `NPC_DIALOGUE_OPTIONS = {"repeat_penalty": 1.25, "repeat_last_n": 256}` (`ollama_client.py:30`).
  `repeat_last_n: 256` covers only ~256 tokens, far below an 8-10 turn history — orthogonal cheap
  lever, to be measured (not blindly bumped) in brief (e).

## Note — TICKET-0046 landed

Constructeur sub-tab present in the cockpit (`cockpit/index.html:1209`, `:4220`, `:6968`);
`main` is clean at 0050.
