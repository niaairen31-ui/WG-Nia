---
id: TICKET-0076
title: Day chain prompt delivery — module-level hoist, one-shot seed, coverage guard
type: bug
status: live-gate
created: 2026-08-26
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]
blast_radius: small
brief_ids: [BRIEF-0076-a-day-prompt-hoist-and-coverage-guard]
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Le ticket 0075 est fermer, il concerne la nouvelle surface de jeu (jouer une
> journee) Lorsque j'essaye, j'ai un erreur, voila a quoi cela ressemble (en
> piece jointe). 1- est-ce normal ? 2- propose moi des options pour regle le
> probleme.

Attached screenshot: the Journee surface, day 2 `submitted`, "Emettre le plan"
returning in red:

> day extraction failed: day_extract: no active prompt_template for
> usage='day_extract_place'

## Clarifications resolved (intake)

**The observed behavior is correct; the observed state is not.** [M] The chain
refuses to call a model without an approved template rather than inlining a
prompt (`day_extract.py:106-108`), and `POST /api/day/{batch}/plan` wraps the
error as a 502 having written nothing (`routes/day.py:663`). What is wrong is
that the eight day-chain `prompt_template` rows have never reached the live DB:
[M] their only creation path is `scripts/seed_pilot.py`, and [M]
`cockpit/crud/prompts.py` exposes list / edit-text / restore-version /
set-model but no create endpoint. [M] No boot hook in `cockpit/app.py` and no
`tooling/verify/checks/*` check reads `prompt_template` from a live DB, so
nothing could detect corpus-vs-DB divergence.

**TICKET-0075 is not reopened.** Its briefs and code stand as merged. The
corrections below live here.

- **A2a+ (delivery)** -- hoist the 14 `DAY_*` prompt constants from inside
  `seed()` to module level in `scripts/seed_pilot.py` (text byte-identical),
  add a module-level `DAY_PROMPT_HEADS` descriptor carrying the eight head-field
  dicts, and ship `scripts/apply_ticket_0076_day_prompt_seed.py`, which embeds
  no prompt text and no head fields of its own.
  RECON note: plain A2a (text constants only) was the locked decision; [M]
  `upsert_prompt_template` (`seed_pilot.py:126-180`) also requires `name`,
  `usage`, `world_id`, `variables`, `destination`, which today live only inside
  the eight call sites in `seed()`. Without `DAY_PROMPT_HEADS` the one-shot must
  restate them -- a second source of truth. The descriptor is the minimum that
  keeps one.
  Rejected: **A1** (`seed_pilot.py` whole) -- [M] converges head fields on all
  37 templates, converges `knowledge` rows, deletes `kn-reike-incidents`
  (`seed_pilot.py:3207`), realigns `rel-unnamed-tavern` to 85
  (`seed_pilot.py:3333`); canon side effects unrelated to delivering a prompt.
  Reactivation: a full pilot reconvergence is wanted for its own sake.
  Rejected: **A3** (manual SQL) -- bypasses `write_prompt_version`, leaves a
  versionless head, [M] the state `upsert_prompt_template:162-166` treats as
  corruption. No reactivation.
- **B2 (guard placement)** -- coverage guard at `POST /api/day/declare`
  (`routes/day.py:163`), before any write. Rejected: **B1** (boot guard) -- one
  missing prompt would stop every surface from serving. Reactivation: a second
  chain ships and per-surface guards start duplicating. Rejected: **B3**
  (advisory report) -- contradicts structural-over-disciplinary.
- **D2 only (derivation)** -- `DAY_CHAIN_USAGES` derived from `PROMPT_REGISTRY`
  via `call_sites` resolving into `src/world_engine/day_*.py`. No literal usage
  list in the module. The D1/D2 cross-agreement rule I recommended is
  **dropped** on Nia's instruction ("D2 seulement").
  RECON note: [M] `surface` cannot carry this -- it is a two-value field
  (`prompt_registry.py:55`), and all 8 day usages share `surface="play"` with 16
  others (`npc_dialogue`, six `mj_*`, both `observation_*`, `world_tick`, ...).
  Rejected: **D1** (usage-key prefix) -- lexical, drifts silently on a rename.
  Reactivation: none foreseen. Rejected: **D3** (new `PromptSpec.chain` field)
  -- one reader, and a forgotten `chain="day"` on a future entry falls out of
  the guard as silently as D1. Reactivation: a day-chain prompt must live
  outside a `day_*.py` module, or a second chain needs the same treatment.
- **Exemption inside D2** -- [M] `day_feasibility.py:186-188` returns
  `_unavailable(...)` instead of raising: BRIEF-0075-g decision Y1's designed
  degradation. Requiring it at `/declare` would convert a tolerated absence into
  a refusal. `day_feasibility` is exempt, and the exemption is recomputed by the
  G1 check rather than trusted.
- **E2 (guard depth)** -- the guard requires an active template AND at least one
  `prompt_version` row. Rejected: **E1** (active template only) -- [M]
  `prompt_store.current_prompt:31-35` raises `RuntimeError` on a versionless
  head one line past the loader, outside the 502 wrapper. E1 would prove the
  loader returns non-None, not that the chain can start.
- **TICKET-0075 closure is picked up here**: front-matter `status: escalated`
  -> `done` only. [M] `tooling/questions/QUESTION-TICKET-0075.md` (the
  `continue` verdict / `agenda_step_change` widening) was answered directly to
  Claude Code out of band -- **not touched by this ticket**, neither the file
  nor the verdict.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] The 14 `DAY_*` prompt constants are module-level in `scripts/seed_pilot.py`, and `seed()` assigns none of them  ->  verify/checks/day_prompt_delivery.py
- [ ] `DAY_PROMPT_HEADS` is module-level, has 8 entries, and `seed()` reads it rather than restating head fields  ->  verify/checks/day_prompt_delivery.py
- [ ] `scripts/apply_ticket_0076_day_prompt_seed.py` embeds no prompt text and no head-field literal: its only string constant over 200 chars is its module docstring  ->  verify/checks/day_prompt_delivery.py
- [ ] `src/world_engine/prompt_coverage.py` derives `DAY_CHAIN_USAGES` from `PROMPT_REGISTRY` `call_sites`, with no usage string literal anywhere in the module  ->  verify/checks/day_prompt_delivery.py
- [ ] The exempt set is recomputed by AST from the `day_*.py` missing-template branches (`raise` = required, `return` = exempt) and equals the module's declared exemption  ->  verify/checks/day_prompt_delivery.py
- [ ] `missing_usages` requires an active template AND at least one `PromptVersion` row (E2)  ->  verify/checks/day_prompt_delivery.py
- [ ] `declare_day` calls `missing_usages` strictly BEFORE `write_batch` -- call order, not mere presence  ->  verify/checks/day_prompt_delivery.py
- [ ] Every rule above is vacuity-guarded: a rule collecting zero items FAILS  ->  verify/checks/day_prompt_delivery.py
- [ ] `prompt_registry.py`'s seed/registry bijection still passes after the hoist  ->  verify/checks/prompt_registry.py
- [ ] `routes/day.py` stays within the 1000-line / 40-function budget  ->  verify/checks/module_budget.py

### Live  ->  human gate (Nia)
- [ ] `python scripts/apply_ticket_0076_day_prompt_seed.py` on the live DB prints 8 `created` lines; a second run prints 8 `existing` lines and changes nothing.
- [ ] Day 2, already `submitted`, emits its plan with no extraction error.
- [ ] A full day runs end to end: declare -> plan -> resolve -> prose account, with the proposed mutations landing in the review queue.
- [ ] With `pt-day-extract-place` set `is_active=0` by hand, `POST /api/day/declare` refuses with a 503 naming `day_extract_place` and the script to run; the message is visible in the Journee surface. Re-enabling it restores normal declaration.
- [ ] With `pt-day-feasibility` set `is_active=0` by hand, a declaration is still ACCEPTED and the day resolves with the veto reported unavailable.
