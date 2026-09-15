# BRIEF 0087-D — "The creator closes the residue"

Lot: LOT-0087-knowledge-subject-participants.md (authoritative on conflict)
Depends on: BRIEF-0087-a (C-01, C-02), BRIEF-0087-c (C-06)
Regenerated after AMENDMENT-0087-1 (code `J2`): the `role="subject"` discriminator
is dropped; `fact_participant` is uniquely keyed on `(fact_id, entity_id)`.
Regenerated again after AMENDMENT-0087-2 (code `K3`): Scope IN item 5, the
residue worklist, is deferred to TICKET-0088.

## Anchors to confirm (Mini-RECON)

Halt if any has moved.

- `src/world_engine/cockpit/crud/knowledge.py:218-235` -> `POST /facts/{fact_id}/participants` exists and calls `attach_participants(db, fact=fact, entity_ids=[body.entity_id], role=body.role)`; `FactParticipantBody` carries an optional `role`.
- `src/world_engine/models/canon_knowledge.py:119-122` -> `idx_fact_participant_unique` on `(fact_id, entity_id)`, unique.
- `src/world_engine/cockpit/crud/knowledge.py:236-250` -> `DELETE /facts/{fact_id}/participants/{entity_id}` exists.
- `src/world_engine/cockpit/crud/knowledge.py:137-141` -> `GET /entities/{entity_id}/knowledge` exists.
- `src/world_engine/cockpit/crud/knowledge.py:143-171` -> `_create_knowledge_core` calls `write_knowledge` and documents the auto-created free-standing fact.
- `frontend/src/creation/KnowledgeEditor.svelte:10` -> `let { knowledge, entityId, levelOptions, legacyDoc, onSaved } = $props();`
- `frontend/src/creation/KnowledgeEditor.svelte:38-49` -> `saveRow` PUTs `/api/knowledge/{id}` with subject, level, source, share_threshold, is_incorrect, is_secret, content — and no fact or participant field.
- `frontend/src/creation/KnowledgeEditor.svelte:8` -> `import { sheetRequest, api } from './sheetRequest.svelte.js';` is the shared request/refresh/status cycle.
- `frontend/src/creation/KnowledgeEditor.svelte:34-36` -> `reloadEntity` re-fetches `/api/entities/{entityId}` and calls `onSaved`.
- `frontend/src/lore/Lore.svelte` exists and is the TICKET-0085 consultation surface.

## Facts carried

**R-08** — `POST /facts/{fact_id}/participants` and `DELETE
/facts/{fact_id}/participants/{entity_id}` are already implemented
(TICKET-0082, BRIEF-0082-b), the first calling `attach_participants`.
`_create_knowledge_core` (`crud/knowledge.py:143-171`) documents the
auto-creation fallback and passes no participants. This brief builds a
surface and a residue query, not a backend.

**R-10** — 12 of 615 knowledge rows carry a `session_id`; 15 of 310 distinct
subjects contain an underscore; 295 rows carry a NULL `source`. The creator
CRUD, not the analyzer, is the dominant producer of existing rows — which is
why this brief, not BRIEF-0087-b, is where coverage actually comes from.

**R-06 / R-07** — after the backfill, 243 distinct subjects and 517 knowledge
rows remain unresolved; 42 of 297 active entities are answerable. Verkhaal
keeps 28 unresolved subjects.

**TICKET-0085 lock** — the lore consultation surface's first perimeter is
**read-only**; the write path is a named successor. That lock is why the
binding surface in this brief lives in the Creation shell and not in
`frontend/src/lore/`.

## Contracts

Consumes **C-01**, **C-02** (verbatim copies in BRIEF-0087-a) and **C-06**
(verbatim copy in BRIEF-0087-c). Produces no new `C-NN`: both backend routes
it needs already exist (R-08), and the residue query is `C-06`.

## Context

Decision E2: close the coverage gap before shipping the selector. The
backfill closes the part the rungs can reach — 22% of subjects. The rest are
propositions no lookup will ever resolve ("Les véritables objectifs de La
Société des Entrepreneurs"), and only the creator knows what they are about.
This is the surface where she says so.

R-10 is why this brief matters more than its position suggests: almost every
existing knowledge row came from creator authoring, not from the analyzer.

## Scope IN

1. **`src/world_engine/cockpit/crud/knowledge.py`** — the dict returned for a knowledge row (used by `GET /entities/{entity_id}/knowledge` and by the entity payload the sheet reloads) gains two keys:
   - `fact_id` — the row's existing `knowledge.fact_id`.
   - `subject_participants` — a list of `{entity_id, name, role}` for **every** one of that fact's `fact_participant` rows, with no role filter (J2), world-scoped at query construction through the join to `entity`. Empty list when there are none. `role` is carried for display only; the surface never filters on it.
   No other key changes and no key is removed.

2. **`GET /api/worlds/{world_id}/unresolved-subjects`** — new read-only route in the same module, returning `C-06`'s rows serialized as JSON. Each entry carries `subject`, `fact_ids`, `row_count`, and the resolution flattened to `{verdict, entity_id, candidate_ids, category}`. Read-only: no write, no side effect, no model call.

3. **`frontend/src/creation/KnowledgeEditor.svelte`** — each existing row card gains one field row, `Subject entity`:
   - when `subject_participants` is non-empty, show each bound name with an `Unbind` action calling `DELETE /api/facts/{fact_id}/participants/{entity_id}` through `sheetRequest` with `reloadEntity` as the refresh;
   - when empty, show a picker over the active world's active entities plus a `Bind` action calling `POST /api/facts/{fact_id}/participants` with `{entity_id}` and **no `role`**, through the same `sheetRequest` cycle;
   - the picker pre-selects `resolve_subject`'s suggestion when the backend supplied one, and never binds it without the creator pressing `Bind`. A suggestion is a suggestion; the surface never binds on its own.
   - The POST body carries no `role`. The surface never offers a role choice and never writes one — a participant is the aboutness claim on its own (J2).
   - Binding an entity already present on that fact under a role written elsewhere is refused by `idx_fact_participant_unique`. Check before posting and show the existing binding instead of a picker, rather than letting the POST return a 500.

4. Do **not** put the subject binding into `saveRow`'s PUT body. Binding is a participant write on the fact; editing a knowledge row is a `write_knowledge` update. Two different writes, two different endpoints, and `C-01` explicitly ignores `subject_entity_ids` on an update.

5. **The residue worklist is not built in this brief.** Deferred to TICKET-0088, which lands the greenfield-island path in `creation_island.py` and then the panel itself, and which runs before BRIEF-0087-e. Do not add a `CREATION_ISLANDS` entry, do not add a container to `Creation.svelte`, do not touch `registry.js`, `tabs.js`, `mount.js` or `Creation.svelte`. Gap closure in this brief is item 3 alone: one knowledge row at a time, from the entity sheet.

6. **Item 2 stays regardless.** `GET /api/worlds/{world_id}/unresolved-subjects` keeps two concrete readers — BRIEF-0087-c's backfill report, and TICKET-0088's panel, queued with a brief and ordered before BRIEF-0087-e. It is not structure without a reader.

7. The frontend build output is committed. Run the build and commit its artefacts, or `frontend_build_fresh.py` fails.

## Scope OUT

- **`frontend/src/lore/`.** Untouched by this brief. The consultation surface stays read-only until TICKET-0085's named successor.
- **The selector.** `lore_selectors.py`, `lore_plan.py`, `lore_render.py` and their checks are BRIEF-0087-e.
- **The dedup guard**, in all three forms. Untouched.
- **`knowledge.subject`.** The text field stays editable exactly as it is today; binding a subject entity never rewrites it, and unbinding never clears it.
- **Bulk auto-bind.** No "bind everything the resolver suggests" button. The resolver's suggestions were already applied by BRIEF-0087-c for the unambiguous ones; what is left is exactly what needs a human.
- **A role vocabulary.** This surface writes no `role` at all. An existing role written elsewhere is displayed and never edited, never overwritten, never cleared.
- **Editing `fact.content`.**
- **`fact_default` / scoped knowledge defaults.** TICKET-0082's G2a resolution is a different feature on the same table.
- **The write path for creator-asserted knowledge** — "tel personnage connaît telle chose" as a new canon row. That is TICKET-0085 queue item 5, not this.
- **Any new mutation type or queue behaviour.**
- **The residue worklist, and every registry it would touch** — `CREATION_ISLANDS` (`frontend/src/creation/registry.js`), `CREATION_TABS` (`tabs.js`), `mount.js`, `Creation.svelte`'s containers, and `creation_island.py` itself. Named deferral to TICKET-0088 (AMENDMENT-0087-2). Reactivation is TICKET-0088 landing, not a judgment call.

## Invariants to defend

- **Two canon-write paths for rows** (`CLAUDE.md:157-158`). This surface writes through the creator CRUD, which is one of the two. It adds no third.
- **Single canon-write paths.** Participant rows are written only by `attach_participants`, reached through the route that already calls it (R-08). The frontend never constructs a participant.
- **The MJ context assembler's perception boundary** (`CLAUDE.md:168-171`). This is a creator surface; it may show secret knowledge, exactly as `KnowledgeEditor` already does with its `Secret` checkbox. It must not become a source that any context assembler reads.
- **Commit before touching any canon-writing path** (`CLAUDE.md:163`). `crud/knowledge.py` is one.
- **Structural over disciplinary.** The bind action posts no role because the surface offers no role field at all, not because the creator is trusted to leave it blank.
- **`idx_fact_participant_unique`** (`canon_knowledge.py:120`). One participant per `(fact_id, entity_id)`. The surface checks before it posts; it never relies on a 500 to tell it a binding exists.

## Decision rights

**STOP:**
- Any anchor above has moved.
- Any work in this brief turns out to require a `CREATION_ISLANDS` entry. It should not: item 3 edits a child component of an already-registered island, which needs none. If it does, that is TICKET-0088's subject and this brief stops.
- The entity payload the sheet reloads is assembled somewhere other than `crud/knowledge.py`, so Scope IN item 1 would have to change a second module's contract.
- `frontend_build_fresh.py` fails and the failure is not resolved by committing the build output.

**ADAPT:**
- `_knowledge_dict` or its equivalent is named differently: use whatever the module actually calls it, proceed, report.
- The picker needs an entity list endpoint that already exists elsewhere in the shell: reuse it rather than adding a route, proceed, report.
- `sheetRequest`'s signature does not fit a DELETE with no body: follow how `deleteRow` (`KnowledgeEditor.svelte:51-54`) already does it, proceed, report.
- A `confirm()` is conventional for destructive actions in this file (`KnowledgeEditor.svelte:52`): unbinding is reversible, so do not add one, and report the judgment.
- The route's response omits `fact_ids`: they are in `C-06` and TICKET-0088's panel needs them; add them, proceed, report.

**REPORT-ONLY:**
- The residue count per world after item 2 exists, and how far it falls during any manual binding from the entity sheet. TICKET-0088 inherits this number.
- Any unresolved subject that names two different entities and therefore cannot be bound to one.
- Any knowledge row whose fact already carries a non-`subject` participant.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor
> a `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or
> a `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] Commit exists on the branch before the first edit to `crud/knowledge.py`.
- [ ] `GET /api/entities/{id}` returns knowledge entries each carrying `fact_id` and `subject_participants`, and every key present before this brief is still present with the same value.
- [ ] `GET /api/worlds/verkhaal/unresolved-subjects` returns 28 entries after BRIEF-0087-c has run, ordered by `row_count` descending, each carrying `subject`, `fact_ids`, `row_count` and a flattened resolution.
- [ ] That route performs no write: `fact_participant` row count is identical before and after calling it.
- [ ] In the entity sheet, a knowledge row with no participant shows a picker; pressing `Bind` creates exactly one `fact_participant` row, with `role IS NULL`, and the row re-renders showing the bound name without a manual page reload.
- [ ] Pressing `Unbind` removes that row and the picker returns.
- [ ] Binding does not change the knowledge row's `subject`, `level`, `content`, `is_secret`, `is_incorrect` or `share_threshold`.
- [ ] Saving a knowledge row through the existing `Save` button does not create, remove or alter any `fact_participant`.
- [ ] `registry.js`, `tabs.js`, `mount.js` and `Creation.svelte` are byte-identical to their state before this brief.
- [ ] Binding a subject already bound on one of its facts creates no duplicate on that fact and returns no error to the surface.
- [ ] A fact carrying a participant with a non-NULL role written elsewhere displays that binding rather than a picker, and its `role` is unchanged after any action on that row.
- [ ] `python tooling/run.py` — `fact_spine.py`, `single_canon_write.py`, `frontend_build_fresh.py`, `static_asset_freshness.py`, `creation_island.py`, `json_ui_boundary.py`, `module_budget.py`, `function_length.py`, `corpus_gate.py` all PASS.
- [ ] `/review-step` and `/close-step` run; engine code is touched.

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: one entry recording that the subject-binding surface lives in the Creation shell because TICKET-0085 locked the lore consultation surface read-only for its first perimeter; with the reactivation condition for moving it (that lock being lifted by TICKET-0085's named successor).
- `CLAUDE.md`: the symbol-location line for the new route, per the TICKET-0070 rule. No panel line — there is no panel in this brief.
- No schema changelog entry. No version bump.
