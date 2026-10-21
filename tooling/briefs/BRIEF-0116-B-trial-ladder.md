<!-- slug: trial-ladder -->
# BRIEF 0116-B — "The trial cascade, « ready », and the points that stop at a waiting threshold"

Lot: LOT-0116-rank-trials.md (authoritative on conflict)
Depends on: BRIEF-0116-A (the trial columns)

## Anchors to confirm (Mini-RECON)

Halt if any has moved.

- `src/world_engine/schema_version.py:15` -> `"v2.29"` (A landed); `models/config.py` `SkillRank.trial_to_next`; `models/canon.py` `SkillSystem`/`SkillDefinition` `trial_to_rank_1..5`.
- `src/world_engine/skill_ranks.py:46-50` -> `RankStep(rank, label, points_to_next)`, frozen; `:68-79` `world_ladder`; `:82-95` `points_to_next`; `:98-105` `skill_owners`; `:108-111` `skill_points_to_next`.
- `src/world_engine/skill_access.py:45-52` -> `_base_row(db, character_id, domain)`; `:55-58` `_definition_row(db, character_id, definition_id)`; `:30` imports `DEFAULT_RANK, rank_modifier` from `skill_ranks`.
- `src/world_engine/writes/characters.py:145-210` -> `SkillProgress(rank_before, rank, xp, points_to_next)`; `write_skill_progress(db, *, skill_id, world_id, points, changed_by)`, its rank-up line `rank, xp = rank + 1, 0`; `:37` imports `MAX_RANK, RANKS, skill_points_to_next`.
- `src/world_engine/cockpit/skill_progress.py:79-109` -> `record_roll`, its early `return None` on `skill is None or skill.rank >= MAX_RANK or db.get(World, world_id) is None`; `:112-129` `grant_step_roll`, its `if skill is None or skill.rank >= MAX_RANK: return`.
- `src/world_engine/writes/quest_settlement.py:79-84` -> `skill_reward_points(db, world_id, row)`.
- `src/world_engine/quest_settlement_view.py:36-42` -> `_skill_note`, « déjà Maître en « {label} » : rien ».
- `src/world_engine/writes/config.py:536-569` -> `upsert_skill_rank(db, *, world_id, rank, label, points_to_next)`.
- `src/world_engine/cockpit/crud/skills.py:55` (the `skill_ranks` import), `:92-110` `_skill_dict`, `:113-114` `_rank_step_dict`, `:124-151` `SkillRankStepBody`, `update_skill_ranks`, `:335-352` `RankPointsBody`, `_rank_points`, `_set_rank_points`.

## Facts carried

### R-01 — the ladder and its cascade [M]
Opened: `src/world_engine/skill_ranks.py:1-111` (docstring, `RANKS`, `MAX_RANK = 5`, `RankStep` at `:46-50`, `default_ladder` `:60-65`, `world_ladder` `:68-79`, `points_to_next` `:82-95`, `skill_owners` `:98-105`, `skill_points_to_next` `:108-111`); `src/world_engine/models/config.py:240-256` (`SkillRank`); `src/world_engine/models/canon.py:580-612` (`RANK_POINTS_CHECK`, `SkillSystem`), `:617-660` (`SkillDefinition`).
Finding: `RankStep(rank, label, points_to_next)` is a frozen dataclass; `world_ladder` reads the world's `skill_rank` rows over `default_ladder()` and never writes; `points_to_next(rank, ladder, *, system, definition)` takes the definition's `points_to_rank_<rank+1>`, else the system's, else the ladder's, None at `MAX_RANK`; `RANK_POINTS_COLUMNS[rank]` is `points_to_rank_<rank+1>` (index = rank left). `skill_ranks.py` imports only `models`.
Consequence: the trial flag mirrors the points exactly, the most specific non-null value winning (B1); the writer refuses a trial at rank 5.

### R-02 — the one writer of points, and who calls it [M]
Opened: `src/world_engine/writes/characters.py:1-39`, `:65-102` (`write_skill_rank`), `:145-210` (`SkillProgress`, `write_skill_progress`); `tooling/verify/canon_write_policy.txt:30-34`, `:68`.
Finding: `write_skill_progress` adds `points` (non-zero) to `xp`; when a gain reaches `skill_points_to_next` the rank rises by one and `xp` restarts at 0, at most one rank per call; a loss below 0 lowers the rank and refills `xp` from the lower threshold; `change_history` gets `{rank, xp, changed_at, by}` only when the rank moves; 58 lines today. `SkillProgress(rank_before, rank, xp, points_to_next)`.
Enumeration: three callers of `write_skill_progress` -- `skill_progress.apply_skill_progress`, `skill_progress.grant_step_roll`, `quest_settlement._skill_reward`.
Consequence: C1 lives in `write_skill_progress` itself, so every caller stops at a waiting threshold by construction.

### R-03 — the two roll paths [M]
Opened: `src/world_engine/cockpit/skill_progress.py:1-129`.
Finding: `record_roll` returns None and writes no mutation for no row, a Maître, an unknown world; otherwise writes one `skill_progress` mutation (`proposed_by='engine_roll'`) and applies it at once. `grant_step_roll` gives the owner's base row one point through `write_skill_progress`, nothing for no domain, no row, a Maître.
Consequence: both skip a waiting skill the way they skip a Maître -- no mutation is written for a roll that would earn nothing.

### R-04 — the ladder and threshold CRUD [M]
Opened: `src/world_engine/cockpit/crud/skills.py:55`, `:92-110`, `:113-151`, `:172-184`, `:261-306`, `:309-358`, `:483-533`; `src/world_engine/writes/config.py:536-569`.
Finding: `update_skill_ranks` upserts all six steps in one transaction through `upsert_skill_rank`, which refuses an empty label, points at rank 5, missing or < 1 points below it (`ValueError`), fetch-or-create, never a DELETE. `RankPointsBody` declares the five `points_to_rank_<n>`; `_rank_points(row)` and `_set_rank_points(row, body)` iterate `RANK_POINTS_COLUMNS`, so a system's and a definition's dict serve them and a PUT replaces all five. `_skill_dict` serves `rank`, `rank_label`, `xp`, `points_to_next`. The module is 667 lines, 24 functions.
Consequence: the trial flags ride the same bodies and helpers; `SkillRankStepBody` gains `trial_to_next`; `_skill_dict` gains `trial_ready`.

### R-07 — settling a quest (the lines this brief needs) [M]
Opened: `src/world_engine/writes/quest_settlement.py:71-84` (`skill_row`, `skill_reward_points`); `src/world_engine/quest_settlement_view.py:36-50` (`_skill_note`, `_terms`).
Finding: `skill_reward_points` is None at Maître; `_skill_note` reads its None as « déjà Maître ».
Consequence: `skill_reward_points` is None for a waiting skill too (silence), and `_skill_note` tells the two apart.

### R-17 — the existing checks (the lines this brief needs) [M]
- `skill_progression.py:444-446` (A4: the word `tier` absent from `crud/skills.py`); B1-B3 run on the default ladder (no trial anywhere); C1-C2 call `upsert_skill_rank` and the CRUD with keyword arguments.
- `quest_rewards.py` RC3 reads « +4 point(s) » and « apprend » in the settlement view's notes.

### R-19 — the time a check may take [M]
Opened: `tooling/verify/checks/corpus_gate.py:53-62` (`TIMEOUT_SECONDS = 15`); local runs: `skill_progression.py` 9.4 s, `quest_rewards.py` 9.8 s.
Consequence: this brief's rules start a new check, `rank_trials.py`; no rule is added to those two.

### R-20 — module sizes and function lengths [M] (the modules this brief edits)
`writes/characters.py` 5/250 (`write_skill_progress` 58); `skill_ranks.py` 6/111; `skill_access.py` 7/116; `cockpit/crud/skills.py` 24/667; `cockpit/skill_progress.py` 4/129; `writes/quest_settlement.py` 14/233; `quest_settlement_view.py` 6/106; caps 40 functions, 1000 lines, 80 lines a function.

### R-21 — which skill row [M]
Opened: `src/world_engine/skill_access.py:1-116` (`_base_row` `:45-52`: `domain` and `skill_definition_id IS NULL`; `_definition_row` `:55-58`; imports `models`, `resolution`, `skill_ranks`).
Consequence: `held_trial_target` reads its row through `_base_row`/`_definition_row` (INV-41's lookup, never a copy).

## Contracts

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

## Context

A1 makes the points come first: a rank that asks a trial is not reached by
points. This step gives the code one reading of « this rank asks a trial »
(the cascade of B1) and one reading of « ready », stops the points at a
waiting threshold in the one writer of points, makes the two roll paths and
the point reward skip a waiting skill, and lets the creator's CRUD carry the
flags. No quest gives a rank yet (C).

## Scope IN

1. `src/world_engine/skill_ranks.py` -- exactly C-02's five names, each with a one-paragraph docstring; `RankStep` gains `trial_to_next: bool = False` last; `world_ladder`'s `RankStep(...)` for a stored row passes `trial_to_next=bool(row.trial_to_next) if step.rank < MAX_RANK else False`. The functions, verbatim in their logic:
   ```python
   def trial_required(rank: int, ladder: tuple[RankStep, ...], *, system: Any = None, definition: Any = None) -> bool:
       if rank >= MAX_RANK:
           return False
       column = RANK_TRIAL_COLUMNS[rank]
       for owner in (definition, system):
           value = getattr(owner, column, None) if owner is not None else None
           if value is not None:
               return bool(value)
       return ladder[rank].trial_to_next


   def trial_target(rank: int, xp: int, ladder: tuple[RankStep, ...], *, system: Any = None,
                    definition: Any = None) -> Optional[int]:
       needed = points_to_next(rank, ladder, system=system, definition=definition)
       if needed is None or not trial_required(rank, ladder, system=system, definition=definition):
           return None
       return rank + 1 if xp >= needed else None
   ```
   `skill_trial_required(db, *, world_id, rank, skill_definition_id)` and `skill_trial_target(db, *, world_id, skill)` read `skill_owners(db, ...)` and `world_ladder(db, world_id)` once each. The module docstring gains one paragraph: TICKET-0116 (B1, A1, C1) -- whether leaving a rank asks a trial follows the points' cascade (`RANK_TRIAL_COLUMNS`, `skill_rank.trial_to_next`); a skill is ready when its points reached the threshold of such a rank (`trial_target`); reads only.
2. `src/world_engine/skill_access.py` -- `held_trial_target` (C-02), reading the row with `_base_row` when `skill_key in BASE_SKILL_DOMAINS`, else `_definition_row` (None for a falsy key); `skill_trial_target` imported from `skill_ranks`. One docstring line.
3. `src/world_engine/writes/characters.py`:
   - `SkillProgress` gains `awaiting_trial: bool = False` (last field), comment `# C1 (TICKET-0116): the points wait at a threshold whose rank asks a trial`.
   - `write_skill_progress`: import `skill_trial_required`; between `needed = threshold(rank)` and the rank-up test:
     ```python
     # C1 (TICKET-0116, BRIEF-0116-B): a rank that asks a trial is never
     # reached by points -- they stop at its threshold and the rank waits.
     awaiting = (points > 0 and needed is not None and xp >= needed
                 and skill_trial_required(db, world_id=world_id, rank=rank,
                                          skill_definition_id=skill.skill_definition_id))
     if awaiting:
         xp = needed if xp_before < needed else xp_before
     elif points > 0 and needed is not None and xp >= needed:
         rank, xp = rank + 1, 0
     elif xp < 0 and rank > 0:
     ```
     (the former `if points > 0 ...` becomes this `elif`; the loss branch is unchanged); the `return SkillProgress(...)` passes `awaiting_trial=awaiting`. Its docstring gains: « Waiting (C1): when the rank asks a trial (`skill_ranks.skill_trial_required`), a gain that reaches the threshold leaves `xp` at the threshold and the rank where it is -- the trial moves it (`write_skill_rank`). » The module docstring's `write_skill_progress` line gains « -- or stops at a threshold whose rank asks a trial (TICKET-0116) ». The function stays <= 80 lines.
4. `src/world_engine/cockpit/skill_progress.py`: `record_roll`, right after its early `return None`: `if skill_trial_target(db, world_id=world_id, skill=skill) is not None: return None` (before the mutation is built); `grant_step_roll`: its skip becomes `if skill is None or skill.rank >= MAX_RANK or skill_trial_target(db, world_id=world_id, skill=skill) is not None: return`. Import `skill_trial_target` from `..skill_ranks`. The module docstring's sentence « A skill at Maître earns nothing more » gains « -- nor does a skill whose points wait for a rank trial (TICKET-0116, C1) ».
5. `src/world_engine/writes/quest_settlement.py`, `skill_reward_points`: `if row.rank >= MAX_RANK or needed is None or skill_trial_target(db, world_id=world_id, skill=row) is not None: return None`; docstring « None at Maître, and while the skill waits for a rank trial (TICKET-0116) ». Import from `..skill_ranks`.
6. `src/world_engine/quest_settlement_view.py`, `_skill_note`: `points` not None -> the current « +N point(s) » line; else `row.rank >= MAX_RANK` -> the current « déjà Maître » line; else `f"épreuve de rang à passer en « {label} » : rien"`. Import `MAX_RANK` from `.skill_ranks`.
7. `src/world_engine/writes/config.py`, `upsert_skill_rank`: keyword `trial_to_next: bool = False`, last; before any read: a non-bool -> `ValueError(f"upsert_skill_rank: trial_to_next must be a boolean, got {trial_to_next!r}")`; `rank == MAX_RANK and trial_to_next` -> `ValueError("upsert_skill_rank: the top rank has no trial")`; both the created and the updated row get `trial_to_next`. Docstring: « `trial_to_next`: leaving this rank asks a trial (TICKET-0116, B1); never at the top rank. »
8. `src/world_engine/cockpit/crud/skills.py` -- C-04: the `skill_ranks` import gains `RANK_TRIAL_COLUMNS, trial_target`; `_rank_step_dict` adds `"trial_to_next": step.trial_to_next`; `SkillRankStepBody.trial_to_next: bool = False`; `update_skill_ranks` passes `trial_to_next=step.trial_to_next`; `RankPointsBody` gains the five `trial_to_rank_<n>: Optional[bool] = None` and its docstring a sentence (« and the five optional trials, None to inherit (TICKET-0116) »); `_rank_points` and `_set_rank_points` iterate `RANK_POINTS_COLUMNS + RANK_TRIAL_COLUMNS`; `_skill_dict` adds `"trial_ready"` (C-04). The word `tier` appears nowhere (A4).
9. `tooling/verify/checks/rank_trials.py` (new; `rules/verify-checks.md`; `quest_requests.py`'s `_fresh_db()` idiom, `FAILURES`, `fail()`; `main()` runs the rule groups in order and prints one `PASS:` line). Its docstring opens « G1 check for TICKET-0116 -- a rank that asks a trial is earned by a quest. » and states that each brief of the lot adds its rules here in the same commit (the `quest_rewards.py` precedent). This brief's rules:
   - **TB1** -- the cascade (fixture). A world with no `skill_rank` row: `world_ladder` gives `trial_to_next` False at every rank. `upsert_skill_rank(rank=3, trial_to_next=True)` -> `world_ladder(...)[3].trial_to_next` True; `trial_required(3, ladder)` True; with a system whose `trial_to_rank_4` is False, False; with a definition of that system whose `trial_to_rank_4` is True, True; `trial_required(5, ...)` False. With the default points (40 to leave rank 3): `trial_target(3, 39, ...)` None, `trial_target(3, 40, ...)` 4. `upsert_skill_rank(rank=5, trial_to_next=True)` and `trial_to_next="yes"` raise `ValueError`, no row written. `held_trial_target` of a character with no row for the key is None.
   - **TB2** -- the CRUD (fixture; the route functions called with the session, `skill_progression.py`'s C1/C2 precedent). `update_skill_ranks` with rank 3 `trial_to_next` True serves it; with rank 5 `trial_to_next` True -> 422 and no `skill_rank` row written. `create_skill_system` with `trial_to_rank_4=False` serves it; `update_skill_system` without it serves None. The same for `create_skill_definition` / `update_skill_definition`. `list_skills` serves `trial_ready` True for a waiting row, False for another.
   - **TB3** -- the waiting threshold (fixture; a world whose rank 1 asks a trial -- 10 points to leave it --, a player character). A base `agility` row at rank 1, 9 points: `write_skill_progress(+1)` -> rank 1, 10 points, `awaiting_trial` True, no `change_history` entry; `+1` again -> rank 1, 10 points, `awaiting_trial` True; `-1` -> rank 1, 9 points, `awaiting_trial` False. In a second world with no trial, the same row at 9 points `+1` -> rank 2, 0 points. The waiting row: `record_roll` returns None and no `skill_progress` mutation is written; `grant_step_roll` for an `agility` step leaves it at 10; `skill_reward_points` is None; `quest_settlement_view._skill_note(db, SimpleNamespace(character_id=<the character>, world_id=<the world>), SimpleNamespace(skill_key="agility"))` reads « épreuve de rang à passer en « agility » : rien » (a Maître row still reads « déjà Maître en « agility » : rien »).
10. `tooling/standards/ARCHITECTURE_DECISIONS.md`, above the footer, header verbatim `## THE POINTS COME FIRST; A RANK THAT ASKS A TRIAL WAITS (TICKET-0116) -- skill_ranks.trial_required, trial_target, held_trial_target (BRIEF-0116-b, no schema change)`; body: A1, B1 (one cascade, `RANK_TRIAL_COLUMNS`), C1 (in the one writer of points, so every caller stops; the rolls and the point reward skip a waiting skill like a Maître; the creator's own rank edit passes over it, I1), « ready » defined once (`trial_target`) and read everywhere. Then `gen_decisions_index.py`, `gen_file_map.py`.

## Scope OUT

- The `rank` currency and its application (C); the trial gate on acceptance (C); INV-64 (C, once both halves exist).
- Opening a request when a skill becomes ready (D): `write_skill_progress` here only returns `awaiting_trial`.
- The day's account (`routes/day._account_gains`) -- unchanged (lot drafting decision 11).
- Any frontend file (F).
- Raising the rank anywhere but `write_skill_rank` (the creator's edit) -- the trial's rise is C's, through it.
- Any rule added to `skill_progression.py` or `quest_rewards.py` (R-19).

## Invariants to defend

- **INV-15** -- `skill_progress` stays the one auto-applied mutation; a waiting skill writes none (`record_roll` returns before building it).
- **INV-41** -- a base-domain lookup filters `skill_definition_id IS NULL`: `held_trial_target` reads through `_base_row`/`_definition_row`, never its own query.
- **INV-08** -- `write_skill_progress` and `upsert_skill_rank` stay the write sites of `skill` and `skill_rank`; nothing else writes them.
- **History is sacred** -- a waiting gain moves no rank and writes no history entry; a rank move still appends one.

## Decision rights

STOP:
- an anchor does not hold;
- an existing check other than those named in Done means goes red, in particular `skill_progression.py` B1-B3 (the default ladder must behave byte for byte as today);
- `write_skill_progress` cannot stay <= 80 lines without changing its loss branch.
ADAPT:
- `cockpit/crud/skills.py` already imports a name C-02 adds: keep one import; report.
REPORT-ONLY:
- a reader of `RankStep` outside R-01's enumeration constructing it positionally (none found): report it.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/rank_trials.py` -> `PASS` (TB1-TB3).
- [ ] Named mutations, each red then reverted: `trial_required` reading the system before the definition -> TB1 red; the `awaiting` branch removed from `write_skill_progress` -> TB3 red; `record_roll`'s new return removed -> TB3 red (a mutation is written); `upsert_skill_rank`'s rank-5 refusal removed -> TB1 red; `_set_rank_points` iterating `RANK_POINTS_COLUMNS` alone -> TB2 red.
- [ ] `skill_progression.py`, `npc_skills.py`, `quest_rewards.py`, `skill_system_shape.py`, `single_canon_write.py`, `module_budget.py`, `function_length.py`, `file_map.py`, `decisions_index.py` -> `PASS`.
- [ ] `python tooling/verify/checks/corpus_gate.py` -> `PASS`.
- [ ] `/review-step` then `/close-step` on the commit.

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md` (item 10); `DECISIONS_INDEX.md`, `FILE_MAP.md` regenerated.
- No schema change.
