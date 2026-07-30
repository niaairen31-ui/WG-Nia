# BRIEF — Step "Doctrine amendment + docs"

> **Revision note.** This file supersedes the first delivery of BRIEF-0055-d.
> Two amendments are folded in: the Node build-vs-runtime paragraph (item 6),
> and the line-ending reproducibility decision escalated during BRIEF-0055-c's
> red-test (item 6, Scope OUT, Done means). No other change.

## Context

Briefs -a, -b and -c changed the facts; this step changes the text, in that
order deliberately so `CLAUDE.md` never describes a state the tree has not
reached. Two doctrine lines assert the old regime and one of them is also
factually wrong about the current one.

Measured constraints, from RECON on `main`:

- `CLAUDE.md` is at **exactly 500 lines** against `claude_md_contract.py`'s
  hard 500-line budget. Zero headroom: this amendment is net-zero or
  net-negative by construction.
- `### File structure` is at 64 lines against its 80-line budget, and
  `claude_md_contract.py` bans `BRIEF-`, `schema v` and `v\d+\.\d+` inside that
  section, plus it asserts every `tooling/...` path named anywhere in
  `CLAUDE.md` exists on disk.
- **There is no HTMX in this project.** `grep -c "hx-"` on `index.html` returns
  0; no `htmx` token exists under `src/` or `tooling/pipeline_cockpit/`.
  `CLAUDE.md:17` is wrong today, independently of this ticket.

## Mini-RECON (report-only)

- **MR-d1.** Report the exact current line count of `CLAUDE.md`, the exact line
  range of `### File structure`, and the verbatim current text of lines 17, 18
  and 58. Anchor the edits below to that output, not to this brief's
  transcription. If any line number has drifted, report the drift and use the
  observed one.
- **MR-d2.** Read `tooling/verify/checks/claude_md_contract.py` and report all
  four assertions with `file:line`, especially the exact `EXPECTED_H2` and
  `EXPECTED_H3_UNDER_CONVENTIONS` lists. The amendment must not add, remove or
  reorder a single heading.
- **MR-d3.** Read `tooling/verify/checks/decisions_index.py` and report exactly
  what it asserts about `DECISIONS_INDEX.md` -- specifically whether entries
  must be in a given order, carry a line anchor, or name a brief. Report the
  format of the last three existing rows verbatim so the new row matches.
- **MR-d4.** Confirm no `tooling/...` path this brief introduces is fictional:
  after -c lands, `tooling/verify/checks/frontend_build_fresh.py` exists.
  Report `ls` output proving it.
- **MR-d5.** Report the verbatim content of `.gitattributes` as it stands after
  BRIEF-0055-c's line-ending fix, and the `node --version` / `npm --version`
  observed during this branch's execution. Both are quoted literally in item 6;
  read them from the tree and the execution record, never from this brief.

## Scope IN

1. **`CLAUDE.md` `## Stack`, replacing the current lines 17-18.** Net line
   count must not grow. Verbatim replacement text (two lines):

   ```
   - Frontend: vanilla-JS single-page `cockpit/index.html` (no HTMX), migrating
     to a built Svelte app under `frontend/`; no new dependency without a decision.
   ```

2. **`CLAUDE.md` `## Invariants`, replacing the current line 58's trailing
   sentence only.** The line currently ends with: *"`index.html` remains a
   single file with no build step; splitting it is a doctrine change, not a
   refactor."* That clause is now false. Replace it, in place, on the same
   physical line, with verbatim:

   > The frontend is mid-migration: `index.html` is the legacy vanilla-JS
   > single-page surface, `frontend/` is the built Svelte app whose committed
   > output under `cockpit/static/` must match its sources -- enforced
   > fail-closed by `tooling/verify/checks/frontend_build_fresh.py`, and by a
   > boot guard that refuses to serve an empty `static/`. Play stays vanilla-JS
   > until its own rewrite. Rationale, target shape and the surface-migration
   > chain live in `tooling/standards/ARCHITECTURE_DECISIONS.md`.

   Do not touch the rest of that line (the review-tree contract). Do not split
   it into several lines -- that would cost budget for nothing.

3. **`CLAUDE.md` `### File structure`.** Two edits, net +1 line at most against
   16 lines of headroom:
   - amend the `index.html` line to say `legacy single-page UI; CREATION_TABS registry + dispatcher`
   - add one sibling line under `cockpit/` for `static/` describing it as the
     committed built-frontend output, and one root-level line for `frontend/`
     as the Svelte sources.

   The archaeology ban applies here: no `BRIEF-`, no `schema v`, no `v\d+\.\d+`
   token anywhere in these lines. Write `TICKET-0055` nowhere in this section.

4. **`CLAUDE.md` `### How to run / test`.** Add exactly one bullet, placed
   immediately before the existing `**Verify:**` bullet:

   ```
   - **Frontend build:** `cd frontend`, `npm ci`, `npm run build` -> writes the
     committed output under `src/world_engine/cockpit/static/`. The output is
     versioned on purpose; rebuild and commit after any `frontend/` edit.
     Node is needed to BUILD only -- a prod launch requires none.
   ```

5. **Verify the budget after edits 1-4** by running
   `python tooling/verify/checks/claude_md_contract.py`. If the file exceeds
   500 lines, do NOT raise `TOTAL_LINE_BUDGET`. Instead report the overage and
   the candidate lines to compress, and stop for Nia's call. The budget is the
   mechanism; raising it because it binds is disarming it.

6. **`tooling/standards/ARCHITECTURE_DECISIONS.md` -- one new section**,
   appended in the file's existing style (H2 heading naming the ticket, brief
   and schema impact), titled:

   `## FRONTEND BUILD FOUNDATION — Svelte/Vite toolchain, static serving, committed build (BRIEF-0055-a..d, no schema change)`

   It must record, each in its own short paragraph, with the locked-code
   labels:

   - **The no-build reversal (A1).** The target is a Svelte SPA owning `/`;
     the transition is necessarily island-shaped because `index.html`'s ~11k
     lines of JS are physically interleaved across surfaces and cannot be
     range-cut. Islands are the intermediate state, not an alternative target.
   - **The Play boundary (B1).** Play stays vanilla-JS until its own rewrite.
     Record the factual correction that no HTMX ever existed here.
   - **The legacy-mount registry, DEFERRED to TICKET-0056 (named deferral).**
     A1 plus a permanently-vanilla Play requires an escape hatch inside the
     SPA; an escape hatch rots unless it is an enumerated, monotonically
     shrinking registry policed by a fail-closed check, reaching exactly one
     entry (Play) at TICKET-0061. Not built at 0055.
   - **Serving topology (C1) and the rejection of C3.** `/static` mount;
     `GET /` untouched; `/shell` as the transitional beachhead and the seam
     TICKET-0056 renames. C3 (extending the per-file vendor whitelist) is
     rejected because a whitelist cannot express content-hashed filenames
     without ceasing to be one. Record that `app.py`'s "wait for a second
     vendored asset" deferral was resolved on different grounds, not by
     analogy.
   - **Cytoscape stays vendored (D3)**, external to the bundler; the graph-
     engine question is TICKET-0057's, deliberately not pre-empted.
   - **Committed build output (E1) and why.** Building at launch fails open --
     a stale or absent build renders a blank page. A committed artifact plus a
     boot guard plus `frontend_build_fresh.py` makes both failure modes
     refusals. Record the canonical hash algorithm's existence and that it is
     specified once and implemented twice.
   - **Permission scope (F3).** `npm ci` and `npm run build` only, never a bare
     `npm install`, so "no new dependencies without a decision" is structural:
     the executor can build and cannot add a package.
   - **Node is a BUILD dependency, never a RUNTIME one (E1 corollary).** The
     output being committed, a prod launch requires no Node at all --
     `docs/launch-procedure.md`'s block stays valid on a machine without it.
     Name the toolchain versions observed at MR-d5, declared as `engines.node`
     in `frontend/package.json` (declarative only, `engine-strict` deliberately
     off). Note the exposure: `frontend_build_fresh.py` compares SOURCES to the
     manifest, not output to anything, so a divergence caused by a different
     Node major would pass unseen. Accepted while a single build machine
     exists; the day a second one appears, pinning (`.nvmrc` plus a version
     manager) becomes a ticket.
   - **Line-ending reproducibility (found at BRIEF-0055-c red-test,
     escalated).** With `core.autocrlf=true` on the build machine, a plain
     `git checkout` of a frontend source rewrites it to CRLF; `git status` sees
     nothing (git normalizes for its own comparison) while the byte-level
     source hash diverges, turning `frontend_build_fresh.py` red with no real
     change -- and a fresh clone on a differently-configured box would do the
     same. Fixed structurally, in the committed `.gitattributes`, extending the
     rule `vendor/* -text` already established for the vendored cytoscape file:
     `frontend/** text eol=lf` (hand-authored, diffs matter) and
     `src/world_engine/cockpit/static/** -text` (generated, like vendor).
     Explicitly REJECTED: a per-machine `core.autocrlf` setting (uncommitted,
     protects nothing beyond one box), and normalizing line endings inside the
     hash algorithm itself (would leave the gate green while Vite still read
     CRLF sources and could emit divergent output -- fail-open). Scope note:
     the rule covers only this ticket's paths; whether the repo wants a global
     `* text=auto eol=lf` is a separate governance question, not settled here.
   - **The 3D guard rail, re-nailed.** No speculative character coordinates;
     "qui entend quoi" stays behind the single earshot accessor; 3D consumes
     what canon exposes and never dictates storage. Restate it here verbatim
     in substance -- the frontend rewrite is the moment of temptation.

7. **`DECISIONS_INDEX.md` -- one new row** for the section added at item 6,
   matching the format reported at MR-d3 exactly.

8. **`docs/launch-procedure.md` -- one new subsection** after `## Prod`,
   titled `## Frontend build`, stating that the output is committed so a normal
   prod launch needs no Node, and giving the rebuild block:

   ```powershell
   cd frontend
   npm ci
   npm run build
   ```

   plus one line: the output under `src/world_engine/cockpit/static/` is
   committed; the cockpit refuses to start if it is missing.

## Scope OUT

- **No restructuring of `CLAUDE.md` beyond the four edits above.** In
  particular: do not touch the `## Invariants` section's other 40 bullets, do
  not merge or split any of them, do not reorder anything.
- **The CLAUDE.md cleanup chantier is a separate ticket and is NOT started
  here.** Measured for that future ticket, record it nowhere in `CLAUDE.md`:
  `## Invariants` is 202 lines / 41 bullets / 2619 words (40% of the file);
  only 7 of the repo's 72 checks are cited in it; the line budget is fail-open
  on content (`CLAUDE.md:276` is a single 5180-character line). Do not act on
  any of it.
- **Do not raise `TOTAL_LINE_BUDGET` or any budget constant in
  `claude_md_contract.py`.** Do not add assertions to it either -- the
  character-budget and enforcer-token assertions belong to the cleanup ticket.
- **Do not widen `.gitattributes` beyond the two rules landed at -c.** A global
  `* text=auto eol=lf` plus a whole-tree renormalize is a governance decision,
  not a rider on a frontend-only ticket. Record the open question; do not
  settle it.
- **Do not enable `engine-strict`, do not add a `.nvmrc`.** `engines` is
  declarative here on purpose.
- **No `world-engine-schema.md` or changelog edit.** This ticket touches no
  schema; `schema_version_touched: none`.
- **No edit to `index.html`.**
- **No `README.md` edit.**
- **No new `ARCHITECTURE_DECISIONS.md` section for TICKET-0056..0061.** Record
  only what 0055 decided, plus the named deferrals at item 6.

## Invariants to defend

- **`CLAUDE.md` is law-only** -- history and rationale live in
  `ARCHITECTURE_DECISIONS.md` and the schema changelog, never in `CLAUDE.md`.
  This is exactly why item 2 ends with a pointer instead of a paragraph.
- **`claude_md_contract.py`'s four assertions** must all still pass: exact
  ordered H2 set, exact ordered H3 set under Conventions, 500/80 budgets,
  archaeology ban inside `### File structure`, and pointer freshness for every
  `tooling/...` path named. Item 2 names
  `tooling/verify/checks/frontend_build_fresh.py` and
  `tooling/standards/ARCHITECTURE_DECISIONS.md`; both must exist on disk when
  the check runs (hence MR-d4).
- **Deferred items are named, never silently dropped** -- the legacy-mount
  registry, the global line-ending question, and Node version pinning are this
  ticket's three named deferrals and must all appear in
  `ARCHITECTURE_DECISIONS.md`, not only in a brief.

## Done means

- [ ] MR-d1..MR-d5 results in the report, with verbatim current text for lines
      17, 18, 58, verbatim `.gitattributes`, and `file:line` citations for
      MR-d2/MR-d3.
- [ ] `CLAUDE.md` is <= 500 lines after all edits; the exact post-edit count is
      reported.
- [ ] `### File structure` is <= 80 lines; the exact post-edit count is
      reported; it contains no `BRIEF-`, `schema v` or `v\d+\.\d+` token.
- [ ] `CLAUDE.md` contains no occurrence of the string `HTMX` anywhere.
- [ ] The `ARCHITECTURE_DECISIONS.md` section names the observed Node and npm
      versions, and `frontend/package.json` declares a matching `engines.node`.
- [ ] `git ls-files --eol frontend/src` reports `w/lf` on every row.
- [ ] `python tooling/verify/checks/claude_md_contract.py` exits 0.
- [ ] `python tooling/verify/checks/decisions_index.py` exits 0.
- [ ] `python tooling/verify/checks/frontend_build_fresh.py` exits 0.
- [ ] `python tooling/verify/run.py --ticket TICKET-0055` returns
      `"green": true` with seven PASS entries; the verdict JSON is in the
      report.
- [ ] `git diff main -- src/world_engine/cockpit/index.html` is EMPTY.
- [ ] All nine pre-existing index-anchored checks pass, each verdict reported.
- [ ] `docs/launch-procedure.md` prod block still works verbatim on a machine
      with no Node installed (state whether this was verified or reasoned; if
      reasoned, say so plainly rather than claiming a test).
- [ ] PR opened on `ticket/0055`; no push to `main`.

## Docs to update

This step IS the doc update: `CLAUDE.md`,
`tooling/standards/ARCHITECTURE_DECISIONS.md`, `DECISIONS_INDEX.md`,
`docs/launch-procedure.md`. No schema changelog entry (no schema change).
