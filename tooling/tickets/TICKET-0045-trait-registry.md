---
id: TICKET-0045
title: Trait registry — code-source-of-truth trait contracts with declared readers
type: feature
status: live-gate
created: 2026-07-24
model_lane: { intake: opus, recon: sonnet, exec: sonnet, verify: sonnet }
danger_class: [db_write, migration]
blast_radius: medium
brief_ids: [BRIEF-0045-a, BRIEF-0045-b, BRIEF-0045-c, BRIEF-0045-d]
schema_version_touched: v1.88
retry_count: 0
---

## Request (verbatim, as Nia stated it)

Registry de traits — definition des traits (describable, spatial, knowable,
secretable, mutable_by_ai), chacun avec son lecteur declare.

Decision amont E2 (upstream, this ticket's frame): the entity-constructor
field palette exposes traits, not bare primitives. Each trait is a predefined
bundle of columns + FK + a registered reader. Checking a trait activates a
complete contract. This ticket defines the trait registry and its contract.

Invariant central a defendre: doctrine "no structure without a reader". A
trait cannot exist without its declared consumer. The registry must make this
constraint structural, not documentary — a trait with no registered reader
must FAIL at verify, never pass with a warning.

Scope OUT: constructor UI (TICKET-0046), runtime DDL (TICKET-0044, landed),
canon-write dispatch (TICKET-0047).

## Clarifications resolved (intake)

Locked decision codes (Nia): A1, E2 (exception mutable_by_ai only), B1,
B2(ii), C1. Derived-trait deferral logged (D-derived).

- **A1 — Registry is code-source-of-truth.** Trait definitions live in a
  Python module (`traits.py`): name, column bundle, FK spec, and an
  IMPORTABLE reference to the reader. A DB table `entity_trait` exists as a
  MATERIALIZED PROJECTION only (which entity_type has checked which trait) —
  never as the trait definition. Rationale: the reader is code; a trait
  declared in the DB cannot structurally prove its reader exists (a TEXT
  string "placement.spawn_point" is unverifiable at commit). Confirmed by
  Nia's design: new traits (e.g. `rideable`) are added via Claude Code and
  then become available to all entity types — NOT hot-editable by the
  creator at runtime.

- **E2 — Every trait carries a real reader.** "No structure without a
  reader" is enforced, not assoupli. A boolean-only flag that nothing reads
  is NOT an admissible trait — it waits for its ticket. `size`/`health` and
  similar are COLUMNS inside a trait's bundle, never traits themselves.

- **B2(ii) — Sole exception: `mutable_by_ai`.** Inscribed in the registry
  with `reader_deferred: TICKET-0047`, tolerated by name by the verify check
  (same ticket-spanning debt already assumed by the socle for
  `entity_type.write_authorities`/`ai_proposable`, per schema v1.87 note).
  No other trait may claim a deferred reader.

- **B1 — Five distinct traits.** `describable`, `spatial`, `knowable`,
  `secretable`, `mutable_by_ai`. `describable` is the non-checkable socle
  (Nia's "what an entity should have, no exception": name + description),
  always present, above the checkable palette. A shared reader does not
  collapse two traits: `describable` and `knowable` both touch the NPC
  context builder but carry different bundles, so they stay distinct.

- **C1 — Reader-exists is an AST import-resolution check.** `trait_reader.py`
  imports the registry module, iterates the traits, and RESOLVES each
  declared reader (the callable is importable and exists). A trait whose
  reader fails to resolve = FAIL naming the trait. Fail-closed, vacuous-proof
  (traits examined must be > 0). The `mutable_by_ai` deferral is the single
  named-exception branch.

- **D-derived (deferral logged, OUT).** Value-conditioned / derived traits
  (Nia's "rideable if size > medium", "portable if size < medium") are a
  richer third tier (computed traits). Logged in ARCHITECTURE_DECISIONS.md
  with trigger condition; NOT built in 0045. The registry ships flat,
  checkbox-activated traits only.

### Real readers anchored by RECON (live main, schema v1.87)

| Trait          | Real reader (file:line)                                        |
|----------------|----------------------------------------------------------------|
| describable    | context.py:229 `_npc_context_identity`; tick_context.py:168 `_tick_identity_block` |
| spatial        | placement.py:179 `spawn_point`; placement.py:212 `derive_positions` (FK location, local coords v1.80) |
| knowable       | context.py:314 `_npc_context_speak`, :299 `_npc_context_perceived`; tick_context.py:352 `assemble_tick_context`, :229 `_tick_knowledge_block` |
| secretable     | context.py:167,194 (`is_secret == False` WHERE); doctrine context.py:4-22 — exclusion at query construction, negative clause not positive read |
| mutable_by_ai  | NONE — reader_deferred TICKET-0047 (entity_type.write_authorities/ai_proposable reserved at socle) |

Note (secretable): its "reader" is a negative WHERE clause, not a positive
accessor. The C1 check for secretable must prove the trait's exclusion column
is referenced in a query-construction filter, not that a function reads it.
Brief -c owns this asymmetry.

## Acceptance criteria

### Machine-checkable  ->  G1 deterministic gate
- [ ] Every non-deferred trait in traits.py resolves an importable reader; `mutable_by_ai` is the sole named reader_deferred exception; zero traits examined is a FAIL  -> verify/checks/trait_reader.py
- [ ] entity_trait projection rows reference only registry-declared trait keys; no orphan trait key, no trait key absent from traits.py  -> verify/checks/trait_registry_projection.py
- [ ] schema doc and models package agree on schema version after entity_trait lands  -> verify/checks/schema_version_agreement.py
- [ ] no module in the 0045 change set exceeds the 1000-line / 40-function budget  -> verify/checks/module_budget.py
- [ ] every function in the 0045 change set is within the 80-line ceiling  -> verify/checks/function_length.py

### Live  ->  human gate (Nia)
- [ ] Live deployment sequence for the entity_trait migration executes clean: backup -> migration -> seed the 5 trait rows -> verify (danger_class: migration).
- [ ] A hand-planted trait in traits.py with a deliberately broken reader import makes trait_reader.py FAIL (red-team the fail-closed path).
- [ ] `mutable_by_ai` with no reader PASSES only via the named reader_deferred branch; renaming any other trait to claim reader_deferred FAILs.
- [ ] Seeding confirms describable is present as the non-checkable socle on every entity_type; the other four are checkable projections.
