---
id: TICKET-0125
slug: player-entry
title: The player's entry -- profiles, the player shell, open worlds, the public perspective
type: feature
status: done
created: 2026-10-22
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: medium
lot_id: LOT-0125-player-entry.md
brief_ids: [A, B, C, D, E, F, G]
current_brief: G
schema_version_touched: v2.31
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Ticket 0124 mergé. Nous ouvrons le ticket 0125. Voilà l'expérience joueur
> que je veux coté joueur : Je suis un joueur. Je choisit dans quel monde je
> veux jouer. Chaque monde a son nom et une petit description. je click sur
> le monde que je veux joueur parce que ca description du monde est
> interessante. Lorsque je rencontre, je dois créer mon personnages.
> c'est-à-dire: Je dit qui je suis dans ce monde, on me montre les
> compétences de base que je peux avoir dans ce monde ( celles qui ne
> necessite pas de les apprendre de quelqu'un), je peux choisir jusqu'a 1
> compétence qui nécessite un maitre, je dois justifié comment je l'ai
> appris. (ici, on va créer une NPC de l'autre coté tu suis ?). Le joueur
> peut ajouter jusqu'a 2 autres NPC ( un maximum de 3). Cela permettra de
> l'ancré dans le monde. Une fois créer, le joueur peut posé différentes
> actions. 1- il peut déclarer ce qu'il fait dans une journée. 2- il peut
> posé des questions sur ses connaissances dans le monde (exactement comme
> pour l'outil lore, mais on filtre avec ce que le joueur connais dans le
> lore).

The request is cut in four tickets (S1, J). This ticket is the first:
the player's entry. Character creation is TICKET-0126, the player's own
knowledge TICKET-0127, the player's day TICKET-0128.

## Clarifications resolved (intake)

- The player is Nia, on her own machine, without a password, with several
  player profiles (A1').
- Choosing a world never activates it: player routes are keyed by world
  (here) and by player character (from TICKET-0126), never by `is_active` (B2).
- During character creation the player may question the lore, on public
  information only ("everybody knows") (E1'). This ticket builds that
  public perspective and makes it usable from the world page.
- `routes/day.py::_resolve_player_character` already refuses a world without
  exactly one PC; only `_player_character_id` and the analyzer's
  `_resolve_player_id` pick the first PC silently (lot R-04, R-05).

## Decisions locked (do not re-litigate without Nia)

- A1' -- Nia alone, local, no password; several player profiles (`user`,
  `role='player'`).
- K1 -- a profile is chosen or created at the entry of the player shell.
- B2 -- player routes never read `world.is_active`.
- C1 -- a world flag "open to players"; the player sees name, description
  and laws.
- P1 -- the player shell is a second frontend entry served at `/jouer`, its
  own bundle; it calls only `/api/joueur/*`.
- N1 -- one perspective pipeline; this ticket builds the `public`
  perspective only. A character perspective is added by TICKET-0127.
- H1-a/b/c/d -- the perspective pipeline is the same code for the player
  and for Nia ("as X"); a creator-only audit lists the withheld lines with
  their reason; every perspective question is journaled with its kept and
  withheld lines; a G1 check with a named mutation proves no secret leaks.
- U1 -- an entity is publicly known iff active and `is_public`; the player
  sees its name and type and only the facts whose public level is above
  `unaware`. A non-public entity answers as an unknown one.
- V1 -- two public entities sharing a name: the player picks among the
  publicly known candidates, name and type only.
- W1 -- a non-secret, current membership is public when both the member and
  the faction are public.
- M2 -- with more than one PC in a world and none named, creator surfaces
  refuse instead of picking one. The "active PC" selector is TICKET-0128.
- R1 -- the creation budget settings (point-buy, limits, visibility cascade)
  move to TICKET-0126 with their readers.
- I -- Play (the scene) stays out of the player shell.

## Carried forward / open

- TICKET-0126 (character creation): designer, pre-review, proposal, Nia's
  review, NPC batches anchored on the PC (F'a-1), the creation budget and
  its settings (Q, Q-limits, L2, R1), re-attaching an existing PC to a
  profile (K1-b), `world_premise` keyed by world instead of `is_active`.
- TICKET-0127 (the player's knowledge): the character perspective ("as X"
  for any character, H1-a), false beliefs rendered as beliefs without the
  "false" mark, learned versions; its own prompt usages if the creator
  wording must differ.
- TICKET-0128 (the player's day): G1, the "active PC" selector (M1).

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Every check passes  -> verify/checks/corpus_gate.py
- [ ] A world with two PCs refuses instead of choosing  -> verify/checks/pc_resolution.py
- [ ] v2.31: `world.open_to_players`, the journal admits `perspective`  -> verify/checks/player_entry_schema.py
- [ ] A world is closed by default and opens from the « Monde » page  -> verify/checks/player_worlds.py
- [ ] The public perspective returns only public lines; the audit names every withheld one  -> verify/checks/perspective_isolation.py
- [ ] Player routes answer only public data, refuse closed worlds, journal every question  -> verify/checks/player_routes.py
- [ ] The Lore "Perspective" tab and the player shell are wired and confined  -> verify/checks/player_shell.py

### Live  ->  human gate (Nia)
- [ ] `/jouer`: create two profiles, pick one; only worlds marked "open to
      players" are listed, each with its description and laws.
- [ ] On an open world, a question about a public entity answers with its
      public facts only; a question about a non-public or unknown name
      answers "nothing known", with no near names.
- [ ] Lore > Perspective, "Public": the same question shows the player's
      answer and, below, the withheld lines with their reason.
- [ ] Création > Monde: ticking "Ouvert aux joueurs" adds the world to
      `/jouer`; unticking removes it.
- [ ] The creator cockpit still plays a world with its one PC as before
      (M2 changes nothing until a second PC exists, which only TICKET-0126
      can create).

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
