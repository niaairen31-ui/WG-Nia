# BRIEF — Step "Creation surfaces: the day of X, who is here by phase, and the phase control"

TICKET-0074, brief -b of three. Depends on BRIEF-0074-a being merged. One
commit.

## Context

BRIEF-0074-a shipped `npc_schedule`, `world.current_phase` and the two reads,
but the only way to author a schedule is a hand-written INSERT. That breaks
Nia's live-gate loop, and it leaves B1's compensating control unbuilt: the table
is sparse by decision, no check enforces coverage, so empty phases must be
VISIBLE to the author before a player walks into one. This step ships the three
surfaces — the authoring island (T-C1), the read panel (F1), and the phase
control that makes T-A1's condition 1 true.

## Mini-RECON — verify before writing

Measured against `main` at schema v1.91 on 2026-08-23, before -a landed. Report
`file:line` for each. **STOP and escalate** if any does not hold.

1. **The anchor the design could not make.** `frontend/src/creation/Sheet.svelte`
   is **752 lines** and owns BOTH sheets: the location branch mounts
   `SubcultureEditor` at `:658-664`, `GeometryEditor` at `:667-673` and
   `DoorsEditor` at `:674-679` under `{#if !isNew && type === 'location'}`; the
   NPC branch mounts `PricingEditor` at `:727-731` and `GoalsEditor` at
   `:733-741` under `{#if !isNew && type === 'character' && tabKey === 'npc'}`.
   Confirm both branch guards verbatim — the two new components mount in
   different branches of the SAME file.
2. `Sheet.svelte`'s budget after this brief. `module_budget.py` enforces 1000
   lines on `frontend/src/**/*.{svelte,js}` with **no exemption mechanism**.
   752 leaves 248. Two mounts plus two imports should cost well under 20. If the
   draft would exceed 1000, **STOP and escalate**.
3. `GoalsEditor.svelte` is **174 lines** and `goalsPanel.svelte.js` is **121** —
   component owns markup, `.svelte.js` module owns state and requests. Confirm;
   this is the shape both new components follow.
4. `sheetRequest.svelte.js` is 53 lines, exports `api(path, options)` and
   `sheetRequest(legacyDoc, path, method, body, reload)`, and its header
   documents the ordering rule: `reload` is awaited and ONLY THEN is the status
   line written, because `Sheet.svelte`'s header-sync `$effect` clears
   `#author-status` on every 'view' re-render. Confirm; both new components use
   this cycle and must not fork it.
5. The mount idiom, verbatim from `Sheet.svelte:674-679`:
   `<DoorsEditor entityId={detail.id} relations={detail.relations}
   doors={detail.doors} {legacyDoc} onSaved={(d) => flushSync(() =>
   enterViewMode(d, d.type))} />`. Note `GoalsEditor` at `:739` takes NO data
   prop and loads its own. Report which of the two shapes each new component
   should use given what `detail` actually carries after -a. **If `detail`
   already carries schedule rows, say so** — that changes the read panel from a
   fetch to a prop.
6. `src/world_engine/cockpit/crud/goals.py` is 416 lines, `crud/locations.py` is
   333, both decorate the shared `router` from `crud/_router.py`, and
   `crud/__init__.py` is a re-export surface only. Confirm; report which module
   the new endpoints should join and its line count.
7. `crud/__init__.py:1-20` records the doctrine verbatim: author CRUD is a
   direct canonical write with no `proposed_mutation` checkpoint, because that
   checkpoint contains the local model's drift during play, not the creator.
   Confirm; the new endpoints inherit it.
8. `tooling/verify/checks/standing_goal.py` is 332 lines, and its R8
   (`GOALS_EDITOR_FILE` at `frontend/src/creation/GoalsEditor.svelte`) asserts
   that the `standing` choice comes from exactly ONE `<select>` mapped through a
   named constant. Confirm; R11 below is that rule, retargeted.
9. `tooling/verify/checks/creation_island.py` enforces the island-mount seam and
   re-anchors on `frontend/src/creation/Creation.svelte` and `tabs.js`. **Read
   its rules before adding a mount.** Report whether a new component mounted
   inside `Sheet.svelte` (rather than into a Creation-owned container) is in
   scope for any of its rules. If it is, this brief's mounts must satisfy them
   too — say so rather than routing around it.
10. Report which component owns the cockpit chrome — the persistent frame
    outside the tab bodies. Candidates seen in the tree:
    `frontend/src/creation/Creation.svelte` (256 lines), and whatever
    `frontend/src/lib/` holds. **The phase control belongs in chrome visible
    from every surface, not inside the Creation tab.** If no such component
    exists, **STOP and escalate**: T-A1's condition 1 cannot be satisfied by a
    control that is only visible on one tab, and picking a substitute location
    is a design decision this brief does not carry.
11. Confirm `SCHEDULE_PHASES` (from -a) is reachable for the frontend: report
    whether the four values arrive through an API payload or must be mirrored
    in a JS constant. Either is acceptable; R11 asserts ONE named source
    whichever it is.

## Scope IN

1. **API — read.** `GET /api/entities/{npc_id}/schedule` returns the NPC's four
   phases, each with `{phase, location_id, location_name, standing_goal_id,
   standing_goal_description}`. **Always four rows**, one per phase in
   `SCHEDULE_PHASES` order, with nulls for phases that have no row — the
   editor renders a day, not a list, and an absent phase must be an empty slot
   rather than a missing element.

2. **API — write.** `PUT /api/entities/{npc_id}/schedule` takes
   `{"rows": [{"phase", "location_id", "standing_goal_id"}]}`, calls
   `writes.write_npc_schedule` (the ONLY write path), commits, and returns the
   same shape as the read. Full replace: rows absent from the payload are
   deleted. `PUT`, not `POST` — the verb states the semantics.

3. **API — the inverse read.** `GET /api/locations/{location_id}/schedule`
   returns, for each of the four phases, the NPCs `who_is_at` resolves there
   (`{npc_id, name, source}`), plus a top-level `unresolved` list per phase from
   `unresolved_npcs`. `is_present` is computed server-side by comparing the
   phase to the active world's `current_phase`.

4. **API — the phase.** `GET /api/world/phase` returns
   `{world_id, current_phase, phases}` (`phases` = `SCHEDULE_PHASES`).
   `PUT /api/world/phase` takes `{"current_phase": str}`, validates against
   `SCHEDULE_PHASES`, writes the column on the ACTIVE world, commits, returns
   the new value. **It does nothing else** — T-A1's condition 2. No tick, no
   mutation, no NPC movement, no cascade of any kind. Its handler body is short
   enough to read in one screen, and the check asserts it calls nothing beyond
   its own validation, write and commit.

5. **`ScheduleEditor.svelte` + `schedulePanel.svelte.js`** — the T-C1 authoring
   island, on the `GoalsEditor` / `goalsPanel` split (component owns markup,
   module owns state and requests through `sheetRequest`). Renders "la journée
   de {name}": four rows in `SCHEDULE_PHASES` order, each with the phase name, a
   location picker (same option source the sheet's other location pickers use),
   and an optional standing-goal picker fed by the NPC's `kind='standing'` goals.
   One Save button writing the whole day. Clearing a row's location and saving
   removes that phase. Empty phases render as visibly empty rows, never omitted.

6. **`SchedulePanel.svelte`** — the F1 read panel, "qui est ici, par phase", on
   the location sheet. Four groups in `SCHEDULE_PHASES` order, each listing the
   NPCs resolved there with their `source`, and each rendering **visibly empty**
   when nobody resolves. Below the four groups, an "unresolved" block naming
   NPCs that resolve nowhere for the currently selected phase. **Read-only by
   construction**: the component issues no POST, PUT, PATCH or DELETE, and the
   check asserts it — this is B1's compensating control, and a control that can
   also write is a second authoring path nobody decided to build.

7. **Mounts in `Sheet.svelte`.** `ScheduleEditor` inside the existing
   `{#if !isNew && type === 'character' && tabKey === 'npc'}` branch, in a
   `field-section` titled `Horaire`, placed after the `Objectifs` section (an
   occupation is the reason, a schedule is the where — they read in that order).
   `SchedulePanel` inside the existing `{#if !isNew && type === 'location'}`
   branch, in a `field-section` titled `Qui est ici, par phase`. Both follow
   mini-RECON item 5's idiom exactly, including the `onSaved` /
   `flushSync(enterViewMode)` ordering.

8. **The phase control in the chrome.** In the component reported by mini-RECON
   item 10: the current phase displayed as persistent text (never behind a
   click, never a tooltip — T-A1's condition 1 is that a forgotten phase is
   VISIBLE), and a control to advance it, calling `PUT /api/world/phase`. Four
   options built from ONE named source per R11.

9. **Check amendment — `tooling/verify/checks/npc_schedule.py`.** Add R9-R11 to
   the file -a authored, each with an anti-vacuity guard:
   - **R9 (read-only panel):** `SchedulePanel.svelte`'s source contains no
     `method:` value among POST/PUT/PATCH/DELETE. Zero fetch calls found is
     fine; the file not existing is a FAILURE.
   - **R10 (mount reachability):** `Sheet.svelte` both IMPORTS and MOUNTS each
     of `ScheduleEditor` and `SchedulePanel`, and each mount sits inside its
     named branch guard. An import without a mount, or a mount without an
     import, is a FAILURE — the "dispatch-site existence proves an event fires
     but not that a listener hears it" lesson, applied to mounts.
   - **R11 (single vocabulary source):** every phase `<select>` under
     `frontend/src/` builds its options from one named constant or one API
     field, never from four inline string literals. Retargeted from
     `standing_goal.py`'s R8. Zero `<select>` elements located across the
     schedule components is a FAILURE.
   - **R4b (the bare write):** `PUT /api/world/phase`'s handler function calls
     nothing outside a fixed allowlist of names (its validation helper, the
     session `add`/`commit`, and the response builder). Any other call is a
     FAILURE. This is T-A1's condition 2 made structural rather than
     documented.

## Scope OUT

- **The L1 concordance wiring.** `context.py` stays untouched. Brief -c owns it.
- **Exposing schedules or agendas to the PLAYER UI.** The player never sees the
  plan. An authoring surface must not become a back door to it — no Play-side
  component, no Play route, no field added to any Play payload.
- **The Play surface generally.** It is sealed (TICKET-0061); TICKET-0069 is its
  named paused successor. Even if the phase control would "look right" there.
- **The legacy mount.** Decommissioned at TICKET-0061. Both new components are
  Svelte islands in `frontend/src/creation/`. `legacy.html` is under a shrinking
  ratchet (`LEGACY_DOCUMENT_LINE_CEILING`) — do not add a line to it.
- **A coverage check.** B1 makes coverage a REPORT. The panel IS the control.
  Do not add a check, a warning badge that blocks save, or a required-field
  validation demanding four filled phases.
- **`schedule_change`, auto-approve, or any mutation type.** S-F, separate
  ticket. The editor writes through creator CRUD, directly.
- **A phase selector on the NPC editor.** The editor authors all four phases at
  once; a selector there would imply per-phase saving and fight full-replace.
- **Advancing the phase doing anything.** No tick trigger, no "advance day"
  button, no NPC repositioning, no confirmation modal implying consequence.
- **Bulk authoring** — copying one NPC's day to another, templates by role,
  faction-wide defaults. E3 was rejected for inventing canon by rule.
- **Any calendar or clock UI.** 100% Scope OUT per Nia, this ticket.

## Invariants to defend

- **Two sanctioned canon-write paths only.** The two write endpoints are creator
  CRUD. Neither emits a `ProposedMutation` (E2 rejected). Neither is reachable
  from a model-facing route.
- **Structural, never disciplinary.** The read panel cannot write (R9). The
  phase write cannot cascade (R4b). Both are enforced by the check, not by the
  component's docstring.
- **Exclusion is structural.** `SchedulePanel` runs through
  `who_is_at`/`unresolved_npcs`, which scope to active alive NPCs at query
  construction. Do not filter a broader result set in the component.
- **No structure without a reader.** Every field the two read endpoints return
  is rendered by one of the two components in this brief. If a field has no
  renderer, drop the field.
- **Fail-closed and vacuous-proof.** R9-R11 and R4b each FAIL on zero items
  located.

## Done means

- [ ] `python -m tooling.verify.checks.npc_schedule` passes with R1-R11 and R4b,
      and each new rule fails when its target is deliberately broken (report the
      verdicts; revert every break).
- [ ] `corpus_gate.py` is green on the whole corpus.
- [ ] `Sheet.svelte` and every other frontend file are under 1000 lines; report
      `Sheet.svelte`'s exact count.
- [ ] On an NPC sheet: four phase rows render, a location can be picked for
      each, Save succeeds, and reloading the sheet shows the same four rows.
- [ ] Clearing one phase's location and saving leaves three rows on reload —
      full replace, not accumulation.
- [ ] On a location sheet: the panel lists NPCs per phase, and a phase with
      nobody renders as a visibly empty group rather than disappearing.
- [ ] An NPC with no schedule row appears in the panel's unresolved block for
      every phase.
- [ ] The current phase is visible in the chrome from every surface, and
      advancing it updates the display.
- [ ] After advancing the phase: no new row in the review queue, no NPC's
      `current_location_id` changed, no tick record created. Report the three
      as measured, not assumed.
- [ ] With two worlds in the database, advancing the phase on the active world
      leaves the other world's `current_phase` untouched. Report both values
      before and after.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- No schema change: `world-engine-schema.md` and the changelog are untouched by
  this brief, and `EXPECTED_STATIC_SCHEMA_VERSION` stays at `v1.92`.
- `ARCHITECTURE_DECISIONS.md`: extend -a's section with T-C1 (why the NPC sheet
  authors and the location sheet reads) and with F1-as-compensating-control for
  B1.
- No `CLAUDE.md` change.
