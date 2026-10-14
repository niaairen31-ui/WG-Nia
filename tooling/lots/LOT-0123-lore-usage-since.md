# LOT — TICKET-0123 "The Lore usage export reads `--since` on the cockpit's clock -- one meaning of « a day » for the export and the dashboard"

## Objective and cut

`scripts/export_lore_usage.py --since D` reads D as midnight UTC, so between
20 h and midnight in Toronto it keeps the evening's rows, and U12c fails
every evening. The dashboard already reads its dates on the cockpit's clock.
This lot gives « a day » one meaning: the dashboard's conversion moves to a
neutral module (A1), the script uses it, `--since` accepts a date only (C1),
and a new rule U12f proves the conversion at fixed offsets, so the proof does
not wait for the evening (B3).

The lot stops before: any other reader of a typed date (not enumerated); any
other rule of `lore_usage.py`; TICKET-0121 and its briefs.

## Briefs in this lot

- **A — one day, one meaning** (no schema change,
  `BRIEF-0123-A-lore-usage-since.md`): commit 1, pure move of
  `cockpit/routes/dashboard.py`'s `_utc` to `src/world_engine/local_day.py`
  (`local_midnight_utc`), `FILE_MAP.md` regenerated; commit 2,
  `local_midnight_utc` gains `tz`, `scripts/export_lore_usage.py` reads
  `--since` through it (C1), U12f in `tooling/verify/checks/lore_usage.py`,
  the decision record and its index.

## Dependency graph

One brief. Inside it, commit 1 strictly before commit 2: commit 2 imports
the module commit 1 creates. The split into two commits is a standing
convention (a pure move precedes new logic), not a dependency.

## RECON

`main` at `301d178` (2026-10-13), cloned fresh. [M] = opened and measured.

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
lines). (The handover's path `cockpit/routes/dashboard.py:44-47` was off;
this is the file.)
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
Enumeration: `grep -rn "def _utc\|astimezone()" --include=*.py .` -> the
route's `_utc` is the only local-day conversion; three other `_utc`
(`passages.py:33`, `encounters.py:41`, `scripts/migrate_v2_14_passage.py:154`)
take a `datetime`, not a day, and are out of scope.
Consequence: A1 moves this body verbatim; afterwards the route imports
`date, timedelta` only.

### R-04 — who exercises the route's dates [M]
Opened: `tooling/verify/checks/dashboard_registry.py:242-287`.
Finding: it calls `routes.dashboard(...)` / `routes.dashboard_export(...)`
with `since`/`until` strings (`tomorrow`, `date.today()`); no check names
`_utc`. Enumeration: `grep -rln "_utc\|routes.dashboard\|routes/dashboard"
tooling/verify/checks` -> `dashboard_registry.py` only, through the routes.
Consequence: the pure move is proved by `dashboard_registry.py` passing
unchanged.

### R-05 — the check `lore_usage.py`, U12 [M]
Opened: `tooling/verify/checks/lore_usage.py` (940 lines): docstring :91-104
(U12 a-e; :99-100 « `--since` a day after today writes an empty file and
exits zero »); :120 `ROOT`, :132 `EXPORT`; :833-842 `_export(db_path, out,
*extra)` runs the script as a subprocess with `WORLD_ENGINE_DATABASE_URL`
and `WORLD_ENGINE_ENV=test`, returning `(CompletedProcess, lines)` (lines
read only on exit 0); :845 `check_u12`; :888-891 U12c (`tomorrow =
(date.today() + timedelta(days=1)).isoformat()`, local date); :891-904 U12d
(AST: no call named `add`, `commit`, `delete`, `execute` or starting with
`write_` anywhere in the script); :907 `main`, :925 `check_u12(db_path)`,
:930-935 the PASS message.
Consequence: the script's fix may not call those names; U12f runs after
`check_u12`, on the same database, reusing `_export`.

### R-06 — Windows and time zones [M]
Opened: `CLAUDE.md:25` (« Runtime: Windows / PowerShell »);
`grep -rn "tzdata\|zoneinfo\|ZoneInfo\|\"TZ\"\|'TZ'\|tzset" --include=*.py
--include=*.txt --include=*.toml .` -> no output.
Consequence: U12f uses `datetime.timezone(timedelta(hours=N))` only, never
an IANA name and never the `TZ` variable.

### R-07 — a new module's obligations [M]
Opened: `tooling/verify/checks/file_map.py:1-15` (FM1: every module under
`src/world_engine` has a module docstring; FM3: `tooling/standards/
FILE_MAP.md` equals a fresh render of `tooling/glue/gen_file_map.py`);
`tooling/verify/checks/module_budget.py:1-14` (scope `src/`; a new
two-function module is far below 40 functions / 1000 lines);
`tooling/verify/checks/import_cycle.py` (PASS at `301d178`).
Absence: `ls src/world_engine/local_day.py` -> « No such file or
directory »; `grep -rn "local_midnight_utc\|local_day" --include=*.py .` ->
no output.
Consequence: commit 1 writes the docstring and regenerates `FILE_MAP.md`.

### R-08 — decision records [M]
Opened: `tooling/verify/checks/decisions_index.py:1-40` (STRICT_HEADER
`^## .+ \(BRIEF-\d{4}(-[a-z])?(, ...)*, (schema vX.YY|no schema change)\)$`
-- the brief letter is LOWERCASE; `DECISIONS_INDEX.md` must equal a fresh
`gen_decisions_index.py` render); `tooling/standards/
ARCHITECTURE_DECISIONS.md` (last record :19786 « « SUIVI », A CRÉATION TAB
THAT READS ONLY (TICKET-0115) -- ... (BRIEF-0115-e, no schema change) »;
the file ends `---` / blank / `*Co-built with Claude, June 2026.*`).
Consequence: the new record goes above that footer, header with
`BRIEF-0123-a`, then the index is regenerated.

### R-09 — the prototype [M]
The whole of brief A was applied to a scratch copy of `301d178` and run on
2026-10-13 at ~22:10 Toronto: `lore_usage.py` PASS under `TZ=America/Toronto`
and `TZ=UTC`; `dashboard_registry.py`, `file_map.py` (after
`gen_file_map.py`), `import_cycle.py` PASS. Mutation M1 (the script's start
back to `datetime.fromisoformat(...)`) under `TZ=UTC` -> two U12f FAILs
(no call to `local_midnight_utc`; a call to `datetime.fromisoformat`).
Mutation M2 (`local_midnight_utc` returning `local.replace(tzinfo=None)`)
under `TZ=UTC` -> three U12f FAILs (UTC-4, UTC-12, UTC+14).
Consequence: gate (e) below names satisfiable modules; the mutations are
known to bite at any hour.

## Contract sheet

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
Error and empty cases: none raised by design; `day` is always a `date`
(callers parse first).

### C-02 — `--since` of `scripts/export_lore_usage.py`
Produced by: BRIEF-0123-A (commit 2)   Consumed by: U12c, U12f, Nia
Shape: `--since YYYY-MM-DD` parsed by `_since_day(raw) -> date`
(`date.fromisoformat`; a `ValueError` becomes
`argparse.ArgumentTypeError(f"not a date YYYY-MM-DD: {raw!r}")`), passed as
argparse `type=`. `_read(since: date | None, world_ref)` keeps the rows of
every attempt whose first event's naive `created_at >=
local_midnight_utc(since)`.
Error and empty cases: a non-date (`2026-10-14T05:00`, `hier`) -> argparse
error, exit 2, no file written; a date after every row -> empty file, exit 0.

## Gate output

(a) Property trace
- `--since` parsed by `datetime.fromisoformat`, compared naive -> R-01 ->
  `scripts/export_lore_usage.py`
- `created_at` is naive UTC; the writer never passes it -> R-02 ->
  `models/pipeline.py`, `models/canon.py`, `writes/lore_usage.py`
- `_utc`'s body, its only callers, the route's imports -> R-03 ->
  `cockpit/routes/dashboard.py`
- no check names `_utc`; `dashboard_registry.py` exercises the route's
  dates -> R-04 -> `tooling/verify/checks/dashboard_registry.py` (plus the
  grep enumeration)
- U12c's date is local; U12d's forbidden names; `_export`'s shape; `main`'s
  order -> R-05 -> `tooling/verify/checks/lore_usage.py`
- Windows runtime; no tz database in the project -> R-06 -> `CLAUDE.md`
  (plus the grep enumeration)
- a new module needs a docstring and a fresh map; budget scope -> R-07 ->
  `file_map.py`, `module_budget.py`
- header pattern (lowercase letter), footer position -> R-08 ->
  `decisions_index.py`, `ARCHITECTURE_DECISIONS.md`

(b) Case table -- U12f's clocks, `day = 2026-10-14`

| offset | `local_midnight_utc(day, tz)` | 23:30 on the 13th, as UTC | 00:30 on the 14th, as UTC | evening < midnight <= morning |
|---|---|---|---|---|
| UTC-4  | 2026-10-14T04:00 | 2026-10-14T03:30 | 2026-10-14T04:30 | yes |
| UTC-12 | 2026-10-14T12:00 | 2026-10-14T11:30 | 2026-10-14T12:30 | yes |
| UTC+14 | 2026-10-13T10:00 | 2026-10-13T09:30 | 2026-10-13T10:30 | yes |
| UTC+0  | 2026-10-14T00:00 | 2026-10-13T23:30 | 2026-10-14T00:30 | yes |

Input classes of `--since` (C-02): a date -> kept from local midnight; a
date-time -> exit 2, no file; a non-ISO word -> exit 2, no file; absent ->
every row. All four reachable; U12f covers the date-time class, U12c and
U12a the date and absent classes.

(c) Enumerations: pasted in R-02 (constructors), R-03 (local-day
conversions), R-04 (checks naming the route), R-06 (tz support), R-07
(`local_day` absent).

(d) [x] C-01 written before both its consumers; re-read after C-02.

(e) Gates proposed and passed
- `lore_usage.py` U12f (proposed) -> satisfied by `local_day.py` (C-01) and
  `scripts/export_lore_usage.py` (C-02); the script needs no forbidden U12d
  name (`date.fromisoformat`, `ArgumentTypeError`, `local_midnight_utc`).
- `lore_usage.py` U12a-e (passed) -> `scripts/export_lore_usage.py`,
  unchanged in shape.
- `dashboard_registry.py` (passed) -> `cockpit/routes/dashboard.py` via
  `local_day.py`.
- `file_map.py` (passed) -> `local_day.py`'s docstring + regenerated
  `FILE_MAP.md`.
- `decisions_index.py` (passed) -> the new record + regenerated
  `DECISIONS_INDEX.md`.
- `import_cycle.py`, `module_budget.py` (passed) -> `local_day.py` imports
  `datetime` and `typing` only; two top-level names.

## Amendments

(none)
