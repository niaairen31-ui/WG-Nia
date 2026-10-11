---
id: TICKET-0113
title: The state of the world -- attributes a creator defines, one value per entity with its history, read by one condition form and proposed by the interpreter
type: feature
status: live-gate
created: 2026-10-10
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: large
lot_id: LOT-0113-world-state.md
brief_ids: [A, B, C, D, E]
current_brief:
schema_version_touched: v2.23
retry_count: 0
slug: world-state
---

## Request (verbatim, as Nia stated it)

The series request is TICKET-0111's (`tooling/tickets/TICKET-0111-condition-language.md`,
« Request »); the series document (`SERIE-conditions.md`, project doc) puts
this ticket third: 0111 the language, 0112 the interpreter, 0113 the state
of the world (B1, G1).

In this planning conversation (2026-10-10):

> Nous somme rendu au ticket 0113 (ticket 0112 mergé) de la série de
> conditions, lis le document, fait un recon, lis le document dans le
> contexte correspondant et porpose moi tes choix.

After the RECON and the decision blocks:

> WA3, WB2, WC1, WD1, WE1, WF1, WG1, WH1, WI1, WJ2, WK2, WL1, WM1, avec ces
> précisions :
> * WK2 : A1 de la série l'a déjà tranché. Quand un état manque, l'interprète
>   propose de le créer (« l'événement repéré n'existe pas dans ce monde, le
>   créer ? »). Je ne veux pas quitter l'interprète pour aller créer une
>   définition dans un autre onglet. La proposition contient la définition
>   (nom, type de valeur, valeurs, types d'entités, valeur par défaut, caché
>   ou non) et la condition. Je confirme les deux ensemble, et le code les
>   écrit dans une seule transaction par les mêmes écrivains, avec la même
>   validation. Un nom de définition proposé qui ressemble à une définition
>   existante doit me proposer celle-ci (pas de doublon « Maudit » /
>   « maudite »).
> * WB2 : une définition s'applique aux types que je coche, et l'interprète
>   les propose. Je ne veux pas créer « Maudit » trois fois.
> * WA3 : choix, nombre entier et référence d'entité. « Le trône est occupé
>   par Ysa » (ma condition nº 40) doit être exprimable, et aucune forme ne
>   lit une relation structurelle.
> * WD1 : chaque ligne d'historique porte « correction » ou « changement »,
>   comme les faits depuis 0105 (G1, H1). Je choisis à chaque modification.
> * WE1 : mesure d'abord les feuilles `vital_status` de `condition_node` en
>   prod avant de figer la migration.
> * WH1 : « caché » est décoché par défaut.
> * WL1 : écris dans le ticket que l'injection des états non cachés dans le
>   contexte du MJ est le premier point de 0114. Avec WK2, ajuste le brief D
>   (interprète) et dis-moi si le découpage WM1 change.

Then, after WK2's consequence on the cut was restated as WN1 / WN2:

> WN2, pour la claude.md, je viens de faire un ticket pour faire le ménage
> (ticket 0117 mergé).

## Clarifications resolved (intake)

- **WE1's measurement.** On a read-only copy of Nia's production database
  (2026-10-10, `condition_node` at v2.21): zero leaves of form
  `vital_status`. The migration still converts them (a database restored
  from an older backup may hold some) and refuses a leaf it cannot convert;
  on production it converts nothing.
- **Where the system attributes live (WE1).** `character.vital_status`,
  `entity.status` and `location.magic_status` stay in their columns (G3 of
  the series: one state in two places diverges); the attribute layer reads
  them in place, under the keys `sys:vital_status`, `sys:status`,
  `sys:magic_status`, and never writes them. They keep their own fields on
  the sheet.
- **WK2 and the cut (WM1 -> WN2).** WK2 makes the interpreter propose a
  definition with its condition. WN2 decides where the proposal waits: in
  the offer's draft, written by the offer's « Enregistrer » in the same
  transaction as the conditions, by `write_attribute_definition` and
  `write_condition`, validated by `clean_definition` and `clean_leaf`. The
  cut stays five briefs; D is split: D teaches the interpreter to read the
  world's attributes, E to propose a missing one (WN2).
- **CLAUDE.md's budget.** TICKET-0117 restructured it; this ticket adds one
  invariant, INV-62 (B), within the budget `claude_md_contract.py` checks.

## Decisions locked (do not re-litigate without Nia)

- **WA3** -- three kinds of value: `choice` (labels, one default),
  `integer` (an integer default), `entity` (another entity, of the value
  types the definition names). « Le trône est occupé par Ysa » is an
  `entity` attribute; no form reads a structural relation. Rejected: WA1
  (choice and integer only), WA2 (choice only).
- **WB2** -- a definition applies to the entity types the creator checks
  (`attribute_definition_type`, side `holder`; an `entity` kind's value
  types, side `value`); the interpreter proposes them. Rejected: WB1 (one
  type per definition: « Maudit » three times), WB3 (every type).
- **WC1** -- an entity holding no value reads the definition's default;
  nothing is written on read. Rejected: WC2 (a value written for every
  entity at definition), WC3 (no value reads unknown).
- **WD1** -- the history is relational and append-only
  (`attribute_change`): each row the value before and after, and
  `correction` or `changement`, chosen by the creator at every change,
  never preselected (as facts since TICKET-0105, G1/H1). Rejected: WD2 (a
  JSON history), WD3 (the history alone).
- **WE1** -- the three canon states are system attributes read in place;
  the form `vital_status` is retired, its leaves converted to `attribute`
  leaves on `sys:vital_status` (zero in production, measured). Rejected:
  WE2 (the `vital_status` form kept beside), WE3 (no system attribute).
- **WF1** -- `item.condition` is untouched: an item's wear is not a state
  of this ticket.
- **WG1** -- one condition form, `attribute`, on any entity the attribute
  applies to; a choice by label, an integer by threshold (« N or more »),
  an entity by entity (or anyone). Rejected: WG2 (two forms).
- **WH1** -- `is_hidden`, off by default: a hidden attribute is never
  written out to a player, even about his own character (INV-62).
  Rejected: WH2, WH3 (reactivation: TICKET-0114's journal knows who
  witnessed a change).
- **WI1** -- Création › États lists and writes definitions; every saved
  entity's sheet carries an « États » panel (values, history). Rejected:
  WI2 (definitions from the sheet only).
- **WJ2** -- nothing in use is taken away: a kind, a type or a label a
  value or a condition holds is kept; a label is retired, never deleted; a
  definition is retired -- refused while a condition names it -- and can be
  restored. Rejected: WJ1, WJ3.
- **WK2** -- when a state is missing, the interpreter proposes its
  definition with the condition (name, kind, labels, types, default,
  hidden); the creator confirms both together; a name near an existing
  attribute's offers that one, never a silent duplicate (« Maudit » /
  « maudite »); in Création too, a near name is confirmed before it is
  written. Rejected: WK1 (send her to États).
- **WL1** -- no assembler reads attributes in this ticket. **The MJ
  context's injection of the non-hidden states is the first point of
  TICKET-0114.**
- **WM1** -- five sequential briefs: A the store (v2.22), B the condition
  form (v2.23), C Création, D the interpreter reads the states, E the
  interpreter proposes a missing one.
- **WN2** -- a proposed definition travels in the offer's draft
  (`unsaved_attributes`, keys `new:<ref>`) and is written by the offer's
  save, in its transaction, by the same writers; a definition no condition
  names any more is not written. Rejected: WN1 (« Insérer » writes the
  definition at once: two transactions, an abandoned offer leaving a
  definition behind).

## Carried forward / open

- **The MJ context reads the non-hidden states (WL1).** First point of
  TICKET-0114. Reactivation is the ticket itself:
  `grep -n "attribute" tooling/tickets/TICKET-0114-*.md`.
- **Who witnessed a change (WH3).** A visible attribute readable by a
  player about others needs TICKET-0114's event journal.
- **Adding a missing label to an existing attribute from the interpreter.**
  Deferred: the proposal is refused with the attribute's labels.
  Reactivation: `condition_draft` rows whose `errors` name « n'est pas un
  libellé de ».
- **`item.condition` (WF1).** Stays a column of `item`; a ticket of its own
  if wear ever becomes a condition.
- **The `magic` entity type.** A world may hold an entity type with no
  physical table behind its slug; the États panel lists it as any other
  type. Not this ticket's to clean.
- **`lore_usage.py` U12c (pre-existing, `main`).** `--since` is built from
  `date.today()` (local) against `created_at` (UTC): red between 20:00 and
  24:00 in Toronto, green otherwise. Not this ticket's; its own small
  ticket.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] v2.22 keeps a world's attributes, one value per entity, its history; the system attributes read their columns; nothing in use is taken away; the migration refuses below v2.21 and is idempotent (AA1-AA7)  -> verify/checks/attributes.py
- [ ] Création › États and the sheet panel write through the routes; a near name is confirmed; the change kind is never preselected (AC1-AC3)  -> verify/checks/attributes.py
- [ ] The `attribute` form judges any entity, unknown off its types, hidden from the player; v2.23 converts `vital_status` leaves (AB1-AB5)  -> verify/checks/attribute_conditions.py
- [ ] The interpreter reads an `a` list, writes an `attribute` leaf, reads a label back; the prompt is delivered by fragments (AD1-AD4)  -> verify/checks/attribute_interpreter.py
- [ ] A missing state is proposed with its condition, a near name picked, both written by the offer's save (AE1-AE3)  -> verify/checks/attribute_interpreter.py
- [ ] The language, the player's view and the interpreter still hold  -> verify/checks/conditions.py
- [ ] The interpreter and its journal still hold  -> verify/checks/condition_interpreter.py
- [ ] The offer API still holds  -> verify/checks/quests.py
- [ ] Deleting a world deletes its attributes  -> verify/checks/world_cascade.py
- [ ] The full corpus is green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After `python scripts/backup.py`, then `python scripts/migrate_v2_22_attributes.py`, `python scripts/migrate_v2_23_attribute_leaves.py` and `python scripts/apply_ticket_0113_condition_prompt.py` (each prints what it did; the second converts 0 leaves on production), the cockpit starts.
- [ ] Création › États lists the three system attributes, read-only; « Ouverte » (choix : non, oui ; défaut non ; lieux) is created; a new « Ouvert » then shows « Ouverte » as near and is written only on « Créer quand même »; « ouverte » is refused as a duplicate.
- [ ] « Le trône est occupé par Ysa » is expressible: an `entity` attribute « Occupé par » on a place, valued Ysa on the throne room's sheet, the change asking « correction » or « changement ».
- [ ] On a sheet, the « États » panel shows each value or « (défaut) » and its history.
- [ ] In Création › Quêtes, the interpreter turns « le Dernier Verre est ouvert » into an `attribute` condition; with no « Ouverte » defined, it proposes the definition in a card; « Insérer » then « Enregistrer » writes both, and the definition appears in États.
- [ ] With « Maudit » defined, « le personnage est maudit » uses « Maudit »; if the model proposes a new « Maudite » instead, the card offers « Utiliser « Maudit » » and « Créer « Maudite » » is a choice of its own; the tool never picks.
- [ ] Retiring an attribute a condition names is refused, with the reason.
- [ ] In Journée, a step blocked by a hidden attribute reads « quelque chose de caché l'en empêche encore », never the attribute's name.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
| AMENDMENT-0113-01 | BRIEF-0113-B | `attribute_unjudged` wrote a hidden attribute's name in an unknown leaf's reason, which player surfaces print (INV-62); `pipeline_state.py` red A-C on arrows to later checks | none (B completed by the amendment's diff; C-E unchanged) |
