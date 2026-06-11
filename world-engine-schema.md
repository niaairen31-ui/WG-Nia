# WORLD ENGINE — Database Schema

*Version 1.11 — Local phase (SQLite → Supabase)*

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
-- NOTE on `secrets` vs `knowledge.is_secret`: `character.secrets` holds
-- creator meta-narrative ABOUT the character (true nature, planned reveal
-- arcs, creator intentions). It is NEVER read by any context assembler.
-- What a character knows-but-conceals is modeled as `knowledge` rows with
-- `is_secret = TRUE`, structurally excluded by the assembler. Suggested
-- shape: {"secrets": [{"id", "content", "category", "narrative_role",
-- "creator_notes"}]} — free-form, engine-invisible.

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
  proposed_by     TEXT DEFAULT 'local_ai', -- local_ai          : final-pass analysis
                                           -- local_ai_immediate : per-turn analysis
                                           --                      (fires after each turn,
                                           --                       owns all relation_change)
                                           -- local_ai_overhearing : Tier 4 overhearing
                                           --                      pass (acquisition-only,
                                           --                      new_knowledge only)
                                           -- claude | creator
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
                   -- conversation_analysis | mj_interpretation |
                   -- overhearing_classification | other
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

- **v1.16** — Added `knowledge.change_history` (JSON DEFAULT '[]'), an exact
  mirror of `relation.change_history`. CRUD debt fix (same class as the
  retroactive `relation` fix in v1.11): `writes.write_knowledge` now appends
  the row's previous state — `level`, `content`, `source`, `is_incorrect`,
  `updated_at`, plus `changed_by` (`"creator_crud"` | `"apply_mutation"`) and
  `changed_at` — to `change_history` via the new `_append_knowledge_history`
  helper before any in-place update. Existing rows start with `[]`; no
  backfill (past edits are unrecoverable). Row creation and deletion are
  unaffected. The helper is shared and ready for `knowledge_change` apply
  support, which arrives in the following step (not implemented here).
- **v1.15** — No new tables or columns. Comment-level changes only:
  documented `local_ai_overhearing` as a third AI source tag on
  `proposed_mutation.proposed_by` (Tier 4 overhearing pass — bystanders
  acquire knowledge from a turn, acquisition-only, never level upgrades) and
  `overhearing_classification` in the `prompt_template.usage` list. Deferred
  decision: **E3-general upgrade rule** (`knowledge_change` apply + upgrade
  detection) is the next step; speaker-level cap at `knows` for direct
  affirmation belongs to that step.
- **v1.14** — No new tables or columns. Application-layer **cockpit batch
  review** (`POST /api/mutations/batch-review`, cockpit `app.py`): the review
  queue gains per-row checkboxes (rendered only for `status = 'proposed'`
  rows) plus a "select all / none" toggle and "Approve selected" / "Reject
  selected" buttons. The endpoint processes the selected ids sequentially,
  re-checking each row's status (`!= 'proposed'` → skipped, never touched —
  history is sacred), and routes approve through the existing
  `_apply_mutation` (same SAVEPOINT, duplicate guard, and "Needs attention"
  fallback as unit approve) and reject through the same field updates as unit
  reject. Processed rows get the literal `batch-review` marker appended to
  `creator_notes`. Returns verdict counts (`applied` / `needs_attention` /
  `skipped`, or `rejected` / `skipped`). Deferred decision: payload editing in
  batch is deliberately excluded — editing means unit review.
- **v1.13** — No new tables or columns. Application-layer **creator travel
  control** (`POST /api/travel`, cockpit `app.py`): a clean location
  transition for the player — closes any open `conversation` (status →
  `closed`, `ended_at` set), closes the player's open `gathering_member`
  row(s) (`left_at` set; NPC members untouched), then updates
  `character.current_location_id`, all in one transaction. No-op if the
  destination equals the current location; rejected (400, no state change)
  if the destination is not a `location` entity of the player's world. Does
  not call `generate_gatherings` / `enter_location` — the existing
  scene-entry transition-detection flow remains the sole owner of gathering
  generation. Narrative travel (`travel` response mode, adjacency model) is
  out of scope, deferred to E2.
- **v1.12** — No new tables or columns. Three application-layer changes
  (BRIEF-03-assembler-prompts, scope D-b3):
  — **Sign rubric for `relation_change`**: `pt-conversation-analysis`
  (`usage='conversation_analysis'`, used by both `analyze_conversation` and
  `analyze_single_turn`) gains an explicit sign rubric — hostility, violence,
  threats, discovered deception, and humiliation are always NEGATIVE; physical
  contact is judged by intent (an embrace warms, a shove or brawl is
  NEGATIVE); helping, defending, gift-giving, and shared danger are POSITIVE
  — plus contrastive mini-examples. Bumped to `version=2`, delivered via
  `seed_pilot.py` upsert (the template moved from `get_or_create` to
  `upsert_prompt_template`).
  — **`relevance_hint` reserved parameter**: `assemble_npc_context` and the
  new `assemble_mj_context` both accept an optional `relevance_hint: str |
  None = None`, accepted and currently ignored. Deferred-decision note: a
  future relevance-selection stage may only NARROW the security-scoped
  context, never widen it — inert until context size measurably hurts.
  — **MJ context assembler** (`assemble_mj_context` in `context.py`): a new,
  deterministic, scoped context for the MJ narration layer — the player's
  perception boundary. Three static parts (location name/description +
  allow-listed `subculture` ambiance, excluding `magic_status`; the player
  character's own `knowledge` rows; up to 5 most recent `event` rows with
  `knowledge_status IN ('public','confirmed')`, location-matched first) plus
  one dynamic part (co-present NPCs' public name + description, read fresh
  from the gathering roster — `gathering_member` with `left_at IS NULL`).
  Structural exclusions (by query construction): no NPC `knowledge`, no
  `character.secrets`, no `entity.internal_name`, no `is_public = FALSE`
  entities, no `secret`/`rumor` events. The static parts are snapshotted
  under a new `"mj"` key in `conversation.injected_context` at conversation
  start (alongside the existing NPC snapshot, unchanged in shape) — the
  baseline a future bleed auditor compares MJ narration against. Wired into
  `pt-mj-narration` (bumped to `version=2`, new `{mj_context}` variable) and
  `_build_mj_user` (all three modes: `dialogue`, `npc_reaction`, `scene`); the
  MJ system prompt gains an anti-invention rule scoped to the provided
  context, mirroring `npc_dialogue`'s rule.
- **v1.11** — No new tables or columns. Retroactive documentation (per
  BRIEF-01-tooling-v2 audit) of the **Author CRUD** (`cockpit/crud.py`,
  shipped just before this entry): a second sanctioned canon-write path —
  direct, state-setting creator edits to `character`/`faction`/`location`
  (composite entity + extension row, soft delete) and in-context
  `relation`/`knowledge` editors (hard delete), with no `proposed_mutation`
  checkpoint. Shares `writes.write_relation`/`write_knowledge` with
  `_apply_mutation` so clamping/validation cannot diverge. **Fix included**:
  `write_relation(mode="set")` (CRUD relation edits) now appends the previous
  state to `change_history` before overwriting — history is sacred on both
  write paths — via a shared `_append_history_snapshot` helper extracted from
  `mode="delta"`; `_apply_mutation`'s behavior is unchanged. See
  `ARCHITECTURE_DECISIONS.md`, "Author CRUD — the second sanctioned
  canon-write path".
- **v1.10** — No new tables or columns. Doc-level change only: documented the
  `character.secrets` / `knowledge.is_secret` boundary convention (NOTE under
  the `character` table — `secrets` is creator meta-narrative, never read by
  any context assembler; concealment is modeled via `knowledge.is_secret`,
  excluded by the assembler) and the two-sanctioned-canon-write-paths rule
  (`_apply_mutation` for AI proposals after creator approval, and the creator
  CRUD for direct creator authority — no other path may write canon). Added
  project tooling: a permanent `## Invariants (verified at every review)`
  section in `CLAUDE.md`, plus `/close-step` and `/review-step` commands.
- **v1.9** — No new tables or columns. Application-layer change only: NPC
  initiative — bystander NPCs can act spontaneously without being addressed
  (Tier 3, C1–C3; full rationale in `ARCHITECTURE_DECISIONS.md`).
  — **C1**: a per-turn vote (`pt-mj-initiative`, `usage='mj_initiative'`)
  decides whether one bystander acts (cadence E1: at most one per turn),
  using each candidate's `relation` signal toward the player and `entity.status`.
  — **C2**: the chosen NPC's act (`pt-npc-initiative-act`,
  `usage='npc_initiative_act'`) is a `{"act_text", "move"}` JSON object;
  `move=true` triggers `migrate_npc` (Tier 1 primitive) before narration —
  not a canon mutation, same as forming/dissolving a gathering. Both new
  templates seeded with `world_id=NULL`, upsert.
  — **C3**: the candidate pool widens from the player's gathering to every
  open gathering at the location; a non-member winner has `move=true` forced
  structurally. New `prompt_template.usage` values: `mj_initiative`,
  `npc_initiative_act`.
- **v1.8** — Multi-NPC scenes, Tier 1 (migration only — generation, name
  resolution, and the multi-participant `/say` flow are later steps). Two new
  tables and one relaxed column:
  — `gathering`: an ephemeral social cluster attached to a `session`
    (`location_id`, MJ-generated `label`, `status` open|dissolved). Its only
    durable trace in canon is the `proposed_mutation` rows it produces —
    **forming or dissolving a gathering is not itself a canon mutation.**
  — `gathering_member`: the roster, doubling as a conversation's participant
    list. Earshot = `left_at IS NULL`; rows are never deleted, only closed off.
  — `conversation.npc_id` relaxed from `NOT NULL` to nullable: it now names an
    optional seed/focus NPC; participants are derived from the gathering
    roster instead. Added `conversation.gathering_id` (the cluster present).
  — Five new indexes: `idx_gathering_location`, `idx_gathering_session`,
    `idx_gathering_member_group`, `idx_gathering_member_entity`,
    `idx_conversation_gathering`.
  Application-layer invariants recorded for the steps that build on this
  migration (see `ARCHITECTURE_DECISIONS.md` for the full rationale):
  **A2** — the MJ returns names, not ids; the code resolves them against the
  entities present, and a name that doesn't resolve is dropped and logged, never
  guessed. **B1** — partitioning into gatherings happens once, in full, at
  entry: every present NPC lands in exactly one gathering (a lone NPC forms a
  solo gathering of one), preserving the invariant that a present NPC always
  belongs to exactly one open gathering — a location may hold several
  simultaneous open gatherings, one per cluster. **C1** — gatherings are
  generated once at entry; no spontaneous reshuffling mid-scene.
  — *Tier 1, step 2 (application layer, no schema change)*: `gathering.py`
  implements the A2/B1 contracts above as two deliberately separate functions —
  `generate_gatherings` (loads the present NPCs, asks the MJ to partition them
  via the new `pt-mj-gathering` template, resolves names to entity ids,
  completes the partition, writes `gathering`/`gathering_member` rows; never
  raises, falls back to an all-solo partition on any failure) and
  `enter_location` (the single-player caller: dissolves the location's open
  gatherings for the session, then regenerates — see the function's docstring
  for why dissolution must live in the caller, not the core). New template:
  `pt-mj-gathering` (`usage='mj_gathering'`, `world_id=NULL`, upsert). Seeded
  by `seed_pilot.py`, which also gained two NPCs (Bryn, Korin) so the pilot
  tavern has five present NPCs to exercise clustering.
  — *Tier 1, step 3 — closes the tier (application layer, no schema change)*:
  the `/say` flow gains a fourth interpretation mode, **`join`** — the player's
  intent to settle with an open gathering. While ungrouped, `join` takes
  priority over the other three modes ("parler n'a pas de cible tant qu'on n'a
  pas rejoint"); the model is given the player's `gathering_status` and a
  free-text `reference` to the named group, resolved against the open
  gatherings' rosters by the same A2 contract (exact match against present
  names/labels; ambiguous or unresolved → the cockpit lists the open
  gatherings and the player picks — reusing the new C2 target selector, see
  below). Joining inserts one `gathering_member` row (`left_at=NULL`) and
  anchors `conversation.gathering_id`; like forming one, **joining a gathering
  is not a canon mutation** — no `proposed_mutation` row is produced.
  The NPC phase generalises from a single fixed NPC to a **selected
  responder**: contract **A3 (hybrid speaker selection)** — an explicitly
  targeted NPC always answers; an address to "the group" triggers one MJ call
  (`pt-mj-speaker`, `usage='mj_speaker_selection'`, new template) that picks
  exactly one active member to respond (cadence **B1bis**: exactly one
  responder per turn, no PNJ↔PNJ exchange — that stays Tier 3). The cockpit
  gains a **C2** target selector ("groupe" / a named NPC) next to the `/say`
  field, populated from the joined gathering's active roster — distinct from
  the existing **C1** ("generated once at entry; no reshuffling"); the label
  collision is deliberate disambiguation, not a renumbering. Context assembly
  gains contract **D1 (mutual awareness)**: `assemble_npc_context` now accepts
  a `gathering_id` and injects an "AVEC QUI TU TE TROUVES EN CE MOMENT" section
  naming co-present members and their public description — simple co-presence,
  no relation-based modulation (that stays a later refinement). New template:
  `pt-mj-speaker`. The `pt-mj-interpretation` template and its `ResponseMode`
  enum gain `join`; `_interpret_mode` now returns `(mode, reference)`.
- **v1.7** — No new tables or columns. Application-layer change only:
  the `/say` flow gains a **mode-routing interpretation phase** (phase 0)
  that classifies the player's input into `dialogue` | `npc_reaction` | `scene`
  before calling the NPC. Consequences:
  — `scene` turns skip the NPC call entirely; no `npc` row is written;
    the MJ narrates the environment without any NPC involvement.
  — `npc_reaction` turns call the NPC with a one-shot wordless-reaction
    instruction; the NPC produces a gesture, not speech; the MJ renders it
    in third-person prose with no quoted dialogue.
  — `dialogue` turns are unchanged (the prior behavior).
  New template: `pt-mj-interpretation` (`usage='mj_interpretation'`,
  `world_id=NULL`, upsert). Seeded by `seed_pilot.py`.
  The `prompt_template` usage column comment is updated to include
  `mj_interpretation`. The `conversation_message` turn_order note is updated:
  N+1 is absent for scene turns.
- **v1.6** — No new tables or columns. Comment-level changes only:
  (1) `conversation_message.speaker` now documents three values: `player` |
  `npc` | `mj`. `mj` rows are the MJ narration (presentation layer); `player`
  and `npc` remain the canonical truth the analysis reads.
  (2) `proposed_mutation.proposed_by` now documents `local_ai_immediate` as a
  second AI source tag, used by the per-turn analysis that fires after each turn
  (owns all `relation_change` proposals).
  Application-layer changes: `relation_change` removed from the duplicate-apply
  guard (`_find_applied_duplicate`) because relation deltas accumulate — two
  independent events must both apply. The final-pass analysis now filters out
  `relation_change` (owned by per-turn flags). Both guards continue to protect
  the idempotent types (`new_knowledge`, `status_change`).
- **v1.5** — No new tables or columns. The creator review cockpit
  (`src/world_engine/cockpit/`) implements the full approve → apply pipeline,
  making the `proposed_mutation` lifecycle operational end-to-end. Two
  application-layer invariants are now enforced in code:
  (1) `--force` re-analysis never deletes reviewed rows (`applied`, `approved`,
  `rejected`) — only `proposed` rows are replaceable.
  (2) `_apply_mutation` runs a duplicate guard before any canon write: if an
  equivalent mutation was already applied for the same conversation (matched on
  `entity_id` + `subject` for `new_knowledge`; unordered entity pair +
  `relation_type` for `relation_change`), the new proposal is blocked and
  surfaced in the "Needs attention" review bucket rather than silently doubling
  the effect.
- **v1.4** — No new tables or columns. Added `conversation_analysis` to the documented `prompt_template.usage` values (the column is TEXT — the value was already valid, this is a doc-only update). The post-conversation analysis pipeline (`analyze_conversation.py` + `analyzer.py`) is now implemented; see `ARCHITECTURE_DECISIONS.md` for the circuit description.
- **v1.3** — Added `knowledge.share_threshold` (INTEGER DEFAULT 50, CHECK 1–100): the minimum NPC→interlocutor relation intensity required to share a non-secret knowledge row in conversation; ignored when `is_secret = TRUE`. Recorded the convention that an absent NPC→interlocutor relation is treated as neutral (50) by the assembler.
- **v1.2** — Added `conversation`, `conversation_message`, and `proposed_mutation` for live sessions and the unified mutation pipeline. Removed `pass_play.local_proposal`. Documented the role-toggle rule on `user`. Added `npc_dialogue` to prompt usages. Changed `relation.intensity` to a 1–100 scale (default 50 = neutral) with a clamp-on-apply rule. Added `updated_at` to `entity` and `knowledge`. Added an INDEXES section for frequent lookups. Schema translated to English.
- **v1.1** — Initial local-phase schema.

*Version 1.11 — Co-built with Claude, June 2026*
