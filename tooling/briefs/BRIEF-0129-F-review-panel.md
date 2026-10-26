<!-- slug: review-panel -->
# BRIEF 0129-F — "The review section of the creator's draft panel"

Lot: LOT-0129-creator-review.md (authoritative on conflict)
Depends on: C (C-08), D (C-09's routes), E (the approval route)

## Anchors to confirm (Mini-RECON)

- `frontend/src/creation/PcDraftPanel.svelte` is 140 lines; :126 is
  `<p class="muted notice">La revue de la créatrice arrive avec un prochain ticket : rien n'est encore écrit au monde.</p>`.
- `frontend/src/creation/pcDrafts.svelte.js` exports `loadSubmittedDrafts`,
  `selectPcDraft`, `loadPcDraft` and holds no `method:`.
- `frontend/src/creation/sheetRequest.svelte.js` exports `api(path,
  options)`.
- `frontend/src/creation/PjCreatePanel.svelte:140` is
  `creationState.entityListActivationTick += 1;`.
- `src/world_engine/cockpit/routes/pc_review.py` serves `GET`/`PUT
  /api/pc-reviews/{id}`, `POST .../lots`, `.../renvoyer`, `.../approuver`
  (C, D, E landed).

Halt if any anchor has moved.

## Facts carried

### R-10 -- the NPC agent's route
Opened: `src/world_engine/cockpit/routes/npc_agent.py:1-298`.
Finding: imports `NpcBatch, NpcBatchRow` (:29), `journal_append,
patch_npc_row, resolve_vocabulary, run_next_npc` (:30), `write_npc_goal`
(:31), `crud as _crud` (:32). `_open_batch(world_id, db)` (:50-55) is the
first `open` batch of the world; `create_npc_batch` (:65-112) 409s when it
finds one, validates each line (`count >= 1`, non-empty `description`,
`faction_id` in the vocabulary, `location_id` in the expanded set), sums
`total += count`, 422s above 30, stores `scope = {root_location_id,
expanded_location_ids, lines, group_brief}`, commits. `list_npc_batches`
(:115-125) returns every batch of the world. `get_npc_batch` (:128-136),
`abandon_npc_batch` (:139-153), `run_next_npc_batch` (:156-163),
`patch_npc_batch_row` (:166-175) take a batch id and no world filter.
`_commit_npc_row_goals(db, world_id, npc_id, goals)` (:178-195) writes the
long and short goals through `write_npc_goal`. `_commit_npc_row(row,
batch, db)` (:198-235) builds `EntityWriteBody(entity={"type":
"character", "name"}, extension={"character_type": "npc",
"current_location_id": row.payload["location_id"], ["faction_id"]},
facets=draft["facets"], carrure=pub.get("physical_tier"))`, calls
`_crud._create_entity_core`, writes each secret knowledge through
`_crud._create_knowledge_core` (`is_secret=True`), the goals, and returns
`{"row_id", "entity_id", "name"}`; it never commits and writes no
relation. `_commit_npc_batch` (:238-290) refuses a non-open batch and
`npcs_done != npcs_total`, commits rows `proposed`/`edited` of kind
`draft`, marks them and the batch `committed`, one `db.commit()`, journals.
Consequence: A moves `_commit_npc_row_goals` and `_commit_npc_row`
verbatim to `cockpit/npc_group_commit.py` (C-02); D filters review batches
out of `_open_batch` and `list_npc_batches` and refuses them in
`_commit_npc_batch` (C-09); the id routes serve review batches unchanged.
### R-11 -- the NPC group author
Opened: `src/world_engine/npc_group_author.py:30-56, 56-91, 170-235, 341-403, 405-470`
(520 lines).
Finding: `JOURNAL_DIR = Path.home() / ".world_engine" / "npc_agent_journal"`
(:41), read by `journal_append` at call time. `resolve_vocabulary(db,
root_location_id)` (:56-91) expands the root (zones dropped) and lists the
factions of the world where `World.is_active == True` (:74).
`plan_placements` (:170-191) calls the model only for lines without a
`location_id`. `_resolve_unit_location` (:203-222) returns a line's pinned
`location_id` first. `run_next_npc(db, batch)` (:341-403) refuses a
non-open batch, composes the brief, calls `generate_entity_draft(
"character", brief, db)` -- a name imported into the module (:33) --
forces `draft["public"]["faction_id"]` from the line (:380-383), checks the
name for collisions, calls `_generate_row_goals` (which calls the imported
`generate_npc_goals`), builds `NpcBatchRow(batch_id, line_index,
kind="draft", payload, row_status="proposed")` (:393), bumps
`npcs_done`, commits. `patch_npc_row` (:456-) edits `name`, the facet
strings, `physical_tier`, `faction_id`, `location_id` (within the
expanded set), the goals, and `row_status` in `("proposed", "rejected")`
(:407).
Consequence: a review batch pins every line's `location_id` to its root,
so no placement call is made; D forces the line's `name` and copies its
`pc_draft_sketch_id` to the row next to the faction forcing (C-10); a
check stubs `npc_group_author.generate_entity_draft`,
`npc_group_author.generate_npc_goals` and `npc_group_author.JOURNAL_DIR`
by assignment (they are module attributes read at call time).
### R-27 -- module budgets of the files this lot edits
Opened: `ast` count (module functions plus methods of module classes) and
`wc -l` at `11cafc0`; `tooling/verify/checks/module_budget.py:1-60`.
Finding: caps 1000 lines and 40 functions (`src/**/*.py`), 1000 lines
(`frontend/src/**`). `routes/creator.py` 968 / 35; `routes/npc_agent.py`
298 / 12; `npc_group_author.py` 520 / 18; `writes/pc_drafts.py` 325 / 18;
`creation_check.py` 257 / 8; `perspective_selectors.py` 321 / 14;
`models/pc_drafts.py` 163; `models/ephemeral.py` 318;
`routes/player_creation.py` 326 / 15; `cockpit/app.py` 347 / 12;
`writes/characters.py` 272 / 5; `PcDraftPanel.svelte` 140;
`PjSkillFiche.svelte` 249; `CharacterCreation.svelte` 91;
`character.svelte.js` 189; `tabs.js` 898; `WorldPage.svelte` 90.
Consequence: nothing new enters `routes/creator.py` (it shrinks by three
functions in A); every other file stays far under its caps; `tabs.js` is
not edited.
### R-28 -- the creator's frontend
Opened: `frontend/src/creation/PcDraftPanel.svelte:1-140`;
`frontend/src/creation/pcDrafts.svelte.js:1-39`;
`frontend/src/creation/EntityList.svelte:85-110, 190-205, 305-350`;
`frontend/src/creation/PjCreatePanel.svelte:25-35, 135-145`;
`frontend/src/creation/PjSkillFiche.svelte:1-120`;
`tooling/verify/checks/creation_layout.py:1-70`.
Finding: `PcDraftPanel.svelte` loads `loadPcDraft(id)` on
`creationState.selectedPcDraftId`, shows the draft read-only and ends with
`<p class="muted notice">La revue de la créatrice arrive avec un prochain
ticket : rien n'est encore écrit au monde.</p>` (:126). `pcDrafts.svelte.js`
exports `loadSubmittedDrafts`, `selectPcDraft`, `loadPcDraft` with a GET-only
fetch helper. CL5 requires `pcDrafts.svelte.js` to hold `'/api/pc-drafts'`
and no `method:`, and `PcDraftPanel.svelte` to hold none of `alert(`,
`confirm(`, `prompt(`, `method:`. `EntityList.svelte` reloads its lists
(`/api/skills/player-characters` included, which feeds
`creationState.playerCharIds`) when `creationState.entityListActivationTick`
changes (:200-203); `PjCreatePanel.svelte:140` bumps it with
`creationState.entityListActivationTick += 1;` after creating a character.
`PjSkillFiche.svelte` serves the `pj` and `npc` tabs: `characterType` is
`'npc'` on the `npc` tab, else `'player'` (:58); `characterId` holds the
selected character (:47, :64-65).
Consequence: the review UI is a child component with its own store (the
store holds `method:`; `PcDraftPanel.svelte` imports the component and
never a fetch); after approval the panel bumps the tick as
`PjCreatePanel.svelte` does; K1-b's field is a child of `PjSkillFiche`
shown when `characterType === 'player'`.
### R-31 -- the arrow floor
Opened: `tooling/verify/checks/pipeline_state.py:54, 113-120`.
Finding: for a ticket in `brief`, `exec`, `verify`, `live-gate` or `done`,
every Machine-checkable arrow must name an existing file under
`tooling/verify/checks/` (or a retired one), else `pipeline_state.py`
fails, and `corpus_gate.py` with it.
Consequence: while 0129 is in `exec`, `pipeline_state.py` is red for each
arrow whose check a later brief creates (`review_schema.py` until B,
`creator_review.py` until C, `draft_approval.py` until E,
`creator_review_ui.py` until F); each brief's Done means names that red,
never a green `corpus_gate.py` before F.

## Contracts

### C-05 -- the review check
Produced by: C   Consumed by: C's routes, D (blockers sit beside it), E
In `creation_check.py`:
```
REVIEW_VIOLATION_CODES: tuple[str, ...] = (
    "review_place_invalid", "sketch_undecided", "attach_invalid",
    "attach_duplicate", "master_not_master", "relation_type_invalid",
    "world_has_pc",
)
def review_place_id(draft: PcDraft) -> Optional[str]
def check_review(db: Session, draft: PcDraft) -> tuple[Violation, ...]
```
`review_place_id` is `draft.review_location_id` when set, else
`draft.start_location_id`. `check_review` reads only, never through the
public view, in this order:
1. `name_missing`, `story_missing` -- `check_draft`'s messages.
2. No place -> `start_place_missing` (« Choisis un lieu de départ. »); a
   place that is not an active `location` entity of the draft's world, or
   is in `zone_ids(db, world_id)` -> `review_place_invalid` « Ce lieu de
   départ ne peut pas être choisi. ».
3. `check_creation(db, world_id, {skill_key: player_rank ...},
   enforce_visibility=True).violations`.
4. `too_many_sketches` -- `check_draft`'s rule and message.
5. `master_without_sketch` -- `check_draft`'s rule and message, counting
   only master sketches whose `review_action` is not `drop`.
6. Each sketch by `(position, id)`:
   - `review_action` NULL -> `sketch_undecided` « « {name} » : choisis de
     créer cette personne, de la rattacher ou de l'écarter. »;
   - `attach` whose `review_entity_id` is not an active `character` entity
     of the world with a `character_type` other than `player` ->
     `attach_invalid` « « {name} » : le personnage choisi n'existe pas
     dans ce monde. »; else an entity an earlier `attach` sketch already
     names -> `attach_duplicate` « « {name} » : ce personnage est déjà
     choisi pour une autre personne. »; else a `master` sketch whose entity
     is not in
     `skill_masters(...)` for its `skill_key` -> `master_not_master`
     « « {name} » n'est pas Maître en « {skill} ». » (`{skill}` the
     `start_sheet` name of the key);
   - `create` or `attach` whose `review_relation_type` (stripped) is empty,
     not `is_social`, or in `RETIRED_RELATION_TYPES` ->
     `relation_type_invalid` « « {name} » : le lien « {type} » ne peut
     pas être choisi. ».
7. Each membership not `review_dropped` whose faction is not an active
   `faction` entity of the world -> `membership_invalid` (`check_draft`'s
   message).
8. `pc_exists` -- `check_draft`'s rule and message.
9. Any `character_type == "player"` character in the world ->
   `world_has_pc` « Ce monde a déjà un personnage joueur : l'approbation
   attend le sélecteur « PJ actif ». ».
A skill key is a base domain when it is in `BASE_SKILL_DOMAINS` (then
`skill_masters(..., definition_id=None, domain=key)`), else a definition id
(`definition_id=key, domain=None`). `DRAFT_VIOLATION_CODES` is unchanged.
### C-08 -- the review routes
Produced by: C (D, E, G add routes)   Consumed by: F, G's frontend
Module `src/world_engine/cockpit/routes/pc_review.py`, keyed by the active
world (`_world_id` from `..crud._shared`); a draft of another world, or not
`submitted` where a submitted one is required, answers 404 `Brouillon
introuvable.`.
- `GET /api/pc-reviews/{draft_id}` -> exactly `{"draft", "player_name",
  "review", "choices", "verdict", "skill_names", "ranks", "groups",
  "blockers"}`: `draft` is `draft_view(db, draft, view=None)`; `review` is
  C-07's `review_view`; `choices` is `review_choices` plus
  `"relation_types": [t for t in RELATION_TYPES if is_social(t)]`;
  `verdict` is `verdict_dict(check_creation(... player ranks ...,
  enforce_visibility=True), check_review(db, draft))`; `skill_names` and
  `ranks` as `GET /api/pc-drafts/{id}`; `groups` is `[{"label",
  "sketch_ids", "lot"}]` for the sketches whose action is `create`, groups
  by first position, `lot` null until D; `blockers` `[]` until D.
- `PUT /api/pc-reviews/{draft_id}` body `{"review_location_id": str |
  null, "sketches": [{"id", "action", "entity_id", "relation_type",
  "intensity"}], "memberships": [{"id", "dropped"}]}` -> `save_review`,
  commit, the GET shape. `DraftLocked` -> 409; `ValueError` -> 422.
- `POST /api/pc-reviews/{draft_id}/renvoyer` body `{"note"}` ->
  (D: `abandon_review_lots` first) `return_draft`, commit, `{"ok": true,
  "status": "returned"}`; `ValueError` -> 422.
- D: `POST /api/pc-reviews/{draft_id}/lots` body `{"group_label"}` ->
  C-09's `prepare_group_lot`, commit, then `journal_append(batch.id,
  {"event": "batch_created", "scope": batch.scope, "pc_draft_id":
  draft.id})`, answer `{"batch_id", "npcs_total"}`; `ValueError` -> 422.
- E: `POST /api/pc-reviews/{draft_id}/approuver` -> C-11, commit, then
  one `journal_append(lot_id, {"event": "commit_by_approval",
  "pc_draft_id", "character_id"})` per committed lot, answer `{"ok": true,
  "character_id", "name"}`; `ApprovalRefused` or `DraftLocked` -> 409
  `Ce personnage ne peut pas encore être approuvé.`; `ValueError` or
  `IntegrityError` -> 409 with its text; every refusal rolls back first.
- G: C-14's two profile routes.
`app.py` registers the router (R-30).
### C-09 -- the review batches
Produced by: D   Consumed by: C-08 (D's additions), E
Module `src/world_engine/cockpit/pc_approval.py` (allowed by
`npc_agent_strata.py`, R-13):
```
def review_groups(db, draft) -> list[dict]          # [{"label", "sketch_ids"}]
def open_review_lots(db, draft) -> list[NpcBatch]    # open batches with pc_draft_id = draft.id, by created_at
def lot_view(batch: NpcBatch) -> dict                # {"batch_id", "status", "npcs_done", "npcs_total"}
def prepare_group_lot(db, draft, group_label: str) -> NpcBatch
def abandon_review_lots(db, draft) -> list[str]
def review_blockers(db, draft) -> list[dict]         # [{"code", "label", "sketch_id", "message"}]
```
`review_groups`: the draft's `create` sketches by `(position, id)`,
grouped by `group_label`, groups in order of first appearance.
`prepare_group_lot`: the draft is `submitted` (`DraftLocked` otherwise);
the group has a `create` sketch (`ValueError("Ce groupe n'a personne à
créer.")`); no open batch for `(draft.id, group_label)`
(`ValueError("Un lot est déjà ouvert pour ce groupe.")`); `root =
review_place_id(draft)` (C-05); `vocabulary = resolve_vocabulary(db,
root)`; one line per `create` sketch of the group, in order:
`{"count": 1, "description": D, "faction_id": None, "location_id": root,
"name": sketch.name, "pc_draft_sketch_id": sketch.id}` with `D =
f"{sketch.name}, {sketch.role or 'une personne de son histoire'}."`, then
`f" {sketch.sentence}"` when the sentence is not empty, then, for a
`master`, `f" Maître en « {skill} », il a enseigné cette compétence à
{draft.name}."`; `group_brief` verbatim:
```
Ces personnes viennent de l'histoire de {draft.name}, un personnage joueur qui entre dans le monde. Chacune le connaît ; développe-la avec tout ce que le monde sait.
Groupe : {group_label or 'sans groupe'}.

Histoire de {draft.name} :
{draft.story}
```
`NpcBatch(world_id=draft.world_id, scope={"root_location_id": root,
"expanded_location_ids": vocabulary["expanded_location_ids"], "lines":
lines, "group_brief": brief}, npcs_total=len(lines),
pc_draft_id=draft.id, pc_group_label=group_label)`, added and flushed;
never commits. `abandon_review_lots`: every open batch of the draft ->
`status = "abandoned"`, `closed_at = now`; returns their ids.
`review_blockers`, for each `create` sketch by `(position, id)`: no open
batch for its group -> `lot_missing` « « {label} » : prépare le lot de ce
groupe. »; else `npcs_done < npcs_total` -> `lot_incomplete` « « {label} »
: la génération du lot n'est pas terminée. »; else no row of that batch
with `pc_draft_sketch_id == sketch.id`, `kind == "draft"` and
`row_status in ("proposed", "edited")` -> `row_missing` « « {name} » :
aucune fiche retenue dans le lot. ». `{label}` is the label or `sans
groupe`. One blocker per sketch at most; a group's `lot_missing` /
`lot_incomplete` is listed once per group.
In `cockpit/routes/npc_agent.py`: `_open_batch` and `list_npc_batches`
add `.where(NpcBatch.pc_draft_id.is_(None))`; `_commit_npc_batch`, right
after its `status != "open"` guard, raises 409 « Ce lot appartient à la
revue d'un personnage : il s'écrit à l'approbation. » when
`batch.pc_draft_id is not None`.
### C-15 -- the review's frontend store
Produced by: F   Consumed by: F's component
`frontend/src/creation/pcReview.svelte.js` exports `loadReview(id)`,
`saveReview(id, body)`, `returnDraft(id, note)`, `prepareLot(id, label)`,
`loadLot(batchId)` (`GET /api/npc-batches/{id}`), `runLot(batchId)`
(`POST /api/npc-batches/{id}/run-next` until `npcs_done ===
npcs_total`), `setLotRow(batchId, rowId, patch)` (`PATCH
/api/npc-batches/{id}/rows/{rowId}`), `abandonLot(batchId)`,
`approveDraft(id)`, each through `api(path, options)` imported from
`./sheetRequest.svelte.js` (the shared helper `PjSkillFiche.svelte`
uses: it throws the response's `detail`); a write passes `{ method,
headers: { 'Content-Type': 'application/json' }, body:
JSON.stringify(...) }`. `afterApproval()` sets
`creationState.selectedPcDraftId = null`, calls `loadSubmittedDrafts()`
(from `./pcDrafts.svelte.js`) and bumps
`creationState.entityListActivationTick += 1;` (the
`PjCreatePanel.svelte:140` precedent); `afterReturn()` does the first two.

## Context

The creator reviews a submitted draft where she already reads it: the
panel that opens from « Personnages joueurs » > « Soumis » (W1' of 0126).
Below the player's version, a review section lets her set the place, each
person, each membership, prepare and generate each group's batch and
review its rows, then return the draft with a note or approve it. Nothing
stacks: the section is inside the panel, the panel alone in the column.

## Scope IN

1. New `frontend/src/creation/pcReview.svelte.js` per C-15 (header comment
   « TICKET-0129 (BRIEF-0129-F, C-15). The creator's review of a submitted
   character draft: her choices, the batches per group, the return and the
   approval. Every write goes through `api` (sheetRequest.svelte.js). »).
2. New `frontend/src/creation/PcReviewSection.svelte`, prop `draftId`,
   header comment naming TICKET-0129, BRIEF-0129-F, C-08, C-15. It loads
   `loadReview(draftId)` when `draftId` changes (a sequence counter as
   `PcDraftPanel.svelte` uses; inside the `$effect`, never read a `$state`
   binding after assigning it -- `effect_self_write.py`), keeps an editable
   copy of `review` and shows, in this order:
   - **Revue de la créatrice** (h4).
   - **Lieu de départ** -- a `<select>` over `choices.places`, the
     player's place marked « (choix du joueur) », bound to the copy's
     `review_location_id` (`''` = the player's).
   - **Personnes** -- one block per sketch of the review body's
     `draft.sketches`, matched by `id` to `review.sketches`: its name, kind
     and role; three radio buttons « Créer », « Rattacher »,
     « Écarter »; on « Rattacher » a `<select>` over `choices.masters[
     skill_key]` for a master sketch, else `choices.characters`, with the
     player's suggestion (`existing_entity`) marked « (proposé par le
     joueur) »; on « Créer » or « Rattacher » a « Lien » `<select>` over
     `choices.relation_types` and an « Intensité » number 1-100.
   - **Appartenances** -- one checkbox « Garder » per membership.
   - A button « Enregistrer la revue » -> `saveReview`, then the answer
     replaces the copy.
   - **Lots** -- per entry of `groups`: its label (« sans groupe » when
     empty) and its people; no `lot` -> « Préparer le lot »
     (`prepareLot`); a lot not complete -> « Générer » (`runLot`, the
     button disabled while it runs, `npcs_done / npcs_total` shown); a
     complete lot -> its rows (`loadLot`): the name in an `<input>` saved on
     change (`setLotRow(..., {payload_patch: {name}})`), the facet
     `description` when present, a checkbox « Retenir » (`row_status`
     `proposed` / `rejected`); « Abandonner le lot » (`abandonLot`). After
     each call, reload the review.
   - **Vérification** -- `verdict.violations` then `blockers` messages; «
     Prêt à approuver. » when both are empty.
   - « Note pour le joueur » `<textarea>` and « Renvoyer au joueur »
     (`returnDraft`, then `afterReturn()`).
   - « Approuver » (`approveDraft`, then `afterApproval()`), disabled while
     violations or blockers remain or a call runs.
   Errors show in place (`r-err`), never through `alert(`, `confirm(`,
   `prompt(`. No `fetch(` in the component.
3. `PcDraftPanel.svelte`: import `PcReviewSection` and replace the line
   :126 by `<PcReviewSection draftId={creationState.selectedPcDraftId} />`;
   the header comment's « Read only -- the review is TICKET-0129 »
   becomes « The review section (PcReviewSection.svelte, TICKET-0129)
   follows the player's version. ». The panel itself still makes no
   write call.
4. `frontend/public/creation.css`: a `.pc-review` rule block (spacing of
   the section's blocks, `r-err` already exists) -- only what the section
   needs.
5. Rebuild the frontend and commit the built output.
6. `tooling/verify/checks/creator_review_ui.py`, first sentence « G1 check
   for TICKET-0129 -- the creator's review section and the player's
   returned and accepted states are wired. », static, stdlib only:
   - **CU1** `PcDraftPanel.svelte` holds `<PcReviewSection` and `import
     PcReviewSection`, not `La revue de la créatrice arrive avec un
     prochain ticket`, and none of `alert(`, `confirm(`, `prompt(`,
     `method:`; `PcReviewSection.svelte` holds `Enregistrer la revue`,
     `Préparer le lot`, `Générer`, `Renvoyer au joueur`, `Approuver`,
     `Rattacher`, `Écarter`, `Prêt à approuver.`, and none of `fetch(`,
     `alert(`, `confirm(`, `prompt(`; `pcReview.svelte.js` holds the
     literals `/api/pc-reviews/`, `/lots`, `/renvoyer`, `/approuver`,
     `/api/npc-batches/`, `/run-next`, `entityListActivationTick += 1`,
     `loadSubmittedDrafts(` and an import from `./sheetRequest.svelte.js`;
     a built asset under `src/world_engine/cockpit/static/assets` carries
     `Renvoyer au joueur`.
   A missing file, or a rule that collected nothing, is a FAILURE. (G adds
   CU2 and CU3.)
7. Commits: (1) items 1-4; (2) item 5; (3) item 6.

## Scope OUT

- Any backend change; the NPC agent's own panel.
- Editing a row beyond its name and its retained state (the agent's
  panel does the rest for its own batches; the review keeps to what the
  approval needs).
- The player's screens and K1-b (G).

## Invariants to defend

- INV-50: no new island; the section is a child component of the
  registered `pcDraftPanel` island, `Creation.svelte` untouched
  (`creation_island.py` rule 13).
- Nothing stacks: CL1-CL5 of `creation_layout.py` hold unchanged.
- INV-20: every value shown comes from the review routes' columns.

## Decision rights

STOP:
- An anchor does not hold.
- `creation_layout.py`, `creation_island.py`, `effect_self_write.py`,
  `modal_primitive.py` or `frontend_build_fresh.py` turns red on a rule
  this brief cannot satisfy without touching another island.

ADAPT:
- `PcDraftPanel.svelte`'s detail fetch 404s once the draft is returned or
  approved: `afterReturn` / `afterApproval` clear the selection first, so
  the panel closes; report if a flash remains.
- A label reads better in another place of the section: keep C-08's data
  and the literals CU1 pins, report.

REPORT-ONLY:
- Long batches: generation runs one `run-next` per person, as the agent's
  panel does.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/creator_review_ui.py`
      PASS (CU1); `creation_layout.py`, `creation_island.py`,
      `effect_self_write.py`, `modal_primitive.py`, `frontend_build_fresh.py`,
      `module_budget.py` PASS.
- [ ] Named mutations, each red then reverted: put the old notice back ->
      CU1; add `alert(` to `PcReviewSection.svelte` -> CU1; add a `method:`
      call to `PcDraftPanel.svelte` -> CU1 and CL5.
- [ ] `corpus_gate.py` PASS (every arrow of the ticket now names an
      existing check).
- [ ] Live: the ticket's live criteria 1-3 and 5 (creator side) behave as
      written.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- None beyond the header comments. No schema change.
