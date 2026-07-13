# BRIEF — Step "Structured editors to relational tables + json_ui_boundary verify check"

## Context

Final TICKET-0025 step. Three JSON columns hide behind structured UI
editors: `npc_goal.prerequisites` (chips editor, BRIEF-0024-a),
`event.involved_entities` (chips editor, H2 — a JSON array of entity ids
with no FK integrity), and `prompt_template.variables` (declared-variable
list validated against template text). All three migrate to relational
tables (E1). This brief then delivers the actual point of the ticket: a
fail-closed verify check, `json_ui_boundary`, that makes "no UI-visible
data in JSON" a structural property of the codebase instead of a CLAUDE.md
note — every surviving JSON column is a named, justified exception living
as code in the check file.

## Scope IN

1. `src/world_engine/models.py` — new table `GoalPrerequisite`
   (`__tablename__ = "goal_prerequisite"`):
   - `id` (uuid pk), `world_id` (FK world.id, not null), `goal_id` (FK
     npc_goal.id, not null), `type: str` with
     `CheckConstraint("type IN ('relation_gte')", name="ck_goal_prerequisite_type")`,
     `target_entity_id` (FK entity.id, not null), `threshold: int` with
     `CheckConstraint("threshold BETWEEN 1 AND 100", name="ck_goal_prerequisite_threshold")`.
   - Unique index on `(goal_id, type, target_entity_id)` — one gate per
     (type, target) pair.
   - Comment: closed vocabulary (K1) enforced by CHECK, extension = new
     enum value in a migration, never a free string.
   Remove `NpcGoal.prerequisites`.

2. `src/world_engine/models.py` — new link table `EventEntity`
   (`__tablename__ = "event_entity"`): `id` (uuid pk), `event_id` (FK
   event.id, not null), `entity_id` (FK entity.id, not null), unique index
   on `(event_id, entity_id)`. Remove `Event.involved_entities`. Comment:
   replaces the FK-less JSON id array; membership queries become joins.

3. `src/world_engine/models.py` — new table `PromptVariable`
   (`__tablename__ = "prompt_variable"`): `id` (uuid pk),
   `prompt_template_id` (FK prompt_template.id, not null), `name: str`,
   unique index on `(prompt_template_id, name)`. Remove
   `PromptTemplate.variables`.

4. `src/world_engine/writes.py`:
   - `write_npc_goal_prerequisites` keeps its signature and full-replace
     contract but writes `goal_prerequisite` rows. History is sacred: it
     STILL snapshots the previous prerequisite list (serialized from the
     old rows) into `npc_goal.change_history` before replacing — the audit
     trail location does not move.
   - `write_event` keeps its `involved_entities: Optional[list]` parameter;
     it inserts `event_entity` rows after the event row.
     `write_event_update` handles the replace case the chips editor uses.
   - Prompt-template create/update path writes `prompt_variable` rows
     (full replace on update).

5. Readers rewired, output-identical:
   - `src/world_engine/tick.py` ~145: prerequisite iteration reads
     `goal_prerequisite` rows for the goal (per-NPC briefing text
     unchanged for equivalent data).
   - `src/world_engine/cockpit/app.py` ~1295 and ~1748: the completion
     judge and the effects/prereq interaction read rows; the anti-double-
     count strip rule (H1) logic is untouched — only its data source moves.
   - `src/world_engine/tick.py` ~643: the faction event filter becomes a
     join/EXISTS on `event_entity` instead of a Python `in` over a JSON
     list.
   - `src/world_engine/analyzer.py` ~329 passes the same list into
     `write_event` (no change beyond what 4 requires).
   - Goal detail / event detail / prompt detail API responses keep their
     current client shapes (`prerequisites` list, `involved_entities` list
     of `{id, name}`, `variables` list of strings) assembled from rows —
     zero client-side JS changes required in index.html for goals and
     prompts; the events chips editor changes only if its endpoint payload
     shape must change (it should not).

6. Migration script `scripts/migrate_vX_YY_structured_editor_tables.py`,
   ONE transaction, idempotent, fail-closed validation pass first
   (malformed prerequisite items or non-list involved_entities abort with
   ids listed). Copies: prerequisites list items -> `goal_prerequisite`
   rows; involved_entities ids -> `event_entity` rows (ids that no longer
   resolve to an entity are SKIPPED and listed in the migration log, not
   fatal — historical events may reference deleted-world debris);
   variables -> `prompt_variable` rows. Then drops the three JSON columns
   (SQLite >= 3.35 guard).

7. NEW verify check `tooling/verify/checks/json_ui_boundary.py`,
   fail-closed, wired into `run.py` like the existing checks. Three
   volets:
   a. CRUD registry volet: parse
      `src/world_engine/cockpit/crud.py`; any field dict with
      `"kind": "json"` in `ENTITY_BASE_FIELDS` or `ENTITY_TYPE_REGISTRY`
      -> FAIL. Allow-list: EMPTY.
   b. Source-access volet: regex scan of `src/` for `metadata_` attribute
      access and `Column("metadata"` declarations -> FAIL on any hit
      outside comments. Allow-list: EMPTY. (Regression guard: the column
      died in -a; this keeps it dead.)
   c. JSON-column volet: parse `src/world_engine/models.py`; every
      `Column(JSON` occurrence must match a named allow-list entry declared
      at the top of the check file, one line each with justification,
      verbatim:
      ```python
      JSON_COLUMN_ALLOWLIST = {
          # Polymorphic model-proposal envelope; rendered readonly in the
          # review queue; shape is the mutation type's contract, not a UI
          # field. First structured UI consumer must relationalize.
          "ProposedMutation.payload",
          # Append-only audit snapshots — never rendered in any UI surface.
          "Relation.change_history",
          "Knowledge.change_history",
          "NpcGoal.change_history",
          "Skill.change_history",
          "Agenda.change_history",
          "AgendaStep.change_history",
          # Internal engine snapshots — never rendered in any UI surface.
          "PassPlay.injected_context",
          "PassPlay.history",
          "Conversation.injected_context",
          "Conversation.scene_state",
          "Visit.present_npc_ids",
          # No UI consumer today. The FIRST UI consumer of any of these
          # MUST migrate it to relational storage in the same brief.
          "Event.consequences",
          "Artifact.known_properties",
          "Artifact.actual_behavior",
      }
      ```
      Any JSON column absent from the allow-list -> FAIL; any allow-list
      entry whose column no longer exists -> FAIL (stale exceptions rot).
   Zero parsed columns/fields found by a volet -> FAIL (fail-closed: a
   parse that finds nothing is a broken parse, per run.py doctrine).

8. `CLAUDE.md`: add one invariant line under the invariants section:
   `UI-visible data is never stored in JSON — relational tables/columns only; enforced fail-closed by verify check json_ui_boundary (exceptions live as code in that file, each justified).`
   The TICKET-0024 RECON lesson line (trace UI fields to storage including
   JSON keys) STAYS — it protects RECON; the check protects the codebase.

9. `ARCHITECTURE_DECISIONS.md`: full TICKET-0025 decision record — the
   rule, the incident that motivated it (0024 duplication), the locked
   options (A1/B1/C1/D1/E1/F1/G1/H1), the exception registry mirroring the
   allow-list with justifications, and the standing consequence: adding a
   JSON column now requires editing the check's allow-list — a visible,
   reviewable diff, never a convention.

## Scope OUT

- No new prerequisite types (`relation_gte` stays the whole vocabulary) —
  the CHECK constraint documents the extension point; extending it is a
  future ticket.
- No UI changes to the goals chips editor, prompts tab, or events chips
  editor beyond what identical API shapes require (target: zero JS diff
  for goals and prompts).
- No backfill of `event_entity` for name-resolution improvements — tick.py
  name->id resolution (~928) keeps its current drop-and-note behavior.
- No `position` column on `goal_prerequisite` or `prompt_variable` — no
  order semantics exist today.
- No relationalization of the Group 4 allow-list columns — that is the
  point of the allow-list.
- No extension of `single_canon_write` or other existing checks in this
  brief — `json_ui_boundary` is a new file; do not refactor the harness.
- The future NPC relation graph (TICKET-0023) reads relations, not these
  tables — no anticipatory columns.

## Invariants to defend

- History is sacred: the prerequisite snapshot into
  `npc_goal.change_history` must survive the storage move (Scope IN 4) —
  losing it would silently break the append-only audit contract of
  BRIEF-0024-a.
- Closed vocabulary (K1): the prerequisite type CHECK constraint replaces a
  code-side validation as a structural guard — writes.py keeps validating
  too (defense in depth), but the schema is the invariant.
- `proposed_mutation` is the only gate to canon: the completion judge
  rewiring (app.py ~1748) must not create a new write path — it reads rows,
  judges, and the existing apply path mutates.
- Fail-closed verify: json_ui_boundary follows run.py doctrine — zero
  findings by a parser is a FAIL, not a pass.
- Structural over disciplinary: the ARCHITECTURE_DECISIONS record must
  state that exceptions are code (allow-list edits), not prose.

## Done means

- [ ] Migration on a live-DB copy completes; re-run is a no-op; the three
  JSON columns are gone from `PRAGMA table_info`; row counts match
  pre-migration list lengths (unresolvable event entity ids listed in the
  log, count reported).
- [ ] Goal prerequisites chips editor: add and remove a `relation_gte`
  gate; rows appear in `goal_prerequisite`; `npc_goal.change_history` gains
  a snapshot entry on each replace.
- [ ] Completing a goal with an unsatisfied prerequisite is still refused
  by the judge; satisfied -> completes; the H1 strip rule still fires
  (existing `h1_strip_bounded` and `prereq_judge` checks green).
- [ ] Events chips editor round-trips; `event_entity` rows match; the
  faction tick event filter returns the same events as pre-migration for
  the pilot data.
- [ ] Prompts tab declared-variables validation renders identically;
  `prompt_variable` rows back it.
- [ ] `python tooling/verify/run.py` green, `json_ui_boundary` listed in
  the results.
- [ ] Negative tests for the check: (1) a scratch branch adding a
  `"kind": "json"` field to the CRUD registry -> check FAILS naming the
  field; (2) a scratch `Column(JSON)` on any model not in the allow-list ->
  FAILS naming it; (3) deleting a real allow-list column while keeping its
  entry -> FAILS as stale.
- [ ] Live deployment sequence: `python scripts/backup.py` -> migration ->
  verify run -> live smoke (goal gate + event chips + prompt validation).
- [ ] /review-step and /close-step runs.

## Docs to update

- `world-engine-schema-changelog.md`: entry — `goal_prerequisite`,
  `event_entity`, `prompt_variable` created; three JSON columns DROPPED.
- `world-engine-schema.md`: bump `Current schema version:` header only.
- `ARCHITECTURE_DECISIONS.md`: full TICKET-0025 record (Scope IN 9).
- `DECISIONS_INDEX.md`: index line for the new record.
- `CLAUDE.md`: the one invariant line (Scope IN 8) — respect the line
  budget; if over, the executor reports rather than trimming other lines.
