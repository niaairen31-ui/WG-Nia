---
id: TICKET-0079
title: Day narration judge false positives -- sentence-blind name extraction and no repair path
type: bug
status: live-gate
created: 2026-08-27
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]
blast_radius: small
brief_ids: [BRIEF-0079-a-sentence-aware-name-extraction, BRIEF-0079-b-bounded-repair-and-failure-surface]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> ticket 0079; lorsque je lance une journee : ''Je veux apprendre les
> preferences de Lorian'' Lorian est un NPC dans mon monde. J'obtiens cela dans
> la resoudre la journee : ''day narration rejected by judge: unauthorised
> name(s) not in authorised_names: Dirigeants, Sans, Serviteurs''. Explique moi
> ce que fait le juge exactement et comment on pourrait le modifie pour que
> cette situation ne se produise plus.

## Clarifications resolved (intake)

**What the judge does.** `judge_narration` (`src/world_engine/day_narration_guard.py:153`)
runs three fail-closed checks in order: (1) anti-vacuity on extracted names
(`:157-162`), (2) name containment against `fact_sheet.authorised_names`
(`:170-182`), (3) anti-vacuity on steps plus per-band marker survival
(`:126-138`, `:184-191`). `authorised_names` is built at `day_resolve.py:437`
from matched NPC names, matched location names and the player character's name.
Check (2) produced this rejection.

**Root cause 1 -- the extractor is blind to sentence boundaries [M].**
`_TOKEN_RE` (`day_narration_guard.py:55`) captures `[.!?]+` as tokens, but
`:99` filters those tokens out before the run-building loop, so the punctuation
branch of the regex is dead code and a run can span a full stop. Reproduced:
`"... les Serviteurs. Sans Dirigeants pour la retenir ..."` yields the single
run `"Serviteurs Sans Dirigeants"`, decomposed by `:175-177` into exactly the
reported triple. `sans` is in `_FUNCTION_WORD_STOPWORDS` (`:72`), so `Sans`
could only ever have been reported as part of a multi-word run -- the `:120`
`len(run) > 1` bypass is what let it through.

**Root cause 2 -- capitalised common nouns are indistinguishable from names [M].**
Fixing root cause 1 alone does not clear this rejection: measured, the same
prose still reports `['Dirigeants', 'Les', 'Serviteurs']`. `Dirigeants` and
`Serviteurs` are an open word class no stopword list can close. The extractor's
only signal is the initial capital. The model capitalised social groups as a
stylistic habit; the judge read them as fabricated proper names.

**Aggravating factor -- a judge rejection is a dead end [M].** The only
recovery path in `_narrate_and_judge` (`cockpit/routes/day.py:707-740`) is
`detect_late_delta`, which `day_narration.py:18-25` documents as unable to fire
today (no applier exists for `entity_creation`). A failing verdict therefore
falls straight through to the 422 at `:766`.

**Decision on where the fix belongs.** `day_resolve.py:141-146` records a prior
live-tested decision: when the model capitalised an unresolved place, the
conclusion was that the judge was right and the fix belonged in the prompt, not
in a looser judge. That precedent is upheld here. The judge is not loosened for
the common-noun class (rejected: B1 determiner exemption, B3 deterministic
de-capitalisation pre-pass). It is only corrected where it is provably wrong --
sentence fusion and function-word edges.

**Locked decisions.**

- `A2` -- restore the sentence break in `extract_names` AND strip function-word
  edges from multi-word runs, closing the `:120` bypass. Position gating
  (discarding a candidate because it is sentence-initial) stays rejected, per
  `day_narration_guard.py:29-36`.
- `B2b-2` -- the `day_narration` system prompt's naming rule is re-anchored on
  the nameable list and stated in fully positive form, carrying the
  typographic rule (initial capital reserved for listed names and for the first
  word of a sentence). The rule is written so that it stays true unchanged when
  factions later join the nameable list (E1). No illustrative examples: an
  example in a system prompt becomes a vocabulary reservoir and tints later
  narration.
- `R2` -- the illustrative examples already present in the adjacent role-hint
  bullet (`scripts/seed_pilot.py:1874-1877`) are removed for the same reason.
- `C1a` -- one bounded repair pass, new prompt usage `day_narration_repair`,
  fed the exact offending words the judge already computed. `MAX_REPAIR_ATTEMPTS = 1`.
- `P1` -- the repair directive is literal ("write these words in lower case"),
  not reformulating. Nia is explicitly indifferent to intermediate-stage
  correctness; see the drafting decision recorded in BRIEF-0079-b about the
  sentence-initial case, which reaches the FINAL prose.
- `D2` -- the 422 body carries a structured `offending_words` list and the
  rejected prose, not only a message string.
- `E2'` -- faction entities matched by concordance but dropped by `freeze_facts`
  (`day_resolve.py:409-411`, `:413`) stay a named deferral. Reactivation
  condition (verifiable): a resolved day whose `pass_play.declared_action`
  contains, case-insensitively, the `name` of an `entity` row with
  `type = 'faction'` in the active world.

**Rejected, with reactivation conditions.**

- `B1` (determiner exemption in the extractor) and `B3` (deterministic
  de-capitalisation of the prose before judging) -- both reverse
  `day_resolve.py:141-146`, and `B3` additionally gives code authority to
  rewrite narrative the player reads. Reactivation: the judge still rejects
  after the repair pass on more than 2 out of 10 resolved days.
- `E1` (widen `freeze_facts` to bin faction entities) -- deferred under `E2'`.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `extract_names` never returns a run whose words span a sentence-final `.`, `!` or `?`  -> verify/checks/day_name_extraction.py
- [ ] `extract_names` strips leading and trailing function words from a multi-word run, so `"Les Serviteurs"` contributes no candidate word `Les`  -> verify/checks/day_name_extraction.py
- [ ] `extract_names` still returns a single-word candidate that opens a sentence, proving no position gating was introduced  -> verify/checks/day_name_extraction.py
- [ ] `extract_names` is non-vacuous: the multi-name golden case returns the player name, the two-word name and the connector-bridged name  -> verify/checks/day_name_extraction.py
- [ ] `day_name_extraction.py` fails when zero golden cases are collected  -> verify/checks/day_name_extraction.py
- [ ] `MAX_REPAIR_ATTEMPTS` is a module-level literal `1` in `day_narration.py`, and `_narrate_and_judge` contains exactly one `repair` call site, itself guarded  -> verify/checks/day_narration.py
- [ ] `day_narration_repair` is a `PROMPT_REGISTRY` key whose `call_sites` names `repair` in `day_narration.py`  -> verify/checks/day_narration.py
- [ ] `JudgeVerdict` declares an `offending_words` field, and `cockpit/routes/day.py` performs no string parsing of `verdict.reason`  -> verify/checks/day_narration.py
- [ ] `DAY_NARRATION_SYSTEM_PROMPT` contains none of the removed example strings and no negative-form naming instruction  -> verify/checks/day_narration.py
- [ ] Seeded prompt usages and `PROMPT_REGISTRY` keys remain a bijection after `day_narration_repair` is added  -> verify/checks/prompt_registry.py

### Live  ->  human gate (Nia)

- [ ] The day "Je veux apprendre les preferences de Lorian" resolves and returns a recit, with no judge rejection.
- [ ] A day whose narration is deliberately made to capitalise a non-listed common noun either passes after exactly one repair call, or returns a 422 whose body carries `offending_words` and the rejected prose.
- [ ] The final stored prose reads as correct French: no listed name lost its capital, no sentence lost its capital.
- [ ] `pass_play.history` holds one entry per attempt, the rejected attempt intact alongside the repaired one.
