<!-- slug: verify-checks-and-baselines -->
# BRIEF-0027-a — Code standards verify checks and transition baselines

Ticket: TICKET-0027 | Danger: none (tooling only, no `src/` change, no
schema change) | Blast radius: small

## Context

`tooling/standards/code_standards.md` v1 (seeded 2026-07-13) defines four
enforced rules: R1 function length, R2 LLM-parse chokepoint, R3 no print in
src, R5 module budget. Per locked decision C2, enforcement ships **before**
any refactor: checks land now with transition baselines/allow-lists that may
only shrink, and are deleted or emptied by later stages (f, g). Findings and
`file:line` evidence: RECON-0027. This brief touches only `tooling/` and
appends to governance docs — zero `src/` modification.

## Scope IN

1. **`tooling/verify/checks/function_length.py`** (R1).
   AST-based: for every function/method in `src/` (including nested),
   length = `end_lineno - lineno + 1`, decorators excluded. Fails if any
   function > 80 lines is absent from
   `tooling/verify/baselines/function_length.json`, or if a baselined
   function exceeds its recorded length. Baseline schema:
   `[{"file": "...", "qualname": "...", "lines": N}, ...]`. Entries may
   only shrink or disappear; the check rewrites nothing (report-only on
   the baseline; shrinking is done by the executor of later briefs).
   Fail-closed: a missing or unparsable baseline file is a FAILURE, not a
   pass. Generate the baseline from current `main` (expect ~35 entries;
   top entries must match RECON-0027 section 3: `say` 1130,
   `_stream` 958, `_apply_mutation` 682, `run_world_tick` 421).

2. **`tooling/verify/checks/module_budget.py`** (R5).
   Same AST pass: per `src/` module, count top-level functions + methods,
   and physical lines. Caps: 40 functions AND 1000 lines — exceeding
   either fails unless the module is in
   `tooling/verify/baselines/module_budget.json` at values it has not
   exceeded on either dimension. Baseline schema:
   `[{"file": "...", "functions": N, "lines": N}, ...]`. Entries may only
   shrink or disappear. Missing/unparsable baseline = FAILURE. Expected
   baseline members per RECON-0027 section 1: `cockpit/app.py`,
   `cockpit/crud.py`, `tick.py`, `writes.py`, `models.py`,
   `entity_author.py` (exact counts regenerated at execution time from
   `main`, not copied from the RECON).

3. **`tooling/verify/checks/llm_parse_chokepoint.py`** (R2).
   AST scan for `json.loads` call sites in `src/`. Two named lists inside
   the check source:
   - `PERMANENT_ALLOW`: non-model JSON only (config loads; request bodies
     already validated by FastAPI). Populate from an execution-time audit
     of the 24 sites (RECON-0027 section 4); every entry carries a one-line
     reason.
   - `TRANSITION_ALLOW`: model-output parse sites that stage e will
     migrate to `llm_parse.py` — entries as `{"file", "max_sites"}`,
     counts may only shrink. Emptiness is enforced structurally, not by
     schedule: the moment `src/world_engine/llm_parse.py` exists in the
     tree, any remaining `TRANSITION_ALLOW` entry is a FAILURE.
   A `json.loads` site in neither list is a FAILURE. Zero parsed sites
   found in `src/` is a FAILURE (vacuous-pass guard: the scanner itself
   must prove it saw the known sites).

4. **`tooling/verify/checks/no_print_in_src.py`** (R3).
   AST call check (not grep) for `print` under `src/world_engine/`.
   `TRANSITION_ALLOW` inside the check: per-file max call counts
   (expect `analyzer.py` ~38 plus any others found; regenerate at
   execution). Counts may only shrink; stage f empties the list. Any
   `print` site beyond the allowance is a FAILURE; `scripts/` is out of
   scope by design.

5. All four checks follow the existing check contract in
   `tooling/verify/checks/` (discovery, exit semantics, output format —
   mirror `json_ui_boundary.py` as the closest pattern: named allow-list,
   fail-closed on zero parsed criteria).

6. Append the seeding decision to `ARCHITECTURE_DECISIONS.md` (decisions
   A2, B2, C2, D2, E3, F2, G1, H1 with one-line rationales; reference
   RECON-0027 and code_standards.md v1) and update `DECISIONS_INDEX.md`
   accordingly (`decisions_index.py` must stay green).

## Scope OUT

- Any modification under `src/` (including creating `llm_parse.py` — that
  is stage e).
- Any refactoring, renaming, or moving of existing functions.
- The `say` capture harness (BRIEF-0027-b).
- Editing `code_standards.md` (Nia deposits it; content is chat-authored).
- Flipping the `bug_log.jsonl` status (deferred to the first brief that
  touches that file, per code_standards section 5).

## Invariants to defend

- Existing 25-check suite stays green: the four new checks must pass on
  current `main` with their freshly generated baselines/allow-lists.
- Fail-closed everywhere: missing baseline file, unparsable JSON, or zero
  scanned criteria is a failure in every one of the four checks.
- Baselines are generated from the live tree at execution time, never
  hand-copied from RECON figures.
- No permanent exemptions in R1/R5 artifacts: baseline files carry a
  header comment naming stage g as their deletion point.

## Done means

### Machine-checkable
- [ ] `tooling/verify` full run green on `main` with the four new checks
      active.
- [ ] Fail-closed proof, each new check: temporarily renaming its baseline
      file (or emptying its allow-list constant) makes the check FAIL;
      restored afterward. Demonstrated in the execution log.
- [ ] Regression proof, `function_length.py`: a scratch function of 81
      lines added to a temp file under `src/` makes the check FAIL;
      removed afterward.
- [ ] Regression proof, `module_budget.py`: growing a baselined module's
      recorded count in the JSON downward then rerunning shows FAIL on the
      real (higher) value; restored afterward.
- [ ] `decisions_index.py` and `claude_md_contract.py` green after doc
      appends.

### Live gate (Nia)
- [ ] `/verify` from the pipeline cockpit shows 29 checks, all green.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` (append, as Scope IN 6) + `DECISIONS_INDEX.md`.
- No schema docs (no schema change).
