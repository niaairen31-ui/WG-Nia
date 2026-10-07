# BRIEF 0109-B — "Costs and rewards in five currencies, copied at acceptance, weighed in an indicative unit"

Lot: LOT-0109-quest-terms.md (authoritative on conflict)
Depends on: BRIEF-0109-A

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0109-A's commit). The facts carried below quote `main`'s line
numbers, as the lot does; where A moved a line, the anchor here gives where it now is.

- `src/world_engine/writes/quests.py:88` -> `def write_quest_offer(`; `:172` -> `def accept_quest(db: Session, *, offer: QuestOffer, character: Character) -> Quest:`.
- `src/world_engine/quest_reads.py:57` -> `def offer_dict(offer: QuestOffer, db: Session) -> dict:`; `:85` -> `def editor_choices(world_id: str, db: Session) -> dict:`; the file is 170 lines.
- `src/world_engine/cockpit/routes/quests.py:52` -> `class OfferBody(BaseModel):`; the file is 148 lines.
- `src/world_engine/day_plan.py:296` -> `def _skill_label(db: Session, skill_key: Optional[str]) -> str:`.
- `src/world_engine/models/quests.py:164` -> `class QuestOfferTerm(SQLModel, table=True):`; `:222` -> `class QuestEconomy(SQLModel, table=True):`.
- `tooling/verify/canon_write_policy.txt:51` -> `src/world_engine/writes/items.py::write_holding                item_holding`.
- `tooling/verify/checks/quest_rewards.py:410` -> `    check_ra3(engine)`.
- No `src/world_engine/writes/quest_terms.py`, `quest_value.py` or `quest_wording.py` exists.

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

### R-13 — the 0108 writers and views [M]
Opened: `src/world_engine/writes/quests.py:88-139` (`write_quest_offer`,
full-replace `:118-120`), `:172-198` (`accept_quest`);
`src/world_engine/quest_reads.py:57-71` (`offer_dict`), `:85-104`
(`editor_choices`), `:115-127` (`_steps_view`), `:129-147`
(`player_quests`), `:149-158` (`journee_payload`);
`src/world_engine/cockpit/routes/quests.py:52-60` (`OfferBody`), `:75`
(the one caller of `write_quest_offer` in `src/`).

### R-16 — one config row per world [M]
Opened: `src/world_engine/models/config.py:26-58`
(`ConversationWindowConfig`: unique per world, absence reads defaults, the
reader never writes).
Consequence: `quest_economy`, same shape.

### R-19 — budgets [M]
Opened: `tooling/verify/checks/module_budget.py:57-58` (40/1000 per `src/`
module), `tooling/verify/checks/function_length.py:29` (80).
Consequence: four new modules (`holdings.py`, `writes/items.py`,
`writes/quest_terms.py`, `writes/quest_settlement.py`) and three reads
(`quest_value.py`, `quest_wording.py`, `quest_settlement_view.py`); none
over budget.

## Contracts

### C-01 — schema v2.18
Produced by: BRIEF-0109-A   Consumed by: B, C, D
- `item(id -> entity, condition DEFAULT 'intact', value INTEGER NOT NULL
  DEFAULT 1 CHECK (value >= 0))`.
- `item_holding(id, world_id, item_id -> item, holder_entity_id -> entity,
  quantity INTEGER NOT NULL DEFAULT 0 CHECK (quantity >= 0), updated_at,
  change_history JSON)`, unique `(item_id, holder_entity_id)`, index on
  `holder_entity_id`.
- `quest_offer_term(id, world_id, offer_id -> quest_offer, term_order,
  direction, currency, counterparty_entity_id -> entity, item_id -> item,
  fact_id -> fact, skill_key, amount, level)` and `quest_term` (same,
  `quest_id -> quest`), three CHECKs each, byte for byte:
  ```
  direction IN ('cost','reward')
  currency IN ('money','item','relation','fact','skill')
  (currency NOT IN ('money','item','relation') OR (amount IS NOT NULL AND amount >= 1)) AND (currency <> 'item' OR item_id IS NOT NULL) AND (currency <> 'fact' OR fact_id IS NOT NULL) AND (currency <> 'skill' OR skill_key IS NOT NULL)
  ```
- `quest_economy(id, world_id unique, rate_money, rate_relation, rate_fact,
  rate_skill, band_low_pct, band_high_pct -- each NULL or >= 0, updated_at)`.
- `quest.settled_at DATETIME NULL`.

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

**b-3 — the value verdict**: cost 0 -> `free`; `ratio_pct < band_low` ->
`meagre`; `ratio_pct > band_high` -> `generous`; otherwise `balanced`.

## Context

With v2.18 in place (A), this brief gives an offer its terms (B1): costs and rewards in five currencies, validated whole by one writer, copied into the quest when it is accepted and never touched again. It weighs them in the world's indicative unit (E1): rates a world may set, defaults otherwise, a verdict against the band. No term is applied here (C).

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. The generated `tooling/standards/DECISIONS_INDEX.md`
is not in the diff: regenerate it as listed.

1. Apply the embedded diff. It:
   - creates `src/world_engine/writes/quest_terms.py` (`TermSpec`, `clean_term`, `clean_terms`, `COUNTED_CURRENCIES`, `PERSONAL_CURRENCIES`, `MAX_RELATION_AMOUNT = 99`, `FACT_REWARD_LEVELS`, `TERM_COLUMNS`, `ECONOMY_COLUMNS`, `write_offer_terms` full replace, `offer_terms`, `quest_terms`, `copy_terms_to_quest`, `upsert_quest_economy` -- C-03, C-04), exported by `writes`;
   - `writes/quests.py`: `write_quest_offer(..., terms=None)` (None keeps the stored terms and revalidates them against the offer's giver); `accept_quest` copies them;
   - creates `src/world_engine/quest_value.py` (`DEFAULT_RATES`, `world_rates`, `term_value`, `offer_value`, `value_dict`) and `src/world_engine/quest_wording.py` (`term_line`, `term_dict`);
   - moves `day_plan._skill_label` to `skill_access.skill_label` (`day_plan` imports it);
   - `quest_reads.py`: `offer_dict` gains `terms` and `value`; `editor_choices` gains `items`, `fact_levels`, `rates`; Journée's offers gain their term lines;
   - `routes/quests.py`: `TermBody`, `OfferBody.terms`, `POST /api/quest-offers/value`, `GET` and `PUT /api/quest-economy` (C-07; 210 lines after);
   - allow-lists `write_offer_terms`, `copy_terms_to_quest`, `upsert_quest_economy` in `canon_write_policy.txt`; names `write_offer_terms` in `single_canon_write.py`'s full-replace list;
   - adds RB1-RB3 to `quest_rewards.py`;
   - appends the decision entry above the footer.
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(quests): costs and rewards in five currencies, copied at acceptance, weighed in an indicative unit (BRIEF-0109-b)`.

````diff
diff --git a/src/world_engine/cockpit/routes/quests.py b/src/world_engine/cockpit/routes/quests.py
index e4c5a86..cd3c919 100644
--- a/src/world_engine/cockpit/routes/quests.py
+++ b/src/world_engine/cockpit/routes/quests.py
@@ -5,6 +5,9 @@ The creator's offers (E1) -- creator CRUD, a sanctioned canon-write path:
     GET  /api/quest-offers/choices   what the editor's pickers list
     POST /api/quest-offers           create one offer
     PUT  /api/quest-offers/{id}      save one offer (steps replaced whole)
+    POST /api/quest-offers/value     the indicative value of draft terms
+    GET  /api/quest-economy          the world's rates (TICKET-0109, E1)
+    PUT  /api/quest-economy          set them (None = the code's default)
 
 The player's quests (Journée):
     GET  /api/quests                     the offers he may accept, his quests
@@ -22,13 +25,15 @@ from typing import Optional
 
 from fastapi import APIRouter, Depends, HTTPException
 from pydantic import BaseModel, Field
-from sqlmodel import Session
+from sqlmodel import Session, select
 
 from ... import quest_reads
 from ...day_plan import PlanStep, RequirementSpec
 from ...db import get_session
-from ...models import Quest, QuestOffer
-from ...writes import abandon_quest, accept_quest, write_quest_offer
+from ...models import Quest, QuestEconomy, QuestOffer
+from ...quest_value import DEFAULT_RATES, offer_value, value_dict, world_rates
+from ...writes import TermSpec, abandon_quest, accept_quest, upsert_quest_economy, write_quest_offer
+from ...writes.quest_terms import ECONOMY_COLUMNS
 from .. import crud as _crud
 from .day import _resolve_player_character
 
@@ -49,6 +54,17 @@ class OfferStepBody(BaseModel):
     requirements: list[RequirementBody] = Field(default_factory=list)
 
 
+class TermBody(BaseModel):
+    direction: str
+    currency: str
+    counterparty_entity_id: Optional[str] = None
+    item_id: Optional[str] = None
+    fact_id: Optional[str] = None
+    skill_key: Optional[str] = None
+    amount: Optional[int] = None
+    level: Optional[str] = None
+
+
 class OfferBody(BaseModel):
     giver_entity_id: str
     title: str
@@ -57,6 +73,26 @@ class OfferBody(BaseModel):
     status: str = "open"
     eligibility: list[RequirementBody] = Field(default_factory=list)
     steps: list[OfferStepBody] = Field(default_factory=list)
+    # TICKET-0109 (B1): the offer's costs and rewards, replaced whole; absent
+    # (None) keeps the stored ones.
+    terms: Optional[list[TermBody]] = None
+
+
+class ValueBody(BaseModel):
+    terms: list[TermBody] = Field(default_factory=list)
+
+
+class EconomyBody(BaseModel):
+    rate_money: Optional[int] = None
+    rate_relation: Optional[int] = None
+    rate_fact: Optional[int] = None
+    rate_skill: Optional[int] = None
+    band_low_pct: Optional[int] = None
+    band_high_pct: Optional[int] = None
+
+
+def _term(term: TermBody) -> TermSpec:
+    return TermSpec(**{name: (value if value != "" else None) for name, value in term.model_dump().items()})
 
 
 class AcceptBody(BaseModel):
@@ -76,6 +112,7 @@ def _save_offer(body: OfferBody, offer: Optional[QuestOffer], world_id: str, db:
             db, world_id=world_id, offer=offer, giver_entity_id=body.giver_entity_id, title=body.title,
             summary=body.summary, repeatable=body.repeatable, status=body.status,
             eligibility=[_spec(r) for r in body.eligibility], steps=steps,
+            terms=None if body.terms is None else [_term(t) for t in body.terms],
         )
     except ValueError as exc:
         db.rollback()
@@ -110,6 +147,31 @@ def save_offer(offer_id: str, body: OfferBody, db: Session = Depends(get_session
     return _save_offer(body, offer, world_id, db)
 
 
+@router.post("/api/quest-offers/value")
+def preview_value(body: ValueBody, db: Session = Depends(get_session)) -> dict:
+    """The editor's live total (C1): no validation, nothing written."""
+    return value_dict(offer_value(db, _crud._world_id(db), [_term(t) for t in body.terms]))
+
+
+@router.get("/api/quest-economy")
+def get_economy(db: Session = Depends(get_session)) -> dict:
+    world_id = _crud._world_id(db)
+    row = db.exec(select(QuestEconomy).where(QuestEconomy.world_id == world_id)).first()
+    stored = {name: getattr(row, name) if row is not None else None for name in ECONOMY_COLUMNS}
+    return {"stored": stored, "effective": world_rates(db, world_id), "defaults": DEFAULT_RATES}
+
+
+@router.put("/api/quest-economy")
+def set_economy(body: EconomyBody, db: Session = Depends(get_session)) -> dict:
+    try:
+        upsert_quest_economy(db, world_id=_crud._world_id(db), values=body.model_dump())
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=422, detail=str(exc)) from exc
+    db.commit()
+    return get_economy(db=db)
+
+
 @router.get("/api/quests")
 def journee_quests(db: Session = Depends(get_session)) -> dict:
     character = _resolve_player_character(_crud._world_id(db), db)
diff --git a/src/world_engine/day_plan.py b/src/world_engine/day_plan.py
index 848e75b..6d5d5e3 100644
--- a/src/world_engine/day_plan.py
+++ b/src/world_engine/day_plan.py
@@ -64,13 +64,12 @@ from .models import (
     QuestOffer,
     Relation,
     Rencontre,
-    SkillDefinition,
 )
 from .prompt_registry import effective_model
 from .prompt_store import current_prompt
 from .prose_render import fact_text, fact_texts
 from .relation_orientation import is_social
-from .skill_access import held_rank
+from .skill_access import held_rank, skill_label
 
 _log = logging.getLogger(__name__)
 
@@ -293,13 +292,6 @@ def _eval_faction_member(req: RequirementSpec, character: Character, db: Session
     )
 
 
-def _skill_label(db: Session, skill_key: Optional[str]) -> str:
-    if skill_key in BASE_SKILL_DOMAINS:
-        return str(skill_key)
-    definition = db.get(SkillDefinition, skill_key) if skill_key else None
-    return definition.name if definition is not None else str(skill_key)
-
-
 def _eval_skill_rank_gte(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
     """`target_key` is a base domain or a skill definition id; the rank held
     is `skill_access.held_rank` (a missing base row is Initié, a missing
@@ -308,7 +300,7 @@ def _eval_skill_rank_gte(req: RequirementSpec, character: Character, db: Session
     rank = held_rank(db, character.id, req.target_key)
     threshold = req.threshold or 0
     met = rank is not None and rank >= threshold
-    label = _skill_label(db, req.target_key)
+    label = skill_label(db, req.target_key)
     current = rank if rank is not None else "not held"
     reason = (
         f"skill {label!r} at rank {rank}, meets requires >= {threshold}" if met
diff --git a/src/world_engine/quest_reads.py b/src/world_engine/quest_reads.py
index 4f38e6e..6a9a7d4 100644
--- a/src/world_engine/quest_reads.py
+++ b/src/world_engine/quest_reads.py
@@ -26,12 +26,16 @@ from .models import (
     Character,
     Entity,
     Fact,
+    Item,
     Quest,
     QuestOffer,
     QuestOfferStep,
     SkillDefinition,
 )
 from .prose_render import fact_texts
+from .quest_value import offer_value, value_dict, world_rates
+from .quest_wording import term_dict, term_line
+from .writes.quest_terms import FACT_REWARD_LEVELS, offer_terms
 from .writes.quests import QUEST_GIVER_TYPES, acceptance_refusal, offer_requirements
 
 # M1: the agenda's status, as the player reads it.
@@ -59,6 +63,7 @@ def offer_dict(offer: QuestOffer, db: Session) -> dict:
     steps with their requirements, in order."""
     steps = db.exec(select(QuestOfferStep).where(QuestOfferStep.offer_id == offer.id)
                     .order_by(QuestOfferStep.step_order)).all()
+    terms = offer_terms(db, offer.id)
     return {
         "id": offer.id, "giver_entity_id": offer.giver_entity_id, "giver_name": _name(db, offer.giver_entity_id),
         "title": offer.title, "summary": offer.summary, "repeatable": offer.repeatable, "status": offer.status,
@@ -67,6 +72,9 @@ def offer_dict(offer: QuestOffer, db: Session) -> dict:
             "objective": step.objective, "cost": step.cost, "domain": step.domain,
             "requirements": [_requirement_dict(r) for r in offer_requirements(db, offer.id, step.id)],
         } for step in steps],
+        # TICKET-0109 (B1, C1): the costs and rewards, and their indicative value.
+        "terms": [term_dict(db, t, offer.giver_entity_id) for t in terms],
+        "value": value_dict(offer_value(db, offer.world_id, terms)),
     }
 
 
@@ -84,8 +92,9 @@ def _named(db: Session, world_id: str, entity_type: str) -> list[dict]:
 
 def editor_choices(world_id: str, db: Session) -> dict:
     """What the offer editor's pickers list: givers, characters, locations,
-    factions, facts (their text), skills (base domains, then definitions)
-    and offers."""
+    factions, facts (their text), skills (base domains, then definitions),
+    offers; items with their value, the fact reward levels and the world's
+    rates (TICKET-0109)."""
     facts = db.exec(select(Fact).where(Fact.world_id == world_id)).all()
     definitions = db.exec(select(SkillDefinition).where(SkillDefinition.world_id == world_id)).all()
     characters = _named(db, world_id, "character")
@@ -101,6 +110,9 @@ def editor_choices(world_id: str, db: Session) -> dict:
         + sorted(({"key": d.id, "label": d.name} for d in definitions), key=lambda d: d["label"].lower()),
         "offers": [{"id": o.id, "title": o.title} for o in world_offers(world_id, db)],
         "giver_types": list(QUEST_GIVER_TYPES),
+        "items": [{**i, "value": db.get(Item, i["id"]).value} for i in _named(db, world_id, "item")],
+        "fact_levels": list(FACT_REWARD_LEVELS),
+        "rates": world_rates(db, world_id),
     }
 
 
@@ -151,6 +163,7 @@ def journee_payload(character: Character, db: Session) -> dict:
     quests. No agenda or step id (checked by `quests.py`)."""
     offers = [{"offer_id": o.id, "title": o.title, "summary": o.summary,
                "giver_name": _name(db, o.giver_entity_id),
+               "terms": [term_line(db, t, o.giver_entity_id) for t in offer_terms(db, o.id)],
                "steps": [s.objective for s in db.exec(select(QuestOfferStep).where(
                    QuestOfferStep.offer_id == o.id).order_by(QuestOfferStep.step_order)).all()]}
               for o in available_offers(character, db)]
diff --git a/src/world_engine/quest_value.py b/src/world_engine/quest_value.py
new file mode 100644
index 0000000..4e22f9f
--- /dev/null
+++ b/src/world_engine/quest_value.py
@@ -0,0 +1,82 @@
+"""The indicative unit of a quest (TICKET-0109, BRIEF-0109-B, C1/E1,
+contract C-03). Reads only.
+
+Every term is worth some units: money 1 a coin, a relation point 1, a fact
+5, a skill 20 (learned, taught, or a reward of points) -- a world changes
+any of them in `quest_economy`; an item is worth its own `value` a piece.
+`offer_value` adds the costs and the rewards and says whether the reward
+lies in the world's band (by default 100 % to 150 % of the cost). The unit
+is a display for the creator, never a currency: nothing converts it.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from typing import Optional
+
+from sqlmodel import Session, select
+
+from .models import Item, QuestEconomy
+
+# The code's defaults (E1); a NULL column of `quest_economy` reads these.
+DEFAULT_RATES: dict[str, int] = {
+    "rate_money": 1, "rate_relation": 1, "rate_fact": 5, "rate_skill": 20,
+    "band_low_pct": 100, "band_high_pct": 150,
+}
+
+# The verdict of a reward against the band, as the editor shows it.
+VERDICT_LABELS: dict[str, str] = {
+    "balanced": "équilibrée", "generous": "généreuse", "meagre": "maigre", "free": "sans coût",
+}
+
+
+@dataclass(frozen=True)
+class OfferValue:
+    cost: int
+    reward: int
+    ratio_pct: Optional[int]
+    band_low_pct: int
+    band_high_pct: int
+    verdict: str
+
+
+def world_rates(db: Session, world_id: str) -> dict[str, int]:
+    """The world's rates, each NULL column or a missing row at its default."""
+    row = db.exec(select(QuestEconomy).where(QuestEconomy.world_id == world_id)).first()
+    return {name: (getattr(row, name) if row is not None and getattr(row, name) is not None else default)
+            for name, default in DEFAULT_RATES.items()}
+
+
+def term_value(db: Session, term, rates: dict[str, int]) -> int:
+    """The units of one term (an offer's or a quest's)."""
+    if term.currency == "money":
+        return (term.amount or 0) * rates["rate_money"]
+    if term.currency == "relation":
+        return (term.amount or 0) * rates["rate_relation"]
+    if term.currency == "fact":
+        return rates["rate_fact"]
+    if term.currency == "skill":
+        return rates["rate_skill"]
+    item = db.get(Item, term.item_id) if term.item_id else None
+    return (term.amount or 0) * (item.value if item is not None else 0)
+
+
+def offer_value(db: Session, world_id: str, terms: list) -> OfferValue:
+    """The two totals, the reward as a percentage of the cost, and the
+    verdict: `free` (no cost), `meagre` (below the band), `generous` (above
+    it), else `balanced`."""
+    rates = world_rates(db, world_id)
+    cost = sum(term_value(db, t, rates) for t in terms if t.direction == "cost")
+    reward = sum(term_value(db, t, rates) for t in terms if t.direction == "reward")
+    low, high = rates["band_low_pct"], rates["band_high_pct"]
+    if cost == 0:
+        return OfferValue(cost, reward, None, low, high, "free")
+    ratio = round(reward * 100 / cost)
+    verdict = "meagre" if ratio < low else "generous" if ratio > high else "balanced"
+    return OfferValue(cost, reward, ratio, low, high, verdict)
+
+
+def value_dict(value: OfferValue) -> dict:
+    return {"cost": value.cost, "reward": value.reward, "ratio_pct": value.ratio_pct,
+            "band_low_pct": value.band_low_pct, "band_high_pct": value.band_high_pct,
+            "verdict": value.verdict, "verdict_label": VERDICT_LABELS[value.verdict]}
diff --git a/src/world_engine/quest_wording.py b/src/world_engine/quest_wording.py
new file mode 100644
index 0000000..340dc4c
--- /dev/null
+++ b/src/world_engine/quest_wording.py
@@ -0,0 +1,58 @@
+"""How a quest term reads, in French (TICKET-0109, BRIEF-0109-B, C-04).
+Reads only.
+
+One line per term, from the character's side: « Donner 10 × Fourrure de
+loup à Garde », « Recevoir 30 pièces de Garde », « La relation de Garde
+envers vous monte de 5 », « Apprendre « Le passage secret » de Garde »,
+« Enseigner « Herboristerie » à Garde ». The counterparty is the term's own
+entity, else the offer's giver.
+"""
+
+from __future__ import annotations
+
+from typing import Optional
+
+from sqlmodel import Session
+
+from .models import Entity, Fact
+from .prose_render import fact_text
+from .skill_access import skill_label
+
+
+def counterparty_id(term, giver_entity_id: str) -> str:
+    return term.counterparty_entity_id or giver_entity_id
+
+
+def _name(db: Session, entity_id: Optional[str]) -> str:
+    entity = db.get(Entity, entity_id) if entity_id else None
+    return entity.name if entity is not None else "?"
+
+
+def term_line(db: Session, term, giver_entity_id: str) -> str:
+    """The French line of one term (an offer's or a quest's)."""
+    who = _name(db, counterparty_id(term, giver_entity_id))
+    cost = term.direction == "cost"
+    if term.currency == "money":
+        return f"Verser {term.amount} pièce(s) à {who}" if cost else f"Recevoir {term.amount} pièce(s) de {who}"
+    if term.currency == "item":
+        item = _name(db, term.item_id)
+        return f"Donner {term.amount} × {item} à {who}" if cost else f"Recevoir {term.amount} × {item} de {who}"
+    if term.currency == "relation":
+        way = "baisse" if cost else "monte"
+        return f"La relation de {who} envers vous {way} de {term.amount}"
+    if term.currency == "fact":
+        fact = db.get(Fact, term.fact_id) if term.fact_id else None
+        text = fact_text(db, fact) if fact is not None else "?"
+        return f"Transmettre « {text} » à {who}" if cost else f"Apprendre « {text} » de {who}"
+    label = skill_label(db, term.skill_key)
+    return f"Enseigner « {label} » à {who}" if cost else f"Progresser en « {label} » (enseigné par {who})"
+
+
+def term_dict(db: Session, term, giver_entity_id: str) -> dict:
+    """The editor's view of one term: its columns and its line."""
+    return {
+        "direction": term.direction, "currency": term.currency,
+        "counterparty_entity_id": term.counterparty_entity_id, "item_id": term.item_id,
+        "fact_id": term.fact_id, "skill_key": term.skill_key, "amount": term.amount, "level": term.level,
+        "line": term_line(db, term, giver_entity_id),
+    }
diff --git a/src/world_engine/skill_access.py b/src/world_engine/skill_access.py
index 5831614..539ceaa 100644
--- a/src/world_engine/skill_access.py
+++ b/src/world_engine/skill_access.py
@@ -91,6 +91,15 @@ def held_rank(db: Session, character_id: str, skill_key: Optional[str]) -> Optio
     return row.rank if row is not None else None
 
 
+def skill_label(db: Session, skill_key: Optional[str]) -> str:
+    """A base domain as is, a skill definition id as its name (TICKET-0108,
+    moved here from `day_plan` at TICKET-0109 for a second reader)."""
+    if skill_key in BASE_SKILL_DOMAINS:
+        return str(skill_key)
+    definition = db.get(SkillDefinition, skill_key) if skill_key else None
+    return definition.name if definition is not None else str(skill_key)
+
+
 def locked_verdict(skill_name: str) -> Verdict:
     """The verdict of a locked skill (B1): no dice were rolled. `domain`
     carries the skill's name, for the verdict event and the MJ rubric."""
diff --git a/src/world_engine/writes/__init__.py b/src/world_engine/writes/__init__.py
index c5675b7..fdd4f1b 100644
--- a/src/world_engine/writes/__init__.py
+++ b/src/world_engine/writes/__init__.py
@@ -40,6 +40,10 @@ Layout, by canon domain:
     pipeline.py         — `batch`/`pass_play` (TICKET-0075, BRIEF-0075-a).
     items.py            — `item_holding`: `write_holding` (TICKET-0109,
                           BRIEF-0109-A).
+    quest_terms.py      — `quest_offer_term`/`quest_term`/`quest_economy`:
+                          `clean_terms`, `write_offer_terms`,
+                          `copy_terms_to_quest`, `upsert_quest_economy`
+                          (TICKET-0109, BRIEF-0109-B).
     quests.py           — `quest_offer`/`quest_offer_step`/
                           `quest_offer_requirement`/`quest`:
                           `write_quest_offer`, `accept_quest`,
@@ -120,6 +124,15 @@ from .knowledge import (
 )
 from .items import write_holding
 from .mentions import bind_mention, dismiss_mention, record_unresolved, resolve_mention
+from .quest_terms import (
+    FACT_REWARD_LEVELS,
+    PERSONAL_CURRENCIES,
+    TermSpec,
+    clean_terms,
+    offer_terms,
+    quest_terms,
+    upsert_quest_economy,
+)
 from .quests import (
     OPEN_QUEST_STATUSES,
     QUEST_GIVER_TYPES,
diff --git a/src/world_engine/writes/quest_terms.py b/src/world_engine/writes/quest_terms.py
new file mode 100644
index 0000000..5b1a225
--- /dev/null
+++ b/src/world_engine/writes/quest_terms.py
@@ -0,0 +1,185 @@
+"""Quest terms: validation and writing (TICKET-0109, BRIEF-0109-B, B1,
+contract C-02).
+
+A term is a cost (what the character gives to settle the quest) or a reward
+(what he receives), in one of five currencies. `clean_term` validates one
+and returns the exact columns a term row takes; `write_offer_terms` replaces
+an offer's terms whole (with its steps, `write_quest_offer`);
+`copy_terms_to_quest` gives an accepted quest its own copy (B1);
+`upsert_quest_economy` writes a world's rates (E1).
+
+The counterparty is the term's own entity, else the offer's giver; for a
+relation, a fact or a skill it must be a character (a faction feels
+nothing, knows nothing, learns nothing). A skill COST is teaching it
+(C-teach1), so it must be a skill definition: every character already holds
+the four base domains. None of these functions commits.
+"""
+
+from __future__ import annotations
+
+from dataclasses import dataclass
+from datetime import UTC, datetime
+from typing import Optional
+
+from sqlalchemy import text
+from sqlmodel import Session, select
+
+from ..models import (
+    BASE_SKILL_DOMAINS,
+    QUEST_TERM_CURRENCIES,
+    QUEST_TERM_DIRECTIONS,
+    Entity,
+    Fact,
+    Item,
+    QuestEconomy,
+    QuestOfferTerm,
+    QuestTerm,
+    SkillDefinition,
+)
+from ..quest_value import DEFAULT_RATES
+from .knowledge import KNOWLEDGE_LEVELS
+
+# The currencies whose counterparty must be a character.
+PERSONAL_CURRENCIES: tuple[str, ...] = ("relation", "fact", "skill")
+# The currencies counted by `amount`.
+COUNTED_CURRENCIES: tuple[str, ...] = ("money", "item", "relation")
+# The largest relation term: an intensity moves within 1-100.
+MAX_RELATION_AMOUNT = 99
+# The knowledge levels a fact reward may give (never `unaware`).
+FACT_REWARD_LEVELS: tuple[str, ...] = tuple(sorted(KNOWLEDGE_LEVELS - {"unaware"}))
+# The columns of a term row, beyond its owner and order.
+TERM_COLUMNS: tuple[str, ...] = (
+    "direction", "currency", "counterparty_entity_id", "item_id", "fact_id", "skill_key", "amount", "level",
+)
+# The economy columns a world may set (E1).
+ECONOMY_COLUMNS: tuple[str, ...] = (
+    "rate_money", "rate_relation", "rate_fact", "rate_skill", "band_low_pct", "band_high_pct",
+)
+
+
+@dataclass(frozen=True)
+class TermSpec:
+    direction: str
+    currency: str
+    counterparty_entity_id: Optional[str] = None
+    item_id: Optional[str] = None
+    fact_id: Optional[str] = None
+    skill_key: Optional[str] = None
+    amount: Optional[int] = None
+    level: Optional[str] = None
+
+
+def _entity_of(db: Session, world_id: str, entity_id: Optional[str], types: tuple[str, ...]) -> Optional[Entity]:
+    entity = db.get(Entity, entity_id) if entity_id else None
+    if entity is None or entity.world_id != world_id or entity.type not in types or entity.status != "active":
+        return None
+    return entity
+
+
+def _clean_target(db: Session, world_id: str, where: str, term: TermSpec) -> dict:
+    """The target columns of `term`'s currency, the others None."""
+    target = {"item_id": None, "fact_id": None, "skill_key": None, "level": None}
+    if term.currency == "item":
+        if _entity_of(db, world_id, term.item_id, ("item",)) is None or db.get(Item, term.item_id) is None:
+            raise ValueError(f"{where}: {term.item_id!r} is not an item of this world")
+        target["item_id"] = term.item_id
+    elif term.currency == "fact":
+        fact = db.get(Fact, term.fact_id) if term.fact_id else None
+        if fact is None or fact.world_id != world_id:
+            raise ValueError(f"{where}: {term.fact_id!r} is not a fact of this world")
+        target["fact_id"] = term.fact_id
+        if term.direction == "reward" and term.level not in (None, *FACT_REWARD_LEVELS):
+            raise ValueError(f"{where}: a fact reward's level is one of {FACT_REWARD_LEVELS}")
+        target["level"] = term.level if term.direction == "reward" else None
+    elif term.currency == "skill":
+        definition = db.get(SkillDefinition, term.skill_key) if term.skill_key else None
+        is_definition = definition is not None and definition.world_id == world_id
+        if term.direction == "cost" and not is_definition:
+            raise ValueError(f"{where}: teaching (a skill cost) needs a skill definition of this world")
+        if not is_definition and term.skill_key not in BASE_SKILL_DOMAINS:
+            raise ValueError(f"{where}: {term.skill_key!r} is not a skill of this world")
+        target["skill_key"] = term.skill_key
+    return target
+
+
+def _clean_amount(where: str, term: TermSpec) -> Optional[int]:
+    if term.currency not in COUNTED_CURRENCIES:
+        return None
+    amount = term.amount
+    if not isinstance(amount, int) or isinstance(amount, bool) or amount < 1:
+        raise ValueError(f"{where}: a {term.currency} term needs an amount of at least 1")
+    if term.currency == "relation" and amount > MAX_RELATION_AMOUNT:
+        raise ValueError(f"{where}: a relation term moves at most {MAX_RELATION_AMOUNT} points")
+    return amount
+
+
+def clean_term(db: Session, world_id: str, giver_entity_id: str, index: int, term: TermSpec) -> dict:
+    """Validate one term against the offer's giver; the row's columns, or
+    `ValueError` (C-02's refusals)."""
+    where = f"term {index + 1}"
+    if term.direction not in QUEST_TERM_DIRECTIONS:
+        raise ValueError(f"{where}: direction must be one of {QUEST_TERM_DIRECTIONS}")
+    if term.currency not in QUEST_TERM_CURRENCIES:
+        raise ValueError(f"{where}: currency must be one of {QUEST_TERM_CURRENCIES}")
+    counterparty = term.counterparty_entity_id or None
+    if counterparty is not None and _entity_of(db, world_id, counterparty, ("character", "faction")) is None:
+        raise ValueError(f"{where}: the counterparty is not an active character or faction of this world")
+    effective = counterparty or giver_entity_id
+    if term.currency in PERSONAL_CURRENCIES and _entity_of(db, world_id, effective, ("character",)) is None:
+        raise ValueError(f"{where}: a {term.currency} term needs a character as counterparty -- name one")
+    return {"direction": term.direction, "currency": term.currency, "counterparty_entity_id": counterparty,
+            **_clean_target(db, world_id, where, term), "amount": _clean_amount(where, term)}
+
+
+def clean_terms(db: Session, world_id: str, giver_entity_id: str, terms: list[TermSpec]) -> list[dict]:
+    """Every term validated before any write (all or nothing)."""
+    return [clean_term(db, world_id, giver_entity_id, i, term) for i, term in enumerate(terms)]
+
+
+def write_offer_terms(db: Session, *, world_id: str, offer_id: str, clean: list[dict]) -> None:
+    """Replace an offer's terms whole (full-replace, the offer's steps' shape)."""
+    db.execute(text("DELETE FROM quest_offer_term WHERE offer_id = :oid"), {"oid": offer_id})
+    for order, columns in enumerate(clean, start=1):
+        db.add(QuestOfferTerm(world_id=world_id, offer_id=offer_id, term_order=order, **columns))
+
+
+def offer_terms(db: Session, offer_id: str) -> list[QuestOfferTerm]:
+    return list(db.exec(select(QuestOfferTerm).where(QuestOfferTerm.offer_id == offer_id)
+                        .order_by(QuestOfferTerm.term_order)).all())
+
+
+def quest_terms(db: Session, quest_id: str) -> list[QuestTerm]:
+    return list(db.exec(select(QuestTerm).where(QuestTerm.quest_id == quest_id)
+                        .order_by(QuestTerm.term_order)).all())
+
+
+def copy_terms_to_quest(db: Session, *, world_id: str, offer_id: str, quest_id: str) -> None:
+    """B1: the accepted quest's own copy, never touched again."""
+    for term in offer_terms(db, offer_id):
+        db.add(QuestTerm(world_id=world_id, quest_id=quest_id, term_order=term.term_order,
+                         **{c: getattr(term, c) for c in TERM_COLUMNS}))
+
+
+def upsert_quest_economy(db: Session, *, world_id: str, values: dict) -> QuestEconomy:
+    """E1: set a world's rates; a None value returns that rate to the code's
+    default. Refuses an unknown column, a negative value, or a band whose low
+    end is above its high end, before any write."""
+    unknown = set(values) - set(ECONOMY_COLUMNS)
+    if unknown:
+        raise ValueError(f"upsert_quest_economy: unknown {sorted(unknown)}")
+    for name, value in values.items():
+        if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
+            raise ValueError(f"upsert_quest_economy: {name} must be a whole number >= 0 or empty")
+    row = db.exec(select(QuestEconomy).where(QuestEconomy.world_id == world_id)).first()
+    merged = {name: (values[name] if name in values else getattr(row, name, None)) for name in ECONOMY_COLUMNS}
+    low = merged["band_low_pct"] if merged["band_low_pct"] is not None else DEFAULT_RATES["band_low_pct"]
+    high = merged["band_high_pct"] if merged["band_high_pct"] is not None else DEFAULT_RATES["band_high_pct"]
+    if low > high:
+        raise ValueError(f"upsert_quest_economy: the band's low end {low} % is above its high end {high} %")
+    if row is None:
+        row = QuestEconomy(world_id=world_id)
+    for name, value in values.items():
+        setattr(row, name, value)
+    row.updated_at = datetime.now(UTC)
+    db.add(row)
+    return row
diff --git a/src/world_engine/writes/quests.py b/src/world_engine/writes/quests.py
index fadd6c4..ddb80ad 100644
--- a/src/world_engine/writes/quests.py
+++ b/src/world_engine/writes/quests.py
@@ -8,7 +8,7 @@ contract C-03).
 - `accept_quest(...)`      : the player takes an offer (B1, A1): one agenda
   born `paused` through `write_agenda`, its steps (the first `active`, the
   creator-agenda precedent) and their requirements copied from the offer,
-  and the `quest` row. Eligibility and L1 are judged HERE, so no caller can
+  the `quest` row, and its own copy of the offer's terms (TICKET-0109, B1). Eligibility and L1 are judged HERE, so no caller can
   skip them.
 - `abandon_quest(...)`     : N1, the quest's agenda to `abandoned` through
   `write_agenda_status`; nothing is deleted.
@@ -44,6 +44,7 @@ from ..models import (
     QuestOfferStep,
 )
 from .goals_agendas import _clean_requirement, write_agenda, write_agenda_status, write_agenda_step
+from .quest_terms import TERM_COLUMNS, TermSpec, clean_terms, copy_terms_to_quest, offer_terms, write_offer_terms
 
 # An offer is given by a character or a faction of the world (H1).
 QUEST_GIVER_TYPES: tuple[str, ...] = ("character", "faction")
@@ -97,10 +98,13 @@ def write_quest_offer(
     status: str,
     eligibility: list[RequirementSpec],
     steps: list[PlanStep],
+    terms: Optional[list[TermSpec]] = None,
 ) -> QuestOffer:
     """Create (`offer` None) or save one offer (C-03). Everything is
     validated before the first write; a `quest_completed` requirement on the
-    offer itself is refused (it could never be met)."""
+    offer itself is refused (it could never be met). `terms` (TICKET-0109,
+    B1) replaces the offer's costs and rewards whole; None keeps them, each
+    re-validated against the giver, who may have changed."""
     if not isinstance(title, str) or not title.strip():
         raise ValueError("write_quest_offer: title is required")
     if status not in QUEST_OFFER_STATUSES:
@@ -111,6 +115,9 @@ def write_quest_offer(
         raise ValueError("write_quest_offer: an offer cannot require its own completion")
     clean_eligibility = [_clean_requirement(db, world_id, -1, req) for req in eligibility]
     clean_steps = _clean_offer_steps(db, world_id, steps)
+    if terms is None:
+        terms = [TermSpec(**{c: getattr(t, c) for c in TERM_COLUMNS}) for t in offer_terms(db, offer.id)] if offer else []
+    clean_term_rows = clean_terms(db, world_id, giver_entity_id, terms)
 
     if offer is None:
         offer = QuestOffer(world_id=world_id, giver_entity_id=giver_entity_id, title=title.strip(), change_history=[])
@@ -136,6 +143,7 @@ def write_quest_offer(
         db.flush()
         for clean in clean_requirements:
             db.add(QuestOfferRequirement(world_id=world_id, offer_id=offer.id, step_id=row.id, **clean))
+    write_offer_terms(db, world_id=world_id, offer_id=offer.id, clean=clean_term_rows)
     return offer
 
 
@@ -195,6 +203,8 @@ def accept_quest(db: Session, *, offer: QuestOffer, character: Character) -> Que
             db.add(AgendaStepRequirement(world_id=offer.world_id, step_id=row.id, **clean))
     quest = Quest(world_id=offer.world_id, offer_id=offer.id, character_id=character.id, agenda_id=agenda.id)
     db.add(quest)
+    db.flush()
+    copy_terms_to_quest(db, world_id=offer.world_id, offer_id=offer.id, quest_id=quest.id)
     return quest
 
 
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 5ffd84a..70b8636 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18159,6 +18159,29 @@ from BRIEF-0109-b on.
 cannot lie in one. A quantity on `item` with one owner (E2 of the series):
 two holders of furs would be two « Fourrure » entities.
 
+
+## A QUEST HAS COSTS AND REWARDS IN FIVE CURRENCIES (TICKET-0109) -- COPIED AT ACCEPTANCE, WEIGHED IN AN INDICATIVE UNIT (BRIEF-0109-b, no schema change)
+
+**B1.** An offer's terms -- each a cost or a reward in money, items,
+relation, a fact or a skill -- are written with the offer and replaced
+whole with its steps; accepting the offer copies them into the quest
+(`quest_term`), so an offer edited later never changes a bargain already
+struck. A term's counterparty is its own entity, else the giver; a
+relation, a fact or a skill needs a character there (a faction feels,
+knows and learns nothing). A skill cost is teaching it (C-teach1), so it
+names a skill definition: every character holds the base domains.
+
+**C1/E1.** The indicative unit weighs a term: a coin 1, a relation point 1,
+a fact 5, a skill 20, an item its own `value` a piece -- each rate set per
+world in `quest_economy`, a missing one at the code's default. The editor
+reads the two totals and whether the reward lies in the world's band
+(default 100-150 % of the cost): « maigre », « équilibrée », « généreuse »,
+or « sans coût ». The unit is never converted, never spent.
+
+**Rejected.** Reading the offer's terms at settlement (B2): an edited offer
+would reprice a bargain. Fixed rates in code (E2): each world has its own
+economy.
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index 107d2c9..29f13a4 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -55,6 +55,10 @@ src/world_engine/writes/goals_agendas.py::write_day_plan       agenda_step_requi
 src/world_engine/writes/quests.py::write_quest_offer           quest_offer quest_offer_step quest_offer_requirement
 # TICKET-0108, BRIEF-0108-B: accept_quest writes the quest row and copies the offer's step requirements; its agenda and steps go through write_agenda/write_agenda_step, allow-listed above (the write_day_plan precedent).
 src/world_engine/writes/quests.py::accept_quest                agenda_step_requirement quest
+# TICKET-0109, BRIEF-0109-B: write_offer_terms replaces an offer's costs and rewards whole (write_quest_offer's full-replace shape); copy_terms_to_quest gives an accepted quest its own copy; upsert_quest_economy sets a world's rates (curated config, upsert-one).
+src/world_engine/writes/quest_terms.py::write_offer_terms      quest_offer_term
+src/world_engine/writes/quest_terms.py::copy_terms_to_quest    quest_term
+src/world_engine/writes/quest_terms.py::upsert_quest_economy   quest_economy
 # TICKET-0044, BRIEF-0044-c: create_entity_type is the 26th site — the governed
 # structural-write authority (D2), a NEW sanctioned site distinct from the two
 # canon-write paths (AI-proposal pipeline, creator CRUD). Its `CREATE TABLE
diff --git a/tooling/verify/checks/quest_rewards.py b/tooling/verify/checks/quest_rewards.py
index 526d48d..c26902f 100644
--- a/tooling/verify/checks/quest_rewards.py
+++ b/tooling/verify/checks/quest_rewards.py
@@ -38,6 +38,27 @@ RA3 -- holdings (fixture). `write_holding` sets and moves a quantity, keeps
    items` and `GET /api/items/{id}/holders` give quantities; `PUT
    /api/item-holdings` sets one and answers 422 on a refusal.
 
+RB1 -- terms (BRIEF-0109-B, fixture). `write_quest_offer` with terms writes
+   them in order; it refuses, with no row written: a direction `gift`, a
+   currency `favour`, money of 0, an item that is not an item, a fact of
+   another world, a relation of 100, a relation, fact or skill term whose
+   counterparty is a faction (the giver a faction, none named), a skill cost
+   on a base domain, a fact reward at `unaware`, a counterparty location.
+   Saving with `terms=None` keeps the terms; with `[]` removes them.
+RB2 -- acceptance copies (fixture, B1). An accepted quest holds a copy of
+   the offer's terms; editing the offer afterwards changes the offer's
+   terms, not the quest's.
+RB3 -- the indicative unit (fixture, C1/E1). With no economy row the rates
+   are `DEFAULT_RATES`; an offer costing 10 coins and 2 furs of value 3 (16)
+   and rewarding a fact and 5 relation points (10) reads 62 % `meagre`;
+   rewarding 20 coins instead reads 125 % `balanced`; 30 coins 188 %
+   `generous`; no cost `free`. `upsert_quest_economy` sets `rate_fact` 20
+   (the fact reward now reads 20), refuses -1, an unknown column and a band
+   of 160-150; a None returns a rate to its default. `term_line` reads
+   « Donner 2 × Fourrure de loup à Garde » and « La relation de Garde envers
+   vous monte de 5 ». The routes `preview_value`, `get_economy`,
+   `set_economy` answer the same numbers and 422 on a refusal.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
@@ -401,6 +422,209 @@ def check_ra3(engine) -> None:
         _ra3_routes(session, ids)
 
 
+# --- RB --------------------------------------------------------------------------
+
+def _rb_world(session) -> dict:
+    from world_engine.models import Character, Entity, Fact, Faction, Item, Location, World
+
+    worlds = []
+    for name in ("Quest rewards RB", "Other RB"):
+        world = World(name=name, is_active=False)
+        session.add(world)
+        session.flush()
+        worlds.append(world.id)
+    ids = {"world": worlds[0]}
+    for key, kind, name in (("pc", "character", "Millys"), ("npc", "character", "Garde"),
+                            ("guild", "faction", "Guilde"), ("place", "location", "Port"),
+                            ("fur", "item", "Fourrure de loup")):
+        row = Entity(world_id=worlds[0], type=kind, name=name)
+        session.add(row)
+        session.flush()
+        ids[key] = row.id
+    session.add_all([Character(id=ids["pc"], world_id=worlds[0], character_type="player"),
+                     Character(id=ids["npc"], world_id=worlds[0], character_type="npc"),
+                     Faction(id=ids["guild"]), Location(id=ids["place"]), Item(id=ids["fur"], value=3)])
+    fact = Fact(world_id=worlds[0], content_raw="Le passage secret", created_by="check")
+    alien = Fact(world_id=worlds[1], content_raw="Ailleurs", created_by="check")
+    session.add_all([fact, alien])
+    session.commit()
+    ids.update(fact=fact.id, alien_fact=alien.id)
+    return ids
+
+
+def _offer(ids: dict, **over) -> dict:
+    from world_engine.day_plan import PlanStep
+
+    base = dict(world_id=ids["world"], offer=None, giver_entity_id=ids["npc"], title="La fourrure",
+                summary=None, repeatable=False, status="open", eligibility=[],
+                steps=[PlanStep(objective="Chasser", cost=1, domain=None)])
+    base.update(over)
+    return base
+
+
+def _rb_terms(ids: dict) -> list:
+    from world_engine.writes import TermSpec
+
+    return [TermSpec(direction="cost", currency="money", amount=10),
+            TermSpec(direction="cost", currency="item", item_id=ids["fur"], amount=2),
+            TermSpec(direction="reward", currency="fact", fact_id=ids["fact"]),
+            TermSpec(direction="reward", currency="relation", amount=5)]
+
+
+def _rb1_refusals(session, ids) -> None:
+    from sqlmodel import func, select
+
+    from world_engine.models import QuestOffer, QuestOfferTerm
+    from world_engine.writes import TermSpec, write_quest_offer
+
+    bad = {
+        "a direction gift": [TermSpec(direction="gift", currency="money", amount=1)],
+        "a currency favour": [TermSpec(direction="cost", currency="favour", amount=1)],
+        "money of 0": [TermSpec(direction="cost", currency="money", amount=0)],
+        "an item that is not an item": [TermSpec(direction="cost", currency="item", item_id=ids["npc"], amount=1)],
+        "a fact of another world": [TermSpec(direction="reward", currency="fact", fact_id=ids["alien_fact"])],
+        "a relation of 100": [TermSpec(direction="reward", currency="relation", amount=100)],
+        "a skill cost on a base domain": [TermSpec(direction="cost", currency="skill", skill_key="agility")],
+        "a fact reward at unaware": [TermSpec(direction="reward", currency="fact", fact_id=ids["fact"], level="unaware")],
+        "a counterparty location": [TermSpec(direction="cost", currency="money", amount=1,
+                                             counterparty_entity_id=ids["place"])],
+    }
+    cases = [(label, _offer(ids, terms=terms)) for label, terms in bad.items()]
+    cases.append(("a relation term owed by a faction",
+                  _offer(ids, giver_entity_id=ids["guild"],
+                         terms=[TermSpec(direction="reward", currency="relation", amount=3)])))
+    for label, kwargs in cases:
+        before = [session.exec(select(func.count()).select_from(m)).one() for m in (QuestOffer, QuestOfferTerm)]
+        try:
+            write_quest_offer(session, **kwargs)
+        except ValueError:
+            session.rollback()
+            after = [session.exec(select(func.count()).select_from(m)).one() for m in (QuestOffer, QuestOfferTerm)]
+            if after != before:
+                fail(f"RB1: a refused offer ({label}) wrote rows")
+            continue
+        session.rollback()
+        fail(f"RB1: write_quest_offer accepts {label}")
+
+
+def check_rb1(session, ids) -> None:
+    from world_engine.writes import offer_terms, write_quest_offer
+
+    _rb1_refusals(session, ids)
+    offer = write_quest_offer(session, **_offer(ids, terms=_rb_terms(ids)))
+    session.commit()
+    ids["offer"] = offer.id
+    got = [(t.term_order, t.direction, t.currency) for t in offer_terms(session, offer.id)]
+    if got != [(1, "cost", "money"), (2, "cost", "item"), (3, "reward", "fact"), (4, "reward", "relation")]:
+        fail(f"RB1: the written terms are {got}")
+    write_quest_offer(session, **_offer(ids, offer=offer, title="La fourrure du loup"))
+    session.commit()
+    if len(offer_terms(session, offer.id)) != 4:
+        fail("RB1: saving with terms=None did not keep the terms")
+
+
+def check_rb2(session, ids) -> None:
+    from world_engine.models import Character, QuestOffer
+    from world_engine.writes import TermSpec, accept_quest, offer_terms, quest_terms, write_quest_offer
+
+    offer = session.get(QuestOffer, ids["offer"])
+    quest = accept_quest(session, offer=offer, character=session.get(Character, ids["pc"]))
+    session.commit()
+    ids["quest"] = quest.id
+    copied = [(t.direction, t.currency, t.amount) for t in quest_terms(session, quest.id)]
+    if copied != [(t.direction, t.currency, t.amount) for t in offer_terms(session, offer.id)] or len(copied) != 4:
+        fail(f"RB2: the quest's terms are {copied}")
+    write_quest_offer(session, **_offer(ids, offer=offer, terms=[TermSpec(direction="reward", currency="money", amount=1)]))
+    session.commit()
+    if len(offer_terms(session, offer.id)) != 1 or len(quest_terms(session, quest.id)) != 4:
+        fail("RB2: editing the offer changed the accepted quest's terms, or did not change the offer's")
+    write_quest_offer(session, **_offer(ids, offer=offer, terms=[]))
+    session.commit()
+    if offer_terms(session, offer.id):
+        fail("RB1: saving with terms=[] did not remove the terms")
+
+
+def _rb3_values(session, ids) -> None:
+    from world_engine.quest_value import DEFAULT_RATES, offer_value, world_rates
+    from world_engine.writes import TermSpec
+
+    if world_rates(session, ids["world"]) != DEFAULT_RATES:
+        fail(f"RB3: the default rates are {world_rates(session, ids['world'])}")
+    terms = _rb_terms(ids)
+    cases = [(terms, (16, 10, 62, "meagre")),
+             (terms[:2] + [TermSpec(direction="reward", currency="money", amount=20)], (16, 20, 125, "balanced")),
+             (terms[:2] + [TermSpec(direction="reward", currency="money", amount=30)], (16, 30, 188, "generous")),
+             (terms[2:], (0, 10, None, "free"))]
+    for case_terms, expected in cases:
+        v = offer_value(session, ids["world"], case_terms)
+        if (v.cost, v.reward, v.ratio_pct, v.verdict) != expected:
+            fail(f"RB3: value is {(v.cost, v.reward, v.ratio_pct, v.verdict)}, expected {expected}")
+
+
+def _rb3_economy(session, ids) -> None:
+    from world_engine.quest_value import DEFAULT_RATES, offer_value, world_rates
+    from world_engine.writes import upsert_quest_economy
+
+    upsert_quest_economy(session, world_id=ids["world"], values={"rate_fact": 20})
+    session.commit()
+    if offer_value(session, ids["world"], _rb_terms(ids)).reward != 25:
+        fail("RB3: rate_fact 20 is not read")
+    for bad in ({"rate_fact": -1}, {"rate_gold": 2}, {"band_low_pct": 160}):
+        try:
+            upsert_quest_economy(session, world_id=ids["world"], values=bad)
+            fail(f"RB3: upsert_quest_economy accepts {bad}")
+        except ValueError:
+            session.rollback()
+    upsert_quest_economy(session, world_id=ids["world"], values={"rate_fact": None})
+    session.commit()
+    if world_rates(session, ids["world"])["rate_fact"] != DEFAULT_RATES["rate_fact"]:
+        fail("RB3: a None rate does not return to the default")
+
+
+def _rb3_wording_and_routes(session, ids) -> None:
+    from fastapi import HTTPException
+    from sqlmodel import select
+
+    from world_engine.cockpit.routes import quests as routes
+    from world_engine.models import World
+    from world_engine.quest_wording import term_line
+
+    terms = _rb_terms(ids)
+    lines = [term_line(session, terms[1], ids["npc"]), term_line(session, terms[3], ids["npc"])]
+    if lines != ["Donner 2 × Fourrure de loup à Garde", "La relation de Garde envers vous monte de 5"]:
+        fail(f"RB3: the term lines are {lines}")
+    for world in session.exec(select(World).where(World.is_active == True)).all():  # noqa: E712
+        world.is_active = False
+        session.add(world)
+    session.flush()
+    session.get(World, ids["world"]).is_active = True
+    session.commit()
+    body = routes.ValueBody(terms=[routes.TermBody(**{k: v for k, v in t.__dict__.items()}) for t in terms])
+    if routes.preview_value(body, db=session)["ratio_pct"] != 62:
+        fail("RB3: POST /api/quest-offers/value disagrees")
+    economy = routes.set_economy(routes.EconomyBody(rate_skill=30), db=session)
+    if economy["effective"]["rate_skill"] != 30 or economy["stored"]["rate_skill"] != 30:
+        fail(f"RB3: PUT /api/quest-economy gives {economy}")
+    try:
+        routes.set_economy(routes.EconomyBody(band_low_pct=200), db=session)
+        fail("RB3: PUT /api/quest-economy accepts a band of 200-150")
+    except HTTPException as exc:
+        if exc.status_code != 422:
+            fail(f"RB3: PUT /api/quest-economy refusal answers {exc.status_code}")
+
+
+def check_rb(engine) -> None:
+    from sqlmodel import Session
+
+    with Session(engine) as session:
+        ids = _rb_world(session)
+        check_rb1(session, ids)
+        check_rb2(session, ids)
+        _rb3_values(session, ids)
+        _rb3_economy(session, ids)
+        _rb3_wording_and_routes(session, ids)
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_ra1()
@@ -408,13 +632,16 @@ def main() -> int:
     from world_engine.db import create_db_and_tables, engine
     create_db_and_tables()
     check_ra3(engine)
+    check_rb(engine)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
         return 1
     print("PASS: quest_rewards -- v2.18 makes an item a kind held in quantity by any entity, "
           "migrates owners and places to holdings from v2.17 only, drops equipped, and one writer "
-          "keeps every holding, its history, and zones empty")
+          "keeps every holding, its history, and zones empty; an offer's terms are validated whole, "
+          "copied to the quest that accepts it, and valued in the world's indicative unit against "
+          "its band")
     return 0
 
 
diff --git a/tooling/verify/checks/single_canon_write.py b/tooling/verify/checks/single_canon_write.py
index dd42503..ea54b1d 100644
--- a/tooling/verify/checks/single_canon_write.py
+++ b/tooling/verify/checks/single_canon_write.py
@@ -77,8 +77,9 @@ and `write_faction_role(mode="delete")` (blocked while an active membership
 holds the role) — creator-CRUD-only, never reachable from any AI or play
 path. Full-replace config deletes (whole-set replace, not
 single-row correction): `write_npc_prices`, `write_world_laws`,
-`write_location_obstacles`, `write_location_doors` and `write_quest_offer`
-(TICKET-0108, BRIEF-0108-B: an offer's steps and requirements) each
+`write_location_obstacles`, `write_location_doors`, `write_quest_offer`
+(TICKET-0108, BRIEF-0108-B: an offer's steps and requirements) and
+`write_offer_terms` (TICKET-0109, BRIEF-0109-B: an offer's terms) each
 `DELETE FROM` their table(s) scoped to one parent (NPC / world / location /
 location / offer) then re-insert the submitted set, in one transaction —
 creator-CRUD and world-bootstrap only (`set_npc_prices`, `create_world`,
````

## Scope OUT

- Applying a term, checking whether a cost can be paid, `settled_at` (C).
- Any frontend file (D).
- Terms on an accepted quest edited after acceptance (B1: never).
- A separate rate for skill points (a skill term is worth `rate_skill`, flat).
- Debts and services as a currency (TICKET-0110); artifacts.
- Every later brief of this lot.

## Invariants to defend

**Two canon-write paths:** the offer's terms and the world's rates are creator CRUD through `writes/quest_terms.py`, allow-listed by function; the copy at acceptance is part of the creator-direct `accept_quest`. **History is sacred:** an offer save snapshots the offer as in 0108; the offer's terms are the named full-replace exception (`write_offer_terms`); an accepted quest's terms are never rewritten. **The schema is authoritative:** no schema change; the CHECK texts are A's, unchanged. **The player never sees the agenda:** the new Journée lines name no `agenda_id` or `step_id`.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- An existing caller of `write_quest_offer` (E2) would change meaning.
- `routes/quests.py` is not exactly 210 lines after the commit.

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
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/quest_rewards.py` -> `PASS: quest_rewards -- v2.18 makes an item a kind held in quantity by any entity, migrates owners and places to holdings from v2.17 only, drops equipped, and one writer keeps every holding, its history, and zones empty; an offer's terms are validated whole, copied to the quest that accepts it, and valued in the world's indicative unit against its band`.
- `quests.py`, `day_plan.py`, `single_canon_write.py`, `module_budget.py`, `function_length.py`, `undefined_names.py`, `pipeline_state.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted: in `clean_term`, `    if term.currency in PERSONAL_CURRENCIES and _entity_of(db, world_id, effective, ("character",)) is None:` -> `    if False:` -> `RB1`; in `accept_quest`, `    copy_terms_to_quest(db, world_id=offer.world_id, offer_id=offer.id, quest_id=quest.id)` -> `    pass` -> `RB2`; in `offer_value`, `    verdict = "meagre" if ratio < low else "generous" if ratio > high else "balanced"` -> `    verdict = "balanced"` -> `RB3`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 142/142.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `A QUEST HAS COSTS AND REWARDS IN FIVE CURRENCIES (TICKET-0109) -- COPIED AT ACCEPTANCE, WEIGHED IN AN INDICATIVE UNIT (BRIEF-0109-b, no schema change)`; `single_canon_write.py`'s full-replace list — all in the diff. No schema change, no CLAUDE.md change.
