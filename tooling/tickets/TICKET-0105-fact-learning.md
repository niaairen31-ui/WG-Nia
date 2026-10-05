---
id: TICKET-0105
title: A fact once learned is kept, in the version learned, until the next contact
type: feature
status: exec
created: 2026-10-05
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: large
lot_id: LOT-0105-fact-learning.md
brief_ids: [A, B, C, D, E, F, G]
current_brief:
schema_version_touched: v2.14
retry_count: 0
slug: fact-learning
---

## Request (verbatim, as Nia stated it)

> Dans l'outils de lore, lorsque je veux mettre qu'un fait est connus par
> défaut par : Ceux qui sont dans le lieux : ... Je ne veux pas sélectionnée
> de lieu.  Je voudrais que si c'est un lieu de zone entrer dans n'importe
> quel lieu de cette zone déclenche l'apprentissage de ce fait, si c'Est un
> lieu visitable, c'est a la visite du lieu.

> Je veux qu'un fait incéré dans le conon par l'outil lore restent. le chat
> n'arrête pas de dormir toute le journée sur la tablette du local
> d'alchimie parce que tu n'est pas là. Je pense que une fois que tu as un
> fait, tu le garde ( comme des collectibles ) maintenant, lorsqu'un fait est
> modifié ou supprimé (par l'outil créateur ou lore par exemple), prenons
> l'exemple des vêtements faits de type tenus. Je connais la tenus du NPC A
> et j'assume qu'il a cette tenus jusqu'à ce que je le voie avec une nouvelle
> tenus. Pour ta description, Elle reste toujours la même, sauf quand celle
> est modifié. Selon moi, tu met a jour ton fait lorsque tu le rencontre avec
> sa nouvelle description. Dans ma tête, le calcul se fait au moment de la
> rencontre, on n'a pas forcément besoin de loggé, sauf si on peut faire
> quelque chose d'intéressant avec les logs.

Planning answers, in order:

> A1, B […]

> B5, G1, H1, I1, J, L1, K1, M1, Ok pour les deux tickets.

> J2, A1'a

> C1, N1 si la tenus ne rafréchis pas en fonction d'un lieu jamais n'est-ce
> pas?. O1, P1, Q1, T1, U1. ok pour la division.

> N1, V1

The picker half of the first request (A1, A1'a) was TICKET-0104, merged.

## Clarifications resolved (intake)

- **A `location` default means presence today, not learning**: it reaches
  whoever stands in the place or a place inside it, and is lost on leaving
  (LOT R-05). The zone half of the request already holds for presence.
- **Nothing records where a character has been**: `visit` covers players
  entering a scene only; NPC positions from schedules are computed, never
  written (LOT R-03, R-04). Placement is written by six paths, two of which
  pass the column through `**ext_kwargs` (LOT R-01).
- **A rewrite today changes what everyone knows at once, and a deletion
  makes everyone forget** (LOT R-06, R-07); nothing says whether a rewrite
  fixes a typo or records a change in the world.
- **« Calculate at the moment of contact » is met by B5**: only the date of
  the last contact is kept, and the knowledge is computed when read — the
  same outcome, without writing knowledge rows by the thousand.
- **An outfit is visible nowhere in play**: `tenue` presets no default and
  no play reader reads it (LOT R-10, R-11). V1 makes the request's example
  testable.
- **Production measurement (Nia, 2026-10-05)**: `fact_default` 540 rows —
  world 328, rencontre 167, location 43, faction 2; 79 of 1,660 facts carry
  a non-empty `change_history`; 647 knowledge rows, 42 without text of their
  own; `rencontre` 223 rows (relation 166, gathering 31, visit 21, schedule
  3, conversation 2); 32 `visit` rows; 157 characters placed; 13
  `npc_schedule` rows; one `tenue` fact, without a default.

## Decisions locked (do not re-litigate without Nia)

- **B5** — the date of the last contact is kept (`rencontre.last_at`, a new
  `passage` registry per character and location); what is known is computed
  at read time. Rejected: B4, writing knowledge rows at each contact
  (reactivates if a reader needs a stored row where only a default exists).
- **G1** — `change_history` entries carry a `kind`: `correction` (everyone
  sees the new text) or `changement` (a change in the world). Rejected: G2,
  copying the learned version into `knowledge.content` (that column is the
  holder's own version).
- **H1** — the creator picks the kind at every rewrite, preselected by facet
  (`physique`, `tenue` → `changement`). Rejected: H2, no preselection.
- **I1** — deleting a fact is a correction: everyone forgets. Rejected: I2,
  knowers keep a deleted fact (nothing would ever bring them up to date).
- **J2** — a faction default is learned too: a member follows its changes,
  and keeps the last version known after leaving. `world` stays ambient.
- **L1** — a contact is any placement write, any play encounter (visit,
  gathering, conversation), and permanent contact through schedules; a
  relation alone is not a contact.
- **K1** — an outdated version is marked in the Lore dossier only.
- **M1** — the migration fills `passage` (current location, visits,
  schedules); existing histories read as corrections.
- **C1** — among several applicable place defaults, the highest level wins.
  Rejected: C2, the current place first.
- **N1** — a fact's version is refreshed by the last contact with any of its
  anchors (participants, the entities its non-world defaults name). An
  outfit is refreshed by a place only if the creator gave it a place scope.
  Rejected: N2, only the anchor of the tier that gave the level.
- **O1** — being at the same exact place right now is a contact. Rejected:
  O2 (a present NPC described in yesterday's outfit).
- **P1** — one `before_flush` listener captures every placement write.
  Rejected: P2, routing every path through `write_character_location`
  (reactivates if the listener proves incompatible with a write path).
- **Q1** — existing encounters are dated with the migration's time.
  Rejected: Q2, `last_at = first_at` (the physique facts the v2.06 migration
  created would be forgotten).
- **T1** — the outdated mark is written by code into the row's text; the
  Lore prompt does not change. Rejected: T2, a prompt rule.
- **U1** — code-made rewrites: a social relation's type change is a
  `changement`; a geographic link's retype and a name binding are
  corrections.
- **V1** — `tenue` presets `rencontre`; the migration gives existing
  one-participant outfits that default; the scene shows the outfit known.

## Carried forward / open

- **What a character knows only through a default is not in the Lore
  dossier** (it lists stored rows). Showing it deserves its own ticket.
- **A stored knowledge row with its own text is never refreshed**: it is the
  holder's own version. Revisit if Lore-written knowers start carrying text.
- **A gathering is a contact when joined, not for as long as it lasts**;
  co-presence right now (O1) covers the scene itself.
- **An NPC's own identity block does not list its outfit**; only the scene
  descriptions do (V1). Add it if NPCs should speak of what they wear.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Passage, last contact, kinds, dated resolution, versioned readers, editors and dossier -> verify/checks/fact_learning.py
- [ ] Resolution precedence holds, highest place default wins, a rencontre default needs a later contact -> verify/checks/knowledge_resolution.py
- [ ] The encounter registry keeps one writer and its live sites -> verify/checks/encounter_registry.py
- [ ] The facet registry matches its table, tenue presets rencontre -> verify/checks/fact_facets.py
- [ ] Lore rewrites carry their kind; the writing path still writes only on commit -> verify/checks/lore_write.py
- [ ] Every world-scoped table is still cascaded, passage included -> verify/checks/world_cascade.py
- [ ] Raw fact text is read only through the render chokepoint -> verify/checks/identity_tokens.py
- [ ] Schema doc and code agree on v2.14 -> verify/checks/schema_version_agreement.py
- [ ] CLAUDE.md budgets and pointers hold -> verify/checks/claude_md_contract.py
- [ ] The built frontend matches its sources -> verify/checks/frontend_build_fresh.py
- [ ] The whole corpus is green -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After `python scripts/backup.py`, `python scripts/migrate_v2_14_passage.py` on prod reports `Migration v2.14 applied.` with `Tenue defaults added: 1` (or lists the one outfit as left without a default, if it has several participants); the cockpit boots.
- [ ] Lore, Écrire: a fact « known by those in the place » on a zone (« Le chat dort toute la journée sur la tablette du local d'alchimie »). A PJ travels into a place inside the zone, then leaves: the fact is in Mes savoirs, and stays there after leaving.
- [ ] A fact on a place the PJ visited BEFORE writing it is not known until the PJ goes back.
- [ ] An NPC's outfit, met by the PJ: the scene shows it. The outfit is changed in the fiche as « Changement dans le monde »: while the PJ is elsewhere, the Lore dossier marks the PJ's version as old (if the PJ holds a stored row on it); after the PJ meets the NPC again, the new outfit is shown.
- [ ] A typo fixed in a description as « Correction »: everyone sees the fixed text at once.
- [ ] Lore, Écrire: a rewritten bloc fact shows « Correction / Changement dans le monde », preselected by its facet; the commit is accepted.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
