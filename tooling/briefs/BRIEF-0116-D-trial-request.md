<!-- slug: trial-request -->
# BRIEF 0116-D — "A player's skill ready for its trial asks the creator for one"

Lot: LOT-0116-rank-trials.md (authoritative on conflict)
Depends on: BRIEF-0116-A (the request's columns), BRIEF-0116-B (the waiting path of `write_skill_progress`), BRIEF-0116-C (an offer holding a `rank` reward)

## Anchors to confirm (Mini-RECON)

Halt if any has moved.

- `src/world_engine/models/pipeline.py` -> `QuestRequest.pass_play_id`/`agenda_step_id` nullable, `skill_key`, `target_rank`, `ck_quest_request_origin` (A landed).
- `src/world_engine/writes/characters.py` -> `write_skill_progress` computes `awaiting` and returns `SkillProgress(..., awaiting_trial=awaiting)` (B landed).
- `src/world_engine/models/quests.py` -> `QUEST_TERM_CURRENCIES` ends `"rank"` (C landed).
- `src/world_engine/writes/quest_requests.py:27` -> `QUEST_REQUEST_TRIGGERS: tuple[str, ...] = ("route", "blocked", "dropped")`; `:42-63` `open_request`; `:70-92` `move_request`; `:25` imports `AgendaStep, QuestRequest`.
- `src/world_engine/quest_requests.py:26-43` -> `request_dict`, `play = db.get(PassPlay, request.pass_play_id)`; `:8-10` imports.
- `src/world_engine/dashboard_metrics.py:259-260` -> `_TRIGGERS_FR` of three pairs; `:296` the metric's note « Ce que deviennent les demandes de quête nées des journées (P1, S3, D2). ».
- `tooling/verify/checks/quest_requests.py:52-62` -> `EXPECTED_ROWS` of nine tuples, « Savoir introuvable » third.
- `tooling/verify/checks/knowledge_identity.py:109-125` -> `_SUBJECT_CENSUS`, `writes/quest_requests.py` 1, `quest_requests.py` 2.

## Facts carried

### R-02 — the one writer of points (the lines this brief needs) [M]
Opened: `src/world_engine/writes/characters.py:1-39`, `:145-210`.
Finding: every gain of points goes through `write_skill_progress`; its three callers are `skill_progress.apply_skill_progress`, `skill_progress.grant_step_roll` and `quest_settlement._skill_reward`. After B it stops a gain at the threshold of a rank that asks a trial and returns `awaiting_trial`.
Consequence: the request is opened inside it, on the gain that makes the row ready -- every path opens it, none can forget.

### R-10 — the quest request [M]
Opened: `src/world_engine/models/pipeline.py:591-630` (`QuestRequest`); `src/world_engine/writes/quest_requests.py:1-92`; `src/world_engine/quest_requests.py:1-50`; `src/world_engine/dashboard_metrics.py:259-296` (`_TRIGGERS_FR`, `_quest_requests`); `src/world_engine/writes/worlds.py:84`; `src/world_engine/cockpit/routes/quest_requests.py:55-121`.
Finding: `open_request` refuses a trigger outside `QUEST_REQUEST_TRIGGERS`, an empty declaration, a missing step, and returns the step's existing request. `move_request` appends the former state. `request_dict` reads `db.get(PassPlay, request.pass_play_id)` unconditionally. `_TRIGGERS_FR` is a literal of three rows; `_quest_requests` emits one `Origine` row per entry, `of` = the requests in scope. `_may_design` allows `new`, `covered`, and a rejected `proposed`. `writes/quest_requests.py` is not exported from `writes/__init__.py`.
Consequence: a `trial` request has no day and no step, a skill and a target rank, and its own writer `open_trial_request`; `request_dict` guards the missing day; the metric gains one row; the routes need no change.

### R-17 — the existing checks (the lines this brief needs) [M]
- `quest_requests.py:52-62` (`EXPECTED_ROWS`), `:280-316` (QR6 compares the metric rows to it exactly, and a world with none to the same labels at 0); QR2 (`open_request` refuses an unknown trigger).
- `knowledge_identity.py:31-35`, `:109-125` (K3: the `subject` references of `src/world_engine` -- an attribute `.subject`, a string constant `"subject"`, a `subject=` keyword or a `subject` parameter --, per file, equal `_SUBJECT_CENSUS` exactly).

### R-20 — module sizes [M] (the modules this brief edits)
`writes/quest_requests.py` 3/92; `quest_requests.py` 3/50; `writes/characters.py` 5/250 (`write_skill_progress` after B, <= 80); `dashboard_metrics.py` 20/339.

## Contracts

### C-03 — the points stop at a waiting threshold (consumed)
`write_skill_progress` -- a gain whose new `xp` reaches the threshold of a rank that asks a trial: `xp` = the threshold, the rank unchanged, `awaiting_trial=True`; a gain on a row already at that threshold: nothing moves, `awaiting_trial=True`.

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

## Context

F1: Nia does not write trials herself -- she reviews, edits and confirms
them. This step opens the request the designer will work from (E): one per
skill and rank in the world, born the moment a player character's skill
becomes ready and no open offer already gives that rank. The request has no
day; the panel and the metric take it as they are.

## Scope IN

1. `src/world_engine/writes/quest_requests.py` -- C-07: the three constants (`QUEST_REQUEST_TRIGGERS` keeps its name and becomes `STEP_TRIGGERS + (TRIAL_TRIGGER,)`); `LIVE_PROPOSAL_STATUSES: tuple[str, ...] = ("proposed", "approved")`; `open_request`'s trigger test against `STEP_TRIGGERS` with the two messages of C-07; `open_trial_request` and its private `_live(db, request) -> bool`. Imports: `Character, Entity, ProposedMutation` from `..models`; `covering_trial_offer, trial_declaration, trial_subject` from `..quest_requests`. The module docstring gains: « - `open_trial_request(...)` : open the request of a skill ready for a rank trial (TICKET-0116, F1-a): one live request per skill and rank in the world, none for a non-player character or while an open offer gives that rank. »
2. `src/world_engine/quest_requests.py` -- C-07's three reads and the guarded `request_dict` (`play = db.get(PassPlay, request.pass_play_id) if request.pass_play_id else None`). Imports `QuestOfferTerm` from `.models`, `skill_label` from `.skill_access`, `world_ladder` from `.skill_ranks`. `covering_trial_offer` joins `QuestOfferTerm` to `QuestOffer` (`QuestOffer.world_id == world_id`, `QuestOffer.status == "open"`, the term's four columns), ordered by `QuestOffer.title`, `QuestOffer.id`, `.first()`. The module docstring: « ... and a rank trial's reads: the open offer that already gives the rank, the request's subject and declaration (TICKET-0116). »
3. `src/world_engine/writes/characters.py`, `write_skill_progress`: after the `if awaiting:` assignment, `if awaiting and xp_before < needed: open_trial_request(...)` per C-07, imported from `.quest_requests`. Its docstring: « The gain that makes the row ready opens the rank trial's request (`writes.quest_requests.open_trial_request`, TICKET-0116 F1-a). » Still <= 80 lines.
4. `src/world_engine/dashboard_metrics.py`: `_TRIGGERS_FR` gains `("trial", "Épreuve de rang")`, last; the metric's note becomes « Ce que deviennent les demandes de quête nées des journées et des épreuves de rang (P1, S3, D2). ». No other change.
5. `tooling/verify/checks/quest_requests.py`: `EXPECTED_ROWS` gains `("Origine", "Épreuve de rang", 0, 3),` right after the « Savoir introuvable » row; QR6's docstring: « ... one request of each step trigger (no trial) ... ». Nothing else.
6. `tooling/verify/checks/rank_trials.py` -- its docstring gains, and `main()` runs after TC, these rules:
   - **TD1** -- the opening (fixture: a world whose rank 1 asks a trial; player characters P, Q, R, S; an NPC N; each with a base `agility` row at rank 1, 9 points). `write_skill_progress(P, +1)` -> exactly one `quest_request`: trigger `trial`, `skill_key` `agility`, `target_rank` 2, status `new`, `pass_play_id` and `agenda_step_id` None, `declaration` « P a assez pratiqué « agility » pour passer de Initié à Apprenti : ce rang demande une épreuve. », `subject` « Épreuve de rang : « agility » vers Apprenti »; P `+1` again -> still one; N `+1` -> still one; Q `+1` -> still one, the same row (live). That request moved to `dropped`: R `+1` -> a second request, `new`. An open offer whose reward is `rank` agility 2 written through `write_quest_offer`: S `+1` -> no new request; `covering_trial_offer(db, world, "agility", 2)` is that offer; `(…, "agility", 3)` and `(…, "perception", 2)` are None.
   - **TD2** -- the edges. `open_request(trigger="trial", ...)` raises C-07's message; `open_trial_request` raises on `target_rank` 6 and on an empty `skill_key`; `request_dict` of a trial request gives `day_number` None and `trigger` `trial` without raising; `compute_metrics` over the fixture holds the row (« Origine », « Épreuve de rang », 2, 2).
7. K3 of `knowledge_identity.py` -- see Decision rights, ADAPT.
8. `tooling/standards/ARCHITECTURE_DECISIONS.md`, above the footer, header verbatim `## A SKILL READY FOR ITS TRIAL ASKS THE CREATOR FOR ONE (TICKET-0116) -- open_trial_request (BRIEF-0116-d, no schema change)`; body: F1, F1-a (per skill and rank in the world, the live rule, a dropped request reopened by the next readiness, none for an NPC or while an open offer gives the rank), opened inside `write_skill_progress` so no path forgets it, a request with no day (`request_dict`), the metric's row. Then `gen_decisions_index.py`, `gen_file_map.py`.

## Scope OUT

- Designing the trial (E): « Concevoir » on a `trial` request still runs 0121's path until E -- not exercised here.
- Closing a request when the creator raises the rank by hand (lot drafting decision 14).
- Any route change; any frontend change (F: the panel's label, the card's badge).
- A request per character (F1-a: per skill and rank).
- `INQUIRY_TRIGGERS` (`route`, `dropped`): a trial is never an inquiry step.

## Invariants to defend

- **INV-18** -- writers never commit: `open_trial_request` adds and flushes; the caller of `write_skill_progress` owns the transaction.
- **INV-15** -- the roll's mutation stays the one auto-applied mutation: the request is a pipeline row, not a mutation, and nothing reaches the canon.
- **INV-02 / INV-62** -- nothing of the request reaches a player surface: no player route reads `quest_request`.

## Decision rights

STOP:
- an anchor does not hold;
- an import cycle appears between `writes/characters.py`, `writes/quest_requests.py` and `quest_requests.py` that a function-level import does not resolve;
- QR1-QR5 or QR7 of `quest_requests.py` go red.
ADAPT:
- an import cycle at module load between those three files: import `open_trial_request` inside `write_skill_progress` (function-level), with a one-line comment naming the cycle; report.
- K3 of `knowledge_identity.py` reports a census mismatch on exactly the files this brief edits (`writes/quest_requests.py`, `quest_requests.py`): set those entries of `_SUBJECT_CENSUS` to the counts measured, under the comment `# TICKET-0116, BRIEF-0116-D: a trial request's subject -- never a knowledge key.`; report the numbers. A mismatch on any other file is a STOP.
REPORT-ONLY:
- a request opened in a fixture of another check by a gain that crosses a trial threshold (none expected: no other check sets a trial).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/rank_trials.py` -> `PASS` (TB, TC, TD1-TD2).
- [ ] Named mutations, each red then reverted: `open_trial_request`'s player test removed -> TD1 red (N opens one); the live test always False -> TD1 red (Q opens a second); `covering_trial_offer` ignoring `amount` -> TD1 red (`(…, "agility", 3)` finds the offer); the call in `write_skill_progress` removed -> TD1 red; `request_dict`'s guard removed -> TD2 red.
- [ ] `quest_requests.py` (QR1-QR7), `knowledge_identity.py`, `dashboard_registry.py`, `dashboard_tab.py`, `quest_designer.py`, `quest_request_panel.py`, `skill_progression.py`, `module_budget.py`, `function_length.py`, `import_cycle.py` -> `PASS`.
- [ ] `python tooling/verify/checks/corpus_gate.py` -> `PASS`.
- [ ] `/review-step` then `/close-step` on the commit.

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md` (item 8); `DECISIONS_INDEX.md`, `FILE_MAP.md` regenerated.
- No schema change.
