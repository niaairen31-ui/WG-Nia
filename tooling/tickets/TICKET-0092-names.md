---
id: TICKET-0092
title: Names — appellations, partial and near names, every category (B)
type: feature
status: live-gate
created: 2026-09-24
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [db_write]
blast_radius: medium
lot_id: LOT-0092-names.md
brief_ids: [A, B, C, D, E]
current_brief: E
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Lore -> Question : « qu'est-ce que la reine sais ? » renvoie « Aucune
> entité nommée « la reine » dans ce monde, et aucun nom proche. »

> « N7c est-ce que je peux avoir un coefficient de probabilité qui dit quel
> nom a le plus de chance d'être le bon? »

## Clarifications resolved (intake)

- Sequence I2': 0090 (done) -> 0091 lore as facts (done) -> this ticket
  (names, B) -> concordance H2 + review loop K1 -> lore injection.
- Inherited locks: B1 partial-name rung, B2 aliases and titles, B3 near
  candidates, B4 every category nameable; B2' aliases and titles are the
  facet `appellation`, no separate table.
- "La reine" is a title, not a name: the resolver read entity names only.
  The message « aucun nom proche » was a constant: nothing computed near
  names (LOT R-11).
- The "probability" Nia asked for is delivered as a resemblance score on
  near names only (N9b). A contextual likelihood is H2's job (N9c).
- The TICKET-0091 artifacts were deposited on `main` by Nia's PR before the
  lot RECON.

## Decisions locked (do not re-litigate without Nia)

- N1c: one module `name_index.py`, extracted from `prose_tokens._build_index`, serves every name reader.
- N2b: Lore and names panel see every appellation, creator-only included; the tokenizer never a creator-only one; play only those the character resolves above `unaware`.
- N3a: `normalize_surface` unchanged; gender, number and synonyms are separate `appellation` facts.
- N4a: partial rung — the surface's tokens (3+ characters each) are a subset of a name's or appellation's tokens; after `named_token`.
- N5c: near names = token overlap or `difflib` ratio >= 0.8, at most 5, display only.
- N6a: every category on the Lore surface, the names panel and the tokenizer; the day chain keeps three categories until H2; no migration.
- N7c: a Lore miss links to « Noms à lier » pre-filled; the panel records an appellation, and binding a mention can record one too.
- N8b: `knowledge.subject` (Q1b) gets its own ticket after this one.
- N9b: resemblance score shown and sorted on near names only; exact homonyms stay alphabetical with no score; nothing preselected.
- N10a: `subject_resolve` unchanged in this ticket: names only, three categories frozen.
- N11a: a name and an appellation matching at the same rung are equal candidates; two entities -> ambiguous; the tool never picks.
- N12a: the day chain gets only the appellations its character knows; partial rung and near names are creator-surface only until H2.
- N13a: near names also in « Noms à lier », sorted by resemblance.
- N14b: the `appellation` preset becomes `rencontre`; the panel offers the scope, `rencontre` by default; no backfill.
- N15b: an appellation's own text is tokenized against names only, never against the owner or any appellation.
- N16a: in play, known appellations join `named_exact`/`named_token`; `named_alias` stays a no-op.
- N17a: the tokenizer indexes only appellations with a scope (a non-`unaware` default); an unscoped one is treated as secret.

## Carried forward / open

- N6c — events as entities (named deferral, ticket > 0092). Reactivation: a
  Lore selector takes an `event_id`.
- N9c — contextual likelihood of a candidate (named deferral). Reactivation:
  H2 opens; the resemblance score becomes one of its pieces of evidence.
- N10a's reactivation: the Q1b ticket opens; `subject_resolve` then chooses
  its scope.
- N12a's reactivation: H2 opens; partial rung and near names in play.
- N11b (names before appellations) rejected; reactivation: the K1 review
  shows recurring ambiguities where the name was always right.
- N14c (`public_world` preset) rejected; reactivation: K1 shows most
  written appellations are public titles.
- N17c (tokenizer reads names only) rejected; reactivation: K1 shows
  appellation tokens bound wrongly.
- Generator `mentions` vocabulary stays three categories (LOT R-18).
- Appellations written before this ticket keep their defaults; one written
  on a character under the old preset has no scope and is no longer indexed
  by the tokenizer (N17a). Re-recording it through the panel gives it
  `rencontre`.
- Route authentication (carried from 0091).
- `frontend_build_fresh.py` fails on the `main` tarball before any change
  (LOT R-20); E's rebuild clears it.

## Acceptance criteria

<!-- One arrow per line: run.py follows the first arrow on a line only. -->

### Machine-checkable  ->  G1 deterministic gate
- [ ] Name surfaces are world-scoped, regime-filtered, and the creator regime stays confined  -> verify/checks/name_index.py
- [ ] Names, appellations, partial and near names resolve per the lot's case tables  -> verify/checks/name_resolution.py
- [ ] The resolver stays pure, world-scoped and non-casting  -> verify/checks/lore_resolve.py
- [ ] The Lore pipeline stays pure and isolated from the names panel  -> verify/checks/lore_isolation.py
- [ ] The facet registry matches the locked table  -> verify/checks/fact_facets.py
- [ ] Fact and knowledge text is read only through the render chokepoint  -> verify/checks/identity_tokens.py
- [ ] The day concordance keeps its rungs and purity  -> verify/checks/day_concordance.py
- [ ] Day concordance golden cases hold  -> verify/checks/day_concordance_golden.py
- [ ] Subject resolution still goes through the resolver  -> verify/checks/subject_resolution.py
- [ ] No module-level import cycle  -> verify/checks/import_cycle.py
- [ ] Every canon write site is declared  -> verify/checks/single_canon_write.py
- [ ] CLAUDE.md contract holds  -> verify/checks/claude_md_contract.py
- [ ] Decisions index matches the archive  -> verify/checks/decisions_index.py
- [ ] Module line and function budgets hold  -> verify/checks/module_budget.py
- [ ] Function length ceiling holds  -> verify/checks/function_length.py
- [ ] Frontend build is fresh  -> verify/checks/frontend_build_fresh.py
- [ ] Build output committed and fresh  -> verify/checks/static_asset_freshness.py
- [ ] Full corpus is green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After writing the appellation « la reine » on the queen's sheet,
      Lore -> Question « qu'est-ce que la reine sait ? » answers about the
      queen.
- [ ] A question naming a misspelled or partial name shows « Noms proches »
      with a resemblance percentage, highest first.
- [ ] The link under a miss opens « Noms à lier » with the name pre-filled;
      choosing an entity and « Enregistrer » records the appellation, and
      asking again resolves it.
- [ ] A question about an object (an item) resolves it by name.
- [ ] In « Noms à lier », binding a mention with « Enregistrer aussi comme
      appellation » checked adds the appellation to the entity's sheet.
- [ ] The facts editor shows « Appellations » on an object's sheet.
- [ ] A day whose declaration uses an appellation the character knows
      resolves it; the same words from a character who does not know it
      stay unresolved.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
