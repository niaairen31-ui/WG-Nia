# BRIEF — Step "Build-freshness gate"

## Context

E1 commits the build output instead of building at launch, because building at
launch fails open -- a stale or absent build renders a blank page rather than
refusing. BRIEF-0055-b paid half that debt with a boot guard that catches an
*absent* build. This step pays the other half: a *stale* build. Without it, E1
rests on remembering to rebuild, which is discipline, not structure.

It is also forced. `tooling/verify/run.py:33-49` makes a ticket whose Machine
section parses to zero criteria red by construction, and no existing check
asserts anything about a frontend build.

The check is modelled on the standing idiom: `FAILURES` list, `_report_and_exit`,
`ROOT` via `parents[3]`, and a vacuous-proof guard -- a zero-result run is a
failure, never a pass.

## Mini-RECON (report-only)

- **MR-c1.** Read `tooling/verify/checks/import_cycle.py` in full and report
  its exact `FAILURES` / `_report_and_exit` / `ROOT` idiom, with `file:line`.
  The new check copies that shape; do not invent a variant.
- **MR-c2.** Read `tooling/verify/run.py:10` and report the exact `LINK` regex
  and the exact arrow syntax it parses out of a ticket's `### Machine` section.
  Then confirm, by running the parser mentally against
  `TICKET-0055-frontend-build-serving-foundation.md`, that all seven arrows in
  its Machine section resolve to existing filenames once this brief lands.
  Report any arrow that would resolve to a missing file.
- **MR-c3.** Report whether any existing check under `tooling/verify/checks/`
  already computes a content hash, and if so its exact algorithm and
  `file:line`. If one exists and is compatible, report it -- but still
  implement the canonical algorithm below verbatim rather than importing, since
  checks are run as standalone subprocesses (`run.py:56`).

## Scope IN

1. **The canonical source-hash algorithm.** Both `frontend/scripts/write-manifest.mjs`
   (created in BRIEF-0055-a) and the new Python check implement these steps
   EXACTLY. This text is normative; copy it, do not paraphrase it, and do not
   "improve" the digest shape on either side.

   > **SOURCE SET.** Every file under `frontend/src/` at any depth, plus
   > exactly these four files: `frontend/package.json`,
   > `frontend/package-lock.json`, `frontend/vite.config.js`,
   > `frontend/index.html`. Nothing else. No exclusion globs, no negations.
   > Paths are expressed relative to the repository root, POSIX-separated.
   >
   > **PER-FILE.** For each file: `sha256` of its raw bytes, lowercase hex.
   >
   > **CANONICAL STRING.** Sort the source set by relative path using plain
   > byte-wise ascending comparison of the UTF-8 path. For each file in that
   > order, append `"<relpath>\n<filehash>\n"`. Concatenate with no separator.
   >
   > **SOURCE HASH.** `sha256` of the canonical string encoded UTF-8,
   > lowercase hex, 64 characters.

   Note for the executor: line endings are hashed as they exist on disk. The
   repo has a `.gitattributes` -- report its content in the execution report
   and state explicitly whether it normalizes `frontend/` files, because a
   normalizing rule would make the hash differ between the working tree and a
   fresh clone. If it does, escalate rather than silently adding a rule.

2. **`tooling/verify/checks/frontend_build_fresh.py`.** Standalone, no DB, exit
   0 on pass and 1 on failure, following the `import_cycle.py` idiom reported
   in MR-c1. A module docstring stating the four assertions and naming
   TICKET-0055 / BRIEF-0055-c. Assertions:

   1. **Sources exist.** `frontend/src/` is a directory and the source set is
      non-empty, and all four named files exist. Any miss is a FAILURE.
      *(Vacuous-proof guard: an empty source set is a failure, never a
      trivially-satisfied comparison.)*
   2. **Output exists.** `src/world_engine/cockpit/static/` is a directory
      containing at least one `*.js` file and an `index.html`. Any miss is a
      FAILURE.
   3. **Manifest exists and is well-formed.**
      `src/world_engine/cockpit/static/.build-manifest.json` parses as JSON and
      carries a `source_hash` matching `^[0-9a-f]{64}$`. Any miss is a FAILURE.
   4. **Manifest is fresh.** The recomputed source hash equals
      `manifest["source_hash"]`. On mismatch the failure message names both
      hashes truncated to 12 chars AND says verbatim:
      `run "npm run build" in frontend/ and commit the output`.

   On pass, print a single `PASS: frontend_build_fresh — ...` line naming the
   source-file count and the output asset count (so a suspiciously small count
   is visible in the verdict rather than hidden behind a green).

3. **Red-test the check before declaring done.** In this order, reporting the
   observed exit code at each step:
   a. Green on a clean build.
   b. Touch one character in `frontend/src/Beachhead.svelte` without
      rebuilding -> exit 1 with the item-2.4 message.
   c. `npm run build` -> exit 0 again.
   d. Delete `.build-manifest.json` -> exit 1 (assertion 3).
   e. Move `frontend/src/` aside -> exit 1 (assertion 1, NOT a vacuous pass).
   f. Restore everything, confirm green.

4. **No ticket-file edit.** `TICKET-0055-frontend-build-serving-foundation.md`
   already routes to this check by name; if MR-c2 finds a mismatch between the
   arrow syntax and what `run.py` parses, REPORT IT and stop -- do not silently
   rewrite the ticket.

## Scope OUT

- **No check that asserts anything about `index.html`, the shell, the router,
  the surfaces, or the graph.** Those belong to 0056-0061 and to the
  re-homing of the nine existing index-anchored checks. This check knows only:
  sources, output, manifest.
- **No modification to any existing check.** In particular
  `relation_graph.py`, `page_contract.py`, `review_component.py` and
  `claude_md_contract.py` are untouched here.
- **No modification to `tooling/verify/run.py`.**
- **No git-based assertion.** Do not shell out to `git` to check whether the
  output is committed. `relation_graph.py:73-83` shows how brittle a
  `git show`-based assertion is (it fails outright when the ref is absent), and
  "is it committed" is already covered by the live gate's clean-`git status`
  criterion. The check must run identically inside and outside a work tree.
- **No timestamp comparison.** `built_at` is informational only; mtimes are not
  reproducible across clones and would make the check fail open on a fresh
  checkout. Freshness is content-hash freshness, nothing else.
- **No auto-rebuild.** The check reports and refuses; it never repairs. A check
  that fixes what it measures cannot fail.
- **No addition to `requirements-dev.txt`.** `hashlib` and `json` are stdlib.

## Invariants to defend

- **Fail-closed over advisory.** Every assertion above refuses; none warns.
- **Vacuous-proof guards on all verify checks** -- the standing lesson. Missing
  sources, an empty source set, a missing manifest and a missing output tree
  are each an explicit FAILURE, never a zero-comparison pass. Assertion 1 and
  assertion 2 exist for exactly this reason and must not be collapsed into the
  hash comparison.
- **One truth about the hash.** The algorithm is specified once, in item 1, and
  implemented twice against that text. If the two implementations disagree the
  check goes red on a fresh build -- which is the correct failure direction and
  must not be "fixed" by loosening the comparison.
- **`CLAUDE.md`'s "no new dependencies without a decision"** -- stdlib only.

## Done means

- [ ] MR-c1, MR-c2, MR-c3 results in the report, with `file:line` citations.
- [ ] `.gitattributes` content reported, with an explicit statement on whether
      it normalizes anything under `frontend/`.
- [ ] `tooling/verify/checks/frontend_build_fresh.py` exists and follows the
      `import_cycle.py` idiom reported at MR-c1.
- [ ] All six red-test steps (item 3 a-f) run, each observed exit code
      reported, ending green.
- [ ] `python tooling/verify/run.py --ticket TICKET-0055` now parses seven
      machine criteria and runs them; the full verdict JSON is in the report.
      All seven must be PASS.
- [ ] `git diff main -- src/world_engine/cockpit/index.html` is EMPTY.
- [ ] `git diff main -- src/world_engine/cockpit/app.py` shows only the
      BRIEF-0055-b changes.

## Docs to update

None in this step. BRIEF-0055-d records the check in
`ARCHITECTURE_DECISIONS.md` and adds its `CLAUDE.md` invariant line.
