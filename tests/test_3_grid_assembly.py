"""
Tier 3 -- grid geometry indicators.

This tier does NOT test the grid builders for their own sake; it asserts structural
invariants that can only hold if the Tier 0/1 math underneath is correct. If a math
tier is green but this tier is red, the bug is in the assembly/wiring, not arithmetic.

Per the harness design, the assembled-grid invariants are read off the REAL mission
(planner.plan_default_mission) and expressed as relationships in N (= plan.total_lines),
so they survive constant changes. The line primitive make_line_through_point is a leaf,
so it is exercised directly.
"""

import datetime

import pytest
from shapely.geometry import Point
import constants as CONST, geo as G, planner as P


def _m1_point():
    return Point(CONST.M1_MOORING_LONG, CONST.M1_MOORING_LAT)


def test_make_line_through_point_structure():
    orientation = 90.0
    line_length = 2000.0                       # >> 2 * inset, so the normal branch runs
    line = G.make_line_through_point(_m1_point(), orientation, line_length)
    coords = list(line.coords)

    assert len(coords) == CONST.V1_POINTS_PER_LINE            # [turn, collect, center, collect, turn]

    start, c_start, center, c_end, end = (Point(*c) for c in coords)

    # full length + symmetry about the center
    assert G.distance_between(start, end) == pytest.approx(line_length, abs=1.0)
    assert G.distance_between(center, start) == pytest.approx(line_length / 2, abs=1.0)
    assert G.distance_between(center, end) == pytest.approx(line_length / 2, abs=1.0)

    # collinear along the orientation (ties back to Tier 0 geodesy)
    assert P._angular_distance(G.bearing_between(start, center), orientation) == pytest.approx(0, abs=0.5)
    assert P._angular_distance(G.bearing_between(center, end), orientation) == pytest.approx(0, abs=0.5)

    # collection points sit one inset in from each turn
    assert G.distance_between(start, c_start) == pytest.approx(CONST.V1_COLLECTION_INSET_m, abs=1.0)
    assert G.distance_between(end, c_end) == pytest.approx(CONST.V1_COLLECTION_INSET_m, abs=1.0)


def test_assembled_grid_invariants():
    plan = P.plan_default_mission("t2")
    N = plan.total_lines
    assert N is not None                       # a built plan always has its metrics populated
    grid_wps = plan.waypoints[1:-1]            # strip launch (0) and land (-1)

    assert len(grid_wps) == CONST.V1_POINTS_PER_LINE * N   # 5 points per line
    assert N % 2 == 1                                      # odd -> center line through M1

    # the M1 overflight waypoint is coincident with the mooring
    m1_wps = [w for w in plan.waypoints if w.action == CONST.WAYPOINT_ACTION_M1_OVERFLIGHT]
    assert len(m1_wps) == 1
    m1_pt = Point(m1_wps[0].longitude, m1_wps[0].latitude)
    assert G.distance_between(m1_pt, _m1_point()) == pytest.approx(0, abs=1.0)

    # the grid route fits the endurance budget the planner sized it against
    route_distance = plan.total_route_distance_m
    budget = plan.usable_endurance_distance_m
    assert route_distance is not None and budget is not None
    assert route_distance <= budget

    # metric relationships (the documented science/transit split)
    assert plan.science_lines == (N + 1) // 2
    assert plan.traverse_lines == N // 2
    assert plan.offset_lines == N - 1


def test_selected_datetime_threads_into_plan():
    # Step A end-to-end indicator: an explicitly chosen mission instant flows all
    # the way through plan_default_mission into the built plan's sun state. If the
    # date/time plumbing regresses, the metadata here stops matching the input.
    chosen = datetime.datetime(2026, 7, 15, 17, 0, tzinfo=datetime.timezone.utc)  # 10:00 PDT
    plan = P.plan_default_mission("t2_dt", chosen)

    assert plan.total_lines is not None          # a real plan actually built
    assert plan.sun_state.current_day == 15      # metadata reflects the chosen instant,
    assert plan.sun_state.current_hour == 17     # not the V1 default
    assert plan.weather.valid_time == chosen     # weather stub carries the same instant
