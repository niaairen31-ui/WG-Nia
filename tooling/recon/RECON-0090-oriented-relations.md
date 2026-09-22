<!-- slug: oriented-relations -->

# RECON-0090 — decision RECON for TICKET-0090 "perceiver-oriented relations"

Run 2026-09-22 against `main` at `8b939361` (codeload tarball, re-fetched
before this RECON; unchanged since the morning's decision RECON). Once the
open decisions in section 9 lock, these findings are carried into LOT-0090's
RECON section as `R-NN` entries, re-anchored where a brief needs them. No
brief cites this file directly.

Tags: **[M]** opened and measured in the file that declares the property;
**[E]** measured on a throwaway in-memory database, never on a real one;
**[C]** carried from an earlier measurement without re-measurement;
**[I]** inferred.

---

## 0. Decisions this RECON serves (locked 2026-09-21/22)

- **C3** — every social relation row has exactly one perceiver; a `mutual`
  row becomes two rows; a migration is accepted.
- **N1** — one typed `lien` fact (`fact.relation_id`) per oriented social
  relation. The relation row keeps its mechanical state (type, intensity).
  `visible_to_b` becomes B's knowledge row on that fact.
- **L2** — the lien facts of existing relations are created by this
  ticket's migration. No prose is rewritten.
- **Editor wording (accepted with C3)** — a relation reads "who feels ->
  what -> toward whom". No direction select. "Reciprocal" creates two
  independent rows.
- **Sequence I2'** — this is the first ticket: C3, then "lore en faits"
  (G2 + F1), then names (B), then H2 + K1, then injection. Identity tokens,
  facets and the `rencontre` registry are later tickets.

Measured by Nia against prod on 2026-09-21 [C]: social relations
`a_to_b` 92, `b_to_a` 14, `mutual` 67. Two unordered pairs hold two rows
each, both legitimately asymmetric (Joran Vey <-> Reike, Reike <-> Senna),
both stored as `a_to_b` with the endpoints swapped.

---

## 1. The relation row

**R-01 — `Relation` declares no orientation and no uniqueness.** [M]
Opened: `models/canon_knowledge.py:23-53`.
Finding: the only CHECK is `intensity BETWEEN 1 AND 100`. The three indexes
(`entity_a_id`, `entity_b_id`, `world_id`) are plain, none unique.
`direction` defaults to `'mutual'` with no CHECK and no vocabulary in the
schema. `visible_to_b` defaults to TRUE. `type` is free text. `notes` is
nullable. `change_history` is JSON NOT NULL.
Consequence: orientation and one-row-per-pair exist nowhere in the schema
today. Any guard this lot adds is new.

**R-02 — the direction vocabulary lives in five code copies.** [M]
Opened: enumeration 8.1.
Finding: `crud/_shared.py:141` (`RELATION_DIRECTIONS`),
`link_author.py:71` (`_LINK_DIRECTIONS`), `context.py:113-114` and
`tick_context.py:87-88` (`_A_PERCEIVES`/`_B_PERCEIVES`), and an inline
tuple at `cockpit/play_initiative.py:458-460`. Every perceiver reader treats
`entity_a` as the perceiver under `a_to_b`: `context.py:128-134`,
`tick_context.py:112-116` (imported by `tick_normalize.py:28`, used `:113`),
`play_initiative.py:457-462`.
Consequence: if every social row is normalized to `direction = 'a_to_b'`
with `entity_a` = perceiver, all four perceiver readers keep working with no
edit. Their `b_to_a`/`mutual` branches become unreachable for social rows,
not wrong.

**R-03 — "social" already has a single definition.** [M]
Opened: `context.py:108-110`.
Finding: `RELATION_GRAPH_EXCLUDED_TYPES = ("connects_to", "controls")`,
imported by `crud/relations.py:18`, `link_context.py:21`,
`link_author.py:34`. The structural writers are
`spatial_author.py:124-127` (`connects_to`, `mutual`) and
`routes/regions.py:282-295` (`controls`, `a_to_b`).
Consequence: social = `type NOT IN RELATION_GRAPH_EXCLUDED_TYPES`. The lot
imports the constant and never re-types it. `connects_to` keeps `mutual`.

---

## 2. The write chokepoint

**R-04 — `write_relation` and `_find_relation_pair`.** [M]
Opened: `writes/relations.py:1-174`; `tooling/verify/canon_write_policy.txt:19`
(the single sanctioned `relation` write site).
Finding:
- `_find_relation_pair` (`:36-51`) matches both orders with no world
  filter and no type filter, and takes `.first()`.
- Delta mode (`:62-79`): on an existing row, only `intensity` and
  `last_evolved_at` change. The delta's `type` is used only when a row is
  created.
- New rows default to `direction='mutual'` (`:123`) and
  `visible_to_b=True` (`:124`).
- Set mode with `relation_id` (`:88-100`) snapshots history, then
  overwrites type, direction, visible_to_b and notes.
Consequence: after C3, a delta must land on the row where the changing side
is `entity_a`. Today it can land on the other side's row, which is exactly
what the two asymmetric prod pairs expose.

**R-05 — every delta producer already puts the changing side in `entity_a`.** [M]
Opened: `tick_normalize.py:673-674` (`entity_a_id: npc_id`),
`analyzer_transcript.py:308-313` (`entity_a` from `"entity_a_id"`/
`"entity_a"`/`"from"`), `cockpit/mutations.py:150-175` (`relation_delta`
effect, subject -> target), `:335-356` (`relation_change` applier),
`day_mutations.py:184-190` (`_emit_relation_change` never emits).
Consequence: an oriented lookup (perceiver = `entity_a`) matches producer
semantics. No payload shape changes.

**R-06 — `_find_relation_pair` has four callers with two meanings.** [M]
Opened: enumeration 8.3.
Finding: `writes/relations.py:68` (delta), `cockpit/mutations.py:556`
(`goal_change complete`, `relation_gte` prerequisite judge),
`tick_context.py:171` (briefing prerequisite line), and
`cockpit/crud/relations.py:129`, which returns the `connects_to` row just
written by `connect_locations`. The finder's docstring (`:37-45`) requires
the judge, the briefing and the write path to share one pair semantics.
Consequence: the three social callers move together to one oriented finder.
The `connects_to` caller keeps unordered semantics.

**R-07 — creator CRUD.** [M]
Opened: `cockpit/crud/relations.py:106-180`.
Finding:
- Create (`:112-146`): the sheet's entity becomes `entity_a`
  (`:136`); direction defaults to `mutual`, visible_to_b to True.
- The `connects_to` branch delegates to `connect_locations`
  (`:123-130`).
- PUT (`:149-170`) overwrites direction.
- DELETE (`:173-180`) hard-deletes the relation row only.

**R-08 — the link agent is a relation writer that emits all three directions.** [M]
Opened: `link_author.py:71`, `:243`, `:307-318`, `:561`, `:596-597`,
`:646-676`, `:830-843`, `:930-946`.
Finding:
- The model output carries `direction` (3 values) and `visible_to_b`
  (default True, `:318`).
- Staged rows are validated against `_LINK_DIRECTIONS`.
- Commit calls `write_relation(db, **row.payload)` (`:942`).
- The coherence pass can patch `direction` and `visible_to_b` on canon
  rows (`_CANON_RELATION_WHITELIST`, `:646`; `_apply_canon_relation_patch`,
  `:830-843`).
- Pair exclusion skips any pair holding a relation in either direction
  (`:243`, `:561`).
Consequence: without a change here, the link agent keeps writing `mutual`
and `b_to_a` social rows after the migration.

---

## 3. Readers

**R-09 — direction readers, behaviour per file.** [M]
Opened: enumeration 8.2, then each file.
- `context.py:128-142`: perceiver, and `_render_perception`.
- `tick_context.py:112-122`: perceiver and render. `tick_normalize.py:28`,
  `:113` import `_perceived_target`.
- `play_initiative.py:457-462`: `_npc_rel`.
- `lore_selectors.py:121-136` carries `subject_side`, but
  `lore_render.py:39-44` prints the raw `direction` and ignores it. The
  Lore surface has the same A/B defect as the sheet.
- `crud/_shared.py:153-168`: `_relation_dict` returns `role: a|b`.
- `crud/relations.py:196-208`: graph edges (`source=a`, `target=b`,
  `direction`).
- `crud/locations.py:257`: `connects_to`, structural.
- `link_context.py:101-102`: agent context.
- `day_concordance.py:281-303` (`_cast_relation`) reads both orders and
  keeps the max intensity per candidate. It never reads direction, so its
  behaviour is preserved.

**R-10 — three frontend surfaces show the raw vocabulary.** [M]
Opened:
- `creation/RelationsEditor.svelte`: raw select at `:14`, `:98-102` and
  `:136-140`; drops `role` at `:22-31`; "Visible to B" at `:108` and
  `:146`.
- `graph/consumers/relations.js`: `:84`; raw select `:109-124`; `:143`;
  PUT, POST and DELETE at `:148-166`.
- `creation/LinkAgent.svelte`: `:143-151`.

**R-11 — `relation.notes` is the perceiver's own characterization.** [M]
Opened: `context.py:137-142`, `tick_context.py:122`.
Finding: `notes` is rendered into the perceiver's context as
`- {name} : {notes} (perception : {type}, disposition : ...)`. It is the
perceiver's view of the other, read in play.
Consequence: this conflicts with N1's drafting detail "notes become the lien
fact's content". Moving notes changes two play readers, and it would expose
the perceiver's private characterization to every knower of the fact
(decision V).

**R-12 — `visible_to_b` has no play reader, and TRUE is a default, not a choice.** [M]
Opened: enumeration 8.5.
Finding:
- Written by `writes/relations.py`, the CRUD and the link agent.
- Read only by `crud/_shared.py:148` and `:165` (display) and
  `link_context.py:102` (agent context). No play assembler reads it.
- It defaults to TRUE in all three writers: `writes/relations.py:124`,
  `crud/relations.py:141`, `link_author.py:318`.
Consequence: turning every TRUE into a knowledge row would create knowledge
nobody decided. Those rows would then render in B's context
(`context.py:384`, NPC) and in the player block of the MJ context
(`context.py:732`). A PC would start "knowing" what every NPC feels toward
them (decision U).

---

## 4. Facts and knowledge

**R-13 — typed facts: the precedent exists.** [M]
Opened: `models/canon_knowledge.py` (`Fact`: `ck_fact_spine_exclusive`,
`default_level` default `'unaware'`); `writes/facts.py:66-74` (participants
refused on a typed fact); `create_fact` with `relation_id`, exercised by
`checks/fact_spine.py:126-135`; `scripts/migrate_v2_00_connects_to_facts.py:1-40`.
Finding: v2.00 created one typed fact per `connects_to` edge, with a
generated French content `"{name_a} communique avec {name_b}."`,
`default_level='knows'` and `created_by='migrate_v2_00'`. It was idempotent
(skips an edge that already has a fact) and post-checked by a checksum of
the whole `relation` table.
Consequence: the lien-fact migration follows this pattern.

**R-14 — a knowledge row can point at a typed fact.** [M]
Opened: `models/canon_knowledge.py:182-218` (`Knowledge`: `fact_id` NOT NULL,
`subject` NOT NULL); `writes/knowledge.py:208-225` (`write_knowledge`
accepts `fact_id`).
Finding: yes, but `subject` is still required text. `subject_entity_ids`
must not be passed for a typed fact (R-13).

**R-15 — deleting a relation that has a typed fact fails.** [M][E]
Opened: `db.py:126` (`PRAGMA foreign_keys=ON`); `crud/relations.py:173-180`;
experiment E-1.
Finding: the DELETE route removes only the relation row, so the fact's
foreign key rejects it with `IntegrityError` and the request fails with an
HTTP 500.
Consequences:
- Every `connects_to` edge that received a fact from v2.00 already cannot
  be deleted from the UI.
- After this lot, every social relation would share that fate unless the
  delete path is specified (decision T).

**R-16 — scoped defaults already reach play.** [M]
Opened: `context.py:384`, `:732`; `knowledge_resolve.py:278-300`.
Finding: the NPC context and the MJ player block union stored knowledge
rows with `resolve_default_rows`.
Consequence: a lien fact at `default_level='unaware'` renders for nobody
until a knowledge row or a scoped default names a knower.

---

## 5. Gates

**R-17 — checks that construct relations.** [M]
Opened: enumeration 8.8.
Finding:
- `fact_spine.py:126-129` builds a social `mutual` relation (`ally`)
  through `write_relation`.
- `context_disclosure_floor.py:105-112` builds `friendship` rows as
  `a_to_b`; they are already oriented.
- `door_coverage.py:131` and `known_reachability.py:126,226,279` build
  `connects_to` rows as `mutual`; these are structural and unaffected.
Consequence: `fact_spine`'s fixture must change if the chokepoint refuses
social `mutual`.

**R-18 — schema version.** [M]
Opened: `schema_version.py:15` (`"v2.03"`), head of
`world-engine-schema-changelog.md` (v2.03).
Finding: the next version is v2.04. The constant, the `schema_meta` row and
the doc header move in one commit.

---

## 6. Experiments (in-memory, never a real database)

**E-1 — relation delete with a typed fact, FK ON.**
```python
eng = create_engine("sqlite://")  # PRAGMA foreign_keys=ON on connect
# world, two locations, Relation(connects_to), Fact(relation_id=rel.id)
s.delete(s.get(Relation, r.id)); s.commit()
```
Output: `DELETE FAILED: IntegrityError (sqlite3.IntegrityError) FOREIGN KEY constraint failed`

**E-2 — partial unique index: one social row per oriented pair.** SQLite 3.45.1.
```sql
CREATE UNIQUE INDEX idx_relation_oriented_social ON relation(entity_a_id, entity_b_id)
  WHERE type NOT IN ('connects_to','controls');
```
Output: A->B `fear`, B->A `rejection` and two A->B `connects_to` rows are
accepted. A second social A->B row (`debt`) is rejected with
`UNIQUE constraint failed`. A partial index needs `CREATE INDEX` only, with
no table rebuild; a CHECK would need a table rebuild.

---

## 7. Side findings (outside TICKET-0090's stated scope)

**S-1 — `connects_to` edges born after v2.00 have no fact, and ticks cannot cross them.** [M]
`spatial_author.py:124-131` (`connect_locations`) writes the relation and
no fact. `tick_context.py:446-462` drops any edge without a fact
(fail-closed, reason `missing_fact`). Every edge created since v2.00 by a
region commit or by manual CRUD is therefore invisible to tick
reachability. The prod count is not measured (query in section 10). This
is the same defect class the lien facts would have if only the migration
created them (decision W).

**S-2 — a delta ignores its `type` on update (R-04).** A `relation_change`
typed `trust` lands on whatever row the pair holds.

**S-3 — the Lore surface prints the raw direction (R-09).**

---

## 8. Enumerations (raw output)

### 8.1 Direction vocabulary sites
```
$ grep -rn "RELATION_DIRECTIONS\s*=\|_LINK_DIRECTIONS\s*=\|_A_PERCEIVES\s*=\|_B_PERCEIVES\s*=\|direction in (" --include=*.py src
src/world_engine/tick_context.py:87:_A_PERCEIVES = ("a_to_b", "mutual")
src/world_engine/tick_context.py:88:_B_PERCEIVES = ("b_to_a", "mutual")
src/world_engine/cockpit/play_initiative.py:458:            if rel.entity_a_id == npc_id and rel.direction in ("a_to_b", "mutual"):
src/world_engine/cockpit/play_initiative.py:460:            if rel.entity_b_id == npc_id and rel.direction in ("b_to_a", "mutual"):
src/world_engine/cockpit/crud/_shared.py:141:RELATION_DIRECTIONS = ("mutual", "a_to_b", "b_to_a")
src/world_engine/link_author.py:71:_LINK_DIRECTIONS = ("mutual", "a_to_b", "b_to_a")
src/world_engine/context.py:113:_A_PERCEIVES = ("a_to_b", "mutual")
src/world_engine/context.py:114:_B_PERCEIVES = ("b_to_a", "mutual")
```

### 8.2 Files reading `direction` (src, models excluded)
```
      2 src/world_engine/cockpit/crud/_shared.py
      1 src/world_engine/cockpit/crud/locations.py
      3 src/world_engine/cockpit/crud/relations.py
      2 src/world_engine/cockpit/play_initiative.py
      2 src/world_engine/context.py
      8 src/world_engine/link_author.py
      1 src/world_engine/link_context.py
      1 src/world_engine/lore_render.py
      1 src/world_engine/lore_selectors.py
      2 src/world_engine/tick_context.py
      1 src/world_engine/writes/relations.py
```

### 8.3 `_find_relation_pair` callers
```
src/world_engine/tick_context.py:171:        rel = _find_relation_pair(session, goal.npc_id, row.target_entity_id)
src/world_engine/writes/relations.py:68:    rel = _find_relation_pair(db, entity_a_id, entity_b_id)
src/world_engine/cockpit/mutations.py:556:            rel = _find_relation_pair(db, npc_id, row.target_entity_id)
src/world_engine/cockpit/crud/relations.py:129:        rel = _find_relation_pair(db, entity_id, body.other_entity_id)
```

### 8.4 `write_relation` call sites
```
src/world_engine/cockpit/mutations.py:170:    write_relation(
src/world_engine/cockpit/mutations.py:346:    write_relation(
src/world_engine/cockpit/crud/relations.py:132:    rel = write_relation(
src/world_engine/cockpit/crud/relations.py:157:    write_relation(
src/world_engine/cockpit/routes/regions.py:282:                write_relation(
src/world_engine/cockpit/routes/regions.py:292:                write_relation(
src/world_engine/link_author.py:838:    write_relation(
src/world_engine/link_author.py:942:            write_relation(db, **row.payload)
src/world_engine/spatial_author.py:124:    write_relation(
```

### 8.5 `visible_to_b` (src, models excluded)
```
src/world_engine/writes/relations.py:64,73,84,96,108,124,147,163,170
src/world_engine/cockpit/crud/_shared.py:148:    {"name": "visible_to_b", "label": "Visible to B", "kind": "bool", "default": True},
src/world_engine/cockpit/crud/_shared.py:165:        "visible_to_b": rel.visible_to_b,
src/world_engine/cockpit/crud/relations.py:102:    visible_to_b: Optional[bool] = None
src/world_engine/cockpit/crud/relations.py:141:        visible_to_b=body.visible_to_b if body.visible_to_b is not None else True,
src/world_engine/cockpit/crud/relations.py:164:        visible_to_b=body.visible_to_b if body.visible_to_b is not None else rel.visible_to_b,
src/world_engine/link_context.py:102:            "visible_to_b": r.visible_to_b, "notes": r.notes,
src/world_engine/link_author.py:318:        "visible_to_b": bool(item.get("visible_to_b", True)),
src/world_engine/link_author.py:646:_CANON_RELATION_WHITELIST = {"intensity", "notes", "type", "direction", "visible_to_b"}
src/world_engine/link_author.py:674,676,835,842
```
(`writes/relations.py` and `link_author.py` line lists are condensed. Every
hit in them is a parameter pass-through or the whitelist, none a play
reader.)

### 8.6 `rel.notes`
```
src/world_engine/tick_context.py:122:    return f"- {name} : {rel.notes} (perception : {rel.type}, disposition : {adjective})"
src/world_engine/writes/relations.py:97:        rel.notes = notes
src/world_engine/cockpit/crud/_shared.py:166:        "notes": rel.notes,
src/world_engine/link_author.py:835:        "visible_to_b": rel.visible_to_b, "notes": rel.notes,
src/world_engine/context.py:140:        f"- {name} : {rel.notes} "
```

### 8.7 Frontend files naming the vocabulary
```
frontend/src/graph/consumers/relations.js
frontend/src/creation/LinkAgent.svelte
frontend/src/creation/RelationsEditor.svelte
```

### 8.8 Checks constructing relations
```
tooling/verify/checks/context_disclosure_floor.py:106:            type="friendship", direction="a_to_b", intensity=80,
tooling/verify/checks/context_disclosure_floor.py:110:            type="friendship", direction="a_to_b", intensity=10,
tooling/verify/checks/door_coverage.py:131:            type="connects_to", value=50, direction="mutual",
tooling/verify/checks/fact_spine.py:128:            type="ally", value=50, direction="mutual",
tooling/verify/checks/known_reachability.py:126:            type="connects_to", value=50, direction="mutual",
tooling/verify/checks/known_reachability.py:226:            type="connects_to", value=50, direction="mutual",
tooling/verify/checks/known_reachability.py:279:            type="connects_to", value=50, direction="mutual",
```

---

## 9. Open decisions (must lock before LOT-0090 is drafted)

Each is put to Nia in the planning conversation with options, a
recommendation and rejected alternatives. Recorded here once settled.

- **O** — where orientation lives: keep `direction`, constant `a_to_b` for
  social rows, guarded in the chokepoint (rec.) | drop the column for social
  rows | add a CHECK (needs a table rebuild).
- **P** — one social row per oriented pair, enforced by the partial unique
  index of E-2 (rec.) | several rows per oriented pair, keyed by type.
- **T** — delete semantics: the delete cascades the lien fact, its knowledge
  rows and its scoped defaults in one transaction (rec.) | deletion is
  refused while knowers exist.
- **U** — inherited `visible_to_b`: not converted to knowledge; the editor
  gains an explicit "B knows" control (rec.) | faithful conversion of every
  TRUE. Needs measurement Q1.
- **V** — lien fact content: a generated statement, with `notes` staying the
  perceiver's own view on the relation row (rec., amends N1's detail) |
  notes move into the fact.
- **W** — S-1 in this ticket, since the chokepoint change is the same
  (rec. if Q2 > 0) | its own ticket.

Drafting decisions to flag (no vote needed unless reversed):
- Link agent: prompt untouched; its output is normalized at commit
  (`mutual` -> two rows, `b_to_a` -> swapped).
- The coherence pass loses `direction` from its whitelist.
- The social delta, the `relation_gte` judge and the briefing move together
  to one oriented finder. The `connects_to` path keeps
  `_find_relation_pair`.
- Lien facts are born at `default_level='unaware'`.
- Link-agent pair exclusion stays "either direction".
- All four surfaces render by perceiver: RelationsEditor, the graph editor,
  LinkAgent and the Lore dossier.

## 10. Prod measurements requested

```sql
-- Q1 (decision U): inherited visibility by direction
SELECT direction, visible_to_b, COUNT(*) FROM relation
WHERE type NOT IN ('connects_to','controls') GROUP BY direction, visible_to_b;

-- Q2 (decision W): connects_to edges with no typed fact
SELECT COUNT(*) FROM relation r
WHERE r.type = 'connects_to'
  AND NOT EXISTS (SELECT 1 FROM fact f WHERE f.relation_id = r.id);
```

---

## 11. Addendum, 2026-09-22 — measurements returned and decisions locked

Locked: **O1, P1, T1, V1, W1** (recorded in TICKET-0090). U reopened, see
below.

Q1 (prod):
```
direction  visible_to_b  count
a_to_b     0             52
a_to_b     1             40
b_to_a     0              8
b_to_a     1              6
mutual     1             67
```
Q2 (prod): `2`. Those 2 edges are backfilled by W1.

**R-19 — where the directed FALSE values come from.** [M]
Opened: `tooling/tickets/TICKET-0036-npc-link-agent.md:40-43` (decisions
D1+D2+D3: asymmetric relations with `visible_to_b` are in scope from v1);
`scripts/seed_pilot.py:1664` (the `npc_link_pair` prompt asks the model to
prefer "a relation one side hides (visible_to_b false)");
`scripts/seed_pilot.py:3522-3742` (the seed writes 12 FALSE and 3 TRUE
explicitly); `frontend/src/creation/LinkAgent.svelte:150-151` (the staged
row's "visible a B" checkbox is editable before commit).
Finding: on directed rows, the value was proposed by design and passed a
review surface where it could be changed. It is a reviewed decision, not an
untouched default. On `mutual` rows the flag carries no information, since
both sides already perceive.
Consequence: the reactivation condition written for the rejected U2 ("Q1
shows FALSE in numbers") is met on directed rows. U goes back to Nia.

**R-20 — `visible_to_b` has no defined meaning on a `b_to_a` row.** [M][I]
Opened: R-12's enumeration (no play reader); `crud/_shared.py:148`
("Visible to B").
Finding: on a `b_to_a` row, entity_b is the perceiver, so "visible to B"
names the side that already feels. No code reads the flag, so no code fixes
whether it meant entity_b literally or the non-perceiving side [I].
Consequence: the 6 `b_to_a` TRUE rows cannot be converted mechanically
without choosing a meaning.
