---
id: TICKET-0119
title: What happens in the world, proposed by every producer -- a type's effects on the state of the world, the tick's and Journée's typed events, Lore declaring events, one event editor
type: feature
status: live-gate
created: 2026-10-12
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: large
lot_id: LOT-0119-event-producers.md
brief_ids: [A, B, C, D, E, F, G]
current_brief:
schema_version_touched: v2.26
retry_count: 0
slug: event-producers
---

## Request (verbatim, as Nia stated it)

The series request is TICKET-0111's (`tooling/tickets/TICKET-0111-condition-language.md`,
« Request »); TICKET-0114 cut this ticket off (A2: « 0119 juste après 0114,
avant 0115 »: the Journée and tick producers, M-c, U1, Y2).

In this planning conversation (2026-10-12):

> Je viens de finir le ticket 0114, mergé. on fait le ticket 0119.

After the RECON and the decision blocks:

> A1, B Je veux absolument que mes journée puisse créer des types. je veux
> que la journée me propose une résolution au prompt du joueur. Une des
> réponses probable pour moi est l'ouverture d'une quest. Si je joueur
> cherche quelque chose par exemple, Est-ce qu'il a ce qu'il faut pour
> trouver ce qu'il cherche. c'est exactement le modèle d'une quête. Pour que
> cela soit possible, je pense que le producteur de journée doit absolument
> pouvoir créer des types. C1 j'aimerais que tu me donne des exemples un peu
> plus détaillé ( au moins 2 différentes). D explique avec un exemple. E
> explique avec des exemples sur ce que cela donne.F1, G un mélange des
> deux, je veux G1, mais j'ai un bouton qui me permet de déclaré un
> évènement spécifiquement. . H1.

> B-b, la journée propose une vrai quête, que j'approuve et je choisi a qui
> est le donneur de quest. le client devra maintenant trouver qui peux lui
> proposé la quête. Bt1, C point 4: est-ce que c'est quelque chose que je
> vais pouvoir réglé plus tard? D3, E1. pour le détail : plus tard, si je
> crée une table d'historique cela sera correct? planificateur ticket 0121.

## Clarifications resolved (intake)

- **The cut (Bt1).** 0119 holds a type's effects, the tick's typed events,
  Journée's objective events (deterministic), Lore declaring events and one
  event editor. Journée proposing a QUEST from the player's day (B-b: a real
  offer the creator approves, choosing its giver; the planner writing
  full-language objectives and proposing types) is TICKET-0121.
- **Effects on a sorte (C, point 4).** An effect on a role a sorte fills
  changes nothing today; it can be settled later without undoing anything
  (an effect names a role, the rule is one place in the writer).
- **A history table for the vital state and the status (E).** Correct to add
  later; from this ticket on, an approved proposal keeps the before and
  after of every system state its event changed (`applied_changes`), so a
  later table can recover them.
- **Production.** The migration is additive (one new table, one new column,
  one CHECK widened by a rebuild of `lore_entry_row`, every row copied); no
  data is written.

## Decisions locked (do not re-litigate without Nia)

- **A1** -- the tick names the world's types by code and its participants by
  role and name; it never proposes a new type (an item naming none keeps the
  untyped shape, typed by its domain at approval). Reactivation: the
  dashboard (0115) shows the creator retyping the tick's domain-typed events
  often.
- **B-b** (TICKET-0121) -- Journée proposes a real quest offer, approved by
  the creator, who picks its giver; the character then finds who can offer
  it. Rejected: B-a (the day plan becoming a giverless personal quest).
- **Bt1** -- 0119 keeps the deterministic Journée producer: a completed step
  whose objective is an event proposes that event; the planner is 0121.
- **C1** -- a type declares its effects as data: « role -> state = value »,
  the value a choice, an integer, or another role's entity.
- **D3** -- an integer effect sets or adds; each effect says which.
- **E1** -- an effect may change `État vital` and `Statut` (never `Magie`);
  their columns keep no history table (a later one is correct; the approved
  proposals keep before and after).
- **F1** -- an event's changes are written all or none.
- **G3** -- Lore declares events in the writing panel's proposal (G1) and by
  a button straight to the journal (G2).
- **H1** -- one event editor for the review card, Lore and the journal.
- **M-c** (TICKET-0114) -- the proposal carries the event and its changes,
  reviewed together; `attribute_change` names its event; a type's effects
  pre-fill.
- **Y2** (TICKET-0114) -- the review card edits an event proposal.

## Drafting decisions (made in the lot; Nia may reverse before execution)

1. **A:** an effect names a role that holds an entity; a role accepting only
   sortes takes none (refused), and a sorte filling a role changes nothing.
2. **A:** a definition an effect names cannot be retired, change its kind, or
   lose the choice the effect names (the WJ2 rule, extended).
3. **C:** an event may change any entity of the world, not only its
   participants (the creator adds what the type does not pre-fill).
4. **C:** a location is never made `active` again by an event (its fiche
   asks about a zone promotion); a character leaving `alive`, like an entity
   leaving `active`, leaves its gatherings.
5. **C:** the before and after of a system state live in the approved
   proposal (`applied_changes`); a Lore or journal event keeps only its event
   and fact as the reason.
6. **D:** a review card may change the event's type (participants kept by
   role name); a proposed type (I2) keeps its definition as proposed.
7. **D:** an untyped proposal keeps its raw payload on the card.
8. **E:** the tick may name a sorte the world lacks (created at approval, as
   Play's).
9. **F:** the event a step proposes carries what the leaf still lacks in its
   window (« 3 loups », one already counted: 2); its title is the step's
   objective and the day's number (the duplicate guard compares titles).
10. **G:** a sorte the world lacks drops the participant with a note in
    Lore (create it in « Vocabulaire du monde »); a proposed type is created
    from its card before the commit, never by the commit.
11. **G:** Lore's event card lists the statement's entities only; « Déclarer
    un événement » lists the world's and writes no lore entry.

## Carried forward / open

- **TICKET-0121** (next): Journée proposes a quest offer from the player's
  day (B-b): the planner writes prerequisites, objectives and failures in the
  full language and proposes the types, sortes and states it needs; the
  creator approves and picks the giver.
- **Effects on a sorte**: a state held by a sorte (« les loups de Brume sont
  enragés »). Reactivation: a type whose effect targets a role that accepts a
  sorte, and the creator asking for it.
- **History of the vital state and the status**: a table; it can recover
  every change an event made since 0119 from `applied_changes`.
- **0115** (dashboard): the acceptance rate of the tick's typed proposals,
  of Journée's objective events, of Lore's events; how often the creator
  edits a pre-filled change.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] A type's effects, v2.26  -> verify/checks/event_effects.py
- [ ] An event writes its changes, all or none  -> verify/checks/event_changes.py
- [ ] One event editor; the review card  -> verify/checks/event_editor.py
- [ ] The tick's typed events  -> verify/checks/event_tick.py
- [ ] Journée's objective events  -> verify/checks/event_day.py
- [ ] Lore declares events  -> verify/checks/event_lore.py
- [ ] Every check of the corpus  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After a backup, `migrate_v2_26_event_effects.py` on a copy of the
      production database, then on production: « Migration v2.26 applied »;
      the cockpit boots.
- [ ] `apply_ticket_0119_tick_prompt.py` and
      `apply_ticket_0119_lore_prompt.py`: each « v1 -> v2 » (or one version
      up), no « fragment not found ».
- [ ] « Vocabulaire du monde »: a type « Ouvrir » with the effect « Cible ->
      Ouvert = oui » is saved and reopened as saved.
- [ ] The journal: a new « Ouvrir » event on a door, « Pré-remplir depuis le
      type », saved: the door's sheet shows « Ouvert : oui », its history a
      change.
- [ ] Play or the tick proposes a typed event: its card shows the editor,
      edited and approved, the event is written as edited.
- [ ] Journée: a quest step whose objective is an event, completed, proposes
      that event beside the step change.
- [ ] Lore: a statement declaring something that happened proposes an event;
      written, it appears in the journal and in the entry's history;
      « Déclarer un événement » writes one straight to the journal.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
