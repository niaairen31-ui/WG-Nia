# BRIEF — Step "skill_system schema and CRUD"

## Context

The skill catalogue (`skill_definition`, v1.63) has no way to say that several
skills belong to one body of rules, so magic has no structural home: the word
appears across `world.magic_status`, `location.magic_status`,
`faction.magic_knowledge_level` and the `magic` entity type, all narrative,
none mechanical. Rather than add a fifth base domain — `resolve_physical` does
not read `domain` in its math, so a fifth buys nothing and breaks the standing
"strictly physical/sensory" guard — magic becomes one instance of a
world-authored `skill_system`. This step lands the table, the attachment
column, the migration, and the CRUD that authors them. Its reader ships in
BRIEF-0084-b, one commit later.

## RECON (measured by Claude against `main` before writing this brief)

Every anchor below is [M] — read from a fresh tarball of `main` at schema
v2.00. Line numbers are for orientation; match on the quoted text, not the
number.

- [M] `BASE_SKILL_DOMAINS = ("physical", "agility", "perception", "composure")`
  — `src/world_engine/models/canon.py:608`.
- [M] `class SkillDefinition` — `src/world_engine/models/canon.py:614-631`.
  Current `__table_args__`: `CheckConstraint("base_domain IN
  ('physical','agility','perception','composure')",
  name="ck_skill_definition_base_domain")`, `Index("idx_skill_definition_world_name",
  "world_id", "name", unique=True)`, `Index("idx_skill_definition_world",
  "world_id")`. Fields: `id`, `world_id`, `name`, `base_domain`, `description`
  (commented "authored in chantier 2, not read this round"), `created_at`,
  `updated_at`.
- [M] `class Skill` — `src/world_engine/models/canon.py:638`. Not touched by
  this step.
- [M] CRUD to mirror — `src/world_engine/cockpit/crud/skills.py`:
  `_skill_definition_dict` at 157, `GET /skill-definitions` at 168,
  `SkillDefinitionWriteBody` at 179, `POST /skill-definitions` at 185,
  `PUT /skill-definitions/{definition_id}` at 236,
  `DELETE /skill-definitions/{definition_id}` at 286. The module imports its
  router from `._router` and `_get_entity, _iso, _world_id` from `._shared`.
- [M] `POST /skill-definitions` backfills a tier-0 `skill` row onto every
  player character of the world in the SAME transaction, and rejects a `name`
  whose lowercase form is in `BASE_SKILL_DOMAINS` (422) and a `base_domain`
  outside it (422); a duplicate name raises 409 off `IntegrityError`.
- [M] `DELETE /skill-definitions/{id}` deletes dependent `skill` rows first,
  then the definition, so the declared `ON DELETE RESTRICT` on
  `skill.skill_definition_id` never fires.
- [M] Migration template — `scripts/migrate_v2_00_connects_to_facts.py`:
  module docstring stating scope/idempotence/post-checks, `SRC` path insert,
  and a fail-closed refusal to run unless `WORLD_ENGINE_ENV` or
  `WORLD_ENGINE_DATABASE_URL` is set (TICKET-0049).
- [M] Column-drop and column-add precedent on this schema:
  `scripts/migrate_v1_40_drop_character_faction_id.py`, v1.78
  (`location.coordinates` dropped), v1.79 (`npc_goal.prerequisites` and
  `event.involved_entities` dropped).
- [M] Verify checks live in `tooling/verify/checks/*.py`.
- [M] Version rollover rule in force since TICKET-0082: `MINOR=99 ->
  MAJOR+1, MINOR=00`. Current version is v2.00, so this step is **v2.01**.
- [I] No existing table or column already expresses "a body of skill rules".
  Searched `skill`, `system`, `discipline`, `school` across `src/models/`.

## Scope IN

1. **`src/world_engine/models/canon.py` — new model `SkillSystem`**, placed
   immediately BEFORE `class SkillDefinition` (so the FK target is declared
   first and reads top-down):

   ```python
   # -------------------------------------------------------------------------
   # skill_system  (world-authored body of skill rules — magic, technology,
   # ritual, ... ; schema v2.01, TICKET-0084)
   # -------------------------------------------------------------------------
   class SkillSystem(SQLModel, table=True):
       __tablename__ = "skill_system"
       __table_args__ = (
           Index("idx_skill_system_world_name", "world_id", "name", unique=True),
           Index("idx_skill_system_world", "world_id"),
       )

       id: str = Field(default_factory=_uuid, primary_key=True)
       world_id: str = Field(foreign_key="world.id", nullable=False)
       name: str
       description: Optional[str] = None  # rendered as the group subtitle (F2)
       created_at: datetime = _created_ts()
       updated_at: datetime = _created_ts()
   ```

   No `status` column, no `roll_spec` column, no magic-specific anything. A
   world without magic owns no row of this table.

2. **`src/world_engine/models/canon.py` — `SkillDefinition` gains one field**,
   declared immediately after `base_domain`:

   ```python
   system_id: Optional[str] = Field(
       default=None,
       foreign_key="skill_system.id",
       sa_column_kwargs={"ondelete": "RESTRICT"},
   )  # the body of rules this skill belongs to; NULL = unaffiliated (v2.01)
   ```

   Nullable is deliberate: the existing catalogue predates systems and every
   current row must remain valid.

   Add to `SkillDefinition.__table_args__`, keeping the three existing entries
   untouched:

   ```python
   Index("idx_skill_definition_system", "system_id"),
   ```

   `ck_skill_definition_base_domain` is NOT modified. Its four literals stay
   exactly as they are.

3. **Export both names** wherever `SkillDefinition` is already exported —
   `src/world_engine/models/__init__.py` — adding `SkillSystem` alongside it in
   the same alphabetical position the file already uses.

4. **`src/world_engine/cockpit/crud/skills.py` — CRUD for systems**, mirroring
   the `skill-definitions` block immediately above it in the same file:

   - `_skill_system_dict(s)` returning `id`, `world_id`, `name`, `description`,
     `skill_count` (count of `skill_definition` rows with `system_id == s.id`),
     `updated_at` via `_iso`.
   - `GET /skill-systems` — the active world's systems, ordered by `name`.
   - `class SkillSystemWriteBody(BaseModel)`: `name: str`,
     `description: Optional[str] = None`.
   - `POST /skill-systems`, status 201 — `name.strip()`; empty name -> 422 with
     the message `name is required`; duplicate name in the world -> 409 off
     `IntegrityError` with the message
     `A skill system named {name!r} already exists in this world`. No backfill
     of any kind: creating a system never touches `skill` or
     `skill_definition`.
   - `PUT /skill-systems/{system_id}` — same body, same validation, 404 when
     the row is missing or belongs to another world, and it refreshes
     `updated_at`.
   - `DELETE /skill-systems/{system_id}` — **fail-closed, unlike the
     skill-definition delete above it.** If any `skill_definition` still
     carries this `system_id`, refuse with 409 and this exact message:

     ```
     Cannot delete a skill system that still has skills attached — detach or delete them first.
     ```

     This is deliberate asymmetry with `DELETE /skill-definitions`, which
     deletes its dependents: a system is a container the creator authored, and
     silently orphaning her catalogue is worse than making her say it twice.
     Every refusal path returns before any `db.delete`.

5. **`SkillDefinitionWriteBody` gains `system_id: Optional[str] = None`**, and
   both `POST` and `PUT /skill-definitions` accept it. Validation, in
   `create_skill_definition` and `update_skill_definition` alike: when
   `system_id` is not `None`, the referenced `SkillSystem` must exist AND its
   `world_id` must equal the active world, else 422 with the exact message:

   ```
   system_id must reference a skill system of the active world
   ```

   `_skill_definition_dict` gains `"system_id": d.system_id`. The existing
   tier-0 backfill on `POST` is untouched — attaching a skill to a system does
   not change which PCs carry it.

6. **`scripts/migrate_v2_01_skill_system.py`**, written on the shape of
   `migrate_v2_00_connects_to_facts.py`:

   - Same fail-closed env preamble (refuse to run without `WORLD_ENGINE_ENV`
     or `WORLD_ENGINE_DATABASE_URL`, exit 1 with a message naming the script).
   - Creates `skill_system` and its two indexes; adds
     `skill_definition.system_id` and `idx_skill_definition_system`.
   - **Idempotent, per object independently** — check table existence and
     column existence separately, so a partially applied prior run completes
     only the missing parts rather than skipping wholesale (the
     `migrate_v1_80_obstacle_geometry.py` rule).
   - Purely additive: creates zero rows. No world gets a default system, not
     even the pilot.
   - Post-checks before commit: `skill_system` row count is 0; the count of
     `skill_definition` rows is identical before and after; every existing
     `skill_definition.system_id` is NULL.

7. **`tooling/verify/checks/skill_system_shape.py`** — a G1 check asserting:
   `skill_system` exists with exactly the columns listed in item 1;
   `skill_definition.system_id` exists and is nullable;
   `BASE_SKILL_DOMAINS` has exactly four members; the
   `ck_skill_definition_base_domain` constraint text still names exactly
   `physical`, `agility`, `perception`, `composure`. A vacuous pass (zero
   columns collected) is a FAIL, per the `known_reachability.py` rule.

## Scope OUT

Named because they were discussed and deferred, and an executor could
reasonably reach for any of them:

- **`roll_spec`, `status`, `intensity`, or any mechanical column on
  `skill_system`.** Differentiated magic rolls were discussed and explicitly
  parked: the house rules are not decided. `resolve_physical` is not touched.
- **A fifth base domain.** `BASE_SKILL_DOMAINS` stays at four and
  `ck_skill_definition_base_domain` keeps its four literals. Rejected
  decision, not a pending one.
- **The Creation UI.** No Svelte file is touched in this step. Grouping,
  forms, and the system editor are BRIEF-0084-b.
- **`skill_resolution`, the shared resolver, and anything in
  `cockpit/play_physical.py`.** BRIEF-0084-c.
- **The gaps view.** BRIEF-0084-d.
- **`world.magic_status`.** BRIEF-0084-e, its own migration, its own commit.
  Do not touch the column, the model field, or `seed_pilot.py` in this step.
- **The world-creation form.** `WorldCreateBody` is not touched. There is no
  checkbox and no field for declaring magic; systems are authored in Creation.
- **`day_plan.py::_validate_step`** keeps accepting only `null` or a base
  domain. The day chain does not learn about the catalogue in this ticket.
- **Seeding a default system anywhere**, including in `seed_pilot.py`.
- **Backfilling `system_id` on existing `skill_definition` rows.** They stay
  NULL until Nia attaches them by hand.
- **An alias table (C3b).** Deferred with a measurable reactivation condition
  that depends on BRIEF-0084-c's table.

## Invariants to defend

- **"Schema is authoritative."** The model, the migration, and
  `world-engine-schema.md` must agree exactly. Three places, one shape.
- **"Two sanctioned canon-write paths."** `skill_system` is a canon table and
  is written only from creator CRUD. Do not add a write site anywhere else,
  and do not let the migration write rows.
- **The standing design guard** at `world-engine-schema.md` (skill section):
  domains are strictly physical/sensory, social abilities are NEVER skill
  domains. This step does not amend it. `skill_system` is an orthogonal axis
  attached to the catalogue, not a new domain — say so in the schema NOTE.
- **"No structure without a reader."** `skill_system` ships one commit ahead of
  its reader (BRIEF-0084-b's grouping). That gap is deliberate and bounded to
  one step. It is NOT a licence to add further unread columns here.
- **"History is sacred."** The migration is additive only: zero rows created,
  zero rows updated, zero rows deleted. The post-check on
  `skill_definition` row count enforces it.
- **"Minimal first, expand later."** Every column in item 1 either has a reader
  in BRIEF-0084-b or is structural (`id`, `world_id`, timestamps). Nothing
  speculative.

## Done means

- [ ] `python scripts/migrate_v2_01_skill_system.py` runs clean on the dev DB,
      then runs a second time and reports every object already present, exit 0.
- [ ] `sqlite3 <db> ".schema skill_system"` shows the two indexes and the
      column list from item 1, no extras.
- [ ] `sqlite3 <db> "SELECT COUNT(*) FROM skill_system"` returns 0.
- [ ] `sqlite3 <db> "SELECT COUNT(*) FROM skill_definition WHERE system_id IS
      NOT NULL"` returns 0.
- [ ] `POST /api/skill-systems {"name":"Magie"}` returns 201 with
      `skill_count: 0`; the same call again returns 409.
- [ ] `POST /api/skill-systems {"name":"  "}` returns 422.
- [ ] `POST /api/skill-definitions` with a `system_id` belonging to another
      world returns 422 with the exact message from item 5.
- [ ] `POST /api/skill-definitions {"name":"Évocation","base_domain":"composure",
      "system_id":"<the Magie id>"}` returns 201, and every existing PC of the
      world gains a tier-0 `skill` row for it (the pre-existing backfill still
      works).
- [ ] `DELETE /api/skill-systems/<the Magie id>` returns 409 with the exact
      message from item 4, and `SELECT COUNT(*) FROM skill_definition` is
      unchanged afterwards.
- [ ] After detaching the skill (`PUT` with `system_id: null`), the same
      `DELETE` returns 200.
- [ ] `python -m tooling.verify.checks.skill_system_shape` returns PASS.
- [ ] `pytest`, `no_print_in_src.py`, `undefined_names.py`, `import_cycle.py`
      all green.
- [ ] `/review-step` and `/close-step` both run (engine code is touched).
- [ ] One commit. If the verify check needs a fix after `/review-step`, that
      fix is a second commit, not an amend.

## Docs to update

- `world-engine-schema-changelog.md` — new entry **v2.01**, TICKET-0084,
  BRIEF-0084-a, following the house form: the new table with its full column
  list and indexes, the new nullable column with its FK and RESTRICT, the
  migration filename, its idempotence rule, and the explicit statement that it
  creates zero rows.
- `world-engine-schema.md` — bump "Current schema version" to v2.01; add the
  `CREATE TABLE skill_system` block immediately before `skill_definition`; add
  `system_id` to the `skill_definition` block with this NOTE, verbatim:

  ```
  -- system_id: the body of rules this skill belongs to (v2.01, TICKET-0084).
  -- NULL = unaffiliated. A world where magic does not exist simply owns no
  -- magic skill_system row, and therefore no magic skill_definition rows --
  -- existence is row presence, never a flag. This column is an axis ORTHOGONAL
  -- to base_domain: it does not add a domain, and the standing guard (domains
  -- are strictly physical/sensory, social abilities are NEVER skill domains)
  -- is unamended by it.
  ```

- `tooling/standards/ARCHITECTURE_DECISIONS.md` — a section for this step
  recording A3 and B3 as locked, and naming the two rejected alternatives with
  their reactivation conditions: a fifth base domain (reactivates only if a
  magic roll must differ AND that difference cannot live on the system row) and
  D3's feasibility refusal (reactivates the day a world must keep a magic
  catalogue with magic mechanically off).
- `CLAUDE.md` — one line in the skills paragraph noting that a
  `skill_definition` may now carry a `system_id`, and that
  `DELETE /api/skill-systems` refuses while skills are attached, unlike
  `DELETE /api/skill-definitions` which deletes its dependents.
