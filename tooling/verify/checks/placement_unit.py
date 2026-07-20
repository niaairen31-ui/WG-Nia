"""G1 check: permanent regression guard for the sole placement/distance
authority (TICKET-0031, BRIEF-0031-a). Deterministic, no DB — imports
`world_engine.placement` and `world_engine.geometry` via the same
`ROOT`/`src` path bootstrap the other checks use (e.g. `geometry_unit.py`).
Every case is a hard assert; one summary PASS line on success.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from world_engine import geometry  # noqa: E402
from world_engine import placement  # noqa: E402

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def close(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


BOUNDS = (40.0, 30.0)
BLOCK: geometry.Polygon = [(5.0, 5.0), (15.0, 5.0), (15.0, 7.0), (5.0, 7.0)]
ROSTERS = [("g1", ["npc-a", "npc-b"]), ("g2", ["npc-c"])]

# Restart-determinism proxy: pinned literals for the fixed input above. A
# salted-hash regression (e.g. swapping sha256 for Python's hash()) would
# flip these on the very next process, failing this check immediately.
EXPECTED = {
    "npc-a": (30.393730120005245, 18.983078361156092),
    "npc-b": (30.785193552068126, 19.92884686483031),
    "npc-c": (14.057121914304645, 19.45361110659411),
}


def check_determinism_across_calls() -> None:
    pos1 = placement.derive_positions(ROSTERS, BOUNDS, [BLOCK])
    pos2 = placement.derive_positions(ROSTERS, BOUNDS, [BLOCK])
    if pos1 != pos2:
        fail(f"determinism: two calls with identical inputs diverged: {pos1} != {pos2}")


def check_restart_determinism_proxy() -> None:
    positions = placement.derive_positions(ROSTERS, BOUNDS, [BLOCK])
    for entity_id, (ex, ey) in EXPECTED.items():
        if entity_id not in positions:
            fail(f"restart-determinism proxy: {entity_id} missing from output")
            continue
        x, y = positions[entity_id]
        if not (close(x, ex) and close(y, ey)):
            fail(
                f"restart-determinism proxy: {entity_id} expected ({ex}, {ey}), got ({x}, {y}) "
                "— a salted-hash regression would flip pinned coordinates like this"
            )


def check_obstacle_avoidance() -> None:
    positions = placement.derive_positions(ROSTERS, BOUNDS, [BLOCK])
    for entity_id, point in positions.items():
        if geometry.point_in_polygon(point, BLOCK):
            fail(f"obstacle avoidance: {entity_id} at {point} lands inside the test block")


def check_bounds_containment() -> None:
    positions = placement.derive_positions(ROSTERS, BOUNDS, [BLOCK])
    width, height = BOUNDS
    for entity_id, (x, y) in positions.items():
        if not (0.0 <= x <= width and 0.0 <= y <= height):
            fail(f"bounds containment: {entity_id} at ({x}, {y}) escapes bounds {BOUNDS}")


def check_clustering() -> None:
    eps = 1e-6
    # A solo roster under the same gathering_id yields the gathering's
    # centroid exactly (derive_positions places a lone member ON it) —
    # deriving the reference point this way avoids reaching into
    # placement's private helpers.
    centroid_g1 = placement.derive_positions([("g1", ["solo"])], BOUNDS, [BLOCK])["solo"]
    centroid_g2 = placement.derive_positions([("g2", ["solo"])], BOUNDS, [BLOCK])["solo"]

    if placement.distance(centroid_g1, centroid_g2) < eps:
        fail("clustering: two distinct gatherings produced the same centroid")

    positions = placement.derive_positions(ROSTERS, BOUNDS, [BLOCK])
    for entity_id in ("npc-a", "npc-b"):
        d = placement.distance(positions[entity_id], centroid_g1)
        if d > placement.MEMBER_RING_RADIUS + eps:
            fail(
                f"clustering: {entity_id} at distance {d} from its gathering's centroid, "
                f"expected <= {placement.MEMBER_RING_RADIUS} + eps"
            )


def check_saturation_totality() -> None:
    tiny_bounds = (2.0, 2.0)
    wall: geometry.Polygon = [(0.0, 0.0), (2.0, 0.0), (2.0, 2.0), (0.0, 2.0)]
    rosters = [("g-tiny", ["npc-x", "npc-y"])]
    try:
        positions = placement.derive_positions(rosters, tiny_bounds, [wall])
    except Exception as exc:  # pragma: no cover - the assertion IS the guard
        fail(f"saturation totality: derive_positions raised on an all-wall location: {exc!r}")
        return
    for entity_id in ("npc-x", "npc-y"):
        if entity_id not in positions:
            fail(f"saturation totality: {entity_id} missing from an all-wall location's output")


def check_distance_3_4_5() -> None:
    d = placement.distance((0.0, 0.0), (3.0, 4.0))
    if not close(d, 5.0):
        fail(f"distance: expected 5.0 on a 3-4-5 triangle, got {d}")


# spawn_point cases (TICKET-0034, BRIEF-0034-b). Same restart-determinism
# proxy shape as EXPECTED above: pinned literal for a fixed
# (door_id, anchor, BOUNDS, [BLOCK]) — a salted-hash regression would
# flip it on the very next process.
SPAWN_ANCHOR = (20.0, 15.0)
SPAWN_EXPECTED = (20.59911422942053, 15.03259049103416)


def check_spawn_point_restart_determinism_proxy() -> None:
    point = placement.spawn_point("door-spawn-basic", SPAWN_ANCHOR, BOUNDS, [BLOCK])
    if not (close(point[0], SPAWN_EXPECTED[0]) and close(point[1], SPAWN_EXPECTED[1])):
        fail(
            f"spawn_point restart-determinism proxy: expected {SPAWN_EXPECTED}, got {point} "
            "— a salted-hash regression would flip a pinned coordinate like this"
        )


def check_spawn_point_offset() -> None:
    point = placement.spawn_point("door-spawn-basic", SPAWN_ANCHOR, BOUNDS, [BLOCK])
    d = placement.distance(SPAWN_ANCHOR, point)
    if not close(d, placement.DOOR_SPAWN_OFFSET, tol=1e-6):
        fail(f"spawn_point offset: expected {placement.DOOR_SPAWN_OFFSET} from anchor, got {d}")


def check_spawn_point_beside_wall() -> None:
    anchor = (10.0, 7.3)  # just outside BLOCK's bottom edge (y=7)
    point = placement.spawn_point("door-wall", anchor, BOUNDS, [BLOCK])
    if geometry.point_in_polygon(point, BLOCK):
        fail(f"spawn_point beside wall: {point} lands inside BLOCK")


def check_spawn_point_bounds_corner() -> None:
    anchor = (0.2, 0.2)  # near the (0, 0) corner of BOUNDS
    point = placement.spawn_point("door-corner", anchor, BOUNDS, [BLOCK])
    width, height = BOUNDS
    if not (0.0 <= point[0] <= width and 0.0 <= point[1] <= height):
        fail(f"spawn_point bounds corner: {point} escapes bounds {BOUNDS}")


def check_spawn_point_saturation() -> None:
    anchor = (10.0, 10.0)
    ring_block: geometry.Polygon = [
        (anchor[0] - 2.0, anchor[1] - 2.0), (anchor[0] + 2.0, anchor[1] - 2.0),
        (anchor[0] + 2.0, anchor[1] + 2.0), (anchor[0] - 2.0, anchor[1] + 2.0),
    ]
    try:
        point = placement.spawn_point("door-sat", anchor, BOUNDS, [ring_block])
    except Exception as exc:  # pragma: no cover - the assertion IS the guard
        fail(f"spawn_point saturation: raised on a fully-boxed anchor: {exc!r}")
        return
    if point != anchor:
        fail(f"spawn_point saturation: expected the anchor itself {anchor}, got {point}")


CASES = [
    check_determinism_across_calls,
    check_restart_determinism_proxy,
    check_obstacle_avoidance,
    check_bounds_containment,
    check_clustering,
    check_saturation_totality,
    check_distance_3_4_5,
    check_spawn_point_restart_determinism_proxy,
    check_spawn_point_offset,
    check_spawn_point_beside_wall,
    check_spawn_point_bounds_corner,
    check_spawn_point_saturation,
]


def main() -> None:
    for case in CASES:
        case()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)

    print(f"PASS: placement_unit — all {len(CASES)} derive_positions/distance cases hold")
    sys.exit(0)


if __name__ == "__main__":
    main()
