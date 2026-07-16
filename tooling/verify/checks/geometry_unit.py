"""G1 check: permanent regression guard for the sole collision authority
(TICKET-0030, BRIEF-0030-a). Deterministic, no DB — imports
`world_engine.geometry` via the same `ROOT`/`src` path bootstrap the other
checks use (e.g. `prompt_registry.py`). Every case is a hard assert; one
summary PASS line on success.
"""
from __future__ import annotations

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from world_engine.geometry import EPS_METERS, clip_segment  # noqa: E402

FAILURES: list[str] = []


def fail(msg: str) -> None:
    FAILURES.append(msg)


def close(a: float, b: float, tol: float = 1e-6) -> bool:
    return abs(a - b) <= tol


RECTANGLE = [(5.0, 5.0), (15.0, 5.0), (15.0, 7.0), (5.0, 7.0)]
TRIANGLE = [(20.0, 20.0), (30.0, 20.0), (25.0, 10.0)]  # apex up (B2 genericity proof)
BOUNDS = (40.0, 30.0)


def check_free_move_open_space() -> None:
    point, blocked = clip_segment((1.0, 1.0), (2.0, 2.0), [RECTANGLE], BOUNDS)
    if blocked:
        fail("free move in open space: expected blocked=False")
    if point != (2.0, 2.0):
        fail(f"free move in open space: expected destination unchanged, got {point}")


def check_rectangle_hit() -> None:
    point, blocked = clip_segment((10.0, 0.0), (10.0, 10.0), [RECTANGLE], None)
    if not blocked:
        fail("rectangle hit: expected blocked=True")
    if not (close(point[0], 10.0) and close(point[1], 5.0 - EPS_METERS, tol=EPS_METERS)):
        fail(f"rectangle hit: expected stop point near (10, 5 - eps), got {point}")


def check_triangle_hit() -> None:
    point, blocked = clip_segment((22.0, 5.0), (22.0, 25.0), [TRIANGLE], None)
    if not blocked:
        fail("triangle hit (B2 genericity): expected blocked=True")
    if not (close(point[0], 22.0) and close(point[1], 16.0, tol=EPS_METERS * 2)):
        fail(f"triangle hit: expected stop point near (22, 16), got {point}")


def check_bounds_clip() -> None:
    point, blocked = clip_segment((35.0, 15.0), (45.0, 15.0), [], BOUNDS)
    if not blocked:
        fail("bounds clip: expected blocked=True")
    if not (close(point[0], 40.0 - EPS_METERS, tol=EPS_METERS) and close(point[1], 15.0)):
        fail(f"bounds clip: expected stop point near (40 - eps, 15), got {point}")


def check_no_bounds_no_polygons_passes() -> None:
    point, blocked = clip_segment((0.0, 0.0), (100.0, 100.0), [], None)
    if blocked:
        fail("bounds=None, no polygons: expected blocked=False")
    if point != (100.0, 100.0):
        fail(f"bounds=None, no polygons: expected destination unchanged, got {point}")


def check_origin_inside_polygon() -> None:
    point, blocked = clip_segment((10.0, 6.0), (10.0, 20.0), [RECTANGLE], None)
    if not blocked:
        fail("origin inside polygon: expected blocked=True")
    if point != (10.0, 6.0):
        fail(f"origin inside polygon: expected origin returned unchanged (destination ignored), got {point}")


def check_origin_outside_bounds() -> None:
    point, blocked = clip_segment((-5.0, 10.0), (10.0, 10.0), [], BOUNDS)
    if not blocked:
        fail("origin outside bounds: expected blocked=True")
    if point != (-5.0, 10.0):
        fail(f"origin outside bounds: expected origin returned unchanged, got {point}")


def check_zero_length_open_space() -> None:
    point, blocked = clip_segment((5.0, 5.0), (5.0, 5.0), [], None)
    if blocked:
        fail("zero-length segment: expected blocked=False")
    if point != (5.0, 5.0):
        fail(f"zero-length segment: expected the point unchanged, got {point}")


def check_destination_on_edge() -> None:
    point, blocked = clip_segment((10.0, 0.0), (10.0, 5.0), [RECTANGLE], None)
    if not blocked:
        fail("destination exactly on edge: expected blocked=True")
    if point[1] >= 5.0:
        fail(f"destination exactly on edge: expected stop pulled back off the edge, got {point}")
    if not close(point[1], 5.0 - EPS_METERS, tol=EPS_METERS):
        fail(f"destination exactly on edge: expected stop near (10, 5 - eps), got {point}")


def check_parallel_graze_not_blocked() -> None:
    point, blocked = clip_segment((4.9, 0.0), (4.9, 10.0), [RECTANGLE], None)
    if blocked:
        fail(f"parallel graze just off a wall: expected blocked=False, got stop point {point}")
    if point != (4.9, 10.0):
        fail(f"parallel graze just off a wall: expected destination unchanged, got {point}")


CASES = [
    check_free_move_open_space,
    check_rectangle_hit,
    check_triangle_hit,
    check_bounds_clip,
    check_no_bounds_no_polygons_passes,
    check_origin_inside_polygon,
    check_origin_outside_bounds,
    check_zero_length_open_space,
    check_destination_on_edge,
    check_parallel_graze_not_blocked,
]


def main() -> None:
    for case in CASES:
        case()

    if FAILURES:
        for msg in FAILURES:
            print(f"FAIL: {msg}")
        sys.exit(1)

    print(f"PASS: geometry_unit — all {len(CASES)} clip_segment cases hold")
    sys.exit(0)


if __name__ == "__main__":
    main()
