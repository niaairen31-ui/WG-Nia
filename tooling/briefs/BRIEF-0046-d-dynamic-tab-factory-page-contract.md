# BRIEF -- Step "Dynamic tab factory + page_contract mechanism assertion"

## Context

BRIEF-0046-b exposes `runtime_types`; BRIEF-0046-c creates types and calls a
(forward-declared) `refreshCreationTabs()`. This step implements the single
factory that injects a real Creation sub-tab per runtime type -- reusing the
entity archetype's shared shell, no new container -- and evolves `page_contract`
to assert the MECHANISM (E1) rather than enumerate live types (the no-DB
doctrine holds).

## RECON verified (ticket/0046)

- `creationInit()` loads `authorRegistry` at boot (`index.html:6952-6954`) --
  the hook point for the factory.
- Generic dispatcher, literal-free; it looks up the button by
  `getElementById('ctab-'+tab)` and shows/hides from `entry.containers`/`slots`
  (`index.html:4313-4349`); `_creationActivateTab` (`:4283-4309`).
- Entity archetype entries reuse container `creation-editor-area` +
  `authorRenderSheet` + `authorLoadEntityList`; models: `npc`/`lieux`/`objets`
  (`index.html:4133-4196`). `creationNewEntity`, `authorRenderSheet` exist.
- Static sub-tab bar (`index.html:1200-1213`).
- `page_contract.py`: frozen `TAB_KEYS` (`:11-14`); asserts each key has a
  `CREATION_TABS` entry + `primaryAction` (`:96-105`); asserts
  `showCreationSubTab` / `_creationActivateTab` bodies carry no tab-id literal
  (`:107-127`); pure static scan of `index.html`, no DB (`:88-89`).
- Serializer ships `runtime_types` (BRIEF-0046-b).

## Scope IN

1. Add `_buildRuntimeCreationTabs()` in `index.html`, called from
   `creationInit()` immediately after `authorRegistry` is assigned
   (`:6954`). For each `slug` in `authorRegistry.runtime_types`:
   - if `CREATION_TABS[slug]` is absent, inject a NORMAL entity-archetype entry:
     `CREATION_TABS[slug] = { label: authorRegistry.types[slug].label,
       archetype: 'entity', containers: ['creation-editor-area'], loader: null,
       state: { onTabEnter: _entityTabEnterReset, onWorldSwitch:
       _entityListWorldReset }, type: slug,
       createPanel: () => authorRenderSheet({}, true, slug),
       primaryAction: { label: '+ Nouveau', handler: creationNewEntity },
       slots: [] }`.
   - if a `#ctab-<slug>` button is absent from `.creation-sub-tab-bar`, append
     `<button class="creation-sub-tab" id="ctab-<slug>"
     onclick="showCreationSubTab('<slug>')">label</button>`.
   The factory adds NO tab-id branch to the dispatcher and NO new container --
   every runtime tab rides the shared `creation-editor-area` shell via its data.
2. Idempotency + world scope: before rebuilding, remove any runtime button/
   entry no longer in `authorRegistry.runtime_types` (types are per-world; a
   world switch must clear the previous world's runtime tabs). Track injected
   runtime slugs in a module set so removal is precise (never touch the static
   buttons/entries).
3. Implement `refreshCreationTabs()` = re-fetch `/api/entity-types` into
   `authorRegistry`, then run `_buildRuntimeCreationTabs()`. This is the hook
   0046-c calls after a successful create, and it should also run on world
   switch (wire into the existing world-switch path that already resets Creation
   state).
4. `page_contract.py` (E1 mechanism assertion), keeping it a static scan:
   - Add `"constructeur"` to `TAB_KEYS` (its bespoke entry + `primaryAction`
     landed in 0046-c; the check now covers it).
   - Assert `_buildRuntimeCreationTabs` is defined AND called from
     `creationInit` (the factory is the sole producer of runtime tabs).
   - Assert the static markup contains a `#ctab-<x>` button ONLY for `x` in
     `TAB_KEYS` -- any hand-authored custom `#ctab-` in static HTML is a FAIL
     (runtime buttons are injected by JS at runtime, never present in the static
     source). Implement by scanning static `id="ctab-..."` occurrences and
     asserting each id's suffix is in `TAB_KEYS`.
   - Keep the existing "no tab-id literal in dispatcher/activate" asserts intact
     -- the factory must not have added any.
   The check never reads the DB or enumerates live runtime types; it verifies
   that runtime tabs can ONLY exist via the factory.

## Scope OUT

- Instance read/write for custom `ext_*` (0046-e) -- the injected tab's form
  renders via `authorRenderSheet` (fields already served by 0046-b), but
  persisting/reading instances of a custom type is 0046-e; until it lands, the
  form renders and submit hits the not-yet-generalized create path.
- `json_ui_boundary` volet (0046-e).
- No new container, no bespoke shell for runtime types (reuse
  `creation-editor-area`).
- No `page_contract` DB read / live-type enumeration (E1 is mechanism-only).

## Invariants to defend

- Generic dispatcher: all per-tab variation lives in `CREATION_TABS` data;
  `page_contract`'s literal-free asserts must still pass after the factory.
- "No page renders outside the registry": runtime tabs are registry entries
  built by the single factory; no ad-hoc DOM tab bypasses it.
- Fail-closed check: zero parsed `#ctab-` buttons or a missing factory call is a
  FAIL, not a vacuous pass.

## Done means

- [ ] With one runtime type present (created via 0046-c or a curl to the
      route), reloading Creation shows its sub-tab; clicking it opens the shared
      list+detail shell with the type's generated form (base fields +
      `location_id` picker + `is_secret` toggle for a spatial+secretable type).
- [ ] Creating a second type via the Constructeur and returning shows its tab
      without a full reload (`refreshCreationTabs` fired).
- [ ] Switching to a world without that type removes the runtime tab; switching
      back restores it. Static tabs are never added/removed.
- [ ] `python tooling/verify/checks/page_contract.py` passes; then (red-team)
      hand-adding `<button id="ctab-foo">` to static markup makes it FAIL, and
      removing the `_buildRuntimeCreationTabs()` call from `creationInit` makes
      it FAIL.
- [ ] No tab-id literal leaked into `showCreationSubTab` / `_creationActivateTab`
      (existing asserts green).
- [ ] `/review-step` and `/close-step` run.

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: append -- runtime Creation tabs are injected by a
  single boot/refresh factory (`_buildRuntimeCreationTabs`) as entity-archetype
  registry entries on the shared shell; `page_contract` asserts the mechanism
  (factory is sole producer; no hand-authored custom `#ctab-`), never enumerates
  live types (E1, no-DB doctrine preserved).
- `CLAUDE.md`: note the factory + `refreshCreationTabs` and the updated
  `page_contract` contract line.

---

### Drafting decisions flagged (reversible)

1. **Runtime entry uses `_entityTabEnterReset` / `_entityListWorldReset`** (the
   generic entity-tab resets), matching `objets`. Fine unless a runtime type
   needs bespoke reset state (none do today).
2. **`page_contract` scans `id="ctab-..."` suffixes against `TAB_KEYS`** as the
   "no hand-authored custom tab" assertion. If you'd rather assert positively
   (exactly the N static buttons, in order), I can switch to a stricter list
   match.
3. **`constructeur` added to `TAB_KEYS` here** (bundled with the factory), not
   in c. Move it to c if you want the check to cover the tab one cycle earlier.
