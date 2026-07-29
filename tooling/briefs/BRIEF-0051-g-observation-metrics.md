# BRIEF — Step "observation metrics"

## Context

TICKET-0051 decision J2 and the locked metric set Q. This is step 3 of Nia's
plan: turning transcripts and decision rows into answers about WHICH failure
mode a flat scene exhibits.

Three failure modes must be distinguishable, because each points at a
different fix:

| Mode | Signature | Points at |
|---|---|---|
| (a) nobody wants to act | low intent rate | propensity / intent prompt |
| (b) all want to act, nothing happens | high intent, low proposal yield | dialogue prompt |
| (c) they loop | high n-gram overlap | context / scene memory |

Deterministic instruments ONLY. The LLM novelty judge is named deferral
**D-J1**: putting a model inside the measurement loop while isolating causes
adds a confounder. It is reactivated once J2 has shown its blind spots on
modes (b) and (c), not before.

Depends on -a and -e. All nine metrics were verified derivable from the -a
socle at ticket time; the mini-RECON re-confirms that against the landed
schema.

## Mini-RECON (report-only, before writing any code)

Report each finding with `file:line`. If a finding contradicts this brief,
STOP and escalate.

1. **Landed socle columns** — the actual columns of `observation_run`,
   `observation_beat`, `observation_intent`, `observation_run_template`,
   `observation_mutation_link`. Map EACH of the nine metrics below to the
   columns it needs. Report any metric that is NOT derivable; do not
   improvise a substitute.
2. **Relation access** — the query shape for NPC-to-NPC intensity at a given
   moment, for the correlation metric. Report whether `relation.intensity` is
   mutated by applied proposals during a run, which would make "the intensity
   at beat 3" unrecoverable after the fact. If so, report it — do NOT add a
   snapshot column on your own initiative.
3. **Derived reason precedence** — the exact precedence recorded in
   `world-engine-schema.md` by -a, so this script and the -f display agree.
4. **Script conventions** — how existing `scripts/*.py` handle
   `WORLD_ENGINE_ENV`, DB resolution, and output, so this one matches.
5. **Existing analysis scripts** — whether any script already computes
   distribution or overlap statistics that should be reused rather than
   duplicated.

## Scope IN

### 1. `scripts/observation_metrics.py`

Takes a `run_id` (or several, to compare runs). Read-only: it opens the DB,
computes, prints. It writes NOTHING — no table, no cache, no column.

The nine locked metrics:

**Participation**
1. Acted-beat share per NPC — `acted` beats by actor over total `acted` beats.
2. Shannon entropy of that distribution, normalised to `[0, 1]`, where 1 is
   perfectly even. This is the single number answering "did one NPC capture
   the run".

**Intent**
3. Intent rate per NPC — `act=true` over opportunities offered.
4. Selection rate given intent — selected over `act=true`. Separates "wanted to
   speak and lost" from "never wanted to speak" — mode (a) versus arbitration.

**Health**
5. Silence rate — `outcome='silence'` over total beats.
6. Degraded rate — `outcome='degraded'` over total beats. Reported SEPARATELY
   and FIRST: a run with a non-zero degraded rate has a technical fault, and
   every other metric on that run is suspect. Say so in the output rather than
   leaving the reader to notice.

**The ticket's originating hypothesis**
7. Correlation between `abs(intensity - 50)` and per-NPC act rate. Report
   Spearman (rank), not Pearson: with 5 NPCs the relationship is ordinal at
   best and a linear coefficient would overstate what the data supports.
   Report the coefficient WITH n, and state plainly that n=5 supports a
   direction, not a conclusion.

**Repetition — mode (c)**
8. Maximum n-gram overlap of each `acted` line against the prior N beats'
   lines. Fixed n (report the choice; 4 is the default unless mini-RECON finds
   a reason otherwise) and fixed window N. Report per-beat maximum and the run
   mean.

**Evolution — mode (b), and feasibility**
9. Proposals per run via `observation_mutation_link`, broken down by mutation
   type; plus latency p50/p95 from `observation_intent.latency_ms`.

### 2. Output

Human-readable to stdout by default; `--csv` for a machine-readable dump.
Multi-run mode prints a side-by-side comparison INCLUDING each run's pinned
arbitration parameters and template versions — a comparison that does not show
what differed between the runs is what the L pinning exists to prevent.

### 3. Interpretation guard

The output opens with a short block stating what the numbers cannot support:
`n=5` NPCs, one location, no replay, and a world that mutates between runs.
Verbatim:

```
These figures describe THIS run. Two runs are comparable only if their
pinned parameters and template versions match (shown below) and the world
did not change materially between them. Bit-exact replay is out of scope by
decision: the world mutates under play. A metric that differs between two
runs with different template versions says nothing about the arbitration.
```

This is not decoration. The whole ticket exists to avoid misattributing a flat
scene to the wrong cause, and a metrics tool that presents numbers without
their preconditions reintroduces exactly that risk.

### 4. Verify check `tooling/verify/checks/observation_metrics.py`

- **Rule 1** (AST): the script contains no write operation — no `db.add`, no
  `commit`, no `INSERT`, no `UPDATE`.
- **Rule 2** (AST): no import of `ollama_client` or any model-calling module.
  D-J1 is enforced, not merely documented.
- **Rule 3** (behavioural, fixture run): a synthetic run where one NPC acts on
  every beat yields entropy near 0; an even run yields entropy near 1. Assert
  BOTH ends — a metric that only ever returns one value is not tested.
- **Rule 4** (behavioural): a fixture with a `degraded` beat produces a
  non-zero degraded rate AND the suspect-run warning in the output.
- **Rule 5**: the derived reason precedence in the script matches the one in
  `world-engine-schema.md` verbatim.
- **Rule 6, vacuous-proof guard**: if the fixture produced zero beats or zero
  intent rows, FAIL.

## Scope OUT

- **The LLM novelty judge (D-J1).** Named deferral. No model call, no import.
- **Charts and dashboards.** stdout and CSV. A visualisation surface is a
  separate ticket.
- **Storing computed metrics.** Recomputed on demand. A metrics table would be
  structure without a reader and would go stale the moment the derivation
  changes.
- **Automatic tuning.** The script reports; it does not adjust parameters,
  recommend values, or write anything back.
- **Cross-world or cross-ticket analytics.** Scoped to observation runs.
- **Changes to the socle schema.** If a metric is not derivable, mini-RECON
  item 1 reports it and this brief STOPS. Adding a column here would be a
  schema change smuggled into an analysis brief.
- **Editing prompts based on findings.** That is step 4, a future ticket.
- **`play*.py`, `tick*.py`, `analyzer*.py`, `context.py`.** Untouched.

## Invariants to defend

- **No structure without a reader.** This brief is the reader for
  `observation_intent`'s component columns and for `latency_ms` — and it is
  where the ticket's declaration that latency has a DIFFERENT reader
  (feasibility, not scene analysis) is honoured, by reporting it under
  feasibility rather than mixing it into the narrative metrics.
- **Read-only.** Enforced by Rule 1, not by convention.
- **Honest uncertainty.** n=5, Spearman not Pearson, preconditions stated up
  front. The tool must not lend more confidence than the data carries.
- **Deterministic measurement.** Same rows in, same numbers out. Rule 2 keeps
  it that way.

## Done means

- [ ] `python scripts/observation_metrics.py <run_id>` prints all nine metrics
      for a real 30-beat run.
- [ ] A run where one NPC took every beat reports entropy near 0; an even run
      reports near 1. Both demonstrated.
- [ ] A run containing a `degraded` beat reports a non-zero degraded rate and
      flags the run as suspect before printing anything else.
- [ ] `--csv` output parses as CSV.
- [ ] Multi-run mode prints the pinned parameters and template versions
      alongside the figures.
- [ ] `grep -rn "ollama\|chat(" scripts/observation_metrics.py` returns
      nothing.
- [ ] `python tooling/verify/checks/observation_metrics.py` exits 0 with
      non-zero fixture counts.
- [ ] Full-tree verify passes.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: subsection recording J2 (deterministic
instruments), the three failure modes and which metric distinguishes each, the
choice of Spearman with its n=5 rationale, and D-J1's reactivation condition
restated at the point where it would be tempting to reach for it.
`DECISIONS_INDEX.md` entry. `world-engine-schema.md` unchanged (read-only
brief, no schema change).
