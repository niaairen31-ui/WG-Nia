# BRIEF — Step "Link-agent staging schema and batch lifecycle" (BRIEF-0036-a)

Ticket: TICKET-0036. Anchored on RECON-0036 (main @ 2026-07-20, schema v1.81).

## Context

TICKET-0036 introduces a batch AI authoring flow for NPC relations and
knowledge. Everything the agent produces lands in an ephemeral staging
area first; canon is touched only at commit, through the existing
write_relation/write_knowledge helpers. This step builds the staging
substrate: two ephemeral tables, their models, the batch lifecycle
endpoints, and the last-2 retention purge. No LLM call exists yet after
this step.

## Pre-exec verification (report, then proceed or stop)

- models/ephemeral.py docstring still states the no-canon-policy-entry
  doctrine (RECON-0036 s.5).
- canon_write_policy.txt [CANON_TABLES] does not mention link_batch or
  link_batch_row (it must never).
- db.py:28 DEFAULT_DB_PATH still resolves to ~/.world_engine/.
If any anchor fails: STOP, report, no code.

## Scope IN

1. Schema doc (world-engine-schema.md): new section after the ephemeral
   tables, schema version bump to vX.YY (executor computes per V1).
   Two tables, with this NOTE verbatim under link_batch:
   "-- NOTE: link_batch / link_batch_row are EPHEMERAL stratum
   (TICKET-0036): staging for the NPC link agent. Never listed in
   canon_write_policy.txt, never a proposed_mutation, never
   creator-CRUD-reviewed as canon. Purge of closed batches (retention:
   last 2) is legal by construction -- the append-only generation
   journal under ~/.world_engine/link_agent_journal/ carries long
   memory. History-is-sacred governs canon, not this plumbing."

   ```sql
   CREATE TABLE link_batch (
     id               TEXT PRIMARY KEY,
     world_id         TEXT NOT NULL REFERENCES world(id),
     status           TEXT NOT NULL DEFAULT 'open',
                      -- open | committed | abandoned
     scope            JSON NOT NULL,
                      -- {root_location_ids, expanded_location_ids,
                      --  npc_ids, pair_count}
     pairs_total      INTEGER NOT NULL DEFAULT 0,
     pairs_done       INTEGER NOT NULL DEFAULT 0,
     coherence_status TEXT,          -- NULL | ran | partial
     coherence_findings JSON DEFAULT '[]',
     created_at       DATETIME DEFAULT CURRENT_TIMESTAMP,
     closed_at        DATETIME
   );
   CREATE TABLE link_batch_row (
     id          TEXT PRIMARY KEY,
     batch_id    TEXT NOT NULL REFERENCES link_batch(id),
     pair_a_id   TEXT NOT NULL REFERENCES entity(id),
     pair_b_id   TEXT NOT NULL REFERENCES entity(id),
     kind        TEXT NOT NULL,   -- relation | knowledge | no_links
     payload     JSON NOT NULL,   -- full proposed field set; {} for no_links
     row_status  TEXT NOT NULL DEFAULT 'proposed',
                 -- proposed | edited | rejected | committed
     created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
     updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
   );
   CREATE INDEX idx_link_batch_row_batch ON link_batch_row(batch_id);
   ```

2. Models: add LinkBatch + LinkBatchRow classes to models/ephemeral.py,
   same conventions as Gathering (RECON-0036 s.5). Migration script in
   the project's established migration location, additive only.

3. New route module src/world_engine/cockpit/routes/link_agent.py
   (routes/creator.py at 688 lines is NOT extended -- R6), registered in
   cockpit/app.py like the other routers. Endpoints, all creator-surface:
   - POST /api/link-batches/preview -- body {root_location_ids:[...]}.
     Expands each root through parent_location_id descent (BFS, code in
     src/world_engine/link_author.py: new module, function
     resolve_roster(db, root_location_ids) -> dict). Roster = characters
     with character_type='npc', vital_status='alive', entity.status=
     'active', current_location_id in expanded set. Returns
     {expanded_location_ids, npcs:[{id,name}], pair_count} where
     pair_count = N*(N-1)/2. NO batch created.
   - POST /api/link-batches -- same body; re-runs resolve_roster, creates
     the open batch with scope + pairs_total filled, pairs enumerated
     and F1-filtered AT RUN TIME in 0036-b (not stored here). Refuses
     (409) if another batch is status='open' -- one open batch at a time.
   - GET /api/link-batches -- list: the open batch if any + closed ones
     still retained.
   - GET /api/link-batches/{id} -- batch + its rows + findings.
   - POST /api/link-batches/{id}/abandon -- sets status='abandoned',
     closed_at now. Refuses on non-open.
   Commit endpoint is 0036-c/d territory: NOT built here.

4. Retention purge: in cockpit/app.py startup (where the app already
   initializes), function purge_closed_link_batches(db): keep the 2 most
   recently closed_at batches with status in (committed, abandoned);
   DELETE older ones and their link_batch_row rows. Journal files are
   never touched by the purge.

5. Journal substrate in link_author.py: journal_append(batch_id, event:
   dict) -> opens ~/.world_engine/link_agent_journal/{batch_id}.jsonl
   (dir created if absent, path built from Path.home() -- ABSOLUTE,
   never repo-relative), appends one JSON line {ts, **event}. Used from
   0036-b onward; this step only creates the helper and calls it for
   batch_created / batch_abandoned events.

6. New verify check tooling/verify/checks/link_agent_strata.py,
   fail-closed:
   - FAIL if link_batch or link_batch_row appears in
     canon_write_policy.txt or in any src/world_engine/writes/ module.
   - FAIL if any module outside routes/link_agent.py, link_author.py,
     models/ephemeral.py, app.py (purge) references the LinkBatch models.
   - FAIL (vacuous-proof) if the check parses zero criteria, e.g. the
     policy file or the models are missing.

## Scope OUT

- No LLM call, no prompt registration, no pair enumeration/F1 filter
  (0036-b).
- No coherence pass, no patches, no commit endpoint (0036-c).
- No frontend (0036-d).
- No relation-evolution on existing pairs (named deferral, ticket).
- No region-wizard integration (D2 deferral, G-ok).
- No extra retention knobs (configurable N, per-world retention): last-2
  is the locked rule.
- Do not add link_batch progress websockets/streaming; polling via GET
  is the contract.

## Invariants to defend

- Single canon-write authority: this step writes NO canon table at all;
  the strata check makes that structural.
- Module budget / 80-line ceiling on the two new modules.
- History is sacred (canon): untouched here; the schema NOTE (verbatim,
  item 1) is the documented exception boundary for the purge.

## Done means

- [ ] Schema doc shows vX.YY with both tables + verbatim NOTE; changelog
      entry added.
- [ ] Deployment sequence executed and logged: backup.py -> migration ->
      verify run green (danger_class: migration).
- [ ] POST preview with a parent location returns children-inclusive
      roster and correct pair_count (manual check vs DB).
- [ ] Creating a second batch while one is open returns 409.
- [ ] Abandon closes the batch; creating 3 closed batches then
      restarting the cockpit leaves exactly 2.
- [ ] {batch_id}.jsonl exists under ~/.world_engine/link_agent_journal/
      with batch_created line; survives the purge.
- [ ] link_agent_strata check green; full verify suite green;
      /review-step and /close-step run.

## Docs to update

- world-engine-schema.md + changelog (executor owns vX.YY).
- ARCHITECTURE_DECISIONS.md: new record "NPC LINK AGENT -- staging
  strata, retention, journal (TICKET-0036, BRIEF-0036-a)" recording
  locked codes A1/R1+journal and the ephemeral-purge rationale.
- CLAUDE.md: file-structure pointers for the two new modules if the
  claude_md_contract check requires it.
