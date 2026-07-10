---
id: TICKET-0022
title: Événements — creator tab on the entity page contract + AI creation assistant
type: feature
status: exec
created: 2026-07-09
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write]      # -b seeds a new prompt template head; no migration
blast_radius: medium
brief_ids: [BRIEF-0022-a, BRIEF-0022-b]
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

« Je n'ai pas d'onglet évènements (events) qui me permet de suivre les
évènements dans mon outil créateur. Je veux que cela suivre le contrat de page
standards des entité. »

Plus, en intake : « assure toi qu'il y [a] l'assistant créateur AI ».

## RECON findings (tarball `main`, 2026-07-09)

1. `Event` (`models.py:607-631`) is a standalone table — own `id`, direct
   `world_id`, **no FK to `entity.id`**. It cannot route through
   `ENTITY_TYPE_REGISTRY` or `/api/entities`.
2. `Agenda` is the exact structural precedent: a non-entity table registered
   `archetype: 'entity'` in `CREATION_TABS` via the `listLoader` /
   `listRenderer` / `sheetRenderer` / `createPanel` seams
   (`index.html:3155-3182`, `index.html:3264`, dispatcher
   `creationSelectRecord` at `index.html:6504`). Nothing new is needed in the
   shell.
3. **No read surface exists.** No `/api/events` route anywhere in `src/`. No
   occurrence of "événement" in `index.html`.
4. Sole write path: `write_event` (`writes.py:911`), called only from
   `_apply_mutation`'s `event_creation` branch. Canon-existence duplicate
   guard at `app.py:886-906` (0014 doctrine — normalized title + `location_id`,
   never `tick_id` equality).
5. Readers of `event`: `context.py:582` (world context), `tick.py:497`
   (location briefing), `tick.py:606` (faction briefing), `app.py:2643`
   (return-visit delta). All filter `knowledge_status IN ('public','confirmed')`.
6. Dormant columns, never written by `write_event`: `occurred_at`,
   `has_magic_impact`, `consequences`, `session_id`, `batch_id`.
7. **Defect:** `context.py:587` orders by `Event.occurred_at.desc()` — a column
   that is always NULL. Public-event ordering into the MJ prompt is therefore
   arbitrary. `tick.py` and `app.py:2650` both order by `recorded_at`.
8. **Doc defect:** `context.py:531` documents a `rumor` knowledge_status that
   exists in no code path; `app.py:1572` clamps to `secret|public|confirmed`.
9. No provenance column on `event` (no `tick_id`, no `mutation_id`). The
   provenance anchor is the `proposed_mutation` row (`writes.py:932-936`).
10. No `change_history` column on `event`.
11. Public-entity predicate (for J3 below): `context.py:611` filters
    `Entity.status == 'active'` in SQL but tests `is_public` **in Python**
    (`context.py:615`), after the query. `internal_name` is never exposed to
    any model (`context.py:530`).

## Clarifications resolved (intake)

- **A1** — The Événements page is a `CREATION_TABS` entry with
  `archetype: 'entity'` and `containers: ['creation-editor-area']`, using the
  declared seams. Exact calque of `intrigues`. This is the second concrete
  non-entity reader of the sheetRenderer seam; minimal-first is satisfied and
  no further shell generalization is built.
- **B2** — Creator create + edit, both routed through `writes.py`:
  `write_event` is reused for creation, a new `write_event_update` helper is
  added for edits. Second sanctioned canon-write path, per the standing
  two-path doctrine. `_apply_mutation` keeps calling the same `write_event`;
  the two paths cannot diverge.
- **C3** — **No deletion.** `event` is history. Retraction is performed by
  setting `knowledge_status = 'secret'`, which structurally excludes the row
  from all four readers. No new column, no soft-delete flag. (Aligned with
  `ledger`'s append-only policy.)
- **D1 + E3** — Fields exposed on the sheet: `title`, `description`, `type`,
  `knowledge_status`, `location_id`, `involved_entities`. `occurred_at` is
  **not** exposed, and `context.py:587` is corrected to order by
  `recorded_at DESC`, aligning it with `tick.py` and `app.py:2650`. This
  removes the only reader of `occurred_at`, which is correct: the column is
  reserved for the deferred in-fiction-time chantier and has no consumer
  until then.
- **R1** — `context.py:531`'s docstring is corrected to name `secret` only.
  `rumor` is **not** promoted to a real status: an event either happened or
  did not; what is uncertain is what an NPC *knows*, and that already lives on
  `knowledge.level = 'rumor'`. Putting `rumor` on `event` would blend canon
  with belief.
- **F1** — Flat list, `recorded_at DESC` (the API's ordering; never re-sorted
  client-side, per the intrigues rule). Each row: title, `knowledge_status`
  badge, resolved location name, type.
- **G1** — No provenance display. Deferred until a reader demands it; adding
  `source_mutation_id` would be a migration for a column with no consumer.
- **H2** — `involved_entities` is edited as **chips** (resolved entity name +
  ✕ to remove) with an `entity_ref` picker to add. JSON remains the storage
  format and is never the editing format. Nia does not author JSON; the
  assistant proposes the contents and she corrects by click.
- **I2** — The AI draft returns `title`, `description`, `type`, `location_id`
  and `involved_entities`, the latter two **resolved by name** against the
  world's entities. An unresolved name lands in the draft's `notes` and is
  **never invented** into an id. `knowledge_status` is **absent from the JSON
  contract** and is forced to `secret` on creation: the model must never
  choose what the world knows, and under C3 `knowledge_status` is also the
  sole retraction lever. Creator promotes `secret -> public` by an informed
  click.
- **J3** — The assistant reads: the brief, the pre-selected location's public
  context, and a **name roster** (`name` + `type` only, no description) of the
  world's entities. Required for name resolution in I2. The roster MUST be
  filtered at query construction on `Entity.status == 'active'` AND
  `Entity.is_public IS TRUE` — not post-filtered in Python as
  `context.py:615` does — and MUST NOT carry `internal_name`.
- **`event.type` vocabulary** (`kind: 'datalist'` — suggestions plus free
  text, the `location_type` / `faction_type` precedent):
  `bataille`, `catastrophe`, `festival`, `découverte`, `traité`,
  `disparition`.

## Brief decomposition

- **BRIEF-0022-a — `evenements-creator-tab`**
  `/api/events` (GET list, GET detail, POST, PUT) in `cockpit/crud.py` ·
  `write_event_update` in `writes.py` · `CREATION_TABS.evenements` entry ·
  `listLoader` / `listRenderer` / `sheetRenderer` / `createPanel` ·
  `involved_entities` chip editor · `context.py` ordering fix (finding 7) and
  docstring fix (finding 8). **No migration.**

- **BRIEF-0022-b — `event-draft-assistant`**
  `entity_author.generate_event_draft` (generate-and-return, writes no canon) ·
  `PROMPT_REGISTRY["event_generation"]` entry · `POST /api/events/generate` ·
  "Générer avec l'IA" panel inside the `createPanel` ·
  `scripts/apply_ticket_0022_prompt_updates.py` + `pt-event-draft` upsert in
  `seed_pilot.py`.

## Scope OUT (both briefs)

1. `has_magic_impact`, `consequences`, `session_id`, `batch_id` — no reader,
   not exposed, not written.
2. Event deletion, in any form (C3).
3. `source_mutation_id` / provenance display (G1).
4. In-fiction time: `occurred_at` and any `passé | en_cours | à_venir` status.
   These are ONE deferred chantier, not two — a "future" event is simply one
   whose `occurred_at` lies ahead of world time, so splitting them would cost
   two migrations where one suffices. Reactivate when Nia opens it.
5. A `rumor` knowledge_status (R1).
6. Any change to `_apply_mutation`'s `event_creation` branch or to its
   canon-existence duplicate guard.
7. Filters or grouping on the event list (F2 / F3 rejected for now).

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] CREATION_TABS `evenements` entry exists with `archetype: 'entity'` and `containers: ['creation-editor-area']`  ->  verify/checks/page_contract.py
- [ ] `showCreationSubTab` body contains no tab-id string literal and no per-tab conditional  ->  verify/checks/page_contract.py
- [ ] `Event(` is constructed nowhere outside `writes.py`  ->  verify/checks/single_canon_write.py
- [ ] `writes.write_event_update` exists; `/api/events` PUT handler contains no direct attribute assignment to an `Event` row  ->  verify/checks/single_canon_write.py
- [ ] No route, handler or JS function performs an event delete: no `DELETE /api/events` route registered  ->  verify/checks/event_tab.py
- [ ] `Event.occurred_at` appears in no `order_by` in `src/`  ->  verify/checks/event_tab.py
- [ ] `entity_author.generate_event_draft` exists, and `writes.` / `session.add` / `db.add` never appear inside its body  ->  verify/checks/event_assist.py
- [ ] The `generate_event_draft` returned dict has no `knowledge_status` key  ->  verify/checks/event_assist.py
- [ ] `pt-event-draft` upsert present in scripts/seed_pilot.py with usage `event_generation`  ->  verify/checks/event_assist.py
- [ ] Route `POST /api/events/generate` registered in the cockpit app  ->  verify/checks/event_assist.py
- [ ] The J3 roster query filters `is_public` in its `where` clause and selects no `internal_name`  ->  verify/checks/event_assist.py

### Live  ->  human gate (Nia)
- [ ] The Événements tab renders the shared list+detail shell: event list left, sheet right, visually indistinguishable from NPC / Lieux / Factions
- [ ] The list shows events already produced by the tick (title, status badge, location name, type), newest first
- [ ] Clicking an event opens its sheet; editing title / description / type / location / status and saving persists, and the change survives a reload
- [ ] `involved_entities` renders as named chips, never as raw JSON; adding and removing a chip persists
- [ ] Setting a `public` event back to `secret` makes it vanish from the MJ's public-events context on the next scene
- [ ] No delete control exists anywhere on the page
- [ ] "+ Nouvel événement" opens the create panel; typing an intent and clicking "Générer" pre-fills title, description, type, location and involved-entity chips; unresolved names appear as notes, not as chips
- [ ] A newly created event is born `secret` regardless of what the model returned
- [ ] World switch clears the event list, the selection, and any draft form state
