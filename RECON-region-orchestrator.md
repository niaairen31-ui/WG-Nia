# RECON — Region orchestrator contracts

**Status: report-only.** No code, no canon, no schema, no template was
modified to produce this document. `git status` after this step shows
exactly one added file (this one) and no change to any `.py`, template, or
schema file. No `/review-step` / `/close-step` was run — there is no engine
code change to review or close.

**Path note:** no `HANDOVER-*` artifact exists anywhere in this repository
or on disk (`find / -iname "HANDOVER*"` returned nothing). This file is
placed at the project root, alongside `ARCHITECTURE_DECISIONS.md` and
`CLAUDE.md`, in lieu of a `HANDOVER-*` precedent that does not exist yet.

Scope and item numbering follow `BRIEF-recon-region-orchestrator.md`.

---

## 1. Atomic generator entry point

File: `src/world_engine/entity_author.py`.

### Signature

```python
def generate_entity_draft(entity_type: str, brief: str, db: Session) -> dict:
```

No defaults on any parameter — all three are required positional/keyword
params. `entity_type` is validated against the keys of `_TYPE_FIELDS`:

```python
_TYPE_FIELDS: dict[str, str] = {
    "character": (...),
    "location": (...),
    "faction": (...),
}
```

So the accepted `type` values today are exactly `"character"`, `"location"`,
`"faction"` — `item`/`artifact` are not populated (module docstring: "adding
one of those later is a config entry here, not new code").

### Return shape

Failure (never raises — "Never raises into the caller"):

```python
{"ok": False, "error": "<reason>"}
```

Success:

```python
{"ok": True, "draft": {"public": {...}, "secret": {...}}, "notes": [...]}
```

Top-level keys: `ok`, `draft`, `notes` on success; `ok`, `error` on failure.
`draft` always has exactly two second-level keys, `public` and `secret`.

### Per-type `public` / `secret` keys, as the parser actually emits them

**`character`** (lines 379–394):
- `public`: `name`, `description`, `appearance`, `backstory`, `aversion`,
  `physical_tier` (int, clamped -1..2 via `_clamp_physical_tier`),
  `faction_id` (resolved id or `None` — see item 5).
- `secret`: `knowledge` (list of `{subject, level, content, is_secret: True}`
  via `_normalize_knowledge`), `creator_meta` (string or `None`),
  `shared_with` (list of `{with, note}` via `_normalize_shared_with`).

**`location`** (lines 331–348):
- `public`: `name`, `description`, `location_type` (validated against
  `_LOCATION_TYPES`, default `"other"`), `access_level` (validated against
  `_ACCESS_LEVELS`, `None` on a miss), `subculture` (dict, filtered to
  `_SAFE_SUBCULTURE_KEYS` via `_filter_subculture_public`).
- `secret`: `subculture_hidden` (string), `sensed_links` (list of
  `{kind, name, note}` via `_normalize_sensed_links`).

**`faction`** (lines 351–368):
- `public`: `name`, `description`, `faction_type` (validated against
  `_FACTION_TYPES`, default `"other"`), `philosophy`, `internal_structure`,
  `roles` (ordered list of `{name, description}` via `_normalize_roles`),
  `aversion`.
- `secret`: `internal_tensions`, `goals`.

---

## 2. Display-only link channels

- **Location**: `draft.secret.sensed_links` — list of `{kind, name, note}`,
  `kind` one of `parent|connection|faction|other` (`_normalize_sensed_links`
  forces unknown kinds to `"other"`). Docstring, verbatim: *"Display-only
  notes (D1) — never resolved, never written anywhere."*
- **Character (NPC)**: `draft.secret.shared_with` — list of `{with, note}`
  (`_normalize_shared_with`). Docstring, verbatim: *"Display-only notes
  (decision G1) — never written anywhere."*
- **Faction**: no equivalent channel exists. `_TYPE_FIELDS["faction"]` has no
  `sensed_links`/`shared_with`-shaped field; the faction draft's only secret
  keys are `internal_tensions` and `goals` (free prose, not link-shaped).

Confirmed from the cockpit consumer side (`index.html`): both
`authorApplyCharacterDraft` and `authorApplyLocationDraft` render
`shared_with` / `sensed_links` only into the read-only "Notes de l'assistant"
block (`pendingDraftNotes` / `authorRenderGenNotes`) — never into a form
field that flows to a write. `authorSave` posts only `entityData` /
`extData` (registry-driven form fields) plus, for new characters,
`pendingDraftKnowledge` through the existing knowledge endpoint — `notes`
text is never read back out of the DOM into any payload. No id resolution
happens anywhere in `entity_author.py` for these two fields (no `Entity`
lookup is performed on `sensed_links` or `shared_with` content, unlike
`faction_name`'s dedicated `_resolve_faction_id`).

---

## 3. `_TYPE_FIELDS` and template rendering

### `_TYPE_FIELDS` current contents

Three keys: `"character"`, `"location"`, `"faction"` (quoted in full in item
1's field lists above; `item`/`artifact` absent). Each value is a single
French-language guidance string describing every `public.*`/`secret.*` field
name and its expected shape, interpolated into the template as
`{type_fields}`.

### `user_template` assembly

`generate_entity_draft` formats the stored template:

```python
user_message = template.user_template.format(
    entity_type=entity_type,
    type_fields=_TYPE_FIELDS[entity_type],
    brief=brief,
)
```

So the template consumes exactly three variables: `{entity_type}`,
`{type_fields}`, `{brief}`. `system_prompt` is passed verbatim, never
`.format()`'d (per its own seed comment: "system_prompt is passed verbatim
(NOT .format()'d, so it carries no variables itself)").

`prompt_template.variables` for `usage='entity_generation'`
(`scripts/seed_pilot.py`, `upsert_prompt_template("pt-entity-generation", ...)`):

```python
variables=["entity_type", "type_fields", "brief"],
```

— matches the template's actual `.format()` call exactly.

### Template body (`ENTITY_GENERATION_USER_TEMPLATE`, `scripts/seed_pilot.py`)

```
Type d'entité : {entity_type}

Champs attendus :
{type_fields}

Intention du créateur : {brief}

Brouillon JSON :
```

### F1 feasibility verdict

**Yes** — extra free context (a region concept brief, or compact peer-entity
summaries) can be injected through the existing template **without adding a
new template or a new `usage`**.

Insertion point: `{brief}` is the only free-text slot, and it is plain
`str.format()` substitution with no length or shape constraint on the
*caller's* side — `generate_entity_draft`'s `brief` parameter is just any
non-empty string passed straight to `.format(brief=brief)`. The orchestrator
can build a composite `brief` string at call time —
e.g. `f"{region_concept}\n\n--- Peer entities already drafted in this stage ---\n{peer_summary}\n\n--- This entity's brief ---\n{entity_brief}"`
— and pass that single composite string as `brief`. No change to
`entity_author.py`, `_TYPE_FIELDS`, the template row, or `variables` is
required; the orchestrator does 100% of the composition before calling
`generate_entity_draft`. The only soft constraint is the model's context
window (not enforced by any code path inspected here).

---

## 4. Per-type parser guards

**Common to all generation, in `generate_entity_draft` itself:**
- `entity_type not in _TYPE_FIELDS` → `{"ok": False, "error": ...}`.
- `brief` empty/whitespace → `{"ok": False, "error": "brief must not be empty"}`.
- No active `pt-entity-generation` template → `{"ok": False, "error": "No active pt-entity-generation template found"}`.
- Template `.format()` raising `KeyError`/`IndexError` → caught, returned as error.
- `OllamaError` from `chat()` → caught, returned as error.
- Non-JSON / malformed JSON output → `{"ok": False, "error": "Model returned non-JSON output"}` or `"...empty or malformed draft"`.
- `parsed.get("public")` / `.get("secret")` coerced to `{}` if not a dict
  (`public_in = public_in if isinstance(public_in, dict) else {}`).

**`character`:**
- `_clamp_physical_tier`: `max(-1, min(2, int(raw)))`, falls back to `0` on
  `TypeError`/`ValueError`.
- `_normalize_knowledge`: drops non-dict rows; drops rows missing `subject`
  or `content` (appends a note); `level` not in `KNOWLEDGE_LEVELS` (imported
  from `writes.py`) or equal to `"unaware"` falls back to `"rumor"`;
  `is_secret` is forced `True` in code, never read from the model.
- `_normalize_shared_with`: drops non-dict rows and rows without a truthy
  `with`.
- Faction resolution: see item 5.

**`location`:**
- `_validate_location_type`: must be in `_LOCATION_TYPES = ("city",
  "district", "building", "natural", "underground", "other")`; else falls
  back to `"other"` with a note.
- `_validate_access_level`: must be in `_ACCESS_LEVELS = ("public",
  "restricted", "secret")`; else **left `None`** with a note ("laissé vide
  pour le créateur" — never defaulted permissive).
- `_filter_subculture_public`: only keys in the *live*
  `_SAFE_SUBCULTURE_KEYS` import from `context.py`
  (`("values", "magic_phenomena", "nexus_link")`) survive into
  `public.subculture`; any other key (notably `"hidden"`) is dropped with a
  note. `"hidden"` can only ever reach the draft via
  `secret.subculture_hidden`, a structurally separate field.
- `_normalize_sensed_links`: drops non-dict rows, rows without `name`; `kind`
  not in `("parent", "connection", "faction", "other")` falls back to
  `"other"`.

**`faction`:**
- `_validate_faction_type`: must be in `_FACTION_TYPES = ("government",
  "criminal", "military", "esoteric", "other")`; else falls back to
  `"other"` with a note.
- `_normalize_roles`: drops non-dict rows; drops rows where `name` is missing
  or blank (note: "Rôle proposé sans nom — ignoré"); order preserved
  (array order = rank); `description` coerced to `""` if not a string.
- **Never-proposed fields, confirmed absent from `_TYPE_FIELDS["faction"]`
  and from the `draft` construction in `generate_entity_draft`:**
  `magic_knowledge_level`, `scope`, `parent_faction_id`. None of the three
  appears anywhere in `entity_author.py`; they exist only as
  `ENTITY_TYPE_REGISTRY["faction"]["fields"]` entries in `crud.py` (creator
  CRUD form fields), confirmed dormant by their own field-spec comment in
  `crud.py`: *"DORMANT trio (BRIEF-26, schema v1.38): stored and
  creator-editable, read by no assembler or guard."*

---

## 5. NPC → faction affiliation today

### Draft proposal

`_TYPE_FIELDS["character"]` asks the model for
`public.faction_name (string ou null — nom exact d'une faction existante, ou
null si aucune)` — the model proposes an affiliation **by name**, not by id.

### Resolution

`_resolve_faction_id(db, world_id, faction_name)` (lines 108–126):

```python
def _resolve_faction_id(
    db: Session, world_id: str | None, faction_name: Any
) -> tuple[str | None, str | None]:
    if not faction_name or not isinstance(faction_name, str):
        return None, None
    stmt = select(Entity).where(Entity.type == "faction")
    if world_id is not None:
        stmt = stmt.where(Entity.world_id == world_id)
    target = faction_name.strip().lower()
    for candidate in db.exec(stmt).all():
        if (candidate.name or "").strip().lower() == target:
            return candidate.id, None
    return None, f"Faction '{faction_name}' introuvable — champ laissé vide"
```

Matching rule: **case-insensitive, whitespace-stripped exact match**
(`.strip().lower() == .strip().lower()`) against `entity.name` for every
`Entity` with `type == "faction"`, scoped to the current world if one
exists. No fuzzy matching, no `internal_name` fallback. A miss leaves
`faction_id` `None` and appends an "introuvable" note — **never auto-creates
a faction** (Scope OUT, confirmed in code).

### Commit-time write target

`cockpit/crud.py`, `create_entity` (`POST /api/entities`), lines 539–583.
The composite entity payload's `body.extension["faction_id"]` (set from
`draft.public.faction_id` by the cockpit form) is pulled out as
`pending_faction_id` **before** `_build_extension_kwargs` runs — the
comment is explicit: *"`faction_id` on a character payload is no longer a
`character` column (BRIEF-28, schema v1.40): it is not in the registry's
`fields`."* After the entity + `character` row commit, if
`pending_faction_id` is set:

```python
write_membership(
    db,
    mode="open",
    world_id=entity.world_id,
    entity_id=entity.id,
    faction_id=pending_faction_id,
    role=None,
    is_primary=True,
    is_secret=False,
)
db.commit()
```

So the commit sets **only `faction_membership`** (`is_primary=True`,
`role=None`, `is_secret=False`) — never a legacy `character.faction_id`.

### Verdict: has the membership migration landed?

**Yes, fully landed.** `models.py`'s `Character` class (lines 99–122) has no
`faction_id` column at all. `world-engine-schema.md`'s changelog, v1.40:
*"Drop `character.faction_id` (BRIEF-28)... `scripts/seed_pilot.py`'s five
`faction_id=` kwargs replaced by a... migration
`scripts/migrate_v1_40_drop_character_faction_id.py`... pre-checks that
every historical non-NULL `character.faction_id` has a matching
`is_primary=TRUE` `faction_membership` row"* — i.e. the migration both
backfilled `faction_membership` from the legacy column and then dropped the
column. `entity_author.py`'s `faction_id` key in the character draft is a
**transient pre-fill value only** (it never names a DB column on
`character`); it flows exclusively into the `write_membership(mode="open")`
call shown above. Today's affiliation write path is `faction_membership`
only, full stop.

---

## 6. Draft → canon commit path (location, representative type)

### Cockpit pre-fill

`index.html`, `authorApplyLocationDraft(result)` (lines 3311–3333):

```js
setVal('author-f-name', draft.public.name);
setVal('author-f-description', draft.public.description);
setVal('author-x-location_type', draft.public.location_type);
setVal('author-x-access_level', draft.public.access_level || '');

const subcultureFull = { ...(draft.public.subculture || {}) };
if (draft.secret.subculture_hidden) subcultureFull.hidden = draft.secret.subculture_hidden;
setVal('author-x-subculture', Object.keys(subcultureFull).length ? JSON.stringify(subcultureFull, null, 2) : '');

const notes = [...(result.notes || [])];
for (const link of (draft.secret.sensed_links || [])) {
  notes.push(`Lien perçu (${link.kind}) : ${link.name}${link.note ? ' — ' + link.note : ''}`);
}
if (draft.secret.subculture_hidden) {
  notes.push(`Subculture cachée proposée : ${draft.secret.subculture_hidden}`);
}
pendingDraftNotes = notes;
authorRenderGenNotes(notes);
```

### Public vs secret → author form mapping

- `draft.public.name` → entity base field `author-f-name`.
- `draft.public.description` → entity base field `author-f-description`.
- `draft.public.location_type` → extension field `author-x-location_type`.
- `draft.public.access_level` → extension field `author-x-access_level`.
- `draft.public.subculture` **merged with** `draft.secret.subculture_hidden`
  (under key `"hidden"`) → the single `author-x-subculture` JSON textarea.
  This is the B1 merge point, explicitly called out in the surrounding
  comment: *"the merge of allow-listed public subculture keys + the secret
  'hidden' key happens HERE, in code, from the two segregated draft fields...
  never from a single field the model controls directly."*
- `draft.secret.sensed_links` → rendered into the **read-only**
  `pendingDraftNotes` block only (`authorRenderGenNotes`); never written to
  any form field.
- `magic_status` and `coordinates` are never touched (stay at form
  defaults) — confirmed absent from `authorApplyLocationDraft`.

### Accept → CRUD endpoint

`authorSave()` (`index.html`, lines 3997 onward) reads every registered
field (`authorRegistry.entity_base_fields` + `authorRegistry.types[type].fields`,
which mirror `ENTITY_BASE_FIELDS` + `ENTITY_TYPE_REGISTRY["location"]["fields"]`
served by the backend) into `entityData` / `extData`, then:

```js
let detail = isNew
  ? await api('/api/entities', { method: 'POST', ... body: JSON.stringify({ entity: entityData, extension: extData }) })
  : await api(`/api/entities/${authorEntityId}`, { method: 'PUT', ... });
```

For a new location this is `POST /api/entities` → `crud.py`'s
`create_entity` (lines 519–589): constructs an `Entity(type="location", ...)`,
calls `_apply_base_fields` then `_build_extension_kwargs` (generic,
registry-driven coercion — no location-specific code), builds the `Location`
extension row, `db.add`/`db.flush`/`db.add`/`db.commit`. No `writes.py`
helper is involved for a location create (unlike the character path, which
additionally calls `write_membership` for the faction leg — item 5). This is
a direct write with **no `proposed_mutation` checkpoint** — `crud.py`'s own
module docstring: *"a second canonical write path... deliberately a direct
write with no `proposed_mutation` checkpoint."*

`sensed_links` is never POSTed anywhere — it dies in `pendingDraftNotes`,
confirming item 2's "never written to canon" for locations end-to-end, not
just inside `entity_author.py`.

---

## 7. Link-write vocabulary for A3

### `parent_location_id`

Generic registry field, not a dedicated endpoint:
`ENTITY_TYPE_REGISTRY["location"]["fields"]` includes
`{"name": "parent_location_id", "label": "Parent location", "kind":
"entity_ref", "ref_type": "location"}` (`crud.py` line 164). It is set via
the same composite `POST /api/entities` (create) or `PUT
/api/entities/{id}` (update) used for every other location field, validated
generically by `_validate_entity_ref(db, value, "location", label)` (must
resolve to an `Entity` with `type == "location"`). Minimal field set: the
location's `entity_id` (path/payload) + `extension.parent_location_id`
(the target location's id) in the same `EntityWriteBody`.

### `connects_to` adjacency

Relation-write path: `POST /api/entities/{entity_id}/relations` →
`create_relation` (`crud.py`, lines 653–677) → `writes.write_relation(db,
mode="set", world_id=..., entity_a_id=entity_id, entity_b_id=other_entity_id,
type=..., value=..., direction=..., visible_to_b=..., notes=...)`. The
cockpit's click-to-connect graph UI calls this with:

```js
body: JSON.stringify({ other_entity_id: B, type: 'connects_to' })
```

(`index.html` line 4553) — `intensity` and `direction` are omitted, so
`RelationWriteBody`'s field defaults apply: `intensity=None` →
`create_relation` substitutes `50` (`body.intensity if body.intensity is not
None else 50`); `direction=None` → `create_relation` substitutes `"mutual"`
(`body.direction or "mutual"`). Confirmed row convention for `connects_to`:
`type="connects_to"`, `direction="mutual"`, `intensity=50` — and per
`crud.py`'s own comment, *"the intensity is a structural default with NO
meaning"* (CLAUDE.md invariant, item unchanged). Minimal field set a caller
must supply: `other_entity_id`, `type="connects_to"` (everything else has a
safe default for this type).

### `faction_membership`

Create path: `POST /api/entities/{entity_id}/memberships` →
`open_entity_membership` (`crud.py`, lines 842–860) → `writes.write_membership(
db, mode="open", world_id=entity.world_id, entity_id=entity_id,
faction_id=body.faction_id, role=body.role, cover_role=body.cover_role,
is_primary=body.is_primary, is_secret=body.is_secret)`. Minimal field set:
`faction_id` (required `MembershipOpenBody` field); `role`, `cover_role`,
`is_primary`, `is_secret` all have defaults (`None`, `None`, `False`,
`False`).

`is_primary` partial unique index, live definition
(`world-engine-schema.md`, also mirrored in `models.py`'s `FactionMembership.__table_args__`):

```sql
CREATE UNIQUE INDEX idx_membership_one_primary
  ON faction_membership(entity_id) WHERE is_primary = TRUE AND left_at IS NULL;
```

— at most one *active* (`left_at IS NULL`) primary membership per
`entity_id`. A second sibling index (also unique, also partial) prevents a
duplicate active membership in the same faction regardless of `is_primary`:

```sql
CREATE UNIQUE INDEX idx_membership_unique_active
  ON faction_membership(entity_id, faction_id) WHERE left_at IS NULL;
```

`is_secret` column: `BOOLEAN`, gates whether `read_public_memberships`
(`context.py`) ever surfaces the row to a prompt — `is_secret = TRUE` rows
are excluded structurally, not instructionally (CLAUDE.md invariant).
`cover_role` column: nullable `TEXT`, the prompt-facing façade role;
`read_public_memberships` resolves `cover_role ?? role` so the true `role`
behind a `cover_role` never reaches any prompt (BRIEF-30, schema v1.41).
Both columns are write-once at `mode="open"` — `write_membership` has no
in-place update of an existing row's `role`/`cover_role`/`is_secret` (only
`mode="close"`, which sets `left_at` and nothing else).

### `controls`

Same relation-write path as `connects_to` — `controls` is one of the values
in `RELATION_TYPES` (`crud.py` line 110), so it goes through the identical
`POST /api/entities/{entity_id}/relations` → `create_relation` →
`write_relation(mode="set", ...)` call. No dedicated endpoint or UI exists
for it today (unlike `connects_to`'s graph click-to-connect) — a caller
would `POST` `{"other_entity_id": <asset_id>, "type": "controls",
"direction": "a_to_b"}` explicitly, since `create_relation`'s default
direction is `"mutual"` and `controls` requires `direction="a_to_b"`
(controller is `entity_a`, asset is `entity_b`) per the row convention
documented in `crud.py`'s `RELATION_TYPES` comment block: *"controls:
controller (faction OR any entity) -> controlled asset (location | item |
artifact | character | other). direction='a_to_b' ... intensity is a
MEANINGLESS structural default (50)."* Minimal field set: `other_entity_id`,
`type="controls"`, **and** an explicit `direction="a_to_b"` (the only one of
the four link kinds where the caller must override a default to get correct
semantics — `connects_to`'s default direction is already correct).

---

## 8. Run-side mechanics that bound a region run

`generate_entity_draft` calls the local model via:

```python
raw = chat(messages, model=AUTHOR_MODEL, format="json")
```

(`entity_author.py` line 308) — `ollama_client.chat()` (non-streaming),
`AUTHOR_MODEL = "llama3.1:8b"` (a module-level constant, decision E1, "a
one-line-change constant" per the module docstring — distinct from the
abliterated game model `huihui_ai/qwen3-abliterated:8b-v2` used for NPC
dialogue). `usage = "entity_generation"` is the only `prompt_template` row
this function ever loads (`_load_template`, filtered on
`PromptTemplate.usage == "entity_generation"` and `is_active == True`).

**Thinking mode:** no `/no_think` is appended to the user message anywhere
in `entity_author.py`, and `chat()` does not accept a thinking toggle — it
always returns `strip_think(content)` (`ollama_client.py` line 132), which
is a no-op if the model never emits a `<think>` block (the author model,
`llama3.1:8b`, is not a Qwen3-family thinking model) and a stripping no-op
otherwise. So: thinking is **left enabled by default** (no explicit
`/no_think`), with `strip_think` as a structural backstop regardless of
whether the model emits a think block — this matches the policy CLAUDE.md
documents for "Conversation analysis," not the "NPC dialogue" `/no_think`
policy.

**Loop precedent:** none. A repo-wide search of `entity_author.py` for
`for ... in range`, `while True`, or any other looping construct around a
model call returns no matches — `generate_entity_draft` is single-shot:
exactly one `chat()` call per invocation, one draft in, one draft out. A
search of `cockpit/app.py`'s ten `ollama_client.chat(...)` /
`ollama_client.chat_stream(...)` call sites (NPC dialogue, MJ narration, MJ
interpretation, MJ arbitration, NPC initiative vote/act, MJ
establishment/speaker selection) likewise shows every one firing **at most
once per `/say` turn** — including NPC initiative, which is explicitly
capped at one NPC per turn ("Cadence E1: at most one NPC per turn"). No
existing code path anywhere in the codebase loops a sequence of model calls
that carry forward accumulating context from call N into call N+1 within a
single triggering action. **A sequential multi-call loop (the
orchestrator's mechanism, F1) has no existing precedent or util to reuse —
it is wholly new** and will need to be written from scratch in the
orchestrator step.

---

## Findings / risks

Report-only — nothing below was acted on (protocol rule 4).

1. **Faction generator has no display-only link channel at all** (item 2).
   `sensed_links`/`shared_with` exist for location/character; the faction
   draft offers no analogous "perceived but unconfirmed" slot (e.g. a
   faction's perceived rivals, or a perceived controlled asset). If the
   orchestrator's A3 wiring wants to harvest faction-side link suggestions
   the same way it harvests location/NPC ones, this is a gap in the atomic
   generator, not something the orchestrator can paper over — worth a
   decision (extend `_TYPE_FIELDS["faction"]`, or accept factions
   contribute no link suggestions in v1 of the orchestrator).

2. **`controls` has no dedicated write surface or default-correct call,
   unlike `connects_to`** (item 7). The only path is the generic
   `create_relation` endpoint with an easy-to-miss explicit
   `direction="a_to_b"` requirement — the default (`"mutual"`) silently
   produces a semantically wrong row for `controls`-typed relations
   (intensity meaningless either way, but direction is load-bearing per the
   schema comment's read convention: "who controls asset X" = the
   `entity_a` side). Any future orchestrator/resolver caller for `controls`
   must remember this; nothing in the code enforces it.

3. **`entity_author.py`'s thinking-mode policy is implicit, not chosen.**
   Every other model-call site in the codebase (CLAUDE.md "Local model
   notes") has an explicit, documented thinking-mode decision per call site.
   `generate_entity_draft`'s lack of `/no_think` appears to be "happens to
   work because `llama3.1:8b` doesn't emit `<think>` blocks," not a
   deliberate choice recorded anywhere. If `AUTHOR_MODEL` is ever swapped to
   a thinking model (the module docstring explicitly anticipates this: "a
   future swap to the abliterated game model is a one-line change to this
   constant"), draft JSON parsing could silently degrade (extra non-JSON
   tokens) since `format="json"` constrains the final output shape but a
   `<think>` preamble could still appear before/inside it depending on
   Ollama's JSON-mode interaction with thinking — not verified here, flagged
   only.

4. **No sequential-generation precedent means F1/C1's "bounded forward
   context" and "sequential-with-peers cohesion" posture (per the brief's
   Context section) will be designed against a blank slate** (item 8) —
   not a defect, just confirmation that chantier 1 is greenfield for this
   mechanism, with no existing loop, retry policy, or partial-failure
   convention to inherit. Worth deciding up front whether a failed
   mid-sequence `generate_entity_draft` call (returns `{"ok": False, ...}`,
   never raises) aborts the whole region run or skips that one entity —
   `entity_author.py` itself is silent on this since it has no caller-loop
   today.

5. **The membership migration is fully landed (item 5) — `character.faction_id`
   no longer exists as a column.** This is good news for the orchestrator
   (only one affiliation-write vocabulary to target, no legacy/dual-write
   ambiguity), but it means any orchestrator-side documentation or mental
   model still referencing "legacy `faction_id`" (as earlier briefs, e.g.
   BRIEF-24, originally did) is stale and should not be load-bearing in the
   orchestrator implementation brief.
