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

import aircraft_math as A
import constants as CONST
import geo as G
import planner as P


def _m1_point():
    return Point(CONST.M1_MOORING_LONG, CONST.M1_MOORING_LAT)


def test_make_line_through_point_structure():
    orientation = 90.0
    line_length = 2000.0                       # >> 2 * inset, so the normal branch runs
    inset = 300.0                              # geo places whatever inset it is handed
    line = G.make_line_through_point(_m1_point(), orientation, line_length, inset)
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
    assert G.distance_between(start, c_start) == pytest.approx(inset, abs=1.0)
    assert G.distance_between(end, c_end) == pytest.approx(inset, abs=1.0)

    # a negative inset would put the camera on before the turn
    with pytest.raises(ValueError):
        G.make_line_through_point(_m1_point(), orientation, line_length, -1)


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

    # and the battery is the plan's own aircraft's. K-3 swapped the default aircraft; a
    # budget left behind from the old one would pass every check above.
    assert usable == pytest.approx(
        A.max_planned_distance_m(plan.aircraft, CONST.RTH_SEED_RESERVE_FRACTION)
    )

    # metric relationships. V2C: the along-track mount put both leg directions the
    # same angular distance off the sun, so EVERY line collects -- the old
    # science/transit split is gone and nothing is traverse-only.
    assert plan.science_lines == N
    assert plan.traverse_lines == 0
    assert plan.offset_lines == N - 1


def _mission_request_launching_from(launch_point_lat, launch_point_long,
                                    design_wind_aloft_ms=CONST.DEFAULT_DESIGN_WIND_ALOFT_ms,
                                    climb_waypoint=None):
    # A MissionRequest identical to the default except for where the aircraft starts and
    # ends, and optionally its design wind and climb point. Launch and land are the same
    # pad, as at Terrace Point.
    import objects

    launch = objects.Waypoint(
        "WP000", launch_point_lat, launch_point_long,
        CONST.V1_DEFAULT_AIRCRAFT_ALTITUDE_m, CONST.BLACKSWIFT_S3_CRUISE_SPEED_ms,
        CONST.WAYPOINT_ACTION_LAUNCH, "launch", "Test-Launch",
    )
    land = objects.Waypoint(
        "WP_END", launch_point_lat, launch_point_long,
        CONST.V1_DEFAULT_LAND_ALTITUDE_m, CONST.BLACKSWIFT_S3_CRUISE_SPEED_ms,
        CONST.WAYPOINT_ACTION_LAND, "land", "Test-Land",
    )
    return objects.MissionRequest(
        mission_name="transit fit probe",
        launch_waypoint=launch,
        land_waypoint=land,
        m1_waypoint=P._M1_Waypoint,
        altitude_m=CONST.V1_DEFAULT_AIRCRAFT_ALTITUDE_m,
        valid_time=P.DEFAULT_MISSION_DATETIME,
        design_wind_aloft_ms=design_wind_aloft_ms,
        require_m1_overflight=True,
        grid_orientation_deg=None,
        notes="transit fit probe",
        included_target_waypoints=[P._M1_Waypoint],
        climb_waypoint=climb_waypoint,
    )


def test_transit_seed_retry_converges():
    # J-4 fallback path. The seed transit is 2 * d(launch, M1), which at Terrace Point is
    # accurate to 0.40% and fits on the first pass -- so the retry branch never executes
    # on the default mission and would rot untested.
    #
    # Launching AT M1 makes the seed 0, so geo is handed the whole battery. Whether the real
    # transit out to the nearest grid corner and back still fits depends on how much of the
    # budget the chosen N left over, and that slack moves with the collection inset. So the
    # probe plans for every design wind up to the aircraft's rating: at least one of them
    # must take the re-seed, and every one must converge on a grid that actually fits.
    sun_state, _, weather_state, sun_az = P._build_dated_objects(P.DEFAULT_MISSION_DATETIME)
    usable = P._BlackSwift_S3_usable_endurance_m
    retried = []

    for design_wind_ms in range(P._BlackSwift_S3.vehicle_wind_rating + 1):
        request = _mission_request_launching_from(
            CONST.M1_MOORING_LAT, CONST.M1_MOORING_LONG, design_wind_ms
        )
        plan = P.build_candidate_plan(
            P._BlackSwift_S3, usable, P._Calypso_payload, request,
            weather_state, sun_az, sun_state, "transit_retry",
        )
        assert plan.total_lines is not None              # a built plan always has its metrics populated
        assert plan.total_grid_distance_m is not None and plan.grid_budget_m is not None

        # a zero seed means pass 1 handed geo the FULL budget, so a grid budget below it can
        # only have come from a re-seed with the measured transit
        retried.append(plan.grid_budget_m < usable)

        # converged on something flyable
        assert plan.total_flight_distance <= usable
        assert plan.total_grid_distance_m <= plan.grid_budget_m
        assert plan.total_lines % 2 == 1

    assert any(retried)


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
        P._BlackSwift_S3, P._BlackSwift_S3_usable_endurance_m, P._Calypso_payload,
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
        P._BlackSwift_S3, P._BlackSwift_S3_usable_endurance_m, P._Calypso_payload,
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

        # and the flight is the route actually handed downstream, waypoint to waypoint. Line
        # 1's lead-in (Strat 1) is flown but sits outside geo's grid, so leaving it out of the
        # transit would still split cleanly and would fail only here.
        wps = plan.waypoints
        flown_m = sum(G.distance_between(a.point, b.point) for a, b in zip(wps, wps[1:]))
        assert flown_m == pytest.approx(flight_m, abs=1.0)

        # the durations split the total
        assert grid_min + transit_min == pytest.approx(total_min)

        # the grid carries every turn: N lines -> N-1 turns (60 s per minute)
        assert grid_min == pytest.approx((grid_m / cruise_ms + (n - 1) * turn_penalty_s) / 60)

        # so the transit is cruise plus the phases flown outside the grid: the climb orbit,
        # whatever descent the approach can't hold, and the two hand-offs (K-4). Rebased
        # from pure cruise when K-4 stopped counting them as zero.
        phase_min = plan.phase_duration_min
        assert phase_min is not None and phase_min > 0
        assert transit_min == pytest.approx(transit_m / cruise_ms / 60 + phase_min)


def test_higher_design_wind_never_gives_more_lines():
    # Camera rollout fix. The design wind sets the inset at both ends of every line, so
    # a windier plan flies longer lines and the same battery buys no more of them. Planned
    # for every design wind up to the aircraft's rating, so it holds wherever the step to
    # fewer lines falls, not at one pinned wind.
    plans = [
        P.plan_default_mission("design_wind", design_wind_aloft_ms=design_wind_ms)
        for design_wind_ms in range(P._BlackSwift_S3.vehicle_wind_rating + 1)
    ]

    for calmer, windier in zip(plans, plans[1:]):
        assert calmer.total_lines is not None and windier.total_lines is not None
        assert calmer.collection_inset_m is not None and windier.collection_inset_m is not None
        assert windier.collection_inset_m > calmer.collection_inset_m
        assert windier.total_lines <= calmer.total_lines

    # and every one of them still fits the battery
    for plan in plans:
        assert plan.total_flight_distance is not None
        assert plan.usable_endurance_distance_m is not None
        assert plan.total_flight_distance <= plan.usable_endurance_distance_m

    # a negative design wind is a typo, never a calm day
    with pytest.raises(ValueError):
        _mission_request_launching_from(CONST.M1_MOORING_LAT, CONST.M1_MOORING_LONG, -1)


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


# ---- Step K-4: takeoff and landing phases --------------------------------------------


def _plan_flown_by(vehicle, mission_request=None, name="k4_variant"):
    # The default mission, or mission_request, flown by vehicle on its own battery.
    sun_state, default_request, weather_state, sun_az = P._build_dated_objects(
        P.DEFAULT_MISSION_DATETIME
    )
    return P.build_candidate_plan(
        vehicle, A.max_planned_distance_m(vehicle, CONST.RTH_SEED_RESERVE_FRACTION),
        P._Calypso_payload, mission_request or default_request, weather_state, sun_az,
        sun_state, name,
    )


def _s3_with(climb_rate_ms=None, descent_rate_ms=None, waypoint_lookahead_s=None):
    # The S3 with its climb and descent rates, or its lookahead, swapped out.
    import objects

    s3 = P._BlackSwift_S3
    return objects.Vehicle(
        s3.vehicle_endurance, s3.vehicle_wind_rating,
        climb_rate_ms or s3.vehicle_climb_rate, descent_rate_ms or s3.vehicle_descent_rate,
        s3.vehicle_turn_radius, s3.vehicle_turn_penalty, s3.vehicle_stall_speed,
        s3.vehicle_cruise_speed, s3.vehicle_type, s3.firmware_type,
        hover_speed_ms=s3.hover_speed_ms,
        transition_height_agl_m=s3.transition_height_agl_m,
        waypoint_lookahead_s=waypoint_lookahead_s or s3.waypoint_lookahead_s,
    )


def test_takeoff_and_landing_phases_are_paid_for():
    # K-4. The climb is flown in an orbit and costs its whole duration. The descent is flown
    # along the approach and costs only what the approach can't hold. Each of the two
    # operator hand-offs has a reserve. Checked from the shore, whose 23 km approach holds
    # the whole descent, and from the boat, whose short approach does not.
    boat_request = _mission_request_launching_from(
        CONST.M1_MOORING_LAT + 0.018, CONST.M1_MOORING_LONG      # ~2 km north of M1
    )
    shore = P.plan_default_mission("phases_shore")
    boat = _plan_flown_by(P._BlackSwift_S3, boat_request, "phases_boat")

    for plan in (shore, boat):
        aircraft = plan.aircraft
        wps = plan.waypoints
        n = plan.total_lines
        flight_m = plan.total_flight_distance
        usable_m = plan.usable_endurance_distance_m
        phase_min = plan.phase_duration_min
        assert n is not None and flight_m is not None and usable_m is not None
        assert phase_min is not None and plan.transition_height_agl_m is not None

        # the climb and the descent span the transition height over the pad to cruise
        height_m = plan.mission_request.altitude - (
            CONST.TERRACE_POINT_AMSL_m + plan.transition_height_agl_m
        )
        assert plan.climb_duration_min == pytest.approx(A.climb_duration_min(aircraft, height_m))
        assert plan.descent_duration_min == pytest.approx(A.descent_duration_min(aircraft, height_m))

        # the descent's overrun is what the plan's own approach leg can't hold
        approach_m = G.distance_between(wps[-2], wps[-1])
        assert plan.descent_overrun_min == pytest.approx(
            A.descent_overrun_min(aircraft, height_m, approach_m)
        )

        climb_min = plan.climb_duration_min
        overrun_min = plan.descent_overrun_min
        handoff_min = plan.handoff_reserve_min
        assert climb_min is not None and overrun_min is not None and handoff_min is not None
        assert handoff_min == pytest.approx(2 * CONST.OPERATOR_HANDOFF_RESERVE_min)
        assert phase_min == pytest.approx(climb_min + overrun_min + handoff_min)

        # the duration is the route at cruise plus the phases, and the battery pays for both
        assert plan.duration == pytest.approx(A.route_duration_min(flight_m, n, aircraft) + phase_min)
        assert flight_m + A.cruise_distance_m(aircraft, phase_min) <= usable_m

    assert shore.descent_overrun_min == 0
    assert boat.descent_overrun_min is not None and boat.descent_overrun_min > 0


def test_slower_climbs_never_give_more_lines():
    # The phases are reserved before geo sizes the grid, so an aircraft that spends longer
    # climbing and descending flies the same grid or a smaller one, and at some rate a
    # smaller one: the reservation reaches the sizing.
    lines = []
    for rate_ms in (100, 3, 1, 0.5):
        plan = _plan_flown_by(_s3_with(climb_rate_ms=rate_ms, descent_rate_ms=rate_ms))
        assert plan.total_lines is not None
        lines.append(plan.total_lines)

    assert all(slower <= faster for faster, slower in zip(lines, lines[1:]))
    assert lines[-1] < lines[0]


def test_climb_point_sits_on_the_departure_bearing_clear_of_the_pad():
    # By default the climb orbit is centred on the departure bearing, one radius plus the
    # pad clearance out, in line with line 1's first waypoint.
    plan = P.plan_default_mission("climb_point")
    climb = plan.climb_waypoint
    radius_m = plan.climb_orbit_radius_m
    pad = plan.waypoints[0]
    assert climb is not None and radius_m is not None

    # the aircraft leaves the pad for the climb point, and the climb point is on its way
    assert plan.departure_bearing_deg == pytest.approx(G.bearing_between(pad, climb), abs=1e-6)
    assert P._angular_distance(
        G.bearing_between(pad, climb), G.bearing_between(pad, plan.waypoints[1])
    ) == pytest.approx(0, abs=1e-6)

    # and the whole orbit clears the pad
    assert G.distance_between(pad, climb) == pytest.approx(
        radius_m + CONST.CLIMB_ORBIT_PAD_CLEARANCE_m, abs=0.01
    )
    assert G.distance_between(pad, climb) > radius_m

    # A climb point the request gives is used as given, off the default's axis. The
    # outbound transit runs through it, the aircraft departs toward it, and line 1's entry
    # is measured from it, so the turn the route flies from it matches the recorded angle.
    import objects

    given_point = G.destination_point(pad, 200, 3000)
    given = objects.Waypoint(
        "WP_CLIMB", given_point.y, given_point.x, CONST.V1_DEFAULT_AIRCRAFT_ALTITUDE_m,
        CONST.BLACKSWIFT_S3_CRUISE_SPEED_ms, CONST.WAYPOINT_ACTION_CLIMB_ORBIT,
        "given climb", "Given-Climb",
    )
    request = _mission_request_launching_from(
        CONST.V1_LAUNCH_POINT_LAT, CONST.V1_LAUNCH_POINT_LONG, climb_waypoint=given
    )
    given_plan = _plan_flown_by(P._BlackSwift_S3, request, "given_climb")
    wps = given_plan.waypoints
    angle = given_plan.entry_arrival_angle_deg
    assert given_plan.climb_waypoint is given
    assert given_plan.entry_pushback_m is not None and angle is not None

    outbound_m = (G.distance_between(wps[0], given) + G.distance_between(given, wps[1])
                  + given_plan.entry_pushback_m)
    assert given_plan.transit_distance_m == pytest.approx(
        outbound_m + G.distance_between(wps[-2], wps[-1])
    )
    assert given_plan.departure_bearing_deg == pytest.approx(G.bearing_between(wps[0], given))

    flown = P._angular_distance(
        G.bearing_between(given, wps[1]), G.bearing_between(wps[1], wps[2])
    )
    assert 0 <= flown - angle < 1


def test_no_leg_is_shorter_than_the_capture_distance():
    # The S3 moves on to its next waypoint 126 m before reaching it, so a shorter leg would
    # be skipped, camera item and all. Every leg of the default plan is longer.
    plan = P.plan_default_mission("legs")
    capture_m = A.waypoint_capture_distance_m(plan.aircraft)
    assert capture_m is not None
    wps = plan.waypoints
    assert min(G.distance_between(a, b) for a, b in zip(wps, wps[1:])) >= capture_m

    # A vehicle that captured 420 m early (a 10 s lookahead at 21 m/s) would skip the
    # 313.4 m legs between lines, so the planner refuses to build it that route.
    with pytest.raises(ValueError):
        _plan_flown_by(_s3_with(waypoint_lookahead_s=10))
