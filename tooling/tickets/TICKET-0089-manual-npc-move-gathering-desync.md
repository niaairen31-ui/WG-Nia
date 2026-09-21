---
id: TICKET-0089
title: Manual NPC move leaves the gathering roster behind
type: bug
status: brief
created: 2026-09-18
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: [db_write]
blast_radius: medium
lot_id: LOT-0089-manual-npc-move-gathering-desync.md
brief_ids: [A, B, C, D, E, F, G]
current_brief:
schema_version_touched:
retry_count: 0
---

## Request (verbatim, as Nia stated it)

> lorsque je joue en monde play, et que je deplace des NPC manuellement, j'ai
> encore des problemes. a l'heure actuelle, j'ai deux NPC que je ne suis plus
> en mesure de retrouver. Ils sont supposes etre dans un Current location X et
> n'y sont pas. Je peux me joindre a un gathering dans ce lieux, mais il n'y a
> pas de NPC present, la narration est vide.

## Clarifications resolved (intake)

Decision session of 2026-09-18, against a fresh RECON of `main`, a read-only
measurement of the production database (seven queries, run by Claude Code),
and a reproduction on a throwaway SQLite carrier. Locked codes:
`A1, B3, C1, D1, E3, F1, G1`.

**The defect is a desynchronisation, not a data loss.** Both NPCs carry the
correct `current_location_id`. Play-side presence is read from
`gathering_member`, never from `current_location_id`; the only code that
turns one into the other is `enter_location`, and its single live caller
runs it only when the location has zero open gatherings. A creator-side
location edit closes the NPC's membership without dissolving the gathering
it empties, so an open gathering with no active member survives and blocks
regeneration for the rest of the session. Both NPCs are at "Chambre " and
invisible; the gathering the player can still join is that empty shell.

**A1 -- the live partie is unblocked by code, not by a data repair.** The
guard fix makes `enter_location` run again at that location; it dissolves the
stale shells itself and regenerates the partition from `current_location_id`.
No write against the production carrier is authorised by this ticket.

**B3 -- the fix is placed at both ends.** The enter guard counts only
gatherings with at least one active member (repairs the existing state), and
a gathering left empty is dissolved at the moment it is emptied (prevents the
state from forming again). Rejected: filtering empty gatherings inside
`_open_gatherings` itself -- six readers depend on it. Reactivation condition:
a third reader must ignore an empty gathering.

**C1 -- the creator-side location write owns both ends of the move.** It
already closes the origin membership; it now also attaches the NPC at the
destination when that location is live in the open session. Without this,
an NPC moved into the room the player is standing in stays invisible, because
a non-empty gathering there legitimately blocks regeneration.

**D1 -- the six NPCs with a NULL `current_location_id` are left alone.**
Measured, not repaired: nothing establishes they were erased rather than
authored that way. No verify check is added for them by this ticket.
Reactivation condition: a seventh appears, or one is shown to have been
erased by a sheet save.

**E3 -- the silent NULL path is closed at both ends.** A `PUT` whose
extension omits a key no longer erases the stored value, and the sheet's
`entity_ref` control no longer falls back to the empty option when the
current value is absent from its candidate list. Neither is proven to have
fired in production; both are reachable by construction.

**F1 -- `crud/entities.py` is at exactly 1000 lines.** The module budget caps
it there and no baseline file exists, so any added line fails the corpus.
A pure-move extraction of the location geometry/doors write routes precedes
every brief that adds a line to that file.

**G1 -- one dissolve behaviour, window analysis included.** The extracted
helper analyses the open conversations of a gathering before dissolving it,
on every caller, exactly as `migrate_npc` does today. Reactivation condition
for a parameterised variant: a measured slow sheet save traced to this call.

## Decisions locked (do not re-litigate without Nia)

- Play-side presence stays gathering-derived. `current_location_id` is not
  read at scene assembly time, and this ticket does not change that.
- An empty open gathering is a defect state, not a legal one. It is dissolved
  where it is created, and ignored by the entry guard where it survives.
- A gathering created on arrival is always solo. Code never asserts that an
  arriving NPC joined an existing social cluster; the MJ partition is the
  only authority for that, and it runs at entry.
- The creator-side arrival never opens a session. A location with no open
  session, or with no open gathering, is left to the normal entry path.
- No write against the production database is part of this ticket. The live
  gate is passed by playing, not by repairing rows.

## Carried forward / open

- The six live NPCs with a NULL `current_location_id` (measured 2026-09-18:
  Kaelin Vex, Kael, Le Comte Vixsen, Kaelin 'Lune' LaFleur, Mira, Sir
  Reginald Voss). D1 leaves them as they are. If a later session decides they
  must be placed or flagged, that is its own ticket.
- Entity names are stored untrimmed (`"Chambre "` carries a trailing space;
  `_coerce_field`'s text branch returns `str(raw)` with no `strip()`). Out of
  scope here -- a separate ticket, since it touches every entity write path.
- `tooling/verify/run.py` reads only the first arrow per line
  (`LINK.search`), so a criterion naming two checks silently runs one. Known
  since TICKET-0087; every line in this ticket carries exactly one arrow.
  A repair to `run.py` is its own ticket.
- `routes/mutations.py` imports `enter_location` and `migrate_npc` with no
  call site. Dead imports, left in place; removing them is not this ticket's
  work.
- `json_ui_boundary.py`'s volet (a) names two end markers -- `# -- Type` and
  `# -- Relation / knowledge field specs` -- that exist nowhere in
  `crud/entities.py`. `_extract_between` falls back to "start marker to end of
  file", so the volet scans the whole file tail instead of two bounded blocks.
  It is green today and stays green through this lot. Repairing it means
  deciding whether to add the markers or to change the check, which is a
  ticket of its own.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] Every check in the corpus runs and passes  -> verify/checks/corpus_gate.py
- [ ] No file over 1000 lines, no module over 40 functions  -> verify/checks/module_budget.py
- [ ] No function over 80 lines  -> verify/checks/function_length.py
- [ ] The geometry/doors extraction leaves no undefined name behind  -> verify/checks/undefined_names.py
- [ ] `crud/entity_geometry.py` introduces no module-level import cycle  -> verify/checks/import_cycle.py
- [ ] The entity type registry and its two markers still live in `crud/entities.py`  -> verify/checks/json_ui_boundary.py
- [ ] The committed frontend build matches the sources after the `Field.svelte` change  -> verify/checks/frontend_build_fresh.py
- [ ] The committed static assets are the ones the build produced  -> verify/checks/static_asset_freshness.py
- [ ] CLAUDE.md stays within its character budget and its invariant section stays reference-free  -> verify/checks/claude_md_contract.py
- [ ] `DECISIONS_INDEX.md` equals a fresh regeneration and the new header matches the strict pattern  -> verify/checks/decisions_index.py

### Live  ->  human gate (Nia)

- [ ] On Verkhaal, entering "Chambre " shows "La Reine des ombres" and "Lily"
      in the Groupes presents list, with their labels, and the join produces a
      narration naming them.
- [ ] Moving an NPC out of the room the player is standing in makes it
      disappear from the scene on the next refresh, and the gathering it
      leaves behind is gone rather than empty.
- [ ] Moving an NPC into the room the player is standing in makes it appear on
      the next refresh, in its own group, without leaving and re-entering.
- [ ] Saving an NPC sheet from the Creation tab leaves the Current location
      field exactly as it was shown, including when the location list had not
      been reloaded in that session.
- [ ] A sheet save is not perceptibly slower than before the change.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
