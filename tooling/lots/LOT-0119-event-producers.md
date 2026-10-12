# LOT — TICKET-0119 "What happens in the world, proposed by every producer: a type's effects on the state of the world, the tick's and Journée's typed events, Lore declaring events, one event editor"

## Objective and cut

TICKET-0114 made `event` the world's journal; Play's analyzer alone proposed
typed events. This lot makes every producer speak the journal's language
and closes the loop with the state of the world (TICKET-0113):

- an event TYPE declares its EFFECTS (M-c, C1): « Ouvrir : Cible -> Ouvert =
  oui », « Usurper : Trône -> Occupé par = l'Usurpateur », « Être repéré :
  Garnison -> Alerte + 1 » (D3), « Tuer : Victime -> État vital = mort »
  (E1) -- data in the world's vocabulary, edited in « Vocabulaire du monde »;
- an event carries its CHANGES, pre-filled from its type's effects and
  edited by the creator, written with it all or none (F1); a change of a
  world's state is a `changement` naming its event (`attribute_change.
  event_id`); the vital state and the status are written by their own
  writer, an approved proposal keeping their before and after;
- ONE event editor (H1) serves the journal's sheet, the review card of a
  proposed event (Y2: approved as edited) and Lore;
- the world tick proposes typed events by code, role and name, never a new
  type (A1);
- Journée proposes the event a completed step's objective names (Bt1),
  nothing invented;
- Lore declares events: in the writing panel's proposal (a type the world
  lacks created from its card first) and by a button straight to the
  journal (U1, G3).

The lot stops before: Journée proposing a QUEST from the player's day
(B-b) -- the planner writing full-language objectives and proposing types,
and the creator picking the giver -- TICKET-0121; a history table for the
vital state and the status (E: the approved proposals keep their before and
after for it); effects on a SORTE (an effect on a role a sorte fills
changes nothing); the dashboard (0115); the calendar (0120).

## Briefs in this lot

- **A — a type's effects, v2.26** (schema v2.26,
  `BRIEF-0119-A-type-effects.md`): `models/canon_event.py`
  `EventTypeEffect`, `attribute_change.event_id`, `lore_entry_row`'s tables;
  `writes/event_types.py` (`EffectSpec`, `EFFECT_SYSTEM_KEYS`,
  `_clean_effects`, `_write_effects`); `event_vocab.py` (`EffectView`);
  `writes/attributes.py` (what an effect holds, `event_id`);
  `migrate_v2_26_event_effects.py`; check `event_effects.py` (EF1-EF5).
- **B — the effects in « Vocabulaire du monde »** (no schema change,
  `BRIEF-0119-B-effects-form.md`): `routes/event_types.py` (`EffectBody`,
  `states`, a type's `effects`); `EventTypeForm.svelte`,
  `eventVocab.svelte.js`; EF6-EF7 in `event_effects.py`.
- **C — an event writes its changes** (no schema change,
  `BRIEF-0119-C-event-changes.md`): `writes/events.py` (`StateChangeSpec`,
  `record_event`, `WrittenEvent`), `writes/entity_states.py`,
  `event_changes.py`; `event_payloads.py`, the applier, `event_analysis.py`
  (Play pre-fills), `crud/events.py`; check `event_changes.py` (EM1-EM6).
- **D — one event editor; the review card** (no schema change,
  `BRIEF-0119-D-event-editor.md`): `EventEditor.svelte`,
  `eventDraft.svelte.js`, `Evenements.svelte`, `QueueCard.svelte`,
  `queue.svelte.js`, `Sheet.svelte`; `POST /api/events/changes`; a card's
  `scopes`; check `event_editor.py` (EY1-EY3).
- **E — the tick's typed events** (no schema change,
  `BRIEF-0119-E-tick-events.md`): `tick_events.py`, `tick_normalize.py`,
  `tick.py`; the seed's tick prompt and
  `apply_ticket_0119_tick_prompt.py`; check `event_tick.py` (ET1-ET5).
- **F — Journée's objective events** (no schema change,
  `BRIEF-0119-F-day-events.md`): `day_events.py`, `day_mutations.py`,
  `conditions.leaf_since`; check `event_day.py` (EJ1-EJ3).
- **G — Lore declares events** (no schema change,
  `BRIEF-0119-G-lore-events.md`): `lore_write_draft.py`,
  `lore_write_apply.py`, `lore_write_read.py`; `WritePanel.svelte`,
  `writePanel.svelte.js`; the seed's Lore prompt and
  `apply_ticket_0119_lore_prompt.py`; check `event_lore.py` (EL1-EL4).

## Dependency graph

Strictly sequential, A -> B -> C -> D -> E -> F -> G.

- B edits what A stores (C-01, C-02). C's pre-fill reads A's effects
  (C-02) and writes through A's `event_id` (C-01). D's editor posts C's
  changes (C-04) and reads B's `states` (C-03). E, F and G each produce C's
  payload (C-05); G renders D's editor (C-06) and records C's rows
  (`record_event`, C-04) in A's `lore_entry_row` tables (C-01).
- Textual chaining makes the order strict anyway: every brief appends to
  `tooling/standards/ARCHITECTURE_DECISIONS.md` above its footer; A and B
  `event_effects.py`; D and G `EventEditor.svelte`, `eventDraft.svelte.js`;
  E and G `scripts/seed_pilot.py`.
- **Order by decision, not dependency:** E before F before G follows the
  ticket's cut (the tick first, then Journée, then Lore); none of the three
  reads another.

## RECON

Opened on `main` at `b512f2d` (merge of PR #146, `ticket/0114`), schema
v2.25, next id `0119` (Nia's). `main` ran the full corpus green: 156/156
(`WORLD_ENGINE_ENV=test`). Then prototyped on a branch (`proto/0119`): each
brief's commit ran its checks and the full corpus green (A 157, C 158, E 160,
G 162), and every named mutation of every brief turned its check red on its
rule. The lot was then replayed from these diffs onto a clean `main`.
Findings tagged [M] were measured. Line numbers are `main`'s.

### R-01 — the event vocabulary and its writer [M]
Opened: `src/world_engine/models/canon_event.py` (the declaring file:
`EventType`, `EventTypeRole`, `EventTypeRoleType`, `EventTypeScope` :110,
`EventSorte`, `EventParticipant` :143; `EVENT_SCOPE_LEVELS` :53, quoted by
the CHECKs); `src/world_engine/writes/event_types.py` (`EventTypeSpec` :85 --
name, domain, roles, counts_quantity, in_chronicle, participants_secret,
scopes; `clean_event_type` :169; `_write_scopes` :270 deletes and
re-inserts a type's scopes; `write_event_type` :278; `ensure_domain_type`
:364); `src/world_engine/event_vocab.py` (`EventTypeView` :66, `_view`
:107, `type_view` :116).
Finding: a type has no effect; its scopes are the full-replace precedent.
Consequence: A adds `event_type_effect` beside the scopes, written whole by
`_write_effects`, read into `EventTypeView.effects`.

### R-02 — the state of the world and its writer [M]
Opened: `src/world_engine/models/canon_attribute.py` (`AttributeChange`
:123 -- value before and after, `kind`, `changed_by`, `changed_at` :141;
no `event_id`); `src/world_engine/attributes.py` (`SYSTEM_ATTRIBUTES` :83:
`sys:vital_status` -- characters, alive/dead/missing/unknown --,
`sys:status` -- every entity, active/inactive/destroyed/missing --,
`sys:magic_status` -- locations; `attribute_view` :167, `world_attributes`
:190, `current_value` :245); `src/world_engine/writes/attributes.py`
(`_clean_update` :195 keeps a choice a value or a condition holds;
`set_attribute_status` :280 refuses retiring while a condition names it;
`write_attribute_value` :338 -- `correction` or `changement`, an unchanged
value writes nothing; :30 « a system attribute is never written here »).
Consequence: A gives `attribute_change` its `event_id` and extends the
in-use guards to effects; system states need their own writer (R-03).

### R-03 — who writes the vital state and the status [M]
Opened: `src/world_engine/cockpit/crud/entities.py` (:138 the
`vital_status` field of the character form; `update_entity` writes it by
`setattr`; :829 an entity leaving `active` closes its gathering seats --
INV-25); `src/world_engine/cockpit/mutations.py:434`
(`_mutation_apply_status_change` sets `entity.status`, closes nothing);
`src/world_engine/gathering.py:283` (`close_open_memberships`, never
commits; `gathering` imports `analyzer`, which imports `writes`).
Enumeration (c-1 below): no play path writes `vital_status`.
Consequence: C adds `writes/entity_states.write_system_state`, which closes
the seats (importing `gathering` inside the function), and never reactivates
a location (a zone promotion is the fiche's, TICKET-0101).

### R-04 — the journal's writer and the applier [M]
Opened: `src/world_engine/writes/events.py` (`EventSpec` :82;
`clean_event` :218; `_knows` :250 and `_add_participants` :267 return
nothing; `write_event` :288 returns the event; `write_event_update` :310);
`src/world_engine/event_payloads.py` (`_typed` :88 reads `type_id` /
`new_type`, participants, quantity, place -- no scopes, no changes;
`spec_from_payload` :132); `src/world_engine/cockpit/mutations.py:694`
(`_mutation_apply_event_creation` -> `write_event`);
`src/world_engine/cockpit/routes/mutations.py:597`
(`_approve_apply_and_commit`: one savepoint, an applier's error string rolls
it back).
Consequence: C writes the changes inside `write_event` (one writer, F1) and
returns every row (`record_event`) for Lore; D reads a card's `scopes`.

### R-05 — Play's typed payload [M]
Opened: `src/world_engine/event_analysis.py` (`analysis_vocabulary` :57,
`AnalysisVocabulary.prompt_values` :52, `typed_payload` :130: `{title,
description, type_id | None, type_name, participants [{role_id, role,
entity_id, sorte_id, sorte_name, secret}], quantity, location_id,
new_type?}`).
Consequence: the tick reuses it whole (E); C adds `state_changes` to it.

### R-06 — the review card and the journal's sheet [M]
Opened: `frontend/src/creation/QueueCard.svelte` (:26 the payload edited as
JSON; :112 `eventSummary`, read-only); `frontend/src/creation/
eventDraft.svelte.js` (:10 a module store; :69 `eventDraftBody()`);
`frontend/src/creation/Evenements.svelte` (type, quantity, participants,
scopes inline); `frontend/src/creation/Sheet.svelte:560`
(`Object.assign(body, eventDraftBody())`); `tooling/verify/checks/
event_writes.py:403` (EC6 pins the sheet's markup in `Evenements.svelte`);
`tooling/verify/checks/event_analyzer.py:332` (EH4 pins `eventSummary` and
the proposed type's badge).
Consequence: D moves the sheet's editing into `EventEditor.svelte` and
retargets EC6 there; the card keeps `eventSummary` for reviewed cards.

### R-07 — the world tick's events [M]
Opened: `src/world_engine/tick_normalize.py` (:431
`_tick_normalize_scope_event_creation`, the untyped shape; :489
`_normalize_scope_event`); `src/world_engine/tick.py` (:305
`_tick_scope_setup` builds `actives_index`; :322 `_tick_call_scope_model`
replaces `{event_context}`, `{interval_label}`; :56 three events per
scope); `scripts/seed_pilot.py` (:1104 / :1130 / :1201 the events prompt,
:3245 its variables); `tooling/verify/checks/world_tick.py` (pins names
inside `_normalize_scope_event`).
Consequence: E types an item in `tick_events.py`, called from
`_normalize_scope_event`; the prompt changes by fragments.

### R-08 — Journée's emission [M]
Opened: `src/world_engine/day_mutations.py` (:91 five
`EMITTED_MUTATION_TYPES`; :107 `_step_action` -- `complete` on success or
partial, None when blocked; :287 `_EMITTERS`); `tooling/verify/checks/
day_mutations.py:93` (R1/R13 pin the five); `src/world_engine/
cockpit/routes/day.py` (`_finalize_resolution` adds every emitted row; R12:
resolving refuses while a step change is proposed); `src/world_engine/
conditions.py` (`Bindings` :86, `for_step` :152, `and_path_leaves` :229,
`_since` :456 private); `src/world_engine/day_plan.py:130`
(`plan_bindings`); `src/world_engine/condition_forms.py:476`
(`counted_events`); `src/world_engine/cockpit/routes/mutations.py:125`
(`_find_event_duplicate`: a conversation-less event is a duplicate by title
and place).
Consequence: F adds `day_events.py` as the sixth emitter, a public
`conditions.leaf_since`, and puts the day's number in the title.

### R-09 — Lore's writing path [M]
Opened: `src/world_engine/lore_write_draft.py` (:124 `_values`, :248
`draft_proposal`); `src/world_engine/lore_write_apply.py` (:178 `validate`
refuses a proposal writing no fact, membership or control; :202 `_Writer`;
:323 `apply_proposal`); `src/world_engine/models/pipeline.py` (:326
`LORE_ENTRY_ROW_TABLES`, :350 its CHECK: seven tables); `src/world_engine/
lore_write_read.py:36` (`_label` maps the seven); `scripts/seed_pilot.py`
(:1910 / :1957 the proposal prompt, :1978 `LORE_WRITE_PROMPT_HEADS`, :1996
its variables); `tooling/verify/checks/lore_write.py:651` (F1b pins the
panel's calls); CLAUDE.md INV-57 (every row recorded).
Consequence: A widens `lore_entry_row`; G records every row an event wrote.

### R-10 — the lists this lot extends [M]
Opened: `tooling/verify/canon_write_policy.txt` (one line per writer);
`tooling/verify/checks/single_canon_write.py` (docstring: the named
full-replace deletes); `src/world_engine/writes/worlds.py:65`
(`_DIRECT_WORLD_SCOPED_DELETES`, :82 the event tables) and
`tooling/verify/checks/world_cascade.py` (W1/W3: every world table in the
list and the fixture); `tooling/verify/checks/attributes.py:123` (AA1/AA6 pin
`attribute_change`'s columns); `src/world_engine/schema_version.py:15`
(v2.25); `.claude/rules/gatherings.md` (INV-25).

### R-11 — fifteen seconds per check [M]
Opened: `tooling/verify/checks/corpus_gate.py`. Measured on the prototype:
`event_effects.py` 5.2 s, `event_changes.py` 2.4 s, `event_editor.py`
2.1 s, `event_tick.py` 6.7 s, `event_day.py` 1.3 s, `event_lore.py` 6.4 s.

## Contract sheet

### C-01 — v2.26
Produced by: BRIEF-0119-A   Consumed by: B-G
`event_type_effect` (`world_id`, `type_id`, `role_id`, `definition_id` XOR
`system_key`, `mode` in `EVENT_EFFECT_MODES = ("set", "add")`, exactly one of
`choice_id` / `system_value` / `integer_value` / `value_role_id`, `add` only
with `integer_value`, `position`; indexes `idx_event_type_effect_type`,
`idx_event_type_effect_definition`); `attribute_change.event_id` (FK
`event`, `idx_attribute_change_event`); `LORE_ENTRY_ROW_TABLES` gains
`event`, `event_participant`, `attribute_value`, `attribute_change`.

### C-02 — a type's effects (writer and reads)
Produced by: BRIEF-0119-A   Consumed by: B, C
`writes.event_types.EffectSpec(role, attribute, value, mode="set")` -- `role`
a role's NAME; `attribute` a definition id or a system key; `value` a choice
key, an integer, or (entity state) another role's NAME;
`EventTypeSpec.effects`; `EFFECT_SYSTEM_KEYS = ("sys:vital_status",
"sys:status")`; `MAX_EFFECTS = 8`. Refused (`ValueError`): an unknown or
retired state, a system state outside `EFFECT_SYSTEM_KEYS`, a role holding
no entity, a state applying to no entity type the role accepts, a value not
of the state's kind, `add` on a non-integer, an entity value naming the
same role or a role the state may not name, one role and state twice.
`event_vocab.EffectView(role_id, attribute, mode, value_kind ("choice" |
"integer" | "role"), value, position)`, `effect_view(row)`,
`EventTypeView.effects`. `write_attribute_value(..., event_id=None)` -- an
`event_id` only on a `changement`. A definition an effect names is not
retired, its kind does not change, its choice an effect names stays.

### C-03 — the vocabulary's routes
Produced by: BRIEF-0119-B   Consumed by: D, G
`EffectBody(role, attribute, mode="set", value: int | str | None)`;
`EventTypeBody.effects`; `type_dict(...)["effects"]` = `[{role (name),
attribute, mode, value (a role's NAME for an entity state)}]`;
`event_vocabulary(...)["states"]` = `[state_dict]` for the two
`EFFECT_SYSTEM_KEYS` and the world's active definitions: `{key, name, kind,
system, holder_types (None: all), value_types, choices [{value, label}]}`.
Frontend: `vocabState.states`; `typeDraft` / `typeBody` carry `effects`.

### C-04 — an event's changes (the journal's writer)
Produced by: BRIEF-0119-C   Consumed by: D-G
`writes.events.StateChangeSpec(entity_id, attribute, value, mode="set")`;
`EventSpec.changes` (default `()`); `WrittenEvent(event, fact, rows [(table,
id, "created" | "updated")], system_changes [{entity_id, attribute, before,
after}])`; `record_event(db, *, world_id, spec, created_by) ->
WrittenEvent`; `write_event` = `record_event(...).event`. Cleaning (all or
nothing): an active state an event may change, an entity of the world it
applies to (a vital state on a character), a value of its kind (`add` on an
integer; an entity value of a type the state names, or None), one state of
one entity once, never a location made active again; a correction
(`write_event_update`) carrying a change is refused. A definition's change:
`write_attribute_value(kind="changement", event_id=event.id)`, `add` summed
on the current value. `writes.entity_states.write_system_state(db, *,
world_id, entity_id, key, value) -> (before, after) | None` --
`SYSTEM_STATE_KEYS`; closes the seats of an entity leaving `active` or a
character leaving `alive`.

### C-05 — pre-fill and payload keys
Produced by: BRIEF-0119-C (D adds `scopes`)   Consumed by: D-G
`event_changes.type_changes(db, world_id, view, [(role_id, entity_id)]) ->
[{entity_id, attribute, mode, value}]` (each entity in the effect's role;
an entity state takes the first entity of its value role, or is left out);
`change_line(db, world_id, change) -> str | None` (« Porte : Ouvert ->
oui », « Garnison : Alerte +1 »); `payload_changes(raw) ->
tuple[StateChangeSpec]`. A typed `event_creation` payload carries
`state_changes`; the applier adds `applied_changes` (the system changes) to
an approved payload; D: `scopes` `[{scope_type, scope_id, level}]` (a list,
even empty, replaces the type's).

### C-06 — the editor
Produced by: BRIEF-0119-D   Consumed by: G
`POST /api/events/changes` (`ChangesBody(type_id, participants
[{role_id, entity_id}], changes [StateChangeBody])`) -> `{prefilled: [...,
line], described: [..., line]}`, reads only; `EventBody.state_changes`.
`EventEditor.svelte` props `{draft, entities, playerCharIds, typeFixed,
withText, withChanges, canPrefill (G)}`; a draft `{typeId, newType,
quantity, participants [{role_id, role, entity_id, sorte_id, sorte_name,
name, secret, saved}], customScopes, scopes, changes, title, description,
locationId}`; `eventDraft.svelte.js`: `blankEventDraft`, `addParticipantTo`,
`removeParticipantFrom`, `prefilledChanges`, `eventDraftBody(isNew)`,
`eventBodyFrom(draft, isNew)` (G), `draftFromPayload`, `payloadFromDraft`.

### C-07 — the tick's typed item
Produced by: BRIEF-0119-E   Consumed by: (none in this lot)
`tick_events.typed_tick_payload(payload_in, *, title, description,
location_id, roster, actives, vocab, db, world_id, notes) -> dict | None |
UNTYPED`; `_normalize_scope_event(..., vocab=None, world_id="")`;
`setup["vocab"]`; `_tick_call_scope_model(..., vocab=None)`. Seed:
`WORLD_TICK_EVENTS_VARIABLES`, `WORLD_TICK_EVENTS_FRAGMENTS_0119`.

### C-08 — Journée's objective event
Produced by: BRIEF-0119-F   Consumed by: (TICKET-0121)
`day_events.emit_objective_events(outcome, pass_play, character, world_id,
db) -> list[ProposedMutation]` (`_EMITTERS["event_creation"]`);
`conditions.leaf_since(spec, bindings)`. Title: « objective — jour N ».

### C-09 — Lore's events
Produced by: BRIEF-0119-G   Consumed by: (none)
Draft item: `{ref v1.., type_id | None, type_name, new_type?, title,
description, quantity, location_ref, participants [{role_id | None, role,
entity_ref | sorte_id, secret}], state_changes [{entity_ref, attribute,
mode, value}]}`; proposal item: the same without `new_type`, plus
`scopes [{scope_type, scope_ref, level}]` when the creator chose them.
Seed: `LORE_PROPOSAL_VARIABLES`, `LORE_PROPOSAL_FRAGMENTS_0119`.

## Gate output

(a) Property trace -- one line per property the briefs assert about `main`:
- a type's scopes are written whole by `_write_scopes` -> R-01,
  `writes/event_types.py`.
- `EventTypeView` carries roles and scopes, no effects -> R-01,
  `event_vocab.py`.
- the three system attributes and their values -> R-02, `attributes.py`
  (`SYSTEM_ATTRIBUTES`, the declaring tuple).
- `attribute_change` has no `event_id` -> R-02, `models/canon_attribute.py`.
- retiring a definition is refused while a condition names it -> R-02,
  `writes/attributes.py` (`set_attribute_status`).
- no play path writes `vital_status` -> R-03, enumeration c-1.
- an entity leaving `active` in the CRUD closes its seats -> R-03,
  `crud/entities.py:829`; the status applier does not -> R-03,
  `cockpit/mutations.py:434`.
- `close_open_memberships` never commits -> R-03, `gathering.py:283`.
- `write_event` returns the event only; `_typed` reads no scopes -> R-04,
  `writes/events.py`, `event_payloads.py`.
- the applier runs in one savepoint -> R-04, `routes/mutations.py:597`.
- `typed_payload`'s shape -> R-05, `event_analysis.py`.
- EC6 and EH4 pin the sheet's and the card's markup -> R-06, the checks'
  implementations (`event_writes.py:403`, `event_analyzer.py:332`).
- the tick's untyped normalizer and two placeholders -> R-07,
  `tick_normalize.py`, `tick.py`.
- five emitters, `_step_action`'s bands, R1/R13 pinning five -> R-08,
  `day_mutations.py`, `checks/day_mutations.py:93`.
- `_since` is private; the duplicate guard compares title and place ->
  R-08, `conditions.py:456`, `routes/mutations.py:125`.
- `lore_entry_row`'s seven tables -> R-09, `models/pipeline.py:350`.
- the panel's five calls pinned by F1b -> R-09, `checks/lore_write.py:651`.
- the world cascade lists the event tables; W1/W3 compare -> R-10,
  `writes/worlds.py`, `checks/world_cascade.py`.
- AA1/AA6 pin `attribute_change`'s columns -> R-10,
  `checks/attributes.py:123`.

(b) Case tables.

An effect's value by the state's kind (C-02, EF2):

| state kind | `set` value | `add` | stored in |
|---|---|---|---|
| choice (definition) | one of its choice ids | refused | `choice_id` |
| choice (system: vital, status) | one of its stored values | refused | `system_value` |
| integer | an int | an int | `integer_value` |
| entity | another role's name, whose types the state names | refused | `value_role_id` |
| `Magie` | refused | refused | -- |

A change at write time (C-04, EM2-EM5):

| change | written by | history | seats |
|---|---|---|---|
| definition, `set` | `write_attribute_value` | `attribute_change`, `changement`, `event_id` | -- |
| definition, `add` | the same, current + value | the same | -- |
| `sys:vital_status` | `write_system_state` | the approved payload's `applied_changes` | closed when leaving `alive` |
| `sys:status` | `write_system_state` | the same | closed when leaving `active`; a location never made `active` |

A tick item (C-07, ET3-ET4):

| item | result |
|---|---|
| `event_type` known, names resolved | typed payload, changes pre-filled |
| `event_type` unknown | dropped, note |
| a participant's name nobody bears | that participant left out, note |
| `new_type` only | untyped shape, note (A1) |
| neither | untyped shape (typed by domain at approval) |

A completion leaf in Journée (C-08, EJ1-EJ2):

| leaf | proposes |
|---|---|
| `event`, under `all`, on `doer`, not met, band success/partial | one event |
| band failure / blocked | nothing |
| already met | nothing |
| under `any` / `not` / `at_least` | nothing |
| on `giver` / `contact` / a named entity | nothing |
| « any role » | the type's first role accepting a character |

(c) Enumerations.

c-1 -- writers of `vital_status` on `main` (`grep -rn "vital_status *="
--include=*.py src | grep -v "=="`):

```
src/world_engine/lore_selectors.py:100:                vital_status=character.vital_status,
src/world_engine/gathering.py:70:    Filters: character_type='npc', vital_status='alive', entity.status='active'.
src/world_engine/link_author.py:103:    Roster = characters with character_type='npc', vital_status='alive',
```

None writes: the column is set only by `update_entity`'s generic `setattr`
from the character form's `vital_status` field (`crud/entities.py:138`).

c-2 -- assignments of an entity's status on `main` (`grep -rn "\.status = "
src/world_engine | grep -i "entity\."`):

```
src/world_engine/cockpit/mutations.py:455:    entity.status = str(new_status)
src/world_engine/cockpit/crud/__init__.py:28:- Entities: **soft delete** (`entity.status = 'inactive'`) — reversible,
src/world_engine/cockpit/crud/entities.py:863:    entity.status = "inactive"
```

(`update_entity` writes it through `_apply_base_fields`.)

c-3 -- callers of `close_open_memberships` on `main`:

```
src/world_engine/cockpit/mutations.py:688:    close_open_memberships(npc_id, db)
src/world_engine/cockpit/crud/entities.py:827:        closed += close_open_memberships(entity_id, db)
src/world_engine/cockpit/crud/entities.py:830:        closed += close_open_memberships(entity_id, db)
src/world_engine/cockpit/crud/entities.py:866:    closed = close_open_memberships(entity_id, db)
src/world_engine/cockpit/crud/zone_hooks.py:56:        closed.extend(close_open_memberships(being["id"], db))
src/world_engine/gathering.py:452:    active_rows = close_open_memberships(npc_id, db)
```

(d) Every family contract (C-02's effect kinds, C-04's change kinds, C-07's
item shapes, C-08's leaf cases) was written before its members and re-read
after the last: tick.

(e) Gates proposed and the module satisfying each:
`event_effects.py` -> `models/canon_event.py`, `writes/event_types.py`,
`writes/attributes.py`, `migrate_v2_26_event_effects.py`,
`routes/event_types.py`, `EventTypeForm.svelte`, `eventVocab.svelte.js`;
`event_changes.py` -> `writes/events.py`, `writes/entity_states.py`,
`event_changes.py`, `event_payloads.py`, `cockpit/mutations.py`,
`event_analysis.py`, `crud/events.py`; `event_editor.py` ->
`crud/events.py`, `event_payloads.py`, the four frontend files;
`event_tick.py` -> `tick_events.py`, `tick_normalize.py`, `tick.py`,
`seed_pilot.py`, `apply_ticket_0119_tick_prompt.py`; `event_day.py` ->
`day_events.py`, `day_mutations.py`; `event_lore.py` -> `lore_write_*.py`,
`seed_pilot.py`, `apply_ticket_0119_lore_prompt.py`, the Lore panel.
Gates merely passed, retargeted in the brief that moves their subject:
`attributes.py` (A), `world_cascade.py` (A), `single_canon_write.py` (A, C),
`event_writes.py` EC6 (D), `day_mutations.py` R1/R13 (F), `lore_write.py`
F1b (G), `event_editor.py` EY3 (G).

## Amendments

(none)
