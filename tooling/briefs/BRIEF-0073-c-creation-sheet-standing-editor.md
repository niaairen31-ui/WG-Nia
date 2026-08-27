# BRIEF — Step "Creation sheet: authoring and reading standing occupations"

TICKET-0073, brief -c. Depends on BRIEF-0073-b being merged (the column must
exist before the UI writes it).

## Context

BRIEF-0073-b added `npc_goal.kind` and made every in-scene reader honour it,
but nothing can author a standing row except a hand-written SQL insert. Under
E1 the creator is the only author in v1, so the Creation-side sheet IS the
write path — and it is also the loop Nia needs in order to run the live gate:
create an occupation, play a scene, judge whether intrigue drift falls.

Two decisions shape this step. O1: one selector with three options, with the
backend deriving the `(kind, horizon)` pair, so the incoherent combination is
unreachable from the sheet rather than rejected after the fact. P1: standing
rows render in their own `OCCUPATIONS` group above the two horizon groups —
an occupation is not an objective and must not read as a third one, which is
the same dilution the M1 prompt framing exists to avoid.

## Mini-RECON — measured, re-verify before editing

All anchors measured against `main` fetched 2026-08-23. `kind` does not exist
yet at measurement time; it lands in BRIEF-0073-b.

**Backend**
- **[M]** `src/world_engine/cockpit/crud/goals.py`:
  - `GoalWriteBody` (`:148`) — `description: Optional[str]`, `horizon: Optional[str]`.
  - `create_goal` (`:171`) — POST `/entities/{entity_id}/goals`, 201. Validates
    world scoping, `body.horizon not in NPC_GOAL_HORIZONS -> 422`, non-empty
    description -> 422, `character_type == "npc"` -> 422. Calls `write_npc_goal(...)`
    with `changed_by="creator"`, commits, refreshes, returns `_goal_dict`.
  - `_goal_dict` (`:126`) — returns `id`, `npc_id`, `description`, `horizon`,
    `status`, `created_at`, `updated_at`, `links`, `prerequisites`. **No `kind`.**
  - `_list_goals` (`:140`) — all rows for the entity, sorted active-first then
    newest-first within each status group.
  - `set_goal_status` (`:197`) — POST `/goals/{goal_id}/status`.
- **[M]** `crud/goals.py` imports `NPC_GOAL_HORIZONS` at `:57`.
- **[M]** `crud/goals.py` is in `npc_goal_read.py`'s `ALLOWED_MODULES`.

**Frontend**
- **[M]** `frontend/src/creation/GoalsEditor.svelte` — 151 lines. Markup only;
  state and requests live in `goalsPanel.svelte.js` (121 lines). Mounts per
  selected NPC (`$effect` on `entityId`), subscribes to
  `creation:goals-backfilled`.
- **[M]** `HORIZON_LABEL = { long: 'LONG TERME', short: 'COURT TERME' }` —
  `GoalsEditor.svelte:36`. Rendered as `<span class="badge b-other">` on each row.
- **[M]** Add form (`GoalsEditor.svelte:139-151`): a `field-grid` with a
  `<select bind:value={newHorizon}>` offering raw `short` / `long` option
  values, a description `<textarea>`, and a `btn-send` calling `onAddGoal`.
- **[M]** `onAddGoal` (`:65`) calls
  `addGoal(legacyDoc, entityId, newHorizon, newDescription)` then resets to
  `'short'` / `''`.
- **[M]** `addGoal` lives in `goalsPanel.svelte.js` and goes through the shared
  `sheetRequest` request-then-reload-then-status cycle.
- **[M]** The rows list is a single `{#each goalsPanelState.goals as g (g.id)}`
  over the flat backend order — there is NO grouping in the component today.
- **[M]** Closed rows render at `opacity:0.6` with the Accompli / Abandonne
  buttons hidden; the prerequisite editor and the agenda attach/detach control
  render per row.
- **[M]** Verbatim component docstring: *"No edit/reopen: description is
  immutable after insert, a closed goal is never reopened (a revived goal is a
  new row) -- unchanged from legacy."*
- **[M]** `module_budget.py` enforces 1000 lines on
  `frontend/src/**/*.{svelte,js}` with NO exemption mechanism. `GoalsEditor.svelte`
  at 151 and `goalsPanel.svelte.js` at 121 have ample room.

### STOP conditions

1. `npc_goal.kind` is absent from the model or the live DB — BRIEF-0073-b has
   not landed. Stop; this brief writes a column that must already exist.
2. `GoalsEditor.svelte` or `goalsPanel.svelte.js` no longer matches the
   anchors above (the add form has moved, `addGoal`'s signature differs, or
   grouping has been introduced). Measure before editing.
3. A second caller of `POST /entities/{id}/goals` exists beyond
   `goalsPanel.svelte.js::addGoal`. Measure with
   `grep -rn "/goals" frontend/src/ src/world_engine/cockpit/`. A second
   caller means the O1 guarantee (the incoherent pair is unreachable from the
   UI) does not hold from that path, and the server-side validation in Scope
   IN 2 becomes the only guard — which is acceptable, but must be known and
   reported, not discovered later.
4. `prereqCandidates` or the agenda-attach control turns out to depend on
   `horizon`. It does not at measurement time; verify before adding a third
   option that could reach those paths.

## Scope IN

1. **`GoalWriteBody`** gains `kind: Optional[str] = None`.

2. **`create_goal`** validates the O1 triple as a PAIR, not two independent
   fields. Insert after the existing horizon validation, before the character
   check:

   ```python
   kind = body.kind or "volition"
   if kind not in NPC_GOAL_KINDS:
       raise HTTPException(422, f"kind must be one of {sorted(NPC_GOAL_KINDS)}")
   if kind == "standing" and body.horizon != "long":
       raise HTTPException(422, "kind='standing' requires horizon='long'")
   ```

   Import `NPC_GOAL_KINDS` alongside the existing `NPC_GOAL_HORIZONS` import.
   Pass `kind=kind` through to `write_npc_goal`.

   The `body.kind or "volition"` default keeps every existing caller working
   unchanged — an omitted `kind` is a volition, which is what every row was
   before v1.91.

3. **`_goal_dict`** returns `"kind": g.kind`, placed immediately after
   `"horizon"`. This is what lets the frontend group rows; without it the
   component has nothing to group ON.

4. **`GoalsEditor.svelte` — the add form (O1).** Replace the two-option
   horizon `<select>` with a single three-option selector bound to a new
   `newChoice` state, defaulting to `'short'`:

   ```
   <option value="short">COURT TERME</option>
   <option value="long">LONG TERME</option>
   <option value="standing">OCCUPATION</option>
   ```

   Relabel the field `Type *`. The component maps the single choice to the
   pair at call time, and nowhere else:

   ```js
   const CHOICE_TO_PAIR = {
     short:    { kind: 'volition', horizon: 'short' },
     long:     { kind: 'volition', horizon: 'long'  },
     standing: { kind: 'standing', horizon: 'long'  },
   };
   ```

   `onAddGoal` resolves `CHOICE_TO_PAIR[newChoice]` and passes both values to
   `addGoal`; it resets `newChoice` to `'short'` afterwards, matching the
   current reset behaviour.

   There must be NO second control from which `kind` and `horizon` can be
   chosen independently. That is the whole of O1: the invalid pair is not
   rejected, it is unformable.

5. **`goalsPanel.svelte.js` — `addGoal`** takes `(legacyDoc, entityId, kind, horizon, description)`
   and posts `{ kind, horizon, description }`. Keep the existing
   request-then-reload-then-status cycle through `sheetRequest`; do not
   reimplement it.

6. **`GoalsEditor.svelte` — the rows list (P1).** Split the flat `{#each}`
   into two groups, in this order:

   - **`OCCUPATIONS`** — rows where `g.kind === 'standing'`. Rendered only
     when the group is non-empty; no empty-group heading.
   - The existing list — rows where `g.kind !== 'standing'`, in the backend's
     current order, with its existing `HORIZON_LABEL` badge unchanged.

   Use `!== 'standing'` for the second group specifically so a row arriving
   with an unexpected `kind` still renders somewhere rather than vanishing
   from the sheet.

   Add a group heading element for `OCCUPATIONS` using the existing badge /
   card styling already present in the component. Do not introduce new CSS
   classes and do not touch `frontend/src/creation/*.css` or the cockpit
   stylesheet partition — TICKET-0063 partitioned it and a new selector there
   is a separate reckoning.

   Standing rows keep every per-row control the volition rows have: status
   badge, Accompli / Abandonne, the closed-row `opacity:0.6` treatment, the
   prerequisite editor and the agenda attach/detach control. They are the same
   table; only the grouping and the badge differ.

7. **`HORIZON_LABEL`** gains no `standing` entry — a standing row is in the
   `OCCUPATIONS` group and does not need a horizon badge repeating `LONG TERME`.
   If a badge is wanted on those rows, use the literal `OCCUPATION`.

8. **Extend `tooling/verify/checks/standing_goal.py`** (created in -b) with
   two rules:

   - **R7 (paired validation).** `crud/goals.py::create_goal` contains a
     `Compare` node testing a kind value against `'standing'` AND a comparison
     involving `horizon`, in the same function — the server-side guarantee
     that the pair is validated together, independent of the UI.
   - **R8 (single-control mapping).** `GoalsEditor.svelte` contains exactly
     ONE `<select>` whose option values include `standing`, and the literal
     `CHOICE_TO_PAIR` (or the chosen constant name) appears in the component.
     Text scan, not AST — Svelte is not Python. Zero matches is a FAILURE,
     two or more selects offering `standing` is a FAILURE.

   Keep the anti-vacuity discipline: a rule that finds nothing to inspect
   fails.

## Scope OUT

- **Editing a goal's description, horizon, or kind in place.** `description`
  is immutable after insert and the component says so verbatim. A changed
  occupation is a closed row plus a new one. Do not add an edit control, and
  do not add a `PATCH` route.
- **A dedicated occupation editor, panel, tab, or modal.** The occupation
  lives in the goals panel because it is a goal. A separate surface would
  re-create the G3 split that was rejected at intake.
- **Any location, phase, or schedule control.** TICKET-0074 owns the schedule
  and its Creation surface. Do not add a location picker to a goal row, and do
  not anticipate `npc_schedule.standing_goal_id`.
- **Exposing occupations on the Play surface or to the player.** The player
  never sees an NPC's goals of any kind; the occupation reaches the player
  only through what the NPC says.
- **`PendingGoalsEditor.svelte` and the review queue.** Those handle
  model-proposed goals. Under E1 no model proposes a standing goal, so there
  is nothing for them to display. Deferred; reactivation condition: *a
  proposer for standing goals exists* (TICKET-0074 brief -b at the earliest).
- **`EntityList.svelte::backfillNpcGoals` and the `creation:goals-backfilled`
  bridge.** Backfill authors volitions; leave it alone. The existing
  subscription in `GoalsEditor` keeps working unchanged.
- **`Intrigues.svelte` and the agenda-link surface.** Standing rows can be
  linked to an agenda through the existing per-row control if the creator
  chooses; no change to that machinery is authorized here.
- **Restyling the goals panel, the badges, or the row cards.** The grouping
  heading reuses what is already in the component.
- **Sorting changes in `_list_goals`.** The backend order stays as it is; the
  grouping happens in the component.

## Invariants to defend

- **Two sanctioned canon-write paths.** This is creator CRUD, the second of
  the two. It goes through `write_npc_goal`, which BRIEF-0073-b already
  extended and validated. No new write site, no direct `db.add(NpcGoal(...))`
  in the route.
- **Structural over disciplinary (O1).** The pair is validated server-side
  (R7) AND unformable client-side (R8). The server check is the structural
  one; the UI shape is what keeps the creator from meeting a 422 in normal use.
- **N1 goal-read doctrine.** `crud/goals.py` is already allowlisted. No new
  module reads `NpcGoal`. `ALLOWED_MODULES` gains no entry.
- **Frontend line budget.** Both files stay far under 1000; there is no
  exemption mechanism for frontend files, so measure after editing.
- **Stylesheet partition (TICKET-0063).** No new selector in the partitioned
  stylesheet. Inline styles consistent with the component's existing practice
  only.
- **History is sacred.** No retroactive edit path is added.

## Done means

- [ ] `GET /api/entities/{id}/goals` returns `kind` on every row; pre-existing
      rows return `volition`.
- [ ] `POST /api/entities/{id}/goals` with `{kind:'standing', horizon:'long', description:'...'}`
      returns 201 and the row comes back with `kind: 'standing'`.
- [ ] The same POST with `{kind:'standing', horizon:'short'}` returns 422 with
      a message naming the constraint.
- [ ] The same POST with `{kind:'bogus'}` returns 422.
- [ ] A POST omitting `kind` entirely still returns 201 and produces a
      `volition` row.
- [ ] In the Creation tab, on an NPC sheet, the goals panel's add form shows
      one selector with COURT TERME / LONG TERME / OCCUPATION, and there is no
      second control for horizon or kind.
- [ ] Adding an OCCUPATION succeeds and the row appears under an `OCCUPATIONS`
      heading ABOVE the existing rows.
- [ ] An NPC with no standing row shows no `OCCUPATIONS` heading.
- [ ] A standing row can be closed with Accompli and with Abandonne, and
      renders at reduced opacity afterwards like any closed goal.
- [ ] Switching the selected NPC reloads the panel correctly and the grouping
      follows.
- [ ] `python tooling/verify/checks/standing_goal.py` exits green, and exits
      RED when the `standing` option value is temporarily removed from the
      selector (verify R8 bites, then restore).
- [ ] `python tooling/verify/checks/module_budget.py` exits green (frontend
      rule included).
- [ ] `python tooling/verify/checks/corpus_gate.py` exits green.
- [ ] `npm run build` in `frontend/` succeeds and the served bundle is fresh
      (TICKET-0066's `frontend_build_fresh` check green).
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- No schema changelog entry — the schema change landed in v1.91 (BRIEF-0073-b).
  This step is API and UI only.
- **`ARCHITECTURE_DECISIONS.md`:** a short entry for O1 — why one selector
  deriving the pair rather than two independent controls (O2 rejected: exposes
  a combination the CHECK refuses, so the creator meets a 422 instead of being
  unable to form the pair; O3 rejected: the forcing would live in the
  component, invisible to every check and bypassed by a second caller).
- **`CLAUDE.md`:** nothing.
