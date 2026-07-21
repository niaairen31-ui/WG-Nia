# BRIEF — Step "NPC group agent: commit, cockpit surface, link handoff"

## Context

Batches now generate and stage (BRIEF-0037-b). This step closes the loop:
the atomic commit of accepted rows into canon (entities + memberships +
goals + the generator's own knowledge, one transaction), the "Agent PNJ"
cockpit panel mirroring the link agent's, and the J1 handoff that prefills
a link batch on the same region root. After this step the new pipeline
regions -> NPCs -> liens is live end-to-end; the region wizard still has
its legacy NPC path until BRIEF-0037-d retires it.

## Scope IN

1. **`src/world_engine/cockpit/routes/npc_agent.py`** —
   `POST /api/npc-batches/{id}/commit` -> `_commit_npc_batch(batch, db)`,
   a route-module function mirroring `_commit_region_npcs`
   (routes/regions.py:230-303) — NOT placed in `npc_group_author.py`,
   same layering as the region commit (canon writes live route-side,
   the author module stays generate-only):
   - Guards: batch `open` (409); `npcs_done == npcs_total` (409,
     "generation incomplete — run or abandon") — the count contract holds
     at commit; abandon is the escape hatch for a batch Nia gives up on.
     No coherence gate exists (I1).
   - Rows `row_status in ("proposed", "edited")` commit; `rejected` and
     `kind == "failed"` rows write nothing.
   - Per row, exactly the `_commit_region_npcs` recipe:
     `_crud.EntityWriteBody(entity={type: "character", name,
     description}, extension={character_type: "npc", appearance,
     backstory, aversion, physical_tier (when set), current_location_id:
     payload["location_id"], faction_id (when set — membership row via
     `_create_entity_core`'s existing `write_membership` path,
     role=None), secrets: json creator_meta when present})` ->
     `_crud._create_entity_core`.
   - `secret.knowledge` rows -> `_crud._create_knowledge_core` with
     `is_secret=True, share_threshold=50, is_incorrect=False,
     source=None` (byte-same posture as regions.py:271-282).
   - `payload["goals"]` -> `write_npc_goal` long + shorts, `changed_by=
     "creator"`, same transaction as the entity (G1: an NPC and its goals
     are never separately observable).
   - Rows flip to `committed`, batch -> `committed` + `closed_at`, ONE
     `db.commit()` at the end. Journal `commit` event with committed row
     ids and per-row entity ids. Response `{committed: [{row_id,
     entity_id, name}], skipped: [...]}`.

2. **`tooling/verify/checks/npc_agent_strata.py`** — extend with the
   guarantee-4 analogue: `routes/npc_agent.py` and `npc_group_author.py`
   contain no direct `db.add(Entity(...)/Character(...)/
   FactionMembership(...)/Knowledge(...)/NpcGoal(...))` and no raw SQL
   INSERT/UPDATE on those tables — commit is structurally forced through
   `_create_entity_core` / `_create_knowledge_core` / `write_npc_goal`.
   Fail-closed as before.

3. **`src/world_engine/cockpit/index.html`** — "Agent PNJ" surface,
   structural mirror of the linkagent one (launcher button at
   index.html:1286, panel at 1296, `linkAgent*` JS from 9832):
   - Header button `npcagent-launcher-btn` "Agent PNJ" + badge dot when a
     batch is open; collapsible `npcagent-panel`. Reuse the existing
     `.linkagent-*` CSS classes wholesale (rename to shared classes ONLY
     if a rename is a pure find-replace; otherwise reuse as-is — no new
     stylesheet block).
   - **Launcher**: location tree with single-select radio on any node
     (single root, intra-region v1), then a preview fetch
     (`GET /api/npc-batches/preview`) loading the vocabulary; a
     `group_brief` textarea; a line editor — rows of
     `[count number input] [description text input] [faction select:
     (aucune) + world factions] [location select: (modèle) + expanded
     locations]` with add/remove buttons; a running total "N PNJ" and a
     launch button posting `POST /api/npc-batches` (422 messages surfaced
     verbatim).
   - **Run**: progress `npcs_done / npcs_total`, a "Suivant" button and a
     "Tout générer" driver looping `run-next` until 409/error — same
     driver cadence as the link agent's pair loop; a 502 stops the loop
     with the error surfaced and a resume-able "Suivant".
   - **Review**: rows grouped by `line_index` (line description as group
     header). Each row: name + description excerpt, inline-editable
     fields wired to the PATCH route (name, description, physical_tier,
     faction select, location select, goals long/shorts), reject/
     un-reject toggle (rejected rows dimmed + struck, `.rejected`
     precedent), collision/fallback/goals notes rendered as plain notes.
   - **Commit**: button enabled only when `npcs_done == npcs_total`;
     result block listing committed names; abandon button with confirm.
   - **J1 handoff**: on a successful commit response, render verbatim
     button "Générer les liens pour ce groupe" which calls the EXISTING
     link agent creation (`POST /api/link-batches`) with
     `{root_location_ids: [<this batch's root_location_id>]}`, then opens
     the link agent panel on the fresh batch. A 409 (a link batch is
     already open) is surfaced as a plain warning banner, never retried.
   - Client state reset on world switch follows the existing pattern
     (the `regionManifest`/linkAgent resets around index.html:4058).

4. **`tooling/verify/checks/page_contract.py` / tab registry** — only if
   the header-button pattern is governed there (check first): register the
   new button the same way the linkagent button is. If nothing governs
   it, change nothing.

## Scope OUT

- `canon_write_policy.txt` is NOT edited — every canon write above rides
  already-allowed sites (`_create_entity_core`, `_create_knowledge_core`,
  `write_npc_goal`); adding entries would be duplication, not compliance.
- No region pipeline change (BRIEF-0037-d).
- No link agent behavior change — the handoff calls its existing routes
  untouched; do not add a "chained auto-run" of pairs.
- No new coherence pass, no commit-time name re-dedup against canon (the
  staging-time note from BRIEF-0037-b is the guard; names carry no
  uniqueness constraint in canon).
- No partial commit ("commit what's generated so far") — the
  `npcs_done == npcs_total` guard is deliberate.
- No portrait, no relation, no inter-NPC knowledge writes (link agent
  territory, downstream).

## Invariants to defend

- **Single canon-write authority / closed-list policy**: the entire
  commit rides three sanctioned helpers; the strata check extension makes
  any bypass a verify failure.
- **Atomicity (G1 posture)**: one transaction for entities + memberships
  + knowledge + goals. A mid-commit exception leaves zero rows written.
- **Server-authoritative, client-advisory**: the commit re-reads rows
  from the DB by `row_status`; the client's rendering is never trusted
  (chantier 2 discipline). PATCH gates re-validate ids server-side.
- **json_ui_boundary**: any new JSON-in-HTML crossing follows the named
  allow-list check — verify will say so.

## Done means

- [ ] Live gate scenario (ticket): batch "5 gardes pinned / 2 marchands /
      1 unanchored" on a region root -> 8 staged; reject 1, edit 1,
      commit -> exactly 7 NPCs in canon with correct
      `current_location_id`, memberships where resolved, goals rows
      present; the rejected row wrote nothing (DB checked).
- [ ] Commit attempted at 6/8 generated -> 409 with the specified
      message; after the remaining runs, commit succeeds.
- [ ] SQLite inspected after a forced mid-commit failure (e.g. corrupt a
      row payload by hand in staging): zero canon rows from that batch.
- [ ] "Générer les liens pour ce groupe" opens a link batch whose roster
      includes BOTH the new NPCs and pre-existing residents of the root;
      F1 skips already-canon pairs (journal shows
      `pair_skipped_existing` when applicable).
- [ ] With a link batch already open, the handoff surfaces the 409
      banner and creates nothing.
- [ ] Badge dot appears with an open npc batch, survives a reload,
      clears after commit/abandon.
- [ ] `python -m tooling.verify` fully green, including the extended
      `npc_agent_strata` guarantee 4.
- [ ] /review-step and /close-step run.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` entry (commit layering route-side, no
  policy-file edit rationale, no-partial-commit guard, J1 handoff) +
  `DECISIONS_INDEX.md`.
- `CLAUDE.md` pointer freshness if its file-structure section enumerates
  cockpit surfaces.
- No schema change.
