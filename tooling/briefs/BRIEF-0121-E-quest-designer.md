<!-- slug: quest-designer -->
# BRIEF 0121-E — "The quest designer -- one save for the route and the applier, the interpreter's reuse points, quest_designer.py and its prompts, the quest_offer_creation applier and the prose guard (C1, D1, F1, G1, H2, V1; no schema change)"

Lot: LOT-0121-journee-quest-designer.md (authoritative on conflict)
Depends on: BRIEF-0121-B (the request and its writer), BRIEF-0121-C (`gather_lore`)

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0121-D).

- `src/world_engine/cockpit/routes/quests.py` -> `class OfferStepBody`, `class TermBody`, `class OfferBody`, `def _term(`, `def _save_offer(` (`materialize` -> `PlanStep`s -> `write_quest_offer` -> `_mark_drafts` -> `db.commit()`), `def _mark_drafts(`.
- `src/world_engine/condition_interpreter.py:171` -> `def build_context(db, world_id, instruction, current, unsaved=())` whose fact list starts `fact_ids = list(ids["f"])`; `:616` `def _answer(db, world_id, parsed, ctx, unsaved, retried)`; `def prompt_values(ctx, role, instruction, errors)` returning the keys `role, forms, entities, tree_entities, facts, offers, skills, attributes, entity_types, event_types, sortes, current, instruction, errors`.
- `src/world_engine/cockpit/routes/conditions.py` -> `def _answer(draft, result, db, unsaved` building `{draft_id, outcome, view, mentions, notes, errors, definitions, vocabulary}`.
- `src/world_engine/writes/condition_drafts.py:62` -> `def write_condition_draft(db, *, attempt_id, world_id, role, instruction, outcome, payload, model_calls, retried=False)`.
- `src/world_engine/cockpit/routes/mutations.py:453` -> `    appliers = {` ending `"skill_progress": _skill_progress.apply_skill_progress,`.
- `src/world_engine/cockpit/mutations.py` -> 931 lines, 22 functions.
- `src/world_engine/proposal_producers.py:16` -> `PRODUCERS` with seven keys, no `local_ai_quest_designer`.
- `src/world_engine/prompt_registry.py:294` -> the `"condition_interpret": PromptSpec(` entry (`surface="authoring"`, `default_model=_author_model`).
- `scripts/seed_pilot.py` -> `CONDITION_INTERPRET_SYSTEM_PROMPT = with_condition_fragments(` holding the headers `FEUILLES.` and `CONDITION ACTUELLE.`, in that order; `CONDITION_INTERPRET_PROMPT_HEADS`.
- `src/world_engine/cockpit/routes/lore_write.py:52` -> `class CommitBody(BaseModel):` with `proposal` and `attempt_id` only.
- `CLAUDE.md` -> the INV-01 bullet containing `(Lore question, names panel, writing panel, condition interpreter)`.
- `.claude/rules/mutation-pipeline.md` -> INV-28 to INV-34, no INV-63.
- `tooling/verify/checks/json_ui_boundary.py` -> the comment above `"ProposedMutation.payload",` ending `First structured UI consumer must relationalize.`
- `tooling/verify/canon_write_policy.txt:56` -> the `write_quest_offer` comment ending `creator CRUD only.`
- `src/world_engine/writes/quest_requests.py`, `src/world_engine/quest_lore.py` exist (B, C).
- No `src/world_engine/quest_designer.py`, `src/world_engine/prose_guard.py`, `src/world_engine/cockpit/quest_offer_save.py`, `src/world_engine/cockpit/routes/quest_requests.py`, `tooling/verify/checks/quest_designer.py`.

## Facts carried

### R-06 — a proposal row [M]
Opened: `models/pipeline.py:98-150`; `tooling/verify/checks/json_ui_boundary.py:40-130`; `dashboard_deferrals.py:115-119`.
Finding: `proposed_mutation` has no CHECK on `mutation_type`, `source_type`, `status` or `proposed_by`; exactly one source (`pass_play_id`, `conversation_id`, or `tick_id`); `payload` JSON, NOT NULL; `target_id` free text; `ProposedMutation.payload` and `.original_payload` are listed exceptions of `json_ui_boundary.py`.
Finding (cont.): the exemption's justification reads « rendered readonly in the review queue; shape is the mutation type's contract, not a UI field. First structured UI consumer must relationalize » (`json_ui_boundary.py:44-47`); TICKET-0119's typed event card is already such a consumer, and TICKET-0115 registered that condition as reached, without a ticket: `dashboard_deferrals.py:115-119`, `Deferral("payload", "TICKET-0025", ..., _JSON_BOUNDARY, "First structured UI consumer must relationalize.", status="reached")` -- its anchor is that sentence of `json_ui_boundary.py`, found exactly once by DB1.
Consequence: `quest_offer_creation` needs no DDL; its payload carries the draft offer as JSON and the card edits it field by field -- a second structured consumer of a reached deferral, flagged to Nia as a drafting decision; the exemption's comment gains one line naming both cards, its anchor sentence untouched; `quest_request.change_history` (JSON, never rendered) needs its own listed exception.

### R-07 — the producers [M]
Opened: `src/world_engine/proposal_producers.py:16-30`; `CLAUDE.md:194-198` (INV-14).
Finding: seven live values (`local_ai_window`, `local_ai_overhearing`, `local_ai_tick`, `local_ai`, `observed_scene`, `engine`, `engine_roll`), kinds `model`/`engine`/`auto`; INV-14 is enforced by `proposal_producers.py`: every `proposed_by` written in `src/` is a key of `PRODUCERS`.
Consequence: the designer's value is added in the brief that writes it (E).

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

### R-19 — prompts [M]
Opened: `prompt_registry.py:50-62` (`PromptSpec`), `:290-300` (`condition_interpret`); `prompt_call.py:1-60` (`call_json`); `scripts/apply_ticket_0112_condition_prompt.py:1-60`; `.claude/rules/prompts.md`.
Finding: a new usage is a `PROMPT_REGISTRY` entry (INV-19) with its `call_sites`, a head in `seed_pilot` and a CREATE-HEAD script that loops the heads through `upsert_prompt_template` (S2: never touches an existing text).
Consequence: E adds `quest_subject` and `quest_design` (authoring, the author model) and `apply_ticket_0121_designer_prompts.py`.

### R-21 — the standing law [M]
Opened: `CLAUDE.md` (20,252 characters, budget 22,000, `claude_md_contract.py:77`), `:131-140` (INV-01), `:227-230` (INV-62); `.claude/rules/mutation-pipeline.md` (2,524 characters, budget 4,000); `tooling/verify/baselines/invariant_ids.retired`.
Finding: INV-01 lists the creator-regime readers « (Lore question, names panel, writing panel, condition interpreter) »; the highest live id is INV-62; ids run on across files.
Consequence: E amends INV-01 to name the quest designer and adds INV-63 to `mutation-pipeline.md`.

### R-22 — secret, for the prose guard [M]
Opened: `day_plan.py:204-220` (`_anchorable_facts`), `facet_reads.py:58-63`.
Finding: a fact the world holds only on `is_secret` rows is not anchorable; a creator-only fact is listed by `creator_only_fact_ids`.
Consequence: V1's « secret » is: a creator-only fact, or a fact no entity holds on a non-secret row (C-10).

### R-24 — how a DB-backed check builds its fixture [M]
Opened: `tooling/verify/checks/mutation_reviews.py:77-82` (`_fresh_db`), `:269-276` (`main`); `.claude/rules/verify-checks.md`.
Finding: `_fresh_db()` points `WORLD_ENGINE_DATABASE_URL` at a temp file and defaults `WORLD_ENGINE_ENV=test` before any `world_engine` import; `main` then imports `world_engine.models` (registering every table) and runs `SQLModel.metadata.create_all(engine)`; rows go through the real writers; failures collect in `FAILURES`; 15 s per check under `corpus_gate.py`.
Consequence: every new DB-backed check of this lot follows these two functions; a table missing from `create_all` means its model is not exported from `models/__init__.py`.


## Contracts

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

### C-05 — the designer's lore gathering
Produced by: BRIEF-0121-C   Consumed by: BRIEF-0121-E
`quest_lore.gather_lore(db, world_id, *, keywords: list[str], names: list[str], entity_ids: tuple[str, ...] = (), lore_entry_id: Optional[str] = None) -> LoreGathering`.
`LoreGathering(fact_ids: tuple[str, ...], entity_ids: tuple[str, ...], lines: tuple[str, ...], empty: bool)`:
- `entity_ids`: `entity_ids` given, then each name of `names` resolved by `lore_resolve.resolve_named(name, "other", world_id, db, scope=CREATOR)` when `matched` (an ambiguous or unmatched name is skipped -- the designer sees what is certain);
- `fact_ids`, in order, de-duplicated: the facts of `facts_mentioning(" ".join(keywords))` (each keyword on its own when the joined call finds nothing), then every fact with a `fact_participant` on each entity of `entity_ids`, then the facts of the `lore_entry_row` rows of `lore_entry_id` whose `row_table = 'fact'`;
- `lines`: one line per fact, `« <text> » -- su par <name> (<level><, secret>), ...` or `« <text> » -- su de personne`, creator-only facts suffixed `(réservé à la créatrice)`;
- `empty`: no fact found.
Reads only. Creator regime: every fact, creator-only included (INV-01, amended by E).

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
  "pending_drafts": [{"where": "eligibility" | "steps.<i>.<role>", "answer": <the dict `routes/conditions.py::_answer` returns for that draft, plus "instruction" and "role">}],
  "notes": [str],
  "consulted_fact_ids": [str],
  "secret_fact_ids": [str],
  "flags": [{"path": "title" | "summary" | "steps.<i>.objective", "fact_id": str, "words": str}],
  "flags_confirmed": false
}
```
A condition the designer proposed cleanly is in its tree, its `*_draft_id` the draft it came from (outcome `proposed`, so the save marks it `saved`); one that needs a name or was refused has tree `null` and appears in `pending_drafts`.
`prose_guard.flags(db, texts: dict[str, str], fact_ids: list[str]) -> list[dict]`: for each text and each fact, the first run of >= 4 consecutive tokens of `normalize_surface(text)` that is also a run of `normalize_surface(<fact text>)`; `secret_ids(db, world_id, fact_ids) -> list[str]` (R-22's definition).
Applier `cockpit/mutations.py::_mutation_apply_quest_offer_creation(mut, payload, db) -> Optional[str]`: refuses (returns the error) when the request is missing or its `mutation_id` is not `mut.id`; when `giver_entity_id` is empty; when `prose_guard.flags` recomputed on the payload's title, summary and objectives against `secret_fact_ids` is non-empty and `flags_confirmed` is not `true`; when `pending_drafts` is non-empty; on any `ValueError` of `save_offer_body` (the message). Otherwise writes the offer through `save_offer_body(db, world_id, OfferBody.model_validate(<OfferBody keys>), None)`, sets `mut.target_id = offer.id`, `move_request(request, "proposed", offer_id=offer.id)`. Writes nothing on refusal.

### C-11 — the designer
Produced by: BRIEF-0121-E   Consumed by: C-12
`quest_designer.design(db, request: QuestRequest, exchanges=None) -> DesignResult(outcome, mutation: Optional[ProposedMutation], notes: list[str])`, `outcome in ("proposed", "asking", "covered", "refused")`:
1. `quest_subject` call (`prompt_call.call_json`): values `{character_name, declaration, existing}` -> `{"subject": str, "keywords": [str], "names": [str]}`; `LlmParseError` when `subject` is empty.
2. `gather_lore(keywords, names, entity_ids=(existing_entity_id,) if set, lore_entry_id)`.
3. `empty` and no `existence_answer` -> `move_request(asking, subject=...)`, outcome `asking`, no further call.
4. `quest_design` call: values `{character_name, declaration, subject, lore, knowers_note, forms, facts, offers, skills, attributes, event_types, entities, entity_types, existence}` from `condition_interpreter.build_context(db, world_id, <declaration + subject>, None, (), extra_fact_ids=gathering.fact_ids)` and `prompt_values`' formatting. Answer:
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


## Context

The heart of the ticket: from a request, the designer frames the subject,
reads what the whole lore says of it (H2), and either sends the existence
question to the creator (N1) or writes a full quest offer as a proposal
(B1) -- its conditions through the interpreter's own reader (C1), its terms
(F1), the vocabulary it lacks (G1), suggested givers (D1). The creator
approves it in the offer editor (F); the applier writes it through the same
save as Création › Quêtes, and refuses a field that repeats a secret she did
not confirm (V1, INV-63).

## Scope IN

**Commit 1 -- pure move: one offer save (C-09).**

1. `src/world_engine/cockpit/quest_offer_save.py`: `OfferStepBody`, `TermBody`, `OfferBody` and `_mark_drafts` moved byte-identical from `routes/quests.py`; `_term` moved as `term_spec`; `save_offer_body(db, world_id, body, offer)` = `_save_offer`'s try block without `db.rollback()`, the `HTTPException` and the commit, followed by `_mark_drafts`. `routes/quests.py` imports them; `_save_offer` keeps its signature: `try: offer = save_offer_body(...)` / `except ValueError as exc: db.rollback(); raise HTTPException(status_code=422, detail=str(exc)) from exc` / `db.commit()`, `db.refresh(offer)`, `return quest_reads.offer_dict(offer, db)`. No behaviour change: the existing quest checks stay green.

**Commit 2 -- the interpreter's reuse points (C-13).**

2. `condition_interpreter.py`: `build_context(..., unsaved=(), extra_fact_ids=())` -- `fact_ids = list(extra_fact_ids) + list(ids["f"])`, everything else unchanged; `settle_answer(...)` public, `_answer` delegating to it (or the reverse; both names exist); docstrings name TICKET-0121.
3. `routes/conditions.py`: `answer_dict(draft, result, db, unsaved=())` public, `_answer` delegating; `POST /api/conditions/view` (`{tree: dict | null, unsaved_attributes: list}`) -> `quest_reads.condition_view(db, clean_condition(...), unsaved_views)`; 422 with the `ValueError`'s text.

**Commit 3 -- the designer, its proposal, its applier.**

4. `src/world_engine/prose_guard.py` (new): `flags(db, texts, fact_ids)` and `secret_ids(db, world_id, fact_ids)` as C-10; tokens through `lore_resolve.normalize_surface`; a fact's text through `prose_render.fact_texts`; `words` is the shared run, joined by spaces. Pure reads.
5. `src/world_engine/quest_designer.py` (new): `design` and `DesignResult` as C-11, with module functions `_subject(db, request, exchanges)` and `_design_call(db, values, exchanges)` (the two prompt call sites), each through `prompt_call.call_json(db, <usage>, values, exchanges, chat)` with `from .ollama_client import chat` at module level (the interpreter's precedent: a check stubs `quest_designer.chat`). Details:
   - `{existing}` for `quest_subject`: "" or « La créatrice dit que le lore le contient déjà : <entity name>. ».
   - `{existence}` for `quest_design`: "" when no answer; `exists`: « La créatrice a dit que ce sujet existe dans ce monde : <creator_text>. »; `absent`: « La créatrice a dit que ce sujet n'existe pas dans ce monde (<creator_text>) : la quête mène le personnage à apprendre qu'il n'existe pas, et pourquoi. »; `already`: « La créatrice dit que le lore le contient déjà : <entity name>. ».
   - `{lore}`: one line per fact of the gathering, `<its f code from ctx.lists["f"]> — <its gathering line>` (a fact beyond the cap: the line without a code); « (rien) » when empty.
   - the other values: `prompt_values(ctx, "eligibility", <declaration>, errors)`'s `forms, entities, facts, offers, skills, attributes, entity_types, event_types, sortes, errors`, plus `character_name, declaration, subject`.
   - the conditions: for `eligibility` and each step's `prerequisite`, `completion`, `failure` (role names as `CONDITION_ROLES`), an answer `None` is no condition; otherwise `settle_answer` then `write_condition_draft(attempt_id=request.id, world_id, role, instruction=<phrase, or the step's objective when the phrase is empty>, outcome=interp.outcome, payload=interp.payload(None), model_calls=[], retried=...)`; `proposed` -> its tree (`node_to_dict`) and `*_draft_id`; otherwise tree `null` and a `pending_drafts` entry whose `answer` is `answer_dict(draft, interp, db)` plus `instruction` and `role`. The model exchanges of the design call are recorded once, on the first draft written (`model_calls`), the others `[]`.
   - the retry (II1): when any condition's interpretation is `refused` with an error other than an unknown name or « nothing proposed » (`condition_interpreter._retryable`'s rule), one more `quest_design` call with `errors` = those errors prefixed by where they occurred; the second answer is final. Drafts of the first answer are written before the retry (the journal keeps both).
   - steps: `cost` clamped into 1..4, `domain` kept only when in `BASE_SKILL_DOMAINS`, an empty objective drops the step with a note; no step -> outcome `refused`, request unchanged, the note returned.
   - givers, terms, notes, flags and the proposal exactly as C-10 and C-11; `consulted_fact_ids` = the codes of `ctx.lists["f"]` resolved; `secret_fact_ids = secret_ids(...)`; `flags` from the title, summary and every objective.
   - an `outcome` outside the three, or `covered` naming no open offer of the list: `LlmParseError`.
6. Prompts. `scripts/seed_pilot.py`: `QUEST_SUBJECT_SYSTEM_PROMPT`, `QUEST_SUBJECT_USER_TEMPLATE`, `QUEST_DESIGN_SYSTEM_PROMPT`, `QUEST_DESIGN_USER_TEMPLATE` and `QUEST_DESIGNER_PROMPT_HEADS` (two heads, ids `pt-quest-subject`, `pt-quest-design`, `world_id=None`, `is_active=True`, their variables -- the placeholders of each user template). The texts are VERBATIM below, except `QUEST_DESIGN_SYSTEM_PROMPT`, which is built in the seed as `DESIGN_PREAMBLE + <the slice of CONDITION_INTERPRET_SYSTEM_PROMPT from "FEUILLES." up to, not including, "CONDITION ACTUELLE."> + DESIGN_POSTAMBLE` -- one source for the language: a later change of the interpreter's language text reaches a fresh seed of the designer. `scripts/apply_ticket_0121_designer_prompts.py`: the CREATE-HEAD pattern of `apply_ticket_0112_condition_prompt.py`, looping `QUEST_DESIGNER_PROMPT_HEADS`.
7. `prompt_registry.py`: `"quest_subject"` and `"quest_design"` `PromptSpec(surface="authoring", world_scoped=False, dry_run_capable=True, call_sites=("src/world_engine/quest_designer.py:_subject",)` / `(... :_design_call,)`, `default_model=_author_model)` with a comment (TICKET-0121, BRIEF-0121-E, the authoring model by default).
8. `proposal_producers.PRODUCERS`: `"local_ai_quest_designer": ("model", "Journée — concepteur de quêtes"),` after `"local_ai"`.
9. The applier. `cockpit/quest_offer_save.py::apply_offer_proposal(mut, payload, db) -> Optional[str]` holding C-10's applier logic (the request through `db.get(QuestRequest, payload.get("request_id"))`; `OfferBody.model_validate` of the payload's `OfferBody` keys; `save_offer_body`; `mut.target_id`; `move_request(request, "proposed", offer_id=...)`); `cockpit/mutations.py::_mutation_apply_quest_offer_creation(mut, payload, db)` delegating in one line, with a docstring naming C-10 and INV-63; `routes/mutations.py` `appliers` gains `"quest_offer_creation": _mutations._mutation_apply_quest_offer_creation,`. The French errors of the lot's case table, verbatim.
10. `cockpit/routes/quest_requests.py` (new, C-12) and its registration in `cockpit/app.py` (import beside `_routes_quests`, `include_router` beside it). `request_dict(request, db)` in `src/world_engine/quest_requests.py` (B's read module). `DESIGNER_UNAVAILABLE_MESSAGE` in `quest_designer.py`: « Le modèle local (Ollama) est indisponible : la demande n'a pas été conçue et rien n'a changé. Relance quand Ollama est démarré. ». A model failure of `/design` writes nothing (the request unchanged).
11. `routes/lore_write.py`: `CommitBody.quest_request_id: Optional[str] = None`; in `write_commit`, before `apply_proposal`, when set: the request exists, is of the active world and `writing_lore`, else 422 « Cette demande de quête n'attend pas d'écriture dans Lore. » (journaled as a refused commit, like the other refusals); after a successful apply, `move_request(request, "new", lore_entry_id=result.entry_id)` before the commit. `lore_isolation.py` R17 stays green: the route imports `writes.quest_requests`, nothing of the consultation.
12. Law and policy text:
    - `CLAUDE.md` INV-01: `(Lore question, names panel, writing panel, condition interpreter)` -> `(Lore question, names panel, writing panel, condition interpreter, quest designer)`.
    - `.claude/rules/mutation-pipeline.md`, after INV-34, verbatim (wrapped at 100 characters like its neighbours):
      ````text
      - **INV-63** A `quest_offer_creation` is applied only with a giver, no condition still
        waiting, and every player-visible field that repeats a secret fact the designer read
        confirmed by the creator (`flags_confirmed`): the applier recomputes the flags
        (`prose_guard.flags`) and writes nothing otherwise. -- enforced by `quest_designer.py`
      ````
    - `json_ui_boundary.py`: one comment line ABOVE the existing `ProposedMutation.payload` comment: `# Edited field by field by the review card for event_creation (TICKET-0119) and quest_offer_creation (TICKET-0121): the « payload » deferral, reached (dashboard_deferrals.py).` The sentence `First structured UI consumer must relationalize.` stays exactly once (it is DB1's anchor).
    - `canon_write_policy.txt`: the `write_quest_offer` comment ends `creator CRUD and, since TICKET-0121 (BRIEF-0121-E), the quest_offer_creation applier through cockpit/quest_offer_save.py.` instead of `creator CRUD only.`
13. New check `tooling/verify/checks/quest_designer.py` (fresh temp-file SQLite; `quest_designer.chat` replaced by a stub returning scripted JSON; rows through the real writers):
    - **QD1** a request whose subject the lore does not hold: `design` -> `asking`, one model call (subject), no draft, no proposal.
    - **QD2** a world with an NPC knowing a secret fact « acier noir » and the scripted offer (two steps: meet the NPC -- `has_met`; learn the fact -- `knowledge` by its code; one cost in money; givers ["<the NPC>", "Zorglub"]): one proposal, `proposed_by == "local_ai_quest_designer"`, `mutation_type == "quest_offer_creation"`, `pass_play_id` the request's; its payload has every key of C-10; one giver suggestion (Zorglub dropped, a note); the fact in `secret_fact_ids`; one `condition_draft` row per non-null condition of the scripted answer, each with `attempt_id == request.id`; the request `proposed` with its `mutation_id`.
    - **QD3** a scripted objective repeating four words of the secret fact: one flag on `steps.1.objective`; approving through `approve_mutation` with a giver set and `flags_confirmed` false leaves the proposal `approved` with the error, no offer written; with `flags_confirmed` true -> `applied`, one `quest_offer` with that giver, `mut.target_id` its id, the request's `offer_id` set, every `proposed` draft of the payload `saved`.
    - **QD4** a scripted condition naming an ambiguous name: its tree `null`, one `pending_drafts` entry whose `answer.outcome == "needs_choice"`; approving -> the error « Des conditions attendent encore un choix. ».
    - **QD5** a first answer with a refused condition (an unknown form), the second fixed: two design calls, the second carrying the error; the proposal from the second.
    - **QD6** `covered` naming an open offer's code -> request `covered`, its `offer_id` that offer; `unknown` -> `asking` with the note.
    - **QD7** the routes: `/design` on `writing_lore` -> 409; `/answer` `absent` on `asking` -> `writing_lore` and the statement « <subject> n'existe pas dans ce monde. <text> »; `/answer` `already` with an entity -> `new`; `/drop` on a pending proposal -> 409; the Lore commit with `quest_request_id` on a `writing_lore` request -> `new` with `lore_entry_id`, on a `new` request -> 422 and nothing written.
    - **QD8** static: INV-01 names the quest designer; INV-63 exists with its marker; `PRODUCERS` holds the value; `PROMPT_REGISTRY` holds both usages with `_author_model`; the applier is in `appliers`.
14. `tooling/standards/ARCHITECTURE_DECISIONS.md`: entries above the footer, one per commit:
    `## ONE OFFER SAVE FOR CRÉATION AND THE REVIEW QUEUE (TICKET-0121) -- quest_offer_save.py (BRIEF-0121-e, no schema change)`;
    `## THE INTERPRETER READS A DESIGNER'S CONDITIONS TOO (TICKET-0121) -- settle_answer, extra_fact_ids, answer_dict, /api/conditions/view (BRIEF-0121-e, no schema change)`;
    `## JOURNÉE'S QUEST DESIGNER (TICKET-0121) -- THE LORE SEARCHED WHOLE, THE EXISTENCE QUESTION, A QUEST OFFER PROPOSED AND GUARDED (BRIEF-0121-e, no schema change)` (H2 and INV-01, C1, D1, F1, G1, V1 and INV-63 -- a paraphrase passes, the creator's review stays the last barrier for prose -- the payload consumer under the reached « payload » deferral). Regenerate `DECISIONS_INDEX.md`, `FILE_MAP.md`.

The prompt texts, verbatim (the `` at a line's end is the seed's continuation, as in the other prompts):

`QUEST_SUBJECT_SYSTEM_PROMPT`
````text
Tu prépares une quête pour un jeu de rôle. On te donne la déclaration d'un \
joueur : ce que son personnage cherche à obtenir. Ton travail : dire de quoi \
il s'agit, pour qu'on cherche dans le lore du monde.

RÈGLES :
- "subject" : le sujet de la recherche en quelques mots, tel qu'on le \
nommerait dans le monde (« le secret de l'acier noir », « les \
dragons-zombies »).
- "keywords" : de 1 à 4 mots qui distinguent ce sujet, sans article (["acier", \
"noir"]).
- "names" : les noms propres de personnes, de lieux, de factions ou \
d'objets que la déclaration cite, tels qu'écrits ; [] s'il n'y en a pas.

Réponds UNIQUEMENT avec un objet JSON valide sur une seule ligne :
{"subject":"...","keywords":["..."],"names":["..."]}\

````
`QUEST_SUBJECT_USER_TEMPLATE`
````text
Personnage : {character_name}
Déclaration : {declaration}
{existing}\

````
`DESIGN_PREAMBLE` (the start of `QUEST_DESIGN_SYSTEM_PROMPT`)
````text
Tu conçois une offre de quête pour un jeu de rôle. Un personnage joueur \
cherche quelque chose ; la créatrice du monde veut qu'une quête lui permette, \
en jouant, de l'obtenir. On te donne sa déclaration, le sujet, et tout ce que \
le lore du monde en dit -- y compris des secrets que le joueur ignore et que \
seules quelques personnes connaissent.

TON TRAVAIL. Choisis d'abord "outcome" :
- "offer" : tu proposes une quête ;
- "covered" : une quête de la liste des quêtes mène déjà à ce sujet ; donne \
son code dans "covered_by" ;
- "unknown" : le lore ne dit rien du sujet lui-même ; écris dans "unknown" \
ce qui manque.

LA QUÊTE. Ses étapes mènent le personnage, pas à pas, vers ceux qui savent \
ou vers ce qu'il faut obtenir : se rendre quelque part, rencontrer quelqu'un, \
gagner sa confiance, apprendre un fait, détenir un objet, vivre un \
événement. Chaque étape a :
- "objective" : ce que le personnage fait, en une phrase, vu du joueur. \
Un objectif, le titre et le résumé nomment l'action (« Trouver l'érudit de \
Valmor », « Apprendre ce qu'il sait de la trempe ») ; le contenu d'un fait \
secret ou réservé à la créatrice reste dans les conditions, par son code ;
- "cost" : de 1 à 4, les moments de journée qu'elle demande ;
- "domain" : null, ou "physical", "agility", "perception", "composure" quand \
elle demande un jet ;
- "prerequisite" (ce qu'il faut pour la tenter), "completion" (quand son \
objectif est atteint), "failure" (quand elle a échoué) : chacune null ou une \
condition (voir CONDITIONS).
"eligibility" : à qui l'offre est proposée ; null le plus souvent (la \
créatrice ajoute la rencontre du donneur).
"title" et "summary" : ce que le joueur lira de l'offre.
"givers" : jusqu'à trois noms de personnages ou de factions du monde qui \
pourraient la donner, les plus plausibles d'abord.
"terms" : ce que la quête coûte et rapporte, chacun {"direction": "cost" | \
"reward", "currency": "money" | "item" | "relation" | "fact" | "skill", \
"target": un nom d'objet ou de personnage, un code de fait "f3" ou de \
compétence "s1", ou null pour la monnaie, "amount": un entier pour la \
monnaie, l'objet ou la relation, sinon null, "level": null}.
"notes" : ce que tu veux signaler à la créatrice -- notamment un fait du \
lore que personne ne sait encore.

CONDITIONS. Chaque condition est un objet {"phrase": la condition en une \
phrase française, "condition": l'arbre, "define": [], "define_events": [], \
"define_sortes": [], "unsupported": []} ; l'arbre et les trois listes \
"define" suivent le langage ci-dessous. Une feuille sur le personnage a \
"subject": "doer".


````
`DESIGN_POSTAMBLE` (its end)
````text
ERREURS. Si des erreurs sont données, ta réponse précédente a été refusée \
pour ces raisons : corrige-la.

Réponds UNIQUEMENT avec ce JSON :
{"outcome": "offer", "covered_by": null, "unknown": null, "title": "...", \
"summary": "...", "givers": ["..."], "eligibility": null, "steps": \
[{"objective": "...", "cost": 1, "domain": null, "prerequisite": null, \
"completion": {"phrase": "...", "condition": {"op": "all", "children": \
[...]}, "define": [], "define_events": [], "define_sortes": [], \
"unsupported": []}, "failure": null}], "terms": [], "notes": []}\

````
`QUEST_DESIGN_USER_TEMPLATE`
````text
Personnage : {character_name}
Déclaration : {declaration}
Sujet : {subject}
{existence}

Ce que le lore en dit (code — fait — qui le sait) :
{lore}

Formes :
{forms}

Types d'entité (clé — nom) :
{entity_types}

Entités nommées :
{entities}

Faits (code — texte) :
{facts}

Quêtes (code — titre) :
{offers}

Compétences (code — nom) :
{skills}

États (code — nom, sorte, pour qui) :
{attributes}

Types d'événements (code — nom, rôles) :
{event_types}

Sortes :
{sortes}

Erreurs de ta réponse précédente :
{errors}\

````
## Scope OUT

- The review card, the offer editor's extraction, the « Quête unique » box (F); the request panel and the Lore pre-fill (G).
- A giver created by the designer (D2, deferred); a search by meaning (S3).
- Any prompt of the play surface; the planner; the narrator.
- Auto-approval of any kind (D1 of the series, M2).
- Reading a `condition_draft`'s payload back in a route (`json_ui_boundary.py`: never rendered).
- Every later brief of this lot.

## Invariants to defend

- **INV-01** -- amended by name: the designer reads the creator regime; its output goes ONLY into a creator-reviewed proposal, never into a play context. No assembler, no player route calls `quest_designer` or `gather_lore`.
- **INV-02** -- the narrator and the play contexts are untouched; the proposal's text reaches the player only after the creator approved it (an offer).
- **INV-08 / INV-14** -- the offer is written by `_apply_mutation` after approval, through the creator CRUD's own save; nothing auto-applies.
- **INV-19** -- both calls resolve their model through the registry.
- **INV-20** -- the request relational; the payload under its listed exemption, the « payload » deferral named.
- **INV-22** -- the model names a fact only by a code of `ctx.lists["f"]`; a code it invents is an error.
- **INV-63** -- new, enforced by `quest_designer.py`.
- **INV-11** -- commit 1 (the pure move) lands before the applier touches `_apply_mutation`'s dispatch.

## Decision rights

STOP:
- an anchor does not hold;
- the pure move of commit 1 changes a body or a route's answer;
- `claude_md_contract.py` refuses the INV-01 or INV-63 text on its budget or its markers (the wording is Nia's to shorten, not the executor's);
- `single_canon_write.py` refuses the applier's path to `write_quest_offer`.
ADAPT:
- `CONDITION_INTERPRET_SYSTEM_PROMPT` holds `FEUILLES.` or `CONDITION ACTUELLE.` with different spacing: slice on the header word, report.
- a check stubs the interpreter's model by another attribute name: follow it, report.
- `request_dict`'s `day_number` needs the batch: read it through `PassPlay.batch_id`, report.
REPORT-ONLY:
- how long a design takes on the creator's machine (the prompt is long).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `quest_designer.py` PASS (QD1-QD8); `quests.py`, `quest_rewards.py`, `condition_interpreter.py`, `conditions.py`, `proposal_producers.py`, `prompt_registry.py`, `single_canon_write.py`, `claude_md_contract.py`, `json_ui_boundary.py`, `dashboard_registry.py`, `lore_isolation.py`, `lore_write.py`, `module_budget.py` PASS.
- [ ] Named mutations, red then reverted: drop the flags recomputation in the applier (QD3); accept a payload with `pending_drafts` (QD4); write the proposal with `proposed_by="local_ai"` (QD2, and `proposal_producers.py`); remove the quest designer from INV-01 (QD8).
- [ ] `apply_ticket_0121_designer_prompts.py` on the test DB: two heads `created`, then `existing`.
- [ ] `/review-step` then `/close-step` on each of the three commits.

## Docs to update

- `CLAUDE.md` (INV-01), `.claude/rules/mutation-pipeline.md` (INV-63), `ARCHITECTURE_DECISIONS.md` (three entries), regenerated `DECISIONS_INDEX.md`, `FILE_MAP.md`. No schema change.
