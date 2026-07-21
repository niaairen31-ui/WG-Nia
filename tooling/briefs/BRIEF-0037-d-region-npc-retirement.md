# BRIEF — Step "Region wizard NPC retirement (A1)"

## Context

The NPC group agent is live end-to-end (BRIEF-0037-a/b/c passed their
gates). The region wizard's NPC machinery — Stage 3, the density floor
(BRIEF-39), the top-up clamp (BRIEF-40), the manifest `npcs` section — is
now a second, inferior path to the same outcome. A1 locked hard removal:
retired, not bypassed (S-norme: no dead code). The region pipeline becomes
factions + locations only; NPCs enter the world exclusively through the
group agent. RECON anchors below are from main @ 2026-07-21 — Claude Code
re-verifies line numbers against its checkout before cutting.

## Scope IN

1. **`src/world_engine/region_author.py`** — remove:
   - `MIN_NPCS_PER_FACTION` / `MIN_FACTIONLESS` (43-44)
   - `_load_manifest_topup_template` (61)
   - `_normalize_npc_placement` (161) and every npcs branch of
     `_normalize_manifest` (198-211) — the normalized manifest shape
     becomes `{concept, factions, locations}` (+ notes/skipped)
   - `_compose_npc_brief` (262)
   - `_npc_deficits` (287), `_topup_blocks` (305), `_run_npc_topup` (321)
     and its call in `generate_region_manifest` (442) — the function
     returns the normalized result directly
   - `_draft_one_npc` (504), `_draft_npcs` (576), and the
     `npcs_in`/Stage-3 block of `generate_region_draft` (624) — the draft
     tree's `npcs` list disappears from the response shape
   - now-unused imports (`generate_npc_goals` if imported here, topup
     template plumbing). Module docstring updated to the two-stage shape.

2. **`src/world_engine/cockpit/routes/regions.py`** — remove
   `_commit_region_npcs` (230-303) and its call inside the commit
   endpoint; drop `write_npc_goal` from the import at line 26 if it
   becomes unused (keep `write_faction_role` / `write_relation` — their
   readers survive). `npc_id_map` plumbing and any NPC keys in the commit
   response are removed.

3. **`scripts/seed_pilot.py`** — rewrite the `pt-region-manifest` seed:
   the npcs section of the JSON contract and ALL floor text ("at least 4
   NPCs per faction", factionless floor) are removed; the contract
   becomes concept + factions + locations. Remove the
   `pt-region-manifest-topup` seed entirely. Seeding is an upsert: state
   in the seed comment that the live DB's old template rows are
   superseded on next seed run.

4. **`src/world_engine/prompt_registry.py`** — delete the
   `region_manifest_topup` entry (197). The `region_manifest` entry's
   call-site list stays valid (re-check).

5. **`src/world_engine/cockpit/index.html`** — region wizard cleanup:
   - manifest screen: PNJ section, `regionManifestAddNpc` (6009), NPC
     option builders that fed its selects
   - review tree: NPC nodes and their accept/reject wiring; NPC entries
     in cascade preview if any
   - client state: NPC-related fields of `regionManifest` handling and
     any NPC keys in `regionDraft` rendering
   - the wizard's flow text if it mentions PNJ counts.
   The factions/locations manifest editing, review tree, judgment-link
   confirm/discard, and commit wiring are byte-for-byte untouched.

6. **`tooling/verify/checks/region_npc_retirement.py`** — NEW fail-closed
   check: `region_author.py` and `cockpit/routes/regions.py` must contain
   NONE of the tokens `MIN_NPCS_PER_FACTION`, `MIN_FACTIONLESS`,
   `_run_npc_topup`, `_npc_deficits`, `_draft_npcs`, `_draft_one_npc`,
   `_compose_npc_brief`, `_commit_region_npcs`,
   `region_manifest_topup`; and `prompt_registry.py` must not contain
   `region_manifest_topup`. A missing target file = FAILURE (vacuous-
   proof). Token scan, stdlib only, same shape as the module's siblings.

7. **`npc_goal_generation` registry entry** — verify its call-site list
   after item 1: the surviving call sites (`entity_author.py` pre-fill
   path, backfill) must keep the entry green; if the registry lists a
   region call site, remove that one line only.

## Scope OUT

- The `npc_goal_generation` prompt, `generate_npc_goals`, the backfill
  endpoint, and the single-NPC creation pre-fill: all SURVIVE untouched —
  they have live readers outside the region pipeline.
- No data deletion of any kind: existing canon NPCs committed by past
  region runs are untouched; `change_history` untouched; old
  `pt-region-manifest` template VERSIONS in the DB are superseded by the
  seed upsert, never deleted (prompt_version history is history).
- No removal of `link_author` / `npc_group_author` anything.
- No "while I'm here" refactor of `region_author.py`'s surviving stages
  or of the wizard's factions/locations UX.
- No CHANGELOG rewriting: BRIEF-39/BRIEF-40 entries in
  ARCHITECTURE_DECISIONS.md stay as written (append-only registry); the
  retirement gets its OWN entry that names them as superseded.

## Invariants to defend

- **History is sacred**: retirement is a code removal + seed supersede;
  zero DB rows deleted, zero history rewritten.
- **No structure without a reader / S-norme**: this brief IS that
  invariant enforced — the check in item 6 makes regression structural.
- **Prompt registry completeness**: every surviving entry's call sites
  must still resolve after the cuts, or the existing registry check
  fails.
- **Module budget**: pure shrinkage; nothing to defend, but function
  removals must take their now-orphaned helpers along (pyflakes/R8 will
  say so).

## Done means

- [ ] Live: region wizard run end-to-end on a fresh brief — manifest
      screen shows Factions + Lieux only; generation produces no
      character drafts; commit writes zero `character` rows and zero
      `npc_goal` rows (DB checked); factions/locations/judgment-links
      commit exactly as before.
- [ ] `grep -c "npc" src/world_engine/region_author.py` returns 0 (case-
      insensitive spot check beyond the token list).
- [ ] Seed run on a copy of the live DB: `pt-region-manifest` active
      version carries no npcs section; `pt-region-manifest-topup` has no
      ACTIVE version (historical versions still present).
- [ ] The group agent still passes its BRIEF-0037-c live scenario after
      this change (no hidden coupling).
- [ ] `python -m tooling.verify` fully green, including the new
      `region_npc_retirement` check and the pre-existing full suite.
- [ ] Deployment sequence (seed-only, no migration): backup -> seed ->
      verify.
- [ ] /review-step and /close-step run.

## Docs to update

- `world-engine-schema.md`: no schema change; update any prose NOTE that
  describes the region manifest's npcs section, if present.
- `ARCHITECTURE_DECISIONS.md` entry: "REGION NPC RETIREMENT (A1)" naming
  BRIEF-39/BRIEF-40/G1-region as superseded by TICKET-0037, with the
  new-pipeline pointer (regions -> group agent -> link agent) +
  `DECISIONS_INDEX.md` line.
- `CLAUDE.md`: remove/adjust any standing reference to the region NPC
  floor doctrine (line-budget respected; archaeology stays banned from
  the File structure section).
