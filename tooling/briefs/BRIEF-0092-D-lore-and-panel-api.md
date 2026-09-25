# BRIEF 0092-D — "near names in the Lore answer, appellations from the panel"

Lot: LOT-0092-names.md (authoritative on conflict)
Depends on: B, C

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a
few lines is drift, not a STOP — note it and proceed; different content is
always a STOP.

- `lore_resolve.py` exports `near_candidates`, `NearCandidate`,
  `CATEGORIES`, `category_of_type` (B, C).
- `lore_query.py:48-55` `LoreResult` has six fields; `:161-165` builds the
  `unknown_entity` result.
- `lore_render.py:155-160` the two unknown-entity constants;
  `:178-187` `_render_unknown_entity` always renders WITHOUT.
- `cockpit/routes/lore.py:76-94` `_result_body` returns seven keys.
- `cockpit/routes/lore_mentions.py:30-31` `MentionResolveBody` has only
  `entity_id`; `:53-64` the resolve route commits once.
- `lore_mentions_read.py:43-46` `binding_is_valid`; `:63-71` `_candidates`.
- `writes/facets.py` `add_entity_fact` accepts `scope: Optional[ScopeChoice]`.

## Facts carried

### R-10 — the Lore query
Opened: `src/world_engine/lore_query.py:1-197`;
`tooling/verify/checks/lore_isolation.py:1-70` [M].
Finding: `LoreResult` (`:48-55`) fields: verdict, rows, trace,
ambiguous_mentions, unmatched_surface_forms, rejection_reason. Four
constructions (E8: `:138`, `:151`, `:161`, `:193`); `unknown_entity` at
`:161-165`. `_resolve_mentions` (`:94-118`). lore_isolation R1/R4: no
`chat(`, `db.add(`, `.commit(` in `lore_query.py` and `lore_selectors.py`.
Consequence: `near` is a new last field with a default, set only by the
`unknown_entity` construction.
### R-11 — the Lore renderer
Opened: `src/world_engine/lore_render.py:150-260`;
`tooling/verify/checks/lore_isolation.py:36-52, 521-635` [M].
Finding: `_UNKNOWN_ENTITY_WITH_NEAR` (`:155-157`) and
`_UNKNOWN_ENTITY_WITHOUT_NEAR` (`:158-160`); `_render_unknown_entity`
(`:178-187`) always renders WITHOUT, and its docstring says no
near-candidate source exists. R10: no `select(`, `db.add(`, `.commit(`,
`Session` identifier in `lore_render.py`; R11: no model call on an empty
verdict; R13: the six message constants exist by name.
Consequence: near candidates reach the renderer inside `LoreResult`, never
through a query.
### R-12 — the Lore routes
Opened: `src/world_engine/cockpit/routes/lore.py:1-133` [M].
Finding: `_result_body` (`:76-94`) returns verdict, rows, trace, plan,
candidates, answer, renderer. lore_isolation R6: no `chat(` and no `select(`
in this file.
Consequence: the body gains `near`, copied from the result.
### R-13 — the names panel backend
Opened: `src/world_engine/lore_mentions_read.py:1-99`;
`cockpit/routes/lore_mentions.py:1-72`; `writes/mentions.py:85-113`;
`tooling/verify/checks/lore_isolation.py:57-62, 699-718` [M].
Finding: `binding_is_valid` (`:43-46`) accepts any category when the
mention's is NULL; `_candidates` (`:63-71`) unions `resolve_named` over the
categories and sorts by name; `list_open_mentions` (`:82-99`) rows carry id,
surface, reason, category, excerpt, owner, candidates. Routes (`:48-73`):
GET `/api/lore/mentions`, POST `.../{id}/resolve` (body
`MentionResolveBody{entity_id}`, `:30-31`), POST `.../{id}/dismiss`; one
commit per request; `_CHANGED_BY = "creator_crud"` (`:27`).
`bind_mention(db, *, mention, entity_id, changed_by)` (`:91-111`) raises
`ValueError` when the surface no longer occurs plain. R17: these two modules
import none of `lore_selectors`, `lore_query`, `lore_plan`, `lore_render`,
`lore_prompt`, and those import neither.
Consequence: D adds its routes here and its reads in `lore_mentions_read`;
R17 needs no change.
### R-22 — canon writes from routes
Opened: `tooling/verify/checks/single_canon_write.py:1-30`;
`tooling/verify/canon_write_policy.txt:150-160`;
`tooling/standards/ARCHITECTURE_DECISIONS.md:16100-16135` [M].
Finding: the policy attributes ORM write sites (`.add()`/`.delete()`, raw
execute) to tables; a route that calls a `writes/*` function adds no site.
0091's names panel records exactly this ("`bind_mention` calls chokepoints
only, so the canon-write policy needs no new site").
Consequence: the new appellation route calls `record_appellation`, which
calls `add_entity_fact`; no policy edit.
### R-24 — route authentication
Opened: carried from LOT-0091 R-27 [M there].
Finding: no route authenticates; the cockpit binds `127.0.0.1:8000`.
Consequence: the new routes are guarded as Creation is. Deferral stands.

## Contracts

### C-01 — `NameScope` and the regime family (`src/world_engine/name_index.py`, new)
Produced by: A   Consumed by: A, B, C, D
```python
REGIMES: tuple[str, ...] = ("names_only", "creator", "prose", "perceiver")

@dataclass(frozen=True)
class NameScope:
    regime: str                                   # one of REGIMES
    known_fact_ids: Optional[frozenset[str]] = None
    exclude_entity_id: Optional[str] = None
    # __post_init__ raises ValueError when: regime not in REGIMES;
    # regime == "perceiver" and known_fact_ids is None;
    # regime != "perceiver" and known_fact_ids is not None.

NAMES_ONLY = NameScope("names_only")
CREATOR = NameScope("creator")
PROSE = NameScope("prose")
```
Regime semantics (which appellation facts count; names always count):

| regime | active entity names | appellation of an active entity |
|---|---|---|
| `names_only` | all | none |
| `creator` | all | all, creator-only included |
| `prose` | all | not creator-only AND has a scope |
| `perceiver` | all | not creator-only AND `fact_id in known_fact_ids` |

"Has a scope" (N17a): `fact.default_level != 'unaware'`, or at least one
`fact_default` row for the fact with `level != 'unaware'`.
"Creator-only": the fact id is in `facet_reads.creator_only_fact_ids(db, ids)`.
`exclude_entity_id`, when set, removes that entity's name and all its
appellations, in every regime.
The regime rules live in one module-level dict literal
`_APPELLATION_RULES` keyed exactly by `REGIMES`.
Who may use `CREATOR` (or construct `NameScope("creator", ...)`):
`name_index.py`, `lore_query.py`, `lore_mentions_read.py`,
`writes/facets.py`. Nowhere else.
Error and empty cases: see `__post_init__`.
### C-05 — `resolve_named` and its callers (`lore_resolve.py`)
Produced by: B   Consumed by: B, C, D
Signature:
`resolve_named(surface_form: str, category: str, world_id: str, db: Session, *, scope: NameScope) -> NamedResolution`
(`scope` is keyword-only, no default). Builds `name_index.surfaces(db,
world_id, scope)` once, walks `NAMED_RUNGS` in order and skips
`named_partial` unless `scope.regime == "creator"` (N12a). `NamedResolution`
and its three verdicts are unchanged.
Caller table (every caller, R-03):

| caller | scope |
|---|---|
| `lore_query._resolve_mentions` | `CREATOR` |
| `lore_mentions_read._candidates` | `CREATOR` |
| `lore_mentions_read.lookup_surface` (D) | `CREATOR` |
| `prose_tokens._mention_spans` | the scope `tokenize` received (C-08) |
| `subject_resolve.resolve_subject` | `NAMES_ONLY`, categories frozen to `("faction", "person", "place")` |
| `day_concordance` (`_rung_named_exact`, `_rung_named_token`) | `NameScope("perceiver", known_fact_ids=frozenset(resolve_levels_for_entity(db, character.id)))`, surfaces built once per `concord` and carried in `_ConcordContext.surfaces` |

Error and empty cases: `KeyError`-free for any category in
`_CATEGORY_ENTITY_TYPE`; an empty surface form walks every rung and returns
`unmatched`.
### C-06 — `near_candidates` (`lore_resolve.py`)
Produced by: B   Consumed by: D
```python
NEAR_RATIO = 0.8
NEAR_LIMIT = 5

@dataclass(frozen=True)
class NearCandidate:
    entity_id: str
    name: str          # entity.name
    entity_type: str
    surface: str       # the surface text that scored highest
    score: int         # 0-100, round(ratio * 100)

def near_candidates(surface_form: str, world_id: str, db: Session, *,
                    scope: NameScope, exclude_ids: frozenset[str] = frozenset()
                    ) -> tuple[NearCandidate, ...]
```
Raises `ValueError` unless `scope.regime == "creator"` (N12a). Ignores the
category (every surface counts). With `F`, `K`, `TF`, `TK` as in C-04 and
`ratio = difflib.SequenceMatcher(None, F, K).ratio()`, a surface qualifies
when `ratio >= NEAR_RATIO`, or when `{t in TF : len(t) >= 3}` and
`{t in TK : len(t) >= 3}` share a token. Per entity keep the qualifying
surface with the highest ratio. Drop ids in `exclude_ids`. Sort by
`(-score, name.casefold(), entity_id)`, keep the first `NEAR_LIMIT`.
Empty cases: `F == ""` returns `()`; no qualifying surface returns `()`.
Never picks; display only (N5c, N9b).
### C-09 — `record_appellation` (`writes/facets.py`)
Produced by: D   Consumed by: D (routes C-11)
Signature:
`record_appellation(db, *, entity_id: str, surface: str, scope_type: str, created_by: str) -> Optional[Fact]`
- `scope_type` in `("rencontre", "world", "none")`, else `ValueError`.
- `surface.strip()` empty -> `ValueError`; unknown entity -> `ValueError`.
- Duplicate: when `normalize_surface(surface)` equals `normalize_surface(s.text)`
  for some `s` in `name_index.surfaces(db, entity.world_id, CREATOR)` with
  `s.entity_id == entity_id`, return `None` and write nothing.
- Otherwise `add_entity_fact(db, entity_id=entity_id, facet="appellation",
  content=surface.strip(), created_by=created_by, scope=...)` with
  rencontre -> `ScopeChoice("rencontre", entity_id)`, world ->
  `ScopeChoice("world")`, none -> `ScopeChoice("none")`; return the fact.
- Never commits.
### C-10 — near candidates in the Lore answer
Produced by: D   Consumed by: E
`LoreResult` gains a last field `near: tuple[dict, ...] = ()`. Only the
`unknown_entity` construction sets it: one dict per unmatched surface form,
in plan order, `{"surface_form": str, "candidates": [{"entity_id", "name",
"type", "score"}, ...]}` from
`near_candidates(surface_form, world_id, db, scope=CREATOR)`.
`lore_render` adds one constant, verbatim:
```python
_NEAR_ITEM = "{nom} (ressemblance {pct} %)"
```
and `_render_unknown_entity` renders each block with
`_UNKNOWN_ENTITY_WITH_NEAR.format(surface_form=..., noms=", ".join(_NEAR_ITEM.format(nom=c["name"], pct=c["score"]) for c in candidates))`
when the surface's candidates are non-empty, else
`_UNKNOWN_ENTITY_WITHOUT_NEAR` as today. The six existing constants are not
edited. `/api/lore/ask` and `/api/lore/resolve` bodies gain
`"near": list(result.near)`.
### C-11 — the names panel API, amended (`cockpit/routes/lore_mentions.py`, `lore_mentions_read.py`)
Produced by: D   Consumed by: E
- `GET /api/lore/mentions`: each row gains `"near": [{"id", "name",
  "type", "score"}]` =
  `near_candidates(m.surface, world, db, scope=CREATOR, exclude_ids=<candidate ids>)`.
- `GET /api/lore/names/lookup?surface=<str>` -> 422 when the stripped
  surface is empty; else `{"surface": str, "candidates": [{"id", "name",
  "type"}], "near": [{"id", "name", "type", "score"}]}`; candidates = union
  over `CATEGORIES` of `resolve_named(surface, c, world, db,
  scope=CREATOR).candidate_ids`, sorted by name; near excludes them. Read in
  `lore_mentions_read.lookup_surface(db, world_id, surface) -> dict`.
- `POST /api/lore/appellations` body `{"entity_id": str, "surface": str,
  "scope_type": str = "rencontre"}` -> 422 when the entity is not an active
  entity of the world (`lore_mentions_read.entity_is_valid`: any category);
  `record_appellation(..., created_by="creator_crud")`; `ValueError` ->
  rollback, 422 with the message; one commit; returns `{"ok": true,
  "written": bool, "fact_id": str | null}`.
- `POST /api/lore/mentions/{id}/resolve` body gains
  `"record_appellation": bool = false` and `"scope_type": str =
  "rencontre"`. After `bind_mention`, when `record_appellation` is true,
  `record_appellation(db, entity_id=..., surface=mention.surface, ...)` in
  the same transaction; one commit; the response gains
  `"appellation_written": bool`.
Error cases: as today for 404 and bind's 422.

## Context

The resolver now finds appellations, partial and near names (B, C). This
brief puts near names in front of the creator — in the Lore answer and in
the names panel — and lets the panel record a missed name as an appellation
(N7c, N13a). The consultation pipeline stays read-only; every write lives in
the panel's route module (Q17d).

## Scope IN

1. `lore_query.py`: `LoreResult` gains `near` per C-10 (last field, default
   `()`); the `unknown_entity` construction fills it with
   `near_candidates(surface_form, world_id, db, scope=CREATOR)` for each
   unmatched surface form, in plan order, as
   `{"surface_form", "candidates": [{"entity_id", "name", "type", "score"}]}`.
   No other construction changes.
2. `lore_render.py`: add `_NEAR_ITEM` verbatim (C-10);
   `_render_unknown_entity` renders WITH when the surface's candidates are
   non-empty; rewrite its docstring (near names are computed upstream in
   `lore_query` and carried in `LoreResult.near`). The six existing constants
   are not edited.
3. `cockpit/routes/lore.py` `_result_body`: add `"near": list(result.near)`.
4. `lore_mentions_read.py`:
   - `list_open_mentions` rows gain `"near"` per C-11.
   - new `lookup_surface(db, world_id, surface) -> dict` per C-11.
   - new `entity_is_valid(db, world_id, entity_id) -> bool` =
     `any(validate_binding(entity_id, c, world_id, db) for c in CATEGORIES)`.
   - `binding_is_valid` and `_candidates` iterate `CATEGORIES` instead of
     the private map.
5. `writes/facets.py`: `record_appellation` per C-09 (imports
   `normalize_surface` from `lore_resolve` and `CREATOR`, `surfaces` from
   `name_index`).
6. `cockpit/routes/lore_mentions.py`, per C-11: `GET /api/lore/names/lookup`,
   `POST /api/lore/appellations` (body model `AppellationBody`), and the
   resolve route's two new body fields and response field. One commit per
   request; `ValueError` from any writer -> `db.rollback()` then 422 with the
   message. `created_by`/`changed_by` = `_CHANGED_BY`.
7. `tooling/verify/checks/name_resolution.py`: add
   - G9 render: a `LoreResult` with verdict `unknown_entity` and `near`
     holding two candidates renders
     "Aucune entité nommée « la reyne » dans ce monde. Noms proches :
     Ysolde (ressemblance 83 %), Reine Grise (ressemblance 63 %)." — built
     from the constants, asserted by equality with
     `_UNKNOWN_ENTITY_WITH_NEAR.format(...)`; with empty candidates, the
     WITHOUT text.
   - G10 `record_appellation`: the four rows of LOT Gate output (b)
     "`record_appellation`".
   - G11 routes with FastAPI's `TestClient` on the fixture DB: lookup of
     "Maelys" returns Maelis in `near` with score 83; POST appellation
     writes then returns `written: false` on the same surface; resolve
     with `record_appellation: true` binds and writes one appellation fact;
     with `scope_type: "nope"` returns 422 and the mention is still open.
8. `ARCHITECTURE_DECISIONS.md`: amend nothing; append
   `## NEAR NAMES AND APPELLATIONS FROM THE PANEL (TICKET-0092) -- THE LORE MISS HAS A WAY OUT (BRIEF-0092-d, no schema change)`
   recording N9b, N13a, C-11, and that the pipeline still never writes;
   regenerate the index.

## Scope OUT

- Any write, route or `Session` in `lore_query.py`, `lore_selectors.py`,
  `lore_render.py`, `lore_plan.py`, `lore_prompt.py` (R1-R17).
- Frontend (E).
- A contextual likelihood (N9c). The K1 review list.
- Route authentication (R-24).

## Invariants to defend

- "The lore renderer receives rows, never a `Session`": near names arrive in
  `LoreResult`, computed in `lore_query`.
- "Commit before touching any canon-writing path": `writes/facets.py` and
  the panel routes. Commit before items 5-6.

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold.
- Any `lore_isolation.py` rule fails.
- `single_canon_write.py` asks for a new allowed site.

ADAPT:
- `TestClient` is unavailable in the environment: test the route handler
  functions directly with a `Session`; report.

REPORT-ONLY:
- None.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] PASS: `name_resolution.py`, `name_index.py`, `lore_isolation.py`,
      `lore_selectors.py`, `single_canon_write.py`, `identity_tokens.py`,
      `module_budget.py`, `function_length.py`, `decisions_index.py`
      (with `WORLD_ENGINE_ENV=test`).
- [ ] `/review-step` and `/close-step` run.

## Docs to update

`ARCHITECTURE_DECISIONS.md` + `DECISIONS_INDEX.md` (Scope IN 8).
