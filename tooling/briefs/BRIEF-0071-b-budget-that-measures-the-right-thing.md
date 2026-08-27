# BRIEF — TICKET-0071 step b: "a budget that measures the right thing"

## Context

Step a brought CLAUDE.md to law-only content and to a 100-character line
ceiling. Nothing yet enforces either. `claude_md_contract.py` still counts
lines — the quantity a 5 202-character line defeats — so the next merge
that appends to a long bullet undoes step a silently. This step replaces
the measure and adds the pointer rule that makes step a's delegation
fail-closed.

Runs only after step a has landed. Its whole design assumes the file is
already compliant, so the check goes green on the commit that tightens it
and no window of red exists.

## Mini-RECON — run first, STOP on any mismatch

1. `wc -c CLAUDE.md` <= 34 000 and `awk 'length($0)>100' CLAUDE.md | wc -l`
   returns 0. If not, step a did not land; STOP.
2. `claude_md_contract.py` still declares `TOTAL_LINE_BUDGET = 500` and
   `FILE_STRUCTURE_LINE_BUDGET = 80`, and its four rules are as documented
   in its module docstring.
3. Every bare `<name>.py` token in CLAUDE.md resolves to a file somewhere
   in the repo. Measured 2026-08-21: 76 distinct tokens, 0 unresolved. If
   any is unresolved, do NOT fix CLAUDE.md silently — report the token and
   STOP, because an unresolved pointer after step a means law went
   somewhere that does not exist.

## Scope IN

Single commit: `feat(verify): CLAUDE.md budget measures characters, not lines`.

1. **Replace the budget constants** in
   `tooling/verify/checks/claude_md_contract.py`:

   - Delete `TOTAL_LINE_BUDGET`.
   - Add `TOTAL_CHAR_BUDGET = 38_000` — the whole file, `len(text)`.
   - Add `MAX_LINE_LENGTH = 100` — every line, fenced blocks included, no
     exemption.
   - Keep `FILE_STRUCTURE_LINE_BUDGET = 80` unchanged: that section's
     failure mode is depth of tree, which lines do measure correctly.

   `check_budgets` reports the character overrun with the actual count,
   and reports **every** offending line individually as
   `line N is C characters, over the 100-character ceiling`, not just the
   first — a single-failure report invites one-at-a-time whack-a-mole.

2. **Widen the archaeology ban to `## Invariants`.** A second banned set,
   `re.compile(r"TICKET-\d")` and `re.compile(r"BRIEF-\d")`, applied to
   the span from the `## Invariants (verified at every review)` heading to
   the next H2. The existing three patterns keep applying to
   `### File structure` only, unchanged: `## Numbering & decisions
   governance` states the identifier format normatively and must stay
   legal.

   **Vacuous-proof guard:** if the `## Invariants` span collects zero
   lines beginning with `- `, that is a FAILURE, not a pass. An emptied
   invariants block must never report green.

3. **Add rule 5 — bare pointer resolution.** Rule 4 covers `tooling/...`
   paths. It does not see `single_canon_write.py` written bare, which is
   how step a's delegation pointers are written. Add: every token matching
   `\b[a-z0-9_]+\.py\b` anywhere in CLAUDE.md must resolve to at least one
   file in the repository, searched by filename under the repo root,
   excluding `.venv/` and `node_modules/`.

   - A token resolving to more than one path passes (e.g.
     `prompt_registry.py` exists under both `src/world_engine/` and
     `tooling/verify/checks/`). This rule asserts existence, not identity.
   - **Vacuous-proof guard:** zero tokens collected is a FAILURE. Step a
     guarantees at least the eight delegation pointers; a file with none
     means the delegation was undone.

4. **Update the module docstring** to describe five rules instead of four,
   in the same numbered form it already uses. State in it, verbatim:

```
   The budget is a character budget on purpose. A line budget measures a
   quantity that line length defeats: at 499 lines this file held 47 084
   characters, three of its lines exceeding 1 000 each, and reflowed at 80
   columns it would have run 750 lines.
```

5. **Update `CLAUDE.md`'s own description of the check** at L49-51 (the
   `Step closure` bullet in `## Working rules`) so it names the budgets it
   now enforces. This is the one CLAUDE.md edit in this step; the edit
   itself must respect the 100-character ceiling.

## Scope OUT

- **Any further content reduction of CLAUDE.md.** Step a set the content;
  this step only measures it. If the file is at 33 900 characters and the
  cap is 38 000, that headroom is the point — do not "use" it and do not
  tighten the cap to fit.
- **`FILE_STRUCTURE_LINE_BUDGET`.** Not converted to characters, not
  retuned.
- **The H2 / H3 whitelist constants.** Untouched.
- **Applying the new ceiling to any other document.**
  `ARCHITECTURE_DECISIONS.md` is 736 KB and governed by nothing here; a
  general markdown line-length check is not this ticket.
- **TICKET-0070's symbol-location rule.** Rule 5 asserts that a `.py`
  token names a file that exists. It deliberately does NOT assert that a
  symbol lives at a claimed path. Do not extend it in that direction.
- **The per-ticket gate gap.** REPORT ONLY.

## Invariants to defend

- **Fail-closed over advisory.** Both new rules have an explicit
  zero-collection failure. A check that passes on an empty corpus is the
  exact defect this project treats as a bug, not an edge case.
- **Structural over disciplinary.** The reason the line budget is being
  removed rather than raised: a number that can be satisfied by rewrapping
  is discipline wearing a check's clothes.
- **Pointer freshness is what makes delegation safe.** Rule 5 is not an
  extra; it is the counterpart of step a. Without it, CLAUDE.md can name a
  check that no longer exists and the law it delegated becomes
  unreachable with the gate still green.

## Done means

- [ ] `python tooling/verify/checks/claude_md_contract.py` prints PASS, and its PASS line names five rules.
- [ ] `grep -n TOTAL_LINE_BUDGET tooling/verify/checks/claude_md_contract.py` returns no match.
- [ ] Negative test, character budget: append 5 000 characters of filler to a copy of CLAUDE.md, point the check at it, confirm FAIL naming the actual character count. Revert.
- [ ] Negative test, line ceiling: join two wrapped lines into one 140-character line, confirm FAIL naming that line number. Revert.
- [ ] Negative test, archaeology: insert `TICKET-0071` into an `## Invariants` bullet, confirm FAIL. Revert.
- [ ] Negative test, rule 5: change one delegation pointer to `no_such_check.py`, confirm FAIL naming the token. Revert.
- [ ] Negative test, vacuity: delete every `- ` bullet from `## Invariants` in a copy, confirm FAIL rather than PASS. Revert.
- [ ] `python tooling/verify/checks/corpus_gate.py` is green.
- [ ] `python tooling/verify/run.py --ticket TICKET-0071` is green.

## Docs to update

- `tooling/verify/checks/claude_md_contract.py` docstring — Scope IN item 4.
- `CLAUDE.md` L49-51 — Scope IN item 5.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` — one appended entry
  recording the decision and its reason: CLAUDE.md's budget is measured in
  characters and per-line length because a line budget is defeatable by
  rewrapping; long law lives in the docstring of the check that defends
  it; and the delegation is only safe because bare `.py` pointers are
  machine-resolved.
- No schema changelog entry: no schema change.
