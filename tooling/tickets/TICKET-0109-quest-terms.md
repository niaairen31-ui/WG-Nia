---
id: TICKET-0109
title: Quest costs and rewards in five currencies, objects held in quantity, the indicative unit, « déclarer accomplie »
type: feature
status: exec
created: 2026-10-07
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: medium
lot_id: LOT-0109-quest-terms.md
brief_ids: [A, B, C, D]
current_brief:
schema_version_touched: v2.18
retry_count: 0
slug: quest-terms
---

## Request (verbatim, as Nia stated it)

The series' request (ticket III of A1) is summarized in
`claude/HANDOVER-quetes-ticket-III.md` §2; TICKET-0108 carried this part
forward (its C1, D1, E1, G1 and nº 16). Nia's words opening this ticket:

> Le ticket 0108 est passé tel qu'écrit, mergé et testé. on passe au ticket
> 0109, coûts et récompenses typés, bouton d'accomplissement, unité
> indicative.

> A1, on fait disparaitre équipped cela ne sert a rien. B1, C-src1, C-skill1
> il gagne 10% des points necessaire a l'avancement du niveau, les points en
> plus ne sont pas reconduit. C-teach1 le PJ doit être maitre. D1, D-fail2,
> E1, F1

## Clarifications resolved (intake)

- **An item is one entity with one owner** (LOT R-01): ten furs would be ten
  entities. E1 of 0108 is realized as A1: `item` a kind, `item_holding`
  (holder, quantity).
- **`item_update` has no producer** (R-03): it only toggled `equipped`;
  retired with it.
- **No item may lie in a zone** (R-04, CLAUDE.md): the holding writer
  refuses a zone that receives; a promotion empties a place that just became
  a zone through the same writer.
- **The interpretation list stays names only** (R-02): the model answers a
  name, the possession check matches it exactly; the MJ's inventory line
  shows quantities.
- **Money has no balance guard** (R-08): a reward is always given (C-src1),
  so a giver's balance may fall below 0; a cost the character cannot pay
  refuses.
- **A rank rise restarts points at 0** (R-11): C-skill1's « surplus not
  carried » holds by construction of `write_skill_progress`.
- **Nothing records that a quest's terms were applied** (R-12):
  `quest.settled_at`.
- **G1's days** (R-14) are the day plays whose `agenda_id` is the quest's.

## Decisions locked (do not re-litigate without Nia)

- **A1** — `item` is a kind (`value` added); `item_holding` says who holds
  how many -- any entity, a place included; the migration turns `owner_id`,
  else `location_id`, into a holding of 1; `owner_id`, `location_id` and
  `equipped` are dropped, `item_update` with them. Rejected: A2 (a quantity
  on `item`).
- **B1** — the terms live on the offer and are copied into the quest at
  acceptance; a later edit of the offer never changes an accepted quest.
- **C-src1** — a reward is always given: the giver's balance may go
  negative; for items, the giver gives what he holds and the rest is
  created.
- **C-skill1** — a skill the character holds: + 10 % of the points its
  next rank needs (rounded up, at least 1), the surplus not carried; nothing
  at Maître. A skill he does not hold: learned at Inexpérimenté, taught by
  the counterparty when the counterparty is Maître.
- **C-teach1** — a skill cost (teaching) needs the character at Maître.
- **D1** — « Déclarer accomplie » in Journée: the recap, then a direct
  write; an unpayable cost refuses. Rejected: D2 (forcing it).
- **D-fail2** — no « déclarer échouée » button.
- **E1** — a per-world rates table (`quest_economy`) plus `item.value`;
  defaults money 1, relation 1, fact 5, skill 20, band 100-150 %.
- **F1** — one migration (v2.18), four briefs: A schema and objects, B
  terms and the unit, C settlement, D surfaces.
- From 0108, still binding: G1 (the measured context only, no model
  opinion), B-dir (a relation term moves what the NPC feels toward the PC),
  the player never sees the agenda.

## Carried forward / open

- **Debts and services** (J2): TICKET-0110. **Rank trials** (K1):
  TICKET-0111.
- **« Déclarer échouée »** (D-fail2): reactivation -- a quest Nia wants
  closed as failed without abandoning it.
- **Artifacts** (unique objects): their own ticket, once they exist.
- **Forcing an unpayable settlement** (D2, rejected): reactivation -- a
  story where the debt is the point (likely 0110).
- **Quests proposed by the model or from the Lore tool**: later tickets.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Holdings, the v2.18 migration, terms, the indicative unit, settlement and the two surfaces -> verify/checks/quest_rewards.py
- [ ] Quest offers, acceptance and the panel keep 0108's contract -> verify/checks/quests.py
- [ ] No being or item lies in a zone, holdings included -> verify/checks/zone_placement.py
- [ ] A promotion moves a place's holdings to its first child -> verify/checks/zone_promotion.py
- [ ] The v2.12 migration still runs on today's models -> verify/checks/zone_migration.py
- [ ] Canon writes stay on sanctioned sites, the term and settlement writers included -> verify/checks/single_canon_write.py
- [ ] The world cascade covers the four new tables -> verify/checks/world_cascade.py
- [ ] Schema doc and code agree on v2.18 -> verify/checks/schema_version_agreement.py
- [ ] The appliers no longer name `item_update` -> verify/checks/day_mutations.py
- [ ] The built frontend matches its sources -> verify/checks/frontend_build_fresh.py
- [ ] The whole corpus is green -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After `python scripts/backup.py`, `python scripts/migrate_v2_18_quest_terms.py` on prod reports `Migration v2.18 applied.`, its notes (an item with both an owner and a place, an item in a zone, a holder gone) and the number of holdings; the cockpit boots.
- [ ] Création, an item « Fourrure de loup », value 3: its sheet shows « Détenu par ». On Millys' sheet, « Objets »: give her 10; on a faction's sheet and on a place's sheet, give a few. Set one to 0: it leaves the list. Giving furs to a zone is refused.
- [ ] Création › Quêtes: an offer with a cost « 5 × Fourrure de loup » and rewards « 20 pièces » and « relation +5 »: the value and the verdict update as you type; ⚖ changes the money rate, the verdict follows. Save.
- [ ] Journée › Quêtes: the offer lists its terms. Accept it, then edit the offer in Création: the accepted quest's terms do not change.
- [ ] « Déclarer accomplie »: the recap shows the steps, the days that advanced it, any change awaiting review, the terms and their value. « Confirmer » -> the quest reads « réglée »; Millys has 5 furs less, 20 coins more; the giver's feeling toward her rose by 5.
- [ ] A quest whose cost Millys cannot pay: the recap says why, « Confirmer » stays disabled.
- [ ] A skill reward on a skill she holds: + 10 % of its next rank's points; on a skill she does not hold: she learns it at Inexpérimenté.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
