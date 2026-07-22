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


# door_placeholder_point cases (N1, TICKET-0040, BRIEF-0040-d): the
# perimeter walk replacing the H1 center placeholder.
class _StubLocation:
    """Minimal location stand-in — door_placeholder_point reads only
    .id, .bounds_width, .bounds_height. No DB import needed here."""

    def __init__(self, id: str, bounds_width, bounds_height):
        self.id = id
        self.bounds_width = bounds_width
        self.bounds_height = bounds_height


DOOR_BOUNDS = (12.0, 8.0)
DOOR_LOCATION = _StubLocation("loc-1", *DOOR_BOUNDS)
DOOR_TARGETS = [f"target-{i}" for i in range(20)]

# Restart-determinism proxy: pinned literals for 3 fixed
# (location_id, target_id, bounds) triples — same shape as EXPECTED and
# SPAWN_EXPECTED above. A salted-hash regression would flip these on the
# very next process.
DOOR_EXPECTED = {
    ("loc-a", "loc-b", (12.0, 8.0)): (1.0271424920696788, 8.0),
    ("loc-b", "loc-a", (20.0, 10.0)): (4.094636449441468, 0.0),
    ("loc-x", "loc-y", (5.0, 5.0)): (0.0, 1.1892164356755295),
}


def check_door_placeholder_on_perimeter() -> None:
    width, height = DOOR_BOUNDS
    for target in DOOR_TARGETS:
        x, y = placement.door_placeholder_point(DOOR_LOCATION, target)
        on_edge = (
            close(x, 0.0, tol=1e-9) or close(x, width, tol=1e-9)
            or close(y, 0.0, tol=1e-9) or close(y, height, tol=1e-9)
        )
        if not on_edge:
            fail(f"door_placeholder_point on-perimeter: {target} at ({x}, {y}) is not on the border")
        if not (0.0 <= x <= width and 0.0 <= y <= height):
            fail(f"door_placeholder_point on-perimeter: {target} at ({x}, {y}) escapes bounds {DOOR_BOUNDS}")


def check_door_placeholder_distinctness() -> None:
    points = [placement.door_placeholder_point(DOOR_LOCATION, target) for target in DOOR_TARGETS]
    if len(set(points)) != len(points):
        fail(f"door_placeholder_point distinctness: duplicate point among {len(points)} distinct targets")


def check_door_placeholder_spread() -> None:
    width, height = DOOR_BOUNDS
    edges: set[str] = set()
    for target in DOOR_TARGETS:
        x, y = placement.door_placeholder_point(DOOR_LOCATION, target)
        if close(y, 0.0, tol=1e-9):
            edges.add("top")
        if close(x, width, tol=1e-9):
            edges.add("right")
        if close(y, height, tol=1e-9):
            edges.add("bottom")
        if close(x, 0.0, tol=1e-9):
            edges.add("left")
    if len(edges) < 3:
        fail(f"door_placeholder_point spread: only touched edges {edges}, expected >= 3 of 4")


def check_door_placeholder_determinism() -> None:
    for (location_id, target_id, bounds), (ex, ey) in DOOR_EXPECTED.items():
        location = _StubLocation(location_id, *bounds)
        x, y = placement.door_placeholder_point(location, target_id)
        if not (close(x, ex) and close(y, ey)):
            fail(
                f"door_placeholder_point determinism: ({location_id}, {target_id}, {bounds}) "
                f"expected ({ex}, {ey}), got ({x}, {y}) — a salted-hash regression would flip "
                "pinned coordinates like this"
            )


def check_door_placeholder_asymmetry() -> None:
    loc_a = _StubLocation("loc-a", 12.0, 8.0)
    loc_b = _StubLocation("loc-b", 20.0, 10.0)
    ab = placement.door_placeholder_point(loc_a, "loc-b")
    ba = placement.door_placeholder_point(loc_b, "loc-a")
    if ab == ba:
        fail(f"door_placeholder_point asymmetry: (A,B)={ab} equals (B,A)={ba}, expected different points")


def check_door_placeholder_null_bounds() -> None:
    cases = [
        (None, None),
        (10.0, None),
        (0.0, 5.0),
        (float("inf"), 5.0),
    ]
    for width, height in cases:
        point = placement.door_placeholder_point(_StubLocation("loc-null", width, height), "target")
        if point != (0.0, 0.0):
            fail(f"door_placeholder_point null bounds: ({width}, {height}) expected (0.0, 0.0), got {point}")


def check_door_placeholder_elongation() -> None:
    location = _StubLocation("loc-elongated", 100.0, 2.0)
    short_edge_hits = 0
    for target in DOOR_TARGETS:
        x, _y = placement.door_placeholder_point(location, target)
        if close(x, 0.0, tol=1e-9) or close(x, 100.0, tol=1e-9):
            short_edge_hits += 1
    fraction = short_edge_hits / len(DOOR_TARGETS)
    if fraction >= 0.2:
        fail(
            f"door_placeholder_point elongation: {fraction:.2f} of points landed on the short edges, "
            "expected < 0.2 — a uniform-angle ray-cast implementation would cluster there"
        )


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
    check_door_placeholder_on_perimeter,
    check_door_placeholder_distinctness,
    check_door_placeholder_spread,
    check_door_placeholder_determinism,
    check_door_placeholder_asymmetry,
    check_door_placeholder_null_bounds,
    check_door_placeholder_elongation,
]


def main() -> None:
    for case in CASES:
        case()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)

    print(
        f"PASS: placement_unit — all {len(CASES)} derive_positions/distance/"
        "door_placeholder_point perimeter cases hold"
    )
    sys.exit(0)


if __name__ == "__main__":
    main()
