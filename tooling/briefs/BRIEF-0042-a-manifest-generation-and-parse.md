# BRIEF - Step "room batch manifest generation + parse"

## Context
TICKET-0042, step 1 of 5. This is the first surface that lets a location fiche
carry a spatial, parental shape: `entity_author._entity_location_draft`
(`entity_author.py:432`) produces name / description / location_type /
access_level / subculture / sensed_links and NOTHING parental or batch-aware.
This step adds the Phase A manifest generator: given a creator-chosen anchor and
a count (3..25), one model call proposes a manifest of rooms, and code judges it
into a validated spanning tree. NO canon is written; the manifest is ephemeral,
returned for Phase A editing. Phase B (fiches) is BRIEF-0042-b; the coherence
pass is BRIEF-0042-c; frontend + review is BRIEF-0042-d; the atomic commit is
BRIEF-0042-e.

## Mini-RECON (verify before writing a line; report any drift, do not adapt silently)
Anchors on live `main`, schema v1.85 (0040/0041/0043 landed).
- `region_author.py` is the two-phase precedent. Manifest parse/normalize:
  `_dedupe_by_name:70`, `_normalize_root_location:103`,
  `_normalize_location_parents:127`, `_normalize_manifest:148`,
  `_parse_manifest_response:169`, `generate_region_manifest:218`. Reuse their
  SHAPE (parse -> normalize -> `{ok, manifest, notes, skipped}`), not their code.
- `_normalize_location_parents` is the direct precedent for K1 name-resolved,
  cycle-detected parent linking (region's `parent_local_id`). Read it; mirror
  its cycle handling.
- Catalog reader for P1 type validation: `spatial_author.py:134 _catalog_row`
  (returns the `LocationTypeCatalog` row by world_id + name) and
  `location_type_template:166`. Type validation reuses `_catalog_row` presence,
  NOT `entity_author._validate_location_type:247`.
- I1 subculture structural exclusion precedent: `context.py:291` and `:567`
  filter `LocationSubculture.is_hidden == False` AT QUERY CONSTRUCTION. The
  anchor-context reader here MUST filter the same way, in the query, never in a
  post-filter.
- Sibling context (I1): siblings are locations whose `location.parent_location_id
  == anchor_id`. Existing `connects_to` edges among them come from the `relation`
  table (`relation.type == 'connects_to'`). Confirm the location extension +
  relation model import paths in `models/`.
- `prompt_registry.py:190` registers `region_manifest` as `PromptSpec(...)`. A
  new `room_batch_manifest` spec is registered the same way.
- `llm_parse.py` is the single parse chokepoint (R2). The manifest response is
  parsed through it, exactly as region's `_parse_manifest_response` does.
- `AUTHOR_MODEL = "llama3.1:8b"` (`entity_author.py:39`); the manifest call uses
  it via `effective_model(template, AUTHOR_MODEL)`.

## Scope IN

1. **New module `src/world_engine/room_batch_author.py`.** Header comment
   verbatim:
   ```
   """Room batch orchestrator (TICKET-0042). Two phases mirroring the region
   generator: generate_room_batch_manifest(anchor_id, count, db) runs the
   manifest model call and returns it for creator editing (Phase A);
   generate_room_batch_draft (BRIEF-0042-b) turns the edited manifest into one
   fiche per room. Writes NO canon -- every draft is ephemeral until the atomic
   commit route (BRIEF-0042-e). Type authority is the manifest, validated
   against location_type_catalog (P1), NEVER the _LOCATION_TYPES enum."""
   ```

2. **`generate_room_batch_manifest(anchor_id: str, count: int, db: Session) ->
   dict`.** Clamp `count` to `[3, 25]` at the boundary (this is the ONLY code
   clamp -- it bounds the request, per S; it never pads a short model response).
   Assemble the I1 context, call the model, parse + normalize, return
   `{"ok": bool, "manifest": {...}, "notes": [...], "skipped": [...],
   "anchor": {...}}`.

3. **I1 context assembly** (`_compose_batch_context` or similar, one helper):
   - Anchor fiche: `name`, `location_type`, `description`, `access_level`, and
     the anchor's `location_subculture` rows filtered `is_hidden == False` IN
     THE QUERY (mirror `context.py:291`).
   - Canon siblings under the anchor (`parent_location_id == anchor_id`): each as
     `{name, location_type, one_line}` where `one_line` is the first sentence /
     first ~140 chars of the sibling's description. Names only, no secrets.
   - Existing `connects_to` edges among those siblings, as `[{a_name, b_name}]`.
   - NOTHING else: no hidden subculture, no `discoverable_detail`, no NPC.

4. **Manifest schema** (per room): `{ "name": str, "one_liner": str,
   "location_type": str, "parent_room": str|null }`. `parent_room` is a manifest
   room NAME or the anchor NAME or null. The model is instructed that null / the
   anchor name both mean "attach to the anchor".

5. **Parse + normalize** (`_parse_batch_manifest_response`, `_normalize_batch_
   manifest`), routing the raw response through `llm_parse` (R2):
   - Dedupe rooms by case-insensitive name (mirror `_dedupe_by_name`); later
     duplicates -> `skipped` with reason.
   - **K1 spanning tree.** Resolve each `parent_room` by case-insensitive,
     whitespace-stripped name against (the surviving manifest rooms | the anchor
     name). Detect cycles (a room reachable from itself through parents). On an
     unresolved name OR a cycle OR self-parent: force-attach to the anchor
     (`parent_room = null`, meaning anchor) and append a note. The result is a
     guaranteed-connected tree rooted at the anchor. Mirror
     `_normalize_location_parents`.
   - **P1 type validation.** For each room, look up `location_type` via
     `_catalog_row(db, world_id, name=location_type)`. If the row is absent,
     KEEP the type string verbatim (do NOT repli-fall to "other") and append a
     note: `f"Type '{t}' absent du catalogue -- ce lieu naitra sans bounds tant
     que le type n'est pas classifie"`. The creator resolves it in Phase A. A
     type present but with NULL template is left as-is (born without bounds,
     legitimately). NEVER call `_validate_location_type`.
   - Return the normalized manifest as `{"rooms": [...]}` plus `notes` and
     `skipped`.

6. **New prompt template `room_batch_manifest`**, registered in
   `prompt_registry.py` beside `region_manifest` (`:190`) as a `PromptSpec`, and
   its default body stored via `prompt_store.py`. The prompt instructs the model
   to: propose exactly `count` rooms coherent with the anchor and its siblings;
   give each a short name, a ONE-LINE hook, a `location_type` (prefer a type from
   the provided catalog list; a room-like interior is usually "room"); set
   `parent_room` to another proposed room's name to build depth, or null / the
   anchor name to attach at the top; and OPTIONALLY nothing else -- supplementary
   edges are a later pass, not this one. Respond as JSON only, no prose. Include
   the catalog type names available for this world in the assembled prompt so the
   model prefers existing types (P1). Version + changelog owned by Claude Code.

## Scope OUT
- Phase B fiches (BRIEF-0042-b). This step returns a manifest ONLY.
- Supplementary edges / D3 / the coherence pass (BRIEF-0042-c). The manifest
  carries the SPANNING TREE ONLY (`parent_room`), no extra edges. Do not add an
  `edges` field to the manifest here.
- Any canon write, any `db.commit()`, any door materialization (BRIEF-0042-e).
- Any frontend (BRIEF-0042-d).
- L2 (unknown name becomes a room). An unresolved parent_room force-attaches to
  the anchor; it NEVER mints a room.
- Modifying `entity_author._validate_location_type` or `_LOCATION_TYPES`. The
  batch bypasses them by construction (P1); the enum stays frozen for the atomic
  author.
- Q0-b geometry, envelope constraints, coordinates.

## Invariants to defend
- **Structural exclusion (secrets at query construction).** The anchor subculture
  read MUST filter `is_hidden == False` in the SQL, not after fetch. This is the
  single most likely place to leak a hidden line into a model prompt.
- **No structure without a reader / no canon without the commit path.** This
  module returns data; it must not acquire a write path. The verify check
  (BRIEF-0042-e / ticket) asserts zero canon writes here.
- **Model proposes, code judges.** The spanning tree is model-proposed but the
  connectivity guarantee (rooted at anchor, acyclic) is enforced in code, not
  trusted from the response.
- **Single llm_parse chokepoint (R2).** Route the raw manifest through it.

## Done means
- [ ] `python -c "from world_engine.room_batch_author import
      generate_room_batch_manifest"` imports clean.
- [ ] In a live session (or a scripted call), `generate_room_batch_manifest`
      against a real anchor returns `{"ok": True, "manifest": {"rooms": [...]},
      ...}` with 3..25 rooms, each having name / one_liner / location_type /
      parent_room.
- [ ] A manifest whose model response contains a `parent_room` cycle, an unknown
      parent name, and a self-parent yields a tree where all three are attached
      to the anchor, each with a note.
- [ ] A room whose `location_type` is not in the catalog keeps its type string
      and carries the "absent du catalogue" note (NOT repli-fallen to "other").
- [ ] The anchor context passed to the model contains zero `is_hidden = TRUE`
      subculture lines (verify by seeding one hidden line and confirming absence
      from the assembled prompt).
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update
- CLAUDE.md: register `room_batch_author.py` in the File structure section
  (pointer-fresh, no archaeology).
- ARCHITECTURE_DECISIONS.md: append the P1 decision (manifest is the type
  authority; batch bypasses the enum; catalog is validated) with its trigger.
- No schema change (`schema_version_touched: none`) -- no changelog entry.
