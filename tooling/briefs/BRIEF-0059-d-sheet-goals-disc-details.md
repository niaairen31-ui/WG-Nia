# BRIEF — Step "entity sheet: goals + discipline details"

Ticket: TICKET-0059. Requires BRIEF-0059-c landed. Reads
SUPPLEMENT-0059-recon-amendments **Amendments 6 and 8**. Cites RECON-0059-a
**M2**, **M3**, **M8**.

## Context

Brief `-c` closed the relations and knowledge sections of `Sheet.svelte`. Two
families remain inside the sheet's legacy interior: goals (13 functions) and
discipline details (9), reached through four surviving bridge-reach sites:

```
Sheet.svelte:311  legacyCall('authorLoadGoals', detail.id)
Sheet.svelte:317  legacyCall('authorLoadDiscDetails', detail.id)
Sheet.svelte:640  legacyCall('authorBackfillGoals', detail.id)
Sheet.svelte:643  legacyCall('authorRenderGoalForm')
Sheet.svelte:650  legacyCall('authorRenderDiscDetailForm', detail.id, detail.world_id)
```

These come after relations and knowledge because they are not the same shape.
Goals carry a prerequisite graph (`authorSetGoalPrerequisites`,
`authorAddGoalPrerequisite`, `authorRemoveGoalPrerequisite`) and an agenda
link/detach path shared with the Intrigues surface. Discipline details carry
a per-row edit-mode state machine (`authorEditDiscDetail` /
`authorResetDiscDetail` / `authorSaveDiscDetail`). Neither is a list-plus-
add-form.

One coupling here runs the **opposite** direction from the seal's census and
is therefore invisible to it: `index.html:7033` installs
`document.addEventListener('creation:goals-backfilled', ...)`, re-triggering
`authorLoadGoals` when the already-migrated `EntityList.svelte` dispatches
that event. Legacy listening to Svelte. It must be re-expressed here or the
backfill button silently stops refreshing the panel.

## Scope IN

1. **`frontend/src/creation/GoalsEditor.svelte`** plus
   **`frontend/src/creation/goalsPanel.svelte.js`** for its non-render logic —
   a faithful port of `authorLoadGoals` (`index.html:6824`),
   `authorRenderGoals` (6840), `authorRenderGoalPrerequisites` (6884),
   `authorAddGoalPrerequisite` (6914), `authorRemoveGoalPrerequisite` (6925),
   `authorSetGoalPrerequisites` (6931), `authorAttachGoalLink` (6946),
   `authorDetachGoalLink` (6962), `authorRenderGoalForm` (6972),
   `authorAddGoal` (6990), `authorSetGoalStatus` (6998),
   `authorBackfillGoals` (7009), `authorGoalRequest` (7039).

   `_goalPrereqRawList` (`index.html:6907`) is a private helper used only by
   this family and is not `author*`-prefixed (M2). It ports with the family
   and is added by name to the retired-identifier list — a prefix scan will
   not catch it.

   Endpoints preserved exactly, per M2: `GET /api/entities/{id}/goals`,
   `GET /api/agendas`, `PATCH /api/goals/{id}/prerequisites`,
   `POST /api/goal-agenda-links`, `POST /api/goal-agenda-links/{id}/detach`,
   `POST /api/entities/{id}/goals`, `POST /api/goals/{id}/status`,
   `POST /api/npc-goals/backfill`.

   The status vocabulary stays closed: `authorSetGoalStatus` is invoked today
   with exactly `'completed'` and `'abandoned'` (M2). It does not become a
   free-text field or a select fed from anywhere.

2. **Re-express the `creation:goals-backfilled` coupling.** Delete the
   listener at `index.html:7033`. `EntityList.svelte` continues to dispatch
   the event unchanged; `GoalsEditor.svelte` subscribes to it Svelte-side and
   reloads. Do not change the event name, do not change who dispatches it,
   and do not replace the event with a direct call — the two components are
   in different islands and the event is the seam between them.

3. **`frontend/src/creation/DiscDetailsEditor.svelte`** — a faithful port of
   `authorLoadDiscDetails` (`index.html:6193`), `authorRenderDiscDetails`
   (6204), `authorRenderDiscDetailRow` (6235), `authorRenderDiscDetailForm`
   (6259), `authorAddDiscDetail` (6294), `authorDeleteDiscDetail` (6323),
   `authorResetDiscDetail` (6333), `authorEditDiscDetail` (6346),
   `authorSaveDiscDetail` (6381).

   The per-row edit-mode machine becomes component state, not a DOM
   convention: today `authorEditDiscDetail` mutates markup in place and
   `authorResetDiscDetail` restores it. In Svelte the row holds its own
   `editing` flag. Behaviour is unchanged — a row enters edit mode, saves or
   resets, and no other row is affected.

   Endpoints preserved: `GET/POST /api/locations/{id}/discoverable-details`,
   `PUT /api/discoverable-details/{id}`,
   `DELETE /api/discoverable-details/{id}`.

4. **Reuse `sheetRequest.svelte.js`** — the shared request/refetch/status
   helper `-c` created. `authorGoalRequest` (7039) is the same
   request-then-refetch-then-status cycle as the two `-c` closed; it does not
   get a third implementation. If its refetch target differs (goals refetch
   `/api/entities/{id}/goals` rather than the whole entity), parameterise the
   existing helper rather than forking it.

5. **Mount both components in `Sheet.svelte`**, replacing the five bridge-
   reach sites listed in Context. The surrounding `field-section` /
   `field-section-title` markup and the section titles stay byte-identical.
   The container ids `#author-goals` and `#author-disc-list` are deleted, not
   preserved; M3 confirms no module outside the sheet reads them. If one does
   at execution time, STOP.

   The "Générer les buts" button (`Sheet.svelte:640`) keeps its exact label
   and position; only its handler changes.

6. **Delete every ported legacy function from `index.html`** in the commit
   that replaces it, including `_goalPrereqRawList` and the
   `creation:goals-backfilled` listener, and extend
   `CREATION_ISLANDS.entitySheet.retiredPrefixes`
   (`frontend/src/creation/registry.js`) with every deleted identifier so
   `creation_island.py` rule 7 proves them gone. Add a `BRIEF-0059-d` comment
   above the block in the style of the existing `-g` family comments.

7. **Prune `legacy_calls.baseline`** of the five records closed here, in the
   same commit each closes, per `-b`'s prune protocol.

8. **Two commits, in this order**, each independently testable: (a) goals,
   including the backfill event re-expression; (b) discipline details.

9. **Respect the frontend module budget** now enforced by `module_budget.py`
   (Amendment 6). `Sheet.svelte` sits at ~656 lines before `-c`; both
   families land in sibling files, not inline. If `Sheet.svelte` nevertheless
   approaches 1000 lines, that is a REPORT and an escalation — extraction by
   domain is a design decision, not an executor's call.

## Scope OUT

- **Any behaviour change.** No new validation, no relaxed constraint, no
  added confirmation, no "the prerequisite editor should really prevent
  cycles". Field for field, message for message, default for default. A
  worthwhile improvement found here is REPORTED, not made.
- **The prerequisite semantics.** `PATCH /api/goals/{id}/prerequisites`
  replaces the whole list today; it keeps doing exactly that. Do not
  introduce add/remove endpoints, and do not start validating prerequisite
  graphs client-side.
- **The agenda link path's other end.** `authorAttachGoalLink` /
  `authorDetachGoalLink` share endpoints with the Intrigues surface
  (`intriguesDetachLink`, `index.html:5035`). Intrigues is brief `-j`; it
  stays legacy here and must keep working. Do not touch it, and do not
  "unify" the two callers.
- **`prereq_judge.py` and `npc_goal_read.py`.** M7 does not list them as
  `index.html`-anchored. If either turns out to grep a function this brief
  deletes, that is a STOP and an escalation, not a silent check edit.
- **The Sheet lifecycle helpers** — `_authorResetCreateDrafts`,
  `creationRefreshList`, `_authorGetPendingCreationMutationId`,
  `_authorConsumePendingCreationMutationId`, `_authorNotifySaved`,
  `authorSelectEntity`, `authorDelete`, `authorGetSelectedEntityId`.
  Brief `-e`.
- **`authorAddLedgerEntry`.** Registre-owned per M3; brief `-h`.
- **The pending knowledge/goals draft panels.** Already migrated by
  TICKET-0058 (`PendingKnowledgeEditor.svelte`, `PendingGoalsEditor.svelte`).
  Do not merge them into the new editors — they serve the create flow, these
  serve the edit flow, and the distinction is load-bearing.
- **Splitting `Sheet.svelte`.** See item 9.
- **Any backend change**, including "the backfill endpoint should return the
  refreshed goals". Frontend-only (cross-cutting rule 2).

## Invariants to defend

- **Single canon-write authority.** Every write stays on the existing
  creator-CRUD routes enumerated in item 1 and item 3. No new endpoint, no
  direct write, no coalescing of two writes into one call.
- **Model proposes, code judges.** `authorBackfillGoals` triggers an
  AI-assisted backfill through `POST /api/npc-goals/backfill`. The Svelte
  side must not gain any path that writes generated goals directly; it calls
  the endpoint and re-reads, exactly as today.
- **History is sacred.** Goal status transitions append; nothing here gains a
  delete path it did not have.
- **Closed vocabulary.** Goal status stays `completed` / `abandoned` at this
  call site.
- **Fail-closed guards never lapse.** `legacy_call.py` and
  `creation_island.py` must pass after commit (a), not only after (b).

## Done means

- [ ] `python tooling/verify/checks/legacy_call.py` exits 0 after each
      commit; `Sheet.svelte` contributes **zero** records naming a goals or
      discipline-details function at the end.
- [ ] `python tooling/verify/checks/creation_island.py` exits 0; scratch
      mutation: re-add `function authorRenderGoals(` to `index.html` and
      confirm rule 7 bites; revert.
- [ ] `grep -c "authorLoadGoals\|authorRenderGoals\|authorGoalRequest\|_goalPrereqRawList\|authorLoadDiscDetails\|authorRenderDiscDetails\|authorSaveDiscDetail\|creation:goals-backfilled" src/world_engine/cockpit/index.html`
      returns 0.
- [ ] Live: on an NPC sheet — add a goal, set a prerequisite, remove it,
      attach the goal to an agenda, detach it, mark the goal completed, mark
      another abandoned. Reload; confirm every state persisted.
- [ ] Live: press "Générer les buts"; confirm the backfill runs AND the goals
      panel refreshes without a manual reload — this is the
      `creation:goals-backfilled` re-expression working.
- [ ] Live: on a location sheet — add a discoverable detail, enter edit mode
      on one row, confirm no other row entered edit mode, reset it, edit
      again, save, delete. Reload; confirm persistence.
- [ ] Live: open Intrigues and detach an agenda link from there; confirm it
      still works and that a goal's link state in the sheet reflects it.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `python tooling/verify/run.py` exits 0, including `module_budget.py`'s
      frontend rule.
- [ ] `function_length.py` passes on every file this brief writes into.
- [ ] `/review-step` and `/close-step` run per commit.

## Docs to update

None. Brief `-m`.
