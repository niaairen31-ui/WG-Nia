# BRIEF 0095-B — "the pending-choice reader"

Lot: LOT-0095-choice-review.md (authoritative on conflict)
Depends on: BRIEF-0095-A (tables, writers, `choice_review.py`)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a few
lines is drift, not a STOP — note it and proceed; different content is always
a STOP.

- A has landed: `src/world_engine/models/pipeline.py` declares
  `DayMentionChoiceCandidate`, `DayMentionChoiceEvidence`, `DayMentionReview`
  per C-01; `writes.write_day_mention_review` exists;
  `tooling/verify/checks/choice_review.py` holds R0 and passes.
- `src/world_engine/day_choice.py:39` `_EXCERPT_EDGE = " \t\n\"'«»“”.,;:!?…"`;
  `:151` `def judge_choice(`; `:164`
  `normalized = normalize_surface(answer["extrait"].strip(_EXCERPT_EDGE))`.
- `src/world_engine/lore_mentions_read.py:30` `def active_world_id(`; `:56`
  `def excerpt(text: Optional[str], surface: str) -> str:`.
- `src/world_engine/facet_reads.py:62` `def facts_of(`.
- `tooling/verify/checks/lore_isolation.py:86`
  `PANEL_FILES = (SRC / "cockpit" / "routes" / "lore_mentions.py", SRC / "lore_mentions_read.py")`.
- `src/world_engine/lore_choices_read.py` does not exist.

## Facts carried

Verbatim from the lot header.

#### R-01 — `day_mention_choice` declaration
Opened: `src/world_engine/models/pipeline.py:205-247`
Finding [M]: table `day_mention_choice`; CHECKs `category IN
('place','person','faction')`, `trigger IN ('ambiguous','near')`, `verdict IN
('accepted','rejected','declined','failed')`, `attempts IN (1, 2)`, and the
shape CHECK (`accepted` ⇒ `chosen_entity_id` set; `declined`/`failed` ⇒
NULL). `candidate_ids` and `evidence_fact_ids` are `str` columns holding JSON
arrays in display order. Indexes `idx_day_mention_choice_pass(pass_play_id)`
and `idx_day_mention_choice_world_verdict(world_id, verdict)`. The header
comment says append-only (W2), one row per model call, refused calls
included. `created_at = _created_ts()`; the next block is the
`# skill_resolution` comment at line 250.
Consequence: the table is not altered (no rebuild). The two id lists are
relationalized into two child tables (C-01, decision G1). The JSON columns
stay NOT NULL and keep being written as an audit copy that no code in `src/`
reads.

#### R-04 — which ids can disappear: facts are hard-deleted, entities are not
Opened: `src/world_engine/writes/facts.py:121-139`;
`src/world_engine/writes/facets.py:300-304`;
`src/world_engine/cockpit/crud/facets.py:130-133`;
`src/world_engine/cockpit/crud/entities.py:817-828`; `src/world_engine/db.py:116-126`
Finding [M]: `delete_free_fact` hard-deletes a free fact after its knowledge,
defaults and participants; `remove_entity_fact` calls it for any descriptive
fact, and the creator route `delete_entity_fact` calls that. Entity deletion
in CRUD is a soft delete (`status = 'inactive'`). SQLite FK enforcement is on
(`PRAGMA foreign_keys=ON` on every connection).
Consequence: an FK from a history row to `fact(id)` would make every fact
ever cited as evidence, or written as a reviewed appellation, undeletable.
So `day_mention_choice_evidence.fact_id` and
`day_mention_review.appellation_fact_id` carry **no FK** (plain TEXT, as the
JSON was). Entity ids keep their FK, as `chosen_entity_id` does.

#### R-07 — what "known to everyone" means for a fact
Opened: `src/world_engine/knowledge_resolve.py:1-37` (docstring) and `195-205`,
`255-265`, `315-330` (the `world` default and `default_level` fallback in code);
`src/world_engine/models/canon_knowledge.py:86-124` (`Fact`), `163-192`
(`FactDefault`); `src/world_engine/name_index.py:1-43`
Finding [M]: resolution tiers, most specific first: stored `knowledge` row;
self (participant of a descriptive fact); `fact_default` `rencontre`
(acquaintances); `location` (nearest ancestor); `faction` (active
membership); `world`; finally `fact.default_level` (NOT NULL, default
`'unaware'`). `fact_default` columns: `fact_id`, `scope_type` (CHECK
`world|faction|location|rencontre`), `scope_id` (NULL iff `world`, FK
entity), `level` (the six-value ladder). The `perceiver` name regime counts an
appellation only when its fact id is in the perceiver's known set.
Consequence: a cited fact is "known to everyone" when it has a
`fact_default` with `scope_type='world'` and `level <> 'unaware'`, or when its
`fact.default_level <> 'unaware'` (tier 7). That, and only that, preselects
`world` (C-05, decision C2).

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

#### R-10 — the evidence reader
Opened: `src/world_engine/facet_reads.py:62-104`; `src/world_engine/facets.py:37-60`
Finding [M]: `facts_of(db, *, entity_id, facets, ...) -> list[FactRow]`
(`fact_id, facet, aspect, content, created_at`), content rendered through
`prose_render.fact_texts`, creator-only facts excluded in the query, ordered by
`facets` order, `created_at`, id. `FACETS` is the registry dict. Measured: a
fact written "Elle chante à la taverne." on a world holding the location
"La Taverne" renders as "Elle chante à La Taverne." (the name was tokenized).
Consequence: K1 reads the cited facts through `facts_of(db,
entity_id=chosen, facets=tuple(FACETS))` filtered to the choice's evidence
ids, never raw `content_raw` (`identity_tokens.py` R1). Expected strings in
the checks are rendered strings.

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

#### R-18 — the 0094 store check's fixture
Opened: `tooling/verify/checks/day_mention_choice_store.py:52-100`, `102-195`
Finding [M]: S1 writes an `accepted` record with `candidate_ids=[maelis_id,
"autre"]` (line 119) and asserts `json.loads(row.candidate_ids) == [maelis_id,
"autre"]` (line 134). `"autre"` is not an entity id. `_record()` defaults
`candidate_ids=[]`, `evidence_fact_ids=[]`. `_parents` builds World → Session
→ Batch → two character entities → PassPlay, flushing each.
Consequence: once C-02 writes candidate rows with an FK to `entity`, S1's
`"autre"` fails the flush. A replaces it with a second real entity (S1 only);
S2-S5 are unchanged.

#### R-22 — governance files
Opened: `tooling/tickets/TICKET-0094-concordance-h2.md:1-15`;
`tooling/verify/checks/claude_md_contract.py:12-14`, `71`, `149-153`;
`tooling/standards/ARCHITECTURE_DECISIONS.md:16502`, `16669-16720`;
`tooling/verify/checks/decisions_index.py:15-17`;
`tooling/verify/checks/pipeline_state.py:1-60`
Finding [M]: TICKET-0094 line 5 reads `status: live-gate`, `current_brief:`
empty (Nia reports it passed). CLAUDE.md's File-structure section is capped at
80 lines, and 0094-D recorded it at the cap (no line added). Its file-map line
`lore_*.py, subject_resolve.py  # resolver/selectors/plan/names-panel reads;
subject<->entity` already covers a `lore_choices_read.py`. Decision headers
must match `^## .+ \(BRIEF-\d{4}(-[a-z])?(, ...)*, (schema v\d+\.\d+|no schema
change)\)$`. `pipeline_state.py`'s docstring (line 22) says "at least one
arrow resolving to a real file"; its implementation (`check_section_shape`,
lines 107-114) fails on EVERY Machine-checkable arrow that does not resolve,
once `status` is in `{brief, exec, verify, live-gate, done}`. Measured: this
lot's ticket at `status: brief` fails pipeline_state on the two new checks
until they exist.
Consequence: A closes 0094 in its own commit and creates both new checks
before running any gate (pipeline_state stays red on this ticket from its
deposit until A's check files exist). No CLAUDE.md edit in this lot.
Decision headers use the lowercase brief letter.

## Contracts

Verbatim from the lot header.

Two families are written here first and re-read after their last member:

- **review verdict** — the values `agreed` / `disagreed` and the appellation
  scopes `rencontre` / `world` / `none`: the table CHECKs (C-01), the writer
  (C-03), the route (C-07), the panel (C-08).
- **pending row** — the dict one reviewable choice becomes (C-06): built only
  by `list_pending_choices` (C-05), returned unchanged by the GET route
  (C-07), rendered by the panel (C-08).

#### C-01 — tables `day_mention_choice_candidate`, `day_mention_choice_evidence`, `day_mention_review`
Produced by: A   Consumed by: C-02, C-03, C-05, the migration
DDL (schema v2.08):
```sql
CREATE TABLE day_mention_choice_candidate (
  id         TEXT PRIMARY KEY,
  choice_id  TEXT NOT NULL REFERENCES day_mention_choice(id),
  ordinal    INTEGER NOT NULL CHECK (ordinal >= 1),
  entity_id  TEXT NOT NULL REFERENCES entity(id)
);
CREATE UNIQUE INDEX idx_day_mention_choice_candidate_choice
  ON day_mention_choice_candidate(choice_id, ordinal);

CREATE TABLE day_mention_choice_evidence (
  id         TEXT PRIMARY KEY,
  choice_id  TEXT NOT NULL REFERENCES day_mention_choice(id),
  ordinal    INTEGER NOT NULL CHECK (ordinal >= 1),
  fact_id    TEXT NOT NULL    -- no FK: a descriptive fact can be hard-deleted (R-04)
);
CREATE UNIQUE INDEX idx_day_mention_choice_evidence_choice
  ON day_mention_choice_evidence(choice_id, ordinal);

CREATE TABLE day_mention_review (
  id                   TEXT PRIMARY KEY,
  world_id             TEXT NOT NULL REFERENCES world(id),
  choice_id            TEXT NOT NULL REFERENCES day_mention_choice(id),
  verdict              TEXT NOT NULL CHECK (verdict IN ('agreed','disagreed')),
  entity_id            TEXT REFERENCES entity(id),
  appellation_fact_id  TEXT,  -- no FK: the appellation can be hard-deleted later (R-04)
  appellation_scope    TEXT CHECK (appellation_scope IS NULL
                                   OR appellation_scope IN ('rencontre','world','none')),
  created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
  CHECK (
    (verdict <> 'agreed' OR entity_id IS NOT NULL)
    AND (appellation_fact_id IS NULL OR entity_id IS NOT NULL)
    AND ((appellation_fact_id IS NULL) = (appellation_scope IS NULL))
  )
);
CREATE INDEX idx_day_mention_review_choice ON day_mention_review(choice_id);
```
Meaning: a candidate row is the `ordinal`-th candidate shown to the model;
an evidence row is the `ordinal`-th fact shown, flattened across candidates
in display order (the JSON order). A review row is Nia's verdict on one
choice: `agreed` → `entity_id` is the model's choice; `disagreed` →
`entity_id` is the entity she picked, or NULL for "no known entity" (H2).
`appellation_fact_id` / `appellation_scope` are set only when an appellation
was actually written. All three tables are append-only (W2), non-canon.
`choice_id` on the review is NOT unique: J1's "one review per choice" is the
route's rule (C-07), so a later re-review needs no rebuild (A1).
Models (`src/world_engine/models/pipeline.py`): `DayMentionChoiceCandidate`,
`DayMentionChoiceEvidence`, `DayMentionReview`, fields in DDL order,
`created_at = _created_ts()` on the review only, ids `default_factory=_uuid`,
CHECK names `ck_day_mention_choice_candidate_ordinal`,
`ck_day_mention_choice_evidence_ordinal`, `ck_day_mention_review_verdict`,
`ck_day_mention_review_scope`, `ck_day_mention_review_shape`.

#### C-04 — `day_choice.excerpt_key`
Produced by: B   Consumed by: `judge_choice`, C-05
Signature: `def excerpt_key(excerpt: str) -> str` in
`src/world_engine/day_choice.py`, placed right above `judge_choice`. Pure.
Returns `normalize_surface(excerpt.strip(_EXCERPT_EDGE))`. `judge_choice`
line 164 becomes `normalized = excerpt_key(answer["extrait"])`; nothing else
in `judge_choice` changes.
Measured: `excerpt_key("« la forge du port. »") == "forge du port"`;
`excerpt_key(" à ") == ""`.

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

## Case tables

Verbatim from the lot header's gate output.

**(b1) Inclusion in the pending list (C-05):**

| choice | reviewed? | listed |
|---|---|---|
| `accepted` (chosen set) | no | yes |
| `accepted` | yes | no (J1) |
| `rejected`, chosen set | no | yes (E2) |
| `rejected`, chosen NULL (out of range) | — | no |
| `declined` / `failed` | — | no (E2) |
| another world | — | no |

**(b2) Excerpt source and preselected scope (C-05):**

| excerpt key | in a cited fact of the chosen entity | in declaration | source | preselect |
|---|---|---|---|---|
| < 3 chars (or NULL) | — | — | none | rencontre |
| ≥ 3 | yes, a hit has a `world` scope | — | facts | world |
| ≥ 3 | yes, no hit has a `world` scope | — | facts | rencontre |
| ≥ 3 | no | yes | declaration | rencontre |
| ≥ 3 | no (fact edited, deleted, or excerpt spans two facts) | no | none | rencontre |

A `world` scope = `fact.default_level != 'unaware'` or a `fact_default`
`world` above `unaware` (R-07). « Pas d'accord »'s scope is always preset to
`rencontre` (the evidence speaks for the wrong entity).

**(b4) "planned" (R-11):**

| path that wrote the choice | rewrite of that pass_play before it? | planned |
|---|---|---|
| 409 (`_record_refused_choices`) | no (a day plans once, after) | false → « sans plan » |
| plan path | yes (generation 1, same transaction, constructed first) | true |
| plan path that failed later (502) | — | never stored |

## Context

A stored each choice's candidates and evidence as rows and added the review
record. This brief builds the read side: which choices wait for Nia, what the
model cited, where that citation came from, and which scope K1 proposes
(C2). No route and no UI yet.

## Scope IN

1. **`excerpt_key` (C-04).** In `src/world_engine/day_choice.py`, add
   `def excerpt_key(excerpt: str) -> str` right above `judge_choice`, with the
   docstring `"""The judge's normalized excerpt (C-06 of LOT-0094): edge
   punctuation stripped, then `normalize_surface`. Shared with the K1 reader
   (TICKET-0095, C-04)."""`, returning
   `normalize_surface(excerpt.strip(_EXCERPT_EDGE))`. Line 164 becomes
   `normalized = excerpt_key(answer["extrait"])`. Nothing else changes in
   that module.

2. **The reader.** Create `src/world_engine/lore_choices_read.py` exactly per
   C-05 and C-06. Module docstring: "Reads for the model-choice review
   (TICKET-0095, K1, C-05/C-06): the choices of the active world that wait
   for Nia's verdict (E2, J1), what the model cited and where it came from,
   and the scope K1 proposes for an appellation (C2). Candidates and evidence
   are read from their rows (G1), never from the JSON audit columns.
   Read-only: no `db.add`, no commit, no model call. Isolated from the
   consultation pipeline like the names panel (`lore_isolation.py` R17)."
   Imports: `Optional` from `typing`; `Session`, `select` from `sqlmodel`;
   `excerpt_key` from `.day_choice`; `facts_of` from `.facet_reads`; `FACETS`
   from `.facets`; `excerpt` from `.lore_mentions_read` (bound as
   `text_excerpt`); `normalize_surface` from `.lore_resolve`; `Batch`,
   `DayMentionChoice`, `DayMentionChoiceCandidate`, `DayMentionChoiceEvidence`,
   `DayMentionReview`, `DayRewrite`, `Entity`, `Fact`, `FactDefault`,
   `PassPlay` from `.models`. Private helpers are free (each ≤ 80 lines); the
   public names are exactly C-05's. The `scopes` rule reads the facts' own
   `default_level` and `fact_default` rows in two queries per call (ids
   `IN (...)`). `"planned"` compares Python `datetime`s read from
   `DayRewrite.created_at` rows of the choice's `pass_play_id`.

3. **Isolation.** In `tooling/verify/checks/lore_isolation.py`, `PANEL_FILES`
   gains `SRC / "lore_choices_read.py"`; R17's docstring paragraph adds
   "and, since TICKET-0095, `lore_choices_read.py`".

4. **`choice_review.py` gains L0-L6** (update the docstring; keep R0; the
   `PASS:` line names R0 and L0-L6). Fixture `_k1_world(engine) -> dict`
   (C reuses it; write it once, at module level), on a fresh temp DB
   (`_fresh_engine` as in `day_mention_review_store.py`):
   - World `"k1"` (`is_active=True`) and World `"other"` (`is_active=False`);
     `models.Session(world_id=k1, number=1)`; `writes.write_batch(...,
     changed_by="creator")`; entities (world k1): `"Aldric"` (character),
     `"Maelis Varn"` (character), `"Maelis Orn"` (character), `"La Taverne"`
     (location); each writer's row added then flushed (R-18's chain);
   - `f_varn = add_entity_fact(db, entity_id=varn, facet="histoire",
     content="Elle tient la forge du port.", created_by="creator",
     scope=ScopeChoice("world"))`; `f_orn = add_entity_fact(db,
     entity_id=orn, facet="histoire", content="Elle chante à la taverne.",
     created_by="creator", scope=ScopeChoice("location", tavern))`;
   - `writes.write_pass_play(..., character_id=aldric, declared_action="Je
     vais voir Maelis à la forge.")`; commit;
   - base record `r(**kw)`: `category="person", surface_form="Maelis",
     trigger="ambiguous", candidate_ids=[varn, orn], evidence_fact_ids=[f_varn,
     f_orn], verdict="accepted", chosen_entity_id=varn,
     excerpt="la forge du port", reason="r", verdict_detail=None,
     attempts=1`, overridden by `kw`;
   - session 1 (a 409 attempt — no rewrite): `write_day_mention_choices` with
     c2 = `r(surface_form="Maelys", trigger="near", candidate_ids=[orn],
     evidence_fact_ids=[f_orn], chosen_entity_id=orn, excerpt="à la
     forge")`, c3 = `r(verdict="rejected", chosen_entity_id=orn,
     excerpt="boulanger", verdict_detail="excerpt not in the chosen
     candidate's facts")`, c4 = `r(verdict="declined", chosen_entity_id=None,
     excerpt=None)`; commit; then `time.sleep(0.01)`;
   - session 2 (the plan): `writes.write_day_rewrite(db, world_id=k1,
     pass_play_id=..., generation=1, rendered_text="x", resolutions=[])`,
     then c1 = `r()` and c5 = `r(surface_form="Varn")`; commit (an empty
     `resolutions` list is accepted — measured);
   - session 3: `write_day_mention_review(db, world_id=k1, choice_id=c5,
     verdict="agreed", entity_id=varn, appellation_fact_id=None,
     appellation_scope=None)`; commit;
   - session 4: c6 = `r(trigger="near", candidate_ids=[orn],
     evidence_fact_ids=[f_orn], chosen_entity_id=orn, excerpt="chante")`;
     commit.
   Rules (every expected value below was measured on a prototype of C-05
   over `main`):
   - L0 (AST): `lore_choices_read.py` holds no `chat(` call, no call to
     `db.add`, `db.add_all` or `db.commit` (receiver named `db`), no `Name`/`Attribute` `CREATOR`, and no
     `Name`, `Attribute.attr` or `keyword.arg` equal to `candidate_ids` or
     `evidence_fact_ids`.
   - L1: `excerpt_key("« la forge du port. »") == "forge du port"`;
     `excerpt_key(" à ") == ""`.
   - L2: `is_reviewable` on `SimpleNamespace(verdict=..., chosen_entity_id=...)`:
     accepted+"x" → True; rejected+"x" → True; rejected+None → False;
     declined+None → False; failed+None → False.
   - L3: `preselected_scope`: `("facts", [{"scopes": [{"scope_type":
     "world", "scope_name": None}]}])` → `"world"`; `("facts", [{"scopes":
     [{"scope_type": "location", "scope_name": "X"}]}])` → `"rencontre"`;
     `("facts", [{"scopes": [{"scope_type": "rencontre", "scope_name": "Y"},
     {"scope_type": "world", "scope_name": None}]}])` → `"world"`;
     `("declaration", [])` → `"rencontre"`; `("none", [])` → `"rencontre"`.
   - L4: `[row["id"] for row in list_pending_choices(db, k1)] == [c2, c3,
     c1, c6]`; `list_pending_choices(db, other) == []`.
   - L5 (exact values per row; names are `entity.name`):
     - every row: `day == {"day_number": 1, "character_name": "Aldric",
       "declaration": "Je vais voir Maelis à la forge.", "planned": <below>}`;
     - c2: `planned` False; `chosen["name"] == "Maelis Orn"`; candidate names
       `["Maelis Orn"]`; `excerpt_source == "declaration"`; `evidence == []`;
       `preselected_scope == "rencontre"`;
     - c3: `planned` False; `verdict == "rejected"`; `verdict_detail ==
       "excerpt not in the chosen candidate's facts"`; candidate names
       `["Maelis Varn", "Maelis Orn"]`; `excerpt_source == "none"`;
       `evidence == []`; `preselected_scope == "rencontre"`;
     - c1: `planned` True; `chosen["name"] == "Maelis Varn"`; candidate
       names `["Maelis Varn", "Maelis Orn"]`; `excerpt_source == "facts"`;
       `evidence == [{"fact_id": f_varn, "content": "Elle tient la forge du
       port.", "scopes": [{"scope_type": "world", "scope_name": None}]}]`;
       `preselected_scope == "world"`;
     - c6: `planned` True; `excerpt_source == "facts"`; `evidence ==
       [{"fact_id": f_orn, "content": "Elle chante à La Taverne.", "scopes":
       [{"scope_type": "location", "scope_name": "La Taverne"}]}]` (the
       rendered text: the name was tokenized, R-10);
       `preselected_scope == "rencontre"`.
   - L6: every row's key set equals C-06's top-level keys, and `day`'s key
     set equals `{"day_number", "character_name", "declaration", "planned"}`.
   Vacuity: L4 must have listed four rows.

5. Append to `ARCHITECTURE_DECISIONS.md` an entry headed
   `## THE PENDING-CHOICE READER (TICKET-0095) -- WHAT K1 SHOWS AND WHICH SCOPE IT PROPOSES (BRIEF-0095-b, no schema change)`:
   E2 and J1 as the listing rule (table b1); how the cited fact is found with
   the judge's own key (`excerpt_key`, C-04); the source/preselection rule
   (table b2) and what "known to everyone" means (R-07); "planned" by
   timestamps (R-11, table b4); the reader reads rows only (G1). Regenerate
   `DECISIONS_INDEX.md`.

## Scope OUT

- The route and the writes: C. The panel: D.
- Any change to what `judge_choice` accepts (item 1 is a pure extraction).
- `cast` rows (Y2c), `declined`/`failed` rows (E3), reviewed rows (J2).
- Showing the matched appellation beside a candidate (F2).
- `include_creator_only` anywhere (only `lore_selectors.py` may pass it).

## Invariants to defend

- Secrets structurally excluded: evidence is read through `facts_of`
  without `include_creator_only`, so a creator-only fact never appears (and
  never did: H2 never cited one).
- "UI-visible data never lives in JSON": L0 forbids the JSON names in the
  reader.
- Read-only surface: L0.

## Decision rights

STOP:
- an anchor does not hold (other than drift);
- `day_choice.py` (the check) J1-J8 change result after item 1;
- an L5 value differs from the one written here: report the measured value;
  never edit the expectation to match.

ADAPT:
- `import_cycle.py` reports a cycle through `day_choice`: import
  `excerpt_key` lazily inside `cited_evidence` (the codebase's lazy-import
  idiom, `import_cycle.py` docstring), report.

REPORT-ONLY:
- how long `list_pending_choices` takes on the executor's DB, if it holds
  choices.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/choice_review.py` → `PASS:` (R0, L0-L6).
- [ ] `python tooling/verify/checks/day_choice.py`, `lore_isolation.py`,
      `name_index.py`, `identity_tokens.py`, `import_cycle.py`,
      `module_budget.py`, `function_length.py` → pass.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` is green.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` + `DECISIONS_INDEX.md` (item 5). No schema
  change. No CLAUDE.md (R-22: the `lore_*.py` file-map line covers the new
  module).
