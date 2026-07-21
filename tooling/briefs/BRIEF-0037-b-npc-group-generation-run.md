# BRIEF — Step "NPC group agent: generation run (H1 direct-to-draft)"

## Context

BRIEF-0037-a laid the staging substrate. This step makes a batch runnable:
one `generate_entity_draft("character")` call per NPC (H1 — exact count by
construction, no floor, no clamp), a single batch-level placement plan for
unanchored-location lines (C1/S1), goals attached per draft (F), and inline
row review edits. Backend only; the cockpit panel arrives in BRIEF-0037-c.

## Scope IN

1. **`pt-npc-batch-placement` template** — seed in `scripts/seed_pilot.py`
   (upsert idiom of the existing templates), `usage =
   "npc_batch_placement"`, `world_id = NULL`, authoring model. Content:
   system prompt instructing — given a group brief, spec lines needing
   placement, and a closed list of candidate location names — to return
   ONLY JSON `{"placements": {"<line_index>": ["<location name>", ...]}}`
   with exactly `count` names per listed line, choosing only from the
   candidate list, placements that make narrative sense for each line's
   description. Register in `prompt_registry.py`:
   `"npc_batch_placement": PromptSpec(...)`, call site
   `src/world_engine/npc_group_author.py:_load_placement_template`.

2. **`src/world_engine/npc_group_author.py`** — generation core:
   - `_load_placement_template(db)` — active-template lookup, sibling of
     `link_author._load_pair_template`.
   - `plan_placements(db, batch) -> dict[int, list[str|None]]` — runs at
     most ONCE per batch, on first `run-next` call, result cached into
     `batch.scope["placement_plan"]` (JSON round-trip safe: string keys).
     Lines with a pinned `location_id` are excluded. Zero unanchored
     lines -> no model call, empty plan. One `chat(...,
     format="json")` call through `llm_parse.extract_object`. Resolution
     is S1: each returned name matched case-insensitively against the
     expanded set's location names; a miss, a short list, an oversized
     list, or a whole-call failure degrades to `None` slots -> the NPC
     falls back to `scope["root_location_id"]` with a payload note
     "Placement non résolu — replié sur la racine" (verbatim). A
     placement failure NEVER aborts the batch and never blocks the count
     contract. Journal `placement_call` / `placement_result` /
     `placement_parse_error`.
   - `_line_units(batch) -> list[tuple[int, int]]` — the flattened run
     order: `(line_index, ordinal)` for each NPC, lines in order,
     ordinals 0..count-1. Unit k of the run = `_line_units[npcs_done]`.
   - `_compose_group_npc_brief(group_brief, line, other_lines, siblings,
     faction_ctx, location_name) -> str` — sections in this order,
     mirroring `_compose_npc_brief`'s prose style (region_author.py:262):
     group brief; `--- Cette ligne ---` (the line's description + count);
     `--- Autres lignes du groupe ---` (each other line's description);
     `--- Sa faction ---` (pinned lines only: faction name +
     `entity.description` truncated to 300 chars); `--- Son lieu ---`
     (resolved location name, when known before the call); and when
     `siblings` is non-empty, verbatim:

     ```
     --- Déjà générés pour cette ligne ---
     <name> : <first 120 chars of description>   (one per sibling)
     Ce PNJ doit être clairement distinct de chacun d'eux : autre nom,
     autre tempérament, autre angle sur le même rôle.
     ```
   - `run_next_npc(db, batch) -> dict` — mirror of `link_author.run_pair`
     (link_author.py:398): batch must be `open` (409); all units done ->
     409 "batch already fully generated". Ensure `plan_placements` ran.
     Determine the unit, resolve its target `location_id` (pin > plan >
     root fallback) and faction pin. Call
     `generate_entity_draft("character", brief, db)`. `ok: False` ->
     journal `npc_parse_error`, raise 502, unit left pending — a silence
     is never a verdict, `npcs_done` unchanged. On success:
     - **Faction**: pinned line -> overwrite
       `draft["public"]["faction_id"]` with the pin (the model's own
       `faction_name` resolution is advisory there); unpinned -> keep
       the generator's `_resolve_faction_id` result as-is (may be null).
     - **Name dedup** (BRIEF-42 `_name_key` posture): compare against (a)
       staged non-rejected rows of this batch and (b) active `entity`
       names of the world. A collision stages the row anyway with note
       "Nom en collision avec <name> — à éditer avant commit" (verbatim).
       Never drop, never retry — the count contract forbids silent
       shortfall; the creator resolves it at review.
     - **Goals** (F/G1 posture): `generate_npc_goals(name, description,
       backstory, faction_goals, db)` with `faction_goals` read from the
       resolved faction's `Faction.goals` (None when factionless). On
       `ok` attach the block to `payload["goals"]`; on failure append a
       note — never blocks the row.
     - Stage `NpcBatchRow(kind="draft", line_index, payload={draft,
       location_id, goals, notes}, row_status="proposed")`, increment
       `npcs_done`, commit, journal `npc_call` (prompt) + `npc_result`.
     Returns `{line_index, name, npcs_done, npcs_total}`.
   - `patch_npc_row(db, batch, row_id, payload_patch, row_status)` —
     sibling of `link_author.patch_row` (link_author.py:451): batch open
     only; `row_status` in `("proposed", "rejected")`, reversible.
     Patchable payload fields with their gates: `name`, `description`,
     `appearance`, `backstory`, `aversion` (non-empty str for name,
     plain str otherwise, applied inside `payload["draft"]["public"]`);
     `physical_tier` (int clamped -1..2); `faction_id` (null or an
     active faction entity of the world, else 422); `location_id` (must
     be in `scope["expanded_location_ids"]`, else 422); `goals.long` and
     `goals.shorts` (strings / list of strings). Ids of batch/rows,
     `line_index`, `kind`: unpatchable. Any patch sets
     `row_status="edited"` + `updated_at`; journal `row_patched`.

3. **`src/world_engine/cockpit/routes/npc_agent.py`** — two routes:
   - `POST /api/npc-batches/{id}/run-next` -> `run_next_npc`.
   - `PATCH /api/npc-batches/{id}/rows/{row_id}` -> `patch_npc_row`
     (body `{payload_patch?, row_status?}`, mirror of the link row PATCH).

## Scope OUT

- Commit path, any canon write, knowledge writes (BRIEF-0037-c).
- Frontend (BRIEF-0037-c). Live-testing this step goes through HTTP calls.
- Region pipeline untouched (BRIEF-0037-d).
- No retry loop on name collision or placement miss — degradation paths
  above are exhaustive; do not add re-prompts (the BRIEF-40 top-up
  pattern is precisely what this ticket retires).
- No mini-manifest / one-liner checkpoint (deferral D-0037-2).
- No per-NPC model choice, no new character prompt template —
  `generate_entity_draft` and its `pt-entity-generation` path are used
  AS-IS ("composes the atomic generators; never modifies them",
  chantier 1 doctrine). `_TYPE_FIELDS` untouched.
- No batching of goals calls; one `generate_npc_goals` per NPC, same as
  every existing gate.

## Invariants to defend

- **Model proposes, code judges**: placement names and faction names are
  resolved by code against canon (S1); a model miss degrades, never
  auto-creates. The pin always overrides the model.
- **Single `llm_parse` chokepoint (R2)**: the placement call parses
  through `llm_parse.extract_object` only.
- **Exact-count contract**: the only paths out of a unit are a staged
  row or an explicit 502 leaving it pending. No code path drops a unit.
- **Module budget (R5 / R6)**: `npc_group_author.py` stays under
  1000 lines / 40 functions including BRIEF-0037-c's additions — keep
  helpers lean now.
- **Prompt registry completeness**: the new usage registered with its
  real call site, or the existing `prompt_registry` check fails.

## Done means

- [ ] Batch "3 gardes (faction+location pinned) / 2 marchands (location
      pinned, no faction) / 2 errants (nothing pinned)": seven successive
      `run-next` calls stage exactly 7 `draft` rows; an 8th -> 409.
- [ ] The placement model was called exactly once (journal shows one
      `placement_call`); the two "errants" carry `location_id` values
      from inside the expanded set, or the root + the verbatim fallback
      note.
- [ ] The 3 gardes carry the pinned `faction_id` regardless of what the
      model's `faction_name` said; their names/descriptions are pairwise
      distinct.
- [ ] Rows carry a `goals` block (or a failure note) — spot-check one.
- [ ] Kill Ollama mid-run: `run-next` -> 502, `npcs_done` unchanged;
      restart Ollama, the same unit succeeds.
- [ ] PATCH a row's `location_id` to an id outside the expanded set ->
      422; to a valid one -> `row_status: "edited"`. Reject then
      un-reject a row.
- [ ] `python -m tooling.verify` fully green (registry check sees the
      new usage; `npc_agent_strata` still green).
- [ ] Deployment: backup -> seed (`pt-npc-batch-placement`) -> verify.
- [ ] /review-step and /close-step run.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` entry (H1 mechanics, placement-plan single
  call, collision-stages-with-note, pin-overrides-model) +
  `DECISIONS_INDEX.md`.
- No schema change expected (placement_plan lives inside the existing
  `scope` JSON). If Claude Code finds a schema bump unavoidable, STOP and
  report instead of bumping.
