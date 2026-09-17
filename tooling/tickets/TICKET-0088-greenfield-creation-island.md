---
id: TICKET-0088
slug: greenfield-creation-island
title: Greenfield Creation islands, and the unresolved-subject worklist
type: feature
status: brief
created: 2026-09-15
model_lane: { intake: opus, recon: opus, exec: sonnet, verify: sonnet }
danger_class: []
blast_radius: medium
lot_id: LOT-0088-greenfield-creation-island.md
brief_ids: [BRIEF-0088-a, BRIEF-0088-b]
current_brief:
schema_version_touched: none
retry_count: 0
---

## Request (verbatim, as Nia stated it)

Opened by Nia's decision `K3` on 2026-09-15, recorded in
`AMENDMENT-0087-2-residue-worklist-deferred.md`:

> **Nia chose K3**, with the gap opened as **TICKET-0088**, to be executed
> **before BRIEF-0087-e**.

No sentence beyond the code was stated. The requirement this ticket
inherits is TICKET-0087's own live criterion, verbatim:

> The creator surface lists unresolved subjects for the active world and
> lets a subject be bound to an entity in one action; the coverage number
> moves after binding.

Ordering, stated by Nia on 2026-09-17:

> l'ordre est : Ce ticket, puis on ferme le ticket 0087 (brief e; dans un
> autre session, ne t'en mêle pas)

## Clarifications resolved (intake)

Decision sessions of 2026-09-15 and 2026-09-16 (decision RECON and option
blocks A–G), and of 2026-09-17 (H–K). Locked codes: `A1b, B1, C2, D3, E1,
F3, G1, H1, I1, J1, K1`.

**Why the worklist could not be built in TICKET-0087.** Every Creation
surface mounts through `CREATION_ISLANDS` and `mount.js`, the only
sanctioned mechanism, and `creation_island.py` rule 2 requires every entry
to declare a non-empty `retiredPrefixes` whose functions rule 7 proves gone
from the legacy document. A surface with no legacy predecessor cannot
declare one honestly, and inventing a prefix is check-gaming. Claude Code
raised the STOP; `K3` deferred the worklist here.

**The registry's doctrine is supplemented, not edited.**
`ARCHITECTURE_DECISIONS.md:11237` says the registry is "the record of what
has MOVED: one entry per migrated surface, never removed once added". The
new ADR entry quotes that sentence and supersedes it on the record, per the
file's own precedent; the old entry is never rewritten.

**No schema change, no backend change.** `danger_class` is empty:
this ticket writes no canon and adds no route. `blast_radius` is `medium`
because the gate it rewrites decides every future Creation merge.

**The corrections the decision RECON made to the opening handover** are
carried in the lot: the registry holds 15 entries, not 16; the registration
surface is six sites, not five (`mount.js`'s `COMPONENTS` map is
hand-kept and no check reads it); the residue route's JSON nests the
resolution under a `resolution` key; rule 8's docstring does not describe
its code; rule 7 never examines 16 of `entitySheet`'s prefixes.

## Decisions locked (do not re-litigate without Nia)

- **A1b — every `CREATION_ISLANDS` entry declares its `origin`, and each
  origin has a closed field set** (`migration`: `containerId`, `component`,
  `origin`, `migratedBy`, `retiredPrefixes`; `new`: `containerId`,
  `component`, `origin`, `createdBy`). A missing field, a field from the
  other variant, or an unknown field is a FAIL naming the entry and the
  field; a declared entry that does not parse is a FAIL, never an invisible
  entry. *Rejected:* **A1a**, a `new` entry keeping `migratedBy` with
  `retiredPrefixes: []` — it records a migration that never happened, the
  class TICKET-0061 removed for `retiredBy`; no reactivation condition.
  **A2**, a second registry — it needs a second mount path or a double
  lookup in `mount.js`; *reactivate* at the first brief that must remove an
  entry from `CREATION_ISLANDS`. **A3**, retiring rules 2 and 7 —
  `legacy.html` is live Play code; *reactivate* when `legacy.html` is absent
  **and** `LEGACY_MOUNTS` is empty.
- **B1 — the worklist gets its own bespoke Creation tab**: key `subjects`,
  label « Sujets », container `creation-subjects`, island key
  `subjectWorklist`, component `SubjectWorklist.svelte`, state module
  `subjectWorklist.svelte.js`, placed between « Événements » and « Review
  Queue », `primaryAction: null`. *Rejected:* **B2**, a second island inside
  an existing tab — no existing tab is a world-scoped curation list, and
  grafting it under the Review Queue degrades that surface's empty states
  permanently; *reactivate* when an existing tab's subject becomes knowledge
  subjects.
- **C2 — one lot, two briefs**: (a) the gate, (b) the panel. *Rejected:*
  **C1**, the gate alone; *reactivate* if brief b escalates — brief a then
  lands on its own and stays green through its self-test.
- **D3 — the three repairs of D2, plus the bypass lock.** Rule 7 applies to
  migration entries only and fails closed when `legacy.html` is missing;
  `COMPONENTS` must agree exactly with `CREATION_ISLANDS`; the check's
  docstring and the `registry.js` header are rewritten from the code. D3
  adds that `Creation.svelte` imports and renders no component. *Rejected:*
  D1 and D2 alone, since D3 contains both.
- **E1 — binding a subject is a client-side loop, with no backend change**:
  one POST per fact, in sequence, with no role; the loop stops at the first
  failure; the list always reloads afterwards; one bind at a time, every
  control disabled until that reload has landed. It is safe because the
  residue excludes every fact that has any participant, so a partly bound
  subject stays listed with only its unbound facts and a retry never sends a
  duplicate pair — which matters, because the route answers 500 on a
  duplicate. *Rejected:* **E2**, a bulk backend route — it would bring
  `db_write` into a frontend ticket; *reactivate* when a partly bound
  subject becomes wrong, i.e. when a role discriminator returns under
  TICKET-0087 `J2`'s reactivation condition.
- **F3 — branching**: `ticket/0088` is cut from an up-to-date `main`
  containing TICKET-0087 a–d, and its MR targets `main`; BRIEF-0087-e starts
  from `main` after TICKET-0088 has merged. Precondition P-1, measured on
  2026-09-17: PR #113 is merged as `994c9b2` and `main`'s tree is identical
  to `ced51c1`'s, so both forms of P-1 hold. *Rejected:* **F1** and **F2**,
  which both assumed TICKET-0087 was unmerged.
- **G1 — AMENDMENT-0087-3 repairs TICKET-0087's Machine section (S-1),
  regenerates BRIEF-0087-e's done-means, and records S-2 and S-3 as named
  deferrals in LOT-0087.** *Rejected:* **G2**, also fixing the attach route
  — *reactivate* when the S-3 query returns more than 0; **G3**, doing
  nothing.
- **H1 — this lot delivers TICKET-0088 only.** G1 is written and deposited
  by the session that closes TICKET-0087, on the branch BRIEF-0087-e runs
  from, before e; open points O-1 (how e starts once the MR is merged) and
  O-2 (re-anchoring e's moved line numbers) go with it. This amends G1's
  deposit clause and nothing else in G1. Consequence here: no TICKET-0088
  artifact names a `D-0087-*` deferral, because none exists yet; S-2 and S-3
  appear as RECON findings (R-25, R-26). *Rejected:* **H2**, the eight-file
  delivery of the opening handover; **H3**, splitting G1 across two sessions
  — an amendment must describe every edit it applies.
- **I1 — brief a makes both `CLAUDE.md` edits**: the `### File structure`
  line for `src/creation/`, and a three-line invariant bullet naming
  `creation_island.py`. *Rejected:* **I2**, the structure line alone —
  Claude Code reads `CLAUDE.md` every session, not the ADR, and would meet
  the invariant on a red gate; *reactivate* when `CLAUDE.md` is within 500
  characters of its 38 000-character budget (34 323 after this ticket).
- **J1 — brief b rewrites `page_contract.py`'s counters and PASS wording**
  (`island_count` / `bare_count`, "mount at least one island" / "mount
  none"). *Rejected:* **J2**, adding `subjects` to `TAB_KEYS` alone — the
  PASS line would state a migration that never happened, the same false
  provenance A1b refuses in the registry; no reactivation condition.
- **K1 — the self-test lives inside `creation_island.py`**, runs first,
  reads no file, and expects "at least one message naming X" per seeded
  break. *Rejected:* **K2**, manual breaks recorded once in the brief's
  done-means — the refusal paths have no example in the real tree, so a
  broken refusal would pass silently; *reactivate* when the check exceeds
  5 s (`corpus_gate.py`'s per-check timeout is 15 s; it runs in 0.09 s
  today).

Proposed by Claude and not objected to by Nia: `danger_class: []` and
`blast_radius: medium`; a commit of the deposited artifacts before the first
edit; the executor records its own `corpus_gate.py` baseline first; one
verify arrow per Machine line with `corpus_gate.py` linked; and
**D-0059-prompts-surface judged not fired** — the worklist curates canon, it
does not configure the engine, so it is not the "second creator-tooling
surface" that reactivates promoting Prompts out of Creation. That judgment
is recorded in brief b's ADR entry.

## Carried forward / open

- **AMENDMENT-0087-3 (`G1`), with O-1 and O-2.** Decided, not delivered
  here (`H1`). It is the first task of the session that closes TICKET-0087,
  and its content is settled: repair the Machine section, regenerate
  BRIEF-0087-e's done-means, record S-2 and S-3 in LOT-0087. No ticket of
  its own.
- **S-4 — `day_mutations.py` needs `WORLD_ENGINE_ENV` at import time**, so
  a clone without a local `.env` reports `CRASH` rather than `ENVIRONMENT`
  for that check. Pre-existing, unrelated to this ticket. Options put to
  Nia: a small ticket of its own (recommended, after BRIEF-0087-e); folding
  it into the next verify-hygiene ticket; leaving it. Undecided.
- **The test seed is broken** — `reset_test.py` unlinks whatever database
  file the environment resolves to before reseeding. Same options as S-4,
  same recommendation. Undecided; brief b works around it by naming an
  explicit new database file.
- **A bind reaches the fact, not the row** (R-27). Several `knowledge` rows
  share one fact, and `subject` is editable while `fact_id` is not, so
  binding one subject also settles any other subject text sitting on the
  same fact. This is the entity sheet's existing reach, and the data state
  it can produce is already named by TICKET-0087 `J2`'s reactivation
  condition. Options: leave it there (recommended), or open a deferral of
  its own with a production count. Undecided; brief b reports what the
  executor observes and changes nothing.
- **The hand-kept literal sets in other checks** (`page_contract.py`'s
  `TAB_KEYS` among them) remain TICKET-0085 queue item 7.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate

- [ ] The island registry parses order-free and comment-aware, and every declared entry conforms to the closed field set of its `origin`  -> verify/checks/creation_island.py
- [ ] Rule 7 examines migration entries only, and fails closed when the legacy document is absent while any migration entry exists  -> verify/checks/creation_island.py
- [ ] `COMPONENTS` in `mount.js` agrees exactly with `CREATION_ISLANDS`, key for key and path for path  -> verify/checks/creation_island.py
- [ ] `Creation.svelte` imports and renders no component  -> verify/checks/creation_island.py
- [ ] The check's own self-test seeds each refusal and each is named  -> verify/checks/creation_island.py
- [ ] Every `CREATION_TABS` entry, the new one included, is covered by the dispatcher rules and mounts at least one island  -> verify/checks/page_contract.py
- [ ] No `$state` binding is written and then read inside one `$effect` in the new component  -> verify/checks/effect_self_write.py
- [ ] Every class the new component applies has a strict base rule  -> verify/checks/stylesheet_partition.py
- [ ] No graph primitive outside `frontend/src/graph/`, and `mount.js` still passes `legacyDoc: node.ownerDocument`  -> verify/checks/graph_primitive.py
- [ ] No legacy-frame access anywhere under `frontend/src`  -> verify/checks/legacy_mount.py
- [ ] The `creation:sheet-reset` dispatch stays confined to `tabs.js`  -> verify/checks/creation_tab_switch.py
- [ ] No frontend file over 1000 lines, and the legacy document still at its ratchet  -> verify/checks/module_budget.py
- [ ] The committed frontend build matches its sources  -> verify/checks/frontend_build_fresh.py
- [ ] Static assets and HTML routes carry their cache policy  -> verify/checks/static_asset_freshness.py
- [ ] `CLAUDE.md` stays inside its character, line and archaeology budgets  -> verify/checks/claude_md_contract.py
- [ ] Both new decision-record headers match the strict pattern and the index is regenerated  -> verify/checks/decisions_index.py
- [ ] This ticket's front matter and section shape parse  -> verify/checks/pipeline_state.py
- [ ] Every check in the corpus passes  -> verify/checks/corpus_gate.py

### Live  ->  human gate (Nia)

- [ ] The Creation tab bar reads « … Événements, Sujets, Review Queue, Prompts », and `/creation/subjects` opens the tab directly.
- [ ] On a world with residue, the panel lists its unresolved subjects, most rows first, with a head count of subjects and lines; switching worlds reloads the list.
- [ ] A subject the resolver matched shows its suggestion with the picker preselected; a subject with no match shows « Aucune suggestion » and keeps « Lier » disabled until an entity is chosen.
- [ ] Binding a subject writes one participant per fact, removes the subject from the list, and lowers the head counts accordingly.
- [ ] If a bind fails part-way, the card states how many facts were bound before the failure and the subject stays listed with its still-unbound facts; a second attempt binds the remainder.
- [ ] A world with no residue shows « ✓ Aucun sujet non résolu dans ce monde. » rather than an empty panel.
- [ ] TICKET-0087's live criterion — "the creator surface lists unresolved subjects … and the coverage number moves after binding" — is satisfied by this surface.

## Amendment log

| id | brief in flight | what deviated | downstream briefs regenerated |
|----|-----------------|---------------|-------------------------------|
|    |                 |               |                               |
