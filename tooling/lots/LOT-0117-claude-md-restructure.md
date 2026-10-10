# LOT — TICKET-0117 "The instruction corpus split by where it holds, and the pipeline as practised"

## Objective and cut

CLAUDE.md stood at 37 202 characters of its 38 000 budget and 572 lines,
loaded whole into every Claude Code session, while parts of the pipeline it
described had stopped being true. This lot makes the instruction corpus fit
what a session needs and the process match how Nia works:

- an escalation lives in the ticket it stops (J2-a); the questions folder,
  the pipeline cockpit and their writer go (L1-L3);
- commits are pre-authorized and `/review-step` chains to `/close-step` in
  one turn, behind a hook that refuses a commit on `main` (M1); the recon
  stage and the stale skills go (L4-L6);
- `next_id.py`, the bug log and `CHANGELOG.md` go, the bug log archived in
  the ticket first (L7-L9);
- the module tree becomes a generated `FILE_MAP.md` (B1);
- the law is split: transversal invariants stay in CLAUDE.md, local ones go
  to `.claude/rules/<topic>.md` with `paths:`, every invariant gets a
  permanent `INV-NN` and a check or `[no check]` (C1, D1, E1, F1, G1, H1).

The lot stops there. It writes no new invariant and weakens none: only
rationale leaves the active text, archived verbatim in the decision
registry. Reshaping `src/world_engine/` into packages is TICKET-0118 (K1).
Turning `[no check]` invariants into checked ones is left to the tickets
that touch them.

**Prototype.** Every brief below was applied, in order, to a private clone
of `main` at `8aa388e`, and the full corpus run after each: 145, 146, 146,
147 and 147 checks, all green (Linux, Python 3.13). The diffs embedded in
the briefs are those commits. `block-commit-on-main.ps1` could not run
there; its proof is a live gate.

## Briefs in this lot

- **A** `escalations-in-the-ticket` — `tooling/glue/escalation.py`, the
  `## Escalations` section, the fourteen QUESTION files archived into their
  tickets, the questions folder, pipeline cockpit and `question_response.py`
  deleted, `checks.retired`, `escalation_writer.py`.
- **B** `pre-authorized-commits` — `/close-step`, `/review-step`,
  `/brief-exec`, `/pipeline` without unattended mode or recon stage,
  `settings.json`, `block-commit-on-main.ps1`, `/recon` and three skills
  deleted, `session_config.py`; CLAUDE.md's pipeline section rewritten.
- **C** `retire-dead-files` — `next_id.py`, `bug_log.jsonl`, `CHANGELOG.md`;
  the numbering rule rewritten.
- **D** `generated-file-map` — `gen_file_map.py`, `FILE_MAP.md`,
  `file_map.py`, a docstring for `cockpit/__init__.py`.
- **E** `law-split-by-scope` — the new CLAUDE.md, ten rule files, the
  extended `claude_md_contract.py`, `invariant_ids.retired`, `npc_skills.py`
  B4, `session_config.py` SC6, the old invariants archived.

## Dependency graph

Strictly sequential: A -> B -> C -> D -> E, all on `ticket/0117`.

- A before B: both rewrite `.claude/commands/pipeline.md` and
  `tooling/verify/checks/pipeline_state.py`; B's diff is taken on A's
  result.
- B before C, C before D: each edits the lines of CLAUDE.md the previous
  one left (the pipeline section, then the numbering section and the tree,
  then the How to run list).
- D before E: E's CLAUDE.md points at `FILE_MAP.md` and `gen_file_map.py`,
  which the contract's pointer freshness requires to exist.
- Every brief's diff is taken on its predecessor's result: none can run out
  of order.

## RECON

All findings measured on `main` at `8aa388e` unless stated.

### R-01 — CLAUDE.md size [M]
Opened: `CLAUDE.md` (read whole); `python -c "len(open('CLAUDE.md',encoding='utf-8').read())"`.
Finding: 37 202 characters, 572 lines. By section: Invariants 18 324
(261 lines), File structure 5 886 (80 lines), Ticket pipeline 3 071, How to
run 2 373, Local model notes 2 230, the rest 5 318.
Consequence: the budget breaks on the next ticket that adds a module or a
lesson; moving the Invariants and the tree is where the room is.

### R-02 — what the CLAUDE.md contract enforces [M]
Opened: `tooling/verify/checks/claude_md_contract.py` (implementation, 249 lines).
Finding: exact ordered H2 list (`EXPECTED_H2`, eight entries including
`Local model notes`) and H3 list under Conventions; `TOTAL_CHAR_BUDGET =
38_000` on `len(text)`; `MAX_LINE_LENGTH = 100` on every line;
`FILE_STRUCTURE_LINE_BUDGET = 80`; File structure bans `BRIEF-`, `schema v`,
`v\d+\.\d+`; Invariants bans `TICKET-\d`, `BRIEF-\d` and fails on zero `- `
bullets; every `tooling/...` token exists; every `[a-z0-9_]+\.py` token
names a file somewhere in the repo, zero tokens is a FAILURE. It reads
`CLAUDE.md` only.
Consequence: E rewrites it to cover the rule files; A to D keep its current
rules green on every intermediate CLAUDE.md.

### R-03 — two checks read CLAUDE.md's text [M]
Opened: `tooling/verify/checks/npc_skills.py:529-532`;
`tooling/verify/checks/skill_progression.py:611-622`; enumeration
`grep -ln "CLAUDE.md" tooling/verify/checks/*.py` (13 files: these two,
the contract itself, and ten that only name it in docstrings, comments or
messages).
Finding: `npc_skills.check_b4` fails unless CLAUDE.md contains
`requires_master` and `skill_access`; `skill_progression.check_b4` fails
unless it contains `skill_progress`.
Consequence: `skill_progress` stays in the root (INV-15). The skills
invariants move to `skills.md`, so E retargets `npc_skills` B4 there.

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

### R-13 — the dead files [M]
Opened: `tooling/glue/next_id.py`; `tooling/improvement/bug_log.jsonl`
(3 lines, parsed: 2026-07-03 `fixed (BRIEF-0025-d, v1.78)`, 2026-09-01
`open`, 2026-09-01 `open`); `CHANGELOG.md` (`git log -1`: 2026-08-20, five
`## ` entries); enumeration of readers (`grep -rn "next_id\|bug_log\|CHANGELOG.md\|tooling/improvement"`).
Finding: readers are CLAUDE.md:107, 489, 492, 495 and
`tooling/standards/code_standards.md:69, 203` (citations of the 2026-07-03
entry); no code reads any of the three. sha256 at `8aa388e`: `bug_log.jsonl`
`03db3414…80efc965`, `CHANGELOG.md` `21f22329…82d92765`, `next_id.py`
`66d19219…aa8064d`.
Consequence: L7-L9; the bug log is archived verbatim in TICKET-0117 first.

### R-14 — module docstrings [M]
Opened: AST scan of every `*.py` under `src/world_engine`, `scripts`,
`tooling/glue`, `tooling/verify` (`ast.get_docstring`).
Finding: 446 non-empty modules; one without a docstring,
`src/world_engine/cockpit/__init__.py`, whose only line is the comment
`# Cockpit sub-package — local review web UI for World Engine.`
Consequence: B1 is feasible now; D turns that comment into the docstring.

### R-15 — how Claude Code loads instructions [external, M]
Opened: https://code.claude.com/docs/en/memory (2026-10-10).
Finding: CLAUDE.md files above the working directory load at launch; a
`CLAUDE.md` in a subdirectory loads when a file there is read or edited.
`.claude/rules/*.md` files with a `paths:` front-matter list load when the
Read, Write or Edit tool (or a `cat`-style read) touches a matching file;
without `paths:` they load at launch. `@path` imports load at launch. Block
HTML comments are stripped from context. The docs recommend under 200 lines
per file. Observed in the prototype session itself: writing
`tooling/verify/checks/claude_md_contract.py` loaded
`.claude/rules/verify-checks.md`.
Consequence: G1, and the rejection of D3.

### R-16 — enforcement links, read in the checks' implementations [M]
Opened: each check's `fail(` call sites and the code around them.
Finding: carried from CLAUDE.md and confirmed: `single_canon_write.py`
(writes outside `canon_write_policy.txt`, hard deletes in its policy),
`runtime_ddl_guard.py`, `skill_progression.py`, `zone_placement.py` (15
placement outcomes, zones refused), `npc_skills.py`, `prompt_registry.py`,
`prompt_model_write.py` (PATCH outcomes), `prompt_version.py` (no
UPDATE/DELETE), `json_ui_boundary.py`, `page_contract.py`,
`creation_island.py`, `review_component.py`, `graph_primitive.py`,
`creation_tab_switch.py`, `creation_container_sizing.py`,
`effect_self_write.py`, `fact_learning.py` (`B1: Passage( constructed in
{rel}`), `lore_usage.py`. New: `knowledge_identity.py` K1 (`idx_knowledge_entity_fact`
UNIQUE on exactly `(entity_id, fact_id)`), `gathering_lifecycle.py` rules
1-6 (entry guard through `_live_gatherings`, `dissolve_emptied`,
`attach_on_arrival`, `update_entity` calling `close_open_memberships`),
`zone_map_links.py` (a/b/c: `connects_to` to a zone refused, link type
derived, no retype across the pair), `lore_write.py` C1a-C1e (rows recorded
in `lore_entry_row`, a refused write leaves no row).
Every other invariant is `[no check]`: no link was established, which is
not a claim that no check exists.
Consequence: the markers of E (39 `[no check]`, 22 linked).

### R-17 — decision entries [M]
Opened: `tooling/verify/checks/decisions_index.py` (`STRICT_HEADER`);
the registry's last 30 lines.
Finding: a new header must match `## … (BRIEF-NNNN[-x][, …], schema vX.YY |
no schema change)` with a lowercase brief letter; entries sit above the
`---` / `*Co-built with Claude, June 2026.*` footer; the index is
regenerated by `python tooling/glue/gen_decisions_index.py`.
Consequence: each brief appends one entry above the footer and regenerates.

### R-18 — the rule globs [M]
Opened: `pathlib.Path(".").glob(...)` for every planned glob.
Finding (match counts): `analyzer*.py` 2, `tick*.py` 3, `observation_*.py`
5, `day_mutations.py` 1, `cockpit/mutations.py` 1, `cockpit/routes/mutations.py`
1, `writes/knowledge.py` 1, `gathering.py` 1, `encounters.py` 1,
`passages.py` 1, `cockpit/routes/scene.py` 1, `cockpit/crud/entities.py` 1,
`context*.py` 3, `cockpit/play*.py` 5, `scene_format.py` 1, `skill*.py` 3,
`cockpit/crud/skills.py` 1, `prompt_*.py` 5, `cockpit/crud/prompts.py` 1,
`scripts/seed_pilot.py` 1, `frontend/src/**/*.svelte` 71,
`frontend/src/**/*.js` 51, `frontend/public/*.css` 2, `ollama_client.py` 1,
`scripts/talk.py` 1, `tooling/verify/checks/*.py` 146, `scripts/migrate_*.py`
70, `writes/schema.py` 1, `schema_*.py` 2, `scripts/rollback_quarantine.py`
1, `region_author.py` 1, `cockpit/routes/regions.py` 1, `lore_*.py` 13,
`scripts/export_lore_usage.py` 1. `src/world_engine/world_tick.py` matches
nothing (it is a check name) and is not used.
Consequence: every glob of C-05 matches at least one file.

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

## Contract sheet

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
### E-NN — <trigger> — <brief>

**Context:**
<text>

**Question:**
<text>

**Options:**
<text>

**Response:**
<empty, or the answer>
```
An archived entry is `### E-NN — archived — QUESTION-…md`, a
`**Response:** archived from …` line, then the file in a `~~~~markdown`
fence. Response = the stripped text after the marker up to the next
`### E-NN — ` line or EOF; open = "".
Error and empty cases: `EscalationError` for an unknown ticket (not exactly
one file), a trigger outside `TRIGGERS`, a body missing a key or with an
empty value, an unknown entry, an answered entry, an empty answer; nothing
is written. No section -> `entries` returns `[]`. Files are written with
`newline="\n"`.

### C-02 — `tooling/verify/baselines/checks.retired`
Produced by: BRIEF-0117-A   Consumed by: `pipeline_state.py` (A), `verify-checks.md` (E)
Signature: comment lines `#`, then one line per retired check,
`<file>|<ticket>`; append-only. First line: `pipeline_cockpit.py|TICKET-0117`.
Return shape: `pipeline_state.retired_checks() -> frozenset[str]` of file
names.
Error and empty cases: the file missing is a FAILURE; a name listed there
that exists under `tooling/verify/checks/` is a FAILURE; an arrow to a
listed name resolves.

### C-03 — `tooling/verify/checks/session_config.py`
Produced by: BRIEF-0117-B (SC1-SC5), BRIEF-0117-E (SC6)   Consumed by: the ticket's Machine section
Signature: rules SC1-SC6 as in its docstring; prose is matched with its
whitespace collapsed (`flat`).
Return shape: exit 0 with one `PASS: session_config -- …` line, else
`FAIL: SCn: …` lines and exit 1.
Error and empty cases: every file it reads missing is a FAILURE; no
`PreToolUse` Bash hook collected is a FAILURE.

### C-04 — `tooling/glue/gen_file_map.py` and `FILE_MAP.md`
Produced by: BRIEF-0117-D   Consumed by: `file_map.py` (D), CLAUDE.md (D, E), `/close-step` (D)
Signature: `SCOPES = ("src/world_engine", "scripts", "tooling/glue",
"tooling/verify")`; `collect() -> (groups, missing)`; `render(groups) -> str`;
`role(path) -> str | None`.
Return shape: `HEADER`, then per directory (sorted, repo-relative POSIX)
`## <dir>/` and one `- \`<name>\` — <first sentence>` line per module; the
first sentence is the docstring's first paragraph, whitespace collapsed,
cut after the first `.`, `!` or `?` followed by whitespace.
Error and empty cases: an empty file is skipped; a non-empty module without
a docstring is in `missing`, and the CLI exits 1 without writing.

### C-05 — the rule files and the invariant bullets
Produced by: BRIEF-0117-E   Consumed by: `claude_md_contract.py`, `/review-step`, `/close-step`
Signature: `.claude/rules/<topic>.md` opens with
```
---
paths:
  - "<glob>"
---
```
(one or more glob lines, no `{` or `[`), then an H1, optional notes, and an
optional `## Invariants`. An invariant bullet is `- **INV-NN** <law>`,
continuation lines indented two spaces, ending with `-- enforced by
\`<check>.py\`` (comma-separated for several) or `[no check]`.
`tooling/verify/baselines/invariant_ids.retired` holds comment lines and
`INV-NN|<ticket>|<reason>` lines.
Return shape: ids unique over the root and every rule file; live plus
retired = INV-01..max.
Error and empty cases: see `claude_md_contract.py` rules 6 and 7.

### C-06 — budgets
Produced by: BRIEF-0117-E   Consumed by: every later ticket
Root CLAUDE.md <= 22 000 characters (19 767 after E); each rule file <= 4 000
(largest 2 524); 100 characters per line everywhere; File structure <= 30
lines (26 after E).

## Gate output

(a) Property trace — one line per asserted property:
- CLAUDE.md is 37 202 chars / budget is characters -> R-01, R-02, `CLAUDE.md`, `claude_md_contract.py`
- the contract's rules -> R-02, `claude_md_contract.py`
- B4 reads CLAUDE.md for three tokens -> R-03, `npc_skills.py`, `skill_progression.py`
- close-step waits for approval unless unattended; review-step ends on its verdict -> R-04, `close-step.md`, `review-step.md`, `brief-exec.md`
- /pipeline's QUESTION, recon and CA1 machinery -> R-05, `pipeline.md`
- escalated needs a QUESTION file; sentinels; arrow floor; filesystem glob -> R-06, `pipeline_state.py`
- fourteen files, mapping, one open, no `~~~~`, no Machine/Live lines -> R-07, `tooling/questions/*`
- the readers of the QUESTION machinery -> R-08, enumeration pasted in R-08
- tickets 0006/0007 arrow to the check -> R-10, the two ticket files
- no commit permission; push hook regex -> R-11, `settings.json`, `block-main-push.ps1`
- skill contents stale -> R-12, the three `SKILL.md`
- dead files have no code reader; bug log states -> R-13, enumeration and `bug_log.jsonl`
- one module without docstring -> R-14, AST scan
- Claude Code loading -> R-15, the documentation page
- each `-- enforced by` link -> R-16, the check's implementation
- header pattern and footer -> R-17, `decisions_index.py`, the registry
- every glob matches -> R-18, the enumeration pasted there

(b) Case tables.
`escalation.open_entries` over a ticket:

| ticket text | `entries` | `open_entries` |
|---|---|---|
| no `## Escalations` | `[]` | `[]` |
| section, entry with empty response | `[E-01 ""]` | `[E-01]` |
| section, entry answered | `[E-01 "…"]` | `[]` |
| archived entry | `[E-01 "archived from …"]` | `[]` |
| section with no entry | `[]` | `[]` — and `pipeline_state` FAILs |

`pipeline_state` per ticket: status `escalated` with no open entry -> FAIL;
`escalated` with one -> pass; any other status with an open entry -> pass
(rule is one-way, as before); ids not E-01..E-n in order -> FAIL; markers !=
entries -> FAIL; arrow to a missing check -> FAIL unless in `checks.retired`;
a retired name present on disk -> FAIL.

`/pipeline` Step 0, first rule that matches wins: merged -> `done`; green
verdict and PR -> `live-gate`; open escalation -> `escalated`; briefs ->
`exec`; lot header -> `brief`; otherwise `intake`.

`/review-step` verdict: CLEAN -> `/close-step` same turn; ATTENTION ->
`/close-step` same turn, items carried; VIOLATION -> stop, no commit.

`block-commit-on-main.ps1`: no `git … commit` in the command -> allow;
commit on `ticket/NNNN` -> allow; commit on `main` or `master` -> deny;
branch unreadable (empty) -> deny; unparsable hook input -> allow (the
`block-main-push` idiom).

Contract rule 6 per bullet: no `**INV-NN**` head -> FAIL; `-- enforced by`
with every check present -> pass; with one missing -> FAIL; ends `[no check]`
-> pass; neither -> FAIL. Per corpus: duplicate id -> FAIL; id in retired
and live -> FAIL; gap in 1..max -> FAIL; zero bullets -> FAIL.

(c) Enumerations: pasted in R-07, R-08, R-13, R-14, R-16, R-18; the negative
claims « no code reads next_id / bug_log / CHANGELOG » (R-13) and « no file
contains `~~~~` » (R-07) rest on those enumerations.

(d) Family contracts: the entry format (C-01) was written before the
archive, the writer and the parser, and re-read after `pipeline_state.py`'s
use of it; the rule-file format (C-05) before the ten files, re-read after
the last (`verify-checks.md`).

(e) Gates proposed and passed, each with the module that satisfies it:
`escalation_writer.py` <- `escalation.py` (A); `pipeline_state.py` <-
`escalation.py`, `checks.retired` (A); `session_config.py` <- the commands,
`settings.json`, `block-commit-on-main.ps1` (B, E); `file_map.py` <-
`gen_file_map.py`, `FILE_MAP.md`, the cockpit docstring (D);
`claude_md_contract.py` <- CLAUDE.md, the ten rule files,
`invariant_ids.retired` (E); `npc_skills.py` B4 <- `skills.md` (E);
`decisions_index.py` <- one entry per brief and the regenerated index;
`corpus_gate.py` <- all of the above. Gates the lot merely passes:
`env_guard.py`, `npc_goal_read.py` (A edits their docstring/comment),
`function_length.py`, `module_budget.py`, `undefined_names.py` (green in the
prototype after each brief). Known transient red, by construction:
`pipeline_state.py` on a deposited TICKET-0117 in a floor status before B
and D create `session_config.py` and `file_map.py` (ADAPT in A, B, C).

## Amendments

(none)
