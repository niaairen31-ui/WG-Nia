# BRIEF 0095-D — "the review panel"

Lot: LOT-0095-choice-review.md (authoritative on conflict)
Depends on: BRIEF-0095-C (the routes)

## Anchors to confirm (Mini-RECON)

Halt if any of these has moved. Drift rule: the same content shifted by a few
lines is drift, not a STOP — note it and proceed; different content is always
a STOP.

- C has landed: `GET /api/lore/choices` and
  `POST /api/lore/choices/{choice_id}/review` exist per C-07;
  `choice_review.py` passes with T0-T10.
- `frontend/src/lore/Lore.svelte:16` `import NamesPanel from './NamesPanel.svelte';`;
  `:96-98` `{#if loreTab === 'names'}` / `<NamesPanel visible={active} />` / `{/if}`.
- `frontend/src/lore/NamesPanel.svelte` declares `SCOPE_OPTIONS` with the three
  labels of R-19.
- `frontend/src/lore/namesPanel.svelte.js:21` `export const DEFAULT_SCOPE = 'rencontre';`;
  `:36` `export function categoryOf(type) {`.
- `frontend/src/creation/sheetRequest.svelte.js:30` `export async function api(path, options) {`.
- Neither `ChoiceReviewPanel.svelte` nor `choiceReview.svelte.js` exists in
  `frontend/src/lore/`.

## Facts carried

Verbatim from the lot header.

#### R-11 — plan-route ordering and timestamps ("sans plan")
Opened: `src/world_engine/cockpit/routes/day.py:506-520`, `537-541`,
`590-594`, `615-622`, `655-669`; `src/world_engine/models/canon.py:48-59`
Finding [M]: a day is planned once: `_load_plannable_day` refuses a
`pass_play` whose `status != 'submitted'`, and a successful plan sets
`status = 'resolving'` in its single commit. On the plan path,
`_write_declaration_rewrite` constructs the `DayRewrite` (generation 1)
BEFORE `write_day_mention_choices` constructs the records, both in the plan's
one transaction. On the 409 path, `_record_refused_choices` rolls back and
commits the records alone; no rewrite exists. A plan failure after the rewrite
(502) commits nothing. `_created_ts()` is a Python `default_factory`
(`datetime.now(UTC)`) evaluated at construction. Measured on a prototype: a
409-path row stamped before the rewrite, and a plan-path row stamped after it;
`any(rw.created_at <= choice.created_at)` gives `False` then `True`.
Consequence: a choice is "planned" iff some `day_rewrite` of its `pass_play`
has `created_at <= choice.created_at` (C-05). Otherwise the panel shows
"sans plan".

#### R-12 — the names panel's route and reads
Opened: `src/world_engine/cockpit/routes/lore_mentions.py:1-110`;
`src/world_engine/lore_mentions_read.py:27-67`;
`src/world_engine/lore_resolve.py:38-43`, `60-65`, `241-261`
Finding [M]: the route module holds `router = APIRouter()`,
`_CHANGED_BY = "creator_crud"`, a `_world_id(db)` helper raising 400 `"No
active world. Activate a world before proceeding."`, one commit per request,
`ValueError` → `db.rollback()` + 422. `lore_mentions_read.active_world_id(db)`
returns the active world's id or `None`; `excerpt(text, surface)` returns up
to `EXCERPT_LENGTH` (80) characters around the surface (the whole text when
shorter). `validate_binding(entity_id, category, world_id, db)` is True iff
the entity is active, in the world, and of the category's types;
`CATEGORIES = ("place", "person", "faction", "object", "other")`;
`category_of_type(entity_type)`.
Consequence: the new route copies that module's shape (named, not gestured
at: C-07). The reader reuses `active_world_id` and `excerpt`.

#### R-19 — the Lore shell and the names panel (frontend)
Opened: `frontend/src/lore/Lore.svelte:1-100`; `frontend/src/lore/NamesPanel.svelte`
(whole); `frontend/src/lore/namesPanel.svelte.js:14-44`, `160-175`;
`frontend/src/creation/sheetRequest.svelte.js:30-35`;
`src/world_engine/cockpit/crud/entities.py:217-226`, `474-483`
Finding [M]: `Lore.svelte` imports `NamesPanel` (line 16) and renders it
inside `{#if loreTab === 'names'}` (96-98), after a tab bar whose second button
reads "Noms à lier". `NamesPanel.svelte` declares `SCOPE_OPTIONS` (rencontre →
"Ceux qui l'ont rencontré", world → "Tout le monde", none → "Personne"),
reloads on `serverState.worldId` in one `$effect` and loads when `visible` in
a second, and renders an entity search (`input type=search` + `select`).
`namesPanel.svelte.js` exports `DEFAULT_SCOPE = 'rencontre'` and
`categoryOf(type)`; its private `loadEntities` calls `api('/api/entities')`
and keeps `status === 'active'` rows. `GET /api/entities` returns
`_entity_summary` dicts (`id, world_id, type, name, internal_name, status,
is_public`) for the active world, ordered by type then name. `api(path,
options)` throws `Error(detail)` on a non-2xx.
Consequence: D builds a sibling component in the same tab, reusing
`categoryOf` and `api`, and fetching `/api/entities` the same way.

#### R-22 — governance files
Opened: `tooling/tickets/TICKET-0094-concordance-h2.md:1-15`;
`tooling/verify/checks/claude_md_contract.py:12-14`, `71`, `149-153`;
`tooling/standards/ARCHITECTURE_DECISIONS.md:16502`, `16669-16720`;
`tooling/verify/checks/decisions_index.py:15-17`;
`tooling/verify/checks/pipeline_state.py:1-60`
Finding [M]: TICKET-0094 line 5 reads `status: live-gate`, `current_brief:`
empty (Nia reports it passed). CLAUDE.md's File-structure section is capped at
80 lines, and 0094-D recorded it at the cap (no line added). Its file-map line
`lore_*.py, subject_resolve.py  # resolver/selectors/plan/names-panel reads;
subject<->entity` already covers a `lore_choices_read.py`. Decision headers
must match `^## .+ \(BRIEF-\d{4}(-[a-z])?(, ...)*, (schema v\d+\.\d+|no schema
change)\)$`. `pipeline_state.py`'s docstring (line 22) says "at least one
arrow resolving to a real file"; its implementation (`check_section_shape`,
lines 107-114) fails on EVERY Machine-checkable arrow that does not resolve,
once `status` is in `{brief, exec, verify, live-gate, done}`. Measured: this
lot's ticket at `status: brief` fails pipeline_state on the two new checks
until they exist.
Consequence: A closes 0094 in its own commit and creates both new checks
before running any gate (pipeline_state stays red on this ticket from its
deposit until A's check files exist). No CLAUDE.md edit in this lot.
Decision headers use the lowercase brief letter.

## Contracts

Verbatim from the lot header.

Two families are written here first and re-read after their last member:

- **review verdict** — the values `agreed` / `disagreed` and the appellation
  scopes `rencontre` / `world` / `none`: the table CHECKs (C-01), the writer
  (C-03), the route (C-07), the panel (C-08).
- **pending row** — the dict one reviewable choice becomes (C-06): built only
  by `list_pending_choices` (C-05), returned unchanged by the GET route
  (C-07), rendered by the panel (C-08).

#### C-06 — the pending row (family)
Produced by: C-05   Consumed by: C-07 (GET, unchanged), C-08
Every key required:
```python
{
  "id": str,                      # the day_mention_choice id
  "surface_form": str, "category": str, "trigger": str,
  "verdict": str,                 # "accepted" | "rejected"
  "verdict_detail": Optional[str], "excerpt": Optional[str], "reason": Optional[str],
  "day": {
    "day_number": int,            # batch.day_number
    "character_name": str,        # entity.name of pass_play.character_id
    "declaration": str,           # lore_mentions_read.excerpt(declared_action, surface_form)
    "planned": bool,              # R-11
  },
  "chosen": {"id": str, "name": str, "type": str},
  "candidates": [{"id": str, "name": str, "type": str}, ...],   # ordinal order
  "excerpt_source": str,          # "facts" | "declaration" | "none"
  "evidence": [{"fact_id": str, "content": str,
                "scopes": [{"scope_type": str, "scope_name": Optional[str]}]}],
  "preselected_scope": str,       # "world" | "rencontre"
}
```

#### C-07 — routes `/api/lore/choices`
Produced by: C   Consumed by: C-08, live play
New module `src/world_engine/cockpit/routes/lore_choices.py`, shaped like
`routes/lore_mentions.py` (R-12): `router = APIRouter()`, `_CHANGED_BY =
"creator_crud"`, a `_world_id(db)` helper raising 400 with the same detail,
one commit per request. No `select(`, no `chat(`.
- `GET /api/lore/choices` → `{"choices": list_pending_choices(db, world_id)}`.
- `POST /api/lore/choices/{choice_id}/review`, body
  `ChoiceReviewBody(verdict: str, entity_id: Optional[str] = None,
  record_appellation: bool = False, scope_type: str = "rencontre")`.
  Steps, first failure wins:
  1. no active world → 400;
  2. `reviewable_choice(...)` is `None` → 404
     `f"reviewable choice {choice_id!r} not found"`;
  3. `is_reviewed(...)` → 409 `f"choice {choice_id!r} is already reviewed"` (J1);
  4. `verdict` not in `("agreed", "disagreed")` → 422
     `"verdict must be 'agreed' or 'disagreed'"`;
  5. `agreed`: `entity_id` not `None` and `!= choice.chosen_entity_id` → 422
     `"agreed: entity_id must be omitted or equal the model's choice"`;
     the effective entity is `choice.chosen_entity_id`;
  6. `disagreed`: `entity_id is None` and `record_appellation` → 422
     `"disagreed without an entity cannot record an appellation"`;
     `entity_id == choice.chosen_entity_id` → 422
     `"disagreed: entity_id equals the model's choice"`; the effective
     entity is `entity_id` (may be `None`: H2);
  7. effective entity not `None` and not `validate_binding(effective,
     choice.category, world_id, db)` → 422
     `"entity_id is not an active entity of this category in the world"`;
  8. inside `try`: if `record_appellation`, `fact = record_appellation(db,
     entity_id=effective, surface=choice.surface_form, scope_type=
     body.scope_type, created_by=_CHANGED_BY)` (else `fact = None`); then
     `write_day_mention_review(db, world_id=world_id, choice_id=choice.id,
     verdict=body.verdict, entity_id=effective, appellation_fact_id=fact.id
     if fact else None, appellation_scope=body.scope_type if fact else None)`;
     `except ValueError` → `db.rollback()`, 422 `str(exc)`;
  9. `db.commit()`; return `{"ok": True, "id": choice_id,
     "appellation_written": fact is not None}`.
  Nothing is written on any failure path. The past day, its rewrite and its
  resolutions are never touched.
Mounted in `cockpit/app.py` right after `lore_mentions`.

#### C-08 — the review panel
Produced by: D   Consumed by: Nia (live gate)
Files: `frontend/src/lore/ChoiceReviewPanel.svelte`,
`frontend/src/lore/choiceReview.svelte.js`; `Lore.svelte` renders
`<ChoiceReviewPanel visible={active} />` right after `<NamesPanel ... />`,
inside the same `{#if loreTab === 'names'}` block.
State module (`choiceReview.svelte.js`), same shape as
`namesPanel.svelte.js`: `reviewState = $state({loading, error, choices: [],
entities: null, record: {}, scope: {}, target: {}, query: {}, busy: {}})`;
`loadChoices()` (GET, then the active entities via `api('/api/entities')`
filtered to `status === 'active'`), `reloadForWorld()`, setters, and
`agree(id)` / `disagree(id)` (POST; on success the row leaves `choices`).
Per row the panel shows, in French:
- head: « {surface_form} » · catégorie · « ambigu » (`ambiguous`) or « nom
  proche » (`near`) · « Jour {day_number} — {character_name} » and, when
  `!day.planned`, a « sans plan » badge;
- the declaration excerpt;
- « Choix du modèle : {chosen.name} », then « accepté » or « refusé par le
  juge — {verdict_detail} »;
- « Extrait : « {excerpt} » » and « Raison : {reason} » when present;
- « Candidats : » the candidate names, comma-separated (F1: names only);
- evidence: each cited fact's content with its scopes (world → « tout le
  monde », location/faction/rencontre → « lieu / faction / rencontre :
  {scope_name} »); `declaration` → « extrait tiré de la déclaration »;
  `none` → « preuve introuvable »;
- « D'accord » block: a checkbox « Enregistrer « {surface_form} » comme
  appellation de {chosen.name} », **checked by default** (I1), and the scope
  select (the three `SCOPE_OPTIONS` labels) preset to `preselected_scope`;
  button « D'accord » → `{verdict: "agreed", record_appellation, scope_type}`;
- « Pas d'accord » block: a search input and a select whose options are
  « — choisir — » (value `""`), « Aucune entité connue » (value `"none"`,
  H2), then the active entities of the row's category (`categoryOf`), the
  model's choice excluded, filtered by the search text; a checkbox
  « Enregistrer aussi comme appellation », **unchecked by default**, disabled
  unless an entity is selected; a scope select preset to `rencontre`; button
  « Pas d'accord », disabled while the select is on « — choisir — » →
  `{verdict: "disagreed", entity_id: <id, or null for "none">,
  record_appellation, scope_type}`.
- empty list → « Aucun choix à revoir. »

## Context

The routes exist; Nia still has no screen. This brief adds the panel beside
« Noms à lier », where the entity selector and the appellation scopes already
live, and ships the built frontend.

## Scope IN

1. **State module.** Create `frontend/src/lore/choiceReview.svelte.js` per
   C-08, on `namesPanel.svelte.js`'s shape: a header comment naming
   TICKET-0095 (K1) and C-08; `import { api } from
   '../creation/sheetRequest.svelte.js'`; `import { serverState } from
   '../lib/serverState.svelte.js'`; `import { categoryOf } from
   './namesPanel.svelte.js'`; the exported `reviewState`; `loadChoices()`;
   `reloadForWorld()` (clears everything, like `namesPanel`'s); setters for
   the per-row `record`, `scope`, `target` (the disagree select's value) and
   `query`; `disagreeOptions(row)` (active entities with
   `categoryOf(e.type) === row.category`, `e.id !== row.chosen.id`, name
   containing the query, case-insensitive); `agree(row)` posting
   `{verdict: "agreed", record_appellation, scope_type}` with
   `record_appellation` defaulting to `true` for a row the user has not
   toggled (I1) and `scope_type` defaulting to `row.preselected_scope`;
   `disagree(row)` posting `{verdict: "disagreed", entity_id, 
   record_appellation, scope_type}` where `entity_id` is `null` for the
   « Aucune entité connue » value `"none"`, `record_appellation` defaults to
   `false` and is forced `false` when `entity_id` is `null`, and `scope_type`
   defaults to `'rencontre'`. On success the row leaves `reviewState.choices`;
   on failure `reviewState.error` holds the message and the row stays.

2. **Panel.** Create `frontend/src/lore/ChoiceReviewPanel.svelte` per C-08:
   header comment naming TICKET-0095 (K1); `let { visible = false } =
   $props();`; the same two `$effect`s as `NamesPanel.svelte` (reload on
   `serverState.worldId`, then load when `visible`), with no `$state` read
   after being assigned in the same effect body (`effect_self_write.py`);
   heading « Choix du modèle à revoir » with a « Rafraîchir » button; its own
   `SCOPE_OPTIONS` constant with NamesPanel's three values and labels; the
   French labels and layout of C-08; styles scoped in the component, reusing
   the CSS variables NamesPanel uses (`--border`, `--muted`, `--red`).

3. **Mount.** In `frontend/src/lore/Lore.svelte`, import the panel after the
   `NamesPanel` import and render `<ChoiceReviewPanel visible={active} />`
   right after `<NamesPanel visible={active} />`, inside the same `{#if}`.
   Add one sentence to the file's header comment: "TICKET-0095 (K1): the
   same tab hosts the model-choice review (ChoiceReviewPanel.svelte)."

4. **Build.** `cd frontend`, `npm ci`, `npm run build`; commit the updated
   `src/world_engine/cockpit/static/` output and its `.build-manifest.json`
   in the same commit as the sources.

5. Append to `ARCHITECTURE_DECISIONS.md` an entry headed
   `## THE REVIEW PANEL (TICKET-0095) -- K1 LIVES BESIDE THE NAMES TO LINK (BRIEF-0095-d, no schema change)`:
   why the « Noms à lier » tab (the K1 principle; the selector and scopes
   already there); I1 (agree checked by default) versus disagree unchecked;
   « — choisir — » versus « Aucune entité connue » (H2 must be an explicit
   pick); « sans plan »; F1 (names only). Regenerate `DECISIONS_INDEX.md`.

## Scope OUT

- Any backend change. Any change to `NamesPanel.svelte` or
  `namesPanel.svelte.js` (only `categoryOf` is imported).
- A « déjà revus » section or a re-review button (J2).
- Showing a candidate's matched appellation (F2).
- A location/faction option in the scope select (C1).
- Any other Lore tab or the question view.

## Invariants to defend

- Creator control: every write is one explicit click on « D'accord » or
  « Pas d'accord »; nothing posts on load or on a select change.
- "Pas d'accord laisse choisir la bonne entité dans un sélecteur, jamais en
  tapant un nom": the search input only filters the select; no free text is
  ever posted.
- Build output is committed (`frontend_build_fresh.py`).

## Decision rights

STOP:
- an anchor does not hold (other than drift);
- the panel needs a field the GET does not return (C-06 is closed).

ADAPT:
- `npm ci` fails on a lockfile mismatch unrelated to this brief: run
  `npm install`, commit nothing but the build output and this brief's
  sources, report.
- `effect_self_write.py` flags an effect: restructure it the way
  `NamesPanel.svelte` does (reset in one effect, load in the other), report.

REPORT-ONLY:
- visual rough edges Nia may want to adjust at the live gate.

> Any finding not listed above that touches neither a CLAUDE.md invariant nor a
> `danger_class` of this ticket: resolve it by the most conservative option
> available, proceed, and report it. Any finding that touches an invariant or a
> `danger_class` is a STOP, whether or not it is listed.

## Done means

- [ ] `python tooling/verify/checks/frontend_build_fresh.py`,
      `module_budget.py`, `effect_self_write.py` → pass.
- [ ] `WORLD_ENGINE_ENV=test python tooling/verify/checks/corpus_gate.py` is green.
- [ ] On the test DB with `choice_review.py`'s kind of data (or any stored
      choice): the cockpit's Lore → « Noms à lier » shows « Choix du modèle à
      revoir »; « D'accord » and « Pas d'accord » remove the row; a failed
      POST shows the error and keeps the row.
- [ ] `/review-step` then `/close-step`.

## Docs to update

- `ARCHITECTURE_DECISIONS.md` + `DECISIONS_INDEX.md` (item 5). No schema
  change. No CLAUDE.md.
