# TICKET-XXXX — Documentation partition: schema changelog extraction + decisions index

status: draft
brief_ids: [BRIEF-0001-a, BRIEF-0001-b]
schema_version_touched: none

## Request

Reduce read amplification on the two heaviest documentation files without
destroying or summarizing any history. The current truth (hot) and the
append-only history (cold) live in the same files, so every reader who needs
5% of a document pays 100% of it.

## Locked decisions (intake, chat session)

- **A1** — Extract the `CHANGELOG` section of `world-engine-schema.md` into a
  new `world-engine-schema-changelog.md`. The schema file keeps
  `TABLES / INDEXES / RELATIONS / MIGRATION` plus a canonical header line
  `Current schema version: vX.YY` and a one-line pointer to the changelog file.
- **A1-guard** — The guardrail "Claude Code owns vX.YY in `schema.md`, single
  source" is amended, explicitly: the **current version number** stays a
  header line in `world-engine-schema.md` (still the single source for "what
  version are we at"); the **append-only log** moves to the changelog file
  (Claude Code appends there). The wording in CLAUDE.md must be explicit
  enough that Claude Code never searches anywhere else for the current
  version number.
- **B1** — Add a mechanically generated `DECISIONS_INDEX.md`: one line per
  decision record (title, BRIEF-NN, schema vX.YY, anchor/line). The archive
  `ARCHITECTURE_DECISIONS.md` stays byte-for-byte intact. The index is a build
  artifact extracted from the existing `## …` record headers, and becomes a
  deterministic verify check (index ≡ headers) so it can never drift.
- **B3 scoped out** — no hand-curated `DOCTRINES.md` distillation this pass.

## Pipeline path

1. RECON-XXXX (report-only) — see companion spec.
2. Briefs (numbers assigned by Nia after RECON analysis; expected split:
   one brief for the A1 changelog extraction + guard rewording, one brief
   for the B1 index generator + verify check).
3. Execution + deterministic verify per brief.
4. Live gate: Nia confirms Claude Code resolves the current schema version
   from the header line only.

## Scope OUT (ticket level)

- The stale-references sweep (README / schema / comments pointing at old
  `ARCHITECTURE_DECISIONS.md` location or at the pre-split changelog) is a
  **separate ticket**; this RECON only produces its inventory.
- Decision **H** (pre-db-backup hook) is not decided by this ticket; this
  RECON only retrieves the F2 reasoning needed to decide it.
- No compression, summarization, or rewriting of any history — in either file.

## Done means (ticket level)

- `world-engine-schema.md` contains no CHANGELOG section, carries the
  canonical `Current schema version:` header line, and every historical
  changelog entry exists verbatim in `world-engine-schema-changelog.md`.
- `DECISIONS_INDEX.md` exists, is generated (not hand-written), and a verify
  check proves index ≡ archive headers.
- CLAUDE.md governance wording updated per A1-guard.
- Live gate passed.

### Machine-checkable

- [ ] hot/cold partition holds  -> verify/checks/schema_partition.py
