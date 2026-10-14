# LOT — TICKET-0121 "Journée proposes a quest: the request, the lore searched whole, the existence question, the designer, its review"

`main` at `301d178` (PR #148, TICKET-0115 merged), schema v2.27.

## Objective and cut

A player declares what he is after. When it is something to obtain rather
than a day's activity -- information on X, doing Y without its
prerequisites -- Journée turns it into a **quest request** on the creator's
side, and the day is spent searching (no dice). The creator presses
« Concevoir »: the designer frames the subject, searches the whole lore
(secrets included, H2), and either asks her whether the subject exists in
this world (N1, the answer written through the Lore writing panel) or
composes a full quest offer -- prerequisites, objectives and failures in the
full condition language (C1), costs and rewards (F1), the vocabulary it
lacks (G1), up to three suggested givers (D1). The offer is a
`quest_offer_creation` proposal reviewed in the offer editor itself, inside
the review card (B1): she picks the giver, the eligibility gains « has met
the giver » (E1), a « Quête unique » box adds « is this character » (E3a),
and every player-visible field that repeats a secret she must confirm (V1).

The lot stops before: the plan tool reworked into a global plan (P1,
deferred and measured); a search by meaning (S3, deferred and measured); a
giver invented by the designer (D2, deferred and measured); the planner's
own four forms (S1 of 0111, unchanged); completion acting on its own (M2);
the character accepting by himself (I1 of 0108); requests born from the
`modify` and `continue` reconciliation paths (only new plans open requests).

## Briefs in this lot

- **A** `is-character-form` -- the form `is_character` in its seven homes (no schema change).
- **B** `quest-request-schema` -- v2.28: `quest_request`, its writer, the cascade, the mutation-type and producer constants, the « Demandes de quête » metric and three deferrals.
- **C** `lore-facts-mentioning` -- the selector `facts_mentioning` and its `text:` argument; the designer's lore gathering, `quest_lore.gather_lore` (no schema change).
- **D** `journee-routing` -- `_finalize_plan` moved out of the route (pure move); the selection's third answer (K1); a blocked step and an unanchored knowledge open a request (K1b, R1); the `inquiry` band (T1, J2-a1) (no schema change).
- **E** `quest-designer` -- the offer save shared by the route and the applier (pure move); the interpreter's reuse points; `quest_designer.py` and its two prompts; the `quest_offer_creation` applier and the prose guard (V1, INV-63); INV-01 amended; the request routes and the Lore commit's link (no schema change).
- **F** `quest-review-card` -- the offer editor extracted (pure move); the review card edits a `quest_offer_creation` in it: giver, « Quête unique », flags, the designer's pending conditions (no schema change).
- **G** `quest-request-panel` -- « Demandes de quête » above the review queue; the existence question; the Lore writing panel pre-filled, its commit sending the request (the server side of that link is E's) (no schema change).

## Dependency graph

- A, B and C depend on nothing in this lot and on nothing in each other.
- D depends on B (`open_request`, the trigger constants).
- E depends on B (the request and its statuses) and C (`gather_lore`).
- F depends on A (the « Quête unique » leaf) and E (the payload, the routes).
- G depends on E (the request routes) and F (the card the panel links to is
  F's; G's Lore hand-off is independent of F).
- **Execution order A, B, C, D, E, F, G.** The A-B-C order is a choice for a
  single linear branch, not a dependency: an executor who finds nothing
  blocking between them is not finding a defect.

## RECON

Every finding was opened on `main` at `301d178`, in the file that declares
what is claimed. `[M]` measured.

### R-01 — the condition vocabulary [M]
Opened: `src/world_engine/condition_forms.py:81-91` (`REQUIREMENT_TYPES`), `:94-96` (`ENTITY_TARGET_TYPES`), `:97` (`KEY_TARGET_TYPES`), `:525-539` (`_EVALUATORS`), `:265-279` (`_eval_has_met`), `:148-170` (`Verdict`).
Finding: thirteen forms, in this order: `knowledge, relation_gte, resource, location_reachable, has_met, faction_member, skill_rank_gte, quest_state, has_debt_to, no_debt_to, item_held, attribute, event`. `ENTITY_TARGET_TYPES` is `relation_gte, location_reachable, has_met, faction_member, has_debt_to, no_debt_to, item_held`, in that order. Every evaluator has the signature `(req, character, db, reachable_ids) -> Verdict`; `Verdict(type, met, current, required, reason, required_label=None, hidden=False, events=())`, `type` first.
Consequence: `is_character` is appended LAST to both tuples, so every order-sensitive mirror keeps its order (R-03).

### R-02 — the per-form homes outside `condition_forms.py` [M]
Opened: `condition_text.py:34-49` (`FORM_PHRASES_FR`), `day_resolve.py:262-285` (`_BLOCKED_DETAIL_FR`), `condition_interpreter.py:94-112` (`TARGET_HINTS_FR`), `writes/conditions.py:59-65` (`_TARGET_ENTITY_TYPE`), `frontend/src/creation/questRequirements.js:1-60` (header: `list` is a key of `GET /api/quest-offers/choices`; `REQUIREMENT_FORMS` at `:21-35`; `STEP_DOMAINS = ['physical', 'agility', 'perception', 'composure']`), `models/config.py:166-183` (`ConditionNode`'s seven CHECKs).
Finding: each is a dict keyed by form. No CHECK names a form: the node CHECKs are `ck_condition_node_op`, `_leaf`, `_connector`, `_subject`, `_role` (`doer`, `giver`, `contact`), `_n`, `_since` (pasted in Gate (c)).
Consequence: a new form is code only, no migration.

### R-03 — the checks that pin the vocabulary [M]
Opened: `tooling/verify/checks/quests.py:105-114` (`MODEL_FORMS`, `CREATOR_FORMS`, `DEBT_FORMS`, `CONDITION_FORMS`), `:155-165` (QA1: `REQUIREMENT_TYPES == MODEL_FORMS + CREATOR_FORMS + DEBT_FORMS + CONDITION_FORMS`; the shape groups partition it), `:797-818` (QC1: `REQUIREMENT_FORMS` keys equal `REQUIREMENT_TYPES` in order, each group in order); `day_plan.py:202-212` (`EXPECTED_REQUIREMENT_TYPES`), `:313-336` (R1: `_EVALUATORS` keys == `REQUIREMENT_TYPES`); `condition_interpreter.py:586-592` (`TARGET_HINTS_FR` keys == `REQUIREMENT_TYPES` in order), `:752-775` (one `form_lines` line per form); `conditions.py:426` (`FORM_PHRASES_FR` key set == `REQUIREMENT_TYPES`).
Finding: two checks hold a literal copy of the tuple (`quests.py` `CONDITION_FORMS`, `day_plan.py` `EXPECTED_REQUIREMENT_TYPES`); the others derive from it.
Consequence: brief A extends the two literal copies; the derived ones go green by A's own additions.

### R-04 — cleaning a leaf [M]
Opened: `writes/conditions.py:87-97` (`_clean_subject`), `:100-110` (`_clean_target`), `:231-248` (`clean_leaf`).
Finding: `_clean_subject` checks one subject (a role of `SUBJECT_ROLES`, or a character of the world unless the form is in `ANY_SUBJECT_TYPES`); `_clean_target` checks an entity target's type against `_TARGET_ENTITY_TYPE[form]` (None: any entity). No form restricts its subject today.
Consequence: `is_character` needs one new rule in `clean_leaf`: its subject is the role `doer`.

### R-05 — where a pipeline table lives, and how a migration moves the schema [M]
Opened: `models/pipeline.py:98-150` (`ProposedMutation`), `:418-445` (`LoreEntry`, `LoreEntryRow`), `:537-570` (`ConditionDraft`); `schema_version.py:15`; `scripts/migrate_v2_27_mutation_reviews.py:1-80`; `writes/worlds.py:64-84` (`_DIRECT_WORLD_SCOPED_DELETES`); `tooling/verify/canon_write_policy.txt:1-13` (`[CANON_TABLES]`); `world-engine-schema-changelog.md:14-24`.
Finding: non-canon pipeline tables live in `models/pipeline.py`; `EXPECTED_STATIC_SCHEMA_VERSION = "v2.27"`; a migration refuses an older database, is idempotent, runs one raw transaction with `foreign_keys` set, post-checks its touched tables with `PRAGMA foreign_key_check`, then moves `schema_meta`; a world's tables are deleted by name in `_DIRECT_WORLD_SCOPED_DELETES` (last line `"event_type_effect", "mutation_review", "mutation_review_change",`); pipeline tables are not in `[CANON_TABLES]`, so `single_canon_write.py` does not police their writers.
Consequence: `quest_request` is a pipeline table in `models/pipeline.py`, v2.28, added to the cascade list.

### R-06 — a proposal row [M]
Opened: `models/pipeline.py:98-150`; `tooling/verify/checks/json_ui_boundary.py:40-130`; `dashboard_deferrals.py:115-119`.
Finding: `proposed_mutation` has no CHECK on `mutation_type`, `source_type`, `status` or `proposed_by`; exactly one source (`pass_play_id`, `conversation_id`, or `tick_id`); `payload` JSON, NOT NULL; `target_id` free text; `ProposedMutation.payload` and `.original_payload` are listed exceptions of `json_ui_boundary.py`.
Finding (cont.): the exemption's justification reads « rendered readonly in the review queue; shape is the mutation type's contract, not a UI field. First structured UI consumer must relationalize » (`json_ui_boundary.py:44-47`); TICKET-0119's typed event card is already such a consumer, and TICKET-0115 registered that condition as reached, without a ticket: `dashboard_deferrals.py:115-119`, `Deferral("payload", "TICKET-0025", ..., _JSON_BOUNDARY, "First structured UI consumer must relationalize.", status="reached")` -- its anchor is that sentence of `json_ui_boundary.py`, found exactly once by DB1.
Consequence: `quest_offer_creation` needs no DDL; its payload carries the draft offer as JSON and the card edits it field by field -- a second structured consumer of a reached deferral, flagged to Nia as a drafting decision; the exemption's comment gains one line naming both cards, its anchor sentence untouched; `quest_request.change_history` (JSON, never rendered) needs its own listed exception.

### R-07 — the producers [M]
Opened: `src/world_engine/proposal_producers.py:16-30`; `CLAUDE.md:194-198` (INV-14).
Finding: seven live values (`local_ai_window`, `local_ai_overhearing`, `local_ai_tick`, `local_ai`, `observed_scene`, `engine`, `engine_roll`), kinds `model`/`engine`/`auto`; INV-14 is enforced by `proposal_producers.py`: every `proposed_by` written in `src/` is a key of `PRODUCERS`.
Consequence: the designer's value is added in the brief that writes it (E).

### R-08 — the dashboard registries [M]
Opened: `dashboard_deferrals.py:1-50` (docstring, `Deferral`), `:50-110` (`DEFERRALS`); `dashboard_metrics.py:36-75` (`Scope`, `Row`, `Metric`), `:258-290` (`METRICS`, `compute_metrics`); `tooling/verify/checks/dashboard_registry.py:1-40` (DB1-DB5).
Finding: a `Deferral(code, ticket, deferred_fr, condition_fr, source, anchor, metric=None, status="open", follow_up=None)`; DB1 finds each `anchor` exactly once in its `source`; a `Metric(key, title, question, watches, dated, compute)` whose `compute(db, scope) -> (rows, note)`; DB2 forbids a JSON column and `text(` in `dashboard_metrics.py`; DB3 compares `dashboard(world=A)` to `EXPECTED` only for the metric keys `EXPECTED` names (`dashboard_registry.py:246-249`), and fails a dated metric that counts anything after tomorrow.
Consequence: B adds one metric and three deferrals, their anchors in the ticket file; DB3 needs no change (the new key is not in `EXPECTED`, and an empty fixture counts zero); the metric's numbers are asserted by B's own check.

### R-09 — the plan finalizer and the route's budget [M]
Opened: `cockpit/routes/day.py:156-175` (`_feasibility_dict`), `:382` (`_plan_step_dict`), `:549-618` (`_finalize_plan`), `:634-704` (`plan_day`); `cockpit/day_reconcile_apply.py:181-207` (`_finalize_replace` calls `_day._finalize_plan`); `tooling/verify/checks/module_budget.py:57-59`; `tooling/verify/checks/day_feasibility.py:161-185` (R4); `day_plan.py:1072-1100` (R27).
Finding: `routes/day.py` is 991 lines (cap 1000), 28 functions (cap 40). `_finalize_plan` runs `anchor_requirements` -> `evaluate_requirements` -> `budget_cut` -> `feasibility_veto` -> blocked index -> `write_day_plan` -> `write_day_feasibility` -> `pass_play.status = "resolving"`, `agenda_id`. R4 and R27 read `_finalize_plan` from the route file by name.
Consequence: D first moves `_finalize_plan`, `_plan_step_dict` and `_feasibility_dict` to `cockpit/day_plan_finalize.py` (pure move, the `day_reconcile_apply.py` precedent) and points R4 and R27 at the new file.

### R-10 — the plan selection [M]
Opened: `day_plan_select.py:1-118`; `scripts/seed_pilot.py:2618-2642` (`DAY_PLAN_SELECT_SYSTEM_PROMPT`, `DAY_PLAN_SELECT_USER_TEMPLATE`), `:2770-2780` (head `pt-day-plan-select`); `prompt_registry.py:371-377`; `scripts/apply_ticket_0119_tick_prompt.py:1-100`.
Finding: `select_plan(declaration, plans, db) -> Optional[Agenda]` returns `None` WITHOUT a model call when `plans` is empty; otherwise one call answering `{"selected": <int or null>, "rationale": ...}`, the ordinal checked. The template's placeholders are `{plans}` and `{declaration}`. A prompt already on the live DB changes through a fragment script that writes a new `prompt_version` and keeps the creator's edits.
Consequence: K1 makes the call on every declaration, empty list included (`(aucun plan ouvert)`), and adds `"route"` to the answer; delivered by `apply_ticket_0121_select_prompt.py` (fragments in `seed_pilot`).

### R-11 — anchoring a knowledge gate [M]
Opened: `day_plan.py:204-220` (`_anchorable_facts`), `:222-245` (`anchor_requirements`), `:285-306` (`_validate_step`: `cost` 1..`DAY_BUDGET_SLOTS`, `domain` in `BASE_SKILL_DOMAINS`), `:337-346` (`_resolve_knowledge_codes`), `:349-408` (`emit_plan`, its call through `ollama_client.chat`).
Finding: a `knowledge` leaf is kept only when its fact is held, in the world, by an entity other than the character, on a row `is_secret == False`. Otherwise the LEAF is dropped -- the step stays, ungated -- and reported `{step_index, objective, target_key}`. A code the model invented stays as emitted and is dropped the same way.
Consequence: R1 -- the first step with a dropped leaf becomes the day's inquiry step and the plan stops there; a secret-only fact reaches the designer through this path.

### R-12 — resolving a day, bands and emitters [M]
Opened: `cockpit/routes/day.py:916-990` (`resolve_day`); `day_resolve.py:95-131` (`StepOutcome`, `StepFact`), `:190` (`BLOCKED_BAND`), `:211-235` (`_roll_included_steps`: `domain is None` -> band `success`), `:237-258` (`_truncate_on_failure`), `:349-390` (`_append_blocked_step`), `:392-426` (`resolve_steps`); `day_narration.py:64-73` (`BAND_MARKERS`, `BAND_LABELS_FR`); `day_mutations.py:114-124` (`_step_action`), `:233-281` (`_emit_new_knowledge`), `:294-321` (`_EMITTERS`, `emit_mutations`); `tooling/verify/checks/day_narration.py:567-615` (R13), `:479-520` (R11: `day_resolve.py` imports no agenda writer, adds and commits nothing); `tooling/verify/checks/day_mutations.py:1-70` (R7: no response of `routes/day.py` carries an agenda or step id).
Finding: `resolve_day` refuses without the character's active agenda. A no-roll step is `success`, so every emitter fires for it (an `agenda_step_change` « complete » among them). `_emit_new_knowledge` proposes a rumor-level lead on a blocked step's unmet `knowledge` verdict (kept, U1). R13 pins `BAND_MARKERS` to exactly four bands with `[BLOQUÉ]`.
Consequence: T1 adds a fifth band `inquiry`: no roll, no emitter, the walk stops after it, its step closed directly; R13 moves to five.

### R-13 — the agenda tables and their writers [M]
Opened: `models/config.py:71-100` (`AgendaStep`: CHECK `status IN ('pending','active','completed','failed')`, one active step per agenda); `models/canon.py:779-797` (`Agenda`: CHECK `status IN ('active','paused','completed','failed','abandoned')`); `writes/goals_agendas.py:289-325` (`write_agenda_step`), `:326-360` (`write_agenda_step_status`), `:532-560` (`write_agenda_status`), `:610-655` (`write_day_plan`); `canon_write_policy.txt:106-107`.
Finding: both status writers append the previous state to `change_history`; they are allow-listed write sites; `write_day_plan` writes one agenda, its steps, their prerequisites.
Consequence: the inquiry day is a one-step plan written by `write_day_plan`; the inquiry band closes its step with `write_agenda_step_status(..., "completed", outcome="inquiry")` and, when no open step remains, the agenda with `write_agenda_status(..., "completed")`.

### R-14 — saving an offer [M]
Opened: `writes/quests.py:108-170` (`write_quest_offer`); `cockpit/routes/quests.py:50-160` (`OfferStepBody`, `TermBody`, `OfferBody`, `_term`, `_save_offer`, `_mark_drafts`); `quest_reads.py:68-105` (`condition_view`, `offer_dict`); `canon_write_policy.txt:56-57`.
Finding: `write_quest_offer` refuses a missing title, an unknown status, a giver that is not a character or faction of the world, a contact outside the faction, any leaf `clean_condition` refuses, any term `clean_terms` refuses against the giver. `_save_offer` runs `attribute_proposals.materialize` (the proposed attributes) -> `PlanStep`s -> `write_quest_offer` -> `_mark_drafts` (each inserted interpreter draft `saved`), then commits. The policy comment on `write_quest_offer` says « creator CRUD only ».
Consequence: E moves the body classes and `_save_offer`'s core to `cockpit/quest_offer_save.py`, called by the route and by the applier; the policy comment names both callers.

### R-15 — approving and applying a proposal [M]
Opened: `cockpit/routes/mutations.py:366-416` (`_find_applied_duplicate`), `:419-475` (`_apply_mutation`, `appliers` at `:453`), `:538-556` (`ApproveBody`, `_approve_apply_edited_payload`), `:645-680` (`approve_mutation`); `cockpit/mutations.py` (931 lines, 22 functions).
Finding: a `pass_play` row reaches the tick-sourced duplicate branch, which has no rule for an unknown type; an unknown type is left `approved` with a note; the edited payload arrives as a JSON string and replaces `mut.payload` before the review is recorded and the applier runs.
Consequence: the applier `_mutation_apply_quest_offer_creation` (in `cockpit/mutations.py`) guards its own duplicate through the request, returns an error string on any refusal, and sets `mut.target_id` to the offer it wrote.

### R-16 — the interpreter's pipeline and journal [M]
Opened: `condition_interpreter.py:171-205` (`build_context`), `:554-566` (`prompt_values`), `:569-655` (`_notes`, `_settle`, `Proposals`, `_answer`, `interpret`, `_retryable`); `writes/condition_drafts.py:45-90` (`PAYLOAD_KEYS`, `write_condition_draft`); `cockpit/routes/conditions.py:110-215` (`_answer`, `interpret`, `resolve` keyed by draft id, `decide`).
Finding: `build_context` codes the facts of the current tree, of the entities the instruction names, then the world-level facts -- creator-only included -- capped at `MAX_CODED_FACTS` (200). `_answer(db, world_id, parsed, ctx, unsaved, retried)` reads ONE answer `{condition, define, define_events, define_sortes, unsupported}` into an `Interpretation(outcome proposed|needs_choice|refused, ...)`, whose `.payload(current)` is a `condition_draft` payload. `/api/conditions/drafts/{id}/resolve` needs a `needs_choice` draft of the active world; `decision` inserts or discards it. No route reads a draft back.
Consequence: the designer writes one `condition_draft` per condition it proposes, through the interpreter's own reader; a pending one's answer travels in the proposal's payload (R-06's exemption), never read back from the draft (`ConditionDraft.payload` is listed « never rendered », `json_ui_boundary.py:118-125`).

### R-17 — the lore consultation [M]
Opened: `lore_selectors.py:1-80`, `:235-300` (`entity_dossier`, `who_knows_about`), `:301-315` (`SELECTORS`, `_SELECTOR_LOOKUPS`); `lore_query.py:63-98` (`validate_plan`), `:141-215` (`execute_plan`, verdicts); `lore_plan.py:32-80` (`_SELECTOR_DESCRIPTIONS`, `_coerce_call`); `lore_render.py:95-125` (`_SECTION_FORMATTERS`, unknown section raises); `facet_reads.py:58-63` (`creator_only_fact_ids`); `prose_render.py:63-84` (`fact_text`, `fact_texts`); `lore_resolve.py:73-90` (`normalize_surface`), `:134-175` (`NamedResolution`, `resolve_named`); `tooling/verify/checks/lore_isolation.py:1-60` (R1, R2, R8, R14, R17).
Finding: three selectors, each keyed by an entity or the world; an argument is `$world` or a mention ref, and `validate_plan` accepts only kinds `entity_id` and `world_id`; verdicts `answered`, `silent_canon`, `unknown_entity`, `ambiguous_mention`, `unsupported_selector` (pasted in Gate (c)). A fact nobody names as an entity is unreachable. `who_knows_about` returns one `coverage` row then `knowers` rows, secrets marked.
Consequence: S2 -- a fourth selector with a new argument kind `text`; the designer calls the selector functions directly (no plan model), the consultation surface gains it through the whitelist.

### R-18 — the Lore writing panel [M]
Opened: `cockpit/routes/lore_write.py:1-75` (docstring, `StatementBody`, `CommitBody {proposal, attempt_id}`), `:140-160` (`write_commit` returns `{ok, entry_id, written, skipped}`); `models/pipeline.py:418-428` (`LoreEntry`); `frontend/src/lore/writePanel.svelte.js:63` (`writeState`), `:357-367` (`commit`); `frontend/src/lore/Lore.svelte:30` (`let loreTab = $state('question')`).
Finding: the commit writes everything in one transaction through `lore_write_apply.apply_proposal`; the panel's tab is local state of `Lore.svelte`; `writeState.statement` holds the text.
Consequence: the commit accepts an optional `quest_request_id` and links the entry to the request in its transaction; the panel opens pre-filled through `writeState`.

### R-19 — prompts [M]
Opened: `prompt_registry.py:50-62` (`PromptSpec`), `:290-300` (`condition_interpret`); `prompt_call.py:1-60` (`call_json`); `scripts/apply_ticket_0112_condition_prompt.py:1-60`; `.claude/rules/prompts.md`.
Finding: a new usage is a `PROMPT_REGISTRY` entry (INV-19) with its `call_sites`, a head in `seed_pilot` and a CREATE-HEAD script that loops the heads through `upsert_prompt_template` (S2: never touches an existing text).
Consequence: E adds `quest_subject` and `quest_design` (authoring, the author model) and `apply_ticket_0121_designer_prompts.py`.

### R-20 — the review card, the queue, the offer editor [M]
Opened: `frontend/src/creation/QueueCard.svelte:1-80` (`typedEvent`, the inline EventEditor precedent), `:200-260`; `Queue.svelte:1-55`; `QuestOffers.svelte:100-200` (the editor, inline); `questOffers.svelte.js:33-175` (`blankStep`, `newDraft`, `editOffer`, `draftBody`, `saveDraft`); `questRequirements.js:190-217` (`conditionDraft`, `blankCondition`, `conditionBody`); `ConditionInterpreter.svelte:20`; `conditionInterpreter.svelte.js:1-60`; `.claude/rules/frontend.md` (INV-49, INV-50, INV-55).
Finding: a typed proposal is edited in place in its card and approved as edited; the offer editor is markup inside `QuestOffers.svelte` bound to `questOffersState.draft`; `editOffer(offer)` reads `offer_dict`'s shape (conditions as `condition_view`s); `draftBody(draft)` gives `OfferBody`'s shape; the interpreter component holds its own state from `interpreterState()`. A child component of `Queue.svelte` is not a Création island.
Consequence: F extracts `OfferEditor.svelte`; G renders `QuestRequests.svelte` inside `Queue.svelte`.

### R-21 — the standing law [M]
Opened: `CLAUDE.md` (20,252 characters, budget 22,000, `claude_md_contract.py:77`), `:131-140` (INV-01), `:227-230` (INV-62); `.claude/rules/mutation-pipeline.md` (2,524 characters, budget 4,000); `tooling/verify/baselines/invariant_ids.retired`.
Finding: INV-01 lists the creator-regime readers « (Lore question, names panel, writing panel, condition interpreter) »; the highest live id is INV-62; ids run on across files.
Consequence: E amends INV-01 to name the quest designer and adds INV-63 to `mutation-pipeline.md`.

### R-22 — secret, for the prose guard [M]
Opened: `day_plan.py:204-220` (`_anchorable_facts`), `facet_reads.py:58-63`.
Finding: a fact the world holds only on `is_secret` rows is not anchorable; a creator-only fact is listed by `creator_only_fact_ids`.
Consequence: V1's « secret » is: a creator-only fact, or a fact no entity holds on a non-secret row (C-10).

### R-23 — judging and describing a tree [M]
Opened: `conditions.py:86` (`Bindings`), `:211` (`all_of(specs)`), `:397` (`evaluate(node, bindings, db) -> Optional[VerdictNode]`), `:512` (`read_condition(db, *, role, **owner)`); `condition_text.py:194` (`describe(db, node, unsaved=None) -> list[dict]`, lines `{"depth", "text"}`); `cockpit/routes/day.py` `_finalize_plan` (`Bindings(doer=character)`).
Finding: a tree is judged with `evaluate(tree, Bindings(doer=<character>), db)` and read in French with `describe(db, tree)`; `all_of` of an empty list is None (no condition).
Consequence: A's check judges and describes an `is_character` leaf through these, never through a copy.

### R-24 — how a DB-backed check builds its fixture [M]
Opened: `tooling/verify/checks/mutation_reviews.py:77-82` (`_fresh_db`), `:269-276` (`main`); `.claude/rules/verify-checks.md`.
Finding: `_fresh_db()` points `WORLD_ENGINE_DATABASE_URL` at a temp file and defaults `WORLD_ENGINE_ENV=test` before any `world_engine` import; `main` then imports `world_engine.models` (registering every table) and runs `SQLModel.metadata.create_all(engine)`; rows go through the real writers; failures collect in `FAILURES`; 15 s per check under `corpus_gate.py`.
Consequence: every new DB-backed check of this lot follows these two functions; a table missing from `create_all` means its model is not exported from `models/__init__.py`.

## Contract sheet

Families first: the request's status family (C-02) is written before any
producer or consumer of a status; the `ROUTE`/`blocked`/`dropped` trigger
family (C-02) before D's three openers (C-07); the band family (C-08)
before the inquiry band. Each family was re-read after its last member.

### C-01 — the form `is_character`
Produced by: BRIEF-0121-A   Consumed by: BRIEF-0121-F
`condition_forms.REQUIREMENT_TYPES` ends `..., "event", "is_character"`; `ENTITY_TARGET_TYPES` ends `..., "item_held", "is_character"`. A leaf `RequirementSpec(type="is_character", subject_role="doer", target_entity_id=<character id>)`. Evaluator `_eval_is_character(req, character, db, reachable_ids) -> Verdict(type="is_character", met=character.id == req.target_entity_id, current=character.id, required=req.target_entity_id, reason=..., required_label=<target name>)`. `clean_leaf` refuses an `is_character` leaf whose subject is not the role `doer` (« is_character judges the one who acts »); its target is a `character` of the world. French: `FORM_PHRASES_FR["is_character"] = "{who} est {target}"`; `_BLOCKED_DETAIL_FR["is_character"] = "cette quête est réservée à {required}"`; `TARGET_HINTS_FR["is_character"] = "un personnage, par son nom (le seul à qui l'offre est proposée)"`; `REQUIREMENT_FORMS.is_character = { label: 'Est le personnage', list: 'characters', column: 'entity', threshold: false }`.
Error and empty cases: a fixed subject or another role -> `ValueError`; an unknown or non-character target -> `ValueError` (existing `_clean_target` message).

### C-02 — `quest_request` (v2.28) and its writer
Produced by: BRIEF-0121-B   Consumed by: D, E, G
Table `quest_request` in `models/pipeline.py`:
`id` TEXT PK; `world_id` FK world NOT NULL; `character_id` FK entity NOT NULL; `pass_play_id` FK pass_play NOT NULL; `agenda_step_id` FK agenda_step NOT NULL; `trigger` TEXT NOT NULL; `declaration` TEXT NOT NULL; `subject` TEXT NULL; `status` TEXT NOT NULL DEFAULT `'new'`; `existence_answer` TEXT NULL; `creator_text` TEXT NULL; `existing_entity_id` FK entity NULL; `lore_entry_id` FK lore_entry NULL; `mutation_id` FK proposed_mutation NULL; `offer_id` FK quest_offer NULL; `note` TEXT NULL; `created_at`, `updated_at` (`_created_ts()`); `change_history` JSON NOT NULL DEFAULT `'[]'`.
CHECKs: `ck_quest_request_trigger` `trigger IN ('route','blocked','dropped')`; `ck_quest_request_status` `status IN ('new','asking','writing_lore','proposed','covered','dropped')`; `ck_quest_request_answer` `existence_answer IS NULL OR existence_answer IN ('exists','absent','already')`.
Indexes: `idx_quest_request_world` (`world_id`, `created_at`); `idx_quest_request_step` UNIQUE (`agenda_step_id`): one request per step.
Constants in `writes/quest_requests.py`: `QUEST_REQUEST_TRIGGERS = ("route", "blocked", "dropped")`, `QUEST_REQUEST_STATUSES = ("new", "asking", "writing_lore", "proposed", "covered", "dropped")`, `EXISTENCE_ANSWERS = ("exists", "absent", "already")`, `QUEST_OFFER_CREATION = "quest_offer_creation"`, `DESIGNER_PRODUCER = "local_ai_quest_designer"`.
Writer:
- `open_request(db, *, world_id, character_id, pass_play_id, trigger, declaration, agenda_step_id) -> QuestRequest` -- `ValueError` on an unknown trigger, an empty declaration, a missing step; a step that already has a request returns that request unchanged (idempotent per step). Adds and flushes, never commits.
Reads in `src/world_engine/quest_requests.py`: `inquiry_step_ids(db, agenda_id) -> frozenset[str]` -- the `agenda_step_id`s of the requests on that agenda's steps whose trigger is `route` or `dropped`.
- `move_request(db, request, status, **fields) -> QuestRequest` -- appends `{status, updated_at, <every field it changes, before>}` to `change_history`, then sets `status`, `updated_at` and the given fields (only `subject`, `existence_answer`, `creator_text`, `existing_entity_id`, `lore_entry_id`, `mutation_id`, `offer_id`, `note`); `ValueError` on an unknown status, an unknown field, an answer outside `EXISTENCE_ANSWERS`. Never commits.
Status meanings: `new` -- waits for « Concevoir »; `asking` -- the subject is unknown, the existence question is shown; `writing_lore` -- answered `exists` or `absent`, the Lore panel is open for it; `proposed` -- a `quest_offer_creation` (`mutation_id`) exists; whether it was approved or rejected is that row's `status`, never a second column; `covered` -- an open offer already covers it (`offer_id`); `dropped` -- the creator set it aside. Re-design is allowed from `new`, `covered`, and `proposed` when its proposal is `rejected`; refused otherwise (C-12).

### C-03 — the « Demandes de quête » metric and three deferrals
Produced by: BRIEF-0121-B   Consumed by: (Suivi)
`dashboard_metrics.METRICS` gains, last, `Metric("quest_requests", "Demandes de quête", "D'où viennent les demandes de quête, et que deviennent-elles ?", ("P1", "S3", "D2"), True, _quest_requests)`. Rows, in this order: group `Origine` -- one row per trigger (`route` « Déclaration aiguillée », `blocked` « Étape bloquée », `dropped` « Savoir introuvable »), value = requests of that trigger, `of` = the requests in scope; plus one row « Journées aiguillées vers une quête », value = `route` requests, `of` = `pass_play` rows with `submitted_at` in scope and a non-null `agenda_id` (P1); group `Existence` -- one row per answer of `EXISTENCE_ANSWERS` (« Elle existe », « Elle n'existe pas », « Le lore le disait déjà ») (S3); group `Donneur` -- « Offres approuvées », value = requests whose proposal is `applied`; « Donneur créé après la proposition », value = those whose offer's giver entity has `created_at` after the proposal's `proposed_at`, `of` = the approved ones (D2). Relational columns only (DB2). Dated on `quest_request.created_at`.
`dashboard_deferrals.DEFERRALS` gains, last, three entries, `ticket="TICKET-0121"`, `source=_T0121 = "tooling/tickets/TICKET-0121-journee-quest-designer.md"`, `metric="quest_requests"`:
- `D2` -- « Le concepteur invente un donneur, créé à l'approbation. » / « Nia crée souvent un PNJ juste pour donner une offre proposée. » / anchor `D2 (an invented giver; reactivation: the creator often creates a character just to give a proposed offer)`;
- `S3` -- « Une recherche du lore par le sens. » / « Des demandes où Nia répond que le lore le disait déjà. » / anchor `S3 (a search by meaning; reactivation: requests the creator answers « the lore already says it »)`;
- `P1` -- « Revoir l'outil de plan en plan global. » / « La part des journées aiguillées vers une quête le demande. » / anchor `P1 (the plan tool reworked; reactivation: the share of days routed to a quest asks for it)`.
Error and empty cases: no request in scope -> every row with value 0 (rows are always emitted).

### C-04 — `facts_mentioning` and the `text:` argument
Produced by: BRIEF-0121-C   Consumed by: C-05, the Lore consultation
`lore_selectors.facts_mentioning(text: str, world_id: str, db: Session) -> list[dict]`. `text` is the words to look for (the argument without its `text:` prefix). A fact of the world matches when every token of `normalize_surface(text)` of length >= 3 (at least one such token, else no row) appears among the tokens of `normalize_surface(<the fact's rendered text>)` -- compared in Python, never in SQL. Rows: one `coverage` row first `{section: "coverage", subject_name: <text>, counted_rows: <n facts>, uncounted_rows: 0}`, then per matching fact, ordered by its rendered text then id, `{section: "mentions", fact_id, content, creator_only: bool, participants: [<names>], knowers: [{knower_entity_id, knower_name, level, is_secret}]}` (knowers by level rank descending then name). Creator-only facts included and marked (the dossier's precedent, INV-01's creator regime). `SelectorSpec(fn=facts_mentioning, arity=2, row_cap=200, arg_kinds=("text", "world_id"), context_sections=("coverage",))`; `SELECTORS` ends `..., "facts_mentioning"`. `validate_plan`: an argument of kind `text` must start `text:` and hold a non-empty rest; `execute_plan` passes the rest. `_SELECTOR_DESCRIPTIONS["facts_mentioning"] = 'facts_mentioning("text:<mots>", $world) -- les faits dont le texte contient ces mots (un sujet qui n\'est pas une entité nommée), avec ceux qui les savent.'`; `lore_render._SECTION_FORMATTERS["mentions"]` renders `« <content> » -- <participants> ; su par <name (level, secret)>, ...`.
Error and empty cases: no token of 3 letters or more -> `[coverage]` only (counted 0) -> `silent_canon`.

### C-05 — the designer's lore gathering
Produced by: BRIEF-0121-C   Consumed by: BRIEF-0121-E
`quest_lore.gather_lore(db, world_id, *, keywords: list[str], names: list[str], entity_ids: tuple[str, ...] = (), lore_entry_id: Optional[str] = None) -> LoreGathering`.
`LoreGathering(fact_ids: tuple[str, ...], entity_ids: tuple[str, ...], lines: tuple[str, ...], empty: bool)`:
- `entity_ids`: `entity_ids` given, then each name of `names` resolved by `lore_resolve.resolve_named(name, "other", world_id, db, scope=CREATOR)` when `matched` (an ambiguous or unmatched name is skipped -- the designer sees what is certain);
- `fact_ids`, in order, de-duplicated: the facts of `facts_mentioning(" ".join(keywords))` (each keyword on its own when the joined call finds nothing), then every fact with a `fact_participant` on each entity of `entity_ids`, then the facts of the `lore_entry_row` rows of `lore_entry_id` whose `row_table = 'fact'`;
- `lines`: one line per fact, `« <text> » -- su par <name> (<level><, secret>), ...` or `« <text> » -- su de personne`, creator-only facts suffixed `(réservé à la créatrice)`;
- `empty`: no fact found.
Reads only. Creator regime: every fact, creator-only included (INV-01, amended by E).

### C-06 — the plan selection's answer
Produced by: BRIEF-0121-D   Consumed by: `plan_day`
`day_plan_select.PlanSelection(agenda: Optional[Agenda], route: str)` with `route in PLAN_ROUTES = ("plan", "quest")`. `select_plan(declaration, plans, db) -> PlanSelection`: ALWAYS one model call; an empty `plans` renders `(aucun plan ouvert)`. Answer `{"selected": <int or null>, "route": "plan" | "quest", "rationale": "..."}`; `selected` non-null -> `PlanSelection(plans[selected-1], "plan")` whatever `route` says; null -> `PlanSelection(None, route)`; a missing or unknown `route` with `selected` null -> `LlmParseError` (never a silent default). Fragments `seed_pilot.DAY_PLAN_SELECT_FRAGMENTS_0121`, delivered by `scripts/apply_ticket_0121_select_prompt.py`.

### C-07 — the three openers of a request
Produced by: BRIEF-0121-D   Consumed by: (the request list)
In `cockpit/day_plan_finalize.py`:
- `finalize_inquiry_day(world_id, character, pass_play, rendered, db) -> dict` (K1): writes, through `write_day_plan`, a one-step plan titled like `_finalize_plan`'s title, its step `objective = "Se renseigner : " + <rendered first line, 180 chars>`, `cost = 1`, `domain = None`, no prerequisite, `active_step_index = 0`; opens `open_request(trigger="route", declaration=rendered, agenda_step_id=<the plan's one step>)`; records no feasibility entry; `pass_play.status = "resolving"`, `agenda_id`; commits; returns the `/plan` response with the one step and `"inquiry": true`.
- in `_finalize_plan`, after the blocked index: when a step is blocked on an unmet prerequisite (the existing `blocked_index`), `open_request(trigger="blocked", declaration=<that step's objective>, agenda_step_id=<its row>)` (K1b);
- in `_finalize_plan`, after anchoring and BEFORE `write_day_plan`: when `dropped` is non-empty, the first step index with a dropped leaf `k` becomes the inquiry step -- steps after `k` are NOT written (reported `inquiry_cut: <n>` in the response); the plan is written with `k`'s requirements as anchored; `open_request(trigger="dropped", declaration=<k's objective>, agenda_step_id=<k's row>)` (R1). A blocked index before `k` keeps its existing meaning and also opens its `blocked` request.
Every opener runs after `write_day_plan`, reading the written step rows by `agenda_id` and `step_order`. `resolve_steps` reads the inquiry steps through `quest_requests.inquiry_step_ids` (C-02).

### C-08 — the `inquiry` band
Produced by: BRIEF-0121-D   Consumed by: narration, emitters
`day_resolve.INQUIRY_BAND = "inquiry"`. `resolve_steps` gives an included step whose id is in `inquiry_step_ids(db, agenda.id)` the band `inquiry` (no roll, `verdict=None`) and stops the walk after it (like `failure`). `BAND_MARKERS["inquiry"] = "[RECHERCHE]"`; `BAND_LABELS_FR["inquiry"] = "recherche en cours, sans réponse encore"`. `emit_mutations` skips an `inquiry` outcome (no emitter runs). `_finalize_resolution` closes each `inquiry` outcome's step: `write_agenda_step_status(step, "completed", outcome="inquiry")`, then `write_agenda_status(agenda, "completed")` when the agenda has no `pending`/`active` step left -- direct writes, in the resolution's transaction (T1: a decision of 0121, not a proposal; V1 of 0075 keeps every other step transition). A replay finds the step `completed` and does not walk it again (`_load_evaluated_steps` excludes terminal steps).

### C-09 — the shared offer save
Produced by: BRIEF-0121-E   Consumed by: `routes/quests.py`, C-11
`cockpit/quest_offer_save.py`: `OfferStepBody`, `TermBody`, `OfferBody` (moved verbatim from `routes/quests.py`), `term_spec(term) -> TermSpec` (was `_term`), `save_offer_body(db, world_id, body: OfferBody, offer: Optional[QuestOffer]) -> QuestOffer` (was `_save_offer`'s try block plus `_mark_drafts`, without the commit and without the HTTP mapping: `ValueError` propagates). `routes/quests.py::_save_offer` maps `ValueError` to 422, commits, returns `offer_dict`.

### C-10 — the `quest_offer_creation` proposal
Produced by: BRIEF-0121-E   Consumed by: F, G
A `ProposedMutation(world_id, source_type="pass_play", pass_play_id=<request's>, mutation_type="quest_offer_creation", target_table="quest_offer", payload=<below>, status="proposed", proposed_by="local_ai_quest_designer", rationale="quest request <id> -- <subject>")`.
Payload -- `OfferBody`'s keys, plus the review's own:
```
{
  "request_id": str, "character_id": str, "subject": str,
  "giver_entity_id": "", "contact_entity_id": null,
  "giver_suggestions": [{"entity_id": str, "name": str, "type": str}],   # 0..3
  "title": str, "summary": str, "repeatable": false, "status": "open",
  "eligibility": <tree dict> | null, "eligibility_draft_id": str | null,
  "steps": [{"objective": str, "cost": 1..4, "domain": str | null,
             "prerequisite": <tree> | null, "completion": <tree> | null, "failure": <tree> | null,
             "prerequisite_draft_id": ..., "completion_draft_id": ..., "failure_draft_id": ...}],
  "terms": [<TermBody dict>],
  "unsaved_attributes": [],
  "pending_drafts": [{"where": "eligibility" | "steps.<i>.<role>", "answer": <the dict `routes/conditions.py::_answer` returns for that draft, plus "instruction" and "role">}],   # AMENDMENT-0121-01: needs_choice, refused, or proposed while it proposes a state, an event type or a sorte
  "notes": [str],
  "consulted_fact_ids": [str],
  "secret_fact_ids": [str],
  "flags": [{"path": "title" | "summary" | "steps.<i>.objective", "fact_id": str, "words": str}],
  "flags_confirmed": false
}
```
A condition the designer proposed cleanly is in its tree, its `*_draft_id` the draft it came from; one that needs a name, was refused, or proposes a state, an event type or a sorte (AMENDMENT-0121-01) has tree `null` and appears in `pending_drafts`.
`prose_guard.flags(db, texts: dict[str, str], fact_ids: list[str]) -> list[dict]`: for each text and each fact, the first run of >= 4 consecutive tokens of `normalize_surface(text)` that is also a run of `normalize_surface(<fact text>)`; `secret_ids(db, world_id, fact_ids) -> list[str]` (R-22's definition).
Applier `cockpit/mutations.py::_mutation_apply_quest_offer_creation(mut, payload, db) -> Optional[str]`: refuses (returns the error) when the request is missing or its `mutation_id` is not `mut.id`; when `giver_entity_id` is empty; when `prose_guard.flags` recomputed on the payload's title, summary and objectives against `secret_fact_ids` is non-empty and `flags_confirmed` is not `true`; when `pending_drafts` is non-empty; on any `ValueError` of `save_offer_body` (the message). Otherwise writes the offer through `save_offer_body(db, world_id, OfferBody.model_validate(<OfferBody keys>), None)` -- the drafts it marks are exactly those the payload's `*_draft_id` fields name: `proposed` -> `inserted` -> `saved`, `inserted` -> `saved`, any other left alone (AMENDMENT-0121-01, D-02) -- sets `mut.target_id = offer.id`, `move_request(request, "proposed", offer_id=offer.id)`. Writes nothing on refusal.

### C-11 — the designer
Produced by: BRIEF-0121-E   Consumed by: C-12
`quest_designer.design(db, request: QuestRequest, exchanges=None) -> DesignResult(outcome, mutation: Optional[ProposedMutation], notes: list[str])`, `outcome in ("proposed", "asking", "covered", "refused")`:
1. `quest_subject` call (`prompt_call.call_json`): values `{character_name, declaration, existing}` -> `{"subject": str, "keywords": [str], "names": [str]}`; `LlmParseError` when `subject` is empty.
2. `gather_lore(keywords, names, entity_ids=(existing_entity_id,) if set, lore_entry_id)`.
3. `empty` and no `existence_answer` -> `move_request(asking, subject=...)`, outcome `asking`, no further call.
4. `quest_design` call: values `{character_name, declaration, subject, lore, forms, facts, offers, skills, attributes, event_types, entities, entity_types, existence}` from `condition_interpreter.build_context(db, world_id, <declaration + subject>, None, (), extra_fact_ids=gathering.fact_ids)` and `prompt_values`' formatting. Answer:
```
{"outcome": "offer" | "covered" | "unknown",
 "covered_by": "q<n>", "unknown": str,
 "title": str, "summary": str, "givers": [str],
 "eligibility": <answer>, "steps": [{"objective": str, "cost": int, "domain": str | null,
     "prerequisite": <answer>, "completion": <answer>, "failure": <answer>}],
 "terms": [{"direction": "cost" | "reward", "currency": str, "target": str | null, "amount": int | null, "level": str | null}],
 "notes": [str]}
```
where `<answer>` is null or `{"phrase": str, "condition": ..., "define": ..., "define_events": ..., "define_sortes": ..., "unsupported": ...}` -- exactly the interpreter's answer plus `phrase`.
5. `covered` with a `q` code of an open offer -> `move_request(covered, offer_id=...)`; `unknown` -> `move_request(asking, note=<unknown>)`.
6. `offer`: each `<answer>` through `condition_interpreter.settle_answer(db, world_id, parsed, ctx, (), retried)` and `write_condition_draft(attempt_id=request.id, role, instruction=phrase, outcome, payload=interp.payload(None), model_calls=[])`; one more `quest_design` call carrying every retryable error when any condition is `refused` for a reason other than an unknown name (II1); givers by name (`resolve_named`, kinds `person`/`faction`, matched only, at most 3); terms by code (`f`, `s`) or name (items, counterparties), an unresolved term dropped with a note; a fact the gathering holds that no entity knows -> a note « Personne ne sait encore : <fact> » (the creator is warned, nothing invented); flags (C-10); the proposal added; `move_request(proposed, subject=..., mutation_id=...)`.
`OllamaError` and `LlmParseError` propagate; nothing is written then.

### C-12 — the request routes
Produced by: BRIEF-0121-E   Consumed by: G
`cockpit/routes/quest_requests.py`, every POST behind the origin guard like every write route:
- `GET /api/quest-requests` -> `[{id, trigger, status, declaration, subject, character_name, day_number, existence_answer, creator_text, note, created_at, proposal: {id, status} | null, offer: {id, title} | null}]`, newest first, the active world, `dropped` excluded.
- `POST /api/quest-requests/{id}/design` -> runs C-11, commits, returns the request dict plus `{outcome, notes}`; 409 when re-design is not allowed (C-02); 503 `DESIGNER_UNAVAILABLE_MESSAGE` on `OllamaError`; 502 on `LlmParseError`.
- `POST /api/quest-requests/{id}/answer` `{answer: "exists" | "absent" | "already", text: str, entity_id: str | null}` -> `asking` only (409 otherwise); `exists`/`absent` -> `writing_lore`, `creator_text`; `already` needs an entity of the world -> `new`, `existing_entity_id`; returns `{request, statement}` where `statement` is the Lore panel's pre-filled text (`exists`: `"<subject> : <text>"`; `absent`: `"<subject> n'existe pas dans ce monde. <text>"`; `already`: null).
- `POST /api/quest-requests/{id}/drop` -> `dropped` (from any status but `proposed` with a pending proposal: 409).
- `CommitBody.quest_request_id: Optional[str]` (`routes/lore_write.py`): when set, the request must be `writing_lore` of the active world (422 otherwise, before `apply_proposal`); after a successful apply, in the same transaction, `move_request(new, lore_entry_id=<entry_id>)`.

### C-13 — the interpreter's reuse points
Produced by: BRIEF-0121-E   Consumed by: C-11, F
- `build_context(..., unsaved=(), extra_fact_ids: tuple[str, ...] = ())`: `extra_fact_ids` first, then what it codes today; the cap unchanged.
- `settle_answer(db, world_id, parsed, ctx, unsaved, retried) -> Interpretation`: the public name of `_answer` (`_answer` stays, delegating, for its two callers).
- `routes/conditions.py::answer_dict(draft, result, db, unsaved) -> dict`: the public name of `_answer` (`_answer` stays, delegating) -- the designer builds each pending condition's answer with it, at proposal time, into the proposal's payload. No route reads a draft back: `ConditionDraft.payload` stays never rendered (`json_ui_boundary.py`).
- `POST /api/conditions/view` `{tree, unsaved_attributes}` -> `condition_view` of the cleaned tree; 422 on a tree `clean_condition` refuses.

### C-14 — the review card and the request panel
Produced by: BRIEF-0121-F (card), BRIEF-0121-G (panel)   Consumed by: Nia
- `frontend/src/creation/OfferEditor.svelte` props `{draft, choices, seeds = {}, onchange}` -- the editor markup of `QuestOffers.svelte` (title to terms and value), bound to `draft`; `seeds[<where>]` an interpreter answer for one condition (`pending_drafts`, C-10), passed to its `ConditionEditor` as `seed`.
- `ConditionEditor` and `ConditionInterpreter` accept `seed` (a `pending_drafts[i].answer` of the payload, C-10): the interpreter opens on it, as after « Interpréter »; « Choisir », « Insérer » and « Écarter » go through the existing draft routes by its `draft_id`.
- `questOffers.svelte.js`: `draftFromProposal(payload, views) -> draft` and `proposalBody(draft, payload) -> payload` (`draftBody(draft)` plus the payload's review keys, `flags_confirmed`).
- `QueueCard.svelte`: a `quest_offer_creation` in `proposed` renders `OfferEditor` (giver from every character and faction, suggestions first), « Quête unique » (adds or removes the leaf `is_character` doer -> `payload.character_id` in the eligibility list), the flags with « Je confirme » (sets `flags_confirmed`), the notes; « Approuver » sends `proposalBody` as the payload. Choosing a giver adds the leaf `has_met` doer -> the giver (the contact when the giver is a faction and a contact is set), once, removable (E1).
- `frontend/src/creation/QuestRequests.svelte`, rendered by `Queue.svelte` above the card list: one row per request -- declaration, day, trigger, status -- with « Concevoir » (`new`, `covered`, rejected), the existence question (`asking`: « Elle existe » + text, « Elle n'existe pas » + text, « Le lore le dit déjà » + entity), « Écrire dans Lore » (`writing_lore`), « Mettre de côté », and a link to its proposal's card.
- `writeState.questRequestId` (`writePanel.svelte.js`): set with `statement` before `navigate('lore')`; `Lore.svelte` opens « Écrire » when it is set; `commit()` sends it as `quest_request_id`, then calls `/design` and clears it.

## Gate output

### (a) Property trace

One line per property the briefs assert about `main`: property -- finding -- declaring file opened.

- the form order and its 13 members -- R-01 -- `condition_forms.py`.
- `ENTITY_TARGET_TYPES`' members and order -- R-01 -- `condition_forms.py`.
- the evaluator signature and `Verdict`'s fields -- R-01 -- `condition_forms.py`.
- each per-form dict and its file -- R-02 -- `condition_text.py`, `day_resolve.py`, `condition_interpreter.py`, `writes/conditions.py`, `questRequirements.js`.
- no CHECK names a form -- R-02 -- `models/config.py` (`ConditionNode.__table_args__`).
- the two literal copies of the tuple -- R-03 -- `checks/quests.py`, `checks/day_plan.py`.
- the derived equalities -- R-03 -- `checks/condition_interpreter.py`, `checks/conditions.py`, `checks/day_plan.py`.
- `_clean_subject`/`_clean_target` rules -- R-04 -- `writes/conditions.py`.
- pipeline tables' home -- R-05 -- `models/pipeline.py`.
- the current schema version -- R-05 -- `schema_version.py`.
- the migration's refuse/idempotent/one-transaction/post-check shape -- R-05 -- `scripts/migrate_v2_27_mutation_reviews.py`.
- the cascade list and its last line -- R-05 -- `writes/worlds.py`.
- pipeline tables are outside `[CANON_TABLES]` -- R-05 -- `canon_write_policy.txt`.
- `proposed_mutation` has no CHECK on type/source/status/producer, `target_id` free -- R-06 -- `models/pipeline.py`.
- the payload exemption's justification and its reached deferral (anchor sentence) -- R-06 -- `checks/json_ui_boundary.py`, `dashboard_deferrals.py`.
- the payload's JSON exemptions -- R-06 -- `checks/json_ui_boundary.py`.
- the seven producers and INV-14's check -- R-07 -- `proposal_producers.py`, `CLAUDE.md`.
- `Deferral`/`Metric` fields; DB1-DB3 rules, DB3 limited to `EXPECTED`'s keys -- R-08 -- `dashboard_deferrals.py`, `dashboard_metrics.py`, `checks/dashboard_registry.py`.
- `routes/day.py` 991 lines / 28 functions; caps 1000/40 -- R-09 -- `routes/day.py` (measured), `checks/module_budget.py`.
- `_finalize_plan`'s order and R4/R27 reading it by name -- R-09 -- `routes/day.py`, `checks/day_feasibility.py`, `checks/day_plan.py`.
- `_finalize_replace` calls `_day._finalize_plan` -- R-09 -- `cockpit/day_reconcile_apply.py`.
- `select_plan` skips the call on an empty list; its answer keys; its placeholders -- R-10 -- `day_plan_select.py`, `scripts/seed_pilot.py`.
- the fragment delivery pattern -- R-10 -- `scripts/apply_ticket_0119_tick_prompt.py`.
- anchorable = held by another entity on a non-secret row; a dropped leaf leaves the step ungated -- R-11 -- `day_plan.py`.
- `resolve_day` needs the active agenda -- R-12 -- `routes/day.py`.
- no-roll = `success`; failure stops the walk; blocked appended -- R-12 -- `day_resolve.py`.
- the four band markers and R13 -- R-12 -- `day_narration.py`, `checks/day_narration.py`.
- every emitter runs on every outcome; the blocked lead -- R-12 -- `day_mutations.py`.
- the two status CHECKs, the one-active index -- R-13 -- `models/config.py`, `models/canon.py`.
- the status writers append history and are allow-listed -- R-13 -- `writes/goals_agendas.py`, `canon_write_policy.txt`.
- `write_quest_offer`'s refusals; `_save_offer`'s sequence; the policy comment -- R-14 -- `writes/quests.py`, `routes/quests.py`, `canon_write_policy.txt`.
- the duplicate branch for `pass_play` rows; unknown type -> approved; edited payload as JSON string -- R-15 -- `routes/mutations.py`.
- `build_context`'s fact order and cap; `_answer`'s input and output; the draft payload keys; resolve needs `needs_choice` -- R-16 -- `condition_interpreter.py`, `writes/condition_drafts.py`, `routes/conditions.py`.
- three selectors; arg kinds; verdicts; unknown section raises; R8 -- R-17 -- `lore_selectors.py`, `lore_query.py`, `lore_render.py`, `checks/lore_isolation.py`.
- `CommitBody`'s fields and the commit's answer; the tab is local state -- R-18 -- `routes/lore_write.py`, `Lore.svelte`, `writePanel.svelte.js`.
- a new usage = registry entry + seed head + CREATE-HEAD script -- R-19 -- `prompt_registry.py`, `scripts/apply_ticket_0112_condition_prompt.py`.
- the inline-editor precedent; the editor inside `QuestOffers.svelte`; `editOffer`/`draftBody` shapes -- R-20 -- `QueueCard.svelte`, `QuestOffers.svelte`, `questOffers.svelte.js`.
- CLAUDE.md's size and budget; INV-01's list; the highest id -- R-21 -- `CLAUDE.md`, `checks/claude_md_contract.py`, `invariant_ids.retired`.
- `evaluate`/`Bindings`/`describe`/`all_of`/`read_condition` signatures -- R-23 -- `conditions.py`, `condition_text.py`.
- a DB-backed check's fixture setup -- R-24 -- `checks/mutation_reviews.py`.

### (b) Case tables

**The request's statuses (C-02) -- what each action does.**

| status | « Concevoir » | answer | Lore commit | « Mettre de côté » |
|---|---|---|---|---|
| `new` | runs -> `asking` / `covered` / `proposed` | 409 | 422 | `dropped` |
| `asking` | 409 | `exists`/`absent` -> `writing_lore`; `already` -> `new` | 422 | `dropped` |
| `writing_lore` | 409 | 409 | -> `new` + `lore_entry_id` | `dropped` |
| `proposed`, proposal `proposed` | 409 | 409 | 422 | 409 |
| `proposed`, proposal `applied` | 409 | 409 | 422 | `dropped` (the offer stays) |
| `proposed`, proposal `rejected` | runs (a new proposal) | 409 | 422 | `dropped` |
| `proposed`, proposal `approved` (Needs attention) | 409 | 409 | 422 | 409 |
| `covered` | runs | 409 | 422 | `dropped` |
| `dropped` | 409 | 409 | 422 | 409 |

Every outcome reachable; `asking` is the only door to `writing_lore`.

**What opens a request at `/plan` (C-06, C-07).**

| selection | blocked index | dropped leaf | result |
|---|---|---|---|
| `selected` = n | -- | -- | reconcile path, unchanged; no request |
| null, `route = "quest"` | -- | -- | inquiry day (one step), request `route` |
| null, `route = "plan"` | none | none | the plan as today |
| null, `"plan"` | at i | none | the plan as today + request `blocked` on i |
| null, `"plan"` | none | first at k | plan cut after k, k inquiry, request `dropped` on k |
| null, `"plan"` | at i < k | first at k | plan cut after k; request `blocked` on i; request `dropped` on k (never walked today: the walk stops at i) |
| null, `"plan"` | at i, i >= k | first at k | the plan is cut after k, so i > k is never written; i = k is impossible (a dropped leaf is gone before evaluation); request `dropped` on k only |
| pinned quest (`quest_id`, O1) | -- | -- | unchanged: no selection call, no request |

**The bands (C-08).**

| band | rolled | emitters | walk | step afterwards |
|---|---|---|---|---|
| `success` | yes, or no roll | all | continues | by proposal (V1) |
| `partial` | yes | all | continues | by proposal |
| `failure` | yes | all | stops | by proposal |
| `blocked` | no | `_emit_new_knowledge` only (U1) | appended last | unchanged |
| `inquiry` | no | none | stops | `completed` directly (T1) |

**The applier (C-10).**

| condition | result |
|---|---|
| request missing / `mutation_id` != this row | error, nothing written |
| no giver | error « Choisis un donneur. » |
| flags recomputed non-empty, `flags_confirmed` not true | error « Confirme les passages qui répètent un secret. » |
| `pending_drafts` non-empty | error « Des conditions attendent encore un choix. » |
| `save_offer_body` refuses | its message |
| otherwise | offer written, `target_id`, request `offer_id` |

### (c) Enumerations

`REQUIREMENT_TYPES` (`condition_forms.py:81-91`):
```
"knowledge", "relation_gte", "resource", "location_reachable",
"has_met", "faction_member", "skill_rank_gte", "quest_state",
"has_debt_to", "no_debt_to", "item_held", "attribute", "event",
```
`ConditionNode` CHECKs (`models/config.py:169-183`): `ck_condition_node_op`, `ck_condition_node_leaf`, `ck_condition_node_connector`, `ck_condition_node_subject`, `ck_condition_node_role`, `ck_condition_node_n`, `ck_condition_node_since` -- none names a form.
`SELECTORS` (`lore_selectors.py:301`): `("entity_dossier", "world_factions", "who_knows_about")`; arg kinds in `_SELECTOR_LOOKUPS`: `("entity_id", "world_id")`, `("world_id",)`, `("entity_id", "world_id")`.
Lore verdicts (`lore_query.py:159-212`): `unsupported_selector`, `ambiguous_mention`, `unknown_entity`, `answered`, `silent_canon`.
`BAND_MARKERS` (`day_narration.py:64-66`): `success`, `partial`, `failure`, `blocked`.
`PRODUCERS` (`proposal_producers.py:16-24`): `local_ai_window`, `local_ai_overhearing`, `local_ai_tick`, `local_ai`, `observed_scene`, `engine`, `engine_roll`.
`proposed_mutation` CHECKs: none (`models/pipeline.py:100-105`: four indexes only).
Module sizes (measured, `ast` count of module functions + methods; physical lines): `routes/day.py` 28/991; `cockpit/mutations.py` 22/931; `routes/mutations.py` 23/806; `day_resolve.py` 14/530; `condition_interpreter.py` 31/704; `condition_forms.py` 23/593; `writes/conditions.py` 14/333; `lore_selectors.py` 10/315; `routes/quests.py` 17/301; `day_plan.py` 17/408; `routes/conditions.py` 9/226; `routes/lore_write.py` 9/165; `dashboard_metrics.py` 18/295.
Negative claims and what was looked at:
- « no route reads a condition draft back » -- `grep -n "@router" routes/conditions.py`: `interpret` (POST), `drafts/{id}/resolve` (POST), `drafts/{id}/decision` (POST).
- « no existing check is named `character_form`, `lore_facts_mentioning`, `journee_inquiry`, `quest_designer`, `quest_review_card`, `quest_request_panel`, `quest_requests` » -- `ls tooling/verify/checks | grep -E "quest|character|inquiry|designer|mentions|request"`: `quest_rewards.py`, `quests.py`.
- « no form restricts its subject today » -- `_clean_subject` (`writes/conditions.py:87-97`) is the only subject rule; `clean_leaf` calls it for every form.

### (d) Families
The status family (C-02), the trigger family (C-02/C-07), the band family (C-08) and the payload's keys (C-10 against `OfferBody`, R-14) were written before their members and re-read after the last. ✓

### (e) Gates and the modules that satisfy them

- `character_form.py` (A) -- `condition_forms.py`, `condition_text.py`, `day_resolve.py`, `condition_interpreter.py`, `writes/conditions.py`, `questRequirements.js`; needs nothing it forbids.
- existing `quests.py` QA1/QC1, `day_plan.py` R1/R2, `condition_interpreter.py`, `conditions.py` (A passes them) -- A's two literal copies extended.
- `quest_requests.py` (B) -- `models/pipeline.py`, `writes/quest_requests.py`, the migration, `writes/worlds.py`, `dashboard_metrics.py`, `dashboard_deferrals.py`.
- existing `dashboard_registry.py` DB1-DB3 (B passes it) -- anchors live in the ticket file, which Nia deposits before execution (DB1 reads it); DB3 compares only `EXPECTED`'s keys.
- existing `json_ui_boundary.py` (B passes it) -- B lists `QuestRequest.change_history`.
- existing `world_cascade`-related rules (B passes them) -- the cascade list.
- `lore_facts_mentioning.py` (C) -- `lore_selectors.py`, `lore_query.py`, `lore_plan.py`, `lore_render.py`, `quest_lore.py`.
- existing `lore_isolation.py` R1/R2/R8/R14 (C passes it) -- the selector is pure and world-scoped at construction; its description; its formatter.
- `journee_inquiry.py` (D) -- `day_plan_select.py`, `cockpit/day_plan_finalize.py`, `day_resolve.py`, `day_narration.py`, `day_mutations.py`, `writes/quest_requests.py`.
- existing `day_narration.py` R13, `day_feasibility.py` R4, `day_plan.py` R15/R27, `module_budget.py` (D passes them) -- R13 to five bands; R4/R27 re-pointed at `day_plan_finalize.py`; the pure move frees the route.
- `quest_designer.py` (E) -- `quest_designer.py`, `prose_guard.py`, `cockpit/quest_offer_save.py`, `cockpit/mutations.py`, `cockpit/routes/quest_requests.py`, `cockpit/routes/lore_write.py` (the commit's link), `condition_interpreter.py`; it uses a stubbed `chat` (the `condition_interpreter.py` check's precedent) -- no live model.
- existing `proposal_producers.py`, `prompt_registry.py`, `single_canon_write.py`, `claude_md_contract.py` (E passes them) -- the producer entry, the two registry entries, the policy comment, INV-01 and INV-63 within budget.
- `quest_review_card.py` (F) -- `OfferEditor.svelte`, `QuestOffers.svelte`, `QueueCard.svelte`, `questOffers.svelte.js`, `ConditionEditor.svelte`, `ConditionInterpreter.svelte`, `conditionInterpreter.svelte.js`; static text checks only.
- existing `frontend_build_fresh.py`, `module_budget.py` frontend rule, `creation_island.py`, `effect_self_write.py` (F and G pass them) -- rebuilt output committed; no new island; no self-write in an `$effect`.
- `quest_request_panel.py` (G) -- `QuestRequests.svelte`, `questRequests.svelte.js`, `Queue.svelte`, `writePanel.svelte.js`, `Lore.svelte`.
- `corpus_gate.py` -- every check, 15 s each: the DB-backed checks of this lot build one small fixture each.

## Docs to update (chat-side, Nia's project)

`SERIE-conditions.md`: 0121 rédigé, son circuit, ses codes (A3 de la série inchangé).

## Amendments

- AMENDMENT-0121-01 (after BRIEF-0121-E): D-02 the drafts marked are those the approved payload names; D-03 `subject` written plainly and counted in `_SUBJECT_CENSUS`; C-10 `pending_drafts` also holds a proposed condition with definitions or vocabulary; C-11 without `knowers_note`.
