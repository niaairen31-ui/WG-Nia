# RECON — Documentation partition (schema changelog extraction + decisions index)

**REPORT ONLY.** This recon confirms facts and produces inventories. It makes
no edit, no fix, no file move — not even "obvious" ones. Every finding is
cited with `file:line`. Anything that would block the planned briefs is
marked **BLOCKING FINDING** with a one-line reason.

Ticket: TICKET-XXXX-doc-partition.
Locked decisions this recon serves: A1 (changelog extraction), A1-guard
(current-version header line stays in schema.md), B1 (generated decisions
index + verify check). See the ticket for wording.

Runtime note: read-only task; no venv or PYTHONPATH needed. Large-file
warning: `tooling/standards/ARCHITECTURE_DECISIONS.md` is ~210 KB — never
read it wholesale; use grep and targeted line ranges only.

---

## Zone A — CHANGELOG boundaries in `world-engine-schema.md`

A1. Report the exact line range of the `CHANGELOG` section: first line of
    its header, last line of its last entry, and whether anything (footer,
    signature line, trailing sections) exists after it. Cite `file:line`
    for each boundary.

A2. Report the current version number as stated by the newest changelog
    entry, and every other place inside `world-engine-schema.md` where a
    version number is asserted (header, intro line, footer such as
    "*Version X.YY — …*"). Cite each. This tells us what the single
    `Current schema version: vX.YY` header line replaces.

A3. Inline duplication check: search the `TABLES` / `INDEXES` / `RELATIONS`
    / `MIGRATION` sections for version references (`v1.`, `schema v`,
    `BRIEF-`) embedded in table notes. Report each occurrence with
    `file:line` and one line of context. Classification question the brief
    will need answered: are these *pointers* (safe to keep after the split)
    or *facts stated only there* (must not be lost)? Report; do not decide.

## Zone B — Decision-record header pattern in `tooling/standards/ARCHITECTURE_DECISIONS.md`

B1. Report the total count of `## ` headers and the count matching the
    expected pattern `## TITLE … (BRIEF-NN[, schema vX.YY | no schema change])`.
    List every header that does NOT match the pattern (verbatim, with
    `file:line`) — these are the exceptions the B1 index generator must
    handle. **BLOCKING FINDING** if more than ~20% of headers are
    pattern-exceptions (the generator design would change).

B2. Report whether any content lines inside records begin with `## `
    (false-positive headers, e.g. inside fenced code blocks). Cite any found.

B3. Report whether headers are unique (any duplicate titles?). Duplicates
    affect anchor generation for the index.

## Zone C — Stale references inventory (feeds the separate sweep ticket)

C1. Repo-wide inventory of references to `ARCHITECTURE_DECISIONS.md`:
    every occurrence in README, CLAUDE.md, `world-engine-schema.md`,
    `.claude/` (commands, skills, settings, hooks), `tooling/`, and code
    comments under `src/`. For each: `file:line`, and whether the path it
    implies is the OLD location (repo root) or the NEW one
    (`tooling/standards/`). Report only.

C2. Same inventory for references to the schema changelog (phrases like
    "schema changelog", "changelog entry", "world-engine-schema.md
    changelog") — these become stale after the A1 split and feed the sweep.

## Zone D — Where Claude Code learns the current schema version today

D1. Report every instruction in CLAUDE.md, `.claude/commands/*`, and
    `.claude/skills/*` that tells Claude Code where to find or how to bump
    the schema version. Verbatim quotes with `file:line`. This is where the
    A1-guard rewording must land so Claude Code reads the header line and
    never searches elsewhere. **BLOCKING FINDING** if version-bump logic is
    encoded anywhere outside these instruction files (e.g. in a hook or
    script).

## Zone E — Verify harness seam for the B1 index check

E1. Report the current structure of `tooling/verify/` (`run.py`, `checks/`):
    how a check is declared, what a check receives, and where a new
    deterministic check (`decisions_index` ≡ archive headers) would plug in.
    `file:line` for the registration point. Report only — do not write the
    check.

## Zone F — Decision F2 retrieval (input for pending decision H)

F1. Locate the decision record in `tooling/standards/ARCHITECTURE_DECISIONS.md`
    that locked **F2 — no auto-backup before destructive operations**
    (context: world block-deletion work; sibling decisions A1 hard delete,
    B2′ "Oui" confirmation modal, G1 re-activation). Quote the record's
    reasoning **verbatim** (the full paragraph(s) justifying F2), with
    `file:line`. If no such record exists, say so explicitly —
    **BLOCKING FINDING** for decision H, which is gated on this reasoning.

---

## Output format

One report, sections mirroring Zones A–F, every claim carrying `file:line`.
End with a `BLOCKING FINDINGS` recap (or "none"). No recommendations, no
fixes, no design.
