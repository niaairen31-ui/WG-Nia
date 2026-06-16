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

### What it does

- **Live play** — select an NPC, start a conversation, type turns. Each turn runs
  the three-phase `/say` flow (interpret → NPC → MJ; see below). Overhearing
  proposals (Tier 4) accumulate silently each turn; window analysis runs only
  at scene boundaries.
- Reads conversations and renders them as a chat transcript with the MJ narration
  as primary text and the raw NPC line as a muted audit annotation below each turn.
- Triggers (re-)analysis via `analyzer.analyze_window` — automatically at
  scene-boundary triggers, or manually via the **Analyze** button.
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

---

*Co-built with Claude, June 2026.*
