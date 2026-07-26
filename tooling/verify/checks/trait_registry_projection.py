"""G1 check: entity_trait projection <-> trait registry vocabulary binding
(TICKET-0045, BRIEF-0045-c), on the location_type_classified.py FAILURES idiom
(zero parsed criteria is never a vacuous pass).

DB-backed, self-contained fresh temp-file SQLite fixture (WORLD_ENGINE_
DATABASE_URL set BEFORE any world_engine import) — same idiom as
location_type_classified.py / spatial_door_travel.py, so this check never
touches Nia's real DB.

Three structural properties:

1. **No orphan projection key.** Every DISTINCT `trait_key` present in
   `entity_trait` is a member of the registry vocabulary (`traits.trait_keys()`).
   Any key not in that vocabulary is a FAIL naming the key. On a fresh, empty
   fixture this volet is vacuously clean by construction — the vocabulary-
   completeness volet below is what keeps ASSERTIONS non-zero regardless.

2. **Vocabulary completeness of the registry itself.** The registry vocabulary
   must be exactly the five canonical trait keys (describable, spatial,
   knowable, secretable, mutable_by_ai) — no fewer, no more. This volet always
   examines the 5 canonical keys, so this check can never silently pass on a
   broken/truncated registry parse even against an empty projection table.

3. **Socle traits are never projected (BRIEF-0045-d).** `describable` (and any
   future non-checkable trait from `traits.socle_traits()`) is implicit on
   every entity_type, guaranteed at read time — it must never appear as an
   `entity_trait` row. A socle trait_key found in the projection is a FAIL
   naming it ("socle traits are implicit, never projected"). Vacuous-proof is
   already satisfied by volet 2's completeness check.
"""
from __future__ import annotations

import os
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

CANONICAL_TRAIT_KEYS = {"describable", "spatial", "knowable", "secretable", "mutable_by_ai"}

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def _fresh_engine():
    """Rebinds `world_engine.db`'s module-level `engine` to a fresh temp
    SQLite file by purging it (and the `world_engine` package itself) from
    `sys.modules` before reimport. `world_engine.models` is deliberately
    LEFT cached (BRIEF-0046-a): `traits.py` now imports `writes.schema`,
    which imports `models`, so by the time this check reaches here
    `world_engine.models` may already be registered on SQLModel's shared
    metadata — purging and re-executing its class bodies a second time
    would collide on the same table names. Reusing the already-registered
    classes is correct: `create_db_and_tables()` only needs the module
    imported once, ever, per process."""
    tmp_dir = tempfile.mkdtemp()
    db_path = pathlib.Path(tmp_dir) / "check.db"
    os.environ["WORLD_ENGINE_DATABASE_URL"] = f"sqlite:///{db_path}"
    sys.path.insert(0, str(SRC))
    for name in list(sys.modules):
        if name == "world_engine" or (
            name.startswith("world_engine.") and not name.startswith("world_engine.models")
        ):
            del sys.modules[name]

    from world_engine.db import create_db_and_tables, engine

    create_db_and_tables()
    return engine


def _check_vocabulary_completeness(vocab: set[str]) -> int:
    """Always examines the 5 canonical keys — never vacuous, even against an
    empty projection table."""
    examined = 0
    for key in sorted(CANONICAL_TRAIT_KEYS):
        examined += 1
        if key not in vocab:
            fail(f"registry vocabulary is missing canonical trait key {key!r}")
    extra = vocab - CANONICAL_TRAIT_KEYS
    if extra:
        fail(f"registry vocabulary carries unexpected key(s) beyond the canonical five: {sorted(extra)}")
    return examined


def _scan_projection(session, vocab: set[str]) -> tuple[int, list[str]]:
    from sqlmodel import select

    from world_engine.models import EntityTrait

    rows = session.exec(select(EntityTrait)).all()
    distinct_keys = {row.trait_key for row in rows}

    failures: list[str] = []
    for key in sorted(distinct_keys):
        if key not in vocab:
            failures.append(f"entity_trait.trait_key {key!r} is not in the registry vocabulary")
    return len(distinct_keys), failures


def _scan_socle_violations(session, socle_keys: set[str]) -> list[str]:
    from sqlmodel import select

    from world_engine.models import EntityTrait

    rows = session.exec(select(EntityTrait)).all()
    distinct_keys = {row.trait_key for row in rows}
    violating = distinct_keys & socle_keys
    return [
        f"entity_trait carries socle trait_key {key!r} — socle traits are implicit, never projected"
        for key in sorted(violating)
    ]


def check_projection_fixture(engine, vocab: set[str], socle_keys: set[str]) -> None:
    from sqlmodel import Session as DbSession, select

    from world_engine.models import EntityTrait, EntityType, World

    with DbSession(engine) as session:
        world = World(name="Check World", is_active=True)
        session.add(world)
        session.commit()
        session.refresh(world)

        entity_type = EntityType(
            world_id=world.id, name="Golem", slug="golem", physical_table="ext_golem"
        )
        session.add(entity_type)
        session.commit()
        session.refresh(entity_type)

        # ── Plant a valid key + an orphan key -> exactly the orphan FAILs ──
        session.add(EntityTrait(entity_type_id=entity_type.id, trait_key="spatial"))
        session.add(EntityTrait(entity_type_id=entity_type.id, trait_key="bogus_trait_xyz"))
        session.commit()

        examined, failures = _scan_projection(session, vocab)
        if examined == 0:
            fail("vacuous-proof: entity_trait rows exist but zero distinct trait_key values were examined")
        if not any("bogus_trait_xyz" in msg for msg in failures):
            fail(f"expected a FAIL naming the orphan key 'bogus_trait_xyz', got: {failures}")
        if any("'spatial'" in msg for msg in failures):
            fail(f"'spatial' is a valid registry key and must never FAIL, got: {failures}")
        if len(failures) != 1:
            fail(f"expected exactly one orphan failure, got: {failures}")

        # ── Remove the orphan row -> green ──────────────────────────────
        for row in session.exec(
            select(EntityTrait).where(EntityTrait.trait_key == "bogus_trait_xyz")
        ).all():
            session.delete(row)
        session.commit()

        _, failures_after = _scan_projection(session, vocab)
        if failures_after:
            fail(f"expected green after removing the orphan row, got: {failures_after}")

        # ── Socle-never-projected: plant a describable row -> FAILs naming it ──
        session.add(EntityTrait(entity_type_id=entity_type.id, trait_key="describable"))
        session.commit()

        socle_failures = _scan_socle_violations(session, socle_keys)
        if not any("describable" in msg for msg in socle_failures):
            fail(f"expected a FAIL naming the planted socle trait 'describable', got: {socle_failures}")

        for row in session.exec(
            select(EntityTrait).where(EntityTrait.trait_key == "describable")
        ).all():
            session.delete(row)
        session.commit()

        socle_failures_after = _scan_socle_violations(session, socle_keys)
        if socle_failures_after:
            fail(f"expected green after removing the socle-trait row, got: {socle_failures_after}")


def main() -> int:
    sys.path.insert(0, str(SRC))
    try:
        from world_engine import traits
    except Exception as exc:  # noqa: BLE001
        fail(f"world_engine.traits failed to import: {exc}")
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1

    vocab = set(traits.trait_keys())
    socle_keys = {trait.key for trait in traits.socle_traits()}
    _check_vocabulary_completeness(vocab)

    engine = _fresh_engine()
    check_projection_fixture(engine, vocab, socle_keys)

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1
    print(
        "PASS: trait_registry_projection — registry vocabulary is exactly the "
        "5 canonical traits; every entity_trait.trait_key resolves against it; "
        "an orphan key FAILs by name"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
