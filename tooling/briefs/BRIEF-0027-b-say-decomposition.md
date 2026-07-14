<!-- slug: say-decomposition -->
# BRIEF-0027-b — Decompose `say` and `_stream` into `cockpit/play.py`

Ticket: TICKET-0027 | Danger: none of {db_write, migration,
destructive_data} as *intent* — but this is the live play path and the
riskiest behavior-preserving refactor of the project to date | Blast
radius: large | Depends on: BRIEF-0027-a merged and green

## Context

`cockpit/app.py:3843` `say` is 1130 lines with a nested 958-line generator
`_stream` (`app.py:4013`), grown by accretion across TICKET-0013..0016,
0020, 0024 (RECON-0027 section 3). Zero behavior tests exist; the verify
suite checks invariants, not behavior. This brief therefore ships in two
movements: **(1) a disposable record/replay harness that freezes current
behavior, (2) the decomposition itself**, proven equivalent under replay.
Per F2/G1 (code_standards R6/R7): extracted helpers go to a new domain
module `src/world_engine/cockpit/play.py` with `_say_*` prefixes; `say` in
`app.py` remains a thin orchestrator.

## Scope IN

1. **Helper inventory first (R7).** Before extracting anything, enumerate
   the helpers `say`/`_stream` already call (in `app.py`, `context.py`,
   `analyzer.py`, `writes.py`, `gathering.py`) with `file:line`, in the
   execution notes. Reuse; do not create a sibling of anything listed.

2. **Harness: `scripts/harness_say_replay.py`** (disposable — deleted at
   stage g; `print` is fine here, it lives in `scripts/`).
   - Never touches the live DB: copies
     `~/.world_engine/world_engine.db` to a temp working path and points
     the engine at the copy for the whole run.
   - **Record mode**: against the copy, runs N reference `/say`
     round-trips (N >= 3: one plain narration turn, one turn addressing an
     NPC, one turn triggering a mutation proposal) on a reference
     conversation chosen at execution time. Captures to a fixture dir:
     (a) every Ollama request/response pair by monkeypatching
     `ollama_client.chat` / `chat_stream`, (b) the full SSE stream emitted
     to the client, (c) a before/after dump of all rows written (tables
     touched by the play path), with volatile fields (UUIDs, timestamps)
     normalized by stable substitution.
   - **Replay mode**: same round-trips with the recorded model responses
     played back instead of calling Ollama, so everything around the model
     is deterministic. Emits a diff of (b) SSE stream and (c) DB writes
     against the recorded fixtures. Empty diff = PASS.
   - Record fixtures on pre-refactor `main`; replay must PASS pre-refactor
     (harness self-validation) and post-refactor (equivalence proof).

3. **Decomposition.** Create `src/world_engine/cockpit/play.py`; extract
   the body of `say`/`_stream` into `_say_*` functions along the existing
   stage seams — mode interpretation, player-line persistence, NPC
   selection/run, mutation-proposal assembly, narration streaming — each
   <= 80 lines (R1). `play.py` must respect R5 caps (<= 40 functions,
   <= 1000 lines) with **no baseline entry**: if the extraction cannot fit,
   split `play.py` by sub-domain (e.g. `play_stream.py`) rather than
   requesting an exemption. The `say` handler stays in `app.py` for now
   (router move is stage d), reduced to an orchestrator <= 80 lines.
   Pure moves and mechanical parameter-passing only: no logic change, no
   renamed routes, no altered SSE event names/shapes, no prompt change.

4. **Baseline shrink.** Remove `say` and `_stream` from
   `baselines/function_length.json`; shrink `cockpit/app.py`'s entry in
   `baselines/module_budget.json` to its new (lower) measured values.

## Scope OUT

- `_apply_mutation` (stage c), router split (stage d), `llm_parse.py`
  (stage e), logging/French strings (stage f) — even where the moved code
  makes those itches visible.
- Any behavior improvement, bug fix, or prompt tweak discovered en route:
  log it as a candidate ticket in the execution notes instead.
- Any schema or migration work. Any change to `writes.py`.
- Harness coverage beyond the play path (it is a `say` harness, not a
  test framework).

## Invariants to defend

- Single canon-write path: every DB write still flows through the same
  `writes.py` helpers as before (`single_canon_write.py` green).
- History append-only; SAVEPOINT atomicity of the mutation-proposal
  segment unchanged.
- Route contract frozen: endpoint path, method, request model, SSE event
  names and ordering identical.
- Earshot doctrine: no new accessor for "who hears what"; the existing
  accessor call sites move verbatim.
- Full verify suite (29 checks) green after the change, with baselines
  strictly smaller than before the brief.

## Done means

### Machine-checkable
- [ ] Harness replay PASS on pre-refactor `main` (self-validation run
      recorded in execution notes).
- [ ] Harness replay PASS post-refactor: empty diff on SSE stream and DB
      writes for all N reference round-trips.
- [ ] `function_length.py` green with `say` and `_stream` no longer in the
      baseline; every function in `play.py` <= 80 lines.
- [ ] `module_budget.py` green: `play.py` unbaselined and within caps;
      `app.py` baseline entry shrunk on both dimensions.
- [ ] `single_canon_write.py`, `page_contract.py`, and the rest of the
      suite green.

### Live gate (Nia)
- [ ] A live `/say` round-trip in an existing conversation: narration
      streams, the line persists, NPC responds — indistinguishable from
      pre-refactor behavior.
- [ ] One turn that triggers a mutation proposal: proposal appears in the
      cockpit approval queue as before.

## Docs to update

- None beyond pipeline state: no schema change, no doctrine change.
  (`code_standards.md` section 4 already describes stage b as shipped
  here; Nia verifies the match at ticket close.)
