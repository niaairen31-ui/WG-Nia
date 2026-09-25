# BRIEF 0092-B — "resolver on name surfaces"

Lot: LOT-0092-names.md (authoritative on conflict)
Depends on: A

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a
few lines is drift, not a STOP — note it and proceed; different content is
always a STOP.

- `name_index.py` exists with `surfaces`, `NameScope`, `CREATOR`,
  `NAMES_ONLY`, `PROSE` (A).
- `lore_resolve.py:28` `_CATEGORY_ENTITY_TYPE: dict[str, str]` with three
  keys; `:33` `NAMED_RUNGS = ("named_exact", "named_token")`; `:112`
  `resolve_named(surface_form, category, world_id, db)`; `:152`
  `validate_binding` holds the module's only `select(` besides the rungs.
- The six resolver call sites of R-03 are the only ones:
  `grep -rn "resolve_named(\|rung_named_exact(\|rung_named_token(" src scripts tooling/verify`
  matches E1/E5 of the lot (paste your output in the report).
- `day_concordance.py:60` imports `rung_named_exact, rung_named_token`;
  `:133` `_ConcordContext`; `:260` and `:361` build it; `:156-161`
  `_rung_named_alias` returns None.
- `subject_resolve.py:47` `for category in sorted(_CATEGORY_ENTITY_TYPE):`.
- `checks/day_concordance.py:74` `EXPECTED_RUNGS` has five names.

## Facts carried

### R-02 — the Lore resolver
Opened: `src/world_engine/lore_resolve.py:1-169` [M];
`tooling/verify/checks/lore_resolve.py:1-230` [M].
Finding: `_CATEGORY_ENTITY_TYPE: dict[str, str]` (`:28`, three keys);
`NAMED_RUNGS = ("named_exact", "named_token")` (`:33`); `normalize_surface`
(`:42-59`) casefolds, strips accents, drops up to three leading tokens from
`_LEADING_TOKENS` (`:35-37`: chez, le, la, les, l, du, de, des, au, aux, a), splits on
whitespace and apostrophes. `rung_named_exact` (`:62-73`) and
`rung_named_token` (`:76-94`) each `select(Entity)` of one type in the world,
names only; the token rung requires the name's tokens to be a subset of the
surface's tokens with one token of 3+ characters. `_NAMED_RUNG_LOOKUPS`
(`:97-100`). `NamedResolution` (`:103-109`). `resolve_named` (`:112-137`):
first rung with a hit; one id -> `matched`, two or more -> `ambiguous`, none
-> `unmatched`. `pre_resolved` (`:140-149`). `validate_binding` (`:152-169`)
selects an active entity of the category's type in the world.
Check rules: R1 no `db.add(`/`.commit(`/`chat(` in `lore_resolve.py`; R2 none
of the identifiers `_cast_one`, `CAST_PRECEDENCE`, `who_is_at`, `Character`
(`:33`); R3 `NAMED_RUNGS`/`_NAMED_RUNG_LOOKUPS` bijection (`:137-165`); R4
every `select(` in `lore_resolve.py` has `world_id` among the names of its
`.where(` call, and zero `select(` calls is a failure (`:167-207`); R5 no
`_normalize_surface` def in `day_concordance.py`.
Consequence: rungs become pure functions over surfaces; `validate_binding`
keeps the module's one `select(` (R4 stays non-vacuous). No identifier
`Character` may enter this module (R2), so the perceiver's known facts are
computed by the day chain, not here.
### R-03 — every caller of the resolver
Opened: enumeration E1, E5 (Gate output (c)); `subject_resolve.py:1-107`;
`lore_mentions_read.py:1-99`; `lore_query.py:94-118`;
`day_mutations.py:240-250`; `cockpit/crud/knowledge.py:56` [M].
Finding: `resolve_named` is called at `lore_query.py:108` (Lore question),
`lore_mentions_read.py:67` (names panel), `prose_tokens.py:191` (tokenizer
mentions), `subject_resolve.py:48` (reached from `day_mutations.py:246` in
play, from `cockpit/crud/knowledge.py:56` through `unresolved_subjects`, and
from `scripts/apply_ticket_0087_subject_participants.py:62`). The day chain
calls `rung_named_exact`/`rung_named_token` directly
(`day_concordance.py:147`, `:153`). `validate_binding` is called at
`lore_mentions_read.py:46` and `cockpit/routes/lore.py:123`. Six callers in
total; no other in `src/`, `scripts/`, `tooling/verify/`.
Consequence: every one of them receives an explicit scope (C-05). A default
scope would silently give the creator regime to a caller that forgot one.
### R-04 — the day concordance
Opened: `src/world_engine/day_concordance.py:1-501`;
`tooling/verify/checks/day_concordance.py:1-80, 290-320` [M]; scratch
import probe [P].
Finding: imports `normalize_surface, rung_named_exact, rung_named_token`
(`:60`). `MATCHING_RUNGS` (`:75-77`) = named_exact, named_token, named_alias,
occupation, presence. `_ConcordContext` (`:132-137`) holds `world_id`,
`place_candidate_ids`, `reachable_location_ids`. `_rung_named_exact`/
`_rung_named_token` (`:144-153`) skip non-`named` mentions and delegate.
`_rung_named_alias` (`:156-161`) returns None; its comment calls it a
structural no-op forever. `_resolve_place_candidates` (`:255-268`) builds its
own context (`:260`) and calls `_rung_named_exact`. `concord` (`:353-406`)
builds the context at `:361-365`. Check R6 pins
`EXPECTED_RUNGS = {"named_exact", "named_token", "named_alias",
"occupation", "presence"}` (`checks/day_concordance.py:74`).
Probe [P]: with `lore_resolve` importing a `name_index` that imports
`facet_reads` only inside a function, adding a module-level
`from .knowledge_resolve import resolve_levels_for_entity` to
`day_concordance.py` imports cleanly (`day_concordance`, `facet_reads`,
`prose_tokens`, `knowledge_resolve`, `day_mutations`, `cockpit.app`) and
`import_cycle.py` passes.
Consequence: the context carries the perceiver's surfaces, built once per
`concord` call; `named_alias` and its comment stay as they are (N16a).
### R-05 — what a character knows
Opened: `src/world_engine/knowledge_resolve.py:1-80, 220-232`;
`src/world_engine/facet_reads.py:108-123` [M].
Finding: resolution order (docstring `:5-27`): stored row, self (participant
of a descriptive-facet fact), rencontre, location chain, faction, world,
`fact.default_level`. `resolve_levels_for_entity(db, entity_id)` (`:220`)
returns `fact_id -> level` for every fact of the entity's world resolving
above `'unaware'`, in one pass. `known_facts_of` uses exactly this as
"known" (`facet_reads.py:108-123`).
Consequence: the perceiver regime's known set is
`frozenset(resolve_levels_for_entity(db, character.id))`.
### R-17 — knowledge-subject resolution
Opened: `src/world_engine/subject_resolve.py:1-107`;
`tooling/verify/checks/subject_resolution.py:1-30, 140-180` [M].
Finding: `resolve_subject` walks `sorted(_CATEGORY_ENTITY_TYPE)` (`:47`),
which is `("faction", "person", "place")` today. `subject_resolution.py` A2
requires at least one `resolve_named(` Name-call in `subject_resolve.py` and
no raw bypass.
Consequence: B freezes the walk to a local tuple with the same three values
and passes the names-only scope; A2 still holds.
### R-21 — budgets
Opened: `wc -l`, `grep -c "^\s*def "` on each file this lot edits [M].
Finding (lines / functions): `lore_resolve.py` 169/6; `prose_tokens.py`
222/12; `day_concordance.py` 501/16; `lore_query.py` 197/3;
`lore_mentions_read.py` 99/7; `subject_resolve.py` 107/2; `lore_render.py`
276/18; `writes/facets.py` 261; `cockpit/routes/lore_mentions.py` 72;
`cockpit/routes/lore.py` 133; `facets.py` 103. Ceilings: 1000 lines and 40
functions per module, 80 lines per function (`module_budget.py`,
`function_length.py`).
Consequence: no module is near a ceiling; no extraction is planned.
### R-25 — check fixture idioms
Opened: `tooling/verify/checks/identity_tokens.py:108-133`;
`tooling/verify/checks/day_concordance_golden.py:78-150` [M].
Finding: `identity_tokens.py` `_fresh_engine()` (`:108-118`) sets
`WORLD_ENGINE_DATABASE_URL` to a temp SQLite file, purges `world_engine`
modules from `sys.modules`, then `create_db_and_tables()`; `_world(session,
label)` (`:121-133`) adds a `World` and returns an `entity(kind, name)`
factory. `day_concordance_golden.py` builds a `Character` row per NPC or PC
with `id=entity.id, world_id, character_type, current_location_id`
(`:125-145`) and calls `concord` with `Mention(category, surface_form,
kind)` (`:223`).
Consequence: the new checks copy these two helpers (by name and body) and
this `Character` construction; they never touch Nia's DB.

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
### C-02 — `NameSurface` (`name_index.py`)
Produced by: A   Consumed by: A, B, D
```python
@dataclass(frozen=True)
class NameSurface:
    text: str               # entity.name, or the appellation rendered by prose_render.fact_texts
    entity_id: str
    entity_name: str        # entity.name, for display
    entity_type: str        # entity.type
    source: str             # "name" | "appellation"
    fact_id: Optional[str]  # None iff source == "name"
```
Text is never normalized here; callers normalize (`lore_resolve.normalize_surface`).
### C-03 — `surfaces` (`name_index.py`)
Produced by: A   Consumed by: A (`prose_tokens`), B (`lore_resolve`,
`day_concordance`), D (`writes/facets.record_appellation`)
Signature: `surfaces(db: Session, world_id: str, scope: NameScope) -> tuple[NameSurface, ...]`
Behaviour:
1. Active entities of `world_id` (`Entity.status == "active"`), minus
   `scope.exclude_entity_id`: one `source="name"` surface each.
2. Unless the regime is `names_only`: every `fact` with
   `Fact.world_id == world_id` and `Fact.facet == "appellation"`, joined to
   its `fact_participant`, whose participant is one of the entities kept in
   step 1; filtered per C-01's table; text through
   `prose_render.fact_texts`; a surface whose text is empty or None is
   skipped.
3. Order: names first, by `entity_id`; then appellations by
   `(entity_id, fact_id)`.
Every `select(` in the module has `world_id` among the names of its
`.where(` call. `creator_only_fact_ids` is imported inside `surfaces`, never
at module level (R-07). No `db.add(`, `.commit(`, `chat(`.
Error and empty cases: a world with no active entity returns `()`.
### C-04 — the rung family (`src/world_engine/lore_resolve.py`)
Produced by: B   Consumed by: B (`resolve_named`, `day_concordance`)
Every rung has the signature
`(surface_form: str, category: str, surfaces: Sequence[NameSurface]) -> Optional[list[str]]`,
considers only surfaces with `category_of_type(s.entity_type) == category`,
and returns the sorted distinct `entity_id`s that match, or `None` when none
does. Let `F = normalize_surface(surface_form)`, `TF = set(F.split())`,
`K = normalize_surface(s.text)`, `TK = set(K.split())`.

| rung | a surface matches when |
|---|---|
| `named_exact` | `F != ""` and `K == F` |
| `named_token` | `TK` non-empty, `TK <= TF`, and some token of `TK` has 3+ characters |
| `named_partial` | `TF` non-empty, every token of `TF` has 3+ characters, and `TF <= TK` |

A name and an appellation matching at the same rung are candidates of equal
rank (N11a): two distinct entity ids make the verdict `ambiguous`.
`NAMED_RUNGS = ("named_exact", "named_token", "named_partial")`, in
bijection with `_NAMED_RUNG_LOOKUPS`.
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
### C-07 — categories (`lore_resolve.py`, `lore_plan.py`)
Produced by: B (three categories), widened by C   Consumed by: B, C, D, E
After B:
```python
_CATEGORY_ENTITY_TYPE: dict[str, tuple[str, ...]] = {
    "place": ("location",), "person": ("character",), "faction": ("faction",),
}
def category_of_type(entity_type: str) -> Optional[str]   # None when no category claims the type
```
After C:
```python
_CATEGORY_ENTITY_TYPE: dict[str, tuple[str, ...]] = {
    "place": ("location",), "person": ("character",), "faction": ("faction",),
    "object": ("item",), "other": (),
}
OTHER_CATEGORY = "other"
CATEGORIES: tuple[str, ...] = tuple(_CATEGORY_ENTITY_TYPE)
def category_of_type(entity_type: str) -> str   # the claiming category, else "other"
```
`validate_binding(entity_id, category, world_id, db)`: for `other`, the
entity's type is claimed by no other category; otherwise its type is in the
category's tuple; always active and in `world_id`; unknown category ->
`False`.
`lore_plan._MENTION_CATEGORIES = ("place", "person", "faction", "object", "other")`
after C (R9 parity with the dict keys).
### C-08 — `tokenize`, amended (`prose_tokens.py`)
Produced by: A (scope), B (mention path)   Consumed by: A (`writes/facets`),
`writes/knowledge.py:173` (unchanged call)
Signature:
`tokenize(db, *, world_id, text, mentions=None, scope: NameScope = PROSE) -> Tokenized`
Raises `ValueError` when `scope.regime` is not `"prose"` or `"names_only"`.
The index is built from `name_index.surfaces(db, world_id, scope)`; keys and
matching are unchanged. From B on, `_mention_spans` passes the same `scope`
to `resolve_named`. Callers for an appellation's own text pass
`NameScope("names_only", exclude_entity_id=<owner id>)` (N15b):
- `add_entity_fact` with `facet == "appellation"`: owner = `entity_id`.
- `edit_entity_fact` on a fact whose `facet == "appellation"`: owner = the
  fact's participant when it has exactly one; `NameScope("names_only")` with
  no exclusion otherwise.
Every other call keeps `PROSE`.

## Context

A put every name surface behind `name_index`. This brief makes the resolver
read it: appellations become resolvable, a partial rung and near names exist
for the creator's surfaces, and every caller states whose names it sees.
Categories stay three here; C widens them.

## Scope IN

1. `src/world_engine/lore_resolve.py`:
   - `_CATEGORY_ENTITY_TYPE` becomes `dict[str, tuple[str, ...]]` with the
     same three keys and one-type tuples (C-07 "After B"); add
     `category_of_type(entity_type) -> Optional[str]`.
   - Rewrite `rung_named_exact`, `rung_named_token`, and add
     `rung_named_partial`, per C-04 (pure functions over surfaces, no
     `select(`). `NAMED_RUNGS` and `_NAMED_RUNG_LOOKUPS` gain
     `named_partial`.
   - `resolve_named(..., *, scope)` per C-05: one `name_index.surfaces`
     call, skip `named_partial` unless `scope.regime == "creator"`.
   - `near_candidates` and `NearCandidate`, `NEAR_RATIO`, `NEAR_LIMIT` per
     C-06 (`difflib` from the stdlib).
   - `validate_binding` keeps its `select(Entity)` with `Entity.world_id ==
     world_id` in the `.where(` (lore_resolve R4) and matches
     `Entity.type.in_(_CATEGORY_ENTITY_TYPE[category])`; unknown category ->
     `False`.
   - No identifier `Character` anywhere in the module (R2).
2. Callers, per C-05's table:
   - `lore_query.py:108`: `scope=CREATOR`.
   - `lore_mentions_read.py:67`: `scope=CREATOR`.
   - `subject_resolve.py`: replace the walk at `:47` by a module-level
     `_SUBJECT_CATEGORIES: tuple[str, ...] = ("faction", "person", "place")`
     and pass `scope=NAMES_ONLY`; drop the `_CATEGORY_ENTITY_TYPE` import;
     update the docstring at `:30-31` accordingly (N10a).
   - `prose_tokens.py`: `_mention_spans` receives the `scope` `tokenize`
     received and passes it to `resolve_named`; `_CATEGORY_OF_TYPE` and its
     comment are removed, `_category` and the category filter at `:185` use
     `lore_resolve.category_of_type` and `category in _CATEGORY_ENTITY_TYPE`.
   - `day_concordance.py`: add
     `from .knowledge_resolve import resolve_levels_for_entity` at module
     level (R-04 probe) and `from .name_index import NameScope, surfaces as
     name_surfaces`; `_ConcordContext` gains `surfaces: tuple = ()`; in
     `concord`, before `_resolve_place_candidates`, build
     `surfaces = name_surfaces(db, character.world_id,
     NameScope("perceiver", known_fact_ids=frozenset(resolve_levels_for_entity(db, character.id))))`
     and pass it into both context constructions (`_resolve_place_candidates`
     takes it as a parameter); `_rung_named_exact`/`_rung_named_token` call
     `rung_named_exact(mention.surface_form, mention.category, ctx.surfaces)`
     (and token). `_rung_named_alias`, its comment and `MATCHING_RUNGS` stay
     untouched (N16a).
3. `tooling/verify/checks/name_index.py`: add R6 — across
   `src/world_engine/**/*.py`, every call whose callee name (a Name, or the
   last part of an Attribute) is `resolve_named` or `near_candidates` passes
   a `scope=` keyword; every call whose callee name is `surfaces` or
   `name_surfaces` has three positional arguments or a `scope=` keyword. At
   least one `resolve_named` call must be found (vacuity guard).
4. `tooling/verify/checks/name_resolution.py` (created by A with G0): pass
   `scope=CREATOR` in G0, then add, with exact set equality:
   - G1: the six rows of LOT Gate output (b) "Rungs", through
     `resolve_named` (verdict, entity_id, candidate_ids, rung).
   - G2: the "Near" table: `near_candidates("Maelys", ..., scope=CREATOR)`
     returns only Maelis with score 83; for "reine" the order is
     La Reine Grise (63) then Reine Ysolde (59); `scope=PROSE` raises
     `ValueError`; `exclude_ids` drops an id.
   - G3 day chain: a PC P and an NPC Y (`Character` rows, R-25) at one
     location; appellation "la reine" on Y with `ScopeChoice("none")`; a
     `knowledge` row for P on that fact at `knows` (same `write_knowledge`
     call shape as `writes/facets.py:179-182`, `is_secret=False`).
     `concord([Mention(category="person", surface_form="la reine",
     kind="named")], P, db)` matches Y via `named_exact`; with a second PC
     Q who holds no row, the same mention is unmatched.
   - G4 subject: `resolve_subject("la reine", world_id, db)` is unmatched
     with that appellation present (N10a).
   - G5 tokenizer mention path: a generator mention
     `{"name": "Varn", "category": "person"}` next to "Maelis Varn" stays
     unresolved (no partial rung outside `creator`).
5. `ARCHITECTURE_DECISIONS.md`: append
   `## NAMES RESOLVE THROUGH THE INDEX (TICKET-0092) -- APPELLATIONS, PARTIAL AND NEAR NAMES (BRIEF-0092-b, no schema change)`
   recording C-04's table, C-05's caller table, N11a, N12a, N16a, N10a;
   regenerate `DECISIONS_INDEX.md`.

## Scope OUT

- `object`/`other` categories, the planner and its prompt (C).
- Near names shown anywhere (D, E).
- `named_alias` and `MATCHING_RUNGS` (N16a). `day_extract`, the
  `day_mention_resolution` CHECK (N6a).
- `entity_author` mention vocabulary (R-18).
- Any caching of surfaces across requests.

## Invariants to defend

- "Secrets are structurally excluded": the day chain must see only
  `perceiver` surfaces; the tokenizer only `prose`/`names_only`. A caller
  using `CREATOR` outside C-01's list is a STOP.
- "Commit before touching any canon-writing path": `prose_tokens` feeds
  `writes/`; commit before item 2.

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold.
- A `resolve_named` caller not in R-03 (a seventh caller).
- `day_concordance_golden.py` or `subject_resolution.py` fails after the
  change.
- `import_cycle.py` fails with the module-level `knowledge_resolve` import.

ADAPT:
- `day_concordance.py` exceeds a function-length ceiling: extract the
  surface construction into `_perceiver_surfaces(character, db)`; report.

REPORT-ONLY:
- Wall-clock of `concord` on the golden fixture before and after.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] PASS: `name_index.py`, `name_resolution.py`, `lore_resolve.py`,
      `lore_isolation.py`, `day_concordance.py`,
      `day_concordance_golden.py`, `subject_resolution.py`,
      `identity_tokens.py`, `import_cycle.py`, `module_budget.py`,
      `function_length.py`, `decisions_index.py` (run with
      `WORLD_ENGINE_ENV=test`).
- [ ] `grep -n "Character" src/world_engine/lore_resolve.py` returns nothing.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

`ARCHITECTURE_DECISIONS.md` + `DECISIONS_INDEX.md` (Scope IN 5).
