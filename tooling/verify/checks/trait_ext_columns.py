"""G1 check: trait ext-column derivation (BRIEF-0046-a, 0045-plane back-fill).

Imports `world_engine.traits` and asserts the concrete D2 shape:

1. `ext_columns_for(("spatial", "secretable"))` == the two expected
   `(name, col_type)` pairs, in socle-then-declaration order.
2. `ext_columns_for(("knowable", "mutable_by_ai"))` == [] and `describable`
   never contributes an ext column to any emitted set.
3. Every `ExtColumnSpec.col_type` across the whole registry is a member of
   `writes.schema.valid_col_types()`, and every `.field["kind"]` != "json".
4. The socle/base-name collision guard holds (import-time assertion in
   traits.py did not raise — this module already imported cleanly by the
   time we get here).

Vacuous-proof (location_type_classified.py idiom): zero parsed ext columns
across the whole registry is a FAIL, not a clean-repo pass — `spatial` and
`secretable` are known to contribute one column each, so a healthy registry
always has >= 2.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def main() -> int:
    sys.path.insert(0, str(SRC))
    try:
        from world_engine import traits
        from world_engine.writes.schema import valid_col_types
    except Exception as exc:  # noqa: BLE001 - a broken import (incl. a guard raise) is a FAIL
        fail(f"world_engine.traits failed to import: {exc}")
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1

    spatial_secretable = traits.ext_columns_for(("spatial", "secretable"))
    expected = [("location_id", "FK_ENTITY_NULLABLE"), ("is_secret", "BOOLEAN")]
    if spatial_secretable != expected:
        fail(
            f"ext_columns_for(('spatial','secretable')) == {spatial_secretable!r}, "
            f"expected {expected!r}"
        )

    knowable_mutable = traits.ext_columns_for(("knowable", "mutable_by_ai"))
    if knowable_mutable != []:
        fail(
            f"ext_columns_for(('knowable','mutable_by_ai')) == {knowable_mutable!r}, "
            "expected []"
        )

    all_keys = traits.trait_keys()
    all_emitted = traits.ext_columns_for(all_keys)
    describable_names = {
        spec.name for spec in next(
            trait.ext_columns for trait in traits.TRAITS if trait.key == "describable"
        )
    }
    if describable_names:
        fail(f"'describable' must contribute zero ext columns, found {sorted(describable_names)}")
    emitted_names = {name for name, _ in all_emitted}
    if describable_names & emitted_names:
        fail("'describable' columns leaked into the full-registry emitted set")

    valid_types = valid_col_types()
    total_specs = 0
    for trait in traits.TRAITS:
        for spec in trait.ext_columns:
            total_specs += 1
            if spec.col_type not in valid_types:
                fail(
                    f"trait {trait.key!r} ext column {spec.name!r}: col_type "
                    f"{spec.col_type!r} not in valid_col_types()"
                )
            if spec.field.get("kind") == "json":
                fail(
                    f"trait {trait.key!r} ext column {spec.name!r}: field kind "
                    "'json' is forbidden"
                )

    if total_specs == 0:
        fail("vacuous-proof: zero ext columns parsed across the whole registry — broken parse, not a clean repo")

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        return 1

    print(
        "PASS: trait_ext_columns — spatial/secretable derive their expected "
        f"columns, socle traits emit none, {total_specs} ext column(s) validate "
        "against the closed col_type enum with no json-kind field"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
