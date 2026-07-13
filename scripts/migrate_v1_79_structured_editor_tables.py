"""Migration to schema v1.79 — structured-editor JSON columns relationalized
(TICKET-0025, BRIEF-0025-c).

Final corrective step of TICKET-0025: three JSON columns that already hid
behind structured UI editors move to relational tables.
`npc_goal.prerequisites` (chips editor, BRIEF-0024-a) becomes
`goal_prerequisite`, closed-vocabulary CHECK-constrained (K1: `relation_gte`
only). `event.involved_entities` (chips editor, H2 — a JSON array of entity
ids with no FK integrity) becomes the `event_entity` link table — real FK
integrity for the first time. `prompt_template.variables` (declared-
variable list) becomes `prompt_variable`.

In ONE transaction:
  a. Create `goal_prerequisite` (+ CHECK constraints + unique index),
     `event_entity` (+ unique index), `prompt_variable` (+ unique index).
  b. Copy `npc_goal.prerequisites` list items -> `goal_prerequisite` rows.
  c. Copy `event.involved_entities` ids -> `event_entity` rows — ids that
     no longer resolve to an entity are SKIPPED and counted in the log
     (historical events may reference deleted-world debris), not fatal.
  d. Copy `prompt_template.variables` -> `prompt_variable` rows.
  e. Drop the three JSON columns (SQLite >= 3.35 guard).

Read-only validation pass BEFORE any write, fail-closed:
  - any `npc_goal.prerequisites` item that isn't a well-formed
    `{"type": "relation_gte", "target_entity_id": <str>, "threshold": int
    1-100}` dict aborts the WHOLE migration, listing the goal id.
  - any `event.involved_entities` value that is non-NULL and not a list
    aborts likewise (individual unresolvable ids inside a well-formed list
    are a SKIP, not an abort — see item c above).
  - any `prompt_template.variables` value that is non-NULL and not a list
    of strings aborts likewise.

Idempotent: safe to re-run — skips entirely once `goal_prerequisite`
exists (the whole migration is one transaction, so a completed run is
all-or-nothing).

Run from the project root:
    python scripts/migrate_v1_79_structured_editor_tables.py
"""

from __future__ import annotations

import json
import sqlite3
import sys
import uuid
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from sqlalchemy import inspect, text  # noqa: E402

from world_engine.db import engine  # noqa: E402

MIN_SQLITE_VERSION = (3, 35)


def _load_goals(conn) -> list[dict]:
    rows = conn.execute(text(
        "SELECT id, world_id, prerequisites FROM npc_goal WHERE prerequisites IS NOT NULL"
    )).mappings().all()
    out = []
    for row in rows:
        prereqs = json.loads(row["prerequisites"]) if row["prerequisites"] else None
        out.append({"id": row["id"], "world_id": row["world_id"], "prerequisites": prereqs})
    return out


def _load_events(conn) -> list[dict]:
    rows = conn.execute(text(
        "SELECT id, involved_entities FROM event WHERE involved_entities IS NOT NULL"
    )).mappings().all()
    out = []
    for row in rows:
        involved = json.loads(row["involved_entities"]) if row["involved_entities"] else None
        out.append({"id": row["id"], "involved_entities": involved})
    return out


def _load_prompt_templates(conn) -> list[dict]:
    rows = conn.execute(text(
        "SELECT id, variables FROM prompt_template WHERE variables IS NOT NULL"
    )).mappings().all()
    out = []
    for row in rows:
        variables = json.loads(row["variables"]) if row["variables"] else None
        out.append({"id": row["id"], "variables": variables})
    return out


def _validate(goals: list[dict], events: list[dict], templates: list[dict]) -> list[str]:
    problems: list[str] = []
    for goal in goals:
        prereqs = goal["prerequisites"]
        if prereqs is None:
            continue
        if not isinstance(prereqs, list):
            problems.append(f"npc_goal {goal['id']}: prerequisites is not a list")
            continue
        for item in prereqs:
            if (
                not isinstance(item, dict)
                or item.get("type") != "relation_gte"
                or not isinstance(item.get("target_entity_id"), str)
                or not item.get("target_entity_id")
                or not isinstance(item.get("threshold"), int)
                or isinstance(item.get("threshold"), bool)
                or not (1 <= item.get("threshold", -1) <= 100)
            ):
                problems.append(f"npc_goal {goal['id']}: malformed prerequisite item {item!r}")
    for event in events:
        involved = event["involved_entities"]
        if involved is not None and not isinstance(involved, list):
            problems.append(f"event {event['id']}: involved_entities is not a list")
    for template in templates:
        variables = template["variables"]
        if variables is not None and (
            not isinstance(variables, list) or not all(isinstance(v, str) for v in variables)
        ):
            problems.append(f"prompt_template {template['id']}: variables is not a list of strings")
    return problems


def _create_tables(conn) -> None:
    conn.execute(text("""
        CREATE TABLE goal_prerequisite (
          id               TEXT PRIMARY KEY,
          world_id         TEXT NOT NULL REFERENCES world(id),
          goal_id          TEXT NOT NULL REFERENCES npc_goal(id),
          type             TEXT NOT NULL CHECK (type IN ('relation_gte')),
          target_entity_id TEXT NOT NULL REFERENCES entity(id),
          threshold        INTEGER NOT NULL CHECK (threshold BETWEEN 1 AND 100)
        )
    """))
    conn.execute(text(
        "CREATE UNIQUE INDEX idx_goal_prerequisite_unique "
        "ON goal_prerequisite(goal_id, type, target_entity_id)"
    ))
    conn.execute(text("""
        CREATE TABLE event_entity (
          id        TEXT PRIMARY KEY,
          event_id  TEXT NOT NULL REFERENCES event(id),
          entity_id TEXT NOT NULL REFERENCES entity(id)
        )
    """))
    conn.execute(text(
        "CREATE UNIQUE INDEX idx_event_entity_unique ON event_entity(event_id, entity_id)"
    ))
    conn.execute(text("""
        CREATE TABLE prompt_variable (
          id                  TEXT PRIMARY KEY,
          prompt_template_id  TEXT NOT NULL REFERENCES prompt_template(id),
          name                TEXT NOT NULL
        )
    """))
    conn.execute(text(
        "CREATE UNIQUE INDEX idx_prompt_variable_unique ON prompt_variable(prompt_template_id, name)"
    ))


def _insert_goal_prerequisites(conn, goals: list[dict]) -> int:
    inserted = 0
    for goal in goals:
        for item in (goal["prerequisites"] or []):
            conn.execute(text(
                "INSERT INTO goal_prerequisite (id, world_id, goal_id, type, target_entity_id, threshold) "
                "VALUES (:id, :world_id, :goal_id, :type, :target_entity_id, :threshold)"
            ), {
                "id": str(uuid.uuid4()),
                "world_id": goal["world_id"],
                "goal_id": goal["id"],
                "type": item["type"],
                "target_entity_id": item["target_entity_id"],
                "threshold": item["threshold"],
            })
            inserted += 1
    return inserted


def _insert_event_entities(conn, events: list[dict]) -> tuple[int, int]:
    inserted = 0
    skipped = 0
    for event in events:
        for entity_id in (event["involved_entities"] or []):
            exists = conn.execute(text(
                "SELECT 1 FROM entity WHERE id = :id"
            ), {"id": entity_id}).first()
            if not exists:
                skipped += 1
                continue
            conn.execute(text(
                "INSERT OR IGNORE INTO event_entity (id, event_id, entity_id) "
                "VALUES (:id, :event_id, :entity_id)"
            ), {"id": str(uuid.uuid4()), "event_id": event["id"], "entity_id": entity_id})
            inserted += 1
    return inserted, skipped


def _insert_prompt_variables(conn, templates: list[dict]) -> int:
    inserted = 0
    for template in templates:
        seen = set()
        for name in (template["variables"] or []):
            if not isinstance(name, str) or not name.strip() or name in seen:
                continue
            seen.add(name)
            conn.execute(text(
                "INSERT INTO prompt_variable (id, prompt_template_id, name) "
                "VALUES (:id, :prompt_template_id, :name)"
            ), {"id": str(uuid.uuid4()), "prompt_template_id": template["id"], "name": name})
            inserted += 1
    return inserted


def _drop_columns(conn) -> None:
    conn.execute(text("ALTER TABLE npc_goal DROP COLUMN prerequisites"))
    conn.execute(text("ALTER TABLE event DROP COLUMN involved_entities"))
    conn.execute(text("ALTER TABLE prompt_template DROP COLUMN variables"))


def main() -> None:
    inspector = inspect(engine)
    if "goal_prerequisite" in inspector.get_table_names():
        print("Table 'goal_prerequisite' already exists — migration already applied, skipping.")
        return

    if sqlite3.sqlite_version_info < MIN_SQLITE_VERSION:
        raise SystemExit(
            f"SQLite {'.'.join(map(str, MIN_SQLITE_VERSION))}+ is required for "
            f"ALTER TABLE ... DROP COLUMN (found {sqlite3.sqlite_version}). "
            "Upgrade SQLite, then re-run this migration — aborting, nothing written."
        )

    with engine.connect() as conn:
        goals = _load_goals(conn)
        events = _load_events(conn)
        templates = _load_prompt_templates(conn)

    problems = _validate(goals, events, templates)
    if problems:
        raise SystemExit(
            "Migration aborted — unexpected content found, nothing written:\n"
            + "\n".join(f"  - {p}" for p in problems)
            + "\nResolve in the live UI, then re-run."
        )

    with engine.begin() as conn:
        _create_tables(conn)
        goal_prereqs_inserted = _insert_goal_prerequisites(conn, goals)
        event_entities_inserted, event_entities_skipped = _insert_event_entities(conn, events)
        prompt_vars_inserted = _insert_prompt_variables(conn, templates)
        _drop_columns(conn)

    print(
        f"Migration v1.79 applied: goal_prerequisite + event_entity + prompt_variable "
        f"tables created, {goal_prereqs_inserted} goal_prerequisite row(s) inserted, "
        f"{event_entities_inserted} event_entity row(s) inserted "
        f"({event_entities_skipped} unresolvable id(s) skipped), "
        f"{prompt_vars_inserted} prompt_variable row(s) inserted, "
        f"npc_goal.prerequisites/event.involved_entities/prompt_template.variables "
        f"columns dropped."
    )


if __name__ == "__main__":
    main()
