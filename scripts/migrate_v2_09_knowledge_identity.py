"""Migration v2.09 — knowledge identity by fact (TICKET-0097, BRIEF-0097-A).

What an entity knows becomes identified by the fact it knows. One
transaction, in this order:

- S1 guard (E1): no world holds a `knowledge.subject` spread over more than
  one `fact_id`, `creator_meta` excepted (each creator note is its own fact
  on purpose). A split aborts the run, writing nothing, and lists the
  groups — there is no merge.
- S2 absorb (F1): every `(entity_id, fact_id)` group holding more than one
  row keeps one survivor — highest level on `KNOWLEDGE_LEVEL_LADDER`, then
  latest `updated_at`, then smallest `id` — and each other row's state is
  appended to the survivor's `change_history` (`changed_by =
  'migrate_v2_09'`, `absorbed_knowledge_id`) before the row is deleted.
  `unresolved_mention.knowledge_id` pointing at an absorbed row is repointed
  to the survivor first.
- S3 `CREATE UNIQUE INDEX idx_knowledge_entity_fact ON knowledge(entity_id,
  fact_id)`.
- S4 link-agent facts (G): every fact whose content is exactly `npc:<id>`,
  where `<id>` is an `entity` of the fact's own world (any status), gets
  that entity as a `fact_participant` (read before write). When `<id>` has
  the identity-token shape (`prose_render.TOKEN_RE`, a 36-character uuid),
  the content is also rewritten to `[[e:<id>|<name>]]`, the previous content
  appended to the fact's `change_history` first; a non-uuid id (the pilot
  seed's hand-written ids) keeps its content. A `npc:<id>` fact whose id is
  no entity of that world is left untouched and reported.
- S5 `ALTER TABLE discoverable_detail ADD COLUMN fact_id TEXT REFERENCES
  fact(id)` (H1).
- S6 day gates (D1'a): every `agenda_step_requirement` of type `knowledge`
  whose `target_key` equals the `subject` of knowledge rows of its world on
  exactly one fact gets `target_key = <that fact_id>`. Any other key is left
  untouched and reported.
- S7 post-checks, then `schema_meta` converges to v2.09.

`knowledge.subject` itself is not touched: v2.10 (BRIEF-0097-F) drops it.

Idempotent: S1 and S2 find nothing on a second run; S3 and S5 are guarded
by `sqlite_master` / `PRAGMA table_info`; S4 attaches a participant only when
absent and tokenizes only `npc:<uuid>` content, which a first run rewrote; S6 matches only keys that are subjects.

Run from the project root (after `python scripts/backup.py`), then run
`migrate_v2_10_drop_knowledge_subject.py` before starting the cockpit:

    python scripts/migrate_v2_09_knowledge_identity.py
"""

from __future__ import annotations

import json
import os
import re
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

_env = os.environ.get("WORLD_ENGINE_ENV")
if not _env and not os.environ.get("WORLD_ENGINE_DATABASE_URL"):
    print(
        "migrate_v2_09_knowledge_identity.py refuses to run without WORLD_ENGINE_ENV "
        "or WORLD_ENGINE_DATABASE_URL set (fail-closed, TICKET-0049) — got: "
        f"{_env or 'unset'}.",
        file=sys.stderr,
    )
    sys.exit(1)

from sqlmodel import Session  # noqa: E402

from world_engine import models  # noqa: E402
from world_engine.db import engine  # noqa: E402
from world_engine.prose_render import entity_token  # noqa: E402
from world_engine.writes.knowledge import KNOWLEDGE_LEVEL_LADDER  # noqa: E402

TARGET_VERSION = "v2.09"
CREATED_BY = "migrate_v2_09"
CREATOR_META = "creator_meta"
INDEX_NAME = "idx_knowledge_entity_fact"
NPC_CONTENT = re.compile(r"^npc:(\S+)$")
UUID_ID = re.compile(r"^[0-9a-fA-F-]{36}$")


class Abort(Exception):
    """A pre- or post-check failed; the transaction is rolled back."""


def _now() -> str:
    return datetime.now(UTC).isoformat()


def split_subjects(cursor) -> list[tuple]:
    """(world name, subject, fact count) of every subject spread over more
    than one fact within a world, `creator_meta` excepted."""
    return cursor.execute(
        "SELECT w.name, k.subject, COUNT(DISTINCT k.fact_id) FROM knowledge k "
        "JOIN entity e ON e.id = k.entity_id JOIN world w ON w.id = e.world_id "
        "WHERE k.subject <> ? GROUP BY e.world_id, k.subject "
        "HAVING COUNT(DISTINCT k.fact_id) > 1 ORDER BY w.name, k.subject",
        (CREATOR_META,),
    ).fetchall()


def _rank(level: str) -> int:
    return KNOWLEDGE_LEVEL_LADDER.index(level) if level in KNOWLEDGE_LEVEL_LADDER else -1


def _absorb_group(cursor, rows: list[tuple]) -> int:
    """rows: (id, level, content, source, is_incorrect, updated_at,
    change_history). Keeps the survivor, absorbs the others. Returns the
    number of rows deleted."""
    ordered = sorted(rows, key=lambda r: r[0])
    ordered = sorted(ordered, key=lambda r: r[5] or "", reverse=True)
    ordered = sorted(ordered, key=lambda r: _rank(r[1]), reverse=True)
    survivor, absorbed = ordered[0], ordered[1:]
    history = json.loads(survivor[6] or "[]")
    for row in absorbed:
        history.append({
            "level": row[1], "content": row[2], "source": row[3],
            "is_incorrect": bool(row[4]), "updated_at": row[5],
            "changed_by": CREATED_BY, "changed_at": _now(),
            "absorbed_knowledge_id": row[0],
        })
        cursor.execute(
            "UPDATE unresolved_mention SET knowledge_id = ? WHERE knowledge_id = ?",
            (survivor[0], row[0]),
        )
        cursor.execute("DELETE FROM knowledge WHERE id = ?", (row[0],))
    cursor.execute(
        "UPDATE knowledge SET change_history = ? WHERE id = ?",
        (json.dumps(history, ensure_ascii=False), survivor[0]),
    )
    return len(absorbed)


def absorb_duplicates(cursor) -> list[tuple]:
    """S2. Returns (entity_id, fact_id, rows deleted) per absorbed group."""
    groups = cursor.execute(
        "SELECT entity_id, fact_id FROM knowledge GROUP BY entity_id, fact_id "
        "HAVING COUNT(*) > 1 ORDER BY entity_id, fact_id"
    ).fetchall()
    report = []
    for entity_id, fact_id in groups:
        rows = cursor.execute(
            "SELECT id, level, content, source, is_incorrect, updated_at, change_history "
            "FROM knowledge WHERE entity_id = ? AND fact_id = ?",
            (entity_id, fact_id),
        ).fetchall()
        report.append((entity_id, fact_id, _absorb_group(cursor, rows)))
    return report


def create_unique_index(cursor) -> bool:
    """S3. False when the index already exists."""
    exists = cursor.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = ?", (INDEX_NAME,)
    ).fetchone()
    if exists:
        return False
    cursor.execute(f"CREATE UNIQUE INDEX {INDEX_NAME} ON knowledge(entity_id, fact_id)")
    return True


def _rewrite_npc_fact(cursor, fact_id: str, content: str, world_id: str, history_raw) -> str | None:
    """"token", "participant" (non-uuid id: participant only) or None
    (no such entity in the fact's world: untouched)."""
    entity_id = NPC_CONTENT.match(content).group(1)
    entity = cursor.execute(
        "SELECT name FROM entity WHERE id = ? AND world_id = ?", (entity_id, world_id)
    ).fetchone()
    if entity is None:
        return None
    attached = cursor.execute(
        "SELECT 1 FROM fact_participant WHERE fact_id = ? AND entity_id = ?", (fact_id, entity_id)
    ).fetchone()
    if not attached:
        cursor.execute(
            "INSERT INTO fact_participant (id, world_id, fact_id, entity_id, role, position) "
            "VALUES (?, ?, ?, ?, NULL, 0)",
            (str(uuid.uuid4()), world_id, fact_id, entity_id),
        )
    if not UUID_ID.match(entity_id):
        return "participant"
    history = json.loads(history_raw or "[]")
    history.append({"content": content, "changed_by": CREATED_BY, "at": _now()})
    cursor.execute(
        "UPDATE fact SET content = ?, change_history = ? WHERE id = ?",
        (entity_token(entity_id, entity[0]), json.dumps(history, ensure_ascii=False), fact_id),
    )
    return "token"


def rewrite_npc_facts(cursor) -> dict[str, list[str]]:
    """S4. Fact ids by outcome: "token", "participant", "untouched"."""
    facts = cursor.execute(
        "SELECT id, content, world_id, change_history FROM fact WHERE content LIKE 'npc:%'"
    ).fetchall()
    outcome: dict[str, list[str]] = {"token": [], "participant": [], "untouched": []}
    for fact_id, content, world_id, history_raw in facts:
        result = None
        if NPC_CONTENT.match(content):
            result = _rewrite_npc_fact(cursor, fact_id, content, world_id, history_raw)
        outcome[result or "untouched"].append(fact_id)
    return outcome


def add_detail_fact_column(cursor) -> bool:
    """S5. False when the column already exists."""
    columns = [row[1] for row in cursor.execute("PRAGMA table_info(discoverable_detail)")]
    if "fact_id" in columns:
        return False
    cursor.execute("ALTER TABLE discoverable_detail ADD COLUMN fact_id TEXT REFERENCES fact(id)")
    return True


def rekey_knowledge_gates(cursor) -> tuple[int, list[tuple]]:
    """S6. Returns (requirements rekeyed, (id, target_key) left untouched)."""
    rows = cursor.execute(
        "SELECT id, world_id, target_key FROM agenda_step_requirement WHERE type = 'knowledge'"
    ).fetchall()
    rekeyed, untouched = 0, []
    for req_id, world_id, key in rows:
        facts = cursor.execute(
            "SELECT DISTINCT k.fact_id FROM knowledge k JOIN entity e ON e.id = k.entity_id "
            "WHERE e.world_id = ? AND k.subject = ?",
            (world_id, key),
        ).fetchall()
        if len(facts) == 1:
            cursor.execute(
                "UPDATE agenda_step_requirement SET target_key = ? WHERE id = ?", (facts[0][0], req_id)
            )
            rekeyed += 1
        elif not cursor.execute("SELECT 1 FROM fact WHERE id = ?", (key,)).fetchone():
            untouched.append((req_id, key))
    return rekeyed, untouched


def post_checks(cursor) -> None:
    """S7."""
    if split_subjects(cursor):
        raise Abort("post-check: a subject is still spread over several facts")
    duplicates = cursor.execute(
        "SELECT COUNT(*) FROM (SELECT 1 FROM knowledge GROUP BY entity_id, fact_id HAVING COUNT(*) > 1)"
    ).fetchone()[0]
    if duplicates:
        raise Abort(f"post-check: {duplicates} (entity_id, fact_id) group(s) still duplicated")
    unbound = cursor.execute(
        "SELECT COUNT(*) FROM fact f JOIN entity e ON e.world_id = f.world_id "
        "AND f.content = 'npc:' || e.id WHERE NOT EXISTS (SELECT 1 FROM fact_participant p "
        "WHERE p.fact_id = f.id AND p.entity_id = e.id)"
    ).fetchone()[0]
    if unbound:
        raise Abort(f"post-check: {unbound} npc:<id> fact(s) of a known entity without participant")


def migrate(cursor) -> dict:
    """S1-S7 on an open transaction. Raises `Abort` on any failed check."""
    splits = split_subjects(cursor)
    if splits:
        lines = "; ".join(f"{world!r} {subject!r} on {n} facts" for world, subject, n in splits)
        raise Abort(f"a subject is spread over several facts, merge them first: {lines}")
    report = {"absorbed": absorb_duplicates(cursor), "index_created": create_unique_index(cursor)}
    report["npc_facts"] = rewrite_npc_facts(cursor)
    report["detail_column_added"] = add_detail_fact_column(cursor)
    report["gates_rekeyed"], report["gates_untouched"] = rekey_knowledge_gates(cursor)
    post_checks(cursor)
    return report


def _print_report(report: dict) -> None:
    print(f"S2 absorbed duplicate rows: {sum(n for _, _, n in report['absorbed'])} "
          f"in {len(report['absorbed'])} group(s)")
    for entity_id, fact_id, n in report["absorbed"]:
        print(f"   entity {entity_id} fact {fact_id}: {n} row(s) absorbed")
    print(f"S3 unique index created: {report['index_created']}")
    npc = report["npc_facts"]
    print(f"S4 npc:<id> facts: {len(npc['token'])} tokenized, {len(npc['participant'])} "
          f"participant only, {len(npc['untouched'])} untouched {npc['untouched']}")
    print(f"S5 discoverable_detail.fact_id added: {report['detail_column_added']}")
    print(f"S6 knowledge gates rekeyed: {report['gates_rekeyed']}; "
          f"left untouched: {len(report['gates_untouched'])} {report['gates_untouched']}")


def _apply() -> None:
    raw = engine.raw_connection()
    try:
        cursor = raw.cursor()
        cursor.execute("BEGIN")
        try:
            report = migrate(cursor)
        except Abort as exc:
            cursor.execute("ROLLBACK")
            raise SystemExit(f"Migration {TARGET_VERSION} aborted, rolled back. {exc}") from None
        cursor.execute("COMMIT")
        cursor.close()
        _print_report(report)
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


def _converge_schema_meta() -> None:
    with Session(engine) as session:
        row = session.get(models.SchemaMeta, 1)
        if row is None:
            session.add(models.SchemaMeta(id=1, static_version=TARGET_VERSION))
            print(f"Row: seeded schema_meta.id=1 at {TARGET_VERSION!r}")
        elif row.static_version != TARGET_VERSION:
            previous = row.static_version
            row.static_version = TARGET_VERSION
            row.updated_at = datetime.now(UTC)
            session.add(row)
            print(f"Row: updated schema_meta.id=1: {previous!r} -> {TARGET_VERSION!r}")
        else:
            print(f"Row: schema_meta.id=1 already at {TARGET_VERSION!r} — nothing to do")
        session.commit()


def main() -> None:
    print(f"Migration {TARGET_VERSION} — knowledge identity by fact")
    _apply()
    _converge_schema_meta()
    print(f"\nMigration {TARGET_VERSION} applied.")


if __name__ == "__main__":
    main()
