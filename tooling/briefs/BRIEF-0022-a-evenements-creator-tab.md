# BRIEF — Step "Événements joins the entity archetype (creator read + CRUD)"

## Context

`event` (models.py:607-631) has been written since TICKET-0017 and read by
four consumers — `context.py:582` (MJ world context), `tick.py:497` (location
briefing), `tick.py:606` (faction briefing), `app.py:2643` (return-visit
delta) — but has **no creator surface at all**: no `/api/events` route exists
anywhere in `src/`, and `index.html` contains no occurrence of "événement".
Nia cannot see, correct, or author the events her own world produces.

This brief gives `event` a Création page on the standard entity page
contract. `event` is not an `entity` row, which makes it the THIRD concrete
non-entity reader of the shell after `agenda` (TICKET-0021) — the
`sheetRenderer` seam generalized there is reused verbatim, and nothing new is
added to the contract. It also opens the second sanctioned canon-write path
into `event` (creator CRUD through `writes.py`), and fixes two defects found
during RECON.

Locked: A1, B2, C3, D1, E3, F1, G1, H2, R1.

## Scope IN

1. **`writes.write_event_update`** — new helper, the ONLY place an existing
   `Event` row's attributes are assigned outside `write_event`:

   ```python
   def write_event_update(
       db: Session,
       *,
       event: Event,
       title: str,
       description: Optional[str] = None,
       type: Optional[str] = None,
       knowledge_status: str,
       involved_entities: Optional[list[str]] = None,
       location_id: Optional[str] = None,
   ) -> Event:
   ```

   Sets exactly those six fields and calls `db.add(event)`. It does NOT
   touch `recorded_at`, `occurred_at`, `has_magic_impact`, `consequences`,
   `session_id`, `batch_id` — those keep whatever they had. No
   `change_history` append: the table has no such column (see `write_event`'s
   docstring, writes.py:932-936), and this is stated in the new docstring so
   the omission reads as deliberate, not forgotten.

   Docstring must state: creator-CRUD-only writer; `_apply_mutation` never
   calls it (AI proposals create events, never edit them); the pair
   (`write_event`, `write_event_update`) is the complete set of `event`
   writers.

2. **Vocabulary constants in `cockpit/crud.py`**, beside the existing
   `RELATION_TYPES` / `KNOWLEDGE_LEVELS_ORDERED` block:

   ```python
   # Single source of the event-type vocabulary is tick.py:_EVENT_TYPES —
   # the tick CLAMPS model proposals onto it (tick.py:877). The creator must
   # write into the SAME vocabulary or the column carries two disjoint
   # namespaces. Imported, never re-typed (drafting decision 1).
   EVENT_TYPE_LABELS_FR: dict[str, str] = {
       "political": "politique",
       "military":  "militaire",
       "criminal":  "criminel",
       "social":    "social",
       "mystery":   "mystère",
       "magical":   "magique",
       "other":     "autre",
   }
   EVENT_KNOWLEDGE_STATUSES = ("secret", "public", "confirmed")
   ```

   `EVENT_TYPE_LABELS_FR` MUST be keyed on `tick._EVENT_TYPES` — add an
   import and an assert-on-import (or a verify check) that the key set equals
   `_EVENT_TYPES`, so adding a type in one place and not the other fails
   loudly. `type` stays a free-text column with a `datalist` widget: the
   seven are suggestions, not a constraint (Nia's Q1 — liste + saisie libre).

   `EVENT_KNOWLEDGE_STATUSES` mirrors `app.py:1572`'s clamp exactly. Note in
   a comment that `tick.py:880` accepts only `("secret", "public")` — a
   narrower, pre-existing clamp on the model-proposal path, deliberately left
   alone by this brief.

3. **`EVENT_FIELDS` field-spec list in `cockpit/crud.py`**, same
   `{name, kind, ...}` shape as `RELATION_FIELDS` / `KNOWLEDGE_FIELDS` so it
   feeds the existing `authorReadField` / coercion machinery:

   ```python
   EVENT_FIELDS: list[dict[str, Any]] = [
       {"name": "title", "label": "Titre", "kind": "text", "required": True},
       {"name": "description", "label": "Description", "kind": "textarea"},
       {"name": "type", "label": "Type", "kind": "datalist",
        "options": list(EVENT_TYPE_LABELS_FR.keys())},
       {"name": "knowledge_status", "label": "Statut de connaissance",
        "kind": "select", "options": list(EVENT_KNOWLEDGE_STATUSES),
        "default": "secret", "required": True},
       {"name": "location_id", "label": "Lieu", "kind": "entity_ref",
        "ref_type": "location"},
   ]
   ```

   `involved_entities` is deliberately ABSENT from `EVENT_FIELDS` — it is not
   a scalar field and is handled by the chip editor (item 7). `occurred_at`
   is absent (E3).

4. **`_event_dict(event, db) -> dict` serializer** in `cockpit/crud.py`:

   ```
   id, title, description, type, type_label, knowledge_status,
   location_id, location_name, involved_entities, recorded_at
   ```

   - `type_label` = `EVENT_TYPE_LABELS_FR.get(type, type)` — an unknown
     free-text type displays as itself, never as `None`.
   - `location_name` = resolved `Entity.name`, or `None` when
     `location_id IS NULL` or the target is gone.
   - `involved_entities` is serialized as a list of
     `{"id": str, "name": str | None}` — **name resolved for display**.
     `name` is `None` for an id that no longer resolves (a soft-deleted or
     purged entity); the id is kept, never dropped. The stored column shape
     stays a **flat list of id strings**, which is what `tick.py:614`'s
     faction-briefing reader (`faction_id in e.involved_entities`) and
     `analyzer.py:329` already produce. Do not change the storage shape.

5. **Routes in `cockpit/crud.py`** (this router, not `app.py` — CRUD lives
   here):

   - `GET /api/events` — world-scoped via the existing `_world_id(db)`
     helper; `ORDER BY recorded_at DESC`; returns `list[_event_dict]`.
     Ordering is the API's; the client never re-sorts (the intrigues rule).
   - `GET /api/events/{event_id}` — 404 when absent or not in the active
     world.
   - `POST /api/events` (201) — body `EventCreateBody`. Validates: non-empty
     `title`; `knowledge_status in EVENT_KNOWLEDGE_STATUSES` (422 otherwise —
     do NOT silently clamp, this is the creator, not the model);
     `location_id`, when present, resolves to an **active `location` entity
     in the active world** (reuse the exact predicate at `app.py:1575-1583`);
     each `involved_entities` id resolves to an entity in the active world
     (422 on any that does not — the creator's picker cannot produce a bad
     id, so a bad id means a bug, not a typo). Calls `write_event`, commits.
   - `PUT /api/events/{event_id}` — body `EventUpdateBody`, same validation,
     calls `write_event_update`, commits.
   - **No `DELETE` route.** C3: `event` is history. Add a module-level
     comment beside the routes stating that retraction is
     `knowledge_status = 'secret'`, which structurally removes the row from
     all four readers, and that this mirrors `ledger`'s append-only policy
     (`crud.py` module docstring, "Deletion policy" block — extend it with an
     `event` bullet).

6. **Registry entry** in `index.html`'s `CREATION_TABS`, inserted directly
   after `intrigues`:

   ```js
   evenements: {
     label: 'Événements',
     archetype: 'entity',
     containers: ['creation-editor-area'],
     loader: null,
     state: { onTabEnter: _evenementsTabEnterReset, onWorldSwitch: _evenementsWorldReset },
     listLoader: loadEventsList,
     listRenderer: renderEvenementsListRows,
     sheetRenderer: renderEventSheet,
     createPanel: evenementsRenderCreatePanel,
     primaryAction: { label: '+ Nouvel événement', handler: creationNewEntity },
   }
   ```

   `type` absent (no entity type), exactly as `intrigues`. Both state
   resetters clear: the event cache, `creationSelectedRecordId`, the chip
   draft, and the create-form fields.

7. **Chip editor for `involved_entities`** (H2 — Nia does not author JSON).
   A tab-scoped draft array `evenementsInvolvedDraft` of `{id, name}`:

   - renders one chip per entry: `name` (or `« entité inconnue »` +
     truncated id when `name` is null) plus a `✕` remove control;
   - an add control = an `entity_ref`-style `<select>` over the already
     cached `authorAllEntities`, excluding ids already in the draft;
   - synced from the DOM into the draft immediately before any save, the
     `_syncFactionRolesFromDom` idiom (index.html:6541);
   - serialized to the API as `involved_entities: [id, id, …]` — **the flat
     id list, never the `{id,name}` objects.**

   Raw JSON must appear nowhere in this tab: no `kind: 'json'` textarea, no
   `JSON.stringify` rendered into a form field.

8. **`renderEventSheet(event)`** — the detail pane. Sets
   `creationSelectedRecordId`, renders the `EVENT_FIELDS` scalars through the
   existing field machinery, then the chip block, then `recorded_at` as
   read-only muted text. **Shows the save button, hides the delete button**
   (`author-delete-btn.style.display = 'none'` — unconditionally, on both the
   sheet and the create panel). Saving dispatches to
   `PUT /api/events/{id}`, not to `authorSave` — that function is entity-only
   and must not learn about events.

9. **`evenementsRenderCreatePanel()`** — same fields, empty, with
   `knowledge_status` pre-set to `secret` and an empty chip list. Emits an
   empty `<div id="event-gen-panel">` placeholder above the form, styled like
   `#agenda-gen-panel` (index.html:3994). **BRIEF-0022-b fills it; this brief
   ships it empty.** "+ Créer l'événement" posts to `POST /api/events`, then
   reloads the list and selects the new row.

10. **`renderEvenementsListRows()`** — F1, flat, API order preserved. Each
    row: title (`ali-name`); meta line (`ali-meta`) = location name (or
    `« sans lieu »`, muted), `type_label` and a `knowledge_status` badge.
    Selection via the existing generic `creationSelectRecord('evenements', row)`
    (index.html:6504) — rows carry full data, no per-row fetch. Add
    `.b-secret` / `.b-public` / `.b-confirmed` badge classes to the CSS block
    at index.html:414.

11. **Defect fix — `context.py:587` (RECON finding 7).** Change
    `.order_by(Event.occurred_at.desc())` to `.order_by(Event.recorded_at.desc())`.
    `occurred_at` is written by nobody (`write_event` leaves it None,
    writes.py:931), so the MJ's public-event ordering is currently the
    database's arbitrary return order. This aligns `context.py` with
    `tick.py:502` and `app.py:2650`, which already order by `recorded_at`.
    The `"occurred_at"` key in the emitted dict (`context.py:596`) STAYS —
    it is a prompt-facing field that will carry in-fiction time when that
    chantier opens; it just stops governing the sort.

12. **Defect fix — `context.py:531` (RECON finding 8, R1).** The docstring
    claims the assembler excludes `knowledge_status IN ('secret', 'rumor')`.
    `rumor` exists in no code path (`app.py:1572` clamps to
    `secret|public|confirmed`). Correct it to name `secret` only, and add one
    line: an event either happened or did not; uncertainty about it lives on
    `knowledge.level = 'rumor'`, never on `event.knowledge_status`.

## Scope OUT

- **Deletion**, in every form: no `DELETE /api/events`, no soft-delete
  column, no UI control. Retraction is `knowledge_status = 'secret'` (C3).
- **`occurred_at`**, and any `passé | en_cours | à_venir` status. These are
  ONE deferred chantier — a "future" event is one whose `occurred_at` lies
  ahead of world time — and splitting them would cost two migrations where
  one suffices. Nothing here anticipates it: no column, no field, no note in
  the schema.
- **`has_magic_impact`, `consequences`, `session_id`, `batch_id`** — no
  reader. Not exposed, not written, not serialized by `_event_dict`.
- **Provenance** — no `source_mutation_id` column, no "d'où vient cet
  événement" block (G1). The anchor stays the `proposed_mutation` row.
- **A `rumor` knowledge_status** — the docstring is corrected, the vocabulary
  is not extended (R1).
- **`_apply_mutation`'s `event_creation` branch** and its canon-existence
  duplicate guard (`app.py:886-906`) — untouched. In particular the guard is
  NOT extended to creator-authored events: the creator may deliberately author
  two same-titled events at one location.
- **`tick.py:406`'s `_EVENT_TYPES`** — read, imported, never modified.
- **The AI panel** — BRIEF-0022-b. Only the empty `#event-gen-panel` div ships
  here.
- **Filters or grouping** on the list (F2/F3 rejected).
- **Any migration.** `schema_version` is not bumped.

## Invariants to defend

- **Single canon-write paths.** After this brief, `event` has exactly two
  writers, both in `writes.py`: `write_event` (creation, called by
  `_apply_mutation` AND by `POST /api/events`) and `write_event_update`
  (creator edit only). `Event(` is constructed nowhere outside `writes.py`;
  no route assigns an `Event` attribute directly.
- **History is sacred.** No `event` row is ever deleted or unrowed. The
  absence of a `change_history` column on this table is a known, accepted gap
  (documented, not silently worked around).
- **Page contract purity** (TICKET-0005/0021). `showCreationSubTab` stays a
  pure registry lookup; `creationSelectRecord` gains no tab-id literal and no
  conditional. `evenements` reuses the `sheetRenderer` seam as-is — the
  contract comment block is NOT amended.
- **G1 state contract.** `onTabEnter` and `onWorldSwitch` each reset ALL
  state this tab owns: event cache, selection, chip draft, form fields.
- **One vocabulary per column.** `EVENT_TYPE_LABELS_FR`'s key set is derived
  from `tick._EVENT_TYPES`, not re-typed. A divergence must fail at import or
  at verify, never at runtime.
- **The creator is the authority.** Bad input from the creator is a `422`,
  never a silent clamp. Silent clamping is for model proposals (`app.py:1572`,
  `tick.py:877`), which is precisely the asymmetry between the two write paths.

## Done means

- [ ] Événements tab renders list left / detail right inside
      `creation-editor-area`, visually indistinguishable from NPC or Lieux
- [ ] The list shows events already produced by the tick, newest first, with
      location name, French type label, and status badge
- [ ] Clicking an event opens its sheet; editing title / description / type /
      lieu / statut and saving persists across a reload
- [ ] `involved_entities` renders as named chips; adding and removing a chip
      persists; no raw JSON is visible anywhere in the tab
- [ ] Flipping a `public` event to `secret` removes it from the MJ's
      public-events block on the next scene (verify with
      `scripts/test_context.py` or a live scene)
- [ ] No delete control exists on the sheet, the list, or the create panel
- [ ] "+ Nouvel événement" opens the create panel; the created event is born
      with the status the creator chose (default `secret`) and is selected
      after creation
- [ ] Switching the active world clears list, selection, chips, and form
- [ ] `grep -rn "occurred_at" src/` shows no `order_by`
- [ ] `python tooling/verify/run.py` passes, including `single_canon_write.py`,
      `page_contract.py`, and the new `verify/checks/event_tab.py`
- [ ] /review-step and /close-step run (engine + cockpit code touched)

## Docs to update

- `ARCHITECTURE_DECISIONS.md`: append **"Événements — creator surface
  (TICKET-0022, A1/B2/C3/D1/E3/G1/H2/R1)"**. Record: the third non-entity
  reader of the entity shell (A3 still deferred); `write_event_update` as the
  second sanctioned `event` writer; **C3 no-deletion doctrine and the
  `knowledge_status = 'secret'` retraction mechanism**; the accepted gap
  (`event` has no `change_history`); the deferred **"Temporalité des
  événements"** chantier (`occurred_at` + `passé|en_cours|à_venir`, one
  chantier, one migration); `rumor` rejected on `event` with its rationale.
- `world-engine-schema.md`: no column change. Annotate the `event` table with
  its two writers, its four readers, and the dormant-column list.
- No changelog entry, no schema version bump.

---

## Drafting decisions flagged for Nia

1. **Vocabulaire de `event.type` (item 2).** J'ai rédigé sur **V1** :
   le créateur écrit dans les sept valeurs existantes de `tick._EVENT_TYPES`
   (`political, military, criminal, social, mystery, magical, other`),
   affichées en français. Motif : le tick clampe déjà les propositions du
   modèle dessus (`tick.py:877`) ; deux vocabulaires sur une même colonne
   libre produiraient une liste bâtarde. **V2** = ta liste française en
   `datalist`, les deux namespaces coexistent — je ne le recommande pas.
   **V3** = on remplace `_EVENT_TYPES` par ta liste, ce qui touche le clamp du
   tick et le prompt de tick, donc un troisième brief. Note aussi que
   `magical` survit dans `_EVENT_TYPES` alors que 0012/D3 a retiré
   l'atmosphère magique des prompts — incohérence préexistante, hors scope.
2. **`involved_entities` — id vs `{id,name}` en stockage.** Aucune décision à
   prendre : `tick.py:614` lit `faction_id in e.involved_entities`, donc la
   forme stockée est une liste plate d'ids. Le `{id,name}` n'existe qu'en
   sortie de `_event_dict`, pour l'affichage. Je le signale pour que ce ne
   soit pas relu comme un oubli.
3. **Validation 422 vs clamp silencieux (item 5).** J'ai posé : la route
   créateur renvoie 422 sur un statut invalide, là où `_apply_mutation`
   clampe. C'est délibéré — le clamp protège des dérives du modèle, pas de
   toi. Si tu préfères la symétrie (clamp des deux côtés), dis-le.
4. **Le bouton « enregistrer » ne passe pas par `authorSave`.** J'ai posé une
   fonction de sauvegarde dédiée. L'alternative — élargir `authorSave` à un
   second type de payload — réintroduirait une conditionnelle dans un chemin
   générique. Refusé.
