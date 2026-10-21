# LOT — TICKET-0116 "Rank trials: a rank that asks a trial is earned by a quest"

`main` at `246e89b` (PR #150, TICKET-0121 merged; PR #149, TICKET-0123 merged), schema v2.28.

## Objective and cut

A world may say that leaving a rank asks a trial -- the same cascade as the
points: the world's ladder per rank, overridden by a skill system, then by a
skill definition (B1). Nothing changes in a world that says nothing: no
trial is the default, everywhere. When a skill reaches the points of a rank
that asks a trial, the points stop at the threshold and the rank waits (A1,
C1): rolls and point rewards give it nothing more. The trial is an ordinary
quest offer whose reward carries a sixth currency, `rank` -- « the next rank
in this skill » (D2, E1) -- offered and accepted only by a character ready
for exactly that rank, and applied at « déclarer accomplie ». A player
character becoming ready opens a quest request of a new trigger, `trial`
(F1); « Concevoir » runs the designer of TICKET-0121 on it with its own
prompt, and Nia reviews, edits and confirms the offer in the review card.
The code imposes no giver and no master (G1); a trial fails like any quest
and may be retried, its offer repeatable by default (H1); only player
characters earn points, so only they face trials (I1).

The lot stops before: a trial over a whole system or any skill (E2,
deferred); a failed trial costing points or a rank (H2, deferred); points
carried past a waiting threshold (C2, rejected); a rank as a cost, a debt or
a service (D2-a); a giver required by code (G2, rejected); NPC trials (I2,
rejected); the day's account (`routes/day._account_gains`) telling apart a
point that a waiting skill did not take (drafting decision 11); the
calendar (TICKET-0120, next).

## Briefs in this lot

- **A** `trial-schema` -- v2.29: the trial columns of the ladder, the systems and the definitions; the `rank` currency in both term tables' CHECKs; `quest_request` rebuilt for the `trial` trigger; the migration; the checks pinned to those shapes (no logic).
- **B** `trial-ladder` -- the trial cascade and readiness (`skill_ranks`, `skill_access`); the points stop at a waiting threshold (C1); rolls and point rewards skip a waiting skill; the ladder, system and definition CRUD carry the flags; `GET /api/skills` says a skill waits (no schema change).
- **C** `rank-reward` -- the `rank` currency: its writer rules, its value, its wording, its application at settlement, the acceptance gate, the service refusal, the editor's choices and term row; INV-64 (no schema change).
- **D** `trial-request` -- a player character becoming ready opens a `trial` request (F1-a); the request reads and the panel's dict take a request with no day; the « Demandes de quête » metric counts trials (no schema change).
- **E** `trial-designer` -- `_masters` moved to `skill_access.skill_masters` (pure move); « Concevoir » on a trial: covered by an open offer, or one `quest_trial` call and a proposal carrying the rank reward; the `quest_trial` prompt; the applier keeps the rank reward (no schema change).
- **F** `trial-surfaces` -- Création › Compétences edits the flags; the fiche shows a waiting skill; « Demandes de quête » and the review card name a trial (no schema change).

## Dependency graph

- A depends on nothing in this lot.
- B depends on A (the trial columns it reads and writes).
- C depends on A (the CHECKs that let a `rank` row exist) and B (`held_trial_target`, `skill_trial_target`).
- D depends on A (the request's columns), B (the waiting path of `write_skill_progress`) and C (an offer holding a `rank` reward, read by `covering_trial_offer`; its fixture is written through C's writer).
- E depends on C (the `rank` term, the designer's `_term`) and D (the request, `covering_trial_offer`, `trial_subject`).
- F depends on B (the CRUD shapes, `trial_ready`), D (the trigger) and E (the proposal's `source_type` and `trial` key).
- **Execution order A, B, C, D, E, F**, strict: each brief consumes the one before.

## RECON

Every finding was opened on `main` at `246e89b`, in the file that declares
what is claimed. `[M]` measured.

### R-01 — the ladder and its cascade [M]
Opened: `src/world_engine/skill_ranks.py:1-111` (docstring, `RANKS`, `MAX_RANK = 5`, `RankStep` at `:46-50`, `default_ladder` `:60-65`, `world_ladder` `:68-79`, `points_to_next` `:82-95`, `skill_owners` `:98-105`, `skill_points_to_next` `:108-111`); `src/world_engine/models/config.py:240-256` (`SkillRank`); `src/world_engine/models/canon.py:580-612` (`RANK_POINTS_CHECK`, `SkillSystem`), `:617-660` (`SkillDefinition`).
Finding: `RankStep(rank, label, points_to_next)` is a frozen dataclass; `world_ladder` reads the world's `skill_rank` rows over `default_ladder()` and never writes; `points_to_next(rank, ladder, *, system, definition)` takes the definition's `points_to_rank_<rank+1>`, else the system's, else the ladder's, None at `MAX_RANK`; `RANK_POINTS_COLUMNS[rank]` is `points_to_rank_<rank+1>` (index = rank left). `skill_rank` declares `id, world_id, rank, label, points_to_next, updated_at`, CHECKs `ck_skill_rank_rank`, `ck_skill_rank_points`, unique `idx_skill_rank_world_rank`. `SkillSystem` and `SkillDefinition` declare `points_to_rank_1..5: Optional[int] = None` and one `ck_*_rank_points` CHECK each; `SkillDefinition.requires_master` follows them. `models/config.py:23` imports `text` from sqlalchemy. `skill_ranks.py` imports only `models`.
Consequence: the trial flag mirrors the points exactly -- `skill_rank.trial_to_next` (index = rank left), `trial_to_rank_<n>` on the system and the definition, the most specific non-null value winning (B1). No CHECK is added on `skill_rank` (A1 of `skill_progression.py` pins its CHECK set, R-17); the writer refuses a trial at rank 5.

### R-02 — the one writer of points, and who calls it [M]
Opened: `src/world_engine/writes/characters.py:1-39` (docstring, imports), `:65-102` (`write_skill_rank`), `:145-210` (`SkillProgress`, `write_skill_progress`); `tooling/verify/canon_write_policy.txt:30-34`, `:68`.
Finding: `write_skill_progress(db, *, skill_id, world_id, points, changed_by) -> SkillProgress` adds `points` (non-zero) to `xp`; when a gain reaches `skill_points_to_next` the rank rises by one and `xp` restarts at 0, at most one rank per call; a loss below 0 lowers the rank and refills `xp` from the lower threshold; `change_history` gets `{rank, xp, changed_at, by}` only when the rank moves; 58 lines today. `SkillProgress(rank_before, rank, xp, points_to_next)`. `write_skill_rank(db, *, skill_id, rank, changed_by="creator")` appends the previous rank and points to `change_history`, sets the rank, restarts `xp` at 0; its docstring names `update_skill_rank` as its only caller. Both are allow-listed write sites of `skill`; the policy comment at `:68` lists the writers `settle_quest` uses (`write_skill_row`, `write_skill_progress`, ...), not `write_skill_rank`.
Enumeration (pasted in Gate (c)): three callers of `write_skill_progress` -- `skill_progress.apply_skill_progress`, `skill_progress.grant_step_roll`, `quest_settlement._skill_reward`.
Consequence: C1 lives in `write_skill_progress` itself, so every caller stops at a waiting threshold by construction; the trial's rank is moved by `write_skill_rank` (its effect is exactly a trial's: history, the rank, `xp` 0), its docstring and the policy comment updated.

### R-03 — the two roll paths [M]
Opened: `src/world_engine/cockpit/skill_progress.py:1-129`.
Finding: `record_roll(*, world_id, conversation_id, skill_id, band)` returns None and writes no mutation for no row, a Maître, an unknown world; otherwise writes one `skill_progress` mutation (`proposed_by='engine_roll'`) and applies it at once. `grant_step_roll(db, *, step, owner_id, world_id, mutation_id)` gives the owner's base row one point through `write_skill_progress`, nothing for no domain, no row, a Maître.
Consequence: both skip a waiting skill the way they skip a Maître (« les jets ne rapportent plus rien », C1) -- no mutation is written for a roll that would earn nothing.

### R-04 — the ladder and threshold CRUD [M]
Opened: `src/world_engine/cockpit/crud/skills.py:55` (imports from `skill_ranks`), `:92-110` (`_skill_dict`), `:113-151` (`_rank_step_dict`, `list_skill_ranks`, `SkillRankStepBody`, `SkillRanksBody`, `update_skill_ranks`), `:172-184` (`_masters`), `:205`, `:214`, `:241` (its three callers), `:261-306` (`list_skills`, `update_skill_rank`), `:309-358` (`_skill_system_dict`, `RankPointsBody`, `_rank_points`, `_set_rank_points`, `SkillSystemWriteBody`), `:483-533` (`_skill_definition_dict`, `SkillDefinitionWriteBody(RankPointsBody)`); `src/world_engine/writes/config.py:536-569` (`upsert_skill_rank`).
Finding: `update_skill_ranks` upserts all six steps in one transaction through `upsert_skill_rank(db, *, world_id, rank, label, points_to_next)`, which refuses an empty label, points at rank 5, missing or < 1 points below it (`ValueError`), fetch-or-create, never a DELETE. `RankPointsBody` declares the five `points_to_rank_<n>`; `_rank_points(row)` and `_set_rank_points(row, body)` iterate `RANK_POINTS_COLUMNS`, so a system's and a definition's dict serve them and a PUT replaces all five. `_skill_dict(s, ladder, definition, system)` serves `rank`, `rank_label`, `xp`, `points_to_next`. `cockpit/crud/skills.py` is 667 lines, 24 functions.
Consequence: the trial flags ride the same bodies and helpers (`RANK_POINTS_COLUMNS + RANK_TRIAL_COLUMNS`), a PUT replacing them like the points; `SkillRankStepBody` gains `trial_to_next`; `_skill_dict` gains `trial_ready`.

### R-05 — how a migration moves the schema [M]
Opened: `scripts/migrate_v2_15_skill_ranks.py:1-215` (raw DBAPI transaction, `PRAGMA foreign_keys=OFF` and `legacy_alter_table=ON` before `BEGIN`, `_rebuild` = drop the table's indexes, rename to `<table>_old`, create from the model, copy named columns, drop the old; post-checks; `_converge_schema_meta`); `scripts/migrate_v2_16_npc_skills.py:1-35`, `:103-106` (`ALTER TABLE skill_definition ADD COLUMN requires_master BOOLEAN NOT NULL DEFAULT 0`); `scripts/migrate_v2_28_quest_requests.py:1-25`, `:55`, `:115-118`; `src/world_engine/schema_version.py:15` (`EXPECTED_STATIC_SCHEMA_VERSION = "v2.28"`); `world-engine-schema.md:3`; `world-engine-schema-changelog.md:14-21`.
Finding: SQLite cannot add a table CHECK nor change a column's nullability in place: such a table is rebuilt from its model; a nullable or defaulted column is added with `ADD COLUMN`. A migration refuses an older database, is idempotent, post-checks before moving `schema_meta`, and lists a dangling reference outside its own tables without stopping (AMENDMENT-0107-01). v2.28's post-check requires its three CHECK names present (a subset), not an exact set. No model declares a foreign key to `quest_request`, `quest_offer_term` or `quest_term` (`grep` of `models/`, empty).
Consequence: v2.29 adds eleven columns with `ADD COLUMN` and rebuilds `quest_offer_term`, `quest_term` and `quest_request` from their models, in one raw transaction.

### R-06 — the term vocabulary [M]
Opened: `src/world_engine/models/quests.py:111-184` (`QUEST_TERM_DIRECTIONS`, `QUEST_TERM_CURRENCIES = ("money", "item", "relation", "fact", "skill")`, `QUEST_TERM_SHAPE_CHECK`, `QUEST_TERM_DIRECTION_CHECK`, `QUEST_TERM_CURRENCY_CHECK`, `QuestOfferTerm`, `QuestTerm`), `:290-308` (`DebtTerm`, CHECK `ck_debt_term_currency` `currency IN ('money','item','fact','skill')`, its own literal); `src/world_engine/writes/quest_terms.py:42-138` (`PERSONAL_CURRENCIES`, `COUNTED_CURRENCIES`, `TERM_COLUMNS`, `TermSpec`, `_clean_target`, `_clean_amount`, `clean_term`, `clean_terms`), `:158-162` (`copy_terms_to_quest`); `src/world_engine/cockpit/quest_offer_save.py:47-55` (`TermBody`, free `currency: str`), `:79` (`term_spec`).
Finding: both term tables carry the same three CHECK texts, built from the three module literals; the currency CHECK is a literal, not derived from the tuple; `clean_term` refuses a currency outside the tuple before any write; `copy_terms_to_quest` copies every `TERM_COLUMNS` column, so a `rank` term reaches the quest's own copy (B1 of 0109) with no change. A debt's terms have their own CHECK: a `rank` can never be owed.
Consequence: A widens the two CHECK literals (the schema allows a `rank` row); C widens the tuple and gives `clean_term` the rank's rules (the writer lets one through) -- the tuple and its mirror `questTerms.js` move together in C (R-15).

### R-07 — settling a quest, and a service [M]
Opened: `src/world_engine/writes/quest_settlement.py:1-63` (docstring, imports, `SKILL_REWARD_SHARE`, `LEARNED_RANK`, `CHANGED_BY = "quest_settlement"`), `:71-84` (`skill_row`, `skill_reward_points`), `:164-203` (`_skill_reward`, `apply_term`), `:206-233` (`in_order`, `finish_settlement`, `settle_quest`); `src/world_engine/quest_settlement_view.py:36-50` (`_skill_note`, `_terms`); `src/world_engine/writes/debt_sources.py:46-72` (`request_service`).
Finding: `apply_term` branches money, item, relation, fact, then `elif cost:` (teaching) and `else:` (`_skill_reward`) -- any other currency falls into the skill branches. Rewards are never checked before settlement (C-src1). `skill_reward_points` is None at Maître; `_skill_note` reads its None as « déjà Maître ». `request_service` validates its terms with `clean_terms` and applies them with `apply_term`, as a settlement does.
Enumeration (pasted in Gate (c)): three callers of `apply_term` -- `request_service`, `settle_quest_on_credit`, `settle_quest`.
Consequence: `apply_term` gains an explicit `rank` branch before the skill branches; `request_service` refuses a `rank` term before any write (D2-a); `skill_reward_points` is None for a waiting skill (silence, Nia's answer); both settlement paths give the rank.

### R-08 — a term's value and its words [M]
Opened: `src/world_engine/quest_value.py:54-65` (`term_value`), `src/world_engine/quest_wording.py:31-58` (`term_line`, `term_dict`).
Finding: `term_value` returns money, relation, fact, skill, and falls through to the item formula for any other currency (an item id of None gives 0). `term_line` ends on the skill wording for any currency it does not name. `QuestOfferTerm` and `QuestTerm` carry `world_id` (R-06).
Consequence: `rank` gets an explicit 0 and its own line, never a fall-through.

### R-09 — offering, accepting, and the editor's choices [M]
Opened: `src/world_engine/writes/quests.py:1-56` (docstring, imports), `:174-232` (`offer_bindings`, `acceptance_refusal`, `accept_quest`); `src/world_engine/quest_reads.py:132-177` (`editor_choices`), `:190-195` (`available_offers`), `:240-262` (term lines on the player's side).
Finding: `acceptance_refusal(db, offer, character)` judges a closed offer, L1 (taken / still open), then the eligibility tree; `accept_quest` raises its reason before any write; `available_offers` lists the open offers whose `acceptance_refusal` is None -- the one judge for both. `editor_choices` serves `skills` as `{key, label}` and no ladder.
Enumeration (pasted in Gate (c)): two callers of `acceptance_refusal` -- `accept_quest`, `available_offers`.
Consequence: the trial gate is one more refusal in `acceptance_refusal`, after L1 and before the eligibility: listing and accepting cannot disagree, and no eligibility leaf the creator may delete carries it (D3, rejected).

### R-10 — the quest request [M]
Opened: `src/world_engine/models/pipeline.py:591-630` (`QuestRequest`); `src/world_engine/writes/quest_requests.py:1-92`; `src/world_engine/quest_requests.py:1-50`; `src/world_engine/dashboard_metrics.py:259-296` (`_TRIGGERS_FR`, `_quest_requests`); `src/world_engine/writes/worlds.py:84` (`"quest_request",` in the cascade); `src/world_engine/cockpit/routes/quest_requests.py:55-121`.
Finding: `pass_play_id` and `agenda_step_id` are NOT NULL; `trigger IN ('route','blocked','dropped')`; one request per step (`idx_quest_request_step` unique). `open_request` refuses a trigger outside `QUEST_REQUEST_TRIGGERS`, an empty declaration, a missing step, and returns the step's existing request. `move_request` appends the former state. `request_dict` reads `db.get(PassPlay, request.pass_play_id)` unconditionally. `_TRIGGERS_FR` is a literal of three rows; `_quest_requests` emits one `Origine` row per entry, `of` = the requests in scope. `_may_design` allows `new`, `covered`, and a rejected `proposed`. `writes/quest_requests.py` is not exported from `writes/__init__.py`.
Consequence: the table is rebuilt (A); a `trial` request has no day and no step, a skill and a target rank, and its own writer `open_trial_request` (D); `request_dict` guards the missing day; the metric gains one row; the routes need no change.

### R-11 — the designer and its applier [M]
Opened: `src/world_engine/quest_designer.py:1-361` (`SUBJECT_USAGE`, `DESIGN_USAGE`, `OUTCOMES` `:43`, `_design_call` `:83-88`, `_design_values` `:106-113`, `_term` `:206-236`, `_payload` `:249-285`, `design` `:295-304`, `_design` `:307-361`); `src/world_engine/cockpit/quest_offer_save.py:139-167` (`apply_offer_proposal`); `src/world_engine/quest_lore.py` (`gather_lore(db, world_id, *, keywords, names, entity_ids=(), lore_entry_id=None)`, C-05 of 0121).
Finding: `_design` runs `quest_subject`, `gather_lore`, the existence check (`asking`), one `quest_design` call, its `covered`/`unknown` answers, then the offer path (steps, `_settle`, one retry with the errors, notes, `_payload`, the proposal `source_type="pass_play", pass_play_id=request.pass_play_id`, `move_request(proposed)`); 55 lines. `_term` drops an unknown currency with a note. `_payload` sets `repeatable: False` and exactly C-10's keys. `apply_offer_proposal` refuses a request missing or not this proposal's, no giver, unconfirmed flags, pending conditions, a refused save; it then writes through `save_offer_body` and moves the request.
Consequence: `_design` dispatches a `trial` request to its own path; the offer path is extracted unchanged into `_offer` for both; the applier gains one refusal for a trial whose terms lost the rank reward.

### R-12 — prompts [M]
Opened: `src/world_engine/prompt_registry.py:300-317` (`quest_subject`, `quest_design`: `surface="authoring"`, `default_model=_author_model`, call sites `quest_designer.py:_subject` / `:_design_call`); `scripts/seed_pilot.py:2320-2486` (`QUEST_SUBJECT_*`, `QUEST_DESIGN_PREAMBLE`, `QUEST_DESIGN_POSTAMBLE`, `_quest_design_system_prompt` slicing `CONDITION_INTERPRET_SYSTEM_PROMPT` from « FEUILLES. » to « CONDITION ACTUELLE. », `QUEST_DESIGN_USER_TEMPLATE`, `QUEST_DESIGNER_PROMPT_HEADS`), `:3515` (the seed loop); `scripts/apply_ticket_0121_designer_prompts.py:1-55`; `tooling/verify/checks/prompt_registry.py` docstring (rule 1: usages seeded in `seed_pilot.py` == registry keys; rule 2: each call site's `def` exists).
Finding: a usage is a registry entry, a seed head and a CREATE-HEAD script relying on `upsert_prompt_template`'s idempotence (S2).
Consequence: E adds `quest_trial` (its own system prompt, the design's user template and variables), `QUEST_TRIAL_PROMPT_HEADS`, its seed loop line and `apply_ticket_0116_trial_prompt.py`.

### R-13 — a proposal's source and the queue [M]
Opened: `src/world_engine/models/pipeline.py:98-150` (`ProposedMutation`: no CHECK, four indexes, `source_type` free text, three nullable sources); `src/world_engine/cockpit/routes/mutations.py:250-286`, `:366-402` (`_find_applied_duplicate`: no `conversation_id` -> the tick branch, which returns None without a `tick_id`), `:106-123` (`_mutation_dict`); `frontend/src/creation/QueueCard.svelte:159-176`, `:296-312`, `:391-410`; `frontend/src/creation/queue.svelte.js` (filters by status).
Finding: every `source_type` value written today, by grep (pasted in Gate (c)): `pass_play`, `world_tick`, `conversation`. The card shows a « TICK » badge for `world_tick` and « JOURNÉE » for `pass_play`; a proposal with no source shows neither and no `sourceRef`.
Consequence: a trial's proposal is `source_type="quest_request"` with no day (drafting decision 5); nothing branches on it but the card's badge (F).

### R-14 — Création › Compétences and the fiche [M]
Opened: `frontend/src/creation/competences.svelte.js:1-326` (`RANK_POINT_KEYS` `:59`, `rankPoints` `:61-65`, `inheritedPoints` `:69-77`, the records `:90-138`, `pointsValue`/`pointsBody` `:238-249`, `saveSkill` `:257-269`, `saveSystem` `:271-278`, `saveRanks` `:280-293`); `frontend/src/creation/CompetencesSheet.svelte:89-128` (the `thresholds` snippet, the `ranks` record), `:187`, `:209` (its two renders); `frontend/src/creation/PjSkillFiche.svelte:129-133` (`pointsLine`), `:213`.
Finding: thresholds are edited in one snippet rendered on the skill and the system fiche; the ladder record edits each rank's label and points; the fiche reads `GET /api/skills`.
Consequence: the trial selects live in the same snippet (its two renders stay two, R-17), the ladder record gains one checkbox per rank below Maître, the fiche's points line names a waiting skill.

### R-15 — the term editor [M]
Opened: `frontend/src/creation/questTerms.js:1-48` (`CURRENCY_FORMS`, one line per currency, `termTargetOptions`, `termBody`); `frontend/src/creation/QuestTermRow.svelte:1-67`; `frontend/src/creation/OfferEditor.svelte:109-118` (one section per direction, rows filtered by `term.direction`); `frontend/src/creation/questOffers.svelte.js:67-73` (`termDraft`), `:185-199` (`REVIEW_KEYS`, `proposalBody`).
Finding: a term row picks its currency among every `CURRENCY_FORMS` entry, its target from the form's `list`, its amount when `counted`, its counterparty always; `termBody` sends `skill_key` only for `skill`, `amount` only when `counted`. `proposalBody` copies `REVIEW_KEYS` from the payload.
Consequence: the `rank` form is one more line of the exact RD1 shape (R-17), reward-only through a separate constant; the row adds a rank picker and hides the counterparty for it.

### R-16 — the requests panel [M]
Opened: `frontend/src/creation/QuestRequests.svelte:16-18` (`TRIGGER_LABEL` of three triggers, unknown shown raw), `:76-78` (« Jour {r.day_number ?? '—'} »).
Consequence: one label more; a trial row reads « Jour — ».

### R-17 — the existing checks that read what this lot changes [M]
Opened: the grep of `tooling/verify/checks` for every file this lot edits (raw output in Gate (c)), then each hit's implementation:
- `skill_progression.py:201-204` (A1: `skill_rank` columns exactly `{id, world_id, rank, label, points_to_next, updated_at}`; its CHECK set), `:444-446` (A4: the word `tier` absent from `PjSkillFiche.svelte` and `crud/skills.py`), `:742-750` (C3: `sheet.count("{@render thresholds()}") == 2`, `state.count("...pointsBody(record)") == 2`), `:789-797` (D2: `s.xp`, `s.points_to_next`, « rang maximal »);
- `skill_system_shape.py:29-35` (`EXPECTED_SKILL_SYSTEM_COLUMNS`, exact);
- `quest_requests.py:46-50` (`COLUMNS` in order, `CHECKS`, `INDEXES`, exact), `:100-102` (one unique index, `idx_quest_request_step`), `:52-62` (`EXPECTED_ROWS`), `:280-316` (QR6 compares the metric rows to it exactly);
- `quest_rewards.py:198-201` (RA1: the two tables' CHECK texts equal), `:959-976` (RD1: `CURRENCY_FORMS` lines matched by `^  (\w+): \{ label: '[^']*', list: [^,]+, (counted: \w+, personal: \w+) \},$`, keys == `QUEST_TERM_CURRENCIES` in order; `counted: true` == `COUNTED_CURRENCIES`, `personal: true` == `PERSONAL_CURRENCIES`);
- `knowledge_identity.py:31-35`, `:109-125` (K3: the `subject` references of `src/world_engine`, per file, equal `_SUBJECT_CENSUS` exactly; `writes/quest_requests.py` 1, `quest_requests.py` 2, `quest_designer.py` 10);
- `event_conditions.py:342-345` (EE5: only `quest_reads.py` and `writes/quests.py` contain `role="failure"`);
- `npc_skills.py:576-589` (C2: patterns of the fiche, the sheet, the state);
- `quests.py:760-764` (QB4: no dict literal with `agenda_id`/`step_id` in `routes/quests.py`, `quest_reads.py`);
- `quest_designer.py:68-80` (its stub routes a call by its system prompt: « Tu prépares une quête » -> subject, anything else -> design), `:268-278` (QD2: a route request's payload keys exactly C-10's), `:494-497` (QD8: `quest_subject`, `quest_design` on `_author_model`);
- `npc_skills.py:100-125`, `:173-174`, `:240-270`, `:598-605` (A2 recreates `skill_definition` in its v2.15 DDL and runs v2.16, an `ADD COLUMN`; A2b compares the migrated shapes with the models'; A3 and later write into that same file);
- `world_cascade.py:207-209`, `:222-225`, `:111` (raw fixture rows of `quest_request` -- `route`, a day and a step --, the two term tables -- `item`, `money` --, `skill_rank` without `trial_to_next`).
Consequence: A updates A1, `skill_system_shape.py`, QR1 and `npc_skills.py` (its migrated file lacks the five `trial_to_rank_<n>`: they are left out of A2b's comparison and added before A3 -- found by a prototype of A, which also showed that `DEBT_TERM_SHAPE_CHECK` ends with the same literal line as `QUEST_TERM_SHAPE_CHECK` and must not change); D updates QR6's expected rows; D and E update K3's census for the files they edit (an ADAPT); every other pinned pattern is kept by construction (two snippet renders, two `...pointsBody(record)`, the RD1 line shape, no `role="failure"`, no `tier`, C-10's keys unchanged for a non-trial request, `trial_to_next` server default 0 for the cascade's raw row).

### R-18 — the standing law [M]
Opened: `CLAUDE.md` (20,448 characters, budget 22,000), INV-15; `.claude/rules/skills.md` (2,221 characters, budget 4,000; `paths:` `src/world_engine/skill*.py`, `src/world_engine/cockpit/crud/skills.py`; INV-41 to INV-46); `tooling/verify/baselines/invariant_ids.retired`; `tooling/verify/checks/claude_md_contract.py:77-78` (budgets), the live ids (highest INV-63).
Finding: INV-15 says `write_skill_progress` moves the rank of the one auto-applied mutation -- still true where no trial is asked, and nothing in this lot auto-applies anything new.
Consequence: INV-15 is untouched; C adds INV-64 to `skills.md` and its `paths:` gain the three writers it names.

### R-19 — the time a check may take [M]
Opened: `tooling/verify/checks/corpus_gate.py:53-62` (`TIMEOUT_SECONDS = 15`, `SLOW_CHECK_TIMEOUTS`); local runs at `246e89b`: `skill_progression.py` 9.4 s, `quest_rewards.py` 9.8 s, `debts.py` 9.1 s, `quests.py` 8.7 s, `quest_designer.py` 3.5 s, `quest_requests.py` 2.1 s.
Consequence: no new rule goes into the four slow checks; this lot's rules live in two new checks, `rank_trial_schema.py` (A, with its migration run) and `rank_trials.py` (B to F).

### R-20 — module sizes and function lengths [M]
Opened: `ast` count of module functions + methods and physical lines; `tooling/verify/checks/module_budget.py:57-59` (40 functions, 1000 lines); `function_length.py` (80 lines).
Finding (functions/lines, longest): `models/canon.py` 2/946; `writes/characters.py` 5/250 (`write_skill_progress` 58); `skill_ranks.py` 6/111; `skill_access.py` 7/116; `cockpit/crud/skills.py` 24/667; `writes/quest_terms.py` 10/187; `writes/quest_settlement.py` 14/233; `writes/quests.py` 10/264; `writes/debt_sources.py` 4/158; `quest_value.py` 4/86; `quest_wording.py` 4/58; `quest_reads.py` 14/276; `quest_settlement_view.py` 6/106; `writes/quest_requests.py` 3/92; `quest_requests.py` 3/50; `dashboard_metrics.py` 20/339; `quest_designer.py` 20/361 (`_design` 55); `cockpit/quest_offer_save.py` 5/167; `cockpit/skill_progress.py` 4/129; `prompt_registry.py` 3/409.
Consequence: no module nears a cap; `models/canon.py` gains ten one-line fields and one comment (<= 960 lines); every new or changed function stays <= 80 lines.

### R-21 — which skill row, and who masters it [M]
Opened: `src/world_engine/skill_access.py:1-116` (`_base_row` `:45-52`: `domain` and `skill_definition_id IS NULL`; `_definition_row` `:55-58`; `held_rank` `:82-92`; `skill_label` `:95-101`; imports `models`, `resolution`, `skill_ranks`); `cockpit/crud/skills.py:172-184` (`_masters`: the world's characters at `MAX_RANK` in one skill, `{id, name}` by name).
Consequence: `held_trial_target` reads its row through `_base_row`/`_definition_row` (INV-41's lookup, never a copy); `_masters` moves, unchanged but its name, to `skill_access.skill_masters` for the designer (E's pure move).

### R-22 — the v2.28 shape of the six tables v2.29 changes [M]
Opened: `CreateTable`/`CreateIndex` of `SkillRank`, `SkillSystem`, `SkillDefinition`, `QuestOfferTerm`, `QuestTerm`, `QuestRequest`, compiled on the SQLite dialect at `246e89b`.
Finding: the DDL is pasted verbatim in BRIEF-0116-A (TS3's fixture).

## Contract sheet

Families first: the currency family (C-05, every consumer of a currency
list), the trigger family (C-07, every reader of `trigger`), and « ready »
(C-02: one definition, every consumer calls it) were written before their
members and re-read after the last.

### C-01 — schema v2.29
Produced by: BRIEF-0116-A   Consumed by: B, C, D, E
- `skill_rank.trial_to_next` BOOLEAN NOT NULL DEFAULT 0 -- model `trial_to_next: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})`, after `points_to_next`. No CHECK.
- `skill_system.trial_to_rank_1` .. `trial_to_rank_5`, and the same five on `skill_definition`: BOOLEAN NULL -- model `trial_to_rank_<n>: Optional[bool] = None`, right after `points_to_rank_5`. NULL inherits; `trial_to_rank_<n>` says whether reaching rank n asks a trial. No CHECK.
- `QUEST_TERM_CURRENCY_CHECK = "currency IN ('money','item','relation','fact','skill','rank')"`.
- `QUEST_TERM_SHAPE_CHECK` = its current four clauses, then ` AND (currency <> 'rank' OR (direction = 'reward' AND skill_key IS NOT NULL AND amount BETWEEN 1 AND 5))`.
- `quest_request`: `pass_play_id` and `agenda_step_id` nullable; `skill_key` TEXT NULL and `target_rank` INTEGER NULL after `note`; column order `id, world_id, character_id, pass_play_id, agenda_step_id, trigger, declaration, subject, status, existence_answer, creator_text, existing_entity_id, lore_entry_id, mutation_id, offer_id, note, skill_key, target_rank, created_at, updated_at, change_history`. CHECKs: `ck_quest_request_trigger` `trigger IN ('route','blocked','dropped','trial')`; `ck_quest_request_status`, `ck_quest_request_answer` unchanged; `ck_quest_request_origin` `(trigger = 'trial' AND skill_key IS NOT NULL AND target_rank BETWEEN 1 AND 5 AND pass_play_id IS NULL AND agenda_step_id IS NULL) OR (trigger <> 'trial' AND skill_key IS NULL AND target_rank IS NULL AND pass_play_id IS NOT NULL AND agenda_step_id IS NOT NULL)`. Indexes: `idx_quest_request_world`, `idx_quest_request_step` (unique, unchanged), `idx_quest_request_trial` (`world_id`, `skill_key`, `target_rank`), not unique.
- `EXPECTED_STATIC_SCHEMA_VERSION = "v2.29"`; `scripts/migrate_v2_29_rank_trials.py` (`_PREVIOUS_VERSION = "v2.28"`).
- `QUEST_TERM_CURRENCIES` and `QUEST_REQUEST_TRIGGERS` are NOT changed by A (C and D).
Error and empty cases: a `rank` cost, a `rank` with no skill or a rank outside 1-5, a `trial` request with a step, a step request with a skill -- `IntegrityError` at the database.

### C-02 — the trial cascade and « ready »
Produced by: BRIEF-0116-B   Consumed by: C, D, E, F
In `skill_ranks.py`:
- `RANK_TRIAL_COLUMNS: tuple[str, ...] = tuple(f"trial_to_rank_{n}" for n in range(1, 6))` -- index = rank left.
- `RankStep(rank, label, points_to_next, trial_to_next: bool = False)`; `default_ladder()` False everywhere; `world_ladder` reads `bool(row.trial_to_next)` below `MAX_RANK`, False at it.
- `trial_required(rank, ladder, *, system=None, definition=None) -> bool` -- False at `MAX_RANK`; the definition's `RANK_TRIAL_COLUMNS[rank]` when not None, else the system's, else `ladder[rank].trial_to_next`.
- `trial_target(rank, xp, ladder, *, system=None, definition=None) -> Optional[int]` -- `rank + 1` when `trial_required(...)` and `points_to_next(...)` is not None and `xp >= points_to_next(...)`; else None. **A skill is « ready » exactly when this is not None.**
- `skill_trial_required(db, *, world_id, rank, skill_definition_id) -> bool` -- `skill_owners` + `world_ladder` + `trial_required`.
- `skill_trial_target(db, *, world_id, skill) -> Optional[int]` -- the same for one `Skill` row.
In `skill_access.py`:
- `held_trial_target(db, *, world_id, character_id, skill_key) -> Optional[int]` -- the character's row for `skill_key` (a base domain: `_base_row`; a definition id: `_definition_row`), then `skill_trial_target`; None when he holds no row.
Error and empty cases: none raise; an unknown definition reads the system and the world (`skill_owners`).

### C-03 — the points stop at a waiting threshold (C1)
Produced by: BRIEF-0116-B   Consumed by: D
`SkillProgress` gains `awaiting_trial: bool = False`, last. `write_skill_progress` -- signature unchanged:
- a gain whose new `xp` reaches the threshold of a rank that asks a trial (`skill_trial_required`): `xp` = the threshold, the rank unchanged, no history entry, `awaiting_trial=True`;
- a gain on a row already at that threshold: nothing moves (`xp` stays), `awaiting_trial=True`;
- every other case: today's behaviour, byte for byte (`awaiting_trial=False`).
`record_roll` returns None and writes no mutation when `skill_trial_target(db, world_id=world_id, skill=skill)` is not None; `grant_step_roll` gives nothing then; `skill_reward_points` is None then.

### C-04 — the CRUD of the ladder, the systems and the definitions
Produced by: BRIEF-0116-B   Consumed by: F
- `GET/PUT /api/skill-ranks`: each step `{rank, label, points_to_next, trial_to_next}`; `SkillRankStepBody.trial_to_next: bool = False`; `upsert_skill_rank(db, *, world_id, rank, label, points_to_next, trial_to_next: bool = False)` refuses `trial_to_next` true at rank 5 with `ValueError("upsert_skill_rank: the top rank has no trial")`, before any write; the PUT answers 422 then, no row written.
- `RankPointsBody` gains `trial_to_rank_1` .. `trial_to_rank_5: Optional[bool] = None`; `_rank_points`/`_set_rank_points` iterate `RANK_POINTS_COLUMNS + RANK_TRIAL_COLUMNS`: `GET /api/skill-systems` and `/api/skill-definitions` serve them, a POST stores them, a PUT without them clears them.
- `_skill_dict` gains `"trial_ready": trial_target(s.rank, s.xp, ladder, system=system, definition=definition) is not None`.

### C-05 — the `rank` currency
Produced by: BRIEF-0116-C   Consumed by: E, F
- `QUEST_TERM_CURRENCIES = ("money", "item", "relation", "fact", "skill", "rank")`; its comment « The six currencies of a quest ».
- `writes/quest_terms.py`: `REWARD_ONLY_CURRENCIES: tuple[str, ...] = ("rank",)`; `COUNTED_CURRENCIES`, `PERSONAL_CURRENCIES` unchanged. `clean_term` sends a `rank` term to `_clean_rank(db, world_id, where, term) -> dict`, which returns `{"direction": "reward", "currency": "rank", "counterparty_entity_id": None, "item_id": None, "fact_id": None, "skill_key": <key>, "amount": <rank>, "level": None}` or raises, in this order: `direction == "cost"` -> `f"{where}: a rank is a reward only -- a rank trial gives it"`; a counterparty -> `f"{where}: a rank reward names no counterparty"`; `skill_key` neither a base domain nor a definition of the world -> `f"{where}: {term.skill_key!r} is not a skill of this world"`; `amount` not an int 1-5 (a bool refused) -> `f"{where}: a rank reward names the rank it gives, 1 to 5"`.
- `request_service` raises `ValueError("request_service: a rank is given by a rank trial, never by a service")` when a cleaned term's currency is in `REWARD_ONLY_CURRENCIES`, before any write.
- `quest_value.term_value`: `rank` -> 0.
- `quest_wording.term_line`: `rank` -> `f"Passer au rang « {label} » en « {skill} » (épreuve)"`, `label = world_ladder(db, term.world_id)[term.amount].label` when `term.amount` is in 1-5, else `str(term.amount)`; `skill = skill_label(db, term.skill_key)`.
- `quest_settlement.apply_term`: `elif term.currency == "rank": _rank_reward(db, world_id, character_id, term.skill_key, term.amount)` before `elif cost:`; `_rank_reward` writes `write_skill_rank(db, skill_id=<the row>, rank=amount, changed_by=CHANGED_BY)` when `held_trial_target(...) == amount`, else nothing (D2-c).
- `skill_reward_points`: None when `skill_trial_target(db, world_id=world_id, skill=row)` is not None.
- `quest_settlement_view`: a `rank` reward's note -- `f"passe à « {label} » en « {skill} »"` when ready for it, else `"sans effet : la compétence n'est pas prête pour ce rang"`; `_skill_note` for a held row whose points are None below Maître -> `f"épreuve de rang à passer en « {skill} » : rien"`.
- `editor_choices` gains `"ranks": [{"rank": s.rank, "label": s.label} for s in world_ladder(db, world_id) if s.rank >= 1]`.
- `quest_designer._term`: `elif currency == "rank": return None, RANK_TERM_FR` with `RANK_TERM_FR = "Un rang ne se donne que par une épreuve de rang : le terme a été abandonné."`
- `questTerms.js`: `CURRENCY_FORMS.rank` is the line `  rank: { label: 'Rang (épreuve)', list: 'skills', counted: false, personal: false },`; `export const REWARD_ONLY_CURRENCIES = ['rank'];`; `termBody` sends `skill_key` for `skill` and `rank`, `amount` for a counted currency and for `rank`, `counterparty_entity_id` null for `rank`.
- `QuestTermRow.svelte`: the currency select omits a reward-only currency on a cost; a `rank` term shows the skill picker and a rank select of `choices?.ranks`, and no counterparty select.

### C-06 — the trial gate
Produced by: BRIEF-0116-C   Consumed by: E (the offer it proposes), the player's Journée
`acceptance_refusal(db, offer, character)`, after the L1 checks and before the eligibility: for each `rank` term of `offer_terms(db, offer.id)`, when `held_trial_target(db, world_id=offer.world_id, character_id=character.id, skill_key=term.skill_key) != term.amount` -> `f"cette épreuve est réservée à qui est prêt à passer « {label} » en « {skill} »"`. `available_offers` and `accept_quest` inherit it.

### C-07 — the trial request
Produced by: BRIEF-0116-D   Consumed by: E, F
`writes/quest_requests.py`:
- `TRIAL_TRIGGER = "trial"`; `STEP_TRIGGERS = ("route", "blocked", "dropped")`; `QUEST_REQUEST_TRIGGERS = STEP_TRIGGERS + (TRIAL_TRIGGER,)`.
- `open_request` refuses `trial` with `ValueError("quest_request: a trial request opens through open_trial_request")`, every other trigger outside `STEP_TRIGGERS` with its current message; otherwise unchanged.
- `open_trial_request(db, *, world_id, character_id, skill_key, target_rank) -> Optional[QuestRequest]`: `ValueError` on an empty `skill_key` or a `target_rank` outside 1-5; None when `character_id` is not a `player` character, or when `covering_trial_offer(...)` finds an offer; the first « live » request of (world, `trial`, `skill_key`, `target_rank`) by `created_at` when one exists -- live = status `new`, or `proposed` while its proposal's status is `proposed` or `approved`; otherwise a new request: `trigger="trial"`, `declaration=trial_declaration(...)`, `subject=trial_subject(...)`, `skill_key`, `target_rank`, no day, no step. Adds and flushes, never commits.
`quest_requests.py` (reads):
- `covering_trial_offer(db, world_id, skill_key, target_rank) -> Optional[QuestOffer]` -- the world's `open` offers holding a `quest_offer_term` `direction='reward'`, `currency='rank'`, that `skill_key` and `amount = target_rank`; the first by title then id.
- `trial_subject(db, world_id, skill_key, target_rank) -> str` -- `f"Épreuve de rang : « {skill} » vers {to}"`.
- `trial_declaration(db, world_id, character_id, skill_key, target_rank) -> str` -- `f"{name} a assez pratiqué « {skill} » pour passer de {frm} à {to} : ce rang demande une épreuve."` (`frm`, `to` = the world's labels of `target_rank - 1` and `target_rank`).
- `request_dict` reads the day only when `pass_play_id` is set (`day_number` None otherwise).
`write_skill_progress`: when a gain makes the row ready (C-03's first case, `xp` before below the threshold) -> `open_trial_request(db, world_id=world_id, character_id=skill.character_id, skill_key=skill.skill_definition_id or skill.domain, target_rank=rank + 1)`.
`dashboard_metrics._TRIGGERS_FR` gains `("trial", "Épreuve de rang")`, last.

### C-08 — « Concevoir » on a trial
Produced by: BRIEF-0116-E   Consumed by: F
- `skill_access.skill_masters(db, world_id, *, definition_id, domain) -> list[dict]` -- `cockpit/crud/skills.py::_masters` moved, body unchanged; the crud's three calls renamed.
- `quest_designer`: `TRIAL_USAGE = "quest_trial"`; `_design_call(db, values, exchanges, usage=DESIGN_USAGE, outcomes=OUTCOMES)` (an outcome outside `outcomes` -> `LlmParseError`); `_design` dispatches `request.trigger == TRIAL_TRIGGER` to `_design_trial`; the offer path, from its steps to its `move_request(proposed)`, is `_offer(db, request, subject, gathering, context, ctx, answer, design_calls, usage, outcomes) -> DesignResult` (extracted unchanged for the normal path).
- `_design_trial(db, request, design_calls)`: `covering_trial_offer` -> `move_request(covered, offer_id)`, `DesignResult("covered", notes=[f"Déjà couverte par « {offer.title} »."])`, no model call; else `subject = request.subject`, `gathering = gather_lore(db, world_id, keywords=<the skill's label, then its system's name when it has one>, names=[], entity_ids=<the ids of skill_masters>)`, never `asking`; one `quest_trial` call (`outcomes=("offer",)`), then `_offer`.
- A trial's payload: C-10 of 0121's keys, then `"repeatable": True`, its `terms` = the resolved terms followed by `{"direction": "reward", "currency": "rank", "counterparty_entity_id": None, "item_id": None, "fact_id": None, "skill_key": request.skill_key, "amount": request.target_rank, "level": None}`, and one more key `"trial": {"skill_key", "target_rank", "skill_label", "rank_label"}`. A non-trial payload is unchanged (QD2).
- The proposal: `source_type="pass_play", pass_play_id=request.pass_play_id` when the request has a day; `source_type="quest_request"`, no source otherwise.
- `apply_offer_proposal`, after the request check: a `trial` request whose payload's terms hold no reward `rank` term with its `skill_key` and `target_rank` -> `"Cette épreuve doit garder sa récompense de rang."`, nothing written.
- Prompt `quest_trial`: `PROMPT_REGISTRY["quest_trial"] = PromptSpec(surface="authoring", world_scoped=False, dry_run_capable=True, call_sites=("src/world_engine/quest_designer.py:_design_call",), default_model=_author_model)`; `seed_pilot.QUEST_TRIAL_PREAMBLE` (verbatim in E), `_quest_trial_system_prompt()`, `QUEST_TRIAL_SYSTEM_PROMPT`, `QUEST_TRIAL_PROMPT_HEADS` (head `pt-quest-trial`, the design's user template and variables); `scripts/apply_ticket_0116_trial_prompt.py`.

### C-09 — the surfaces
Produced by: BRIEF-0116-F   Consumed by: Nia
- `competences.svelte.js`: `RANK_TRIAL_KEYS`, `rankTrials(row)` in the skill, system, draft and blank records, `inheritedTrial(record, n)`, `trialsBody(record)` spread as `...trialsBody(record)` in `saveSkill` and `saveSystem`; `saveRanks` sends `trial_to_next`.
- `CompetencesSheet.svelte`: the `thresholds` snippet gains one select per rank (`''` « hérité (oui|non) », `'true'` « Épreuve », `'false'` « Sans épreuve »); the ranks record one checkbox per rank below Maître, « Épreuve pour passer au rang suivant ».
- `PjSkillFiche.svelte`: `pointsLine(s)` ends « · épreuve de rang à passer » when `s.trial_ready`.
- `QuestRequests.svelte`: `TRIGGER_LABEL.trial = 'épreuve de rang'`.
- `QueueCard.svelte`: a « ÉPREUVE » badge for `source_type === 'quest_request'`; in the quest block, « Épreuve de rang : « <skill> » vers <rank> » from `questPayload.trial`.
- `questOffers.svelte.js`: `REVIEW_KEYS` gains `'trial'`.

## Gate output

### (a) Property trace

One line per property the briefs assert about `main`: property -- finding -- declaring file opened.

- `RankStep`'s fields; `world_ladder` never writes; the cascade order; `RANK_POINTS_COLUMNS[rank]` -- R-01 -- `skill_ranks.py`.
- `skill_rank`'s columns, CHECKs, unique index -- R-01 -- `models/config.py`.
- `SkillSystem`/`SkillDefinition` declare `points_to_rank_1..5` then (definition) `requires_master` -- R-01 -- `models/canon.py`.
- `models/config.py` imports `text` -- R-01 -- `models/config.py`.
- `write_skill_progress`'s rules and 58 lines; `SkillProgress`'s fields; `write_skill_rank`'s effect -- R-02 -- `writes/characters.py`.
- both are allow-listed; the policy comment's list -- R-02 -- `canon_write_policy.txt`.
- `record_roll` skips a Maître and writes no mutation; `grant_step_roll`'s three skips -- R-03 -- `cockpit/skill_progress.py`.
- `upsert_skill_rank`'s refusals; fetch-or-create -- R-04 -- `writes/config.py`.
- `RankPointsBody`, `_rank_points`, `_set_rank_points`, `_skill_dict`'s keys, the ladder routes -- R-04 -- `cockpit/crud/skills.py`.
- `_masters`' body and its three callers -- R-21 -- `cockpit/crud/skills.py`.
- rebuild vs `ADD COLUMN`; refuse/idempotent/post-check shape -- R-05 -- `scripts/migrate_v2_15_skill_ranks.py`, `scripts/migrate_v2_16_npc_skills.py`.
- v2.28's post-check is a subset of CHECK names -- R-05 -- `scripts/migrate_v2_28_quest_requests.py`.
- the current schema version -- R-05 -- `schema_version.py`.
- no model foreign key to the three rebuilt tables -- R-05 -- `models/` (grep).
- the term literals, the two tables' CHECKs, the tuple -- R-06 -- `models/quests.py`.
- `debt_term`'s own currency CHECK -- R-06 -- `models/quests.py`.
- `clean_term`'s order and refusals; `copy_terms_to_quest` copies `TERM_COLUMNS` -- R-06 -- `writes/quest_terms.py`.
- `TermBody.currency` is free text -- R-06 -- `cockpit/quest_offer_save.py`.
- `apply_term`'s branches and fall-through; rewards never checked; `skill_reward_points` None at Maître -- R-07 -- `writes/quest_settlement.py`.
- `_skill_note`'s reading of None -- R-07 -- `quest_settlement_view.py`.
- `request_service` validates with `clean_terms`, applies with `apply_term` -- R-07 -- `writes/debt_sources.py`.
- `term_value`'s fall-through; `term_line`'s fall-through; the term rows carry `world_id` -- R-08 -- `quest_value.py`, `quest_wording.py`, `models/quests.py`.
- `acceptance_refusal`'s order; `accept_quest` and `available_offers` use it -- R-09 -- `writes/quests.py`, `quest_reads.py`.
- `editor_choices`' keys -- R-09 -- `quest_reads.py`.
- `quest_request`'s NOT NULLs, CHECKs, indexes -- R-10 -- `models/pipeline.py`.
- `open_request`'s refusals and idempotence; `move_request` -- R-10 -- `writes/quest_requests.py`.
- `request_dict` reads the day unconditionally -- R-10 -- `quest_requests.py`.
- `_TRIGGERS_FR` and the metric's rows -- R-10 -- `dashboard_metrics.py`.
- the routes' `_may_design` -- R-10 -- `cockpit/routes/quest_requests.py`.
- `_design`'s sequence and 55 lines; `_term`'s unknown-currency note; `_payload`'s keys and `repeatable: False` -- R-11 -- `quest_designer.py`.
- `gather_lore`'s signature -- R-11 -- `quest_lore.py`.
- the applier's refusals -- R-11 -- `cockpit/quest_offer_save.py`.
- a prompt usage = registry entry + seed head + CREATE-HEAD script; the language slice -- R-12 -- `prompt_registry.py`, `scripts/seed_pilot.py`, `scripts/apply_ticket_0121_designer_prompts.py`, `checks/prompt_registry.py`.
- `proposed_mutation` has no CHECK; the duplicate guard with no source -- R-13 -- `models/pipeline.py`, `cockpit/routes/mutations.py`.
- the card's badges -- R-13 -- `QueueCard.svelte`.
- the Compétences snippet and records; the fiche's `pointsLine` -- R-14 -- `CompetencesSheet.svelte`, `competences.svelte.js`, `PjSkillFiche.svelte`.
- `CURRENCY_FORMS`' line shape, `termBody`, the row, `REVIEW_KEYS` -- R-15 -- `questTerms.js`, `QuestTermRow.svelte`, `questOffers.svelte.js`.
- `TRIGGER_LABEL`; « Jour — » -- R-16 -- `QuestRequests.svelte`.
- every pinned rule of R-17 -- R-17 -- each check's implementation, at the lines cited.
- the budgets, INV-15, the highest id -- R-18 -- `CLAUDE.md`, `.claude/rules/skills.md`, `checks/claude_md_contract.py`, `invariant_ids.retired`.
- the gate's timeout -- R-19 -- `checks/corpus_gate.py`.
- module sizes -- R-20 -- the modules (measured), `checks/module_budget.py`.
- `_base_row`/`_definition_row`/`skill_label`; `skill_access`' imports -- R-21 -- `skill_access.py`.
- the v2.28 DDL -- R-22 -- the models (compiled).

### (b) Case tables

**`write_skill_progress` (C-03).** `T` = the threshold of the row's rank, `trial` = `skill_trial_required` for it.

| points | trial | xp before | result | history | `awaiting_trial` | D: request |
|---|---|---|---|---|---|---|
| > 0 | no | xp + p < T | xp + p | no | False | no |
| > 0 | no | xp + p >= T | rank + 1, 0 | yes | False | no |
| > 0 | yes | xp + p < T | xp + p | no | False | no |
| > 0 | yes | xp < T <= xp + p | xp = T | no | True | opened |
| > 0 | yes | xp >= T | unchanged | no | True | no |
| > 0 | -- | rank 5 | xp + p (today) | no | False | no |
| < 0 | any | xp + p >= 0 | xp + p | no | False | no |
| < 0 | any | xp + p < 0, rank > 0 | rank - 1, refilled (today) | yes | False | no |
| < 0 | any | rank 0 | 0 | no | False | no |
| 0 | -- | -- | `ValueError` | -- | -- | -- |

Every row reachable; the waiting cases never move the rank.

**`open_trial_request` (C-07).**

| character | covering offer | live request | result |
|---|---|---|---|
| not a player | -- | -- | None |
| player | yes | -- | None |
| player | no | `new` | that request |
| player | no | `proposed`, its proposal `proposed` or `approved` | that request |
| player | no | only `dropped`, `covered`, or `proposed` with an `applied`/`rejected` proposal | a new `new` request |
| player | no | none | a new `new` request |

**A `rank` reward at settlement (C-05).**

| `held_trial_target` | term's `amount` | result |
|---|---|---|
| = amount | n | rank n, xp 0, one history entry (`quest_settlement`) |
| another rank | n | nothing (« sans effet ») |
| None (not waiting, or no row) | n | nothing (« sans effet ») |

**Acceptance (C-06).**

| offer | character | result |
|---|---|---|
| no `rank` term | any | as today |
| `rank` (k, n) | ready for n in k | the eligibility decides, as today |
| `rank` (k, n) | not ready, or ready for another rank | refused, the trial sentence |

**« Concevoir » (C-08).**

| request | covering offer | model answer | result |
|---|---|---|---|
| step trigger | -- | -- | 0121's path, unchanged |
| `trial` | yes | none called | `covered`, `offer_id` |
| `trial` | no | `offer` | proposal `quest_request`-sourced, repeatable, rank reward last, `trial` key |
| `trial` | no | anything but `offer` | `LlmParseError` (502), nothing written |

**The applier on a trial (C-08).**

| approved terms | result |
|---|---|
| hold the reward `rank` (`skill_key`, `target_rank`) | 0121's other refusals, then the offer written |
| do not | « Cette épreuve doit garder sa récompense de rang. », nothing written |

### (c) Enumerations

`QUEST_TERM_CURRENCIES` (`models/quests.py:116`): `("money", "item", "relation", "fact", "skill")`.
`QUEST_REQUEST_TRIGGERS` (`writes/quest_requests.py:27`): `("route", "blocked", "dropped")`.
Callers of `write_skill_progress` (`grep -rn "write_skill_progress(" src`, `def` excluded):
```
src/world_engine/writes/quest_settlement.py:177:        write_skill_progress(db, skill_id=row.id, world_id=world_id, points=points, changed_by=CHANGED_BY)
src/world_engine/cockpit/skill_progress.py:60:    write_skill_progress(db, skill_id=skill_id, world_id=mut.world_id, points=points,
src/world_engine/cockpit/skill_progress.py:128:    write_skill_progress(db, skill_id=skill.id, world_id=world_id, points=ROLL_POINTS,
```
Callers of `apply_term`:
```
src/world_engine/writes/debt_sources.py:70:        apply_term(db, world_id=world_id, character_id=character.id, term=term, giver_id=provider.id, reason=label,
src/world_engine/writes/debt_sources.py:153:        apply_term(db, world_id=quest.world_id, character_id=quest.character_id, term=term,
src/world_engine/writes/quest_settlement.py:231:        apply_term(db, world_id=quest.world_id, character_id=quest.character_id, term=term,
```
Callers of `acceptance_refusal`: `writes/quests.py:207` (`accept_quest`), `quest_reads.py:194` (`available_offers`).
Callers of `clean_terms`: `writes/quests.py:143` (`write_quest_offer`), `writes/debt_sources.py:62` (`request_service`).
Callers of `skill_reward_points`: `writes/quest_settlement.py:175`, `quest_settlement_view.py:41`.
Callers of `world_ladder`/`upsert_skill_rank`/`RankStep(`: `skill_ranks.py:62,75,111`, `cockpit/skill_progress.py:67`, `cockpit/crud/skills.py:121,145,151,257,266,306` -- no other writer of `skill_rank`.
`source_type` values a `ProposedMutation` is written with (`grep -rn 'source_type="' src`, ledger lines excluded): `pass_play` (`day_events.py`, `day_concordance.py`, `day_mutations.py`, `quest_designer.py`), `world_tick` (`tick.py`), `conversation` (`skill_progress.py`, `play_discovery.py`, `play_stream.py`, `analyzer_transcript.py`).
Foreign keys to the rebuilt tables (`grep -rn 'foreign_key="quest_request\|foreign_key="quest_term\|foreign_key="quest_offer_term\|ForeignKey("quest_...' src/world_engine/models/`): none (exit 1).
The checks that read a file this lot edits (`grep -rln <file> tooling/verify/checks`):
```
questTerms.js: quest_rewards.py
QuestTermRow.svelte: (none)
CompetencesSheet.svelte: page_contract.py npc_skills.py skill_progression.py
competences.svelte.js: npc_skills.py graph_primitive.py skill_progression.py
PjSkillFiche.svelte: npc_skills.py graph_primitive.py skill_progression.py
QueueCard.svelte: graph_primitive.py quest_review_card.py event_analyzer.py event_editor.py
QuestRequests.svelte: quest_request_panel.py
questOffers.svelte.js: event_conditions.py quests.py condition_interpreter.py quest_review_card.py conditions.py debts.py attribute_interpreter.py quest_rewards.py
quest_wording.py: (none)
quest_value.py: (none)
skill_ranks.py: skill_progression.py
quest_settlement_view.py: quest_rewards.py
quest_designer.py: quest_designer.py name_index.py knowledge_identity.py
quest_offer_save.py: condition_interpreter.py
dashboard_metrics.py: dashboard_registry.py
crud/skills.py: skill_progression.py
writes/characters.py: zone_placement.py
skill_progress.py: (none)
debt_sources.py: (none)
writes/quest_terms.py: (none)
writes/quests.py: event_conditions.py
writes/quest_requests.py: knowledge_identity.py
quest_requests.py: quest_requests.py knowledge_identity.py
quest_reads.py: event_conditions.py quests.py
writes/config.py: known_reachability.py encounter_registry.py
```
No file is moved or renamed by this lot; `_masters` moves between two files that stay (E), and no check names it (`grep -rn "_masters" tooling/verify/checks`: empty).
Negative claims and what was looked at:
- « no CHECK names `trial_to_next` » -- C-01 adds none; A1 pins `skill_rank`'s CHECK set (R-17).
- « nothing outside `quest_reads.py` and `writes/quests.py` contains `role="failure"` » -- EE5's own scan (R-17); this lot adds none.

### (d) Families
The currency family (C-05: the tuple, the CHECK, `clean_term`, `apply_term`, `term_value`, `term_line`, the view, the service, `_term`, `questTerms.js`, the row), the trigger family (C-07: the tuple, the CHECK, `open_request`, `open_trial_request`, `_TRIGGERS_FR`, `TRIGGER_LABEL`, `_design`) and « ready » (C-02: `trial_target`, read by C-03, C-04, C-05, C-06) were written before their members and re-read after the last. ✓

### (e) Gates and the modules that satisfy them

- `rank_trial_schema.py` (A) -- `models/config.py`, `models/canon.py`, `models/quests.py`, `models/pipeline.py`, `schema_version.py`, `scripts/migrate_v2_29_rank_trials.py`; its migration run is a subprocess on a fresh file (R-19: its own check, not a slow one).
- existing `skill_progression.py` A1, `skill_system_shape.py`, `quest_requests.py` QR1, `npc_skills.py` A2/A3 (A updates them, R-17). A prototype of A's models with these four updates passed the full corpus (174 checks) at `246e89b`; `schema_version_agreement.py`, `schema_partition.py` (the doc header, the changelog's newest entry); `world_cascade.py` W4 (its raw rows satisfy the new CHECKs: a `route` request with its day and step, `item`/`money` terms, `trial_to_next` defaulted); `quest_rewards.py` RA1 (both tables' CHECKs equal) and RA2, `skill_progression.py` A2 (the older migrations create the rebuilt tables from the current models).
- `rank_trials.py` (B to F) -- `skill_ranks.py`, `skill_access.py`, `writes/characters.py`, `cockpit/skill_progress.py`, `writes/config.py`, `cockpit/crud/skills.py` (B); `models/quests.py`, `writes/quest_terms.py`, `writes/quest_settlement.py`, `writes/debt_sources.py`, `writes/quests.py`, `quest_value.py`, `quest_wording.py`, `quest_settlement_view.py`, `quest_reads.py`, `quest_designer.py`, `questTerms.js`, `QuestTermRow.svelte`, `.claude/rules/skills.md` (C); `writes/quest_requests.py`, `quest_requests.py`, `dashboard_metrics.py` (D); `quest_designer.py`, `cockpit/quest_offer_save.py`, `prompt_registry.py`, `scripts/seed_pilot.py`, `scripts/apply_ticket_0116_trial_prompt.py` (E, a stubbed `chat` -- `quest_designer.py`'s precedent); the Svelte files of C-09 and the built bundle (F, static).
- existing `quest_rewards.py` RD1 (C passes it: the tuple and the `CURRENCY_FORMS` line move together, the line of the exact shape, reward-only in its own constant); `npc_skills.py` C2, `skill_progression.py` A4/C3/D2, `page_contract.py`, `graph_primitive.py` (F passes them: patterns kept, two snippet renders, two `...pointsBody(record)`, no word `tier`).
- existing `quest_requests.py` QR6 (D updates `EXPECTED_ROWS`: one row ("Origine", "Épreuve de rang", 0, 3) after « Savoir introuvable »).
- existing `knowledge_identity.py` K3 (D and E: the census of the files each edits, ADAPT; R-17).
- existing `quest_designer.py` QD1-QD8 (E passes them: the normal path unchanged by the extraction, C-10's keys for a non-trial request, the stub's routing untouched -- the trial prompt starts « Tu conçois une épreuve de rang », the new check's own stub routes it).
- existing `prompt_registry.py` rules 1-2 (E: the head seeded, `_design_call` exists); `name_index.py` R5 (no new creator-regime file: the designer and `quest_lore.py` stay the only ones); `proposal_producers.py` (no new `proposed_by`); `json_ui_boundary.py` (no new JSON column; the payload's `trial` key rides 0121's exemption).
- existing `claude_md_contract.py` (C: INV-64 in `skills.md`, its marker naming `rank_trials.py`, `paths:` matching three existing files, <= 4,000 characters, 100-character lines); `event_conditions.py` EE5 (no `role="failure"` added); `quests.py` QB4 (no `agenda_id`/`step_id` dict in `quest_reads.py`); `single_canon_write.py` (`write_skill_rank` stays the write site; `settle_quest` only calls it).
- existing `module_budget.py`, `function_length.py` (R-20); `frontend_build_fresh.py` (C and F rebuild and commit); `file_map.py` (A, E add modules: `gen_file_map.py`); `decisions_index.py` (each brief's record: `gen_decisions_index.py`).
- `corpus_gate.py` -- every check, 15 s each; `rank_trials.py` builds one small fixture per brief's rules.

## Docs to update (chat-side, Nia's project)

`SERIE-conditions.md`: 0116 rédigé (6 briefs A–F, schéma v2.29), ses codes.

## Amendments

(none)
