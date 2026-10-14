# AMENDMENT-0123-01 — per-check timeouts in corpus_gate

Ticket: TICKET-0123   Lot: LOT-0123-lore-usage-since.md (header authoritative)
Brief in flight: A   Escalation answered: E-01 (D1-d)
Branch: `ticket/0123` (`07462d0`, `79de685`, `3670636`). Base: `origin/main`
(`301d178`).

## What deviated

Brief A's fix works: U12c passes inside the 20:00–24:00 America/Toronto
window and U12f proves it at any hour. But `lore_usage.py` now runs
15.5–17.7 s (13.9 s before U12f), around the 15 s per-check limit of
`corpus_gate.py`. The gate times it out under load and passes it in
isolation, so `/verify` is random. `event_analyzer.py`, untouched by this
ticket, timed out once in the same runs.

Decision recorded for E-01: **B** — a named per-check timeout for the checks
that need one; 15 s stays the default for every other check. Rejected: A, one
higher limit for all (it would hide a fast check that grows slow; reactivation:
more than a handful of checks need their own entry); C alone (≈1.5 s saved,
still at the limit; U12f needs real subprocesses since `time.tzset()` does not
exist on Windows); D alone (leaves `/verify` random meanwhile — kept as a
follow-up, see below).

## Amended RECON (new findings)

### R-A01-01 — corpus_gate timeout
Opened: `tooling/verify/checks/corpus_gate.py` (reported by the brief-A
session; confirmed by the anchor below).
Finding: one constant, `TIMEOUT_SECONDS = 15`, applies to every check; its
comment dates from a run whose slowest check took 3.22 s.
Consequence: the timeout becomes a lookup: a named entry, else the default.

### R-A01-02 — measured durations
Finding: `lore_usage.py` 13.9 s without U12f, 15.5–17.7 s with it, on Nia's
machine. `event_analyzer.py` exceeded 15 s once under `/verify`; not measured
in isolation.
Consequence: FX-1 measures `event_analyzer.py` before writing its entry.

## Anchors to confirm (Mini-RECON)

- `corpus_gate.py` declares `TIMEOUT_SECONDS = 15` and applies it to each check
  it runs.
- `corpus_gate.py` identifies each check by its file name (as in its output
  line « … timeout … » naming `lore_usage.py`).

A moved anchor is a STOP.

## Fix commits (on `ticket/0123`, in order, one commit each)

**FX-1 — measure.** Run `lore_usage.py` and `event_analyzer.py` alone, three
times each, with `WORLD_ENGINE_ENV=test`. Paste the six durations in the
report. No commit if nothing changes; this step feeds FX-2's comment.

**FX-2 — named timeouts.** In `tooling/verify/checks/corpus_gate.py`:

1. Keep `TIMEOUT_SECONDS = 15` as the default. Replace its comment with,
   verbatim except the bracketed values from FX-1:

   ```python
   # Default per-check timeout. Most checks finish in a few seconds; a check
   # that needs longer gets its own line in SLOW_CHECK_TIMEOUTS, with its
   # measured duration, never a higher default (TICKET-0123, AMENDMENT-0123-01).
   ```

2. Add directly below it, verbatim except the bracketed values:

   ```python
   # Checks known to run near or above the default, keyed by file name.
   # Each value is roughly twice the slowest measured run. A name here that no
   # longer matches a check fails the gate: a stale entry is a defect.
   SLOW_CHECK_TIMEOUTS = {
       # TICKET-0123: U12 exports run as subprocesses; U12f adds three
       # time zones. Measured [min]-[max] s on Nia's machine.
       "lore_usage.py": 30,
       # Timed out once under /verify during TICKET-0123. Measured
       # [min]-[max] s alone.
       "event_analyzer.py": 30,
   }
   ```

3. Each check runs under `SLOW_CHECK_TIMEOUTS.get(name, TIMEOUT_SECONDS)`.
4. Before running anything, the gate fails if a key of `SLOW_CHECK_TIMEOUTS`
   is not the file name of a check it would run, naming the key.

If FX-1 measures `event_analyzer.py` above 15 s in **none** of three runs, its
entry still goes in (the `/verify` timeout is the evidence), with the
measurements in its comment.

## Scope OUT

- Speeding up `lore_usage.py` or its U12 exports (follow-up ticket below).
- U12f's subprocess design; moving U12f in-process (option C).
- Any other check's duration or code.
- Raising the default.

## Invariants to defend

None of CLAUDE.md's domain invariants. The gate itself must stay fail-closed:
a timeout is still a failure, and an unknown key fails rather than being
ignored.

## Decision rights

STOP: an anchor moved; any check other than `lore_usage.py` and
`event_analyzer.py` exceeds 15 s in FX-1 or in `/verify` (it is a new entry,
and that is Nia's call); `lore_usage.py` exceeds 25 s in any run.
ADAPT: `corpus_gate.py` names checks by a path rather than a bare file name →
key `SLOW_CHECK_TIMEOUTS` the same way the gate names them, and report it.
REPORT-ONLY: the six durations of FX-1.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] FX-1 durations in the report; FX-2 as one commit.
- [ ] Mutation 1: add `"no_such_check.py": 30` → `corpus_gate.py` red, naming
      it. Revert.
- [ ] Mutation 2: set `"lore_usage.py": 1` → `corpus_gate.py` red on a timeout
      of `lore_usage.py`. Revert.
- [ ] `/verify` green twice in a row, at least once between 20:00 and 24:00
      America/Toronto, or once inside that window if run now and once outside.
- [ ] Ticket: E-01 closed with this amendment's id; `retry_count` reset to 0
      when brief A lands; amendment log row added.
- [ ] Ticket "Carried forward / open" gains, verbatim:
      `- Speed up lore_usage.py's U12 exports so it fits the default timeout
      again; then remove its SLOW_CHECK_TIMEOUTS entry. Own ticket, numbered
      above 0123.`

## Docs to update

`ARCHITECTURE_DECISIONS.md`: one entry above the footer
(`---` / `*Co-built…*`), « PER-CHECK TIMEOUTS ARE NAMED », stating the rule of
FX-2 and the rejected option A. Regenerate `DECISIONS_INDEX.md`; never edit it
by hand.

## Ticket amendment log row

| AMENDMENT-0123-01 | A | lore_usage.py at ~15–18 s exceeds corpus_gate's single 15 s timeout | none (one brief) |
