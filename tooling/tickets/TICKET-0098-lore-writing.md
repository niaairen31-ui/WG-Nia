---
id: TICKET-0098
title: Lore writing path — write lore in prose, confirm it, get facts
type: feature
status: exec
created: 2026-09-29
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
lot_id: LOT-0098-lore-writing.md
brief_ids: [A, B, C, D, E, F]
current_brief: F
schema_version_touched: v2.11
retry_count: 0
slug: lore-writing
---

## Request (verbatim, as Nia stated it)

> mon problème a l'heure actuelle c'est que c'est long de peuplé mon monde et
> d'y ajouter des choses avec lequel le joueur peut jouer (les faits). Donc je
> veux pouvoir écrire dans l'outil Lore ex : Dans ce monde, l'homme est capable
> d'utilisé diverses technologies. La majeure partie de l'humanité possède une
> puce, implanté dans le cerveau et lié directement au système nerveux de
> l'homme. Je veux que ce lore soit découper en fait et qu'il soit maintenant
> utilisable. [...] je suis ouverte a avoir une discussion de type clavardage
> et qu'on me pose une question de clarification [...] Je répond et on me
> propose des faits [...] Un autre exemple : La reine est la propriétaire du
> manoir et règne en maitre sur ses lieux. [...] Je m'attendrais a ce que la
> reine et tous les gens ayant passé plus d'une journée dans son manoir
> obtiennent cette connaissance.

## Clarifications resolved (intake)

- « Injection de lore » is two tickets (A3): this one is the writing path
  (A1); injecting lore into play (A2) follows, with N6a (Y6b) still behind it.
- A story produces several related facts, and stories relate to each other
  through the entities they share (the tunnel, the alcohol, the guards).
- The queen's rule is both her preference and her power in her own manor.
- Occupations are factions: « les dockers » and « le Syndicat des quais » are
  two factions, told apart by `faction_type`.
- Test world: Nia's new world, created after this ticket.

## Decisions locked (do not re-litigate without Nia)

- A3 — two tickets: A1 (writing path) now, A2 (lore in play) next.
- B2 — stories connect through shared entities, and each committed text is
  kept as a source record linked to what it produced.
- C1 — a proposal may create entities (minimal fiche: name + type); every
  unknown name is created, linked to an existing entity, or kept as text.
- D1 + P1 — the queen: her preference (participant: her), a custom of the
  manor (participants: manor + queen), the `controls` relation, and a
  `statut` fact for the ownership (a `controls` relation births no fact).
- E1 — who knows: the four existing default scopes (world, faction,
  location, rencontre) plus a list of entities the creator checks (stored
  rows: level, secret, false belief).
- F1 — an occupation is a faction.
- G3 — only the static entity types (character, location, faction, item);
  runtime types wait for 0096-E2 (deleting a world that holds them).
- H1 — the writing panel lives in the Lore shell (second bounded reopening).
- I1 — one origin guard for every write method, in its own brief, first.
- J3 — at most one round of clarification questions, then an editable
  proposal; the creator can add text and redraft.
- K1 — Ollama down: an explicit message, the text kept, nothing written, no
  fallback extractor.
- L1 — the model sees the facts of the entities the text names plus the
  world-level facts, coded; never the whole world.
- M1 — the source record keeps and links; bulk undo is a later ticket.
- N1 — the Lore prompt loader moves to a shared module; no second loader.
- O1 — two prompts: questions, then proposal.
- R1 — a proposal writes facts (any non-typed facet), participants,
  defaults, knowers, bloc rewrites, entities, memberships (S1) and
  `controls`; no social relations, events or world laws.
- S1 — faction memberships are part of R1.
- Same code, never a copy: every write goes through the existing
  chokepoints; where an isolation rule forbids an import, the shared piece
  moves to a neutral module.

## Carried forward / open

- **M2 — bulk undo of a story.** Options put to Nia: in this ticket (heavier:
  entities completed since, facts learned in play) or later. Chosen later.
  Deserves its own ticket; reactivates at the first injection to take back.
- **0096-E2 — deleting a world with runtime types.** Blocks G2 (the tool
  proposing new entity types for an encyclopedia by category). Own ticket.
- **R2 — social relations, events and world laws from prose.** Reactivates
  when a story loses its sense without its relation or law.
- **E2 — new default criteria** (occupation other than a faction, duration of
  stay). Reactivates when a group no criterion covers recurs in two stories,
  or a new NPC ignores what it should know.
- **A2 — lore in play** (next ticket).
- **I2 — a session token on writes.** Reactivates if the cockpit listens
  beyond loopback or another local tool calls the API.

## Acceptance criteria

<!-- One arrow per line: run.py follows the first arrow on a line only. -->

### Machine-checkable  ->  G1 deterministic gate
- [ ] Writes from a non-local Host or Origin are refused; reads and local writes pass  -> verify/checks/origin_guard.py
- [ ] The lore writing path: schema, apply, draft, routes, panel  -> verify/checks/lore_write.py
- [ ] The consultation pipeline stays pure; panels stay outside it  -> verify/checks/lore_isolation.py
- [ ] Name regimes hold; the creator regime stays in its allow-list  -> verify/checks/name_index.py
- [ ] Facet writers and creator-only exclusion hold  -> verify/checks/fact_facets.py
- [ ] Every prompt usage is registered and resolved  -> verify/checks/prompt_registry.py
- [ ] Every world-scoped table is deleted, guarded or purged  -> verify/checks/world_cascade.py
- [ ] Schema version constant and doc agree  -> verify/checks/schema_version_agreement.py
- [ ] Every canon write site is declared  -> verify/checks/single_canon_write.py
- [ ] Raw stored text is read only in the allow-list  -> verify/checks/identity_tokens.py
- [ ] UI-visible data never lives in JSON  -> verify/checks/json_ui_boundary.py
- [ ] Name resolution regimes hold  -> verify/checks/name_resolution.py
- [ ] The frontend build is fresh  -> verify/checks/frontend_build_fresh.py
- [ ] CLAUDE.md contract holds  -> verify/checks/claude_md_contract.py
- [ ] Module line and function budgets hold  -> verify/checks/module_budget.py
- [ ] Function length ceiling holds  -> verify/checks/function_length.py
- [ ] Decisions index matches the archive  -> verify/checks/decisions_index.py
- [ ] Every ticket's front matter conforms  -> verify/checks/pipeline_state.py
- [ ] Every check in the corpus runs green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After a backup, `migrate_v2_11_lore_entry.py` then
      `apply_ticket_0098_lore_write_prompts.py` run on the prod DB; the
      cockpit boots.
- [ ] Ordinary Création and Lore edits still save (the origin guard lets the
      cockpit's own pages write).
- [ ] In the new world, « la puce » example: one question round at most, a
      world-level fact that every NPC knows (Lore question « qui sait … »).
- [ ] « La reine » example: her preference, a manor custom and the
      ownership, with the defaults Nia chooses; the queen appears as owner.
- [ ] « Le tunnel » example: a guild secret held by checked members, a false
      belief held by checked dockers, a new entity created from the
      proposal; « Histoires écrites » lists what was written.
- [ ] Ollama stopped: the panel shows the explicit message and keeps the text.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
