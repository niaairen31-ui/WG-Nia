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

## CONVERSATION ANALYSIS — Window analysis (BRIEF-09, schema v1.21)

A single function, `analyze_window(conversation_id, db, ...)` in
`analyzer.py`, owns all proposal generation for a conversation. It replaces
the former two-tier system (a per-turn immediate pass that owned
`relation_change`, plus a final pass that filtered it out) — see "Deferred
decisions" for the rationale.

### `analyze_window`

1. **Load** — reads the `conversation` row and its `conversation_message`
   rows with `turn_order > conversation.last_analyzed_turn` and
   `speaker ∈ {player, npc}` (`mj` rows are never fed to the model), ordered
   by `turn_order`.
2. **No-op** — if there are no such rows, return `[]` immediately: no model
   call, no marker change, no commit. This is the steady state between scene
   boundaries when nothing new has happened since the last analysis.
3. **Prompt** — the `pt-conversation-analysis` template (`usage =
   conversation_analysis`, v3 — see "Anti-inflation rubric" below) over the
   unanalyzed transcript + the `injected_context` snapshot.
4. **Call** — `ollama_client.chat()` with `format="json"`. Thinking mode
   enabled; `strip_think()` removes the block before parsing.
5. **Parse failure** — if the response is not valid JSON or not a list, log a
   warning and return `[]` WITHOUT advancing `last_analyzed_turn` — the next
   trigger retries these same turns.
6. **Normalise + validate** — `_normalize_to_schema(raw_item, conv)` maps the
   model's natural field names to our schema; items that cannot be normalised
   (including a `relation_change` whose `entity_a_id`/`entity_b_id` cannot be
   resolved — see "Multi-NPC `relation_change` attribution" below) are skipped
   and logged. ALL THREE mutation types survive — `relation_change` is no
   longer filtered.
7. **Write-time dedup** — `_mutation_match_key` (idempotent types only:
   `new_knowledge` on `(entity_id, subject)`, `status_change` on `entity_id`)
   against existing `proposed` rows for this conversation, so a fact already
   flagged by `analyze_overhearing` (Tier 4, fires sync-after-stream every
   turn) for the same window isn't re-proposed. `relation_change` is never
   deduped — it accumulates, and `analyze_window` is its only producer.
8. **Persist** — `db.add()` each surviving mutation (`proposed_by =
   'local_ai_window'`), set `conversation.last_analyzed_turn =
   max(turn_order)` over the rows just read, single `db.commit()`. Returns the
   list of written mutations.

### Triggers

`analyze_window` fires automatically at three scene-boundary points, plus a
manual button. Each automatic trigger calls it inside `try/except (Exception,
SystemExit)`, logged via `_log.exception` — analysis must never block a scene
transition or a conversation close.

- **(a) Conversation close** — `POST /api/conversations/{id}/end` and
  `POST /api/travel` (the loop that closes the player's open conversations),
  before the row's `status` is set to `closed`.
- **(b) Player location transition** — `enter_scene`, inside the "no open
  gatherings yet" guard: any conversation the player left open at a
  *different* location is analyzed before `enter_location` regenerates the
  new location's partition.
- **(c) Gathering dissolution** — `gathering.py`'s `enter_location`
  (dissolving the location's open gatherings before regenerating) and
  `migrate_npc` (auto-dissolving an emptied source gathering): any
  conversation still open on the dissolving gathering is analyzed first.
- **Manual** — the cockpit's **Analyze** button
  (`POST /api/conversations/{id}/analyze`). Returns `{"status":
  "nothing_new", "count": 0, "proposals": []}` when there are no unanalyzed
  turns (no model call).

### Force (debug path)

`--force` (cockpit `Force` button, or `scripts/analyze_conversation.py
--force`) deletes ONLY `status='proposed'` rows for the conversation and
resets `conversation.last_analyzed_turn` to 0, then re-runs over the full
transcript. Reviewed rows (`applied`, `approved`, `rejected`) are NEVER
deleted — history is sacred.

> Force is a debug path: re-analyzing the full transcript may re-propose
> relation deltas that were already applied. Review re-proposals manually.

### Anti-inflation rubric (`pt-conversation-analysis` v3)

Per-turn analysis caused relation inflation — every cordial exchange produced
a `+5 relation_change`, aggressive scenes could still net positive, and the
review queue filled with near-duplicate deltas. `analyze_window` runs over a
multi-turn window instead, and the prompt (v3) instructs the model to: emit at
most ONE `relation_change` per ordered entity pair per window, representing
the NET effect across the whole window (not a sum of per-turn increments);
not treat routine/cordial exchanges as relation-worthy by themselves; and keep
`|intensity_delta|` proportionate to the weight of the event. This moves
`relation_change` ownership from "one delta per turn, summed" to "one delta
per pair per window, judged holistically".

### Multi-NPC `relation_change` attribution

In a window spanning a multi-NPC gathering, more than one entity pair may be
in play. `_normalize_to_schema` therefore does NOT fall back to a
window-level "entity_a" (the old `npc_entity_id`/`conv.npc_id` default is
removed): a `relation_change` is kept only if the model's own output resolves
both `entity_a_id` and `entity_b_id` per item; otherwise the item is skipped
and logged (`[skip] Item {i}: normalization failed`). A lost-but-visible
consequence beats a false-but-recorded one. Per-item resolution against the
gathering roster is deferred — see "Deferred decisions".

### Overhearing analysis pass (`analyze_overhearing`, Tier 4)

A per-turn pass, fired (sync-after-stream, `dialogue` turns only) after the
main turn's NPC/MJ phases. NPCs within earshot of a conversation may
**acquire** or **upgrade** knowledge from what was said — always via
`proposed_mutation`, never by direct write. A receiver with no existing row on
the subject gets a `new_knowledge` acquisition; a receiver who already holds a
row gets a `knowledge_change` upgrade proposal ONLY if the computed level is
strictly higher (monotone) — see "Deterministic level ladder" below (v1.17).
It coexists with `analyze_window` via the write-time dedup in step 7 above:
`analyze_window` never re-proposes a `new_knowledge` acquisition that
`analyze_overhearing` already flagged for the same window (idempotent types
only — `relation_change` and `knowledge_change` are not covered by this key
and may both legitimately appear from either pass).

The model's only job is closed-list classification (`pt-overhearing-classification`, `usage = overhearing_classification`): given the turn's player/NPC lines and the world's distinct `knowledge.subject` values, return `[{"subject": ..., "speaker": "player"|"npc"}, ...]`. All attribution, receiver computation, and level computation happen in code.

Guard chain, all before any model call except (g)/(h)/(j)/(k) which run per classified element:

- **Turn-mode guard** — re-checks `npc_line` is non-empty even though the caller already gates on `dialogue`.
- **Receiver computation (b)** — eligible receivers = active members of the conversation's gathering (`gathering_member.left_at IS NULL`, the single roster source) MINUS the responding NPC MINUS the player. Empty set → return with **no model call** (two-party conversations cost nothing).
- **Subject list (c)** — `SELECT DISTINCT subject FROM knowledge` scoped to the world. Empty → no model call.
- **Normalization (e)** — only elements whose `subject` is an EXACT member of the closed list and whose `speaker` ∈ {`player`, `npc`} survive; everything else is dropped and logged. No fuzzy matching.
- **Speaker resolution (f)** — `speaker = "npc"` → the responding NPC's entity id; `speaker = "player"` → the conversation's player entity id. The eligible receiver set additionally excludes the resolved speaker (an NPC never overhears itself).
- **K2 guard (g)** — load the SPEAKER's `knowledge` row for the subject. No row → skip the element entirely. The speaker's canonical knowledge is the only authority; a speaker "knowing" without a row is model noise.
- **Secret guard (h)** — if the speaker's row has `is_secret = TRUE`, skip. Secrets are structurally excluded from NPC context, so a classification match on one is spurious by definition — this extends the secrets invariant to propagation.
- **Existing-row branch (j)** — for each eligible receiver: no existing row on the subject → `new_knowledge` acquisition (unchanged); an existing row → `knowledge_change` upgrade IF the computed level is strictly higher than the receiver's current level (monotone), else skip silently — no noise in the queue.
- **Proposal-dedup (k)** — skip a receiver if a `proposed` row already exists for this `(conversation_id, receiver entity_id, subject)` of the SAME mutation type (`new_knowledge` or `knowledge_change`) — re-stating a fact later in the conversation must not stack proposals.

**Deterministic level ladder (i, decision E)** — ladder `unaware < rumor < suspicious < partial < knows < fully_understands`, computed entirely in code (the model never judges levels):

- **Overhearing**: the acquired/target level is one step below the speaker's row level, floored at `rumor`:

```
fully_understands → knows
knows             → partial
partial           → suspicious
suspicious, rumor → rumor
```

- `analyze_overhearing` caps the acquired/upgraded level at `knows` in code
  (`_KNOWLEDGE_LEVEL_DOWNGRADE` above). `analyze_window` applies no such
  ceiling: a model-proposed `knowledge_change` only passes
  `_apply_mutation`'s monotonicity guard (no level decrease) — there is no
  upper bound. The effective ceiling on this path is creator approval, not a
  structural guarantee. Downgrades, forgetting, and `is_incorrect` correction
  remain creator CRUD only.
- **Monotone everywhere**: levels never go down through this path; if the computed target <= the receiver's existing level, nothing is proposed (silent skip at detection) or nothing is applied (the apply-time guard, "Needs attention").

**Write (l)** — one `proposed_mutation` per surviving (receiver × subject), `proposed_by = 'local_ai_overhearing'`:
- `new_knowledge` (no existing row): `payload.content` copied VERBATIM from the speaker's row (anti-invention), `payload.is_incorrect` inherited, `payload.source = "overheard:{conversation_id}:{speaker_entity_id}"`. `rationale`: `Overheard from {speaker name} at {location name} (level {speaker level} → {acquired level})`.
- `knowledge_change` (existing row, upgrade): `payload = {entity_id, subject, from_level, to_level, source}` with `source = "overheard:{conversation_id}:{speaker_entity_id}"`. `rationale`: `Overheard from {speaker name} at {location name} ({from_level} → {to_level})`.

`_apply_mutation` implements `knowledge_change` (see "apply_mutation" above) —
both `analyze_overhearing` and `analyze_window` proposals flow through the
same canon-write path and creator approval as every other mutation type.

---

## CREATOR REVIEW COCKPIT

`src/world_engine/cockpit/` is the local web UI for live play **and** creator
review. It is the **only place where world state gets written** in response to
approved proposals.

### Shell layout (schema v1.27, BRIEF-14)

The cockpit is a **two-mode shell**: **Play** and **Création**. Both are
client-side display toggles (no server-side role gating).

**Play** — three sub-tabs:
- *Discussion* — the scene view (location, gatherings, Voyager travel control,
  join phrase) and the conversation transcript, full-width. The review queue is
  not present here.
- *Historique* — the conversation list; clicking a conversation loads it and
  switches to Discussion.
- *Mes savoirs* — read-only view of the resolved player character's knowledge
  rows (subject, level, content, source). Fetched fresh on each activation.

A persistent banner "Tu incarnes : {name}" shows the active world's player
character across all Play sub-tabs. Since BRIEF-45, this id is resolved
structurally (`character_type='player'` scoped to the active world, via
`GET /api/bootstrap`) rather than the literal `char-player`. Since BRIEF-46,
a PC can be created and placed: the *Personnage joueur* sub-tab has a
minimal create-PC form (name + starting-location dropdown) that posts to
`POST /api/characters/player` and re-bootstraps on success. **One player
character per user per world is the v1 invariant**, defended structurally
by the partial unique index `idx_character_one_pc_per_user_world`
(`character(world_id, user_id) WHERE character_type = 'player'`) — not by
route discipline alone. Deferred: editing/deleting a PC after creation,
multiple PCs per user, a PC switcher/picker, and generating a PC's stats or
backstory from a model (the creator types the name; skills start flat at
tier 0, exactly like the seed).

**Création** — seven sub-tabs:
- *NPC* — character entities that are not player characters.
- *Personnage joueur* — player characters (from `/api/skills/player-characters`),
  with the Fiche skill editor (`#skill-main`) rendered by default and the
  create-PC form + generate panel (`#pj-create-block`) collapsed behind a
  PJ-specific `+ Nouveau` button (`pjCreateNew`, BRIEF-60); Fiche is
  deliberately left outside the gate so it shows without a click; the
  list-selection rewire of the Fiche (A2) remains deferred.
- *Lieux* — location entities (including the discoverable-details editor).
- *Factions* — faction entities.
- *Objets* — item entities (create + edit via the existing CRUD path).
- *Artefacts* — read-only scaffold; creation deferred pending backend support.
- *Review Queue* — the full mutation queue (Proposed / ⚠ Needs attention /
  Applied / Rejected), batch controls, unit approve/reject.

Each sub-tab fetches its own data on activation (no polling, no boot-time
pre-fetch for queue or conv-list).

### What it does

- **Live play** — enter a location (scene view), write a join phrase, then type
  turns. Each turn runs the three-phase `/say` flow (interpret → NPC → MJ; see
  below). Overhearing proposals (Tier 4) accumulate silently each turn; window
  analysis runs only at scene boundaries.
- Reads conversations and renders them as a chat transcript with the MJ narration
  as primary text and the raw NPC line as a muted audit annotation below each turn.
- Triggers (re-)analysis via `analyzer.analyze_window` — automatically at
  scene-boundary triggers, or manually via the **Analyze** button (in Discussion).
- Lists the review queue in Création → Review Queue, filterable by status
  (`proposed` / applied / rejected / needs attention).
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
   open gatherings exist if they're not in one yet) and an `item_list`
   (`context.format_item_list_for_interpretation` — the player's tracked items,
   e.g. "Objets du joueur : Dague."; since BRIEF-08/D2a.1, identical to
   `format_inventory_line`, no equip-state annotation). Returns `(mode,
   reference, used_object)` — `reference` is the player's exact words naming a
   group, populated only for `join`; `used_object` is the canonical name of the
   item the player physically uses this turn (`null`, or `"unknown_object"` if
   their wording matches nothing in `item_list`). Falls back to `(dialogue, "",
   null)` on any failure — a misclassification or extraction failure must never
   break a turn.

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

   **Possession check (binary, BRIEF-08/D2a.1, schema v1.19)** — runs
   immediately after interpretation, for any non-`join` mode where
   `used_object` is not `null`. The CODE judges possession against canon
   `item` rows — the structural fix for a close-step finding on D1: the 8b
   model does not reliably honor prohibition-style rules in the narration
   prompt (same lesson as secrets — structural mechanisms, not prompt
   discipline). The check is binary: `used_object` owned by the player (a
   matching `item` row with `owner_id = player_id`) → pass; `"unknown_object"`
   or no matching owned `item` row → **refused**. `item.equipped` is no longer
   read — the equipped/stowed distinction went dormant in this step (see
   "Auto-applied mutations" below).
   A refusal no longer skips the NPC phase — the failed gesture is socially
   visible. `_stream` forces `mode = ResponseMode.dialogue` so the turn
   proceeds normally: the responding NPC gets a one-shot `[GESTE RATÉ]`
   instruction (not persisted, same pattern as `[MODE RÉACTION
   NON-VERBALE]`) telling it what it just witnessed, and its reply is
   persisted as a normal `npc` row. The MJ system prompt gets a one-shot
   `[ACTION REFUSÉE]` instruction (not persisted) directing it to narrate the
   failure in fiction without breaking the fourth wall, then integrate the
   NPC's reaction "comme pour un tour normal" (the dialogue MJ template
   already quotes `{npc_reply}` verbatim).

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

Overhearing analysis (Tier 4, `analyze_overhearing`) still runs
sync-after-stream for `dialogue` turns, after the MJ phase. Window analysis
(`analyze_window`, BRIEF-09) no longer runs per turn — it fires only at scene
boundaries (conversation close, location transition, gathering dissolution)
and via the cockpit's manual Analyze button; see "CONVERSATION ANALYSIS —
Window analysis" above. No `proposed_mutation` rows (other than overhearing's)
are written during a turn itself.

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
write canon **in response to an AI proposal**, after creator approval (or,
for `item_update`, after self-approval at proposal time, when a producer
exists — see "Auto-applied mutations" below; same function, same guards). The
other sanctioned path is the **author CRUD** (see below), for the creator's
direct edits — see CLAUDE.md, "Two sanctioned canon-write paths, no others."
Five mutation types are implemented:

| mutation_type    | What is written |
|------------------|-----------------|
| `relation_change`  | Find or create the Relation row; apply intensity delta (clamped 1–100); append previous state to `change_history`. |
| `new_knowledge`    | Insert a `knowledge` row; inherits `session_id` from the source conversation. |
| `status_change`    | Update `entity.status` + `entity.updated_at`. |
| `item_update`      | Set `item.equipped` (BRIEF-07, schema v1.19). Verifies the item exists and `owner_id IS NOT NULL` (the schema CHECK: no equipping without an owner) — on violation, left at `status='approved'` with a note, never wrongly applied. **Dormant since BRIEF-08/D2a.1** — no live code path produces this mutation type; the branch and the cockpit toggle remain functional for reactivation. |
| `knowledge_change` | Find the `knowledge` row by `entity_id` + `subject` (never creates — that's `new_knowledge`'s job); append previous state via `_append_knowledge_history(row, "apply_mutation")`; update `level` to payload `to_level`, `source` to payload `source`, `updated_at`. Guards: row not found → "Needs attention" (`knowledge row not found`); current `level` >= `to_level` (monotone re-check at apply time) → "Needs attention" (`level already >= proposed`). |

Any other type is left at `status = 'approved'` with a note — never wrongly
applied. Better un-applied than wrongly applied.

Canon writes are wrapped in a **SAVEPOINT** (`db.begin_nested()`): if the apply
fails, only the canon writes roll back; the mutation-row update (status,
`reviewed_at`, error note) lives in the outer transaction and always commits.

### Auto-applied mutations

> **Auto-applied mutations.** A mutation may bypass creator review and
> self-apply at proposal time only if ALL of the following hold: (1) it
> is trivially reversible by an inverse mutation of the same type; (2)
> it creates and destroys nothing — no entity, no knowledge, no event;
> (3) it affects no relation and no knowledge state; (4) it still flows
> through `_apply_mutation` and is recorded with `status='applied'` and
> its own `proposed_by` tag, fully visible in the review cockpit. `item_update`
> (equip toggle) remains the sole member of this category, currently
> **dormant**: live D2a play showed the equipped/stowed distinction cost
> playability with no game decision depending on it, so the BRIEF-08/D2a.1
> possession check went binary and the interpretation-side producer
> (`_auto_apply_item_update`) was removed — drawing/stowing a possessed item
> is free narration again. The apply branch and the cockpit toggle remain
> functional, ready for reactivation if combat design later needs an in-hand
> state. Any extension of this category is a creator decision, recorded here.

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

**State-transition type — `item_update` is intentionally excluded** (BRIEF-07,
schema v1.19). Redundancy is already prevented at proposal time — a toggle
that wouldn't change `item.equipped` is a silent no-op, no row is written —
and a legitimate draw→stow→draw sequence within one conversation must apply
each time. Dormant since BRIEF-08/D2a.1 (no live producer); this exclusion
remains correct documentation for the cockpit toggle's apply path.

**`knowledge_change` is also intentionally excluded** (v1.17). Successive
legitimate upgrades in one conversation (e.g. `rumor → partial`, then later
`partial → knows`) must both apply. The monotone re-check inside
`_apply_mutation` (current `level` >= proposed `to_level` → "Needs
attention") is the correct guard here — an identity-based duplicate check
would incorrectly block the second, legitimate upgrade.

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
  (`speaker='npc'`), its MJ narration as `speaker='mj'`, and both are
  included in the next `analyze_window` pass (BRIEF-09) — an initiative act
  can produce `proposed_mutation` rows like any other turn; only the act of
  speaking/moving itself is exempt.

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

## OBJECT PERMANENCE — ambient props vs tracked items (schema v1.18, BRIEF-06)

Live tests showed the need to distinguish two kinds of "things" in a scene:

- **Ambient props** (a mug, a stool, a stone) — never canon. The MJ invents
  them freely in narration, on one condition: they must be *plausible for the
  current location* (no beer mug in a desert or a church). The player can
  gesture at this kind of object without it ever existing as a row anywhere.
- **Tracked items** (weapons, letters, anything the story needs to persist) —
  canon entities, type `item`, extension table `item`. Three states, never
  deletion: **equipped** (`owner_id` set + `equipped=TRUE`), **carried but
  stowed** (`owner_id` set + `equipped=FALSE`), **lying in a location**
  (`owner_id` NULL + `location_id` set). `artifact` remains reserved for
  magical/historically significant objects; an `item` can be promoted to
  `artifact` later if the fiction demands it.

**Arbitration is prompt-level, with in-fiction refusal — not a code gate.**
Every turn, the MJ narration prompt (`pt-mj-narration`, schema v1.18) is
given a fresh, non-cached inventory line built by
`context.format_inventory_line` — `"Équipé : …. Sur soi : ….\"` — listing the
player character's `item` rows split on `equipped`. The system prompt's
"RÈGLES SUR LES OBJETS" then tell the model: ambient props are free if
plausible for the location; tracked-item actions (attack, cut, show) require
the object to be in the inventory line AND equipped; a stowed item must be
"sorted out" first; and if the player invokes an object they don't possess or
that isn't equipped, the MJ refuses **in fiction** ("ta main ne trouve que du
vide"), never breaking the fourth wall. No code path validates or blocks the
player's input — the boundary lives entirely in what the model is told it can
draw on, the same "exclusion, not restraint" doctrine as secrets and the MJ
perception boundary.

**Static possession only, in v1.** This step delivers the read side: items
exist in canon, the player owns them, the MJ knows what they carry. Nothing
in-game changes canon — if the player narrates "je range ma dague", the MJ
narrates it but the `equipped` flag doesn't flip; the creator corrects via
the cockpit entity flow if needed. A temporary one-turn mismatch between
fiction and the inventory line is accepted. No new `mutation_type` is added;
`analyzer.py` and `_apply_mutation` are untouched.

**Deferred to D2 (next step):**
- `item_transfer` mutation type (give/take/drop/pick up).
- `entity_creation` for ambient-prop promotion (e.g. a letter the player
  picks up becomes a tracked `item`), with creator-editable content at the
  review checkpoint.
- In-game equip/unequip as a detected, applied mutation.
- NPC inventories (no injection into NPC dialogue contexts in v1; no
  NPC-owned items seeded).
- The player's personal storage location ("sa maison").
- Per-location ambient-props override (`ambient_affordances` in
  `location.subculture`/`metadata`) — model judgment only for now.

---

## PHYSICAL LAYER — skill sheet (schema v1.22, BRIEF-10)

The first piece of a future dice/arbiter layer: a player character's physical
and sensory aptitudes, recorded as a small per-domain sheet rather than a
single number.

- **Dedicated `skill` table, full change history.** Four domains —
  `physical`, `agility`, `perception`, `composure` — each a row with a
  `tier` in `-1..2` (-1 weak, 0 average, +1 trained, +2 exceptional), the
  same "history is sacred" pattern as `relation`/`knowledge`:
  `change_history` is an append-only JSON array of
  `{"tier": <old>, "changed_at": <iso>, "by": "creator"}` snapshots, and
  `updated_at` bumps on every real change. A no-op write (resubmitting the
  current tier) touches neither.
- **Seeded minimally, evolution is creator-controlled.** `seed_pilot.py`
  creates one test player character (`char-pc-test-2`) with all four
  domains at `tier=0` — a starting point, not a balanced character. From
  there, tiers change only through the cockpit "Fiche" view (creator mode),
  a direct canon write with no `proposed_mutation` — the same rule as every
  other creator-mode edit (Author CRUD, see "Author CRUD" above). There is
  no automatic progression yet.
- **Create-route seed (BRIEF-46) is forward-only; BRIEF-59 is the explicit
  retrofit.** `POST /api/characters/player` seeds the four base-domain rows
  unconditionally for every PC created through it. PCs that predate that
  route (e.g. `char-player` / Joran Vey, created directly in the seed or
  before BRIEF-46) received no `skill` rows at origin and must be backfilled
  explicitly via `migrate_v1_65_pc_skill_backfill.py`. A lazy self-heal on
  read or create was considered (BRIEF-59 rejected B2) and rejected:
  implicit healers obscure data state and violate the `structural over
  disciplinary` principle. The migration is the intentional, one-shot,
  idempotent retrofit.
- **NPCs do not get `skill` rows.** An NPC's physical capability, when a
  scene needs to compare it against the player's, lives as a single
  opposition tier in `entity.metadata` (key `physical_tier`, `-1..2`,
  default `0`) — read later, by the arbiter step. This keeps the `skill`
  table exclusively a player-character sheet and avoids seeding four rows
  per NPC for a number that, for NPCs, only ever needs to be one.
- **Social domains are a standing guard, not a deferral.** Persuasion,
  deception, charm and similar social aptitudes are never `skill` domains.
  Those interactions stay in dialogue/relation territory (`relation_change`
  via window analysis) — adding a "social skill" would create two competing
  systems for the same kind of outcome. This is a permanent design
  boundary, to be re-affirmed (not relaxed) if a future step considers
  adding social mechanics.

**Out of scope for this step** (see also "Deferred decisions" below): no
dice/arbiter or `ResponseMode.physical` (the next step that consumes this
sheet); no `skill_change` mutation type or automatic progression; no NPC
`skill` rows or `physical_tier` seeded yet; no condition ladder, `scene_state`,
HP, or opposed rolls. The `/say` flow, analyzer, and prompt templates are
untouched.

---

## PHYSICAL LAYER — part 2: arbiter + dice (BRIEF-11, schema v1.23)

The first consumer of the skill sheet: a fourth `/say` interpretation mode for
actions with an uncertain physical outcome, a small classification ("arbiter")
call, and a **pure Python 2d6 roll** — the model never rolls.

- **`/say` interpretation modes relevant to physical actions** (`pt-mj-interpretation`, v4):

  | Mode           | Routes to                                                |
  |----------------|-----------------------------------------------------------|
  | `dialogue`     | words/question/solicitation toward the NPC — unchanged, highest priority after `join`. |
  | `physical`     | a physical attempt whose outcome is uncertain — climbing, grabbing, dodging, forcing, sneaking, resisting. Routed to `_arbitrate()` + `resolve_physical()`. |
  | `npc_reaction` | a gesture/action toward the NPC with a *certain* outcome — wordless reaction, no roll. |
  | `scene`        | environment action, no stake, NPC not engaged — no roll. |

  `join`'s existing absolute priority (player ungrouped + intent to approach a
  group) is unchanged and still takes precedence over `physical`.

- **Arbiter circuit.** `_arbitrate()` fires only for `physical` turns, between
  phase 0 (`mj_interpretation`) and the NPC phase. Non-streaming `chat()` with
  `format="json"` and `/no_think`, template `pt-mj-arbiter`
  (`usage='mj_arbitration'`, `world_id=NULL`). Input: the player's line and the
  names of co-present NPCs (never raw entity rows — same context-assembler
  boundary as everywhere else). Output:
  `{"domain": "physical|agility|perception|composure", "opposed_npc_id": "<name
  or null>"}`. The model **classifies only** — it never rolls and never decides
  outcomes. `_arbitrate` resolves the returned name to an entity id via
  case-insensitive lookup against the actual roster (same "exact match, never
  invented" pattern as `_resolve_join_target`'s `reference`). On any failure —
  bad JSON, unknown domain, Ollama error, timeout — it falls back to
  `("physical", None)`; a misclassification must never break a turn.

- **`resolve_physical` (resolution.py) — pure Python, no DB/model access.**
  `roll = randint(1,6) + randint(1,6) + player_tier - npc_tier`, where
  `player_tier` is the player's `skill.tier` for the classified domain (schema
  v1.22, default 0 if no row) and `npc_tier` is `entity.metadata.physical_tier`
  of `opposed_npc_id` (default 0 when absent or unopposed). Band table:

  | Total    | Band      | Meaning                                                  |
  |----------|-----------|----------------------------------------------------------|
  | `<= 6`   | `failure` | the action fails outright.                                |
  | `7–9`    | `partial` | success with a cost/complication, or failure with a silver lining — narration's choice, band is the law. |
  | `>= 10`  | `success` | the action clearly succeeds.                              |

  The `Verdict` (`domain`, `dice`, `modifier`, `total`, `band`) is logged
  (audit) and sent to the player as an SSE event `data: {"verdict": {...}}`
  before narration — same pattern as `npc_raw`.

- **Player-roll rule (verbatim)**: "The roll always belongs to the player.
  When an NPC initiates a physical action against the player, we do not roll
  the NPC's attempt — we roll the player's response (dodge, resist, endure),
  with the NPC tier as opposition. One mechanic, one code path, one audit
  point." There is no code path that rolls for an NPC; an NPC-initiated grab is
  handled by the player describing their own response, classified and resolved
  exactly like any other physical turn.

- **NPC phase for physical turns.** If `opposed_npc_id` is set, that NPC is
  called exactly like `npc_reaction` (one-shot wordless reaction instruction)
  with the verdict band appended so the reaction matches the outcome; the
  `npc` row IS written canonically, so `analyze_window` keeps proposing
  `relation_change` for fights as usual. Unopposed physical turns behave like
  `scene` — no NPC call, no `npc` row.

- **MJ narration constrained by the verdict.** The `physical` branch of
  `_build_mj_user` injects a verbatim rubric: *"Tu narres les conséquences ;
  tu ne rejuges JAMAIS le résultat"* — `failure` must not be softened into a
  partial success, `partial` must carry a real cost or complication (or a
  failure with an unexpected upside), `success` succeeds cleanly.

- **Canon boundary.** A physical scene can at most neutralize or constrain.
  Death, permanent injury, durable capture, or an item being taken require a
  `proposed_mutation` and creator approval — never a direct effect of this
  narration. This is enforced twice: at the prompt level (the rubric
  explicitly forbids death/permanent injury/durable capture, capping outcomes
  at "neutralized or constrained"), and structurally (the resolution path —
  arbiter, dice, NPC phase, narration — writes **zero** canon; no new
  `relation`/`knowledge`/`entity` row is ever produced directly by it).

---

## PHYSICAL LAYER — part 3: scene constraints, condition ladder (BRIEF-12, schema v1.24)

Adds `conversation.scene_state` — an ephemeral JSON blob that tracks transient
combat/constraint state for the duration of a scene. It is **not canon**: only
`proposed_mutation` rows (after creator approval) produce lasting consequences.
Same design philosophy as `gathering`.

### scene_state structure

```json
{"constraints": ["gagged"|"restrained"|"blindfolded"],
 "condition":   "unharmed"|"bruised"|"injured"|"neutralized",
 "frozen":      false,
 "history":     [<previous state snapshots>]}
```

Every write to `scene_state` appends the previous state to `history[]` before
overwriting — history is sacred, even for ephemeral state.

### Constraint gating

Constraints override the MJ interpretation outcome **in code**, before any
model call:

| Constraint    | Trigger                               | Route                       | Effect on success     |
|---------------|---------------------------------------|-----------------------------|-----------------------|
| `gagged`      | player sends dialogue turn            | physical, composure domain  | (none — just narrated)|
| `restrained`  | any physical / scene / npc_reaction   | physical, physical domain   | removes `restrained`  |
| `blindfolded` | (always active when in constraints)   | context assembler           | excludes location desc + NPC appearance |

Both gated turn types resolve at `npc_tier=1` — a fixed pilot difficulty
(schema v1.25). `opposed_npc_id` remains `None` for both; the 1-point
penalty represents the resistance of the gag / restraint, not a named NPC.
Possession check is skipped for constraint-gated turns (the player
isn't deliberately trying to use an item).

Blindfolded exclusion is **structural data exclusion** in `assemble_mj_context`:
`location.description = None`, `co_presents[].description = None`. Never an
instruction; enforced at the data boundary.

### Condition ladder

`unharmed → bruised → injured → neutralized` — monotone for engine writes.

Moved only on `violent=True` physical verdicts (new `pt-mj-arbiter` v2 field):
- **failure**: degrade one step on the ladder (partial never degrades
  condition — it is a complication band, not a damage band; keeping the three
  2d6 outcome bands mechanically distinct also keeps combat survivable).
- **success**: no change.
- `neutralized` auto-sets `frozen=True`.

Reaching `injured` or `neutralized` triggers an automatic `status_change`
proposal with `proposed_by='engine'` — a new value for `ProposedMutation.
proposed_by`. The proposal follows the same review queue as AI proposals; the
creator approves or rejects it. It does not auto-apply.

### Frozen scene checkpoint

When `scene_state.frozen = True`, `/say` short-circuits immediately: player
message is persisted, a fixed French MJ message is streamed as SSE narration,
no model calls are made. The creator panel (see below) can unfreeze.

### Arbiter v2

`pt-mj-arbiter` bumped to v2: four output fields instead of two.

```json
{"domain": "physical|agility|perception|composure",
 "opposed_npc_id": "<name or null>",
 "applies_constraint": "restrained|gagged|blindfolded|null",
 "violent": true|false}
```

`applies_constraint`: populated on failure/partial when the turn has a
constraint theme; `null` on success or when the turn has no constraint
outcome. Written to `scene_state.constraints` only on failure or partial.
`violent`: True when the physical turn involves harm; gates condition
degradation. Falls back to `("physical", None, None, False)` on any error —
a misclassification must never break a turn.

### Condition injection

`player_condition` passed to both `assemble_npc_context` and
`assemble_mj_context`. When not `"unharmed"`, injected as a labelled
`[ÉTAT DU JOUEUR]` line in both NPC and MJ context — NPCs and the MJ know the
player's mechanical state and can react accordingly.

### Creator panel

Creator cockpit gains a `scene_state` panel below the transcript, visible
whenever a conversation is selected. Shows: condition (colour-coded dot),
frozen badge, constraint checkboxes, condition dropdown. Direct edit → PATCH
`/api/conversations/{id}/scene-state` — archives to `history[]`. Refreshes
automatically after each `/say` turn.

### Invariants

- `scene_state` is cleared to `{}` when a conversation closes (same lifecycle
  as the gathering membership: scoped to the scene).
- Constraint and condition writes are batched — a single turn produces at most
  one `history[]` snapshot, even if both a constraint is added and condition
  degrades in the same verdict.
- `proposed_by='engine'` proposals are never auto-applied; they enter the same
  review queue as AI proposals.

**Out of scope for this step**: no `skill_change` mutation type or automatic
progression; no passive perception checks; no richer scene-entry description;
NPC↔NPC dice remain deferred (see "Deferred decisions" below).

---

## PHYSICAL LAYER — part 4: perception & discovery (BRIEF-13, schema v1.26)

Adds explicit search as a `physical` turn with `domain="perception"`, and the
`discoverable_detail` table the creator seeds per location.

### Search routing

An explicit search ("je fouille la pièce", "je cherche un passage", "j'examine
les étagères pour trouver quelque chose") is routed to `physical` by
`pt-mj-interpretation` v5. Distinguishing test, verbatim in the prompt:

> *"chercher activement quelque chose de précis (un objet, un indice, un
> passage) = physical ; simplement observer l'ambiance sans rien chercher de
> précis = scene."*

A stale ambient glance without search intent stays `scene`. The arbiter then
classifies `domain="perception"`, `opposed_npc_id=null` (a search has no NPC
opponent — the future "an NPC intervenes to hide information" is deferred).

### Discovery gating (`_stream`, physical branch)

Fires only when `domain == "perception"` AND `opposed_npc_id is None`. A
perception roll WITH opposition (e.g. spotting something under pressure from a
NPC) is NOT a search and must not trigger discovery.

| Band | No undiscovered detail | Undiscovered detail present |
|---|---|---|
| `failure` | `[FOUILLE INFRUCTUEUSE]` rubric | `[FOUILLE INFRUCTUEUSE]` rubric |
| `partial` | `[FOUILLE INFRUCTUEUSE]` rubric | `[FOUILLE — VERDICT partial]` rubric + `_propose_engine_discovery` |
| `success` | `[FOUILLE INFRUCTUEUSE]` rubric | `[FOUILLE — VERDICT success]` rubric + `_propose_engine_discovery` |

The `[FOUILLE INFRUCTUEUSE]` rubric carries the anti-invention rule verbatim:
no object, letter, passage, or clue may be invented. The model describes the
search gestures only.

For a REACHABLE detail, `partial` reveals its content in full — `partial`
means a complication (noise, a knocked-over object, a co-present NPC
notices), never a withheld or watered-down version of a detail the roll
reached. This keeps the three 2d6 bands mechanically distinct (partial is a
complication band, not a failure band).

`discovery_threshold` is ACTIVE (N1): a detail is a revelation candidate
only when `discovery_threshold <= roll total` (`2d6 + modifier`, the same
total that yields the band). The gate is a fourth `.where()` clause on the
selection query in `_stream()`, applied AT SELECTION (B1) — so an easy
detail stays reachable even when a harder detail shares the location. A
`partial`/`success` search whose candidates are all above threshold returns
no row and reuses the `[FOUILLE INFRUCTUEUSE]` rubric (C1) —
indistinguishable from an exhausted location, so the existence of gated
content never leaks. Effective creator scale: the gate only runs on
partial/success (total >= 7), so thresholds 0-6 all mean "any successful
search"; 7-12 carve out harder finds, up to a near-max roll. Doctrine
refinement (D1): `partial` never *withholds* a detail within its reach; it
may simply fail to *reach* a higher-threshold detail. Same philosophy as
`knowledge.share_threshold`.

### `_propose_engine_discovery`

Sibling of `_propose_engine_injury`. Writes one `ProposedMutation` row:
- `mutation_type="new_knowledge"`, `proposed_by="engine"`
- Payload: `entity_id`, `subject`, `level="knows"`, `content`, `source="discovery"`,
  `is_secret=False`, `discoverable_detail_id` (back-reference for the flip below)
- Status `proposed` — enters the normal review queue, never auto-applied.

### `discovered` flip on APPLY

In `_apply_mutation`'s `new_knowledge` branch, after `write_knowledge`, if
`payload["discoverable_detail_id"]` is set, the corresponding
`DiscoverableDetail` row's `discovered` is set to `True` and `updated_at`
is bumped. This is the ONLY new write inside `_apply_mutation` and is a benign
side-effect inside the already-sanctioned path (wrapped in its SAVEPOINT).

**Why on APPLY, not on propose:** the creator must be able to reject the
proposal; a pre-flipped `discovered` flag would block re-selection in future
conversations even when the mutation was never approved.

**Two guards prevent double-discovery:**
1. `_find_applied_duplicate` (in-conversation): same `conversation_id` + `entity_id`
   + `subject` blocks re-proposing the same subject within one conversation.
2. `discovered=TRUE` query gate (cross-conversation): the selection query in
   `_stream()` excludes `discovered=TRUE` rows, so an already-discovered detail
   is never re-selected in a later conversation.

### Exclusion guarantee

`discoverable_detail` is **never read by any context assembler**
(`assemble_mj_context`, `assemble_npc_context`, or any prompt-building path).
Undiscovered content is absent from every prompt by data exclusion, not by
instruction. Content reaches a model only via the `{detail_content}` injection
on partial/success, and only after code-side selection. This is the same
structural pattern as `character.secrets` and `is_secret=TRUE` knowledge rows.

**`subculture["hidden"]` trap**: the pilot tavern's `subculture` dict has a
`"hidden"` key (`"point d'appui de L'Innommée"`), already excluded from all
context via `_SAFE_SUBCULTURE_KEYS`. This key must NEVER be used as a
discoverable content source, added to the safe-key list, or read into any
prompt. Discoverable content lives ONLY in `discoverable_detail`.

### Creator CRUD

`GET /locations/{id}/discoverable-details` — list (creator view only).
`POST /locations/{id}/discoverable-details` — seed a new detail.
`PUT /discoverable-details/{id}` — edit subject/content/access_level/threshold;
  creator can also reset `discovered=False` to re-enable re-discovery.
`DELETE /discoverable-details/{id}` — hard delete.

All four are creator-direct writes (no `proposed_mutation` checkpoint), same
doctrine as the rest of `crud.py`. In player mode this surface is hidden.

---

## Signpost layer — perceptible entry cues (BRIEF-17, schema v1.30)

Closes the gap BRIEF-13 left open: `access_level='ambient'` existed in the
schema but was structurally dead (no code path read it). This step builds the
missing layer: a **signpost** — a perceptible-without-roll detail, narrated by
the MJ on location entry, that orients the search and falls silent once its
linked content is known.

### Signpost/cluster model (D1)

A **signpost** is one `ambient` row. It can group N `hidden` content rows via
a new `signpost_group TEXT` column: both the panel row and its grouped
contents carry the SAME `signpost_group` value. One signpost groups N
contents; each content belongs to exactly one group. The full N↔N
cardinality (a hidden content under multiple panels) is a named deferral
(D2) — no link table, no `subject` carrying multiple `signpost_group` values.

### E1 — the silence rule

A grouped signpost is silent iff the player holds a `knowledge` row (existence
only — any level counts) for EVERY hidden subject in its cluster. Partial
knowledge (some but not all subjects known) still narrates. Ungrouped ambient
rows (`signpost_group IS NULL`) are always active — a standalone ambient note
with no linked content has no silence condition.

### I3 — the silence judgment is code, never a prompt instruction

`active_signposts(db, location_id, player_character_id)` (context.py) is a
pure DB-read function, sibling to `assemble_mj_context`, called from the entry
path BEFORE any assembler. It returns ONLY the surviving ambient `content`
strings — no `subject`, no `signpost_group` value ever leaves this function,
matching **"Le modèle extrait, le code juge"**: the exhaustion judgment is a
code predicate, the model receives only the surviving prose and writes from
it. `assemble_mj_context` is unchanged — it performs no `discoverable_detail`
query and never holds a `subject` (Preferred wiring from the brief: the entry
path calls `active_signposts` directly and passes the `list[str]` into the
establishment prompt builder, never touching the assembler).

### The consciously-narrowed BRIEF-13 invariant

BRIEF-13 stated "discoverable_detail is never read by any context assembler."
This step narrows that invariant, deliberately and narrowly, for `ambient`
rows only:

- `hidden` rows remain fully excluded from every assembler, exactly as
  before — the existing search/reveal path (`_stream`'s perception branch,
  `_propose_engine_discovery`, the `discovered` flip in `_apply_mutation`) is
  untouched by this step.
- `ambient` content is read, but only by the code-side predicate above, never
  by `assemble_mj_context`/`assemble_npc_context`/any prompt-building path,
  and only its `content` — never a `subject` or `signpost_group`.
- `subculture["hidden"]` remains a trap: `_SAFE_SUBCULTURE_KEYS` is not
  widened by this step.

### F3 / G1 — non-streamed establishment, every entry

`enter_scene` (app.py), after the gathering-partition step, fires a single
non-streamed `chat()` MJ call (`pt-mj-establishment`, new
`usage='mj_establishment'`) on EVERY entry — not gated behind the idempotent
"genuine transition" guard that protects gathering generation, so a same-
location re-render also re-narrates. No change-detection ("a signpost fell
silent / an NPC left") is built — that is G2, a named deferral. The user
message is built from `entity.description` (NOT `location.description` — no
such column), the same `_SAFE_SUBCULTURE_KEYS` slice `assemble_mj_context`
reads, and `active_signposts(...)`'s surviving content. The system prompt
carries the same anti-invention rule as `pt-mj-narration`: describe ONLY from
the provided context, invent no object, letter, passage, clue, or NPC not
given. Established prose names no co-present NPCs (J1) — the scene UI's
gathering list already shows who is present; reading "all NPCs at the
location" into the establishment call is a named deferral, not built.

The call is wrapped in `try/except (Exception, SystemExit)`, logged via
`_log.exception`: a failed or skipped establishment narration must never
block scene entry, same resilience doctrine as the analysis passes.
`_scene_response` gains one field, `establishment: str | None` — `None` when
the call was skipped (no active template) or failed.

### Resolution writes zero canon

The establishment call writes no canon: no `proposed_mutation`, no
`knowledge`, no `entity`. Pure narration, like the MJ narration phase. The
only writes this step introduces to canon are creator-direct CRUD edits of
`signpost_group` — the sanctioned author-CRUD path, no `change_history` (same
as the rest of `discoverable_detail`'s CRUD).

### Cockpit (C1)

The Lieux discoverable-details editor groups rows sharing a `signpost_group`
under a header (`{group} : N ambient panel(s) + M hidden content(s)`), each
row carrying an ambient/hidden badge. Ungrouped rows render individually, as
before. `signpost_group` is editable on create and edit, round-trips through
`crud.py`'s existing CRUD endpoints (creator-direct write, no
`proposed_mutation`).

### Named deferrals (this step)

- **N↔N cardinality (D2).** A hidden content under multiple panels, or the
  full many-to-many. Strictly D1 this step.
- **Pickable-object layer.** "The player picks up the letter" (the `item`
  path) is not in scope. Signpost = perceptible panel + its hidden content
  only.
- **G2 change-cadence.** Narrate-only-on-change is not built; G1 (every
  entry) is the chosen cadence.
- **NPC-naming at entry (J2).** No "all NPCs present, ungathered-scoped" read
  path for the establishment call.
- **NPC opposition to a search, per-character discovery state** — unchanged
  BRIEF-13 deferrals, untouched by this step. (`discovery_threshold`
  activation — resolved by BRIEF-23.)

---

## WORLD MAP — location adjacency (Step A, BRIEF-15, schema v1.28)

### `connects_to` convention

Location adjacency is modelled as a `relation` row with `type='connects_to'`,
`direction='mutual'`, and `intensity=50`. The intensity is a **meaningless
structural default with no gameplay significance** — it must never be read as
an affective or relational signal. The same guard comment is embedded verbatim
in `RELATION_TYPES` in `crud.py`.

**Structural isolation:** every gameplay consumer of the `relation` table is
keyed on a specific character or player entity id. A `connects_to` row has two
location endpoints, so it is invisible to the initiative vote, the NPC context
assembler, and the MJ context assembler (which doesn't query `relation` at
all). Any future world-wide relation scan added to the codebase **must**
explicitly exclude `type='connects_to'`.

### `{x,y}` coordinates and the canon-safe write

Node positions are stored in `location.coordinates` as `{"x": <n>, "y": <n>}`
in SVG canvas units. The write is a **read-merge-write**: on drag-end the
frontend GETs the full entity, sets only `extension.coordinates`, and PUTs the
complete body back. This guarantees that no other location field
(`subculture`, `location_type`, `description`, `access_level`, …) can be
silently clobbered by a position update.

### Graph endpoint

`GET /api/locations/graph` (creator surface, `crud.py`) is the only new route.
It is **read-only** — no writes, no pathfinding, no reachability computation.
Returns active-location nodes (id, name, coordinates) and their `connects_to`
edges (id, entity_a_id, entity_b_id, direction). Dangling edges (pointing at
soft-deleted locations) are filtered server-side so the client always receives a
consistent graph.

The location list payload (`GET /api/entities?type=location`) omits
`coordinates` (it lives in the extension row, not the entity row), which is
why a dedicated graph endpoint is needed rather than reusing the list.

### Deferred (Step A)

- **Graph/layout libraries** — hand-rolled SVG only; no vendored dependency.

---

## WORLD MAP — travel (Step B, BRIEF-16, schema v1.29)

### Travel model

Intent detection via `pt-mj-interpretation` v6 (`travel` mode). On a `travel`
turn in `_stream`:

1. `_location_neighbours(conv.location_id, db)` reads `connects_to` relation
   rows touching the current location and returns `(entity_id, name)` for each
   ACTIVE linked location. Distinct from `GET /api/locations/graph`; no shared
   code (decision D1 — the two readers have different shapes and different
   callers; a real dedup opportunity should be reported but not acted on).

2. **Zero neighbours** → downgrade to `scene`; MJ receives `[SORTIE INTROUVABLE]`
   one-shot instruction; `current_location_id` unchanged; no `traveled`/
   `travel_candidates` SSE.

3. `_resolve_travel_target(reference, neighbours)` does case-insensitive
   exact-ish matching of the player's destination words against neighbour names
   (contract A2 — never guesses, never nearest-match). Returns one `entity_id`
   or `None`.

4. **Resolved (exactly one)** → `[DÉPART]` instruction to MJ; stream departure
   narration; emit `{"traveled": {"location_id": ..., "name": ...}}` SSE;
   call `_perform_travel` → conversation closed, membership closed, location
   updated; `[DONE]`.

5. **Unresolved / ambiguous** → `[DÉPART INCERTAIN]` instruction to MJ; stream
   hesitation narration; emit `{"travel_candidates": [...]}` SSE; conversation
   stays open; player clicks → `POST /api/conversations/{conv_id}/travel`.

6. **Cockpit UI (BRIEF-16b):** `traveled` SSE → `showSceneView()` (mirrors the
   Voyager control's `await loadScene()` success path, closes the transcript view).
   `travel_candidates` SSE → `_renderTravelCandidates` picker (mirrors
   `_renderJoinCandidates`); each button calls `_pickTravelDestination` →
   `POST /api/conversations/{id}/travel` → `showSceneView()`.

### Key decisions

**B1 — Departure only; arrival scene reforms via `enter_scene`.** The travel
turn narrates the DEPARTURE only. Arrival narration ("what you see entering")
is step C, deferred. On the next interaction in the new location, the existing
`enter_scene` flow generates gatherings as normal. `_perform_travel` and the
picker callback deliberately do NOT call `enter_location` / `generate_gatherings`.

**C1 — `_perform_travel` shared helper.** Callers: (1) creator `POST /api/travel`
(god-mode, any active location); (2) in-fiction direct resolved case in `_stream`;
(3) in-fiction picker callback `POST /api/conversations/{conv_id}/travel`.
The neighbour restriction is NOT in the helper — it is a property of the
in-fiction callers only. The creator tool keeps its god-mode reach.

**C-a — Inactive-destination guard in `_perform_travel`.** `dest.status != "active"`
is rejected alongside other destination validation failures. Tightens the creator
path (previously let inactive locations through) and defends the in-fiction path
by construction (neighbours are already filtered to active by `_location_neighbours`).
Isolated in Commit 2 so it can be reverted independently if needed.

**E1 — `restrained` reroutes `travel` to a physical escape attempt.** A travel
turn under the `restrained` constraint is intercepted before dispatch and
rerouted to `physical` (escape roll). Same interception as `scene` and
`npc_reaction`. `gagged` does NOT intercept travel — a gag does not prevent
walking.

**Travel is not a canon mutation.** `_perform_travel` writes `current_location_id`
(direct state transition bookkeeping, same category as join/migrate/enter_scene),
`conversation.status/ended_at`, and `gathering_member.left_at`. None of these are
world-table mutations; no `proposed_mutation` row is written.

### In-fiction picker callback

`POST /api/conversations/{conv_id}/travel` (body `{"location_id": str}`):
re-validates that the chosen `location_id` is an active `connects_to` neighbour
of the current location (stale-client guard); calls `_perform_travel`; returns
its result. No MJ narration — the `[DÉPART INCERTAIN]` turn already narrated the
fictional moment. Distinct from the creator `POST /api/travel`.

### Deferred

- **Arrival narration (step C)** — the destination scene reforms silently via
  `enter_scene` on the next interaction there. No "what you see entering" prose here.
- **Directed edges (B2)** — `connects_to` is treated as mutual-only;
  `_location_neighbours` does not read `relation.direction`.
- **Conflict → neighbours only gate** — restricting travel out of a conflict scene
  waits on `gathering.mode` from the combat chantier.
- **Multi-hop travel** — single direct neighbour only.
- **Edge distance / traversal time / per-edge descriptions.**
- **Graph-endpoint code dedup (D2 rejected)** — `GET /api/locations/graph` and
  `_location_neighbours` are not refactored to share code.

---

## ECONOMY — ledger (currency, schema v1.31, BRIEF-18)

### Conserved vs non-conserved: the core split

Two kinds of "value" exist in the world, and they get two different
mechanisms, never one:

- **Conserved currency** — moving from one pocket to another, with a real
  total. Gets the append-only `ledger` table: every line is an immutable
  fact, balance is `SUM(amount)` computed at read time.
- **Non-conserved influence** — trust, fear, fascination, debt-as-feeling.
  Stays in `relation` (a jauge, not a ledger): it can be created from
  nothing and destroyed into nothing: there is no total to conserve.

BRIEF-18 built only the foundation for the first kind: the table, the
single write chokepoint, the reads, and a creator-direct write path. AI
detection (`resource_change`) followed in BRIEF-19, below; pricing and
double-entry remain deferred (see "Deferred decisions").

### A1 — player-relevant single line, no PNJ double-entry

When the player buys something from an NPC, only the player's line is
written. `counterparty_id` is filled (so the registre reads "Maelis → -15,
counterparty: Aubergiste") but it triggers NO second `ledger` row for the
NPC. Tracked NPC purses (A2: an NPC gets its own balance) and full
double-entry bookkeeping (A3) are deferred — most NPCs are not economic
agents the player needs to audit; building their books now is premature.

### B1 — transactions are detected by `analyze_window`, not a separate path

`resource_change` (BRIEF-19) is a `proposed_mutation.mutation_type` detected
by the SAME analyzer that already proposes `relation_change` and
`new_knowledge` from a conversation window — not a parallel "economy
analyzer." One unified detection pass, one more mutation type it can emit.

### Base-unit integer storage, display-layer tiering

`amount` is always an integer in the world's smallest base unit. A world
that wants "1 or = 100 argent = 10000 bronze" expresses that as a display
formatting rule (and later, a per-world config), never as a storage
decision — `ledger.amount` never changes meaning based on which tier the
narration is currently using.

### Append-only: the deliberate divergence from the rest of `crud.py`

Every other in-context editor in `crud.py` (`relation`, `knowledge`) allows
creator update and hard-delete — the creator is the authority, free to
correct or remove. `ledger` does not: it is INSERT-only on every write
path, full stop. A pricing mistake or accidental credit is corrected with a
new compensating line (`source_type='correction'`), never an edit or a
delete. This is a structural choice, not an oversight — an executor reading
the surrounding `crud.py` conventions must not pattern-match the ledger to
its neighbors. `writes.write_ledger_entry` is the single INSERT chokepoint,
shared by the creator-direct path and `_apply_mutation`'s `resource_change`
branch (BRIEF-19), so the two canon-write paths cannot diverge into
different validation or shapes.

### The shadow-economy guard

`resource_change` (BRIEF-19) is reserved for conserved currency, plus an
optional `knowledge` leg when information is the thing being bought (the
double-table atomic write, also BRIEF-19). It must never become the vehicle
for "a service rendered against relation intensity" — a favor performed
because someone is liked or feared, with no currency changing hands. That
stays the implicit-favor path: a pure `relation_change`, no ledger touch,
ever. This mirrors the existing "social skills are never a skill domain"
guard in spirit: a deliberately-excluded mechanism must stay excluded by
construction, not by a model being asked nicely. Favors becoming *explicit*
(an NPC names a price in favor-currency, trackable like money) is a
separate, deferred design — see "Deferred decisions."

### Cockpit (creator-mode only, structural)

A read-only "Registre" sub-tab in Création (global journal, `GET
/api/ledger`, filterable by entity and by session) plus a read-only "Solde"
block on the character entity sheet (`GET /api/entities/{id}/ledger`). The
write control (crediting/debiting) lives on the Registre tab, calling `POST
/api/ledger` — the character sheet block is display-only. Both surfaces are
reachable only inside the Création shell, which is itself the creator's
tool (see "Creator control is structural" elsewhere in this doc) — the
player must never see a balance number or the journal; wealth is felt in
fiction, never read as a figure.

### resource_change — the transaction mutation (schema v1.32, BRIEF-19)

The 6th implemented `proposed_mutation.mutation_type`, owned by
`analyze_window` (decision B1, reaffirmed: window-detected only, no
overhearing/per-turn path — a purchase is a concluded scene event, not a
fact a bystander happens to overhear). Two-leg payload: a mandatory money
leg (`entity_id`, signed `amount`, `counterparty_id`, `reason`) and an
OPTIONAL `knowledge` leg, present only when the thing exchanged is
information, and always a fresh acquisition (`new_knowledge` semantics) —
never an upgrade this step.

**The double-table-in-one-SAVEPOINT exception.** `_apply_mutation` writes
both legs — `ledger` always, `knowledge` when present — inside the single
existing `db.begin_nested()` SAVEPOINT that already wraps every apply call.
This is the ONE documented exception to "one apply branch writes one canon
table": a partial "paid but didn't receive the info" (or the reverse) is
impossible by construction, because both writes commit or both roll back
together. The exception is justified entirely by atomicity, not convenience
— it must not normalise into a pattern for any other mutation type.

**Accumulating money, idempotent knowledge — and why the two dedup guards
treat the same mutation differently.** The money leg behaves exactly like
`relation_change`: two genuine purchases in one conversation both apply,
so `resource_change` is excluded from BOTH `_mutation_match_key`
(write-time dedup, propose time) and `_find_applied_duplicate` (apply
time). The knowledge leg, in contrast, IS idempotent — a fact, once
granted, must not be granted twice — but its guard does not live in either
of those generic mechanisms; it lives inside the `resource_change` branch
itself (`_knowledge_leg_already_applied`, guard 4c), as a block-WHOLE
check: if the knowledge leg cannot be created cleanly, the entire
mutation (money leg included) is routed to Needs attention and nothing is
written. An executor must never "fix" this by adding `resource_change` to
either generic guard — that would either block legitimate repeat purchases
(money) or apply a duplicate knowledge row before the block-whole check
runs (knowledge).

**A1 reaffirmed.** The money leg targets the player only; `counterparty_id`
is filled for the registre's legibility but never triggers a second
`ledger` row. Tracked NPC purses remain deferred.

**No price inference, reaffirmed.** The analyzer records the amount the
dialogue *stated* — `pt-conversation-analysis` v4's rubric explicitly
forbids inventing a price. Reading `entity.metadata.price_list` or having
the model propose a price is step 3, not this step.

**The shadow-economy guard, reaffirmed.** A service performed against
relation intensity, with no currency stated, must never become a
`resource_change` — it stays the implicit-favor path (`relation_change`,
no ledger touch). The rubric makes this explicit to the model; the guard
exists in the rubric, not in code, the same as before this step.

### Pricing — permanent catalogue vs unique quote (schema v1.33, BRIEF-20)

**The firm/improvised split.** `entity.metadata.price_list` (`{tag: int}`)
holds a seller's FIRM catalogue — identical for every buyer, never relation-
modulated. Anything not in the catalogue gets an AI-improvised quote: the
NPC names one price, anchored on the catalogue's order of magnitude and
modulated by its relation toward the buyer. The split is deliberate: a
firm catalogue is config a creator can audit at a glance; an improvised
quote is free dialogue, bounded only by the anchor and the relation cue
already surfaced in `assemble_npc_context`. No haggling round either way —
the NPC states one number.

**One injection, two uses.** The "TES TARIFS" block `assemble_npc_context`
writes into an NPC's own context block serves both roles at once: it is
the verbatim text the NPC quotes for catalogue items, AND the reference
scale the rubric tells it to stay within when improvising an uncatalogued
price. No second query, no separate "pricing context" — the existing
seller's-own-list injection already carries everything the rubric needs.

**Why dialogue, not a structured call.** Unlike the arbiter or the
interpretation phase, pricing has no `pt-pricing` classification step. A
quoted number is free dialogue precisely because the real control is
downstream: the money only moves canonically through a `resource_change`
at the checkpoint (BRIEF-19) when a sale actually concludes. Gating the
quote itself would duplicate a control that already exists at the point
that matters — free dialogue, controlled consequences, same doctrine as
the rest of the engine.

**Metadata-config treatment, not canon history.** `price_list` lives in
`entity.metadata`, same category as `physical_tier` and `coordinates`: a
creator-CRUD read-merge-write, no `change_history`. The actual sale audit
trail is the `ledger`, not the catalogue — editing a price going forward
does not need to preserve what it used to be, the same way moving a pin on
the location graph doesn't.

**The exclusion guarantee, reaffirmed.** `price_list` is read ONLY inside
`assemble_npc_context`, for the NPC being assembled, never for anyone else's
context and never inside `assemble_mj_context`. A player perceives a price
exclusively as something they're told in dialogue — never a sheet they can
see. Enforced by query construction (the assembler reads `npc_entity`'s own
`metadata_`, nothing else's), not by instruction.

---

## AI entity-authoring assistant (NPC, Location, Faction) (schema v1.36–v1.37, v1.43, BRIEF-24, BRIEF-25, BRIEF-32)

**A1: NPC/`character` only, parameterized for later types.** The generation
module (`entity_author.py`) has exactly one public function,
`generate_entity_draft(entity_type, brief, db)`. Its only populated
per-type config is `_TYPE_FIELDS["character"]`; the `pt-entity-generation`
template carries `{entity_type}`/`{type_fields}` variables so a future
`location`/`faction`/etc. is a new `_TYPE_FIELDS` key, not a template or
parser change. The two-block `public`/`secret` structure itself, not the
field list inside each block, is what the parser is built around — that
part of the contract is already type-agnostic.

**The two-block `public`/`secret` contract, enforced structurally.** The
model proposes a single JSON object with exactly `public` and `secret`
top-level keys. The parser ignores any key it doesn't recognise (the model
cannot invent a field that reaches canon) and — critically — `is_secret` on
every `secret.knowledge` row is forced `TRUE` in code; the model is never
given the opportunity to set it. This is the same doctrine as the rest of
the engine ("Secrets are structurally excluded", CLAUDE.md): concealment is
never trusted to an instruction, even one as explicit as "never merge
secret into public" (which the system prompt also states, belt-and-braces).

**C3 — full-canon visibility, and why it doesn't weaken exclusion.** The
generator may see hidden canon because it runs out of the play loop,
operated by the creator, with every draft reviewed before any write — there
is no player to leak a secret to. This is a property of WHO is looking at
the output (the creator, pre-write), not a relaxation of the play-time
security boundary. `secret.knowledge` rows the generator proposes land in
the exact same `knowledge` rows, with the exact same `is_secret = TRUE`
flag, that `assemble_npc_context`/`assemble_mj_context` already exclude by
query construction. Provenance (AI-authored vs. creator-typed) is invisible
to the assemblers — they exclude by `is_secret`, never by who wrote the row.

**D1 — draft pre-fills, author-CRUD writes; the generate endpoint is NOT a
canon-write path.** `generate_entity_draft` and `POST /api/entities/generate`
write zero canon — no `entity`, `character`, `knowledge`, `relation`, or
`proposed_mutation` row, ever, in this call path. The endpoint lives in
`cockpit/app.py`, deliberately outside `crud.py` (`crud.py` IS a sanctioned
canon-write path; keeping the generator in a separate router makes "this
writes nothing" legible at a glance, not just true). The ONLY write is the
creator's accept: the existing composite `POST /api/entities` then the
existing `POST /api/entities/{id}/knowledge`, run exactly as they would be
if the creator had typed every field by hand. This step adds no new write
function anywhere. The two sanctioned canon-write paths
(`_apply_mutation`, author-CRUD) remain exactly two; this step deliberately
does not become a third.

**Why this isn't routed through `proposed_mutation`.** That queue exists to
contain the LOCAL MODEL'S drift during PLAY — a creator-supervised,
out-of-loop authoring assistant has no analogous risk to contain: the
creator IS the checkpoint, reviewing every field before the existing
author-CRUD write. Routing a one-shot authoring draft through the Review
Queue would relocate creator judgment to the wrong place in the flow,
not add safety.

**Model extracts, code judges (the post-processing layer).**
`physical_tier` is clamped to −1..2 (default 0 on anything unparsable);
`knowledge[].level` is validated against the ladder and dropped to `rumor`
on anything unrecognised (never `unaware` — the NPC holds the row, by
definition); `faction_name` is resolved to a `faction` entity by
case-insensitive name match, same doctrine as other name→id resolution in
the codebase, with NO auto-creation on a miss (blank field + an
"introuvable" note for the creator instead). Any `knowledge` row missing a
`subject` or `content` is dropped and noted. None of this is the model's
job to get right — the model proposes text, code is the only place a value
is judged fit for canon.

**G1 — `shared_with` is display-only, never written.** Suspected sharing
the model infers (`secret.shared_with`) surfaces in the draft's `notes` for
the creator to act on manually — by hand, later, through the existing
relation/knowledge editors if they choose. No code path writes a
`shared_with` entry anywhere; it is pure text in the API response.

**Named deferrals (do not build silently):**
- **G2 — cross-entity writes.** The generator authors only the NPC's OWN
  canon. It must never propose or write a `knowledge` row on another
  entity; that's what `shared_with` notes are for instead.
- **F2 — conversational refinement.** No "make her older / hostile to the
  Guild" follow-up. One-shot only: a second "Générer" click discards the
  current draft (`pendingDraftKnowledge`/`pendingDraftNotes` in the cockpit
  UI) and starts over.
- **Generator-proposed `relation` rows.** The model proposes only the
  single primary `faction_id` link (by name resolution); it never proposes
  a `relation` row or an intensity — that calibration stays a manual
  creator act, same as everywhere else in the engine.
- **Auto-creating a referenced faction/location.** Unresolved name → blank
  field + note. Never create the entity the brief merely names.

**Location (BRIEF-25, schema v1.37) — confirming the seam is config, not
code.** Adding `location` meant exactly one new `_TYPE_FIELDS` key plus a
new branch in `generate_entity_draft` that builds a different draft shape;
the two-block `public`/`secret` contract, the template, the generate
endpoint, and the accept path were all reused completely unchanged — the
A1 prediction held.

**B1 — `subculture`'s intra-JSON public/secret segregation, the headline of
this step.** Every prior `public`/`secret` split in this engine has been a
split between top-level blocks (NPC `public`/`secret`,
`character.secrets`/`knowledge.is_secret`). `location.subculture` is the
first field where BOTH regions live inside the SAME JSON value once
written — a public region and a `"hidden"` trap key. The parser makes this
safe structurally, not by instruction:
- `_filter_subculture_public` reads the LIVE `_SAFE_SUBCULTURE_KEYS`
  constant (imported from `context.py`, never a hardcoded copy) and drops
  any key the model proposes under `public.subculture` that isn't on it —
  noted, never written. `"hidden"` is not on that allow-list, so the model
  cannot place it in the public region even if it tries.
- The ONLY path to `subculture["hidden"]` is the model's
  `secret.subculture_hidden` field, which the cockpit JS merges into the
  textarea pre-fill (`authorApplyLocationDraft`) from two already-segregated
  draft fields (`draft.public.subculture`, `draft.secret.subculture_hidden`)
  — the merge is code reading two trusted buckets, never the model writing
  one mixed key directly.
- This means `_SAFE_SUBCULTURE_KEYS` doubles as the SAME allow-list
  `assemble_npc_context`/`assemble_mj_context`/`active_signposts` already
  use to decide what's safe ambient atmosphere (CLAUDE.md's "subculture is a
  TRAP" note) — the generator cannot produce a public subculture the
  play-time assemblers wouldn't already have surfaced anyway, and it cannot
  produce a `hidden` value the assemblers will ever read, because no
  assembler reads it regardless of provenance.

**`access_level` never defaulted permissive — stronger than the NPC step's
defaults.** Unlike `location_type` (unrecognised → `"other"`, a neutral
fallback), an unrecognised or missing `access_level` is left BLANK for the
creator. `"public"` is not a safe default to guess on the model's behalf —
whether a place is open, restricted, or secret is a creator decision about
the world's structure, not a detail to infer from a one-line brief.

**`magic_status` never generator-proposed (C2), same doctrine as
`physical_tier` is NOT — and that asymmetry is intentional.** `physical_tier`
(NPC) is model-proposed then code-clamped, because a combat capability
guess is low-stakes and reviewable. `magic_status` going to `nexus`/`active`
is a world-structuring reveal the creator places deliberately; the
generator doesn't propose it at all, not even into a field the creator
must then notice and override. The schema default (`inert`) stands
untouched; the creator sets it by hand during pre-fill review, same as
the existing Lieux CRUD editor outside generation entirely.

**D1, restated for Location — hierarchy/adjacency/discoverables stay
out.** The generator never resolves `parent_location_id`, never proposes a
`connects_to` edge, never creates a `discoverable_detail`/signpost row.
Any sensed parent, neighbour, or controlling faction the model infers from
the brief becomes a `sensed_links` entry in the draft's `secret` block,
surfaced as a display-only note (`authorApplyLocationDraft` pushes each
into the notes panel) — identical doctrine to the NPC step's
`shared_with`. These are separate, already-existing subsystems (travel,
passive perception) with their own creator-direct CRUD; generation must
not shortcut them.

**No `knowledge` rows for locations.** A location doesn't "know" anything —
its concealed lore lives entirely in `subculture["hidden"]`, a column on
the `location` row itself, not a `knowledge` table entry. This step
generates zero `knowledge` rows for `location` entities, unlike the NPC
step's `secret.knowledge` list.

**Faction (BRIEF-32, schema v1.43) — third confirmation of the seam.**
`faction` is the third `_TYPE_FIELDS` entry, again zero changes to the
two-block contract, the template, or the accept path. Field partition:
`name`, `description`, `faction_type` (validated against the enum, falls
back to `other`), `philosophy`, `internal_structure` are public/proposed;
`roles` (`[{name,description}]`, ordered by rank) is public/proposed,
landing in `entity.metadata['roles']` — the same flat ordered list the
BRIEF-31 roles editor already reads/writes, so generation and the
structured roles UI share one in-memory array
(`authorFactionRolesDraft`) with no new store. A nameless proposed role is
dropped with a note, deliberately closing the gap `authorSave`'s
`cleanRoles` filter leaves silent today (a creator hand-typing a nameless
row gets no warning; a generated one does).

**No secret store for factions — simpler than the NPC generator.**
`internal_tensions` and `goals` route straight to typed `faction` columns
no assembler reads (CLAUDE.md's "Secrets are structural, not
instructional" — confirmed by grep before closing this step). There is no
per-row secret table analogous to `knowledge`, so unlike the NPC step
there is nothing to hold client-side until accept: the secret block is
just two passthrough strings into the existing form fields.

**`parent_faction_id` deliberately never model-emitted.** Same
structural-link invariant as `parent_location_id` for the location
generator: absent from `_TYPE_FIELDS`, never read out of the parsed dict,
never coerced from a proposed name. The multi-level faction pyramid (the
"mondial → local" hierarchy) is left neutral here — neither wired nor
forbidden in schema — and deferred to its own future brief that will
follow the "model proposes names → code creates entities and wires the
links" pattern, never "model emits a parent id."

**`magic_knowledge_level` and `scope` never proposed — both stay
default,** same doctrine as `magic_status` for locations: these are
creator-structuring decisions, not details to infer from a one-line
brief.

**This step creates the faction entity only — no roster.** The roles list
is vocabulary (rank names + functions), not a membership roster. No NPC
creation, no `faction_membership` row, no role *assignment* happens here;
that remains entirely the existing membership CRUD (BRIEF-29/30/31).

---

## FACTION — structure & resources (BRIEF-26, schema v1.38)

**Scope: creator-CRUD, zero active mechanic.** Factions gain a containment
hierarchy mirroring `location`, a descriptive scale label, a treasury
reusing the existing `ledger`, and a generic `controls` relation for owned
assets. Membership (roster, ranks, secret affiliation) is the NEXT,
separate chantier (C1) and is explicitly out of scope here —
`character.faction_id` stays the single primary pointer this step.

**A1a — `parent_faction_id` dormant, same posture as `equipped`.** Three
new nullable `faction` columns (`parent_faction_id`, `scope`, `goals`) plus
`idx_faction_parent`, no `CHECK`. All three are placed-but-unread: no
assembler, guard, or code path reads them. The traversal index exists for
a deferred consumer (the C1 membership/authority follow-up), not for
anything live today. The risk this guards against is an executor wiring a
reader "while it's here" — explicitly forbidden.

**`scope` is descriptive, not depth-derived.** `global | national |
regional | local | other` is a creator-set label on the faction sheet. It
is never computed from walking the `parent_faction_id` tree, and no
mechanic (access gating by reach, etc.) reads it.

**`controls` — the `connects_to` isolation pattern, directed instead of
undirected.** Reuses the `relation` table exactly like `connects_to`:
`direction='a_to_b'` (controller is `entity_a`, asset is `entity_b`),
`intensity=50` is a MEANINGLESS structural default that must never be read
as an affective or relational signal. Every gameplay consumer of
`relation` (the initiative vote, both context assemblers) is keyed on a
character/player id, so a `controls` row is structurally invisible to all
of them. The guard comment in `RELATION_TYPES` (`crud.py`) is verbatim
with the brief and mirrors the `connects_to` guard; any future world-wide
relation scan must explicitly exclude both types. "Who controls asset X"
is read as the `entity_a` of `controls` rows whose `entity_b = X`; several
rows means shared/contested control, with no special handling.

**Faction treasury reuses `ledger`, reaffirming A1/A2/A3 — no new table,
no new route.** `ledger.entity_id` already accepts any entity id, so a
faction balance is `SUM(amount) WHERE entity_id = <faction_id>`, computed
at read time exactly like a character's. The only changes are cockpit
surfacing: the existing read-only "Solde" block (`GET
/api/entities/{id}/ledger`) now also renders on the faction sheet, and the
Registre's credit/debit form (`POST /api/ledger`) already targets any
active entity — no change was needed there, it was generic from BRIEF-18.
A1 (`resource_change`'s money leg stays player-only through the AI
pipeline) and A2/A3 (tracked NPC/faction purses, double-entry) are
reaffirmed as deferred: this step adds no faction-targeting path through
`_apply_mutation`, only the creator-direct `write_ledger_entry` chokepoint
that already existed.

**`goals` is prose with no mechanic.** Free text on what the faction is
trying to do. No event generation, no agenda-driven NPC behavior reads it
— a structured "agenda" subsystem is a hypothetical future step, not
implied by storing this field.

**Cycle prevention deferred — excluding self from the dropdown is the only
guard.** The cockpit's parent-faction picker filters out the faction
currently being edited (`entity_ref` field gains an `exclude_self` flag,
read against the in-memory `authorEntityId`). This is a UI nicety, not a
backend invariant: the API itself does not reject a self-referencing or
cyclic `parent_faction_id`, because nothing traverses the tree yet, so a
cycle is inert. Full cycle detection is deferred — revisit only once a
consumer actually walks `parent_faction_id`.

**Hierarchical authority propagation is explicitly NOT implemented.**
Being `leader` of a parent faction confers no computed authority over
child factions. The tree stores facts only; this is a tripwire for the
next step (C1 membership), not a decision this step makes.

**Next: C1 — faction membership.** A `faction_membership` roster (`role`,
`is_secret` affiliation, `joined_at`/`left_at`) is the natural next chantier
once this structural layer exists, and is the first place a reader of
`parent_faction_id` would plausibly appear (e.g. inherited relations from a
member's faction — also explicitly deferred, C2).

---

## FACTION MEMBERSHIP — C1 (BRIEF-27, schema v1.39)

**Scope: storage + creator-CRUD + cockpit roster only — no assembler reads
membership.** A character's faction tie moves from a single
`character.faction_id` pointer to a durable `faction_membership` roster:
one row per member<->faction tie, supporting multiplicity, rank labels, and
secret affiliation. The first reader (membership injected into context) and
the structural secret-exclusion it requires are the next, separate brief.

**A1 — single-source rationale, durable not ephemeral.** `faction_membership`
mirrors `gathering_member`'s roster shape (active iff `left_at IS NULL`,
never deleted or edited in place) but drops `session_id`: a faction tie
outlives any single session, unlike gathering co-presence. This is the
distinguishing fact between the two tables — same predicate, different
lifetime.

**B1 — `is_primary` + partial-unique enforcement, structural over
instructional.** Two invariants are enforced by partial unique indexes, not
by remembered discipline: `idx_membership_one_primary` (at most one ACTIVE
primary per member) and `idx_membership_unique_active` (no duplicate ACTIVE
membership of the same member in the same faction). Both are
`WHERE ... AND left_at IS NULL` partial indexes — a closed membership never
counts against either guard, so re-joining a faction or re-establishing a
primary after a close is always legal. Violating either surfaces as an
`IntegrityError` → HTTP 409 at the cockpit route; the executor must never
catch it and silently demote the existing primary.

**Close + reopen, no `change_history` column — append/close only, by
construction.** `writes.write_membership(mode="open"/"close")` is
INSERT-only / close-only: it can never update `role`, `is_secret`,
`faction_id`, or `is_primary` of an existing row. A rank promotion or a
primary-status change is `mode="close"` on the old row followed by a fresh
`mode="open"` call — the resulting sequence of closed rows IS the history,
which is why this table carries no `change_history` column (unlike
`relation`/`knowledge`). This is a deliberate, narrower instance of "history
is sacred" than the rest of the schema: instead of snapshotting prior state
inside one row, the row itself becomes the snapshot once closed.

**`role` and `is_secret` seeded DORMANT — same posture as
`discoverable_detail.discovery_threshold` before BRIEF-23, or `equipped`
before its consumer existed.** Both are stored and creator-editable via the
cockpit Appartenances sub-block, but read by no assembler. The temptation
this guards against is wiring a reader "while it's here" during this step —
explicitly out of scope. When the first reader is added, it MUST filter
`is_secret = FALSE` for every non-creator context by query construction
(never by instruction) — that filter is the next brief's central job, not
this one's.

**Creator-CRUD only — no `membership_change` mutation type.** Membership is
written exclusively through `writes.write_membership`, reached only via the
cockpit's `POST /api/entities/{id}/memberships` (open) and
`POST /api/memberships/{id}/close` (close). No `_apply_mutation` branch
exists for this table this step, and none should be added without a
deliberate, separate decision — AI-proposed membership change is Scope OUT.

**Backfill is exact-mirror, not best-effort.** Every `character` row with a
non-NULL `faction_id` gets exactly one membership row
(`is_primary=TRUE`, `is_secret=FALSE`, `role=NULL`, `joined_at` = the
character entity's `created_at`). The migration
(`scripts/migrate_v1_39_faction_membership.py`) is idempotent: it checks
for an existing active `(entity_id, faction_id)` row before inserting, on
top of the partial-unique-index backstop.

**The grep-gated `character.faction_id` retirement — DROPPED (BRIEF-28,
schema v1.40).** BRIEF-27 Scope IN #6 found four consumers beyond the
cockpit editor and `idx_character_faction`, so the column stayed at v1.39,
report-only. A fresh RECON for BRIEF-28 re-confirmed the same four sites
with no drift and no sixth consumer, so the column is now retired for
real:
- `app.py`'s `list_npcs` no longer reads `char.faction_id`; it queries
  `faction_membership` for the active (`left_at IS NULL`) `is_primary=TRUE`
  row and resolves the faction name from there. At most one such row is
  guaranteed by `idx_membership_one_primary` — no `ORDER BY`/`LIMIT` crutch.
- The composite create (`crud.py`'s `POST /api/entities`) no longer writes
  `faction_id` into the `character` row — the field was removed from
  `ENTITY_TYPE_REGISTRY` entirely (the Appartenances sub-block is the only
  display now). If the incoming character payload carries a non-null
  `faction_id`, the route opens a primary membership via
  `writes.write_membership(mode="open", ..., is_primary=True,
  is_secret=False)` AFTER the entity row commits (the membership write
  needs the new entity's id — same post-accept-flush shape as BRIEF-24's
  `pendingDraftKnowledge`). This is **creator authority**: the create/accept
  is a creator action, not an AI proposal, so it does NOT go through
  `proposed_mutation`.
- `entity_author.py`'s `_resolve_faction_id` and its `index.html` pre-fill
  mirror (`author-x-faction_id`) are explicitly UNCHANGED — they still
  produce/display a transient `draft.public.faction_id`; the recabled
  create-path (above) is what now consumes that field correctly. The DOM
  element it used to mirror into no longer exists in the registry-driven
  form, so the mirror line is a harmless no-op (guarded by `if (factionEl)`)
  — not worth touching for a frozen internal.
- `scripts/seed_pilot.py`'s five `faction_id=` kwargs are replaced by a
  post-create `ensure_primary_membership(session, world_id, entity_id,
  faction_id)` call per NPC — idempotent (checks for an existing active
  `(entity_id, faction_id)` row before calling `write_membership`), so
  re-seeding an already-migrated DB inserts no duplicate rows.

Migration `scripts/migrate_v1_40_drop_character_faction_id.py` drops
`idx_character_faction` (SQLite refuses `ALTER TABLE ... DROP COLUMN` while
an index still references the column) then `character.faction_id` itself.
Pre-check: count of historical non-NULL `character.faction_id` values must
equal the count of matching `is_primary=TRUE` `faction_membership` rows —
if they don't match, the migration aborts and drops nothing (no
re-backfill attempt; that's `migrate_v1_39_faction_membership.py`'s job).
Commit boundary: the four recabled sites landed in one commit; the drop
migration in a second commit, so the recabling could be live-verified
before the column was removed.

**Hierarchical authority propagation remains explicitly NOT implemented.**
Being `role`d in a parent faction's membership confers no computed
authority over a child faction's membership — `role` is a flat label, same
posture as BRIEF-26's tree-depth non-derivation for `scope`.

**Next: the membership reader + structural secret-exclusion (C1, separate
brief).** No assembler (`assemble_npc_context`, `assemble_mj_context`)
reads `faction_membership`, `role`, or `is_secret` this step. Adding that
reader, the prompt-rubric changes it implies, and the mandatory
`is_secret = FALSE` filter for every non-creator context are the next,
separate brief — not bundled here.

---

## FACTION MEMBERSHIP — Reader A1: TES AFFILIATIONS (BRIEF-29, no schema change)

**`read_public_memberships` is the single structural choke-point for
membership-in-prompts.** Co-located in `context.py` (one consumer; not
promoted to a `reads.py` module). Its query filters
`is_secret = FALSE` BY CONSTRUCTION — the word "public" in the name encodes
the guarantee, and there is no parameter to opt into secret rows. Every
future membership-into-prompt read (third-party perception, MJ context,
anything) MUST go through this function rather than querying
`faction_membership` directly or reusing the cockpit's `_membership_dict`
(which exposes `is_secret` to the creator by design).

**Corrected-B: no secret self-include, even in the holder's own prompt.**
The original idea — let an NPC's own secret affiliation into its own
context, trusting the model to keep it concealed — was dropped. On an
abliterated model (no refusal mechanism), putting a secret label in the
prompt is handing the model something to confess under pressure. The
holder's own secret membership stays out of its own prompt exactly like
every other secret in this engine ("Secrets are structurally excluded",
CLAUDE.md). Espionage behaviour rides on `goals` prose, never on a
confessable affiliation label — there is no narrower, "just for self"
include-secret path anywhere in this step.

**TES AFFILIATIONS — the first `faction_membership` reader, mirroring TES
TARIFS' house style exactly.** `assemble_npc_context` builds the block
inline (no new section helper), placed immediately before the TES TARIFS
block (BRIEF-20) — affiliations are identity, injected before commerce. Same
empty-case idiom: zero public memberships → `""`, header omitted entirely,
no signpost of absence. A dangling `faction_id` (entity doesn't resolve) is
silently skipped — never a raw id rendered into a prompt. `is_primary`/
ordering is read for static rendering only (primary first, then
oldest-joined by `joined_at`); no `[principale]` tag, no role-based
behaviour, no authority propagation — same dormant posture BRIEF-27 set for
`role`/`is_primary` beyond this.

**Read-only step — no schema change.** This brief touches no canon-write
path and bumps no schema version; `faction_membership` (v1.39) and its
columns are unchanged. The changelog note for this step should say so
explicitly, the same way a read-only step's "Schema: none" gets called out
elsewhere in this doc.

---

## FACTION MEMBERSHIP — cas 3, the cover_role mechanism (BRIEF-30, schema v1.41)

**The double agent.** A character can be a PUBLICLY-known member of a
faction (`is_secret = FALSE`) while presenting a false role: the true
`role` ("espion") is creator-only and must never reach a prompt; a
`cover_role` ("membre") is the façade every prompt reader sees. The actual
espionage behaviour rides on the character's `goals` prose (positive
framing, no confessable label) — that is creator authoring, not code.

**One resolution rule, baked into the single accessor.** Everywhere a role
reaches a model prompt — the holder's own context (A1, BRIEF-29) and every
future third-party reader — the promptable role is `cover_role if
cover_role is not None else role`. This is resolved INSIDE
`read_public_memberships` (`context.py`), not by callers: the function now
enforces TWO structural guarantees, `is_secret = FALSE` AND
`cover_role ?? role`. The true `role` never crosses the accessor boundary
when a cover is set — same trust level as a secret.

**Backward-compatible by construction.** `cover_role` defaults NULL;
`NULL ?? role = role`, so every pre-existing membership (and the committed
A1 render block, untouched) behaves identically. No backfill needed or
attempted.

**INSERT-only, set at open time.** `write_membership` gained a
`cover_role` parameter persisted only on `mode="open"`. Like `role`,
changing a cover on an existing membership is close + reopen — no
in-place update, consistent with the table's append-only history
discipline (BRIEF-27).

**Creator sees both faces.** The cockpit roster (`_membership_dict`,
membership open form, "Appartenances" / faction-roster renders) shows the
true `role` AND the `cover_role` side by side (`role — cover ` rendered as
`role <em>(façade : cover)</em>`) — full creator visibility, mirroring how
`is_secret` rows are shown to the creator today. Nothing about this is
read by any prompt path; the cockpit's `_membership_dict` is a creator
surface, not the prompt-facing accessor.

**Scope held at the line.** This step does NOT add the third-party
perception block (interlocutor/co-present affiliations) — that is the
next brief. It only makes the cover mechanism exist and makes the
holder's own context cover-aware for free (the accessor change propagates
to A1 without touching A1's render block).

---

## FACTION ROLES — curated vocabulary, picker groundwork (BRIEF-31, schema v1.42)

**Vocabulary, not a referential store.** A faction now carries a curated,
ordered list of roles (`entity.metadata['roles']`, `{name, description}`,
array order = rank) for the creator to author and the NPC membership form
to pick from. `faction_membership.role` stays exactly what it always was —
a free-text snapshot label, no FK, no enum. Picking a listed role just
fills that free-text field with a known-good string; the membership write
path (`writes.write_membership`) is untouched. This is deliberate
consistency with the append/close membership philosophy (BRIEF-27): the
row that captures "who held what role, when" is already creator-CRUD and
history-preserving by construction (close + reopen), so a roles *store*
referencing it would be a second source of truth for no gain.

**"autre" is one-shot.** Typing a free-text role through the "autre"
escape hatch writes only to that one `membership.role`; `faction.roles` is
never mutated in response. Promoting ad-hoc labels into the curated list
is a deliberate non-feature — the vocabulary is creator-curated, not
crowd-sourced from play.

**Flat-ordered, tree left open.** `{name, description}` carries no
`parent` key. A role hierarchy / member-to-member command chain is a
free additive extension for later, not designed in now — adding `parent`
later costs one optional key, no migration.

---

## AVERSION — prose dual of philosophy, character live + faction dormant (BRIEF-33, schema v1.44)

**Prose, not structured.** `aversion` is a free-text `TEXT` column on both
`character` and `faction`, mirroring `philosophy`/`backstory`: what an
entity rejects or fears as a concept or category (technology, sunlight,
magic, outsiders) — never a named entity. A named target belongs to the
relation graph, not this field; the generator's field guidance carries an
explicit "PAS une entité nommée" clause on both sides to keep the author
model from coercing a rival faction or person into prose. No
`[{thing,intensity}]` list, no mechanical effect, no `change_history` —
creator-CRUD prose config, written in place, like its `philosophy`/
`backstory` siblings.

**Deliberate asymmetry: character live, faction dormant.** `character.aversion`
is read into the NPC dialogue prompt's `H_IDENTITY` block
(`assemble_npc_context`), raw prose appended after `backstory` and before
`description` — identical shape to its neighbours. `faction.aversion` is
authored in CRUD and proposed by the generator exactly like the character
side, but read by **no** assembler. The value is public-tagged (injectable
in principle) yet stays dormant: authoring symmetry across both entity
types is the justification for building it now, while the faction-side
*reader* is a prompt-architecture decision in its own right, deferred to a
future brief.

**The future faction-posture reader's only sanctioned path.** When that
reader is built, it MUST route through `read_public_memberships` — the
same accessor boundary that already keeps secret affiliations and a
double agent's true `role` out of every prompt (BRIEF-29/BRIEF-30). It
must NOT, as a side effect, resurrect `philosophy`, `description`, or
`internal_structure` into prompts: those have never been read into any
assembler, and `aversion`'s dormancy precedent must not become an excuse
to open a second injection path around the membership choke-point.

---

## REGION GENERATION — orchestrator (chantier 1) (BRIEF-34, schema v1.45)

**Composes the atomic generators; never modifies them.** The orchestrator
(`region_author.generate_region_draft`) calls
`entity_author.generate_entity_draft("faction"|"location"|"character", ...)`
exactly as it exists today — no new parameter, no new entity-type field, no
change to `_TYPE_FIELDS`. **H1 is retired by K1**: an earlier design
considered exposing `faction_name` directly on the character draft for the
orchestrator's benefit; K1 makes that unnecessary because affiliation is
carried entirely by the Stage-0 manifest (`npc.faction_name`), resolved by
the orchestrator to a draft-local faction id, never read back out of the
NPC's own drafted `public.faction_id` (which resolves to `None` during
region generation since the region's own factions aren't in the DB yet —
expected and ignored).

**A3 — auto-wire the structural skeleton only; everything else is a
suggestion.** The manifest's by-name relationships (`location.parent_name`,
`npc.location_name`, `npc.faction_name`) are resolved into draft-local
pointers in code — this is the only "wiring" this step does, and it never
touches canon. The atomic generators' own display-only link channels
(`sensed_links`, `shared_with`) are harvested as-is, unresolved, exactly as
`entity_author.py` already produces them — confirm-by-creator suggestions
for chantier 2, never auto-resolved here (D1, see below).

**B1 — generation order: Concept -> Factions -> Locations -> NPCs.**
Factions and locations carry no manifest-time dependency on each other in
v1 (factions are flat, I1), so either could run first; locations run after
factions and before NPCs because an NPC's composite brief wants both its
location's and its faction's one-liner already known, and a location's
brief benefits from knowing the region's factions exist (even though I1
means a location draft never names a controlling faction structurally).
Locations are generated root first, then the rest in manifest order — purely
so a child's composite brief can mention its parent's one-liner.

**C1/F1 — bounded forward context, sequential calls, peers via one-liners
only.** Each `generate_entity_draft` call in Stages 1-3 receives a composite
brief built from `concept` + the **manifest's own one-liners** of relevant
peers (other factions; all locations with their parent relationships; the
NPC's own location/faction one-liners + co-located NPC one-liners) — never
from the drafted `public`/`secret` prose of already-generated entities. This
keeps context bounded (one-liners are short and fixed in number, unlike
accumulating full drafts) and is the structural enforcement of "secrets
never spray across prompts": a drafted entity's `secret` block is *never*
read by `region_author.py`, only the manifest's own public one-liners
transit between stages.

**K1 — the manifest is both the density control and the peer-summary
source.** No numeric knob exists anywhere in code; the model's manifest
response to the creator's brief is the only determinant of how many
factions/locations/NPCs get generated. The same manifest object that
encodes "how much" also encodes the one-liners Stage 2b composes into every
downstream composite brief — one structure serves both jobs, which is why
H1 (a dedicated `faction_name` parameter on the character generator) became
redundant once K1 was adopted.

**I1 — factions stay flat in v1.** No `parent_faction_id`, no `controls`,
no faction-side link-suggestion channel (RECON finding #1: the faction
generator has no `sensed_links`/`shared_with` analogue) is added. Inter-
faction tension in a generated region stays prose, inside each faction's own
`secret.internal_tensions` — never a structural edge.

**J1 — stage-sensitive failure.** A failed or empty Stage-0 manifest aborts
the entire run (`generate_region_draft` returns `{"ok": false, "error":
...}`, no downstream stage runs) — a manifest is the plan every later stage
depends on, so a missing plan cannot degrade gracefully. A failed
Stage 1-3 `generate_entity_draft` call (which never raises, per its own
contract) drops only that one entity, recorded in `region.skipped`, and the
run continues — downstream references to a dropped entity degrade
gracefully (an NPC whose location was dropped is itself dropped + skipped;
an NPC whose faction was dropped gets `faction_local_id = null` + a note).

**The region draft is ephemeral; draft-local ids are not canon ids.**
`generate_region_draft` writes no canon — no `Entity`, no `Character`, no
`Location`, no `Faction`, no `FactionMembership`, no `Relation` row, ever.
Its `fac-N`/`loc-N`/`npc-N` draft-local ids exist only as pointers *within
the one returned tree*; they are never looked up against real entities and
never persisted anywhere (no staging table, no draft store — the draft is
held client-side by the caller, mirroring the single-entity author flow).
Turning a draft-local id into a real entity id — `parent_location_id`,
`faction_membership`, `connects_to`/`controls` — is canon wiring, deferred
in full to chantier 3 at commit time; the review/accept surface itself is
chantier 2 (E1). Neither is built in this step.

---

## COMMIT-BOUNDARY SEAM — pre-step for atomic region commit (BRIEF-35, no schema change)

**E1 — atomic region commit needs a caller-owned transaction boundary.**
Chantier 2 (region review + commit) must batch-commit a whole region as one
unit: a failure on entity K rolls back entities 1..K-1, leaving canon intact.
RECON (`RECON-region-commit.md`, item 1) found this impossible as written:
`create_entity`, `create_knowledge`, and `open_entity_membership` each
hard-coded their own `db.commit()`, so a batch sharing one session still
committed irreversibly mid-loop, even though the shared `writes.py` helpers
(`write_relation`, `write_knowledge`, `write_membership`) already never
commit.

**The seam: commit-free core + thin route wrapper, not a `commit:` flag.**
Each of the three creator-direct create helpers now exposes a commit-free
core (`_create_entity_core`, `_create_knowledge_core`,
`_open_membership_core` — does the write logic up to `db.add`/`db.flush()`,
never `db.commit()`/`db.refresh()`, returns the ORM row) plus a route wrapper
that owns the single commit/refresh and shapes the response exactly as
before. Chosen over a `commit: bool` parameter threaded through all three
call sites — structural over disciplinary (every caller would have to
remember to pass the flag correctly; the structural seam makes the
commit-free contract the only option for a batch caller). A future chantier-2
batch caller calls the three cores directly against one shared session, in
dependency order (factions → locations → NPCs, matching
`region_author.generate_region_draft`'s own order), and commits or rolls back
once for the whole region. This step builds no such loop — only the cores
and the wrappers that preserve today's single-entity behaviour.

**Side effect: closes the pre-existing single-entity two-commit atomicity
gap.** `create_entity`'s character-with-`faction_id` path collapsed from two
`db.commit()` calls (entity+extension, then the membership leg) to one — the
gap RECON flagged, where a process crash between the two old commits could
leave a character with no primary faction membership despite the form having
submitted one, no longer exists for this path.

**No behavioural change for any existing caller.** Single-entity creator-CRUD
("Ajouter un PNJ/lieu/faction") still commits once per click, returns the
same JSON shape, and still 409s on a membership conflict
(`open_entity_membership`'s wrapper keeps the `try: ... except
IntegrityError: db.rollback(); raise HTTPException(409, ...)` guard, now
wrapping the core call + commit instead of just the commit). `writes.py`
stays untouched and commit-free.

---

## REGION REVIEW + ATOMIC COMMIT — chantier 2 (BRIEF-36, no schema change)

**D1 — the review tree is a spatial spine, not a flat list.** The cockpit's
Création surface gains a "Région" sub-tab: a brief textarea ->
`POST /api/regions/generate` -> the returned `region` envelope held in
client state only (`regionDraft`/`regionAccepted`, mirroring the single-
entity `pendingDraft*` pattern at tree scale — never server-persisted).
Locations nest by `parent_local_id` with the root (`parent_local_id == null`)
at top; NPCs nest under their host location (`location_local_id`) with a
colour-coded faction badge; factions get a separate non-spatial panel with a
live member count. Judgment-tier suggestions (`sensed_links`, `shared_with`,
plus each entity's own generation notes) render read-only, inline per node —
same content shape `authorApplyLocationDraft`/`authorApplyCharacterDraft`
already build for the single-entity flow, never applied.

**B1 — soft cascade, advisory only.** Every faction/location/NPC node has an
accept/reject toggle, default accept. The client renders the same cascade
rules the manifest parser already encodes (faction rejection greys an NPC's
badge but still commits it unaffiliated; host-location rejection auto-
rejects its NPCs; parent-location rejection re-parents children to root,
walking arbitrarily many levels) **purely for UX** — `regionCascade()` in
`index.html` is a pure, side-effect-free re-derivation from `regionAccepted`,
never sent to the server as a precomputed result.

**E1 — the commit is atomic and server-authoritative; this is the chantier's
load-bearing invariant.** New route `POST /api/regions/commit`
(`commit_region` in `cockpit/app.py`, deliberately outside `crud.py` like
`/api/regions/generate` but — unlike that route — this one DOES write canon)
takes the re-sent region draft tree plus a raw per-`local_id` accept/reject
map and treats both as **untrusted input**: it re-derives the entire cascade
itself (`_region_resolve_location_parent` walks the rejection chain to the
root; an NPC is placeable only if both its own flag and its host location's
derived acceptance hold; a faction leg is wired only if the faction survived
the cascade) rather than trusting anything the client rendered. The commit
walks factions -> locations (dependency order via a small topological pass,
not raw draft order, so a multi-level reparent-to-root resolves correctly in
one pass) -> placeable NPCs + their knowledge, calling the BRIEF-35
commit-free cores (`_crud._create_entity_core`, `_crud._create_knowledge_core`)
directly against one shared session, building draft-local -> real-id maps as
it goes. Exactly **one `db.commit()`** fires at the end; any exception
(`HTTPException`, `IntegrityError`, or anything else) triggers `db.rollback()`
and a `{"ok": false, "error": ...}` response — verified live: a forced
validation failure on the second entity left the first entity's already-
flushed row rolled back too, zero rows in canon. The single-entity creator-
CRUD path and the route wrappers (`create_entity`, `create_knowledge`,
`open_entity_membership`) are never called from this loop — only their
commit-free cores.

**A1 — only the structural skeleton is wired here.** `parent_location_id`
(re-parented per the server cascade), the primary **public**
`faction_membership` (riding `extension.faction_id` into
`_create_entity_core`'s existing `pending_faction_id` leg — no new
membership-writing code), and `current_location_id` are the only canon
edges this chantier writes. `sensed_links`/`shared_with` are read only to
render suggestion notes, never resolved into a `connects_to`/`controls`/
secret-membership row — that wiring is chantier 3's scope. No
`is_secret=True` membership is ever written by this route.

**Draft -> commit field mapping.** Public + secret entity fields go straight
into the create payload (faction: `name/description/faction_type/
philosophy/internal_structure/aversion` + secret `internal_tensions/goals`,
with `roles` cleaned exactly as `authorSave`'s structured roles editor does;
location: `name/description/location_type/access_level` + `subculture`
merged with `secret.subculture_hidden` exactly as `authorApplyLocationDraft`
merges it; NPC: `name/description/appearance/backstory/aversion` +
`metadata.physical_tier` + secret `creator_meta` (JSON-encoded into the
`secrets` column the same way the single-entity form does) + one
`_create_knowledge_core` call per `secret.knowledge` item, `is_secret=True`
forced as it already is at generation time). The two note channels
(`sensed_links`, `shared_with`) go nowhere — display-only, by construction.

---

## JUDGMENT-LINK WIRING — chantier 3, closes the region loop (BRIEF-37, no schema change)

**P1 — extends chantier 2's single transaction, not a separate pass.** The
confirmed-link suggestions live only on the client-held draft; they die with
it at commit. So chantier 3 adds **phase 4** to `commit_region` — after
factions/locations/NPCs (stages 1-3) have flushed and the local->real id map
is complete, before the single `db.commit()` — rather than a second pass that
would need its own persistence for the suggestions. `write_relation` is
already commit-free (BRIEF-35/RECON item 7), so it drops in with zero new
plumbing.

**Default is unconfirmed — opt-in, the inverse of B1.** Entities default-
accept (creator curates *out*); judgment links default *unconfirmed*
(creator curates *in*). Confidence framing: entities are direct generation
output, links are the model's own "I think I sensed X" guess about
something the generator pipeline didn't structurally verify.

**Only two `sensed_links` kinds map to a relation.** `connection` ->
`connects_to` (direction `mutual`, intensity `50` — the same meaningless
structural default BRIEF-15 established for location-map topology).
`faction` -> `controls`, written **faction -> location**
(`entity_a_id`=faction, `entity_b_id`=location, `direction="a_to_b"`
explicit) — the default `direction="mutual"` would be semantically wrong for
a controller/asset relation, so it is always overridden. `parent` stays
display-only (the manifest's `parent_location_id` is already authoritative;
a perceived second opinion must never re-wire it) and `other` stays
display-only (no relation type fits). NPC `shared_with` stays display-only
(Q1, below).

**Q1 — secret memberships are out, deliberately, not foreclosed.** No
channel in the current pipeline produces a secret-membership suggestion, so
there is nothing to wire; building the write path now would be speculative.
A future manifest "double-agent" channel (model proposes a cover role +
true affiliation) would be the natural reader once it exists.

**S1 — targets resolve against the whole committed world.**
`_region_resolve_link_target` checks the just-committed entities first (by
name, from the `committed["locations"]`/`committed["factions"]` lists this
same call already built) then falls back to a DB exact-match scoped to the
world (mirrors `entity_author._resolve_faction_id`) — so a new region can
name a connection to, or be claimed by, geography/factions that already
exist in canon. Never auto-creates a miss; a miss is recorded as an
unresolved note with a reason, never written as a relation.

**Server-authoritative resolution, same posture as chantier 2's cascade.**
The client's `confirmed_links` map (`{"<location_local_id>#<index>": bool}`)
is advisory only. The endpoint independently re-checks: the link's source
location must itself have committed (`loc_id_map` hit) or the link is
dropped as unresolved; the resolved target must exist (intra-region or DB)
or it's dropped; a target resolving to the same entity as the source
(self-link) is dropped. No confirmed link can ever produce a dangling or
wrong-typed relation — the same "never trust the client's rendering"
discipline as `_region_resolve_location_parent`.

**Response shape.** The commit response gains `links: {written: [...],
unresolved: [...]}` alongside the existing `committed` block — each
unresolved entry carries `location_local_id`, `kind`, `name`, `reason` for
creator visibility.

**UI.** The D1 review tree's location nodes gain a small confirm/discard
toggle per wirable `sensed_links` row (`regionRenderLinkToggles`,
`regionConfirmedLinks` client state) right where the read-only note used to
render; `parent`/`other` rows keep rendering as plain notes via the existing
`regionEntityNotes`/`regionRenderNotes`, untouched.

**The region loop is now closed end-to-end:** the model only ever proposes
names (chantier 1, `region_author.py`); the creator confirms entities AND
links (chantier 2's accept/reject, chantier 3's confirm/discard); the code
resolves names to ids and wires both the structural skeleton and the
judgment links, atomically, in one transaction. No model-emitted id ever
reaches a `relation` row.

---

## REGION GENERATION — two-phase manifest checkpoint (BRIEF-38, schema v1.49)

**Why now.** Live testing of the chantier 1-3 region pipeline showed the
creator needs to edit the manifest's one-liners *before* the entity stages
run: the one-liner is the single largest lever on downstream generation
quality (RECON B5/K1 — one-liners are the only peer text crossing into every
composite brief built by `_compose_faction_brief`/`_compose_location_brief`/
`_compose_npc_brief`). Editing after Stage 1-3 (on the full draft tree) is
too late — the entity prose is already generated from the un-edited
one-liner.

**Phase split, not a rewrite.** `region_author.py`'s single-shot
`generate_region_draft(brief, db)` is split at the Stage-0/Stage-1 boundary:
- `generate_region_manifest(brief, db)` — Phase A. Mechanical extraction of
  the existing Stage-0 logic (empty-brief check, `pt-region-manifest` load,
  `chat()` call, `_parse_manifest_response` → `_normalize_manifest`). Every
  failure path returns the pre-existing `{"ok": False, "error": ...}` shape
  verbatim — no behavior change.
- `generate_region_draft(manifest, db)` — Phase B. Signature changes from
  `brief: str` to `manifest: dict` (already-produced, possibly creator-
  edited). Its first action re-runs `_normalize_manifest` on the incoming
  dict and uses the result as authoritative, then runs the existing Stages
  1-3 unchanged.

**Server-authoritative / client-is-advisory (structural over
instructional).** The edited manifest re-sent by the client is never trusted
directly — Phase B re-normalizes it before use, mirroring `commit_region`'s
posture toward the re-sent draft + accept/reject map. The C1 boundary
(one-liner is the only writable field) is enforced by the UI (name fields
rendered read-only) — not by a server-side "reject if a name changed" guard.
Under B1 (no draft store) the server has no stored Phase-A manifest to diff
the re-submission against, so re-normalization is the only — and sufficient —
safeguard: it cannot repair a creator's mistaken edit, but it guarantees
structural invariants (exactly one root, valid `parent_name`, NPCs placed
only into locations that exist in the manifest) regardless of what the
client sends back.

**B1 — no persistence, again.** Same posture as chantiers 1-3: the manifest
is held in `regionManifest` client-side only, between Phase A and Phase B,
and re-sent on "Générer les fiches" — no new table, no session store, no
server-side caching of the Phase-A output. The B1 precedent (region draft
held client-side, re-sent at commit) extends naturally to the manifest;
nothing new was invented here.

**C1 — one-liner text only, C2/C3 deferred.** The checkpoint screen
(`regionRenderManifest`) shows a flat list per kind (Factions, Lieux, PNJ):
entity name read-only, one-liner in an editable `<textarea>` bound directly
onto the held `regionManifest` object (`oninput` writes the field in place —
no separate "apply" step, since C1 was the only practice ever blessed). No
density steering, NPC floors, faction caps, count editing, add/remove, or
rewiring (planned R2 / C2 / C3) — the manifest's counts are whatever the
model produced, unclamped, exactly as chantiers 1-3 left them. K1 is
unweakened: the composite-brief composers still read only
`name`/`one_liner`/`parent_name`/`concept`.

**Routes.** `POST /api/regions/manifest` (new, `RegionGenerateBody`,
`{brief}`) is Phase A — writes no canon, same neighbourhood as
`/api/entities/generate`. `POST /api/regions/generate` is repurposed: its
request body changes from `{brief}` to `{manifest}` (`RegionBuildBody`) and
it now calls the refactored Phase B; its response shape (the full draft
tree) and its no-canon-write posture are both unchanged. `POST
/api/regions/commit` is untouched — still the single write point, still
re-derives the accept/reject cascade and judgment-link resolution
server-side from raw client state (chantiers 2/3, unaffected by this step).

**UI flow.** `regionGenerate()` now calls `/api/regions/manifest` and stores
the result in the new `regionManifest` client state, rendering the
checkpoint screen on success and surfacing the error (without advancing) on
failure — J1 preserved. A new `regionBuild()`, wired to a "Générer les
fiches" button, calls `/api/regions/generate` with `{manifest:
regionManifest}` and stores the result in the existing `regionDraft`,
handing off to the **unchanged** `regionRenderTree`. `regionRestart()` now
also nulls `regionManifest`. The review tree, accept/reject, cascade
preview, link confirm/discard, and the commit button are all byte-for-byte
untouched — the checkpoint is a new stage inserted *before* generation, not
a change to anything after it.

---

## REGION NPC DENSITY FLOOR — instructional steering, not a clamp (BRIEF-39, schema v1.50)

**Why now.** Live testing of the region pipeline (chantiers 1-3) showed
factions coming back thinly staffed and almost no unaffiliated NPCs — the
manifest model under-populates `npcs` relative to what a playable region
needs.

**Locked choice: B1 (instructional steering via the Stage-0 prompt) over
B2 (a re-prompt top-up clamp) or a structural code clamp.** The manifest
model (`llama3.1`, the authoring model) is compliant, and the failure mode
here is "a count is off," not "a secret leaked" — the same risk calculus
that already lets `pt-region-manifest` shape output through instruction
rather than code. `region_author.py`'s `generate_region_manifest` gained
**no count-enforcement code**: the floor lives only in
`REGION_MANIFEST_SYSTEM_PROMPT`'s text. K1 (manifest is the sole density
determinant — see chantier 1) is unweakened: the model still decides the
counts, the prompt only asks for more of them.

**Floor values (locked).** At least 4 NPCs per faction (`faction_name`
exact match) and at least 4 factionless NPCs (`faction_name = null`) per
region. These are minimums, not targets to hit exactly — the brief can
still ask for more.

**The floor is a target, not a guarantee.** Live test (brief naming 3
factions: a garrison, a smuggler guild, a heretic cult) with
`llama3.1:8b` produced only 1 NPC per faction and 3 factionless NPCs out
of 6 total — well under the floor. This is **recorded as a finding**, not
patched in this step (scope OUT: no code clamp, no re-prompt). It is the
expected signal that motivates **B2** below, not a bug in B1's prompt
wording.

**Deferred: B2 — re-prompt top-up clamp.** If live testing continues to
show steering undershoots (as it did above), a follow-up step can add a
second model call that tops up under-floor factions/factionless NPCs
without touching the original manifest's accepted entities. Not opened
automatically by this finding — a deliberate next-step decision.

**Deferred: A2 — role-exact staffing ("1 NPC per role").** Not calculable
at manifest stage: faction roles are generated fresh in Stage 1, after the
R1 checkpoint, so the manifest has no role vocabulary to staff against.

---

## REGION NPC TOP-UP CLAMP — A1, targeted re-prompt (BRIEF-40, schema v1.51)

**Why now.** BRIEF-39's instructional steering (B1) proved unreliable in
live testing: NPC counts came back at floor one run, zero the next — the
small authoring model (`llama3.1:8b`) drops the density constraint
unpredictably. **Locked: A1 — a code-side targeted re-prompt clamp**, the
B2 deferral named in BRIEF-39.

**K1 amendment (bounded).** K1 previously held "the manifest is the
**sole** density determinant; no numeric code knob." This step amends K1,
justified by K1's own escape clause ("no knob until a measured problem
forces it") — the measured 4-then-0 shortfall is that problem. The
amendment is bounded: the code floor may only **add** NPCs to reach a
minimum; it never caps, removes, or overrides the model's choices above
the floor. The manifest remains the primary density source — B1 steering
(BRIEF-39's prompt-text floor) stays in place, since it shrinks the gap
the clamp has to close.

**Mechanism.** Inside `generate_region_manifest` (Phase A), after
`_parse_manifest_response` succeeds and before return: compute the
shortfall against `MIN_NPCS_PER_FACTION` (4) per faction and
`MIN_FACTIONLESS` (4) factionless, per `region_author.py`'s
`_npc_deficits`. Zero deficit → return unchanged, no model call. A
non-zero deficit issues **one** narrow re-prompt
(`pt-region-manifest-topup`, usage `region_manifest_topup`) to the
**same** `AUTHOR_MODEL` (never the game model — a hard requirement, not a
default) asking for exactly the missing NPCs per target
(`_run_npc_topup`). **One pass only**: success or failure, the function
returns after this single attempt — no loop, no second pass (A3,
deferred).

**Merge-before-normalize.** The top-up response is never normalized on
its own partial payload — that would silently drop every new NPC, since
`_normalize_manifest` expects a full manifest shape (factions/locations
context to validate `location_name`/`faction_name` against). The new NPCs
are merged into the full manifest dict first
(`{**manifest, "npcs": manifest["npcs"] + new_npcs}`), then
`_normalize_manifest` runs on the merged whole — same function, same
invariants (dedup, location/faction resolution) as Stage 0's own output.
Skips from the merge are appended (not overwritten) to the original
`skipped` list — the original Stage-0 skips survive.

**Graceful degradation, never an abort.** A top-up failure (Ollama down,
non-JSON response, empty/missing `npcs`, missing template, template
format error) is caught in an isolated `try/except` around the top-up
call only. On any failure: append a note to `result["notes"]` and return
the **original** `result` unchanged — the primary manifest's `{"ok":
true}` is preserved, downstream stages proceed with a short-but-valid
manifest. This is asymmetric with the primary path: a failed *primary*
manifest still aborts via the unchanged `{"ok": false}` J1 path; a failed
*top-up* never aborts anything, by design (J1 is about the plan being
missing, not about the plan being merely short).

**Residual shortfall is a note, not a second attempt.** If the merged,
re-normalized manifest still falls short of the floor (the model
under-delivered even the requested count, or some new NPCs were skipped
on a bad `location_name`), a single note is appended
("Plancher PNJ non atteint après complément : …") and the manifest is
returned as-is. This records the signal for a possible future A2/A3
escalation without building it now.

**Real names, no stubs.** Added NPCs are real model-generated entities
(name + one-liner + location + faction), never placeholder stubs — that
deferred path is A2 (deterministic name-pool net), out of scope here. This
keeps the R1 checkpoint invariant intact: every NPC arriving there,
original or topped-up, has a real name and an editable one-liner.

**Constants/prose coupling.** `MIN_NPCS_PER_FACTION` / `MIN_FACTIONLESS`
(`region_author.py`) must equal the prose floor in
`REGION_MANIFEST_SYSTEM_PROMPT` (`seed_pilot.py`, BRIEF-39's text) — a
one-line sync comment lives at the prose floor pointing back to the
constants. No code enforces this sync; it's a manual-discipline coupling,
same posture as other constant/prose pairs in this codebase.

**Deferred (named, not built).** **A2** — a deterministic name-pool net
guaranteeing the floor with placeholder-derived names if the model still
falls short. **A3** — more than one re-prompt pass. **Faction caps** —
the clamp adds only; capping or removing NPCs above the floor is
explicitly out of scope and was never considered for this step.

---

## REGION REVIEW — read-only full-sheet modal (BRIEF-41, R4a, schema v1.52)

RECON (`RECON-region-fullsheet-modal`) confirmed the full draft (every
public field + the secret block) already rides into every review-tree
node as `entry.result.draft` since BRIEF-36 — never rendered. This step
adds a read-only modal, opened by clicking an entity's **name**, showing
that full draft. **Pure client render** — no new endpoint, no payload
change, no canon read/write; `regionRenderSheet(type, localId)` reads only
the in-memory `regionDraft`.

**Secrets shown by design.** This is the creator surface, not the player
surface — the modal's secret section is labelled "Secret — caché en jeu"
and is creator-only display. In-play structural exclusion is enforced
elsewhere (the context assemblers and `read_public_memberships`-style
accessors), and this step does not touch any of that — the modal feeds no
prompt and issues no fetch.

**Click target isolation.** The modal opens from the name/header element
only, structurally distinct from the existing accept/reject
(`regionToggleAccept`) and link confirm/discard (`regionToggleLink`)
buttons — no collision, no regression to those controls.

**Deferred (named, not built).** Editing the rendered sheet (D1/D2) and
add-missing (B/C) stay deferred — the modal body is a swappable plain
container (not three separate modals) so a future editable mode can mount
there without restructuring, but no editing is built now.

---

## REGION DEDUP NAME-KEY HARDENING — bugfix (BRIEF-42, schema v1.53)

RECON (`RECON-duplicate-npc-name`) found two NPCs both named "Lysandra la
Sagesse" surviving in one region draft. Verdict H1: `_dedupe_by_name`'s
comparison key (`name.strip().lower()`, `region_author.py`) only trims
outer whitespace and case-folds — it has no defense against
apostrophe-glyph variants (`'` U+0027 vs `'` U+2019/U+02BC), inner/
non-breaking whitespace differences, or Unicode accent-composition
differences, so two byte-different renderings of the same name both
survive. H2 was ruled out: the A1 top-up merge and the Phase-B re-submit
both correctly re-run `_normalize_manifest`/`_dedupe_by_name` over the
full merged list — that wiring was already correct, root cause was the
weak key, not the merge path.

**Fix.** A module-level `_name_key(name)` (NFC normalize, fold apostrophe
variants to `'`, collapse inner whitespace incl. NBSP, lowercase) replaces
the raw key inside `_dedupe_by_name`. Behavior is unchanged: still
global-by-name, first-occurrence-wins, drop-later + note; the kept row's
stored `name` stays byte-for-byte the original. `_dedupe_by_name` is
shared across NPCs/factions/locations, so all three get the same
hardening. No schema/route/canon change.

---

## WORLD BOOTSTRAP + PREMISE READER — B2 (BRIEF-44, schema v1.55)

**Decision β over α.** Two ways to give a newly-bootstrapped world an
identity were on the table: α — generate the bible (`description` /
`fundamental_laws`) at creation time via a model call; β — let the creator
type it at creation, and build only the reader that makes those two
already-existing, previously-dormant `World` columns load-bearing. β was
chosen: it is strictly smaller (no new prompt, no new model call, no
generation-quality risk on a field that gates every future region in the
world) and it is the same seam a future model-authored generator would
plug into — B3 = this reader + a generator that fills the same two fields,
not a parallel mechanism.

**`POST /api/worlds`** (`cockpit/app.py`, beside Brief 1's
`/api/worlds/{id}/activate` — deliberately not `crud.py`, same reasoning
as the activate route: this creates a selection-scoped row, not narrative
canon in an existing world) takes `name` + `description` +
`fundamental_laws` (the latter two optional), inserts one `World` row
(fresh UUID via the existing `_uuid` default-factory — never pattern-matched
to `"verkhaal"`), and auto-activates it by reusing the activate route's
deactivate-all-then-activate-target logic inside the same transaction and
single `db.commit()`. The created world is empty by construction — the
route does nothing beyond the one `World` insert, so there is no PC,
session, location, template, or entity to clean up.

**Premise reader.** `region_author.generate_region_manifest` now resolves
the active world (`_active_world`, the same `is_active == True` query as
`crud._world_id`, kept local to `region_author.py` rather than imported
from `cockpit.crud` to avoid a core-module-depends-on-UI-layer inversion)
and renders two additional, independently-optional blocks ahead of the
existing `brief`: `Contexte du monde : {description}` and `Lois
fondamentales du monde (contraintes absolues) : {fundamental_laws}`. Each
block is built in Python as a complete, ready-to-splice string (label +
text + trailing blank line) or `""` when the corresponding world field is
empty — the prompt template (`pt-region-manifest`, `user_template`) just
interpolates `{world_description}{world_fundamental_laws}` ahead of
`{brief}` via plain `.format()`, so an empty-premise (B1-style) world
renders byte-identical to the pre-BRIEF-44 brief-only prompt: no dangling
label, no conditional logic in the template itself. `generate_region_draft`
does not render this template (it only composes `entity_author`'s
per-entity prompts), so it needed no change.

**Not a structural-exclusion exception.** `World.description` /
`fundamental_laws` are public world identity — not secrets, not gated by
any accessor boundary — so injecting them into the manifest prompt is
ordinary non-secret world config reaching a prompt, the same category as
`entity.metadata.price_list` or faction `philosophy`. It must not be read
as precedent for injecting other, non-public world state into prompts.

**Deferred, named:**
- **B3 — model-authored bible.** Resolved by BRIEF-47 (see "WORLD-BIBLE
  GENERATOR — B3" below) — sat directly on top of this reader, no
  reader-side change was needed.
- **Bible editing.** `description` / `fundamental_laws` are set-at-creation
  only; no `PATCH`/edit route exists yet for an already-created world's
  premise. Still deferred after BRIEF-47 — the generator only feeds the
  create-time form, it does not add an edit path.
- **Region provenance (D2).** Entities generated into a world remain flat;
  no `region` table or `region_id` tags which generation pass produced
  what. Unaffected by this step.

---

## WORLD-BIBLE GENERATOR — B3 (BRIEF-47, no schema change)

**Resolves the B3 deferral above.** A creator-side draft generator that
turns a one-line seed into a `description` / `fundamental_laws` draft,
pre-fills the existing "Nouveau monde" create form, and commits through the
**unchanged** `POST /api/worlds` (`create_world`) — same shape as the B2
decision: build the smallest thing that fills already-existing, already-read
fields, not a parallel mechanism.

**Sibling to `generate_entity_draft`, not routed through it.**
`entity_author.generate_world_draft(brief, db)` mirrors the entity-author
propose flow (`AUTHOR_MODEL`, `chat(..., format="json")`, JSON parse,
notes-on-drop) but is its own function: `World` is not an `entity` row (no
`entity_id` FK), so it can never ride `_create_entity_core`, and there is no
`_TYPE_FIELDS["world"]` entry — adding one would have been the wrong seam.
`db` is strictly read-only inside this function: its only use is the new
`pt-world-generation` template lookup (`_load_world_template`, mirroring
`_load_template`). Unlike `region_author.generate_region_manifest`, this
function *creates* a world, so there is no existing premise to read or
inject — the asymmetry with B2's reader is intentional, not an oversight.

**`fundamental_laws` flattening is structural, not a frontend concern.** The
model is prompted to return `fundamental_laws` as a JSON array of short,
world-spanning constraints; `generate_world_draft` flattens that array in
Python to a numbered, newline-joined string (`"1. ...\n2. ..."`) before
returning. The draft value that reaches the form — and, once created, the
exact value `region_author.py`'s premise reader later loads — is always a
flat `str`, never a list/dict/Python-repr. A non-list `fundamental_laws`
from the model is dropped with a note rather than coerced.

**`POST /api/worlds/generate`** (`cockpit/app.py`, beside
`POST /api/entities/generate` — same no-canon-write neighborhood, same
reasoning: this route writes nothing, so it stays out of `crud.py`)
delegates only to `generate_world_draft`. The frontend mounts a "Générer
avec l'IA" panel *inside* the existing `worldCreateOpen()` modal (not a
separate modal) so the three pre-filled fields are the exact same inputs
`worldCreateSubmit()` already reads — that submit function, `create_world`,
and `WorldCreateBody` needed zero changes. Regenerating re-runs the same
call and overwrites the fields in place; there is no separate "discard"
step because the fields are ordinary editable inputs.

**Verified end-to-end** against the live cockpit with Ollama
(`llama3.1:8b`): seed → generate → edit a field → create → the new world's
premise renders into a region manifest generation identically to a
hand-typed world's, confirming the B2 reader needed no change; a second
"Générer" on a different seed fully overwrote the first draft.

---

## CRÉATION WORLD SCOPING (BRIEF-48, no schema change)

**The Création surface listed entities from every world, not just the
active one.** A single unscoped chokepoint, `GET /api/entities`
(`cockpit/crud.py`), backed 6 of the 9 Création sub-tabs (NPC, Personnage
joueur, Lieux, Factions, Objets, Artefacts). Two secondary list endpoints
(`GET /api/skills/player-characters`, `GET /api/ledger`) and the review
queue (`GET /api/mutations`) were also unscoped. This step closes all four
read paths plus the client-side staleness on world switch — no schema, no
canon-write path touched.

**Scoping is structural at every site — a `.where(... world_id ...)` clause
in query construction, never a post-fetch filter,** reusing the existing
`_world_id(db)` resolver unchanged (its raise-on-no-active-world posture is
not softened):
- `list_entities` (`crud.py`) — `.where(Entity.world_id == _world_id(db))`.
- `list_skill_player_characters` (`crud.py`) — `.where(Character.world_id
  == _world_id(db))` (the BRIEF-46/v1.57 denormalized column).
- `get_ledger_journal` (`crud.py`) — `ledger.list_entries` gained an
  optional `world_id` param; the global-journal route passes
  `_world_id(db)`. `ledger.world_id` exists directly on the table, so this
  is a plain clause, not a join — the per-entity ledger route
  (`GET /api/entities/{id}/ledger`) passes no `world_id` and is unaffected,
  already scoped transitively through its `entity_id`.
- `list_mutations` (`cockpit/app.py`) — `.where(ProposedMutation.world_id ==
  _crud._world_id(db))`. `proposed_mutation.world_id` also exists directly;
  this endpoint lives in `app.py`, not `crud.py` (the review-queue resolver
  was previously unverified — RECON confirmed its location here).

**Client-side staleness on world switch.** `activateWorld` (`index.html`)
previously only refreshed the world selector after activation, leaving
stale other-world rows rendered from cached client state
(`authorAllEntities`, `playerCharIds`, `skillCharacters`, the Registre
entity-filter cache) until a manual reload. On a *successful* activation it
now nulls those four caches and, if the Création view is currently visible,
re-invokes `showCreationSubTab(currentCreationSubTab)` (or `creationInit()`
if Création has never been opened) — reusing the same per-tab loader
dispatch the tab-switch path already calls, rather than a parallel refresh
mechanism. The visible sub-tab updates immediately; every other sub-tab
re-fetches fresh on next view because its cache was nulled. A failed
activation leaves all caches and the visible tab untouched.

**Verified directly against the ORM** (two `World` rows, one `Entity` each,
toggling `is_active`): with world A active, `list_entities` returned only
A's entity; flipping the active flag to B returned only B's. The full
in-browser multi-tab/multi-world walkthrough from the brief's "Done means"
was not run this step — see Debts below.

**Naming note:** the source brief was filed as `BRIEF-47-creation-world-
scoping.md`, but BRIEF-47 was already consumed by the World-Bible Generator
(previous section, same numbering authority). This step is recorded as
BRIEF-48 to keep the sequence unique; the brief's own content used a
placeholder `BRIEF-NN` title.

---

## PER-MODAL BACKDROP DISMISS (BRIEF-50, no schema change)

**Outside-click on the generic modal shell (BRIEF-41) destroyed unsaved
input in form-bearing modals.** The shared `generic-modal-backdrop` is
dismissed on outside-click via an inline handler that always calls
`genericModalClose()` (which clears `generic-modal-body.innerHTML`). Of the
two `genericModalOpen` consumers, `worldCreateOpen` renders a creation FORM
(name/description/fundamental_laws) — losing it to an accidental outside
click is a bug — while `regionRenderSheet` renders a read-only entity sheet,
where click-away dismissal is a harmless, useful affordance.

**Fix is an opt-out flag, not a new mechanism.** `genericModalOpen(title,
bodyHtml, options)` gained `options.dismissOnBackdrop` (default `true`,
preserving existing behavior for every un-migrated caller). The flag is
written to `generic-modal-backdrop.dataset.dismissOnBackdrop` on every open
(no stale leak across modals — verified by opening the false-flag form, then
the default-true sheet, in the same session) and read by the backdrop's
existing `event.target === this` outside-click guard before calling
`genericModalClose()`. `worldCreateOpen` now opens with `dismissOnBackdrop:
false`; `regionRenderSheet` is untouched (keeps the default).

**× and Escape are deliberately untouched** — both call `genericModalClose()`
unconditionally for every consumer, including form modals. Only the
*accidental* backdrop dismissal is gated; every modal retains at least one
working explicit close path regardless of the flag's value.

---

## LIEUX HIERARCHY BROWSE (BRIEF-51, no schema change)

**Locked design.** Per-level type grouping (A1): each screen groups the
current node's children into `LOCATION_TYPE_ORDER` buckets, not a single
flat list. Breadcrumb replace (B1): descending overwrites the rail in place
with the children screen; a breadcrumb trail (always starting at "Racine")
provides the way back — no separate flat-list view, no modal stack. `room`
is vocabulary + display-order only (C1): it is appended to the creator CRUD
`location_type` datalist and given a position in `LOCATION_TYPE_ORDER`
between `building` and `natural` — nothing else changes. No structural
parent-type constraint exists or is scaffolded; `parent_location_id` stays a
free tree, and the region generator (`entity_author.py`) is untouched —
`room` is creator-CRUD-only, never offered to the generator. In-place
replacement of the existing *Lieux* rail (D1): the browse IS the rail for
that sub-tab, not an added panel. Dedicated read-only endpoint (E1):
`GET /api/locations`, separate from `GET /api/locations/graph` (the SVG map
panel, untouched) and from `GET /api/entities` (which carries neither
`parent_location_id` nor `location_type`). All statuses returned (F2): the
endpoint applies no `status` filter (unlike the graph endpoint), and the
default "Actifs seulement" toggle is OFF. Dimmed + status pill, plus a
toggle (G2): a non-active node always renders with a `dimmed` class and a
literal status-string pill; the separate "Actifs seulement" checkbox is the
only filter, no per-status colour coding. Traverse-through preserved (H2):
toggling "Actifs seulement" ON hides a node only when it is non-active AND
has no active descendant (`lieuxHasActiveDescendant`, recursive with a
`visited` guard against malformed cycles) — a non-active building containing
an active room stays visible (dimmed) and traversable.

**Orphan locations surface at root, never disappear.** A location whose
`parent_location_id` points to an id absent from the fetched tree (soft-
deleted parent, cross-world leftover, etc.) is treated as a root child
(`lieuxChildrenOf(null)` matches `!parent_location_id || !knownIds.has(...)`)
— it is never silently dropped from the browse.

**Creator browse intentionally shows what player-facing context never
would.** `GET /api/locations` applies no `is_public` filter, matching
`list_entities`'s existing behavior — this is the creator's own management
surface, not a context assembled for a model or a player. Secret structural
exclusion (`character.secrets`, `knowledge.is_secret`) governs NPC prompt
assembly and is not implicated here.

**Active-world scoping is the chokepoint defended.** `GET /api/locations`
filters `Entity.world_id == _world_id(db)` exactly like `list_entities` and
the graph endpoint, placed immediately adjacent to
`GET /api/locations/graph` in `crud.py` to keep the two read patterns
visually comparable. The endpoint is read-only end to end — no
`_apply_mutation` call, no `change_history` write, no canon mutation of any
kind.

**No server-side persistence of browse state.** `lieuxBrowseParentId`,
`lieuxBreadcrumb`, and `lieuxActiveOnly` are client view-state only, reset
when the *Lieux* sub-tab is freshly entered — consistent with the project's
no-draft-persistence doctrine elsewhere in the cockpit.

---

## PC CREATION ASSISTANT (BRIEF-52, schema v1.60)

**Locked design.** A1 — the model proposes `entity.description` +
`knowledge[]` + the player-reference `appearance`/`backstory` only; never
`aversion`, `physical_tier`, or a secret block. B1 — skills stay flat
`tier=0`; no model-proposed tiers. C1 — starting location stays
creator-picked in the dropdown; the model is silent on it. D1 — no secret
block, no `secret` JSON envelope. E1 — accept goes through the existing
`POST /api/characters/player`, extended, not a new endpoint. G1 — a
dedicated `pt-player-generation` template and a standalone
`generate_player_draft` sibling function; no `_TYPE_FIELDS["player"]`
entry, no public/secret two-block contract. H1 — structural co-presence
hardening so A1 holds by construction, not by caller convention. I1 —
prose fields (`description`/`appearance`/`backstory`) are inline-editable
in the draft; `knowledge[]` is read-only there, edited post-creation on the
Fiche via the existing knowledge CRUD.

**Standalone sibling, same shape as `generate_world_draft`, not the
entity-author parser.** `entity_author.generate_player_draft(brief, db)`
mirrors `generate_world_draft`'s propose flow (`AUTHOR_MODEL`,
`chat(..., format="json")`, JSON parse, notes-on-drop, never raises) but
parses a **single top-level JSON object** — `{name, description,
appearance, backstory, knowledge}` — with no `public`/`secret` nesting.
This is deliberately NOT a `_TYPE_FIELDS["player"]` entry routed through
`generate_entity_draft`: that parser's two-block contract exists to
segregate public fields from a secret block a PC must never have (D1), and
reusing it would have required carving out an exception inside a function
whose entire job is producing one. `db` is read-only: its only use is the
`pt-player-generation` template lookup (`_load_player_template`, mirroring
`_load_world_template`). The function never calls `_create_entity_core`
and emits no `world_id`/`current_location_id`/`faction`/`entity_id` —
location stays creator-resolved (C1), the same display-only posture as
`sensed_links`.

**PC knowledge normalization is a new, deliberately separate helper —
reusing `_normalize_knowledge` was a trap.** `_normalize_knowledge`
(NPC-only, BRIEF-24) forces `is_secret=True` in code, because every NPC
knowledge row it produces is concealed-by-default until the creator
decides otherwise. A PC's own knowledge is the opposite case: it is never
secret from the player who *is* that knowledge. `_normalize_player_knowledge`
is a sibling function that validates `{subject, level, content}` rows
(drops malformed/empty rows, falls back an unrecognised `level` to
`"rumor"`, caps at 5) and emits no `is_secret` key at all — the draft is
data only. `is_secret=False` is applied at write time, in the accept
route, never in the generator.

**Knowledge write rides the sanctioned `writes.write_knowledge` helper,
not the entity-knowledge CRUD endpoint.** `POST
/api/entities/{id}/knowledge` (`crud.py`) 422s on an unrecognised `level` —
correct for a creator typing a value by hand, wrong for a model-proposed
draft that may carry a level outside the ladder. The accept route
(`create_player_character`, extended) calls `write_knowledge` directly
inside its existing single `try`/`db.commit()` block, defaulting an
invalid level to `"rumor"` exactly like the analyzer already does for
model output elsewhere (see CLAUDE.md "Local model notes"). The 4-skill
seed is untouched — byte-identical to BRIEF-46 — and the one-PC-per-user
guard (`idx_character_one_pc_per_user_world`) still governs the same
`IntegrityError` → `{"ok": false, "error": ...}` path.

**H1 — co-presence exclusion becomes structural, not conventional.** The
`H_COMPANY` query inside `assemble_npc_context` (`context.py`) gained
`Character.character_type != "player"`. Before this commit, A1 ("a PC's
`appearance`/`description` never reaches an NPC prompt") held only because
every one of the four call sites passes the player as `interlocutor_id`,
which a downstream `co_entity.id in (npc_id, interlocutor_id)` check then
filters. That is caller discipline, not a guarantee — a future call site
that forgets to pass the player as `interlocutor_id` would silently leak a
PC's `appearance` into an NPC's "AVEC QUI TU TE TROUVES" list. The new
predicate excludes a PC from that query's result set unconditionally, by
construction, independent of any caller's `interlocutor_id` argument.
Behaviorally a no-op today (the player was already filtered downstream at
every existing call site) — deliberately shipped as its own commit,
separate from the assistant itself, because it changes a *different*
file's invariant surface (`context.py`, not the player-creation path) and
deserves its own review.

**Carried-forward deferrals, not addressed here:**
- **B2** — model-proposed skill tiers or a point/zero-sum budget. Skills
  stay flat `tier=0`.
- **C2/C3** — model-suggested or model-emitted starting location. Stays
  creator-picked in the dropdown.
- **D2/G2** — a secret block, a `secret` JSON envelope, or a
  `_TYPE_FIELDS["player"]` entry.
- **I2** — inline knowledge editing inside the draft. `knowledge[]` stays
  read-only there; post-creation editing is the existing Fiche knowledge
  CRUD.
- **Tier-3 onlooking-PC perception.** When NPC-to-NPC observation lands,
  how an onlooking PC is represented to NPCs is a deliberate decision made
  then, via a dedicated path reading `description` — not by widening the
  H1 filter or by routing it back through the `appearance`-first
  co-presence default this brief just excluded the PC from.

---

## GATHERING LIFECYCLE RECONCILIATION (BRIEF-53, application-layer, no schema change)

RECON (findings, commit `a5f12c0`) established a single shared root behind
two live-play bugs: nothing closed an NPC's `gathering_member` row except
`migrate_npc`, and nothing reconciled `gathering_member` against
`current_location_id` or `entity.status`. This step seals the root at the
creator-CRUD write site (A1) and adds a defensive vivacity gate on the
roster/co-present reads (B1).

**A1 — write-side reconciliation seam.** `close_open_memberships`
(`gathering.py`) is `migrate_npc`'s inline B1-repair close, extracted
verbatim into a module-level helper: select `gathering_member` rows for
`entity_id` with `left_at IS NULL`, set `left_at = now` on each, never
delete. `migrate_npc` now calls it — net behavior byte-identical. The
creator-CRUD entity editor (`update_entity`, `cockpit/crud.py`) calls it
when a `character`'s `current_location_id` actually changes (re-saving the
same value closes nothing) and when `entity.status` transitions away from
`"active"`; `delete_entity`'s soft-delete (`status = "inactive"`) calls it
unconditionally. The helper writes no canon — no `_apply_mutation`, no
`proposed_mutation`, no `change_history` — because gatherings are not
canon.

**B1 — defensive read-side vivacity gate.** `_active_members`
(`cockpit/app.py`, the Play roster), `assemble_npc_context`'s H_COMPANY
roster query, and `assemble_mj_context`'s co-presents query
(`context.py`) each gained a join to `Character` and the where clauses
`Entity.status == "active"` and `Character.vital_status == "alive"`,
mirroring `_present_npcs`. The roster's membership predicate remains
`gathering_member.left_at IS NULL` (single source, no snapshot). The added
`entity.status='active' AND vital_status='alive'` filter is an
entity-vivacity gate computed live at read time, not a cached roster — it
narrows *which live members count*, it does not replace the membership
source. B1 is not redundant with A1: `entity.status`/`vital_status` can
change via paths other than creator CRUD — the mutation pipeline's
`status_change` (an NPC dies or is destroyed) closes no membership row. B1
defends every state-change path at the read; A1 defends only the two CRUD
edits at the write. Both are needed.

**Named deferral — destination promptness (C1).** A creator move into a
location that already holds an open gathering this session reflects in
Play only at the next genuine entry to that location; the busy destination
is not force-regenerated. This preserves C1 (generated once at entry; no
mid-scene reshuffle). After A1 the move is already *consistent* (the NPC
is removed from its old gathering and never double-membered) — only its
*appearance at the new busy location* waits for re-entry.

**Named deferral — never-closing session.** `GameSession.status` is only
ever `"open"` (`app.py`); no end-session affordance exists in the cockpit
or as an endpoint. Stale per-session state (orphaned `Gathering` rows
whose members were closed, etc.) accumulates indefinitely. Deferred: a
session-close path that dissolves open gatherings.

---

## WORLD BLOCK DELETION (BRIEF-54, schema v1.62)

A prior RECON (`recon-world-block-deletion-findings.md`) established the
ground truth this step builds on: the cascade is greenfield (no `region`
precedent; region persistence stays deferred, see "Deferred decisions"
below), `PRAGMA foreign_keys=ON` is enforced at the engine (`db.py`),
`prompt_template.world_id` is nullable with 13 global `world_id=NULL`
seeds that must survive any cascade, and no server-side redirect mechanism
exists anywhere in the app.

**A1 — hard delete, full cascade, irreversible.** No soft-delete, no
`deleted_at`, no trash/undo. This is the single deliberate violation of
*History is sacred* in the whole system, contained entirely inside one
named helper, `delete_world_cascade` (`writes.py`) — the first delete-side
helper in that module, registered as the sole exception in `CLAUDE.md`'s
invariants list. Mirrors the framing already used for `resource_change`'s
two-table-in-one-SAVEPOINT exception (`:1556` above): a deliberate,
contained, named violation of a stated invariant, not a precedent for
more deletion code.

**B2′ — type-`Oui` confirm, not type-the-name.** The original type-the-
world-name confirmation (B2) was downgraded during planning: a short,
exact-match `Oui` gate is enough friction against a reflexive misclick
while staying fast for a single-player creator tool. The confirm modal
reuses the existing click-away-protected pattern (`genericModalOpen(...,
{ dismissOnBackdrop: false })`, the same shape `worldCreateOpen()` uses) —
× and Escape still close it; only the backdrop is gated.

**C2-c — deletion permitted while active; last-world deletion force-opens
creation.** Deleting the active world is allowed (no "switch away first"
requirement) and re-resolves `is_active` onto a survivor in the same
transaction (G1). Deleting the last world leaves zero worlds — there is no
redirect mechanism in this app (client-side or server-side) to send the
creator anywhere, so the frontend response handler calls the existing
`worldCreateOpen()` directly when `remaining === 0`, the same modal the
"+ Monde" button opens. No `RedirectResponse`/`HX-Redirect`/3xx was added;
this app has none anywhere and BRIEF-54 doesn't introduce the pattern.

**D1 — `PRAGMA defer_foreign_keys = ON` for the cascade.** Set on the
session connection inside the caller's transaction, before any DELETE.
This defers FK *constraint* checks to COMMIT, so the self-referential
columns (`location.parent_location_id`, `faction.parent_faction_id`,
`character.current_location_id`) resolve without a separate null-out pass.
It does NOT make statement order fully arbitrary, though: several deletes
are correlated subqueries against `entity`/`conversation`/`gathering`/
`session` (e.g. `knowledge` via `entity_id IN (SELECT id FROM entity WHERE
world_id = :wid)`), and those must run while the parent rows they query
still exist, or the subquery returns nothing and rows get orphaned —
silently, since the FK *check* is deferred to commit and a row that's
already gone can't raise on a subquery that found zero matches. The
deferral genuinely buys order-independence among the plain
`world_id`-scoped deletes (no subquery), and among the self-referential
columns within `location`/`faction`/`character`; it does not exempt the
subquery-dependent deletes from running before their parent table is
cleared.

**E1 — extract `_activate_world_core`, delete-path only.** `app.py`
already had this deactivate-all → `db.flush()` → activate-one logic
written out twice (`activate_world`, `create_world`'s auto-activation
step) with no shared helper — confirmed by the prior RECON (section 6).
This step extracts a third copy as `_activate_world_core(world_id, db)`
so the delete route can re-resolve `is_active` onto a survivor without a
third inline duplication. The flush-between is mandatory regardless of D1:
`idx_world_one_active` is a partial UNIQUE index, not a FK — `PRAGMA
defer_foreign_keys` does not cover it, so two `is_active=TRUE` rows must
never coexist even mid-transaction.

**Named deferral — converging `activate_world`/`create_world` onto
`_activate_world_core`.** Deliberately NOT done here. The existing inline
duplication at both call sites stays untouched; converging all three onto
one helper is a separate, named cleanup, not bundled into a delete-only
brief.

**F2 — no auto-backup.** `scripts/backup.py` exists, is documented as a
manual pre-session step, and has zero existing call-sites (confirmed by
the prior RECON, section 10). BRIEF-54 does not import it or call it from
the delete path — an automatic backup before an irreversible action was
considered and explicitly rejected; the creator is expected to back up
manually if they want a safety net before deleting a world.

**G1 — re-activate the most-recently-created survivor.** `ORDER BY
created_at DESC LIMIT 1` among the worlds remaining after the cascade.
Arbitrary but deterministic and the cheapest rule available — no "last
played" timestamp exists on `World` to prefer instead.

---

## WORLD-SCOPED CUSTOM SKILL CATALOGUE — table + both readers (BRIEF-55, schema v1.63)

**1-C — two readers, asymmetric guarantee, by design.** The catalogue
(`skill_definition`) is consumed by two structurally different readers, and
this asymmetry is intentional rather than a violation of
"structural-over-disciplinary":

- **Arbiter (mechanical) — structural/deterministic.** The candidate domain
  set, the clamp, and the resolution path (custom name → `base_domain` →
  the PC's `skill_definition_id`-keyed row → `tier`) are all enforced in
  Python, by query construction and a code-side clamp. A custom skill
  either resolves correctly or falls back to `"physical"` — never an
  invented or silently-wrong outcome.
- **MJ narration (ambiance) — an assumed probabilistic nudge, not a
  guarantee.** Injecting custom skill names into the narration prompt only
  *encourages* the local model to use the world's vocabulary; nothing
  structurally forces the model to use a name once it is in context, the
  way the arbiter's clamp forces a valid domain. This is accepted because
  the narration layer has no canon-write consequence — at worst the
  vocabulary doesn't surface in a given line, never a wrong roll or a
  leaked secret.

The master invariant ("structural over disciplinary") is about
**canon-affecting and security-affecting behavior**: the mechanical layer
that touches dice/canon stays fully structural. A best-effort vocabulary
nudge into free narration prose is not in that category, the same way
`pt-mj-narration`'s prose itself is never structurally guaranteed to use any
particular word.

**FK-by-id is the rename-safety mechanism.** `skill.skill_definition_id`
(not a copied name string) is a custom skill's identity. Every reader
(arbiter resolution, MJ vocabulary, the skill sheet display) resolves
the display name by joining to `skill_definition.name` at read time — so
renaming a `skill_definition` row propagates everywhere instantly and
orphans nothing. This is the same rename-safety pattern role roles/factions
already use for membership labels, applied here to a brand-new table instead
of retrofitted onto the existing free-text `skill.domain` column (which
stays a base-domain literal, never a definition name).

**Decision 3 — one source of truth for the four base domains.**
`BASE_SKILL_DOMAINS` (`models.py`) replaces three independently-declared
literal tuples (`cockpit/app.py` `_PHYSICAL_DOMAINS`, `cockpit/crud.py` and
`seed_pilot.py` `SKILL_DOMAINS`) that had drifted into existence with no
shared import (RECON IP-2/IP-7 — see `recon-world-scoped-skills-findings.md`
for the prior-state inventory). `skill_definition.base_domain`'s CHECK
constraint is the first-ever validated reference to a domain in this
codebase; it cites the same constant rather than introducing a fourth copy.

**Deferred to chantier 2 (closed in BRIEF-56 below):**
- The creator CRUD surface for `skill_definition` (no "Compétences" sub-tab,
  no routes, no frontend) — the only way a custom skill exists after this
  brief is the pilot seed fixture.
- AI authoring of a catalogue during world creation (no `pt-skill-catalogue`
  template, no `entity_author.py` change) — RECON IP-6 left the attachment
  point (extend `generate_world_draft` vs. a standalone generator) as an
  open choice for chantier 2 to pick.
- The real delete/rename UX and any cascade. `ON DELETE RESTRICT` (this
  brief) is a structural floor only — it prevents a silent orphan, it is not
  the final word on what deleting a custom skill should do (snapshot?
  confirmation modal? soft-delete with history?).
- **B2 — per-PC subset selection.** Every PC currently seeds every custom
  skill of its world (B1, flat). Letting a PC choose a subset at creation
  remains a live, unforeclosed option — nothing in this brief's `skill_row`
  lookups assumes "every PC has every definition of its world," they all key
  off `skill_definition_id` directly, so narrowing the seed later needs no
  reader change.

**Named risk, closed in chantier 2.** The base-domain-name collision risk
named above is now closed: both write paths opened by chantier 2 (the
creator-CRUD `POST`/`PUT /api/skill-definitions` and
`entity_author.generate_skill_catalogue_draft`'s normalizer) reject a
`name` that case-insensitively equals a `BASE_SKILL_DOMAINS` literal —
application-side validation, not a CHECK constraint (consistent with the
rest of this module's enum validation, e.g. `base_domain`'s own check).

---

## WORLD-SCOPED CUSTOM SKILL CATALOGUE — authoring + creator CRUD, chantier 2 (BRIEF-56, no schema change)

Closes every deferral chantier 1 (BRIEF-55) named above. Four decisions were
locked before this chantier was written-final (Nia's protocol: no silent
defaults on a deferred design decision):

**D2-attach-b — standalone author call.** `generate_skill_catalogue_draft`
is a standalone sibling to `generate_world_draft`/`generate_player_draft`
(NOT a `_TYPE_FIELDS` entry, NOT folded into the world-bible call) — same
reasoning as those two: independently re-runnable, and `skill_definition`
has no `entity_id` so it was never going to route through
`generate_entity_draft` anyway.

**D2-template-b — dedicated `pt-skill-catalogue` template.**
`usage='skill_catalogue'`, `world_id=NULL`, idempotent upsert via
`seed_pilot.py` — a separate system prompt from `pt-world-generation`,
independently editable.

**D2-delete-cascade, narrowed at the table.** The brief's original
cascade text asked for a `change_history` snapshot of each affected PC
`skill` row before deletion; this was caught as incoherent during planning
— the row being deleted carries the column the snapshot would live in, so
nothing actually survives the delete. Re-decided at the table: the cascade
carries **no separate history snapshot**. Deletion is always possible
(never `ON DELETE RESTRICT`-blocked, honoring "no add-only" — D2-delete-block
would have re-created the soft add-only-after-first-PC pattern Nia
explicitly rejected for this catalogue); the creator-side type-"Oui"
confirmation modal is the sole safeguard, the same idiom and the same
risk profile as world block deletion (`DELETE /api/worlds/{id}`,
BRIEF-54) — both are now named, deliberate exceptions to "History is
sacred" at the row-deletion level (world deletion was already the
sanctioned exception at the world-block level).

**D2-backfill-yes.** `POST /api/skill-definitions` inserts a tier-0
`skill` row for the new definition onto every existing player character of
the world, in the same transaction as the create. Preserves the B1
invariant from chantier 1 ("every PC seeds every world skill") — without
it, an arbiter that selects a newly-added custom skill could find no `skill`
row for a PC created before the definition existed, and the chantier-1
fallback (resolve via `base_domain` when the custom row is absent) would
become load-bearing rather than defensive, which chantier 1 explicitly
did not want.

**Rebase propagates to dependent rows.** `PUT /api/skill-definitions/{id}`,
when `base_domain` changes, also updates the `domain` column on every
`skill` row referencing that definition (`skill_definition_id` match) — so
the 2d6 band lookup, the `domain` CHECK, and the chantier-1 readers all see
a consistent value without a separate migration step. Rename alone touches
no `skill` row (FK-by-id, chantier 1's rename-safety mechanism, holds).

**Scope OUT, unchanged from chantier 1.** No `description` injection into
the arbiter or MJ prompts (prose is CRUD-UI-only, same as before); no
NPC-side custom skills; no per-PC subset selection (B2); no tier authoring
by the model.

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

## DATABASE CARRIER FILE — out-of-tree relocation (incident 2026-06-19)

**Incident.** On 2026-06-19 the live `world_engine.db` (gitignored, at the
repo root) was destroyed out-of-application; the rebuild produced an empty
seed-only world. Read-only recon cleared the code — no boot hook, no
`drop_all`, no file deletion; `create_all` is non-destructive. Most probable
cause: a `git clean -fdx` or manual deletion of the carrier file, since the
file sat inside the git working tree.

**Lesson.** "History is sacred" (see DESIGN CONSTRAINTS CARRIED FORWARD)
protects *rows* — `change_history`, the append-only `ledger`, the reviewed
`proposed_mutation` queue. It says nothing about the *file that carries
those rows*. A workspace-clean operation has no concept of "sacred rows
inside this file" — it only sees an untracked/ignored path inside the tree
and removes it.

**Guardrails put in place:**
1. **`scripts/backup.py`** — resolves the DB path from the live `engine`,
   prints `entities=`/`locations=` counts, and refuses to operate against an
   empty world (catches a silently-rebuilt empty DB before it's trusted).
2. **This relocation (BRIEF-21, schema v1.34)** — `db.py`'s default URL now
   resolves to an absolute `~/.world_engine/world_engine.db`, outside the git
   working tree, so a workspace-clean can never reach it again. The env
   override `WORLD_ENGINE_DATABASE_URL` keeps top precedence — the path is
   never locked. A structural ensure-dir guard (`make_url(...).database` +
   `mkdir(parents=True, exist_ok=True)`, sqlite-only) guarantees the carrier
   directory exists before any connection, removing the manual
   "create the folder first" step from the critical path.
3. **This changelog entry** (schema v1.34) — the doc record of the
   incident and the fix, so the reasoning survives independent of the code.

**Manual relocation runbook** (creator-run, in order — wrong order risks an
empty rebuild):
1. Stop everything (no app, no scripts, nothing holding the DB open).
2. `mkdir -p ~/.world_engine`
3. **Copy** (not move) the good DB to the new path — keep the original as a
   fallback until verified: `cp <repo>/world_engine.db ~/.world_engine/world_engine.db`
4. Apply the `db.py` relocation commit.
5. Verify against the **new** path: run `python scripts/backup.py` — it
   resolves the path from the engine, prints `entities=`/`locations=`, and
   refuses an empty world. Fallback: a raw `SELECT count(*) FROM entity`.
   Expect a non-zero count.
6. Confirm no new `world_engine.db` reappears at the repo root after a
   normal start.
7. Only after 5–6 pass: optionally delete the old repo-root `world_engine.db`.

---

## CRÉATION PAGE CONTRACT (BRIEF-0005-a, no schema change)

RECON-0005 found ten Création sub-tabs (not the seven the ticket assumed),
switched by one hand-maintained dispatcher (`showCreationSubTab`) with
per-tab conditionals, three divergent layout idioms, and a world-switch
reset (`activateWorld`) covering only 4 of ~17 tab-scoped state variables.
Locked pre-brief: **D′2-shell** — a two-level registry (all ten tabs, an
entity archetype now, a bespoke-shell archetype in BRIEF-0005-c), not mere
surface harmonization; **F1** — stay in `index.html`, vanilla JS, no new
dependency; **G1** — a declared per-tab state contract, both
`onTabEnter`/`onWorldSwitch`, closing the reset gap structurally; **H1** —
remove Lieux's duplicate "Ajouter un lieu" button.

**The registry.** `CREATION_TABS` (`index.html`) is the single source of
truth — one entry per tab, ten entries, keyed by the existing tab ids. The
entry contract (verbatim comment above the const):
```
// CREATION_TABS entry contract (TICKET-0005):
// { label:        string, tab title shown in the shell header
//   archetype:    'entity' | 'bespoke'
//   containers:   [element ids to show when active; all others hidden]
//   loader:       function called on activation
//   state:        { onTabEnter: fn|null, onWorldSwitch: fn|null }
//                 each fn resets ALL state this tab owns for that event
//   // entity archetype only:
//   listLoader:   fn (default authorLoadEntityList)
//   listRenderer: fn|null (null = flat list; lieux = renderLieuxBrowse)
//   createPanel:  fn|null (null = no + Nouveau rendered; default =
//                 () => authorRenderSheet({}, true, <type>))
//   slots:        [{ id, containerId, loader, onSelect: fn|null }]
// }
// Every Création page is a registry entry. No page renders outside it.
```
`showCreationSubTab(tab)` is now a pure lookup + generic render over this
data — no tab-id string literal and no per-tab conditional in its body
(enforced structurally by `verify/checks/page_contract.py`, not by
convention). `creationInit()` (the pre-`authorRegistry` bootstrap path) and
`creationNewEntity()` (the `+ Nouveau` handler) were folded onto the same
registry-driven helpers (`_creationActivateTab`, `entry.createPanel`) rather
than left as a second hand-written copy of the same per-tab logic.

**Graph-as-slot posture.** The Lieux graph panel is declared as a `slots`
entry (`{ id: 'graph', containerId: 'creation-lieux-graph', loader:
graphLoad, onSelect: null }`) — the component itself (`graphLoad`/render)
is untouched. This is declarable-now, generalized-only-on-a-second-reader:
no other entity type gets a graph slot in this brief, and none should be
added speculatively — the slot mechanism is the extension point, nothing
more.

**Artefacts is a deliberately degenerate entity entry.** It is tagged
`archetype: 'entity'` for taxonomy (matching BRIEF-0005-c's later note that
"enabling creation = filling `primaryAction`"), but it keeps its own
container (`#creation-artefacts`) and its own `loader`
(`loadCreationArtefacts`) rather than folding into the shared
`creation-editor-area` list+detail shell — `archetype` alone does not imply
shell membership; only `containers.includes('creation-editor-area')` does,
a shape check the dispatcher makes generically for every entry, present or
future. This keeps today's single-column, no-selection Artefacts layout
byte-identical (avoiding a visual regression a full fold would have
introduced — an empty, misleading "select an entity" detail pane with
nothing selectable) while still being a registry citizen with no code
special-casing its tab id anywhere.

**World-switch reset widened, never narrowed (G1).** `activateWorld()` and
`worldDeleteConfirm()` both now call one `_creationRunWorldSwitchResets()`
loop over every entry's `state.onWorldSwitch` in place of the four
hardcoded resets. Coverage was verified live: switching the active world
now also clears `lieuxBrowseParentId`/`lieuxBreadcrumb`/`lieuxActiveOnly`/
`graphData` (lieux), `competencesDraft` (compétences), `regionDraft` and
its siblings (région), `authorFactionRolesDraft` (factions),
`pendingDraftKnowledge`/`pendingDraftNotes` (npc), and
`pcDraftKnowledge`/`skillCharacters` (pj) — RECON's named gap is closed.

**Scope OUT of this brief, carried forward:** PJ's parallel create
machinery (`#pj-create-new-btn`/`#pj-create-block`/`pjCreateOpen`, the
hardcoded `pj` branch in `authorSelectEntity`) — BRIEF-0005-b; the bespoke
tabs' in-body primary action (Compétences' add-row button, Registre's
always-open form, Région's wizard entry, Review Queue's filter/batch band)
— BRIEF-0005-c; any backend change (none — endpoint heterogeneity across
NPC/Lieux/Factions/Objets vs PJ/skill-definition/ledger stays legitimate).

### BRIEF-0005-b — PJ migrates onto the entity archetype (no schema change)

Closes the ticket's motivating divergence and realizes the two decisions
BRIEF-0005-a deferred:

**C1 realized — Fiche as a declared slot.** The pj entry's `slots` now
carries `{ id: 'fiche', containerId: 'creation-pj-skill', loader: skillInit,
onSelect: pjFicheOnSelect }`. `#creation-pj-skill` is no longer a top-level
`containers` entry — it is shown/hidden purely by the generic dispatcher's
slot-container logic, the same mechanism Lieux's graph slot already
exercised in -a. `skillInit()` now runs unconditionally on every pj
activation (dropping the old `if (!skillCharacters) skillInit()` guard) —
one extra background re-fetch of `/api/skills/player-characters` per tab
re-entry, the same unconditional-refresh precedent the graph slot already
set; not a user-visible behavior change.

**E′1 realized — generic `onSelect` hook, not a rewire.** RECON-0005 had
already found that list-click → Fiche wiring was correctly implemented
(`authorSelectEntity`'s hardcoded `pj` branch), just not expressed
generically. `authorSelectEntity(id)` now iterates the active entry's
`slots` and calls each non-null `onSelect(id)` after the detail fetch —
`pjFicheOnSelect(id)` does exactly what the deleted branch did (sync
`#skill-character-select`, call `skillSelectCharacter(id)`). This is a
one-loop generalization, not a new mechanism (event bus, pub/sub — Scope
OUT, unchanged).

**BRIEF-60's gate is superseded, not removed.** The collapsed
`#pj-create-block` + `#pj-create-new-btn` + `pjCreateOpen` toggle is deleted
entirely. `pj.createPanel = pjRenderCreatePanel` renders the identical form
(unchanged fields, unchanged `POST /api/characters/player` submit path)
into `#author-main` — the same detail region every other entity type's
`+ Nouveau` already used, wired through the shared `#creation-new-btn`.
BRIEF-60's visible guarantee (the create form is hidden until the creator
deliberately asks for it; the Fiche renders by default) is preserved
exactly, by the standard mechanism instead of a bespoke one — no second
create affordance exists after this brief; the DB's
`idx_character_one_pc_per_user_world` constraint is untouched.

### BRIEF-0005-c — Standard shell for bespoke Création tabs (no schema change, D′2-shell closed)

Realizes the last locked decision: every Création page — entity or bespoke
— renders under one standard shell, closing the ticket end to end.

**The shell is one shared band, not per-tab markup.** A single
`#creation-shell-band` (`class="panel-head"`, reusing the existing
panel-head look rather than new CSS) sits above every tab body. It shows
`entry.label` as the title and, iff `entry.primaryAction`, exactly one
`#creation-shell-action` button — the same DOM node, same position, for all
ten tabs. `#creation-new-row`'s old markup (the entity archetype's
`+ Nouveau`, previously top-of-sidebar) is retired; `renderCreationShell(
entry)` is called from `_creationActivateTab()` (not `showCreationSubTab`
directly) so the very first Création activation — which reaches
`_creationActivateTab()` through `creationInit()`, bypassing
`showCreationSubTab` entirely — renders the shell too. This was caught live
during this brief: the shell rendered blank on first load until the call
was moved into the shared activation helper.

**`primaryAction` supersedes "`createPanel` presence implies a button."**
`createPanel` still decides WHAT an entity's `+ Nouveau` renders;
`primaryAction: {label, handler} | null` alone now decides WHETHER a button
shows and what it does — decoupled, because a bespoke tab has no
`createPanel` at all but still needs a primary action (Compétences,
Régistre, Région). Every entity entry's `primaryAction.handler` is the
existing `creationNewEntity` (which already gates on `authorRegistry`/
`entry.createPanel`) — one shared reference, not five copies.

**Registre's form is collapsed by default in static markup**, not by an
inline style JS sets on load — `#registre-add-form` carries the native
`hidden` attribute in the HTML, toggled by `registreToggleAddForm()`
(the primaryAction handler) and re-set after a successful
`authorAddLedgerEntry()` append. `POST /api/ledger` itself, and the
append-only posture, are untouched.

**Review Queue's filter bar and batch bar are the one deliberate
non-generic exception**, exactly as scoped: both moved from inside
`#creation-queue` into `#creation-shell-extra` (declared as a `slots` entry,
`{ containerId: 'creation-shell-extra', loader: null }` — reusing the
existing generic slot-container show/hide, not a new "shell API"). The
static filter buttons never regenerate; `loadQueue()`'s only change is
where it mounts `renderBatchBar()`'s output. No other entry uses this slot;
none should without a deliberate decision, per Scope OUT.

**Deferred: a `catalogue` archetype.** Compétences and Registre both render
an inline-editable/read-only table body; a shared archetype for that shape
is explicitly not built here (Scope OUT). Trigger to revisit: a third
table-shaped Création page appears.

## Deferred decisions

Recorded here so each is revisited deliberately rather than forgotten:

- **Coup-de-grâce exception to the unconsciousness ceiling** (`neutralized` +
  `frozen`). Deferred: the frozen-scene checkpoint already blocks further
  action; a kill path would need a deliberate creator-level gate and is not
  scoped.
- **Generic non-conversation `scene_state`** (investigation, fire, chase
  scenes outside a conversation). Resolved at the conversation level (BRIEF-12,
  v1.24); a conversation-spanning or world-level state table remains deferred.
- **Every-N-turns fallback cadence for long scenes** (window analysis,
  BRIEF-09). Deferred because scene-boundary triggers (close, location
  transition, gathering dissolution) plus the manual button were judged
  sufficient for v1; revisit only if live testing shows scenes running long
  enough that unanalyzed turns accumulate noticeably between boundaries.
- **Code-level relation-amplitude threshold (D2 guard)** (window analysis,
  BRIEF-09). Deferred pending live-test results of the
  `pt-conversation-analysis` v3 anti-inflation rubric — add a code-side cap
  only if the prompt-level rubric proves insufficient in practice.
- **Per-item `entity_a`/`entity_b` resolution against the gathering roster**
  for multi-NPC windows (window analysis, BRIEF-09). Today an unresolvable
  `relation_change` is skipped and logged (`_normalize_to_schema`, see
  "CONVERSATION ANALYSIS — Window analysis" above) rather than attributed to a
  default NPC. If live testing in multi-NPC scenes shows the model frequently
  omits `entity_a_id`/`entity_b_id`, a follow-up step should resolve them
  per-item against the gathering membership (candidate set = present roster)
  — separate change, separate commit.
- **Player knowledge acquisition and organization.** How the player character
  accumulates and structures what they know is an open design question. The
  current `knows` ceiling on `analyze_overhearing` (see "Deterministic level
  ladder" above) is a v1 testing safeguard, not a settled invariant — do not
  harden a code-level `knows` cap on `analyze_window`'s `knowledge_change`
  path until this is decided; doing so would lock in a choice that is
  deliberately still open.
- **Skill sheet consumers, remainder** (physical layer, post-BRIEF-12).
  `ResponseMode.physical` + `resolve_physical` read the skill sheet (v1.23);
  `scene_state` constraints + condition ladder implemented (v1.24) — still
  deferred: `skill_change` mutation type and automatic progression (tiers stay
  creator-edit only); passive perception checks; richer scene-entry description
  (MJ establishing what a character with a given perception tier notices).
- **NPC↔NPC physical dice** (BRIEF-11). When Tier-3 initiative produces an
  NPC-vs-NPC physical act, the MJ narrates by tier comparison — no roll,
  nothing implemented this step. Accepted design: the player-roll rule means
  the resolution machinery (`_arbitrate`, `resolve_physical`) is wired only to
  player-initiated or player-responding turns; an NPC↔NPC roll would need its
  own (still hypothetical) trigger and is not scoped.
- **Passive perception on location entry** (BRIEF-13) — **resolved by
  BRIEF-17** (schema v1.30, "Signpost layer — perceptible entry cues" above).
  `access_level='ambient'` is now read by `active_signposts` (code predicate,
  never an assembler) and narrated via a new MJ establishment call in
  `enter_scene`.
- **`discovery_threshold` activation** (BRIEF-13) — **resolved by BRIEF-23**
  (N1, schema v1.35): the column is now compared against `verdict.total` as a
  fourth `.where()` clause at selection in `_stream()`.
- **NPC opposition to a search** (BRIEF-13). A search always resolves at
  `npc_tier=0`; the future "a named NPC intervenes to block or hide information"
  (opposition to a perception roll) is deferred. Do not read co-present NPCs
  into the search roll; do not add an opposed-search path this step.
- **Per-character discovery state** (BRIEF-13). `discovered` is a single
  world-level bool (`discoverable_detail.discovered`) — suitable for the solo
  pilot. Multiplayer per-player discovery (each player character has their own
  `discovered` flag) requires a join table or a `player_discoveries` column and
  is explicitly deferred.
- **One-directional knowledge-leg dedup gap** (ECONOMY, schema v1.32,
  BRIEF-19). Guard 4c (`_knowledge_leg_already_applied`) scans both applied
  `new_knowledge` rows and applied `resource_change` knowledge legs, but the
  `new_knowledge` branch's own `_find_applied_duplicate` is NOT extended to
  scan `resource_change` legs. If a `resource_change` knowledge leg applies
  FIRST, a later colliding `new_knowledge` (same conversation/entity/subject
  — e.g. from `analyze_overhearing`) is not blocked, producing two knowledge
  rows. Narrow: requires the player to *sell* information to an NPC who, in
  the same turn, also overhears that subject (the player is excluded from
  overhearing receivers, so a player *purchase* is never affected).
  Accepted for the pilot — caught by creator review at the checkpoint; to be
  closed only if live play shows it occurring.
- **Tracked NPC purses / full double-entry** (ECONOMY, A2/A3, schema v1.31).
  Today only the player-relevant single line is written per transaction
  (decision A1); giving NPCs their own auditable balance is a later step, if
  ever needed.
- **Explicit favors / `resource_type` column** (ECONOMY, schema v1.31).
  Favors stay an implicit `relation` delta. Re-adding a `resource_type`
  column to `ledger` later (to make favor-currency trackable like money) is a
  zero-migration `ALTER … DEFAULT 'currency'` — deliberately not built now.
- **Ledger-as-pricing-dataset** (ECONOMY, schema v1.31, reaffirmed v1.33).
  Querying historical `ledger` lines to inform AI pricing decisions needs the
  ledger to actually have lines first — still deferred post-BRIEF-20.
- **Haggling / negotiation, relation-modulated catalogue prices, structured
  pricing call, Claude-routed high-stakes quotes, price→entity linkage,
  automatic price evolution, NPC purchasing/inventories, per-world currency
  display name** (ECONOMY, schema v1.33, BRIEF-20). `price_list` itself and
  its AI-improvised-quote rubric are now built (see "Pricing — permanent
  catalogue vs unique quote" above); these surrounding refinements remain
  deliberately out of scope.

- **Active world is a single global flag, per-session selection deferred**
  (BRIEF-43, schema v1.54). `world.is_active` is one flag for the whole
  database, chosen by the creator via the cockpit selector — appropriate for
  solo, single-creator use. Multiplayer's eventual "each session picks its
  own world" is a named, not foreclosed, future direction: the global flag
  is additive (a per-session override could read it as a fallback) and
  requires no migration away from it. This step is also the hard
  prerequisite for A1 (several worlds in one database) — until a creator
  explicitly activates one, `_world_id()` refuses to guess.
- **Converging `activate_world`/`create_world` onto `_activate_world_core`**
  (BRIEF-54, E1). The deactivate-all → flush → activate-one logic now exists
  three times (`activate_world`, `create_world`'s auto-activation step, and
  `_activate_world_core`, all `app.py`). BRIEF-54 deliberately added the
  third copy rather than rewiring the first two onto it, to keep a
  delete-only brief from also touching the activate/create routes. Revisit
  as a named, separate cleanup if a fourth caller ever needs the same logic.

---

*Co-built with Claude, June 2026.*
