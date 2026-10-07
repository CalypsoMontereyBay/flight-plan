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

import constants as CONST
import geo as G
import planner as P


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

    # TWO budget assertions, because they catch different failures and the J-4 transit
    # fix is exactly the bug that looked fine under only the first one.
    #
    #   1. the grid fits the budget geo was HANDED  -> geo respected its instructions
    #   2. the whole FLIGHT fits the battery        -> those instructions were correct
    #
    # Before J-4 the engine passed (1) while failing (2) by 45 km: geo was handed the
    # entire battery, sized a grid that consumed all of it, and the transit to M1 was
    # never paid for. Keep both -- dropping (1) loses the ability to tell which half
    # broke when (2) goes red.
    grid_distance = plan.total_grid_distance_m
    grid_budget = plan.grid_budget_m
    assert grid_distance is not None and grid_budget is not None
    assert grid_distance <= grid_budget

    total_flight = plan.total_flight_distance
    usable = plan.usable_endurance_distance_m
    assert total_flight is not None and usable is not None
    assert total_flight <= usable

    # the transit is real and is being paid for: the flown route must exceed the grid by
    # the launch/land legs. A regression that silently reverts to the grid-only figure
    # makes these equal, which is precisely the defect this tier now guards.
    assert total_flight > grid_distance
    assert plan.grid_budget_m < usable

    # metric relationships. V2C: the along-track mount put both leg directions the
    # same angular distance off the sun, so EVERY line collects -- the old
    # science/transit split is gone and nothing is traverse-only.
    assert plan.science_lines == N
    assert plan.traverse_lines == 0
    assert plan.offset_lines == N - 1


def _mission_request_launching_from(launch_point_lat, launch_point_long):
    # A MissionRequest identical to the default except for where the aircraft starts and
    # ends. Launch and land are the same pad, as at Terrace Point.
    import objects

    launch = objects.Waypoint(
        "WP000", launch_point_lat, launch_point_long,
        CONST.V1_DEFAULT_AIRCRAFT_ALTITUDE_m, CONST.BLACKSWIFT_CRUISE_SPEED_ms,
        CONST.WAYPOINT_ACTION_LAUNCH, "launch", "Test-Launch",
    )
    land = objects.Waypoint(
        "WP_END", launch_point_lat, launch_point_long,
        CONST.V1_DEFAULT_LAND_ALTITUDE_m, CONST.BLACKSWIFT_CRUISE_SPEED_ms,
        CONST.WAYPOINT_ACTION_LAND, "land", "Test-Land",
    )
    return objects.MissionRequest(
        mission_name="transit fit probe",
        launch_waypoint=launch,
        land_waypoint=land,
        m1_waypoint=P._M1_Waypoint,
        altitude_m=CONST.V1_DEFAULT_AIRCRAFT_ALTITUDE_m,
        valid_time=P.DEFAULT_MISSION_DATETIME,
        require_m1_overflight=True,
        grid_orientation_deg=None,
        notes="transit fit probe",
        included_target_waypoints=[P._M1_Waypoint],
    )


def test_transit_seed_retry_converges():
    # J-4 fallback path. The seed transit is 2 * d(launch, M1), which at Terrace Point is
    # accurate to 0.40% and fits on the first pass -- so the retry branch never executes
    # on the default mission and would rot untested.
    #
    # Launching AT M1 is the degenerate case that forces it: the seed is 0, geo is handed
    # the whole battery, sizes a grid that consumes it, and the real transit out to the
    # nearest grid corner and back is then unpayable. The loop must re-seed with the
    # MEASURED transit and come back with a grid that actually fits.
    sun_state, _, weather_state, sun_az = P._build_dated_objects(P.DEFAULT_MISSION_DATETIME)
    request = _mission_request_launching_from(CONST.M1_MOORING_LAT, CONST.M1_MOORING_LONG)
    usable = P._Black_Swift_usable_endurance_m

    plan = P.build_candidate_plan(
        P._Black_Swift, usable, P._Calypso_payload, request,
        weather_state, sun_az, sun_state, "transit_retry",
    )

    # the retry actually ran: a zero seed means pass 1 handed geo the FULL budget, so a
    # grid budget below it can only have come from a re-seed with the measured transit
    assert plan.grid_budget_m < usable

    # and it converged on something flyable
    assert plan.total_lines is not None                  # a built plan always has its metrics populated
    assert plan.total_grid_distance_m is not None and plan.grid_budget_m is not None
    assert plan.total_flight_distance <= usable
    assert plan.total_grid_distance_m <= plan.grid_budget_m
    assert plan.total_lines % 2 == 1


def test_closer_launch_buys_more_science():
    # The operational payoff of the transit fix, pinned as an invariant: transit is paid
    # out of the same battery as the grid, so moving the launch point nearer M1 must buy
    # flight lines. This is the "or a stationary boat" escape hatch from the roadmap, and
    # it can only be true once the budget arithmetic accounts for the transit at all --
    # before J-4 the engine returned N=15 from anywhere, because it never paid for one.
    from_shore = P.plan_default_mission("shore")

    sun_state, _, weather_state, sun_az = P._build_dated_objects(P.DEFAULT_MISSION_DATETIME)
    boat_request = _mission_request_launching_from(
        CONST.M1_MOORING_LAT + 0.018, CONST.M1_MOORING_LONG      # ~2 km north of M1
    )
    from_boat = P.build_candidate_plan(
        P._Black_Swift, P._Black_Swift_usable_endurance_m, P._Calypso_payload,
        boat_request, weather_state, sun_az, sun_state, "boat",
    )

    # both plans are built, so the metrics compared below are populated
    assert from_boat.total_lines is not None and from_shore.total_lines is not None
    assert from_boat.total_grid_distance_m is not None and from_shore.total_grid_distance_m is not None
    assert from_boat.total_flight_distance is not None and from_shore.total_flight_distance is not None
    assert from_boat.usable_endurance_distance_m is not None
    assert from_shore.usable_endurance_distance_m is not None

    assert from_boat.total_lines > from_shore.total_lines
    assert from_boat.total_grid_distance_m > from_shore.total_grid_distance_m

    # both remain flyable -- more science, not an overrun
    assert from_boat.total_flight_distance <= from_boat.usable_endurance_distance_m
    assert from_shore.total_flight_distance <= from_shore.usable_endurance_distance_m

    # J-4.5: the approach bearing is DERIVED, not a property of the site. From shore it
    # sits near the pad->M1 reciprocal because 22 km of transit dominates a few-km grid
    # (pinned in Tier 4). Move the pad next to the grid and that reasoning evaporates --
    # the arrival swings tens of degrees. A hardcoded 344.6 would be wrong here, which is
    # exactly why the pilot-notes figure has to be recomputed per plan.
    assert P._angular_distance(
        from_boat.approach_bearing_deg, from_shore.approach_bearing_deg
    ) > 20


def test_flight_splits_into_grid_and_transit():
    # J-6 reports the flight as a grid part and a transit part. The grid is costed on its own
    # (cruise over the grid distance plus all N-1 turns) and the transit is the remainder,
    # so these closed-form relationships hold on any plan. Checked from the shore AND from
    # the boat, so they hold for two different N rather than one literal.
    #
    # A split by distance share looks right and is not: it spreads the grid's turn time into
    # the transit (42.4 / 30.5 min instead of 41.6 / 31.3 on the default plan).
    sun_state, _, weather_state, sun_az = P._build_dated_objects(P.DEFAULT_MISSION_DATETIME)
    boat_request = _mission_request_launching_from(
        CONST.M1_MOORING_LAT + 0.018, CONST.M1_MOORING_LONG      # ~2 km north of M1
    )
    from_boat = P.build_candidate_plan(
        P._Black_Swift, P._Black_Swift_usable_endurance_m, P._Calypso_payload,
        boat_request, weather_state, sun_az, sun_state, "boat_split",
    )

    for plan in (P.plan_default_mission("shore_split"), from_boat):
        n = plan.total_lines
        grid_m = plan.total_grid_distance_m
        transit_m = plan.transit_distance_m
        flight_m = plan.total_flight_distance
        grid_min = plan.grid_duration_min
        transit_min = plan.transit_duration_min
        total_min = plan.duration

        # every part of the split reaches the plan
        assert n is not None and grid_m is not None and transit_m is not None
        assert flight_m is not None and total_min is not None
        assert grid_min is not None and transit_min is not None

        cruise_ms = plan.aircraft.vehicle_cruise_speed
        turn_penalty_s = plan.aircraft.vehicle_turn_penalty

        # the distances split the flight, and the transit is real
        assert transit_m > 0
        assert grid_m + transit_m == pytest.approx(flight_m)

        # the durations split the total
        assert grid_min + transit_min == pytest.approx(total_min)

        # the grid carries every turn: N lines -> N-1 turns (60 s per minute)
        assert grid_min == pytest.approx((grid_m / cruise_ms + (n - 1) * turn_penalty_s) / 60)

        # so the transit is pure cruise. Climb and descent are unmodeled today; when Step G
        # adds them to route_duration_min they land in this remainder, and this line is the
        # one to rebase.
        assert transit_min == pytest.approx(transit_m / cruise_ms / 60)


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
        G.offset_distance_m(plan.cross_track_width_m, plan.sensor.cross_track_overlap)
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
    assert plan.weather.source == CONST.WEATHER_SOURCE_NWS
