"""Governed-runtime-type instance CRUD mechanics (TICKET-0046, BRIEF-0046-e).

Split out of `entities.py` (which owns the STATIC `ENTITY_TYPE_REGISTRY` +
SQLModel-class CRUD, unchanged) to keep that module under the
`module_budget` line cap and to isolate the one place this codebase reaches
a table by reflection instead of an ORM model class. A runtime type has no
SQLModel class — its `ext_*` table is reflected via SQLAlchemy Core and
every statement built on it is a parameterized `insert()`/`select()`/
`update()`, never string-interpolated. `physical_table` is never user
input: it only ever comes from an `entity_type` row already validated as a
safe identifier at creation time (`writes/schema.py`, Dname1).

Imports only from `_shared` (never from `entities.py`) so `entities.py` can
import this module with no import cycle — `entities.py` still owns entity
+ base-field construction (`_apply_base_fields`) and calls into this module
only for the ext-row mechanics.
"""
from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import MetaData, Table
from sqlalchemy import insert as sa_insert
from sqlalchemy import select as sa_select
from sqlalchemy import update as sa_update
from sqlmodel import Session as DbSession, select

from ...models import EntityTrait, EntityType
from ...traits import form_fields_for
from ._shared import _coerce_field, _world_id


def _runtime_type_spec(db: DbSession, type_slug: str) -> Optional[dict]:
    """The single "is this slug a governed runtime type" gate (A1). ACTIVE +
    world-scoped `entity_type` row only — a retired/quarantined or
    foreign-world slug resolves to None, same as an unknown one. Returns
    `{"physical_table", "fields"}`, `fields` derived through the same
    `form_fields_for` used by `GET /api/entity-types` (never recomputed
    inline)."""
    row = db.exec(
        select(EntityType).where(
            EntityType.world_id == _world_id(db),
            EntityType.slug == type_slug,
            EntityType.status == "active",
        )
    ).first()
    if row is None:
        return None
    trait_keys = [
        et.trait_key
        for et in db.exec(select(EntityTrait).where(EntityTrait.entity_type_id == row.id)).all()
    ]
    return {"physical_table": row.physical_table, "fields": form_fields_for(trait_keys)}


def _reflected_ext_table(db: DbSession, physical_table: str) -> Table:
    return Table(physical_table, MetaData(), autoload_with=db.get_bind())


def _build_runtime_ext_kwargs(db: DbSession, fields: list[dict], data: dict) -> dict:
    return {f["name"]: _coerce_field(db, f, data.get(f["name"])) for f in fields}


def _read_runtime_ext_row(db: DbSession, runtime_spec: dict, entity_id: str) -> dict:
    table = _reflected_ext_table(db, runtime_spec["physical_table"])
    row = db.execute(sa_select(table).where(table.c.id == entity_id)).mappings().first()
    if row is None:
        return {}
    result: dict[str, Any] = {}
    for f in runtime_spec["fields"]:
        value = row[f["name"]]
        # SQLite has no native BOOLEAN type: the closed Dcol1 mapping stores
        # it as INTEGER CHECK (col IN (0,1)), and plain Core reflection (no
        # ORM Boolean type decorator) hands back a raw 0/1 int — coerce to a
        # real Python bool so the JSON response matches every other bool
        # field in this API (e.g. ENTITY_BASE_FIELDS.is_public).
        if f["kind"] == "bool" and value is not None:
            value = bool(value)
        result[f["name"]] = value
    return result


def _insert_runtime_ext_row(db: DbSession, runtime_spec: dict, entity_id: str, ext_kwargs: dict) -> None:
    """Takes already-coerced kwargs (`_build_runtime_ext_kwargs`) — callers
    coerce/validate before touching the session, same posture as the static
    path's `_build_extension_kwargs`."""
    table = _reflected_ext_table(db, runtime_spec["physical_table"])
    db.execute(sa_insert(table).values(id=entity_id, **ext_kwargs))


def _update_runtime_ext_row(db: DbSession, runtime_spec: dict, entity_id: str, ext_kwargs: dict) -> None:
    table = _reflected_ext_table(db, runtime_spec["physical_table"])
    db.execute(sa_update(table).where(table.c.id == entity_id).values(**ext_kwargs))
