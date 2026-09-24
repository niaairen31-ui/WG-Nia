# BRIEF 0091-K — "name-resolution panel in Lore"

Lot: LOT-0091-lore-as-facts.md (authoritative on conflict)
Depends on: J

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved.

- `lore_isolation.py` R1-R16 name only the pipeline modules of R-22.
- `cockpit/app.py:130` mounts the Lore router.
- `Lore.svelte` 179 lines, header comment `:1-8` says read-only.
- `writes/mentions.py` exists (J).

## Facts carried

### R-22 — the Lore surface and its gates
Opened: `tooling/verify/checks/lore_isolation.py:1-60`;
`src/world_engine/lore_render.py:27-113`; `lore_selectors.py:187-265`;
`tooling/verify/checks/lore_selectors.py:5-26`;
`frontend/src/lore/Lore.svelte:1-30`; `cockpit/app.py:130` [M].
Finding: `lore_isolation.py` R1-R16 name only `lore_selectors.py`,
`lore_query.py`, `lore_render.py`, `lore_plan.py`, `lore_prompt.py` and
`cockpit/routes/lore.py` (R6: no `chat(`, no `select(`). `lore_render`'s
`_SECTION_FORMATTERS` (`:87-96`) is the closed section vocabulary; an
unknown section raises (`:99-113`). `entity_dossier` (`:187-199`) returns
identity, relations, knowledge, memberships, goals. `SELECTORS` (`:251`),
`_SELECTOR_LOOKUPS` (`:253-265`); `checks/lore_selectors.py` R6 requires
every `context_sections` string to be an emitted `"section"` literal.
`Lore.svelte` declares itself read-only (`:1-8`) and labels sections in
`SECTION_LABEL` (`:22-29`); 179 lines; `lore.svelte.js` 88 lines.
The Lore router is mounted at `cockpit/app.py:130`.
Consequence: H adds a `facets` section (formatter + label). K adds a
separate route module and panel; R1-R16 stay untouched; a new rule forbids
imports between the panel's modules and the consultation pipeline.

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

### R-27 — the cockpit has no request authentication
Opened: `grep -rn "Depends(" src/world_engine/cockpit | grep -v get_session`
(empty) [M]; `CLAUDE.md:525` (`http://127.0.0.1:8000`) [M].
Finding: no role check on any route; Creation writes are as open as Lore.
Consequence: K's panel is guarded exactly as Creation is. Route
authentication is a named deferral (ticket > 0091).

## Contracts

### C-03 — `update_fact_content` (new, `writes/facts.py`)
Produced by: A   Consumed by: C-05, C-16
```python
def update_fact_content(db, *, fact, content, changed_by) -> Fact
```
Appends `{"content": <previous>, "changed_by": changed_by, "at": <iso UTC>}`
to `change_history` (same shape as `update_typed_fact_content`), flags it
modified, overwrites the content. Works on free and typed facts.
Declared in the policy (`fact`).

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

### C-16 — the name-resolution panel API (`cockpit/routes/lore_mentions.py`, new)
Produced by: K   Consumed by: K's frontend
- `GET /api/lore/mentions` -> `{"mentions": [{"id", "surface", "reason",
  "category", "excerpt", "owner": {"kind": "fact"|"knowledge", "id"},
  "candidates": [{"id", "name", "type"}]}]}` for the active world, open
  only, oldest first. `excerpt` = up to 80 rendered characters around the
  first plain occurrence of `surface`. Candidates recomputed with
  `resolve_named` (all three categories when `category` is NULL).
- `POST /api/lore/mentions/{id}/resolve` body `{"entity_id"}`: 404 unknown
  or already resolved; 422 when `validate_binding` fails for the category
  (any category when NULL); otherwise replaces the first plain occurrence
  of `surface` in the owner's raw text with `entity_token(entity_id,
  surface)` through `update_fact_content` (fact) or `write_knowledge`
  (knowledge), marks resolved, commits once.
- `POST /api/lore/mentions/{id}/dismiss`: marks resolved with no entity.

## Context

Unresolved names need a place where Nia resolves them. Q17d puts it in the
Lore shell, reopening the 0085 lock in a bounded way: the consultation
pipeline stays pure.

## Scope IN

1. New `src/world_engine/lore_mentions_read.py` (list + excerpt +
   candidates, C-16 GET) and `src/world_engine/cockpit/routes/lore_mentions.py`
   (the three routes of C-16); mount the router in `cockpit/app.py` after
   the Lore router.
2. The resolve route writes through `update_fact_content` or
   `write_knowledge` and `resolve_mention`; declare the route function in
   `canon_write_policy.txt` only if the gate attributes a site to it
   (it calls chokepoints only).
3. Frontend: `frontend/src/lore/NamesPanel.svelte` + `namesPanel.svelte.js`;
   `Lore.svelte` gains a tab "Noms à lier" beside the question view; the
   header comment `:1-8` is amended to state the bounded reopening (Q17d).
   Each line: surface, reason, excerpt, a candidate selector (plus a search
   over existing entities of the category), "Lier", "Ignorer".
4. `lore_isolation.py` R17 per gate (e); docstring names Q17d.
5. Rebuild and commit the bundle.

## Scope OUT

- Any write from the consultation pipeline. K1 review list (later ticket).
- Route authentication (deferred, R-27).

## Invariants to defend

- 0085 lock, as reopened: R1-R16 unchanged and green.

## Decision rights

STOP:
- Any Mini-RECON anchor that does not hold (always a STOP, protocol §2).
- R17 cannot be expressed without editing R1-R16.

ADAPT:
- `Lore.svelte` would exceed 1000 lines: put the tab switch in a new
  `LoreShell.svelte`; report.

REPORT-ONLY:
- None.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] A fixture `ambigu` mention lists both candidates; "Lier" writes the
      token and closes the line; the fact's history holds the old text.
- [ ] "Ignorer" closes an `inconnu` line with no entity.
- [ ] Green: `lore_isolation.py`, `page_contract.py`,
      `frontend_build_fresh.py`, `static_asset_freshness.py`,
      `single_canon_write.py`, `corpus_gate.py`.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

`ARCHITECTURE_DECISIONS.md`: amend the Lore read-only entry with Q17d's
bounded reopening.
