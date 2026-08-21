---
id: TICKET-0061
title: Legacy decommission and doctrine seal — the legacy document is sealed and renamed, not deleted
type: feature
status: live-gate
created: 2026-08-20
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
brief_ids: [BRIEF-0061-a, BRIEF-0061-b, BRIEF-0061-c]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Nous travaillons sur le refactor de l'index. Nous somme au ticket 0061 (le
> dernier). Fait un RECON avant de me proposé des options et regarde l'état du
> main et des décisions qui ont été prises qui peuvent influencé ce ticket.

Decision blocks returned after RECON, across two rounds:

> A Explique moi avec des exemple la différence entre A1 et A3. Pour la
> réactivation du 3D, ce sera dans longtemps (1ans et +, à ma demande). B2 et
> j'exécuterai le ticket de bug (0067) en premier. C1 , mais C3 me semble une
> meilleure chose pour l'entretiens et l'amélioration long terme de mon code,
> est-ce que je me trompe? D1 ticket de bug 0068. E1, F explique moi la
> différence entre F1 et F2 si les check existent déja, pourquoi ne pas les
> utilisés.

> A3 + 3b, F1 + ticket 0070 en pause + le claude.md doit être revus (dans un
> prochain ticket. Je pense qu'il faut faire une passe d'hygiène dessus pour
> qu'il grade seulement les informations les plus pertinantes et réfère a
> d'autre documents au besoin ( ex : conventions de code ) G1

## Clarifications resolved (intake)

Grounded by RECON-0061-a (in-conversation, report-only, anchored to
`niaairen31-ui/WG-Nia @ main` as fetched 2026-08-20). Findings that shaped
this ticket:

- **The legacy document is already Play-only.** 2 762 lines (from 12 708):
  420 lines of inline `<style>`, 177 of markup, 2 145 of `<script>` holding
  73 top-level functions — all Play (`scene*`, `play*`, transcript,
  `spatial*`). 30 inline handlers (from 319), 36 top-level globals (from
  175, ~30 of them `_spatial*`). Zero `author*`, `region*`, `batch*`,
  `observation*`, `review*` remain.

- **The shell→legacy coupling is exactly four points.** The iframe
  (`LegacyFrame.svelte:21`), `showSurface('play')` (`App.svelte:28` →
  `bridge.js:33`), `hideLegacyHeader()` (`App.svelte:41`), and
  `initCreationMount(legacyDocument())` (`App.svelte:43`, listening for
  `mutations:proposed` emitted by Play's `analyzeConv`). `legacyCall`
  (`bridge.js:68`) has **zero call sites** in `frontend/src` — a dead
  export. `legacy_calls.baseline` holds one record:
  `frontend/src/App.svelte::showFn::TICKET-0061`.

- **Two decisions in the append-only registry contradict each other on
  Play's fate.** `ARCHITECTURE_DECISIONS.md:10973` (TICKET-0056 entry):
  "`play` survives to TICKET-0061 **and beyond**, until its own rewrite."
  `ARCHITECTURE_DECISIONS.md:12015` (TICKET-0060 entry): "`TICKET-0061`
  **empties `LEGACY_MOUNTS` and retires `cockpit/index.html` entirely**."
  The same conflict is carved into `frontend/src/legacy/registry.js` five
  lines apart: the comment says `play` *survives at* TICKET-0061, the field
  says `retiredBy: 'TICKET-0061'`. Q2 of the workstream map locked the
  former. This ticket resolves it in favour of TICKET-0056's entry.

- **`legacy_mount.py` rule 3 validates the FORMAT of `retiredBy` and nothing
  else** (`RETIRED_BY_RE = ^TICKET-\d{4}$`). It never checks that the named
  ticket exists, nor that it is not already `done`. Left as-is, a sealed
  `retiredBy: 'TICKET-0061'` becomes a well-formed falsehood blessed by a
  green check — a future reader (human or Claude Code doing RECON) reads the
  registry, sees a done ticket, and concludes Play was retired.

- **Deleting the legacy document turns 6 checks RED — measured, not
  inferred.** Built as an experimental tree (`rm index.html`, corpus run):
  `legacy_mount.py`, `stylesheet_partition.py`, `graph_primitive.py`,
  `review_component.py`, `faction_roster_panel.py`, `schema_0024.py`.
  Tolerant: `page_contract.py`, `creation_island.py`. **9 sites hard-code
  the path**: 8 checks + `app.py:66`.

- **The retirement alarms fire exactly as designed.** Second experimental
  tree (`LEGACY_MOUNTS` emptied, document kept):
  `stylesheet_partition.py` rule7 (legacy) emits its C3 retirement message
  verbatim; `legacy_mount.py` fails on `zero LEGACY_MOUNTS entries parsed` —
  which is its vacuous-proof guard, not an alarm: the check is structurally
  built to shrink *to one*, never to zero. Under this ticket's decision
  neither fires, and both stay live and meaningful.

- **`main` carries three genuine REDs, all outside the frontend scope.**
  Measured by running `corpus_gate.py` with every dependency installed:
  `npc_goal_read.py` (6 failures, incl. `src/world_engine/observation_runner.py:129`
  — product code, an N1 doctrine breach), `pipeline_state.py` (3 failures:
  TICKET-0036/-0048/-0062 carry inline comments on their `status:` field),
  and `prompt_model_write.py` (deterministic, machine-independent: the check
  builds its own temp DB via `_fresh_engine()`, inserts a `PromptTemplate`
  with no `prompt_version` row, and `crud/prompts.py:115` →
  `prompt_store.current_prompt` raises — a fixture that never followed the
  prompt-versioning work).

- **`corpus_gate.py` is executed by no gate.** TICKET-0060's
  Machine-checkable section links 13 arrows and not the corpus gate itself.
  The gate that proves "every guard is live" is run by nothing. This is the
  "proves X, not Y" pattern at its fourth consecutive occurrence.

- **The corpus gate's ENVIRONMENT classification is measurably weak.** With
  five dependencies absent (`sqlalchemy`, `sqlmodel`, `fastapi`, `httpx`,
  `pyflakes`), it reported `0 environment, 0 timeout, 6 other` — setup noise
  indistinguishable from regression. `MODULE_RE` only matches a bare
  `No module named '...'`; a wrapped one (`observation_surface` rule 5), a
  check that handles its own absence (`pyflakes is not installed`), and a
  `$ pip install httpx2` message all pass through. Its DB surface, by
  contrast, is nil: 19 checks import the DB layer, 18 self-seed via
  TICKET-0049's test-DB infrastructure and pass with no database on disk,
  and **zero** read the production DB.

- **The legacy document is exempt from both budget checks.**
  `module_budget.py` covers `src/**/*.py` (AST) and `frontend/src/**/*.{svelte,js}`
  (1000-line cap); `function_length.py` covers `src/**/*.py`. Neither sees
  `cockpit/index.html`: 2 762 lines against a 1000-line cap elsewhere,
  `sendPlayerLine` at ~247 lines against an 80-line cap elsewhere. Under
  this ticket's decision that exemption lives another year or more.

- **`CLAUDE.md` describes a state that no longer exists, and its budget is
  contourned.** `:55` names `_buildRuntimeCreationTabs()`/`refreshCreationTabs()`
  as living in `index.html` (measured: 1 textual occurrence, in a comment;
  the implementation is `frontend/src/creation/tabs.js`). `:58` names
  `batchRenderAll`/`batchReviewDescriptor` as `index.html` globals reached
  through a bridge installed by `creation/mount.js` (measured:
  `batchRenderAll` = **0** occurrences; `reviewRegister` = **0**;
  `RoomBatch.svelte` carries them; no such bridge exists in `mount.js`).
  `claude_md_contract.py` never guarded this class of claim: its rule 4
  covers `tooling/...` paths only, and asserts path EXISTENCE, not symbol
  LOCATION. Separately, the file is 499 lines against a 500-line cap while
  8 lines carry 30 % of its 45 979 characters (line 278 = 5 180 chars, line
  58 = 3 438) — the budget measures lines, and lines grew instead.

Decisions locked before any artifact was authored:

| Code | Decision |
|---|---|
| **A3** | Play is **sealed, not migrated**. This ticket is a seal, per PART C rule 1 of the workstream map. `LEGACY_MOUNTS` keeps `play`; the legacy document stays. Its migration becomes **TICKET-0069**, deposited now with `status: paused` and an explicit human gate ("opened at Nia's request, not before the 3D decision; horizon 1 year+"). The contradiction in the decision registry is resolved by SUPPLEMENT in favour of TICKET-0056's entry — the TICKET-0060 entry is never rewritten. |
| **3b** | `legacy_mount.py` rule 3 is extended: for every `LEGACY_MOUNTS` entry, the file `tooling/tickets/TICKET-{retiredBy}-*.md` must **exist** and its `status` must **not** be `done`. A `retiredBy` pointing at a finished ticket while the mount still lives becomes structurally unconstructible. Vacuous-proof: a missing ticket file is a FAILURE. This is what makes A3 a guarantee rather than a tidy intention — and it is inexpressible under the alternative, where `retiredBy` would name this very ticket. |
| **B2** | `pipeline_state.py`'s three failures are repaired **here** (governance artifacts are the seal's own domain). `npc_goal_read.py` goes to **TICKET-0067**, executed first. |
| **G1** | `prompt_model_write.py`'s fixture drift rides **TICKET-0067** as a second, isolated commit — same nature (a red guard on `main`, outside the frontend scope), one ticket that returns the corpus to green before the seal. |
| **C1** | This ticket links `corpus_gate.py` in its own Machine-checkable section, and `CLAUDE.md` records as standing law that every ticket must link it. |
| **C3** | Locked together with C1, not as an enhancement but as its precondition: the environment contract is hardened so a missing dependency is classified `ENVIRONMENT` wherever it surfaces (wrapped, self-reported, or as an install instruction), backed by a declared list of required external tools checked before execution. `ENVIRONMENT` stays a FAILURE, never a skip, but is counted separately from regressions. No DB clause: the measured production-DB dependency of the corpus is zero. |
| **D1** | Play's stale `WORLD_ID` (written once at `index.html:1746` by `loadBootstrap()`, never refreshed by `activateWorldCascade`) — the same defect TICKET-0060/F1 fixed for Observation — becomes **TICKET-0068**, executed after this ticket. Not repaired here: it would reopen the shell→legacy bridge this ticket exists to freeze. |
| **E1** | `cockpit/index.html` is renamed `cockpit/legacy.html`. The original deferral's rationale ("the migration retires those checks anyway", `ARCHITECTURE_DECISIONS.md:11042`) is false under A3, so the deferral expires here. 8 checks + `app.py:66` + `CLAUDE.md:414`. |
| **F1** | The two measured-false doctrine lines (`CLAUDE.md:55`, `:58`) are repaired, and `:17-18`/`:414` rewritten to state the sealed posture. Net-neutral or reducing: the file has one line of headroom. |
| **F2 → TICKET-0070** | A `claude_md_contract.py` rule asserting symbol LOCATION (for every `` `symbol` (`path`) `` claim, the symbol occurs in the path) is deposited now with `status: paused`. Out of this ticket: a new parser with real false-positive surface (a prototype found 8 candidate pairs at ~40 % noise) does not belong in the ticket that closes a seven-ticket series. |
| **Hygiene → TICKET-0071** | A `CLAUDE.md` hygiene pass — keep only what is law, delegate the rest to the documents that already exist (`tooling/standards/code_standards.md`, `ARCHITECTURE_DECISIONS.md`, the schema changelog) — is deposited now with `status: paused`. It must also repair the budget itself, which is measurably contourned by line length. |

Brief decomposition (three briefs, sequential; each merges to `main` before
the next opens):

- **BRIEF-0061-a** — the corpus back to green, and the gate that keeps it
  there. `pipeline_state.py`'s three ticket front-matters repaired (B2);
  `corpus_gate.py`'s environment contract hardened (C3); the corpus gate
  linked in this ticket's own Machine section and recorded as standing law
  (C1). Tooling and governance artifacts only, zero product code.
  **HARD PREREQUISITE: TICKET-0067 merged to `main`.** Without it this
  brief's own gate cannot pass.
- **BRIEF-0061-b** — the seal. `retiredBy` repointed to `TICKET-0069` (A3);
  `legacy_mount.py` rule 3 extended (3b); `legacyCall` removed from
  `bridge.js` and `legacy_calls.baseline` shrunk accordingly; the legacy
  document brought inside `module_budget.py` as a ratchet at its measured
  current size. **HARD PREREQUISITE: `TICKET-0069-*.md` on disk**, or rule
  3b is red by construction.
- **BRIEF-0061-c** — the rename and the doctrine. `cockpit/index.html` →
  `cockpit/legacy.html` across 8 checks + `app.py:66` (E1); `CLAUDE.md`
  repaired (F1); the `ARCHITECTURE_DECISIONS.md` supplement resolving the
  registry contradiction and correcting TICKET-0066's expired exclusion.
  Last, so the rename's churn never collides with the seal's edits.

## Scope OUT

Every one of these was discussed during planning and is deliberately not
built here. An executor finding any of them is REPORT ONLY.

- **Play's migration out of the legacy document.** TICKET-0069, `paused`.
  No Play function, handler, global or markup node is moved, ported,
  refactored or deleted by this ticket. The rename in BRIEF-0061-c is a path
  change and nothing else — the document's bytes below the `<head>` are
  untouched.
- **The `WORLD_ID` fix.** TICKET-0068.
- **`npc_goal_read.py` and `prompt_model_write.py`.** TICKET-0067.
- **The symbol-location rule.** TICKET-0070, `paused`. `claude_md_contract.py`
  gains no new rule here.
- **The `CLAUDE.md` hygiene pass.** TICKET-0071, `paused`. BRIEF-0061-c
  repairs two false lines and rewrites four; it does not restructure the
  file, does not move content to other documents, and does not touch the
  line budget.
- **F3 — `start_run` deriving the active world server-side.** Named deferral
  from TICKET-0060, a backend write, escalation under the frontend-only
  rule. Its condition ("a ticket opened after TICKET-0061") is now
  satisfiable; opening it is not this ticket's job.
- **D-0063-scoped-component-styles does NOT reactivate.** Its condition —
  "no document outside the shell consumes these rules" — remains false: the
  legacy document lives on. `creation.css` stays a file.
- **Content-hashing `shared.css` / `creation.css` does NOT become
  available.** TICKET-0066 recorded that exclusion as expiring "on its own
  at TICKET-0061"; under A3 it does not. BRIEF-0061-c corrects that record
  by supplement — it does not implement the hashing.
- **`stylesheet_partition.py` rule7 (legacy) is NOT retired.**
  `LEGACY_MOUNTS` stays non-empty, so its retirement condition is unmet and
  its alarm must remain silent. Removing it "because the series is closing"
  is exactly the qualitative reasoning it was built to replace.
- **`legacy_mount.py` is NOT restructured for an empty registry.** Its
  vacuous-proof rule 1 stays as written.
- **Region's parallel field renderer** (`ARCHITECTURE_DECISIONS.md:11282`,
  RECON-SUPPLEMENT-0058) — a named, still-unopened convergence candidate.
  Untouched.
- **Backend, schema, canon-write paths, mutation gating.** Untouched. If a
  seal step appears to need one, that is an escalation.

## Invariants to defend

- **PART C rule 1 — fail-closed guards never lapse.** This ticket only ever
  makes a check stricter, re-points it, or leaves it alone. No check is
  disabled, weakened, or made tolerant. The rename must leave all 8
  index-anchored checks green on the same assertions they hold today.
- **PART C rule 2 — frontend-only.** BRIEF-0061-a touches governance
  artifacts and tooling; -b and -c touch tooling, `bridge.js`, `app.py`'s
  path constant and documentation. Nothing under `src/world_engine/` outside
  `cockpit/app.py:66` and the renamed file.
- **PART C rule 3 — the 3D guard rail is CROSS-REFERENCED, never restated.**
  TICKET-0055/-0056/-0057 each held this line: restating doctrine is how
  doctrine drifts. The seal is the strongest temptation to re-nail it. Do
  not.
- **History is sacred.** The `ARCHITECTURE_DECISIONS.md` work is a
  SUPPLEMENT appended at the end. The TICKET-0056 and TICKET-0060 entries
  are not edited, not annotated in place, not reconciled by rewriting.
  Neither is the `registry.js` comment history — the stale sentence gets a
  correction beneath it, not a deletion.
- **`CLAUDE.md` budgets.** ≤ 500 lines total (currently 499); the
  `### File structure` section ≤ 80 lines (currently 68). F1 must be
  net-neutral or reducing.
- **`legacy_mounts.baseline` may only shrink**, and rule 3b must not make
  the baseline's own maintenance load-bearing.

## Prerequisites (not acceptance criteria)

- `TICKET-0067` is `done` on `main` before BRIEF-0061-a opens.
- `tooling/tickets/TICKET-0069-play-surface-migration.md` is on `main` before
  BRIEF-0061-b commit 2. Rule 3b reads it.
- Brief order is hard: `-a` -> `-b` -> `-c`.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] The corpus gate exits 0 with `0 environment, 0 crash, 0 timeout, 0 other`  -> verify/checks/corpus_gate.py
- [ ] Red-test A: a synthetic check that appends to `FAILURES` then raises is reported as `CRASH ... verdict UNKNOWN` with its masked failure recovered and printed; reverted  -> verify/checks/corpus_gate.py
- [ ] Red-test B: a nonexistent name in `REQUIRED_TOOLS` yields `ENVIRONMENT: required tool ... is not installed` before any check runs; reverted  -> verify/checks/corpus_gate.py
- [ ] TICKET-0036/-0048/-0062 carry a bare enum `status:`, each relocated comment appended verbatim as a `## Status note`  -> verify/checks/pipeline_state.py
- [ ] `frontend/src/legacy/registry.js` reads `retiredBy: 'TICKET-0069'`; rule 3b red-tested three ways (nonexistent ticket, status `done`, file removed), each reverted  -> verify/checks/legacy_mount.py
- [ ] `legacy_calls.baseline` reads `frontend/src/App.svelte::showFn::TICKET-0069`; `legacyCall` still defined exactly once and exported in `bridge.js`  -> verify/checks/legacy_call.py
- [ ] The legacy document is named with a ceiling equal to its committed line count; +1 line FAILS, -1 line FAILS instructing the constant be lowered, file absent FAILS; each reverted  -> verify/checks/module_budget.py
- [ ] `src/world_engine/cockpit/legacy.html` exists, `index.html` does not, content hash unchanged across the move  -> verify/checks/creation_island.py
- [ ] Renamed anchor holds its assertion against the new path  -> verify/checks/faction_roster_panel.py
- [ ] Renamed anchor holds its assertion against the new path  -> verify/checks/graph_primitive.py
- [ ] Renamed anchor holds its assertion against the new path  -> verify/checks/page_contract.py
- [ ] Renamed anchor holds its assertion against the new path  -> verify/checks/review_component.py
- [ ] Renamed anchor holds its assertion against the new path  -> verify/checks/schema_0024.py
- [ ] Renamed anchor holds its assertion; rule7 (legacy) alarm silent and armed  -> verify/checks/stylesheet_partition.py
- [ ] `CLAUDE.md` is within its 500-line cap and carries no claim placing `batchRenderAll` or `buildRuntimeCreationTabs` in the legacy document  -> verify/checks/claude_md_contract.py
- [ ] The appended supplement is indexed  -> verify/checks/decisions_index.py

### Live  ->  human gate (Nia)

- [ ] `GET /` serves the shell; Play renders inside the iframe, unchanged in
      appearance and behaviour.
- [ ] Play's four sub-tabs (Discussion, Historique, Mes savoirs, Play
      spatiale) all work; a conversation can be started, sent and ended; the
      spatial canvas accepts WASD.
- [ ] `analyzeConv` still reaches the Review Queue filter across the iframe
      boundary (`mutations:proposed`).
- [ ] `GET /legacy` returns 200 and the same bytes as before the rename; the
      direct escape hatch still works.
- [ ] Creation and Observation are unaffected.
- [ ] `/review-step` and `/close-step` run on each brief.

## Docs to update

- `CLAUDE.md` — `:17-18` (sealed posture), `:55` and `:58` (false claims),
  `:414` (file tree + new name), plus the standing law that every ticket
  links `corpus_gate.py`. Net-neutral or reducing.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` — one appended supplement:
  the Play-fate contradiction resolved in favour of TICKET-0056's entry;
  rule 3b's rationale; TICKET-0066's expired exclusion corrected; the four
  named deferrals (0068, 0069, 0070, 0071) with their reactivation
  conditions, the 3D one recorded explicitly as a HUMAN gate rather than a
  structural condition.
- `tooling/standards/DECISIONS_INDEX.md` — regenerated mechanically.
- `Active_project.md` — the workstream map's PART B entry for 0061 and its
  PART D Q2 both need the sealed outcome recorded.
- No schema changelog entry: `schema_version_touched: none`.
