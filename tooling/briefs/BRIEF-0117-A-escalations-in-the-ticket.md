<!-- slug: escalations-in-the-ticket -->
# BRIEF 0117-A — "An escalation lives in the ticket it stops -- `escalation.py`, the questions archived into their tickets, the pipeline cockpit retired"

Lot: LOT-0117-claude-md-restructure.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any has moved (on `main` at `8aa388e`).

- `git apply --check` of the embedded diff succeeds on a clean `ticket/0117` created from `main`.
- `.claude/commands/pipeline.md:20` -> ``3. A `tooling/questions/QUESTION-TICKET-NNNN.md` exists with an empty``
- `tooling/verify/checks/pipeline_state.py:35` -> `QUESTIONS = ROOT / "tooling" / "questions"`
- `tooling/glue/question_response.py:51` -> `def is_open(path: pathlib.Path) -> bool:`
- `tooling/verify/checks/env_guard.py:17` -> ``exception set (TICKET-0049 escalation, `tooling/questions/``
- `tooling/verify/checks/npc_goal_read.py:67` -> `    # or tooling/pipeline_cockpit/.`
- `.claude/launch.json:12` -> `      "name": "pipeline_cockpit",`
- `tooling/tickets/TICKET-0006-pipeline-second-pass.md:110` and `tooling/tickets/TICKET-0007-cockpit-file-upload.md:51` each end with `-> verify/checks/pipeline_cockpit.py` (0007: followed by ` (extended)`).
- `tooling/questions/` holds exactly the fourteen files of R-07 plus `.gitkeep`; no ticket file contains `## Escalations`.
- No `tooling/glue/escalation.py`, no `tooling/verify/checks/escalation_writer.py`, no `tooling/verify/baselines/checks.retired`.

## Facts carried

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

### R-07 — the QUESTION files [M]
Opened: `ls -a tooling/questions`; each file's headers (`grep -E '^#'`);
`question_response.is_open` over all; `grep -l '~~~~'`;
`grep -il '^### *machine\|^### *live'`.
Finding: fourteen `QUESTION-TICKET-*.md` plus `.gitkeep`. Each maps to
exactly one ticket file (`TICKET-0072` takes two: `-0072.md`, `-0072-2.md`):
0013, 0037, 0044, 0049, 0060, 0064, 0067, 0072 (x2), 0075, 0077, 0082, 0085,
0111. One is open by `is_open`: `QUESTION-TICKET-0075.md`, whose ticket is
`done`. None contains `~~~~`; none has a `### Machine` or `### Live` line;
several hold `#` lines inside code fences and nested `##` headings.
Consequence: archived as fenced `~~~~markdown` blocks, each an answered
entry (C-01); an entry boundary is `### E-NN — `, which no file contains.

### R-08 — who uses question_response.py [M]
Opened: enumeration `grep -rn "pipeline_cockpit\|pipeline cockpit\|question_response\|tooling/questions\|QUESTION-"`
outside tickets, briefs, lots, recon, questions and the decision registry.
Finding: `tooling/pipeline_cockpit/app.py` (imports `list_open_questions`),
`tooling/verify/checks/pipeline_cockpit.py`, `.claude/commands/pipeline.md`,
`.claude/launch.json:12` (a `pipeline_cockpit` launch entry),
`tooling/verify/checks/env_guard.py:17-18` (docstring pointer to
`QUESTION-TICKET-0049.md`), `tooling/verify/checks/npc_goal_read.py:67`
(comment), CLAUDE.md lines 91-104, 491, 498, 502, 559; history only in
`world-engine-schema-changelog.md`, `scripts/migrate_v2_00_connects_to_facts.py`
and two verdict JSONs.
Consequence: A deletes the cockpit with its writer and check, edits the
three live pointers, leaves history as written.

### R-09 — the pipeline cockpit is dormant [M]
Opened: `git log -1 -- tooling/pipeline_cockpit scripts/pipeline_cockpit.py`.
Finding: last change 2026-07-03; CLAUDE.md calls its deposit flow dormant.
Consequence: L1.

### R-10 — two tickets link the retired check [M]
Opened: `tooling/tickets/TICKET-0006-pipeline-second-pass.md:110`,
`TICKET-0007-cockpit-file-upload.md:51`; both `status: live-gate`.
Finding: both arrows name `verify/checks/pipeline_cockpit.py`; deleting the
check turns `pipeline_state.py` red on both (measured in the prototype).
`tooling/verify/baselines/graph_impls.retired` is the precedent of an
append-only retirement record read by a check.
Consequence: `checks.retired` (C-02) instead of rewriting two tickets.

### R-17 — decision entries [M]
Opened: `tooling/verify/checks/decisions_index.py` (`STRICT_HEADER`);
the registry's last 30 lines.
Finding: a new header must match `## … (BRIEF-NNNN[-x][, …], schema vX.YY |
no schema change)` with a lowercase brief letter; entries sit above the
`---` / `*Co-built with Claude, June 2026.*` footer; the index is
regenerated by `python tooling/glue/gen_decisions_index.py`.
Consequence: each brief appends one entry above the footer and regenerates.

### R-19 — corpus baseline [M]
Opened: `python tooling/verify/checks/corpus_gate.py` at `8aa388e`.
Finding: 145 discovered, 145 executed, 145 passed.
Consequence: the counts in each brief's Done means.

### R-20 — the repository's ticket template [M]
Opened: `tooling/tickets/TEMPLATE.md`.
Finding: the pre-lot template (`recon: sonnet`, no `lot_id`, no Decisions
locked, no Amendment log, no `slug:`).
Consequence: A replaces it with the current template plus the
`## Escalations` note.

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

### C-02 — `tooling/verify/baselines/checks.retired`
Produced by: BRIEF-0117-A   Consumed by: `pipeline_state.py` (A), `verify-checks.md` (E)
Signature: comment lines `#`, then one line per retired check,
`<file>|<ticket>`; append-only. First line: `pipeline_cockpit.py|TICKET-0117`.
Return shape: `pipeline_state.retired_checks() -> frozenset[str]` of file
names.
Error and empty cases: the file missing is a FAILURE; a name listed there
that exists under `tooling/verify/checks/` is a FAILURE; an arrow to a
listed name resolves.

## Context

`/pipeline` stops on a D1 trigger by writing `tooling/questions/QUESTION-TICKET-NNNN.md`
and asking in the session; Nia answers in the session and never reads the
folder. J2-a moves the trace into the ticket it stops. L1-L3 remove the
dormant pipeline cockpit and the writer it shared with `/pipeline`. This is
the first of five sequential briefs; B, C, D and E take their diffs on this
one's result.

## Scope IN

1. `git switch -c ticket/0117` from `main` (the `/brief-exec` step 1).
2. Apply the embedded diff (`git apply`). It creates
   `tooling/glue/escalation.py`, `tooling/verify/checks/escalation_writer.py`
   and `tooling/verify/baselines/checks.retired`; rewrites
   `tooling/tickets/TEMPLATE.md`; edits `.claude/commands/pipeline.md`,
   `.claude/launch.json`, `CLAUDE.md`, `tooling/verify/checks/pipeline_state.py`,
   `tooling/verify/checks/env_guard.py` (docstring),
   `tooling/verify/checks/npc_goal_read.py` (comment); appends one entry to
   `tooling/standards/ARCHITECTURE_DECISIONS.md` above its footer.
3. Save the archive script below to a file OUTSIDE the repository (for
   example `$env:TEMP\archive_questions.py`) and run it from the repository
   root with the project interpreter:
   `python $env:TEMP\archive_questions.py .`
   It prints fourteen `QUESTION-… -> TICKET-… E-NN` lines and appends one
   archived entry to each of the thirteen tickets of R-07 (`TICKET-0072`
   gets `E-01` then `E-02`). Do not commit the script.
4. Prove the archive verbatim before deleting anything: save the Verbatim
   proof block below outside the repository and run it from the repository
   root. It must print `verbatim 14`.
5. `git rm -r tooling/questions tooling/pipeline_cockpit scripts/pipeline_cockpit.py tooling/glue/question_response.py tooling/verify/checks/pipeline_cockpit.py`
6. `python tooling/glue/gen_decisions_index.py` (regenerates
   `tooling/standards/DECISIONS_INDEX.md`).
7. One commit: `feat(pipeline): an escalation lives in the ticket it stops; questions folder and pipeline cockpit retired (TICKET-0117, BRIEF-0117-a)`.

### Archive script (copy verbatim; never committed)

```python
"""One-shot, not committed: archives every tooling/questions/QUESTION-*.md
into its ticket's `## Escalations` section, verbatim, then exits.
Run from the repository root: python archive_questions.py <repo-root>"""
import pathlib
import re
import sys

root = pathlib.Path(sys.argv[1]).resolve()
sys.path.insert(0, str(root / "tooling" / "glue"))
import escalation  # noqa: E402

ORDER = [
    "QUESTION-TICKET-0013.md", "QUESTION-TICKET-0037.md", "QUESTION-TICKET-0044.md",
    "QUESTION-TICKET-0049.md", "QUESTION-TICKET-0060.md", "QUESTION-TICKET-0064.md",
    "QUESTION-TICKET-0067.md", "QUESTION-TICKET-0072.md", "QUESTION-TICKET-0072-2.md",
    "QUESTION-TICKET-0075.md", "QUESTION-TICKET-0077.md", "QUESTION-TICKET-0082.md",
    "QUESTION-TICKET-0085.md", "QUESTION-TICKET-0111.md",
]
questions = root / "tooling" / "questions"
on_disk = sorted(p.name for p in questions.glob("QUESTION-*.md"))
if sorted(ORDER) != on_disk:
    sys.exit(f"STOP: questions on disk {on_disk} differ from the archive list")

for name in ORDER:
    source = (questions / name).read_text(encoding="utf-8")
    if "~~~~" in source:
        sys.exit(f"STOP: {name} contains '~~~~'; the archive fence would break")
    ticket_id = re.match(r"QUESTION-(TICKET-\d{4})", name).group(1)
    path = escalation.ticket_path(ticket_id)
    text = path.read_text(encoding="utf-8")
    existing = escalation.entries(text)
    entry_id = f"E-{len(existing) + 1:02d}"
    block = (
        f"### {entry_id} — archived — {name}\n"
        "\n"
        f"{escalation.RESPONSE_MARKER} archived from `tooling/questions/{name}`, "
        "which the ticket pipeline wrote before escalations moved into the ticket. "
        "The file follows verbatim, its own Response included.\n"
        "\n"
        "~~~~markdown\n"
        f"{source.rstrip()}\n"
        "~~~~\n"
    )
    out = text.rstrip("\n") + "\n\n"
    if not existing and escalation.SECTION_HEADER not in text.splitlines():
        out += escalation.SECTION_HEADER + "\n\n"
    path.write_text(out + block, encoding="utf-8", newline="\n")
    print(f"{name} -> {path.name} {entry_id}")
```

### Verbatim proof (copy verbatim; run from the repository root)

```python
import pathlib, re
n = 0
for q in sorted(pathlib.Path("tooling/questions").glob("QUESTION-*.md")):
    tid = re.match(r"QUESTION-(TICKET-\d{4})", q.name).group(1)
    t = next(pathlib.Path("tooling/tickets").glob(tid + "-*.md")).read_text(encoding="utf-8")
    assert "~~~~markdown\n" + q.read_text(encoding="utf-8").rstrip() + "\n~~~~" in t, q.name
    n += 1
print("verbatim", n)
```

### Embedded diff

Applies on `main` at `8aa388e`. It excludes the generated
`DECISIONS_INDEX.md` (step 6), the thirteen ticket files (step 3) and the
deleted files (step 5).

````diff
diff --git a/.claude/commands/pipeline.md b/.claude/commands/pipeline.md
index 9732c8b..a39da1a 100644
--- a/.claude/commands/pipeline.md
+++ b/.claude/commands/pipeline.md
@@ -17,8 +17,8 @@ front-matter, in this precedence order:
    the PR's mergeable state via `gh pr view --json mergeable,mergeStateStatus`.
    `live-gate` + `CONFLICTING` triggers the PR-conflict procedure below
    instead of stopping.
-3. A `tooling/questions/QUESTION-TICKET-NNNN.md` exists with an empty
-   `## Response` section -> `escalated`.
+3. The ticket's own `## Escalations` section holds an open entry
+   (`tooling/glue/escalation.py`'s `open_entries`) -> `escalated`.
 4. Brief file(s) `tooling/briefs/BRIEF-NNNN*.md` exist -> eligible for
    `exec`.
 5. A recon result (`tooling/recon/RECON-NNNN*.result.md`) exists ->
@@ -53,8 +53,9 @@ observes and records.
 - `brief` / `intake` -> name the missing artifact (brief, or recon
   result), stop. Those stages are chat-side per P1 — this command does
   not author them.
-- `escalated` with a filled `## Response` -> resume applying the
-  response, then continue the chain from where it left off.
+- `escalated` -> display the open entry's Question and Options and take
+  Nia's answer in this session (see Escalation below), then continue the
+  chain from where it left off.
 - Eligible for `exec` -> run the `/brief-exec` protocol for each brief in
   suffix order (e.g. `-a` before `-b`), then run `/verify` for this
   ticket. When invoking `/review-step` and `/close-step` from within this
@@ -70,8 +71,7 @@ observes and records.
     outside the brief's stated perimeter). Set `retry_count: 1`.
     Re-run `/verify`.
   - If still red after that retry, OR if any D1 (a/b/c/d) trigger fires
-    at any point in the chain: write the QUESTION file (see below), set
-    `status: escalated`, stop.
+    at any point in the chain: escalate (see Escalation below).
 
 ## Step 3 — open the PR (PR1)
 
@@ -93,7 +93,7 @@ On `live-gate` with a CONFLICTING PR:
 2. List conflicted paths: `git diff --name-only --diff-filter=U`.
 3. If ANY conflicted path is under `src/`, or is
    `world-engine-schema-changelog.md`, or is `world-engine-schema.md`:
-   `git merge --abort`, escalate (D1) with a QUESTION file citing the
+   `git merge --abort`, escalate (D1) with an entry citing the
    conflicted paths. The machine never resolves semantic or
    version-numbering conflicts (O1).
 4. Otherwise (append-only docs only): resolve
@@ -117,8 +117,8 @@ changed on disk or in git/GitHub.
 
 ## D1 escalation triggers (QF1)
 
-Any of the following writes the QUESTION file below, sets
-`status: escalated`, and stops the chain — nothing else escalates:
+Any of the following escalates and stops the chain — nothing else
+escalates:
 
 - **D1-a** — an unspecified user-visible behavior change.
 - **D1-b** — a destructive/irreversible data operation.
@@ -127,37 +127,26 @@ Any of the following writes the QUESTION file below, sets
 - **D1-d** — two consecutive `/verify` failures (Step 2's retry
   exhausted).
 
-QUESTION file, created at `tooling/questions/QUESTION-TICKET-NNNN.md`
-(verbatim skeleton):
-
-```
-# QUESTION — TICKET-NNNN
-Trigger: <D1-a|b|c|d>
-## Context
-<what was attempted; verdicts quoted verbatim if D1-d>
-## Question
-<exactly one precise question>
-## Options
-<lettered options if the executor sees any; else "none proposed">
-## Response
-<empty — Nia writes here>
-```
-
-The file persists after resolution — it is an append-only trace, never
-deleted or rewritten, even once `## Response` is filled and the chain
-resumes. "Empty `## Response`" is defined by
-`tooling/glue/question_response.py:is_open` (stripped content == `""`) —
-the prose above points at the code; the code is the definition.
-
-After writing the QUESTION file, commit it on `ticket/NNNN` (append-only
-trace) but do NOT push it (the cockpit reads the local tree; chat never
-reads QUESTION files). Then: display the `## Question` and `## Options`
-sections in this session and offer to take the answer here. If Nia
-answers in-session, write it through
-`python tooling/glue/question_response.py answer <file>` (stdin) — the
-single sanctioned writer — commit, and resume the chain immediately,
-without requiring a relaunch. The relaunch path (Step 0 detecting a
-filled `## Response`) remains valid and unchanged.
+## Escalation
+
+An escalation lives in the ticket it stops, in its `## Escalations`
+section. `tooling/glue/escalation.py` is the only writer of that section;
+never edit it by hand.
+
+1. Write a JSON file with three strings — `context` (what was attempted;
+   verdicts quoted verbatim if D1-d), `question` (exactly one precise
+   question), `options` (lettered options, or "none proposed") — and run
+   `python tooling/glue/escalation.py open TICKET-NNNN <D1-a|b|c|d> <brief letter>`
+   with that file on stdin. It prints the new entry's id (`E-NN`).
+2. Set `status: escalated`, commit the ticket on `ticket/NNNN` (do not
+   push), and display the entry's Question and Options in this session.
+3. When Nia answers, write her answer verbatim with
+   `python tooling/glue/escalation.py answer TICKET-NNNN E-NN` (answer on
+   stdin), commit, and resume the chain immediately.
+
+Entries are never edited or deleted once written; an answered entry stays
+in the ticket as its trace. If the session ends first, a later
+`/pipeline TICKET-NNNN` finds the open entry at Step 0 and asks again.
 
 ## CA1 — unattended invocations
 
diff --git a/.claude/launch.json b/.claude/launch.json
index d807414..ac81bd7 100644
--- a/.claude/launch.json
+++ b/.claude/launch.json
@@ -7,13 +7,6 @@
       "runtimeArgs": ["-c", "import sys; sys.path.insert(0, 'src'); import uvicorn; from world_engine.cockpit.app import app; uvicorn.run(app, host='127.0.0.1', port=8001)"],
       "port": 8001,
       "autoPort": false
-    },
-    {
-      "name": "pipeline_cockpit",
-      "runtimeExecutable": "python",
-      "runtimeArgs": ["-c", "import sys; sys.path.insert(0, '.'); import uvicorn; from tooling.pipeline_cockpit.app import app; uvicorn.run(app, host='127.0.0.1', port=8100)"],
-      "port": 8100,
-      "autoPort": false
     }
   ]
 }
diff --git a/CLAUDE.md b/CLAUDE.md
index 56bbeb1..5f0b2d4 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -88,22 +88,18 @@ and `world-engine-schema-changelog.md` — never here.
   placeholder resolution step. Nia deposits artifacts into
   `tooling/tickets|recon|briefs` manually. Tickets keep a `slug:`
   front-matter field; recon specs and briefs keep a line-1
-  `<!-- slug: ... -->` comment. The pipeline cockpit's deposit flow is
-  dormant (see ARCHITECTURE_DECISIONS.md) — never route artifacts through
-  it.
+  `<!-- slug: ... -->` comment.
 - **Where things live:** `tooling/tickets`, `tooling/recon`,
-  `tooling/briefs`, `tooling/questions` (pipeline escalations),
+  `tooling/briefs`, `tooling/lots`,
   `tooling/glue` (`next_id.py`, `gen_decisions_index.py`,
-  `question_response.py`), `tooling/verify` (`run.py`, `checks/`,
+  `escalation.py`), `tooling/verify` (`run.py`, `checks/`,
   `baselines/`, `results/`), `tooling/standards`
   (`ARCHITECTURE_DECISIONS.md`, generated `DECISIONS_INDEX.md`,
-  `code_standards.md`), `tooling/improvement/bug_log.jsonl`,
-  `tooling/pipeline_cockpit/` (separate app, port 8100, never imports
-  `src/world_engine/`; deposit flow dormant).
+  `code_standards.md`), `tooling/improvement/bug_log.jsonl`.
 - **Orchestration:** `/pipeline TICKET-NNNN` chains exec -> verify -> PR to
-  the next human gate; `tooling/questions/` is where it escalates (D1) for
-  Nia's response. Recon results are pushed at recon time; everything else
-  publishes at Step 3.
+  the next human gate; it escalates (D1) into the ticket's own
+  `## Escalations` section, through `escalation.py`. Recon results are
+  pushed at recon time; everything else publishes at Step 3.
 - This section governs the ticket pipeline itself (process, gating,
   escalation). It does not replace or relax any invariant below — those
   still apply to every change regardless of how it was ticketed.
@@ -488,18 +484,15 @@ WG-Nia/
 │   ├── talk.py              # CLI conversation with an NPC
 │   ├── analyze_conversation.py  # manual window analysis of a conversation
 │   ├── cockpit.py           # launch the world cockpit
-│   ├── pipeline_cockpit.py  # launch the pipeline cockpit (port 8100; deposit dormant)
 │   ├── backup.py            # manual DB backup, 2-file rotation
 │   ├── rollback_quarantine.py  # quarantine/restore for runtime entity types (destructive, manual)
 │   └── migrate_*.py         # one idempotent migration per schema step
 ├── tooling/
 │   ├── tickets/, recon/, briefs/  # pipeline artifacts (filename is law)
-│   ├── questions/           # pipeline escalations awaiting Nia
-│   ├── glue/                # next_id.py, gen_decisions_index.py, question_response.py
+│   ├── glue/                # next_id.py, gen_decisions_index.py, escalation.py
 │   ├── standards/           # decision registry, generated index, code_standards.md
 │   ├── verify/              # run.py, checks/, baselines/, results/
-│   ├── improvement/         # bug_log.jsonl
-│   └── pipeline_cockpit/    # deposit UI app (dormant; never imports src/world_engine/)
+│   └── improvement/         # bug_log.jsonl
 ├── world-engine-schema.md   # single authoritative schema; header = current version
 ├── world-engine-schema-changelog.md  # append-only schema log
 ├── CHANGELOG.md             # project changelog
@@ -556,8 +549,6 @@ WG-Nia/
   loopback only; requires Ollama for all AI calls. Turn mechanics, overhearing
   accumulation, window-analysis triggers, batch review and Voyager ordering
   are documented in `tooling/standards/ARCHITECTURE_DECISIONS.md`.
-- **Pipeline cockpit:** `python scripts/pipeline_cockpit.py` -> port 8100.
-  Deposit flow dormant; artifacts are deposited manually.
 - **Frontend build:** `cd frontend`, `npm ci`, `npm run build` -> writes the
   committed output under `src/world_engine/cockpit/static/`. The output is
   versioned on purpose; rebuild and commit after any `frontend/` edit.
diff --git a/tooling/glue/escalation.py b/tooling/glue/escalation.py
new file mode 100644
index 0000000..92c1710
--- /dev/null
+++ b/tooling/glue/escalation.py
@@ -0,0 +1,171 @@
+"""The single writer of a ticket's `## Escalations` section. Stdlib only, UTF-8.
+
+An escalation lives in the ticket it stops, never in a separate file: a
+`### E-NN — <trigger> — <brief>` entry appended at the end of the ticket's
+`## Escalations` section, the section created at the end of the file if
+the ticket has none. Entries are appended and answered, never rewritten or
+deleted -- history is sacred.
+
+The machine definition of an open escalation: the text after the entry's
+`**Response:**` marker, up to the next entry header or the end of the file,
+strips to "". `/pipeline` derives `status: escalated` from it and
+`pipeline_state.py` imports it -- neither restates it.
+
+CLI (the only way /pipeline writes the section):
+    python tooling/glue/escalation.py open TICKET-NNNN D1-x <brief>  < body.json
+    python tooling/glue/escalation.py answer TICKET-NNNN E-NN          < text
+    python tooling/glue/escalation.py list
+`body.json` holds `context`, `question` and `options`, each a string.
+"""
+from __future__ import annotations
+
+import json
+import pathlib
+import re
+import sys
+
+ROOT = pathlib.Path(__file__).resolve().parents[2]
+TICKETS = ROOT / "tooling" / "tickets"
+
+SECTION_HEADER = "## Escalations"
+RESPONSE_MARKER = "**Response:**"
+TRIGGERS = ("D1-a", "D1-b", "D1-c", "D1-d")
+ENTRY_RE = re.compile(r"^### (E-(\d{2})) — (.+)$")
+
+
+class EscalationError(Exception):
+    """A refused write: unknown ticket or entry, bad trigger, filled response."""
+
+
+def _section_start(lines: list[str]) -> int | None:
+    for i, line in enumerate(lines):
+        if line.strip() == SECTION_HEADER:
+            return i
+    return None
+
+
+def entries(text: str) -> list[dict]:
+    """Every entry of the section, in file order: `id`, `title`, `response`.
+
+    `response` is the stripped text after the marker up to the next entry
+    header or the end of the file; "" when the marker is absent."""
+    lines = text.splitlines()
+    start = _section_start(lines)
+    if start is None:
+        return []
+    found: list[dict] = []
+    current: dict | None = None
+    body: list[str] = []
+    for line in lines[start + 1:]:
+        m = ENTRY_RE.match(line)
+        if m:
+            if current is not None:
+                current["response"] = _response(body)
+                found.append(current)
+            current, body = {"id": m.group(1), "title": m.group(3)}, []
+        elif current is not None:
+            body.append(line)
+    if current is not None:
+        current["response"] = _response(body)
+        found.append(current)
+    return found
+
+
+def _response(body: list[str]) -> str:
+    for i, line in enumerate(body):
+        if line.startswith(RESPONSE_MARKER):
+            rest = [line[len(RESPONSE_MARKER):]] + body[i + 1:]
+            return "\n".join(rest).strip()
+    return ""
+
+
+def open_entries(text: str) -> list[str]:
+    """The ids of the entries whose response is empty."""
+    return [e["id"] for e in entries(text) if e["response"] == ""]
+
+
+def ticket_path(ticket_id: str) -> pathlib.Path:
+    matches = sorted(TICKETS.glob(f"{ticket_id}-*.md"))
+    if len(matches) != 1:
+        raise EscalationError(f"{ticket_id}: {len(matches)} ticket files match, expected 1")
+    return matches[0]
+
+
+def append_entry(path: pathlib.Path, trigger: str, brief: str, body: dict) -> str:
+    """Appends one open entry and returns its id (E-01, E-02, ...)."""
+    if trigger not in TRIGGERS:
+        raise EscalationError(f"trigger {trigger!r} is not one of {TRIGGERS}")
+    for key in ("context", "question", "options"):
+        if not str(body.get(key, "")).strip():
+            raise EscalationError(f"body has no {key!r}")
+    text = path.read_text(encoding="utf-8")
+    numbers = [int(e["id"][2:]) for e in entries(text)]
+    entry_id = f"E-{(max(numbers) if numbers else 0) + 1:02d}"
+    block = [
+        f"### {entry_id} — {trigger} — {brief}",
+        "",
+        "**Context:**",
+        str(body["context"]).strip(),
+        "",
+        "**Question:**",
+        str(body["question"]).strip(),
+        "",
+        "**Options:**",
+        str(body["options"]).strip(),
+        "",
+        RESPONSE_MARKER,
+    ]
+    out = text.rstrip("\n") + "\n\n"
+    if _section_start(text.splitlines()) is None:
+        out += SECTION_HEADER + "\n\n"
+    path.write_text(out + "\n".join(block) + "\n", encoding="utf-8", newline="\n")
+    return entry_id
+
+
+def write_response(path: pathlib.Path, entry_id: str, answer: str) -> None:
+    """Writes `answer` after the marker of an open entry; nothing else moves."""
+    if not answer.strip():
+        raise EscalationError("empty answer")
+    text = path.read_text(encoding="utf-8")
+    known = {e["id"]: e for e in entries(text)}
+    if entry_id not in known:
+        raise EscalationError(f"{path.name}: no entry {entry_id}")
+    if known[entry_id]["response"]:
+        raise EscalationError(f"{path.name}: {entry_id} is already answered")
+    lines = text.splitlines()
+    start = _section_start(lines)
+    in_entry = False
+    for i in range(start + 1, len(lines)):
+        m = ENTRY_RE.match(lines[i])
+        if m:
+            in_entry = m.group(1) == entry_id
+        elif in_entry and lines[i].startswith(RESPONSE_MARKER):
+            lines[i] = RESPONSE_MARKER
+            lines.insert(i + 1, answer.strip())
+            break
+    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
+
+
+def _main(argv: list[str]) -> int:
+    try:
+        if argv[:1] == ["list"] and len(argv) == 1:
+            for path in sorted(TICKETS.glob("TICKET-*.md")):
+                for entry_id in open_entries(path.read_text(encoding="utf-8")):
+                    print(f"{path.name} {entry_id}")
+            return 0
+        if argv[:1] == ["open"] and len(argv) == 4:
+            print(append_entry(ticket_path(argv[1]), argv[2], argv[3], json.load(sys.stdin)))
+            return 0
+        if argv[:1] == ["answer"] and len(argv) == 3:
+            write_response(ticket_path(argv[1]), argv[2], sys.stdin.read())
+            return 0
+    except (EscalationError, json.JSONDecodeError) as exc:
+        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
+        return 1
+    print("usage: escalation.py list | open TICKET-NNNN D1-x <brief> | answer TICKET-NNNN E-NN",
+          file=sys.stderr)
+    return 2
+
+
+if __name__ == "__main__":
+    sys.exit(_main(sys.argv[1:]))
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 2f31959..eed7543 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18648,6 +18648,34 @@ sends, per condition, the id of the proposal inserted there (IH1).
 Rejected: IB2 (a panel in the Lore shell: detached from the offer it
 changes, and a third reopening of 0085's read-only lock).
 
+## AN ESCALATION LIVES IN THE TICKET IT STOPS (TICKET-0117) -- `tooling/questions/`, THE PIPELINE COCKPIT AND ITS QUESTION WRITER ARE RETIRED (BRIEF-0117-a, no schema change)
+
+**J2-a, L1-L3.** `/pipeline` no longer writes a `QUESTION-TICKET-NNNN.md`.
+An escalation is an entry `### E-NN — <trigger> — <brief>` appended to the
+ticket's own `## Escalations` section by `tooling/glue/escalation.py`, the
+section's only writer; Nia answers in the session and the answer is
+written after the entry's `**Response:**` marker. An entry with an empty
+response is open, and an open entry is what makes a ticket `escalated` --
+`pipeline_state.py` imports that definition rather than restating it.
+Entries are appended and answered, never edited or deleted.
+
+The fourteen files of `tooling/questions/` were archived verbatim, each as
+an answered entry of its own ticket (`TICKET-0072` holds two), then the
+folder was deleted. The pipeline cockpit (`tooling/pipeline_cockpit/`,
+`scripts/pipeline_cockpit.py`, its check) and `question_response.py` were
+deleted with it: the cockpit's deposit flow had been dormant since July and
+its questions surface had nothing left to read. Nia's call (L): a dormant
+tool that can mislead is removed, not kept against a plausible
+reactivation. Older entries of this registry and of the schema changelog
+still name those paths; they are history and stay as written.
+
+A retired check is recorded in `tooling/verify/baselines/checks.retired`
+(the `graph_impls.retired` precedent): `TICKET-0006` and `TICKET-0007` keep
+their arrows to `pipeline_cockpit.py`, and `pipeline_state.py` accepts an
+arrow to a retired check instead of a rewritten ticket. Rejected: J2-b (no
+trace; a relaunch could not know a question was pending), J1 (keep the
+files and only describe them).
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/tickets/TEMPLATE.md b/tooling/tickets/TEMPLATE.md
index b0f7c49..9dd5a93 100644
--- a/tooling/tickets/TEMPLATE.md
+++ b/tooling/tickets/TEMPLATE.md
@@ -4,22 +4,62 @@ title:
 type:                 # feature | bug
 status: intake        # intake|recon|brief|exec|verify|live-gate|done|paused|escalated
 created:
-model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
+model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
+                      # recon is the lot RECON, run in the chat session.
+                      # The per-brief Mini-RECON is the first move of exec.
 danger_class: []      # any of: db_write, migration, destructive_data
 blast_radius:         # small | medium | large
-brief_ids: []
+lot_id:               # LOT-NNNN-slug.md — authoritative on conflict with a brief
+brief_ids: []         # letters in execution order, e.g. [A, B, C, D, E]
+current_brief:        # letter in flight, or empty
 schema_version_touched:
-retry_count: 0        # D1(d): 2 consecutive verify failures -> escalate
+retry_count: 0        # 2 consecutive verify failures on the SAME brief -> escalate
+                      # reset to 0 when a brief lands
+slug:
 ---
 
 ## Request (verbatim, as Nia stated it)
 
 ## Clarifications resolved (intake)
 
+## Decisions locked (do not re-litigate without Nia)
+
+<!-- Settled in the planning conversation, before any brief was drafted. These
+     outlive the lot: an amendment replaces contracts and RECON findings, never
+     these. One line each; include the reason only where the reason is what makes
+     the decision load-bearing. -->
+
+- 
+
+## Carried forward / open
+
+<!-- Ordered by how much they block. Each: what is undecided, the options put to
+     Nia, and whether it deserves its own ticket. An item touching an invariant
+     gets a ticket rather than a line in a brief. -->
+
+- 
+
 ## Acceptance criteria
 
+<!-- The living gate for the whole ticket. The "Done means" of each brief are
+     intermediate observables and do not replace this section; an amendment may
+     change a brief's Done means without touching anything here. -->
+
 ### Machine-checkable  ->  G1 deterministic gate
 - [ ] <criterion>  -> verify/checks/<name>.py
 
 ### Live  ->  human gate (Nia)
 - [ ] <criterion>
+
+## Amendment log
+
+<!-- Index only, appended and never rewritten. The content of each amendment
+     lives in AMENDMENT-NNNN-NN.md and its effect is applied to the lot header. -->
+
+| id | brief in flight | what deviated | downstream briefs regenerated |
+|----|-----------------|---------------|-------------------------------|
+|    |                 |               |                               |
+
+<!-- ## Escalations is created at the end of the ticket by
+     `python tooling/glue/escalation.py open ...` the first time /pipeline
+     escalates. Never write it by hand. -->
diff --git a/tooling/verify/baselines/checks.retired b/tooling/verify/baselines/checks.retired
new file mode 100644
index 0000000..d24bd1b
--- /dev/null
+++ b/tooling/verify/baselines/checks.retired
@@ -0,0 +1,7 @@
+# TICKET-0117 (L1). Append-only record of every verify check ever retired
+# from tooling/verify/checks/: one line per check, `<file>|<ticket>`, the
+# ticket being the one whose commit deleted it. A check enters this file in
+# the same commit that deletes it, and is never removed or edited afterward.
+# tooling/verify/checks/pipeline_state.py accepts an older ticket's arrow to
+# a check named here, and fails if a check named here exists again.
+pipeline_cockpit.py|TICKET-0117
diff --git a/tooling/verify/checks/env_guard.py b/tooling/verify/checks/env_guard.py
index d8d0f46..bf46aaf 100644
--- a/tooling/verify/checks/env_guard.py
+++ b/tooling/verify/checks/env_guard.py
@@ -14,8 +14,8 @@ that import in module top-level order, the script either:
 
 Scripts that don't import the engine are out of scope (skipped, not
 failed). `KNOWN_OPERATOR_SCRIPT_ALLOW` below is the single declared
-exception set (TICKET-0049 escalation, `tooling/questions/
-QUESTION-TICKET-0049.md`, Nia 2026-07-27, option A): one-shot migrations,
+exception set (TICKET-0049's escalation E-01, in that ticket's
+`## Escalations` section, Nia 2026-07-27, option A): one-shot migrations,
 one-shot ticket-apply scripts, and standing operator tools that predate
 this ticket and are no longer in active use — allow-listed rather than
 retrofitted, by Nia's explicit call. Extending this list requires the same
diff --git a/tooling/verify/checks/escalation_writer.py b/tooling/verify/checks/escalation_writer.py
new file mode 100644
index 0000000..0890c5f
--- /dev/null
+++ b/tooling/verify/checks/escalation_writer.py
@@ -0,0 +1,118 @@
+"""G1 check for TICKET-0117 (BRIEF-0117-a, J2-a) -- an escalation lives in
+the ticket it stops, written only by `tooling/glue/escalation.py`.
+
+Runs the writer against a scratch ticket in a temporary directory (its
+`TICKETS` constant is pointed there), never against a real ticket.
+
+EW1 -- open. The first `append_entry` on a ticket with no section creates
+   `## Escalations` at the end of the file and appends `E-01`; a second
+   appends `E-02`; everything above the section is byte-identical to the
+   ticket before the first write; both entries are open.
+EW2 -- answer. `write_response` on `E-01` leaves only `E-02` open and
+   stores the answer verbatim; answering `E-01` again, an unknown id, or
+   with an empty answer raises `EscalationError` and changes nothing.
+EW3 -- refusals. A trigger outside `TRIGGERS`, and a body missing
+   `question`, raise `EscalationError` and change nothing.
+EW4 -- the one parser. `pipeline_state.py` imports `escalation` and calls
+   `open_entries(`; it holds no `**Response:**` literal of its own.
+
+Every rule judges at least one concrete entry or file -- a rule that
+collects nothing is a FAILURE.
+"""
+from __future__ import annotations
+
+import pathlib
+import sys
+import tempfile
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+sys.path.insert(0, str(ROOT / "tooling" / "glue"))
+import escalation  # noqa: E402
+
+PIPELINE_STATE = ROOT / "tooling" / "verify" / "checks" / "pipeline_state.py"
+TICKET_TEXT = (
+    "---\nid: TICKET-9999\nstatus: exec\n---\n\n## Request\n\nA scratch ticket.\n\n"
+    "## Acceptance criteria\n\n### Machine-checkable\n- [ ] x  -> verify/checks/x.py\n\n"
+    "### Live\n- [ ] y\n"
+)
+BODY = {"context": "Tried the brief.", "question": "Which one?", "options": "A. this\nB. that"}
+
+FAILURES: list[str] = []
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def refused(call) -> bool:
+    try:
+        call()
+    except escalation.EscalationError:
+        return True
+    return False
+
+
+def check_writer(tmp: pathlib.Path) -> None:
+    escalation.TICKETS = tmp
+    path = tmp / "TICKET-9999-scratch.md"
+    path.write_text(TICKET_TEXT, encoding="utf-8")
+    first = escalation.append_entry(escalation.ticket_path("TICKET-9999"), "D1-a", "B", BODY)
+    second = escalation.append_entry(path, "D1-d", "C", BODY)
+    text = path.read_text(encoding="utf-8")
+    if (first, second) != ("E-01", "E-02"):
+        fail(f"EW1: ids are {(first, second)}, expected ('E-01', 'E-02')")
+    if not text.startswith(TICKET_TEXT.rstrip("\n")):
+        fail("EW1: the ticket above the section changed")
+    if text.count(escalation.SECTION_HEADER) != 1:
+        fail(f"EW1: {text.count(escalation.SECTION_HEADER)} section headers, expected 1")
+    if escalation.open_entries(text) != ["E-01", "E-02"]:
+        fail(f"EW1: open entries are {escalation.open_entries(text)}")
+
+    escalation.write_response(path, "E-01", "  B, with the caveat.  ")
+    text = path.read_text(encoding="utf-8")
+    if escalation.open_entries(text) != ["E-02"]:
+        fail(f"EW2: open entries after an answer are {escalation.open_entries(text)}")
+    answered = {e["id"]: e["response"] for e in escalation.entries(text)}
+    if answered.get("E-01") != "B, with the caveat.":
+        fail(f"EW2: E-01's response is {answered.get('E-01')!r}")
+    for label, call in (
+        ("a second answer", lambda: escalation.write_response(path, "E-01", "again")),
+        ("an unknown id", lambda: escalation.write_response(path, "E-07", "x")),
+        ("an empty answer", lambda: escalation.write_response(path, "E-02", "  ")),
+        ("an unknown trigger", lambda: escalation.append_entry(path, "D2-a", "B", BODY)),
+        ("a body without a question",
+         lambda: escalation.append_entry(path, "D1-a", "B", {"context": "x", "options": "y"})),
+    ):
+        if not refused(call):
+            fail(f"EW2/EW3: {label} was not refused")
+        if path.read_text(encoding="utf-8") != text:
+            fail(f"EW2/EW3: {label} changed the ticket")
+            text = path.read_text(encoding="utf-8")
+
+
+def check_one_parser() -> None:
+    if not PIPELINE_STATE.exists():
+        fail("EW4: pipeline_state.py not found")
+        return
+    source = PIPELINE_STATE.read_text(encoding="utf-8")
+    if "import escalation" not in source or "open_entries(" not in source:
+        fail("EW4: pipeline_state.py does not use escalation.open_entries")
+    if "**Response:**" in source:
+        fail("EW4: pipeline_state.py restates the response marker")
+
+
+def main() -> int:
+    with tempfile.TemporaryDirectory() as tmp:
+        check_writer(pathlib.Path(tmp))
+    check_one_parser()
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: escalation_writer -- an escalation is appended to and answered in its "
+          "own ticket, by one writer, and read by one parser")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/npc_goal_read.py b/tooling/verify/checks/npc_goal_read.py
index 9dfecf5..2319933 100644
--- a/tooling/verify/checks/npc_goal_read.py
+++ b/tooling/verify/checks/npc_goal_read.py
@@ -63,8 +63,7 @@ ALLOWED_MODULES = {
     # NpcGoal rows to build its own test corpus. Allowlisted by name, one
     # entry, on the precedent of npc_goal_read.py's own entry above — not
     # as a directory-wide rule, and NOT by narrowing the tooling/ scan,
-    # which is what would catch a real reader appearing in tooling/glue/
-    # or tooling/pipeline_cockpit/.
+    # which is what would catch a real reader appearing in tooling/glue/.
     "tooling/verify/checks/observation_runner.py",
     # TICKET-0075/BRIEF-0075-c (M4): the occupation-matching rung reads
     # STANDING goals ONLY (`kind='standing'`, reached through
diff --git a/tooling/verify/checks/pipeline_state.py b/tooling/verify/checks/pipeline_state.py
index b610fd9..26e037a 100644
--- a/tooling/verify/checks/pipeline_state.py
+++ b/tooling/verify/checks/pipeline_state.py
@@ -9,7 +9,20 @@ No DB. Every tooling/tickets/TICKET-*.md (TEMPLATE.md excluded, its glob
 pattern doesn't match) must carry a parseable YAML front-matter block
 containing every TEMPLATE.md field; `status` must be a literal member of
 TEMPLATE.md's enum; `retry_count` an integer in 0-2; and a
-`status: escalated` ticket must have a matching QUESTION file.
+`status: escalated` ticket must hold an open entry in its own
+`## Escalations` section.
+
+TICKET-0117 (J2-a). Escalations live in the ticket they stop. The
+section's shape is asserted here with `tooling/glue/escalation.py`'s own
+parser, imported, never a second copy (the same reason `run.py` is
+imported below): its entries are numbered E-01, E-02, ... in file order
+with no gap, each carries exactly one response marker, and a
+section that holds no entry is a FAILURE.
+
+TICKET-0117 (L1). A retired check is recorded in
+`tooling/verify/baselines/checks.retired`; an older ticket's arrow to it
+still resolves, so history is never rewritten to follow a retirement. A
+check named there that exists again on disk is a FAILURE.
 
 TICKET-0061 (E1). TICKET-0061 itself was authored with `## Done means` --
 the brief template's section name -- instead of the ticket template's
@@ -26,18 +39,21 @@ actually do, and a second copy of `machine_checks()`/`LINK` would drift
 from the original the same way this ticket's own malformed section drifted
 from the template.
 """
+import functools
 import pathlib
 import re
 import sys
 
 ROOT = pathlib.Path(__file__).resolve().parents[3]
 TICKETS = ROOT / "tooling" / "tickets"
-QUESTIONS = ROOT / "tooling" / "questions"
 PIPELINE_MD = ROOT / ".claude" / "commands" / "pipeline.md"
+RETIRED_CHECKS = ROOT / "tooling" / "verify" / "baselines" / "checks.retired"
 BRIEF_EXEC_MD = ROOT / ".claude" / "commands" / "brief-exec.md"
 
 sys.path.insert(0, str(ROOT / "tooling" / "verify"))
 import run  # noqa: E402 -- reuse run.py's machine_checks/LINK, never a second copy
+sys.path.insert(0, str(ROOT / "tooling" / "glue"))
+import escalation  # noqa: E402 -- the one definition of an open escalation
 
 ARROW_FLOOR_STATUSES = {"brief", "exec", "verify", "live-gate", "done"}
 MACHINE_HEADER_RE = re.compile(r"^###\s*machine")
@@ -46,6 +62,7 @@ LIVE_HEADER_RE = re.compile(r"^###\s*live")
 PIPELINE_MD_SENTINELS = [
     "A ticket with NO recon spec on disk is not an error",
     "git push origin ticket/NNNN",
+    "python tooling/glue/escalation.py open TICKET-NNNN",
 ]
 BRIEF_EXEC_MD_SENTINEL = "unattended mode (CA1)"
 
@@ -58,7 +75,6 @@ STATUS_ENUM = {
     "intake", "recon", "brief", "exec", "verify", "live-gate", "done",
     "paused", "escalated",
 }
-TICKET_ID_RE = re.compile(r"^(TICKET-\d{4})")
 
 FAILURES: list[str] = []
 
@@ -110,10 +126,28 @@ def check_section_shape(path: pathlib.Path, text: str, status: str | None) -> No
             fail(f"{path.name}: status '{status}' has zero Machine-checkable arrows -- a ticket that has been briefed must have criteria")
         for rel in arrows:
             check_path = run.CHECKS / pathlib.Path(rel).name
-            if not check_path.exists():
+            if not check_path.exists() and check_path.name not in retired_checks():
                 fail(f"{path.name}: Machine-checkable arrow '{rel}' does not resolve to an existing file under tooling/verify/checks/")
 
 
+@functools.lru_cache(maxsize=None)
+def retired_checks() -> frozenset[str]:
+    if not RETIRED_CHECKS.exists():
+        fail(f"{RETIRED_CHECKS.relative_to(ROOT).as_posix()} not found")
+        return frozenset()
+    names = set()
+    for line in RETIRED_CHECKS.read_text(encoding="utf-8").splitlines():
+        if line.strip() and not line.startswith("#"):
+            names.add(line.split("|", 1)[0].strip())
+    return frozenset(names)
+
+
+def check_retired_absent() -> None:
+    for name in sorted(retired_checks()):
+        if (run.CHECKS / name).exists():
+            fail(f"{name} is recorded as retired in checks.retired but exists again")
+
+
 def check_ticket(path: pathlib.Path) -> None:
     text = path.read_text(encoding="utf-8")
     block = extract_front_matter(text)
@@ -138,17 +172,29 @@ def check_ticket(path: pathlib.Path) -> None:
         elif not (0 <= int(retry_raw) <= 2):
             fail(f"{path.name}: field 'retry_count' out of range 0-2 ({retry_raw})")
 
-    if status == "escalated":
-        m = TICKET_ID_RE.match(path.stem)
-        if m is None:
-            fail(f"{path.name}: cannot derive TICKET-NNNN id from filename")
-        else:
-            question_path = QUESTIONS / f"QUESTION-{m.group(1)}.md"
-            if not question_path.exists():
-                fail(
-                    f"{path.name}: field 'status' is 'escalated' but "
-                    f"{question_path.relative_to(ROOT).as_posix()} does not exist"
-                )
+    check_escalations(path, text)
+    if status == "escalated" and not escalation.open_entries(text):
+        fail(f"{path.name}: field 'status' is 'escalated' but its '## Escalations' "
+             "section holds no open entry")
+
+
+def check_escalations(path: pathlib.Path, text: str) -> None:
+    lines = [line.strip() for line in text.splitlines()]
+    if escalation.SECTION_HEADER not in lines:
+        return
+    found = escalation.entries(text)
+    if not found:
+        fail(f"{path.name}: '## Escalations' holds no entry")
+        return
+    ids = [entry["id"] for entry in found]
+    want = [f"E-{n:02d}" for n in range(1, len(found) + 1)]
+    if ids != want:
+        fail(f"{path.name}: escalation ids are {ids}, expected {want}")
+    section = text.splitlines()[lines.index(escalation.SECTION_HEADER):]
+    markers = [line for line in section if line.startswith(escalation.RESPONSE_MARKER)]
+    if len(markers) != len(found):
+        fail(f"{path.name}: {len(found)} escalation(s) but {len(markers)} "
+             f"'{escalation.RESPONSE_MARKER}' marker(s)")
 
 
 def check_pipeline_md_sentinels() -> None:
@@ -180,6 +226,7 @@ def main() -> None:
         for path in tickets:
             check_ticket(path)
 
+    check_retired_absent()
     check_pipeline_md_sentinels()
     check_brief_exec_md_sentinel()
 
````

## Scope OUT

- Editing an archived QUESTION text, or an older ticket's arrows: history
  is archived as written; `checks.retired` carries the retirement.
- The historical mentions of the retired paths in
  `ARCHITECTURE_DECISIONS.md`, `world-engine-schema-changelog.md`,
  `scripts/migrate_v2_00_connects_to_facts.py` and
  `tooling/verify/results/*.json`.
- The commit flow, `/close-step`, `/review-step`, `/brief-exec`, the recon
  stage, CA1, `settings.json`, the hooks (BRIEF-0117-B).
- `next_id.py`, the bug log, `CHANGELOG.md` (BRIEF-0117-C); the module map
  (D); the invariants and rule files (E).
- Any change to `tooling/recon/`.

## Invariants to defend

**History is sacred**: every QUESTION file reaches its ticket byte for byte
(step 4 proves it before step 5 deletes); escalation entries are appended
and answered, never rewritten (`escalation.py` refuses a second answer, C-01).
**Fail-closed checks**: `pipeline_state.py` still fails a briefed ticket
whose arrow resolves to nothing, unless the check is recorded as retired; a
retired check that reappears is a FAILURE. No canon path, no DB, no player
surface is touched.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` fails on a file this brief names, other than the ADAPT case below.
- The archive script prints a `STOP:` line, or the verbatim proof does not print `verbatim 14`.
- A named mutation does not turn its rule red.
- Any check of Done means is red for a reason this brief does not list.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry by hand just above the `---` / `*Co-built with Claude, June 2026.*` footer, then regenerate the index.
- `TICKET-0117-claude-md-restructure.md` is deposited in `tooling/tickets/` with a status in `brief/exec/verify/live-gate/done`, and `pipeline_state.py` fails ONLY with `Machine-checkable arrow 'session_config.py'` and/or `'file_map.py' does not resolve` on that ticket: expected until BRIEF-0117-B and -D create them. Report it; the corpus count in Done means is then one lower, with exactly that failure.

REPORT-ONLY:
- Corpus timing; a check that times out under load and passes when rerun alone (name it).
- Line-ending notices from git on the archived tickets.
- `git apply` warns of two trailing-whitespace lines: the template's empty `- ` bullets in `TEMPLATE.md`, as in the project template.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists the files of the embedded diff, the thirteen archived tickets, `tooling/standards/DECISIONS_INDEX.md`, and the 22 deletions of step 5 (14 QUESTION files, `.gitkeep`, four `tooling/pipeline_cockpit/` files, `scripts/pipeline_cockpit.py`, `question_response.py`, the check).
- `python tooling/glue/escalation.py list` prints nothing (every archived entry is answered).
- `python tooling/verify/checks/escalation_writer.py` -> `PASS: escalation_writer -- an escalation is appended to and answered in its own ticket, by one writer, and read by one parser`
- `pipeline_state.py`, `env_guard.py`, `npc_goal_read.py`, `claude_md_contract.py`, `decisions_index.py`, `function_length.py`, `module_budget.py` -> `PASS`.
- Mutation tests, each red then reverted:
  - in `tooling/glue/escalation.py`, `    if known[entry_id]["response"]:` -> `    if False:` -> `escalation_writer.py`: `EW2/EW3: a second answer was not refused`
  - in `tooling/glue/escalation.py`, `    if trigger not in TRIGGERS:` -> `    if trigger is None:` -> `EW2/EW3: an unknown trigger was not refused`
  - in `tooling/tickets/TICKET-0013-npc-goals-in-scene.md`, `### E-01 — archived — QUESTION-TICKET-0013.md` -> `### E-03 — archived — QUESTION-TICKET-0013.md` -> `pipeline_state.py`: `escalation ids are ['E-03'], expected ['E-01']`
  - in `tooling/tickets/TICKET-0111-condition-language.md`, `status: intake` -> `status: escalated` -> `pipeline_state.py`: `field 'status' is 'escalated' but its '## Escalations' section holds no open entry`
  - in `tooling/verify/baselines/checks.retired`, delete the line `pipeline_cockpit.py|TICKET-0117` -> `pipeline_state.py`: `TICKET-0006-pipeline-second-pass.md: Machine-checkable arrow 'pipeline_cockpit.py' does not resolve`
- `$env:WORLD_ENGINE_ENV="test"; python tooling/verify/checks/corpus_gate.py` -> `145 check(s) discovered, 145 executed, 145 passed` (or the ADAPT count).
- `/review-step` then `/close-step` ran on the commit, in the same turn.

## Docs to update

Decision entry « AN ESCALATION LIVES IN THE TICKET IT STOPS (TICKET-0117) … (BRIEF-0117-a, no schema change) » -- in the diff. `CLAUDE.md` pipeline lines and tree -- in the diff. `tooling/tickets/TEMPLATE.md` -- in the diff. No schema change.
