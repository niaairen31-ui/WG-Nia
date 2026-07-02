# RECON-0004 — Scaffold ground truth for the /pipeline glue

**REPORT ONLY.** No edit, no fix, no design. Every claim cited `path:line`
(or command output quoted verbatim for infrastructure facts). Blocking
items marked **BLOCKING FINDING**.

Ticket: TICKET-0004. Purpose: the glue brief must anchor on the scaffold
as it exists, not as it was designed. Five zones: command contracts,
front-matter reality, hooks/permissions, git/GitHub infrastructure, glue
seams.

Runtime note: read-only except Zone D's status commands (git/gh reads, no
mutation). PowerShell; venv not needed.

---

## Zone A — Existing command contracts

A1. For each of `.claude/commands/recon.md`, `brief-exec.md`, `verify.md`,
    `review-step.md`, `close-step.md`: report verbatim (quote, `file:line`)
    what input it expects (argument shape), what it produces (files,
    branch, commits), and — critically — whether it reads or writes the
    ticket front-matter `status` field today. The glue design assumes
    /pipeline owns exec→verify→live-gate transitions; if any existing
    command already mutates `status`, that is a double-writer risk —
    report it.

A2. Report whether any command file references another command (chaining
    already exists?) and whether `.claude/commands/*` files can carry
    multi-step orchestration per Claude Code's command format as used in
    this repo (cite how existing commands structure their steps).

A3. Report how a command currently learns "the verify verdict": confirm
    `tooling/verify/results/<TICKET-ID>.json` shape (keys, verdict field)
    as run.py writes it (run.py:44-47, per RECON-0002 Zone E — confirm
    unchanged post-0001/0003 merges).

## Zone B — Ticket front-matter reality vs TEMPLATE.md

B1. For every file in `tooling/tickets/`: report its front-matter fields
    and current `status` value verbatim. Flag any drift from TEMPLATE.md's
    field set and enum (TEMPLATE.md:2-13) — missing fields, invented
    values, absent front-matter entirely.

B2. Report whether anything in the repo currently READS ticket
    front-matter programmatically (grep `status:` consumers under
    tooling/, .claude/, src/ — run.py's machine_checks() reads the body,
    does anything read the YAML?). The glue's state machine must not
    become the second reader of a field a first reader parses differently.

## Zone C — Hooks and permissions

C1. For each hook in `.claude/hooks/` (session-start, block-main-push,
    block-db-in-git, any other): report verbatim its trigger event, its
    matcher/condition, and its effect (`file:line`). Specifically: does
    block-main-push block `git push origin main` only, or any push to
    main including PR-merge-side effects? The glue's PR1 endpoint must
    not collide with it.

C2. Report `.claude/settings.json` permission entries relevant to the
    glue: git commands, `gh` commands, file writes under `tooling/`.
    Verbatim allowlist/denylist entries with line refs. **BLOCKING
    FINDING** if `gh pr create` (or `gh` at all) is currently denied or
    unmentioned-and-therefore-prompting — the glue cannot chain to a PR
    through an interactive permission prompt in a semi-supervised session.

## Zone D — Git / GitHub infrastructure (PR1 viability)

D1. Report (commands + verbatim output): `git remote -v` (remote name,
    URL, protocol), default branch name, whether the working tree is a
    GitHub-hosted repo.

D2. Report `gh --version` and `gh auth status` output (redact tokens if
    any appear; report only authenticated yes/no + host). **BLOCKING
    FINDING** if gh is absent or unauthenticated — PR1 falls back to PR2
    (local merge) and the glue brief must know before it is written.

D3. Report the branch naming convention actually used so far (git branch
    -a / log inspection: `ticket/0001` was observed in RECON-0003's
    header — confirm pattern, list existing ticket branches, report
    whether 0003 followed it).

D4. Report how PRs have been merged so far if any exist (gh pr list
    --state all, or merge commits on main): squash, merge commit, or
    rebase — the glue's post-live-gate expectations depend on it.

## Zone E — Glue seams

E1. Report current contents of `tooling/glue/` (`file:line` for each
    script's argument contract — next_id.py, gen_decisions_index.py, and
    anything else that landed).

E2. Report whether `tooling/questions/` exists (QF1 target directory) and
    whether anything references it yet.

E3. Report Claude Code's model configuration as scaffolded (settings.json
    or CLAUDE.md statements about model lanes, E1 opus/sonnet split) —
    verbatim — so the glue brief can state which lane /pipeline runs in
    without inventing.

---

## Output format

Sections mirroring Zones A–E; infrastructure facts as quoted command
outputs. End with `BLOCKING FINDINGS` recap (or "none"). No design, no
recommendation, no fix.
