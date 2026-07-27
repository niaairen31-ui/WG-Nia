# BRIEF-0050-b — Step "K-verbatim cap + scene-tail re-injection"

## Context

The saturation bug is the uncapped history block (`cockpit/play.py:145-149`) feeding the NPC
model between the system message and the current line (`cockpit/play.py:577`). This step stops the
saturation: above the word budget, the history handed to the model is capped to the last K
player/npc rows, and a compact scene tail (D2/H1) is appended just before the current line so the
model's last read is the present scene, not a stale exchange. Below budget, behavior is unchanged.
The summary that RECOVERS the dropped older turns is brief (d); this brief deliberately ships the
degraded-but-bounded baseline first — it already beats the pre-0050 behavior and is independently
live-testable. Reads config from brief (a); no summarization here.

## Scope IN

1. **Word-count + split helpers** in `src/world_engine/conversation_window.py`:
   - `history_word_count(npc_history: list[dict]) -> int` — total whitespace-split word count over
     the `content` of the player/npc message dicts (the same list built at
     `cockpit/play.py:145-149`). Pure, no DB.
   - `split_verbatim_tail(npc_history, k) -> tuple[list[dict], list[dict]]` returning
     `(older, recent_k)` where `recent_k` is the last `k` messages (or the whole list if shorter)
     and `older` is the prefix. Pure.

2. **Scene-tail assembler** `assemble_scene_tail(npc_id, location_id, gathering_id,
   player_condition, db) -> str` in `src/world_engine/context.py` (98 lines of headroom; it is
   context assembly, its semantic home). Returns a SHORT block (aim <= ~6 lines) re-stating: the
   location name + one-line setting, who is currently present (co-presents by public name), and the
   player's current condition if any. Reuse the existing section builders where possible
   (`_npc_context_setting` `context.py:267`, `_npc_context_perception` `context.py:334`) rather
   than duplicating their reads; if reuse is impractical without exceeding the module budget,
   REPORT it and inline a minimal read — do not silently balloon `context.py`. Wrap the block with
   an explicit lead line, verbatim:
   `[SCENE — etat courant, prioritaire sur l'historique ci-dessus]`

3. **Message-list builder** `build_npc_message_list(*, system_prompt, npc_history, scene_tail,
   word_budget, verbatim_turns, summary_note=None) -> list[dict]` in
   `conversation_window.py`. Logic:
   - Start `msgs = [{"role": "system", "content": system_prompt}]`.
   - If `summary_note` is not None, append `{"role": "system", "content": summary_note}` (the slot
     stays UNUSED in this brief — always None here; brief (d) fills it).
   - Compute `over = history_word_count(npc_history) > word_budget`.
   - If `over`: `_, recent = split_verbatim_tail(npc_history, verbatim_turns)`; extend `msgs` with
     `recent`. Else: extend `msgs` with the full `npc_history` (unchanged below-budget behavior).
   - Append the scene tail as the LAST element before returning, as
     `{"role": "system", "content": scene_tail}` (H1: scene tail after the verbatim window; a
     system role keeps it out of the assistant/user alternation the model continues).
   - Return `msgs`.

4. **Wire it into `_say_npc_generation`** (`cockpit/play.py:545`). Replace the inline
   construction `npc_msg_list = [{"role": "system", ...}, *ctx.npc_history]`
   (`cockpit/play.py:577`) with a call to `build_npc_message_list(...)`, passing the resolved
   `responder_system_prompt`, `ctx.npc_history`, the scene tail from `assemble_scene_tail(...)`
   (resolved with the responder's id, `ctx.conv.location_id`, `ctx.conv.gathering_id`, and the
   `ss_condition` already in scope), and `word_budget` / `verbatim_turns` from
   `load_conversation_window_config(ctx.world_id, db)`. `summary_note=None` in this brief.
   CRITICAL: the existing `npc_reaction` and possession-refusal suffix appends onto
   `npc_msg_list[0]` (`cockpit/play.py:578-593`) must keep operating on the returned list's first
   element (the behaviour+context system message) unchanged. Net line delta in `play.py` must be
   ~0 (remove the inline literal, add the call + a config read); `play.py` MUST stay < 1000 lines
   — if the config read pushes it over, extract the read into a one-line helper in
   `conversation_window.py` and call that. Confirm the final `wc -l`.

## Scope OUT

- No summarization, no `conversation_summary` prompt call, no `ollama_client.chat` for a summary —
  brief (d). `summary_note` stays None here.
- Do NOT gate the cap on `summary_enabled`. The cap + scene tail apply on the over-budget
  condition alone (they fix saturation regardless of the summary toggle). `summary_enabled` is read
  only in brief (d).
- Do NOT touch `assemble_mj_context` or the MJ narration path — this is the NPC dialogue prompt
  only.
- Do NOT change the persisted history or `_say_persist_and_build_history` — the full history is
  still stored; only what is HANDED to the model is capped.
- Do NOT re-run the whole `assemble_npc_context` for the tail; the tail is a compact re-statement,
  not a second full context.
- Do NOT introduce per-gathering scope — E1 is per conversation.

## Invariants to defend

- **history is sacred**: only the model-input slice is capped; every `player`/`npc` row remains
  persisted and untouched.
- **module budget**: new logic lives in `conversation_window.py`; `play.py` stays < 1000 lines
  (verify with `wc -l`), `context.py` stays < 1000 after `assemble_scene_tail`.
- **model extracts, code judges**: the scene tail is code-assembled from canon reads, never model-
  authored.
- **no structure without a reader**: `build_npc_message_list` and `assemble_scene_tail` have a
  live consumer in `_say_npc_generation` this same brief.

## Done means

- [ ] Live: a conversation UNDER the word budget produces the same NPC input as before (spot-check
      the assembled `npc_msg_list` length equals system + full history + scene tail).
- [ ] Live: past the budget, the NPC input is system(+empty summary slot) + last K messages +
      scene tail; the saturated-paragraph repeat no longer occurs, and the reply references the
      current scene tail (e.g. a co-present just introduced) rather than a stale turn.
- [ ] Lowering `verbatim_turns` (via a direct `upsert_conversation_window_config` for now) visibly
      shortens the verbatim tail in the next over-budget turn.
- [ ] `npc_reaction` (a wordless gesture) and a failed-possession refusal still receive their
      one-shot system suffix (behavior unchanged).
- [ ] `wc -l src/world_engine/cockpit/play.py` < 1000; `wc -l src/world_engine/context.py` < 1000;
      `python tooling/verify/checks/module_budget.py` PASSES.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: note D2 (scene tail re-injection) and H1 (message-list shape) as
  implemented, and that the cap applies on the budget condition independently of `summary_enabled`.
- This step is otherwise its own doc (no schema change).
