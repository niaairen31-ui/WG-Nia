# RECON — Region commit mechanics (chantier 2)

**Status: report-only.** No code, no canon, no schema, no template was
modified to produce this document. `git status` after this step shows
exactly one added file (this one) and no change to any `.py`, template, or
schema file. No `/review-step` / `/close-step` was run — there is no engine
code change to review or close.

Scope and item numbering follow `BRIEF-NN-recon-region-commit.md`.

---

## 1. `create_entity` transaction boundary (atomicity)

### Commit/flush structure, as written (`src/world_engine/cockpit/crud.py`, `create_entity`, lines 519–589)

```python
db.add(entity)
# Flush the entity row first: SQLModel's auto insert-order detection gets
# confused for extension tables with multiple FK columns to entity.id
# (e.g. character.current_location_id) and may try to insert the
# extension row before its own entity row.
db.flush()
db.add(ext_row)
db.commit()
db.refresh(entity)
db.refresh(ext_row)

if pending_faction_id:
    write_membership(
        db, mode="open", world_id=entity.world_id, entity_id=entity.id,
        faction_id=pending_faction_id, role=None, is_primary=True, is_secret=False,
    )
    db.commit()
```

So: **one `db.flush()` seam** (entity row only, before the extension row is
even added — purely to fix SQLModel's insert-order guess) and **two
`db.commit()` calls** for a character with a `faction_id` in its payload (one
for entity+extension, one for the faction-membership leg); **one
`db.commit()`** for every other entity type (no second leg).

The helpers `create_entity` calls into:
- `_apply_base_fields` (crud.py:423–428) and `_build_extension_kwargs`
  (crud.py:431–436) — pure Python, only call `_coerce_field`/`_validate_entity_ref`
  (raise `HTTPException` on bad input, never touch `db.commit()`/`db.flush()`).
- `write_membership` (`writes.py:353–422`) — docstring: *"Caller adds the row
  to the session."* It calls `db.add(membership)` and returns; **no commit, no
  flush** inside it. The same is true of `write_relation` (writes.py:129–244)
  and `write_knowledge` (writes.py:247–310) — every `writes.py` helper follows
  this convention. The `db.commit()` lines above belong to `create_entity`
  itself, not to any shared helper.

### Does `create_entity` accept an externally-provided `Session`, or own its own?

It accepts an injected `Session` via `db: DbSession = Depends(get_session)`
(`get_session` in `db.py:63–66` is a generator that does `with Session(engine)
as session: yield session` — a fresh session per FastAPI request). Because
`Depends(...)` is just a default value, **nothing stops a Python caller from
calling `create_entity(body, db=my_session)` directly**, passing in a session
it owns (this is exactly how a non-HTTP commit loop would have to invoke it).
But that does not help: the `db.commit()` calls are **hard-coded inside the
function body**, unconditionally. A caller cannot defer them — every call to
`create_entity` (and equally, `create_knowledge` at crud.py:722–744, and
`open_entity_membership` at crud.py:~833–873, both of which also end in their
own hard-coded `db.commit()`) commits whatever is pending on that session at
that point, including anything the caller had already `db.add()`-ed earlier
and not yet committed.

### Atomicity verdict

**No** — a batch of N entity creates (+ their knowledge/membership legs)
cannot be wrapped in one rollback-on-any-failure transaction without changing
`create_entity`'s own commit boundary, even if every call in the batch shares
one externally-supplied `Session`. Each `create_entity` call (and each
`create_knowledge` / `open_entity_membership` call) commits internally; a
failure on entity K does not roll back entities 1..K-1, which are already
durably committed by the time K runs.

**What would have to change, and what it would touch:** `create_entity`
(and `create_knowledge`, `open_entity_membership`) would need their
`db.commit()` / `db.refresh()` calls removed from the core write logic, with
the commit moved to whoever owns the request/batch boundary instead. Two
ways to do this, both real refactors:
- Split each into a commit-free "core" function plus a thin route wrapper
  that calls `db.commit()` + `db.refresh()` after — touches three call sites
  (`POST /api/entities`, `POST /api/entities/{id}/knowledge`,
  `POST /api/entities/{id}/memberships`) and their response-shaping code,
  which currently assumes the row is committed/refreshed by the time it
  builds the JSON response (`_entity_dict(entity)` after `db.refresh(entity)`,
  etc.).
- Or add a `commit: bool = True` parameter threaded through all three, with
  the existing single-entity creator-CRUD UI (the cockpit's "Ajouter" forms)
  passing the default (commit immediately, current behaviour preserved) and
  a future batch-commit caller passing `commit=False` — same blast radius
  (three functions, three route handlers, anything that reads `entity.id`
  immediately after a create call and currently relies on it being already
  flushed/committed — though `db.flush()` alone, which is already happening
  for the entity row, is enough for `entity.id` to be usable by a same-
  transaction follow-up write without a full commit).

Either way the risk is legible and narrow: exactly the three direct-write
functions above, and their three route call sites — no analyzer, no
`_apply_mutation`, no gathering code is touched. The single-entity creator
CRUD path (the existing "Ajouter un PNJ/lieu/faction" forms) would need its
behaviour preserved exactly (still one visible commit per click), which both
options above do.

---

## 2. NPC location / presence representation + mutable path (D1)

### Authoritative representation

`Character.current_location_id` (`models.py:109–111`, indexed at
`models.py:102`, `Index("idx_character_location", "current_location_id")`):

```python
current_location_id: Optional[str] = Field(default=None, foreign_key="entity.id")
```

This is the column every live reader actually queries:
- `gathering.py:_present_npcs` (lines 56–72): `Character.current_location_id
  == location_id` — this IS the query that decides which NPCs are "at" a
  location when gatherings are (re)generated.
- `context.py:254`: `select(Character).where(Character.current_location_id ==
  location_id)`.

No `located_at`/`present_at` relation type exists in `RELATION_TYPES`
(`crud.py:107–111`: `ally, enemy, debt, fear, fascination, shared_secret,
instrumentalizes, interest, indifference, rejection, passive_attention,
other, connects_to, controls`) — location is not modelled as a `relation`
row. The `gathering`/`gathering_member` tables are downstream and
session-ephemeral (formed/dissolved by `generate_gatherings`/
`enter_location`, "not a canon mutation" per `gathering.py`'s module
docstring) — they cluster NPCs already filtered by `current_location_id`,
they do not define where an NPC is. **`current_location_id` is the sole
authoritative source.**

### The mutable path

`current_location_id` is a plain registry field on the `character` entity
type (`crud.py:149`):

```python
{"name": "current_location_id", "label": "Current location", "kind": "entity_ref", "ref_type": "location"},
```

— validated generically by `_validate_entity_ref(db, value, "location",
label)` (crud.py:251–257), which only checks `target.type == ref_type`
(it does **not** check `target.status == "active"` — see Findings below).
Because it is a normal registry field, it is written through the **same
composite endpoints as every other character field**: `POST /api/entities`
at creation (the extension payload's `current_location_id` flows straight
through `_build_extension_kwargs`, no special-casing — unlike `faction_id`,
which had to be pulled out of the extension dict because it is *not* a
`character` column any more), or `PUT /api/entities/{id}` to relocate an
existing character. Minimal write to relocate an existing NPC: `PUT
/api/entities/{npc_entity_id}` with `{"entity": {...}, "extension":
{"current_location_id": "<location_entity_id>", ...other required fields...}}`
— `update_entity` (crud.py:592–629) re-validates the ref, sets it via
`_build_extension_kwargs`, and commits once.

A second, player-only mechanism exists for the same underlying write:
`_perform_travel` (`cockpit/app.py:3416–3484`) — closes the player's open
conversation/gathering rows, then `char.current_location_id = location_id;
db.add(char); db.commit()` (line 3480–3483). This is **not** reusable
as-is for an NPC commit (it is keyed to `player_id` semantics — closing the
*player's* conversations/gathering rows — and it validates `dest.status ==
"active"`, stricter than `_validate_entity_ref`), but it confirms the
underlying column write is the same scalar assignment.

### Verdict

**Mutable, not a hard FK-as-permanent-default.** `current_location_id` is an
ordinary nullable foreign key column, editable through the normal composite
entity write path with no `proposed_mutation` checkpoint (creator-direct,
like everything else in `crud.py`). The **minimal write to place an NPC** at
a location through the normal mutable mechanism is: `extension.
current_location_id = <location entity id>` in either the creating `POST
/api/entities` payload or a follow-up `PUT /api/entities/{npc_id}` — both go
through `_validate_entity_ref` and a single `db.commit()`.

### Are new NPCs placed at creation today?

**No current flow sets it.** `entity_author.py`'s character draft fields
(`public`: `name, description, appearance, backstory, aversion,
physical_tier, faction_id`; `secret`: `knowledge, creator_meta, shared_with`
— confirmed by grep, no `current_location_id` / `location_local_id`
anywhere in the file) never proposes a location. `region_author.py` tracks a
`location_local_id` per NPC at the manifest-resolution stage (line 327,
`loc_local = location_local_id.get(location_name)`) but only as a
**draft-local pointer carried in the returned JSON tree** — `region_author`
writes no canon at all (module docstring, reconfirmed: "writes no canon,
ever"), so this pointer never reaches a `current_location_id` column today.
**New NPCs are placeless until something moves them** — `current_location_id`
defaults to `None` (models.py:109, `default=None`) and stays that way unless
a `POST`/`PUT` extension payload sets it explicitly.

---

## 3. Full NPC draft→commit sequence

For one NPC, in dependency order, using the existing helpers/endpoints
unchanged:

1. **`POST /api/entities`** (`create_entity`, crud.py:519) —
   `{"entity": {"type": "character", "name": "...", ...}, "extension":
   {"character_type": "npc", "current_location_id": "<location id>", ...,
   "faction_id": "<faction id or omitted>"}}`.
   - If `extension.faction_id` is present, `create_entity` pulls it out as
     `pending_faction_id` (crud.py:545–551) and validates the target is a
     `faction` entity **before** committing the character row — so the
     *faction entity must already exist* (hard ordering constraint #1).
   - `current_location_id`, by contrast, needs no special pulling-out: it is
     a normal `character` column, so it can be set **in this same call** if
     the host location already exists (ordering constraint #2, shared with
     the faction case) — no separate placement step is structurally required
     for a freshly-created NPC, only for relocating an existing one.
   - Commits: one (entity + character row), plus a second if
     `pending_faction_id` was set (the `write_membership` leg, item 5 below
     — already covered by this single call when a primary faction is known
     at creation time).

2. **`POST /api/entities/{npc_id}/knowledge`** (`create_knowledge`,
   crud.py:722–744), once per `pendingDraftKnowledge` item — `{"subject":
   "...", "level": "...", "content": "...", "is_secret": true, ...}`. Calls
   `write_knowledge(db, entity_id=npc_id, ...)` then its own `db.commit()`.
   Hard ordering constraint: the NPC entity must already exist (`npc_id`
   known) — satisfied by step 1 having already committed.

3. **`write_membership(mode="open", is_primary=True, is_secret=False)`**
   for the primary public affiliation — **either** already executed as
   step 1's internal `pending_faction_id` leg (if `faction_id` rode in the
   original `POST /api/entities` extension payload), **or**, if chantier 2
   chooses to drive this explicitly itself (e.g. because the faction id is
   only resolved after the NPC row exists), the equivalent direct call:
   `write_membership(db, mode="open", world_id=npc.world_id,
   entity_id=npc_id, faction_id=faction_entity_id, role=None,
   is_primary=True, is_secret=False)` followed by `db.commit()` — there is no
   dedicated single-purpose endpoint distinct from `POST
   /api/entities/{entity_id}/memberships` → `open_entity_membership`
   (crud.py:~833–873), which does exactly this and additionally guards the
   partial-unique-index conflict with a `try/except IntegrityError` →
   `db.rollback()` → `409`. Hard ordering constraint: the faction entity
   must already exist — same constraint as step 1.

4. **Placement** (pending item 2) — **already satisfied by step 1** if
   `current_location_id` rode in the creating payload. If placement happens
   after the fact (e.g. the host location wasn't resolved yet when the NPC
   was drafted), the write is `PUT /api/entities/{npc_id}` with
   `extension.current_location_id = <location id>` (item 2's minimal write).
   Hard ordering constraint: the host location entity must already exist —
   matches `region_author.py`'s actual pipeline order (Stage 1 Factions →
   Stage 2 Locations, root first → Stage 3 NPCs), so by the time chantier 2
   reaches the NPC stage, both the faction and the location it needs are
   already committed.

Net: for a region commit walking factions → locations → NPCs in that order
(the same order `region_author.generate_region_draft` already produces), an
NPC's full commit can collapse to **one `POST /api/entities` call carrying
`current_location_id` and `faction_id` in the same extension payload**
(two commits internally) **plus one `POST .../knowledge` call per knowledge
item** (one commit each) — no separate placement call needed for a brand-new
NPC, only for relocating an already-committed one.

---

## 4. Read-only suggestion surface reuse

Confirmed reusable as-is. The pattern lives in `cockpit/index.html`:
`pendingDraftNotes` (a plain JS array) + `authorRenderGenNotes(notes)` (the
renderer) — already used today for exactly this purpose on two entity
types:
- Location: `authorApplyLocationDraft` pushes one note per
  `draft.secret.sensed_links` entry (`Lien perçu (${link.kind}) :
  ${link.name}...`) and one for `draft.secret.subculture_hidden`, then calls
  `pendingDraftNotes = notes; authorRenderGenNotes(notes);`.
- Character: the equivalent `authorApplyCharacterDraft` renders
  `draft.secret.shared_with` into the same notes block.

Both are confirmed (prior RECON item 2/6) to be **display-only**: `notes`
text is never read back out of the DOM by `authorSave()`, which only posts
registry-driven form fields (`entityData`/`extData`) plus, for new
characters, `pendingDraftKnowledge` through the real knowledge endpoint.
No id resolution happens on this text anywhere.

For region review, the same shape generalizes directly: location
`sensed_links` → `connects_to`/`controls` candidates, NPC `shared_with`,
and any secret-membership hint are all already free-text/structured notes
sitting in the region draft tree (`region_author.py`'s per-entity `result`
objects, which are exactly each entity's `generate_entity_draft` return
value — same `draft.secret.*` shape item 1 of the prior RECON catalogued).
Rendering them with `authorRenderGenNotes` (or a near-identical clone scoped
to the region view) requires no change to the function or its contract —
just feeding it a notes array built the same way `authorApplyLocationDraft`/
`authorApplyCharacterDraft` already build theirs, once per drafted entity in
the region tree. Nothing here is built by this RECON.

---

## 5. Skeleton-wire targets at commit

Re-confirmed unchanged from prior RECON item 7, against the live tree read
in this step:

- **`parent_location_id`**: a generic registry field
  (`crud.py:164`, `{"name": "parent_location_id", "label": "Parent
  location", "kind": "entity_ref", "ref_type": "location"}`), set via the
  same composite `POST /api/entities` / `PUT /api/entities/{id}` used for
  every other location field, validated by `_validate_entity_ref(db, value,
  "location", label)`. Minimal payload: the location's id (path/payload) +
  `extension.parent_location_id = <parent location id>` in the same
  `EntityWriteBody`. No dedicated endpoint exists or is needed.

- **Primary public `faction_membership`**: `write_membership(mode="open",
  is_primary=True, is_secret=False)` (writes.py:353), reached either through
  `create_entity`'s `pending_faction_id` leg (crud.py:570–583, for a
  brand-new character) or through `POST /api/entities/{entity_id}/
  memberships` → `open_entity_membership` (crud.py, confirmed at the
  `try: db.commit() except IntegrityError: db.rollback(); raise
  HTTPException(409, ...)` block read in this step). Minimal payload:
  `world_id`, `entity_id`, `faction_id` (`role=None`, `cover_role=None`,
  `is_secret=False` all default).

Both confirmed unchanged since the prior RECON pass — same line ranges,
same code.

---

## 6. Partial-state recovery (informs E)

**Greenfield — no existing mechanism.** Searched the codebase for
idempotency keys, draft-entity flags, and cleanup scripts:

- `Entity.status` (`crud.py:85`, `ENTITY_STATUSES = ("active", "inactive",
  "destroyed", "missing")`) has **no `"draft"` value** — an entity created
  by a future chantier-2 commit is immediately `"active"`, indistinguishable
  from any hand-authored entity, the moment its row commits.
- No idempotency key column or parameter exists on `create_entity` /
  `create_knowledge` / `open_entity_membership` — calling any of them twice
  with the same logical input creates a second row every time (entities get
  a fresh `_uuid()` id; `create_knowledge` has no dedup; `open_entity_
  membership` only collides on the *unrelated* partial-unique indexes
  guarding one-active-primary / no-duplicate-active-membership, which is a
  data-integrity guard, not a resume mechanism).
- Every "idempotent" hit in the codebase (`grep -i idempot`) belongs to a
  different concern: `migrate_npc`'s already-in-target-gathering guard
  (gathering.py:268,277), gathering re-join no-ops (app.py:809),
  `write_membership(mode="close")`'s already-closed no-op (writes.py:386),
  the front-end's safe-to-re-enter-on-F5 scene load (index.html:1260–1264),
  and the analyzer's idempotent-fact dedup for `new_knowledge`/
  `status_change` (analyzer.py:644–649) — none of these touch entity
  creation.
- No cleanup script exists for half-written entity sets (only migration
  scripts: `migrate_v1_24.py`, `migrate_v1_26.py`, `migrate_v1_30.py`,
  `migrate_v1_31_ledger.py` — all schema migrations, not data cleanup).
- The only `db.rollback()` call anywhere in `crud.py` is the
  `IntegrityError` catch in `open_entity_membership`, which rolls back a
  single failed membership-open and re-raises a `409` — it does not undo any
  earlier entity/knowledge writes in a batch.

This confirms the scope of risk for decision E: a best-effort chantier-2
commit that fails partway through leaves whatever was already committed
(entities, knowledge, memberships, location placements) sitting in canon as
ordinary active rows, with **no structural marker** distinguishing them as
"part of an incomplete region commit" — recovery (resume, dedupe, or manual
cleanup) would have to be designed from scratch, not adapted from an
existing mechanism.

---

## Findings / risks (passing observations, report-only)

- **`_validate_entity_ref` does not check `entity.status`.** Setting
  `current_location_id` or `parent_location_id` to an `inactive`/`destroyed`
  location succeeds silently — only `target.type != ref_type` is checked
  (crud.py:251–257). This is inconsistent with `_perform_travel`, which
  explicitly requires `dest.status == "active"` (app.py:3433) for the
  player-travel path. Not a chantier-2 blocker (region commits place NPCs in
  freshly-created, necessarily-active locations) but worth knowing: nothing
  stops a future caller from "placing" an NPC at a soft-deleted location
  through the generic composite write.
- **`create_entity`'s two-commit shape for a character with a faction is
  already a tiny pre-existing atomicity gap**, independent of chantier 2: if
  the process crashes between the two `db.commit()` calls at crud.py:566 and
  crud.py:583, today's creator-CRUD UI can already produce a character with
  no primary faction membership despite the form having submitted one. This
  is the same gap item 1 describes at batch scale, just visible today at
  single-entity scale.
- **`create_knowledge` commits per row** (crud.py:742) — for an NPC with N
  knowledge items, that's N separate commits already, even outside any
  chantier-2 batching concern.

---

## Summary verdicts

- **Item 1 (atomicity):** **No** — batch-in-one-transaction is not
  achievable without touching `create_entity`'s (and `create_knowledge`'s,
  `open_entity_membership`'s) hard-coded commit boundary. The shared
  `writes.py` helpers (`write_relation`, `write_knowledge`, `write_membership`)
  already never commit — the commits live in the three route-adjacent
  functions, costing a refactor of those three functions and their three
  HTTP route call sites (commit-free core + committing wrapper, or a
  `commit:` flag), with the existing single-entity creator-CRUD UI required
  to keep its current one-commit-per-click behaviour.
- **Item 2 (NPC placement):** `Character.current_location_id` is the sole
  authoritative representation; it is a **mutable**, ordinary foreign-key
  column reachable through the normal composite `POST`/`PUT
  /api/entities[/{id}]` write (no `proposed_mutation`, no rigid binding).
  Minimal placement write: `extension.current_location_id = <location id>`.
  **New NPCs are placeless today** — no current author/CRUD/region flow sets
  it at creation; it can be set in the same creating payload, but nothing
  does so yet.

This step writes no canon and touches no engine code; no `/review-step` /
`/close-step` was run.
