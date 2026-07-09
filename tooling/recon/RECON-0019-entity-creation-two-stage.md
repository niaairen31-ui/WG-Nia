# RECON-0019 — entity-creation-two-stage (tick proposes the need, authoring produces the sheet)

Date: 2026-07-08
Branch inspected: `main` (post TICKET-0018 merge; schema head v1.72,
world-engine-schema.md:3; 0015-0018 closed, live-gates validated)
Mode: report-only. No actions taken.

Locked decisions in force: H1 (two stages: germ -> approval parks ->
on-demand generation -> creator commit realizes), I2 (generation happens
in the Création tab, never synchronously during queue review), quota by
construction, code-side name-collision guard, connects_to never
auto-wired.

---

## F1 — The authoring chain is PURE and its purity is a named property;
## H1 composes onto it without modification

`entity_author.py:389-397` — `generate_entity_draft(entity_type, brief,
db)` docstring: "Pure generate-and-return: writes no canon anywhere in
this function or its call path. Never raises into the caller — every
failure mode returns {'ok': False, 'error': ...}". Input is a TEXT BRIEF
— exactly what the germ composes into. Supported types = `_TYPE_FIELDS`
keys: `character | location | faction` — precisely Nia's three.
`AUTHOR_MODEL` (llama3.1) does the writing-quality work; the 8b gameplay
model never authors a sheet (H2 stays rejected by construction).

## F2 — The generation route is DELIBERATELY outside crud.py; the
## realization generator belongs beside it

`cockpit/app.py:127-150` — `POST /api/entities/generate` docstring:
"Deliberately NOT in crud.py: crud.py is a sanctioned canon-write path
and this route writes nothing — keeping it in a separate router makes
that property legible." It also carries the L1 enrichment (BRIEF-0013-b):
a successful CHARACTER draft additionally calls `generate_npc_goals` and
merges `draft["public"]["goals"]`; a goals failure never fails the draft.
CONSEQUENCE: `POST /api/creations/{mutation_id}/generate` lives in the
same write-free router region and REUSES this flow (compose brief ->
same draft+goals path -> return draft + mutation_id for the form) rather
than calling entity_author directly — one generation path, L1 included
for free.

## F3 — The queue's approve flow already has the exact parking state I2
## needs; only the FRAMING must change

`cockpit/app.py:5330-5364` — approve endpoint: `_apply_mutation` runs in
a SAVEPOINT; success -> `status="applied"`; any error -> savepoint rolls
back, `status="approved"` + note `"[apply error] <msg>"`. Today
entity_creation is "unimplemented" (docstring app.py:1078) and would fall
through the ERROR branch — parked correctly but framed as a failure.
CONSEQUENCE: the approve endpoint gains a SHORT-CIRCUIT before the
savepoint for `mutation_type == "entity_creation"`: run the canon
name-collision guard (F5); pass -> `status="approved"`,
`reviewed_at=now`, note "en attente de réalisation — onglet Création",
response `{"status": "pending_realization", ...}` — no savepoint, no
error framing, `_apply_mutation` untouched for this type (it keeps
writing NO canon for entity_creation; its docstring "Unimplemented"
shrinks to `other` with a pointer to the realization flow).

## F4 — The realization flip is a JSON-column mutation with a known trap

`create_entity` (cockpit/crud.py:690) is the commit path the pre-filled
form already posts to. It gains optional `mutation_id`: after the entity
commit succeeds, load the ProposedMutation; GUARDS — must exist, be
`entity_creation`, be `approved`, and its payload must LACK
`created_entity_id` (double-commit protection); then stamp
`payload = {**payload, "created_entity_id": new_id}` (REASSIGNMENT, not
in-place update — SQLModel JSON columns do not detect in-place mutation;
alternatively `flag_modified`), `status="applied"`, `applied_at=now`.
Guard failures REJECT the linkage but NEVER the entity commit (the
entity is the creator's hand; a broken linkage is a note, not a
rollback) — surfaced in the response for visibility.

## F5 — Collision guard: two moments, one canon question

Emit-time (scope normalizer): germ `name` casefolded equals the name of
an ACTIVE entity of the world -> drop with note (the model proposed
something that exists). Approval-time (the F3 short-circuit): same check
re-run — the world may have moved between proposal and review (0014
canon-existence doctrine; tick_id is never the key). Scope of the check:
ANY active entity type, not same-type-only — a location and a faction
sharing a name is exactly the confusion to prevent (flagged, reversible).
The creator can still rename in the form at realization — the guard
protects the QUEUE from noise, not the creator from her own choices.

## F6 — The dormant conversation channel: accepted type, NO payload branch

`analyzer.py:58` accepts `entity_creation`; target map `analyzer.py:124`
maps it to `entity`; but the payload normalization has NO dedicated
branch (unlike event_creation, analyzer.py:324) — conversation-sourced
germs carry free-form payloads. CONSEQUENCE: the pending list includes
them (same status+type+no-created_entity_id query — 0017-style
awakening), and the germ->brief composer must TOLERATE shape variance:
name from `name|title` fallbacks, concept from `concept|description|
content`, entity_type validated against `_TYPE_FIELDS` keys with drop-to
-note when absent/invalid (an unrealizable germ shows in the pending
list with a "type inconnu" badge and no Generate button, rather than
crashing the composer).

## F7 — Emit side: the 0018 seams take the third type without stretch

`_normalize_scope_event` (tick.py:535+, extended by 0018) gains an
`entity_creation` branch active for BOTH scope types (unlike agenda
types): `entity_type` validated against `{"character","location",
"faction"}` -> drop otherwise; `name`/`concept` required strings;
`anchor` optional string passed through verbatim; collision check (F5)
against an actives-name index built once per scope call (extend the
existing index builds at tick.py:985-1032). Quota: new module constant
`ENTITY_CREATION_QUOTA = 1`, own seen-counter (events and agendas keep
their own budgets). `target_table="entity"`, `target_id=None`. Payload
carries the germ verbatim — no ids anywhere in it (nothing to force;
rule-3 surface untouched).

## F8 — Prompt and germ-brief composition

New VERSION of `pt-world-tick-events`: germ shape
(`entity_creation -> {"entity_type","name","concept","anchor"?}`),
rules — propose a creation ONLY when the interval's happenings imply
someone/somewhere that does not exist in the briefing; ONE per reply;
the concept is one line; never invent a name colliding with a briefing
name. Delivery: `apply_ticket_0019_prompt_updates.py`, append-version
branch. The germ->brief composer (code, French): one template per
entity_type weaving name + concept + anchor + scope context (faction
name / location name of the invoking scope) into 2-4 sentences — the
shape `generate_entity_draft` expects (a prose brief, F1).

---

## Notes for the brief

1. No migration — the germ lives in `proposed_mutation.payload`, the
   pending list is a query, the flip is column updates on existing rows.
2. The Création tab UI: a "Créations en attente" strip above the
   existing creation form — germ summary (type badge, name, concept,
   source TICK/CONVERSATION, age) + "Générer la fiche"; generating
   loads the existing form pre-filled with `mutation_id` in a hidden
   field. Executor follows the tab's HTMX idioms.
3. Verify additions stay light: quota constant rule; entity_creation
   absent from `_normalize_tick_item`; no `Entity(` in `_apply_mutation`
   (already covered by single_canon_write — confirm the rule sees
   app.py); the create_entity linkage guarded (status/type/unrealized)
   — AST-checkable as "the flip block references all three guards".
