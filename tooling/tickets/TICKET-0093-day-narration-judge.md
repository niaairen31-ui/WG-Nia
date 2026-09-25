---
id: TICKET-0093
title: Day narration — a judge that can pass
type: bug
status: live-gate
created: 2026-09-25
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [db_write]
blast_radius: medium
lot_id: LOT-0093-day-narration-judge.md
brief_ids: [A, B, C]
current_brief:
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> « j'ai beaucoup de journées qui ne se résolvent pas pour le moment »

> « Z1a » — fix the narration judge in its own ticket, before H2.

## Clarifications resolved (intake)

- A diagnostic (2026-09-25, prod read-only + a DB copy) measured the cause:
  1 fresh narration in 20 passes the judge, and no rejection is a name the
  model invented. See LOT-0093 R-29.
- No ambiguity (the 409 H2 targets) was observed in any stored day.
- The four historical days stuck in `resolving` without a `day_rewrite`
  stay as they are (Nia: « elles peuvent rester comme elles sont »).
- Nia has not played days recently; the stored data predates recent
  tickets. The fresh-narration measurement is on current `main` (204ed7c).

## Decisions locked (do not re-litigate without Nia)

- **Z1a** — the narration judge gets its own ticket first: 0093 = judge,
  0094 = H2, 0095 = K1. H2's live gate needs days that resolve.
- **J1'a** — the zero-names guard stays exactly as it is. Measured: it never
  rejected a prose that named no one; it caught a lower-cased prose and
  erased paragraphs.
- **J2'a** — the repair becomes code: the offending words are lower-cased by
  a pure function, no model call. The `day_narration_repair` prompt rows stay
  in the DB (history is sacred) and are no longer called.
- **J3a** — NPCs chosen by the cast verdict are named on the fact sheet and
  authorised, in this ticket.
- **J4'a** — sentence-initial capitalized words are handled by J2'a
  (lower-cased); the judge never ignores a sentence's first word.
- **J5b** — the model returns one text per step as JSON; the code writes the
  band markers.
- Rejected, with reactivation conditions:
  - J1'b (accept zero names when markers are present): reactivate if, after
    0093, a « zero names » rejection falls on a prose containing the
    character's name capitalized.
  - J2'b (widen the model repair): no reactivation — measured to make things
    worse.
  - J2'c (keep the model repair, fix its prompt): reactivate if J2'a lets
    through a prose Nia flags as unreadable at the live gate.
  - J4'b (ignore sentence-initial words): reactivate if Nia flags more than
    half the proses at the live gate as spoiled by a lower-case sentence
    start.
  - J5a (tolerant marker counting only): reactivate if more than 20 % of
    narrations fail with a 502 on invalid JSON after 0093.
  - J3b (cast in a separate ticket): no reactivation — measured defect.

## Carried forward / open

- **TICKET-0094 — concordance H2** (locked: Y1b, Y2b, Y3b, Y4b, Y5c, Y6b,
  Y7b, Y8a). Plan after 0093's live gate.
- **TICKET-0095 — review loop K1.** Its own decisions (what « agree »
  writes, creator CRUD vs `_apply_mutation`) are closed in its session.
- Q1b `knowledge.subject` after K1 (Y7b); N6a widening of the day chain in
  its own ticket after K1 (Y6b).
- The four stuck `resolving` days: no ticket (Nia).
- TICKET-0092's front matter still reads `status: live-gate` on `main`;
  Nia reports it passed. BRIEF-0093-A closes it in its own commit (R-32).

## Acceptance criteria

<!-- One arrow per line: run.py follows the first arrow on a line only. -->

### Machine-checkable  ->  G1 deterministic gate
- [ ] Cast NPCs are named and authorised on the fact sheet  -> verify/checks/day_fact_sheet_refs.py
- [ ] Code repair, beat assembly and band labels hold their case tables  -> verify/checks/day_narration_beats.py
- [ ] The narration chain keeps its guards, bounded code repair and retired model repair  -> verify/checks/day_narration.py
- [ ] Day prompt heads and constants match the retired repair  -> verify/checks/day_prompt_delivery.py
- [ ] Prompt registry and seed stay in bijection  -> verify/checks/prompt_registry.py
- [ ] Name extraction golden cases hold  -> verify/checks/day_name_extraction.py
- [ ] No module-level import cycle  -> verify/checks/import_cycle.py
- [ ] Module line and function budgets hold  -> verify/checks/module_budget.py
- [ ] Function length ceiling holds  -> verify/checks/function_length.py
- [ ] Decisions index matches the archive  -> verify/checks/decisions_index.py
- [ ] Ticket front matter conforms  -> verify/checks/pipeline_state.py
- [ ] Full corpus is green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] `scripts/apply_ticket_0093_narration_prompt.py` run on prod prints
      `pt-day-narration: vN -> vN+1`.
- [ ] Of 5 new days declared, planned and resolved on current `main`, at
      least 4 resolve on the first click on « Résoudre ».
- [ ] Every resolved narration shows exactly one marker per step, in step
      order, matching each step's outcome.
- [ ] The prose is readable: no text in brackets, no fully lower-cased
      paragraph.
- [ ] « Prompts » no longer lists `day_narration_repair`.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
