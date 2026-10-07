# BRIEF 0110-B — "A debt written whole with its fact, repaid at once or forgiven; a service owes the rest, a quest settles on credit"

Lot: LOT-0110-debts-services.md (authoritative on conflict)
Depends on: BRIEF-0110-A

## Anchors to confirm (Mini-RECON)

Halt if any has moved (after BRIEF-0110-A's commit). The facts carried below quote `main`'s line numbers, as the lot does; where A moved a line, the anchor here gives where it now is.

- `src/world_engine/writes/quest_settlement.py:80` -> `def _cost_refusals(db: Session, quest: Quest, giver_id: str) -> list[str]:`
- `src/world_engine/writes/quest_settlement.py:122` -> `def _money(db: Session, quest: Quest, payer: str, payee: str, amount: int, reason: str) -> None:`
- `src/world_engine/writes/quest_settlement.py:161` -> `def _apply_term(db: Session, quest: Quest, term, giver_id: str, reason: str) -> None:`
- `src/world_engine/writes/quest_settlement.py:181` -> `def settle_quest(db: Session, *, quest: Quest) -> Quest:`
- `tooling/verify/canon_write_policy.txt:64` -> `src/world_engine/writes/quest_settlement.py::settle_quest       quest`
- `src/world_engine/writes/quests.py:78` -> `def _snapshot(offer: QuestOffer) -> None:`
- `src/world_engine/writes/quests.py:101` -> `terms: Optional[list[TermSpec]] = None,`
- `src/world_engine/quest_reads.py:93` -> `def editor_choices(world_id: str, db: Session) -> dict:`
- `src/world_engine/quest_settlement_view.py:66` -> `def settlement_context(db: Session, quest: Quest) -> dict:`
- `src/world_engine/cockpit/app.py:142` -> `app.include_router(_routes_quests.router)`
- `src/world_engine/cockpit/routes/quests.py:71` -> `class OfferBody(BaseModel):`
- `src/world_engine/models/quests.py:283` -> `class Debt(SQLModel, table=True):` (A)
- `src/world_engine/quest_value.py:28` -> `"debt_fact_relation": 10, "debt_skill_relation": 20,` (A)
- `tooling/verify/checks/debts.py:457` -> `check_da3(engine)` (A)
- No `src/world_engine/writes/debts.py` exists.
- No `src/world_engine/cockpit/routes/debts.py` exists.

## Facts carried

### R-04 — the fact spine: a free fact, its participants, its changes [M]
Opened: `src/world_engine/models/canon_knowledge.py:87-125` (`Fact`:
`ck_fact_spine_exclusive`, a free fact has no typed FK), `:133-145`
(`FactParticipant`); `src/world_engine/writes/facts.py:56`
(`FACT_CHANGE_KINDS = ("correction", "changement")`), `:75-106`
(`create_fact`, `facet` required), `:130-139` (`update_fact_content`: the
previous content appended to `change_history` with its `kind`), `:175-201`
(`attach_participants`, free facts only); `src/world_engine/facets.py:75`
(`information`: family `monde`, granularity `affirmation`, preset `none`);
`src/world_engine/prose_render.py:28-35` (`TOKEN_RE`, `entity_token`);
`src/world_engine/writes/relations.py:150-155` (`_endpoint_tokens`: the
precedent for a server-written fact naming its parties by token).
Consequence: a debt's fact is a free `information` fact, aspect `dette`,
participants debtor, creditor, contact; its text names them by token;
settling and forgiving rewrite it as a `changement` (C-04).

### R-05 — knowledge: secrecy per row, contact dated by the stored row [M]
Opened: `src/world_engine/models/canon_knowledge.py:199-239` (`Knowledge`:
`is_secret` `:225`, per knower; unique `(entity_id, fact_id)`);
`src/world_engine/writes/knowledge.py:241-290` (`write_knowledge`: a create
on `fact_id` attaches to the fact, content may be None), `:202-213` (an
update appends the previous state and sets `updated_at = now`), `:77`
(`knowledge_level_rank`); `src/world_engine/knowledge_resolve.py:34-37`,
`:203-214` (`_as_of`: the later of the anchors' last contact and the stored
row's `updated_at`), `:46-49` (a resolved default never carries
`is_secret`); `src/world_engine/fact_refs.py:57-67` (`find_held` on a
`fact_id`: the stored row).
Finding: after a `changement`, a party whose row is older than the change
would know the old text.
Consequence: F-b1 is the parties' rows `is_secret`; closing a debt
refreshes both parties' rows (same values, `updated_at` now) so they know
at once (C-04).

### R-06 — a faction's members know through a `faction` default [M]
Opened: `src/world_engine/models/canon_knowledge.py:164-193` (`FactDefault`:
`scope_type IN ('world','faction','location','rencontre')`, unique `(fact,
scope_type, scope_id)`); `src/world_engine/writes/facts.py:204-221`
(`create_fact_default`).
Consequence: U1 -- a debt toward a faction that is not secret gets one
`faction` default at `knows` (C-03).

### R-08 — the settlement's internals [M]
Opened: `src/world_engine/writes/quest_settlement.py:64-69` (`skill_row`),
`:80-108` (`_cost_refusals`, private, French), `:111-119`
(`settlement_refusals`), `:122-126` (`_money`: `source_type="quest"`
hard-written), `:129-135` (`_items`), `:145-158` (`_skill_reward`),
`:161-178` (`_apply_term(db, quest, …)`), `:181-198` (`settle_quest`: the
`quest` write); `src/world_engine/quest_settlement_view.py:23`
(imports `skill_row`, `settlement_refusals`, `skill_reward_points`);
`tooling/verify/canon_write_policy.txt:63-64` (`settle_quest` allow-listed
for `quest`).
Finding: every term application is bound to a quest row and to the
`quest` ledger origin; the refusals are strings with no kind.
Consequence: B makes them reusable without changing what a settlement
does: `cost_checks` returns `(kind, reason)`, `apply_term` takes the world
and the character (and `amount`, `source_type`), `finish_settlement` holds
the `quest` write -- the same one site, relocated in the policy (C-05).

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

### R-10 — an offer names a giver, never a person for a faction [M]
Opened: `src/world_engine/models/quests.py:39-61` (`QuestOffer`:
`giver_entity_id` `:49`, a character or a faction, H1);
`src/world_engine/writes/quests.py:71-75` (`_check_giver`), `:78-86`
(`_snapshot`), `:89-147` (`write_quest_offer`);
`src/world_engine/cockpit/routes/quests.py:71-81` (`OfferBody`);
`src/world_engine/quest_reads.py:61-78` (`offer_dict`), `:93-116`
(`editor_choices`); `frontend/src/creation/questOffers.svelte.js:118-130`
(`draftBody`); `frontend/src/creation/QuestOffers.svelte:104-109` (« Donnée
par »).
Consequence: X1 -- `quest_offer.contact_entity_id`, written by the
writer, shown and edited in the offer editor.

### R-11 — an active membership is a row with no `left_at` [M]
Opened: `src/world_engine/models/canon_faction.py:85-129`
(`FactionMembership`: `left_at` `:129`, NULL = active;
`idx_membership_unique_active` `:103-106` on `left_at IS NULL`).
Consequence: « active member » is `left_at IS NULL` (C-03).

### R-12 — money, items and skills: the writers a debt calls [M]
Opened: `src/world_engine/ledger.py:18-23` (`get_balance`);
`src/world_engine/writes/characters.py:213-250` (`write_ledger_entry`: no
balance guard, INSERT only), `:105-142` (`write_skill_row`: refuses a row
already held); `src/world_engine/models/canon.py:467` (`ledger.source_type`
TEXT, no CHECK); `src/world_engine/writes/items.py:39-74`
(`write_holding`); `src/world_engine/holdings.py:16-20` (`held_quantity`);
`src/world_engine/skill_access.py:82-91` (`held_rank`), `:94-100`
(`skill_label`);
`src/world_engine/skill_ranks.py:30` (`MAX_RANK = 5`).
Consequence: repayment uses these writers; the ledger origins `debt` and
`service` need no migration (documented in the schema doc).

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

### C-03 — the owed currencies and the debt writer (family contract)
Produced by: BRIEF-0110-B   Consumed by: B (C-04, C-05), C, D
Written before its members; re-read after the last (`skill`).

`DebtTermSpec(currency, item_id=None, fact_id=None, skill_key=None,
amount=None)`. The receiver of a fact or a skill is the creditor, his
contact for a faction (`receiver_of`).

| currency | target | amount | `clean_debt_term` refuses | owed line (`debt_term_line`) | in the fact | value |
|---|---|---|---|---|---|---|
| `money` | -- | >= 1 | amount < 1 | « N pièce(s) » | « N pièce(s) » | N x rate_money |
| `item` | `item_id`, an item of the world | >= 1 | not an item; amount < 1 | « N × name » | « N × [token] » | N x item.value |
| `fact` | `fact_id`, a fact of the world | -- | a fact elsewhere | « le savoir « text » » | « le savoir « text » » | rate_fact |
| `skill` | `skill_key`, a skill definition of the world | -- | a base domain; an unknown skill | « l'enseignement de « label » » | same | rate_skill |

`clean_debt_term` also refuses a currency outside `DEBT_CURRENCIES`.
- `prepare_debt(db, *, world_id, debtor_id, creditor_id, contact_id,
  origin, origin_quest_id=None, reason=None, is_secret=False, terms) ->
  PreparedDebt`: case table (b-1), nothing written. `reason` is stripped,
  empty -> None.
- `write_debt(db, prepared, *, changed_by) -> Debt`: the fact (free,
  `information`, aspect `dette`, `default_level` `unaware`, text
  `debt_fact_text(..., state="open")`), its participants (debtor, creditor,
  contact if any, in that order), the row `open`, its terms in order
  (`term_order` from 1), the parties' knowledge and the faction default
  (b-5). `create_debt(db, *, changed_by, **fields)` is the two in a row.
- `debt_fact_text(db, *, debtor_id, creditor_id, contact_id, terms, reason,
  state, note=None)`: with `D`, `C`, `K` the parties' tokens, `via` = «
  (par l'entremise de K) » or nothing, `tail` = « : owed » + « — reason »
  if any, `owed` = the terms' fact phrases joined by « , » or « une
  faveur »: `open` -> « D doit à C{via}{tail}. »; `settled` -> « D a réglé
  sa dette envers C{via}{tail}. »; `forgiven` -> « C a fait grâce à D de sa
  dette{via}{tail}. » + « (note) » if any.
- `is_active_member(db, character_id, faction_id) -> bool` (R-11).
- Constants: `DEBT_FACT_LEVEL = "knows"`, `DEBT_FACT_ASPECT = "dette"`,
  `DEBT_SOURCE = "dette"`, `DEBT_LEDGER_SOURCE = "debt"`,
  `STALE_RELATION_SETTING = {"fact": "debt_fact_relation", "skill":
  "debt_skill_relation"}`.

### C-04 — repaying and forgiving
Produced by: BRIEF-0110-B   Consumed by: C, D (through C-07)
- `debt_refusals(db, debt) -> list[str]` (French): case table (b-2).
- `settle_debt(db, *, debt, changed_by) -> Debt`: `ValueError(joined)` on a
  refusal, before any write; else every term delivered in term order (b-3),
  then closed `settled`.
- `forgive_debt(db, *, debt, note, changed_by) -> Debt`: `ValueError` when
  not `open`; else closed `forgiven`, `closed_note` the stripped note or
  None.
- Closing: `status`, `closed_at = now`, `closed_note`; the fact rewritten
  by `update_fact_content(kind="changement")` with the closed state's text;
  the debtor's and the receiver's knowledge rows refreshed (b-5). The
  ledger lines carry `source_type` `debt`, reason « Dette envers C ».

### C-05 — where a debt comes from (service, credit) and the settlement made reusable
Produced by: BRIEF-0110-B   Consumed by: C-06, C-07
- `writes/quest_settlement.py`: `cost_checks(db, character_id, terms,
  giver_id) -> [(kind, reason)]`, kind `money`, `item` or `other`, the
  reasons `_cost_refusals` gave, in its order; `closed_refusal(db, quest)`;
  `settlement_refusals` = `[closed]` or the reasons of `cost_checks`
  (unchanged output); `apply_term(db, *, world_id, character_id, term,
  giver_id, reason, source_type="quest", amount=None)` (the D table of
  0109; `amount` replaces a money or item term's own); `in_order(terms)`;
  `finish_settlement(db, quest)` (the agenda `completed` when it is not,
  `settled_at`); `settle_quest` = refusals, `apply_term` over `in_order`,
  `finish_settlement`. `canon_write_policy.txt` moves the `quest` site from
  `settle_quest` to `finish_settlement`.
- `writes/debt_sources.py`:
  - `request_service(db, *, character, provider_id, on_behalf_of_id, terms:
    [TermSpec], owed: [DebtTermSpec], reason, is_secret) -> Debt`: case
    table (b-7), nothing written before every check; then `apply_term` over
    `in_order` of the cleaned terms (giver = the provider, `source_type`
    `service`, reason « Service de P »), then `write_debt` (origin
    `service`, `changed_by` `service`).
  - `credit_plan(db, quest) -> CreditPlan(refusals, paid, owed)`: case
    table (b-4).
  - `credit_contact(db, quest, creditor_id, contacts) -> Optional[str]`:
    a character creditor -> None; a faction -> `contacts[creditor]` if set,
    else the offer's contact when the faction is the giver, else None.
  - `settle_quest_on_credit(db, *, quest, contacts, is_secret) -> Quest`:
    `ValueError` on any plan refusal, and « il faut choisir le membre de « F
    » qui porte la dette » for a faction creditor with no contact, before
    any write; every debt prepared (origin `quest`, `origin_quest_id`,
    reason « Quête « title » », the shortfall terms); then `apply_term` over
    `in_order` with `amount = paid` for a money or item cost (skipped when
    0), `finish_settlement`, then each debt written (`changed_by`
    `quest_credit`).
- `writes/quests.py`: `write_quest_offer(..., contact_entity_id=None)`;
  `_check_contact`: a contact on a character giver, or one who is not an
  active character member of the faction giver, raises; the value is
  written as given; `_snapshot` records it.

### C-06 — what the surfaces read
Produced by: BRIEF-0110-B   Consumed by: C, D
- `debt_reads.debt_dict(debt, db)` keys, always all present: `id,
  debtor_id, debtor_name, creditor_id, creditor_name, contact_id,
  contact_name, origin, origin_label` (« service », « création », « quête
  « title » »)`, reason, is_secret, status, status_label` (« due »,
  « réglée », « remise »)`, created_at, closed_at, closed_note, terms`
  (`[{currency, item_id, fact_id, skill_key, amount, line}]`)`, value` (the
  sum of `term_value` at the world's rates). No agenda or step id.
- `world_debts(world_id, db)`: every debt, open first, then most recent.
- `player_debts(character, db)`: `{owes, owed}` -- the debts he is debtor
  of, creditor of -- each with `refusals` (C-04, empty when closed) and
  `repayable`.
- `quest_reads.offer_dict` gains `contact_entity_id`, `contact_name`;
  `editor_choices` gains `members: {faction_id: [{id, name}]}` (active
  character members, by name).
- `quest_settlement_view.settlement_context` gains `credit: {possible,
  refusals, debts: [{creditor_id, creditor_name, is_faction, lines,
  contact_id, members}]}` (`contact_id` from `credit_contact(…, {})`).

### C-07 — routes
Produced by: BRIEF-0110-B   Consumed by: C, D

| route | body | success | refusal |
|---|---|---|---|
| `GET /api/debts` | -- | `[debt_dict]` | 400 no world |
| `POST /api/debts` | `{debtor_entity_id, creditor_entity_id, contact_entity_id, reason, is_secret, terms: [{currency, item_id, fact_id, skill_key, amount}]}` | 201 `debt_dict` (origin `creator`) | 422 |
| `POST /api/debts/{id}/repay` | -- | `debt_dict` | 404 other world, 409 refusal |
| `POST /api/debts/{id}/forgive` | `{note}` | `debt_dict` | 404, 409 closed |
| `GET /api/journee/debts` | -- | `player_debts` | 400 |
| `POST /api/services` | `{provider_entity_id, on_behalf_of_id, terms: [TermBody], owed: [owed term], reason, is_secret}` | 201 `player_debts` | 422 |
| `POST /api/quests/{id}/settle-on-credit` | `{is_secret, contacts: {faction_id: member_id}}` | `journee_payload` | 404 not his, 409 refusal |
| `POST`/`PUT /api/quest-offers…` | `OfferBody` + `contact_entity_id` | `offer_dict` | 422 |

`routes/debts.py` is registered after `routes/quests.py` in `app.py`.

## Case tables carried (lot, gate output (b))

**b-1 — `prepare_debt`**, checked in this order (the first failure raises):

| input | result |
|---|---|
| debtor not an active character of the world | `ValueError` |
| creditor not an active character or faction of the world | `ValueError` |
| creditor = debtor | `ValueError` |
| character creditor with a contact | `ValueError` |
| faction creditor with no contact | `ValueError` (X1) |
| contact not an active character, or not an active member of the faction | `ValueError` |
| origin outside `DEBT_ORIGINS` | `ValueError` |
| origin `quest` without a quest of the world, or a quest with another origin | `ValueError` |
| a term refused by `clean_debt_term` (C-03) | `ValueError` naming the term |
| no term and no reason | `ValueError` |
| otherwise | `PreparedDebt` |

**b-2 — `debt_refusals`** (D = the debtor's name; the first two end the list):

| condition | reason |
|---|---|
| `settled` | « cette dette est déjà réglée » |
| `forgiven` | « cette dette a été remise » |
| a fact term, the receiver does not hold it, the debtor does not know it | « D doit connaître le fait à transmettre » |
| a skill term, the receiver does not hold it, the debtor is not at Maître | « D doit être Maître en « label » pour l'enseigner » |
| a fact or skill term the receiver already holds | no refusal (b-3) |
| the money terms exceed the debtor's balance | « il faut N pièce(s), D en a M » |
| an item's terms (summed) exceed what he holds | « il faut N × item, D en a M » |

**b-3 — what repaying writes** (D debtor, C creditor, R receiver):

| currency | write |
|---|---|
| money | ledger D -n (counterparty C), C +n (counterparty D), `source_type` `debt` |
| item | holding D -n, C +n |
| fact, R does not hold it | R learns it at `knows`, source « dette » |
| skill, R does not hold it | R's row at rank 0, `taught_by` D |
| fact, R holds it | R's regard toward D: `- debt_fact_relation` (none when 0) |
| skill, R holds it | R's regard toward D: `- debt_skill_relation` (none when 0) |

**b-4 — `credit_plan`** (the quest's cost terms, in order):

| condition | result |
|---|---|
| quest settled, or its agenda missing, failed, abandoned | refused: `closed_refusal` |
| any `other` cost check (a fact unknown, a skill not Maître, the counterparty holds it) | refused: those reasons |
| a money cost | pay = min(amount, money left of max(0, balance)); the rest owed to its counterparty, else the giver |
| an item cost | pay = min(amount, that item left of what he holds); the rest owed likewise |
| nothing owed | refused: « rien à régler à crédit : la quête peut être déclarée accomplie » |
| otherwise | `paid` per cost term, `owed` per creditor, in term order |

**b-5 — who knows a debt's fact**:

| creditor | secret | at creation | at closing |
|---|---|---|---|
| character | no | debtor, creditor: rows `knows` | both rows refreshed |
| character | yes | debtor, creditor: rows `knows`, `is_secret` | both rows refreshed (secrecy kept) |
| faction | no | debtor, contact: rows `knows`; `faction` default `knows` | debtor's and contact's rows refreshed |
| faction | yes | debtor, contact: rows `knows`, `is_secret`; no default | likewise |

A refreshed row keeps its level when it is `knows` or above, else rises to
`knows`; its other fields are kept; `updated_at` is now.

**b-7 — `request_service`**, in order:

| input | result |
|---|---|
| provider not another active character of the world | `ValueError` |
| `on_behalf_of_id` a faction the provider is not an active member of | `ValueError` |
| a term refused by `clean_terms` (0109 C-03, giver = provider) | `ValueError` |
| a cost the player cannot pay now (`cost_checks`, any kind) | `ValueError` (French reasons) |
| the debt refused by `prepare_debt` (b-1) | `ValueError` |
| otherwise | the terms applied, then the debt written |

## Context

The tables exist (A). This brief writes them: a debt is validated whole, written with its fact known by the parties (F-a, F-b1, U1, X1), repaid all at once or forgiven, and closing it rewrites the fact as a change. Debts are born of the creator's hand, of a service asked in Journée (S2) and of « régler à crédit » (A2) -- for which the settlement's term application becomes reusable, its behavior unchanged. The routes serve C and D.

## Scope IN

The embedded diff is the prototype's commit for this brief, verbatim. Apply it; do not retype it.
Save the block below (between the four-backtick fences) to a file and run `git apply --check <file>`
then `git apply <file>` from the repository root. The generated `tooling/standards/DECISIONS_INDEX.md`
is not in the diff: regenerate it as listed.

1. Apply the embedded diff. It:
   - creates `src/world_engine/writes/debts.py` (C-03, C-04) and `writes/debt_sources.py` (C-05), exported by `writes`; allow-lists `write_debt` (`debt debt_term`) and `_close` (`debt`) and moves the `quest` site from `settle_quest` to `finish_settlement` in `canon_write_policy.txt`;
   - `writes/quest_settlement.py`: `cost_checks`, `closed_refusal`, `apply_term`, `in_order`, `finish_settlement`; `settle_quest` rebuilt on them (same refusals, same writes, R-08);
   - `writes/quests.py`: `write_quest_offer(contact_entity_id=None)`, `_check_contact`, the snapshot records the contact (X1);
   - creates `src/world_engine/debt_reads.py` (C-06); `quest_reads.py`: `offer_dict`'s contact, `faction_members`, `editor_choices.members`; `quest_settlement_view.py`: `credit` (C-06);
   - creates `src/world_engine/cockpit/routes/debts.py`, registered in `app.py`; `routes/quests.py`: `OfferBody.contact_entity_id`, `CreditBody`, `POST /api/quests/{quest_id}/settle-on-credit` (C-07);
   - documents the ledger origins `debt` and `service` in the schema doc (no schema change);
   - adds DB1-DB5 to `debts.py`;
   - appends the decision entry above the footer.
   The files it touches, exactly:
   - src/world_engine/cockpit/app.py
   - src/world_engine/cockpit/routes/debts.py
   - src/world_engine/cockpit/routes/quests.py
   - src/world_engine/debt_reads.py
   - src/world_engine/quest_reads.py
   - src/world_engine/quest_settlement_view.py
   - src/world_engine/writes/__init__.py
   - src/world_engine/writes/debt_sources.py
   - src/world_engine/writes/debts.py
   - src/world_engine/writes/quest_settlement.py
   - src/world_engine/writes/quests.py
   - tooling/standards/ARCHITECTURE_DECISIONS.md
   - tooling/verify/canon_write_policy.txt
   - tooling/verify/checks/debts.py
   - world-engine-schema.md
2. Regenerate the index: `python tooling/glue/gen_decisions_index.py`.
3. Commit message: `feat(debts): a debt written whole with its fact, repaid at once or forgiven; a service owes the rest, a quest settles on credit (BRIEF-0110-b)`.

````diff
diff --git a/src/world_engine/cockpit/app.py b/src/world_engine/cockpit/app.py
index d978b06..ae6456b 100644
--- a/src/world_engine/cockpit/app.py
+++ b/src/world_engine/cockpit/app.py
@@ -56,6 +56,7 @@ from . import crud as _crud
 from .origin_guard import origin_guard
 from .routes import creator as _routes_creator
 from .routes import day as _routes_day
+from .routes import debts as _routes_debts
 from .routes import link_agent as _routes_link_agent
 from .routes import lore as _routes_lore
 from .routes import lore_mentions as _routes_lore_mentions
@@ -140,6 +141,7 @@ app.include_router(_routes_lore_mentions.router)
 app.include_router(_routes_lore_choices.router)
 app.include_router(_routes_lore_write.router)
 app.include_router(_routes_quests.router)
+app.include_router(_routes_debts.router)
 
 app.mount("/static", _FreshnessAwareStaticFiles(directory=_STATIC_DIR), name="static")
 
diff --git a/src/world_engine/cockpit/routes/debts.py b/src/world_engine/cockpit/routes/debts.py
new file mode 100644
index 0000000..6bbe280
--- /dev/null
+++ b/src/world_engine/cockpit/routes/debts.py
@@ -0,0 +1,141 @@
+"""Debt routes (TICKET-0110, BRIEF-0110-B, contract C-07).
+
+The creator's ledger of debts (Création › Dettes) -- creator CRUD, a
+sanctioned canon-write path:
+    GET  /api/debts                 every debt of the active world
+    POST /api/debts                 write one by hand (origin `creator`)
+    POST /api/debts/{id}/repay      the debtor repays it, all at once (D1)
+    POST /api/debts/{id}/forgive    the creditor lets it go, with a note
+
+The player's side (Journée):
+    GET  /api/journee/debts         what he owes and what is owed to him
+    POST /api/services              ask a character a service (S2)
+
+Every rule lives in `writes/debts.py` and `writes/debt_sources.py`; what is
+shown, in `debt_reads.py`. This module parses, maps a refusal to its status
+code (422 a request that cannot be written, 409 a debt that cannot be
+repaid or forgiven now), and commits.
+"""
+
+from __future__ import annotations
+
+from typing import Optional
+
+from fastapi import APIRouter, Depends, HTTPException
+from pydantic import BaseModel, Field
+from sqlmodel import Session
+
+from ... import debt_reads
+from ...db import get_session
+from ...models import Debt
+from ...writes import DebtTermSpec, create_debt, forgive_debt, request_service, settle_debt
+from .. import crud as _crud
+from .day import _resolve_player_character
+from .quests import TermBody, _term
+
+router = APIRouter()
+
+
+class DebtTermBody(BaseModel):
+    currency: str
+    item_id: Optional[str] = None
+    fact_id: Optional[str] = None
+    skill_key: Optional[str] = None
+    amount: Optional[int] = None
+
+
+class DebtBody(BaseModel):
+    debtor_entity_id: str
+    creditor_entity_id: str
+    contact_entity_id: Optional[str] = None
+    reason: Optional[str] = None
+    is_secret: bool = False
+    terms: list[DebtTermBody] = Field(default_factory=list)
+
+
+class ForgiveBody(BaseModel):
+    note: Optional[str] = None
+
+
+class ServiceBody(BaseModel):
+    provider_entity_id: str
+    on_behalf_of_id: Optional[str] = None
+    terms: list[TermBody] = Field(default_factory=list)
+    owed: list[DebtTermBody] = Field(default_factory=list)
+    reason: Optional[str] = None
+    is_secret: bool = False
+
+
+def _owed(terms: list[DebtTermBody]) -> list[DebtTermSpec]:
+    return [DebtTermSpec(**{name: (value if value != "" else None) for name, value in t.model_dump().items()})
+            for t in terms]
+
+
+def _world_debt(debt_id: str, db: Session) -> Debt:
+    debt = db.get(Debt, debt_id)
+    if debt is None or debt.world_id != _crud._world_id(db):
+        raise HTTPException(status_code=404, detail=f"debt {debt_id!r} not found")
+    return debt
+
+
+@router.get("/api/debts")
+def list_debts(db: Session = Depends(get_session)) -> list[dict]:
+    return debt_reads.world_debts(_crud._world_id(db), db)
+
+
+@router.post("/api/debts", status_code=201)
+def write_debt_by_hand(body: DebtBody, db: Session = Depends(get_session)) -> dict:
+    try:
+        debt = create_debt(db, world_id=_crud._world_id(db), debtor_id=body.debtor_entity_id,
+                           creditor_id=body.creditor_entity_id, contact_id=body.contact_entity_id or None,
+                           origin="creator", reason=body.reason, is_secret=body.is_secret, terms=_owed(body.terms),
+                           changed_by="creator_crud")
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=422, detail=str(exc)) from exc
+    db.commit()
+    return debt_reads.debt_dict(debt, db)
+
+
+@router.post("/api/debts/{debt_id}/repay")
+def repay(debt_id: str, db: Session = Depends(get_session)) -> dict:
+    debt = _world_debt(debt_id, db)
+    try:
+        settle_debt(db, debt=debt, changed_by="creator_crud")
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=409, detail=str(exc)) from exc
+    db.commit()
+    return debt_reads.debt_dict(debt, db)
+
+
+@router.post("/api/debts/{debt_id}/forgive")
+def forgive(debt_id: str, body: ForgiveBody, db: Session = Depends(get_session)) -> dict:
+    debt = _world_debt(debt_id, db)
+    try:
+        forgive_debt(db, debt=debt, note=body.note, changed_by="creator_crud")
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=409, detail=str(exc)) from exc
+    db.commit()
+    return debt_reads.debt_dict(debt, db)
+
+
+@router.get("/api/journee/debts")
+def journee_debts(db: Session = Depends(get_session)) -> dict:
+    character = _resolve_player_character(_crud._world_id(db), db)
+    return debt_reads.player_debts(character, db)
+
+
+@router.post("/api/services", status_code=201)
+def ask_service(body: ServiceBody, db: Session = Depends(get_session)) -> dict:
+    character = _resolve_player_character(_crud._world_id(db), db)
+    try:
+        request_service(db, character=character, provider_id=body.provider_entity_id,
+                        on_behalf_of_id=body.on_behalf_of_id or None, terms=[_term(t) for t in body.terms],
+                        owed=_owed(body.owed), reason=body.reason, is_secret=body.is_secret)
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=422, detail=str(exc)) from exc
+    db.commit()
+    return debt_reads.player_debts(character, db)
diff --git a/src/world_engine/cockpit/routes/quests.py b/src/world_engine/cockpit/routes/quests.py
index 4214965..b33d98b 100644
--- a/src/world_engine/cockpit/routes/quests.py
+++ b/src/world_engine/cockpit/routes/quests.py
@@ -15,6 +15,7 @@ The player's quests (Journée):
     POST /api/quests/{quest_id}/abandon  abandon one quest (N1)
     GET  /api/quests/{quest_id}/settlement  what « déclarer accomplie » shows (G1)
     POST /api/quests/{quest_id}/settle      « déclarer accomplie » (D1, TICKET-0109)
+    POST /api/quests/{quest_id}/settle-on-credit  « régler à crédit » (A2, TICKET-0110)
 
 Every rule lives in `writes/quests.py` (what may be written) and
 `quest_reads.py` (what is shown); this module parses, maps a refusal to its
@@ -35,7 +36,10 @@ from ...db import get_session
 from ...models import Quest, QuestEconomy, QuestOffer
 from ...quest_value import DEFAULT_RATES, offer_value, value_dict, world_rates
 from ...quest_settlement_view import settlement_context
-from ...writes import TermSpec, abandon_quest, accept_quest, settle_quest, upsert_quest_economy, write_quest_offer
+from ...writes import (
+    TermSpec, abandon_quest, accept_quest, settle_quest, settle_quest_on_credit, upsert_quest_economy,
+    write_quest_offer,
+)
 from ...writes.quest_terms import ECONOMY_COLUMNS
 from .. import crud as _crud
 from .day import _resolve_player_character
@@ -70,6 +74,8 @@ class TermBody(BaseModel):
 
 class OfferBody(BaseModel):
     giver_entity_id: str
+    # TICKET-0110 (X1): a faction giver's contact; null clears it.
+    contact_entity_id: Optional[str] = None
     title: str
     summary: Optional[str] = None
     repeatable: bool = False
@@ -104,6 +110,12 @@ class AcceptBody(BaseModel):
     offer_id: str
 
 
+class CreditBody(BaseModel):
+    is_secret: bool = False
+    # A faction creditor's id -> the member the debt is linked to (X1).
+    contacts: dict[str, str] = Field(default_factory=dict)
+
+
 def _spec(req: RequirementBody) -> RequirementSpec:
     return RequirementSpec(type=req.type, target_entity_id=req.target_entity_id or None,
                            target_key=req.target_key or None, threshold=req.threshold)
@@ -118,6 +130,7 @@ def _save_offer(body: OfferBody, offer: Optional[QuestOffer], world_id: str, db:
             summary=body.summary, repeatable=body.repeatable, status=body.status,
             eligibility=[_spec(r) for r in body.eligibility], steps=steps,
             terms=None if body.terms is None else [_term(t) for t in body.terms],
+            contact_entity_id=body.contact_entity_id or None,
         )
     except ValueError as exc:
         db.rollback()
@@ -239,3 +252,17 @@ def settle(quest_id: str, db: Session = Depends(get_session)) -> dict:
         raise HTTPException(status_code=409, detail=str(exc)) from exc
     db.commit()
     return quest_reads.journee_payload(character, db)
+
+
+@router.post("/api/quests/{quest_id}/settle-on-credit")
+def settle_on_credit(quest_id: str, body: CreditBody, db: Session = Depends(get_session)) -> dict:
+    """A2 (TICKET-0110): what the player lacks of coins or items becomes a
+    debt per creditor; the quest is settled."""
+    quest, character = _players_quest(quest_id, db)
+    try:
+        settle_quest_on_credit(db, quest=quest, contacts=body.contacts, is_secret=body.is_secret)
+    except ValueError as exc:
+        db.rollback()
+        raise HTTPException(status_code=409, detail=str(exc)) from exc
+    db.commit()
+    return quest_reads.journee_payload(character, db)
diff --git a/src/world_engine/debt_reads.py b/src/world_engine/debt_reads.py
new file mode 100644
index 0000000..7b40965
--- /dev/null
+++ b/src/world_engine/debt_reads.py
@@ -0,0 +1,99 @@
+"""Debts: what the two surfaces read (TICKET-0110, BRIEF-0110-B, contract
+C-06). Reads only: this module never writes.
+
+`debt_dict` is one debt as both surfaces show it: the parties by name, its
+origin (a quest by its title, never an agenda id), its motive, its terms
+each with a French line, its indicative value in the world's unit -- a
+display, never converted (C1 of the series) -- and its state.
+`world_debts` is every debt of a world, for Création › Dettes;
+`player_debts` is what the player owes and what is owed to him, for
+Journée › Dettes, each open one with the reasons it cannot be repaid now.
+"""
+
+from __future__ import annotations
+
+from typing import Optional
+
+from sqlmodel import Session, select
+
+from .models import Agenda, Character, Debt, Entity, Fact, Quest
+from .prose_render import fact_text
+from .quest_value import term_value, world_rates
+from .skill_access import skill_label
+from .writes.debts import debt_refusals, debt_terms
+
+DEBT_STATUS_LABELS: dict[str, str] = {"open": "due", "settled": "réglée", "forgiven": "remise"}
+DEBT_ORIGIN_LABELS: dict[str, str] = {"service": "service", "quest": "quête", "creator": "création"}
+
+
+def _name(db: Session, entity_id: Optional[str]) -> Optional[str]:
+    entity = db.get(Entity, entity_id) if entity_id else None
+    return entity.name if entity is not None else None
+
+
+def debt_term_line(db: Session, term) -> str:
+    """One owed term in French: « 20 pièce(s) », « 2 × Fourrure », « le savoir
+    « … » », « l'enseignement de « Herboristerie » »."""
+    if term.currency == "money":
+        return f"{term.amount} pièce(s)"
+    if term.currency == "item":
+        return f"{term.amount} × {_name(db, term.item_id) or '?'}"
+    if term.currency == "fact":
+        fact = db.get(Fact, term.fact_id) if term.fact_id else None
+        return f"le savoir « {fact_text(db, fact) if fact is not None else '?'} »"
+    return f"l'enseignement de « {skill_label(db, term.skill_key)} »"
+
+
+def _origin_label(db: Session, debt: Debt) -> str:
+    if debt.origin != "quest":
+        return DEBT_ORIGIN_LABELS[debt.origin]
+    quest = db.get(Quest, debt.origin_quest_id)
+    agenda = db.get(Agenda, quest.agenda_id) if quest is not None else None
+    return f"quête « {agenda.title} »" if agenda is not None else "quête"
+
+
+def debt_dict(debt: Debt, db: Session) -> dict:
+    """C-06: one debt, every key always present."""
+    terms = debt_terms(db, debt.id)
+    rates = world_rates(db, debt.world_id)
+    return {
+        "id": debt.id,
+        "debtor_id": debt.debtor_entity_id, "debtor_name": _name(db, debt.debtor_entity_id),
+        "creditor_id": debt.creditor_entity_id, "creditor_name": _name(db, debt.creditor_entity_id),
+        "contact_id": debt.contact_entity_id, "contact_name": _name(db, debt.contact_entity_id),
+        "origin": debt.origin, "origin_label": _origin_label(db, debt),
+        "reason": debt.reason, "is_secret": debt.is_secret,
+        "status": debt.status, "status_label": DEBT_STATUS_LABELS[debt.status],
+        "created_at": debt.created_at.isoformat() if debt.created_at else None,
+        "closed_at": debt.closed_at.isoformat() if debt.closed_at else None,
+        "closed_note": debt.closed_note,
+        "terms": [{"currency": t.currency, "item_id": t.item_id, "fact_id": t.fact_id, "skill_key": t.skill_key,
+                   "amount": t.amount, "line": debt_term_line(db, t)} for t in terms],
+        "value": sum(term_value(db, t, rates) for t in terms),
+    }
+
+
+def _ordered(debts: list[Debt]) -> list[Debt]:
+    """Open first, then the most recent."""
+    return sorted(debts, key=lambda d: (d.status != "open", -(d.created_at.timestamp() if d.created_at else 0), d.id))
+
+
+def world_debts(world_id: str, db: Session) -> list[dict]:
+    """GET /api/debts: every debt of the world."""
+    return [debt_dict(d, db) for d in _ordered(list(db.exec(select(Debt).where(Debt.world_id == world_id)).all()))]
+
+
+def _with_refusals(debt: Debt, db: Session) -> dict:
+    view = debt_dict(debt, db)
+    view["refusals"] = debt_refusals(db, debt) if debt.status == "open" else []
+    view["repayable"] = debt.status == "open" and not view["refusals"]
+    return view
+
+
+def player_debts(character: Character, db: Session) -> dict:
+    """GET /api/journee/debts: `owes` (he is the debtor) and `owed` (he is
+    the creditor), each open one with why it cannot be repaid now."""
+    owes = db.exec(select(Debt).where(Debt.debtor_entity_id == character.id)).all()
+    owed = db.exec(select(Debt).where(Debt.creditor_entity_id == character.id)).all()
+    return {"owes": [_with_refusals(d, db) for d in _ordered(list(owes))],
+            "owed": [_with_refusals(d, db) for d in _ordered(list(owed))]}
diff --git a/src/world_engine/quest_reads.py b/src/world_engine/quest_reads.py
index ba23c02..8b4fd0b 100644
--- a/src/world_engine/quest_reads.py
+++ b/src/world_engine/quest_reads.py
@@ -26,6 +26,7 @@ from .models import (
     Character,
     Entity,
     Fact,
+    FactionMembership,
     Item,
     Quest,
     QuestOffer,
@@ -66,6 +67,8 @@ def offer_dict(offer: QuestOffer, db: Session) -> dict:
     terms = offer_terms(db, offer.id)
     return {
         "id": offer.id, "giver_entity_id": offer.giver_entity_id, "giver_name": _name(db, offer.giver_entity_id),
+        # TICKET-0110 (X1): a faction giver's contact.
+        "contact_entity_id": offer.contact_entity_id, "contact_name": _name(db, offer.contact_entity_id),
         "title": offer.title, "summary": offer.summary, "repeatable": offer.repeatable, "status": offer.status,
         "eligibility": [_requirement_dict(r) for r in offer_requirements(db, offer.id, None)],
         "steps": [{
@@ -90,11 +93,23 @@ def _named(db: Session, world_id: str, entity_type: str) -> list[dict]:
     return sorted(({"id": e.id, "name": e.name} for e in rows), key=lambda d: (d["name"].lower(), d["id"]))
 
 
+def faction_members(world_id: str, db: Session) -> dict[str, list[dict]]:
+    """TICKET-0110 (X1): each faction's active character members, by name --
+    who may be a contact."""
+    rows = db.exec(select(FactionMembership.faction_id, Entity).join(Entity, Entity.id == FactionMembership.entity_id)
+                   .where(Entity.world_id == world_id, Entity.type == "character", Entity.status == "active",
+                          FactionMembership.left_at.is_(None))).all()
+    members: dict[str, list[dict]] = {}
+    for faction_id, entity in rows:
+        members.setdefault(faction_id, []).append({"id": entity.id, "name": entity.name})
+    return {fid: sorted(people, key=lambda d: (d["name"].lower(), d["id"])) for fid, people in members.items()}
+
+
 def editor_choices(world_id: str, db: Session) -> dict:
     """What the offer editor's pickers list: givers, characters, locations,
     factions, facts (their text), skills (base domains, then definitions),
     offers; items with their value, the fact reward levels and the world's
-    rates (TICKET-0109)."""
+    rates (TICKET-0109); each faction's members (TICKET-0110, X1)."""
     facts = db.exec(select(Fact).where(Fact.world_id == world_id)).all()
     definitions = db.exec(select(SkillDefinition).where(SkillDefinition.world_id == world_id)).all()
     characters = _named(db, world_id, "character")
@@ -113,6 +128,7 @@ def editor_choices(world_id: str, db: Session) -> dict:
         "items": [{**i, "value": db.get(Item, i["id"]).value} for i in _named(db, world_id, "item")],
         "fact_levels": list(FACT_REWARD_LEVELS),
         "rates": world_rates(db, world_id),
+        "members": faction_members(world_id, db),
     }
 
 
diff --git a/src/world_engine/quest_settlement_view.py b/src/world_engine/quest_settlement_view.py
index b54630e..609da5e 100644
--- a/src/world_engine/quest_settlement_view.py
+++ b/src/world_engine/quest_settlement_view.py
@@ -8,14 +8,23 @@ text the day chain read, each step's band), how many of its step changes
 still await review, and why it cannot be settled now, if it cannot. No
 model is called (G1). No agenda or step id appears: the quest is named by
 its `quest_id`.
+
+TICKET-0110 (A2): `credit` says whether « régler à crédit » applies and,
+per creditor, what would be owed and who the debt would be linked to -- a
+faction creditor lists its members, its contact preselected when the offer
+names one.
 """
 
 from __future__ import annotations
 
 from sqlmodel import Session, select
 
-from .models import Agenda, AgendaStep, Batch, Character, DayRewrite, PassPlay, ProposedMutation, Quest, QuestOffer
-from .quest_reads import QUEST_STATE_LABELS, _steps_view
+from .debt_reads import debt_term_line
+from .models import (
+    Agenda, AgendaStep, Batch, Character, DayRewrite, Entity, PassPlay, ProposedMutation, Quest, QuestOffer,
+)
+from .quest_reads import QUEST_STATE_LABELS, _steps_view, faction_members
+from .writes.debt_sources import credit_contact, credit_plan
 from .quest_value import offer_value, value_dict
 from .quest_wording import term_line
 from .skill_access import skill_label
@@ -63,6 +72,20 @@ def _pending_reviews(db: Session, agenda: Agenda) -> int:
     return sum(1 for m in pending if isinstance(m.payload, dict) and m.payload.get("step_id") in step_ids)
 
 
+def _credit(db: Session, quest: Quest) -> dict:
+    plan = credit_plan(db, quest)
+    members = faction_members(quest.world_id, db)
+    debts = []
+    for creditor_id, owed in plan.owed.items():
+        creditor = db.get(Entity, creditor_id)
+        is_faction = creditor.type == "faction"
+        debts.append({"creditor_id": creditor_id, "creditor_name": creditor.name, "is_faction": is_faction,
+                      "lines": [debt_term_line(db, t) for t in owed],
+                      "contact_id": credit_contact(db, quest, creditor_id, {}),
+                      "members": members.get(creditor_id, []) if is_faction else []})
+    return {"possible": not plan.refusals, "refusals": plan.refusals, "debts": debts}
+
+
 def settlement_context(db: Session, quest: Quest) -> dict:
     """GET /api/quests/{quest_id}/settlement (C-06)."""
     agenda = db.get(Agenda, quest.agenda_id)
@@ -79,4 +102,5 @@ def settlement_context(db: Session, quest: Quest) -> dict:
         "days": _days(db, agenda),
         "pending_reviews": _pending_reviews(db, agenda),
         "refusals": refusals, "can_settle": not refusals,
+        "credit": _credit(db, quest),
     }
diff --git a/src/world_engine/writes/__init__.py b/src/world_engine/writes/__init__.py
index ea71f6f..7b72934 100644
--- a/src/world_engine/writes/__init__.py
+++ b/src/world_engine/writes/__init__.py
@@ -42,6 +42,12 @@ Layout, by canon domain:
                           BRIEF-0109-A).
     quest_settlement.py — « déclarer accomplie »: `settle_quest`,
                           `settlement_refusals` (TICKET-0109, BRIEF-0109-C).
+    debts.py            — `debt`/`debt_term`: `prepare_debt`, `write_debt`,
+                          `create_debt`, `debt_refusals`, `settle_debt`,
+                          `forgive_debt` (TICKET-0110, BRIEF-0110-B).
+    debt_sources.py     — a service (`request_service`) and « régler à
+                          crédit » (`credit_plan`, `settle_quest_on_credit`)
+                          (TICKET-0110, BRIEF-0110-B).
     quest_terms.py      — `quest_offer_term`/`quest_term`/`quest_economy`:
                           `clean_terms`, `write_offer_terms`,
                           `copy_terms_to_quest`, `upsert_quest_economy`
@@ -127,6 +133,8 @@ from .knowledge import (
 from .items import write_holding
 from .mentions import bind_mention, dismiss_mention, record_unresolved, resolve_mention
 from .quest_settlement import settle_quest, settlement_refusals
+from .debts import DebtTermSpec, create_debt, debt_refusals, debt_terms, forgive_debt, settle_debt
+from .debt_sources import credit_plan, request_service, settle_quest_on_credit
 from .quest_terms import (
     FACT_REWARD_LEVELS,
     PERSONAL_CURRENCIES,
diff --git a/src/world_engine/writes/debt_sources.py b/src/world_engine/writes/debt_sources.py
new file mode 100644
index 0000000..fdb8feb
--- /dev/null
+++ b/src/world_engine/writes/debt_sources.py
@@ -0,0 +1,158 @@
+"""Where a debt comes from besides the creator's hand (TICKET-0110,
+BRIEF-0110-B, S2 and A2, contract C-05).
+
+- `request_service(...)` (S2): a character helps the player now. What he
+  does is a list of quest terms -- rewards the player receives, costs he
+  pays at once (a fall of regard, typically: E stays available) -- applied
+  exactly as a quest's settlement applies them (`apply_term`), the ledger
+  lines marked `service`. What the player will owe is a debt toward that
+  character, or toward his faction when he acts for it (X1: he is then its
+  contact). Every check -- the terms, the costs he must pay now, the debt
+  -- passes before the first write.
+- `credit_plan(...)` / `settle_quest_on_credit(...)` (A2): « régler à
+  crédit ». When the only reasons a quest cannot be settled are coins or
+  items the player lacks, he pays what he has -- money in term order from
+  a balance above 0, each item from what he holds -- and the rest becomes
+  one debt per creditor (the term's counterparty, else the giver), origin
+  `quest`, its motive the quest's title. A faction creditor's contact is
+  the offer's contact when the faction is the giver, else the one Nia
+  names (`contacts`). Everything else is the settlement: every reward
+  given, the agenda completed, `settled_at` set. A refusal of another kind
+  (a fact, a skill) still refuses.
+
+None of these functions commits.
+"""
+
+from __future__ import annotations
+
+from collections import defaultdict
+from dataclasses import dataclass, field
+from typing import Optional
+
+from sqlmodel import Session
+
+from ..holdings import held_quantity
+from ..ledger import get_balance
+from ..models import Agenda, Character, Debt, Entity, Quest, QuestOffer
+from .debts import DebtTermSpec, PreparedDebt, is_active_member, prepare_debt, write_debt
+from .quest_settlement import apply_term, closed_refusal, cost_checks, finish_settlement, in_order
+from .quest_terms import TermSpec, clean_terms, quest_terms
+
+SERVICE_LEDGER_SOURCE = "service"
+CHANGED_BY_SERVICE = "service"
+CHANGED_BY_CREDIT = "quest_credit"
+
+
+def request_service(
+    db: Session, *, character: Character, provider_id: str, on_behalf_of_id: Optional[str],
+    terms: list[TermSpec], owed: list[DebtTermSpec], reason: Optional[str], is_secret: bool,
+) -> Debt:
+    """S2 (C-05): `ValueError` before any write; else the service's terms
+    applied (costs, then rewards) and the debt written. Returns the debt."""
+    world_id = character.world_id
+    provider = db.get(Entity, provider_id) if provider_id else None
+    if (provider is None or provider.world_id != world_id or provider.type != "character"
+            or provider.status != "active" or provider.id == character.id):
+        raise ValueError("request_service: the provider is another active character of this world")
+    creditor, contact = provider.id, None
+    if on_behalf_of_id:
+        if not is_active_member(db, provider.id, on_behalf_of_id):
+            raise ValueError("request_service: the provider is not an active member of that faction")
+        creditor, contact = on_behalf_of_id, provider.id
+    rows = [TermSpec(**columns) for columns in clean_terms(db, world_id, provider.id, terms)]
+    unpaid = [reason_ for _kind, reason_ in cost_checks(db, character.id, rows, provider.id)]
+    if unpaid:
+        raise ValueError("; ".join(unpaid))
+    prepared = prepare_debt(db, world_id=world_id, debtor_id=character.id, creditor_id=creditor, contact_id=contact,
+                            origin="service", reason=reason, is_secret=is_secret, terms=owed)
+    label = f"Service de {provider.name}"
+    for term in in_order(rows):
+        apply_term(db, world_id=world_id, character_id=character.id, term=term, giver_id=provider.id, reason=label,
+                   source_type=SERVICE_LEDGER_SOURCE)
+    return write_debt(db, prepared, changed_by=CHANGED_BY_SERVICE)
+
+
+@dataclass
+class CreditPlan:
+    refusals: list[str] = field(default_factory=list)
+    paid: dict[str, int] = field(default_factory=dict)             # quest_term.id -> paid now
+    owed: dict[str, list[DebtTermSpec]] = field(default_factory=dict)  # creditor id -> shortfall
+
+
+def credit_plan(db: Session, quest: Quest) -> CreditPlan:
+    """What « régler à crédit » would pay and owe (case table b-4)."""
+    plan = CreditPlan()
+    closed = closed_refusal(db, quest)
+    if closed is not None:
+        plan.refusals.append(closed)
+        return plan
+    offer = db.get(QuestOffer, quest.offer_id)
+    terms = quest_terms(db, quest.id)
+    checks = cost_checks(db, quest.character_id, terms, offer.giver_entity_id)
+    plan.refusals = [reason for kind, reason in checks if kind == "other"]
+    if plan.refusals:
+        return plan
+    money = max(0, get_balance(db, quest.character_id))
+    stock: dict[str, int] = defaultdict(int)
+    owed: dict[str, list[DebtTermSpec]] = defaultdict(list)
+    for term in terms:
+        if term.direction != "cost" or term.currency not in ("money", "item"):
+            continue
+        if term.currency == "money":
+            pay = min(term.amount, money)
+            money -= pay
+        else:
+            if term.item_id not in stock:
+                stock[term.item_id] = held_quantity(db, quest.character_id, term.item_id)
+            pay = min(term.amount, stock[term.item_id])
+            stock[term.item_id] -= pay
+        plan.paid[term.id] = pay
+        if pay < term.amount:
+            owed[term.counterparty_entity_id or offer.giver_entity_id].append(
+                DebtTermSpec(currency=term.currency, item_id=term.item_id, amount=term.amount - pay))
+    plan.owed = dict(owed)
+    if not plan.owed:
+        plan.refusals.append("rien à régler à crédit : la quête peut être déclarée accomplie")
+    return plan
+
+
+def credit_contact(db: Session, quest: Quest, creditor_id: str, contacts: dict[str, str]) -> Optional[str]:
+    """X1: who a faction creditor's debt is linked to -- the one Nia named,
+    else the offer's contact when the faction is the giver; None for a
+    character creditor."""
+    creditor = db.get(Entity, creditor_id)
+    if creditor is None or creditor.type != "faction":
+        return None
+    offer = db.get(QuestOffer, quest.offer_id)
+    if contacts.get(creditor_id):
+        return contacts[creditor_id]
+    return offer.contact_entity_id if offer.giver_entity_id == creditor_id else None
+
+
+def settle_quest_on_credit(db: Session, *, quest: Quest, contacts: dict[str, str], is_secret: bool) -> Quest:
+    """A2 (C-05): `ValueError` before any write; else the costs paid in part,
+    every reward, one debt per creditor, the quest settled."""
+    plan = credit_plan(db, quest)
+    if plan.refusals:
+        raise ValueError("; ".join(plan.refusals))
+    title = db.get(Agenda, quest.agenda_id).title
+    prepared: list[PreparedDebt] = []
+    for creditor_id, owed in plan.owed.items():
+        contact = credit_contact(db, quest, creditor_id, contacts)
+        if contact is None and db.get(Entity, creditor_id).type == "faction":
+            raise ValueError(f"il faut choisir le membre de « {db.get(Entity, creditor_id).name} » qui porte la dette")
+        prepared.append(prepare_debt(db, world_id=quest.world_id, debtor_id=quest.character_id,
+                                     creditor_id=creditor_id, contact_id=contact, origin="quest",
+                                     origin_quest_id=quest.id, reason=f"Quête « {title} »", is_secret=is_secret,
+                                     terms=owed))
+    offer = db.get(QuestOffer, quest.offer_id)
+    for term in in_order(quest_terms(db, quest.id)):
+        pay = plan.paid.get(term.id)
+        if pay == 0:
+            continue
+        apply_term(db, world_id=quest.world_id, character_id=quest.character_id, term=term,
+                   giver_id=offer.giver_entity_id, reason=f"Quête « {title} »", amount=pay)
+    finish_settlement(db, quest)
+    for debt in prepared:
+        write_debt(db, debt, changed_by=CHANGED_BY_CREDIT)
+    return quest
diff --git a/src/world_engine/writes/debts.py b/src/world_engine/writes/debts.py
new file mode 100644
index 0000000..72e34a7
--- /dev/null
+++ b/src/world_engine/writes/debts.py
@@ -0,0 +1,364 @@
+"""Debts: the writers (TICKET-0110, BRIEF-0110-B, J2, C2, T1, F-a, F-b1, U1,
+V1, X1, contract C-03).
+
+- `prepare_debt(...)` validates a debt whole -- parties, contact, origin,
+  terms -- and returns what `write_debt` writes; nothing is written before
+  every check has passed. `create_debt` is the two in a row.
+- `write_debt(...)`   : the debt's fact (a free `information` fact, aspect
+  `dette`, whose participants are the debtor, the creditor and the
+  contact), the parties' knowledge of it (the debtor, and the creditor --
+  his contact for a faction -- at `knows`, secret when the debt is), a
+  `faction` default at `knows` for a faction creditor's members when the
+  debt is not secret (U1), the `debt` row and its terms.
+- `debt_refusals(...)` / `settle_debt(...)`: repaying, all at once (D1).
+  Money and items move from the debtor to the creditor; a fact is
+  delivered, a skill taught, to the RECEIVER (the creditor, his contact for
+  a faction). A receiver who already holds that fact or skill is not
+  refused: his regard toward the debtor falls by the world's
+  `debt_fact_relation` or `debt_skill_relation` instead.
+- `forgive_debt(...)`: the creditor lets it go, with an optional note.
+
+Settling and forgiving close the row once (`status`, `closed_at`, and the
+note) -- a debt is never deleted -- and rewrite its fact with a
+`changement` (TICKET-0105): whoever learned the debt earlier keeps the old
+version until a later contact; the two parties' rows are refreshed, so they
+know at once. None of these functions commits.
+"""
+
+from __future__ import annotations
+
+from collections import defaultdict
+from dataclasses import dataclass
+from datetime import UTC, datetime
+from typing import Optional
+
+from sqlmodel import Session, select
+
+from ..fact_refs import find_held
+from ..holdings import held_quantity
+from ..ledger import get_balance
+from ..models import (
+    DEBT_CURRENCIES,
+    DEBT_ORIGINS,
+    Debt,
+    DebtTerm,
+    Entity,
+    Fact,
+    FactionMembership,
+    Item,
+    Knowledge,
+    Quest,
+    SkillDefinition,
+)
+from ..prose_render import entity_token
+from ..quest_value import world_rates
+from ..skill_access import held_rank, skill_label
+from ..skill_ranks import MAX_RANK
+from .characters import write_ledger_entry, write_skill_row
+from .facts import attach_participants, create_fact, create_fact_default, update_fact_content
+from .items import write_holding
+from .knowledge import knowledge_level_rank, write_knowledge
+from .quest_settlement import LEARNED_RANK, skill_row
+from .relations import write_relation
+
+# What a party learns of the debt, and from where (F-a).
+DEBT_FACT_LEVEL = "knows"
+DEBT_FACT_ASPECT = "dette"
+DEBT_SOURCE = "dette"
+# The ledger origin of a repayment.
+DEBT_LEDGER_SOURCE = "debt"
+# The settings of `quest_economy` a delivery no longer possible costs.
+STALE_RELATION_SETTING = {"fact": "debt_fact_relation", "skill": "debt_skill_relation"}
+
+
+@dataclass(frozen=True)
+class DebtTermSpec:
+    currency: str
+    item_id: Optional[str] = None
+    fact_id: Optional[str] = None
+    skill_key: Optional[str] = None
+    amount: Optional[int] = None
+
+
+@dataclass(frozen=True)
+class PreparedDebt:
+    world_id: str
+    debtor_id: str
+    creditor_id: str
+    contact_id: Optional[str]
+    origin: str
+    origin_quest_id: Optional[str]
+    reason: Optional[str]
+    is_secret: bool
+    terms: tuple[dict, ...]
+
+
+def _active(db: Session, world_id: str, entity_id: Optional[str], types: tuple[str, ...]) -> Optional[Entity]:
+    entity = db.get(Entity, entity_id) if entity_id else None
+    if entity is None or entity.world_id != world_id or entity.type not in types or entity.status != "active":
+        return None
+    return entity
+
+
+def is_active_member(db: Session, character_id: Optional[str], faction_id: str) -> bool:
+    """X1: `character_id` holds an active membership of `faction_id`."""
+    return character_id is not None and db.exec(select(FactionMembership.id).where(
+        FactionMembership.entity_id == character_id, FactionMembership.faction_id == faction_id,
+        FactionMembership.left_at.is_(None))).first() is not None
+
+
+def clean_debt_term(db: Session, world_id: str, index: int, spec: DebtTermSpec) -> dict:
+    """One owed term validated (C-02); its columns, or `ValueError`."""
+    where = f"owed term {index + 1}"
+    if spec.currency not in DEBT_CURRENCIES:
+        raise ValueError(f"{where}: currency must be one of {DEBT_CURRENCIES}")
+    columns = {"currency": spec.currency, "item_id": None, "fact_id": None, "skill_key": None, "amount": None}
+    if spec.currency in ("money", "item"):
+        if not isinstance(spec.amount, int) or isinstance(spec.amount, bool) or spec.amount < 1:
+            raise ValueError(f"{where}: a {spec.currency} term needs an amount of at least 1")
+        columns["amount"] = spec.amount
+    if spec.currency == "item":
+        if _active(db, world_id, spec.item_id, ("item",)) is None or db.get(Item, spec.item_id) is None:
+            raise ValueError(f"{where}: {spec.item_id!r} is not an item of this world")
+        columns["item_id"] = spec.item_id
+    elif spec.currency == "fact":
+        fact = db.get(Fact, spec.fact_id) if spec.fact_id else None
+        if fact is None or fact.world_id != world_id:
+            raise ValueError(f"{where}: {spec.fact_id!r} is not a fact of this world")
+        columns["fact_id"] = spec.fact_id
+    elif spec.currency == "skill":
+        definition = db.get(SkillDefinition, spec.skill_key) if spec.skill_key else None
+        if definition is None or definition.world_id != world_id:
+            raise ValueError(f"{where}: teaching needs a skill definition of this world")
+        columns["skill_key"] = spec.skill_key
+    return columns
+
+
+def _check_contact(db: Session, world_id: str, creditor: Entity, contact_id: Optional[str]) -> None:
+    if creditor.type == "character":
+        if contact_id is not None:
+            raise ValueError("prepare_debt: a character creditor has no contact")
+        return
+    if contact_id is None:
+        raise ValueError("prepare_debt: a debt toward a faction names its contact, an active member (X1)")
+    if _active(db, world_id, contact_id, ("character",)) is None or not is_active_member(db, contact_id, creditor.id):
+        raise ValueError(f"prepare_debt: {contact_id!r} is not an active member of the creditor faction")
+
+
+def prepare_debt(
+    db: Session, *, world_id: str, debtor_id: str, creditor_id: str, contact_id: Optional[str], origin: str,
+    origin_quest_id: Optional[str] = None, reason: Optional[str] = None, is_secret: bool = False,
+    terms: list[DebtTermSpec],
+) -> PreparedDebt:
+    """Every check of C-03's case table (b-1), before any write."""
+    if _active(db, world_id, debtor_id, ("character",)) is None:
+        raise ValueError(f"prepare_debt: debtor {debtor_id!r} is not an active character of this world")
+    creditor = _active(db, world_id, creditor_id, ("character", "faction"))
+    if creditor is None:
+        raise ValueError(f"prepare_debt: creditor {creditor_id!r} is not an active character or faction")
+    if creditor_id == debtor_id:
+        raise ValueError("prepare_debt: a character cannot owe himself")
+    _check_contact(db, world_id, creditor, contact_id or None)
+    if origin not in DEBT_ORIGINS:
+        raise ValueError(f"prepare_debt: origin must be one of {DEBT_ORIGINS}")
+    quest = db.get(Quest, origin_quest_id) if origin_quest_id else None
+    if (origin == "quest") != (quest is not None and quest.world_id == world_id):
+        raise ValueError("prepare_debt: a debt born of a quest names that quest, and only then")
+    clean = tuple(clean_debt_term(db, world_id, i, spec) for i, spec in enumerate(terms))
+    motive = (reason or "").strip() or None
+    if not clean and motive is None:
+        raise ValueError("prepare_debt: a debt that owes nothing counted needs a reason")
+    return PreparedDebt(world_id, debtor_id, creditor_id, contact_id or None, origin, origin_quest_id, motive,
+                        bool(is_secret), clean)
+
+
+def _owed_phrase(db: Session, terms: list) -> str:
+    """What the fact says is owed: « 20 pièce(s), 2 × [Fourrure] … »."""
+    phrases = []
+    for term in terms:
+        if term.currency == "money":
+            phrases.append(f"{term.amount} pièce(s)")
+        elif term.currency == "item":
+            item = db.get(Entity, term.item_id)
+            phrases.append(f"{term.amount} × {entity_token(term.item_id, item.name if item else '?')}")
+        elif term.currency == "fact":
+            fact = db.get(Fact, term.fact_id)
+            phrases.append(f"le savoir « {fact.content_raw if fact else '?'} »")
+        else:
+            phrases.append(f"l'enseignement de « {skill_label(db, term.skill_key)} »")
+    return ", ".join(phrases) if phrases else "une faveur"
+
+
+def debt_fact_text(db: Session, *, debtor_id: str, creditor_id: str, contact_id: Optional[str], terms: list,
+                   reason: Optional[str], state: str, note: Optional[str] = None) -> str:
+    """The stored text of a debt's fact (C-04), identity tokens for the
+    parties: `open`, `settled` or `forgiven`."""
+    def token(entity_id: str) -> str:
+        entity = db.get(Entity, entity_id)
+        return entity_token(entity_id, entity.name if entity else "?")
+    debtor, creditor = token(debtor_id), token(creditor_id)
+    via = f" (par l'entremise de {token(contact_id)})" if contact_id else ""
+    tail = f" : {_owed_phrase(db, terms)}" + (f" — {reason}" if reason else "")
+    if state == "open":
+        return f"{debtor} doit à {creditor}{via}{tail}."
+    if state == "settled":
+        return f"{debtor} a réglé sa dette envers {creditor}{via}{tail}."
+    return f"{creditor} a fait grâce à {debtor} de sa dette{via}{tail}." + (f" ({note})" if note else "")
+
+
+def receiver_of(debt: Debt) -> str:
+    """Who receives a fact or a skill: the creditor, his contact for a faction."""
+    return debt.contact_entity_id or debt.creditor_entity_id
+
+
+def _knows(db: Session, entity_id: str, fact_id: str, is_secret: bool, changed_by: str) -> None:
+    """The entity knows the debt's fact now: a new row at `knows`, or its row
+    refreshed (the same values, `updated_at` now -- a level never falls)."""
+    row = db.exec(select(Knowledge).where(Knowledge.entity_id == entity_id, Knowledge.fact_id == fact_id)).first()
+    if row is None:
+        write_knowledge(db, entity_id=entity_id, fact_id=fact_id, level=DEBT_FACT_LEVEL, is_secret=is_secret,
+                        source=DEBT_SOURCE, changed_by=changed_by)
+        return
+    level = row.level if knowledge_level_rank(row.level) >= knowledge_level_rank(DEBT_FACT_LEVEL) else DEBT_FACT_LEVEL
+    write_knowledge(db, knowledge_id=row.id, level=level, content=row.content_raw, source=row.source,
+                    is_incorrect=row.is_incorrect, is_secret=row.is_secret, share_threshold=row.share_threshold,
+                    session_id=row.session_id, changed_by=changed_by)
+
+
+def write_debt(db: Session, prepared: PreparedDebt, *, changed_by: str) -> Debt:
+    """C-03: the fact, the parties' knowledge, the faction default (U1), the
+    row and its terms, from a `PreparedDebt`."""
+    p = prepared
+    terms = [DebtTerm(**columns) for columns in p.terms]  # for the text only, never added
+    fact = create_fact(db, world_id=p.world_id, created_by=changed_by, facet="information", aspect=DEBT_FACT_ASPECT,
+                       content=debt_fact_text(db, debtor_id=p.debtor_id, creditor_id=p.creditor_id,
+                                              contact_id=p.contact_id, terms=terms, reason=p.reason, state="open"))
+    db.flush()
+    attach_participants(db, fact=fact, entity_ids=[p.debtor_id, p.creditor_id] + ([p.contact_id] if p.contact_id else []))
+    debt = Debt(world_id=p.world_id, debtor_entity_id=p.debtor_id, creditor_entity_id=p.creditor_id,
+                contact_entity_id=p.contact_id, origin=p.origin, origin_quest_id=p.origin_quest_id, reason=p.reason,
+                is_secret=p.is_secret, fact_id=fact.id, status="open")
+    db.add(debt)
+    db.flush()
+    for order, columns in enumerate(p.terms, start=1):
+        db.add(DebtTerm(world_id=p.world_id, debt_id=debt.id, term_order=order, **columns))
+    for party in (p.debtor_id, receiver_of(debt)):
+        _knows(db, party, fact.id, p.is_secret, changed_by)
+    if p.contact_id and not p.is_secret:
+        create_fact_default(db, world_id=p.world_id, fact_id=fact.id, scope_type="faction",
+                            scope_id=p.creditor_id, level=DEBT_FACT_LEVEL, created_by=changed_by)
+    db.flush()
+    return debt
+
+
+def create_debt(db: Session, *, changed_by: str, **fields) -> Debt:
+    """`prepare_debt(**fields)` then `write_debt` -- the creator's hand."""
+    return write_debt(db, prepare_debt(db, **fields), changed_by=changed_by)
+
+
+def debt_terms(db: Session, debt_id: str) -> list[DebtTerm]:
+    return list(db.exec(select(DebtTerm).where(DebtTerm.debt_id == debt_id).order_by(DebtTerm.term_order)).all())
+
+
+def _name(db: Session, entity_id: Optional[str]) -> str:
+    entity = db.get(Entity, entity_id) if entity_id else None
+    return entity.name if entity is not None else "?"
+
+
+def _already_held(db: Session, debt: Debt, term) -> bool:
+    """The receiver already holds what this fact or skill term delivers."""
+    receiver = receiver_of(debt)
+    if term.currency == "fact":
+        return find_held(db, receiver, {"fact_id": term.fact_id}) is not None
+    return term.currency == "skill" and skill_row(db, receiver, term.skill_key) is not None
+
+
+def debt_refusals(db: Session, debt: Debt) -> list[str]:
+    """Why the debtor cannot repay `debt` now (French, case table b-2);
+    empty when he can."""
+    if debt.status == "settled":
+        return ["cette dette est déjà réglée"]
+    if debt.status == "forgiven":
+        return ["cette dette a été remise"]
+    debtor, who = debt.debtor_entity_id, _name(db, debt.debtor_entity_id)
+    money, items, refusals = 0, defaultdict(int), []
+    for term in debt_terms(db, debt.id):
+        if term.currency == "money":
+            money += term.amount
+        elif term.currency == "item":
+            items[term.item_id] += term.amount
+        elif _already_held(db, debt, term):
+            continue
+        elif term.currency == "fact" and find_held(db, debtor, {"fact_id": term.fact_id}) is None:
+            refusals.append(f"{who} doit connaître le fait à transmettre")
+        elif term.currency == "skill" and held_rank(db, debtor, term.skill_key) != MAX_RANK:
+            refusals.append(f"{who} doit être Maître en « {skill_label(db, term.skill_key)} » pour l'enseigner")
+    balance = get_balance(db, debtor)
+    if money > balance:
+        refusals.append(f"il faut {money} pièce(s), {who} en a {balance}")
+    for item_id, needed in items.items():
+        held = held_quantity(db, debtor, item_id)
+        if needed > held:
+            refusals.append(f"il faut {needed} × {_name(db, item_id)}, {who} en a {held}")
+    return refusals
+
+
+def _deliver(db: Session, debt: Debt, term, rates: dict[str, int], reason: str, changed_by: str) -> None:
+    """One owed term, from the debtor to the creditor (b-3)."""
+    debtor, creditor, receiver = debt.debtor_entity_id, debt.creditor_entity_id, receiver_of(debt)
+    if term.currency == "money":
+        write_ledger_entry(db, world_id=debt.world_id, entity_id=debtor, amount=-term.amount, counterparty_id=creditor,
+                           reason=reason, source_type=DEBT_LEDGER_SOURCE)
+        write_ledger_entry(db, world_id=debt.world_id, entity_id=creditor, amount=term.amount, counterparty_id=debtor,
+                           reason=reason, source_type=DEBT_LEDGER_SOURCE)
+    elif term.currency == "item":
+        write_holding(db, world_id=debt.world_id, item_id=term.item_id, holder_entity_id=debtor, delta=-term.amount,
+                      changed_by=changed_by)
+        write_holding(db, world_id=debt.world_id, item_id=term.item_id, holder_entity_id=creditor, delta=term.amount,
+                      changed_by=changed_by)
+    elif _already_held(db, debt, term):
+        fall = rates[STALE_RELATION_SETTING[term.currency]]
+        if fall > 0:
+            write_relation(db, mode="delta", world_id=debt.world_id, entity_a_id=receiver, entity_b_id=debtor,
+                           type="other", value=-fall, changed_by=changed_by)
+    elif term.currency == "fact":
+        write_knowledge(db, entity_id=receiver, fact_id=term.fact_id, level=DEBT_FACT_LEVEL, source=DEBT_SOURCE,
+                        changed_by=changed_by)
+    else:
+        write_skill_row(db, character_id=receiver, rank=LEARNED_RANK, skill_definition_id=term.skill_key,
+                        taught_by_id=debtor)
+    db.flush()
+
+
+def _close(db: Session, debt: Debt, status: str, note: Optional[str], changed_by: str) -> Debt:
+    """The row closed once, the fact's `changement`, both parties refreshed."""
+    debt.status, debt.closed_at, debt.closed_note = status, datetime.now(UTC), note
+    db.add(debt)
+    fact = db.get(Fact, debt.fact_id)
+    update_fact_content(db, fact=fact, changed_by=changed_by, kind="changement", content=debt_fact_text(
+        db, debtor_id=debt.debtor_entity_id, creditor_id=debt.creditor_entity_id, contact_id=debt.contact_entity_id,
+        terms=debt_terms(db, debt.id), reason=debt.reason, state=status, note=note))
+    db.flush()
+    for party in (debt.debtor_entity_id, receiver_of(debt)):
+        _knows(db, party, fact.id, debt.is_secret, changed_by)
+    return debt
+
+
+def settle_debt(db: Session, *, debt: Debt, changed_by: str) -> Debt:
+    """D1: `ValueError` with the refusals joined, before any write; else
+    every term delivered in order, then the debt `settled`."""
+    refusals = debt_refusals(db, debt)
+    if refusals:
+        raise ValueError("; ".join(refusals))
+    rates = world_rates(db, debt.world_id)
+    reason = f"Dette envers {_name(db, debt.creditor_entity_id)}"
+    for term in debt_terms(db, debt.id):
+        _deliver(db, debt, term, rates, reason, changed_by)
+    return _close(db, debt, "settled", None, changed_by)
+
+
+def forgive_debt(db: Session, *, debt: Debt, note: Optional[str], changed_by: str) -> Debt:
+    """The creditor lets an open debt go; `ValueError` when it is closed."""
+    if debt.status != "open":
+        raise ValueError("cette dette n'est plus due")
+    return _close(db, debt, "forgiven", (note or "").strip() or None, changed_by)
diff --git a/src/world_engine/writes/quest_settlement.py b/src/world_engine/writes/quest_settlement.py
index b87a678..23e2d08 100644
--- a/src/world_engine/writes/quest_settlement.py
+++ b/src/world_engine/writes/quest_settlement.py
@@ -23,6 +23,13 @@ Per currency (the series' D table):
   rise, at least 1 (a rise resets the points to 0: the surplus is not
   carried, `write_skill_progress`); at Maître, nothing; not held -> the row
   at Inexpérimenté, taught by the counterparty when he is at Maître in it.
+
+TICKET-0110 (BRIEF-0110-B): the checks and the application of one term are
+public and take the world and the character rather than a quest --
+`cost_checks` and `apply_term` -- so a service applies its terms exactly as
+a settlement does (`writes/debt_sources.py`), and a settlement on credit
+pays a cost in part (`amount`). `finish_settlement` is what closes a quest
+either way. Nothing here changes what « déclarer accomplie » does.
 """
 
 from __future__ import annotations
@@ -77,12 +84,15 @@ def skill_reward_points(db: Session, world_id: str, row: Skill) -> Optional[int]
     return max(1, math.ceil(needed * SKILL_REWARD_SHARE))
 
 
-def _cost_refusals(db: Session, quest: Quest, giver_id: str) -> list[str]:
-    character = quest.character_id
+def cost_checks(db: Session, character_id: str, terms: list, giver_id: str) -> list[tuple[str, str]]:
+    """Every cost of `terms` the character cannot pay now, as `(kind, French
+    reason)`: `money` and `item` for a stock too small (summed per item), and
+    `other` for a fact he does not know, a skill he is not Maître in, or one
+    the counterparty already holds. Rewards are never checked (C-src1)."""
     money = 0
     items: dict[str, int] = defaultdict(int)
-    refusals: list[str] = []
-    for term in quest_terms(db, quest.id):
+    checks: list[tuple[str, str]] = []
+    for term in terms:
         if term.direction != "cost":
             continue
         other = term.counterparty_entity_id or giver_id
@@ -90,48 +100,57 @@ def _cost_refusals(db: Session, quest: Quest, giver_id: str) -> list[str]:
             money += term.amount
         elif term.currency == "item":
             items[term.item_id] += term.amount
-        elif term.currency == "fact" and find_held(db, character, {"fact_id": term.fact_id}) is None:
-            refusals.append("il faut connaître le fait à transmettre")
+        elif term.currency == "fact" and find_held(db, character_id, {"fact_id": term.fact_id}) is None:
+            checks.append(("other", "il faut connaître le fait à transmettre"))
         elif term.currency == "skill":
             label = skill_label(db, term.skill_key)
-            if held_rank(db, character, term.skill_key) != MAX_RANK:
-                refusals.append(f"il faut être Maître en « {label} » pour l'enseigner")
+            if held_rank(db, character_id, term.skill_key) != MAX_RANK:
+                checks.append(("other", f"il faut être Maître en « {label} » pour l'enseigner"))
             elif skill_row(db, other, term.skill_key) is not None:
-                refusals.append(f"{_name(db, other)} connaît déjà « {label} »")
-    balance = get_balance(db, character)
+                checks.append(("other", f"{_name(db, other)} connaît déjà « {label} »"))
+    balance = get_balance(db, character_id)
     if money > balance:
-        refusals.append(f"il faut {money} pièce(s), vous en avez {balance}")
+        checks.append(("money", f"il faut {money} pièce(s), vous en avez {balance}"))
     for item_id, needed in items.items():
-        held = held_quantity(db, character, item_id)
+        held = held_quantity(db, character_id, item_id)
         if needed > held:
-            refusals.append(f"il faut {needed} × {_name(db, item_id)}, vous en avez {held}")
-    return refusals
+            checks.append(("item", f"il faut {needed} × {_name(db, item_id)}, vous en avez {held}"))
+    return checks
 
 
-def settlement_refusals(db: Session, quest: Quest) -> list[str]:
-    """Why `quest` cannot be settled now (French); empty when it can."""
+def closed_refusal(db: Session, quest: Quest) -> Optional[str]:
+    """The reason a quest can no longer be settled at all, or None."""
     if quest.settled_at is not None:
-        return ["cette quête est déjà réglée"]
+        return "cette quête est déjà réglée"
     agenda = db.get(Agenda, quest.agenda_id)
     if agenda is None or agenda.status in ("failed", "abandoned"):
-        return ["cette quête est terminée sans succès"]
+        return "cette quête est terminée sans succès"
+    return None
+
+
+def settlement_refusals(db: Session, quest: Quest) -> list[str]:
+    """Why `quest` cannot be settled now (French); empty when it can."""
+    closed = closed_refusal(db, quest)
+    if closed is not None:
+        return [closed]
     offer = db.get(QuestOffer, quest.offer_id)
-    return _cost_refusals(db, quest, offer.giver_entity_id)
+    return [reason for _kind, reason in cost_checks(db, quest.character_id, quest_terms(db, quest.id),
+                                                    offer.giver_entity_id)]
 
 
-def _money(db: Session, quest: Quest, payer: str, payee: str, amount: int, reason: str) -> None:
-    write_ledger_entry(db, world_id=quest.world_id, entity_id=payer, amount=-amount, counterparty_id=payee,
-                       reason=reason, source_type="quest")
-    write_ledger_entry(db, world_id=quest.world_id, entity_id=payee, amount=amount, counterparty_id=payer,
-                       reason=reason, source_type="quest")
+def _money(db: Session, world_id: str, payer: str, payee: str, amount: int, reason: str, source_type: str) -> None:
+    write_ledger_entry(db, world_id=world_id, entity_id=payer, amount=-amount, counterparty_id=payee,
+                       reason=reason, source_type=source_type)
+    write_ledger_entry(db, world_id=world_id, entity_id=payee, amount=amount, counterparty_id=payer,
+                       reason=reason, source_type=source_type)
 
 
-def _items(db: Session, quest: Quest, giver: str, receiver: str, item_id: str, amount: int, cost: bool) -> None:
+def _items(db: Session, world_id: str, giver: str, receiver: str, item_id: str, amount: int, cost: bool) -> None:
     taken = amount if cost else min(amount, held_quantity(db, giver, item_id))
     if taken:
-        write_holding(db, world_id=quest.world_id, item_id=item_id, holder_entity_id=giver, delta=-taken,
+        write_holding(db, world_id=world_id, item_id=item_id, holder_entity_id=giver, delta=-taken,
                       changed_by=CHANGED_BY)
-    write_holding(db, world_id=quest.world_id, item_id=item_id, holder_entity_id=receiver, delta=amount,
+    write_holding(db, world_id=world_id, item_id=item_id, holder_entity_id=receiver, delta=amount,
                   changed_by=CHANGED_BY)
 
 
@@ -142,31 +161,37 @@ def _fact(db: Session, receiver: str, fact_id: str, level: Optional[str]) -> Non
                     source="quête", changed_by=CHANGED_BY)
 
 
-def _skill_reward(db: Session, quest: Quest, teacher: str, skill_key: str) -> None:
-    row = skill_row(db, quest.character_id, skill_key)
+def _skill_reward(db: Session, world_id: str, character_id: str, teacher: str, skill_key: str) -> None:
+    row = skill_row(db, character_id, skill_key)
     if row is None and skill_key not in BASE_SKILL_DOMAINS:
         master = teacher if held_rank(db, teacher, skill_key) == MAX_RANK else None
-        write_skill_row(db, character_id=quest.character_id, rank=LEARNED_RANK, skill_definition_id=skill_key,
+        write_skill_row(db, character_id=character_id, rank=LEARNED_RANK, skill_definition_id=skill_key,
                         taught_by_id=master)
         return
     if row is None:
-        row = write_skill_row(db, character_id=quest.character_id, rank=held_rank(db, quest.character_id, skill_key),
+        row = write_skill_row(db, character_id=character_id, rank=held_rank(db, character_id, skill_key),
                               domain=skill_key)
         db.flush()
-    points = skill_reward_points(db, quest.world_id, row)
+    points = skill_reward_points(db, world_id, row)
     if points is not None:
-        write_skill_progress(db, skill_id=row.id, world_id=quest.world_id, points=points, changed_by=CHANGED_BY)
+        write_skill_progress(db, skill_id=row.id, world_id=world_id, points=points, changed_by=CHANGED_BY)
 
 
-def _apply_term(db: Session, quest: Quest, term, giver_id: str, reason: str) -> None:
-    character, other = quest.character_id, term.counterparty_entity_id or giver_id
+def apply_term(db: Session, *, world_id: str, character_id: str, term, giver_id: str, reason: str,
+               source_type: str = "quest", amount: Optional[int] = None) -> None:
+    """Apply one term between the character and its counterparty (else the
+    giver), as the D table says. `amount` replaces a money or item term's
+    own amount (a cost paid in part, on credit); `source_type` names the
+    ledger lines' origin."""
+    character, other = character_id, term.counterparty_entity_id or giver_id
     cost = term.direction == "cost"
+    count = term.amount if amount is None else amount
     if term.currency == "money":
-        _money(db, quest, character if cost else other, other if cost else character, term.amount, reason)
+        _money(db, world_id, character if cost else other, other if cost else character, count, reason, source_type)
     elif term.currency == "item":
-        _items(db, quest, character if cost else other, other if cost else character, term.item_id, term.amount, cost)
+        _items(db, world_id, character if cost else other, other if cost else character, term.item_id, count, cost)
     elif term.currency == "relation":
-        write_relation(db, mode="delta", world_id=quest.world_id, entity_a_id=other, entity_b_id=character,
+        write_relation(db, mode="delta", world_id=world_id, entity_a_id=other, entity_b_id=character,
                        type="other", value=-term.amount if cost else term.amount, changed_by=CHANGED_BY)
     elif term.currency == "fact":
         _fact(db, other if cost else character, term.fact_id, None if cost else term.level)
@@ -174,10 +199,25 @@ def _apply_term(db: Session, quest: Quest, term, giver_id: str, reason: str) ->
         write_skill_row(db, character_id=other, rank=LEARNED_RANK, skill_definition_id=term.skill_key,
                         taught_by_id=character)
     else:
-        _skill_reward(db, quest, other, term.skill_key)
+        _skill_reward(db, world_id, character_id, other, term.skill_key)
     db.flush()
 
 
+def in_order(terms: list) -> list:
+    """Every cost, then every reward, each in term order."""
+    return [t for t in terms if t.direction == "cost"] + [t for t in terms if t.direction == "reward"]
+
+
+def finish_settlement(db: Session, quest: Quest) -> Quest:
+    """The agenda `completed` when it is not, and `settled_at`, once."""
+    agenda = db.get(Agenda, quest.agenda_id)
+    if agenda.status != "completed":
+        write_agenda_status(db, agenda=agenda, status="completed")
+    quest.settled_at = datetime.now(UTC)
+    db.add(quest)
+    return quest
+
+
 def settle_quest(db: Session, *, quest: Quest) -> Quest:
     """D1 (C-05): `ValueError` with the refusals joined, before any write;
     otherwise every cost, then every reward, the agenda `completed`, and
@@ -186,13 +226,8 @@ def settle_quest(db: Session, *, quest: Quest) -> Quest:
     if refusals:
         raise ValueError("; ".join(refusals))
     offer = db.get(QuestOffer, quest.offer_id)
-    agenda = db.get(Agenda, quest.agenda_id)
-    reason = f"Quête « {agenda.title} »"
-    terms = quest_terms(db, quest.id)
-    for term in [t for t in terms if t.direction == "cost"] + [t for t in terms if t.direction == "reward"]:
-        _apply_term(db, quest, term, offer.giver_entity_id, reason)
-    if agenda.status != "completed":
-        write_agenda_status(db, agenda=agenda, status="completed")
-    quest.settled_at = datetime.now(UTC)
-    db.add(quest)
-    return quest
+    reason = f"Quête « {db.get(Agenda, quest.agenda_id).title} »"
+    for term in in_order(quest_terms(db, quest.id)):
+        apply_term(db, world_id=quest.world_id, character_id=quest.character_id, term=term,
+                   giver_id=offer.giver_entity_id, reason=reason)
+    return finish_settlement(db, quest)
diff --git a/src/world_engine/writes/quests.py b/src/world_engine/writes/quests.py
index ddb80ad..ec7062e 100644
--- a/src/world_engine/writes/quests.py
+++ b/src/world_engine/writes/quests.py
@@ -43,6 +43,7 @@ from ..models import (
     QuestOfferRequirement,
     QuestOfferStep,
 )
+from .debts import is_active_member
 from .goals_agendas import _clean_requirement, write_agenda, write_agenda_status, write_agenda_step
 from .quest_terms import TERM_COLUMNS, TermSpec, clean_terms, copy_terms_to_quest, offer_terms, write_offer_terms
 
@@ -75,10 +76,24 @@ def _check_giver(db: Session, world_id: str, giver_entity_id: str) -> None:
         raise ValueError(f"write_quest_offer: giver {giver_entity_id!r} is not an active character or faction")
 
 
+def _check_contact(db: Session, world_id: str, giver_entity_id: str, contact_entity_id: Optional[str]) -> None:
+    """X1 (TICKET-0110): an offer's contact is an active character member of
+    its faction giver; a character giver has none."""
+    if contact_entity_id is None:
+        return
+    giver, contact = db.get(Entity, giver_entity_id), db.get(Entity, contact_entity_id)
+    if giver is None or giver.type != "faction":
+        raise ValueError("write_quest_offer: only an offer given by a faction names a contact")
+    if (contact is None or contact.world_id != world_id or contact.type != "character" or contact.status != "active"
+            or not is_active_member(db, contact.id, giver.id)):
+        raise ValueError(f"write_quest_offer: contact {contact_entity_id!r} is not an active member of the giver")
+
+
 def _snapshot(offer: QuestOffer) -> None:
     history = list(offer.change_history or [])
     history.append({
-        "giver_entity_id": offer.giver_entity_id, "title": offer.title, "summary": offer.summary,
+        "giver_entity_id": offer.giver_entity_id, "contact_entity_id": offer.contact_entity_id,
+        "title": offer.title, "summary": offer.summary,
         "repeatable": offer.repeatable, "status": offer.status,
         "updated_at": offer.updated_at.isoformat() if offer.updated_at else None,
     })
@@ -99,17 +114,20 @@ def write_quest_offer(
     eligibility: list[RequirementSpec],
     steps: list[PlanStep],
     terms: Optional[list[TermSpec]] = None,
+    contact_entity_id: Optional[str] = None,
 ) -> QuestOffer:
     """Create (`offer` None) or save one offer (C-03). Everything is
     validated before the first write; a `quest_completed` requirement on the
     offer itself is refused (it could never be met). `terms` (TICKET-0109,
     B1) replaces the offer's costs and rewards whole; None keeps them, each
-    re-validated against the giver, who may have changed."""
+    re-validated against the giver, who may have changed.
+    `contact_entity_id` (TICKET-0110, X1) is written as given."""
     if not isinstance(title, str) or not title.strip():
         raise ValueError("write_quest_offer: title is required")
     if status not in QUEST_OFFER_STATUSES:
         raise ValueError(f"write_quest_offer: status must be one of {QUEST_OFFER_STATUSES}, got {status!r}")
     _check_giver(db, world_id, giver_entity_id)
+    _check_contact(db, world_id, giver_entity_id, contact_entity_id or None)
     every = list(eligibility) + [req for step in steps for req in step.requirements]
     if offer is not None and any(r.type == "quest_completed" and r.target_key == offer.id for r in every):
         raise ValueError("write_quest_offer: an offer cannot require its own completion")
@@ -126,6 +144,7 @@ def write_quest_offer(
         db.execute(text("DELETE FROM quest_offer_requirement WHERE offer_id = :oid"), {"oid": offer.id})
         db.execute(text("DELETE FROM quest_offer_step WHERE offer_id = :oid"), {"oid": offer.id})
     offer.giver_entity_id = giver_entity_id
+    offer.contact_entity_id = contact_entity_id or None
     offer.title = title.strip()
     offer.summary = (summary or "").strip() or None
     offer.repeatable = bool(repeatable)
diff --git a/tooling/standards/ARCHITECTURE_DECISIONS.md b/tooling/standards/ARCHITECTURE_DECISIONS.md
index 02cfd9b..3602aa3 100644
--- a/tooling/standards/ARCHITECTURE_DECISIONS.md
+++ b/tooling/standards/ARCHITECTURE_DECISIONS.md
@@ -18274,6 +18274,41 @@ ticket): repaying in any currency at the rates would make the unit a
 currency.
 
 
+## A DEBT IS WRITTEN WHOLE, REPAID AT ONCE OR FORGIVEN (TICKET-0110) -- A SERVICE OWES THE REST, A QUEST SETTLES ON CREDIT (BRIEF-0110-b, no schema change)
+
+**F-a, F-b1, U1.** Every debt has its fact: a free `information` fact whose
+participants are the debtor, the creditor and his contact, worded from its
+terms and motive. The debtor and the receiver (the creditor, his contact
+for a faction) know it at `knows`, secret when the debt is; a faction's
+members know a debt that is not secret, through a `faction` default.
+Repaying or forgiving rewrites it as a `changement`: whoever heard of the
+debt before keeps the old version until a later contact; the parties know
+at once.
+
+**D1, T1.** Repaying is all at once. Money and items move from the debtor to
+the creditor; a fact is delivered and a skill taught to the receiver -- so a
+debt of a fact or a skill may wait until the player knows it or is Maître,
+the way an NPC invests in him. A receiver who already holds that fact or
+skill lowers his regard toward the debtor instead, by the world's
+`debt_fact_relation` (10) or `debt_skill_relation` (20).
+
+**S2.** A service is asked of a character from Journée: what he does now is
+a list of quest terms applied as a settlement applies them (the ledger
+marks them `service`), what the player will owe is a debt -- toward him, or
+toward his faction when he acts for it, he being its contact (X1).
+
+**A2.** « Régler à crédit »: when coins or items are the only reasons a
+quest cannot be settled, the player pays what he has and the rest becomes
+one debt per creditor, motive the quest's title; a faction creditor's debt
+is linked to the offer's contact, or to the member Nia names. Every reward
+is given and the quest settled. « Déclarer accomplie » still refuses (D1 of
+0109).
+
+**Rejected.** A partial repayment (D2): one debt, one moment. A rule of
+relation at borrowing and repayment (E): it waits for a calendar, in its own
+ticket.
+
+
 ---
 
 *Co-built with Claude, June 2026.*
diff --git a/tooling/verify/canon_write_policy.txt b/tooling/verify/canon_write_policy.txt
index 4701a41..e1a5b06 100644
--- a/tooling/verify/canon_write_policy.txt
+++ b/tooling/verify/canon_write_policy.txt
@@ -60,8 +60,11 @@ src/world_engine/writes/quests.py::accept_quest                agenda_step_requi
 src/world_engine/writes/quest_terms.py::write_offer_terms      quest_offer_term
 src/world_engine/writes/quest_terms.py::copy_terms_to_quest    quest_term
 src/world_engine/writes/quest_terms.py::upsert_quest_economy   quest_economy
-# TICKET-0109, BRIEF-0109-C: settle_quest sets quest.settled_at once, at « déclarer accomplie »; every term it applies goes through write_ledger_entry, write_holding, write_relation, write_knowledge, write_skill_row, write_skill_progress and write_agenda_status, allow-listed above.
-src/world_engine/writes/quest_settlement.py::settle_quest       quest
+# TICKET-0109, BRIEF-0109-C: settle_quest sets quest.settled_at once, at « déclarer accomplie »; every term it applies goes through write_ledger_entry, write_holding, write_relation, write_knowledge, write_skill_row, write_skill_progress and write_agenda_status, allow-listed above. TICKET-0110, BRIEF-0110-B: the write moved, unchanged, to finish_settlement, which settle_quest and settle_quest_on_credit both end with -- the same one site, relocated.
+src/world_engine/writes/quest_settlement.py::finish_settlement  quest
+# TICKET-0110, BRIEF-0110-B: write_debt writes a debt and its owed terms, once (its fact, participants, knowledge and faction default go through create_fact, attach_participants, write_knowledge and create_fact_default, allow-listed above); _close closes it once -- status, closed_at, closed_note -- never deleted. Creator CRUD, a service, or a settlement on credit.
+src/world_engine/writes/debts.py::write_debt                    debt debt_term
+src/world_engine/writes/debts.py::_close                        debt
 # TICKET-0044, BRIEF-0044-c: create_entity_type is the 26th site — the governed
 # structural-write authority (D2), a NEW sanctioned site distinct from the two
 # canon-write paths (AI-proposal pipeline, creator CRUD). Its `CREATE TABLE
diff --git a/tooling/verify/checks/debts.py b/tooling/verify/checks/debts.py
index 8cd603a..c1f71e1 100644
--- a/tooling/verify/checks/debts.py
+++ b/tooling/verify/checks/debts.py
@@ -38,6 +38,55 @@ DA3 -- the evaluators (fixture). With an OPEN debt of the character toward
    `_clean_requirement` accepts a character and a faction as target and
    refuses a location.
 
+DB1 -- writing a debt (BRIEF-0110-B, fixture). `create_debt` refuses, each
+   with no row written: a location debtor, a debtor owing himself, a faction
+   creditor with no contact, a contact who is not its active member, a
+   character creditor with a contact, an origin `quest` with no quest, a
+   money term of 0, a skill term on a base domain, and nothing owed without
+   a reason. A valid debt toward a character: one row `open`, its terms in
+   order, its fact free (`information`, aspect `dette`) with the debtor and
+   the creditor as participants and the reason in its text, both parties
+   knowing it at `knows`, secret as the debt is. Toward a faction, not
+   secret: the contact is a participant and knows it, the faction has a
+   `faction` default at `knows`; secret: no default.
+DB2 -- repaying and forgiving (fixture). `settle_debt` refuses, with no row
+   written: coins or items the debtor lacks, a fact he does not know and the
+   receiver does not, a skill he is not Maître in. Once he can: the coins
+   (ledger `debt`) and the items move to the creditor, the fact is learned
+   and the skill taught by the receiver; a fact or a skill the receiver
+   already holds lowers the receiver's regard toward the debtor by the
+   world's setting instead (here 7 and 11). The debt is `settled` with
+   `closed_at`, its fact rewritten as a `changement` (« a réglé »), both
+   parties' rows refreshed, `has_debt_to` no longer met; a second repayment
+   is refused. `forgive_debt` closes an open debt `forgiven` with its note
+   (« a fait grâce »), and refuses a closed one.
+DB3 -- a service (fixture, S2). `request_service` refuses, with no row
+   written: the player as his own provider, a provider acting for a faction
+   he is not a member of, a cost the player cannot pay now, nothing owed
+   without a reason. Valid: the reward reaches the player (ledger
+   `service`), the cost lowers the provider's regard, and one debt
+   `service` is owed to the provider -- or to his faction, the provider its
+   contact.
+DB4 -- « régler à crédit » (fixture, A2). A quest whose giver is a faction
+   with a contact costs 30 coins and 3 furs; the player has 10 coins and 1
+   fur: `settle_quest` refuses, `credit_plan` pays 10 and 1 and owes the
+   faction 20 coins and 2 furs; `settle_quest_on_credit` pays them, gives
+   the reward, settles the quest and writes that one debt, origin `quest`,
+   linked to the offer's contact. A quest with a fact cost the player does
+   not know, or with nothing lacking, is refused credit with no row
+   written. A faction creditor that is not the giver needs a contact named,
+   and a member.
+DB5 -- what the surfaces read (fixture and route functions). `debt_dict`
+   carries exactly C-06's keys and its value in the world's unit; nothing
+   the routes return carries `agenda_id` or `step_id`. `player_debts` splits
+   what the player owes from what he is owed, an open one with its
+   refusals. The routes answer 201/422 on a debt by hand, 409 on a refused
+   repayment and forgiveness, 201/422 on a service. An offer's contact is
+   refused on a character giver and for a non-member, kept and shown by
+   `offer_dict`; `editor_choices` lists each faction's members; the
+   settlement context's `credit` names the creditor, the lines owed and the
+   preselected contact.
+
 Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
 world_engine import) -- never Nia's DB. A rule that collects nothing fails.
 """
@@ -446,6 +495,437 @@ def check_da3(engine) -> None:
                     fail(f"DA3: _clean_requirement {'refuses' if ok else 'accepts'} {form} toward {target}")
 
 
+# --- DB --------------------------------------------------------------------------
+
+def _db_world(session, active: bool = False) -> dict:
+    from world_engine.models import Character, Entity, Fact, Faction, Item, SkillDefinition, World
+    from world_engine.writes import write_membership
+
+    world = World(name="Debts DB", is_active=active)
+    session.add(world)
+    session.flush()
+    ids = {"world": world.id}
+    for key, kind, name in (("pc", "character", "Millys"), ("npc", "character", "Garde"),
+                            ("agent", "character", "Ivo"), ("outsider", "character", "Pell"),
+                            ("guild", "faction", "Guilde"), ("other_guild", "faction", "Ordre"),
+                            ("place", "location", "Col"), ("fur", "item", "Fourrure")):
+        row = Entity(world_id=world.id, type=kind, name=name)
+        session.add(row)
+        session.flush()
+        ids[key] = row.id
+    session.add_all([Character(id=ids[k], world_id=world.id, character_type="player" if k == "pc" else "npc")
+                     for k in ("pc", "npc", "agent", "outsider")]
+                    + [Faction(id=ids["guild"]), Faction(id=ids["other_guild"]), Item(id=ids["fur"], value=3)])
+    for key, name in (("herb", "Herboristerie"), ("forge", "Forge")):
+        definition = SkillDefinition(world_id=world.id, name=name, base_domain="perception")
+        session.add(definition)
+        session.flush()
+        ids[key] = definition.id
+    for key, text in (("secret", "Le passage secret"), ("map", "La carte du col"), ("rumor", "Une rumeur")):
+        fact = Fact(world_id=world.id, content_raw=text, created_by="check", facet="information")
+        session.add(fact)
+        session.flush()
+        ids[key] = fact.id
+    for member, faction in (("agent", "guild"), ("npc", "other_guild")):
+        session.add(write_membership(session, mode="open", world_id=world.id, entity_id=ids[member],
+                                     faction_id=ids[faction]))
+    session.commit()
+    return ids
+
+
+def _counts(session) -> tuple:
+    from sqlmodel import func, select
+
+    from world_engine.models import Debt, DebtTerm, Fact, FactDefault, ItemHolding, Knowledge, Ledger, Relation, Skill
+
+    return tuple(session.exec(select(func.count()).select_from(m)).one()
+                 for m in (Debt, DebtTerm, Fact, FactDefault, Knowledge, Ledger, ItemHolding, Relation, Skill))
+
+
+def _refused(session, label: str, call) -> None:
+    before = _counts(session)
+    try:
+        call()
+    except ValueError:
+        session.rollback()
+        if _counts(session) != before:
+            fail(f"{label}: a refusal wrote rows")
+        return
+    session.rollback()
+    fail(f"{label}: accepted")
+
+
+def _new_debt(session, ids, creditor="npc", contact=None, secret=False, terms=None, reason="pour la corde"):
+    from world_engine.writes import DebtTermSpec, create_debt
+
+    terms = terms if terms is not None else [DebtTermSpec(currency="money", amount=5)]
+    debt = create_debt(session, world_id=ids["world"], debtor_id=ids["pc"], creditor_id=ids[creditor],
+                       contact_id=ids[contact] if contact else None, origin="creator", reason=reason,
+                       is_secret=secret, terms=terms, changed_by="check")
+    session.commit()
+    return debt
+
+
+def _knowledge(session, entity_id, fact_id):
+    from sqlmodel import select
+
+    from world_engine.models import Knowledge
+
+    return session.exec(select(Knowledge).where(Knowledge.entity_id == entity_id, Knowledge.fact_id == fact_id)).first()
+
+
+def check_db1(session, ids) -> None:
+    from sqlmodel import select
+
+    from world_engine.models import DebtTerm, Fact, FactDefault, FactParticipant
+    from world_engine.writes import DebtTermSpec, create_debt
+
+    def make(**over):
+        fields = dict(world_id=ids["world"], debtor_id=ids["pc"], creditor_id=ids["npc"], contact_id=None,
+                      origin="creator", reason="r", is_secret=False, terms=[DebtTermSpec(currency="money", amount=5)])
+        fields.update(over)
+        return lambda: create_debt(session, changed_by="check", **fields)
+
+    bad = {
+        "a location debtor": make(debtor_id=ids["place"]),
+        "a debtor owing himself": make(creditor_id=ids["pc"]),
+        "a faction with no contact": make(creditor_id=ids["guild"]),
+        "a contact not a member": make(creditor_id=ids["guild"], contact_id=ids["outsider"]),
+        "a character creditor with a contact": make(contact_id=ids["agent"]),
+        "origin quest with no quest": make(origin="quest"),
+        "a money term of 0": make(terms=[DebtTermSpec(currency="money", amount=0)]),
+        "a skill term on a base domain": make(terms=[DebtTermSpec(currency="skill", skill_key="perception")]),
+        "nothing owed without a reason": make(terms=[], reason="  "),
+    }
+    for label, call in bad.items():
+        _refused(session, f"DB1 ({label})", call)
+    debt = _new_debt(session, ids, secret=True, terms=[DebtTermSpec(currency="money", amount=5),
+                                                       DebtTermSpec(currency="item", item_id=ids["fur"], amount=2)])
+    terms = session.exec(select(DebtTerm).where(DebtTerm.debt_id == debt.id).order_by(DebtTerm.term_order)).all()
+    fact = session.get(Fact, debt.fact_id)
+    parts = set(session.exec(select(FactParticipant.entity_id).where(FactParticipant.fact_id == fact.id)).all())
+    if debt.status != "open" or [(t.term_order, t.currency) for t in terms] != [(1, "money"), (2, "item")]:
+        fail(f"DB1: the debt is {debt.status} with terms {[(t.term_order, t.currency) for t in terms]}")
+    if fact.facet != "information" or fact.aspect != "dette" or "pour la corde" not in fact.content_raw:
+        fail(f"DB1: the fact is {fact.facet}/{fact.aspect} « {fact.content_raw} »")
+    if parts != {ids["pc"], ids["npc"]}:
+        fail(f"DB1: the participants are {parts}")
+    for party in ("pc", "npc"):
+        row = _knowledge(session, ids[party], fact.id)
+        if row is None or row.level != "knows" or not row.is_secret:
+            fail(f"DB1: {party} does not know the secret debt at knows")
+    open_debt = _new_debt(session, ids, creditor="guild", contact="agent")
+    secret_debt = _new_debt(session, ids, creditor="guild", contact="agent", secret=True)
+    for d, expected in ((open_debt, 1), (secret_debt, 0)):
+        defaults = session.exec(select(FactDefault).where(FactDefault.fact_id == d.fact_id)).all()
+        if len(defaults) != expected or any(x.scope_type != "faction" or x.scope_id != ids["guild"] for x in defaults):
+            fail(f"DB1: a faction debt (secret {d.is_secret}) has defaults {[(x.scope_type, x.scope_id) for x in defaults]}")
+    if _knowledge(session, ids["agent"], open_debt.fact_id) is None:
+        fail("DB1: the contact does not know the faction debt")
+
+
+def _db2_stock(session, ids) -> None:
+    from world_engine.models import Knowledge, Skill
+    from world_engine.writes import upsert_quest_economy, write_holding, write_ledger_entry
+
+    w = ids["world"]
+    write_ledger_entry(session, world_id=w, entity_id=ids["pc"], amount=50, source_type="creator")
+    write_holding(session, world_id=w, item_id=ids["fur"], holder_entity_id=ids["pc"], quantity=5, changed_by="check")
+    session.add_all([Knowledge(entity_id=ids["pc"], fact_id=ids["secret"], level="knows"),
+                     Knowledge(entity_id=ids["pc"], fact_id=ids["map"], level="knows"),
+                     Knowledge(entity_id=ids["npc"], fact_id=ids["map"], level="knows"),
+                     Skill(character_id=ids["pc"], domain="perception", skill_definition_id=ids["herb"], rank=5,
+                           change_history=[]),
+                     Skill(character_id=ids["pc"], domain="perception", skill_definition_id=ids["forge"], rank=5,
+                           change_history=[]),
+                     Skill(character_id=ids["npc"], domain="perception", skill_definition_id=ids["forge"], rank=0,
+                           change_history=[])])
+    upsert_quest_economy(session, world_id=w, values={"debt_fact_relation": 7, "debt_skill_relation": 11})
+    session.commit()
+
+
+def _regard(session, ids, who="npc") -> int:
+    from sqlmodel import select
+
+    from world_engine.models import Relation
+
+    row = session.exec(select(Relation).where(Relation.entity_a_id == ids[who], Relation.entity_b_id == ids["pc"])).first()
+    return row.intensity if row else 50
+
+
+def check_db2(session, ids) -> None:
+    from world_engine.day_plan import RequirementSpec, evaluate_specs
+    from world_engine.ledger import get_balance
+    from world_engine.holdings import held_quantity
+    from sqlmodel import select
+
+    from world_engine.models import Character, Debt, Fact
+    from world_engine.writes import DebtTermSpec, forgive_debt, settle_debt
+    from world_engine.writes.quest_settlement import skill_row
+
+    lacking = (("coins", [DebtTermSpec(currency="money", amount=500)]),
+               ("furs", [DebtTermSpec(currency="item", item_id=ids["fur"], amount=9)]),
+               ("a fact", [DebtTermSpec(currency="fact", fact_id=ids["secret"])]),
+               ("a skill", [DebtTermSpec(currency="skill", skill_key=ids["herb"])]))
+    for label, terms in lacking:
+        debt = _new_debt(session, ids, creditor="outsider", terms=terms)
+        _refused(session, f"DB2 ({label} lacking)", lambda d=debt: settle_debt(session, debt=d, changed_by="check"))
+    _db2_stock(session, ids)
+    terms = [DebtTermSpec(currency="money", amount=20), DebtTermSpec(currency="item", item_id=ids["fur"], amount=2),
+             DebtTermSpec(currency="fact", fact_id=ids["secret"]), DebtTermSpec(currency="fact", fact_id=ids["map"]),
+             DebtTermSpec(currency="skill", skill_key=ids["herb"]), DebtTermSpec(currency="skill", skill_key=ids["forge"])]
+    debt = _new_debt(session, ids, terms=terms)
+    pc = session.get(Character, ids["pc"])
+    regard = _regard(session, ids)
+    balance, furs = get_balance(session, ids["pc"]), held_quantity(session, ids["pc"], ids["fur"])
+    settle_debt(session, debt=debt, changed_by="check")
+    session.commit()
+    if get_balance(session, ids["pc"]) != balance - 20 or held_quantity(session, ids["pc"], ids["fur"]) != furs - 2:
+        fail("DB2: the coins or the furs did not leave the debtor")
+    if get_balance(session, ids["npc"]) < 20 or held_quantity(session, ids["npc"], ids["fur"]) != 2:
+        fail("DB2: the creditor did not receive the coins or the furs")
+    if _knowledge(session, ids["npc"], ids["secret"]) is None or skill_row(session, ids["npc"], ids["herb"]) is None:
+        fail("DB2: the fact was not learned or the skill not taught")
+    if _regard(session, ids) != regard - 7 - 11:
+        fail(f"DB2: the regard went {regard} -> {_regard(session, ids)}, expected -7 -11")
+    fact = session.get(Fact, debt.fact_id)
+    if debt.status != "settled" or debt.closed_at is None or "a réglé" not in fact.content_raw:
+        fail(f"DB2: the debt is {debt.status}, fact « {fact.content_raw} »")
+    if not fact.change_history or fact.change_history[-1].get("kind") != "changement":
+        fail("DB2: the fact was not rewritten as a changement")
+    row = _knowledge(session, ids["pc"], fact.id)
+    if row is None or len(row.change_history or []) < 1:
+        fail("DB2: the debtor's knowledge of the debt was not refreshed")
+    for left in session.exec(select(Debt).where(Debt.creditor_entity_id == ids["npc"], Debt.status == "open")).all():
+        forgive_debt(session, debt=left, note=None, changed_by="check")
+    session.commit()
+    if evaluate_specs((RequirementSpec(type="has_debt_to", target_entity_id=ids["npc"]),), pc, session)[0].met:
+        fail("DB2: a settled debt is still owed")
+    _refused(session, "DB2 (a second repayment)", lambda: settle_debt(session, debt=debt, changed_by="check"))
+    other = _new_debt(session, ids)
+    forgive_debt(session, debt=other, note="en souvenir", changed_by="check")
+    session.commit()
+    text = session.get(Fact, other.fact_id).content_raw
+    if other.status != "forgiven" or other.closed_note != "en souvenir" or "a fait grâce" not in text:
+        fail(f"DB2: the forgiven debt is {other.status} « {text} »")
+    _refused(session, "DB2 (forgiving a closed debt)", lambda: forgive_debt(session, debt=other, note=None,
+                                                                             changed_by="check"))
+
+
+def check_db3(session, ids) -> None:
+    from sqlmodel import select
+
+    from world_engine.models import Character, Ledger
+    from world_engine.writes import DebtTermSpec, TermSpec, request_service
+
+    pc = session.get(Character, ids["pc"])
+    owed = [DebtTermSpec(currency="money", amount=15)]
+    reward = [TermSpec(direction="reward", currency="money", amount=15),
+              TermSpec(direction="cost", currency="relation", amount=4)]
+
+    def ask(**over):
+        fields = dict(character=pc, provider_id=ids["npc"], on_behalf_of_id=None, terms=reward, owed=owed,
+                      reason="un prêt", is_secret=False)
+        fields.update(over)
+        return lambda: request_service(session, **fields)
+
+    _refused(session, "DB3 (himself as provider)", ask(provider_id=ids["pc"]))
+    _refused(session, "DB3 (for a faction he is not in)", ask(on_behalf_of_id=ids["guild"]))
+    _refused(session, "DB3 (an unpayable cost)", ask(terms=[TermSpec(direction="cost", currency="money", amount=9999)]))
+    _refused(session, "DB3 (nothing owed, no reason)", ask(owed=[], reason=None))
+    regard = _regard(session, ids)
+    debt = ask()()
+    session.commit()
+    lines = session.exec(select(Ledger).where(Ledger.entity_id == ids["pc"], Ledger.source_type == "service")).all()
+    if [line.amount for line in lines] != [15]:
+        fail(f"DB3: the service's ledger lines are {[line.amount for line in lines]}")
+    if _regard(session, ids) != regard - 4:
+        fail("DB3: the service's cost did not lower the provider's regard")
+    if (debt.origin, debt.creditor_entity_id, debt.contact_entity_id) != ("service", ids["npc"], None):
+        fail(f"DB3: the service's debt is {(debt.origin, debt.creditor_entity_id, debt.contact_entity_id)}")
+    debt = ask(provider_id=ids["agent"], on_behalf_of_id=ids["guild"], terms=[])()
+    session.commit()
+    if (debt.creditor_entity_id, debt.contact_entity_id) != (ids["guild"], ids["agent"]):
+        fail("DB3: a service for a faction is not owed to it, its provider the contact")
+
+
+def _db4_quest(session, ids, giver, terms, title, contact=None):
+    from world_engine.day_plan import PlanStep
+    from world_engine.models import Character
+    from world_engine.writes import accept_quest, write_quest_offer
+
+    offer = write_quest_offer(session, world_id=ids["world"], offer=None, giver_entity_id=ids[giver], title=title,
+                              summary=None, repeatable=True, status="open", eligibility=[],
+                              steps=[PlanStep(objective="Chasser", cost=1, domain=None)], terms=terms,
+                              contact_entity_id=ids[contact] if contact else None)
+    session.flush()
+    quest = accept_quest(session, offer=offer, character=session.get(Character, ids["pc"]))
+    session.commit()
+    return quest
+
+
+def check_db4(session, ids) -> None:
+    from sqlmodel import select
+
+    from world_engine.holdings import held_quantity
+    from world_engine.ledger import get_balance
+    from world_engine.models import Debt, DebtTerm
+    from world_engine.writes import (
+        TermSpec, credit_plan, settle_quest, settle_quest_on_credit, write_holding, write_ledger_entry,
+    )
+
+    w = ids["world"]
+    write_ledger_entry(session, world_id=w, entity_id=ids["pc"], amount=10 - get_balance(session, ids["pc"]),
+                       source_type="creator")
+    write_holding(session, world_id=w, item_id=ids["fur"], holder_entity_id=ids["pc"], quantity=1, changed_by="check")
+    session.commit()
+    terms = [TermSpec(direction="cost", currency="money", amount=30),
+             TermSpec(direction="cost", currency="item", item_id=ids["fur"], amount=3),
+             TermSpec(direction="reward", currency="relation", amount=5, counterparty_entity_id=ids["agent"])]
+    quest = _db4_quest(session, ids, "guild", terms, "La meute", contact="agent")
+    _refused(session, "DB4 (settle_quest with coins lacking)", lambda: settle_quest(session, quest=quest))
+    plan = credit_plan(session, quest)
+    owed = {k: [(t.currency, t.amount) for t in v] for k, v in plan.owed.items()}
+    if plan.refusals or sorted(plan.paid.values()) != [1, 10] or owed != {ids["guild"]: [("money", 20), ("item", 2)]}:
+        fail(f"DB4: the plan is {plan.refusals} {plan.paid} {owed}")
+    settle_quest_on_credit(session, quest=quest, contacts={}, is_secret=False)
+    session.commit()
+    debt = session.exec(select(Debt).where(Debt.origin_quest_id == quest.id)).first()
+    if quest.settled_at is None or get_balance(session, ids["pc"]) != 0 or held_quantity(session, ids["pc"], ids["fur"]):
+        fail("DB4: the quest was not settled with what the player had")
+    if debt is None or (debt.creditor_entity_id, debt.contact_entity_id, debt.origin) != (ids["guild"], ids["agent"], "quest"):
+        fail("DB4: no debt toward the giver faction, linked to the offer's contact")
+    else:
+        rows = session.exec(select(DebtTerm).where(DebtTerm.debt_id == debt.id).order_by(DebtTerm.term_order)).all()
+        if [(t.currency, t.amount) for t in rows] != [("money", 20), ("item", 2)]:
+            fail(f"DB4: the debt owes {[(t.currency, t.amount) for t in rows]}")
+    fact_quest = _db4_quest(session, ids, "npc", [TermSpec(direction="cost", currency="fact", fact_id=ids["rumor"],
+                                                           counterparty_entity_id=ids["outsider"]),
+                                                  TermSpec(direction="cost", currency="money", amount=99)], "Le col")
+    paid_quest = _db4_quest(session, ids, "npc", [TermSpec(direction="reward", currency="money", amount=1)], "Rien")
+    for label, q in (("a fact cost", fact_quest), ("nothing lacking", paid_quest)):
+        _refused(session, f"DB4 (credit with {label})",
+                 lambda q=q: settle_quest_on_credit(session, quest=q, contacts={}, is_secret=False))
+    other = _db4_quest(session, ids, "npc", [TermSpec(direction="cost", currency="money", amount=5,
+                                                      counterparty_entity_id=ids["other_guild"])], "L'ordre")
+    _refused(session, "DB4 (a faction creditor with no contact)",
+             lambda: settle_quest_on_credit(session, quest=other, contacts={}, is_secret=False))
+    _refused(session, "DB4 (a contact who is not a member)",
+             lambda: settle_quest_on_credit(session, quest=other, contacts={ids["other_guild"]: ids["agent"]},
+                                            is_secret=False))
+    settle_quest_on_credit(session, quest=other, contacts={ids["other_guild"]: ids["npc"]}, is_secret=True)
+    session.commit()
+
+
+DEBT_DICT_KEYS = {
+    "id", "debtor_id", "debtor_name", "creditor_id", "creditor_name", "contact_id", "contact_name", "origin",
+    "origin_label", "reason", "is_secret", "status", "status_label", "created_at", "closed_at", "closed_note",
+    "terms", "value",
+}
+
+
+def _keys_deep(value) -> set:
+    if isinstance(value, dict):
+        return set(value) | {k for v in value.values() for k in _keys_deep(v)}
+    if isinstance(value, list):
+        return {k for v in value for k in _keys_deep(v)}
+    return set()
+
+
+def _http(label: str, status: int, call) -> None:
+    from fastapi import HTTPException
+
+    try:
+        call()
+    except HTTPException as exc:
+        if exc.status_code != status:
+            fail(f"{label}: answered {exc.status_code}, expected {status}")
+        return
+    fail(f"{label}: answered 2xx, expected {status}")
+
+
+def _db5_routes(session, ids) -> None:
+    from world_engine.cockpit.routes import debts as routes
+    from world_engine.cockpit.routes import quests as quest_routes
+
+    created = routes.write_debt_by_hand(routes.DebtBody(
+        debtor_entity_id=ids["pc"], creditor_entity_id=ids["npc"], reason="un service",
+        terms=[routes.DebtTermBody(currency="money", amount=500)]), db=session)
+    if set(created) != DEBT_DICT_KEYS or created["value"] != 500 or created["status_label"] != "due":
+        fail(f"DB5: debt_dict is {sorted(created)} value {created.get('value')}")
+    _http("DB5 (a debt by hand toward a place)", 422, lambda: routes.write_debt_by_hand(routes.DebtBody(
+        debtor_entity_id=ids["pc"], creditor_entity_id=ids["place"], reason="r"), db=session))
+    _http("DB5 (an unpayable repayment)", 409, lambda: routes.repay(created["id"], db=session))
+    routes.forgive(created["id"], routes.ForgiveBody(note="n"), db=session)
+    _http("DB5 (forgiving twice)", 409, lambda: routes.forgive(created["id"], routes.ForgiveBody(), db=session))
+    payload = routes.journee_debts(db=session)
+    owes_ids = {d["id"] for d in payload["owes"]}
+    if created["id"] not in owes_ids or "owed" not in payload or any(d["debtor_id"] != ids["pc"]
+                                                                    for d in payload["owes"]):
+        fail("DB5: player_debts does not list what the player owes")
+    if not all("refusals" in d and "repayable" in d for d in payload["owes"] + payload["owed"]):
+        fail("DB5: player_debts lacks the refusals")
+    served = routes.ask_service(routes.ServiceBody(provider_entity_id=ids["npc"], reason="un abri"), db=session)
+    _http("DB5 (a service from a place)", 422, lambda: routes.ask_service(
+        routes.ServiceBody(provider_entity_id=ids["place"], reason="r"), db=session))
+    every = [created, routes.list_debts(db=session), payload, served]
+    if _keys_deep(every) & {"agenda_id", "step_id"}:
+        fail("DB5: a debt payload names an agenda or a step")
+    _http("DB5 (an offer contact on a character giver)", 422, lambda: quest_routes.create_offer(
+        quest_routes.OfferBody(giver_entity_id=ids["npc"], contact_entity_id=ids["agent"], title="t",
+                               steps=[quest_routes.OfferStepBody(objective="o", cost=1)]), db=session))
+    _http("DB5 (an offer contact not a member)", 422, lambda: quest_routes.create_offer(
+        quest_routes.OfferBody(giver_entity_id=ids["guild"], contact_entity_id=ids["outsider"], title="t",
+                               steps=[quest_routes.OfferStepBody(objective="o", cost=1)]), db=session))
+    offer = quest_routes.create_offer(quest_routes.OfferBody(
+        giver_entity_id=ids["guild"], contact_entity_id=ids["agent"], title="t",
+        steps=[quest_routes.OfferStepBody(objective="o", cost=1)]), db=session)
+    if (offer["contact_entity_id"], offer["contact_name"]) != (ids["agent"], "Ivo"):
+        fail(f"DB5: offer_dict shows the contact {offer.get('contact_entity_id')}")
+    members = quest_routes.offer_choices(db=session)["members"]
+    if [m["id"] for m in members.get(ids["guild"], [])] != [ids["agent"]]:
+        fail(f"DB5: editor_choices lists the guild's members as {members.get(ids['guild'])}")
+
+
+def _db5_credit_context(session, ids) -> None:
+    from world_engine.ledger import get_balance
+    from world_engine.quest_settlement_view import settlement_context
+    from world_engine.writes import TermSpec, write_ledger_entry
+
+    balance = get_balance(session, ids["pc"])
+    if balance > 0:
+        write_ledger_entry(session, world_id=ids["world"], entity_id=ids["pc"], amount=-balance, source_type="creator")
+    quest = _db4_quest(session, ids, "guild", [TermSpec(direction="cost", currency="money", amount=8)], "Dîme",
+                       contact="agent")
+    credit = settlement_context(session, quest)["credit"]
+    debts = credit["debts"]
+    if not credit["possible"] or len(debts) != 1 or debts[0]["creditor_id"] != ids["guild"] \
+            or debts[0]["lines"] != ["8 pièce(s)"] or debts[0]["contact_id"] != ids["agent"] \
+            or [m["id"] for m in debts[0]["members"]] != [ids["agent"]]:
+        fail(f"DB5: the settlement's credit is {credit}")
+
+
+def check_db(engine) -> None:
+    from sqlmodel import Session
+
+    with Session(engine) as session:
+        ids = _db_world(session)
+        check_db1(session, ids)
+        check_db2(session, ids)
+        check_db3(session, ids)
+        check_db4(session, ids)
+    with Session(engine) as session:
+        from world_engine.models import World
+
+        for world in session.exec(__import__("sqlmodel").select(World)).all():
+            world.is_active = False
+            session.add(world)
+        session.commit()
+        ids = _db_world(session, active=True)
+        _db5_routes(session, ids)
+        _db5_credit_context(session, ids)
+
+
 def main() -> int:
     db_path = _fresh_db()
     check_da1a()
@@ -455,6 +935,7 @@ def main() -> int:
     create_db_and_tables()
     check_da1c(engine)
     check_da3(engine)
+    check_db(engine)
     if FAILURES:
         for msg in FAILURES:
             print(f"FAIL: {msg}")
@@ -462,7 +943,11 @@ def main() -> int:
     print("PASS: debts -- v2.19 lays the debt tables, an offer's contact and the economy's two debt "
           "settings, migrates from v2.18 only, widens the requirement vocabulary with has_debt_to and "
           "no_debt_to for the creator alone, judges an open debt toward a character or a faction, and "
-          "retires the relation type debt")
+          "retires the relation type debt; a debt is validated whole, written with its fact known by "
+          "both parties (secret as it is, a faction's members when it is not), repaid at once or "
+          "forgiven and never deleted, its fact changed; a service applies its terms and owes the rest; "
+          "« régler à crédit » pays what the player has and owes the rest per creditor; the surfaces "
+          "read every debt without an agenda or step id")
     return 0
 
 
diff --git a/world-engine-schema.md b/world-engine-schema.md
index e516eaa..5fef23a 100644
--- a/world-engine-schema.md
+++ b/world-engine-schema.md
@@ -862,7 +862,7 @@ CREATE TABLE ledger (
   amount          INTEGER NOT NULL,        -- signed: + credit, − debit; world base unit
   counterparty_id TEXT REFERENCES entity(id),           -- the other party (filled, not double-written)
   reason          TEXT,                    -- "pécule de départ", "correction prix"
-  source_type     TEXT,                    -- creator | correction | conversation | pass_play | tick | quest (v2.18 settlement)
+  source_type     TEXT,                    -- creator | correction | conversation | pass_play | tick | quest (v2.18 settlement) | debt, service (v2.19)
                                             -- ('conversation' written by
                                             -- _apply_mutation's resource_change
                                             -- branch, BRIEF-19/v1.32; 'pass_play'
````

## Scope OUT

- Any frontend file (C, D).
- Changing what « déclarer accomplie » refuses or writes: `quest_rewards.py` RC1-RC3 must stay green untouched.
- A relation change at borrowing or repayment beyond what the service's own terms say (E).
- Raising a knowledge level a party already holds above `knows`; lowering one.
- Editing or deleting a debt; a DELETE or PUT route on debts.
- The relation's change at borrowing and repayment (E -- its own ticket, with a calendar).
- The erosion of an unpaid debt (H1): no world time exists.
- Settling a debt « otherwise » (C3), a partial repayment (D2), a debt proposed by the model.
- Porting « Mes savoirs » into Journée; rank trials (TICKET-0111); any change to `legacy.html` or Play.
- Any change to the day-chain prompts, and to any prompt but `pt-npc-link-pair`'s type list.
- Every later brief of this lot.

## Invariants to defend

**Two canon-write paths:** every debt write is creator-direct (Création, or Nia's clicks in Journée), through `write_debt` and `_close`, allow-listed by function; they call the existing writers (`create_fact`, `attach_participants`, `create_fact_default`, `update_fact_content`, `write_knowledge`, `write_ledger_entry`, `write_holding`, `write_relation`, `write_skill_row`). **All or nothing:** every refusal is found before the first write; each route commits once. **History is sacred:** a debt is closed, never deleted; its fact keeps its previous text (`changement`); each knowledge refresh appends its history; the ledger is INSERT only. **Knowledge levels never decrease:** a refreshed row keeps a level above `knows`. **A participant is the aboutness claim:** participants are attached once, at creation. **The player never sees the agenda:** no debt payload names an `agenda_id` or `step_id`.

## Decision rights

STOP:
- A Mini-RECON anchor does not hold.
- `git apply --check` of the embedded diff fails on a file this brief names, other than the ADAPT case below.
- The full corpus is not green after the commit, for a reason the diff does not explain.
- `quest_rewards.py` turns red: the settlement's refactor changed behavior.
- A debt writer would write before every refusal is checked.

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
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/debts.py` -> `PASS: debts -- v2.19 lays the debt tables, an offer's contact and the economy's two debt settings, migrates from v2.18 only, widens the requirement vocabulary with has_debt_to and no_debt_to for the creator alone, judges an open debt toward a character or a faction, and retires the relation type debt; a debt is validated whole, written with its fact known by both parties (secret as it is, a faction's members when it is not), repaid at once or forgiven and never deleted, its fact changed; a service applies its terms and owes the rest; « régler à crédit » pays what the player has and owes the rest per creditor; the surfaces read every debt without an agenda or step id`
- `quest_rewards.py`, `quests.py`, `single_canon_write.py`, `fact_spine.py`, `module_budget.py`, `function_length.py`, `undefined_names.py`, `decisions_index.py` -> `PASS`.
- `src/world_engine/cockpit/routes/quests.py` is 268 lines; `writes/debts.py` 364; `writes/quest_settlement.py` 233.
- Mutation tests, each red then reverted (`debts.py` exits 1 with the rule named): in `src/world_engine/writes/debts.py`, `    if p.contact_id and not p.is_secret:` -> `    if p.contact_id:` -> `DB1`; in `src/world_engine/writes/debts.py`, `        fall = rates[STALE_RELATION_SETTING[term.currency]]` -> `        fall = 10` -> `DB2`; in `src/world_engine/writes/debts.py`, `kind="changement",` -> `kind="correction",` -> `DB2`; in `src/world_engine/writes/debt_sources.py`, `    if unpaid:` -> `    if False:` -> `DB3`; in `src/world_engine/writes/debt_sources.py`, `    plan.refusals = [reason for kind, reason in checks if kind == "other"]` -> `    plan.refusals = []` -> `DB4`; in `src/world_engine/debt_reads.py`, `"value": sum(term_value(db, t, rates) for t in terms),` -> `"value": sum(term_value(db, t, rates) for t in terms), "agenda_id": None,` -> `DB5`.
- `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` -> 143/143.
- `/review-step` then `/close-step` ran on the commit.

## Docs to update

Decision entry `A DEBT IS WRITTEN WHOLE, REPAID AT ONCE OR FORGIVEN (TICKET-0110) -- A SERVICE OWES THE REST, A QUEST SETTLES ON CREDIT (BRIEF-0110-b, no schema change)`; the ledger `source_type` line of the schema doc -- both in the diff. No schema change, no CLAUDE.md change.
