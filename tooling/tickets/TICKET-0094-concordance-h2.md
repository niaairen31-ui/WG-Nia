---
id: TICKET-0094
title: Concordance H2 — the model chooses, the code judges
type: feature
status: exec
created: 2026-09-25
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
lot_id: LOT-0094-concordance-h2.md
brief_ids: [A, B, C, D]
current_brief: D
schema_version_touched: v2.07
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> « se rendre au cas le plus probable en tenant compte du contenu des fiches,
> du lore et de ce que le joueur vient de dire »

(H2, locked in principle before TICKET-0092; sequence Z1a: 0093 judge →
0094 H2 → 0095 K1.)

## Clarifications resolved (intake)

- TICKET-0093 passed (Nia, 2026-09-25); A closes its front matter.
- Measured (0093 diagnostic): no stored ambiguity, zero appellations in
  prod. H2 first acts through near and partial names.
- Nia prioritizes quality over latency (X3b).

## Decisions locked (do not re-litigate without Nia)

- **Y1b** — two tickets: 0094 = H2, 0095 = K1.
- **Y2b** — the model is called on a named ambiguous mention, and on a named
  unmatched mention with partial or near candidates; cast stays
  deterministic.
- **Y3b** — new non-canon append-only table `day_mention_choice`, one row per
  call; an accepted choice is stored in `day_mention_resolution` as
  `matched` with `rung='model_choice'`.
- **Y4b** — evidence = what the character knows about each candidate.
- **Y5c** — one retry, then today's behaviour.
- **Y8a** — the retry fires on a technical failure only.
- **X1b** — every call is recorded, including on the 409 path, in its own
  transaction keyed by the day.
- **X2b** — ambiguous: the excerpt comes from the chosen candidate's facts;
  near: from the declaration or the chosen candidate's facts.
- **X3b** — no bound on calls per declaration.
- **X4a** — a missing prompt refuses the declaration (coverage guard).
- **Y6b / Y7b** — N6a widening and Q1b come after K1.
- Rejected, with reactivation conditions:
  - Y2a (ambiguous only): if K1 shows near choices contested more often than
    accepted.
  - Y2c (model casting): if a `cast` row is contested in review.
  - Y3a (columns on `day_mention_resolution`): if a reader must filter
    resolutions by the model's verdict without a join.
  - Y4a (names only): no reactivation — the judge would have nothing to
    check.
  - Y4c (recent history as evidence): if K1 shows a refusal « excerpt not
    found » where the right entity was among the candidates.
  - Y5a (unmatched on failure, no 409): if the remaining 409 blocks more than
    one day per week of play.
  - Y8b (retry on judge refusal): if more than 20 % of refusals are « excerpt
    not found » on choices K1 confirms.
  - X1a (log only): if K1 never displays a refused choice.
  - X1c (ambiguous → unmatched): if Y5a reactivates.
  - X2a (any fact): no reactivation.
  - X2c (chosen facts only): if K1 shows contested near choices that cited
    the declaration.
  - X3a (bound of 3): if a plan with choices takes Nia longer than she accepts
    at the live gate.
  - X4b (degrade silently): if Nia wants to switch H2 off by removing its
    prompt.

## Carried forward / open

- **TICKET-0095 — K1 review loop.** Reads `day_mention_choice`; decides what
  « agree » writes (creator CRUD vs `_apply_mutation`).
- Rejections whose condition is K1 (N11b, N14c, N17c from 0092).
- Y6b (N6a), Y7b (Q1b) after K1.
- Near/partial candidates display only the entity name, not the matched
  appellation (drafting judgment; revisit in K1).

## Acceptance criteria

<!-- One arrow per line: run.py follows the first arrow on a line only. -->

### Machine-checkable  ->  G1 deterministic gate
- [ ] Choice records are validated, stored and append-only  -> verify/checks/day_mention_choice_store.py
- [ ] Narrowing, judge, call and wiring hold their case tables  -> verify/checks/day_choice.py
- [ ] Day concordance keeps its rungs and purity  -> verify/checks/day_concordance.py
- [ ] Day concordance golden cases hold  -> verify/checks/day_concordance_golden.py
- [ ] Rewrite trace stays append-only with one plan-time extraction  -> verify/checks/day_rewrite.py
- [ ] Names, near names and scopes resolve as before  -> verify/checks/name_resolution.py
- [ ] Name index regimes stay confined  -> verify/checks/name_index.py
- [ ] The resolver stays pure  -> verify/checks/lore_resolve.py
- [ ] Prompt registry and seed stay in bijection  -> verify/checks/prompt_registry.py
- [ ] Day prompt heads, constants and coverage match  -> verify/checks/day_prompt_delivery.py
- [ ] Schema version agrees across code and doc  -> verify/checks/schema_version_agreement.py
- [ ] Schema doc and changelog partition holds  -> verify/checks/schema_partition.py
- [ ] Every canon write site is declared  -> verify/checks/single_canon_write.py
- [ ] Fact text is read only through the render chokepoint  -> verify/checks/identity_tokens.py
- [ ] No module-level import cycle  -> verify/checks/import_cycle.py
- [ ] Module line and function budgets hold  -> verify/checks/module_budget.py
- [ ] Function length ceiling holds  -> verify/checks/function_length.py
- [ ] CLAUDE.md contract holds  -> verify/checks/claude_md_contract.py
- [ ] Decisions index matches the archive  -> verify/checks/decisions_index.py
- [ ] Ticket front matter conforms  -> verify/checks/pipeline_state.py
- [ ] Full corpus is green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] On prod: `scripts/migrate_v2_07_day_mention_choice.py` then
      `scripts/apply_ticket_0094_mention_choice_seed.py` (prints `created
      prompt_template/pt-day-mention-choice`); the cockpit starts.
- [ ] Near: a declaration naming a known NPC with a typo (e.g. « Maelys » for
      Maelis) plans without a germ; the plan's concordance lists the NPC with
      rung `model_choice`.
- [ ] Ambiguous: with two NPCs sharing an appellation the character knows and
      a fact that distinguishes them, the day plans on the right one; with no
      distinguishing fact, the day 409s as before.
- [ ] After both, `day_mention_choice` holds one row per call, including the
      409 attempt, with excerpt and reason readable.
- [ ] The resolved narration of the near day names the chosen NPC without a
      judge refusal.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
