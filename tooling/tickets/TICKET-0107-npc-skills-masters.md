---
id: TICKET-0107
title: NPCs have skill sheets; a skill may require a master, and cannot be rolled until taught
type: feature
status: live-gate
created: 2026-10-06
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: medium
lot_id: LOT-0107-npc-skills-masters.md
brief_ids: [A, B, C]
current_brief:
schema_version_touched: v2.16
retry_count: 0
slug: npc-skills-masters
---

## Request (verbatim, as Nia stated it)

> 3- […] Un maintre dans un compétence peut débloqué cette compétence chez un
> joueur ou au autre NPC. […]

(TICKET-0106's request, its I1 half: « débloquer une compétence ».)

> Je veux que tu ne puisse pas utilisé une compétence si personne ne te l'a
> appris/ débloqué ( un maitre). pour les autres competenses que je ne lui ai
> pas donné, on lui donne le rang qui ne fait pas de modificateurs. 2. on
> remplace par la fiche PNJ les PNJ ont par défaut aucun modificateur dans
> les domaines de base (+0). 3. impossible a lancé.

> A2, B1, C1 oui pour les deux sous-questions. D Tous le monde a un domaine
> de base, donc dans D1 on ne devrais jamais se rendre a initié )(+0). E1,
> F ok, mais je peux faire comme a l'heure actuelle et bypassé pour ajouter
> des competenses maitre only en tant que créateur.

## Clarifications resolved (intake)

- **Every PC holds every skill of the world today**: creating a skill
  backfills every PC, a CLAUDE.md invariant (LOT R-02). Under A2 it holds
  for skills open to all; a `requires_master` skill is held once taught.
- **Play falls back to the base domain when the PC lacks a custom row**
  (R-03): « impossible à lancer » (B1) removes that fallback for a master
  skill only.
- **Day steps roll base domains only** (R-04): the lock never reaches them.
- **`physical_tier` has seven readers** (R-05): the opposition, two
  generators, the batch editor, the fiche's « Carrure » field, the Lore
  dossier.
- **« Everyone has a base domain »** (Nia, D): an NPC base domain without a
  row reads Initié (+0) — the same value as a seeded row, without seeding
  four rows on every NPC creation path (drafting decision, announced).

## Decisions locked (do not re-litigate without Nia)

- **A2** — a skill definition may `require_master`; a player holds no row
  for it until taught. Rejected: A1 (every custom skill locked).
- **B1** — Play does not roll a master skill the player was never taught:
  no dice, no point; the MJ narrates that he cannot. Rejected: B2 (roll the
  base domain).
- **C1** — « Apprendre » on the player's fiche grants the row from a
  character at Maître in that skill, or without a master (the creator's
  bypass); a skill learned starts at Inexpérimenté. Rejected for now: C2
  (learning proposed from a conversation; quests ticket).
- **D1** — an opposing NPC rolls its row for the skill, else its base row
  for the domain, else Initié (+0). Rejected: D2 (base domain only).
- **E1** — `physical_tier` is dropped; a generator's carrure becomes the
  NPC's `physical` row (`TIER_TO_RANK`), the migration converts every NPC's
  non-zero tier. Rejected: E2 (generators stop proposing it).
- **F1** — one skill fiche for players and NPCs; an NPC is given any skill
  at any rank; a skill's fiche carries « Exige un maître ».
- NPCs earn no points (only the player rolls).

## Carried forward / open

- **Learning through play (C2)**: a conversation or a day where a master
  teaches proposes the grant for review. Quests ticket.
- **Removing a skill row from a character**: not offered (a hard delete);
  the creator sets the rank instead.
- **The constraint-gated rolls** (gag, escape) keep their fixed difficulty
  of 1; the captor's own skill is not read (pre-existing deferral).
- **Play shows the locked band as text** (« locked ») in its sealed audit
  line until TICKET-0069.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] NPC rows, migration, opposition, carrure, the lock, learning, the fiche -> verify/checks/npc_skills.py
- [ ] TICKET-0106's rules still hold on the new rows -> verify/checks/skill_progression.py
- [ ] Canon writes stay on sanctioned sites, write_skill_row included -> verify/checks/single_canon_write.py
- [ ] The Play stream's request session stays read-only, skill_access declared -> verify/checks/stream_session_readonly.py
- [ ] Création islands and tabs keep their contracts -> verify/checks/creation_island.py
- [ ] Création pages keep their contracts -> verify/checks/page_contract.py
- [ ] Schema doc and code agree on v2.16 -> verify/checks/schema_version_agreement.py
- [ ] CLAUDE.md budgets and pointers hold -> verify/checks/claude_md_contract.py
- [ ] The built frontend matches its sources -> verify/checks/frontend_build_fresh.py
- [ ] The whole corpus is green -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After `python scripts/backup.py`, `python scripts/migrate_v2_16_npc_skills.py` on prod reports `Migration v2.16 applied.` and the number of carrures converted; the cockpit boots.
- [ ] Création › PNJ: an NPC whose carrure was +1 shows « Physique — Apprenti »; another lists no row and « Initié dans chaque domaine de base ». « Compétences à donner »: give an NPC « Alchimie » at Maître.
- [ ] Création › Compétences: tick « Exige un maître » on « Alchimie ». Création › PJ: Millys keeps her row if she had one; otherwise « À apprendre » lists « Alchimie » with the NPC as master. « Apprendre » from the master -> the row appears at Inexpérimenté, « enseignée par … ».
- [ ] Play, with a master skill Millys was never taught: « je distille une potion » (the arbiter names the skill) -> no dice, the MJ narrates that she does not know how; no `skill_progress` is applied.
- [ ] Play, against an NPC given « Escrime » at Maître: the verdict line's modifier carries -3 from the NPC's side.
- [ ] Création › PNJ › generator: a generated NPC with a carrure shows the note « Carrure proposée » and, once created, its Physique row.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
