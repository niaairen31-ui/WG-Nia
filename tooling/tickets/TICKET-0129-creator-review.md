---
id: TICKET-0129
slug: creator-review
title: The creator reviews a submitted character -- her choices beside the player's version, NPC batches anchored on the character per group, a return with a note, one transaction to canon; K1-b
type: feature
status: live-gate
created: 2026-10-25
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: large
lot_id: LOT-0129-creator-review.md
brief_ids: [A, B, C, D, E, F, G]
current_brief: G
schema_version_touched: v2.33
retry_count: 0
---

## Request (verbatim, as Nia stated it)

From the request that opened the player series (TICKET-0125), the part this
ticket serves:

> Lorsque je rencontre, je dois créer mon personnages. [...] je peux choisir
> jusqu'a 1 compétence qui nécessite un maitre, je dois justifié comment je
> l'ai appris. (ici, on va créer une NPC de l'autre coté tu suis ?). Le
> joueur peut ajouter jusqu'a 2 autres NPC ( un maximum de 3). Cela
> permettra de l'ancré dans le monde.

Planning of this ticket (2026-10-25), Nia's answers as written:

> Le ticket 0126 est fusionnée sur main.

> A1, B1, C1, D2, E1 tu es conscient que le maitre est un PNJ aussi ? F1,
> G1, H1, I1

> J1, K1

## Clarifications resolved (intake)

- The master is an NPC like the others: a « master » sketch to create is a
  line of its group's batch, written by the same row commit. It is written
  before the character only because its Maître rank must exist before the
  character's skill row names it as teacher (`taught_by_id`). The order of
  the approval: every NPC of the batches (masters included), the masters'
  rank, the character and his skills, memberships, knowledge, relations
  and encounters, then the draft closes.
- The final rank of a skill is the player's (`player_rank`); the
  designer's is a suggestion the player copies or not (`creation_check.py:222`).
- A relation PNJ -> PJ of a social type already records the encounter
  (`writes/relations.py:223-233`): the people of the story meet the
  character through it; F-b's encounters use the new source `pc_creation`.
- The NPC agent's panel takes the first open batch of the world
  (`npcAgent.svelte.js:107`): review batches are kept out of its list, its
  « one open batch » rule and its commit route.
- Testing the approval needs a world without a player character (G2):
  attaching Millys to a profile (K1-b) does not take her out of Aestia.
- Letters of this ticket's planning repeat some letters locked for 0129 at
  TICKET-0126 (C1, D1, E1, F1, H1); the latter are written `C1 (0126)`
  and so on below.

## Decisions locked (do not re-litigate without Nia)

Locked for this ticket at TICKET-0126 (handover, unchanged):

- E1' -- nothing reaches canon before the creator's approval; she reviews
  the final version with all the lore.
- C1 (0126) -- a refusal gives back the player's own version with the
  creator's note, never her edits; he corrects and resubmits; nothing is
  deleted.
- D1 (0126) -- at review, any starting place, always visitable (not a zone).
- E1 (0126) -- every skill that requires a master has a « master » sketch;
  at review the master is an existing character already at Maître in it,
  or an NPC created at Maître. Rejected E2 (raising an existing NPC to
  Maître inside the approval).
- F'a-1 -- each logical group of sketches becomes one NPC batch of the
  existing generator, anchored on the character, developed with all the
  lore; a sketch may be attached to an existing character.
- F-b -- a membership gives an encounter with every public member of the
  faction.
- F1 (0126) -- encounters are present, `first_at` at approval, source
  `pc_creation`. Named deferral: dated encounters wait for TICKET-0120.
- G2 -- the approval is refused while the world holds a player character,
  until TICKET-0128's « PJ actif » selector. Reactivation: TICKET-0128
  merged.
- H1 (0126) -- K1-b: a « Joueur » field on a player character in Création;
  « Créatrice » detaches; one character per profile and world, a clear
  refusal otherwise.
- L2 (series) -- an invisible skill cannot be proposed by the player; the
  creator may grant it (see A1 below for when).
- INV-67 -- the final sheet is judged by `creation_check`.

Locked while planning this ticket (2026-10-25):

- A1 -- the review decides only what cannot be done after the approval:
  the starting place, each person (create, attach, drop), each master,
  each membership kept or dropped, each person's feeling for the
  character. These choices live in review columns of the draft tables
  (v2.33) that the player's reads never name. Skills are written at the
  player's ranks; the creator adjusts them after the approval with the
  existing skill tools, an invisible skill included -- L2's « at review »
  becomes « right after the approval ». Rejected A2 (a whole creator layer,
  `creator_rank` and creator rows; reactivation: Nia asks to set ranks
  before the write instead of after) and A3 (`pc_review_*` copy tables:
  the draft twice).
- B1 -- `returned` is writable by the player: he sees « Renvoyé », the
  note and his own version, corrects and resubmits. The note is replaced
  at the next return. Rejected B2 (back to `draft` with the note: a status
  nothing sets, and the creator's list cannot tell a returned draft from a
  new one).
- C1 -- `pc_draft.character_id`, set at approval: the draft leads to the
  character it gave. Rejected C2 (nothing).
- D2 -- one NPC batch per logical group (F'a-1 to the letter), several open
  at once, each tied to the draft and its group. Rejected D1 (one batch per
  draft, one line per sketch; reactivation: Nia finds a batch per group too
  heavy to follow).
- E1 -- two steps: « Préparer » generates each group's batch outside
  canon, reviewed row by row; « Approuver » is one transaction (NPCs,
  masters' rank, character, skills, memberships, knowledge, relations,
  encounters, the draft closed, the batches committed). Nothing is
  written when a step fails. Rejected E2 (the batches committed first:
  NPCs without anchor when the character fails).
- F1 -- the master is a line of its group's batch; its Maître rank is
  written at approval before the character. Rejected F2 (the creator
  creates the master by hand, then attaches it).
- G1 -- each person created or attached gets a relation NPC -> character,
  which also records the encounter. Rejected G2 (an encounter only;
  reactivation: the default relations are often deleted after approval).
- H1 -- the character recipe leaves `routes/creator.py` for a commit-free
  writer used by the route and by the approval. Rejected H2 (a second copy
  of the recipe).
- I1 -- one ticket, seven briefs. Rejected I2 (an approval without
  batches first, the batches in a later ticket).
- J1 -- the NPC row commit moves to `cockpit/npc_group_commit.py`; the
  approval's orchestration lives in `cockpit/pc_approval.py`; the
  character writer in `writes/` never names the staging tables; both
  cockpit modules join the NPC agent's strata check. Rejected J2 (a route
  importing another route).
- K1 -- the review sets each person's relation type (the social types of
  the relation fiche) and intensity, `ally` and 60 by default, direction
  NPC -> character, the sketch's role as the note. Rejected K2 (the model
  proposes the relation; reactivation: Nia often changes the default type).

## Carried forward / open

- TICKET-0128: the « PJ actif » selector lifts G2 (the approval's
  `world_has_pc`).
- TICKET-0120 (time): dated encounters for « membre depuis longtemps »
  (F1 (0126)).
- Ranks at review (A2): only if Nia asks to set ranks before the write.
- A designer metric in « Suivi » (acceptance of the counter-proposal): its
  own ticket when Nia wants it.
- A skill's description is shown as written once visible (from 0126).

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Every check passes  -> verify/checks/corpus_gate.py
- [ ] v2.33: the review columns, the draft's character, the review batch's draft and group, the row's sketch, the source `pc_creation`; the migration applies once  -> verify/checks/review_schema.py
- [ ] The v2.32 shape check follows the new columns  -> verify/checks/creation_schema.py
- [ ] The review check, the review routes, the return and resubmission, the batches per group and K1-b behave as specified  -> verify/checks/creator_review.py
- [ ] The approval writes the whole character in one transaction, or nothing  -> verify/checks/draft_approval.py
- [ ] The creator's review section and the player's returned and accepted states are wired  -> verify/checks/creator_review_ui.py
- [ ] The staging tables are touched only by the NPC agent's modules and the approval  -> verify/checks/npc_agent_strata.py
- [ ] Every canon write goes through a listed site  -> verify/checks/single_canon_write.py
- [ ] The character writer is a known location writer  -> verify/checks/zone_placement.py
- [ ] The carrure and the open skills follow their new modules  -> verify/checks/npc_skills.py
- [ ] The player's draft stays judged by the one check; a submitted draft stays locked  -> verify/checks/player_creation.py
- [ ] The player shell stays in `/api/joueur/`  -> verify/checks/player_shell.py
- [ ] The world cascade deletes every row the new columns hang on  -> verify/checks/world_cascade.py

### Live  ->  human gate (Nia)
- [ ] In a world without a player character, a profile submits a character
      with a skill that requires a master, a family of two, a membership
      and two knowledge lines. In Création > Personnages joueurs >
      « Soumis », the draft opens with its review section.
- [ ] Choose another starting place, attach the master to an existing
      Maître (or create one), drop one person, keep the membership, change
      one relation type; save; reopen: the choices hold. The verification
      lists what is still missing.
- [ ] « Préparer le lot » for each group, then generate: one row per person
      to create, each named as in the story; reject one row, rename
      another. The NPC agent's own panel shows none of these batches.
- [ ] « Renvoyer » with a note: in `/jouer`, the player sees « Renvoyé par
      la créatrice. », the note and his own version, corrects and
      resubmits. Back in Création, the review choices are still there and
      the batches must be prepared again.
- [ ] « Approuver »: the character appears in « Personnages joueurs »,
      linked to the profile, at the chosen place; his skills show the
      player's ranks, the skill that requires a master taught by the
      chosen master; the created people exist as NPCs with a relation to
      him; he has met the faction's public members. In `/jouer`, the
      player reads that his character was accepted.
- [ ] On another world, attach an existing player character to a profile
      with the « Joueur » field, then give it back to « Créatrice ».

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
