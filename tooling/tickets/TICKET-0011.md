---
id: TICKET-0011
title: Manual prompt editing with append-only version history
type: feature
status: exec          # BRIEF-0011-a merged (main, PR #11); brief_ids reconciled from disk; BRIEF-0011-b ready for brief-exec
created: 2026-07-04
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: large        # every prompt-text read site in src/ is rewired
brief_ids: [BRIEF-0011-a, BRIEF-0011-b]
schema_version_touched: vX.YY (placeholder — Claude Code owns numbering)
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Je veux pouvoir modifier mes prompts manuellement, le nouveau prompt est
> désormais celui qui est utilisé, j'ai besoin d'avoir l'historique des
> versions.

## Clarifications resolved (intake)

- **A2** — `prompt_template` becomes a head/identity row (name, usage,
  variables, model, destination, is_active, notes). Prompt text lives in
  `prompt_version` rows exclusively. "Current" = highest `version_number`
  for the head — no pointer column.
- **B1** — version rows carry `system_prompt` + `user_template` only.
  `model` and `variables` stay on the head, unversioned. Extending
  versioning to them (**B2**) is explicitly DEFERRED — named in Scope OUT.
- **C1** — fail-closed placeholder validation on save: any simple-identifier
  placeholder `{name}` in the submitted text that is not in the head's
  declared `variables` list → 422, write refused.
- **D1** — restore = append a NEW version whose content copies the restored
  one. History is strictly monotone; no pointer moves, no rewrites.
- **F1** — after migrating current text into `prompt_version` v1 rows, the
  text columns (`system_prompt`, `user_template`, `version`) are DROPPED
  from `prompt_template`. No denormalized cache, no second source of truth.
- **G1** — single pure accessor (`current_prompt(...)`) is the ONLY read
  path for `prompt_version`; wired at every consuming site (loaders,
  assemblers, previews, reader API). Mirrors the `effective_model` pattern.
  Verify: static scan forbids `prompt_version` reads outside the accessor
  module.

## Clarifications PENDING (surfaced by RECON-0011 — must be locked before brief)

- **S — seed vs. creator edits**: `upsert_prompt_template`
  (scripts/seed_pilot.py:125) converges DB text to seed wording on every
  re-seed. Under append-only versioning this collides with creator edits.
  Options S1/S2/S3 in RECON-0011 §5.
- **H — substitution mechanics**: two coexisting mechanisms
  (`str.format()` at 6 sites, chained `.replace()` elsewhere). Creator
  edits make literal `{`/`}` reachable in `.format()`-consumed templates →
  runtime crash class. Options H1/H2 in RECON-0011 §6.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `prompt_version` table exists; UNIQUE(prompt_template_id, version_number)  -> verify/checks/prompt_version.py
- [ ] `prompt_template` no longer has `system_prompt` / `user_template` / `version` columns  -> verify/checks/prompt_version.py
- [ ] Static scan: no `PromptVersion` / `prompt_version` read outside the accessor module  -> verify/checks/prompt_version.py
- [ ] Single write shape: exactly one helper in writes.py writes `prompt_version`; PATCH route and seed both route through it  -> verify/checks/prompt_version.py
- [ ] Save with undeclared placeholder returns 422 and writes nothing (fail-closed)  -> verify/checks/prompt_version.py
- [ ] No UPDATE/DELETE statement ever targets `prompt_version` (append-only by construction)  -> verify/checks/prompt_version.py

### Live  ->  human gate (Nia)
- [ ] Edit a prompt in the cockpit Prompts tab; the very next model call uses the new text (verify via assembled preview — fidelity path, never a duplicate)
- [ ] History list shows all versions, newest first, with timestamps
- [ ] Restore an old version → it appears as a new head version; the intermediate versions remain visible
- [ ] Reject test: save text containing `{typo_var}` → 422, current version unchanged
