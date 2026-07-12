---
id: TICKET-0025
title: Extract all UI-visible fields from JSON storage into relational tables
type: feature
status: brief
created: 2026-07-12
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration, destructive_data]
blast_radius: large
brief_ids: [BRIEF-0025-a, BRIEF-0025-b, BRIEF-0025-c]
schema_version_touched: TBD (executor assigns; one bump per migration brief)
retry_count: 0
---

## Request (verbatim, as Nia stated it)

"Je veux qu'il n'existe plus de champs UI lié a un JSON. Si c'est important
pour un champ, je veux que cela soit justifié spécifiquement pour s'assurer
que c'est la meilleur solution. Je veux que tu identifie tous les champs UI
qui sont lié a un fichier JSON et je veux qu'on les transfère dans la BD."

Motivating incident: the TICKET-0024 duplication bug — RECON failed to
detect a UI field backed by an `entity.metadata` JSON key, producing a
parallel role structure (corrected by BRIEF-0024-d). A CLAUDE.md note is
not accepted as the long-term fix; the rule must be structural.

## Clarifications resolved (intake)

- A1: metadata.physical_tier -> `character` column; metadata.price_list ->
  `npc_price` table; location.coordinates -> `coord_x` / `coord_y` columns.
- B1: character.secrets -> plain TEXT column (no reader, no structure).
- C1: location.subculture -> `location_subculture` table with `is_hidden`
  flag (secret exclusion becomes structural).
- D1: world.fundamental_laws -> `world_law` table (position-ordered rows).
- E1: npc_goal.prerequisites -> `goal_prerequisite` table;
  event.involved_entities -> `event_entity` link table;
  prompt_template.variables -> `prompt_variable` table.
- F1: the raw "Metadata (JSON)" form field is removed and the
  `entity.metadata` column itself is dropped once emptied. Sequencing
  prerequisite satisfied: BRIEF-0024-d is merged (schema v1.76,
  `faction_role` live, `role_capacities` and `metadata['roles']` gone).
- G1: new fail-closed verify check `json_ui_boundary.py` enforces the rule
  structurally (CRUD registry volet + source-access volet + JSON-column
  allow-list volet). Exceptions live as code in the check file with
  per-line justification.
- H1: three briefs — -a (metadata keys + column drop), -b (dedicated JSON
  columns on entity extensions + world), -c (structured editors + boundary
  check + decision record).
- Group 4 columns (proposed_mutation.payload, the six change_history
  columns, conversation/pass_play snapshots, event.consequences,
  artifact.known_properties / actual_behavior) are NOT UI-visible fields
  (payload is a readonly polymorphic envelope; the rest have no UI
  surface). They remain JSON as named, justified exceptions registered in
  BRIEF-0025-c's check allow-list and ARCHITECTURE_DECISIONS entry.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] zero fields with kind json in cockpit CRUD registries  -> verify/checks/json_ui_boundary.py
- [ ] zero entity.metadata accesses in src/  -> verify/checks/json_ui_boundary.py
- [ ] every Column(JSON) in models.py is in the named allow-list  -> verify/checks/json_ui_boundary.py
- [ ] full verify suite green after each brief  -> tooling/verify/run.py

### Live  ->  human gate (Nia)
- [ ] NPC sheet shows Carrure and Tarifs sourced from columns/rows; edits persist
- [ ] map drag persists to coord_x/coord_y; location form has no JSON textarea
- [ ] subculture hidden rows never appear in any prompt preview
- [ ] goal prerequisites chip editor works against goal_prerequisite rows
- [ ] event chips editor works against event_entity rows
- [ ] world creation with one law per line produces ordered world_law rows
