---
id: TICKET-0126
slug: character-creation
title: The player creates a character -- creation rules and their one check, the visible skills in the public view, a designer that reads only what everybody knows, a draft the player reviews and submits
type: feature
status: live-gate
created: 2026-10-22
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: large
lot_id: LOT-0126-character-creation.md
brief_ids: [A, B, C, D, E, F, G, H, I]
current_brief: I
schema_version_touched: v2.32
retry_count: 0
---

## Request (verbatim, as Nia stated it)

From the request that opened the player series (TICKET-0125), the part this
ticket serves:

> Lorsque je rencontre, je dois créer mon personnages. c'est-à-dire: Je dit
> qui je suis dans ce monde, on me montre les compétences de base que je
> peux avoir dans ce monde ( celles qui ne necessite pas de les apprendre de
> quelqu'un), je peux choisir jusqu'a 1 compétence qui nécessite un maitre,
> je dois justifié comment je l'ai appris. (ici, on va créer une NPC de
> l'autre coté tu suis ?). Le joueur peut ajouter jusqu'a 2 autres NPC ( un
> maximum de 3). Cela permettra de l'ancré dans le monde.

Planning of this ticket (2026-10-22), Nia's answers as written:

> A1, A-b1 le cout par palier est le defaut, mais dans l'outil de création,
> je peux l'ajusté a mon bon désir par monde B1, C1, D1, E1, F1 avec report
> nommé lorsque l'on fait le système de temps du monde. G2 si les surfaces
> ne fonctionnent pas, cela sert a rien. Je vais faire les tickets avant de
> rejouer sérieusement de toute façons. H1, I1, J1, L2, M j'ai réglé le
> problème des artefacts entre temps tu ne t'en occupe pas.

> N2 Si c'est publique? pourquoi ne pas les mélanger ensemble ? [...] O1, P1
> ok pour les commentaires, R1, S1, T1, U1, V1, W1 assure toi qu'il n'y
> aurra pas de problème d'affichage (empilement dans ma l'onglet). X1.

> W1' et je veux le selecteur pour le lore. On est en train de géré cela et
> je vais l'oublier sinon.

> J1'

## Clarifications resolved (intake)

- The player series is cut in tickets (S1): 0125 the player's entry
  (merged), 0126 creating a character -- the player's side up to the
  submission --, 0129 the creator's review and the write to canon, then
  0127 the player's knowledge and 0128 the player's day. 0129 runs before
  0127 by decision (L2, cut), not by dependency.
- « Compétence à maître » means a skill that requires a master
  (`skill_definition.requires_master`), never the rank Maître (5). Both
  are named apart everywhere in this ticket.
- The world has no calendar before TICKET-0120: an encounter's `first_at`
  is a real date, so « membre depuis longtemps » cannot be dated yet.
- `routes/player.py` is held by `player_routes.py` PR8 (no `chat(`, its
  `select(` limited to `User`, `World`, `WorldLaw`): the creation routes
  live in a module of their own.
- Approving a character (0129) in a world that already has one would make
  every creator surface of that world refuse until 0128 (M2,
  `_player_character_id`, `cockpit/crud/entities.py:209-229`).

## Decisions locked (do not re-litigate without Nia)

Locked for the series before this ticket (handover, TICKET-0125):

- A1' -- Nia alone, on her machine, no password, several player profiles.
- B2 -- player routes are keyed by the world, then the character, never by
  `world.is_active`.
- D2 -- the designer proposes the starting place.
- E1' -- draft, the player's pre-review (he may correct it himself),
  submission, the creator's final review. Nothing reaches canon before her
  approval. During creation the player can question the public lore.
- F' -- the player writes his backstory; the designer draws what it
  implies (people, memberships, knowledge).
- F'a-1 -- player side: the designer reads only the public lore and the
  player's text, and draws sketches of people (a name, what the person is
  to the character, the sentence that grounds it, a logical group), 8 at
  most, with a clear message. Creator side, at review (0129): each group
  becomes one NPC batch anchored on the character, developed with all the
  lore; a sketch may be attached to an existing character.
- F-b -- a proposed membership gives an encounter with every public member
  of the faction (0129). F-c -- the player-side designer reads only the
  public lore.
- K1-b -- an existing character can be attached to a player profile from
  Création (0129).
- L2 (series) -- « visible à la création » cascades world, then system,
  then skill, visible by default; an invisible skill cannot be proposed by
  the player, the creator may grant it at review.
- Q -- point-buy: the start is unchanged (base domains and open skills at
  Initié); a pool per world, 6 by default; a cost per rank set per world,
  rising by default; lowering a skill to Inexpérimenté gives back a point.
- Q-limits -- a closed list of rule kinds (a new kind is code, a new value
  is data): a maximum rank at creation (world, system, skill); a maximum
  number of skills that require a master; a cap per exact rank; per system,
  a cap of raised skills and a cap of held skills. « Pas de maître » is two
  rules.
- The skill circuit -- the player proposes ranks with a justification, the
  designer counter-proposes, the player accepts or corrects; one function
  in code judges the player's sheet, the designer's and the final one.
- R1 (series) -- the creation settings and their check arrive here, with
  their readers.

Locked while planning this ticket (2026-10-22):

- A1 -- a skill that requires a master starts at Inexpérimenté, as a
  skill learned; reaching Initié costs the Initié step. Rejected A2 (free
  at Initié; reactivation: Nia wants the master's « dowry » as a backstory
  gift).
- A-b1 -- costs are per step, rising: Initié 1, Apprenti 1, Confirmé 2,
  Expert 3, Maître 4 by default, each set per world in Création.
- B1 -- the draft is relational (`pc_draft` and its child tables), never a
  JSON payload. Rejected B2 (a `pc_creation` proposal in JSON;
  reactivation: the draft is never shown to the player after submission),
  B3 (relational draft plus a proposal pointer: two truths).
- C1 -- while submitted, the draft is read-only; a refusal (0129) gives
  back the player's own version with the creator's note, never her edits.
  Nothing is deleted.
- D1 -- the starting place is a public, visitable place (not a zone); the
  designer proposes, the player may change it within that list; the
  creator may choose any place at review (0129).
- E1 -- every skill that requires a master needs a « master » sketch for
  that skill; at review the master is an existing character at Maître in
  it, or created at Maître (0129). Rejected E2 (raising an existing NPC to
  Maître inside the approval).
- F1 -- encounters are present, `first_at` at approval, a new source
  `pc_creation` (0129). Named deferral: dated encounters wait for the
  world's time system, TICKET-0120.
- G2 -- the approval (0129) refuses while the world already holds a player
  character, until TICKET-0128's « PJ actif » selector. Reactivation:
  TICKET-0128 merged.
- H1 -- K1-b lives on the character's sheet in Création, a « Joueur »
  field; « Créatrice » detaches (0129).
- I1 -- `world_premise` takes the chosen world (`world_id`); the designer
  receives the visible skills in its own block, the `player` regime stays
  as it is. Rejected I2 (a `player_creation` regime).
- J1' -- every world-level creation value lives in one `creation_rules`
  row per world; the system and skill overrides are columns of
  `skill_system` / `skill_definition`; nothing is added to `skill_rank`.
  Rejected J1 (values on `skill_rank`: a second writer or sentinels, and a
  missing row that cannot tell « default cap » from « no cap »;
  reactivation: a second reader of per-rank values that is not creation).
  Rejected J2 (columns on `world`: `models/canon.py` budget), J3 (a
  key/value table: loses the typed CHECKs of the closed rule list).
- L2 (cut) -- this ticket ends at the submission; the creator's review,
  the write to canon, the NPC batches anchored on the character and K1-b
  are TICKET-0129, run before 0127.
- N2 -- one door: the public view also holds the skills visible at
  creation, read by a public selector `public_skills`, which the Lore
  planner also gets. INV-66 keeps its sense. The creation rules are game
  rules, not the world, read by their own reader.
- O1 -- caps per exact rank exist for Inexpérimenté and for Apprenti to
  Maître, never for Initié.
- P1 -- lowering gives back the world's Initié cost; base domains may be
  lowered; a skill that requires a master gives nothing back; the
  Inexpérimenté cap is the bound, 2 by default.
- R1 (held) -- a skill is held at Initié or above.
- S1 -- the designer makes two calls (`creation_subject`, then
  `creation_design`), reads the public lore gathered by code in between,
  and its skills pass the same check, with one retry on violations.
- T1 -- a sketch carries a name, a role, its grounding sentence, a free
  group, a closed kind (`family`, `master`, `faction`, `other`), the skill
  a master teaches, and optionally the public character it may be; the
  player adds, corrects or removes them; a ninth is refused.
- U1 -- every designer call is journaled in `lore_usage_event`, kind
  `creation`, steps `creation_subject` and `creation_design`.
- V1 -- one open draft per profile and world; refused when the profile
  already has a character in that world; « Redemander au concepteur »
  replaces the designer's suggestions, never the player's choices.
- W1' -- submitted drafts are a group of the « Personnages joueurs » list;
  one opens read-only in place of the sheet (the germ precedent of 0124):
  nothing stacks.
- X1 -- the settings live in Création > Compétences: a « Création de
  personnage » record beside « Rangs du monde », and the override fields
  on the system and skill sheets.

## Carried forward / open

- TICKET-0129 (to open, before 0127): the creator's review of a submitted
  draft -- edits, the check on the final version, refusal with a note
  (C1), the write to canon (character, skills with `taught_by_id`, place,
  memberships, knowledge), NPC batches anchored on the character per
  logical group (F'a-1, with an anchor « personnage » beside the root
  location of `npc_group_author`), attaching a sketch to an existing
  character, masters (E1), encounters (F1, F-b), G2, K1-b (H1).
- TICKET-0120 (time): dated encounters for « membre depuis longtemps »
  (F1, named deferral).
- TICKET-0128: the « PJ actif » selector lifts G2.
- A skill's description is shown as written once the skill is visible: a
  secret written in it reaches the player. The sheet warns; no check can
  tell a secret in free text.
- The designer's model calls are journaled but not measured in « Suivi »;
  a metric (acceptance of the counter-proposal) is its own ticket once
  Nia wants it.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Every check passes  -> verify/checks/corpus_gate.py
- [ ] v2.32: the creation rules, the overrides, the draft tables and the journal kind exist; the skill stratum lives in its own module; the migration applies once  -> verify/checks/creation_schema.py
- [ ] The world cascade deletes every new world table  -> verify/checks/world_cascade.py
- [ ] One function judges a creation sheet; the case table holds; the creator reads and writes the rules  -> verify/checks/creation_budget.py
- [ ] The public view holds the visible skills, the audit names the hidden ones, the planner may call `public_skills`  -> verify/checks/perspective_isolation.py
- [ ] Création > Compétences carries the creation record and the overrides  -> verify/checks/creation_rules_ui.py
- [ ] The premise follows the chosen world; the designer reads only the public view, retries once, caps the sketches and journals every call  -> verify/checks/creation_designer.py
- [ ] Every premise regime holds its usages, the designer's two among `player`  -> verify/checks/world_premise.py
- [ ] The player's draft lives and is submitted only through the check; the routes stay in the public view  -> verify/checks/player_creation.py
- [ ] The player shell reaches creation only through `/api/joueur/`  -> verify/checks/player_shell.py
- [ ] Submitted drafts are a group of the PJ list, opened alone in the column  -> verify/checks/creation_layout.py
- [ ] The creator lists and reads a submitted draft  -> verify/checks/submitted_drafts.py

### Live  ->  human gate (Nia)
- [ ] Création > Compétences > « Création de personnage »: change the pool,
      a cost and the Inexpérimenté cap, save, reopen: the values hold. On a
      system, set « visible à la création » off: its skills disappear from
      `/jouer`'s catalogue.
- [ ] `/jouer`, an open world: « Créer mon personnage » opens the creation
      screen; the skills shown are the visible ones; raising and lowering
      ranks updates the points left; going over the pool or a cap shows the
      reason in French.
- [ ] Write a backstory naming a public character and a public faction,
      ask the designer: a counter-proposal appears beside each skill, with
      its reason; sketches, a starting place, memberships and knowledge
      appear; nothing named is a non-public entity.
- [ ] Take a skill that requires a master without a master sketch:
      submission is refused with the reason; add the sketch: it passes.
- [ ] While creating, « Ce que tout le monde sait » still answers; asked
      « quelles compétences existe-t-il ? », Lore > Perspective lists the
      visible skills and the audit names the hidden ones.
- [ ] Submit: the screen turns read-only. In Création > Personnages
      joueurs, the « Soumis » group shows the draft; opening it shows it
      read-only in the column, the sheet hidden, nothing stacked.
- [ ] A second « Créer mon personnage » with the same profile in the same
      world reopens the same draft.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
