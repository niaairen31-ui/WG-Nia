<!-- slug: pre-authorized-commits -->
# BRIEF 0117-B — "A commit is pre-authorized and review chains to close in one turn -- a hook refuses a commit on `main`; the recon stage and its skills retired"

Lot: LOT-0117-claude-md-restructure.md (authoritative on conflict)
Depends on: BRIEF-0117-A

## Anchors to confirm (Mini-RECON)

Halt if any has moved (on `ticket/0117` after BRIEF-0117-A).

- `git apply --check` of the embedded diff succeeds.
- `.claude/commands/close-step.md:21` -> `6. **Commit** — propose a commit message summarizing the step. Wait for`
- `.claude/commands/close-step.md:24` -> `Unattended mode: when invoked from /pipeline (the invoker will say`
- `.claude/commands/brief-exec.md:12` -> ``   and `/close-step` in unattended mode (CA1) and state so explicitly at``
- `.claude/commands/pipeline.md:151` -> `## CA1 — unattended invocations`
- `.claude/settings.json:8` -> `      "Bash(git branch:*)",`
- `tooling/verify/checks/pipeline_state.py:67` -> `BRIEF_EXEC_MD_SENTINEL = "unattended mode (CA1)"`
- `.claude/commands/recon.md:4` -> `You are running a RECON. Read the RECON spec the user names (in tooling/recon/).`
- `.claude/skills/` holds exactly `brief/`, `recon/`, `verify-authoring/`, each with one `SKILL.md`.
- No `.claude/hooks/block-commit-on-main.ps1`, no `tooling/verify/checks/session_config.py`.

## Facts carried

### R-04 — the step commands [M]
Opened: `.claude/commands/{brief-exec,review-step,close-step,pipeline,recon,verify}.md` (read whole).
Finding: `close-step.md:21` « propose a commit message … Wait for approval
before committing », `:24` « Unattended mode: when invoked from /pipeline
… skip the approval wait »; `brief-exec.md` announces unattended mode only
« If this execution was invoked from `/pipeline` »; `review-step.md` reads
« the project invariants in CLAUDE.md » and ends on « End with a one-line
verdict », with no instruction after it; `brief-exec.md:4` « Read the named
BRIEF-NN … AND its cited RECON ».
Consequence: the two behaviours Nia observed are written in these files
(M1). B rewrites the three step commands whole.

### R-05 — /pipeline [M]
Opened: `.claude/commands/pipeline.md` (168 lines).
Finding: Step 0 derives `escalated` from `tooling/questions/QUESTION-TICKET-NNNN.md`
with an empty `## Response` (rule 3), `brief` from a recon result, `recon`
from a recon spec (rules 5-6); Step 1 has a `recon` branch running
`recon.md`; « D1 escalation triggers (QF1) » writes the QUESTION file and
answers through `question_response.py answer`; « CA1 — unattended
invocations » closes the file.
Consequence: A replaces rule 3, the escalated branch and QF1's file; B
removes the recon stage and CA1.

### R-06 — pipeline_state.py [M]
Opened: `tooling/verify/checks/pipeline_state.py` (whole).
Finding: `QUESTIONS = ROOT / "tooling" / "questions"` (:35); an `escalated`
ticket needs `QUESTION-<id>.md` (:141-152); `PIPELINE_MD_SENTINELS` requires
« A ticket with NO recon spec on disk is not an error » and « git push
origin ticket/NNNN » in pipeline.md, `BRIEF_EXEC_MD_SENTINEL = "unattended
mode (CA1)"` in brief-exec.md (:62-67); for status in
`brief/exec/verify/live-gate/done`, every Machine arrow must resolve to a
file under `tooling/verify/checks/`. It globs the filesystem
(`TICKETS.glob("TICKET-*.md")`), so an untracked deposit counts.
Consequence: A, B rewrite it (C-01, C-02). A deposited TICKET-0117 in a
floor status names `session_config.py` and `file_map.py` before B and D
create them: an expected, listed red (ADAPT in A, B, C).

### R-11 — session configuration [M]
Opened: `.claude/settings.json` (whole); `.claude/hooks/*.ps1` (whole).
Finding: `permissions.allow` has `git branch`, `git push origin ticket/*`,
`git merge origin/main`… and no `git add`, `git commit`, `git switch`.
`PreToolUse` Bash runs `block-main-push.ps1` (denies a command matching
`git\s+push` AND `\b(main|master)\b`) and `block-db-in-git.ps1`.
`session-start.ps1` only warns about the venv and `PYTHONPATH`.
Consequence: a commit on `main` followed by a bare `git push` passes today;
M1 adds the commit hook and the three permissions.

### R-12 — the recon stage and the skills [M]
Opened: `.claude/commands/recon.md`, `.claude/skills/{recon,brief,verify-authoring}/SKILL.md`
(whole); `git log -1` on each (2026-07-01); `ls tooling/recon` (36 files,
last `RECON-0090-oriented-relations.md`).
Finding: the `brief` skill says a brief « is written AFTER its RECON » and
« backup runs first (hook) »; no backup hook exists (R-11) and CLAUDE.md
says no automated backup exists. `verify-authoring` says a DB assertion
« connect[s] to ~/.world_engine/world_engine.db ».
Consequence: L4-L6. `tooling/recon/` stays as an archive.

### R-17 — decision entries [M]
Opened: `tooling/verify/checks/decisions_index.py` (`STRICT_HEADER`);
the registry's last 30 lines.
Finding: a new header must match `## … (BRIEF-NNNN[-x][, …], schema vX.YY |
no schema change)` with a lowercase brief letter; entries sit above the
`---` / `*Co-built with Claude, June 2026.*` footer; the index is
regenerated by `python tooling/glue/gen_decisions_index.py`.
Consequence: each brief appends one entry above the footer and regenerates.

## Contracts

### C-01 — `tooling/glue/escalation.py` and the `## Escalations` section
Produced by: BRIEF-0117-A   Consumed by: BRIEF-0117-A (`pipeline_state.py`, `pipeline.md`), B (`session_config.py`)
Signature:
- `SECTION_HEADER = "## Escalations"`, `RESPONSE_MARKER = "**Response:**"`,
  `TRIGGERS = ("D1-a", "D1-b", "D1-c", "D1-d")`,
  `ENTRY_RE = re.compile(r"^### (E-(\d{2})) — (.+)$")`
- `entries(text: str) -> list[dict]` — keys `id`, `title`, `response`
- `open_entries(text: str) -> list[str]`
- `ticket_path(ticket_id: str) -> pathlib.Path`
- `append_entry(path, trigger: str, brief: str, body: dict) -> str`
- `write_response(path, entry_id: str, answer: str) -> None`
- CLI: `list`; `open TICKET-NNNN D1-x <brief>` (stdin: JSON with
  `context`, `question`, `options`); `answer TICKET-NNNN E-NN` (stdin: text)
Return shape: an entry is
```

### C-03 — `tooling/verify/checks/session_config.py`
Produced by: BRIEF-0117-B (SC1-SC5), BRIEF-0117-E (SC6)   Consumed by: the ticket's Machine section
Signature: rules SC1-SC6 as in its docstring; prose is matched with its
whitespace collapsed (`flat`).
Return shape: exit 0 with one `PASS: session_config -- …` line, else
`FAIL: SCn: …` lines and exit 1.
Error and empty cases: every file it reads missing is a FAILURE; no
`PreToolUse` Bash hook collected is a FAILURE.

## Context

Nia sees Claude Code ask before every commit under `/brief-exec` and not
under `/pipeline`, and stop between `/review-step` and `/close-step`. Both
are written in the command files (R-04). M1 makes one behaviour for both
paths, and replaces the approval that kept commits off `main` with a hook.
The recon stage, `/recon` and the stale skills go (L4-L6). Second of five
sequential briefs.

## Scope IN

1. Apply the embedded diff (`git apply`). It rewrites
   `.claude/commands/brief-exec.md`, `review-step.md` and `close-step.md`
   whole; edits `pipeline.md` (Step 0 rules 4-6, Step 1 without the recon
   branch, the exec branch, the escalation JSON written outside the
   repository, CA1 removed); adds `Bash(git switch:*)`, `Bash(git add:*)`,
   `Bash(git commit:*)` and the `block-commit-on-main.ps1` hook to
   `.claude/settings.json`; creates `.claude/hooks/block-commit-on-main.ps1`
   and `tooling/verify/checks/session_config.py`; removes the command-file
   sentinels from `pipeline_state.py`; rewrites CLAUDE.md's « Ticket
   pipeline (governance) » section and two tree lines; appends one decision
   entry above the footer.
2. `git rm -r .claude/commands/recon.md .claude/skills`
3. `python tooling/glue/gen_decisions_index.py`
4. One commit: `feat(pipeline): commits pre-authorized behind a no-commit-on-main hook; review chains to close; recon stage retired (TICKET-0117, BRIEF-0117-b)`.
   This brief's own commit already follows the new chain only once the
   diff is applied: run `/review-step`, then `/close-step` in the same turn.

### Embedded diff

Applies on `ticket/0117` after BRIEF-0117-A. Excludes the generated index
(step 3) and the deletions (step 2).

````diff
diff --git a/.claude/commands/brief-exec.md b/.claude/commands/brief-exec.md
index 05f7591..30e8ce3 100644
--- a/.claude/commands/brief-exec.md
+++ b/.claude/commands/brief-exec.md
@@ -1,15 +1,18 @@
 ---
-description: Execute a BRIEF-NN on a ticket branch.
+description: Execute one brief of a ticket's lot on its ticket branch.
 ---
-Read the named BRIEF-NN (tooling/briefs/) AND its cited RECON AND only the target
-files it names. Do NOT read the whole tree.
+Read the named brief (tooling/briefs/) and only the files it names. The brief
+embeds every RECON finding and contract it relies on; its lot header
+(tooling/lots/) is authoritative on conflict. Do NOT read the whole tree.
 
-1. Create/switch to branch `ticket/<NNNN>`.
-2. Implement exactly what the brief specifies. If you find yourself needing a
-   decision the brief did not settle (D1), STOP and report — do not guess.
-3. Commit with the mandatory protocol: /review-step then /close-step.
-   If this execution was invoked from `/pipeline`, invoke `/review-step`
-   and `/close-step` in unattended mode (CA1) and state so explicitly at
-   each invocation; do not wait for a manual `/close-step` between
-   briefs of the same ticket.
-4. Never push to main. When done, run /verify for this ticket.
+1. `git switch ticket/<NNNN>`, or `git switch -c ticket/<NNNN>` from `main`
+   when the branch does not exist yet. Never commit on `main`.
+2. Confirm the brief's Mini-RECON anchors. One that does not hold is a STOP.
+3. Implement exactly what the brief specifies, under its Decision rights. A
+   decision the brief did not settle is a STOP: report it, do not guess.
+4. For every commit the brief lists: run /review-step, then continue to
+   /close-step in the same turn when the verdict is CLEAN or ATTENTION.
+   Stop only on VIOLATION. Commits are pre-authorized: /close-step commits
+   without waiting for approval.
+5. Never push to main. When the brief's commits are done, run /verify for
+   this ticket.
diff --git a/.claude/commands/close-step.md b/.claude/commands/close-step.md
index ec6165b..d20e060 100644
--- a/.claude/commands/close-step.md
+++ b/.claude/commands/close-step.md
@@ -12,17 +12,17 @@ Run the step-closure checklist for the work just completed:
 tooling/standards/ARCHITECTURE_DECISIONS.md, run
 python tooling/glue/gen_decisions_index.py and commit the regenerated
 DECISIONS_INDEX.md.
-3. **Docs sync** diff what tooling/standards/ARCHITECTURE_DECISIONS.md and the root CLAUDE.md claim against what the code now does. Update any stale statement.
+3. **Docs sync** diff what tooling/standards/ARCHITECTURE_DECISIONS.md, the root CLAUDE.md and
+   every `.claude/rules/*.md` claim against what the code now does. Update any stale statement.
    Quote each correction made.
 4. **Debts** — list any shortcuts, deferred decisions, or new debts
    introduced in this step. Propose a changelog or backlog note for each.
-5. **Invariants** — re-read the Invariants section of CLAUDE.md and confirm
-   none was weakened. Flag anything ambiguous.
-6. **Commit** — propose a commit message summarizing the step. Wait for
-   approval before committing.
+5. **Invariants** — re-read the invariants (the root CLAUDE.md and every
+   `.claude/rules/*.md`) and confirm none was weakened. Flag anything
+   ambiguous.
+6. **Commit** — check that the current branch is `ticket/NNNN`, never
+   `main`; stage the step's files and commit with a message summarizing
+   the step. Commits are pre-authorized: do not wait for approval.
 
-Unattended mode: when invoked from /pipeline (the invoker will say
-so), skip the approval wait and commit directly. All other steps
-(changelog, decisions index, message quality) unchanged.
-
-Report as a numbered checklist with PASS / FIXED / ATTENTION per item.
+Report as a numbered checklist with PASS / FIXED / ATTENTION per item,
+including the ATTENTION items /review-step carried over.
diff --git a/.claude/commands/pipeline.md b/.claude/commands/pipeline.md
index a39da1a..30e5e98 100644
--- a/.claude/commands/pipeline.md
+++ b/.claude/commands/pipeline.md
@@ -21,10 +21,8 @@ front-matter, in this precedence order:
    (`tooling/glue/escalation.py`'s `open_entries`) -> `escalated`.
 4. Brief file(s) `tooling/briefs/BRIEF-NNNN*.md` exist -> eligible for
    `exec`.
-5. A recon result (`tooling/recon/RECON-NNNN*.result.md`) exists ->
-   `brief`.
-6. A recon spec (`tooling/recon/RECON-NNNN*.md`) exists -> `recon`.
-7. Otherwise -> `intake`.
+5. A lot header `tooling/lots/LOT-NNNN-*.md` exists -> `brief`.
+6. Otherwise -> `intake`.
 
 Also reconcile `brief_ids` from the brief files actually observed on
 disk.
@@ -39,28 +37,17 @@ observes and records.
 - `live-gate` -> if the PR's mergeable state is `CONFLICTING`, run the
   PR-conflict procedure (F1/O1) below instead of stopping. Otherwise say
   it awaits Nia's play-test and merge, stop.
-- `recon` -> execute the recon protocol (as defined in
-  `.claude/commands/recon.md`) against the ticket's spec, in this
-  session. Create `ticket/NNNN` from `main` if it does not exist yet.
-  Commit the result file on `ticket/NNNN`, then
-  `git push origin ticket/NNNN` so the result is readable from the
-  chat-side raw-URL channel. Then STOP and say so: the brief phase is
-  chat-side (P1). A ticket with NO recon spec on disk is not an error:
-  the recon phase is inapplicable by construction (intake judged it
-  unnecessary) and status derivation already proceeds past it.
-  `recon.md` itself is unchanged and remains available standalone for
-  any chat-side ad-hoc use.
-- `brief` / `intake` -> name the missing artifact (brief, or recon
-  result), stop. Those stages are chat-side per P1 — this command does
-  not author them.
+- `brief` / `intake` -> name the missing artifact (the lot, or its
+  briefs), stop. The lot RECON, the lot and its briefs are written in the
+  chat session — this command never authors them.
 - `escalated` -> display the open entry's Question and Options and take
   Nia's answer in this session (see Escalation below), then continue the
   chain from where it left off.
 - Eligible for `exec` -> run the `/brief-exec` protocol for each brief in
-  suffix order (e.g. `-a` before `-b`), then run `/verify` for this
-  ticket. When invoking `/review-step` and `/close-step` from within this
-  chain, state explicitly that the invocation is unattended (CA1), so
-  `close-step` skips its approval wait.
+  the order of the ticket's `brief_ids` (A before B), then run `/verify`
+  for this ticket. Every commit goes `/review-step` then `/close-step` in
+  the same turn, exactly as `/brief-exec` states; commits are
+  pre-authorized.
 
 ## Step 2 — verify outcome (V1)
 
@@ -133,7 +120,7 @@ An escalation lives in the ticket it stops, in its `## Escalations`
 section. `tooling/glue/escalation.py` is the only writer of that section;
 never edit it by hand.
 
-1. Write a JSON file with three strings — `context` (what was attempted;
+1. Write, outside the repository, a JSON file with three strings — `context` (what was attempted;
    verdicts quoted verbatim if D1-d), `question` (exactly one precise
    question), `options` (lettered options, or "none proposed") — and run
    `python tooling/glue/escalation.py open TICKET-NNNN <D1-a|b|c|d> <brief letter>`
@@ -147,11 +134,3 @@ never edit it by hand.
 Entries are never edited or deleted once written; an answered entry stays
 in the ticket as its trace. If the session ends first, a later
 `/pipeline TICKET-NNNN` finds the open entry at Step 0 and asks again.
-
-## CA1 — unattended invocations
-
-When this command invokes `/review-step` or `/close-step` as part of the
-chain, it states explicitly that the invocation is unattended (from
-`/pipeline`), so `close-step` knows to skip its normal approval wait and
-commit directly. All other steps of `close-step` (changelog, decisions
-index, message quality) are unchanged.
diff --git a/.claude/commands/review-step.md b/.claude/commands/review-step.md
index bb02794..98096dd 100644
--- a/.claude/commands/review-step.md
+++ b/.claude/commands/review-step.md
@@ -1,14 +1,21 @@
 Review the latest changes (uncommitted diff, last commit if the tree is
 clean, or the commit range given as argument) against the project
-invariants in CLAUDE.md:
+invariants: the Invariants section of the root CLAUDE.md and the
+`## Invariants` section of every `.claude/rules/*.md` file that has one.
 
 For each invariant, state: TOUCHED or NOT TOUCHED by these changes.
 For every TOUCHED invariant, show the relevant code and argue explicitly
-why the invariant still holds. If you cannot argue it convincingly, mark
-it VIOLATION SUSPECTED with the exact lines.
+why the invariant still holds. When the invariant ends with
+`-- enforced by <check>.py`, the full law is that check's docstring: read
+it, and run the check. If you cannot argue it convincingly, mark it
+VIOLATION SUSPECTED with the exact lines.
 
 Also check: does any new code path inject context without going through a
 scoped assembler? Does any new code write canon in response to an AI
 proposal outside `_apply_mutation`? Either is an automatic VIOLATION.
 
 End with a one-line verdict: CLEAN / ATTENTION / VIOLATION.
+
+Then, in the same turn: on CLEAN or ATTENTION, continue to /close-step in
+the same turn and carry every ATTENTION item into its report. On
+VIOLATION, stop and report; do not commit.
diff --git a/.claude/hooks/block-commit-on-main.ps1 b/.claude/hooks/block-commit-on-main.ps1
new file mode 100644
index 0000000..654ace4
--- /dev/null
+++ b/.claude/hooks/block-commit-on-main.ps1
@@ -0,0 +1,16 @@
+# M1 (TICKET-0117). Commits are pre-authorized, so a commit on main must be
+# refused structurally: block-main-push only sees a command naming main.
+# Fail-closed: a branch that cannot be read is refused too.
+$raw = [Console]::In.ReadToEnd()
+try { $in = $raw | ConvertFrom-Json } catch { exit 0 }
+$cmd = "$($in.tool_input.command)"
+if ($cmd -notmatch '\bgit\b[^;&|]*\bcommit\b') { exit 0 }
+$branch = "$(git -C "$env:CLAUDE_PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>$null)".Trim()
+if ($branch -eq '' -or $branch -match '^(main|master)$') {
+  $out = @{ hookSpecificOutput = @{ hookEventName = "PreToolUse"
+            permissionDecision = "deny"
+            permissionDecisionReason = "M1: no commit on main (branch '$branch'). Switch to ticket/NNNN first." } }
+  $out | ConvertTo-Json -Depth 5
+  exit 0
+}
+exit 0
diff --git a/.claude/settings.json b/.claude/settings.json
index 164a0f9..03d76b4 100644
--- a/.claude/settings.json
+++ b/.claude/settings.json
@@ -6,6 +6,9 @@
       "Bash(python tooling/glue/*)",
       "Bash(python -m tooling.verify.run:*)",
       "Bash(git branch:*)",
+      "Bash(git switch:*)",
+      "Bash(git add:*)",
+      "Bash(git commit:*)",
       "Bash(git log:*)",
       "Bash(git fetch origin:*)",
       "Bash(git merge origin/main:*)",
@@ -26,7 +29,8 @@
       { "matcher": "Bash",
         "hooks": [
           { "type": "command", "command": "powershell -NoProfile -File \"$CLAUDE_PROJECT_DIR/.claude/hooks/block-main-push.ps1\"" },
-          { "type": "command", "command": "powershell -NoProfile -File \"$CLAUDE_PROJECT_DIR/.claude/hooks/block-db-in-git.ps1\"" }
+          { "type": "command", "command": "powershell -NoProfile -File \"$CLAUDE_PROJECT_DIR/.claude/hooks/block-db-in-git.ps1\"" },
+          { "type": "command", "command": "powershell -NoProfile -File \"$CLAUDE_PROJECT_DIR/.claude/hooks/block-commit-on-main.ps1\"" }
         ]
       }
     ]
diff --git a/CLAUDE.md b/CLAUDE.md
index 5f0b2d4..0a109c0 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -59,8 +59,9 @@ and `world-engine-schema-changelog.md` — never here.
 
 ## Ticket pipeline (governance)
 
-- **Git (C1):** never push to `main`. Work on a `ticket/NNNN` branch and open
-  a PR. Merge only after a green `/verify` AND Nia's live gate.
+- **Git:** never push to `main`, never commit on it (the `block-main-push`
+  and `block-commit-on-main` hooks refuse both). Work on `ticket/NNNN`, open
+  a PR, merge only after a green `/verify` AND Nia's live gate.
 - **Danger classes (D1):** destructive_data | migration | permanent deletion
   -> human gate, no auto-merge (Nia decides). No automated backup exists;
   `scripts/backup.py` is a manual, deliberate step. db_write alone triggers
@@ -68,38 +69,35 @@ and `world-engine-schema-changelog.md` — never here.
 - **Escalate to Nia only on:** (a) an unspecified user-visible behavior
   change, (b) a destructive/irreversible data operation, (c) an architecture
   change above the ticket's stated `blast_radius`, (d) two consecutive
-  `/verify` failures.
-- **Model lanes (E1):** Opus for intake and escalated architecture decisions;
-  Sonnet for RECON, execution, and verify. `/model opusplan` = plan on Opus,
-  execute on Sonnet.
-- **Protocol gate:** RECON before every brief (report-only, never acts on a
-  finding); every commit touching the engine runs `/review-step` then
-  `/close-step`; a ticket ends with `/verify`. Schema version: `vMAJOR.MINOR`,
-  MINOR two digits, 00-99. Next version: MINOR < 99 -> `vMAJOR.(MINOR+1)`
-  zero-padded; MINOR = 99 -> `v(MAJOR+1).00`. MAJOR counts MINOR overflows
-  and carries no semantic meaning. Published changelog versions are never
-  renumbered. RECON lesson: "RECON: trace every UI-visible field to its
-  storage, including `entity.metadata` JSON keys — grepping columns is not
-  sufficient." Every ticket's Machine-checkable section links
-  `verify/checks/corpus_gate.py`.
-- **Artifact convention — the filename is law.** Tickets, RECONs, and briefs
-  arrive as `.md` files carrying their final real IDs in both filename and
-  content (`TICKET-0010.md`, `RECON-0010.md`, `BRIEF-0010-a.md`); no
-  placeholder resolution step. Nia deposits artifacts into
-  `tooling/tickets|recon|briefs` manually. Tickets keep a `slug:`
-  front-matter field; recon specs and briefs keep a line-1
-  `<!-- slug: ... -->` comment.
-- **Where things live:** `tooling/tickets`, `tooling/recon`,
-  `tooling/briefs`, `tooling/lots`,
-  `tooling/glue` (`next_id.py`, `gen_decisions_index.py`,
-  `escalation.py`), `tooling/verify` (`run.py`, `checks/`,
-  `baselines/`, `results/`), `tooling/standards`
-  (`ARCHITECTURE_DECISIONS.md`, generated `DECISIONS_INDEX.md`,
-  `code_standards.md`), `tooling/improvement/bug_log.jsonl`.
-- **Orchestration:** `/pipeline TICKET-NNNN` chains exec -> verify -> PR to
-  the next human gate; it escalates (D1) into the ticket's own
-  `## Escalations` section, through `escalation.py`. Recon results are
-  pushed at recon time; everything else publishes at Step 3.
+  `/verify` failures. An escalation is an entry of the ticket's own
+  `## Escalations` section, written only by `tooling/glue/escalation.py`.
+- **Planning is chat-side, execution is here.** Decisions, the lot RECON and
+  the lot are made with Nia in the chat (Opus): a lot header in
+  `tooling/lots`, authoritative, plus one brief per commit set in
+  `tooling/briefs`, each embedding the findings and contracts it uses.
+  Claude Code (Sonnet) executes one brief per session, starting with its
+  Mini-RECON; an anchor that does not hold is a STOP.
+- **Commands:** `/brief-exec` runs one brief; `/pipeline TICKET-NNNN` runs
+  every brief, `/verify`, then opens the PR. Every commit goes `/review-step`
+  then `/close-step` in the same turn; commits are pre-authorized and only a
+  VIOLATION verdict stops the chain. Every ticket's Machine-checkable section
+  links `verify/checks/corpus_gate.py`.
+- **Schema version:** `vMAJOR.MINOR`, MINOR two digits, 00-99. Next version:
+  MINOR < 99 -> `vMAJOR.(MINOR+1)` zero-padded; MINOR = 99 -> `v(MAJOR+1).00`.
+  MAJOR counts MINOR overflows and carries no semantic meaning. Published
+  changelog versions are never renumbered.
+- **The filename is law.** Tickets, lots, briefs and amendments carry their
+  final real ID and slug in filename and content (`TICKET-0117-slug.md`,
+  `LOT-0117-slug.md`, `BRIEF-0117-A-slug.md`, `AMENDMENT-0117-01.md`). Nia
+  deposits them in `tooling/tickets|lots|briefs` by hand. Tickets keep a
+  `slug:` front-matter field; briefs a line-1 `<!-- slug: ... -->` comment.
+  An amendment is never named `TICKET-*`, which `pipeline_state.py` globs.
+- **Where things live:** `tooling/tickets`, `tooling/lots`, `tooling/briefs`;
+  `tooling/recon` (archived RECONs of earlier tickets, none written now);
+  `tooling/glue` (`gen_decisions_index.py`, `escalation.py`);
+  `tooling/verify` (`run.py`, `checks/`, `baselines/`, `results/`);
+  `tooling/standards` (`ARCHITECTURE_DECISIONS.md`, generated
+  `DECISIONS_INDEX.md`, `code_standards.md`).
 - This section governs the ticket pipeline itself (process, gating,
   escalation). It does not replace or relax any invariant below — those
   still apply to every change regardless of how it was ticketed.
@@ -433,9 +431,8 @@ schema changelog, never in this tree.
 ```
 WG-Nia/
 ├── .claude/                 # Claude Code session config
-│   ├── commands/            # /pipeline /recon /brief-exec /verify /review-step /close-step
-│   ├── hooks/               # session-start, block-main-push, block-db-in-git (PowerShell)
-│   ├── skills/              # recon, brief, verify-authoring skills
+│   ├── commands/            # /pipeline /brief-exec /verify /review-step /close-step
+│   ├── hooks/               # session-start, block-main-push, block-commit-on-main, block-db-in-git
 │   └── settings.json        # permissions allowlist
 ├── frontend/                 # Svelte + Vite sources; build writes the committed static/ output
 │   ├── src/legacy/           # enumerated legacy-mount registry + sole bridge into legacy
@@ -488,7 +485,7 @@ WG-Nia/
 │   ├── rollback_quarantine.py  # quarantine/restore for runtime entity types (destructive, manual)
 │   └── migrate_*.py         # one idempotent migration per schema step
 ├── tooling/
-│   ├── tickets/, recon/, briefs/  # pipeline artifacts (filename is law)
+│   ├── tickets/, lots/, briefs/  # pipeline artifacts (filename is law); recon/ archived
 │   ├── glue/                # next_id.py, gen_decisions_index.py, escalation.py
 │   ├── standards/           # decision registry, generated index, code_standards.md
 │   ├── verify/              # run.py, checks/, baselines/, results/
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index eed7543..f124b51 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18676,6 +18676,35 @@ arrow to a retired check instead of a rewritten ticket. Rejected: J2-b (no
 trace; a relaunch could not know a question was pending), J1 (keep the
 files and only describe them).
 
+## A COMMIT IS PRE-AUTHORIZED AND REVIEW CHAINS TO CLOSE IN ONE TURN (TICKET-0117) -- A HOOK REFUSES A COMMIT ON `main`; THE RECON STAGE AND ITS SKILLS ARE RETIRED (BRIEF-0117-b, no schema change)
+
+**M1.** `/close-step` commits without waiting for approval, whoever invoked
+it: the « unattended mode » that `/pipeline` announced and `/brief-exec`
+did not is gone, and with it the difference Nia saw between the two.
+`/review-step` ends its verdict by continuing to `/close-step` in the same
+turn on CLEAN or ATTENTION -- ATTENTION items are carried into the close
+report -- and stops only on VIOLATION; a verdict was the place a session
+used to hand the turn back. `settings.json` allows `git switch`, `git add`
+and `git commit`.
+
+Approving every commit was the net that kept a commit off `main`.
+`block-main-push.ps1` refuses only a command that names `main`, so a commit
+on `main` followed by a bare `git push` passed it. The new
+`block-commit-on-main.ps1` reads the branch and refuses a commit on `main`
+or `master`, and on a branch it cannot read (fail-closed).
+
+**L4-L6.** The lot RECON is chat-side and no ticket since TICKET-0090 wrote
+a `tooling/recon/` file: `/recon`, the `recon` skill and `/pipeline`'s
+recon stage are deleted; `/pipeline` derives `brief` from a lot header. The
+`brief` skill described the pre-lot format and promised a backup hook that
+does not exist; the `verify-authoring` skill told a check to open the
+production database. Both are deleted. `tooling/recon/` keeps its files as
+the archive of earlier tickets. The command-file sentinels move from
+`pipeline_state.py`, which judges tickets, to `session_config.py`, which
+owns the session configuration. Rejected: M2 (ATTENTION also stops; more
+stops for the same safety, reactivation: an ATTENTION commit turns out to
+have been a violation).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/checks/pipeline_state.py b/tooling/verify/checks/pipeline_state.py
index 26e037a..53b4e38 100644
--- a/tooling/verify/checks/pipeline_state.py
+++ b/tooling/verify/checks/pipeline_state.py
@@ -1,9 +1,7 @@
 """Structural gate for ticket front-matter conformity (pipeline glue, BRIEF-0004),
-extended by BRIEF-0006-b (TICKET-0006) with two grep-grade sentinel checks:
-`.claude/commands/pipeline.md` must contain both the no-recon-spec
-derivation clause and the post-recon push clause within its Step 1 recon
-branch text, and `.claude/commands/brief-exec.md` must contain the CA1
-relay wiring.
+extended by BRIEF-0006-b (TICKET-0006) with sentinel checks on the
+command files -- moved to `session_config.py` by TICKET-0117 (BRIEF-0117-b),
+which owns the Claude Code session configuration.
 
 No DB. Every tooling/tickets/TICKET-*.md (TEMPLATE.md excluded, its glob
 pattern doesn't match) must carry a parseable YAML front-matter block
@@ -46,9 +44,7 @@ import sys
 
 ROOT = pathlib.Path(__file__).resolve().parents[3]
 TICKETS = ROOT / "tooling" / "tickets"
-PIPELINE_MD = ROOT / ".claude" / "commands" / "pipeline.md"
 RETIRED_CHECKS = ROOT / "tooling" / "verify" / "baselines" / "checks.retired"
-BRIEF_EXEC_MD = ROOT / ".claude" / "commands" / "brief-exec.md"
 
 sys.path.insert(0, str(ROOT / "tooling" / "verify"))
 import run  # noqa: E402 -- reuse run.py's machine_checks/LINK, never a second copy
@@ -59,12 +55,6 @@ ARROW_FLOOR_STATUSES = {"brief", "exec", "verify", "live-gate", "done"}
 MACHINE_HEADER_RE = re.compile(r"^###\s*machine")
 LIVE_HEADER_RE = re.compile(r"^###\s*live")
 
-PIPELINE_MD_SENTINELS = [
-    "A ticket with NO recon spec on disk is not an error",
-    "git push origin ticket/NNNN",
-    "python tooling/glue/escalation.py open TICKET-NNNN",
-]
-BRIEF_EXEC_MD_SENTINEL = "unattended mode (CA1)"
 
 REQUIRED_FIELDS = [
     "id", "title", "type", "status", "created", "model_lane",
@@ -197,25 +187,6 @@ def check_escalations(path: pathlib.Path, text: str) -> None:
              f"'{escalation.RESPONSE_MARKER}' marker(s)")
 
 
-def check_pipeline_md_sentinels() -> None:
-    if not PIPELINE_MD.exists():
-        fail(f"{PIPELINE_MD} not found")
-        return
-    text = PIPELINE_MD.read_text(encoding="utf-8")
-    for sentinel in PIPELINE_MD_SENTINELS:
-        if sentinel not in text:
-            fail(f"{PIPELINE_MD.relative_to(ROOT).as_posix()}: missing sentinel phrase {sentinel!r}")
-
-
-def check_brief_exec_md_sentinel() -> None:
-    if not BRIEF_EXEC_MD.exists():
-        fail(f"{BRIEF_EXEC_MD} not found")
-        return
-    text = BRIEF_EXEC_MD.read_text(encoding="utf-8")
-    if BRIEF_EXEC_MD_SENTINEL not in text:
-        fail(f"{BRIEF_EXEC_MD.relative_to(ROOT).as_posix()}: missing sentinel phrase {BRIEF_EXEC_MD_SENTINEL!r}")
-
-
 def main() -> None:
     if not TICKETS.exists():
         fail(f"{TICKETS} not found")
@@ -227,8 +198,6 @@ def main() -> None:
             check_ticket(path)
 
     check_retired_absent()
-    check_pipeline_md_sentinels()
-    check_brief_exec_md_sentinel()
 
     if FAILURES:
         for msg in FAILURES:
diff --git a/tooling/verify/checks/session_config.py b/tooling/verify/checks/session_config.py
new file mode 100644
index 0000000..470086c
--- /dev/null
+++ b/tooling/verify/checks/session_config.py
@@ -0,0 +1,161 @@
+"""G1 check for TICKET-0117 (BRIEF-0117-b, M1, L4-L6) -- the Claude Code
+session configuration: how a brief is executed, committed and escalated.
+
+Text and JSON only, no DB. Every rule reads a file that must exist -- a
+missing file is a FAILURE, never a skip.
+
+SC1 -- permissions. `.claude/settings.json` parses, and `permissions.allow`
+   holds `Bash(git switch:*)`, `Bash(git add:*)` and `Bash(git commit:*)`:
+   commits are pre-authorized (M1). Prose is matched with its whitespace
+   collapsed, so a phrase may wrap.
+SC2 -- the commit net. `hooks.PreToolUse` has a `Bash` matcher whose
+   commands name `block-main-push.ps1`, `block-db-in-git.ps1` and
+   `block-commit-on-main.ps1`, each present under `.claude/hooks/`;
+   `block-commit-on-main.ps1` reads the branch with `rev-parse --abbrev-ref
+   HEAD`, denies `main|master`, and denies a branch it cannot read.
+SC3 -- the chain. `review-step.md` and `brief-exec.md` each say to
+   continue to /close-step in the same turn; `review-step.md` names
+   VIOLATION as the stop; `close-step.md` commits without waiting for
+   approval and holds neither `Wait for approval` nor `Unattended mode`.
+SC4 -- /pipeline. `pipeline.md` pushes only `ticket/NNNN`, escalates
+   through `tooling/glue/escalation.py`, and holds neither an unattended
+   mode nor a recon stage.
+SC5 -- retired. `.claude/commands/recon.md` and the skills `recon`,
+   `brief` and `verify-authoring` do not exist (L4-L6).
+"""
+from __future__ import annotations
+
+import json
+import pathlib
+import sys
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+CLAUDE_DIR = ROOT / ".claude"
+COMMANDS = CLAUDE_DIR / "commands"
+HOOKS = CLAUDE_DIR / "hooks"
+
+REQUIRED_ALLOW = ("Bash(git switch:*)", "Bash(git add:*)", "Bash(git commit:*)")
+REQUIRED_HOOKS = ("block-main-push.ps1", "block-db-in-git.ps1", "block-commit-on-main.ps1")
+CHAIN_PHRASE = "continue to /close-step in the same turn"
+RETIRED = (
+    COMMANDS / "recon.md",
+    CLAUDE_DIR / "skills" / "recon",
+    CLAUDE_DIR / "skills" / "brief",
+    CLAUDE_DIR / "skills" / "verify-authoring",
+)
+
+FAILURES: list[str] = []
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def read(path: pathlib.Path) -> str:
+    if not path.exists():
+        fail(f"{path.relative_to(ROOT).as_posix()} not found")
+        return ""
+    return path.read_text(encoding="utf-8")
+
+
+def flat(text: str) -> str:
+    """The prose with every run of whitespace made one space: a phrase is
+    found whatever line it wraps on."""
+    return " ".join(text.split())
+
+
+def check_settings() -> None:
+    raw = read(CLAUDE_DIR / "settings.json")
+    if not raw:
+        return
+    try:
+        settings = json.loads(raw)
+    except json.JSONDecodeError as exc:
+        fail(f"SC1: settings.json does not parse: {exc}")
+        return
+    allow = settings.get("permissions", {}).get("allow", [])
+    for entry in REQUIRED_ALLOW:
+        if entry not in allow:
+            fail(f"SC1: permissions.allow lacks {entry!r}")
+    commands = [
+        hook.get("command", "")
+        for group in settings.get("hooks", {}).get("PreToolUse", [])
+        if group.get("matcher") == "Bash"
+        for hook in group.get("hooks", [])
+    ]
+    if not commands:
+        fail("SC2: no PreToolUse Bash hook collected")
+    for name in REQUIRED_HOOKS:
+        if not any(name in command for command in commands):
+            fail(f"SC2: no PreToolUse Bash hook runs {name}")
+        if not (HOOKS / name).exists():
+            fail(f"SC2: .claude/hooks/{name} not found")
+
+
+def check_commit_hook() -> None:
+    text = read(HOOKS / "block-commit-on-main.ps1")
+    if not text:
+        return
+    for needle, why in (
+        ("rev-parse --abbrev-ref HEAD", "does not read the current branch"),
+        ("'^(main|master)$'", "does not deny main or master"),
+        ("$branch -eq ''", "does not deny a branch it cannot read"),
+        ('permissionDecision = "deny"', "never denies"),
+    ):
+        if needle not in text:
+            fail(f"SC2: block-commit-on-main.ps1 {why}")
+
+
+def check_chain() -> None:
+    review = flat(read(COMMANDS / "review-step.md"))
+    brief_exec = flat(read(COMMANDS / "brief-exec.md"))
+    close = flat(read(COMMANDS / "close-step.md"))
+    for name, text in (("review-step.md", review), ("brief-exec.md", brief_exec)):
+        if text and CHAIN_PHRASE not in text:
+            fail(f"SC3: {name} does not say {CHAIN_PHRASE!r}")
+    if review and "On VIOLATION, stop and report" not in review:
+        fail("SC3: review-step.md does not stop on VIOLATION")
+    if close:
+        if "do not wait for approval" not in close:
+            fail("SC3: close-step.md does not commit without approval")
+        for stale in ("Wait for approval", "Unattended mode"):
+            if stale in close:
+                fail(f"SC3: close-step.md still holds {stale!r}")
+
+
+def check_pipeline() -> None:
+    text = flat(read(COMMANDS / "pipeline.md"))
+    if not text:
+        return
+    for needle in ("git push origin ticket/NNNN", "python tooling/glue/escalation.py open TICKET-NNNN"):
+        if needle not in text:
+            fail(f"SC4: pipeline.md lacks {needle!r}")
+    lowered = text.lower()
+    for stale in ("unattended", "recon spec", "recon.md"):
+        if stale in lowered:
+            fail(f"SC4: pipeline.md still holds {stale!r}")
+
+
+def check_retired() -> None:
+    for path in RETIRED:
+        if path.exists():
+            fail(f"SC5: {path.relative_to(ROOT).as_posix()} exists; it was retired")
+
+
+def main() -> int:
+    check_settings()
+    check_commit_hook()
+    check_chain()
+    check_pipeline()
+    check_retired()
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: session_config -- commits pre-authorized behind a no-commit-on-main hook; "
+          "review chains to close in one turn; /pipeline escalates into the ticket")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
````

## Scope OUT

- Any change to `block-main-push.ps1` or `block-db-in-git.ps1`.
- Any permission beyond the three of SC1 (no `git checkout`, `git reset`, broad `git push`).
- Deleting `tooling/recon/` or any RECON file: they are the archive of earlier tickets.
- `next_id.py`, the bug log, `CHANGELOG.md` (C); the module map (D); the invariants, the rule files, SC6 (E).
- Retrying, `/verify`, or the PR flow of `/pipeline` (unchanged).

## Invariants to defend

**Never commit on `main`, never push to it**: approving each commit was the
net; after this brief the hook is, and it denies an unreadable branch too
(fail-closed). **A VIOLATION is never committed**: `/review-step` stops on
it. No canon path, no DB, no player surface is touched.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` fails on a file this brief names, other than the ADAPT case below.
- A named mutation does not turn its rule red.
- Any check of Done means is red for a reason this brief does not list.
- The live hook test lets a commit on `main` through.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry by hand just above the footer, then regenerate the index.
- `pipeline_state.py` fails ONLY with `Machine-checkable arrow 'file_map.py' does not resolve` on a deposited `TICKET-0117-claude-md-restructure.md`: expected until BRIEF-0117-D. Report it; the corpus count is then one lower, with exactly that failure.
- PowerShell prints a parse error for `block-commit-on-main.ps1` in the live test: fix the syntax only (same logic, same four needles SC2 reads), in this commit, and report the change.

REPORT-ONLY:
- Corpus timing; a check that times out under load and passes when rerun alone.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists the files of the embedded diff, `tooling/standards/DECISIONS_INDEX.md`, and the four deletions of step 2.
- `python tooling/verify/checks/session_config.py` -> `PASS: session_config -- commits pre-authorized behind a no-commit-on-main hook; review chains to close in one turn; /pipeline escalates into the ticket`
- `pipeline_state.py`, `escalation_writer.py`, `claude_md_contract.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`session_config.py` exits 1 with the rule named):
  - in `.claude/commands/close-step.md`, `the step. Commits are pre-authorized: do not wait for approval.` -> `the step. Wait for approval before committing.` -> `SC3: close-step.md does not commit without approval` and `SC3: close-step.md still holds 'Wait for approval'`
  - in `.claude/hooks/block-commit-on-main.ps1`, `if ($branch -eq '' -or $branch -match '^(main|master)$') {` -> `if ($branch -match '^(main|master)$') {` -> `SC2: block-commit-on-main.ps1 does not deny a branch it cannot read`
  - in `.claude/commands/brief-exec.md`, `continue to` -> `go on to` -> `SC3: brief-exec.md does not say 'continue to /close-step in the same turn'`
- Live (in a Claude Code session in the project; the hook reads the project's branch): after `git switch main`, `git commit --allow-empty -m test` is denied with `M1: no commit on main`; after `git switch ticket/0117`, the same command commits; then `git reset --soft HEAD~1`.
- `python tooling/verify/checks/corpus_gate.py` -> `146 check(s) discovered, 146 executed, 146 passed` (or the ADAPT count).
- `/review-step` then `/close-step` ran on the commit, in the same turn, without an approval prompt.

## Docs to update

Decision entry « A COMMIT IS PRE-AUTHORIZED AND REVIEW CHAINS TO CLOSE IN ONE TURN (TICKET-0117) … (BRIEF-0117-b, no schema change) » -- in the diff. CLAUDE.md « Ticket pipeline (governance) » -- in the diff. No schema change.
