# BRIEF — Step "NPC goal generator, three gates" (BRIEF-0013-b)

## Context

BRIEF-0013-a is closed: `npc_goal` (schema v1.69), the `writes.py` helpers
(`write_npc_goal`, `write_npc_goal_status`), the creator CRUD
(`GET/POST /api/entities/{id}/goals`, `POST /api/goals/{id}/status`), the
`TES OBJECTIFS` injection, and the `npc_goal_read.py` verify check all
exist. This step makes goals model-authored so Nia never hand-manages them:
ONE generator function + ONE prompt template (T1), called from three gates —
region generation (G1), single-NPC creation pre-fill (L1), and an
existing-world backfill (G2, per-horizon deficits, P2).

**Anchor note**: at drafting time the GitHub remote had not yet received the
0013-a push; every `file:line` below is in a file 0013-a did NOT modify and
was re-verified against `main`. Symbols created by 0013-a are referenced by
their contract names from that brief; the executor resolves their exact
positions in the real tree.

The behaviour loop (initiative signal, `goal_change`, dialogue directive)
remains BRIEF-0013-c.

## Scope IN

1. **Prompt template `pt-npc-goals`** — seed in `scripts/seed_pilot.py`,
   `upsert_prompt_template` idiom (seed_pilot.py:1149-1159), placed near
   the other authoring templates. `world_id=None`,
   `usage="npc_goal_generation"`, `destination="local"`,
   `name="NPC goals — génération 1 long + 2 courts (JSON)"`,
   `variables=["npc_name", "npc_description", "npc_backstory",
   "faction_goals"]`. S2 discipline applies automatically (seed writes v1
   on virgin heads only). System prompt, verbatim:

   ```
   Tu es un assistant d'écriture pour un jeu de rôle. On te donne
   l'identité d'un personnage non-joueur (PNJ). Tu produis ses objectifs
   personnels : exactement 1 objectif à long terme et 2 objectifs à court
   terme.

   Règles :
   - L'objectif long terme est une ambition ou un désir profond, cohérent
     avec l'identité et le passé du personnage.
   - Les objectifs court terme sont des intentions concrètes, actionnables
     dans les jours qui viennent, au service de l'objectif long terme ou
     d'une préoccupation immédiate.
   - Chaque objectif tient en UNE seule phrase, commençant par un verbe à
     l'infinitif.
   - N'invente aucun nom propre absent des informations fournies.
   - Si des objectifs de faction sont fournis, le personnage peut y
     adhérer, s'en écarter ou les subvertir — selon son caractère.

   Tu réponds UNIQUEMENT avec un objet JSON, sans texte autour :
   {"long": "…", "shorts": ["…", "…"]}
   ```

   User template, verbatim:

   ```
   PNJ : {npc_name}
   Description : {npc_description}
   Passé : {npc_backstory}
   Objectifs de sa faction : {faction_goals}
   ```

2. **Generator** — `generate_npc_goals(name, description, backstory,
   faction_goals, db) -> dict` in `src/world_engine/entity_author.py`,
   next to the other draft generators. Loader
   `_load_npc_goals_template(db)` follows the loader idiom
   (entity_author.py:96-131). Body follows `generate_entity_draft`
   (entity_author.py:380-425): `current_prompt(db, template)`, chained
   `.replace()` substitution (0011 H1 norm — never `str.format()`),
   `chat(..., model=effective_model(template, AUTHOR_MODEL),
   format="json")`. `faction_goals=None` substitutes the literal
   `(aucune faction)`. Pure generate-and-return: writes no canon anywhere
   in its call path; never raises into the caller.

   Output contract: `{"ok": True, "long": str, "shorts": [str, ...],
   "notes": [...]}` or `{"ok": False, "error": str}`. Validation:
   `long` non-empty trimmed string else `""` + note; `shorts` = trimmed
   non-empty strings, truncated to 2; fewer than 2 → partial accept +
   note; long empty AND shorts empty → `ok: False`.

3. **G1 — region draft phase** — `generate_region_draft` Stage 3 loop
   (`src/world_engine/region_author.py:494-542`): after the character
   draft succeeds, call `generate_npc_goals` with the draft's `public`
   fields (`name`, `description`, `backstory`) and the faction goals taken
   from the already-generated faction draft
   (`factions_out` entry for `fac_local` →
   `result["draft"]["secret"]["goals"]`, None when unaffiliated or the
   faction draft failed). Attach the result to the NPC entry as
   `result["draft"]["public"]["goals"] = {"long": …, "shorts": […]}`.
   On generator failure: append a note, the NPC ships WITHOUT goals —
   never skip an NPC over a goal failure.

4. **G1 — region review UI** — the region review NPC card displays the
   attached goals read-only (long + shorts, horizon-tagged), so the
   creator sees them before commit. Accept/reject stays per-NPC exactly
   as today; no per-goal controls (see Scope OUT).

5. **G1 — region commit** — `commit_region` Stage 3
   (`src/world_engine/cockpit/app.py:490-536`): after
   `_crud._create_entity_core` succeeds for an NPC, read
   `draft["public"].get("goals")`; when present and well-formed, write
   the long (if non-empty, `horizon="long"`) and each short via
   `write_npc_goal(..., changed_by="creator")`, in the SAME transaction
   as the NPC (single `db.commit()` at the end, unchanged). Malformed or
   absent block → write nothing for that NPC, continue. `world_id` comes
   from the same source Stage 4 already uses (app.py:537).

6. **L1 — single-NPC creation pre-fill** — `/api/entities/generate`
   (`app.py:108-121`): when `entity_type == "character"` and the draft
   returns ok, call `generate_npc_goals` with the draft fields; resolve
   `faction_goals` by fetching `Faction.goals` for the draft's resolved
   `faction_id` (read-only query; None when unaffiliated). Merge as
   `draft["public"]["goals"]`; generator failure adds a note, the draft
   stays ok. The creation form renders the block as EDITABLE pre-fill
   (one long textarea + two short textareas, each clearable). On submit,
   the form first POSTs the entity (existing endpoint, untouched), then
   POSTs each non-empty goal to `POST /api/entities/{id}/goals`
   (0013-a endpoint) — no change to `EntityWriteBody` or
   `_create_entity_core`, which `commit_region` shares.

7. **G2/P2 — backfill** — `POST /api/npc-goals/backfill` in
   `src/world_engine/cockpit/crud.py` (sanctioned creator-write
   neighbourhood), body `{entity_id?: str}`:

   - Scope: the given NPC, or every character of the active world with
     `character_type == "npc"` and `vital_status == "alive"`.
   - Per NPC, compute the per-horizon deficit (P2): needs a long iff
     zero ACTIVE long goals; needs `2 − n` shorts iff `n < 2` ACTIVE
     shorts. Zero deficit → skip, no model call.
   - For each deficient NPC: one `generate_npc_goals` call
     (faction goals via the NPC's first public faction membership →
     `Faction.goals`, read-only query; None otherwise); write ONLY the
     missing horizons via `write_npc_goal(...,
     changed_by="creator-backfill")` — surplus generator output for an
     already-satisfied horizon is discarded.
   - Response: `{"ok": true, "processed": n, "skipped_complete": n,
     "written": {"long": n, "short": n}, "failures":
     [{"npc": name, "reason": …}]}`. A failure never aborts the batch.
   - Idempotent by construction: a second run on an unchanged world
     writes zero rows.

8. **Backfill UI** — character sheet: a « Générer les buts » button on
   the « Objectifs » block (0013-a), calling the backfill endpoint scoped
   to that NPC, HTMX-refreshing the block. Entities list page: a
   « Générer les buts manquants » button calling it unscoped and showing
   the summary. Exact placement executor's choice within
   `page_contract.py` compliance.

9. **Verify** — extend `tooling/verify/checks/npc_goal_read.py`'s module
   allowlist with `src/world_engine/cockpit/app.py` (the commit-side
   `write_npc_goal` calls). `entity_author.py` and `region_author.py`
   handle plain dicts and must NOT need allowlisting — if the executor
   finds themselves importing `NpcGoal` there, the design is being
   violated. All existing checks (`prompt_lean`, `prompt_version`,
   `single_canon_write`, `page_contract`) must pass unmodified except
   where this brief says otherwise.

10. **Docs** — see "Docs to update".

## Scope OUT

- **The behaviour loop** — initiative-vote signal (R1), `goal_change`
  emit/apply (H1/O1), the D1 dialogue directive: all BRIEF-0013-c.
- **The region MANIFEST contract** (Stage 0 / top-up, T1): untouched —
  goals are generated per-NPC at the DRAFT phase, never in the manifest.
- **Per-goal accept/edit in the region review UI** — display-only there;
  the creator edits goals post-commit on the character sheet (0013-a
  CRUD). Region acceptance stays per-NPC.
- **Any "regenerate" / overwrite mode** — backfill fills deficits only
  (P2); it never rewrites an NPC whose horizons are satisfied. Replacing
  a goal = close it on the sheet, then backfill or hand-write.
- **Player-character goals** — still out; backfill and pre-fill apply to
  `character_type == "npc"` only.
- **F2 hierarchy, N3 is_secret, TICKET-0014 machinery** — unchanged
  deferrals.
- **`assemble_mj_context`, `assemble_npc_context`** — untouched this
  step (the injection shipped in a).
- **Waking `Faction.goals` for prompt INJECTION** — this brief reads it
  as generator INPUT only; injecting faction posture into NPC prompts
  remains the separate queued "faction posture" chantier.

## Invariants to defend

- **Model proposes, code judges** — the generator only ever produces
  drafts/pre-fills; every canon write goes through creator-direct paths
  (region commit, sheet CRUD, creator-triggered backfill) via the
  `writes.py` helpers. No new approval pipeline, no silent writes.
- **Two sanctioned canon-write paths** — backfill and commit both call
  `write_npc_goal`; `single_canon_write.py` stays green without new
  helper entries.
- **S2 seed discipline** — `pt-npc-goals` seeds v1 on a virgin head only;
  re-seeding never touches existing text.
- **H1 substitution norm** — chained `.replace()`, never `str.format()`.
- **Never raise into callers** — generator and backfill degrade per-item
  with notes/failure entries; a region or batch never dies on one NPC.
- **Language convention** — prompt text and generated goals in French;
  code, identifiers, docs in English.

## Done means

- [ ] Seed run on a virgin DB creates `pt-npc-goals` with a v1
  `prompt_version`; re-running the seed changes nothing.
- [ ] `POST /api/entities/generate` for a character returns a draft whose
  `public.goals` holds 1 long + 2 shorts; the creation form shows them
  editable; submitting writes the entity then the non-empty goals, visible
  on the sheet.
- [ ] A region generated end-to-end shows goals on each NPC review card;
  committing it writes the goal rows in the same transaction (an NPC and
  its goals are never observable separately).
- [ ] On a live world with mixed states (NPC with no goals; NPC with only
  a long; NPC complete), unscoped backfill writes exactly the deficits and
  reports them; an immediate second run reports zero written.
- [ ] The sheet button fills one NPC's deficits and refreshes the block.
- [ ] `tooling/verify/run.py` fully green, including the extended
  `npc_goal_read.py`.
- [ ] `/review-step` and `/close-step` run (engine code touched).

## Docs to update

- `ARCHITECTURE_DECISIONS.md` — append to the "NPC GOALS" section
  (0013-a): T1 single generator / three gates (draft-phase generation so
  the creator reviews before commit); M2 generation cardinality vs S1
  read-side bound; P2 per-horizon idempotent backfill, no-overwrite rule;
  and an explicit note that `faction.goals` (dormant since v1.44) gains
  its FIRST reader as generator input only — prompt injection of faction
  posture remains deferred to its own chantier.
- `world-engine-schema.md` / changelog — untouched (no schema change this
  step; v1.69 already covers the table).
- `CLAUDE.md` — untouched.
