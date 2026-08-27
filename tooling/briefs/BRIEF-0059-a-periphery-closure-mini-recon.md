# BRIEF — Step "periphery closure mini-RECON"

Ticket: TICKET-0059. First brief of the chain. **REPORT ONLY — this brief
changes no code, no docs, no baseline.** Its output is a findings file that
briefs `-b` through `-m` cite by finding number.

## Context

TICKET-0055..0058 landed. `index.html` went 12708 -> 8903 lines;
`frontend/src/creation/` holds 30 files; `CREATION_ISLANDS` declares five
keys. What remains on the Creation side is a periphery of standalone tabs
plus a residue inside already-converged islands.

The planning RECON for this ticket was performed against the `main` tarball
on 2026-08-03 and produced the anchors below. This brief re-runs those
measurements against `main` as it stands at execution time and either
confirms them or stops the chain. Every subsequent brief is written on top of
these numbers; a silent drift would make ten briefs wrong at once.

## Scope IN

Produce `tooling/briefs/RECON-0059-a-findings.md` containing findings **M1**
through **M8** below, each with `file:line` anchors read from the working
tree at execution time.

1. **M1 — the `legacyCall` census.** Enumerate every call site of
   `legacyCall(` under `frontend/src/`, excluding the definition itself at
   `frontend/src/legacy/bridge.js:153` and any occurrence inside a comment.
   Report as `file:line -> 'fnName'`.

   Planning RECON found **20 sites in 5 files**:

   ```
   frontend/src/creation/Sheet.svelte:167   '_authorResetCreateDrafts'
   frontend/src/creation/Sheet.svelte:311   'authorLoadGoals'
   frontend/src/creation/Sheet.svelte:317   'authorLoadDiscDetails'
   frontend/src/creation/Sheet.svelte:393   'creationRefreshList'
   frontend/src/creation/Sheet.svelte:415   '_authorGetPendingCreationMutationId'
   frontend/src/creation/Sheet.svelte:465   '_authorConsumePendingCreationMutationId'
   frontend/src/creation/Sheet.svelte:474   'creationRefreshList'
   frontend/src/creation/Sheet.svelte:475   '_authorNotifySaved'
   frontend/src/creation/Sheet.svelte:589   'authorRenderRelations'
   frontend/src/creation/Sheet.svelte:590   'authorRenderRelationForm'
   frontend/src/creation/Sheet.svelte:593   'authorRenderKnowledge'
   frontend/src/creation/Sheet.svelte:594   'authorRenderKnowledgeForm'
   frontend/src/creation/Sheet.svelte:640   'authorBackfillGoals'
   frontend/src/creation/Sheet.svelte:643   'authorRenderGoalForm'
   frontend/src/creation/Sheet.svelte:650   'authorRenderDiscDetailForm'
   frontend/src/creation/Region.svelte:311  'creationRefreshList'
   frontend/src/creation/RoomBatch.svelte:246 'creationRefreshList'
   frontend/src/creation/FactionRoster.svelte:58 'creationOpenEntityFrom'
   frontend/src/creation/locationType.js:46 'genericModalOpen'
   frontend/src/creation/locationType.js:104 'genericModalClose'
   ```

   `frontend/src/creation/GeneratePanel.svelte:5` mentions `legacyCall` inside
   a comment and is NOT a call site. Confirm that classification.

   **This census is the seed value for `-b`'s baseline.** If the count
   differs, report the difference and STOP (see Stop rule).

2. **M2 — the residual `author*` cluster.** Confirm that exactly the
   following `author*` / `_author*` declarations remain in `index.html`, and
   report each one's current line:

   - Relations: `authorRenderRelations` (6610), `authorRenderRelationForm`
     (6641), `authorAddRelation` (6670), `authorUpdateRelation` (6682),
     `authorDeleteRelation` (6693), `authorRelationRequest` (6698), plus the
     `RELATION_DIRECTIONS` const declared between them (~6638).
   - Knowledge: `authorRenderKnowledge` (6719), `authorRenderKnowledgeForm`
     (6749), `authorAddKnowledge` (6770), `authorUpdateKnowledge` (6783),
     `authorDeleteKnowledge` (6796), `authorKnowledgeRequest` (6801).
   - Goals: `authorLoadGoals` (6824), `authorRenderGoals` (6840),
     `authorRenderGoalPrerequisites` (6884), `authorAddGoalPrerequisite`
     (6914), `authorRemoveGoalPrerequisite` (6925),
     `authorSetGoalPrerequisites` (6931), `authorAttachGoalLink` (6946),
     `authorDetachGoalLink` (6962), `authorRenderGoalForm` (6972),
     `authorAddGoal` (6990), `authorSetGoalStatus` (6998),
     `authorBackfillGoals` (7009), `authorGoalRequest` (7039).
   - Discipline details: `authorLoadDiscDetails` (6193),
     `authorRenderDiscDetails` (6204), `authorRenderDiscDetailRow` (6235),
     `authorRenderDiscDetailForm` (6259), `authorAddDiscDetail` (6294),
     `authorDeleteDiscDetail` (6323), `authorResetDiscDetail` (6333),
     `authorEditDiscDetail` (6346), `authorSaveDiscDetail` (6381).
   - Lifecycle / shared: `authorSelectEntity` (6422), `_authorNotifySaved`
     (6451), `authorDelete` (6592), `_authorGetPendingCreationMutationId`
     (6581), `_authorConsumePendingCreationMutationId` (6587),
     `_authorResetCreateDrafts` (5912), `authorGetSelectedEntityId` (3236),
     `authorAddLedgerEntry` (4801).

   For **each** of the four editor families, additionally report: the DOM
   container id it writes into (`author-relations`, `author-knowledge`,
   `author-goals`, `author-disc-list`), every API path it calls, and every
   inline `on*` handler name emitted in its HTML strings.

3. **M3 — which residual functions have callers OUTSIDE their own family.**
   For each name in M2, list every caller. Planning RECON established that
   `authorSelectEntity`, `authorDelete`, `authorGetSelectedEntityId`,
   `_authorNotifySaved`, `_authorResetCreateDrafts` and the two pending-
   mutation-id helpers are reached from `Sheet.svelte` and/or from other
   legacy clusters. `authorAddLedgerEntry` belongs to the `registre` tab, NOT
   to the sheet (per `CREATION_ISLANDS.entitySheet`'s own note). Confirm that
   attribution — it decides whether `authorAddLedgerEntry` closes in `-d` or
   in `-h`.

4. **M4 — the location-tree duplication (lock C1).** Report the full bodies
   and line spans of `_npcAgentTreeHtml` and `_linkAgentTreeHtml`, plus every
   CSS class each emits and every selector rule in the `<style>` block that
   matches those classes. State explicitly whether the two functions are
   structurally identical modulo (a) the radio `name` attribute, (b) the
   `onchange` handler name, (c) the selected-id variable read, or whether
   there is a behavioural difference. **If they differ behaviourally, say how
   and STOP** — lock C1 assumed a copy-paste and a single
   `LocationTree.svelte` cannot absorb a real difference silently.

   Also report: whether either agent's tree is a consumer of the governed
   review component (`reviewRegister` / `reviewCascade`). Planning RECON
   concluded they are location pickers, not review cascades. Confirm.

5. **M5 — the standalone tab clusters.** For each of `competences`,
   `registre`, `artefacts`, `prompts`, `intrigues`, `pj`/`pc`/`skill`,
   Review Queue + mutation review, and `world*`, report: function names, line
   spans, the container id(s) in the body markup, whether the tab declares
   `loader` / `state.onWorldSwitch` / `slots` in `CREATION_TABS`
   (`index.html:4260`), and every API endpoint touched.

   Planning RECON spans, to be confirmed:

   ```
   prompts          31 fns  5256..5854
   competences      12 fns  4222..4765
   registre          5 fns  4224..4863
   intrigues        13 fns  4226..5157
   pj/pc/skill      12 fns  7069..7342
   queue+mutation   13 fns  2079..3132
   world             6 fns  8400..8513
   artefacts         1 fn   5203
   npcAgent         29 fns  7395..7811
   linkAgent        27 fns  7882..8280
   chrome           18 fns  3302..6560
   ```

   Note that the queue + mutation-review cluster is interleaved with Play
   scene code (workstream map A2). Report precisely which of those 13
   functions are read by Play and which are Creation-only — a function used
   by both cannot be deleted in `-k`.

6. **M6 — the chrome inventory (lock D1).** Report, with anchors: every
   function in the chrome cluster; the `CREATION_TABS` literal's full key
   list and every field each key declares; the `#ctab-*` static buttons in
   the body markup (`index.html:1213-1226`) and the shell band markup
   (`1235-1275`); `_buildRuntimeCreationTabs` (5940) and
   `refreshCreationTabs` (5979) with the exact registry fetch they read;
   `route:subtab` emission (4533); and every element id under
   `#creation-view` (1209) with the module that currently owns it.

   Additionally: enumerate every `document.getElementById(...)` in
   `frontend/src/creation/*` that resolves against the **legacy** document
   rather than the component's own subtree. Those are the bindings the chrome
   inversion must sever, and they are invisible to the `legacyCall` census.

7. **M7 — check anchoring.** For each of `page_contract.py`,
   `creation_return_nav.py`, `faction_roster_panel.py`, `review_component.py`,
   `schema_0024.py`, `legacy_mount.py`, `creation_island.py`,
   `graph_primitive.py`: report every path constant it reads, every pattern
   it greps, and whether that pattern's target is scheduled to move in this
   ticket. Name the brief that must re-home it.

   Report the vacuous-proof guard each one uses, so `-b`'s new check can
   follow the same idiom (`FAILURES` list, `_report_and_exit`, `ROOT` via
   `parents[3]`).

8. **M8 — module budget headroom.** Report current line counts for every
   file under `frontend/src/creation/` and for `src/world_engine/cockpit/
   index.html`. Flag any file within 150 lines of the 1000-line module budget
   (R5) — `Sheet.svelte` is the likely candidate and `-c`/`-d` add to it.
   State whether `module_budget.py` currently covers `frontend/src/`.

## Scope OUT

- **Any code change whatsoever.** No file under `src/` or `frontend/` is
  edited by this brief. If a bug is found, REPORT ONLY.
- **Creating `legacy_call.py` or its baseline.** Brief `-b`.
- **Creating `LocationTree.svelte`.** Brief `-f`.
- **Touching `LEGACY_MOUNTS` or `legacy_mounts.baseline`.** Brief `-l`.
- **Re-homing any check.** Each re-homing lands in the brief that moves its
  target.
- **Doc updates, including `ARCHITECTURE_DECISIONS.md`.** Brief `-m`.
- **Deciding whether `prompts` should become a top-level surface.** Recorded
  as deferral D-0059-prompts-surface; not this ticket's question.
- **Any backend change.** Frontend-only (cross-cutting rule 2).

## Invariants to defend

None threatened — this brief writes one findings file and nothing else. The
invariant it *serves* is "RECON before any brief": every downstream brief in
this chain cites M1..M8 by number, and none may execute on planning-session
anchors alone.

## Stop rule (hard)

STOP and escalate to Nia, without proceeding to `-b`, if any of the
following holds:

- The `legacyCall` census (M1) is not 20 sites in exactly those 5 files.
- Any `author*` name listed in M2 is absent, or an unlisted `author*`
  declaration exists in `index.html`.
- M4 finds a behavioural difference between the two location trees.
- M5 finds a queue/mutation function read by both Play and Creation that
  planning RECON did not anticipate.
- M7 finds a check anchored on `index.html` that this ticket's chain does not
  name a re-homing brief for.

An escalation here is correct behaviour and produces an amendment to
TICKET-0059, not a silent adaptation inside a later brief.

## Done means

- [ ] `tooling/briefs/RECON-0059-a-findings.md` exists and contains M1..M8,
      each with `file:line` anchors read this session.
- [ ] `git status` shows exactly one added file and zero modified files.
- [ ] Every planning-RECON figure quoted in Scope IN is explicitly marked
      CONFIRMED or CORRECTED in the findings file — none left unaddressed.
- [ ] Every M4 and M7 question is answered with a yes/no, not a hedge.
- [ ] Any Stop-rule trigger is reported at the top of the findings file and
      no further brief is started.

## Docs to update

None. This brief IS the finding record. `ARCHITECTURE_DECISIONS.md` and
`CLAUDE.md` are touched only at `-m`.
