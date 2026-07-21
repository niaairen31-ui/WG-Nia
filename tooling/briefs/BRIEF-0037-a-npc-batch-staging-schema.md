# BRIEF — Step "NPC group agent: staging substrate (schema vX.YY)"

## Context

TICKET-0037 splits NPC creation out of the region wizard into a standalone
batch agent, mirroring the TICKET-0036 link agent (locked: A1, B1, C1, G1,
H1, I1, J1 — see the ticket file). This first step lays the ephemeral
staging substrate: two sibling tables, the retention purge, the journal,
and the batch lifecycle routes. No generation, no canon write, no UI yet.

## Scope IN

1. **`src/world_engine/models/ephemeral.py`** — add `NpcBatch`
   (`__tablename__ = "npc_batch"`) and `NpcBatchRow`
   (`__tablename__ = "npc_batch_row"`) directly after `LinkBatchRow`,
   preceded by this NOTE (verbatim):

   ```
   # NOTE: npc_batch / npc_batch_row are EPHEMERAL stratum (TICKET-0037):
   # staging for the NPC group agent. Never listed in canon_write_policy.txt,
   # never a proposed_mutation, never creator-CRUD-reviewed as canon. Purge of
   # closed batches (retention: last 2) is legal by construction -- the
   # append-only generation journal under ~/.world_engine/npc_agent_journal/
   # carries long memory. History-is-sacred governs canon, not this plumbing.
   ```

   `NpcBatch` columns (mirror `LinkBatch`'s idioms — `_uuid` default,
   `server_default` text, `_created_ts()`):
   - `id` PK, `world_id` FK world.id NOT NULL
   - `status` str default `"open"` — `open | committed | abandoned`
   - `scope` JSON NOT NULL — `{root_location_id, expanded_location_ids,
     lines, group_brief}` where `lines` is
     `[{count, description, faction_id, location_id}]` (nullable ids)
   - `npcs_total` int default 0, `npcs_done` int default 0
   - `created_at`, `closed_at` (nullable)
   - NO coherence columns (I1 — no model coherence pass for this agent).

   `NpcBatchRow` columns:
   - `id` PK, `batch_id` FK npc_batch.id NOT NULL,
     `Index("idx_npc_batch_row_batch", "batch_id")`
   - `line_index` int NOT NULL (which spec line produced this NPC)
   - `kind` str — `draft | failed`
   - `payload` JSON NOT NULL — full draft (public/secret), resolved
     `location_id`, `goals` block, `notes` list; `{}` + reason for `failed`
   - `row_status` str default `"proposed"` —
     `proposed | edited | rejected | committed`
   - `created_at`, `updated_at`

2. **Migration** — schema bump to vX.YY following the v1.82 (BRIEF-0036-a)
   migration precedent exactly: create both tables + index, no data
   movement. Claude Code owns the version number and the changelog entry.

3. **`src/world_engine/link_author.py`** — extract the BFS descent from
   `resolve_roster` (currently link_author.py:82-90) into a module-level
   `expand_location_ids(db: Session, root_ids: list[str]) -> set[str]`;
   `resolve_roster` calls it (behavior byte-identical). This is the C2
   refactor-over-duplication move: the NPC agent needs the same descent.

4. **`src/world_engine/npc_group_author.py`** — NEW module, this step
   containing only:
   - `JOURNAL_DIR = Path.home() / ".world_engine" / "npc_agent_journal"`
     and `journal_append(batch_id, event)` — same shape and docstring
     posture as `link_author.journal_append` (link_author.py:110-114):
     append-only JSONL per batch, never purged.
   - `resolve_vocabulary(db, root_location_id) -> dict` — expands the root
     via `link_author.expand_location_ids`, returns
     `{expanded_location_ids (sorted), locations: [{id, name}] (the
     expanded set), factions: [{id, name}] (active faction entities of the
     world)}`. Read-only, writes nothing.

5. **`src/world_engine/cockpit/routes/npc_agent.py`** — NEW router,
   registered in `cockpit/app.py` beside `_routes_link_agent`:
   - `NpcBatchBody(BaseModel)`: `root_location_id: str`,
     `group_brief: str`, `lines: list[dict]`.
   - `GET /api/npc-batches/preview?root_location_id=...` — read-only:
     `resolve_vocabulary` output, no batch created (S1-preview posture,
     mirror of link_agent.py:52-59).
   - `POST /api/npc-batches` — validation, then create:
     - 409 if an OPEN `npc_batch` exists for this world (per-agent rule:
       an open `link_batch` does NOT block this — each table enforces its
       own singleton).
     - Each line: `count` int >= 1 (422 otherwise); `description`
       non-empty str; `faction_id`, if present, must be an active faction
       entity of the world (422); `location_id`, if present, must be in
       the expanded set (422). `sum(count)` > 30 -> 422
       ("batch trop grand — 30 PNJ max").
     - Create `NpcBatch` with `scope` as specified above,
       `npcs_total = sum(count)`, journal `batch_created` with the scope.
   - `GET /api/npc-batches` — the open batch (if any) + retained closed
     batches, `created_at desc` (mirror list_link_batches).
   - `GET /api/npc-batches/{id}` — batch + its rows serialized.
   - `POST /api/npc-batches/{id}/abandon` — open only (409 otherwise),
     status -> `abandoned`, `closed_at` set, journal `batch_abandoned`.

6. **`src/world_engine/cockpit/app.py`** — refactor
   `purge_closed_link_batches` into a parametrized private helper
   `_purge_closed_batches(db, batch_model, row_model, row_fk_attr)`
   keeping the last-2/`closed_at desc`/`offset(2)` logic, with two thin
   named wrappers `purge_closed_link_batches` (docstring unchanged) and
   `purge_closed_npc_batches` (sibling docstring citing TICKET-0037).
   Startup hook calls both.

7. **`tooling/verify/checks/npc_agent_strata.py`** — NEW fail-closed
   check, sibling of `link_agent_strata.py`, guarantees 1-2 only for now:
   - `npc_batch`/`npc_batch_row` appear in NEITHER
     `canon_write_policy.txt` NOR any `src/world_engine/writes/` module.
   - `NpcBatch`/`NpcBatchRow` referenced only from:
     `cockpit/routes/npc_agent.py`, `npc_group_author.py`,
     `models/ephemeral.py`, `models/__init__.py`, `cockpit/app.py`.
   - Vacuous-proof: missing policy file or model definitions = FAILURE.
   (Guarantees 3-4 analogues arrive with BRIEF-0037-c's commit path.)

## Scope OUT

- Any generation call, any prompt template, `pt-npc-batch-placement`
  (BRIEF-0037-b).
- Any canon write, commit path, `patch_row` sibling (BRIEF-0037-b/-c).
- Any frontend surface (BRIEF-0037-c).
- Any change to the region pipeline (BRIEF-0037-d) — `region_author.py`
  and `routes/regions.py` are untouched this step.
- Multi-root batches / cross-region groups (deferral D-0037-1).
- Any generalization of `link_batch` itself (G1 locked: sibling tables,
  not a polymorphic table).
- Do not "improve" `resolve_roster` beyond the mechanical extraction of
  item 3 — its query, return shape, and docstring stay as they are.

## Invariants to defend

- **Single canon-write authority**: these tables are ephemeral stratum;
  nothing in this step writes canon. The NOTE + `npc_agent_strata.py`
  make that structural.
- **History is sacred**: the last-2 purge is legal ONLY because the
  journal carries long memory — the journal dir and `journal_append`
  ship in the same brief as the purge, never later.
- **No structure without a reader**: every column above has a named
  consumer in briefs b/c (payload -> generation/commit, line_index ->
  review grouping, npcs_done -> run driver). No speculative columns.
- **Module budget (R5)** — `cockpit/app.py` is near other duties; the
  purge refactor must not grow it beyond budget.

## Done means

- [ ] Migration applied on a copy of the live DB: `npc_batch` /
      `npc_batch_row` exist, schema version reads vX.YY.
- [ ] `POST /api/npc-batches` with 2 valid lines creates a batch with
      `npcs_total` = sum of counts; journal file
      `~/.world_engine/npc_agent_journal/<batch_id>.jsonl` exists with a
      `batch_created` event.
- [ ] Second `POST` while the first is open -> 409; abandoning the first
      then posting again -> 201-path succeeds.
- [ ] A line with `count: 0`, an unknown `faction_id`, a `location_id`
      outside the expanded set, and a batch of `sum(count) = 31` each
      -> 422 with the specified messages.
- [ ] An open `link_batch` and an open `npc_batch` coexist without
      either 409ing the other.
- [ ] Close 3 npc batches (abandon), restart the app: only the last 2
      remain; `link_batch` retention unaffected; journals intact.
- [ ] `python -m tooling.verify` fully green, including the new
      `npc_agent_strata` check and the untouched `link_agent_strata`.
- [ ] Deployment sequence executed (danger_class migration):
      backup -> migration -> verify.
- [ ] /review-step and /close-step run.

## Docs to update

- `world-engine-schema.md` (both tables + NOTE) + changelog entry vX.YY.
- `ARCHITECTURE_DECISIONS.md` entry (G1 sibling-tables decision, per-agent
  open-batch rule, purge parametrization) + `DECISIONS_INDEX.md` line.
- `CLAUDE.md` only if its file-structure section names route modules
  (pointer freshness for `routes/npc_agent.py`).
