<!-- slug: screens-and-docs -->
# BRIEF 0127-E — "The Lore panel « Un personnage », the player's « Mes savoirs », the invariants and the decision entry"

Lot: LOT-0127-character-perspective.md (authoritative on conflict)
Depends on: BRIEF-0127-D (C-13's routes)

## Anchors to confirm (Mini-RECON)

- `frontend/src/lore/PerspectivePanel.svelte`: `REASON_LABEL` (:13-19)
  holds five keys; `:47` is `<option value="public">Public — ce que tout le
  monde sait</option>`; `:71` `<h3>Ce que voit le joueur</h3>`.
- `frontend/src/lore/perspective.svelte.js:14` opens `perspectiveState`
  with `perspective: 'public',`; `:92` is `export function
  resetPerspectiveForWorld() {`.
- `frontend/src/joueur/WorldPage.svelte:39` is `<h2>Ce que tout le monde
  sait</h2>`.
- `frontend/src/joueur/joueur.svelte.js:121` is `export function
  openWorld(w) {`, `:134` posts `/api/joueur/savoir/ask`, `:165` posts
  `/api/joueur/savoir/resolve`.
- `CLAUDE.md:133-141` is INV-01 as R-13 quotes it;
  `.claude/rules/player-surface.md:21-32` is INV-66, ending «
  `player_shell.py`, `creation_designer.py`, `player_creation.py` ».
- `tooling/standards/ARCHITECTURE_DECISIONS.md` ends with `---`, a blank
  line, `*Co-built with Claude, June 2026.*`.
- `GET /api/lore/perspective/characters`, `GET /api/joueur/personnage` and
  `POST /api/joueur/personnage/savoir/ask|resolve` exist (D);
  `character_perspective.py` passes CP1-CP7.

Halt if any anchor has moved.

## Facts carried

### R-13 -- creator-only facts and the holder's own secrets
Opened: `src/world_engine/facet_reads.py:58-63`;
`src/world_engine/tick_context.py:125-133`; `CLAUDE.md:133-141` (INV-01).
Finding: `creator_only_fact_ids(db, fact_ids) -> set[str]`, one query.
`tick_context._knowledge_line` renders an NPC's own `is_secret` rows into
that NPC's own context, prefixed `[SECRET] ` -- the precedent C1 follows.
INV-01 reads « excluded at every assembler AND every propagation path ».
Consequence: C1 (the creator's door shows the holder's own secrets) is
written into INV-01 by E; the player's door drops them by construction
(C-03 step 3).
### R-22 -- the checks of the perspective, the player's door and the shell
Opened: `tooling/verify/checks/perspective_isolation.py:1-80, 108-153, 182-270`;
`player_routes.py:1-70, 74-165, 308-358`; `player_shell.py:1-40, 80-100`;
`name_index.py:1-40, 285-310`; `creation_designer.py:14-24, 228-250`;
`knowledge_identity.py:31-34, 125-131, 842-863`.
Finding: PI1 (`MODULES` :70; `FORBIDDEN` :71-72 holds `chat(`, `db.add(`,
`.commit(`, `include_creator_only`, `CREATOR`, `NameScope("creator"`,
`near_candidates`, `validate_binding`; `CREATOR_SELECTORS` :73);
`FORBIDDEN_KEYS = {"is_secret", "is_incorrect", "intensity", "internal_name",
"knowers", "creator_only", "level"}` (:74); PI2 (:137-152) requires five
public names and the three tables in their order; PI3 the verdict literals;
PI4 builds the world `_build_world(engine)` (:182-255: Hero, Shade
(non-public), Guild, Guild2, Cabal (non-public), two public Twins; F1-F7;
Hero in Guild, Cabal and secretly Guild2; one law) and plans with
`_plan(selector, *, mention=None, text=None)` (:258-265). player_routes:
harness `_fresh_engine` (:74), `_seed_prompts(db)` (:91), `_Stub(replies)`
with `.messages` (:113-122), `_swap(module, stub)` (:125-128), `_events`
(:131), `_all_events` (:140), `_attempt(n)` (:149), `_one` (:153);
`PLAYER_KEYS`, `CREATOR_KEYS` (:58-59); PR8 (:320-358): `lore_perspective.py`
and `perspective_flow.py` hold no `chat(` nor `select(`, `player.py` no
`chat(` and `select(` naming only `User`, `World`, `WorldLaw`, none holds
`World.is_active`, `_world_id(`, `write_usage_event`, `lore_selectors`, and
every route path of `player.py` starts `/api/joueur/`. player_shell PSH1
requires five French reason labels in `PerspectivePanel.svelte`; PSH2 every
URL literal under `frontend/src/joueur/` starts `/api/joueur/`; PSH3 no
import out of that folder; PSH5 a built asset carries a creation string.
knowledge_identity K3 pins one `subject` reference in `perspective_audit.py`.
Consequence: each brief names which of these it must keep green or extend;
CP (the new check, C-15) imports `_build_world`, `_plan` and the harness of
`player_routes.py` rather than copying them.
### R-23 -- the frontend surfaces
Opened: `frontend/src/lore/PerspectivePanel.svelte:1-143`;
`frontend/src/lore/perspective.svelte.js:1-101`; `frontend/src/lore/Lore.svelte:24,
110, 118-119`; `frontend/src/joueur/WorldPage.svelte:1-90`;
`frontend/src/joueur/joueur.svelte.js:1-179`;
`frontend/src/joueur/character.svelte.js:112-123`;
`src/world_engine/cockpit/routes/player_creation.py:183-197`;
`src/world_engine/cockpit/crud/entities.py:522-531`; `.claude/rules/frontend.md`.
Finding: the panel's `REASON_LABEL` (:13-19) holds five reasons
(`skill_not_visible` has none); the perspective `<select>` (:44-49) one option
`public`; the answer heading is « Ce que voit le joueur » (:71); the state
(:14-22) holds `perspective, question, asking, error, result, selections,
attemptId`; the ask body (:38-43) and resolve body (:74-81) send
`perspective`; `resetPerspectiveForWorld` (:92-101). `WorldPage.svelte`'s
section « Ce que tout le monde sait » (:38-78) calls `askSavoir`,
`selectSavoirCandidate`, `allSavoirChoicesMade`, `confirmSavoir`.
`joueur.svelte.js`: state (:12-23), `clearQuestion` (:56), `openWorld`
(:121-125), `askSavoir` (:127-147, `/api/joueur/savoir/ask`), `confirmSavoir`
(:159-179, `/resolve`). The player sees an accepted character only through
`character_name` of `GET /api/joueur/creation/brouillon`. `GET /api/entities`
reads the active world and returns no `character_type`. Every frontend edit
is rebuilt and the build under `src/world_engine/cockpit/static/` committed.
Consequence: E reads the characters through a perspective route (C-13) and
the player's character through `GET /api/joueur/personnage` (C-13).
### R-24 -- budgets
Opened: `tooling/verify/checks/module_budget.py:58-59`;
`tooling/verify/checks/claude_md_contract.py:77-80, 132-138`; `wc -l`/`wc -c`.
Finding: 40 top-level functions and 1000 lines per module (frontend 1000
lines). Today: `perspective_selectors.py` 338, `perspective_audit.py` 137,
`perspective_query.py` 122, `perspective_render.py` 42, `perspective_flow.py`
113, `lore_perspective.py` 62, `player.py` 129, `lore_render.py` 350,
`name_index.py` 175, `PerspectivePanel.svelte` 143, `joueur.svelte.js` 179.
`CLAUDE.md` 20 895 of 22 000 characters; `.claude/rules/player-surface.md`
body 1 038 of 4 000; no line over 100 characters.
Consequence: no extraction is needed; E's amendments fit the budgets.
### R-26 -- the generated maps and the decisions file
Opened: `tooling/standards/FILE_MAP.md:1-8, 231-234, 286, 334, 547-554`;
`tooling/standards/DECISIONS_INDEX.md:1-3`; `tooling/glue/gen_file_map.py:36`;
`tail -5 tooling/standards/ARCHITECTURE_DECISIONS.md`.
Finding: `FILE_MAP.md` is generated by `python tooling/glue/gen_file_map.py`
from the first docstring sentence of every module of `scripts/`, `src/` and
`tooling/` (checks included); `file_map.py` fails when it is stale.
`DECISIONS_INDEX.md` is generated by `python tooling/glue/gen_decisions_index.py`.
`ARCHITECTURE_DECISIONS.md` ends with `---` / blank / `*Co-built with
Claude, June 2026.*`; the last entry is `## TICKET-0130 -- ...` (:20921).
Consequence: every brief that adds a module or changes a first sentence
regenerates `FILE_MAP.md`; E inserts the decision entry above the footer and
regenerates `DECISIONS_INDEX.md`.

## Contracts

### C-10 -- the audit over a view
Produced by: BRIEF-0127-D   Consumed by: BRIEF-0127-D (flow), E (panel labels)
In `perspective_audit.py`:
- `WITHHELD_REASONS` = today's six, then `"not_known", "entity_unknown",
  "membership_unknown", "skill_unknown", "false_belief", "stale_version",
  "concealed"`.
- `withheld_for(plan, view, db, bindings=None) -> list[dict]`;
  `withheld(plan, world_id, db, bindings=None)` returns `withheld_for(plan,
  public_view(db, world_id), db, bindings)`.
- A public view: exactly today's lines.
- A character view, per call (`subject` = the dossier entity's name or the
  searched text, `content` as below):
  | call | line | reason | content |
  |---|---|---|---|
  | `known_dossier` on E not in `view.entity_ids` (E matched under `NAMES_ONLY`) | one | `entity_unknown` | E's name |
  | `known_dossier` / `known_facts_mentioning`: a fact not in `view.fact_ids` | per fact | `creator_only` if creator-only; else `concealed` if `view.door == "player"` and the holder's stored row on it is `is_secret` and not `unaware`; else `not_known` | the fact's current text |
  | same, a fact in `view.fact_ids` whose belief is `incorrect` | per fact | `false_belief` | the fact's current text |
  | same, a fact in the view, belief `text is None`, `fact_is_stale(fact, as_of)` | per fact | `stale_version` | the fact's current text |
  | `known_dossier`: a secret membership of E, or a secret member of faction E | per row | `secret_membership` | `_membership_line(...)` |
  | `known_dossier`: a non-secret membership or member failing rule M | per row | `membership_unknown` | `_membership_line(...)` |
  | `known_factions`: an active faction not in `view.entity_ids` | per faction | `entity_unknown` | its name |
  | `known_skills`: a definition not in `view.skill_ids` | per definition | `skill_unknown` | its name |
  | `world_laws`, `self_sheet` | none | -- | -- |
  The dossier's facts are those of C-06 member 1 (participants, events,
  liens); `known_facts_mentioning` audits `_facts_matching` on current texts.
- Rows `{reason, subject, content}` sorted as today, through the module's one
  existing dict line (R-25).
Error and empty cases: `[]` for an invalid plan or an ambiguous mention.

### C-13 -- the routes
Produced by: BRIEF-0127-D   Consumed by: BRIEF-0127-E
Creator, `cockpit/routes/lore_perspective.py`:
- both bodies gain `character_id: Optional[str] = None`;
- `_check_perspective(perspective, character_id)`: accepted only `("public",
  None)` and `("character", <non-empty>)`; otherwise 422
  `UNKNOWN_PERSPECTIVE_MESSAGE`, before any journal row;
- ask / resolve pass `character_id=body.character_id, door="creator"`;
- `GET /api/lore/perspective/characters?world_id=<id>` ->
  `perspective_view.world_characters(db, world_id)`.
Player, `cockpit/routes/player.py`:
- `CHARACTER_NOT_FOUND = "Personnage introuvable."`;
- `GET /api/joueur/personnage?profile_id=&world_id=` -> `_open_world`,
  `_player_profile`, then `{"character_id": id, "name": name}` from
  `player_character_of`, or `{"character_id": None, "name": None}`;
- `CharacterSavoirAskBody(profile_id, world_id, character_id, question,
  attempt_id=None)`, `CharacterSavoirResolveBody(profile_id, world_id,
  character_id, plan, bindings, question, attempt_id=None)`;
- `_own_character(profile_id, world_id, character_id, db)`: 404
  `CHARACTER_NOT_FOUND` unless `player_character_of(...)` names that id;
- `POST /api/joueur/personnage/savoir/ask` and `/resolve`: `_open_world`,
  `_player_profile`, `_own_character` (none journals), then the flow with
  `character_id`, `door="player"`, `asked_by=f"player:{profile_id}"`; the
  answer through `_player_answer`.
Neither module gains a `select(` (PR8).
Error and empty cases: as stated.

### C-14 -- the two screens
Produced by: BRIEF-0127-E   Consumed by: the live gate
Lore (`frontend/src/lore/`):
- `perspectiveState` gains `characterId: ''` and `characters: []`;
  `loadPerspectiveCharacters()` reads `GET
  /api/lore/perspective/characters?world_id=<serverState.worldId>`; the ask
  and resolve bodies send `character_id: perspectiveState.perspective ===
  'character' ? perspectiveState.characterId : null`;
  `resetPerspectiveForWorld` also empties `characterId` and `characters`.
- `PerspectivePanel.svelte`: a second option `<option value="character">Un
  personnage — ce qu'il sait</option>`; when chosen, a character `<select>`
  with `<optgroup label="Personnages joueurs">` (type `player`) and
  `<optgroup label="PNJ">`; « Interroger » disabled until a character is
  chosen; the answer heading reads « Ce que voit le joueur » for public and
  « Ce que sait <name> » for a character; `REASON_LABEL` gains
  `skill_not_visible: 'compétence invisible à la création'`, `not_known:
  'inconnu de ce personnage'`, `entity_unknown: 'entité inconnue de ce
  personnage'`, `membership_unknown: 'appartenance inconnue de ce
  personnage'`, `skill_unknown: 'compétence inconnue de ce personnage'`,
  `false_belief: 'croyance fausse — la vérité'`, `stale_version: 'version
  périmée — le texte actuel'`, `concealed: 'su mais caché (porte joueur)'`.
Player (`frontend/src/joueur/`):
- `joueurState` gains `character: null`; `loadCharacter()` reads `GET
  /api/joueur/personnage?profile_id=<id>&world_id=<id>` and sets
  `character` to `{id, name}` or `null`; `openWorld(w)` calls it when `w`
  is set;
- `askSavoir` / `confirmSavoir` post to `/api/joueur/personnage/savoir/ask`
  / `/resolve` with `character_id` when `joueurState.character`, else to
  today's public routes;
- `WorldPage.svelte`'s section heading reads « Mes savoirs — <name> » when
  `joueurState.character`, else « Ce que tout le monde sait »; the rest of
  the section is unchanged.
Rebuilt; the build committed.

### C-15 -- the check `character_perspective.py` (family)
Produced by: BRIEF-0127-B (CP1-CP3), C (CP4-CP5), D (CP6-CP7)
Consumed by: the ticket's acceptance arrows; fixture writers: R-28
`tooling/verify/checks/character_perspective.py`, first docstring sentence:
« G1 check for TICKET-0127 -- a character's perspective answers only what he
knows, keeps a secret from the player's door, and journals every question. »
Fresh temp-file SQLite (`WORLD_ENGINE_DATABASE_URL` set before any
`world_engine` import, as `player_routes._fresh_engine`); never Nia's DB; a
rule that collected nothing is a FAILURE; exit 1 on any failure.
Fixture `_extend(engine, ids)` on top of `perspective_isolation._build_world`
(imported), through sanctioned writers, in this order:
1. entities (non-public unless said): `mira` « Mira » NPC; `vex` « Vex » NPC;
   `twin3` « Twin » NPC; `ordre` « Ordre » faction; `lune` « Lune » player
   character with `user_id` = a profile « Ana » (`create_player_profile`),
   and a second profile « Bo »; the world `open_to_players = True`;
2. `F8` « Shade porte un masque » (`description`, participant Shade), a
   `rencontre` default on Shade at `knows`; `record_encounter(mira, shade,
   source="relation")`; then `update_fact_content(F8, "Shade a ote son
   masque", kind="changement")`;
3. knowledge (`write_knowledge(db, entity_id=..., fact_id=..., level=...)`,
   its default mode, which inserts): Mira on F7 `rumor`,
   `is_secret=True`; Mira on F2 `knows`, content « Hero fut affranchi »,
   `is_incorrect=True`; Lune on F7 `rumor`, `is_secret=True` (a deliberate
   breach of INV-07: the player's door must hold even so);
4. Mira's membership in Cabal, not secret (`write_membership`);
5. `F9` « Vex vend des secrets » (`description`, participant Vex, no default);
6. an event type « Fait » (role « qui », characters and factions); `E1`
   « Le sacre de Hero » (Hero, scope world `knows`); `E2` « La fuite de
   Shade » (Shade and Mira, no scope);
7. `SkillDefinition` « Ombre » (`perception`, `visible_at_creation=False`,
   no system); Mira's `Skill` rows: `agility` rank 2, `perception` rank 1 on
   Ombre; `SkillDefinition` « Lame » (`agility`, `visible_at_creation=False`,
   no system), held by nobody;
8. `F10` « Hero cache une dague » (`information`, participant Hero, no
   default); Shade's membership in Guild, not secret.
Rules (exact sets; R-27 measured them):
- CP1 (B, static): `perspective_view.py` holds none of
  `perspective_isolation.FORBIDDEN` and imports none of its
  `CREATOR_SELECTORS`.
- CP2 (B): `character_view(db, wid, mira, door="creator")`: `fact_ids ==
  {F1, F2, F4, F5, F6, F7, F8, E1, E2}`; `entity_ids == {hero, guild,
  guild2, twin1, twin2, mira, shade, cabal}`; `skill_ids == {ombre}`;
  `member_of == {cabal}`; `beliefs[F2]` text « Hero fut affranchi »,
  `incorrect`; `beliefs[F7]` certainty « rumeur », `secret`, text `None`;
  `beliefs[F8]` text `None`, `fact_is_stale(F8, as_of)`; `beliefs[F1].as_of
  is None`; `set(beliefs) == fact_ids`. `door="player"`: the same minus F7.
  `character_view` on `ordre` (a faction), on an unknown id, and on `mira`
  under the world id `"no-world"` raise `UnknownCharacter`; `door="x"`
  raises `ValueError`.
  `public_view(db, wid)` has the defaults of C-02.
- CP3 (B): the names of `surfaces(db, wid, NameScope("character",
  known_fact_ids=v.fact_ids, entity_ids=v.entity_ids))` (Mira's creator view
  `v`) belong exactly to `v.entity_ids`; `resolve_named("Twin", "person",
  ...)` under it is `ambiguous` with exactly `{twin1, twin2}`; « Vex » is
  `unmatched`; `NameScope("character", known_fact_ids=frozenset())` and
  `NameScope("public", known_fact_ids=frozenset(), entity_ids=frozenset())`
  raise `ValueError`.
- CP4 (C): selectors on Mira's creator view (labels from `FACETS`):
  `known_dossier(hero)` facets `{(Description, « Hero porte une cape
  rouge », False, None), (Histoire, « Hero fut affranchi », False, None),
  (Événement, « Le sacre de Hero », False, None), (Lien, F5's text, False,
  None)}` as `(label, content, secret, certainty)`; memberships `{Guild,
  Cabal}`; `known_dossier(shade)` facets contents `{« Shade est une ombre »,
  « Shade creuse un tunnel », « Shade porte un masque », « La fuite de
  Shade »}`; `known_dossier(cabal)` members `{Hero, Mira}`;
  `known_dossier(vex)` and `(ordre)` are `[]`; `known_factions` names
  `[Cabal, Guild, Guild2]`; `known_facts_mentioning("tunnel")` is `[(« Le
  tunnel cache un tresor », [], True, « rumeur »), (« Shade creuse un
  tunnel », [Shade], False, None)]` as `(content, participants, secret,
  certainty)`, and on the player's view only the second; `self_sheet`
  acquaintances `[(Shade, character)]`, own_skills `[(agility, agility,
  None, Apprenti), (Ombre, perception, None, Initié)]`; `known_skills` names
  `[Ombre]`. On `public_view`: `known_dossier(hero)` facets contents `{F1,
  « Le sacre de Hero », F5}`, memberships `{Guild}`; `self_sheet` is `[]`.
  No row of any call holds a key of `FORBIDDEN_KEYS`.
- CP5 (C): `lore_render._serialize_rows_by_section` over the tunnel rows
  holds `« Le tunnel cache un tresor » (certitude : rumeur) [secret]` and
  `« Shade creuse un tunnel » -- Shade`; over `self_sheet`'s rows `Shade
  (character)` and `agility (sans système, agility) : Apprenti`; over
  public `known_dossier(hero)` the F1 line `Description : Hero porte une cape
  rouge` with no suffix.
- CP6 (D): executor and audit on Mira's views (`_plan` of
  `perspective_isolation`): `known_dossier` « Hero » answered with C-06's
  rows; « Vex » `nothing_known`; « Twin » `ambiguous_mention` with exactly
  the two public Twins; a binding to `twin3` raises `BindingRefused`;
  `_plan("self_sheet")` on `public_view` is `unsupported_selector`.
  `withheld_for` as `(reason, subject, content)`: « Hero », creator door ->
  `{(creator_only, Hero, « Hero trahira la guilde »), (false_belief, Hero,
  « Hero fut esclave »), (not_known, Hero, « Hero cache une dague »),
  (secret_membership, Hero, « Guild2 (-) »)}`; « Shade » ->
  `{(stale_version, Shade, « Shade a ote son masque »), (membership_unknown,
  Shade, « Guild (-) »)}`;
  `text:tunnel` creator door -> `[]`, player door -> `{(concealed, tunnel,
  « Le tunnel cache un tresor »)}`; `known_factions` -> `{(entity_unknown,
  Ordre, Ordre)}`; « Vex » -> `{(entity_unknown, Vex, Vex)}`; `known_skills`
  -> `{(skill_unknown, Lame, Lame)}`, and on `public_view`
  `{(skill_not_visible, Lame, Lame), (skill_not_visible, Ombre, Ombre)}`.
  `withheld` (public) of « Hero » is PI4g's four lines plus `(not_public,
  Hero, « Hero cache une dague »)`.
  `render_perspective(nothing_known, ..., nom="Mira")` prose is « Rien de ce
  que Mira sait ne répond à cette question. ».
- CP7 (D, TestClient, `player_routes` harness imported: `_seed_prompts`,
  `_Stub`, `_swap`, `_events`, `_all_events`, `_attempt`): (a) `GET
  /api/lore/perspective/characters` lists Lune first, then Hero, Mira,
  Shade, Twin, Twin, Twin, Vex, keys exactly `{id, name, character_type}`; (b)
  `perspective "character"` without `character_id`, `"public"` with one, and
  an unknown id -> 422 (`Perspective inconnue.` / `Personnage inconnu.`), no
  journal row; (c) creator ask as Mira, plan `known_facts_mentioning`
  « tunnel » -> 200 with `CREATOR_KEYS`, the render stub's user message holds
  « Le tunnel cache un tresor » and `[secret]`, one row `perspective_ask/ok`
  with `perspective "character"`, `character_id` Mira, `asked_by "creator"`;
  (d) `GET /api/joueur/personnage` -> `{character_id: lune, name: "Lune"}`
  for Ana, both `None` for Bo; (e) Ana asks as Lune, same plan -> 200 with
  `PLAYER_KEYS`, the render stub's user message does NOT hold « Le tunnel
  cache un tresor », the journal row's `withheld` holds `(concealed, tunnel,
  « Le tunnel cache un tresor »)` and `character_id` Lune, `asked_by
  "player:<ana>"`; (f) Bo asks with Lune's id -> 404 `Personnage
  introuvable.`, no row; (g) resolve as Lune, plan « Twin » bound to `twin3`
  -> 422 `Choix refusé.`, one `perspective_resolve/refused` row.
Named mutations (each must turn the named rule red): drop the creator-only
subtraction of `character_view` -> CP2; drop its player-door `is_secret`
filter -> CP2 and CP7e; drop the `character` condition of `surfaces` -> CP3;
drop rule M's `member_of` branch -> CP4; return `public_view` from the flow
for a character -> CP7c.

## Context

The doors exist (D). This brief puts them on screen -- Lore's Perspective
tab gains « Un personnage » (I1), the player's world page gains « Mes
savoirs » (G1) -- and writes the law: INV-01 admits the holder's own view at
the creator's door, INV-66 admits the player's own character's view.

## Scope IN

1. `frontend/src/lore/perspective.svelte.js` per C-14.
2. `frontend/src/lore/PerspectivePanel.svelte` per C-14; it calls
   `loadPerspectiveCharacters()` when « Un personnage » is chosen and the
   list is empty. Its header comment names TICKET-0127 (I1).
3. `frontend/src/joueur/joueur.svelte.js` per C-14 (`clearQuestion` leaves
   `character` alone; `openWorld(null)` sets it to `null`).
4. `frontend/src/joueur/WorldPage.svelte` per C-14.
5. Rebuild (`cd frontend`, `npm run build`); commit the build under
   `src/world_engine/cockpit/static/`.
6. `tooling/verify/checks/player_shell.py`: rule PSH6 (static) --
   `perspective.svelte.js` holds `/api/lore/perspective/characters` and
   `character_id`; `PerspectivePanel.svelte` holds `Un personnage`,
   `Personnages joueurs`, `PNJ`, `Ce que sait` and the eight labels of C-14;
   `joueur.svelte.js` holds `/api/joueur/personnage/savoir/ask`,
   `/api/joueur/personnage/savoir/resolve` and `/api/joueur/personnage?`;
   `WorldPage.svelte` holds `Mes savoirs`; a built asset under
   `src/world_engine/cockpit/static/assets` carries `Mes savoirs`. The
   docstring gains PSH6's paragraph.
7. `CLAUDE.md`, INV-01: the sentence « What an NPC knows but conceals ...
   from one). » becomes, verbatim (wrapped at the file's width, no line
   over 100 characters):
   « What an NPC knows but conceals is a `knowledge` row with `is_secret =
   TRUE`, excluded at every assembler AND every propagation path
   (`analyze_overhearing` never sources a proposal from one), but for its
   holder's own view: the tick, and the holder's perspective at the
   creator's door (`perspective_view.character_view`); the player's door
   drops it. »
8. `.claude/rules/player-surface.md`, INV-66: the first sentence becomes,
   verbatim: « A player surface learns about the world only through a
   perspective view (`perspective_selectors` over `public_view`, or over
   `perspective_view.character_view` of its own character at the player's
   door; `perspective_query` for a planned question), never a creator
   selector, the creator name regime, a trace, near names or the audit. »;
   « A skill is in that view only when » becomes « A skill is in the public
   view only when »; the sentence on `faction_membership` ends « ... keyed
   by faction (a third sanctioned reader, INV-03); a character's own
   factions come through `read_public_membership_faction_ids`. »; the
   enforced-by list gains `character_perspective.py`.
9. `tooling/standards/ARCHITECTURE_DECISIONS.md`: one entry inserted above
   the footer (`---` / `*Co-built ...*`), never appended after it:
   `## TICKET-0127 -- a character's perspective (BRIEF-0127-a,
   BRIEF-0127-b, BRIEF-0127-c, BRIEF-0127-d, BRIEF-0127-e, no schema
   change)`, then one short paragraph per locked code of the ticket (A1, B1,
   C1, D1/D1-a, E1, F1, G1, H1, I1), each with its rejected alternative and
   reactivation condition as the ticket states them.
10. Regenerate `DECISIONS_INDEX.md` (`python
    tooling/glue/gen_decisions_index.py`) and `FILE_MAP.md`.
11. Commits: (a) « TICKET-0127 E: Lore > Perspective asks as a character
    (I1) »; (b) « TICKET-0127 E: « Mes savoirs » in /jouer (G1); rebuilt »;
    (c) « TICKET-0127 E: player_shell PSH6 »; (d) « TICKET-0127 E: INV-01,
    INV-66, the decision entry; DECISIONS_INDEX and FILE_MAP
    regenerated ».

## Scope OUT

- Any backend change (D is done); a new route.
- Re-reading the player's character while the page stays open (ticket,
  « Carried forward »).
- A link from `/jouer` to anything else (B1 of TICKET-0130).
- The « PJ actif » selector (TICKET-0128).
- A per-character metric in « Suivi » (H2, rejected).

## Invariants to defend

- INV-66 / PSH2-PSH3: every URL under `frontend/src/joueur/` starts
  `/api/joueur/`; no import leaves that folder.
- INV-55 (`.claude/rules/frontend.md`): inside a `$effect`, a `$state`
  binding assigned there is never read afterwards in the same body --
  `loadPerspectiveCharacters` is called from an event handler, not from the
  reset effect.
- The CLAUDE.md contract: no line over 100 characters, the root under 22 000
  characters, the rule file under 4 000, no `TICKET-` or `BRIEF-` id inside
  an Invariants section (R-24).

## Decision rights

STOP:
- An anchor does not hold.
- `claude_md_contract.py` turns red on the verbatim text of items 7-8 (a
  budget or a banned token): report the message; never shorten the law on
  your own.

ADAPT:
- `npm ci` is needed before the build: run it, report.
- PSH1's five labels move in the file: keep them, report.

REPORT-ONLY:
- Visual polish of the two screens beyond C-14.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] PASS: `player_shell.py` (PSH1-PSH6), `character_perspective.py`,
      `perspective_isolation.py`, `player_routes.py`,
      `frontend_build_fresh.py`, `static_asset_freshness.py`,
      `effect_self_write.py`, `claude_md_contract.py`, `file_map.py`,
      `module_budget.py`.
- [ ] Named mutation, red then reverted: post the player's ask to
      `/api/joueur/savoir/ask` while a character is set (remove the
      `/api/joueur/personnage/savoir/ask` literal) -> PSH6 red.
- [ ] `corpus_gate.py` green (paste the summary line).
- [ ] The decision entry sits above the footer (`tail -4` pasted).
- [ ] /review-step and /close-step run.

## Docs to update

This step IS the doc update: INV-01, INV-66, the decision entry,
DECISIONS_INDEX and FILE_MAP regenerated.
