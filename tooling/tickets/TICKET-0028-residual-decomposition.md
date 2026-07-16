---
id: TICKET-0028
title: Residual decomposition — retire the R1/R5 transition baselines
type: feature
status: live-gate
# Stages a-f executed; full verify suite green on ticket/0028. Both
# transition baselines emptied (a-e) then deleted outright (f); R1/R5 run
# exemption-free, fail-closed absence proof recorded. Four disposable
# harnesses + fixtures deleted. code_standards.md closure edit applied
# (v1 -> v1.01). Awaiting Nia's live gate: merge, mark done, open the next
# ticket.
created: 2026-07-15
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: []       # no db_write/migration/destructive intent; behavior-
                       # preserving refactors on the tick pipeline and the
                       # canon-write module — treated as high-care regardless
blast_radius: large
brief_ids: [BRIEF-0028-a, BRIEF-0028-b, BRIEF-0028-c, BRIEF-0028-d, BRIEF-0028-e, BRIEF-0028-f]
schema_version_touched:     # none — no schema change anywhere in this ticket
retry_count: 0
---

## Request (verbatim, as Nia stated it)

Open TICKET-0028 per the TICKET-0027 handover: the transition baselines
were frozen at 0027's close as a shrink-only residual OWNED by this
ticket (decision I2); both baseline files are deleted at this ticket's
close, after which R1 (`function_length.py`) and R5 (`module_budget.py`)
run exemption-free.

## Clarifications resolved (intake)

RECON against live `main` (2026-07-15) confirmed the frozen residual:
4 module entries (`tick.py` 1799/19, `writes.py` 1607/32, `models.py`
1188/2, `entity_author.py` 1055/28) and 31 function entries. One
shrink-only drift observed (`commit_region` 271 -> 264), no baseline
edit needed.

Decisions locked (option blocks, 2026-07-15 session):
- **A1** — Briefs grouped by module; `tick.py` first (only module over
  the line cap that also owns the five largest baselined functions).
- **B1** — `writes.py` converts to a `writes/` package split by canon
  domain, with `writes/_shared.py` as a closed helper set;
  `canon_write_policy.txt` sites re-keyed under the
  relocation-not-broadening precedent (BRIEF-0027-c/-d). RECON finding
  that forced the split: ~440 of 1607 lines sit in the four baselined
  functions — in-place decomposition cannot reach the 1000-line cap, and
  I2 forbids re-baselining, so "ride until the tripwire" was not a real
  option.
- **C1** — `models.py` becomes a `models/` package split by schema
  stratum (canon / ephemeral / pipeline-internal), the classification
  that already has a reader (`schema_partition.py`); re-export via
  `models/__init__.py` freezes existing imports. Brief must require a
  generated-DDL equivalence proof (CREATE TABLE dump before/after, empty
  diff).
- **D1** — Third disposable record/replay harness
  (`scripts/harness_tick_replay.py`) shipped BEFORE the tick
  decomposition, covering both model-call sites (`tick.py:1460`,
  `tick.py:1675`), with a fixture coverage manifest (vacuous-proof rule
  made structural). D2 (generalizing the say harness) rejected.
- **E1** — Sequencing: a (harness + tick) -> b (writes) -> c (models)
  -> d (entity_author) -> e (remaining R1 residual) -> f (baseline +
  harness deletion, exemption-free checks, code_standards.md closure
  edit).
- **F1** — Tick split shape: flat modules `tick_context.py` +
  `tick_normalize.py`; `run_world_tick` (decomposed) stays in `tick.py`,
  keeping both importers (`routes/mutations.py:41`,
  `routes/play.py:27,992`) and both prompt-registry anchors
  (`prompt_registry.py:208,215`) untouched. F2 (a `tick/` package)
  rejected: name collision with root `context.py`, wider import
  re-keying for a 19-function module.
- **G1** — The TICKET-0027 `status: live-gate -> done` flip rides the
  first commit of BRIEF-0028-a.

BRIEF-0028-c citation correction (stated openly, supersedes C1's intake
wording above): the machine reader of the canon/ephemeral/pipeline-internal
stratum classification is NOT `schema_partition.py` (that check guards the
hot/cold doc partition) — it is `canon_write_policy.txt`'s `[CANON_TABLES]`
plus the class->table mapping `single_canon_write.py:69`
(`build_model_tables`) derives by parsing the models file(s). C1 itself
stands; only the citation moves.

BRIEF-0028-c stratum escalation (2026-07-15, four ambiguous rows resolved
by Nia): `GoalPrerequisite`/`goal_prerequisite` and `EventEntity`/
`event_entity` -> `models/canon.py` (world-truth rule data written by a
sanctioned site; their absence from `[CANON_TABLES]` is a known governance
gap, not a nature signal — two candidate follow-up tickets logged in the
BRIEF-0028-c execution notes: (a) add both tables to `[CANON_TABLES]` and
extend their sanctioned-site lines; (b) no-reader review of the dormant
`user` table). `User` -> `models/pipeline.py` (app/account infrastructure,
zero readers outside the models module as of schema v1.79). `PassPlay` ->
`models/pipeline.py` (batch-anchored offline-analysis grouping).
`[CANON_TABLES]` itself is untouched by BRIEF-0028-c (Scope OUT).

Standing precedents applied, not re-litigated: shrink-only baselines
with a named owner and a death date; open baseline bends only;
moved-helpers-keep-names / new-extractions-take-prefixes (R7);
check-anchor relocation preserves assertions verbatim with recorded
fail-closed proof; regenerate-never-hand-resolve on generated files;
one branch + one PR per brief.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] `baselines/function_length.json` deleted  -> verify/checks/function_length.py green with zero exemptions
- [ ] `baselines/module_budget.json` deleted  -> verify/checks/module_budget.py green with zero exemptions
- [ ] Every function in `src/` <= 80 lines  -> verify/checks/function_length.py
- [ ] Every module in `src/` <= 1000 lines AND <= 40 functions  -> verify/checks/module_budget.py
- [ ] Canon-write closed list re-keyed, count of sanctioned paths unchanged  -> verify/checks/single_canon_write.py
- [ ] LLM parse chokepoint intact, no new parse sites  -> verify/checks/llm_parse_chokepoint.py
- [ ] Generated DDL equivalence for the `models/` split (empty CREATE TABLE diff, recorded in execution notes)
- [ ] All three record/replay harnesses PASS post-refactor, then deleted at stage f
- [ ] Full verify suite green (30 checks) on every brief's PR and at close

### Live  ->  human gate (Nia)
- [ ] One live world tick: proposals reach the approval queue as before (stage a)
- [ ] One live `/say` round-trip and one mutation approval: unchanged behavior after the `writes/` split (stage b)
- [ ] Cockpit boots and a world loads after the `models/` split (stage c)
- [ ] Entity/event/player draft generation round-trips unchanged (stage d)

## Notes

- Harness ownership: `harness_say_replay.py` and
  `harness_mutation_apply.py` transferred from TICKET-0027;
  `harness_tick_replay.py` created here. All three deleted at stage f,
  alongside `harness_entity_author_replay.py` (created BRIEF-0028-d).
- Status flip: this ticket closes stage f with `status: live-gate`, not
  `done`. Per the TICKET-0027 precedent (BRIEF-0027-g's own `live-gate`
  close, flipped to `done` by BRIEF-0028-a — the first commit of this
  ticket, G1 pattern), the `live-gate -> done` flip for TICKET-0028 rides
  the first commit of the next ticket, not a commit of this one.
- After this ticket: return to the spatial / Play mode stream (four
  standalone discussion briefs; NPC spatial presence is the blocking
  chantier), plus pending Tier 4 overhearing propagation and Tier 3 C2
  gathering migration. TICKET-0023 (NPC relation graph) unchanged.
