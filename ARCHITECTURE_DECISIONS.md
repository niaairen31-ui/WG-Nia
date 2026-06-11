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

### Overhearing analysis pass (`analyze_overhearing`, Tier 4)

A THIRD per-turn pass, fired (sync-after-stream, `dialogue` turns only) after `analyze_single_turn`. NPCs within earshot of a conversation may **acquire** knowledge from what was said — always via `proposed_mutation`, never by direct write. It is **acquisition-only**: a receiver who already holds ANY row on a subject (any level) is skipped. Level upgrades (`knowledge_change`) are a later step.

The model's only job is closed-list classification (`pt-overhearing-classification`, `usage = overhearing_classification`): given the turn's player/NPC lines and the world's distinct `knowledge.subject` values, return `[{"subject": ..., "speaker": "player"|"npc"}, ...]`. All attribution, receiver computation, and level computation happen in code.

Guard chain, all before any model call except (g)/(h)/(j)/(k) which run per classified element:

- **Turn-mode guard** — re-checks `npc_line` is non-empty even though the caller already gates on `dialogue`.
- **Receiver computation (b)** — eligible receivers = active members of the conversation's gathering (`gathering_member.left_at IS NULL`, the single roster source) MINUS the responding NPC MINUS the player. Empty set → return with **no model call** (two-party conversations cost nothing).
- **Subject list (c)** — `SELECT DISTINCT subject FROM knowledge` scoped to the world. Empty → no model call.
- **Normalization (e)** — only elements whose `subject` is an EXACT member of the closed list and whose `speaker` ∈ {`player`, `npc`} survive; everything else is dropped and logged. No fuzzy matching.
- **Speaker resolution (f)** — `speaker = "npc"` → the responding NPC's entity id; `speaker = "player"` → the conversation's player entity id. The eligible receiver set additionally excludes the resolved speaker (an NPC never overhears itself).
- **K2 guard (g)** — load the SPEAKER's `knowledge` row for the subject. No row → skip the element entirely. The speaker's canonical knowledge is the only authority; a speaker "knowing" without a row is model noise.
- **Secret guard (h)** — if the speaker's row has `is_secret = TRUE`, skip. Secrets are structurally excluded from NPC context, so a classification match on one is spurious by definition — this extends the secrets invariant to propagation.
- **Acquisition-only filter (j)** — for each eligible receiver, an existing row on the subject (any level, any conversation) skips that receiver.
- **Proposal-dedup (k)** — skip a receiver if a `proposed` `new_knowledge` row already exists for this `(conversation_id, receiver entity_id, subject)` — re-stating a fact later in the conversation must not stack proposals.

**Deterministic level ladder (i)** — the acquired level is one step below the speaker's row level on `unaware < rumor < suspicious < partial < knows < fully_understands`, floored at `rumor`:

```
fully_understands → knows
knows             → partial
partial           → suspicious
suspicious, rumor → rumor
```

**Write (l)** — one `proposed_mutation` per surviving (receiver × subject): `mutation_type = 'new_knowledge'`, `proposed_by = 'local_ai_overhearing'`, `payload.content` copied VERBATIM from the speaker's row (no model-generated content — anti-invention), `payload.is_incorrect` inherited from the speaker's row, `payload.source = "overheard:{conversation_id}:{speaker_entity_id}"` (structured form for provenance). `rationale` is human-readable: `Overheard from {speaker name} at {location name} (level {speaker level} → {acquired level})`.

No change to `_apply_mutation` — these are plain `new_knowledge` mutations and use the existing apply path and idempotent duplicate guard.

Deferred: the **E3-general upgrade rule** (`knowledge_change` apply + upgrade detection — "computed level > existing level") is the next step; a speaker-level cap at `knows` for direct affirmation belongs to that step.

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
- **Batch review** (`POST /api/mutations/batch-review`, schema v1.14) — select
  several `proposed` rows via checkboxes and approve/reject them in one
  gesture, sequentially through the same unit-review paths (see below).
- **Travel** (scene view "Voyager" control, `POST /api/travel`, schema v1.13)
  — a creator tool performing a clean location transition (close conversation,
  close gathering membership, update `current_location_id`); silent, no
  narration. Narrative travel (an in-fiction `travel` response mode) is E2,
  deferred pending an adjacency model decision.

### The `/say` flow — multi-participant (Tier 1, step 3)

Each player turn runs through one SSE generator. With gatherings (schema
v1.8), the flow generalises from a fixed 1:1 NPC to a **selected responder**
drawn from the player's gathering — while staying perfectly backward
compatible for plain 1:1 conversations (`conv.gathering_id IS NULL`).

0. **Interpret phase** — `_interpret_mode()` classifies the player's raw input
   into one of four `ResponseMode` values via a non-streaming `chat()` call
   (`pt-mj-interpretation`, `usage='mj_interpretation'`), now also fed the
   player's `gathering_status` (free text: which gathering they're in, or which
   open gatherings exist if they're not in one yet). Returns `(mode, reference)`
   — `reference` is the player's exact words naming a group, populated only for
   `join`. Falls back to `(dialogue, "")` on any failure — a misclassification
   must never break a turn.

   | Mode | Trigger | NPC called? |
   |---|---|---|
   | `dialogue` | speech / question to the NPC (default) | yes, full reply |
   | `npc_reaction` | visible action *toward* the NPC, no words | yes, wordless gesture only |
   | `scene` | environment action, NPC not engaged | **no** |
   | `join` | settling with an open gathering — *only while ungrouped* | **no** (action, not dialogue) |

   For `npc_reaction`, a `[MODE RÉACTION NON-VERBALE]` instruction is appended
   to the NPC system prompt at call time (not persisted; one-shot). A `join`
   classification while already grouped is a misread — `_stream` downgrades it
   to `dialogue` as a safety net, since "join" is meaningless once anchored.

   **Join resolution (contract A2 reused)** — `reference` is matched against
   the open gatherings' labels and member names (`_resolve_join_target`,
   exact-ish matching, never guessed). Exactly one match → `_join_gathering`
   inserts a `gathering_member` row (`left_at=NULL`, idempotent) and sets
   `conversation.gathering_id`; the MJ narrates the player settling in. Zero or
   ambiguous matches → the cockpit lists the open gatherings (`join_candidates`
   SSE event) and the player clicks one — the **C2** target selector doubles as
   this fallback picker, posting to `POST .../join`. **Joining is not a canon
   mutation** (same rationale as forming a gathering, see MULTI-NPC SCENES
   below); no `proposed_mutation` row is produced either way.

   **Speaker selection (contract A3 — hybrid)** — for `dialogue` /
   `npc_reaction` turns, the responder is resolved from `SayBody.target`:
   absent/`None` → the conversation's seed NPC (`conv.npc_id`, the 1:1
   default); an explicit entity id → that NPC answers directly; `"group"` →
   one MJ call (`pt-mj-speaker`, `usage='mj_speaker_selection'`) picks exactly
   one active co-member to respond. **Cadence B1bis: exactly one responder per
   turn — no PNJ↔PNJ exchange** (that is Tier 3). If addressing the group
   resolves to nobody (no active co-members, or selection fails), the turn
   downgrades to `scene` rather than inventing a reply.

1. **NPC phase** (conditional) — `chat_stream` (buffered; thinking filtered by
   `_StreamThinkFilter`). Skipped for `scene` and `join` turns; no `npc` row is
   written. The player sees no tokens yet; the "réflexion…" indicator stays.
   Result persisted as `speaker='npc'`, `speaker_id=<responder id>` (canonical
   truth) — the per-message speaker, not a fixed conversation-level NPC.

   **Context per responder (contract D1 — mutual awareness)** — the frozen
   `injected_context.system_prompt` from conversation start is reused only for
   the seed NPC in a non-gathering conversation; any other responder gets a
   freshly assembled `assemble_npc_context(responder_id, player_id, location_id,
   db, gathering_id=conv.gathering_id)`, which injects an "AVEC QUI TU TE
   TROUVES EN CE MOMENT" section naming co-present gathering members and their
   *public* description (appearance/entity description — never knowledge or
   relations). Simple co-presence; no relation-based modulation of who an NPC
   "notices" — that is a later refinement.

2. **MJ phase** — MJ narration generated from `pt-mj-narration`
   (`usage='player_narration'`) for `dialogue`; mode-specific user messages for
   `npc_reaction` (third-person gesture), `scene` (environment prose, no NPC),
   and `join` (settling-in narration, or hesitation while the cockpit shows the
   picker). Streamed to the player token by token. `{"mode": "..."}` and
   `{"npc_raw": "..."}` SSE events are sent before `[DONE]` for creator audit
   (`npc_raw` is `""` for `scene`/`join` turns); a `join` turn additionally
   sends either `{"joined": {...}}` or `{"join_candidates": [...]}`. Result
   persisted as `speaker='mj'` (presentation layer).

3. **Per-turn analysis** (sync-after-stream) — runs after `[DONE]` is sent, while
   the player reads and types. Calls `analyze_single_turn()`. For `scene` and
   `join` turns `npc_reply` is `""`; the mini-transcript ends with `[PNJ] ` and
   the model correctly returns `[]`. Silently writes `proposed_mutation` rows
   tagged `proposed_by='local_ai_immediate'`.

The NPC's words never reach the player directly — the player always reads the MJ's narration, which quotes them verbatim (`dialogue`) or renders them as third-person prose (`npc_reaction`, `join`).

### C2 — Cockpit speaker-target selector (distinct from C1)

A selector ("le groupe" / a named active member) sits next to the `/say`
field, populated from the joined gathering's roster, and drives `SayBody.target`
(contract A3). It is hidden for plain 1:1 conversations (no gathering yet —
`/say` keeps its backward-compatible default). It doubles as the fallback
picker for an unresolved `join` reference. **Naming note:** the task spec that
requested this selector labelled it "C1" — colliding with the existing,
unrelated C1 ("generated once at entry; no spontaneous reshuffling", below).
It is labelled **C2** throughout the code and docs to keep both concepts
addressable without ambiguity.

### apply_mutation — one of two sanctioned canon-write paths

`_apply_mutation()` in `cockpit/app.py` is the only function authorised to
write canon **in response to an AI proposal**, after creator approval. The
other sanctioned path is the **author CRUD** (see below), for the creator's
direct edits — see CLAUDE.md, "Two sanctioned canon-write paths, no others."
Three mutation types are implemented:

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

### Batch review

`POST /api/mutations/batch-review` (schema v1.14) adds a batch gesture over the
**existing** unit review paths — no new canon-write path, no payload editing.

**Selection** — the review queue shows one checkbox per row, rendered ONLY for
`status = 'proposed'` rows; reviewed rows have none. A "select all / none"
toggle acts on the currently displayed proposed rows. "Approve selected" /
"Reject selected" are disabled while zero rows are checked.

**Processing** — sequential, per row, in selection order:
- Re-load the row; if `status != 'proposed'`, SKIP it (counted, not touched).
  This re-check defends "history is sacred" against a stale client selection
  (e.g. the row was already reviewed in another tab).
- Approve: the same `_apply_mutation` call as unit approve, stored payload
  unmodified, inside its own SAVEPOINT. The duplicate-application guard and
  the "Needs attention" routing apply per row exactly as in unit review. One
  row's failure never stops the loop.
- Reject: same field updates as unit reject (`status='rejected'`,
  `reviewed_at`). No creator note input in batch.

**Verdict** — the endpoint returns counts (`applied` / `needs_attention` /
`skipped` for approve; `rejected` / `skipped` for reject); the cockpit shows
them and refreshes the queue.

**Audit trail** — every row the batch endpoint actually processes (not
skipped) gets the literal marker `batch-review` appended to `creator_notes`,
distinguishing a batch decision from a unit decision later.

**Deferred decision** — payload editing in batch is deliberately excluded;
editing means unit review.

### History is sacred — force protection

`--force` (CLI and cockpit endpoint) deletes ONLY rows with `status = 'proposed'`.
Reviewed rows (`applied`, `approved`, `rejected`) are immutable audit history
and are never deleted.

### Author CRUD — the second sanctioned canon-write path

`src/world_engine/cockpit/crud.py` (mounted on the cockpit app under `/api`)
is the creator's direct world-editing tool — the **Author** view, alongside
the **Play** view. It is the second of the two sanctioned canon-write paths
(see CLAUDE.md, "Two sanctioned canon-write paths, no others"): a *direct*,
state-setting write with no `proposed_mutation` checkpoint, since that
checkpoint exists to contain AI drift during play, not to gate the creator.

What it edits:
- **Composite entity editors** for `character`, `faction`, `location` — the
  `entity` row plus its type extension row, written transactionally
  (`POST`/`PUT /api/entities/...`). Soft delete only (`entity.status =
  'inactive'`); relations and knowledge pointing at the entity survive.
- **In-context `relation` editor** — create/update/hard-delete relation rows
  from an entity's sheet (`/api/entities/{id}/relations`, `/api/relations/{id}`).
- **In-context `knowledge` editor** — create/update/hard-delete `knowledge`
  rows (`/api/entities/{id}/knowledge`, `/api/knowledge/{id}`).

Shared write rules with `_apply_mutation`: both paths call
`writes.write_relation` / `writes.write_knowledge` so clamping and field
validation cannot diverge between them. For `relation`:
`_apply_mutation` uses `mode="delta"` (intensity delta, accumulates);
the author CRUD uses `mode="set"` (intensity set to an absolute value).
**Both modes append the previous state to `change_history` before writing**
— history is sacred on either path — via the shared
`_append_history_snapshot` helper; the 1-100 intensity clamp applies to both.
Author edits to `knowledge` are full in-place updates and pass through no
`proposed_mutation`; as of schema v1.16, `writes.write_knowledge` likewise
appends the row's previous state to `knowledge.change_history` before any
in-place update, via the shared `_append_knowledge_history` helper —
history is sacred on this path too.

Creator-mode-only: the CRUD router is mounted on the cockpit app (loopback
only, no auth) and is never reachable from, or invoked by, any AI-proposal
flow — `_apply_mutation` and the author CRUD are independent code paths that
both terminate in `writes.py`, and neither calls the other.

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

The player is never placed in a gathering at entry — joining one is an
explicit action. **Tier 1, step 3 — now implemented** — closes the tier: the
multi-participant `/say` flow and the "join a gathering" action (see the
`/say` flow section above for `join` mode, contracts A3/C2/D1, and cadence
B1bis) are built on top of these invariants:

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

## NPC INITIATIVE — Spontaneous bystander actions (Tier 3)

Gatherings (Tier 1) give every present NPC a roster; Tier 3 lets a bystander
NPC act on its own, without being addressed — the room feels alive even when
the player is talking to just one person. Built in three steps on top of the
existing gathering/relation/conversation tables — **no schema change**.

### C1 — The initiative vote

After the main NPC reply and MJ narration for a turn, `_npc_initiative_vote`
makes one cheap, non-streaming `format="json"` call (`pt-mj-initiative`,
`usage='mj_initiative'`, `/no_think` appended) asking: does any bystander NPC
spontaneously act this turn?

- **Cadence E1** — at most one NPC takes initiative per turn.
- **Candidate pool** — every active member of the player's gathering except
  the player and this turn's responder (C3 widens this further, see below).
- **Signal list** — for each candidate, the prompt states its
  `relation=<type> (<intensity>/100)` toward the player (or "neutre (50/100)"
  if no relation row exists) and its `entity.status`. The MJ's judgment, not a
  hard threshold, decides whether a signal is "enough"; the prompt only hints
  (relation < 40 → hostility/mistrust more likely to intervene; > 70 →
  affective involvement more likely).
- **Relation directionality convention** — a candidate NPC's "view of the
  player" is read as: `entity_a_id == npc` with `direction ∈ {a_to_b,
  mutual}`, OR `entity_b_id == npc` with `direction ∈ {b_to_a, mutual}`. A
  relation row stored from the *player's* perspective does not automatically
  give the NPC a signal — each side of an asymmetric relation needs its own
  row to carry its own signal (e.g. `rel-reike-player`, a `méfiance` edge from
  Reike toward the player, distinct from `rel-player-reike`).
- **Resolution (contract A2 reused)** — exact name from the candidate list;
  unresolved/invented → `(False, None)`, never guessed.
- Vote failure (timeout, bad JSON) is silent — initiative simply doesn't fire.

### C2 — The initiative act and migration

When the vote returns `act: true`, the chosen NPC gets a second, non-streaming
`format="json"` call (`pt-npc-initiative-act`, `usage='npc_initiative_act'`) —
fresh context assembled exactly like a normal responder (contract D1), with a
`{"act_text": "...", "move": <bool>}` JSON contract appended in place of the
shared `npc_dialogue` template's free-text contract. `/no_think` is **not**
appended — `format="json"` already constrains output. A hardcoded fallback
(`_NPC_INITIATIVE_ACT_FALLBACK`) covers databases predating this template.

- `act_text` — first person, 1–2 sentences, grounded only in its context sheet
  (same "never invent" rule as normal dialogue).
- `move` — `true` only if the NPC physically joins the player's gathering.
  Migration runs via `migrate_npc` (Tier 1's idempotent primitive) **before**
  narration, so the DB roster is already correct for the per-turn analysis and
  the next turn's context. **Migration is not a canon mutation** — same
  rationale as forming/dissolving a gathering: scene bookkeeping, not a
  lasting world fact. No `proposed_mutation` row for the move itself.
  `migrate_npc` closes ALL of the NPC's active `gathering_member` rows (B1
  repair, idempotent) and inserts the new one in a single transaction; if
  closing the source leaves it with zero active members, that source
  gathering is auto-dissolved (`status='dissolved'`, `dissolved_at` set) —
  same bookkeeping-only status as a player-triggered dissolve.
- An empty `act_text` (e.g. bare `{"move": true}`) skips **both** the act and
  the migration — no migration without narration.
- The initiative line persists as a normal `conversation_message`
  (`speaker='npc'`), its MJ narration as `speaker='mj'`, and both feed
  `analyze_single_turn` — an initiative act can produce `proposed_mutation`
  rows like any other line; only the act of speaking/moving itself is exempt.

### C3 — Widening the vote to the whole location (Option A v1)

C1/C2 only considered the player's own gathering. C3 widens the candidate pool
to **every active member of every open gathering at the player's location** —
a hostile NPC two tables over can now notice and approach.

- **Two-section signal list** — "DANS LE GROUPE DU JOUEUR" (in-group; react in
  place) vs. "DANS UN AUTRE GROUPE" (non-members; can only intervene by
  getting up and joining). Structural, not flavour: it tells the model the
  *only* way a non-member can act is to move.
- **Structural `move=True` override** — if the vote picks a non-member, the
  caller forces `move=True` regardless of the act-generation result. A
  non-member NPC cannot "act in place" in the player's scene; true by
  construction rather than relying on the model. `migrate_npc`'s idempotent
  guard makes this a no-op if an in-group NPC ever emits `move=True` itself.
- **Conservatism lever** — `MJ_INITIATIVE_SYSTEM_PROMPT` now requires a
  strong, narratively grounded reason for picking a "DANS UN AUTRE GROUPE"
  candidate; when in doubt, `{"act": false}` — guards against the wider pool
  inflating `act: true` just because more names are listed.
- **v1 context-assembly choice for non-members** — a winning non-member's
  fresh context (D1) is assembled with `gathering_id = <player's gathering>`
  — it sees who it's *approaching*, not who it currently stands with. The
  whole location is "at a glance" distance (same room). Revisit if
  out-of-sight gatherings (different rooms) are ever introduced.
- **No mechanical tie-break** — left entirely to the MJ's judgment in one JSON
  call; no secondary scoring or randomization, consistent with `act:
  true/false` already being a judgment call.
- **Open question (not yet measured)** — whether the model "prefers" in-group
  over distant candidates given a mixed pool. To verify in play (cockpit):
  compare a mono-gathering scene vs. a multi-gathering scene without strong
  relations. Not yet executed.

---

## MJ CONTEXT — the player's perception boundary (schema v1.12, scope D-b3)

Until now the MJ (`pt-mj-narration`) was a near-blind presentation layer: it
received the NPC's reply and the bare scene labels (`npc_name`,
`location_name`) and dressed them in prose. It had no material to describe
the room, reference who else was around, or anchor a scene in something that
had actually happened in the world. `assemble_mj_context` (in `context.py`)
gives it exactly that — and only that.

**The doctrine:** the MJ context contains ONLY what the player may perceive
or already knows. This is a *different* boundary from the NPC's
(`assemble_npc_context`, gated by NPC→interlocutor relation intensity) — the
MJ doesn't roleplay a character with opinions and secrets to guard, it
narrates the player's surroundings. So its boundary is simpler and stricter
in one sense (no NPC-private knowledge ever, regardless of relation) and
broader in another (the player's own knowledge, including their own
`is_secret` rows, is fair game — it's not a leak to describe to the player
what they already know).

**Static vs dynamic split:**

- **Static** (assembled once at conversation start, snapshotted under the new
  `"mj"` key in `conversation.injected_context`, alongside the existing NPC
  snapshot): the location's name/description and an allow-listed slice of its
  `subculture` (ambiance is perceptible; `magic_status` is not, by default),
  the player character's own `knowledge` rows, and up to 5 of the most recent
  `event` rows with `knowledge_status IN ('public', 'confirmed')` for the
  world (location-matched events preferred). The snapshot is the baseline a
  future bleed auditor compares MJ narration against.
- **Dynamic** (read fresh at every narration phase, never snapshotted):
  co-present NPCs' public name + public `entity.description`, read from the
  gathering roster (`gathering_member` with `left_at IS NULL` — the same
  single source of truth `_active_members` uses). Fresh because C2 migrations
  change who's standing where mid-conversation.

**Structural exclusions, by query construction, never by instruction:** no
NPC `knowledge` row (the assembler never reads another entity's knowledge at
all), `character.secrets`, `entity.internal_name`, entities with `is_public =
FALSE`, relations (the assembler doesn't query `relation` at all), and
`event` rows with `knowledge_status IN ('secret', 'rumor')`. This is the
invariant the new assembler most directly threatens, simply by being a new
context consumer — hence "impossible by construction" rather than "the prompt
says don't".

**Wiring:** `pt-mj-narration` and `_build_mj_user` (all three response
modes — `dialogue`, `npc_reaction`, `scene`) receive the rendered context as a
"CONTEXTE DE SCÈNE" block; the MJ system prompt gains an anti-invention rule
("describe only from the provided context"), mirroring the `npc_dialogue`
rule. `scene` mode benefits most — environment prose finally has material to
draw on. The `relevance_hint` parameter (also added to `assemble_npc_context`)
is accepted and inert: a future relevance-selection stage may only narrow
this set further, never widen it.

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
