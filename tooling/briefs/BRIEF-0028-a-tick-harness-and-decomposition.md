<!-- slug: tick-harness-and-decomposition -->
# BRIEF-0028-a — Tick replay harness + decomposition of `tick.py`

Ticket: TICKET-0028 | Danger: none of {db_write, migration,
destructive_data} as *intent* — but this touches the world-tick pipeline
(a `ProposedMutation`-producing path) and is the largest single-module
refactor of the residual | Blast radius: large | Depends on: nothing
(first brief of TICKET-0028); `main` green with the full 30-check suite

## Context

TICKET-0028 owns the frozen shrink-only residual (decision I2): both
transition baselines die at this ticket's close, after which R1/R5 run
exemption-free. `tick.py` is the natural first target: it is the only
module over the R5 line cap that also owns the five largest baselined
functions — `run_world_tick` 417 (`tick.py:1383`), `_normalize_scope_event`
292 (`tick.py:682`), `_normalize_tick_item` 239 (`tick.py:1142`),
`assemble_tick_context` 214 (`tick.py:164`),
`assemble_faction_event_context` 114 (`tick.py:566`).

`run_world_tick` calls the model at two sites (`tick.py:1460`,
`tick.py:1675`); the existing say/mutation harnesses do not cover this
path, so per the checks-first precedent this brief ships in two movements:
**(1) a disposable record/replay harness that freezes current tick
behavior, (2) the decomposition itself**, proven equivalent under replay.

Decomposition shape is locked (F1): flat modules, not a package. The
module has three clean zones — context assembly (`tick.py:88-679`),
model-output normalization (`tick.py:682-1380` minus goal-text helper
overlap), orchestration (`run_world_tick`, `tick.py:1383-1799`). Extract
the first two into `tick_context.py` and `tick_normalize.py`;
`run_world_tick`, decomposed, stays in `tick.py`. This keeps both
importers untouched (`routes/mutations.py:41`, `routes/play.py:27,992`)
and both prompt-registry anchors untouched (`prompt_registry.py:208,215`
anchor `world_tick` / `world_tick_events` to
`src/world_engine/tick.py:run_world_tick`).

Executes decision G1 in passing: the first commit of this brief flips
`TICKET-0027-code-standards-seeding-and-remediation.md` front-matter from
`status: live-gate` to `status: done`.

## Scope IN

1. **Ticket + status housekeeping.** Deposit the already-authored
   `tooling/tickets/TICKET-0028-residual-decomposition.md` verbatim (do
   NOT create a new one from TEMPLATE.md). Flip TICKET-0027 front-matter
   to `status: done` (G1).

2. **Helper inventory first (R7).** Before extracting anything, enumerate
   in the execution notes, with `file:line`, every helper the three zones
   already call — inside `tick.py` and in `context.py`, `analyzer.py`,
   `llm_parse.py`, `writes.py`. Reuse; do not create a sibling of
   anything listed. Moved helpers keep their names; only NEW extractions
   (function bodies carved out of the five baselined functions) take the
   domain prefix (`_tick_*`).

3. **Harness: `scripts/harness_tick_replay.py`** (disposable — owned by
   TICKET-0028, deleted at its close alongside the say/mutation
   harnesses; `print` is fine here, it lives in `scripts/`).
   - Never touches the live DB: copies `~/.world_engine/world_engine.db`
     to a temp working path and points the engine at the copy for the
     whole run (same mechanics as `harness_say_replay.py`).
   - **Record mode**: against the copy, runs N reference
     `run_world_tick` invocations (N >= 2, chosen at execution time so
     that fixtures jointly traverse BOTH model-call sites: the
     per-NPC/tick-item call at `tick.py:1460` and the events call at
     `tick.py:1675`, each producing at least one `ProposedMutation` row
     of each kind emitted at `tick.py:1566` and `tick.py:1767`).
     Captures per invocation: (a) every Ollama request/response pair by
     monkeypatching `ollama_client.chat`, (b) the return value of
     `run_world_tick`, (c) a before/after dump of `proposed_mutation`
     rows written, with volatile fields (UUIDs, timestamps) normalized
     by stable substitution.
   - **Fixture coverage manifest (mandatory).** The rule learned in 0027:
     a green replay over non-covering fixtures is a vacuous proof. The
     harness therefore writes, next to the fixtures, a manifest NAMING
     the functions each fixture traverses (at minimum: which of the two
     call sites fired, which normalizers ran — `_normalize_scope_event`,
     `_normalize_tick_item`, `_normalize_effect_item` — and which
     assemble functions built the context). Replay refuses to report
     PASS if the manifest does not cover both call sites and all three
     normalizers.
   - **Replay mode**: same invocations with recorded model responses
     played back; emits a diff of (b) and (c) against the fixtures.
     Empty diff = PASS.
   - Record fixtures on pre-refactor `main`; replay must PASS
     pre-refactor (self-validation) and post-refactor (equivalence
     proof).

4. **Decomposition (F1).**
   - Create `src/world_engine/tick_context.py`: move the rendering
     helpers (`_section` .. `_goal_prerequisite_lines`, `tick.py:88-161`),
     `assemble_tick_context`, `_reachable_locations`,
     `assemble_location_event_context`, `assemble_faction_event_context`.
     Decompose `assemble_tick_context` (214) and
     `assemble_faction_event_context` (114) into <= 80-line functions
     along their existing section seams.
   - Create `src/world_engine/tick_normalize.py`: move
     `_normalize_scope_event`, `_normalize_goal_text`, `_build_roster`,
     `_build_effects_roster`, `_normalize_effect_item`,
     `_normalize_effects_list`, `_normalize_tick_item`. Decompose
     `_normalize_scope_event` (292) and `_normalize_tick_item` (239) into
     <= 80-line functions.
   - `tick.py` keeps `run_world_tick`, decomposed into <= 80-line stages
     along its existing seams (roster/context assembly loop, model call +
     parse, proposal assembly, events pass, commit), importing from the
     two new modules.
   - Both new modules must respect R5 caps with **no baseline entry**; if
     either cannot fit, split further by sub-domain (R6: no catch-all)
     rather than requesting an exemption.
   - Pure moves and mechanical parameter-passing only: no logic change,
     no prompt change, no reordering of `ProposedMutation` construction,
     no change to what is proposed vs written.

5. **Baseline shrink.** Remove the five `tick.py` entries from
   `baselines/function_length.json` and the `tick.py` entry from
   `baselines/module_budget.json` entirely (the module and its offspring
   comply unbaselined). Residual after this brief: 26 function entries,
   3 module entries.

## Scope OUT

- `writes.py` package split (stage b), `models.py` stratum split
  (stage c), `entity_author.py` (stage d), the remaining R1 residual in
  `analyzer.py` / `context.py` / routes (stage e), baseline deletion +
  harness deletion (stage f) — even where the moved code makes those
  itches visible.
- Any behavior improvement, bug fix, prompt tweak, or normalization
  tightening discovered en route: log it as a candidate ticket in the
  execution notes instead.
- Any schema or migration work. Any change to `writes.py`,
  `llm_parse.py`, or `prompt_registry.py`.
- Harness coverage beyond the tick path.
- No generalization of the three harnesses into a shared framework (D1
  rejected D2).

## Invariants to defend

- **Model proposes, code judges**: `tick.py` and its offspring write
  ONLY `proposed_mutation` rows (`tick.py:1566`, `tick.py:1767`, single
  commit `tick.py:1789`); zero canon-table writes appear anywhere in the
  three modules (`single_canon_write.py` green — none of these modules
  is, or becomes, an allowed site).
- **R2 chokepoint**: both model outputs keep flowing through
  `llm_parse.extract_array` (`tick.py:1463`, `tick.py:1681`);
  `llm_parse_chokepoint.py` green with no new parse sites.
- **Prompt-registry anchors frozen**: `run_world_tick` keeps its name and
  module; `prompt_registry.py` untouched and its check green.
- **Import surface frozen**: `routes/mutations.py:41` and
  `routes/play.py:27` import statements unchanged.
- **R3**: the new modules use the `logging` preamble pattern, zero
  `print()` (`no_print_in_src.py` green); French interval labels are
  DATA, never translated.
- Full verify suite (30 checks) green, both baselines strictly smaller
  than before the brief, shrink-only respected.

## Done means

### Machine-checkable
- [ ] Harness replay PASS on pre-refactor `main` (self-validation run
      recorded in execution notes).
- [ ] Fixture coverage manifest present and covering both model-call
      sites and all three normalizers (harness refuses PASS otherwise).
- [ ] Harness replay PASS post-refactor: empty diff on return values and
      `proposed_mutation` writes for all N invocations.
- [ ] `function_length.py` green with the five `tick.py` entries removed
      from the baseline; every function in `tick.py`,
      `tick_context.py`, `tick_normalize.py` <= 80 lines.
- [ ] `module_budget.py` green: `tick.py` entry removed from the
      baseline; all three modules within caps unbaselined.
- [ ] `single_canon_write.py`, `llm_parse_chokepoint.py`,
      `no_print_in_src.py`, `prompt_registry.py`, `undefined_names.py`
      and the rest of the suite green.
- [ ] TICKET-0027 front-matter reads `status: done`.

### Live gate (Nia)
- [ ] One live world tick from the cockpit on a real world: tick items
      appear in the approval queue as before, events pass included —
      indistinguishable from pre-refactor behavior.

## Docs to update

- `tooling/tickets/TICKET-0028-residual-decomposition.md`: deposited
  verbatim (already authored; `brief_ids` starts with this brief —
  executor appends b..f as they ship).
- `TICKET-0027` front-matter status flip (G1) — no other 0027 edits.
- Pipeline state only otherwise: no schema change, no doctrine change.
  `code_standards.md` is NOT edited here (its section 4 describes 0027;
  the 0028 closure edit belongs to stage f).
