# BRIEF — Step "goal<->agenda links: table, owner unlock, cascade (BRIEF-0020-a-goal-agenda-link-schema-writes)"

## Context

Agendas (v1.72) and NpcGoals ignore each other: no structure ties a
goal to the intrigue it serves, and `write_agenda` locks owners to
factions. This chantier ships the B3 many-to-many link table with soft
detach (FactionMembership.left_at precedent), unlocks `character`-type
agenda owners under a one-active-personal-agenda invariant, and wires
the E2+M1 cascade (last-parent rule) into `write_agenda_status`.
Readers arrive in BRIEF-0020-b/c — this brief is schema + writes only.
danger_class: migration (one new table, expected v1.73) — live
deployment sequence mandatory in Done means.

## Scope IN

1. **Model (`src/world_engine/models.py`)** — place after `AgendaStep`:
   - `GoalAgendaLink`, table `goal_agenda_link`: `id` (uuid pk),
     `world_id` (FK world.id, not null), `goal_id` (FK npc_goal.id,
     not null), `agenda_id` (FK agenda.id, not null), `created_at`
     (datetime, default now UTC), `created_by` (str, not null — e.g.
     `"creator"` or `"mutation:<id>"`), `detached_at` (nullable
     datetime), `detached_by` (nullable str). NO change_history column:
     link rows are immutable facts whose only transition is the soft
     detach, fully audited by the two detach columns; goal-side
     transitions live in npc_goal.change_history.
   - Indexes: `idx_goal_agenda_link_goal (goal_id)`,
     `idx_goal_agenda_link_agenda (agenda_id)`, and PARTIAL UNIQUE
     `idx_goal_agenda_link_active` on `goal_id, agenda_id`,
     `sqlite_where text("detached_at IS NULL")` — no duplicate ACTIVE
     link for the same pair; a detached pair may be re-attached
     (FactionMembership `idx_membership_unique_active` precedent,
     models.py:222-226). Add to `__all__`.

2. **Migration `scripts/migrate_v1_73_goal_agenda_link.py`** (executor
   owns the number; v1.69 idempotent-inspector shape, same as 0018):
   one CREATE TABLE + three indexes including the partial unique. No
   backfill. Re-run must no-op.

3. **Write helpers (`src/world_engine/writes.py`)** — keyword-only,
   caller owns the transaction; the ONLY constructors/mutators of
   GoalAgendaLink in gameplay code:
   - `write_goal_agenda_link(db, *, world_id, goal_id, agenda_id,
     created_by, mutation_id=None) -> GoalAgendaLink` — validates: the
     goal exists AND `status == "active"`; the agenda exists AND
     `status == "active"`; both belong to `world_id`; no ACTIVE link
     for the pair already exists (explicit query — clearer error than
     the index violation). Any failure raises ValueError with a
     one-line reason. `mutation_id` audit-only symmetry param.
   - `detach_goal_agenda_link(db, *, link: GoalAgendaLink,
     detached_by) -> GoalAgendaLink` — sets `detached_at = now UTC`
     and `detached_by`; raises ValueError if already detached. Never
     deletes. There is NO delete helper — soft detach is the only exit.
   - `write_agenda` (writes.py:660-662) owner validation CHANGES to:
     owner must resolve to an ACTIVE entity of `type` in
     `{"faction", "character"}` in this world. IF `type ==
     "character"`: additionally query for any existing Agenda with
     `owner_entity_id == owner` and `status == "active"`; if one
     exists, raise ValueError
     `"character owner already holds an active agenda"` — the
     one-active-personal-agenda invariant, enforced in the sole
     canon-write path. Faction owners keep multi-agenda freedom
     (UNCHANGED — do not tighten).

4. **Cascade (`write_agenda_status`, writes.py:738-764)** — extend the
   existing helper; do NOT create a parallel one:
   - Fires only when the PREVIOUS status is `"active"` and the new
     status is in `{"completed", "failed", "abandoned"}`.
   - For each ACTIVE link of this agenda (`detached_at IS NULL`):
     load the goal; skip unless `goal.status == "active"`.
     LAST-PARENT RULE: skip if the goal has ANY OTHER active link
     (`detached_at IS NULL`) pointing to an agenda with
     `status == "active"` (the agenda being closed is excluded by its
     just-written status; guard explicitly anyway by excluding
     `agenda.id`).
   - M1 mapping: new agenda status `completed` -> goal `completed`;
     `failed` or `abandoned` -> goal `abandoned`.
   - Each transition goes through `write_npc_goal_status(db,
     goal=..., new_status=..., changed_by=f"cascade:agenda:{agenda.id}:{status}")`
     — snapshot discipline preserved, provenance auditable. Links are
     NOT detached by the cascade — the historical tie remains readable.
   - The cascade therefore fires identically for tick-approved
     transitions AND creator CRUD overrides (both route through this
     helper) — intended, per intake.

5. **Docs**:
   - `world-engine-schema.md`: new `goal_agenda_link` section (B3,
     last-parent cascade note, partial index rationale) + changelog
     entry v1.73 (executor owns the number).
   - `ARCHITECTURE_DECISIONS.md` (append-only) three entries:
     (i) TICKET-0020 B3 + last-parent rule + E2/M1 mapping and why
     mechanical cascade is sanctioned (every link passed creator
     review; code judges a reviewed structure);
     (ii) one-active-personal-agenda invariant, guard placement
     (helper-level code guard, same tier as the 0018 faction-type
     check);
     (iii) forward note that the per-NPC contract extension itself is
     logged by BRIEF-0020-b (cross-reference only).

## Scope OUT

- Any reader: no briefing section, no dialogue provenance, no
  agendas_index change, no prompt version (all BRIEF-0020-b).
- No mutation types (`agenda_delegation`, per-NPC agenda types) — b.
- No cockpit surface, endpoint, or UI (BRIEF-0020-c).
- No seed changes.
- No cascade on AgendaStep closure; no `failed` in the goal
  vocabulary (M3 rejected); no change_history on link rows.
- Location-type owners stay rejected by `write_agenda`.

## Invariants to defend

- **Single canon-write paths**: GoalAgendaLink must be constructed
  nowhere but writes.py; the cascade must route through
  `write_npc_goal_status`, never a bare status assignment.
- **History is sacred**: no DELETE on links; cascade snapshots via the
  existing goal helper; detach is additive columns only.
- **Structural over disciplinary**: the active-pair uniqueness and the
  one-personal-agenda rule live in the index and the write helper —
  never in prompt instructions.
- **Minimal first**: no extra link metadata (weights, kinds, notes) —
  no reader exists for any of it.

## Done means

- [ ] `migrate_v1_73_goal_agenda_link.py` runs after backup; table +
      three indexes exist (PRAGMA/inspector proof); immediate re-run
      no-ops.
- [ ] `write_agenda` accepts an active character owner; a SECOND
      active agenda for the same character raises ValueError; faction
      multi-agenda behaviour unchanged (regression check).
- [ ] `write_goal_agenda_link` rejects: inactive goal, inactive
      agenda, cross-world pair, duplicate active pair. Detach then
      re-attach of the same pair succeeds (partial index proof).
- [ ] Closing an agenda with two linked goals — one single-parent, one
      also linked to another still-active agenda — transitions ONLY
      the first (M1 mapping), with `cascade:agenda:<id>:<status>` in
      its change_history snapshot; the second goal untouched; links
      remain attached.
- [ ] `verify/checks/single_canon_write.py` extended: `GoalAgendaLink(`
      only in writes.py; cascade goal writes only via
      write_npc_goal_status. Full suite green: `tooling/verify/run.py`.
- [ ] /review-step and /close-step run (engine code touched).

## Docs to update

Covered in Scope IN item 5 — schema section + changelog v1.73
(executor owns the number) + three ARCHITECTURE_DECISIONS entries.
