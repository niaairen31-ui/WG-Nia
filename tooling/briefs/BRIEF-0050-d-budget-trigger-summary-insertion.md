# BRIEF-0050-d — Step "budget trigger + summary recompute + insertion"

## Context

Bricks in place: the config (a), the capped message list with an empty summary slot + scene tail
(b), and the `conversation_summary` prompt usage (c). This step fills the slot. When a conversation
is over the word budget AND `summary_enabled` is true for the world, summarize the older turns
(the `older` half from `split_verbatim_tail`) via the `conversation_summary` prompt and insert the
result into the summary slot. Per F1 (C1 is ephemeral, nothing persisted), the summary is
recomputed on each over-budget turn — accepted latency cost. This closes the A/B: with the flag on,
the model gets summary(older) + verbatim(K) + scene tail; with it off, it gets the cap-only
baseline from brief (b).

## Scope IN

1. **Summary template loader** `_load_summary_template(world_id, db) -> PromptTemplate` in
   `src/world_engine/conversation_window.py`, mirroring `_load_npc_dialogue_template`
   (`cockpit/play.py:752`): select active `usage="conversation_summary"` templates, prefer
   `world_id == world_id` then `world_id is None`, raise HTTP 503 if none. (This is the call site
   named in the registry entry from brief c.)

2. **Summarizer** `summarize_older_turns(older: list[dict], world_id, db) -> str` in
   `conversation_window.py`:
   - If `older` is empty, return `""` (no call).
   - Render the older turns into a plain transcript string (label player vs npc lines, e.g.
     `[Joueur] ...` / `[PNJ] ...`, reusing the labeling style at `cockpit/play.py:194-199`).
   - Resolve the model: `template = _load_summary_template(...)`;
     `model = effective_model(template, _author_model())` (import `effective_model` from
     `prompt_registry`, `_author_model` per the registry's resolver). This is what routes a creator
     override.
   - Call `ollama_client.chat([{ "role": "system", "content": template.<active version
     system_prompt> }, { "role": "user", "content": transcript }], model=model)` — NON-streaming
     (`ollama_client.chat`, `ollama_client.py:88`). Resolve the active version via `current_prompt`
     next to the load, same as other call sites (do NOT read `template.system_prompt` raw; use the
     resolved version's `system_prompt` + substitute `{transcript}` into `user_template`).
   - Return the model's text, stripped. On `ollama_client.OllamaError`, REPORT via log and return
     `""` (fail-soft: a summary failure must NOT abort the turn — the NPC still answers with the
     cap-only input). Flagged decision: fail-soft, not fail-closed, because this is a prompt
     enrichment, not a canon gate.

3. **Wrap the summary as a system note**: `format_summary_note(summary_text: str) -> str` in
   `conversation_window.py`, wrapping non-empty text with a verbatim lead line:
   `[RESUME DE CE QUI PRECEDE — contexte, non rejouable tel quel]` followed by the summary.
   Empty text -> return None (no note).

4. **Wire into the assembly.** In `build_npc_message_list` (brief b) OR at its `_say_npc_generation`
   call site, when `over` is true AND `load_conversation_window_config(world_id, db).summary_enabled`
   is true: compute `older, recent = split_verbatim_tail(npc_history, verbatim_turns)`,
   `note = format_summary_note(summarize_older_turns(older, world_id, db))`, and pass
   `summary_note=note` into `build_npc_message_list`. Keep the branch inside
   `conversation_window.py` (a single `assemble_npc_turn_input(...)` orchestrator is acceptable and
   preferred so `play.py` calls one function). `play.py` MUST stay < 1000 lines — confirm `wc -l`.

5. **Structural guarantee that the summary is never persisted.** No function in
   `conversation_window.py` may INSERT/UPDATE a `ConversationMessage` or any canon row. Add verify
   check `tooling/verify/checks/summary_not_persisted.py` (standard idiom, vacuous-proof): AST- or
   grep-scan `conversation_window.py` for `ConversationMessage(`, `.add(`, `session.add`, `INSERT`,
   `UPDATE` against canon tables — FAIL if any write of summary/message content is found. (Reads and
   the config upsert are elsewhere; this module is read + compute only.)

## Scope OUT

- Do NOT persist the summary anywhere — not on `conversation`, not a new column, not a cache table.
  C1 is ephemeral by decision. If latency proves painful, that is a SEPARATE future ticket
  (named deferral D-0050-cache), not this brief.
- Do NOT advance `conv.last_analyzed_turn` or touch `analyze_window` (`analyzer.py:894`) — that is
  the orthogonal Tier 4 mutation pass; the summary must not couple to it.
- Do NOT emit any `proposed_mutation` from the summary path.
- Do NOT gate the K-cap on `summary_enabled` (brief b already applies it on the budget condition);
  only the summary NOTE is gated by the flag.
- Do NOT make the summary fail-closed (abort the turn) — fail-soft to `""`.
- Do NOT add creator UI here — brief (e).

## Invariants to defend

- **C1 ephemeral / summary is not canon**: enforced structurally by
  `summary_not_persisted.py`; the summary lives only inside the assembled prompt.
- **model proposes, code judges**: the summary is prose fed back to the model, never a mutation;
  no canon write.
- **module budget**: all new logic in `conversation_window.py`; `play.py` stays < 1000 lines.
- **history is sacred**: the summarizer reads persisted rows, writes nothing.

## Done means

- [ ] Live, `summary_enabled=true`, past budget: the NPC input carries a
      `[RESUME DE CE QUI PRECEDE ...]` system note summarizing the dropped older turns, followed by
      the last K verbatim messages and the scene tail; the NPC's reply reflects earlier facts it
      would otherwise have lost, without re-emitting the saturated paragraph.
- [ ] Live, `summary_enabled=false` (set on the active world via `upsert_...` for now): no summary
      note appears; the input is the cap-only baseline from brief (b). The two modes are visibly
      different.
- [ ] Changing the `conversation_summary` model override (prompts tab) routes the summary call to
      the chosen model (confirm via Ollama server logs or a model-echo probe).
- [ ] Killing the summary model mid-turn (simulate `OllamaError`) does NOT abort the turn — the NPC
      still answers with the cap-only input; the failure is logged.
- [ ] `python tooling/verify/checks/summary_not_persisted.py` PASSES; adding a stub
      `ConversationMessage(...)` write to the module makes it FAIL.
- [ ] `wc -l src/world_engine/cockpit/play.py` < 1000; `module_budget.py` PASSES.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: record F1 (per-over-budget-turn recompute, ephemeral), the fail-soft
  choice, and the orthogonality to `analyze_window`. Add named deferral **D-0050-cache** (persisted
  summary cache) as explicitly NOT done.
- This step is otherwise its own doc (no schema change).
