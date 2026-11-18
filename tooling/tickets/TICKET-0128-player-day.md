---
id: TICKET-0128
slug: player-day
title: The player lives his days; a world may have several player characters (the « PJ actif » selector)
type: feature
status: live-gate
created: 2026-11-17
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: large
lot_id: LOT-0128-player-day.md
brief_ids: [A, B, C, D, E, F, G]
current_brief:
schema_version_touched: v2.34
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> But. Le joueur vit ses journées, et un monde peut enfin avoir plusieurs PJ.
> * La journée du joueur (G1) : le joueur déclare ce que fait son personnage,
>   tu valides dans ta revue, puis il lit le récit.
> * Le sélecteur « PJ actif » (M1), côté créatrice. Aujourd'hui,
>   `_player_character_id` refuse dès qu'un monde a deux PJ (M2), dans les
>   entités, Création, la scène, Play et le spatial. Le sélecteur donne à ces
>   surfaces le PJ dont il s'agit.
> * G2 est levé : 0129 refuse d'approuver un second PJ dans un monde. Ce refus
>   tombe quand 0128 est fusionné.
> * Hors portée : Play, la scène (I), et les rencontres datées, qui attendent
>   le temps (0120).

> A1, B2, C1, C′2, D1, E1, F1, J1, K1, L1, M1, N1, P1, Q1, R1, S1, T1

> Z1, W1, Y1

## Clarifications resolved (intake)

- Measured on `main` at `055b890` (LOT R-01 to R-37): three functions
  resolve « the » player character and each refuses a second one
  differently (R-02, 21 call sites); the day chain reads the active world
  in its extraction, feasibility, world premise and presence rung (R-18);
  the plan flushes a write before its model calls, so it holds SQLite's
  write lock across them (R-21); a character is deleted softly (R-07).
- `flagged` already exists in `PASS_PLAY_STATUSES` and nothing writes it
  (R-06): it becomes the failed day's status.
- No check calls the plan or resolve HTTP routes (R-17): the worker can
  take them over.
- The days resolved before this ticket have no publication: E1 would block
  every PC that has one -- settled by W1.

## Decisions locked (do not re-litigate without Nia)

- A1 -- `world.active_pc_id` (v2.34), cleared when the character is
  deleted; one resolver in a neutral module replaces the three; one PC needs
  no choice; several and none chosen -> « Choisissez le PJ actif. »; the
  selector sits in the cockpit header. Rejected: A2, the choice kept in the
  browser (reactivation: two cockpit tabs on two PCs at once).
- B2 -- the chain (plan, then resolution) starts by itself after the
  declaration; a failure is never silent (L1, M1). Rejected: B1, each step
  launched by hand (reactivation: « Suivi » shows many failures).
- C1 -- the creator publishes a day, only when no proposal of that day
  awaits in the queue. Rejected: C2, without condition; C3, the narrative
  visible at resolution.
- C′2 -- at publication she may rewrite the narrative; the narrator's text
  stays intact. Rejected: C′1, publishing as is.
- D1 -- the player sees the day, his declaration, the published narrative,
  « en attente de la créatrice »; knowledge comes through « Mes savoirs »;
  INV-66 amended: the published narrative is the one player text outside a
  perspective, because she read it. Rejected: D2, showing the gains
  (reactivation: Nia asks after the live gate).
- E1 -- a PC has at most one unpublished day. Rejected: E2, declaring
  freely.
- F1 -- the day counter stays the world's, shared by its PCs. Rejected: F2,
  one per PC (reactivation: TICKET-0120 opens).
- J1 -- one ticket. Rejected: J2, two.
- K1 -- the declaration is written and answers at once; the chain runs in
  the background with its own session; the player's page reloads while the
  day is « en cours ». Rejected: K2, in the declaration request.
- L1 -- relational `day_run_failure` (v2.34): day, stage (`plan`,
  `resolve`), code, reason as text, date; the day turns `flagged`.
  Rejected: L2, an entry of `pass_play.history` (JSON shown, INV-20).
- M1 -- Journée lists « Journées en échec » with the reason and « Relancer »
  (resume at the failed stage); the player sees only « en attente de la
  créatrice »; a metric « échecs de la chaîne, par étape » in « Suivi ».
  Rejected: M2, no metric.
- N1 -- done by TICKET-0131 (`errorMessage`, INV-69).
- P1 -- the chain's world comes from the day (batch -> session -> world),
  passed to the extraction, the feasibility and the world premise
  (`premised_prompt` gets `world_id`); a check forbids any active-world
  read in the day modules. Rejected: P2, advancing only when the player's
  world is active.
- Q1 -- the quest pin is chosen at the declaration (`pass_play.quest_id`,
  v2.34); no pin on the player's side. Rejected: Q2, manual cockpit days.
- R1 -- at cockpit startup, every day left `submitted` / `resolving` gets an
  « interrompue (serveur arrêté) » failure; at the first start after 0128,
  days left half-way by hand fall there too, on purpose. Rejected: R2,
  relaunching at startup.
- S1 -- one worker thread handles the days one at a time, in arrival order
  (local Ollama). Rejected: S2, one thread per day.
- T1 -- `pass_play.published_text`, `published_at` (v2.34); published =
  `published_at` set; the narrator stays in `batch.final_result`; a
  published day can never be replayed. Rejected: T2, a `day_publication`
  table.
- Z1 -- in « Journées en échec », the creator may abandon a day: status
  `abandoned`, it no longer counts for E1, the player sees it « abandonnée »
  without text. Rejected: Z2, « Relancer » only (reactivation: a day stays
  in failure after many relaunches).
- W1 -- migration v2.34 publishes every day already resolved:
  `published_at` = its resolution date, `published_text` = the narrator's
  text. Rejected: W2, the old days in « À publier ».
- Y1 -- the plan keeps its write transaction across its model calls (R-21);
  the cockpit header shows « Journée en calcul… » while the worker runs;
  the error of a blocked write stays readable (0131). Rejected for now:
  Y2, moving the model calls out of the transaction (deferred, below).
- Drafting decisions already flagged to Nia (reversible): (1) Nia may
  still declare a day for the active PC from the cockpit (it runs by
  itself, B2); (2) quests, debts and services follow the active PC in the
  cockpit, out of scope on the player's side; (3) Journée shows two lists
  for the active world: « En échec » (M1) and « À publier » (C1).

## Carried forward / open

- Y2 -- the plan's model calls outside its write transaction. Reactivation:
  a cockpit or Play write fails « database is locked » while a day plans.
  Its own ticket (the chain's call order is pinned by about ten checks).
- Dated encounters and the calendar wait for TICKET-0120; F2 reopens there.
- Play and the scene for the player (I); quests, debts and services on the
  player's side; showing the gains (D2).
- The legacy document's `PLAYER_ID` follows the active PC only at its next
  load (Play out of scope; no new bridge call).
- Lesson of AMENDMENT-0131-01 (paste `grep -nw <name>` for every name a lot
  imports into existing files) is applied in this lot's RECON (R-31) and
  Mini-RECONs; its line in `brief-generation-protocol.md` still awaits Nia.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Schema v2.34: `world.active_pc_id` (FK `character`, ON DELETE SET
      NULL), `pass_play.quest_id`, `published_text`, `published_at`, the
      `day_run_failure` table with its CHECKs and indexes, `abandoned`; the
      migration refuses below v2.33, publishes the resolved days once (W1),
      changes nothing twice  -> verify/checks/day_schema.py
- [ ] One resolver gives every creator surface its PC; several and none
      chosen is a 409 « Choisissez le PJ actif. »; the routes set and clear
      the choice; deleting the character clears it (INV-70)
      -> verify/checks/pc_resolution.py
- [ ] The cockpit header carries the « PJ actif » selector
      -> verify/checks/active_pc_selector.py
- [ ] The day chain takes its world and its character from the day; no day
      module reads the active world; the pin is chosen at the declaration
      (INV-71)  -> verify/checks/day_chain_world.py
- [ ] A declared day runs in the background; every failure is written with
      its stage, code and reason, listed, relaunched or abandoned; a stopped
      server leaves « interrompue » failures; « Suivi » counts them
      -> verify/checks/day_runs.py
- [ ] A resolved day is published only once its proposals are reviewed,
      may be rewritten, is never replayed; one unpublished day per PC
      -> verify/checks/day_publication.py
- [ ] The player declares his day and reads only the published narrative;
      a second player character is approved (G2 lifted; INV-66 amended)
      -> verify/checks/player_journee.py
- [ ] The existing day, quest, review, player and corpus checks stay green
      -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
Before the gate, on Nia's database after a backup:
`python scripts/migrate_v2_34_player_day.py` (with
`WORLD_ENGINE_ENV=prod`); it prints how many old days W1 published.
- [ ] 1. Aestia (one PC): Journée, Play and Création behave as before; the
      header's « PJ actif » shows Millys.
- [ ] 2. In `/jouer`, as a second profile, create a character in an open
      world and submit it; in Création, approve it (G2 lifted). The header
      now asks « — Choisissez le PJ actif — »; Journée › Quêtes says «
      Choisissez le PJ actif. »; pick one, then the other: quests and debts
      follow.
- [ ] 3. In `/jouer`, as that profile, « Ma journée »: declare. The page
      answers at once and shows « en cours… »; the cockpit header shows «
      Journée en calcul… »; the day then reads « en attente de la créatrice
      ».
- [ ] 4. In Journée, the day is in « À publier » with its pending count;
      review its proposals in the queue, rewrite a sentence, « Publier ».
      In `/jouer`, the day shows the rewritten text; declaring again is now
      possible (before publishing it was refused).
- [ ] 5. Stop Ollama, declare a day: it lands in « Journées en échec » with
      a readable reason; the player sees « en attente de la créatrice ».
      Start Ollama, « Relancer »: the day resolves. Another failed day: «
      Abandonner »: the player sees « abandonnée ».
- [ ] 6. Stop the cockpit while a day plans; start it again: the day is in
      « Journées en échec », « Interrompue (serveur arrêté) ».
- [ ] 7. « Suivi » shows « Chaîne de la journée » with the failures by
      stage and reason.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
