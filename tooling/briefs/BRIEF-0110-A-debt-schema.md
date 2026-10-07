# BRIEF 0110-A — "Debt tables, two debt requirement forms, an offer's contact; the relation type `debt` retired, schema v2.19"

Lot: LOT-0110-debts-services.md (authoritative on conflict)
Depends on: nothing in this lot

## Anchors to confirm (Mini-RECON)

Halt if any has moved (on `main` at `42f2310` or later; the lot's line numbers are `main`'s).

- `src/world_engine/schema_version.py:15` -> `EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.18"`
- `world-engine-schema.md:3` -> `Current schema version: v2.18`
- `src/world_engine/day_plan.py:84` -> `REQUIREMENT_TYPES: tuple[str, ...] = (`
- `src/world_engine/day_plan.py:96` -> `ENTITY_TARGET_TYPES: tuple[str, ...] = ("relation_gte", "location_reachable", "has_met", "faction_member")`
- `src/world_engine/day_plan.py:337` -> `_EVALUATORS: dict[str, Callable[[RequirementSpec, Character, Session, object], Verdict]] = {`
- `src/world_engine/models/config.py:135` -> `name="ck_agenda_step_requirement_type",`
- `src/world_engine/models/quests.py:93` -> `name="ck_quest_offer_requirement_type",`
- `src/world_engine/models/quests.py:222` -> `class QuestEconomy(SQLModel, table=True):`
- `src/world_engine/writes/goals_agendas.py:607` -> `_TARGET_ENTITY_TYPE: dict[str, Optional[str]] = {`
- `src/world_engine/day_resolve.py:260` -> `_BLOCKED_DETAIL_FR: dict[str, str] = {`
- `src/world_engine/cockpit/crud/_shared.py:144` -> `"ally", "enemy", "debt", "fear", "fascination", "shared_secret",`
- `src/world_engine/link_author.py:73` -> `"ally", "enemy", "debt", "fear", "fascination", "shared_secret",`
- `scripts/seed_pilot.py:1656` -> `{"kind":"relation","type":<one of: ally, enemy, debt, fear, fascination, \`
- `src/world_engine/writes/relations.py:361` -> `if mode not in ("delta", "set"):`
- `src/world_engine/quest_value.py:22` -> `DEFAULT_RATES: dict[str, int] = {`
- `src/world_engine/writes/quest_terms.py:55` -> `ECONOMY_COLUMNS: tuple[str, ...] = (`
- `src/world_engine/cockpit/routes/quests.py:88` -> `class EconomyBody(BaseModel):`
- `frontend/src/creation/QuestOffers.svelte:34` -> `const RATE_LABELS = {`
- `tooling/verify/checks/quests.py:105` -> `CREATOR_FORMS = ("has_met", "faction_member", "skill_rank_gte", "quest_completed")`
- `tooling/verify/checks/day_plan.py:192` -> `EXPECTED_REQUIREMENT_TYPES = (`
- No `scripts/migrate_v2_19_debts.py` exists.
- No `tooling/verify/checks/debts.py` exists.

## Facts carried

### R-01 — a relation's type is a free label on one row per oriented pair [M]
Opened: `src/world_engine/models/canon_knowledge.py:23-63` (`Relation`:
`type` TEXT, no CHECK on it; `idx_relation_oriented_social` `:37-40`, at
most one social row per `(entity_a_id, entity_b_id)`);
`src/world_engine/cockpit/crud/_shared.py:143-154` (`RELATION_TYPES`, the
fiche's `datalist` suggestions: `debt` among them).
Finding: the type is a label, suggested not enforced; a pair has one social
row, so a « debt » type would replace whatever the pair already is.
Consequence: I2 -- the table is the one home of a debt; the type is
retired from the suggestions and refused by the writer (C-02).

### R-02 — the model can write a `debt` link, and its prompt offers it [M]
Opened: `src/world_engine/link_author.py:72-78` (`_LINK_RELATION_TYPES`,
`debt` among them), `:274-275` (a type outside it is rejected);
`scripts/seed_pilot.py:1648-1659` (`NPC_LINK_PAIR_USER_TEMPLATE` lists
`ally, enemy, debt, fear, …`), `:2860-2870` (head `pt-npc-link-pair`,
variables `world_name, a_sheet, b_sheet, shared_context`);
`tooling/verify/checks/prompt_version.py:5-8` (the seed never touches text
once a head has a version; `prompt_store`/`write_prompt_version` is the
one path); `scripts/apply_ticket_0097_fact_code_prompts.py` (the delivery
precedent: a new `prompt_version` through `write_prompt_version`).
Consequence: `debt` leaves `_LINK_RELATION_TYPES` and the seed; the live
head loses it through `scripts/apply_ticket_0110_link_prompt.py`, which
edits the CURRENT head's text (one fragment) so a creator edit is kept.

### R-03 — `relation_gte` reads the pair's intensity, whatever its type [M]
Opened: `src/world_engine/day_plan.py:189-217` (`_eval_relation_gte`: the
social row target -> character, `is_social`, any type).
Consequence: retiring a type changes no requirement verdict.

### R-07 — the requirement vocabulary and every place that mirrors it [M]
Opened: `src/world_engine/day_plan.py:84-98` (`REQUIREMENT_TYPES`,
`MODEL_REQUIREMENT_TYPES`, the three shape groups), `:337-346`
(`_EVALUATORS`), `:379-400` (`evaluate_specs`: an unknown type raises),
`:545-561` (`_validate_requirement`: the model's four only, `:549`);
`src/world_engine/models/config.py:133-144` and
`src/world_engine/models/quests.py:91-103` (the two CHECK pairs, byte for
byte); `src/world_engine/writes/goals_agendas.py:607-609`
(`_TARGET_ENTITY_TYPE`, one type or None), `:631-675`
(`_clean_requirement`); `src/world_engine/day_resolve.py:260-270`
(`_BLOCKED_DETAIL_FR`); `frontend/src/creation/questRequirements.js:10-19`
(`REQUIREMENT_FORMS`); `tooling/verify/checks/quests.py:104-105`, `:153`,
`:180` (QA1), `:797-805` (QC1); `tooling/verify/checks/day_plan.py:
192-195` (R2), `:356-368` (R3); `tooling/verify/checks/day_narration.py:
651-682` (R15).
Consequence: the two forms land in every mirror in one commit (A); the
target is a character or a faction, so `_TARGET_ENTITY_TYPE` takes a tuple
of types (C-02).

### R-09 — the economy: defaults, columns, and a PUT that writes them all [M]
Opened: `src/world_engine/quest_value.py:22-25` (`DEFAULT_RATES`), `:43-47`
(`world_rates`: one key per default), `:50-61` (`term_value`);
`src/world_engine/writes/quest_terms.py:55-57` (`ECONOMY_COLUMNS`),
`:163-185` (`upsert_quest_economy`: every key it receives is written);
`src/world_engine/cockpit/routes/quests.py:88-94` (`EconomyBody`), `:168-
175` (`set_economy`: `body.model_dump()`, so a column absent from the body
is written None); `frontend/src/creation/QuestOffers.svelte:34-37`
(`RATE_LABELS`, the ⚖ panel's fields); `src/world_engine/models/quests.py:
222-243` (`QuestEconomy`: no `change_history`).
Consequence: the two debt settings join `DEFAULT_RATES`,
`ECONOMY_COLUMNS`, `EconomyBody` and `RATE_LABELS` in the same commit, or
saving the rates would erase them (A).

### R-14 — the migration's shape, and the governance a schema touches [M]
Opened: `scripts/migrate_v2_17_quests.py:103-114` (rebuild from the model),
`:118-149` (`_apply_ddl`: one raw transaction, `foreign_keys` OFF and
`legacy_alter_table` ON before `BEGIN`); `scripts/migrate_v2_18_quest_terms.py:
69` (the FK post-check scoped to the tables written), `:154` (`ALTER TABLE
… ADD COLUMN` precedent); the v2.18 DDL of `agenda_step_requirement`,
`quest_offer_requirement`, `quest_economy` and `quest_offer`, dumped from
`main` (embedded in `debts.py`); `src/world_engine/schema_version.py:15`;
`world-engine-schema.md:3`; `src/world_engine/writes/worlds.py:66-79`;
`tooling/verify/checks/world_cascade.py:150-207`;
`tooling/verify/canon_write_policy.txt:4-9` (`[CANON_TABLES]`);
`tooling/verify/checks/module_budget.py:57-58` (40 functions and 1000
lines per `src/` module -- not « 40 modules »);
`tooling/verify/checks/corpus_gate.py:53` (15 s per check);
`tooling/verify/checks/decisions_index.py:15-17` (strict header);
`CLAUDE.md` (37 838 characters of 38 000).
Consequence: A follows the v2.17 shape; no JSON column is added (no
`json_ui_boundary` entry); no CLAUDE.md change.

### R-15 — the engine keeps no world time [M]
Opened: `src/world_engine/models/pipeline.py:30-56` (`Batch`;
`day_number` `:44`, `max + 1` per SESSION `:40`, unique per session
`:33`); `grep -rn "world_day" src/world_engine/models` ->
nothing.
Consequence: H1 -- the erosion of an unpaid debt waits for a world-level
day counter: its reactivation is `grep -rn "world_day"
src/world_engine/models` returning a column.

## Contracts

### C-01 — schema v2.19
Produced by: BRIEF-0110-A   Consumed by: B, C, D
- `debt(id, world_id -> world, debtor_entity_id -> entity NOT NULL,
  creditor_entity_id -> entity NOT NULL, contact_entity_id -> entity,
  origin, origin_quest_id -> quest, reason, is_secret BOOLEAN NOT NULL
  DEFAULT 0, fact_id -> fact NOT NULL, status NOT NULL DEFAULT 'open',
  created_at, closed_at, closed_note)`, CHECKs byte for byte:
  ```
  ck_debt_origin        origin IN ('service','quest','creator')
  ck_debt_status        status IN ('open','settled','forgiven')
  ck_debt_parties       debtor_entity_id <> creditor_entity_id
  ck_debt_origin_quest  (origin = 'quest') = (origin_quest_id IS NOT NULL)
  ck_debt_closed        (status = 'open') = (closed_at IS NULL)
  ```
  indexes on `world_id`, `debtor_entity_id`, `creditor_entity_id`.
- `debt_term(id, world_id, debt_id -> debt, term_order, currency, item_id
  -> item, fact_id -> fact, skill_key, amount)`, CHECKs:
  ```
  ck_debt_term_currency currency IN ('money','item','fact','skill')
  ck_debt_term_shape    (currency NOT IN ('money','item') OR (amount IS NOT NULL AND amount >= 1)) AND (currency <> 'item' OR item_id IS NOT NULL) AND (currency <> 'fact' OR fact_id IS NOT NULL) AND (currency <> 'skill' OR skill_key IS NOT NULL)
  ```
  index on `debt_id`.
- `quest_offer.contact_entity_id -> entity` (nullable).
- `quest_economy.debt_fact_relation`, `.debt_skill_relation` (each NULL or
  >= 0, in `ck_quest_economy_rates`).
- Both requirement CHECK pairs gain `'has_debt_to','no_debt_to'` in the type
  list and in the `target_entity_id` group.
- `models.DEBT_ORIGINS`, `DEBT_STATUSES`, `DEBT_CURRENCIES` quote those
  CHECKs, in order.

### C-02 — the vocabulary
Produced by: BRIEF-0110-A   Consumed by: B, C
- `day_plan.REQUIREMENT_TYPES` = the eight, then `has_debt_to`,
  `no_debt_to`; both in `ENTITY_TARGET_TYPES`; neither in
  `THRESHOLD_TYPES` nor `MODEL_REQUIREMENT_TYPES`. Verdicts: case table
  (b-6). French detail: « il ne doit rien à {required} », « il a encore une
  dette envers {required} ».
- `writes.goals_agendas._TARGET_ENTITY_TYPE`: values are `None` or a tuple
  of entity types; the two debt forms take `("character", "faction")`.
- `frontend/src/creation/questRequirements.js`: `has_debt_to` « A une dette
  envers », `no_debt_to` « N’a aucune dette envers », both `list:
  'givers'`, `column: 'entity'`, `threshold: false`; `targetOptions` lists
  `choices.givers`.
- `relation_orientation.RETIRED_RELATION_TYPES = ("debt",)`;
  `write_relation` raises `ValueError` on a retired type, before any write;
  `debt` leaves `crud._shared.RELATION_TYPES`,
  `link_author._LINK_RELATION_TYPES` and the seeded link-pair prompt.
- `quest_value.DEFAULT_RATES` gains `debt_fact_relation: 10`,
  `debt_skill_relation: 20`; `writes.quest_terms.ECONOMY_COLUMNS`,
  `routes.quests.EconomyBody` and the ⚖ panel's `RATE_LABELS` list both.

## Case tables carried (lot, gate output (b))

**b-6 — the debt forms** (C the character, T the target):

| state | `has_debt_to` | `no_debt_to` |
|---|---|---|
| C debtor of an `open` debt toward T | met | not met |
| C's debts toward T all `settled`/`forgiven`, or none | not met | met |
| only debts toward others, or debts T owes C | not met | met |

## Context

TICKET-0109 settled quests in five currencies. This lot adds debts. This brief lays them: the two tables, the offer's contact, the economy's two debt settings, and the two requirement forms that judge a debt -- with their evaluators, because three existing gates bind the vocabulary to its evaluators in one commit. It retires the relation type `debt` (I2): from now on a debt is a row and nothing else. No writer of debts yet: B writes them.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. The generated `tooling/standards/DECISIONS_INDEX.md`
and the built `src/world_engine/cockpit/static/` are not in the diff: regenerate them as listed.

1. Apply the embedded diff. It:
   - `models/quests.py`: `Debt`, `DebtTerm`, `DEBT_ORIGINS`, `DEBT_STATUSES`, `DEBT_CURRENCIES` (C-01), `QuestOffer.contact_entity_id`, `QuestEconomy.debt_fact_relation`/`debt_skill_relation` in `ck_quest_economy_rates`; the requirement CHECKs widened in `models/quests.py` and `models/config.py`; exports in `models/__init__.py`;
   - `day_plan.py`: the two forms, `_open_debt`, `_eval_has_debt_to`, `_eval_no_debt_to` (b-6); `day_resolve.py`: their French detail; `writes/goals_agendas.py`: `_TARGET_ENTITY_TYPE` takes a tuple; `questRequirements.js`: the two forms on the `givers` list (C-02);
   - I2: `relation_orientation.RETIRED_RELATION_TYPES`, `writes/relations._refuse_retired_type` called first in `write_relation`; `debt` out of `crud/_shared.RELATION_TYPES`, `link_author._LINK_RELATION_TYPES` and the seeded link-pair template; creates `scripts/apply_ticket_0110_link_prompt.py`;
   - the economy: `DEFAULT_RATES`, `ECONOMY_COLUMNS`, `EconomyBody`, `RATE_LABELS` (R-09);
   - creates `scripts/migrate_v2_19_debts.py`; `schema_version.py` v2.19; the schema doc and changelog; `debt`/`debt_term` in the world cascade, its fixture and `[CANON_TABLES]`;
   - extends `quests.py` (QA1's `DEBT_FORMS`) and `day_plan.py` (R2, R3); creates `debts.py` (DA1-DA3);
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - frontend/src/creation/QuestOffers.svelte
   - frontend/src/creation/questRequirements.js
   - scripts/apply_ticket_0110_link_prompt.py
   - scripts/migrate_v2_19_debts.py
   - scripts/seed_pilot.py
   - src/world_engine/cockpit/crud/_shared.py
   - src/world_engine/cockpit/routes/quests.py
   - src/world_engine/day_plan.py
   - src/world_engine/day_resolve.py
   - src/world_engine/link_author.py
   - src/world_engine/models/__init__.py
   - src/world_engine/models/config.py
   - src/world_engine/models/quests.py
   - src/world_engine/quest_value.py
   - src/world_engine/relation_orientation.py
   - src/world_engine/schema_version.py
   - src/world_engine/writes/goals_agendas.py
   - src/world_engine/writes/quest_terms.py
   - src/world_engine/writes/relations.py
   - src/world_engine/writes/worlds.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/canon_write_policy.txt
   - tooling/verify/checks/day_plan.py
   - tooling/verify/checks/debts.py
   - tooling/verify/checks/quests.py
   - tooling/verify/checks/world_cascade.py
   - world-engine-schema-changelog.md
   - world-engine-schema.md
2. Rebuild the frontend: `cd frontend && npm run build` (commit `src/world_engine/cockpit/static/`).
3. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
4. Commit message: `feat(debts): debt tables, two debt requirement forms, an offer's contact; the relation type debt retired, schema v2.19 (BRIEF-0110-a)`.

````diff
diff --git a/frontend/src/creation/QuestOffers.svelte b/frontend/src/creation/QuestOffers.svelte
index 4171852..d1df013 100644
--- a/frontend/src/creation/QuestOffers.svelte
+++ b/frontend/src/creation/QuestOffers.svelte
@@ -31,9 +31,12 @@
   let value = $derived(questOffersState.value);
 
   // TICKET-0109 (E1): the world's rates; '' = the code's default.
+  // TICKET-0110: the two debt settings, in relation points.
   const RATE_LABELS = {
     rate_money: 'Pièce', rate_relation: 'Point de relation', rate_fact: 'Fait', rate_skill: 'Compétence',
     band_low_pct: 'Bande basse (%)', band_high_pct: 'Bande haute (%)',
+    debt_fact_relation: 'Dette : fait déjà su (relation −)',
+    debt_skill_relation: 'Dette : compétence déjà connue (relation −)',
   };
   let showEconomy = $state(false);
   let economyDraft = $state({});
diff --git a/frontend/src/creation/questRequirements.js b/frontend/src/creation/questRequirements.js
index 89a9a9c..c64079c 100644
--- a/frontend/src/creation/questRequirements.js
+++ b/frontend/src/creation/questRequirements.js
@@ -1,11 +1,12 @@
-/* TICKET-0108 (BRIEF-0108-C). The eight requirement forms as the offer
+/* TICKET-0108 (BRIEF-0108-C). The requirement forms as the offer
    editor shows them: a French label, the picker list its target comes
    from (a key of GET /api/quest-offers/choices, or 'money'), whether that
    target is an entity (`target_entity_id`) or a key (`target_key`), and
    whether it takes a threshold. Mirrors `day_plan.REQUIREMENT_TYPES`,
    `ENTITY_TARGET_TYPES`, `KEY_TARGET_TYPES` and `THRESHOLD_TYPES` across
    the network boundary -- kept equal by `quests.py` (QC1), never by hand
-   alone. */
+   alone. TICKET-0110 (BRIEF-0110-A): the two debt forms, whose target is
+   a creditor -- a character or a faction (the `givers` list). */
 
 export const REQUIREMENT_FORMS = {
   knowledge: { label: 'Connaît le fait', list: 'facts', column: 'key', threshold: false },
@@ -16,6 +17,8 @@ export const REQUIREMENT_FORMS = {
   faction_member: { label: 'Est membre de', list: 'factions', column: 'entity', threshold: false },
   skill_rank_gte: { label: 'Compétence au rang (≥)', list: 'skills', column: 'key', threshold: true },
   quest_completed: { label: 'A accompli la quête', list: 'offers', column: 'key', threshold: false },
+  has_debt_to: { label: 'A une dette envers', list: 'givers', column: 'entity', threshold: false },
+  no_debt_to: { label: 'N’a aucune dette envers', list: 'givers', column: 'entity', threshold: false },
 };
 
 // `resource`'s key is a label: one currency per world (the ledger has no
@@ -38,6 +41,7 @@ export function targetOptions(form, choices) {
     case 'characters': return choices.characters.map((c) => ({ value: c.id, label: c.name }));
     case 'locations': return choices.locations.map((c) => ({ value: c.id, label: c.name }));
     case 'factions': return choices.factions.map((c) => ({ value: c.id, label: c.name }));
+    case 'givers': return choices.givers.map((c) => ({ value: c.id, label: c.name }));
     default: return [];
   }
 }
diff --git a/scripts/apply_ticket_0110_link_prompt.py b/scripts/apply_ticket_0110_link_prompt.py
new file mode 100644
index 0000000..bfea74d
--- /dev/null
+++ b/scripts/apply_ticket_0110_link_prompt.py
@@ -0,0 +1,68 @@
+"""One-shot, idempotent delivery of the TICKET-0110 prompt update onto the
+live DB (BRIEF-0110-A, I2): the NPC link agent's pair pass no longer offers
+the relation type `debt` -- « X owes Y » is a `debt` row, never a link.
+
+Unlike `apply_ticket_0097_fact_code_prompts.py`, this script does not take
+the text from `scripts/seed_pilot.py`: it edits the CURRENT head of
+`pt-npc-link-pair` in place of one fragment, so an edit the creator made in
+the Prompts tab is kept. The fragment is the type list's opening, exactly as
+the seed wrote it (`ally, enemy, debt, fear`); it becomes `ally, enemy,
+fear`. A head whose text no longer carries the fragment is left alone and
+reported -- the creator then removes `debt` by hand, if it is still there.
+
+History is sacred: a changed text lands as a new `prompt_version` row
+through `write_prompt_version`, the old one untouched. Touches nothing else.
+Safe to re-run: an already-updated head prints "unchanged".
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+from pathlib import Path
+
+_env = os.environ.get("WORLD_ENGINE_ENV")
+if _env not in ("prod", "test"):
+    print(
+        "apply_ticket_0110_link_prompt.py refuses to run unless "
+        f"WORLD_ENGINE_ENV is 'prod' or 'test' (got: {_env or 'unset'})."
+    )
+    sys.exit(1)
+
+SRC = Path(__file__).resolve().parent.parent / "src"
+sys.path.insert(0, str(SRC))
+
+from sqlmodel import Session  # noqa: E402
+
+from world_engine.db import engine  # noqa: E402
+from world_engine.models import PromptTemplate  # noqa: E402
+from world_engine.prompt_store import current_prompt  # noqa: E402
+from world_engine.writes import write_prompt_version  # noqa: E402
+
+HEAD_ID = "pt-npc-link-pair"
+OLD_FRAGMENT = "ally, enemy, debt, fear"
+NEW_FRAGMENT = "ally, enemy, fear"
+NOTE = "TICKET-0110 BRIEF-0110-A -- the relation type `debt` is retired (I2)"
+
+
+def main() -> None:
+    with Session(engine) as session:
+        head = session.get(PromptTemplate, HEAD_ID)
+        if head is None:
+            print(f"{HEAD_ID}: head not found -- nothing to do")
+            return
+        current = current_prompt(session, head)
+        if OLD_FRAGMENT not in current.user_template:
+            state = "unchanged" if NEW_FRAGMENT in current.user_template else "fragment not found, edit by hand"
+            print(f"{HEAD_ID}: {state} (v{current.version_number})")
+            return
+        version = write_prompt_version(
+            session, template_id=head.id, system_prompt=current.system_prompt,
+            user_template=current.user_template.replace(OLD_FRAGMENT, NEW_FRAGMENT), note=NOTE,
+        )
+        session.commit()
+        print(f"{HEAD_ID}: v{current.version_number} -> v{version.version_number}")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/scripts/migrate_v2_19_debts.py b/scripts/migrate_v2_19_debts.py
new file mode 100644
index 0000000..c6bb13f
--- /dev/null
+++ b/scripts/migrate_v2_19_debts.py
@@ -0,0 +1,241 @@
+"""Migration v2.19 — debts, two debt requirement forms, an offer's contact
+(TICKET-0110, BRIEF-0110-A, decisions J2, C2, G1, X1, I2).
+
+1. Rebuild. `agenda_step_requirement` and `quest_offer_requirement` are
+   rebuilt from their models so their two CHECKs carry `has_debt_to` and
+   `no_debt_to` (an entity target, no threshold); `quest_economy` is rebuilt
+   so its CHECK covers `debt_fact_relation` and `debt_skill_relation`, both
+   added NULL (the code's defaults, 10 and 20). SQLite cannot alter a CHECK:
+   each table is renamed, recreated from its model, its rows copied column
+   for column, the old table dropped -- `migrate_v2_17_quests.py`'s
+   raw-connection rebuild, verbatim in shape. The new CHECKs accept every
+   row the old ones accepted.
+2. Add. `quest_offer.contact_entity_id` (nullable, a reference to `entity`).
+3. Create. `debt` and `debt_term`, from their models, when missing.
+
+The relation type `debt` is retired in code (I2); this migration writes no
+`relation` row and reads none: production held none (Nia's query,
+2026-10-07). A row still carrying it is listed, never changed.
+
+Refuses to run on a database whose `schema_meta.static_version` is older
+than v2.18 (the migrations are sequential), before any change.
+
+Idempotent: each rebuild runs only while its table lacks what it adds
+(`'has_debt_to'` in the stored CHECK, `debt_fact_relation` among the
+columns); the column is added and each table created only when missing.
+
+Post-checks, before `schema_meta` converges: both stored requirement CHECKs
+name the two forms; the four rebuilt or widened tables keep their row
+counts; the column and the two tables exist; `PRAGMA foreign_key_check` is
+empty on the six tables this migration writes. A dangling reference
+elsewhere in the database predates it: it is listed, never a reason to stop
+(AMENDMENT-0107-01).
+
+Run from the project root:
+
+    python scripts/migrate_v2_19_debts.py
+"""
+
+from __future__ import annotations
+
+import os
+import sys
+from datetime import UTC, datetime
+from pathlib import Path
+
+SRC = Path(__file__).resolve().parent.parent / "src"
+sys.path.insert(0, str(SRC))
+
+_env = os.environ.get("WORLD_ENGINE_ENV")
+if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
+    print(
+        "migrate_v2_19_debts.py refuses to run without WORLD_ENGINE_ENV "
+        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
+        f"{_env or 'unset'}.",
+        file=sys.stderr,
+    )
+    sys.exit(1)
+
+from sqlalchemy import inspect, text  # noqa: E402
+from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402
+from sqlmodel import Session  # noqa: E402
+
+from world_engine import models  # noqa: E402
+from world_engine.db import engine  # noqa: E402
+from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION  # noqa: E402
+
+_PREVIOUS_VERSION = "v2.18"
+_NEW_FORMS = ("has_debt_to", "no_debt_to")
+_REQUIREMENT_COLUMNS = {
+    "agenda_step_requirement": "id, world_id, step_id, type, target_entity_id, target_key, threshold",
+    "quest_offer_requirement": "id, world_id, offer_id, step_id, type, target_entity_id, target_key, threshold",
+}
+_REQUIREMENT_MODELS = {
+    "agenda_step_requirement": models.AgendaStepRequirement,
+    "quest_offer_requirement": models.QuestOfferRequirement,
+}
+_ECONOMY_COLUMNS = ("id, world_id, rate_money, rate_relation, rate_fact, rate_skill, band_low_pct, "
+                    "band_high_pct, updated_at")
+# Parents first: a debt before its terms.
+_NEW_MODELS = (models.Debt, models.DebtTerm)
+# The tables this migration writes: the only ones its foreign-key post-check judges.
+_TOUCHED_TABLES = ("agenda_step_requirement", "quest_offer_requirement", "quest_economy", "quest_offer",
+                   "debt", "debt_term")
+_COUNTED_TABLES = ("agenda_step_requirement", "quest_offer_requirement", "quest_economy", "quest_offer")
+
+
+def _version_key(version: str) -> tuple[int, int]:
+    major, minor = version.lstrip("v").split(".")
+    return int(major), int(minor)
+
+
+def _refuse() -> None:
+    with engine.connect() as conn:
+        row = conn.execute(text("SELECT static_version FROM schema_meta WHERE id = 1")).first()
+    if row is None or _version_key(row[0]) < _version_key(_PREVIOUS_VERSION):
+        found = row[0] if row is not None else "no schema_meta row"
+        raise SystemExit(
+            f"Migration v2.19 refused: the database is at {found!r}; run the migrations "
+            f"up to {_PREVIOUS_VERSION} first."
+        )
+
+
+def _table_sql(table: str) -> str:
+    with engine.connect() as conn:
+        row = conn.execute(text("SELECT sql FROM sqlite_master WHERE type='table' AND name=:t"), {"t": table}).first()
+    return row[0] if row is not None else ""
+
+
+def _columns(table: str) -> set[str]:
+    return {column["name"] for column in inspect(engine).get_columns(table)}
+
+
+def _row_counts() -> dict[str, int]:
+    with engine.connect() as conn:
+        return {t: conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar_one() for t in _COUNTED_TABLES}
+
+
+def _create_from_model(cursor, model) -> None:
+    cursor.execute(str(CreateTable(model.__table__).compile(dialect=engine.dialect)))
+    for index in model.__table__.indexes:
+        cursor.execute(str(CreateIndex(index).compile(dialect=engine.dialect)))
+
+
+def _rebuild(cursor, table: str, model, columns: str) -> None:
+    for (index_name,) in cursor.execute(
+        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL", (table,)
+    ).fetchall():
+        cursor.execute(f"DROP INDEX {index_name}")
+    cursor.execute(f"ALTER TABLE {table} RENAME TO {table}_old")
+    _create_from_model(cursor, model)
+    cursor.execute(f"INSERT INTO {table} ({columns}) SELECT {columns} FROM {table}_old")
+    cursor.execute(f"DROP TABLE {table}_old")
+
+
+def _plan() -> tuple[list[str], bool, bool, list]:
+    rebuild = [t for t in _REQUIREMENT_MODELS if "'has_debt_to'" not in _table_sql(t)]
+    economy = "debt_fact_relation" not in _columns("quest_economy")
+    contact = "contact_entity_id" not in _columns("quest_offer")
+    existing = set(inspect(engine).get_table_names())
+    missing = [model for model in _NEW_MODELS if model.__tablename__ not in existing]
+    return rebuild, economy, contact, missing
+
+
+def _apply_ddl() -> list[str]:
+    """One raw transaction (`migrate_v1_95_parked_plans.py`'s docstring: the
+    PRAGMAs must land before any transaction exists)."""
+    rebuild, economy, contact, missing = _plan()
+    if not (rebuild or economy or contact or missing):
+        return []
+    applied: list[str] = []
+    raw = engine.raw_connection()
+    try:
+        cursor = raw.cursor()
+        cursor.execute("PRAGMA foreign_keys=OFF")
+        cursor.execute("PRAGMA legacy_alter_table=ON")
+        cursor.execute("BEGIN")
+        for table in rebuild:
+            _rebuild(cursor, table, _REQUIREMENT_MODELS[table], _REQUIREMENT_COLUMNS[table])
+            applied.append(f"{table} rebuilt")
+        if economy:
+            _rebuild(cursor, "quest_economy", models.QuestEconomy, _ECONOMY_COLUMNS)
+            applied.append("quest_economy rebuilt")
+        if contact:
+            cursor.execute("ALTER TABLE quest_offer ADD COLUMN contact_entity_id VARCHAR REFERENCES entity (id)")
+            applied.append("quest_offer.contact_entity_id added")
+        for model in missing:
+            _create_from_model(cursor, model)
+            applied.append(f"{model.__tablename__} created")
+        cursor.execute("COMMIT")
+        cursor.execute("PRAGMA legacy_alter_table=OFF")
+        cursor.execute("PRAGMA foreign_keys=ON")
+        cursor.close()
+    except Exception:
+        raw.rollback()
+        raise
+    finally:
+        raw.close()
+    return applied
+
+
+def _post_checks(before: dict[str, int]) -> None:
+    for table in _REQUIREMENT_MODELS:
+        absent = [form for form in _NEW_FORMS if f"'{form}'" not in _table_sql(table)]
+        if absent:
+            raise SystemExit(f"Migration v2.19 aborted, post-check failed: {table}'s CHECK lacks {absent}.")
+    after = _row_counts()
+    changed = {t: (before[t], after[t]) for t in _COUNTED_TABLES if before[t] != after[t]}
+    if changed:
+        raise SystemExit(f"Migration v2.19 aborted, post-check failed: row counts changed {changed}.")
+    missing = [c for c in ("debt_fact_relation", "debt_skill_relation") if c not in _columns("quest_economy")]
+    if "contact_entity_id" not in _columns("quest_offer"):
+        missing.append("quest_offer.contact_entity_id")
+    tables = set(inspect(engine).get_table_names())
+    missing += [m.__tablename__ for m in _NEW_MODELS if m.__tablename__ not in tables]
+    if missing:
+        raise SystemExit(f"Migration v2.19 aborted, post-check failed: missing {missing}.")
+    with engine.connect() as conn:
+        dangling = [row for table in _TOUCHED_TABLES
+                    for row in conn.execute(text(f"PRAGMA foreign_key_check({table})")).fetchall()]
+        elsewhere = [row for row in conn.execute(text("PRAGMA foreign_key_check")).fetchall()
+                     if row[0] not in _TOUCHED_TABLES]
+        retired = conn.execute(text("SELECT COUNT(*) FROM relation WHERE type = 'debt'")).scalar_one()
+    if dangling:
+        raise SystemExit(f"Migration v2.19 aborted, post-check failed: foreign_key_check {dangling}.")
+    for table, rowid, parent, _fk in elsewhere:
+        print(f"  Note: {table} rowid {rowid} points to a missing {parent} row (not written by this migration).")
+    if retired:
+        print(f"  Note: {retired} relation row(s) still carry the retired type 'debt' (not changed).")
+    print(f"Post-check: two CHECKs widened; row counts kept {after}; debt tables in place.")
+
+
+def _converge_schema_meta() -> None:
+    with Session(engine) as session:
+        row = session.get(models.SchemaMeta, 1)
+        if row is None:
+            session.add(models.SchemaMeta(id=1, static_version=EXPECTED_STATIC_SCHEMA_VERSION))
+            print(f"Row: seeded schema_meta.id=1 at {EXPECTED_STATIC_SCHEMA_VERSION!r}")
+        elif row.static_version != EXPECTED_STATIC_SCHEMA_VERSION:
+            previous = row.static_version
+            row.static_version = EXPECTED_STATIC_SCHEMA_VERSION
+            row.updated_at = datetime.now(UTC)
+            session.add(row)
+            print(f"Row: updated schema_meta.id=1: {previous!r} -> {EXPECTED_STATIC_SCHEMA_VERSION!r}")
+        else:
+            print(f"Row: schema_meta.id=1 already at {EXPECTED_STATIC_SCHEMA_VERSION!r} — nothing to do")
+        session.commit()
+
+
+def main() -> None:
+    print("Migration v2.19 — debts, two debt requirement forms, an offer's contact")
+    _refuse()
+    before = _row_counts()
+    applied = _apply_ddl()
+    print("Applied: " + ", ".join(applied) + "." if applied else "Schema already in place.")
+    _post_checks(before)
+    _converge_schema_meta()
+    print("\nMigration v2.19 applied.")
+
+
+if __name__ == "__main__":
+    main()
diff --git a/scripts/seed_pilot.py b/scripts/seed_pilot.py
index 0ce925e..eef826b 100644
--- a/scripts/seed_pilot.py
+++ b/scripts/seed_pilot.py
@@ -1653,7 +1653,7 @@ Shared context: {shared_context}
 Reply ONLY with JSON:
 {"verdict": "links" or "no_links", "links": [ ... ]}
 Each link is one of:
-{"kind":"relation","type":<one of: ally, enemy, debt, fear, fascination, \
+{"kind":"relation","type":<one of: ally, enemy, fear, fascination, \
 shared_secret, instrumentalizes, interest, indifference, rejection, \
 passive_attention, other>,"direction":"mutual"|"a_to_b"|"b_to_a", \
 "intensity":1-100,"visible_to_b":true|false,"notes":"..."}
diff --git a/src/world_engine/cockpit/crud/_shared.py b/src/world_engine/cockpit/crud/_shared.py
index 1070be5..f2fb5a2 100644
--- a/src/world_engine/cockpit/crud/_shared.py
+++ b/src/world_engine/cockpit/crud/_shared.py
@@ -140,8 +140,9 @@ def _coerce_field(db: DbSession, field: dict, raw: Any) -> Any:
 # The fiche relation form's datalist. `connects_to` is its ONE geographic
 # entry (TICKET-0101, V1): `borde` is never offered, the server derives the
 # geographic type from the two locations (`spatial_author.link_locations`).
+# `debt` is retired (TICKET-0110, I2): « X owes Y » is a `debt` row.
 RELATION_TYPES = (
-    "ally", "enemy", "debt", "fear", "fascination", "shared_secret",
+    "ally", "enemy", "fear", "fascination", "shared_secret",
     "instrumentalizes", "interest", "indifference", "rejection",
     "passive_attention", "other", "connects_to", "controls",
 )
diff --git a/src/world_engine/cockpit/routes/quests.py b/src/world_engine/cockpit/routes/quests.py
index c2d104c..4214965 100644
--- a/src/world_engine/cockpit/routes/quests.py
+++ b/src/world_engine/cockpit/routes/quests.py
@@ -92,6 +92,8 @@ class EconomyBody(BaseModel):
     rate_skill: Optional[int] = None
     band_low_pct: Optional[int] = None
     band_high_pct: Optional[int] = None
+    debt_fact_relation: Optional[int] = None
+    debt_skill_relation: Optional[int] = None
 
 
 def _term(term: TermBody) -> TermSpec:
diff --git a/src/world_engine/day_plan.py b/src/world_engine/day_plan.py
index 6d5d5e3..680db1c 100644
--- a/src/world_engine/day_plan.py
+++ b/src/world_engine/day_plan.py
@@ -54,6 +54,7 @@ from .models import (
     AgendaStep,
     AgendaStepRequirement,
     Character,
+    Debt,
     Entity,
     Fact,
     FactionMembership,
@@ -81,9 +82,12 @@ DAY_BUDGET_SLOTS: int = len(SCHEDULE_PHASES)
 # S1: the closed requirement vocabulary, each form with a named evaluator.
 # Eight forms since v2.17 (TICKET-0108, BRIEF-0108-A, C-01): the four the
 # day-plan model may emit, then four only the creator authors (quest offers).
+# Ten since v2.19 (TICKET-0110, BRIEF-0110-A, G1): `has_debt_to` and
+# `no_debt_to`, creator only as well.
 REQUIREMENT_TYPES: tuple[str, ...] = (
     "knowledge", "relation_gte", "resource", "location_reachable",
     "has_met", "faction_member", "skill_rank_gte", "quest_completed",
+    "has_debt_to", "no_debt_to",
 )
 
 # What `emit_plan`'s parser accepts from the model (TICKET-0108): the four
@@ -93,7 +97,9 @@ MODEL_REQUIREMENT_TYPES: tuple[str, ...] = ("knowledge", "relation_gte", "resour
 
 # The shape of each form, the three groups of the `*_requirement_shape`
 # CHECK (C-01): which column names its target, and which need a threshold.
-ENTITY_TARGET_TYPES: tuple[str, ...] = ("relation_gte", "location_reachable", "has_met", "faction_member")
+ENTITY_TARGET_TYPES: tuple[str, ...] = (
+    "relation_gte", "location_reachable", "has_met", "faction_member", "has_debt_to", "no_debt_to",
+)
 KEY_TARGET_TYPES: tuple[str, ...] = ("knowledge", "resource", "skill_rank_gte", "quest_completed")
 THRESHOLD_TYPES: tuple[str, ...] = ("relation_gte", "resource", "skill_rank_gte")
 
@@ -334,6 +340,38 @@ def _eval_quest_completed(req: RequirementSpec, character: Character, db: Sessio
     )
 
 
+def _open_debt(db: Session, debtor_id: str, creditor_id: Optional[str]) -> bool:
+    return db.exec(select(Debt.id).where(
+        Debt.debtor_entity_id == debtor_id, Debt.creditor_entity_id == creditor_id, Debt.status == "open",
+    )).first() is not None
+
+
+def _eval_has_debt_to(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """TICKET-0110 (G1): the character owes the target (a character or a
+    faction) at least one OPEN debt -- one he is the debtor of; existence
+    only, no amount. A settled or forgiven debt is not owed."""
+    del reachable_ids
+    met = _open_debt(db, character.id, req.target_entity_id)
+    name = _entity_name(db, req.target_entity_id)
+    reason = f"owes {name}" if met else f"prerequisite not met — owes {name} nothing"
+    return Verdict(
+        type=req.type, met=met, current=("owes" if met else "owes nothing"), required=req.target_entity_id,
+        reason=reason, required_label=name,
+    )
+
+
+def _eval_no_debt_to(req: RequirementSpec, character: Character, db: Session, reachable_ids) -> Verdict:
+    """TICKET-0110 (G1): the exact negation of `has_debt_to`."""
+    del reachable_ids
+    owes = _open_debt(db, character.id, req.target_entity_id)
+    name = _entity_name(db, req.target_entity_id)
+    reason = f"prerequisite not met — still owes {name}" if owes else f"owes {name} nothing"
+    return Verdict(
+        type=req.type, met=not owes, current=("owes" if owes else "owes nothing"), required=req.target_entity_id,
+        reason=reason, required_label=name,
+    )
+
+
 _EVALUATORS: dict[str, Callable[[RequirementSpec, Character, Session, object], Verdict]] = {
     "knowledge": _eval_knowledge,
     "relation_gte": _eval_relation_gte,
@@ -343,6 +381,8 @@ _EVALUATORS: dict[str, Callable[[RequirementSpec, Character, Session, object], V
     "faction_member": _eval_faction_member,
     "skill_rank_gte": _eval_skill_rank_gte,
     "quest_completed": _eval_quest_completed,
+    "has_debt_to": _eval_has_debt_to,
+    "no_debt_to": _eval_no_debt_to,
 }
 
 
diff --git a/src/world_engine/day_resolve.py b/src/world_engine/day_resolve.py
index 1df4f64..9c41d3b 100644
--- a/src/world_engine/day_resolve.py
+++ b/src/world_engine/day_resolve.py
@@ -267,6 +267,9 @@ _BLOCKED_DETAIL_FR: dict[str, str] = {
     "faction_member": "il n'appartient pas à {required}",
     "skill_rank_gte": "sa maîtrise de « {required} » ne suffit pas encore",
     "quest_completed": "il doit d'abord mener à bien « {required} »",
+    # TICKET-0110 (BRIEF-0110-A): the two debt forms.
+    "has_debt_to": "il ne doit rien à {required}",
+    "no_debt_to": "il a encore une dette envers {required}",
 }
 
 
diff --git a/src/world_engine/link_author.py b/src/world_engine/link_author.py
index 8a3178e..3c1b2de 100644
--- a/src/world_engine/link_author.py
+++ b/src/world_engine/link_author.py
@@ -68,9 +68,10 @@ JOURNAL_DIR = Path.home() / ".world_engine" / "link_agent_journal"
 # Closed vocab for the pair-pass model (RECON-0036 s.1): deliberately
 # NARROWER than cockpit.crud._shared.RELATION_TYPES — connects_to/controls
 # are location-map topology / control edges, structurally impossible for
-# the link agent to propose.
+# the link agent to propose. `debt` is retired (TICKET-0110, I2): the model
+# never writes a debt as a link; « X owes Y » is a `debt` row.
 _LINK_RELATION_TYPES = (
-    "ally", "enemy", "debt", "fear", "fascination", "shared_secret",
+    "ally", "enemy", "fear", "fascination", "shared_secret",
     "instrumentalizes", "interest", "indifference", "rejection",
     "passive_attention", "other",
 )
diff --git a/src/world_engine/models/__init__.py b/src/world_engine/models/__init__.py
index 89c3bf9..1eff21b 100644
--- a/src/world_engine/models/__init__.py
+++ b/src/world_engine/models/__init__.py
@@ -32,7 +32,8 @@ Layout, by stratum:
                         QuestOfferStep, QuestOfferRequirement, Quest;
                         TICKET-0108, schema v2.17), their terms and a
                         world's quest economy (QuestOfferTerm, QuestTerm,
-                        QuestEconomy; TICKET-0109, v2.18), canon.
+                        QuestEconomy; TICKET-0109, v2.18), and debts
+                        (Debt, DebtTerm; TICKET-0110, v2.19), canon.
 
 This module re-exports the ENTIRE former public surface of the flat
 `models.py` — every class, constant, and the two module functions
@@ -131,6 +132,9 @@ from .observation import (
     ObservationRunTemplate,
 )
 from .quests import (
+    DEBT_CURRENCIES,
+    DEBT_ORIGINS,
+    DEBT_STATUSES,
     QUEST_OFFER_STATUSES,
     QUEST_TERM_CURRENCIES,
     QUEST_TERM_DIRECTIONS,
@@ -141,6 +145,8 @@ from .quests import (
     QuestOfferStep,
     QuestOfferTerm,
     QuestTerm,
+    Debt,
+    DebtTerm,
 )
 
 __all__ = [
@@ -216,6 +222,11 @@ __all__ = [
     "QuestEconomy",
     "QuestOfferTerm",
     "QuestTerm",
+    "DEBT_CURRENCIES",
+    "DEBT_ORIGINS",
+    "DEBT_STATUSES",
+    "Debt",
+    "DebtTerm",
     "GoalAgendaLink",
     "EntityType",
     "EntityTypeHistory",
diff --git a/src/world_engine/models/config.py b/src/world_engine/models/config.py
index 534e89c..5f8fbd5 100644
--- a/src/world_engine/models/config.py
+++ b/src/world_engine/models/config.py
@@ -112,7 +112,9 @@ class AgendaStep(SQLModel, table=True):
 # id) rather than an entity. Eight forms since v2.17 (TICKET-0108,
 # BRIEF-0108-A): the four the day-plan model may emit, plus `has_met`,
 # `faction_member`, `skill_rank_gte` and `quest_completed`, authored by the
-# creator only (`day_plan.MODEL_REQUIREMENT_TYPES`).
+# creator only (`day_plan.MODEL_REQUIREMENT_TYPES`). Ten since v2.19
+# (TICKET-0110, BRIEF-0110-A, G1): `has_debt_to` and `no_debt_to`, an open
+# debt toward the target entity or none, creator only too.
 #
 # The per-type shape CHECK is the structural guarantee that an ill-formed row
 # cannot exist; its three groups are `day_plan.ENTITY_TARGET_TYPES`,
@@ -131,11 +133,11 @@ class AgendaStepRequirement(SQLModel, table=True):
     __table_args__ = (
         CheckConstraint(
             "type IN ('knowledge','relation_gte','resource','location_reachable',"
-            "'has_met','faction_member','skill_rank_gte','quest_completed')",
+            "'has_met','faction_member','skill_rank_gte','quest_completed','has_debt_to','no_debt_to')",
             name="ck_agenda_step_requirement_type",
         ),
         CheckConstraint(
-            "(type NOT IN ('relation_gte','location_reachable','has_met','faction_member') "
+            "(type NOT IN ('relation_gte','location_reachable','has_met','faction_member','has_debt_to','no_debt_to') "
             "OR target_entity_id IS NOT NULL) "
             "AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') "
             "OR target_key IS NOT NULL) "
diff --git a/src/world_engine/models/quests.py b/src/world_engine/models/quests.py
index 600cee8..8536864 100644
--- a/src/world_engine/models/quests.py
+++ b/src/world_engine/models/quests.py
@@ -47,6 +47,11 @@ class QuestOffer(SQLModel, table=True):
     world_id: str = Field(foreign_key="world.id", nullable=False)
     # A character or a faction of the world (H1), checked by the writer.
     giver_entity_id: str = Field(foreign_key="entity.id", nullable=False)
+    # v2.19 (TICKET-0110, X1): when the giver is a faction, the member who
+    # speaks for it -- the person a debt born of this offer is linked to.
+    # NULL for a character giver; optional for a faction (asked at « régler
+    # à crédit » when absent). Checked by the writer.
+    contact_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
     title: str
     summary: Optional[str] = None
     # L1: a repeatable offer may be accepted again once the last quest taken
@@ -89,11 +94,11 @@ class QuestOfferRequirement(SQLModel, table=True):
     __table_args__ = (
         CheckConstraint(
             "type IN ('knowledge','relation_gte','resource','location_reachable',"
-            "'has_met','faction_member','skill_rank_gte','quest_completed')",
+            "'has_met','faction_member','skill_rank_gte','quest_completed','has_debt_to','no_debt_to')",
             name="ck_quest_offer_requirement_type",
         ),
         CheckConstraint(
-            "(type NOT IN ('relation_gte','location_reachable','has_met','faction_member') "
+            "(type NOT IN ('relation_gte','location_reachable','has_met','faction_member','has_debt_to','no_debt_to') "
             "OR target_entity_id IS NOT NULL) "
             "AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') "
             "OR target_key IS NOT NULL) "
@@ -227,7 +232,9 @@ class QuestEconomy(SQLModel, table=True):
             "(rate_money IS NULL OR rate_money >= 0) AND (rate_relation IS NULL OR rate_relation >= 0) "
             "AND (rate_fact IS NULL OR rate_fact >= 0) AND (rate_skill IS NULL OR rate_skill >= 0) "
             "AND (band_low_pct IS NULL OR band_low_pct >= 0) "
-            "AND (band_high_pct IS NULL OR band_high_pct >= 0)",
+            "AND (band_high_pct IS NULL OR band_high_pct >= 0) "
+            "AND (debt_fact_relation IS NULL OR debt_fact_relation >= 0) "
+            "AND (debt_skill_relation IS NULL OR debt_skill_relation >= 0)",
             name="ck_quest_economy_rates",
         ),
     )
@@ -240,4 +247,96 @@ class QuestEconomy(SQLModel, table=True):
     rate_skill: Optional[int] = None
     band_low_pct: Optional[int] = None
     band_high_pct: Optional[int] = None
+    # v2.19 (TICKET-0110): what the creditor's regard falls by when a debt's
+    # fact or skill can no longer be delivered (he already holds it); NULL
+    # reads the code's default (`quest_value.DEFAULT_RATES`: 10 and 20).
+    debt_fact_relation: Optional[int] = None
+    debt_skill_relation: Optional[int] = None
     updated_at: datetime = _created_ts()
+
+
+# -----------------------------------------------------------------------------
+# debt  (what one entity owes another, v2.19, TICKET-0110, BRIEF-0110-A, J2)
+#
+# Born of a service (S2), of a quest settled on credit (A2) or of the
+# creator's hand. The debtor is a character; the creditor a character or a
+# faction (J1); a faction creditor always names its contact, an active
+# member (X1), and a character creditor never does (writer-checked). What is
+# owed is a list of typed terms (`debt_term`, C2); its indicative value is
+# computed at read, never stored and never converted (C1 of the series).
+#
+# A debt is SETTLED or FORGIVEN, never deleted (J2): `status` leaves `open`
+# once, with `closed_at` and, for a remission, `closed_note`; nothing else
+# on the row moves after creation. Its fact (`fact_id`, a free `information`
+# fact whose participants are the parties, F-a) receives a `changement` at
+# that moment, so whoever learned the debt earlier keeps the old version
+# until a later contact (TICKET-0105).
+#
+# This table is the one way to say « X owes Y » (I2): the relation type
+# `debt` is retired and never written by this table or any other path.
+# -----------------------------------------------------------------------------
+DEBT_ORIGINS: tuple[str, ...] = ("service", "quest", "creator")
+DEBT_STATUSES: tuple[str, ...] = ("open", "settled", "forgiven")
+DEBT_CURRENCIES: tuple[str, ...] = ("money", "item", "fact", "skill")
+
+
+class Debt(SQLModel, table=True):
+    __tablename__ = "debt"
+    __table_args__ = (
+        CheckConstraint("origin IN ('service','quest','creator')", name="ck_debt_origin"),
+        CheckConstraint("status IN ('open','settled','forgiven')", name="ck_debt_status"),
+        CheckConstraint("debtor_entity_id <> creditor_entity_id", name="ck_debt_parties"),
+        CheckConstraint("(origin = 'quest') = (origin_quest_id IS NOT NULL)", name="ck_debt_origin_quest"),
+        CheckConstraint("(status = 'open') = (closed_at IS NULL)", name="ck_debt_closed"),
+        Index("idx_debt_world", "world_id"),
+        Index("idx_debt_debtor", "debtor_entity_id"),
+        Index("idx_debt_creditor", "creditor_entity_id"),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    debtor_entity_id: str = Field(foreign_key="entity.id", nullable=False)
+    creditor_entity_id: str = Field(foreign_key="entity.id", nullable=False)
+    contact_entity_id: Optional[str] = Field(default=None, foreign_key="entity.id")
+    origin: str
+    origin_quest_id: Optional[str] = Field(default=None, foreign_key="quest.id")
+    reason: Optional[str] = None
+    is_secret: bool = Field(default=False, sa_column_kwargs={"server_default": text("0")})
+    fact_id: str = Field(foreign_key="fact.id", nullable=False)
+    status: str = Field(default="open", sa_column_kwargs={"server_default": text("'open'")})
+    created_at: datetime = _created_ts()
+    closed_at: Optional[datetime] = None
+    closed_note: Optional[str] = None
+
+
+# -----------------------------------------------------------------------------
+# debt_term  (one thing a debt owes, C2/T1). Written with its debt, never
+# touched again. Money and items count; a fact is delivered (the creditor --
+# his contact for a faction -- learns it); a skill is taught (the debtor
+# must be Maître). No relation: regard is not repaid.
+# -----------------------------------------------------------------------------
+DEBT_TERM_SHAPE_CHECK = (
+    "(currency NOT IN ('money','item') OR (amount IS NOT NULL AND amount >= 1)) "
+    "AND (currency <> 'item' OR item_id IS NOT NULL) "
+    "AND (currency <> 'fact' OR fact_id IS NOT NULL) "
+    "AND (currency <> 'skill' OR skill_key IS NOT NULL)"
+)
+
+
+class DebtTerm(SQLModel, table=True):
+    __tablename__ = "debt_term"
+    __table_args__ = (
+        CheckConstraint("currency IN ('money','item','fact','skill')", name="ck_debt_term_currency"),
+        CheckConstraint(DEBT_TERM_SHAPE_CHECK, name="ck_debt_term_shape"),
+        Index("idx_debt_term_debt", "debt_id"),
+    )
+
+    id: str = Field(default_factory=_uuid, primary_key=True)
+    world_id: str = Field(foreign_key="world.id", nullable=False)
+    debt_id: str = Field(foreign_key="debt.id", nullable=False)
+    term_order: int
+    currency: str
+    item_id: Optional[str] = Field(default=None, foreign_key="item.id")
+    fact_id: Optional[str] = Field(default=None, foreign_key="fact.id")
+    skill_key: Optional[str] = None
+    amount: Optional[int] = None
diff --git a/src/world_engine/quest_value.py b/src/world_engine/quest_value.py
index 4e22f9f..a8bec3d 100644
--- a/src/world_engine/quest_value.py
+++ b/src/world_engine/quest_value.py
@@ -19,9 +19,13 @@ from sqlmodel import Session, select
 from .models import Item, QuestEconomy
 
 # The code's defaults (E1); a NULL column of `quest_economy` reads these.
+# TICKET-0110 (BRIEF-0110-A): the two debt settings are not rates of the
+# unit but relation points -- what a creditor's regard falls by when a debt's
+# fact or skill can no longer be delivered (he already holds it).
 DEFAULT_RATES: dict[str, int] = {
     "rate_money": 1, "rate_relation": 1, "rate_fact": 5, "rate_skill": 20,
     "band_low_pct": 100, "band_high_pct": 150,
+    "debt_fact_relation": 10, "debt_skill_relation": 20,
 }
 
 # The verdict of a reward against the band, as the editor shows it.
diff --git a/src/world_engine/relation_orientation.py b/src/world_engine/relation_orientation.py
index debbf0a..4478925 100644
--- a/src/world_engine/relation_orientation.py
+++ b/src/world_engine/relation_orientation.py
@@ -29,6 +29,12 @@ RELATION_GRAPH_EXCLUDED_TYPES: tuple[str, str, str] = ("connects_to", "borde", "
 # (`zone_rules.geographic_link_type`), never chosen by the creator.
 MAP_TOPOLOGY_TYPES: tuple[str, str] = ("connects_to", "borde")
 
+# Relation types no path may write any more (TICKET-0110, BRIEF-0110-A, I2):
+# « X owes Y » lives in the `debt` table alone, never in a relation's type.
+# `write_relation` refuses them; no row of production carried one when the
+# type was retired (Nia's query, 2026-10-07).
+RETIRED_RELATION_TYPES: tuple[str, ...] = ("debt",)
+
 
 def is_social(relation_type: str) -> bool:
     """True for a social relation type; False for a structural one or None."""
diff --git a/src/world_engine/schema_version.py b/src/world_engine/schema_version.py
index 7ab189a..b5b206c 100644
--- a/src/world_engine/schema_version.py
+++ b/src/world_engine/schema_version.py
@@ -12,4 +12,4 @@ statically checks this constant against the doc header.
 
 from __future__ import annotations
 
-EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.18"
+EXPECTED_STATIC_SCHEMA_VERSION: str = "v2.19"
diff --git a/src/world_engine/writes/goals_agendas.py b/src/world_engine/writes/goals_agendas.py
index 7fac0a2..932f9e8 100644
--- a/src/world_engine/writes/goals_agendas.py
+++ b/src/world_engine/writes/goals_agendas.py
@@ -604,8 +604,10 @@ def write_agenda_status(
 # The entity type each entity-targeted form must name (TICKET-0108, C-01);
 # `None` accepts any entity of the world -- the two model-emitted forms keep
 # the check they always had, so a day plan is refused for nothing new.
-_TARGET_ENTITY_TYPE: dict[str, Optional[str]] = {
-    "relation_gte": None, "location_reachable": None, "has_met": None, "faction_member": "faction",
+_TARGET_ENTITY_TYPE: dict[str, Optional[tuple[str, ...]]] = {
+    "relation_gte": None, "location_reachable": None, "has_met": None, "faction_member": ("faction",),
+    # TICKET-0110 (G1): a debt's creditor, a character or a faction (J1).
+    "has_debt_to": ("character", "faction"), "no_debt_to": ("character", "faction"),
 }
 
 
@@ -647,7 +649,7 @@ def _clean_requirement(db: Session, world_id: str, step_index: int, req: Require
             )
         target = db.get(Entity, req.target_entity_id)
         wanted = _TARGET_ENTITY_TYPE[req.type]
-        if target is None or target.world_id != world_id or (wanted is not None and target.type != wanted):
+        if target is None or target.world_id != world_id or (wanted is not None and target.type not in wanted):
             raise ValueError(f"write_day_plan: unknown target entity {req.target_entity_id!r}")
     else:
         if not req.target_key:
diff --git a/src/world_engine/writes/quest_terms.py b/src/world_engine/writes/quest_terms.py
index 5b1a225..6888a59 100644
--- a/src/world_engine/writes/quest_terms.py
+++ b/src/world_engine/writes/quest_terms.py
@@ -51,9 +51,11 @@ FACT_REWARD_LEVELS: tuple[str, ...] = tuple(sorted(KNOWLEDGE_LEVELS - {"unaware"
 TERM_COLUMNS: tuple[str, ...] = (
     "direction", "currency", "counterparty_entity_id", "item_id", "fact_id", "skill_key", "amount", "level",
 )
-# The economy columns a world may set (E1).
+# The economy columns a world may set (E1); the two debt settings since
+# v2.19 (TICKET-0110).
 ECONOMY_COLUMNS: tuple[str, ...] = (
     "rate_money", "rate_relation", "rate_fact", "rate_skill", "band_low_pct", "band_high_pct",
+    "debt_fact_relation", "debt_skill_relation",
 )
 
 
diff --git a/src/world_engine/writes/relations.py b/src/world_engine/writes/relations.py
index 3f6360b..848c328 100644
--- a/src/world_engine/writes/relations.py
+++ b/src/world_engine/writes/relations.py
@@ -74,6 +74,7 @@ from ..models import Entity, Fact, Knowledge, Relation
 from ..prose_render import entity_token
 from ..relation_orientation import (
     MAP_TOPOLOGY_TYPES,
+    RETIRED_RELATION_TYPES,
     borde_fact_content,
     connects_to_fact_content,
     is_social,
@@ -319,6 +320,15 @@ def _build_relation_set(
     )
 
 
+def _refuse_retired_type(relation_type: Optional[str]) -> None:
+    """I2 (TICKET-0110): a retired type is never written -- « X owes Y » is a
+    `debt` row, not a relation."""
+    if relation_type in RETIRED_RELATION_TYPES:
+        raise ValueError(
+            f"write_relation: the relation type {relation_type!r} is retired -- a debt lives in the debt table"
+        )
+
+
 def write_relation(
     db: Session,
     *,
@@ -360,6 +370,7 @@ def write_relation(
     """
     if mode not in ("delta", "set"):
         raise ValueError(f"write_relation: invalid mode {mode!r}")
+    _refuse_retired_type(type)
 
     now = datetime.now(UTC)
     provenance = changed_by or (f"mutation:{mutation_id}" if mutation_id else "creator_crud")
diff --git a/src/world_engine/writes/worlds.py b/src/world_engine/writes/worlds.py
index 2972ed2..9d39897 100644
--- a/src/world_engine/writes/worlds.py
+++ b/src/world_engine/writes/worlds.py
@@ -76,6 +76,7 @@ _DIRECT_WORLD_SCOPED_DELETES: tuple[str, ...] = (
     "skill_rank", "skill_resolution", "skill_system", "unresolved_mention", "visit",
     "world_law", "quest", "quest_offer", "quest_offer_requirement", "quest_offer_step",
     "item_holding", "quest_offer_term", "quest_term", "quest_economy",
+    "debt", "debt_term",
 )
 
 # Refusing tables (root_table, label_column, guarded_children, message) —
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 379deb1..02cfd9b 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18235,6 +18235,45 @@ cost cannot be paid. A completed quest still to settle reads « accomplie —
 **Rejected.** Computing the value in the browser: a second implementation
 of the rates to keep in step; the server already has them.
 
+## A DEBT IS A ROW, NEVER A RELATION TYPE (TICKET-0110) -- TEN REQUIREMENT FORMS, AN OFFER'S CONTACT (BRIEF-0110-a, schema v2.19)
+
+**J2.** `debt` records what a character owes a character or a faction (J1):
+origin (`service`, `quest`, `creator`), an optional motive (V1), secrecy
+(F-b1), the debt's fact, a status that leaves `open` once -- `settled` or
+`forgiven`, never deleted: deleting would be a correction (I1 of 0105),
+paying is a change. What is owed is a list of typed terms in `debt_term`
+(C2): money, items, a fact to deliver, a skill to teach (T1) -- never
+relation, which is not repaid. Its value in the indicative unit is computed
+at read, never stored, never converted (C1 of the series).
+
+**I2.** « X owes Y » has one home. The relation type `debt` is retired:
+offered neither in the fiche's list nor to the link agent, and
+`write_relation` refuses it (`RETIRED_RELATION_TYPES`). Production held no
+such row. The live link-pair prompt loses it through
+`apply_ticket_0110_link_prompt.py`, which edits the current head's text so
+an edit of the creator is kept.
+
+**X1.** A faction creditor is always linked to a person: the contact, an
+active member. An offer given by a faction may name its contact
+(`quest_offer.contact_entity_id`); a debt born of it is linked to him.
+
+**G1.** `has_debt_to` and `no_debt_to`: the character is the debtor of at
+least one open debt toward the target, or of none -- existence only,
+creator only (the model still emits four forms). The target is a character
+or a faction.
+
+**The economy.** `quest_economy` gains `debt_fact_relation` and
+`debt_skill_relation` (defaults 10 and 20): what the creditor's regard falls
+by when a debt's fact or skill can no longer be delivered, because he
+already holds it. Set in the ⚖ panel with the rates.
+
+**Rejected.** A relation of type `debt` with a fact (I3): one social row per
+oriented pair would overwrite the feeling it stands on, and it has no place
+for terms, an origin or a settlement. A value in units alone (C1 of this
+ticket): repaying in any currency at the rates would make the unit a
+currency.
+
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index 555ff17..4701a41 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -7,6 +7,7 @@ location_type_catalog entity_type entity_type_history conversation_window_config
 npc_schedule agenda_step_requirement fact fact_participant fact_default
 skill_rank quest_offer quest_offer_step quest_offer_requirement quest
 item_holding quest_offer_term quest_term quest_economy
+debt debt_term
 
 [ALLOWED_SITES]
 # path::function                                              tables
diff --git a/tooling/verify/checks/day_plan.py b/tooling/verify/checks/day_plan.py
index a2a460c..2c94c96 100644
--- a/tooling/verify/checks/day_plan.py
+++ b/tooling/verify/checks/day_plan.py
@@ -192,6 +192,8 @@ _MODEL_FILES = (CANON_FILE, CONFIG_FILE)
 EXPECTED_REQUIREMENT_TYPES = (
     "knowledge", "relation_gte", "resource", "location_reachable",
     "has_met", "faction_member", "skill_rank_gte", "quest_completed",
+    # TICKET-0110 (BRIEF-0110-A, G1): ten since v2.19.
+    "has_debt_to", "no_debt_to",
 )
 EXPECTED_RECONCILE_VERDICTS = ("continue", "modify", "replace")
 EXPECTED_PLAN_ACTIONS = ("continue", "modify", "replace", "resume")
@@ -365,6 +367,8 @@ def check_shape_constraint() -> None:
         ("skill_rank_gte", "target_key"),
         ("quest_completed", "target_key"),
         ("skill_rank_gte", "threshold"),
+        ("has_debt_to", "target_entity_id"),
+        ("no_debt_to", "target_entity_id"),
     ]
     missing = [pair for pair in required_pairs if pair[0] not in expr or pair[1] not in expr]
     if missing:
diff --git a/tooling/verify/checks/debts.py b/tooling/verify/checks/debts.py
new file mode 100644
index 0000000..8cd603a
--- /dev/null
+++ b/tooling/verify/checks/debts.py
@@ -0,0 +1,470 @@
+"""G1 check for TICKET-0110 -- debts and services.
+
+The lot adds its pieces brief by brief; this check grows with it (the
+`quests.py` and `quest_rewards.py` precedent). Each brief adds its rules
+here in the same commit.
+
+DA1 -- schema and vocabulary (BRIEF-0110-A, import and static).
+   a. `debt` and `debt_term` carry exactly their contract's columns and
+      CHECK texts; `DEBT_ORIGINS`, `DEBT_STATUSES`, `DEBT_CURRENCIES` are the
+      values those CHECKs quote, in order; `quest_offer` has
+      `contact_entity_id` and `quest_economy` `debt_fact_relation` and
+      `debt_skill_relation`; `DEFAULT_RATES` gives them 10 and 20 and
+      `ECONOMY_COLUMNS` lists them; the code's schema version is v2.19.
+   b. `day_plan.REQUIREMENT_TYPES` ends with `has_debt_to`, `no_debt_to`;
+      both are in `ENTITY_TARGET_TYPES`, neither in `THRESHOLD_TYPES` nor
+      `MODEL_REQUIREMENT_TYPES`; each has an evaluator and a French blocked
+      detail; `questRequirements.js` offers both on the `givers` list.
+   c. I2: `debt` is in `RETIRED_RELATION_TYPES` and in neither the fiche's
+      `RELATION_TYPES` nor the link agent's `_LINK_RELATION_TYPES`; the
+      seeded link-pair prompt does not offer it; `write_relation` refuses
+      it with no row written.
+DA2 -- migration `scripts/migrate_v2_19_debts.py`, on a v2.18-shaped
+   database (the four tables it changes in their v2.18 DDL, verbatim below;
+   no debt table), holding one row in each and a `session` row pointing to
+   a missing world:
+   a. at v2.17 it refuses (non-zero exit) and changes nothing;
+   b. at v2.18 it keeps every row, both requirement CHECKs name the two
+      forms, the columns and the two tables exist with the models' shapes, a
+      `has_debt_to` row can be inserted, `PRAGMA foreign_key_check` is empty
+      on the six tables it writes, the orphan `session` is noted and not
+      stopped on, and `schema_meta` is the code's version;
+   c. a second run exits zero and changes no row.
+DA3 -- the evaluators (fixture). With an OPEN debt of the character toward
+   the creditor: `has_debt_to` met, `no_debt_to` not. A settled debt, a
+   debt toward another creditor and a debt the character is OWED count for
+   nothing. A faction creditor is judged like a character.
+   `requirement_detail_fr` names the creditor in both forms.
+   `_clean_requirement` accepts a character and a faction as target and
+   refuses a location.
+
+Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
+world_engine import) -- never Nia's DB. A rule that collects nothing fails.
+"""
+from __future__ import annotations
+
+import os
+import pathlib
+import re
+import sqlite3
+import subprocess
+import sys
+import tempfile
+from datetime import UTC, datetime
+
+ROOT = pathlib.Path(__file__).resolve().parents[3]
+MIGRATION = ROOT / "scripts" / "migrate_v2_19_debts.py"
+FRONTEND = ROOT / "frontend" / "src"
+
+FAILURES: list[str] = []
+
+DEBT_FORMS = ("has_debt_to", "no_debt_to")
+DEBT_COLUMNS = (
+    "id", "world_id", "debtor_entity_id", "creditor_entity_id", "contact_entity_id", "origin",
+    "origin_quest_id", "reason", "is_secret", "fact_id", "status", "created_at", "closed_at", "closed_note",
+)
+DEBT_TERM_COLUMNS = ("id", "world_id", "debt_id", "term_order", "currency", "item_id", "fact_id", "skill_key", "amount")
+DEBT_CHECKS = {
+    "ck_debt_origin": "origin IN ('service','quest','creator')",
+    "ck_debt_status": "status IN ('open','settled','forgiven')",
+    "ck_debt_parties": "debtor_entity_id <> creditor_entity_id",
+    "ck_debt_origin_quest": "(origin = 'quest') = (origin_quest_id IS NOT NULL)",
+    "ck_debt_closed": "(status = 'open') = (closed_at IS NULL)",
+}
+DEBT_TERM_CHECKS = {
+    "ck_debt_term_currency": "currency IN ('money','item','fact','skill')",
+    "ck_debt_term_shape": (
+        "(currency NOT IN ('money','item') OR (amount IS NOT NULL AND amount >= 1)) "
+        "AND (currency <> 'item' OR item_id IS NOT NULL) "
+        "AND (currency <> 'fact' OR fact_id IS NOT NULL) "
+        "AND (currency <> 'skill' OR skill_key IS NOT NULL)"
+    ),
+}
+CHANGED_TABLES = ("agenda_step_requirement", "quest_offer_requirement", "quest_economy", "quest_offer")
+
+# The four tables as v2.18 created them (dumped from `main` at 42f2310).
+_V218_DDL = (
+    """CREATE TABLE agenda_step_requirement (
+	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, step_id VARCHAR NOT NULL, type VARCHAR NOT NULL,
+	target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER, PRIMARY KEY (id),
+	CONSTRAINT ck_agenda_step_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed')),
+	CONSTRAINT ck_agenda_step_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable','has_met','faction_member') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)),
+	FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(step_id) REFERENCES agenda_step (id),
+	FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
+    "CREATE UNIQUE INDEX idx_agenda_step_requirement_unique ON agenda_step_requirement "
+    "(step_id, type, target_entity_id, target_key)",
+    """CREATE TABLE quest_offer_requirement (
+	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, offer_id VARCHAR NOT NULL, step_id VARCHAR,
+	type VARCHAR NOT NULL, target_entity_id VARCHAR, target_key VARCHAR, threshold INTEGER, PRIMARY KEY (id),
+	CONSTRAINT ck_quest_offer_requirement_type CHECK (type IN ('knowledge','relation_gte','resource','location_reachable','has_met','faction_member','skill_rank_gte','quest_completed')),
+	CONSTRAINT ck_quest_offer_requirement_shape CHECK ((type NOT IN ('relation_gte','location_reachable','has_met','faction_member') OR target_entity_id IS NOT NULL) AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed') OR target_key IS NOT NULL) AND (type NOT IN ('relation_gte','resource','skill_rank_gte') OR threshold IS NOT NULL)),
+	FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(offer_id) REFERENCES quest_offer (id),
+	FOREIGN KEY(step_id) REFERENCES quest_offer_step (id), FOREIGN KEY(target_entity_id) REFERENCES entity (id))""",
+    "CREATE INDEX idx_quest_offer_requirement_offer ON quest_offer_requirement (offer_id)",
+    """CREATE TABLE quest_economy (
+	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, rate_money INTEGER, rate_relation INTEGER,
+	rate_fact INTEGER, rate_skill INTEGER, band_low_pct INTEGER, band_high_pct INTEGER,
+	updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, PRIMARY KEY (id),
+	CONSTRAINT ck_quest_economy_rates CHECK ((rate_money IS NULL OR rate_money >= 0) AND (rate_relation IS NULL OR rate_relation >= 0) AND (rate_fact IS NULL OR rate_fact >= 0) AND (rate_skill IS NULL OR rate_skill >= 0) AND (band_low_pct IS NULL OR band_low_pct >= 0) AND (band_high_pct IS NULL OR band_high_pct >= 0)),
+	FOREIGN KEY(world_id) REFERENCES world (id))""",
+    "CREATE UNIQUE INDEX idx_quest_economy_world ON quest_economy (world_id)",
+    """CREATE TABLE quest_offer (
+	id VARCHAR NOT NULL, world_id VARCHAR NOT NULL, giver_entity_id VARCHAR NOT NULL, title VARCHAR NOT NULL,
+	summary VARCHAR, repeatable BOOLEAN DEFAULT 0 NOT NULL, status VARCHAR DEFAULT 'open' NOT NULL,
+	created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL, updated_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
+	change_history JSON DEFAULT '[]' NOT NULL, PRIMARY KEY (id),
+	CONSTRAINT ck_quest_offer_status CHECK (status IN ('open','closed')),
+	FOREIGN KEY(world_id) REFERENCES world (id), FOREIGN KEY(giver_entity_id) REFERENCES entity (id))""",
+    "CREATE INDEX idx_quest_offer_world ON quest_offer (world_id)",
+)
+
+
+def fail(msg: str) -> None:
+    FAILURES.append(msg)
+
+
+def _fresh_db() -> str:
+    db_path = str(pathlib.Path(tempfile.mkdtemp()) / "check.db")
+    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
+    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
+    sys.path.insert(0, str(ROOT / "src"))
+    return db_path
+
+
+def _read(rel: str) -> str:
+    path = FRONTEND / rel
+    if not path.exists():
+        fail(f"{rel} is missing")
+        return ""
+    return path.read_text(encoding="utf-8")
+
+
+# --- DA1 -----------------------------------------------------------------------
+
+def _check_texts(table) -> dict[str, str]:
+    from sqlalchemy import CheckConstraint
+
+    return {c.name: str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}
+
+
+def _quoted(text: str) -> tuple[str, ...]:
+    return tuple(re.findall(r"'([^']*)'", text))
+
+
+def check_da1a() -> None:
+    from world_engine import models
+    from world_engine.quest_value import DEFAULT_RATES
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+    from world_engine.writes.quest_terms import ECONOMY_COLUMNS
+
+    for model, columns, checks in ((models.Debt, DEBT_COLUMNS, DEBT_CHECKS),
+                                   (models.DebtTerm, DEBT_TERM_COLUMNS, DEBT_TERM_CHECKS)):
+        found = tuple(c.name for c in model.__table__.columns)
+        if found != columns:
+            fail(f"DA1a: {model.__tablename__} columns are {found}")
+        if _check_texts(model.__table__) != checks:
+            fail(f"DA1a: {model.__tablename__} CHECKs are {_check_texts(model.__table__)}")
+    pairs = ((models.DEBT_ORIGINS, DEBT_CHECKS["ck_debt_origin"]), (models.DEBT_STATUSES, DEBT_CHECKS["ck_debt_status"]),
+             (models.DEBT_CURRENCIES, DEBT_TERM_CHECKS["ck_debt_term_currency"]))
+    for constant, check in pairs:
+        if tuple(constant) != _quoted(check):
+            fail(f"DA1a: {constant} differs from the CHECK {check}")
+    if "contact_entity_id" not in models.QuestOffer.__table__.columns:
+        fail("DA1a: quest_offer has no contact_entity_id")
+    for name, default in (("debt_fact_relation", 10), ("debt_skill_relation", 20)):
+        if name not in models.QuestEconomy.__table__.columns:
+            fail(f"DA1a: quest_economy has no {name}")
+        if DEFAULT_RATES.get(name) != default or name not in ECONOMY_COLUMNS:
+            fail(f"DA1a: {name} is not a default {default} economy column")
+    if EXPECTED_STATIC_SCHEMA_VERSION != "v2.19":
+        fail(f"DA1a: the code's schema version is {EXPECTED_STATIC_SCHEMA_VERSION}")
+
+
+def check_da1b() -> None:
+    from world_engine import day_plan, day_resolve
+
+    if tuple(day_plan.REQUIREMENT_TYPES[-2:]) != DEBT_FORMS:
+        fail(f"DA1b: REQUIREMENT_TYPES ends with {day_plan.REQUIREMENT_TYPES[-2:]}")
+    for form in DEBT_FORMS:
+        if form not in day_plan.ENTITY_TARGET_TYPES:
+            fail(f"DA1b: {form} is not an entity-target form")
+        if form in day_plan.THRESHOLD_TYPES or form in day_plan.MODEL_REQUIREMENT_TYPES:
+            fail(f"DA1b: {form} takes a threshold or is offered to the model")
+        if form not in day_plan._EVALUATORS or form not in day_resolve._BLOCKED_DETAIL_FR:
+            fail(f"DA1b: {form} has no evaluator or no French detail")
+    text = _read("creation/questRequirements.js")
+    for form in DEBT_FORMS:
+        if not re.search(rf"^\s+{form}: \{{ label: '[^']+', list: 'givers', column: 'entity', threshold: false \}},$",
+                         text, re.M):
+            fail(f"DA1b: questRequirements.js does not offer {form} on the givers list")
+    if "case 'givers': return choices.givers" not in text:
+        fail("DA1b: targetOptions has no givers list")
+
+
+def check_da1c(engine) -> None:
+    from sqlmodel import Session, func, select
+
+    from world_engine import link_author
+    from world_engine.cockpit.crud._shared import RELATION_TYPES
+    from world_engine.models import Entity, Relation, World
+    from world_engine.relation_orientation import RETIRED_RELATION_TYPES
+    from world_engine.writes import write_relation
+
+    if "debt" not in RETIRED_RELATION_TYPES:
+        fail("DA1c: debt is not retired")
+    if "debt" in RELATION_TYPES or "debt" in link_author._LINK_RELATION_TYPES:
+        fail("DA1c: debt is still offered as a relation type")
+    seed = (ROOT / "scripts" / "seed_pilot.py").read_text(encoding="utf-8")
+    template = re.search(r'NPC_LINK_PAIR_USER_TEMPLATE = """(.*?)"""', seed, re.S)
+    if template is None or "debt" in template.group(1) or "fascination" not in template.group(1):
+        fail("DA1c: the seeded link-pair prompt still offers debt, or was not found")
+    with Session(engine) as session:
+        world = World(name="Debts DA1", is_active=False)
+        session.add(world)
+        session.flush()
+        a, b = Entity(world_id=world.id, type="character", name="A"), Entity(world_id=world.id, type="character", name="B")
+        session.add_all([a, b])
+        session.commit()
+        before = session.exec(select(func.count()).select_from(Relation)).one()
+        for mode in ("set", "delta"):
+            try:
+                write_relation(session, mode=mode, world_id=world.id, entity_a_id=a.id, entity_b_id=b.id,
+                               type="debt", value=5)
+                fail(f"DA1c: write_relation({mode}) accepted the type debt")
+            except ValueError:
+                pass
+            session.rollback()
+        if session.exec(select(func.count()).select_from(Relation)).one() != before:
+            fail("DA1c: a refused debt relation wrote a row")
+
+
+# --- DA2 -----------------------------------------------------------------------
+
+def _shape(conn, table: str) -> list[tuple]:
+    return sorted((r[1], r[2], r[3], r[4]) for r in conn.execute(f"PRAGMA table_info({table})"))
+
+
+def _seed_v218(db_path: str) -> dict:
+    from sqlmodel import Session
+
+    from world_engine.db import create_db_and_tables, engine
+    from world_engine.models import Agenda, AgendaStep, Entity, SchemaMeta, World
+
+    create_db_and_tables()
+    ids: dict = {}
+    with Session(engine) as session:
+        world = World(name="Debts DA2", is_active=True)
+        session.add(world)
+        session.flush()
+        person = Entity(world_id=world.id, type="character", name="pc")
+        session.add(person)
+        session.flush()
+        agenda = Agenda(world_id=world.id, owner_entity_id=person.id, title="t", change_history=[])
+        session.add(agenda)
+        session.flush()
+        step = AgendaStep(agenda_id=agenda.id, step_order=1, objective="o", change_history=[])
+        session.add(step)
+        session.flush()
+        ids.update(world=world.id, person=person.id, step=step.id)
+        if session.get(SchemaMeta, 1) is None:
+            session.add(SchemaMeta(id=1, static_version="v2.18"))
+        session.commit()
+    engine.dispose()
+    with sqlite3.connect(db_path) as conn:
+        ids["model_shapes"] = {t: _shape(conn, t) for t in CHANGED_TABLES + ("debt", "debt_term")}
+        conn.execute("PRAGMA foreign_keys=OFF")
+        for table in ("debt_term", "debt") + CHANGED_TABLES:
+            conn.execute(f"DROP TABLE {table}")
+        for statement in _V218_DDL:
+            conn.execute(statement)
+        w, p, s = ids["world"], ids["person"], ids["step"]
+        conn.execute("INSERT INTO agenda_step_requirement (id, world_id, step_id, type, target_key) "
+                     "VALUES ('req-1', ?, ?, 'knowledge', 'fact-x')", (w, s))
+        conn.execute("INSERT INTO quest_offer (id, world_id, giver_entity_id, title) VALUES ('qo-1', ?, ?, 'q')", (w, p))
+        conn.execute("INSERT INTO quest_offer_requirement (id, world_id, offer_id, type, target_entity_id) "
+                     "VALUES ('qor-1', ?, 'qo-1', 'has_met', ?)", (w, p))
+        conn.execute("INSERT INTO quest_economy (id, world_id, rate_fact, band_high_pct) VALUES ('qe-1', ?, 7, 140)", (w,))
+        # A dangling reference this migration never wrote (AMENDMENT-0107-01).
+        conn.execute("INSERT INTO session (id, world_id, number) VALUES ('orphan-session', 'gone-world', 9)")
+    return ids
+
+
+def _state(db_path: str) -> dict:
+    with sqlite3.connect(db_path) as conn:
+        tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
+        return {
+            "version": conn.execute("SELECT static_version FROM schema_meta WHERE id = 1").fetchone()[0],
+            "rows": {t: conn.execute(f"SELECT id FROM {t} ORDER BY id").fetchall() for t in CHANGED_TABLES},
+            "economy": conn.execute("SELECT rate_fact, band_high_pct FROM quest_economy").fetchall(),
+            "sql": {t: conn.execute("SELECT sql FROM sqlite_master WHERE name=?", (t,)).fetchone()[0]
+                    for t in CHANGED_TABLES},
+            "shapes": {t: _shape(conn, t) for t in CHANGED_TABLES + ("debt", "debt_term") if t in tables},
+        }
+
+
+def _run_migration(db_path: str) -> subprocess.CompletedProcess:
+    env = dict(os.environ, WORLD_ENGINE_DATABASE_URL=f"sqlite:///{db_path}", WORLD_ENGINE_ENV="test")
+    return subprocess.run([sys.executable, str(MIGRATION)], env=env, capture_output=True,
+                          text=True, cwd=str(ROOT), timeout=120)
+
+
+def check_da2(db_path: str) -> None:
+    from world_engine.schema_version import EXPECTED_STATIC_SCHEMA_VERSION
+
+    ids = _seed_v218(db_path)
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("UPDATE schema_meta SET static_version = 'v2.17' WHERE id = 1")
+    before = _state(db_path)
+    result = _run_migration(db_path)
+    if result.returncode == 0 or _state(db_path) != before:
+        fail("DA2a: the migration ran on a v2.17 database or changed it")
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("UPDATE schema_meta SET static_version = 'v2.18' WHERE id = 1")
+    result = _run_migration(db_path)
+    if result.returncode != 0:
+        fail(f"DA2b: the migration failed: {result.stdout[-400:]} {result.stderr[-400:]}")
+        return
+    after = _state(db_path)
+    if after["rows"] != before["rows"] or not all(after["rows"].values()):
+        fail(f"DA2b: the rows are {after['rows']}")
+    if after["economy"] != [(7, 140)]:
+        fail(f"DA2b: the economy row is {after['economy']}")
+    for table in ("agenda_step_requirement", "quest_offer_requirement"):
+        absent = [form for form in DEBT_FORMS if f"'{form}'" not in after["sql"][table]]
+        if absent:
+            fail(f"DA2b: {table}'s stored CHECK lacks {absent}")
+    for table in ("quest_economy", "debt", "debt_term"):
+        if after["shapes"].get(table) != ids["model_shapes"][table]:
+            fail(f"DA2b: {table} is {after['shapes'].get(table)}, expected the model's")
+    if "contact_entity_id" not in {c[0] for c in after["shapes"]["quest_offer"]}:
+        fail("DA2b: quest_offer has no contact_entity_id")
+    if after["version"] != EXPECTED_STATIC_SCHEMA_VERSION:
+        fail(f"DA2b: schema_meta is {after['version']}")
+    if "Note: session rowid" not in result.stdout:
+        fail("DA2b: the orphan session row was not noted")
+    with sqlite3.connect(db_path) as conn:
+        conn.execute("PRAGMA foreign_keys=ON")
+        try:
+            conn.execute("INSERT INTO agenda_step_requirement (id, world_id, step_id, type, target_entity_id) "
+                         "VALUES ('req-2', ?, ?, 'has_debt_to', ?)", (ids["world"], ids["step"], ids["person"]))
+        except sqlite3.DatabaseError as exc:
+            fail(f"DA2b: a has_debt_to row cannot be inserted: {exc}")
+        dangling = [r for t in CHANGED_TABLES + ("debt", "debt_term")
+                    for r in conn.execute(f"PRAGMA foreign_key_check({t})").fetchall()]
+        if dangling:
+            fail(f"DA2b: foreign_key_check {dangling}")
+    again_before = _state(db_path)
+    result = _run_migration(db_path)
+    if result.returncode != 0 or _state(db_path) != again_before:
+        fail(f"DA2c: a second run exit {result.returncode} or changed a row")
+
+
+# --- DA3 -----------------------------------------------------------------------
+
+def _da3_world(session) -> dict:
+    from world_engine.models import Character, Entity, Faction, World
+
+    world = World(name="Debts DA3", is_active=False)
+    session.add(world)
+    session.flush()
+    ids = {"world": world.id}
+    for key in ("pc", "npc", "other"):
+        row = Entity(world_id=world.id, type="character", name=key.upper())
+        session.add(row)
+        session.flush()
+        session.add(Character(id=row.id, world_id=world.id, character_type="player" if key == "pc" else "npc"))
+        ids[key] = row.id
+    for key, kind in (("guild", "faction"), ("place", "location")):
+        row = Entity(world_id=world.id, type=kind, name=key.title())
+        session.add(row)
+        session.flush()
+        if kind == "faction":
+            session.add(Faction(id=row.id))
+        ids[key] = row.id
+    session.commit()
+    return ids
+
+
+def _debt(session, ids: dict, debtor: str, creditor: str, status: str = "open") -> None:
+    from world_engine.models import Debt
+    from world_engine.writes.facts import create_fact
+
+    fact = create_fact(session, world_id=ids["world"], content="dette", created_by="check", facet="information")
+    session.flush()
+    session.add(Debt(world_id=ids["world"], debtor_entity_id=ids[debtor], creditor_entity_id=ids[creditor],
+                     contact_entity_id=ids["other"] if creditor == "guild" else None, origin="creator",
+                     fact_id=fact.id, status=status,
+                     closed_at=None if status == "open" else datetime.now(UTC)))
+    session.commit()
+
+
+def _verdicts(session, pc, target: str) -> tuple[bool, bool]:
+    from world_engine.day_plan import RequirementSpec, evaluate_specs
+
+    has, none = evaluate_specs((RequirementSpec(type="has_debt_to", target_entity_id=target),
+                                RequirementSpec(type="no_debt_to", target_entity_id=target)), pc, session)
+    return has.met, none.met
+
+
+def check_da3(engine) -> None:
+    from sqlmodel import Session
+
+    from world_engine.day_plan import RequirementSpec, evaluate_specs
+    from world_engine.day_resolve import requirement_detail_fr
+    from world_engine.models import Character
+    from world_engine.writes.goals_agendas import _clean_requirement
+
+    with Session(engine) as session:
+        ids = _da3_world(session)
+        pc = session.get(Character, ids["pc"])
+        if _verdicts(session, pc, ids["npc"]) != (False, True):
+            fail("DA3: with no debt, has_debt_to is met or no_debt_to is not")
+        _debt(session, ids, "pc", "npc", status="settled")
+        _debt(session, ids, "pc", "other")
+        _debt(session, ids, "npc", "pc")
+        if _verdicts(session, pc, ids["npc"]) != (False, True):
+            fail("DA3: a settled debt, a debt to another or a debt owed to the character counted")
+        _debt(session, ids, "pc", "npc")
+        if _verdicts(session, pc, ids["npc"]) != (True, False):
+            fail("DA3: an open debt toward the NPC is not seen")
+        _debt(session, ids, "pc", "guild")
+        if _verdicts(session, pc, ids["guild"]) != (True, False):
+            fail("DA3: an open debt toward a faction is not seen")
+        verdicts = evaluate_specs((RequirementSpec(type="has_debt_to", target_entity_id=ids["place"]),
+                                   RequirementSpec(type="no_debt_to", target_entity_id=ids["npc"])), pc, session)
+        details = [requirement_detail_fr(v) for v in verdicts]
+        if details != ["il ne doit rien à Place", "il a encore une dette envers NPC"]:
+            fail(f"DA3: the French details are {details}")
+        for target, ok in (("npc", True), ("guild", True), ("place", False)):
+            for form in DEBT_FORMS:
+                try:
+                    _clean_requirement(session, ids["world"], 0, RequirementSpec(type=form, target_entity_id=ids[target]))
+                    accepted = True
+                except ValueError:
+                    accepted = False
+                if accepted != ok:
+                    fail(f"DA3: _clean_requirement {'refuses' if ok else 'accepts'} {form} toward {target}")
+
+
+def main() -> int:
+    db_path = _fresh_db()
+    check_da1a()
+    check_da1b()
+    check_da2(db_path)
+    from world_engine.db import create_db_and_tables, engine
+    create_db_and_tables()
+    check_da1c(engine)
+    check_da3(engine)
+    if FAILURES:
+        for msg in FAILURES:
+            print(f"FAIL: {msg}")
+        return 1
+    print("PASS: debts -- v2.19 lays the debt tables, an offer's contact and the economy's two debt "
+          "settings, migrates from v2.18 only, widens the requirement vocabulary with has_debt_to and "
+          "no_debt_to for the creator alone, judges an open debt toward a character or a faction, and "
+          "retires the relation type debt")
+    return 0
+
+
+if __name__ == "__main__":
+    sys.exit(main())
diff --git a/tooling/verify/checks/quests.py b/tooling/verify/checks/quests.py
index a547dcf..afcd2de 100644
--- a/tooling/verify/checks/quests.py
+++ b/tooling/verify/checks/quests.py
@@ -6,7 +6,7 @@ The lot adds its pieces brief by brief; this check grows with it (the
 the same commit.
 
 QA1 -- vocabulary (BRIEF-0108-A, static and import). `day_plan.REQUIREMENT_
-   TYPES` holds the eight forms; `MODEL_REQUIREMENT_TYPES` is exactly the
+   TYPES` holds the eight forms, then TICKET-0110's two debt forms; `MODEL_REQUIREMENT_TYPES` is exactly the
    model's four and a subset of it; `ENTITY_TARGET_TYPES` and
    `KEY_TARGET_TYPES` partition it and `THRESHOLD_TYPES` is inside it; the
    three `type NOT IN (...)` groups of `ck_agenda_step_requirement_shape`
@@ -103,6 +103,8 @@ FAILURES: list[str] = []
 
 MODEL_FORMS = ("knowledge", "relation_gte", "resource", "location_reachable")
 CREATOR_FORMS = ("has_met", "faction_member", "skill_rank_gte", "quest_completed")
+# TICKET-0110 (BRIEF-0110-A, G1): two more creator-only forms; `debts.py` owns them.
+DEBT_FORMS = ("has_debt_to", "no_debt_to")
 QUEST_TABLES = ("quest_offer", "quest_offer_step", "quest_offer_requirement", "quest")
 
 # `agenda_step_requirement` as v2.16 created it (dumped from `main` at 4b06dde).
@@ -150,7 +152,7 @@ def check_qa1() -> None:
     from world_engine.models import AgendaStepRequirement, QuestOfferRequirement
 
     types = day_plan.REQUIREMENT_TYPES
-    if tuple(types) != MODEL_FORMS + CREATOR_FORMS:
+    if tuple(types) != MODEL_FORMS + CREATOR_FORMS + DEBT_FORMS:
         fail(f"QA1: REQUIREMENT_TYPES is {types}")
     if tuple(day_plan.MODEL_REQUIREMENT_TYPES) != MODEL_FORMS or not set(MODEL_FORMS) <= set(types):
         fail(f"QA1: MODEL_REQUIREMENT_TYPES is {day_plan.MODEL_REQUIREMENT_TYPES}")
@@ -177,7 +179,7 @@ def check_qa1() -> None:
             day_plan._validate_requirement({"type": form, "target_key": "k", "threshold": 1})
         except llm_parse.LlmParseError as exc:
             fail(f"QA1: the model's parser refuses {form!r}: {exc}")
-    for form in CREATOR_FORMS:
+    for form in CREATOR_FORMS + DEBT_FORMS:
         try:
             day_plan._validate_requirement({"type": form, "target_key": "k", "threshold": 1})
         except llm_parse.LlmParseError:
diff --git a/tooling/verify/checks/world_cascade.py b/tooling/verify/checks/world_cascade.py
index 37035fa..f09a961 100644
--- a/tooling/verify/checks/world_cascade.py
+++ b/tooling/verify/checks/world_cascade.py
@@ -204,6 +204,11 @@ _FIXTURE: tuple[tuple[str, dict], ...] = (
     ("quest_term", {"id": "qt-{w}", "world_id": "{w}", "quest_id": "qu-{w}", "term_order": 1,
                     "direction": "cost", "currency": "money", "amount": 3}),
     ("quest_economy", {"id": "qe-{w}", "world_id": "{w}", "rate_fact": 4}),
+    ("debt", {"id": "de-{w}", "world_id": "{w}", "debtor_entity_id": "{w}-char",
+              "creditor_entity_id": "{w}-fac", "origin": "quest", "origin_quest_id": "qu-{w}",
+              "fact_id": "fa-{w}"}),
+    ("debt_term", {"id": "dt-{w}", "world_id": "{w}", "debt_id": "de-{w}", "term_order": 1,
+                   "currency": "item", "item_id": "{w}-item", "amount": 2}),
 )
 
 
diff --git a/world-engine-schema-changelog.md b/world-engine-schema-changelog.md
index a2d171e..37316eb 100644
--- a/world-engine-schema-changelog.md
+++ b/world-engine-schema-changelog.md
@@ -13,6 +13,16 @@ boot guard checks against the stored `schema_meta` row.
 
 ## CHANGELOG
 
+- **v2.19** — TICKET-0110, BRIEF-0110-A: debts. `debt` (debtor, creditor,
+  a faction creditor's contact, origin, reason, secrecy, its fact, status
+  open/settled/forgiven -- never deleted) and `debt_term` (money, items, a
+  fact to deliver, a skill to teach) are added. `agenda_step_requirement`'s
+  and `quest_offer_requirement`'s two CHECKs gain `has_debt_to` and
+  `no_debt_to` (an entity target). `quest_offer.contact_entity_id` and
+  `quest_economy.debt_fact_relation`/`debt_skill_relation` are added. The
+  relation type `debt` is retired in code. `migrate_v2_19_debts.py`
+  rebuilds the three tables whose CHECK changes, adds the column, creates
+  the two tables, and refuses a database older than v2.18.
 - **v2.18** — TICKET-0109, BRIEF-0109-A: objects held in quantity, quest
   terms, the quest economy. `item` becomes a kind: `owner_id`,
   `location_id`, `equipped` and `ck_item_equipped_owner` dropped, `value`
diff --git a/world-engine-schema.md b/world-engine-schema.md
index e6b5a12..e516eaa 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -1,6 +1,6 @@
 # WORLD ENGINE — Database Schema
 
-Current schema version: v2.18
+Current schema version: v2.19
 Append-only history: world-engine-schema-changelog.md (repo root)
 
 -----
@@ -531,10 +531,12 @@ CREATE TABLE relation (
   entity_a_id         TEXT NOT NULL REFERENCES entity(id),
   entity_b_id         TEXT NOT NULL REFERENCES entity(id),
   type                TEXT NOT NULL,
-                      -- ally | enemy | debt | fear | fascination |
+                      -- ally | enemy | fear | fascination |
                       -- shared_secret | instrumentalizes | interest |
                       -- indifference | rejection | passive_attention | other |
                       -- connects_to | controls
+                      -- `debt` retired at v2.19 (TICKET-0110, I2): « X owes
+                      -- Y » is a `debt` row; `write_relation` refuses it.
   direction           TEXT DEFAULT 'mutual',
                       -- mutual | a_to_b | b_to_a
                       -- NOTE: magic relations = always a_to_b
@@ -2248,7 +2250,11 @@ a label); `has_met` an encounter row of the pair; `faction_member` an
 active membership of the target faction; `skill_rank_gte` the rank held in
 a base domain or a skill definition (`target_key`), `threshold` 1-5;
 `quest_completed` a quest taken from the offer `target_key` whose agenda is
-`completed`. Curated plan metadata, same family as `npc_schedule` -- no
+`completed`. Ten forms since v2.19 (TICKET-0110, BRIEF-0110-A, G1):
+`has_debt_to` and `no_debt_to`, creator only, with `target_entity_id` the
+creditor (a character or a faction) -- the character is the debtor of at
+least one OPEN `debt` toward it, or of none; existence only, no threshold.
+Curated plan metadata, same family as `npc_schedule` -- no
 `change_history`. THE POSITIONAL WALL: `location_reachable`'s target lives
 HERE, never on `agenda_step` -- a requirement states "the player must be
 able to reach L", a precondition on the player, never a position of an NPC
@@ -2262,12 +2268,14 @@ CREATE TABLE agenda_step_requirement (
   step_id           TEXT NOT NULL REFERENCES agenda_step(id),
   type              TEXT NOT NULL
                       CHECK (type IN ('knowledge','relation_gte','resource','location_reachable',
-                                      'has_met','faction_member','skill_rank_gte','quest_completed')),
+                                      'has_met','faction_member','skill_rank_gte','quest_completed',
+                                      'has_debt_to','no_debt_to')),
   target_entity_id  TEXT REFERENCES entity(id),
   target_key        TEXT,
   threshold         INTEGER,
   CHECK (
-    (type NOT IN ('relation_gte','location_reachable','has_met','faction_member')
+    (type NOT IN ('relation_gte','location_reachable','has_met','faction_member',
+                  'has_debt_to','no_debt_to')
        OR target_entity_id IS NOT NULL)
     AND (type NOT IN ('knowledge','resource','skill_rank_gte','quest_completed')
        OR target_key IS NOT NULL)
@@ -2290,12 +2298,16 @@ accepted again once the last quest taken from it is over; any other offer
 once per character. Its steps and requirements are replaced whole on save
 (the `npc_price` full-replace precedent); the offer row keeps a
 `change_history`. Written only by `writes.write_quest_offer`.
+`contact_entity_id` (v2.19, TICKET-0110, X1): when the giver is a faction,
+the active member who speaks for it -- the person a debt born of the offer
+is linked to; NULL for a character giver, optional for a faction.
 
 ```sql
 CREATE TABLE quest_offer (
   id               TEXT PRIMARY KEY,
   world_id         TEXT NOT NULL REFERENCES world(id),
   giver_entity_id  TEXT NOT NULL REFERENCES entity(id),
+  contact_entity_id TEXT REFERENCES entity(id),   -- v2.19
   title            TEXT NOT NULL,
   summary          TEXT,
   repeatable       BOOLEAN NOT NULL DEFAULT 0,
@@ -2436,7 +2448,10 @@ the `conversation_window_config` precedent. Each column NULL, or no row,
 reads the code's default (`quest_value.DEFAULT_RATES`: money 1, relation
 point 1, fact 5, skill 20; band 100-150 %); an item's rate is its own
 `value`. The unit is a display -- never converted, never spent. Written
-only by `writes.upsert_quest_economy`.
+only by `writes.upsert_quest_economy`. `debt_fact_relation` and
+`debt_skill_relation` (v2.19, TICKET-0110): what the creditor's regard
+toward the debtor falls by when a debt's fact or skill can no longer be
+delivered because he already holds it (defaults 10 and 20).
 
 ```sql
 CREATE TABLE quest_economy (
@@ -2448,6 +2463,8 @@ CREATE TABLE quest_economy (
   rate_skill     INTEGER,
   band_low_pct   INTEGER,
   band_high_pct  INTEGER,
+  debt_fact_relation   INTEGER,           -- v2.19
+  debt_skill_relation  INTEGER,           -- v2.19
   updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
   CHECK (every column IS NULL OR >= 0)
 );
@@ -2456,6 +2473,87 @@ CREATE UNIQUE INDEX idx_quest_economy_world ON quest_economy(world_id);
 
 -----
 
+### `debt`
+
+What one entity owes another (v2.19, TICKET-0110, BRIEF-0110-A, J2). Born
+of a service asked of a character (`origin = 'service'`, S2), of a quest
+settled on credit (`'quest'`, A2, with `origin_quest_id`), or of the
+creator's hand (`'creator'`). The debtor is a character; the creditor a
+character or a faction (J1). A faction creditor always names its contact,
+an active member (X1); a character creditor never does (writer-checked).
+`reason` is an optional motive, carried into the fact (V1). `is_secret`
+(F-b1) makes both parties' knowledge rows secret. `fact_id` is the debt's
+fact: a free `information` fact whose participants are the debtor, the
+creditor and the contact (F-a); the debtor and the creditor (his contact
+for a faction) learn it at `knows`, and a faction's members know a debt
+that is not secret through a `faction` default (U1). What is owed lives in
+`debt_term` (C2); its indicative value is computed at read, never stored.
+A debt is SETTLED or FORGIVEN, never deleted: `status` leaves `open` once,
+with `closed_at` and, for a remission, `closed_note`; the fact receives a
+`changement` then. This table is the one way to say « X owes Y » (I2).
+Written only by `writes/debts.py`.
+
+```sql
+CREATE TABLE debt (
+  id                 TEXT PRIMARY KEY,
+  world_id           TEXT NOT NULL REFERENCES world(id),
+  debtor_entity_id   TEXT NOT NULL REFERENCES entity(id),
+  creditor_entity_id TEXT NOT NULL REFERENCES entity(id),
+  contact_entity_id  TEXT REFERENCES entity(id),
+  origin             TEXT NOT NULL CHECK (origin IN ('service','quest','creator')),
+  origin_quest_id    TEXT REFERENCES quest(id),
+  reason             TEXT,
+  is_secret          BOOLEAN NOT NULL DEFAULT 0,
+  fact_id            TEXT NOT NULL REFERENCES fact(id),
+  status             TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','settled','forgiven')),
+  created_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
+  closed_at          DATETIME,
+  closed_note        TEXT,
+  CHECK (debtor_entity_id <> creditor_entity_id),
+  CHECK ((origin = 'quest') = (origin_quest_id IS NOT NULL)),
+  CHECK ((status = 'open') = (closed_at IS NULL))
+);
+CREATE INDEX idx_debt_world ON debt(world_id);
+CREATE INDEX idx_debt_debtor ON debt(debtor_entity_id);
+CREATE INDEX idx_debt_creditor ON debt(creditor_entity_id);
+```
+
+-----
+
+### `debt_term`
+
+One thing a debt owes (v2.19, C2/T1), in order. `currency`: `money` and
+`item` count (`amount`); `fact` is delivered -- the debtor must know it,
+the creditor (his contact for a faction) learns it; `skill` is taught --
+the debtor must be at Maître in a skill definition. No relation term:
+regard is not repaid. When the receiver already holds the fact or the
+skill, that term is settled by his regard toward the debtor falling by the
+world's `debt_fact_relation` or `debt_skill_relation`. Written with its
+debt; immutable.
+
+```sql
+CREATE TABLE debt_term (
+  id          TEXT PRIMARY KEY,
+  world_id    TEXT NOT NULL REFERENCES world(id),
+  debt_id     TEXT NOT NULL REFERENCES debt(id),
+  term_order  INTEGER NOT NULL,
+  currency    TEXT NOT NULL CHECK (currency IN ('money','item','fact','skill')),
+  item_id     TEXT REFERENCES item(id),
+  fact_id     TEXT REFERENCES fact(id),
+  skill_key   TEXT,
+  amount      INTEGER,
+  CHECK (
+    (currency NOT IN ('money','item') OR (amount IS NOT NULL AND amount >= 1))
+    AND (currency <> 'item' OR item_id IS NOT NULL)
+    AND (currency <> 'fact' OR fact_id IS NOT NULL)
+    AND (currency <> 'skill' OR skill_key IS NOT NULL)
+  )
+);
+CREATE INDEX idx_debt_term_debt ON debt_term(debt_id);
+```
+
+-----
+
 ### `goal_agenda_link`
 
 Many-to-many tie between an `npc_goal` and the `agenda` intrigue(s) it
````

## Scope OUT

- Any writer of `debt` or `debt_term` (B); any route or surface of debts (B, C, D).
- The offer's contact in the writer, the routes or the editor (B, C): this brief only adds the column.
- Converting any existing relation or staged link: production holds no `debt` relation (E1).
- Running the migration or the prompt script on the production database (the live gate).
- The relation's change at borrowing and repayment (E -- its own ticket, with a calendar).
- The erosion of an unpaid debt (H1): no world time exists.
- Settling a debt « otherwise » (C3), a partial repayment (D2), a debt proposed by the model.
- Porting « Mes savoirs » into Journée; rank trials (TICKET-0111); any change to `legacy.html` or Play.
- Any change to the day-chain prompts, and to any prompt but `pt-npc-link-pair`'s type list.
- Every later brief of this lot.

## Invariants to defend

**History is sacred:** the migration copies every row of the three tables it rebuilds (row counts post-checked) and changes no `relation`. **Schema version triad:** the constant, the doc header and the migration's `schema_meta` convergence move together in this commit. **The model proposes, Python judges:** the model's parser still accepts its four forms only; the two debt forms are creator-only. **One prompt write path:** the delivery script writes through `write_prompt_version` and keeps a creator's edit (it edits one fragment of the current head).

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- A check other than `quests.py`, `day_plan.py`, `day_narration.py`, `world_cascade.py` or `debts.py` binds the requirement vocabulary or the relation types and turns red.
- `write_relation` is over 80 lines after the commit.

ADAPT:
- `git apply` fails only on `tooling/standards/ARCHITECTURE_DECISIONS.md` because another entry landed above the footer: insert this brief's entry just above the `---` / `*Co-built…*` footer by hand, then regenerate the index.
- `npm run build` names a different asset hash than the prototype's: commit what it builds (`frontend_build_fresh.py` judges the manifest, not the name).

REPORT-ONLY:
- Timing of the corpus run.
- `day_mutations.py` crashing when `WORLD_ENGINE_ENV` is unset (pre-existing; run the corpus with `WORLD_ENGINE_ENV=test`).
- `pyflakes` reporting `VetoVerdict` imported but unused in `routes/day.py` (pre-existing).
- Svelte a11y warnings during the build on `QuestOffers.svelte:90`, `Journee.svelte`'s day rows, `PjSkillFiche.svelte`, `PjCreatePanel.svelte` and `Graph.svelte` (pre-existing); npm's `EBADENGINE` notice on a Node older than 24.18.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- `git diff --stat HEAD~1` lists exactly the files of the embedded diff, plus `tooling/standards/DECISIONS_INDEX.md` and `src/world_engine/cockpit/static/`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/debts.py` -> `PASS: debts -- v2.19 lays the debt tables, an offer's contact and the economy's two debt settings, migrates from v2.18 only, widens the requirement vocabulary with has_debt_to and no_debt_to for the creator alone, judges an open debt toward a character or a faction, and retires the relation type debt`
- `quests.py`, `day_plan.py`, `day_narration.py`, `world_cascade.py`, `single_canon_write.py`, `schema_version_agreement.py`, `prompt_version.py`, `module_budget.py`, `function_length.py`, `undefined_names.py`, `frontend_build_fresh.py`, `decisions_index.py` -> `PASS`.
- Mutation tests, each red then reverted (`debts.py` exits 1 with the rule named): in `src/world_engine/day_plan.py`, `"faction_member", "has_debt_to", "no_debt_to",` -> `"faction_member", "has_debt_to",` -> `DA1b`; in `scripts/migrate_v2_19_debts.py`, `    "quest_offer_requirement": models.QuestOfferRequirement,` -> `(line removed)` -> `DA2b`; in `src/world_engine/day_plan.py`, `Debt.creditor_entity_id == creditor_id, Debt.status == "open",` -> `Debt.creditor_entity_id == creditor_id,` -> `DA3`; in `src/world_engine/relation_orientation.py`, `RETIRED_RELATION_TYPES: tuple[str, ...] = ("debt",)` -> `RETIRED_RELATION_TYPES: tuple[str, ...] = ()` -> `DA1c`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 143/143.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `A DEBT IS A ROW, NEVER A RELATION TYPE (TICKET-0110) -- TEN REQUIREMENT FORMS, AN OFFER'S CONTACT (BRIEF-0110-a, schema v2.19)`; `world-engine-schema.md` (header v2.19, `relation.type`, `agenda_step_requirement`, `quest_offer`, `quest_economy`, `debt`, `debt_term`) and `world-engine-schema-changelog.md` -- all in the diff. No CLAUDE.md change (37 838 of 38 000).
