<!-- slug: rank-reward -->
# BRIEF 0116-C — "The rank currency: a reward only, given to who is ready, at « déclarer accomplie »"

Lot: LOT-0116-rank-trials.md (authoritative on conflict)
Depends on: BRIEF-0116-A (the CHECKs), BRIEF-0116-B (`held_trial_target`, `skill_trial_target`)

## Anchors to confirm (Mini-RECON)

Halt if any has moved.

- `src/world_engine/models/quests.py:116` -> `QUEST_TERM_CURRENCIES` of five; `QUEST_TERM_CURRENCY_CHECK` names `'rank'` (A landed).
- `src/world_engine/skill_ranks.py` -> `skill_trial_target`; `src/world_engine/skill_access.py` -> `held_trial_target` (B landed).
- `src/world_engine/writes/quest_terms.py:42-49` -> `PERSONAL_CURRENCIES`, `COUNTED_CURRENCIES`, `MAX_RELATION_AMOUNT`, `FACT_REWARD_LEVELS`; `:118-133` `clean_term` (direction, currency, counterparty, personal, then `_clean_target` and `_clean_amount`).
- `src/world_engine/writes/quest_settlement.py:180-203` -> `apply_term`'s branches `money`, `item`, `relation`, `fact`, `elif cost:`, `else:`; `:47-50` imports `held_rank, skill_label` from `..skill_access` and `write_skill_progress, write_skill_row` from `.characters`.
- `src/world_engine/writes/debt_sources.py:62-65` -> `rows = [TermSpec(...) for columns in clean_terms(...)]`, then `cost_checks`.
- `src/world_engine/quest_value.py:54-65` -> `term_value` falls through to the item formula.
- `src/world_engine/quest_wording.py:31-48` -> `term_line` ends on the skill wording.
- `src/world_engine/quest_settlement_view.py:45-50` -> `_terms` notes only a `skill` reward.
- `src/world_engine/writes/quests.py:180-200` -> `acceptance_refusal`: closed, taken (L1), open (L1), then the eligibility.
- `src/world_engine/quest_reads.py:132-177` -> `editor_choices` without a `ranks` key.
- `src/world_engine/quest_designer.py:206-236` -> `_term`'s branches end `else: return None, f"Une monnaie inconnue ({currency}) : ..."`.
- `frontend/src/creation/questTerms.js:11-17` -> five `CURRENCY_FORMS` lines of the RD1 shape; `:36-48` `termBody`.
- `frontend/src/creation/QuestTermRow.svelte:33-60` -> one currency select over every form, the target picker, the amount when counted, the fact level, the counterparty select.
- `.claude/rules/skills.md` -> 2,221 characters, `paths:` two entries, INV-41 to INV-46.
- `tooling/verify/canon_write_policy.txt:68` -> the settlement comment naming `write_skill_row, write_skill_progress and write_agenda_status`.

## Facts carried

### R-06 — the term vocabulary [M]
Opened: `src/world_engine/models/quests.py:111-184`, `:290-308` (`DebtTerm`, CHECK `ck_debt_term_currency` `currency IN ('money','item','fact','skill')`, its own literal); `src/world_engine/writes/quest_terms.py:42-138`, `:158-162` (`copy_terms_to_quest`); `src/world_engine/cockpit/quest_offer_save.py:47-55` (`TermBody`, free `currency: str`), `:79` (`term_spec`).
Finding: both term tables carry the same three CHECK texts, built from the three module literals; the currency CHECK is a literal, not derived from the tuple; `clean_term` refuses a currency outside the tuple before any write; `copy_terms_to_quest` copies every `TERM_COLUMNS` column, so a `rank` term reaches the quest's own copy (B1 of 0109) with no change. A debt's terms have their own CHECK: a `rank` can never be owed.
Consequence: C widens the tuple and gives `clean_term` the rank's rules -- the tuple and its mirror `questTerms.js` move together here (R-15).

### R-07 — settling a quest, and a service [M]
Opened: `src/world_engine/writes/quest_settlement.py:1-63`, `:71-84`, `:164-203`, `:206-233`; `src/world_engine/quest_settlement_view.py:36-50`; `src/world_engine/writes/debt_sources.py:46-72`.
Finding: `apply_term` branches money, item, relation, fact, then `elif cost:` (teaching) and `else:` (`_skill_reward`) -- any other currency falls into the skill branches. Rewards are never checked before settlement (C-src1). `request_service` validates its terms with `clean_terms` and applies them with `apply_term`, as a settlement does.
Enumeration: three callers of `apply_term` -- `request_service`, `settle_quest_on_credit`, `settle_quest`.
Consequence: `apply_term` gains an explicit `rank` branch before the skill branches; `request_service` refuses a `rank` term before any write (D2-a); both settlement paths give the rank.

### R-08 — a term's value and its words [M]
Opened: `src/world_engine/quest_value.py:54-65`, `src/world_engine/quest_wording.py:31-58`.
Finding: `term_value` falls through to the item formula for any currency it does not name; `term_line` ends on the skill wording. `QuestOfferTerm` and `QuestTerm` carry `world_id`.
Consequence: `rank` gets an explicit 0 and its own line.

### R-09 — offering, accepting, and the editor's choices [M]
Opened: `src/world_engine/writes/quests.py:1-56`, `:174-232`; `src/world_engine/quest_reads.py:132-177`, `:190-195`, `:240-262`.
Finding: `acceptance_refusal(db, offer, character)` judges a closed offer, L1, then the eligibility; `accept_quest` raises its reason before any write; `available_offers` lists the open offers whose `acceptance_refusal` is None -- the one judge for both. `editor_choices` serves `skills` as `{key, label}` and no ladder.
Enumeration: two callers of `acceptance_refusal` -- `accept_quest`, `available_offers`.
Consequence: the trial gate is one more refusal in `acceptance_refusal`, after L1 and before the eligibility.

### R-15 — the term editor [M]
Opened: `frontend/src/creation/questTerms.js:1-48`; `frontend/src/creation/QuestTermRow.svelte:1-67`; `frontend/src/creation/OfferEditor.svelte:109-118`; `frontend/src/creation/questOffers.svelte.js:67-73`, `:185-199`.
Finding: a term row picks its currency among every `CURRENCY_FORMS` entry, its target from the form's `list`, its amount when `counted`, its counterparty always; `termBody` sends `skill_key` only for `skill`, `amount` only when `counted`.
Consequence: the `rank` form is one more line of the exact RD1 shape, reward-only through a separate constant; the row adds a rank picker and hides the counterparty for it.

### R-17 — the existing checks (the lines this brief needs) [M]
- `quest_rewards.py:959-976` (RD1: `CURRENCY_FORMS` lines matched by `^  (\w+): \{ label: '[^']*', list: [^,]+, (counted: \w+, personal: \w+) \},$`, keys == `QUEST_TERM_CURRENCIES` in order; `counted: true` == `COUNTED_CURRENCIES`, `personal: true` == `PERSONAL_CURRENCIES`); RC3 (« +4 point(s) », « apprend »).
- `event_conditions.py:342-345` (EE5: only `quest_reads.py` and `writes/quests.py` contain `role="failure"`).
- `quests.py:760-764` (QB4: no dict literal with `agenda_id`/`step_id` in `quest_reads.py`).

### R-18 — the standing law [M]
Opened: `CLAUDE.md` (20,448 characters, budget 22,000), INV-15; `.claude/rules/skills.md` (2,221 characters, budget 4,000; `paths:` `src/world_engine/skill*.py`, `src/world_engine/cockpit/crud/skills.py`; INV-41 to INV-46); `invariant_ids.retired`; `checks/claude_md_contract.py:77-78`; highest live id INV-63.
Consequence: INV-15 is untouched; INV-64 goes to `skills.md`, whose `paths:` gain the three writers it names.

### R-20 — module sizes [M] (the modules this brief edits)
`writes/quest_terms.py` 10/187; `writes/quest_settlement.py` 14/233; `writes/quests.py` 10/264; `writes/debt_sources.py` 4/158; `quest_value.py` 4/86; `quest_wording.py` 4/58; `quest_reads.py` 14/276 (`editor_choices` 46 lines); `quest_settlement_view.py` 6/106; `quest_designer.py` 20/361.

## Contracts

### C-02 — the trial cascade and « ready » (consumed)
- `skill_ranks.skill_trial_target(db, *, world_id, skill) -> Optional[int]`; `skill_access.held_trial_target(db, *, world_id, character_id, skill_key) -> Optional[int]` -- the rank a trial would give the character's row for `skill_key`, None when it does not wait (or there is no row). **« Ready for n » means `held_trial_target(...) == n`.**

### C-05 — the `rank` currency
Produced by: BRIEF-0116-C   Consumed by: E, F
- `QUEST_TERM_CURRENCIES = ("money", "item", "relation", "fact", "skill", "rank")`; its comment « The six currencies of a quest ».
- `writes/quest_terms.py`: `REWARD_ONLY_CURRENCIES: tuple[str, ...] = ("rank",)`; `COUNTED_CURRENCIES`, `PERSONAL_CURRENCIES` unchanged. `clean_term` sends a `rank` term to `_clean_rank(db, world_id, where, term) -> dict`, which returns `{"direction": "reward", "currency": "rank", "counterparty_entity_id": None, "item_id": None, "fact_id": None, "skill_key": <key>, "amount": <rank>, "level": None}` or raises, in this order: `direction == "cost"` -> `f"{where}: a rank is a reward only -- a rank trial gives it"`; a counterparty -> `f"{where}: a rank reward names no counterparty"`; `skill_key` neither a base domain nor a definition of the world -> `f"{where}: {term.skill_key!r} is not a skill of this world"`; `amount` not an int 1-5 (a bool refused) -> `f"{where}: a rank reward names the rank it gives, 1 to 5"`.
- `request_service` raises `ValueError("request_service: a rank is given by a rank trial, never by a service")` when a cleaned term's currency is in `REWARD_ONLY_CURRENCIES`, before any write.
- `quest_value.term_value`: `rank` -> 0.
- `quest_wording.term_line`: `rank` -> `f"Passer au rang « {label} » en « {skill} » (épreuve)"`, `label = world_ladder(db, term.world_id)[term.amount].label` when `term.amount` is in 1-5, else `str(term.amount)`; `skill = skill_label(db, term.skill_key)`.
- `quest_settlement.apply_term`: `elif term.currency == "rank": _rank_reward(db, world_id, character_id, term.skill_key, term.amount)` before `elif cost:`; `_rank_reward` writes `write_skill_rank(db, skill_id=<the row>, rank=amount, changed_by=CHANGED_BY)` when `held_trial_target(...) == amount`, else nothing (D2-c).
- `skill_reward_points`: None when `skill_trial_target(db, world_id=world_id, skill=row)` is not None (done in B).
- `quest_settlement_view`: a `rank` reward's note -- `f"passe à « {label} » en « {skill} »"` when ready for it, else `"sans effet : la compétence n'est pas prête pour ce rang"`; `_skill_note` (done in B).
- `editor_choices` gains `"ranks": [{"rank": s.rank, "label": s.label} for s in world_ladder(db, world_id) if s.rank >= 1]`.
- `quest_designer._term`: `elif currency == "rank": return None, RANK_TERM_FR` with `RANK_TERM_FR = "Un rang ne se donne que par une épreuve de rang : le terme a été abandonné."`
- `questTerms.js`: `CURRENCY_FORMS.rank` is the line `  rank: { label: 'Rang (épreuve)', list: 'skills', counted: false, personal: false },`; `export const REWARD_ONLY_CURRENCIES = ['rank'];`; `termBody` sends `skill_key` for `skill` and `rank`, `amount` for a counted currency and for `rank`, `counterparty_entity_id` null for `rank`.
- `QuestTermRow.svelte`: the currency select omits a reward-only currency on a cost; a `rank` term shows the skill picker and a rank select of `choices?.ranks`, and no counterparty select.

### C-06 — the trial gate
Produced by: BRIEF-0116-C   Consumed by: E (the offer it proposes), the player's Journée
`acceptance_refusal(db, offer, character)`, after the L1 checks and before the eligibility: for each `rank` term of `offer_terms(db, offer.id)`, when `held_trial_target(db, world_id=offer.world_id, character_id=character.id, skill_key=term.skill_key) != term.amount` -> `f"cette épreuve est réservée à qui est prêt à passer « {label} » en « {skill} »"`. `available_offers` and `accept_quest` inherit it.

## Context

D2 makes the trial's reward a sixth currency of the existing terms, so the
offer editor, the quest's own copy and « déclarer accomplie » serve a trial
unchanged. This step teaches every reader of a currency the `rank`: its
writer rules (a reward only, a skill and a rank), its value (none), its
words, its application (only to a character ready for exactly that rank),
the gate that offers it only to him, and its absence from services. After
it, Nia can write a trial by hand in Création › Quêtes.

## Scope IN

1. `src/world_engine/models/quests.py`: `QUEST_TERM_CURRENCIES = ("money", "item", "relation", "fact", "skill", "rank")`, its comment « The six currencies of a quest (the series' D table; `rank`, TICKET-0116 D2: the trial's reward). »
2. `src/world_engine/writes/quest_terms.py` -- C-05: `REWARD_ONLY_CURRENCIES` under the comment `# The currencies a term may only give (TICKET-0116, D2-a): a rank comes from a trial.`; `clean_term`, right after its currency check: `if term.currency == "rank": return _clean_rank(db, world_id, where, term)`; `_clean_rank` with C-05's four refusals in that order (the skill accepted when it is in `BASE_SKILL_DOMAINS` or a `SkillDefinition` of the world, `_clean_target`'s test). The module docstring: « in one of six currencies »; « A `rank` (TICKET-0116) is a reward only: the skill and the rank it gives, no counterparty. »
3. `src/world_engine/writes/debt_sources.py`, `request_service`: right after `rows = [...]`, the C-05 refusal (`from .quest_terms import REWARD_ONLY_CURRENCIES, ...`). Docstring of `request_service`: « A `rank` is never a service (D2-a). »
4. `src/world_engine/quest_value.py`, `term_value`: `if term.currency == "rank": return 0` before the item fallback; the module docstring: « a rank (TICKET-0116) is worth nothing: a trial is not a trade ».
5. `src/world_engine/quest_wording.py`, `term_line`: before the skill wording, `if term.currency == "rank":` C-05's line (`world_ladder` from `.skill_ranks`, read only when `term.amount` is an int 1-5 and `term.world_id` is set); the module docstring's examples gain « Passer au rang « Expert » en « Forge » (épreuve) ».
6. `src/world_engine/writes/quest_settlement.py`: `_rank_reward(db, world_id, character_id, skill_key, rank)` -- `row = skill_row(db, character_id, skill_key)`; when `row is not None and held_trial_target(db, world_id=world_id, character_id=character_id, skill_key=skill_key) == rank`: `write_skill_rank(db, skill_id=row.id, rank=rank, changed_by=CHANGED_BY)`; nothing otherwise. `apply_term`: `elif term.currency == "rank": _rank_reward(db, world_id, character_id, term.skill_key, term.amount)` placed right after the `fact` branch, before `elif cost:`. Imports: `held_trial_target` from `..skill_access`, `write_skill_rank` from `.characters`. The D table of the module docstring gains « - rank, reward (TICKET-0116, D2-b/c): a character ready for exactly that rank rises to it (`write_skill_rank`, points 0); otherwise nothing -- « sans effet ». »
7. `src/world_engine/quest_settlement_view.py`, `_terms`: a `rank` reward's note is C-05's (ready read with `held_trial_target`; label from `world_ladder(db, quest.world_id)`; skill from `skill_label`).
8. `src/world_engine/writes/quests.py`, `acceptance_refusal` -- C-06, placed after `if any(status in OPEN_QUEST_STATUSES ...)` and before the eligibility; imports `held_trial_target`, `skill_label` from `..skill_access`, `world_ladder` from `..skill_ranks`, `offer_terms` from `.quest_terms` (already imported). Its docstring: « ... L1 ..., a rank trial the character is not ready for (TICKET-0116, C-06), or an unmet eligibility requirement ». The module docstring's `accept_quest` line: « Eligibility, L1 and the trial gate are judged HERE ».
9. `src/world_engine/quest_reads.py`, `editor_choices`: the `"ranks"` key of C-05 (`world_ladder` from `.skill_ranks`), comment `# TICKET-0116 (BRIEF-0116-C): the ranks a rank reward may give.`; docstring « ... the world's ranks above Inexpérimenté (TICKET-0116) ». `role="failure"` and `agenda_id`/`step_id` dict keys are not added (EE5, QB4).
10. `src/world_engine/quest_designer.py`, `_term`: `elif currency == "rank": return None, RANK_TERM_FR` before `else:`; `RANK_TERM_FR` beside `NO_STEP_FR`. Nothing else in the designer changes here (E).
11. `src/world_engine/writes/characters.py`, `write_skill_rank`'s docstring: « Two callers: `cockpit/crud/skills.py`'s `update_skill_rank` (the creator's edit) and `writes/quest_settlement._rank_reward` (a rank trial settled, TICKET-0116). »; the module docstring's `write_skill_rank` line names both. `tooling/verify/canon_write_policy.txt:68`: the comment's list gains `write_skill_rank` (« ... write_skill_row, write_skill_progress, write_skill_rank and write_agenda_status ... »), and the line ends « TICKET-0116, BRIEF-0116-C: a rank reward goes through write_skill_rank. ». No allowed site is added.
12. `frontend/src/creation/questTerms.js` -- C-05: the header comment « The six currencies ... `REWARD_ONLY_CURRENCIES` mirrors `writes.quest_terms.REWARD_ONLY_CURRENCIES` (TICKET-0116) »; the `rank` line, last, verbatim `  rank: { label: 'Rang (épreuve)', list: 'skills', counted: false, personal: false },`; `export const REWARD_ONLY_CURRENCIES = ['rank'];` right after `CURRENCY_FORMS`; `termBody` per C-05:
    ```js
    counterparty_entity_id: REWARD_ONLY_CURRENCIES.includes(term.currency) ? null : (term.counterparty_entity_id || null),
    skill_key: term.currency === 'skill' || term.currency === 'rank' ? (term.skill_key || null) : null,
    amount: form.counted || term.currency === 'rank'
      ? (term.amount === '' || term.amount === null ? null : Number(term.amount)) : null,
    ```
13. `frontend/src/creation/QuestTermRow.svelte` -- C-05: import `REWARD_ONLY_CURRENCIES`; `let currencies = $derived(Object.entries(CURRENCY_FORMS).filter(([c]) => term.direction === 'reward' || !REWARD_ONLY_CURRENCIES.includes(c)));` and the currency select loops `currencies`; after the target picker:
    ```svelte
    {#if term.currency === 'rank'}
      <select value={term.amount ?? ''} title="Le rang que l'épreuve donne"
              onchange={(e) => set('amount', e.target.value === '' ? null : Number(e.target.value))}>
        <option value="">— rang —</option>
        {#each choices?.ranks || [] as r (r.rank)}<option value={r.rank}>{r.label}</option>{/each}
      </select>
    {/if}
    ```
    the counterparty select wrapped in `{#if !REWARD_ONLY_CURRENCIES.includes(term.currency)}` ... `{/if}`. The header comment gains « a rank (TICKET-0116): a skill and the rank it gives, a reward only, no counterparty ». Then `cd frontend; npm ci; npm run build`; the built output committed.
14. `.claude/rules/skills.md`: `paths:` gains, after the two existing entries,
    ```
      - "src/world_engine/writes/characters.py"
      - "src/world_engine/writes/quest_settlement.py"
      - "src/world_engine/writes/quests.py"
    ```
    and, after INV-46, verbatim:
    ```
    - **INV-64** A rank that asks a trial is never reached by points: `write_skill_progress`
      stops them at its threshold (`skill_ranks.trial_required`) and the rank waits. Only a
      `rank` reward settled for a character ready for exactly that rank
      (`skill_access.held_trial_target`), or the creator's own edit, moves it, both through
      `write_skill_rank`. A `rank` term is a reward only, never a service; an offer holding
      one is listed and accepted only by a character ready for it (`acceptance_refusal`).
      -- enforced by `rank_trials.py`
    ```
15. `tooling/verify/checks/rank_trials.py` -- its docstring gains, and `main()` runs after TB, these rules (INV-64's full law is TB3 with them):
    - **TC1** -- the writer (fixture). `clean_term` of a reward `rank` on `agility`, amount 2, gives exactly C-05's row; it refuses, each with C-05's message: a cost, a counterparty, the skill `flying`, amounts 0, 6, None and True. `write_quest_offer` with that reward writes it; `accept_quest` copies it to `quest_term`. `request_service` with a `rank` reward raises C-05's message and writes no `debt`, `ledger` or `skill` row (counts before and after).
    - **TC2** -- the gate (fixture: a world whose rank 1 asks a trial; an offer whose reward is `rank` agility 2; player A at agility rank 1 with 10 points -- ready --, B at rank 1 with 5, C ready in `perception` only). `available_offers(A)` holds the offer, `(B)` and `(C)` do not; `accept_quest` for B raises « cette épreuve est réservée à qui est prêt à passer « Apprenti » en « agility » », nothing written; for A it accepts.
    - **TC3** -- the settlement (fixture, continued). Before settling, `settlement_context` gives A's `rank` term the note « passe à « Apprenti » en « agility » » and the line « Passer au rang « Apprenti » en « agility » (épreuve) »; `settle_quest` -> A's agility at rank 2, 0 points, the last `change_history` entry `by` `quest_settlement`. D, ready like A, accepts; the creator sets D's agility to rank 2 (`write_skill_rank`); D's note reads « sans effet : la compétence n'est pas prête pour ce rang »; `settle_quest` succeeds and D stays at rank 2 with one history entry (the creator's). `term_value` of a `rank` term is 0; `editor_choices(world)["ranks"]` lists ranks 1-5 with the world's labels; `quest_designer._term(db, world_id, None, {"direction": "reward", "currency": "rank", "target": "s1", "amount": 2, "level": None})` returns `(None, RANK_TERM_FR)`.
    - **TC4** -- static. `QUEST_TERM_CURRENCIES[-1] == "rank"`; `questTerms.js` holds the `rank` line verbatim and `export const REWARD_ONLY_CURRENCIES = ['rank'];`; `QuestTermRow.svelte` names `REWARD_ONLY_CURRENCIES` and `choices?.ranks`; the built bundle (`src/world_engine/cockpit/static/assets/*.js`) carries « Rang (épreuve) »; `.claude/rules/skills.md` holds INV-64 ending « -- enforced by `rank_trials.py` » and the three new `paths:`.
16. `tooling/standards/ARCHITECTURE_DECISIONS.md`, above the footer, header verbatim `## A RANK IS A REWARD THE READY CHARACTER RECEIVES (TICKET-0116) -- THE rank CURRENCY, THE TRIAL GATE, INV-64 (BRIEF-0116-c, no schema change)`; body: D2, D2-a/b/c, the gate in `acceptance_refusal` (one judge for listing and accepting; not a removable leaf, D3), the rank worth nothing in the indicative unit, a rank is never a service and never owed (`debt_term`'s own CHECK), `write_skill_rank` as the one mover besides the points. Then `gen_decisions_index.py`, `gen_file_map.py`.

## Scope OUT

- Opening a request when a skill becomes ready (D); the designer's trial path, its prompt and the applier's refusal (E).
- A rank as a cost, a debt or a service (D2-a: refused); a counterparty for a rank (C-05: refused).
- Warning the creator in the editor that a point reward gives nothing to a waiting skill (« le silence me convient »).
- Any change to `debt_term`, `DEBT_CURRENCIES` or `debtTerms.js`.
- Any frontend file besides `questTerms.js` and `QuestTermRow.svelte` (F).
- A trial over a system (E2, deferred); a failed trial costing anything (H2, deferred).

## Invariants to defend

- **INV-64** (new) -- this brief establishes it; TC1-TC3 with TB3 enforce it.
- **INV-08** -- `write_skill_rank` stays the write site; `_rank_reward` only calls it, on the settlement's creator-CRUD path.
- **INV-62** -- a player surface shows a condition only as its character may know it: the trial gate is a refusal sentence, never a condition leaf; the term line names the skill and the rank only.
- **INV-13** -- a rank moves no money: no ledger line is written for a `rank` term.

## Decision rights

STOP:
- an anchor does not hold;
- `quest_rewards.py` RD1 cannot match the `rank` line in its exact shape;
- an existing check of the settlement (`quest_rewards.py` RC1-RC3, `debts.py`) goes red;
- `.claude/rules/skills.md` would exceed 4,000 characters, or `claude_md_contract.py` refuses INV-64's form.
ADAPT:
- `npm ci` changes `package-lock.json`: commit only the built output and the two sources; restore the lock file; report.
REPORT-ONLY:
- another reader of a currency list outside R-06/R-07/R-08/R-09's enumerations (none found).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/rank_trials.py` -> `PASS` (TB1-TB3, TC1-TC4).
- [ ] Named mutations, each red then reverted: `_clean_rank` accepting a cost -> TC1 red; `request_service`'s refusal removed -> TC1 red; the gate removed from `acceptance_refusal` -> TC2 red; `_rank_reward` writing without the readiness test -> TC3 red (D rises to 3); the `rank` line of `term_line` removed -> TC3 red; `REWARD_ONLY_CURRENCIES` removed from `questTerms.js` -> TC4 red.
- [ ] `quest_rewards.py` (RA1, RD1-RD3, RC1-RC3), `debts.py`, `quests.py`, `event_conditions.py`, `quest_designer.py`, `claude_md_contract.py`, `single_canon_write.py`, `frontend_build_fresh.py`, `module_budget.py`, `function_length.py` -> `PASS`.
- [ ] `python tooling/verify/checks/corpus_gate.py` -> `PASS`.
- [ ] `/review-step` then `/close-step` on the commit.

## Docs to update

- `.claude/rules/skills.md` (item 14).
- `tooling/standards/ARCHITECTURE_DECISIONS.md` (item 16); `DECISIONS_INDEX.md`, `FILE_MAP.md` regenerated.
- No schema change.
