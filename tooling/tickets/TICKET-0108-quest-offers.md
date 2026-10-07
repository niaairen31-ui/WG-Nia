---
id: TICKET-0108
title: Quest offers authored by the creator, accepted as open plans, pinned to a day
type: feature
status: exec
created: 2026-10-06
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: medium
lot_id: LOT-0108-quest-offers.md
brief_ids: [A, B, C]
current_brief:
schema_version_touched: v2.17
retry_count: 0
slug: quest-offers
---

## Request (verbatim, as Nia stated it)

The series' request (ticket III of A1; 0106 and 0107 done) is summarized in
`claude/HANDOVER-quetes-ticket-III.md` §2 -- quests or missions that give
things to do in the days, an economy of services tied to relations, five
currencies, two kinds of prerequisites. Nia's words in this ticket's
planning:

> A1, B Je veux que tu me donne l'ensemble des requis possible avant de
> prendre une décision. C1, D1 […] E on a déja les ressources de type
> monnaie, mais je pense qu'il est important qu'un objet peut être possédé
> par plusieurs personnes (ex les fourrures), un artefact est une autre
> chose et est unique. F1. ok pour ta proposition concernant l'enjeu avec A.

> E1, B, en 11, il faudrait que ce soit lié aux roles de la faction sinon sa
> sert a rien, 17 laisse faire les artefacts, ils n'existent pas encore pour
> vrai. Il semble manqué possède une dette envers X. ok pour ton découpage de
> V1, ok pour la direction on veut l'apprécisation du NPC sur le PJ. G1,

> H1, I1, L1, M1, N1, O1

## Clarifications resolved (intake)

- **The one-active-agenda rule is not the obstacle** (LOT R-01, R-03): a
  planned day is itself an agenda of the player, and TICKET-0077 already
  keeps several open plans, one selected per day. A quest born `paused` is
  one of them.
- **A quest born `active` would collide with the day's plan** (R-01):
  `write_agenda` gains a `paused` birth.
- **`resource` is money** (R-08): the ledger has no currency column; the
  « 10 fourrures » case needs objects held in quantity (E1, TICKET-0109).
- **`relation_gte` read either direction, structural rows included** (R-07):
  it now reads the target's feeling toward the character, as the NPC-goal
  judge already does -- for day plans too.
- **The day-plan model must not emit the creator's forms** (R-06): a
  separate tuple for its parser.
- **Journée never sees the agenda** (R-19): quests are shown by `quest_id`.

## Decisions locked (do not re-litigate without Nia)

- **A1** — a quest accepted is an agenda born `paused`: several quests at
  once, the one-active rule unchanged; a day selects its plan, or the player
  pins it (O1). Rejected: A2 (selection by the model only -- reactivation:
  the pin is never used), A3 (several active agendas -- reactivation: a day
  must advance two quests at once).
- **B (v1 forms)** — 1 knowledge, 2 relation >= N, 4 money >= N, 5 place
  reachable, 8 has met, 9 faction member, 12 skill rank >= N, 15 quest
  completed. Eligibility and steps share the vocabulary (one language, the
  locked B1 of the series). Rejected: B2 (a separate targeting vocabulary).
- **B-dir** — `relation_gte` reads the NPC's appreciation of the PC.
- **C1** — an offer's costs and rewards are terms applied at completion by
  their own applier (TICKET-0109); `_EFFECT_TYPES` stays closed. Rejected:
  C2 (widening `_EFFECT_TYPES` -- reactivation: quests proposed by the
  model).
- **D1** — « déclarer accomplie » in Journée, a direct creator write after a
  summary (TICKET-0109). Rejected: D2 (a mutation in the queue).
- **E1** — `item` becomes a kind of object held in quantity
  (`item_holding`); `artifact` is the unique object (TICKET-0109). Rejected:
  E2 (a quantity on `item`), E3 (no common objects).
- **F1** — four tickets: 0108 offers and quests, 0109 costs, rewards,
  objects, the button, the indicative unit; 0110 debts and services; 0111
  rank trials.
- **G1** — at « déclarer accomplie », the measured context only, no
  model opinion. Rejected: G2 (the model suggests -- reactivation: reading
  the days becomes too long in practice).
- **H1** — the giver is a character or a faction.
- **I1** — Journée lists the offers the player is eligible for. Rejected:
  I2 (ineligible ones greyed), I3 (proposed on contact -- reactivation:
  TICKET-0069 unseals Play).
- **L1** — a `repeatable` flag: otherwise once per character.
- **M1** — a quest's state is its agenda's.
- **N1** — « Abandonner »: the agenda to `abandoned`, nothing deleted.
- **O1** — « Cette journée avance »: the pinned quest replaces the
  selection call; the reconciliation still runs.
- The quest is visible in Journée; the agenda behind it is not.

## Carried forward / open

- **Costs, rewards, objects held in quantity, « déclarer accomplie », the
  indicative unit** (C1, D1, E1, G1, nº 16): TICKET-0109. Until then a
  completed quest gives what its steps' approved changes give, nothing more.
- **Debts and services** (J2, nº 18 « aucune dette envers X », nº 19 « a une
  dette envers X »): TICKET-0110. Unpaid-debt erosion stays deferred until
  the engine moves time.
- **Rank trials** (K1): TICKET-0111.
- **A requirement on a faction role** (nº 11): needs
  `faction_membership.role` tied to `faction_role` first -- its own ticket;
  reactivation: `faction_membership` carries a foreign key to `faction_role`.
- **Forms 3, 6, 7, 10, 13, 14** (relation <= N, at the place, has been to,
  not a member, skill learned, X alive): not in v1; reactivation: an offer
  Nia writes cannot be expressed without one.
- **Quests proposed by the model, quests created from the Lore tool**:
  later tickets (E1 of the series).
- **A rendezvous names only a `relation_gte` target** (R-11): a `has_met`
  target is not named; report only.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Vocabulary, migration, evaluators, offers, acceptance, abandon, the pin, the two surfaces -> verify/checks/quests.py
- [ ] The day plan's requirement rules hold on eight forms -> verify/checks/day_plan.py
- [ ] Every requirement form has its French reason -> verify/checks/day_narration.py
- [ ] Journée still names no agenda id -> verify/checks/day_mutations.py
- [ ] Canon writes stay on sanctioned sites, the quest writers included -> verify/checks/single_canon_write.py
- [ ] The world cascade covers the quest tables -> verify/checks/world_cascade.py
- [ ] Schema doc and code agree on v2.17 -> verify/checks/schema_version_agreement.py
- [ ] Création islands and tabs keep their contracts -> verify/checks/creation_island.py
- [ ] Création pages keep their contracts -> verify/checks/page_contract.py
- [ ] The built frontend matches its sources -> verify/checks/frontend_build_fresh.py
- [ ] The whole corpus is green -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After `python scripts/backup.py`, `python scripts/migrate_v2_17_quests.py` on prod reports `Migration v2.17 applied.` and the number of requirement rows preserved; the cockpit boots.
- [ ] Création › Quêtes: « + Nouvelle quête » -> « La fourrure du loup géant », given by an NPC, proposed to the members of a faction, two steps (« Traquer le loup » with « A rencontré » the hunter, « Rapporter la fourrure »). Save, change the title, save again: the list shows the new title.
- [ ] Journée › Quêtes: the offer is listed only once Millys is a member of that faction. « Accepter » -> « Mes quêtes » shows it « en cours », its first step bold with what it still needs.
- [ ] Declare a day, choose « Cette journée avance : la quête … », « Émettre le plan », then resolve: the day works on the quest's step; after approving the step's change in the review queue, the panel shows the step done.
- [ ] Declare another day without choosing: the day still plans as before (a new plan or a plan the game selects).
- [ ] « Abandonner » (confirmed): the quest reads « abandonnée »; it is no longer offered.
- [ ] A day plan whose step needs an NPC's appreciation now reads that NPC's feeling toward Millys (the reverse row no longer counts).

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
