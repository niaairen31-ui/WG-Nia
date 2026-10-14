<!-- slug: lore-usage-since -->
# BRIEF 0123-A — "One day, one meaning: the Lore usage export reads `--since` on the cockpit's clock (no schema change)"

Lot: LOT-0123-lore-usage-since.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

On `main` at `301d178` or later. Halt if any has moved.

- `scripts/export_lore_usage.py:34` -> `from datetime import datetime`
- `scripts/export_lore_usage.py:99` -> `        start = datetime.fromisoformat(since)`
- `scripts/export_lore_usage.py:111` -> `    parser.add_argument("--since", help="keep attempts started on or after this ISO date")`
- `src/world_engine/cockpit/routes/dashboard.py:18` -> `from datetime import UTC, date, datetime, time, timedelta`
- `src/world_engine/cockpit/routes/dashboard.py:43` -> `def _utc(day: date) -> datetime:`, its body at :46 `    return datetime.combine(day, time.min).astimezone().astimezone(UTC).replace(tzinfo=None)`
- `src/world_engine/cockpit/routes/dashboard.py:59-60` -> the only two calls of `_utc(`
- `src/world_engine/models/pipeline.py:507` -> `    created_at: datetime = _created_ts()` inside `class LoreUsageEvent`
- `src/world_engine/models/canon.py:57` -> `        default_factory=lambda: datetime.now(UTC),`
- `tooling/verify/checks/lore_usage.py:888` -> `    tomorrow = (date.today() + timedelta(days=1)).isoformat()`
- `tooling/verify/checks/lore_usage.py:925` -> `    check_u12(db_path)`
- `tooling/standards/ARCHITECTURE_DECISIONS.md` ends with `---`, a blank line, `*Co-built with Claude, June 2026.*`
- No `src/world_engine/local_day.py`; no `local_midnight_utc` anywhere.

## Facts carried

### R-01 — the export script's `--since` [M]
Opened: `scripts/export_lore_usage.py` (whole file, 130 lines).
Finding: :34 `from datetime import datetime`; :92 `def _read(since: str |
None, world_ref: str | None)`; :99 `start = datetime.fromisoformat(since)`
(naive midnight); :100-104 keep the rows of every attempt whose FIRST event's
`created_at.replace(tzinfo=None)` is `>= start.replace(tzinfo=None)`; :111
`parser.add_argument("--since", help="keep attempts started on or after this
ISO date")`; :25 the docstring's usage line `[--since 2026-10-01]`.
`datetime.fromisoformat` also accepts a date-time, unvalidated.
Consequence: the comparison is naive against naive UTC (R-02), so D means
midnight UTC. The script is the side to fix.

### R-02 — what `created_at` holds [M]
Opened: `src/world_engine/models/pipeline.py:474-507` (`LoreUsageEvent`,
:507 `created_at: datetime = _created_ts()`); `src/world_engine/models/
canon.py:54-59` (`_created_ts`: `default_factory=lambda: datetime.now(UTC)`,
`sa_column=Column(DateTime, nullable=False, server_default=func.now())`);
`src/world_engine/writes/lore_usage.py:74-78` (the writer constructs
`LoreUsageEvent(...)` without `created_at`). Enumeration of constructors:
`grep -rn "LoreUsageEvent(" --include=*.py .` ->
`./src/world_engine/writes/lore_usage.py:74` and the class line
`./src/world_engine/models/pipeline.py:474`, nothing else.
Finding: every row's `created_at` is UTC (Python default or SQLite
`CURRENT_TIMESTAMP`), read back naive.
Consequence: the script must compare against a naive UTC instant.

### R-03 — the dashboard's conversion [M]
Opened: `src/world_engine/cockpit/routes/dashboard.py` (whole file, 83
lines).
Finding: :18 `from datetime import UTC, date, datetime, time, timedelta`;
:28 `from ...db import get_session`; :43-46
```python
def _utc(day: date) -> datetime:
    """Midnight of `day` on the cockpit's own clock (Nia's machine), as the
    naive UTC the timestamps are stored in."""
    return datetime.combine(day, time.min).astimezone().astimezone(UTC).replace(tzinfo=None)
```
:59-60 its only callers (`since=_utc(first)`, `until=_utc(last +
timedelta(days=1))`). Outside `_utc`, the file uses `date` (`_day`, :34-40)
and `timedelta` (:60); `UTC`, `datetime` and `time` appear only in `_utc`.
Consequence: A1 moves this body verbatim; afterwards the route imports
`date, timedelta` only.

### R-04 — who exercises the route's dates [M]
Opened: `tooling/verify/checks/dashboard_registry.py:242-287`.
Finding: it calls `routes.dashboard(...)` / `routes.dashboard_export(...)`
with `since`/`until` strings; no check names `_utc`.
Consequence: the pure move is proved by `dashboard_registry.py` passing
unchanged.

### R-05 — the check `lore_usage.py`, U12 [M]
Opened: `tooling/verify/checks/lore_usage.py` (940 lines): docstring :91-104
(U12 a-e); :120 `ROOT`, :132 `EXPORT`; :833-842 `_export(db_path, out,
*extra)` runs the script as a subprocess with `WORLD_ENGINE_DATABASE_URL`
and `WORLD_ENGINE_ENV=test`, returning `(CompletedProcess, lines)` (lines
read only on exit 0); :845 `check_u12`; :888-891 U12c (local date);
:891-904 U12d (AST: no call named `add`, `commit`, `delete`, `execute` or
starting with `write_` anywhere in the script); :907 `main`, :925
`check_u12(db_path)`, :930-935 the PASS message.
Consequence: the script's fix may not call those names; U12f runs after
`check_u12`, on the same database, reusing `_export`.

### R-06 — Windows and time zones [M]
Opened: `CLAUDE.md:25` (« Runtime: Windows / PowerShell »); grep for
`tzdata|zoneinfo|ZoneInfo|"TZ"|'TZ'|tzset` over `*.py`, `*.txt`, `*.toml` ->
no output.
Consequence: U12f uses `datetime.timezone(timedelta(hours=N))` only, never
an IANA name and never the `TZ` variable.

### R-07 — a new module's obligations [M]
Opened: `tooling/verify/checks/file_map.py:1-15` (FM1 docstring, FM3 fresh
`FILE_MAP.md` from `tooling/glue/gen_file_map.py`); `module_budget.py:1-14`.
Consequence: commit 1 writes the docstring and regenerates `FILE_MAP.md`.

### R-08 — decision records [M]
Opened: `tooling/verify/checks/decisions_index.py:1-40` (header pattern; the
brief letter is LOWERCASE; `DECISIONS_INDEX.md` equals a fresh
`gen_decisions_index.py` render); `tooling/standards/
ARCHITECTURE_DECISIONS.md` (ends `---` / blank / `*Co-built with Claude,
June 2026.*`).
Consequence: the record goes above that footer, then the index is
regenerated.

## Contracts

### C-01 — `local_midnight_utc`
Produced by: BRIEF-0123-A (commit 1 without `tz`; commit 2 adds `tz`)
Consumed by: BRIEF-0123-A (`cockpit/routes/dashboard.py`,
`scripts/export_lore_usage.py`, `tooling/verify/checks/lore_usage.py` U12f)
Module: `src/world_engine/local_day.py`, standard library imports only.
Signature (after commit 2):
`def local_midnight_utc(day: date, tz: Optional[tzinfo] = None) -> datetime`
Return shape: a NAIVE `datetime` (tzinfo None) in UTC: the instant at which
`day` begins on clock `tz`, or on the machine's local clock when `tz` is
None.
Body (after commit 2):
```python
    local = (datetime.combine(day, time.min, tzinfo=tz) if tz is not None
             else datetime.combine(day, time.min).astimezone())
    return local.astimezone(UTC).replace(tzinfo=None)
```
Error and empty cases: none raised by design; `day` is always a `date`.

### C-02 — `--since` of `scripts/export_lore_usage.py`
Produced by: BRIEF-0123-A (commit 2)   Consumed by: U12c, U12f, Nia
Shape: `--since YYYY-MM-DD` parsed by `_since_day(raw) -> date`
(`date.fromisoformat`; a `ValueError` becomes
`argparse.ArgumentTypeError(f"not a date YYYY-MM-DD: {raw!r}")`), passed as
argparse `type=`. `_read(since: date | None, world_ref)` keeps the rows of
every attempt whose first event's naive `created_at >=
local_midnight_utc(since)`.
Error and empty cases: a non-date -> argparse error, exit 2, no file
written; a date after every row -> empty file, exit 0.

## Context

`/verify` is red every evening: U12c asks the Lore usage export for
`--since <tomorrow>` (a local date) and the script, reading the date as
midnight UTC, keeps the evening's rows. The dashboard already reads dates on
the cockpit's clock (`_utc`, TICKET-0115 E2). This brief gives the export
the same reading through one shared function, and adds a rule that proves it
at any hour on any machine. Locked decisions: A1, B3, C1 of TICKET-0123.

## Scope IN

**Commit 1 — pure move (no behaviour change).**

1. Create `src/world_engine/local_day.py`, exactly:
   ```python
   """A real-world day on the cockpit's own clock (Nia's machine), turned into the naive UTC instant every timestamp is stored in (TICKET-0123, BRIEF-0123-A; decision A1).

   The one meaning of « a day » for the dashboard's `since`/`until`
   (`cockpit/routes/dashboard.py`) and for `scripts/export_lore_usage.py`'s
   `--since`. Standard library only.
   """

   from __future__ import annotations

   from datetime import UTC, date, datetime, time


   def local_midnight_utc(day: date) -> datetime:
       """Midnight of `day` on the cockpit's own clock (Nia's machine), as the
       naive UTC the timestamps are stored in."""
       return datetime.combine(day, time.min).astimezone().astimezone(UTC).replace(tzinfo=None)
   ```
2. In `src/world_engine/cockpit/routes/dashboard.py`:
   - :18 becomes `from datetime import date, timedelta`;
   - after :28 `from ...db import get_session`, add
     `from ...local_day import local_midnight_utc`;
   - delete `_utc` (:43-46) and the blank lines that separated it, leaving
     two blank lines between `_day` and `scope_of`;
   - :59 `since=_utc(first) ...` -> `since=local_midnight_utc(first) ...`;
     :60 `until=_utc(last + timedelta(days=1)) ...` ->
     `until=local_midnight_utc(last + timedelta(days=1)) ...`.
   Nothing else in the file changes (module docstring included).
3. Run `python tooling/glue/gen_file_map.py` and stage
   `tooling/standards/FILE_MAP.md`.
4. Commit: `TICKET-0123 A: move the dashboard's local-day conversion to local_day.py (pure move)`.

**Commit 2 — the script, the rule, the record.**

5. `src/world_engine/local_day.py`: the import line becomes
   `from datetime import UTC, date, datetime, time, tzinfo`, add
   `from typing import Optional` after it, and replace the function with
   C-01 verbatim:
   ```python
   def local_midnight_utc(day: date, tz: Optional[tzinfo] = None) -> datetime:
       """Midnight of `day` on the cockpit's own clock (Nia's machine), as the
       naive UTC the timestamps are stored in. `tz` fixes the clock instead of
       the machine's (`lore_usage.py` U12f); None is the machine's."""
       local = (datetime.combine(day, time.min, tzinfo=tz) if tz is not None
                else datetime.combine(day, time.min).astimezone())
       return local.astimezone(UTC).replace(tzinfo=None)
   ```
6. `scripts/export_lore_usage.py`:
   - :34 becomes `from datetime import date, datetime`;
   - after `from world_engine.db import engine  # noqa: E402` add
     `from world_engine.local_day import local_midnight_utc  # noqa: E402`;
   - insert above `def _read`:
     ```python
     def _since_day(raw: str) -> date:
         """`--since`: a date `YYYY-MM-DD`, nothing else (decision C1)."""
         try:
             return date.fromisoformat(raw)
         except ValueError as exc:
             raise argparse.ArgumentTypeError(f"not a date YYYY-MM-DD: {raw!r}") from exc
     ```
   - `_read`'s signature becomes
     `def _read(since: date | None, world_ref: str | None) -> list[LoreUsageEvent]:`;
   - :99 becomes `        start = local_midnight_utc(since)`;
   - :104 `                >= start.replace(tzinfo=None)]` becomes
     `                >= start]` (`start` is already naive);
   - :111 becomes
     ```python
         parser.add_argument("--since", type=_since_day,
                             help="keep attempts started on or after this date (YYYY-MM-DD), on the cockpit's clock")
     ```
   - in the module docstring, after the paragraph ending « it can never be
     staged by accident. », add the paragraph:
     ```
     `--since` is a date, read on the cockpit's own clock like the dashboard's
     « du » (`world_engine.local_day`, TICKET-0123): `--since 2026-10-14`
     keeps the attempts started from midnight of the 14th at Nia's place.
     Anything but a date `YYYY-MM-DD` is refused.
     ```
   No other line of the script changes.
7. `tooling/verify/checks/lore_usage.py`:
   - in the docstring, after U12's item `e.` (:103-104), add:
     ```
        f. a day is the cockpit's day (TICKET-0123, B3, C1):
           `local_midnight_utc` of 2026-10-14 is, at UTC-4, UTC-12, UTC+14
           and UTC+0, the naive UTC instant of that local midnight, with
           23:30 the evening before strictly earlier and 00:30 not earlier;
           the export script calls `local_midnight_utc` and never
           `datetime.fromisoformat`; `--since 2026-10-14T05:00` exits 2 and
           writes no file. Fixed offsets only: no IANA name, no `TZ`
           (Windows).
     ```
   - insert between `check_u12` and `main` (after :904):
     ```python


     _U12F_CLOCKS = (
         (-4, "2026-10-14T04:00:00"),
         (-12, "2026-10-14T12:00:00"),
         (14, "2026-10-13T10:00:00"),
         (0, "2026-10-14T00:00:00"),
     )


     def check_u12f(db_path: str) -> None:
         import ast
         from datetime import date, datetime, timedelta, timezone

         from world_engine.local_day import local_midnight_utc

         day = date(2026, 10, 14)
         for hours, want in _U12F_CLOCKS:
             tz = timezone(timedelta(hours=hours))
             got = local_midnight_utc(day, tz)
             if got.tzinfo is not None or got.isoformat() != want:
                 fail(f"U12f: local midnight of {day} at UTC{hours:+d} is {got.isoformat()}, want {want}")
                 continue
             evening = datetime(2026, 10, 13, 23, 30, tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
             morning = datetime(2026, 10, 14, 0, 30, tzinfo=tz).astimezone(timezone.utc).replace(tzinfo=None)
             if not evening < got <= morning:
                 fail(f"U12f: at UTC{hours:+d}, 23:30 the evening before or 00:30 of {day} is on the wrong side")
         tree = ast.parse(EXPORT.read_text(encoding="utf-8"))
         names = [(n.func.attr if isinstance(n.func, ast.Attribute) else getattr(n.func, "id", ""),
                   getattr(getattr(n.func, "value", None), "id", None))
                  for n in ast.walk(tree) if isinstance(n, ast.Call)]
         if not names:
             fail("U12f: no call collected from the export script")
         if ("local_midnight_utc", None) not in names:
             fail("U12f: the export script never calls local_midnight_utc()")
         if ("fromisoformat", "datetime") in names:
             fail("U12f: the export script calls datetime.fromisoformat() -- --since is a date on the cockpit's clock")
         tmp = tempfile.mkdtemp(prefix="lore_usage_since_")
         result, _ = _export(db_path, f"{tmp}/bad.jsonl", "--since", "2026-10-14T05:00")
         if result.returncode != 2 or pathlib.Path(f"{tmp}/bad.jsonl").exists():
             fail(f"U12f: --since 2026-10-14T05:00 exit {result.returncode}, want 2 and no file")
     ```
   - in `main`, after `    check_u12(db_path)` add `    check_u12f(db_path)`;
   - in the PASS message, replace the final fragment
     `"both panels send their attempt id; the export reads every attempt and writes nothing")`
     with
     `"both panels send their attempt id; the export reads every attempt and writes nothing, "`
     followed by a new line
     `"and reads --since as a day on the cockpit's clock")`.
   U12a-e are not touched.
8. `tooling/standards/ARCHITECTURE_DECISIONS.md`: insert ABOVE the closing
   `---` / `*Co-built with Claude, June 2026.*` footer (never appended after
   it):
   ```
   ## A DAY IS THE COCKPIT'S DAY (TICKET-0123) -- `local_day.py`, the Lore usage export's `--since` (BRIEF-0123-a, no schema change)

   A real-world date typed by the creator means that day at her place, never
   that day in UTC. `world_engine/local_day.py`'s `local_midnight_utc(day)`
   is the one conversion into the naive UTC the timestamps are stored in; the
   dashboard's « du / au » (TICKET-0115, E2) and
   `scripts/export_lore_usage.py --since` both use it. `--since` accepts a
   date only (C1). The conversion takes an optional fixed clock so
   `lore_usage.py` U12f proves it at any hour on any machine, with fixed
   offsets: the `TZ` variable proves nothing on Windows (B3; rejected B2,
   reactivation: `tzdata` becomes a dependency for another reason). A third
   reader of a typed date imports this function; it never writes a third
   conversion (A1; rejected A2).

   ```
   Then run `python tooling/glue/gen_decisions_index.py` and stage
   `tooling/standards/DECISIONS_INDEX.md`.
9. Commit: `TICKET-0123 A: the Lore usage export reads --since on the cockpit's clock (U12f)`.

## Scope OUT

- Any other rule of `lore_usage.py` (U0-U12e): unchanged, U12c included (B3
  keeps it as it is).
- Any `TZ` manipulation, `zoneinfo`, or a `tzdata` dependency (B2 rejected).
- Re-stamping journal rows in the check's database (B4 rejected).
- The three other `_utc` helpers (`passages.py:33`, `encounters.py:41`,
  `scripts/migrate_v2_14_passage.py:154`): they take a `datetime`, not a
  day; not this ticket.
- Any other place that turns a typed date into an instant: not enumerated;
  report it if met, change nothing (a ticket above 0123).
- The dashboard's behaviour, routes, query parameters or docstring.
- `--until` or any new option for the export script.
- TICKET-0121, its branch and its briefs.
- Any other script, module or doc beyond those listed in Scope IN.

## Invariants to defend

- **The export's secrets stay out of the repository** (the script's own
  refusal of an `--out` inside the repo, U12e): the edit to `main` must not
  move or weaken the `REPO in out.parents` refusal.
- **Read-only export** (U12d): no `add`, `commit`, `delete`, `execute` or
  `write_*` call may enter the script.
- **A pure move precedes new logic** (standing convention): commit 1 changes
  no behaviour; `dashboard_registry.py` passes on it unchanged.
- No CLAUDE.md invariant on canon writes, schema or the UI/JSON boundary is
  touched: no table, no column, no UI surface changes.

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold.
- `dashboard_registry.py` fails after commit 1.
- U12d or U12e fails after commit 2.
- The prompt to change any line of `ARCHITECTURE_DECISIONS.md` other than the
  inserted record, or of `CLAUDE.md`.

ADAPT:
- Line numbers shifted but the anchored text is identical and unique: use
  the text, report the new numbers.
- `gen_file_map.py` or `gen_decisions_index.py` changes lines beyond the new
  module or record (another stale entry already on `main`): keep the
  regenerated file as produced, report which lines.
- `lore_usage.py` exceeds 15 s under `corpus_gate.py` with U12f: report the
  timing with and without U12f, change nothing.

REPORT-ONLY:
- Any other reader of a typed date found while working.
- Style or wording you would change in the files touched.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

All with `WORLD_ENGINE_ENV=test`.

- [ ] After commit 1: `python tooling/verify/checks/dashboard_registry.py`,
      `file_map.py`, `import_cycle.py`, `module_budget.py` print PASS;
      `git show --stat HEAD` lists exactly `src/world_engine/local_day.py`,
      `src/world_engine/cockpit/routes/dashboard.py`,
      `tooling/standards/FILE_MAP.md`.
- [ ] After commit 2: `python tooling/verify/checks/lore_usage.py` prints
      PASS, whatever the hour.
- [ ] Mutation M1 (temporary, reverted, reported): the script's
      `start = local_midnight_utc(since)` replaced by
      `start = datetime.fromisoformat(since.isoformat())` ->
      `lore_usage.py` prints a FAIL naming U12f, at any hour.
- [ ] Mutation M2 (temporary, reverted, reported): `local_midnight_utc`
      returning `local.replace(tzinfo=None)` -> `lore_usage.py` prints FAIL
      lines naming U12f for UTC-4, UTC-12 and UTC+14.
- [ ] `python scripts/export_lore_usage.py --out <path outside the repo>
      --since hier` exits 2 with « not a date YYYY-MM-DD: 'hier' ».
- [ ] `python tooling/verify/checks/decisions_index.py` and `file_map.py`
      print PASS.
- [ ] `python tooling/verify/run.py --ticket TICKET-0123` passes.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `tooling/standards/FILE_MAP.md` (generated, commit 1).
- `tooling/standards/ARCHITECTURE_DECISIONS.md` record and
  `tooling/standards/DECISIONS_INDEX.md` (generated), commit 2.
- No schema changelog entry (no schema change). No CLAUDE.md change.
