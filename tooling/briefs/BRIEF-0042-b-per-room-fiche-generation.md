# BRIEF - Step "per-room fiche generation (Phase B)"

## Context
TICKET-0042, step 2 of 5. BRIEF-0042-a returns a validated, creator-editable
manifest (spanning tree, typed rooms). This step turns the edited manifest into
one full location fiche per room: one model call each, each call seeing the whole
manifest, mirroring the region generator's Phase B. The type is NOT re-proposed
here -- it is taken verbatim from the manifest (P1), so the enum gate is never
touched. NO canon is written; fiches are ephemeral until the commit route
(BRIEF-0042-e).

## Mini-RECON (verify before writing a line; report any drift, do not adapt silently)
Anchors on live `main`, schema v1.85.
- Region Phase B precedent: `region_author.py:298`
  `generate_entity_draft("location", composite_brief, db)` per location, brief
  composed by `_compose_location_brief:201`. It reuses the ATOMIC author's model
  call for content. Mirror this shape.
- `entity_author.generate_entity_draft(entity_type, brief, db)` (`:506`) ->
  `_entity_draft_call:389` -> `_entity_location_draft:432`. Read `:432-452`:
  confirm it validates `location_type` via `_validate_location_type:247` (the
  enum gate). This step must NOT let that value win -- the manifest type
  overrides whatever the model echoes.
- `_normalize_sensed_links:371` shapes `sensed_links`; the fiche keeps it (the
  commit's link resolution consumes it, BRIEF-0042-e).
- Confirm the region generator drops a failed entity into `skipped` and
  continues (`generate_region_draft:325` region loop). Mirror the `skipped`
  shape; the retry-once is new here.

## Scope IN

1. **`generate_room_batch_draft(manifest: dict, anchor: dict, db: Session) ->
   dict`** in `room_batch_author.py`. Iterate the manifest's rooms in order. For
   each room:
   - Compose a text brief (`_compose_room_brief(anchor, manifest, this_room)`):
     the anchor's name + type + one-line; the full manifest as peer context (each
     room's name + one_liner + location_type + parent_room); and THIS room's name
     + one_liner + type highlighted as the room to write. Manifest-sourced only
     (no DB re-read, no secrets).
   - Call `generate_entity_draft("location", brief, db)` for the CONTENT
     (description, access_level, subculture, sensed_links).
   - **P1 type override.** After the call, set the fiche's public
     `location_type` to the room's MANIFEST type verbatim, discarding whatever
     the atomic author produced (it may have repli-fallen to "other"). Record a
     note if the two differ, for transparency, but the manifest wins
     unconditionally.
   - Attach `local_id` (a stable per-batch id, e.g. a slug of the room name +
     index) and `parent_room` (carried from the manifest) to the fiche entry so
     the review descriptor (BRIEF-0042-d) and commit (BRIEF-0042-e) can wire the
     tree.

2. **Retry-once-then-skip (R).** Wrap each room's model call. On failure (parse
   error, exception, empty draft): retry the SAME call ONCE. If the retry also
   fails, drop the room into `skipped` with `{local_id, name, reason}` and
   continue. A skipped internal node's children are NOT reparented here -- they
   keep their `parent_room` pointing at the now-absent room; the review cascade
   (M2, `fallbackParentId` = anchor) reparents them to the anchor at review time
   (R1). This is deliberate: no new reparenting mechanism in Phase B.

3. **Return shape:** `{"ok": bool, "rooms": [<fiche entry>...], "skipped":
   [...], "notes": [...]}`. Each fiche entry: `{"local_id", "name",
   "parent_room", "result": {"draft": {"public": {...}, "secret": {...}}}}` --
   the same envelope region uses, so the review descriptor can read it uniformly.

## Scope OUT
- Supplementary edges / coherence pass (BRIEF-0042-c). Phase B writes fiches from
  the manifest as-is; it proposes no new edges.
- Reparenting orphaned children of a skipped node (that is the review cascade's
  job, BRIEF-0042-d, via `fallbackParentId`). Do NOT reparent in Phase B.
- Any canon write, `db.commit()`, door materialization.
- Re-validating or re-proposing `location_type` (the manifest is authoritative).
- Touching `entity_author._entity_location_draft` / `_validate_location_type` /
  `_LOCATION_TYPES`. Reuse `generate_entity_draft` unchanged; override the type
  in THIS module after the call.
- More than one retry, or exponential backoff. Exactly one retry (R).

## Invariants to defend
- **Model proposes, code judges.** The fiche content is the model's; the type is
  the manifest's (creator-owned); neither becomes canon here.
- **No canon without the commit path.** Still zero writes in this module.
- **Single llm_parse chokepoint (R2).** The fiche call already routes through the
  atomic author's parse; do not add a second parse path.
- **Module budget (R5) / 80-line functions (R1).** `_compose_room_brief` and the
  per-room loop must stay within budget; extract if the loop body grows past 80
  lines.

## Done means
- [ ] `generate_room_batch_draft` over a 5-room manifest returns 5 fiche entries,
      each with a non-empty description and the room's manifest `location_type`
      (verify a room typed "room" in the manifest keeps "room" in the fiche, even
      if the atomic author would have said "other").
- [ ] A room forced to fail (e.g. a brief the model chokes on, or a mocked
      failure) is retried once; on second failure it appears in `skipped` and the
      other rooms still generate.
- [ ] A skipped INTERNAL node's children still carry their original
      `parent_room` in the returned entries (they are NOT reparented in Phase B).
- [ ] `/review-step` and `/close-step` run.

## Docs to update
- CLAUDE.md: note `generate_room_batch_draft` under `room_batch_author.py`.
- No schema change.
