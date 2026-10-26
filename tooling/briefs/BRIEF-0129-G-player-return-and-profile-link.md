<!-- slug: player-return-and-profile-link -->
# BRIEF 0129-G — "The player's returned and accepted states; K1-b"

Lot: LOT-0129-creator-review.md (authoritative on conflict)
Depends on: C (C-06, C-08's module), E (an approved draft has its character), F (`creator_review_ui.py`)

## Anchors to confirm (Mini-RECON)

- `frontend/src/joueur/CharacterCreation.svelte:12` is `const locked =
  $derived(characterState.draft && characterState.draft.status !==
  'draft');`, `:28` shows `Soumis à la créatrice — en attente de sa
  revue.`.
- `frontend/src/joueur/character.svelte.js:111` is `export async function
  openCreation() {`; its body posts `brouillon` when `body.draft` is null.
- `src/world_engine/cockpit/routes/player_creation.py:182-188` is
  `get_draft`, answering `{"draft": None, "verdict": None}` when no draft
  is open.
- `frontend/src/creation/PjSkillFiche.svelte` is 249 lines; `const
  characterType` at :58, `let characterId` at :47; its markup opens at
  :174 with `<div class="panel-head"`, and `<div class="author-main"` at
  :185.
- `tooling/standards/ARCHITECTURE_DECISIONS.md` ends with a blank line,
  `---`, a blank line, `*Co-built with Claude, June 2026.*`.
- `tooling/verify/checks/creator_review_ui.py` holds CU1 (F landed).

Halt if any anchor has moved.

## Facts carried

### R-04 -- the player's creation routes
Opened: `src/world_engine/cockpit/routes/player_creation.py:1-326`.
Finding: `_writable(draft)` (:127-129) raises 409 `DRAFT_LOCKED_MESSAGE`
when `draft.status != "draft"`; `ask_designer` (:254-311) and
`submit_player_draft` (:314-326) call it; `save_draft` (:204-224) relies on
`save_player_draft`'s `DraftLocked`. `get_draft` (:182-188) answers
`{"draft": None, "verdict": None}` when `open_draft_of` finds nothing, else
`_draft_body` = `{"draft": draft_view(..., view=public_view(...)),
"verdict": ...}`. Every path starts with `/api/joueur/creation/`.
Consequence: C changes `_writable` with `_require_open` (one rule, two
places, both named in Scope IN); G adds `character_name` to `get_draft`'s
`None` branch (C-16).
### R-15 -- the canon-write policy
Opened: `tooling/verify/canon_write_policy.txt:1-147`;
`tooling/verify/checks/single_canon_write.py:1-70, 337-366, 557-580`.
Finding: `[CANON_TABLES]` holds `entity character ... faction_membership
relation knowledge ... skill ...`; `[ALLOWED_SITES]` lines are
`path::function   tables`, a relocation carrying a `#` comment above it;
`creator.py::create_player_character  entity character skill` (:147). The
check attributes each `.add()`/`.delete()` on a session to a table,
following a variable through the declared return type of the function that
produced it (`build_return_types`, :337), and fails a canon table written
from an unlisted site or an unattributable site. `write_membership`
(`writes/factions.py:61-108`), `write_relation` (`writes/relations.py:402`),
`write_skill_row` (`writes/characters.py:145`) and `write_knowledge` add
their row themselves; `write_skill_rank` leaves the add to its caller.
Consequence: A replaces line 147 by `writes/player_characters.py::
write_player_character  entity character skill` with a relocation
comment; E adds `writes/player_characters.py::write_master_rank  skill`
(`write_skill_rank` leaves the add to its caller); G adds
`writes/player_characters.py::set_player_profile  character`. No other module of the lot calls `db.add` on a row a writer
returned; `write_skill_rank`'s row is added inside the writer module that
calls it (E's master step lives in `writes/player_characters.py`, C-12).
### R-20 -- the character and the profile
Opened: `src/world_engine/models/canon.py:149-175`;
`src/world_engine/models/pipeline.py:711-726`.
Finding: `Character` declares `idx_character_one_pc_per_user_world
(world_id, user_id) UNIQUE WHERE character_type = 'player'` (:158-161),
`character_type: str` (:169), `user_id: Optional[str]` with no FK (:170).
`User`: `id, name, email, role (server default 'player'), created_at,
is_active`; the creator is the user with `role == "creator"`
(`routes/creator.py:826`).
Consequence: K1-b (G) sets `Character.user_id` to a player profile's id or
to the creator's; a collision is the unique index's `IntegrityError`.
### R-24 -- the player's creation check
Opened: `tooling/verify/checks/player_creation.py:1-90, 280-340`.
Finding: PC3 requires every code of `DRAFT_VIOLATION_CODES` to be reached
with its message in `MESSAGES` (:74-84, :338-339). PC5: after a clean
submit, `PUT`, designer and submit answer 409 `DRAFT_LOCKED_MESSAGE`. PC7
forbids `chat(`, `World.is_active`, `_world_id(`, `lore_selectors`,
`CREATOR` in `routes/player_creation.py`, `writes/pc_drafts.py`,
`pc_draft_reads.py`, and requires every route path to start with
`/api/joueur/creation/`.
Consequence: review codes live in a new `REVIEW_VIOLATION_CODES`;
`writes/pc_drafts.py` takes no `_world_id(` (the review writer receives the
draft); a submitted draft stays locked (PC5 holds); the player's route
module gains no non-`/api/joueur/creation/` path.
### R-26 -- the instruction corpus
Opened: `tooling/verify/checks/claude_md_contract.py:1-80`; `CLAUDE.md`
(20 663 bytes) lines 145-151, 169-177, 204-218; `.claude/rules/character-creation.md`
(1 066 bytes, 20 lines); `tooling/standards/ARCHITECTURE_DECISIONS.md` (last 5 lines).
Finding: root budget 22 000 characters, each rule file 4 000, no line over
100 characters; every Invariants bullet starts `- **INV-NN**` and ends with
`-- enforced by` and checks under `tooling/verify/checks/`, or
`[no check]`; ids run INV-01 to the highest without a gap; a rule file
opens with `paths:` globs that each match a file; no `TICKET-\d` or
`BRIEF-\d` inside an Invariants section. `character-creation.md`'s paths
are `creation_rules.py`, `creation_check.py`, `writes/creation_rules.py`,
`writes/pc_drafts.py`, `pc_draft_reads.py`, `routes/player_creation.py`;
its one invariant is INV-67. INV-08 names the two canon-write paths for
rows (`_apply_mutation`, creator CRUD). ARCHITECTURE_DECISIONS ends with a
blank line, `---`, a blank line, `*Co-built with Claude, June 2026.*`.
Consequence: E adds INV-68 to `character-creation.md` with its new paths;
A edits INV-07's parenthesis (R-19); G inserts the decisions entry above
the footer. The approval is a creator-direct write (INV-08's creator path),
like the NPC agent's commit of model-generated rows (R-10).
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
### R-29 -- the player's frontend
Opened: `frontend/src/joueur/CharacterCreation.svelte:1-91`;
`frontend/src/joueur/character.svelte.js:1-189`;
`tooling/verify/checks/player_shell.py:1-40`.
Finding: `locked` is `characterState.draft && characterState.draft.status
!== 'draft'` (:12); when locked the screen shows `Soumis à la créatrice —
en attente de sa revue.` (:28). `openCreation()` (:111-119) loads the
catalogue, `GET brouillon`, and `POST brouillon` when `body.draft` is null;
`take(body)` stores `draft`, `verdict`, `form`. PSH2: every URL literal
under `frontend/src/joueur/` starts with `/api/joueur/`; PSH5 requires the
three creation components to hold `Soumis à la créatrice — en attente de sa
revue.` among other strings.
Consequence: G locks only `submitted`, shows the note on `returned`, and
reads `character_name` before posting; the PSH5 string stays.
### R-34 -- the check fixture
Opened: `tooling/verify/checks/submitted_drafts.py:40-60, 155-170`;
`tooling/verify/checks/player_creation.py:90-140`.
Finding: `_fresh_engine()` sets `WORLD_ENGINE_DATABASE_URL` to a temp file
and `WORLD_ENGINE_ENV=test` before any `world_engine` import, purges
`world_engine*` from `sys.modules`, imports `world_engine.models`, runs
`SQLModel.metadata.create_all(engine)`. Routes are called through
`TestClient(app, base_url="http://127.0.0.1")` with `app` from
`world_engine.cockpit.app` (:159-166). Profiles come from
`writes.users.create_player_profile`; drafts from `writes/pc_drafts.py`.
Consequence: the lot's checks build their worlds this way, never on Nia's
database.

## Contracts

### C-06 -- the draft writer's review functions
Produced by: C (E adds `mark_approved`)   Consumed by: C's routes, E, G
In `writes/pc_drafts.py`:
```
OPEN_STATUSES: tuple[str, ...] = ("draft", "returned")
REVIEW_LOCKED_MESSAGE = "Ce personnage n'est pas soumis : il ne peut pas être revu."
RETURN_NOTE_MISSING = "Écris une note pour le joueur."
def _require_open(draft) -> None        # status not in OPEN_STATUSES -> DraftLocked(DRAFT_LOCKED_MESSAGE)
def _require_submitted(draft) -> None   # status != "submitted" -> DraftLocked(REVIEW_LOCKED_MESSAGE)
def save_review(db, draft, *, review_location_id: Optional[str],
                sketches: list[dict], memberships: list[dict]) -> None
def return_draft(db, draft, *, note: str) -> None
def mark_approved(db, draft, *, character_id: str) -> None     # E
```
`save_review`: `_require_submitted`; `review_location_id` None or an
existing entity id (`ValueError("Entité inconnue.")`); each sketch item
`{"id", "action", "entity_id", "relation_type", "intensity"}` names a
sketch of this draft (`ValueError("Personne inconnue.")`), `action` is
None or in `PC_REVIEW_ACTIONS` (`ValueError("Choix inconnu.")`),
`entity_id` is kept only for `attach` (an existing entity, else
`ValueError("Entité inconnue.")`; None for every other action), an empty
`relation_type` becomes `PC_REVIEW_DEFAULT_RELATION`, `intensity` is an int
in 1..100 (`ValueError("L'intensité va de 1 à 100.")`); each membership
item `{"id", "dropped"}` names a membership of this draft
(`ValueError("Appartenance inconnue.")`). An unlisted row keeps its
values. Sets `updated_at`, flushes. `return_draft`: `_require_submitted`;
a stripped empty note -> `ValueError(RETURN_NOTE_MISSING)`; `status =
"returned"`, `creator_note = note` (stripped), `updated_at`; flushes. The
review columns are left as they are. `mark_approved`:
`_require_submitted`; `status = "approved"`, `character_id`, `updated_at`;
flushes. `submit_draft`, `save_player_draft`, `apply_design` keep their
code and reach a `returned` draft through the widened `_require_open`.
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
### C-14 -- K1-b
Produced by: G   Consumed by: G's frontend
In `writes/player_characters.py`:
```
PROFILE_UNKNOWN = "Profil inconnu."
NOT_A_PC = "Ce personnage n'est pas un personnage joueur."
PROFILE_CREATING = "Ce profil crée déjà un personnage dans ce monde."
def set_player_profile(db: Session, *, character_id: str, user_id: str) -> Character
```
The `Character` must exist with `character_type == "player"`
(`ValueError(NOT_A_PC)`); the `User` must exist with `role` in `("player",
"creator")` (`ValueError(PROFILE_UNKNOWN)`); a `player` user holding a
not-approved draft in the character's world -> `ValueError(PROFILE_CREATING)`;
sets `user_id`, adds, flushes (an `IntegrityError` propagates).
In `cockpit/routes/pc_review.py`:
- `GET /api/pc-profiles?character_id=` (a player character of the active
  world, else 404 `Personnage introuvable.`) -> `{"profiles": [{"id",
  "name"}], "current_profile_id": str | null}`: active `player` users by
  name; `current_profile_id` the character's `user_id` when that user is a
  `player`, else null.
- `PUT /api/pc-profiles/{character_id}` body `{"profile_id": str | null}`
  -> null means the `creator` user; `set_player_profile`, commit, the GET
  shape. `ValueError` -> 422; `IntegrityError` -> rollback, 409 « Ce profil
  a déjà un personnage dans ce monde. ».
### C-16 -- the player's accepted and returned states
Produced by: G   Consumed by: G's frontend
`get_draft`'s branch with no open draft answers `{"draft": None, "verdict":
None, "character_name": name}`, `name` the entity name of the player
character the profile holds in the world (`Character.world_id`,
`Character.user_id == profile_id`, `character_type == "player"`) --
approved from a draft or attached by K1-b --, else null. The branch with
an open draft keeps its two keys. A `returned` draft is answered as any
open draft (`status: "returned"`, `creator_note` set).
### C-17 -- K1-b's frontend
Produced by: G   Consumed by: `PjSkillFiche.svelte`
`frontend/src/creation/pcProfiles.svelte.js` exports
`loadProfiles(characterId)` (`GET /api/pc-profiles?character_id=`) and
`setProfile(characterId, profileId)` (`PUT /api/pc-profiles/{id}`, body
`{profile_id}`), through the same `api`. `PjProfileField.svelte` (prop
`characterId`) shows a `<select>` labelled « Joueur » whose first option
is « Créatrice » (value `''`, sent as `null`), then one option per
profile; a change saves at once and shows the server's message on a
refusal, in place; no `alert(`, `confirm(`, `prompt(`.
`PjSkillFiche.svelte` imports it and renders `<PjProfileField
{characterId} />` above its skill list when `characterType === 'player'`
and `characterId` is set.

## Context

B1: a returned draft is the player's again -- he sees « Renvoyé », the
creator's note and his own version, corrects and resubmits. Once
approved, he reads that his character exists. H1 (0126): a player
character in Création can be attached to a player profile, or given back
to the creator. This brief closes the ticket with its decisions entry.

## Scope IN

1. `routes/player_creation.py`: C-16 in `get_draft`'s None branch (one
   `select(Entity.name).join(Character, Character.id == Entity.id).where(
   Character.world_id == world_id, Character.user_id == profile_id,
   Character.character_type == "player")`; import `Character, Entity`
   from `...models`).
2. `frontend/src/joueur/character.svelte.js`: `characterState` gains
   `characterName: null`; `openCreation()` takes `body.character_name`
   into it and, when it is set, opens no draft (no `POST`); `closeCreation`
   resets it. The header comment: « A returned draft is the player's
   again; a profile holding a character sees its name (TICKET-0129,
   BRIEF-0129-G). »
3. `frontend/src/joueur/CharacterCreation.svelte`: `locked` is
   `characterState.draft && characterState.draft.status === 'submitted'`;
   on `status === 'returned'` a block « Renvoyé par la créatrice. » with
   `creator_note` (pre-wrapped) above the form; when
   `characterState.characterName` is set the screen shows only « Ton
   personnage {name} a été accepté dans ce monde. » and « Fermer ». The
   string `Soumis à la créatrice — en attente de sa revue.` stays (PSH5).
4. `writes/player_characters.py`: C-14's constants and
   `set_player_profile` (import `PcDraft, User` from `..models`).
   `canon_write_policy.txt`: `src/world_engine/writes/player_characters.py::set_player_profile character`
   with the comment `# TICKET-0129, BRIEF-0129-G: set_player_profile
   attaches a player character to a player profile or gives it back to
   the creator (K1-b, H1).`
5. `routes/pc_review.py`: C-14's two routes (`PcProfileBody {profile_id:
   Optional[str] = None}`); the `creator` user is read as
   `select(User).where(User.role == "creator")`, 422 « Aucune
   créatrice. » when absent.
6. New `frontend/src/creation/pcProfiles.svelte.js` and
   `frontend/src/creation/PjProfileField.svelte` per C-17 (header comments
   naming TICKET-0129, BRIEF-0129-G, K1-b); `PjSkillFiche.svelte` imports
   the field and renders it as the first child of `<div
   class="author-main"`, inside `{#if characterType === 'player' &&
   characterId}`. Add no other line to `PjSkillFiche.svelte`; it renders
   inside the legacy document (no scoped `<style>`, R-28).
7. Rebuild the frontend and commit the built output.
8. `tooling/verify/checks/creator_review.py`, new rule **CR6** (and its
   docstring line), on the fixture of CR1: a player character `Héros` of
   the world bound to the creator; `GET /api/pc-profiles?character_id=`
   -> profiles Ana and Bea, `current_profile_id` null; `PUT` Ana -> 200,
   `Character.user_id` Ana, `current_profile_id` Ana; `PUT` null -> the
   creator user; Bea holding an open draft in the world -> 422
   `PROFILE_CREATING`; Ana holding another player character in the world
   -> 409 « Ce profil a déjà un personnage dans ce monde. »; an NPC id ->
   422 `NOT_A_PC`; an unknown id -> 404 `Personnage introuvable.`. And
   C-16: once `Héros` is Ana's, her `GET /api/joueur/creation/brouillon`
   answers `{"draft": None, "verdict": None, "character_name": "Héros"}`;
   Bea's, with no draft and no character, `character_name` null.
9. `tooling/verify/checks/creator_review_ui.py`: **CU2** --
   `CharacterCreation.svelte` holds `status === 'submitted'`, `Renvoyé
   par la créatrice.`, `creator_note`, `a été accepté dans ce monde.`;
   `character.svelte.js` holds `character_name`; a built asset carries
   `Renvoyé par la créatrice.`. **CU3** -- `PjSkillFiche.svelte` holds
   `<PjProfileField` and `characterType === 'player'`;
   `PjProfileField.svelte` holds `Joueur`, `Créatrice`, and none of
   `alert(`, `confirm(`, `prompt(`, `fetch(`; `pcProfiles.svelte.js`
   holds `/api/pc-profiles`. The docstring lists CU2 and CU3.
10. `tooling/standards/ARCHITECTURE_DECISIONS.md`, inserted above the
    footer's `---`, verbatim:
    ```
    ## TICKET-0129 — the creator reviews a submitted character

    The creator reviews a player's submitted character beside his own
    version, never editing it (A1): her starting place, each person of his
    story created, attached to an existing character or left out, each
    master, each membership, and the feeling each person has for him (K1)
    live in review columns of the draft tables (v2.33). Each group of
    people to create is one batch of the NPC group agent, anchored on the
    character and his story (D2, F'a-1), kept out of the agent's own panel
    and commit. She returns the draft with a note -- the player gets his
    version back and resubmits (B1) -- or approves it: one transaction
    writes the NPCs, the masters' Maître rank, the character at the
    player's ranks with his teachers, memberships with encounters of the
    factions' public members (F-b), knowledge, relations, and closes the
    draft with its character (E1, C1). The character recipe moved to a
    commit-free writer shared with Création's own route (H1); the NPC row
    commit to `cockpit/npc_group_commit.py` (J1). A player character can be
    attached to a player profile from its skill pane (K1-b).

    **INV-68.** A drafted character reaches canon only through
    `pc_approval.approve_draft`, in one transaction, refused unless
    `check_review` and `review_blockers` find nothing; the review never
    edits the player's version; a review batch is written only by the
    approval. Held in `.claude/rules/character-creation.md`. Gates:
    `draft_approval.py`, `creator_review.py`.

    Deferred: ranks set before the write (A2; the skill tools after the
    approval meanwhile); a second player character per world (G2,
    TICKET-0128); dated encounters (TICKET-0120).

    ```
    (the blank line before the footer's `---` kept).
11. Commits: (1) items 1-3, 8's C-16 part, 7's build; (2) items 4-6, the
    rest of 8, 9, 7's build; (3) item 10.

## Scope OUT

- The « PJ actif » selector (TICKET-0128); a player choosing among
  several characters.
- Showing the creator's review choices to the player (C1 (0126)).
- Deleting a returned draft (nothing is deleted).

## Invariants to defend

- INV-66: the player's routes still read the world through the public
  view; `character_name` is the player's own character.
- PC7 and PSH2: `routes/player_creation.py` gains no non-`/api/joueur/`
  path and none of PC7's tokens; `frontend/src/joueur/` calls only
  `/api/joueur/`.
- INV-08: K1-b's write goes through a listed writer.
- One player character per profile and world
  (`idx_character_one_pc_per_user_world`), refused clearly.

## Decision rights

STOP:
- An anchor does not hold.
- `player_creation.py`, `player_shell.py`, `npc_skills.py`,
  `skill_progression.py`, `rank_trials.py` or `single_canon_write.py`
  turns red on a rule this brief cannot satisfy.

ADAPT:
- `PjSkillFiche.svelte`'s selected character is not the character the
  sheet shows (`selectedEntityId` drives it, R-28): pass `characterId`
  as the fiche holds it, report.
- A profile with a character and also a not-approved draft (from before
  K1-b): `character_name` wins, the draft stays untouched; report.

REPORT-ONLY:
- Profiles that are inactive are not offered.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/creator_review.py`
      PASS (CR1-CR6); `creator_review_ui.py` PASS (CU1-CU3);
      `player_creation.py`, `player_shell.py`, `single_canon_write.py`,
      `npc_skills.py`, `skill_progression.py`, `rank_trials.py`,
      `frontend_build_fresh.py`, `module_budget.py`, `claude_md_contract.py`
      PASS.
- [ ] Named mutations, each red then reverted: `locked` back to `!==
      'draft'` -> CU2; drop the `PROFILE_CREATING` test -> CR6; render the
      field on the `npc` tab too (drop the `characterType` test) -> CU3.
- [ ] `corpus_gate.py` PASS.
- [ ] Live: the ticket's live criteria 4-6 behave as written.
- [ ] `/review-step` then `/close-step` (DECISIONS_INDEX regenerated).

## Docs to update

- ARCHITECTURE_DECISIONS (Scope IN 10). No schema change. After the
  merge, Nia runs `python scripts/migrate_v2_33_creator_review.py` after a
  backup.
