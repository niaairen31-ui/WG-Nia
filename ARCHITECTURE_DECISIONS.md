# WORLD ENGINE — Architecture Decisions

*Companion to the schema and founding document. Records the decisions made before building. This file is the brief for Claude Code.*

---

## CONTEXT

The engine runs a persistent RPG world. The creator keeps structural control over how the world evolves. Two modes of play feed the same world:

- **Pass-plays** — actions players declare asynchronously between sessions.
- **Live sessions** — real-time play where a player acts as if inside the story (enters a location, sees the NPCs present, talks to them, learns things, builds relationships).

Local AI models (Llama, GLM) drive analysis and NPC dialogue. The creator controls every master prompt to set the limits and keep control.

---

## CORE DECISION — Free dialogue, controlled consequences

The founding principle is "creator control is structural" (approval checkpoints). Live conversation makes per-line approval impossible, so we split interaction into two layers with different risk levels:

- **Dialogue** (talking, learning, feeling out an NPC) — low risk, runs autonomously in real time. The NPC speaks freely, but only within the bounds of what it knows.
- **World mutations** (a relationship evolving, a secret revealed, knowledge acquired, an event created) — these pass through a checkpoint. Not the conversation itself, but its *consequences* on world state.

During a conversation the local AI plays the NPC **and** proposes mutations (e.g. "player gained Marek's trust → relation +2", "Marek hinted the Council is hiding something → new knowledge"). The player plays without friction; proposals accumulate. The creator validates them later, at the checkpoint.

**Why this works:** even if a local model drifts or an NPC says something off, it cannot change world state without creator approval. Worst case stays recoverable. The same validation pipeline serves both pass-plays and live sessions — one mutation pipeline, one source of truth.

---

## SCHEMA ADJUSTMENTS

Three additions. Not a rewrite — the existing schema holds.

### 1. Live conversations

Store the raw player ↔ NPC exchanges. The transcript is the raw material the AI later analyzes to propose mutations.

- `conversation` — who talks to whom, in which location, during which session.
- `conversation_message` — each line (player or NPC), in order.

### 2. Proposed mutations as a first-class concept

Currently `pass_play` blends the declared action and its `local_proposal`. We extract a generic `proposed_mutation` table describing **one atomic change** (relation delta, new knowledge, event creation, status change, etc.) with its approval status.

Both pass-plays and live conversations produce `proposed_mutation` rows. This gives a single validation pipeline regardless of source — the thing that makes the engine coherent.

### 3. Context assembly (logic, not a table)

When a player talks to an NPC, the engine builds that NPC's prompt: who it is, what it knows (`knowledge`), its relations to the interlocutor, and its secrets to **never** reveal. The schema already holds all of this. The missing piece is a function: "assemble an NPC's context for a conversation." This is where real creator control lives — inject only what the NPC knows, never its secrets nor others'.

---

## CONVERSATION ANALYSIS — Two-tier proposal system

Proposals are generated at two moments, by two functions in `analyzer.py`.

### Per-turn immediate analysis (`analyze_single_turn`)

Fires automatically **after each turn's MJ narration stream**, while the player is composing their next line. Analyses only the current exchange (one `[JOUEUR]` + one `[PNJ]` line). Uses the same prompt, normaliser, and validator as the final pass.

- Tagged `proposed_by = 'local_ai_immediate'`.
- **Owns all `relation_change` proposals.** Relation deltas accumulate across turns (two independent +5 events total +10); the final pass must never re-propose them.
- Within-turn collapse: if the model emits duplicate `relation_change` entries for the same entity pair + type in one response (model stutter), only the first is kept.
- Failures are silently swallowed — analysis must never surface to the player.

### Final-pass analysis (`analyze_conversation`)

Triggered manually via the **Analyze** button in the cockpit (or `scripts/analyze_conversation.py`). Reads the full transcript (`player` and `npc` rows only — `mj` rows are excluded).

1. **Load** — reads the `conversation` row, its ordered `conversation_message` rows (speaker ∈ {`player`, `npc`}), and the `injected_context` snapshot.
2. **Prompt** — the `pt-conversation-analysis` template (`usage = conversation_analysis`, editable in DB) instructs the model to identify ONLY concrete changes that ACTUALLY occurred. An empty result is explicitly valid for idle chat.
3. **Call** — `ollama_client.chat()` with `format="json"`. Thinking mode enabled; `strip_think()` removes the block before parsing.
4. **Normalise** — `_normalize_to_schema()` maps the model's natural field names to our schema (the 8b model reliably detects *what* changed but ignores exact field names).
5. **Validate** — items that cannot be normalised are skipped and logged.
6. **Filter** — `relation_change` items are dropped before writing. Rationale: the per-turn flags already sum the full arc; re-proposing them would double-count.
7. **Deduplicate** — remaining items are checked against existing `proposed` rows for this conversation using the idempotent match key (`entity_id` + `subject` for `new_knowledge`; `entity_id` for `status_change`). Only what the per-turn flags missed is written.
8. **Write** — each surviving item becomes one `proposed_mutation` row: `status = proposed`, `proposed_by = local_ai`.

Idempotency: re-running without `--force` returns existing proposals. `--force` deletes ONLY rows with `status = 'proposed'` (including per-turn flags); reviewed rows (`applied`, `approved`, `rejected`) are permanent audit history and survive regardless.

---

## CREATOR REVIEW COCKPIT

`src/world_engine/cockpit/` is the local web UI for live play **and** creator
review. It is the **only place where world state gets written** in response to
approved proposals.

### What it does

- **Live play** — select an NPC, start a conversation, type turns. Each turn runs
  the three-phase `/say` flow (see below). Per-turn proposals accumulate silently.
- Reads conversations and renders them as a chat transcript with the MJ narration
  as primary text and the raw NPC line as a muted audit annotation below each turn.
- Triggers (re-)analysis via `analyzer.analyze_conversation` (final pass).
- Lists the review queue filterable by status (`proposed` / applied / rejected /
  needs attention).
- Approve / reject mutations with an optional creator note and (for approve) an
  editable payload before writing.

### The four-phase `/say` flow

Each player turn runs four phases inside one SSE generator:

0. **Interpret phase** — `_interpret_mode()` classifies the player's raw input
   into one of three `ResponseMode` values via a non-streaming `chat()` call
   (`pt-mj-interpretation`, `usage='mj_interpretation'`). Falls back to
   `ResponseMode.dialogue` on any failure — a misclassification must never break
   a turn.

   | Mode | Trigger | NPC called? |
   |---|---|---|
   | `dialogue` | speech / question to the NPC (default) | yes, full reply |
   | `npc_reaction` | visible action *toward* the NPC, no words | yes, wordless gesture only |
   | `scene` | environment action, NPC not engaged | **no** |

   For `npc_reaction`, a `[MODE RÉACTION NON-VERBALE]` instruction is appended
   to the NPC system prompt at call time (not persisted; one-shot).

1. **NPC phase** (conditional) — `chat_stream` (buffered; thinking filtered by
   `_StreamThinkFilter`). Skipped entirely for `scene` turns; no `npc` row is
   written. The player sees no tokens yet; the "réflexion…" indicator stays.
   Result persisted as `speaker='npc'` (canonical truth).

2. **MJ phase** — MJ narration generated from `pt-mj-narration`
   (`usage='player_narration'`) for `dialogue`; mode-specific user messages for
   `npc_reaction` (third-person gesture, no dialogue quote) and `scene`
   (environment prose, NPC not mentioned). Streamed to the player token by token.
   `{"mode": "..."}` and `{"npc_raw": "..."}` SSE events are sent before `[DONE]`
   for creator audit (`npc_raw` is an empty string for `scene` turns). Result
   persisted as `speaker='mj'` (presentation layer).

3. **Per-turn analysis** (sync-after-stream) — runs after `[DONE]` is sent, while
   the player reads and types. Calls `analyze_single_turn()`. For `scene` turns
   `npc_reply` is `""`; the mini-transcript ends with `[PNJ] ` and the model
   correctly returns `[]`. Silently writes `proposed_mutation` rows tagged
   `proposed_by='local_ai_immediate'`.

The NPC's words never reach the player directly — the player always reads the MJ's narration, which quotes them verbatim (`dialogue`) or renders them as third-person prose (`npc_reaction`).

### apply_mutation — the only canon-write path

`_apply_mutation()` in `cockpit/app.py` is the single function authorised to
write to canon tables. Three types are implemented:

| mutation_type    | What is written |
|------------------|-----------------|
| `relation_change`  | Find or create the Relation row; apply intensity delta (clamped 1–100); append previous state to `change_history`. |
| `new_knowledge`    | Insert a `knowledge` row; inherits `session_id` from the source conversation. |
| `status_change`    | Update `entity.status` + `entity.updated_at`. |

Any other type is left at `status = 'approved'` with a note — never wrongly
applied. Better un-applied than wrongly applied.

Canon writes are wrapped in a **SAVEPOINT** (`db.begin_nested()`): if the apply
fails, only the canon writes roll back; the mutation-row update (status,
`reviewed_at`, error note) lives in the outer transaction and always commits.

### The "Needs attention" tab

`status = 'approved'` is an **exception bucket**, not a success state. A
proposal lands there only when it was reviewed but could NOT be applied:

- Unimplemented `mutation_type`
- Apply error (e.g. entity not found, malformed payload)
- Duplicate-application blocked (see below)

A successful approval always reaches `status = 'applied'`. The "Needs
attention" tab being empty is the normal, healthy state.

### Duplicate-application guard

`_find_applied_duplicate()` runs as the first check inside `_apply_mutation`.
If an equivalent mutation was already applied for the same conversation, the
new one is blocked and routed to "Needs attention" instead of writing a
duplicate row.

**Idempotent types** — applying the same fact twice is wrong; the guard is active:

| mutation_type  | Match key (same `conversation_id` required) |
|----------------|----------------------------------------------|
| `new_knowledge` | `entity_id` + `subject` |
| `status_change` | `entity_id` |

**Accumulating type — `relation_change` is intentionally excluded.** Relation
deltas sum across turns: two independent +5 events total +10 and must both apply.
`relation_change` proposals come only from per-turn immediate flags (one per turn);
the final pass never proposes them. There is therefore no double-application risk,
and the guard would incorrectly block a legitimate second event.

### History is sacred — force protection

`--force` (CLI and cockpit endpoint) deletes ONLY rows with `status = 'proposed'`.
Reviewed rows (`applied`, `approved`, `rejected`) are immutable audit history
and are never deleted.

---

## MULTI-NPC SCENES — Gatherings (schema v1.8, Tier 1)

A location can hold more than one NPC at once, and a scene should reflect who's
actually clustered together — not force every conversation into a 1:1 with a
single NPC. **Tier 1, step 1 was the migration**: `gathering` and
`gathering_member` exist in the schema and `conversation` can reference a
gathering. **Tier 1, step 2 — now implemented (`src/world_engine/gathering.py`,
application layer, no schema change)** — generates the initial partition when
a player enters a location:

- `generate_gatherings(location_id, session_id, db)`: the structural core.
  Loads the present NPCs (`vital_status='alive'`, `entity.status='active'`,
  player excluded), asks the MJ to partition them via the `pt-mj-gathering`
  template, resolves the returned names to entity ids (contract A2 below),
  completes the partition so it is total (invariant B1 below), and writes
  `gathering` (`status='open'`) and `gathering_member` (`left_at=NULL`) rows.
  Never raises — a missing template, an unreachable model, malformed JSON, or
  zero resolved names all fall back to an all-solo partition. Dissolves
  nothing.
- `enter_location(location_id, session_id, db)`: the single-player caller.
  Dissolves the location's open gatherings for the session first, then calls
  `generate_gatherings`. The dissolve step deliberately lives here rather than
  in the core — see the function's docstring for the multiplayer-decoupling
  rationale (a future second player should *join* the existing partition, not
  wipe it out from under the first).

The player is never placed in a gathering at entry — joining one is a later,
explicit action. The multi-participant `/say` flow and the "join a gathering"
action remain the next steps, designed against — but not yet built on top of —
these invariants:

**Forming or dissolving a gathering is not a canon mutation.** A gathering is
a *reading* of who's standing together for the scene's duration, scoped to the
session — not a lasting fact about the world. It produces no
`proposed_mutation` row by itself. Only what happens *inside* it (a relation
shifting, a secret slipping, a fact learned) generates proposals, exactly as
today. This keeps "creator control is structural" intact: the checkpoint
guards consequences, not scene bookkeeping.

### A2 — Name resolution is structural, not generative

The MJ narrates in terms of *names* ("Maelis se tourne vers Joren"), never
entity ids — that's the natural register for prose, and the only one a local
model can produce reliably. The application resolves those names against the
entities actually present in the gathering roster (`gathering_member` with
`left_at IS NULL`). **A name that does not resolve to a present entity is
dropped and logged — never guessed, never silently mapped to the nearest
match.** A misresolution would let the wrong NPC "hear" or "say" something;
better an omission the creator can audit than a false attribution baked into
the transcript.

### B1 — Partition fully at entry; every present NPC in exactly one open gathering

When a player enters a location, the engine partitions **every** NPC present
into gatherings **once, completely, in a single pass** — there is no
"unassigned" remainder. An NPC standing alone still gets a gathering: a solo
gathering of one. A location can (and typically will) hold **several**
simultaneous open `gathering` rows — one per cluster the MJ identified, plus
one per loner — that is the partition, by definition. The invariant the rest
of the design leans on is narrower and per-NPC: **at any moment, a present NPC
belongs to exactly one open `gathering`** (`gathering_member` with
`left_at IS NULL` resolves unambiguously to a single open gathering).
Conversations, earshot, and later multi-participant dialogue all key off "the
open gathering this NPC currently belongs to" — a partial or overlapping
partition would break that lookup.

### C1 — Generated once at entry; no spontaneous reshuffling

The gathering's shape (who's clustered with whom, the MJ's descriptive
`label`) is decided **once, when the player arrives**, and holds for the scene.
NPCs do not spontaneously regroup mid-conversation — that would make the
roster (and therefore earshot, and therefore secret-exclusion) a moving
target the player could not reason about, and would multiply the surface for
local-model drift. Membership still *evolves* through explicit, narratively
grounded events (someone leaves, someone new arrives) — recorded by closing
or adding `gathering_member` rows (`left_at` set, never deleted; new rows
appended) — but the *partition itself* is not regenerated from scratch.

---

## V1 SCOPE — Minimal playable

Goal: find out fast whether the local models can hold a character. That is the project's real unknown.

**In scope:**
- One player, one location, a few NPCs.
- A live conversation that runs with correctly injected NPC context.
- Mutations accumulate as proposals — **not yet applied** to the world.
- Local web app, running locally.
- **Role toggle.** The single test user switches between creator mode and player mode. The rule: injected context depends on the *active role*, not the account. In creator mode the user sees real world state (secrets included), edits, and reviews mutations. In player mode the app injects only what the player character is meant to know — secrets are hidden from view even though the same human knows them. This makes solo testing more honest and is the exact mechanism multiplayer will reuse later (a real player just gets their own account, locked to player mode).

**Out of scope for v1 (but kept easy to add later):**
- Multiplayer / real concurrent players (solo testing first).
- The neighbouring nation and wider lore expansion.
- Migration to Supabase (stay on SQLite).

The minimal version tells us in a few days whether the dialogue "holds" before building the rest of the loop.

---

## DESIGN CONSTRAINTS CARRIED FORWARD

- SQLite now, Supabase-compatible later (UUID text PKs, JSON → JSONB). Only env vars change, not app code.
- History is sacred — nothing overwritten; successive states preserved.
- Creator owns and edits every master prompt.
- Everything is an entity; magic is an actor.

---

*Co-built with Claude, June 2026.*
