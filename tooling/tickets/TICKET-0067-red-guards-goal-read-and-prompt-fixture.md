---
id: TICKET-0067
title: Two red guards on main — the N1 goal-read breach and the prompt-model fixture drift
type: bug
status: live-gate
created: 2026-08-20
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
brief_ids: [BRIEF-0067-a]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> B2 et j'exécuterai le ticket de bug (0067) en premier.

> G1

> Rédige le brief du ticket 0067

Decision block returned after RECON:

> A1, B1, C1

## Clarifications resolved (intake)

Surfaced by running `tooling/verify/checks/corpus_gate.py` (TICKET-0060,
BRIEF-0060-d) with every dependency installed, against `main` as fetched
2026-08-20. Two of the three failures it reports are genuine and belong
here; the third (`pipeline_state.py`) goes to TICKET-0061 by decision B2.

- **`npc_goal_read.py` is RED with 6 failures.** One locus is product code:
  `src/world_engine/observation_runner.py:129` selects `NpcGoal` inside
  `_precondition_failures`, outside the N1 allowlist. Four are check
  fixtures: `tooling/verify/checks/observation_runner.py:109,134,236,260`
  seed `NpcGoal` rows to build its test corpus.

- **The product read is a PRESENCE PROBE, not a content read.** It computes
  `{g.npc_id for g in ... status == "active"}` and uses it only to emit
  `"NPC {label} has no active goal"` as a run precondition. No
  `description`, `horizon` or any interiority field is touched. That is
  what makes A2 (simply allowlisting the runner) the wrong shape: an
  allowlist entry would license content reads the code does not currently
  perform and nothing would keep it that way.

- **The guard lapsed the same way `observation_surface.py` did.**
  `npc_goal_read.py` is linked by the Machine sections of TICKET-0013,
  -0014, -0015, -0020 and -0048. `TICKET-0051` and `TICKET-0053` — which
  authored `observation_runner.py` — link it **zero times** (measured), and
  `verify/run.py` runs only what a ticket names. Second instance of the
  pattern; the corpus gate is what made it visible.

- **`prompt_model_write.py` is RED, deterministically and independently of
  any machine.** Its fixture (`:98-106`) creates a `PromptTemplate` head
  with no `prompt_version` row. The PATCH under test summarises the row
  through `_prompt_row_summary` (`cockpit/crud/prompts.py:115`) →
  `prompt_store.current_prompt` (`prompt_store.py:32`), which raises by
  design on a versionless head. The check builds its own temp-file DB
  (`_fresh_engine()`, `:69-84`), so this is a fixture that never followed
  the prompt-versioning work — not an environment artifact and not a
  product defect.

- **`context.py` cannot host the accessor.** 979 lines against
  `module_budget.py`'s 1000-line cap, and
  `tooling/verify/baselines/module_budget.json` **does not exist** — the
  check treats a missing baseline as an empty exemption set and enforces
  the cap on every module, fail-closed. 21 lines of headroom is not a
  place to add a documented accessor inside a ticket whose purpose is
  returning guards to green.

- **`observation_reads.py` is the right layer and has the room.** 216 lines
  / 14 functions. It is already the observation domain's declared read
  module ("reads go through this one"), and its docstring already records
  its own governed relationship to an allowlist
  (`observation_socle.py`'s model-identifier rule). `observation_socle.py`
  rule 6 constrains the reverse direction only (no `Observation*` identifier
  in `context.py`/`tick*.py`), so nothing there is disturbed.

Decisions locked before any artifact was authored:

| Code | Decision |
|---|---|
| **A1** | The presence probe moves behind a **named read accessor** returning `set[str]` of NPC ids. `observation_runner.py` stops naming `NpcGoal` entirely. The return type is the structural guarantee: no caller can reach a goal's content, so the accessor cannot silently become a second content reader. The allowlist grows by one entry — a READ MODULE, definitionally a reader — never by a consumer. |
| **B1** | `tooling/verify/checks/observation_runner.py` is allowlisted by name, one entry, with the precedent already in place (`tooling/verify/checks/npc_goal_read.py` is itself allowlisted). Not a directory-wide rule (B2), not a narrowed scan scope (B3) — `tooling/` scanning is what would catch a real reader appearing in `tooling/glue/` or `tooling/pipeline_cockpit/`. |
| **C1** | The prompt fixture seeds its v1 row through `writes.prompts.write_prompt_version`, the sanctioned write path. Not a bare `Session.add(PromptVersion(...))`: `prompt_version.py`'s single-write-shape rule scans `src/` plus the migration and would not catch it in `tooling/` — exploiting a check's blind spot inside the ticket that returns checks to green is the wrong move regardless of whether it is detected. |
| **Gate linkage** | This ticket links `npc_goal_read.py` AND `prompt_model_write.py` in its own Machine-checkable section. The lapse that produced this ticket must not recur on the ticket repairing it. The corpus-wide fix (TICKET-0061, C1/C3) lands after this one. |

## Scope OUT

- **`pipeline_state.py`'s three failures** (TICKET-0036/-0048/-0062 inline
  comments on `status:`) — TICKET-0061, decision B2.
- **The corpus gate's environment contract** (C3) and linking the corpus
  gate as standing law (C1) — TICKET-0061.
- **`context.py`'s 979/1000 budget position.** Reported here, repaired
  nowhere: it is a pre-existing condition this ticket routes around rather
  than inherits. It deserves its own ticket.
- **The scan-scope asymmetry.** `npc_goal_read.py` scans `tooling/`;
  `prompt_version.py` (`_iter_py_files`) scans `src/` plus the migration
  only. Two checks, the same class of doctrine, opposite scopes. Report
  only.
- **The observation run precondition itself** (A3). Whether requiring an
  active goal to start a run is the right product rule is not reopened
  here; its behaviour is preserved byte-for-byte.
- **Frontend, schema, canon-write paths.** Untouched.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `NpcGoal` appears nowhere in `src/world_engine/observation_runner.py`
      — not in its imports, not in its body  -> verify/checks/npc_goal_read.py
- [ ] The allowlist grows by exactly two entries
      (`src/world_engine/observation_reads.py`,
      `tooling/verify/checks/observation_runner.py`) and the check exits 0,
      red-tested by removing each entry in turn  -> verify/checks/npc_goal_read.py
- [ ] The MJ boundary rule and the D1 dialogue-provenance rule are
      unchanged and still pass  -> verify/checks/npc_goal_read.py
- [ ] `prompt_model_write.py` exits 0 against its own fresh temp DB, on a
      tree with no `~/.world_engine/world_engine.db`  -> verify/checks/prompt_model_write.py
- [ ] `prompt_version.py` still exits 0 — no `PromptVersion` constructor
      reaches `Session.add` outside `write_prompt_version`  -> verify/checks/prompt_version.py
- [ ] `observation_runner.py`, `observation_socle.py`, `observation_metrics.py`
      and `json_ui_boundary.py` all still exit 0  -> verify/checks/observation_runner.py
- [ ] No import cycle is introduced  -> verify/checks/import_cycle.py
- [ ] Every touched module stays within 1000 lines and 40 functions  -> verify/checks/module_budget.py
- [ ] The new accessor is under 80 lines  -> verify/checks/function_length.py
- [ ] No unused import remains after `NpcGoal` leaves the runner  -> verify/checks/undefined_names.py

### Live  ->  human gate (Nia)

- [ ] An observation run started against a location with two NPCs both
      holding an active goal launches exactly as before.
- [ ] A run started against a location where one NPC has no active goal is
      refused with the same message text as before
      (`NPC {name} has no active goal`).
- [ ] The Prompts tab still saves a model on a template and still displays
      its version number.

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md` — one appended entry: why
  the presence probe became an accessor rather than an allowlist entry
  (the return type as the structural guarantee); the two allowlist
  additions and their distinct rationales; the second instance of the
  lapsed-guard pattern and its cross-reference to TICKET-0061's corpus
  gate; the two report-only findings (`context.py`'s budget position, the
  scan-scope asymmetry).
- `tooling/standards/DECISIONS_INDEX.md` — regenerated mechanically.
- `CLAUDE.md` — **no change.** Measured: it carries zero mentions of
  `npc_goal` or `NpcGoal`. The N1 doctrine lives in `npc_goal_read.py`'s
  docstring and in TICKET-0013. Do not add one; the file has one line of
  headroom against its 500-line cap.
- No schema changelog entry: `schema_version_touched: none`.

## Amendment (D1, escalated during BRIEF-0067-a commit 2, resolved by Nia)

Executing commit 2's `write_prompt_version` fixture fix let
`prompt_model_write.py`'s `main()` run to completion for the first time,
unmasking a second, independent, previously-invisible failure in the same
check file: `check_seed_model_free`'s `re.search(r"\bmodel\s*=", ...)`
matched three comments in `scripts/seed_pilot.py` (`:2206`, `:2227`,
`:2339`) documenting the `model=NULL (Q1)` invariant — not any actual
`model=` assignment. It was masked on `main` because
`check_write_path_and_list_route()` used to crash with an uncaught
`RuntimeError` before `main()` ever reached its `if FAILURES:` print
block. See `tooling/questions/QUESTION-TICKET-0067.md` for the full
escalation and Nia's decision (option A: repair now, as a separate third
commit).

Additional Machine-checkable criterion, landed by commit 3:

- [x] `check_seed_model_free` parses `scripts/seed_pilot.py`'s AST (never
      greps raw text) for a `model=` keyword argument on any
      `upsert_prompt_template(...)` call or a `.model =` attribute
      assignment, with a vacuous-proof guard (`seeded == 0` fails) —
      red-tested by injecting `model=` at one call site (FAIL naming that
      line) and by renaming `upsert_prompt_template` throughout (FAIL on
      the vacuous-proof guard), both reverted  ->
      verify/checks/prompt_model_write.py
