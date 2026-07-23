"""Governed runtime-DDL writer (TICKET-0044, BRIEF-0044-c — Dcol1, Dname1,
Ddrop1, A1 atomicity). The socle's third structural-write authority (D2): it
materializes a runtime `ext_*` table AND registers it, in one transaction.

"(CREATE TABLE ext_*) + (INSERT entity_type) + (INSERT entity_type_history
'type_created') are one transaction: all three commit together or none do.
A runtime type never exists physically without its registry row and its
birth record, and vice versa."

Scope boundary (socle, TICKET-0044): this module writes STRUCTURE plus rows
into the two static config/history tables (`entity_type`,
`entity_type_history`) ONLY. It performs no row write into any `ext_*`
table — that is 0046 (creator CRUD) / 0047 (AI dispatch). `columns` is
supplied by the caller; deriving it from traits is 0045. No additive-column
or destructive-DDL path exists here, ever (Ddrop1) — retiring a type is a
status flag on `entity_type`, never a further DDL statement.
"""

from __future__ import annotations

import re

from sqlalchemy import inspect, text
from sqlmodel import Session, select

from ..models import EntityType, EntityTypeHistory

EXT_PREFIX = "ext_"

# Dcol1 — the ONLY source of SQL type fragments. A col_type outside this
# mapping raises before any DDL is built.
_COLUMN_TYPES: dict[str, str] = {
    "TEXT": "TEXT",
    "INTEGER": "INTEGER",
    "REAL": "REAL",
    "BOOLEAN": "INTEGER CHECK ({col} IN (0,1))",
    "JSON": "TEXT",
    "TIMESTAMP": "TIMESTAMP",
    "FK_ENTITY": "TEXT NOT NULL REFERENCES entity(id)",
    "FK_ENTITY_NULLABLE": "TEXT REFERENCES entity(id)",
}

_IDENTIFIER_RE = re.compile(r"^[a-z][a-z0-9_]{0,62}$")
_RESERVED_WORDS = {
    "select", "insert", "update", "delete", "drop", "alter", "table",
    "index", "from", "where", "join", "entity",
}


def _validate_identifier(name: str) -> None:
    """Dname1. Raises ValueError on anything but a safe, non-reserved,
    lowercase snake_case identifier with no leading/trailing underscore."""
    if not _IDENTIFIER_RE.match(name):
        raise ValueError(f"invalid identifier {name!r}: must match {_IDENTIFIER_RE.pattern}")
    if name.startswith("_") or name.endswith("_"):
        raise ValueError(f"invalid identifier {name!r}: leading/trailing underscore forbidden")
    if name in _RESERVED_WORDS:
        raise ValueError(f"invalid identifier {name!r}: reserved word")


def _validate_columns(columns: list[tuple[str, str]]) -> None:
    """Dcol1 + Dname1, up front: every col_name is a valid identifier and
    every col_type is a member of the closed enum. Raises before any DDL
    text is built."""
    for col_name, col_type in columns:
        _validate_identifier(col_name)
        if col_type not in _COLUMN_TYPES:
            raise ValueError(f"invalid col_type {col_type!r}: must be one of {sorted(_COLUMN_TYPES)}")


def _column_fragment(col_name: str, col_type: str) -> str:
    """One `col_name col_sql` line, built only from a validated identifier
    and the closed Dcol1 enum fragment."""
    fragment = _COLUMN_TYPES[col_type].format(col=col_name)
    return f"{col_name} {fragment}"


def _build_create_table_ddl(physical_table: str, columns: list[tuple[str, str]]) -> str:
    """Constrained CREATE TABLE generator (Ddrop1: CREATE only — no
    destructive-DDL branch exists anywhere in this module). The shared PK
    line is always first and is never part of the caller-supplied `columns`.
    Assumes `_validate_columns` already ran — never called on unvalidated
    input."""
    lines = ["id TEXT PRIMARY KEY REFERENCES entity(id)"]
    lines.extend(_column_fragment(col_name, col_type) for col_name, col_type in columns)
    body = ",\n    ".join(lines)
    return f"CREATE TABLE {physical_table} (\n    {body}\n)"


def _check_collision(session: Session, engine, *, slug: str, physical_table: str) -> None:
    if inspect(engine).has_table(physical_table):
        raise ValueError(f"physical table {physical_table!r} already exists")
    existing = session.exec(
        select(EntityType).where(EntityType.physical_table == physical_table)
    ).first()
    if existing is not None:
        raise ValueError(f"entity_type row already targets physical table {physical_table!r}")
    folded = slug.casefold()
    for row in session.exec(select(EntityType)).all():
        if row.slug.casefold() == folded:
            raise ValueError(f"entity_type slug {slug!r} already exists (case-insensitive)")


def create_entity_type(
    session: Session,
    *,
    world_id: str,
    name: str,
    slug: str,
    columns: list[tuple[str, str]],
    changed_by: str,
) -> str:
    """The single governed entry point materializing a runtime `ext_*` table.

    In ONE transaction: validates `slug` and every `col_name` (Dname1),
    derives `physical_table`, checks for a collision, builds and executes
    the constrained CREATE TABLE DDL (Dcol1/Ddrop1), then inserts the
    `entity_type` registry row and the `entity_type_history` `type_created`
    birth record. Caller commits (or lets the SAVEPOINT/session roll back on
    any raised error, per A1). Returns the new `entity_type.id`.
    """
    _validate_identifier(slug)
    _validate_columns(columns)
    physical_table = EXT_PREFIX + slug
    _check_collision(session, session.get_bind(), slug=slug, physical_table=physical_table)

    ddl_text = _build_create_table_ddl(physical_table, columns)
    session.execute(text(ddl_text))

    entity_type = EntityType(
        world_id=world_id, name=name, slug=slug, physical_table=physical_table,
    )
    session.add(entity_type)

    definition_snapshot = {
        "name": name, "slug": slug, "physical_table": physical_table, "columns": columns,
    }
    session.add(EntityTypeHistory(
        world_id=world_id,
        entity_type_id=entity_type.id,
        event="type_created",
        definition_snapshot=definition_snapshot,
        physical_table=physical_table,
        ddl_text=ddl_text,
        changed_by=changed_by,
    ))

    return entity_type.id
