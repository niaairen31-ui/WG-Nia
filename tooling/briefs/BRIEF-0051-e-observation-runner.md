# BRIEF — Step "observation runner"

## Context

TICKET-0051 decisions B2/B1, K2, F3, plus the fail-closed readiness gate. This
brief assembles the parts: the socle tables (-a), the disclosure floor (-b),
the analysis seam (-c) and the engine (-d) become a run that executes N beats
and stops.

Depends on -a, -b, -c and -d. It is the first brief in the ticket that WRITES
observation rows and the first that can emit proposals.

## Mini-RECON (report-only, before writing any code)

Report each finding with `file:line`. If a finding contradicts this brief,
STOP and escalate.

1. **Write chokepoint** — confirm the exact signatures shipped by -a's
   `observation_writes.py`, including `close_observation_run`'s one-way
   transition and the `ValueError` on `player_presence != 'absent'`.
2. **Seam signatures** — confirm `analyze_transcript` and
   `analyze_overheard_lines` from -c, and confirm both return UN-PERSISTED
   objects and never commit.
3. **Engine signatures** — confirm `request_intent` and `arbitrate` from -d,
   and that `arbitrate` performs no I/O.
4. **Gathering roster** — how a gathering is created, how members are added,
   and whether an observed run should create one or attach to an existing one.
   Report the B1 invariant's exact form (each present NPC belongs to exactly
   one open gathering) and whether an observed run can violate it.
5. **Active goals** — the exact query for "NPC has at least one active goal",
   for the readiness gate.
6. **`proposed_by`** — confirm `OBSERVED_PROPOSED_BY` from -a and that -a's
   NULL-safe queue exclusion is in place BEFORE this brief produces the first
   proposal.
7. **Long-running work in the cockpit process** — how the existing world tick
   handles a multi-call operation (blocking, background task, or otherwise).
   A 30-beat run at 5 NPCs is ~150 intent calls plus up to 30 act calls;
   report what that implies for the process model. Do NOT design a solution
   in the mini-RECON — report and let the brief's Scope IN stand or escalate.

## Scope IN

### 1. New module `src/world_engine/observation_runner.py`

**a. Readiness gate — fail-closed, runs BEFORE anything is written.**

`check_run_readiness(location_id, npc_ids, db) -> list[str]` returns the list
of failed conditions. A run with a non-empty list is REFUSED: no
`observation_run` row, no model call.

Conditions:
- at least 2 NPCs present;
- every present NPC has at least one active goal;
- every present NPC has a describable identity (name and description
  non-empty);
- the location exists and belongs to the world;
- `player_presence == 'absent'` (H2: the other values raise in -a's writer;
  the gate refuses earlier and more legibly).

Rationale, to carry into the docstring verbatim:

```
The gate exists because a flat scene has two very different causes: a
passive initiative system (what this ticket measures) and an
under-populated world (what it does not). Without the gate the first
finding of every run risks being misattributed to the engine. Refusing
loudly costs one message; a misattributed conclusion costs a redesign.
```

**b. The beat.**

For each beat, in order:
1. Build the transcript from prior beats of this run.
2. Call `request_intent` for EVERY present NPC (C3: universal opportunity),
   with `audience_ids` = all present NPCs minus the speaker (-b's floor).
3. Call `arbitrate` (-d).
4. Write ONE `observation_beat` and ONE `observation_intent` per candidate,
   always, including on failure.
5. If a candidate was selected: generate the line with
   `pt-npc-initiative-act`, store it on the beat, set `outcome='acted'`.
6. `outcome` is set from evidence, never inferred:
   - any candidate selected -> `acted`
   - no selection, at least one `call_status='ok'` -> `silence`
   - no selection, NO `call_status='ok'` -> `degraded`
7. If `mj_narration` is on, one MJ call after the line; store on the beat.
   Off by default: no MJ call is made at all, not a discarded one.

**c. Stop conditions — bounded by construction.**

`max_beats` reached -> `stop_reason='max_beats'`. `quiescence_limit`
consecutive non-`acted` beats -> `'quiescence'`. Creator stop -> `'creator_stop'`.
Unhandled exception -> `'error'`, and the run is closed as `failed` — a run
never stays `running` after the process returns.

**d. Single-beat stepping (B1).**

`run_one_beat(run_id, db)` executes exactly one beat against an open run.
`run_bounded(run_id, db)` loops it until a stop condition. The bounded path is
built ON the single-beat path — one implementation, two entry points.

**e. Event injection (K2).**

`inject_event(run_id, text, db)` writes a beat with `outcome='event'`,
`actor_id=None`, `line=text`. It consumes no beat allowance and produces no
intent rows. It becomes part of the transcript every subsequent NPC reads —
that is the whole mechanism.

**f. Proposal production (F3).**

After the run closes, call -c's seam over the run transcript, tag every
returned proposal `proposed_by=OBSERVED_PROPOSED_BY`, persist them, and write
one `observation_mutation_link` per proposal.

Overhearing: `analyze_overheard_lines` receives an EXPLICIT receiver set —
every present NPC except the speaker. No player subtraction, since there is no
player.

Proposals are produced once per run, not per beat: a run is the unit of
analysis, and per-beat analysis would multiply model calls by 30 for no gain
at this stage.

### 2. Route

One POST route to start a run, one to step, one to stop, one to inject an
event. Thin: parameter validation and a call into the runner. No business
logic in the route. Placed per the mini-RECON item 7 finding on the process
model; if that finding shows a 150-call run cannot be served synchronously,
STOP and escalate rather than inventing a background-task mechanism here.

### 3. Verify check `tooling/verify/checks/observation_runner.py`

- **Rule 1** (AST): every `observation_*` write in this module goes through
  `observation_writes.py`. No direct `db.add(Observation...)`.
- **Rule 2** (AST): `outcome` is never assigned from a truthiness test on
  `actor_id`; the three branches are explicit.
- **Rule 3** (behavioural, temp DB): a run whose intent calls are all forced to
  fail produces `outcome='degraded'`, NOT `'silence'`, and produces a full set
  of `observation_intent` rows.
- **Rule 4** (behavioural): a readiness-gate failure produces ZERO
  `observation_run` rows.
- **Rule 5** (behavioural): a completed run writes zero `conversation` and zero
  `conversation_message` rows.
- **Rule 6** (behavioural): proposals produced by a run do NOT appear in
  `list_mutations` output, and DO appear via `observation_mutation_link`.
- **Rule 7**: no run is left in `status='running'` after `run_bounded` returns,
  including on exception.
- **Rule 8, vacuous-proof guard**: if the fixture executed zero beats or wrote
  zero intent rows, FAIL.

## Scope OUT

- **Any cockpit UI.** No `index.html` change, no tab, no template. Routes only.
  BRIEF-0051-f.
- **Metrics.** No aggregation, no n-gram, no export. BRIEF-0051-g.
- **`play.py` / `play_stream.py` / `play_physical.py` / `play_initiative.py`.**
  The played path is untouched. No shared runner, no "while we're here".
- **`tick.py` / `tick_context.py` / `tick_normalize.py`.** Untouched.
- **Real-time streaming** (B3, not taken). The bounded run returns when done;
  the transcript is read cold.
- **`player_presence='silent'` / `'active'`.** Refused by the gate. H2.
- **Per-beat analysis.** Once per run.
- **Retention / purge.** Append-only, nothing deleted.
- **Auto-tuning of arbitration parameters.** They are pinned per run and set by
  the caller; nothing adapts them mid-run.

## Invariants to defend

- **Fail-closed over advisory.** The gate refuses; it does not warn and
  proceed.
- **Silence is a logged outcome, and `degraded` is not `silence`.** Rule 3 is
  the mechanical form of the ticket's central measurement claim.
- **History is sacred.** Append-only; the only in-place update is the run's
  one-way close.
- **Single canon-write authority.** Observed runs reach canon ONLY through
  `proposed_mutation` under creator approval — same gate as a played scene.
- **The tick is not this.** No import from any `tick*` module.
- **No structure without a reader.** Every column -a shipped is written here
  and read by -f or -g.

## Done means

- [ ] A 5-NPC / 30-beat run completes and `observation_beat` holds 30 rows.
- [ ] `observation_intent` holds one row per NPC per beat — 150 rows for that
      run, with none missing.
- [ ] A run started against a location where one NPC has no active goal is
      REFUSED, names that condition, and leaves no `observation_run` row.
- [ ] Killing Ollama mid-run produces beats with `outcome='degraded'`, and the
      run closes as `failed` with `stop_reason='error'`.
- [ ] `inject_event` at beat 15 appears in the transcript read by beat 16's
      intent calls — show the assembled context.
- [ ] Proposals from the run are absent from `GET /api/mutations?status=proposed`
      and reachable through `observation_mutation_link`.
- [ ] A run with `mj_narration=False` makes zero MJ model calls (show the call
      count, not just an empty column).
- [ ] `SELECT COUNT(*) FROM conversation_message` is unchanged across a run.
- [ ] `python tooling/verify/checks/observation_runner.py` exits 0 with
      non-zero beat and intent counts.
- [ ] Full-tree verify passes.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: subsection recording B2/B1 (bounded run, cold
read, why B3 was refused), the readiness gate with its verbatim rationale, the
three-way `outcome` and why `degraded` must not collapse into `silence`, K2's
event mechanism, and F3's once-per-run production with structural isolation.
`world-engine-schema.md`: note that `observation_mutation_link` now has a
writer. `DECISIONS_INDEX.md` entry.
