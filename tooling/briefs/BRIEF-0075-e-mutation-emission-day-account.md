# BRIEF — Step "Mutation emission and the day account"

## Context

After -d, a day resolves: Python rolls, a fact sheet freezes, prose renders it
and a judge accepts it. But nothing reaches canon and the player still cannot
read their day.

This step closes that gap. The fact sheet's computed deltas become
`ProposedMutation` rows in the review queue, the Journée surface renders the
account, and a rendezvous discovered during the day is ARMED so the player can
play the conversation at the keyboard on their next connection.

Decisions in force: **A1** (asynchronous, creator in the loop — every mutation
enters at `proposed`), **O1** (no auto-approve, none, anywhere), **I1** (a
rendezvous is a `Knowledge` row plus an active agenda step, read by the UI to
OPEN the existing conversation surface), **Q1** (the Journée surface, not
Play).

After this brief a full day is playable end to end. That is the point of
putting it before reconciliation.

## Mini-RECON

Measured 2026-08-24 at schema v1.93 unless delegated. Each anchor is a STOP
condition.

- **[M1]** `ProposedMutation` — `models/pipeline.py`. `source_type` in
  `pass_play | conversation | world_tick`; exactly one source anchor set;
  `payload` JSON NOT NULL; `status` default `'proposed'`; `proposed_by`
  default `'local_ai'`; indexes `idx_mutation_status` and
  `idx_mutation_passplay`.
- **[M2]** `_apply_mutation` and the approval routes —
  `src/world_engine/cockpit/mutations.py` and
  `cockpit/routes/mutations.py`. One of the two sanctioned canon-write paths;
  the other is creator CRUD. `tooling/verify/checks/single_canon_write.py`
  guards this, and has a known AST blind spot for `db.execute` calls — do not
  reintroduce that shape.
- **[M3]** `_approve_entity_creation_shortcircuit` — approving an
  `entity_creation` PARKS the germ, authoring nothing (I2). Untouched by -c
  and untouched here.
- **[M4]** The mutation type vocabulary already in use: `knowledge_change`,
  `relation_change`, `resource_change`, `status_change`, `npc_move`,
  `agenda_creation`, `agenda_step_change`, `agenda_delegation`,
  `entity_creation`, `goal_change`. Locate the constant or dispatch that
  enumerates them; if the enumeration is implicit in `_apply_mutation`'s
  branches, report that and STOP before adding a type.
- **[M5]** `Knowledge` — `models/canon.py`. Read its exact shape; item 3
  writes one and must not invent a column. `writes/knowledge.py` is the
  chokepoint.
- **[M6]** `AgendaStep` — partial unique index `idx_agenda_step_one_active`,
  `status` CHECK `IN ('pending','active','completed','failed')`,
  `objective`, `outcome`, `change_history`.
- **[M7]** `routes/day.py` after -b/-c/-d: `_get_or_open_session`,
  `_resolve_player_character`, `_day_dict`, `POST /api/day/declare`,
  `GET /api/days`, `GET /api/day/{id}`, `POST /api/day/{id}/plan`,
  `POST /api/day/{id}/resolve`.
- **[M8]** `frontend/src/journee/` from -a: `Journee.svelte` +
  `journee.svelte.js`, mounted from `App.svelte` with an `active` prop,
  `/journee` in both `SHELL_ROUTES` and `_SHELL_ROUTES`.
- **[M9]** `Batch.local_summary` / `final_result` hold the draft and accepted
  prose after -d, subject to that brief's D3.
- **[DELEGATED D1]** The conversation-opening surface. Determine exactly what
  the legacy Play surface needs in order to open a conversation with a given
  NPC at a given location — the route, the parameters, the preconditions.
  Item 3 arms a rendezvous that this surface consumes. Report the contract
  before writing it. If opening a conversation requires state this brief
  cannot legitimately create, STOP.
- **[DELEGATED D2]** The review queue's rendering of a `pass_play`-sourced
  mutation. `idx_mutation_passplay` exists, so the anchor is expected to be
  supported; confirm the queue actually displays these rows and shows a
  meaningful badge. If it does not, that is in scope for item 2.

**STOP conditions.**

- S1. Any mutation type in the emission whitelist is not handled by
  `_apply_mutation`. Emitting a type nothing can apply is a dead proposal.
- S2. The `pass_play` source branch of the duplicate guard, the queue, or
  `_apply_mutation` is missing or behaves differently from the `conversation`
  branch in a way this brief would have to work around.
- S3. Any code path applies a `pass_play`-sourced mutation without human
  approval. O1 forbids it; if one exists, stop.
- S4. Arming a rendezvous cannot be done without creating scene state (D1).
- S5. `Knowledge` cannot represent "X expects you at Y" without a new column.
  Report what it CAN represent and stop rather than migrating here.

## Scope IN

### 1. Delta computation to mutation payloads — `src/world_engine/day_mutations.py` (new)

- `EMITTED_MUTATION_TYPES: tuple[str, ...] = ("knowledge_change", "relation_change", "resource_change", "agenda_creation", "agenda_step_change", "entity_creation")`.
  A named module constant, and the emission dispatch's key set must equal it
  exactly — the `_SOURCE_LOOKUPS` bijection precedent.
- **`npc_move` is absent, deliberately.** Under N1 the schedule is the
  positional truth; a resolution-emitted move would create a second positional
  authority and put the 0074 amendment back in play. Item 5's check asserts
  its absence by name.
- `emit_mutations(fact_sheet, pass_play, db) -> list[ProposedMutation]`. One
  row per delta. Every row: `source_type='pass_play'`, `pass_play_id` set,
  `conversation_id` and `tick_id` NULL, `status='proposed'`,
  `proposed_by='local_ai'`, and a `rationale` naming the step and the band
  that produced it — a proposal Nia cannot trace back to a beat is not
  reviewable.
- Payload shapes are NOT invented here: each type's payload must match what
  `_apply_mutation`'s existing branch for that type consumes (M4). Where the
  existing shape is ambiguous, report and STOP.
- The module writes rows but applies nothing. No `_apply_mutation` call, no
  status other than `proposed`, anywhere.

### 2. Queue integration

- Confirm (D2) that `pass_play`-sourced rows render in the existing review
  queue with a badge distinguishing them from `conversation` and `TICK` rows.
  If the badge is missing, add it — one label, matching the existing pattern.
- The queue entry links back to the day: day number and the declaration's
  first line, so a proposal can be read in context.
- No new approval path, no bulk-approve for this source, no auto-approve.

### 3. The armed rendezvous (I1)

A rendezvous is a POINTER, not a scene.

- When a step's outcome establishes a future meeting — a contact found, an
  appointment made — the day emits:
  - a `knowledge_change` mutation giving the player character a `Knowledge`
    row stating the meeting in plain terms (M5's shape, no invented column);
    and
  - an `agenda_step_change` mutation setting the next step `active` with an
    `objective` naming the meeting.
- **Both go through the queue.** The rendezvous is armed only once Nia
  approves — consistent with A1, and it means a resolution Nia rejects arms
  nothing.
- The Journée surface reads the ACTIVE step and the matching knowledge and
  offers "play this conversation", which hands off to the existing
  conversation surface per D1's contract.
- **The day never plays the conversation.** No simulated transcript, no
  auto-resolved dialogue. The player types it.
- The objective and the knowledge text are the only things surfaced. No
  `agenda_id`, no `step_id`, no step list — the ticket's Scope OUT stands, and
  "the player sees one active objective" is not "the player sees the agenda".

### 4. The day account — route and surface

- `GET /api/day/{batch_id}` (existing, from -a) is extended. When the day has
  resolved it returns, in addition to -a's fields: the accepted prose; the
  NPCs interacted with, by display name, with role-rendered ones marked as
  roles; the locations visited; the resource, knowledge and skill deltas with,
  for each, whether its mutation is still `proposed` or has been approved; the
  armed rendezvous if any; and the germs emitted, by role hint.
- The four bullets of Nia's original request map onto four blocks of this
  payload: prose, NPCs, locations, gains. A fifth block, "pending review",
  carries everything not yet approved — because under A1 the honest answer to
  "did I gain this?" is sometimes "not until Nia says so".
- Scoping in the query, not after. Nothing from another world is reachable.
- `journee.svelte.js` and `Journee.svelte` render the account below the
  declaration. Read-only. No approve control, no edit control, no delete
  control — review happens in the review queue, which is Nia's surface, not
  the player's.
- A replayed day (a second `history` entry from -d) renders the LATEST
  resolution, and says the day was re-resolved.

### 5. Verify — `tooling/verify/checks/day_mutations.py` (new)

Stdlib `ast` and text only. Fail-closed, vacuity-guarded, each failure naming
the empty collection.

- R1. The emission dispatch's key set equals `EMITTED_MUTATION_TYPES` exactly,
  both directions.
- R2. `"npc_move"` appears nowhere in `day_mutations.py`, `day_resolve.py` or
  `day_plan.py`.
- R3. Every `ProposedMutation(` constructed in the day chain sets
  `source_type='pass_play'` and `status='proposed'`; no constructor or
  assignment in the day chain sets `status` to `approved`, `applied` or any
  other value.
- R4. No module in the day chain calls `_apply_mutation`, and none imports it.
- R5. Every type in `EMITTED_MUTATION_TYPES` is handled by a branch in
  `_apply_mutation` (S1 as a standing check, not a one-time RECON).
- R6. `routes/day.py` still contains no `PUT`, `PATCH` or `DELETE` decorator,
  and no response builder in it references `injected_context` or `history`
  (re-assert -a's R5 now that the payload has grown).
- R7. No response builder in `routes/day.py` emits a key named `agenda_id` or
  `step_id`, and `Journee.svelte` references neither.
- R8. `_approve_entity_creation_shortcircuit` still parks and still authors
  nothing (re-assert -c's R5 from this brief's angle, because this brief
  touches the queue).
- R9. Vacuity guard on every collection above.

## Scope OUT

- **Reconciliation** (R1) — BRIEF-0075-f. This brief still refuses a
  declaration when the player owns a standing active agenda.
- **Auto-approve** (O1) in any form, including a "safe types" shortcut for
  `resource_change`. Its own ticket, later.
- **`npc_move` emission** (N1).
- **Location germs**, still. Persons only.
- **Simulating a conversation.** The rendezvous is armed and handed off; the
  day never writes dialogue. Comparing a played conversation to a simulated one
  remains a later, cheap experiment.
- **TICKET-0069.** The handoff to the conversation surface uses that surface as
  it stands; do not migrate it, do not restyle it.
- **`world.current_phase`** — not read (P2), not advanced. Nia advances it by
  hand.
- **`schedule_reads.py`** — untouched.
- **A player-facing approval affordance.** The player never approves anything.
- **Prompt-injection filtering.** `flagged` stays unwritten; `flag_reason`
  still does not exist.

## Invariants to defend

- **Two sanctioned canon-write paths only.** This brief adds a PROPOSER, not a
  writer. R3 and R4 are the tripwires, and `single_canon_write.py` must stay
  green.
- **The resolver never authors** (C1 / I2). R8 protects it from a queue-side
  regression.
- **The positional wall** (N1, BRIEF-0074-a-amendment-1). R2 is the tripwire.
- **Query-level scoping.** The account route filters by active world in the
  query.
- **Secrets stay structurally excluded.** The account is built from the fact
  sheet and from approved canon, never from a raw registry read that could
  carry a secret the player should not hold.
- **No structure without a reader.** Every field added to the account payload
  is rendered by `Journee.svelte` in this same brief, or it does not go in.

## Done means

- [ ] A resolved day emits one `ProposedMutation` per computed delta, all at
      `status='proposed'`, all with `pass_play_id` set and `conversation_id`
      and `tick_id` NULL.
- [ ] Every emitted type is applied successfully by `_apply_mutation` on
      approval; approving each type once, live, leaves canon correct.
- [ ] No `npc_move` row is ever emitted by the day chain.
- [ ] Rejecting a proposal leaves canon untouched and the account shows the
      delta as still pending.
- [ ] `pass_play`-sourced rows appear in the review queue with a
      distinguishing badge and a link back to the day.
- [ ] An `entity_creation` germ approved from the queue is still PARKED — row
      counts before and after confirm no `Entity` was created.
- [ ] A day that establishes a meeting arms a rendezvous only AFTER the two
      mutations are approved; before approval, nothing is armed.
- [ ] The Journée surface shows the armed objective and offers the handoff;
      following it opens the conversation surface with the right NPC, and the
      player types the conversation.
- [ ] `GET /api/day/{id}` on a resolved day returns prose, NPCs, locations,
      gains and a pending-review block, with role-rendered NPCs marked as
      roles.
- [ ] The account payload and `Journee.svelte` contain no `agenda_id` and no
      `step_id`.
- [ ] A replayed day renders the latest resolution and says so.
- [ ] `python tooling/verify/checks/day_mutations.py` green, each of R1–R9
      observed FAILING under a deliberate local mutation before revert.
- [ ] `single_canon_write.py`, `day_narration.py`, `day_concordance.py`,
      `day_plan.py`, `pipeline_wiring.py`, `json_ui_boundary.py`,
      `npc_schedule.py`, `corpus_gate.py` all green.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `tooling/standards/ARCHITECTURE_DECISIONS.md`: a subsection on A1/O1 — the
  day chain is a PROPOSER and never a writer; why `npc_move` is excluded; and
  the I1 rendezvous shape, stating that a rendezvous is a pointer read by the
  UI, not a pre-opened scene.
- `tooling/standards/DECISIONS_INDEX.md`: A1, I1, O1.
- `CLAUDE.md`: only if it enumerates the canon-write paths or the mutation
  source types; if so, note that `pass_play` is now live. Otherwise leave it —
  TICKET-0071's hygiene pass owns that file.
- No schema change expected, so no version bump. If M5 forces one for the
  rendezvous knowledge, that is S5 and a STOP, not a quiet migration.
