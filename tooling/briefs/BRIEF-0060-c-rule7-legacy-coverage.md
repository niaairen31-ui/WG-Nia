# BRIEF — Step "extend rule7's APPLIED domain to the legacy document"

## Context

`stylesheet_partition.py` rule7 (TICKET-0064) closes the gap rule2 left open:
disjointness proves the three sheets never overlap, coverage proves a surface
actually receives its visual layer. But rule7's `APPLIED(F)` domain is
`frontend/src/**/*.{svelte,js}` — one direction only.

`BRIEF-0060-b`'s fourth red test demonstrated the consequence: deleting
`.r-warn` / `.r-err` from `Observation.svelte`'s scoped block leaves
`stylesheet_partition.py` green. Before that migration, the same two rules
were unreachable from the legacy document for nine live call sites and rule7
never spoke, because `cockpit/index.html` is not an applying file.

Decision **C3**: extend the `APPLIED` domain to the legacy document, with
`REACHABLE(legacy) = shared.css ∪ inline` only — deliberately excluding
`creation.css` and the built bundle, neither of which that document links.
The extension carries a retirement condition expressed as a fail-closed alarm
rather than a note, so it announces its own obsolescence instead of waiting to
be remembered.

## Mini-RECON — verify before writing

Report `file:line` for each. **If any anchor does not resolve as described,
STOP and escalate — do not adapt.**

1. `tooling/verify/checks/stylesheet_partition.py` — report the line ranges of
   `_scan_frontend_src`, `_base_rule_names`, `_reachable_names`,
   `_scoped_names_for_file`, `_stranded_names_by_kind`, `_check_rule7`, and
   the constants `FRONTEND_SRC`, `SHARED_SRC`, `CREATION_SRC`, `STATIC_DIR`,
   `APPLIED_ATTR_RE`, `BASE_RULE_RE`, `_tokenize_attr_value`.
2. Confirm `_reachable_names()` unions `shared.css`, `creation.css` and
   `static/assets/*.css`, and that it is called from `_check_rule7` only.
3. Confirm the check currently PASSES and report its PASS line verbatim —
   the selector, file, class-name, id-name and inline-selector counts.
4. `frontend/src/legacy/registry.js` — confirm `LEGACY_MOUNTS` has exactly one
   entry (`play`) after `BRIEF-0060-b`. If it has two, `BRIEF-0060-b` has not
   merged — STOP.
5. `src/world_engine/cockpit/index.html` — confirm it links `shared.css` and
   **not** `creation.css`, and report the line of each `<link>`.
6. Report the git SHA of the commit immediately preceding `BRIEF-0060-b`'s
   first commit. The red test needs the pre-migration `index.html`.
7. Confirm `grep -rn "r-warn\|r-err" frontend/public/` is empty and that both
   names now appear only inside `Observation.svelte`'s scoped block.

## Scope IN

One commit. Only `tooling/verify/checks/stylesheet_partition.py` changes.

### 1. `_scan_legacy_document()` — the new APPLIED source

A function returning `(applied_classes, applied_ids, ok)` for
`src/world_engine/cockpit/index.html`, reusing `APPLIED_ATTR_RE` and
`_tokenize_attr_value` unchanged. Scan the **whole file** — `class="…"` occurs
both in static markup and inside the `<script>` block's template literals, and
both are real applications.

Skip the `<style>` block itself when scanning: a selector is not an
application.

Return `ok=False` when the file is missing or empty. Never return empty sets
as a success.

### 2. `_reachable_names_legacy()` — a deliberately narrower REACHABLE

Strict base rules from **`shared.css` and the inline `<style>` block only**.
Not `creation.css`. Not `static/assets/*.css`.

Add this comment above it, verbatim:

```python
    # TICKET-0060 (BRIEF-0060-c, C3). REACHABLE is per-DOCUMENT, not
    # global. cockpit/index.html links shared.css and nothing else --
    # stylesheet_partition rule5 forbids it linking creation.css while
    # LEGACY_MOUNTS lacks a `creation` entry, and it never loads the
    # Svelte bundle. Unioning either in here would be exactly the
    # fail-open that let .r-warn/.r-err sit unreachable at nine call
    # sites through the whole of TICKET-0059 without this check speaking.
```

### 3. `_check_rule7_legacy()` — the assertion

```
STRANDED(legacy) = APPLIED(legacy)
                   ∩ (creation.css ∪ built bundle)
                   − shared.css
                   − inline
```

computed separately for the class namespace and the id namespace, never
unioned — the same F2 discipline the existing rule7 half follows.

The intersection term is what keeps the rule honest: without it, every purely
semantic class the legacy document applies with no rule anywhere would be
flagged. With it, the rule says precisely *this name is styled somewhere the
legacy document cannot see*, which is the `.r-err` case and nothing else.

Failure message, verbatim shape:

```
rule7 (legacy): class 'NAME' is stranded -- applied in cockpit/index.html
but its only rule lives in a sheet that document does not link
```

and the `id` equivalent.

### 4. Vacuity guards — four, none inheriting liveness from another

- `cockpit/index.html` missing or empty → FAIL.
- zero applied class names extracted → FAIL.
- zero applied id names extracted → FAIL.
- zero base rules parsed from `shared.css` → FAIL.

### 5. The retirement condition, as a fail-closed alarm

Read `LEGACY_MOUNTS` from `frontend/src/legacy/registry.js`. When it parses to
**zero entries**, `_check_rule7_legacy` must FAIL with:

```
rule7 (legacy): retirement condition met -- LEGACY_MOUNTS is empty, no
document applies these selectors any more. Delete the legacy half of rule7
(TICKET-0060, decision C3) and this message with it.
```

Add this comment above the branch, verbatim:

```python
    # TICKET-0060 (BRIEF-0060-c, C3). The retirement condition, stated so
    # a check can evaluate it rather than a person remember it. "Remove it
    # once it serves nothing" is qualitative; "LEGACY_MOUNTS is empty" is
    # not. TICKET-0061 empties that registry, and this rule fails loudly
    # the moment it does -- a deferral whose reactivation condition is
    # enforced by the same fail-closed machinery as the rule itself,
    # never by a note someone has to find.
```

Reuse `legacy_mount.py`'s existing entry regex rather than inventing a second
parser; if that means lifting it into a small shared helper, do so as a pure
relocation with no behaviour change and say so in the commit message.

### 6. Wiring and reporting

Call `_check_rule7_legacy()` from the same place `_check_rule7()` is called.
Extend the PASS line with the legacy half's counts — applied class names,
applied id names, stranded count — so a future reader can see it is not
silently absent.

### 7. Red tests

Perform, capture the transcript, revert. No mutation is committed.

- **The historical case.** Materialise the pre-migration `index.html` from the
  SHA reported in mini-RECON item 6 into a scratch path, restore `.r-warn`
  and `.r-err` to `creation.css`, point the check at that pair, and run it.
  It must FAIL naming both classes. This is the whole justification for the
  rule: it must catch the bug that motivated it.
- **A live case.** Move one rule the legacy document currently applies out of
  `shared.css` into `creation.css`. The check must FAIL. Revert.
- **The retirement alarm.** Empty `LEGACY_MOUNTS`. The check must FAIL with
  the retirement message, not pass and not silently skip. Revert.
- **Namespace separation.** Confirm a stranded class name does not mask a
  same-named id, and vice versa.

## Scope OUT

1. **Do not modify the existing rule7 half.** `_scan_frontend_src`,
   `_reachable_names`, `_scoped_names_for_file`, `_stranded_names_by_kind` and
   `_check_rule7` keep their current behaviour and their current counts. This
   brief adds a second half; it does not refactor the first.
2. **Do not touch rules 1–6.** Not the partition, not the token move, not the
   link assertions, not the freshness comparison.
3. **Do not move any CSS.** If the rule finds a stranded selector on today's
   tree, that is a REPORT ONLY finding for its own ticket. This brief writes a
   check; it does not fix what the check finds.
4. **Do not widen `REACHABLE(legacy)`** to make a finding go away. A green
   obtained by unioning `creation.css` back in is the exact fail-open this
   rule exists to remove.
5. **Do not touch `frontend/public/`, `frontend/src/`, or
   `cockpit/index.html`** except for the temporary, reverted red-test
   mutations.
6. **Do not build the corpus gate.** That is `BRIEF-0060-d`.
7. **Do not delete the legacy half preemptively** or gate it behind a flag.
   It runs until `LEGACY_MOUNTS` is empty, and then it fails until removed.

## Invariants to defend

- **Fail-closed over advisory.** Four independent vacuity guards, and a
  retirement branch that fails rather than skips. A check that can go quiet is
  a check that has already failed.
- **Named deferrals carry verifiable reactivation conditions.** C3's
  retirement is expressed as a predicate the check evaluates, not as a
  qualitative note. This is the direct application of the TICKET-0059 lesson:
  a deferral whose condition cannot be evaluated is not a deferral.
- **Structural over disciplinary.** The rule forbids a configuration; it does
  not remind anyone to check one.
- **Minimal first.** One new source of applied names, one narrowed REACHABLE,
  one assertion. No generalisation to a per-document reachability model —
  there are two documents and one of them is scheduled for removal.

## Done means

- [ ] `WORLD_ENGINE_ENV=dev PYTHONPATH=src python tooling/verify/checks/stylesheet_partition.py`
      exits 0 on unmodified `main`.
- [ ] Its PASS line reports the legacy half's counts alongside the existing
      ones, with a non-zero applied-class count and a non-zero applied-id
      count.
- [ ] `git diff --stat` lists exactly one file:
      `tooling/verify/checks/stylesheet_partition.py` — or two, if the
      `LEGACY_MOUNTS` parser was lifted into a shared helper as a stated pure
      relocation.
- [ ] Four red-test transcripts are in the execution report — historical
      case, live case, retirement alarm, namespace separation — each showing
      the expected failure message, with every mutation reverted and
      `git status` clean.
- [ ] The historical red test names **both** `r-warn` and `r-err`.
- [ ] `legacy_mount.py` still passes and reports 1 mount.

## Docs to update

`tooling/standards/ARCHITECTURE_DECISIONS.md`: append to the TICKET-0060
section opened by `BRIEF-0060-b` — why `REACHABLE` is per-document rather than
global, why the intersection term is what keeps the rule from flagging
unstyled semantic classes, and why the retirement condition is a fail-closed
alarm rather than a comment.

No CLAUDE.md change: rule7 is already covered by the existing
`stylesheet_partition.py` reference and the file is under an enforced line
budget.

No schema change.
