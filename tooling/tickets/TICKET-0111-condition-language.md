---
id: TICKET-0111
title: The condition language -- a tree of four connectors over the requirement forms, stored as rows, one language for every agenda
type: feature
status: intake
created: 2026-10-08
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: large
lot_id: LOT-0111-condition-language.md
brief_ids: [A, B, C, D]
current_brief:
schema_version_touched: v2.20
retry_count: 0
slug: condition-language
---

## Request (verbatim, as Nia stated it)

The series (« conditions ») opened in this planning conversation
(2026-10-08), after TICKET-0110 was merged and before TICKET-0111 (rank
trials, the last of the « quêtes et compétences » series) was begun:

> Est-ce qu’on pourrait gérer toute les conditions comme des requêtes SQL
> mais en langage naturellle et il y a un interprête qui écrit la requête, je
> confirme et ça devien ma condition, je pourrais dire; le joueur apporte 15
> fourrures de loup?

> Voila une liste, NON Exaustive de question/condition de quête. La limite
> est seulement l’imaginaire de la personne qui crée le monde. Mon objectif
> dans ce projet et ce pourquoi on travail c’est d’avoir un generateru de
> jeu/monde/univers autosifisant qui te permet un maximum liberté pour créer
> l’expérience que tu veux. Le travail que je fait là sert a mettre les base
> pour cela, si nous somme dans la mauvaise voie, il est encore temps de
> changer. Concernant le modèle 8B abliterated sert a faire des test, mais
> plus recement, je fais des test avec un 14B abliterated et Gemma 4 12B pour
> plus de précision. Je vais faire l’aquisition d’un ordinateur plus
> performant lorsque ce sera le temps. Je ne veux pas que tu considère le
> modèle 8b comme une limite, je veux que tu considère ce que peux faire un
> LLM plus gros. Je voudrais justement ne pas avoir a faire un ticket a
> chaque nouvelle forme de questions. Ticker 0110 est mergé et 0111 en
> attente de mes décisions (non commencé)

Her list of 49 conditions followed (a target dead, N enemies of a type
killed, a boss defeated with no ally fallen, an item held, given, destroyed,
made or returned intact, a place reached, a secret passage found, an NPC
convinced, two factions allied, a culprit identified, an alarm left silent,
no magic used, before day N, a place held N turns, a curse lifted, a throne
occupied by Y, sub-quests X, Y, Z done, N conditions of M, a quest failed).

Then the codes:

> A1, B1, C1 faire attention a la collision du vocabulaire, il existe déja
> évênement, il faudra peut-être changer ce dernier. D1 je dois pouvoir
> calculer le taux d'acceptation (petit dash bord créateur qui me permet de
> suivre des statistique et des conditions de réactivation? E1.

> F1 Question en plus : Est-ce que les évènements sont aussi des faits ou des
> faits en découlent ? G il va falloir que tu m'explique plus en detail le
> concept d'état du monde. Donne des exemples. H1, I1. J1

> K1, G1, L1

> M1, N1, O1, P1, Q1, R1, S1, T1

> O-a, GP1

After Claude Code's STOP on BRIEF-0111-D (`tooling/questions/QUESTION-TICKET-0111.md`,
trigger D1-a), AMENDMENT-0111-01:

> A1, V2 si tu n'a pas d'autres objections,  cela ne me dérange pas que tue
> le loup soit seulement suivi a partir de 0114

## Clarifications resolved (intake)

- **The obstacle is not the language but what the engine records** (the
  planning RECON): of the 49 conditions, only those about canon already
  kept -- holdings, known facts, relations, memberships, encounters,
  passages, ledger, ranks, quest states -- can be judged today. World state
  (alive, open, cursed, occupied by) and events (killed, captured, spotted)
  are not recorded. Hence a series, not a ticket: the language first
  (0111), then the interpreter, the state, the events.
- **Why not SQL, even with a larger model** (A2 rejected): stored SQL
  breaks at every migration, bypasses the structural exclusion of secrets,
  and cannot ask about what is not recorded. The tree is compiled by code.
- **An event is the truth; a fact makes it learnable** (K1): the fact spine
  already allows a fact to BE an event (`fact.event_id`); each event type
  will say whether it is born with a fact and its default scope.
- **World state** (G1, L1): an attribute is what is true now (« le pont est
  détruit »); an event is what happened (« 3 loups tués, jour 12 »). An
  event of play sets an attribute; a correction edits it without one.
- **« événement » collides** (F1): the existing `event` table becomes the
  one journal in 0114, not a second table.
- **A requirement is never an objective** (LOT R-01, R-07): a step's
  requirements say whether it may be attempted; most of the 49 are
  objectives. Hence M1: a third role, completion.
- **The tree cannot be JSON** (LOT R-14): CLAUDE.md keeps UI-visible data
  relational; O1 was put back to Nia as O-a / O-b.
- **A third language exists** (LOT R-19): `goal_prerequisite`, an NPC
  goal's completion gate; GP1 keeps it out of this ticket.
- **Numbering** (`next_id.py` -> 0111; Nia's rule « un report va toujours
  dans un ticket de numéro supérieur »): this series takes 0111; the rank
  trials planned as 0111 move to 0116 (J1).

## Decisions locked (do not re-litigate without Nia)

The series (« conditions »), locked 2026-10-08:

- **A1** -- conditions are a language in a tree: generic primitives,
  connectors, an interpreter in natural language that proposes, code that
  validates and compiles; Nia confirms. Rejected: A2 (generated SQL;
  reactivation: a real condition the tree cannot express even with a new
  primitive); A3 (a closed vocabulary grown ticket by ticket).
- **B1** -- world state as attributes defined per world (0113).
- **C1** -- a generic event journal, event types defined per world (0114).
- **D1** -- narrative events are proposed by the MJ and reviewed by Nia;
  their acceptance rate measurable on a creator dashboard. Rejected: D2
  (auto-applied; reactivation: an acceptance rate measured high enough
  under D1); D3 (Nia alone, by hand).
- **E1** -- this series before the rank trials.
- **F1** -- the existing `event` becomes the one journal: a type defined
  per world, roles on its participants, a quantity, a day; the seven
  categories become a type's domain; a type says whether it enters the
  chronicle. Rejected: F2 (a second table « acte »; reactivation: a
  measured slowdown of the chronicle by the volume of traces); F3 (renaming
  the existing table).
- **G1** -- an attribute is a definition per world and a value per entity,
  with its history; the fixed states that exist (`vital_status`) are read
  as « system » attributes. Rejected: G2 (entity-type traits: DDL per
  idea); G3 for now (migrating `vital_status`; reactivation: one state
  stored in two places that diverge).
- **H1** -- the creator dashboard is a registry of metrics in code (a
  query, a threshold, the decision code it watches); a reactivation
  condition joins it when created or touched. Rejected: H2 (metrics
  written in the UI: free SQL); H3 (back-filling the 109 existing ones).
- **I1** -- one language for every agenda: the tree replaces both
  requirement tables; the model emits trees restricted to its forms.
- **J1** -- the order: 0111 the language, 0112 the interpreter, 0113 the
  attributes, 0114 the event journal and the MJ's proposals, 0115 the
  dashboard, 0116 the rank trials.
- **K1** -- each event type declares whether it is born with a learnable
  fact and its default scope; `event.knowledge_status` gives way to the
  scopes. Rejected: K2 (every event a fact), K3 (no automatic fact).
- **L1** -- a state changes in play through an event that sets it; only a
  correction edits it directly. Rejected: L2 (free edits, an event
  optional).

This ticket's, locked 2026-10-08:

- **M1** -- three roles for one language: eligibility, prerequisite, and
  completion (« objectif atteint quand »), shown in Journée and in
  « Déclarer accomplie », never acting. Rejected: M2 (completing on its
  own; reactivation: a dashboard metric showing Nia confirms what the
  condition already says).
- **N1** -- a failure condition waits for the event journal (0114).
- **O-a** -- the tree is rows: `condition` (one per owner and role) and
  `condition_node`. Rejected: O-b (JSON with an exception in
  `json_ui_boundary.py`: the first for durable canon, no foreign keys).
- **P1** -- every leaf names its subject: `doer`, `giver`, `contact`, or one
  character. Rejected: P2 (always the player).
- **Q1** -- the day's NPC and the deepened facts read the leaves reached
  through `all` only. Rejected for now: Q2 (explicit step fields;
  reactivation: a step whose day's NPC is not the target of a relation).
- **R1** -- a verdict has three states, `met`, `unmet`, `unknown`, from
  now. Rejected: R2 (two now, widened later).
- **S1** -- the ten forms plus `item_held`, `vital_status`, `quest_state`
  (all reading data the canon already keeps), and the four connectors; the
  model keeps its four forms.
- **T1** -- the list editor stays and writes `all`; a nested condition is
  shown read-only, edited by the interpreter (0112). Rejected: T2 (a visual
  tree editor).
- **GP1** -- `goal_prerequisite` gets its own ticket, after this one.

AMENDMENT-0111-01, locked 2026-10-08:

- **A1** -- a player surface (Journée's quests, « Déclarer accomplie », a
  standing plan's refusal, a blocked step's line in the narration) writes a
  fact out only when the character resolves it above `unaware`; otherwise
  « un fait encore caché ». It closes the path open since TICKET-0108 too.
  The creator's surfaces are unchanged. Rejected: A2 (the fact as
  player-visible: the secrets invariant); A3 (no `knowledge` leaf in a
  completion: 0108's path stays open, « apprends X » is lost).
- **V2** -- on a player surface, a judged leaf about someone else (the
  giver, the contact, a named character) reads `?`, and a head line is
  recombined from what is left; another's regard is never counted. A leaf
  about the character himself is shown, its target named. Rejected: V1
  (the canon's state as a quest tracker; reactivation: the event journal of
  TICKET-0114 knows who witnessed what -- « tue le loup géant » is tracked
  from then).

## Carried forward / open

- **The interpreter in natural language** (A1): TICKET-0112. It proposes a
  tree in C-03's dict form, the code validates it (`clean_condition`), Nia
  confirms; a nested condition becomes editable through it (T1).
- **World state attributes** (B1, G1, L1): TICKET-0113. Measured on the way
  (LOT R-13): `item.condition` (`'intact'`) is already a state of an item.
- **The event journal and the MJ's proposals** (C1, D1, F1, K1): TICKET-0114,
  with the failure condition (N1) and the « absence over a period »
  conditions (a fourth leaf state is NOT needed: `unknown` exists, R1).
  Measured: `event` (`src/world_engine/models/canon.py:479-503`), its seven
  categories (`tick_normalize._EVENT_TYPES`, `:67-69`), `knowledge_status`
  read by the tick (`tick_context.py:622,725`), `fact.event_id`
  (`models/canon_knowledge.py:107`), `write_event` creating no fact.
- **The creator dashboard** (H1): TICKET-0115. `proposed_mutation` already
  keeps `status`, `proposed_at`, `reviewed_at` (`models/pipeline.py:126-145`):
  D1's acceptance rate is computable from existing rows.
- **Rank trials** (K1 of the « quêtes » series): TICKET-0116, in this
  language.
- **`goal_prerequisite`** (GP1): its own ticket, numbered after 0111.
  Reactivation: this ticket merged.
- **M2** (a completion that acts on its own): reactivation -- the dashboard
  shows Nia confirming what the condition already says.
- **Q2** (explicit day's NPC and deepened facts on the step): reactivation
  -- a step whose day's NPC is not the target of a relation.
- **V1** (show another's state on a player surface): reactivation -- the
  event journal (TICKET-0114) records who witnessed an event.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] The forms live in one module; the tree's shape, its three-valued evaluation, its subjects and its French; the storage, the v2.20 migration, the twelve forms, every agenda on trees; the completion, the API and the editors; what a player may read (AMENDMENT-0111-01) -> verify/checks/conditions.py
- [ ] The day plan's gates keep their meaning on the new home and storage -> verify/checks/day_plan.py
- [ ] Quest offers keep 0108's contract on condition trees -> verify/checks/quests.py
- [ ] Debts keep 0110's contract, their two forms included -> verify/checks/debts.py
- [ ] Settlement keeps 0109's contract -> verify/checks/quest_rewards.py
- [ ] Knowledge identity and the day's knowledge gates hold -> verify/checks/knowledge_identity.py
- [ ] Every form has its French detail -> verify/checks/day_narration.py
- [ ] The moved BFS reader is documented -> verify/checks/known_reachability.py
- [ ] Canon writes stay on sanctioned sites, the condition writers included -> verify/checks/single_canon_write.py
- [ ] The world cascade covers the two new tables -> verify/checks/world_cascade.py
- [ ] No JSON column is added -> verify/checks/json_ui_boundary.py
- [ ] Schema doc and code agree on v2.20 -> verify/checks/schema_version_agreement.py
- [ ] The built frontend matches its sources -> verify/checks/frontend_build_fresh.py
- [ ] The whole corpus is green -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] BEFORE the migration, read-only on prod, report the three numbers:
  `SELECT COUNT(*) FROM agenda_step_requirement;`
  `SELECT COUNT(*) FROM quest_offer_requirement;`
  `SELECT type, COUNT(*) FROM quest_offer_requirement GROUP BY type UNION ALL SELECT type, COUNT(*) FROM agenda_step_requirement GROUP BY type;`
- [ ] After `python scripts/backup.py`, with `WORLD_ENGINE_ENV=prod`:
  `python scripts/migrate_v2_20_conditions.py` reports `Migration v2.20
  applied.`, its « Post-check » line naming the leaves by form -- their
  total equals the two counts above, `quest_completed` counted as
  `quest_state` -- and its notes. The cockpit boots.
- [ ] Création › Quêtes: an existing offer opens with its conditions as
  before (one row each); each row starts with « Le personnage ». Add to a
  step « Objectif atteint quand » : « Possède au moins (objet) » 3 ×
  Fourrure; save, reopen: kept.
- [ ] A row « Quête dans l'état » shows the four states; « Est dans
  l'état » shows no target and the four vital states, and its subject can
  be a character (« Garde ») -- saved and kept.
- [ ] Journée › Quêtes: accept that offer; its active step shows
  « Objectif : » with « ✗ Le personnage possède au moins 3 × « Fourrure »
  — 0/3 » (or her real count); on Millys's sheet, in its items panel, set
  Fourrure to 3; reload Journée: the line reads ✓ and « Objectif atteint ».
  Nothing completes by itself.
- [ ] « Déclarer accomplie » shows the same lines under the step.
- [ ] A1/V2 (AMENDMENT-0111-01): give a step of an offer « Objectif atteint
  quand » : « Le personnage connaît » a fact Millys does not know (a secret
  of an NPC), and « Le donneur a rencontré » someone. Accept it: Journée
  reads « ✗ Le personnage connaît un fait encore caché » and « ? Le donneur
  a rencontré … (le personnage ne peut pas le vérifier) », never the fact's
  text and never « Objectif atteint ». Création › Quêtes still shows the
  fact's text. Give Millys the fact on her sheet; reload Journée: its text
  appears.
- [ ] Declare a day for an ordinary plan (no quest): the plan is cut and
  resolved as before; a step blocked by a requirement still says what it
  lacks in French.
- [ ] An offer whose eligibility a former `quest_completed` row gated is
  still proposed exactly when that quest is accomplished.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
| AMENDMENT-0111-01 | D | a player surface wrote out the fact of an unmet `knowledge` leaf, since TICKET-0108 (R-23); A1, V2 | D |

## Escalations

### E-01 — archived — QUESTION-TICKET-0111.md

**Response:** archived from `tooling/questions/QUESTION-TICKET-0111.md`, which the ticket pipeline wrote before escalations moved into the ticket. The file follows verbatim, its own Response included.

~~~~markdown
# QUESTION — TICKET-0111
Trigger: D1-a
## Context
BRIEFs 0111-A, -B, -C are committed (verify checks and corpus gate 144/144 green at each step).
BRIEF-0111-D's embedded diff applies cleanly, its checks pass (conditions, quests, quest_rewards,
debts, creation_island, page_contract, frontend_build_fresh, module_budget, function_length,
decisions_index) and the frontend is rebuilt. It is applied in the working tree but NOT committed.
Stopped before commit because of the brief's own rule: a finding that touches an invariant is a
STOP even if unlisted.
The finding: `quest_reads._steps_view` (the player's quest payload, read by `player_quests` and the
settlement recap) now returns `"completion": verdict_lines(db, completion)`. For a `knowledge` leaf,
`condition_text._target` renders the fact through `prose_render.fact_text` (no scope filter). So a
creator-authored completion such as « Le personnage connaît « <fact> » » shows the fact's full text to
the player, even when the player does not know that fact — it may be an NPC secret or the creator's
note. This touches "Secrets are structurally excluded" / "the player never learns what the character
is not meant to know". Noted ATTENTION at /review-step for B and C; D is where it becomes reachable.
## Question
Should a `knowledge` leaf shown in a player-facing completion line reveal the fact's text only when the
player already holds a Knowledge row on it, and otherwise show a neutral phrase (« quelque chose à
apprendre »)?
## Options
A. Yes — filter by query construction in the player path (`_steps_view` only; creator views and the
   Lore dossier keep full text). Adds a small change to D's diff, then commit and continue.
B. No — the creator's completion text is deliberately player-visible; accept as is.
C. Forbid `knowledge` leaves in a `completion` condition at write time.
## Response
A1, V2 -- AMENDMENT-0111-01
~~~~
