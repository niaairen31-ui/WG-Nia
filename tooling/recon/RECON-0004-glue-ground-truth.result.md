# RECON-0004 — Result: Scaffold ground truth for the /pipeline glue

**REPORT ONLY.** No edit, no fix, no design was performed. Every claim below
is cited `path:line` or a verbatim command/output quote.

Ticket: TICKET-0004. Run against the working tree on branch `ticket/0003`
(current branch at recon time — TICKET-0004 has not yet been branched).

---

## Zone A — Existing command contracts

### A1. Per-command contract + status field read/write

**`.claude/commands/recon.md`** (frontmatter `description:` only, `recon.md:1-3`)
- Input: "the RECON spec the user names (in tooling/recon/)" (`recon.md:4`) — a
  free-text argument, not a structured flag.
- Produces: `tooling/recon/<id>.result.md` "as a plain report" (`recon.md:14`).
  No branch, no commit.
- Front-matter `status`: not mentioned anywhere in the file. Does not read or
  write it.

**`.claude/commands/brief-exec.md`** (frontmatter `description:` only,
`brief-exec.md:1-3`)
- Input: "the named BRIEF-NN (tooling/briefs/) AND its cited RECON" (`brief-exec.md:4`).
- Produces: creates/switches to branch `ticket/<NNNN>` (`brief-exec.md:7`);
  commits via the chained `/review-step` then `/close-step` protocol
  (`brief-exec.md:9`); on completion runs `/verify` (`brief-exec.md:11`).
- Front-matter `status`: not mentioned. Does not read or write it.
- Step 2 (`brief-exec.md:8`) instructs: "If you find yourself needing a
  decision the brief did not settle (D1), STOP and report — do not guess."
  This is the existing human-escalation idiom the glue's exec→escalated path
  would need to detect.

**`.claude/commands/verify.md`** (frontmatter `description:` only, `verify.md:1-3`)
- Input: none structured — runs `python -m tooling.verify.run --ticket <TICKET-ID>`
  (`verify.md:6`) against whatever ticket ID the invoker supplies in-context.
- Produces: no file write of its own; delegates entirely to `run.py`, then
  "Report the JSON verdict" (`verify.md:8`). Explicitly: "Do not attempt fixes
  here — that is the exec stage's job." (`verify.md:9`).
- Front-matter `status`: not mentioned. Does not read or write it.

**`.claude/commands/review-step.md`** — **no frontmatter block at all**
(file starts directly at prose, `review-step.md:1`). Produces a verdict line
"CLEAN / ATTENTION / VIOLATION" (`review-step.md:14`) as chat output only —
no file write specified in the command text itself. Front-matter `status`:
not mentioned.

**`.claude/commands/close-step.md`** — **no frontmatter block at all**
(`close-step.md:1`). Produces: conditionally updates
`world-engine-schema-changelog.md` and `world-engine-schema.md`'s header
(`close-step.md:6-9`); conditionally regenerates `DECISIONS_INDEX.md` via
`tooling/glue/gen_decisions_index.py` (`close-step.md:12-14`); "propose a
commit message... Wait for approval before committing" (`close-step.md:21-22`)
— i.e. it does not commit unattended by design. Front-matter `status`: not
mentioned.

**Verdict on the double-writer risk the spec asked about:** none of the five
commands reads or writes the ticket YAML front-matter `status` field today —
confirmed by content inspection of all five files (see above) and by a
zero-match grep for `status` across `.claude/commands/` (ripgrep, no hits).
Corroborated in Zone B2.

### A2. Command-to-command chaining and orchestration format

`brief-exec.md:9,11` and `close-step.md` reference `/review-step`,
`/close-step`, `/verify` by name in prose — chaining already exists, but only
as a natural-language instruction inside a single command's body, interpreted
by the running Claude Code session; there is no structured "steps:" /
"calls:" field in the frontmatter of any of the five commands. Frontmatter
across the five is inconsistent: `recon.md`, `brief-exec.md`, `verify.md`
each carry a two-line `---\ndescription: ...\n---` block only (no other
keys); `review-step.md` and `close-step.md` carry no frontmatter block at
all. No command file references any orchestration primitive beyond numbered
prose steps.

### A3. Verify-verdict shape, `run.py` line anchors

Confirmed unchanged: `RESULTS.mkdir(parents=True, exist_ok=True)` at
`tooling/verify/run.py:44`, `(RESULTS / f"{tid}.json").write_text(...)` at
`run.py:45`, `print(json.dumps(verdict, indent=2))` at `run.py:46`,
`sys.exit(0 if ok else 1)` at `run.py:47`. Verdict shape (`run.py:42-43`):
`{"ticket": tid, "when": <iso ts>, "green": <bool>, "checks": [{"check",
"status", "msg"}, ...]}`.

One nuance not explicit in the spec's assumption: `tid` is whatever string
follows `--ticket` verbatim (`run.py:28-30`), and the ticket markdown is
read from `TICKETS / f"{tid}.md"` (`run.py:30`) — since ticket files are
named `TICKET-NNNN-<slug>.md` (e.g. `TICKET-0003-single-canon-write.md`),
`--ticket` must be passed as the **full slug**, not the bare `TICKET-NNNN`
id. This is corroborated by the two existing result files on disk:
`tooling/verify/results/TICKET-0001-doc-partition.json` and
`tooling/verify/results/TICKET-0003-single-canon-write.json` — both verdict
JSON's `"ticket"` field holds the full slug, not the 4-digit id alone.

---

## Zone B — Ticket front-matter reality vs TEMPLATE.md

### B1. Front-matter per ticket file

`tooling/tickets/TEMPLATE.md:1-13` — canonical field set: `id, title, type,
status, created, model_lane, danger_class, blast_radius, brief_ids,
schema_version_touched, retry_count`; `status` enum verbatim (`TEMPLATE.md:5`):
`intake|recon|brief|exec|verify|live-gate|done|paused|escalated`.

- **`TICKET-0001-doc-partition.md`** — **no YAML front-matter block at all**
  (no `---` delimiters anywhere in the file). Line 1 is an `#` title; line 3
  is a bare prose line `status: draft` (`TICKET-0001-doc-partition.md:3`) —
  `draft` is not a value in TEMPLATE.md's enum. Also present as bare lines:
  `brief_ids: [BRIEF-0001-a, BRIEF-0001-b]` (`:4`),
  `schema_version_touched: none` (`:5`) — but `id`, `type`, `created`,
  `model_lane`, `danger_class`, `blast_radius`, `retry_count` are entirely
  absent. This is a full-format drift from TEMPLATE.md, not a partial one.
- **`TICKET-0003-single-canon-write.md`** — proper front-matter block
  (`:1-13`), all TEMPLATE.md fields present, `status: recon`
  (`TICKET-0003-single-canon-write.md:6`) — matches the enum.
- **`TICKET-0004-pipeline-glue.md`** — proper front-matter block (`:1-13`),
  all TEMPLATE.md fields present, `status: recon`
  (`TICKET-0004-pipeline-glue.md:6`) — matches the enum. (Read for
  cross-reference; not itself part of the "existing tickets" drift check.)

### B2. Programmatic readers of ticket front-matter

Grep for `status:`/`status\s*:` under `tooling/` (ripgrep): **no matches**.
Grep for `status` under `.claude/`: **no matches**. Grep for `status` under
`src/`: 8 files matched (`crud.py`, `writes.py`, `app.py`, `index.html`,
`context.py`, `models.py`, `gathering.py`, `analyzer.py`) — all are
`entity.status` / `vital_status` (world-model columns), unrelated to ticket
YAML. `tooling/verify/run.py`'s `machine_checks()` (`run.py:13-23`) parses
the ticket markdown **body** only (scanning for `### Machine` /
`### Live` section headers and `-> verify/checks/*.py` links) — it never
touches the YAML front-matter block or the `status` key. **Confirmed: nothing
in the repo today programmatically reads the ticket front-matter `status`
field.** The glue would be the first reader.

---

## Zone C — Hooks and permissions

### C1. Hooks — trigger, condition, effect

- **`.claude/hooks/session-start.ps1`** — registered under `SessionStart`
  (`.claude/settings.json:3-5`). Effect: checks `.venv\Scripts\Activate.ps1`
  exists and `$env:PYTHONPATH -eq "src"`; prints a `WARNING:` line for either
  miss (`session-start.ps1:3-4`); always `exit 0` (`:5`) — never blocks.
- **`.claude/hooks/block-main-push.ps1`** — registered under `PreToolUse`,
  `matcher: "Bash"` (`.claude/settings.json:7-9`). Condition
  (`block-main-push.ps1:4`): `$cmd -match 'git\s+push' -and $cmd -match
  '\b(main|master)\b'` — this matches **any** Bash command containing the
  literal text `git push` together with the whole word `main` or `master`
  anywhere in the string, regardless of remote name (`origin`, `upstream`,
  a refspec like `head:main`, etc. would all match). Effect: denies via
  `permissionDecision: "deny"` with reason `"C1: direct push to main is
  blocked..."` (`block-main-push.ps1:5-8`). It fires only on the `Bash` tool
  and only on a literal local `git push` invocation — it does not intercept
  GitHub-side operations (`gh pr merge`, or a merge performed by clicking
  "Merge" in the GitHub UI), since those never construct a `git push`
  command string. No collision with a `gh pr create` call is possible
  through this hook, structurally.
- **`.claude/hooks/block-db-in-git.ps1`** — registered under `PreToolUse`,
  same `matcher: "Bash"` entry (`.claude/settings.json:7-10`). Condition
  (`block-db-in-git.ps1:5`): `git\s+add` + `\.db\b`. Effect: denies with
  reason citing the "June 19 incident" (`block-db-in-git.ps1:6-9`). Comment
  at `block-db-in-git.ps1:1` notes this is "belt-and-suspenders", primary
  defense is `.gitignore`.

No other files exist under `.claude/hooks/` (directory listing: exactly
these three `.ps1` files).

### C2. `.claude/settings.json` permission entries

Full file quoted (`.claude/settings.json:1-15`): it contains exactly one
top-level key, `"hooks"`, with `SessionStart` and `PreToolUse` entries
covering the three hooks above. **There is no `"permissions"` key at all** —
no allow-list, no deny-list, for `git`, `gh`, or any file-write pattern
under `tooling/`. No `.claude/settings.local.json` exists either (checked,
not found).

**BLOCKING FINDING (C2):** `gh` (any subcommand, including `gh pr create`)
is entirely unmentioned in `.claude/settings.json`. Absent an allow-list
entry, a `gh` invocation is subject to whatever the session's default
interactive-permission-prompt behavior is — the glue cannot chain through
that prompt in a semi-supervised session, per the spec's own framing.

---

## Zone D — Git / GitHub infrastructure (PR1 viability)

### D1. Remote, default branch, hosting

```
$ git remote -v
origin  https://github.com/niaairen31-ui/WG-Nia.git (fetch)
origin  https://github.com/niaairen31-ui/WG-Nia.git (push)

$ git symbolic-ref refs/remotes/origin/HEAD
refs/remotes/origin/main
```
GitHub-hosted (`github.com/niaairen31-ui/WG-Nia`), default branch `main`.

### D2. `gh` presence/auth

```
$ gh --version
bash: gh: command not found

(PowerShell)
> gh --version
gh : Le terme «gh» n'est pas reconnu comme nom d'applet de commande...
```

**BLOCKING FINDING (D2):** the `gh` CLI is not installed / not on `PATH` in
either shell available to this session (Git Bash or Windows PowerShell).
`gh auth status` and `gh pr list` could not be run for the same reason.
PR1 (glue opens the PR via `gh pr create`) is not viable as scaffolded today
— confirmed absent, not merely unauthenticated.

### D3. Branch naming convention

```
$ git branch -a
  main
  ticket/0001
* ticket/0003
  tier4-overhearing-analysis
  remotes/origin/HEAD -> origin/main
  remotes/origin/main
  remotes/origin/ticket/0001
  remotes/origin/ticket/0003
  remotes/origin/tier4-overhearing-analysis
```
Convention observed: `ticket/<4-digit-number>` (no `TICKET-` prefix, no
slug suffix) — matches `brief-exec.md:7`'s literal instruction (`ticket/<NNNN>`).
`ticket/0001` and `ticket/0003` both follow it exactly, and both exist on
`origin` too. `tier4-overhearing-analysis` is a pre-existing branch that
predates the convention (does not follow it). No `ticket/0004` branch exists
yet — consistent with TICKET-0004 still being at `status: recon`.

### D4. Merge history

```
$ git log --oneline --all --graph -20
```
shows one merge commit, `2eca999`, message "Merge pull request #2 from
niaairen31-ui/ticket/0001", with two parents (`git log -1 --format="%P"
2eca999` → `c6dd438e... 426b2a9b...`) — a standard (non-squash, non-rebase)
merge commit, preserving `ticket/0001`'s two individual commits
(`bde0bad`, `426b2a9`) as first-parent-side history rather than collapsing
them. This is the only PR merge found in local history (`gh pr list` could
not be run — see D2 — so this is git-log-derived, not confirmed against the
GitHub API).

---

## Zone E — Glue seams

### E1. `tooling/glue/` contents

Directory listing: `next_id.py`, `gen_decisions_index.py`, `__pycache__/`
(compiled artifacts, not source). No other scripts exist yet.

- **`tooling/glue/next_id.py`** — no CLI arguments (no `argparse`, no
  `sys.argv` read). Docstring (`next_id.py:1-5`): scans
  `tooling/tickets`, `tooling/recon`, `tooling/briefs` (`next_id.py:10-14`)
  for filenames matching `(?:TICKET|RECON|BRIEF)-(\d{4})`
  (`next_id.py:15`), prints `max+1` zero-padded to 4 digits
  (`next_id.py:18-27`). Never creates, renames, or writes any file (as
  stated in its own docstring, `next_id.py:3-4`).
- **`tooling/glue/gen_decisions_index.py`** — no CLI arguments. Docstring
  (`gen_decisions_index.py:1-2`): reads
  `tooling/standards/ARCHITECTURE_DECISIONS.md`
  (`gen_decisions_index.py:7`), writes
  `tooling/standards/DECISIONS_INDEX.md` (`:8`, write call at `:49`).
  Never writes the archive file itself.

### E2. `tooling/questions/`

Directory does not exist (`ls` on the path errors "No such file or
directory"). Grep across the whole repo for `tooling/questions` or
`tooling\questions`: **no matches** — nothing references it yet. QF1's
target directory is unbuilt ground, not a rename/retrofit.

### E3. Model-lane configuration

Not present in `.claude/settings.json` (no model-related key at all — see
C2's full-file quote). The only scaffolded statement is prose in
`CLAUDE.md:53-54`: "**Model lanes (E1):** Opus for intake and escalated
architecture decisions; Sonnet for RECON, execution, and verify. `/model
opusplan` = plan on Opus, execute on Sonnet." Each ticket's own front-matter
also carries a per-ticket `model_lane` snapshot (e.g.
`TICKET-0004-pipeline-glue.md:7`: `{ intake: opus, recon: sonnet, exec:
sonnet, verify: sonnet }`) — consistent with the CLAUDE.md prose, not a
separate source of truth.

---

## Cross-cutting finding — not assigned to a single zone, discovered inspecting Zone B/D/E together

While reading `tooling/tickets/`, `tooling/recon/`, `tooling/briefs/` for
Zone B/E, a git-tracking gap surfaced that touches all three zones:

The working tree's `.gitignore` currently (uncommitted — `git status
--short` shows ` M .gitignore`, i.e. an unstaged modification against HEAD)
contains three lines not present in `HEAD:.gitignore`:
```
tooling/tickets/
tooling/recon/
tooling/briefs/
```
(`.gitignore:8-10` in the working copy; absent from `git show HEAD:.gitignore`,
which has no such lines at all, confirmed by direct diff).

Effect, confirmed with `git status --short --ignored -- tooling/tickets/
tooling/recon/ tooling/briefs/`:
```
!! tooling/briefs/BRIEF-0003-a-write-normalization.md
!! tooling/briefs/BRIEF-0003-b-single-canon-write-check.md
!! tooling/recon/RECON-0003-canon-write-map.md
!! tooling/recon/RECON-0003-canon-write-map.result.md
!! tooling/recon/RECON-0004-glue-ground-truth.md
!! tooling/tickets/TICKET-0004-pipeline-glue.md
```
`git ls-files tooling/briefs/ tooling/recon/ tooling/tickets/` confirms none
of these six files are tracked by git at all — only `.gitkeep`, `TEMPLATE.md`,
`TICKET-0001-doc-partition.md`, `TICKET-0003-single-canon-write.md`,
`RECON-0001.md`, `RECON-0001.result.md`, `RECON-0002-doc-partition.md`, and
`RECON-0002-doc-partition.result.md` are tracked (all from before the
`.gitignore` change).

**BLOCKING FINDING (cross-cutting):** the BRIEF-0003-a/-b files and
RECON-0003 files that TICKET-0003's already-merged-to-branch commits
(`418c647`, `56dd093`, `6c52217` — all on `ticket/0003`, all citing
BRIEF-0003-a/-b) depend on for provenance are not, and under the current
`.gitignore` state cannot become, part of git history via an ordinary
`git add`. The newly authored `TICKET-0004-pipeline-glue.md` and
`RECON-0004-glue-ground-truth.md` are in the same state right now. Plain
`git status` (no `--ignored` flag) shows none of this — it reports only
`.gitignore` itself and the two untracked verify-result JSON files — so the
gap is invisible to a normal status check. TICKET-0004's own P1 clarification
states "the file contract is the boundary" between chat-side intake/brief
authoring and the glue's exec segment; that boundary is currently a set of
files git does not see.

---

## BLOCKING FINDINGS (recap)

1. **(C2)** No `permissions` entry for `gh` (or anything) exists in
   `.claude/settings.json` — a `gh pr create` call would hit interactive
   permission prompting, unscaffolded.
2. **(D2)** The `gh` CLI is not installed / not on `PATH` in this
   environment (Bash or PowerShell) — PR1 cannot run at all until this is
   resolved, independent of finding 1.
3. **(cross-cutting, Zone B/D/E)** `tooling/tickets/`, `tooling/recon/`,
   `tooling/briefs/` are gitignored in the current (uncommitted) working
   tree, and six real files — including the just-authored TICKET-0004 and
   RECON-0004 files themselves — are untracked and invisible to plain
   `git status` as a result. Any glue step that commits ticket-pipeline
   artifacts via a normal `git add` will silently omit them.
