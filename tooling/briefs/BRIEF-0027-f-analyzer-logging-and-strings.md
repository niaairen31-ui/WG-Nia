<!-- slug: analyzer-logging-and-strings -->
# BRIEF-0027-f — `analyzer.py` to logging; English strings; bug_log flip

Ticket: TICKET-0027 | Danger: none (observability + strings only) |
Blast radius: small | Depends on: BRIEF-0027-e merged; own branch
`ticket/0027-f`

## Context

R3: no `print()` in `src/`. Current `TRANSITION_ALLOW` in
`no_print_in_src.py`: `analyzer.py` -> 12 sites (down from 38 at RECON;
stages b/e absorbed the rest). S5: known French strings in `analyzer.py`
(e.g. "Analyse en cours..."). code_standards section 5: the stale
`bug_log.jsonl` status flips in the first brief touching that file —
this one.

## Scope IN

1. Replace the 12 `print()` sites in `analyzer.py` with module logging
   (`_log = logging.getLogger(__name__)` at module top, matching
   `app.py`/`gathering.py` style). Level mapping: progress -> `info`,
   recoverable anomalies -> `warning`, per-site judgment recorded in the
   execution notes. Message content preserved (translated where French),
   no new information added or dropped.
2. Translate every non-English string in `src/` to English — audit the
   whole tree, not just `analyzer.py`; list findings in execution notes.
   EXCLUSION: the canonical French interval labels ("quelques heures",
   etc.) are **data**, part of the closed interval vocabulary consumed by
   prompts and UI — they are not log strings and MUST NOT be translated.
   When in doubt whether a string is data or message: escalate, do not
   translate.
3. Empty `TRANSITION_ALLOW` in `no_print_in_src.py` (R3 exemption-free).
4. Flip `tooling/improvement/bug_log.jsonl` entry 2026-07-03 to
   `"status": "fixed"` with a note referencing BRIEF-0025-d / v1.78
   (append-style edit of the status field only; the record's history
   fields stay intact).

## Scope OUT

- Any behavior change in analysis logic; any change to what is analyzed.
- Log-capture infrastructure, handlers, formatters, or log-level config
  (module loggers inherit the existing root config).
- Prompt text (French interval labels reaffirmed untouched).

## Invariants to defend

- Interval-label vocabulary byte-identical (`effects_vocab.py` /
  related checks green).
- `no_print_in_src.py` green with an empty transition list; full suite
  green.
- Analyzer outputs unchanged: same proposals from same inputs (logging
  is side-channel only).

## Done means

### Machine-checkable
- [ ] `no_print_in_src.py` green, TRANSITION_ALLOW empty; zero `print`
      sites under `src/world_engine/`.
- [ ] `grep` audit for non-ASCII French message strings in `src/` comes
      back empty outside the documented data vocabularies.
- [ ] `harness_mutation_apply.py` replay PASS (analyzer feeds proposal
      generation upstream — cheap confidence, fixtures already exist).
- [ ] `bug_log.jsonl` parses as JSONL, entry status `fixed`, all other
      fields byte-identical.
- [ ] Full suite green.

### Live gate (Nia)
- [ ] One analyzed turn live: proposals appear as usual; analyzer
      progress visible in the server log (not stdout prints).

## Docs to update

- None.
