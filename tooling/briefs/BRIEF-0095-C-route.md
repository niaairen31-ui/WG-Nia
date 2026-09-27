# BRIEF 0095-C — "the review route"

Lot: LOT-0095-choice-review.md (authoritative on conflict)
Depends on: BRIEF-0095-B (the reader and `_k1_world`)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a few
lines is drift, not a STOP — note it and proceed; different content is always
a STOP.

- B has landed: `src/world_engine/lore_choices_read.py` exposes C-05's names;
  `tooling/verify/checks/choice_review.py` holds R0, L0-L6 and
  `_k1_world(engine)`, and passes.
- `src/world_engine/cockpit/routes/lore_mentions.py:30` `_CHANGED_BY = "creator_crud"`;
  `:45-49` `_world_id` raising 400 `"No active world. Activate a world before proceeding."`;
  `:92-102` `record_appellation_route` (rollback + 422 on `ValueError`, one commit).
- `src/world_engine/writes/facets.py:242` `def record_appellation(`.
- `src/world_engine/lore_resolve.py:241` `def validate_binding(entity_id, category, world_id, db)`.
- `src/world_engine/cockpit/app.py:58` `from .routes import lore_mentions as _routes_lore_mentions`;
  `:132` `app.include_router(_routes_lore_mentions.router)`.
- `tooling/verify/checks/name_resolution.py:438-445` the G11 TestClient setup.
- No route under `/api/lore/choices` exists.

## Facts carried

Verbatim from the lot header.

#### R-06 — `record_appellation`
Opened: `src/world_engine/writes/facets.py:60-70`, `92-145`, `239-259`
Finding [M]: `record_appellation(db, *, entity_id, surface, scope_type,
created_by) -> Optional[Fact]`; `_APPELLATION_SCOPES = ("rencontre", "world",
"none")` (line 239). `ValueError` on a scope outside it, a blank surface or an
unknown entity. Returns `None` and writes nothing when `normalize_surface(
surface)` equals the entity's name or one of its appellations (CREATOR
regime). Otherwise `add_entity_fact(facet="appellation", content=surface.strip(),
scope=...)`: `rencontre` → a `fact_default(rencontre, entity_id, knows)`,
`world` → `fact_default(world, NULL, knows)`, `none` → no default (creator-only
by scope). Never commits. Measured on a prototype (entities "Maelis Varn",
"Maelis Orn"): appellation "Maelis" on Varn at `world` is stored plain
(`content_raw == "Maelis"`), one default `('world', 'knows')`, zero
`unresolved_mention` rows; a second call with "maelis" returns `None`;
"Maelis" on Orn at `none` writes a fact with no default.
Consequence: « agree » and « disagree » write through this function only
(decision B1, creator CRUD, `created_by="creator_crud"`). The review row's
scope vocabulary equals `_APPELLATION_SCOPES` (asserted by V7, C-03).

#### R-08 — how a written appellation changes the next concordance
Opened: `src/world_engine/day_concordance.py:81-83`, `365-425`;
`src/world_engine/lore_resolve.py:48`, `93-122`
Finding [M]: `concord` walks `MATCHING_RUNGS = ("named_exact", "named_token",
"named_alias", "occupation", "presence")` and stops at the first rung with a
hit. `named_exact`: normalized surface form equals a normalized name surface.
`named_token`: every token of the name surface is in the surface form (the
mention contains the whole name). `named_partial` (surface form ⊆ name) is NOT
a matching rung; H2 uses it only to build `near` requests. Measured on a
prototype (PC Aldric; "Maelis Varn", "Maelis Orn"): "Maelis" hits neither
`named_exact` nor `named_token` (it becomes a `near` request with both as
partial candidates); after an appellation "Maelys" on Orn at `world`, "Maelys"
hits `named_exact` on Orn alone; after an appellation "Maelis" on Varn at
`rencontre`, a PC who never met Varn still hits nothing.
Consequence: agreeing with an appellation the character can know makes the
same name resolve at `named_exact` next time, with no model call; at
`rencontre`, only for characters who met the entity. The live gate is built on
this.

#### R-09 — H2 requests are named only; the judge's excerpt key
Opened: `src/world_engine/day_choice.py:39`, `93-114`, `151-178`, `181-192`
Finding [M]: `choice_requests` builds requests only from `result.ambiguous`
(named by construction, `day_concordance.py:357-358`) and from unmatched
mentions with `kind == "named"`. `judge_choice` computes
`normalized = normalize_surface(answer["extrait"].strip(_EXCERPT_EDGE))`
(line 164) with `_EXCERPT_EDGE = " \t\n\"'«»“”.,;:!?…"` (line 39) and tests
substring inclusion in `normalize_surface(" ".join(facts))` or in
`normalize_surface(declaration)`. `record_of` stores `excerpt =
answer["extrait"].strip() or None`.
Consequence: every reviewable surface form is a name, so « agree » only ever
proposes an `appellation`; the `reputation`/`statut` branch of K1 is
unreachable until `cast` rows are reviewed (Y2c, deferred). K1 must find the
cited fact with the judge's own key: C-04 extracts `excerpt_key` from the
judge, with no behaviour change (day_choice J1-J8 unchanged).

#### R-11 — plan-route ordering and timestamps ("sans plan")
Opened: `src/world_engine/cockpit/routes/day.py:506-520`, `537-541`,
`590-594`, `615-622`, `655-669`; `src/world_engine/models/canon.py:48-59`
Finding [M]: a day is planned once: `_load_plannable_day` refuses a
`pass_play` whose `status != 'submitted'`, and a successful plan sets
`status = 'resolving'` in its single commit. On the plan path,
`_write_declaration_rewrite` constructs the `DayRewrite` (generation 1)
BEFORE `write_day_mention_choices` constructs the records, both in the plan's
one transaction. On the 409 path, `_record_refused_choices` rolls back and
commits the records alone; no rewrite exists. A plan failure after the rewrite
(502) commits nothing. `_created_ts()` is a Python `default_factory`
(`datetime.now(UTC)`) evaluated at construction. Measured on a prototype: a
409-path row stamped before the rewrite, and a plan-path row stamped after it;
`any(rw.created_at <= choice.created_at)` gives `False` then `True`.
Consequence: a choice is "planned" iff some `day_rewrite` of its `pass_play`
has `created_at <= choice.created_at` (C-05). Otherwise the panel shows
"sans plan".

#### R-12 — the names panel's route and reads
Opened: `src/world_engine/cockpit/routes/lore_mentions.py:1-110`;
`src/world_engine/lore_mentions_read.py:27-67`;
`src/world_engine/lore_resolve.py:38-43`, `60-65`, `241-261`
Finding [M]: the route module holds `router = APIRouter()`,
`_CHANGED_BY = "creator_crud"`, a `_world_id(db)` helper raising 400 `"No
active world. Activate a world before proceeding."`, one commit per request,
`ValueError` → `db.rollback()` + 422. `lore_mentions_read.active_world_id(db)`
returns the active world's id or `None`; `excerpt(text, surface)` returns up
to `EXCERPT_LENGTH` (80) characters around the surface (the whole text when
shorter). `validate_binding(entity_id, category, world_id, db)` is True iff
the entity is active, in the world, and of the category's types;
`CATEGORIES = ("place", "person", "faction", "object", "other")`;
`category_of_type(entity_type)`.
Consequence: the new route copies that module's shape (named, not gestured
at: C-07). The reader reuses `active_world_id` and `excerpt`.

#### R-13 — the panel/pipeline isolation rule
Opened: `tooling/verify/checks/lore_isolation.py:57-63`, `86-87`, `684-720`
Finding [M]: R17 fails when a file of `PANEL_FILES`
(`cockpit/routes/lore_mentions.py`, `lore_mentions_read.py`) imports a module
whose stem is in `PIPELINE_FILES` (`lore_selectors`, `lore_query`,
`lore_plan`, `lore_render`, `lore_prompt`), or the reverse; import names are
compared by last dotted component. A file in `PANEL_FILES` that does not exist
is a failure (`_parse`).
Consequence: B adds `lore_choices_read.py` to `PANEL_FILES`; C adds
`cockpit/routes/lore_choices.py`. Each brief adds the file it creates.

#### R-14 — creator-regime confinement
Opened: `tooling/verify/checks/name_index.py:17-30`, `51-58`
Finding [M]: R5 allows `CREATOR` (or `NameScope("creator")`) only in
`name_index.py`, `lore_query.py`, `lore_mentions_read.py`,
`writes/facets.py`.
Consequence: `lore_choices_read.py` and `routes/lore_choices.py` never name
`CREATOR`; the creator regime is used only inside `record_appellation`
(allowed file).

#### R-20 — router mounting
Opened: `src/world_engine/cockpit/app.py:54-67`, `118-132`
Finding [M]: each route module is imported as `from .routes import <name> as
_routes_<name>` (alphabetical, `lore_mentions` at 58) and mounted with
`app.include_router(_routes_<name>.router)` (`lore_mentions` last, at 132).
`/api/lore/*` today: `ask`, `resolve` (`routes/lore.py`); `mentions`,
`mentions/{id}/resolve`, `names/lookup`, `appellations`,
`mentions/{id}/dismiss` (`routes/lore_mentions.py`). No `/api/lore/choices`.
Consequence: C mounts `lore_choices` right after `lore_mentions` in both
places.

#### R-21 — route testing precedent
Opened: `tooling/verify/checks/name_resolution.py:38-46`, `430-460`
Finding [M]: G11 imports `fastapi.testclient.TestClient` and
`world_engine.cockpit.app.app` after `_fresh_engine()` has pointed
`WORLD_ENGINE_DATABASE_URL` at a temp file, builds its world with
`is_active=True`, and posts JSON bodies; no `with TestClient(...)` block (the
startup boot guard does not run).
Consequence: C's T rules follow G11's setup exactly.

## Contracts

Verbatim from the lot header.

Two families are written here first and re-read after their last member:

- **review verdict** — the values `agreed` / `disagreed` and the appellation
  scopes `rencontre` / `world` / `none`: the table CHECKs (C-01), the writer
  (C-03), the route (C-07), the panel (C-08).
- **pending row** — the dict one reviewable choice becomes (C-06): built only
  by `list_pending_choices` (C-05), returned unchanged by the GET route
  (C-07), rendered by the panel (C-08).

#### C-03 — `write_day_mention_review`
Produced by: A   Consumed by: C-07
In `src/world_engine/writes/pipeline.py`, with module constants
`_REVIEW_VERDICTS: tuple[str, ...] = ("agreed", "disagreed")` and
`_REVIEW_SCOPES: tuple[str, ...] = ("rencontre", "world", "none")` (must equal
`writes.facets._APPELLATION_SCOPES`; V7 asserts it).
Signature: `def write_day_mention_review(db: Session, *, world_id: str,
choice_id: str, verdict: str, entity_id: Optional[str],
appellation_fact_id: Optional[str], appellation_scope: Optional[str]) ->
DayMentionReview`.
Behaviour: validate, in this order, each failure raising `ValueError` whose
message starts `write_day_mention_review: ` and adding nothing:
1. `verdict` not in `_REVIEW_VERDICTS`;
2. `verdict == "agreed"` and `entity_id is None`;
3. `appellation_fact_id is not None` and `entity_id is None`;
4. `(appellation_fact_id is None) != (appellation_scope is None)`;
5. `appellation_scope is not None` and not in `_REVIEW_SCOPES`.
Then construct one `DayMentionReview`, `db.add` it, return it. No flush, no
commit.

#### C-05 — `lore_choices_read` (the reader)
Produced by: B   Consumed by: C-07
New module `src/world_engine/lore_choices_read.py`. Read-only: no `db.add`,
no commit, no `chat(`, no `CREATOR`, no import of a pipeline module (R-13,
R-14), no identifier `candidate_ids` / `evidence_fact_ids`.
- `REVIEWABLE_VERDICTS: tuple[str, ...] = ("accepted", "rejected")`.
- `is_reviewable(choice: DayMentionChoice) -> bool` — pure:
  `choice.verdict == "accepted" or (choice.verdict == "rejected" and
  choice.chosen_entity_id is not None)` (E2).
- `reviewable_choice(db, choice_id: str, world_id: str) ->
  Optional[DayMentionChoice]` — `db.get(DayMentionChoice, choice_id)`;
  `None` if absent, of another world, or not `is_reviewable`. Reviewed or
  not.
- `is_reviewed(db, choice_id: str) -> bool` — any `DayMentionReview` row with
  that `choice_id`.
- `cited_evidence(db, choice: DayMentionChoice, declaration: str) ->
  tuple[str, list[dict]]` — `key = excerpt_key(choice.excerpt or "")`;
  `len(key) < 3` → `("none", [])`. Else: the choice's evidence fact ids
  (`DayMentionChoiceEvidence` rows, ordinal order); the rows of
  `facts_of(db, entity_id=choice.chosen_entity_id, facets=tuple(FACETS))`
  whose `fact_id` is among them, in `facts_of` order; the hits are those
  rows with `key in normalize_surface(row.content)`. Hits → `("facts",
  [{"fact_id", "content", "scopes"}...])`. No hit and `key in
  normalize_surface(declaration)` → `("declaration", [])`. Otherwise
  `("none", [])`.
  `scopes` of one fact: first `{"scope_type": "world", "scope_name": None}`
  if `fact.default_level != "unaware"`; then, for each `FactDefault` of the
  fact with `level != "unaware"`, ordered by `(scope_type, id)`,
  `{"scope_type": d.scope_type, "scope_name": <entity name of d.scope_id, or
  None>}`, an entry equal to one already listed skipped.
- `preselected_scope(source: str, evidence: list[dict]) -> str` — pure:
  `"world"` iff `source == "facts"` and some entry of some evidence item's
  `scopes` has `scope_type == "world"`; else `"rencontre"` (C2).
- `list_pending_choices(db, world_id: str) -> list[dict]` — every
  `DayMentionChoice` of `world_id` with `verdict in REVIEWABLE_VERDICTS`,
  kept if `is_reviewable` and not reviewed (J1), ordered by `(created_at,
  id)`; each becomes one pending row (C-06). "planned" = some `DayRewrite`
  of the row's `pass_play_id` has `created_at <= choice.created_at` (R-11).
  Empty list when none.

#### C-06 — the pending row (family)
Produced by: C-05   Consumed by: C-07 (GET, unchanged), C-08
Every key required:
```python
{
  "id": str,                      # the day_mention_choice id
  "surface_form": str, "category": str, "trigger": str,
  "verdict": str,                 # "accepted" | "rejected"
  "verdict_detail": Optional[str], "excerpt": Optional[str], "reason": Optional[str],
  "day": {
    "day_number": int,            # batch.day_number
    "character_name": str,        # entity.name of pass_play.character_id
    "declaration": str,           # lore_mentions_read.excerpt(declared_action, surface_form)
    "planned": bool,              # R-11
  },
  "chosen": {"id": str, "name": str, "type": str},
  "candidates": [{"id": str, "name": str, "type": str}, ...],   # ordinal order
  "excerpt_source": str,          # "facts" | "declaration" | "none"
  "evidence": [{"fact_id": str, "content": str,
                "scopes": [{"scope_type": str, "scope_name": Optional[str]}]}],
  "preselected_scope": str,       # "world" | "rencontre"
}
```

#### C-07 — routes `/api/lore/choices`
Produced by: C   Consumed by: C-08, live play
New module `src/world_engine/cockpit/routes/lore_choices.py`, shaped like
`routes/lore_mentions.py` (R-12): `router = APIRouter()`, `_CHANGED_BY =
"creator_crud"`, a `_world_id(db)` helper raising 400 with the same detail,
one commit per request. No `select(`, no `chat(`.
- `GET /api/lore/choices` → `{"choices": list_pending_choices(db, world_id)}`.
- `POST /api/lore/choices/{choice_id}/review`, body
  `ChoiceReviewBody(verdict: str, entity_id: Optional[str] = None,
  record_appellation: bool = False, scope_type: str = "rencontre")`.
  Steps, first failure wins:
  1. no active world → 400;
  2. `reviewable_choice(...)` is `None` → 404
     `f"reviewable choice {choice_id!r} not found"`;
  3. `is_reviewed(...)` → 409 `f"choice {choice_id!r} is already reviewed"` (J1);
  4. `verdict` not in `("agreed", "disagreed")` → 422
     `"verdict must be 'agreed' or 'disagreed'"`;
  5. `agreed`: `entity_id` not `None` and `!= choice.chosen_entity_id` → 422
     `"agreed: entity_id must be omitted or equal the model's choice"`;
     the effective entity is `choice.chosen_entity_id`;
  6. `disagreed`: `entity_id is None` and `record_appellation` → 422
     `"disagreed without an entity cannot record an appellation"`;
     `entity_id == choice.chosen_entity_id` → 422
     `"disagreed: entity_id equals the model's choice"`; the effective
     entity is `entity_id` (may be `None`: H2);
  7. effective entity not `None` and not `validate_binding(effective,
     choice.category, world_id, db)` → 422
     `"entity_id is not an active entity of this category in the world"`;
  8. inside `try`: if `record_appellation`, `fact = record_appellation(db,
     entity_id=effective, surface=choice.surface_form, scope_type=
     body.scope_type, created_by=_CHANGED_BY)` (else `fact = None`); then
     `write_day_mention_review(db, world_id=world_id, choice_id=choice.id,
     verdict=body.verdict, entity_id=effective, appellation_fact_id=fact.id
     if fact else None, appellation_scope=body.scope_type if fact else None)`;
     `except ValueError` → `db.rollback()`, 422 `str(exc)`;
  9. `db.commit()`; return `{"ok": True, "id": choice_id,
     "appellation_written": fact is not None}`.
  Nothing is written on any failure path. The past day, its rewrite and its
  resolutions are never touched.
Mounted in `cockpit/app.py` right after `lore_mentions`.

## Case tables

Verbatim from the lot header's gate output.

**(b3) Review route (C-07):**

| input | status | writes |
|---|---|---|
| no active world | 400 | nothing |
| unknown / other world / not reviewable | 404 | nothing |
| already reviewed | 409 | nothing |
| verdict not agreed/disagreed | 422 | nothing |
| agreed, entity_id ≠ chosen | 422 | nothing |
| agreed, no record | 200, `appellation_written: false` | review(agreed, chosen) |
| agreed, record, new surface | 200, `true` | appellation + review(fact, scope) |
| agreed, record, surface already known | 200, `false` | review(agreed, chosen), no fact |
| any record with bad scope | 422 | nothing (rollback) |
| disagreed, entity NULL, no record | 200, `false` | review(disagreed, NULL) |
| disagreed, entity NULL, record | 422 | nothing |
| disagreed, entity = chosen | 422 | nothing |
| disagreed, entity of another category / inactive | 422 | nothing |
| disagreed, entity, record | 200, `true`/`false` | [appellation +] review(disagreed, entity) |

## Context

The reader (B) lists what waits for Nia. This brief adds the two endpoints:
the list, and one review per choice, written through the creator path (B1)
in one commit. The past day is never touched: a review only records Nia's
verdict and, if she asks, an appellation.

## Scope IN

1. **The route module.** Create `src/world_engine/cockpit/routes/lore_choices.py`
   exactly per C-07. Module docstring: "Model-choice review routes
   (TICKET-0095, K1, C-07). Nia agrees or disagrees with one H2 choice; every
   write goes through the creator path (B1): `writes/facets.record_appellation`
   for an optional appellation, `writes.write_day_mention_review` for the
   verdict, one commit per request. One review per choice (J1); the past day,
   its rewrite and its resolutions are never touched. Reads live in
   `lore_choices_read.py`. Isolated from the consultation pipeline
   (`lore_isolation.py` R17). Guarded exactly as the names panel (no route
   authentication)." Imports: `Optional`; `APIRouter`, `Depends`,
   `HTTPException`; `BaseModel`; `Session`; `from ... import
   lore_choices_read as _read`; `from ...db import get_session`;
   `from ...lore_mentions_read import active_world_id`;
   `from ...lore_resolve import validate_binding`;
   `from ...writes import write_day_mention_review`;
   `from ...writes.facets import record_appellation`. The 400 helper copies
   `lore_mentions.py`'s `_world_id` body, calling `active_world_id`. The
   handler may delegate steps 4-7 of C-07 to one private function returning
   the effective entity or raising `HTTPException(422, ...)`; each function
   ≤ 80 lines.

2. **Mount.** In `src/world_engine/cockpit/app.py`, add
   `from .routes import lore_choices as _routes_lore_choices` right after
   line 58 and `app.include_router(_routes_lore_choices.router)` right after
   line 132.

3. **Isolation.** In `tooling/verify/checks/lore_isolation.py`,
   `PANEL_FILES` gains `SRC / "cockpit" / "routes" / "lore_choices.py"`; R17's
   docstring adds it beside `lore_choices_read.py`.

4. **`choice_review.py` gains T0-T10** (update the docstring and `PASS:`
   line). T0 is static; T1-T10 use `fastapi.testclient.TestClient(app)` on
   the database `_k1_world` built (the G11 setup, R-21: import
   `world_engine.cockpit.app.app` after the fresh engine exists; no `with`
   block), run after L0-L6, in this order. Record `choices_before =
   count(day_mention_choice)` and `rewrites_before = count(day_rewrite)`
   first. Every expectation below was measured on a prototype of C-07 over
   the same fixture.
   - T0 (AST): `routes/lore_choices.py` holds no `select(` and no `chat(`
     call, no `CREATOR`, no `candidate_ids` / `evidence_fact_ids` identifier.
   - T1: `GET /api/lore/choices` → 200; ids `[c2, c3, c1, c6]`.
   - T2: `POST /api/lore/choices/{c1}/review` `{"verdict": "agreed",
     "record_appellation": true, "scope_type": "world"}` → 200,
     `appellation_written` true. DB: exactly one review for c1 —
     `verdict "agreed"`, `entity_id == varn`, `appellation_scope "world"`;
     its `appellation_fact_id` is a fact with `facet "appellation"`,
     `prose_render.fact_text(...) == "Maelis"`, one participant `varn`, and
     `fact_default` rows `[("world", None, "knows")]` as
     `(scope_type, scope_id, level)`.
   - T3: the same POST with `{"verdict": "agreed"}` → 409; still one review
     for c1.
   - T4: POST on c4 (declined) → 404; POST on `"no-such-choice"` → 404.
   - T5: on c2, each → 422: `{"verdict": "maybe"}`; `{"verdict": "agreed",
     "entity_id": varn}`; `{"verdict": "disagreed", "entity_id": orn}`;
     `{"verdict": "disagreed", "record_appellation": true}`;
     `{"verdict": "disagreed", "entity_id": tavern}`. Then c2 has zero
     reviews.
   - T6: on c3, `{"verdict": "disagreed", "entity_id": varn,
     "record_appellation": true, "scope_type": "nope"}` → 422; c3 has zero
     reviews; varn still has exactly one `appellation` fact.
   - T7: on c2, `{"verdict": "disagreed"}` → 200, `appellation_written`
     false; its review: `disagreed`, `entity_id` NULL,
     `appellation_fact_id` NULL, `appellation_scope` NULL.
   - T8: on c3, `{"verdict": "disagreed", "entity_id": varn,
     "record_appellation": true, "scope_type": "rencontre"}` → 200,
     `appellation_written` false ("Maelis" is already varn's since T2); its
     review: `disagreed`, `entity_id == varn`, `appellation_fact_id` NULL.
   - T9: on c6, `{"verdict": "agreed"}` → 200, `appellation_written` false;
     its review: `agreed`, `entity_id == orn`, `appellation_fact_id` NULL.
   - T10: `GET /api/lore/choices` → `{"choices": []}`; `day_mention_review`
     holds 5 rows (c5's from the fixture, plus c1, c2, c3, c6);
     `count(day_mention_choice) == choices_before` and
     `count(day_rewrite) == rewrites_before`.
   Vacuity: T1 must list four choices.

5. Append to `ARCHITECTURE_DECISIONS.md` an entry headed
   `## THE REVIEW ROUTE (TICKET-0095) -- ONE REVIEW PER CHOICE, WRITTEN THROUGH THE CREATOR PATH (BRIEF-0095-c, no schema change)`:
   B1 (why creator CRUD, the click is the approval); the step order of C-07
   and table b3; H2 (« aucune entité connue » writes a review and nothing
   else); J1 as a route rule over a non-unique column (A1); the past day is
   never re-planned; `record_appellation`'s "already known" answer is a
   success without a fact. Regenerate `DECISIONS_INDEX.md`.

## Scope OUT

- The panel: D.
- A re-review endpoint or any UPDATE/DELETE of a review (J2, W2).
- Proposals through `_apply_mutation` (B2, rejected).
- Writing `reputation`/`statut` (unreachable, R-09).
- Route authentication (named deferral; the names panel has none either).
- Any change to `routes/lore_mentions.py` or `routes/day.py`.

## Invariants to defend

- Two canon-write paths: the only canon write is `record_appellation` →
  `add_entity_fact`, the creator-CRUD chokepoint; `changed_by` /
  `created_by` is `"creator_crud"`.
- "Commit before touching any canon-writing path": this brief calls one; the
  executor commits A and B's state before starting.
- History is sacred: no route edits or deletes a choice, a rewrite, a
  resolution or a review (T10 counts).
- Creator control: nothing is written without Nia's click; the model never
  writes here.

## Decision rights

STOP:
- an anchor does not hold (other than drift);
- satisfying T2-T9 would need a write outside `record_appellation` and
  `write_day_mention_review`;
- a T value differs from the one written here: report the measured value;
  never edit the expectation to match.

ADAPT:
- FastAPI returns 422 for a malformed body before the handler runs (e.g.
  `verdict` not a string): leave it, report.
- `routes/lore_choices.py` needs a helper `lore_mentions.py` keeps private
  (other than `_world_id`, which is copied): copy it, report.

REPORT-ONLY:
- whether `app.py`'s route import block is still alphabetical after item 2.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/choice_review.py` → `PASS:` (R0, L0-L6, T0-T10).
- [ ] `python tooling/verify/checks/lore_isolation.py`, `name_index.py`,
      `name_resolution.py`, `single_canon_write.py`, `import_cycle.py`,
      `module_budget.py`, `function_length.py` → pass.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` is green.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` + `DECISIONS_INDEX.md` (item 5). No schema
  change. No CLAUDE.md.
