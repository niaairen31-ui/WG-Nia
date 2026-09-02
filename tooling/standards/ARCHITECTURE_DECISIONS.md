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
| `knowledge_change` | Find the `knowledge` row by `entity_id` + `subject` (never creates — that's `new_knowledge`'s job); call `write_knowledge(mode="level_change", knowledge_id=row.id, level=to_level, source=..., changed_by="apply_mutation")` (BRIEF-0003-a) — appends the previous state to `change_history`, updates `level`, `source`, `updated_at`, leaves `content`/`is_incorrect`/`is_secret`/`share_threshold`/`subject` untouched. Guards: row not found → "Needs attention" (`knowledge row not found`); current `level` >= `to_level` (monotone re-check at apply time) → "Needs attention" (`level already >= proposed`). |

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

## DOCUMENTATION PARTITION — hot/cold split, generated index, mechanical numbering (BRIEF-0001-a, BRIEF-0001-b, no schema change)

`world-engine-schema.md` mixed hot truth with a 1,200-line cold history, and
`ARCHITECTURE_DECISIONS.md` had no cheap lookup surface — every reader paid
for the whole document to use 5% of it. This record locks the split and the
numbering scheme that came with it.

- **A1** — extract the `CHANGELOG` section of `world-engine-schema.md` into
  `world-engine-schema-changelog.md`, moved byte-for-byte: separates cold
  history from the hot TABLES/INDEXES/RELATIONS/MIGRATION truth.
- **A1-guard** — the current schema version stays a single header line
  (`Current schema version: vX.YY`) in `world-engine-schema.md`; the
  changelog file is the append-only log, never the source of "what version
  are we at" — one place asserts the current number, not three.
- **N1** — the new file is named `world-engine-schema-changelog.md` at repo
  root, deliberately distinct from the pre-existing, unrelated
  `CHANGELOG.md` (a French application-level changelog) so the two are
  never confused or merged.
- **B1** — `DECISIONS_INDEX.md` is a mechanically generated index (one row
  per `## ` record: line, title, BRIEF refs, schema versions); the archive
  stays byte-for-byte intact, and a verify check proves index ≡ headers so
  the two can never silently drift apart.
- **G1 / G3-b** — the index generator is tolerant of the archive's real
  header shapes (RECON-0002 found 20/47 deviate from the nominal pattern in
  three distinct ways) rather than dropping or mis-parsing them; a strict
  header regex gates only headers added AFTER a frozen baseline snapshot,
  so future drift is stopped without rewriting the past.
- **U1** — ticket/recon/brief numbering becomes a computed 4-digit counter
  (`tooling/glue/next_id.py`, max existing ID + 1) instead of a
  human-chosen number.
- **V1** — schema version numbers are likewise computed, never chosen: new
  version = the header line's minor + 1.
- **U-now** — the computed-numbering regime takes effect now, for new IDs
  only: legacy two-digit `BRIEF-NN` filenames are a closed, grandfathered
  namespace, never renumbered or reused.

---

## CANON-WRITE DOCTRINE — table classification, write normalization, structural gate (BRIEF-0003-a, BRIEF-0003-b, no schema change)

RECON-0003 mapped every write site in `src/`; this record locks the
classification and enforcement that followed.

**K1 — three-strata table classification.** Every table in
`world-engine-schema.md` falls into exactly one stratum:
- **Canon** (15 tables, listed verbatim in
  `tooling/verify/canon_write_policy.txt`'s `[CANON_TABLES]`): `world`,
  `entity`, `character`, `location`, `faction`, `faction_membership`,
  `relation`, `knowledge`, `ledger`, `item`, `skill`, `skill_definition`,
  `discoverable_detail`, `event`, `artifact`. These are the tables the "two
  sanctioned canon-write paths" doctrine actually governs.
- **Ephemeral** (session/play machinery, never a `proposed_mutation`, never
  creator-CRUD-reviewed): `gathering`, `gathering_member`, `conversation`,
  `conversation_message`, `session`, `batch`, `pass_play`.
- **Pipeline-internal** (the mutation/config plumbing itself, not narrative
  canon): `proposed_mutation`, `user`, `prompt_template`.

Ephemeral and pipeline tables carry no `canon_write_policy.txt` entries at
all — a write to one is invisible to the check by construction, not by an
allowlist exemption.

**M1 — one table, one write shape (`knowledge`).** `_apply_mutation`'s
`knowledge_change` branch (`cockpit/app.py`) no longer bypasses
`write_knowledge` to call the private `_append_knowledge_history` directly;
it calls `write_knowledge(mode="level_change", ...)` (writes.py), which
reproduces the prior hand-rolled semantics byte-for-byte (same
`change_history` entry shape). `_append_knowledge_history` now has exactly
one caller: `write_knowledge` itself.

**W1 — one table, one write shape (`skill`).** `cockpit/crud.py`'s
`update_skill_tier` no longer hand-rolls the `skill.change_history` append;
it calls the new `write_skill_tier` (writes.py), the sole write shape for
`skill` tier changes.

**L1 — the three unnamed hard-deletes become a named, closed list.**
RECON-0003 C2 found three hard-delete routes in `cockpit/crud.py`
(`delete_relation`, `delete_knowledge`, `delete_discoverable_detail`)
existing outside `writes.py`, unnamed in CLAUDE.md's Invariants section
despite that section's own sentence ("No other delete-side helper exists;
any new hard-delete path must be named here, not added silently"). CLAUDE.md
now names all three explicitly, immediately after that sentence — see
"Named creator-correction hard-deletes (closed list, BRIEF-0003-b)" in
Invariants. **Soft-archival of these three deletes (converting them to a
status flag instead of a hard `DELETE`) was considered and explicitly
deferred, not rejected** — see "Deferred decisions" below; L1 only names the
existing behavior, it does not change it. The list is closed and enforced
structurally: `verify/checks/single_canon_write.py` treats any hard-delete
site on a canon table as a policy violation unless its `path::function` is
in `canon_write_policy.txt`, so a fourth hard-delete added anywhere else
fails `/verify` on sight, naming file, function, and table.

**T1 — static AST scan, `src/`-scoped, function-grain allowlist.**
`tooling/verify/checks/single_canon_write.py` (stdlib `ast` only, no DB)
walks every `.py` under `src/`, attributes every `.add()`/`.delete()` call on
a `Session`-typed receiver — and every raw-SQL `.execute()`/`.exec()` call —
to the table it writes, and fails if a CANON-table write's `path::function`
is not listed in `canon_write_policy.txt`'s `[ALLOWED_SITES]`. Attribution
is function-grain (a call inside `write_relation` is legal because
`write_relation` itself is allowlisted — the check never asks whether
`write_relation`'s *caller* was also allowed to call it) and purely
lexical: a call made by a function the scanned function calls is not
attributed to the scanned function, matching how the two sanctioned paths
actually compose (`_apply_mutation` and creator CRUD delegate to
`writes.py`, they do not inline its writes). A canon-table site that cannot
be attributed to any table at all is always a failure (`unattributable
write site`) — RECON-0003 D1 confirmed zero dynamic-dispatch write sites
exist in `src/` today, so an unattributable site is new and must be made
legible before merging, not silently allowed through. `scripts/` and every
`migrate_v1_*.py` are out of scope **by construction** (the scan never walks
outside `src/`), not by an allowlist carve-out — none of them is a live
request-serving path.

### CANON STRATUM EXTENSION (TICKET-0026)

`npc_price`, `location_subculture`, `world_law` join the canon stratum,
allowlisted at their `writes.py` chokepoints. The authoritative canon
enumeration is `canon_write_policy.txt`'s `[CANON_TABLES]`, not the frozen
"15 tables" figure in the K1 record above — that figure predates
`faction_role`, `npc_goal`, `agenda`, `agenda_step`, `goal_agenda_link`, and
now these three. Read K1's count as illustrative-at-time-of-writing; the
policy file is the single source of truth.

---

## PIPELINE GLUE — /pipeline orchestration, derived ticket status, structural permissions (BRIEF-0004, no schema change)

TICKET-0004's intake clarifications, locked; BRIEF-0004 built `/pipeline`
against them unchanged.

- **P1** — `/pipeline` covers only the Claude Code segment: ticket + brief
  present -> exec -> verify -> retry -> PR or escalate. Intake and brief
  authoring stay in chat; the file contract (a brief deposited under
  `tooling/briefs/`) is the boundary, so future automation of the deposit
  gesture needs no glue change.
- **Q1** — a single command, `/pipeline TICKET-NNNN`, idempotent and
  resumable.
- **SM1 (transition ownership)** — Nia owns `intake->recon`,
  `recon->brief`, `brief->exec` (brief deposit is the green light), and
  `live-gate->done` (merge). `/pipeline` owns `exec->verify`,
  `verify->live-gate` (green), `->escalated` (D1), `->paused` (clean
  interruption). `/pipeline` never performs a Nia-owned transition.
- **V1** — first red `/verify`: one confined fix attempt (the executed
  brief's Scope IN only), `retry_count` incremented, re-verify. Second
  consecutive red -> `escalated` + a QUESTION file citing both verdicts
  (D1-d, literal).
- **QF1** — `tooling/questions/QUESTION-TICKET-NNNN.md`, fixed sections
  (Trigger a/b/c/d, Context, exactly one Question, lettered Options,
  empty `## Response` for Nia). A filled `## Response` on relaunch resumes
  the chain; an empty one stops it again. The file persists after
  resolution — an append-only trace, never deleted.
- **PR1** — a green verify opens the PR (`gh pr create`, body: ticket id,
  brief id(s), the verdict JSON inline), sets `status: live-gate`. Nia
  plays and merges on GitHub; C1 stands untouched (`/pipeline` never
  pushes or merges to `main`; `block-main-push` remains the net).
- **SES1** — one invocation chains to the next human gate (exec then
  verify in the same session, when context allows); a clean interruption
  sets `status: paused`, resumable by a later invocation.
- **CA1** — the commit-approval wait moves to the PR surface: `/pipeline`
  states explicitly when it invokes `/review-step`/`/close-step`
  unattended, and `close-step` skips its wait in that mode only — Nia's
  approval gate becomes the PR review itself, not a per-commit prompt.
- **NT2** — `status` is a derived fact, never hand-written: Step 0
  reconciles it from observable facts (merge state, verdict JSON, PR
  existence, QUESTION files, brief files on disk) on every invocation.
  This amends SM1's literal wording — Nia owns the *acts* (deposits,
  merges); `/pipeline` owns *recording their consequences* as `status`,
  not the acts themselves.
- **GT-A** — `tooling/tickets|recon|briefs/` were gitignored in the
  working tree, hiding BRIEF-0003-a/-b and RECON-0003/-0004 from `git
  status` and from any commit. Reverted: the exclusion is gone, all
  pipeline artifacts are tracked. Provenance — a brief's citation of its
  RECON must be checkable in history, not just present on disk today.
- **GH1** — `.claude/settings.json` gains a narrow, nominative
  `permissions.allow` list (exactly `gh pr create`, `git push origin
  ticket/*`, `tooling/glue/*` scripts, `python -m tooling.verify.run`,
  and the two read-only git families `git branch`/`git log`) — the
  structural declaration of what the chain may do unattended. No generic
  `Bash(*)` entry exists; `block-main-push`/`block-db-in-git` are
  untouched.
- **H1** — no backup hook is added (F2 stands: backup.py stays a manual,
  deliberate step). Destructive/irreversible operations escalate through
  D1-b instead — the QUESTION file is the net, not an automatic snapshot.

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

### sheetRenderer seam (TICKET-0021, A1, no schema change)

Intrigues (agendas — `agenda`/`agenda_step`/`goal_agenda_link`, not `entity`
rows) is the SECOND concrete non-entity reader of the shared list+detail
shell (Lieux's `renderLieuxBrowse` being the first, for the list pane only).
By minimal-first this finally justifies generalizing the one hardcoded
piece of the shell: the detail-pane renderer.

**The seam.** The entity-archetype-only section of the `CREATION_TABS`
entry contract gains `sheetRenderer: fn|null` (null = `authorRenderSheet`).
`authorSelectEntity(id)` — the entity fetch/shape path — and the new
`creationSelectRecord(tabId, record)` — for tabs whose rows already carry
full data, no per-row fetch — both resolve `(entry.sheetRenderer ||
authorRenderSheet)` before rendering: one renderer seam, two data shapes,
no second dispatcher. Every existing entity tab leaves `sheetRenderer`
absent, so `authorRenderSheet` still runs unchanged for all of them — zero
behavior change.

**Intrigues becomes a registry entity entry.** `archetype: 'entity'`,
`containers: ['creation-editor-area']`, `listLoader: loadAgendasList`,
`listRenderer: renderIntriguesListRows`, `sheetRenderer: renderAgendaSheet`,
`createPanel: intriguesRenderCreatePanel`. It deliberately has no `type` —
`listLoader` fully replaces the default `authorLoadEntityList`, and the two
existing `entry.type` dereferences (`creationRenderEntityList`,
`loadPendingCreations`) were already presence-guarded before this brief
(short-circuited by `listRenderer`, and `!entry.type`, respectively) — no
new guard needed. The bespoke `#creation-intrigues` container, its
collapsible add-form, and `loadIntrigues`/`intriguesToggleAddForm`/
`_intriguesRenderList` are retired; the create form moves into the shared
detail pane (the PJ/NPC idiom) via `intriguesRenderCreatePanel`, keeping
its element ids unchanged so `intriguesSubmitCreate` needed no rewrite
beyond its post-success tail.

**Selection state, not just render.** `creationSelectedRecordId` is the
`authorEntityId` counterpart for `sheetRenderer` tabs — one shared variable
is sufficient since only one such tab is ever visible at a time. Every
agenda-mutating action (status transition, step transition, link detach)
re-fetches the list and re-renders the sheet for the same agenda id via
`creationSelectRecord`, keeping selection through fresh data — the same
guarantee `authorSave`'s post-save re-render already gave entity tabs.

**A3 stays deferred.** Full data-source abstraction of the shell (folding
Compétences/Registre/Région/Review Queue/Artefacts onto it) is not
attempted here — `sheetRenderer` is the whole generalization this ticket
makes. Reactivate A3 only on a third concrete case needing it.

---

## PIPELINE COCKPIT — deposit surface, question writer, structural boundaries (BRIEF-0006-a, no schema change)

TICKET-0006 second pipeline pass. RECON-0006 confirmed no naming/port/
template/loader collision with the world cockpit (findings 1-4), that
`next_id.py` was CLI-print-only (finding 6), and that no QUESTION file had
ever existed, so nothing enforced its append-only contract (findings 13-15).

**H1 (collision-audited separation).** `tooling/pipeline_cockpit/` is a
separate FastAPI app — its own package, its own port (8100, distinct from
the world cockpit's 8000), its own `index.html` served as a raw string
(mirrors `src/world_engine/cockpit/app.py`'s `_INDEX_HTML` pattern — no
Jinja, no `StaticFiles`, no new dependency). Launched on demand via
`scripts/pipeline_cockpit.py`, structurally parallel to `scripts/cockpit.py`.

**I1 (cockpit v1 scope, I2 deferred).** Exactly two surfaces: "Soumettre"
(paste an artifact; type detected from body shape; number assigned at
deposit; file written; confirmation displays the created name — widened,
never narrowed, by BRIEF-0007's upload channel, a converging second input
mode on the same surface) and
"Questions" (list open QUESTION files, answer inline). No git operation, no
status board, no `/pipeline` launcher button. **I2, deferred**: a read-only
ticket status board — add only when live usage shows the need.

**J2 (cockpit assigns numbers).** Chat delivers artifacts with `NNNN`
placeholders; `tooling/pipeline_cockpit/deposit.py`'s `assign_number`
resolves the number at deposit time via `compute_next_id()` (tickets) or the
page's `bound_ticket` state (recon/briefs carrying the placeholder) and
substitutes it everywhere in the body. The disk at deposit time is the only
authority — GitHub lags the working tree, so there is no race window.

**K1 (import boundary, structural).** Nothing under `tooling/pipeline_cockpit/`
imports from `src/world_engine/` — enforced by an `ast`-based scan in
`tooling/verify/checks/pipeline_cockpit.py`, not by convention.

**L1 (`next_id.py` extraction).** `compute_next_id() -> str` now holds the
counting logic; `main()` is a thin `print(compute_next_id())` wrapper.
CLI behavior is byte-identical; the cockpit imports the same function — one
counter authority for both callers.

**N1 (QUESTION writer, writer half).** `tooling/glue/question_response.py`
is the single QUESTION writer: `is_open()` is the one machine definition of
"empty `## Response`" (stripped section content `== ""`); `write_response()`
raises `ResponseAlreadyFilled` on a non-empty section and `MalformedQuestion`
on a missing header, and never touches anything above the `## Response`
header. Both the cockpit's Questions route and the inline in-session
escalation flow (BRIEF-0006-b) call this one writer — no second writer
exists anywhere.

**P1 (producer contract, documented).** See CLAUDE.md's "Artifact producer
contract" bullet: every chat-produced artifact embeds a machine-readable
slug; type is detected from body shape, never H1 prose (RECON-0006 finding
20: the real population's H1 text is inconsistent across all three types).

## PIPELINE SECOND PASS — recon absorption, CA1 relay, inline escalation, bounded conflict resolution (BRIEF-0006-b, no schema change)

TICKET-0006, second half. RECON-0006 located every gap precisely: Step 1's
`recon` branch stopped instead of executing (finding 9); the only push in
the whole command surface was Step 3's end-of-ticket push, so nothing was
raw-URL-readable before the full brief chain completed (findings 10, 22);
the CA1 unattended clause was written at the `/pipeline`↔`/close-step`
boundary but the real call path goes through `/brief-exec`, which carried
zero wiring for it (finding 12); PR mergeability was never checked and
0005's conflict was resolved 100% manually (finding 16); the two
append-only files grow in opposite directions (finding 17).

**C1 (recon absorbed by `/pipeline`, as amended).** `.claude/commands/
pipeline.md` Step 1's `recon` branch now executes the recon protocol
in-session (reusing `.claude/commands/recon.md` verbatim as the payload),
creates `ticket/NNNN` from `main` if needed, commits and pushes the result
on `ticket/NNNN` — the first-ever early push point, before any brief
exists — then stops (the brief phase stays chat-side, P1 unchanged). A
ticket with no recon spec on disk is not an error: the recon phase is
inapplicable by construction and status derivation already proceeds past
it (rule 7's `intake` fallback). Recon itself (`/recon.md`) is untouched
and remains available standalone for ad-hoc use.

**M1 (the CA1 relay).** RECON-0006 traced the actual deviation observed on
TICKET-0005: `/pipeline` never invokes `/review-step`/`/close-step`
directly — it invokes `/brief-exec` once per brief, and `brief-exec.md`
carried zero CA1 wiring, so the unattended flag depended on the executing
session remembering to restate it at that inner call site. `brief-exec.md`
step 3 now carries its own explicit relay clause: if invoked from
`/pipeline`, it invokes `/review-step`/`/close-step` in unattended mode
and states so explicitly at each invocation — the chain a→b→...→verify now
runs with zero manual `/close-step` gaps between briefs of the same
ticket, mechanically, not by convention.

**N1 (invoker half + no-early-push corollary).** The inline escalation
flow and the pipeline cockpit's Questions surface (BRIEF-0006-a) are the
only two writers of a QUESTION file's `## Response`, both going through
`question_response.py:write_response` — no direct edit anywhere. "Empty
`## Response`" is defined by `question_response.py:is_open`, not prose. A
QUESTION file is committed on `ticket/NNNN` when written (append-only
trace) but is deliberately never pushed early — chat never reads QUESTION
files (the cockpit reads the local tree), so there is no raw-URL reason to
push one ahead of the ticket's normal push points.

**O1 (PR-conflict resolution is bounded, never semantic).** The new
PR-conflict procedure (`pipeline.md`, "PR-conflict procedure (F1/O1)")
only ever auto-resolves a CONFLICTING PR whose conflicted paths are
entirely append-only docs (`ARCHITECTURE_DECISIONS.md`, keep-both,
main's sections first) followed by a full re-verify and re-push. Any
conflicted path under `src/`, or either schema-carrying file
(`world-engine-schema.md`, `world-engine-schema-changelog.md`), aborts the
merge and escalates via D1 with the conflicted paths cited — the machine
never resolves a semantic or version-numbering conflict. This codifies
exactly the manual resolution that succeeded on TICKET-0005.

**Q1 (permission additions, flagged read-only extensions).**
`.claude/settings.json`'s `permissions.allow` gained exactly seven entries
needed by the above: `git fetch origin`, `git merge origin/main`,
`git merge --abort`, `git diff`, `git status`, `gh pr view`, `gh pr list`.
No generic `Bash(*)`; `block-main-push` and `block-db-in-git` untouched.

## SOUMETTRE FILE UPLOAD — per-channel detection authority (BRIEF-0007, no schema change)

TICKET-0007. Nia wants to upload the delivered `.md` files directly
instead of pasting their body.

**A1 (converging adapter, no second logic).** An upload zone
(`<input type="file" multiple accept=".md">`) sits next to the existing
textarea in the Soumettre surface; both feed the same downstream write
logic (`deposit.target_path`, `TargetExists` unchanged). `target_path`
gained an optional `brief_suffix` parameter (paste channel omits it and
keeps its existing body-H1 scan; upload channel supplies it directly) so
the one shared path-building/existence-check function serves both
channels without duplication.

**B2 (filename is the authority, upload channel only).** `deposit.
parse_filename` parses `(TICKET|RECON|BRIEF)-(0007|NNNN digits)
(-[a-z])?-(slug).md` from the filename alone — body shape is never
consulted on this path. The suffix segment is legal only for BRIEF; its
presence elsewhere refuses the file (`UnparseableFilename`), never a
silent fallback to `detect_type`/`extract_slug` (the paste channel's
unchanged authority). The literal digit string `"0007"` is this
channel's numeric placeholder (a 4-digit stand-in for the paste
channel's `"NNNN"`, since the filename grammar's number slot is
digits-only) — a number segment equal to it resolves to `None`
(bound at deposit time), for every artifact type, not just TICKET;
any other 4-digit number is concrete and used as-is. (TICKET-0007's own
intake example collided "0007-as-placeholder" with "0007-as-this-
ticket's-real-number"; the implemented rule is the literal, type-uniform
one stated above — the ticket text was corrected to a non-colliding
example accordingly.)

**C1 (ordered multi-file upload).** `deposit.order_upload_batch` sorts a
submitted batch so ticket-typed filenames process first (submitted order
preserved within each group); `resolve_upload_number` gives a ticket a
fresh `compute_next_id()` (ignoring whatever was in its filename) and
binds every placeholder-numbered non-ticket in the same batch to that
result via a request-local `bound_ticket`, refusing (`MissingBoundTicket`)
if none is available. A refusal is per file: one bad name writes nothing
for that file and does not block its siblings.

**No new dependency (forced substitution).** `POST /api/upload` accepts
JSON with base64-encoded file contents rather than `multipart/form-data`
— FastAPI's `UploadFile`/`File`/`Form` require `python-multipart`, which
is not installed and would be a new dependency, explicitly ruled out by
this brief's scope. The browser still uses a native `<input
type="file">`; only the wire format differs. Server-side, the payload is
base64-decoded then UTF-8-decoded explicitly, so an invalid encoding
still refuses the same way a direct multipart read would have.

## PROMPT MODEL COLUMN + REGISTRY (BRIEF-0008-a, schema v1.67)

TICKET-0008, first half — the plumbing the read-only Prompts tab
(BRIEF-0008-b) will display. RECON-0008 corrected the spec on two points
material to this brief: the "world-preferred-else-global" resolution chain
is NOT uniform across all 16 template loaders (6 authoring loaders —
`entity_author.py` ×4, `region_author.py` ×2 — take no `world_id` at all
and filter only `is_active`); and the seeded usage count is 17, with
`region_manifest_topup` a ninth omission from the schema-doc enum comment
(now fixed alongside the other 8).

**A2-a2 (nullable authoritative `model` column).** `prompt_template.model
TEXT NULL`. NULL = code decides (the caller's existing default); non-NULL =
creator override. `prompt_registry.effective_model(template, default)` is
the resolver every templated model call routes through — a day-one reader,
not just future display. With `model` NULL everywhere (guaranteed: no write
path exists, seed untouched), every call site resolves to exactly the model
it used before this brief.

**A2-b (full creator model authority, no structural locks).** Any Ollama
model is selectable for any prompt, play or authoring, once a write path
ships. Consequence, explicitly accepted: `region_manifest_topup`'s
documented "hard requirement — never the game model" (BRIEF-40) downgrades
to a *default* — `AUTHOR_MODEL` remains what the topup call uses absent an
override, but nothing in the code prevents a creator from overriding it to
the game model. This downgrade is recorded now, becomes ACTIVE only when a
write path ships (Scope OUT of this brief).

**A2-c (code registry for code facts).** `prompt_registry.py` declares, per
usage: `surface` (play|authoring), `world_scoped` (R1, below),
`dry_run_capable` (C3, consumed by BRIEF-0008-b), `default_model` (a
zero-argument callable resolved at read time from `ollama_client.
DEFAULT_MODEL` / `entity_author.AUTHOR_MODEL` — never a copied string
literal, so a `WORLD_ENGINE_OLLAMA_MODEL` env override shows through), and
`call_sites` (`"path:function"`, B1 — the static loader function per
usage). The DB owns prompt text + the `model` override; code owns wiring.
`prompt_registry.py` imports `entity_author.AUTHOR_MODEL` lazily (inside
`_author_model()`, not at module load) because `entity_author.py` imports
`effective_model` from `prompt_registry` — a top-level import the other
way would cycle.

**R1 (`world_scoped` encodes each usage's REAL resolution semantics).**
Per RECON result F1's correction: `world_scoped=True` for the 9 cockpit/
gathering usages (`npc_dialogue`, `player_narration`, `mj_interpretation`,
`mj_arbitration`, `mj_establishment`, `mj_gathering`, `mj_speaker_
selection`, `mj_initiative`, `npc_initiative_act`) plus `conversation_
analysis`/`overhearing_classification` (the analyzer's generic loader is
world-preferred-else-global); `world_scoped=False` for the 6 authoring
usages (`entity_generation`, `world_generation`, `player_generation`,
`skill_catalogue`, `region_manifest`, `region_manifest_topup`), which take
no `world_id` and resolve `.first()` over active rows only. The registry
matches the actual loader bodies, not an idealized uniform chain.

**Wiring scope + the injected-context exemption.** All 4 `entity_author.py`
chat calls, both `region_author.py` calls, both `analyzer.py` calls, and
`gathering.py`'s one call now read `model=effective_model(template,
<existing default>)`. In `cockpit/app.py`, the resolver is wired at the
three points where a fresh `model = ollama_client.DEFAULT_MODEL` binding
sits next to its driving `PromptTemplate` — conversation start
(`start_conversation`), and `scene_join`'s two branches (existing-gathering
resume, and the interpret-then-resolve path) — plus the standalone
`_build_establishment_narration` inline call. Deliberately NOT wired:
`app.py:2607`'s `model = injected.get("model", ollama_client.DEFAULT_
MODEL)` (the `/say` turn's model, already resolved once at conversation
start) and everything downstream of it in the same call path — `say`'s
nested `_stream()` closure and the pass-through helpers it calls
(`_interpret_mode`, `_arbitrate`, `_npc_initiative_vote`, `_select_group_
speaker`), all of which consume that single already-resolved value via
their own `model: str` parameter rather than a `PromptTemplate` object.
Wiring it would silently encode a `template.model` vs `injected_context
["model"]` precedence — deferred to the write-path chantier. `verify/
checks/prompt_registry.py`'s static wiring scan allowlists these five
functions by name, with a comment naming the deferral.

## PROMPTS TAB — read-only reader, API, dry-run previews (BRIEF-0008-b, no schema change)

TICKET-0008, second half — the reader that justifies -a's registry structure.
A read-only cockpit tab: `GET /api/prompts` (master list, grouped by usage,
lazy — no template bodies in the list payload), `GET /api/prompts/{id}`
(full detail on demand, D1), and two assembled dry-run preview endpoints
(C3).

**Effective-row resolution replicated, not idealized.** `crud.py`'s
`_effective_prompt_row(rows, world_scoped, world_id)` mirrors the REAL
loader bodies exactly per R1: the world-preferred-else-global chain for
`world_scoped=True` usages, bare "first active row" for the 6
`world_scoped=False` authoring usages — including their latent
non-determinism with 2+ active rows, deliberately not fixed here (an
accepted observation, not a bug this brief owns).

**Fidelity rule, applied.** The two assembled previews
(`GET /api/prompts/preview/npc_dialogue`, `GET /api/prompts/preview/
player_narration`, both in `app.py` — same no-canon-write neighborhood as
`POST /api/entities/generate`, deliberately not in `crud.py`) call the REAL
`assemble_npc_context`/`assemble_mj_context` — never a reimplementation.
The npc_dialogue system-prompt concatenation (`f"{behaviour.system_prompt}
\n\n{context}"`) was inline and duplicated across 4 call sites
(`start_conversation`, `_stream`'s two responder branches, the NPC
initiative act) before this brief; extracted into
`_npc_dialogue_system_prompt(behaviour, context)`, now the single
construction all 4 live sites AND the preview call — behavior-preserving,
byte-identical output, no reordering. Live verification surfaced a
pre-existing, unrelated bug in `assemble_npc_context` (a location whose
`subculture.values` is a list, not a string, crashes `" ".join(setting_
lines)`) on several of Verkhaal's NPCs — left untouched: the preview's job
is to show exactly what the live path would build, bugs included; fixing
an assembler bug is a separate, unscoped concern.

**`destination` omitted from the tab entirely**, per the ticket's locked
decision — no reader in code, so displaying it would show a routing
promise the code does not keep.

## PROMPT MODEL SELECTION — write path (BRIEF-0009-a, no schema change)

TICKET-0009 — the write path `prompt_registry.py:9-11` said stayed
unbuilt until "a write path ships". Schema: none — the nullable
`prompt_template.model` column shipped in v1.67 (BRIEF-0008-a); this brief
adds no column, no migration, no version bump.

**S-null (seed stays NULL, reversing the intake's Q1-seed lock).**
RECON-0009 flagged the intake's "seed explicit defaults" lock as refuted by
BRIEF-0008-a's own design: `default_model` is a callable resolved at read
time specifically so `WORLD_ENGINE_OLLAMA_MODEL` shows through for every
NULL-model row. Materializing explicit names into seeded rows would sever
that channel. `scripts/seed_pilot.py` is untouched; the dropdown's NULL
option renders `Défaut (⟨resolved name⟩)` so visibility survives without
materializing anything.

**W1 (model-only write, no template editing).** `PATCH
/api/prompts/{prompt_id}/model`, body `{"model": string | null}`
(`cockpit/crud.py`, beside the existing read-only prompt routes). Writes
`model` and `updated_at` only — full template text editing
(`system_prompt`/`user_template`/`notes`/`is_active`/`version`) stays a
separate, unscoped chantier. No `change_history` row: `prompt_template` is
creator-CRUD state-setting territory, the same posture as every other
creator-direct write (restated, not a new exception).

**V1 (fail-closed validation).** A non-NULL value calls
`ollama_client.ping()` first: `OllamaError` -> `503`, row untouched
(setting an override requires Ollama running, deliberately — a model
override is only meaningful if the model can be checked); a value absent
from the live tag list -> `422` naming the value, row untouched. NULL is
always accepted with **no** `ping()` call — clearing an override must work
with Ollama down. `GET /api/ollama/models` (thin wrapper over `ping()`,
same file) mirrors the same rule: `200 {"models": [...]}` on success,
`503` with the error's own message on failure — never an empty-list
masquerade that would look like "Ollama has zero models installed".

**Badge semantics (C3) — visible truth, never silent fallback.** A stored
`model` absent from the live list renders a `⚠ modèle absent` badge, both
on the detail selector and on every master-list row — comparison is
client-side against the one `GET /api/ollama/models` fetch held in cockpit
view-state (`promptsOllamaModels`/`promptsOllamaError`, `index.html`),
reset on every sub-tab entry and world switch, never persisted server-side.
The stored-but-absent value renders as a marked, non-selectable `<option>`
(re-saving it is refused server-side by V1 regardless). When the list
endpoint itself is unreachable, the selector area shows the error and falls
back to the prior read-only display — badges are simply not computed (no
list to compare against), absence of signal rather than a wrong one.

**No second resolver.** The write path adds no new model-dispatch reader:
every `.model` reference in `crud.py` is either of the two pre-existing
display reads (`_prompt_row_summary`, `get_prompt_detail`), the new write
(`row.model = value`), or the new PATCH body field
(`PromptModelBody.model`) — `prompt_registry.effective_model` remains the
sole resolver every templated call site routes through.
`verify/checks/prompt_model_write.py` enforces this with a line-level
allowlist grep guard, alongside the PATCH/list behavioral assertions
(stubbed `ping`, no live Ollama dependency).

## CLAUDE.MD CONTRACT + ARTIFACT CONVENTION (BRIEF-0010-a, no schema change)

TICKET-0010. CLAUDE.md had grown to 1366 lines / 107 KB — a ~25K-token tax
on every Claude Code session — with `### File structure` alone at 916
lines (67%): a brief-by-brief annotated tree duplicating this registry and
the schema changelog, going stale on every chantier, and simultaneously
incomplete (it omitted `tooling/`, `.claude/`, `prompt_registry.py`,
`writes.py`, `backup.py`, the second cockpit, and pointed at
`verify/checks/` instead of the real `tooling/verify/checks/`). The
existing freshness rule — "step closure keeps this file consistent" — was
disciplinary and demonstrably failed; this brief makes it structural.

**A1 (bare file-structure tree).** `### File structure` is now one line
per file, role only, rebuilt from the real repo tree. History references
(`BRIEF-NNNN`, `schema vX.YY`) are banned from the section by construction
— `tooling/verify/checks/claude_md_contract.py`'s archaeology-ban
assertion enforces zero matches for `BRIEF-` / `schema v` / `v\d+\.\d+`
within it. Every file's brief-by-brief history stays exactly where it
already lived: this registry and the schema changelog.

**B1 (invariants kept, rewritten as law only).** All 33 pre-existing
invariants survive (title-level, verified by diff during execution), plus
two integrated from shipped reality: TICKET-0009's prompt-model write-path
invariant, and corrected verify-check paths (`verify/checks/` ->
`tooling/verify/checks/` throughout — the tree's actual location).
Rationale, chantier narrative, and deferred alternatives for every
invariant live here, in `ARCHITECTURE_DECISIONS.md`, never in CLAUDE.md
itself.

**C1 (structural freshness contract).** New deterministic check
`tooling/verify/checks/claude_md_contract.py` — no live dependency, same
harness conventions as its siblings — asserts, every `/verify` run wired
to it: (1) the H2 section whitelist is exact and ordered (`What this is`
through `Conventions`), with the H3 whitelist under `Conventions` (`File
structure`, `Naming`, `Schema fidelity rules`, `How to run / test`)
checked the same way; (2) total file <= 500 lines, `### File structure`
<= 80 lines; (3) the archaeology ban, scoped to `### File structure`
only — governance sections legitimately reference `BRIEF-NNNN` forms, so
the ban does not apply file-wide; (4) pointer freshness — every
`tooling/...` path token mentioned anywhere in CLAUDE.md is tested against
the real filesystem (`Path.exists()`), turning a moved/deleted reference
into a red verify instead of a silent discovery. This is the file's actual
"stays up to date" lever now, replacing the disciplinary sentence with a
mechanical one.

**D1 (chat-side authored, Claude Code replaces).** The replacement file
was authored chat-side at content-constant law and delivered as a
finished artifact; Claude Code's execution step was a byte-for-byte
replace plus a required content-constancy review (diff old vs new,
confirm every one of the 33+2 laws survives at title level) before
committing — no editorial changes to the delivered wording; anything found
missing would have escalated (D1-a) rather than being silently re-added.

**T2 — artifact convention + pipeline-cockpit dormancy, folded in.**
Tickets, RECONs, and briefs now arrive as `.md` files carrying their final
real IDs in both filename and content (`TICKET-NNNN.md`, `RECON-NNNN.md`,
`BRIEF-NNNN-a.md`) — no placeholder resolution step. Nia deposits
artifacts into `tooling/tickets|recon|briefs` manually. The pipeline
cockpit's deposit flow (BRIEF-0006-a) is dormant: its filename format
proved too strict and its docs were not visible at deposit time in
practice. The app stays in-tree, unmaintained, never routed to; reopening
it is a future ticket with these two friction facts as its intake — not
acted on here.

## PROMPT VERSIONING — append-only history, single accessor/write shape (BRIEF-0011-a, schema v1.68)

TICKET-0011 (RECON-0011). `prompt_template` carried text directly, with a
decorative `version` column nothing ever incremented — no history existed.
This chantier moves text into an append-only `prompt_version` table, makes
the head a pure identity/wiring row, and threads every read through one
accessor, so a creator can edit a prompt and see the change take effect
immediately with a recoverable history.

**A2 (head pointer, text in version rows).** `prompt_template` keeps only
identity/wiring fields (`name`, `usage`, `variables`, `destination`,
`model`, `is_active`, `notes`, `updated_at`); `system_prompt`/
`user_template` live exclusively in `prompt_version`. "Current" =
`MAX(version_number)` per head — no pointer column anywhere, so there is no
second write to keep in sync with the append.

**B1 (version scope: text only, `model`/`variables` stay head-resident).**
A version row carries `system_prompt` + `user_template` and nothing else.
Versioning `model` or `variables` too (**B2**) is explicitly deferred —
below.

**C1 (fail-closed placeholder validation).** Every write extracts each
`{identifier}` placeholder (regex `\{([A-Za-z_][A-Za-z0-9_]*)\}` — chosen
so JSON-example braces like `{"key": ...}` never match) from BOTH
`system_prompt` and `user_template`; every name must already be in the
head's `variables` list or the write is refused entirely (nothing written)
with the offending names surfaced to the caller. Applies identically to a
first-time edit and a restore — a restore is not exempt just because the
text previously existed.

**D1 (restore = new version).** `POST .../versions/{n}/restore` appends a
new version copying `n`'s text verbatim (auto-note `"restored from v{n}"`);
it never rewinds a pointer or touches history. If the head's `variables`
changed since `n` was written, C1 can refuse the restore — a deliberate
consequence of "no exemptions," not a bug.

**F1 (drop the head's text columns after backfill).** The migration
(`scripts/migrate_v1_68_prompt_version.py`) backfills a v1 `prompt_version`
row for every existing head from its current `system_prompt`/
`user_template`, asserts every head now has >= 1 version, THEN drops
`prompt_template.system_prompt`/`user_template`/`version` — no denormalized
cache, no second source of truth to drift.

**G1 (single read accessor).** `prompt_store.current_prompt(db, template)`
(plus `get_version`/`list_versions`) is the ONLY code allowed to read
`prompt_version` rows — mirrors the `prompt_registry.effective_model`
precedent. `current_prompt` raises `RuntimeError` on a versionless head
rather than falling back to blank text: post-migration that state is
structurally impossible (migration post-check + S2 + append-only), so a
silent fallback would hide a real bug. Every one of the ~25 call sites
across `region_author.py`, `analyzer.py`, `entity_author.py`, `gathering.py`,
`cockpit/app.py`, and `cockpit/crud.py` now fetches its version once, next
to the existing template load, and reads text off the version instead of
the head.

**S2 (seed never touches text once a head has a version).** Arbitrated
against S1 (converge-on-diff forever, which would silently supersede a
creator's edit on the next re-seed) and S3 (a `source` column
distinguishing seed-authored from creator-authored versions, gating
reconvergence on it). S2 won: the ticket's entire point is that the
creator's edit is what runs, and S3's extra column/reader bought
provenance display that has no consumer yet (minimal-first). Concretely:
`upsert_prompt_template` creates a virgin head's v1 from seed text, then
NEVER touches text again once >= 1 version exists — a re-seed only
converges non-text head fields (name, variables, destination, notes,
is_active), same as before. A head found with zero versions mid-bootstrap
(a pre-migration DB that skipped the migration) aborts loudly rather than
guessing.

**H1 (one substitution mechanic repo-wide).** Arbitrated against H2
(teach C1 a mechanism-aware branch that additionally rejects any
undeclared brace content for the 6 `.format()`-consuming call sites, no
call-site diff). H1 won: normalizing the 6 `str.format()` sites
(`region_author.py:321/400`, `entity_author.py:398/527/616/704`) to the
same chained `.replace()` mechanic as every other call site is a small,
bounded diff, and it makes literal `{`/`}` in an edited template safe by
construction everywhere — C1 stays a clean identifier-membership check
with no mechanism-aware branch. The pre-existing risk this closes: seeded
play templates already contain literal JSON braces (safe today only
because those are `.replace()`-consumed); once ANY template is creator-
editable, pasting a JSON example into a `.format()`-consumed authoring
template would have raised `KeyError`/`ValueError` at call time.

**API surface.** `PATCH /api/prompts/{id}/text` (write, C1-gated),
`GET /api/prompts/{id}/versions` (history list, no bodies — same lazy
rationale as BRIEF-0008-b), `GET /api/prompts/{id}/versions/{n}` (one
version, with bodies), `POST /api/prompts/{id}/versions/{n}/restore`.
Preview endpoints (`app.py`'s `npc_dialogue`/`player_narration` dry-runs)
needed no route change — they inherit the accessor through the shared
helpers they already called, so the fidelity invariant (preview == live)
holds by construction rather than by a second implementation.

New verify check: `tooling/verify/checks/prompt_version.py` — schema shape
(table + UNIQUE index, head columns dropped), static allowlists for both
the `PromptVersion` class and raw SQL naming the table, single-write-shape
scan, universal (no-allowlist) append-only scan, the H1 `.format()` scan,
and a live exercise of the write/PATCH/restore paths including the C1
422 case.

Cockpit edit form, history list, and restore button are **BRIEF-0011-b** —
this brief ends at a working, verified API + bit-identical runtime (the
first behavioral change happens only when a creator saves an edit through
the new API).

## COCKPIT PROMPT EDITING UI — edit mode, history, restore (BRIEF-0011-b, no schema change)

TICKET-0011, second brief. Consumes the API BRIEF-0011-a shipped
(`PATCH .../text`, `GET .../versions[/{n}]`, `POST .../versions/{n}/restore`)
as-is — `src/world_engine/cockpit/index.html` only, no Python change.

**U1 (explicit edit mode, one renderer).** `_promptsRenderDetail` gains a
second branch gated on `promptsEditMode`
(`_promptsRenderReadBodies`/`_promptsRenderEditBodies`) rather than a second
renderer — the same fidelity lesson as BRIEF-0008-b: a duplicate render path
is where drift breeds. Draft text lives in client state
(`promptsEditDraftSystem`/`...User`/`...Note`), never read back off the DOM
or off `promptsCurrentDetail`, so an incidental full-pane re-render (e.g. a
model-selector change mid-edit) never clobbers in-progress text.

**V1 (collapsible lazy history + per-version read-only view).** `GET
.../versions` fires only on first expansion (`promptsHistoryVersions` starts
`null`); a save or restore nulls the cache so the next render (if still
expanded) refetches. Opening a version fetches its body on demand. The
restore control is gated on the server's own `is_current`, never inferred
client-side, so it can never appear on the current version.

**W1 (one-click restore, no modal).** Append-only makes restore
non-destructive by construction — it appends a version, it never overwrites
one — so the consequence is made visible instead via a computed label
(`Restore v{n} as new v{next}`) rather than a confirmation dialog.

**X1 (dirty guard).** `promptsEditDirty` is set on any edit-mode keystroke;
`_promptsConfirmDiscard` (a plain `confirm()`) gates both switching the
selected prompt and a world-switch reset — declining leaves the edit
untouched. No draft persistence beyond that: a reload still loses an
in-progress edit, matching the rest of the cockpit's no-draft-persistence
doctrine.

**Server stays sole authority.** The live placeholder hint
(`_promptsUpdateEditHint`, reusing `_promptsExtractTokens` against the
head's declared `variables`) is advisory only — it never blocks Save. The
422 from BRIEF-0011-a's C1 is the only real refusal, rendered inline under
the form with the offending names, drafts intact, never an `alert()`.

**Fidelity on write.** Save and restore never patch `promptsCurrentDetail`
locally — both refetch through `_promptsRefreshDetail` (GET the head, plus
a forced history refetch if the section is open), the same read-after-write
doctrine already used for the model-override PATCH (BRIEF-0009-a).

## PROMPT LEAN REWRITE — resolved facts over conditional instructions (BRIEF-0012-a, no schema change)

TICKET-0012 (informal RECON embedded in the ticket, no RECON-0012 file —
intake judged a formal recon spec unnecessary). Live prompts carried
instructions the code could already resolve (a 5-tier affinity table the
model was asked to self-select from), blocks irrelevant to most NPCs
(pricing rules in every NPC's universal system prompt), a factually wrong
universal paragraph (a reflexive allegiance denial contradicting TES
AFFILIATIONS), pilot-world names inside `world_id=NULL` templates, and
code-forced magic vocabulary. The throughline: where code already computes
a fact, the prompt states the resolved fact — it never re-explains the
computation or asks the model to reproduce it.

**A1/H2 (affinity tier resolved in code, one directive, no raw number).**
`context.py` gains `_AFFINITY_TIERS` (5 bands, boundaries formalized from
the removed table's fuzzy wording: `<30` hostile, `30-49` méfiante,
`50-59` neutre, `60-75` chaleureuse, `>75` confiante) and `_affinity_tier(intensity)
-> (adjective, directive)` — code is the sole authority on tier boundaries
and wording. `assemble_npc_context` appends exactly ONE resolved directive
line for the interlocutor only (H2); other perceived people get the
adjective via `_render_perception` (now "disposition : <adjectif>", never
"intensité N/100" — the raw number never reaches a prompt). The 5-tier
table and the "assume ~50" paragraph are removed from
`NPC_DIALOGUE_SYSTEM_PROMPT` entirely. Named deferral: `_AFFINITY_TIERS`
text is a code constant, not creator-editable — no template, no cockpit
surface for it until a concrete need says otherwise.

**B1 (pricing rules relocated, condition unchanged).** The tariff rules
text moves out of the universal system prompt into `pricing_section`
(`context.py`), inside the same `price_list` branch that already gated the
tariff lines themselves — a relocation, not new logic. The text now exists
in exactly one place in the codebase (verified: zero occurrences in
`seed_pilot.py`).

**C1 (allegiance-denial paragraph deleted, no replacement).** "QUESTIONS
SUR TES ALLÉGEANCES" asserted a universal "you work for no one," which is
false for any NPC with a public `faction_membership`. Deleted outright:
TES AFFILIATIONS and the `cover_role ?? role` mechanism already state
structurally what each NPC presents; no universal default behavior
replaces the deleted paragraph.

**D3 (magic ambience removed structurally, extended to all three injection
points).** The unconditional `"L'atmosphère y est magiquement « … »"` line
(plus its `magic_phenomena` read) is deleted from `assemble_npc_context`.
`_SAFE_SUBCULTURE_KEYS` narrows from `("values", "magic_phenomena",
"nexus_link")` to `("values",)` — since this allow-list also feeds
`assemble_mj_context` and the `pt-mj-establishment` ambiance join
(`cockpit/app.py`), the narrowing structurally removes magic vocabulary
from all three surfaces at once, not just the NPC fiche (RECON finding
folded into D3's scope — the locked decision named "the assembler"
singular, but the allow-list is shared). `location.magic_status` and
subculture keys keep their stored shape; they simply no longer reach any
prompt. The `values` line stays, independent and non-magical.

**E1 (universal-template examples rewritten world-neutral).** Generic
names/ids (`npc-a`, `rel-a-player`, "le PNJ", "la patronne et le garde")
replace pilot identifiers (Maelis, Reike, Senna, Korin, Le Dernier Verre)
across `pt-conversation-analysis` (7 examples collapsed to 4, all three
rubrics — sign, anti-inflation, resource_change — kept unchanged),
`pt-mj-narration`, and `pt-mj-interpretation`. The English instruction body
of `pt-conversation-analysis` is deliberately NOT translated — only
transcripts/examples go French; full translation is a separate, unscoped
step.

**F1 (developer sync note out of model text).** The
`REGION_MANIFEST_SYSTEM_PROMPT` parenthesis instructing the model to keep
"4 and 4" in sync with `MIN_NPCS_PER_FACTION`/`MIN_FACTIONLESS` was
developer bookkeeping sent to the model as if it were gameplay content.
Moved to a Python comment above the constant; the density floor rules
themselves ("au moins 4", ×2) stay in the prompt unchanged.

**G1 (sequencing) / live-DB delivery.** This ticket executed strictly
after TICKET-0011 closed, because TICKET-0011's S2 guarantee (seed never
touches text on an existing head) means the live DB never picks up a seed
constant rewrite automatically. `scripts/apply_ticket_0012_prompt_rewrite.py`
is a new one-shot, idempotent script: it imports the rewritten constants
from `seed_pilot.py` (single source of text, no text of its own), reads
each touched head's current version via `prompt_store.current_prompt`, and
writes a new version through `writes.write_prompt_version` only when the
text actually differs — a second run reports "unchanged" for all five
heads. Run order: `seed_pilot.py` first (converges head fields, e.g. the
narrowed `pt-npc-dialogue.variables`), then this script (text as new
versions) — both paths land on the same final text, live DB and virgin DB
alike.

New verify check: `tooling/verify/checks/prompt_lean.py` — static
assertions only (AST-parsed seed constants + `context.py` source text, no
DB): removed blocks absent from `NPC_DIALOGUE_SYSTEM_PROMPT`, zero pilot
identifiers across every `*_SYSTEM_PROMPT`/`*_USER_TEMPLATE` constant, the
tier resolver wired into `assemble_npc_context`, pricing text in exactly
one place, the conversation-analysis example count/rubrics, and the
region-manifest sync-note removal.

## NPC GOALS — in-scene volition (BRIEF-0013-a, BRIEF-0013-b, BRIEF-0013-c, schema v1.69)

Nia's frustration: NPCs feel like they wait on the player's orders rather
than pursuing their own agenda in-scene. TICKET-0013 covers only the
in-scene half (goal structure, injection, and — in later briefs — the
initiative signal and `goal_change`); the "world advances off-screen" half
is TICKET-0014, deliberately deferred until this ticket has been observed
live.

**F1 (flat table, no hierarchy).** `npc_goal` — `id`, `world_id`, `npc_id`,
`description` (immutable after insert), `horizon ∈ {short, long}`,
`status ∈ {active, completed, abandoned}` (default `active`),
`change_history`. No `parent_goal_id`: goal hierarchy is a named deferral
(F2, below), not an oversight. A "changed" goal is a closed goal
(`write_npc_goal_status`) plus a new row (`write_npc_goal`) — descriptions
are never edited in place, and a closed goal is never reopened (mirrors the
knowledge-ladder doctrine of "correction is a new entry, not a rewrite").

**Q1 (injection) + S1 (read-side bound).** `assemble_npc_context` gains a
`TES OBJECTIFS` section (`H_GOALS`), placed immediately after `QUI TU ES`
and before `OÙ TU TE TROUVES` — the model sees its goals before its
surroundings. Content: the single most recent active long goal (if any) plus
the 2 most recent active short goals, one line each
(`[LONG TERME] …` / `[COURT TERME] …`), no intro sentence, no ids, no status
text (0012 lean discipline). The bound lives entirely on the read side
(`ORDER BY created_at DESC LIMIT` 1/2 at query construction) — there is no
write-side cap anywhere on active shorts; older un-closed shorts simply go
silent in the prompt until a slot opens up. The section is omitted entirely
when the NPC has zero active goals (same pattern as the affiliations/pricing
optional blocks). `assemble_mj_context` is untouched — no `NpcGoal` import
is reachable from it.

**N1 (structural exclusion, MJ boundary).** Goals are NPC interiority: read
ONLY by `assemble_npc_context` this step (the initiative vote joins in
BRIEF-0013-c). `assemble_mj_context` must never gain a `npc_goal` query —
enforced by a new static check, `tooling/verify/checks/npc_goal_read.py`
(same mechanical philosophy as `single_canon_write.py`): Rule 1 restricts the
`NpcGoal` identifier to an explicit module allowlist (`models.py`,
`writes.py`, `context.py`, `cockpit/crud.py`, the migration script, the
check itself); Rule 2 asserts zero `NpcGoal`/`"npc_goal"` references anywhere
from `assemble_mj_context`'s definition to the end of `context.py` (the
file's entire MJ block).

**Two sanctioned write chokepoints, day one.** `write_npc_goal` (insert,
always `active`) and `write_npc_goal_status` (the ONLY path that transitions
status — appends the previous state to `change_history` first, then allows
exactly `active -> completed` and `active -> abandoned`; any other
transition, including reopening a closed goal, raises `ValueError`).
`canon_write_policy.txt` gains `npc_goal` as a canon table with these two
sites as its only `ALLOWED_SITES` entries — the creator CRUD calls the
helpers rather than writing rows itself, so `single_canon_write.py` needs no
`cockpit/crud.py` entry for this table (same shape as `update_relation`
calling `write_relation`).

**Creator CRUD (E1 baseline authority).** `GET/POST /api/entities/{id}/goals`
+ `POST /api/goals/{id}/status`, scoped to the active world
(`entity.world_id != _world_id(db)` -> 404, mirroring the
`skill_definition` idiom). Creation is rejected (422) unless the target
entity is an NPC character — goals are NPC interiority this ticket; player
goals are not scoped. The character sheet gains an "Objectifs" block
(horizon tag + description + status pill, dimmed when closed, per-active-goal
"Accompli"/"Abandonné" buttons), gated to NPC sheets the same way the
existing "Tarifs" block is (`currentCreationSubTab === 'npc'`) — no edit or
reopen control exists, by design.

**Scope OUT BRIEF-0013-a** (shipped in BRIEF-0013-b, below, and BRIEF-0013-c):
the `pt-npc-goals` generator and its three gates (region generation,
existing-world backfill, single-NPC pre-fill); the initiative-vote signal;
the `goal_change` mutation type (emit and apply sides); the dialogue-template
directive. `_CANONICAL_TYPES`, `_apply_mutation`, `_signal_line`, and every
prompt template stayed untouched in that step.

**T1 (one generator, three gates) / M2 (cardinality).** `generate_npc_goals`
(`entity_author.py`) — one function, one prompt template (`pt-npc-goals`,
authoring model, `format="json"`) — is the sole path to model-authored
goals, requesting exactly 1 long + 2 short goals per call. Pure
generate-and-return, like every other `entity_author.py` generator: it
writes no canon; every canon write happens at the caller via
`writes.write_npc_goal`. Three callers share it: region generation (G1,
per-NPC after the character draft succeeds, attached to
`draft["public"]["goals"]` for the region review UI and written by
`commit_region` Stage 3 in the SAME transaction as the NPC — an NPC and its
goals are never separately observable), single-NPC creation pre-fill (L1,
`/api/entities/generate` merges the block into the editable draft; the
creator form holds it in `pendingDraftGoals` the same way BRIEF-24 holds
`pendingDraftKnowledge`, POSTing each non-empty goal through the 0013-a
endpoint right after the entity is created), and backfill (G2/P2, below). A
goal-generation failure at any of the three gates degrades gracefully
(a note, or a batch failure entry) — it never drops the NPC and never
raises into the caller.

**P2 (per-horizon backfill, no-overwrite).** `POST /api/npc-goals/backfill`
(`cockpit/crud.py`), scoped to one NPC or unscoped (every `character_type
== 'npc'`, `vital_status == 'alive'` NPC of the active world). Per NPC, the
deficit is computed structurally — needs a long iff zero ACTIVE long goals,
needs `2 - n` shorts iff `n < 2` ACTIVE shorts — and only the missing
horizon(s) are requested and written; a fully-satisfied NPC triggers no
model call at all. Idempotent by construction: a second run on an unchanged
world writes zero rows (live-verified: an 11-NPC region commit followed by
an unscoped backfill wrote 16 longs/32 shorts across the remaining deficits
in one pass, then a second run reported zero). Surplus generator output for
an already-satisfied horizon is discarded, never queued for a future run.

**`faction.goals` gains its first reader (generator input only).** Dormant
since schema v1.44 (BRIEF-33), `Faction.goals` is now read at three call
sites — `region_author.py`'s Stage-3 NPC loop (via the local faction
draft's `secret.goals`), `cockpit/app.py`'s `/api/entities/generate` (via a
direct `db.get(Faction, faction_id)` on the draft's resolved faction), and
`cockpit/crud.py`'s backfill (via the NPC's first public active
membership) — feeding `generate_npc_goals`' `faction_goals` parameter only.
This is deliberately NOT a prompt-injection path: no assembler reads
`faction.goals` into any model-facing context. Injecting faction posture
into NPC dialogue prompts remains its own, separately queued chantier.

New verify wiring: `npc_goal_generation` registered in `PROMPT_REGISTRY`
(authoring surface, `_author_model` default, `entity_author.py:
_load_npc_goals_template` call site); `npc_goal_read.py`'s module allowlist
extended with `cockpit/app.py` (the Stage-3 commit-side `write_npc_goal`
calls) — `entity_author.py` and `region_author.py` deliberately need no
entry, since both handle the goals block as a plain dict, never importing
`NpcGoal`.

**BRIEF-0013-c closes the behaviour loop.** Goals now influence the
initiative vote, evolve through creator-approved `goal_change` proposals,
and the dialogue template tells the NPC to pursue them — TICKET-0013 is
complete; TICKET-0014 (world-tick — off-screen agenda progression, scoped
approval batches, H2/I1/J1 pre-locked at TICKET-0013 intake) is the named
successor, to be designed only after this ticket is observed live.

**R1 (vote signal, short-only, code-side).** `_npc_initiative_vote`
(`cockpit/app.py`) gains one batched query — every candidate's most recent
ACTIVE short-term `NpcGoal`, `npc_id IN (...)`, reduced in Python to first-
per-npc — alongside the existing batched relation query (same one-round-
trip discipline). `_signal_line` appends `, objectif=« … »` (80-char
truncation, `…` when cut) when a candidate has one; omitted entirely
otherwise. Long-term goals never enter the vote — R1 is short-only, by
design, not a truncation of both horizons down to one. `pt-mj-initiative`
itself is untouched: the fragment is built in code, the same way the
relation/status signal fields already are.

**H1 (emit) — enabled by a structural fact already true since BRIEF-09.**
`analyze_window` feeds the analysis model the NPC's `injected_context.
assembled_context` (preferred over the raw context blob) — which, since
BRIEF-0013-a, already contains the `TES OBJECTIFS` section. No new
plumbing was needed: the analysis model already sees the NPC's active
goals verbatim, so the rubric only has to instruct exact-copy of the
listed text. `analyzer.py` gains `goal_change` in `VALID_MUTATION_TYPES` +
`VALID_TARGET_TABLES` (`npc_goal`), seven natural-language aliases in
`_MUTATION_TYPE_MAP`, and a `_normalize_to_schema` branch that runs
**unconditionally** whenever `mutation_type == "goal_change"` — even when
the model's own `payload` already looks well-formed, never trusting a
model-supplied `npc_id` or a stray `horizon` key. `action` is coerced
through `_GOAL_ACTION_MAP` (an unrecognised value drops the item); `goal`
text is the first non-empty of `goal`/`description`/`content`, trimmed.
**`npc_id` is FORCED to `conv.npc_id` in code — structural, not
instructional** — the model's input only ever contains ONE NPC's `TES
OBJECTIFS`, so multi-NPC attribution is out of scope by construction (same
posture as `relation_change`'s per-item roster resolution, deferred rather
than guessed at).

**O1 (model may close, never create/re-horizon a long) + S1 (read-side
bound, restated at the apply site).** The `_apply_mutation` branch:
`complete`/`abandon` match against the NPC's ACTIVE goals — **both
horizons** — by exact `_normalize_goal_text` (casefold + whitespace-
collapse) equality; anything other than exactly one match (zero, or an
ambiguous multiple) is treated as "no match" → error string → Needs
attention, nothing written (the `knowledge_change` posture: better
un-applied than wrongly applied). `create_short` always inserts via
`write_npc_goal` with **`horizon="short"` hard-coded in the branch** — the
payload carries no horizon field and none is ever read, so a crafted
`"horizon":"long"` in the payload is silently ignored (live-verified). No
active-count check on insert: S1's bound is still the injection's
read-side `LIMIT`, restated here rather than re-implemented — a third
active short is written without complaint.

**Duplicate-guard asymmetry vs `knowledge_change` (deliberate).**
`_find_applied_duplicate` gains a `goal_change` branch — same
`conversation_id` + same `action` + same normalized goal text is a
duplicate. This is the OPPOSITE choice from `knowledge_change`, which
stays excluded from this guard: successive legitimate knowledge upgrades
across a conversation (rumor → partial → knows) must all apply, but a
repeated identical goal event (the same goal, same action) within one
conversation window is never legitimate — a goal is completed, abandoned,
or newly formed once per scene, not twice. Live-verified: re-approving an
identical `goal_change` in the same conversation is blocked.

**D1 (dialogue directive, final wording).** One paragraph inserted into
`NPC_DIALOGUE_SYSTEM_PROMPT` between ATTITUDE and DISCRÉTION ET NATUREL:
"Ta fiche liste tes objectifs (« TES OBJECTIFS »). Poursuis-les quand la
scène s'y prête — tu peux solliciter, refuser, marchander ou mettre fin à
l'échange si cela les sert — sans jamais en réciter la liste." Delivered to
the live DB, alongside the `pt-conversation-analysis` GOAL_CHANGE rubric +
a fifth worked example, by a new one-shot idempotent script,
`scripts/apply_ticket_0013_prompt_updates.py` (mirrors
`apply_ticket_0012_prompt_rewrite.py` exactly — embeds no text of its own,
compares against `current_prompt`, appends via `write_prompt_version` only
on a real diff). `tooling/verify/checks/prompt_lean.py` Rule 5 updated: 5
`=== EXEMPLE` markers (was 4), four rubric headers (adds `GOAL_CHANGE
RUBRIC`).

**No `npc_goal_read.py` change this step.** `analyzer.py` handles plain
dicts and never imports `NpcGoal`; the apply branch lives in
`cockpit/app.py`, already allowlisted since BRIEF-0013-b.

## WORLD TICK — off-screen NPC advancement (BRIEF-0014-a, BRIEF-0014-b, schema v1.70)

TICKET-0013's named successor (I1 pre-locked at that ticket's intake): a
manual, scoped cockpit action asks the gameplay model what each NPC in scope
did during a creator-chosen interval, and the answers land as
`proposed_mutation` rows under creator approval (C2). This first chantier
ships the READ side and the prompt contract only; the runner (endpoint,
model call, normalization, emit-time dedup) is BRIEF-0014-b.

**K2 (new module, not `context.py`).** `assemble_tick_context(npc_id,
session)` lives in a NEW module, `src/world_engine/tick.py` — never the
dialogue assembler. RECON-0014 F6: `tooling/verify/checks/npc_goal_read.py`
rule 2 scans `context.py` positionally (from `assemble_mj_context` onward);
a tick builder added below that line would be invisible to the scan. A new
module sidesteps the fragility entirely and keeps the MJ boundary rule
byte-identical. `tick.py` imports nothing from `context.py` (drafting
decision, BRIEF-0014-a): the small shared helpers (`_section`,
`_knowledge_line`, `_perceived_target`, `_render_perception`, an
adjective-only slice of the affinity ladder) are replicated locally so the
module's AST stays self-contained.

**T1 (full-interiority briefing — conscious, logged exception).** Unlike
`assemble_npc_context`, a tick has no interlocutor, so the two dialogue
filters (secret exclusion, share-threshold gating) do not apply: the
briefing includes ALL of the NPC's own knowledge — rows with `is_secret`
prefixed exactly `[SECRET] ` rather than dropped — and ALL active
memberships read DIRECTLY from `FactionMembership` (never
`read_public_memberships`), carrying the TRUE `role` (never `cover_role`)
and secret memberships prefixed exactly `[AFFILIATION SECRÈTE] `. The
invariant ("secrets are structurally excluded from every assembled context")
is re-anchored, not waived: the exception is (a) scoped to this one builder,
(b) confined to its allowlisted call sites by static scan (below), and
(c) every downstream effect crosses `proposed_mutation` under creator
approval — the briefing itself is never rendered to a player or MJ surface,
only consumed by the tick model call (BRIEF-0014-b) and the creator preview
script (this brief).

**Section order and composition.** `QUI TU ES` (identity, same composition
as the dialogue assembler) → `TES OBJECTIFS` (ALL active goals, both
horizons, newest first, long-terms first — no read-side cap, unlike the
dialogue injection's `LIMIT` 1/2: the tick must see everything active to
judge what advanced) → `CE QUE TU SAIS` → `TES RELATIONS` (every perceived
edge, `_perceived_target` logic, type + intensity line followed by the
rendered perception sentence) → `TES AFFILIATIONS` (with an indented Faction
posture block per membership — `Philosophie`, `Buts` (`Faction.goals`'s
second reader, after the 0013 generator input), `Tensions internes`,
`Aversion`, one line per non-empty field) → `OÙ TU TE TROUVES` (location +
subculture values, no player-condition injection — that's scene-specific,
not a tick concern) → `QUI EST AUTOUR` (co-located characters by
`current_location_id`, public description only — deliberately UNFILTERED by
`character_type`, unlike the dialogue assembler's `H_COMPANY` query: a tick
judging what an NPC did needs to know whether a player character was
physically present, and the brief specifies no exclusion. The
"PC excluded from NPC co-presence by construction" invariant names
`H_COMPANY` specifically and calls a repoint-or-widen elsewhere a
"deliberate decision" — this is a distinct query in a distinct module, and
this paragraph is that decision, made explicit). Ends with a tick-specific
anti-invention boundary line (distinct wording from the dialogue boundary).
Empty sections render a French placeholder (e.g. `(aucun objectif actif)`)
rather than being omitted — unlike the dialogue assembler's optional
sections, the tick's "Done means" contract requires every section header to
appear in every briefing.

**N1 extension + new structural check.** `tick.py` joins
`npc_goal_read.py`'s `ALLOWED_MODULES`; `assemble_mj_context` stays
untouched. A new check, `tooling/verify/checks/world_tick.py` (stdlib `ast`,
same shape as `npc_goal_read.py`), lands rules 1-2 this brief: rule 1
restricts the identifier `assemble_tick_context` to `tick.py`,
`cockpit/app.py`, and `scripts/preview_tick_context.py` (RECON-0014 F6: an
indirect call from elsewhere would evade a scan keyed on `NpcGoal`/goal
identifiers alone); rule 2 asserts `context.py` and `gathering.py` carry no
reference to `assemble_tick_context` at all. BRIEF-0014-b extends this same
check with rules 3-5 (forced attribution, the `tick_id` duplicate-guard
branch, the `secret_derived` emit-time floor).

**Prompt delivered, no runner yet.** `pt-world-tick` (usage `world_tick`,
`world_id` NULL, `model` NULL — Q1: the eventual runner passes
`ollama_client.DEFAULT_MODEL` through `effective_model`, keeping a
per-template override available) is seeded in `scripts/seed_pilot.py` and
delivered to the live DB by a new one-shot idempotent script,
`scripts/apply_ticket_0014_prompt_updates.py` (0013 pattern, but this head
is BRAND NEW — unlike 0013's script, which only appended versions onto
already-seeded heads, this one also handles the head-absent branch: create
the head + write v1 via `write_prompt_version`, no-op when the head already
exists with identical text). English-bodied system prompt (mirrors
`pt-conversation-analysis`); the payload shapes (`"other"` for a relation
counterpart, `"recipient":"self"|name` for knowledge) are locked here —
BRIEF-0014-b's normalizer must match them exactly. **No `PROMPT_REGISTRY`
entry yet**: that entry (and the loader call site it points to) lands with
the runner in BRIEF-0014-b, mirroring the 0013 precedent —
`npc_goal_generation`'s registry entry arrived with `generate_npc_goals`
(BRIEF-0013-b), not with the earlier goal-table brief. Until BRIEF-0014-b
closes, `usage="world_tick"` is seeded but absent from `PROMPT_REGISTRY`; no
check gated on TICKET-0014's own G1 exercises the registry bijection, and no
`chat`/`chat_stream` call references this usage yet.

**Preview reader.** `scripts/preview_tick_context.py --npc <id>` prints the
assembled briefing to stdout; a player character or unknown id exits 1 with
a clear error and prints nothing. This is `assemble_tick_context`'s only
reader this brief, and the live-gate instrument for T1 review.

**Scope OUT this brief** (BRIEF-0014-b): the tick RUNNER (endpoint, model
call, JSON extraction, E1/O1 forced attribution, emit-time dedup,
`secret_derived` code floor per Z3); the `tick_id` migration (Y2) and the
duplicate-guard's tick branch; queue labels/badges, `_mutation_dict`
changes; cockpit UI (scope selector, interval selector, the button); any
movement/`status_change` emission (deferred at L3); any automatic trigger or
in-game time system (I3 deferred, no `last_tick_at` storage per M); goal
hierarchy `parent_goal_id` (F2 stays closed — `create_short` stays flat even
here); pre-authorization/auto-apply of any proposal category (J3 stays
rejected).

**BRIEF-0014-b makes the tick RUN.** `run_world_tick(db, npc_ids,
interval_label, model, host)` (`tick.py`) generates one `tick_id` per
invocation and, per NPC (degrade-don't-abort, R3): assembles the briefing,
loads `pt-world-tick`, calls the model with `format="json"`, and normalizes
the result — any exception (briefing guard, model call, JSON parse) records
a note for that NPC and moves on; nothing is written for it. Surviving
proposals across ALL NPCs commit in ONE transaction at the end — a crashed
invocation (before that point) writes nothing.

**E1/O1-mirror (forced attribution).** `_normalize_tick_item` FORCES
`npc_id` (goal_change) and `entity_a_id` (relation_change) from the
function's own parameter — never read from the model's payload, structural
not instructional (`world_tick.py` rule 3, AST-verified: no
`.get("npc_id")`/`.get("entity_a_id")` anywhere in `tick.py`, and both
identifiers appear as dict-literal keys only with a bare-`Name` value).

**Closed type contract.** Unlike conversation analysis, the tick accepts
ONLY `goal_change | relation_change | new_knowledge` (via the same alias
map as `analyzer._MUTATION_TYPE_MAP`, imported not duplicated); anything
else — including the fallback `other` — is dropped with a note, never
proposed. `_content_to_subject_slug`, `_extract_json_array`,
`_GOAL_ACTION_MAP`, and `load_analysis_prompt` are reused from `analyzer.py`
verbatim (analyzer never imports tick — no cycle).

**Roster (E1, name-based resolution).** `_build_roster` maps
`name.casefold() -> id` from EXACTLY what the briefing names: the ticked
NPC itself, co-located characters (QUI EST AUTOUR), and perceived relation
targets (TES RELATIONS) — no faction-mate expansion. A casefolded name
carried by two different ids is ambiguous and removed from the roster;
resolution then fails for that name and the item is dropped, never guessed.
`relation_change`'s `"other"` and `new_knowledge`'s `"recipient"` (when not
`"self"`) resolve through it.

**Z3 floor (mechanical, decoupled).** Before normalizing an NPC's items,
`secret_subjects` is built as a set comprehension of that NPC's own
`Knowledge.subject` (casefolded) where `is_secret` — then `secret_derived`
is forced `True` when the proposal's subject or content matches. The floor
NEVER reads or writes `is_secret`: confidentiality stays the model's
(then the creator's) call, provenance is code's. `world_tick.py` rule 5
AST-verifies both the set-comprehension shape and that no assignment or
dict-literal key inside `_normalize_tick_item` sets `is_secret` from
`secret_subjects`/`secret_derived`.

**Emit-time dedup (item 6).** Within one NPC's item list — never across
NPCs or across the whole invocation — subsequent duplicates are dropped,
keeping the FIRST occurrence: `goal_change` keyed `(action, normalized goal
text)`; `new_knowledge` keyed `(entity_id, subject)`; `relation_change`
keyed `(entity_a_id, entity_b_id)` (the rubric already demands one NET
delta per counterpart per interval — extras are rubric violations, not
legitimate accumulation).

**Y2 (implemented) — canon-existence guard, re-run-proof AND revival-safe.**
`_find_applied_duplicate` (`cockpit/app.py`) now branches in two mutually
exclusive scopes: conversation-sourced mutations keep the pre-existing
branch byte-identical; tick-sourced mutations (`conversation_id IS NULL`,
`tick_id` set) run CANON-EXISTENCE checks instead of a tick_id-scoped
history comparison — a re-run gets a NEW `tick_id` every time, so comparing
WITHIN one `tick_id` would miss exactly the cross-run duplicates F2 is
about, while an unbounded history comparison would block legitimate goal
revivals (a revived goal is a new row, 0013 doctrine). `create_short` is a
duplicate iff an ACTIVE `NpcGoal` already matches by normalized text;
`complete`/`abandon` get NO guard here (the apply branch's
exactly-one-active-match requirement is already correct); `new_knowledge`
is a duplicate iff a `Knowledge` row already exists for
`(entity_id, subject)`; `relation_change` gets NO guard, same
accumulating-deltas doctrine as the conversation-sourced branch — a double
delta from a re-run tick is visible in the queue, the creator's to judge,
never blocked. `world_tick.py` rule 4 AST-verifies the branch exists.

**Endpoint.** `POST /api/world-tick` (`cockpit/app.py`, beside the
analyzer-facing endpoints, per RECON-0014 F8 — not `crud.py`, since it
writes `ProposedMutation` rows through the proposal pipeline, not creator
CRUD). Resolves `scope_type` (`npcs` | `location` | `faction`) to NPC ids
server-side (never trusts a client-supplied NPC list beyond per-id
validation), rejects an unknown interval/scope_type/empty resolved scope
with 422 before any model call, pings Ollama fail-fast (503), then calls
`run_world_tick` and returns its R3 summary verbatim.

**Queue surfacing (P1 + Z3 badge).** `_mutation_dict` gains `tick_id`.
`renderCard` (`index.html`) shows a `TICK ·xxxx` badge (first 4 chars,
grouping label — same invocation, same suffix) when `source_type ===
"world_tick"`, and a distinct warning-styled badge
`dérivé d'un secret` when `payload.secret_derived === true` — independent
of `is_secret`, which stays the receiving NPC's own disposition.

**Cockpit controls (I1/J1/M3).** A "Faire avancer le monde" button, a
scope-type selector (PNJ(s) multi-select / Lieu / Faction, single-select),
and an interval selector (the three verbatim French labels) live in the
Review Queue tab's existing `creation-shell-extra` slot, alongside the
filter bar — not a new registry entry or a new primaryAction (Queue's
`primaryAction` stays `null`; this reuses the same one-off slot mechanism
the filter bar already occupies). Scope selectors populate from the
entity-list APIs the Création view already calls (`/api/entities`,
`/api/skills/player-characters` for the NPC/PC split, `/api/locations`,
`/api/entities?type=faction`) — no new listing endpoint.

**`PROMPT_REGISTRY` entry lands here, closing the BRIEF-0014-a gap.**
`"world_tick"` — `surface="play"`, `world_scoped=False` (the template loads
via `world_id=None`, mirroring the authoring-surface entries' pattern, not
a per-conversation world), `call_sites=("src/world_engine/tick.py:
run_world_tick",)`, `default_model=_game_model`. `prompt_registry.py`'s
bijection check now passes for `world_tick` — the seeded usage and its
registry entry are no longer split across two commits. `tick.py` also
joins `prompt_registry.py`'s `WIRED_FILES` (static wiring scan, rule 3) —
found missing during this brief's review-step: the check had never
actually scanned `tick.py`'s `chat()` call for `model=effective_model(`,
so the correct wiring was unverified rather than unenforced. Fixed and
red-tested (a bare `model=` in `run_world_tick` now fails the check).

**Docs.** `world-engine-schema.md`/-changelog: `tick_id` column + index +
third `source_type` value + `local_ai_tick` documented alongside the schema
bump to v1.70. `CLAUDE.md`: one line noting tick-sourced rows'
`source_type`/NULL-FK/`tick_id` shape and that the duplicate guard's tick
branch must never be extended to `relation_change`.

## WORLD TICK — NPC movement (BRIEF-0015-a, no schema change)

Lifts TICKET-0014's L3 movement deferral: a ticked NPC may relocate along the
`connects_to` graph during off-screen advancement. `proposed_mutation.
mutation_type` is unconstrained TEXT and `tick_id` already exists since
v1.70 — no migration, confirmed at RECON.

**E3 — interval-scaled radius, structural not instructional.** Nia's
rationale on record: when ticks later become automatic (I3, still deferred),
the radius is what guarantees a session-close tick cannot move an NPC across
a continent — a code bound, never a prompt request. `INTERVAL_HOP_RADIUS`
(`tick.py`, a plain module-level dict) maps the interval label to a hop
count: `"quelques heures" -> 1`, `"quelques jours" -> 3`, `"quelques
semaines" -> None` (unbounded). RECON-0015 F1 correction: the keys are the
VERBATIM labels of `cockpit/app.py`'s `_VALID_TICK_INTERVALS`
(`"quelques heures/jours/semaines"`), not the shorter forms drafted at
intake.

**"Unbounded" means the origin's connected component, not all locations**
(RECON-0015 F3, drafting decision confirmed). `_reachable_locations`
(`tick.py`) is a NEW, tick-local BFS over `Relation.type == "connects_to"`
among ACTIVE locations, origin excluded — deliberately NOT sharing code with
`_location_neighbours` (`cockpit/app.py`, direct-neighbours-only): decision
D1 (BRIEF-19) stands, this is now the third `connects_to` reader. An island
location with no `connects_to` path stays unreachable at any interval — the
map is the world's traversability truth, not a proxy for physical distance.

**Briefing section `OÙ TU PEUX ALLER`.** Rendered between `OÙ TU TE TROUVES`
and `QUI EST AUTOUR` in `assemble_tick_context`, which gains a keyword-only
`destinations: list[tuple[str, str]] | None` parameter — `- <name>` plus the
location's `description` when non-empty, placeholder `(nulle part — aucun
lieu accessible)` when empty. T1 contract unchanged: the header always
renders. The candidate set is computed ONCE per NPC in `run_world_tick`
(moved ahead of the model call, since the briefing needs it — RECON-0015 F2)
and passed BOTH to the briefing and to `_normalize_tick_item`, so the model
never sees a set different from the one resolution accepts.

**Type acceptance without touching the shared map.** A tick-local alias
dict, `_TICK_TYPE_ALIASES = {**_MUTATION_TYPE_MAP, "npc_move": "npc_move",
"move": "npc_move", "movement": "npc_move"}`, replaces the direct
`_MUTATION_TYPE_MAP.get` read in `_normalize_tick_item`.
`analyzer._MUTATION_TYPE_MAP` itself stays byte-identical — conversation
analysis and overhearing must never gain movement vocabulary
(`world_tick.py` rule 6, AST-verified: no dict-literal key in
`_MUTATION_TYPE_MAP` maps to `"npc_move"`). `_TICK_MUTATION_TYPES` gains
`"npc_move"` as its fourth (and, for this chantier, final) member.

**Forced attribution extended (rule-3 pattern).** `from_location_id` joins
`_FORCED_FIELDS` in `world_tick.py` (alongside `npc_id`, `entity_a_id`):
`_normalize_tick_item` stamps it from the `from_location_id` parameter
(the NPC's own `current_location_id` at emit time), never reads it from the
model's payload. `to_location_id` is deliberately NOT added — it is
resolved from the model's `"destination"` name against the candidate set,
not forced; the resolution vs. attribution distinction is semantic, not an
AST-visible one (RECON-0015 F5). Display fields `from_name`/`to_name` ride
in the payload itself (`_mutation_dict` already passes payloads verbatim —
RECON-0015 F9, precedent: `resource_change`'s `reason` field). Out-of-radius
and invented destinations fail identically (one dropped note) — the model
only ever sees in-radius names, so distinguishing the two would only label
model hallucination more precisely, not worth a second code path (drafting
decision, confirmed).

**Emit-time dedup.** A per-NPC `seen_move: bool` in `run_world_tick` allows
AT MOST ONE `npc_move` per NPC per invocation — first occurrence wins, later
ones dropped with a note (same idiom as `seen_goal`/`seen_knowledge`/
`seen_relation`).

**Apply-time: the stale-from gate replaces the tick_id-keyed guard drafted
at intake** (RECON-0015 F6, strictly stronger, per the 0014 tick-guard
doctrine of canon-existence over `tick_id` equality). `_apply_mutation`'s
new `npc_move` branch loads the `Character` by `payload["npc_id"]`, then
checks `character.current_location_id != payload["from_location_id"]` —
one canon question that covers duplicate re-approval, cross-run re-run
duplicates, AND a manual move since the proposal, while correctly ALLOWING a
later legitimate A->B->A move. `_find_applied_duplicate`'s tick branch gains
a mirror `npc_move` clause returning the same verdict, for pre-write/apply
symmetry with the other tick types. On success: the write routes through a
new `writes.py` helper, `write_character_location(db, *, entity_id,
to_location_id, mutation_id=None) -> Character` (loads the row, sets
`current_location_id`, caller commits — `write_relation` precedent). No
`change_history`: `character` has no such column and the creator-CRUD
location edit snapshots nothing; the `proposed_mutation` row (from/to
payload, `tick_id`, `applied_at`) is the durable audit trail (RECON-0015
F7). `close_open_memberships(npc_id, db)` runs unconditionally — **an
approved move pulls the NPC out of its open gathering even when the player
character shares it** (Nia's locked decision, verbatim: « je pense qu'il
doit être possible de sortir un NPC de son gathering »); the Play roster
reflects the departure live via the existing `gathering_member.left_at IS
NULL` seam, no snapshot, no parallel presence state.

**`world_tick.py` gains rules 6-8** (stdlib `ast`, same idiom as
`check_forced_attribution`/`check_guard_branch`): rule 6 scans
`analyzer.py`'s `_MUTATION_TYPE_MAP` literal for a `"npc_move"` value (must
find none); rule 7 asserts `INTERVAL_HOP_RADIUS` carries EXACTLY the three
verbatim label keys and that `_reachable_locations` references it; rule 8
scans `_apply_mutation`'s function body for a direct `current_location_id`
attribute assignment (must find none) and for calls to both
`write_character_location` and `close_open_memberships` (must find both).
`canon_write_policy.txt` gains one `ALLOWED_SITES` line —
`writes.py::write_character_location -> character` — following the same
convention as `write_relation`/`write_knowledge`: `_apply_mutation`'s own
policy entry is untouched, since the actual `db.add` happens inside the
helper's function scope, not the caller's.

**Preview script.** `scripts/preview_tick_context.py` gains `--interval`
(choices = the three verbatim labels, default `"quelques jours"`); computes
the reachable set exactly as the runner does and passes it through, so the
printed T1 briefing shows `OÙ TU PEUX ALLER` as the model will see it.

**Prompt.** `pt-world-tick`'s existing head (since BRIEF-0014-a) gains an
appended version: `npc_move` joins the mutation_type/target_table
enumeration, a `npc_move -> {"destination":"…"}` payload shape, and a new
`=== NPC_MOVE RULES ===` block (at most one move per interval; destination
must be copied from `OÙ TU PEUX ALLER`; staying put = emit nothing; a move
needs a stated motive). Delivered by
`scripts/apply_ticket_0015_prompt_updates.py` — append-version branch only
(unlike 0014's script, no head-absent branch is needed).

**Scope OUT this brief** — carried or newly named deferrals: `status_change`
emission from the tick (0014's L3, other half); automatic triggers/in-game
time (I3); player movement via the tick, NPC schedules/routines,
travel-time or multi-hop journey simulation (after apply the NPC simply IS
at the destination); any analyzer/overhearing producer for `npc_move`
(permanently out, not merely deferred — movement is a tick-only concept);
return-visit delta narration/`visit` table (G2, next ticket); refactoring
`_location_neighbours` or the locations graph endpoint to share the new BFS
(D1 stands).

## Deferred decisions

- **F2 — goal hierarchy (`parent_goal_id`)** (TICKET-0013). Deferred until a
  reader exploits parentage — e.g. "short goal completed -> model proposes
  the next step of the parent long goal." Nia is explicitly interested;
  reactivate only when a concrete reader needs it, not speculatively.
- **Goal-proposal pre-authorization** (TICKET-0013, J2). Nia anticipates
  needing pre-authorized categories of `goal_change` "si le jeu devient
  gros" (batch or auto-approval bypassing the creator checkpoint). This is a
  conscious, deliberate doctrinal exception to *model proposes, code
  judges* — never a drift — and must be its own future decision, not folded
  into a later brief incidentally.
- **Affinity tier text creator editability** (BRIEF-0012-a). `_AFFINITY_TIERS`
  (adjectives + directives) live as `context.py` constants, not a template or
  a cockpit surface — resolved behavior is mechanics, not creator content,
  until a concrete need says otherwise. Re-opening this means either a new
  head/version pair per tier or a small config table; neither is built now.
- **B2 — versioning `model`/`variables`/head metadata** (BRIEF-0011-a,
  schema v1.68). Text-only versioning shipped this chantier; extending the
  same append-only pattern to `model` and `variables` is deliberately
  deferred, to be re-opened "just after" per Nia's own framing at intake.
- **`_effective_prompt_row`'s multi-active-row nondeterminism** (BRIEF-0011-a).
  Unchanged, pre-existing observation (world-scoped usages fall back to
  `active[0]` when 2+ rows tie) — accepted, not this chantier's scope.
- **X1 dirty guard is best-effort across a world switch** (BRIEF-0011-b).
  `_promptsWorldReset`'s `confirm()` can only gate whether the *client
  state* (`promptsEditMode` et al.) gets cleared — by the time it runs,
  `activateWorld`/`worldDeleteConfirm` have already switched the world
  server-side, and if the Prompts tab is the active one, the subsequent
  `showCreationSubTab` → `promptsLoadList()` call unconditionally wipes the
  visible detail pane regardless of the guard's answer. Declining the
  confirm therefore preserves the JS draft variables but not necessarily
  the on-screen textareas. Accepted as-is: the scenario (mid-edit + a world
  switch in the same moment) is narrow, and a full fix would mean teaching
  `promptsLoadList`/`showCreationSubTab` about a foreign tab's dirty state
  — out of this brief's single-file, minimal-surface intent.
- **D-0052-shape — full prompt-shape parity for the observed lane**
  (TICKET-0052, K1: a role-alternating message list instead of a single
  `{transcript}` blob). Reactivate only after F1's measurement
  (`scripts/observation_metrics.py`, `per_beat_overlap`) has isolated the
  repetition cause, so the two changes are never confounded.
- **D-0052-mj — the observed MJ narrator receives the full transcript while
  the played MJ narrator receives none** (TICKET-0052, H1). Deliberately
  unchanged. Reactivate if `mj_narration` ever becomes an input to a
  measured path (today it is opt-in and display-only).
- **D-0052-repetition — the beat-8 repetition onset itself** (TICKET-0052).
  Fed by F1. `repeat_last_n=256` (`ollama_client.py:30`) was calibrated for
  played turns (its own comment says "3-4 turns") and has never been
  revisited for 25-35 word observed beats; a hypothesis for that
  workstream, not a decision made here.

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
- **Soft-archival of the three named hard-deletes** (CANON-WRITE DOCTRINE,
  BRIEF-0003-b, L1). `delete_relation`, `delete_knowledge`, and
  `delete_discoverable_detail` were considered for conversion to a status
  flag (soft delete, preserving `change_history`/the row instead of
  discarding it) when they were named into CLAUDE.md's closed hard-delete
  list. Considered and deferred, not rejected — L1 only named the existing
  hard-delete behavior; changing it to a soft pattern is a separate,
  not-yet-scoped ticket.

## RETURN-VISIT DELTA (BRIEF-0016-a, schema v1.71)

TICKET-0015 gave NPCs off-screen movement; nothing told the player the world
moved. G2 lands: a new `visit` table anchors the player's last entry per
location, and a code-computed diff (NPCs arrived/departed, public events
since) rides into the EXISTING `mj_establishment` narration at
`enter_scene`. The deferral was named in code at `cockpit/app.py` since
BRIEF-17 ("no change-detection (G2 deferred)") — this brief lifts it.

**G2 over G1 — a table, not a conversation-derived anchor.** Nia's locked
rationale: "visited without conversing" is a normal play pattern a
conversation-derived last-seen timestamp would miss entirely (a player can
walk through a location, see nobody, leave, and still deserves a delta on
return). `visit` is append-only, born empty at migration — no backfill, so
every location the player has never re-entered since counts as a first
visit exactly once, by design.

**F3 — scoped naming exception to the establishment rule.** The existing
`mj_establishment` system prompt forbade naming ANY present NPC (J1,
BRIEF-17) — narrating a departure would violate it as written, and
departures are shown NOWHERE else in the UI, which is this ticket's entire
point. The new prompt version scopes the rule instead of removing it: NPCs
cited in the CHANGEMENTS block (arrivals/departures) may be named; any
presently-present NPC remains unnameable, exactly as before (the roster UI
is still the sole surface for "who's here now"). A mirrored anti-invention
clause (parallel to the signposts rule) forbids inventing a change when the
block reports nothing.

**F4 — `recorded_at`, not `occurred_at`, is the delta's axis.** `Event.
occurred_at` is nullable and represents in-fiction time; `recorded_at` is
always set (`_created_ts`) and represents "when the world learned of it" —
the correct axis for "since you were last here". The delta's Event query
applies the SAME structural exclusion as the only other Event reader
(`context.py`): `knowledge_status IN ('public','confirmed')` at query
construction, never by instruction. No producer writes Event rows yet — the
event leg is a deliberate forward-reader, rendering empty today and giving
the eventual event producer (TICKET-0017 territory) a perception channel on
day one.

**F5 — departed NPCs are named even if dead or deactivated since.** The
snapshot and the "current" side of the diff reuse the tick's location-scope
predicate VERBATIM (`cockpit/app.py` — NPC, alive, active, world-scoped).
The DEPARTED side resolves names from `Entity` WITHOUT that filter: the
player saw the NPC while it was still active; naming its absence now
reveals nothing new, and filtering departures to still-active entities
would silently drop real information the player already has. An id that no
longer resolves at all (hard-deleted) is silently skipped.

**Compute-then-append ordering (F7).** Inside `enter_scene`'s existing
genuine-transition guard (`if not open_g:`), after the window-analysis loop
and before `_enter_location`: the delta is computed from the PREVIOUS
`visit` row, THEN `_enter_location` runs (dissolves/regenerates gatherings —
touches only `gathering_member`, never `current_location_id`, so the
presence read is safe on either side of it), THEN the new `visit` row is
appended. A single request-scoped session, same commit discipline as the
surrounding code. Outside the guard (an F5 browser refresh) nothing
changes: `changes=None` reaches the narration unconditionally, so a refresh
narrates the scene without a delta and writes no `visit` row.

**Not canon.** `visit` is intentionally absent from `canon_write_policy.txt`'s
`CANON_TABLES` — it is written directly from `enter_scene`, the same
non-canon bookkeeping status as `gathering`/`gathering_member`. Its
append-only doctrine is enforced by a dedicated structural check instead
(`visit_delta.py` rule 1: `Visit(` constructed only in `cockpit/app.py`, no
delete, no post-construction attribute assignment) — the same mechanical
philosophy as `single_canon_write.py`, applied to a table that doctrine
doesn't cover.

**Scope OUT this brief** — carried or newly named deferrals: any Event
PRODUCER (tick lane or creator CRUD for events — the delta ships only the
reader); signpost/discoverable deltas (already re-narrated fresh via
`active_signposts` on every entry); journal UI, cross-location "world news"
digests; visit tracking for NPCs or anything but the player character;
visit pruning/retention (append-only, small rows, revisit only if
measured).

## WORLD TICK — scope-level event producer (BRIEF-0017-a, no schema change)

The `event` table existed since the founding schema with no producer and no
apply branch — TICKET-0016 gave it a reader (the return-visit delta); this
brief gives it two producers at once. Location- and faction-scoped tick
invocations gain ONE additional scope-level model call proposing
`event_creation` mutations (new prompt head `pt-world-tick-events`), and
`_apply_mutation` finally implements `event_creation` — awakening the
analyzer's dormant conversation-sourced channel (`analyzer.py:324-330`,
left "approved with a note" since the founding schema) alongside it.

**Scope shapes the briefing, never the nature of the event.** Nia's locked
correction on record: events are not creatures of factions — a storm or a
festival has no factional author. What changes between a location-scoped
and a faction-scoped tick is the BRIEFING (a place's setting and occupants,
versus a faction's posture and members), not the payload contract. An
`"npcs"`-scoped invocation produces no event call at all: an NPC does
things, it does not author world events. One button, two granularities.

**Quota = `SCOPE_EVENT_QUOTA = 3` (J1 volume by construction).** A module
constant, machine-checked the same way as `INTERVAL_HOP_RADIUS`
(TICKET-0015): items beyond the cap are dropped with a note in the R3
`scope_events` summary, never silently truncated.

**`knowledge_status`: the model proposes secret|public only; `confirmed` is
creator-reserved.** Both the scope-level normalizer and `_apply_mutation`'s
apply-time clamp (defense in depth) coerce anything else to `secret` —
except `confirmed` at APPLY time, which is accepted there because a creator
may have hand-edited the payload at review; the model itself may never emit
it.

**The canon-existence guard is extended to the conversation-sourced
channel too, not just the tick.** The 0014 guard doctrine (canon-existence
— same normalized title + same `location_id`, never tick_id/conversation
equality) already covered a re-run tick; this brief adds the identical
check to `_find_applied_duplicate`'s conversation branch for
`event_creation` specifically, bypassing that branch's usual
same-conversation scoping. Reason: awakening the dormant analyzer channel
means a `--force` re-analysis could otherwise re-emit and double-apply an
event exactly like a re-run tick could — the same failure mode needs the
same fix, regardless of which producer it came from.

**Full-interiority tick exception RE-LOGGED, extended to the faction
briefing.** The per-NPC tick briefing already reads raw `FactionMembership`
(`tick.py:189`, never `read_public_memberships`) — a conscious, logged
exception (TICKET-0014) because its output passes creator review before
anything is written. The faction-scoped event briefing sits on the SAME
creator-gated surface (every `event_creation` proposal is reviewed like any
other), so the exception extends to it: secret memberships and
`internal_tensions` are visible to the model there too. Logged here as a
conscious extension, not a silent widening.

## FACTION AGENDAS (BRIEF-0018-a, schema v1.72)

The tick stopped inventing isolated one-shots: factions now carry AGENDAS —
ordered `agenda_step` rows with states — so the faction-scoped scope-event
call (TICKET-0017) reads a plan in progress and proposes its advancement or
a brand-new intrigue, both through the same review queue.

**A1 (locked, this step): owners are FACTIONS ONLY.** `agenda.owner_entity_id`
is an FK to `entity.id` (A2-ready — a future step widens it to locations and
NPCs) but `write_agenda` validates the owner resolves to an ACTIVE
faction-type entity, raising otherwise — the write helper carries the
constraint, not the column. Doubly enforced on the read side: the
faction-scoped scope call builds an `agendas_index` (title -> id) that the
location-scoped call always leaves empty, so agenda types are structurally
unresolvable there even before the explicit `scope_type == "faction"` gate
in the normalizer fires — belt and braces, both machine-checked (rule 12,
`world_tick.py`).

**B2 (locked): the tick may propose a brand-new agenda, creator-reviewed
like everything else.** `agenda_creation` is capped at one per scope call
(first wins, later dropped with a note) and guarded by canon-existence at
apply time: duplicate iff an ACTIVE agenda already exists for the same
owner with the same normalized title. Creator CRUD (`POST /api/agendas`) is
the other authoring path, unguarded — a human choosing two similarly-titled
intrigues is not a bug.

**Title-resolution / step-derivation doctrine: the model proposes, code
judges.** The model never addresses an agenda or a step by id — it names
the agenda by TITLE, resolved against the briefing's own `agendas_index`
(unresolved -> drop with a note). The step is never in the model's payload
at all: `agenda_step_change`'s target step is always the agenda's unique
ACTIVE step, loaded fresh at normalize time (F2's partial unique index
guarantees at most one exists) — a since-closed agenda drops with a note
rather than acting on stale state. `step_id`/`agenda_id`/`owner_entity_id`
join the tick's forced-attribution field set (rule 13): no `.get(...)` read
of any of the three from a raw model payload, ever.

**Advancement is entirely code, at apply — never the model's call.**
`complete` activates the next `pending` step by `step_order`, or completes
the agenda when none remain. **`fail` fails the WHOLE agenda, no per-step
branching** (drafting decision, kept): a failed step is read as the plan
having failed, not as a detour — the creator can always reactivate a failed
step via `PATCH /api/agenda-steps/{id}` if the intrigue survives
differently in play. The apply-side guard is canon-existence (`step.status
!= "active"` -> "Needs attention", nothing written) — strictly stronger
than any tick_id key (the 0015 F6 argument, verbatim): it catches duplicate
approval, cross-run re-proposal, AND a creator having moved the world since
the tick, all in one check. `agenda_step_change` therefore needs no
`_find_applied_duplicate` clause at all.

**`agenda_creation`'s parent-child write is NOT a `resource_change`-style
exception.** One agenda plus its N ordered steps write in a single
SAVEPOINT, but this is not a second sanctioned "one-branch-two-tables"
carve-out alongside `resource_change` (`cockpit/app.py:930-936`) — a
`resource_change` genuinely touches two independent canon DOMAINS (ledger
+ knowledge); an `agenda_step` has no existence outside its parent agenda,
so writing both is one domain, two tables of the same aggregate. Step 1 is
born `active` on both authoring paths (tick-approved and creator-authored)
— the approval/authoring act itself IS the activation, kept symmetric on
purpose.

**First dedicated non-entity creator-CRUD surface.** Every prior
creator-CRUD route either composes an `entity` + its extension row or
edits an in-context child table reached from an entity's sheet
(`relation`, `knowledge`, `npc_goal`, `faction_membership`). `/api/agendas`
+ `/api/agenda-steps` is the first surface with no entity composite at all
— a bare aggregate root. Manual step reactivation
(`PATCH /api/agenda-steps/{id}`, `status: "active"`) must still respect the
partial unique index (deactivating the current active step is not a
thing — the creator completes or fails it first); the resulting
`IntegrityError` surfaces as a 409, not a 500.

**Deferred: `npc_goal` <-> `agenda_step` parentage.** A member NPC's short
goal serving its faction's active step (the F2 hierarchy engagement RECON
flagged) is the natural next chantier — no `parent_step_id` column ships
this step, by design, to avoid pre-building for a shape that isn't locked
yet.

---

## TWO-STAGE ENTITY CREATION (BRIEF-0019-a, no schema change)

The world can now GROW: the tick proposes the NEED for a new NPC, location,
or faction — a thin `entity_creation` germ, `entity_type`/`name`/`concept`/
optional `anchor` — through the same review queue as every other tick
mutation; the sheet itself is authored later, by the EXISTING pure chain
(`generate_entity_draft` + L1 goals), on the creator's own time.

**H1/I2 (locked): two stages, two checkpoints, no synchronous authoring
call.** Stage one — the model proposes the NEED; creator approval does NOT
write the entity, it PARKS the germ (`status` stays `approved`,
`creator_notes` gets "en attente de réalisation — onglet Création",
response `pending_realization`). Stage two — the Création tab's "Créations
en attente" strip lets the creator trigger sheet generation whenever she
chooses; nothing during batch/unit review ever blocks on an Ollama call for
this type. `_apply_mutation` gains no `entity_creation` branch at all — the
germ never reaches it; the approve endpoint short-circuits before the
savepoint.

**H2 (permanently rejected, not deferred): the tick never authors a full
sheet.** The 8b gameplay model proposes a one-line concept; the authoring
model (`AUTHOR_MODEL`) writes the sheet, exactly as it already does for a
creator-typed brief — entity_author.py's purity (writes nothing, ever) is
untouched, the germ just composes into the same `brief: str` shape in code.

**Realization lifecycle: `approved` (parked) -> `applied` (realized),
`created_entity_id` is the provenance stamp.** `create_entity`
(`cockpit/crud.py`) gains an optional `mutation_id`; after its OWN entity
commit succeeds, a separate guarded step (`_link_entity_creation`) loads
the mutation fresh, checks THREE guards — is `entity_creation`, is
`approved`, payload LACKS `created_entity_id` (double-commit protection) —
then reassigns `payload = {**payload, "created_entity_id": new_id}` (a JSON
column needs reassignment, not in-place mutation) and flips to `applied`.
**A guard failure NEVER rolls back the entity commit** — the entity is the
creator's hand, made through the sanctioned creator-CRUD path; a broken
linkage is a visible note, never a reason to undo her save. This is why the
pair is two separate commits, not one SAVEPOINT (the opposite shape from
`resource_change`'s two-leg exception, deliberately — here the two writes
must be allowed to diverge).

**Collision scope: ANY active entity type, asked twice.** A faction named
like an existing location is confusion, not richness, so the guard is never
same-type-only. Emit-time (`tick.py`, an actives-name index built once per
scope call, both scope types) drops a colliding name before it ever reaches
the queue; approval-time (`cockpit/app.py`, the short-circuit) re-asks the
same question fresh — canon-existence, never `tick_id` — because the world
may have moved between proposal and review (0014 doctrine, unchanged). The
creator can still rename in the pre-filled form at realization; the guard
protects the QUEUE from noise, not the creator from her own choices.

**Both scope types may propose a germ; per-NPC ticks never do.** A location
can need an occupant, a faction can need an agent — `_normalize_scope_event`
gains the branch for both `scope_type`s (unlike the 0018 agenda types,
faction-only); `_normalize_tick_item` and the per-NPC closed frozenset stay
untouched (verify rule 15). `ENTITY_CREATION_QUOTA = 1` is its own
seen-counter, outside `SCOPE_EVENT_QUOTA` and the agenda caps — the world
grows one being at a time per tick scope.

**The dormant conversation channel awakens, shapelessness tolerated, not
reformed.** `analyzer.py` has accepted `entity_creation` since before this
step but had no dedicated payload branch — its free-form germs join the
SAME pending list (`GET /api/creations/pending`, no source-type filter
beyond the type/status/unrealized query) rather than getting their own
surface. An invalid or missing `entity_type` renders visibly ("type
inconnu", no Generate action) instead of being silently dropped — the
creator sees everything the world proposed and rejects unwanted ones
through the existing queue path. `analyzer.py` itself is untouched this
step (a deliberate deferral, not an oversight).

**No `connects_to` auto-wiring, no auto faction-membership.** A realized
location germ commits with zero edges; a realized character germ commits
unaffiliated unless the creator fills the form's normal faction field — the
germ's `anchor` is prose situating the need (near/within/serves), never an
id, and never auto-resolved into a `relation` or `faction_membership` row
(region chantier 2 precedent: links are creator-confirmed, never
auto-created).

---

## GOAL<->AGENDA LINKS — B3 many-to-many, last-parent cascade (BRIEF-0020-a, schema v1.73)

Goals and agendas stopped ignoring each other. `goal_agenda_link` is a
many-to-many join at B3 grain — the link targets the AGENDA, never a step,
and a goal may serve several intrigues concurrently. The cascade is
sanctioned as a MECHANICAL, not a discretionary, act: every link on the
table passed through a `proposed_mutation` (or the creator's own CRUD)
before it existed, so code closing a goal because its last active parent
closed is judging a structure the creator already reviewed, not inventing
new canon unsupervised. `write_agenda_status` — the existing sole
status-transition helper for `agenda` — is extended in place rather than
forking a parallel cascade path; the goal-side transition still runs
through `write_npc_goal_status` (the sole `npc_goal` status chokepoint),
so the cascade adds no second way to move a goal, only a new caller of the
one that exists. The cascade fires on ANY exit from `active` — tick
approval AND creator override alike — a deliberate consistency: if the
creator's manual close cascades, the model's approved close must too, or
"why did closing it my way work differently" becomes a support question.

**E2+M1 mapping is a vocabulary compromise, not a new state.** `npc_goal`
has no `failed` (M3 was rejected at intake) — `agenda.status='failed'` and
`'abandoned'` both map to `npc_goal.status='abandoned'`; only `'completed'`
maps to `'completed'`. The distinction between "the intrigue failed" and
"the intrigue was abandoned" survives on the AGENDA row (still readable via
its own `change_history`); the goal's own history only needed to know it
stopped being pursued, and gets exactly that, tagged
`cascade:agenda:<id>:<status>` so the full agenda outcome is one join away,
never lost.

**Last-parent rule is a survival check, not a priority order.** A goal with
two active links (two intrigues it serves) is not "primarily" owned by
either — closing ONE of its parents only ends the goal if that was the
LAST one still active. The check queries the goal's OTHER active links at
cascade time (not a cached count), so it is correct regardless of how many
agendas were closed earlier in the same transaction or session.

**No cascade on detach.** Soft-detaching a link (creator-only, BRIEF-0020-c)
never touches the goal — detach is a correction to the graph, not an
agenda-status event; only a genuine `active -> {completed,failed,abandoned}`
transition on the AGENDA fires the cascade.

## ONE-ACTIVE-PERSONAL-AGENDA — character owners, guard placement (BRIEF-0020-a, schema v1.73)

`write_agenda`'s owner check unlocks `character`-type entities alongside
`faction` — an NPC may now OWN an intrigue, not just serve one. The
one-active-personal-agenda invariant (at most one active agenda per
character owner) is enforced with an explicit existence query inside
`write_agenda` itself, the same tier as the pre-existing
faction-vs-location type check in that helper — a code guard in the sole
canon-write path, never a database CHECK/UNIQUE constraint. This mirrors
the 0018 faction-type guard's placement rather than reaching for a new
mechanism: `agenda.owner_entity_id` has no type discriminator column to
build a partial index against (owner ROLE is not owner TYPE), so the
structural options available to `faction_membership`/`agenda_step`
(a `sqlite_where` partial unique) don't apply here without denormalizing
the owner's type onto the row — deliberately not done, since the helper
already sees the owner's `Entity.type` on every call. Faction owners are
explicitly UNCHANGED: their multi-agenda freedom is a regression the
Done-means checklist tests for, not an oversight.

## FORWARD NOTE — per-NPC agenda contract extension (BRIEF-0020-a, no schema change)

This step (BRIEF-0020-a) ships schema and writes only: no reader, no tick
mutation type, no prompt change. The per-NPC tick contract's extension
(`_TICK_MUTATION_TYPES` gaining `agenda_step_change`/`agenda_creation`,
scoped to agendas the NPC owns) and the faction-scope `agenda_delegation`
type are logged as their own decision entries by BRIEF-0020-b when they
land — this note exists so a reader of this entry knows where to look
next, not to duplicate that record here.

## PER-NPC AGENDA CONTRACT — evolution of the 0017 closed contract (BRIEF-0020-b, no schema change)

The per-NPC tick contract's "closed, faction-scope-only" doctrine for
`agenda_step_change`/`agenda_creation`, stated at BRIEF-0018-a and
mechanically enforced since, is SUPERSEDED here — on the record, not by
drift. The exact claim this entry supersedes, verbatim from
`tooling/verify/checks/world_tick.py`'s prior Rule 12:

> Rule 12 (closed per-NPC contract stays closed, TICKET-0018/BRIEF-0018-a):
> the strings `"agenda_step_change"`/`"agenda_creation"` appear inside
> `_normalize_scope_event` but NEVER in `_normalize_tick_item` /
> `_TICK_MUTATION_TYPES` / `_TICK_TYPE_ALIASES` — the scope-level agenda
> types are a `tick.py`-only, faction-scope-only extension of the SCOPE
> contract, never the per-NPC one.

That claim was true and correct for BRIEF-0018-a's scope — it simply
predates BRIEF-0020-a's NPC-owned agendas (an NPC couldn't own an agenda
yet, so there was nothing per-NPC to advance). Now that a `character` can
own an ACTIVE agenda (0020-a), the closed contract widens: `_TICK_
MUTATION_TYPES` gains both types, but through a STRUCTURALLY SEPARATE door
from the scope one. `_normalize_tick_item`'s two new branches resolve an
agenda title ONLY against a per-NPC `agendas_index` the caller
(`run_world_tick`) builds by querying `Agenda.owner_entity_id == npc_id` —
never the faction/scope index, never widened to agendas the NPC merely
SERVES via a `goal_agenda_link` (owning and serving stay structurally
distinct query paths). `agenda_creation`'s `owner_entity_id` is FORCED to
`npc_id`, joining the same forced-attribution family as `npc_id`/
`entity_a_id`/`owner_entity_id` (scope) — never read from the model's
payload, verified by the SAME rule 13 that already covered the scope
branch (the check is file-wide, not per-function). A second layer of the
0014 tick-guard doctrine applies twice over: `_normalize_tick_item` itself
drops a second `agenda_creation` at normalize time (canon-existence: the
NPC already owns an active agenda), and `run_world_tick`'s per-item loop
caps it at one per call (mirroring the scope loop's `agenda_creation_
emitted` flag) — catching, respectively, a re-run tick and two creations
proposed in the SAME call before either is canon. `world_tick.py`'s Rule
12 is rewritten to assert the OPPOSITE of its original claim (presence,
not absence) in `_TICK_MUTATION_TYPES`/`_normalize_tick_item`; a NEW Rule
20 asserts the owner-restriction structurally (an `Agenda.owner_entity_id
== npc_id` comparison inside `run_world_tick`).

`agenda_delegation` (faction scope only — the mechanism by which a faction
tasks a MEMBER, never itself, with a goal serving one of its own active
intrigues) stays on the ORIGINAL side of the 0017/0018 doctrine: never
enters the per-NPC contract, isolated by a new Rule 19 (twin of rules 9/15,
same isolation shape as `event_creation`/`entity_creation`). Delegation
writes a `NpcGoal` + `GoalAgendaLink` in one SAVEPOINT — the 0018
`agenda_creation` parent-child-aggregate precedent, not a
`resource_change`-style two-domain exception — after re-validating at
apply (canon-existence, 0014 doctrine) that the agenda is still active and
the NPC holds an ACTIVE `FactionMembership` (secret OR public — a faction
may task a secret member) in the agenda's owner faction.

`goal_change` (create_short, per-NPC path only) gains an optional
own-agenda reference: an `"agenda"` title, resolved against the SAME
owner-restricted index and written as `agenda_id` in the normalized
payload. Unlike the two new mutation types, an unresolved title never
drops the goal_change itself — the reference is an enrichment (the NPC
started a short goal that happens to serve its own intrigue), not a
requirement; only the key is dropped, with a note. At apply
(`cockpit/app.py`), a `write_goal_agenda_link` failure (e.g. the agenda
closed since the tick) is NOT pre-validated separately — it raises
`ValueError`, caught and returned as a string (keeping `_apply_mutation`'s
"never raises" contract intact), and the caller's outer `db.begin_nested()`
SAVEPOINT rolls back the just-inserted goal along with it: a rejected link
means no goal either, achieved by relying on the existing rollback
mechanism rather than adding a second validation pass (the brief's O1 note
explicitly sanctioned either approach; this is the mechanically simpler
one).

## D1 DIALOGUE PROVENANCE — second sanctioned faction_membership reader (BRIEF-0020-b, no schema change)

Dialogue goals may now show WHY they matter — but only when the NPC is
allowed to reveal it. `read_public_membership_faction_ids` joins
`read_public_memberships` as the second, and ONLY other, code path through
which `faction_membership` may ever reach a model prompt: identical
structural WHERE triplet (`entity_id` match, `left_at IS NULL`,
`is_secret == False`), no parameter exists to opt into secret rows on
either accessor. `_goal_provenance_suffix` (`context.py`) renders a goal's
` (sert : « <title> »)` suffix IFF the serving agenda's owner is the NPC
itself (its own intrigue — always visible, no gate needed, since it can't
leak anything the NPC doesn't already know about itself) OR the owner
faction id is in that set — a link failing the gate contributes nothing,
and the goal renders exactly as it did before this brief, bare. This is
query-mechanical, never an instruction: the model is never shown a
provenance it must be told to withhold, because the excluded titles are
never assembled into the prompt in the first place (the same
exclusion-not-restraint doctrine `context.py`'s module docstring states
for secrets). `tooling/verify/checks/npc_goal_read.py` gains a Rule 3
asserting `_goal_provenance_suffix` both calls the new accessor AND
contains an `owner_entity_id == npc_id` comparison — the two-part gate is
structurally present, never collapsed to an unconditional render.

This is deliberately narrower than the TICK briefing's equivalent
suffix (`tick.py`'s `_goal_provenance_suffix`, BRIEF-0020-a's cascade
made this readable, BRIEF-0020-b added the render): the tick briefing is
FULL interiority (T1, BRIEF-0014-a) — secret-faction agendas ARE shown
there, same tier as the affiliation block's `[AFFILIATION SECRÈTE]` rows
— because the NPC is judging its own situation, not talking to someone
who might not be owed the truth. Dialogue has an interlocutor; the tick
does not. Two functions, same name, deliberately different gates —
documented here so the asymmetry reads as intentional.

## AI AGENDA-DRAFT ASSISTANT (BRIEF-0021-b, no schema change)

Fills the empty `#agenda-gen-panel` placeholder BRIEF-0021-a shipped: the
creator selects an owner, types a one-sentence intent, and the assistant
pre-fills the create shell — title + 2-to-5 steps. Locked pre-brief: **B1**
— standalone sibling generator (`generate_agenda_draft`, the
`generate_npc_goals` precedent), NOT a `_TYPE_FIELDS` entry, since agendas
are not `entity` rows; **C1** — draft content is exactly title + steps,
mirroring the manual form (**C2**, suggested goal-name links, stays
deferred — no design for goal-name resolution yet); **D1** — the creator
selects the owner FIRST, the model never proposes or names it (**D2**
rejected).

**Server-side D1 resolution mirrors `write_agenda`'s own gate.**
`POST /api/agendas/generate` 404s a missing owner and 422s one that is
inactive or not `faction`/`character` — the exact rule `write_agenda`
enforces — so the assistant can never draft toward an owner the create
would then reject. `owner_context` is assembled from PUBLIC columns only
(`Entity.description` + `Faction.philosophy` for a faction;
`Entity.description` + `Character.backstory` for a character, each part
dropped when empty, `"(aucune description)"` when both are) — secrets stay
structurally excluded: no `knowledge` row, no `character.secrets`, no
`internal_tensions` is ever read by this route.

**`generate_agenda_draft` writes nothing** — mechanically gated by the new
`tooling/verify/checks/agenda_assist.py`, which AST-scans the function
body for `writes.`/`session.add`/`db.add`/`.commit(` (none present) and
asserts the `pt-agenda-draft` seed shape and the route's registration. The
only write remains the creator's existing `POST /api/agendas` accept.

**Prompt wiring closes a gap this brief's own review pass caught:** the new
`usage="agenda_generation"` seeded in `seed_pilot.py` needs a
`PROMPT_REGISTRY` entry (BRIEF-0008-a's bijection gate,
`tooling/verify/checks/prompt_registry.py`) — added mirroring
`npc_goal_generation`'s exact shape (`surface="authoring"`,
`world_scoped=False`, `default_model=_author_model`).

**One-shot, not conversational (F2 precedent).** A second click on
« Générer » overwrites title and all five step fields with the new draft —
no incremental refine, matching BRIEF-24's established assistant idiom.

## ÉVÉNEMENTS — CREATOR SURFACE (BRIEF-0022-a, no schema change)

`event` had been written since TICKET-0017 with no creator surface at all —
no `/api/events` route, no occurrence of "événement" in `index.html`. This
brief gives it a Création page on the standard entity page contract and
opens the second sanctioned `event` canon-write path.

**Third non-entity reader of the `sheetRenderer` seam** (after `agenda` —
TICKET-0021, and the shell's own registry generalization), reusing it
verbatim: `archetype: 'entity'`, `containers: ['creation-editor-area']`,
`listLoader: loadEventsList`, `listRenderer: renderEvenementsListRows`,
`sheetRenderer: renderEventSheet`, `createPanel: evenementsRenderCreatePanel`.
No shell change was needed — the seam TICKET-0021 built already covers this.
**A3** (full data-source abstraction of the shell) stays deferred.

**`saveHandler` — the registry seam extended.** Unlike Intrigues (no save
control at all — status transitions only), Événements needs an edit save,
but `authorSave` is entity-only (writes through `ENTITY_TYPE_REGISTRY`) and
must not learn about non-entity rows. The static `#author-save-btn`'s
`onclick` moved from `authorSave()` to a new `creationSaveDispatch()`, which
resolves `(entry.saveHandler || authorSave)()` off the registry — the same
`sheetRenderer`-style default-to-existing-behavior seam, so every other
entity-archetype tab (which declares no `saveHandler`) is unaffected.
`CREATION_TABS.evenements.saveHandler = evenementsSave`, which `PUT`s
`/api/events/{id}`.

**Second sanctioned `event` writer: `write_event_update`** (`writes.py`).
`write_event` (creation) is shared between `_apply_mutation`'s
`event_creation` branch and the new `POST /api/events`; `write_event_update`
is creator-CRUD-only — `_apply_mutation` never calls it, since AI proposals
create events, never edit them. Together they are the complete, closed set
of `event` writers, mirroring the `write_relation`/`write_knowledge`
two-path doctrine already established for other tables.

**C3 — no deletion, ever.** An event either happened or did not; `event` is
history. Retraction is `knowledge_status = 'secret'`, which structurally
excludes the row from all four readers (`context.py`'s MJ world context,
`tick.py`'s location and faction briefings, `app.py`'s return-visit delta) —
mirroring `ledger`'s append-only policy. No `DELETE /api/events` route, no
soft-delete column, no UI control; `tooling/verify/checks/event_tab.py`
gates this structurally.

**Accepted gap: no `change_history` on `event`.** `write_event_update`
overwrites `title`/`description`/`type`/`knowledge_status`/
`involved_entities`/`location_id` in place with no prior-state append — the
table has no `change_history` column to append to. Documented here so the
omission reads as deliberate (consistent with "history is sacred" applying
to `relation`/`knowledge`, which do carry that column), not forgotten.

**One vocabulary per column.** `EVENT_TYPE_LABELS_FR` (`crud.py`) is keyed
verbatim off `tick._EVENT_TYPES` — imported, never re-typed — with a
module-load `assert` so the two vocabularies cannot silently diverge; the
tick already clamps model proposals onto the same set (`tick.py:877`).
`type` stays a free-text `datalist` column: the seven are suggestions, not
a constraint.

**`rumor` rejected on `event` (R1).** `context.py`'s docstring wrongly
named a `rumor` `knowledge_status` that exists in no code path (`app.py`
clamps to `secret|public|confirmed`); corrected to name `secret` only. An
event's occurrence is binary; uncertainty about it belongs on
`knowledge.level = 'rumor'`, never on `event.knowledge_status` — putting
`rumor` here would blend canon with belief.

**Defect fix: `context.py`'s public-events ordering.** `occurred_at` is
written by nobody (`write_event` leaves it `None`), so ordering by it
(RECON finding 7) was the database's arbitrary return order. Now orders by
`recorded_at DESC`, aligning with `tick.py` and `app.py`'s return-visit
delta. The `"occurred_at"` key stays in the emitted prompt dict — reserved
for the deferred in-fiction-time chantier below — it just stops governing
sort order.

**Deferred: "Temporalité des événements."** `occurred_at` and any
`passé | en_cours | à_venir` status are ONE future chantier, not two — a
"future" event is simply one whose `occurred_at` lies ahead of world time —
so splitting them now would cost two migrations where one later suffices.
Nothing in this brief anticipates it.

## AI EVENT-DRAFT ASSISTANT (BRIEF-0022-b, no schema change)

Fills the empty `#event-gen-panel` placeholder BRIEF-0022-a shipped: the
creator types a one-sentence intent, optionally pre-selects a location, and
`generate_event_draft` pre-fills the create shell — title, description,
type, location, involved-entity chips. Third instance of the
standalone-sibling-generator shape (`generate_npc_goals`,
`generate_agenda_draft`, `generate_event_draft`) — a shared abstraction is
now *one* case away and is deliberately NOT built yet.

**`knowledge_status` is structurally absent from the model contract.** No
key in the prompt, none read from the parsed response, none in the
returned dict — even if the model volunteers one, it is silently discarded
(not noted; noting it would invite the creator to honour it). This is the
single most counter-intuitive point of the brief: the model may invent an
entire event, but never decides whether the world knows about it. It is
also what makes C3 (BRIEF-0022-a's no-deletion doctrine) livable —
`knowledge_status` is the creator's only lever, so it can never be
model-authored. `tooling/verify/checks/event_assist.py` gates this
structurally (scans the function body, docstring excluded, for the
substring).

**`build_world_roster` (`entity_author.py`) — the J3 assembler.** Filters
`is_public IS TRUE` and `status = 'active'` in the `where(...)` clause
(query construction, never a Python post-filter) — the pattern
`context.py:615` does NOT follow (it post-filters `is_public` in Python
after the query); that divergence is logged here as one to correct
opportunistically, not fixed in this brief (play-path code, out of scope).
Only `name`/`type` leave the function; `internal_name` is never selected.
Ambiguity discipline is reused from `tick.py:_build_roster` verbatim: two
active public entities sharing a casefolded name are both dropped from the
roster rather than guessed at.

**Name→id resolution is reused, not extracted.** The `involved_entities`
loop is `tick.py:889-897`'s shape, copied rather than shared — a third
near-identical usage (`tick.py:889`, `tick.py:1114`, this one) with three
different roster scopes (location, faction, world). Minimal-first:
generalize on a fourth.

**The pre-selected location wins outright over the model's own proposal.**
When the creator has already chosen a location before generating,
`location_hint` overrides `parsed["location"]` entirely; a disagreement is
noted, never silently swallowed. Known narrow gap: `location_hint`
resolves back to an id through the same public-only `roster`, so a
pre-selected location that is itself `is_public = FALSE` would fail to
resolve and silently drop the creator's own selection. Not fixed here
(would need a second, non-roster resolution path for the hint case) —
flagged for whoever next touches this function.

**Server-side context assembly, not client-side.** `POST /api/events/generate`
(app.py) builds `location_context` from the location entity's `name` +
`description` only (public fields — never `internal_name`, never
`metadata`) and calls `build_world_roster` before delegating to
`generate_event_draft`. The route itself writes no canon; the only write
remains the creator's existing `POST /api/events` accept (BRIEF-0022-a).

**One-shot, not conversational (F2 precedent).** A second click on
« Générer » overwrites the whole shell — title, description, type,
location, and chips — with the new draft, matching the established
assistant idiom (BRIEF-24, BRIEF-0021-b).

## ON-DEMAND GRAPH SLOTS + CYTOSCAPE VENDORING (BRIEF-0023-a, no schema change)

Two pieces of groundwork for TICKET-0023's NPC relation ego-graph, which is
the slot mechanism's second concrete reader (TICKET-0005, "Graph-as-slot
posture" — generalization was deferred exactly until this point).

**Slot contract gains `display: 'always' | 'on_demand'`, default `'always'`.**
Today's behavior (every slot's container visible and its `loader` firing on
tab activation) is the unchanged default for undeclared slots — `pj`'s
`fiche` slot and `queue`'s `filters` slot are zero-diff. `'on_demand'`
means: container hidden and `loader` skipped on tab activation; the
standard shell (`renderCreationShell`) renders one toggle button per
`on_demand` slot in the same fixed band position on every tab, mirroring
`primaryAction`'s posture; first click shows the container and fires
`loader` once; later clicks only hide/show (no unload, no refetch); state
is tracked in `onDemandSlotState` (keyed by `containerId`) and reset by the
owning tab's `onTabEnter`/`onWorldSwitch` — never persisting across a tab
re-entry or world switch. `_creationActivateTab` and `showCreationSubTab`
branch on this slot DATA, never on a tab id — the 0005 doctrine extends
unchanged to the new field.

**Lieux's graph slot is the first to declare `on_demand`.** Nia does not
want any graph permanently displayed (Lieux or NPC). The Lieux graph
component itself (`graphLoad`, `graphRender`, drag, edge click/delete, its
markup and CSS) is byte-untouched — `relation_graph.py` (BRIEF-0023-b)
enforces this. Only its registry declaration changed.

**Cytoscape.js is vendored, not CDN'd.** The cockpit is a loopback-only,
offline creator tool (CLAUDE.md); a CDN `<script>` tag would silently break
without internet access. `cytoscape-3.34.0.min.js` (exact upstream minified
UMD build, MIT-licensed, version pinned in the filename per H1) is
committed under `src/world_engine/cockpit/vendor/` and served by one
whitelisted route (`GET /vendor/{filename}`, 404 on any other name) — no
`StaticFiles` mount, which stays deferred until a second vendored asset
justifies the generalization (minimal-first, same posture as every other
"wait for a second reader" call in this codebase). The hand-rolled SVG
idiom the Lieux graph uses today was deliberately not extended: Nia's own
words are that graphs "will complexify" going forward, and cytoscape gives
pan/zoom/click/recenter for free — the Lieux graph's own migration to
cytoscape is an explicit future ticket, not part of this one.

---

## TICKET-0024 INTAKE DECISIONS — completion mechanics (BRIEF-0024-a, BRIEF-0024-b, BRIEF-0024-c, schema v1.74)

Goal/agenda completion stopped being purely declarative. Nia's own
taxonomy split the problem in three: (1) **prerequisite mechanics** — a
claimed state change ("gained X's trust") must be grounded in canon before
the model may complete the goal; (2) **consequence mechanics** — a
completion may move relation, money, or a role; (3) some
events/objectives legitimately live in prose only, with zero mechanical
footprint. The three briefs of this ticket ship, in order: schema +
creator surface (-a), the prerequisite judge + tick briefing (-b), and the
completion effects (-c). One-line record per intake decision, full detail
on the two named doctrine events (H1, K1/L2) lands in BRIEF-0024-c where
the code does:

- **A1** — Effects are optional-but-solicited on completion; zero
  prerequisites and zero effects is legitimate (Nia's type 3), tagged
  `no_footprint` in `change_history`.
- **B1** — Effect vocabulary v1 is closed: `relation_delta`,
  `ledger_transfer`, `role_change`. One type per concrete named case;
  expand only at a second concrete case.
- **G1** — Prerequisites: optional `prerequisites` JSON on `npc_goal`, v1
  type `relation_gte` (target entity + 1-100 threshold), creator-CRUD
  authored only, judged in code at `goal_change complete` — unmet is a
  whole-mutation reject with the measured gap; the per-NPC tick briefing
  shows resolved prerequisite state so the model does not loop on doomed
  completions.
- **H1** — Anti-double-count is *strip*, not reject: a `relation_delta`
  effect on the same entity pair as a satisfied `relation_gte`
  prerequisite is silently removed, the rest of the mutation applies, a
  note is recorded — the project's first sanctioned partial application of
  a mutation (0020 all-or-nothing precedent), strictly bounded to this one
  case.
- **I1** — `role_change` requires an ACTIVE membership in the named
  faction; joining/leaving a faction is NOT an effect in v1
  (`membership_change` deferred).
- **C2/J1** — Role capacities live on `faction.role_capacities` (JSON),
  edited via a line editor (number limit + role name) in the Faction tab;
  empty limit = unlimited; capacity counts ACTIVE memberships bearing the
  true `role`, never `cover_role`; full is a reject, never an eviction.
- **K1** — The declared role list is a CLOSED vocabulary for the AI path
  only: an undeclared role in a `role_change` is rejected (exact
  case-insensitive resolution, gathering-role precedent); creator CRUD
  stays free-form.
- **L2** — The model may declare-and-occupy a NEW role in one completion
  via `declare: true`; a role is never created without a holder —
  declaration and occupation are atomic in the same SAVEPOINT; a newly
  declared role's capacity is always empty (unlimited), only the creator
  sets limits thereafter.
- **M1** — Ledger rows written by completion effects carry
  `source_type='tick'` (new documented enum value).
- **N1** — Max 3 effects per completion; more is a whole-mutation reject.
- **E1** — Nothing is declared at goal creation; effects are decided at
  completion time (structured stakes-at-creation deferred).
- **F** — Both surfaces carry effects: `goal_change complete` AND
  `agenda_step_change complete`. Effects apply on `complete` only — never
  on `fail` or `abandon`.

---

## PREREQUISITE JUDGE (BRIEF-0024-b, no schema change)

"Model proposes, code judges." The judge lives inside `_apply_mutation`'s
existing `goal_change` branch — a gate on `complete` only, never a new
write path — and is fail-closed: an unrecognised prerequisite type
rejects the whole mutation rather than skipping the check, because the
column is creator-authored and a hand-written row could still be
malformed. The per-NPC tick briefing resolves the SAME prerequisites to
live state and injects one line per prerequisite so the model does not
propose doomed completions in a loop; resolution never triggers anything
by itself — satisfaction is not auto-completion, the model still
proposes and Nia still approves. Both the judge and the briefing resolve
a goal's `relation_gte` pair through the SAME extracted helper,
`writes._find_relation_pair` (previously inlined in
`write_relation(mode="delta")`) — one source of pair semantics so the
judge and the briefing can never disagree about "the" relation for a
pair.

---

## FACTION ROLE TABLE — corrective, JSON to relational (BRIEF-0024-d, schema v1.76)

0024-d corrective — roles promoted from JSON (`metadata.roles` +
`role_capacities`) to relational `faction_role`: creator doctrine
"UI-visible data lives in columns and tables, not JSON blobs" (global
blob-extraction hunt = future ticket); case-uniqueness moved from code
check to unique index; S1 guarded hard delete; T1 rename realigns active
memberships only.

A RECON-after-the-fact found BRIEF-0024-a built `faction.role_capacities`
unaware of the pre-existing declared-role structure,
`entity.metadata['roles']` (BRIEF-31, schema v1.42) — the faction sheet
carried two disconnected role vocabularies. The fix merges both into one
table rather than picking a survivor: metadata-role entries keep their
array order and description; `role_capacities` limits merge in by
casefold name match; a capacity-only key becomes a new row. The migration
validates every faction in a read-only pass before writing anything — a
casefold collision inside one faction's own sources aborts the WHOLE
migration with a readable list, never a partial write.

**Lesson, recorded verbatim in CLAUDE.md's RECON section:** "RECON: trace
every UI-visible field to its storage, including `entity.metadata` JSON
keys — grepping columns is not sufficient."

**This entry SUPERSEDES C2/J1 of "TICKET-0024 INTAKE DECISIONS"** — on the
record, not by drift. The exact claim it supersedes, verbatim: "Role
capacities live on `faction.role_capacities` (JSON), edited via a line
editor (number limit + role name) in the Faction tab." Capacity counting
against the true `role` (never `cover_role`) and "full is a reject, never
an eviction" both carry forward unchanged onto `faction_role.max_holders`.

---

## NPC_PRICE HARD-DELETE NAMED EXCEPTION (BRIEF-0025-a, schema v1.77)

`npc_price` follows the `faction_role` curated-config doctrine: no
`change_history` column, full-replace writes (`writes.write_npc_prices`
deletes every existing row for the entity, then inserts one row per
`{tag: amount}` pair). The prior rows' hard delete is a NAMED exception to
"history is sacred" — tariff lines are seller configuration, not event
canon, and carry no narrative audit requirement. `character.physical_tier`
and `npc_price` replace `entity.metadata['physical_tier']` and
`entity.metadata['price_list']` (BRIEF-20); this is the first corrective
step of TICKET-0025 (motivated by the TICKET-0024 duplication bug — see
"FACTION ROLE TABLE" above). The full TICKET-0025 decision record —
locked options, the `json_ui_boundary` verify check, and the exception
registry — lands with BRIEF-0025-c.

---

## SUBCULTURE HIDDEN SLICE — structural exclusion (BRIEF-0025-b, schema v1.78)

`location.subculture`'s `hidden` key moves from a JSON blob key
cohabiting with public keys to a `location_subculture` row carrying its
own `is_hidden` flag. The hidden slice is now structurally excluded: every
non-creator reader (`context.py`'s NPC setting line and MJ perception
slice, `tick.py`'s two location-briefing readers) filters `is_hidden =
FALSE` at query construction, never as a post-filter on a fully-fetched
dict and never as a prompt instruction — the same doctrinal payoff C1
(TICKET-0025 intake) named for this table. `character.secrets` (B1) and
`location.coordinates` -> `coord_x`/`coord_y` (A1) land in the same brief
as plain-type/column moves with no structural-exclusion story of their
own (secrets has no reader at all; coordinates was never secret).
`world.fundamental_laws` -> `world_law` (D1) resolves the pre-existing
string-vs-array shape split between the manual create form and the AI
draft into one relational, position-ordered shape.

---

## TICKET-0025 — UI-VISIBLE DATA IS NEVER STORED IN JSON (BRIEF-0025-a, BRIEF-0025-b, BRIEF-0025-c, schema v1.79)

**The rule.** No UI-visible field is ever backed by a JSON column. Every
field a creator can see or edit lives in a plain typed column or a
relational table. The rule is enforced structurally, fail-closed, by
`tooling/verify/checks/json_ui_boundary.py` — not by convention, not by a
CLAUDE.md note that a future ticket can miss.

**The incident that motivated it.** TICKET-0024's RECON pass built
`faction.role_capacities` unaware of the pre-existing
`entity.metadata['roles']` structure (BRIEF-31) — RECON traced columns,
not JSON keys inside `entity.metadata`, and missed that a second,
disconnected role vocabulary already existed on the same sheet.
BRIEF-0024-d corrected the immediate duplication and added a RECON lesson
line to CLAUDE.md ("trace every UI-visible field to its storage, including
`entity.metadata` JSON keys"). Nia judged a prose lesson insufficient — a
future RECON could miss it exactly the same way. TICKET-0025 is the
structural fix: a verify gate that fails the build the moment a new
`"kind": "json"` field or an unlisted `Column(JSON` appears, independent
of whether anyone remembers the lesson.

**Locked options (intake).**
- **A1** — `entity.metadata['physical_tier']` -> `character.physical_tier`
  column; `entity.metadata['price_list']` -> `npc_price` table;
  `location.coordinates` -> `coord_x`/`coord_y` columns.
- **B1** — `character.secrets` -> plain TEXT column; no reader ever
  consumed structure, so no relational shape is needed, just a type
  change.
- **C1** — `location.subculture` -> `location_subculture` table with an
  `is_hidden` flag; the secret slice becomes structurally excluded (query
  construction) instead of cohabiting with public keys in one JSON blob.
- **D1** — `world.fundamental_laws` -> `world_law` table, position-ordered
  rows; resolves the pre-existing string-vs-array shape split between the
  manual create form and the AI draft.
- **E1** — `npc_goal.prerequisites` -> `goal_prerequisite` table (closed
  vocabulary, CHECK-constrained); `event.involved_entities` ->
  `event_entity` link table (real FK integrity for the first time —
  the JSON array had none); `prompt_template.variables` ->
  `prompt_variable` table.
- **F1** — the raw "Metadata (JSON)" form field is removed and
  `entity.metadata` itself is dropped once emptied (BRIEF-0025-a).
- **G1** — the fail-closed verify check `json_ui_boundary.py`: CRUD
  registry volet (zero `"kind": "json"` fields), source-access volet (zero
  `metadata_`/`Column("metadata"` outside comments), JSON-column volet
  (every `Column(JSON` in `models.py` is a named, justified allow-list
  entry). A volet that parses to zero findings is itself a FAIL — a
  parser that finds nothing is broken, not a clean repo (run.py doctrine,
  reused here).
- **H1** — three briefs: -a (metadata keys + `entity.metadata` column
  drop), -b (dedicated JSON columns on entity extensions + world), -c
  (structured editors + boundary check + this decision record).

**The exception registry.** `JSON_COLUMN_ALLOWLIST` in
`json_ui_boundary.py` is the single source of truth — this table mirrors
it for narrative context only; the check file is authoritative.

| Column | Why it's exempt |
|---|---|
| `ProposedMutation.payload` | Polymorphic model-proposal envelope, rendered readonly in the review queue; shape is the mutation type's contract, not a UI field. First structured UI consumer must relationalize. |
| `Relation.change_history`, `Knowledge.change_history`, `NpcGoal.change_history`, `Skill.change_history`, `Agenda.change_history`, `AgendaStep.change_history` | Append-only audit snapshots — never rendered in any UI surface. |
| `PassPlay.injected_context`, `PassPlay.history`, `Conversation.injected_context`, `Conversation.scene_state`, `Visit.present_npc_ids` | Internal engine snapshots — never rendered in any UI surface. |
| `Event.consequences`, `Artifact.known_properties`, `Artifact.actual_behavior` | No UI consumer today. The FIRST UI consumer of any of these MUST migrate it to relational storage in the same brief that adds the consumer. |

**The standing consequence.** Adding a new JSON column to `models.py` now
requires editing `JSON_COLUMN_ALLOWLIST` in the same commit — a visible,
reviewable diff in code, never a silent convention. `json_ui_boundary.py`
fails closed on both directions: an unlisted `Column(JSON` fails, and a
stale allow-list entry whose column no longer exists also fails —
exceptions rot loudly, not silently. Verified with three negative-test
fixtures at brief-exec time: a scratch `"kind": "json"` CRUD field, a
scratch unlisted `Column(JSON)`, and a stale allow-list entry each
independently make the check fail, naming the offending field/column.

**Deliberately out of scope.** No extension of `single_canon_write.py` or
`canon_write_policy.txt` to cover the new curated-config tables
(`npc_price`, `location_subculture`, `world_law`) — a separate,
already-flagged policy question, not this ticket's job. No new
prerequisite types beyond `relation_gte`. No relationalization of the
Group 4 allow-list columns — that is the allow-list's entire point.

---

## MIGRATION VALIDATOR CORRECTION — subculture shape (BRIEF-0025-d, no schema change)

**The incident.** `migrate_v1_78_dedicated_json_columns.py` (BRIEF-0025-b)
never applied on the live DB: its fail-closed validation rejected 37 of 42
locations with a non-NULL `subculture` blob, because BRIEF-0025-b's RECON
mischaracterized the real shape as "flat dict of string/number values." A
read-only census of the live DB (2026-07-13, all 52 locations, 11 distinct
shapes) established the actual shape: a flat dict over a fixed 4-key
vocabulary (`hidden` / `values` / `magic_phenomena` / `nexus_link`), each
value `str | bool | list[str]`. No nested dicts exist anywhere. The data
was sound; the migration's validation and coercion were wrong.

**The fix (A1).** The validator now accepts any flat dict whose values are
`str | bool | int | float | list[str]`; coercion to `location_subculture
.value` (TEXT) is purely representational: str unchanged, bool ->
`"true"`/`"false"`, int/float -> `str(value)`, list[str] ->
`", ".join(items)` (empty list -> no row). Zero data edits (A2 rejected —
the data is the source of truth, the validator was wrong).

**Migration coercion is representational, never editorial (B1).**
Migrations may change representation (bool -> text, list -> joined text)
but must never drop or rewrite values on semantic grounds (B2 rejected:
`false` migrates as `"false"`, `["none"]` migrates as `"none"` — no
silent cleanup). Content judgment belongs to the creator, post-migration,
in the UI.

**Standing lesson.** Migration validators must be grounded in a census of
live data, not an assumed shape — a RECON that infers a JSON shape from
schema/code alone (rather than querying the live rows) can pass review and
still be wrong; the fail-closed validator caught the mismatch before any
data was touched, exactly as designed.

---

## CODE STANDARDS v1 SEEDING (BRIEF-0027-a, no schema change)

**The trigger.** 26 tickets closed; Nia asked for a one-time architecture
SEEDING review of the codebase against `tooling/improvement/bug_log.jsonl`
and ticket history (RECON-0027), to see whether a first `code_standards.md`
was warranted, plus a follow-up: cap not just function length but the
number of functions in a single file (`cockpit/app.py` at 103 functions).
RECON-0027 confirmed four risk zones: monolith concentration (`say` 1130
lines / nested `_stream` 958, `_apply_mutation` 682, `run_world_tick` 421),
duplicated LLM-output parsing (24 `json.loads` sites across 8 modules, the
exact failure class behind the 2026-07-03 subculture bug), logging
inconsistency (38 `print()` sites invisible to log capture), and an
ungoverned frontend. `code_standards.md` v1 is deposited from that review;
this brief ships its enforcement.

**A2 — document scope.** Ratify the emergent norms already held
unwritten (return-type annotations, no bare `except`, `select()` over raw
`text()`, SAVEPOINT atomicity, English-only strings) alongside corrective
rules targeting the four risk zones — not a green-field style guide.

**B2 — two-tier enforcement.** Every rule is tagged `enforced` (a
dedicated fail-closed `tooling/verify/checks/` script) or `advisory`
(reviewed at `/review-step`, no automated check); an advisory rule
violated twice across distinct tickets becomes a promotion candidate.

**C2 — legacy violations are remediated, not grandfathered.** TICKET-0027
refactors the flagged code itself (staged briefs b–g); the R1/R5 transition
baselines shipped in this brief exist only so the four checks can go live
*before* that refactor lands. Baseline entries may only shrink or
disappear, and the files are deleted outright at stage g — a permanent
exemption was never on the table.

**D2 — frontend stays lightly governed.** `cockpit/index.html` (8.8k
lines, ~350 JS functions) gets an advisory-only section (F1–F3);
`page_contract.py` remains the sole frontend check — no new machine gate
on the frontend from this seeding.

**E3 — module budget is two-dimensional, one check.** A module fails at
>40 top-level functions/methods OR >1000 physical lines, both assessed in
the same AST pass; no permanent exemption exists for either dimension —
a doctrinal registry module (e.g. `writes.py`) outgrowing the cap is the
intended tripwire forcing a deliberate package split at that moment, not
before.

**F2 — function ceiling at 80 lines.** AST span
(`end_lineno - lineno + 1`), decorators excluded, applied to every
function/method including nested ones — chosen over a looser ceiling
because `say`/`_stream`/`_apply_mutation` already show that a permissive
cap doesn't create a tripwire before four-digit accretion.

**G1 — the LLM-parse chokepoint is a new dedicated module.** All
model-output JSON parsing converges on `src/world_engine/llm_parse.py`
(stage e), not `analyzer.py` (already a duplication source, not a neutral
host for a shared helper) and not `ollama_client.py` (stays transport-only
— its own `json.loads` sites decode the Ollama wire protocol, never a
model's substantive output, and are named `PERMANENT_ALLOW` entries in
`llm_parse_chokepoint.py`, not migration candidates).

**H1 — single ticket, staged briefs a→g, checks-first.** One ticket
carries the whole seeding-to-remediation arc so the R1/R5 baseline
lifecycle is atomic and verifiable at ticket close: born in stage a
(this brief, checks ship with fresh baselines generated from `main`),
shrunk stage by stage as b–f decompose the flagged functions/modules and
migrate the flagged parse/print sites, deleted outright in stage g.

**This brief (a).** Ships `function_length.py` (R1), `module_budget.py`
(R5), `llm_parse_chokepoint.py` (R2), and `no_print_in_src.py` (R3),
zero `src/` change. Baselines/allow-lists were regenerated from `main` at
this brief's execution time, not copied from RECON-0027's figures (which
undercounted `cockpit/app.py`'s top-level function count at 103 vs. the
measured 97 — RECON is report-only, never authoritative for exact
figures). Fail-closed proof for all four checks and regression proof for
`function_length.py`/`module_budget.py` were run and restored at
brief-exec time, per BRIEF-0027-a's Done criteria.

---

## SAY/_STREAM DECOMPOSITION — record/replay proof + module split (BRIEF-0027-b, no schema change)

**The trigger.** `app.py:3843` `say` (1130 lines) with a nested 958-line
`_stream` generator was RECON-0027's flagged monolith and the riskiest
behavior-preserving refactor of the project to date: the live play path,
zero behavior tests, tightly interleaved SSE streaming, canon writes, and
every invariant the play system defends (frozen-scene gating, constraint
gating, monotone condition ladder, discoverable-detail exclusion, the
model= exemption).

**Harness before refactor, not after.** `scripts/harness_say_replay.py`
(disposable, deleted at stage g) copies the live DB to a throwaway path,
never opens the real one for writing, and proves equivalence by recording
real `/say` round-trips (Ollama request/response pairs, SSE text, and
normalized before/after DB dumps of every table the play path touches)
against pre-refactor code, then replaying the SAME model responses against
post-refactor code and diffing. Volatile fields (UUIDs, timestamps) are
normalized via a stable first-seen-order placeholder mapping so the diff
compares structure, not literal values. Self-validated PASS on
pre-refactor code before any decomposition began; PASS again post-refactor
proved SSE + DB write equivalence for the exercised paths (scene mode,
direct-target dialogue in a gathering with bystanders, the overhearing
model call). The physical/join/travel/initiative-generate branches were
NOT exercised by those 3 turns (the model didn't route into them) — those
were verified by manual line-by-line diff against the original source
instead, which caught and fixed two real bugs (two `player_condition`
sites hardcoded to `"unharmed"` instead of threading `ss_condition`)
before they ever reached the harness. Live replay of the untouched
branches remains a debt — see below.

**Extraction shape.** `say` stays in `app.py` as a ~20-line orchestrator
(persist-turn-setup call, build-stream call, return `StreamingResponse`);
its exhaustive mode-routing/SSE-protocol/turn_order documentation moved to
a comment block directly above the function (kept adjacent, not deleted)
because the docstring alone was 63 lines — inside the function's AST span
it would have blown the 80-line cap on its own. Every `_say_*` helper
threads a `_TurnCtx` dataclass (turn-setup facts, built once) plus
explicit stream-time locals (`ss_condition`, `ss_constraints`, `mode`,
etc.) as plain parameters — mechanical, not a new abstraction. A
`_SayAbort` exception replaces the original's scattered
`yield error; yield [DONE]; return` idiom (frozen scene, an Ollama error
mid-turn) with one raise site per case and one catch site at the top.

**R5 forced a 3-way split, not 2.** `play.py` alone measured 1476 lines —
over the 1000-line cap even after the R1 line-length trims. Split along
sub-domain, not arbitrarily: `play_physical.py` (arbiter, dice verdict,
opposed NPC reaction, scene_state writes, discovery gating — a
self-contained resolution domain) and `play_stream.py` (MJ narration
token streaming, NPC initiative vote/act/migrate/narrate, the shared
per-turn finish) each ended up close to 400 lines; `play.py` (setup, mode
routing, join/travel/dialogue resolution, the top dispatcher) settled at
~700. No baseline entry was requested for any of the three, per BRIEF's
Scope IN.

**Circular import, resolved by direction + laziness.** `play.py` needs
~30 pre-existing helpers from `app.py` (R7: reuse, never duplicate);
`app.py` needs `play.py`'s two entry points. `app.py`'s `say()` imports
`play` lazily (inside the function body) — by the time a request actually
calls `say()`, `app.py` has fully finished loading, so `play.py`'s
`from . import app as _app` at module top succeeds unconditionally. The
same pattern repeats one level down: `play.py`'s `_say_run_turn` lazily
imports `play_physical`/`play_stream`, which import `_TurnCtx`/`_SayAbort`
from `.play` at their own module top. No file imports "up" the dependency
chain at its own top level — only ever lazily, from a function body that
only runs once the target is guaranteed loaded.

**Two verify checks had gone silently blind, not merely red.**
`prompt_registry.py`'s static wiring scan and `llm_parse_chokepoint.py`'s
transition allowance are both keyed by `path::qualname` /
`path::max_sites`. Neither named the new files, so neither *failed* when
the code moved — the scan simply stopped looking, a false PASS. Caught by
independently re-deriving the expected site count from the moved code
(5 `model=model` call sites, 1 `json.loads` site) and cross-checking the
scanner's own findings before trusting the green result. Both allowlists
now name `play.py`/`play_physical.py`/`play_stream.py` explicitly.

**`_analyze_overhearing` via `_app._analyze_overhearing(...)` broke
`single_canon_write.py`'s attribution**, which resolves a `.add()`
argument's table through import-alias tracking — an attribute access
through a module reference (`_app.foo(...)`) isn't a traceable import
alias the way `from ..analyzer import analyze_overhearing as
_analyze_overhearing` is. Fixed by importing it directly from `analyzer.py`
in `play_stream.py` (analyzer.py has no dependency on cockpit, so this
isn't a new coupling) rather than routing through `app.py`'s re-export —
a real second sanctioned-write-path check regression, not a false
positive; every other `.add()` site in the three new files resolves fine
because its argument is a direct model-class constructor call.

**Debt.** Physical-mode, join, travel, and the initiative act-generation
branch were validated by static line-by-line diff, not harness replay —
the 3 reference turns never routed into them. A follow-up brief or manual
play-test exercising a physical roll, a join, a travel attempt, and a
gathering where the vote actually fires would close this gap; nothing in
BRIEF-0027-b's scope required it (Scope OUT: "harness coverage beyond the
play path" and no behavior-improvement side quests).

*Partially closed at BRIEF-0027-i*: that brief's mandatory gap-closure
turn (recorded against pre-d commit `5b5f237`, replayed against the fixed
branch — see that entry below) routes through `POST /api/scene/join` and
so now gives the join branch harness coverage, for the unrelated reason
that it's also the only route touching `_interpret_mode`/
`_load_mj_interpret_template`. Physical-mode, travel, and initiative
act-generation remain undercovered by harness replay.

---

## UNDEFINED-NAME REMEDIATION + R8 PROMOTION (BRIEF-0027-i, no schema change)

**The defect.** BRIEF-0027-d's split (app.py -> routers, crud.py -> a
domain package) left 80 pyflakes `UndefinedName` (F821) sites: a shared
private helper stayed resident in one domain module while the sibling
modules whose route handlers called it moved out from under it without
gaining an import. Python resolves names at call time, so every module
still imported cleanly and the route table stayed set-identical (109/110
routes verified before and after this fix, zero shadow pairs) — every
existing check, including a manual route-table census, saw a green result.
The defect was invisible until a handler actually touching one of the
missing names ran, 500ing at request time. This is why BRIEF-0027-d's live
gate broke on both play and creation despite every machine check passing.

**Fix shape — a closed `crud/_shared.py`, not a re-import shuffle.**
`_iso`, `_world_id`, `_get_entity` were re-homed from `crud/entities.py`
into a new `crud/_shared.py`, and every crud domain module now imports
explicitly what it uses. The brief's stated closed set also named
`_list_relations`/`_list_knowledge` and the `RELATION_FIELDS`/
`KNOWLEDGE_FIELDS`/`EVENT_FIELDS` constants; execution inventory (as the
brief anticipated: "exact closed set = execution inventory") had to widen
that set slightly to avoid a circular import: `_list_relations` calls
`_relation_dict` (previously local to `relations.py`), so both moved
together, same reasoning for `_list_knowledge`/`_knowledge_dict`. Moving
only the lister without its dict-builder would have made `_shared.py`
import back from `relations.py`/`knowledge.py`, which in turn import
`_list_relations`/`RELATION_FIELDS` etc. from `_shared.py` — a load-time
deadlock. `RELATION_TYPES`/`RELATION_DIRECTIONS`/`KNOWLEDGE_LEVELS_ORDERED`
moved alongside their respective `*_FIELDS` constant for the same reason
(each is used nowhere else in its home file). `EVENT_TYPE_LABELS_FR`/
`EVENT_KNOWLEDGE_STATUSES` moved too, since `EVENT_FIELDS` is built from
them and `events.py` also needs them for its own validation — keeping a
single source of truth beat duplicating the literals in two modules.
`crud/__init__.py`'s existing re-export imports (`from .relations import
RELATION_FIELDS, ...`) needed no changes at all: `from .relations import
X` resolves against whatever name is bound in `relations`'s namespace,
whether defined there or imported — so every domain module re-importing
its needed names from `._shared` kept the package's public re-export
surface working unchanged.

`routes/play.py` gained `_log = logging.getLogger(__name__)` (never
defined there; both call sites are on `_analyze_window`'s exception path,
which is exactly why neither the harness nor any prior review noticed) and
imports for `_load_mj_interpret_template`/`_interpret_mode` from
`..play_physical`. `cockpit/play.py`'s `_propose_engine_discovery` type
hint on `DiscoverableDetail` was undefined too (same class of miss,
different site) — added to its `..models` import.

**Mandatory harness re-runs, and the gap those closed.** Both disposable
harnesses replay clean on the fixed branch: `harness_say_replay.py replay`
(SSE + DB dumps, the 3 existing TURNS) and `harness_mutation_apply.py
replay` (all 13 mutation types + the deliberately-failing sibling). But
the 3 `say` TURNS never route through `POST /api/scene/join`, so they
never exercised `_interpret_mode`/`_load_mj_interpret_template` — the
exact two names BRIEF-0027-d silently broke. Per the brief's mandatory
instruction, a 4th reference turn was recorded once against commit
`5b5f237` (merge of BRIEF-0027-c, immediately pre-BRIEF-0027-d — confirmed
by its file list: monolithic `cockpit/app.py`/`crud.py`, no `routes/` or
`crud/` package yet) via a throwaway script run from a `git worktree`,
starting from the harness's own already-recorded `pre_state.sqlite` (not a
fresh live-DB pull) with the reference player's `gathering_member.left_at`
soft-set so `scene_join` falls through to the `_interpret_mode` branch
instead of short-circuiting on `already_joined`. The recorded outcome is
an ambiguous `join_candidates` result (two open gatherings at the
location) — a legitimate, deterministic branch, not an error. Replayed
against the fixed branch's `cockpit.routes.play.scene_join` with an
isolated `sqlmodel` engine (its own workdb copy, never touching
`world_engine.db.engine`, which the 3-TURN replay has already bound): PASS
on both the JSON result and the before/after DB dump. The recorded
fixtures (`scene_join_call/result/dump.json`) live in the existing
gitignored, disposable `scripts/harness_say_fixtures/` directory;
`harness_say_replay.py`'s `record` mode does not regenerate them (it only
ever captures the 3 `say` TURNS against whatever is currently checked
out) — regenerating against post-fix code would defeat the point of
proving pre/post-d equivalence.

**R8 promotion.** `undefined_names.py` runs pyflakes over every file under
`src/` via `pyflakes.checker.Checker` directly (typed `UndefinedName`
message objects, not string-matching the text reporter — a renamed
message string would otherwise silently blind the check the same way
`prompt_registry.py`'s static scan went blind during BRIEF-0027-b).
Fail-closed on zero files scanned or pyflakes unavailable. Proven
fail-closed by a temporary injected F821 (added to `_shared.py`, confirmed
red, removed, confirmed green again) before this record was written.
`code_standards.md` section 2 gained R8 verbatim; `pyflakes>=3.4.0` is
pinned in a new `requirements-dev.txt` (no prior dev-requirements file
existed in the repo).

**Standing lesson.** A module split is not proven correct by import success
or route-table identity — Python's late name binding means a decomposition
can be wrong in exactly the branches nothing exercises (here: two
exception-handler `_log` calls and one non-`/say` route). `undefined_names.py`
now makes that entire failure class visible on every future split,
independent of what any specific harness happens to traverse.

## ANALYZER/TICK LOGGING + MODULE-BUDGET RE-KEY (BRIEF-0027-f, no schema change)

**Scope amendment.** BRIEF-0027-f originally scoped `analyzer.py`'s 12
`print()` sites only. Mid-execution, `TRANSITION_ALLOW`'s live entry for
`tick.py` (26 sites, matching the AST-authoritative census, not
RECON-0027's grep-based one) surfaced a contradiction: Scope IN named only
`analyzer.py`, but the brief's own Done-means required
`TRANSITION_ALLOW` empty and zero `print()` sites tree-wide. Nia amended
the brief in-session to extend the conversion to `tick.py`, same rules
verbatim (module `_log = logging.getLogger(__name__)`, level mapping
info/warning, message content preserved, French-label DATA exclusion
unchanged).

**Every converted site was informational, not decorative.** All 11 actual
`analyzer.py` sites (RECON's estimate of 12 overcounted by one) and all 26
`tick.py` sites carry real diagnostic payload — "what was dropped/skipped
and why," one item at a time. The single exception was `analyzer.py`'s
mid-window terminal cursor-clear (`print(" " * 40, end="\r")`, paired with
the "Analyse en cours…" progress print): pure terminal-redraw mechanics
with zero informational content, deleted rather than converted — a log
stream has no cursor to clear. `analyzer.py:140`'s
`_GOAL_ACTION_MAP["abandonné"]` key and `:749`'s
`"(aucun contexte enregistré)"` fallback stayed untouched: both are
prompt-consumed DATA (the first matches the local model's own French
wording, the second is transcript filler sent back into the next model
call), not messages — same category as the canonical interval-vocabulary
exclusion already on record.

**Whole-tree French-string audit (scope item 2) — no further sites
qualified.** A `[àâäéèêëîïôöùûüçÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ]` sweep across `src/`
turned up French content in `tick.py`, `context.py`, `play.py`,
`play_stream.py`, `play_physical.py`, `entity_author.py`, `region_author.py`,
and several `cockpit/crud`/`cockpit/routes` modules. Every hit resolved to
one of: (a) prompt content sent to or shaping a model call (NPC/MJ
narration instructions, briefing headers, affinity-tier and
condition-ladder labels — the interval-vocabulary precedent generalizes to
all of it), or (b) creator-facing note/reason strings surfaced in the
cockpit UI, which is itself French by deliberate product design
(`index.html`'s own tab labels — "Création", "Créations en attente" —
confirm this) — translating those would desync UI copy from its own
review notes, not fix a stray developer message. `ollama_client.py`'s
docstring quoting `"réflexion…"` is a literal reference to that exact
`index.html` UI string, not prose. None of this is `src/`'s frontend
governance gap either (RECON-0027 risk zone D, a separate, larger, un-ticketed
concern). Zero additional translations were made; this reasoning is the
audit's documented output per the brief's own "escalate, do not
translate" instruction for ambiguous data-vs-message calls.

**Module-budget collision, and its resolution.** Adding `tick.py`'s
mandated logger preamble (`import logging` + module-level `_log`) costs 2
physical lines with zero print-call-site content — all 26 conversions
themselves are exactly line-neutral (one `print()` line replaced by one
`_log.warning()` line each, after collapsing initially-wrapped calls back
to single lines to protect `function_length.py`'s `_normalize_tick_item`
baseline, which closed unchanged at 239/239). `module_budget.py`'s own
docstring is explicit that trimming unrelated content to dodge the line
cap is the exact workaround the check exists to block, and the 26
converted sites are all substantive (no decorative separator/banner
prints existed to delete and absorb the 2 lines). Nia approved a one-time,
documented re-key of `tooling/verify/baselines/module_budget.json`:
`tick.py` `1797 -> 1799` lines, `functions` unchanged at 19, comment
citing this decision. Shrink-only from 1799 forward; the entry (and the
whole baseline file) is deleted outright at TICKET-0028's close, per the
updated baseline-file header comment.

**Bug-log flip.** `tooling/improvement/bug_log.jsonl`'s sole entry
(2026-07-03, `context.py` subculture-values crash, actually fixed by
BRIEF-0025-d/v1.78) had sat at `status: "open"` since — `code_standards.md`
section 5's documented housekeeping debt. Flipped to
`"fixed (BRIEF-0025-d, v1.78)"`, the exact string `code_standards.md`
already specified; every other field byte-identical.

---

## RESIDUAL FREEZE — successor ownership handoff to TICKET-0028 (BRIEF-0027-g, no schema change)

**The trigger.** Stages a–f decomposed `say`/`_stream`, `_apply_mutation`,
`cockpit/app.py`/`crud.py`, the LLM-parse chokepoint, and
`analyzer.py`/`tick.py` logging — but never targeted the whole codebase.
At stage g, `tooling/verify/baselines/function_length.json` still carries
30 entries (`tick.py`, `context.py`, `analyzer.py`, `entity_author.py`,
`writes.py`, `region_author.py`, plus handlers moved intact by stage d
into `cockpit/routes/*.py`, `cockpit/play_stream.py`,
`cockpit/play_physical.py`, `cockpit/mutations.py`, `cockpit/crud/goals.py`)
and `module_budget.json` still carries 4 (`tick.py`, `writes.py`,
`models.py`, `entity_author.py`). Every entry belonging to a file/function
stages b–f actually touched (`say`, `_stream`, `_apply_mutation`,
`cockpit/app.py`, `cockpit/crud.py`) is confirmed absent from both files —
the residual is exactly, and only, what the ticket never scoped.

**I2 (locked by Nia) — freeze, don't extend or relax.** Two rejected
alternatives: extending TICKET-0027 itself to decompose the residual
(scope creep on an already nine-brief ticket), or relaxing R1/R5 to a
permanent exemption (the exact grandfathering C2 already rejected at
intake). Instead the residual is FROZEN — shrink-only (existing mechanic,
unchanged), ownership named to a successor ticket, TICKET-0028 (residual
decomposition; ID to be confirmed by Nia at deposit), which deletes both
baseline files at its own close. A bounded transition with a named owner,
not grandfathering: the freeze is scoped to two files with a fixed,
enumerated entry set, not an open-ended carve-out.

**Baseline audit (no entries changed).** Both baseline files were
regenerated against `main`-equivalent `src/` state at this brief's
execution and diffed entry-for-entry against an AST pass over the current
tree: identical. Every stage from a onward already kept its own baseline
edits shrink-only and in sync (confirmed via `git log` on both files:
stages a, b, c, d, e, f each touched exactly the baseline rows their own
decomposition affected). Stage g's baseline audit is therefore a
confirmation, not a rewrite — only the header comment in each file changes,
recording the freeze and the new deletion owner.

**Residual enumeration (execution notes).** `function_length.json`, 30
entries, `file:qualname:lines`: `tick.py:run_world_tick:417`,
`tick.py:_normalize_scope_event:292`,
`context.py:assemble_npc_context:267`,
`cockpit/routes/regions.py:commit_region:264`,
`analyzer.py:analyze_overhearing:256`,
`cockpit/routes/mutations.py:_find_applied_duplicate:256`,
`tick.py:_normalize_tick_item:239`, `tick.py:assemble_tick_context:214`,
`analyzer.py:_normalize_to_schema:180`,
`cockpit/routes/play.py:scene_join:163`,
`context.py:assemble_mj_context:161`,
`region_author.py:generate_region_draft:157`,
`cockpit/mutations.py:_apply_completion_effects:150`,
`analyzer.py:analyze_window:149`, `writes.py:write_faction_role:144`,
`entity_author.py:generate_entity_draft:119`,
`entity_author.py:generate_event_draft:118`,
`cockpit/play_stream.py:_npc_initiative_vote:117`,
`cockpit/play_stream.py:_build_mj_user:114`,
`tick.py:assemble_faction_event_context:114`,
`writes.py:write_relation:111`,
`cockpit/routes/creator.py:create_player_character:108`,
`cockpit/routes/mutations.py:approve_mutation:106`,
`cockpit/routes/mutations.py:batch_review_mutations:97`,
`writes.py:delete_world_cascade:94`,
`region_author.py:_normalize_manifest:91`, `writes.py:write_knowledge:91`,
`cockpit/play_physical.py:_arbitrate:87`,
`cockpit/crud/goals.py:backfill_npc_goals:84`,
`cockpit/routes/play.py:world_tick_endpoint:81`,
`entity_author.py:generate_player_draft:81`. `module_budget.json`, 4
entries, `file:functions:lines`: `entity_author.py:28:1055`,
`models.py:2:1188`, `tick.py:19:1799`, `writes.py:32:1607`.

**Harness ownership transfer.** `scripts/harness_say_replay.py` and
`scripts/harness_mutation_apply.py` (record/replay proofs for the `say`
and `_apply_mutation` decompositions) are not deleted at this stage.
TICKET-0028's decompositions (`run_world_tick` 421 lines, tick.py;
`assemble_npc_context` 267 lines, context.py; `analyze_overhearing` 260
lines, analyzer.py) will need the same before/after proof discipline;
their deletion is re-scoped to TICKET-0028's close alongside the
baselines, noted in each script's header docstring.

**Ticket close.** TICKET-0027 ships zero schema change
(`schema_version_touched` stays empty). `code_standards.md` R1, R5, and
section 4 stage g are rewritten to match: the baseline files are described
as reduced to a frozen residual at this stage, not deleted here.
`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## I2 CLOSED — baseline retirement, harness deletion, exemption-free R1/R5 (BRIEF-0028-f, no schema change)

**I2's death date.** Stages a–e of TICKET-0028 emptied both transition
baselines entry-by-entry (`tick.py` via BRIEF-0028-a, `writes.py` via
BRIEF-0028-b, `models.py` via BRIEF-0028-c, `entity_author.py` via
BRIEF-0028-d, the remaining 19 `function_length.json` entries via
BRIEF-0028-e) — both files stood at `[]` going into this brief. This brief
deletes the artifacts outright: `tooling/verify/baselines/function_length.json`
and `tooling/verify/baselines/module_budget.json` are gone; `function_length.py`
and `module_budget.py` run with no exemptions, decision I2 (`ARCHITECTURE_DECISIONS.md`,
BRIEF-0027-g) fully discharged, not merely frozen.

**Fail-closed absence handling.** Both checks previously treated a missing
baseline file as an error (`fail(f"{BASELINE_FILE} not found")`), which
would have broken the check the moment the (already-empty) baseline was
deleted. `_load_baseline()` in each check now returns `{}` on file absence
instead of failing — an empty exemption set, not a vacuous pass: every
function/module over cap still fails since nothing is baselined. Proven at
execution, not assumed: with both baseline files absent, a scratch function
of 92 lines was planted in a throwaway `src/world_engine/` module and
`function_length.py` FAILed on it (`not present in function_length.json`);
removed, the suite returned to PASS. Same proof for `module_budget.py`
with a scratch 45-function module. Both scratch files were never committed.

**Harness deletion.** All four disposable record/replay harnesses and
their fixture directories are deleted: `scripts/harness_say_replay.py`
and `scripts/harness_mutation_apply.py` (transferred from TICKET-0027,
BRIEF-0027-g), `scripts/harness_tick_replay.py` (BRIEF-0028-a),
`scripts/harness_entity_author_replay.py` (BRIEF-0028-d) — plus
`scripts/harness_{say,mutation,tick,entity_author}_fixtures/` (untracked,
`.gitignore`-only) and the now-dead `.gitignore` entries pointing at them.
Pre-deletion census (grep across `src/`, `tooling/`, `CLAUDE.md`,
`scripts/`) found one live-code reference outside the harnesses
themselves: `src/world_engine/tick.py`'s module docstring named
`scripts/harness_tick_replay.py` directly; reworded to describe the proof
without naming the deleted file. Every other hit was either a harness
mentioning a sibling harness (deleted alongside it) or a historical
mention in a ticket/brief/this archive (kept, per the append-only-history
exception).

**`code_standards.md` closure edit.** R1 and R5's transition-artifact
sentences, and the I2 paragraph in section 4 stage g, move from
present/future tense ("owned by TICKET-0028, deleted at TICKET-0028's
close") to past-tense closure ("transition baseline retired at
TICKET-0028's close (BRIEF-0028-f); the check runs with no exemptions").
No assertion, cap, or mechanic changed — historical tense only. Doc
version bumped v1 -> v1.01 (no prior explicit version line existed; one
was added to the header, per the brief's default convention).

**Ticket bookkeeping.** `TICKET-0028` front-matter: `BRIEF-0028-f`
appended to `brief_ids`, `status: live-gate`. Per the BRIEF-0027-g/
TICKET-0028 precedent (G1 pattern), the `live-gate -> done` flip rides the
first commit of the next ticket, not this one.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

---

## OBSTACLE GEOMETRY SCHEMA (BRIEF-0029-a, schema v1.80)

First step of the spatial / Play mode workstream (0029 obstacle geometry ->
0030 collision authority -> 0031 NPC spatial presence + proximity gate ->
0032 canvas/WASD surface). Adds persistent intra-location wall geometry
storage the server can judge movement against and the client can draw —
nothing that moves ships in this step.

**A1 — two relational tables, agenda/agenda_step precedent.** `obstacle`
(`id, world_id, location_id, created_at`) + `obstacle_vertex` (`id,
obstacle_id, vertex_order, x, y`), unique index `idx_obstacle_vertex_order
(obstacle_id, vertex_order)`. Rejected: single-table-with-implicit-obstacle
(identity by convention is an anti-pattern this codebase avoids
elsewhere). No `kind`/`label` column: no reader exists for one yet (same
discipline as the DORMANT `npc_price`/`faction` fields — do not
speculatively add columns).

**B1 — curated-config governance family.** `obstacle`/`obstacle_vertex`
join the `faction_role`/`location_subculture`/`npc_price`/`world_law`
family: no `change_history`, full-replace per location via new sanctioned
site `writes.write_location_obstacles`, added to
`canon_write_policy.txt`'s `[CANON_TABLES]` and as the 23rd site in the
`writes/` package (22 relocated at TICKET-0028 + this one new site).
Correction against the brief's assumption: `location.bounds_width`/
`bounds_height` writes inside the new `set_location_geometry` endpoint are
NOT covered by the existing `crud/entities.py::update_entity` sanctioned
site — `single_canon_write.py` attributes sites at function grain, not
file grain, so a second entity of `location` was added:
`crud/entities.py::set_location_geometry   location`.

**B2 — vertex storage, never `(x,y,w,h)` in the schema.** Locked upstream
in the workstream doc: even though v1's only authoring surface is
rectangles, the schema stores ordered vertex rows from day one so a future
polygon migration only adds rows, never rewrites the schema. The v1 UI's
`rect` shorthand (`[x, y, width, height]`) is an API/UI convenience,
expanded server-side into 4 vertices — it never touches the schema.

**C1 — per-location local coordinate space.** Origin top-left, x
rightward, y DOWNWARD (canvas-native), floats, nominal unit 1.0 = one
world-meter. Explicitly DISTINCT from `location.coord_x`/`coord_y`
(world-map placement, schema v1.78) — the two coordinate spaces answer
different questions (where is this location on the world map, vs. where
are the walls inside it) and must never be conflated. The doctrine comment
above the `Obstacle` model class states this verbatim; any future reader
confusing the two spaces is a defect against this decision.

**C-b1 — playable bounds as two nullable `location` columns.** NULL means
"no spatial mode" for that location — most locations never opt in.
Rejected: bounds-as-special-obstacle (would require every geometry reader
to special-case the first row).

**D'1 — rectangle-form authoring over a polygon-ready contract.** The
creator sheet exposes plain numeric rows (x, y, width, height); the wire
contract (`PUT /entities/{id}/geometry`) accepts EITHER `rect` shorthand OR
a generic `vertices` list (>= 3), so a future graphical polygon editor
(deferred, D'2) needs no endpoint change. Server-side rectangle expansion
is clockwise from top-left: `(x,y), (x+w,y), (x+w,y+h), (x,y+h)` — a
declared convention, not structurally enforced (nothing rejects a
CCW-wound custom `vertices` polygon; only the rect shorthand is
canonicalized).

**Migration discipline.** `migrate_v1_80_obstacle_geometry.py` guards
table existence (`obstacle`, `obstacle_vertex`) and column existence
(`location.bounds_width`, `bounds_height`) INDEPENDENTLY rather than a
single "does the first artifact exist" check — a partially applied prior
run (e.g. interrupted after creating `obstacle` but before the `location`
ALTER) completes only the missing pieces on re-run instead of silently
skipping the rest. Purely additive: no data copy, no seed rows: the live
smoke authors its one demo rectangle through the new form instead of the
migration seeding one.

**Read/write surface.** Location detail payload gains `geometry:
{bounds_width, bounds_height, obstacles: [{id, vertices}]}` at every site
already carrying `subculture_rows` (`GET /entities/{id}`, `POST
/entities`, `PUT /entities/{id}`). `PUT /entities/{id}/geometry` is a new,
dedicated full-replace endpoint (bounds + obstacles, one transaction) —
same shape as `PUT /entities/{id}/subculture`, but 404 (not 422) on a
non-location entity, matching this ticket's acceptance criteria rather
than the subculture endpoint's precedent literally. Validation is
fail-closed before any write: each obstacle needs >= 3 vertices, every
coordinate finite (NaN/inf rejected), `rect` width/height and `bounds_*`
must be `> 0` when present.

**Frontend — advisory tier.** The location sheet gets a "Spatial
geometry" panel below the subculture editor: bounds width/height inputs,
a row list of rect obstacles (x/y/width/height + remove), an "Add block"
button, one Save. Existing-locations-only (Tarifs-editor discipline, no
`isNew` draft — unlike the subculture/roles editors). Incoming vertex
lists that are exactly 4 corners of an axis-aligned rectangle (the
server's clockwise-from-top-left convention) render as an editable rect
row; any other polygon renders read-only (`polygone (N sommets)`) and
round-trips its vertices unchanged on save — `authorGeometryDetectItem` in
`cockpit/index.html` is the sole classifier.

**Scope OUT, deferred:** the collision endpoint and movement judging
(ticket 0030); NPC positions and the proximity endpoint (ticket 0031); the
canvas renderer, WASD input, and player circle (ticket 0032); the
graphical obstacle editor — click-to-draw, drag handles (D'2); obstacle
metadata (`kind`, `label`, passable flags, materials — no reader exists);
bounds enforcement / clamping movement inside bounds (0030's job);
`change_history` on the obstacle tables (B1 locked: curated config,
none); building entry/exit, doors, multi-level/z (deferred
workstream-wide).

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

---

## SERVER-SIDE COLLISION ENDPOINT (BRIEF-0030-a, BRIEF-0030-b, no schema change)

Second step of the spatial / Play mode workstream (0029 obstacle geometry
-> **0030 collision authority** -> 0031 NPC spatial presence + proximity
gate -> 0032 canvas/WASD surface). A single server authority judges
transient player movement against the persistent obstacle geometry
written in 0029, and never writes position to canon.

**D5 — a named third register: transient adjudication.** Neither
`_apply_mutation` (AI proposal -> creator checkpoint -> canon) nor creator
CRUD (direct canon): read persistent geometry, judge transient position,
persist NOTHING. Stated verbatim in both `geometry.py`'s and
`spatial.py`'s module docstrings — this is the first citizen of the
register; 0031's proximity endpoint joins the same module.

**D1 — pure module as sole collision authority.** All intersection math
lives in `src/world_engine/geometry.py::clip_segment` (zero DB, zero
FastAPI, zero `cockpit/` imports); `cockpit/routes/spatial.py` is a caller
only, never a co-implementer. Gate-guarded by the permanent regression
check `tooling/verify/checks/geometry_unit.py` (free move, rectangle hit,
triangle hit, bounds clip, degenerate origins, zero-length, on-edge
destination, parallel graze). Rejected: math inlined in the route module
(logic/interface fusion) — the pure module is exactly the piece a future
client-side predictor (rejected C3) would reuse verbatim. Placement
forced by RECON: `routes/play.py` sits at exactly 1000 lines, the G1
module-budget cap — the endpoint lands in a new `routes/spatial.py`
instead.

**D2 — endpoint contract + structural location guard.** `POST
/api/spatial/move-check`, body `{location_id, origin: {x, y},
destination: {x, y}}`, response `{x, y, blocked}`. The handler verifies
`location_id` matches the resolved player's `current_location_id` (409
otherwise) — role doctrine: injected context, and judged geometry,
depends on the active role; a player client must not probe the geometry
of a location the PC is not in. Errors: 404 unknown player or unknown
location; 409 wrong location; 409 no spatial mode (NULL bounds); 422
non-finite coordinates. Rejected: free `location_id` (geometry probing by
segment dichotomy).

**D3 — hard-stop semantics, client-emergent slide.** The server returns
the clipped stop point (pulled back 1mm along the segment) plus
`blocked`; slide-along-wall emerges client-side in 0032 via
axis-component re-submission. Server-computed slide (option B) is
recorded as a compatible evolution — same endpoint, same response shape,
only the returned point would change — kept in mind, not built.

**D4 — point player, visual-only radius.** The player is a point; the
0032 circle radius is purely visual. Rejected: polygon inflation / radius
parameter (premature, same doctrine as the rejected C3). A degenerate
origin (inside an obstacle or outside bounds) returns `(origin,
blocked=true)` — the judge never rescues the player; unblocking is a
creator act.

**Bounds enforcement.** In scope for this ticket (0029 explicitly
deferred it): bounds edges are judged as walls seen from inside, uniformly
with obstacle edges — `geometry.clip_segment`'s edge set always includes
the four bounds edges when bounds is present, no containment assumption
between obstacles and bounds.

**Module budget tripwire as placement rationale.** `routes/play.py`
stayed untouched at its 1000-line cap; `routes/spatial.py` is a new,
same-tier sibling router (mounted alongside play/mutations/creator/
regions/prompts in `cockpit/app.py`), reusing `crud/entities.py`'s
`_location_geometry_dict` (0029's sole geometry assembler) rather than a
second reader.

**Scope OUT, deferred:** persisting any position (Q1 locked
workstream-wide — player position stays client-held per scene); NPC
positions and the proximity endpoint (ticket 0031); canvas, WASD, player
circle, any frontend (ticket 0032); a play-facing geometry READ endpoint
(0032's intake decides its shape); server-side slide (D3-B), player
radius (D4-B) — recorded, not built; rate limiting/batching for WASD
cadence (0032 owns call cadence).

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

---

## NPC SPATIAL PRESENCE + PROXIMITY ENDPOINT (BRIEF-0031-a, BRIEF-0031-b, no schema change)

Third step of the spatial / Play mode workstream (0029 obstacle geometry
-> 0030 collision authority -> **0031 NPC spatial presence + proximity
gate** -> 0032 canvas/WASD surface). NPCs get a position the canvas can
draw and the server can measure distance against, without introducing
persistent NPC coordinates.

**A — deterministic pure derivation, zero storage.** NPC position =
`f(location geometry, open gatherings + rosters, stable ids)`, recomputed
on every request; stability comes from determinism, not storage. Q1 holds
workstream-wide: nothing transient is ever persisted. Rejected: prose
extraction (B — non-deterministic, model-call cost, fragile against the
resilience doctrine); client placement (C — server-side proximity
authority evaporates, the rejected-C3 anti-pattern's NPC edition);
authored spawn layout (D — persistent config nobody reads yet; recorded
as a compatible refinement, not built).

**A-i — placement.py pure sibling + spatial_presence.py sole assembler.**
`src/world_engine/placement.py` (geometry.py's sibling: zero DB, zero
FastAPI, zero `cockpit/` imports) holds `derive_positions`/`distance`.
`cockpit/spatial_presence.py::npc_positions` is the SINGLE site that
turns a location into named NPC positions, reusing `_open_gatherings`,
`_active_members` (cockpit/play.py) and `_location_geometry_dict`
(crud/entities.py, 0029's sole geometry assembler). Player exclusion
lives at the assembler level (filter `character_type == "player"`) —
RECON finding: `_active_members` rosters include the player; that helper
itself is NOT narrowed, since other consumers (initiative vote, speaker
selection) legitimately see the player.

**Determinism doctrine.** All placement randomness derives from
`hashlib.sha256` over stable ids, never Python's salted `hash()` — a
server restart mid-scene must never reshuffle a circle. Gate-guarded by
the permanent regression check `placement_unit.py` (determinism,
obstacle avoidance, bounds containment, clustering, saturation totality,
`distance` exactness), the same discipline `geometry_unit.py` applies to
the collision authority.

**E2 — two endpoints, one derivation.** `GET /api/spatial/presence`
returns the drawable NPC circles (0032's draw cadence); `POST
/api/spatial/proximity` judges a transient player position against the
same recomputed NPC positions (interaction cadence). Both are thin
callers of `spatial_presence.npc_positions` — `routes/spatial.py` stays a
caller only (D1-0030 precedent). Rejected: one merged endpoint (draw
cadence != interaction cadence; 0032 would call "proximity" just to
draw).

**G-A — advisory dialogue gate.** The proximity result enables the
client-side "Parler" affordance for in-range NPCs; `POST
/api/conversations/start` and `/api/scene/join` are byte-for-byte
untouched. Player position is client-held workstream-wide (Q1), so a
structural gate would judge client-supplied data anyway — no added
guarantee — and non-spatial locations / creator flows must keep working
unchanged. G-B (optional `position` in start_conversation, re-judged
server-side when the location has spatial mode) is recorded as a
compatible evolution, not built.

**Threshold.** `placement.INTERACTION_RANGE = 2.0` world-meters, a named
constant, echoed in every proximity response so 0032 never hardcodes it.
Calibrated at live gate; a per-location column is a trivial additive
change later, not built now.

**Earshot rail.** `placement.distance` and
`spatial_presence.npc_positions` are the SOLE spatial-distance site in
the engine; any future audibility reader (who-hears-what) imports them,
never recomputes — mirroring the gate-guarded "sole collision authority"
discipline of 0030. Nothing of earshot itself ships in this ticket.

**Guards mirror move-check (D2-0030 parity).** Both endpoints: 404
unknown player; 409 `location_id` != player's `current_location_id`; 404
unknown location; 409 no spatial mode (NULL bounds); proximity adds 422
non-finite position.

**Scope OUT, deferred:** canvas/WASD/frontend (ticket 0032); a
play-facing wall-geometry READ endpoint (0032's intake decides its
shape); earshot/audibility implementation (rail named only); authored
spawn zones, per-location threshold column, persistent NPC coordinates
(workstream-wide never for this ticket); G-B structural gate (compatible
evolution, not built); rate limiting (0032 owns call cadence).

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

---

## "PARLER" HANDOFF AMENDED + SCENE ROUTE SPLIT (BRIEF-0032-a, no schema change)

Fourth step of the spatial / Play mode workstream (0029 obstacle geometry
-> 0030 collision authority -> 0031 NPC spatial presence + proximity gate
-> **0032-a deterministic targeted join**, ahead of 0032-b/-c's canvas).

**C2 — module split over exemption.** `routes/play.py` was at exactly
1000/1000 lines (the G1 module-budget cap, zero baseline headroom) when
this brief's addition needed room. Rejected: a `module_budget.json`
baseline entry — the check's own doctrine ("no permanent exemptions... the
failing check IS the mechanism forcing a split") rules it out for a new
violation. Resolution: extract the scene lifecycle cluster (`get_scene`,
`enter_scene`, `SceneJoinBody`, the `_scene_join_*` helpers, `scene_join`,
`scene_leave`) verbatim into a new `cockpit/routes/scene.py`, landed as its
own move-only commit (byte-identical bodies, confirmed by diff) before the
G2-b addition — same precedent as `routes/spatial.py` splitting off 0030,
and as the original BRIEF-0027-d module-budget split. `routes/play.py`
keeps conversations, travel, and world-tick; `visit_delta.py`'s
`Visit(...)` constructor allowlist relocated with `enter_scene`
(relocation-not-broadening, not a new write site).

**G2-b — "Parler" handoff AMENDED:** the 0031 client contract
(`routes/spatial.py` header) pointed the talk affordance at
`POST /api/conversations/start`, which creates gathering-less
conversations invisible to `_active_conv_for_gathering`. The affordance
now performs a deterministic targeted join via
`scene/join.target_gathering_id` (no LLM call — code resolves what code
knows). `conversations/start` remains for 1:1 pilot flows.
`SceneJoinBody` requires exactly one of `player_text` /
`target_gathering_id` (422 otherwise); the targeted branch validates the
gathering exists, is open, and matches the player's current
location/session (404 / 400, mirroring `join_gathering`'s wording) before
reusing the same conversation-creation tail as the free-text path
(`_scene_join_create_for_gathering`, extracted from
`_scene_join_resolve_and_create`'s tail — the free-text path is otherwise
byte-identical: same interpretation call, same rows, same response shape).

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## TICKET-0033 (BRIEF-0033-a, no schema change)

**Region commit now writes faction roles.** `_commit_region_factions`
(`cockpit/routes/regions.py`) displayed `public.roles` (from
`entity_author._normalize_roles`) in the review sheet but never wrote them
— the unitary faction creator committed roles correctly via
`POST /api/factions/{id}/roles`, but the region path silently dropped
them. Fixed by calling `write_faction_role` — the sole `faction_role`
write chokepoint — for each draft role, in draft order, right after the
faction entity is created, inside the same commit-free transaction as the
rest of `commit_region` (no new commit point). `max_holders` stays `null`
at region commit (the draft never carries it, consistent with the unitary
creator's `limit: null`); `world_id` is the region commit's already-computed
`world_id` (no re-derivation). Casefold-deduped within one faction's list,
first occurrence wins, before the write — a model-produced duplicate name
would otherwise abort the whole atomic region commit against
`idx_faction_role_name`'s unique index.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## REGION MANIFEST CHECKPOINT — FULL EDITING (BRIEF-0033-b, no schema change)

**Locked: A1 — everything editable.** Amends the BRIEF-38 entry above
("REGION GENERATION — two-phase manifest checkpoint"): the C1 boundary
("one-liner is the only writable field", "name fields rendered read-only")
and the "C1 — one-liner text only, C2/C3 deferred" section are both
superseded. The concept (now a `<textarea>`), every entity's `name`, and
row add/remove for factions/locations/NPCs are editable; locations gain an
`is_root` checkbox and a `parent_name` select, NPCs gain `location_name`
(required) and `faction_name` selects. No new manifest key was added — only
existing keys (`concept`, `name`, `one_liner`, `is_root`, `parent_name`,
`location_name`, `faction_name`) became writable, so K1 stays intact: the
composite-brief composers still read only
`name`/`one_liner`/`parent_name`/`concept`.

**Server-authoritative / client-is-advisory still holds, now doing more
work.** The BRIEF-38 posture is unchanged in kind, only in load: Phase B's
`_normalize_manifest` re-run on the incoming dict is still the *sole*
safeguard (no draft store to diff against, B1), and it now has to resolve a
materially wider edit surface — renamed/added/removed factions, locations,
and NPCs, dangling `parent_name`/`location_name`/`faction_name` references
left behind by a rename — with the same structural guarantees as before
(exactly one root, valid `parent_name`, NPCs placed only into manifest
locations). Nothing new is trusted client-side; this step adds no
server-side validation of its own by design (Scope OUT).

**Selects are not live-synced against renames.** A faction/location rename
does not walk the manifest to update every row that references its old
name by string — selects are rebuilt from current names only on
add/remove re-renders, and a stored reference that no longer matches any
current name is injected as its own selected option rather than silently
reassigned or dropped. This mirrors the existing contract Phase B already
has to handle (an edited `parent_name`/`location_name`/`faction_name` may
not resolve, and the server notes/nulls it) — the UI does not pre-empt
that resolution.

**Nameless-row handling at build time.** `regionBuild()` drops
empty-named rows before POSTing (mirrors the server's own drop-nameless
posture) — unless a nameless row carries a non-empty one-liner, in which
case the build is blocked with a status message instead of silently
discarding typed content.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## REGION REVIEW SHEET — FULL EDITING (BRIEF-0033-c, no schema change)

**Locked: B1 — the zoom sheet is the region-review editing surface.**
`regionRenderSheet` (`cockpit/index.html`) turns from a display-only
`_sheetField` render into a form: every field oninput/onchange-mutates
`regionDraft` directly (`node.result.draft.public.X` / `.secret.X`), the
same direct-mutation pattern BRIEF-0033-b established for the manifest
checkpoint. Faction/Lieu/parent reassignment writes the node's top-level
`faction_local_id`/`location_local_id`/`parent_local_id` via `<select>`s
built from the live draft (rejected entities included, suffixed
"(rejeté)") — the accept/reject cascade still re-derives entirely at
commit, unchanged (`_commit_region_*`, `cockpit/routes/regions.py`). No
save button: the draft IS the state, and `genericModalClose()` now calls
`regionRenderAll()` on every close so renames/reassignments reach the tree
cards immediately (guarded on `regionDraft` truthy, so closing an
unrelated modal — world create/delete, skill delete — while only a bare
manifest/brief view is up never clobbers `regionRenderBriefForm`'s
in-progress input).

**Locked: F1 — faction roles editable in the sheet.** New
`_regionSheetRolesHtml` mirrors the look of the NEW-faction roles editor
(`authorRenderRolesEditor`) but binds to this faction's
`draft.public.roles` array, not `authorFactionRolesDraft` — add/remove/
reorder, committed in draft order via `write_faction_role`
(BRIEF-0033-a). NPC knowledge rows and goals (long + shorts) get the same
row-editor treatment, bound to `draft.secret.knowledge` /
`draft.public.goals`.

**No new draft fields, no backend change.** Every editable field already
had a commit-side reader; nothing new was invented. Knowledge `level` is a
plain text input, not a `KNOWLEDGE_LEVELS` select — that constant isn't
exposed to the frontend today, and adding an endpoint for it was
explicitly out of scope; the brief's documented fallback applies. The
knowledge row's `is_secret` checkbox is editable but currently inert at
commit: `_commit_region_npcs` hardcodes `is_secret=True` regardless of the
draft value (pre-existing, unchanged) — a known, harmless discrepancy
between what the sheet shows and what the commit writes, left as-is
because fixing it is a backend change this step's scope forbids.

**Multi-root tree rendering (incidental fix).** `regionRenderTree`
previously rendered only the *first* location found with
`parent_local_id == null`, matching the single-root invariant generation
always produced. Parent reassignment (B1) can now legitimately produce a
second such location (the "--" / root-fallback option, matching the
commit's `None` -> no-parent resolution in
`_region_resolve_location_parent`) — without this fix that location, and
any NPCs hosted in it, would silently disappear from the review tree
while remaining correct in the underlying draft and at commit. Fixed to
render every top-level location, not just one.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## REGION REVIEW — PRE-COMMIT LOCATION GRAPH (BRIEF-0033-d, no schema change)

**Locked: C1 — on-demand, read-only viewport over the draft cascade.**
`regionRenderAll` (`cockpit/index.html`) gains a `regionLocGraphOpen`
toggle (hidden by default) and a `region-lieux-graph`/
`region-lieux-graph-svg` container, reusing the Lieux tab's SVG renderer
functions (`graphAutoPlace`, the node/edge markup shape) rather than
Cytoscape or a new rendering path. Fed entirely by client-held draft state
(`regionDraft`, `regionCascade()`, `regionAccepted`, `regionConfirmedLinks`)
— no new backend endpoint, no new draft key.

**Adapter mirrors backend link resolution, intra-region half only.**
`regionLocGraphData()` draws hierarchy edges from `regionCascade()`'s
already-computed `effectiveParent` map (no re-implementation of the
fallback-to-root rule) and connection edges from CONFIRMED `sensed_links`
of kind `connection`, matched to another accepted draft location by
trim+lowercase name equality — the same intra-region half
`_region_resolve_link_target` (`cockpit/routes/regions.py`) applies before
falling back to a DB scan. Pre-commit there is nothing to fall back to, so
the DB half is intentionally not replicated client-side; an unresolved or
self-referential name simply produces no edge rather than a synthesized
one, keeping the viewport from ever showing a connection the server
wouldn't also draw.

**Strictly read-only.** No handlers are wired for edge creation, edge
deletion, or position persistence (`graphCreateEdge`, `graphEdgeClick`,
`graphPersistPos` are never called from this path); node drag is omitted
entirely (static circular layout). `regionRestart()` and
`_regionWorldReset()` both reset `regionLocGraphOpen` to `false` alongside
the existing region state resets, so a fresh draft or a world switch never
inherits a stale open graph.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## NPC TAB — GLOBAL RELATION GRAPH + LINK EDITING (BRIEF-0033-e, no schema change)

**Locked: D1 — global mode inside the existing ego panel, no new surface.**
The on_demand `relgraph` slot (BRIEF-0023-a/b) gains a `relGraphMode`
('ego' | 'global') instead of a second panel: a "Global" toggle in the
panel head flips the fetch target between the existing ego endpoint
(`GET /characters/{id}/relation-graph`) and the new
`GET /api/relation-graph`, re-rendering the same cytoscape instance with
the same bucket coloring and info-card column. `relGraphOnSelect` ignores
NPC-list selection while in global mode (the graph is world-wide, not
keyed to a selected character); `_relGraphReset` resets the mode to
`'ego'` on every tab-enter/world-switch, so global mode never survives a
navigation.

**Backend: one read-only route, two shared row-builders.** `_relation_graph_nodes`/
`_relation_graph_edges` (`cockpit/crud/relations.py`) factor the node/edge
dict shapes out of the ego endpoint so `GET /api/relation-graph` reuses
them byte-for-byte — same fields, no `center` key. The path is a top-level
`/relation-graph` segment (not nested under `/characters/{entity_id}/...`)
specifically so the ego route's `{entity_id}` path parameter never
swallows it. Same structural exclusion of `_RELATION_GRAPH_EXCLUDED_TYPES`
in the WHERE clause as the ego route (G1 of BRIEF-0023-b) — never
post-filtered. Writes nothing; isolated (zero-edge) active characters are
included so a link can be created toward them.

**Locked: E1 — tap/dbltap/edge semantics differ only in global mode.**
Ego mode's tap (info card) and dbltap (recenter via `relGraphFetch`) are
untouched. In global mode: tap opens the info card with the node's own
relations list (label "Relations", not "Relations avec le centre");
dbltap toggles a cosmetic `.followed` cytoscape class (56px, not
persisted); a "Lier" toggle arms two-tap link creation (tap A, tap B ->
edge panel in CREATE mode); tap on an edge opens the edge panel in EDIT
mode. All three writes (create/update/delete) go through the existing
relation CRUD routes (`POST /entities/{id}/relations`,
`PUT /relations/{id}`, `DELETE /relations/{id}` -> `write_relation`) — the
edge panel itself writes nothing, it only calls them. Every successful
write refetches `GET /api/relation-graph` and re-renders, preserving the
live bucket-visibility state (`relGraphBucketState` is untouched by a
refetch).

**Layout: `cose` for global, `concentric` stays for ego.** A world-wide
graph has no natural center, so `isCenter` is forced `false` for every
node in global mode and the concentric layout (which needs one) is
swapped for `cose`, matching the brief's locked choice.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## PLAY_INITIATIVE MODULE SPLIT (BRIEF-0035-a, no schema change)

**Relocation only, on the `play_physical.py` split precedent.** `play_stream.py`
sat at exactly the 1000-line `module_budget.py` cap before TICKET-0034's
BRIEF-0034-c door-travel work needed to add a few lines to it. Rather than
shorten the mandated comment (the check-dodge `module_budget.py`'s own
docstring warns against) or re-add a retired baseline exemption, the
self-contained NPC-initiative cluster — vote, candidate signal assembly,
self-initiated NPC action, group speaker selection, join narration — moved
verbatim into a new `play_initiative.py`. No function body changed; only
the file boundary moved. Sequenced between BRIEF-0034-b and BRIEF-0034-c
so the door-travel work lands with headroom (recorded on both TICKET-0034
and TICKET-0035).

**One-way import edge, no cycle.** `play_initiative.py` imports from
`play.py` only (the shared `_TurnCtx`, `ResponseMode`, and a few
`_load_*`/`_active_members` helpers); it never imports `play_stream.py`.
`play_stream.py`'s single remaining reference to the moved cluster
(`_say_narrate_and_finish` calling `_say_initiative_phase`) is a lazy,
function-body import (`from . import play_initiative as _play_initiative`)
— the same idiom `play.py`/`play_physical.py` already use to call into
`play_stream.py` without a module-load-time cycle. `play.py`'s two
external callers of the moved `_select_group_speaker` and
`_build_join_narration_user` were repointed from `_play_stream` to
`_play_initiative` the same way.

**New generic check: `tooling/verify/checks/import_cycle.py`.** TICKET-0035's
acceptance criteria named this check before it existed ("if present; else
asserted in the live smoke"); the deterministic G1 gate fails closed on a
MISSING check, so the retry built it rather than leaving the criterion
unsatisfiable. AST-based, module-level-only (mirrors `module_budget.py`'s
"nested closures don't count" discipline): only import statements that are
direct children of a module's top-level body count as graph edges, so the
lazy function-body imports this codebase relies on to break cycles are
correctly excluded, not flagged as false positives. Generic over all of
`src/world_engine`, not scoped to this ticket's two files — reusable for
any future module split.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

---

## DOOR SCHEMA, WRITE PATH AND CREATOR AUTHORING (BRIEF-0034-a, schema v1.81)

Fifth step of the spatial / Play mode workstream (0029 geometry -> 0030
collision -> 0031 presence/proximity -> 0032 canvas/WASD -> 0034 doors).
This step ships storage, the sanctioned write path, the creator read
helper and the authoring panel — nothing that resolves, judges or moves.

**A1 — one row per side, unique index `(location_id,
target_location_id)`, pairing derived not defended.** `door(id, world_id,
location_id, target_location_id, x, y, created_at)`. A passage between A
and B is two independent rows, each carrying the point in its own
location's local space; pairing is derived at arrival ("the door of B
that points back at A") and made unambiguous by `idx_door_target`, not by
a defended invariant. Consequence, deliberate: at most one door per
ordered pair of locations.

**A1 escalation guard (locked with A1).** `door` is TERMINAL: no table
may take a foreign key on `door.id` while A1 stands. The A1 -> A2
escalation — one `passage` row carrying both endpoints — stays a
mechanical self-join (a data migration, not a write-path reshape) only
while nothing references a door by id. Trigger: a second passage needed
between the same pair of locations. Enforced by
`tooling/verify/checks/door_terminal.py` (BRIEF-0034-b), not by memory.

**B1 — the door is the spatial manifestation of a `connects_to` edge.**
`write_location_doors` REJECTS a target with no active `connects_to`
relation touching both endpoints (read in either column order, the same
predicate `play.py::_location_neighbours` uses — decision D1 of BRIEF-19
stands, this is the fourth `connects_to` reader, not refactored to share
code). The play-side reader (`cockpit/spatial_doors.py`, BRIEF-0034-b)
FILTERS doors whose edge later disappeared. No cascade, no delete on
either side — the map stays the world's traversability truth.

**No write-time geometry validation, by design.** `write_location_doors`
does not check that the door's point is inside bounds or outside an
obstacle. A write-time check could not stay true: the creator may edit
bounds or obstacles afterwards and strand a door inside a wall without
touching the `door` table. Only a READ-TIME fallback is sound
(`cockpit/spatial_doors.py::resolve_spawn`, BRIEF-0034-b). The relational
gates (target active, `connects_to` live) can go stale the same way,
which is why B1 pairs them with a read-time filter at the same site.

**Write/read surface.** `write_location_doors` (`writes/config.py`, 24th
sanctioned site) is a full-replace per location — the
`write_location_obstacles` shape, copied: delete-then-insert inside the
caller's transaction, validated all-or-nothing before any write
(non-empty target, no self-target, finite coordinates, no duplicate
target in one payload, target is an active location of the same world,
B1 gate). `_location_doors_rows` (`crud/entities.py`) is the
creator-facing read helper: returns EVERY row including orphans
(`edge_live: false`) — the creator-facing surface is deliberately more
permissive than the play-side reader, structural exclusion for which
lives only in `cockpit/spatial_doors.py` (BRIEF-0034-b). Location detail
payload gains `doors: [...]` at the three sites already returning
`geometry` from a live query (`GET /entities/{id}`, `POST /entities`,
`PUT /entities/{id}`) — the write endpoint's own response
(`PUT /entities/{id}/doors`) returns its own fresh `doors` alongside the
existing `geometry`/`subculture_rows` keys, matching
`set_location_geometry`'s shape. `PUT /entities/{id}/doors` is a
SEPARATE endpoint from `/geometry` (the subculture/geometry precedent:
one concern, one full-replace endpoint, one Save button); 404 (not 422)
on a non-location entity.

**Frontend — advisory tier.** A "Portes" panel below "Spatial geometry"
in the location sheet, existing-locations-only (geometry-editor
discipline, no `isNew` draft). Its row set is driven by the location's
`connects_to` neighbours (from `detail.relations`, filtered
`type === 'connects_to'`) — not free text: one row per neighbour, static
name label plus x/y inputs; blank x or y = no door toward that neighbour
(the row is simply not sent on Save). This is structurally why the panel
cannot author a door toward a non-neighbour: the choice surface has no
such row. An orphan door (`edge_live: false`) renders read-only above the
neighbour rows with the destination id and a warning; its remove button
triggers an immediate save (the subculture-row-delete precedent) built
from the currently-valid neighbour rows — full-replace drops every
orphan from any subsequent save by construction, since an orphan's target
is never a live neighbour. No neighbour -> empty-state text, no Save
button.

**Migration discipline.** `migrate_v1_81_door_geometry.py` guards table
existence (`door`) and index existence (`idx_door_target`)
INDEPENDENTLY, so a partially applied prior run (interrupted after
`CREATE TABLE` but before `CREATE INDEX`) completes only the missing
piece on re-run instead of skipping wholesale. Purely additive: no data
copy, no seed rows.

**Scope OUT, deferred:** door resolution, `DOOR_RANGE`, spawn offset,
`cockpit/spatial_doors.py`, `placement.spawn_point`, `GET
/api/spatial/spawn`, `doors_in_range` (BRIEF-0034-b); `POST
/api/spatial/travel` (BRIEF-0034-c); canvas door rendering, spawn-at-door,
the "Aller à X" affordance (BRIEF-0034-d); a `label` column on `door` (no
reader — canvas labels with the destination entity's name, BRIEF-0034-d,
same discipline that kept `kind`/`label` off `obstacle`); `width` /
orientation columns (the walk-through chantier, C3, needs them to punch
an opening — no reader now); locked doors, `access_level` gating, one-way
doors (no reader, named deferrals of TICKET-0034); two passages between
the same pair of locations (structurally excluded by `idx_door_target` —
that index IS the A1 -> A2 trigger); punching a hole in bounds/obstacle
edges (the wall stays solid, the door is a marker); any FK onto
`door.id` (the A1 escalation guard); cascading door deletion when a
`connects_to` relation is deleted (B1 is reject-at-write +
filter-at-read, no cascade, no orphan sweep).

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## DOOR RESOLUTION MODULE AND READ ENDPOINTS (BRIEF-0034-b, no schema change)

Sixth step of the spatial / Play mode workstream. BRIEF-0034-a stored
doors and let the creator author them; nothing read them in play. This
step builds the resolution layer: which doors of a location are live,
which are within reach of a transient position, and where the player
appears on arrival.

**K1 — `cockpit/spatial_doors.py`, on the `spatial_presence.py:39`
precedent.** Three readers span two route modules: `routes/spatial.py`
needs it twice (proximity's `doors_in_range`, the new spawn endpoint) and
`routes/play.py` needs it once for door-travel (BRIEF-0034-c, which
writes and so cannot live in `routes/spatial.py`'s zero-write register).
Without this seam the two route modules would import each other for the
same resolution. The module touches the DB, calls `placement` and
`geometry`, and implements NO math — a `math.hypot` appearing there is a
bug, not a convenience, and `door_terminal.py`'s K1 guard makes that
structural rather than reviewed-by-eye.

**Threshold vs. authority — `DOOR_RANGE` and `DOOR_SPAWN_OFFSET` live in
`placement.py`, not in `spatial_doors.py`.** A dedicated `door.py`
carrying threshold + distance + offset was considered and rejected (K3):
it would fork the sole distance authority and pull placement logic out
of the placement authority for no reason beyond topical grouping.
`DOOR_RANGE` (1.5m) is deliberately distinct from `INTERACTION_RANGE`
(2.0m) — reaching a door handle and being heard across a room are
calibrated separately — but both are compared by the same `distance`
function; two thresholds, one authority.

**`spawn_point`'s ring derivation, and why no orientation column
exists.** A door is a point with no facing — TICKET-0034 deliberately
left `width`/orientation off the schema (BRIEF-0034-a Scope OUT, reserved
for the future walk-through chantier C3) — so "inward" is not
computable. `spawn_point` instead derives a standing point
`DOOR_SPAWN_OFFSET` off the anchor via deterministic rejection sampling
on a ring, seeded by `door_id` (the `_derive_member_position` shape,
copied for the same reason: candidates outside bounds or inside a wall
are rejected, so the survivor is inside the room by construction, no
orientation needed). Total function: saturation (the whole ring boxed
in) returns the anchor itself rather than raising — `resolve_spawn` is
what turns that degenerate case into a center fallback, not
`spawn_point` itself.

**`resolve_spawn`'s three fallback conditions, and why the geometry
check can only be sound at read time.** `anchor="center"` when: no
`from_location_id` (narrative travel, creator god-mode, page reload); no
live return door (the counterpart side was never authored, or B1's
read-time filter dropped it); or a degenerate anchor (the door's point
now sits in a wall or out of bounds). BRIEF-0034-a's write path
deliberately carries no geometry validation, because a write-time check
could not stay true — the creator can edit bounds or obstacles after a
door is authored, stranding it without ever touching the `door` table.
Only a check performed at the moment of resolution can be sound, and
`resolve_spawn` is that moment. The center fallback itself is returned
RAW, unchecked — carrying forward TICKET-0032's documented behavior
(`cockpit/index.html:3311`) verbatim: if the center lies inside an
obstacle, `geometry.clip_segment`'s degenerate-origin rule blocks
movement by design, and the judge never rescues the player. Fixing that
is a creator geometry edit, not adjudicator behavior.

**B1's read half.** `location_doors` is the structural counterpart to
`write_location_doors`'s reject-at-write: a live door additionally
requires an active `connects_to` edge touching both endpoints, checked
at query construction (not filtered after the fact by the caller). This
is the fifth `connects_to` reader (`play.py::_location_neighbours`,
`write_location_doors`, `crud/entities.py::_location_doors_rows`, the
world graph endpoint, now `spatial_doors.py::location_doors`) — decision
D1 (BRIEF-19) stands: reported, not refactored together.

**Scope OUT, deferred:** `POST /api/spatial/travel`,
`_perform_travel`'s `origin_location_id`, `spatial_door_travel.py`
(BRIEF-0034-c — nothing in this step writes, nothing calls
`_perform_travel`); canvas rendering, spawn-at-door on the client, the
"Aller à X" button (BRIEF-0034-d — `GET /api/spatial/spawn` ships with
no caller, the one deliberate exception to "no structure without a
reader" in this ticket); widening or relocating
`_resolve_spatial_location` (BRIEF-0034-c deliberately does not import
it); a `door.py` module (K3, rejected above); orientation/`width` on
doors (C3); caching door resolution across requests (matches
`spatial_presence.npc_positions`, recomputed from scratch every call).

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## DOOR-GATED TRAVEL ENDPOINT (BRIEF-0034-c, no schema change)

Seventh step of the spatial / Play mode workstream. BRIEF-0034-b resolved
which doors are live and where a transient position stands relative to
them; nothing moved the player yet. This step adds the third
`_perform_travel` caller: `POST /api/spatial/travel`, door-gated in-fiction
travel fired from the Play canvas.

**E1 + J1 — the endpoint lives in `routes/play.py`, not `routes/spatial.py`,
because it writes.** `_perform_travel` closes conversations (running
`analyze_window` first), closes `gathering_member` rows, and moves
`character.current_location_id` — `routes/spatial.py`'s zero-write register
(`routes/spatial.py:4-10`) forbids it there. It joins the other two
`_perform_travel` callers (the in-fiction `/say` travel path and the
creator god-mode route) in the same module. The `/api/spatial/` URL prefix
names the player-facing surface, not the module that implements it — the
`scene/join`-in-`routes/scene.py` precedent (BRIEF-0032-a).

**`door_id` carries the neighbour restriction.** The in-fiction callers'
property of only reaching a directly-linked location (C1, BRIEF-16) is
enforced here by re-judging the same predicate BRIEF-0034-b already
resolves: a door toward a non-neighbour cannot be written
(`write_location_doors`) and a door toward a dead `connects_to` edge does
not resolve (`spatial_doors.location_doors`). The handler calls
`location_doors` itself rather than trusting the client's earlier
proximity read — the read filter is live state, not a cached snapshot from
an earlier call.

**Gate hardness is not uniform, and that asymmetry is deliberate.** Checks
1-3 (unknown door, door not in the player's location, door that doesn't
resolve) are judged against canon — a client cannot bypass them. Check 4
(`placement.distance` vs. `DOOR_RANGE`) is good-faith: `position` is
client-declared and the server persists no position (Q1, BRIEF-0031-a), so
it has nothing to verify it against — the same advisory posture as
proximity's G-A gate. Persisting a position to harden check 4 was
considered and rejected: it is exactly what Q1 already ruled out, not a
pending fix.

**G1 — the origin is transient and client-carried.** `_perform_travel`
captures `character.current_location_id` before its own mutation and
returns it as `origin_location_id`; the client passes that value straight
to `GET /api/spatial/spawn` (BRIEF-0034-d) to be placed at the return
door. No `character.last_location_id` column exists and none will — a
transient concern (only meaningful for the instant between one travel call
and the next spawn read) never earns a canon write. The `noop` branch
(origin equals destination) carries no `origin_location_id` key: no reader
wants it there.

**Scope OUT, deferred:** canvas rendering, spawn-at-door on the client, the
"Aller à X" affordance button (BRIEF-0034-d); widening or relocating
`_resolve_spatial_location` (deliberately not imported here — a
routes -> routes import is exactly what K1's `spatial_doors.py` seam
exists to prevent); refactoring the three `_perform_travel` callers to
share a guard chain (they gate differently on purpose: conversation-bound,
god-mode, door-bound); locked doors / `access_level` checks (named
deferral of TICKET-0034, four checks and no fifth); rate-limiting or
debouncing travel server-side (no reader, no requirement); walk-through /
automatic door crossing (C2, permanently out — the later chantier is C3,
an advisory `door_crossed` from `move-check` with the client firing this
same endpoint, which still does not move the player on its own).

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## CANVAS DOORS, SPAWN-AT-DOOR AND THE TRAVEL AFFORDANCE (BRIEF-0034-d, no schema change)

Eighth and closing step of the spatial / Play mode workstream. Every
server surface TICKET-0034 built (door storage, resolution, spawn
resolution, the travel gate) had no caller until this step wires the Play
canvas to them, closing the dette named verbatim at `cockpit/index.html:3311`
— *"TRANSITIONAL SPAWN (TICKET-0032): fixed center until the door chantier
introduces spawn-at-door"* — the ticket's stated request, *"J'apparais
toujours a la porte."*

**C1 — the affordance stays a button, the deliberate pilot shape.** Doors
render on the canvas as a filled diamond (visually distinct from obstacle
polygons and NPC/player circles) labelled with `target_name` — the reader
that kept a `label` column off the `door` table (BRIEF-0034-a Scope OUT).
A door within reach gets the same ring-stroke reachable style already used
for in-range NPCs; no second visual language for "reachable" was
introduced. The `POST /api/spatial/travel` call site this step wires up is
the same one the later walk-through chantier (C3) will reuse unchanged —
C3 adds an advisory `door_crossed` from `move-check`, the client still
fires this endpoint, which still does not move the player on its own.

**D1 — no new server cadence.** `doors_in_range` rides the existing
on-stop proximity call (the 200 ms debounce from BRIEF-0032-c); the door
affordance button is rendered from the same response that already
populates "Parler". No door polling, no per-frame distance check.

**G1 — the origin is page-scoped with a one-arrival lifetime.**
`_spatialArrivalFrom` is a plain module-level variable, written only by a
successful travel's `origin_location_id` and consumed (then cleared)
exactly once by the `spatialActivate()` call that follows — never
`localStorage`, `sessionStorage`, a cookie, or the URL. A reload, a
narrative travel, or a creator god-mode move loses it by design and costs
a center spawn, never an error; `GET /api/spatial/spawn`'s own fallback
chain (BRIEF-0034-b) absorbs all of those cases identically.

**The client is not the judge — verified, not just asserted.** The door
list, the reachability flag, and the spawn point are all server responses
rendered as-is; no `Math.hypot`, `localStorage`, or `sessionStorage` was
introduced in the spatial tab (grepped clean). A refused travel (404/409)
re-enables the clicked button, re-fires the proximity call to re-sync the
affordance with what the server actually allows, and shows no modal or
alert — a stale client picture correcting itself IS the message, matching
proximity's own advisory posture (G-A).

**Scope OUT, deferred:** walk-through / door-crossing (C2, permanently
out); a door hitbox or blocking the door point; a graphical door editor on
the creator's geometry panel (deferred alongside the graphical obstacle
editor, D'2, TICKET-0029); showing orphan (`edge_live: false`) doors in
play (creator-only); any refactor of the spatial tab beyond the door pass
(the ungoverned 8,834-line frontend — the pull is real, reported, not
acted on).

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## NPC LINK AGENT — STAGING STRATA, RETENTION, JOURNAL (BRIEF-0036-a, schema v1.82)

First step of TICKET-0036 (batch AI authoring of NPC relations/knowledge,
plus a final coherence pass). This step builds only the ephemeral
substrate the later passes stage into — no LLM call, no canon write, no
commit endpoint yet.

**Numbering note.** RECON-0036/TICKET-0036/BRIEF-0036-a through -d were
authored and deposited under the number 0035, which by the time of
execution had already been spent (merged) by the unrelated play-stream-
extraction ticket. Renumbered 0035 -> 0036 wholesale (filename + every
in-content id/front-matter reference) before branching, per the "IDs are
computed, never chosen" rule — no content change beyond the number.

**A1 — two new tables, EPHEMERAL stratum, not canon.** `link_batch` /
`link_batch_row` join `gathering`/`pass_play` in `models/ephemeral.py`:
never listed in `canon_write_policy.txt`, never a `proposed_mutation`,
never creator-CRUD-reviewed. The commit step (0036-c) writes canon
exclusively through the existing `write_relation`/`write_knowledge`
chokepoints — this ticket adds ZERO new canon-write sites, made
structural by the new `tooling/verify/checks/link_agent_strata.py` gate
(fails if either table ever appears in the canon policy or a `writes/`
module, and fails if the `LinkBatch`/`LinkBatchRow` model classes are
referenced from anywhere outside `routes/link_agent.py`,
`link_author.py`, `models/ephemeral.py`, and `cockpit/app.py`'s purge).

**R1 + journal — retention is legal by construction, not a "history is
sacred" exception.** Closed batches (`committed`/`abandoned`) are purged
to the last 2 at cockpit startup (`purge_closed_link_batches`,
`cockpit/app.py`, wired to a FastAPI `startup` event — the first one this
codebase has needed). This is sound specifically BECAUSE canon is
untouched by the purge: the durable trace of a run is the append-only
generation journal under `~/.world_engine/link_agent_journal/`
(`link_author.journal_append`), an absolute home-anchored path outside
the git tree and outside the DB entirely, so it survives the purge by
construction. `link_author.py` also owns `resolve_roster` (S1): a
code-owned BFS over `location.parent_location_id`, zero model call, that
resolves a multi-location root selection into the present-NPC roster and
`N*(N-1)/2` pair count surfaced for creator confirmation before launch.

**Staging JSON columns are allow-listed, not relationalized, at this
step.** `LinkBatch.scope`, `LinkBatch.coherence_findings`, and
`LinkBatchRow.payload` are `json_ui_boundary` allow-list entries, same
non-UI-consumed status as `Conversation.scene_state` — the first
structured-field UI consumer (0036-d renders them readonly first) must
relationalize if it ever needs to query into them.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## NPC LINK AGENT — PAIR PASS (BRIEF-0036-b, no schema change)

Second step of TICKET-0036: one LLM call per NPC pair proposes relations
and knowledge; code judges everything before staging into `link_batch_row`
(still ephemeral — see BRIEF-0036-a above, unchanged by this step).

**Coverage is code-owned, never the model's.** `enumerate_pairs` computes
every unordered pair over the batch's roster, sorted ids, MINUS pairs that
already hold a canon `relation` in either direction (F1) — one query over
the whole id set, not N^2, reusing `_find_relation_pair`'s both-directions
semantics. Excluded pairs are journaled (`pair_skipped_existing`) and never
reach the model. `POST /api/link-batches/{id}/run-next` processes exactly
one pending pair per call and recomputes "pending" (enumerated pairs minus
pairs already holding any row in this batch) fresh every call — resume
after a restart costs nothing extra.

**A silence is never a verdict.** The model must return an explicit
`{"verdict": "links"|"no_links", "links": [...]}`; a `no_links` verdict
still writes one `link_batch_row` (`kind='no_links'`, `payload={}`) so it
is visibly distinct from "not yet processed." A parse failure or a missing/
invalid `verdict` writes NO row, journals `pair_parse_error` with the raw
response, and surfaces as a 502 — the pair stays pending; a plain retry
(`run-next` again) is the whole recovery path, no retry budget in code.

**Per-item drop policy.** Within a `"links"` verdict, each item is
validated independently: relation `type` against a vocabulary deliberately
NARROWER than the creator-CRUD list (`connects_to`/`controls` excluded —
those are location-map topology/control edges, structurally impossible for
this agent to propose, asserted at import time in `link_author.py`),
`direction` against `mutual|a_to_b|b_to_a`, `intensity`/`share_threshold`
clamped 1-100, knowledge `level` against the canonical ladder
(`writes.KNOWLEDGE_LEVELS`), `holder` against `a|b`. An invalid item is
dropped alone (journaled `link_item_rejected` with the reason) — it never
fails the whole pair.

**D3 — the model proposes a holder, code alone derives a subject.** Every
staged knowledge payload's `subject` is code-stamped `npc:{other_id}` in
exactly one function (`_build_knowledge_row`); the model's JSON never
carries a `subject` field and none of its output ever reaches that key.
`tooling/verify/checks/link_agent_strata.py` gained a third guarantee: an
AST scan asserts the `"subject"` key of a knowledge payload is built in a
single function, as an f-string carrying the `npc:` literal, and never as
a passthrough of the model's own `item.get(...)` output.

**Creator-surface exception, named (RECON-0036 R-4).** Pair-context
assembly (`build_pair_context`) never reads `character.secrets` — same
structural exclusion as every other context assembler. It DOES read
existing `knowledge` rows with `is_secret=TRUE` when they are already
about the other member of the pair (matched on the same `npc:{id}` subject
convention this step introduces), because the link agent's output is
reviewed by the creator before any commit — the one context assembler
allowed this inclusion, and only for this reason.

**Prompt wiring.** New registry key `npc_link_pair` (surface="authoring",
`world_scoped=False`, single global template like the other authoring
prompts), seeded as `pt-npc-link-pair`. Call site
`link_author.py:_load_pair_template`; the pair prompt substitutes
`{world_name}` into the system text and `{a_sheet}`/`{b_sheet}`/
`{shared_context}` into the user text, both via chained `.replace()` (H1) —
never `.format()`.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## NPC LINK AGENT — COHERENCE PASS AND COMMIT (BRIEF-0036-c, no schema change)

Third and final step of TICKET-0036: a coherence pass over the staged
batch AND the full canon character graph (E1-tout-le-graphe), producing
pre-validated one-click patches (W-ok), plus the commit endpoint that
turns accepted staged rows into canon. `link_batch`/`link_batch_row` stay
ephemeral (BRIEF-0036-a, unchanged); `coherence_findings` (shipped at
0036-a) is the only column this step writes to on `link_batch`.

**Two-phase contract, phase 1 never blocked by phase 2.** Mechanical
findings (`_mechanical_findings`, code, no model call) always run first
and are persisted even if the model call or parse fails — duplicate
staged pairs (same pair + kind + type/subject discriminator), a staged
relation whose pair gained a canon relation since generation (F1 re-run,
`_canon_relation_exists`), payload vocab/bounds defense-in-depth vs
0036-b, and a D3 subject-stamp mismatch. Model findings (phase 2) run
`link_context.serialize_staged_batch`/`serialize_canon_graph` through the
`npc_link_coherence` template, parsed via `llm_parse.extract_object` only.
A parse failure or malformed `findings` key journals
`coherence_parse_error`, persists the phase-1 findings, and raises 502 —
`batch.coherence_status` stays NULL (coherence has not "run" until phase 2
also succeeds), so a failed pass cannot silently unlock commit.

**R-1 budget — truncation is a row-boundary fact, not a best-effort
guess.** `serialize_canon_graph` sorts canon relations (structural
exclusion of `connects_to`/`controls`, same `context.RELATION_GRAPH_EXCLUDED_TYPES`
constant now shared with the relation-graph endpoints — extracted out of
`cockpit/crud/relations.py` at this step, never re-typed) and knowledge
rows (subject `npc:{id}` OR `entity_id` in the roster) by how many
endpoints touch the batch's NPC roster, then adds rows one at a time
until the next row would exceed `CANON_SERIAL_BUDGET` (24000 chars) —
truncation always lands between rows, never mid-JSON. A truncated pass
sets `coherence_status='partial'` and journals `coherence_truncated`;
Nia may still commit a partial pass (the refusal at commit is only for
"never ran").

**W — the patch whitelist gate.** Every model finding's `patch` is
validated BEFORE storage (`_validate_patch`) and again at apply time
(`apply_finding`'s time-of-use re-check, same function): target exists
(staged row of this batch, not rejected; or a canon relation/knowledge row
of this world), field is on the whitelist (staged: any existing payload
key EXCEPT identity fields — ids, `mode`, `subject`, session bookkeeping,
never patchable, on either side, not just canon; canon relation:
`intensity`/`notes`/`type`/`direction`/`visible_to_b`; canon knowledge:
`level`/`content`/`source`/`is_incorrect`/`is_secret`/`share_threshold`),
and `new_value` passes the same vocab/clamp validation as 0036-b's item
builders (`_coerce_patch_value`) — a canon relation `type` patch is
checked against the narrower link-agent vocabulary, never the full
creator vocabulary, so a patch can never introduce `connects_to`/
`controls` as a "social" edge. Invalid -> `validation='rejected'` +
`validation_reason`, `patch` stripped to `null`, finding kept as a flag —
never silently dropped. The UI contract (0036-d): only
`validation='valid'` findings with a non-null `patch` are ever
button-eligible.

**Apply and commit are the ONLY places this ticket writes canon**, and
both do so exclusively through `write_relation(mode="set", ...)` /
`write_knowledge(mode="update", ...)` — never a bespoke write. A canon
patch merges the finding's one field into the row's CURRENT other fields
before calling the helper (so an untouched field is never silently reset
to a default); the helper's own history-snapshot-before-overwrite
behavior (history is sacred) is unchanged and untouched by this step.
Commit re-runs the F1 check per relation row immediately before writing
(`_canon_relation_exists`, RECON-0036 s.9) — a pair that gained a canon
relation since generation, including one gained by an EARLIER row in the
same commit transaction, is skipped and surfaced in `{skipped: [...]}`,
never silently double-written. Knowledge rows carry no such conflict risk
and always write. Commit refuses (409) when `coherence_status` is NULL;
`'partial'` is an allowed commit, `'ran'` is the ordinary case.

**Structural guarantee, extended (`link_agent_strata.py`).** A fourth
AST check: neither `cockpit/routes/link_agent.py` nor `link_author.py`
may contain a direct `db.add(Relation(...))` / `db.add(Knowledge(...))`
or raw SQL INSERT/UPDATE touching `relation`/`knowledge` — the coherence
patch and commit paths are structurally forced through the two
chokepoints. `link_context.py` (new, serialization only — no writes) was
added to the reference-scope allowlist alongside the existing four files.

**Prompt wiring.** New registry key `npc_link_coherence` (surface=
"authoring", `world_scoped=True`, unlike `npc_link_pair`'s `False` —
canon serialization is genuinely per-world), seeded as
`pt-npc-link-coherence`. Call site
`link_author.py:_load_coherence_template`; substitutes `{world_name}`
into the system text and `{staged_serialized}`/`{canon_serialized}`/
`{truncation_marker}` into the user text via chained `.replace()` (H1).

Routes: `POST /api/link-batches/{id}/coherence`,
`POST /api/link-batches/{id}/findings/{index}/apply`,
`POST /api/link-batches/{id}/commit` — all thin wrappers in
`cockpit/routes/link_agent.py` delegating to `link_author.run_coherence`/
`apply_finding`/`commit_batch`.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## NPC LINK AGENT — FRONTEND ON THE RELGRAPH PANEL (BRIEF-0036-d, no schema change)

Fourth and closing step of TICKET-0036: the creator UI for the whole
0036-a/b/c flow, attached to the existing NPC relation graph panel
(`#creation-npc-relgraph`, "Agent liens" button in its head bar) — no new
creation tab, `CREATION_TABS` untouched. All new JS is `linkAgent*`,
appended after the `relGraph*` block in `cockpit/index.html`; the panel's
entire content is rendered by JS into one empty `#linkagent-panel` div,
matching the file's existing dynamic-panel convention (relgraph info card,
mutation review cards).

**One backend addition: `PATCH /api/link-batches/{id}/rows/{row_id}`**
(`link_author.patch_row`). Edits a staged row's payload fields and/or
`row_status`, staging-only (batch must be `open`), reusing
`_coerce_patch_value` — the SAME vocab/clamp gate BRIEF-0036-c's coherence
patch pipeline uses — so a field edit here can never introduce a value the
pair-pass or the coherence patch would have rejected. `link_agent_strata.py`
needed no change: this function writes only `link_batch_row`, never
`Relation`/`Knowledge`.

**Supersedes BRIEF-0036-a's "readonly" prediction.** That step's
`json_ui_boundary` allow-list comment for `LinkBatchRow.payload` assumed
0036-d would render the staged payload readonly. The brief actually locked
inline editing (relation type/direction/intensity/notes; knowledge
level/content/source/is_incorrect/is_secret/share_threshold), so the
comment is corrected in this step rather than left stale. This does not
weaken the `json_ui_boundary` guarantee: every edit goes through the
per-field PATCH validation gate above, never a raw JSON blob write, and the
row is staging that becomes a real relational `relation`/`knowledge` row on
commit — not a durable UI-query surface. The allow-list's actual
requirement (relationalize on the FIRST consumer that needs to QUERY into
the JSON, e.g. list/filter/report) is unaffected and still open.

**Server-truth resume, no client state.** The run loop is a plain
sequential `fetch` loop (`POST run-next` until `{done:true}`) — no SSE/
websocket. "Pause" only flips a client-side flag the loop checks between
iterations; "Reprendre" calls the same loop function again. Reopening the
panel (or the cockpit itself) re-derives everything from
`GET /api/link-batches` (open-batch badge) and
`GET /api/link-batches/{id}` (rows) — no browser storage of any kind. A 502
from `run-next` (pair parse failure, BRIEF-0036-b) leaves the batch
untouched server-side and is surfaced as a blocking "Réessayer" state
client-side; the loop never silently continues past it.

**Commit gate mirrors the server exactly.** "Committer le lot" is disabled
client-side unless `coherence_status` is `ran` or `partial` — the same
condition `commit_batch` enforces server-side (409 otherwise) — so the
button is a UX convenience, never the actual gate. NPC names shown in the
pair groups and roster preview are resolved by re-calling
`POST /api/link-batches/preview` with the batch's own
`scope.root_location_ids` (no new read endpoint added for this — the
preview endpoint already returns exactly `{id, name}` pairs over the same
roster).

Ticket closed: TICKET-0036 status -> `live-gate` after this step's
`/verify` and PR.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## DOOR-WRITE VALIDATION EXTRACTION (BRIEF-0038-a, no schema change)

**Extraction, not exemption, on the TICKET-0035 precedent.**
`write_location_doors` (`writes/config.py`) landed at 99 physical lines via
BRIEF-0034-a (2026-07-20) — over the R1 80-line ceiling — because the
transition baseline had already been retired at TICKET-0028/BRIEF-0028-f,
so it was born over budget rather than exempted into it. The failure
surfaced only in TICKET-0037's verify run (the check scans all of `src/`;
0037 does not touch this file). TICKET-0034 is closed, so a dedicated
remediation ticket (TICKET-0038) owns the fix, the same shape TICKET-0035
used for the sibling `module_budget` over-`play_stream.py` case: split the
unit, never re-add the retired baseline.

**Per-item validation moved verbatim into a new private, read-only
helper, `_validate_doors_payload`**, defined immediately above
`write_location_doors` in the same module. It owns the `clean`/
`seen_targets` loop — non-empty target, no self-target, no duplicate
target within one payload, finite coordinates, target-is-an-active-
location-of-this-world, and the B1 `connects_to` double-`select` gate
(still the fourth reader of that relation, per BRIEF-19's D1 — not
deduplicated here either) — and returns the cleaned
`(target_location_id, x, y)` tuples. `write_location_doors` keeps its
public signature, full docstring (including the NO-GEOMETRY block), and
the `DELETE`-then-insert unchanged; it now calls the helper for the
`clean` list. No import changed (the helper is intra-module). Both
functions land under 80 lines by construction: `_validate_doors_payload`
at 72, `write_location_doors` at 48.

**Canon-write site count is unchanged.** `write_location_doors` remains
the sole sanctioned writer of `door` rows; `_validate_doors_payload`
performs no write. `canon_write_policy.txt` has a zero-line diff.

**Process finding, for follow-up.** Under the same baseline-retired
regime, `module_budget` fail-closed on `play_stream.py` mid-TICKET-0034
(surfaced as TICKET-0035), but `function_length` did NOT fail-closed on
`write_location_doors@99` landing via BRIEF-0034-a — it let the merge
through, and the violation only surfaced later, incidentally, via
TICKET-0037's unrelated verify run. Preliminary read: `function_length.py`
is a G1 gate run by `/verify` at ticket close, and TICKET-0034's own
`/verify` pass evidently ran before this function crossed 80 lines, or
the check's per-ticket scope at that time did not force a fresh full-tree
scan the way the current `/verify` does — the exact mechanism is not yet
confirmed. Escalate for a deliberate look at whether `function_length.py`
(and any sibling line/def-count check) needs to run against the full
tree, not a ticket-scoped diff, on every ticket's close — the evasion
class (an over-budget unit born clean of its own ticket's verify, caught
only by a later unrelated ticket) should not repeat silently.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

---

## NPC GROUP AGENT — STAGING SUBSTRATE (BRIEF-0037-a, schema v1.83)

First step of TICKET-0037 (splitting NPC creation out of the region wizard
into a standalone batch agent, mirroring TICKET-0036's link agent). This
step builds only the ephemeral substrate the later passes stage into — no
LLM call, no canon write, no commit endpoint, no frontend yet.

**G1 — sibling ephemeral tables, entity grain, not a `link_batch`
generalization.** `npc_batch`/`npc_batch_row` join `link_batch`/
`link_batch_row`/`gathering`/`pass_play` in `models/ephemeral.py`: never
listed in `canon_write_policy.txt`, never a `proposed_mutation`, never
creator-CRUD-reviewed. `npc_batch_row` payload is one full NPC draft per
row (entity grain) versus `link_batch_row`'s one pair-verdict per row (pair
grain) — deliberately NOT a polymorphic table, since the two agents stage
structurally different things. Made structural by the new
`tooling/verify/checks/npc_agent_strata.py` gate, scoped to the two
guarantees this step can actually prove (policy/writes-dir absence,
reference-scope narrowing to `cockpit/routes/npc_agent.py`,
`npc_group_author.py`, `models/ephemeral.py`, `models/__init__.py`,
`cockpit/app.py`) — the D3-style subject-stamp and no-direct-canon-write
scans arrive with BRIEF-0037-c's commit path, once there is a commit path
to scan.

**Per-agent open-batch rule.** `npc_batch` and `link_batch` each enforce
their own single-open-batch-per-world 409 independently — an open batch of
one agent never blocks the other, since they stage disjoint things (NPC
drafts vs. NPC-pair relations/knowledge) and TICKET-0037's own J1 handoff
(BRIEF-0037-c) deliberately chains a fresh link batch onto a just-committed
NPC batch.

**Purge parametrization.** `cockpit/app.py`'s `purge_closed_link_batches`
is refactored into a private, model-parametrized `_purge_closed_batches(db,
batch_model, row_model, row_fk_attr)` carrying the same last-2/
`closed_at desc`/`offset(2)` logic, with `purge_closed_link_batches` and
the new `purge_closed_npc_batches` as thin named wrappers — both still
called from the one FastAPI `startup` hook. Legal by construction for both
tables' ephemeral stratum, per each table's own NOTE in
`models/ephemeral.py`; each agent's append-only journal
(`~/.world_engine/link_agent_journal/`, `~/.world_engine/npc_agent_journal/`)
carries the long memory the purge discards from the DB.

**Corollary: one new `canon_write_policy.txt` wildcard entry, no new canon
site.** `_purge_closed_batches`'s generic `Type[SQLModel]` parameters defeat
`single_canon_write.py`'s static per-table write attribution (it resolves a
literal model class or a `list[Model]`/`Optional[Model]` annotation, not a
type-parameterized generic) — the same class of case the checker already
carves out for `delete_world_cascade`. Added
`src/world_engine/cockpit/app.py::_purge_closed_batches *` to
`ALLOWED_SITES` with a comment explaining why: it never writes a CANON
table (both call sites pass only their own agent's EPHEMERAL batch/row
pair), verified instead by each agent's own strata check. The comment
deliberately never spells out either ephemeral table's literal name, so it
cannot trip the strata checks' own text-substring guarantee.

**C2 refactor-over-duplication: `link_author.expand_location_ids`.** The
BFS descent embedded in `link_author.resolve_roster` is extracted verbatim
into a module-level `expand_location_ids(db, root_ids) -> set[str]`;
`resolve_roster` now calls it, behavior byte-identical. `npc_group_author.
resolve_vocabulary` reuses the same function for the NPC agent's
placement vocabulary (expanded location set + the active world's active
faction entities) — the same S1 code-owned descent, no model call, shared
rather than re-implemented.

**No structure without a reader.** Every new column has a named consumer
in briefs b/c: `payload` -> generation output then the commit path,
`line_index` -> review grouping back to its spec line, `npcs_done` -> the
BRIEF-0037-b run driver's progress counter. No coherence columns on
`npc_batch` (I1: this agent gets no model coherence pass — mechanical
checks only; social coherence stays the link agent's downstream territory).

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## NPC GROUP AGENT — GENERATION RUN (BRIEF-0037-b, no schema change)

Second step of TICKET-0037: makes a staged `npc_batch` (BRIEF-0037-a)
runnable — one `generate_entity_draft("character")` call per NPC (H1),
a single batch-level placement plan for unanchored spec lines, goals
attached per draft (F), and inline row-review edits. Still no canon write,
no commit endpoint, no frontend (BRIEF-0037-c).

**H1 — exact count by construction, no floor, no clamp.** `_line_units`
flattens every spec line's `count` into a fixed run order (`(line_index,
ordinal)` per NPC); unit `k` of the run is always `_line_units[k]`.
`run_next_npc` (mirror of `link_author.run_pair`) processes exactly one
pending unit per call: `ok: False` from `generate_entity_draft` journals
`npc_parse_error` and raises 502 with the unit left pending (`npcs_done`
unchanged) — a silence is never a verdict, and there is no retry loop or
top-up construct anywhere in this module (the BRIEF-40 pattern this ticket
retires).

**Placement plan — one model call per batch, S1-resolved.**
`plan_placements` runs at most once, triggered by the first `run_next_npc`
call, covering every spec line lacking a pinned `location_id` in a single
`chat(..., format="json")` call parsed through `llm_parse.extract_object`
only. Returned location names are matched case-insensitively against the
expanded location set in code (S1 — the model proposes, code resolves); a
whole-call failure or a per-line count mismatch leaves that line's slots at
`None`, individually resolved to `scope["root_location_id"]` at
unit-resolution time with the verbatim note "Placement non résolu — replié
sur la racine". The plan is cached into `batch.scope["placement_plan"]`
(JSON round-trip forces string keys, converted back to `int` on read) so a
restart never re-triggers the call. A placement failure never aborts the
batch or blocks the count contract — every unit still gets a location.

**Pin always overrides the model.** A pinned line's `faction_id` /
`location_id` (from the batch's own `scope["lines"]`) resolve before the
generation call and are applied AFTER it: `draft["public"]["faction_id"]`
is overwritten with the pin regardless of what the model's own
`faction_name` resolved to (that resolution is advisory only on a pinned
line). An unpinned line keeps `generate_entity_draft`'s own resolved
`faction_id` as-is, including `None`.

**Name dedup stages, never drops (BRIEF-42 `_name_key` posture).** Each
generated name is checked against (a) this batch's own staged non-rejected
rows and (b) active `entity` names of the world, using a local
`_name_key` (apostrophe/whitespace/accent-composition fold — same posture
as `region_author._name_key`, not a cross-module reuse of that private
helper). A collision stages the row anyway with the verbatim note "Nom en
collision avec {name} — à éditer avant commit"; the creator resolves it at
review, never a silent retry.

**Goals attach per draft, never block it (F/G1).** After a successful
character draft, `generate_npc_goals` runs once with `faction_goals` read
from the FINAL resolved faction's `Faction.goals` (post-pin-override, None
when factionless) — same call as the region wizard's existing gate, one
per NPC, no batching. A goal-generation failure appends a note and leaves
`payload["goals"]` `None`; it never drops or blocks the row.

**Composite brief, adapted not reused verbatim.** `_compose_group_npc_brief`
mirrors `region_author._compose_npc_brief`'s prose style but with a
different peer set: the group brief, this spec line (description + count),
every other spec line's description, the pinned faction's name + truncated
(300 char) description when pinned, the resolved location's name, and — for
every already-staged sibling of the same line — an explicit anti-clone
block naming each sibling and instructing the model to differ in name,
temperament, and angle on the shared role.

**Row PATCH, sibling of `link_author.patch_row`.** `patch_npc_row` edits
one staged row's payload and/or `row_status` while the batch stays open.
Patchable fields route to different parts of the nested payload —
`name`/`description`/`appearance`/`backstory`/`aversion`/`physical_tier`/
`faction_id` into `payload["draft"]["public"]`, `location_id` into the
payload's own top level (re-validated against `scope["expanded_location_ids"]`),
`goals.long`/`goals.shorts` into `payload["goals"]` — ids of batch/row,
`line_index`, and `kind` are never reachable through this vocabulary.
`row_status` is reversible between `proposed`/`rejected` while the batch
stays open, same as the link agent's row PATCH.

**Prompt wiring.** New registry key `npc_batch_placement`
(surface="authoring", `world_scoped=False`, single global template),
seeded as `pt-npc-batch-placement`. Call site
`npc_group_author.py:_load_placement_template`; the placement prompt
substitutes `{group_brief}`/`{spec_lines}`/`{candidate_locations}` into the
user text via chained `.replace()` (H1), never `.format()`.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## NPC GROUP AGENT — COMMIT, COCKPIT SURFACE, LINK HANDOFF (BRIEF-0037-c, no schema change)

Third step of TICKET-0037: closes the loop opened by BRIEF-0037-a/b — the
atomic commit of accepted `npc_batch_row`s into canon, the "Agent PNJ"
cockpit panel mirroring the link agent's, and the J1 handoff that prefills
a link batch on the same region root. After this step the pipeline
regions -> NPCs -> liens is live end-to-end; the region wizard's legacy NPC
path is untouched until BRIEF-0037-d retires it.

**Commit lives route-side, not in `npc_group_author.py` — region-commit
layering, not link-agent layering.** `_commit_npc_batch`/`_commit_npc_row`
are `cockpit/routes/npc_agent.py`-module functions mirroring
`routes/regions.py::_commit_region_npcs` + `commit_region`'s transaction
shape (try/rollback, exactly one `db.commit()`), deliberately NOT the link
agent's own precedent (`link_author.py::commit_batch`, author-module-side).
Same "canon writes live route-side, the author module stays generate-only"
split as the region commit. `_commit_npc_row` is split out from
`_commit_npc_batch` to hold the R1 80-line ceiling on the per-row NPC +
knowledge + goals write.

**No new `canon_write_policy.txt` entry — the commit rides only
already-allowed sites.** `_commit_npc_row` calls `_crud._create_entity_core`
(entity + character + optional primary faction membership),
`_crud._create_knowledge_core` per `secret.knowledge` item (`is_secret=True,
share_threshold=50, is_incorrect=False, source=None` — byte-same posture as
`_commit_region_npcs`), and `write_npc_goal` for the attached goals block —
all three already-sanctioned sites. Neither `_commit_npc_batch` nor
`_commit_npc_row` performs a direct `db.add(Entity(...)/...)`, so — exactly
like `_commit_region_npcs` itself — no ALLOWED_SITES entry is added. Made
structural by `npc_agent_strata.py`'s new guarantee 3 (link_agent_strata.py
guarantee-4 precedent): an AST scan of `routes/npc_agent.py` and
`npc_group_author.py` for direct `db.add(Entity(...)/Character(...)/
FactionMembership(...)/Knowledge(...)/NpcGoal(...))` or raw SQL touching
those tables.

**No-partial-commit guard (I1 precedent).** `_commit_npc_batch` refuses
(409) unless `batch.status == "open"` and `npcs_done == npcs_total` —
"generation incomplete — run or abandon" is the only escape hatch, deliberate
per Scope OUT (no "commit what's generated so far"). No coherence gate
either (I1 carries forward from BRIEF-0037-a). Rows are re-read from the DB
by `row_status in ("proposed", "edited")` — server-authoritative, the
client's rendering is never trusted; a `kind == "failed"` row (defensive,
not currently produced by `run_next_npc`) is skipped rather than committed.

**J1 handoff reuses the link agent's own creation route verbatim.** The
cockpit's "Générer les liens pour ce groupe" button calls the EXISTING
`POST /api/link-batches` with `{root_location_ids: [batch.scope.
root_location_id]}` — no new backend route, no link-agent behavior change.
A 409 (a link batch already open) surfaces as a plain warning banner and is
never retried automatically (Scope OUT: no "chained auto-run" of pairs).

**Cockpit surface — structural mirror of the link agent's, `.linkagent-*`
CSS reused wholesale.** `npcagent-launcher-btn`/`npcagent-panel` sit in the
same relgraph panel head as `linkagent-launcher-btn`/`linkagent-panel`
(index.html, NPC tab's `creation-npc-relgraph` block), "Agent PNJ" preceding
"Agent liens" — the region -> NPC -> liens pipeline order. `npcAgent*` JS
mirrors `linkAgent*`'s shape (reset/checkOpenBatch/toggle/launcher/run
loop/review/commit) with two deliberate departures: (a) the location picker
is a single-select radio, not a multi-select checkbox tree (C1 — one root
per batch, intra-region v1); (b) the run driver's stop condition is a
message-text check on the 409 ("already fully generated") rather than an
explicit `{done:true}` response field, since `run_next_npc` signals
completion via HTTPException, not a sentinel payload — `api()`'s thin fetch
wrapper only ever surfaces `Error(detail)`, no status code. `npcAgentReset`
is wired into `_relGraphReset` (world switch / tab re-entry), same as
`linkAgentReset`.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## REGION NPC RETIREMENT (BRIEF-0037-d, no schema change)

A1 (TICKET-0037 intake): hard retirement of the region pipeline's NPC
machinery, superseding BRIEF-39 (density floor) and BRIEF-40 (top-up
clamp) now that the NPC group agent (BRIEF-0037-a/b/c) is live end-to-end.
Region generation becomes factions + locations only — every character
enters the world exclusively through the group agent, which the region
commit hands off into via the existing J1 handoff button. Removal, not a
bypass flag (S-norme: no dead code); their ARCHITECTURE_DECISIONS.md
entries stay as written (append-only), superseded by this one.

**`region_author.py`** loses `MIN_NPCS_PER_FACTION`/`MIN_FACTIONLESS`,
`_load_manifest_topup_template`, `_normalize_npc_placement` (and the npcs
branch of `_normalize_manifest` — the normalized manifest shape is now
`{concept, factions, locations}`), `_compose_npc_brief`, `_npc_deficits`,
`_topup_blocks`, `_run_npc_topup` and its call site, `_draft_one_npc`,
`_draft_npcs`, and the Stage-3 block of `generate_region_draft`. Pure
shrinkage — module and function-length budgets hold on their own.

**`cockpit/routes/regions.py`** loses `_commit_region_npcs` and its call in
`commit_region`; the commit's `committed` response dict drops its `npcs`
key. `write_npc_goal` and the `json` import both lose their only caller
and are dropped. `npc_goal_generation`'s registry entry needed no edit —
it never listed a region call site (only `entity_author.py`'s pre-fill
loader), so its surviving readers (single-NPC pre-fill, backfill) are
unaffected.

**`scripts/seed_pilot.py`**: `pt-region-manifest`'s system prompt is
rewritten to a three-key contract (`concept`/`factions`/`locations`) with
the density-floor paragraph removed; S2 (a head with an existing v1 never
has its text touched again) means an already-seeded DB keeps the OLD
npcs-section wording until re-seeded from a virgin head. The seed stops
upserting `pt-region-manifest-topup` entirely — its `prompt_template` head
(if a DB was ever seeded through TICKET-0036 or earlier) is left exactly
as it stands, untouched, `is_active` unchanged, `prompt_version` history
intact (history is sacred); a world never seeded with a predecessor never
gets the row.

**`prompt_registry.py`** drops the `region_manifest_topup` entry outright
(its only call site, `_load_manifest_topup_template`, no longer exists).

**`cockpit/index.html`**: the manifest checkpoint's PNJ section and
`regionManifestAddNpc` are gone (`{concept, factions, locations}` only);
the review tree's `regionRenderNpc` and its call sites (faction member
counts, location nodes' `npcsHere`) are gone, along with `regionCascade`'s
`npcPlaceable`/`npcFactionEffective` and the now-dead `acceptedFactions`
they were the sole reader of. The full-sheet editor (BRIEF-0033-c) drops
its entire `type === 'npc'` branch — knowledge-row and goals-row editors
included — and `_regionSheetNode` narrows to location/faction. The
`.region-npc-row` CSS rule is removed with its only consumer.

**New fail-closed gate, `tooling/verify/checks/region_npc_retirement.py`**
(door_terminal.py idiom): `region_author.py` and `regions.py` carry none
of the nine retired tokens; `region_author.py` additionally carries zero
case-insensitive `"npc"` substrings; `prompt_registry.py` carries no
`region_manifest_topup` token. A missing target file fails closed, never
a vacuous pass.

**CLAUDE.md**: the region-generation invariant's described commit skeleton
(`parent_location_id`, primary faction membership, `current_location_id`)
was entirely NPC wiring — rewritten to `parent_location_id` + faction role
vocabulary only, with a pointer to this ticket.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## PURGE CHILD-BEFORE-PARENT DELETE ORDERING FIX (BRIEF-0037-e, no schema change)

Live-gate regression on TICKET-0037: the shared retention purge
`_purge_closed_batches` (`cockpit/app.py`) crashed app startup with
`sqlite3.IntegrityError: FOREIGN KEY constraint failed` as soon as more
than 2 closed batches existed for either staging agent — the exact
condition the group agent's live test finally produced. Latent since
TICKET-0036 (`purge_closed_link_batches` had the identical body); 0037
generalized it into the shared helper and surfaced it once a second agent
started closing batches too.

**Root cause.** The batch/row models (`link_batch`/`link_batch_row`,
`npc_batch`/`npc_batch_row`) carry only a column-level `foreign_key=` on
the row model — no ORM `relationship()`. Per-object `db.delete(...)` gives
the SQLAlchemy unit-of-work no child-before-parent dependency edge; the
next loop iteration's `select(...)` autoflushes, and the UOW emitted the
parent batch's DELETE before its rows' DELETEs. `PRAGMA foreign_keys=ON`
(the `db.py` connect listener) then rejects it.

**Fix — Option A, statement-ordered Core deletes.** `_purge_closed_batches`
now selects the to-purge batch ids, then issues two explicit
`sqlalchemy.delete(...)` Core statements in the same session — rows first,
batch second — instead of relying on UOW flush ordering. `if not ids:
return` keeps the empty case a clean no-op (no stray `IN ()`, no pointless
commit). Signature, retention semantics (last-2, `committed`/`abandoned`,
`closed_at` desc), and both thin wrappers (`purge_closed_link_batches`,
`purge_closed_npc_batches`) are unchanged — one fix repairs both agents.
Adding an ORM `relationship()` or `ON DELETE CASCADE` (schema change) were
both considered and rejected: the ephemeral models are deliberately
relationship-free (`models/ephemeral.py`), and this is code-only plumbing,
not a schema-touching brief.

**New runtime gate, `tooling/verify/checks/purge_fk_ordering.py`** — the
first RUNTIME check in this family (the sibling `npc_batch_purge.py` is
AST-only and structurally cannot see a flush-ordering fault). Fresh
temp-file SQLite DB, real `PRAGMA foreign_keys=ON` in force, exercises the
real `_purge_closed_batches` against BOTH table pairs: 3 closed batches
(ascending `closed_at`) plus 1 open batch, each with row-children.
Confirmed to FAIL with the exact reproduced `IntegrityError` against the
pre-fix helper body and PASS against the fixed one. TICKET-0037's
Machine-checkable section gains this criterion — the gate is now 9/9.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## LOCATION TYPE CLASSIFIED REGISTRY (BRIEF-0039-a, schema v1.84)

First step of TICKET-0039 (spatial creation: door materialization +
`location_type` classification). Ships the storage and the sanctioned
write path only — no reader consumes `classification` yet; it lands later
in the SAME ticket (door derivation, BRIEF-0039-c; type-vocab/E1 checks,
BRIEF-0039-e). A deliberate, ticket-scoped exception to "no structure
without a reader".

**G — classified, extensible registry; NULL = lazy classification;
upsert-one, not full-replace.** `location_type` was a free-text datalist
backed only by a frontend constant (`LOCATION_TYPE_ORDER`), with no
persistence and no interior/exterior notion. `location_type_catalog`
(`id, world_id, name, classification, created_at`, UNIQUE
`(world_id, name COLLATE NOCASE)`) makes `classification`
(`interior` | `exterior` | NULL) the ONLY interior/exterior signal in the
engine: door kind (D1, BRIEF-0039-c) is derived from the two endpoints'
classification, never stored on the door itself, and street-access (E1,
BRIEF-0039-e) reads it. NULL = not yet decided by the creator — inert for
both readers until classified. The table is a per-row upsert catalog
(`writes.upsert_location_type`, 25th sanctioned canon-write site), NOT a
full-replace config table like `world_law`/`npc_prices`: types are added
one at a time from the picker (BRIEF-0039-b), so a delete-then-insert
shape would destroy every other type's classification on every edit.
`upsert_location_type` inserts if the case-insensitive `(world_id, name)`
lookup misses, and on a hit updates `classification` ONLY when the
incoming value is non-NULL — a decided classification is never
downgraded to NULL by a later NULL-classified upsert (e.g. the seed
re-discovering the same free-text type). Curated config, same family as
`location_subculture`/`npc_price`: no `change_history` column.

`migrate_v1_84_location_type_catalog.py` seeds every world with the 7
known defaults (exterior: `city`/`district`/`natural`; interior:
`building`/`room`/`underground`; NULL: `other`) plus every DISTINCT
non-null `location.location_type` value already in use, not covered by
the defaults, seeded NULL and printed so the creator sees what still
needs classifying (RECON against the live DB surfaced one such value,
`settlement`, confirming the dynamic DISTINCT query is load-bearing and
must never be replaced by a hardcoded list beyond the 7 defaults).

**B1 simplification carried forward — exterior-public == exterior for
v1.** The ticket's B1 resolution ("a street is an ordinary exterior
location") collapses the public/private axis into the single
interior/exterior classification for now. Named deferral, same trigger as
stated in the ticket: the day a walled private courtyard must not count
as street access, `location_type_catalog` gains a second classification
axis (or a `classification` value split) rather than reusing
`access_level` (which is a per-location override, not a per-type
default). Scope OUT of BRIEF-0039-e locks this deferral in place.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

---

## DOOR MATERIALIZATION CORE (BRIEF-0039-c, no schema change)

Third step of TICKET-0039. Builds the pure core that turns a location's live
`connects_to` neighbours into `door` rows — no call sites wired in yet (that
is BRIEF-0039-d); exercised here by a standalone script only.

**Placeholder point stays in `placement.py`, the sole placement/distance
authority.** `door_placeholder_point(location)` returns the center of
`(bounds_width, bounds_height)` when both are non-null and finite, else
`(0.0, 0.0)` — H1 verbatim. `door_terminal.py` forbids this math living in
`spatial_doors.py`; keeping it in `placement.py` alongside `distance` and
`derive_positions` means `spatial_author.py` (below) does no coordinate
arithmetic of its own, only dict-building and dispatch.

**`spatial_author.py` — Creation-side orchestrator, delegates every write to
`write_location_doors`.** `materialize_doors(db, *, world_id, location_ids,
changed_by)` is the fifth `connects_to` reader (decision D1 of BRIEF-19
stands — not refactored into a shared helper with `play.py`'s
`_location_neighbours` or `write_location_doors`'s validator). Per location:
gather its live `connects_to` neighbours that are active locations (a
neighbour that is not an active location entity is dropped, never aborts
the commit); read the location's current `door` rows into a
`{target_location_id: (x, y)}` map; build one payload item per neighbour,
reusing the existing point if a door already exists for that target, else
`placement.door_placeholder_point(location)`; call `write_location_doors` —
the SOLE door-write path — with the full payload. The full-replace
naturally drops doors whose edge died and keeps hand-placed coordinates for
every surviving edge. Idempotent: re-running on the same locations
reproduces the same door set. `materialize_doors` never commits — the
caller owns the transaction, matching the region commit's single-commit
contract. Not reachable from `_apply_mutation`: world creation is creator
direct authority, never an AI proposal — this module is inert until
BRIEF-0039-d imports it.

Verified live (script, not committed): two active locations with one
`connects_to` edge produce exactly two door rows (A->B, B->A) at the
placeholder point; hand-placing one door's coordinate and adding a second
neighbour preserves the hand-placed point and places the new door at the
placeholder; deleting the `connects_to` edge and re-running drops the
corresponding door row while leaving the others untouched.

**N1 supersedes H1 (TICKET-0040, BRIEF-0040-d).** The center placeholder
above stacked every door of a room at one point — three neighbours, three
doors, one coordinate — a defect visible in both TICKET-0034's proximity
affordance and TICKET-0032's spawn, both of which read these points. The
replacement is a deterministic arc-length walk of the location's bounds
perimeter, clockwise from the top-left corner `(0, 0)`, seeded by the
asymmetric pair `f"{location.id}:{target_location_id}"` — asymmetric
because the door A->B and the door B->A each live in their OWN location's
local coordinate space, with different bounds and a different origin, so a
symmetric (sorted-pair) seed would be a bug. The signature gained a second
required parameter, `target_location_id` (the single call site,
`spatial_author.py`, passes `neighbour_id`). `(0.0, 0.0)` survives verbatim
as the NULL/non-finite-bounds fallback, now also guarding `<= 0` (a
zero-width location would otherwise yield a degenerate perimeter). The
placement stays in `placement.py` for the same reason H1 did — the sole
placement/distance authority. This is an assumed evolution of a function
delivered by BRIEF-0039-c, not a silent bugfix; no existing `door` row is
re-derived here (`materialize_doors` still reuses `existing_points` for
every surviving edge) — that is BRIEF-0040-e.

**G1 — legacy-center re-derivation (BRIEF-0040-e, no schema change).**
Replacing `door_placeholder_point` (above) was not enough on its own:
`materialize_doors` preserves any existing `(x, y)` for a surviving edge,
so no door materialized before this ticket would ever have moved off the
center just because the function producing NEW points changed. This step
adds `placement.is_legacy_center(location, point)`: true when the location
has usable bounds (non-None, finite, > 0 on both axes) AND `point` equals
`(width / 2.0, height / 2.0)` within `1e-9` on both axes — false in every
other case, including NULL bounds, whose `(0, 0)` doors must never be
disturbed (I1). The comparison lives in `placement.py`, not
`spatial_author.py`, for the same reason the placement math does —
coordinate math has one authority (`door_terminal.py`). `materialize_doors`'s
per-neighbour branch becomes three-way: no existing door -> invent a
placeholder (`summary["placeholders"]`); existing door at the exact legacy
center -> re-derive onto the perimeter (`summary["rederived"]`, new key);
existing door anywhere else -> reuse verbatim (hand-placed, untouched).
The rule is exact-equality only, by design: a door the creator hand-placed
at the exact center is statistically null, and the accepted false positive
is that it moves to a wall — no proximity threshold, no heuristic beyond
equality, no `door.is_placeholder` column (`door` stays terminal, gains no
column) and no one-shot retro-derivation script (re-derivation lives on the
materialization path itself, so a world loaded later can never revert to
stacked doors). Idempotence survives: a re-derived point is a perimeter
point, so `is_legacy_center` is false for it on the next pass and it is
then reused verbatim. Guarded by a new fail-closed check,
`tooling/verify/checks/door_distinct_points.py` (L1): within one active
location carrying non-NULL, positive bounds, no two `door` rows share the
same `(x, y)`; a location with NULL bounds is excluded (its doors are
legitimately all at `(0, 0)`). Live DB check before deployment found 2 of 8
existing door rows sitting at the exact legacy center — the number this
ticket's live gate expects to see move onto the perimeter.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

---

## WIRE MATERIALIZATION AT CONNECTS_TO BIRTH (BRIEF-0039-d, no schema change)

Fourth step of TICKET-0039. `materialize_doors` (BRIEF-0039-c) had no call
site; this step fires it at every point a `connects_to` edge is actually
born, per **J1**: door coverage is a build-time invariant, not something
each edge-creating call site has to remember.

**J1 — `connect_locations(db, *, world_id, entity_a_id, entity_b_id,
changed_by)` (`spatial_author.py`) is the thin wrapper: write the edge, then
materialize both endpoints.** It calls `write_relation(mode="set", ...,
type="connects_to", value=50, direction="mutual")` — the exact args the
region-commit connection branch already used — then
`materialize_doors(db, world_id=world_id, location_ids=[entity_a_id,
entity_b_id], changed_by=changed_by)`. Returns the merged
`materialize_doors` summary; never commits (caller owns the transaction).
Two call sites now route through it or its bulk equivalent:

- **Region commit** (`routes/regions.py::commit_region`) takes the bulk
  path (preferred over routing `_commit_region_links` through
  `connect_locations` edge-by-edge): `_commit_region_links` is unchanged,
  still writing edges via `write_relation` directly; after it returns,
  `commit_region` collects every location id touched by a `connects_to`
  entry in `written_links` (`_touched_location_ids`, a named extraction to
  hold `commit_region` under the R1 80-line cap) and calls
  `materialize_doors` ONCE with that set, before the single `db.commit()`.
  A region with many adjacency edges materializes each node's doors exactly
  once, not once per incident edge. `controls` links are excluded —
  materialization is connects_to only.
- **Manual adjacency** (`POST /entities/{id}/relations`,
  `crud/relations.py::create_relation` — the route the location graph editor
  posts to) branches on `body.type == "connects_to"`: that branch calls
  `connect_locations` (fixed value=50/direction=mutual, mirroring the
  region-commit args — `intensity`/`direction`/`visible_to_b`/`notes` from
  the request body are not applicable to a topology edge) and re-reads the
  written row via `_find_relation_pair` for the response shape; every other
  relation type is untouched, still going through `write_relation` mode=set
  as before.

**Rejected J2 — embedding materialization inside `write_relation` itself.**
Would blur `write_relation` back into a mixed writer (it currently writes
one canon type, cleanly) and fire on every relation type, not just
`connects_to`; `connect_locations` at the call site is the narrower change.

Both call sites thread the existing creator identity (`"creator"`) into
`changed_by` — no new identity invented. No second `db.commit()` was added
on either path. `single_canon_write.py` stays green: doors still only
reach the table via `write_location_doors`, itself only reached through
`materialize_doors`.

Two other `write_relation` call sites were checked and excluded as
`connects_to` birth points: `link_author.py`'s coherence-patch path
(`_apply_canon_relation_patch`) edits an existing row by `relation_id` and
never varies its type into `connects_to` (`_LINK_RELATION_TYPES`
structurally excludes it); `cockpit/mutations.py`'s `relation_change` apply
(`mode="delta"`, AI-proposed, creator-review-gated) is a different
write semantic entirely (accumulating delta on a possibly-new pair) and is
not a `connects_to` edge author in practice — CLAUDE.md's "connects_to is
never a social signal" invariant keeps AI relation proposals off it. Neither
is rewired here; both are out of scope without a deliberate decision.

Not addressed here (deferred to BRIEF-0039-e per that brief's scope): no
verify check yet enforces every `connects_to` edge has materialized doors;
no delete-time sweep for a location's doors on hard delete (a surviving
neighbour's dangling door is dropped on its own next materialize, not
swept eagerly).

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

---

## INVARIANTS: DOOR COVERAGE, TYPE VOCAB, STREET NOTE (BRIEF-0039-e, no schema change)

Fifth and final step of TICKET-0039. With materialization wired
(BRIEF-0039-d), door coverage becomes a build-time invariant — this step
adds the two G1 gates that guard it, plus the E1 building-shell
street-access soft note.

**D1 — `location_classification` is the ONLY interior/exterior reader,
door kind stays derived, never stored.** `spatial_author.location_classification
(db, *, world_id, location_id) -> Optional[str]` reads a location's
`location_type`, case-insensitively against `location_type_catalog` (same
lookup `writes.upsert_location_type` uses). NULL `location_type`, an
uncatalogued type, or a catalogued-but-still-NULL classification all
resolve to `None` — inert for both this note and any future door-kind
reader. No `door.type`/`door.kind` column was added; door kind (interior-
interior / boundary / exterior-exterior) stays derived on demand from the
two endpoints' classification wherever a reader needs it.

**E1 — building-shell street-access is a SOFT note, never a gate.** A
BUILDING SHELL is defined as: `location_classification == "interior"` AND
(its parent's classification is `"exterior"` OR it has no parent — an
interior root). `commit_region` (`routes/regions.py`) checks, for every
location committed THAT transaction, whether a building shell has at least
one live `connects_to` neighbour classified `"exterior"` (exterior-public
== exterior for v1 — the same named deferral BRIEF-0039-a recorded: the
day a walled PRIVATE courtyard must not satisfy this, add an exterior
sub-classification and refine the neighbour test; trigger = first private-
exterior location that wrongly clears the note). No neighbour qualifies ->
one note, verbatim `f"Batiment '{name}' sans acces exterieur-public -
aucune porte ne donne sur un lieu exterieur."`, appended to the response's
`notes` list (same channel `region_author` uses) — advisory only, never
rejects, never mutates, no stored exception flag. "Most buildings on a
street" is deliberately not "all": a hidden cabin or an interior courtyard
is legitimate. The neighbour scan re-implements the two-query
`connects_to` read locally in `regions.py` rather than importing
`spatial_author._live_neighbour_ids` — decision D1 of BRIEF-19 stands, not
refactored into a shared helper.

**Two new fail-closed G1 gates, both DB-backed against a self-contained
fresh temp-file SQLite fixture** (WORLD_ENGINE_DATABASE_URL set before any
`world_engine` import — same idiom as `spatial_door_travel.py` /
`scene_join_target.py`, so neither check ever touches Nia's real DB), on
the `door_terminal.py`/`single_canon_write.py` FAILURES-list idiom (zero
parsed criteria is never a vacuous pass):

- **`door_coverage.py`** — for every active `connects_to` relation whose
  both endpoints are active locations, both directed `door` rows must
  exist. Exercises the REAL production writers (`connect_locations` /
  `materialize_doors`) to build the positive fixture; an edge touching an
  archived location is excluded (same active-locations filter as
  `crud/locations.py:get_locations_graph`). Verified live: deleting one
  direction surfaces it by name; re-running `materialize_doors` heals it;
  an empty world reaches an explicit "no edges to verify" pass, reachable
  only because the scan query concretely ran (an exception during the scan
  crashes the check non-zero, never masquerading as a pass).
- **`location_type_classified.py`** — every DISTINCT `location_type` on an
  active location must exist in `location_type_catalog` (case-insensitive)
  with a non-NULL classification in `{"interior", "exterior"}`. An
  archived location's uncatalogued type never surfaces. Vacuous-proof:
  when active locations carry a `location_type`, the examined-type count
  must be `> 0`. Verified live: an uncatalogued type and a catalogued-but-
  NULL type both FAIL by name; classifying them heals the gate; an
  out-of-vocab classification value landing via a path other than
  `upsert_location_type` (which validates) also FAILs by name.

Neither check depends on `connects_to` being created only via
`connect_locations` — both assert the RESULTING state, so either would
also catch an edge that somehow bypassed materialization.

`single_canon_write.py` and `door_terminal.py` stay green: this brief adds
readers and checks, no new canon-write path.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

---

## LOCATION TYPE SIZE TEMPLATES (BRIEF-0040-a, schema v1.85)

First step of TICKET-0040 (location type size templates + perimeter door
placement — first of three tickets toward contextual room-batch
generation). Ships storage, the write path, and the `room` seed only; the
template is applied to NOTHING yet (BRIEF-0040-b).

**A1 — the model produces no number.** Sizes come from the code, never a
generation prompt. `location_type_catalog` gains two nullable REAL columns,
`default_width`/`default_height`, in the same local coordinate space as
`obstacle_vertex` (1.0 = one world-meter, never `coord_x`/`coord_y`).

**B1 — templates live on the per-world catalog, not Python constants.**
`location_type_catalog` is already per-world and upsert-per-row, hence
reusable across worlds without a code change per world. A type with no
template -> bounds stay NULL -> no spatial mode for a location of that
type — fail-closed, no invented number. `upsert_location_type` gains
keyword-only `default_width`/`default_height`, posture identical to
`classification`: on an existing row, assigned ONLY when the incoming
value is non-NULL — a decided template is never overwritten with NULL.
Validated before any lookup: both-or-neither (`ValueError`), and each
value finite and `> 0` (`ValueError`) — the same 422 idiom
`set_location_geometry` already uses, no new SQL CHECK constraint.

**K2 — `room`-only seed, 6.0 x 5.0 world-meters, never overwriting a
decided value.** `migrate_v1_85_location_type_templates.py` finds the
`room` row case-insensitively per world (same fold as
`upsert_location_type`); if it exists with both columns NULL, sets the
seed values; if it does not exist, creates it via `upsert_location_type`
with `classification="interior"` (matching `migrate_v1_84`'s defaults) and
the seed values. No other type is seeded — `city`, `district`, `natural`,
`building`, `underground`, `other` keep NULL templates, since inventing a
width for `city` would defeat B1's fail-closed posture. This is the one
value TICKET-0042's room-batch generator needs to be unblocked.

**B4 — DEFERRED, named.** Template override by the median of `>= 3`
sibling locations under the same parent, once worlds are populated enough
for a median to mean something. Not implemented this brief; no code path
computes or stores a median. Trigger: a world with enough sibling rooms
under one parent that a per-type flat default starts looking wrong.

Curated config, same family as `location_subculture`/`npc_price`: no
`change_history` column — `location_type_catalog` carries none today and
this brief does not add one. `upsert_location_type` stays the only writer
of the table; the migration calls it to create the `room` row rather than
issuing a raw INSERT.

**E1/J1 (BRIEF-0040-b, no schema change) — the template gets one reader and
one application site.** `spatial_author._catalog_row` is now the single
catalog read accessor (J1): a case-insensitive, world-scoped
`location_type_catalog` lookup, extracted verbatim from
`location_classification`'s old inline scan — `location_classification`
keeps its signature, return type and docstring contract byte-identical, and
is now its first caller. `spatial_author.location_type_template` is the
second caller: fail-closed (B1) — no type, no catalog row, either bound
NULL, non-finite, or `<= 0` all resolve to `None`, never an exception, never
an invented number.

`cockpit/crud/entities.py::_stamp_type_template` (E1) is the template's only
application site, called from `_create_entity_core` immediately after the
extension row is constructed, in-memory, before `db.add`. It writes
`bounds_width`/`bounds_height` only when the template resolves AND both
columns are still NULL on the row — true for every row in this function,
since the row was just constructed, but written as an explicit guard rather
than assumed. Deliberately NOT placed in `_build_extension_kwargs`: that
function is shared with the `PUT /entities/{id}` update path, and stamping
there would re-apply the template on every edit — including a
`location_type` change on an already-born location — silently overwriting
creator-set geometry and breaking F1 (a template change is never
retroactive). `routes/regions.py` and `routes/npc_agent.py` both construct
their location rows via `_create_entity_core`; no second birth path exists,
so one call site covers region commit and NPC-agent-driven creation too.
The create response's under-reporting of the stamped bounds (BRIEF-0040-c's
job) is left visibly broken rather than half-fixed here.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

---

## BOUNDS PRESERVATION AND TEMPLATE AUTHORING IN THE TYPE PICKER (BRIEF-0040-c, no schema change)

Closes the two silent-erasure paths BRIEF-0040-b's birth-bounds stamping
exposed, and gives the creator surface to author a template for a type
other than `room`.

**Truthful create response.** `create_entity`
(`cockpit/crud/entities.py`) no longer hardcodes
`{"bounds_width": None, "bounds_height": None, "obstacles": []}` in its
`elif entity.type == "location":` branch — it calls the same
`_location_geometry_dict` accessor `set_location_geometry` already uses.
Before this, a templated room's sheet opened with an EMPTY geometry editor
immediately after creation; the next save posted `null` for both bounds
and silently wiped the stamped template — the exact under-reporting
BRIEF-0040-a named and deliberately left broken.

**F1 — absent means preserve, explicit null clears.**
`set_location_geometry` distinguishes a bounds key OMITTED from the
request body from one sent as explicit `null`, via Pydantic v2's
`body.model_fields_set`: an omitted key leaves the stored
`bounds_width`/`bounds_height` untouched; an explicit `null` clears it
(the emptied-field-then-save case from the geometry editor); a number
still validates `> 0` before assignment. Same posture as
`writes.upsert_location_type`'s never-overwrite-a-decided-value-with-NULL
rule — now the second place in the codebase with this asymmetry. The
`obstacle` full-replace under it is unchanged: `write_location_obstacles`
still receives and replaces the submitted set wholesale — this brief
touches only the two bounds columns, no other route.

**Template authoring is lazy-on-use plus one on-demand button, never a
bulk screen.** The classification prompt (BRIEF-0039-b) gains two
optional numeric inputs, pre-filled from the catalog row when a template
already exists, posted to `POST /api/location-types` alongside
`classification`. The modal's trigger condition is UNCHANGED — uncatalogued
type or `classification == null` — a missing template alone never fires
it. The new `Gabarit...` button beside the `location_type` field opens the
SAME modal, unconditionally, for whatever string the field currently
holds: the only way to size an already-classified type (`building`,
`city`, ...) without a bulk admin screen, matching BRIEF-0039-b's Scope
OUT doctrine. Client-side guard (exactly one of the two fields filled) is
a UX nicety only — `upsert_location_type`'s both-or-neither `ValueError`
stays the actual authority.

**A template change is never retroactive.** Nothing in this brief writes
a bounds value onto an existing location the creator did not explicitly
submit through `PUT /entities/{id}/geometry`; the `Gabarit...` button
touches only `location_type_catalog`, never a `location` row, and no
"re-apply template" action exists anywhere in the UI.

`json_ui_boundary.py`, `page_contract.py`, `module_budget.py`, and
`function_length.py` stay green: no new route, no new JSON-blob field, and
`crud/entities.py` grows under 15 lines.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## SHARED REVIEW-TREE COMPONENT — EXTRACTION (BRIEF-0041-a, BRIEF-0041-b, BRIEF-0041-c, no schema change)

Nine `region*` review functions (cascade, accept/reject, notes, node, tree,
graph toggle, graph data, graph render) are replaced by a generic `review*`
component (`index.html`) driven by an explicit descriptor, with the region
tree and the pre-commit location graph cut over to it. Zero behaviour
change: region review renders, cascades, toggles and commits identically to
`main` — asserted by static gates plus a scripted live sequence run once
end to end, not by a JS runtime the codebase does not have.

**Structural justification, not aesthetics.** `regionCascade` computed the
region root inside its own body and hard-wired it as the fallback parent of
every orphaned node. TICKET-0042's batch generator must re-attach orphans to
a creator-chosen anchor instead — the two consumers differ by the VALUE of
one parameter (`fallbackParentId`), not by behaviour. Duplicating the
cascade would have shipped two copies identical up to a constant, and two
places to fix the next reparenting bug (S-norme; C2, refactor over
exemption).

**E1 — a registry, not a closure.** Inline `onclick` handlers are string
literals evaluated in global scope; they cannot carry a JS closure over a
descriptor object. The component therefore keeps `REVIEW_DESCRIPTORS`, a
plain object keyed by a registry key (`reviewRegister(key, descriptor)`),
and every DOM-reachable entry point (`reviewToggleAccept`, `reviewOpenSheet`,
`reviewToggleGraph`, …) takes that key as its first argument and re-resolves
the descriptor via `reviewDescriptor(key)`. `reviewCascade` and `reviewNotes`
are the two exceptions: they are pure functions of their arguments and never
touch the registry.

**B1 — the anti-vacuity teeth are purity plus a parameterised fallback, not
a caller count.** A caller-count criterion cannot be green at THIS ticket's
close: the component's second consumer is TICKET-0042, not yet written, so
four of the nine generics would show exactly one caller here regardless of
how correctly the extraction was done. A fail-closed gate that cannot
structurally be green is a broken gate. The teeth that replace it, both
enforced by `tooling/verify/checks/review_component.py`: (a) no `review*`
function body may contain the token `region` or `REGION_`, in any
context — a rename without real mutualisation leaves a global read in the
body and fails here; (b) `reviewCascade` takes exactly one parameter and its
body references `fallbackParentId` while touching no DOM and no registry — a
rename that keeps the root hard-wired recomputed inside the function fails
here.

**Rejected: the `_git_show` byte-identical footprint criterion.** Precedent
(`relation_graph.py`'s Lieux-graph-vs-`main` diff) compares the current tree
to `main`. That criterion goes vacuous the moment this ticket merges — `main`
then instantly equals the new code, and the check would silently stop
proving anything. Replaced by a permanent BIDIRECTIONAL boundary, named-
allow-list style (`json_ui_boundary.py` precedent): outside the component,
only `regionRenderAll`, `regionReviewDescriptor`, `regionRenderFactionsPanel`
and `_sheetEntityOptions` may reference a `review*` symbol — checked by
walking every top-level function in `index.html` and testing its
brace-balanced body against the exact twelve `review*` identifiers, not
against the bare substring `review`. The substring alone false-positives on
unrelated, pre-existing English prose already on `main` (`doApprove`'s
"reviewed but not applied" comment, the `/api/mutations/batch-review`
endpoint literal in `doBatchAction`, `npcAgentLoadBatch`'s "review selects"
comment, `renderCard`'s "reviewed rows" comment) — none of those four
functions calls a `review*` symbol, so a raw-substring gate would have been
permanently red for reasons unconnected to this boundary. The
identifier-boundary match proves the same "blast radius is exactly the four
sanctioned consumers" claim without that false-positive surface, confirmed
against the live file before the check was committed.

**C1 — why `index.html` stays one file.** Splitting it out of a single page
is a documented convention (`CLAUDE.md`, "single-page HTMX/vanilla-JS
cockpit/index.html, no build step"), and `module_budget.py` scans
`src/**/*.py` only — `index.html` is structurally exempt from the
1000-line cap by construction, not by oversight. Splitting it needs a
serving decision (today only `/vendor/{filename}` is a whitelisted static
route, and it explicitly rejects non-vendored assets), an evaluation-order
decision (`const NODE_R` is declared after the region/review block and does
not hoist — a `<script src>` split could load the component before `NODE_R`
exists, a TDZ error silent until the graph is opened), and a `CLAUDE.md`
doctrine amendment. None of that is this ticket's work.

**Named deferral — `index.html` file split (D3).** Trigger: the next ticket
that needs a JS unit test or a golden-render snapshot test, since neither
can exist without a loadable module. Blocked on: the serving-route decision,
the `const NODE_R` evaluation-order decision, and the `CLAUDE.md` doctrine
amendment above.

`review_component.py` is `index.html`'s fifth structural gate alongside
`page_contract.py`, `relation_graph.py`, `event_tab.py` and `schema_0024.py`;
none of the other four regressed on this ticket's CSS renames.
`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

---

## ROOM BATCH MANIFEST — TYPE AUTHORITY (BRIEF-0042-a, no schema change)

First step of TICKET-0042 (room batch generator). Ships
`room_batch_author.generate_room_batch_manifest` — a Phase A manifest call
mirroring `region_author`'s two-phase shape (parse -> normalize ->
`{ok, manifest, notes, skipped}`), scoped to one creator-chosen anchor
location. Writes no canon; the manifest is ephemeral until the atomic
commit route (BRIEF-0042-e).

**P1 — the manifest is the sole `location_type` authority; the batch never
routes through `entity_author._validate_location_type`.** Every other
authoring path (`entity_author._entity_location_draft`) validates a
proposed type against the frozen `_LOCATION_TYPES` enum and repli-falls an
unrecognized value to `"other"`, silently discarding it. That is wrong for
a batch: the real vocabulary with classification AND size template is
`location_type_catalog` (TICKET-0039/0040), and a repli-fall to `"other"`
would lose the template on the very generator whose rooms most need one. So
`_normalize_batch_types` looks the proposed string up via
`spatial_author._catalog_row` (the single catalog read path, J1,
TICKET-0040) and, on a miss, **keeps the string verbatim** and appends a
note (`"Type '{t}' absent du catalogue -- ce lieu naîtra sans bounds tant
que le type n'est pas classifié"`) instead of substituting anything. The
creator resolves it in Phase A editing via the existing classification
affordance (P-a, BRIEF-0042-d). A type present in the catalog but with a
NULL size template is left as-is — that room legitimately borns without
bounds, consistent with T1 (an anchor/room with NULL bounds never blocks
the batch).

**K1 spanning tree — cycle detection is new, not mirrored.** The manifest's
`parent_room` per room is model-proposed, code-guaranteed: resolved
case-insensitively against (surviving manifest rooms | the anchor name),
with any unresolved name, self-parent, or a cycle (a room reachable from
itself through a chain of `parent_room` pointers) forced to attach
directly to the anchor, noted. `region_author._normalize_location_parents`
is the SHAPE precedent (parse -> normalize -> notes) but does not itself
detect true cycles among non-root entries (a region's flat two-tier
manifest has no depth to cycle through); `room_batch_author._detect_cycle`
walks the resolved-parent chain against a frozen first-pass resolution
(`_resolve_parent_keys`), so a forced-attach mutation made for one room
never corrupts the chain walk for another room evaluated later in the same
pass.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## ROOM BATCH FICHE GENERATION — P1 OVERRIDE + RETRY-ONCE (BRIEF-0042-b, no schema change)

Second step of TICKET-0042. Ships `room_batch_author.generate_room_batch_draft`
— Phase B, one full location fiche per manifest room, mirroring
`region_author.generate_region_draft`'s per-entity loop shape
(`_draft_locations`) and its `skipped`-on-failure precedent. Writes no canon;
every fiche stays ephemeral until the atomic commit route (BRIEF-0042-e).

**P1 enforced in this module, not in `entity_author`.** Each room's content
call is the unmodified `entity_author.generate_entity_draft("location", brief,
db)` — same call, same `_validate_location_type` repli-fall-to-`"other"`
internally. `generate_room_batch_draft` overwrites the returned
`draft["public"]["location_type"]` with the manifest room's verbatim type
*after* the call returns, noting any divergence for transparency. This keeps
the enum gate (`_validate_location_type`, `_LOCATION_TYPES`) untouched and
shared by every other authoring path, while the batch's own type authority
(BRIEF-0042-a's P1) never round-trips through it.

**R — retry-once-then-skip, new at this step.** `_draft_room_with_retry`
calls the same content generation exactly twice on a first failure (parse
error, empty draft, or a defensive exception backstop — `generate_entity_draft`
itself never raises); a second failure drops the room into `skipped` with
`{local_id, name, reason}` and the loop continues. No exponential backoff, no
per-room retry budget beyond one.

**A skipped internal node's children are NOT reparented in Phase B.** They
keep their original `parent_room` pointing at the now-absent room name. This
is deliberate (ticket decision R): reparenting orphans to the anchor is
already the review cascade's job (`fallbackParentId`, TICKET-0041's generic
component, wired in BRIEF-0042-d) — Phase B introduces no second reparenting
mechanism.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

## ROOM BATCH COHERENCE — D3 RELOCATED POST-PHASE-B (BRIEF-0042-c, no schema change)

Third step of TICKET-0042. Ships `room_batch_author.propose_batch_coherence`
— Phase C, one model call over the FULL generated batch (all Phase B fiches)
proposing supplementary undirected edges (`{a, b, reason}`, room/sibling
names) plus advisory incoherence notes. Writes no canon; every edge stays
`{id, a_id, b_id, a_local, b_local, reason}` — ephemeral until the atomic
commit route (BRIEF-0042-e).

**D3 relocated to run AFTER Phase B, not blind at the manifest stage.** At
intake (2026-07-23) this pass was moved past fiche generation: a
supplementary edge motivated by real generated content (a room's actual
description, not just its one-line manifest pitch) is a materially better
proposal than one guessed from the manifest alone, at the cost of being the
heaviest token call in the ticket (it is the only call that sees every
fiche). Measured once at the ticket's own MAX_COUNT (25 rooms, synthetic
fiches with realistic-length descriptions): ~3500 characters (~875 tokens on
a chars/4 heuristic) for the full user message — comfortably inside any of
the project's local 8b models' context window, so the Scope-OUT compaction
fallback (name + one-line only, dropping descriptions) is NOT triggered at
this step. If a future template revision or richer fiches push this over
budget, that compaction is where to reach first — not a new mechanism.

**L1 enforced by `_resolve_coherence_edges`, never the model.** Every
proposed edge is resolved by name against a `fold(name) -> (id, is_local)`
index built from real data only: Phase B's surviving fiches (`local_id`,
`is_local=True`), the anchor, and canon siblings queried fresh from
`location.parent_location_id == anchor_id` (`is_local=False` for both — both
are already-real entity ids, unlike a batch `local_id` which BRIEF-0042-e
must still resolve through its own commit-time id map). A name that resolves
to neither, resolves both sides to the same node, or duplicates a K1
spanning-tree pair (BRIEF-0042-a) is dropped into `unresolved` with a
reason — a name naming a manifest room that Phase B itself skipped gets a
more specific reason than a truly unknown name, using `manifest` (the
function's third input) purely for that distinction; it plays no role in
resolution itself. No name ever creates a room.

**Named deferral, on the record: no O(N^2) pairwise semantic re-check.**
This pass proposes edges and advisory notes only — it never rewrites a
fiche's description, renames a room, or changes a type, and it never
compares every fiche against every other fiche. A full semantic coherence
sweep across the batch is a real, larger feature Nia may want later; it is
NOT built here.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

---

## ROOM BATCH REVIEW — SECOND CONSUMER OF THE SHARED COMPONENT (BRIEF-0042-d, no schema change)

Fourth step of TICKET-0042. Ships the Lieux-browse entry point ("Générer un
lot ici"), the Phase A manifest editor (type-picker reuse, add/remove rows,
parent_room select), the Phase B/C trigger buttons, and `batchReviewDescriptor`
+ `batchRenderAll` — the room batch generator's wiring into the TICKET-0041
shared review component. Writes no canon; the atomic commit route
(BRIEF-0042-e) is called by the panel's "Commiter le lot" button but does not
yet exist as of this step.

**The predicted second consumer arrives.** TICKET-0041's closure entry
(`SHARED REVIEW-TREE COMPONENT — EXTRACTION`) named its `CONSUMER_ALLOW_LIST`
teeth as necessarily four-entry-only at that ticket's close ("the component's
second consumer is TICKET-0042, not yet written") and predicted this exact
extension. `review_component.py`'s `CONSUMER_ALLOW_LIST` grows from four to
six: `batchRenderAll` (mirrors `regionRenderAll` — the registration + render
site, calling `reviewRegister`/`reviewCascade`/`reviewTree`/`reviewToggleGraph`/
`reviewGraphRender`) and `batchReviewDescriptor` (mirrors `regionReviewDescriptor`
— the descriptor factory, whose `onToggleAccept` closure calls `reviewIsAccepted`).
No other function was added to the list; `batchRenderEdgesPanel`, `_batchNodeName`,
`batchOpenSheet`, `batchCommit` and the Phase A/B/C trigger functions reference
no `review*` symbol, so none needed allow-listing — confirmed by
`review_component.py` rule 6 passing unchanged (whole-identifier boundary,
zero new false positives).

**Q1 (the synthetic anchor) needed no component change.** The anchor enters
`batchReviewDescriptor`'s `nodes` array as an ordinary, always-accepted,
`parentId: null` root; `onToggleAccept` no-ops for its id. `reviewNode` still
renders an Accepter/Rejeter button for it (the shared component was
deliberately left untouched, per BRIEF-0042-d Scope OUT) — the button is
visually present but inert, confirmed live (`reviewToggleAccept('batch',
batchAnchorId)` leaves `batchAccepted` unchanged). O1's "visually distinct
non-editable root" therefore falls out entirely from descriptor data
(`subtitle: '(ancre)'`), exactly as TICKET-0041 predicted.

**Batch state lives in a second container, not a new tab.** `CREATION_TABS.lieux`
gained a second `containers` entry (`batch-panel-wrap`) — the existing
multi-container array shape, previously exercised by no other entry — so the
generic show/hide loop in `showCreationSubTab` hides the batch panel on any
tab switch with zero new tab-id literals. The panel's own open/closed state
(`#batch-panel`, nested one level deeper) is independent of that loop,
reset by `batchReset()` from both `_lieuxTabEnterReset` and `_lieuxWorldReset`.

**Confirmed live** (manual browser session against a real anchor + Ollama):
Phase A manifest generation and edit, Phase B fiche generation, Phase C
coherence (one supplementary edge to a canon sibling, one unresolved
skeleton-duplicate), reject-cascade reparenting with the badge, edge
confirm/discard, and graph rendering (solid spanning-tree lines, dashed
confirmed supplementary edges) — zero console errors throughout.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

---

## ROOM BATCH ATOMIC COMMIT (BRIEF-0042-e, no schema change)

Fifth and final step of TICKET-0042. Ships `cockpit/routes/room_batch.py::
commit_room_batch` — the SOLE canon-write path for a batch, posture
identical to `commit_region`: rooms commit via `_create_entity_core`
(template bounds from the manifest type, P1) in parent-before-child
dependency order; every `connects_to` edge (the K1 spanning tree,
unconditional, plus confirmed supplementary edges from Phase C) commits via
`spatial_author.connect_locations` so doors materialize on the perimeter
(N1); the whole batch commits in ONE transaction, full rollback on any
exception. Also ships `tooling/verify/checks/room_batch_report_only.py`,
the ticket's own machine-checkable acceptance criterion (a fail-closed token
scan proving `room_batch_author.py` carries none of `_apply_mutation`,
`write_relation`, `_create_entity_core`, `db.commit(`).

**Door materialization: `connect_locations` PER edge, not a single
end-of-commit sweep (drafting decision, flagged in the brief).** Region's
`commit_region` collects every touched location id into a set and calls
`materialize_doors` ONCE before its single commit — more efficient when many
edges share endpoints. This route instead calls `connect_locations` once per
confirmed/tree edge, so a room touched by k edges is re-swept k times.
`materialize_doors` is idempotent and full-replace per location, so the
redundancy is a performance cost, not a correctness one — chosen here for
single-point-of-edge-birth clarity (every edge's write and door
materialization happen at the exact same call site, easier to read than a
two-phase collect-then-sweep). **Trigger to switch to the region pattern:**
if the redundant re-sweeps show up as a measurable latency cost at
`MAX_COUNT` (25 rooms, up to 24 tree edges plus any supplementary edges) —
measure before switching, don't assume.

**No canon-write-policy allow-list entry needed.** `commit_room_batch`
makes zero direct `.add()`/`.delete()`/`.exec()` session calls — every write
delegates to `_crud._create_entity_core` and `connect_locations` (->
`write_relation` + `write_location_doors`), both already sanctioned sites in
`canon_write_policy.txt`. `single_canon_write.py`'s function-grain
attribution (not call-graph-grain) means a route that fully delegates, like
`commit_region` before it, needs no entry of its own — confirmed by running
the check after this route landed: unchanged PASS, zero new lines in the
policy file.

**Server-authoritative cascade re-derivation reuses `room_batch_author.
_name_key` directly, not a second copy.** Unlike `region_author.py` and
`room_batch_author.py`, which each keep their OWN separate `_name_key`
(no shared-module abstraction — a deliberate precedent, not an oversight),
this route imports `room_batch_author._name_key` directly: the SAME
case-insensitive, whitespace-normalized key must resolve a `parent_room`
name identically at generation time (BRIEF-0042-a's K1 tree, BRIEF-0042-c's
coherence index) and at commit time, or a room could silently resolve to a
different parent than the one the creator reviewed. A second, subtly
different copy is the one thing that must not happen here.

**Confirmed live** (manual browser session, three scenarios): (1) a
5-room batch with one room rejected mid-tree — the rejected room is absent,
its child's `parent_location_id` re-resolved to the anchor server-side
(never the rejected room), template bounds and perimeter doors materialized
on both sides of every tree edge; (2) a batch under a NULL-bounds,
NULL-classification anchor (`location_type` absent from the catalog) —
commit succeeds, the anchor-side doors land at `(0, 0)`, and the T1 note is
returned; (3) a corrupted room (empty `name`, forcing `_create_entity_core`'s
422) mid-batch — the whole commit rolls back, location count under the
anchor unchanged (zero partial writes), `{"ok": false, "error": ...}`
returned. Zero console errors throughout.

**Named deferral, on the record: a Phase B fiche's `subculture`/
`sensed_links` are not wired to canon.** Region's commit writes
`pub.subculture` (plus `sec.subculture_hidden` folded in as `"hidden"`) onto
the new location; this route's `_commit_batch_rooms` sets only
`location_type`, `access_level`, `description` and `parent_location_id` —
Scope IN never named subculture wiring, and the ticket's supplementary-edge
mechanism (Phase C) already supersedes fiches' own `sensed_links` as the
room batch's edge-proposal path. A batch room therefore commits with
whatever `subculture` its fiche proposed silently discarded. Trigger to
revisit: if Nia wants a generated room's ambient/hidden subculture rows to
survive the batch commit, wire `pub.get("subculture")` (and
`sec.get("subculture_hidden")`) through the same `ext_data` dict
`_commit_batch_rooms` already builds — the region precedent is a direct
copy-paste away.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

---

## CANON.PY STRATUM SUB-SPLIT — FACTION DOMAIN EXTRACTION (BRIEF-0048-a, no schema change)

Resume-blocking decision surfaced during BRIEF-0044-b execution: adding
`EntityType`/`EntityTypeHistory` to `canon.py` would have pushed it from
985 to 1064 lines, tripping `module_budget.py`'s 1000-line cap for the
first time (PASS -> FAIL). Per doctrine C2 (refactor over exemption) and
`module_budget.py`'s own docstring — its baseline is a transition artifact
retired at TICKET-0028's close, entries "may only shrink or disappear,"
never grow for new work — the resolution is a split, not a fresh baseline
entry. This is the first sub-split of a canon-stratum file by domain, one
fractal level below the TICKET-0028 canon/ephemeral/pipeline split.

**A1 — extract the faction domain.** `Faction`, `FactionRole`,
`FactionMembership` move verbatim into a new `models/canon_faction.py` —
the largest clean single-domain block in `canon.py` (395-515, 121 lines).
Post-split `canon.py` is 864 lines, leaving ~136 lines of headroom before
BRIEF-0044-b's own EntityType/EntityTypeHistory addition (which stays in
the slimmed `canon.py`, decision C1 below) brings it to ~943.

**B1 — shared helpers stay in `canon.py`, no `models/_base.py` yet.**
`canon_faction.py` imports `_uuid`/`_created_ts` from `.canon` rather than
duplicating them or extracting a shared base module. Trigger to revisit:
extract `models/_base.py` only when a SECOND domain extraction also needs
these helpers — one consumer doesn't justify the abstraction.

**C1 — no registry/catalog stratum.** `EntityType`/`EntityTypeHistory`
(BRIEF-0044-b) stay in the slimmed `canon.py`, unchanged from that brief's
original placement; this ticket does not introduce a registry stratum
(`C2` deferred, same trigger discipline as B1 — a second registry-shaped
table would be the signal to revisit).

**D — module name `models/canon_faction.py`,** following the existing
`canon.py` naming, scoped to the extracted domain rather than a generic
`canon2.py`.

**Move-only, zero blast radius beyond the package boundary.** RECON (live
`main`, canon.py at 985) confirmed all 93 external import sites resolve
through `from .models import X` — zero direct `models.canon` imports — so
only `models/__init__.py`'s internal import block changes; `__all__` stays
byte-for-byte identical, same names and order. Structural gates
(`single_canon_write.py`, `world_tick.py`) walk the package directory, not
a fixed file list, so the new module is covered automatically; no
verify-check needed a path-coupling edit (`npc_goal_read.py`'s
`canon.py`-only allow-list concerns an unrelated cluster, and
`prompt_version.py` deliberately excludes `canon.py` either way).
Zero test-file edits — the existing suite is the move-only correctness
signal.

`DECISIONS_INDEX.md` is regenerated from this entry via
`gen_decisions_index.py`.

---

## SCHEMA VERSION — two-plane governance (C2), plane 1: stored static version + fail-closed boot guard (BRIEF-0044-a, schema v1.86)

TICKET-0044 introduces a third structural-write authority: the runtime-DDL
constructor (BRIEF-0044-c) creates `ext_*` tables at runtime, outside
migration. Once tables can be born that way, the schema version doc string
stops describing the base — nothing detected DB-vs-code drift. This step
ships plane 1 of the locked design: a STATIC-plane version, stored and
checked at boot. Plane 2 (per-world runtime-type manifest / reconciliation)
is a separate, later concern (BRIEF-0044-b/d) — the two planes answer
different questions and never share a write path.

**Stored, not doc-only.** `schema_meta` is a new singleton table
(`CHECK (id = 1)`) holding `static_version`. It lives in `models/pipeline.py`
(infra stratum, alongside `User`) — never `canon.py`, never
`canon_write_policy.txt [CANON_TABLES]`: it is engine infra, not
world-domain canon, and the constructor is structurally forbidden any write
path to it. The ONLY writer is a migration script (this ticket's
`migrate_v1_86_schema_meta.py`) plus `scripts/init_db.py`'s virgin-head
seed — the same "migration backfill AND seed virgin-head both" idiom
`writes/prompts.py` already documents for `prompt_version`.

**Code-side constant, checked at boot, fail-closed.** New module
`schema_version.py` exposes `EXPECTED_STATIC_SCHEMA_VERSION`. The cockpit's
existing startup hook (`cockpit/app.py`, previously only the link/NPC batch
purge) gained a second `@app.on_event("startup")` handler, registered
FIRST, that reads the `schema_meta` singleton and raises `RuntimeError`
before the app serves a single route when: the table is absent, the row is
absent, or `static_version != EXPECTED_STATIC_SCHEMA_VERSION`. On agreement
it starts silently — no log noise on the success path. A migration bumps
the constant, the `schema_meta` row, and the `world-engine-schema.md`
header line together, in the same commit — never one without the others;
`verify/checks/schema_version_agreement.py` is the static G1 gate that
catches drift between the doc line and the constant (not between the doc
and the live DB — that's what the boot guard is for).

**Deliberately narrow scope.** This guard checks the VERSION only — no
table-enumeration or "every physical table accounted for" logic; that's
plane 2's reconciliation job (BRIEF-0044-d), scoped OUT here on purpose so
the two planes stay genuinely separate. No `world_id` on `schema_meta` —
it is GLOBAL static-plane; per-world runtime types are a different plane
entirely.

---

## ENTITY-TYPE CONSTRUCTOR — socle registry + schema-birth history (BRIEF-0044-b, schema v1.87)

Plane 2 of the C2 two-plane governance design (BRIEF-0044-a shipped plane 1,
`schema_meta`, v1.86): the per-world runtime-type manifest that the
governed runtime-DDL writer (BRIEF-0044-c), reconciliation (BRIEF-0044-d),
and B1 quarantine (BRIEF-0044-e) all read. This step ships the two static
tables ONLY — no writer, no DDL emission, no traits, no seeding. No
runtime types exist yet, so no code path reads a populated row.

**`entity_type` mirrors `location_type_catalog`, not the entity-extension
shape.** A plain `TEXT PRIMARY KEY` with a `world_id` foreign key — NOT
`id: str = Field(primary_key=True, foreign_key="entity.id")` like
`Character`/`Location`/`Item`. `entity_type` is world-scoped CONFIG
describing a category of entity, never an entity itself; the FUTURE
`ext_*` runtime tables (BRIEF-0044-c) are the ones that take the
extension shape, one per registered type.

**Dname1/Ddrop1 belt-and-suspenders in the CHECK constraints, not just the
writer.** `physical_table GLOB 'ext_*'` and `status IN ('active',
'retired','quarantined')` are enforced at the schema level now, even
though the writer that produces these values doesn't exist until
BRIEF-0044-c — a partially-built registry can never smuggle a non-`ext_`
physical table name or an out-of-vocabulary status past the DB, regardless
of which code path writes it later. `quarantined` (B1) and the `retired`
soft-retire value (Ddrop1 — never a `DROP`) are both present in the CHECK
now so their respective briefs need no ALTER.

**Dgov1 — reserved governance columns, a named cross-ticket exception.**
`write_authorities` (JSON, which authorities may write ROWS of this type)
and `ai_proposable` (the future `mutable_by_ai` trait wire, TICKET-0045)
ship now, unpopulated, with NO reader until 0047. This deliberately
violates "no structure without a reader" — unlike `location_type_catalog`,
whose reader lands in the SAME ticket (BRIEF-0039-c/d/e). The exception is
taken because `entity_type` is the chantier's central table: adding these
columns via a later ALTER would touch it on every subsequent ticket
through 0047. Recorded here as the named exception; no reader may be
"helpfully" added before 0047.

**`entity_type_history` extends "History is sacred" to the schema grain.**
Same append-only posture as `Ledger` and the closed `FactionMembership`/
`FactionRole` rows: no `change_history` column, because there is no
"previous state" to snapshot — each row already IS one immutable event
(A1). `definition_snapshot` (JSON) carries the full definition at the
instant of the event and `ddl_text` carries the exact DDL emitted, making
each row independently auditable and replayable without reconstructing
state from a diff chain. Only `'type_created'` is produced at the socle;
`trait_added` (0045), `type_retired`/`type_quarantined`/`type_restored`
(BRIEF-0044-e) are reserved in the `event` CHECK now so those briefs need
no ALTER — the closed-vocabulary-via-CHECK idiom already used for
`npc_goal.status`, `goal_prerequisite.type`, and `skill.base_domain`.

**Scope boundary held.** No writer, no `[CANON_TABLES]`/
`[ALLOWED_SITES]` policy edit (BRIEF-0044-c's job — adding these tables to
`canon_write_policy.txt` before a governed write site exists would leave
the policy pointing at nothing); no reconciliation; no quarantine status
transition logic beyond reserving the enum values. Migration
`scripts/migrate_v1_87_entity_type.py` follows the `migrate_v1_86_schema_meta`
two-independent-guard shape (table existence, index existence) but seeds
nothing — a virgin registry, unlike `location_type_catalog`'s v1.84 seed.

## ENGINE — TRANSACTIONAL DDL ON SQLITE, UNBLOCKS A1 (BRIEF-0044-f, no schema change)

BRIEF-0044-c's live gate proved A1 (the "(CREATE TABLE ext_*) + (INSERT
entity_type) + (INSERT entity_type_history) commit together or none do"
guarantee) cannot hold on the engine as configured: pysqlite's default
driver mode auto-commits any pending transaction the instant a DDL
statement runs, so a `CREATE TABLE` inside `engine.begin()` survives a
later `rollback()` even though the row INSERTs around it correctly do
not. This was asserted "(it does)" in BRIEF-0044-c's own mini-RECON and
was wrong — see `tooling/questions/QUESTION-TICKET-0044.md` for the
minimal reproduction and root cause. This step lands BEFORE BRIEF-0044-c
because the fix is to the shared `engine` object every canon-write path
binds to, not to `writes/schema.py`; 0044-c's code needed no change once
this landed.

**The fix is SQLAlchemy's own documented pysqlite recipe, guarded to
`dialect.name == "sqlite"`.** In the existing connect listener
(`db.py::_enable_sqlite_foreign_keys`), `dbapi_connection.isolation_level
= None` disables the driver's own BEGIN/COMMIT management (which is what
was silently committing DDL early); a new `engine`-instance `"begin"`
listener (`_begin_sqlite_transaction`) issues an explicit
`conn.exec_driver_sql("BEGIN")` so every transaction — DDL included — is
one SQLite transaction, committed or rolled back as a whole. The existing
`PRAGMA foreign_keys=ON` connect-time behavior is unaffected (it always
ran in autocommit at connect time, before any BEGIN). Both empirically
verified on the installed SQLAlchemy 2.0.50 / sqlmodel 0.0.38 pair against
scratch databases: a forced failure between a CREATE TABLE and a later
INSERT now leaves neither; a committed transaction leaves both; FK
enforcement still fires on a fresh connection; every existing
`migrate_*.py`'s DDL pattern (`engine.begin()` context manager, or a bare
`Table.create(engine)`) still lands and commits under the new setup, and
`scripts/init_db.py` still fully creates a virgin database (49 tables).
Re-running BRIEF-0044-c's forced-failure A1 test through the actual
`create_entity_type` afterward, unmodified, now correctly leaves none of
the three writes behind.

**Process lesson — engine/driver claims in a mini-RECON are asserted-then-
verified, never trusted.** BRIEF-0044-c's mini-RECON stated the SQLite
CREATE-TABLE-rollback behavior as settled fact ("(it does)") without
reproducing it; that claim was false and only surfaced at the brief's own
live-gate check. This brief's own mini-RECON therefore re-verified every
claim (SQLAlchemy major version, the exact `"begin"`-listener incantation,
the connect-listener class-vs-instance question, and the full
`migrate_*.py`/`init_db.py` regression surface) empirically before
touching `db.py` — the verify step is load-bearing for exactly this kind
of claim, and is not satisfied by restating the recipe from memory.

**Scope held.** `writes/schema.py`/`create_entity_type` and its A1
acceptance test are untouched (BRIEF-0044-c's own scope); no change to
what any canon-write path writes or to `canon_write_policy.txt`; no
Postgres/Supabase transactional path (untouched, sqlite-guarded); A1
itself is not broadened or narrowed, only made true on this engine.

---

## ENTITY-TYPE CONSTRUCTOR — governed runtime-DDL writer (BRIEF-0044-c, no schema change)

The socle's third structural-write authority (D2): `writes/schema.py::create_entity_type`
materializes a runtime `ext_*` table AND registers it — one transaction,
all three writes or none (A1): `CREATE TABLE ext_<slug>`, the `entity_type`
row, the `entity_type_history` `type_created` row. This is CREATOR-authority
structural, invoked only by explicit creator action, never by an AI
proposal — the "two sanctioned canon-write paths" invariant (AI-proposal
pipeline, creator CRUD) is unchanged for canon ROWS; this is a distinct,
named THIRD authority for canon STRUCTURE plus the two static registry
tables. CLAUDE.md's canon-write invariant is amended accordingly.

**Socle boundary held.** The writer performs NO row write into any `ext_*`
table — entities of a runtime type are authored later (0046 creator CRUD,
0047 AI dispatch). The F1' runtime write-authority check for DYNAMIC-table
ROW writes is therefore 0047's concern; `runtime_ddl_guard.py` here is a
STATIC guard on the DDL writer itself, not the F1' runtime check.

**Dcol1 — closed column-type enum, the sole source of SQL type
fragments.** `_COLUMN_TYPES` maps TEXT/INTEGER/REAL/BOOLEAN/JSON/TIMESTAMP/
FK_ENTITY/FK_ENTITY_NULLABLE to their SQL fragments (BOOLEAN emits an
`INTEGER` column with a `CHECK (col IN (0,1))`; JSON is SQLite `TEXT`). A
`col_type` outside this set raises before any DDL is built. The mandatory
shared PK (`id TEXT PRIMARY KEY REFERENCES entity(id)`) is emitted first,
always, never part of the caller-supplied `columns` — reproducing the
extension-table PK shape (`Character`/`Location`/... in `canon.py`) exactly.

**Dname1 — mandatory `ext_` prefix, single-sourced.** `EXT_PREFIX = "ext_"`
is the ONLY definition of the literal in the codebase; BRIEF-0044-d's
reconciliation imports this constant rather than re-declaring it.
`_validate_identifier` (regex `^[a-z][a-z0-9_]{0,62}$`, closed reserved-word
set, no leading/trailing underscore) gates `slug` and every `col_name`
before any DDL text exists. Collision is checked two ways: `inspect(engine)
.has_table(...)` (the physical table doesn't already exist) AND no
`entity_type` row already claims the slug (case-insensitive) or the
physical table name.

**Ddrop1 — CREATE only, structurally.** No `DROP`/`ALTER` branch, and no
`ADD COLUMN` function, exists anywhere in `writes/schema.py` — not
"unused," genuinely absent. `runtime_ddl_guard.py` (new G1 check, AST-based)
enforces this fail-closed over the module: no DROP/ALTER token reaches a
code-path string (docstrings and the `_RESERVED_WORDS` rejection set are
the two named exemptions — the latter's entire purpose is REJECTING those
words as identifiers); every literal SQL-type fragment traces to the
`_COLUMN_TYPES` enum or the one fixed PK line; the `"ext_"` literal appears
nowhere but `EXT_PREFIX`; every `.add(...)` targets only `EntityType`/
`EntityTypeHistory`, and no raw-SQL `.execute()`/`.exec()` resolves to an
INSERT/UPDATE/DELETE on a dynamic table. Zero parsed assertions is itself a
failure (vacuous-proof), matching the `door_terminal.py`/
`single_canon_write.py` idiom this check is built on.

**Canon-write policy closed, not left open.** `entity_type` and
`entity_type_history` join `[CANON_TABLES]`; `create_entity_type` is the
sole `[ALLOWED_SITES]` entry for both. The DDL `session.execute(text(...))`
is a `CREATE TABLE` statement, not `INSERT`/`UPDATE`/`DELETE` — invisible to
`single_canon_write.py`'s row-write attribution by construction, not a
broadening of row-write authority; only the two INSERTs are row writes and
both are allow-listed.

## SCHEMA VERSION — two-plane governance (C2), plane 2: physical-table reconciliation (BRIEF-0044-d, no schema change)

Plane 1 (`schema_meta`, BRIEF-0044-a) answers "is the code's expected
static schema live in this DB." Plane 2 answers a different question that
plane 1 structurally cannot: "does every PHYSICAL table in the live DB
actually belong here." Once `create_entity_type` can birth tables at
runtime, a table can exist that no migration declared and no registry row
claims — that is corruption or a failed constructor write, and the two
planes never collapse into one check.

**Why runtime, not static.** The accounting depends on the live database's
actual tables (`sqlalchemy.inspect(engine).get_table_names()`) and the
live `entity_type` rows — a static AST check cannot see either. So
`schema_reconcile.py` runs the ACCOUNTING at boot and as a CLI
(`python -m world_engine.schema_reconcile`); the new
`schema_reconciliation.py` G1 check stays static and guards only that the
MECHANISM exists, is `SQLModel.metadata`-sourced (never a hardcoded table
list), single-sources `EXT_PREFIX` from `writes/schema.py`, and is
imported by the boot module — mirroring `single_canon_write.py`'s
static-AST precedent for a check that cannot itself touch the DB.

**Accounted set.** `static ∪ registered_runtime ∪ {_orphan_ext_* pattern}`.
`static_table_names()` is every table on `SQLModel.metadata` post-import.
`registered_runtime_tables()` reads `entity_type.physical_table` for ALL
statuses (`active`, `retired`, `quarantined`) — a retired or quarantined
type's table still physically exists and must not read as unaccounted.
`_orphan_ext_*` (BRIEF-0044-e's quarantine tables) are pattern-accounted:
this step only accounts for that prefix, it never creates it. Any `ext_*`
table outside all three is the dangerous case — a runtime table with no
registry row — and trips both the CLI (`sys.exit(1)`, naming it) and the
boot guard (`RuntimeError`, refuse to serve).

**Boot wiring extends, not duplicates.** `cockpit/app.py`'s single startup
hook now runs the plane-1 version check, then the plane-2 reconciliation
check, in that order, both fail-closed — not two independent hooks, one
guard with two sequential gates.

## ENTITY-TYPE CONSTRUCTOR — rollback quarantine (B1) (BRIEF-0044-e, no schema change)

Consequence #2 of D2 (hot materialization): a code rollback past the
constructor version finds `ext_*` tables it does not know about, and —
because `PRAGMA foreign_keys=ON` (`db.py:44`) — their FK into `entity`
BLOCKS the old code's `entity` deletes. B1 (locked at intake): quarantine
by construction, not prevention. `entity_type` is the manifest;
`scripts/rollback_quarantine.py` (danger_class: destructive_data, manual —
mirrors `backup.py`, no hook, no scheduler, no boot integration) rebuilds
each runtime table WITHOUT the entity FK, preserving data under
`_orphan_ext_*`.

**Why rename alone fails, and why a rebuild is required.** SQLite has no
`ALTER TABLE DROP CONSTRAINT`. While `ext_grimoire.id REFERENCES
entity(id)` exists under any name, an old-code `DELETE` on `entity` is
still blocked by a table the old code cannot see. Only a rebuild —
`CREATE TABLE _orphan_ext_<slug>` with the same columns MINUS the entity
FK (and minus any other `REFERENCES entity(id)` column's FK, kept plain
`TEXT`) → copy every row → `DROP TABLE ext_<slug>` — actually neutralizes
the FK. `_table_columns_from_creation` sources the exact original column
shape from the `type_created` `entity_type_history` row (the manifest's
own birth record), never re-derived or guessed; `_orphan_column_fragment`
reuses `writes/schema.py`'s `_COLUMN_TYPES` enum for every non-FK column,
so no second SQL-type-fragment source exists.

**Restore is a rebuild, not an undo, and the lossy edge is inherent.**
`--restore` rebuilds `ext_<slug>` WITH the FK restored (via
`writes/schema.py::_build_create_table_ddl`, the SAME builder the original
constructor used — single-sourced DDL shape). A row whose `entity` still
exists re-attaches. A row whose `entity` was deleted DURING the
quarantine window cannot re-attach (its FK target is gone) — that loss is
inherent to letting old code mutate `entity` freely during the window,
not a bug to eliminate. B1's guarantee is honesty, not losslessness: that
row is parked in `_orphan_lost_ext_<slug>` (created on demand, no FK),
counted, and the count is recorded on the `type_restored` history row's
`definition_snapshot.lost_count` — never a silent drop.

**History is sacred on both transitions.** `type_quarantined` and
`type_restored` were already reserved in `entity_type_history`'s CHECK
constraint at BRIEF-0044-b (Dgov1-style forward reservation) — this brief
USES them, no `ALTER` needed, confirmed live. Both statuses
(`quarantined`/`active`) and both history events append; nothing is
overwritten in place.

**Reconciliation stays green through both transitions.**
`schema_reconcile.py`'s `_ORPHAN_PREFIX` pattern-accounts `_orphan_ext_*`
during quarantine (BRIEF-0044-d) — `python -m world_engine.schema_reconcile`
reports nothing unaccounted while a type sits quarantined. The B1 reader,
`scripts/test_rollback_quarantine.py`, exercises the full cycle (create a
throwaway type via `create_entity_type` → quarantine → simulate an
old-code `entity` delete during the window → restore) against a scratch
DB, asserting the FK is genuinely absent on `_orphan_ext_qtest`, present
again on the rebuilt `ext_qtest`, the deleted-entity row lands in
`_orphan_lost_ext_qtest`, and reconciliation is clean throughout — 18/18
assertions, satisfying "no structure without a reader" for the socle.

**The rollback contract (verbatim, also in CLAUDE.md):**

> Once a runtime type exists, rolling code back past the constructor
> version requires running scripts/rollback_quarantine.py first (after a
> backup). Roll-forward restoration (--restore) is potentially lossy,
> bounded to rows whose entity row was deleted during the rollback
> window; every lost row is preserved in _orphan_lost_* and reported —
> never silently dropped. This contract is SQLite-scoped (the
> rebuild-without-FK recipe is SQLite-specific), matching the engine's
> current single-backend reality.

---

## TRAIT REGISTRY — code-source-of-truth, structural reader enforcement (BRIEF-0045-b, no schema change)

TICKET-0045. A1 (locked at intake): the trait registry is code, not data.
`src/world_engine/traits.py` is the single source of truth for what a
trait IS — its key, its column bundle, its FK spec, and an IMPORTABLE
reference to its reader — never a DB row: a trait declared in the DB
cannot structurally prove its reader exists (a TEXT string
`"placement.spawn_point"` is unverifiable at commit). New traits (e.g.
`rideable`) are added via Claude Code and become available to every
entity type — never hot-editable by the creator at runtime. The
projection (which entity_type has checked which trait) is the separate,
DB-backed `entity_trait` table (BRIEF-0045-a); this decision covers only
the definitional module.

**E2 — every trait carries a real reader, enforced structurally, not
documentarily.** `TraitDef` is a frozen dataclass whose `__post_init__`
raises `ValueError` unless exactly one of `reader_callable`,
`reader_guard`, `reader_deferred` is non-`None` — a malformed trait fails
at import time, before `trait_reader.py` (BRIEF-0045-c) ever runs. This
makes "no structure without a reader" a construction-time guarantee, the
same posture as `runtime_ddl_guard.py`'s enum-typed DDL enforcement.

**F1 — two reader forms, because `secretable` has no positive accessor.**
Most traits declare `reader_callable` (a dotted `"module:function"` path
the check resolves to a real, importable callable — `describable` to
`context.py:_npc_context_identity`, `spatial` to
`placement.py:spawn_point`, `knowable` to `context.py:_npc_context_speak`,
all RECON-anchored on live main at schema v1.87). `secretable`'s reader is
a negative WHERE-clause exclusion (`is_secret == False` at query
construction, `context.py:167,194`), not an accessor a callable can name —
so `reader_guard` carries `(module_dotted_path, column_name)` and the
check instead confirms the column appears in a query-construction filter
in that module. This is a second, mutually-exclusive reader FORM, never a
second doctrine for what counts as "read": secrets stay excluded
structurally, never instructionally — `secretable`'s reader_guard points
at the filter, not at a prose instruction to the model.

**B2(ii) — `mutable_by_ai` is the sole `reader_deferred` exception.** Its
reader is the canon-write dispatch of TICKET-0047
(`entity_type.write_authorities`/`ai_proposable`, reserved unpopulated at
the schema v1.87 socle, BRIEF-0044-b) — not yet built. `trait_reader.py`
tolerates this ONE trait by name; renaming any other trait to claim
`reader_deferred` is a FAIL (verified by BRIEF-0045-c's check, red-teamed
in that brief's Done means). This mirrors the socle's own
`write_authorities`/`ai_proposable` ticket-spanning exception — the
project now has exactly two such named, deliberate gaps, both logged
here.

**S-norme — one vocabulary, one partition authority.** `trait_keys()` is
the sole source `scripts/seed_trait_keys.py` (BRIEF-0045-a) and the
projection check (BRIEF-0045-c) cross-reference; that seed script's
literal is a pre-registry bootstrap only, asserted equal to `trait_keys()`
the instant this module exists (verified live: re-running
`seed_trait_keys.py` after this brief now imports `traits.py` and passes
the equality assertion; a hand-mocked drift was confirmed to FAIL the
same assertion). `checkable_traits()` is the second view over the same
`TRAITS` tuple (excludes `describable`, the non-checkable socle) — the
constructor UI (TICKET-0046) will consume it, but no UI ships in this
brief.

**D-derived (deferral logged, OUT).** Value-conditioned / derived traits
(Nia's "rideable if size > medium", "portable if size < medium") are a
richer third tier the registry does not model: `TraitDef` carries no
`condition` field. Trigger for building this: when a value-conditioned
trait is first genuinely needed by a ticket (not anticipated here).

## SOCLE TRAITS ARE IMPLICIT, NEVER PROJECTED (BRIEF-0045-d, no schema change)

TICKET-0045. `describable` (and any future non-checkable trait) is the
"what an entity should have, no exception" socle (Nia's framing): every
entity_type carries it, unconditionally — never a palette checkbox, never
an `entity_trait` row. `traits.socle_traits()` is the single authority for
"which traits are implicit", the counterpart to `checkable_traits()` from
BRIEF-0045-b: together the two partition `TRAITS` totally and disjointly
(`set(socle_traits()) | set(checkable_traits()) == set(TRAITS)`, and the
two sets never intersect — asserted structurally, not just documented).

**Why no row.** A describable projection row on every entity_type would be
redundant on every single row and invite drift (a type missing the row by
accident vs. by design becomes unanswerable). Instead, the (future, 0046)
constructor reads `socle_traits() + that type's entity_trait rows`;
describable is always in the effective set without ever being written.

**Structural, not disciplinary.** `trait_registry_projection.py`
(BRIEF-0045-c) gained a third volet: any `entity_trait` row naming a socle
trait_key is a FAIL ("socle traits are implicit, never projected"),
verified live by planting a `describable` row in the temp fixture and
confirming the check FAILs, then removing it and confirming green again.

## TRAIT EXT-COLUMN TYPING + FIELD-SPEC (BRIEF-0046-a, no schema change)

TICKET-0046. Completes the 0045 derivation gap flagged at
`writes/schema.py:15` ("`columns` is supplied by the caller; deriving it
from traits is 0045"): `TraitDef` now carries `ext_columns: tuple[
ExtColumnSpec, ...]`, replacing the dormant, reader-less `columns`/`fk`
pair (RECON confirmed no `.columns`/`.fk` consumer existed anywhere in
`src/`). `ExtColumnSpec` bundles a name, a `col_type` (validated against
`writes/schema.py::valid_col_types()`, a new read-only accessor onto the
same Dcol1 enum — referenced, never redefined) and the form field-spec
that column renders as, so one declaration on the trait is the single
source for both the DDL `columns` list `create_entity_type` consumes and
the generated-form fields `GET /api/entity-types` will serve (0046-b).

**Zero-ext-column rule.** `describable` (socle), `knowable`, and
`mutable_by_ai` all declare `ext_columns=()` — their concerns are either
already served by `ENTITY_BASE_FIELDS` (`describable`'s name/description)
or carry no typed state at all. `spatial` contributes `location_id`
(`FK_ENTITY_NULLABLE`); `secretable` contributes `is_secret` (`BOOLEAN`).

**Single readers, ordered.** `ext_columns_for()` / `form_fields_for()`
(E2: structure ships with its reader) both iterate `socle_traits()` first,
then `checkable_traits()` filtered to the requested keys in `TRAITS`
declaration order, raising on any cross-trait name collision — the one
ordering both derivations share.

**Base-name guard, hardcoded by necessity.** A module-import-time
assertion in `traits.py` rejects a socle trait whose `ext_columns` collides
with an `ENTITY_BASE_FIELDS` name. The base-name set is hardcoded (with a
pointer comment) rather than imported from `cockpit/crud/entities.py`:
that module sits in the FastAPI cockpit route layer and pulls in the
whole app, which `traits.py` — a core module imported by verify checks
and (0046-b) the DDL path — must stay free of.

**Side effect on an existing check, fixed here.** `traits.py` now
transitively imports `world_engine.models` (via `writes.schema`).
`trait_registry_projection.py`'s temp-fixture helper used to purge every
`world_engine.*` submodule from `sys.modules` before reimporting to force
a fresh engine bind; re-executing `models`' class bodies a second time
against SQLModel's shared metadata now collides ("table already defined").
Fixed by excluding `world_engine.models*` from the purge — the module only
ever needs to be imported once per process; only `world_engine.db` (for
its module-level `engine` binding) needs the fresh reimport.

## ENTITY-TYPE CONSTRUCTOR — creator route + runtime-type serializer (BRIEF-0046-b, no schema change)

TICKET-0046. `POST /api/entity-types` is the creator-direct type-creation
path: it composes the governed DDL/registry writer (`create_entity_type`,
BRIEF-0044-c) with the `entity_trait` projection inserts (BRIEF-0045-a) in
ONE transaction — never a second write path, never a bypass. Validation
order: unknown/non-checkable `trait_keys` (including socle keys like
`describable`, which are implicit and never a checkbox) -> 422; a `slug`
colliding case-insensitively with a static `ENTITY_TYPE_REGISTRY` key -> 422
("runtime-vs-static" collision — `create_entity_type` itself already guards
runtime-vs-runtime via `_check_collision`). `columns` come from
`ext_columns_for(trait_keys)` exclusively (never recomputed inline); no
`entity_trait` row is written for a socle trait.

**`db.flush()` between the governed writer and the `entity_trait` inserts —
required, not defensive.** Neither `EntityType` nor `EntityTrait` declares
an ORM `relationship()` to the other (plain FK columns only, matching the
rest of this codebase). Without an explicit flush, SQLAlchemy's
unit-of-work has no dependency information ordering the two mapper
batches within one flush and can emit the `entity_trait` INSERT before its
parent `entity_type` row exists, raising a FOREIGN KEY constraint failure
(reproduced directly: `entity_type`/`entity_trait` added un-flushed in the
same transaction fails every time, table-name-ordered, not FK-ordered;
`entity_type`/`entity_type_history` — both written inside
`create_entity_type` itself — happens to commit fine un-flushed only
because "entity_type" alphabetically precedes "entity_type_history",
not because SQLAlchemy resolved the FK). This is the same reason
`_create_entity_core` (`cockpit/crud/entities.py`) flushes the `entity` row
before adding its extension row — an established codebase pattern for any
multi-table insert of FK-dependent rows sharing one uncommitted
transaction, now also documented here since 0046-b hit it fresh.

**Serializer is the single source for the frontend (0046-c/d/e build on
this).** `GET /api/entity-types` appends one `types[slug]` entry per
ACTIVE, world-scoped `entity_type` row (`fields` from `form_fields_for`
over that row's `entity_trait` keys), a new `runtime_types` key (the
runtime slug list, letting the client distinguish runtime from static
without shipping the static set), and a new `checkable_traits` key (the
trait-palette source for the UI, BRIEF-0046-c). Static entries and their
`fields` are unchanged — regression-verified against the pre-change
serializer output.

**`changed_by="creator"`.** RECON (`grep changed_by src/world_engine/cockpit`)
found no dedicated creator-identity accessor; every existing author-CRUD
write site (`write_npc_prices`, `write_location_subculture`,
`write_faction_role`, `write_relation`, goal/skill writers, etc.) already
passes the literal `"creator"`. This route follows the same established
convention rather than inventing a new identity source.

---

## DYNAMIC TAB FACTORY — runtime Creation tabs + page_contract mechanism assertion (BRIEF-0046-d, no schema change)

TICKET-0046 (B1/E1). Runtime Creation tabs are injected by a single
boot/refresh factory, `_buildRuntimeCreationTabs()`
(`cockpit/index.html`) — the sole producer of a runtime `#ctab-<slug>`
button + `CREATION_TABS[<slug>]` entry, one per ACTIVE, world-scoped
`entity_type` row from `authorRegistry.runtime_types`
(`GET /api/entity-types`, BRIEF-0046-b). Every injected entry is a NORMAL
entity-archetype registry entry on the shared `creation-editor-area`
shell (`createPanel: () => authorRenderSheet({}, true, slug)`) — no new
container, no per-type hand authoring, no dispatcher branch. The factory
is idempotent and world-scoped: a `_runtimeCreationSlugs` set tracks
exactly what it injected, so a slug no longer live (retirement, or a
world switch) is removed without ever touching a static entry/button.

`refreshCreationTabs()` re-fetches `authorRegistry` then rebuilds — called
from `creationInit()` (boot), from the Constructeur's create-success path
(BRIEF-0046-c), and from `_creationRunWorldSwitchResets()` (both
`activateWorld()` and `worldDeleteConfirm()` already awaited it) so a
world switch never leaves the previous world's runtime tab live.

**Fixed during live verification: the factory must never write
`currentCreationSubTab` directly.** The first draft reset
`currentCreationSubTab` to `'npc'` inside the removal loop, on the
assumption the caller's subsequent `showCreationSubTab(currentCreationSubTab)`
would then activate it. Instead this silently defeated
`showCreationSubTab`'s own `prev !== tab` guard (`prev` is captured as
whatever `currentCreationSubTab` already holds at call time) — with both
`prev` and `tab` now `'npc'`, `onTabEnter` never ran and the stale
removed-type form stayed rendered under the NPC tab. The factory now
leaves `currentCreationSubTab` untouched; instead the two world-switch
call sites (`activateWorld`, `worldDeleteConfirm`) compute the fallback
inline right before calling `showCreationSubTab`:
`CREATION_TABS[currentCreationSubTab] ? currentCreationSubTab : 'npc'` —
so `prev` (still the just-removed slug) legitimately differs from the
resolved `tab`, and the reset fires. General lesson: never pre-mutate a
dispatcher's tracked "current" state ahead of the call that is supposed
to react to the transition — the transition's own before/after diff is
what triggers the reset.

`page_contract.py` (E1) now asserts the MECHANISM, never live types
(no-DB doctrine preserved): `_buildRuntimeCreationTabs` is defined and
called from `creationInit`; every static `id="ctab-<slug>"` in the raw
HTML source must have its slug in the frozen `TAB_KEYS` list (a runtime
button's id only ever exists in the live DOM via `insertAdjacentHTML`
template interpolation, never in the static source text, so this static
scan cannot false-positive on an injected tab) — red-teamed both ways:
hand-adding a static `#ctab-foo` fails, and removing the factory's call
from `creationInit` fails. `constructeur` was added to `TAB_KEYS` here
(its registry entry + `primaryAction` landed in BRIEF-0046-c, uncovered
by the check until now).

---

## DYNAMIC INSTANCE CRUD for custom ext_* + json_ui_boundary F1 volet (BRIEF-0046-e, no schema change)

TICKET-0046 (A1 vertical slice, closing). `POST`/`GET`/`PUT /api/entities`
now dispatch on `type`: a static `ENTITY_TYPE_REGISTRY` slug takes the
unchanged SQLModel-class path (`_create_static_entity_core`, byte-for-byte
moved out of the old `_create_entity_core`); a slug resolving to an ACTIVE,
world-scoped `entity_type` row (`_runtime_type_spec`, the single "is this
governed" gate) takes the new reflected-table path — `entity_runtime.py`'s
`_insert_runtime_ext_row`/`_update_runtime_ext_row`/`_read_runtime_ext_row`,
built entirely on parameterized SQLAlchemy Core statements
(`sa_insert(table).values(...)`, never string interpolation) against a
`Table` reflected via `autoload_with`. `physical_table` is never user
input: it only ever comes from an `entity_type` row already validated as a
safe identifier at creation (`writes/schema.py`, Dname1) and DB-CHECK-
constrained to `GLOB 'ext_*'`. Neither dispatch branch is reachable for an
AI proposal — this is the creator-CRUD path only, same as every static
type; the AI-proposal dispatch and its fail-closed completeness check are
TICKET-0047. An ungoverned slug (neither static nor an active
`entity_type`) 422s on create AND update before any table is touched
(A1 fail-closed), verified by the new `dynamic_ext_crud.py` (temp-fixture
idiom, same as `trait_registry_projection.py`) and live in the browser.

**Delete needed no change (brief's "REPORT which" resolved).** RECON
`grep db.delete\(` across `entities.py` found zero hits: `delete_entity`
is, and always was, a SOFT delete (`entity.status = 'inactive'`) with no
ext-row touch of any kind, for ANY entity type, static or runtime —
already generic over `type`. The brief's drafted "delete the ext row then
the entity row" assumption didn't match the actual code; the brief itself
named the resolution mechanism ("match the existing pattern"), and the
existing pattern is non-destructive. `entity`/`ext_*` were never eligible
for the closed hard-delete list (CLAUDE.md) and stay that way.

**SQLite has no native BOOLEAN.** The Dcol1 `BOOLEAN` mapping is
`INTEGER CHECK (col IN (0,1))`; plain Core reflection (no ORM `Boolean`
type decorator) hands back a raw `0`/`1` int on read. `_read_runtime_ext_row`
coerces any `kind: "bool"` field to a real Python `bool` so the JSON
response matches every other bool field in this API (e.g.
`ENTITY_BASE_FIELDS.is_public`) — caught by `dynamic_ext_crud.py`'s strict
`is True`/`is False` assertions before this fix, not a cosmetic choice.

**`json_ui_boundary.py` gained a fourth volet (F1):** imports `traits`
(pure, no DB) and fails if any `ExtColumnSpec.field.get("kind") ==
"json"` across the whole registry — mirrors `ExtColumnSpec.__post_init__`'s
construction-time guard at the verify plane, defense in depth against a
future removal of that guard. Red-teamed: mutating a real spec's `field`
dict in place to plant `kind:"json"` FAILs by name; reverting returns green.

**Module split, not a baseline exemption (`module_budget.py`).** The
runtime-CRUD addition pushed `entities.py` past the 1000-line cap; per
that check's own "no permanent exemptions — the failing check IS the
mechanism" doctrine, the ext-row mechanics moved to a new
`src/world_engine/cockpit/crud/entity_runtime.py` instead. To keep the
import graph acyclic (`entity_runtime.py` must never import `entities.py`),
the two generic field helpers `_validate_entity_ref`/`_coerce_field`
(previously defined in `entities.py`) moved to `_shared.py`, the existing
closed cross-domain accessor set (R6 — this brief is the "requires a
brief" justification for the addition); both `entities.py` and
`entity_runtime.py` import them from there, one direction only.
`single_canon_write.py`'s policy and `llm_parse_chokepoint.py`'s
`_coerce_field` allow-list entry were re-keyed to match.

**Deferred:** runtime-type relations/knowledge editing (both stay `[]` for
a governed runtime type this brief, same as any unknown type today) —
logged as "runtime-type relations/knowledge UI", picked up whenever a
concrete need lands, not necessarily 0047. Also deferred (not a brief
requirement, noted for awareness): `ext_*` row INSERT/UPDATE is invisible
to `single_canon_write.py`'s static per-table attribution (it only
recognizes raw SQL-text `.execute(text(...))`, not Core statement
objects) — same class of blind spot already precedented for
`create_entity_type`'s DDL in `canon_write_policy.txt`'s own comments,
mitigated here by `dynamic_ext_crud.py`'s functional round-trip instead
of a static guard. A `runtime_ddl_guard.py`-style dedicated AST guard for
`entity_runtime.py`'s row-write shape would close that gap structurally;
out of this brief's scope, worth a future ticket.

## DB ENGINE — WORLD_ENGINE_ENV primary resolver, fail-closed (BRIEF-0049-a, no schema change)

TICKET-0049 (test database infrastructure, opening). `src/world_engine/db.py`
previously read `WORLD_ENGINE_DATABASE_URL` and silently fell back to the
prod SQLite file (`~/.world_engine/world_engine.db`) when unset — the exact
trap that let test runs write into prod. `_resolve_database_url()` is now
the single resolution point: an explicit, non-empty `WORLD_ENGINE_DATABASE_URL`
wins outright (override, satisfies fail-closed on its own — used unchanged
by `scripts/test_ddl_atomicity.py`, `scripts/test_rollback_quarantine.py`,
and every temp-fixture `tooling/verify/checks/*.py`); otherwise
`WORLD_ENGINE_ENV` must be exactly `"prod"` or `"test"`, resolving to
`~/.world_engine/world_engine.db` or `~/.world_engine/test/world_engine_test.db`
respectively. Any other state — both unset, or an unrecognized
`WORLD_ENGINE_ENV` value — raises `RuntimeError` at import time; there is
no implicit default. `docs/launch-procedure.md` documents the operator-side
export for prod and test. F1 (per TICKET-0049 intake): explicit URL >
resolved ENV > refuse to start.

## VERIFY — env_fail_closed + env_guard, KNOWN_OPERATOR_SCRIPT_ALLOW (BRIEF-0049-d, no schema change)

TICKET-0049 (test database infrastructure, closing). Two new G1 checks make
the ticket's promise structural rather than a `CLAUDE.md` convention:
`tooling/verify/checks/env_fail_closed.py` statically proves (AST-only, no
DB) that `db.py`'s resolver carries no `os.getenv(..., <default>)` shape
anywhere in the module, that the unresolved path raises with "Refusing to
start" in its message, and that the `"test"` branch resolves to a path
distinct from `"prod"` containing a `test` segment.
`tooling/verify/checks/env_guard.py` walks every `scripts/*.py` that
imports `world_engine.db` and requires, lexically before that import, an
explicit `os.environ[...]` set or a fail-closed
`os.environ.get("WORLD_ENGINE_ENV")` + `sys.exit` guard — both vacuous-proof
(zero files, or zero engine-importing files, is a FAILURE).

**Escalation resolved (`tooling/questions/QUESTION-TICKET-0049.md`, D1-a/c).**
BRIEF-0049-d's mini-RECON expected exactly one exception (`seed_pilot.py`);
the actual `scripts/*.py` importing the engine numbered 55, not 6 — every
`migrate_v1_*.py` (33), every `apply_ticket_NNNN_prompt_*.py` (10), plus
`backup.py`, `init_db.py`, `talk.py`, `analyze_conversation.py`,
`rollback_quarantine.py`, `seed_trait_keys.py`, and
`preview_tick_context.py` import the engine with no per-script guard.
Nia's call (2026-07-27, option A): allow-list all of them — these scripts
are no longer in active use and pose no ongoing risk — rather than
retrofitting ~49 scripts or narrowing the check's scope. `env_guard.py`'s
`KNOWN_OPERATOR_SCRIPT_ALLOW` names every one explicitly, each with a
one-line rationale (migration / one-shot ticket-apply / standing operator
tool), so the check still enforces fail-closed on every script BRIEF-0049-b/
-c actually targets (`seed_test.py`, `reset_test.py`, `test_context.py`,
`test_ddl_atomicity.py`, `test_rollback_quarantine.py`) and on any new
script added later — the allow-list is a closed, named exception set, not a
silent bypass.

## CONVERSATION WINDOW CONFIG — dedicated table, summary default-on, editing surface deferred (BRIEF-0050-a, schema v1.89)

TICKET-0050 (conversation context window: sliding summary + K-verbatim tail
+ scene re-injection). This step lays the persisted, relational config every
later brief reads: word budget, verbatim-turn count, summary kill-switch.

**L1 — dedicated narrow relational table, not a key-value settings table.**
No key-value config table exists in the engine (RECON-0050); the in-doctrine
pattern for world-scoped curated config is a dedicated table plus an
upsert-one chokepoint, same family as `location_type_catalog`
(`writes.upsert_location_type` precedent) — not a generic settings blob,
which would violate `json_ui_boundary` the moment the fields become
creator-editable (brief e).

**M1 — `summary_enabled` defaults TRUE.** The K-verbatim cap and scene tail
always apply above budget regardless of this flag; the flag alone gates the
sliding-summary recovery. Defaulting TRUE means every existing world gets
the full behavior with no explicit opt-in, while still letting Nia flip it
off per-world for a live A/B against the cap-only baseline (brief e).

**Named deferral D-0050 — config editing surface.** The `word_budget` /
`verbatim_turns` / `summary_enabled` fields are edited on the existing
prompts surface, beside the `conversation_summary` template row (N2, ticket
intake) — not a dedicated world-configuration surface, because none exists
yet. Migrate this editing to a dedicated surface once one exists; not
scoped to this ticket.

This step ships the table (`conversation_window_config`), the writer
(`writes.upsert_conversation_window_config`, upsert-one, no
`change_history` — metadata-config category), and the reader
(`conversation_window.load_conversation_window_config`, new module — G1,
`play.py` has no line budget left to grow) ONLY. No prompt-assembly change,
no creator UI, no trigger wiring — those are briefs (b)-(e).

## CONVERSATION WINDOW — K-verbatim cap + scene-tail re-injection implemented (BRIEF-0050-b, no schema change)

TICKET-0050. Implements D2 and H1 (intake), previously only decided:

**D2 — scene context re-injected as a compact tail, not only at the head.**
`context.assemble_scene_tail` (new function, same module as
`assemble_npc_context` — its semantic home) re-states location + one-line
setting + co-presence + player condition in <=~6 lines, appended as the
LAST message before the model's turn — never a second full
`assemble_npc_context`.

**H1 — message-list shape implemented exactly:** `[behaviour+context
system, summary note (unused, None, until brief d), *verbatim_K, scene
tail]`, built by `conversation_window.build_npc_message_list`. The
K-verbatim cap and scene tail apply on the `word_budget` condition ALONE —
never gated on `summary_enabled` (that flag only controls the brief-d
sliding-summary recovery layered on top; a degraded-but-bounded baseline
ships now, independently live-testable, and already beats the pre-0050
uncapped-history behavior).

Below `word_budget`, behavior is byte-for-byte unchanged (full history,
same system-prompt suffix mutations for `npc_reaction`/refusal). `play.py`
and `context.py` both had no line budget left (RECON-0050); the
config-read + scene-tail + message-list composition lives in
`conversation_window.resolve_npc_message_list`, the single call site
`cockpit/play.py::_say_npc_generation` uses — kept out of `play.py` itself
to hold both the file's 1000-line cap and `_say_npc_generation`'s
80-line cap.

## CONVERSATION SUMMARY — prompt-usage plumbing, no call site yet (BRIEF-0050-c, no schema change)

TICKET-0050. Ships the `conversation_summary` prompt usage's two halves
together (registry + seed), per the standing invariant that every seeded
usage carries a `PROMPT_REGISTRY` entry:

- `PROMPT_REGISTRY["conversation_summary"]`: `surface="play"`,
  `world_scoped=True`, `default_model=_author_model` (the authoring model,
  `llama3.1:8b` — this is a compression tool, not the game-dialogue model),
  `call_sites=("src/world_engine/conversation_window.py:_load_summary_template",)`
  naming the loader brief (d) adds.
- Seeded `prompt_template` row `pt-conversation-summary`, `world_id=None`,
  `model=NULL` (creator override resolved at read time via
  `effective_model`, same as every other usage), verbatim French compression
  system prompt, `user_template="{transcript}"`.

**C1 reaffirmed.** The summary this prompt produces is an ephemeral prompt
artifact (brief d wires the call); this step adds no call site and no
`proposed_mutation` path — the prompt is plumbing only, never a canon-write
vector.

## CONVERSATION SUMMARY — budget-trigger, recompute, fail-soft insertion (BRIEF-0050-d, no schema change)

TICKET-0050. Fills the summary slot briefs (a)-(c) left empty: when a
conversation is over `word_budget` AND `summary_enabled`,
`resolve_npc_message_list` (`conversation_window.py`) computes
`older, _recent = split_verbatim_tail(...)`, summarizes `older` via the
`conversation_summary` prompt, and inserts the result as a system note
right after the behaviour+context system message (H1 shape intact).

**F1 — recomputed on every over-budget turn, not cached.** C1 (ephemeral)
means no persisted summary artifact exists to invalidate; the accepted
cost is one extra LLM call per over-budget turn. Named deferral
**D-0050-cache** (a persisted summary cache) is explicitly NOT done —
future ticket if latency proves painful.

**Fail-soft, not fail-closed.** `summarize_older_turns` catches
`OllamaError` specifically, logs, and returns `""` -> `format_summary_note`
returns `None` -> no note, but the turn is NEVER aborted: the NPC still
answers on the cap-only baseline from brief (b). This is a prompt
enrichment, not a canon gate, so degrading gracefully is the correct
failure mode (unlike, say, `_apply_mutation`, where failure must be loud).

**Orthogonal to `analyze_window`.** The summarizer never touches
`conversation.last_analyzed_turn` and emits no `proposed_mutation` — it
reads persisted `ConversationMessage` rows and writes nothing, structurally
enforced (vacuous-proof) by `tooling/verify/checks/summary_not_persisted.py`.
Tier-4 mutation analysis and this ephemeral prompt-compression layer are
two independent consumers of the same history rows.

**Model resolution stays inline.** `ollama_client.chat(messages,
model=effective_model(template, _author_model()))` — the call is inline
(not a pre-bound local `model` variable) so `prompt_registry.py`'s static
AST wiring scan can verify it; `conversation_window.py` was added to that
check's `WIRED_FILES`.

## CONVERSATION WINDOW — config editing surface + replay measurement (BRIEF-0050-e, no schema change)

TICKET-0050, closing brief. Two independent halves:

**Editing surface (N2).** `GET`/`PATCH /api/conversation-window-config`
(`cockpit/crud/prompts.py`, co-located per N2) resolve/write the ACTIVE
world's row only — `_world_id(db)` is the same active-world accessor every
other creator-CRUD route uses. `GET` on a fresh world returns the in-memory
defaults object (1200/6/true) without creating a row; `PATCH` is a thin
wrapper over the existing `upsert_conversation_window_config` writer,
surfacing its `ValueError` (non-positive `word_budget`/`verbatim_turns`) as
422. The Prompts-tab panel ("Fenêtre de conversation") posts each field
individually — relational-only, no JSON blob (`json_ui_boundary` still
passes). **Named deferral D-0050 stays OPEN**: this rides the prompts
surface until a dedicated world-configuration surface exists.

**Replay measurement (mini-RECON finding).** No pre-existing monkeypatched-
Ollama *replay* harness was found reusable (the one precedent,
`prompt_model_write.py`, stubs `ping()` for a model-list check, not `chat()`
for a multi-turn dialogue) — `scripts/measure_conversation_window.py` is a
small, self-contained harness built on the real call path
(`conversation_window.build_npc_message_list` + `ollama_client.chat`)
against a real local Ollama model (no stub), replaying the seeded pilot
tavern scene (`char-player` vs `npc-maelis`) with a 10-line scripted
small-talk fixture.

**Finding: no differentiating signal.** Across all six (verbatim_turns,
word_budget) cells in {2,4,6}x{800,1200}, and both `repeat_last_n` values in
the K2 probe (256 vs 512), no near-duplicate NPC reply appeared over the
10-turn fixture (`difflib.SequenceMatcher` ratio never crossed 0.5). Per
Scope OUT ("absent a clear signal, leave them"), the script reports this
explicitly rather than fabricating a preferred pair, and changes NOTHING:
seeded defaults (word_budget=1200, verbatim_turns=6) and
`ollama_client.py`'s `repeat_last_n=256` are both untouched. Read as a
result, not a null test: even the smallest K (2) already prevented the
collapse on this scripted small-talk scene, which is consistent with the
K-verbatim cap doing its job (A2's anti-collision lever) — a longer or more
repetition-provoking fixture would be needed to actually locate the
saturation point TICKET-0050 originally described. Full table:
`tooling/recon/RECON-0050-window-measurement.result.md`.

## OBSERVED SCENE — socle and decision instrumentation (BRIEF-0051-a, schema v1.90)

TICKET-0051's first step: structure and write chokepoints only — no loop, no
model call, no UI. A loop that ran before the decision tables existed would
produce unmeasured runs that must be re-executed, so instrumentation is
folded into the socle rather than deferred.

**A3 (superseded A2).** Observed scenes get their OWN tables
(`observation_*`), never `conversation`. RECON found `Conversation.player_id`
`nullable=False` (`models/ephemeral.py:94`) with 49 read sites, several using
it as a DEFAULT identity (`analyzer.py:258`, `analyzer.py:275`) — making it
nullable would be disciplinary safety pushed onto 49 call sites, not a
structural change. `analyze_window`/`analyze_overhearing` are still reused,
by projecting beats into an in-memory transcript; no `conversation_message`
row is ever written by an observed run (A3-adapter).

**M1.** `observation_intent` deliberately carries NO `not_selected_reason`
column. A candidate can be excluded by cooldown AND by debt AND by
arbitration simultaneously; a single-valued reason would force a precedence
and destroy the rest of the information. The COMPONENTS
(`propensity`/`cooldown_active`/`debt_score`/`final_score`) are stored
instead, and the reason is DERIVED at read time by documented precedence
(`act=FALSE` -> no_intent; `cooldown_active` -> cooldown; `selected=FALSE,
debt_score<0` -> debt; otherwise -> lost_arbitration) — reconstructible, not
merely reported.

**M2.** `observation_beat.outcome` is explicit (`acted`/`silence`/
`degraded`/`event`), never inferred from `actor_id` being NULL. Conflating
`silence` (every candidate declined — a datum) with `degraded` (every intent
call failed — a bug) would let a JSON parse failure be misread as passivity,
the exact confound this ticket exists to measure.

**H2, closed vocabulary.** `player_presence` is `absent`/`silent`/`active`,
not a boolean — a SILENT player is still an AUDITOR for disclosure gating
(E2, BRIEF-0051-b) while an ABSENT one is not, unrepresentable with a
boolean. Only `absent` is implemented; `write_observation_run` raises
`ValueError` on `silent`/`active` rather than downgrading them silently.

**F3, structural isolation.** Observed runs will produce `proposed_mutation`
rows marked `proposed_by='observed_scene'` (constant `OBSERVED_PROPOSED_BY`,
`observation_writes.py`) — isolated from the creator-facing queue by
construction, not by a UI flag. `list_mutations`'s exclusion is NULL-safe
(`proposed_by.is_(None) | proposed_by != OBSERVED_PROPOSED_BY`) — a bare
`!=` would silently drop rows with a NULL `proposed_by`. Duplicate-detection
paths (`_find_applied_duplicate*`) are untouched: they must keep seeing
observed rows, or a re-run could double-propose. No producer exists yet in
this brief — the filter guards an empty set, fail-closed before the window
in which a run could pollute the queue ever opens.

**L, reduced to attribution.** Bit-exact replay is abandoned — the world
mutates under play (G1: runs execute against the live world DB, the pilot
world retired). What is KEPT is attribution: `observation_run_template` pins
each usage's template `id`+`version`, and `observation_run` pins
`cooldown_beats`/`debt_weight`/`propensity_mode` per run rather than reading
code constants, so two runs separated by a tuning pass stay comparable.
`seed` and a world fingerprint are dropped — a sensor whose verdict is
always "changed" does not inform.

**Named deferral D-J1.** An LLM judge scoring line novelty/quality is
deferred: putting a model inside the MEASUREMENT loop while isolating causes
adds a confounder. Reactivation condition: once J2's deterministic metrics
(BRIEF-0051-f) have shown their blind spots on passivity modes (b)/(c), not
before.

Five tables ship with no consumer yet — `latency_ms`/`raw_response` on
`observation_intent` are explicitly declared to have a DIFFERENT reader (run
feasibility and parse diagnosis) than the rest of the table (scene
analysis), so their absence of use in this brief is not an oversight.
`canon_write_policy.txt` gains a comment explaining the five tables' absence
from `[CANON_TABLES]` — never an entry in that section, which would
misdeclare telemetry as canon.

## OBSERVED SCENE — worst-case-listener disclosure floor (BRIEF-0051-b, no schema change)

**E2.** `assemble_npc_context` derived ONE relation intensity and fed it to
two different jobs: gating what the NPC may DISCLOSE, and colouring how it
PERCEIVES the person in front of it. With a single interlocutor the
conflation was harmless; with a plural audience (the normal case for
observed scenes) it was a leak — an NPC trusting the addressee would
disclose in front of an untrusted bystander standing right there.

The fix splits the single value into two: `inter_intensity` (interlocutor
relation, unchanged, still feeds perception) and `disclosure_intensity` (the
MINIMUM relation intensity across every auditor present — the addressee
plus a new `audience_ids` parameter — substituting `NEUTRAL_INTENSITY` where
no relation row exists). Only `disclosure_intensity` reaches
`_npc_context_speak`'s `share_threshold` gate.

**Why perception stays keyed on the addressee.** Perception is about manner
— how this NPC's tone reads to the person it is looking at — not about
which facts are safe to say. Flattening it to the audience floor would make
an NPC's warmth toward a trusted addressee visibly curdle merely because a
stranger walked into the room, which is a manner regression this brief does
not own.

**Why an empty `audience_ids` raises rather than defaulting.** `None` means
"single auditor, reproduces pre-v1.90 behaviour exactly" (the addressee is
always in the auditor set). An empty list is never "nobody is listening" —
it is a caller bug, and treating it as "disclose freely" is the exact
failure this brief exists to prevent, so `assemble_npc_context` raises
`ValueError` fail-closed instead.

**Scope.** All five existing call sites (`play_initiative.py`,
`play_physical.py`, `play.py`, `routes/prompts.py`, `routes/play.py`) keep
passing nothing, so `audience_ids` defaults to `None` everywhere today and
behaviour is bit-identical (asserted by
`tooling/verify/checks/context_disclosure_floor.py`, Rule 3). The first real
caller supplying a plural audience is BRIEF-0051-e's runner.
`player_presence='silent'` counting as an auditor (H2) remains a named
deferral — `_npc_context_company`'s player exclusion is untouched.

## OBSERVED SCENE — analyzer transcript seam (BRIEF-0051-c, no schema change)

**R1.** `analyze_window` and `analyze_overhearing` (`analyzer.py`) were
conversation-bound by signature AND internals — RECON found no
transcript-shaped seam to adapt to. Executing the brief surfaced that the
conversation binding ran deeper than the brief's own "expected to move" list
assumed: three escalations (recorded as AMENDMENT 01/02/03 against
BRIEF-0051-c) were needed before the seam's final shape was settled. Each is
recorded here because the reasoning, not just the outcome, is what a future
seam extraction should reuse.

**Escalation 1 — identity attribution.** `_normalize_to_schema`'s payload
builders read `conv.player_id`/`conv.npc_id` directly to attribute 5 of 8
mutation types (`new_knowledge`, `relation_change`, `event_creation`,
`resource_change`, `goal_change`). The brief's stated `analyze_transcript`
signature had no parameter for either. Resolution: a refusable
`AttributionContext(default_subject_id, default_counterparty_id)` — `None`
means no default is available, and an item that needs a missing default is
DROPPED and counted (`TranscriptAnalysis.dropped_unattributed` /
`.dropped_by_type`), never attributed by guess. A run-level default was
rejected outright: an observed run spans ~30 beats and 5 NPCs with no
run-level counterparty (beat 12 may be Maelis addressing Reike, beat 19
Senna addressing Maelis) — supplying one would let a fabricated
`relation_change` reach the queue looking legitimate. Fail-closed drops carry
real cost, stated up front rather than discovered later:
`_build_payload_event_creation` populates `involved_entities` from both
identities UNCONDITIONALLY (the model never supplies them explicitly), so an
observed run — both defaults `None` at the window-analysis level — will drop
EVERY `event_creation` proposal. This is correct (a 30-beat multi-NPC scene
has no single involved pair to invent), not a defect, and BRIEF-0051-e must
read a 100% `event_creation` drop rate as expected, not as evidence of a
passive scene.

**Distinguishing this from the `tick_normalize.py:757` precedent.** That
precedent — world-tick proposals use a wholly separate normalizer rather
than reusing `analyzer._normalize_to_schema` — is real and was respected,
not overridden. It applies when the PROPOSAL VOCABULARY differs (the tick's
closed contract is `goal_change | relation_change | new_knowledge | npc_move
| agenda_step_change | agenda_creation`, entity-scoped, not
conversation-scoped at all). Observation and the played path share the SAME
vocabulary and the same judge; only the participant topology differs. Making
the identity model an explicit, refusable input is not force-generalizing
across a vocabulary boundary — it is removing an implicit conversation read
from a judge that was already vocabulary-compatible.

**Escalation 2 — `payload["source"]` duplicated `conversation_id`.**
`_overhearing_mutation_for_receiver` embedded `conversation_id` a second
time inside a payload string (`f"overheard:{conversation_id}:{speaker_id}"`)
in addition to setting the `ProposedMutation.conversation_id` column. Ruling:
this was not "a minor content drift accepted because nothing reads it" — it
was a duplicated provenance record. The column is the structural copy; the
wrapper (`analyzer.py`) populates it (also newly true for the window path's
`_window_build_mutations`, a symmetric gap the census caught). The string
copy is redundant once the column is guaranteed populated, and
`speaker_id` — transcript-local, no column of its own — stays.
`payload["source"]` reads `f"overheard:{speaker_id}"` for rows written from
schema v1.90 onward; rows written before keep the pre-BRIEF-0051-c
`f"overheard:{conversation_id}:{speaker_id}"` format (history is
append-only, never migrated — see `world-engine-schema.md`).
`tooling/verify/checks/analyzer_seam.py` Rule 9 confirms by AST that no
dedup/lookup path anywhere in `src/` ever read the dropped segment — the
only reader was the verbatim apply-time passthrough into
`Knowledge.source` (`cockpit/mutations.py`), a data copy, not a decision.

**Recorded, not acted on — provenance-as-structure candidate.**
`proposed_mutation` now carries provenance four different ways:
`proposed_by` (column), `conversation_id` (column),
`observation_mutation_link` (table, BRIEF-0051-a), and `payload["source"]`
(a formatted string inside a JSON blob) — the same category of defect as
JSON-backed UI-visible data, provenance as ad hoc content instead of
structure. The clean fix (a dedicated provenance column/table, payloads
carrying only the semantic change) touches a canon table, the mutation
application path, the Review Queue, and existing history — larger than
TICKET-0051. Named here as a future ticket candidate; not begun, not
partially prepared for.

**Escalation 3 — mandatory coupling census.** Two couplings surfaced
mid-flight, each after the previous one was declared resolved — evidence,
not noise, that amending per-discovery was producing exactly the irregular
design this ticket exists to avoid. A full report-only census of every
`Conversation` attribute read, every conversation-derived value written into
a `ProposedMutation`, and every conversation_id/gathering_id-keyed query in
`analyzer.py` (A=15 transcript-local, B=3 already-columnar, C=6 genuine
identity defaults, D=7 irreducibly conversation-bound, zero transitive
coupling in `writes/`/`prompt_store`) settled the seam once, against the
complete picture, rather than trickling out further amendments. Two
classifications were corrected during that settlement: `location_name`
(`conv.location_id` → `Entity.name`, used in overhearing rationale text) is
Class A, not Class D — location is a property of the SCENE, not the
conversation (an `observation_run` carries `location_id` natively too), so
`analyze_overheard_lines` gained a `location_id` parameter the module
resolves itself; and `_window_build_transcript` was kept in `analyzer.py`
rather than moved, since `analyze_transcript` takes an already-built
`transcript: str` — transcript CONSTRUCTION is the caller's job, which keeps
`ConversationMessage` out of the seam module entirely rather than
introducing an intermediate line type that exists only to launder a type.
The exact transcript format (one line per turn, `"\n"`-joined,
`f"[{'JOUEUR'|'PNJ'}] {content}"`) is documented as a contract in
`analyzer_transcript.py`'s module docstring, since two callers now produce
it independently (BRIEF-0051-e's observed-run caller will be the second).

**D-0051-c-1 (sharpened).** Observed-transcript participant attribution: with
both `AttributionContext` fields `None`, an observed run's proposal yield
depends entirely on whether the analysis prompt names its participants
explicitly per line. `dropped_by_type` on the first observed run is the
first real measurement — `event_creation` is predicted at 100%. If other
types are also high, the fix is teaching `pt-conversation-analysis` (left
untouched by this brief) to name speaker/addressee per line, never
reintroducing a run-level default, never relaxing the fail-closed rule.

**Verification.** `tooling/verify/checks/analyzer_seam.py`: no
`Conversation`/`ConversationMessage` coupling in `analyzer_transcript.py`
(AST, narrow exception only for `payload["npc_id"]`-shaped string subscript
keys — string literals used as candidate JSON key names, e.g. inside
`_first_of(item, ..., "npc_id", ...)`, are correctly not flagged, since only
true Python identifiers are scanned); no `.commit()` in the seam module;
`analyze_window`/`analyze_overhearing` signatures unchanged; both modules
within 40 functions / 1000 lines (`analyzer_transcript.py` 906 lines,
`analyzer.py` 307 lines, at landing); fail-closed attribution demonstrated
on both the window
(`relation_change`) and overhearing (player-spoken with no player) paths;
`conversation_id` non-null on every mutation both wrappers return; no
dedup/lookup reader of `payload["source"]` outside the sanctioned
passthrough. A before/after regression capture against the test DB (fixed,
stubbed model output — live local-model sampling is not deterministic, so a
live-model diff would be noise, not signal) produced an empty diff for both
`analyze_window` and `analyze_overhearing` except for the one authorized
`payload["source"]` format change.

## OBSERVED SCENE — intent and arbitration engine (BRIEF-0051-d, no schema change)

**C3, model proposes / code judges.** One short JSON intent call PER present
NPC per beat (`{act, urgency, target, why}`), never a single MJ call that
picks an actor. The model answers ONLY for itself — never ranks, never sees
a rival's intent, never told one NPC acts per beat. `observation_engine.py`
ships two pure responsibilities: `request_intent` (one model call) and
`arbitrate` (pure, no I/O, no model) — kept in separate functions so
arbitration is independently testable with a hand-built `intents` list.

**D1/O1, propensity moves from prompt to code.** `scripts/seed_pilot.py`'s
`MJ_INITIATIVE_SYSTEM_PROMPT` (the PLAYED path, untouched by this brief)
hard-codes a U-curve: "intensité < 40" and "intensité > 70" both raise the
odds of taking initiative, so an NPC at 20 or at 85 always outranks one at
50, invisibly and unadjustably. `pt-observation-intent`'s system prompt
carries NO intensity threshold of any kind (asserted by
`grep -n "40\|70\|intensit"` returning nothing against its body) — the
model is never told relation magnitude matters. `arbitrate`'s
`propensity_mode='flat'` (the DEFAULT) sets `propensity=1.0` for every
candidate regardless of relation intensity; `'relation_weighted'` exists as
the non-default second mode
(`1.0 + 0.5 * (abs(intensity_toward_last_actor - 50) / 50)`, capped at a
1.5× multiplier — k=0.5 is exactly that cap, since the intensity term
already ranges [0, 1]). O1's rationale for shipping `flat` as default rather
than damping the curve immediately: damping before measuring would leave
cooldown, debt, and the curve itself indistinguishable as causes of any
observed passivity — the A/B run (flat vs relation_weighted, same scene)
is what decides, not a code default masquerading as the fix.

**Signature gap, resolved additively.** The brief's `arbitrate` signature
has no field carrying "how long ago did `last_actor_id` last act" or "this
candidate's relation intensity toward `last_actor_id`" — both are required
by D2's and O1's own rule text but have nowhere else to live given
`IntentResult` is fixed to the model call's own output shape
(`act`/`urgency`/`target_id`/`why`/`call_status`/`latency_ms`/
`raw_response`). Resolved by adding two keyword-only parameters with
defaults that reproduce the documented/tested behavior when omitted:
`beats_since_last_act: int = 1` (D2's cooldown rule, `beats_since_last_act
< cooldown_beats`, is then exactly the single-beat-ago case the Done-means
criteria exercise) and `relation_intensities: dict[str, int] | None = None`
(missing entries default to neutral 50, so an un-supplied map degrades
`relation_weighted` to `flat`'s propensity=1.0 rather than raising). Neither
changes `flat` mode's behavior, and both are additive to the brief's given
positional signature — not a design decision, a plumbing completion.

**D2, cooldown is a soft floor.** `cooldown_active = (npc_id ==
last_actor_id and beats_since_last_act < cooldown_beats)`. A cooling
candidate is excluded from the selection pool UNLESS every other candidate
declined (`act=False`), in which case it may still be selected —
`cooldown_active` stays `True` on that row regardless. `_observation_select`
implements this as two ranked pools (non-cooling acting candidates first,
falling back to the cooling one only when the first pool is empty), never a
hard drop — a hard drop would let a single-candidate beat report a false
`silence`.

**D3, speaking debt.** `debt_score = debt_weight * (expected_share -
actual_share)` where `expected_share = beats_elapsed / len(npc_ids)` and
`actual_share = acted_counts[npc_id]`; positive means under-served. Folded
into `final_score = urgency * propensity + debt_score` alongside D1's
propensity — one linear score, no separate debt-vs-urgency tie-break stage.

**D4, explicitly not taken.** No RNG anywhere in `observation_engine.py`
(`grep -rn "random\|shuffle\|choice"` returns nothing). Ties break on lowest
`acted_counts`, then stable `npc_ids` order — deterministic given the same
inputs, so a re-run of the same intents/scores always selects the same
candidate.

**Parse-error vs decline, the defect this ticket exists to fix.**
`play_initiative.py:508-510` (`_initiative_vote_call`) wraps its model call
in a bare `except Exception`, collapsing a JSON parse failure, a network
timeout, and a genuine model decline into the same `(False, None)` return —
unobservable which one occurred. `request_intent` distinguishes all three by
construction: `llm_parse.extract_object` (raises `LlmParseError`, unlike
`extract_object_or_none` which swallows the distinction) drives
`call_status='parse_error'`; `ollama_client.OllamaError.__cause__` is
inspected for `TimeoutError` to set `'timeout'` vs `'error'` (`chat()`
collapses every network failure into `OllamaError` — the cause chain,
preserved by its own `raise ... from exc`, is the only place the original
exception type survives); a well-formed `{"act": false}` sets `call_status
='ok'`. Every path returns an `IntentResult` — never raises past
`request_intent` — so a beat runner (BRIEF-0051-e) always gets a row to
persist, matching `observation_intent`'s "always written" contract
(BRIEF-0051-a).

**Model never resolves ids.** The intent prompt shows each NPC the exact
name roster of everyone else present; `target` in the model's JSON reply is
a name, resolved to an entity id in code
(`_observation_resolve_target`, exact case-insensitive match) — an
unresolved or empty name is `None`, never guessed, never passed through as
a string.

**Disclosure floor reuse.** `request_intent` calls `assemble_npc_context`
with the full `audience_ids` list from BRIEF-0051-b — one member is
designated `interlocutor_id` to satisfy the existing required-positional
parameter, the rest passed as `audience_ids`; `context.py`'s
`_disclosure_intensity_floor` unions them back into one set before computing
the floor, so which member plays which role has no effect on disclosure —
it only picks who the cosmetic "how you see X" section describes.

**Finding, not fixed here.** `pt-npc-initiative-act`'s `move` field
instruction ("te lèves physiquement pour rejoindre le groupe DU JOUEUR")
reads incorrectly in an observed scene: there is no player group to join
when `player_presence='absent'`. Per this brief's Scope OUT
(`play_initiative.py` untouched), this is reported, not edited — a
consumer of the reused act template (BRIEF-0051-e or later) must either
substitute a scene-appropriate instruction fragment or accept `move` as
always-false-in-practice for observed beats.

**Incidental fix.** `prompt_registry.py`'s `conversation_analysis` and
`overhearing_classification` entries still pointed their `call_sites` at
`analyzer.py:load_analysis_prompt`, stale since BRIEF-0051-c relocated the
function to `analyzer_transcript.py` (the def moved; `analyzer.py` only
imports the name now). Corrected as part of restoring a green full-tree
`prompt_registry.py` check — unrelated to this brief's own feature work,
found only because that check now runs `observation_intent`'s bijection
alongside it.

---

## OBSERVED SCENE — runner: bounded run, readiness gate, F3 proposals (BRIEF-0051-e, no schema change)

**B2 + B1, bounded run over real-time streaming.** `run_one_beat(run_id, db)`
executes exactly one beat; `run_bounded(run_id, db)` loops it until a stop
condition — one implementation, two entry points, matching the ticket's
decision text verbatim. B3 (real-time streaming) was never a candidate here:
the transcript is read cold, after the fact, by both the beat loop itself
(`_intent_transcript`) and by F3's post-close analysis
(`_analysis_transcript`); no SSE, no partial-line delivery. The mini-RECON's
process-model finding (item 7) is why `start` is a separate route from
`step`: a 30-beat/5-NPC run is ~150 model calls, too long for one
synchronous HTTP request, so there is no "run to completion" HTTP route —
`cockpit/routes/observation.py` exposes exactly the four routes the brief
names (start / step / stop / inject-event); `run_bounded` stays a
Python-level entry point for scripts and the verify check, called
step-by-step by whatever drives the four routes (a future cockpit UI,
BRIEF-0051-f, or a script).

**Readiness gate, verbatim rationale (fail-closed, pre-write).**
`check_run_readiness` carries this rationale in its docstring, unedited:

> The gate exists because a flat scene has two very different causes: a
> passive initiative system (what this ticket measures) and an
> under-populated world (what it does not). Without the gate the first
> finding of every run risks being misattributed to the engine. Refusing
> loudly costs one message; a misattributed conclusion costs a redesign.

The gate's five conditions (>=2 NPCs present, every present NPC has an
active goal, every present NPC has a describable name+description, the
location exists and belongs to the world, `player_presence == 'absent'`) are
checked before any write; a non-empty failure list means zero
`observation_run` rows (verify Rule 4). The brief's documented signature
(`check_run_readiness(location_id, npc_ids, db)`) omits two identities two
of its own five conditions cannot be checked without — `world_id` (for "the
location belongs to the world") and `player_presence` (for the H2
condition). Both were added as required keyword-only parameters, following
BRIEF-0051-d's own precedent (`arbitrate`'s `beats_since_last_act` /
`relation_intensities`) for completing an underspecified signature
additively rather than guessing a workaround.

**Roster is re-derived, never snapshotted.** `observation_run` carries no
participant column. "Present NPCs" is recomputed at every beat from
`Character.current_location_id == run.location_id` (mirrors
`gathering.py`'s `_present_npcs`), not captured once at start. This ticket
adds no NPC-movement mechanism, so the set is expected to be stable across a
run; G1's "runs execute against the live world DB" accepts the consequence
that an external edit to an NPC's location mid-run changes who gets the next
beat's opportunity. Mini-RECON item 4 (gathering roster) concluded a run
neither creates nor attaches to a `gathering` — presence is a physical-
location fact, not gathering membership, so the B1 per-NPC-one-gathering
invariant is never touched by this brief.

**Three-way outcome, why `degraded` must not collapse into `silence`.**
`_beat_outcome` is three explicit `return` statements — `selected_npc_id is
not None` -> `'acted'`; `any(call_status == 'ok')` -> `'silence'`; else
`'degraded'` — never a truthiness ternary on `actor_id` (verify Rule 2,
AST-enforced). This is the ticket's central measurement claim in code form:
a scene where every NPC's intent call timed out must never read as "the NPCs
chose not to act" (a datum about the initiative system) when it is actually
"the model was unreachable" (a bug/ops signal). Verify Rule 3 forces every
intent call to fail and asserts `outcome == 'degraded'` with a full,
non-empty `observation_intent` row set — the mechanical form of this claim.

**K2, event injection.** `inject_event` writes one `observation_beat`
(`outcome='event'`, `actor_id=None`) directly via `write_observation_beat`
— no intent rows, no beat-allowance consumption (`_regular_beat_count`
excludes `outcome='event'`; `_consecutive_non_acted` skips event rows
entirely rather than resetting or counting them, since an injected event is
creator narration, not an NPC declining to act). The mechanism is exactly
"it becomes part of the transcript every subsequent NPC reads":
`_intent_transcript` includes every beat with a non-null `line`, event or
acted, in `beat_index` order.

**Template pinning stays attribution, not a replay lock (L, reduced).**
`_pin_templates` resolves and records each usage's `(template_id,
version_number)` ONCE, at `start_run`, into `observation_run_template` — but
every beat re-resolves the head template by usage and calls `current_prompt`
for its latest text, exactly like BRIEF-0051-d's `request_intent`. This
matches the ticket's L decision: bit-exact replay is abandoned (the world
mutates under play), so pinning exists to make two runs comparable
(“what was active when this run began”), not to lock beat 17 to the exact
text beat 1 saw if a creator edits the template mid-run.

**F3, once per run, after close — and its overhearing sub-pass.**
`produce_run_proposals` is never called from the beat loop; it runs exactly
once, from `_produce_proposals_quietly`, itself called from every path that
reaches a terminal `close_observation_run` (`_apply_stop_conditions`'s
max_beats/quiescence branches, `stop_run`'s creator_stop, and
`_run_beat_safely`'s exception handler before it re-raises) — "after the run
closes" is enforced structurally, not by caller discipline. A parse failure
in the window pass is caught and logged, never allowed to undo the run's
already-terminal status (`_produce_proposals_quietly` swallows any
exception).

The window sub-pass (`analyze_transcript`) runs once over the whole run,
using the seam's frozen `[PNJ]`/`[JOUEUR]` transcript contract with every
line labeled `[PNJ]` (no player exists) and `AttributionContext(None,
None)` — R1's documented shape for a multi-NPC scene with no run-level
counterparty. Event beats get a third label, `[ÉVÉNEMENT]`, not in the
seam's frozen two-way contract: they are creator narration, not something a
PNJ said, and excluding them entirely would drop causally relevant context
(e.g. an injected fire that later motivates a `status_change`).

The overhearing sub-pass (`analyze_overheard_lines`) is called once PER
ACTED BEAT, not once for the whole run and not once per beat of the live
loop — resolved this way after finding that `analyze_overheard_lines`'
identity contract can only resolve a speaker via a SINGLE
`AttributionContext.default_subject_id`, which a 30-beat/multi-NPC run has
no run-level value for (beat 12's speaker and beat 19's speaker are
different NPCs). Per-acted-beat scoping sidesteps this cleanly: each call's
`AttributionContext(default_subject_id=beat.actor_id,
default_counterparty_id=None)` is unambiguous, because the beat's actor IS
that call's speaker by construction — never a guess, never a cross-beat
default. `receiver_ids` is "every present NPC except the speaker" per the
brief's own wording, with no player subtraction (H2 — there is no player).
`speaker_line`/`listener_line` both receive the beat's own line (there is no
distinct "reply" within a single-line beat, unlike a played turn's
player-line/npc-reply pair) — a degenerate but safe input: even a
misclassified `"speaker":"player"` from the model drops silently
(`default_counterparty_id=None`), never misattributes. The brief's "once per
run, not per beat" sentence is read as bounding the ANALYSIS PHASE to a
single post-close pass (never interleaved into the live 30-beat loop, which
is the multiplication it warns against) rather than bounding the sub-pass to
exactly one call — a per-beat live analysis would have been the actual
30x-multiplication the brief rejects; a per-acted-beat pass inside one
already-single post-close phase is not.

**F3 isolation.** Every mutation `analyze_transcript`/
`analyze_overheard_lines` returns is retagged `proposed_by =
OBSERVED_PROPOSED_BY` before persisting (overwriting the seam's own
`local_ai_window`/`local_ai_overhearing` default) and linked via one
`observation_mutation_link` row — the sole write authority for that tag and
that join stays `observation_writes.py` (`link_observation_mutation`);
`produce_run_proposals` never touches a canon table directly beyond the
`ProposedMutation` insert itself, which is the same non-canon staging write
`analyzer.py`'s window pass already performs today.

**New template, `observation_narration` (mj_narration, off by default).**
The brief names `pt-npc-initiative-act` for the line (step 5) but names no
template for the optional MJ-narration call (step 7). Reusing the existing
`player_narration` template verbatim was rejected: its user template's
fixed prose ("Le joueur dit : {player_line}") is not a placeholder
substitution problem, it is baked-in text asserting a player exists, which
is false for every observed run by construction (`player_presence`
implemented value is only `'absent'`). A new usage,
`observation_narration` (`pt-observation-narration`, seeded in
`scripts/seed_pilot.py`, registered in `prompt_registry.py`), was authored
instead — same pattern BRIEF-0051-d used for `observation_intent` (a new
model-facing prompt seeded alongside the code that calls it). Off by
default (H2/ticket text); a run with `mj_narration=False` never resolves or
calls this template at all — `_generate_mj_narration` is only reached when
`run.mj_narration` is true AND a beat's `outcome == 'acted'`.

**`move` finding from BRIEF-0051-d, resolved by omission.** -d flagged that
`pt-npc-initiative-act`'s `move` field ("rejoindre le groupe DU JOUEUR")
reads incorrectly with no player. `_generate_act_line` parses `act_text`
only and never reads `move` — this ticket adds no NPC-movement mechanism for
observed scenes, so the field is simply never consumed; the prompt's
mis-worded instruction is inert here rather than fixed (fixing the shared
template's wording is out of scope — `play_initiative.py` is untouched by
this ticket).

**`_run_beat_safely`, the exception safety net.** A run must never be left
`status='running'` after the process returns "by any path" (verify Rule 7).
`run_one_beat` itself stays a pure "execute exactly one beat" primitive with
no exception handling; `_run_beat_safely` wraps it, closes the run
`failed`/`'error'` on ANY exception (best-effort — a `ValueError` from
`close_observation_run` on an already-terminal run is swallowed so the
original exception is never masked), fires `_produce_proposals_quietly` over
whatever transcript exists, then re-raises. Both `step_run` (single manual
step) and `run_bounded`'s loop call this same wrapper — the safety net is
identical whether a creator steps one beat at a time or lets a script run to
completion.

---

## OBSERVED SCENE — cockpit surface: top-level mode-tab, F3 read-only visibility (BRIEF-0051-f, no schema change)

**P1, corrected: a mode-tab, never a Creation sub-tab.** The intake
conversation described P1 as "a top-level tab in `TAB_KEYS`" — RECON showed
that reading was wrong. `TAB_KEYS`/`CREATION_TABS`
(`tooling/verify/checks/page_contract.py`, `index.html`) govern the
**Creation** entity-CRUD sub-surfaces, each requiring a `primaryAction` and
rendered through `showCreationSubTab`'s generic dispatcher. Observation is
not an entity-CRUD surface and creates no entities. The decision itself (a
top-level surface, sibling of Jouer and Création, not a sub-surface of Play,
not a separate port) is unchanged — only the registry it lands in is
corrected: a third `mode-tab` button (`#mode-tab-observation`, alongside the
existing `#mode-tab-play`/`#mode-tab-creation`) calling
`showObservationView()`, which mirrors `showPlayView()`/`showCreationView()`'s
exact contract (show/hide the three top-level `.app-view` divs, toggle the
three mode-tab buttons' `active` class, lazy-init once via an
`obsInitialized` guard). `TAB_KEYS` and `CREATION_TABS` carry zero
`observation` entry — asserted both directions by
`tooling/verify/checks/observation_surface.py` (Rule 2).

**Reads get their own chokepoint, mirroring writes.** `observation_socle.py`
(BRIEF-0051-a) restricts the five `Observation*` model identifiers to a
declared module allowlist — a rule written for writes, but its shape
(model identifiers confined to named modules) applies just as well to reads.
Rather than adding `cockpit/routes/observation.py` to that allowlist and
letting route handlers touch `Observation*` classes directly, this brief
ships `src/world_engine/observation_reads.py` — the read-side twin of
`observation_writes.py` — and adds ONLY that one module to the allowlist.
`cockpit/routes/observation.py` calls `observation_reads.list_runs` /
`get_run_detail` / `get_run_proposals` / `list_present_npcs` and never
references an `Observation*` class itself; `observation_surface.py`'s Rule 6
asserts this by AST (zero `Observation*` `Name` references, zero `db.add(...)`
calls in the routes module) — every write still reaches canon only through
`observation_runner.py`.

**`not_selected_reason` derivation lives in the reader, not the renderer.**
`observation_reads.derive_not_selected_reason` implements the precedence
documented in `world-engine-schema.md`'s `observation_intent` NOTE (M1:
`act=False -> no_intent`, `cooldown_active -> cooldown`,
`debt_score < 0 -> debt`, else `lost_arbitration`) once, server-side, and
ships it as a `not_selected_reason` KEY in the JSON response — never a stored
column. The transcript renderer labels it "raison (dérivée)" so a creator
never mistakes a computed value for a persisted one.

**Outcome visual distinction is a verified CSS claim, not a convention.**
`.b-acted`/`.b-silence`/`.b-degraded`/`.b-event` are four badge classes with
deliberately distant colors (green / muted-grey / red / purple) rather than
shades of one hue — `degraded` must never look like `silence` at a glance,
since that visual read IS the ticket's central measurement claim (a datum
about passivity vs. a bug in the model call) in surface form.
`observation_surface.py`'s Rule 3 asserts `.b-silence` and `.b-degraded`
resolve to textually DIFFERENT class bodies, not merely that both class names
exist somewhere in the stylesheet.

**Run detail is the reader for the L columns.** `_obsRenderRunDetail`
displays every pinned arbitration parameter (`cooldown_beats`, `debt_weight`,
`propensity_mode`, `mj_narration`, `model`) and, per `observation_run_template`
row, the usage/template_id/version triple — the one surface making two runs
comparable, per L's reduced form (attribution, not replay). Each pinned
template links into the existing Prompts tab (`observationOpenPrompt`:
`showCreationView(); showCreationSubTab('prompts'); promptsLoadList().then(...
promptsSelectDetail(templateId))`) rather than duplicating its editor —
Scope OUT is explicit that this brief never edits a template.

**F3 proposals: read-only, reached only through the link table.** The
Observation surface's proposals region calls
`GET /api/observation/runs/{id}/proposals`, which reads
`observation_mutation_link` and never `/api/mutations` — isolation proven the
same way BRIEF-0051-a proved it (a NULL-safe exclusion on the queue side),
now with a positive reader on the other side so isolation is not invisibility.
No approve/reject control exists here; whether an observed proposal should
ever be promotable to canon is logged as an OPEN QUESTION, not answered by
this brief.

**Verified live (test world, real Ollama call).** A 2-NPC run against a
minimal test-world location produced a genuine `silence` beat (both
candidates' `observation_intent` rows carrying `call_status='ok'`,
`act=False`) rendered with the correct badge and derived
`not_selected_reason='no_intent'` on both candidates; the readiness gate's
per-condition refusal (missing description/goal) rendered as named,
itemized failures rather than a generic error, confirming the direct-`fetch`
path used for `start_run` (bypassing the shared `api()` helper's lossy
`Error(data.detail)` coercion) correctly surfaces a `{failures: [...]}` 422
body.

---

## OBSERVED SCENE — run metrics: deterministic instruments, J2 (BRIEF-0051-g, no schema change)

**J2, enforced by AST, not by convention.** `scripts/observation_metrics.py`
is read-only (opens the DB, computes, prints — no table, no cache, no
column) and imports no local-model client. `tooling/verify/checks/
observation_metrics.py`'s Rule 1 (no session-shaped `.add`/`.commit`/
`.flush`/`.delete` call) and Rule 2 (no local-model-client import) make both
claims mechanical rather than a docstring promise. D-J1, the LLM novelty
judge, stays a named deferral: putting a model inside the measurement loop
while isolating causes (this ticket's whole point) would add a confounder —
reactivated once this tool has shown its blind spots on failure modes (b)
and (c) below, not before.

**Three failure modes, three distinguishing metrics.** A flat scene can be
any one of these, and conflating them would misattribute the finding to the
wrong fix:

| Mode | Signature | Points at |
|---|---|---|
| (a) nobody wants to act | low intent rate (metric 3) | propensity/intent prompt |
| (b) all want, nothing happens | high intent (3), low proposal yield (9) | dialogue prompt |
| (c) they loop | high n-gram overlap (metric 8) | context/scene memory |

Metric 6 (degraded rate) is reported separately and FIRST, before any other
figure: a non-zero degraded rate means the intent calls themselves failed —
a technical fault, not a datum about passivity — and every other metric on
that run is suspect until it reads zero. `_print_human` prints the
suspect-run warning before the Participation section, never after.

**Entropy is normalised against the full present roster, not the support of
NPCs who acted.** A single NPC capturing every beat is a degenerate
distribution with entropy exactly 0 (well-defined), not an "undefined"
value — the earlier draft normalised by `log2(len(shares))`, which returns
`None` on a captured run (only one non-zero entry) instead of the near-0
value the brief's Done-means demands. The fix: `normalized_entropy` divides
by `log2(len(npc_ids))` — the full roster size — and sums `p*log2(p)` only
over non-zero shares (the zero-share terms contribute 0 by the standard
convention). `None` is now reserved for the genuinely undefined case: fewer
than 2 present NPCs.

**Spearman, not Pearson, and no scipy dependency.** With 5 NPCs the
intensity/act-rate relationship is ordinal at best; a linear coefficient
would overstate what the data supports. `spearman()` is implemented
directly (average-rank ties, then Pearson over the ranks) rather than
importing `scipy.stats.spearmanr` — CLAUDE.md: no new dependency without a
decision, and `requirements.txt` carries neither `scipy` nor `numpy`. The
coefficient is always printed WITH `n`, and the human output states plainly
that `n=5` supports a direction, not a conclusion — the honesty is in the
output, not just the docstring.

**Per-NPC intensity has no run-level "reference" NPC — mean pairwise
intensity is the documented substitute.** `relation` is pairwise; the
ticket's originating hypothesis ("un personnage avec une intensité très
faible ou très forte...") treats intensity as a per-character scalar, which
a pairwise table does not directly carry. `_mean_pairwise_intensity`
resolves this to the NPC's MEAN `relation.intensity` across every OTHER
present NPC in the run — a documented choice, not a schema change: no
snapshot column is added (mini-RECON item 2 confirmed `relation.intensity`
carries no per-beat snapshot and a creator approving a proposal between the
run and the metrics pass would shift the read; the interpretation guard
states this precondition before any figure, rather than silently reporting
a number that may already describe a different world state). The scan
excludes `type='connects_to'` — location topology, never a social signal
(the CLAUDE.md invariant on `connects_to` applies to every world-wide
relation scan, and this is one).

**`not_selected_reason` has exactly one implementation, and so does the
reader chokepoint.** The script imports
`observation_reads.derive_not_selected_reason` (BRIEF-0051-f) rather than
re-deriving the precedence — Rule 5 asserts the import exists, which is a
stronger guarantee than comparing two independently-written functions for
textual agreement: there is only one function to drift. The same module
gained five raw ORM accessors this brief (`get_run`/`list_beats`/
`list_intents`/`list_run_templates`/`list_mutation_links`, alongside -f's
JSON-shaped `list_runs`/`get_run_detail`/`get_run_proposals`) so that
`scripts/observation_metrics.py` computes over real rows without ever
naming an `Observation*` class itself — caught by `observation_socle.py`'s
existing model-identifier allowlist (unchanged in shape since -a; this
brief adds only the check file, `observation_metrics.py` itself needs no
entry because it imports `observation_reads` functions, not the classes).

**n-gram overlap: fixed n=4, window=5, containment not Jaccard.** Overlap of
a line's n-grams against a PRIOR beat is `|current ∩ prior| / |current|`
(containment, asked "how much of THIS line already existed"), maximised over
the preceding `NGRAM_WINDOW` lined beats, then averaged across the run for
the summary figure — reported per-beat AND as a run mean, per the brief.
Event beats participate as lined beats (their text enters the window) since
an injected event is part of what an NPC's line could be echoing.

**Latency's different reader, honoured.** `observation_intent.latency_ms`
is deliberately NOT mixed into the narrative metrics (participation/intent/
health) — it is reported under "Evolution / feasibility" alongside proposal
counts, the ticket's own declared reader for that column (does a 5-NPC/
30-beat run stay tractable, not a scene-analysis question).

---

## OBSERVATION CONTEXT WINDOW PARITY (BRIEF-0052-a, BRIEF-0052-b, BRIEF-0052-c, no schema change)

**B1/I2: a lane-neutral seam, forced by an existing docstring's own
admission.** `conversation_window.py`'s primitives operated on `list[dict]`
ollama messages, and `_render_older_transcript` labelled by `role` alone
with a docstring stating the list "carries no per-NPC name" — true for the
played lane (one player, one NPC voice) but false for the observed lane
(several named NPCs, no player). Rather than have the observed lane import a
conversation-named module, or duplicate the cap/summary logic under an
`observation_` name, the module is renamed to `context_window.py` and its
primitives moved onto a new `TurnLine(role, label, content)` dataclass:
`label` carries the full literal prefix — separator included — so
`render_transcript` renders any lane's lines byte-for-byte through one
function. The played lane's public entry points (`build_npc_message_list`,
`resolve_npc_message_list`) keep their exact `list[dict]` signatures and
convert internally (`_played_to_lines`/`_lines_to_played`); the round-trip
is asserted by `observation_window_parity.py`'s fixture check, not merely a
docstring claim.

**C1 + E1: one config row, word budget only, and an accepted dormancy.**
`conversation_window_config` stays a single per-world row serving both
lanes — no lane-specific column, no composite `OR beats > K` trigger. The
observed lane's beats are short by design
(`_NPC_INITIATIVE_ACT_FALLBACK` caps an act at "1 à 2 phrases", ~25-35
words), so a default 30-beat run stays close to but under the 1200-word
default budget — the compression branch is dormant there by design, not by
oversight. Live measurement against a real production run (beat-by-beat
cumulative word count of `_intent_transcript`) showed ~31 words at beat 0
growing to ~812 by beat 19 (~41 words/beat average) — close enough to the
1200 budget that a full 30-beat run sits near the edge, not comfortably
under it; fidelity when the branch DOES fire, not how often it fires, was
the stated objective (E1).

**G2 coupled to J1: per-NPC resolution, because the scene tail cannot be
shared.** `assemble_scene_tail` produces a result for ONE viewer (it embeds
that NPC's own co-presence framing); a shared, beat-level transcript
resolution could not feed it correctly for more than one NPC.
`observation_window.beats_to_lines` therefore projects prior beats onto
`TurnLine` from ONE NPC's point of view per call (`role='assistant'` for
the viewer's own lines, `'user'` for everyone else's — currently unread
under K2, populated for the deferred K1 shape-parity work), and
`resolve_observation_transcript` is called once per present NPC per beat
inside `run_one_beat`'s intent loop — accepted cost: N summary calls on an
over-budget beat, verified live at N=3 for a 3-NPC location
(`conversation_summary` call count captured during BRIEF-0052-c's live
gate).

**H1: the observed MJ narration deliberately keeps the raw transcript,
because the played MJ has no history to mirror.**
`_say_stream_mj_narration` (`play_stream.py:51-54`) sends the played MJ
narrator exactly `[system, one user message]` — no window, no summary, no
scene tail, ever. There is therefore no MJ window in the played lane to
extend to the observed lane; `_generate_mj_narration` keeps calling
`_intent_transcript` (full, unwindowed) rather than
`resolve_observation_transcript`. What was a comment before this brief
(`observation_runner.py`) is now `observation_window_parity.py`'s Rule 4: a
structural, vacuous-proof assertion that `_generate_mj_narration` contains
no reference to the windowed resolver and that no call site passes it one.

**K2: prompt SHAPE parity deferred, deliberately, to keep the repetition
measurement (F1) uncontaminated.** The observed prompts keep their existing
single `{transcript}` blob (`observation_intent`/`npc_initiative_act`'s
`user_template`); only the LINES composing that blob are windowed. Adopting
the played lane's role-alternating message-list shape now would change
model input structure for reasons unrelated to windowing, and would
confound F1's ongoing measurement of the beat-8 repetition onset
(`scripts/observation_metrics.py`, `per_beat_overlap`) — a ticket explicitly
NOT attempting a repetition fix must not smuggle in a shape change that
could itself move the repetition point. Named deferral: D-0052-shape.

**Two findings surfaced by live verification, deliberately left unfixed
(Scope OUT).** `assemble_scene_tail(npc_id, location_id, None, "", db)` —
the correct J1 call, since an observed run carries no gathering and
`player_presence` is always `'absent'` — renders a dangling
`"...actuellement : ."` label: `_npc_context_setting`'s player-condition
guard (`context.py`) tests `!= "unharmed"`, not truthiness, so an empty
string still emits the label with nothing to fill it. `context.py` sits at
979 of its 1000-line hard cap; fixing this is a follow-up, not this
ticket. Separately, a live over-budget test showed the `conversation_summary`
prompt (author model) refusing to summarize adult-themed observed-scene
content — the same shared code path the played lane already uses, just far
more likely to fire on the observed lane's content mix; a model-selection
question for a future decision, not a structural defect of this seam.

## OBSERVATION MULTI-BEAT SEQUENCE — client-driven loop (BRIEF-0053-a, no schema change)

**A1: the loop lives in the client, not behind a new batch route.**
`observationRunBeats()` (`index.html`) drives `POST
/api/observation/runs/{id}/step` X times — the exact single-beat path a
manual "Un beat" click already takes. Rejected: a backend batch route
(`POST /runs/{id}/steps {count}`), which would hold N x NPC model calls
inside one synchronous HTTP request and contradict `routes/observation.py`'s
own recorded finding that a bounded run can be ~150 model calls, too long
for one request. Rejected: exposing `run_bounded` over HTTP — it has no
count parameter and the same process-model objection applies. Zero backend
diff results: `observation_runner.py` and `cockpit/routes/observation.py`
are byte-identical to `main`.

**D1/D3: "Interrompre" and "Arrêter" stay two distinct verbs.** Interrupting
(`observationAbortSequence()`) leaves the run `running` and steppable — it
only raises `obsSequenceAbort`, honoured between beats. Closing the run
(`observationStopRun()`) also sets that same flag as its first statement, so
killing a run mid-sequence exits the loop cleanly on the next iteration's
status check instead of via a 422 from the now-non-`running` run.

**D2: interruption is cooperative and never cancels an in-flight beat.**
History is sacred — a cancelled request could abandon a beat whose
`observation_beat`/`observation_intent` rows are already being written. The
abort flag is only ever consulted before starting the next iteration
(`index.html`, `observationRunBeats()`'s loop head); no `AbortController`,
no request cancellation exists anywhere in the sequence.

**E1: no client-side "beats remaining" arithmetic.** `max_beats` counts
NPC-decision beats only, exempting injected events (`_regular_beat_count`,
`observation_runner.py:253-256`) — a non-obvious rule that stays
server-side. The client loop does not clamp X to any computed allowance; it
simply stops the first time a step response reports `run.status !==
'running'`, reading `stop_reason` off that same response rather than
re-deriving why the run closed. `observation_surface.py`'s Rule 7d makes
this a fail-closed gate: the literals `max_beats` and `quiescence` inside
`observationRunBeats()`'s body are a FAILURE, not a lint warning.

**F1: per-beat refresh excludes proposals.** `produce_run_proposals` runs
once, after a run closes (`observation_runner.py:616-621`), so a per-beat
`/proposals` GET during a sequence is guaranteed empty. `observationRefreshDetail`
gained an opt-out parameter (`{ proposals = true } = {}`) rather than a
duplicated "transcript only" function; the sequence calls it with
`proposals:false` per beat and once more, with proposals, when it ends. All
four pre-existing call sites keep their no-arg, default-true behaviour.

**G1: re-entrancy blocked structurally, not by convention.** A module-level
`obsSequenceRunning` flag refuses a second concurrent sequence, and
`_obsSetSequenceUi()` disables the step/sequence/inject buttons for the
duration — belt-and-braces alongside the flag check inside each handler.

**Named deferrals opened:**
- **D-0053-unattended** — no unattended/background run (close the tab, let
  it finish server-side). Would require the async/batch design A1 rejected
  plus a progress channel. Reactivate only for a measurement workstream
  needing runs longer than a creator will sit through.
- **D-0053-sequence-record** — the sequence is a UI gesture, persisted
  nowhere; no reader exists for "these beats were requested as one batch"
  (E2). Reactivate if metrics ever need to distinguish batched from
  hand-stepped beats.

## FACTION ROSTER — server-side rank ordering (BRIEF-0054-a, no schema change)

`GET /entities/{entity_id}/faction-roster` (`cockpit/crud/factions.py`) had
no `order_by` at all; the rank already existed relationally
(`faction_role.position`) but no reader consumed it. This step makes the
roster route the single source of roster ordering.

**A1: the server orders the roster.** Ordering is a structural property of
this one route, not a JS convention any caller must reimplement — any
future roster reader inherits it by calling the route; none re-sorts
client-side.

**B1: three ordered buckets with visible headers.** Declared roles by
`faction_role.position` ascending, then roles borne by active members but
not declared (alphabetical, casefold), then members with no role. Within
one role: `is_primary` first, then `joined_at` ascending — the same static
ordering `read_public_memberships` already uses (BRIEF-29).

**Casefold, never SQL `lower()`.** `_roster_rank_index` matches role names
via Python `.casefold()` — SQLite's `lower()`/`NOCASE` is ASCII-only and
would mishandle accented French role names. Same rationale as
`_resolve_role_change_role` (`cockpit/mutations.py`).

**`_membership_dict` was deliberately left alone.** The two new response
keys (`role_position`, `role_declared`) ship only through the new
`_roster_dict` wrapper, scoped to the roster route. Adding them to
`_membership_dict` would put an N+1 `faction_role` lookup on
`list_entity_memberships` (the character sheet's "Appartenances" list) for
no reader (E2).

## FACTION MEMBERSHIP — creator role reassignment + capacity chokepoint (BRIEF-0054-b, no schema change)

`faction_membership` is INSERT-only / close-only by construction (BRIEF-27):
`write_membership` can never update `role`. Close+reopen for a role change
existed exactly once, on the AI path (`cockpit/mutations.py`); the creator
path could only add and close memberships, and `max_holders` was enforced
only on the AI path via an inline counting loop.

**D2: role change is a dedicated close+reopen route.** `POST
/memberships/{id}/role` performs close then reopen inside one
`_reassign_membership_role_core` (commit-free, same shape as
`_open_membership_core`, BRIEF-35), preserving `cover_role` / `is_primary`
/ `is_secret` — mirroring the AI path's existing shape
(`mutations.py`'s `_apply_effect_role_change`) verbatim. A no-op
reassignment (same role, any casing) writes nothing; a closed membership
409s — a closed row is history and is never reassigned. The client never
issues the underlying close+open writes itself.

**E1: `max_holders` becomes fail-closed on the creator paths too.** New
`writes/factions.py::role_capacity_state(db, faction_id, role_name) ->
(active_holder_count, max_holders, canonical_name)` is the single
accessor answering "how many hold this role and what is the limit",
built on `active_role_counts` (moved verbatim from `crud/factions.py`'s
`_active_role_counts`, now public because it has two importers). Both
creator paths (open a membership, change a role) and the AI `role_change`
effect now call it; a second counting loop reappearing anywhere is the
regression `role_capacity_chokepoint.py` exists to catch. No `force`
override flag — raising `max_holders` in the roles editor is the
sanctioned escape hatch. An undeclared role stays unconstrained
(BRIEF-31's creator "autre" escape hatch) — the creator/AI asymmetry on
undeclared roles (K1 whole-rejects on the AI path, legal on the creator
path) is deliberate, not an oversight, and is untouched by this step.

**Message-preserving recabling.** `mutations.py`'s reject string
(`"role_change: role {resolved_key} is full ({count}/{limit})"`) stays
constructed in `mutations.py`, unmoved — `role_closed_vocab.py` scans that
literal text and was not retargeted; only the holder-counting sub-block
was replaced with a call to `role_capacity_state`.

## FACTION ROSTER — grouped panel + member authoring (BRIEF-0054-c, no schema change)

The faction sheet's "Membres" section was a flat, inert list
(`authorRenderFactionRoster`) even after BRIEF-0054-a shipped
`role_position`/`role_declared` on the roster route — nothing rendered them.
This step gives the roster its grouped panel and lets the creator add a
member or change a member's role without leaving the faction sheet
(decision C3). Frontend only: no route, no schema, no navigation (that is
BRIEF-0054-d).

**B1, client side: server orders, client groups.** `authorRenderFactionRoster`
groups rows the server already returned in order into three zones — declared
roles (by `authorFactionRolesLive`'s `position` order, including empty
ranks), undeclared-but-borne roles (grouped by distinct `role`, in server
arrival order — already alphabetised), then `Sans rôle`. Member order INSIDE
a zone is never recomputed; the one client-side ordering read is
`authorFactionRolesLive`'s array order for the HEADER list, because the
roster route cannot describe a rank with zero members. `faction_roster_panel.py`
tripwires a `.sort(` reappearing in the renderer.

**One sequencing wrapper, not a merge.** `authorLoadFactionMembersPanel`
awaits `authorLoadFactionRoles` before `authorLoadFactionRoster` — the
grouped render needs the declared-role list in memory first. Both loaders
keep their existing bodies and containers.

**C3: one add-member form, reusing the existing route in reverse.**
`authorAddFactionMember` posts to the same `POST /entities/{id}/memberships`
the character-side form already uses, with `faction_id` fixed to the open
faction — no new backend route. Inline role change
(`authorMemberRoleEditStart`/`Submit`/`Cancel`) reuses BRIEF-0054-b's
`POST /memberships/{id}/role` the same way. Both surface a 409 (full role,
duplicate active membership) as readable `#author-status` text, unmodified —
the client never pre-filters by occupancy.

**Debt, deliberately accepted:** the inline role-edit `<select>` reuses the
add-form's shared option list (`_factionRoleOptionsHtml`, including the
always-present `autre` option) but — per the brief — carries none of the
add-form's accompanying free-text row. Selecting `autre` inline submits the
literal string `"__other__"` as the role. No creator-facing scenario in this
step's "Done means" exercises that path; a future step should either drop
`autre` from the inline select or give it its own text-entry affordance.

## CREATION NAVIGATION — single-slot return crumb (BRIEF-0054-d, no schema change)

The Creation surface had no notion of "where a cross-tab navigation came
from" — `showCreationSubTab` resets the selected entity on every tab change
via `state.onTabEnter`. BRIEF-0054-c's grouped roster gave the faction sheet
a reason to open a member's real sheet without losing the faction; this step
adds that navigation plus a single return control, on the `<- Lieu`
(`btn-scene`) house idiom.

**F2a: one crumb, never a stack.** `creationReturnTo` holds `{tabId,
entityId}` or `null` — no array, no depth. Faction -> NPC -> another faction
leaves one crumb, the most recent; that is the decided behaviour, not a
limitation. The day a second consumer needs depth, this becomes an array
with no other change (no structure without a reader).

**Structural over disciplinary: one unconditional clear plus call ordering,
not a remembered-at-each-site discipline.** `showCreationSubTab` clears the
crumb unconditionally, immediately after `currentCreationSubTab = tab;` —
every tab activation, manual or programmatic, passes through here.
`creationOpenEntityFrom` re-sets the crumb only AFTER calling
`showCreationSubTab`, which is what makes a manual sub-tab click (no re-set
follows) clear it while a programmatic navigation (re-set follows) keeps it.
`creation_return_nav.py` tripwires the ordering: reversing the two lines
inside `creationOpenEntityFrom` silently breaks the whole feature while
looking correct, which is exactly the regression the check exists to catch.

**Fail-closed over advisory.** Both `creationOpenEntityFrom` and
`creationReturnToOrigin` verify `currentCreationSubTab === ` the target
before touching the crumb or selecting an entity — `showCreationSubTab`
early-returns into `creationInit()` when the registry isn't loaded yet, and
in that case both helpers abort silently rather than leave a crumb pointing
at a tab never reached.

**The one documented hardcoded tab-id pair.** `creationResolveEntityTab`
resolves every entity type through the `CREATION_TABS` registry
(`archetype === 'entity'`, matching `type`) except `character`, split into
`npc`/`pj` by `playerCharIds` — the registry has no other way to
distinguish them, the same discriminator already used elsewhere in the
file. This lives in the resolver, not inside `showCreationSubTab` or
`_creationActivateTab`, so it does not trip `page_contract.py`'s
no-tab-literal scan of those two bodies; it is a deliberate, singular,
commented exception, not a precedent for hardcoding elsewhere.

**F3 (multi-entity tab bar) stays refused.** No openable/closable entity
tabs, no strip, no per-entity state retention — explicitly out of scope and
coupled to the pending `index.html` split decision.

## FRONTEND BUILD FOUNDATION — Svelte/Vite toolchain, static serving, committed build (BRIEF-0055-a, BRIEF-0055-b, BRIEF-0055-c, BRIEF-0055-d, no schema change)

**The no-build reversal (A1).** The target is a Svelte SPA owning `/`; the
transition is necessarily island-shaped because `index.html`'s ~11k lines of
JS are physically interleaved across surfaces and cannot be range-cut.
Islands are the intermediate state, not an alternative target.

**The Play boundary (B1).** Play stays vanilla-JS until its own rewrite.
Factual correction of record: no HTMX ever existed in this project —
`grep -c "hx-"` on `index.html` returns 0, and no `htmx` token exists
anywhere under `src/` or `tooling/pipeline_cockpit/`. The prior `CLAUDE.md`
line claiming an HTMX frontend was wrong independently of this ticket.

**The legacy-mount registry, DEFERRED to TICKET-0056 (named deferral).** A1
plus a permanently-vanilla Play requires an escape hatch inside the SPA; an
escape hatch rots unless it is an enumerated, monotonically shrinking
registry policed by a fail-closed check, reaching exactly one entry (Play)
at TICKET-0061. Not built at 0055.

**Serving topology (C1) and the rejection of C3.** `/static` mount; `GET /`
untouched; `/shell` as the transitional beachhead and the seam TICKET-0056
renames. C3 (extending the per-file vendor whitelist) is rejected because a
whitelist cannot express content-hashed filenames without ceasing to be
one. `app.py`'s "wait for a second vendored asset" deferral is resolved on
different grounds, not by analogy — a build output is a whole asset FAMILY
with content-hashed names, not a second individually-whitelistable file.

**Cytoscape stays vendored (D3)**, external to the bundler; the graph-engine
question is TICKET-0057's, deliberately not pre-empted here.

**Committed build output (E1) and why.** Building at launch fails open — a
stale or absent build renders a blank page. A committed artifact, a boot
guard (`app.py`'s `_check_frontend_build_on_startup`), and
`frontend_build_fresh.py` make both failure modes refusals instead. The
canonical source-hash algorithm is specified once, in `BRIEF-0055-c`, and
implemented twice against that text: `frontend/scripts/write-manifest.mjs`
(writer, at build time) and `tooling/verify/checks/frontend_build_fresh.py`
(reader, at verify time) — if the two implementations ever disagree, the
check goes red on a fresh build, which is the correct failure direction.

**Permission scope (F3).** `.claude/settings.json` gained exactly
`Bash(npm ci:*)` and `Bash(npm run build:*)`, never a bare `npm install`, so
"no new dependencies without a decision" is structural rather than
instructional: the executor can build and reproduce the lockfile, and
cannot add a package.

**Node is a BUILD dependency, never a RUNTIME one (E1 corollary).** The
output being committed, a normal prod launch requires no Node at all —
`docs/launch-procedure.md`'s prod block stays valid on a machine with none
installed. Toolchain versions observed during this ticket's execution:
`node v24.18.0`, `npm 11.16.0`; `frontend/package.json` declares a matching
`engines.node` field, declarative only (`engine-strict` deliberately off).
Exposure, accepted for now: `frontend_build_fresh.py` compares SOURCES to
the manifest, never output to anything, so a divergence caused by a
different Node major on a future second build machine would pass unseen.
The day a second build machine exists, pinning (`.nvmrc` plus a version
manager) becomes a ticket of its own — not decided here.

**Line-ending reproducibility (found at BRIEF-0055-c's red-test,
escalated).** With `core.autocrlf=true` on the build machine, a plain `git
checkout` of a frontend source file silently rewrote it to CRLF; `git
status`/`git diff` showed nothing (git normalizes for its own comparison)
while the byte-level source hash diverged, turning `frontend_build_fresh.py`
red with zero real source change — and a fresh clone on a differently
configured machine would reproduce the same false failure. Fixed
structurally in the committed `.gitattributes`, extending the rule
`src/world_engine/cockpit/vendor/* -text` already established for the
vendored cytoscape file: `frontend/** text eol=lf` (hand-authored sources,
diffs matter) and `src/world_engine/cockpit/static/** -text` (generated
output, treated like vendor). Explicitly REJECTED: a per-machine
`core.autocrlf` setting (uncommitted, protects no other machine), and
normalizing line endings inside the hash algorithm itself (would leave the
gate green while Vite still read CRLF sources and could emit divergent
output — fail-open). `frontend_build_fresh.py` carries a diagnostic-only
4-bis check that names this exact failure mode by message when it recurs,
without ever letting the normalized comparison substitute for the primary
one. Scope note: the `.gitattributes` rule covers only this ticket's paths;
whether the repo wants a global `* text=auto eol=lf` is a separate
governance question, not settled here.

**The 3D guard rail, re-nailed.** No speculative character coordinates;
"qui entend quoi" stays behind the single earshot accessor; 3D consumes
what canon exposes and never dictates storage. The frontend rewrite is the
moment of temptation to leak spatial shortcuts into the client — this
invariant holds unchanged through the migration.

## COCKPIT SHELL — legacy-mount registry, iframe boundary, enumerated routing (BRIEF-0056-a, BRIEF-0056-b, BRIEF-0056-c, BRIEF-0056-d, no schema change)

**The registry is three entries, not one (A2).** A single "monolith" entry
cannot discharge TICKET-0055's deferral: it vanishes rather than shrinks, so
the count stops being a measurable gate. `creation` is retired by
TICKET-0059, `observation` by TICKET-0060, `play` survives to TICKET-0061
and beyond, until its own rewrite.

**One iframe, and `index.html` byte-untouched (B1).** The three views are
`display:none` siblings over one global scope; "load only Play's JS" is not
constructible. The iframe isolates JS and CSS by construction, so 319 inline
handlers and 175 globals keep working with zero edits and the nine
index-anchored checks stay green by non-event. B2 (same-document injection)
rejected: it would merge 175 globals and 1039 lines of unscoped CSS into the
new surface.

**No `postMessage`: same-origin direct invocation, confined.** Shell and
legacy share an origin, so surface switching is a direct call on the legacy
window. Confinement is a check (`legacy_mount.py` assertion 5), not a
convention: `contentWindow` / `legacy-frame` tokens may occur only in
`frontend/src/legacy/bridge.js` and `LegacyFrame.svelte`.

**The history trap, and why the frame `src` is written once.** An iframe
navigation pushes onto the PARENT history stack; reassigning `src` to switch
surfaces would make Back replay legacy boots instead of shell routes.
Enforced by assertion 6 (exactly one `src="/legacy"` site, zero `.src =`
reassignments), not by memory.

**C3: the server stays the authority.** The shell delegates the whole
world-switch cascade to the legacy `activateWorld()` rather than re-POSTing
`/api/worlds/{id}/activate` itself, then mirrors `/api/bootstrap` +
`/api/worlds` afterwards. Named contrast: the legacy `loadBootstrap()`
swallows every error in `catch (_) {}`; the shell's mirror refuses visibly
(a failed read sets a store `error` field and the shell renders a refusal
band, never a silently-stale selector).

**D3b and the death of the catch-all.** The measured fact that decides it:
the 151 API route literals do not carry `/api` in their text
(`crud/_router.py` declares the prefix at mount time), so a catch-all's
exclusion list would be a convention with a silent failure mode — a future
router included without the prefix would vanish into the shell. D2 (hash
routing) is fail-open in the other direction: a typo'd hash can never be a
404. Enumeration (`_SHELL_ROUTES` in `app.py`, mirrored by `SHELL_ROUTES` in
`frontend/src/lib/router.js`, cross-checked by `legacy_mount.py` assertion 7)
makes both a surface typo and an API typo real 404s.

**The server never learns the tab vocabulary (D-ii).** `{sub_tab}` is opaque
server-side and resolved against `CREATION_TABS` client-side, so a runtime
entity type (TICKET-0046) is deep-linkable with no server change — the same
rule `page_contract` already enforces on the tab mechanism generally. The
`'npc'` fallback is reused from `activateWorld`, not invented. Executor's
finding: `authorRegistry` and `CREATION_TABS` are `let`/`const` bindings at
the legacy script's top level, never reflected as `window` properties
(unlike a function declaration or `var`) — the deep-link resolver reads an
equivalent DOM-only signal instead (`#creation-shell-title` populated,
`#ctab-<key>` presence), same throw-on-timeout semantics, zero `index.html`
edit.

**The URL is authoritative on entry, not continuously synchronized.**
Continuous sync would require the legacy document to call out to the shell,
i.e. an edit to `index.html`, which this ticket refuses. **Named deferral,
logged here:** continuous sync arrives with the Creation surface itself at
TICKET-0058.

**G1: no check re-homed.** Nothing structural moved. `relation_graph.py`'s
Lieux-graph byte-equality assertion against `main` stays a live gate the
next editor of those functions will meet.

**Two records corrected.** (i) The map's "Play preserved as an HTMX island"
is wrong — no HTMX ever existed, already established at TICKET-0055; Play is
a vanilla-JS island. (ii) The 3D guard-rail is NOT restated in this entry:
TICKET-0055's entry already re-nailed it, and restating doctrine is how
doctrine drifts — cross-reference only.

**Renaming `index.html` is deferred to TICKET-0061 (named deferral, logged
here).** Three files now share the name (`frontend/index.html` the Vite
entry, `cockpit/index.html` the legacy surface, `cockpit/static/index.html`
the build output); the rename touches all nine index-anchored checks, which
that ticket retires anyway.

## GRAPH PRIMITIVE — one component, three consumers, a shrinking registry (BRIEF-0057-a, BRIEF-0057-b, BRIEF-0057-c, BRIEF-0057-d, BRIEF-0057-e, no schema change)

**There were three implementations, not two (RECON finding).** The
workstream map named the Lieux SVG editor and the cytoscape relation graph.
RECON found a third: `reviewGraphRender`, the pre-commit preview, with two
consumers of its own (region and room batch). It already called
`graphAutoPlace` from the Lieux implementation and then re-emitted its own
SVG — placement shared, rendering diverged. That is what "plusieurs choses
qui font la meme chose" looks like from the inside: not a decision to
duplicate, a convergence abandoned halfway.

**A1 — the pilot renders as an in-frame island, and why nothing else was
constructible.** All four graph surfaces live in Creation, a legacy mount
until TICKET-0059; TICKET-0056 deferred continuous route sync to
TICKET-0058, so the shell cannot know which sub-tab is active. A shell-side
graph pane was therefore not an option, and reordering after 0058 would have
defeated the locked strategy of proving the primitive BEFORE broad migration
while inflating 0058.

**B3 — three consumers, not one.** A primitive with one consumer proves
nothing; the second is what tests the contract. The two SVG implementations
also carried no cytoscape dependency and no scoped-CSS problem. Accepted and
recorded cost: the contract is frozen without ever exercising a force
layout. `force` arrives with its consumer at TICKET-0058.

**The contract, and why capability is a callback and not a boolean.**
`onConnect` / `onDeleteEdge` / `onMoveNode` absent means the interaction is
structurally off. Boolean axes (`editable`, `persistsPositions`) would have
had to be invented in pairs that only one consumer sets, and never
independently — an axis nobody varies is a lie in the contract and the
first plank of a leaky union type.

**G, and the axis that evaporated.** `graphAutoPlace` entered the primitive
as its single placement strategy. It already handled both stored
coordinates and null-coordinate fallback, so `placement` never became an
axis at all: one strategy, data-driven branch. Recorded because it is the
cleanest evidence that E1 was the right discipline — the axis the map
proposed did not survive contact with the code.

**D2 — the declaration site is the slot descriptor, not the trait
registry. NAMED DEFERRAL: `graph_spec_for(entity_type)`.** `CREATION_TABS`
slots and the review descriptor already had live readers and a structural
assertion; `traits.py` had none — no entity type declares a graph today, so
`graph_spec_for` would have been structure without a reader (E2). It is
deferred, not dropped: the day a runtime entity type wants to declare a
graph, that is a ticket with a real consumer.

**C1 — the lock, and what a shrinking registry buys.** Modelled on
TICKET-0056's legacy-mount registry. The guarantee is measurable during the
transition — a counter that can only decrease — rather than promised for
the end. Rule 5 (every entry must still describe real code) is what keeps
rule 3 honest: the registry is forced to shrink when its code goes, instead
of rotting into a stale list.

**F — a guard that was fail-open, named.** `relation_graph.py`'s clause 5
asserted the Lieux functions were byte-identical to `main` via `git show`.
On a branch it bit; once merged, `main == HEAD` and it passed trivially
forever. Recorded rather than quietly deleted, because the failure mode is
general: any check comparing the working tree to `main` is a branch freeze,
not an invariant. Replaced by `graph_primitive.py`, which holds after merge.

**Zero dormant code, made structural.** The creator's constraint was that
no converged implementation survive at close. It is enforced by the lock's
rule 1 as raw-substring absence, any context — a commented-out body is
dormant code. This matters more than usual here because `undefined_names.py`
covers Python only: there is no automated safety net for a dangling JS
reference in `index.html`.

**Finding handed forward to TICKET-0060.** Observation renders no graph.
Zero `<svg>` elements and zero graph calls in the thirteen `observation*`
functions. TICKET-0060's open decision D-A is answered in advance: it is
not a primitive consumer.

**The 3D guard rail: cross-reference only.** TICKET-0055's entry nailed it
and TICKET-0056 declined to restate it on the grounds that restating
doctrine is how doctrine drifts. That reasoning holds here too.
Cross-reference, do not restate.

---

## CREATION SPINE — island seam, graph convergence, closure-driven scope (BRIEF-0058-a, BRIEF-0058-b, BRIEF-0058-c, BRIEF-0058-d, BRIEF-0058-e, BRIEF-0058-f, BRIEF-0058-g, BRIEF-0058-h, BRIEF-0058-i, BRIEF-0058-j, BRIEF-0058-k, BRIEF-0058-l, no schema change)

**A1 — the seam runs legacy-hosts-Svelte, and why nothing else was
constructible.** A migrated Creation surface mounts as a Svelte island
inside the legacy container it already owns, signalled by a CustomEvent —
the exact mechanism TICKET-0057 proved with `graph:slot`. The alternative,
shell-owned Creation chrome, was rejected: it would have put a Svelte tab
bar and the legacy tab bar in the tree simultaneously for two tickets, with
a synchronization contract between them — two authorities over one fact,
the failure mode this whole workstream exists to end. It was also not
constructible without defeating a standing registry:
`frontend/src/legacy/registry.js` already declared
`creation: { retiredBy: 'TICKET-0059' }` before this ticket started.

**B2 — measured wrong twice, and corrected in flight both times. This is
the ticket's most transferable lesson.** Intake assumed the migration
surface was eleven `CREATION_TABS` keys, by label. RECON-0058-a's M4
measured the real `author*` call closure and found only eight —
`artefacts`, `intrigues`, and `queue` never call or are called by
`author*` code, three independent ways each. That measurement was itself
incomplete: `intrigues` never calls `author*`, but its registry entry
writes into `#author-entity-list`/`#author-main`, the exact nodes the
entity-list and sheet briefs turn into mount points. A call-graph rule
alone missed a real coupling — occupying a container a Svelte island is
about to own is a dependency, even with zero function calls in either
direction. RECON-SUPPLEMENT-0058 restated the rule as **call closure UNION
container occupancy, with the generic dispatcher
(`_creationActivateTab`/`showCreationSubTab`/`renderCreationShell`/
`_onDemandSlotToggle*`/`_renderOnDemandToggles`) as a BOUNDARY, never a
member** — those five functions are shared by every `CREATION_TABS` entry,
including the three that stay legacy, and no brief may move them under A1.
The final, measured migration surface is **nine** keys: `npc`, `pj`,
`lieux`, `factions`, `objets`, `intrigues`, `evenements`, `region`,
`constructeur`. The residual, confirmed by brief -j's closure-sealing pass,
is **five** legacy tabs: `competences`, `registre`, `prompts`, `artefacts`,
`queue` — all five go to TICKET-0059. `markCardDone`, `spatialTalkTo`, and
`evenementsRemoveChip` were M4 false positives (apparent `author*` call
sites that were actually inside a comment block); they were never in
scope.

**The Review Queue never used the review component — corrected here.**
The workstream map assumed the Review Queue tab was a `review*` consumer.
`reviewRegister` has exactly two real call sites, `region` and the room
batch generator (`batch`); the queue's loader and its whole
proposed-mutation section carry zero `author*` and zero review-component
references. The queue was never in this ticket's closure under any reading
of B2; it goes to TICKET-0059 alongside `artefacts`.

**C2 — one renderer, not two behind one API, and the cost paid on
purpose.** The relation graph converges onto `Graph.svelte`; the vendored
`cytoscape-3.34.0.min.js` (435 KB) and its `/vendor` route are deleted, and
`frontend/src/graph/registry.js` is now permanently empty. Ego/global
modes, the four strength buckets, zoom/pan, double-tap recentring and the
create/edit edge panel were reimplemented against the primitive's
contract, not carried across. The one DROP candidate RECON-0058-a flagged
— `relGraphGlobalNodeDblTap`, a cosmetic, non-persisted "followed" node
enlargement in global mode only — was dropped; ego-mode double-tap-to-
recenter is a different behaviour and was ported. The force-layout
parameters are measured, not guessed: RECON-0058-a M1 ran a plain,
library-free force simulation (Coulomb repulsion + spring attraction +
centring, fixed 300 iterations) against the pilot's real graph (`|V|=7,
|E|=8`) and found it legible (no node overlap, 1 of 8 edges crossing) in
under 1 ms; at 10x synthetic scale (`|V|=70, |E|=80`) wall-clock time stays
under 20 ms (~100x headroom below the 2000 ms escalation gate) but
legibility degrades under the primitive's fixed, non-zoomable 960×480
viewBox — a headroom ceiling for a future large-world graph, not a
blocker at the pilot's current scale. The substrate itself changed:
cytoscape painted to a `<canvas>`; the primitive paints SVG DOM.

**D1 — the shape of the amended lock.** The graph registry parsing zero
entries is no longer, by itself, a failure. `graph_primitive.py`'s rule
changed direction: from "each declared implementation is present at its
locus" to "each baselined implementation (`baseline - live`) is proven
ABSENT from its locus, via the append-only `graph_impls.retired` record" —
`graph_impls.retired` is now the load-bearing half of the guarantee, not
the shrinking `GRAPH_IMPLS` export. The registry is empty and stays empty:
a second graph engine is constructible today only by defeating this
fail-closed check.

**E1 discharged.** The TICKET-0056 named deferral — continuous route sync
— landed at brief -k. `showCreationSubTab` dispatches a one-way
`route:subtab` CustomEvent after the active tab actually changes; the
shell mirrors it into the address bar via `router.js`'s `replace()`
(`history.replaceState`, no `popstate` re-entry, so Back leaves Creation in
one step and the legacy document is never re-entered) — the same
one-way legacy-to-shell signalling `graph:slot` already established, no
new direction of control.

**M5's refutation, and the structural answer — not a remount
convention.** RECON-0058-a M5 found that a Svelte island mounted as a
plain child of a legacy container does NOT survive a sub-tab switch away
and back, nor a world switch: `_creationActivateTab` and
`_creationRunWorldSwitchResets` both unconditionally re-run a live legacy
`loader`/`onWorldSwitch` renderer, which `innerHTML`s over the mounted
island. The RECON result's own suggested fix — remount from inside the
legacy renderer on every call — was rejected as the fix for the PROBE, not
the product: it would have kept a destructive legacy renderer alive
permanently and made the mount's survival a matter of call-site
discipline. The structural answer instead: an entry declaring `island`
MUST also declare `loader: null` and `state.onWorldSwitch: null` — the
shell owns that tab's body outright, and there is no legacy renderer left
to destroy anything. World-state resets move into the Svelte component,
driven by `serverState.worldId` directly (the server is the authority on
the active world, TICKET-0056 C3) rather than a legacy callback telling the
island to reset. `creation_island.py` enforces both halves of this rule —
one entry declaring `island` without `loader: null`/`onWorldSwitch: null`
is a failure, and the `island:slot` dispatch itself must be unconditional,
never gated behind a first-time/loaded flag.

**The island registry GROWS.** Unlike `frontend/src/legacy/registry.js`
and `frontend/src/graph/registry.js` — both monotonically SHRINKING lists
of what remains legacy — `frontend/src/creation/registry.js` is a record
of what has MOVED: one entry per migrated surface, never removed once
added. A later reader must not apply a shrink-only rule to it; growth is
the correct, intended shape of this particular registry.

**Every check re-homed, and where.** No guard lapsed between commits.
`graph_primitive.py` (BRIEF-0058-b/-c) — amended semantics above, its
locus is now `frontend/src/graph/consumers/relations.js` for the live
relation engine. `relation_graph.py` (BRIEF-0058-c) — re-homed onto the
same consumer; its prior byte-identical-to-`main` clause (a fail-open
branch-freeze, not an invariant, as TICKET-0057's entry already named) is
gone with it. `creation_island.py` (BRIEF-0058-d) — new, asserts the
island seam and the loader/onWorldSwitch partition. `page_contract.py`
(BRIEF-0058-e..-k) — asserts the `CREATION_TABS` mechanism against its new
locus, reporting the islands/legacy migration split on every pass; the
loader/onWorldSwitch partition rule lives in `creation_island.py`, not
duplicated here. `review_component.py` / `review_root_fallback.py`
(BRIEF-0058-i/-j) — re-homed onto `frontend/src/creation/review/
registry.js` plus its two Svelte consumers, `Region.svelte` and
`RoomBatch.svelte`; the component's now-unused string-render half
(`reviewNode`/`reviewTree`/`reviewOpenSheet`/`reviewToggleGraph`/
`reviewIsAccepted`/`reviewToggleAccept`/`reviewNotes`) was retired at -j,
shrinking the governed surface to the four generics with a real reader.
`creation_return_nav.py` — re-homed onto `FactionRoster.svelte` (a
same-family follow-up after brief -g). `event_tab.py` (BRIEF-0058-j) —
re-homed onto `Evenements.svelte`. `faction_roster_panel.py`
(BRIEF-0058-g) — re-homed onto `FactionRoster.svelte`. `legacy_mount.py`
still passes with `creation` present in the registry — this ticket does
not retire it. `frontend_build_fresh.py` still passes against the larger
committed build.

**Region's parallel field renderer — a named, unresolved convergence
candidate.** `region` carries its own field-rendering family
(`_sheetListSection`/`_regionSheetNode`/`_sheetFieldInput`/
`_sheetFieldTextarea`/`_sheetEntityOptions`/`_regionSheetRolesHtml`/
`_regionSheetAddRole`/`RemoveRole`/`MoveRole`/`regionRenderSheet`),
distinct from the migrated `authorRenderField`/`Field.svelte` engine — a
genuine "plusieurs choses qui font la meme chose" candidate. RECON-
SUPPLEMENT-0058 directed report-only: it was not converged in this ticket
and no ticket has been opened for it.

**What is still deferred, by name.** `graph_spec_for(entity_type)`
(TICKET-0057 D2) — still no reader; no runtime entity type declares a
graph today. The `index.html` rename — TICKET-0061. The link agent and
`npcAgent*`/`linkAgent*` — TICKET-0059; RECON-0058-a M8 confirmed they sit
outside the `author*` closure entirely, in their own sibling DOM panels,
with exactly one coupling point (`linkAgentCommit`'s post-commit refresh,
now retargeted at the primitive's `graph:invalidate` event instead of the
deleted `relGraphFetchGlobal`/`relGraphFetch`). The 3D guard rail —
cross-reference only, per TICKET-0055/-0056/-0057's own discipline;
restating doctrine is how doctrine drifts.

---

## DOORS EDITOR EFFECT CYCLE — pure derivations are $derived, not $state (BRIEF-0062-a, no schema change)

`DoorsEditor.svelte`'s `neighbours` and `orphans` were `$state`, seeded by
a `resetFromProps` function called from a single `$effect`. That function
assigned `neighbours` and then read it (`.forEach`) later in the same
body. On mount the write was untracked (not yet a dependency) and the
read made it one; on every subsequent run — triggered by any relation or
door prop change — the write now redirtied an established dependency
with a fresh array (new reference every time, so equality never held),
rescheduling the effect forever. Svelte threw `effect_update_depth_exceeded`
during the flush, which aborted the whole flush — the reason
`RelationsEditor`, `KnowledgeEditor` and `DiscDetailsEditor`, siblings in
the same `Sheet.svelte` render pass, silently stopped repainting even
though their own mutations had already persisted on the backend
(TICKET-0062's field report).

**The fix removes the cycle by construction, not by reordering.**
`neighbours` and `orphans` are pure derivations of props (`relations`,
`doors`) — they were never state to begin with. Converting them to
`$derived` means there is nothing to write inside the seeding effect
except `values` (genuinely stateful: seeded from the derivations, then
edited via `bind:value`), and `values` is never read back inside that
same effect body. Rejected: reordering the assignments so the reads come
first — fixes the symptom, leaves three bindings that were never state.
Rejected: wrapping the read in `untrack()` — hides a cycle rather than
removing one.

**The seeding effect had to become `$effect.pre`, not a plain `$effect`
— a finding beyond the brief's original spec, made during live
verification.** With a plain `$effect`, `$derived neighbours` can observe
a new prop (e.g. a fresh `connects_to` relation) before the plain effect
— which runs after the DOM commit — has populated `values[n.id]`, so the
template's `bind:value={values[n.id].x}` reads through a not-yet-existing
entry and throws (`Cannot read properties of undefined (reading 'x')`).
`$effect.pre` runs before the DOM patch, closing that window. Retested
live after the change: no crash, no stale door coordinates, Relations/
Knowledge/Portes all repaint correctly on a location with a `connects_to`
neighbour.

**Structural guard: `effect_self_write.py`.** The general rule —
inside a `$effect` (or `$effect.pre`) body, a `$state` binding that is
assigned in that body must not be read (`.`/`[` access) afterwards in
the same body, with local functions called from the body inlined one
level deep — is enforced fail-closed across every `.svelte` file under
`frontend/src/`. Deliberately narrow: a bare identifier reference isn't
a "read" for this rule, and only reads *after* the first assignment
count — `RelationsEditor.svelte`'s `newOther` effect reads that binding
first and assigns it later under a converging guard, and must keep
passing. Verified against both trees: one finding
(`DoorsEditor.svelte`/`neighbours`) before this fix, zero after.

Two related defects surfaced during live verification and are
explicitly NOT fixed here (recorded for a follow-up ticket):
`GeometryEditor` receives a fresh object literal (`detail.geometry ||
{...}`) whenever `detail.geometry` is falsy, so its effect re-runs on
unrelated parent updates; and `DoorsEditor`'s `values` reseeds from
`doors` on every prop change, so a concurrent `onSaved` can discard an
in-flight or just-saved x/y entry — concretely observed after a
geometry save, whose response carries no `doors` key. Backend data was
confirmed intact via direct API read in both cases; this is a display
staleness, not data loss, and fixing it means touching `Sheet.svelte`
and/or the geometry endpoint's response shape, both out of this brief's
scope.

## COCKPIT STYLESHEET PARTITION — one shared sheet, two documents (BRIEF-0063-a, no schema change)

Creation's entire visual layer — buttons, cards, badges, the `:root`
design tokens — lived in one ~1050-line `<style>` block inside
`cockpit/index.html`, shared by Play/Observation/Creation alike. Once
Creation mounts outside the legacy iframe (BRIEF-0059-l), nothing in that
inline block reaches it — a finding escalated during BRIEF-0059-l's own
reconnaissance (RECON confirmed it: not a fraction lost, all of it,
tokens included, and no check in the tree would have noticed).

**Three destinations, not two.** `frontend/public/shared.css` — the layer
both surviving documents (`frontend/index.html`, `cockpit/index.html`)
need — and `frontend/public/creation.css` — Creation-only, linked by both
documents while Creation still renders inside the legacy iframe, until
BRIEF-0059-l deletes the legacy `<link>` and nothing else. What's left
inline in `cockpit/index.html` is Play plus the legacy document's own
chrome (header, mode tabs, the `.app-view` wrappers) — never duplicated,
never needed by `frontend/index.html`, so never extracted. Cascade order
is made moot by a check, not reasoned about: `stylesheet_partition.py`
forbids any selector from appearing in more than one of the three
destinations, so if none does, load order cannot decide a conflict.

**The selector audit corrected the planning hypothesis on two points**
(`RECON-0063-a-selector-audit.md`), both load-bearing enough to record
here rather than only in the brief artifact:

- **Header and Mode tabs stay inline, not shared.css.**
  `frontend/src/Header.svelte` already fully reimplements both with its
  own scoped `<style>` — independent, hardcoded colors, not even the
  shared `var(--*)` tokens. No Creation island renders a `<header>` or
  `.mode-tab` element. `frontend/index.html` has zero dependency on
  `cockpit/index.html`'s copy, on any timeline — the shell's header is
  permanently a different implementation. The governing test isn't
  "is this Creation-flavored," it's "does a Creation island's own
  generated markup, or something it inherits, reference this rule" —
  page-chrome selectors that exist solely in `cockpit/index.html`'s own
  hand-written body fail that test even though they're not Play, either.
- **Generic modal moved to shared.css, not creation.css.** The world
  create/delete modal (`Header.svelte`'s "+ Monde" / "🗑 Monde", visible
  on every surface, not Creation-scoped) renders into the legacy
  document's `#generic-modal-backdrop` via `worldCreateOpen`/
  `worldDeleteOpen` — reachable, and required to render correctly, while
  Play or Observation is the active surface. Leaving `.modal-backdrop` in
  creation.css would work today (creation.css is linked from both
  documents "for now") but silently break the day BRIEF-0059-l drops
  `cockpit/index.html`'s creation.css `<link>` — Play and Observation
  never stop living in that document. shared.css is linked
  unconditionally in both documents forever; `Modal.svelte` (the one
  genuine Creation-island consumer) is unaffected either way.

**Asset shape: unhashed, in `publicDir`.** `static/assets/index-*.css` is
content-hashed by Vite; a `<link>` in `cockpit/index.html` (a Python-served
template, not a Vite entry) would break on every rebuild. Both sheets live
in `frontend/public/`, copied verbatim by Vite's `publicDir` mechanism,
referenced by absolute path (`/static/shared.css`) so `base: '/static/'`
never rewrites them.

**rule5 binds the creation.css `<link>`'s lifetime to `LEGACY_MOUNTS`,
structurally, not by discipline.** `cockpit/index.html` links
`/static/creation.css` if and only if `frontend/src/legacy/registry.js`'s
`LEGACY_MOUNTS` still declares `creation`; both directions FAIL. This is
what makes BRIEF-0059-l's single deleted `<link>` a required edit rather
than a remembered one — the same shape as `legacy_call.py`'s rule7 tying a
bridge-reach baseline's survival to the same `LEGACY_MOUNTS` declaration.

**Named deferral: D-0063-scoped-component-styles.** `creation.css`'s rules
are NOT moved into per-component scoped `<style>` blocks in this ticket —
this brief runs *before* BRIEF-0059-l, so Creation still renders inside
the iframe, where a scoped style would be inert the moment it was written
(Svelte's shell-injected scoped CSS never reaches that document; several
islands already document this constraint in their own header comments).
Reactivate after TICKET-0061, when no document outside the shell consumes
these rules.

**Pre-existing, not introduced here, reported only:** two dead rules in
Author view (`.author-type-tabs`, `.author-new-row`, zero markup consumers
anywhere in the tree) moved verbatim rather than deleted (a stylesheet
extraction is not the place for that cleanup); `.scene-gathering-card`
reads `var(--surface)`, never declared in the `:root` token block.

## TICKET-0059 DOCTRINE SEAL — bridge-reach, LocationTree, Modal, effect-cycle, three-surface census (BRIEF-0059-m, no schema change)

TICKET-0059 retired the legacy `creation` mount and finished the Creation
periphery migration begun in TICKET-0058. Five decisions from across the
chain are load-bearing enough to record here, each with why it went the
way it did, not just what shipped.

**The bridge-reach seam is scoped to `callLegacy`, not the string
`legacyCall`.** RECON-0059-a M1 found eight further named wrapper exports
(`showSurface`, `activateWorldViaLegacy`, `openWorldCreate`,
`openWorldDelete`, `showCreationTab`, `getSelectedCharacterId`,
`selectEntity`, `selectRecord`) reaching the same legacy window through the
identical `callLegacy` primitive without ever spelling `legacyCall` — a
check that grepped the literal string would have been structurally blind
to all eight, and to a tenth wrapper added the same way. `legacy_call.py`
rule 2 derives the reaching surface from `bridge.js`'s own exports rather
than hardcoding names, so a new wrapper is caught automatically. Rule 7
structurally ordered the mount retirement (`-l`) after the seam closed to
zero-for-TICKET-0059, rather than trusting brief sequencing to get there.

**`LocationTree.svelte` converges the two agent location pickers, but they
were not a copy-paste.** RECON-0059-a M4 found `_npcAgentTreeHtml` and
`_linkAgentTreeHtml` differ in kind, not just naming: single-select radio
over one `npcAgentSelectedRoot` versus multi-select checkbox over a `Set`
whose predicate additionally treats a node as checked when any ancestor is
checked. What's shared is the recursive traversal and the two already
shared CSS classes; what differs is the row control and the checked-state
predicate. The resolution is a row snippet plus an `isChecked(node)`
predicate prop, not a `mode: 'single' | 'multi'` prop — the union-type
shape TICKET-0057's own D-C question taught this project to refuse: a
component that branches internally on an interaction-model enum has
absorbed two behaviours rather than converged one. `location_tree.py`
locks the count at exactly one recursive location-tree renderer under
`frontend/src/`.

**`Modal.svelte` landed only once the legacy `genericModal*`
implementation died, with no allow-list.** `genericModalOpen`/
`genericModalClose` were chrome, not sheet-local — consumed by three
legacy call sites beyond the Svelte one (`competences`, world create,
world delete) — so the primitive could not converge until the chrome
inverted at `-l`. `modal_primitive.py` asserts exactly one
backdrop-plus-panel dialog implementation exists under `frontend/src/`,
with no exception list: the same shape as the graph and review primitives
before it.

**The effect-cycle rule (TICKET-0062), discovered inside this ticket's
live testing.** Pure derivations of props are `$derived`, not `$state`;
assign-then-read of a `$state` binding inside one `$effect` body is
forbidden, enforced fail-closed across `frontend/src/` by
`effect_self_write.py`. Observed failure mode: a flush aborted by
`effect_update_depth_exceeded` silently stops *sibling* components
repainting, even though their own mutations had already persisted on the
backend — the symptom (stale UI on unrelated components) sits far from the
cause (a write-then-read cycle in one sibling's effect), and the two must
be connected explicitly for the next person to diagnose it quickly. Full
account: this file, "DOORS EDITOR EFFECT CYCLE — pure derivations are
`$derived`, not `$state`".

**The three-surface census rule supersedes RECON-0059-a M5's two-surface
claim.** M5 asserted no cross-reads existed between Play and Creation; the
search covered only those two surfaces, and `observationOpenPrompt` — a
Creation-to-Observation cross-read — was found only during brief `-i`'s own
execution, not by the RECON that was supposed to catch it. The rule going
forward: every caller census for a migrating function covers Play,
Creation **and** Observation — never just the two surfaces the ticket
happens to be about.

**Named deferrals**, each with an explicit reactivation condition:

- **D-0059-prompts-surface** — promoting the Prompts tab out of Creation
  into its own top-level surface. Reactivate when a second
  creator-tooling surface appears, or when D-0050 activates and the two
  would share a home.
- **D-0059-npc-agent-termination** — the NPC agent's run loop detects
  completion by catching an error and string-matching `'already fully
  generated'`, while the link agent reads a `result.done` flag: two
  different completion contracts for structurally similar loops.
  Reactivate when either endpoint's contract is next touched; a backend
  message-text edit silently breaks the loop today with nothing to catch
  it.
- **D-0050** is re-stated verbatim, not modified:

  **Named deferral D-0050 — config editing surface.** The `word_budget` /
  `verbatim_turns` / `summary_enabled` fields are edited on the existing
  prompts surface, beside the `conversation_summary` template row (N2, ticket
  intake) — not a dedicated world-configuration surface, because none exists
  yet. Migrate this editing to a dedicated surface once one exists; not
  scoped to this ticket.

  Confirmed unchanged by SUPPLEMENT-0059 Amendment 5: the `cw*` functions
  (conversation-window config) migrated with the Prompts tab verbatim and
  still render inside the Prompts pane; D-0050's reactivation condition is
  untouched.

---

## STYLESHEET COVERAGE — disjointness proves no overlap, not that Creation is reachable (BRIEF-0064-a, no schema change)

`stylesheet_partition.py`'s original six rules (TICKET-0063) proved the
three destination sheets never overlap — cascade order can never decide a
conflict. They never proved the inverse: that every selector a Creation
island actually applies resolves *somewhere* the Svelte shell loads. Ten
selectors (`.app-view`, `.panel-head`, `.layout`, `.sidebar`,
`.sidebar-head`, `.conv-list`, `.right-col`, `.transcript-panel`,
`.btn-end`, `.analyze-status`) were stranded in `cockpit/index.html`'s
inline `<style>` by the time `Creation.svelte` existed to apply them —
`3fa8844` created it inside the same TICKET-0059 merge train TICKET-0063
landed alongside, invalidating RECON-0063-a's "stays inline" call for
that group the same day it was made (`RECON-0063-a-selector-audit.md`,
`## Correction (TICKET-0064)`). All nine of the original rules stayed
green throughout — disjointness and coverage are independent guarantees,
and a check that proves one says nothing about the other.

**rule7 (coverage), per applying file F:**

```
STRANDED(F) = APPLIED(F) ∩ INLINE − REACHABLE − SCOPED(F)
REACHABLE   = strict base rules in shared.css ∪ creation.css
              ∪ the built CSS bundle
SCOPED(F)   = strict base rules in F's own <style> block
```

`APPLIED(F)` is literal `class="..."`/`id="..."` markup in one
`frontend/src` file; `INLINE` is loose — any class/id name appearing
anywhere in an inline selector, descendant position included, since a
name buried in a compound inline selector is exactly as unreachable as
one at top level. `REACHABLE` and `SCOPED` are the opposite: STRICT. A
selector counts as a base rule only when its whole text is `.N` (or `#N`)
with optional pseudo-classes, pseudo-elements or self-compound classes —
`.N`, `.N:hover`, `.N.active`, `.N::before`. A descendant or compound
selector like `.parent .N` is a contextual override and proves nothing
about `N`'s base styling.

**The strict/loose asymmetry is not a stylistic choice — a loose
`REACHABLE` reproduces the exact bug this check exists to close, inside
the check itself.** rule7's first draft (BRIEF-0064-a's original
specification) had no `REACHABLE`/`SCOPED` terms at all — `STRANDED =
APPLIED ∩ INLINE`, full stop. Run against the real tree, that draft
missed a live, 24-file stranding of `.btn-send`'s base rule (Creation's
primary-action button style) entirely, because `creation.css` already
carried an unrelated compound override, `.lieux-graph-head .btn-send`,
and a loose "does this bare name appear anywhere in shared.css/
creation.css" test reads that compound rule as coverage. It is not: it
only styles `.btn-send` inside a `.lieux-graph-head` ancestor, and every
one of the 24 consumers needed the base rule that did not exist outside
the inline block. Strict matching is what makes `.lieux-graph-head
.btn-send` correctly NOT count, and is what caught the stranding rule7
was built to catch. `.btn-send` is the worked example proving the
distinction is load-bearing, not defensive over-engineering.

**`SCOPED(F)` is the fix for a false positive rule7's first draft also
produced, and RECON-0063-a already told this project why.** RECON-0063-a
flagged, report-only: "`Header.svelte` duplicates `.local-badge` under
its own scoped styling with different (hardcoded) colors than the shared
`.local-badge`... two independent implementations of one visual idea."
TICKET-0063's own decision record above says the same about `.mode-tab`
and Mode tabs. rule7's first draft, having no notion of a component's own
scoped `<style>`, flagged `Header.svelte`'s `.local-badge`, `.mode-tab`,
`.mode-tabs`, `.spacer` and `.sub` as stranded: all five are genuinely
applied under `frontend/src` and genuinely present in `cockpit/index.html`'s
inline block (which still needs them — its own, JS-suppressed legacy
header markup still carries those classes). But Svelte compiles
`Header.svelte`'s own `<style>` block into a per-component-scoped rule
set, so those elements are correctly styled independent of the inline
copy entirely. `SCOPED(F)` closes this without an exemption list: it is
computed per file, from that file's own source, and — critically — never
unioned across components. One component's own rule for `.N` must not be
allowed to cover a same-named `.N` applied by a *different* component,
or rule7 would silently stop catching the exact stranding class this
ticket exists to close.

**Class names and id names are two disjoint namespaces throughout rule7
— never unioned.** `btn-send` exists in this tree as both a class
(Creation's buttons) and an id (`id="btn-send"`, the legacy Play input's
send button, `cockpit/index.html`). Nothing cross-triggers today, but a
version of rule7 that merged the two namespaces would eventually produce
a false positive or a false negative the day one namespace's `btn-send`
diverges from the other's reachability.

**rule7 is directional, by named deferral.** It covers `frontend/src/**`
against the Svelte-reachable sheets only. The mirror direction — the
legacy document's own markup against `shared.css` plus its remaining
inline block — is unguarded. Reactivate when TICKET-0060 migrates
Observation out of the legacy document.

## SHELL HEIGHT CHAIN — one height authority, html/body -> #app -> .shell-layout -> surface (BRIEF-0065-a, no schema change)

TICKET-0059 inserted `#app` and `.shell-layout` between the shell's
full-height `html`/`body` (`shared.css:11`) and every surface's own
`flex:1; min-height:0` ladder, but gave neither wrapper a height or a
flex context. `.app-view` and `.layout` were written against a parent
chain that used to end at the legacy document's own `body` — a genuine
full-height flex column — so Creation's ladder resolved against an
auto-height ancestor and `.conv-list` never became scrollable. Play and
Observation were unaffected only because `LegacyFrame.svelte` sized its
iframe off `calc(100vh - var(--header-height))` directly: a second,
independent height authority that happened to still work because it
never depended on the wrappers at all.

This step retires that second authority instead of patching around it.
`html`/`body` stay the one source of viewport height; `#app` and
`.shell-layout` now each declare `flex:1; min-height:0; display:flex;
flex-direction:column`, carrying that height down explicitly the way the
legacy `body` used to carry it implicitly. The iframe's wrapper
(`.legacy-slot`) and the iframe itself become sized flex items in the
same chain — `LegacyFrame.svelte`'s `iframe` rule reads `flex:1;
min-height:0` instead of computing `100vh` itself. `--header-height`
keeps exactly one reader after this (`Header.svelte`'s own `height` rule)
and is kept for that reason alone, not retired.

`shell_height_chain.py` (new, same `FAILURES`/`_report_and_exit`/`ROOT`
idiom as `legacy_mount.py`) holds this structurally: rule1 fails on any
`100vh` literal anywhere under `frontend/src`, `frontend/public` or
`frontend/index.html`, comments included, so the second authority cannot
silently return; rule2 fails unless `App.svelte` declares both the
`:global(#app)` and `.shell-layout` rules with all three of `display:
flex`, `flex-direction: column` and `min-height: 0`. Both rules are
vacuous-proof: an empty file scan, or a rule that simply isn't found, is
a FAILURE, never a pass.

**`.signpost-group` (`DiscDetailsEditor.svelte`) and `.tick-controls`
(`QueueFilters.svelte`) were checked, report-only, per the brief's Scope
OUT.** Neither has a class rule in any stylesheet, but neither renders
unstyled: both carry their own inline `style=` attribute supplying the
layout that would otherwise come from a class rule (border/padding/margin
on `.signpost-group`; flex layout on `.tick-controls`). No CSS rule was
added for either.

## GRAPH MOUNT SEAM — single document, rule 11 (BRIEF-0065-b, no schema change)

`creation/mount.js` moved off the legacy document at BRIEF-0059-l, and its
own header comment (`frontend/src/creation/mount.js:11-15`) named
`graph/mount.js` as "a distinct, already-established mechanism" — an
exclusion whose premise (Creation lives in the legacy iframe) was true when
written and became false in the same merge train, with no check assuming
the governance burden. The result, live on `main` until this brief: every
`graph:slot`/`graph:invalidate` dispatch fired on the shell document while
`initGraphMount`'s listeners sat on the legacy document, so no graph ever
mounted; had one mounted, `legacyContainer(id)` would have thrown, because
all four mount targets (`relgraph-mount`, `creation-lieux-graph`,
`region-graph-mount`, `batch-graph-mount`) are `Creation.svelte`'s own
children now. Four surfaces were dead: the NPC relation graph, the Lieux
graph, and the Region and RoomBatch pre-commit previews — under a fully
green verify corpus throughout, because nothing checked cross-document
identity.

This step moves the seam fully onto the shell, mirroring the migration
`creation/mount.js` already made: `graph/mount.js` resolves containers via
`document.getElementById(id)` (throwing the same shape `legacyContainer`
used to on a miss) and `initGraphMount()` takes no document parameter,
registering both listeners on the bare `document`. `legacy/bridge.js`'s
`legacyContainer` export is deleted outright — zero importers remained
once `graph/mount.js` stopped calling it, and "no structure without a
reader" forbids leaving it exported anyway. `legacy_call.py`'s own rule9
(BRIEF-0059-l amendment) previously confined `legacyContainer` to a
two-file allow-list; that assumption ("these two names are used by the
mount seam today, so a clean scan always finds at least one importer")
broke the moment the name had zero importers left, so the same commit
drops it from `MOUNT_DOOR_ALLOWED` — the retirement's structural
consequence reaching a second check, not a second decision.

**`graph_primitive.py` rule 11 holds the seam's single-document identity
structurally**, the same way rules 1-10 hold convergence and confinement:

- **11a** — zero `legacyContainer` occurrences anywhere under
  `frontend/src/graph/`, comments included.
- **11b** — every mount target named by a `graph:` spec's `mountId` (or,
  absent that, the enclosing slot's own `containerId` — `tabs.js`'s
  `lieux` slot has no `mountId`, so its `graph:{ consumer: 'lieux' }` spec
  resolves against the slot's `containerId: 'creation-lieux-graph'`
  exactly as `onDemandSlotToggle` itself does at runtime) resolves to a
  real `id="..."` element under `frontend/src/creation/` or
  `frontend/src/graph/`. Zero mount targets collected is a FAILURE.
- **11c** — every dispatch site fires on the bare `document` or on a
  `legacyDoc` binding proven, via `creation/mount.js`'s own
  `legacyDoc: node.ownerDocument` prop, to BE the shell document; every
  `graph/mount.js` listener registers on the bare `document`. A receiver
  resolving to `legacyDocument()` or any `contentWindow`-derived document
  is a FAILURE, not a silent miss — the receiver-capture regex spans
  parens as well as word/dot characters specifically so a `legacyDocument()`
  call is captured and rejected rather than failing to match the pattern
  at all and vanishing from the count uncounted. Zero dispatch or zero
  listener sites collected is a FAILURE.

Rule 8's assertion (no scoped `<style>` on `Graph.svelte`) is unchanged;
only its rationale is corrected. It used to read "the component renders
inside the legacy iframe document, where Svelte injects scoped CSS into
the SHELL's head, where it never reaches the frame" — true before this
ticket, false after it, since the primitive now mounts in the shell and
Svelte's scoped CSS would reach it. The rule stands on a different,
durable reason instead: all graph CSS lives in `creation.css`, under
`stylesheet_partition`'s rule7 coverage; a scoped block on `Graph.svelte`
would be a second, shadow styling authority for the same selectors, not
merely inert markup.

**The generalized lesson, named explicitly because this is the second time
this ticket has found it:** a named exclusion must state the check that
assumes its governance burden, not just the reasoning that justified it at
the time — "already covered elsewhere" is only true until the "elsewhere"
changes. `creation/mount.js:23`'s exclusion of `graph/mount.js` stated no
such check; none existed to catch the premise going stale. An exclusion
justified by a state of the world (Creation lives in the iframe; these two
names are always imported by the mount seam) is invalid the moment a later
commit changes that state, and the invalidity is silent — a green corpus,
not a red one — unless some rule is written to notice the state changed,
not just to assert the exclusion's original conclusion.

---

## STATIC ASSET FRESHNESS — revalidate is the default posture, immutable is opt-in (BRIEF-0066-a, no schema change)

Bare `StaticFiles(directory=_STATIC_DIR)` emitted `etag` and `last-modified`
but no `Cache-Control`. With no explicit freshness directive a browser
applies HEURISTIC freshness and reuses a cached response without issuing a
request at all — no round trip, no 304, nothing in the Network panel.
`_serve_shell` and `serve_legacy` returned the shell document the same way,
with no cache headers either — the more dangerous half, since a cached
`index.html` names a hashed bundle filename that `emptyOutDir: true` has
already deleted from disk on the next build, so the failure mode is a 404
on the bundle and a blank page, not a stale render.

TICKET-0063/0064 moved rules out of `cockpit/index.html`'s inline `<style>`
into `shared.css`/`creation.css`. Browsers took the new hashed bundle (a
hashed filename forces a fetch) but kept the stale unhashed stylesheets: a
post-TICKET-0059 bundle rendered its DOM against pre-TICKET-0063 CSS. The
Creation surface presented as a layout defect and consumed a full RECON
session before the delivery layer — not the build, not the server, not the
checkout — was identified. A `npm run build` plus a prod-server restart
changed nothing, because the browser was asking the server nothing; a
single `Ctrl+F5` restored correct rendering immediately and permanently.

**The fix.** `_FreshnessAwareStaticFiles` (a `StaticFiles` subclass
overriding `get_response`, the stable cross-version API that also covers
the 304 path) sets `cache-control` on every `/static` response: `public,
max-age=31536000, immutable` when the request path's first segment is the
declared `_IMMUTABLE_ASSET_PREFIX` ("assets" — where Vite writes its
content-hashed build output), `no-cache` otherwise. `no-cache` means
revalidate, not "do not store": with the etag already emitted, the
steady-state cost is a 304 on two small files. **The default posture is
revalidate; immutability is the opt-in exception** — a file dropped into
`frontend/public/` tomorrow is covered without anyone thinking about it.
`_serve_shell` and `serve_legacy` now return `HTMLResponse` objects
carrying the same `no-cache` directive, so the blank-page failure mode
closes at the same time as the stale-CSS one.

**Two locked exclusions.** `shared.css`/`creation.css` keep their stable,
unhashed filenames — `cockpit/index.html` links them by fixed path and
cannot link a content-hashed asset; that constraint expires on its own at
TICKET-0061 and is not re-litigated here. Cache headers on the 151 `/api`
routes are out of scope — a middleware covering all API routes for a
static-serving concern was rejected as disproportionate blast radius; only
`/static` and the enumerated HTML shell routes carry the directive.

**`static_asset_freshness.py` holds the boundary structurally**, not as a
convention to remember: it AST-reads `app.py`'s `_IMMUTABLE_ASSET_PREFIX`,
`_IMMUTABLE_CACHE_CONTROL`, `_REVALIDATE_CACHE_CONTROL` and `_SHELL_ROUTES`
(never regex — same discipline as `legacy_mount.py`/`single_canon_write.py`),
asserts the `/static` mount's second argument is the freshness subclass and
not bare `StaticFiles`, walks `_STATIC_DIR` to assert the immutable/
revalidate partition is exhaustive with BOTH classes inhabited (a partition
with a dead branch proves nothing about the branch that is dead), and
asserts every `response_class=HTMLResponse` route — decorator-form and the
`_SHELL_ROUTES` loop-registration form alike — constructs its response with
a `cache-control` header. It is deliberately a separate check from
`frontend_build_fresh.py`: that check proves the artifact on disk matches
its source; this one proves what ships to the browser matches policy.
Merging them would make a single report line ambiguous about which
guarantee lapsed — the conflation is exactly what made the original bug
look like a CSS regression instead of a delivery-layer defect.

**The generalized lesson, its third instance:** a check that proves an
artifact is correct on disk does not prove it is the artifact the consumer
received. First seen as partition-vs-coverage (`stylesheet_partition.py`
rule7: a stylesheet can partition selectors cleanly while some are
unreachable from any live document). Second as dispatch-vs-listen
(`graph_primitive.py` rule 11, TICKET-0065: an event can dispatch on one
document while a listener sits on another, and nothing fires). Third here
as build-vs-delivery: the frontend build can be byte-correct and freshly
committed while the browser a real person is looking at never asks the
server for it. Each instance closed with a check that reasons about a
*channel* — reachability, document identity, HTTP freshness — rather than
about an artifact's own internal correctness.

---

## OBSERVATION SURFACE — shell-native migration (BRIEF-0060-a, BRIEF-0060-b, no schema change)

Observation was the last Creation-era surface still rendered by the legacy
document. BRIEF-0060-a repaired `observation_surface.py`'s Rule 1/Rule 2
anchors against the post-TICKET-0059 tree (a two-view, not three-view,
contract) before any migration began — a red test proving the repair holds
on `main` as-is, so no fail-closed guard sat red across the commit
boundary into the migration itself. BRIEF-0060-b then moved the surface
out of the legacy document entirely (`frontend/src/observation/`, two
files: `observation.svelte.js` for state/API calls, `Observation.svelte`
for template + scoped style) and re-homed the check onto the result, in
the same brief, for the same reason.

**D1 — the two stranded CSS rules move into the component, not a global
sheet.** `.r-warn`/`.r-err` lived only in `frontend/public/creation.css`;
`cockpit/index.html` stopped linking that sheet the moment TICKET-0059
retired the Creation mount (`stylesheet_partition.py` rule5 ties the
link's lifetime to `LEGACY_MOUNTS.creation`), so every Observation error
message and the no-NPC warning rendered uncoloured on `main` — a mirror-
image of the TICKET-0064 coverage bug, one direction up. Both rules have
zero consumers under `frontend/src` and are Observation-exclusive, so they
land in `Observation.svelte`'s own scoped `<style>` block: no selector is
added to the shared partition, and rule7's `SCOPED(F)` term covers them.
A red test proved the honest gap this leaves: deleting the two scoped
rules still leaves `stylesheet_partition.py` green, because rule7's
`APPLIED(F)` domain scans `frontend/src/**` only — the legacy document's
own markup (before this migration, the one place that applied these two
classes) was never in scan domain. That direction is `BRIEF-0060-c`'s
territory, not fixed here.

**E1 — full Svelte templating, no `{@html}` anywhere in the surface.** The
four legacy string renderers (`_obsRenderRunDetail`/`_obsRenderTranscript`/
`_obsRenderIntents`/`_obsLoadProposals`'s render half, each building HTML
via template literals and an `innerHTML` write) become real Svelte markup;
every `${esc(...)}` disappears because Svelte interpolation escapes on its
own. This is what makes D1 possible — Svelte's scoped-style compilation
never reaches `{@html}`-injected content, so a raw-HTML escape hatch
would have silently defeated the coloring fix. Enforced by
`observation_surface.py`'s new Rule 8, a plain-text scan of
`frontend/src/observation/**` for the literal directive.

**F1 — the world-switch bug is fixed BY the migration, not beside it.**
The legacy surface read a `WORLD_ID` global written once at document boot
(`loadBootstrap()`) and never refreshed by `activateWorldCascade`
(`creation/tabs.js`) on a Header world switch — so a run started after
switching worlds mid-session was created, silently, in the previously
active world, and its mutation proposals with it. `obsInitialized`
compounded this as a one-shot latch: the location dropdown never reloaded
either, so the stale world and the stale location list moved together,
which is why the bug produced no visible mismatch. The port carries no
local world cache at all: `startRun()` reads `serverState.worldId` at call
time, and a single `$effect` on that same field drives `reloadForWorld()`
(locations + run list reload, selection/run state reset) on every switch,
mirroring `Creation.svelte`'s own boot-and-every-switch pattern. **F3**
(the server-side half — `start_run` deriving the active world instead of
trusting `body.world_id`) is a named deferral to a ticket opened after
TICKET-0061: it is a backend write, an escalation under the frontend-only
cross-cutting rule this ticket otherwise holds to, not a silent edit
smuggled into a frontend migration brief.

**H1 — two files, not three.** ≈428 lines across 18 functions
(RECON-0060-a, PART B1/B2) fit comfortably under every module budget at
one cut; the state/template split follows the `Creation.svelte`/`tabs.js`
precedent rather than inventing a third shape. `observationState` is the
one seam the component renders — an explicit, closed field list, not a
free-form store — so a future change to what the surface tracks is a
visible diff to that list, not a silent shape drift.

**I2 — a retirement guard, explicitly not a staleness guard.**
`legacy_mount.py` Rule 4 asserted only that a registry's `showFn` exists
as a top-level function; it never asserted that function's BODY stays
consistent with the registry as sibling surfaces retire. That gap is
exactly how BRIEF-0060-a's finding (`showObservationView` still touching
`creation-view`/`mode-tab-creation` after TICKET-0059 removed both) went
undetected — `tooling/verify/run.py` only executes the checks a ticket's
own Machine-checkable section names, and TICKET-0059's section never
named `observation_surface.py`. Rule 4 now also scans each `showFn`'s
body for DOM access (`getElementById('{key}-view')`, `'mode-tab-{key}'`)
naming a surface key absent from `LEGACY_MOUNTS`, and fails closed if one
is found — a null-dereference-at-first-switch defect the moment a sibling
surface retires, invisible to every other check. This guards the
RETIREMENT step itself; the TICKET-0059 lapse was a stale check over
otherwise-correct code, a distinct failure mode that is `BRIEF-0060-d`'s
corpus gate to close.

**Environment-bearing checks stay a named gap.** RECON-0060-a's stdlib-only
container could not evaluate `observation_socle`/`observation_runner`/
`observation_metrics`/`json_ui_boundary`/`schema_*` — recorded as UNKNOWN,
never promoted to PASS. `observation_surface.py`'s Rule 5
(`json_ui_boundary` subprocess) is re-verified live in this brief's own
execution environment, not merely inherited from the RECON's container.

---

## STYLESHEET PARTITION RULE7 FAIL-OPEN + ROW CONTAINERS UNSTRANDED (BRIEF-0060-e, no schema change)

`BRIEF-0060-c`'s execution surfaced two pre-existing defects on `main`,
both unrelated to Observation, that blocked its own commit. This brief
cleared both so `-c` can resume.

**J1 — `BASE_RULE_RE`'s fail-open, and its direction.** The self-compound
branch of `stylesheet_partition.py`'s `BASE_RULE_RE`
(`(?:\.[\w-]+)*` before this fix) accepted a Svelte-compiled scope hash
as an ordinary compound class: `.spacer.svelte-13t3afu` matched and
yielded `spacer`, so every component-scoped rule leaked into the GLOBAL
`REACHABLE` set `_reachable_names()` builds — directly contradicting that
function's own docstring, which already claimed a hashed selector "fails
the strict base-rule match". Measured before the fix: the built bundle
contributed 12 class names to `REACHABLE` (`brand`, `divider`,
`legacy-slot`, `local-badge`, `mode-tab`, `mode-tabs`, `r-err`, `r-warn`,
`refusal-band`, `shell-layout`, `spacer`, `sub`), all 12 via a hashed
selector and none legitimately — the brief's own text, drafted against an
earlier build of the bundle, cites 11; the twelfth (`r-err`/`r-warn`
region aside) reflects one additional scoped rule the intervening
Observation rebuild (BRIEF-0060-b commit 5) added before this fix landed,
not a second defect. The error is directional: every one of these names
was GRANTED reachability it never structurally had, which is fail-open,
not fail-closed. A negative lookahead (`(?:\.(?!svelte-)[\w-]+)*`) refuses
the scope-hash suffix specifically; after the fix the bundle's class
contribution to `REACHABLE` is 0, verified by an in-process before/after
regex transcript and an old-branch-restoration test, with
`stylesheet_partition.py` still exiting 0 and its PASS line's five counts
unchanged. Whether a genuine compound like `.a.b` should grant a base
rule for `a` at all stays an open, unmeasured question — the lookahead
does not touch it.

Defect origin is `TICKET-0064`'s rule7 coverage formula, not
`TICKET-0060` — repaired here anyway (not deferred to its own ticket)
because `BRIEF-0060-c`'s legacy-half rule7 feeds the same `REACHABLE` set
into its stranding formula, where an over-grant flips from harmless noise
into a false stranding failure; a cross-ticket dependency would have
blocked `-c` on work outside this ticket's scope.

**K1 — row containers move to `shared.css`; membership follows
readership.** `cockpit/index.html`'s `loadPlayerKnowledge` (Play's "Mes
savoirs" tab) applies `.row-table`/`.row-card` from a JS template
literal; both were styled only in `creation.css`, which the legacy
document does not link once `LEGACY_MOUNTS.creation` retired
(`TICKET-0059`) — `stylesheet_partition` rule5 ties that link's lifetime
to the mount. Play's knowledge rows had been rendering with no card
background, border or padding since. The fix is a move, not a copy —
rule2 forbids a selector in more than one sheet, and a copy would hand
the outcome back to load order, the exact thing the partition exists to
prevent. `.row-card-actions`, syntactically adjacent to the two moved
rules, stays in `creation.css`: it has zero legacy consumers, and
`shared.css` means *both documents read this rule*, not *this rule sits
near one that both documents read*. Membership in `shared.css` follows
readership, never adjacency.

The complete legacy-stranded set measured on `main` before this brief was
exactly `classes -> ['r-err', 'r-warn', 'row-card', 'row-table']`,
`ids -> []`. `r-err`/`r-warn` left with Observation in `BRIEF-0060-b`;
this brief clears the remaining two.

---

## STYLESHEET PARTITION RULE7 (LEGACY) — coverage mirrored onto cockpit/index.html (BRIEF-0060-c, no schema change)

Rule7's original half proved `frontend/src/**` receives its visual layer;
the mirror direction — the legacy document's own markup against the
sheets it can actually reach — stayed unguarded, the gap `BRIEF-0060-b`'s
`.r-warn`/`.r-err` finding named explicitly. This brief closes it:
`_check_rule7_legacy` scans `cockpit/index.html` (static markup and the
`<script>` block's template literals alike, the `<style>` block excluded)
for `class=`/`id=` applications and asserts none is stranded.

**REACHABLE is per-document, not global.** The original rule7 unions
`shared.css`, `creation.css` and the built bundle into one global
reachable set — correct for `frontend/src/**`, which can load any of the
three. `cockpit/index.html` cannot: it links `shared.css` only (rule5
ties a `creation.css` link's lifetime to `LEGACY_MOUNTS.creation`, retired
at `TICKET-0059`), and never loads the Svelte bundle. Unioning either back
in for this half would silently readmit the exact fail-open that let
`.r-warn`/`.r-err` sit unreachable at nine call sites through the whole of
`TICKET-0059` without rule7 speaking — so `REACHABLE(legacy)` is scoped to
`shared.css ∪` the document's own inline `<style>` block, nothing else,
and Scope OUT of this brief forbids widening it to make a finding go
away.

**The intersection term is what keeps the rule honest.** `STRANDED(legacy)
= APPLIED(legacy) ∩ (creation.css ∪ bundle) − shared.css − inline` computes
the intersection against `creation.css ∪` bundle before subtracting, not
just `APPLIED(legacy) − REACHABLE(legacy)`. Without it, every purely
semantic class or id the document applies with no rule anywhere in the
codebase — eight class names measured on the current tree — would be
flagged as a false stranding. With it, the rule says precisely *this name
is styled somewhere this document cannot see*, which is the `.r-err` case
and nothing else. Class and id namespaces are computed and asserted
separately throughout (F2), never unioned, so a class and an id sharing a
literal name can never cross-trigger — verified by a dedicated red test
constructing exactly that collision.

**The retirement condition is a fail-closed alarm, not a comment.**
`TICKET-0061` empties `LEGACY_MOUNTS` and retires `cockpit/index.html`
entirely, at which point rule7 (legacy) has nothing left to guard —
"remove it once it serves nothing" is qualitative and unenforceable, the
exact shape of gap that let the TICKET-0059 lapse `BRIEF-0060-a` found go
undetected. `_check_rule7_legacy` instead evaluates the condition itself:
zero entries parsed from `LEGACY_MOUNTS` (via `legacy_mount.py`'s own
`ENTRY_RE`, imported rather than re-implemented) is a FAIL naming the
retirement explicitly, never a silent skip or a vacuous pass. The
reactivation condition for deleting the legacy half is therefore
enforced by the same fail-closed machinery as the rule itself.

**D1 execution pause, resumed after `BRIEF-0060-e`.** A correct first
implementation FAILed on unmodified `main` with five names —
`local-badge`/`row-card`/`row-table`/`spacer`/`sub` — contradicting the
brief's original "exits 0 on `main`" acceptance line, which had inferred
a clean tree from the Observation surface's 13 classes without measuring
the legacy document's 81. `row-card`/`row-table` were a genuine stranding
(K1, above); the other three were `BASE_RULE_RE`'s Svelte-hash fail-open
(J1, above) surfacing for the first time because this half feeds the
bundle scan into the *stranding* side of the formula, where an over-grant
that was harmless in the original rule7 becomes a false failure here.
Execution stopped rather than guessed at either fix — moving CSS and
loosening shared regex logic were both outside this brief's Scope OUT —
and resumed once `BRIEF-0060-e` cleared both upstream. The amended
acceptance criterion requires the check to report the computed
`STRANDED(legacy)` set explicitly, including when empty, rather than a
bare zero count a reader cannot distinguish from an unrun scan.

---

## CORPUS GATE — every check runs, or the gate is red (BRIEF-0060-d, no schema change)

**A per-ticket gate proves the checks a ticket names; a corpus gate proves
the corpus.** `tooling/verify/run.py` parses one ticket's Machine-checkable
section and executes only the checks its `-> verify/checks/NAME.py` arrows
name — correct as a per-ticket gate, silent about everything else.
`observation_surface.py` was red on `main` from the moment TICKET-0059
merged until `BRIEF-0060-a` repaired it: TICKET-0059's own Machine section
linked eleven checks and not that one, so nothing was wrong with the gate
that ran — the gate simply had nothing to say about a file outside its
ticket's arrow set. `corpus_gate.py` (B1) closes that gap one level up
from where `TICKET-0064`'s rule7 closed the same shape at the stylesheet
level ("non-duplication does not prove coverage" -> "referenced by some
ticket does not prove executed"): it discovers every `*.py` in
`tooling/verify/checks/`, runs each as a subprocess, and asserts — via an
independent re-glob taken *after* the run, not a reuse of the discovery
list — that the executed set equals the directory. Proving "some checks
passed" is a much weaker claim than proving "every check in the directory
was executed"; only the second is what TICKET-0059's lapse needed.

**ENVIRONMENT is a failure, never a skip.** RECON-0060-a ran in a
stdlib-only container lacking `fastapi`/`sqlalchemy`: four checks could not
even be imported, and one (`observation_surface.py` Rule 5, which shells
out to `json_ui_boundary.py`) reported a subprocess failure visually
indistinguishable from a genuine invariant violation. A corpus gate that
treated a missing dependency as a skip would either drown in that noise on
a bare container or, worse, quietly learn to tolerate it everywhere — the
fail-open this whole ticket exists to close one level down. `corpus_gate.py`
classifies every non-zero exit as `ENVIRONMENT` (stderr carries
`ModuleNotFoundError`/`ImportError`), `TIMEOUT`, or `FAIL`, and all three
resolve to the same red exit code — the classification exists solely for
the reader, never as a second, more lenient control path.

**Measured on this tree at BRIEF-0060-d's execution:** 83 sibling checks
discovered (84 with `corpus_gate.py` itself, self-excluded by resolved
path), 43s total wall-clock, slowest single check `prompt_version.py` at
3.22s — the per-check timeout is set to four times that (15s) with
headroom. Three genuine reds surfaced, **REPORT ONLY, left unfixed** per
this brief's Scope OUT (a brief that both builds a gate and repairs
whatever it finds has no reviewable boundary):

- `npc_goal_read.py` — `NpcGoal` imported/referenced outside its allowlist
  in `src/world_engine/observation_runner.py` and in the checks directory's
  own `observation_runner.py`. Genuine failure, needs a follow-up ticket.
- `pipeline_state.py` — three ticket files (`TICKET-0036`, `TICKET-0048`,
  `TICKET-0062`) carry a `status:` value with a trailing inline comment
  that fails the front-matter enum parse. Genuine failure, pipeline-artifact
  hygiene, needs a follow-up ticket.
- `prompt_model_write.py` — the local dev DB's `npc_dialogue`
  `prompt_template` row has zero `prompt_version` rows; the check's own
  live `TestClient` round-trip hits `prompt_store.current_prompt`'s
  fail-closed `RuntimeError`. Requires a live DB in a state this tree's dev
  database is not currently in (a migration/seed step, not a code defect
  provable from this gate alone), needs a follow-up ticket.

**No exclusion list, no baseline, no runner-mode flag.** Discovery excludes
exactly one file — itself, matched by resolved path — and any exclusion
list beyond that is the seam through which a check quietly stops being run,
the precise failure this gate exists to prevent (Scope OUT item 4). No
baseline file either: the check count grows over time and a shrink-only
baseline is the wrong shape for a set that only ever gains members (Scope
OUT item 6). `run.py` gained no `--all` flag or default corpus mode
(Scope OUT item 3) — the gate is reachable exactly the way every other
check is, through a ticket's own arrow, because a runner mode could not be
named from a `### Machine-checkable` section in the first place.

**Second occurrence of the linked-checks-only failure mode (TICKET-0077,
BRIEF-0077-b).** BRIEF-0077-a relocated six reconciliation finalizers from
`cockpit/routes/day.py` to `cockpit/day_reconcile_apply.py`; three rules in
`day_plan.py` (R12/R14/R19) still resolved them in the old file and went
red on `main` the moment that commit landed. TICKET-0077's own
Machine-checkable section linked six checks and not `day_plan.py`, and not
`corpus_gate.py` either, so `run.py` reported green on a corpus that was
not — the identical shape as `observation_surface.py`/TICKET-0059
(BRIEF-0060-a), one section up. BRIEF-0077-b retargets the three rules,
adds R22 (a location-drift guard so a future move fails as one location
message instead of three unrelated "not found" lines), and closes TICKET-
0077's own gap by adding both `day_plan.py` and `corpus_gate.py` to its
Machine-checkable section. Standing rule, now carried by two occurrences:
**every ticket's Machine-checkable section links `corpus_gate.py`** —
already recorded in `CLAUDE.md`; this entry is the second measured
instance of what happens when a ticket does not.

---

## RED GUARDS REPAIRED — goal-read accessor and prompt-model fixture (BRIEF-0067-a, no schema change)

`corpus_gate.py` (BRIEF-0060-d) surfaced two genuine, previously-invisible
reds on `main`: `npc_goal_read.py` (the observation runner selecting
`NpcGoal` directly, outside its allowlist) and `prompt_model_write.py`
(its fixture creating a versionless `PromptTemplate` head, tripping
`prompt_store.current_prompt`'s fail-closed `RuntimeError`).

**The presence probe became an accessor, not an allowlist entry.**
`observation_runner.check_run_readiness` needs exactly one boolean per
NPC — does it hold an active goal — as a run-launch precondition. Simply
allowlisting the runner for `NpcGoal` would have licensed content reads
(`description`/`horizon`/`note`) the code does not perform and nothing
would keep it that way. Instead, `npc_ids_with_active_goal(npc_ids, db)
-> set[str]` lands in `observation_reads.py` — the observation domain's
existing read module. The return type IS the structural guarantee: no
caller can reach a goal's content through this function, so the presence
need can never silently widen into a second content reader.

`npc_goal_read.py`'s `ALLOWED_MODULES` gains exactly two entries, both
relocations, never new consumers: `src/world_engine/observation_reads.py`
(a READ MODULE, definitionally a reader) and
`tooling/verify/checks/observation_runner.py` (a check fixture that seeds
`NpcGoal` rows for its own test corpus, allowlisted by name on the
precedent of `npc_goal_read.py`'s own existing entry — not a
directory-wide rule, and not a narrowed `tooling/` scan).

**Second instance of the lapsed-guard pattern.** `npc_goal_read.py` is
linked by the Machine sections of TICKET-0013/-0014/-0015/-0020/-0048;
TICKET-0051 and -0053, which authored `observation_runner.py`, link it
zero times — the same shape as `observation_surface.py`'s lapse
(BRIEF-0060-a). `verify/run.py` runs only what a ticket names; the
corpus gate is what made both lapses visible. The corpus-wide fix
(linking `corpus_gate.py` as standing law) is TICKET-0061's, not this
one's.

**The prompt-model fixture repair, and a second defect it unmasked
(D1).** The fixture now seeds its v1 `prompt_version` row through the
sanctioned write path, `writes.prompts.write_prompt_version`, inside the
check's own fresh temp-file DB — never a bare
`Session.add(PromptVersion(...))`, which `prompt_version.py`'s
single-write-shape rule would not have caught in `tooling/` regardless
(exploiting that blind spot was rejected on the same footing as writing
around it).

Fixing that crash let `prompt_model_write.py`'s `main()` run to
completion for the first time — which unmasked a second, independent,
previously-invisible failure in the same file: `check_seed_model_free`'s
`re.search(r"\bmodel\s*=", ...)` matched three comments in
`scripts/seed_pilot.py` (`:2206`, `:2227`, `:2339`) documenting the
S-null invariant in the words `model=NULL (Q1)`, not any actual
assignment. It had been silently swallowed because
`check_write_path_and_list_route()` used to crash with an uncaught
exception before `main()` ever reached its `if FAILURES:` print block.
Escalated (QUESTION-TICKET-0067.md, D1) rather than patched as a
drive-by; Nia's decision: repair it, as its own third commit, by parsing
rather than grepping. `check_seed_model_free` now walks the AST for a
`model=` keyword argument on any `upsert_prompt_template(...)` call or a
`.model =` attribute assignment, plus a `seeded == 0` vacuous-proof guard
— a rule that passes because it found nothing to inspect is the flaw
this ticket exists to close. Anchoring on a literal `PromptTemplate(`
construction was rejected (measured: zero exist in `seed_pilot.py`, 29
`upsert_prompt_template(...)` calls do, whose `**head_fields` is the
actual path a `model=` would take); stripping `#` comments before
grepping was rejected too (still a raw-text scan over a 3257-line file
holding 64 triple-quoted prompt bodies, re-tripped by future prompt text
containing the characters `model=`).

**Report-only findings, left unfixed by decision:** `context.py` sits at
979/1000 lines against `module_budget.py`'s cap — a pre-existing
condition this ticket routed around (the accessor could not live there)
rather than repaired; it deserves its own ticket. The scan-scope
asymmetry between `npc_goal_read.py` (scans `tooling/`) and
`prompt_version.py` (scans `src/` plus the migration only) — same class
of doctrine, opposite scopes — is reported, not reconciled.

With all three commits landed, `corpus_gate.py` reports exactly one
remaining failure — `pipeline_state.py` — TICKET-0061's to close.

---

## TICKET-0061 LEGACY SEAL — Play sealed not migrated, the pointer made true, the rename lands (BRIEF-0061-a, BRIEF-0061-b, BRIEF-0061-c, no schema change)

Last ticket of the seven-ticket frontend-migration series (TICKET-0055
through TICKET-0061). One supplement, appended once, for the whole
ticket — the two entries it reconciles are quoted and left standing,
never edited.

**The Play-fate contradiction, resolved.** `:10973` (the COCKPIT SHELL
entry, BRIEF-0056-a/b/c/d) reads "`play` survives to TICKET-0061 and
beyond, until its own rewrite." `:12015` (the STYLESHEET PARTITION
RULE7 (LEGACY) entry, BRIEF-0060-c) reads "`TICKET-0061` empties
`LEGACY_MOUNTS` and retires `cockpit/index.html` entirely." These say
opposite things about what happens to Play at this ticket. TICKET-0056's
reading is the one that stands: Q2 of the workstream map locked it before
either entry was written, and PART C rule 1 of that map makes the seal
ticket — the one that closes the series — structurally the wrong place to
also land the largest single migration of the series (73 top-level
functions, 2 762 lines, four sub-tabs of live play surface). Neither
entry is rewritten; this paragraph is the reconciliation, and it resolves
in TICKET-0056's favour. Decision A3 (below) is what makes that
resolution real rather than aspirational.

**A3 — Play is sealed, not migrated.** `LEGACY_MOUNTS` keeps `play`;
the legacy document stays, renamed to `cockpit/legacy.html` (BRIEF-0061-c
commit 1) but byte-untouched below the rename. Its migration becomes
TICKET-0069, deposited paused, reactivated only at Nia's request — the
3D decision is the gate (see below), not a structural condition.

**A3 and 3b, together.** Before this ticket, `legacy_mount.py`'s
`_check_retired_by` validated only the FORMAT of a `retiredBy` field
(`^TICKET-\d{4}$`) — never that the named ticket exists, never that it
isn't already `done`. A sealed `retiredBy: 'TICKET-0061'` would have been
a well-formed falsehood a green check blessed: this very ticket, still
open, named as the one that already retired Play. Rule 3b
(`legacy_mount.py`, BRIEF-0061-b commit 2) closes that hole structurally:
for every `LEGACY_MOUNTS` entry, the named ticket must exist on disk
(resolved by glob) and its `status` must not be `done` — vacuous-proof,
so a missing or unreadable ticket file is a FAILURE, not a pass. The
accessor to this guarantee is the ticket file's existence plus its
non-`done` status — nothing else makes the claim checkable. The rule is
**inexpressible** under the alternative where `retiredBy` names
TICKET-0061 itself: a rule asserting "this ticket is not done" while
executing as part of this ticket's own closure is not a rule, it's a
tautology waiting to become false the moment the ticket merges. Repointed
at TICKET-0069 (BRIEF-0061-b commit 1; `frontend/src/legacy/registry.js`,
`legacy_calls.baseline`), the pointer names a ticket this one does not
control the status of, and 3b keeps it honest for as long as TICKET-0069
stays open.

**The ratchet on the legacy document.** At 2 762 lines, `legacy.html` sits
at 2.7× `module_budget.py`'s 1000-line cap, which no baseline exempts it
from because the check never scanned `.html` files at all — a structural
blind spot, not a deliberate exemption. `function_length.py`'s 80-line
cap is escaped the same way: `sendPlayerLine` runs ~247 lines. Under A3
the document's exemption from ordinary discipline lives a year or more,
so BRIEF-0061-b commit 3 puts it on a RATCHET instead — a named constant
(`LEGACY_DOCUMENT_LINE_CEILING = 2762`) that fails the check on growth
*and* on shrinkage (instructing the constant be lowered), the same
monotonically-shrinking discipline as `LEGACY_MOUNTS` itself. The
per-function cap is a named, explicit deferral: baselining 73 functions
in a seal ticket was rejected as disproportionate to what a seal is for.
Reactivation condition: TICKET-0069, which deletes the functions rather
than baselining them.

**`legacyCall` stays — a specification error in two earlier documents,
corrected here by supplement.** Both TICKET-0067's decision table and
this ticket's own brief decomposition (`## Brief decomposition`, above)
listed "`legacyCall` removed from `bridge.js` and `legacy_calls.baseline`
shrunk accordingly" as part of BRIEF-0061-b. Measured at that brief's own
RECON: deleting `export function legacyCall` produces `FAIL: rule6:
legacyCall is defined 0 time(s) in the tree, expected exactly 1` —
`legacy_call.py` rule 6 requires the bridge primitive to exist and be
exported, independent of whether anything currently calls it. Zero call
sites in `frontend/src` is the confinement rule working (every consumer
already migrated), not dead code awaiting a purge. It dies with the
bridge at TICKET-0069, not before. Neither earlier document is edited —
this is the correction, standing beside them.

**C3's two halves, and what produced them.** TICKET-0067 found
`prompt_model_write.py` holding two independent defects where the first
crashed the process before `main()`'s `if FAILURES` block, silently
discarding the second — a check can *raise*, which is a distinct, worse
verdict than *fail*. BRIEF-0061-a commit 2 gave that a name: CRASH,
recovered via a harness that owns the checked script's globals dict and
reports whatever it had already appended to `FAILURES` before dying.
The harness's `sys.path.insert(0, ...)` restoration of the script's own
directory is load-bearing, not defensive: found by running the corpus
under the harness without it, which crashed `stylesheet_partition.py` on
its `import legacy_mount` sibling import — direct script execution puts
that directory on `sys.path[0]` and the harness must replicate it exactly
or introduce a false CRASH of its own. The second half is a declared
external-tool contract, `REQUIRED_TOOLS = ("fastapi", "httpx",
"pyflakes", "sqlalchemy", "sqlmodel")`, measured by AST import scan
across the corpus — checked via `importlib.util.find_spec` before any
check runs, reported as `ENVIRONMENT` immediately rather than letting a
missing dependency masquerade as content failures. Measured need: with
five dependencies absent, the corpus previously reported `0 environment,
0 timeout, 6 other` — six genuine defects indistinguishable from six
environment gaps in the summary line alone.

**C1.** This ticket's own Machine-checkable section links
`corpus_gate.py` (confirmed present, BRIEF-0061-a commit 3), and
`CLAUDE.md` now records as standing law that every ticket's
Machine-checkable section must do the same (`:87`). `corpus_gate.py`
itself was, until this ticket, run by no gate — TICKET-0060's Machine
section linked 13 arrows and not the corpus gate that proves all of them
are live.

**The lapsed-guard pattern, third instance.** `observation_surface.py`
lapsed between TICKET-0059 and TICKET-0060; `npc_goal_read.py` lapsed
between TICKET-0051/-0053 and TICKET-0067; the corpus gate itself lapsed
between its own authorship (BRIEF-0060-d) and this ticket, unlinked from
any Machine-checkable section the whole time. Same shape three times: a
guard is built, works, and is never wired to anything that runs it by
default. C1 is the closure — cross-referenced here, not restated; the
general lesson already has its own entry.

**TICKET-0066's exclusion has NOT expired.** `:11785` records that
`shared.css`/`creation.css` keep unhashed filenames because
`cockpit/legacy.html` (then `index.html`) links them by fixed path, and
states "that constraint expires on its own at TICKET-0061." Under A3 it
does not: the legacy document still links both stylesheets by fixed path,
unchanged. The exclusion continues, reactivating only alongside
TICKET-0069.

**D-0063-scoped-component-styles has NOT reactivated.** Its condition —
no document outside the shell consumes `creation.css` — remains false for
the same reason: `legacy.html` still links it.

**The four named deferrals, each with its reactivation condition:**

| Ticket | Covers | Reactivates |
|---|---|---|
| TICKET-0068 | Play's stale `WORLD_ID` (`loadBootstrap()` writes it once, never refreshed by `activateWorldCascade` — the defect TICKET-0060/F1 fixed for Observation) | Immediately; deposited, not paused |
| TICKET-0069 | Play's migration out of the legacy document | **Human gate.** Nia's explicit request only — horizon one year or more, tied to the 3D reactivation decision. Not a structural condition this or any check can satisfy. |
| TICKET-0070 | A `claude_md_contract.py` rule asserting symbol LOCATION (a `` `symbol` (`path`) `` claim must find that symbol in that path) | A parser existing with acceptable false-positive surface — a prototype measured ~40% noise across 8 candidate pairs; deposited paused |
| TICKET-0071 | `CLAUDE.md` hygiene pass — keep only what is law, delegate the rest; must also repair the budget itself, measurably contourned by line length (8 lines carry 30% of 45 979 characters, e.g. `:278` at 5 180 chars) | Deposited paused; no structural trigger |

**The 3D guard rail: cross-reference only.** TICKET-0055, TICKET-0056 and
TICKET-0057 each held this line at less temptation than a seal ticket
carries. Restating doctrine is how doctrine drifts. Not restated here.

## CLAUDE.MD BUDGET — characters and per-line length, not lines (BRIEF-0071-a, BRIEF-0071-b, no schema change)

Step a brought CLAUDE.md to law-only content, reclassified four
frontend invariants out of Working rules, delegated eight oversized
check-backed invariants to their primary check's module docstring, and
reflowed the whole file to a 100-character line ceiling. Step b made
that ceiling structural.

**Why a character budget replaces the line budget.** `TOTAL_LINE_BUDGET`
measured a quantity that line length defeats: at 499 lines the file held
47 084 characters, three of its lines exceeding 1 000 each, and reflowed
at 80 columns it would have run 750 lines — 150% of the 500-line budget
it was supposedly under. A number satisfiable by rewrapping is discipline
wearing a check's clothes, not a structural guard. `claude_md_contract.py`
now enforces `TOTAL_CHAR_BUDGET = 38_000` (`len(text)` on the whole file)
and `MAX_LINE_LENGTH = 100` (every line, fenced blocks included, no
exemption, each offender reported individually rather than
one-at-a-time). `FILE_STRUCTURE_LINE_BUDGET = 80` is untouched: that
section's failure mode is tree depth, which lines do measure correctly.

**Long law lives in the docstring of the check that defends it.** The
eight delegated invariants (BRIEF-0071-a) each left an obligation bullet
in CLAUDE.md naming its check; the mechanism, enumeration and rationale
moved to that check's module docstring. This is only safe if a stale
pointer fails loudly — so rule 5 (`check_py_pointer_freshness`) asserts
that every bare `\b[a-z0-9_]+\.py\b` token anywhere in CLAUDE.md resolves
to at least one file on disk by filename, excluding `.venv/` and
`node_modules/`, with zero tokens collected itself a FAILURE (step a
guarantees at least the eight delegation pointers). Without this rule,
CLAUDE.md could name a check that no longer exists and the law it
delegated would become unreachable with the gate still green.

**The archaeology ban widens to Invariants,** scoped to that section only
(`## Numbering & decisions governance` states the identifier format
normatively and must stay legal): zero `TICKET-\d` / `BRIEF-\d` matches
from the Invariants heading to the next H2. Both this rule and rule 5
carry a vacuous-proof guard — an Invariants section with zero `- `
bullets, or zero `.py` tokens found anywhere, is a FAILURE, not a pass. A
check that goes green on an empty corpus is the exact defect this project
treats as a bug.

Landing: CLAUDE.md at 496 lines / ~31 300 characters, comfortably under
the 38 000 cap with the intended headroom for future invariants.

---

## ENGINE — SQLITE WAL CONCURRENCY POSTURE (BRIEF-0072-a, BRIEF-0072-d, no schema change)

TICKET-0072: Play crashed with "database is locked" on every NPC turn. Root
cause was BRIEF-0044-f, not `play.py`. Making every SQLite transaction
explicit (`isolation_level = None` plus an engine-instance `"begin"` listener
issuing `BEGIN`) so DDL could not escape a rollback had an unintended
consequence under the default rollback journal: a `SELECT` now held a
`SHARED` lock for the life of its transaction, not just for the statement.
The Play request session, bound through `Depends(get_session)` and returned
inside a `StreamingResponse`, therefore held that lock for an entire SSE
turn. The nested `Session(engine)` persisting the NPC line
(`play.py:609-617`) could INSERT — `RESERVED` is compatible with a foreign
`SHARED` — but its COMMIT had to promote to `EXCLUSIVE`, which waited on the
request session's `SHARED`, exhausted the busy timeout, and raised. The
traceback itself discriminates the cause: the failure lands in `do_commit`,
not the `INSERT` — a competing writer fails at the INSERT, a competing
reader fails exactly at the COMMIT.

**A second, masked failure mode exists** (decision B1, out of scope here,
closed by BRIEF-0072-b): the same open transaction pins the request session
to a read snapshot. Under WAL, a pinned transaction that then attempts to
WRITE does not wait — it fails instantly with `SQLITE_BUSY_SNAPSHOT`,
reported as the identical "database is locked" text and immune to
`busy_timeout`. `play_stream.py:110`'s travel write is the one site in the
stream that hits this, and today it is invisible only because failure mode 1
kills the turn first.

**Decision (A1): `PRAGMA journal_mode=WAL` plus an explicit, declared
`PRAGMA busy_timeout`, in the existing connect listener.** One place,
structural, measured. WAL removes the reader-blocks-writer conflict at its
root — a `SHARED` reader no longer excludes a `RESERVED`/`EXCLUSIVE` writer —
without touching `PRAGMA synchronous` (stays at the durable default `FULL`;
recent commits are not traded away for throughput). `_SQLITE_JOURNAL_MODE`
and `_SQLITE_BUSY_TIMEOUT_MS` are declared as module-level constants in
`src/world_engine/db.py`, read by both the listener and the new check, so
the posture is a fact about the module rather than something someone must
remember about the database file. An unexpected `journal_mode` at connect
time raises rather than serving a Play surface that cannot persist a turn —
`_SQLITE_JOURNAL_MODES_OK = ("wal", "memory")` admits an in-memory carrier
too, since nothing in the tree binds one today but `WORLD_ENGINE_DATABASE_URL`
could.

**Rejected alternatives.** A2 (end the request session's transaction before
streaming): there are reads on `ctx.db` throughout the stream, so the fix
would survive only as a rule people remember, not a structural one. A3 (make
the explicit `BEGIN` opt-in, DDL-only): reopens BRIEF-0044-f's doctrine and
is fail-open the day a DDL path forgets to opt in; its reactivation
condition is WAL being measured unavailable or unsafe on the carrier
filesystem. A4 (one session per turn): deletes the independent commit
boundaries that keep an NPC line persisted when a later phase fails — those
boundaries are deliberate, not incidental.

**Why the nested-session persist pattern across the Play modules is legal
now, not lucky.** Eleven sites (`play.py:266`, `play.py:609`,
`play_stream.py:116`, `play_stream.py:133`, `play_physical.py:266/324/333/395`,
`play_initiative.py:203/207/250`) open a second `Session(engine)` to commit
independently of the request session. Before this brief, every one of them
carried failure mode 1 the instant the request session held any read
transaction — `play_initiative.py:200-204`'s own comment ("the SSE
generator's db session has no open write transaction at this point ... so
there is no nested-transaction conflict") states the invariant BRIEF-0044-f
invalidated, and is left uncorrected here deliberately: fixing the comment
belongs with the B1 reader audit, not this ticket. Under WAL, a read
transaction never blocks a write commit regardless of which session holds
which, which is what makes the pattern legal by construction rather than by
timing luck.

**Preserved, not traded: BRIEF-0044-f's guarantee.** `scripts/test_ddl_atomicity.py`
runs unmodified under WAL and still passes 3/3 — a forced failure between a
`CREATE TABLE` and a following `INSERT` still leaves neither the table nor
the row. Transactional DDL was never sqlite-journal-mode-dependent; it
depends on `isolation_level = None` plus the explicit `BEGIN`, both
untouched.

**New check: `tooling/verify/checks/sqlite_concurrency.py`.** AST-parses
`db.py` to confirm the posture is declared (rule 1) and referenced by the
listener; opens a real connection to confirm it is effective (rule 2);
reproduces `play.py:136`→`play.py:143` with two sessions to prove a reader
genuinely holding an open transaction (asserted at both the SQLAlchemy and
the driver level — the vacuity guard) does not block a nested writer's
commit, in under a second (rule 3); and reproduces the identical shape
against a second scratch file left in the default rollback journal, via raw
`sqlite3` with a 0.2s timeout, to prove the instrument itself can still see
red (rule 4) — a concurrency proof that never actually contends anything is
the textbook vacuous pass, and rule 4 is what rules that out. Touches only
scratch files under `tempfile.gettempdir()`, deleted (with `-wal`/`-shm`
sidecars) at start and end; never the prod or test carrier.

**Process lesson, recorded so it is not re-litigated.** BRIEF-0044-f's
verification surface was DDL, migrations and `init_db.py` — thorough within
that frame, and the frame was itself the defect. An engine-wide
transaction-semantics change alters the behaviour of every concurrent path
in the application; the concurrent paths that mattered (a streaming request
session coexisting with nested persist sessions) were never exercised. Same
shape as the "proves X, not Y" family already recorded elsewhere in this
document: proving DDL atomic does not prove ordinary reads and writes still
compose.

**The check's honest limit.** `sqlite_concurrency.py` proves a reader does
not block a writer; it does NOT prove that no path holds an open WRITE
transaction across a nested commit — WAL would not save that case either
(two writers still serialize; a pinned snapshot attempting to write is
exactly BRIEF-0072-b's E1 territory, not this check's).

**Checked and clear, recorded so it is not re-litigated:** `scripts/backup.py`
uses SQLite's online backup API (`source.backup(target)`), which is
WAL-safe — no backup change was needed. `.gitignore` already covers
`*.db-wal` / `*.db-shm` alongside `*.db`.

**E1 — the request session is read-only for the life of a streaming
response (BRIEF-0072-d).** WAL alone only relocated the crash: it stopped
one write (`play.py:390`'s join-gathering commit) from landing on a session
already blocked by a foreign reader, but it does nothing for a write
attempted on a session already pinned to a stale snapshot — `SQLITE_BUSY_SNAPSHOT`,
the same "database is locked" text, immune to `busy_timeout`. Two sites
wrote on `ctx.db` inside the SSE stream: `play_stream.py:110`
(`_perform_travel`, live-crashing the instant WAL landed, since nested
persists earlier in the same turn had already committed) and `play.py:390`
(`_join_gathering`, latent rather than live — nothing commits between the
snapshot pin at `play.py:143` and the join branch today, so it is correct
by phase ordering, not by construction). Both halves of TICKET-0072 are
load-bearing and neither suffices alone: WAL alone relocates the crash from
dialogue turns to travel turns; the session change alone leaves failure
mode 1 (a plain reader blocking a writer under the rollback journal) fully
intact. Both sites now run on a nested `Session(engine)` of their own,
never `ctx.db`, matching the eleven pre-existing nested-session sites
BRIEF-0072-a already documented.

**The autoflush finding.** Measured (scratch-DB probe, not inferred):
`Session(engine).autoflush` is `True` by default, and mutating a persistent
attribute on an object still attached to `ctx.db` — even with no explicit
`.commit()` — gets silently flushed into `ctx.db`'s own open transaction the
next time any query runs on that session. It never reaches a second
connection (nothing to contend with, so no crash), but FastAPI's dependency
teardown then rolls that transaction back on request completion since
nothing ever explicitly commits `ctx.db` again for the rest of the stream —
the mutation is silently lost, no error, no trace. An in-memory
`ctx.conv.gathering_id = ...` sync was the design this ruled out: it looks
like it avoids a write, and is actually a write with no call site,
invisible to a call-site-based check by construction. `stream_session_readonly.py`'s
rule4 forbids any `ctx.conv.<attr> = ...` (or the same through a local
alias) for exactly this reason.

**The enumeration-scope rule.** Three enumerations on this ticket were each
scoped to less than the artifact's true blast radius, and each produced a
STOP: BRIEF-0072-b assumed one request-session write site in the stream
(there were two — `play.py:390` was missed); BRIEF-0072-c, correcting that,
assumed `_join_gathering` had one caller (there were three repo-wide —
`play.py:390`, `routes/scene.py:303`, `routes/play.py:239`, one of which
pre-`flush()`es a still-pending `Conversation` specifically to obtain its id
before calling in). Neither predecessor brief is edited; both stay on disk
as the withdrawn chain (`QUESTION-TICKET-0072.md`, `QUESTION-TICKET-0072-2.md`).
The corollary this ticket records: **a brief that changes a shared
function's signature carries a repo-wide enumeration requirement — grep
across the tree, output pasted verbatim, count stated — never "confirm
there is one caller."** And the stronger corollary BRIEF-0072-d actually
acted on (decision H1): **prefer the fix whose correctness does not depend
on a complete enumeration.** `_join_gathering`'s signature, body and return
type stay byte-identical; the session boundary is owned by the one call
site that needed it (`play.py:390`, re-fetching the `Conversation` by id on
its own nested session, same idiom as `play_physical.py:324-330`'s
`ss_db.get(Conversation, ...)`), so the fix is correct regardless of how
many other callers `_join_gathering` turns out to have.

**The named condition under which `ctx.conv.gathering_id`'s post-join
staleness stops being harmless.** `player_gathering` is computed once at
`play.py:677`, before interpretation, and threaded unchanged through the
rest of the turn into `_say_initiative_phase` — so on a first-time join it
is still `None` when initiative evaluates, initiative returns early
(`play_initiative.py:61-62`), and nothing downstream reads the value
`_join_gathering` just wrote. That silence is today's safety net, not a
guarantee: **the day `player_gathering` is recomputed after the mode
dispatch, the joined id must be threaded to the initiative phase
explicitly** — `_say_join_branch` already has it in hand as `joined_id`,
returned rather than synced onto `ctx.conv` (no structure without a
reader).

---

## STANDING OCCUPATION GOALS — kind discriminator, presence not action (BRIEF-0073-b, schema v1.91)

**G2 — a discriminator column, not a second table.** NPC dialogue drifted
toward intrigue: every active `npc_goal` was a volition aimed at changing a
state, so an NPC with nothing else in its briefing played every scene as an
operator. There was no representation of what an NPC simply *does* — its
trade, its pastime, the thing that explains its presence somewhere. The fix
is `npc_goal.kind` (`volition` | `standing`), not a second table: one write
path, one prompt-assembly family, one place a diverging behaviour could
hide. Rejected: G1, a third `horizon` value (`horizon` is a temporal reach,
not a nature — both pre-existing readers already query it by explicit
equality, so a third value would have been silently invisible to every one
of them); G3, a separate `npc_occupation` table (two tables meaning "what
this NPC wants" guarantees the two write paths and two prompt renders
diverge over time). `kind='standing'` implies `horizon='long'`, enforced by
`ck_npc_goal_standing_horizon` — defence in depth, not the primary
mechanism: every in-scene reader (`context.py::_npc_context_goals`,
`tick_context.py::_tick_goals_block`, `play_initiative.py::
_initiative_candidate_data`, `cockpit/mutations.py::
_mutation_goal_change_close`) filters on `kind` explicitly, and the CHECK
only catches a future reader that forgets to.

**M1 — a reason for presence, never a current action.** Nia's objection,
verbatim from intake: a briefing that asserts "what you are doing right
now" is re-injected unchanged on every turn while the scene moves on — the
NPC is told at turn 14 it is still whittling, and loops instead of
advancing. `assemble_npc_context` receives no history and is rebuilt from
canon on every call, so a `kind='standing'` row is stable across a whole
scene by construction; the objection is therefore about the framing, not
the field. The fix: the new `POURQUOI TU ES ICI` section states a REASON
FOR PRESENCE, which stays true for the whole scene, while the moment-to-
moment gesture stays exactly where it already lives — the conversation
history the model already receives. The section's own fixed sentence makes
the precedence explicit: *"Si la scène t'a déjà écarté de cette occupation,
la scène prime."* Rejected: M2, first-turn-only injection
(`assemble_npc_context` has no turn index and seven call sites, two of
which have no notion of a turn — reactivate this if the live gate shows the
NPC looping on its occupation across a long scene); M3, continuously
rewritten activity (would need either a model call per NPC per turn or a
parse pass over generated prose, plus a WRITE inside the stream — the exact
shape of the TICKET-0072 `database is locked` regression — and would build
a second, competing source of truth about what an NPC is doing, when the
scene history already tracks it for free).

**N1 (initiative) extended, not re-litigated.** The standing goal DOES
reach the initiative vote, as its own fragment (`standing_by_npc`,
`ici pour=`), never merged into the existing short-goal pool — that pool is
collapsed to one string per NPC via `setdefault`, so admitting the
occupation there would silently suppress one of the two by creation date.
An NPC held by its post and an NPC at leisure in its own room now read
differently to the vote, which is exactly the signal it lacked before.

**E1 — creator CRUD only, this ticket.** No model authors a standing row in
v1: `generate_npc_goals` is not extended, no new mutation type exists, and
`_mutation_goal_change_close`'s candidate pool now excludes `kind='standing'`
— closing the one path (a `goal_change` whose text happened to match an
occupation's description) by which a model-proposed mutation could have
reached a standing row. The Creation-side editor (BRIEF-0073-c) is the only
way to create or close one.

## STANDING OCCUPATION EDITOR — one selector deriving the pair (BRIEF-0073-c, no schema change)

**O1 — a single `(kind, horizon)` choice, not two independent fields.** The
`GoalsEditor` add form offered one `horizon` `<select>` before this step;
`kind='standing'` requires `horizon='long'` (`ck_npc_goal_standing_horizon`,
BRIEF-0073-b), so a second, independent `kind` control would let the
creator form the one pair the CHECK refuses. The form instead offers three
labelled choices — COURT TERME / LONG TERME / OCCUPATION — mapped through a
single `CHOICE_TO_PAIR` constant to the `(kind, horizon)` pair the backend
receives; there is no second control from which the two could be chosen
independently. `crud/goals.py::create_goal` validates the pair server-side
regardless (`kind == "standing" and horizon != "long"` -> 422) — the
structural guarantee; the single-selector shape is what keeps the creator
from meeting that 422 in normal use, not what enforces it. Rejected: O2,
two independent controls plus the existing CHECK (exposes the combination
the CHECK refuses, so the creator meets a 422 instead of being unable to
form the pair at all); O3, forcing the pair in the component without a
named mapping constant (the coupling would live in ad hoc conditional
logic, invisible to a structural check and silently bypassed by any second
caller of the same route).

## NPC SCHEDULES — background versus foreground, two-branch precedence, the world's phase (BRIEF-0074-a, BRIEF-0074-b, BRIEF-0074-c, schema v1.92)

**J1 — a schedule is background, an agenda is foreground; one accessor.**
TICKET-0073 gave an NPC a standing occupation (a reason to be somewhere) but
nothing said WHERE that somewhere is, or WHEN. `npc_schedule` is the
positional expression of that background disposition: `npc_id`, `phase`,
`location_id`, a nullable `standing_goal_id` back-pointer to the `npc_goal`
row it explains. It is read through exactly one accessor, `schedule_reads.
where_is`, on the earshot precedent (one code path, not a scatter of ad hoc
lookups). Rejected: J2, a schedule as a recurring agenda (an agenda has a
terminal status and at most one active step; a routine has neither — forcing
the shape would mean an agenda that never terminates, which the agenda
machinery elsewhere assumes cannot happen); J3, last-known position only
(`character.current_location_id` alone) — a fact about right now that says
nothing about a phase three days out, the exact gap this table exists to
close.

**C1 — time-relative precedence, two branches, one accessor.** A present
phase resolves a set of FACTS (a roster, a stored location); a future phase
resolves a set of PREDICTIONS, where `current_location_id` is only a last
known position and must never beat the schedule. `PRESENT_PRECEDENCE` =
gathering > current_location > schedule > unknown; `FUTURE_PRECEDENCE` =
schedule > last_known > unknown. Both are module-level tuples in
`schedule_reads.py`, dispatched through a name-keyed `_SOURCE_LOOKUPS` table
that `where_is` iterates performing no lookup of its own —
`verify/checks/npc_schedule.py` asserts the bijection between tuple names
and lookup keys, and that `where_is`'s body contains no `select(` call.
Rejected: C2, a single total order (would let a stale `current_location_id`
beat the schedule for a phase three days out — the exact failure this table
exists to fix); C3, schedule-always-wins with overlays at call sites
(violates J1: a background default cannot outrank a live fact like gathering
membership without inverting which one is background).

C1 originally named a third term, `agenda_step`, in both branches. Execution
of BRIEF-0074-a's mini-RECON (item 13) found no location column reachable
from `AgendaStep`, `Agenda`, or `NpcGoal` — STOP fired correctly, and Nia's
resolution (AMENDMENT-1) removed the term BY DESIGN rather than deferring
it: an agenda states an OBJECTIVE, never a place, and giving it one would
create a second positional authority competing with `npc_schedule`. An
agenda's positional consequence already reaches `where_is` some other way —
the tick moves the NPC via `write_character_location`, and the present
branch's `current_location` term reads that fact one rank above the
schedule. There is no reactivation condition: a future predictive term
comes from whatever the day-resolution chain emits, as a new named term,
never resurrected from an agenda. See
`tooling/briefs/BRIEF-0074-a-amendment-1-no-agenda-term.md` for the full
correction.

**T-A1 — the world's phase is a bare creator-set column, with two riders.**
Nothing in the tree named a current phase (`current_phase` grep returned
zero hits pre-ticket) and `World` carried no temporal state, yet C1's
present/future split and the coming L1 concordance both need one. The fix,
`world.current_phase` (four-value CHECK, default `'matin'`), rides with two
non-optional conditions: (1) a forgotten phase mis-renders L1 *silently*,
which the doctrine refuses as a disciplinary safeguard — the compensating
control is the phase displayed permanently in cockpit chrome (BRIEF-0074-b),
so "forgotten" is visible rather than mute; without that display, deferring
L1 entirely would have been the correct call instead. (2) Advancing the
phase moves nothing else — a bare state write, no tick, no cascade, no
recomputation; the day-resolution chain stays Scope OUT of this ticket.
Per-world by construction: two worlds are two `world` rows, so two
independent phases, with no rule anyone has to remember. Rejected: T-A2,
derive from wall-clock time (couples fiction to real time; the engine is
turn-based); T-A3, phase on `conversation` (cannot be the only source — the
Creation-side `who_is_at` panel has no conversation; kept non-foreclosed: a
`conversation.phase_snapshot` stays a possible additive migration later);
T-A4, defer L1 entirely (the real contender, retained as the fallback if
condition 1 above is ever dropped).

**S-I1 — no `change_history` on `npc_schedule`.** A schedule row is a
standing DEFAULT, not a narrative event — the same curated-config family as
`location_type_catalog`/`world_law` (`write_location_doors` precedent: full-
replace per NPC, delete-then-insert in the caller's transaction). "History
is sacred" protects narrative artifacts; a model-authored `schedule_change`
mutation, when it exists, is what would need its own trail — deferred with
auto-approve (S-F) to a separate ticket that needs a real proposer.

**T-C1 — the NPC sheet authors, the location sheet reads.** `ScheduleEditor.
svelte` (mounted on the NPC sheet, after Objectifs — an occupation is the
reason, a schedule is the where, so they read in that order) authors all
four phases of one NPC's day at once, full-replace through
`PUT /api/entities/{id}/schedule` -> `write_npc_schedule`, matching E1's
per-NPC write shape and matching how a creator actually thinks: one authors
a character's day, not a location's footfall. `SchedulePanel.svelte`
(mounted on the location sheet) is the read-only mirror. The two surfaces
never overlap: authoring a schedule and verifying its footprint are
deliberately different screens, on the `GoalsEditor`/`goalsPanel.svelte.js`
split (component owns markup, `schedulePanel.svelte.js` owns state and
requests through `sheetRequest.svelte.js`) — neither component receives
schedule rows as a prop from `Sheet.svelte`'s own `detail` (confirmed
absent from `crud/entities.py::get_entity`'s response), so both load their
own data, the same shape `GoalsEditor` already uses. Rejected: T-C2, author
from the location sheet (each edit would touch one cell of one NPC's day,
fighting the full-replace write shape); T-C3, ship the read panel and CLI
only, defer authoring (leaves Nia unable to create a schedule except by
hand, breaking the live-gate loop this brief exists to unblock).

**F1 as B1's compensating control, structurally enforced.** B1 made
`npc_schedule` sparse by decision and refused a coverage check (inventing
canon by rule). `SchedulePanel.svelte`'s four phase groups (via
`GET /api/locations/{id}/schedule`, which calls `who_is_at`/
`unresolved_npcs` per phase with a server-computed `is_present` — the one
phase matching `world.current_phase` resolves through
`PRESENT_PRECEDENCE`, the other three through `FUTURE_PRECEDENCE`) render
visibly empty rather than omitted, and the panel's own `unresolved` block
names every NPC that resolves nowhere. This is a REPORT, not a gate: no
required-field validation, no save-blocking badge. The panel's read-only
posture is not a docstring promise — `verify/checks/npc_schedule.py`'s R9
asserts no POST/PUT/PATCH/DELETE method literal appears in
`SchedulePanel.svelte`'s own source, on the same "structural, never
disciplinary" doctrine as the rest of this ticket.

**T-A1 condition 1, closing the loop.** The phase control lives in
`Header.svelte`, not inside the Creation tab — `Header.svelte` is mounted
unconditionally by `App.svelte`, outside every surface's own gated
container, so it is the one component visible from Play, Création and
Observation alike. The current phase renders as persistent text next to a
`<select>` that calls `PUT /api/world/phase`; R4b (`verify/checks/
npc_schedule.py`) asserts that handler's body calls nothing beyond its
world-resolution helper, its validation helper, `db.add`/`db.commit`, and
its response builder — condition 2 (advancing the phase moves nothing
else) made structural rather than documented, the same shape R9 gives
condition 1's read-only panel.

**L1 — the occupation is earned by concordance, not shown unconditionally.**
TICKET-0073 shipped `POURQUOI TU ES ICI` unconditionally: any NPC carrying a
`kind='standing'` goal rendered its occupation in every scene, everywhere —
an innkeeper met in a forest at midnight still explained itself as an
innkeeper on duty, collapsing J1's background/foreground distinction. L1
gates the render on a new `_standing_is_concordant(npc_id, location_id,
session)`: the active world's `current_phase` feeds `where_is(npc_id,
current_phase, session, is_present=True)`, and the section renders only if
that resolution's `location_id` equals the scene's own `location_id`.
Deliberately NOT `resolution.source == "schedule"` (rejected L3): in a live
scene with the player the NPC is in a gathering, so the present branch
resolves via `gathering` every time and that test would never fire. It is
the LOCATION that must agree, not the winning term — a schedule-driven
gate would be structurally correct but never demonstrable in the one
context (a live conversation) `_npc_context_standing` runs in.
`_npc_context_standing` gained `location_id` as a parameter, drawn from
`assemble_npc_context`'s own — no new parameter on `assemble_npc_context`
or any of its seven callers. `verify/checks/npc_schedule.py`'s R12 proves
the test is REACHED, not merely defined: `_standing_is_concordant` exists
and references `where_is`; `_npc_context_standing` calls it;
`assemble_npc_context` calls `_npc_context_standing` with >= 3 positional
arguments; `_npc_context_standing` keeps exactly one call site in `src/`.

Because C1's present branch ranks `gathering` and `current_location` above
`schedule`, and a live scene's NPC is normally a member of an open
gathering at that same location, the schedule term is usually never
reached during ordinary play — concordance holds via `gathering` instead,
and only fails when the scene's `location_id` genuinely disagrees with
where the NPC currently, factually, is. The schedule term decides
concordance only for an NPC with neither an open gathering nor a
`current_location_id` matching the scene — e.g. a freshly authored NPC, or
one reached outside a live gathering. This is C1 holding as designed, not
an L1 gap: advancing `world.current_phase` alone, with nothing else moved,
will not hide the section for an NPC the player is presently gathered
with, precisely because condition 2 (advancing the phase moves nothing
else) forbids the gathering itself from following the clock.

**An unscheduled NPC loses the section TICKET-0073 gave it unconditionally
— intended, not a regression.** An NPC with a standing goal and NO
`npc_schedule` row for the current phase resolves to `source="unknown"`,
`location_id=None` (T-D2's terminal), which never equals a real scene
location, so `_standing_is_concordant` returns `False` and the section is
withheld. Every NPC without an authored schedule is in this state until one
is written (B1 leaves the table sparse), so this reads as correct behaviour
on every pre-existing NPC rather than a bug — recorded here because it is
the criterion most likely to surprise on first live-gate pass. The
initiative vote's standing fragment (TICKET-0073, N1) is untouched by this
gate: L1 withholds the dialogue section only.

## DAY DECLARATION SOCLE — the day is the batch, an explicit ordinal, a new surface (BRIEF-0075-a, schema v1.93)

**L1 — the day IS the batch; the day number is its ordinal.** No new world
column: `Batch` already existed (declared since the pipeline package split)
but had never had a reader, a standing "no structure without a reader"
violation this step clears. Rejected L2 (`world.current_day` — a second
temporal authority beside the deliberately inert `current_phase`) and L3
(no day counter, everything relative — fragile as soon as a rendezvous is
at D+2).

**U1 — the ordinal is an explicit column, unique per session.**
`Batch.day_number: int NOT NULL` plus a unique index on
`(session_id, day_number)` — decided over U2 (derive by row number over
`created_at`: no migration, but the ordinal is never stable — a deleted or
reordered row would renumber every day after it) and U3 (reuse
`Session.number`, one batch per session: a session is a period of PLAY, not
a world day, and `cockpit/play.py`'s `_get_or_open_session` already creates
sessions for live conversations — collapsing the two would make a
conversation and a declared day compete for the same counter).
`writes.write_batch` is the sole allocator (`max(day_number) + 1` per
`session_id`, or `1` for a session with none); no update path exists.

**Q1 — a new, minimal Svelte surface, independent of Play.** `Journée`
(`frontend/src/journee/`) is a sibling of `Creation`/`Observation`,
following the same `active`-prop mount pattern (declare / read the
account only — no legacy bridge call). Rejected Q2 (grafting onto legacy
Play — adds legacy after the TICKET-0061 doctrine seal) and Q3 (API only —
the chain could not be PLAYED). A rendezvous conversation still runs in
the legacy Play surface until TICKET-0069; this brief's surface is
declaration-only and reads no agenda.

This step is PLUMBING ONLY: `POST /api/day/declare`, `GET /api/days`,
`GET /api/day/{id}` (new `cockpit/routes/day.py`) store and read back a
declaration; nothing resolves, and no model is called anywhere in this
brief. `declared_action` is write-once by construction (`writes/pipeline.py`'s
`PassPlay(...)` constructor is the only site that ever sets it) —
resolution, plan emission, concordance and narration are later briefs,
tracked as decisions I1 (rendezvous is a pointer, not a scene) and the
open mutation-type/budget/rewrite-guard questions still gating them.

---

## DAY PLAN EMISSION AND BUDGET — model proposes, code judges (BRIEF-0075-b, schema v1.94)

**F1 — one model emission, Python cut.** `day_plan.emit_plan` makes exactly
ONE call: the model proposes the FULL ordered step list for a declaration:
every downstream decision (which requirements are met, how many steps
happen today) is Python. Rejected a multi-turn plan-then-refine loop —
unnecessary latency and a second place a plan could silently drift from
what the player declared.

**M1/P2 — the four `SCHEDULE_PHASES` ARE the budget; the phase is never
read.** `DAY_BUDGET_SLOTS = len(SCHEDULE_PHASES)`, derived rather than
written as `4` (a future fifth phase widens the budget for free). Every day
gets the full budget regardless of `world.current_phase` (P2) —
`day_plan.py` reads no `current_phase` anywhere and performs no `select(`
against `NpcSchedule`; positional/schedule reads stay exclusively in
`schedule_reads.py`.

**S1 — four requirement forms, one named evaluator each, closed by a CHECK.**
`agenda_step_requirement.type IN ('knowledge','relation_gte','resource',
'location_reachable')`, and a SECOND CheckConstraint
(`ck_agenda_step_requirement_shape`) enforces the per-type shape at the row
level — an ill-formed row (e.g. `relation_gte` with a NULL
`target_entity_id`) cannot exist, full stop, not by evaluator discipline.
`day_plan._EVALUATORS`'s key set is asserted equal to `REQUIREMENT_TYPES` in
both directions (`day_plan.py`'s R1, the `_SOURCE_LOOKUPS` bijection
precedent) — widening the vocabulary without adding an evaluator fails
loudly, at `evaluate_requirements`'s fail-closed unknown-type branch AND at
verify.

**H1 — a plan reuses `Agenda`/`AgendaStep`, deliberately.** `agenda_step`
gains two nullable columns (`cost`, `domain`) rather than a parallel
`day_plan_step` table — NULL for every pre-v1.94 (NPC) step, since a plan
IS a plan: an NPC's agenda and a player's day plan are the same shape, one
step at a time, one active at once (the existing partial unique index,
unmodified, is still the whole guarantee). The alternative (a bespoke table)
would have duplicated `step_order`/`status`/`change_history` for no
structural gain.

**THE POSITIONAL WALL HOLDS (BRIEF-0074-a-amendment-1) — reaffirmed, not
merely inherited.** `agenda_step` gains NO location column even though this
step's budget metadata rides on the same row; `location_reachable`'s target
lives on `agenda_step_requirement`, a REQUIREMENT row, never on the step —
"the player must be able to reach L" is a precondition on the player, never
a position of an NPC. `day_plan.py`'s R6 (`tooling/verify/checks/
day_plan.py`) is the single most important check in this brief: no
location-named field on `Agenda`/`AgendaStep`, and `schedule_reads.py`
references neither `Agenda`, `AgendaStep` nor `AgendaStepRequirement`.

**The `location_reachable` reader — an escalation, corrected.** The original
brief instructed "reuse the existing traversal; do not write a second one."
That instruction was wrong: it directly contradicted decision **D1
(BRIEF-19)**, standing doctrine that each new `connects_to` consumer gets
its OWN reader (a real dedup opportunity is REPORTED, never acted on — see
the `connects_to` convention section and every reaffirmation since,
`_location_neighbours` through `spatial_doors.py`). Claude Code stopped
under the brief's own STOP condition rather than guess; the correction is
`tooling/briefs/BRIEF-0075-b-amendment-1-location-reachable-reader.md`.
`day_plan._day_reachable_ids` is a NEW, day-local BFS over `connects_to`
among ACTIVE locations — unbounded (a day has no meaningful hop radius,
unlike the tick's interval bound) and origin-INCLUSIVE (the player being
already there satisfies reachability — the concrete shape difference from
`_reachable_locations`, which excludes the origin, meaning sharing would
have been wrong on the merits and not only on doctrine). Measured at
amendment time: roughly the SEVENTH independent `connects_to` reader in the
tree (`_location_neighbours` `cockpit/play.py:854`; `_reachable_locations`
`tick_context.py:405`; `write_location_doors`'s B1 gate
`writes/config.py:275`; `spatial_doors.py:60-62`;
`spatial_author._live_neighbour_ids`; `room_batch_author.py:141`) — D1
reaffirmed in a code comment at each addition, count still rising, still not
acted on. `tooling/verify/checks/day_plan.py`'s R10 makes the
non-reuse structural for this consumer rather than a comment convention:
`day_plan.py` imports none of the sibling readers and is asserted to declare
its own loop referencing `connects_to`.

**Reported, not acted on (D1's own posture, applied to this brief):**
(1) the dedup count above; (2) this archive's own `connects_to`-convention
section and the L1/BRIEF-16 travel-model note cite reader locations
(`cockpit/app.py`, `tick.py`) that have since moved (`cockpit/play.py:854`,
`tick_context.py:405`) — same check-anchor drift class as TICKET-0027's;
retargeting those anchors is TICKET-0071 hygiene territory, not this
brief's; (3) a "proves X, not Y" gap this step introduces and does not
close: `_day_reachable_ids` proves a path exists in the `connects_to` graph;
it does NOT prove the Play surface's door/travel gate would let the player
actually walk it. Harmless today — the day chain resolves travel
abstractly, and Play is sealed (TICKET-0061) — and worth a fresh look only
if a future ticket ever routes a day step through Play.

Scope OUT, named explicitly so a later brief doesn't assume otherwise: no
`resolve_physical` call anywhere in this step (BRIEF-0075-d);
no `proposed_mutation` row is written (BRIEF-0075-e); the emitted plan's
`requires` items are restricted, at the PROMPT level, to `knowledge`/
`resource` (target-key-based — no entity resolution needed); `relation_gte`/
`location_reachable` have full evaluators and write-path validation but are
not yet reachable from a live declaration, because extraction/concordance
(name -> entity id) is BRIEF-0075-c's job, not this one's. `POST
/api/day/{batch_id}/plan`'s response carries neither `agenda_id` nor
`step_id` — the player never sees the agenda.

---

## EXTRACTION AND CONCORDANCE — the resolver never authors (BRIEF-0075-c, no schema change)

**C1 — the whole shape.** A day plan is emitted against the player's raw
words: "find whoever stole the guild seal" names a faction and an object,
and implies a fence, a district, a contact — none of it resolved to canon.
This step resolves it, and the ONE rule governing every path through it is:
**the resolver never authors.** On a match it uses the canon id. Failing
that, the day names a FUNCTION WITHOUT IDENTITY ("a flower seller set up
near the east gate") and emits an `entity_creation` germ carrying the hint —
the SAME parked-germ mechanism BRIEF-0019-a built for the tick
(`_approve_entity_creation_shortcircuit`, byte-identical here: approval
PARKS, it never authors synchronously). The NPC becomes canon only when Nia
realises it in the Creation tab; at that moment it was already there,
narratively free.

**Two-model, one-code shape.** Three SEPARATE extraction passes
(`day_extract.py`: `extract_places`/`extract_persons`/`extract_factions`,
usages `day_extract_place`/`day_extract_person`/`day_extract_faction`) read
the declaration and a compact, secret-free world frame
(`World.name`/`.description` — no per-entity query backs it, so nothing else
can leak through it) and return `Mention`s: `surface_form` (the player's
words), `kind` (`named`|`inferred`), and for `inferred` mentions a
`role_hint` (the FUNCTION needed). **They never see the registry** — R2
(`tooling/verify/checks/day_concordance.py`) asserts no `select(` in
`day_extract.py` references `Entity`, `Faction` or `Location`. Handing a
model the registry invites it to invent a plausible id; matching stays
Python, against real rows, in `day_concordance.py` — "another AI with the
full registry" from the design conversation, resolved to code, which is
strictly better: a lookup cannot hallucinate an id.

**Four matching rungs, tried in order, stopping at the first hit**
(`day_concordance.MATCHING_RUNGS`, dispatched through `_RUNG_LOOKUPS` — the
same one-tuple/one-dict idiom as `schedule_reads.PRESENT_PRECEDENCE`/
`_SOURCE_LOOKUPS`, bijection-checked by R6):
1. `named_exact` — `surface_form` against entity names in the active world,
   case-folded, scoped by `Entity.world_id` at query construction.
2. `named_alias` — an alias/cover-role surface. Measured: none exists.
   `faction_membership.cover_role` is a faction ROLE label (a title), never
   a person's name — using it here would conflate "what someone is called"
   with "what someone is called *by their faction*." This rung is a
   structural no-op, reported once as skipped, per mention, NOT built for
   the occasion (Scope OUT: alias infrastructure).
3. `occupation` — persons, `inferred` only: `role_hint` keywords (casefolded,
   stopword- and length-filtered) against STANDING goals
   (`npc_goal.kind='standing'`) reached through
   `npc_schedule.standing_goal_id` — **the occupation index** landed by
   TICKET-0074. "Who is a flower seller" is answered by joining a schedule
   row to its standing goal, never by reading free text elsewhere. Goal
   `description` text is compared in Python and never leaves this module:
   only the resolved entity id (never goal content) reaches a payload, a
   response, or a model prompt — `npc_goal_read.py`'s allowlist grew by this
   one READ MODULE, same precedent as `observation_reads.py`, because N1's
   real concern (goal content leaking into a prompt) does not apply to an
   id-only consumer.
4. `presence` — persons, `inferred` only, only when a PLACE mention already
   matched within the SAME `concord()` call: `who_is_at` (the one sanctioned
   positional read, `schedule_reads.py`) swept across all four
   `SCHEDULE_PHASES` for each matched place. Consumed through the public
   accessor only — no new precedence term, no edit to `where_is`'s dispatch
   (Scope OUT, defended by R4's constructor scan).

**Ambiguity is reported, never resolved by picking.** Two or more equally
good candidates at any rung is `ambiguous`, carrying every candidate id — the
mention is treated as unmatched for germ purposes (no germ) but reported
distinctly, so Nia sees the engine hesitated rather than failed. Measured in
execution: a place-scoped `presence` rung can widen past two candidates (a
busy tavern scene) — "two or more" is the real rule, not "exactly two."

**Persons only; places and factions are reported, never germinated.** A
location germ drags in the location tree, doors, geometry and four
fail-closed checks — explicitly deferred to a location-symmetry ticket. A
faction the player invents is a misunderstanding to surface, not an entity
to create. `emit_germs` filters `mention.category == "person"` before
constructing a single `ProposedMutation` — R3 asserts every constructed row
sets `source_type='pass_play'`, `mutation_type='entity_creation'`,
`status='proposed'`, and nothing else.

**The germ payload matches what the Creation tab actually reads.** Measured
from `list_pending_creations`/`generate_creation_draft`
(`cockpit/routes/creator.py`): `entity_type` (`"character"`), `name`
(falls back across `name|title`), `concept` (`concept|description|content`),
`anchor`. The germ payload carries all four PLUS `role_hint`,
`surface_form`, `kind`, and `candidate_location_id` — the anchoring context
concordance had, even when rung 4 tried and missed. `rationale` states which
rungs were tried and missed, so a germ reads as reviewable, not mysterious.

**Writes split by construction, not by convention.** `day_concordance.py`
contains no `db.add(`, no `.commit(`, no `chat(` (R1) — `concord` and
`emit_germs` return objects; the route (`cockpit/routes/day.py`,
`_extract_and_concord`) adds them to the session. Germs commit in the SAME
transaction as the plan — all-or-nothing: an extraction or concordance
failure reports and stops before anything is staged, matching the existing
`write_day_plan` all-or-nothing convention rather than inventing a second
one.

**The plan receives resolved context as text, never as a template
placeholder.** `day_plan.emit_plan` gained a `concordance_summary: str = ""`
parameter (`day_concordance.plan_context` builds it), appended to the user
message in code — deliberately NOT woven into the seeded `{declaration}`
template via a new `{concordance}` placeholder. S2 (prompt text is
append-only, locked after v1) means a placeholder added to
`DAY_PLAN_USER_TEMPLATE`'s source would be inert on any already-provisioned
world; appending in code sidesteps that entirely and needs no reseed. A
matched mention reaches the model as a resolved name; an unmatched person
reaches it as a role — never a canon id the model could misuse, since
`relation_gte`/`location_reachable` requirements stay out of the model's
reach (BRIEF-0075-b's own forward note, honored: no requirement-schema
wiring lands here, only prompt-facing text).

**Response shape.** `POST /api/day/{batch_id}/plan` gains a `concordance`
block: matched mentions with resolved display names, ambiguous ones with
candidate counts, unmatched ones with role hints and germ ids. Entity ids
for MATCHED mentions may appear; germ ids may appear; no `agenda_id`, no
`step_id` — unchanged from BRIEF-0075-b's posture, reasserted by
`pipeline_wiring.py`.

Verified live (not only by the check suite): a canned-model smoke run
against a seeded world confirmed rung 1 (named place and person), rung 3
(a planted `standing` goal resolving a French role hint), an `ambiguous`
outcome from a busy-tavern `presence` sweep, and the full germ lifecycle —
construct, approve, PARK — with the world's `entity` row count asserted
unchanged before germ emission, after germ emission, and after approval.

## RESOLUTION, FACT SHEET AND NARRATION — the prose renders, it never decides (BRIEF-0075-d, no schema change)

**The whole shape, restated from the brief because it is the point.** Dice
are Python (`resolve_physical`, unchanged since BRIEF-11). Banding and
truncation are Python. The fact sheet is Python, frozen once, never
mutated. Only THEN does a model write prose — and even then it receives
the fact sheet, never the registry, never the DB. A judge (also Python)
verifies the prose against that same fact sheet before anything is stored.
Every stage after the dice roll can only render or reject what the dice
already decided; none of them can originate a fact.

**`resolve_steps` re-derives the plan from the DB on EVERY call, not once
at plan-emission time.** `day_resolve.py` reloads the character's active
`Agenda`'s `agenda_step`/`agenda_step_requirement` rows, reconstructs
`day_plan.PlanStep`/`RequirementSpec`, and re-runs the SAME
`evaluate_requirements`/`budget_cut` pair `day_plan.py` uses at emission
time — never a cached in-memory plan. This is what makes a REPLAY
(Scope IN item 5) a real re-resolution rather than a re-render of stored
dice: `POST /api/day/{id}/resolve` on an already-`resolved` `pass_play`
re-evaluates every requirement against CURRENT world state and re-rolls
every included step, and `write_agenda_step_status`'s existing
snapshot-before-overwrite discipline means the previous attempt's
`{status, outcome, updated_at}` survives in `agenda_step.change_history`
— a step can flip from `completed` to `failed` between two resolves of the
same day, and both attempts are readable.

**Superseded by AMENDMENT 1 (V1), below.** The rest of this paragraph
described `persist_step_outcomes` writing every `agenda_step` transition
directly through `write_agenda_step_status` on every `/resolve` call.
That function no longer exists: `resolve_day` now only computes
`StepOutcome`s and emits `ProposedMutation` proposals
(BRIEF-0075-e/`day_mutations.py`); `AgendaStep.status`/`.outcome`/`.
change_history` move only once Nia approves one. A replay still re-rolls
every included step fresh each call (`resolve_steps` re-evaluates from
`step_order` 1 every time, unchanged) — but two resolves of the same day
now emit two independent sets of proposals rather than two direct writes,
and only proposals matching canon's actual current step state apply
cleanly (the ordered-approval consequence, see AMENDMENT 1).

**D2 (NPC opposition tier) resolves to a constant, not a second
derivation.** `play_physical.py`'s live-Play precedent derives `npc_tier`
from `character.physical_tier` when a turn is opposed by a specific NPC —
but neither `agenda_step` nor `agenda_step_requirement` carries an
opposing-NPC id; a day-plan step names no opponent. `_step_player_tier`
reproduces the base-domain half of that precedent verbatim (custom-skill
dispatch never applies here, since `day_plan._validate_step` rejects any
`domain` outside `BASE_SKILL_DOMAINS`); `npc_tier` is passed `0` always.
Not an ambiguity between two derivations (the brief's own STOP
condition) — the one derivation found reduces to its already-existing
`None -> 0` fallback because its gate is never true on this schema.

**The fact sheet's `concordance` parameter is a FRESH re-run, not a
persisted object.** The brief's signature anticipated `freeze_facts`
receiving a `concordance` argument; `day_concordance.ConcordanceResult` is
never persisted past the `/plan` call that builds it (BRIEF-0075-c), and —
measured live — `agenda_step_requirement.target_entity_id` is populated
essentially NEVER in practice: the seeded `day_plan` prompt only ever asks
the model for the two requirement forms that need no entity id
(knowledge/resource). Sourcing `FactSheet.npcs`/`.locations` from
`agenda_step_requirement` rows alone would leave the fact sheet almost
always empty even when the declaration named a real NPC concordance HAD
resolved at plan time. The route (`cockpit/routes/day.py::
_concord_declaration`) re-runs extraction + `concord()` — the SAME
deterministic, model-free lookup, minus `emit_germs` (re-emitting germs at
resolve time, including on every replay, would duplicate the
`entity_creation` proposals `/plan` already staged). This is not a
regression from BRIEF-0075-c's "extraction happens once" posture:
extraction is three real model calls, but concordance ITSELF (the
Python-only matching) is idempotent and cheap to re-run, and re-running it
means AMENDMENT 1's ordering guarantee (concordance precedes narration)
holds a second time, inside `/resolve` too — not only inside `/plan`.

**What the T1 judge proves, and — as important — what it does NOT
prove.** Name containment (`day_narration_guard.extract_names` against
`FactSheet.authorised_names`) proves no proper name outside the
authorised list appears in the prose. It does NOT prove the prose is
coherent, and it does NOT prove a role hint was rendered as a function
rather than silently dropped — a beat that mentions no one at all still
passes name containment cleanly. Outcome survival (band-marker counting,
`BAND_MARKERS` shared between `day_narration.py`'s prompt-building and the
judge) proves the prose carries, for each band present on the fact sheet,
AT LEAST as many occurrences of that band's marker as there are steps of
that band — a COUNT, not a per-step positional pin: two same-band steps
are proven both rendered in aggregate, never individually tied to their
own sentence. The anti-vacuity guards (zero names extracted, zero steps on
the fact sheet) are both hard failures, never a silent pass — the single
most important lines in `judge_narration`, per the brief's own framing.

**The name-extraction heuristic is a real, if inherently incomplete,
detector — not a claim of completeness.** French has no small closed set
of "words that can never be a name." `extract_names` strips `[MARKER]`
band tags first (discovered live: without stripping, `[RÉUSSITE]` fuses
onto the name that follows it into one bogus multi-word candidate), then
treats a run of one-or-more consecutive capitalized words as a name
candidate, joined across a lowercase connector (de/du/des/le/la/l'/d'/
von/van). A lone SINGLE-word capitalized run is discarded when that word,
case-folded, is in `_FUNCTION_WORD_STOPWORDS` — a substantial but
deliberately non-exhaustive list of French articles, pronouns,
prepositions, conjunctions and discourse adverbs — REGARDLESS of sentence
position. Position-gating this (discard only at the very start of a
sentence) was the FIRST design and was live-tested wrong twice over:
gap-filling the stoplist itself ("Malgré", "À") fixed sentence-initial
false positives, but a THIRD live run produced "[RÉUSSITE] Le marchand
accepte : Il vend à Joran Vey." — a pronoun ("Il") sitting right after a
colon, a position this module cannot reliably prove is "sentence-initial"
(French punctuation the model actually produces is not limited to
`.`/`!`/`?`), so the position gate let a known function word through
ungated and the judge rejected a clean narration for it. Dropping the
position gate entirely (a function word is never a name candidate,
anywhere) fixed it, and is now the rule. The remaining risk — a genuine
one-word character name that collides with a function word — is accepted
as vanishingly rare next to two independent observed failures from the
position-gated design. The list is still expected to keep needing entries
as real narration prose is produced — the module docstring says so, on
purpose, rather than implying the heuristic is finished.

**A candidate run is authorised at the WORD level, not only verbatim.**
Live testing surfaced "Joran" (the player's own first name) rejected as
unauthorised because `FactSheet.authorised_names` only ever held the full
display name, "Joran Vey" — a model naturally refers to someone by one
name component, not always the full string. `day_narration_guard.
_authorised_words` expands every authorised full name into its
constituent words; a candidate run passes if it matches an authorised
name VERBATIM or if every one of its own words is individually
authorised. This also sharpens a merge artifact the extractor cannot
otherwise disambiguate from a real two-word name — two adjacent
capitalized words with no sentence boundary between them ("Maelis En",
from "Maelis. En quête de calme...") — by reporting only the genuinely
unauthorised word ("En"), not the whole run, since "Maelis" alone is
already authorised.

**An unresolved PLACE mention needed the same "render as a function, not
a name" instruction an unresolved PERSON already got.** `FactSheet.
role_hints` was person-only through the first live-test pass; a
declaration naming an unconfirmed market ("le marché", never resolved to
a real `location` entity, C1) gave the model no instruction at all for
that mention, and it capitalized "Marché" into what read as an invented
proper place name — a judge rejection the judge was RIGHT to produce (an
invented capitalized place name is exactly what name containment exists
to catch). The fix is on the prompt side, not the judge side:
`freeze_facts` now collects role hints for `concordance.unmatched` mentions
of category `person` OR `place`, and both the rendered fact sheet
(`day_narration._render_fact_sheet`) and the seeded `day_narration` prompt
say "personnes et lieux sans nom résolu... en minuscules, jamais comme un
nom propre" — loosening the judge here would have meant accepting an
actually-invented name; tightening the model's instructions instead keeps
the judge's guarantee intact.

**Zero resolved steps is a legitimate outcome, not a judge failure —
discovered live, not anticipated by the brief text.** A step-1 requirement
the character does not meet (e.g. a `resource` threshold against a zero
ledger balance) makes `budget_cut` exclude EVERY step before any dice
roll: `resolve_steps` returns `[]`, and a `FactSheet` built from an empty
`outcomes` list has `steps == ()`. The anti-vacuity guard (`judge_
narration`'s "zero steps on the fact sheet" check) is not wrong to exist —
a genuinely empty fact sheet passed to a model asking it to render
something is exactly the vacuity trap R5 exists to catch — but this
particular emptiness is not a broken computation, it is the correct,
narratable answer to "what happened today": nothing did, and code already
knows exactly why (`evaluate_requirements`'s own verdict reason for step
1). `day_resolve.blocked_reason` surfaces that reason; `resolve_day`
checks for the empty-outcomes case BEFORE calling `narrate`, and when it
fires, renders the day's prose directly in Python — no model call, no
judge call, a synthetic `JudgeVerdict(passed=True, ...)` fed straight into
the SAME `_finalize_resolution` persistence path every other outcome
uses. Skipping the model here is not a workaround for the judge's
anti-vacuity rule; it removes the only case where that rule would have
had to make an exception, which is safer than adding one.

**The rewrite pass is built against a trigger that cannot currently
fire.** `detect_late_delta` looks for an `entity_creation`
`proposed_mutation` tied to the resolving `pass_play_id` with
`status='applied'` and a real `target_id` — but no code path anywhere
turns that mutation type into a real entity: `_approve_entity_creation_
shortcircuit` (BRIEF-0019-a, reasserted by `day_concordance.py`'s R5)
PARKS every entity_creation approval, synchronously, unconditionally (I2).
`detect_late_delta` is therefore written against the day an applier for
that mutation type ships, not against today's actual behavior — Scope IN
item 4's own text predicts this ("the rewrite is expected never to fire in
a correctly ordered run"). Observed over the live verification runs for
this brief (repeated `/resolve` calls against one seeded declaration,
narrate+judge only, no rewrite trigger present): **0 rewrite firings**,
consistent with the prediction. This 0 is the evidence the D3 reactivation
condition (an entity_creation applier eventually shipping) is phrased
against — a nonzero count would mean the trigger fired despite the
structural block above still holding, which would itself be worth
investigating.

**A judge failure commits nothing mechanical either, superseded by V1.**
This paragraph originally read "a judge failure leaves the mechanical
outcome committed, only the prose rejected," describing
`persist_step_outcomes` committing `agenda_step` transitions independently
of the judge. Under V1 (AMENDMENT 1, below) that direct commit no longer
exists at all: a judge failure and a judge success now differ only in
whether `emit_mutations` runs — `_finalize_resolution` calls it exclusively
on the success path, so a rejected attempt proposes NOTHING for Nia to
review, and the dice-are-final argument below applies to the *outcome
value* (a real `StepOutcome` the instant `resolve_physical` returns), not
to any canon write, since none happens at resolve time regardless of the
judge. On a judge failure, `_finalize_resolution` still appends ONE
`pass_play.history` entry (the fact sheet, the rejected prose, the judge's
reason) and commits, then raises a 422 — Nia sees exactly what was
rejected and why. `pass_play.status` is left untouched (`resolving`, not
moved to `resolved`), so a second `POST /resolve` on the same batch
re-enters `resolve_steps` fresh — a real retry (new dice, since
`resolve_steps` re-rolls every call), never a queued retry of the SAME
rejected prose. This is deliberately not a "rollback the dice on judge
failure" design: the roll is Python and already true the instant it
happens: a narration problem is not a mechanics problem, and treating a
narration rejection as grounds to un-happen a real dice roll would make
the dice conditional on prose quality, which is exactly backwards from
"the prose is a rendering of an already-decided outcome, never a source
of one."

**`Batch.local_summary`/`.final_result` are repurposed, not added (D3).**
Confirmed zero readers and zero writers for both, in `src/` and
`tooling/`, before reuse — `local_summary` now holds the narration draft
(the prose as first accepted, whether that is the first attempt or the
rewrite), `final_result` holds the identical accepted prose a second time,
framed as "the canon-ready value" rather than "the draft"; the two are
byte-identical in every observed run because the rewrite path (above)
never fires. `message_to_claude`/`claude_raw_response` stay untouched,
still vestigial, still zero writers — Scope OUT is explicit that this
brief repurposes only its two siblings. `batch.status` gains one new
value, `resolved_awaiting_review` (`writes.pipeline.BATCH_RESOLVED_
STATUS`, declared beside the new `BATCH_STATUSES` vocabulary tuple — the
`PASS_PLAY_STATUSES` idiom, restated for `batch`) — legal without a schema
change, since the column carries no CHECK constraint on its vocabulary.

**`pass_play.history` gets its first writer.** `writes.pipeline.write_
pass_play_resolution` is the sole write path: `history = list(pass_play.
history or []); history.append(entry); pass_play.history = history` —
built from the CURRENT value plus one new entry, never a fresh literal,
matching `write_agenda_step_status`/`write_npc_goal_status`'s snapshot-
before-overwrite idiom even though this is a genuinely new column rather
than an edit to an existing row's live fields. A replay calls this a
second time on the same `pass_play` row and appends a SECOND entry; the
first is never touched. `declared_action` stays completely unwritten by
this brief, reasserted by both `pipeline_wiring.py`'s existing R3 and this
brief's own `day_narration.py` R8.

Verified live (not only by the check suite): `POST /api/day/declare` →
`POST /api/day/{id}/plan` → `POST /api/day/{id}/resolve` against the
seeded pilot world, real Ollama calls throughout (no mocking). A
three-step plan budget-cut to two included steps (the third genuinely
excluded by budget, never attempted) resolved with real 2d6 rolls,
persisted `agenda_step` transitions, and produced a judge-accepted
narration naming the concordance-matched NPC and rendering the
budget-excluded step correctly as never-attempted. Repeated `/resolve`
calls against the SAME `pass_play` (replay) produced different dice each
time and a growing `pass_play.history`, with every earlier entry intact.
A judge REJECTION was also observed live (the model mislabelling a
`failure`-banded step with the `[RÉUSSITE]` marker) and correctly stored
nothing final, appended the rejected attempt to `history`, and returned a
422 — confirming the fail-closed path is not only theoretical.

Extended live soak testing (repeated `/resolve` calls against varied
declarations and plans, real Ollama calls throughout) found the three
gaps documented above — the position-gated stoplist letting "Il" through
after a colon, whole-string-only name matching rejecting "Joran" against
authorised "Joran Vey", and unresolved places never being told to stay
generic — each confirmed by a REAL rejected `/resolve` call before the
fix, and each confirmed passing after it: a run using the full name, a
first-name-only reference, and a lowercase "le marche" in the SAME
narration all cleared the judge together once every fix landed. The
zero-attempted-steps edge case was also found live (a plan's first step
carrying a `resource` requirement the seeded player character's zero
ledger balance could never satisfy) and confirmed fixed: the SAME batch,
resolved and replayed, returned `200` both times with a code-rendered
prose naming the exact unmet requirement, no model call, no judge
involvement, and `pass_play.history` growing by one entry per call.

**AMENDMENT 1 (V1 — no direct step write).** The paragraph above describing
`persist_step_outcomes`'s direct `agenda_step` transitions is superseded.
Claude Code's execution of BRIEF-0075-e escalated a dead-proposal STOP
condition: -e's own Invariants section states the day chain "adds a
PROPOSER, not a writer," while this brief had it writing `agenda_step`
transitions directly — both cannot be true, and by the time an
`agenda_step_change` proposal reached the queue the step was no longer
`active`, so `_mutation_apply_agenda_step_change`'s stale guard rejected
it on arrival. The fault was this brief's: decision **V1** (locked,
`BRIEF-0075-d-amendment-1-no-direct-step-write.md`) removes
`persist_step_outcomes` entirely — `day_resolve.py` now computes
`StepOutcome`s and writes NO canon at all. The boundary is EMPTY FOOTPRINT
vs. WORLD FOOTPRINT, not agenda vs. non-agenda: creating a plan
(`write_day_plan`) records the player's own declared intent and stays a
direct write; completing a step carries `effects` (relations, ledger,
roles) and advances the agenda, so it goes through the review queue,
always. `AgendaStep.status`/`.outcome`/`.change_history` now move only
when Nia approves an `agenda_step_change` mutation (BRIEF-0075-e). A
consequence carried forward: `_mutation_apply_agenda_step_change` already
cascades on `complete` (activates the lowest-`step_order` `pending` step,
or completes the agenda when none remain), so a multi-step day still
works under V1 with no change to the applier — but the N proposals a day
emits must be approved in `step_order`, since an out-of-order approval
hits the stale guard. `fail` fails the WHOLE agenda (the applier's
existing, unbranching behaviour), so a failed step terminates the day's
plan rather than pausing it; recovery is BRIEF-0075-f's reconciliation.

---

## MUTATION EMISSION AND THE DAY ACCOUNT — proposer, not writer (BRIEF-0075-e, no schema change)

**A1 (asynchronous, creator in the loop) / O1 (no auto-approve).** The day
chain's ONLY new write is a `ProposedMutation` row at `status='proposed'`,
`source_type='pass_play'`, `pass_play_id` set, `conversation_id`/`tick_id`
NULL — built entirely in the new `day_mutations.py` (plus the
pre-existing `day_concordance.emit_germs` for `entity_creation` germs,
BRIEF-0075-c, unchanged). Nothing in the chain calls `_apply_mutation`;
every emitted mutation reaches canon only through the ordinary review
queue, exactly like a conversation- or tick-sourced proposal. A rejected
narration (the T1 judge, BRIEF-0075-d) emits NOTHING — `resolve_day` only
calls `emit_mutations` on the success path, inside the same transaction as
the narration/status writes, so a discarded attempt proposes nothing for
Nia to review.

**The corrected vocabulary (BRIEF-0075-e-amendment-1).**
`EMITTED_MUTATION_TYPES = ("knowledge_change", "relation_change",
"agenda_step_change", "entity_creation")`. `resource_change` and
`agenda_creation` from the original brief are REMOVED: under V1's
boundary, creating a plan has no world footprint and stays
`write_day_plan`'s direct write, and resources travel as `ledger_transfer`
effects on a step's own completion rather than a second vocabulary for
the same thing. `npc_move` stays absent (N1, BRIEF-0074-a-amendment-1):
the schedule is the positional truth, and a resolution-emitted move would
reopen that amendment. `relation_change` is kept for relation movement
belonging to no step, but has no computed source in v1 either — the
emitter always returns an empty list, the same deliberate no-op posture as
skill deltas (X1, below); the type stays in the vocabulary for a future
source, never invented here.

**The delta contract travels on the payload, not a column.** The
escalation looked for an `effects`/reward column on `AgendaStep`/
`AgendaStepRequirement` and correctly found none — the contract is
`_apply_completion_effects`'s own `_EFFECT_TYPES = frozenset({"relation_
delta", "ledger_transfer", "role_change"})` (`cockpit/mutations.py`,
TICKET-0024/BRIEF-0024-c), already shared with `goal_change complete`.
Every emitted `agenda_step_change` carries an EMPTY `effects` list in v1:
no per-step reward exists to compute one from (a `resource`-type
requirement carries no counterparty entity, so a `ledger_transfer` cannot
even be well-formed from it; a `relation_gte`-type requirement carries no
relation type or delta amount) — inventing a value here would be exactly
the house-rule the brief forbids. Nia edits the proposed payload in the
review queue (`ApproveBody.payload`, an existing creator affordance) to
attach a concrete effect when the day's narrative warrants one.

**The armed rendezvous (I1) needs no new mechanism.** `AgendaStepRequirement`
already has a `knowledge` requirement type (`_eval_knowledge`, day_plan.py)
gating a step on the player ALREADY holding some `Knowledge` subject —
that row must exist for the step to have been attemptable at all.
`day_mutations._emit_knowledge_change` deepens that SAME row to `knows`
whenever the step carrying that precondition completes successfully — the
"a contact found, an appointment made" case — emitted alongside the
generic `agenda_step_change` for that step. Arming the rendezvous is then
just the ordinary chain: approving the `agenda_step_change` cascades the
NEXT `pending` step to `active` (the applier's existing behaviour, V1),
whose `objective` — written at plan time by the model — IS the meeting;
approving the `knowledge_change` deepens the fact. Nothing is inserted,
nothing is invented, and the rendezvous is armed only once both are
approved. A day establishing a meeting the plan never anticipated (no
`knowledge` requirement on the completed step) emits nothing extra here —
bending the applier to insert a step was ruled out of scope; the next
day's reconciliation (BRIEF-0075-f) is the recovery path.

**X1 (named deferral) — skills have no carrier.** `_EFFECT_TYPES` covers
relations, ledger transfers and faction roles; it has no skill-gain
effect. In v1 the day produces no skill gain, and the account says so
positively (a `skill: {produced: [], note: "..."}` block, never a silent
omission) rather than pretending the category doesn't exist. Reactivation
condition: when a skill effect type exists in `_EFFECT_TYPES` — adding one
touches `_apply_completion_effects`, shared with `goal_change`, so it is
its own ticket, never an addition inside `day_mutations.py`.

**The day account (`GET /api/day/{id}`) never reads `pass_play.history`.**
`routes/day.py` is forbidden that attribute file-wide (`pipeline_wiring.
py`'s R5), so the account reads through two new helpers in `writes/
pipeline.py` — `read_latest_resolution` (the latest `history` entry) and
`resolution_count` (its length, `> 1` meaning a replay) — rather than
re-running extraction/concordance a second time, which would also cost a
fresh, non-deterministic model call on every read of an already-resolved
day. The account assembles prose (`batch.final_result`), NPCs/locations/
role_hints (the frozen fact sheet, unchanged since the resolution that
produced it), gains (read from this pass_play's own `ProposedMutation`
rows, each tagged with its live review status), a pending-review block,
and the rendezvous (surfaced only once its `agenda_step_change` shows
`status='applied'` — i.e., Nia already approved it and the applier's
cascade already ran). No `agenda_id`/`step_id` key reaches the response or
`Journee.svelte` (re-asserted by `tooling/verify/checks/day_mutations.py`
R7).

**The review queue badge and day link (D2).** `pass_play`-sourced rows
already rendered via the generic `sourceRef` text; this brief adds a
proper `b-pass-play` badge (`JOURNÉE · Jour N`) matching the existing
`b-tick` precedent, plus the day's declaration first line, resolved
through a new lazy `pass_play_id -> {day_number, declared_action}` cache
in `queue.svelte.js` fed by the already-existing `pass_play_id` field on
`GET /api/days`' response.

**The handoff to Play adds no new bridge-reach site.** The DELEGATED D1
from the original brief (what the legacy Play surface needs to open a
conversation with a given NPC) resolved to a hard constraint rather than a
contract to implement: `legacy_call.py`'s bridge-reach seam is shrink-only,
and its baseline holds exactly one sanctioned site
(`App.svelte::showFn`). `Journee.svelte`'s "Parler" button therefore calls
only `router.navigate('play')` — the same ordinary SPA navigation any
surface switch uses — which `App.svelte`'s existing route handler turns
into the one baselined `showSurface('play')` call. The player is handed
the rendezvous objective and the NPC's name in prose and lands on Play;
finding and starting the conversation there is Play's own existing
affordance, untouched, exactly as Scope OUT requires ("do not migrate it,
do not restyle it").

Verified live against the seeded pilot world (no schema change, real
Ollama calls for extraction/narration where exercised): a resolved day's
account rendered NPCs, role hints, prose and an empty gains block
correctly before any mutation existed for it. A scratch `agenda_step_
change` (`action=complete`) plus a `knowledge_change` deepening a
pre-existing `rumor`-level fact, approved in order through the live
`/api/mutations/{id}/approve` route: the first approval cascaded the
agenda's next `pending` step to `active` exactly as the applier's
existing logic predicts; the second upgraded the `Knowledge` row's level
to `knows` with its prior state preserved in `change_history`. The day
account then showed the rendezvous block (`armed: true`, the new active
step's objective) and the knowledge gain (`status: "applied"`), and the
review queue displayed the new `JOURNÉE · Jour N` badge with the day's
declaration linked. The "Parler" handoff was confirmed to navigate the
shell to `/play` with no new legacy bridge-reach site.

## THE FEASIBILITY VETO — a downward-only clamp is not an exception (BRIEF-0075-g, no schema change)

**Y1 (the veto's shape is the whole safety argument).** A model call that
can only SUBTRACT from an already-legal plan cannot break F1
("model proposes, code judges"), because it never proposes anything new:
`day_feasibility.veto()` receives `budget_result.included` — the steps
`budget_cut` (BRIEF-0075-b) already retained, requirements already judged
— and asks one question ("how many of these, in order, could this
character plausibly do in one day?"). `clamp_verdict()`, a PURE function
(no `db`, `select(`, `chat(`, `datetime`, `randint` — R1), is what actually
enforces the bound with a real `min(raw_retained, python_retained)` call
(R2), never a prompt instruction: this is deliberate, because an
abliterated model follows a positive request but cannot be trusted to
honour a negative one, so "never propose more than you were given" has to
be code, not phrasing. This is why Y1 is not an exception to "model
proposes, code judges" at all — the model's only two possible effects on
canon are "resolve fewer of Python's steps today" or "no effect" (an
honoured or unavailable verdict). It can never add a step, raise a cost,
lower a cost, or overturn a prerequisite verdict — Y3 (the model deciding
how many steps fit, replacing Python's sum) was rejected as F3 in the
original brief and stays rejected.

**Proves X, not Y.** The clamp proves the veto CANNOT lengthen a day —
that is a structural guarantee, true on every input, adversarial or not
(verified by feeding `clamp_verdict` a deliberately inflated `retained`,
a negative one, a missing `reason`, and a citation naming a step outside
the input — every case lands on `clamped` or `unavailable`, never a
widened `veto_retained`). It does NOT prove the veto's judgment is GOOD —
whether the character/plausibility reasoning is any good is an empirical
question the clamp is structurally blind to. That is what the calibration
numbers (below) are for, and why Scope OUT forbids tuning the prompt
against them in this same brief: reporting and tuning are different
activities, and mixing them here would make the first report already a
biased one.

**Fail-closed in the direction that matters.** `veto()` never raises —
Ollama unreachable, an unparseable response, a missing/malformed field, or
a citation naming a step outside the input all collapse to
`outcome="unavailable"` with `veto_retained == python_retained` (R6): the
day proceeds on Python's cut, exactly unchanged. This is a deliberate
asymmetry with every other model call in the day chain (`day_plan.
emit_plan`, the extraction passes) — those RAISE on failure and abort the
whole `/plan` call (F1's "propose or stop" posture), because a day plan
with no steps is meaningless. The veto is an ADD-ON judgment layered onto
a plan Python already legally computed; its own failure must never block
that plan, and "inert" (Python's cut stands) is the only failure mode that
cannot also be a silent widening.

**D1 resolved: there is no "character frame" to build, only to reuse.**
The mini-RECON asked what character context the extraction passes
(`day_extract.py`) already assemble, on the premise that the veto needed
"the same frame." The premise half-held: `day_extract.py`'s passes take NO
character parameter at all — they see only a secret-free `world_frame(world)`
(name + description; `World` carries no secret column, so this cannot leak
one). The one piece of character-specific context anywhere in the day
chain is a NAME, looked up in `day_plan.emit_plan` via `db.get(Entity,
character.id)` — nothing deeper (goals, secrets-excluded knowledge,
personality) is ever assembled for a day-chain model call. `day_feasibility.
veto()` reuses BOTH builders verbatim (`world_frame`, promoted public in
`day_extract.py` for this reuse, plus the identical name lookup) rather
than building a second, deeper frame — which is exactly the ad-hoc
assembly the mini-RECON's D1 was warning against: a frame nothing else in
the chain has is a frame that has never been audited for what it leaks.

**The persistence problem the brief didn't spell out, and how it's solved.**
The veto decides ONCE, at `/plan` time (Wiring: "calls veto AFTER
budget_cut… never before"), but `POST /api/day/{id}/resolve`
(`day_resolve.resolve_steps`) independently RE-DERIVES `budget_cut` from
the persisted `AgendaStep` rows every time it runs (BRIEF-0075-d's
deliberate replay semantics) — with no schema change available, there was
no column to carry `veto_retained` from one request to the other. The
"Docs to update" line ("the verdict record rides in `PassPlay.history`")
pins the answer: `write_day_feasibility` (`writes/pipeline.py`) appends a
SECOND entry kind to the same `pass_play.history` list `write_pass_play_
resolution` (BRIEF-0075-d) already owns, discriminated by `"kind":
"feasibility"` (resolution entries carry no `"kind"` key at all, before or
after this brief). `resolve_day` reads it back via a new `read_latest_
feasibility` and hands `veto_retained` into `resolve_steps`, which slices
`budget_result.included` to that prefix BEFORE rolling any dice — a
further truncation layered on top of `budget_cut`'s own output, never a
change to what `budget_cut` computes or to any requirement verdict, so S4
("any existing caller depends on `budget_cut`'s output being final") does
not fire: every caller still gets `budget_cut`'s exact result; the veto
only ever narrows the PREFIX of it that gets used, identically at `/plan`
and `/resolve`. `resolution_count`/`read_latest_resolution`
(BRIEF-0075-e's `is_replay` machinery) are updated to skip any entry whose
`"kind"` is `"feasibility"` — since a feasibility entry is written exactly
once per `pass_play`, never on a replay (Scope OUT: "retrying a rejected
verdict"), this cannot inflate the replay count, and every entry written
before this brief is unaffected (no `"kind"` key to filter on).

**Live-tested against the seeded pilot world, real Ollama calls
throughout** (`huihui_ai/qwen3-abliterated:8b-v2`, the seeded default):
nine feasibility verdicts across nine declared days, five carried through
to a full resolution (declare → plan → resolve → account), plus one
synthetic injection (a persisted `veto_retained` edited directly in the
test DB from 3 to 1, citing step 2) to force-observe an ACTUAL reduction
end to end without waiting on the model to volunteer one. That synthetic
case confirmed the mechanism precisely: with `python_retained=3`,
`veto_retained=1`, `resolve_steps` rolled exactly ONE step ("Saler
Maelis"), and the frozen fact sheet / emitted mutations both reflected
one step, not three — steps 2 and 3 stayed `pending`, untouched, exactly
as Done-means item 1 specifies.

**The calibration numbers (Scope IN item 4 — evidence, not tuning).**
Outcome distribution across the nine organic (model-produced) verdicts:
9 `honoured`, 0 `clamped`, 0 `unavailable`. `python_retained -
veto_retained` distribution: `{0: 8, 2: 1}` (the one non-zero delta is the
synthetic injection above, not an organic model judgment). Read plainly:
in this session, the model never once disagreed with Python's own budget
cut. The likely reason is structural, not a prompt defect: `DAY_BUDGET_
SLOTS` is small (four slots derived from the phase vocabulary) and most
emitted steps cost 1-4, so `budget_cut` itself rarely retains more than
one to three steps before the veto ever sees the plan — there is
typically little room left for a plausibility judgment to disagree with an
already-tight mechanical cut. `clamp_verdict`'s `clamped`/`unavailable`
paths are independently verified correct by direct unit exercise (an
inflated `retained`, a negative one, a missing `reason`, a citation
outside the input — see execution notes), so their absence here is a
statement about what this run's inputs produced, not about whether the
code paths work. Per Y1's own "proves X, not Y": a veto that never fires
is a calibration fact to sit with, not a code defect to chase inside this
brief — Scope OUT explicitly forbids tuning the prompt against it here.

**A live-testing aside, unrelated to Y1, reported for the record.** Several
resolve attempts (independent of the veto) were rejected by the T1
narration judge (BRIEF-0075-d) for reasons the veto never touches: a
location matched by declaration text without its definite article ("Dernier
Verre" vs. the canon "Le Dernier Verre") went unmatched by concordance and
then got rendered as an unauthorised proper noun; the world/city name
"Verkhaal" surfaced in narration despite never being added to `authorised_
names` (only matched NPCs and locations feed that set, never factions); and
a very long, multi-clause declaration twice produced truncated/invalid JSON
from `day_plan.emit_plan`. None of these touch the veto's own code path —
they are pre-existing surface area in `day_concordance.py`/`day_narration_
guard.py`/`day_plan.py` — reported here only because they were observed
during this brief's live-testing, exactly as CLAUDE.md's testing guidance
asks; not fixed, as fixing them is out of this brief's scope.

## THE REMAINING-WORK INVARIANT AND THE RESOLVE PRECONDITION (BRIEF-0075-f, no schema change)

**BB1 (locked with Nia) — two structural fixes, discovered mid-execution of
BRIEF-0075-f, landed ahead of that brief's own commit.**

**Part 1 — the remaining-work invariant.** `day_resolve._load_evaluated_steps`
loaded EVERY `agenda_step` row for the agenda, unconditionally, and fed all
of them into `budget_cut`, which always walks starting at the lowest
`step_order`. Harmless while an agenda could never outlive a single day
(BRIEF-0075-b through -e refused a second declaration on an active agenda
outright — the S3 refusal BRIEF-0075-f replaces). Once continuation is
real, the first time Nia approves a prior day's `agenda_step_change`
(moving a step to `completed`), the NEXT day's `/resolve` would still
re-include and re-roll that same completed step forever — the greedy walk
can never progress past step 1 once it is done. The resulting mutation
would be safely REJECTED at approval time by the applier's existing stale
guard (`step.status != "active"`), so canon was never at risk; only the
day's own dice and narration were wrong, repeatedly.

`_load_evaluated_steps` now excludes `agenda_step` rows already at a
TERMINAL status (`completed`, `failed`) from its walk — the agenda's
REMAINING work only, on every call, present or future. This is safe under
REPLAY (Scope IN item 5, BRIEF-0075-d): under V1, `day_resolve.py` writes
no canon, so a step's status only ever moves when Nia approves the
corresponding `agenda_step_change` mutation — an action structurally
decoupled from `/resolve` itself. A replay called before that approval
therefore never encounters a step that "moved" out from under it; nothing
about REPLAY ever depended on terminal-status rows being in the walk.

**Part 2 — the resolve precondition.** Excluding terminal steps closes the
APPROVED case completely, but leaves the RESOLVED-BUT-UNAPPROVED case open:
a step `/resolve` proposed yesterday, still sitting at `status='proposed'`
in the queue, keeps its `AgendaStep.status` as `active`/`pending` — so
today's walk re-rolls it and today's narration replays the same beats a
second time. Canon still cannot be corrupted (the stale guard holds), but
the day ACCOUNT would lie about what happened.

`POST /api/day/{batch_id}/resolve` now refuses, fail-closed
(`_guard_no_pending_agenda_step_change`, `routes/day.py`), when the
standing agenda carries ANY `agenda_step_change` proposal still
`status='proposed'` — deliberately with NO distinction between a mutation
THIS batch just emitted and one a PRIOR day emitted. This is the
structural expression of A1's rhythm (the world does not advance while
proposals about it are unreviewed) extended from "no direct write" to "no
further resolution either." It also means a REPLAY of the SAME day is now
gated exactly like a NEXT day's continuation: rejecting a resolution
rejects its own proposals, which clears the precondition and unblocks the
replay — one rule, one rhythm, not an exception carved out for same-batch
proposals. The check is ONE precondition query, self-contained in
`routes/day.py`: `day_resolve.py` has no business knowing the review queue
exists (unchanged discipline), so the walk itself stays uncoupled from
`ProposedMutation`.

**Verify.** `tooling/verify/checks/day_narration.py` R12 (the remaining-
work invariant: the terminal-status constant and the `.not_in(...)`
exclusion are both located, not presumed) and
`tooling/verify/checks/day_mutations.py` R12 (the resolve precondition:
the guard filters `mutation_type='agenda_step_change'` at
`status='proposed'`, raises a 409, and is actually called from
`resolve_day`) — both fail-closed and vacuity-guarded, each observed
FAILING under a deliberate local mutation before revert.

## RECONCILIATION AND CLOSURE — Z4 repairs the source, AA2 makes replace a creator act (BRIEF-0075-f, no schema change)

**R1 (unaffected by the amendment).** `day_reconcile.reconcile()` is ONE
model call classifying a new declaration against a STANDING agenda as
`continue`/`modify`/`replace`, citing a real `step_order`. The model
CLASSIFIES; it writes nothing (R1's own tripwire) — every structural
effect, when there is one, goes through the ordinary mutation queue,
never a direct write. A validation failure (a verdict outside the trio, or
a citation naming no real step) raises `LlmParseError` and stops the day —
never a silent fallback to `continue`, which the brief's own Invariants
call "the worst possible failure mode: it looks like inertia and is
actually a swallowed error."

**Z4 (locked with Nia) — the escalation was correct, the fix goes where
the state breaks, not downstream.** The original brief's Scope IN item 2
needed a `pending -> active` flip that `_mutation_apply_agenda_step_
change` cannot express (it accepts only `action in ("complete", "fail")`
on the CURRENTLY ACTIVE step), while the brief's own Scope OUT forbids
widening that vocabulary. Escalated rather than guessed at (the correct
call — see the mini-RECON's own STOP condition). The resolution: the
mechanism already existed. `PATCH /agenda-steps/{step_id}` has always
been able to perform that exact flip (creator CRUD, the SECOND sanctioned
canon-write path) — nothing was missing from the engine. The real gap was
narrower: `PATCH /agendas/{agenda_id}` with `status='active'` (reactivating
a failed agenda) never touched the reactivated agenda's steps, so a
reactivation onto an agenda with pending-but-no-active steps left it
INCOHERENT — active at the agenda grain, with no active step underneath.

`_activate_lowest_pending_step_if_none_active` (`cockpit/crud/agendas.py`)
closes that gap AT ITS SOURCE: the SAME `PATCH /agendas/{agenda_id}` call
that reactivates the agenda also promotes its lowest-`step_order` PENDING
step to `active`, in the SAME transaction, via `write_agenda_step_status`
(so `change_history` is appended — history stays sacred), when and only
when no step is already active. Idempotent both ways: a step already
active is untouched, and an agenda with no pending step left is untouched
too — that agenda is INERT, a `replace` case for the day chain, not a
`continue` one. This makes the invariant unconditional rather than
situational: **an active agenda with pending steps always has exactly one
active step**, defended at the one place the state can break, never
patched around downstream. `_mutation_apply_agenda_step_change`'s action
vocabulary stays exactly `("complete", "fail")` — Z4 exists precisely so
that widening is never needed (re-asserted, `day_plan.py` check R21).

Live-verified: a step approved as `fail` (agenda -> `failed`, that step ->
`failed`, remaining steps left `pending` with none promoted — `fail`
touches only the failing step, per the applier's own code) reactivated via
`PATCH /agendas/{id}` -> `status='active'` correctly activated the next
`pending` step, with the prior `pending` state recorded in that step's
`change_history`.

**Corrected `continue`: a true no-op.** In the normal case (an approved
prior step already cascaded the next one active) there is nothing to
activate — `continue` proposes NOTHING, ever, and emitting an empty
proposal for a no-op was ruled queue noise (day_plan.py check R19: the
`continue` path constructs no `ProposedMutation`). Z4 guarantees the ONLY
way an active agenda reaches reconciliation with no active step is the
now-impossible-to-reach INERT case — so `continue` on that state reports
the plan exhausted (409) and stops; that classification should have been
`replace`.

**`modify`, and why it structurally never expresses a diff.**
`_mutation_apply_agenda_step_change` has no action to insert, reorder, or
edit a PENDING step's objective — its only actions transition the
CURRENTLY ACTIVE step, and even those describe something ALREADY ROLLED
(dice happen at `/resolve`, reconciliation happens at `/plan`, before any
roll exists to describe). The consequence, confirmed by direct
implementation and live-tested: comparing the revised plan (`emit_plan`
re-run with the standing agenda's remaining steps as context) against
those remaining steps is either IDENTICAL (no real diff — a no-op,
`mutation_ids: []`, same as `continue`) or DIFFERENT, and every observed
DIFFERENT case is S2 — a 422 naming exactly why ("no action exists to
insert, reorder or edit a pending step"). This is not a limitation
introduced here; it is what `_mutation_apply_agenda_step_change`'s
existing, unwidened vocabulary always implied. `modify` is otherwise
unaffected by the amendment.

**AA2 (locked with Nia) — a correction, and `replace` becomes a creator
act.** The original brief's R4 forbade `replace` from ever emitting
`abandoned`, reasoning "history is sacred" as if `abandoned` erased
something `failed` preserves. That conflated two different rules:
`abandoned` preserves `change_history` exactly as `failed` does — the
difference is TERMINAL MEANING, not audit fidelity. `failed` additionally
routes through `_cascade_agenda_status_to_goals` (`writes/goals_agendas.
py`), abandoning every linked `npc_goal` — the correct side effect for a
plan the character genuinely lost, and the WRONG one for a plan the
player merely dropped to do something else. `replace` therefore emits
NOTHING and writes NOTHING (R14: no `.delete(` in `day_reconcile.py`, no
`ProposedMutation` construction in the `replace` handler): the chain
records the verdict, reports that the standing plan must be closed,
names it, and stops (409). Nia closes it manually through the EXISTING
`PATCH /agendas/{id}` -> `'abandoned'` — a creator act, not a chain-
automated one; rejected alternatives were proposing `agenda_step_change
fail` (wrong terminal state, plus the goal cascade) and adding a new
`abandon` mutation type or action (correct but scope creep into the
shared applier — its own ticket if the manual step proves tiresome after
five separate days, the named reactivation condition for that deferral).

Live-verified end to end: an unrelated declaration against a standing
agenda classified `replace`, named the standing agenda's title, committed
nothing (the standing agenda's steps were unchanged in the DB); the
standing agenda closed via `PATCH .../abandoned`; the SAME declaration
re-planned found no active agenda and took BRIEF-0075-b's fresh-plan path
unchanged (no `reconciliation` key in the response).

**The dispatch is a real dict, not an if/elif chain** (`_reconcile_and_
finalize`, `routes/day.py`) — `RECONCILE_VERDICTS` and the `handlers`
dict's key set are the same static, checkable fact (day_plan.py check
R12), the same `_EVALUATORS`/`REQUIREMENT_TYPES` bijection idiom this
ticket has used throughout. **Superseded in shape, not in spirit, by
BRIEF-0077-c** (see "DEDICATED PLAN SELECTION AND THE RESUME ACTION"
below): the dispatch now keys on a four-value `action`
(`PLAN_ACTIONS`), not `RECONCILE_VERDICTS` directly, and R12 checks the
`handlers` key set against `EXPECTED_PLAN_ACTIONS` instead — the
real-dict-not-if/elif property this bullet documents is unchanged.

**Ticket-closure sweep (Scope IN item 4).** Every named deferral
confirmed still deferred, by diff (nothing outside this brief's own file
list was touched): multiplayer and `batch_order` beyond 1 (`write_pass_
play` still hardcodes `1`), auto-approve, `flag_reason`, location germs
(`day_concordance.emit_germs` unchanged, person-only), D3's prologue,
P1's phase-anchored budget (`DAY_BUDGET_SLOTS` still `len(SCHEDULE_
PHASES)`), M3's interval unification, TICKET-0069, `schedule_reads.py`
(zero-diff), `PUT /api/world/phase` (zero-diff).

**The four vestigial `Batch` columns, reported only.** `local_summary`
and `final_result` have writers (`_finalize_resolution`, since
BRIEF-0075-d); `message_to_claude` and `claude_raw_response` have NO
writer and NO reader anywhere in `src/` — unchanged by this ticket
end to end. A no-reader review candidate for a later ticket, per the
brief's own instruction — not dropped here.

**The rewrite-firing counter: zero, across every day resolved during
this ticket's verification** (both this brief's live-testing and
BRIEF-0075-g's, spanning roughly twenty declared days) — matching the
structural prediction in `day_narration.py`'s own module docstring: no
applier exists yet for `entity_creation`, so `detect_late_delta` can
never find an approved germ to fire on. The D3 reactivation condition
(an applier for `entity_creation` exists) remains unmet.

## DAY CHAIN PROMPT DELIVERY AND COVERAGE GUARD (BRIEF-0076-a, no schema change)

TICKET-0075 shipped eight `prompt_template` heads (`pt-day-plan`,
`pt-day-extract-place/person/faction`, `pt-day-narration`, `pt-day-rewrite`,
`pt-day-feasibility`, `pt-day-reconcile`) with exactly one creation path:
`scripts/seed_pilot.py`. `cockpit/crud/prompts.py` has list / edit-text /
restore-version / set-model but no create endpoint, no boot hook in
`cockpit/app.py` reads `prompt_template`, and every prompt-related check
under `tooling/verify/checks/` is static (none opens a database) — so a live
DB seeded before the day chain shipped, or one restored from an older
backup, silently diverges from the corpus with no detector anywhere. The
symptom (TICKET-0076's intake report): `POST /api/day/{batch}/plan` failing
502 with `day_extract: no active prompt_template for usage='day_extract_place'`
on a DB that had never run the post-BRIEF-0075-b seed.

**Delivery is a hoist, not a rewrite.** The 14 `DAY_*` prompt-text constants
move from inside `seed()` to module level in `scripts/seed_pilot.py`,
byte-identical. A module-level `DAY_PROMPT_HEADS` — a tuple of eight
`dict(id=..., name=..., usage=..., world_id=..., system_prompt=...,
user_template=..., variables=..., destination=...)` calls — is the single
source for both the head fields `upsert_prompt_template` needs and the text
constants; `seed()` now loops `for entry in DAY_PROMPT_HEADS:
upsert_prompt_template(session, **entry)` instead of eight literal calls.
`scripts/apply_ticket_0076_day_prompt_seed.py` is the one-shot delivery path
for an already-running DB: a CREATE-HEAD script (unlike
`apply_ticket_0024_prompt_updates.py`'s append-a-version shape) that embeds
no text and no head fields of its own, importing `seed_pilot.DAY_PROMPT_HEADS`
and looping the same `upsert_prompt_template`. S2 (creator sovereignty) is
inherited, never reimplemented: a head already present with >= 1 version
never has its text touched, by either path.

**The `dict(...)` call form is load-bearing, not stylistic.** The existing
`prompt_registry.py` check's bijection assertion greps the WHOLE seed file
for a literal `usage\s*=\s*"([a-z_]+)"` text pattern — it is not scoped to
`seed()` and does not parse the AST. A dict LITERAL (`{"usage": "day_plan"}`)
would have made all eight `usage=` occurrences vanish from the file's text,
silently failing that check's bijection in the wrong direction (registry
entries with no seeded usage). Keyword-call syntax keeps the literal text
pattern intact while still letting `DAY_PROMPT_HEADS` be actual structured
data. Rejected: touching `prompt_registry.py`'s check to scope or AST-ify
the scan — out of blast radius for a delivery-only step, and the existing
check has three other assertions this ticket has no reason to touch.

**The coverage guard sits at `POST /api/day/declare`** (`declare_day`,
`routes/day.py`), as its first statement, before any write —
`src/world_engine/prompt_coverage.missing_usages` is called against
`DAY_CHAIN_USAGES` and a non-empty result raises a 503 naming every missing
usage and the one-shot script to run. Rejected: a boot-time guard (B1) — one
missing prompt would stop every surface from serving, not just the day
chain; reactivation condition: a second chain ships and per-surface guards
start duplicating each other. Rejected: an advisory report only (B3) —
contradicts structural-over-disciplinary (the same posture as every other
fail-closed gate in this codebase).

**`DAY_CHAIN_USAGES` is derived, never restated.** `prompt_coverage.py`
computes it from `PROMPT_REGISTRY`: every usage whose `PromptSpec.call_sites`
names a `src/world_engine/day_*.py` module, minus `DEGRADING_USAGES`. No
usage string literal appears in the module outside that one frozenset.
Rejected: a usage-key prefix rule (D1) — lexical, drifts silently on a
rename, no reactivation foreseen. Rejected: a new `PromptSpec.chain` field
(D3) — one reader only, and a forgotten `chain="day"` on a future entry
falls out of the guard exactly as silently as the prefix rule; reactivation
condition: a day-chain prompt moves outside a `day_*.py` module, or a second
chain needs the same treatment. `surface` cannot carry this distinction
either — it is a two-value field (`"play"` | `"authoring"`) and all eight
day usages share `surface="play"` with sixteen others.

**`day_feasibility` is exempt, deliberately, and the exemption is checked
rather than trusted.** `day_feasibility.py:188` returns
`_unavailable(...)` instead of raising on a missing template —
BRIEF-0075-g's decision Y1, a designed degradation (the veto is optional;
its absence just means nothing narrows the plan Python already cut).
Requiring it at `/declare` would convert a tolerated absence into a refusal
it was never meant to have. `tooling/verify/checks/day_prompt_delivery.py`'s
R6 recomputes this by AST every run: for each `day_*.py` file carrying a
day-chain usage, it finds the file's "no active prompt_template" message(s)
and classifies the file as `Raise` or `Return`; the `Return`-classified
usages must equal `DEGRADING_USAGES` exactly, and the `Raise`-classified
usages must equal `DAY_CHAIN_USAGES` exactly, in both directions. Rejected:
a `D1`/`D2` cross-agreement rule pairing the prefix approach with the
derivation — dropped on Nia's explicit instruction ("D2 seulement"); R6
checks the exemption's correctness directly instead.

**Ticket-closure sweep.** TICKET-0075's front-matter `status` moves
`escalated` -> `done` (front-matter only; `QUESTION-TICKET-0075.md` and its
`continue` verdict were answered out of band directly to Claude Code and are
untouched here, per this brief's explicit Scope OUT).

## PARKED PLANS — direct write, not auto-approved; the owner_type index rejected (BRIEF-0077-a, schema v1.95)

**(a) Parking/activating a plan is a direct write, never an auto-approved
mutation.** Nia's requirement is absolute: a plan swap must never block the
day (A1). `day_mutations.py:12-16` already records the governing precedent
for this exact posture:

> `resource_change` and `agenda_creation` are OUT: under V1, creating a plan
> has no world footprint and stays `write_day_plan`'s direct write
> (BRIEF-0075-b); resources travel as `ledger_transfer` effects on a step's
> own completion, never a parallel vocabulary.

A status swap between two plans of the SAME player has the same property —
no NPC sees it, no relation/knowledge/ledger row moves — so `day_plans.
park_active_plan` calls `write_agenda_status` directly, exactly as
`write_day_plan` calls `write_agenda` directly. Considered and rejected:
routing the park through `_apply_mutation` as an auto-approved
`ProposedMutation` (`status='applied'` on creation) — this would still be a
queue row for Nia to eventually SEE, contradicting "nothing can leave the
day blocked" only by accident of timing, and it would be the first
mutation type ever created pre-approved, a precedent this codebase's
review-queue doctrine does not want. The audit trail is `agenda.
change_history`, appended by `write_agenda_status` on every transition —
the same mechanism as every other agenda status change, not a special case.

**(b) A denormalized `agenda.owner_type` column with a partial unique index
is rejected.** `(owner_entity_id) WHERE status='active' AND
owner_type='character'` would buy structural (database-level) enforcement
of the one-active-per-character-owner rule, at the cost of a denormalized
copy of `entity.type` that can drift from the real value — and the two
canon-write sites (`write_agenda`, `write_agenda_status`, see (c) below)
are already a complete chokepoint without it: nothing else constructs an
`Agenda` row or transitions its `status`, per `canon_write_policy.
txt:53,56`. *Reactivation condition: if a third canon-write site for
`agenda.status` is ever introduced* — at that point a code-level guard
stops being a complete chokepoint and the structural index earns its
denormalization cost.

**(c) Amendment to ONE-ACTIVE-PERSONAL-AGENDA (BRIEF-0020-a).** The section
above (line ~5522) placed the one-active-per-character guard inside
`write_agenda` alone, on the reasoning that it was "the sole canon-write
path" for `agenda.status = 'active'`. BRIEF-0077-a's intake found that
reasoning stale: `PATCH /agendas/{id}` (`cockpit/crud/agendas.py`) already
routed a reactivation through `write_agenda_status` WITHOUT replaying the
guard — a second, unguarded path to `status='active'` for a character
owner, reachable since `write_agenda_status` first unlocked `character`
owners (BRIEF-0020-a) alongside `write_agenda`. Two active agendas for one
player character were therefore already reachable before this brief, not a
risk `paused` introduces. The guard is now replayed verbatim at
`write_agenda_status`'s own `status == "active"` branch — same tier, same
existence-query shape, closing the gap rather than converting the
invariant into something the `PATCH` route caller must remember to check.

---

## DEDICATED PLAN SELECTION AND THE RESUME ACTION — a SELECT before a CLASSIFY, an ordinal never an id (BRIEF-0077-c, no schema change)

After BRIEF-0077-a a player can hold several open plans (`active` and
`paused`), but `plan_day` still looked only at the single `active` one
(`_load_standing_agenda`): a declaration that means "I go back to what I
was doing before" could not find a parked plan, and resuming stayed a
manual two-step through the Creation intrigues tab. This brief adds ONE
model call, `day_plan_select.select_plan`, whose only job is to say which
of the player's open plans a declaration targets, or none, and wires the
`resume` transition Python derives from the answer.

**(a) Selection is a SEPARATE model call from reconciliation — Nia's
decision C3, "un appel modèle dédié juste à cela".** `day_reconcile.
reconcile` already classifies a declaration against ONE agenda's remaining
steps (`continue`/`modify`/`replace`); collapsing "which plan" and "what
does it mean for that plan" into a single call was considered and
rejected. A dedicated SELECT keeps each call's failure mode narrow and
legible — a bad selection is a wrong plan, a bad reconciliation is a wrong
classification of an already-known plan — and keeps `day_reconcile.py`'s
prompt untouched (S2: an already-seeded head's text is not retouched by
this brief).

**(b) The model answers with an ORDINAL into a Python-owned list, never an
id.** `select_plan` builds the numbered `{plans}` list itself, in the order
`day_plans.open_plans` returns it; the model's `"selected"` field is that
number or `null`, exactly as `day_reconcile` already has the model cite a
`step_order` rather than a `step_id`. A hallucinated identifier therefore
cannot reach canon — there is no identifier to hallucinate. An
out-of-range or non-integer answer is a parse failure
(`llm_parse.LlmParseError`), never a silent fallback to `None` or to plan
1: the same discipline BRIEF-0075-f's own decision record calls "the worst
possible failure mode: it looks like inertia and is actually a swallowed
error." `MAX_SELECTABLE_PLANS` does not exist — every open plan is
offered, uncapped (decision G).

**(c) Decision D2 — four dispatch ACTIONS, three model VERDICTS.**
`day_reconcile.RECONCILE_VERDICTS` stays exactly `("continue", "modify",
"replace")`; the model is never asked to report whether the plan it
classified was active or paused; asking it to restate a fact Python
already measured (`agenda.status`) would add a failure mode for no
benefit. Instead `day_reconcile.plan_action(verdict, selected_status)` is a
total, code-only mapping from `RECONCILE_VERDICTS x
day_plans.OPEN_PLAN_STATUSES` (six pairs) onto a four-value ACTION
vocabulary, `PLAN_ACTIONS = ("continue", "modify", "replace", "resume")`:
`continue`/`modify` on an `active` plan pass through unchanged;
`continue`/`modify` on a `paused` plan both land on `resume` (plan
revision on a resumed plan is BRIEF-0077-d's; until then a paused plan
resumes unchanged and `modify`'s 422 is unreachable from this path);
`replace` is `replace` regardless of the selected plan's status, since
`_finalize_replace` parks whatever is ACTIVE and opens a fresh plan
unconditionally. `_reconcile_and_finalize` (`cockpit/day_reconcile_apply.
py`) dispatches on the ACTION, not the verdict; `resume`'s handler is
`handlers["continue"]` reused verbatim — a resumed plan's content does not
change, only which plan is active does, so the distinct dispatch key is
what makes the action visible and checkable (`day_plan.py` R12/R23), not a
different code path. Before dispatch, a `resume`/non-`replace` action on a
`paused` selection parks whichever plan is currently active
(`day_plans.park_active_plan`) and activates the selected one
(`write_agenda_status`) — park before activate, flushed between, so the
one-active-per-character guard cannot normally fire; if it somehow does,
its `ValueError` surfaces as a 409, never a 500.

**(d) `plan_day` routes selection before reconciliation, and the fresh-plan
path now explicitly parks.** `plan_day` calls `day_plans.open_plans` then
`day_plan_select.select_plan`; a non-`None` result goes to
`_reconcile_and_finalize` against the SELECTED plan (which may be paused);
`None` means the declaration opens something new, and — because selection
now runs against ALL open plans rather than gating on "is there an active
one" — the standing active plan, if any, must be parked explicitly
(`day_plans.park_active_plan`) before a fresh plan is emitted, a step the
old `_load_standing_agenda`-gated branch got for free. `_load_standing_agenda`
is deleted (an unused reader is structure without a reader); `tooling/verify/
checks/day_plan.py` R15 is retargeted from it to `day_plan_select.select_plan`,
the same kind of retarget BRIEF-0077-b already applied to R12/R14/R19 for a
relocation.

## STEP ACTIVATION AT THE TRANSITION — Z4 bound structurally, not by convention (BRIEF-0080-a, BRIEF-0080-b, no schema change)

TICKET-0080's intake measured that a parked plan resuming via the day chain
hit a false 409: `_finalize_continue` (`day_reconcile_apply.py`) trusted the
Z4 guarantee — "an ACTIVE agenda either already has an active step, or has
no pending step left at all" — but that guarantee held at only ONE of the
two canon-write sites that can turn an agenda `active`. The creator's
`PATCH /agendas/{id}` route called the repair
(`_activate_lowest_pending_step_if_none_active`, formerly
`cockpit/crud/agendas.py`); the day chain's `resume` branch called
`write_agenda_status(..., status="active")` directly and skipped it. A
parked plan with all-`pending` steps therefore resumed into a state the
guard refused, with a message that prescribed `abandoned` — destroying
resumable work to fix a bug in the repair's own coverage.

**(a) The fix moves the repair to the transition, not to the missed
caller.** `_activate_lowest_pending_step_if_none_active` relocates into
`writes/goals_agendas.py` and is called from inside `write_agenda_status`
itself, on the `status == "active"` branch, after the one-active-per-
character guard and the goal cascade, before `return agenda`. Every canon-
write path that can produce an `active` agenda — today's five call sites,
and any future one — is covered by construction; there is no second
caller left to forget. This is the same move BRIEF-0077-a made for the
one-active-per-character guard: a caller-side discipline promoted into a
property of the chokepoint itself. `parked_plan_guard.py` gained two rules
to keep this checkable rather than asserted: R7 confirms the call exists
inside `write_agenda_status`; R8 confirms the helper has exactly one
definition anywhere under `src/world_engine/`, in `writes/goals_agendas.py`
— a second copy appearing elsewhere would silently reintroduce the same
asymmetry this brief closes.

**(b) The promotion stays unconditional, exactly as Z4 was before this
brief.** Re-evaluating a promoted step's requirements before activating it
is deferred (G3's behavioural half); this brief is a pure relocation plus
one call, not a widening. The `blocked` band (BRIEF-0078-b) already
surfaces an unmet prerequisite as a narrated outcome at resolve time, so an
unconditional promotion here cannot produce a false success — it can only
make a step selectable, never make it succeed.

**(c) G3 stays locked as doctrine, deferred as behaviour.** A plan born
with `active_step_index = None` (`cockpit/routes/day.py:484`, the
feasibility veto retaining zero steps) is INERT BY INTENTION: the veto
judged nothing startable, and this brief does not touch that line or force
step 1 active there. What "resume a blocked plan" should mean is a
separate workstream. Until it lands, such a plan still refuses on
`continue` — that refusal's message is BRIEF-0080-b's 422 split, not this
brief's concern — and the reactivation condition recorded at intake is the
first live session in which that 422 branch fires.

**(d) BRIEF-0080-b: the guard's single message was two conflated failure
modes.** After (a), `resume` no longer reaches the guard at all — the
transition promotes a pending step before dispatch. One path still does: a
plan born with `active_step_index = None` ((c) above), selected with a
`continue` verdict, never parked. For that plan the old guard was correct
to refuse and wrong in what it said — it reported exhaustion ("no active
or pending step left") when the plan was in fact blocked, and prescribed
`abandoned` when the work was intact. Two distinct causes sharing one
message is what sent Nia toward destroying a recoverable plan at intake.

The fix splits the refusal into `_refuse_unstarted_plan`
(`day_reconcile_apply.py`), extracted out of `_finalize_continue` so the
guard is a single, nameable assertion rather than an inline branch:

- **EXHAUSTED** (no `pending` step either, every step terminal) — 409,
  naming exhaustion, offering `completed` OR `abandoned` as the remedy —
  closure is a choice, not the only one.
- **UNSTARTED** (a `pending` step exists at the lowest `step_order` but was
  never activated) — 422, naming the plan intact, explicitly stating
  "do NOT abandon it", and citing the first remaining step's own unmet
  requirement in French.

**A guard asserts, it never repairs.** `_refuse_unstarted_plan` contains no
`db.add`, no `write_*`, no `db.commit` — the same discipline (a) already
established for the transition-bound repair: any future "resume a blocked
plan" behaviour is G3's workstream, not a widening of this guard.

**One evaluation, not two.** The 422's requirement detail is built by
`day_plan.evaluate_agenda_step` — the per-step evaluation carved out of
`day_resolve._load_evaluated_steps` in this same brief's first commit — so
the day chain's resolve walk and the guard's refusal share ONE judgment of
"is this step's requirement met", rather than growing a second, hand-rolled
copy that could drift from it. `requirement_detail_fr` (BRIEF-0078-b)
renders the unmet verdicts into the same player-facing French the
`blocked` band already uses.

**G3's reactivation condition, restated in its verifiable form (supersedes
(c)'s wording):** the first live session in which `_refuse_unstarted_plan`'s
422 branch actually fires against a real player. Until then, "resume a
blocked plan" stays deferred — the plan refuses with a true message instead
of a false one, which is strictly better than today without deciding G3's
behavioural half.

---

## REQUIREMENT ANCHORING — a knowledge gate is legitimate only on a learnable subject (BRIEF-0078-a, schema v1.96)

TICKET-0078: a day plan could gate step 1 on `{"type":"knowledge",
"target_key":"room_setup"}` — a key the model invented with no canon row
behind it — and `budget_cut` breaking at the first unmet step then emptied
the whole day. The inversion the doctrine forbids: the model was proposing
the CRITERION a Python gate would enforce, not the action a Python gate
would judge. This step restores the boundary: "model proposes, code
judges" now applies to the REQUIREMENT itself, not only to the character's
state against it.

**B3 — the anchoring predicate.** A `knowledge` requirement's `target_key`
survives emission only when it matches a `knowledge.subject` held, in this
world, by an entity OTHER than the player, on a row that is not
`is_secret`. `_anchorable_subjects` (`day_plan.py`) is the ONE place this
predicate lives, expressed as a single explicitly-filtered `select(`:
`Entity.world_id == character.world_id` (in-world only — a cross-world
name collision must not anchor a gate), `Knowledge.entity_id !=
character.id` (the player's OWN held subjects can never anchor a gate on
themselves — a gate on something already held is dead, not legitimate),
`Knowledge.is_secret == False` (structural, not instructional: a secret
subject is both an unsatisfiable gate and a leak, since the reject message
would itself disclose that the secret exists — the same doctrine that
excludes `character.secrets` and `is_secret` rows from every context
assembler). An unanchored `knowledge` requirement is DROPPED at emission
(`anchor_requirements`), never the step it sat on: the step keeps its
objective and loses only the gate, becoming an ungated step — the intended
outcome, a day that runs, not a degradation. `_held_subjects` (also
`day_plan.py`) feeds the emission model the player's own held subjects
(`held_subjects_summary`, appended verbatim to `emit_plan`'s user message,
the `concordance_summary`/`standing_steps_summary` precedent — never a new
prompt-template placeholder) so it stops proposing a dead gate in the
first place; `anchor_requirements` catches the opposite error, a gate on
something that exists for NOBODY. Together they carve out exactly the
legal band: **you can only be locked on something that exists to be
learned.**

**Schema v1.96 — `idx_knowledge_subject`.** `knowledge` carried no index on
`subject`; anchoring's join through `entity` would otherwise be a full
scan on every `/plan` call. Index-only migration
(`migrate_v1_96_knowledge_subject_index.py`), no table rebuild — this
column needed no CHECK, no NOT NULL change, nothing an index add can't do
alone. `_anchorable_subjects` and `_held_subjects` are its only readers,
and each runs AT MOST ONCE per `/plan` call (one explicitly filtered
`select(`, not once per requirement) — the enumeration-scope discipline
applied to a lookup that previously did not exist.

**E2 — `/plan` reports, it does not refuse.** `_finalize_plan` already
computed `first_excluded_index` and used it for nothing; this step wires
it to two new response keys, `blocked_at_index` and `blocked_reason`
(non-null only when the excluded step's own requirements are unmet — a
budget-only cut is not a block), alongside `anchoring.dropped` (the
anchoring drop report). The day is still written and `/plan` still
returns 200 exactly as before: visibility, not refusal. Rendering the
blocked step as narrative prose is BRIEF-0078-b's job — after this step an
anchored-but-unmet step 1 still produces the pre-existing one-line
failure at `/resolve`.

**`Verdict` gains a `type` field, placed FIRST.** BRIEF-0078-b and -c both
need to know which requirement TYPE produced an unmet verdict (to decide
whether a blocked step should propose a learned rumor); rather than thread
`RequirementSpec` alongside `Verdict` everywhere, each of the four
evaluators now sets `type=req.type` on its own `Verdict`. `type` is FIRST
in the dataclass, not appended, so that a positional `Verdict(...)`
construction anywhere in the tree (none exist today — checked, not
assumed) would fail loudly on the wrong type in the wrong slot rather than
silently shifting every other field one place over.

## G1 — subject-vocabulary hygiene, deferred (BRIEF-0078-a, no schema change)

The pilot seed already holds numerous distinct `knowledge.subject` values
with visible near-twins (`magic_existence` / `magic_awakening` /
`personal_magic_incident` / `local_magic_incidents`; `lettre_innommee` /
`the_unnamed`), no normalization at the write chokepoint
(`writes/knowledge.py`), and exact-string comparison in the existing
duplicate guard (`cockpit/mutations.py`). Anchoring gives this problem its
first READER — `_anchorable_subjects` now cares whether two near-duplicate
strings are "the same subject" — but does not introduce the problem, and
is deliberately not the ticket that fixes it: a normalization pass, an
alias table, or a canonical-vocabulary table is real scope, and
anchoring's own C2/D3 design (BRIEF-0078-b/-c) makes anchoring PRECISION
affect flavour only, never liveness — a near-duplicate subject can still
produce a legitimate gate the player cannot open from any NPC, and a
blocked step's proposed rumor opens it through play anyway. Reopen this
deferral once either becomes true, verified, not estimated: `SELECT
COUNT(DISTINCT subject) FROM knowledge` on a live world exceeds **150**,
OR a similarity pass measures more than **20%** of subjects within
Levenshtein distance <= 3 of another.

---

## C2 — A BLOCKED STEP IS AN OUTCOME, NOT AN ABSENCE (BRIEF-0078-b, no schema change)

After BRIEF-0078-a a `knowledge` gate is anchored in canon, but an anchored
gate the player genuinely does not meet still emptied the day:
`budget_cut` breaks at the first unmet step, `resolve_steps` returned an
empty list, and `judge_narration`'s own zero-step anti-vacuity guard then
refused the fact sheet — the only way past it was a code-rendered
one-liner (`cockpit/routes/day.py`'s old zero-outcome branch), never a real
narrative.

**The zero-step case is ELIMINATED, not excused.** The temptation this
step's whole shape is built to resist: adding a special case to
`judge_narration` for "blocked days." That would be a weaker judge. Instead
`resolve_steps` (`day_resolve.py`) now appends AT MOST ONE trailing
`StepOutcome` at `band=BLOCKED_BAND` (`_append_blocked_step`) whenever the
budget cut excluded a step for being genuinely unmet — and ONLY then: a
budget-only cut invents no blocked beat, a feasibility-veto truncation
past that point owns its own reason instead, and a step that already
FAILED on the dice keeps its own stop, never a fabricated gate beat after
it. `day_narration_guard.py` is byte-identical after this step — its
zero-names and zero-steps anti-vacuity guards, and `extract_names`, are
untouched. Making the input non-empty, rather than loosening what checks
it, is the whole point.

**A blocked step was never attempted.** `day_mutations._step_action`
widens to return `None` for it (neither `"complete"` nor `"fail"`), and
`_emit_agenda_step_change` emits nothing for that `None` —
`_mutation_apply_agenda_step_change`'s own action vocabulary stays exactly
`("complete", "fail")` (R21), since no third literal is ever constructed
into a payload. The step's `AgendaStep` therefore stays exactly as
`pending`/`active` as it was; nothing enters the review queue for it.
Proposing the rumor the player learns from bumping into the gate (D3) is
NOT this step — that is BRIEF-0078-c.

**French only, structurally.** `requirement_detail_fr` maps a `Verdict`'s
`type` (BRIEF-0078-a's field) to one of four fixed French templates
(`_BLOCKED_DETAIL_FR`) — `Verdict.reason`, the English machine text
`evaluate_requirements` produces for logs and the `/plan` response, never
reaches a player. The rendered detail (including a `knowledge` gate's raw
subject label) is fed to the narration model as fact-sheet INPUT, never
shown to the player directly; the reseeded `day_narration` prompt's marker
rule is the safeguard that keeps the raw label out of the player-visible
prose — it explicitly instructs the model to use the given reason "sans
la recopier" (without copying it verbatim). This is a Live (human-gate)
acceptance criterion, not a machine-checkable one, because it depends on
the local model's actual behaviour.

**History is sacred, again.** The `day_narration` prompt's marker rule
gains one clause (`[BLOQUÉ]`) via a NEW `prompt_version` row
(`scripts/apply_ticket_0078_narration_seed.py`, the
`apply_ticket_0024_prompt_updates.py` append-version shape) — the existing
version is never edited in place. `blocked_detail` is a new, defaulted
`None` key on `StepFact`/`fact_sheet_dict`; a `pass_play.history` entry
written before this step simply lacks the key on read-back — no migration,
no rewrite of stored rows.

## D3 — A BLOCKED STEP PROPOSES A RUMOR-LEVEL LEAD ON ITS OWN BLOCKING SUBJECT (BRIEF-0078-c, no schema change)

Nia's own reading, verbatim from the ticket's follow-up decisions: *"un plan
peut être créer avec un knowledge que le joueur ne détient pas ... et le
joueur aura une piste sur comment l'obtenir (rumor) jouable la prochaine
journée."* This is a WORLD RULE she decided, not a technical fallout of
C2's blocked band — bumping into a door teaches a little about it.

`day_mutations._emit_new_knowledge` walks a blocked outcome's
`requirement_verdicts` and, for each unmet `knowledge` verdict, proposes a
`new_knowledge` mutation at `_BLOCKED_LEAD_LEVEL = "rumor"` on the EXACT
subject that blocked the step — spelling and all, no normalization (G1
stays deferred). The proposal goes through the review queue like every
other day-chain mutation: V1 stands, the day chain proposes and never
applies. This is what makes REQUIREMENT ANCHORING's precision non-load-
bearing (BRIEF-0078-a): a legitimate gate on a near-duplicate subject no
reachable NPC holds still resolves through play instead of deadlocking,
because the player earns a lead on it regardless of which near-twin key
the model happened to invent.

The TICKET-0077 park/resume precedent does not apply here — that is a
DIRECT write (`writes/goals_agendas.py`) because a plan has no world
footprint; granting knowledge has one, so it stays proposal-only.

A duplicate guard (`_blocked_lead_already_proposed`) stops re-resolving the
same blocked day from stacking identical proposals before Nia clears the
queue. It is a DELIBERATE duplicate of `cockpit/mutations.py`'s
`_knowledge_already_applied`, not a call into it — that guard is
conversation-scoped and scans APPLIED rows; this one is world-scoped and
scans the OPEN `proposed` queue, a different question with a different
key. Bounded by the size of that queue.

## H1 — ANY KNOWLEDGE LEVEL SATISFIES A GATE (BRIEF-0078-a, BRIEF-0078-c, no schema change)

`_eval_knowledge` (`day_plan.py`) tests `row is not None` and never reads
`level` — kept exactly as is, because it is what makes D3's rumor
playable the very next day, precisely as Nia described. The price, stated
plainly: **every knowledge gate is a one-day speed bump, never a durable
obstacle.**

H2 (a floor level carried on the unused
`agenda_step_requirement.threshold` column, ranked via a
`KNOWLEDGE_LEVEL_LADDER`) is the named deferral. Reactivation condition:
*once a level escalator on repeated blocking exists* — a step blocked N
times proposing a rising `knowledge_change`. Without that escalator, H2/H3
would produce a permanently shut gate, which is this ticket's own bug
returning by another door — so it stays out until the escalator exists.

## A2 — THE NAME EXTRACTOR IS SENTENCE-SCOPED AND EDGE-STRIPPED, POSITION GATING STAYS REJECTED (BRIEF-0079-a, no schema change)

TICKET-0079's measured root cause: `_TOKEN_RE` (`day_narration_guard.py`)
captured `[.!?]+` as tokens, but the pre-fix `extract_names` filtered them
out before the run-building loop, so a run could span a full stop —
`"... les Serviteurs. Sans Dirigeants ..."` fused into the single run
`"Serviteurs Sans Dirigeants"`, and the `len(run) > 1` bypass let `Sans`
(a listed stopword) through despite never being a real name candidate.

Fixed with two independent, composable passes: `_sentences` splits the
marker-stripped token stream on `.`/`!`/`?` and `extract_names` builds runs
per sentence, unioning the results — a run can no longer span a sentence
boundary. `_strip_stopword_edges` then trims function words off the FRONT
and BACK of every built run before the keep decision, closing the bypass
that let a fused run smuggle a stopword through as an "interior" word;
interior words are never touched, so a genuine oddity between two real
names is still reported rather than silently discarded.

**Position gating stays rejected.** `_sentences` makes sentence position
knowable for the first time, which makes discarding a candidate for being
sentence-initial newly tempting — it is still forbidden. A single
capitalized word is discarded ONLY by the `_FUNCTION_WORD_STOPWORDS` test,
at any position, per the live-tested-wrong precedent already recorded in
the module docstring (`day_narration_guard.py:39-56`).

**The capitalised common-noun class is out of scope here and stays a
judge-external fix.** `Dirigeants`/`Serviteurs`-shaped capitalized common
nouns still report as unauthorised after this step — no French common-noun
lexicon, determiner exemption, or lowercase-elsewhere heuristic was added
to the extractor. This upholds the precedent already recorded at
`day_resolve.py:141-146`: when the model over-capitalizes, the fix belongs
in the prompt (and, per BRIEF-0079-b, a bounded repair pass), never in a
looser judge. Rejected again here for the same reason: `B1` (determiner
exemption) and `B3` (deterministic de-capitalisation pre-pass).

**Amendment, in-session (no ticket-artifact file deposited):** the
brief's original `verify/checks/day_name_extraction.py` Scope IN spec used
containment assertions ("no returned run contains X") on a G1 golden case
whose prose kept the offending common noun lowercase. Measured: those
assertions held for the target implementation, for a sentence-split-only
revert, AND for the fully pre-fix `extract_names` alike — the case
distinguished nothing. Corrected with Nia in-session: G1's prose was
replaced with the live-observed reproduction (capitalized
`Serviteurs`/`Dirigeants`), and every golden case now asserts the exact
returned set. Each case's mutation-kill is recorded inline in the check
file; the two reverts (sentence-split, edge-strip) were each run once
against the corrected suite and confirmed to fail it.

## THE BOUNDED REPAIR PASS AND THE STRUCTURED 422 (BRIEF-0079-b, no schema change)

Second and last step of TICKET-0079. After -a, the extractor no longer
fuses across sentences, but a capitalized common noun (`Dirigeants`,
`Serviteurs`) still correctly reports as unauthorised, per the precedent at
`day_resolve.py:141-146`: the judge stays strict and the fix belongs to the
model. Three changes ship together: `JudgeVerdict` gains a defaulted
`offending_words: tuple[str, ...] = ()` field, populated only by the
containment branch; `DAY_NARRATION_SYSTEM_PROMPT`'s naming rule is
re-anchored on the nameable LIST rather than a word class, in positive
form only, with no illustrative examples (an example in a system prompt is
a vocabulary reservoir that tints later narration) — forward-compatible
with factions joining the nameable list later (`E2'`); and one bounded
repair pass (`day_narration.repair`, `MAX_REPAIR_ATTEMPTS = 1`) fires in
`_narrate_and_judge` when, and only when, the verdict failed AND
`offending_words` is non-empty — never on a band-marker or anti-vacuity
failure. The 422 body (`cockpit/routes/day.py:_finalize_resolution`) is now
a structured dict (`message`/`reason`/`offending_words`/`prose`); the route
never parses `verdict.reason` (R21).

**R19 exists as its own rule, not a stretch of R6.** R6 (the rewrite's
bound) counts calls named `rewrite`/`day_rewrite`; it is structurally blind
to a call named `repair`. R19 mirrors R6's shape for the repair pass
specifically, so each of the two independent model-call passes carries its
own bound, verified by its own rule.

**R20 extends R9 (registry wiring) rather than duplicating it** — the same
function now walks `{day_narration, day_rewrite, day_narration_repair}`,
each against its own rule id in the failure message.

**Downstream governance list also needed updating.** Adding the
`day_narration_repair` seed head and its `PROMPT_REGISTRY` entry pushed
`tooling/verify/checks/day_prompt_delivery.py`'s R1/R2 counts from 9/16 to
10/18 heads/constants — that check's own docstring calls its counts
"deliberately literal and deliberately brittle" (TICKET-0076), by design
requiring exactly this kind of manual bump on every legitimate addition
(TICKET-0077/BRIEF-0077-c set the precedent). Updated in the same commit;
`corpus_gate.py` (96 checks) is green.

### Execution notes (live-gate findings for Nia)

**The re-anchored naming rule (item 2) is NOT live on any already-seeded
world, by design (S2, TICKET-0011, locked) — action needed from Nia.**
`upsert_prompt_template`'s own docstring: "a head already present with
>= 1 version -> NEVER touch text again (creator sovereignty is absolute —
seed wording improvements no longer propagate to an already-seeded DB)."
Measured on "La Dichotomie": `pt-day-narration` already carries 2
`prompt_version` rows (both pre-dating this ticket), so re-running
`seed_pilot.py` left its live text exactly as it was — the two bullets
this brief rewrote in `scripts/seed_pilot.py` are correct in the SOURCE
CONSTANT (and will seed correctly on any virgin/new-world head) but are
NOT what the live model was tested against below. `day_narration_repair`,
being a brand-new head, seeded its v1 correctly and WAS live for every
test. To put the new wording in effect on an existing world, Nia creates a
new `prompt_version` for `pt-day-narration` herself via the Prompts tab
(S2's whole point: text propagation to a live world is a creator act, not
an automatic one) — this is not a defect, but it does mean the false-
positive rate on "La Dichotomie" will not visibly improve until she does.

**Item 8 (422 consumer enumeration, report-only).** The sole consumer of
`POST /api/day/{batch_id}/resolve` is `frontend/src/journee/journee.svelte.js:92`
(`resolveDay`), through `frontend/src/creation/sheetRequest.svelte.js:33`
(`api()`: `throw new Error(data.detail || JSON.stringify(data))`) into
`journee.svelte.js:96` (`journeeState.resolveError = e.message`). `detail`
is now a dict, not a string: `new Error(dict)` coerces it to the string
`"[object Object]"`, discarding `offending_words` and `prose` entirely.
Confirmed live: resolving Jour 6 of "La Dichotomie" through the actual
Journée UI rendered exactly `[object Object]` as the error text. Per this
brief's Scope OUT, NOT fixed here — Journée is shell-native (not the sealed
Play surface), but the brief's item 8 is report-only regardless of which
surface holds the broken consumer.

**A discrepancy in this brief's own Done-means, found live.** One Done-means
bullet reads: "force a rejection the repair cannot fix (temporarily remove
`day_narration_repair`'s seeded row) and confirm the 422 body carries
`offending_words` and `prose`." Tested exactly as written (`is_active =
False` on the seeded row, then resolved a day whose narration drew a
name-containment rejection): the actual result is a **502**
(`"day narration repair failed: ...no active prompt_template..."`), not a
422 — because Scope IN item 6 explicitly specifies `LlmParseError` from a
missing template is handled "exactly as the two existing calls handle it"
(502), and item 5's `repair()` raises exactly that when the template is
absent. The code is internally consistent with its own Scope IN; the
Done-means bullet's premise (missing template -> 422) does not hold given
item 6's own instruction. A 422 carrying `offending_words`/`prose` DOES
happen — reliably — on the OTHER meaning of "a rejection the repair cannot
fix": the repair prompt is present, fires, and the repaired prose is
STILL rejected. Confirmed live and via a direct `narrate`/`judge_narration`/
`repair` probe against the real model and the seeded prompts (below).

**The repair pass's real-world success rate, measured against the live
game model (`huihui_ai/qwen3-abliterated:8b-v2`).** A 6-sample probe
against a synthetic fact sheet reproducing the ticket's exact scenario
(Lorian, `Serviteurs`/`Dirigeants` role hints) drew: 1 clean pass, 1
anti-vacuity failure (repair not attempted — correctly, per Scope OUT),
and 4 name-containment rejections that triggered repair — of which **0
of 4 repaired successfully**. The repair model's failure mode is
consistent: rather than lower-casing only the listed offending word(s), it
lower-cases the ENTIRE prose, including the authorised names and the
`[RÉUSSITE]`/`[PARTIEL]`/`[BLOQUÉ]` markers — which then fails the judge's
anti-vacuity guard instead (zero names extracted). Every failure still
degrades correctly to a structured 422 (never a silent bad narration, per
"Fail-closed narration" above) — this is a model-compliance quality
finding, not a code defect (per the project's own precedent: "French
quality... is a model-selection signal, not a code defect"). It is flagged
here because it bears directly on this ticket's own governance: `B1`/`B3`
carry a reactivation condition — "the judge still rejects after the repair
pass on more than 2 out of 10 resolved days" — and this sample (4 of 6,
counting the anti-vacuity case, rejected even after the repair attempt was
either skipped or failed) is already past that threshold. Recorded for
Nia's live-gate judgment, not acted on unilaterally: revisiting `B1`/`B3`,
or tuning the repair prompt or model, is a design decision outside this
brief's Scope IN.

**Live-tested and confirmed working (against the pre-existing narration
wording, per the note above).** `JudgeVerdict.offending_words` is populated
correctly on every containment rejection; the repair pass fires exactly
when, and only when, `offending_words` is non-empty (never on the
anti-vacuity/band-marker failures also observed live); the 422 body is
structured on every rejection path tested (repair not attempted, repair
attempted and still rejected, and repair unavailable). A "clean pass" DID
occur in the probe's first sample — the pre-existing prompt wording
sometimes gets it right on its own, model stochasticity — but this is not
evidence for the new bullets specifically, per the note above; the
re-anchored wording's own effect on the false-positive rate is untested
until it is live on a world. `pass_play.history` on the live "Jour 6"
(`392d014a-9eff-4b83-86af-b1462d5ce58f`) grew append-only from 3 to 7
entries across this session's live/API test calls; the pre-existing
feasibility entry and every prior rejected attempt survived intact.

## THE FACT SPINE — KNOWLEDGE'S STRUCTURAL ANCHOR, SUBJECT CUTOVER DEFERRED (BRIEF-0082-b, schema v1.98)

`knowledge` pointed at a string (`subject`) with no foreign key to what is
known. `fact` gives it a structural target: `id, world_id, relation_id,
event_id, world_law_id, content, default_level, created_at, created_by,
change_history`, with `ck_fact_spine_exclusive` (at most one of
`relation_id`/`event_id`/`world_law_id` set) and `ck_fact_default_level`
(the six-value level vocabulary). A fact is EITHER a typed row that
already exists OR free-standing (every typed FK NULL); `fact_participant`
(`id, world_id, fact_id, entity_id, role, position`, unique on
`(fact_id, entity_id)`) carries a free-standing fact's arity — zero for a
world-level statement, one for a statement about a single entity, several
for a secret shared by conspirators. No `entity_id` column on `fact`
itself (an intake amendment): an arity-1 fact is a nu spine plus one
`fact_participant` row, exactly one way to express each arity — avoiding
two ways to say the same thing. `situation_id` is deliberately absent; the
`situation` table does not exist yet.

**Single write chokepoint, spanning-constraint enforced in code.**
`writes/facts.py::create_fact`/`attach_participants` are the only
sanctioned `fact`/`fact_participant` write sites (registered in
`canon_write_policy.txt`, AST-scanned by both `single_canon_write.py` and
`fact_spine.py`'s own narrower scan). `attach_participants` raises
`ValueError` when the target fact carries any typed FK — the one rule
SQLite cannot express as a CHECK because it spans two tables — surfaced as
a 409 by the creator endpoint (`POST`/`DELETE
/api/facts/{fact_id}/participants`), never silently dropped.

**`knowledge.fact_id` is NOT NULL — the write-site blast radius was wider
than the brief's own enumeration.** The Scope IN text names only
`cockpit/crud/knowledge.py::_create_knowledge_core` for the "auto-create a
free-standing fact when none is given" fallback. `write_knowledge`
(`writes/knowledge.py`) has five call sites, not one:
`cockpit/crud/knowledge.py::_create_knowledge_core`,
`cockpit/mutations.py`'s `new_knowledge` and `resource_change` branches,
`link_author.py::commit_batch` (`write_knowledge(db, **row.payload)`), and
`cockpit/routes/creator.py::_write_pc_knowledge`. Making `fact_id` NOT
NULL without touching any of them would 500 four sanctioned paths outright.
The fallback therefore lives in `write_knowledge`/`_build_knowledge_update`
itself — the single chokepoint all five already share — rather than
duplicated at `_create_knowledge_core` alone: an explicit `fact_id`
attaches to that fact, omitting it auto-creates a free-standing one via
`create_fact` with `content = subject`, exactly the behaviour the brief
specifies, just placed where every creator benefits from it for free. This
was executed as a mechanical consequence of the NOT NULL column (there was
one coherent answer, not a D1 fork), not a re-litigation of Scope IN.

**Migration (`scripts/migrate_v1_98_fact_spine.py`).** One raw-DBAPI-
connection transaction (`migrate_v1_95_parked_plans.py` precedent):
backfills one free-standing fact per distinct `(world_id, subject)` pair
reachable through `knowledge.entity_id -> entity.world_id`
(`content = subject`, `default_level = 'unaware'`, `created_by =
'migrate_v1_98'`, zero participants — the literal subject `"unknown"`
gets a fact like any other, never special-cased), then rebuilds
`knowledge` with `fact_id` populated via a `(world_id, content=subject)`
join. An orphan guard (a `knowledge` row whose `entity_id` cannot resolve
a world) aborts before any DDL runs. Post-checks — row count unchanged,
zero NULL `fact_id`, a checksum over `(id, entity_id, subject, level,
content, acquired_at)` unchanged — run BEFORE commit and roll back the
whole transaction on failure (stricter than the `migrate_v1_95` precedent,
which checks after commit).

**Deferred decision — `Knowledge.subject` cutover.** Ten identity-key
sites survive this ticket, matching from the string rather than
`fact_id`: `scene_format.py:61-63`, `cockpit/mutations.py:464-466`,
`cockpit/mutations.py:724-726`, `cockpit/routes/mutations.py:172-174`,
`day_plan.py:141-142`, `day_plan.py:332`, `day_plan.py:344-349`,
`link_context.py:89-90`, `link_author.py:191-193`,
`analyzer_transcript.py:658 / 716-726 / 834-836` — including
`link_author.py:193`'s `f"npc:{other_id}"` convention, a foreign key
already encoded inside the string. `subject` and `idx_knowledge_subject`
(v1.96) are untouched; none of the ten sites is converted here. Reactivates
immediately on close of TICKET-0082 — a successor ticket is required
before any NEW reader is written against `subject`.

## SCOPED KNOWLEDGE DEFAULTS — THE G2a PRECEDENCE LADDER (BRIEF-0082-c, schema v1.99)

**The single authority on level resolution.** `knowledge_resolve.py::
resolve_knowledge_level(db, entity_id, fact_id) -> str` is total over the
six-value ladder (`writes/knowledge.py::KNOWLEDGE_LEVEL_LADDER`) — it always
returns one of the six values, never `None`, because its last tier
(`fact.default_level`) is NOT NULL by schema. Precedence, most specific
first, the function returning at the FIRST tier that produces a value:

1. a stored `knowledge` row for `(entity_id, fact_id)` — wins outright,
   including when it is `'unaware'`;
2. a `fact_default` at `scope_type='location'` for the entity's current
   location (`character.current_location_id`) or any ancestor of it via
   `location.parent_location_id` — nearest ancestor wins;
3. a `fact_default` at `scope_type='faction'` for any faction the entity
   holds an ACTIVE membership in (`faction_membership.left_at IS NULL`) —
   across several such memberships, the HIGHEST level on the ladder wins;
4. a `fact_default` at `scope_type='world'` (`scope_id IS NULL`);
5. `fact.default_level`.

`resolve_levels_for_entity(db, entity_id) -> dict[str, str]` is the batch
companion: one pass over every fact in the entity's world, each precomputed
context (stored rows, location chain, active faction ids, every
`fact_default` for the world) fetched exactly once rather than once per
fact, returning only the facts resolving above `'unaware'`. Both entry
points share one pure tier function (`_resolve_tiers`) so the two never
drift.

**New table `fact_default`** (`models/canon_knowledge.py`): `id, world_id,
fact_id, scope_type, scope_id, level, created_at, created_by`, with
`ck_fact_default_scope_type` (`scope_type IN ('world','faction',
'location')`), `ck_fact_default_scope_shape` (`scope_id` NULL iff
`scope_type='world'`) and `ck_fact_default_level` (the six-value
vocabulary). A faction scope uses the faction's `entity.id` directly —
`faction.id` is already an `entity.id` FK, so `scope_id` needs no second
column and no polymorphic type tag. Unique on `(fact_id, scope_type,
scope_id)`. Ships empty (no migration seed); the creator surface is its
first writer.

**Single write chokepoint, duplicate-checked at the route.**
`writes/facts.py::create_fact_default` is the sole sanctioned write site
(registered in `canon_write_policy.txt`). It performs no duplicate check of
its own — the creator route (`POST /api/facts/{fact_id}/defaults`,
`cockpit/crud/knowledge.py`) queries for an existing `(fact_id, scope_type,
scope_id)` row first and returns 409 rather than a silent upsert; SQLite's
NULL semantics would otherwise let several `scope_type='world'` rows past
the unique index (`NULL <> NULL`), so the 409 pre-check is load-bearing for
that case specifically, not merely defense in depth. `DELETE
/api/fact-defaults/{id}` is a creator-correction hard delete, same class as
`delete_knowledge`/`detach_fact_participant` — named in
`single_canon_write.py`'s closed hard-delete list; a `fact_default` row
carries no `change_history` of its own (curated-config shape, no
per-knower identity to preserve).

**Readers stay thin — the union lives in one shared helper.**
`resolve_default_rows(db, entity_id, exclude_fact_ids)` builds transient
(never `db.add`-ed) `Knowledge` instances for every fact resolving above
`'unaware'`, skipping any fact a stored row already covers, each carrying
`is_secret=False` and `share_threshold=50` — item 5's structural defence
(see `knowledge_resolve.py`'s module docstring, reproduced verbatim there):
a resolved default can never mint a secret, because secrecy stays a
property of a stored row, structurally excluded at query level by the
existing readers; a default-minted secret would put a second, weaker
authority behind that exclusion. The three readers
(`context.py::_npc_context_speak`, `context.py::
_mj_context_player_knowledge`, `tick_context.py::_tick_knowledge_block`)
each add a 2-3 line union call and nothing else — `context.py`
(956 lines) and `tick_context.py` (644 lines) both stayed clear of the
1000-line `module_budget.py` cap.

**Verify check `knowledge_resolution.py`.** Four assertions on a
self-contained fresh-SQLite fixture (never Nia's real DB): all five
precedence tiers resolve correctly on one shared fixture; no `fact_default`
row violates its shape constraints; an AST scan confirms
`knowledge_resolve.py` and the check itself import the six-value vocabulary
from `writes/knowledge.py` rather than re-typing it; and a
mutation-sensitivity fixture (a member of two factions with levels
`'rumor'` (joined first) and `'knows'` (joined second) on the same fact)
proves two named wrong policies — lowest-wins, first-membership-wins —
would each disagree with the real answer (`'knows'`), so the fixture would
catch either mutation rather than passing vacuously regardless of which
policy ran.

**Scope OUT, explicitly not decided here.** Whether a SECRET faction
membership (`faction_membership.is_secret=TRUE`) resolves that faction's
`fact_default` rows is unsettled — `resolve_knowledge_level`'s faction tier
reads `faction_membership` directly (same table `read_public_memberships`
gates), not through that accessor, so a secret member currently DOES
resolve faction defaults like any other active member. This is a
conscious non-decision, not an oversight: the STOP condition in
BRIEF-0082-c required halting before the live gate if any secret
membership existed in the dev database, which it did not, so the question
never had to be forced.

**Deferral this step makes satisfiable, not acted on.**
`faction.magic_knowledge_level` (`models/canon_faction.py:31`) is a
hardcoded, faction-scoped default knowledge level on a single subject — the
direct ancestor of `fact_default`, and still rendered at
`tick_context.py:543` (`"Connaissance de la magie : "`), untouched by this
step (TICKET-0082's own named deferral). Its reactivation condition — "a
`world_law`-backed fact about magic exists AND a `fact_default` row with
`scope_type='faction'` exists" — has its second half satisfiable as of this
step (the table and its faction-scope write path now exist); the first
half (a `world_law`-backed magic fact) does not yet exist in any seeded
world, so the condition as a whole remains unmet. Logged here per
BRIEF-0082-c's own instruction, not because anything is due.

---

*Co-built with Claude, June 2026.*
