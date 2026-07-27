---
id: TICKET-0050
title: Conversation context window — sliding summary, K-verbatim tail, scene re-injection
type: feature
status: brief
created: 2026-07-27
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
brief_ids: [BRIEF-0050-a, BRIEF-0050-b, BRIEF-0050-c, BRIEF-0050-d, BRIEF-0050-e]
schema_version_touched: vX.YY  # Claude Code assigns; one migration adds conversation_window_config
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> J'ai reflechi a la fluidite de mes echanges avec les NPC. Apres quelques echanges, le 8b
> abliterated commence a se repeter. Je me dis que si j'ai une petite analyse qui roule tous les
> x mots, qui fait un petit resume et corrige le prompt, le prompt serait simplifie et
> comprendrait les elements essentiels (la majeure partie du prompt ne change pas, juste la
> conversation resumee et peut-etre autre chose eventuellement).

Refined during intake: the NPC re-emits a near-identical paragraph after ~8-10 turns, content
loosely tracks the scene, nothing progresses. Root cause is an uncapped raw history block
(attention collapse) plus scene context stranded at the prompt head.

## Clarifications resolved (intake)

- **A2** — sliding summary PLUS K most-recent turns verbatim (not summary-only; verbatim tail is
  the anti-collision lever).
- **B2** — trigger on a word budget of accumulated history, not a fixed turn count.
- **C1** — the summary is an ephemeral prompt artifact, recomputed, never persisted as canon.
- **D2** — scene context re-injected as a compact tail just before the current line, not only at
  the head.
- **E1** — summary scope is per `conversation`, not per `gathering`.
- **F1** — under C1, the summarizer runs on each over-budget turn (accepted latency cost).
- **G1** — new module `src/world_engine/conversation_window.py`; `play.py` must not grow (budget).
- **H1** — message list shape: `[behaviour+context system, summary note, *verbatim_K, scene
  tail]`.
- **I2** — word budget and K are creator-configurable now (persisted, relational).
- **J1 / O** — single ticket, five briefs (a-e) in the sequence below.
- **K2** — measure a `repeat_last_n` bump in brief (e); do not blindly change it.
- **L1** — dedicated narrow relational table `conversation_window_config` (world-scoped, one row
  per world), curated-config write chokepoint (upsert-one), reader applies defaults when absent.
- **M1** — `summary_enabled` BOOL, server default TRUE; the K-cap + scene tail always apply above
  budget, the summary recovery is gated by this flag (enables live A/B of summary vs cap-only).
- **N2** — the config fields (budget, K, enabled) are edited on the existing prompts surface,
  beside the `conversation_summary` template row. Named deferral D-0050: migrate this editing to a
  dedicated world-configuration surface once one exists.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `conversation_window_config` is a static model table with columns `world_id` (unique),
      `word_budget` INT, `verbatim_turns` INT, `summary_enabled` BOOL default 1; DDL-text asserted
      via `sqlite_master`  -> verify/checks/conversation_window_config.py
- [ ] `conversation_window_config` present in `[CANON_TABLES]` and its writer registered in
      `[ALLOWED_SITES]`; `single_canon_write.py` passes  -> existing check
- [ ] `conversation_window` module under the 40/1000 budget; `play.py` still under budget after
      the message-list construction is externalized  -> existing module_budget.py
- [ ] `conversation_summary` appears in `PROMPT_REGISTRY` with `default_model=_author_model`, and
      a seeded `prompt_template` row exists for it  -> verify/checks/conversation_summary_usage.py
- [ ] the summary artifact is never persisted: no write of summary text to any table (grep-guard
      that `conversation_window` performs no INSERT/UPDATE of ConversationMessage or any canon
      row)  -> verify/checks/summary_not_persisted.py
- [ ] config fields are relational-only on the edit surface; `json_ui_boundary.py` passes

### Live  ->  human gate (Nia)
- [ ] In a live session past the word budget, the NPC no longer re-emits the saturated paragraph;
      the reply reads as a continuation, not a restart.
- [ ] Setting `summary_enabled = false` on the active world (prompts tab) yields the cap-only
      baseline; setting it back to true restores the summarized older context. Both are visibly
      different and both beat the pre-0050 behavior.
- [ ] Editing `word_budget` / `verbatim_turns` on the active world changes when the summary kicks
      in and how much verbatim tail survives, observable in a live long conversation.
- [ ] Changing the `conversation_summary` model override in the prompts tab routes the summary
      call to the chosen model (verified by a dry-run or model-echo).
- [ ] Replay-harness report (brief e) shows the turn at which repetition reappears for
      K in {2,4,6} and at least two `word_budget` values, with a recommended default pair.
