---
id: TICKET-0124
title: Every generator knows the world it writes for -- the world premise, a germ attached to an existing character, a Création page that no longer stacks
type: feature
status: live-gate
created: 2026-10-21
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: large
lot_id: LOT-0124-world-premise.md
brief_ids: [A, B, C, D, E, F, G, H, I, J]
current_brief:
schema_version_touched: v2.30
retry_count: 0
slug: world-premise
---

## Request (verbatim, as Nia stated it)

In the planning conversation (2026-10-20):

> Lorsque je fait une journée (tous les autres surfaces ont le même défaut)
> et que cette journée donne lieu a la création d'une entitée ( ex : un NPC)
> le npc créer ne '' fitte''' jamais dans l'univers. Par exemple, si dans le
> monde, tous le monde peut se lié a une créature spirituelle, un nouveau NPC
> devrais avoir cette information sur lui. Si c'est un monde beaucoup plus
> technologique avec des modification corporelle (par robots) les NPC créer
> devrais avoir de l'information là dessus. Il se passe la même chose pour
> les quêtes généré, elles ne sont pas toujours dans le ton de l'univers.

(2026-10-21):

> A2, B2, C1, D2 les loi du monde sont quelque chose que tous le monde sais
> et qui sont des réalitées observable dans le monde. Si je veux qu'une loi
> du monde ne soit pas visible des joueur je ferai un ticket pour cela a la
> place. E1 pour le germe, je veux pourvoir l'associé a un NPC existant en
> plus s'il existe déja. j'ai eu le cas d'un professeur d'escrime alors que
> j'avais un maitre des épées. ( selon moi on aurrais du me proposé un lien
> entre les deux ou au moins moi j'aurrais du avoir la possibilité de les
> liées. G2 j'ai déja le problème que pourrait être lié a ... je fini par
> perdre cette phrase et je nee crée pas l'autre personne au final. 1.
> ticket 0124. 2. l'état n'existe pas encore en ce moment j'ai créer
> quelques un des exprits comme des NPC avec une relation, les autre je les
> ai mis en description. Je pense que tous le monde peut se lier a un esprit
> est dans les règles du monde. Pour le fontend. En ce moment les germe, la
> création et les competences s'empilent et je vois mal le texte, j'aimerais
> qu'on rêgle cela en passant.

> H1, I1, L1, P il me semble que l'on est mieux de s'en tenir a ce qui se
> fait déja. c'Est a dire, faire une nouvelle version des prompts. Si on se
> met a faire différentes facons de modifié les prompts, on va perdre le
> controle quand le projet va grossir. S1. Question : est-ce qu'il y a une
> place ou je peut modifié les loi du monde? Ta question : je ne vais pas le
> testé avec cette exemple parce que je l'ai réglé a la main. mais c'est le
> premier cas. Claissification Ok

> W1, P1-g

## Clarifications resolved (intake)

- The entity generator receives only a type, a field list and one sentence; the world's laws reach the region generator alone; a Journée germ hands the generator a location id as prose (LOT R-14, R-15, R-17).
- The world's laws and description cannot be edited after the world's creation (LOT R-03): this ticket adds the page.
- The test world Aestia has no « Esprit lié » state yet; its spirits are characters with a relation or a line of description. « Everyone can bind to a spirit » belongs to the world's laws. Creating the state is part of Nia's live gate, not of the lot.
- The « professeur d'escrime » / « maître des épées » case was settled by hand; it is the first case, not the test case.

## Decisions locked (do not re-litigate without Nia)

- **A2** -- the premise carries the description, the laws, and, for a creator surface drafting an entity, the world's skill systems and the states that apply to its type; a draft proposes a value for each state.
- **B2** -- a free-text « Ton et style » field on the world (`world.tone`, v2.30 -- AMENDMENT-0124-01), read by every generator.
- **C1** -- one assembler; every registry usage declares its regime (`creator`, `player`, `none` with a reason); a check holds the render sites to it.
- **D2** -- the play surfaces receive the premise too (`player` regime: description, tone, laws -- never a state, never a skill system). The laws are public: true everywhere, known to all, observable. A law hidden from the players is a separate ticket.
- **Classification** -- approved as proposed; the drafting decisions of the lot place `player_generation` and `skill_catalogue` in `creator`, `npc_batch_placement` and `day_reconcile` in `none`; AMENDMENT-0124-01 places TICKET-0116's `quest_trial` in `creator`.
- **E1** -- a Journée germ keeps the sentence it was mentioned in and its place's name, never a location id.
- **H1** -- a germ can be attached to an existing character (« Rattacher »: no new entity) or created with a link prepared to one (« Créer et lier »); candidates are the characters of its place and the neighbouring places, plus a free picker.
- **G2 / I1** -- a draft names the entities it calls for that do not exist yet; ticking one at save writes an approved germ that keeps its sentence and the link it was born with.
- **L1** -- germs become a group of the entity list, opened in a germ panel; the skill sheet becomes a pane of the sheet (« Fiche | Compétences »); nothing stacks.
- **P1** -- the premise enters every template as a new `prompt_version` (`{world_premise}`), the one existing way to change a prompt; no second injection path.
- **K1** (AMENDMENT-0124-02) -- `prompt_version.py` rule 7's fixture head takes a `none` usage (`conversation_summary`); the guard is tested by WP4, not there.
- **P1-g** -- a cockpit edit or restore of a creator/player template that drops `{world_premise}` is refused (422), and a `none` template that carries it is refused.
- **S1** -- the states the draft proposes are written in the create's own transaction; a failure writes nothing.
- **W1** -- a « Monde » page edits the name, description, tone and laws of a world; the laws keep their full-replace writer, without history.

## Carried forward / open

- H2 (the model recognises an existing character in play; reactivation: Journée germs the creator attaches to an existing character) -- deferred. Opening the 0094 arbitration to inferred mentions changes Journée's behavior; the « Germes » metric counts the attached Journée germs. Own ticket when reached.
- W2 (law history; reactivation: a writer passes world_law_id= to a fact) -- deferred. Laws stay curated config, full-replace, no `change_history`. The day a fact points at a law, the full replace fails on its foreign key: own ticket.
- **B3** -- a structured world bible (several fields instead of one « Ton et style »). Reactivation: Nia fills the free field with the same headings from one world to the next. Not instrumented.
- **A3** -- states derived from the laws' text. Rejected (judgment in code). Reactivation: laws Nia often rewrites into states by hand. Not instrumented.
- **Law hidden from players** -- D2 says a separate ticket.
- **Report-only defects found by the lot RECON** (each its own ticket if Nia wants it): `entity_author._world_id` reads the first world, not the active one (LOT R-15); `routes/day.py` pairs unmatched persons with germs by `zip` while `emit_germs` may skip or truncate, so a germ id can be paired with the wrong mention (LOT R-17).

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] v2.30 `world.tone`; `GET`/`PUT /api/worlds/{id}` read and write name, description, tone, laws  -> verify/checks/world_sheet.py
- [ ] Every registry usage declares its regime; the premise holds the right lines per regime, never a state for a player  -> verify/checks/world_premise.py
- [ ] Every render site of a creator or player usage reads through `premised_prompt` or `call_json`; the others are a closed list  -> verify/checks/world_premise.py
- [ ] The seed and the delivery give every creator/player template `{world_premise}`; the two edit routes refuse a text without it  -> verify/checks/world_premise.py
- [ ] A create writes its states, links and ticked germs in one transaction, or nothing  -> verify/checks/world_extras.py
- [ ] A Journée germ carries its sentence and place name; candidates and attach behave per the case tables; the « Germes » metric counts by source  -> verify/checks/germ_attach.py
- [ ] A draft's states, links, same-as and entities to create are judged by code per the case table  -> verify/checks/draft_world.py
- [ ] Germs are a group of the list; the right column holds no stacked strip; the skill sheet is a pane  -> verify/checks/creation_layout.py
- [ ] The sheet sends the checked world extras with a create  -> verify/checks/draft_panel.py
- [ ] The « Monde » tab edits the world; the create modal carries the tone  -> verify/checks/world_sheet.py
- [ ] Every check of the corpus  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] `migrate_v2_30_world_tone.py` then `apply_ticket_0124_world_premise.py` run on the live database: every creator/player template reads « vN -> vN+1 » once, « unchanged » on a second run.
- [ ] In « Monde », Aestia's tone is filled and the law « tout le monde peut se lier à un esprit » is present; the « Esprit lié » state exists for characters (Vocabulaire du monde).
- [ ] A Journée day that mentions an unknown person gives a germ whose card shows the sentence and the place by name; « Générer la fiche » drafts a character who proposes a value for « Esprit lié » and fits Aestia's tone.
- [ ] A germ is attached to an existing character with « Rattacher »: no new entity, the germ leaves the list, the « Germes » metric counts it.
- [ ] A draft's « pourrait être lié à » entity is ticked at save: a germ appears in the list with its link; generating it pre-fills the link.
- [ ] The NPC tab no longer stacks: the list shows the germs, the sheet takes the column, « Compétences » is its own pane.
- [ ] A prompt edit in the Prompts tab that removes `{world_premise}` is refused with the French message.
- [ ] A Play scene and a Journée day narrate in Aestia's tone, and a law shows in the MJ's behavior.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
| AMENDMENT-0124-02 | D (implemented, uncommitted) | `prompt_version.py` rule 7 calls the guarded routes on an `npc_dialogue` head (K1: `conversation_summary`) | D only |
| AMENDMENT-0124-01 | A (stopped at Mini-RECON, nothing written) | TICKET-0116 merged first: v2.29 taken (-> v2.30), a 47th usage `quest_trial` (-> `creator`), anchors shifted; `corpus_gate.py` red before brief I (pipeline_state arrows) | A, B, C, D (substance); E-J (base commit, shifted anchors) |
