# RECON-0003 — Canon-write paths and table classification facts

**REPORT ONLY.** No edit, no fix, no classification decision. Every claim
cited `path:line`. Blocking items marked **BLOCKING FINDING**.

Ticket: TICKET-0003. Purpose: produce the complete factual map (tables ×
write sites × paths) that lets the creator classify tables
canon/ephemeral/pipeline-internal and choose the design of the
`single_canon_write` verify check.

Runtime note: read-only. Venv + `$env:PYTHONPATH="src"` only if a command
must render a verdict (none expected).

---

## Zone A — Table inventory

A1. List every SQLModel table class in `src/world_engine/models.py` (and
    any other module declaring tables, if any exists — say so explicitly
    either way): class name, table name, `file:line`.

A2. For each table, report the structural signals relevant to
    classification, as facts only:
    - has a `change_history` (or equivalent audit) column? `file:line`
    - referenced by `writes.py` helpers? (see Zone B)
    - written by `_apply_mutation`? (see Zone B)
    - append-only by doctrine (docstring/comment saying so)? `file:line`

## Zone B — Write-site inventory (the core of this recon)

B1. Repo-wide inventory of every write site in `src/`: `session.add(`,
    `session.delete(`, `session.exec(` carrying INSERT/UPDATE/DELETE,
    bulk operations, and raw SQL writes. For each: `file:line`, enclosing
    function, and the table(s) touched (from the object type or statement).

B2. Group the sites by path membership:
    (a) inside `writes.py` helpers;
    (b) inside `_apply_mutation` (directly or via writes.py — say which);
    (c) creator CRUD routes (cockpit `app.py` or elsewhere) — via
        writes.py or direct;
    (d) session/play machinery (conversation, turns, gathering lifecycle,
        proposed_mutation creation, analysis) — via writes.py or direct;
    (e) seed / migration / backup / one-off scripts;
    (f) anything else — each of these is a potential doctrine breach
        candidate; list exhaustively.

B3. **BLOCKING FINDING** if any write site cannot be attributed to a table
    statically (dynamic table dispatch, generic writes) — that would
    constrain the check design to runtime/DB strategies.

## Zone C — writes.py surface

C1. List every public helper in `writes.py`: name, tables written,
    `file:line`, and its callers (module-level inventory of call sites).

C2. Report whether any module bypasses writes.py to write a table that
    writes.py ALSO covers (same table, two conventions) — each occurrence
    cited; report only.

## Zone D — Check-design seams

D1. Static-scan viability: report whether module boundaries alone
    (writes.py + an allowlist of caller modules) suffice to express "no
    canon write outside sanctioned paths" as a grep/AST fact, given the
    B2 grouping. List the modules that would need to be on such an
    allowlist today.

D2. DB-assertion viability: report which tables carry enough audit signal
    (change_history, timestamps, provenance columns) for a DB-level
    invariant, and which carry none — cited.

D3. Report where the check would plug in (expected: same seam as
    RECON-0002 Zone E — `tooling/verify/checks/*.py` + ticket Machine
    line; confirm nothing has changed).

## Zone E — Known exemption candidates

E1. `seed_pilot.py`, `backup.py`, any migration scripts: list their write
    targets (`file:line`) so the classification session can decide their
    status (exempt-by-list vs routed-through-writes.py later).

---

## Output format

Sections mirroring Zones A–E; Zone B as a table (site, function, table,
group). End with `BLOCKING FINDINGS` recap (or "none"). No classification,
no recommendation, no fix.
