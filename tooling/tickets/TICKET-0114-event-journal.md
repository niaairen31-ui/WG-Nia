---
id: TICKET-0114
title: The event journal -- what happens in a world is one of its own event types, with roles, sortes and who learns it; read by the models by what is known, counted by one condition form, proposed by the interpreter and by Play
type: feature
status: live-gate
created: 2026-10-11
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, destructive_data, db_write]
blast_radius: large
lot_id: LOT-0114-event-journal.md
brief_ids: [A, B, C, D, E, F, G, H]
current_brief:
schema_version_touched: v2.25
retry_count: 0
slug: event-journal
---

## Request (verbatim, as Nia stated it)

The series request is TICKET-0111's (`tooling/tickets/TICKET-0111-condition-language.md`,
« Request »); the series document (`SERIE-conditions.md`, project doc) puts
this ticket fourth: the event journal (C1, F1, K1, L1 of the series).

In this planning conversation (2026-10-11):

> Ticket 0114 de la série des conditions. Regarde ou nous en somme et
> propose les choix. n'oublie pas. Je veux le plus de liberté possible dans
> ce que mon outil est en mesure de supporté.

After the RECON and the decision blocks:

> A2 on fait 0019 avant de continuer la série c'est cela ? B1, C1, D1, E1 a
> moins que tu ne me dise que la qualité de travail va être moindre. Dans ce
> cas, je suis ouverte a ouvrir le ticket 0120 pour faire le chantier du
> calandrier. F1, G1, H1, I2, K-a, L1, M-c me semble mieux que M-a.

> P1, N1 je me pose la question, si les type deviennent obligatoire et que
> je peux les modifié, cela deviens du vocabulaire de mon monde et ils ont
> des définitions. Est-ce qu'ils ont leur propre onglet dans création ou ils
> sont listé au même titre que les entitées ou non? O1, Q1, R1.

> si je comprend bien, le journal que l'on est en train de faire remplacera
> ce que Évènement fait a l'heure actuelle. créer un evênement se fait
> maintenant en déclarant des choses qui se sont passé dans l'outil de lore
> qui sont convertis en Facts. T3 je pense que cela vaut la peine de
> regrouper.

> U1

> V1, W1, X1 cela dépend il peut y avoir seulement les participant qui le
> savent par défaut, mais cela se propage plus tard si ils en parle. Ou ils
> peuvent voiloir que cela soit secret et personne n'en parle ou un des
> participant en parle (non secret pour lui). Y2.

## Clarifications resolved (intake)

- **Production (R-02).** Nia measured her database (2026-10-11): four
  events -- `military`, `other`, `political` secret, `social` public --,
  each with `consequences` = the JSON `null`, no magic impact, no
  `occurred_at`, zero facts with an `event_id`. v2.24 types them by their
  category; v2.25 loses nothing by dropping the columns (L1).
- **The cut (A2).** 0114 holds the journal, the vocabulary, the readers,
  the `event` form, the `failure` role, the interpreter and Play's
  proposals. TICKET-0119 follows at once, before 0115: the Journée and
  tick producers, M-c, U1, Y2. TICKET-0120, the calendar, after 0116 (P1).
- **The journal replaces « Événements » (T3).** The tab stays and becomes
  the journal (type, participants by role, quantity, scopes); the world's
  vocabulary -- states, event types, sortes -- is one new tab,
  « Vocabulaire du monde ». Declaring events from Lore is U1 (0119).
- **Secrecy is per participant (X1, refined by Nia).** Each participant's
  knowledge row is secret or not, the type giving the default: a pact can
  be known to its participants only, kept secret by all, or secret for one
  and not another. Scopes are independent of secrecy. A player character
  is never secret (INV-07).

## Decisions locked (do not re-litigate without Nia)

- **A2** -- 0114 as cut above; 0119 right after, then 0115; 0120 after 0116.
- **B1** -- an event type declares its name, domain (the seven former
  categories), roles, whether it counts a quantity, enters the chronicle,
  and its participants' default secrecy.
- **C1** -- roles per type, each accepting entity types.
- **D1** -- per-world SORTES (anonymous kinds: « loup ») may fill a role
  that accepts one; the quantity lives on the event.
- **E1** -- an event keeps its session and day (`session_id`, `batch_id`).
- **F1** -- a leaf counts `always`, since the quest, since the step
  (`agenda_step.started_at`, else `accepted_at`); an eligibility refuses
  the last two.
- **G1** -- one condition form, `event`.
- **H1** -- a `failure` role: shown, never acting.
- **I2** -- the MJ (Play's analyzer) may propose a new type, approved with
  the event.
- **K-a / W1** -- an event's fact, known by its participants; the type's
  scopes (`location`, `world`, `rencontre`(role), `faction`(role), each at
  a level), overridable per event.
- **X1** -- secrecy per participant, the type's default; never a PC.
- **L1** -- `consequences`, `has_magic_impact`, `occurred_at` dropped
  (v2.25). Rejected: L1' (keep `consequences`: all JSON null).
- **M-c** -- a type's effects pre-fill state changes: TICKET-0119.
- **N1** -- the type required; old events typed by their domain, role
  « Impliqué ». **O1** -- public/confirmed -> a `world` scope at `knows`;
  secret -> none.
- **P1** -- the calendar is 0120, after 0116.
- **Q1** -- Play's MJ reads the chronicle events the PC knows; the tick
  what everyone knows; only `in_chronicle` types are told to a model.
- **R1** -- the interpreter knows the types and sortes, writes event
  leaves, and proposes a missing type or sorte.
- **T3** -- « Vocabulaire du monde » groups États, Types d'événements,
  Sortes; « Événements » becomes the journal.
- **U1** -- Lore declares events (0119). **V1** -- `event_participant`
  replaces `event_entity`. **Y2** -- the event review card (0119).
- **WL1** (TICKET-0113's carried point) -- the MJ sees non-hidden states.

## Drafting decisions (made in the lot; Nia may reverse before execution)

1. A step activated before v2.24 has no `started_at`: `since step` counts
   from the quest's acceptance.
2. The place is an event column, not a role; a leaf names a place and
   counts it and everything under it.
3. Several filters per leaf, in `condition_node_filter`.
4. A leaf may say « any role ».
5. A leaf sums quantities; an event without one counts 1.
6. `quest` / `step` windows are refused in an eligibility.
7. The fact's text is « title — description ».
8. An event's type is fixed; participants are never removed (the journal
   corrects and adds).
9. **G:** a type or sorte the interpreter proposes is created when the
   creator clicks « Créer » on its card, not with the offer's save (0113's
   states wait for the save). The vocabulary is the world's; one
   validation path. A type created for a proposal she then discards stays,
   retirable.
10. **H:** an analyzer participant the type cannot take is left out, the
    rest of the event kept; an unknown type code drops the proposal.
11. **V1 for events:** on a player surface, an event leaf about someone
    else is recounted from the events the character knows, not hidden
    behind « ? » -- the events are facts he may know.

## Carried forward / open

- **TICKET-0119** (next): the Journée and tick producers of typed events,
  M-c (a type's effects pre-fill state changes), U1 (Lore declares events),
  Y2 (the event review card). The tick still emits the untyped shape,
  typed by its domain at apply (C-06).
- **TICKET-0120** (after 0116): the calendar -- « avant le jour N »,
  « tenir N tours », a day number on events.
- **0115** (dashboard): the acceptance rate of typed proposals (D1), of
  proposed types (I2), of interpreter proposals carrying `vocabulary`.
- Absence (« sans être repéré ») is `not` over an `event` leaf today; a
  dedicated form only if the dashboard shows the need.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] The vocabulary, its writer and v2.24  -> verify/checks/event_journal.py
- [ ] The journal's writer and the applier  -> verify/checks/event_writes.py
- [ ] The readers, WL1 and v2.25  -> verify/checks/event_contexts.py
- [ ] The `event` form and the `failure` role  -> verify/checks/event_conditions.py
- [ ] The interpreter reads and proposes  -> verify/checks/event_interpreter.py
- [ ] Play's analyzer proposes typed events  -> verify/checks/event_analyzer.py
- [ ] Every check of the corpus  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After `migrate_v2_24_event_journal.py` then `migrate_v2_25_event_columns.py`
      on a backup copy, then on prod: the four events show in « Événements »
      typed « Militaire », « Autre », « Politique », « Social », the public
      one known by everyone, the secret ones by their participants only.
- [ ] « Vocabulaire du monde »: create « Tuer » (tueur: personnage;
      victime: personnage ou une sorte; compte une quantité), a sorte
      « Loup »; « Tuers » asks before it is written.
- [ ] Journal: « Mira tue 3 loups » (Mira tueur, Loup victime) -- Mira's
      sheet knows the fact; Play's MJ mentions it to Mira, not to another
      PC who never learned it.
- [ ] A quest step « A tué 3 loups depuis le début de l'étape », and a
      failure « Le donneur a été tué »: Journée shows both, marks them,
      never acts.
- [ ] The interpreter: « a piégé deux lapins » proposes « Piéger » and
      « Lapin »; created from the card, inserted, saved.
- [ ] Play: a scene where something happens proposes a typed event in the
      queue; a proposed type shows its badge and roles; approving writes
      both.
- [ ] After the merge: `apply_ticket_0114_condition_prompt.py` and
      `apply_ticket_0114_analysis_prompt.py` on prod, each printing
      `vN -> vN+1` (an edited head: « fragment not found » lines to edit by
      hand).

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
