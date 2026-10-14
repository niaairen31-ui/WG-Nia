---
id: TICKET-0121
title: Journée proposes a quest -- the request, the lore searched whole, the existence question, the designer, its review in the offer editor
type: feature
status: escalated
created: 2026-10-13
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: large
lot_id: LOT-0121-journee-quest-designer.md
brief_ids: [A, B, C, D, E, F, G]
current_brief: G
schema_version_touched: v2.28
retry_count: 0
slug: journee-quest-designer
---

## Request (verbatim, as Nia stated it)

The series request is TICKET-0111's; TICKET-0119 reserved this ticket (B-b):

> B-b, la journée propose une vrai quête, que j'approuve et je choisi a qui
> est le donneur de quest. le client devra maintenant trouver qui peux lui
> proposé la quête.

In this planning conversation (2026-10-13):

> Ouverture du ticket 0121. Le ticket 0115 est fini et mergé.

> A j'aimerais qu'on y réfléchisse un peu plus. Mon objectif est d'avoir la
> meilleur expérience possible. Selon moi, l'expérience de jeu sera meilleur
> si on utilise l'outil de quest pour la gestion de ce qui a des conditions.
> L'outil de plan peut servir (mais je suis ouverte a le décommissionné ou le
> revoir, au besoin) pour faire un plan plus global. Je pense que cela ne sert
> a rien de tirer des dées pour savoir si le joueur a trouver une piste. A la
> limite oui, mais cela ajoute seulement une étape a a quest. récolter les
> bonnes informations. B1, C1, D1 et je veux que la condition de réactivation
> D2 soit suivi. E1 et on ajoute E3 que je coche si c'est une quête unique.
> F1, G1, H selon moi, pour que le créateur de quests soit performant et
> autosifisant, il doit pouvoir aller fouiller dans tous le lore, même si ce
> n'est pas connus du monde entier. Le joueur peut vouloir obtenir
> l'information connus de quelques personnes spécifique dans un autre pays et
> une quest doit être créer ( on s'entend, cela ne sera pas facile) pour que
> le joueur puisse finir par trouver l'information. Aussi, si le joueur
> interoge sur un sujet qui n'existe pas encore ( ex : les dragons-zombies)
> Je veux qu'en temps que créateur, on me demande si c'Est quelque chose que
> je veux qui existe. Je peux répondre oui avec quelques clarifications (on
> est un peu dans l'outils de lore ici; on réutilise?) les bon faits sont
> créer, puis la quête peut être créer a partir de tout cela. ou je dit non
> et il n'y a pas de création de Dragon-zombi, le joueur est envoyé sur une
> quest pour apprendre que cela n'existe pas et pourquoi.

> K1, J je ne comprend pas. Le joueur a déja fait ca déclaration a ce moment
> là non ? sa déclaration est qu'il cherche de l'information sur X ou qu'il
> veut faire Y, mais qu'il n'a pas les pré-requis. Donc cela n'a pas le choix
> de '' dépensé sa déclaration''. L1, N1, E3a, P1, H2. Ok pour les enjeu. Je
> suis a l'aise avec beaucoup d'appels aux modèle et avec le temps que cela
> prend répondre. Ok pour me faire avertir pour un fait que personne ne sais.

> K1b-oui, J2-a1 mais on ne dit pas une piste se prépare. Pourquoi le joueur
> a besoin de savoir ce que je fais en arrière? on lui donne la narration
> qu'il cherche des informations, il devra continuer a chercher pour trouver
> l'information qu'il cherche.

> S2 avec rapport suivi de S3, R1, T1

> U1 puisque je veux que certains savoir que je considère ''normal ou que
> tous le monde peut aquérir facielement'' puissent obtenir leur rumeur. V1.

## Clarifications resolved (intake)

- **What a quest is for.** Anything that has conditions goes through the
  quest tool; the day plan keeps a day's activities and advancing an
  accepted quest (O1 of 0108). Finding a lead is not rolled: if gathering
  information should cost something, it is a step of the quest.
- **The day of the declaration is spent** (J2). When the declaration is
  routed to a quest, the day narrates the character searching and nothing
  more: the narrator reads the declaration only, never the request, never
  the lore the designer searched; the player is not told a quest is being
  prepared (J2-a1).
- **The designer runs on the creator's side**, when she presses
  « Concevoir » on the request: the cockpit has no background job, and the
  player's day never waits on it.
- **Production.** The migration is additive (one new table); no data is
  written.

## Decisions locked (do not re-litigate without Nia)

- **K1** -- the plan selection's one call gains a third answer: a quest.
  It runs on every declaration, no open plan included.
- **K1b** -- a step blocked on an unmet prerequisite opens a quest request
  too, its subject what was missing.
- **R1** -- a knowledge the planner cannot anchor (unknown, or held only in
  secret) stops the plan at that step: it becomes the day's inquiry step,
  and a request is opened.
- **J2 / J2-a1 / T1** -- the declaration is spent; a routed day is a
  one-step plan « Se renseigner : ... », no roll, a fifth band `inquiry`
  that proposes nothing and closes its step directly, narrated as a search.
- **B1** -- the offer is a `quest_offer_creation` proposal; its review card
  is the offer editor itself; approving saves the offer; the review is
  recorded (A3 of 0115).
- **C1** -- the designer writes the trees in the interpreter's answer form,
  read by the interpreter's own reader, one retry carrying the errors; a
  condition it cannot settle waits in the card as an interpreter proposal.
- **D1** -- up to three suggested givers among existing characters and
  factions; the creator picks any; no character is created.
- D2 (an invented giver; reactivation: the creator often creates a character just to give a proposed offer) -- followed by the « Demandes de quête » metric.
- **E1** -- picking the giver adds « the character has met the giver » to
  the eligibility (the contact for a faction), removable.
- **E3a** -- a new form `is_character`; « Quête unique » ticked adds it to
  the eligibility (offered to this character only); distinct from
  « répétable ».
- **F1** -- the designer proposes the costs and rewards, all five
  currencies; an unresolved one is dropped with a note.
- **G1** -- it may propose the event types, sortes and states it lacks,
  created from their cards as in the interpreter.
- **H2** -- it searches the whole lore, secrets and creator-only facts
  included; INV-01 names it among the creator-regime readers.
- **V1** -- a player-visible field (title, summary, objective) that repeats
  four consecutive words of a secret fact it read is flagged; approval
  requires « Je confirme » (INV-63). A paraphrase passes: the creator's
  review remains the last barrier for prose.
- **L1** -- a relational `quest_request` holds each request and its state.
- **N1** -- the existence question: « exists » or « does not exist », each
  with her text, opens the Lore writing panel pre-filled; its commit links
  the entry to the request; « the lore already says it » names the entity
  and designs again.
- **S2** -- a fourth Lore selector, `facts_mentioning`, finds the facts whose
  text holds the subject's words; the consultation can use it too.
- S3 (a search by meaning; reactivation: requests the creator answers « the lore already says it ») -- followed by the « Demandes de quête » metric.
- **P1** -- the plan tool is unchanged in 0121; P1 (the plan tool reworked; reactivation: the share of days routed to a quest asks for it) -- followed by the « Demandes de quête » metric.
- **U1** -- a blocked step still proposes its rumor-level lead (D3 of 0078)
  beside the request: some knowledge is meant to be easy to get; the
  creator chooses at review.
- **Warned, never invented** -- a fact found that no one knows is a note on
  the proposal.

## Drafting decisions (made in the lot; Nia may reverse before execution)

1. The steps of a plan after its inquiry step (R1) are not written: pursuing
   them is the quest. The `/plan` answer reports how many were cut.
2. A request opens only from a NEW plan (`_finalize_plan`: a fresh plan or a
   « replace »); a blocked step met again by « continue » or « modify »
   already has its request from when it was written.
3. One request per step (unique), and the designer's condition drafts carry
   the request's id as their `attempt_id`, so the dashboard can tell them
   from the creator's own interpreter use.
4. The designer's two prompts are `quest_subject` (frames the subject: words
   and names) and `quest_design` (writes the offer); both on the authoring
   model, editable in Prompts.
5. Each condition of the designer's answer carries its own `define` blocks
   (the interpreter's answer, unchanged): a type proposed by two conditions
   shows two cards; creating it from the first makes it the near choice of
   the second.
6. The lore the designer reads: the facts naming the subject's words, then
   the facts of every entity it names (matched names only), then the facts
   of the Lore entry the creator wrote for it.
7. « Secret » for V1: a creator-only fact, or a fact no entity holds on a
   non-secret row.
8. A request whose proposal was rejected can be designed again; a request
   is never deleted, only set aside (`dropped`).
9. « Demandes de quête » sits above the review queue's cards, not in a new
   Création tab.
10. The approved offer is `open`, not repeatable; the card lets her change
    both.

## Carried forward / open

- **D2, S3, P1** -- deferred, each watched by the « Demandes de quête »
  metric in « Suivi ».
- **The `modify` and `continue` paths** opening requests for a step that
  becomes blocked later: not in 0121 (drafting decision 2); reopen if the
  creator meets a blocked step with no request.
- **The interpreter metric and the designer's drafts** (AMENDMENT-0121-01): « Interprète de conditions » counts the designer's drafts too; separate them by `attempt_id` (a `quest_request.id`).
- **TICKET-0116** (rank trials) and **TICKET-0120** (calendar) follow, in
  that order (J1, A2 of 0114, G1 of 0115).

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `is_character` in every home of the vocabulary  -> verify/checks/character_form.py
- [ ] v2.28 stores a request; the writer, the cascade, the metric, the deferrals  -> verify/checks/quest_requests.py
- [ ] `facts_mentioning` and the designer's lore gathering  -> verify/checks/lore_facts_mentioning.py
- [ ] The selection routes; blocked and unanchored steps open requests; the inquiry band  -> verify/checks/journee_inquiry.py
- [ ] The designer, its proposal, the applier and the prose guard (INV-63)  -> verify/checks/quest_designer.py
- [ ] The review card edits a proposed offer in the offer editor  -> verify/checks/quest_review_card.py
- [ ] « Demandes de quête », the existence question, the Lore hand-off  -> verify/checks/quest_request_panel.py
- [ ] Every check of the corpus  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After a backup, `migrate_v2_28_quest_requests.py` on a copy of the
      production database, then on production: « Migration v2.28 applied »;
      `apply_ticket_0121_select_prompt.py` and
      `apply_ticket_0121_designer_prompts.py`; the cockpit boots.
- [ ] Journée: « Je cherche qui connaît le secret de l'acier noir » -- the
      day narrates a search, no dice, no « piste » announced; « Demandes de
      quête » shows the request.
- [ ] Journée: a plan whose second step needs to have met someone the
      character has not met -- the first step plays, the second is blocked;
      a request appears beside the blocked step's usual proposals.
- [ ] « Concevoir » on a subject the lore holds (a secret known by one
      character far away): a proposal in the queue -- giver suggestions, the
      steps lead to that character, the secret fact is a condition, never
      written in the objectives; a flagged field requires « Je confirme ».
- [ ] « Concevoir » on « les dragons-zombies »: the existence question.
      « Elle n'existe pas » with a reason -> Lore « Écrire » opens pre-filled;
      commit -> the designer proposes a quest to learn that they do not exist
      and why.
- [ ] In the card: pick a giver (the eligibility gains « a rencontré »),
      tick « Quête unique », approve. Journée lists the offer only once the
      character has met the giver, and only for him.
- [ ] « Suivi » shows « Demandes de quête »: origins, existence answers,
      approved offers.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
| AMENDMENT-0121-01 | none (after E, before F) | E: drafts marked beyond the approved payload; `SUBJECT_FIELD` evading K3; `knowers_note` unused; pending conditions also cover proposed definitions; commit 2 unreviewed | none (F and G unchanged) |

## Escalations

### E-01 — D1-d — G

**Context:**
/pipeline TICKET-0121 ran BRIEF-0121-G (commit e03f761; quest_request_panel RP1-RP4 PASS, its named mutations red then reverted, frontend_build_fresh / module_budget / creation_island / effect_self_write / lore_isolation / lore_write PASS). /verify then ran red; verdict tooling/verify/results/TICKET-0121-journee-quest-designer.json: "corpus_gate.py FAIL -- SUMMARY: 9 check(s) failed (0 environment, 0 crash, 0 timeout, 9 other)". Every ticket-linked check passes; the 9 are corpus checks, verbatim:
- attribute_interpreter.py: "AE1: QuestOffers.svelte lacks unsaved={draft.unsavedAttributes}"; "AE1: QuestOffers.svelte does not pass the unsaved attributes to its four conditions"
- condition_interpreter.py: "NE1: QuestOffers.svelte does not pass role='eligibility'|'prerequisite'|'completion' to one ConditionEditor"
- conditions.py: "CD1: QuestOffers.svelte lacks '<ConditionEditor cond={draft.eligibility}'" (and step.prerequisite, step.completion)
- debts.py: "DC3: QuestOffers.svelte lacks choices?.members?.[draft.giver_entity_id]"; "DC3: QuestOffers.svelte lacks draft.contact_entity_id = ''"
- event_conditions.py: "EE6: QuestOffers.svelte lacks 'role=\"failure\"'"
- quest_rewards.py: "RD2: QuestOffers.svelte renders no QuestTermRow"
- function_length.py: "src/world_engine/cockpit/day_plan_finalize.py::_finalize_plan is 95 lines (> 80) and not present in function_length.json"; "src/world_engine/lore_query.py::execute_plan is 81 lines (> 80) and not present in function_length.json"
- name_index.py: "R5 src/world_engine/quest_designer.py:27 uses the creator name regime outside its allow-list"; "R5 src/world_engine/quest_lore.py:22 uses the creator name regime outside its allow-list"
- lore_usage.py: "U12c: --since 2026-10-14 exit 0, 8 line(s)"
Origins: the six QuestOffers.svelte pins are BRIEF-0121-F's pure move of the editor into OfferEditor.svelte (F's Scope IN retargeted none of them); function_length comes from D's move of _finalize_plan out of routes/day.py and C's execute_plan growth; name_index R5 from C (quest_lore.py) and E (quest_designer.py) -- CLAUDE.md INV-01 was amended to name the quest designer but name_index.py's CREATOR_ALLOWED was not; lore_usage U12c is TICKET-0123's (AMENDMENT-0121-01 Scope OUT; its U12f fix is on ticket/0123, itself escalated E-01). No failure touches a file of BRIEF-0121-G, so the V1 retry has no fix inside G's Scope IN: it was not attempted (retry_count stays 0); a re-run unchanged would be the second consecutive failure.

**Question:**
How should the 9 corpus failures, none of them inside BRIEF-0121-G's scope, be resolved before TICKET-0121 can open its PR?

**Options:**
(a) Authorize a fix-up commit on ticket/0121 now: retarget the six QuestOffers.svelte pins to OfferEditor.svelte (same patterns, the file F moved them to), add quest_designer.py and quest_lore.py to name_index.py's CREATOR_ALLOWED (matching the amended INV-01), and record _finalize_plan and execute_plan in the function_length baseline -- then re-verify; lore_usage U12c stays red until TICKET-0123 lands, and the PR opens with it noted.
(b) As (a), but split the two long functions instead of baselining them.
(c) Write an amendment (AMENDMENT-0121-02) in the chat with the exact retargets and allow-list entries; this session stops.
(d) Something else.

**Response:**
