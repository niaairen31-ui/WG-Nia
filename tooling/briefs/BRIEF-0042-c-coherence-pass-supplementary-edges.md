# BRIEF - Step "coherence pass: supplementary edges (Phase C)"

## Context
TICKET-0042, step 3 of 5. The manifest gives a guaranteed-connected SPANNING
TREE (BRIEF-0042-a) and Phase B gives one fiche per room (BRIEF-0042-b). This
step is D3, relocated (intake decision, 2026-07-23) to run AFTER Phase B: one
model call sees the full generated batch and proposes SUPPLEMENTARY edges
(service corridor, hidden stair) over the tree, plus optional incoherence notes.
Running after the fiches means the edges are motivated by real content, not
guessed at the manifest stage. Every proposed edge is resolved by NAME in code;
an unresolved name is a note, never a new room or a canon write (L1). This is the
heaviest token call in the ticket (it sees all fiches) -- measure at 25.

## Mini-RECON (verify before writing a line; report any drift, do not adapt silently)
Anchors on live `main`, schema v1.85.
- L1 name-resolution precedent: `cockpit/routes/regions.py:101
  _region_resolve_link_target` -- resolves a link target by committed name then
  DB exact-match (case-insensitive, whitespace-stripped), NEVER auto-creates.
  Mirror the RESOLUTION shape (name -> id-or-note), but resolve against the
  in-flight batch + canon siblings, since nothing is committed yet.
- Canon siblings under the anchor: `location.parent_location_id == anchor_id`;
  their existing `connects_to` edges from `relation` (type `connects_to`). These
  are candidate targets for a supplementary edge that leaves the batch and joins
  an existing sibling (D3 case b).
- `llm_parse.py` (R2) -- the coherence response parses through it.
- `prompt_registry.py:190` -- register the new spec beside `region_manifest`.
- Confirm the review descriptor's `graphExtraEdges` contract expects
  `[{id, entity_a_id, entity_b_id, kind:'connection'}]` (`index.html:5991`
  `reviewGraphData`; region's adapter `regionReviewDescriptor:6071`). The edges
  this pass produces feed that adapter in BRIEF-0042-d; shape them compatibly
  (local_id-keyed, resolved to draft `local_id` or canon sibling id).

## Scope IN

1. **`propose_batch_coherence(manifest: dict, drafts: dict, anchor: dict,
   db: Session) -> dict`** in `room_batch_author.py`. One model call. Assemble a
   context of: the anchor (name/type/one-line); every GENERATED room
   (name + type + description one-line from Phase B) with its `local_id`; the
   spanning-tree parent of each; and the canon siblings under the anchor
   (name + type) as external candidates. Instruct the model to propose 0..N
   supplementary undirected edges, each `{a, b, reason}` where `a`/`b` are room
   names (batch) or sibling names (canon), plus an optional list of short
   incoherence notes (advisory prose the creator reads). Respond JSON only.

2. **Resolve every proposed edge by name (L1), in code.** For each `{a, b}`:
   - Build a name index: `{fold(name) -> local_id}` for batch rooms +
     `{fold(name) -> entity_id}` for canon siblings under the anchor
     (trim + lowercase, mirroring `_region_resolve_link_target`).
   - Resolve `a` and `b` independently. If EITHER fails to resolve, OR they
     resolve to the same node, OR the edge duplicates a spanning-tree edge: drop
     the edge into `unresolved` with `{a, b, reason}`. NEVER create a room.
   - A resolved edge becomes `{id, a_id, b_id, a_local, b_local, reason}` where
     `a_id`/`b_id` are draft `local_id`s or canon sibling entity ids. Keep enough
     to (i) render it dashed in the graph and (ii) commit it via
     `connect_locations` in BRIEF-0042-e.

3. **Retry-once-then-skip (R, consistent with Phase B).** The coherence call
   retries once on failure; a second failure yields `{"ok": False, "edges": [],
   "unresolved": [], "notes": ["Passe de coherence indisponible"]}` -- the batch
   proceeds with the spanning tree ONLY. The coherence pass is never blocking (a
   batch with no supplementary edges is valid).

4. **New prompt template `room_batch_coherence`**, registered like
   `room_batch_manifest`. Body: given the generated rooms and their tree, propose
   passages that a designer would add for flow (shortcuts, service routes, hidden
   connections), referencing rooms and existing siblings BY NAME; do not invent
   room names not present; keep it sparse (a few edges, not a mesh). Version +
   changelog owned by Claude Code.

5. **Return shape:** `{"ok": bool, "edges": [<resolved>...], "unresolved":
   [...], "notes": [...]}`.

## Scope OUT
- Any semantic re-write of fiche content. This pass proposes EDGES + advisory
  notes; it does not edit descriptions, rename rooms, or change types. (A full
  O(N^2) pairwise semantic re-check is a NAMED DEFERRAL if Nia wants it later --
  do not build it here.)
- Auto-creating a room for an unresolved name (L1). Unresolved -> note.
- Directed edges. `connects_to` is mutual; edges are undirected pairs.
- Any canon write, `db.commit()`, door materialization (BRIEF-0042-e).
- Rendering the graph (BRIEF-0042-d). This step produces edge DATA only.
- Compacting the peer context UNLESS a measured 25-room call overflows the model
  context -- if it does, report the token count and compact to name + one-line
  per room (drop descriptions), as a separate finding, not a silent change.

## Invariants to defend
- **Exclusion is structural, never instructional.** The coherence context is
  built from Phase B fiches + non-hidden sibling data; do not pull hidden
  subculture or NPC data into this prompt.
- **L1 -- naming a location never creates it.** Enforced in the resolver, in
  code, not by prompt wording.
- **Model proposes, code judges.** Edges are model-proposed; validity (resolves,
  distinct, non-duplicate) is judged in code.
- **Single llm_parse chokepoint (R2).**
- **No canon without the commit path.** Zero writes here.

## Done means
- [ ] On a batch that warrants it, `propose_batch_coherence` returns >= 1
      resolved edge with a `reason`, rendered later as a dashed graph edge.
- [ ] An edge naming a room that does not exist lands in `unresolved` with a
      reason; no room is created; no write occurs.
- [ ] An edge between a batch room and a real canon sibling under the anchor
      resolves to the sibling's entity id.
- [ ] A forced coherence-call failure retries once, then returns `ok: False`
      with empty edges and the batch still proceeds on the tree alone.
- [ ] A 25-room coherence call is exercised once and its token usage is reported
      (to confirm no compaction is needed, or to trigger it as a finding).
- [ ] `/review-step` and `/close-step` run.

## Docs to update
- CLAUDE.md: note `propose_batch_coherence` under `room_batch_author.py`.
- ARCHITECTURE_DECISIONS.md: append "D3 relocated to a post-Phase-B coherence
  pass" with the rationale (edges motivated by generated content) and the named
  deferral (O(N^2) semantic re-check) for the record.
- No schema change.
