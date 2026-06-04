# WORLD ENGINE — Database Schema

*Version 1.3 — Local phase (SQLite → Supabase)*

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
  fundamental_laws      JSON,          -- world rules (magic, physics, etc.)
  magic_status          TEXT DEFAULT 'dormant',
                                       -- dormant | awakening | active | suppressed
  created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at            DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

-----

### `entity`

Central table. Anything that can have relations or knowledge is an entity.

```sql
CREATE TABLE entity (
  id            TEXT PRIMARY KEY,
  world_id      TEXT NOT NULL REFERENCES world(id),
  type          TEXT NOT NULL,
                -- character | faction | location | concept | magic | artifact | other
  name          TEXT NOT NULL,
  internal_name TEXT,                  -- creator-only name (ex: "The Unnamed")
  description   TEXT,
  is_public     BOOLEAN DEFAULT TRUE,  -- FALSE = existence denied or secret
  status        TEXT DEFAULT 'active', -- active | inactive | destroyed | missing
  metadata      JSON,                  -- type-specific data
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
  faction_id      TEXT REFERENCES entity(id),   -- primary faction
  character_type  TEXT NOT NULL,                -- player | npc
  user_id         TEXT,                         -- NULL for NPCs
  current_location_id TEXT REFERENCES entity(id),
  vital_status    TEXT DEFAULT 'alive',         -- alive | dead | missing | unknown
  appearance      TEXT,
  backstory       TEXT,
  secrets         JSON                          -- creator-only
);
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
  subculture        JSON,     -- values, habits, collective memory, rumors
  magic_status      TEXT DEFAULT 'inert',
                    -- inert | sensitive | active | nexus
  coordinates       JSON,     -- for future mapping
  access_level      TEXT      -- public | restricted | secret
);
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
  internal_tensions     TEXT
);
```

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
                      -- indifference | rejection | passive_attention | other
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
  session_id       TEXT             -- acquired during which session
);
-- NOTE: when the NPC has no relation toward the interlocutor, the assembler
--       treats the relation as neutral (intensity 50). A row therefore shares
--       by default (threshold 50) and only becomes warmth-gated when its
--       share_threshold is raised above 50.
```

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
  status                TEXT DEFAULT 'pending',
                        -- pending | local_analysis | ready_checkpoint_1 |
                        -- approved_checkpoint_1 | sent_to_claude |
                        -- received_from_claude | ready_checkpoint_2 |
                        -- approved_checkpoint_2 | applied
  local_summary         TEXT,          -- summary generated by local AI
  message_to_claude     TEXT,          -- editable at checkpoint 1
  claude_raw_response   TEXT,          -- raw Claude API response
  final_result          TEXT,          -- edited at checkpoint 2
  creator_notes         TEXT,
  created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
  processed_at          DATETIME,
  applied_at            DATETIME
);
```

-----

### `pass_play`

An action declared by a player between two sessions.

```sql
CREATE TABLE pass_play (
  id                  TEXT PRIMARY KEY,
  batch_id            TEXT NOT NULL REFERENCES batch(id),
  session_id          TEXT NOT NULL REFERENCES session(id),
  character_id        TEXT NOT NULL REFERENCES entity(id),
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

### `conversation`

A live player ↔ NPC exchange, anchored to a location and a session.

```sql
CREATE TABLE conversation (
  id               TEXT PRIMARY KEY,
  world_id         TEXT NOT NULL REFERENCES world(id),
  session_id       TEXT NOT NULL REFERENCES session(id),
  location_id      TEXT REFERENCES entity(id),         -- where it happens
  player_id        TEXT NOT NULL REFERENCES entity(id), -- the player character
  npc_id           TEXT NOT NULL REFERENCES entity(id), -- the NPC being spoken to
  status           TEXT DEFAULT 'open',
                   -- open | closed | archived
  injected_context JSON,    -- snapshot of the NPC context used to drive dialogue
                            -- (what the NPC was allowed to know — for audit/replay)
  started_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
  ended_at         DATETIME
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
  speaker         TEXT NOT NULL,           -- player | npc
  speaker_id      TEXT REFERENCES entity(id),  -- which entity spoke
  content         TEXT NOT NULL,           -- the line itself
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

-----

### `proposed_mutation`

A single atomic change to world state, awaiting creator approval. Produced by both pass-plays and live conversations — the unified validation pipeline.

```sql
CREATE TABLE proposed_mutation (
  id              TEXT PRIMARY KEY,
  world_id        TEXT NOT NULL REFERENCES world(id),

  -- source: exactly one of these is set
  source_type     TEXT NOT NULL,           -- pass_play | conversation
  pass_play_id    TEXT REFERENCES pass_play(id),
  conversation_id TEXT REFERENCES conversation(id),

  -- what kind of change
  mutation_type   TEXT NOT NULL,
                  -- relation_change | new_knowledge | knowledge_change |
                  -- event_creation | status_change | entity_creation | other
  target_table    TEXT,                    -- table the change applies to
  target_id       TEXT,                    -- row affected (NULL if creation)
  payload         JSON NOT NULL,           -- the proposed change, structured

  -- control
  status          TEXT DEFAULT 'proposed',
                  -- proposed | approved | rejected | applied
  rationale       TEXT,                    -- why the AI proposed it (raw draft text)
  creator_notes   TEXT,                    -- creator edit/justification
  proposed_by     TEXT DEFAULT 'local_ai', -- local_ai | claude | creator
  proposed_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  reviewed_at     DATETIME,
  applied_at      DATETIME
);
-- status = 'applied' is set only after the creator approves AND the change is
-- written to the real table. Until then, world state is untouched.
```

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
  involved_entities     JSON,     -- list of entity_id with their role
  location_id           TEXT REFERENCES entity(id),
  has_magic_impact      BOOLEAN DEFAULT FALSE,
  consequences          JSON,     -- changes applied to the world
  occurred_at           DATETIME,
  recorded_at           DATETIME DEFAULT CURRENT_TIMESTAMP
);
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

### `prompt_template`

The master prompts — accessible and editable by the creator.

```sql
CREATE TABLE prompt_template (
  id               TEXT PRIMARY KEY,
  world_id         TEXT REFERENCES world(id),
  name             TEXT NOT NULL,
  usage            TEXT NOT NULL,
                   -- pass_play_analysis | lore_coherence | event_generation |
                   -- player_narration | session_summary | npc_dialogue |
                   -- conversation_analysis | other
  system_prompt    TEXT NOT NULL,
  user_template    TEXT NOT NULL,   -- user message template (with variables)
  variables        JSON,            -- expected variable list
  destination      TEXT DEFAULT 'local',
                   -- local | claude_api | both
  version          INTEGER DEFAULT 1,
  is_active        BOOLEAN DEFAULT TRUE,
  notes            TEXT,
  updated_at       DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

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

-- "every relation touching entity X" (both directions)
CREATE INDEX idx_relation_a          ON relation(entity_a_id);
CREATE INDEX idx_relation_b          ON relation(entity_b_id);
CREATE INDEX idx_relation_world      ON relation(world_id);

-- character lookups by faction, location, and owning user
CREATE INDEX idx_character_faction   ON character(faction_id);
CREATE INDEX idx_character_location  ON character(current_location_id);
CREATE INDEX idx_character_user      ON character(user_id);

-- location hierarchy traversal
CREATE INDEX idx_location_parent     ON location(parent_location_id);

-- conversation transcript, fetched in order
CREATE INDEX idx_message_conversation ON conversation_message(conversation_id);

-- the mutation review queue, filtered by status and source
CREATE INDEX idx_mutation_status     ON proposed_mutation(status);
CREATE INDEX idx_mutation_passplay   ON proposed_mutation(pass_play_id);
CREATE INDEX idx_mutation_conversation ON proposed_mutation(conversation_id);

-- pass-plays grouped into a batch
CREATE INDEX idx_passplay_batch      ON pass_play(batch_id);

-- events and conversations scoped to a session / world
CREATE INDEX idx_event_world         ON event(world_id);
CREATE INDEX idx_conversation_world  ON conversation(world_id);
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

## CHANGELOG

- **v1.4** — No new tables or columns. Added `conversation_analysis` to the documented `prompt_template.usage` values (the column is TEXT — the value was already valid, this is a doc-only update). The post-conversation analysis pipeline (`analyze_conversation.py` + `analyzer.py`) is now implemented; see `ARCHITECTURE_DECISIONS.md` for the circuit description.
- **v1.3** — Added `knowledge.share_threshold` (INTEGER DEFAULT 50, CHECK 1–100): the minimum NPC→interlocutor relation intensity required to share a non-secret knowledge row in conversation; ignored when `is_secret = TRUE`. Recorded the convention that an absent NPC→interlocutor relation is treated as neutral (50) by the assembler.
- **v1.2** — Added `conversation`, `conversation_message`, and `proposed_mutation` for live sessions and the unified mutation pipeline. Removed `pass_play.local_proposal`. Documented the role-toggle rule on `user`. Added `npc_dialogue` to prompt usages. Changed `relation.intensity` to a 1–100 scale (default 50 = neutral) with a clamp-on-apply rule. Added `updated_at` to `entity` and `knowledge`. Added an INDEXES section for frequent lookups. Schema translated to English.
- **v1.1** — Initial local-phase schema.

*Version 1.4 — Co-built with Claude, June 2026*
