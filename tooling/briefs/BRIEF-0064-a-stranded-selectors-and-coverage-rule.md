# BRIEF — Step "Stranded Creation selectors and the missing coverage rule"

Ticket: TICKET-0064
Brief: BRIEF-0064-a (first and, if nothing unexpected surfaces, only brief)
Commits: 2, in the order given. Do not reorder.

---

## Mini-RECON (verify before writing anything)

Report each item as PASS/FAIL with `file:line` citations. **If any item fails,
STOP and report — do not adapt the plan.** These numbers were measured on
`main` @ `6185e3d`; the tree may have moved.

**M1.** `src/world_engine/cockpit/index.html` has exactly one `<style>` block.
Record its opening and closing line numbers (expected `12` and `511`).

**M2.** Inside that block, confirm each of the following selectors exists, and
record its line:

```
.layout            35      .transcript-panel   89
.sidebar           44      .panel-head         96
.sidebar-head      51      .panel-head h2     105
.sidebar-head button 64    .analyze-status    106
.conv-list         65      .btn-end           400
.right-col         82      .app-view          473
```

**M3.** Confirm these three are present in the same block and are **not**
applied anywhere under `frontend/src/**` (they stay inline):

```
.conv-item (70), .conv-item:hover (76), .conv-item.active (77),
.conv-item .ci-id (78), .conv-item .ci-meta (79), .transcript-body (108)
```

**M4.** Count surviving legacy consumers for each mover — occurrences of the
class inside a `class="..."` attribute anywhere in `cockpit/index.html`
**after** the `</style>` tag (this includes its `<script>`, which builds markup
from template strings). Expected exactly:

```
.app-view 2   .panel-head 3   .sidebar 1   .sidebar-head 1   .conv-list 1
.transcript-panel 1   .btn-end 1   .analyze-status 1
.layout 0   .right-col 0
```

`.layout` and `.right-col` at zero is the entire justification for sending
those two to `creation.css` rather than `shared.css`. **If either is non-zero,
STOP.** If one of the other eight is zero, STOP as well: that selector's
destination changes and the decision is Nia's, not yours.

**M5.** Confirm `frontend/src/creation/Creation.svelte` contains no `<style>`
block, and that `src/world_engine/cockpit/static/assets/*.css` defines none of
the twelve selectors in M2. This is what makes them unreachable.

**M6.** Confirm `src/world_engine/cockpit/static/index.html` links
`/static/shared.css` and `/static/creation.css`, and that
`src/world_engine/cockpit/index.html` links `/static/shared.css` only. Do not
change either.

**M7.** Confirm `frontend/src/creation/Creation.svelte` applies
`id="creation-editor-area"` (expected line 160). Commit 2 needs a real,
frontend-applied id for its negative demonstration.

**M8.** Record the current line count of
`tooling/verify/checks/stylesheet_partition.py` (expected 299) and the length
of its longest function. The 1000-line module cap and 80-line function ceiling
apply to commit 2's additions.

---

## Scope IN

### Commit 1 — relocate the ten stranded selectors

The rules below are **moved verbatim**: byte-for-byte identical declaration
blocks, same property order, same formatting. Do not reformat, do not merge
rules, do not rename. Delete each from `cockpit/index.html`'s inline `<style>`
in the same commit that adds it to its destination sheet. A selector present in
two places at any point in this commit is a rule2 violation.

**1.1 — Into `frontend/public/shared.css`.** Insert a new banner immediately
after the existing `Base` section and immediately before the
`/* ── Queue panel ── */` banner. Banner text verbatim:

```css
/* ── Surface shell (shared: legacy document + Svelte shell) ──────────────── */
```

Under it, in this order: `.app-view`, `.sidebar`, `.sidebar-head`,
`.sidebar-head button`, `.conv-list`, `.transcript-panel`, `.panel-head`,
`.panel-head h2`, `.analyze-status`.

`.btn-end` does **not** go in that banner. It belongs to the existing
`/* ── Buttons ── */` section of `shared.css`; append it as the last rule of
that section.

**1.2 — Into `frontend/public/creation.css`.** Insert a new banner immediately
before the existing `/* ── Création sub-tab bar ── */` banner. Banner text
verbatim:

```css
/* ── Creation two-column layout (TICKET-0064; zero legacy consumers) ─────── */
```

Under it, in this order: `.layout`, `.right-col`.

**1.3 — Leave inline.** `.conv-item` and its four sibling rules, and
`.transcript-body`, stay in `cockpit/index.html`. They share banners with
movers and it will be tempting to take the whole section. Do not. The move is
selector-level, decided by M4's consumer counts.

**1.4 — Banner hygiene in `cockpit/index.html`.** The `Two-column layout`,
`Right column` and `App views` banners become empty once their only rules
leave. Delete those three banner comments. The `Sidebar` and `Transcript panel`
banners retain rules and keep their comments unchanged.

**1.5 — Rebuild.** Run the frontend build so
`src/world_engine/cockpit/static/shared.css` and `static/creation.css`
byte-match their `frontend/public/` sources, and the JS bundle plus
`.build-manifest.json` are regenerated. Commit the rebuilt artifacts.

### Commit 2 — `rule7 (coverage)` in `stylesheet_partition.py`

Add a seventh rule to the existing check. Do not create a new check file.

**2.1 — What rule7 asserts.** A selector that survives in `cockpit/index.html`'s
inline `<style>` **and** is applied by markup under `frontend/src/**` is a
stranding: the Svelte document does not load that block, so the rule cannot
reach the element. Any such selector FAILS.

This is deliberately narrower than "every applied class has a style." A class
applied under `frontend/src/**` and defined nowhere at all is **not** a rule7
failure — it is either a JavaScript query hook or an inline-styled element, and
four such classes exist today (see Notes). Narrowing this way is what makes
rule7 carry no exemption list, no baseline and no annotation convention.

**2.2 — The applied-name extractor.** Scan every `*.svelte` and `*.js` file
under `frontend/src/`. From each, extract applied **class** names and applied
**id** names (F2 — both, same mechanism).

Match only literal double-quoted attributes: `class="..."` and `id="..."`.
An attribute written `class={expr}` with no quotes contributes nothing.

Within a matched attribute value, expressions `{...}` are removed, and the
literal runs between them are tokenised on whitespace. A token is discarded
when it is **adjacent to a removed expression with no intervening whitespace**:

- run not preceded by whitespace or the start of the value → discard its first token
- run not followed by whitespace or the end of the value → discard its last token

So `class="card {resultCls}"` yields `card`; `class="b-{kind}"` yields nothing;
`class="a{x}b"` yields nothing; `class="row {x} tall"` yields `row` and `tall`.
Without this adjacency rule the extractor emits fragments like `b-` and `s-`
and rule7 becomes noise. Surviving tokens must match `^[A-Za-z_][\w-]*$`.

**2.3 — The inline-selector set.** Parse the `<style>` block of
`cockpit/index.html` and collect every class name (`.name`) and id name
(`#name`) appearing anywhere in a selector, including in descendant and
compound selectors, so `.panel-head h2` contributes `panel-head` and
`#obs-panel .row` contributes both.

**2.4 — The verdict.** `STRANDED = APPLIED ∩ INLINE`. If non-empty, FAIL, and
print one line per stranded name giving the name and up to three
`frontend/src` files that apply it, so the fix is actionable without a
re-scan.

**2.5 — Vacuous-proof guards.** Each of these FAILS on its own, independently
of rule1's ordering — rule7 must not inherit its liveness from another rule:

- `frontend/src/` is not a directory
- zero `.svelte`/`.js` files scanned
- zero applied class names extracted (a broken extractor must not pass)
- zero applied id names extracted
- the inline `<style>` block is absent, unparseable, or yields zero selectors

**2.6 — Negative demonstration.** Prove rule7 bites, in both directions of F2.
Perform each temporarily, capture the FAIL output, revert, and confirm the
check returns to PASS. Record the four outputs in the commit message. Do not
commit the temporary edits.

- **Class:** re-add the `.layout` rule to `cockpit/index.html`'s inline
  `<style>`. rule7 must FAIL naming `layout` and citing `Creation.svelte`.
  (rule2 will also fail — that is expected and does not substitute for rule7
  firing; report both.)
- **Id:** add `#creation-editor-area { outline: 1px solid red; }` to the inline
  `<style>`. rule7 must FAIL naming `creation-editor-area`. rule2 will pass
  here, since the id is defined nowhere else — this case is precisely why F2
  exists and must be shown independently.

**2.7 — PASS message.** Extend the existing one-line PASS in the established
idiom, reporting real counts: files scanned, applied class names, applied id
names, inline selectors parsed, zero stranded. A count of zero anywhere is a
failure per 2.5, not a passing scan.

---

## Scope OUT

Each item below was discussed and deliberately excluded. None is an oversight;
none is to be "improved while we're in there."

1. **Observation, and the mirror direction of rule7.** Decision `G1`. rule7 is
   one-directional: `frontend/src/**` against the Svelte-reachable sheets. It
   does **not** verify that the legacy document's own markup resolves against
   `shared.css` plus its inline block. Observation still lives in the legacy
   document and may have lost selectors to `creation.css` by the same
   mechanism. Not audited, not fixed here. Reactivation condition, verbatim for
   the docstring: **"the mirror direction is unguarded until TICKET-0060
   migrates Observation out of the legacy document."**

2. **The four applied-but-undefined classes.** `.graph-mount-target` and
   `.graph-side-panel` (`frontend/src/graph/mount.js:152,154`, retrieved via
   `querySelector` at `:159,160`), `.signpost-group`
   (`DiscDetailsEditor.svelte:209`, styled by an inline `style=` attribute) and
   `.tick-controls` (`QueueFilters.svelte:138`). REPORT ONLY. Do not style
   them, do not delete them, do not add them to any sheet. rule7 as specified
   does not flag them — that is the design, not a gap to close.

3. **Dead CSS carried over by TICKET-0063.** `.author-type-tabs` and
   `.author-new-row` in `creation.css` have zero consumers. Already reported by
   `RECON-0063-a`. Leave them.

4. **TICKET-0059's live gate.** Thirty-two unchecked criteria. This brief makes
   the Creation ones testable. It does not discharge them and must not tick
   them.

5. **The other six rules of `stylesheet_partition.py`.** No refactor, no
   renumbering, no shared-helper extraction. rule7 is additive.

6. **Banner reorganisation of `shared.css` / `creation.css`** beyond the two
   insertions in 1.1 and 1.2. Do not sort, do not consolidate.

7. **Play's remaining inline CSS.** ~89 class selectors survive in the inline
   block after commit 1. Leave every one.

8. **An annotation convention for dynamic classes** (the rejected `E3`). No
   `<!-- css-classes: -->` comments, anywhere.

9. **Any backend change.** Frontend-only. If a fix appears to need one, that is
   an escalation.

---

## Invariants to defend

- **rule2 (disjointness) must still pass after commit 1.** Moving a selector
  means deleting it from the source in the same commit. This is the rule most
  likely to break here, because the natural way to work is copy-then-delete and
  the intermediate state violates it.
- **rule5 (creation.css link lifetime).** `cockpit/index.html` must **not**
  regain a `creation.css` link. `.layout` and `.right-col` land in
  `creation.css` precisely because the legacy document has no consumer for
  them. Re-adding the link to "be safe" defeats the mount-lifetime coupling
  that rule5 exists to enforce.
- **rule6 (byte parity).** Both `static/` copies must byte-match their
  `frontend/public/` sources after commit 1. No line-ending normalisation.
- **Fail-closed and vacuous-proof** (CLAUDE.md). rule7 has five independent
  vacuity guards (2.5). A rule that passes when its scan finds nothing is worse
  than no rule, and is the exact failure this ticket exists to correct.
- **Structural over disciplinary.** rule7 must carry no baseline, no
  allow-list, no exemption file and no annotation convention. If the
  implementation seems to need one, the specification has been misread — STOP
  and report rather than introducing a list.
- **History is sacred.** `RECON-0063-a-selector-audit.md` is corrected by
  **appending** a note, never by editing its original classification. Its
  reasoning was sound at the time it was written; the record must show that.
- **Module budget.** `stylesheet_partition.py` stays under 1000 lines; every
  function under 80. If rule7 pushes a function past the ceiling, split it
  along a real boundary (extraction / inline parsing / verdict) rather than
  requesting an exemption.
- **Frontend-only scope.** Files touched: `frontend/public/shared.css`,
  `frontend/public/creation.css`, `src/world_engine/cockpit/index.html`,
  `src/world_engine/cockpit/static/**` (build output),
  `tooling/verify/checks/stylesheet_partition.py`, and the docs named below.
  Nothing else.

---

## Done means

**Commit 1**

- [ ] `.app-view`, `.sidebar`, `.sidebar-head`, `.sidebar-head button`,
      `.conv-list`, `.transcript-panel`, `.panel-head`, `.panel-head h2`,
      `.analyze-status` appear in `frontend/public/shared.css`, byte-identical
      to their previous inline text.
- [ ] `.btn-end` appears in `shared.css` under the `Buttons` banner.
- [ ] `.layout` and `.right-col` appear in `frontend/public/creation.css`.
- [ ] None of those ten appears in `cockpit/index.html` any longer.
- [ ] `.conv-item`, `.conv-item:hover`, `.conv-item.active`,
      `.conv-item .ci-id`, `.conv-item .ci-meta`, `.transcript-body` remain in
      `cockpit/index.html`.
- [ ] The `Two-column layout`, `Right column` and `App views` banner comments
      are gone from `cockpit/index.html`; `Sidebar` and `Transcript panel`
      remain.
- [ ] `cockpit/index.html` still links `shared.css` and still does not link
      `creation.css`.
- [ ] `static/shared.css` and `static/creation.css` byte-match their sources.
- [ ] `stylesheet_partition.py` (six rules, pre-rule7) PASSES.
- [ ] `frontend_build_fresh.py` PASSES.

**Commit 2**

- [ ] `stylesheet_partition.py` PASSES with a seven-rule message reporting
      non-zero counts for files scanned, applied classes, applied ids and
      inline selectors.
- [ ] Re-adding `.layout` inline makes rule7 FAIL, naming `layout` and citing
      `Creation.svelte`. Output recorded in the commit message. Reverted.
- [ ] Adding `#creation-editor-area` inline makes rule7 FAIL, naming
      `creation-editor-area`, **while rule2 passes**. Output recorded.
      Reverted.
- [ ] Emptying the extractor (or pointing `frontend/src` at a non-existent
      path) makes rule7 FAIL rather than pass. Output recorded. Reverted.
- [ ] `stylesheet_partition.py` is under 1000 lines; no function exceeds 80.
- [ ] No baseline file, allow-list or annotation was added anywhere.

**Both**

- [ ] `git diff` touches no file under `src/world_engine/` outside
      `cockpit/index.html` and `cockpit/static/`.
- [ ] Full verify suite green; `/review-step` and `/close-step` run.
- [ ] `tooling/verify/results/TICKET-0064-creation-stylesheet-coverage.json`
      written.

---

## Docs to update

- **`stylesheet_partition.py` module docstring.** "Six rules" becomes seven.
  Add rule7's paragraph in the existing idiom, stating what it proves *and*
  what it deliberately does not: that a class defined nowhere is out of scope
  by design. Include the G1 deferral verbatim from Scope OUT item 1.
- **`tooling/briefs/RECON-0063-a-selector-audit.md`.** Append — do not edit — a
  dated correction under a new `## Correction (TICKET-0064)` heading: the
  "stays inline" classification of Two-column layout / Sidebar / Right column /
  Transcript panel / App views was correct when measured and was invalidated by
  `3fa8844`, which created `Creation.svelte` applying those class names inside
  the same merge train.
- **`tooling/standards/ARCHITECTURE_DECISIONS.md`.** New append-only entry: a
  partition check that proves disjointness does not prove coverage; the two
  guarantees are independent and both must be asserted. Name `rule7` as the
  coverage half and record the directional deferral to TICKET-0060.
- **`tooling/tickets/TICKET-0064-creation-stylesheet-coverage.md`.** Tick the
  machine-checkable criteria as they are demonstrated. Leave the live gate for
  Nia.
- **`CLAUDE.md`.** No doctrine change. Touch it only if it enumerates the check
  roster's guarantees; if so, one line for rule7's coverage assertion.

---

## Drafting decisions embedded in this brief (Nia may reverse before deposit)

1. **`.btn-end` goes to `shared.css`'s existing `Buttons` banner, not the new
   `Surface shell` banner.** It sits under the Play-exclusive `Scene view`
   banner in `index.html` today, but it is a button, it has one legacy consumer
   and four Svelte consumers. Alternative: give it its own line in the new
   banner and keep the physical grouping.
2. **The three emptied banner comments are deleted** (1.4) rather than left as
   markers. Deleting is cleaner; leaving them would document that the section
   moved. I chose clean.
3. **The adjacency rule in the extractor** (2.2) is my refinement of `E2`, not
   something you locked. Without it the extractor emits `b-` and `s-` fragments
   and rule7 is unusable. I read it as `E2` correctly implemented rather than a
   new decision, but it is a judgment call and it is the single most
   consequential line of the spec.
4. **rule7 lives in one function or three** is left to the executor, bounded by
   the 80-line ceiling. I did not prescribe the internal shape.
5. **The vacuity-guard demonstration** (commit 2, third checkbox) is my
   addition. `2.5` specifies five guards; I require only one to be shown
   firing, on the grounds that demonstrating all five is ceremony. If you want
   all five demonstrated, say so.

---

## Amendment 2 (Nia, in-session — rule7 implementation discoveries)

The executor implemented rule7 exactly per Sec2.1–2.7 above and ran it
against the real tree. Two findings surfaced, neither answerable from this
brief as written. Full record: `QUESTION-TICKET-0064.md`'s follow-up
section (appended, not edited into the original exchange). This amendment
corrects Sec2.1 and Sec2.3's `STRANDED = APPLIED ∩ INLINE` formula and
resequences the remaining commits. §2.1 and §2.3 above are NOT edited in
place — the record should show the original specification was wrong and
how, not read as if it were always correct.

### The corrected formula

A missing term, not an exemption. Evaluated per applying file F:

```
STRANDED(F) = APPLIED(F) ∩ INLINE − REACHABLE − SCOPED(F)
REACHABLE = base rules in shared.css ∪ creation.css ∪ built bundle CSS
SCOPED(F) = base rules in F's own <style> block
```

`SCOPED` is per-file and must not be unioned across components — Svelte
scopes CSS per component, so `Header.svelte`'s `.local-badge` does not
cover a same-named `.local-badge` applied by a different component. This
resolves Finding 1 (`Header.svelte`'s `.local-badge`/`.mode-tab`/
`.mode-tabs`/`.spacer`/`.sub` are correctly styled via its own scoped
`<style>`, independent of the inline block's identically-named — and
still legitimately needed, for the legacy document's own suppressed
header markup — rules). Computed, not enumerated: no baseline, no
allow-list, no annotation. The "no exemption list" invariant (Sec2.1,
Invariants to defend) is intact.

**`INLINE` stays loose** (Sec2.3, unchanged): any class/id name anywhere
in a selector, descendant position included. **`REACHABLE` and `SCOPED`
must be strict — base rules only:** a selector counts only when its whole
text is `.N` with optional pseudo-classes, pseudo-elements or
self-compounds (`.N`, `.N:hover`, `.N.active`, `.N::before`); anything
more qualified is a contextual override and proves nothing about the
element's base styling.

**The asymmetry is the fix for Finding 2, not a refinement.** Loose
reachability reports the original ten stranded names and silently misses
`.btn-send` — 24 files, defined only inline — because
`.lieux-graph-head .btn-send` (`creation.css`) reads as coverage under a
loose test. Strict correctly reports eleven, `.btn-send` included, zero
additional false positives anywhere under `frontend/src`. Loose would
have shipped rule7 green over a live stranding: the exact fail-open this
ticket exists to close, reproduced inside the fix.

**Class and id namespaces stay separate**, never unioned — `btn-send`
exists as both a class and an id in this tree; nothing fires today, but a
unioned rule7 would eventually cross-trigger between namespaces.

### `.btn-send` is in scope for TICKET-0064 (not a separate ticket)

The 24-file count is a consumer count, not a work estimate — the fix is
one seven-line base rule changing sheets, smaller than commit 1. More
decisively: rule7 must be green when this ticket lands (baselining it is
forbidden by its own invariants; landing it disabled empties the ticket;
landing it red violates fail-closed), and there is no clean way to get
there without moving `.btn-send`. Destination: `frontend/public/shared.css`,
`Buttons` banner, adjacent to `.btn-end` — A1 applied to its six measured
legacy consumers (all Play). `creation.css`'s `.lieux-graph-head .btn-send`
override is untouched; rule2 keys on full selector strings, not
normalized bare names, so it does not collide with the bare `.btn-send`
in `shared.css`.

### Resequenced commits

Commit 1 stands as merged, unamended — history is sacred. Commit
numbering from here:

- **Commit 2** — relocate `.btn-send` to `shared.css`; rebuild `static/`.
- **Commit 3** — rule7 with the corrected formula above, all
  demonstrations (the original two from Sec2.6, plus a third proving
  strictness: weakening `shared.css`'s base `.btn-send` rule to a
  compound selector must make rule7 FAIL, naming `btn-send` — a loose
  implementation would wrongly PASS), and the docs listed in "Docs to
  update" above plus this brief's own amendment trail.

Added STOP condition: before commit 2, the corrected rule7 run against
the branch tip must report exactly one stranded name, `btn-send`, across
24 files — any additional name means the formula correction is still
incomplete.
