# BRIEF 0089-G — "The gathering lifecycle gate, and the doctrine it defends"

Lot: LOT-0089-manual-npc-move-gathering-desync.md (authoritative on conflict)
Depends on: BRIEF-0089-a, BRIEF-0089-c, BRIEF-0089-d (it asserts the shape all
three leave behind)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `src/world_engine/cockpit/routes/scene.py` declares `_live_gatherings`;
  `enter_scene` calls it and does not call `_open_gatherings`.
- `src/world_engine/gathering.py` declares `dissolve_emptied` and
  `attach_on_arrival`; `migrate_npc` calls `dissolve_emptied` and contains no
  `status = "dissolved"` assignment of its own.
- `src/world_engine/cockpit/crud/entities.py` -> `update_entity` calls
  `close_open_memberships`, `attach_on_arrival` and `dissolve_emptied`.
- `tooling/verify/checks/corpus_gate.py` discovers every `*.py` in its own
  directory except itself, runs each as a subprocess, and classifies a
  non-zero exit as ENVIRONMENT / CRASH / TIMEOUT / FAIL -- never a skip.
  `REQUIRED_TOOLS = ("fastapi", "httpx", "pyflakes", "sqlalchemy", "sqlmodel")`.
- `tooling/verify/checks/world_tick.py:470-497` collects call names with
  `{node.func.id for node in ast.walk(func) if isinstance(node, ast.Call) and
  isinstance(node.func, ast.Name)}` after locating the function by name, and
  fails on a missing call name.
- `CLAUDE.md` is at most 36 000 characters; no line exceeds 100 characters;
  its Invariants section contains zero `TICKET-\d` and zero `BRIEF-\d`
  matches; and it holds, verbatim, the clause beginning "**Creator-CRUD edits
  that change a character's `current_location_id`".
- `tooling/verify/checks/decisions_index.py` enforces
  `^## .+ \(BRIEF-\d{4}(-[a-z])?(, BRIEF-\d{4}(-[a-z])?)*, (schema v\d+\.\d+|no schema change)\)$`
  on headers added after the baseline, and requires
  `tooling/standards/DECISIONS_INDEX.md` to equal a fresh
  `python tooling/glue/gen_decisions_index.py`.
- `tooling/verify/checks/pipeline_state.py` fails any Machine-checkable arrow
  that does not resolve to an existing file under `tooling/verify/checks/`.

## Facts carried

**R-24 — what the new check must be.** `corpus_gate` discovers every `*.py`
in the checks directory except itself and runs each as a subprocess; a check
that cannot import is an ENVIRONMENT failure, never a skip;
`REQUIRED_TOOLS = ("fastapi", "httpx", "pyflakes", "sqlalchemy", "sqlmodel")`.
`world_tick.py`'s precedent for this exact class of assertion parses the
module with `ast`, finds the function by name, collects the called `Name` ids
and fails on a missing one. Consequence: the new check is stdlib-`ast` only,
imports no application module, and follows the `FAILURES`/`fail`/`main`
idiom of its siblings.

**R-22 — the CLAUDE.md clauses this lot touches, verbatim, and its budget.**
The per-NPC uniqueness clause, the dissolve-before-create clause and the
creator-CRUD clause, quoted in the lot header. Budgets: total file
<= 38 000 characters (34 752 at drafting), no line over 100 characters, and
the Invariants section must contain zero `TICKET-\d` or `BRIEF-\d` matches.

**R-23 — the decision registry's header contract.** The strict pattern above,
plus regeneration of `DECISIONS_INDEX.md`. The most recent entries follow
`## TITLE IN CAPS (BRIEF-0087-d, no schema change)`.

**R-21 — what the ticket artifact itself must satisfy.** Every Machine
arrow must resolve to an existing file; `LINK.search` takes the first arrow
per line only. Consequence: TICKET-0089 shipped without an arrow for this
check; the arrow is added by this commit, which is also the one that creates
the file.

**R-30 — `_get_or_open_session` creates a session when none is open.** The
check asserts `attach_on_arrival` never calls it.

## Contracts

**C-07 — `gathering_lifecycle.py`**
Produced by: BRIEF-0089-g   Consumed by: TICKET-0089 acceptance criteria
Declared in: `tooling/verify/checks/gathering_lifecycle.py`.
Contract: stdlib `ast` only, imports no application module,
`FAILURES`/`fail`/`main` idiom, vacuous-proof (an empty collection is a
FAILURE). Asserts, each failing independently:
1. `routes/scene.py` declares `_live_gatherings`, and `enter_scene`'s body
   calls it and does not call `_open_gatherings`.
2. `_live_gatherings`'s own body calls `_active_members`, so the roster
   predicate is not re-expressed.
3. `gathering.py` declares `dissolve_emptied` and `attach_on_arrival`.
4. `migrate_npc` calls `dissolve_emptied` and contains no
   `status = "dissolved"` assignment of its own.
5. `crud/entities.py`'s `update_entity` calls `close_open_memberships`,
   `dissolve_emptied` and `attach_on_arrival`.
6. `attach_on_arrival`'s body does not call `_get_or_open_session`.
PASS line names the counts it collected.

## Context

Briefs A, C and D put three verbs in place: the entry guard that ignores
shells, the dissolve that stops them forming, and the arrival that makes a
manual move take effect immediately. Each of the three is one call that a
later refactor could quietly drop, and none of them is visible in any
existing gate. This brief makes the arrangement structural, records the
doctrine behind it, and closes the ticket's machine-checkable section.

## Scope IN

1. Create `tooling/verify/checks/gathering_lifecycle.py` implementing `C-07`.
   Model its structure on `world_tick.py`: module-level `ROOT`, `SRC`, the
   three target paths, a `FAILURES` list, `fail`, a `_parse` helper, a
   `_find_function` helper, per-rule functions, and a `main` that prints one
   `PASS:` line or the accumulated `FAIL:` lines and exits 1.
2. Make each rule vacuous-proof: a target file that does not parse, a
   function that is not found, and a rule that collected zero call names are
   each a FAILURE with a message naming the file and the symbol -- never a
   silent pass.
3. Write the module docstring in the house shape: what it guards, why the
   guard exists (an open gathering with no active member froze a location for
   a whole session and no gate saw it), and one sentence per rule.
4. Add one line to TICKET-0089's `### Machine-checkable` section, with
   exactly one arrow:
   `- [ ] The entry guard, the dissolve and the arrival are all wired  -> verify/checks/gathering_lifecycle.py`
5. In `CLAUDE.md`, extend the creator-CRUD clause with the two new
   obligations -- attach at the destination when the location already holds
   an open gathering in the open session, and call `dissolve_emptied` after
   the commit -- and add one clause stating that an open gathering with no
   active member is a defect state: dissolved where it is emptied, ignored by
   the entry guard, so that a location counts as "already entered" only while
   one of its open gatherings still holds an active member. No ticket or
   brief id anywhere in that section; no line over 100 characters.
6. Append one entry to `tooling/standards/ARCHITECTURE_DECISIONS.md` in the
   strict header shape
   `## AN EMPTY OPEN GATHERING IS A DEFECT STATE, NOT A LEGAL ONE (BRIEF-0089-a, BRIEF-0089-c, BRIEF-0089-d, no schema change)`.
   Record: presence is gathering-derived and stays that way; the shell state
   and how it froze a location; why the fix is placed at both ends; why an
   arrival is always solo; why `dissolve_emptied` runs after its caller's
   commit rather than inside `close_open_memberships`; and the rejected
   alternative -- filtering empty gatherings inside `_open_gatherings` --
   with its reactivation condition, a third reader needing to ignore one.
7. Regenerate `tooling/standards/DECISIONS_INDEX.md` with
   `python tooling/glue/gen_decisions_index.py` in this same commit.

## Scope OUT

- Asserting anything about runtime data. This check reads source with `ast`;
  it never opens a database, and "no empty open gathering exists" is not a
  property it can or should assert.
- Importing any application module. `corpus_gate` runs every check in a
  subprocess and an import failure is an ENVIRONMENT failure for the whole
  corpus -- see the `day_mutations.py` precedent.
- Teaching the check to tolerate exceptions. If a legitimate future caller
  must dissolve differently, it gets its own module rather than an exemption
  branch here.
- Repairing `json_ui_boundary.py`'s absent end markers, `run.py`'s
  one-arrow-per-line parser, or `enter_location`'s failure to close member
  rows on dissolve. All three are recorded in the ticket's carried-forward
  section.
- The six NPCs with a NULL `current_location_id`. D1: no check, no repair.
- Every other brief in this lot: A, B, C, D, E, F.

## Invariants to defend

- **Fail-closed over advisory; checks must be vacuous-proof.** Zero items
  collected is a FAILURE. A rule that cannot find its function must say so
  and fail, not pass quietly.
- **A check's rule comes from its implementation, never its docstring.**
  Write the docstring after the rules, and make it describe what the code
  actually asserts.
- **Every ticket's Machine-checkable section links
  `verify/checks/corpus_gate.py`.** TICKET-0089 already does; do not disturb
  that line while adding yours.
- **History is sacred.** `ARCHITECTURE_DECISIONS.md` is appended to, never
  rewritten.

## Decision rights

STOP:
- Any of the six asserted shapes is absent -- one of briefs A, C or D has not
  landed, or landed differently. The check must not be softened to match; the
  answer is an amendment.
- CLAUDE.md is within 500 characters of its 38 000-character budget.

ADAPT:
- A rule is unwritable as a `Name` call lookup because the symbol is called
  through an attribute (`_gathering.dissolve_emptied(...)`): match
  `ast.Attribute` with that `attr` as well as `ast.Name` with that `id`, and
  report.
- The decisions-index regeneration produces a diff in entries this brief did
  not add: commit the regenerated file as produced and report the diff.

REPORT-ONLY:
- The PASS line the new check prints.
- The character count CLAUDE.md ends at.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/gathering_lifecycle.py` prints a single
      `PASS:` line naming its counts and exits 0.
- [ ] Each of the six rules fails when it should: for each, make the named
      mutation on a scratch copy of the tree (never the working tree),
      confirm the check exits 1 with a message naming the file and symbol,
      and restore. The six mutations: rename `_live_gatherings`; make
      `enter_scene` call `_open_gatherings` again; drop
      `_active_members` from `_live_gatherings`; delete `attach_on_arrival`;
      put `status = "dissolved"` back inside `migrate_npc`; add a
      `_get_or_open_session` call to `attach_on_arrival`.
- [ ] The check imports only `ast`, `pathlib` and `sys`
      (`grep -n "^import\|^from" tooling/verify/checks/gathering_lifecycle.py`).
- [ ] TICKET-0089's Machine-checkable section carries the new line with
      exactly one arrow, and `python tooling/verify/checks/pipeline_state.py`
      passes.
- [ ] `python tooling/verify/checks/claude_md_contract.py` passes.
- [ ] `python tooling/verify/checks/decisions_index.py` passes.
- [ ] `python tooling/verify/checks/corpus_gate.py` passes, reporting one more
      discovered check than before this commit.
- [ ] `/review-step` then `/close-step`.

## Docs to update

This step IS the doc update: `CLAUDE.md`'s invariant section,
`tooling/standards/ARCHITECTURE_DECISIONS.md`, the regenerated
`tooling/standards/DECISIONS_INDEX.md`, and TICKET-0089's Machine-checkable
section. No schema changelog entry -- no schema change in this lot.
