<!-- slug: usage-export -->
# BRIEF 0103-E — "The journal's one reader: a JSONL export"

Lot: LOT-0103-lore-usage-journal.md (authoritative on conflict)
Depends on: BRIEF-0103-A (the table), BRIEF-0103-C and D (U12 reads what U8-U9 journal)
Commit header for decisions: `(BRIEF-0103-e, no schema change)`

## Anchors to confirm (Mini-RECON)

Confirm each on the branch `ticket/0103`, on the tree BRIEF-0103-D left, before applying anything. Halt if one has moved (line numbers may drift by a few lines; the quoted text must match).

- `tooling/verify/checks/env_guard.py:12` → `  (b) carries a fail-closed guard: reads `os.environ.get("WORLD_ENGINE_ENV")`` (the guard `scripts/migrate_v2_13_lore_usage.py` already carries).
- `tooling/verify/checks/claude_md_contract.py:69-71` → `TOTAL_CHAR_BUDGET = 38_000`, `MAX_LINE_LENGTH = 100`, `FILE_STRUCTURE_LINE_BUDGET = 80`.
- `CLAUDE.md:375` → `- **The lore renderer receives rows, never a `Session`,** and only the `answered` verdict reaches` (the last invariant, followed by `## Local model notes` after one blank line); the `### File structure` section is exactly 80 lines.
- `scripts/export_lore_usage.py` does not exist.
- `python tooling/verify/checks/lore_usage.py` passes (U0-U11).

## Facts carried

### R-10 — what the world cascade calls a world's table [M]
Opened: `tooling/verify/checks/world_cascade.py:9-14` (W1) and its
implementation `_reaching_tables` 208-224.
Finding: a table is world-reaching if it has a `world_id` column or a FK to
a world-reaching table; every such table must be named by
`delete_world_cascade`.
Consequence: I1 — the journal has `world_ref` and `world_name`, no
`world_id`, no FK at all; U1 asserts it, U4 proves a row outlives its world.

### R-15 — scripts and CLAUDE.md budgets [M]
Opened: `tooling/verify/checks/env_guard.py:7-15` (a script importing the
engine carries a fail-closed env guard before the import),
`tooling/verify/checks/claude_md_contract.py:12-14, 69-71` (38 000
characters, 100 per line, File structure ≤ 80 lines); enumeration E5.
Finding: CLAUDE.md is at 36 922 characters and its File structure section
at exactly 80 lines.
Consequence: the export carries the migration's guard; E adds one
invariant and no File structure line.

## Contracts

### C-02 — `PAYLOAD_KEYS` (consumed, as stored)
- `questions`: `statement, questions, error`
- `draft`: `statement, answers, draft, error`
- `commit`: `proposal, result, error`
- `ask`: `question, response, error`
- `resolve`: `question, plan, bindings, response, error`

### C-07 — the export line
Produced by: BRIEF-0103-E   Consumed by: the analysis session
One JSON line per `(attempt_id, world_ref, kind)`, in start order:
`attempt_id, kind, world_ref, world_name, started_at, ended_at, committed
(true/false for write, null for consult), lore_entry_refs, events: [step,
outcome, created_at, payload, model_calls, lore_entry_ref]`. Options
`--out` (required, refused inside the repository), `--since`,
`--world-ref`. Read-only.

## Context

« No structure without a reader »: the journal's reader is a script, run before an analysis session in Claude Code (E1). It exports, it never diffs or summarizes — the analysis does that from the draft and the committed proposal of each attempt (D1). The export carries every world's secrets and creator notes, so it refuses to write inside the repository.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. Generated files (`tooling/standards/DECISIONS_INDEX.md`)
are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It: creates `scripts/export_lore_usage.py` (C-07: env guard (b) before the engine import; groups the journal's rows, read in `(created_at, id)` order, by `(attempt_id, world_ref, kind)`; `committed` true/false for a write attempt, null for a consultation; `--since`, `--world-ref`; refuses an `--out` inside the repository with exit 2; writes nothing to the database); adds one invariant to CLAUDE.md after the lore renderer's (no File structure line: the section is at its 80-line budget); extends `lore_usage.py` with U12 and the `scripts/` census in U0; appends the decision entry.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(lore): export the Lore usage journal as JSON Lines, its one reader (BRIEF-0103-e)`.

````diff
diff --git a/CLAUDE.md b/CLAUDE.md
index 2e46fd1..43d9a39 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -374,6 +374,9 @@ Law only. Rationale, chantier history, and deferred alternatives live in
   same body — enforced by `effect_self_write.py`.
 - **The lore renderer receives rows, never a `Session`,** and only the `answered` verdict reaches
   a model — every empty verdict is rendered by code, so an absence is never explained by a model.
+- **The Lore usage journal (`lore_usage_event`) is written only through `lore_usage` and read only
+  by `scripts/export_lore_usage.py`;** no prompt, play or creator path reads it back, and it has no
+  `world_id`, so it outlives its world -- enforced by `lore_usage.py`.
 
 ## Local model notes
 
diff --git a/scripts/export_lore_usage.py b/scripts/export_lore_usage.py
new file mode 100644
index 0000000..6ad5cb4
--- /dev/null
+++ b/scripts/export_lore_usage.py
@@ -0,0 +1,130 @@
+"""Export the Lore shell's usage journal as JSON Lines (TICKET-0103,
+BRIEF-0103-E, decision E1).
+
+The journal's sole reader (`lore_usage_event`, schema v2.13). One line per
+attempt -- one use of a Lore panel, keyed by `(attempt_id, world_ref, kind)`
+-- in the order the attempts started:
+
+    {"attempt_id", "kind", "world_ref", "world_name", "started_at",
+     "ended_at", "committed", "lore_entry_refs", "events": [
+        {"step", "outcome", "created_at", "payload", "model_calls",
+         "lore_entry_ref"}, ...]}
+
+`committed` is true when a write attempt holds an `ok` commit, false when it
+holds none (an abandoned attempt), and null for a consultation. Nothing is
+diffed or summarized here: the analysis reads the draft and the committed
+proposal of an attempt from its events. Read-only: this script never writes
+the database.
+
+The export carries everything the journal holds -- secrets and creator notes
+of every world included -- so it refuses an `--out` inside this repository:
+it can never be staged by accident.
+
+Run from the project root:
+
+    python scripts/export_lore_usage.py --out lore_usage.jsonl [--since 2026-10-01] [--world-ref <id>]
+"""
+
+from __future__ import annotations
+
+import argparse
+import json
+import os
+import sys
+from datetime import datetime
+from pathlib import Path
+
+REPO = Path(__file__).resolve().parent.parent
+SRC = REPO / "src"
+sys.path.insert(0, str(SRC))
+
+_env = os.environ.get("WORLD_ENGINE_ENV")
+if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
+    print(
+        "export_lore_usage.py refuses to run without WORLD_ENGINE_ENV or "
+        "WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
+        f"{_env or 'unset'}.",
+        file=sys.stderr,
+    )
+    sys.exit(1)
+
+from sqlmodel import Session, select  # noqa: E402
+
+from world_engine.db import engine  # noqa: E402
+from world_engine.models import LoreUsageEvent  # noqa: E402
+
+
+def _iso(value: datetime) -> str:
+    return value.isoformat()
+
+
+def _event(row: LoreUsageEvent) -> dict:
+    return {
+        "step": row.step, "outcome": row.outcome, "created_at": _iso(row.created_at),
+        "payload": row.payload, "model_calls": row.model_calls,
+        "lore_entry_ref": row.lore_entry_ref,
+    }
+
+
+def attempts(rows: list[LoreUsageEvent]) -> list[dict]:
+    """Group `rows` (already in `(created_at, id)` order) by attempt, in the
+    order each attempt's first event appears."""
+    grouped: dict[tuple[str, str, str], dict] = {}
+    for row in rows:
+        key = (row.attempt_id, row.world_ref, row.kind)
+        attempt = grouped.get(key)
+        if attempt is None:
+            attempt = grouped[key] = {
+                "attempt_id": row.attempt_id, "kind": row.kind, "world_ref": row.world_ref,
+                "world_name": row.world_name, "started_at": _iso(row.created_at),
+                "ended_at": None, "committed": None, "lore_entry_refs": [], "events": [],
+            }
+        attempt["events"].append(_event(row))
+        attempt["ended_at"] = _iso(row.created_at)
+        if row.lore_entry_ref is not None:
+            attempt["lore_entry_refs"].append(row.lore_entry_ref)
+    for attempt in grouped.values():
+        if attempt["kind"] == "write":
+            attempt["committed"] = bool(attempt["lore_entry_refs"])
+    return list(grouped.values())
+
+
+def _read(since: str | None, world_ref: str | None) -> list[LoreUsageEvent]:
+    query = select(LoreUsageEvent).order_by(LoreUsageEvent.created_at, LoreUsageEvent.id)
+    if world_ref:
+        query = query.where(LoreUsageEvent.world_ref == world_ref)
+    with Session(engine) as session:
+        rows = list(session.exec(query).all())
+    if since:
+        start = datetime.fromisoformat(since)
+        first: dict[tuple[str, str, str], datetime] = {}
+        for row in rows:
+            first.setdefault((row.attempt_id, row.world_ref, row.kind), row.created_at)
+        rows = [r for r in rows if first[(r.attempt_id, r.world_ref, r.kind)].replace(tzinfo=None)
+                >= start.replace(tzinfo=None)]
+    return rows
+
+
+def main(argv: list[str] | None = None) -> int:
+    parser = argparse.ArgumentParser(description="Export the Lore usage journal as JSON Lines.")
+    parser.add_argument("--out", required=True, help="the .jsonl file to write (overwritten)")
+    parser.add_argument("--since", help="keep attempts started on or after this ISO date")
+    parser.add_argument("--world-ref", help="keep one world's attempts (a world id, even deleted)")
+    args = parser.parse_args(argv)
+    out = Path(args.out).resolve()
+    if out == REPO or REPO in out.parents:
+        print(f"export_lore_usage.py refuses to write inside the repository ({out}): "
+              "the export holds every world's secrets. Choose a path outside it.", file=sys.stderr)
+        return 2
+    rows = _read(args.since, args.world_ref)
+    exported = attempts(rows)
+    out.parent.mkdir(parents=True, exist_ok=True)
+    with out.open("w", encoding="utf-8") as handle:
+        for attempt in exported:
+            handle.write(json.dumps(attempt, ensure_ascii=False) + "\n")
+    print(f"{len(exported)} attempt(s), {len(rows)} event(s) -> {out}")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 208ee6a..e22049a 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -17678,6 +17678,24 @@ and mints its own for a missing or malformed one. A write attempt without
 an `ok` commit is an abandoned one: the analysis reads that from the
 journal, nothing records it.
 
+
+## THE LORE USAGE JOURNAL HAS ONE READER (TICKET-0103) -- A JSONL EXPORT (BRIEF-0103-e, no schema change)
+
+**E1.** `scripts/export_lore_usage.py` is the journal's sole reader (the
+"no structure without a reader" doctrine): one JSON line per attempt, keyed
+by `(attempt_id, world_ref, kind)`, its events in order with payloads and
+model calls as stored, plus `committed` (true / false for a write attempt,
+null for a consultation). It filters by `--since` and `--world-ref` (a
+deleted world's id still works) and writes nothing to the database. The
+export holds every world's secrets and creator notes, so the script refuses
+an `--out` inside the repository: it cannot be staged by accident. The
+analysis -- what the creator removed, changed, added, abandoned -- runs on
+the export, in a Claude Code session, never in the application.
+
+**Rejected.** E2, an analysis panel in the cockpit: reactivates once an
+analysis has shown which measures deserve a screen; its first UI consumer
+relationalizes the JSON columns (D2).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/lore_usage.py b/tooling/verify/checks/lore_usage.py
index 2c52f10..40ece0c 100644
--- a/tooling/verify/checks/lore_usage.py
+++ b/tooling/verify/checks/lore_usage.py
@@ -8,6 +8,8 @@ U0 -- census. The files under `src/world_engine` that name the journal
    (`LoreUsageEvent` or `lore_usage_event`) equal `_NAMING_FILES` exactly,
    and the files that call `write_usage_event` equal `_WRITER_CALLERS`:
    nothing in the application reads the journal, and one module writes it.
+   Under `scripts/`, the files naming the journal equal `_SCRIPTS` (its
+   migration and its one reader, BRIEF-0103-E).
 U1 -- schema (BRIEF-0103-A, v2.13, I1). `lore_usage_event` has no
    `world_id` column and no foreign key at all; `world_ref`, `world_name`,
    `attempt_id`, `kind`, `step`, `outcome`, `payload`, `model_calls` are NOT
@@ -86,6 +88,20 @@ U11 -- the panels carry the attempt (BRIEF-0103-D), static:
       crypto.randomUUID()` before its POST, both POSTs send `attempt_id:
       loreState.attemptId`, and `reloadForWorld()` clears it;
    c. the built bundle under `cockpit/static/assets` carries `attempt_id`.
+U12 -- the reader (BRIEF-0103-E, E1), `scripts/export_lore_usage.py` run as
+   a subprocess on this check's database once U3-U9 have filled it:
+   a. one line per `(attempt_id, world_ref, kind)` in the journal, each with
+      exactly that attempt's events, in order;
+   b. U8's write attempt is `committed: true` with its one `lore_entry_ref`;
+      U3's (a draft, no commit) is `committed: false`; U9's consultation is
+      `committed: null`; U4's attempt is exported with its deleted world's
+      name;
+   c. `--world-ref` keeps one world's attempts only; `--since` a day after
+      today writes an empty file and exits zero;
+   d. the script is read-only: no `.add(`, `.commit(`, `.delete(`,
+      `.execute(` and no `write_` call;
+   e. an `--out` inside the repository is refused (non-zero exit) and no
+      file is written there.
 
 Fresh temp-file SQLite database for any fixture rule
 (`WORLD_ENGINE_DATABASE_URL` set before any world_engine import) -- never
@@ -112,6 +128,8 @@ _NAMING_FILES: frozenset[str] = frozenset({
 })
 _WRITER_CALLERS: frozenset[str] = frozenset({"writes/lore_usage.py", "lore_usage.py"})
 _ROUTES = ("cockpit/routes/lore.py", "cockpit/routes/lore_write.py")
+_SCRIPTS: frozenset[str] = frozenset({"migrate_v2_13_lore_usage.py", "export_lore_usage.py"})
+EXPORT = ROOT / "scripts" / "export_lore_usage.py"
 _PIPELINE = {"lore_selectors", "lore_query", "lore_plan", "lore_render", "lore_prompt"}
 _PANEL = {"lore_write_apply", "lore_write_draft", "lore_write_read", "lore_mentions_read",
           "lore_choices_read"}
@@ -186,6 +204,9 @@ def check_u0() -> None:
         fail(f"U0: {extra} calls write_usage_event but is not in _WRITER_CALLERS")
     for missing in sorted(_WRITER_CALLERS - callers):
         fail(f"U0: {missing} is in _WRITER_CALLERS but never names write_usage_event")
+    scripts = {p.name for p in (ROOT / "scripts").glob("*.py") if _naming(p)}
+    if scripts != _SCRIPTS:
+        fail(f"U0: scripts naming the journal are {sorted(scripts)}, expected {sorted(_SCRIPTS)}")
 
 
 def _check_sql(table, name: str) -> str:
@@ -809,6 +830,80 @@ def check_u11() -> None:
         fail("U11c: the built bundle does not carry attempt_id (rebuild the frontend)")
 
 
+def _export(db_path: str, out: str, *extra: str) -> tuple[subprocess.CompletedProcess, list[dict]]:
+    import json
+
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    result = subprocess.run([sys.executable, str(EXPORT), "--out", out, *extra], env=env,
+                            capture_output=True, text=True, cwd=str(ROOT), timeout=120)
+    lines = []
+    if result.returncode == 0:
+        lines = [json.loads(line) for line in pathlib.Path(out).read_text(encoding="utf-8").splitlines()]
+    return result, lines
+
+
+def check_u12(db_path: str) -> None:
+    import ast
+    from datetime import date, timedelta
+
+    from sqlmodel import Session, select
+
+    from world_engine.db import engine
+    from world_engine.models import LoreUsageEvent
+
+    with Session(engine) as db:
+        rows = list(db.exec(select(LoreUsageEvent)).all())
+    keys: dict[tuple, int] = {}
+    for row in rows:
+        keys[(row.attempt_id, row.world_ref, row.kind)] = keys.get((row.attempt_id, row.world_ref, row.kind), 0) + 1
+    if len(keys) < 4:
+        fail(f"U12: only {len(keys)} attempt(s) to export")
+        return
+    tmp = tempfile.mkdtemp(prefix="lore_usage_export_")
+    result, lines = _export(db_path, f"{tmp}/all.jsonl")
+    if result.returncode != 0:
+        fail(f"U12a: export exit {result.returncode}: {result.stderr.strip()[-200:]}")
+        return
+    got = {(a["attempt_id"], a["world_ref"], a["kind"]): len(a["events"]) for a in lines}
+    if got != keys or len(lines) != len(keys):
+        fail(f"U12a: exported {len(lines)} attempt(s), journal holds {len(keys)}")
+    for attempt in lines:
+        stamps = [e["created_at"] for e in attempt["events"]]
+        if stamps != sorted(stamps):
+            fail(f"U12a: attempt {attempt['attempt_id']} events out of order")
+    by_id = {a["attempt_id"]: a for a in lines}
+    write = by_id.get("0b0b0b0b-0000-4000-8000-000000000008", {})
+    if write.get("committed") is not True or len(write.get("lore_entry_refs", [])) != 1:
+        fail(f"U12b: the committed write attempt exported as {write.get('committed')!r}")
+    if by_id.get("att-u3", {}).get("committed") is not False:
+        fail("U12b: an attempt without commit is not committed: false")
+    if by_id.get("0c0c0c0c-0000-4000-8000-000000000009", {}).get("committed", "-") is not None:
+        fail("U12b: a consultation is not committed: null")
+    if by_id.get("att-u4", {}).get("world_name") != "Doomed 0103":
+        fail("U12b: the deleted world's attempt is missing or nameless")
+    world_ref = write.get("world_ref", "")
+    result, lines = _export(db_path, f"{tmp}/one.jsonl", "--world-ref", world_ref)
+    if result.returncode != 0 or not lines or {a["world_ref"] for a in lines} != {world_ref}:
+        fail(f"U12c: --world-ref exported {[a['world_ref'] for a in lines]}")
+    tomorrow = (date.today() + timedelta(days=1)).isoformat()
+    result, lines = _export(db_path, f"{tmp}/none.jsonl", "--since", tomorrow)
+    if result.returncode != 0 or lines:
+        fail(f"U12c: --since {tomorrow} exit {result.returncode}, {len(lines)} line(s)")
+    inside = ROOT / "tooling" / "verify" / "results" / "lore_usage_refused.jsonl"
+    result, _ = _export(db_path, str(inside))
+    if result.returncode == 0 or inside.exists():
+        fail(f"U12e: an --out inside the repository was accepted (exit {result.returncode})")
+        inside.unlink(missing_ok=True)
+    tree = ast.parse(EXPORT.read_text(encoding="utf-8"))
+    calls = [n.func for n in ast.walk(tree) if isinstance(n, ast.Call)]
+    if not calls:
+        fail("U12d: no call collected from the export script")
+    for func in calls:
+        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
+        if name in ("add", "commit", "delete", "execute") or name.startswith("write_"):
+            fail(f"U12d: the export script calls {name}() at line {func.lineno}")
+
+
 def main() -> int:
     tmp = tempfile.mkdtemp(prefix="lore_usage_")
     db_path = f"{tmp}/u.db"
@@ -827,6 +922,7 @@ def main() -> int:
     check_u9()
     check_u10()
     check_u11()
+    check_u12(db_path)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -836,7 +932,7 @@ def main() -> int:
           "writer refuses every malformed record; a journal row outlives its world; every "
           "Lore model call can be captured with its prompt version and raw reply; every "
           "writing and consultation step is journaled under its attempt, failures included; "
-          "both panels send their attempt id")
+          "both panels send their attempt id; the export reads every attempt and writes nothing")
     return 0
 
 
````

## Scope OUT

- The analysis itself, and any summary, diff or statistic computed by the script (D1: the analysis computes them from the export).
- An in-app analysis screen or route (E2).
- Exporting `lore_entry` rows committed before this ticket.
- Pruning, archiving or deleting journal rows after an export.
- A File structure line for the script in CLAUDE.md (over the section's budget).
- Running the export on Nia's database (live gate).

## Invariants to defend

**History is sacred:** the export only reads; U12d proves it calls no `add`/`commit`/`delete`/`execute`/`write_*`. **Secrets are structurally excluded** from every assembled context: the journal holds secrets and stays out of every prompt — the new CLAUDE.md invariant and U0 make the export its only reader; its output can never land in the repository (U12e).

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- `claude_md_contract.py` fails (a budget is exceeded): do not trim other invariants to make room.
- The full corpus is not green after the commit, for a reason the diff does not explain.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `git apply` fails only on `CLAUDE.md` because another invariant was appended after the lore renderer's: insert this brief's three-line invariant at the end of the Invariants section by hand.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `python tooling/verify/checks/lore_usage.py` → `PASS: lore_usage -- … both panels send their attempt id; the export reads every attempt and writes nothing`.
- `env_guard.py`, `claude_md_contract.py`, `decisions_index.py`, `single_canon_write.py` → `PASS`.
- `python scripts/export_lore_usage.py --out ./tooling/x.jsonl` (with `WORLD_ENGINE_ENV=test`) exits 2 and writes no file.
- Mutation test: in `export_lore_usage.py`, set `attempt["committed"] = True` for every write attempt; U12b fails; revert.
- `WORLD_ENGINE_ENV=test python tooling/verify/run.py --ticket TICKET-0103-lore-usage-journal` → every linked check `PASS`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` → 137/137.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

CLAUDE.md: one invariant (the journal's single writer path, single reader, no `world_id`) — in the diff. Decision entry `THE LORE USAGE JOURNAL HAS ONE READER (TICKET-0103) -- A JSONL EXPORT (BRIEF-0103-e, no schema change)` — in the diff.
