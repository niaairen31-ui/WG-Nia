# Code standards

Seeded: 2026-07-13, from the one-time SEEDING review (26 tickets closed,
schema v1.79, `main`). Amendments happen only through a ticket; rationale for
any rule change is appended to `ARCHITECTURE_DECISIONS.md`, never rewritten
here silently.

Every rule carries a tier:

- **enforced** -> a fail-closed check exists in `tooling/verify/checks/`.
- **advisory** -> reviewed at `/review-step`, no automated check. An advisory
  rule that is violated twice across distinct tickets becomes a promotion
  candidate (new check).

A standard without a reader is a convention; enforced rules name their check.

## 1. Ratified emergent norms

These describe what the codebase already does (measured at seeding:
359/363 functions return-annotated, zero bare excepts, zero TODO markers).
They are ratified so drift becomes visible, not to change behavior.

- **S1 (advisory)** Every function declares a return type annotation.
- **S2 (advisory)** No bare `except:`. Catch the narrowest exception that the
  handler can actually act on. `except Exception` is permitted only at
  process boundaries: FastAPI route bodies, the tick loop, CLI entry points.
- **S3 (advisory)** Database access uses SQLModel `select()`. Raw `text()` is
  permitted only in `src/world_engine/writes.py` (chokepoint helpers),
  `src/world_engine/models.py` (DDL/indexes), and `scripts/migrate_*.py`.
- **S4 (advisory)** Multi-row canon mutations run under a SAVEPOINT
  (`begin_nested`) and roll back all-or-nothing. (Restates the mutation
  atomicity doctrine; listed here so code review checks for it explicitly.)
- **S5 (advisory)** All strings in `src/` are English, including CLI-facing
  progress and warning text. (Known violations in `analyzer.py` are fixed by
  the remediation ticket, section 4.)

## 2. Corrective rules

Each rule targets a concrete failure mode observed in the ticket history.

- **R1 (enforced) Function length ceiling.**
  Any function created or modified in a commit must be <= 80 lines
  (AST `end_lineno - lineno + 1`, decorators excluded). Existing violations
  are frozen in `tooling/verify/baselines/function_length.json`
  (name + file + length). The check fails if: (a) a non-baselined function
  exceeds 80 lines, or (b) a baselined function grows past its recorded
  length. Baselined entries may only shrink or disappear. The baseline file
  is a transition artifact: it is deleted at the final remediation stage
  (section 4, stage g), after which the check runs with no exemptions.
  Check: `function_length.py`.
  Failure mode addressed: `say` reached 1130 lines (958-line nested
  `_stream`), `_apply_mutation` 682, through per-ticket accretion with no
  tripwire.

- **R2 (enforced) Single LLM-parse chokepoint.**
  All parsing of local-model output lives in `src/world_engine/llm_parse.py`
  (`_extract_json_array` and successors move there from `analyzer.py`).
  Mechanic: `json.loads` may appear only in `llm_parse.py` plus a named
  allow-list for non-model JSON (config loads, request bodies already
  validated by FastAPI). Zero parsed occurrences outside the allow-list is
  required; an empty allow-list section in the check is a failure, not a
  vacuous pass.
  Check: `llm_parse_chokepoint.py`.
  Failure mode addressed: 7 independent parse sites in `entity_author.py`;
  model output shape drift produced the subculture blob bug
  (bug_log 2026-07-03, corrected by BRIEF-0025-d) — the exact class a single
  normalizing chokepoint contains.

- **R3 (enforced) No `print()` in `src/`.**
  `src/world_engine/` uses the `logging` module
  (`_log = logging.getLogger(__name__)` at module top). `print` remains
  legitimate in `scripts/` (operator-facing CLI output).
  Check: `no_print_in_src.py`.
  Failure mode addressed: 38 `print()` calls in `analyzer.py` invisible to
  any log capture during live play.

- **R4 (advisory) Cockpit app growth budget.**
  `cockpit/app.py` must not gain new top-level route handlers; new API
  surface goes into route modules under `cockpit/` included via
  `app.include_router`. R5 bounds the file structurally; this rule directs
  where new surface goes.

- **R5 (enforced) Module budget.**
  Any module in `src/` stays within <= 40 top-level functions and methods
  (AST count) and <= 1000 physical lines. Both dimensions are checked in
  the same pass; exceeding either fails. Existing violations are frozen in
  `tooling/verify/baselines/module_budget.json` (file + function count +
  line count); a baselined module may not grow past its recorded values on
  either dimension, and entries may only shrink or disappear. The baseline
  is a transition artifact, deleted at stage g alongside R1's.
  No permanent exemptions: when a doctrinal registry module such as
  `writes.py` legitimately needs to grow past the cap, the failing check is
  the intended tripwire — it forces the split (e.g. a `writes/` package by
  domain) at exactly the moment it becomes necessary, not before.
  Check: `module_budget.py`.
  Failure mode addressed: `cockpit/app.py` reached 6180 lines / 103
  functions and `cockpit/crud.py` 2932 / 109 with no structural bound;
  function-level ceilings alone push decomposition pressure into the file,
  which must have somewhere bounded to go.
  Baseline at seeding: `cockpit/app.py` (103f/6180l), `cockpit/crud.py`
  (109f/2932l), `tick.py` (20f/1803l), `writes.py` (32f/1607l — line
  dimension only at current count), `models.py` (1188l), `entity_author.py`
  (1062l).

- **R6 (advisory) No catch-all modules.**
  No `utils/`, `helpers/`, `common/` or equivalent grab-bag module may be
  created. A shared helper exists only in a module named for a single
  responsibility, created deliberately (`llm_parse.py`, `writes.py`
  pattern). Backend decomposition is by domain, not by technical layer:
  route handlers under `cockpit/routes/{play,mutations,creator,prompts}.py`,
  domain logic in domain-named modules. Existing chokepoints (`writes.py`
  as the write-access layer, validation inside write helpers) are not
  re-homed into generic layers.
  Failure mode addressed: grab-bag modules hide existing helpers, inviting
  near-duplicates beside them — the BRIEF-0024-d parallel-structure class.

- **R7 (advisory) Extraction naming and inventory.**
  Functions extracted during decomposition carry a domain prefix
  (`_say_*`, `_mutation_*`, `_tick_*`, ...) so `grep _<domain>_` lists all
  siblings. Any brief that extracts helpers must first inventory the
  existing helpers of that domain (same obligation as tracing UI-visible
  fields) and reuse before creating.

- **R8 (enforced) No undefined names in `src/`.**
  `python -m pyflakes src/` must report zero `UndefinedName` warnings.
  Check: `undefined_names.py` (typed-message scan via
  `pyflakes.checker.Checker`, not string matching on the reporter's text;
  fail-closed on zero files scanned or pyflakes unavailable).
  Failure mode addressed: BRIEF-0027-d's module split left 80 undefined-name
  sites — a shared private helper stayed in one domain module while its
  callers moved to siblings without importing it. Python resolves names at
  call time, so every import in the split still succeeded and the route
  table stayed set-identical (109/110 routes, zero shadow pairs, unchanged
  by the fix) — the defect was invisible to every existing check and
  surfaced only as a 500 when a handler touching the missing name actually
  ran, breaking the live gate on both play and creation (BRIEF-0027-i).

## 3. Frontend (advisory)

`cockpit/index.html` (8.8k lines, ~350 JS functions) stays governed
primarily by the existing `page_contract.py` check (registry pattern,
`CREATION_TABS`, `primaryAction`). In addition, advisory:

- **F1** New JS functions follow the existing camelCase naming and live
  inside the single main script block; no second top-level script block, no
  inline `onclick` handlers added to markup that the registry dispatcher
  could own.
- **F2** New client state hangs off the existing top-level state objects;
  no new module-level mutable globals.
- **F3** A JS function past ~80 lines is split, same spirit as R1 — not
  machine-checked in v1.

## 4. Legacy remediation (TICKET-0027, staged briefs)

TICKET-0027 (no schema change; touches the live play path and a canon-write
path) executes, in order:

- **a.** Ship the four verify checks (`function_length.py`,
  `llm_parse_chokepoint.py`, `no_print_in_src.py`, `module_budget.py`) with
  their transition baselines. Enforcement starts here, before any refactor.
- **b.** Extract `_stream` from `say`; decompose `say` into mode
  interpretation / persistence / NPC run / narration stages, extracted
  helpers living in a new domain module `cockpit/play.py` (R6/R7 apply);
  the route handler in `app.py` becomes a thin orchestrator.
- **c.** Decompose `_apply_mutation` into per-mutation-type appliers sharing
  the existing `writes.py` helpers (no new write path).
- **d.** Split `cockpit/app.py` routes into routers under
  `cockpit/routes/{play,mutations,creator,prompts}.py` and `cockpit/crud.py`
  into domain modules; `app.py` retains wiring only.
- **e.** Create `llm_parse.py`; migrate the 7 `entity_author.py` parse sites
  and the `analyzer.py`/`tick.py` helpers onto it (shrinks R2's allow-list
  to final form).
- **f.** Replace `analyzer.py` `print()` with logging; translate its French
  strings (closes S5 known violations; R3 runs with no exemptions). Scope
  amended in-session (BRIEF-0027-f) to also cover `tick.py`'s 26 sites,
  once `TRANSITION_ALLOW`'s AST-authoritative count (not RECON-0027's
  grep-based one) surfaced both files still open — see
  ARCHITECTURE_DECISIONS.md. `tick.py`'s `module_budget.json` entry was
  re-keyed 1797 -> 1799 lines for the mandated logging preamble, a
  one-time, Nia-approved, shrink-only-from-here exception.
- **g.** Delete `tooling/verify/baselines/function_length.json` and
  `module_budget.json`; R1 and R5 run exemption-free from this point.
  Deferred to TICKET-0028's close (not this ticket) per the same
  amendment.

Behavior-preserving throughout: no route contract, prompt, or schema change.
Each stage closes with `/verify` green plus a live smoke of the touched
surface (a `/say` round-trip for b, d; one mutation approval for c).

## 5. Housekeeping recorded at seeding

- `tooling/improvement/bug_log.jsonl` entry 2026-07-03 (subculture values)
  is still `status: "open"`; flip to `fixed (BRIEF-0025-d, v1.78)` at the
  next commit touching the file.
