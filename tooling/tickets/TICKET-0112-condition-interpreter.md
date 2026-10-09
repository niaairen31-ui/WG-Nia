---
id: TICKET-0112
title: The condition interpreter -- a sentence in French becomes a condition tree the creator confirms, journaled for its acceptance rate
type: feature
status: live-gate
created: 2026-10-09
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: medium
lot_id: LOT-0112-condition-interpreter.md
brief_ids: [A, B, C, D, E]
current_brief:
schema_version_touched: v2.21
retry_count: 0
slug: condition-interpreter
---

## Request (verbatim, as Nia stated it)

The series request is TICKET-0111's (`tooling/tickets/TICKET-0111-condition-language.md`,
« Request »): « Est-ce qu'on pourrait gérer toute les conditions comme des
requêtes SQL mais en langage naturellle et il y a un interprête qui écrit la
requête, je confirme et ça devien ma condition, je pourrais dire; le joueur
apporte 15 fourrures de loup? » -- « La limite est seulement l'imaginaire de
la personne qui crée le monde. » -- « Je ne veux pas que tu considère le
modèle 8b comme une limite, je veux que tu considère ce que peux faire un
LLM plus gros. » Its order J1 puts this ticket second: 0111 the language,
0112 the interpreter.

The handover of TICKET-0112 (2026-10-08) states what she wants, in her
words summarized: write a condition in natural language, an interpreter
translates it, she confirms, it becomes her condition; a self-sufficient
generator, no ticket per new form; design for a bigger model than the 8B.

In this planning conversation (2026-10-09), after the RECON and the
decision blocks:

> IA1, IB1, IC1, ID ils ne sont pas dans name_index pour le moement, mais
> est-ce que l'on ne crée ppas une deuxième structure qui fait quelque chose
> de similaire, mais pas vraiment juste pour ne pas changer comment
> fonctionne Name_index. Est-ce que ca vaut la peine d'ajouter
> competence_index, Quest_index... IE1, IF1, IG1, IH1, II1, IJ ok, IK1.

Then, after the ID block was restated in three variants:

> ID1a

## Clarifications resolved (intake)

- **Why not `name_index` for offers and skills (her question on ID).** A
  name surface is an entity's: it carries an `entity_id` and an
  `entity_type` (`name_index.py:65-71`), and eight modules import it --
  among them the tokenizer, which turns every surface it finds in a text
  into an identity token `[[e:<uuid>|nom]]`, and the day concordance,
  which matches a player's words against it. An offer or a skill there
  would become an entity token in prose and a match for a player's
  sentence. A `quest_index` or `skill_index` would be a second structure
  for a job that is not name resolution: the sets are small and shown
  whole, the model picks, code checks the pick was shown. That is what
  `fact_refs.code_facts` already does for facts; ID1a generalizes it.
- **What the handover's budget figure meant.** « 37 839 sur 38 000 » is
  `CLAUDE.md`'s size in bytes; `claude_md_contract.py` counts characters
  (`len(text)`), and `main` holds 37 180 -- 820 left (R-22).
- **No new write path.** The offer editor already confirms: an inserted
  proposal lands in the editor's draft and only « Enregistrer » writes it,
  through `routes/quests.py` and `clean_condition` (R-14). The interpreter
  writes no condition; its journal is a non-canon table.

## Decisions locked (do not re-litigate without Nia)

- **IA1** -- conditions only, in their three roles (eligibility,
  prerequisite, completion). A cost or a reward the sentence names is
  listed as unsupported and shown « ajoute-le dans Coûts / Récompenses »;
  never translated into a condition (« apporte » is a cost, « possède » an
  `item_held`). Rejected: IA2 (terms too: a second judge; reactivation: the
  journal shows the creator typing costs into the interpreter), IA3 (a
  whole offer from one sentence, after IA2).
- **IB1** -- « Écrire en langage naturel » under each `ConditionEditor` of
  the offer editor; the proposal is inserted into the draft, « Enregistrer »
  writes. Rejected: IB2 (a panel in the Lore shell: detached from the offer,
  a third reopening of 0085's read-only lock).
- **IC1** -- editing: the model receives the current tree in its own form
  (entities by an `e` code, other targets by code) with the instruction,
  and answers the whole tree. Rejected: IC2 (always rewrite from a full
  sentence).
- **ID1a** -- one coded list: `fact_refs.CodedFacts` becomes `CodedRefs`,
  built by `code_refs(prefix, pairs)`; facts `f`, quest offers `q`, skills
  `s`. Entities by name through `name_index` (creator regime); an ambiguity
  goes up with its candidates, the tool never picks (0092). Rejected: ID1b
  (offers and skills in `name_index`; reactivation: a quest offer becomes
  an entity), ID1c (a `quest_index` and a `skill_index`).
- **IE1** -- the model sees the language, the entities the sentence names,
  and coded lists: the current tree's facts, then the named entities'
  facts, then the world-level facts, creator-only facts included, capped
  at `MAX_CODED_FACTS`; every offer; the base domains and the world's
  skills. Rejected: IE2 (creator-only facts hidden; no condition on a
  secret through the interpreter).
- **IF1** -- the expressible part is proposed; what the forms cannot say
  yet is listed, each with where it will come from (state -> TICKET-0113,
  event -> TICKET-0114, time -> no ticket yet). Rejected: IF2 (all or
  nothing).
- **IG1** -- confirmation by the French lines (`describe`) and the notes;
  « insérer dans l'offre » or « écarter / reformuler ». Rejected for now:
  IG2 (a dry-run verdict on a chosen character; reactivation: a dry-run
  evaluation is asked for elsewhere).
- **IH1** -- a journal of its own, `condition_draft` (v2.21): one row per
  proposal, `outcome` moving `proposed` / `needs_choice` / `refused` /
  `unavailable` / `parse_error` -> `inserted` / `discarded` -> `saved`, with
  `offer_ref` and `saved_as_proposed`; no `world_id`, no FK (I1 of 0103).
  The acceptance rate (D1) is a query on relational columns. Rejected: IH2
  (a new `kind` in `lore_usage_event`: a rebuild of its CHECKs, the rate
  inside JSON), IH3 (an export only: D1 not measurable).
- **II1** -- every leaf validated on its own, every error kept; the model is
  asked once more with the errors when code refused its answer for anything
  but an unknown name; a second refusal shows the errors, nothing
  insertable. Rejected: II2 (no second call).
- **IJ1** -- default model `AUTHOR_MODEL`, overridable per prompt in the
  prompts panel (`effective_model`); Ollama down -> a deterministic message,
  the sentence kept, nothing inserted (K1 of 0098).
- **IK1** -- five sequential briefs: A the coded list and the shared JSON
  call (pure refactors), B the journal (v2.21), C the interpreter module and
  its prompt, D the routes and the save marking, E the editor.

## Carried forward / open

- **Costs and rewards from a sentence (IA2), then a whole offer (IA3).**
  Reactivation: the journal's `instruction` column shows costs typed into
  the interpreter (a query on `condition_draft` whose notes name « Coûts »).
  Its own ticket.
- **A dry-run verdict in the confirmation (IG2).** Reactivation: a dry-run
  evaluation is asked for on another surface. Its own ticket.
- **States, events and time in the language.** TICKET-0113 (attributes),
  TICKET-0114 (event journal); time has no ticket. The interpreter's notes
  already name them; the prompt's form lines grow with `REQUIREMENT_TYPES`
  (NC1 keeps them equal).
- **The acceptance-rate dashboard (D1, H1).** TICKET-0115 reads
  `condition_draft.outcome` and `saved_as_proposed`.
- **Offers as entities.** Would move offers into `name_index` (ID1b's
  reactivation) and retire the `q` list.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] One coded list names facts, offers and skills; one templated JSON call serves Lore and the interpreter (NA1, NA2)  -> verify/checks/condition_interpreter.py
- [ ] `condition_draft` (v2.21) has its contract's columns, CHECKs and moves; its writer refuses every malformed record; the migration refuses below v2.20 and is idempotent (NB1-NB3)  -> verify/checks/condition_interpreter.py
- [ ] The interpreter reads the model's answer back through codes and names, validates every leaf, retries once on a fixable error, leaves an ambiguous name to the creator, lists what it cannot say, and writes nothing (NC1-NC4)  -> verify/checks/condition_interpreter.py
- [ ] The routes journal every proposal that reached the model, move it on a pick and a decision; saving the offer marks an inserted proposal saved, as proposed or changed (ND1-ND3)  -> verify/checks/condition_interpreter.py
- [ ] The offer editor shows the interpreter under each condition and sends the inserted proposal's id (NE1)  -> verify/checks/condition_interpreter.py
- [ ] The language and the offer API still hold  -> verify/checks/conditions.py
- [ ] Lore writing still journals and stubs through its own `chat`  -> verify/checks/lore_write.py
- [ ] The full corpus is green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] With Ollama running and the migration applied (`python scripts/migrate_v2_21_condition_draft.py`, then `python scripts/apply_ticket_0112_condition_prompt.py`), in Création -> Quêtes, under « Proposée à qui remplit », « le joueur possède 15 fourrures de loup ou est membre de la Guilde » is proposed as « Au moins une de ces conditions : … », inserted, saved; the offer reloads with that nested condition.
- [ ] « le joueur apporte 15 fourrures » proposes no condition and says to add it in « Coûts ».
- [ ] On a flat condition already in the list, « ajoute : ou s'il a rencontré <PNJ> » returns the whole tree with the addition.
- [ ] A name two characters carry asks which one, and the pick is used.
- [ ] With Ollama stopped, the explicit message shows, the sentence stays, the offer is unchanged.
- [ ] Choosing Gemma 4 12B or the 14B for `condition_interpret` in Prompts changes the model used, without a ticket.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
