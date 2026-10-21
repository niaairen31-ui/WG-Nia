---
id: TICKET-0116
title: Rank trials -- a rank that asks a trial is earned by a quest, in any world
type: feature
status: escalated
created: 2026-10-20
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [migration, db_write]
blast_radius: large
lot_id: LOT-0116-rank-trials.md
brief_ids: [A, B, C, D, E, F]
current_brief: F
schema_version_touched: v2.29
retry_count: 1
slug: rank-trials
---

## Request (verbatim, as Nia stated it)

The quests series reserved this ticket (K1 of « quêtes et compétences »:
the threshold half in TICKET-0106, rank trials as quests later), and the
conditions series placed it after TICKET-0121 (J1).

In this planning conversation (2026-10-20):

> Les tickets 0121 et 0123 sont supposé être fermer et mergé. le protocol est
> mis a jour. nous somme a 0116, mais il faut faire attention de ne pas faire
> quelque chose de trop spécifique a un jeu. Je veux qu'il puisse y avoir des
> ''epreuves de rang'' pour monter un competence de niveau et ela doit être
> vrai dans un nouveau monde aussi. Je veux que cela réutilise les quest (
> parce que finalement c'est juste une quest qui te donne la possibilité de
> monter de niveau).

> A1, B1, C1, D2 me semble mieux, on utilise ce qui existe déja au lieu de
> refaire quelque chose de similaire a coté. E on est d'accord qu'une épreuve
> est une quest? explique avec des exemples. F1 je ne veux pas avoir a créer
> les offres moi-même, je veux les relire, les modifié au besoin et les
> confirmer. G1, H1, I1. Le silence me conviens dans ce cas là.

> E1, ok pour les sous-choix

## Clarifications resolved (intake)

- A trial is a quest: an ordinary offer -- giver, eligibility, steps,
  completion and failure conditions, costs and rewards -- one of whose
  rewards is « the next rank in this skill ». The engine knows no trial as
  such: only that a rank may ask one, and that this reward is offered only
  to a character ready for that rank.
- Nothing game-specific lives in code: whether a rank asks a trial is data
  (the world's ladder, a system, a skill), and what a trial asks is the
  offer's own conditions and terms.
- A new world asks no trial anywhere until its creator says so: existing
  worlds behave exactly as today.
- A point reward on a skill that waits for its trial gives nothing, and
  nothing warns the creator in the offer editor (« le silence me convient »).

## Decisions locked (do not re-litigate without Nia)

- **A1** -- points first: at the threshold of a rank that asks a trial the
  rank does not rise; the skill is « ready »; the trial, declared
  accomplished, raises it. Rejected: A2 (the trial first, unlocking the
  rank; reactivation: entry trials, « admitted before learning »), A3 (the
  trial replacing the points: two ways to one rank).
- **B1** -- « this rank asks a trial » follows the thresholds' cascade: the
  world per rank, a system, a skill; empty inherits; no trial by default.
  Rejected: B2 (per skill only), B3 (per world only).
- **C1** -- the points stop at the threshold while the rank waits; they
  restart at 0 when the rank rises (U2). Rejected: C2 (points carried over,
  against U2).
- **D2** -- the trial's reward is a sixth term currency, `rank`, in the
  existing term tables: the editor, the quest's copy and « déclarer
  accomplie » are reused. Rejected: D1 (trial columns on the offer, a
  second mechanism beside the terms), D3 (a « ready » leaf in the
  eligibility, removable).
  - **D2-a** -- a rank is a reward only: never a cost, a debt or a service.
  - **D2-b** -- the term names the rank it gives; it applies only to a
    character ready for exactly that rank.
  - **D2-c** -- a character no longer ready at settlement: the reward is
    « sans effet », the rest applies.
  - **D2-d** -- the two term tables are rebuilt (migration).
- **E1** -- a trial names one skill (a base domain or a skill definition)
  and one rank. Deferred: E2 (a trial over a whole system or any skill,
  the skill chosen at acceptance; reactivation: the creator often rewrites
  the designer's proposals into one trial common to several skills).
- **F1** -- a player character becoming ready opens a quest request; the
  designer of TICKET-0121 proposes the trial; Nia reviews, edits and
  confirms it. Rejected: F2 (shown only, Nia writes the offers herself),
  F3 (nothing shown).
  - **F1-a** -- one request per skill and rank in the world, not per
    character, born when a skill becomes ready and no open offer gives that
    rank in that skill.
  - **F1-b** -- `quest_request` rebuilt: its day and step optional, a
    `trial` trigger with its skill and rank; no existence question.
  - **F1-c** -- the player sees « épreuve de rang à passer » on the fiche,
    nothing of the request; the offer reaches Journée once confirmed.
- **G1** -- the code imposes no giver and no master; the creator writes
  « a rencontré un Maître » or anything else in the eligibility. Rejected:
  G2 (the giver at least at the target rank: some worlds have no masters).
- **H1** -- a trial fails like any quest (the failure condition shown, the
  quest abandoned), its offer repeatable by default; the points stay at the
  threshold. Deferred: H2 (a failure costs points or a rank; reactivation:
  Nia asks for it after playing).
- **I1** -- whoever earns points faces trials: player characters. The
  creator's own rank edit on the fiche passes over any trial, as every
  creator correction does. Rejected: I2 (NPCs: they earn no points in play).

## Carried forward / open

- **E2** and **H2** -- deferred above; not entered in « Suivi » (only the
  deferrals Nia names, with a condition she approves, are -- L of 0115).
- **The day's account** (`routes/day._account_gains`) lists a point for a
  rolled step even when the skill waited and took nothing (drafting
  decision 11). `routes/day.py` is at its budget; a fix is its own small
  ticket if the line misleads in play.
- **A trial request after a creator's rank edit** stays open until she
  sets it aside (drafting decision 14).
- **TICKET-0120** (the calendar) follows (P1 of 0114).

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] v2.29: the trial columns, the `rank` currency's CHECKs, the trial request's shape, the migration  -> verify/checks/rank_trial_schema.py
- [ ] The cascade, the waiting threshold, the rank reward, the gate, the trial request, the designer's trial, the surfaces  -> verify/checks/rank_trials.py
- [ ] Every check of the corpus  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] After a backup, `migrate_v2_29_rank_trials.py` on a copy of the
      production database, then on production: « Migration v2.29 applied »;
      `apply_ticket_0116_trial_prompt.py` reports `created` once; the
      cockpit boots.
- [ ] Création › Compétences › Rangs du monde: tick « Épreuve pour passer
      au rang suivant » on Confirmé; save. A skill of a system set to
      « Sans épreuve » for Expert keeps rising by points alone.
- [ ] A player character's skill at Confirmé, one point from the threshold:
      a roll in Play -- the fiche reads « … / … pts · épreuve de rang à
      passer »; another roll gives no point; the rank stays Confirmé.
- [ ] « Demandes de quête » shows one « épreuve de rang » request;
      « Concevoir » -> a proposal in the queue with « ÉPREUVE », its terms
      ending « Passer au rang « Expert » en « … » (épreuve) », repeatable.
      Removing that reward and approving -> « Cette épreuve doit garder sa
      récompense de rang. »; restoring it, choosing a giver and approving
      writes the offer.
- [ ] Journée › Quêtes: the offer is listed for the ready character (once
      he meets its eligibility), not for a character whose skill is not
      ready; accept; « Déclarer accomplie » -> the skill is Expert, 0
      points.
- [ ] A new world created after the migration: no rank asks a trial; a
      skill rises by points alone.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |

## Escalations

### E-01 — D1-d — F

**Context:**
BRIEF-0116-F executed and committed (47d6cd2); rank_trials.py PASS (TB-TF), live check on a throwaway v2.29 DB PASS. /verify ran twice, both verdicts identical: rank_trial_schema.py PASS; rank_trials.py PASS; corpus_gate.py FAIL "SUMMARY: 1 check(s) failed (0 environment, 0 crash, 0 timeout, 1 other)". The one failing check: "FAIL: pipeline_state.py â€” FAIL: TICKET-0124-world-premise.md: Machine-checkable arrow 'draft_panel.py' does not resolve to an existing file under tooling/verify/checks/". TICKET-0124-world-premise.md is an untracked file in tooling/tickets (deposited for the next ticket, not part of this branch's commits); draft_panel.py is a check its own briefs will create. No fix is possible inside BRIEF-0116-F's Scope IN, so the retry (retry_count 1) re-ran verify unchanged.

**Question:**
How should TICKET-0116's verify be made green given that the only red check comes from the untracked TICKET-0124 ticket file?

**Options:**
A) Run /verify with the untracked TICKET-0124 artifacts (ticket, lot, briefs) moved outside the repository for the run and restored right after -- the verdict then reflects exactly what this branch commits; then open the PR. B) Nia removes or adjusts TICKET-0124-world-premise.md herself (e.g. until its lot starts), then /pipeline TICKET-0116 is re-run. C) An amendment to pipeline_state.py (e.g. tolerate a pending check named by a ticket whose status is intake/brief) -- a separate decision, outside this ticket.

**Response:**
