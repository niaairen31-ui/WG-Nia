---
id: TICKET-0021
title: Intrigues — entity-sheet page contract membership + AI creation assistant
type: feature
status: live-gate
created: 2026-07-09
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]      # -b seeds a new prompt template head; no migration
blast_radius: medium
brief_ids: [BRIEF-0021-a, BRIEF-0021-b]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

« Je veux regarder les intrigues. deux choses spécifiquement. Premièrement, je
veux que que la page ai le même rendu que mes pages d'entités. Je ne veux pas
que cela soit un hazard, j'aimerais utilisé le contrat de page si possible.
Ensuite, je veux avoir la possibilité d'utiliser mon outil d'aide à la
création comme toutes les autres choses (AI). Je veux qu'il fonctionne comme
les autres. »

## Clarifications resolved (intake)

- **A1** — Intrigues migrates onto the `entity` archetype of the CRÉATION
  page contract via declared seams: `listLoader` (existing seam) plus ONE new
  contract seam `sheetRenderer` (default `authorRenderSheet`). Justified by
  the second concrete non-entity reader of the shell (minimal-first
  satisfied). **A3** (full data-source generalization of the shell) is noted
  as an aspiration, reactivable on a third concrete case — not built now.
- **B1** — AI assistant is a standalone sibling generator
  (`generate_agenda_draft`, the `generate_npc_goals` precedent), NOT a
  `_TYPE_FIELDS` entry: agendas are not `entity` rows. Creator describes an
  intent in one sentence; the assistant pre-fills the create form (the
  "coquille"); accept goes through the EXISTING `POST /api/agendas` — the
  generator writes no canon.
- **C1** — Draft content = title + 2 to 5 steps (mirror of the manual form).
  **C2 deferred explicitly**: suggested goal links in the draft are scope
  OUT, to revisit when goal-name resolution has a concrete design.
- **D1** — Creator selects the owner FIRST; the assistant generates in
  context (owner name + public description + philosophy/backstory injected).
  Model never proposes the owner (D2 rejected).
- Sheet capabilities are frozen at today's API surface: status transitions
  and link detach only. No title edit, no step add after creation — explicit
  scope OUT, revisit on demand.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] CREATION_TABS `intrigues` entry has `archetype: 'entity'` and `containers: ['creation-editor-area']`; no element id `creation-intrigues` remains in index.html  ->  verify/checks/page_contract.py
- [ ] `showCreationSubTab` body still contains no tab-id string literal and no per-tab conditional after the sheetRenderer seam lands  ->  verify/checks/page_contract.py
- [ ] `entity_author.generate_agenda_draft` exists, and `writes.` / `session.add` / `db.add` never appear inside its body (generate-and-return, no canon)  ->  verify/checks/agenda_assist.py
- [ ] `pt-agenda-draft` upsert present in scripts/seed_pilot.py with usage `agenda_generation` and variables `owner_kind, owner_name, owner_context, brief`  ->  verify/checks/agenda_assist.py
- [ ] Route `POST /api/agendas/generate` registered in the cockpit app  ->  verify/checks/agenda_assist.py

### Live  ->  human gate (Nia)
- [ ] The Intrigues tab renders the shared list+detail shell: agenda list left, sheet right, visually consistent with NPC/Lieux/Factions
- [ ] Clicking an agenda opens its sheet: title, owner badge (personnelle/faction), status, steps with ✓/✗/▶ actions, linked goals with detach — all behaviours identical to before the migration
- [ ] World switch clears the intrigues list, selection, and any draft form state (G1)
- [ ] "+ Nouvelle intrigue" opens the create panel in the detail pane; selecting an owner, typing an intent, and clicking "Générer" pre-fills title + steps; editing then creating produces the agenda through the normal path; step 1 is born active
- [ ] "Générer" without an owner selected shows « Propriétaire requis. » and touches nothing
