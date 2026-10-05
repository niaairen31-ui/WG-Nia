"""G1 check for TICKET-0096 (BRIEF-0096-A) -- the world cascade deletes every
world-scoped row, or refuses before deleting anything.

`writes/worlds.py::delete_world_cascade` is the one sanctioned hard delete
of a whole world. Its table lists are hand-written; this check keeps them
equal to the schema and proves, on a populated fixture, that the delete
commits under real FK enforcement.

W1 -- coverage (metadata). The world-reaching tables of
   `SQLModel.metadata` (a `world_id` column, or a foreign key to a
   world-reaching table) equal exactly the tables the module names:
   `_DIRECT_WORLD_SCOPED_DELETES`, the children of
   `_SUBQUERY_SCOPED_DELETES`, the roots and guarded children of
   `_REFUSING_TABLES`. No table is named twice; every named table exists.
W2 -- shape. Every direct table has a `world_id` column. Every subquery
   triple `(child, column, parent)` has `child.column` declared as a
   foreign key to `parent`, and `parent` is a direct table.
W3 -- fixture completeness. `_FIXTURE` names exactly the cascaded tables
   (direct plus subquery children), each once.
W4 -- delete. Two worlds carry one fixture row per cascaded table. The
   cascade on one world commits; `PRAGMA foreign_key_check` is empty;
   every table is back to the counts it had before the doomed world was
   built; `schema_reconcile.unaccounted_tables` is empty.
W5 -- refusal. A fixture world that also holds an `entity_type` row, and
   one that also holds its own `prompt_template` with a `prompt_version`,
   each make the cascade raise `WorldDeleteRefused` with the exact message
   below, and no row of any table has changed at that point.
W6 -- route. `DELETE /api/worlds/{id}` (the route function, called
   directly) answers 409 with that message on a refused world, and
   `{"ok": True, ...}` on a populated world.

Fresh temp-file SQLite database (`WORLD_ENGINE_DATABASE_URL` set before any
world_engine import) -- never Nia's DB. Zero cascaded tables, or a W4
count that did not grow when the doomed world was built, is a FAILURE.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []

ENTITY_TYPE_MESSAGE = (
    "Suppression refusée : ce monde porte des types d'entité personnalisés "
    "(Navire). Leur suppression n'est pas encore prise en charge."
)
# The ephemeral staging tables (TICKET-0036/0037 strata): no `writes/` module
# may name them, so each agent's own module deletes its world's rows, called
# by the delete route after the cascade (TICKET-0096, G1).
_STAGING_TABLES: tuple[str, ...] = ("link_batch", "link_batch_row", "npc_batch", "npc_batch_row")

PROMPT_MESSAGE = (
    "Suppression refusée : ce monde possède des gabarits de prompt propres "
    "(pt-{w}), dont les versions ne sont jamais effacées."
)

# One row per cascaded table, in insertion order (parents first). `{w}` is
# the world id. Values satisfy every NOT NULL column without a default and
# every CHECK of the schema. `skill.skill_definition_id` and
# `skill_definition.system_id` are set on purpose: they are the schema's two
# ON DELETE RESTRICT keys, so the fixture exercises them too.
_FIXTURE: tuple[tuple[str, dict], ...] = (
    ("entity", {"id": "{w}-char", "world_id": "{w}", "type": "character", "name": "A"}),
    ("entity", {"id": "{w}-loc", "world_id": "{w}", "type": "location", "name": "L"}),
    ("entity", {"id": "{w}-fac", "world_id": "{w}", "type": "faction", "name": "F"}),
    ("entity", {"id": "{w}-art", "world_id": "{w}", "type": "artifact", "name": "R"}),
    ("entity", {"id": "{w}-item", "world_id": "{w}", "type": "item", "name": "I"}),
    ("character", {"id": "{w}-char", "world_id": "{w}", "character_type": "npc"}),
    ("location", {"id": "{w}-loc"}),
    ("faction", {"id": "{w}-fac"}),
    ("artifact", {"id": "{w}-art"}),
    ("item", {"id": "{w}-item"}),
    ("conversation_window_config", {"id": "cwc-{w}", "world_id": "{w}"}),
    ("faction_membership", {"id": "fm-{w}", "world_id": "{w}", "entity_id": "{w}-char",
                            "faction_id": "{w}-fac"}),
    ("faction_role", {"id": "fr-{w}", "world_id": "{w}", "faction_id": "{w}-fac",
                      "name": "r", "created_by": "creator_crud"}),
    ("link_batch", {"id": "lb-{w}", "world_id": "{w}", "scope": "{{}}"}),
    ("link_batch_row", {"id": "lbr-{w}", "batch_id": "lb-{w}", "pair_a_id": "{w}-char",
                        "pair_b_id": "{w}-loc", "kind": "no_links", "payload": "{{}}"}),
    ("location_type_catalog", {"id": "ltc-{w}", "world_id": "{w}", "name": "t"}),
    ("lore_entry", {"id": "le-{w}", "world_id": "{w}", "statement": "s"}),
    ("lore_entry_row", {"id": "ler-{w}", "entry_id": "le-{w}", "row_table": "entity",
                        "row_id": "{w}-char", "action": "created"}),
    ("npc_batch", {"id": "nb-{w}", "world_id": "{w}", "scope": "{{}}"}),
    ("npc_batch_row", {"id": "nbr-{w}", "batch_id": "nb-{w}", "line_index": 0,
                       "kind": "draft", "payload": "{{}}"}),
    ("npc_goal", {"id": "ng-{w}", "world_id": "{w}", "npc_id": "{w}-char",
                  "description": "d", "horizon": "short"}),
    ("npc_price", {"id": "np-{w}", "world_id": "{w}", "entity_id": "{w}-char",
                   "tag": "t", "amount": 1}),
    ("npc_schedule", {"id": "ns-{w}", "world_id": "{w}", "npc_id": "{w}-char",
                      "phase": "matin", "location_id": "{w}-loc"}),
    ("obstacle", {"id": "ob-{w}", "world_id": "{w}", "location_id": "{w}-loc"}),
    ("obstacle_vertex", {"id": "obv-{w}", "obstacle_id": "ob-{w}", "vertex_order": 0,
                         "x": 0.0, "y": 0.0}),
    ("passage", {"id": "pas-{w}", "world_id": "{w}", "entity_id": "{w}-char",
                 "location_id": "{w}-loc", "last_at": "2026-01-01 00:00:00"}),
    ("relation", {"id": "rel-{w}", "world_id": "{w}", "entity_a_id": "{w}-char",
                  "entity_b_id": "{w}-loc", "type": "knows"}),
    ("rencontre", {"id": "ren-{w}", "world_id": "{w}", "entity_lo_id": "{w}-char",
                   "entity_hi_id": "{w}-loc", "first_at": "2026-01-01 00:00:00",
                   "last_at": "2026-01-01 00:00:00", "source": "fixture"}),
    ("session", {"id": "ses-{w}", "world_id": "{w}", "number": 1}),
    ("skill_system", {"id": "ss-{w}", "world_id": "{w}", "name": "s"}),
    ("visit", {"id": "vis-{w}", "world_id": "{w}", "player_id": "{w}-char",
               "location_id": "{w}-loc"}),
    ("world_law", {"id": "wl-{w}", "world_id": "{w}", "text": "t"}),
    ("agenda", {"id": "ag-{w}", "world_id": "{w}", "owner_entity_id": "{w}-char",
                "title": "t"}),
    ("agenda_step", {"id": "ags-{w}", "agenda_id": "ag-{w}", "step_order": 1,
                     "objective": "o"}),
    ("agenda_step_requirement", {"id": "agr-{w}", "world_id": "{w}", "step_id": "ags-{w}",
                                 "type": "knowledge", "target_key": "k"}),
    ("batch", {"id": "bat-{w}", "session_id": "ses-{w}"}),
    ("door", {"id": "door-{w}", "world_id": "{w}", "location_id": "{w}-loc",
              "target_location_id": "{w}-loc", "x": 0.0, "y": 0.0}),
    ("event", {"id": "ev-{w}", "world_id": "{w}", "title": "t"}),
    ("event_entity", {"id": "eve-{w}", "event_id": "ev-{w}", "entity_id": "{w}-char"}),
    ("fact", {"id": "fa-{w}", "world_id": "{w}", "content": "c",
              "created_by": "creator_crud"}),
    ("fact_default", {"id": "fd-{w}", "world_id": "{w}", "fact_id": "fa-{w}",
                      "scope_type": "world", "level": "knows", "created_by": "creator_crud"}),
    ("fact_participant", {"id": "fp-{w}", "world_id": "{w}", "fact_id": "fa-{w}",
                          "entity_id": "{w}-char"}),
    ("discoverable_detail", {"id": "dd-{w}", "world_id": "{w}", "location_id": "{w}-loc",
                             "subject": "s", "content": "c", "fact_id": "fa-{w}"}),
    ("gathering", {"id": "ga-{w}", "world_id": "{w}", "session_id": "ses-{w}",
                   "location_id": "{w}-loc"}),
    ("gathering_member", {"id": "gm-{w}", "gathering_id": "ga-{w}", "entity_id": "{w}-char"}),
    ("goal_agenda_link", {"id": "gal-{w}", "world_id": "{w}", "goal_id": "ng-{w}",
                          "agenda_id": "ag-{w}", "created_by": "creator_crud"}),
    ("goal_prerequisite", {"id": "gp-{w}", "world_id": "{w}", "goal_id": "ng-{w}",
                           "type": "relation_gte", "target_entity_id": "{w}-loc",
                           "threshold": 50}),
    ("knowledge", {"id": "kn-{w}", "entity_id": "{w}-char", "fact_id": "fa-{w}",
                   "level": "knows"}),
    ("observation_run", {"id": "or-{w}", "world_id": "{w}", "location_id": "{w}-loc",
                         "max_beats": 1, "quiescence_limit": 1, "cooldown_beats": 1,
                         "debt_weight": 1.0, "propensity_mode": "flat", "model": "m"}),
    ("observation_run_template", {"id": "ort-{w}", "run_id": "or-{w}", "usage": "u",
                                  "template_id": "t", "version": 1}),
    ("pass_play", {"id": "pp-{w}", "batch_id": "bat-{w}", "session_id": "ses-{w}",
                   "character_id": "{w}-char", "declared_action": "a"}),
    ("skill_definition", {"id": "sd-{w}", "world_id": "{w}", "name": "Escrime",
                          "base_domain": "agility", "system_id": "ss-{w}"}),
    ("unresolved_mention", {"id": "um-{w}", "world_id": "{w}", "surface": "s",
                            "reason": "r"}),
    ("conversation", {"id": "co-{w}", "world_id": "{w}", "session_id": "ses-{w}",
                      "player_id": "{w}-char"}),
    ("conversation_message", {"id": "cm-{w}", "conversation_id": "co-{w}",
                              "turn_order": 1, "speaker": "s", "content": "c"}),
    ("day_mention_choice", {"id": "dmc-{w}", "world_id": "{w}", "pass_play_id": "pp-{w}",
                            "category": "person", "surface_form": "s",
                            "trigger": "near", "candidate_ids": "[]",
                            "evidence_fact_ids": "[]", "verdict": "accepted",
                            "chosen_entity_id": "{w}-char", "attempts": 1}),
    ("day_mention_choice_candidate", {"id": "dmcc-{w}", "choice_id": "dmc-{w}",
                                      "ordinal": 1, "entity_id": "{w}-char"}),
    ("day_mention_choice_evidence", {"id": "dmce-{w}", "choice_id": "dmc-{w}",
                                     "ordinal": 1, "fact_id": "fa-{w}"}),
    ("day_mention_review", {"id": "dmr-{w}", "world_id": "{w}", "choice_id": "dmc-{w}",
                            "verdict": "agreed", "entity_id": "{w}-char"}),
    ("day_rewrite", {"id": "drw-{w}", "world_id": "{w}", "pass_play_id": "pp-{w}",
                     "generation": 1, "rendered_text": "t"}),
    ("day_mention_resolution", {"id": "dmres-{w}", "world_id": "{w}", "rewrite_id": "drw-{w}",
                                "ordinal": 1, "category": "person", "surface_form": "s",
                                "kind": "named", "verdict": "unmatched"}),
    ("ledger", {"id": "led-{w}", "world_id": "{w}", "entity_id": "{w}-char", "amount": 1}),
    ("observation_beat", {"id": "obb-{w}", "run_id": "or-{w}", "beat_index": 0,
                          "outcome": "silence"}),
    ("observation_intent", {"id": "obi-{w}", "run_id": "or-{w}", "beat_id": "obb-{w}",
                            "npc_id": "{w}-char", "propensity": 0.0,
                            "cooldown_active": 0, "debt_score": 0.0,
                            "final_score": 0.0, "call_status": "ok"}),
    ("proposed_mutation", {"id": "pm-{w}", "world_id": "{w}", "source_type": "fixture",
                           "mutation_type": "fixture", "payload": "{{}}"}),
    ("observation_mutation_link", {"id": "oml-{w}", "run_id": "or-{w}",
                                   "mutation_id": "pm-{w}"}),
    ("skill", {"id": "sk-{w}", "character_id": "{w}-char", "domain": "agility",
               "skill_definition_id": "sd-{w}"}),
    ("skill_resolution", {"id": "sr-{w}", "world_id": "{w}", "conversation_id": "co-{w}",
                          "surface_form": "s", "verdict": "unmatched"}),
)


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    tmp_dir = tempfile.mkdtemp()
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{pathlib.Path(tmp_dir) / 'check.db'}"
    os.environ.setdefault("WORLD_ENGINE_ENV", "test")
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or name.startswith("world_engine."):
            del sys.modules[name]
    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def _reaching_tables(tables) -> set[str]:
    reach: dict[str, bool] = {}

    def walk(name: str, seen: frozenset) -> bool:
        if name == "world":
            return True
        if name in seen:
            return False
        table = tables[name]
        if "world_id" in table.c:
            return True
        return any(walk(fk.column.table.name, seen | {name}) for fk in table.foreign_keys)

    for name in tables:
        reach[name] = name != "world" and walk(name, frozenset())
    return {name for name, hit in reach.items() if hit}


def _named_tables(worlds) -> list[str]:
    named = list(worlds._DIRECT_WORLD_SCOPED_DELETES) + list(_STAGING_TABLES)
    named += [child for child, _col, _parent in worlds._SUBQUERY_SCOPED_DELETES]
    for root, _label, children, _message in getattr(worlds, "_REFUSING_TABLES", ()):
        named += [root, *children]
    return named


def rule_w1_w2(tables, worlds) -> None:
    named = _named_tables(worlds)
    for name in sorted({n for n in named if named.count(n) > 1}):
        fail(f"W1 table named twice: {name}")
    for name in sorted(set(named) - set(tables)):
        fail(f"W1 named table does not exist: {name}")
    reaching = _reaching_tables(tables)
    for name in sorted(reaching - set(named)):
        fail(f"W1 world-reaching table not named by the cascade: {name}")
    for name in sorted(set(named) & set(tables) - reaching):
        fail(f"W1 named table does not reach world: {name}")
    for name in worlds._DIRECT_WORLD_SCOPED_DELETES:
        if name in tables and "world_id" not in tables[name].c:
            fail(f"W2 direct table has no world_id column: {name}")
    for child, column, parent in worlds._SUBQUERY_SCOPED_DELETES:
        if child not in tables or column not in tables[child].c:
            fail(f"W2 subquery column missing: {child}.{column}")
            continue
        targets = {fk.column.table.name for fk in tables[child].c[column].foreign_keys}
        if parent not in targets:
            fail(f"W2 {child}.{column} is not a foreign key to {parent}")
        if parent not in worlds._DIRECT_WORLD_SCOPED_DELETES:
            fail(f"W2 subquery parent is not a direct table: {parent}")


def rule_w3(worlds) -> None:
    cascaded = set(worlds._DIRECT_WORLD_SCOPED_DELETES)
    cascaded |= {child for child, _col, _parent in worlds._SUBQUERY_SCOPED_DELETES}
    cascaded |= set(_STAGING_TABLES)
    fixture = {table for table, _row in _FIXTURE}
    if not cascaded:
        fail("W3 vacuous: the cascade names no table")
    for name in sorted(cascaded - fixture):
        fail(f"W3 cascaded table has no fixture row: {name}")
    for name in sorted(fixture - cascaded):
        fail(f"W3 fixture row for a table the cascade does not delete: {name}")


def _insert(db, table: str, row: dict, world_id: str) -> None:
    from sqlalchemy import text

    values = {k: (v.format(w=world_id) if isinstance(v, str) else v) for k, v in row.items()}
    cols = ", ".join(values)
    marks = ", ".join(f":{k}" for k in values)
    db.execute(text(f"INSERT INTO {table} ({cols}) VALUES ({marks})"), values)


def _build_world(engine, world_id: str) -> None:
    from sqlmodel import Session
    from sqlalchemy import text

    with Session(engine) as db:
        db.execute(text("INSERT INTO world (id, name, is_active) VALUES (:w, :w, 0)"),
                   {"w": world_id})
        for table, row in _FIXTURE:
            _insert(db, table, row, world_id)
        db.commit()


def _counts(db, names) -> dict[str, int]:
    from sqlalchemy import text

    return {n: db.execute(text(f"SELECT COUNT(*) FROM {n}")).scalar_one() for n in names}


def rule_w4(engine, tables) -> None:
    from sqlmodel import Session
    from sqlalchemy import text

    import world_engine.link_author as link_author
    import world_engine.npc_group_author as npc_group_author
    from world_engine.schema_reconcile import unaccounted_tables
    from world_engine.writes import delete_world_cascade

    purge_link = getattr(link_author, "purge_world_link_batches", None)
    purge_npc = getattr(npc_group_author, "purge_world_npc_batches", None)
    if purge_link is None or purge_npc is None:
        fail("W4 purge_world_link_batches / purge_world_npc_batches missing")

    names = sorted(tables)
    _build_world(engine, "keep")
    with Session(engine) as db:
        before = _counts(db, names)
    _build_world(engine, "doom")
    with Session(engine) as db:
        grown = _counts(db, names)
    for table in sorted({t for t, _row in _FIXTURE}):
        if grown[table] <= before[table]:
            fail(f"W4 vacuous: fixture added no row to {table}")
    with Session(engine) as db:
        try:
            delete_world_cascade("doom", db)
            for purge in (purge_link, purge_npc):
                if purge is not None:
                    purge("doom", db)
            violations = db.execute(text("PRAGMA foreign_key_check")).fetchall()
            db.commit()
        except Exception as exc:  # noqa: BLE001 -- the regression is an exception
            db.rollback()
            fail(f"W4 cascade on a populated world raised {type(exc).__name__}")
            return
    for row in violations:
        fail(f"W4 foreign_key_check violation: {tuple(row)}")
    with Session(engine) as db:
        after = _counts(db, names)
        for table in names:
            if after[table] != before[table]:
                fail(f"W4 {table}: {after[table]} rows after the cascade, "
                     f"expected {before[table]}")
        leftover = unaccounted_tables(engine, db)
        if leftover:
            fail(f"W4 unaccounted tables after the cascade: {leftover}")


def _refused_world(engine, world_id: str, kind: str) -> None:
    from sqlmodel import Session
    from sqlalchemy import text

    _build_world(engine, world_id)
    with Session(engine) as db:
        if kind == "entity_type":
            db.execute(text(
                "INSERT INTO entity_type (id, world_id, name, slug, physical_table) "
                "VALUES (:i, :w, 'Navire', :s, :p)"
            ), {"i": f"et-{world_id}", "w": world_id, "s": f"navire_{world_id}",
                "p": f"ext_navire_{world_id}"})
        else:
            db.execute(text(
                "INSERT INTO prompt_template (id, name, usage, world_id) "
                "VALUES (:i, 'p', 'fixture', :w)"
            ), {"i": f"pt-{world_id}", "w": world_id})
            db.execute(text(
                "INSERT INTO prompt_version (id, prompt_template_id, version_number, "
                "system_prompt, user_template) VALUES (:i, :t, 1, 's', 'u')"
            ), {"i": f"pv-{world_id}", "t": f"pt-{world_id}"})
        db.commit()


def rule_w5(engine, tables) -> None:
    from sqlmodel import Session

    import world_engine.writes as writes

    refused = getattr(writes, "WorldDeleteRefused", None)
    if refused is None:
        fail("W5 world_engine.writes exports no WorldDeleteRefused")
        return

    names = sorted(tables)
    cases = (("refuse_type", "entity_type", ENTITY_TYPE_MESSAGE),
             ("refuse_prompt", "prompt_template", PROMPT_MESSAGE.format(w="refuse_prompt")))
    for world_id, kind, message in cases:
        _refused_world(engine, world_id, kind)
        with Session(engine) as db:
            before = _counts(db, names)
            try:
                writes.delete_world_cascade(world_id, db)
            except refused as exc:
                if str(exc) != message:
                    fail(f"W5 {kind}: message {str(exc)!r}, expected {message!r}")
            except Exception as exc:  # noqa: BLE001 -- any other outcome is the defect
                fail(f"W5 {kind}: the cascade raised {type(exc).__name__} instead of refusing")
            else:
                fail(f"W5 {kind}: the cascade did not refuse")
            if _counts(db, names) != before:
                fail(f"W5 {kind}: rows changed before the refusal")
            db.rollback()


def rule_w6(engine) -> None:
    from fastapi import HTTPException
    from sqlmodel import Session

    from world_engine.cockpit.routes.creator import delete_world

    _refused_world(engine, "route_refuse", "entity_type")
    with Session(engine) as db:
        try:
            delete_world("route_refuse", db)
        except HTTPException as exc:
            if exc.status_code != 409 or exc.detail != ENTITY_TYPE_MESSAGE:
                fail(f"W6 refused world answered {exc.status_code} {exc.detail!r}")
        else:
            fail("W6 refused world did not answer 409")
    _build_world(engine, "route_ok")
    with Session(engine) as db:
        result = delete_world("route_ok", db)
    if not (isinstance(result, dict) and result.get("ok") is True):
        fail(f"W6 populated world: route answered {result!r}")


def main() -> int:
    engine = _fresh_engine()
    from sqlmodel import SQLModel

    import world_engine.models  # noqa: F401 -- registers every table
    from world_engine.writes import worlds

    tables = SQLModel.metadata.tables
    if not hasattr(worlds, "_REFUSING_TABLES"):
        fail("W1 writes/worlds.py declares no _REFUSING_TABLES")
    rule_w1_w2(tables, worlds)
    rule_w3(worlds)
    rule_w4(engine, tables)
    rule_w5(engine, tables)
    rule_w6(engine)
    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print("PASS: world_cascade -- every world-scoped table is deleted or guarded; "
          "a populated world deletes under FK enforcement; refusals delete nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
