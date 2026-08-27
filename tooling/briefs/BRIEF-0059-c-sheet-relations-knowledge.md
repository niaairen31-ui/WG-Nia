# BRIEF — Step "entity sheet: relations + knowledge editors"

Ticket: TICKET-0059. Requires BRIEF-0059-b landed. Cites RECON-0059-a **M1**,
**M2**, **M3**, **M8**.

## Context

`Sheet.svelte` is a converged island with legacy interiors. Four of its field
sections are still legacy-rendered HTML strings interpolated with `{@html}`,
carrying inline `on*` attributes bound to globals in the legacy window:

```
Sheet.svelte:589  <div id="author-relations">{@html legacyCall('authorRenderRelations', detail.relations)}</div>
Sheet.svelte:590  {@html legacyCall('authorRenderRelationForm')}
Sheet.svelte:593  <div id="author-knowledge">{@html legacyCall('authorRenderKnowledge', detail.knowledge)}</div>
Sheet.svelte:594  {@html legacyCall('authorRenderKnowledgeForm')}
```

This brief closes the first two families. Relations and knowledge go together
because they are structurally the same editor twice — a list of rows with
inline edit plus an add-form beneath — and because `authorRelationRequest`
(`index.html:6698`) and `authorKnowledgeRequest` (`index.html:6801`) are
line-for-line the same request/refresh/status cycle against different paths.
Porting them in one brief is what makes the duplication visible and lets one
shared request helper replace both. Porting them separately would produce two
Svelte helpers with the same body, which is the divergence pattern this
workstream exists to end.

Goals and discipline details follow in `-d`; they carry prerequisite graphs
and an edit-mode state machine and do not belong in the same commit.

## Scope IN

1. **`frontend/src/creation/RelationsEditor.svelte`** — a faithful port of
   `authorRenderRelations` (`index.html:6610`), `authorRenderRelationForm`
   (6641), `authorAddRelation` (6670), `authorUpdateRelation` (6682),
   `authorDeleteRelation` (6693).

   - Props: the entity's `relations` array, the current entity id, the
     candidate entity list (`authorAllEntities` minus self), and the
     registry's `relation_fields` type options.
   - `RELATION_DIRECTIONS` moves verbatim as a frozen module const:
     `['mutual', 'a_to_b', 'b_to_a']`. It is a closed vocabulary; it does not
     become a free-text field and it is not re-derived from the registry.
   - Every field keeps its exact current semantics: `type` free text with a
     datalist of registry options, `direction` a select, `intensity` a number
     input with `min="1" max="100"`, `visible_to_b` a checkbox, `notes` a
     textarea nulled when empty (`|| null`, preserved exactly — an empty
     string must keep becoming `null` in the request body).
   - Delete keeps its confirmation. Verbatim text:
     `Permanently delete this relation?`
   - The add-form's defaults are preserved: direction `mutual`, intensity
     `50`, `visible_to_b` checked.

2. **`frontend/src/creation/KnowledgeEditor.svelte`** — the same treatment for
   `authorRenderKnowledge` (6719), `authorRenderKnowledgeForm` (6749),
   `authorAddKnowledge` (6770), `authorUpdateKnowledge` (6783),
   `authorDeleteKnowledge` (6796). Field semantics, option sources,
   confirmation text and null-coercion read from the live bodies at execution
   time — RECON-0059-a M2 reports them; do not reconstruct from memory.

3. **`frontend/src/creation/sheetRequest.svelte.js`** — one shared helper
   replacing both `authorRelationRequest` and `authorKnowledgeRequest`. It
   performs the request, refetches
   `/api/entities/<id>`, hands the refreshed detail back to the caller, and
   drives the status line. It does NOT write DOM: the legacy versions ended
   with `document.getElementById('author-relations').innerHTML = ...`; the
   Svelte version returns data and lets reactivity render.

   The status line is currently `#author-status` in the legacy markup, owned
   by `Sheet.svelte`'s surrounding shell. Route status through the existing
   `Sheet.svelte` mechanism rather than reaching for the element id — if
   `Sheet.svelte` has no status channel to pass down, add one prop rather
   than a `document.getElementById`. Success text stays verbatim: `Saved.`

4. **Mount both components in `Sheet.svelte`**, replacing lines 589-590 and
   593-594. The surrounding `field-section` / `field-section-title` markup and
   the section titles `Relations` and `Knowledge` stay byte-identical, so the
   sheet's visual structure is unchanged.

   The container ids `#author-relations` and `#author-knowledge` are deleted,
   not preserved — nothing may target them after this brief. Confirm via
   RECON-0059-a M3 that no other module reads them; if one does, STOP.

5. **Delete the ported legacy functions from `index.html`** in the same
   commit, including `RELATION_DIRECTIONS`, and extend
   `CREATION_ISLANDS.entitySheet.retiredPrefixes`
   (`frontend/src/creation/registry.js`) with every deleted identifier so
   `creation_island.py` rule 7 proves them gone. Add a `BRIEF-0059-c` comment
   above the added block in the same style as the existing `-g` family
   comments.

6. **Prune `legacy_calls.baseline`** of the four records closed here
   (`Sheet.svelte::authorRenderRelations`,
   `Sheet.svelte::authorRenderRelationForm`,
   `Sheet.svelte::authorRenderKnowledge`,
   `Sheet.svelte::authorRenderKnowledgeForm`) in the same commit, per `-b`'s
   prune protocol. Baseline goes 20 -> 16.

7. **Two commits, in this order**, each independently testable: (a)
   relations + the shared request helper; (b) knowledge. Each commit prunes
   its own baseline records and deletes its own legacy functions.

## Scope OUT

- **Any behaviour change.** No new validation, no relaxed constraint, no
  added confirmation, no "the intensity should really be 0-100". Field for
  field, message for message, default for default. A behaviour improvement
  found worth making is REPORTED, not made.
- **Goals and discipline details.** Brief `-d`, including
  `authorLoadGoals`/`authorLoadDiscDetails` at `Sheet.svelte:311`/`317` and
  `authorBackfillGoals`/`authorRenderGoalForm`/`authorRenderDiscDetailForm`
  at 640/643/650. Those four `legacyCall` records stay in the baseline.
- **The Sheet lifecycle helpers** — `_authorResetCreateDrafts` (167),
  `creationRefreshList` (393, 474), `_authorGetPendingCreationMutationId`
  (415), `_authorConsumePendingCreationMutationId` (465),
  `_authorNotifySaved` (475). Brief `-e`.
- **`authorSelectEntity`, `authorDelete`, `authorGetSelectedEntityId`.**
  They are read from outside the sheet (M3) and close at `-e` or `-l`.
- **`authorAddLedgerEntry`.** It belongs to the `registre` tab, not the
  sheet — brief `-h`, subject to M3's confirmation.
- **The relation GRAPH.** `graph/consumers/relations.js` is converged and
  untouched. Editing a relation must still invalidate the graph exactly as
  it does today, through the existing `graph:invalidate` event — do not
  invent a second refresh path.
- **Splitting `Sheet.svelte`.** It is near the module budget (M8); if this
  brief pushes it over 1000 lines, that is a REPORT and an escalation, not a
  spontaneous refactor — extraction by domain is a design decision, not an
  executor's call.
- **Any backend change**, including "this endpoint should accept a PATCH".
  Frontend-only (cross-cutting rule 2).

## Invariants to defend

- **Single canon-write authority.** Every save here stays on the existing
  creator-CRUD routes (`/api/entities/<id>/relations`, `/api/relations/<id>`,
  and the knowledge equivalents reported by M2). No new endpoint, no direct
  write, no batching of two writes into one call.
- **History is sacred.** `authorDeleteRelation` and `authorDeleteKnowledge`
  hit existing DELETE routes and keep their confirmations; the entity soft-
  delete path (`authorDelete`) is out of scope and must not acquire a
  neighbour here.
- **Exclusion is structural.** `visible_to_b` is a canon field submitted by
  the form; it is not a display filter and this brief must not start
  filtering rows on it client-side.
- **Fail-closed guards never lapse.** `legacy_call.py` must pass after each
  of the two commits, not only after the second.
- **Closed vocabulary.** `RELATION_DIRECTIONS` stays a three-value frozen
  list.

## Done means

- [ ] `python tooling/verify/checks/legacy_call.py` exits 0 after commit (a)
      and after commit (b); baseline is 16 records at the end.
- [ ] `python tooling/verify/checks/creation_island.py` exits 0; scratch
      mutation: re-add `function authorRenderRelations(` to `index.html` and
      confirm rule 7 bites; revert.
- [ ] `grep -c "authorRenderRelations\|authorRenderKnowledge\|authorAddRelation\|authorUpdateRelation\|authorDeleteRelation\|authorRelationRequest\|authorAddKnowledge\|authorUpdateKnowledge\|authorDeleteKnowledge\|authorKnowledgeRequest\|RELATION_DIRECTIONS" src/world_engine/cockpit/index.html`
      returns 0.
- [ ] Live: on an NPC sheet — add a relation to another entity, edit its
      type/direction/intensity/notes, save, reload the sheet, confirm the
      values persisted; delete it and confirm the confirmation dialog text is
      unchanged.
- [ ] Live: leave the notes textarea empty on save and confirm the stored
      value is null, not `""`.
- [ ] Live: same add/edit/delete cycle for a knowledge entry.
- [ ] Live: open the relation graph from the NPC tab after editing a
      relation and confirm the edit is reflected — the existing
      `graph:invalidate` path still fires.
- [ ] Live: the status line shows `Saved.` on success and the server's error
      message on failure, in the same place as before.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `python tooling/verify/run.py` exits 0.
- [ ] `module_budget.py` and `function_length.py` pass on every file this
      brief writes into.
- [ ] `/review-step` and `/close-step` run per commit.

## Docs to update

None. Brief `-m`.
