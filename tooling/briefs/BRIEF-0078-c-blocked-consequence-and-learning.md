# BRIEF — Step "Blocked consequence and learning"

## Context

After BRIEF-0078-b a blocked day is narrated, but it teaches nothing: the day
chain's mutation vocabulary holds no `new_knowledge`, so it can only DEEPEN a
knowledge row the player already has. A gate the player cannot open therefore
stays shut until Nia creates the row by hand through creator CRUD. Decision D3
closes that loop: bumping into a door proposes a `rumor`-level lead on the very
subject that blocked the step, so the next day can open it through play. This
is a world rule Nia decided, not a technical fallout, and it is what makes
anchoring precision non-load-bearing -- a legitimate gate on a near-duplicate
subject no reachable NPC holds still resolves through play instead of
deadlocking. The proposal goes through the review queue like every other
day-chain mutation: V1 stands, the day chain proposes and never applies.

## Mini-RECON (measured against the fresh tarball, `main`)

All anchors verified against the tree. **If any of these contradicts what you
find, STOP and escalate -- do not adapt the brief yourself.**

- [M] `day_mutations.py` -- 200 physical lines. `EMITTED_MUTATION_TYPES` at
  80-82 (`"knowledge_change", "relation_change", "agenda_step_change",
  "entity_creation"`), `_KNOWLEDGE_DEEPEN_LEVEL = "knows"` at 89,
  `_step_action` at 92-93, `_emit_agenda_step_change` at 96-118,
  `_emit_knowledge_change` at 121-155, `_emit_relation_change` at 158-165
  (always returns `[]`), `_emit_entity_creation` at 167-174 (documented
  no-op), `_EMITTERS` at 177-182, `emit_mutations` at 185-200.
- [M] `_emit_knowledge_change` (129-134) reads its subjects by querying
  `AgendaStepRequirement` filtered on `step_id` and `type == "knowledge"` --
  the precedent query shape for reaching a step's knowledge requirements.
- [M] `emit_mutations` (197-199) iterates every emitter for every outcome; an
  emitter that does not apply returns `[]`.
- [M] `cockpit/mutations.py:361-398` -- `_mutation_apply_new_knowledge`
  exists and routes through `write_knowledge`; it defaults `level` to
  `"rumor"` and `source` to `"conversation"` when absent, and flips a
  `discoverable_detail` only when `payload["discoverable_detail_id"]` is set.
- [M] `cockpit/mutations.py:75-108` -- `_knowledge_already_applied`, a
  CONVERSATION-scoped duplicate guard keyed on `conversation_id`. It is not
  usable here: a day-chain proposal carries `pass_play_id`, not
  `conversation_id`.
- [M] `tooling/verify/canon_write_policy.txt:21` --
  `writes/knowledge.py::write_knowledge` is the sole allow-listed writer of
  table `knowledge`; line 76 allow-lists
  `_mutation_apply_new_knowledge` for table `discoverable_detail` only.
- [M] `ProposedMutation` rows from this module carry `source_type="pass_play"`,
  `pass_play_id`, `status="proposed"`, `proposed_by="local_ai"` and a
  `rationale` kwarg (enforced by `day_plan.py` check R17).
- [M] `writes/knowledge.py:34-43` -- `KNOWLEDGE_LEVELS` and
  `KNOWLEDGE_LEVEL_LADDER`; `"rumor"` is rank 1.
- [M] `day_plan.py:127-139` -- `_eval_knowledge` tests `row is not None` and
  never reads `level` (H1).
- [M] `tooling/verify/checks/day_mutations.py` exists and owns this module's
  structural rules.

**STOP conditions.** Stop and escalate, without writing code, if: (1) any
anchor above is materially different; (2) `BLOCKED_BAND` /
`StepOutcome.requirement_verdicts` / `Verdict.type` are not present as
BRIEF-0078-a and -b specify -- this brief depends on all three and must not
reconstruct them; (3) `_mutation_apply_new_knowledge` turns out to require a
`conversation_id` to function; (4) applying the proposal would need a
`world_id` this module cannot reach without a new query.

## Scope IN

Items 1-4 are one commit. Item 5 is the verify commit.

1. **`EMITTED_MUTATION_TYPES` gains `"new_knowledge"`**
   (`day_mutations.py:80-82`), and `_EMITTERS` (177-182) gains the matching
   `"new_knowledge": _emit_new_knowledge` so the dict stays a literal
   bijection with the constant (R1).

2. **`_BLOCKED_LEAD_LEVEL: str = "rumor"`** as a module-level constant beside
   `_KNOWLEDGE_DEEPEN_LEVEL` (89). Never a bare literal at the construction
   site.

3. **`_emit_new_knowledge(outcome, pass_play, character, world_id, db) -> list[ProposedMutation]`**,
   same five-argument signature as every sibling emitter. It returns `[]`
   unless `outcome.band == BLOCKED_BAND` (imported from `day_resolve`) --
   a successful, partial or failed step proposes nothing here.

   For a blocked outcome it walks `outcome.requirement_verdicts` and emits one
   proposal per verdict where `v.type == "knowledge" and not v.met`, taking
   the subject from `v.required`. It does NOT re-query
   `AgendaStepRequirement`: `Verdict.type` (BRIEF-0078-a) makes the verdicts
   self-describing, and re-deriving the same fact from a second source would
   be a second authority for it. Payload:

   ```python
   payload = {
       "entity_id": character.id,
       "subject": subject,
       "level": _BLOCKED_LEAD_LEVEL,
       "content": (
           f"Piste entrevue en butant sur « {outcome.objective} » : "
           f"il reste quelque chose à apprendre au sujet de « {subject} »."
       ),
       "source": "journée bloquée",
       "is_secret": False,
   }
   ```

   `is_secret` is `False` explicitly and never derived from anything: B3
   already guarantees the anchoring subject came from a non-secret row, and a
   lead the player earned by playing is not a secret. `rationale` (English,
   machine-facing), VERBATIM:

   ```python
   rationale=(
       f"step {outcome.step_order} ({outcome.objective}) blocked on unheld "
       f"knowledge {subject!r} -- proposes a rumor-level lead so the gate can "
       f"open through play (TICKET-0078, D3)"
   )
   ```

4. **A duplicate guard, `_blocked_lead_already_proposed(character, subject, db) -> bool`.**
   Re-resolving the same blocked day before Nia clears the queue must not
   stack identical proposals. It runs ONE explicitly-filtered `select(` --
   `ProposedMutation` where `world_id == character.world_id`,
   `mutation_type == "new_knowledge"`, `status == "proposed"` -- and matches
   `payload["entity_id"]` and `payload["subject"]` in Python, because the
   payload is JSON and SQLite cannot filter it in the WHERE clause. Bounded by
   the size of the open review queue; state that bound in the function's
   docstring. `_emit_new_knowledge` skips any subject the guard reports.

   This is deliberately NOT an extension of `_knowledge_already_applied`
   (`cockpit/mutations.py:75-108`): that guard is conversation-scoped and
   scans APPLIED rows, a different question with a different key. Record the
   duplication and its reason in the module docstring, in the same posture the
   module already takes for its other deliberate duplicates.

5. **Verify.** Extend `tooling/verify/checks/day_mutations.py`, continuing its
   own numbering, each anti-vacuity guarded:
   - `_EMITTERS`' key set equals `EMITTED_MUTATION_TYPES` in both directions
     and is five-valued.
   - `_emit_new_knowledge` exists; its body references `BLOCKED_BAND` and
     returns early when the band does not match; it references
     `_BLOCKED_LEAD_LEVEL` and contains no bare `"rumor"` literal.
   - `_emit_new_knowledge` constructs no `ProposedMutation` with a `status`
     other than the literal `"proposed"`, and passes a non-empty `rationale`.
   - `day_mutations.py` calls `_apply_mutation` nowhere and calls
     `write_knowledge` nowhere -- it proposes only.
   - `_blocked_lead_already_proposed`'s `select(` carries all three filters by
     name; an unfiltered `select(ProposedMutation)` in this module is a
     FAILURE.

## Scope OUT

- **Applying the proposal, auto-approving it, or any path that writes a
  `knowledge` row from the day chain.** V1 is absolute: propose only. Do not
  add `write_knowledge` to this module and do not add a day-chain entry to
  `canon_write_policy.txt`. The park/resume direct write from TICKET-0077 is
  not a precedent -- a plan has no world footprint, knowledge has one.
- **A level escalator.** A step blocked a second time proposes nothing new
  (the duplicate guard suppresses it) and must not propose a rising
  `knowledge_change`. That is H2's machinery, deferred with the ticket's
  reactivation condition.
- **Reading or writing `level` in `_eval_knowledge`.** H1 is locked; the rumor
  opens the gate on the next day and that is the intended behaviour.
- **Emitting a lead for a non-`knowledge` unmet verdict.** A blocked
  `resource`/`relation_gte`/`location_reachable` step proposes nothing. The
  fact sheet still narrates it (BRIEF-0078-b); only D3's knowledge case has a
  sanctioned consequence.
- **Emitting `agenda_step_change` for a blocked step.** BRIEF-0078-b already
  made `_emit_agenda_step_change` return `[]` for that band. Do not revisit
  it, and do not widen
  `_mutation_apply_agenda_step_change`'s `("complete", "fail")` vocabulary.
- **`_emit_relation_change`'s always-empty return** (158-165) and
  `_emit_entity_creation`'s documented no-op (167-174). Both stay exactly as
  they are.
- **`resource_change`, `ledger_transfer`, `npc_move`, skill deltas.**
  Unchanged, still out of the vocabulary.
- **A `discoverable_detail` link.** `payload["discoverable_detail_id"]` is not
  set; the applier's flip branch must stay unreached from this path.
- **Subject normalization or near-duplicate merging** when choosing the
  subject. The lead is on the EXACT key that blocked the step, spelling and
  all. G1 is deferred.
- **Any change to `day_plan.py`, `day_resolve.py`, `day_narration*.py` or
  `cockpit/routes/day.py`.** This brief touches `day_mutations.py` and its
  check only.

## Invariants to defend

- **The day chain proposes, never applies (V1).** This is the brief most
  likely to break it, because the loop feels incomplete until the row exists.
  It is not incomplete: Nia's approval is the loop's closing step.
- **Single canon-write authority per resource type.** `write_knowledge` stays
  the sole writer of table `knowledge`; nothing here goes near it.
- **Exclusion is structural.** `is_secret: False` is a literal, not a derived
  value, and no secret subject can reach this path because B3 filtered it at
  anchoring time. Do not add an `is_secret` read here to "double-check" -- a
  second authority for the same rule.
- **No structure without a reader.** No new table, no new column, no marker
  field recording that a lead was proposed; the duplicate guard reads the
  review queue, which already exists.
- **Fail-closed with vacuous proof.** A check that finds zero
  `ProposedMutation` constructions in this module is a FAILURE, not a pass.

## Done means

- [ ] `python -m tooling.verify.checks.day_mutations` prints PASS naming the
      new rules.
- [ ] `python -m tooling.verify.checks.single_canon_write` prints PASS and
      `canon_write_policy.txt` is unchanged.
- [ ] `python -m tooling.verify.checks.corpus_gate` prints PASS.
- [ ] `grep -n "write_knowledge\|_apply_mutation" src/world_engine/day_mutations.py`
      returns nothing.
- [ ] Live: resolving a day blocked on an unheld, anchored subject produces
      exactly one `ProposedMutation` with `mutation_type='new_knowledge'`,
      `status='proposed'`, `source_type='pass_play'`, payload `level='rumor'`,
      the blocking subject, and the player's `entity_id`.
- [ ] Live: `SELECT COUNT(*) FROM knowledge WHERE subject = <subject> AND entity_id = <player>`
      is still 0 immediately after the resolve -- nothing was written.
- [ ] Live: re-resolving the SAME day before approving adds no second
      proposal.
- [ ] Live: approving it from the review queue creates the row at level
      `rumor`, and the next declaration on the same objective is no longer
      blocked -- the step is rolled and appears with a dice band.
- [ ] Live: a day blocked on a `resource` requirement proposes no
      `new_knowledge` and still narrates its `[BLOQUÉ]` beat.
- [ ] Live: a fully successful day proposes exactly what it proposed before
      this ticket -- no extra `new_knowledge` row.
- [ ] `/review-step` and `/close-step` both run and report clean.

## Docs to update

- `world-engine-schema.md` -- no change (no schema surface).
- `ARCHITECTURE_DECISIONS.md` -- append **D3 (a blocked step proposes a
  rumor-level lead on its own blocking subject)**, recording that it is a
  world rule Nia decided, that it is what keeps anchoring precision
  non-load-bearing, and that it proposes through the queue under V1. Append
  **H1 (any knowledge level satisfies a gate)** with its stated price and H2's
  reactivation condition verbatim from the ticket.
- `CLAUDE.md` -- no change.
