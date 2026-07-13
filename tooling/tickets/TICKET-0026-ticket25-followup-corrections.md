---
id: TICKET-0026
title: TICKET-0025 follow-up corrections — classify config tables into canon, remove dead region-roles block
type: bug
status: live-gate
created: 2026-07-13
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []          # no schema change; no migration; no destructive data op
blast_radius: small
brief_ids: [BRIEF-0026-a, BRIEF-0026-b]
schema_version_touched:   # none
retry_count: 1
---

## Request (verbatim, as Nia stated it)

Ticket 0026 : correction de certains éléments découvert dans l'implémentation
du ticket 0025 (implémenté et mergé). RECON via github sur le code réel, puis
deux briefs de correction.

1. `npc_price` / `location_subculture` / `world_law` font des full-replace
   hard-deletes hors de `canon_write_policy.txt` et hors de la liste fermée de
   CLAUDE.md, contrairement à `faction_role`. Lecture : incohérence non
   intentionnelle — un petit brief de suivi pour les ajouter à
   `[CANON_TABLES]`/`[ALLOWED_SITES]` et à la liste fermée serait cohérent avec
   « exclusion structurelle, jamais disciplinaire ».

2. Bloc `roles` mort dans `commit_region` Stage 1 : `entity_data["metadata"] =
   {"roles": roles}` sur une colonne `metadata` désormais droppée. Pourrait
   être un vrai trou fonctionnel (rôles de faction générés par région perdus au
   commit) plutôt que du simple code mort — à confirmer après lecture du code
   réel. Lean initial : écrire vers `faction_role` dans la même transaction
   plutôt que suppression sèche.

## Clarifications resolved (intake)

RECON-0026 fetched `main` at schema v1.79 and settled both points against live
code:

- **Issue 1 confirmed.** `faction_role` is canon + allowlisted + named in the
  closed list; the three new tables are in neither `[CANON_TABLES]` nor
  `[ALLOWED_SITES]` nor the closed list, so `single_canon_write.py` ignores
  their full-replace deletes by construction. The same gap also affects
  `goal_prerequisite` and `event_entity` (report only). Root cause: no
  completeness guarantee that every table is classified into a K1 stratum.
  -> Decision **F**: BRIEF-0026-a scope. **F1** (three named tables) recommended
  and taken; F2 (add the two extra children) / F3 (F1 + completeness check)
  offered.

- **Issue 2 re-framed by RECON.** The block is still present and is genuinely
  dead: `metadata` is not in `ENTITY_BASE_FIELDS`, so the key is read by no one
  (silent discard, no error). Decisively, NO accept/create path writes
  `faction_role` — the single-entity faction accept path ALSO discards drafted
  roles. The two commit paths are already symmetric. "Persist in region-commit"
  would create a new asymmetry, not restore parity.
  -> Decision **E**: **E1** (remove the dead block; symmetric, zero behavior
  change) recommended and taken; E2 (persist drafted roles in BOTH paths via
  `_create_entity_core` — a feature, own decisions) offered.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `single_canon_write.py` stays green with `npc_price`,
      `location_subculture`, `world_law` in `[CANON_TABLES]` and their three
      `writes.py` chokepoints in `[ALLOWED_SITES]`  ->  verify/run
- [ ] Negative proof: a temporary stray `DELETE FROM npc_price` outside the
      allowlisted helper turns `single_canon_write.py` RED (reverted after)  -> verify/checks/single_canon_write.py
- [ ] `grep -n 'metadata' src/world_engine/cockpit/app.py` shows no
      `entity_data["metadata"]` assignment in `commit_region`  ->  grep

### Live  ->  human gate (Nia)
- [ ] Commit a region containing a faction whose AI draft declares roles;
      confirm the commit succeeds and behavior is unchanged vs. today (roles
      not auto-persisted; roles editor still the path).
- [ ] CLAUDE.md closed-list and ARCHITECTURE_DECISIONS read correctly after
      the two edits.
