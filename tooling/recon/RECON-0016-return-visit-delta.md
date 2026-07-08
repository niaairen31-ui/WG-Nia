# RECON-0016 — return-visit-delta (visit table + change narration at enter_scene)

Date: 2026-07-08
Branch inspected: `main` (post TICKET-0015 merge; schema head v1.70,
world-engine-schema.md:3; TICKET-0015 closed, live-gate validated)
Mode: report-only. No actions taken.

Locked decisions in force: G2 (visit table over conversation-derived anchor),
delta injected at enter_scene, structural exclusion doctrine, append-only
writes.

---

## F1 — The deferral is named in code, and the injection point is exact

`cockpit/app.py:4211-4213` — the entry-narration comment reads: "fired on
EVERY entry, not just genuine transitions — no change-detection (G2
deferred)". `enter_scene` (app.py:4160) already separates the two cases this
ticket needs:

- Genuine transition: `if not open_g:` (app.py:4189-4210) — open-gathering
  emptiness is the existing detector for a real location entry vs an F5
  re-render (contract B1/C1). The visit write AND the delta computation
  belong inside this block.
- Every entry: `_build_establishment_narration(...)` (app.py:4214) fires
  unconditionally. The delta rides into it as a new optional argument —
  `None` on re-renders, so a refresh narrates the scene without changes.

## F2 — The establishment pipeline has one builder, one user-message
## assembler, one seeded template; all three are version-safe to extend

- `_build_establishment_narration` (app.py:2045-2090): loads the
  `mj_establishment` template (`_load_mj_establishment_template`,
  app.py:1997), gathers `entity.description`, `_SAFE_SUBCULTURE_KEYS`
  slice, `active_signposts`, calls `_build_establishment_user`
  (app.py:2014-2043), one non-streamed chat; any failure returns None and
  never blocks scene entry (resilience doctrine — the delta inherits it
  for free by riding this call).
- `_build_establishment_user` does verbatim `str.replace` on
  `{location_name}/{description}/{subculture}/{signposts}` — a new
  `{changes}` variable follows the same mechanism; signature gains
  `changes: Optional[list[str]] = None` with the French placeholder
  when None/empty.
- Template seeded at scripts/seed_pilot.py:655-686 (system) / 677-686
  (user), registered at seed_pilot.py:1398-1413, `usage="mj_establishment"`,
  `world_id=None`. The head EXISTS on the live DB (BRIEF-17) -> the
  delivery script needs the append-a-version branch only (0014/0015
  precedent).

## F3 — CONFLICT: the current system prompt forbids naming ANY NPC

seed_pilot.py:669-671 — "=== RÈGLE — AUCUN PNJ NOMMÉ === Ne nomme et ne
décris aucun personnage présent." Narrating "Reike n'est plus là" violates
the rule as written. The new prompt version must scope the rule: NPCs named
in the CHANGEMENTS block (departures/arrivals) MAY be named — because
departures are shown NOWHERE else, which is this ticket's entire point —
while presently-present NPCs remain unnameable (they are shown by the
roster UI, the original rule's rationale). Plus an anti-invention clause
mirroring the signposts rule (seed_pilot.py:661-665): an empty CHANGEMENTS
block means no change is mentioned, never invented.

## F4 — Event leg: the exclusion filter has exactly one precedent, and the
## default is `secret`

`models.py:607-631` — `Event.knowledge_status` defaults to `'secret'`
(server_default, models.py:618-621); `location_id` and `occurred_at` are
nullable; `recorded_at` is always set (`_created_ts`). The ONLY existing
Event reader, `context.py:533-538`, filters
`Event.knowledge_status.in_(("public", "confirmed"))`. The delta's query
must apply the SAME filter at query construction (structural exclusion) and
anchor on `recorded_at > previous_visit.entered_at` — `occurred_at` is
nullable and represents in-fiction time, `recorded_at` represents "when the
world learned of it", which is the correct axis for "since you were last
here". Note: no producer writes Event rows today — this leg is a
forward-reader that renders empty until the event producer ships, and gives
it a perception channel on day one.

## F5 — Presence predicate: reuse the tick's location-scope shape verbatim

`cockpit/app.py:4795-4808` (location-scoped tick resolution) is the
canonical "who is publicly at this location" predicate:
`Character.current_location_id == location_id`,
`character_type == "npc"`, `vital_status == "alive"`,
`Entity.status == "active"`, world-scoped via join. The snapshot writer and
the "current" side of the diff use this predicate. The DEPARTED side
resolves names from `Entity` WITHOUT the alive/active filters — an NPC who
died or was deactivated since the last visit still gets its absence named
(the player saw them; their absence is public information).

## F6 — Migration precedent for a new table is v1.69, not v1.70

`scripts/migrate_v1_69_npc_goal.py` is the new-table precedent
(CREATE TABLE + index, idempotent via inspector); migrate_v1_70_tick_id.py
(read this recon's tarball at scripts/migrate_v1_70_tick_id.py:1-45) is the
ALTER-column shape. v1.71 follows the v1.69 shape: `visit` table + composite
index `(player_id, location_id, entered_at)` for the latest-visit lookup.
Schema head confirmed v1.70 (world-engine-schema.md:3) — TICKET-0015 shipped
without a bump as planned.

## F7 — Transaction and ordering inside the genuine-transition block

Order inside `if not open_g:` — (1) read previous latest visit, (2) compute
presence snapshot + diff lists + event lines, (3) `_enter_location(...)`
(app.py:4209 — dissolves/creates gatherings; touches `gathering_member`,
never `current_location_id`, so it cannot perturb the presence read), (4)
append the new Visit row. The delta must be computed from the PREVIOUS row
before the new one is appended — compute-then-append, single request-scoped
session, same commit discipline as the surrounding code. `left_convs`
window analysis (app.py:4195-4207) stays first, untouched.

## F8 — Verify surface: no existing check covers Visit; two rules suffice

`tooling/verify/checks/` has no visit/establishment coverage. A new
`visit_delta.py` check needs exactly: (rule 1) `Visit(` constructor calls
appear only in `cockpit/app.py` (AST scan, same allowlist idiom as
world_tick.py:45-49), and no `db.delete` receives a Visit-typed name /
no attribute assignment on a loaded Visit outside its creation (append-only
guard); (rule 2) in the delta helper, the `select(Event)` call chain
textually references `knowledge_status` (exclusion is structural —
same spirit as the secret-exclusion checks on the assemblers).

---

## Summary of corrections to TICKET-0016 intake

None — intake was drafted post-recon this time; F3 (prompt rule conflict)
and F4 (recorded_at axis, secret default) are already encoded in it. The
brief carries the reversible drafting decisions.
