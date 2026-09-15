# AMENDMENT-0087-2 — "The residue worklist is deferred to TICKET-0088"

Amends: LOT-0087-knowledge-subject-participants.md, BRIEF-0087-d
Raised by: Claude Code, executing BRIEF-0087-d, as a STOP on Scope IN item 5
Decided by: Nia, 2026-09-15, code `K3`
Status: applied to the header and to BRIEF-0087-d; items 1-4 and 7 stand

## What deviated

BRIEF-0087-d's Scope IN item 5 asked for a world-scoped residue worklist as
"a new panel in the Creation shell", and closed with:

> Follow the existing panel conventions of the Creation shell —
> registration, mount, and styling — rather than inventing a new pattern.
> Where an existing panel already does the thing, copy it.

That instruction asserts a convention exists to copy. For a *greenfield*
Creation panel, none does.

Every Creation surface mounts through `CREATION_ISLANDS`
(`frontend/src/creation/registry.js`) and `mount.js`, the only sanctioned
mechanism (`creation_island.py` rule 6). `creation_island.py` rule 2
(`:246-248`) requires every registry entry to declare a **non-empty**
`retiredPrefixes` list, and rule 7 (`:332-337`) proves each prefix matches
zero `function <prefix>...(` declarations in
`src/world_engine/cockpit/legacy.html` (`INDEX_HTML`, `:107`).

The residue worklist has no legacy predecessor. There is nothing to retire.
Claude Code refused to invent a prefix, correctly: a fabricated "retired"
name that was never live is check-gaming, the exact failure mode R-12 of this
lot's own RECON names and TICKET-0086 just finished fixing elsewhere.

## The finding underneath, which is larger than this lot

`CREATION_ISLANDS` holds 16 entries. **Every one carries `migratedBy:
TICKET-0058` or `TICKET-0059`.** Nothing has been added since the frontend
migration series, and `registry.js`'s own header states what the registry is:

> one entry per surface a brief **converges** ... It is **the record of what
> has moved**, not of what remains.

It is a migration-provenance ledger. A surface with no migration has no
provenance to declare, and the check has no way to tell "greenfield" from
"forgot the field". TICKET-0087 is simply the first ticket since the
migration series to want a new Creation panel; every future one will hit the
same wall.

That is a frontend-seam gap, not a knowledge-subject problem. Fixing a G1
gate inside a `db_write` lore ticket is the scope bleed Scope OUT exists to
prevent.

## What the decision session concluded

Options put to Nia: K1 amend `creation_island.py` to admit greenfield
provenance; K2 land the worklist as a child section of an already-registered
island (child components need no registry entry — proven by
`QueueCard.svelte`, `ConversationWindowConfig.svelte`, and
`KnowledgeEditor.svelte` itself); K3 defer the worklist; K4 move it to the
Lore shell.

**Nia chose K3**, with the gap opened as **TICKET-0088**, to be executed
**before BRIEF-0087-e**.

K2 was rejected on cost: `Queue.svelte`'s own header calls its empty states
*"the surface's meaning, not decoration"*, and grafting a second, unrelated
list under the Review Queue degrades that permanently to save one ticket.
K4 was rejected: it would reopen TICKET-0085's read-only lock on the
consultation surface.

## Amended BRIEF-0087-d — Scope IN item 5, verbatim replacement

> 5. **The residue worklist is not built in this brief.** Deferred to
> TICKET-0088, which lands the greenfield-island path in
> `creation_island.py` and then the panel itself, and which runs before
> BRIEF-0087-e. Do not add a `CREATION_ISLANDS` entry, do not add a
> container to `Creation.svelte`, do not touch `registry.js`, `tabs.js`,
> `mount.js` or `Creation.svelte`. Gap closure in this brief is item 3
> alone: one knowledge row at a time, from the entity sheet.

## What item 5's deferral does NOT retract

**Scope IN item 2 stays.** `GET /api/worlds/{world_id}/unresolved-subjects`
is built, committed and green. It keeps two concrete readers: BRIEF-0087-c's
backfill report, which already consumes `C-06` behind it, and TICKET-0088's
panel, which is queued with a brief and ordered before BRIEF-0087-e. This is
recorded here so a later reader does not flag the route as structure without
a reader — it has one today and a second one named.

**`C-06` stands unchanged.** It is the single query behind both the report
and the future worklist, which is why it was written once.

## Downstream briefs touched

- **BRIEF-0087-d** — Scope IN item 5 replaced as above; the Scope OUT gains the worklist as a named deferral; the STOP condition about world-scoped panel conventions is removed (it fired, it was answered, it no longer applies); one done-means line about the worklist is struck; one ADAPT entry about the worklist's `fact_ids` is struck; one REPORT-ONLY line is re-aimed at the entity sheet.
- **BRIEF-0087-e** — no content change. One ordering line added: TICKET-0088 now runs between BRIEF-0087-d and this brief, by E2.
- **BRIEF-0087-a, -b, -c** — untouched.

## Gate checks re-run

- **(a) Unverified symbol** — re-run, and it failed a third time on the same defect class. `registry.js`, `mount.js`, `creation_island.py` and `Creation.svelte` were named by BRIEF-0087-d item 5 and appear in no RECON finding; the lot asserted a convention existed in files it never opened. The deferral removes the claim rather than repairing it, since TICKET-0088's own RECON will open those files properly. R-20 is added to the header recording what was measured in the escalation, so TICKET-0088 inherits it rather than re-deriving it.
- **(b) Unwalked rule** — no case table changes. Item 5 had none; that absence is itself part of the defect.
- **(c) Unenumerated generalization** — the `migratedBy` enumeration is pasted into R-20.
- **(d) Un-rederived contract** — unchanged. `C-06` keeps both consumers.
- **(e) Unsatisfiable check** — this is the entry that should have caught it at drafting. Item 5 required `creation_island.py` to pass and never named the module that would satisfy it, because no such module can exist today. Gate (e) is restated in the header accordingly.

## Ordering after this amendment

```
BRIEF-0087-a  ->  BRIEF-0087-b
              ->  BRIEF-0087-c  ->  BRIEF-0087-d
              ->  TICKET-0088 (greenfield island + residue worklist)
              ->  BRIEF-0087-e
```

BRIEF-0087-e still depends technically only on BRIEF-0087-a. TICKET-0088
precedes it by decision E2, on the same reasoning as before: close the
coverage gap before shipping a selector that reports it.
