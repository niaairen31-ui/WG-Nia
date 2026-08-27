# BRIEF — Step "prompts tab + parked conversation-window config"

Ticket: TICKET-0059. Requires BRIEF-0059-h landed. Reads
SUPPLEMENT-0059-recon-amendments **Amendment 5**. Cites RECON-0059-a **M5**,
**M7**. Locks: **I1**.

## Context

The prompts tab is the largest single-surface residue in this ticket: 31
`prompts*` functions plus 3 `cw*`, `index.html:5288-5910`, behind
`#creation-prompts` (markup at 1504-1528). It is a creator-management surface,
read-mostly, with five distinct sub-behaviours: the usage list, the detail
view with a live Ollama model selector, an edit mode with a dirty guard, a
lazily-loaded version history with restore, and an assembled-prompt preview
panel.

The container also hosts `#cw-config-panel` — the per-world conversation-
window config (`cwLoadConfig` 5355, `_cwRenderConfig` 5366, `cwPatchField`
5391). It is a world-level config surface **parked** in this tab by named
deferral **D-0050**, and the markup at `index.html:1505-1507` says so. Lock
**I1**: it ports verbatim, still parked, D-0050 untouched.

The tab carries a real dirty guard: `_promptsConfirmDiscard` (5288) returns
`!promptsEditDirty || confirm('Unsaved prompt edit will be lost — continue?')`
and gates every navigation away from an in-progress edit. The module comment
at 5269 states the doctrine it serves — nothing here persists across a reload
or a prompt/world switch. That guard and that doctrine are the two things
easiest to lose in a port.

`prompt_registry.py`, `prompt_version.py`, `prompt_lean.py`,
`prompt_model_write.py` and `conversation_window_config.py` all scan
`src/**/*.py` only (M7, re-confirmed this session). **No check re-homing in
this brief.** Do not spend effort looking for one.

## Scope IN

### Commit 1 — list, detail, model selector, cw config

1. **`frontend/src/creation/Prompts.svelte`** plus
   **`frontend/src/creation/prompts.svelte.js`** for non-render logic. Commit
   1 ports: `_promptsResetEditState` (5294), `_promptsWorldReset` (5309),
   `_promptsFetchOllamaModels` (5319), `promptsLoadList` (5330),
   `_promptsRenderList` (5408), `_promptsRenderUsageCard` (5420),
   `_promptsExtractTokens` (5447), `_promptsHighlightTokens` (5453),
   `promptsSelectDetail` (5457), `_promptsRenderModelSelector` (5479),
   `promptsChangeModel` (5513), `_promptsRenderDetail` (5540),
   `_promptsRenderReadBodies` (5576).

   The eight module-level `let promptsX` globals at `index.html:5260-5285`
   become component state. Preserve their documented semantics verbatim:
   `promptsOllamaModels` distinguishes `null` (unknown / unreachable) from
   `[]` (reachable, empty) — that is a three-state, not a boolean, and the
   selector renders differently for each. `promptsSelectedId` is highlight
   state only and persists nothing.

2. **`frontend/src/creation/ConversationWindowConfig.svelte`** — port
   `cwLoadConfig` (5355), `_cwRenderConfig` (5366), `cwPatchField` (5391),
   and the `#cw-config-panel` markup (`index.html:1505-1517`).

   It is a **child component of `Prompts.svelte`, not a second island.** One
   island per container; the panel stays where it renders today. When D-0050
   activates and a world-configuration surface exists, moving it is then a
   component relocation rather than an extraction — which is the point of
   giving it its own file now, and the limit of what this brief does about
   it.

   Carry the deferral comment across verbatim into the component header:

   > TICKET-0050 (BRIEF-0050-e) — per-active-world config, edited here (N2)
   > beside conversation_summary until a dedicated world-configuration
   > surface exists (named deferral D-0050).

   `promptsLoadList` calls `cwLoadConfig()` today (`index.html:5304`). That
   coupling is preserved: the child loads when the parent loads.

3. **Registry.** Add `prompts` to `CREATION_ISLANDS` and `mount.js`'s
   `COMPONENTS`. In `CREATION_TABS.prompts`: `loader: null`,
   `state.onWorldSwitch: null` (the reset moves into the component, driven by
   `serverState.worldId`),
   `islands: [{ key: 'prompts', containerId: 'creation-prompts' }]`.
   `primaryAction` stays `null` — preserve the existing comment,
   `read-only, creator management surface (BRIEF-0008-b)`.

   Reduce `index.html:1504-1528` to an empty container with a comment
   matching `#creation-region`'s at 1432.

### Commit 2 — edit mode

4. Port `_promptsConfirmDiscard` (5288), `_promptsRenderEditBodies` (5595),
   `promptsEnterEditMode` (5619), `promptsCancelEdit` (5630),
   `promptsEditInput` (5641), `_promptsUpdateEditHint` (5649),
   `promptsSaveEdit` (5664), `_promptsRefreshDetail` (5691).

   **The dirty guard is the load-bearing item.** Enumerate every current call
   site of `_promptsConfirmDiscard` before porting and reproduce each one —
   selecting another prompt, changing the model, toggling history, selecting
   a history version, restoring, and a world switch are the candidates.
   Missing one turns a guarded navigation into silent data loss, and the
   symptom is invisible until someone loses an edit. List the call sites you
   found in the commit message.

   The confirm text stays verbatim, em dash included:
   `Unsaved prompt edit will be lost — continue?`

5. Preserve the no-draft-persistence doctrine: nothing in the edit path
   writes to storage, and nothing survives a reload or a prompt/world switch.
   Carry the module comment at `index.html:5269-5271` into the component.

### Commit 3 — history, restore, preview

6. Port `_promptsRenderHistorySection` (5715), `promptsToggleHistory` (5736),
   `_promptsLoadHistory` (5751), `_promptsRenderHistoryList` (5763),
   `promptsSelectHistoryVersion` (5777),
   `_promptsRenderHistoryVersionDetail` (5794), `promptsRestoreVersion`
   (5816), `_promptsRenderPreviewPanel` (5830),
   `_promptsPopulateEntitySelectors` (5868), `promptsRunAssembledPreview`
   (5886).

   Preserve the laziness exactly: history is collapsed and unfetched by
   default, fetched on first expansion, and cached until a save or restore
   invalidates it (`promptsHistoryVersions === null` means not fetched, which
   is distinct from an empty list). A port that fetches on mount is a
   behaviour change and a load on every tab entry.

### Every commit

7. **Delete each ported function from `index.html`** in the commit that
   replaces it; extend the island entry's `retiredPrefixes` in `registry.js`
   by name, including the twenty underscore-prefixed helpers and the three
   `cw*` functions, which a `prompts` prefix scan would not catch. Add a
   `BRIEF-0059-i` comment. Extend `graph_primitive.py`'s `GONE_PLAIN`.

8. **Prune `legacy_calls.baseline`** of anything closed. Planning RECON
   expects none — the prompts tab is legacy-to-legacy today. Say so in the
   commit message either way. No commit here may add a record.

## Scope OUT

- **Activating D-0050.** The conversation-window panel stays rendered inside
  the prompts pane. Building a world-configuration surface is a doctrine
  decision and a migration brief does not carry one. `-m` re-states D-0050
  with its reactivation condition intact.
- **Making `cw` a second island.** Item 2. One island per container.
- **Debouncing, batching or otherwise "improving" `cwPatchField`.** Read its
  current write cadence and reproduce it.
- **Changing the Ollama model fetch.** `_promptsFetchOllamaModels` refetches
  on every sub-tab entry and every detail open, deliberately (the model list
  is live and never persisted server-side). A port that caches it is a
  behaviour change.
- **Turning the three-state `promptsOllamaModels` into a boolean.** Item 1.
- **Fetching history eagerly.** Item 6.
- **Any prompt-content change.** This brief moves a UI. It does not edit a
  template body, a rubric, a token or a default model.
- **Re-homing `prompt_registry.py`, `prompt_version.py`, `prompt_lean.py`,
  `prompt_model_write.py`, `conversation_window_config.py`.** All backend-only
  (M7). If any turns out to grep `index.html`, that is a deviation to report,
  and the re-homing belongs to this brief.
- **`context_disclosure_floor.py` and `conversation_summary_usage.py`.**
  Confirm they are backend-only before assuming; do not edit them otherwise.
- **The Review Queue and world CRUD.** `-k` and `-l`.
- **Any backend change.** Frontend-only.

## Invariants to defend

- **Model proposes, code judges.** Editing a prompt template edits an
  authoring artifact, not canon. Nothing in this port may acquire a path that
  writes world state.
- **Prompt versioning is append-only.** `promptsRestoreVersion` restores by
  writing a new version, not by rewriting history. Read the endpoint it calls
  and confirm the port does not turn a restore into an in-place edit.
- **No draft persistence.** Items 1 and 5. Nothing in this surface survives a
  reload or a prompt/world switch, and the port must not introduce a store
  that quietly does.
- **The dirty guard holds at every exit.** Item 4.
- **The seam only shrinks.** No commit adds a bridge-reach record.
- **Assign-then-read is forbidden** (`effect_self_write.py`). The highlighted
  token spans, the rendered usage cards, the history list are `$derived`.
- **Module budget.** Thirty-four functions across ~600 lines will breach the
  1000-line ceiling if they land in one file. The split into
  `Prompts.svelte`, `prompts.svelte.js` and
  `ConversationWindowConfig.svelte` is the expected shape; if it is still
  tight after commit 3, extract by sub-behaviour (history, preview) and say
  so — extraction by domain is the standing answer, not an exemption.

## Done means

- [ ] `python tooling/verify/checks/legacy_call.py` exits 0 after every
      commit, with the baseline unchanged at 14 records.
- [ ] `python tooling/verify/checks/creation_island.py` exits 0; scratch:
      re-add `function promptsLoadList(` and confirm rule 7 bites; revert.
- [ ] `grep -c "promptsLoadList\|_promptsRenderDetail\|promptsRestoreVersion\|cwLoadConfig\|cwPatchField" src/world_engine/cockpit/index.html`
      returns 0.
- [ ] `#creation-prompts` is an empty div with an explanatory comment.
- [ ] The commit message for commit 2 lists every `_promptsConfirmDiscard`
      call site found and reproduced.
- [ ] Live: the tab opens; the conversation-window panel loads above the
      prompts panel, same position, same heading; its refresh button works;
      patching a field persists and survives a tab switch.
- [ ] Live: the usage list renders; selecting a prompt opens its detail;
      tokens are highlighted the same way.
- [ ] Live: the model selector shows the live Ollama list; with Ollama
      unreachable it shows the unknown state, not an empty list — the
      three-state distinction is visible.
- [ ] Live: change the model on a prompt; it persists.
- [ ] Live: enter edit mode, type in the system and user bodies, add a note;
      the dirty hint appears; cancel and confirm the guard fires; re-enter,
      edit, save; the detail refreshes with the new body.
- [ ] Live: with a dirty edit, try to select another prompt, change the
      model, toggle history and switch worlds — the guard fires on each, and
      declining the confirm keeps the edit.
- [ ] Live: history is collapsed on open and fetches nothing until expanded;
      expand it, select a version, view its detail, restore it; the list
      invalidates and refetches.
- [ ] Live: the assembled preview panel populates its entity selectors and
      runs a preview.
- [ ] Live: reload the page mid-edit; the draft is gone, as designed.
- [ ] Live: switch worlds; the tab resets exactly as `_promptsWorldReset` did.
- [ ] `npm run build` succeeds; `frontend_build_fresh.py` passes.
- [ ] `python tooling/verify/run.py` exits 0.
- [ ] `module_budget.py`, `function_length.py` and `effect_self_write.py`
      pass on every file written.
- [ ] `/review-step` and `/close-step` run per commit.

## Docs to update

None. Brief `-m`, which re-states D-0050 verbatim with its reactivation
condition.
