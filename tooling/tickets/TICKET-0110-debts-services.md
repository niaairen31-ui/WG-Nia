---
id: TICKET-0110
title: Debts and services -- a debt is a row with its fact, a service owes the rest, a quest settles on credit
type: feature
status: exec
created: 2026-10-07
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: medium
lot_id: LOT-0110-debts-services.md
brief_ids: [A, B, C, D]
current_brief: C
schema_version_touched: v2.19
retry_count: 0
slug: debts-services
---

## Request (verbatim, as Nia stated it)

The series' request is summarized in
`claude/HANDOVER-quetes-tickets-0110-0111.md` §2 (services tied to the
relation, debts, an unpaid debt eroding the relation once time passes);
J2 and the split F1 of 0108 carried it here. Nia's words in this ticket's
planning conversation (2026-10-07):

> A2, B3, C2 pour commencé en jouer je vais voir si je réactive C3, D1, E
> fera l'objet de son ticket séparer lorsque j'aurrai implanté un calandrier
> ou un horraire comme il faut. (diffiéré), F pourquoi recommande tu le
> facultatif? Il me semble que c'est bien mieux que cela soit automatique,
> si la transaction est secrete, on applique le tag secret au fait. G1, H1,
> I je pense que ca vaut la peine d'y pensée pourquoi on n'utilise pas
> relation de type dette avec un fait pour repondre a F? Je ne veux pas deux
> choses qui font la même chose. J1, K ok pour le découpage.

> F-a, F-b1, I2. E laisse disponible, C2 est l'option que je choisi, c'est
> C3 que je réactive si je le veux. The query returned 0 rows. I ran it
> read-only against the prod database (`~/.world_engine/world_engine.db`),
> so no `relation` row has `type = 'debt'`.

> S2, T1 mais au niveau des faits et des competences, il est possible que
> je traine la dette jusqu'a ce que moi, en tant que joueur j'aprenne le
> fait ou devienne maitre dans cette competence. Ainsi, un NPC peut investir
> dans la progression du joueur et y retirer quelquechose ( ce qui fait du
> sens pour un joueur). U1, une dette envers une faction est toujours lié a
> au moins une personne (maintenant si cette personne meurs, ce n'Est pas de
> la faute du joueur si le NPC n'a pas partagé l'information). Je propose de
> le lié avec le NPC de la faction auquel on a lié a quête a la base. V1, W
> je veux quelque chose comme dans l'onglet Play, Mes savoirs, Quêtes,
> dettes. Demander un service est dans l'onglet journée ''vanille''. ok pour
> la création d'un onglet dans création pour toute les dettes du monde.

> X1, W-a. Ok pour ta clarification, une diminution automatique de X point
> d'intensité de la relation. ( le montant de base est 10 pour un fait, 20
> pour un connaissance)

## Clarifications resolved (intake)

- **A relation's type is a label on one row per oriented pair** (LOT R-01):
  a « debt » type would replace what the pair already is, and has no place
  for terms, an origin or a settlement. Hence I2: the table alone.
- **The model can write a `debt` link** (R-02): the link agent's closed
  vocabulary and its seeded prompt carry it; the live prompt is edited by a
  delivery script that keeps a creator's edits.
- **A party would keep the old text after a change** (R-05): the version a
  knower sees is dated by his last contact; closing a debt refreshes both
  parties' rows.
- **A faction knows nothing by itself** (R-06, 0109's C-03): U1 is a
  `faction` default on a debt that is not secret; X1 links the debt to a
  person, the contact.
- **An offer names no person for a faction** (R-10): X1 adds
  `quest_offer.contact_entity_id`.
- **Saving the world's rates writes every column** (R-09): the two debt
  settings must be in the ⚖ panel or a save would erase them.
- **The settlement's term application is bound to a quest** (R-08): B makes
  it reusable for services and credit, behavior unchanged.
- **The engine keeps no world time** (R-15): the erosion waits.
- **Journée is one view; « Mes savoirs » lives only in sealed Play and
  reads stored rows** (R-13): W-a adds three sub-tabs and does not port it.
- « connaissance » in Nia's last message is read as « compétence »: 10 for
  a fact, 20 for a skill (drafting decision 1 of the delivery).

## Decisions locked (do not re-litigate without Nia)

- **J2** (series) -- a `debt` table; settled or forgiven, never deleted
  (deleting is a correction, paying is a change); a fact attached.
- **A2** -- a debt is born of a service, of Nia's hand, or of « régler à
  crédit »: when coins or items are the only reasons a quest cannot be
  settled, the player pays what he has and the rest becomes a debt per
  creditor. Rejected: a debt proposed by the model (reactivation: quests
  proposed by the model exist).
- **B3** -- a service is not an offer: Nia asks it from Journée, names who
  helps and what he does with the quest term editor; applied at once.
  Rejected: B1 (a reversed quest offer; reactivation: a service with steps
  or prerequisites to fulfil).
- **C2** -- a debt is a list of typed terms; its value in the indicative
  unit is shown, never converted. Rejected for now: C3 (settling « otherwise
  », Nia entering what was given in exchange; reactivation: Nia asks for it
  after playing with C2). C1 (units only, repaid in any currency at the
  rates) rejected: it makes the unit a currency (C1 of the series).
- **D1** -- repaid all at once; refused when the debtor lacks something.
  Rejected: D2 (partial repayment).
- **E** -- the relation's change at borrowing and at repayment is its own
  ticket, once a calendar exists. A `relation` term stays available in a
  service's « what it costs now ».
- **F-a** -- every debt's fact is automatic: a free `information` fact,
  participants debtor, creditor (and contact), worded from its terms and
  motive; settled and forgiven rewrite it as a `changement`.
- **F-b1** -- « transaction secrète » makes both parties' knowledge rows
  secret; nothing else.
- **G1** -- `has_debt_to` / `no_debt_to`: existence only, creator only.
- **H1** -- the erosion of an unpaid debt is deferred (see Carried
  forward).
- **I2** -- the table is the one way to say « X owes Y »: the relation type
  `debt` is retired (offered to no one, refused by the writer). Rejected: I3
  (a `debt` relation with a fact, no table).
- **J1** -- the debtor is a character; the creditor a character or a
  faction. Journée shows the player's debts; Création writes any.
- **K1** -- one migration (v2.19), four briefs: A schema and vocabulary, B
  writers and routes, C Création, D Journée.
- **S2** -- a service = what the character does now (quest terms, applied
  as a settlement applies them) + what the player will owe, prefilled from
  the coins and items received.
- **T1** -- a debt owes money, items, a fact to deliver, a skill to teach;
  never relation. A fact or skill debt waits until the debtor knows the
  fact or is Maître (an NPC invests in the player). When the receiver
  already holds it, his regard toward the debtor falls instead: 10 for a
  fact, 20 for a skill, per-world settings.
- **U1** -- a debt toward a faction that is not secret is known by its
  members.
- **V1** -- an optional motive, carried into the fact.
- **W-a** -- Journée in three sub-tabs, like Play's: « Journée » (declare,
  « Demander un service », the days), « Quêtes », « Dettes »; Création
  gains « Dettes », every debt of the world. « Mes savoirs » is not ported
  here.
- **X1** -- a faction creditor is always linked to a person: the offer's
  contact (a member, set in the offer editor), else the member Nia names;
  a service for a faction is linked to the one who helps. If that person
  dies, the debt stays owed to the faction.

## Carried forward / open

- **The relation at borrowing and repayment** (E): its own ticket, with a
  calendar. Reactivation: a world-level day counter exists (see below).
- **Erosion of an unpaid debt** (H1). Reactivation, verifiable: `grep -rn
  "world_day" src/world_engine/models` returns a column (a world-level day
  counter; `batch.day_number` is per session).
- **Settling « otherwise »** (C3): Nia asks for it after playing.
- **Partial repayment** (D2): rejected; reactivation -- a debt Nia wants to
  pay down in instalments.
- **Debts proposed by the model**: reactivation -- quests proposed by the
  model exist.
- **« Mes savoirs » in Journée** (W-a): a ticket numbered after 0111; it
  must read resolved knowledge and its versions, not only stored rows.
- **Rank trials** (K1 of the series): TICKET-0111.
- **The faction-role prerequisite** (nº 11 of 0108): its own ticket, once
  `faction_membership.role` is tied to `faction_role`.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] The debt tables, the v2.19 migration, the two requirement forms, the retired relation type, the writers, a service, « régler à crédit », the reads and routes, and both surfaces -> verify/checks/debts.py
- [ ] Quest offers keep 0108's contract with ten forms -> verify/checks/quests.py
- [ ] Settlement keeps 0109's contract after its refactor -> verify/checks/quest_rewards.py
- [ ] The requirement vocabulary, its CHECKs and its evaluators agree -> verify/checks/day_plan.py
- [ ] Every requirement form has its French detail -> verify/checks/day_narration.py
- [ ] Canon writes stay on sanctioned sites, the debt writers included -> verify/checks/single_canon_write.py
- [ ] Facts and participants are written through the fact chokepoint -> verify/checks/fact_spine.py
- [ ] The world cascade covers the two new tables -> verify/checks/world_cascade.py
- [ ] Schema doc and code agree on v2.19 -> verify/checks/schema_version_agreement.py
- [ ] The « Dettes » island is mounted the one way -> verify/checks/creation_island.py
- [ ] Every Création tab has its shell and primary action -> verify/checks/page_contract.py
- [ ] The built frontend matches its sources -> verify/checks/frontend_build_fresh.py
- [ ] The whole corpus is green -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After `python scripts/backup.py`, with `WORLD_ENGINE_ENV=prod`: `python scripts/migrate_v2_19_debts.py` reports `Migration v2.19 applied.` (and its notes); `python scripts/apply_ticket_0110_link_prompt.py` reports `pt-npc-link-pair: vN -> vN+1` (or `unchanged`, or `fragment not found, edit by hand` -- then remove `debt` from the type list in the Prompts tab). The cockpit boots.
- [ ] Read-only, on prod: `SELECT COUNT(*) FROM link_batch_row WHERE kind = 'relation' AND json_extract(payload, '$.type') = 'debt';` -- report the number (a staged link of that type would be flagged by the coherence pass).
- [ ] Création › a character's relations: « debt » is no longer suggested. ⚖ in Quêtes shows the two debt settings, empty = 10 and 20.
- [ ] Création › Quêtes: an offer given by a faction shows « Contact de la faction » with its members; pick one, save, reopen: it is kept. Change the giver: it is cleared.
- [ ] Création › Dettes: « + Nouvelle dette » Millys -> Garde, 10 pièces, motive, secret: listed « due », « secrète », value 10. Millys's knowledge (her sheet) holds the fact « Millys doit à Garde : 10 pièce(s) — … ». A debt toward a faction without a contact is refused.
- [ ] Journée › Journée: « Demander un service » to Garde: he gives 20 pièces, it costs relation 5; « Ce que vous devrez » fills with 20 pièces. « Accepter le service » -> Millys +20, Garde's regard toward her -5; Journée › Dettes lists the debt, origin « service ».
- [ ] Journée › Dettes: « Rembourser » -> « réglée »; the fact now reads « Millys a réglé sa dette envers Garde … ». A debt of a fact Millys does not know: « Pas encore : Millys doit connaître le fait à transmettre », « Rembourser » disabled; « Remettre » with a note -> « remise ».
- [ ] « Régler à crédit »: a quest costing more coins than Millys has: « Confirmer : quête accomplie » stays disabled; « Régler à crédit » lists what will be owed to whom (a faction's contact preselected); confirm -> the quest reads « réglée », Journée › Dettes shows the debt, origin « quête « … » ».
- [ ] Prerequisite: an offer with « N’a aucune dette envers Garde » is not proposed while a debt to Garde is open, and is once it is repaid or remitted.
- [ ] Journée's three sub-tabs switch; « Quêtes » behaves as before (accept, pin a day, abandon, « Déclarer accomplie »).

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
