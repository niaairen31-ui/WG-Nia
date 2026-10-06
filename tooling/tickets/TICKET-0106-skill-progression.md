---
id: TICKET-0106
title: A skill progresses from Inexpérimenté to Maître, a point per roll
type: feature
status: exec
created: 2026-10-05
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: medium
lot_id: LOT-0106-skill-progression.md
brief_ids: [A, B, C, D]
current_brief:
schema_version_touched: v2.15
retry_count: 0
slug: skill-progression
---

## Request (verbatim, as Nia stated it)

> Pour améliorer l'expérience joueur, je pense qu'il faut créer des
> ''quêtes/mission'' pour donner des choses a faire dans mon jeu, plus
> spécifiquement dans mes journées. […]
>
> 3- Je pense qu'il faut revoir les compétenses. En ce momement c'est -0 a 1.
> et le système que j'imagine est un système axé sur la progression. Qui part
> de inexpérimenté a maitre (propose la gradation). Un maintre dans un
> compétence peut débloqué cette compétence chez un joueur ou au autre NPC.
> J'aimerais qu'il soit possible d'améliorer des compétenses en atteingant
> certains seuil, déterminer dans l'outil de création compétence/ nom de la
> compétense.

Planning answers, in order:

> A1, B1 on reste ouvert a revoir comment fonctionne l'agenda par contre. tu
> peux mener le nombre de quête que tu veux en même temps. C1, D un fait ou
> une compétence peut être un cout dans le sens ou il faut l'obtenir et la
> partagé au demandeur pour oubtenir la recompense. E1, mais ma vision c'est
> de créer des questions dans mon outil lore éventuellement. F1, G1, H1,
> selon moi les points peuvent venir des jets réussi et échouer, tu apprend
> des echecs aussi. Est-ce que tu pense que la monter de niveau est une quête
> en soit? I1, J Est-ce que l'on peut créer des faits de type dette qui sont
> supprimer lorsqu'elles sont payé ?

> K1, J2 cela érode la relation, mais son système de calandrier/temps n'est
> pas encore rendu a géré cela. L1, M2, N2 aucune limite, on regarde plus
> tard, O1, P2

> Q1, S1, T1, U2, V ok pour le default, Est-ce que je peux aussi les modifié
> manuellement par compétence ou par système? Si je veux un système plus
> compliqué ou une compétence plus compliqué que les autres. W voir ma
> reponse précédente. Y1. ticket 0105 est terminer, et mergé sur main.

> Y1b, tant que cela fonctionne pour les journées. ok pour le decoupage.

This ticket is the first of three (A1): skill progression. NPC skill sheets
and teaching (I1) and quests (B1-F1, J2) are their own tickets.

## Clarifications resolved (intake)

- **A skill is not 0 to 1 today but -1 to 2**: `skill.tier`, the 2d6
  modifier itself (LOT R-01, R-03). NPCs carry one `physical_tier`, no skill
  sheet (R-01).
- **Writing a point during play adds a canon write**: the ARCHITECTURE
  « Auto-applied mutations » category is the sanctioned door, and extending
  it is Nia's decision (R-08) — taken as Q1.
- **A day's dice are replayable and write no canon** (R-06): a day's point
  is given when Nia approves the step, never at the roll.
- **Play is sealed (TICKET-0061)**: its client cannot show the point without
  breaking the seal (R-10) — Y1b: the point rides on the verdict event, shown
  on the PC's fiche and in the day's account until Play's migration.
- **« Can I set them per skill or per system? »** — yes: thresholds at three
  levels, the most specific wins (O1 extended, drafting decision 1 of the
  lot).

## Decisions locked (do not re-litigate without Nia)

- **A1** — three tickets in order: skill progression (this one), NPC skill
  sheets and teaching, quests.
- **G1** — six ranks fixed in the engine, read as numbers: Inexpérimenté,
  Initié, Apprenti, Confirmé, Expert, Maître. Rejected: G2 (a ladder length
  per world), G3 (rank = modifier).
- **L1** — dice modifier by rank: -1, 0, +1, +2, +2, +3; the four former
  tiers keep their roll. Rejected: L2 (-1..+4).
- **M2** — one point per roll, success, partial and failure alike.
- **N2** — no cap; revisit after play.
- **O1** — default thresholds per world; a system and a skill may each
  override any threshold (Nia's follow-up), the most specific winning.
- **P2** — one set of rank names per world. Rejected: P1 (per system).
- **V** — default points to leave each rank: 5, 10, 20, 40, 80.
- **K1** — reaching a threshold ranks up automatically; trials with extra
  requirements are quests (quests ticket).
- **Q1** — a Play roll's point is an auto-applied `skill_progress`
  mutation; a day's point is given at the step's approval. Rejected: Q2
  (review each point), Q3 (a third write path).
- **S1** — the point goes to the skill row rolled (the custom skill when
  named).
- **T1** — `skill.rank` and `skill.xp` replace `skill.tier`. Rejected: T2.
- **U2** — points count within a rank and restart at 0 on a rank change,
  manual or earned.
- **W1** — ranks and thresholds are set in Création › Compétences.
- **Y1b** — Play stays sealed; the point is shown on the fiche and in the
  day's account. Rejected: Y1a (a line-neutral edit of `legacy.html`).

## Carried forward / open

- **NPC skill sheets and teaching (I1)**: a skill flagged « requires a
  master », unlocked by a Maître NPC. Own ticket; NPCs keep
  `physical_tier` (-1..2) until then, so a player reaches +3 and an NPC +2.
- **Quests (B1, C1, D, E1, F1)**: an offer table becoming a player `agenda`;
  several quests at once means revisiting the one-active-agenda rule;
  creating quests from the Lore tool later. Own ticket.
- **Rank trials (K1)**: a rank-up with requirements (an item, a fact, a
  master) offered as a quest. Quests ticket.
- **Debts (J2)**: a `debt` table, settled never deleted, with an optional
  fact so others may learn of it. Erosion of the relation by an unpaid debt
  waits for time to pass in the engine.
- **`day_plan._eval_resource` ignores `target_key`** (sums the whole
  ledger): harmless with one currency, a bug once quests ask for typed
  resources. Quests ticket.
- **Showing the point in Play**: the verdict event carries `progress`;
  TICKET-0069 (Play's migration) shows it.
- **Anti-farming (N2)**: no cap per conversation or day; revisit after play.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Rank, points, thresholds, migration, points per roll, ranks authoring and displays -> verify/checks/skill_progression.py
- [ ] Canon writes stay on sanctioned sites, write_skill_progress and upsert_skill_rank included -> verify/checks/single_canon_write.py
- [ ] The Play stream's request session stays read-only -> verify/checks/stream_session_readonly.py
- [ ] skill_system declares its five thresholds and nothing else new -> verify/checks/skill_system_shape.py
- [ ] Every world-scoped table is still cascaded, skill_rank included -> verify/checks/world_cascade.py
- [ ] Modules within budget, play_physical.py included; the legacy document unchanged in length -> verify/checks/module_budget.py
- [ ] Schema doc and code agree on v2.15 -> verify/checks/schema_version_agreement.py
- [ ] CLAUDE.md budgets and pointers hold -> verify/checks/claude_md_contract.py
- [ ] The built frontend matches its sources -> verify/checks/frontend_build_fresh.py
- [ ] The whole corpus is green -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After `python scripts/backup.py`, `python scripts/migrate_v2_15_skill_ranks.py` on prod reports `Migration v2.15 applied.`; the cockpit boots.
- [ ] Création › PJ › Fiche de compétences: Millys's skills show rank names (a former « 0 · Average » is now « Initié ») and « 0 / 10 pts ».
- [ ] Play: a physical action (« je grimpe au mur ») -> the applied mutations list a `skill_progress` +1 (proposed by `engine_roll`); the fiche shows one more point.
- [ ] Journée: a resolved day lists « compétence +1 point (à l'approbation) » per rolled step; after approving the step, the fiche shows the point.
- [ ] Création › Compétences › « Rangs du monde »: rename a rank and set a default to 1; a system's fiche shows the world's values as greyed placeholders; set a system threshold and a skill threshold — the skill's fiche shows the system's value as placeholder.
- [ ] With a threshold of 1, one roll moves the skill up one rank on the fiche.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
