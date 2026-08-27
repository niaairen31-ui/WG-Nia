# BRIEF — TICKET-0071 step a: "law only — reclassify, delegate, reflow"

## Context

CLAUDE.md is 499 lines / 47 084 characters and passes
`claude_md_contract.py` with one line of margin. Reflowed at 80 columns it
would be 750 lines — the line budget has been defeated by line length, not
by discipline. This step brings the file to law-only content and to a
100-character line ceiling **while the outgoing 500-line budget is still
enforced**; step b then replaces the budget. Ordered this way, no commit
leaves the gate red.

Three commits, in this order. Each is separately green.

## Mini-RECON — run first, STOP on any mismatch

Fetch `main` and verify these anchors before editing. They were measured
on 2026-08-21; if any has drifted, STOP and report rather than adapt.

1. `CLAUDE.md` is 499 lines / 47 084 characters, and
   `python tooling/verify/checks/claude_md_contract.py` prints PASS.
2. `tooling/verify/run.py` line 28 reads
   `ap.add_argument("--ticket", required=True)`, and
   `tooling/verify/checks/corpus_gate.py` exists.
3. The four frontend bullets open at CLAUDE.md lines 52, 58, 59, 60 inside
   `## Working rules`.
4. The eight delegation sources open at the lines given in the table under
   Scope IN item 3, and each named primary check exists under
   `tooling/verify/checks/`.
5. `module_budget.py` covers `src/**` and `frontend/src/**` only — it does
   NOT cover `tooling/verify/checks/`. If it has grown a `tooling/` rule,
   STOP: growing a check docstring by ~8 000 characters would then trip a
   budget, and the delegation target must be re-decided.

If a delegation target's docstring **already states the law** being moved,
do not duplicate it: shorten CLAUDE.md and leave the docstring alone.
`graph_primitive.py` (5 368-character docstring) is the likeliest case.

## Scope IN

### Commit 1 — `docs: correct the verify invocation claim`

1. In `### How to run / test`, replace the final bullet (CLAUDE.md:498)
   with exactly this text, wrapped as shown:

```
- **Verify:** `python tooling/verify/run.py --ticket TICKET-NNNN` runs the
  checks that ticket links in its Machine-checkable section;
  `tooling/verify/checks/corpus_gate.py` runs every check in the directory,
  regardless of which ticket references it.
```

   Nothing else changes in this commit. Anything else found wrong in
   `### How to run / test` is REPORT ONLY.

### Commit 2 — `docs: CLAUDE.md law-only pass`

2. **Reclassify.** Move the four bullets at CLAUDE.md:52, :58, :59, :60
   out of `## Working rules` and append them to the end of the bullet list
   in `## Invariants (verified at every review)`, text unchanged at this
   point (item 3 shortens them). `## Working rules` keeps its nine
   remaining bullets in their current order and is otherwise untouched.

3. **Delegate.** For each row below: move the mechanism, the enumeration
   and the rationale into the **primary check's module docstring**, and
   leave in CLAUDE.md a single bullet of **at most 180 characters** that
   states the obligation in the imperative and names the check.

| Source (current line) | Chars | Primary check (docstring target) |
|---|---|---|
| `CREATION_TABS` registry entry (L52) | 970 | `page_contract.py` |
| The review tree (L58) | 3 230 | `review_component.py` |
| The graph primitive (L59) | 909 | `graph_primitive.py` |
| Svelte effect hygiene (L60) | 523 | `effect_self_write.py` |
| Two sanctioned canon-write paths (L159) | 2 388 | `single_canon_write.py` |
| Hard deletes are a closed, named list (L270) | 5 787 | `single_canon_write.py` |
| `prompt_template.model` write path (L304) | 534 | `prompt_model_write.py` |
| Prompt text lives only in `prompt_version` (L316) | 841 | `prompt_version.py` |

   Rules for this move, no exceptions:

   - The **primary check is the first check named in the bullet, reading
     left to right**. It is given in the table; do not re-derive it.
   - `single_canon_write.py` receives two blocks (L159 and L270). Both go
     into its docstring as two clearly separated sections, L159's first.
   - Other checks named in a bullet are not edited. They remain named in
     the surviving CLAUDE.md sentence where they were named before, if the
     sentence still needs them.
   - Docstring voice follows the existing corpus: see
     `claude_md_contract.py`'s docstring, which states its rules as a
     numbered list under a one-paragraph statement of purpose.
   - Nothing is deleted. Every sentence removed from CLAUDE.md exists,
     verbatim or reworded without loss, in the target docstring.
   - The bullet at L300 (224 chars, `prompt_registry.py`) and the 28
     invariants that name no check are NOT touched.

4. **Strip identifiers.** Remove every `TICKET-\d+` and `BRIEF-\d`
   reference inside `## Invariants`, including `BRIEF-0045-d` at L163 and
   the 13 `TICKET-NNNN` references. Where a reference carries meaning,
   that meaning moves to the check docstring or to
   `tooling/standards/ARCHITECTURE_DECISIONS.md` — it does not survive as
   a bare number in the law. References outside `## Invariants` are NOT
   touched; `## Numbering & decisions governance` states the identifier
   format normatively and must keep it.

5. **Reflow.** No line in CLAUDE.md exceeds 100 characters, fenced blocks
   included. In `### File structure`, **shorten the trailing `#` comments;
   do not wrap them onto new lines** — the section has an 80-line cap and
   currently sits at 68. The longest tree line today is L402 at 350
   characters.

6. **Landing, and its STOP.** After items 2-5, measure. Required:
   **<= 34 000 characters and <= 495 lines.** If either is exceeded, take
   the reserve below; if it is still exceeded after the reserve, STOP and
   report rather than cutting further by judgment.

   **Reserve (only if item 6 requires it).** Reduce `## Local model notes`
   to the default-model sentence plus a pointer, and move the per-call-site
   thinking policies to a new `tooling/standards/local_model_notes.md`.
   The `## Local model notes` heading itself stays — `EXPECTED_H2` is an
   exact ordered list and removing the heading turns the gate red.

## Scope OUT

Named explicitly because each is a live temptation:

- **The 28 invariants that name no check.** Their text is the only guard
  that exists. Shortening them removes a guarantee and has no delegation
  target. Do not touch them, even the long ones.
- **The H2 / H3 whitelist.** No section is added, removed, renamed or
  reordered. A section may be emptied to a pointer; its heading stays.
- **`claude_md_contract.py` itself.** The budget change is step b. This
  step must leave the check byte-identical, so that the file's compliance
  with the *outgoing* rules is what proves the pass landed.
- **`### File structure` content.** Comments get shorter. The tree does
  not get restructured, re-ordered, or re-generated.
- **The per-ticket gate gap.** 53 of 84 checks are named by no ticket and
  therefore run only under `corpus_gate.py`. Real, out of scope, REPORT
  ONLY.
- **TICKET-0070's symbol-location rule.** Do not validate that
  `` `symbol` (`path`) `` claims resolve. That is a different ticket, and
  it does not exist yet.
- **`ARCHITECTURE_DECISIONS.md` and the schema changelog**, except where
  item 4 relocates the meaning of a stripped identifier.

## Invariants to defend

- **"No structure without a reader."** The delegation is only sound if the
  reader follows the pointer. Every surviving bullet must name its check,
  and step b makes that pointer machine-verified. A bullet that delegates
  without naming where the law went is the failure mode of this step.
- **"Structural over disciplinary."** Do not shorten a bullet whose only
  enforcement is the sentence itself. That is the whole reason the 28
  unchecked invariants are out of scope.
- **History is sacred** applies to documents here: text moves, it does not
  evaporate. The diff must show every removed sentence arriving somewhere.
- **The gate never goes red between commits.** Commit 2 must satisfy the
  *current* `claude_md_contract.py` — 500 lines, 80-line File structure,
  archaeology-free structure section, live `tooling/` pointers.

## Done means

- [ ] `python tooling/verify/checks/claude_md_contract.py` prints PASS after commit 1, and again after commit 2.
- [ ] `python tooling/verify/checks/corpus_gate.py` is green after commit 2.
- [ ] `wc -c CLAUDE.md` <= 34 000 and `wc -l CLAUDE.md` <= 495.
- [ ] `awk 'length($0)>100' CLAUDE.md | wc -l` returns 0.
- [ ] `grep -nE 'TICKET-[0-9]|BRIEF-[0-9]' CLAUDE.md` returns no match between the `## Invariants` heading and the next H2.
- [ ] `## Working rules` contains exactly nine bullets and no `frontend/src/` path.
- [ ] The eight primary checks in the table each carry the delegated law in their module docstring; `python -c "import ast; ..."` or direct reading shows a docstring longer than before for each one that received text.
- [ ] `git log --oneline -3` shows the three commits in the stated order, and commit 1 touches only CLAUDE.md's final bullet.
- [ ] `/review-step` and `/close-step` are NOT required: no engine code is touched. Confirm no file under `src/` changed.

## Docs to update

- `CLAUDE.md` — this brief IS the update.
- The eight check docstrings — same.
- `tooling/standards/local_model_notes.md` — only if the reserve is taken.
- No schema changelog entry: no schema change.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` — one entry, appended at
  close of step b, not here: the decision recorded is the budget change,
  which is step b's subject.
