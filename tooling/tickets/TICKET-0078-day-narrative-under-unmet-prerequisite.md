---
id: TICKET-0078
title: Day narrative under an unmet prerequisite -- requirement anchoring, blocked band, learned rumor
type: bug
status: live-gate
created: 2026-08-27
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
brief_ids: [BRIEF-0078-a-requirement-anchoring, BRIEF-0078-b-blocked-band-and-narration, BRIEF-0078-c-blocked-consequence-and-learning]
schema_version_touched: v1.95 -> v1.96
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> Ticket 0078: dans récit, j'obtiens parfois : La journée n'a pas pu commencer :
> prerequisite not met — knowledge 'room_setup' not held. Je m'attend a avoir
> quand même un récit avec ce qui se passe et les choses que j'apprend.

Follow-up decisions, verbatim:

> A5(A1b), B3, C2, D3, E2, F2+F3, G1. J'en comprend qu'un plan peut être créer
> avec un knowledge que le joueur ne détiens pas ( ou le monde) et le joueur
> aura une piste sur comment l'obtenir ( rumor) jouable la prochaine journée.

> H1

## Clarifications resolved (intake)

**The failure, traced end to end.** Four separable facts, not one bug.

1. [M] The `day_plan` prompt invites a free-form requirement key --
   `{"type":"knowledge","target_key":"<étiquette courte>"}`
   (`scripts/seed_pilot.py:1745-1746`). `_validate_requirement`
   (`day_plan.py:298-314`) validates the `type` only; `target_key` passes
   through `str()` with no canon check. `plan_context`
   (`day_concordance.py:259-278`) hands the model resolved mentions only --
   never a knowledge inventory. `room_setup` is therefore an invention, and
   the code obediently enforced a criterion no canon row defines. This is the
   inversion the doctrine forbids: the model proposed the RULE, not the action.
2. [M] `budget_cut` breaks at the first `not evaluated.met`
   (`day_plan.py:264-266`), so an unmet step 1 empties the whole day:
   `resolve_steps` returns `[]` (`day_resolve.py:280-286`).
3. [M] A narrative is structurally impossible today for that case:
   `judge_narration` fails on a zero-step fact sheet
   (`day_narration_guard.py:184-185`). The code-rendered one-liner
   (`cockpit/routes/day.py:816-832`) is the only way past the judge, not a
   shortcut.
4. [M] The block is a permanent dead end: `EMITTED_MUTATION_TYPES`
   (`day_mutations.py:80-82`) holds no `new_knowledge`, so the day chain can
   only DEEPEN an existing knowledge row. The player can never learn
   `room_setup` by playing; only creator CRUD unblocks.

**A5(A1b) + B3 -- a knowledge gate must be anchored in canon.** A `knowledge`
requirement survives emission only when its `target_key` matches an existing
`knowledge.subject` held, in this world, by an entity OTHER than the player,
on a row that is not `is_secret`. An unanchored requirement is DROPPED at
emission: the step keeps its objective and loses the gate. The rule in one
sentence: **you can only be locked on something that exists to be learned.**
`is_secret` is excluded because a gate on a secret is both unsatisfiable and a
leak -- the reject message would disclose the secret's existence, which the
structural-exclusion doctrine forbids. A1b additionally appends the player's
OWN held subjects to the emission call so the model stops proposing a gate on
something already held (a dead gate); A2's drop covers the opposite error (an
impossible gate). Together they carve out exactly the legal band.

Nia's reading of the parenthesis is corrected here and is load-bearing: a
subject held by NOBODY produces **no gate, no blocked step and no rumor** --
the step simply runs and is rolled. Only a subject held by someone else
produces the blocked/rumor path. Granting a rumor on an unanchored key would
let the model populate canon with its own invented vocabulary through the back
door, which is the failure mode G1 defers rather than feeds.

**C2 -- a blocked step is an outcome, not an absence.** The unmet step becomes
a `StepOutcome` with a fourth band, `blocked`, and enters the fact sheet with
its own marker `[BLOQUÉ]`. `narrate`/`judge_narration` then run normally. This
makes the zero-outcome case impossible by construction, which retires
`blocked_reason`'s bypass **without weakening the judge by one line** --
`day_narration_guard.py:184-185` stays exactly as it is. [M] `band` is
constrained nowhere in schema (`resolution.py:26` and `BAND_MARKERS` only), so
the fourth band costs no migration.

**D3 -- bumping into a door teaches a little about it.** A blocked step
proposes `new_knowledge` at level `rumor` on the very subject that blocked it.
This is a world rule, decided by Nia, not a technical fallout. It is the piece
that makes anchoring precision non-load-bearing: a near-duplicate subject
(`magic_existence` vs `magic_awakening` -- both already in the pilot seed) can
still produce a legitimate gate the player cannot open from any NPC, and D3
opens it through play anyway. The proposal goes through the review queue like
every other day-chain mutation (V1: the day chain proposes, never applies).
The precedent invoked in TICKET-0077 is not one: plan park/resume is a DIRECT
write (`writes/goals_agendas.py:488`) because a plan has no world footprint --
granting knowledge has one.

**H1 -- any level satisfies a knowledge gate.** [M] `_eval_knowledge` tests
`row is not None` (`day_plan.py:134`) and never reads `level`. Kept as is: it
is what makes D3's rumor playable the next day, exactly as Nia described. The
price, stated plainly: **every knowledge gate is a one-day speed bump, never a
durable obstacle.** H2 (a floor level carried on the unused
`agenda_step_requirement.threshold` column, as a `KNOWLEDGE_LEVEL_LADDER`
rank) is the named deferral. Reactivation condition: *once a level escalator
on repeated blocking exists* -- a step blocked N times proposing a rising
`knowledge_change`. Without that escalator H2/H3 produce a permanently shut
gate, which is this ticket's own bug returning by another door.

**E2 -- `/plan` reports, it does not refuse.** [M] `_finalize_plan` already
computes and returns `first_excluded_index` (`cockpit/routes/day.py:505`) and
acts on none of it, so the player only discovers a dead day at `/resolve`.
Since C2 makes a blocked day narratable, refusing at plan time would be the
wrong repair. E2 therefore resolves to VISIBILITY: the `/plan` response gains
the anchoring drop report and the blocking condition. (Drafting decision --
see BRIEF-0078-a's closing note.)

**F2+F3 -- the anchoring query is indexed and runs once.** [M] `knowledge`
carries no `world_id`, so anchoring joins through `entity`; the only index is
`idx_knowledge_entity` (`world-engine-schema.md:2001`), leaving a subject
lookup as a full scan. F2 adds `idx_knowledge_subject` (schema v1.96,
index-only migration, no table rebuild). F3 loads the anchorable vocabulary
ONCE per `/plan` call rather than once per requirement -- also what the
enumeration-scope discipline wants: one explicitly filtered `select(`, not N.

**E1 stays REPORT ONLY.** [M] `_eval_resource` (`day_plan.py:167-176`) sums
the character's whole `Ledger` and ignores `target_key` entirely -- the key
appears only in the message. Same invented-key family, different mechanic; it
gets its own ticket, not a seat on this one.

**G1 -- subject-vocabulary hygiene is deferred.** [M] The pilot seed already
holds 14 distinct subjects with visible near-twins (`magic_existence`,
`magic_awakening`, `personal_magic_incident`, `local_magic_incidents`;
`lettre_innommee` / `the_unnamed`), no normalization at the write chokepoint
(`writes/knowledge.py:128-129`), and exact-string comparison in the existing
duplicate guard (`cockpit/mutations.py:102`). The problem is real at n=14 and
is NOT introduced by this ticket -- anchoring merely gives it a first reader.
It stays deferred because C2+D3 make anchoring precision affect flavour only,
never liveness. Reactivation condition (verifiable, not qualitative): reopen
once `SELECT COUNT(DISTINCT subject)` on a live world exceeds **150**, OR once
a similarity pass measures more than **20%** of subjects within Levenshtein
distance <= 3 of another.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] a `knowledge` requirement whose `target_key` is not anchored is dropped
      before `evaluate_requirements`; the anchoring reader is a single
      explicitly-filtered `select(` naming `world_id`, the player exclusion and
      `is_secret`; zero anchoring sites collected is a FAILURE
      -> verify/checks/day_plan.py
- [ ] `Verdict` carries a `type` field and every evaluator sets it from
      `req.type`; the four construction sites are enumerated, zero collected is
      a FAILURE  -> verify/checks/day_plan.py
- [ ] `emit_plan` appends the held-subjects summary verbatim to the user
      message and never into the seeded template text
      -> verify/checks/day_plan.py
- [ ] `idx_knowledge_subject` exists in the schema doc and in `models/`;
      the migration is index-only (no table rebuild)
      -> verify/checks/schema_version_agreement.py
- [ ] `BAND_MARKERS`' key set is exactly the four bands, and
      `day_narration_guard.judge_narration` still fails on a zero-step fact
      sheet (the anti-vacuity line is unchanged)
      -> verify/checks/day_narration.py
- [ ] `resolve_steps` appends at most ONE blocked outcome, under all three
      conjuncts; `_truncate_on_failure` stays pure (no `db`, `select(`,
      `chat(`, `datetime`, `randint`)  -> verify/checks/day_narration.py
- [ ] `_mutation_apply_agenda_step_change`'s action vocabulary is still
      exactly `('complete', 'fail')` -- a blocked outcome emits no
      `agenda_step_change`  -> verify/checks/day_plan.py
- [ ] `_EMITTERS`' key set is a literal bijection with
      `EMITTED_MUTATION_TYPES`, now five-valued; `_emit_new_knowledge` fires
      only on the blocked band and only for unmet `knowledge` verdicts
      -> verify/checks/day_mutations.py
- [ ] `day_mutations.py` still constructs no `ProposedMutation` with a
      `status` other than the literal `'proposed'`, and calls
      `_apply_mutation` nowhere  -> verify/checks/day_mutations.py
- [ ] the day chain's prompt usages are all delivered, and the reseeded
      `day_narration` prompt is the one the DB holds
      -> verify/checks/day_prompt_delivery.py
- [ ] the `day_narration` system prompt stays lean
      -> verify/checks/prompt_lean.py
- [ ] `canon_write_policy.txt` gains no new writer for table `knowledge`
      -> verify/checks/single_canon_write.py
- [ ] no module in `src/world_engine/` exceeds the 1000-line budget
      -> verify/checks/module_budget.py
- [ ] no function exceeds 80 lines  -> verify/checks/function_length.py
- [ ] every check in tooling/verify/checks/ runs and passes
      -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)
- [ ] Declare a day whose plan the model gates on an invented subject
      (the `room_setup` case). `/plan` reports the dropped requirement; the day
      resolves with a normal narrative and normal dice. No "La journée n'a pas
      pu commencer".
- [ ] Declare a day gated on a REAL subject held by an NPC and not by the
      player. The day resolves; the narrative contains a `[BLOQUÉ]` beat that
      reads as prose, not as a machine message. No English string reaches the
      account.
- [ ] The review queue holds a `new_knowledge` proposal at level `rumor` on
      that exact subject, for the player character, with a readable rationale.
      No `agenda_step_change` was proposed for the blocked step.
- [ ] Approve it. The next day's declaration on the same objective is no
      longer blocked, and the step is rolled.
- [ ] Re-resolve the SAME blocked day before approving: no second identical
      `new_knowledge` proposal appears.
- [ ] A day that blocks purely on BUDGET (not on a requirement) still behaves
      as before -- no `[BLOQUÉ]` beat invented for it.
- [ ] A day whose feasibility veto retained zero steps still renders its own
      veto reason, unchanged.
- [ ] A day resolved before this ticket still reads back from
      `pass_play.history` without error.
