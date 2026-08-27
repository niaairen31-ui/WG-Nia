---
id: TICKET-0070
title: CLAUDE.md symbol-location rule — pointer freshness that checks where a symbol lives
type: feature
status: paused
created: 2026-08-20
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: small
brief_ids: []
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> F explique moi la différence entre F1 et F2 si les check existent déja,
> pourquoi ne pas les utilisés.

> F1 + ticket 0070 en pause

## The gap this closes

`claude_md_contract.py` exists (TICKET-0010) and is green. It was green
throughout the drift TICKET-0061 repaired. It never claimed to guard this
class of statement, and that is the whole point: it proves pointer
existence, not pointer truth — the "proves X, not Y" pattern again.

Measured on `main` at 2026-08-20, its rule 4 reads:

> every `tooling/...` path mentioned anywhere in CLAUDE.md exists on disk

Two restrictions, both fatal to the drift that occurred:

| Restriction | Consequence |
|---|---|
| Domain is `tooling/...` only | `index.html`, `frontend/src/...`, `src/world_engine/...` tokens are invisible to it |
| Semantics is path EXISTENCE | It says nothing about where a symbol lives |

Applied to the two false lines TICKET-0061 repaired:

- `CLAUDE.md:55` claimed `_buildRuntimeCreationTabs()` lived in
  `index.html`. Not a `tooling/` path, so ignored — and even with the domain
  widened, the file existed, so still green. What was false was the
  location: 1 textual occurrence (a comment), implementation in
  `frontend/src/creation/tabs.js`.
- `CLAUDE.md:58` claimed `batchRenderAll` was an `index.html` global.
  `grep -c` returned **0**.

## Scope (sketch — not a specification)

A rule 5 on `claude_md_contract.py`: for every `` `symbol` (`path`) ``
claim in CLAUDE.md, assert that `symbol` occurs in `path`.

**Its real cost, measured.** A prototype regex found **8 candidate pairs**
in CLAUDE.md, of which **3 resolved and 5 were false positives** — the
parser confused path/path couples such as `` `tooling/glue`
(`tooling/glue/next_id.py`) `` with symbol/file couples. Roughly 40 % noise
on a first pass. Reparable (require the symbol to be an identifier with no
`/`; require the path to carry a code extension) but it is a parser with
its own false-positive surface, over a file whose line 278 is 5 180
characters and line 58 is 3 438.

Design constraints to settle at intake:

- The pair grammar, and whether CLAUDE.md's prose should be constrained to
  a declared citation form rather than the parser guessing.
- Vacuous-proof shape: zero pairs collected must be a FAILURE, not a pass.
- Interaction with the file's own line budget: a stricter citation form may
  cost lines the file does not have.

## Sequencing

**Best executed AFTER TICKET-0071** (the CLAUDE.md hygiene pass). The
hygiene pass reduces the number of symbol/path claims and may impose a
citation form, which is precisely the input that shrinks this parser's
surface. Running this ticket first would build a parser against prose that
0071 then rewrites.

The counter-argument, worth weighing at intake and not pre-settled here:
landing this rule first would catch drift *introduced by* 0071.

## Reactivation condition

TICKET-0071 reaches `done`, or Nia opens this ticket explicitly.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] To be authored at intake.

### Live  ->  human gate (Nia)

- [ ] To be authored at intake.
