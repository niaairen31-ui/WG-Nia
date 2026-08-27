# WORLD ENGINE — Database Schema

Current schema version: v1.96
Append-only history: world-engine-schema-changelog.md (repo root)

-----

## SCHEMA PRINCIPLES

- **Everything is an entity.** Characters, factions, locations, concepts, magic itself — all take part in the same system of relations and knowledge.
- **Magic is an actor.** It has outgoing relations toward other entities. It chooses; it does not merely undergo.
- **History is sacred.** Nothing is overwritten. Successive states are preserved.
- **Creator control is structural.** Approval checkpoints live in the schema, not only in application logic.
- **One mutation pipeline.** Pass-plays and live conversations both produce proposed mutations; nothing touches world state until the creator approves.

-----

## TABLES

-----

### `world`

The root of everything. Each world is an independent instance of the engine.

```sql
CREATE TABLE world (
  id                    TEXT PRIMARY KEY,
  name                  TEXT NOT NULL,
  description           TEXT,
  magic_status          TEXT DEFAULT 'dormant',
                                       -- dormant | awakening | active | suppressed
  is_active             BOOLEAN NOT NULL DEFAULT FALSE,
                                       -- the single globally-active world (v1.54)
  current_phase         TEXT NOT NULL DEFAULT 'matin'
                          CHECK (current_phase IN ('matin','apres-midi','soir','nuit')),
                                       -- creator-set day-cycle phase (v1.92, TICKET-0074,
                                       -- T-A1). Per-world; advancing it writes only this
                                       -- column -- no tick, no cascade.
  created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at            DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- At most one ACTIVE world across the whole database.
CREATE UNIQUE INDEX idx_world_one_active ON world(is_active) WHERE is_active = TRUE;
```

-----

### `world_law`

Position-ordered fundamental laws (schema v1.78, TICKET-0025, BRIEF-0025-b
— replaces `world.fundamental_laws` JSON). One row per law, in
creation-form order. Curated config, same family as `faction_role`: no
`change_history`. Written ONLY via `writes.write_world_laws`. No editing
UI beyond the create form this phase — editing an existing world's laws
is a future ticket.

```sql
CREATE TABLE world_law (
  id       TEXT PRIMARY KEY,
  world_id TEXT NOT NULL REFERENCES world(id),
  position INTEGER NOT NULL DEFAULT 0,
  text     TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_world_law_position ON world_law(world_id, position);
```

-----

### `entity`

Central table. Anything that can have relations or knowledge is an entity.

```sql
CREATE TABLE entity (
  id            TEXT PRIMARY KEY,
  world_id      TEXT NOT NULL REFERENCES world(id),
  type          TEXT NOT NULL,
                -- character | faction | location | concept | magic | artifact | item | other
  name          TEXT NOT NULL,
  internal_name TEXT,                  -- creator-only name (ex: "The Unnamed")
  description   TEXT,
  is_public     BOOLEAN DEFAULT TRUE,  -- FALSE = existence denied or secret
  status        TEXT DEFAULT 'active', -- active | inactive | destroyed | missing
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

-----

### `character`

Extension of entity for characters (players and NPCs).

```sql
CREATE TABLE character (
  id              TEXT PRIMARY KEY REFERENCES entity(id),
  world_id        TEXT NOT NULL REFERENCES world(id),
                                                  -- denormalized from
                                                  -- entity.world_id (same
                                                  -- pattern as
                                                  -- relation.world_id) —
                                                  -- needed because the
                                                  -- one-PC-per-user-per-world
                                                  -- index lives on this
                                                  -- table (schema v1.57,
                                                  -- BRIEF-46)
  character_type  TEXT NOT NULL,                -- player | npc
  user_id         TEXT,                         -- NULL for NPCs
  current_location_id TEXT REFERENCES entity(id),
  vital_status    TEXT DEFAULT 'alive',         -- alive | dead | missing | unknown
  appearance      TEXT,
  backstory       TEXT,
  aversion        TEXT,                         -- prose dual of philosophy
                                                  -- (schema v1.44, BRIEF-33):
                                                  -- what this character
                                                  -- rejects/fears, a concept
                                                  -- or category, never a
                                                  -- named entity. Read into
                                                  -- the NPC dialogue prompt
                                                  -- (H_IDENTITY block).
  secrets         TEXT,                         -- creator-only, plain text
                                                  -- since schema v1.78
                                                  -- (TICKET-0025, B1): no
                                                  -- reader ever consumed
                                                  -- structure.
  physical_tier   INTEGER NOT NULL DEFAULT 0     -- opposed-roll resistance
                                                  -- tier, -1..2 (schema
                                                  -- v1.77, TICKET-0025,
                                                  -- BRIEF-0025-a). Migrated
                                                  -- from entity.metadata
                                                  -- ['physical_tier'].
                                                  -- 0 = ordinaire default.
);
```
-- NOTE on `secrets` vs `knowledge.is_secret`: `character.secrets` holds
-- creator meta-narrative ABOUT the character (true nature, planned reveal
-- arcs, creator intentions), free-form prose. It is NEVER read by any
-- context assembler. What a character knows-but-conceals is modeled as
-- `knowledge` rows with `is_secret = TRUE`, structurally excluded by the
-- assembler.

-----

### `npc_price`

Seller tariff lines (schema v1.77, TICKET-0025, BRIEF-0025-a — replaces
`entity.metadata['price_list']`, BRIEF-20). Curated config, same family as
`faction_role`: no `change_history` column, full-replace writes, hard
delete of a line is the sanctioned edit. Read by the seller-tariff block of
`assemble_npc_context`; written ONLY via `writes.write_npc_prices` (creator
Tarifs editor).

```sql
CREATE TABLE npc_price (
  id         TEXT PRIMARY KEY,
  world_id   TEXT NOT NULL REFERENCES world(id),
  entity_id  TEXT NOT NULL REFERENCES entity(id),
  tag        TEXT NOT NULL,
  amount     INTEGER NOT NULL
);
CREATE UNIQUE INDEX idx_npc_price_tag
  ON npc_price(entity_id, tag COLLATE NOCASE);
```

-----

### `location`

Extension of entity for locations. Supports hierarchy (city > district > building).

```sql
CREATE TABLE location (
  id                TEXT PRIMARY KEY REFERENCES entity(id),
  parent_location_id TEXT REFERENCES entity(id), -- NULL = root location
  location_type     TEXT,
                    -- city | district | building | natural | underground | other
  magic_status      TEXT DEFAULT 'inert',
                    -- inert | sensitive | active | nexus
  coord_x           REAL,      -- map position (schema v1.78, TICKET-0025)
  coord_y           REAL,      -- was coordinates JSON {x,y}; NULL = unplaced
  access_level      TEXT,     -- public | restricted | secret
  bounds_width      REAL,      -- playable-area bounds (schema v1.80, TICKET-0029)
  bounds_height     REAL       -- NULL = no spatial mode. Same local space as
                    -- obstacle_vertex, NOT coord_x/coord_y above.
);
```

-----

### `location_type_catalog`

Classified interior/exterior type registry (schema v1.84, TICKET-0039,
BRIEF-0039-a). One row per `location_type` string, per world.
`classification` is the ONLY interior/exterior signal in the engine: door
kind is derived from the two endpoints' classification, and street-access
checks read it. NULL classification = not yet decided — inert for door
derivation until the creator classifies it via the type picker. Curated
config, but NOT full-replace: this is a per-row upsert catalog, written
ONLY via `writes.upsert_location_type`, which never overwrites a decided
classification with NULL.

`default_width`/`default_height` (schema v1.85, TICKET-0040, BRIEF-0040-a)
are the size template for a location born with this type: the ONLY source
of birth bounds, applied ONCE at creation and never retroactive to an
existing location. Both NULL or both set, enforced by
`writes.upsert_location_type`; a type with no template leaves bounds NULL
(no spatial mode). Same local coordinate space as `obstacle_vertex`.

```sql
CREATE TABLE location_type_catalog (
  id             TEXT PRIMARY KEY,
  world_id       TEXT NOT NULL REFERENCES world(id),
  name           TEXT NOT NULL,
  classification TEXT,        -- interior | exterior | NULL (not yet classified)
  default_width  REAL,        -- size template, world-meters; NULL = no template
  default_height REAL,        -- size template, world-meters; NULL = no template
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_location_type_catalog_name
  ON location_type_catalog(world_id, name COLLATE NOCASE);
```

-----

### `entity_type`

Per-world runtime-type registry (schema v1.87, TICKET-0044, BRIEF-0044-b —
socle of the governed runtime-DDL constructor, A1/Dgov1). World-scoped
config, `location_type_catalog` family (a plain PK, not the entity-extension
shape) — one row per runtime type the constructor has materialized as an
`ext_<slug>` physical table. `status` reserves `quarantined` for B1
(BRIEF-0044-e) now so that step needs no ALTER; `retired` is the soft-retire
value (Ddrop1 — never a `DROP`). `write_authorities`/`ai_proposable` are
Dgov1 governance columns: present now, unpopulated, with NO reader until
0047 — a deliberate, ticket-spanning exception to "no structure without a
reader", taken to avoid an ALTER on this central table every subsequent
ticket. This step ships the table only — no writer, no DDL emission
(BRIEF-0044-c).

```sql
CREATE TABLE entity_type (
  id                TEXT PRIMARY KEY,
  world_id          TEXT NOT NULL REFERENCES world(id),
  name              TEXT NOT NULL,
  slug              TEXT NOT NULL,
  physical_table    TEXT NOT NULL CHECK (physical_table GLOB 'ext_*'),
  status            TEXT NOT NULL DEFAULT 'active',
                    -- active | retired | quarantined
  write_authorities JSON NOT NULL DEFAULT '[]',  -- reserved, Dgov1, no reader yet
  ai_proposable     BOOLEAN NOT NULL DEFAULT FALSE,  -- reserved, Dgov1, no reader yet
  created_by        TEXT,
  created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_entity_type_world ON entity_type(world_id);
CREATE UNIQUE INDEX idx_entity_type_slug
  ON entity_type(world_id, slug COLLATE NOCASE);
CREATE UNIQUE INDEX idx_entity_type_physical_table ON entity_type(physical_table);
```

-----

### `entity_type_history`

Append-only DDL-event log (schema v1.87, TICKET-0044, BRIEF-0044-b — A1,
`ledger` family). History is sacred, now at the schema grain: append-only by
construction, no `change_history` column — the rows ARE the history. Only
`type_created` is produced at the socle; the remaining `event` values are
reserved (present in the CHECK now so 0045/BRIEF-0044-e need no ALTER).
Source for B1 quarantine and C2 reconciliation (later briefs of this
ticket).

```sql
CREATE TABLE entity_type_history (
  id                   TEXT PRIMARY KEY,
  world_id             TEXT NOT NULL REFERENCES world(id),
  entity_type_id       TEXT NOT NULL REFERENCES entity_type(id),
  event                TEXT NOT NULL,
                       -- type_created | trait_added | type_retired |
                       -- type_quarantined | type_restored
  definition_snapshot  JSON NOT NULL,  -- full definition at the instant of the event
  physical_table       TEXT NOT NULL,
  ddl_text             TEXT,           -- exact DDL emitted for this event
  changed_by           TEXT,
  created_at           DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_entity_type_history_type ON entity_type_history(entity_type_id);
```

-----

### `entity_trait`

Materialized trait projection (schema v1.88, TICKET-0045, BRIEF-0045-a).
Which `entity_type` has checked which trait — NOT the trait definition
(that lives in code, `traits.py`) and NOT an entity-extension row, a
projection join row only. `trait_key` legality is a code-plane property
verified by `trait_registry_projection.py`, NOT a SQL CHECK — a CHECK would
duplicate the vocabulary across code and DDL and need an ALTER every time a
trait is added. Reader is the projection check plus the constructor UI
(TICKET-0046). Not history: a creator un-checking a trait is an
`entity_type` DDL event recorded in `entity_type_history` (`trait_added`),
not a `change_history` column here. Socle traits (`traits.socle_traits()`,
`describable` today) are implicit on every entity_type and NEVER appear as
a row here — guaranteed at read time, not projected (BRIEF-0045-d); a
socle trait_key in this table is a `trait_registry_projection.py` FAIL.

```sql
CREATE TABLE entity_trait (
  id             TEXT PRIMARY KEY,
  entity_type_id TEXT NOT NULL REFERENCES entity_type(id),
  trait_key      TEXT NOT NULL,
  created_by     TEXT,
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_entity_trait_type ON entity_trait(entity_type_id);
CREATE UNIQUE INDEX idx_entity_trait_unique
  ON entity_trait(entity_type_id, trait_key);
```

-----

### `location_subculture`

Ambient culture lines (schema v1.78, TICKET-0025, BRIEF-0025-b — replaces
`location.subculture` JSON). One row per key. `is_hidden = TRUE` rows are
creator-only: every non-creator read path filters `is_hidden = FALSE` AT
QUERY CONSTRUCTION — exclusion is structural, never instructional. Curated
config, same family as `faction_role`: no `change_history`, full-replace
writes via `writes.write_location_subculture` only.

```sql
CREATE TABLE location_subculture (
  id          TEXT PRIMARY KEY,
  world_id    TEXT NOT NULL REFERENCES world(id),
  location_id TEXT NOT NULL REFERENCES entity(id),
  key         TEXT NOT NULL,
  value       TEXT NOT NULL,
  is_hidden   BOOLEAN NOT NULL DEFAULT FALSE
);
CREATE UNIQUE INDEX idx_location_subculture_key
  ON location_subculture(location_id, key COLLATE NOCASE);
```

-----

### `obstacle` / `obstacle_vertex`

Intra-location wall geometry (schema v1.80, TICKET-0029, BRIEF-0029-a).
First step of the spatial / Play mode workstream — the server can judge
movement against this (collision endpoint, ticket 0030) and the client can
draw it (canvas renderer, ticket 0032); nothing here moves. Curated config,
same family as `faction_role`: no `change_history`, full-replace writes via
`writes.write_location_obstacles` only. One obstacle = one closed polygon,
stored as ordered vertex rows (`agenda_step.step_order` precedent) — NEVER a
JSON list. v1 obstacles are 4-vertex rectangles; real polygons later add
vertex rows only, never a schema rewrite.

**COORDINATE SPACE:** per-location local coordinates. Origin at the
top-left of the playable area, x rightward, y DOWNWARD (canvas-native).
Nominal unit: 1.0 = one world-meter. This space is DISTINCT from
`location.coord_x` / `coord_y` (v1.78), which place the location on the
WORLD map — never mix the two. Rectangle→vertex expansion emits the 4
corners CLOCKWISE from the top-left corner (declared convention, not
structurally enforced).

```sql
CREATE TABLE obstacle (
  id          TEXT PRIMARY KEY,
  world_id    TEXT NOT NULL REFERENCES world(id),
  location_id TEXT NOT NULL REFERENCES entity(id),
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_obstacle_location ON obstacle(location_id);

CREATE TABLE obstacle_vertex (
  id            TEXT PRIMARY KEY,
  obstacle_id   TEXT NOT NULL REFERENCES obstacle(id),
  vertex_order  INTEGER NOT NULL,
  x             REAL NOT NULL,
  y             REAL NOT NULL
);
CREATE UNIQUE INDEX idx_obstacle_vertex_order
  ON obstacle_vertex(obstacle_id, vertex_order);
```

-----

### `door`

Inter-location passage, spatial side (schema v1.81, TICKET-0034,
BRIEF-0034-a). Curated config, same family as `faction_role`: no
`change_history`, full-replace writes via `writes.write_location_doors`
only.

**ONE ROW PER SIDE.** A passage between A and B is two rows: (A -> B) and
(B -> A), each carrying the point in ITS OWN location's local space.
Pairing is DERIVED at arrival — "the door of B that points back at A" —
and made unambiguous BY `idx_door_target`, not by a defended invariant.
The consequence is deliberate: at most one door per ordered pair of
locations.

**TERMINAL BY CONTRACT:** no table may take a foreign key on `door.id`.
The A1 -> A2 escalation (one `passage` row carrying both endpoints,
needed the day two passages must join the same pair of locations) is a
mechanical self-join ONLY while nothing references a door by id. This is
enforced by `tooling/verify/checks/door_terminal.py`, not by memory.

A door is the SPATIAL MANIFESTATION of a `connects_to` edge, never its
source: `write_location_doors` REJECTS a target with no active
`connects_to` edge; the play-side reader FILTERS doors whose edge later
disappeared. The map stays the world's traversability truth. Neither side
cascades or deletes.

**COORDINATE SPACE:** per-location local coordinates — the
`obstacle_vertex` space (origin top-left, x rightward, y DOWNWARD, 1.0 =
one world-meter), NOT `location.coord_x` / `coord_y` (world map). `x, y`
is the door's point in `location_id`'s space; the counterpart row carries
its own point in the counterpart's space. Nothing at the write site judges
whether that point is inside a wall.

```sql
CREATE TABLE door (
  id                 TEXT PRIMARY KEY,
  world_id           TEXT NOT NULL REFERENCES world(id),
  location_id        TEXT NOT NULL REFERENCES entity(id),
  target_location_id TEXT NOT NULL REFERENCES entity(id),
  x                  REAL NOT NULL,
  y                  REAL NOT NULL,
  created_at         DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_door_target
  ON door(location_id, target_location_id);
```

-----

### `faction`

Extension of entity for factions.

```sql
CREATE TABLE faction (
  id                    TEXT PRIMARY KEY REFERENCES entity(id),
  faction_type          TEXT,
                        -- government | criminal | military | esoteric | other
  internal_structure    TEXT,
  philosophy            TEXT,
  magic_knowledge_level TEXT DEFAULT 'unaware',
                        -- unaware | suspicious | partial | knows | understands
  internal_tensions     TEXT,
  parent_faction_id     TEXT REFERENCES entity(id),
                        -- containment tree, mirror of location.parent_location_id.
                        -- NULL = root faction. DORMANT (BRIEF-26, schema v1.38):
                        -- no assembler or guard traverses it yet — creator-CRUD
                        -- only, metadata-config category, no change_history (same
                        -- as location_type / coord_x / coord_y).
  scope                 TEXT,
                        -- global | national | regional | local | other.
                        -- DORMANT: descriptive scale label, NOT derived from
                        -- tree depth. No code reads it yet.
  goals                 TEXT,
                        -- DORMANT: prose, what the faction is trying to do.
                        -- No mechanic, no structured consumer.
  aversion              TEXT
                        -- DORMANT (schema v1.44, BRIEF-33): prose dual of
                        -- philosophy — what the faction rejects/combats, a
                        -- concept or category, never a named entity. Public-
                        -- tagged, authored + proposed, but read by no
                        -- assembler yet; the future reader MUST route
                        -- through read_public_memberships.
);
CREATE INDEX idx_faction_parent ON faction(parent_faction_id);
```

-----

### `faction_role`

Declared role vocabulary of a faction (schema v1.76, TICKET-0024,
BRIEF-0024-d — corrective). Replaces the disconnected pair
`faction.role_capacities` (JSON, BRIEF-0024-a) + `entity.metadata['roles']`
(JSON, BRIEF-31) with one relational table: informations in columns and
tables, not JSON blobs. Public by construction (BRIEF-31 lineage) — safe to
expose to prompts and player-facing reads. Closed vocabulary for the AI
path (K1: `role_change` rejects an undeclared role unless `declare:true`,
L2). Curated config, same family as `faction_type` / `philosophy` — no
`change_history` column; case-uniqueness is the unique index's job, not a
code-side casefold check.

```sql
CREATE TABLE faction_role (
  id           TEXT PRIMARY KEY,
  world_id     TEXT NOT NULL REFERENCES world(id),
  faction_id   TEXT NOT NULL REFERENCES faction(id),
  name         TEXT NOT NULL,
  description  TEXT,
  max_holders  INTEGER,        -- NULL = unlimited
  position     INTEGER NOT NULL DEFAULT 0,   -- display order
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_by   TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_faction_role_name
  ON faction_role(faction_id, name COLLATE NOCASE);
  -- Structural: case-duplicate role names are schema-impossible for the
  -- same faction. writes.write_faction_role is the sole chokepoint;
  -- mode="rename" (T1) closes+reopens every ACTIVE faction_membership row
  -- whose true `role` casefold-matches the old name, preserving
  -- cover_role/is_primary/is_secret; mode="delete" (S1) is a guarded hard
  -- delete, blocked while any active membership still holds the role.
```

-----

### `faction_membership`

Durable member <-> faction roster (schema v1.39, BRIEF-27). Mirror of
`gathering_member`'s roster shape, but **durable** — no `session_id`,
membership persists across sessions (`gathering_member` is session-ephemeral
co-presence; this table is the long-lived relationship).

```sql
CREATE TABLE faction_membership (
  id          TEXT PRIMARY KEY,
  world_id    TEXT NOT NULL REFERENCES world(id),
  entity_id   TEXT NOT NULL REFERENCES entity(id),  -- the member (a character, by intent)
  faction_id  TEXT NOT NULL REFERENCES entity(id),  -- the faction
  role        TEXT,            -- creator-authored TRUE label (e.g. "espion").
                               -- Creator-only — never read by any prompt
                               -- assembler when cover_role is set (schema
                               -- v1.41, BRIEF-30).
  cover_role  TEXT,            -- prompt-facing façade role (e.g. "membre").
                               -- NULL by default. read_public_memberships
                               -- resolves cover_role ?? role; the true role
                               -- never crosses that accessor when a cover
                               -- is set (schema v1.41, BRIEF-30).
  is_primary  BOOLEAN DEFAULT FALSE,  -- the member's identifying faction.
  is_secret   BOOLEAN DEFAULT FALSE,  -- the mole. DORMANT: present but its
                               -- exclusion is NOT enforced this step (no
                               -- reader exists). The first reader MUST
                               -- filter is_secret=FALSE for every
                               -- non-creator context, by query construction.
  joined_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  left_at     DATETIME         -- NULL = active. Roster predicate, single
                               -- source: a membership is active iff
                               -- left_at IS NULL. Rows are NEVER deleted or
                               -- edited in place — only closed (left_at set).
);
CREATE INDEX idx_faction_membership_entity  ON faction_membership(entity_id);
CREATE INDEX idx_faction_membership_faction ON faction_membership(faction_id);
-- Structural guards (enforce by construction, not by instruction):
CREATE UNIQUE INDEX idx_membership_one_primary
  ON faction_membership(entity_id) WHERE is_primary = TRUE AND left_at IS NULL;
CREATE UNIQUE INDEX idx_membership_unique_active
  ON faction_membership(entity_id, faction_id) WHERE left_at IS NULL;
```
-- NOTE: `entity_id`/`faction_id` carry no `CHECK` on type (loose typing,
-- consistent with the rest of the schema) — membership is character->faction
-- by INTENT, not enforced. Faction-in-faction containment is
-- `parent_faction_id`'s job (schema v1.38), not this table.
-- NOTE: append/close only, by construction — no `change_history` column. A
-- role or primary-status change is close (set `left_at`) + reopen (a new
-- row); the closed-row sequence IS the history.
-- NOTE: `role`/`is_secret` are DORMANT — stored, creator-editable
-- (`writes.write_membership`), read by no assembler. No reader, no
-- structural secret-exclusion this step (Scope OUT, BRIEF-27); both are the
-- next, separate brief.

-----

### `relation`

The universal relation graph. Works between any entities.

```sql
CREATE TABLE relation (
  id                  TEXT PRIMARY KEY,
  world_id            TEXT NOT NULL REFERENCES world(id),
  entity_a_id         TEXT NOT NULL REFERENCES entity(id),
  entity_b_id         TEXT NOT NULL REFERENCES entity(id),
  type                TEXT NOT NULL,
                      -- ally | enemy | debt | fear | fascination |
                      -- shared_secret | instrumentalizes | interest |
                      -- indifference | rejection | passive_attention | other |
                      -- connects_to | controls
  direction           TEXT DEFAULT 'mutual',
                      -- mutual | a_to_b | b_to_a
                      -- NOTE: magic relations = always a_to_b
                      --       (magic chooses, not the other way around)
  intensity           INTEGER DEFAULT 50 CHECK (intensity BETWEEN 1 AND 100),
                      -- single axis: 1 = actively works/spends to harm,
                      -- 50 = neutral/indifferent, 100 = actively works/spends to help.
                      -- Direction and strength are intentionally one number:
                      -- words and actions push it up or down, and that value
                      -- directly drives the entity's attitude.
                      -- CLAMP on apply: a delta must never push below 1 or above 100
                      -- (e.g. +20 on a relation at 95 settles at 100, not 115).
  visible_to_b        BOOLEAN DEFAULT TRUE,
                      -- FALSE = entity_b does not feel or know
  notes               TEXT,
  created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
  last_evolved_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  change_history      JSON DEFAULT '[]'  -- archived evolutions
);
```
-- NOTE: `connects_to` (location<->location map topology) and `controls`
--       (controller -> controlled asset, schema v1.38/BRIEF-26) are
--       structurally isolated relation types. Both carry a MEANINGLESS
--       structural `intensity=50` default with no social significance.
--       Every gameplay reader of `relation` keyed on a character/player id
--       is structurally blind to them (their endpoints are non-character
--       entities). `controls` is direction='a_to_b' (controller is
--       entity_a, asset is entity_b); reading "who controls asset X" = the
--       entity_a of `controls` rows whose entity_b = X — several rows means
--       shared/contested control, no special handling. Any future
--       world-wide relation scan MUST explicitly exclude both
--       type='connects_to' and type='controls'.

-----

### `knowledge`

What each entity knows — structured and injectable into prompts.

```sql
CREATE TABLE knowledge (
  id               TEXT PRIMARY KEY,
  entity_id        TEXT NOT NULL REFERENCES entity(id),
  subject          TEXT NOT NULL,
                   -- ex: "magic_existence", "the_11", "verkhaal_nexus",
                   --     "the_unnamed", "faction_X_status"
  level            TEXT NOT NULL,
                   -- unaware | rumor | suspicious | partial | knows | fully_understands
  content          TEXT,            -- what exactly it knows
  source           TEXT,            -- how it learned it
  is_incorrect     BOOLEAN DEFAULT FALSE,  -- knows but it's wrong
  is_secret        BOOLEAN DEFAULT FALSE,  -- does not share
  share_threshold  INTEGER DEFAULT 50 CHECK (share_threshold BETWEEN 1 AND 100),
                   -- minimum NPC→interlocutor relation intensity (1–100) required
                   -- for the NPC to share this row in conversation. Ignored when
                   -- is_secret = TRUE (secrets are never shared, whatever the relation).
  acquired_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
  session_id       TEXT,            -- acquired during which session
  change_history   JSON DEFAULT '[]'  -- archived previous states, mirror of
                     --                  relation.change_history
);
-- NOTE: when the NPC has no relation toward the interlocutor, the assembler
--       treats the relation as neutral (intensity 50). A row therefore shares
--       by default (threshold 50) and only becomes warmth-gated when its
--       share_threshold is raised above 50.
```

-----

### `npc_goal`

NPC volition (schema v1.69, TICKET-0013/BRIEF-0013-a; `kind` added v1.91,
TICKET-0073). Read ONLY by `assemble_npc_context` (the `TES OBJECTIFS` and
`POURQUOI TU ES ICI` sections), the tick briefing, the initiative vote and
`_mutation_goal_change_close` — `assemble_mj_context` never reads this table
(structural exclusion, N1).

```sql
CREATE TABLE npc_goal (
  id              TEXT PRIMARY KEY,
  world_id        TEXT NOT NULL REFERENCES world(id),
  npc_id          TEXT NOT NULL REFERENCES entity(id),
  description     TEXT NOT NULL,   -- immutable after insert (see NOTE below)
  horizon         TEXT NOT NULL CHECK (horizon IN ('short','long')),
  kind            TEXT NOT NULL DEFAULT 'volition'
                    CHECK (kind IN ('volition','standing')),
                    -- volition | standing (TICKET-0073, G2) — see NOTE below
  status          TEXT NOT NULL DEFAULT 'active'
                    CHECK (status IN ('active','completed','abandoned')),
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  change_history  JSON DEFAULT '[]'  -- archived previous states, mirror of
                    --                  knowledge.change_history
  -- CHECK (kind <> 'standing' OR horizon = 'long')  -- ck_npc_goal_standing_horizon
);
CREATE INDEX idx_npc_goal_npc_status ON npc_goal(npc_id, status);
```
-- NOTE: description is immutable after insert; a changed goal is a closed
--       goal plus a new row. Status transitions are one-way, active ->
--       closed only (completed | abandoned) — a closed goal is never
--       reopened; a revived goal is a new row.
-- NOTE (v1.91, TICKET-0073, G2): `kind='volition'` is in-scene volition —
--       everything this table held before v1.91. `kind='standing'` is
--       background volition (an occupation, a trade, a pastime): no
--       terminal state, never closed by play, creator-CRUD authored only,
--       and implies `horizon='long'` (ck_npc_goal_standing_horizon). Every
--       in-scene reader filters on `kind` explicitly; the CHECK is defence
--       in depth. Standing rows render in their own section
--       (`POURQUOI TU ES ICI`), framed as a reason for presence rather than
--       a current action (M1), and add an `ici pour=` fragment to the
--       initiative signal line — never merged with a volition goal.

-----

### `npc_schedule`

Standing per-phase location default (schema v1.92, TICKET-0074,
BRIEF-0074-a). Curated config, same family as `location_type_catalog` /
`world_law`: no `change_history`, written ONLY via
`writes.write_npc_schedule` (full-replace per NPC). Sparse by decision
(B1) — absence of a row is legal; `schedule_reads.py::where_is` supplies
the fallback. `standing_goal_id`, when set, must reference an `npc_goal`
row belonging to the same `npc_id` with `kind='standing'` (writer-enforced,
not a DB constraint — SQLite CHECK cannot cross-reference another table's
row).

```sql
CREATE TABLE npc_schedule (
  id                TEXT PRIMARY KEY,
  world_id          TEXT NOT NULL REFERENCES world(id),
  npc_id            TEXT NOT NULL REFERENCES entity(id),
  phase             TEXT NOT NULL CHECK (phase IN ('matin','apres-midi','soir','nuit')),
  location_id       TEXT NOT NULL REFERENCES entity(id),
  standing_goal_id  TEXT REFERENCES npc_goal(id),
  created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_npc_schedule_npc_phase ON npc_schedule(npc_id, phase);
CREATE INDEX idx_npc_schedule_location_phase ON npc_schedule(location_id, phase);
```
-- NOTE: no calendrical axis in v1 (A1a) — `phase` is a pure day-cycle,
--       never widened to `(npc_id, phase, day_kind)` if a calendar lands
--       later (SQLite treats NULLs as DISTINCT inside a UNIQUE index, so
--       that widening would silently lose the one-row-per-NPC-per-phase
--       guarantee). The correct future path is the `faction_membership`
--       partial-unique idiom: one partial UNIQUE `WHERE day_kind IS NULL`,
--       one `WHERE day_kind IS NOT NULL`.

-----

### `goal_prerequisite`

`npc_goal` completion gate (schema v1.79, TICKET-0025, BRIEF-0025-c —
replaces `npc_goal.prerequisites` JSON). Closed vocabulary (K1) enforced
by CHECK: v1 accepts ONLY `relation_gte`. Creator-CRUD authored only
(`writes.write_npc_goal_prerequisites`, BRIEF-0024-a's editor). Read by
`_apply_mutation`'s `goal_change complete` judge and the per-NPC tick
briefing (BRIEF-0024-b).

```sql
CREATE TABLE goal_prerequisite (
  id               TEXT PRIMARY KEY,
  world_id         TEXT NOT NULL REFERENCES world(id),
  goal_id          TEXT NOT NULL REFERENCES npc_goal(id),
  type             TEXT NOT NULL CHECK (type IN ('relation_gte')),
  target_entity_id TEXT NOT NULL REFERENCES entity(id),
  threshold        INTEGER NOT NULL CHECK (threshold BETWEEN 1 AND 100)
);
CREATE UNIQUE INDEX idx_goal_prerequisite_unique
  ON goal_prerequisite(goal_id, type, target_entity_id);
```

-----

### `ledger`

Conserved currency, append-only (schema v1.31, BRIEF-18). Balance is `SUM(amount)` per `entity_id`, computed at read time — no stored balance, no `CHECK`.

```sql
CREATE TABLE ledger (
  id              TEXT PRIMARY KEY,
  world_id        TEXT NOT NULL REFERENCES world(id),
  entity_id       TEXT NOT NULL REFERENCES entity(id),  -- whose balance moves
  amount          INTEGER NOT NULL,        -- signed: + credit, − debit; world base unit
  counterparty_id TEXT REFERENCES entity(id),           -- the other party (filled, not double-written)
  reason          TEXT,                    -- "pécule de départ", "correction prix"
  source_type     TEXT,                    -- creator | correction | conversation | pass_play | tick
                                            -- ('conversation' written by
                                            -- _apply_mutation's resource_change
                                            -- branch, BRIEF-19/v1.32; 'pass_play'
                                            -- still unused; 'tick' written by
                                            -- _apply_mutation's ledger_transfer
                                            -- completion effect, schema v1.75,
                                            -- TICKET-0024/BRIEF-0024-c, M1)
  conversation_id TEXT REFERENCES conversation(id),
  pass_play_id    TEXT REFERENCES pass_play(id),
  session_id      TEXT REFERENCES session(id),
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_ledger_entity  ON ledger(entity_id);
CREATE INDEX idx_ledger_session ON ledger(session_id);
```
-- NOTE: INSERT-only. No UPDATE, no DELETE, ever, on any write path — a
--       mistake is corrected with a new compensating line
--       (source_type='correction'), never by editing or deleting a row.
--       counterparty_id is filled for the registre's legibility but never
--       triggers a second ledger row (decision A1, no PNJ double-entry).

-----

### `session`

A period of play. Pass-plays and live conversations attach to it.

```sql
CREATE TABLE session (
  id              TEXT PRIMARY KEY,
  world_id        TEXT NOT NULL REFERENCES world(id),
  number          INTEGER NOT NULL,
  title           TEXT,
  started_at      DATETIME,
  ended_at        DATETIME,
  status          TEXT DEFAULT 'open',
                  -- open | closed | archived
  summary         TEXT,             -- written after the fact
  creator_notes   TEXT              -- creator-only
);
```

-----

### `batch`

Grouping of pass-plays for consolidated processing.

```sql
CREATE TABLE batch (
  id                    TEXT PRIMARY KEY,
  session_id            TEXT NOT NULL REFERENCES session(id),
  day_number            INTEGER NOT NULL DEFAULT 0,
                        -- the day IS the batch ordinal (L1), scoped to its
                        -- session (U1); allocated by writes.write_batch as
                        -- max(day_number) + 1 per session_id
  status                TEXT DEFAULT 'pending',
                        -- pending | local_analysis | ready_checkpoint_1 |
                        -- approved_checkpoint_1 | sent_to_claude |
                        -- received_from_claude | ready_checkpoint_2 |
                        -- approved_checkpoint_2 | applied
  local_summary         TEXT,          -- day narration draft (repurposed
                        -- BRIEF-0075-d; formerly "summary generated by
                        -- local AI" for the abandoned checkpoint pipeline)
  message_to_claude     TEXT,          -- editable at checkpoint 1 (vestigial,
                        -- abandoned Claude-checkpoint pipeline; zero writers)
  claude_raw_response   TEXT,          -- raw Claude API response (vestigial,
                        -- abandoned Claude-checkpoint pipeline; zero writers)
  final_result          TEXT,          -- day narration, accepted post-judge
                        -- (repurposed BRIEF-0075-d; formerly "edited at
                        -- checkpoint 2" for the abandoned checkpoint pipeline)
  creator_notes         TEXT,
  created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
  processed_at          DATETIME,
  applied_at            DATETIME
);
-- idx_batch_session_day: UNIQUE (session_id, day_number).
```

-----

### `pass_play`

An action declared by a player between two sessions. `agenda_id` (schema
v1.95, TICKET-0077/BRIEF-0077-a) records which day plan this pass advanced —
written once, at plan time, never rewritten. NULL for every pre-v1.95 row and
for a day that never reached plan emission; `/resolve` falls back to the
player's active agenda in that case (no backfill).

```sql
CREATE TABLE pass_play (
  id                  TEXT PRIMARY KEY,
  batch_id            TEXT NOT NULL REFERENCES batch(id),
  session_id          TEXT NOT NULL REFERENCES session(id),
  character_id        TEXT NOT NULL REFERENCES entity(id),
  agenda_id           TEXT REFERENCES agenda(id),  -- BRIEF-0077-a
  declared_action     TEXT NOT NULL,    -- player free text
  injected_context    JSON,             -- world state snapshot at deposit time
  creator_notes       TEXT,
  status              TEXT DEFAULT 'submitted',
                      -- submitted | analyzed | batched | applied | rejected
  batch_order         INTEGER,
  history             JSON DEFAULT '[]', -- all successive versions
  submitted_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
  applied_at          DATETIME
);
-- NOTE: the old `local_proposal` column is removed.
-- Proposed changes now live in `proposed_mutation` (one pass-play can spawn several).
```

-----

### `gathering`

An ephemeral social cluster: who is standing together at a location, for the
duration of a session. Attached to the session, not to the world's lasting
state — its only durable trace is the `proposed_mutation` rows it produces
(forming or dissolving a gathering is not itself a canon mutation).

```sql
CREATE TABLE gathering (
  id            TEXT PRIMARY KEY,
  world_id      TEXT NOT NULL REFERENCES world(id),
  session_id    TEXT NOT NULL REFERENCES session(id),
  location_id   TEXT NOT NULL REFERENCES entity(id),
  label         TEXT,             -- generated by the MJ (descriptive, not canon)
  status        TEXT DEFAULT 'open',
                -- open | dissolved
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  dissolved_at  DATETIME
);
```

-----

### `gathering_member`

The roster of a gathering — also doubles as the participant list for any
conversation attached to it. Earshot is `left_at IS NULL`; rows are never
deleted, only closed off, so the roster's history stays intact.

```sql
CREATE TABLE gathering_member (
  id            TEXT PRIMARY KEY,
  gathering_id  TEXT NOT NULL REFERENCES gathering(id),
  entity_id     TEXT NOT NULL REFERENCES entity(id),
  joined_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  left_at       DATETIME          -- NULL = still present; never erased
);
```

-----

### `conversation`

A live player ↔ NPC exchange, anchored to a location and a session.

```sql
CREATE TABLE conversation (
  id               TEXT PRIMARY KEY,
  world_id         TEXT NOT NULL REFERENCES world(id),
  session_id       TEXT NOT NULL REFERENCES session(id),
  location_id      TEXT REFERENCES entity(id),         -- where it happens
  player_id        TEXT NOT NULL REFERENCES entity(id), -- the player character
  npc_id           TEXT REFERENCES entity(id),         -- optional seed/focus NPC;
                                                        -- participants now derive
                                                        -- from the gathering roster
  gathering_id     TEXT REFERENCES gathering(id),      -- the social cluster present
  status           TEXT DEFAULT 'open',
                   -- open | closed | archived
  injected_context JSON,    -- snapshot of the NPC context used to drive dialogue
                            -- (what the NPC was allowed to know — for audit/replay)
  started_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
  ended_at         DATETIME,
  last_analyzed_turn INTEGER NOT NULL DEFAULT 0,
                            -- high-water mark for window analysis
                            -- (analyze_window): conversation_message rows with
                            -- turn_order <= this value have already been
                            -- analyzed. 0 = never analyzed.
  scene_state       JSON NOT NULL DEFAULT '{}'
                            -- EPHEMERAL combat/constraint state, scoped to
                            -- this conversation. Cleared on close. NOT canon.
                            -- Structure: {constraints: ["gagged"|"restrained"|
                            -- "blindfolded"], condition: "unharmed"|"bruised"|
                            -- "injured"|"neutralized", frozen: false,
                            -- history: [<snapshots>]}
                            -- Every write appends the previous state to
                            -- history[] before overwriting (history is sacred).
);
```

-----

### `conversation_message`

Each line in a conversation, in order. The raw transcript the AI later analyzes to propose mutations.

```sql
CREATE TABLE conversation_message (
  id              TEXT PRIMARY KEY,
  conversation_id TEXT NOT NULL REFERENCES conversation(id),
  turn_order      INTEGER NOT NULL,        -- sequence within the conversation
  speaker         TEXT NOT NULL,           -- player | npc | mj
                                           --   player : canonical player turn
                                           --   npc    : canonical NPC reply (buffered,
                                           --            never streamed raw to player)
                                           --   mj     : MJ narration prose (presentation
                                           --            layer — what the player sees)
  speaker_id      TEXT REFERENCES entity(id),  -- which entity spoke (NULL for mj)
  content         TEXT NOT NULL,           -- the line itself
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
-- turn_order layout per player turn:
--   N   → player (canonical)
--   N+1 → npc    (canonical; ABSENT for scene turns — NPC was not called)
--   N+2 → mj     (presentation)
-- Analysis reads only player + npc rows; mj rows are never fed to the model.
-- For scene turns npc_reply="" → mini-transcript ends "[PNJ] " → analyzer
-- returns [] (correct: no world-state change in a pure environment action).
```

-----

### `conversation_window_config`

Creator-tunable NPC dialogue context window (schema v1.89, TICKET-0050,
BRIEF-0050-a). One row per world; absence is legal — the code reader
(`conversation_window.load_conversation_window_config`) applies in-memory
defaults and never inserts a row on read. Curated config, same family as
`location_type_catalog`: no `change_history`, written ONLY via
`writes.upsert_conversation_window_config` (upsert-one, never a
`DELETE FROM conversation_window_config`).

`word_budget` and `verbatim_turns` govern the sliding-summary NPC-dialogue
window (brief b/d): `verbatim_turns` counts player/npc MESSAGE rows, not
exchanges (6 = 3 exchanges). `summary_enabled` gates the sliding-summary
recovery above budget; the K-verbatim cap and scene tail always apply
regardless of this flag (M1 — enables a live A/B of summary vs cap-only).

```sql
CREATE TABLE conversation_window_config (
  id              TEXT PRIMARY KEY,
  world_id        TEXT NOT NULL REFERENCES world(id),
  word_budget     INTEGER NOT NULL DEFAULT 1200,
  verbatim_turns  INTEGER NOT NULL DEFAULT 6,
  summary_enabled BOOLEAN NOT NULL DEFAULT 1,
  updated_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_conversation_window_config_world
  ON conversation_window_config(world_id);
```

-----

### `proposed_mutation`

A single atomic change to world state, awaiting creator approval. Produced by both pass-plays and live conversations — the unified validation pipeline.

```sql
CREATE TABLE proposed_mutation (
  id              TEXT PRIMARY KEY,
  world_id        TEXT NOT NULL REFERENCES world(id),

  -- source: exactly one of these is set (world_tick sets NEITHER FK below;
  -- tick_id is its anchor — schema v1.70, TICKET-0014/BRIEF-0014-b)
  source_type     TEXT NOT NULL,           -- pass_play | conversation | world_tick
  pass_play_id    TEXT REFERENCES pass_play(id),
  conversation_id TEXT REFERENCES conversation(id),
  tick_id         TEXT,                    -- one UUID per run_world_tick invocation

  -- what kind of change
  mutation_type   TEXT NOT NULL,
                  -- relation_change | new_knowledge | knowledge_change |
                  -- event_creation | status_change | entity_creation |
                  -- item_update | resource_change | goal_change |
                  -- npc_move | other
                  -- (goal_change targets npc_goal — TICKET-0013/BRIEF-0013-c)
                  -- (npc_move targets character.current_location_id,
                  -- tick-only producer, no schema bump — TICKET-0015/
                  -- BRIEF-0015-a)
  target_table    TEXT,                    -- table the change applies to
  target_id       TEXT,                    -- row affected (NULL if creation)
  payload         JSON NOT NULL,           -- the proposed change, structured

  -- control
  status          TEXT DEFAULT 'proposed',
                  -- proposed | approved | rejected | applied
  rationale       TEXT,                    -- why the AI proposed it (raw draft text)
  creator_notes   TEXT,                    -- creator edit/justification
  proposed_by     TEXT DEFAULT 'local_ai', -- local_ai_window    : window analysis
                                           --                      (analyze_window, v1.21).
                                           --                      Fires at scene-boundary
                                           --                      triggers (conversation
                                           --                      close, location
                                           --                      transition, gathering
                                           --                      dissolution) and the
                                           --                      manual Analyze button.
                                           --                      Owns ALL mutation
                                           --                      types, including
                                           --                      relation_change (one
                                           --                      per pair per window —
                                           --                      see anti-inflation
                                           --                      rubric).
                                           -- local_ai_overhearing : Tier 4 overhearing
                                           --                      pass (new_knowledge
                                           --                      acquisitions and
                                           --                      knowledge_change
                                           --                      upgrades, v1.17)
                                           -- local_ai_tick      : world tick
                                           --                      (run_world_tick, v1.70).
                                           --                      Manual, scoped, creator-
                                           --                      triggered off-screen NPC
                                           --                      advancement. Owns
                                           --                      goal_change |
                                           --                      relation_change |
                                           --                      new_knowledge |
                                           --                      npc_move only (closed
                                           --                      contract, TICKET-0015/
                                           --                      BRIEF-0015-a); rows
                                           --                      share a tick_id, both FKs
                                           --                      above NULL.
                                           -- interpretation     : /say interpretation
                                           --                      phase (item_update,
                                           --                      equip toggle) — dormant
                                           --                      since BRIEF-08/D2a.1,
                                           --                      no live producer; tag
                                           --                      remains on existing
                                           --                      applied rows
                                           -- local_ai           : legacy — final-pass
                                           --                      analysis
                                           --                      (analyze_conversation,
                                           --                      removed in v1.21).
                                           --                      No longer produced;
                                           --                      historical rows
                                           --                      preserved.
                                           -- local_ai_immediate : legacy — per-turn
                                           --                      analysis
                                           --                      (analyze_single_turn,
                                           --                      removed in v1.21).
                                           --                      No longer produced;
                                           --                      historical rows
                                           --                      preserved.
                                           -- claude | creator
  proposed_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  reviewed_at     DATETIME,
  applied_at      DATETIME
);
-- status = 'applied' is set only after the creator approves AND the change is
-- written to the real table. Until then, world state is untouched.
```

`entity_creation` (TICKET-0019/BRIEF-0019-a, no schema change) has a
two-stage lifecycle distinct from every other type: approval does NOT apply
it. `status` stays `approved` (response `pending_realization`) —
`_apply_mutation` has no branch for this type at all; `target_id` is always
NULL and `target_table` is always `"entity"` (the germ,
`{entity_type, name, concept, anchor?}`, carries no id whatsoever).
Realization happens later, on the creator's own time, via the Création
tab's "Créations en attente" strip: the pure authoring chain drafts a sheet
from the germ, and the creator's own `create_entity` commit (the OTHER
sanctioned canon-write path) creates the entity — a separate, guarded
follow-up commit then stamps this row's `payload.created_entity_id` and
flips `status` to `applied`; a linkage guard failure never rolls back the
entity. Produced by the scope-level `world_tick` call (both location and
faction scopes, `ENTITY_CREATION_QUOTA = 1`, own budget) and, dormantly, by
conversation analysis (a shapeless payload tolerated at the pending-list
read side rather than normalized).

-----

### `event`

Facts that occur in the world, arising from sessions or generated.

```sql
CREATE TABLE event (
  id                    TEXT PRIMARY KEY,
  world_id              TEXT NOT NULL REFERENCES world(id),
  session_id            TEXT REFERENCES session(id),
  batch_id              TEXT REFERENCES batch(id),
  title                 TEXT NOT NULL,
  description           TEXT,
  type                  TEXT,
                        -- political | magical | criminal | military |
                        -- social | mystery | other
  knowledge_status      TEXT DEFAULT 'secret',
                        -- secret | rumor | confirmed | public
  location_id           TEXT REFERENCES entity(id),
  has_magic_impact      BOOLEAN DEFAULT FALSE,
  consequences          JSON,     -- changes applied to the world
  occurred_at           DATETIME,
  recorded_at           DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

Two producers write this table (TICKET-0017/BRIEF-0017-a, no schema
change), both through `_apply_mutation`'s `event_creation` branch ->
`write_event` (the single canon-write site): a scope-level `world_tick`
call for location/faction-scoped invocations (closed payload shape
`{title, description, type, knowledge_status, involved_entities,
location_id}`, quota-bounded), and the analyzer's conversation-sourced
channel (minimal shape `{title, description, type, involved_entities}` —
no `knowledge_status`/`location_id`, so this column's `DEFAULT 'secret'`
applies). The model may propose `secret`/`public` only; `confirmed` is
creator-reserved, accepted only at apply time. Duplicate guard is
canon-existence (normalized title + `location_id`, same world), never
tick_id/conversation-id equality, and applies to both producers alike.
`session_id`/`batch_id` stay NULL for tick-sourced rows — the sibling
`proposed_mutation` row's `tick_id`/`conversation_id` is the provenance
anchor. Read by `context.py`'s MJ context assembler and the return-visit
delta (TICKET-0016), both filtering `knowledge_status IN
('public','confirmed')` at query construction. `involved_entities` (the
payload key both producers still emit) is relationalized on write into
`event_entity` — see below.

-----

### `event_entity`

`event` <-> entity link (schema v1.79, TICKET-0025, BRIEF-0025-c —
replaces the FK-less `event.involved_entities` JSON id array). Real FK
integrity for the first time; membership queries are joins/EXISTS instead
of a Python `in` over a JSON list.

```sql
CREATE TABLE event_entity (
  id        TEXT PRIMARY KEY,
  event_id  TEXT NOT NULL REFERENCES event(id),
  entity_id TEXT NOT NULL REFERENCES entity(id)
);
CREATE UNIQUE INDEX idx_event_entity_unique ON event_entity(event_id, entity_id);
```

-----

### `artifact`

Magical or historically significant objects.

```sql
CREATE TABLE artifact (
  id                TEXT PRIMARY KEY REFERENCES entity(id),
  owner_id          TEXT REFERENCES entity(id),
  location_id       TEXT REFERENCES entity(id),
  origin            TEXT,
  known_properties  JSON,           -- what it does (or what people think it does)
  actual_behavior   JSON,           -- creator-only
  status            TEXT DEFAULT 'unknown',
                    -- unknown | studied | understood | active | dormant | destroyed
  magic_link        TEXT            -- relationship to magic (if applicable)
);
```

-----

### `item`

Mundane tracked objects — static possession (schema v1.18). Extension of
entity for type `item`.

```sql
CREATE TABLE item (
  id           TEXT PRIMARY KEY REFERENCES entity(id),
  owner_id     TEXT REFERENCES entity(id),   -- NULL = lying in a location
  location_id  TEXT REFERENCES entity(id),   -- NULL = carried (follows owner)
  equipped     BOOLEAN DEFAULT FALSE,
  condition    TEXT DEFAULT 'intact',
  CHECK (NOT equipped OR owner_id IS NOT NULL)
);
```

> Three states, never deletion: equipped (`owner_id` set + `equipped=TRUE`),
> carried but stowed (`owner_id` set + `equipped=FALSE`), lying in a
> location (`owner_id` NULL + `location_id` set). Mundane tracked objects
> live here; `artifact` remains reserved for magical/historically
> significant objects. An item can be promoted to artifact later if the
> fiction demands it.

-----

### `skill_definition`

World-scoped custom skill catalogue (schema v1.63, BRIEF-55). One row = one
custom skill definition for one world; each specialises exactly one of the
four base domains (decision A1). Names only this round — `description` is
authored in chantier 2 and read by no consumer yet.

```sql
CREATE TABLE skill_definition (
  id           TEXT PRIMARY KEY,
  world_id     TEXT NOT NULL REFERENCES world(id),
  name         TEXT NOT NULL,
  base_domain  TEXT NOT NULL,          -- specialises exactly one base domain
               CHECK (base_domain IN ('physical','agility','perception','composure')),
  description  TEXT,                   -- prose; authored in chantier 2, NOT
                                       -- read by any consumer this round
  created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_skill_definition_world_name
  ON skill_definition(world_id, name);
CREATE INDEX idx_skill_definition_world ON skill_definition(world_id);
```

-- NOTE: `UNIQUE(world_id, name)` is the structural guard that makes a name a
-- stable per-world identifier for the MJ-narration vocabulary and the
-- arbiter's candidate list. `base_domain`'s CHECK references the canonical
-- list `BASE_SKILL_DOMAINS` (`models.py`) — the single source of truth for
-- the four base domains (decision 3).

-----

### `skill`

The player character's skill sheet (schema v1.22) — physical/sensory domains
with a tier value and full change history. `skill_definition_id` added
schema v1.63 distinguishes a base-domain row (NULL) from a custom-skill row
(set).

```sql
CREATE TABLE skill (
  id                    TEXT PRIMARY KEY,
  character_id          TEXT NOT NULL REFERENCES entity(id),
  domain                TEXT NOT NULL,
                        -- physical | agility | perception | composure
  tier                  INTEGER NOT NULL DEFAULT 0 CHECK (tier BETWEEN -1 AND 2),
                        -- -1 weak | 0 average | +1 trained | +2 exceptional
                        -- translated directly into the 2d6 modifier (later step)
  change_history        JSON DEFAULT '[]',  -- archived previous states, same
                                             -- pattern as relation.change_history
  skill_definition_id    TEXT REFERENCES skill_definition(id) ON DELETE RESTRICT,
                        -- NULL for the four base-domain rows; set for a
                        -- custom-skill row. `domain` always carries the
                        -- definition's base_domain (so bands/display/CHECK
                        -- keep working); the display name is read by join
                        -- to skill_definition.name, never copied onto this
                        -- row — rename-safe by construction. ON DELETE
                        -- RESTRICT is a structural floor only (chantier 2
                        -- owns the real delete/cascade UX).
  created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at            DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_skill_character ON skill(character_id);
```

-- NOTE: skill rows exist ONLY for player characters in this phase. NPC
-- physical capability is a single tier in character.physical_tier
-- (-1..2, default 0; schema v1.77, TICKET-0025 — moved off
-- entity.metadata). Domains are strictly physical/sensory: social
-- abilities (persuasion, deception, charm) are NEVER skill domains — they
-- belong to the free-dialogue layer and the relation graph. This is a
-- standing design guard, not a deferral.

-----

### `discoverable_detail`

Pre-seeded hidden content per location, revealed by explicit perception
searches (schema v1.26, BRIEF-13). `ambient` rows additionally form
**signpost clusters** with grouped `hidden` content, read by the code-side
silence predicate on location entry (schema v1.30, BRIEF-17).

```sql
CREATE TABLE discoverable_detail (
  id                  TEXT PRIMARY KEY,
  world_id            TEXT NOT NULL REFERENCES world(id),
  location_id         TEXT NOT NULL REFERENCES entity(id),
  subject             TEXT NOT NULL,   -- short tag, e.g. "lettre_innommee"
  content             TEXT NOT NULL,   -- what the player learns on discovery
  access_level        TEXT NOT NULL DEFAULT 'hidden',
                      -- ambient | hidden
                      -- ambient : revealed passively on location entry, no
                      --           roll. ACTIVE since v1.30 — read by the
                      --           code-side silence predicate
                      --           (`active_signposts`), never by an assembler.
                      -- hidden  : requires an explicit search + a successful
                      --           perception roll to reveal
  discovery_threshold INTEGER NOT NULL DEFAULT 0 CHECK (discovery_threshold BETWEEN 0 AND 12),
                      -- ACTIVE (N1): the minimum 2d6+modifier roll total
                      -- required to reveal. Applied as a candidate filter on
                      -- explicit perception searches in _stream(): a detail
                      -- is selectable only when discovery_threshold <= roll
                      -- total. The gate runs only on partial/success
                      -- (total >= 7), so 0-6 all mean "any successful
                      -- search"; 7-12 carve out harder finds up to a
                      -- near-max roll. All candidates above threshold ->
                      -- no row -> [FOUILLE INFRUCTUEUSE] (no leak). Same
                      -- philosophy as knowledge.share_threshold.
  discovered          BOOLEAN NOT NULL DEFAULT FALSE,
                      -- flips TRUE when a discovery new_knowledge mutation for
                      -- this detail is APPLIED (creator-approved), not at
                      -- propose time. Ambient rows never flip this (they are
                      -- never "discovered" — their visibility is the cluster
                      -- predicate below).
  signpost_group      TEXT,
                      -- NULL = no cluster. Clusters one `ambient` panel row
                      -- with N `hidden` content rows that carry the SAME
                      -- signpost_group value (schema v1.30, BRIEF-17, D1: one
                      -- signpost groups N contents, each content in exactly
                      -- one group — no N↔N).
  created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_discoverable_location ON discoverable_detail(location_id);
CREATE INDEX idx_discoverable_world ON discoverable_detail(world_id);
CREATE INDEX idx_discoverable_signpost_group ON discoverable_detail(signpost_group);
```

-- NOTE (narrowed in v1.30 — see world-engine-schema-changelog.md): this table is NEVER read by any
-- context assembler (assemble_mj_context, assemble_npc_context, or any
-- prompt-building path). `hidden` content remains fully excluded from every
-- assembler; it reaches a model only via the explicit post-selection
-- injection in _stream() on a partial/success perception search. `ambient`
-- content is the one consciously narrowed exception: it is read, but only by
-- a pure code predicate (`active_signposts`, context.py) that runs BEFORE any
-- assembler and returns ONLY surviving ambient `content` strings — never a
-- `subject` or `signpost_group`, never through `assemble_mj_context` itself.

-----

### `user`

System accounts (creator + players).

```sql
CREATE TABLE user (
  id            TEXT PRIMARY KEY,
  name          TEXT NOT NULL,
  email         TEXT UNIQUE,
  role          TEXT NOT NULL DEFAULT 'player',
                -- creator | game_master | player
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  is_active     BOOLEAN DEFAULT TRUE
);
-- NOTE on role toggle: a creator account may act in player mode for testing.
-- Injected context depends on the ACTIVE ROLE, not the account: in player mode
-- the app injects only what the player character is meant to know — secrets are
-- hidden from view. This is the same mechanism multiplayer reuses later.
```

-----

### `schema_meta`

Static-plane schema version (C2 two-plane governance, schema v1.86,
TICKET-0044). Singleton row (`CHECK (id = 1)`) recording the DB's applied
static schema version. Migration-only infra, never canon — the ONLY writer
is `scripts/migrate_v1_86_schema_meta.py` (plus `scripts/init_db.py`'s
virgin-head seed). Read by the cockpit's fail-closed boot guard
(`cockpit/app.py`) against `schema_version.EXPECTED_STATIC_SCHEMA_VERSION`;
app startup refuses when the row is absent or the version disagrees. This
is the STATIC plane only — the per-world runtime-type manifest
(`entity_type`, plane 2) is a separate concern and never writes here.

```sql
CREATE TABLE schema_meta (
  id             INTEGER PRIMARY KEY CHECK (id = 1),
  static_version TEXT NOT NULL,
  updated_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

-----

### `prompt_template`

Head/identity row — accessible and editable by the creator. Text lives
exclusively in `prompt_version` (schema v1.68, TICKET-0011); "current" =
`MAX(version_number)` for the head, no pointer column.

```sql
CREATE TABLE prompt_template (
  id               TEXT PRIMARY KEY,
  world_id         TEXT REFERENCES world(id),
  name             TEXT NOT NULL,
  usage            TEXT NOT NULL,
                   -- pass_play_analysis | lore_coherence | event_generation |
                   -- player_narration | session_summary | npc_dialogue |
                   -- conversation_analysis | mj_interpretation |
                   -- overhearing_classification | mj_arbitration |
                   -- mj_establishment | entity_generation | region_manifest |
                   -- mj_gathering | mj_speaker_selection | mj_initiative |
                   -- npc_initiative_act | observation_intent |
                   -- world_generation | player_generation |
                   -- skill_catalogue | other
  destination      TEXT DEFAULT 'local',
                   -- local | claude_api | both
  model            TEXT,            -- NULL = code decides (default_model);
                   -- non-NULL = creator override, consumed by
                   -- prompt_registry.effective_model (BRIEF-0008-a, v1.67)
  is_active        BOOLEAN DEFAULT TRUE,
  notes            TEXT,
  updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

-----

### `prompt_variable`

Declared template variables (schema v1.79, TICKET-0025, BRIEF-0025-c —
replaces `prompt_template.variables` JSON). One row per declared name.
Read by `writes.write_prompt_version`'s C1 fail-closed placeholder
validation (every `{identifier}` in the template text must be declared
here). Curated config: no `change_history`.

```sql
CREATE TABLE prompt_variable (
  id                 TEXT PRIMARY KEY,
  prompt_template_id TEXT NOT NULL REFERENCES prompt_template(id),
  name               TEXT NOT NULL
);
CREATE UNIQUE INDEX idx_prompt_variable_unique
  ON prompt_variable(prompt_template_id, name);
```

-----

### `prompt_version`

Append-only prompt text history (schema v1.68, TICKET-0011). No UPDATE, no
DELETE, ever. The sole read path is `prompt_store.current_prompt`/
`get_version`/`list_versions`; the sole write path is
`writes.write_prompt_version`.

```sql
CREATE TABLE prompt_version (
  id                  TEXT PRIMARY KEY,
  prompt_template_id  TEXT NOT NULL REFERENCES prompt_template(id),
  version_number      INTEGER NOT NULL,
  system_prompt       TEXT NOT NULL,
  user_template       TEXT NOT NULL,   -- user message template (with variables)
  note                TEXT,            -- optional creator note; restore autofills
  created_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_prompt_version_head_number
  ON prompt_version(prompt_template_id, version_number);
CREATE INDEX idx_prompt_version_head ON prompt_version(prompt_template_id);
```

-----

### `visit`

Player location entries, append-only (schema v1.71, TICKET-0016/BRIEF-0016-a).
Anchors the player's last entry per location so `enter_scene` can compute a
return-visit delta (NPCs arrived/departed, public events since). No UPDATE,
no DELETE, ever — a correction is impossible by construction (there is
nothing to correct; a row is a snapshot in time). Born empty on migration —
no backfill, every location counts as a first visit once. NOT a canon table
(`canon_write_policy.txt`) — written directly from `enter_scene`, same
bookkeeping status as `gathering`/`gathering_member`.

```sql
CREATE TABLE visit (
  id                TEXT PRIMARY KEY,
  world_id          TEXT NOT NULL REFERENCES world(id),
  player_id         TEXT NOT NULL REFERENCES entity(id),
  location_id       TEXT NOT NULL REFERENCES entity(id),
  entered_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
  present_npc_ids   JSON   -- public NPC ids present at the moment of entry
);
CREATE INDEX idx_visit_player_location ON visit(player_id, location_id, entered_at);
```

-----

### `agenda`

Structured intrigue (schema v1.72, TICKET-0018/BRIEF-0018-a; owner unlock
schema v1.73, TICKET-0020/BRIEF-0020-a; `paused` schema v1.95, TICKET-0077/
BRIEF-0077-a). `owner_entity_id` is FK-shaped for A2 (location owners stay
rejected) but `write_agenda` enforces an ACTIVE owner of type `faction` OR
`character` — the write helper, not the column, carries the constraint.
Factions keep unlimited concurrent agendas; a `character` owner may hold AT
MOST ONE active agenda at a time (the one-active-personal-agenda invariant),
now enforced at BOTH canon-write sites that can produce an `active` agenda —
`write_agenda` at creation and `write_agenda_status` at transition. A
`character` owner may additionally hold any number of `paused` agendas — a
day plan set aside and resumable later, never terminal, deliberately absent
from `_AGENDA_GOAL_CASCADE_MAP` so parking never cascades onto a linked
`npc_goal`. The tick's faction-scoped scope-event call reads active agendas
via `AGENDA EN COURS` and proposes `agenda_step_change`/`agenda_creation`,
reviewed like any other `proposed_mutation`; the creator authors/edits
agendas directly (first dedicated non-entity CRUD surface,
`/api/agendas`). Per-NPC tick readers for character-owned agendas are
BRIEF-0020-b.

```sql
CREATE TABLE agenda (
  id                TEXT PRIMARY KEY,
  world_id          TEXT NOT NULL REFERENCES world(id),
  owner_entity_id   TEXT NOT NULL REFERENCES entity(id),
  title             TEXT NOT NULL,
  status            TEXT NOT NULL DEFAULT 'active'
                      CHECK (status IN ('active','paused','completed','failed','abandoned')),
  created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
  change_history    JSON DEFAULT '[]'  -- archived previous states, mirror of
                      --                 npc_goal.change_history
);
CREATE INDEX idx_agenda_owner_status ON agenda(owner_entity_id, status);
```

-----

### `agenda_step`

Ordered step of an `agenda`, schema v1.72, TICKET-0018/BRIEF-0018-a. The
model never addresses a step directly — it names the agenda by TITLE; the
active step is always derived in code (this table's partial unique index
guarantees at most one). Advancement (`complete` -> next step active / agenda
completed; `fail` -> whole agenda failed) is CODE, at apply.

`cost`/`domain` (schema v1.94, TICKET-0075, BRIEF-0075-b): day-plan budget
metadata. NULL for every pre-v1.94 (NPC) step — no backfill; populated only
by the day-plan chain. `cost` = day-budget slots consumed (1-4); `domain` =
the `resolve_physical` domain, or NULL when the step needs no roll. No
location column here or ever (the positional wall,
BRIEF-0074-a-amendment-1) — `agenda_step_requirement`'s `location_reachable`
rows carry a location on the REQUIREMENT, never on the step.

```sql
CREATE TABLE agenda_step (
  id                TEXT PRIMARY KEY,
  agenda_id         TEXT NOT NULL REFERENCES agenda(id),
  step_order        INTEGER NOT NULL,
  objective         TEXT NOT NULL,
  status            TEXT NOT NULL DEFAULT 'pending'
                      CHECK (status IN ('pending','active','completed','failed')),
  outcome           TEXT,
  visibility_trace  TEXT,
  cost              INTEGER CHECK (cost IS NULL OR cost BETWEEN 1 AND 4),
  domain            TEXT,
  created_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME DEFAULT CURRENT_TIMESTAMP,
  change_history    JSON DEFAULT '[]'
);
CREATE INDEX idx_agenda_step_agenda ON agenda_step(agenda_id, step_order);
-- STRUCTURAL invariant (RECON-0018 F2): at most ONE active step per agenda,
-- enforced by SQLite itself — never by discipline.
CREATE UNIQUE INDEX idx_agenda_step_one_active
  ON agenda_step(agenda_id) WHERE status = 'active';
```

-----

### `agenda_step_requirement`

Day-plan precondition gate on one `agenda_step` (schema v1.94, TICKET-0075,
BRIEF-0075-b). `goal_prerequisite` shape precedent, widened to a closed
four-form vocabulary (`knowledge`, `relation_gte`, `resource`,
`location_reachable`) and a `target_key` column for the two forms that gate
on a string (a knowledge subject, a resource tag) rather than an entity. The
per-type shape CHECK is the structural guarantee that an ill-formed row
cannot exist: `relation_gte`/`location_reachable` require `target_entity_id`
NOT NULL; `knowledge`/`resource` require `target_key` NOT NULL;
`relation_gte`/`resource` require `threshold` NOT NULL. Curated plan
metadata, same family as `npc_schedule` — no `change_history`. THE
POSITIONAL WALL: `location_reachable`'s target lives HERE, never on
`agenda_step` — a requirement states "the player must be able to reach L", a
precondition on the player, never a position of an NPC (see
BRIEF-0074-a-amendment-1). Written only by `writes.write_day_plan`, read
only by `day_plan.evaluate_requirements`.

```sql
CREATE TABLE agenda_step_requirement (
  id                TEXT PRIMARY KEY,
  world_id          TEXT NOT NULL REFERENCES world(id),
  step_id           TEXT NOT NULL REFERENCES agenda_step(id),
  type              TEXT NOT NULL
                      CHECK (type IN ('knowledge','relation_gte','resource','location_reachable')),
  target_entity_id  TEXT REFERENCES entity(id),
  target_key        TEXT,
  threshold         INTEGER,
  CHECK (
    (type NOT IN ('relation_gte','location_reachable') OR target_entity_id IS NOT NULL)
    AND (type NOT IN ('knowledge','resource') OR target_key IS NOT NULL)
    AND (type NOT IN ('relation_gte','resource') OR threshold IS NOT NULL)
  )
);
CREATE UNIQUE INDEX idx_agenda_step_requirement_unique
  ON agenda_step_requirement(step_id, type, target_entity_id, target_key);
```

-----

### `goal_agenda_link`

Many-to-many tie between an `npc_goal` and the `agenda` intrigue(s) it
serves (B3 grain: the AGENDA, never the step — a goal may serve several
intrigues at once), schema v1.73, TICKET-0020/BRIEF-0020-a. No
`change_history`: link rows are immutable facts whose only transition is
the soft detach, fully audited by `detached_at`/`detached_by` (the
`faction_membership.left_at` precedent) — there is no DELETE path.
`write_agenda_status` cascades onto linked goals when an agenda exits
`active` (E2+M1 mapping: `completed` -> goal `completed`; `failed`/
`abandoned` -> goal `abandoned`), but ONLY for a goal whose link to the
closing agenda is its LAST still-active parent link (last-parent rule) —
a goal with another active link survives. Cascaded transitions go through
`write_npc_goal_status` with `changed_by='cascade:agenda:<id>:<status>'`.

```sql
CREATE TABLE goal_agenda_link (
  id            TEXT PRIMARY KEY,
  world_id      TEXT NOT NULL REFERENCES world(id),
  goal_id       TEXT NOT NULL REFERENCES npc_goal(id),
  agenda_id     TEXT NOT NULL REFERENCES agenda(id),
  created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
  created_by    TEXT NOT NULL,   -- 'creator' or 'mutation:<id>'
  detached_at   DATETIME,        -- NULL = active, never erased
  detached_by   TEXT
);
CREATE INDEX idx_goal_agenda_link_goal ON goal_agenda_link(goal_id);
CREATE INDEX idx_goal_agenda_link_agenda ON goal_agenda_link(agenda_id);
-- STRUCTURAL invariant: at most one ACTIVE link per goal/agenda pair,
-- enforced by SQLite itself (idx_membership_unique_active precedent) — a
-- detached pair may be re-attached.
CREATE UNIQUE INDEX idx_goal_agenda_link_active
  ON goal_agenda_link(goal_id, agenda_id) WHERE detached_at IS NULL;
```

-----

### `link_batch`

-- NOTE: link_batch / link_batch_row are EPHEMERAL stratum
(TICKET-0036): staging for the NPC link agent. Never listed in
canon_write_policy.txt, never a proposed_mutation, never
creator-CRUD-reviewed as canon. Purge of closed batches (retention:
last 2) is legal by construction -- the append-only generation
journal under ~/.world_engine/link_agent_journal/ carries long
memory. History-is-sacred governs canon, not this plumbing.

```sql
CREATE TABLE link_batch (
  id               TEXT PRIMARY KEY,
  world_id         TEXT NOT NULL REFERENCES world(id),
  status           TEXT NOT NULL DEFAULT 'open',
                   -- open | committed | abandoned
  scope            JSON NOT NULL,
                   -- {root_location_ids, expanded_location_ids,
                   --  npc_ids, pair_count}
  pairs_total      INTEGER NOT NULL DEFAULT 0,
  pairs_done       INTEGER NOT NULL DEFAULT 0,
  coherence_status TEXT,          -- NULL | ran | partial
  coherence_findings JSON DEFAULT '[]',
  created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
  closed_at        DATETIME
);
```

-----

### `link_batch_row`

One staged relation/knowledge proposal (or an explicit "no links" verdict)
between a pair of NPCs in an open or closed `link_batch`. Ephemeral
stratum, same non-canon status as `link_batch` (see NOTE above).

```sql
CREATE TABLE link_batch_row (
  id          TEXT PRIMARY KEY,
  batch_id    TEXT NOT NULL REFERENCES link_batch(id),
  pair_a_id   TEXT NOT NULL REFERENCES entity(id),
  pair_b_id   TEXT NOT NULL REFERENCES entity(id),
  kind        TEXT NOT NULL,   -- relation | knowledge | no_links
  payload     JSON NOT NULL,   -- full proposed field set; {} for no_links
  row_status  TEXT NOT NULL DEFAULT 'proposed',
              -- proposed | edited | rejected | committed
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_link_batch_row_batch ON link_batch_row(batch_id);
```

-----

### `npc_batch`

-- NOTE: npc_batch / npc_batch_row are EPHEMERAL stratum
(TICKET-0037): staging for the NPC group agent. Never listed in
canon_write_policy.txt, never a proposed_mutation, never
creator-CRUD-reviewed as canon. Purge of closed batches (retention:
last 2) is legal by construction -- the append-only generation
journal under ~/.world_engine/npc_agent_journal/ carries long
memory. History-is-sacred governs canon, not this plumbing.

```sql
CREATE TABLE npc_batch (
  id          TEXT PRIMARY KEY,
  world_id    TEXT NOT NULL REFERENCES world(id),
  status      TEXT NOT NULL DEFAULT 'open',
              -- open | committed | abandoned
  scope       JSON NOT NULL,
              -- {root_location_id, expanded_location_ids, lines,
              --  group_brief}
              -- lines = [{count, description, faction_id, location_id}]
              -- (faction_id/location_id nullable)
  npcs_total  INTEGER NOT NULL DEFAULT 0,
  npcs_done   INTEGER NOT NULL DEFAULT 0,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  closed_at   DATETIME
);
```

-----

### `npc_batch_row`

One staged NPC draft (or an explicit generation failure) produced by a
spec line in an open or closed `npc_batch`. Ephemeral stratum, same
non-canon status as `npc_batch` (see NOTE above).

```sql
CREATE TABLE npc_batch_row (
  id          TEXT PRIMARY KEY,
  batch_id    TEXT NOT NULL REFERENCES npc_batch(id),
  line_index  INTEGER NOT NULL,   -- which spec line produced this NPC
  kind        TEXT NOT NULL,      -- draft | failed
  payload     JSON NOT NULL,
              -- full draft (public/secret), resolved location_id, goals
              -- block, notes list; {} + reason for failed
  row_status  TEXT NOT NULL DEFAULT 'proposed',
              -- proposed | edited | rejected | committed
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_npc_batch_row_batch ON npc_batch_row(batch_id);
```

-----

### `observation_run`

Observed-scene instrumentation (schema v1.90, TICKET-0051, BRIEF-0051-a): a
creator watches NPCs act among themselves rather than playing. Telemetry,
never canon — absent from `canon_write_policy.txt`'s `[CANON_TABLES]`. The
single write chokepoint is `observation_writes.py`; a lasting consequence of
an observed run reaches the world only through `proposed_mutation` under
creator approval, exactly like a played scene. Append-only except this
table's own terminal `status`/`stop_reason`/`ended_at`, set exactly once by
`close_observation_run`.

```sql
CREATE TABLE observation_run (
  id                 TEXT PRIMARY KEY,
  world_id           TEXT NOT NULL REFERENCES world(id),
  location_id        TEXT NOT NULL REFERENCES entity(id),
  gathering_id       TEXT REFERENCES gathering(id),
  player_presence    TEXT NOT NULL DEFAULT 'absent',
                                       -- absent | silent | active
  max_beats          INTEGER NOT NULL,
  quiescence_limit   INTEGER NOT NULL,
  mj_narration       BOOLEAN NOT NULL DEFAULT FALSE,
  cooldown_beats     INTEGER NOT NULL,
  debt_weight        REAL NOT NULL,
  propensity_mode    TEXT NOT NULL,     -- flat | relation_weighted
  model              TEXT NOT NULL,
  status             TEXT NOT NULL DEFAULT 'running',
                                       -- running | completed | stopped | failed
  stop_reason        TEXT,             -- max_beats | quiescence | creator_stop | error
  started_at         DATETIME DEFAULT CURRENT_TIMESTAMP,
  ended_at           DATETIME
);
CREATE INDEX idx_observation_run_world    ON observation_run(world_id);
CREATE INDEX idx_observation_run_location ON observation_run(location_id);

-- NOTE: player_presence is a closed vocabulary, not a boolean, because a
--       SILENT player is still an AUDITOR for disclosure gating (E2) while
--       an ABSENT one is not. Only 'absent' is implemented at v1.90;
--       'silent' and 'active' are named deferrals (TICKET-0051, H2) and the
--       runner refuses them explicitly rather than silently treating them
--       as 'absent'.
-- NOTE: cooldown_beats / debt_weight / propensity_mode are pinned PER RUN,
--       not read from code constants, so that two runs separated by a tuning
--       pass remain attributable. They are not a replay mechanism: the world
--       mutates under play and bit-exact replay is out of scope by decision.
```

-----

### `observation_run_template`

Per-usage prompt pinning (L): which template `id` + `version` a run used for
each prompt usage, so two runs separated by a template edit stay comparable.

```sql
CREATE TABLE observation_run_template (
  id            TEXT PRIMARY KEY,
  run_id        TEXT NOT NULL REFERENCES observation_run(id),
  usage         TEXT NOT NULL,
  template_id   TEXT NOT NULL,
  version       INTEGER NOT NULL
);
CREATE UNIQUE INDEX idx_observation_run_template_unique
  ON observation_run_template(run_id, usage);
```

-----

### `observation_beat`

One row per beat of an observed run.

```sql
CREATE TABLE observation_beat (
  id             TEXT PRIMARY KEY,
  run_id         TEXT NOT NULL REFERENCES observation_run(id),
  beat_index     INTEGER NOT NULL,
  outcome        TEXT NOT NULL,        -- acted | silence | degraded | event
  actor_id       TEXT REFERENCES entity(id),
  line           TEXT,
  mj_narration   TEXT,
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_observation_beat_unique
  ON observation_beat(run_id, beat_index);

-- NOTE: outcome is explicit and never inferred from actor_id being NULL.
--       'silence'  = every candidate declined (a datum: passivity mode (a))
--       'degraded' = every intent call failed (a bug, not a datum)
--       'event'    = a creator-injected event line (no NPC actor)
--       Conflating the first two would let a JSON parse failure be read as
--       "the NPCs are passive" — the exact misreading this table exists to
--       prevent.
```

-----

### `observation_intent`

One row per NPC per beat, ALWAYS written, including on a failed model call.

```sql
CREATE TABLE observation_intent (
  id                TEXT PRIMARY KEY,
  run_id            TEXT NOT NULL REFERENCES observation_run(id),
  beat_id           TEXT NOT NULL REFERENCES observation_beat(id),
  npc_id            TEXT NOT NULL REFERENCES entity(id),
  act               BOOLEAN NOT NULL DEFAULT FALSE,
  urgency           INTEGER,
  target_id         TEXT REFERENCES entity(id),
  why               TEXT,
  propensity        REAL NOT NULL,
  cooldown_active   BOOLEAN NOT NULL,
  debt_score        REAL NOT NULL,
  final_score       REAL NOT NULL,
  selected          BOOLEAN NOT NULL DEFAULT FALSE,
  call_status       TEXT NOT NULL,     -- ok | parse_error | timeout | error
  latency_ms        INTEGER,
  raw_response      TEXT,
  created_at        DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX idx_observation_intent_unique
  ON observation_intent(beat_id, npc_id);
CREATE INDEX idx_observation_intent_run ON observation_intent(run_id);

-- NOTE: there is deliberately NO not_selected_reason column. A candidate can
--       be excluded by cooldown AND by debt AND by arbitration at once; a
--       single-valued reason would force a precedence and destroy the rest of
--       the information. The COMPONENTS are stored (propensity,
--       cooldown_active, debt_score, final_score) and the reason is DERIVED
--       at read time by a documented precedence:
--         act = FALSE                       -> no_intent
--         cooldown_active = TRUE            -> cooldown
--         selected = FALSE, debt_score < 0  -> debt
--         otherwise                         -> lost_arbitration
--       The arbitration is therefore reconstructible, not merely reported.
-- NOTE: a row is written for every candidate on every beat, including when
--       the model call fails (call_status != 'ok'). A missing row is a bug,
--       never a silent decline.
-- NOTE: latency_ms and raw_response have a DIFFERENT reader from the rest of
--       this table: run feasibility (does a 5-NPC / 30-beat run stay
--       tractable) and parse diagnosis. They are not scene-analysis columns.
```

-----

### `observation_mutation_link`

Provenance without altering a canon table: joins a `proposed_mutation` back
to the run/beat that produced it. `proposed_by = 'observed_scene'` on the
`proposed_mutation` row carries the FILTER; this table carries the JOIN.

```sql
CREATE TABLE observation_mutation_link (
  id            TEXT PRIMARY KEY,
  run_id        TEXT NOT NULL REFERENCES observation_run(id),
  beat_id       TEXT REFERENCES observation_beat(id),
  mutation_id   TEXT NOT NULL REFERENCES proposed_mutation(id)
);
CREATE UNIQUE INDEX idx_observation_mutation_link_unique
  ON observation_mutation_link(mutation_id);
```

**Writer (BRIEF-0051-e, no schema change).** `observation_runner.py`'s
`produce_run_proposals` is the first and only writer of this table (via
`observation_writes.link_observation_mutation`): once per closed run, one
row per proposal the -c seam returns over that run's transcript, `beat_id`
left NULL (provenance is at the run grain here, not per-beat).

**`proposed_mutation.payload["source"]` format boundary (BRIEF-0051-c, no
schema change).** The overhearing pass (`proposed_by = 'local_ai_overhearing'`)
writes a `"source"` key inside `payload` for provenance. Rows written before
schema v1.90 carry `overheard:{conversation_id}:{speaker_id}`; rows written
from v1.90 onward carry `overheard:{speaker_id}` only — the
`conversation_id` segment was a duplicate of the `conversation_id` column,
which the caller now always populates (`analyzer.py`'s `analyze_window` /
`analyze_overhearing`). History is append-only: existing rows are never
migrated to the new format; a reader must not assume either shape.

-----

## INDEXES

Created alongside the tables. They change nothing functionally — they keep the
most frequent lookups fast as data grows. Add them now while the database is empty.

```sql
-- entities scoped to a world, and by type
CREATE INDEX idx_entity_world        ON entity(world_id);
CREATE INDEX idx_entity_type         ON entity(type);

-- "everything entity X knows"
CREATE INDEX idx_knowledge_entity    ON knowledge(entity_id);

-- "who (if anyone) holds subject S" (schema v1.96, BRIEF-0078-a) — the
-- knowledge-gate anchoring lookup, day_plan._anchorable_subjects
CREATE INDEX idx_knowledge_subject   ON knowledge(subject);

-- "this NPC's active goals" (schema v1.69, BRIEF-0013-a)
CREATE INDEX idx_npc_goal_npc_status ON npc_goal(npc_id, status);

-- "every relation touching entity X" (both directions)
CREATE INDEX idx_relation_a          ON relation(entity_a_id);
CREATE INDEX idx_relation_b          ON relation(entity_b_id);
CREATE INDEX idx_relation_world      ON relation(world_id);

-- character lookups by location and owning user
CREATE INDEX idx_character_location  ON character(current_location_id);
CREATE INDEX idx_character_user      ON character(user_id);
CREATE INDEX idx_character_world     ON character(world_id);

-- one player character per user per world (BRIEF-46), multiplayer-safe
CREATE UNIQUE INDEX idx_character_one_pc_per_user_world
  ON character(world_id, user_id) WHERE character_type = 'player';

-- location hierarchy traversal
CREATE INDEX idx_location_parent     ON location(parent_location_id);

-- gatherings: by location (who's clustered where) and by session
CREATE INDEX idx_gathering_location  ON gathering(location_id);
CREATE INDEX idx_gathering_session   ON gathering(session_id);

-- gathering rosters: by group and by member entity
CREATE INDEX idx_gathering_member_group  ON gathering_member(gathering_id);
CREATE INDEX idx_gathering_member_entity ON gathering_member(entity_id);

-- conversations attached to a gathering
CREATE INDEX idx_conversation_gathering ON conversation(gathering_id);

-- conversation transcript, fetched in order
CREATE INDEX idx_message_conversation ON conversation_message(conversation_id);

-- the mutation review queue, filtered by status and source
CREATE INDEX idx_mutation_status     ON proposed_mutation(status);
CREATE INDEX idx_mutation_passplay   ON proposed_mutation(pass_play_id);
CREATE INDEX idx_mutation_conversation ON proposed_mutation(conversation_id);
CREATE INDEX idx_mutation_tick       ON proposed_mutation(tick_id);

-- pass-plays grouped into a batch
CREATE INDEX idx_passplay_batch      ON pass_play(batch_id);

-- events and conversations scoped to a session / world
CREATE INDEX idx_event_world         ON event(world_id);
CREATE INDEX idx_conversation_world  ON conversation(world_id);

-- items: by owner (carried/equipped) and by location (lying around)
CREATE INDEX idx_item_owner    ON item(owner_id);
CREATE INDEX idx_item_location ON item(location_id);

-- skill sheet rows, by character
CREATE INDEX idx_skill_character ON skill(character_id);

-- discoverable details: by location (search reveals), by world, and by
-- signpost cluster (entry-narration silence predicate)
CREATE INDEX idx_discoverable_location ON discoverable_detail(location_id);
CREATE INDEX idx_discoverable_world    ON discoverable_detail(world_id);
CREATE INDEX idx_discoverable_signpost_group ON discoverable_detail(signpost_group);

-- "the player's latest visit to this location" (schema v1.71, BRIEF-0016-a)
CREATE INDEX idx_visit_player_location ON visit(player_id, location_id, entered_at);

-- agendas: by owner + status (schema v1.72, BRIEF-0018-a)
CREATE INDEX idx_agenda_owner_status ON agenda(owner_entity_id, status);

-- agenda steps: ordered within an agenda, and the one-active-step invariant
CREATE INDEX idx_agenda_step_agenda ON agenda_step(agenda_id, step_order);
CREATE UNIQUE INDEX idx_agenda_step_one_active
  ON agenda_step(agenda_id) WHERE status = 'active';
```

-----

## KEY RELATIONS

```
world
  └── entity (everything)
        ├── character
        ├── faction
        ├── location (hierarchical)
        └── artifact

entity ←→ entity : relation (universal graph)
entity  →  knowledge (what it knows)

session
  ├── batch
  │     └── pass_play (per character) ──┐
  └── conversation (live)               │
        └── conversation_message        │
        └──────────────────────────────► proposed_mutation (unified pipeline)
                                          │
                                  creator approval → applied to world

session → event
batch   → event
```

-----

## MIGRATION NOTES

**Local phase:** SQLite, single file, zero configuration.

**Multiplayer phase:** migration to Supabase.

- `TEXT PRIMARY KEY` with UUIDs is compatible on both sides.
- `JSON` columns become `JSONB` in PostgreSQL — performance gain.
- Only environment variables change, not application code.

-----


