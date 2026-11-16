---
id: TICKET-0127
slug: character-perspective
title: A character's perspective -- the player asks what his character knows; the creator asks as any character, with the audit
type: feature
status: live-gate
created: 2026-11-14
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
lot_id: LOT-0127-character-perspective.md
brief_ids: [A, B, C, D, E]
current_brief:
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> TICKET-0127 : les savoirs du joueur
> But. Le joueur interroge le monde comme avec l'outil Lore, mais ne reçoit
> que ce que son personnage sait.
> Ce qu'il comprend :
>
> * Une nouvelle perspective, « un personnage ». 0125 a construit le
>   pipeline avec une seule perspective, « public » (N1). 0127 ajoute la
>   perspective d'un personnage donné, à côté de celle-là : ses
>   connaissances, ses rencontres, ses appartenances, plus ce que tout le
>   monde sait.
> * Pour n'importe quel personnage (H1-a), pas seulement les PJ. Tu pourras
>   voir le monde du point de vue de chaque PNJ.
> * « Répondre en tant que X » dans Lore (H1-b), avec le même code que la
>   surface joueur. C'est ce qui te permet de vérifier que l'outil dit
>   juste.
> * La vue d'audit (H1-c) : les lignes retenues, chacune avec sa raison,
>   comme l'audit « public » de 0125.
> * Le journal (H1-d) : chaque question et chaque résolution sont
>   journalisées, et un contrôle G1 avec une mutation nommée prouve qu'un
>   secret ne fuit pas.
> * Côté joueur : l'écran « Mes savoirs » dans `/jouer`, sous INV-66 (une
>   surface joueur n'apprend le monde que par une perspective).

> A!, B1, C1, D1 mais il peut aussi connaitre l'existance des factions dont
> il ne fait pas partie, il en connais juste l'information publique. E1, F1,
> G1, H1, I1. ok pour le decoupage

> D1-a

## Clarifications resolved (intake)

- « A! » is A1 (read back to Nia, not contested).
- D1's amendment: a public faction the character does not belong to is in
  his view through « les entités publiques »; he reads its public facts plus
  whatever he has himself learned (D1-a). A non-public faction he does not
  belong to exists for him only when a fact he knows names it (D1's
  « participants »); otherwise the audit names it « unknown to him ».
- The engine already resolves what an entity knows (`resolve_known_for_entity`,
  R-10); the character's perspective is built on it, never on a second
  authority.
- A PC's knowledge is never secret (INV-07); the player's door still drops
  secret rows by construction, and the check proves it with a deliberately
  secret PC row (C-15).

## Decisions locked (do not re-litigate without Nia)

- A1 -- one code for both perspectives: `PublicView` becomes
  `PerspectiveView` (public or character); the selectors, executor, audit and
  renderer take it; « public » is one case. The selectors take neutral names
  in a pure-rename commit first. Rejected: A2, a sibling module of character
  selectors (a second copy, against H1-b).
- B1 -- the resolution is the authority. A line's text is what the character
  believes: his knowledge row's own wording when he has one, else the version
  of the fact he last saw. Certainty is said in words (« rumeur »,
  « soupçon », « partiel »), never the raw level. « Croyance fausse » is shown
  only in the audit and the creator's detail. A stored `unaware` row hides
  even a public fact. Rejected: B2, the fact's current text and no level (the
  player would learn a version his character never saw; a rumor would read
  as certain).
- C1 -- at the creator's door, the character's perspective holds what he
  knows and conceals, marked as such (the tick's precedent); at the player's
  door those rows are excluded by construction. Secret memberships never
  enter rows (INV-03); the audit names them. INV-01 is amended by one
  sentence. Rejected: C2, secrets excluded everywhere (reactivation: a
  discrepancy Nia finds while checking an NPC).
- D1, D1-a -- the entities a character knows: the public ones, the ones he
  met, himself, the factions of his non-secret memberships, and the
  participants of the facts he knows; a new name regime `character`
  restricted to them; a binding outside them is refused. Of a faction he does
  not belong to he reads the public information plus what he has learned
  himself, with its certainty. Rejected: D2, the `perceiver` regime as is (an
  unknown homonym would surface in « Laquelle ? »); D1-b, only the public
  information of a foreign faction (one more rule, and a rumor learned in
  play would vanish).
- E1 -- a « self » selector for the character only: the people he met, his
  skills and their rank. Rejected: E2, nothing more.
- F1 -- known event facts enter the dossier of their participants, for both
  perspectives (one code), labelled « Événement ». Supersedes drafting
  decision 8 of TICKET-0125. Rejected: F2, the character only (one selector,
  two behaviours); F3, not now.
- G1 -- new routes `/api/joueur/personnage/savoir/{ask,resolve}` with the
  world, the profile and the character, refused unless it is that profile's
  character in that world; « Mes savoirs » replaces the public section of the
  world page when the profile has a character. The public routes stay for
  creation. Rejected: G2, one route whose perspective the server picks.
- H1 -- the journal keeps its kind and steps; the payload gains
  `perspective: "character"` and `character_id`. No migration. Rejected: H2,
  a relational column (reactivation: Nia wants a per-character metric in
  « Suivi »).
- I1 -- Lore's Perspective tab offers « Tout le monde » or « Un personnage »,
  with every character of the world, players and NPCs grouped; answer, rows
  and audit as today.
- Cut -- one ticket, five briefs: pure rename; view and name regime;
  selectors; executor, audit, renderer, flow, routes and journal; the two
  screens, the docs.

## Carried forward / open

- The player's character is never re-read while the world page stays open:
  a character approved meanwhile appears on the next opening. No ticket
  unless Nia asks.
- The « PJ actif » selector (TICKET-0128) will let a profile hold several
  characters in a world; `player_character_of` reads the one the unique index
  allows today (R-18). 0128 revisits it.
- Dated encounters wait for the time system (TICKET-0120); `as_of` already
  dates what a character saw.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] A character's view holds exactly the facts he knows minus the
      creator's notes, the entities of D1, his visible and held skills; the
      player's door drops his secret rows  -> verify/checks/character_perspective.py
- [ ] The `character` name regime names only the character's entities; an
      unknown homonym is never a candidate  -> verify/checks/character_perspective.py
- [ ] Every selector answers through the view: beliefs, versions,
      certainty, secret marks, rule M, events in the dossier, the self
      sheet  -> verify/checks/character_perspective.py
- [ ] The audit names every withheld line with its reason (not known,
      unknown entity, membership, skill, false belief, stale version,
      concealed)  -> verify/checks/character_perspective.py
- [ ] The creator asks as any character; the player asks as his own; a
      secret row never reaches the player's render prompt; every question
      is journaled with its character  -> verify/checks/character_perspective.py
- [ ] The public perspective is unchanged but for events in the dossier
      -> verify/checks/perspective_isolation.py
- [ ] The routes stay thin and the player's door selects only its own
      tables  -> verify/checks/player_routes.py
- [ ] The Lore panel and « Mes savoirs » are wired and built
      -> verify/checks/player_shell.py
- [ ] `name_index.py`, `creation_designer.py`, `player_creation.py`,
      `draft_approval.py`, `player_entry_schema.py`, `knowledge_identity.py`,
      `lore_isolation.py`, `file_map.py`, `module_budget.py`,
      `claude_md_contract.py` stay green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] 1. Lore > Perspective > « Un personnage »: the list shows the players
      first, then the NPCs.
- [ ] 2. As an NPC who keeps a secret, a question on it answers with the
      secret marked; the « Retenu » list shows what he does not know, with
      the reasons in French.
- [ ] 3. As the same NPC, a question on someone he never met answers « Rien
      de ce que <nom> sait ne répond à cette question. » and « Retenu »
      names the entity as unknown to him.
- [ ] 4. In `/jouer`, with an approved character, the world page shows
      « Mes savoirs — <nom> »; a question answers from what he knows.
- [ ] 5. With a profile without a character, the page still shows « Ce que
      tout le monde sait ».

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
