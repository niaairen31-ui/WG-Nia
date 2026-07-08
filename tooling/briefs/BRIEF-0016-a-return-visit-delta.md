# BRIEF — Step "visit table + return-visit delta narration (BRIEF-0016-a-return-visit-delta)"

## Context

TICKET-0015 gave NPCs off-screen movement; nothing yet tells the player the
world moved. This chantier lands G2: an append-only `visit` table anchoring
the player's last entry per location, and a code-computed diff (NPCs
arrived/departed, public events since) injected into the EXISTING
establishment narration at `enter_scene`. The deferral is named in code at
cockpit/app.py:4211-4213 ("no change-detection (G2 deferred)"). Grounding:
RECON-0016 (F1-F8). danger_class: migration — the live deployment sequence
is mandatory in Done means. Executor owns the schema version (expected
v1.71; new-table precedent `scripts/migrate_v1_69_npc_goal.py`).

## Scope IN

1. **Model `Visit` (`src/world_engine/models.py`).**
   `__tablename__ = "visit"`: `id` (uuid pk), `world_id` (FK world.id,
   not null), `player_id` (FK entity.id, not null), `location_id`
   (FK entity.id, not null), `entered_at` (datetime, `_created_ts()`),
   `present_npc_ids` (JSON list of entity ids, `Column(JSON)`).
   `__table_args__`: composite index
   `idx_visit_player_location (player_id, location_id, entered_at)`.
   Append-only by doctrine: no code path updates or deletes a row.
   Added to the models `__all__` export (models.py:886 region).

2. **Migration `scripts/migrate_v1_71_visit.py`** (executor assigns the
   number; v1.69 shape): idempotent CREATE TABLE via inspector +
   CREATE INDEX IF missing; no backfill (table is born empty — every
   location counts as first-visit once, by design). Docstring documents
   that.

3. **Delta helper (`cockpit/app.py`).**
   `_compute_return_delta(db, world_id, player_id, location_id)
   -> tuple[Optional[list[str]], list[str]]` returning
   `(changes_lines_or_None, current_present_npc_ids)`:
   - Latest previous `Visit` for (player_id, location_id) by
     `entered_at DESC`. None -> `(None, snapshot)` (first visit: no delta
     block, snapshot still taken).
   - Current public presence: the tick location-scope predicate VERBATIM
     (cockpit/app.py:4795-4808 — npc, alive, active, world-scoped).
   - `arrived` = current minus previous `present_npc_ids`; `departed` =
     previous minus current. Departed names resolve from `Entity` WITHOUT
     alive/active filters (RECON F5: a dead/deactivated NPC's absence is
     still named; the player saw them, nothing secret is revealed). An id
     that no longer resolves at all is silently skipped.
   - Public events:
     `select(Event).where(Event.world_id == world_id,
     Event.location_id == location_id,
     Event.knowledge_status.in_(("public", "confirmed")),
     Event.recorded_at > previous.entered_at)` — the SAME structural
     filter as the sole existing reader (context.py:533-538); axis is
     `recorded_at` (RECON F4: `occurred_at` is nullable in-fiction time).
     Renders `title` (+ `description` first sentence when present) as a
     line each. Forward-reader: empty today, the perception channel for
     the future event producer.
   - Output lines, French, code-composed:
     `- Parti·e·s depuis votre dernière visite : <names>` /
     `- Arrivé·e·s : <names>` / `- Événement : <title …>` per event.
     All three empty -> return `(None, snapshot)` — a visit with nothing
     to report produces NO block (the prompt never sees an empty header
     to embroider on).

4. **`enter_scene` wiring (cockpit/app.py:4160-4216).**
   Inside the existing `if not open_g:` block (genuine transition —
   RECON F1), AFTER the `left_convs` window-analysis loop and BEFORE
   `_enter_location`: call `_compute_return_delta`; hold the lines; after
   `_enter_location(...)` returns, append the new `Visit` row
   (compute-then-append, RECON F7 — `_enter_location` touches only
   gatherings, the presence read is safe either side, but the PREVIOUS
   row must be read before the new one exists). Outside the block nothing
   changes: re-renders pass `changes=None`. The unconditional
   establishment call (app.py:4214) gains the argument:
   `_build_establishment_narration(location_id, player_id, world_id, db,
   changes=changes_lines)`. Update the app.py:4211-4213 comment (the G2
   deferral is now lifted).

5. **Narration plumbing (cockpit/app.py:2014-2090).**
   - `_build_establishment_narration` gains keyword-only
     `changes: Optional[list[str]] = None`, passed through.
   - `_build_establishment_user` gains the same parameter and replaces a
     new `{changes}` variable: joined lines when non-empty, else
     `(rien de notable depuis votre dernière venue — ou première visite)`.
     Same verbatim `str.replace` mechanism as the four existing
     variables; failure/None anywhere keeps the resilience doctrine
     (narration failure never blocks entry).

6. **Prompt version (`scripts/seed_pilot.py` +
   `scripts/apply_ticket_0016_prompt_updates.py`).**
   New `mj_establishment` version (RECON F3):
   - User template gains a `CHANGEMENTS DEPUIS LA DERNIÈRE VISITE :`
     block carrying `{changes}`, between the signposts block and the
     final cue; `variables` list gains `"changes"`.
   - System prompt: the "AUCUN PNJ NOMMÉ" rule becomes scoped — NPCs
     cited in the CHANGEMENTS block MAY be named (their
     departure/arrival is the information), any presently-present NPC
     still may NOT be named or described; plus an anti-invention clause
     mirroring the signposts rule: if the block reports nothing, mention
     no change and invent none. Length stays 3-4 lines of prose.
   - Seed text updated in place (idempotent upsert);
     `apply_ticket_0016_prompt_updates.py` on the 0015 script pattern —
     append-a-version branch only (the head exists since BRIEF-17),
     no-op when the head's current text already matches.

7. **Verify check `tooling/verify/checks/visit_delta.py`** (RECON F8),
   registered in `run.py`'s fail-closed harness:
   - Rule 1 (append-only + single writer): `Visit(` constructor calls
     appear only in `src/world_engine/cockpit/app.py`; no `db.delete`
     call whose argument resolves to a Visit name; no attribute
     assignment on a Visit-typed target outside the constructor site
     (AST scan, world_tick.py:45-49 allowlist idiom).
   - Rule 2 (structural exclusion): the function containing the delta's
     `select(Event)` references `knowledge_status` within that call
     chain (AST walk over `_compute_return_delta`).

## Scope OUT

- Any Event PRODUCER (tick lane or creator CRUD for events) — the next
  chantier; this brief only ships the reader.
- Signpost/discoverable deltas (already re-narrated fresh via
  `active_signposts` on every entry).
- Journal UI, cross-location news digests, NPC-side visit tracking.
- Visit pruning/retention (append-only; revisit only if measured).
- Any change to gathering generation, `_enter_location`, or the
  idempotent-enter guard's semantics.

## Invariants to defend

- **History is sacred** — `visit` is append-only; no update, no delete,
  enforced by the new check.
- **Exclusion is structural** — the event leg filters
  `knowledge_status IN ('public','confirmed')` at query construction;
  secret events cannot reach the delta regardless of prompt content.
- **Model narrates, code decides** — the diff is computed entirely in
  code; the model receives finished French lines and may only phrase
  them; an empty diff sends no block, so there is nothing to embroider.
- **Resilience doctrine** — establishment (now with delta) may fail or
  be skipped without ever blocking scene entry (existing try/except
  envelope unchanged).
- **B1/C1 enter contract** — visit rows and deltas exist only on genuine
  transitions; F5 re-renders write nothing and reshuffle nothing.
- **No structure without a reader** — `visit` ships with its reader
  (`_compute_return_delta`) in this same brief.

## Done means

Machine gate (`python tooling/verify/run.py`, fail-closed):
- [ ] visit_delta.py rule 1: Visit constructed only in cockpit/app.py; append-only (no delete, no post-construction mutation) -> tooling/verify/checks/visit_delta.py
- [ ] visit_delta.py rule 2: the delta's Event query structurally references knowledge_status -> tooling/verify/checks/visit_delta.py
- [ ] Existing suites still green (world_tick, single_canon_write, page_contract, prompt checks) -> tooling/verify/run.py

Live gate (Nia) — live deployment sequence FIRST (danger_class: migration):
- [ ] Backup script run; `python scripts/migrate_v1_71_visit.py` on the live DB (immediate re-run: no-op); `python scripts/apply_ticket_0016_prompt_updates.py` (immediate re-run: no-op)
- [ ] Enter a location (first visit): normal establishment narration, no invented changes; `visit` has one row with the correct presence snapshot
- [ ] Tick an NPC out of the location (0015 npc_move, approved), re-enter: the narration names the departure; a second `visit` row exists
- [ ] F5 on the scene: no new visit row, no delta in the re-rendered narration
- [ ] Creator-insert an `event` at the location with knowledge_status='secret': absent from the next delta; flip to 'public': present on the following re-entry
- [ ] Enter with nothing changed since last visit: narration mentions no change

## Docs to update

- `world-engine-schema.md` — new `visit` table section + version bump;
  changelog entry extracted to `world-engine-schema-changelog.md`.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` — new section
  "RETURN-VISIT DELTA (BRIEF-0016-a)": G2-over-G1 rationale, the scoped
  naming exception to the establishment rule (F3), recorded_at axis
  choice (F4), departed-names-resolve-regardless-of-status (F5),
  forward-reader stance on the event leg, compute-then-append ordering.
- `CLAUDE.md` — only if its law list enumerates tables or check files;
  freshness contract decides.

## Drafting decisions flagged for Nia (reverse before deposit if wrong)

1. **The MJ model narrates the delta** (new prompt version + scoped
   naming exception). Reverse = code-composed deterministic line
   appended outside the model call — zero hallucination surface, drier
   prose, no prompt change.
2. **The event leg ships now as a forward-reader** (empty until the
   producer exists). Reverse = strip it to the presence diff and add the
   event leg in the producer's brief.
3. **A visit with an empty diff sends NO changes block** to the prompt
   (placeholder only lives in the template default). Keeps the model
   from embroidering "nothing changed" into fake continuity. Reverse =
   always send the block with an explicit "rien de notable".
4. **Departed NPCs are named even if dead/deactivated since** (F5).
   Reverse = filter departures to still-active entities.
5. **No backfill** — every known location counts as first-visit once
   after migration. Reverse = synthesize visit rows from open session
   data (fragile, against G2's own rationale).
