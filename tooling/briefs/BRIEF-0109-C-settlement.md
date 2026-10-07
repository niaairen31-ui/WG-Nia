# BRIEF 0109-C — "« Déclarer accomplie » settles a quest at once, after its measured context"

Lot: LOT-0109-quest-terms.md (authoritative on conflict)
Depends on: BRIEF-0109-B

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0109-B's commit). The facts carried below quote `main`'s line
numbers, as the lot does; where A or B moved a line, the anchor here gives where it now is.

- `src/world_engine/quest_reads.py:127` -> `def _steps_view(agenda: Agenda, character: Character, db: Session) -> list[dict]:`; `:141` -> `def player_quests(character: Character, db: Session) -> list[dict]:`; the file is 183 lines.
- `src/world_engine/cockpit/routes/quests.py:175` -> `@router.get("/api/quests")`; the file is 210 lines.
- `src/world_engine/writes/quest_terms.py:151` -> `def quest_terms(db: Session, quest_id: str) -> list[QuestTerm]:`.
- `src/world_engine/quest_value.py:64` -> `def offer_value(db: Session, world_id: str, terms: list) -> OfferValue:`.
- `src/world_engine/quest_wording.py:31` -> `def term_line(db: Session, term, giver_entity_id: str) -> str:`.
- `src/world_engine/skill_access.py:94` -> `def skill_label(db: Session, skill_key: Optional[str]) -> str:`.
- `tooling/verify/checks/quest_rewards.py:635` -> `    check_rb(engine)`.
- No `src/world_engine/writes/quest_settlement.py` or `quest_settlement_view.py` exists.

## Facts carried

### R-08 — money [M]
Opened: `src/world_engine/writes/characters.py:213-247`
(`write_ledger_entry`: INSERT only, no balance guard, `amount != 0`);
`src/world_engine/ledger.py:18-23` (`get_balance`);
`world-engine-schema.md:863` (`source_type` vocabulary documented, not
CHECKed); `src/world_engine/cockpit/crud/ledger.py:86` (creator types).
Consequence: a money term is two ledger lines, `source_type` `quest`; a
counterparty may go below 0 (C-src1).

### R-09 — relation [M]
Opened: `src/world_engine/writes/relations.py:267-288`
(`_build_relation_delta`: a social type finds the perceiver's own row,
`_find_perceived_relation`; a missing row is created at `50 + value`;
clamped 1-100), `:322-395` (`write_relation`).
Consequence: a relation term moves what the counterparty feels toward the
character (B-dir of 0108), type `other` on a new row.

### R-10 — fact [M]
Opened: `src/world_engine/writes/knowledge.py:65-67` (`KNOWLEDGE_LEVELS`),
`:180-238` (`_build_knowledge_update`: a create on a `fact_id` attaches to
the fact; `content` may be None); `src/world_engine/models/
canon_knowledge.py:216-221` (`content` nullable);
`src/world_engine/fact_refs.py:57-67` (`find_held` on a `fact_id`).
Consequence: a fact term writes a row only when the receiver holds none --
a level never falls.

### R-11 — skills [M]
Opened: `src/world_engine/writes/characters.py:105-150`
(`write_skill_row`: refuses a row already held), `:153-210`
(`write_skill_progress`: at the threshold the rank rises and `xp` restarts
at 0 -- `:187`, the surplus is not carried; at `MAX_RANK` points still
accumulate); `src/world_engine/skill_ranks.py:30` (`MAX_RANK = 5`), `:39`
(`DEFAULT_POINTS_TO_NEXT = (5, 10, 20, 40, 80)`), `:108-111`;
`src/world_engine/skill_access.py:82-92` (`held_rank`);
`src/world_engine/cockpit/crud/skills.py:227-258` (teaching from a Maître);
`src/world_engine/day_plan.py:296-300` (`_skill_label`, private).
Consequence: C-skill1 is `ceil(10 % of points_to_next)`, at least 1, through
`write_skill_progress` (no carry by construction); nothing at Maître;
`skill_label` moves to `skill_access` for a second reader.

### R-12 — what completes a quest today [M]
Opened: `src/world_engine/cockpit/mutations.py:828-887` (the last step's
change approved writes the agenda `completed` at `:884`; nothing else).
Finding: no column records that a quest's terms were applied.
Consequence: `quest.settled_at`; D1 completes the agenda when it is not.

### R-13 — the 0108 writers and views [M]
Opened: `src/world_engine/writes/quests.py:88-139` (`write_quest_offer`,
full-replace `:118-120`), `:172-198` (`accept_quest`);
`src/world_engine/quest_reads.py:57-71` (`offer_dict`), `:85-104`
(`editor_choices`), `:115-127` (`_steps_view`), `:129-147`
(`player_quests`), `:149-158` (`journee_payload`);
`src/world_engine/cockpit/routes/quests.py:52-60` (`OfferBody`), `:75`
(the one caller of `write_quest_offer` in `src/`).

### R-14 — the days that advanced a quest [M]
Opened: `src/world_engine/models/pipeline.py:74-80` (`pass_play.agenda_id`,
written once at plan time), `:160-172` (`day_rewrite`);
`src/world_engine/writes/pipeline.py:128-150` (`read_latest_resolution`);
`src/world_engine/day_resolve.py:444-464` (`fact_sheet_dict`: steps with
`objective` and `band`).
Consequence: G1's days are the pass_plays whose `agenda_id` is the quest's.

### R-15 — awaiting review [M]
Opened: `src/world_engine/cockpit/routes/day.py:741-773`
(`agenda_step_change`, `status == "proposed"`, the payload's `step_id`).

### R-19 — budgets [M]
Opened: `tooling/verify/checks/module_budget.py:57-58` (40/1000 per `src/`
module), `tooling/verify/checks/function_length.py:29` (80).
Consequence: four new modules (`holdings.py`, `writes/items.py`,
`writes/quest_terms.py`, `writes/quest_settlement.py`) and three reads
(`quest_value.py`, `quest_wording.py`, `quest_settlement_view.py`); none
over budget.

## Contracts

### C-02 — holdings
Produced by: BRIEF-0109-A   Consumed by: C
- `writes.write_holding(db, *, world_id, item_id, holder_entity_id,
  quantity=None, delta=None, changed_by) -> ItemHolding`: case table (b-1).
- `holdings.held_quantity(db, holder, item) -> int` (0 when none);
  `items_held(db, holder) -> [(ItemHolding, Item, Entity)]` and
  `holders_of(db, item) -> [(ItemHolding, Entity)]`, `quantity > 0`, by
  name; `held_label(name, n)` -> « name » or « name ×n ».
- Routes (creator CRUD, `crud/items.py`): `GET /api/items/{id}/holders`
  -> `[{id, name, type, quantity}]`; `PUT /api/item-holdings {item_id,
  holder_entity_id, quantity}` -> 200, 422 on a refusal.
  `GET /api/entities/{id}/items` -> `[{id, name, quantity, condition,
  value}]`.

### C-03 — the currencies (family contract)
Produced by: BRIEF-0109-B   Consumed by: C, D
Written before its members; re-read after the last (`skill`).

`QUEST_TERM_DIRECTIONS = ("cost", "reward")`; `QUEST_TERM_CURRENCIES =
("money", "item", "relation", "fact", "skill")`; `COUNTED_CURRENCIES =
("money", "item", "relation")`; `PERSONAL_CURRENCIES = ("relation", "fact",
"skill")`; `FACT_REWARD_LEVELS` = `KNOWLEDGE_LEVELS` minus `unaware`,
sorted. The counterparty is the term's own entity (an active character or
faction of the world), else the offer's giver.

| currency | target | amount | counterparty | `clean_term` refuses | unit (default) |
|---|---|---|---|---|---|
| `money` | -- | >= 1 | character or faction | amount < 1 | 1 a coin |
| `item` | `item_id` (an item of the world) | >= 1 | character or faction | not an item; amount < 1 | the item's `value` a piece |
| `relation` | -- | 1-99 | a character | amount < 1 or > 99; a faction | 1 a point |
| `fact` | `fact_id` (a fact of the world); reward `level` in `FACT_REWARD_LEVELS` or None | -- | a character | a fact elsewhere; level `unaware`; a faction | 5 |
| `skill` | `skill_key`: cost a skill definition of the world; reward a definition or a base domain | -- | a character | a cost on a base domain; an unknown skill; a faction | 20 |

Every term also refuses a direction or a currency outside the vocabulary
and a counterparty that is not an active character or faction of the world.

### C-04 — the indicative unit
Produced by: BRIEF-0109-B   Consumed by: C, D
`quest_value.DEFAULT_RATES = {rate_money: 1, rate_relation: 1, rate_fact:
5, rate_skill: 20, band_low_pct: 100, band_high_pct: 150}`;
`world_rates(db, world_id)` (a NULL column or no row -> the default);
`term_value(db, term, rates)` (C-03's last column); `offer_value(db,
world_id, terms) -> OfferValue(cost, reward, ratio_pct, band_low_pct,
band_high_pct, verdict)`, `ratio_pct = round(reward * 100 / cost)`; verdict
case table (b-3); `value_dict` adds `verdict_label` (« sans coût »,
« maigre », « équilibrée », « généreuse »).
`writes.upsert_quest_economy(db, *, world_id, values)`: refuses an unknown
column, a value that is not a whole number >= 0, and an effective band
whose low end is above its high end, before any write; None returns a rate
to its default.
`quest_wording.term_line(db, term, giver_id)`: one French line per term
(« Donner 2 × Fourrure de loup à Garde », « La relation de Garde envers
vous monte de 5 », ...).

### C-05 — settlement
Produced by: BRIEF-0109-C   Consumed by: D (through C-07)
`writes.settlement_refusals(db, quest) -> list[str]` (French) and
`writes.settle_quest(db, *, quest) -> Quest`: refusals case table (b-4),
application table (b-5). Order: every cost (term order), then every reward
(term order); then the agenda `completed` through `write_agenda_status`
when it is not already; then `settled_at = now`. All in the caller's
transaction; any refusal raises `ValueError(joined)` before the first
write. `SKILL_REWARD_SHARE = 0.10`, `LEARNED_RANK = 0`,
`DEFAULT_FACT_LEVEL = "knows"`, `changed_by = "quest_settlement"`.

### C-06 — the measured context (G1)
Produced by: BRIEF-0109-C   Consumed by: D
`quest_settlement_view.settlement_context(db, quest) -> {quest_id, title,
state, settled, steps: [{order, objective, status, outcome, blocked}],
terms: [{direction, line, note}], value, days: [{day_number,
declared_action, rewritten, steps: [{objective, band}]}], pending_reviews,
refusals, can_settle}`. `note` only on a skill reward: « +N point(s) en
« label » », « apprend « label » (Inexpérimenté) », or « déjà Maître en
« label » : rien ». No model call; no `agenda_id`/`step_id`.

### C-07 — routes
Produced by: B and C   Consumed by: D

| route | body | success | refusal |
|---|---|---|---|
| `POST /api/quest-offers`, `PUT /api/quest-offers/{id}` | `OfferBody` + `terms: [TermBody] | null` (null keeps) | `offer_dict` + `terms: [term + line]`, `value` | 422 |
| `POST /api/quest-offers/value` | `{terms: [TermBody]}` | `value_dict` | -- |
| `GET /api/quest-economy` | -- | `{stored, effective, defaults}` | 400 |
| `PUT /api/quest-economy` | the six columns | same as GET | 422 |
| `GET /api/quest-offers/choices` | -- | + `items: [{id, name, value}]`, `fact_levels`, `rates` | 400 |
| `GET /api/quests/{quest_id}/settlement` | -- | C-06 | 404 not his |
| `POST /api/quests/{quest_id}/settle` | -- | `journee_payload` | 404, 409 refusal |

`journee_payload`: each offer gains `terms: [line]`; each quest gains
`terms: [line]`, `settled`, `settleable` (`settled_at` NULL and agenda
`active`/`paused`/`completed`); each step gains `outcome`.

## Case tables carried (lot, gate output (b))

**b-1 — `write_holding`**, checked in this order:

| input | result |
|---|---|
| both or neither of `quantity`/`delta` | `ValueError` |
| `quantity`/`delta` not an integer | `ValueError` |
| item not an item of the world | `ValueError` |
| holder not an active entity of the world | `ValueError` |
| holder a location that is a zone, and the quantity grows | `ValueError` (the zone message) |
| holder a zone, and the quantity falls | accepted |
| result below 0 | `ValueError` |
| otherwise | the row (created at 0 when absent), previous quantity appended to `change_history` |

**b-4 — `settlement_refusals`**, in order (the first two end the list):

| condition | reason |
|---|---|
| `settled_at` set | « cette quête est déjà réglée » |
| agenda missing, `failed` or `abandoned` | « cette quête est terminée sans succès » |
| a fact cost the character does not know | « il faut connaître le fait à transmettre » |
| a skill cost he is not at Maître in | « il faut être Maître en « label » pour l'enseigner » |
| a skill cost the counterparty holds | « X connaît déjà « label » » |
| the money costs exceed his balance | « il faut N pièce(s), vous en avez M » |
| an item's costs (summed) exceed what he holds | « il faut N × item, vous en avez M » |

**b-5 — what each term writes** (X = the counterparty, C = the character):

| currency | cost | reward |
|---|---|---|
| money | ledger C -n (counterparty X), X +n (counterparty C) | ledger X -n, C +n |
| item | holding C -n, X +n | X -min(n, held), C +n |
| relation | X's row toward C: -n | +n |
| fact | X learns it (`knows`) unless X holds a row | C learns it (`level` or `knows`) unless C holds a row |
| skill | X's row at rank 0, `taught_by` C | held: + max(1, ceil(10 % x points_to_next)), none at Maître; base domain not held: row at `held_rank` then points; definition not held: row at rank 0, `taught_by` X when X is Maître, else none |

## Context

Terms exist (B). This brief applies them (D1): « déclarer accomplie » first shows the measured context of a quest -- its steps and outcomes, the days that advanced it, any step change awaiting review, the terms and their value -- with no model opinion (G1); then, when every cost can be paid, it applies every cost, then every reward, at once, completes the agenda if it is not, and marks the quest settled. A reward is always given (C-src1); a skill reward is 10 % of the next rank's points (C-skill1); teaching needs a Maître (C-teach1). There is no « déclarer échouée » (D-fail2).

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. The generated `tooling/standards/DECISIONS_INDEX.md`
is not in the diff: regenerate it as listed.

1. Apply the embedded diff. It:
   - creates `src/world_engine/writes/quest_settlement.py` (`SKILL_REWARD_SHARE = 0.10`, `LEARNED_RANK = 0`, `DEFAULT_FACT_LEVEL = "knows"`, `skill_row`, `skill_reward_points`, `settlement_refusals` (b-4), `settle_quest` (b-5) -- C-05), exported by `writes`; allow-lists `settle_quest` in `canon_write_policy.txt`;
   - creates `src/world_engine/quest_settlement_view.py` (`settlement_context`, C-06), reusing `quest_reads`' state labels and steps view;
   - `quest_reads.py`: each step gains `outcome`; each quest gains `terms`, `settled`, `settleable` (C-07);
   - `routes/quests.py`: `GET /api/quests/{quest_id}/settlement` and `POST /api/quests/{quest_id}/settle` (404 when the quest is not the player's, 409 on a refusal; 239 lines after);
   - documents `quest` as a ledger `source_type` in the schema doc (no schema change);
   - adds RC1-RC3 to `quest_rewards.py`;
   - appends the decision entry above the footer.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(quests): « déclarer accomplie » settles a quest's terms at once, after its measured context (BRIEF-0109-c)`.

````diff
diff --git a/src/world_engine/cockpit/routes/quests.py b/src/world_engine/cockpit/routes/quests.py
index cd3c919..c2d104c 100644
--- a/src/world_engine/cockpit/routes/quests.py
+++ b/src/world_engine/cockpit/routes/quests.py
@@ -13,6 +13,8 @@ The player's quests (Journée):
     GET  /api/quests                     the offers he may accept, his quests
     POST /api/quests/accept              accept one offer (B1, A1)
     POST /api/quests/{quest_id}/abandon  abandon one quest (N1)
+    GET  /api/quests/{quest_id}/settlement  what « déclarer accomplie » shows (G1)
+    POST /api/quests/{quest_id}/settle      « déclarer accomplie » (D1, TICKET-0109)
 
 Every rule lives in `writes/quests.py` (what may be written) and
 `quest_reads.py` (what is shown); this module parses, maps a refusal to its
@@ -32,7 +34,8 @@ from ...day_plan import PlanStep, RequirementSpec
 from ...db import get_session
 from ...models import Quest, QuestEconomy, QuestOffer
 from ...quest_value import DEFAULT_RATES, offer_value, value_dict, world_rates
-from ...writes import TermSpec, abandon_quest, accept_quest, upsert_quest_economy, write_quest_offer
+from ...quest_settlement_view import settlement_context
+from ...writes import TermSpec, abandon_quest, accept_quest, settle_quest, upsert_quest_economy, write_quest_offer
 from ...writes.quest_terms import ECONOMY_COLUMNS
 from .. import crud as _crud
 from .day import _resolve_player_character
@@ -208,3 +211,29 @@ def abandon(quest_id: str, db: Session = Depends(get_session)) -> dict:
         raise HTTPException(status_code=409, detail=str(exc)) from exc
     db.commit()
     return quest_reads.journee_payload(character, db)
+
+
+def _players_quest(quest_id: str, db: Session) -> tuple[Quest, object]:
+    character = _resolve_player_character(_crud._world_id(db), db)
+    quest = db.get(Quest, quest_id)
+    if quest is None or quest.character_id != character.id:
+        raise HTTPException(status_code=404, detail=f"quest {quest_id!r} not found")
+    return quest, character
+
+
+@router.get("/api/quests/{quest_id}/settlement")
+def settlement(quest_id: str, db: Session = Depends(get_session)) -> dict:
+    quest, _character = _players_quest(quest_id, db)
+    return settlement_context(db, quest)
+
+
+@router.post("/api/quests/{quest_id}/settle")
+def settle(quest_id: str, db: Session = Depends(get_session)) -> dict:
+    quest, character = _players_quest(quest_id, db)
+    try:
+        settle_quest(db, quest=quest)
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=409, detail=str(exc)) from exc
+    db.commit()
+    return quest_reads.journee_payload(character, db)
diff --git a/src/world_engine/quest_reads.py b/src/world_engine/quest_reads.py
index 6a9a7d4..ba23c02 100644
--- a/src/world_engine/quest_reads.py
+++ b/src/world_engine/quest_reads.py
@@ -35,7 +35,7 @@ from .models import (
 from .prose_render import fact_texts
 from .quest_value import offer_value, value_dict, world_rates
 from .quest_wording import term_dict, term_line
-from .writes.quest_terms import FACT_REWARD_LEVELS, offer_terms
+from .writes.quest_terms import FACT_REWARD_LEVELS, offer_terms, quest_terms
 from .writes.quests import QUEST_GIVER_TYPES, acceptance_refusal, offer_requirements
 
 # M1: the agenda's status, as the player reads it.
@@ -134,7 +134,7 @@ def _steps_view(agenda: Agenda, character: Character, db: Session) -> list[dict]
             evaluated = evaluate_agenda_step(step, character, db)
             blocked = [requirement_detail_fr(v) for v in evaluated.verdicts if not v.met]
         view.append({"order": step.step_order, "objective": step.objective, "status": step.status,
-                     "blocked": blocked})
+                     "outcome": step.outcome, "blocked": blocked})
     return view
 
 
@@ -154,6 +154,10 @@ def player_quests(character: Character, db: Session) -> list[dict]:
             "summary": offer.summary if offer is not None else None,
             "state": QUEST_STATE_LABELS[agenda.status], "open": agenda.status in ("active", "paused"),
             "steps": _steps_view(agenda, character, db),
+            # TICKET-0109 (D1): its terms, and whether « déclarer accomplie » applies.
+            "terms": [term_line(db, t, offer.giver_entity_id) for t in quest_terms(db, quest.id)] if offer else [],
+            "settled": quest.settled_at is not None,
+            "settleable": quest.settled_at is None and agenda.status in ("active", "paused", "completed"),
         })
     return view
 
diff --git a/src/world_engine/quest_settlement_view.py b/src/world_engine/quest_settlement_view.py
new file mode 100644
index 0000000..b54630e
--- /dev/null
+++ b/src/world_engine/quest_settlement_view.py
@@ -0,0 +1,82 @@
+"""What « déclarer accomplie » shows before Nia decides (TICKET-0109,
+BRIEF-0109-C, G1, contract C-06). Reads only.
+
+Measured context, never a verdict: the quest's steps (status and recorded
+outcome, what the active one still needs), its terms with what each will do,
+their indicative value, the days that advanced it (the declared action, the
+text the day chain read, each step's band), how many of its step changes
+still await review, and why it cannot be settled now, if it cannot. No
+model is called (G1). No agenda or step id appears: the quest is named by
+its `quest_id`.
+"""
+
+from __future__ import annotations
+
+from sqlmodel import Session, select
+
+from .models import Agenda, AgendaStep, Batch, Character, DayRewrite, PassPlay, ProposedMutation, Quest, QuestOffer
+from .quest_reads import QUEST_STATE_LABELS, _steps_view
+from .quest_value import offer_value, value_dict
+from .quest_wording import term_line
+from .skill_access import skill_label
+from .writes.pipeline import read_latest_resolution
+from .writes.quest_settlement import skill_row, settlement_refusals, skill_reward_points
+from .writes.quest_terms import quest_terms
+
+
+def _skill_note(db: Session, quest: Quest, term) -> str:
+    label = skill_label(db, term.skill_key)
+    row = skill_row(db, quest.character_id, term.skill_key)
+    if row is None:
+        return f"apprend « {label} » (Inexpérimenté)"
+    points = skill_reward_points(db, quest.world_id, row)
+    return f"+{points} point(s) en « {label} »" if points is not None else f"déjà Maître en « {label} » : rien"
+
+
+def _terms(db: Session, quest: Quest, giver_id: str, terms: list) -> list[dict]:
+    view = []
+    for term in terms:
+        note = _skill_note(db, quest, term) if term.currency == "skill" and term.direction == "reward" else None
+        view.append({"direction": term.direction, "line": term_line(db, term, giver_id), "note": note})
+    return view
+
+
+def _days(db: Session, agenda: Agenda) -> list[dict]:
+    rows = db.exec(select(PassPlay, Batch).join(Batch, Batch.id == PassPlay.batch_id)
+                   .where(PassPlay.agenda_id == agenda.id).order_by(Batch.day_number)).all()
+    days = []
+    for pass_play, batch in rows:
+        rewrite = db.exec(select(DayRewrite).where(DayRewrite.pass_play_id == pass_play.id)
+                          .order_by(DayRewrite.generation.desc())).first()
+        resolution = read_latest_resolution(pass_play) or {}
+        steps = (resolution.get("fact_sheet") or {}).get("steps") or []
+        days.append({"day_number": batch.day_number, "declared_action": pass_play.declared_action,
+                     "rewritten": rewrite.rendered_text if rewrite is not None else None,
+                     "steps": [{"objective": s.get("objective"), "band": s.get("band")} for s in steps]})
+    return days
+
+
+def _pending_reviews(db: Session, agenda: Agenda) -> int:
+    step_ids = set(db.exec(select(AgendaStep.id).where(AgendaStep.agenda_id == agenda.id)).all())
+    pending = db.exec(select(ProposedMutation).where(
+        ProposedMutation.mutation_type == "agenda_step_change", ProposedMutation.status == "proposed")).all()
+    return sum(1 for m in pending if isinstance(m.payload, dict) and m.payload.get("step_id") in step_ids)
+
+
+def settlement_context(db: Session, quest: Quest) -> dict:
+    """GET /api/quests/{quest_id}/settlement (C-06)."""
+    agenda = db.get(Agenda, quest.agenda_id)
+    offer = db.get(QuestOffer, quest.offer_id)
+    character = db.get(Character, quest.character_id)
+    terms = quest_terms(db, quest.id)
+    refusals = settlement_refusals(db, quest)
+    return {
+        "quest_id": quest.id, "title": agenda.title, "state": QUEST_STATE_LABELS[agenda.status],
+        "settled": quest.settled_at is not None,
+        "steps": _steps_view(agenda, character, db),
+        "terms": _terms(db, quest, offer.giver_entity_id, terms),
+        "value": value_dict(offer_value(db, quest.world_id, terms)),
+        "days": _days(db, agenda),
+        "pending_reviews": _pending_reviews(db, agenda),
+        "refusals": refusals, "can_settle": not refusals,
+    }
diff --git a/src/world_engine/writes/__init__.py b/src/world_engine/writes/__init__.py
index fdd4f1b..ea71f6f 100644
--- a/src/world_engine/writes/__init__.py
+++ b/src/world_engine/writes/__init__.py
@@ -40,6 +40,8 @@ Layout, by canon domain:
     pipeline.py         — `batch`/`pass_play` (TICKET-0075, BRIEF-0075-a).
     items.py            — `item_holding`: `write_holding` (TICKET-0109,
                           BRIEF-0109-A).
+    quest_settlement.py — « déclarer accomplie »: `settle_quest`,
+                          `settlement_refusals` (TICKET-0109, BRIEF-0109-C).
     quest_terms.py      — `quest_offer_term`/`quest_term`/`quest_economy`:
                           `clean_terms`, `write_offer_terms`,
                           `copy_terms_to_quest`, `upsert_quest_economy`
@@ -124,6 +126,7 @@ from .knowledge import (
 )
 from .items import write_holding
 from .mentions import bind_mention, dismiss_mention, record_unresolved, resolve_mention
+from .quest_settlement import settle_quest, settlement_refusals
 from .quest_terms import (
     FACT_REWARD_LEVELS,
     PERSONAL_CURRENCIES,
diff --git a/src/world_engine/writes/quest_settlement.py b/src/world_engine/writes/quest_settlement.py
new file mode 100644
index 0000000..b87a678
--- /dev/null
+++ b/src/world_engine/writes/quest_settlement.py
@@ -0,0 +1,198 @@
+"""« Déclarer accomplie »: settling a quest (TICKET-0109, BRIEF-0109-C, D1,
+contract C-05).
+
+`settlement_refusals` says why a quest cannot be settled now; `settle_quest`
+applies, in one transaction the caller commits, every cost then every
+reward of the quest's own terms (B1), writes its agenda `completed` when it
+is not already, and sets `quest.settled_at`. The code checks what it can:
+a cost the character cannot pay refuses the whole settlement (D1); a
+reward is always given, even when the counterparty lacks it (C-src1: its
+purse may go below 0; it gives the items it holds, the rest is new).
+
+Per currency (the series' D table):
+- money: two ledger lines (the payer -n, the payee +n), `source_type`
+  `quest`.
+- item: the giver's holding -n, the receiver's +n (`write_holding`).
+- relation: what the counterparty feels toward the character, -n (cost) or
+  +n (reward) -- `write_relation(mode="delta")`, type `other` on a new row.
+- fact: the receiver learns it (`knows`, or the reward's level); a holder
+  who already knows it is left as is -- a level never falls.
+- skill, cost: the character, at Maître (C-teach1), teaches the
+  counterparty, who gains the row at Inexpérimenté, `taught_by` him.
+- skill, reward (C-skill1): held -> 10 % of the points its rank needs to
+  rise, at least 1 (a rise resets the points to 0: the surplus is not
+  carried, `write_skill_progress`); at Maître, nothing; not held -> the row
+  at Inexpérimenté, taught by the counterparty when he is at Maître in it.
+"""
+
+from __future__ import annotations
+
+import math
+from collections import defaultdict
+from datetime import UTC, datetime
+from typing import Optional
+
+from sqlmodel import Session, select
+
+from ..fact_refs import find_held
+from ..holdings import held_quantity
+from ..ledger import get_balance
+from ..models import BASE_SKILL_DOMAINS, Agenda, Entity, Quest, QuestOffer, Skill
+from ..skill_access import held_rank, skill_label
+from ..skill_ranks import MAX_RANK, skill_points_to_next
+from .characters import write_ledger_entry, write_skill_progress, write_skill_row
+from .goals_agendas import write_agenda_status
+from .items import write_holding
+from .knowledge import write_knowledge
+from .quest_terms import quest_terms
+from .relations import write_relation
+
+# The share of the points a rank needs that a skill reward gives (C-skill1).
+SKILL_REWARD_SHARE = 0.10
+# The rank a skill learned or taught starts at (Inexpérimenté, 0107 C1).
+LEARNED_RANK = 0
+# The knowledge level a fact gives when the term names none.
+DEFAULT_FACT_LEVEL = "knows"
+CHANGED_BY = "quest_settlement"
+
+
+def _name(db: Session, entity_id: Optional[str]) -> str:
+    entity = db.get(Entity, entity_id) if entity_id else None
+    return entity.name if entity is not None else "?"
+
+
+def skill_row(db: Session, character_id: str, skill_key: str) -> Optional[Skill]:
+    if skill_key in BASE_SKILL_DOMAINS:
+        return db.exec(select(Skill).where(Skill.character_id == character_id, Skill.domain == skill_key,
+                                           Skill.skill_definition_id.is_(None))).first()
+    return db.exec(select(Skill).where(Skill.character_id == character_id,
+                                       Skill.skill_definition_id == skill_key)).first()
+
+
+def skill_reward_points(db: Session, world_id: str, row: Skill) -> Optional[int]:
+    """C-skill1: the points a skill reward gives this row, or None at Maître."""
+    needed = skill_points_to_next(db, world_id=world_id, rank=row.rank, skill_definition_id=row.skill_definition_id)
+    if row.rank >= MAX_RANK or needed is None:
+        return None
+    return max(1, math.ceil(needed * SKILL_REWARD_SHARE))
+
+
+def _cost_refusals(db: Session, quest: Quest, giver_id: str) -> list[str]:
+    character = quest.character_id
+    money = 0
+    items: dict[str, int] = defaultdict(int)
+    refusals: list[str] = []
+    for term in quest_terms(db, quest.id):
+        if term.direction != "cost":
+            continue
+        other = term.counterparty_entity_id or giver_id
+        if term.currency == "money":
+            money += term.amount
+        elif term.currency == "item":
+            items[term.item_id] += term.amount
+        elif term.currency == "fact" and find_held(db, character, {"fact_id": term.fact_id}) is None:
+            refusals.append("il faut connaître le fait à transmettre")
+        elif term.currency == "skill":
+            label = skill_label(db, term.skill_key)
+            if held_rank(db, character, term.skill_key) != MAX_RANK:
+                refusals.append(f"il faut être Maître en « {label} » pour l'enseigner")
+            elif skill_row(db, other, term.skill_key) is not None:
+                refusals.append(f"{_name(db, other)} connaît déjà « {label} »")
+    balance = get_balance(db, character)
+    if money > balance:
+        refusals.append(f"il faut {money} pièce(s), vous en avez {balance}")
+    for item_id, needed in items.items():
+        held = held_quantity(db, character, item_id)
+        if needed > held:
+            refusals.append(f"il faut {needed} × {_name(db, item_id)}, vous en avez {held}")
+    return refusals
+
+
+def settlement_refusals(db: Session, quest: Quest) -> list[str]:
+    """Why `quest` cannot be settled now (French); empty when it can."""
+    if quest.settled_at is not None:
+        return ["cette quête est déjà réglée"]
+    agenda = db.get(Agenda, quest.agenda_id)
+    if agenda is None or agenda.status in ("failed", "abandoned"):
+        return ["cette quête est terminée sans succès"]
+    offer = db.get(QuestOffer, quest.offer_id)
+    return _cost_refusals(db, quest, offer.giver_entity_id)
+
+
+def _money(db: Session, quest: Quest, payer: str, payee: str, amount: int, reason: str) -> None:
+    write_ledger_entry(db, world_id=quest.world_id, entity_id=payer, amount=-amount, counterparty_id=payee,
+                       reason=reason, source_type="quest")
+    write_ledger_entry(db, world_id=quest.world_id, entity_id=payee, amount=amount, counterparty_id=payer,
+                       reason=reason, source_type="quest")
+
+
+def _items(db: Session, quest: Quest, giver: str, receiver: str, item_id: str, amount: int, cost: bool) -> None:
+    taken = amount if cost else min(amount, held_quantity(db, giver, item_id))
+    if taken:
+        write_holding(db, world_id=quest.world_id, item_id=item_id, holder_entity_id=giver, delta=-taken,
+                      changed_by=CHANGED_BY)
+    write_holding(db, world_id=quest.world_id, item_id=item_id, holder_entity_id=receiver, delta=amount,
+                  changed_by=CHANGED_BY)
+
+
+def _fact(db: Session, receiver: str, fact_id: str, level: Optional[str]) -> None:
+    if find_held(db, receiver, {"fact_id": fact_id}) is not None:
+        return
+    write_knowledge(db, entity_id=receiver, fact_id=fact_id, level=level or DEFAULT_FACT_LEVEL,
+                    source="quête", changed_by=CHANGED_BY)
+
+
+def _skill_reward(db: Session, quest: Quest, teacher: str, skill_key: str) -> None:
+    row = skill_row(db, quest.character_id, skill_key)
+    if row is None and skill_key not in BASE_SKILL_DOMAINS:
+        master = teacher if held_rank(db, teacher, skill_key) == MAX_RANK else None
+        write_skill_row(db, character_id=quest.character_id, rank=LEARNED_RANK, skill_definition_id=skill_key,
+                        taught_by_id=master)
+        return
+    if row is None:
+        row = write_skill_row(db, character_id=quest.character_id, rank=held_rank(db, quest.character_id, skill_key),
+                              domain=skill_key)
+        db.flush()
+    points = skill_reward_points(db, quest.world_id, row)
+    if points is not None:
+        write_skill_progress(db, skill_id=row.id, world_id=quest.world_id, points=points, changed_by=CHANGED_BY)
+
+
+def _apply_term(db: Session, quest: Quest, term, giver_id: str, reason: str) -> None:
+    character, other = quest.character_id, term.counterparty_entity_id or giver_id
+    cost = term.direction == "cost"
+    if term.currency == "money":
+        _money(db, quest, character if cost else other, other if cost else character, term.amount, reason)
+    elif term.currency == "item":
+        _items(db, quest, character if cost else other, other if cost else character, term.item_id, term.amount, cost)
+    elif term.currency == "relation":
+        write_relation(db, mode="delta", world_id=quest.world_id, entity_a_id=other, entity_b_id=character,
+                       type="other", value=-term.amount if cost else term.amount, changed_by=CHANGED_BY)
+    elif term.currency == "fact":
+        _fact(db, other if cost else character, term.fact_id, None if cost else term.level)
+    elif cost:
+        write_skill_row(db, character_id=other, rank=LEARNED_RANK, skill_definition_id=term.skill_key,
+                        taught_by_id=character)
+    else:
+        _skill_reward(db, quest, other, term.skill_key)
+    db.flush()
+
+
+def settle_quest(db: Session, *, quest: Quest) -> Quest:
+    """D1 (C-05): `ValueError` with the refusals joined, before any write;
+    otherwise every cost, then every reward, the agenda `completed`, and
+    `settled_at`. Never commits."""
+    refusals = settlement_refusals(db, quest)
+    if refusals:
+        raise ValueError("; ".join(refusals))
+    offer = db.get(QuestOffer, quest.offer_id)
+    agenda = db.get(Agenda, quest.agenda_id)
+    reason = f"Quête « {agenda.title} »"
+    terms = quest_terms(db, quest.id)
+    for term in [t for t in terms if t.direction == "cost"] + [t for t in terms if t.direction == "reward"]:
+        _apply_term(db, quest, term, offer.giver_entity_id, reason)
+    if agenda.status != "completed":
+        write_agenda_status(db, agenda=agenda, status="completed")
+    quest.settled_at = datetime.now(UTC)
+    db.add(quest)
+    return quest
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 70b8636..f9781ca 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18182,6 +18182,37 @@ or « sans coût ». The unit is never converted, never spent.
 would reprice a bargain. Fixed rates in code (E2): each world has its own
 economy.
 
+
+## « DÉCLARER ACCOMPLIE » SETTLES A QUEST AT ONCE (TICKET-0109) -- MEASURED CONTEXT FIRST, AN UNPAYABLE COST REFUSES (BRIEF-0109-c, no schema change)
+
+**D1.** Settling is a direct write Nia makes from Journée, on any quest not
+yet settled and not failed or abandoned -- still open, or completed by its
+steps. One transaction: every cost, then every reward, of the quest's own
+terms; the agenda `completed` when it is not; `quest.settled_at` set, once.
+The steps left are untouched: they are the quest's history. A cost the
+character cannot pay -- coins, items (summed per item across terms), a fact
+he does not know, a skill he is not Maître in, or one the counterparty
+already holds -- refuses the whole settlement with its reasons, and nothing
+is written (D2, a « forcer », rejected: the creator adjusts the sheet).
+
+**C-src1.** A reward is always given: money moves even below the
+counterparty's 0; items come from what he holds, the rest is new.
+**C-skill1.** A skill reward gives 10 % of the points the skill's rank needs
+to rise, at least 1; a rise resets the points to 0 (the surplus is not
+carried, `write_skill_progress`'s rule); at Maître, nothing; a skill not
+held is learned at Inexpérimenté, taught by the counterparty when he is at
+Maître. **C-teach1.** Teaching needs the character at Maître; the
+counterparty learns at Inexpérimenté, `taught_by` him.
+
+**G1.** Before the click: the steps and their outcomes, the terms and what
+each will do, their value, the days that advanced the quest (declared
+action, the text the day read, each step's band), the step changes still
+awaiting review, and the refusals. No model is asked.
+
+**Rejected.** A « déclarer échouée » button (D-fail1): « Abandonner »
+exists. A mutation in the review queue (D2 of the series): Nia would
+approve her own click.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index 29f13a4..555ff17 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -59,6 +59,8 @@ src/world_engine/writes/quests.py::accept_quest                agenda_step_requi
 src/world_engine/writes/quest_terms.py::write_offer_terms      quest_offer_term
 src/world_engine/writes/quest_terms.py::copy_terms_to_quest    quest_term
 src/world_engine/writes/quest_terms.py::upsert_quest_economy   quest_economy
+# TICKET-0109, BRIEF-0109-C: settle_quest sets quest.settled_at once, at « déclarer accomplie »; every term it applies goes through write_ledger_entry, write_holding, write_relation, write_knowledge, write_skill_row, write_skill_progress and write_agenda_status, allow-listed above.
+src/world_engine/writes/quest_settlement.py::settle_quest       quest
 # TICKET-0044, BRIEF-0044-c: create_entity_type is the 26th site — the governed
 # structural-write authority (D2), a NEW sanctioned site distinct from the two
 # canon-write paths (AI-proposal pipeline, creator CRUD). Its `CREATE TABLE
diff --git a/tooling/verify/checks/quest_rewards.py b/tooling/verify/checks/quest_rewards.py
index c26902f..ca22710 100644
--- a/tooling/verify/checks/quest_rewards.py
+++ b/tooling/verify/checks/quest_rewards.py
@@ -59,6 +59,34 @@ RB3 -- the indicative unit (fixture, C1/E1). With no economy row the rates
    vous monte de 5 ». The routes `preview_value`, `get_economy`,
    `set_economy` answer the same numbers and 422 on a refusal.
 
+RC1 -- refusals (BRIEF-0109-C, fixture, D1). `settle_quest` refuses, with
+   no row written anywhere: 12 coins owed with 10; 3 furs owed across two
+   terms with 2; a fact to transmit the character does not know; a skill to
+   teach he is not Maître in; a skill the counterparty already holds; an
+   abandoned quest; a quest already settled.
+RC2 -- what settlement writes (fixture). One quest with every currency:
+   costs 10 coins, 2 furs, 5 relation points, a fact, teaching a skill;
+   rewards 20 coins (the giver, paid 10, ends at -10: C-src1), 3
+   ropes (the giver holds 1: he ends at 0, the character gains 3), 8
+   relation points, a fact at `partial`, a skill held at rank 3 (+4 points,
+   10 % of 40), a skill held at rank 1 with 9 points (+1: rank 2, 0
+   points), a skill held at Maître (nothing), a skill not held (its row at
+   Inexpérimenté, taught by the giver, a Maître). Afterwards: the ledger,
+   the holdings, the relation of the giver toward the character (50 - 5 + 8
+   = 53), both knowledge rows, the giver's taught row (rank 0, taught by the
+   character), the four skill rows; the agenda `completed`; `settled_at`
+   set. A quest with no cost, settled once, is refused the second time. The ledger lines carry `source_type`
+   `quest`.
+RC3 -- what Nia sees (fixture and static). `settlement_context` gives the
+   steps, the terms with their lines and the skill notes (« +4 point(s) »,
+   « apprend »), the value, one day advanced by the quest (its declared
+   action, the rewritten text, the step's band), the count of step changes
+   awaiting review, the refusals and `can_settle`; no key `agenda_id` or
+   `step_id` at any depth, no model call (`quest_settlement_view.py` imports
+   no `ollama_client`). The routes `settlement` and `settle` answer it and
+   409 on a refusal; `journee_payload` marks the quest `settled`, not
+   `settleable`, with its term lines.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
@@ -625,6 +653,282 @@ def check_rb(engine) -> None:
         _rb3_wording_and_routes(session, ids)
 
 
+# --- RC --------------------------------------------------------------------------
+
+def _rc_world(session) -> dict:
+    from world_engine.models import Character, Entity, Fact, Faction, Item, SkillDefinition, World
+
+    world = World(name="Quest rewards RC", is_active=False)
+    session.add(world)
+    session.flush()
+    ids = {"world": world.id}
+    for key, kind, name in (("pc", "character", "Millys"), ("npc", "character", "Garde"),
+                            ("fur", "item", "Fourrure de loup"), ("rope", "item", "Corde")):
+        row = Entity(world_id=world.id, type=kind, name=name)
+        session.add(row)
+        session.flush()
+        ids[key] = row.id
+    session.add_all([Character(id=ids["pc"], world_id=world.id, character_type="player"),
+                     Character(id=ids["npc"], world_id=world.id, character_type="npc"),
+                     Item(id=ids["fur"], value=3), Item(id=ids["rope"], value=1)])
+    for key, name in (("herb", "Herboristerie"), ("forge", "Forge"), ("chant", "Chant")):
+        definition = SkillDefinition(world_id=world.id, name=name, base_domain="perception")
+        session.add(definition)
+        session.flush()
+        ids[key] = definition.id
+    for key, text in (("secret", "Le passage secret"), ("map", "La carte du col")):
+        fact = Fact(world_id=world.id, content_raw=text, created_by="check")
+        session.add(fact)
+        session.flush()
+        ids[key] = fact.id
+    session.commit()
+    return ids
+
+
+def _rc_holdings(session, ids) -> None:
+    from world_engine.models import Knowledge, Skill
+    from world_engine.writes import write_holding, write_ledger_entry
+
+    w = ids["world"]
+    write_ledger_entry(session, world_id=w, entity_id=ids["pc"], amount=10, source_type="creator")
+    write_holding(session, world_id=w, item_id=ids["fur"], holder_entity_id=ids["pc"], quantity=2, changed_by="check")
+    write_holding(session, world_id=w, item_id=ids["rope"], holder_entity_id=ids["npc"], quantity=1, changed_by="check")
+    session.add(Knowledge(entity_id=ids["pc"], fact_id=ids["secret"], level="knows"))
+    session.add_all([
+        Skill(character_id=ids["pc"], domain="perception", skill_definition_id=ids["herb"], rank=5, change_history=[]),
+        Skill(character_id=ids["pc"], domain="agility", rank=3, xp=0, change_history=[]),
+        Skill(character_id=ids["pc"], domain="composure", rank=1, xp=9, change_history=[]),
+        Skill(character_id=ids["pc"], domain="physical", rank=5, xp=0, change_history=[]),
+        Skill(character_id=ids["npc"], domain="perception", skill_definition_id=ids["chant"], rank=5, change_history=[]),
+    ])
+    session.commit()
+
+
+def _rc_quest(session, ids, terms, title: str):
+    from world_engine.day_plan import PlanStep
+    from world_engine.models import Character
+    from world_engine.writes import accept_quest, write_quest_offer
+
+    offer = write_quest_offer(session, world_id=ids["world"], offer=None, giver_entity_id=ids["npc"], title=title,
+                              summary=None, repeatable=True, status="open", eligibility=[],
+                              steps=[PlanStep(objective="Chasser", cost=1, domain=None)], terms=terms)
+    session.flush()
+    quest = accept_quest(session, offer=offer, character=session.get(Character, ids["pc"]))
+    session.commit()
+    return quest
+
+
+def _snapshot(session) -> tuple:
+    from sqlmodel import func, select
+
+    from world_engine.models import ItemHolding, Knowledge, Ledger, Relation, Skill
+
+    return tuple(session.exec(select(func.count()).select_from(m)).one()
+                 for m in (Ledger, ItemHolding, Knowledge, Relation, Skill)) + tuple(
+        (h.item_id, h.holder_entity_id, h.quantity) for h in session.exec(select(ItemHolding)).all())
+
+
+def _settle_refused(session, quest, label: str) -> None:
+    from world_engine.writes import settle_quest
+
+    before = _snapshot(session)
+    try:
+        settle_quest(session, quest=quest)
+    except ValueError:
+        session.rollback()
+        if _snapshot(session) != before or quest.settled_at is not None and label != "already settled":
+            fail(f"RC1: a refused settlement ({label}) wrote rows")
+        return
+    session.rollback()
+    fail(f"RC1: settle_quest accepts {label}")
+
+
+def check_rc1(session, ids) -> None:
+    from world_engine.models import Agenda
+    from world_engine.writes import TermSpec
+
+    cases = {
+        "12 coins owed with 10": [TermSpec(direction="cost", currency="money", amount=12)],
+        "3 furs owed across two terms with 2": [TermSpec(direction="cost", currency="item", item_id=ids["fur"], amount=2),
+                                                TermSpec(direction="cost", currency="item", item_id=ids["fur"], amount=1)],
+        "a fact he does not know": [TermSpec(direction="cost", currency="fact", fact_id=ids["map"])],
+        "a skill he is not Maître in": [TermSpec(direction="cost", currency="skill", skill_key=ids["forge"])],
+        "a skill the counterparty holds": [TermSpec(direction="cost", currency="skill", skill_key=ids["chant"])],
+    }
+    for label, terms in cases.items():
+        _settle_refused(session, _rc_quest(session, ids, terms, label), label)
+    abandoned = _rc_quest(session, ids, [], "abandonnée")
+    agenda = session.get(Agenda, abandoned.agenda_id)
+    agenda.status = "abandoned"
+    session.add(agenda)
+    session.commit()
+    _settle_refused(session, abandoned, "an abandoned quest")
+
+
+def _rc2_terms(ids) -> list:
+    from world_engine.writes import TermSpec
+
+    return [
+        TermSpec(direction="cost", currency="money", amount=10),
+        TermSpec(direction="cost", currency="item", item_id=ids["fur"], amount=2),
+        TermSpec(direction="cost", currency="relation", amount=5),
+        TermSpec(direction="cost", currency="fact", fact_id=ids["secret"]),
+        TermSpec(direction="cost", currency="skill", skill_key=ids["herb"]),
+        TermSpec(direction="reward", currency="money", amount=20),
+        TermSpec(direction="reward", currency="item", item_id=ids["rope"], amount=3),
+        TermSpec(direction="reward", currency="relation", amount=8),
+        TermSpec(direction="reward", currency="fact", fact_id=ids["map"], level="partial"),
+        TermSpec(direction="reward", currency="skill", skill_key="agility"),
+        TermSpec(direction="reward", currency="skill", skill_key="composure"),
+        TermSpec(direction="reward", currency="skill", skill_key="physical"),
+        TermSpec(direction="reward", currency="skill", skill_key=ids["chant"]),
+    ]
+
+
+def _rc2_expect(session, ids) -> None:
+    from sqlmodel import select
+
+    from world_engine.holdings import held_quantity
+    from world_engine.ledger import get_balance
+    from world_engine.models import Knowledge, Ledger, Relation, Skill
+
+    pc, npc = ids["pc"], ids["npc"]
+    got = {
+        "balances": (get_balance(session, pc), get_balance(session, npc)),
+        "holdings": (held_quantity(session, pc, ids["fur"]), held_quantity(session, npc, ids["fur"]),
+                     held_quantity(session, pc, ids["rope"]), held_quantity(session, npc, ids["rope"])),
+        "relation": [r.intensity for r in session.exec(select(Relation).where(
+            Relation.entity_a_id == npc, Relation.entity_b_id == pc)).all()],
+        "knowledge": sorted((k.entity_id == npc, k.fact_id == ids["map"], k.level) for k in session.exec(
+            select(Knowledge).where(Knowledge.entity_id.in_([pc, npc]))).all()),
+    }
+    expected = {
+        "balances": (20, -10), "holdings": (0, 2, 3, 0), "relation": [53],
+        "knowledge": sorted([(False, False, "knows"), (False, True, "partial"), (True, False, "knows")]),
+    }
+    for key, value in expected.items():
+        if got[key] != value:
+            fail(f"RC2: {key} is {got[key]}, expected {value}")
+    rows = {(s.character_id, s.domain, s.skill_definition_id): (s.rank, s.xp, s.taught_by_id)
+            for s in session.exec(select(Skill)).all() if s.character_id in (pc, npc)}
+    skills = {
+        "taught": rows.get((npc, "perception", ids["herb"])), "agility": rows.get((pc, "agility", None)),
+        "composure": rows.get((pc, "composure", None)), "physical": rows.get((pc, "physical", None)),
+        "learned": rows.get((pc, "perception", ids["chant"])),
+    }
+    want = {"taught": (0, 0, pc), "agility": (3, 4, None), "composure": (2, 0, None),
+            "physical": (5, 0, None), "learned": (0, 0, npc)}
+    if skills != want:
+        fail(f"RC2: the skill rows are {skills}, expected {want}")
+    sources = {e.source_type for e in session.exec(select(Ledger).where(Ledger.reason.like("Quête%"))).all()}
+    if sources != {"quest"}:
+        fail(f"RC2: the settlement's ledger lines carry {sources}")
+
+
+def check_rc2(session, ids) -> None:
+    from world_engine.models import Agenda
+    from world_engine.writes import TermSpec, settle_quest
+
+    quest = _rc_quest(session, ids, _rc2_terms(ids), "Tout")
+    ids["quest"] = quest.id
+    settle_quest(session, quest=quest)
+    session.commit()
+    _rc2_expect(session, ids)
+    if session.get(Agenda, quest.agenda_id).status != "completed" or quest.settled_at is None:
+        fail("RC2: the settled quest's agenda is not completed, or settled_at is not set")
+    # A quest with no cost: only the settled guard can refuse it the second time.
+    free = _rc_quest(session, ids, [TermSpec(direction="reward", currency="money", amount=1)], "Sans coût")
+    settle_quest(session, quest=free)
+    session.commit()
+    _settle_refused(session, free, "already settled")
+
+
+def _rc3_day(session, ids, quest) -> None:
+    from world_engine.models import Batch, DayRewrite, PassPlay, Session as GameSession
+
+    game = GameSession(world_id=ids["world"], number=1)
+    session.add(game)
+    session.flush()
+    batch = Batch(session_id=game.id, day_number=4)
+    session.add(batch)
+    session.flush()
+    pass_play = PassPlay(batch_id=batch.id, session_id=game.id, character_id=ids["pc"], agenda_id=quest.agenda_id,
+                         declared_action="Je traque le loup.", status="resolved",
+                         history=[{"fact_sheet": {"steps": [{"objective": "Chasser", "band": "success"}]}}])
+    session.add(pass_play)
+    session.flush()
+    session.add(DayRewrite(world_id=ids["world"], pass_play_id=pass_play.id, generation=1,
+                           rendered_text="Millys traque le loup."))
+    session.commit()
+
+
+def check_rc3(session, ids) -> None:
+    from sqlmodel import select
+
+    from fastapi import HTTPException
+
+    from world_engine.cockpit.routes import quests as routes
+    from world_engine.models import Quest, World
+    from world_engine.quest_reads import journee_payload
+    from world_engine.quest_settlement_view import settlement_context
+    from world_engine.writes import TermSpec
+
+    pending = _rc_quest(session, ids, [TermSpec(direction="reward", currency="skill", skill_key="agility"),
+                                       TermSpec(direction="cost", currency="money", amount=99)], "À régler")
+    _rc3_day(session, ids, pending)
+    context = settlement_context(session, pending)
+    day = (context["days"] or [{}])[0]
+    if (day.get("day_number"), day.get("declared_action"), day.get("rewritten"), day.get("steps")) != (
+            4, "Je traque le loup.", "Millys traque le loup.", [{"objective": "Chasser", "band": "success"}]):
+        fail(f"RC3: the days are {context['days']}")
+    notes = [t["note"] for t in context["terms"] if t["note"]]
+    if notes != ["+4 point(s) en « agility »"] or context["can_settle"] or not context["refusals"]:
+        fail(f"RC3: notes {notes}, refusals {context['refusals']}")
+    if {"agenda_id", "step_id"} & _keys(context):
+        fail("RC3: the settlement context names an agenda or a step id")
+    if "ollama_client" in (SRC / "quest_settlement_view.py").read_text(encoding="utf-8"):
+        fail("RC3: the settlement view imports the model client")
+    for world in session.exec(select(World).where(World.is_active == True)).all():  # noqa: E712
+        world.is_active = False
+        session.add(world)
+    session.flush()
+    session.get(World, ids["world"]).is_active = True
+    session.commit()
+    if routes.settlement(pending.id, db=session)["quest_id"] != pending.id:
+        fail("RC3: GET settlement disagrees")
+    try:
+        routes.settle(pending.id, db=session)
+        fail("RC3: POST settle accepts an unpayable quest")
+    except HTTPException as exc:
+        if exc.status_code != 409:
+            fail(f"RC3: POST settle refusal answers {exc.status_code}")
+    settled = session.get(Quest, ids["quest"])
+    row = next((q for q in journee_payload(session.get(__import__("world_engine.models", fromlist=["Character"]).Character,
+                                                       ids["pc"]), session)["quests"]
+                if q["quest_id"] == settled.id), None)
+    if row is None or not row["settled"] or row["settleable"] or len(row["terms"]) != 13:
+        fail(f"RC3: the settled quest in the Journée payload is {row and {k: row[k] for k in ('settled', 'settleable')}}")
+
+
+def check_rc(engine) -> None:
+    from sqlmodel import Session
+
+    with Session(engine) as session:
+        ids = _rc_world(session)
+        _rc_holdings(session, ids)
+        check_rc1(session, ids)
+        check_rc2(session, ids)
+        check_rc3(session, ids)
+
+
+def _keys(value) -> set:
+    if isinstance(value, dict):
+        return set(value) | {k for v in value.values() for k in _keys(v)}
+    if isinstance(value, list):
+        return {k for v in value for k in _keys(v)}
+    return set()
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_ra1()
@@ -633,6 +937,7 @@ def main() -> int:
     create_db_and_tables()
     check_ra3(engine)
     check_rb(engine)
+    check_rc(engine)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -641,7 +946,8 @@ def main() -> int:
           "migrates owners and places to holdings from v2.17 only, drops equipped, and one writer "
           "keeps every holding, its history, and zones empty; an offer's terms are validated whole, "
           "copied to the quest that accepts it, and valued in the world's indicative unit against "
-          "its band")
+          "its band; « déclarer accomplie » shows the measured context, refuses an unpayable cost "
+          "with no write, and applies every cost then every reward at once")
     return 0
 
 
diff --git a/world-engine-schema.md b/world-engine-schema.md
index ac4350e..e6b5a12 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -860,7 +860,7 @@ CREATE TABLE ledger (
   amount          INTEGER NOT NULL,        -- signed: + credit, − debit; world base unit
   counterparty_id TEXT REFERENCES entity(id),           -- the other party (filled, not double-written)
   reason          TEXT,                    -- "pécule de départ", "correction prix"
-  source_type     TEXT,                    -- creator | correction | conversation | pass_play | tick
+  source_type     TEXT,                    -- creator | correction | conversation | pass_play | tick | quest (v2.18 settlement)
                                             -- ('conversation' written by
                                             -- _apply_mutation's resource_change
                                             -- branch, BRIEF-19/v1.32; 'pass_play'
````

## Scope OUT

- Any frontend file (D).
- A « déclarer échouée » button (D-fail2), forcing an unpayable settlement (D2), a partial settlement.
- A model call of any kind in the recap (G1).
- Raising a fact level the receiver already holds; carrying skill points past a rank.
- Settling through a mutation in the review queue (D1: a direct creator write).
- Debts born of a settlement (TICKET-0110).
- Every later brief of this lot.

## Invariants to defend

**Two canon-write paths:** settlement is a creator-direct write from Journée, through `settle_quest`, allow-listed by function; it calls the existing writers (`write_ledger_entry`, `write_holding`, `write_relation`, `write_knowledge`, `write_skill_row`, `write_skill_progress`, `write_agenda_status`) and writes only `quest.settled_at` itself. **All or nothing:** every refusal is found before the first write; the route commits once. **History is sacred:** every write appends where its writer does; the ledger lines carry `source_type` `quest` and the quest's id. **The model proposes, Python judges:** the recap measures, it does not judge -- Nia decides. **The player never sees the agenda:** the recap and the payload name no `agenda_id` or `step_id`.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `settle_quest` would write anything before every refusal is checked.
- `routes/quests.py` is not exactly 239 lines after the commit.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).
- `pyflakes` reporting `VetoVerdict` imported but unused in `routes/day.py` (pre-existing).

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/quest_rewards.py` -> `PASS: quest_rewards -- v2.18 makes an item a kind held in quantity by any entity, migrates owners and places to holdings from v2.17 only, drops equipped, and one writer keeps every holding, its history, and zones empty; an offer's terms are validated whole, copied to the quest that accepts it, and valued in the world's indicative unit against its band; « déclarer accomplie » shows the measured context, refuses an unpayable cost with no write, and applies every cost then every reward at once`.
- `quests.py`, `single_canon_write.py`, `day_mutations.py`, `module_budget.py`, `function_length.py`, `undefined_names.py`, `schema_version_agreement.py`, `pipeline_state.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted, in `writes/quest_settlement.py`: `    if money > balance:` -> `    if False:` -> `RC1` and `RC3`; `SKILL_REWARD_SHARE = 0.10` -> `SKILL_REWARD_SHARE = 0.5` -> `RC2`; `    if quest.settled_at is not None:` -> `    if False:` -> `RC1`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 142/142.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `« DÉCLARER ACCOMPLIE » SETTLES A QUEST AT ONCE (TICKET-0109) -- MEASURED CONTEXT FIRST, AN UNPAYABLE COST REFUSES (BRIEF-0109-c, no schema change)`; the ledger `source_type` line of the schema doc — both in the diff. No schema change, no CLAUDE.md change.
