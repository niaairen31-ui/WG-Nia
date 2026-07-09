# BRIEF — Step "faction agendas: tables, CRUD, tick advancement (BRIEF-0018-a-faction-agendas)"

## Context

The tick produces one-shots: each invocation invents an isolated
advancement with no memory of a plan. This chantier gives factions
AGENDAS — ordered steps with states — read by the faction-scoped event
call (0017), advanced through the queue, authored by the creator or
proposed by the tick (A1/B2 locked). The model references an agenda by
TITLE; the step is code-derived (the unique active one — enforced by a
partial unique index, the idx_membership_one_primary precedent);
advancement logic lives in code at apply. Grounding: RECON-0018 (F1-F8).
danger_class: migration (two new tables, expected v1.72) — the live
deployment sequence is mandatory in Done means.

## Scope IN

1. **Models (`src/world_engine/models.py`)** — NpcGoal shape precedent
   (models.py:338-359), change_history on BOTH:
   - `Agenda`: `id` (uuid pk), `world_id` (FK world.id, not null),
     `owner_entity_id` (FK entity.id, not null — named A2-ready; the
     write helper enforces faction-type owners this step), `title`
     (str, required), `status`
     CheckConstraint `active|completed|failed|abandoned`
     (default/server_default 'active'), `created_at`, `updated_at`,
     `change_history` (JSON NOT NULL '[]').
     Index `idx_agenda_owner_status (owner_entity_id, status)`.
   - `AgendaStep`: `id`, `agenda_id` (FK agenda.id, not null),
     `step_order` (int, not null), `objective` (str, required),
     `status` CheckConstraint `pending|active|completed|failed`
     (default 'pending'), `outcome` (nullable str), `visibility_trace`
     (nullable str), `created_at`, `updated_at`, `change_history`.
     Indexes: `idx_agenda_step_agenda (agenda_id, step_order)`;
     PARTIAL UNIQUE `idx_agenda_step_one_active` on `agenda_id`,
     `sqlite_where text("status = 'active'")` — at most one active step
     per agenda, enforced by SQLite (RECON F2). Both in `__all__`.

2. **Migration `scripts/migrate_v1_72_agenda.py`** (executor owns the
   number; v1.69 idempotent-inspector shape): two CREATE TABLEs +
   the three indexes including the partial unique. No backfill.

3. **Write helpers (`src/world_engine/writes.py`)** — keyword-only,
   `mutation_id` audit param, caller owns the transaction:
   - `write_agenda(db, *, world_id, owner_entity_id, title,
     mutation_id=None) -> Agenda` — validates the owner resolves to an
     ACTIVE entity of `type == "faction"` in this world (A1 structural),
     else raises ValueError.
   - `write_agenda_step(db, *, agenda_id, step_order, objective,
     visibility_trace=None, status="pending") -> AgendaStep`.
   - `write_agenda_step_status(db, *, step: AgendaStep, status,
     outcome=None, mutation_id=None) -> AgendaStep` — appends the
     previous `{status, outcome, updated_at}` to change_history BEFORE
     overwriting (write_npc_goal_status discipline, writes.py:592);
     sets outcome only when provided.
   - `write_agenda_status(db, *, agenda: Agenda, status,
     mutation_id=None) -> Agenda` — same snapshot discipline.
   The ONLY constructors of Agenda/AgendaStep in gameplay code.

4. **Briefing section (tick.py, `assemble_faction_event_context`,
   tick.py:449-533).** New section `AGENDA EN COURS` between POSTURE and
   MEMBRES: for each ACTIVE agenda of the faction — its title, the
   active step's `objective` and `visibility_trace` (when set), and the
   outcomes of the last 2 completed steps (continuity, lean context —
   RECON note 2). Placeholder `(aucune intrigue en cours)`;
   header always present (T1).

5. **Scope-call extension (tick.py:985-1075 + `_normalize_scope_event`).**
   - Faction branch builds `agendas_index` (title.casefold() ->
     agenda_id over ACTIVE agendas of the faction; ambiguous duplicate
     titles removed — `_build_roster` idiom tick.py:285-326). The
     location branch passes `{}` — agenda types become structurally
     unresolvable for location scopes; an explicit
     `scope_type == "faction"` gate guards the branches too (belt and
     braces, both machine-checked).
   - `_normalize_scope_event` grows two branches (aliases in ITS local
     map only; the per-NPC `_TICK_TYPE_ALIASES` / `_TICK_MUTATION_TYPES`
     untouched):
     - `agenda_step_change` — payload in:
       `{"agenda": <title>, "action": "complete"|"fail",
       "outcome": "..."}`. Title resolved via `agendas_index`
       (unresolved -> drop with note); the STEP derived code-side: the
       agenda's unique active step loaded fresh (none -> drop with
       note). Action outside the pair -> drop. Outcome optional string.
       Payload out: `{"agenda_id", "step_id", "action", "outcome"}` —
       ids as bare Names; `.get("step_id")`/`.get("agenda_id")` banned
       (item 8). `target_table="agenda_step"`.
     - `agenda_creation` — payload in: `{"title": str,
       "steps": [2..5 non-empty objective strings]}` (a per-step
       visibility trace is NOT model-authorable this step — creator
       edits pending steps after the fact; keeps the output contract
       flat for the 8b model). Title required; steps list validated
       (length 2-5, all non-empty strings) else drop with note.
       Payload out: `{"owner_entity_id": scope_id (bare Name — forced),
       "title", "steps"}`. `target_table="agenda"`.
       Emit cap: at most ONE agenda_creation per scope call (first
       wins, later dropped with note); step_changes capped at one PER
       AGENDA per call (seen-set on agenda_id). Both OUTSIDE
       `SCOPE_EVENT_QUOTA` (events keep their own quota).

6. **Apply branches (`cockpit/app.py`, `_apply_mutation`).**
   - `agenda_step_change`: load step by `payload["step_id"]` (missing
     row -> error). STALE GUARD (0014 doctrine): `step.status !=
     "active"` -> error string "step no longer active — world moved
     since the tick" (covers duplicate approval, re-run duplicates,
     creator-moved-since; strictly stronger than any tick_id key —
     0015 F6 argument; NO `_find_applied_duplicate` clause needed for
     this type, document why in the guard docstring). Then:
     `write_agenda_step_status(step, "completed"|"failed", outcome)`;
     ADVANCE in code: `complete` -> next `pending` step by
     `step_order` gets `write_agenda_step_status(..., "active")`, none
     left -> `write_agenda_status(agenda, "completed")`; `fail` ->
     `write_agenda_status(agenda, "failed")` (whole agenda — no
     branching this step; creator can reactivate via PATCH). One
     SAVEPOINT.
   - `agenda_creation`: guard in `_find_applied_duplicate`'s tick
     branch — duplicate iff an ACTIVE agenda exists for
     `owner_entity_id` with the same normalized title (reuse the
     normalize-text helper local to app.py:913). Apply:
     `write_agenda(...)` + one `write_agenda_step` per objective
     (step_order 1..n), step 1 with `status="active"` (the approval IS
     the activation). Parent-child aggregate in one SAVEPOINT — NOT a
     one-branch-one-table exception (steps have no existence outside
     their agenda; document the distinction next to the
     resource_change comment, cockpit/app.py:930-936). Docstring's
     "Implemented types" updated; "Unimplemented" shrinks to
     `entity_creation, other`.

7. **Creator CRUD + Intrigues surface (cockpit).** First dedicated
   non-entity CRUD (RECON F7), all writes through the item-3 helpers:
   - `GET /api/agendas` — world-scoped list, each with owner name,
     status, ordered steps.
   - `POST /api/agendas` — `{owner_entity_id, title,
     steps: [{objective, visibility_trace?}, ...]}`; step 1 born
     `active` (symmetric with the applied creation — flagged decision).
   - `PATCH /api/agendas/{id}` — status override
     (`abandoned`/`active` reactivation), snapshot via helper.
   - `PATCH /api/agenda-steps/{id}` — edit `objective` /
     `visibility_trace` while `pending`; status override
     (complete/fail/activate — activating manually must respect the
     partial unique: deactivate is not a thing, the creator completes
     or fails the current active step first; surface the IntegrityError
     as a 409 with a clear message).
   - UI: an "Intrigues" panel following the cockpit's existing HTMX
     idioms — agenda list grouped by faction with status badges,
     per-step rows with status buttons, one create form. Keep it flat;
     no drag-reorder, no inline editing beyond the two text fields.

8. **Verify checks (`tooling/verify/checks/world_tick.py` +
   `single_canon_write.py`).**
   - Rule 12: the strings `"agenda_step_change"`/`"agenda_creation"`
     appear in `_normalize_scope_event` but NOT in
     `_normalize_tick_item` / `_TICK_MUTATION_TYPES` /
     `_TICK_TYPE_ALIASES` (per-NPC contract closed).
   - Rule 13: no `.get("step_id")` / `.get("agenda_id")` /
     `.get("owner_entity_id")` on model payloads in tick.py;
     `owner_entity_id` dict values are bare Names (rule-3 walker
     extension).
   - Rule 14: the AgendaStep model carries a UniqueConstraint/Index with
     `sqlite_where` on `status = 'active'` (AST scan of the model's
     `__table_args__`).
   - single_canon_write: `Agenda(` / `AgendaStep(` constructed only in
     writes.py (seed/migration exemption idiom).

9. **Prompt version (`scripts/seed_pilot.py` +
   `scripts/apply_ticket_0018_prompt_updates.py`).** New VERSION of
   `pt-world-tick-events` (same head/usage): the contract enumerates
   the two agenda types as FACTION-SCOPE ONLY; payload shapes of
   item 5; rules (RECON F6): advance ONLY an agenda named in AGENDA EN
   COURS; `fail` requires evidence FROM THE BRIEFING (an event, a lost
   member, a leak — never boredom); `outcome` = one line of what
   happened; at most ONE agenda_creation, 2-5 steps, only when POSTURE
   implies a plan no current agenda covers; when a completed step's
   visibility_trace would be publicly perceivable, PAIR it with an
   event_creation materializing it (same reply — no code coupling).
   Delivery: append-version branch (0015/0016 shape), idempotent.

## Scope OUT

- Non-faction owners (A2) — named deferral; `owner_entity_id` is ready,
  nothing else is pre-built.
- `npc_goal.parent_step_id` / any parentage (the F2 hierarchy
  engagement) — the natural NEXT chantier; no column ships now.
- Agendas in per-NPC tick briefings or any dialogue context (secret
  leak surface — own exclusion design needed first).
- Branching, conditional steps, deadlines, per-step event coupling in
  code.
- Entity creation (H1/I2).
- Drag-reorder or rich editing in the Intrigues UI.

## Invariants to defend

- **Model proposes, code judges** — agendas resolved by title against a
  code index; steps derived, never model-addressed; owner forced;
  advancement logic entirely code-side.
- **Structural over disciplinary** — one active step per agenda is a
  partial unique INDEX; A1 is a write-helper validation + an empty
  index for location scopes + an explicit gate.
- **History is sacred** — change_history snapshots before every status
  overwrite on both tables; no deletes anywhere.
- **Single canon-write path** — constructors only in writes.py; both
  sanctioned paths (apply + creator CRUD) share the same helpers.
- **Closed contracts stay closed** — the per-NPC type set is untouched;
  the scope contract grows only in its own normalizer.
- **C2** — every tick proposal lands `proposed`; creator CRUD is the
  creator's hand, not the model's.
- **Tick-guard doctrine** — canon-existence (active-step staleness /
  active-agenda title), never tick_id equality.
- **No structure without a reader** — both tables ship with their
  readers (briefing section + apply branches + Intrigues surface) in
  this same brief; `visibility_trace`'s reader is the briefing section
  (the model materializes it) — noted explicitly.

## Done means

Machine gate (`python tooling/verify/run.py`, fail-closed):
- [ ] Rules 12-14 pass; rules 1-11 still green -> tooling/verify/checks/world_tick.py
- [ ] Agenda/AgendaStep constructed only in writes.py -> tooling/verify/checks/single_canon_write.py
- [ ] Full suite green -> tooling/verify/run.py

Live gate (Nia) — deployment sequence FIRST (danger_class: migration):
- [ ] Backup; `python scripts/migrate_v1_72_agenda.py`; `python scripts/apply_ticket_0018_prompt_updates.py` (immediate re-runs: no-ops)
- [ ] Create a 3-step agenda for a faction in Intrigues (step 1 active); faction tick: briefing shows AGENDA EN COURS with the active step + trace; a step advancement is proposed with an outcome
- [ ] Approve `complete`: step completed (outcome stored, change_history grew), step 2 active; completing the final step closes the agenda (`completed`)
- [ ] A `fail` approval fails step AND agenda; reactivate via PATCH works
- [ ] An `agenda_creation` proposal applies: agenda + steps in Intrigues, step 1 active; re-approving it -> "Needs attention"; a second creation with the same title while active -> blocked
- [ ] Manually complete the active step, then approve the stale step proposal -> "Needs attention", nothing written
- [ ] Location-scoped tick: agenda items (if the model emits any) appear only as dropped notes; nothing enters the queue
- [ ] A paired event_creation materializing a visibility_trace flows through 0017 normally and, if public at a location, surfaces in the 0016 return delta

## Docs to update

- `world-engine-schema.md` — `agenda` + `agenda_step` sections, the
  partial-unique invariant, version bump; changelog entry in
  `world-engine-schema-changelog.md`.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` — new section "FACTION
  AGENDAS (BRIEF-0018-a)": A1/B2 verbatim, title-resolution /
  step-derivation doctrine, code-side advancement, fail-fails-the-agenda
  (+ creator reactivation), the aggregate-write distinction vs
  resource_change, first non-entity CRUD surface note, F2-hierarchy
  named deferral.
- `CLAUDE.md` — freshness contract decides.

## Drafting decisions flagged for Nia (reverse before deposit if wrong)

1. **`fail` fails the whole agenda** (no branching); the creator
   reactivates via PATCH if the intrigue survives differently. Reverse =
   fail only the step, next step activates anyway.
2. **Creator-authored agendas are born with step 1 `active`** (symmetric
   with applied creations). Reverse = born all-pending, explicit manual
   activation.
3. **The model cannot author visibility traces** (agenda_creation ships
   objectives only; traces are creator-edited on pending steps). Keeps
   the 8b output contract flat. Reverse = optional per-step trace in the
   creation payload.
4. **Agenda caps live outside SCOPE_EVENT_QUOTA** (1 creation + 1
   step_change per agenda per call; events keep their own 3). Reverse =
   one shared budget.
5. **AGENDA EN COURS shows the last 2 completed outcomes** for
   continuity. Reverse = active step only (leaner) or full history
   (heavier).
6. **No `_find_applied_duplicate` clause for agenda_step_change** — the
   apply-side active-status stale guard is strictly stronger (0015 F6
   argument). Reverse = add a mirror clause for pre-write symmetry.
