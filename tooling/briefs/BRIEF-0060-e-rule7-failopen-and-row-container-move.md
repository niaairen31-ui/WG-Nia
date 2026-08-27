# BRIEF — Step "repair rule7's fail-open, and unstrand the Play knowledge rows"

## Context

`BRIEF-0060-c`'s execution surfaced two defects on `main`, both pre-existing,
both unrelated to Observation. Neither can be fixed inside `-c` without
breaking its Scope OUT, and `-c` cannot land green while they stand. This
brief clears the path; `-c` resumes after it merges.

**Defect 1 — `stylesheet_partition.py` rule7 is fail-open.**
`BASE_RULE_RE` (`stylesheet_partition.py:131-134`) ends with a self-compound
branch `(?:\.[\w-]+)*`, which accepts a Svelte-compiled scope hash as if it
were an ordinary compound class:

```
.spacer.svelte-13t3afu   ->   MATCH  ('.', 'spacer')
```

`_reachable_names()`'s own docstring asserts the opposite — that hashed output
"fails the strict base-rule match, so scoped component output never leaks into
this global set." The code contradicts its documentation. Measured
consequence on `main`: the built bundle contributes **11 class names** to
`REACHABLE`, **all 11** via hashed selectors, **0** legitimately. The bundle
term currently supplies nothing but noise, and every name it supplies
over-grants reachability — which is the fail-open direction.

In the merged rule7 half this only weakens a guard. Fed into the stranding
side of `-c`'s legacy half, the same mismatch produces false failures. The
defect belongs to TICKET-0064's deliverable, not to TICKET-0060, but `-c`
depends on it and a cross-ticket dependency would block this ticket on
external work. Decision **L1**: repaired here, provenance recorded.

**Defect 2 — Play's knowledge rows are unstranded nowhere.**
`index.html:1855-1856` (inside `loadPlayerKnowledge`, Play's "Mes savoirs"
sub-tab) applies `row-table` and `row-card` from a JS template literal. Both
are styled only at `creation.css:286-295`, which the legacy document does not
link — `stylesheet_partition.py` rule5 ties that link's lifetime to
`LEGACY_MOUNTS.creation`, retired by TICKET-0059. **Live on `main`: Play's
knowledge rows render with no card background, no border, no padding.** The
same mirror-image loss that hit Observation's `.r-err` / `.r-warn`, on a
surface nobody was looking at.

Measured, the complete legacy stranded set on `main` is exactly:

```
classes -> ['r-err', 'r-warn', 'row-card', 'row-table']
ids     -> []
```

`r-err` and `r-warn` leave with Observation in `BRIEF-0060-b` (decision D1).
This brief clears the residue. Eight further classes applied by `index.html`
are styled nowhere at all and are correctly **not** in that set — the
intersection term in `-c`'s formula does its job.

Locked decisions: **J1** (own brief, before `-c`), **K1** (`.row-table` and
`.row-card` move to `shared.css`; `.row-card-actions` does not), **L1**
(in-ticket, provenance to TICKET-0064 recorded).

## Mini-RECON — verify before writing

Report `file:line` or a count for each. **If any anchor does not resolve as
described, STOP and escalate — do not adapt.**

1. `tooling/verify/checks/stylesheet_partition.py` — report the exact source
   of `BASE_RULE_RE` and confirm its final branch is `(?:\.[\w-]+)`. Report
   the line range of `_base_rule_names` and of `_reachable_names`, and quote
   the docstring sentence claiming hashed output fails the base-rule match.
2. Confirm `_base_rule_names` is called from exactly three places
   (`_reachable_names`, `_scoped_names_for_file`, and the rule1/rule2 path) —
   report each call site. The regex change affects all of them.
3. Measure and report, before any change: how many class names and id names
   the built bundle (`src/world_engine/cockpit/static/assets/*.css`)
   contributes to `_reachable_names()`, and how many of those come **only**
   from a selector carrying a `.svelte-` suffix.
4. Confirm `stylesheet_partition.py` currently exits 0 and report its PASS
   line verbatim.
5. `frontend/public/creation.css` — confirm `.row-table` (one line) and
   `.row-card` (a multi-line block) are declared once each, and that
   `.row-card-actions` follows them. Report the exact line range of all
   three. Confirm **no other selector anywhere names `row-card` or
   `row-table`** — no contextual variant, no `.row-card.something`.
6. `frontend/public/shared.css` — report the section banner list and the file
   length. Confirm the header comment explains the copied-unhashed-by-Vite
   arrangement.
7. Confirm `row-card` / `row-table` are applied by `src/world_engine/cockpit/index.html`
   and report every line. Confirm `row-card-actions` is applied **only** under
   `frontend/src` and never by the legacy document.
8. Report how `frontend/public/*.css` reaches
   `src/world_engine/cockpit/static/` — whether a Vite build, a copy step, or
   both — and which check asserts the copies are byte-fresh.

## Scope IN

Two commits.

### Commit 1 — `BASE_RULE_RE` refuses a scope hash (J1)

Only `tooling/verify/checks/stylesheet_partition.py` changes.

The final branch of `BASE_RULE_RE` gains a negative lookahead so a
`.svelte-…` suffix can never be read as a compound class:

```python
    r"(?:(?::[\w-]+(?:\([^)]*\))?)|(?:::[\w-]+)|(?:\.(?!svelte-)[\w-]+))*$"
```

Add this comment immediately above the constant, verbatim:

```python
# TICKET-0060 (BRIEF-0060-e, J1). The self-compound branch used to accept
# a Svelte scope hash: `.spacer.svelte-13t3afu` matched and yielded
# `spacer`, so every component-scoped rule leaked into the GLOBAL
# reachable set that _reachable_names() builds. That function's docstring
# already asserted the opposite -- the code contradicted its own
# documentation, and the direction of the error was fail-open: names were
# granted reachability they never had. Measured on main before this fix,
# the built bundle contributed 11 class names to REACHABLE, all 11 via a
# hashed selector and none legitimately, so the bundle term supplied
# nothing but over-grants. The lookahead is deliberately narrow: it
# refuses Svelte's scope suffix and nothing else. Whether a genuine
# compound like `.a.b` should grant a base rule for `a` at all is a
# separate question with unmeasured blast radius -- not reopened here.
# Defect originates in TICKET-0064's rule7; repaired here because
# BRIEF-0060-c cannot land while it stands.
```

Non-hash compounds keep their current behaviour: `.a.b` still yields `a`.
Pseudo-classes and pseudo-elements are untouched.

`_reachable_names()`'s docstring becomes true as written — leave its wording
alone rather than rewriting a sentence that is now accurate.

**Red tests.** Perform, capture the transcript, revert. Nothing is committed.

- Regex behaviour, before and after, on this exact set:
  `.spacer` → yields `spacer`; `.spacer:hover` → yields `spacer`;
  `.spacer.active` → yields `spacer`; `.spacer.svelte-13t3afu` → **no match
  after the fix, match before**; `.parent .spacer` → no match either way.
- Bundle contribution: re-run mini-RECON item 3's measurement after the fix
  and report the new counts. The class count must drop to **0**.
- Temporarily restore the old branch and confirm the count returns to the
  figure reported in item 3. This before/after pair is the proof that the
  change has teeth; a narrowing fix has no natural failing red test.
- `stylesheet_partition.py` must still exit 0 with its PASS line's five
  counts unchanged from mini-RECON item 4.

### Commit 2 — `.row-table` and `.row-card` move to `shared.css` (K1)

Move — do not copy. `stylesheet_partition.py` rule2 forbids a selector
appearing in more than one sheet, and that is the guarantee being preserved.

- Delete both rules from `frontend/public/creation.css`, keeping
  `.row-card-actions` exactly where it is.
- Add them to `frontend/public/shared.css` under a new section banner
  matching the file's existing style, placed after the **Queue panel**
  section and before **Badges** — row containers sit at the same structural
  level as the panel that holds them.
- Move the rule bodies byte-identically. Do not reformat, do not reorder
  declarations, do not substitute tokens.

Banner and comment in `shared.css`, verbatim:

```css
/* ── Row containers (TICKET-0060, BRIEF-0060-e) ──────────────────────────── */
/* Moved out of creation.css: cockpit/index.html applies both classes from
   loadPlayerKnowledge's template literal (Play's "Mes savoirs" tab), and
   that document does not link creation.css -- stylesheet_partition rule5
   ties the link's lifetime to LEGACY_MOUNTS.creation, retired by
   TICKET-0059. Play's knowledge rows had been rendering with no card
   background, border or padding ever since. Both documents read these two
   rules now, which is exactly what shared.css means. .row-card-actions
   stays in creation.css: it has no legacy consumer, and moving it would
   put a Creation-only rule in the shared layer. */
```

Leave this comment in `creation.css` where the two rules were, verbatim:

```css
/* TICKET-0060 (BRIEF-0060-e, K1): .row-table and .row-card moved to
   shared.css -- the legacy document applies both and cannot link this
   sheet. .row-card-actions stays: zero legacy consumers. */
```

Refresh whatever copies `frontend/public/*.css` into
`src/world_engine/cockpit/static/`, per mini-RECON item 8, and commit the
refreshed copies in this same commit so the freshness assertion holds at every
commit boundary.

### Docs (in commit 2)

`tooling/standards/ARCHITECTURE_DECISIONS.md`, appended to the TICKET-0060
section: the fail-open and its direction, the measured before/after bundle
figures, that the defect originates in TICKET-0064's rule7 and why it was
repaired in this ticket rather than its own, and the partition rule K1
applies — a rule belongs in `shared.css` when both documents read it, and
sibling rules do not travel with it merely for being adjacent.

`CHANGELOG.md`: fold into the existing TICKET-0060 entry. Name the
user-visible half — Play's knowledge rows regain their card styling.

## Scope OUT

1. **Do not implement `_scan_legacy_document`, `_reachable_names_legacy`, or
   `_check_rule7_legacy`.** That is `BRIEF-0060-c`, whose session resumes
   after this merges. This brief adds no rule and no new half.
2. **Do not touch `_scan_frontend_src`, `_reachable_names`,
   `_scoped_names_for_file`, `_stranded_names_by_kind` or `_check_rule7`**
   beyond what the regex change reaches through `_base_rule_names`. No
   refactor, no signature change, no extraction into a shared helper.
3. **Do not remove or generalise the self-compound branch.** `.a.b` must keep
   yielding `a`. The lookahead refuses Svelte's scope suffix and nothing
   else. Whether compounds should grant base rules at all is unmeasured and
   out of scope.
4. **Do not move `.row-card-actions`,** and do not move any other rule from
   `creation.css` to `shared.css` for tidiness. Two rules move because two
   rules are stranded.
5. **Do not fix the eight classes `index.html` applies that are styled
   nowhere.** They are not stranded — they are unstyled, which is a different
   thing and possibly intentional. REPORT ONLY if you enumerate them.
6. **Do not touch `src/world_engine/cockpit/index.html`.** Not the markup,
   not `loadPlayerKnowledge`, not the template literal. The CSS moves to the
   document; the document does not change.
7. **Do not touch anything `BRIEF-0060-b` owns** — no Observation code, no
   `LEGACY_MOUNTS`, no `.r-err` / `.r-warn`. If those two rules are still in
   `creation.css`, `-b` has not merged and this brief must not compensate:
   STOP and escalate.
8. **Do not build the corpus gate** or edit `tooling/verify/run.py`.
9. **Do not modify any other check**, even if the regex change makes one
   newly red. A newly red check is a REPORT ONLY finding and an escalation.

## Invariants to defend

- **Fail-closed over advisory.** The change moves a guard from over-granting
  to strict. Any adjustment that restores reachability to make something pass
  is the defect being re-introduced.
- **One definition of every rule.** The move is a move. A copy would put the
  same selector in two sheets, defeating rule2 and handing the outcome back to
  load order — the exact thing `shared.css`'s header comment says the
  partition exists to prevent.
- **Structural over disciplinary.** `shared.css` means *both documents read
  this*. Membership follows readership, not adjacency or convenience.
- **Minimal first.** One lookahead, two rules moved. No generalisation of
  compound semantics, no sweep of `creation.css`.
- **Docstrings are claims.** A function whose documentation contradicts its
  behaviour has already failed; the repair makes the existing sentence true
  rather than rewriting it to match a defect.

## Done means

- [ ] `WORLD_ENGINE_ENV=dev PYTHONPATH=src python tooling/verify/checks/stylesheet_partition.py`
      exits 0 at HEAD, and its PASS line's five counts are identical to the
      figures reported in mini-RECON item 4.
- [ ] The bundle contributes **0** class names to `_reachable_names()` after
      commit 1, against the figure reported in mini-RECON item 3.
- [ ] The before/after regex transcript is in the execution report, covering
      all five selector forms listed in commit 1, and shows
      `.spacer.svelte-13t3afu` matching before and not after.
- [ ] The old-branch restoration test is in the report and returns the
      original count, with the mutation reverted.
- [ ] `grep -n "row-card\|row-table" frontend/public/creation.css` returns
      only `.row-card-actions` and the left-behind comment.
- [ ] `grep -n "row-card\|row-table" frontend/public/shared.css` returns both
      moved rules under the new banner.
- [ ] The moved rule bodies are byte-identical to the originals — show the
      diff.
- [ ] The static copies under `src/world_engine/cockpit/static/` are
      refreshed in commit 2, and the freshness assertion passes at both
      commit boundaries.
- [ ] `git diff --stat` shows commit 1 touching one file and commit 2
      touching `shared.css`, `creation.css`, the refreshed static copies,
      `ARCHITECTURE_DECISIONS.md` and `CHANGELOG.md` — nothing else.
- [ ] `git status` is clean; no red-test mutation survives.
- [ ] Live: Play → "Mes savoirs" — the knowledge rows render as cards with
      background, border and padding.
- [ ] Live: Creation's row cards are unchanged. Check at least Prompts,
      Region and the Faction roster, since `shared.css` loads before
      `creation.css` and the move changes these rules' cascade position.

## Docs to update

Covered by commit 2: `ARCHITECTURE_DECISIONS.md` (the fail-open, its
direction, the measured figures, the TICKET-0064 provenance, and the K1
partition rule) and the existing TICKET-0060 `CHANGELOG.md` entry.

No CLAUDE.md change — no doctrine moves, and the file is under an enforced
line budget.

No schema change.
