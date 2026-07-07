# QUESTION — TICKET-0013
Trigger: D1-c
## Context
All three briefs (BRIEF-0013-a, -b, -c) are executed and committed on
`ticket/0013`. Running `/verify` (`python -m tooling.verify.run --ticket
TICKET-0013-npc-goals-in-scene`) returned:

```
{
  "ticket": "TICKET-0013-npc-goals-in-scene",
  "when": "2026-07-07T16:28:13.330971+00:00",
  "green": true,
  "checks": []
}
```

`"checks": []` is vacuous, not a real pass: `tooling/verify/run.py`'s
`LINK` regex only matches the ASCII arrow `->`
(`r"->\s*verify/checks/([A-Za-z0-9_./-]+\.py)"`), but TICKET-0013's own
"### Machine-checkable" section (lines 241-246 of
`tooling/tickets/TICKET-0013-npc-goals-in-scene.md`) uses the Unicode
arrow `→` throughout, e.g.:

```
- [ ] `NpcGoal` referenced only in allowlisted modules; zero references inside `assemble_mj_context` → verify/checks/npc_goal_read.py
```

Every other ticket (0001, 0005, 0011, 0012, ...) uses the ASCII `->`
consistently and their G1 gates parse and run real checks. TICKET-0013 is
the only ticket using `→`, so none of its five listed criteria were ever
mechanically run this whole ticket. Fixing this means editing either:
(a) the deposited ticket artifact `tooling/tickets/TICKET-0013-npc-goals-in-scene.md`
    (filename/content is normally Nia's manual deposit, never rewritten
    by the executor), or
(b) the shared `tooling/verify/run.py` LINK regex (infra used by every
    ticket's G1 gate, outside any of the three briefs' stated Scope IN).

Both are outside BRIEF-0013-c's file perimeter, so this isn't a fix I can
make under the pipeline's "one confined retry" allowance — it needs a
decision.

Note: I DID separately run every individual check by hand this session
(`npc_goal_read.py`, `single_canon_write.py`, `prompt_lean.py`,
`prompt_registry.py`, `prompt_version.py`, `schema_partition.py`,
`page_contract.py`, `claude_md_contract.py`, `decisions_index.py`,
`pipeline_state.py`, `pipeline_cockpit.py`) plus live functional tests
(goal_change apply/emit, R1 signal, idempotent prompt delivery) — all
passed. The gap is specifically in `run.py`'s automated ticket-level
aggregation, not in the underlying checks themselves.

## Question
Which fix should I apply: (a) edit the ticket's arrows from `→` to `->`
to match every other ticket's convention, or (b) extend `run.py`'s LINK
regex to also accept `→` (so future tickets using either arrow style both
work)? Or would you rather resolve this yourself?

## Options
A. Edit `tooling/tickets/TICKET-0013-npc-goals-in-scene.md`: replace the
   five `→` occurrences in the "Machine-checkable" section with `->`,
   matching the established convention. Zero risk to other tickets.
B. Extend `tooling/verify/run.py`'s `LINK` regex to accept both `->` and
   `→`. Slightly broader (touches shared infra), but future-proofs
   against the same mismatch recurring, and requires no edit to the
   ticket artifact.
C. Something else (specify).

## Response
C = A + garde fail-closed.

A tel quel : les cinq flèches "→" du ticket redeviennent "->", alignées
sur la convention de tous les autres tickets.

Ajout minimal dans run.py : si la section Machine-checkable produit zéro
critère parsé, le run échoue avec un message explicite
("machine-checkable section parsed to zero criteria — malformed arrows
or empty section") au lieu de rendre "checks": [] vert. Une condition,
pas de refonte — ça durcit l'infra partagée, ça ne l'élargit jamais.
