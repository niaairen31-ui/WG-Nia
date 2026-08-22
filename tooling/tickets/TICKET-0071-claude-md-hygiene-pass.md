---
id: TICKET-0071
title: CLAUDE.md hygiene pass — law only, delegated detail, and a budget that measures the right thing
type: feature
status: live-gate
created: 2026-08-20
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
brief_ids: [BRIEF-0071-a, BRIEF-0071-b]
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> le claude.md doit être revus (dans un prochain ticket. Je pense qu'il faut
> faire une passe d'hygiène dessus pour qu'il grade seulement les
> informations les plus pertinantes et réfère a d'autre documents au besoin
> ( ex : conventions de code )

## Why now — measured on `main`, 2026-08-21 [M]

`claude_md_contract.py` is GREEN today, with one line of budget left.

| Measure | Value |
|---|---|
| Size | 499 lines / 47 084 characters |
| Lines over 200 chars | 14 |
| Lines over 1 000 chars | 3 — L279 = 5 202, L58 = 3 234, L163 = 2 067 |
| Share carried by the 8 longest lines | 29 % (13 690 ch) |
| Reflowed at 80 columns | **750 lines — 150 % of the 500-line budget** |
| Reflowed at 100 columns | 682 lines |

The 20 August intake estimated ~575 reflowed lines. That was low by a
third. The budget is not merely soft; it is measuring a quantity the file
has already left behind by 50 %.

### Section weights [M]

| Lines | Chars | Section |
|---|---|---|
| 202 | 21 913 | `## Invariants (verified at every review)` — 47 % of the file |
| 68 | 6 079 | `### File structure` (cap 80 lines) |
| 52 | 3 177 | `## Ticket pipeline (governance)` |
| 40 | 2 230 | `## Local model notes` |
| 39 | 7 511 | `## Working rules` |
| 36 | 2 356 | `### How to run / test` |

### Three findings that shape the work [M]

1. **`## Working rules` is a dumping ground, not a fat section.** Four
   bullets deposited by the 0055 -> 0061 series — `CREATION_TABS` (L52),
   the review tree (L58), the graph primitive (L59), Svelte effect hygiene
   (L60) — carry 5 637 characters, **75 % of the section**. They are
   invariants filed in the wrong place. The nine genuine working rules
   total 1 856 characters and are all short. The first move is
   reclassification, not deletion.

2. **The check corpus supplies a mechanical partition.** 84 checks exist
   under `tooling/verify/checks/`; 31 are named in CLAUDE.md, 53 never
   are. Of the 41 invariant bullets, eight oversized ones (> 500 chars)
   name a check that exists on disk, and together they carry **15 182
   characters — 32 % of the file**. The precedent for delegation is not
   `code_standards.md`; it is the check docstring itself:
   `graph_primitive.py` already carries 5 368 characters of doctrine in
   its module docstring, and `claude_md_contract.py` states its four rules
   there in full while CLAUDE.md keeps one sentence (L49-51).

3. **One law in the file is false.** `CLAUDE.md:498` claims
   `python tooling/verify/run.py` runs every check. `run.py:28` declares
   `--ticket` as `required=True`: without a ticket the command exits on an
   argparse error, and with one it runs only the checks that ticket links.
   `corpus_gate.py` exists (10 482 chars) and is what actually executes
   the directory.

### Arithmetic of the pass [M/I]

Delegating the eight oversized check-backed invariants to their primary
check's docstring, leaving <= 180 characters each in CLAUDE.md, releases
**~13 740 characters** [I]. Landing: ~33 300 characters, ~485 lines
reflowed at 100 columns. Both the outgoing 500-line budget and the
incoming 38 000-character budget hold, at every commit, without touching
the 28 invariants no check defends.

## Decisions locked (intake, 2026-08-21)

- **A1 — budget shape.** A per-line character ceiling plus a whole-file
  character budget. `TOTAL_LINE_BUDGET` is removed: a line cap that
  permits an unbounded file measures nothing, and three numbers of which
  two disagree is worse than two that agree.
- **B1 — the ceiling applies everywhere**, fenced blocks included. No
  exemption, because an exemption is a 5 000-character hiding place. In
  `### File structure`, trailing comments are shortened, never wrapped —
  wrapping the tree would breach its 80-line cap.
- **C2 — 38 000 characters cap, 34 000 landing target.** 38 000 is the
  budget the 500-line cap always meant (500 x ~76). The 4 000-character
  gap is deliberate headroom: roughly ten future invariants before this
  ticket must reopen.
- **D1 — long law lives in the docstring of the check that defends it.**
  CLAUDE.md keeps the imperative and the check name. Accepted cost: a
  check says no after the fact, whereas the text guides before — so the
  imperative that stays must be sufficient to steer, and only the
  mechanism, enumeration and rationale move.
- **E1 — the H2 whitelist is untouched.** `EXPECTED_H2` and
  `EXPECTED_H3_UNDER_CONVENTIONS` are exact and ordered; a section may be
  emptied to a pointer but never removed or reordered, so no commit can
  land in which file and check disagree.
- **F1 — the false claim is fixed inside this ticket, in its own commit**,
  separate from the hygiene pass.
- **G1 — the archaeology ban widens to numbered identifiers inside
  `## Invariants` only** (`TICKET-\d`, `BRIEF-\d`). It does not widen
  file-wide: `## Numbering & decisions governance` states the identifier
  *format* normatively at L90, L118, L121 and L125, and a naive ban would
  outlaw the section that defines the convention.

## Scope

**IN.** Reclassification of the four misfiled frontend bullets;
delegation of the eight oversized check-backed invariants to their primary
check's docstring; removal of numbered identifiers from `## Invariants`; a
100-character reflow of the whole file; replacement of the line budget by
a character budget plus per-line ceiling in `claude_md_contract.py`; a new
pointer-resolution rule covering bare `<name>.py` tokens; correction of
the `run.py` claim.

**OUT.** The 28 invariants no check defends (their text is the only guard
that exists — shortening them removes a guarantee, and no delegation
target exists). The H2/H3 whitelist. `### File structure` content beyond
comment shortening. TICKET-0070's symbol-location rule. The per-ticket
gate gap (53 unnamed checks). `ARCHITECTURE_DECISIONS.md` and the schema
changelog.

## Sequencing

Independent of TICKET-0069 (`paused`). **TICKET-0070 does not exist in
`tooling/tickets/`** as of this fetch; the 20 August sequencing note
pointed at a ticket that was never deposited, and at a counter-argument in
a document that cannot be read. If 0070 is later opened, this pass
precedes it: it reduces and regularises exactly the `` `symbol` (`path`) ``
claims a symbol-location parser would have to handle.

Note for the record: 0055 -> 0061 and 0063 -> 0067 all sit at
`status: live-gate` on disk, not `done`. Nothing in this ticket depends on
that, but the pipeline reads status.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] CLAUDE.md is <= 38 000 characters  -> verify/checks/claude_md_contract.py
- [ ] No line in CLAUDE.md exceeds 100 characters, fenced blocks included  -> verify/checks/claude_md_contract.py
- [ ] `TOTAL_LINE_BUDGET` no longer exists in the check; its removal is asserted by the check's own PASS line naming the rules it ran  -> verify/checks/claude_md_contract.py
- [ ] Zero `TICKET-\d` / `BRIEF-\d` matches inside `## Invariants`; a `## Invariants` section that collects zero bullets is a FAILURE  -> verify/checks/claude_md_contract.py
- [ ] Every bare `<name>.py` token anywhere in CLAUDE.md resolves to a file on disk; zero tokens collected is a FAILURE  -> verify/checks/claude_md_contract.py
- [ ] `### File structure` is still <= 80 lines and archaeology-free  -> verify/checks/claude_md_contract.py
- [ ] The whole check corpus is green  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)

- [ ] CLAUDE.md read end to end: every remaining sentence in `## Invariants` states an obligation. No mechanism, enumeration or rationale survives there.
- [ ] For each of the eight delegated invariants, the primary check's docstring carries the full law — verified by opening the eight files. Nothing was deleted without a home.
- [ ] `python tooling/verify/run.py --ticket TICKET-0071` runs and the corrected `### How to run / test` line describes what the code actually does.
- [ ] `## Working rules` reads as working rules only.
- [ ] Landing size is <= 34 000 characters, leaving >= 4 000 of headroom under the cap.
