---
id: TICKET-0074
title: NPC schedules — npc_schedule, the world phase, and the two reads the day-resolution chain needs
type: feature
status: live-gate
created: 2026-08-23
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
brief_ids: [BRIEF-0074-a, BRIEF-0074-b, BRIEF-0074-c]
schema_version_touched: v1.91 -> v1.92
retry_count: 0
---

## Request (verbatim, as Nia stated it)

From the schedule design conversation carried in
`HANDOFF-0074-npc-schedules-final-decision-pass.md` (predecessor TICKET-0073,
merged, schema v1.91). Decision codes returned during that pass:

> A1a, B1, C1, D1/H1, E1, F1, L1, I2

Closing pass, 2026-08-23:

> T-A1, pour la sous question, a me semble approprié, mais confirme moi que si
> je choisi de mettre des calendrier et des horloge dans mes mondes, je vais
> pouvoir en avoir un par défaut, ou que je vais pouvoir avoir un
> horloge/calendrier spécifique par monde. (l'implémentation de cela est 100%
> scoop out pour le moment).

> T-B1, T-C1, T-D2, T-E1, T-G1, S-I 1, S-F scope out ecplicite.

## Clarifications resolved (intake)

**The problem.** TICKET-0073 gave an NPC a standing occupation — a reason to be
somewhere — but nothing says WHERE that somewhere is, or when. The day-resolution
chain (K3, neighborhood-scoped tick) cannot scope a tick without knowing who is
plausibly at a location at a given time, and there is no read that answers it.
Today the only positional truth is `character.current_location_id`, a fact about
right now that says nothing about a phase three days out.

**Background versus foreground (J1, upstream).** A schedule is the background;
an agenda is the foreground. One accessor, one code path, the earshot precedent.
Rejected: J2 (schedule as a recurring agenda — an agenda has a terminal status
and at most one active step, a routine has neither); J3 (last known position
only — the failure this ticket exists to fix).

**Phase vocabulary (A1a).** Four named cycle phases: `matin`, `apres-midi`,
`soir`, `nuit`. Own frozen constant `SCHEDULE_PHASES`, machine-checked on the
`INTERVAL_HOP_RADIUS` idiom (`tick_context.py:85`, asserted by
`world_tick.py:427-449`). No calendrical axis in v1. Rejected: A2 (phase +
nullable `day_kind` — no world clock exists to evaluate it; reactivation
condition: *a world-clock ticket has shipped a readable day counter*); A3
(numeric slot index — unreadable in prompt and UI); A4 (reuse
`interval_label` — `INTERVAL_HOP_RADIUS` is a DURATION axis, a BFS hop bound
on `connects_to`, not a phase axis, and `world_tick.py` fails if its key set
changes).

**Coverage (B1).** Sparse table. The fallback is declared inside the accessor;
coverage is a REPORT, never a check failure. Rejected: B2 (fail-closed full
coverage — the seeding migration would invent canon at scale by script, which
"the model proposes, code judges" forbids); B3 (`is_scheduled` cohort flag —
its only reader would be the check that reads it).

**Precedence (C1).** Time-relative, two branches, one accessor.
- Present phase: gathering membership > `current_location_id` > active agenda
  step > schedule > terminal.
- Future phase: active agenda step > schedule > `current_location_id` (last
  known) > terminal.

Each branch is an ordered module-level tuple; the accessor iterates it and
dispatches through a name-keyed table; a check asserts the accessor performs no
source lookup outside that table. `resolution.source` names the winning term.
Rejected: C2 (single total order — lets a stale `current_location_id` beat the
schedule for a phase three days out); C3 (schedule always wins with overlays at
call sites — violates J1).

**Row shape (D1/H1).** `npc_id`, `phase`, `location_id`, nullable
`standing_goal_id` FK to `npc_goal`. Plus `world_id` (every canon table carries
it) and timestamps. Nothing else. Rejected: free-text `activity` (no reader;
TICKET-0073 gave it a typed home instead); frozen `activity` enum (reactivation
condition: *the resolution chain's matching pass names the activity as an
input*); `gathering_id` (a gathering is ephemeral and already outranks the
schedule in the present branch — a pointer to a fact, stored in a table of
defaults).

**Authorship (E1).** Creator CRUD only. One new write site,
`writes/config.py::write_npc_schedule`, full-replace per NPC, on the
`write_location_doors` idiom (`writes/config.py:296`). `schedule_change` and
auto-approve are deferred and gated on a real proposer existing. Rejected: E2
(Creation UI emits its own mutation — creator CRUD IS a sanctioned canon-write
path; making it propose to itself inverts the two-path doctrine); E3 (derived
from role or faction — invents canon by rule, and needs a role->location table
that does not exist).

**First reader (F1).** `who_is_at(location_id, phase)` rendered as a
"who is here, by phase" panel on the Creation location sheet, plus a CLI
companion `scripts/preview_npc_schedule.py` on the `preview_tick_context.py`
precedent (`scripts/preview_tick_context.py`, 64 lines). The panel is the
compensating control for B1: with no coverage check, empty phases must be
visible to the author before a player walks into one.

**Source of "now" (T-A1).** L1's concordance test needs a current phase and
nothing in the tree supplies one — a grep across `src/` for
`current_phase|world_day|day_index|game_time|world_clock|time_of_day` returns
zero hits, and `World` (`models/canon.py:64`) carries no temporal state. The
phase becomes a creator-set column on `world`, four legal values, advanced from
a cockpit control. Two conditions ride with the decision and are not optional:

1. **Compensating control.** A forgotten phase mis-renders L1 silently, which is
   a disciplinary safeguard, and the doctrine refuses those. The remedy is the
   same shape B1/F1 already use: the current phase is displayed permanently in
   the cockpit chrome, so "forgotten" is visible rather than mute. Without the
   display, T-A4 (defer L1 entirely) was the correct choice instead.
2. **Advancing the phase moves nothing else.** A bare state write: no tick, no
   cascade, no recomputation. The day-resolution chain stays Scope OUT, and a
   check asserts the write site calls nothing beyond its own commit.

Rejected: T-A2 (derive from wall-clock time — couples fiction to real time,
breaks the moment a session runs past midnight; no reactivation, the engine is
turn-based); T-A3 (phase on `conversation` — cannot be the only source, since
`who_is_at` on the Creation surface has no conversation; *non-foreclosure:
`conversation.phase_snapshot` stays an additive migration later, no existing row
rewritten*); T-A4 (defer L1 — the real contender, retained as the fallback if
condition 1 is ever dropped).

**Per-world clocks, confirmed (answer to Nia's question).** The phase lives on
the `world` ROW. Two worlds are two rows, so two independent phases, by
construction — not by a rule anyone has to remember. A future `world_calendar`
keyed on `world_id` is purely additive and touches nothing this ticket ships,
and "a default calendar" is not a special case: it is a `world` row whose
calendar FK is NULL, resolved to a module default — the same fallback idiom B1
already uses for missing schedule rows. Implementation of calendars and clocks
is 100% Scope OUT here.

**Vocabulary enforcement (T-G1).** A named `CheckConstraint` against the four
literals, on the `ck_npc_goal_kind` precedent (`models/canon.py:502`), at both
sites: `npc_schedule.phase` and `world.current_phase`. Cost if per-world phase
vocabularies are ever wanted: SQLite cannot `ALTER` a CHECK, so it would mean a
create-copy-drop-rename inside a calendar ticket already doing schema work.
Accepted. Rejected: T-G2 (FK to a `schedule_phase` catalogue on the
`location_type_catalog` precedent — equally structural, cheaper to extend, but
costs a table, a seeding migration and a catalogue-CRUD question today;
*reactivation condition: a ticket needs different phase vocabularies per
world*); T-G3 (unconstrained TEXT validated at the write site — disciplinary,
not structural).

**Model placement (T-B1).** `models/canon.py` measures 993/1000 lines and
`tooling/verify/baselines/module_budget.json` does not exist, so the cap is
enforced with no exemption. `npc_schedule` lands in a new
`src/world_engine/models/schedule.py`, on the exact precedent recorded verbatim
in `models/config.py:1-8` — a curated-config table split out of `canon.py` for
budget reasons, not because it belongs to a different stratum. The
`world.current_phase` COLUMN cannot be split out the same way (a column lives on
its class) and lands in `canon.py`, inside its 7-line margin, under a hard STOP.
Rejected: T-B2 (extend `models/config.py` — the module is named and documented
for the conversation-window config specifically); T-B3 (an extraction brief on
`canon.py` first — *reactivation condition: brief -a's STOP fires, in which case
the extraction becomes mandatory and lands as BRIEF-0074-0 before -a*).

**Authoring surface (T-C1).** An authoring island on the NPC sheet, "the day of
X": four phase rows, each a location picker. Matches E1's full-replace-per-NPC
shape and matches how a creator thinks — one authors a character's day, not a
location's footfall. The location sheet carries the read-only F1 panel, so
authoring and verification sit on two surfaces. Rejected: T-C2 (author from the
location sheet — each edit touches one cell of one NPC's day, fighting the write
shape; *reactivation: if practice shows editing happens from the read panel*);
T-C3 (read panel and CLI only, authoring later — leaves Nia unable to create a
schedule except by hand, breaking the live-gate loop).

**Unresolved shape (T-D2).** `where_is` returns a resolution with
`location_id=None` and `source="unknown"` — never an exception, never an empty
result. `unknown` is the TERMINAL TERM of the C1 order, not an error condition:
raising would make it inexpressible inside the ordered constant and would punch
a hole in the check that asserts no lookup happens outside it. `who_is_at` stays
consistent: an NPC resolving to `unknown` appears in no location's roster.

T-D2 adds a companion read, `unresolved_npcs(phase) -> [npc_id]`, consumed by
the F1 panel. Without it, NPCs that resolve nowhere are invisible everywhere —
the exact gap F1 exists to close. Rejected: T-D1 (bare resolution, no
companion); T-D3 (exception).

**C1 terminal reconciliation.** C1 named the present branch's last term
"fallback" and the future branch's "unknown". T-D2 defines one shape for both.
They are the same terminal and are named `unknown` in both tuples. This is a
reconciliation of two decisions, recorded here rather than resolved silently in
a brief.

**Indexing (T-E1).** `UNIQUE (npc_id, phase)`, plus `(location_id, phase)` for
the inverse read that drives `who_is_at`.

**Correction to A1a's non-foreclosure note.** A1a recorded that a calendar would
mean "widening the unique index to `(npc_id, phase, day_kind)`". That is
subtly wrong: SQLite treats NULLs as distinct inside a UNIQUE index, so the
naive widening would silently lose the one-row-per-NPC-per-phase guarantee for
every default row. The correct path when a calendar lands is the partial-unique
idiom already in the tree (`models/canon_faction.py:105-114`): one partial
unique `WHERE day_kind IS NULL`, another `WHERE day_kind IS NOT NULL`. Costs
nothing today; avoids an index rebuild later. Rejected: T-E2 (declare
`day_kind NOT NULL` with a `'*'` sentinel now so the index never moves — a
column with no reader, and A1a forbids the calendrical axis in v1;
*reactivation condition: a world-clock ticket has shipped a readable day
counter*).

**History (S-I1).** No `change_history` on schedule rows. The whole
curated-config family carries none (`write_location_doors`,
`upsert_location_type`, `upsert_conversation_window_config`). A schedule row is
a standing DEFAULT, not an event — "history is sacred" protects narrative
artifacts, not a table of defaults. The `ProposedMutation` trail covers
model-authored changes when `schedule_change` arrives. *Reactivation condition:
a brief needs to render WHEN a routine changed as a narrative fact.*

**Auto-approve (S-F).** Explicit Scope OUT, assigned to a separate ticket. It
requires a real proposer — `schedule_change` emitted by the tick — which means
changing the tick's model-call vocabulary. Locked constraint recorded for
whoever builds it: auto-approvability is NOT an attribute on a mutation row; it
is a whitelist of mutation types in a Python constant, guarded fail-closed.
"Auto-approved" means *reviewed by code*, not *unreviewed* — a full
`ProposedMutation` row is still written, with an audit trail distinguishing
code-review from human-review, and an auto-applied mutation is compensated,
never retracted.

**Germ realization (S-H).** No new obligation: B1 is sparse and the accessor
fallback covers a brand-new NPC.

**Sequencing.** Brief -a is the schema and the reads, live-testable through the
CLI companion. Brief -b is the Creation surfaces, live-testable in the cockpit.
Brief -c is the L1 concordance wiring, live-testable in a scene. Each is one
coherent commit.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] `SCHEDULE_PHASES` is a module-level tuple in `models/schedule.py` holding EXACTLY `matin`, `apres-midi`, `soir`, `nuit`; zero constants located is a FAILURE  -> verify/checks/npc_schedule.py
- [ ] `ck_npc_schedule_phase` and `ck_world_current_phase` both exist, and each constraint expression quotes exactly the four values of `SCHEDULE_PHASES` and no other literal  -> verify/checks/npc_schedule.py
- [ ] `INTERVAL_HOP_RADIUS` still holds exactly its three interval-label keys — the phase vocabulary is a separate constant, never a reuse of the duration axis  -> verify/checks/world_tick.py
- [ ] `PRESENT_PRECEDENCE` and `FUTURE_PRECEDENCE` are module-level tuples in `schedule_reads.py`; every name in both is a key of `_SOURCE_LOOKUPS` and every key appears in at least one tuple; `where_is`'s own body contains no `select(` call; zero names collected is a FAILURE  -> verify/checks/npc_schedule.py
- [ ] Both precedence tuples end with `"unknown"`, the `unknown` lookup returns `location_id=None`, and `where_is` contains no `raise` on the unresolved path  -> verify/checks/npc_schedule.py
- [ ] `NpcSchedule` declares `idx_npc_schedule_npc_phase` (unique) and `idx_npc_schedule_location_phase`, and declares no `change_history` field  -> verify/checks/npc_schedule.py
- [ ] `npc_schedule` is in `[CANON_TABLES]` and exactly ONE `[ALLOWED_SITES]` line maps to it; `write_npc_schedule`'s DELETE is parameterized on `npc_id` and is never an unscoped `DELETE FROM npc_schedule`  -> verify/checks/npc_schedule.py
- [ ] Every canon row write is attributed to a sanctioned site  -> verify/checks/single_canon_write.py
- [ ] `EXPECTED_STATIC_SCHEMA_VERSION` equals the `world-engine-schema.md` header at `v1.92`  -> verify/checks/schema_version_agreement.py
- [ ] `models/canon.py` stays at or under 1000 lines after the `current_phase` column lands  -> verify/checks/module_budget.py
- [ ] `SchedulePanel.svelte` issues no POST, PUT, PATCH or DELETE — the F1 panel is read-only by construction  -> verify/checks/npc_schedule.py
- [ ] `Sheet.svelte` imports and mounts `ScheduleEditor` inside the `character`/`npc` branch and `SchedulePanel` inside the `location` branch; a mount present without its import, or either absent, is a FAILURE  -> verify/checks/npc_schedule.py
- [ ] Every phase `<select>` in the frontend builds its options from one named constant, never from four inline literals  -> verify/checks/npc_schedule.py
- [ ] `_npc_context_standing` receives the phase and the location, compares a schedule resolution against them, and is reached from `assemble_npc_context`  -> verify/checks/npc_schedule.py
- [ ] Every frontend file stays under the 1000-line budget  -> verify/checks/module_budget.py
- [ ] `corpus_gate.py` is green on the whole corpus at the close of each brief  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)

- [ ] `python scripts/preview_npc_schedule.py --npc <id>` prints a four-row day for an NPC with a schedule, and for an NPC with none prints four `unknown` rows without raising.
- [ ] The same script with `--location <id> --phase soir` lists the NPCs `who_is_at` resolves there, and reports the NPCs that resolve nowhere for that phase.
- [ ] On an NPC sheet in Creation, the schedule island shows four phase rows, a location can be picked for each, and saving then reloading the sheet shows the same four rows.
- [ ] Clearing a phase row and saving removes it — full-replace, not an accumulating list.
- [ ] On a location sheet, the "who is here, by phase" panel lists the NPCs scheduled there per phase, and phases with nobody are visibly empty rather than absent. This is B1's compensating control under test.
- [ ] The current world phase is visible in the cockpit chrome at all times and can be advanced from there. This is T-A1's condition 1 under test.
- [ ] Advancing the phase changes nothing except the displayed phase: no tick fires, no mutation appears in the review queue, no NPC moves. This is T-A1's condition 2 under test.
- [ ] Two worlds hold two independent phases: advancing the phase in one leaves the other untouched.
- [ ] In a live scene, an NPC standing where its schedule says it should be shows the `POURQUOI TU ES ICI` section; the same NPC met somewhere its schedule does not assign for the current phase does not. This is L1 under test.
- [ ] An NPC with a standing occupation and NO schedule row still behaves as it did after TICKET-0073 — no regression from the sparse table.
