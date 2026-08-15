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

    # metric relationships. V2C: the along-track mount put both leg directions the
    # same angular distance off the sun, so EVERY line collects -- the old
    # science/transit split is gone and nothing is traverse-only.
    assert plan.science_lines == N
    assert plan.traverse_lines == 0
    assert plan.offset_lines == N - 1


def test_viewing_geometry_reaches_the_plan():
    # V2C-1 wiring: geo measures the swath and the parallax during grid assembly and
    # ships them in the metrics dict. Before set_grid_metrics learned to read those two
    # keys they died at that boundary -- computed, carried, and silently dropped. This
    # pins the whole path, so a typo'd metrics key (which .get() swallows into None)
    # can never go unnoticed again.
    plan = P.plan_default_mission("t2_geom")

    assert plan.sensor is not None            # a built plan always carries its payload
    assert plan.cross_track_width_m is not None
    assert plan.parallax_m is not None

    # both are pure functions of altitude + off-nadir, so they must agree with the
    # primitives called directly on the plan's own altitude
    altitude = plan.mission_request.altitude
    off_nadir = plan.sensor.off_nadir

    assert plan.parallax_m == pytest.approx(G.sensor_parallax_m(altitude, off_nadir))
    assert plan.cross_track_width_m == pytest.approx(
        G.ground_swath_width_m(altitude, plan.sensor.cross_track_fov, off_nadir)
    )

    # the swath is what sets line spacing: offset = swath * (1 - overlap)
    assert plan.offset_distance_m == pytest.approx(
        G.offset_distance_m(plan.cross_track_width_m, plan.sensor.desired_overlap)
    )


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


def test_planner_uses_weather_leaf(monkeypatch):
    # Step B wiring: the planner must call weather.get_weather and, when it returns a
    # populated Weather (not None), use THAT object on the plan rather than the stub.
    import weather
    import objects
    sentinel = objects.Weather(
        CONST.V1_LAUNCH_POINT_LAT, CONST.V1_LAUNCH_POINT_LONG,
        datetime.datetime(2026, 7, 15, 17, 0, tzinfo=datetime.timezone.utc),
        42, 7.0, 180, 12.0, 9000, "overcast", source=CONST.WEATHER_SOURCE_NWS,
    )
    monkeypatch.setattr(weather, "get_weather", lambda lat, lon, when: sentinel)

    plan = P.plan_default_mission("t3_wx")
    assert plan.weather is sentinel                          # planner used the leaf's result
    assert plan.weather._data_source == CONST.WEATHER_SOURCE_NWS
