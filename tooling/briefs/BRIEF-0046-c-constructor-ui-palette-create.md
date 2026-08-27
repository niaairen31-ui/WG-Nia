# BRIEF -- Step "Constructor UI: trait palette + create-type panel"

## Context

BRIEF-0046-b landed the create-type route and the serializer that now ships
`checkable_traits` (palette source) and `runtime_types`. This step adds the
Creation-mode surface where the creator names a type, checks traits, and
submits. The created type persists and appears in `GET /api/entity-types`; the
live sub-tab for it is BRIEF-0046-d (this brief's success path ends at a
confirmed create + a refreshed registry).

## RECON verified (ticket/0046)

- Boot: `creationInit()` fetches `/api/entity-types` -> `authorRegistry`
  (`src/world_engine/cockpit/index.html:6952-6954`).
- Bespoke tab shape (models to mirror): `competences`
  (`index.html:4197-4204`), `region` (`:4205-4211`) -- `{label, archetype:
  'bespoke', containers:[...], loader, state:{onTabEnter, onWorldSwitch},
  primaryAction:{label, handler}}`.
- Static sub-tab bar, 13 hand-written buttons (`index.html:1200-1213`).
- Generic dispatcher, literal-free (`index.html:4313-4349`).
- Serializer now provides `authorRegistry.checkable_traits` = `[{key,label}]`
  and `authorRegistry.runtime_types` (BRIEF-0046-b).

## Scope IN

1. Register a bespoke Creation tab `constructeur` in `CREATION_TABS`
   (`index.html`, alongside `competences`/`region`):
   `constructeur: { label: 'Constructeur', archetype: 'bespoke',
     containers: ['creation-constructeur'], loader: constructeurRender,
     state: { onTabEnter: constructeurResetForm, onWorldSwitch:
     constructeurResetForm }, primaryAction: { label: 'Creer le type',
     handler: constructeurSubmit } }`.
2. Add the static button in `.creation-sub-tab-bar` (`index.html:1200-1213`):
   `<button class="creation-sub-tab" id="ctab-constructeur"
   onclick="showCreationSubTab('constructeur')">Constructeur</button>`, and a
   `<div id="creation-constructeur" ...>` container in the Creation panel markup
   (hidden by default like the other bespoke containers).
3. `constructeurRender()` renders into `#creation-constructeur`:
   - a `name` text input and a `slug` text input. Auto-suggest slug from name
     (lowercase, spaces/accents -> `_`, strip to `[a-z0-9_]`), editable; the
     server validates the final slug.
   - a checkbox palette, one per `authorRegistry.checkable_traits` entry
     (`key` as value, `label` as text). No `describable` checkbox (it is socle,
     never in `checkable_traits`).
   - a status line region for success/error.
4. `constructeurSubmit()`:
   - collect `name`, `slug`, and checked `trait_keys`; guard `name` and `slug`
     non-empty client-side (server re-validates).
   - `POST /api/entity-types {name, slug, trait_keys}`.
   - on success: show a success line naming the created type + its columns;
     re-fetch `/api/entity-types` into `authorRegistry`; then call
     `if (typeof refreshCreationTabs === 'function') refreshCreationTabs();`
     (the function is implemented in 0046-d; the guarded call is a forward
     declaration so this brief has no hard dependency on d).
   - on error: show the server message; leave the form populated.
5. `constructeurResetForm()` clears inputs, unchecks the palette, clears the
   status line. Wired as both `onTabEnter` and `onWorldSwitch` (types are
   per-world).

## Scope OUT

- The runtime type's sub-tab appearing live + its generated instance form is
  BRIEF-0046-d (factory) + 0046-e (instance CRUD). This brief stops at a
  confirmed create and a refreshed `authorRegistry`.
- No backend change: the route and `checkable_traits`/`runtime_types` are
  0046-b; consume them, do not add serializer keys here.
- No `page_contract` edit -- adding `constructeur` to `TAB_KEYS` is 0046-d
  (bundled with the factory assertion), so this tab is momentarily uncovered by
  the check until d; do NOT partially edit the check here.
- No type retire/delete UI, no editing an existing type's traits.

## Invariants to defend

- All per-tab variation lives in `CREATION_TABS` data; `constructeur` is a
  normal bespoke entry -- do NOT add a `constructeur` branch inside
  `showCreationSubTab` / `_creationActivateTab` (dispatcher stays literal-free;
  0046-d's `page_contract` will enforce this).
- Palette is server-sourced (`authorRegistry.checkable_traits`) -- never a
  hardcoded trait list in the frontend (single source; a new trait added in
  `traits.py` must appear without a frontend edit).

## Done means

- [ ] A "Constructeur" sub-tab appears in Creation; opening it shows the
      name/slug inputs and a checkbox per checkable trait (spatial, knowable,
      secretable, mutable_by_ai), no describable box.
- [ ] Typing a name auto-fills a sanitized slug (editable).
- [ ] Checking spatial + secretable, naming a type, and clicking "Creer le
      type" POSTs and shows a success line; `GET /api/entity-types` (re-fetched)
      then lists the new slug in `runtime_types`.
- [ ] A server 422 (e.g. slug `character`) surfaces its message inline; the
      form stays populated.
- [ ] Switching worlds resets the form; no tab-id literal for `constructeur`
      exists in the dispatcher/activate bodies.
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `CLAUDE.md`: add `constructeur` to any Creation sub-tab inventory, noting it
  is bespoke and palette-driven from the serializer.
- This step is otherwise its own doc (UI wiring).

---

### Drafting decisions flagged (reversible)

1. **Tab label "Constructeur"** and id `constructeur`. Rename to "Types" /
   `types` if you prefer.
2. **Client-side slug auto-suggest** (sanitize name), server validates. Drop the
   auto-suggest and require manual slug if you'd rather.
3. **Forward-declared `refreshCreationTabs()`** call (guarded) so c lands before
   d without a hard dependency; the created tab appears live only once d lands.
   If you'd rather sequence d before c, the guard becomes unconditional.
4. **`page_contract` coverage of `constructeur` deferred to d** (bundled with
   the mechanism assertion) -- so between c and d the check does not yet know
   this tab. Acceptable for one landing cycle; flag if you want it covered in c.
