---
id: TICKET-0104
title: The Lore writing panel's default scopes pick their entity from the whole world
type: bug
status: live-gate
created: 2026-10-05
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
lot_id: LOT-0104-lore-scope-picker.md
brief_ids: [A]
current_brief:
schema_version_touched:
retry_count: 0
slug: lore-scope-picker
---

## Request (verbatim, as Nia stated it)

> Dans l'outils de lore, lorsque je veux mettre qu'un fait est connus par
> défaut par : Ceux qui sont dans le lieux : ... Je ne veux pas sélectionnée
> de lieu.  Je voudrais que si c'est un lieu de zone entrer dans n'importe
> quel lieu de cette zone déclenche l'apprentissage de ce fait, si c'Est un
> lieu visitable, c'est a la visite du lieu.

Planning answers, in order:

> A1, B […]

> J2, A1'a

The second half of the request — learning a fact on entering a place, and
keeping it — is TICKET-0105 (codes B5, G1, H1, I1, J2, L1, K1, M1). This
ticket is the picker only.

## Clarifications resolved (intake)

- **« Je ne veux pas sélectionner de lieu » is a bug, not a wish**: the
  scope's entity list offers only the entities the text named (LOT R-01).
  A text naming no place leaves « Ceux qui sont dans le lieu » with an empty
  list. The faction scope has the same defect.
- **The zone half of the request already holds for presence**: a
  `location` default reaches anyone whose current location is that place or
  one of its descendants (LOT R-06). What does not hold is that the fact
  stays known after leaving — that is TICKET-0105.
- **A `rencontre` scope is not limited to characters**: the preset gives a
  non-character appellation a `rencontre` scope on its own entity, and a
  social relation records an encounter whatever its two ends are (LOT R-05).

## Decisions locked (do not re-litigate without Nia)

- **A1** — a `location` or `faction` scope picks its entity among the
  draft's entities, then among every active entity of the world of that
  type; a world entity picked joins the draft as `existing`, through the
  same helper a knower uses. Rejected: A2, places only (the faction scope
  has the same defect).
- **A1'a** — a `rencontre` scope picks among entities of any type, panel
  only; the server is unchanged. Rejected: A1'b, characters only in panel
  and server (the `rencontre` scope of a non-character appellation could no
  longer be written from Lore). Reactivates if a production measurement
  shows no `rencontre` pair involving anything but two characters.

## Carried forward / open

- **Learning by visit, keeping what was learned, versions of a fact** —
  TICKET-0105, locked in the same planning conversation: B5 (last-contact
  registries, read-time resolution), G1 (`correction` vs `changement` in
  `change_history`), H1 (the choice at every edit, preselected by facet),
  I1 (deleting is correcting), J2 (faction scope learned too), L1 (what
  counts as a contact), K1 (stale knowledge marked in Lore only), M1
  (backfill). Production measurement for 0105: `fact_default` 540 rows —
  world 328, rencontre 167, location 43, faction 2; 79 of 1,660 facts carry
  a non-empty `change_history`.
- **Zones are not marked in the picker.** `/api/entities` does not say
  which place is a zone; the creator reads it from the name. Reopen if
  telling them apart in the list is asked for.
- **The model still proposes scopes only on named entities**
  (`lore_write_draft._scopes`, LOT R-04). Widening what the model may
  propose is not asked for.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] The panel's scopes pick from the whole world; rencontre takes any type; one path adds a world entity to the draft -> verify/checks/lore_write.py
- [ ] The built frontend matches its sources -> verify/checks/frontend_build_fresh.py
- [ ] The panels still send their attempt id -> verify/checks/lore_usage.py
- [ ] The decision registry and its index agree -> verify/checks/decisions_index.py
- [ ] The whole corpus is green -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] Écrire, a text that names no place: add « Ceux qui sont dans le lieu », pick a zone from the list, commit. The fact's fiche shows the default on that zone.
- [ ] Same with « Les membres de la faction » on a faction the text did not name.
- [ ] « Ceux qui ont rencontré » lists characters, places, factions and objects; a character picked there commits.
- [ ] A scope set to a place, then switched to « Les membres de la faction », shows « — choisir — » again; the commit is not refused for a wrong type.
- [ ] A character added as a knower, then picked for a « Ceux qui ont rencontré » scope, counts once in « N entité(s) retenue(s) ».

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
