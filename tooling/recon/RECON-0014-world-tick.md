# RECON-0014 — world tick (off-screen NPC advancement)

Date: 2026-07-07
Branch inspected: `main` (post TICKET-0013 merge; schema head v1.69)
Mode: report-only. No actions taken.

Locked decisions in force: C2, I1, J1, H2 (pre-locked); K2, L3, M3, P1, Q1, R3
(intake 2026-07-07). J3 (auto-apply) remains a rejected/named-deferred decision.

---

## F1 — `ProposedMutation` accepts a third source without migration

`src/world_engine/models.py:556-596` — `source_type` is a free string
(comment: `pass_play | conversation`), and both `pass_play_id` and
`conversation_id` are nullable with no CHECK constraint. A tick source
(`source_type="world_tick"`, both FKs NULL, `proposed_by="local_ai_tick"`)
fits the existing table with **no schema change**. `_mutation_dict`
(`cockpit/app.py:678-695`) already surfaces `source_type` and `proposed_by`
to the queue UI — the P1 label has a channel without new structure.

## F2 — CRITICAL: the duplicate-application guard is bypassed for any
## proposal with NULL `conversation_id`

`cockpit/app.py:753-755` (`_find_applied_duplicate`):

```python
if not mut.conversation_id:
    return None
```

Every tick proposal will skip the guard entirely. Exposure by type:

- `goal_change complete/abandon` — **naturally idempotent at apply**:
  `cockpit/app.py:1053-1060` requires exactly one ACTIVE goal matching the
  normalized text; a second apply finds none and returns "Needs attention".
  Safe.
- `goal_change create_short` — **exposed**: `cockpit/app.py:1069-1082`
  inserts unconditionally (S1: no active-count check by design). A re-run
  tick re-proposing the same short, approved twice, writes two identical
  active goals.
- `new_knowledge` — **exposed**: the identity dedup for
  (conversation, entity_id, subject) lives in this guard
  (`cockpit/app.py:773-782`). Double apply = duplicate knowledge row,
  context inflation. (Whether the `new_knowledge` apply branch has its own
  existence check must be verified in the brief; the guard docstring
  implies it does not.)
- `relation_change` — excluded from the guard **by doctrine**
  (`cockpit/app.py:720-724`, accumulating deltas). Tick re-runs re-proposing
  a delta and double-approval = double delta. This is inherent to L3 and
  must be surfaced to the creator (R3 summary + queue visibility), not
  guarded.

The emit-side dedup in `analyze_window` (`analyzer.py:824-858`, `covered`
set via `_mutation_match_key` `analyzer.py:711-728`) is also
conversation-scoped. The tick needs its own emit-side dedup within one
invocation regardless of the Y decision.

## F3 — Normalization is conversation-coupled; the tick needs a parallel
## path with the same O1 discipline

`analyzer.py:252-433` — `_normalize_to_schema(raw_item, conv, db)` reads
`conv.player_id`, `conv.npc_id`, `conv.world_id` for defaults:

- `new_knowledge` attribution defaults to player-vs-npc heuristics
  (`analyzer.py:291-307`) — meaningless in a tick.
- `relation_change` defaults `entity_b_id` to `conv.player_id`
  (`analyzer.py:308-323`) — wrong default for a tick.
- `goal_change` O1 branch forces `npc_id = conv.npc_id`
  (`analyzer.py:398-424`), action coerced via `_GOAL_ACTION_MAP`, shorts
  only at creation.

A tick normalizer must force `npc_id` (and `relation_change.entity_a_id`)
to the **ticked NPC**, code-side, unconditionally — same structural pattern,
new anchor (the tick has no `Conversation`). `_GOAL_ACTION_MAP`,
`_validate_item`, `_extract_json_array`, `_content_to_subject_slug` are
reusable as-is.

## F4 — Entity references: the model has no IDs; unresolved references are
## dropped, never guessed

Doctrine holds in code: the window rubric's payload shapes name ids
(`scripts/seed_pilot.py:245-251`) but the normalizer never validates them;
`relation_change` with unresolved endpoints is **dropped**
(`analyzer.py:380-388` — "a silent wrong attribution is worse than a
dropped proposal"). There is no name→id resolution anywhere in
`analyzer.py`.

For the tick, the model must reference other entities **by name**; code
must build a resolution roster (scope NPCs + the ticked NPC's existing
relation targets) and resolve case-insensitively; unresolved → drop with a
note (R3). `entity_a_id` never comes from the model.

## F5 — K2 raw material inventory (what a tick briefing can be built from)

All accessors exist; none is tick-shaped yet:

- **Goals**: active 1 long + 2 shorts query pattern,
  `context.py:225-243`.
- **Relations**: all edges of one NPC + perception rendering,
  `context.py:269-278` with `_perceived_target`/`_render_perception`
  (`context.py:114-129`).
- **Knowledge**: the dialogue assembler gates by `is_secret` and
  `share_threshold` vs interlocutor intensity (`context.py:285-293`). A
  tick has **no interlocutor** — inclusion policy is decision T.
- **Affiliations**: `read_public_memberships` (`context.py:131-168`)
  resolves `cover_role ?? role` and excludes `is_secret` memberships — a
  public façade. The NPC's true role and secret memberships are its own
  interiority — decision T.
- **Faction posture**: `Faction.philosophy`, `internal_tensions`,
  `aversion`, and the dormant prose `goals` (`models.py:167-198`;
  `Faction.goals` gained its first reader as generator INPUT in 0013 —
  the tick would be its second).
- **Location**: `Entity.description` + `Location.subculture` values
  (`context.py:246-266`).

## F6 — N1 verify check: allowlist extension required; positional fragility
## argues for a new module

`tooling/verify/checks/npc_goal_read.py:31-39` — `ALLOWED_MODULES` is
explicit. Rule 2 scans `context.py` from `assemble_mj_context`'s lineno to
EOF: **any function added to `context.py` below the MJ assembler that
touches `NpcGoal` fails the check**. Recommendation: the K2 builder lives
in a new module (`src/world_engine/tick.py`), added to the allowlist —
clean entry, no positional fragility, and the MJ boundary rule stays
byte-identical.

## F7 — Prompt delivery pattern confirmed and reusable

- Template registration + seed constants: `scripts/seed_pilot.py:1448`
  (`pt-npc-goals`) is the closest precedent; new `pt-world-tick` follows
  the same spec shape with a new `usage` string.
- Loader precedent: `load_analysis_prompt(db, world_id, usage=...)`
  (`analyzer.py:166-192`) is generic over `usage` — reusable verbatim.
- Model routing: `effective_model(template, default)`
  (`prompt_registry.py:40-42`); Q1 default = `ollama_client.DEFAULT_MODEL`
  (gameplay model), overridable per-template without code.
- Live delivery: one-shot idempotent script, precedent
  `scripts/apply_ticket_0013_prompt_updates.py`, through
  `write_prompt_version`.

## F8 — Queue and endpoint shapes

- `GET /api/mutations` is a flat status-filtered list
  (`cockpit/app.py:4697-4718`); `POST /api/mutations/batch-review`
  (`cockpit/app.py:4839`) already exists — a tick batch can be reviewed
  efficiently with zero new structure (P1 holds).
- Endpoint precedent for a creator-triggered batch action with per-item
  degradation: `POST /npc-goals/backfill` (`cockpit/crud.py:977-1055`).
  BUT the tick writes `ProposedMutation` rows (proposal pipeline, not
  direct authority) — it belongs beside the analyzer-facing endpoints in
  `cockpit/app.py`, not in `crud.py` (which is the creator-CRUD channel,
  `crud.py:1-30`).

---

## Residual design questions raised by the code (blocks T, Y, E)

- **T** — tick briefing interiority depth: own secret knowledge? true
  (non-cover) roles and secret memberships? (F5)
- **Y** — re-run/duplicate posture given the F2 guard bypass: emit-time
  dedup only, vs a `tick_id` column (would revisit P1, but with two
  concrete readers: the guard's match key and the queue label).
- **E** — confirm name-based reference + roster resolution + drop-unresolved
  + `entity_a` forced code-side (F4). Effectively settled by doctrine;
  presented for explicit confirmation.

No brief will be authored while T and Y are open.
