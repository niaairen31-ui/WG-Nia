# BRIEF 0091-J — "identity tokens (F1)"

Lot: LOT-0091-lore-as-facts.md (authoritative on conflict)
Depends on: I (locked order I2', not a dependency)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `Fact.content` and `Knowledge.content` are the model attributes (R-24).
- The readers as restated by AMENDMENT-0091-04 (lines after E, G, H, I):
  `knowledge_resolve.py:358-359`; `context.py:124` (`_knowledge_line`) and
  `:678` (PC knowledge list); `lore_selectors.py:183`, `:263`;
  `writes/facts.py:110,116` and `:147,153`; `writes/relations.py:374`
  (`lien.content`); `cockpit/crud/facets.py:53` (`_fact_dict`);
  `link_author.py:162` ("already knows" lines) and `:814`
  (`_apply_canon_knowledge_patch`); `tick_context.py`, `cockpit/crud/_shared.py`,
  `link_context.py`, `writes/knowledge.py` readers of R-24;
  `facet_reads.py:100` (`FactRow.content`).
- `relation_orientation.py:33-35` `lien_fact_content`;
  `writes/relations.py` `_endpoint_names` (`:124`), `_birth_typed_fact`
  (`:134`).
- Same content shifted is drift; different content is a STOP.
- `lore_resolve.py:42` `normalize_surface`, `:112` `resolve_named`.
- `checks/relation_orientation.py:156`.

## Facts carried

### R-19 — `write_relation` and the lien fact
Opened: `writes/relations.py:123-294`; `relation_orientation.py:23-45` [M].
Finding: `write_relation` (`:220-294`) creates then flushes, then
`_birth_typed_fact` (`:133-147`) when `is_new` (`:285-292`). The function
body is about 75 lines (80 is the ceiling). `_endpoint_names` (`:123-130`)
returns the two names. `lien_fact_content(name_a, relation_type, name_b)`
(`relation_orientation.py:33-35`) returns
`f"{name_a} éprouve « {relation_type} » envers {name_b}."`;
`connects_to_fact_content` (`:38-41`). Both typed births pass through
`create_fact(relation_id=…)`.
Consequence: C adds the encounter in a helper called from the `is_new`
branch (not inline, to stay under 80 lines). A tags both typed births with
facet `lien`. J poses tokens in the lien content.

### R-23 — the world-scoped name resolver
Opened: `src/world_engine/lore_resolve.py:1-169` [M].
Finding: `_CATEGORY_ENTITY_TYPE = {"place": "location", "person":
"character", "faction": "faction"}` (`:28`); `normalize_surface(text)`
(`:42`); `rung_named_exact` (`:62`); `rung_named_token` (`:76`);
`resolve_named(surface_form, category, world_id, db) -> NamedResolution`
(`:112`); `validate_binding(entity_id, category, world_id, db)` (`:152`).
No model call; two or more candidates are reported, never picked.
Consequence: J reuses `normalize_surface` and `resolve_named` for
generator `mentions`; K reuses `resolve_named` to recompute candidates and
`validate_binding` before writing a token.

### R-24 — readers of `fact.content` and `knowledge.content`
**Corrected by AMENDMENT-0091-04**: the enumeration below filtered hits by
receiver name and was therefore incomplete; `scene_format.py:71,76` read
`discoverable_detail`, not `Knowledge` (out of scope). Lines have also
shifted since E, G, H and I. The authoritative list is the amendment's,
and BRIEF-J now requires a complete AST enumeration of `.content` before
any edit.
Opened: `grep -rn "\.content\b" src/world_engine` filtered to `Fact` and
`Knowledge` receivers [M] (pasted in gate (c)).
Finding: fact: `knowledge_resolve.py:299-300`, `cockpit/crud/_shared.py:264`,
`writes/facts.py:69,75`, `writes/relations.py:362` (`lien.content`);
knowledge: `context.py:121-122` (`_knowledge_line`), `tick_context.py:126`,
`scene_format.py:71,76`, `lore_selectors.py:155,233`,
`cockpit/crud/_shared.py:255`, `link_context.py:109`,
`writes/knowledge.py:98,178`. `analyzer_transcript.py:779` is a
`conversation_message` row — out. Other `.content` hits in `src/` are
`ctx.content`, `discoverable_detail.content` or message payloads — out.
Checks: `relation_orientation.py:156` compares `fact.content` to
`lien_fact_content`.
Consequence: J renames the model attribute to `content_raw` on both
models (SQL column name unchanged) so every reader is found by the
interpreter, then routes each through C-13.

### R-26 — check fixtures that build facts
Opened: `tooling/verify/checks/fact_spine.py:1-140`,
`knowledge_resolution.py:78-146`, `known_reachability.py:178-240`,
`relation_orientation.py:150-160` [M]. FK enforcement: `db.py:126` [C].
Finding: `fact_spine.py` asserts (1) no participant on a typed fact, (2) no
knowledge with NULL `fact_id`, (3) level vocabulary, (4) AST: no
`db.add(Fact(...))` / `FactParticipant(...)` outside `writes/facts.py`;
fixture calls `create_fact` at `:138`. `knowledge_resolution.py:120`
calls `create_fact` and `:126-146` `create_fact_default` for the tier
fixture. `known_reachability.py:233` calls `create_fact_default`.
Consequence: A updates the two `create_fact` fixtures with a facet; D
extends `knowledge_resolution.py` with the new tiers; J updates
`relation_orientation.py:156`.

## Contracts

### C-05 — the entity-fact writer (`src/world_engine/writes/facets.py`, new)
Produced by: E (module), with `add_entity_fact` used by I's migration
logic only as a reference (I writes SQL)   Consumed by: C-12, E's cores, J
```python
@dataclass(frozen=True)
class ScopeChoice:
    scope_type: str            # "none"|"world"|"location"|"faction"|"rencontre"
    scope_id: str | None = None

def add_entity_fact(db, *, entity_id, facet, content, created_by,
                    aspect=None, scope: ScopeChoice | None = None) -> Fact
def write_entity_facets(db, *, entity_id, facets: dict, created_by) -> list[Fact]
def edit_entity_fact(db, *, fact_id, content, changed_by) -> Fact
def remove_entity_fact(db, *, fact_id) -> None
def facts_payload_keys() -> frozenset[str]   # descriptive facet names
```
`add_entity_fact`: facet must be in `DESCRIPTIVE_FACETS` (else
`ValueError`); empty/whitespace content raises; for a `bloc` facet, an
existing fact with this entity as participant, the same facet and the same
aspect raises `ValueError("bloc facet already has a fact")`;
`create_fact(facet=…, aspect=…)`, `attach_participants([entity_id])`, then
the default: `scope` when given (`none` writes nothing; `world` scope_id
None; others require scope_id), else the facet's preset (C-01). Default
level is always `knows`.
`write_entity_facets`: keys must be descriptive facet names or the
special key `creator_meta`; a `bloc` value is a `str`; an `affirmation`
value is a `list[str]` **or a `str`, split into one fact per non-empty
stripped line** (Q20b); `coutume` is a `list[{"aspect": str | None,
"content": str, "hidden": bool}]` where `hidden` means scope `none` and not
hidden means the preset. `creator_meta` (a `str`) becomes one `histoire`
fact with scope `none` plus one `knowledge` row written through
`write_knowledge(entity_id=<the entity>, fact_id=<that fact>,
subject="creator_meta", level="unaware", is_secret=True)` — the entity never
knows the creator's note (same shape as C-18's `character.secrets` row).
Empty strings are skipped. Returns the created facts in input order.
`edit_entity_fact`: refuses a fact whose facet is not descriptive;
delegates to C-03. `remove_entity_fact`: same refusal; delegates to C-04.
All four add rows and never commit.

### C-11 — the entity write payload, amended (`cockpit/crud`)
Produced by: E   Consumed by: F, generators
`EntityWriteBody` gains `facets: dict | None = None` (shape of C-05's
`write_entity_facets`) and, from J, `mentions: list[dict] | None = None`
(`[{"name": str, "category": "place"|"person"|"faction"}]`). The
descriptive fields leave `ENTITY_BASE_FIELDS` (`description`) and the
type specs (`appearance`, `backstory`, `aversion`, `secrets`,
`internal_structure`, `philosophy`, `internal_tensions`). Create cores call
`write_entity_facets` after the entity row is flushed, in the same
transaction. `update_entity` with a non-empty `facets` returns 422 with
detail `"descriptive lore is edited through /api/entities/{id}/facts"`.
The PC-creation body of `create_player_character` loses `description`,
`appearance` and `backstory` and gains the same `facets` field.

### C-13 — prose render (`src/world_engine/prose_render.py`, new)
Produced by: J   Consumed by: C-10, G, H, K, every fact/knowledge reader
```python
TOKEN_RE = re.compile(r"\[\[e:([0-9a-fA-F-]{36})\|([^\]|]*)\]\]")
def entity_token(entity_id: str, name: str) -> str   # strips "]" and "|" from name
def render(db, text: str | None) -> str | None
def render_many(db, texts: list[str | None]) -> list[str | None]
def fact_text(db, fact) -> str
def knowledge_text(db, k) -> str | None
```
`render`: each token becomes the entity's current `name`; an id with no
entity row becomes the token's stored name; text without tokens is
returned unchanged; `None` stays `None`. `render_many` issues one entity
query for all ids. `fact_text` renders `fact.content_raw`;
`knowledge_text` renders `k.content_raw`. The only module outside
`models/`, `writes/` and `knowledge_resolve.py` that reads `content_raw`.

### C-14 — token posing (`src/world_engine/prose_tokens.py`, new)
Produced by: J   Consumed by: C-05, `writes/knowledge.py`, `writes/relations.py`
```python
@dataclass(frozen=True)
class Unresolved:
    surface: str
    reason: str            # "ambigu" | "inconnu"
    category: str | None   # "place"|"person"|"faction" when known

@dataclass(frozen=True)
class Tokenized:
    text: str
    unresolved: tuple[Unresolved, ...]

def tokenize(db, *, world_id, text, mentions=None) -> Tokenized
```
Index = every active entity `name` of the world plus every `appellation`
fact content, each normalized with `lore_resolve.normalize_surface`.
Longest match first, whole words only, text already inside a token
skipped. A surface naming exactly one entity becomes `entity_token`; a
surface naming two or more stays plain and yields `Unresolved(reason=
"ambigu")`. Each `mentions` entry not found in the text by the index is
resolved with `resolve_named`: one candidate → its first occurrence in the
text is tokenized; zero → `Unresolved("inconnu", category)`; two or more →
`Unresolved("ambigu", category)`. Never calls a model.

### C-15 — `unresolved_mention` (`models/pipeline.py`) and its writer
Produced by: A (table), J (writer `writes/mentions.py`)   Consumed by: K
```python
class UnresolvedMention(SQLModel, table=True):
    __tablename__ = "unresolved_mention"
    # idx_unresolved_mention_world_open (world_id, resolved_at)
    id: str (uuid pk); world_id: str FK world NOT NULL
    fact_id: str | None FK fact
    knowledge_id: str | None FK knowledge
    surface: str NOT NULL
    reason: str NOT NULL          # "ambigu" | "inconnu"
    category: str | None
    created_at: datetime NOT NULL
    resolved_at: datetime | None
    resolved_entity_id: str | None FK entity   # NULL + resolved_at = dismissed
```
Exactly one of `fact_id`, `knowledge_id` is set (guarded in the writer).
No JSON column. Writer functions: `record_unresolved(db, *, world_id,
fact_id=None, knowledge_id=None, items: tuple[Unresolved, ...])`,
`resolve_mention(db, *, mention, entity_id)`, `dismiss_mention(db, *,
mention)`.

## Context

G2 is done. From now on a name written into canon prose is a reference.
This brief renames the text attribute so every reader is found, adds one
render, and poses tokens on new writing.

## Scope IN

1. `models/canon_knowledge.py`: `Fact.content` -> `content_raw` and
   `Knowledge.content` -> `content_raw`, SQL column name kept `content`
   (`sa_column=Column("content", …)` with the current type and nullability).
2. New `src/world_engine/prose_render.py` per C-13; new
   `src/world_engine/prose_tokens.py` per C-14; new
   `src/world_engine/writes/mentions.py` with C-15's three functions.
3. **Before any edit**, paste into the report an AST enumeration of every
   `ast.Attribute` with `attr == "content"` in `src/world_engine/`
   (outside `models/`), each hit classified as Fact, Knowledge or other
   (with the receiver's origin). Every Fact/Knowledge **reader** reads
   through `fact_text` / `knowledge_text` / `render_many`;
   `facet_reads.FactRow.content` is rendered. This includes
   `cockpit/crud/facets.py::_fact_dict` (`fact_text`), the PC knowledge
   list at `context.py:678` (`knowledge_text`) and the "already knows"
   lines at `link_author.py:162` (`render_many`, one query).
   `scene_format.py` reads `discoverable_detail`: untouched.
3b. `link_author.py::_apply_canon_knowledge_patch` (`:814`): the lines that
   read the current knowledge content, merge the patch and call
   `write_knowledge` move **unchanged in logic** into a new
   `writes/knowledge.py::apply_knowledge_patch(db, *, knowledge, patch,
   **<the keyword arguments those lines pass to write_knowledge>)`,
   which reads `content_raw`; `link_author.py` calls it and never touches
   raw content (AMENDMENT-0091-04, option b). New text coming from the patch
   is new writing and is tokenized by the write path.
   `knowledge_resolve.py` copies `content_raw` into transient rows.
3c. `scripts/seed_pilot.py::upsert_knowledge` (`:101-140`): its
   create-or-converge logic moves **unchanged in logic** into
   `writes/knowledge.py::upsert_knowledge_row(db, *, id, **fields)`, which
   maps the `content` key to `content_raw` and returns a status
   (`"created"`, `"updated"` or `"existing"`); the seed calls it and keeps
   its `_created` / `_updated` / `_existing` bookkeeping from that status.
   Seed text is **not tokenized** (treated like migrated text, L2), so the
   seed stays idempotent and creates no `unresolved_mention` rows
   (AMENDMENT-0091-05). `seed_pilot.py::_seed_customs` (`:262`) compares
   `fact_text(db, fact)` instead of `m.Fact.content`.
3d. Readers outside `src/` go through the render: `scripts/test_context.py`
   (`:87,96,106,112,120`), `checks/fact_facets.py` (`:285,301,413`),
   `checks/relation_orientation.py:156-157`.
4. Token posing on new writing: `writes/facets.py` (`add_entity_fact`,
   `edit_entity_fact`) and `writes/knowledge.py` (content path) call
   `tokenize` and `record_unresolved` with the created fact or knowledge id.
   `writes/relations.py::_birth_typed_fact` and `_refresh_lien_content`
   pass `entity_token(id, name)` for both endpoints into
   `lien_fact_content` / `connects_to_fact_content`.
5. Generator `mentions`: `_TYPE_FIELDS` of the three types gains, verbatim,
   `'mentions (tableau d\'objets {"name","category"} — chaque personne,
   lieu ou faction nommé dans le texte ; category parmi
   place|person|faction)'`; drafts carry it; `EntityWriteBody.mentions`
   (C-11) reaches `write_entity_facets`, which passes it to `tokenize`.
6. New `tooling/verify/checks/identity_tokens.py` R1-R4 of gate (e);
   `relation_orientation.py:156` compares `fact_text(db, fact)` to the
   rendered expected content.

## Scope OUT

- Tokens on migrated text (L2). A mention picker (Q15b).
- `relation.notes`, `event.*`, `npc_goal.description`,
  `world_law.text` (deferred).
- The names panel (K).

## Invariants to defend

- No model call in `prose_tokens.py`.
- Canon writes stay in the chokepoints; `unresolved_mention` is non-canon
  with one writer.

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold (always a STOP, protocol §2).
- A module outside `writes/` needs raw content to write it back (the
  `link_author` case is settled by item 3b; any other is a STOP).

ADAPT:
- A raw-SQL reader selects the `content` column directly: route its value
  through `render`; report.
- The step-3 enumeration finds a Fact/Knowledge **reader** not listed in
  the anchors: route it through `fact_text` / `knowledge_text` /
  `render_many`; report it with its line (AMENDMENT-0091-04). A **writer**
  outside `writes/` that reads raw content to write it back is a STOP.

REPORT-ONLY:
- The number of `unresolved_mention` rows created by the fixture run.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] Renaming an entity changes the rendered lien fact of its relations.
- [ ] A fact written with two same-named NPCs creates one `ambigu` row.
- [ ] Green: `identity_tokens.py`, `relation_orientation.py`,
      `fact_spine.py`, `knowledge_resolution.py`, `single_canon_write.py`,
      `corpus_gate.py`.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: "Identity tokens (F1)" — token shape,
render chokepoint, `content_raw` allow-list.
