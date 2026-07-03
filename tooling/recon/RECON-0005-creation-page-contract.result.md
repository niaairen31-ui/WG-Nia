# RECON-0005 result — Création sub-tab layout map

Ticket: TICKET-0005. Report-only — no code touched. All citations verified
against the live tree (`src/world_engine/cockpit/index.html`, `app.py`,
`crud.py`) as of this recon; several were spot-checked directly in addition
to the exploring pass.

**Correction to the RECON spec's framing, surfaced up front:** the spec's
question list and the ticket's open decision D both frame the tab set as
*seven* (NPC, Personnage joueur, Lieux, Factions, Objets, Artefacts, Review
Queue). The live tab bar (`index.html:1152-1161`) has **ten** buttons: NPC,
Personnage joueur, Lieux, Factions, Objets, **Compétences**, **Région**,
Artefacts, **Registre**, Review Queue. Compétences, Région, and Registre are
real Création sub-tabs with their own render paths (question 1) and are not
generic-entity pages. Decision D (contract perimeter) needs to explicitly
place these three, not just implicitly exclude them. See "Surprises" below.

## 1. Rendering reality

All sub-tabs live in one file, `index.html`, switched by one dispatcher:
`showCreationSubTab(tab)` (`index.html:2961-3026`), which shows/hides one of
several fixed containers and calls a tab-specific loader.

- **NPC / Lieux / Factions / Objets** (`isEditorTab`, `index.html:2969`):
  share container `#creation-editor-area` (`index.html:1180`). Sidebar list:
  `authorLoadEntityList()` (`index.html:3930`) -> `creationRenderEntityList()`
  (`index.html:3781`, routes to `renderLieuxBrowse()` for Lieux,
  `index.html:3872`, or the flat list otherwise, `index.html:3809-3815`).
  Detail/edit panel: `authorRenderSheet(detail, isNew, type)`
  (`index.html:4024`), injected into `#author-main`.
- **Personnage joueur (PJ)**: same editor-area list/detail as above (filtered
  to `playerCharIds`), PLUS a second static block, `#creation-pj-skill`
  (`index.html:1208`, shown only when `tab==='pj'`, `index.html:2978-2979`)
  containing the skill Fiche, initialized by `skillInit()`
  (`index.html:5281` — exact def line approximate, called `index.html:3012`)
  -> `skillLoadCharacters()` (`index.html:5426`).
- **Lieux** additionally shows `#creation-lieux-graph`
  (`index.html:1165`, shown only when `tab==='lieux'`, `index.html:2976`),
  loaded by `graphLoad()` (`index.html:5680`).
- **Compétences**: own static container `#creation-competences`
  (`index.html:1291`), loader `competencesLoadList()` (`index.html:3132`) ->
  `_competencesRenderTable()` (`index.html:3143`). No entity list/detail
  pattern — inline-editable rows.
- **Région**: own container `#creation-region`, loader `regionRenderAll()`
  (`index.html:3022` call site; render fn `index.html:3696`) — a
  manifest/tree flow, not list+detail.
- **Artefacts**: own static container `#creation-artefacts`
  (`index.html:1281`), loader `loadCreationArtefacts()` (`index.html:3312`) —
  fetch-and-render only, no selection.
- **Registre**: own static container `#creation-registre`
  (`index.html:1325`), loader `loadRegistre()` (`index.html:3274`) ->
  `_registreRenderTable()` (`index.html:3293`).
- **Review Queue**: own static container `#creation-queue`
  (`index.html:1375`), loader `loadQueue()` (`index.html:2489`) ->
  `renderCard()` per mutation (`index.html:2565`).

One dispatcher, but effectively three distinct rendering archetypes today:
(a) entity list+detail via `authorRenderSheet` (NPC/PJ/Lieux/Factions/Objets),
(b) inline-editable-row catalogues (Compétences, and Registre's read-only
variant), (c) bespoke flows (PJ Fiche, Région, Artefacts, Review Queue).

## 2. "+ Nouveau" inventory

- **NPC / Factions / Objets**: shared button `#creation-new-btn`
  (`index.html:1183`, inside `#creation-new-row`, top of sidebar) ->
  `onclick="creationNewEntity()"` (`index.html:3753`) -> routes by
  `currentCreationSubTab` -> `authorRenderSheet({}, true, type)`. Opens
  inline in `#author-main`, includes the AI generate panel
  (`authorRenderGeneratePanel()`, `index.html:4170`) for NPC/Lieux/Factions.
- **Lieux**: same `creationNewEntity()` path, but the button is a second
  "Ajouter un lieu" control inside the graph panel header
  (`index.html:1169`), not `#creation-new-btn` — a positional divergence
  from NPC/Factions/Objets even though the handler is identical.
- **Personnage joueur**: separate button `#pj-create-new-btn`
  (`index.html:1215`), inside `#creation-pj-skill`, NOT `#creation-new-row`
  (`index.html:1182` shows `#creation-new-row` is hidden for `tab==='pj'`,
  `index.html:2982`). Handler `pjCreateNew()` (`index.html:5378`) toggles a
  collapsed block `#pj-create-block` (`index.html:1217`) — inline expand,
  not a modal, not `authorRenderSheet`. Own AI-draft control
  (`pcGenerateDraft()`, `index.html:5396`) and own minimal form
  (name + location + description/appearance/backstory,
  `index.html:1233-1256`).
- **Compétences**: "+ Ajouter une compétence" (`index.html:1312-1314`) pushes
  a blank row onto the draft list client-side — no panel/modal at all.
- **Artefacts / Review Queue**: no create control. Artefacts: explicit static
  notice "arriveront dans une étape ultérieure" (`index.html:1282-1283`) —
  backend support pending. Review Queue: append-only by design, rows
  originate from Play-side proposals, never created here.
- **Registre**: has an "add entry" form (`index.html:1339-1370`,
  `authorAddLedgerEntry()` per `index.html:3240`) but it is not a "+
  Nouveau" — always-visible inline form, not a toggled/modal create
  affordance, and it's a ledger append, not an entity create.
- **Région**: creation happens through the brief -> manifest -> draft ->
  commit flow, not a "+ Nouveau" button.

Three distinct "create" idioms already exist for what the ticket wants
unified: (i) inline panel via `authorRenderSheet` (NPC/Lieux/Factions/Objets),
(ii) collapsed block with dedicated form + dedicated endpoint (PJ), (iii)
no control / non-applicable (Artefacts, Review Queue, Compétences' inline
add-row, Registre's always-open form, Région's multi-step flow).

## 3. List -> detail binding

- **NPC / Factions / Objets**: click `.author-list-item`
  (`onclick="authorSelectEntity('${e.id}')"`, `index.html:3811`) ->
  `authorSelectEntity(id)` (`index.html:4939`) -> `GET /api/entities/{id}`
  (`index.html:4942`) -> `authorRenderSheet(detail, false, detail.type)`
  (`index.html:4943`). Fully dynamic, driven by the clicked id.
- **Lieux**: same `authorSelectEntity()` call
  (`index.html:3918`, inside `renderLieuxBrowse()`'s row markup), plus
  separate hierarchy navigation (`lieuxDescend()` `index.html:3852`,
  `lieuxJumpTo()`) that changes the browse root, not the detail panel.
- **Personnage joueur — the ticket's stated assumption does not hold.**
  Verified directly at `index.html:5439-5443`
  (`skillLoadCharacters()`): `skillCharacters[0].id` is used **only as a
  fallback** when `skillCharacterId` is unset or stale
  (`if (!skillCharacterId || !skillCharacters.some(c => c.id ===
  skillCharacterId)) { skillCharacterId = skillCharacters[0].id; }`). The
  live binding is the dropdown (`#skill-character-select`,
  `onchange="skillSelectCharacter(this.value)"`, `index.html:1266`) and,
  critically, `authorSelectEntity()` itself already wires list-click to the
  Fiche for this tab — verified directly at `index.html:4945-4949`:
  ```
  if (currentCreationSubTab === 'pj') {
    const sel = document.getElementById('skill-character-select');
    if (sel) sel.value = id;
    skillSelectCharacter(id);
  }
  ```
  So list-selection -> Fiche rewiring (open decision E's stated concern) is
  **already implemented** for the one case that exists today. There is no
  `skillCharacters[0]`-as-primary-binding to fix. Open decision E should be
  reframed: the question is whether a *generic* list-selection -> slot-data
  contract can absorb this existing ad hoc wiring, not whether a hardcoded
  first-element bug needs fixing.
- **Compétences / Registre / Review Queue / Artefacts**: no list-to-detail
  panel exists — see question 1/8. Registre and Review Queue instead filter
  by status/entity (not per-row selection); Compétences edits happen inline
  per row; Artefacts has no interaction at all.

## 4. Endpoint map

| Tab | List | Create | Update | Notes |
|---|---|---|---|---|
| NPC | `GET /api/entities` (`index.html:3935`; `crud.py:516`) | `POST /api/entities` (`index.html:5002`; `crud.py:621`) | `PUT /api/entities/{id}` (`index.html:5003`; `crud.py:648`) | generic entity CRUD |
| Factions | same `GET/POST/PUT /api/entities`, filtered client-side by `type==='faction'` | same | same | + `GET /api/entities/{id}/roles` (`index.html:4628`; `crud.py:891`), memberships (`crud.py:906/946`), faction-roster (`crud.py:976`) |
| Objets | same, filtered `type==='item'` | same | same | no dedicated routes |
| Lieux | `GET /api/locations` (`index.html:3937`; `crud.py:1438`) for hierarchy; `GET /api/entities` also used for dropdowns | `POST /api/entities` (type='location') | `PUT /api/entities/{id}` | + `GET /api/locations/graph` (`crud.py:1392`), discoverable-details CRUD (`crud.py:1278/1301/1338/1377`) |
| Personnage joueur | `GET /api/skills/player-characters` (`index.html:3936`; `crud.py:1038`) for Fiche dropdown; `GET /api/entities` filtered by `playerCharIds` for sidebar | **dedicated** `POST /api/characters/player` (`index.html:5328`; `app.py:1123`) — not generic entity create | `PUT /api/entities/{id}` for sheet fields; `PATCH /api/skills/{id}` (`crud.py:1069`) for skill tiers | only tab with a dedicated create route |
| Compétences | `GET /api/skill-definitions` (`index.html:3136`; `crud.py:1107`) | `POST /api/skill-definitions` (`crud.py:1124`) | `PUT /api/skill-definitions/{id}` (`crud.py:1175`); `DELETE` (`crud.py:1225`) | dedicated router, no `entity_id` |
| Registre | `GET /api/ledger` (`index.html:3286`; `crud.py:1546`) | `POST /api/ledger` (`index.html:3254`; `crud.py:1498`) | none (append-only) | |
| Artefacts | `GET /api/entities?type=artifact` (`index.html:3316`) | none | none | read-only |
| Review Queue | `GET /api/mutations?status=...` (`index.html:2493`) | n/a | approve/reject/apply routes in `app.py` (not `crud.py`) | not entity CRUD |

Generic `/api/entities` CRUD covers NPC/Factions/Objets/Lieux fully and PJ
partially (sheet fields only, not creation). Compétences, Registre, and PJ
creation each have their own dedicated router surface — this is called out
in the ticket as legitimate and out of scope for change.

## 5. Slot candidates (tab-specific blocks beyond list + standard create)

- **NPC**: relations panel `#author-relations` (`index.html:4090-4093`),
  knowledge panel `#author-knowledge` (`index.html:4095-4098`), pending
  knowledge (new-entity AI draft only) `#author-pending-knowledge`
  (`index.html:4101-4104`, state `pendingDraftKnowledge`, `index.html:2879`),
  items `#author-items` (`index.html:4107-4110`), memberships
  `#author-memberships` (`index.html:4113-4117`), ledger/"Solde"
  `#author-ledger` (`index.html:4127-4129`), pricing/"Tarifs"
  `#author-pricing` (`index.html:4132-4135`, NPC-only per CLAUDE.md).
- **Lieux**: discoverable-details editor `#author-disc-list` +
  `#disc-add-form` (`index.html:4138-4142`, list renderer
  `index.html:4722-4750`), plus the hierarchy browse header (breadcrumb +
  "Actifs seulement" toggle, `index.html:3885-3891`, state
  `lieuxBrowseParentId`/`lieuxBreadcrumb`/`lieuxActiveOnly`,
  `index.html:2869-2871`) and the graph panel (`index.html:1165-1177`).
- **Factions**: roles editor `#author-roles` (`index.html:4084-4086`, state
  `authorFactionRolesDraft`, `index.html:2887`), faction-roster (read-only)
  `#author-faction-roster` (`index.html:4120-4123`), ledger/"Solde" (shared
  with NPC, `index.html:4127-4129`).
- **Personnage joueur**: the entire `#creation-pj-skill` block
  (`index.html:1208-1276`) is one big slot — character selector, mode
  toggle, Fiche (`#skill-main`, `index.html:1273`, rendered by
  `skillRender()`, `index.html:5459`) — plus the `#pj-create-block` create
  form (`index.html:1217-1262`), both structurally outside
  `#creation-editor-area`/`authorRenderSheet` entirely.
- **Objets / Artefacts**: no tab-specific blocks beyond the generic sheet
  (Objets) or the bare list (Artefacts).
- **Compétences / Registre / Review Queue**: their entire body is
  tab-specific (inline-editable table, ledger table + filter/add-form, and
  mutation cards + batch bar respectively) — none of it maps onto the
  entity list+detail shape at all.

## 6. Shared state & refresh

Key module-level JS variables (`index.html`, declared ~2855-3346 and
5277-5279): `authorRegistry` (2855), `authorAllEntities` (2856),
`authorEntityId`/`authorEntityType` (2858-2859), `authorLocationTree` (2863),
`lieuxBrowseParentId`/`lieuxBreadcrumb`/`lieuxActiveOnly` (2869-2871),
`pendingDraftKnowledge` (2879), `authorFactionRolesDraft` (2887),
`playerCharIds` (1414), `currentCreationSubTab` (1413), `pjCreateOpen`
(5376), `pcDraftKnowledge` (5375), `skillCharacters`/`skillCharacterId`/
`skillRows` (5277-5279), `regionDraft`/`regionManifest`/
`regionManifestNotes`/`regionManifestSkipped`/`regionAccepted`/
`regionConfirmedLinks` (3341-3346), `competencesDraft` (3035), `graphData`
(5509), `_registreEntitiesLoaded` (3219), `currentFilter` (1405).

`showCreationSubTab()` (`index.html:2961-3026`) resets, per tab switch, only:
`authorEntityId`/`authorEntityType` -> null, the detail panel to its empty
state (all editor tabs, `index.html:2988-3002`), plus
`lieuxBrowseParentId`/`lieuxBreadcrumb` when entering Lieux
(`index.html:2991-2994`), and `pjCreateOpen`/`#pj-create-block` visibility
when entering PJ (`index.html:3007-3010`). No other tab's state is touched
on switch — `regionDraft`, `competencesDraft`, `authorFactionRolesDraft`,
`graphData`, `_registreEntitiesLoaded`, `currentFilter` all persist across
tab switches by default.

`activateWorld()` (`index.html:5824-5855`, world-switch refresh, BRIEF-47/48
per its own comment at `index.html:5839-5841`) explicitly nulls exactly four
things: `authorAllEntities = []`, `playerCharIds = new Set()`,
`skillCharacters = null`, `_registreEntitiesLoaded = false`
(`index.html:5842-5845`) — then re-invokes `showCreationSubTab(...)` (or
`creationInit()`) if the Création view is open. `worldDeleteConfirm()`
(`index.html:5973-6003` per the exploring pass; not independently
re-verified line-by-line) follows the same reset plus `loadBootstrap()` +
`loadScene()`. Confirmed NOT reset by either: `lieuxBrowseParentId`,
`lieuxBreadcrumb`, `regionDraft` and its siblings, `competencesDraft`,
`authorFactionRolesDraft`, `graphData`. Any future template's per-tab state
contract needs to decide whether world-switch should own resetting all of
it generically, since today's coverage is partial and ad hoc.

## 7. Existing shared helpers

- `authorRenderSheet(detail, isNew, type)` (`index.html:4024`) — the actual
  existing "shared render path," already used by NPC/Lieux/Factions/Objets
  and partially by PJ (sheet fields only, not the Fiche or the create form).
- `authorLoadEntityList()` (`index.html:3930`) / `creationRenderEntityList()`
  (`index.html:3781`) — shared list fetch/render for the same four-plus tabs.
- `authorSelectEntity(id)` (`index.html:4939`), `authorSave()`
  (`index.html:4955`), `authorDelete()` (`index.html:5037`),
  `creationNewEntity()` (`index.html:3753`) — shared CRUD glue for the same
  set.
- `authorGenerateEntity()` (`index.html:4184`) / `authorRenderGeneratePanel()`
  (`index.html:4170`) — shared AI-draft panel for NPC/Lieux/Factions (new
  only).
- `genericModalOpen()`/`genericModalClose()` (`index.html:5695`/`5703`) —
  used outside the entity editor too (world create/delete, Compétences
  delete confirm) — a true cross-cutting helper, not entity-CRUD-specific.
- `authorReadField()`/`authorRenderField()` (`index.html:4009`/`3952`) —
  schema-driven field (de)serialization, used only inside
  `authorRenderSheet`/`authorSave`.
- No shared helper exists today that Compétences, Registre, Région, or
  Review Queue reuse from the entity-editor family — each rolled its own
  fetch/render/table code.

## 8. Divergence catalogue

| Tab | Create control | Create UX | List->detail | Layout archetype |
|---|---|---|---|---|
| NPC | `#creation-new-btn`, top of sidebar | inline panel via `authorRenderSheet` | dynamic, `authorSelectEntity` | baseline |
| Lieux | separate "Ajouter un lieu" button in graph header, same handler | inline panel via `authorRenderSheet` | dynamic + hierarchy browse | baseline + graph + hierarchy + discoverable-details slot |
| Factions | `#creation-new-btn` (shared) | inline panel via `authorRenderSheet` | dynamic | baseline + roles/roster slots |
| Objets | `#creation-new-btn` (shared) | inline panel via `authorRenderSheet` | dynamic | baseline, no extra slots |
| Personnage joueur | separate `#pj-create-new-btn`, inside the Fiche block, `#creation-new-row` hidden for this tab | collapsed block, dedicated form, dedicated endpoint (`POST /api/characters/player`) | dynamic, but wired manually in `authorSelectEntity`'s `pj` branch, not the generic path | two parallel panels (entity sheet + Fiche), own create flow entirely outside `authorRenderSheet` |
| Compétences | inline "+ Ajouter" row, no button chrome | new row appended to an editable table | n/a (no list/detail split) | flat editable-table archetype |
| Région | none (multi-step brief->manifest->draft->commit) | n/a | n/a | bespoke wizard archetype |
| Artefacts | none | n/a | none | read-only list archetype |
| Registre | always-visible add-form (not a toggle) | inline form, always open | n/a (filter, not selection) | read-only table + form archetype |
| Review Queue | none | n/a | none (status filter + inline card actions) | queue/card archetype |

## Surprises

The RECON spec and the ticket's own open-decision framing both undercount
the tab set: the live UI has ten Création sub-tabs, not seven — Compétences,
Région, and Registre exist as full sub-tabs alongside the seven originally
named, each with its own non-generic rendering archetype (inline-editable
table, multi-step wizard, and read-only ledger-plus-form respectively).
Decision D needs a third option or an explicit amendment to name where
these three land, since none of them fit the "six entity pages + Review
Queue out" framing at all. Separately, the ticket's premise for open
decision E (a hardcoded `skillCharacters[0]` binding needing a rewire) is
not accurate: `index.html:4945-4949` shows list-selection already drives the
PJ Fiche via `skillSelectCharacter(id)` when an entity is clicked from the
sidebar, and `skillCharacters[0]` is used only as an initial/fallback
default, not the live binding. E should be re-scoped at brief time to "can
the existing ad hoc list->Fiche wiring be expressed through the generic
template's slot-data contract," not "fix a hardcoded first-element bug."
Two further items worth carrying into brief time even though the RECON
questions didn't name them: the "+ Nouveau" affordance already has three
distinct behaviors today (toggle-open inline panel, collapsed block, no
control at all) rather than one convention with exceptions; and the
world-switch cache-reset in `activateWorld()` only clears four of the many
tab-scoped state variables, so a generic per-tab reset contract is itself a
latent gap the template should probably close, not just preserve.
