# AMENDMENT-0124-01 — TICKET-0116 merged first: v2.30, a 47th usage, the lot re-based

Ticket: TICKET-0124   Lot: LOT-0124-world-premise.md (header authoritative)
Brief in flight: A -- stopped at its Mini-RECON; nothing written, nothing committed.
Branch: `ticket/0124`, cut from `origin/main` at `386c01a` (PR #151, TICKET-0116 merged). Lot planned on `246e89b`.

## What deviated

BRIEF-0124-A's first anchor did not hold: `schema_version.py:15` reads
`"v2.29"`, not `"v2.28"`. TICKET-0116 (rank trials) merged after the lot was
planned and took v2.29 (`migrate_v2_29_rank_trials.py`). The executor
stopped, as it should.

The lot RECON was re-run on `386c01a` for every file TICKET-0116 changed
(`git diff --stat 246e89b 386c01a`, 65 files). Five findings and three
contracts move; the rest hold.

1. **Schema.** This ticket's version is **v2.30**; its migration
   `migrate_v2_30_world_tone.py`, refusing a database older than v2.29.
2. **A 47th usage.** TICKET-0116 added `quest_trial` (`prompt_registry.py:318-325`,
   seeded from `seed_pilot.QUEST_TRIAL_PROMPT_HEADS`, called by
   `quest_designer._design_call` through `prompt_call.call_json`). It designs
   a quest offer, like `quest_design`: placed in **`creator`** (drafting
   decision, flagged to Nia). The partition becomes 14 / 15 / 18 = 47. It is
   filled by `call_json` (C-06), so C-07's render-site table does not change;
   the `current_prompt(` count is still 53 (re-run on `386c01a`).
3. **Shifted lines** (no change of meaning): `models/pipeline.py` +14 after
   `:587` (`PromptVersion` `:795`, `PromptVariable` `:776`); `models/canon.py`
   `SkillSystem` `:591-617`; `seed_pilot.py` +77 after `:2487`
   (`DAY_PROMPT_HEADS` `:2969`, seed loops `:3588-3595`, `:3767`);
   `quest_designer.py` `call_json` calls `:91`, `:101`; `npc_skills.py` C2
   needles `:598`; `knowledge_identity.py` `day_plan` fixture `:634-640`.
   Unchanged and re-confirmed: every frontend file of briefs H, I, J;
   `cockpit/routes/creator.py`, `cockpit/crud/entities.py`, `entity_author.py`,
   `day_concordance.py`, `writes/prompts.py`, `writes/attributes.py`,
   `dashboard_deferrals.py`; `canon_write_policy.txt:133-140`;
   `world-engine-schema.md:22-56`.
4. **A gate the lot could not pass (gate (e), missed).** `pipeline_state.py`
   (through `corpus_gate.py`) requires every Machine-checkable arrow of a
   ticket whose status is in `ARROW_FLOOR_STATUSES` (`pipeline_state.py:54`:
   `brief, exec, verify, live-gate, done`) to name an existing check
   (`:113-120`). TICKET-0124 names seven checks its own briefs create, the
   last in brief I, so `corpus_gate.py` is red from the ticket's deposit until
   brief I lands. Briefs C and D named `corpus_gate.py -> PASS`: unsatisfiable.
   The same rule is what turned TICKET-0116's `/verify` red while
   TICKET-0124 sat untracked in `tooling/tickets` (its E-01, answered A).
5. **Two stubs route on the system prompt's first words.** After brief D
   prefixes `{world_premise}`, `rank_trials.py:775-778` and
   `quest_designer.py:77-78` (`system.startswith(...)`) can misroute when
   their fixture world gives the creator premise any content (skill systems
   count). Brief D's ADAPT now names them.

## Amended RECON

R-04, R-05, R-06, R-08, R-12, R-13, R-23 and R-29 are rewritten in the lot
header on `386c01a`, each opening with a line naming this amendment. Their
new text is in the header (authoritative) and in the regenerated briefs.

## Amended contracts

- **C-01** -- `World.tone`, schema **v2.30**.
- **C-03** -- `creator` (14) gains `quest_trial`.
- **C-06** -- unchanged in shape; its usages are five (`lore_statement_questions`, `lore_statement_to_proposal`, `quest_subject`, `quest_design`, `quest_trial`).
- Gate (c) lists 47 usages and heads; gate (d) reads 14/15/18 (47); gate (e) gains the `pipeline_state.py` line of point 4.

## Briefs regenerated

- **A** -- v2.30 throughout; `migrate_v2_30_world_tone.py`, `_PREVIOUS_VERSION = "v2.29"`; anchors on v2.29; R-04 re-embedded.
- **B** -- 47 entries; WP1's literal `CREATOR` holds 14 (with `quest_trial`); five `call_json` usages; R-05, R-06, R-08, R-23 re-embedded.
- **C** -- Done means: the named checks a swap can turn red, not `corpus_gate.py` (point 4).
- **D** -- WP4 over 47 usages; Done means: `corpus_gate.py` red only on `pipeline_state.py`'s arrows to the checks of E-I; ADAPT names the two stubs of point 5; R-12, R-13 re-embedded.
- **E-J** -- base commit `386c01a`; H's `npc_skills.py:598`; R-29 re-embedded. No scope changed.

## Gate checks re-run

(a) every property re-traced on `386c01a` for the files TICKET-0116 touched;
(c) the 47-usage list, the 53 `current_prompt(` calls, the 47 seeded heads
re-enumerated; (e) re-run for every proposed and passed gate -- the
`pipeline_state.py` line added.

## Anchors to confirm before brief A resumes

- `git rev-parse origin/main` -> `386c01a...`; `ticket/0124` holds no commit beyond it.
- `schema_version.py:15` -> `"v2.29"`; no `scripts/migrate_v2_30_*.py`.
- `prompt_registry.py` -> 47 `PromptSpec(` entries, `quest_trial` at `:319`.

## For Nia

- One drafting decision: `quest_trial` in `creator` (point 2).
- `corpus_gate.py` stays red on `pipeline_state.py` from the ticket's deposit until brief I; `/pipeline TICKET-0124` reaches `/verify` only after J, where it passes. Another ticket verified meanwhile with TICKET-0124 deposited meets the same red (TICKET-0116's E-01).
