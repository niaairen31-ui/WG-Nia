# AMENDMENT-0111-01 — a player reads a condition as his character may know it

Ticket: TICKET-0111 "The condition language"   Lot: LOT-0111-condition-language.md
Brief in flight: BRIEF-0111-D (applied, not committed, on `ticket/0111`)
Trigger: Claude Code's STOP, `tooling/questions/QUESTION-TICKET-0111.md` (D1-a)
Decision: Nia, 2026-10-08 -- A1, V2

## What deviated

BRIEF-0111-D shows a quest step's completion lines in Journée. For a
`knowledge` leaf they wrote out the fact's text, with no regard for what the
character knows: an NPC's secret or the creator's note could reach the
player. Measured (R-23): the same text already reached the player since
TICKET-0108 through a blocked step's « ce qui manque » in Journée and a
standing plan's refusal, and the day's narration received it as model
context -- a creator's quest gate is not anchored (B3 anchors the model's
gates only). A second defect, of BRIEF-0111-C: a step's verdicts became
every judged leaf, so a leaf under a `not` or about the giver reached the
narration and `_emit_new_knowledge`'s lead.

A lot defect: BRIEF-0111-D's « Invariants to defend » did not name
« Secrets are structurally excluded ». Claude Code stopped where it should.

## Decisions

- **A1** -- every player surface writes a fact out only when the character
  resolves it above `unaware`; otherwise « un fait encore caché ». The
  creator's surfaces are unchanged. Rejected: A2 (the fact as
  player-visible), A3 (no `knowledge` leaf in a completion).
- **V2** -- on a player surface, a judged leaf about someone else reads
  `?`; head lines are recombined from what is left; another's regard is
  never counted. Rejected: V1 (reactivation: the event journal of
  TICKET-0114 records who witnessed what -- « tue le loup géant » is
  tracked from then; Nia accepts the wait).

## Added finding (verbatim; the lot header carries the same text)

### R-23 — a player surface writes out the fact of an unmet `knowledge` gate [M]
Added by AMENDMENT-0111-01 (Claude Code's STOP on BRIEF-0111-D, trigger D1-a).
Opened: `src/world_engine/day_plan.py:173-192` (`_eval_knowledge`: the
verdict's `required_label` is `fact_text`, met iff the character holds a
row), `src/world_engine/day_resolve.py:256-283` (`_BLOCKED_DETAIL_FR`
`:261` writes `{required}`, the label, for `knowledge`), `:426` (the
narration's `blocked_detail`, from every unmet verdict);
`src/world_engine/quest_reads.py:143-155` (`_steps_view` `:151`, Journée's
quest panel and `settlement_context`); `src/world_engine/cockpit/day_reconcile_apply.py:74`
(the 422 a standing plan answers); `src/world_engine/day_mutations.py:225-272`
(`_emit_new_knowledge` `:240`: a lead per unmet `knowledge` verdict);
`src/world_engine/day_plan.py:536` (`anchor_requirements`: B3 anchors only
the MODEL's gates); `src/world_engine/knowledge_resolve.py:248`
(`resolve_knowledge_level`); `CLAUDE.md:148` (« Secrets are structurally
excluded »).
Finding: a `knowledge` gate is shown to the player precisely when his
character does not know the fact, and its line writes the fact out. A day
plan's gates are anchored to facts others hold openly (B3); a quest's are
written by the creator, unanchored -- a secret or the creator's note can be
one. The path exists since TICKET-0108 (quest steps judged in Journée);
BRIEF-0111-D's completion lines add a second; the day's narration receives
the same text as model context. Since BRIEF-0111-C a step's verdicts are
every judged leaf: a leaf under a `not` or about the giver also reaches the
narration and `_emit_new_knowledge`.
Consequence: A1 -- every player surface writes a fact out only when the
character resolves it above `unaware`; V2 -- a judged leaf about someone
else reads `?` there; a blocked step names and teaches only the leaves that
hold it back for its doer (C-04, C-05, C-07, C-08, C-09 amended in D).

## Amended contracts (verbatim; the lot header carries the same text)

### C-04 — evaluation, `conditions.evaluate`
Produced by: BRIEF-0111-B   Consumed by: C, D
Signature: `evaluate(tree: Optional[ConditionTree], bindings: Bindings,
db) -> Optional[VerdictNode]`; `Bindings(doer: Character, giver_id:
Optional[str] = None, contact_id: Optional[str] = None)`.
Return shape: `VerdictNode(state, op, children, n, spec, verdict, reason)`
-- `state` in `("met", "unmet", "unknown")`; a leaf carries its `spec`
and either its `Verdict` (judged) or its French `reason` (`unknown`);
`.met`; `.leaf_nodes()`; `.leaf_verdicts()` (judged leaves only).
Error and empty cases: None for no condition (the caller treats it as
met); a role bound to nothing -> `unknown` « … n'est pas défini ici »; a
subject that is not a character -> `unknown` « … n'est pas un personnage »;
an unknown form raises `ValueError`. Connectors per table b-1. One
reachable set per subject per call.
Amended by AMENDMENT-0111-01 (produced by BRIEF-0111-D):
`VerdictNode.seen_by(viewer_id) -> VerdictNode` -- a judged leaf whose
subject is neither `doer` nor `viewer_id` becomes `unknown`, no verdict,
reason `UNSEEN_REASON_FR` (« le personnage ne peut pas le vérifier »);
every connector recombined from its seen children (table b-6).
`VerdictNode.blocking_verdicts() -> tuple[Verdict, ...]` -- the verdicts
of the judged leaves on `doer` that are unmet and under no `not`, in order.

### C-05 — the French of a tree, `condition_text`
Produced by: BRIEF-0111-B (new forms: BRIEF-0111-C)   Consumed by: C, D
Signature: `describe(db, tree) -> list[dict]` (`{"depth", "text"}`, a
connector's head before its children one level deeper; [] for None);
`verdict_lines(db, verdict) -> list[dict]` (`{"depth", "text", "state",
"mark", "progress"}`, `mark` in ✓ ✗ ?, `progress` `"current/required"`
when both are integers, an unknown leaf's text ending with its reason);
`leaf_text(db, spec) -> str`. `FORM_PHRASES_FR` (one per form, `{who}`
`{target}` `{threshold}` `{value}`), `CONNECTOR_HEADS_FR` (one per
connector), `SUBJECT_LABELS_FR`, `VALUE_LABELS_FR` (one label per
`FORM_VALUES` value).
Error and empty cases: `leaf_text` raises `ValueError` on an unknown form.
Amended by AMENDMENT-0111-01 (produced by BRIEF-0111-D): `leaf_text(db,
spec, viewer_id=None)` and `verdict_lines(db, verdict, viewer_id=None)`.
With `viewer_id` (a player surface): the verdict is first `seen_by` him;
a `knowledge` leaf whose fact `known_to(db, viewer_id, fact_id)` denies
(`resolve_knowledge_level` is `unaware`) reads `HIDDEN_FACT_FR` («
{who} connaît un fait encore caché »); a form in `HIDDEN_PROGRESS_FORMS`
(`relation_gte`) has no progress. Without it (the creator): unchanged.

### C-07 — the plan step and its evaluation (`day_plan`)
Produced by: BRIEF-0111-C (`completion`: BRIEF-0111-D)   Consumed by: C, D
Signature: `PlanStep(objective, cost, domain, prerequisite:
Optional[ConditionTree] = None, completion: Optional[ConditionTree] =
None)`; `EvaluatedStep(step, verdict: Optional[VerdictNode] = None)` with
`.met` (None or `verdict.met`) and `.verdicts` (`verdict.leaf_verdicts()`);
`evaluate_requirements(step, bindings, db) -> Optional[VerdictNode]`;
`plan_bindings(agenda_id, character, db) -> Bindings` (the character; and,
for a quest's agenda, its offer's giver and contact);
`evaluate_agenda_step(agenda_step, character, db) -> EvaluatedStep` (the
stored prerequisite, judged with `plan_bindings`).
Error and empty cases: a model's plan step without requirements has no
prerequisite and is met.
Amended by AMENDMENT-0111-01 (produced by BRIEF-0111-D):
`EvaluatedStep.blocking` (`verdict.blocking_verdicts()`, () for none) --
what a `StepOutcome`'s `requirement_verdicts` holds, for the narration and
`_emit_new_knowledge`.

### C-08 — what a condition still lacks, `day_resolve.blocked_details_fr`
Produced by: BRIEF-0111-C   Consumed by: C, D
Signature: `blocked_details_fr(verdict: Optional[VerdictNode], db) ->
list[str]`.
Return shape: [] when met or None; else, walking the tree: an unmet leaf
-> `requirement_detail_fr(verdict)`; an unknown leaf -> its reason; under
a `not`, a MET leaf -> « il ne faut pas que : <leaf_text, first letter
lowered> ».
Amended by AMENDMENT-0111-01 (produced by BRIEF-0111-D):
`blocked_details_fr(verdict, db, viewer_id) -> list[str]` -- [] when met or
None; else walking `verdict.seen_by(viewer_id)`: an unmet leaf ->
`player_detail_fr(verdict, viewer_id, db)`; an unknown leaf -> its
`leaf_text(…, viewer_id)`, first letter lowered, then « (reason) »; under a
`not`, a MET leaf -> « il ne faut pas que : <leaf_text(…, viewer_id)> ».
`player_detail_fr(verdict, viewer_id, db) -> str` --
`HIDDEN_KNOWLEDGE_DETAIL_FR` (« il lui manque encore un fait à découvrir »)
for a `knowledge` verdict whose fact the viewer does not know, else
`requirement_detail_fr(verdict)`. Every caller is a player surface:
`quest_reads._steps_view`, `day_reconcile_apply`'s refusal; the narration's
`blocked_detail` calls `player_detail_fr` on the step's `blocking`.

### C-09 — what the surfaces read and send (`quest_reads`, `routes/quests`)
Produced by: BRIEF-0111-D   Consumed by: D (frontend)
Signature: `quest_reads.condition_view(db, tree) -> {"tree":
node_to_dict(tree), "flat": [leaf dict] | None, "lines": describe(...)}`
(`flat` None when the tree is not flat; a leaf dict carries `type`,
`target_entity_id`, `target_key`, `threshold`, `subject_role`,
`subject_entity_id`, `value`). `offer_dict`: `"eligibility"` a view; each
step `"prerequisite"` and `"completion"` views (no `"requirements"`).
`OfferBody.eligibility`, `OfferStepBody.prerequisite` / `.completion`:
`Optional[dict]` trees (C-03's dict form); a malformed tree -> 422, no row.
`_steps_view` adds `"completion": verdict_lines(...)` (every step) and
`"completion_met": bool | None`. Amended by AMENDMENT-0111-01: both as
the character may read them -- `verdict_lines(db, completion, character.id)`
and `completion.seen_by(character.id).met`; `"blocked"` is
`blocked_details_fr(..., character.id)`. `editor_choices` adds `"form_values":
{form: [{"value", "label"}]}`. No payload carries `agenda_id` or `step_id`.

## Added case table

b-6 -- what a player reads of a leaf (AMENDMENT-0111-01, C-04, C-05, C-08).

| leaf                                         | creator          | player (`viewer_id` = the doer)                 |
|----------------------------------------------|------------------|-------------------------------------------------|
| on `doer`, any form but the two below       | text, mark, count | same                                           |
| on `doer`, `knowledge`, fact known           | the fact's text   | same                                           |
| on `doer`, `knowledge`, fact not known       | the fact's text   | « … connaît un fait encore caché »; detail « il lui manque encore un fait à découvrir » |
| on `doer`, `relation_gte`                    | mark, « 40/50 »   | mark, no count                                 |
| on `giver` / `contact` / a named character  | its state         | `?` « (le personnage ne peut pas le vérifier) », no count; a `knowledge` one hides its fact as above |
| a role bound to nothing                       | `?` and why      | same                                           |
| a connector                                   | its state         | recombined from what the player sees (b-1)    |

A blocked step (narration, lead): only the unmet leaves on `doer` under no
`not`.

## Touched briefs

- **BRIEF-0111-D** -- regenerated (its embedded diff includes the
  amendment; its facts, contracts and tables carry R-23, C-08 and b-6; its
  done-means add CD4 and four mutations). Set aside the earlier D first:
  `git stash push --include-untracked -m "BRIEF-0111-D before
  AMENDMENT-0111-01"` -- kept, never dropped.
- **BRIEF-0111-A, -B, -C** -- unchanged and already committed; their
  embedded copies of C-04, C-05, C-07, C-08 predate this amendment, and the
  lot header wins (its « Amended by » lines).
- **TICKET-0111** -- A1, V2 under « Decisions locked »; V1 under « Carried
  forward »; one live-gate item; the amendment log row.

## Gate checks re-run

(a) the property trace gains R-23's six lines; (b) b-6 added; (d) the
verdict family re-read after `seen_by` and `blocking_verdicts` joined it
(C-04) -- unchanged for the creator, every player reader named in C-08;
(e) CD4 proposed, satisfied by `conditions.py`, `condition_text.py`,
`day_resolve.py` and `quest_reads.py` in D. Verified on a copy: A, B, C
from their delivered briefs, then the regenerated D, replayed on a clean
`main` -- each tree identical to the prototype but for the build
timestamp; corpus 144/144 after each; every named mutation of D, the four
new CD4 ones included, turns its rule red.

## Answering the escalation

BRIEF-0111-D's Scope IN fills the QUESTION file's `## Response` with
`tooling/glue/question_response.py` (« A1, V2 -- AMENDMENT-0111-01 ») and
commits it with the brief.
