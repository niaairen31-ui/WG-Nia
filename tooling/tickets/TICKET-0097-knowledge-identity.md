---
id: TICKET-0097
title: Knowledge identity — a knowledge row is who knows which fact; knowledge.subject goes
type: feature
status: live-gate
created: 2026-09-28
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: large
lot_id: LOT-0097-knowledge-identity.md
brief_ids: [A, B, C, D, E, F, G]
current_brief: G
schema_version_touched: v2.10
retry_count: 0
slug: knowledge-identity
---

## Request (verbatim, as Nia stated it)

> Mon objectif est de faire les travaux préparatoire a l'ajout de la voie
> d'écriture du lore ( en ce moment, je peux posé des questions, mais pas
> ajouter des informations a partir de langage naturelle. Donc on fait A1.

(A1 = Q1b, `knowledge.subject`, as sequenced after 0096: Y7b of 0094, N8b of
0092, Q1b of 0091.)

## Clarifications resolved (intake)

- TICKET-0096 passed its live gate as written (Nia, 2026-09-28); brief A
  closes its front matter in its own commit.
- `knowledge.subject` carried five jobs (LOT R-02): a dedup/identity key, a
  bridge to other tables (`discoverable_detail`, day gates, the link agent's
  `npc:<id>`), a label, the input of aboutness resolution, and a write-time
  argument. The newer code (0082–0091) already reasons by `fact_id`.
- Prod, measured 2026-09-28 (LOT R-03): 641 rows, 11 worlds. No subject
  spreads over two facts in a world except `creator_meta` (31 facts, each a
  distinct note). 3 duplicated `(entity_id, fact_id)` pairs. 269 rows carry
  `subject = npc:<uuid>` (link agent) with no participant, so « qui sait
  quoi sur X » misses 42 % of knowledge. Outside `creator_meta`, every
  fact's content equals its subject. 5 details, none discovered. 5 open and
  1 approved-unapplied subject-keyed proposals.
- The subject was never a good finder: a fact's content already is the
  subject's text; aboutness is `fact_participant`; concept search is facets
  and later search (explained to Nia, who agreed to drop it).

## Decisions locked (do not re-litigate without Nia)

- **A1** — 0097 is Q1b, as groundwork for the lore writing path.
- **B3** — the fact is the identity of what is known; `knowledge.subject`
  is dropped (v2.10) once no code reads it. Nia accepted the migration.
- **C1** — a legacy fact keeps its slug as content; no rewrite. New facts
  carry a sentence.
- **D1** — a model designates a fact only by a code from a coded list the
  code built and resolves (whitelist, as the Lore planner's selectors).
- **D1′a** — the day planner receives the coded list of learnable facts;
  knowledge gates now hold more often (0078's B3 intent). Nia accepted the
  gameplay change.
- **E1** — no merge: v2.09 refuses to run while a subject spreads over two
  facts in a world (`creator_meta` excepted).
- **F1** — UNIQUE `(entity_id, fact_id)`; v2.09 absorbs each duplicate into
  its highest-level twin, the absorbed state in the survivor's history.
- **G1** — the link agent's aboutness is a participant: v2.09 attaches the
  `npc:<id>` entity (and tokenizes a uuid id); the agent reads what a holder
  knows on facts the other side participates in; one fact per new row.
- **H1** — `discoverable_detail.fact_id` (nullable), set by the first
  approved discovery; signposts compare facts.
- **I1** — `subject_resolve.py` goes (N10a fires); the « Sujets » worklist
  lists unbound facts through the names panel's resolver.
- **J1** — a worklist card shows the fact's text, its first knower's
  version, and how many know it; the tab keeps its name.
- **K1** — the creator editors lose the Subject field; attaching someone to
  an existing fact belongs to the writing path.
- **L1** — overhearing classifies against a coded list of the speakers'
  non-secret facts; the bystander learns the speaker's fact itself.
- **M1** — a fact born from a proposal carries the knowledge's sentence; a
  model never emits a subject; dedup keys on the fact, or on a text key
  computed at compare time and never stored.
- **N1** — a model-emitted `knowledge_change` is dropped; upgrades come only
  from code-built proposals carrying a `fact_id`.
- **Z2** — the tick names what an NPC passes on by its briefing code
  (`source_fact`); `secret_derived` is exact on that code. (Nia: « je ne veux
  pas prendre le risque ».)
- One ticket, seven briefs.
- Rejected, with reactivation conditions:
  - B1 (keep the subject as identity): the writing path is abandoned, or only
    ever writes onto existing facts.
  - B2 (keep the column as a dead label): no reader left after B3's cutover
    and nothing needs it — superseded by B3.
  - C2 (a worklist to rewrite legacy slugs): Nia finds the slugs unreadable
    in the creator surface. C3 (a `fact.label` column): the writing path
    needs a short title distinct from the sentence.
  - D2 (model emits the fact text, exact match): D1 visibly degrades plans.
  - D1′b (no list for the planner): Nia finds gates make days too
    constraining.
  - E2 (automatic merge): v2.09 refuses on her DB because a split appeared.
  - F2 (refuse until duplicates are fixed by hand): Nia wants to choose
    which version survives. F3 (no index): the index breaks a legitimate
    write path.
  - G2 (one shared "knowledge of X" fact per NPC): Nia wants all « connaît X »
    grouped under one entry.
  - H2 (compare `fact.content` to `detail.subject`): H1 costs more than one
    brief because of the cascade.
  - I2 (keep `subject_resolve`'s frozen scope): I1 lists candidates that
    bother Nia.
  - J2 (fact text only): the excerpts clutter the list. J3 (rename the
    tab): « Sujets » reads as misleading once the column is gone.
  - K2 (a fact picker in the editors now): the writing path slips past the
    next ticket.
  - L2 (textual list, exact match): the model misses codes in practice.
  - M2 (the model still names a short label): the creator surface becomes
    unreadable without short names.
  - N2 (coded knowledge in the analysis contexts): Nia notices missing
    level upgrades in play.
  - Z1 (substring test only): superseded by Z2.

## Carried forward / open

- The lore writing path (next): affirmation → structured proposal → creator
  write, now onto facts. It owns attaching an entity to an existing fact
  (K2's ground) and any short fact title (C3).
- `scripts/seed_test.py` and `scripts/test_context.py` already fail on
  `main` (no `fact_id` since 0082); left as they are.
- `apply_ticket_0087_subject_participants.py` imports the deleted
  `subject_resolve`; a one-shot that ran in 0087, kept as history.
- Sequence after 0097: N6a day-chain widening (Y6b) → the lore injection
  path, with the writing path to be placed by Nia.
- Every reactivation condition in the 0096 handover §3 stands.

## Acceptance criteria

<!-- One arrow per line: run.py follows the first arrow on a line only. -->

### Machine-checkable  ->  G1 deterministic gate
- [ ] Knowledge is unique per (entity, fact); v2.09 and v2.10 migrate; models name facts by code; the subject census holds  -> verify/checks/knowledge_identity.py
- [ ] Every world-scoped table is deleted, guarded or purged  -> verify/checks/world_cascade.py
- [ ] The worklist stays pure and reaches names through one resolver  -> verify/checks/subject_resolution.py
- [ ] The tick's secret floor forces provenance, never confidentiality  -> verify/checks/world_tick.py
- [ ] Day gates anchor on facts and the list is appended text  -> verify/checks/day_plan.py
- [ ] The link agent stamps who a row is about in one place  -> verify/checks/link_agent_strata.py
- [ ] Name resolution regimes hold  -> verify/checks/name_resolution.py
- [ ] The analyzer core stays conversation-agnostic  -> verify/checks/analyzer_seam.py
- [ ] Raw stored text is read only in the allow-list  -> verify/checks/identity_tokens.py
- [ ] Facet writers and creator-only exclusion hold  -> verify/checks/fact_facets.py
- [ ] Day prompts ship through their single source  -> verify/checks/day_prompt_delivery.py
- [ ] Schema version constant and doc agree  -> verify/checks/schema_version_agreement.py
- [ ] Every canon write site is declared  -> verify/checks/single_canon_write.py
- [ ] The frontend build is fresh  -> verify/checks/frontend_build_fresh.py
- [ ] CLAUDE.md contract holds  -> verify/checks/claude_md_contract.py
- [ ] Module line and function budgets hold  -> verify/checks/module_budget.py
- [ ] Function length ceiling holds  -> verify/checks/function_length.py
- [ ] Decisions index matches the archive  -> verify/checks/decisions_index.py
- [ ] Ticket front matter conforms  -> verify/checks/pipeline_state.py
- [ ] Full corpus is green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After `python scripts/backup.py`, `migrate_v2_09_knowledge_identity.py`
      prints the absorbed duplicates (3 expected) and the `npc:<id>` facts
      tokenized (about 269 rows' facts), then `migrate_v2_10_drop_knowledge_subject.py`
      and `apply_ticket_0097_fact_code_prompts.py` run, and the cockpit starts.
- [ ] Lore: « qui sait quoi sur X » for an NPC the link agent wrote about
      now names those knowers.
- [ ] Création → Sujets: each card shows a fact, a knower's excerpt and a
      count; binding one removes it from the list.
- [ ] On a sheet, adding a knowledge row asks for no Subject; the row shows
      its fact's text.
- [ ] Play a day whose declaration needs to learn something another
      character knows: the plan shows a knowledge gate in words, never an id.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
