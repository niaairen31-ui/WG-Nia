---
id: TICKET-0091
title: Lore as facts (G2 + F1)
type: feature
status: live-gate
created: 2026-09-22
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write, destructive_data]
blast_radius: large
lot_id: LOT-0091-lore-as-facts.md
brief_ids: [A, B, C, D, E, F, G, H, I, J, K]
current_brief: K
schema_version_touched: v2.06
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> "Peu de backstories écrites pour l'instant : je préfère changer la
> structure maintenant, avant d'en accumuler."

> "Plusieurs faits par facette : chaque élément (p. ex. chaque aversion) doit
> être apprenable un par un, pas un bloc."

> "Q12 Je veux pourvoir savoir qui connais une coutume précise. est-ce qu'il
> y a une façons de revoir le code pour ne pas faire d'exception. C'est
> important parce que a terme, je vous ppouvoir écrire en langage naturelle
> une histoire et que mon outil remplisse les bons facts par rapport a ce que
> je j'écrit. j'ai besoin de quelque chose qui me permet d'efficacement faire
> cela et d'ajouter des lecteurs au fur et a mesure facilement."

> "Q19 la reponse dépend de quel partie du lore d'une fiche tu parle, en
> fonction de si cela s'apprend en bloc ou peu s'apprendre fait par fait, ma
> reponse est différente. l'un peut rester en boc et être un ''gros'' fait,
> les autre doivent être séparer par affirmation (ex les aversions)"

## Clarifications resolved (intake)

- Sequence I2': TICKET-0090 (done) -> this ticket (G2 then F1, one lot) ->
  names (B) -> H2 + K1 -> lore injection.
- Prod, 2026-09-22 (Nia): 3 schedule co-presence pairs across two worlds,
  never more than 2 NPCs per `(location, phase)`.
- The cockpit has no request authentication (LOT R-27); Lore and Creation
  are equally reachable.
- Artifacts (`artifact.origin`, `known_properties` / `actual_behavior`) are
  out of scope (Nia's call, carried).

## Decisions locked (do not re-litigate without Nia)

- F1 — a name in canon prose is an identity token rendered to the current
  name; one render chokepoint; unresolved names go on a worklist.
- G2 — all descriptive lore becomes facts with a facet; mechanics stay in
  their tables; `discoverable_detail` never becomes a fact.
- M — cartography v2 (facet / participants / knowledge as three axes);
  physique becomes known at the first encounter.
- L2 — relocation without rewriting: one fact per filled cell, text
  unchanged, no tokens, no splitting on migrated text.
- D3b' — no duplicate worklist; the control query re-runs after migration.
- R1, R-a (amended), R-b1, R-c — `rencontre` registry and scope; NPCs learn
  by encounter; a declared day creates no encounter; physique known by
  encounter renders to the MJ only for entities present.
- Q0a — the `rencontre` registry is in this lot, before the migration.
- Q1b — `knowledge.subject` gets its own ticket, numbered after 0091.
- Q2a — `fact.facet` nullable, validated in `create_fact` against the
  `FACETS` registry, no CHECK; NULL means "predates TICKET-0091".
- Q3a — `fact_default` is rebuilt to admit scope `rencontre`.
- Q4b — encounter sources: player traces, gathering co-membership,
  schedule co-presence.
- Q5a — any social relation, either direction, makes both entities
  acquainted.
- Q6a + Q18a — self-knowledge is a resolver rule, after the stored row, and
  applies only to facts with a descriptive facet.
- Q7a — writers write facts; the columns are dropped in the last migration.
- Q8b — token `[[e:<uuid>|name at writing]]`, attribute `content_raw`,
  `prose_render.py`.
- Q9b — v2.05 additive; v2.06 relocation + drop.
- Q10a — "state" encounters (schedule, relation) are materialized, never
  erased.
- Q11a — schedule co-presence means the exact same `location_id` and phase.
- Q12d — a general `fact.aspect`; `location_subculture` migrates to facet
  `coutume` with aspect = key; notoriety follows `is_hidden`.
- Q13a — play readers switch with constant behaviour, except physique.
- Q14a — pure moves before any addition to a budget-bound file.
- Q15a + Q16b — the server poses tokens by matching existing names; the
  generator declares its `mentions`.
- Q17d — the name-resolution panel lives in the Lore shell; the 0085
  read-only lock is reopened in a bounded way (consultation pipeline stays
  pure, enforced by a new rule).
- Q19d — each facet declares its granularity (`bloc` / `affirmation`) in
  the registry.
- Q20b — the generator emits facet keys; region, NPC-batch and PC review
  surfaces keep one text field per facet, the server splits affirmations by
  line.
- Q21b — creator-only facts (a participant's own stored `unaware` + secret
  row) are excluded by `facts_of` at query construction; only the Lore
  dossier opts in (AMENDMENT-0091-01).
- Rule — a deferral or follow-up of this ticket always goes to a ticket
  numbered above 0091.

## Carried forward / open

- Named deferrals, each to a ticket numbered above 0091:
  `knowledge.subject` cutover (Q1b); `relation.notes`, `event.*`,
  `npc_goal.description`, `world_law.text` token-bearing; runtime `ext_*`
  descriptive columns; route authentication (LOT R-27); the "story -> facts"
  extractor; physique for entities **cited** in a scene (needs H2);
  a mention picker in the sheet's text fields (Q15b, reactivation: the F1
  worklist exceeds what Nia wants to sort by hand); dropping
  `relation.visible_to_b` (carried from 0090).
- None blocking.

## Acceptance criteria

<!-- One arrow per line: run.py follows the first arrow on a line only. -->

### Machine-checkable  ->  G1 deterministic gate
- [ ] The facet registry matches the locked table and every fact is born with a facet  -> verify/checks/fact_facets.py
- [ ] The encounter registry has one writer, no update or delete, and every live site records  -> verify/checks/encounter_registry.py
- [ ] No reader or writer touches a dropped prose column or the subculture table  -> verify/checks/lore_as_facts.py
- [ ] Fact and knowledge text is read only through the render chokepoint  -> verify/checks/identity_tokens.py
- [ ] The resolver applies self, encounter, location, faction and world tiers in order  -> verify/checks/knowledge_resolution.py
- [ ] The fact spine still holds  -> verify/checks/fact_spine.py
- [ ] Relations still birth one lien fact each  -> verify/checks/relation_orientation.py
- [ ] The Lore consultation pipeline stays pure and isolated from the names panel  -> verify/checks/lore_isolation.py
- [ ] Every selector section is an emitted literal  -> verify/checks/lore_selectors.py
- [ ] Every canon write site is declared  -> verify/checks/single_canon_write.py
- [ ] No JSON column added without an allow-list entry  -> verify/checks/json_ui_boundary.py
- [ ] Visits stay append-only  -> verify/checks/visit_delta.py
- [ ] Prompt-lean rules hold with the registry aspects  -> verify/checks/prompt_lean.py
- [ ] Module line and function budgets hold  -> verify/checks/module_budget.py
- [ ] Function length ceiling holds  -> verify/checks/function_length.py
- [ ] Schema version agrees across constant, doc and changelog  -> verify/checks/schema_version_agreement.py
- [ ] Frontend build is fresh  -> verify/checks/frontend_build_fresh.py
- [ ] Build output committed and fresh  -> verify/checks/static_asset_freshness.py
- [ ] Full corpus is green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After v2.05 and v2.06 on a copy of prod, Maelis's sheet shows her description, physique, histoire and aversions as facts, text unchanged, each under its facet.
- [ ] Adding a second aversion to an NPC creates a second line; editing one keeps the previous text in its history.
- [ ] A bloc facet (physique) cannot receive a second fact from the sheet.
- [ ] A location's visible customs show as `coutume` facts with their aspect; a hidden one shows with no knower.
- [ ] The Lore dossier of an NPC lists its facts by facet, the creator note marked secret.
- [ ] In play, an NPC's identity block still carries its physique, histoire and aversion; the MJ sees the physique of a co-present NPC the player has met.
- [ ] Two NPCs scheduled at the same place and phase can describe each other's physique in a tick.
- [ ] Renaming an entity changes its name inside a fact written after this ticket, without editing the fact.
- [ ] A generated NPC whose backstory names an unknown person puts that name in the Lore names panel; choosing an entity writes the token; ignoring it closes the line.
- [ ] The migration report lists the duplicate control query result.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
| AMENDMENT-0091-05 | J | seed knowledge upsert moves into `writes/`; seed text untokenized | J |
| AMENDMENT-0091-04 | J | R-24 reader list incomplete; `link_author` knowledge merge moves into `writes/knowledge.py` | J |
| AMENDMENT-0091-03 | I | seed customs honour each entry's `is_hidden` (hidden-custom trap) | I |
| AMENDMENT-0091-02 | H | R-12 reader enumeration incomplete (play_physical, entity_geometry, imports, seed); anchor drift after E | H, I |
| AMENDMENT-0091-01 | G | C-10 did not exclude the creator's note from `facts_of`; secrets leak into tick and link prompts (found by G's review) | D (copy), G, H |
