# RECON-0003 — Canon-write paths and table classification facts (RESULT)

**REPORT ONLY.** No edit, no fix, no classification decision made. Every
claim below is cited `path:line` against the working tree at HEAD of
`ticket/0001` (commit `426b2a9` + untracked ticket/recon files).

---

## Zone A — Table inventory

### A1. Every SQLModel table class

All 24 tables are declared in exactly one module:
[src/world_engine/models.py](../../src/world_engine/models.py). No other
module in `src/` declares a `table=True` class (confirmed by a repo-wide
grep for `__tablename__` / `class .*table=True` — only `models.py` matched).

| # | Class | `__tablename__` | `file:line` |
|---|---|---|---|
| 1 | `World` | `world` | models.py:51-52 |
| 2 | `Entity` | `entity` | models.py:79-80 |
| 3 | `Character` | `character` | models.py:110-111 |
| 4 | `Location` | `location` | models.py:147-148 |
| 5 | `Faction` | `faction` | models.py:167-168 |
| 6 | `FactionMembership` | `faction_membership` | models.py:212-213 |
| 7 | `Relation` | `relation` | models.py:255-256 |
| 8 | `Knowledge` | `knowledge` | models.py:292-293 |
| 9 | `Ledger` | `ledger` | models.py:335-336 |
| 10 | `Session` | `session` | models.py:360-361 |
| 11 | `Batch` | `batch` | models.py:379-380 |
| 12 | `PassPlay` | `pass_play` | models.py:401-402 |
| 13 | `Gathering` | `gathering` | models.py:428-429 |
| 14 | `GatheringMember` | `gathering_member` | models.py:450-451 |
| 15 | `Conversation` | `conversation` | models.py:467-468 |
| 16 | `ConversationMessage` | `conversation_message` | models.py:504-505 |
| 17 | `ProposedMutation` | `proposed_mutation` | models.py:522-523 |
| 18 | `Event` | `event` | models.py:567-568 |
| 19 | `Artifact` | `artifact` | models.py:597-598 |
| 20 | `Item` | `item` | models.py:618-619 |
| 21 | `SkillDefinition` | `skill_definition` | models.py:650-651 |
| 22 | `Skill` | `skill` | models.py:674-675 |
| 23 | `DiscoverableDetail` | `discoverable_detail` | models.py:716-717 |
| 24 | `User` | `user` | models.py:760-761 |
| 25 | `PromptTemplate` | `prompt_template` | models.py:780-781 |

(Numbered 1-25 for reference; 24 concrete tables — `Session` and `Batch`
bring the count shown above to 25 rows because both are listed; the schema
itself has 24 tables total as declared.)

Fact: `models.py`'s own `__all__` (models.py:804-827) omits `FactionMembership`,
`Ledger`, and `SkillDefinition` — all three exist as real tables and are
imported directly by name elsewhere (e.g. `from ..models import
FactionMembership` in cockpit/app.py:68). Reported as a fact only; not a
write-path concern.

### A2. Structural signals per table

| Table | `change_history` (or equiv.) | Referenced by `writes.py`? | Written by `_apply_mutation`? | Append-only by doctrine comment? |
|---|---|---|---|---|
| `world` | none | no | no | no |
| `entity` | none (`created_at`/`updated_at` only) | no | yes (status_change branch, direct) | no |
| `character` | none | no | no (extension, never targeted directly) | no |
| `location` | none | no | no | no |
| `faction` | none | no | no | no |
| `faction_membership` | none — models.py:205-207 doctrine comment: "closed rows ARE the history... no `change_history` column here, by construction" | yes (`write_membership`) | no (no AI-proposal branch exists for this table — matches models.py:25-26 writes.py docstring) | insert/close-only by doctrine (writes.py:24-30) |
| `relation` | yes — `change_history: list` models.py:283-286 | yes (`write_relation`) | yes (relation_change branch) | no explicit append-only comment (mutable intensity, history-appended) |
| `knowledge` | yes — `change_history: list` models.py:322-325 | yes (`write_knowledge`, `_append_knowledge_history`) | yes (new_knowledge, knowledge_change, resource_change branches) | no |
| `ledger` | none (append-only is enforced by convention, not a column) — models.py:329-333 NOTE: "this table is INSERT-only. No code path may UPDATE or DELETE..." | yes (`write_ledger_entry`) | yes (resource_change branch) | **yes**, explicit doctrine comment models.py:331 |
| `session` | none | no | no | no |
| `batch` | none | no | no | no |
| `pass_play` | has `history: list` (models.py:417-420), same JSON-append shape as `change_history` | no | no (no live write path found in `src/`; a legacy pass-play/batch pipeline referenced in CLAUDE.md folder layout, no active write site located) | no |
| `gathering` | none | no | no | no — ephemeral by doctrine (models.py:426 comment) |
| `gathering_member` | none | no | no | no — ephemeral; `left_at` close-only per gathering.py comments |
| `conversation` | none (has `scene_state` JSON, itself doctrine-ephemeral — models.py:485-493) | no | no | no |
| `conversation_message` | none | no | no | no explicit comment, but no update/delete site found anywhere (append-only in practice) |
| `proposed_mutation` | none (status/reviewed_at/applied_at/creator_notes mutated in place) | no | n/a (this IS the mutation record) | no — deletable only via the documented `--force`-on-`status='proposed'` exception |
| `event` | none | no | no | no |
| `artifact` | none | no | no | no |
| `item` | none | no | yes (item_update branch, direct — dormant per CLAUDE.md) | no |
| `skill_definition` | none | no | no | no |
| `skill` | yes — `change_history: list` models.py:687-690 | no (skill's history append is hand-rolled in `cockpit/crud.py`, not via a `writes.py` helper) | no | no |
| `discoverable_detail` | none (has `discovered` flag, flipped by `_apply_mutation`) | no | yes (new_knowledge branch flips `discovered`, direct) | no |
| `user` | none | no | no | no |
| `prompt_template` | none | no | no | no |

---

## Zone B — Write-site inventory

### B1/B2. Every write site in `src/`, grouped by path membership

Legend for group column: (a) writes.py helper · (b) inside `_apply_mutation`
· (c) creator CRUD · (d) session/play machinery · (e) seed/migration/backup ·
(f) other/unattributed.

**Zero write sites** (grep-confirmed, no `.add`/`.delete`/`.execute` matches)
in: [context.py](../../src/world_engine/context.py),
[entity_author.py](../../src/world_engine/entity_author.py),
[region_author.py](../../src/world_engine/region_author.py),
[ledger.py](../../src/world_engine/ledger.py),
[resolution.py](../../src/world_engine/resolution.py),
[ollama_client.py](../../src/world_engine/ollama_client.py),
[db.py](../../src/world_engine/db.py).

#### `writes.py` (group a — the helpers themselves)

| site | function | table(s) | file:line |
|---|---|---|---|
| `db.add(rel)` ×2 | `write_relation` | `relation` | writes.py:216, writes.py:252 |
| `db.add(k)` | `write_knowledge` | `knowledge` | writes.py:318 |
| `db.add(entry)` | `write_ledger_entry` | `ledger` | writes.py:358 |
| `db.add(membership)` ×2 | `write_membership` | `faction_membership` | writes.py:419, writes.py:430 |
| `db.execute(text(...))` ×17 (raw DELETE, one per table + PRAGMA) | `delete_world_cascade` | 15 tables scoped to `world_id` + `world` itself — see writes.py:461-531 for the full per-table list | writes.py:461-531 |

#### `gathering.py` (group d — session/play machinery)

| site | function | table | file:line |
|---|---|---|---|
| `db.add(gathering)` | `generate_gatherings` | `gathering` | gathering.py:240 |
| `db.add(GatheringMember(...))` | `generate_gatherings` | `gathering_member` | gathering.py:242 |
| `row.left_at = now; db.add(row)` | `close_open_memberships` | `gathering_member` | gathering.py:276-277 |
| `db.add(GatheringMember(...))` | `migrate_npc` | `gathering_member` | gathering.py:317 |
| `source_g.status = ...; db.add(source_g)` | `migrate_npc` | `gathering` | gathering.py:349-351 |
| `gathering.status = ...; db.add(gathering)` | `enter_location` | `gathering` | gathering.py:391-393 |

Both tables written here (`gathering`, `gathering_member`) are the
ephemeral pair per module doctrine (gathering.py:198-199, 256-263,
296-298, 362-369) — never through `writes.py`, never a `proposed_mutation`.

#### `analyzer.py` (group d)

| site | function | table | file:line |
|---|---|---|---|
| `db.add(mutation)` (loop) | `analyze_window` | `proposed_mutation` | analyzer.py:817-818 |
| `conv.last_analyzed_turn = ...; db.add(conv)` | `analyze_window` | `conversation` | analyzer.py:819-820 |

`analyze_overhearing` (analyzer.py:395) *constructs* `ProposedMutation`
objects (analyzer.py:593, 626) but never calls `db.add` on them itself —
the caller (`cockpit/app.py` `_stream`, see below) adds them to its own
session. Reported as a fact for Zone C2/D1: this is a cross-module split
write (construct in `analyzer.py`, persist in `cockpit/app.py`).

#### `cockpit/app.py` — `_apply_mutation` (group b, app.py:691-955)

| mutation_type branch | write | table | via writes.py? | file:line |
|---|---|---|---|---|
| `relation_change` | `write_relation(mode="delta", ...)` | `relation` | yes | app.py:751-760 |
| `new_knowledge` | `write_knowledge(...)` | `knowledge` | yes | app.py:776-786 |
| `new_knowledge` (discovery flip) | `detail.discovered = True; db.add(detail)` | `discoverable_detail` | **no** — direct, no helper exists for this table | app.py:797-801 |
| `status_change` | `entity.status = ...; db.add(entity)` | `entity` | **no** — direct, no helper exists for this table | app.py:822-824 |
| `item_update` (dormant) | `item.equipped = ...; db.add(item)` | `item` | **no** — direct, no helper exists for this table | app.py:841-842 |
| `knowledge_change` | `_append_knowledge_history(row, ...)` (private helper, imported directly) + `row.level = ...; db.add(row)` | `knowledge` | **partially** — calls writes.py's *private* `_append_knowledge_history`, but bypasses the *public* `write_knowledge` entirely | app.py:865-869 |
| `resource_change` | `write_ledger_entry(...)` | `ledger` | yes | app.py:923-933 |
| `resource_change` (knowledge leg) | `write_knowledge(...)` | `knowledge` | yes | app.py:936-946 |

**See Zone C2 for the `knowledge_change` bypass — it is a genuine
two-convention situation on the same table (`knowledge`).**

#### `cockpit/app.py` — outside `_apply_mutation` (groups c/d mixed — this file hosts both creator-CRUD-adjacent routes and play-loop machinery)

| site | function | table | via writes.py? | group | file:line |
|---|---|---|---|---|---|
| `write_relation(mode="set", ...)` ×2 | `commit_region` | `relation` | yes | c (creator-direct region commit) | app.py:502-506, 512-516 |
| `db.add(w)` / `db.add(target)` | `activate_world` | `world` | no | c | app.py:983, 986 |
| `db.add(new_world)` / `db.add(w)` / `db.add(new_world)` | `create_world` | `world` | no | c | app.py:1012, 1016, 1019 |
| `db.add(w)` / `db.add(target)` | `_activate_world_core` | `world` | no | c | app.py:1039, 1043 |
| `_delete_world_cascade(world_id, db)` | `delete_world` | 15 tables + `world` (via writes.py) | yes | c | app.py:1058 |
| `db.add(entity)` / `db.add(character)` / `db.add(Skill(...))` ×N / `write_knowledge(...)` | `create_player_character` | `entity`, `character`, `skill`, `knowledge` | mixed (knowledge via helper; entity/character/skill direct) | c | app.py:1176-1216 |
| `db.add(sess)` | `_get_or_open_session` | `session` | no | d | app.py:1286 |
| `db.add(GatheringMember(...))` / `db.add(conv)` | `_join_gathering` | `gathering_member`, `conversation` | no | d | app.py:1497, 1504 |
| `db.add(ProposedMutation(...))` | `_propose_engine_injury` | `proposed_mutation` | no | d (engine-proposed, `proposed_by='engine'`) | app.py:2218-2236 |
| `db.add(ProposedMutation(...))` | `_propose_engine_discovery` | `proposed_mutation` | no | d | app.py:2251-2272 |
| `db.add(conv)` | `start_conversation` | `conversation` | no | d | app.py:2482 |
| `db.add(ConversationMessage(...))` | `say` (player line) | `conversation_message` | no | d | app.py:2591-2597 |
| `persist_db.add(ConversationMessage(...))` (frozen-scene MJ line) | `_stream` (nested in `say`) | `conversation_message` | no | d | app.py:2674-2681 |
| `persist_db.add(ConversationMessage(...))` (NPC physical-reaction line) | `_stream` | `conversation_message` | no | d | app.py:3042-3050 |
| `ss_db.add(ss_conv)` (scene_state write after verdict) | `_stream` | `conversation` | no | d | app.py:3090-3095 |
| (nested) `_propose_engine_injury(...)` | `_stream` | `proposed_mutation` | no | d | app.py:3099-3103 |
| `persist_db.add(ConversationMessage(...))` (dialogue NPC line) | `_stream` | `conversation_message` | no | d | app.py:3296-3304 |
| `persist_db.add(ConversationMessage(...))` (initiative NPC line) | `_stream` | `conversation_message` | no | d | app.py:3514-3522 |
| `persist_db.add(ConversationMessage(...))` (initiative MJ line) | `_stream` | `conversation_message` | no | d | app.py:3554-3562 |
| `persist_db.add(ConversationMessage(...))` (main MJ narration) | `_stream` | `conversation_message` | no | d | app.py:3576-3584 |
| `overhear_db.add(mut)` (loop) | `_stream` | `proposed_mutation` | no | d — see cross-module note above (mutations built in analyzer.py) | app.py:3603-3606 |
| `_perform_travel(conv.player_id, travel_dest_id, db)` | `_stream` | (delegates — see `_perform_travel` row below) | — | d | app.py:3569 |
| `conv.status = "closed"; ...; db.add(conv)` | `end_conversation` | `conversation` | no | d | app.py:3629-3631 |
| (delegates) `_join_gathering(...)` | `join_gathering` | `gathering_member`, `conversation` | no | d | app.py:3659 |
| `_write_scene_state(conv, new_ss); db.add(conv)` | `update_scene_state` | `conversation` | no | c (creator-direct, per docstring app.py:4093-4099) | app.py:4137-4139 |
| `open_conv.status=...; db.add(open_conv)` | `_perform_travel` | `conversation` | no | d | app.py:4182-4192 |
| `gm.left_at = now; db.add(gm)` | `_perform_travel` | `gathering_member` | no | d | app.py:4203-4205 |
| `char.current_location_id = ...; db.add(char)` | `_perform_travel` | `character` | no | d | app.py:4208-4209 |
| `db.add(new_conv)` | `scene_join` | `conversation` | no | d | app.py:3921 |
| `db.add(conv)` | `scene_join` | `conversation` | no | d | app.py:3991 |
| `gm.left_at=now; db.add(gm)` | `scene_leave` | `gathering_member` | no | d | app.py:4046-4047 |
| `open_conv.status="closed"; db.add(open_conv)` | `scene_leave` | `conversation` | no | d | app.py:4060-4062 |
| `db.delete(row)` (loop, `status=='proposed'` only) | `analyze_conversation_endpoint` (`force=True`) | `proposed_mutation` | no | d — matches documented `--force` exception | app.py:4377-4378 |
| `conv.last_analyzed_turn = 0; db.add(conv)` | `analyze_conversation_endpoint` | `conversation` | no | d | app.py:4381-4382 |
| `mut.status="rejected"; ...; db.add(mut)` | `reject_mutation` | `proposed_mutation` | no | c (review action) | app.py:4464-4468 |
| `mut.status="applied"; ...; db.add(mut)` | `approve_mutation` (success) | `proposed_mutation` | no | c | app.py:4528-4530 |
| `mut.status="approved"; ...; db.add(mut)` | `approve_mutation` (failure) | `proposed_mutation` | no | c | app.py:4538-4541 |
| `db.add(mut)` ×2 (approve success / needs-attention) | `batch_review_mutations` | `proposed_mutation` | no | c | app.py:4618, 4629 |
| `db.add(mut)` | `batch_review_mutations` (reject) | `proposed_mutation` | no | c | app.py:4652 |

`commit_region` (app.py:284-533) additionally calls the **crud.py
commit-free cores** (`_crud._create_entity_core`, `_crud._create_knowledge_core`)
directly, in dependency order, sharing app.py's own `db` session — see the
crud.py table below for what those cores write. This is the one cross-module
call chain where a creator-CRUD-owned core is invoked from `cockpit/app.py`
rather than through its own router.

#### `cockpit/crud.py` (group c — creator CRUD, all direct writes; `writes.py` helpers used where the table is one of `relation`/`knowledge`/`ledger`/`faction_membership`)

| site | route / core | table | via writes.py? | file:line |
|---|---|---|---|---|
| `db.add(entity)` / `db.add(ext_row)` | `_create_entity_core` | `entity` + one of `character`/`location`/`faction`/`item` | no | crud.py:589, 595 |
| `write_membership(mode="open", ...)` | `_create_entity_core` (character w/ `faction_id`) | `faction_membership` | yes | crud.py:600-609 |
| `db.add(entity)` | `update_entity` | `entity` | no | crud.py:653 |
| `db.add(ext)` | `update_entity` | one of `character`/`location`/`faction`/`item` | no | crud.py:667 |
| (delegates) `close_open_memberships(...)` | `update_entity` (location/status change) | `gathering_member` | no (delegates to `gathering.py`) | crud.py:674, 676 |
| `entity.status="inactive"; db.add(entity)` | `delete_entity` (soft delete) | `entity` | no | crud.py:698-700 |
| (delegates) `close_open_memberships(...)` | `delete_entity` | `gathering_member` | no | crud.py:701 |
| `write_relation(mode="set", ...)` | `create_relation` | `relation` | yes | crud.py:726-737 |
| `write_relation(mode="set", ...)` | `update_relation` | `relation` | yes | crud.py:751-760 |
| **`db.delete(rel)`** | `delete_relation` | `relation` | **no — hard delete** | crud.py:772 |
| `write_knowledge(...)` | `_create_knowledge_core` | `knowledge` | yes | crud.py:793-804 |
| `write_knowledge(...)` | `update_knowledge` | `knowledge` | yes | crud.py:825-835 |
| **`db.delete(k)`** | `delete_knowledge` | `knowledge` | **no — hard delete** | crud.py:847 |
| `write_membership(mode="open", ...)` | `_open_membership_core` | `faction_membership` | yes | crud.py:924-934 |
| `write_membership(mode="close", ...)` | `close_entity_membership` | `faction_membership` | yes | crud.py:961 |
| `skill.change_history=...; skill.tier=...; db.add(skill)` | `update_skill_tier` | `skill` | **no** — hand-rolled history append, not via a `writes.py` helper | crud.py:1082-1085 |
| `db.add(definition)`; `db.add(Skill(...))` (loop, backfill) | `create_skill_definition` | `skill_definition`, `skill` | no | crud.py:1152, 1165 |
| `db.add(definition)`; `db.add(skill)` (loop, re-base) | `update_skill_definition` | `skill_definition`, `skill` | no | crud.py:1207, 1216 |
| **`db.delete(skill)`** (loop) / **`db.delete(definition)`** | `delete_skill_definition` | `skill`, `skill_definition` | **no — hard delete, documented 2nd named exception (CLAUDE.md)** | crud.py:1247-1248 |
| `db.add(detail)` | `create_discoverable_detail` | `discoverable_detail` | no | crud.py:1324 |
| `db.add(detail)` | `update_discoverable_detail` | `discoverable_detail` | no | crud.py:1373 |
| **`db.delete(detail)`** | `delete_discoverable_detail` | `discoverable_detail` | **no — hard delete** | crud.py:1387 |
| `write_ledger_entry(...)` | `create_ledger_entry` | `ledger` | yes | crud.py:1521-1532 |

---

### B3. BLOCKING FINDING — dynamic table dispatch

One dynamic-dispatch write site exists, in a seed script, not in `src/`:
`scripts/seed_pilot.py`'s `get_or_create(session, model, id, **fields)`
(seed_pilot.py:55-64) does `obj = model(id=id, **fields); session.add(obj)`
where `model` is a parameter — the table is **not statically determinable
from the helper's own body**. It IS statically determinable **per call
site** (each of the ~52 call sites passes a literal `m.<Model>` as the
second positional argument, e.g. seed_pilot.py:1154-1156 passes `m.World`).
An AST-level static scan of `get_or_create`'s definition alone cannot name
the table; a scan that also resolves call-site arguments can. No such
dynamic-dispatch write site exists anywhere in `src/` — only in this one
seed script. Not marked as a hard BLOCKING FINDING for the `src/`-scoped
doctrine (seed_pilot.py is itself an E1 exemption candidate), but flagged
per B3's instruction since it does constrain a naive "grep the callee"
design.

---

## Zone C — `writes.py` surface

### C1. Public helpers, tables, callers

| helper | tables written | file:line | callers (file:line) |
|---|---|---|---|
| `write_relation` | `relation` | writes.py:138-253 | `cockpit/app.py`: _apply_mutation (751), commit_region (502, 512); `cockpit/crud.py`: create_relation (726), update_relation (751) |
| `write_knowledge` | `knowledge` | writes.py:256-319 | `cockpit/app.py`: _apply_mutation (776, 936), create_player_character (1205); `cockpit/crud.py`: _create_knowledge_core (793), update_knowledge (825) |
| `write_ledger_entry` | `ledger` | writes.py:322-359 | `cockpit/app.py`: _apply_mutation (923); `cockpit/crud.py`: create_ledger_entry (1521) |
| `write_membership` | `faction_membership` | writes.py:362-431 | `cockpit/crud.py`: _create_entity_core (600), _open_membership_core (924), close_entity_membership (961); `scripts/seed_pilot.py`: ensure_primary_membership (85) |
| `delete_world_cascade` | 15 tables (see writes.py:465-528) + `world` | writes.py:438-531 | `cockpit/app.py`: delete_world (1058), imported as `_delete_world_cascade` |
| `_append_knowledge_history` (private, underscore-prefixed) | `knowledge` (history-append only, no persistence itself) | writes.py:114-135 | `writes.write_knowledge` (internal, writes.py:293); **also imported directly by `cockpit/app.py`** (app.py:86 import list) and called from `_apply_mutation`'s `knowledge_change` branch (app.py:865) — see C2 |

### C2. Bypass report — same table, two conventions

**Finding: `knowledge` has two write conventions inside `cockpit/app.py`
itself.** `_apply_mutation`'s `new_knowledge` and `resource_change` branches
call the public `write_knowledge(...)` (app.py:776, 936) — the sanctioned
helper. But the `knowledge_change` branch (app.py:846-870) imports and
calls writes.py's *private*, underscore-prefixed `_append_knowledge_history`
directly (app.py:865), then mutates `row.level`/`row.source`/`row.updated_at`
and calls `db.add(row)` itself (app.py:866-869) — it never calls the public
`write_knowledge`. Both paths correctly append history and both live inside
the same sanctioned `_apply_mutation` function, so this is not a doctrine
breach in the "outside `_apply_mutation`" sense — but it IS two different
code shapes writing the same table, one going through the module's public
surface and one reaching around it into a private helper. Cited: app.py:84-92
(import list includes both `write_knowledge` and `_append_knowledge_history`
from `..writes`), app.py:865-869.

**Finding: three hard-deletes exist outside `writes.py`, on tables that
otherwise have "history is sacred" write conventions, and none of the three
is named in CLAUDE.md's closed list of hard-delete exceptions**
(CLAUDE.md's Invariants section states: "World block deletion
(`delete_world_cascade`) is the broadest sanctioned hard-delete of canon...
`skill_definition` deletion... is a second, narrower named exception... No
other delete-side helper exists; any new hard-delete path must be named
here, not added silently."):
- `cockpit/crud.py`'s `delete_relation` (crud.py:766-774): `db.delete(rel)`
  on a `relation` row — `relation` has a `change_history` column
  (models.py:283) that this route entirely discards along with the row.
- `cockpit/crud.py`'s `delete_knowledge` (crud.py:841-849): `db.delete(k)`
  on a `knowledge` row — same pattern, `knowledge.change_history`
  (models.py:322) discarded with the row.
- `cockpit/crud.py`'s `delete_discoverable_detail` (crud.py:1379-1389):
  `db.delete(detail)` on a `discoverable_detail` row — this table has no
  `change_history` column, so no history is discarded by this delete, but
  it is still an unnamed hard-delete-side helper per the CLAUDE.md sentence
  above.

Reported as fact only — whether these three are pre-existing, intentional,
undocumented exceptions, or a doctrine drift, is a classification-session
decision, not a recon judgment.

---

## Zone D — Check-design seams

### D1. Static-scan viability

Module boundaries alone are close to sufficient but not exact, because of
the C2 findings above:

- A "no canon write outside `writes.py` + an allowlist" grep/AST rule would
  need the allowlist to include, at minimum: `cockpit/app.py` (both
  `_apply_mutation` AND several non-`_apply_mutation` routes that write
  `world`/`entity`/`character`/`conversation`/`conversation_message`/
  `gathering`/`gathering_member`/`proposed_mutation` directly — none of
  which have a `writes.py` helper today), `cockpit/crud.py` (all its direct
  entity/extension/skill/discoverable_detail writes), `gathering.py`
  (`gathering`/`gathering_member`), `analyzer.py`
  (`proposed_mutation`/`conversation.last_analyzed_turn`).
- The rule would ALSO need to special-case the C2 `knowledge_change`
  bypass (private-helper import) if "uses `writes.py`" is meant to mean
  "uses `writes.py`'s public surface" — a plain `from ..writes import`
  check would pass it since `_append_knowledge_history` does live in
  `writes.py`.
- The three unnamed hard-deletes (delete_relation, delete_knowledge,
  delete_discoverable_detail) are structurally indistinguishable from any
  other `db.delete()` call by a static scan alone — a scan would need an
  explicit denylist/allowlist of delete-side call sites, since
  `writes.py`'s docstring claim ("the sole delete-side helper... is
  `delete_world_cascade`") is not enforced anywhere in code.
- `scripts/seed_pilot.py`'s `get_or_create` dynamic dispatch (Zone B3) means
  a pure "grep the function body" scan misses its per-call-site table; an
  AST scan resolving call arguments would not.

### D2. DB-assertion viability

| Table | Audit signal present? | Usable for a DB-level invariant? |
|---|---|---|
| `relation` | `change_history` JSON list | yes — could assert every UPDATE is preceded by an append (hard to express as a pure SQL/DB constraint without triggers; SQLite has no native audit-trigger idiom already in use here) |
| `knowledge` | `change_history` JSON list | yes, same caveat |
| `skill` | `change_history` JSON list | yes, same caveat |
| `ledger` | none besides `created_at` — append-only is convention, not schema-enforced (no trigger, no `CHECK`) | no — nothing in the schema itself prevents an UPDATE/DELETE; the guarantee is 100% code-discipline (`write_ledger_entry` is the only inserter, but nothing stops a future `db.delete(Ledger...)`) |
| `faction_membership` | none (`left_at` close pattern is the audit trail) | partial — could assert no row is ever hard-deleted (no `is_deleted`/tombstone needed since closing sets `left_at`), but only by absence-of-DELETE, not a positive column signal |
| `proposed_mutation` | `status`/`reviewed_at`/`applied_at`/`creator_notes` (implicit audit via state machine) | partial — the `--force`-deletes-`proposed`-only rule could be asserted at the DB level with a `BEFORE DELETE` trigger rejecting `status != 'proposed'`, but no such trigger exists today |
| everything else (`world`, `entity`, `character`, `location`, `faction`, `session`, `batch`, `pass_play`, `gathering`, `gathering_member`, `conversation`, `conversation_message`, `event`, `artifact`, `item`, `skill_definition`, `discoverable_detail`, `user`, `prompt_template`) | none | no — no column-level signal exists to hang a DB assertion on |

### D3. Check-plug-in seam

Confirmed unchanged from RECON-0002 Zone E
([RECON-0002-doc-partition.md:77](RECON-0002-doc-partition.md)):
checks are standalone Python scripts under
[tooling/verify/checks/*.py](../verify/checks/), run as a subprocess by
[tooling/verify/run.py](../verify/run.py) (run.py:37), and linked from a
ticket's `### Machine` section via a `-> verify/checks/<name>.py` line
(run.py:10, 13-23 — `machine_checks()` regex-scans that section). A
`single_canon_write.py` check would plug in identically: exit 0 = pass,
non-zero = fail, last stdout/stderr line surfaced as the message
(run.py:38-41). No new harness plumbing needed.

---

## Zone E — Known exemption candidates

### `scripts/seed_pilot.py`
Generic dynamic-dispatch writes via `get_or_create` (Zone B3) touching (per
call-site argument, non-exhaustive sample confirmed by reading call sites):
`m.World` (seed_pilot.py:1156), plus `m.User`/`m.Character`/`m.Entity`/
`m.Location`/`m.Faction`/`m.Skill`/`m.SkillDefinition`/`m.Relation` and
others across ~50 more call sites (seed_pilot.py:1168-2360-ish — not
individually enumerated here per the "report facts, don't enumerate every
seed row" scope). Also: `upsert_knowledge` (seed_pilot.py:98-122, `knowledge`
table, direct `session.add`/mutate, NOT via `writes.write_knowledge`),
`upsert_prompt_template` (seed_pilot.py:125-148, `prompt_template`),
`delete_if_exists` (seed_pilot.py:151-156, generic hard `session.delete`,
dynamic table, called at least once against `m.Knowledge`, seed_pilot.py:1970),
`align_relation_intensity` (seed_pilot.py:159+, direct `relation.intensity`
mutation — not shown to route through `write_relation`), and one call to
the sanctioned `writes.write_membership` (seed_pilot.py:28, 85-94).

### `scripts/backup.py`
Read-only. Confirmed: its only DB calls are two `ro.execute("SELECT ...")`
reads (backup.py:55-56). No write site.

### `scripts/init_db.py`
Schema-only: calls `create_db_and_tables()` (init_db.py:26, defined in
`world_engine.db`) — `CREATE TABLE`/index DDL via SQLModel metadata, no row
data written.

### `scripts/talk.py` (CLI live-conversation tool)
Direct writes, same shape as `cockpit/app.py`'s play loop but standalone:
`session` (talk.py:92-99), `conversation` (talk.py:132-151, and close at
221-223), `conversation_message` (talk.py:178-186, 207-215) — all direct
`db.add`, none via `writes.py` (none of these tables have a `writes.py`
helper regardless).

### `scripts/analyze_conversation.py` (CLI window-analysis tool)
Mirrors `cockpit/app.py`'s `analyze_conversation_endpoint` force-path
exactly: `db.delete(row)` on `proposed_mutation` rows where
`status == "proposed"` only (analyze_conversation.py:82-83), then
`conv.last_analyzed_turn = 0; db.add(conv)` (analyze_conversation.py:87-88).
Delegates the actual analysis writes to `analyzer.analyze_window`
(imported analyze_conversation.py:37), which is the same function
`cockpit/app.py` calls — no duplicate write logic for the analysis itself,
only for the force-reset preamble.

### `scripts/migrate_v1_*.py` (16 files)
All use raw `conn.execute(text(...))` (SQLAlchemy Core, not the ORM
session) for schema DDL (`ALTER TABLE`, `CREATE INDEX`, `DROP TABLE`).
Several also perform one-off **data** backfills via raw SQL, not just DDL:
- `migrate_v1_8_gatherings.py:60-64` — `INSERT INTO conversation (...)
  SELECT ...` (table rebuild/copy for the `gathering_id` column addition).
- `migrate_v1_39_faction_membership.py:105-106` — `INSERT INTO
  faction_membership ...` (backfills rows from the old `character.faction_id`
  column).
- `migrate_v1_54.py:58-59` — `UPDATE world SET is_active = 1 WHERE id = :id`
  (auto-activates the sole world row on a single-world DB).
- `migrate_v1_57.py:39-51` — `UPDATE character SET world_id = (...)`
  (backfills `character.world_id` from `entity.world_id`).
- `migrate_v1_65_pc_skill_backfill.py:69-70` — `INSERT INTO skill ...`
  (backfills the four base-domain skill rows for pre-existing PCs).

None of these five go through `writes.py` or any ORM session — all are raw
SQL against a `sqlalchemy.Connection`, run once, outside any live-app
request path.

---

## BLOCKING FINDINGS recap

1. **B3**: `scripts/seed_pilot.py`'s `get_or_create` helper dispatches to a
   table determined by a runtime parameter, not statically visible from the
   helper's own body (statically visible per call site only). No such
   dynamic-dispatch write site exists in `src/`.
2. **C2 (reported as a finding, not literally under B3, but load-bearing for
   check design)**: the `knowledge` table has two write shapes inside
   `_apply_mutation` itself — public `write_knowledge` (2 branches) vs. the
   private `_append_knowledge_history` + hand-rolled mutation (1 branch,
   `knowledge_change`, app.py:865-869).
3. **C2**: three hard-delete routes in `cockpit/crud.py` — `delete_relation`
   (crud.py:772), `delete_knowledge` (crud.py:847), and
   `delete_discoverable_detail` (crud.py:1387) — exist outside `writes.py`
   and are not named in CLAUDE.md's closed list of sanctioned hard-delete
   exceptions (`delete_world_cascade`, `skill_definition` cascade delete).
   `delete_relation` and `delete_knowledge` specifically discard a
   `change_history` column's contents along with the row.

These three are the facts most likely to change how "single sanctioned
canon-write path" gets defined and checked; the classification/design
decision is Nia's, per TICKET-0003.
