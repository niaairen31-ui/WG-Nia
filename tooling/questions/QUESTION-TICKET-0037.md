# QUESTION — TICKET-0037
Trigger: D1-d
## Context
Both `/pipeline TICKET-0037` `/verify` runs are red with an identical
fail-closed error, before and after BRIEF-0037-d's mandatory retry:

Run 1 (2026-07-21T15:31:40Z, retry_count 0):
```json
{
  "ticket": "TICKET-0037-npc-group-agent",
  "when": "2026-07-21T15:31:40.692774+00:00",
  "green": false,
  "checks": [],
  "error": "machine-checkable section parsed to zero criteria — malformed arrows or empty section"
}
```

Run 2 (2026-07-21T15:32:13Z, retry_count 1, no code change — no fix
confined to BRIEF-0037-d's Scope IN was available):
```json
{
  "ticket": "TICKET-0037-npc-group-agent",
  "when": "2026-07-21T15:32:13.991240+00:00",
  "green": false,
  "checks": [],
  "error": "machine-checkable section parsed to zero criteria — malformed arrows or empty section"
}
```

This predates BRIEF-0037-d: the identical red verdict already existed in
`tooling/verify/results/TICKET-0037-npc-group-agent.json`
(timestamp 2026-07-21T14:51:00Z) before this session started any brief-d
work — this is the first time the ticket's full brief chain has reached
Step 2 (`/verify` runs once, at the very end, per CLAUDE.md).

**Root cause 1 — malformed arrow links.** `tooling/verify/run.py`'s `LINK`
regex (`->\s*verify/checks/([A-Za-z0-9_./-]+\.py)`) requires the literal
substring `verify/checks/` immediately followed by an allowed-character
filename ending in `.py`. None of the ticket's 8 "Machine-checkable"
bullets match:
- 2 bullets link a bare filename with no `verify/checks/` prefix
  (`-> single_canon_write.py ...`).
- 2 bullets use an unresolved `<placeholder>.py` name
  (`-> verify/checks/<staging_purge>.py`,
  `-> verify/checks/<npc_batch_count_contract>.py`) — angle brackets
  aren't in the regex's allowed character class.
- 2 bullets link no filename at all
  (`-> prompt_registry check`, `-> existing module_budget check`).
- Only 2 bullets have a resolvable literal name at all, and even those
  were never given a real filename by the briefs that were meant to
  create them (see below).

**Root cause 2 — two referenced check files were never created.** The
`<staging_purge>` placeholder (BRIEF-0037-a's "startup purge covers
`npc_batch` with last-2 retention") and `<npc_batch_count_contract>`
placeholder (BRIEF-0037-b's "exact-count invariant") point at checks that
don't exist under `tooling/verify/checks/`. The underlying functionality
IS implemented correctly (`purge_closed_npc_batches` in `cockpit/app.py`,
wired into startup purge alongside the link agent's; the generation loop
in `npc_group_author.py`) — only the dedicated verify-check files were
never authored, by briefs already closed and committed (a, b), outside
BRIEF-0037-d's Scope IN.

BRIEF-0037-d's own deliverables are complete and committed (commit
`7e399a4` on `ticket/0037`): region NPC machinery retired end-to-end,
its own new check (`region_npc_retirement.py`) passes standalone, docs
synced (CLAUDE.md, ARCHITECTURE_DECISIONS.md, world-engine-schema.md),
review-step verdict CLEAN. I ran the full `tooling/verify/checks/*.py`
suite by hand (not just the ticket-linked subset) — every check touching
this ticket's actual files passes; the only failures are 5 pre-existing,
confirmed-unrelated ones (verified byte-identical via `git stash`) in
files this ticket never touches (TICKET-0034/0036 territory, local dev-DB
migration state).

## Question
How should TICKET-0037's malformed "Machine-checkable" section be
resolved so `/verify` can parse real criteria and reach a genuine
green/red verdict — and who should make that edit, given the ticket body
is a Nia-deposited artifact I don't normally rewrite?

## Options
A. I rewrite the 8 bullets' arrow syntax to the literal, regex-matching
   form, and either (a) point `<staging_purge>`/`<npc_batch_count_contract>`
   at newly-authored check files I'd write now (a fix for briefs a/b's
   gap, technically outside BRIEF-0037-d's stated perimeter), or
   (b) mark those two criteria as "not machine-checked, verify at live
   gate" and fix only the 6 bullets whose intended check already exists.
B. Nia edits `tooling/tickets/TICKET-0037-npc-group-agent.md` herself
   (arrow syntax + a decision on the two missing checks), then re-runs
   `/pipeline TICKET-0037`.
C. Loosen `tooling/verify/run.py`'s `LINK` regex to also match the
   ticket's existing formats (bare filenames, filename-less "check"
   mentions) — a tooling change affecting every future ticket's `/verify`
   parsing, not scoped to this one alone.
## Response
Option A(a): rewrite the 8 bullets' arrow syntax to the parseable form,
and author the two missing checks now (staging_purge retention check for
BRIEF-0037-a, exact-count invariant check for BRIEF-0037-b) so all 8
criteria are real, machine-checked gates.
