# BRIEF — Step "Link-agent coherence pass and commit" (BRIEF-0036-c)

Ticket: TICKET-0036. Anchored on RECON-0036. Requires 0036-a/b landed.

## Context

Pairs are staged (0036-b). This step adds the final pass: mechanical
fail-closed checks plus a model review over the staged batch AND the
full canon character graph (E1-tout-le-graphe), producing pre-validated
one-click patches (W-ok), and the commit endpoint that turns accepted
staged rows into canon through write_relation/write_knowledge.

## Pre-exec verification (report, then proceed or stop)

- cockpit/crud/relations.py:262 global graph endpoint still excludes
  _RELATION_GRAPH_EXCLUDED_TYPES in the WHERE clause; the exclusion
  constant is importable or extractable to a shared location.
- writes/relations.py write_relation mode="set" update-in-place still
  snapshots change_history first (:142-148 area).
- writes/knowledge.py write_knowledge mode="update" signature unchanged.
If any anchor fails: STOP, report, no code.

## Scope IN

1. Prompt registration "npc_link_coherence": surface="authoring",
   world_scoped=True, dry_run_capable=False, call_sites=
   ("src/world_engine/link_author.py:_load_coherence_template",),
   default_model=_author_model. Seed default template verbatim:

   "You review a proposed batch of NPC relations and knowledge for the
   world {world_name}, against the existing canon graph. Find
   contradictions and implausibilities. Do NOT invent new links.

   Staged batch: {staged_serialized}
   Canon graph: {canon_serialized}{truncation_marker}

   Reply ONLY with JSON: {\"findings\": [ ... ]}
   Each finding:
   {\"target\": {\"scope\": \"staged\"|\"canon\", \"id\": \"<row id or
   relation/knowledge id, copied exactly from the input>\"},
   \"problem\": \"one sentence\",
   \"patch\": null or {\"field\": \"<field name>\", \"new_value\": ...},
   \"rationale\": \"one sentence\"}
   A finding with patch null is a flag for the creator with no proposed
   fix. Typical problems: mutual hostility alongside intimate secret
   knowledge with no shared_secret link; A knows B's secret but B's
   sheet says nobody does; intensity contradicting notes; duplicate or
   near-duplicate staged rows; staged row contradicting a canon
   relation."

2. Serialization, code-owned, in link_author.py (or link_context.py):
   - staged_serialized: every non-rejected row of the batch, with its
     row id, kind, resolved names, full payload.
   - canon_serialized: all relations between active characters of the
     world (SAME structural exclusion as the global graph endpoint --
     reuse/extract the constant, never a local copy) + all knowledge
     rows whose subject matches npc:{id} OR whose entity is in the
     batch roster. Deterministic order.
   - Budget (RECON-0036 R-1): serialize canon in deterministic priority
     (rows touching batch NPCs first, then the rest); hard character
     budget CANON_SERIAL_BUDGET = 24000 characters. If exceeded:
     truncate at a row boundary, set truncation_marker to
     "\nWARNING: canon graph truncated for length." , set batch
     coherence_status='partial', journal event=coherence_truncated.
     Otherwise coherence_status='ran'. A truncated pass is NEVER
     reported as complete.

3. Endpoint POST /api/link-batches/{id}/coherence:
   - Phase 1, mechanical (code, runs even if the model call fails):
     duplicate staged pairs of same kind+type; staged relation on a pair
     that gained a canon relation since generation (re-run the F1 query);
     payload fields out of vocab/bounds (defense in depth vs 0036-b);
     staged knowledge subject not matching npc:{other}. Each mechanical
     finding is appended to coherence_findings with source='code',
     validation='valid' when auto-fixable is FALSE -- mechanical findings
     are FLAGS ONLY, patch=null, always.
   - Phase 2, model: render, call, parse via llm_parse.extract_object.
     Parse failure -> journal event=coherence_parse_error, HTTP 502,
     findings from phase 1 are still saved. A silence is never a verdict.
   - Patch validation (W): for each model finding, code validates BEFORE
     storage: target id exists (staged row of THIS batch and not
     rejected, or canon relation/knowledge row of this world); field is
     in the patchable whitelist -- staged: any payload field; canon
     relation: intensity, notes, type, direction, visible_to_b; canon
     knowledge: level, content, source, is_incorrect, is_secret,
     share_threshold -- ids and subjects are NEVER patchable; new_value
     passes the same vocab/clamp validation as 0036-b. Valid ->
     validation='valid'. Invalid -> validation='rejected' +
     validation_reason, patch stripped, finding kept as a flag. The UI
     contract: ONLY validation='valid' findings may render a button.
   - All findings (both phases) stored in link_batch.coherence_findings
     with a stable index; journal event=coherence_result with raw
     response.

4. Endpoint POST /api/link-batches/{id}/findings/{index}/apply:
   - Refuses unless the finding exists, validation='valid', not yet
     applied, batch status='open'.
   - Re-validates the target still exists and value still passes clamps
     (time-of-use check), then:
     scope=staged -> update the row payload field, row_status='edited'.
     scope=canon relation -> write_relation(mode="set",
     relation_id=..., value/type/direction/visible_to_b/notes merged
     from current row + patch) -- creator-direct authority, snapshot via
     the helper.
     scope=canon knowledge -> write_knowledge(mode="update",
     knowledge_id=..., patched field).
   - Marks the finding applied_at; journal event=patch_applied.

5. Endpoint POST /api/link-batches/{id}/commit:
   - For every row_status in (proposed, edited): kind=relation ->
     write_relation(mode="set", relation_id=None, **payload); kind=
     knowledge -> write_knowledge(mode="update", knowledge_id=None,
     **payload); kind=no_links -> nothing. Per-row F1 re-check first: a
     pair that gained a canon relation since generation is SKIPPED and
     surfaced in the response ({skipped:[...]}) -- never silently
     double-written (RECON-0036 s.9).
   - Single transaction; rows flip to committed; batch status=
     'committed', closed_at now; journal event=commit with per-row ids.
   - Refuses when coherence_status is NULL: coherence must have run
     (status 'ran' OR 'partial') before commit. Nia can still commit a
     'partial' -- the refusal is only for never-ran.

6. Extend link_agent_strata.py: FAIL if routes/link_agent.py or
   link_author.py contains any direct db.add of Relation/Knowledge
   models or raw SQL INSERT/UPDATE on relation/knowledge -- the only
   canon writes are calls into writes/ helpers (AST check).

## Scope OUT

- Frontend rendering of findings/buttons/commit (0036-d): everything
  here is curl-testable.
- Auto-apply of any finding, bulk-apply endpoint: one click = one
  finding.
- Patches creating NEW rows or deleting rows: field-level edits only.
- Mechanical findings never carry patches (flags only) in this ticket.
- Tuning CANON_SERIAL_BUDGET or chunked multi-call coherence: single
  call + explicit partial is the locked v1.
- No proposed_mutation involvement anywhere.

## Invariants to defend

- Single canon-write authority: item 6 makes it structural for this
  feature; commit and canon patches are creator-direct authority through
  writes/ helpers exclusively.
- History is sacred: canon patches go through helpers that snapshot
  change_history; staged edits need no history (ephemeral stratum).
- Fail-closed checks: invalid patches are first-class rejected findings;
  truncated coherence is 'partial'; parse silence is an error.
- Structural exclusion of connects_to/controls in every serialization
  (shared constant, never re-typed).

## Done means

- [ ] Seed a contradiction (staged hostile relation + staged intimate
      secret knowledge, same pair): coherence produces a model finding
      targeting one of them.
- [ ] Seed a canon contradiction (existing canon relation clashing with
      a staged row): a finding with scope=canon appears; applying its
      valid patch updates the canon row and its change_history gains a
      snapshot.
- [ ] Hand-inject an invalid finding path (temporary template edit
      making the model emit a bogus target id): finding stored as
      validation='rejected' with reason; apply endpoint refuses it.
- [ ] Oversized world simulation (lower the budget constant locally for
      the test, restore after): coherence_status='partial', truncation
      marker journaled.
- [ ] Commit on a never-ran-coherence batch -> 409; after coherence,
      commit writes all non-rejected rows, skips the F1-conflicted one
      and reports it; relation graph shows the new edges.
- [ ] Full verify suite green incl. extended strata check; /review-step
      and /close-step run.

## Docs to update

- ARCHITECTURE_DECISIONS.md: append to the 0036 record -- coherence
  two-phase contract, patch whitelist, time-of-use re-validation,
  partial-truncation doctrine, commit F1 re-check.
- No schema change expected (coherence_findings column shipped in
  0036-a); if the executor believes one is needed, STOP and report.
