# BRIEF — Step "Schema + creator surface: role capacities & goal prerequisites" (TICKET-0024, BRIEF-0024-a)

## Context

Goal/agenda-step completion is currently purely declarative: `status`
flips, an `outcome` string lands, nothing mechanical moves. TICKET-0024
grounds completion in canon in three briefs. This first brief lays the
schema and the creator-only surface: two nullable JSON columns and their
creator editors. The AI-path consumers arrive in BRIEF-0024-b (prerequisite
judge) and BRIEF-0024-c (effects) — the established sequencing pattern
where an earlier brief ships elements a later brief in the same ticket
fills (0022 precedent). Both columns are documented as
DORMANT-until-0024-b/c in the schema.

## Scope IN

1. **Migration script** `scripts/migrate_vX_YY_completion_mechanics.py`
   (Claude Code assigns the version number), adding:
   - `faction.role_capacities` — JSON, nullable, default NULL. Shape:
     `{"<role name>": <int limit | null>}`. A key present with `null`
     limit = declared, unlimited. Absent map or absent key = (until
     0024-c ships K1) no constraint.
   - `npc_goal.prerequisites` — JSON, nullable, default NULL. Shape:
     `[{"type": "relation_gte", "target_entity_id": "<entity id>",
     "threshold": <int 1-100>}]`. v1 accepts ONLY `relation_gte`.
   Follow the idempotent column-add idiom of
   `migrate_v1_73_goal_agenda_link.py`.
2. **models.py**: add both columns with `Column(JSON, nullable=True)`;
   comment blocks stating DORMANT status and the exact first reader
   (BRIEF-0024-b for `prerequisites`, BRIEF-0024-c for
   `role_capacities`'s AI-path reader; the creator editor in THIS brief
   is their creator-side reader/writer). Include verbatim in the
   `faction.role_capacities` comment:
   `# Capacity counts the true 'role', never 'cover_role'.`
3. **writes.py**: helper `write_faction_role_capacities(db, *, faction,
   capacities: dict, changed_by: str)` — validates keys are non-empty
   strings, values are `None` or `int >= 1`; rejects duplicate keys
   differing only by case (`casefold` collision check); reassigns the
   dict (never in-place mutation — SQLAlchemy JSON change-detection
   rule). `npc_goal.prerequisites` writes go through a new
   `write_npc_goal_prerequisites(db, *, goal, prerequisites: list|None,
   changed_by: str)` that snapshots previous state to `change_history`
   (history is sacred) and validates the v1 shape strictly
   (`type == "relation_gte"`, `target_entity_id` exists in the same
   world, `1 <= threshold <= 100`).
4. **Cockpit — Faction tab capacity editor** (`cockpit/app.py` +
   `index.html`): in the faction sheet, a "Rôles & capacités" section
   using the line-editor pattern (0022 chip-editor family): each line =
   numeric limit field (left, empty allowed) + role name field (right),
   line add/remove. On first open with `role_capacities` NULL, pre-fill
   lines from DISTINCT true `role` values on ACTIVE memberships
   (`left_at IS NULL`) of this faction, limits empty — zero canon writes
   until save. Save = `PATCH /api/factions/{id}/role-capacities` calling
   the writes.py helper. French labels: "Limite" / "Rôle" /
   "vide = illimité".
5. **Cockpit — Goal prerequisites CRUD**: on the goal sheet (Personnages
   tab, goals section), a "Prérequis" block: v1 form = target entity
   picker (characters + factions of the world) + threshold number field
   (1–100), add/remove; writes via
   `PATCH /api/goals/{id}/prerequisites` calling the writes.py helper.
   Display shows the resolved entity NAME, stores the id.
6. **Schema doc** (`world-engine-schema.md`): both columns, shapes,
   DORMANT notes naming their 0024-b/-c readers, changelog entry vX.YY.

## Scope OUT

- NO AI-path reader of either column (that is 0024-b and 0024-c). No
  change to `_apply_mutation`, tick normalization, or prompts here.
- NO capacity enforcement anywhere yet — the editor writes the map, nothing
  reads it to reject.
- NO prerequisite checking anywhere yet.
- NO prerequisite types beyond `relation_gte` (no `ledger_gte`, no
  `role_is`) — deferred until a second concrete case (G-vocabulary).
- NO model-proposed prerequisites (G2 deferred) and NO prerequisites on
  `agenda_step` (G3 deferred).
- NO uniqueness/eviction logic on roles; NO `membership_change`
  (join/leave as effect — I1 deferral).
- Do not "improve" the free-form `role` field on memberships (no enum, no
  FK to the capacity map) — creator CRUD stays free-form by decision K1.

## Invariants to defend

- **History is sacred**: `npc_goal.prerequisites` edits snapshot to
  `change_history`; `faction.role_capacities` is metadata-config category
  (same family as `faction_type` / `philosophy`) — creator-edited, no
  change_history column on `faction`, consistent with existing fields.
- **JSON reassignment rule**: both helpers reassign, never mutate
  in-place.
- **Two sanctioned canon-write paths**: only the two new writes.py helpers
  touch these columns; routes call helpers, never write directly.
- **No structure without a reader**: creator editors are the same-brief
  readers; AI readers named per column in schema DORMANT notes
  (sequenced-ticket pattern).

## Done means

- [ ] Migration runs idempotently twice on a copy of the live DB (second run: no-op)
- [ ] `PATCH /api/factions/{id}/role-capacities` with `{"Président": 1, "Conseiller": 6, "Ambassadeur": null}` persists; GET of the faction sheet shows three lines: `1 / Président`, `6 / Conseiller`, `vide / Ambassadeur`
- [ ] Duplicate-by-case key (`{"chef":1,"Chef":2}`) -> 422 with readable reason
- [ ] Faction with NULL map and two active memberships roled "garde" and "capitaine" -> editor opens pre-filled with those two lines, limits empty; DB still NULL until save
- [ ] Goal prerequisite `relation_gte` threshold 65 targeting an existing entity persists; goal sheet shows entity name + "≥ 65"; `change_history` gained one snapshot
- [ ] Threshold 0 or 101, unknown entity id, or unknown type -> 422
- [ ] `/review-step` and `/close-step` pass (engine code touched)

**Live deployment sequence (danger_class: migration):**
backup (`scripts/backup.py`) -> migration script -> no seed changes -> no
apply-prompt script (no prompt touched this brief).

## Docs to update

- `world-engine-schema.md`: both columns + changelog vX.YY (Claude Code
  assigns number).
- `ARCHITECTURE_DECISIONS.md`: append "TICKET-0024 intake decisions"
  record (A1/B1/G1/H1/I1/C2-J1/K1/L2/M1/N1/E1/F — one-line each; the H1
  atomicity exception gets its full record in BRIEF-0024-c where the code
  lands).
- `CLAUDE.md`: no standing-convention change.
