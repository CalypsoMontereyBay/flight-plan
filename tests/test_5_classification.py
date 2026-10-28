"""
Tier 4 -- planner classification + heading-safety.

Depends on every tier below: it drives the REAL mission and checks that the route the
planner hands downstream is semantically correct. The crown jewel is the heading-safety
test, which pins the subtle reversal fix (science follows the actual flown heading, not a
pre-reversal index) so V2 can never silently regress it.
"""

import datetime
from collections import Counter

import pytest
from shapely.geometry import Point

import aircraft_math as A
import constants as CONST
import geo as G
import planner as P


def _plan():
    return P.plan_default_mission("t3")


def _legs(grid_wps):
    step = CONST.V1_POINTS_PER_LINE
    return [grid_wps[i:i + step] for i in range(0, len(grid_wps), step)]


def _point(waypoint):
    return Point(waypoint.longitude, waypoint.latitude)


def test_route_shape_and_endpoints():
    plan = _plan()
    wps = plan.waypoints
    N = plan.total_lines
    assert N is not None                                     # a built plan always has its metrics populated

    assert len(wps) == CONST.V1_POINTS_PER_LINE * N + 2      # grid + launch + land
    assert wps[0].action == CONST.WAYPOINT_ACTION_LAUNCH
    assert wps[-1].action == CONST.WAYPOINT_ACTION_LAND


def test_action_counts():
    plan = _plan()
    N = plan.total_lines
    assert N is not None                                     # a built plan always has its metrics populated
    counts = Counter(w.action for w in plan.waypoints)

    assert counts[CONST.WAYPOINT_ACTION_TURN] == 2 * N            # 2 turns per line
    assert counts[CONST.WAYPOINT_ACTION_M1_OVERFLIGHT] == 1
    assert counts[CONST.WAYPOINT_ACTION_LINE_LABEL] == N - 1      # centers, minus the M1 override
    # V2C: every leg is a science leg under the along-track mount, so collection is
    # tagged on ALL N legs and no grid waypoint is left over as transit.
    assert counts[CONST.WAYPOINT_ACTION_COLLECT_START] == N
    assert counts[CONST.WAYPOINT_ACTION_COLLECT_STOP] == N
    assert counts[CONST.WAYPOINT_ACTION_TRANSIT] == 0


def test_collection_ordering():
    plan = _plan()
    grid = plan.waypoints[1:-1]

    for leg in _legs(grid):
        actions = [w.action for w in leg]
        if CONST.WAYPOINT_ACTION_COLLECT_START in actions:
            # camera turns on before it turns off, in flight order
            assert actions.index(CONST.WAYPOINT_ACTION_COLLECT_START) < \
                   actions.index(CONST.WAYPOINT_ACTION_COLLECT_STOP)


def test_heading_safety():
    # CROWN JEWEL (V2C): every leg collects now, so the old "is this leg flown at H?"
    # proxy has nothing left to decide. What must still hold is the PHYSICAL
    # requirement the proxy was standing in for -- every collecting leg's flown
    # bearing sits within the glint tolerance of the target relative azimuth to the
    # sun, in EITHER direction, because glint is symmetric about the solar principal
    # plane. Still reversal-safe for the same reason the old test was: it measures
    # the bearing actually flown, never an index or a parity.
    #
    # This is strictly stronger than what it replaces: it pins that the route the
    # planner actually built satisfies the gate the planner claims to enforce.
    # Using _score_glint as the measuring instrument is not circular -- Tier 0
    # already pins its behaviour against hard literals.
    plan = _plan()
    sun_az = plan.sun_state.azimuth
    grid = plan.waypoints[1:-1]

    for leg in _legs(grid):
        start = Point(leg[0].longitude, leg[0].latitude)
        end = Point(leg[-1].longitude, leg[-1].latitude)

        assert CONST.WAYPOINT_ACTION_COLLECT_START in {w.action for w in leg}
        assert P._score_glint(G.bearing_between(start, end), sun_az) \
            <= CONST.V1_GLINT_TOLERANCE_DEG


def test_glint_gate_helpers():
    assert P._passes_glint_gate(0)
    assert not P._passes_glint_gate(CONST.V1_GLINT_TOLERANCE_DEG + 1)
    # _score_candidate is a thin pass-through to the glint score for the science leg
    assert P._score_candidate(135, 0) == P._score_glint(135, 0)


def test_transit_bearings_reach_the_plan():
    # J-4.5 wiring. Same failure mode test_viewing_geometry_reaches_the_plan guards in
    # Tier 3: a reported figure can be computed, stored and then silently unreachable.
    # These two are the pilot-notes document's first real input, so pin the whole path.
    plan = _plan()

    assert plan.departure_bearing_deg is not None
    assert plan.approach_bearing_deg is not None
    assert 0 <= plan.departure_bearing_deg < CONST.FULL_CIRCLE_DEG
    assert 0 <= plan.approach_bearing_deg < CONST.FULL_CIRCLE_DEG


def test_transit_bearings_measure_the_final_route():
    # THE invariant of J-4.5, and the one that catches the mistake actually made while
    # scoping it: the bearings must be read off the route AFTER _reorient_to_launch has
    # chosen which end of the serpentine the aircraft exits from. Measured on the raw
    # grid the approach comes out ~10 deg off, because the other corner is the exit.
    #
    # Expressed as "whatever the plan reports must equal the bearing between the last two
    # waypoints it is handing downstream", so it stays true when N, the orientation or
    # the launch point change -- none of which this tier hardcodes.
    plan = _plan()
    wps = plan.waypoints

    pad_out = Point(wps[0].longitude, wps[0].latitude)
    first_grid = Point(wps[1].longitude, wps[1].latitude)
    last_grid = Point(wps[-2].longitude, wps[-2].latitude)
    pad_in = Point(wps[-1].longitude, wps[-1].latitude)

    assert plan.departure_bearing_deg == pytest.approx(
        G.bearing_between(pad_out, first_grid), abs=1e-6
    )
    assert plan.approach_bearing_deg == pytest.approx(
        G.bearing_between(last_grid, pad_in), abs=1e-6
    )


def test_shore_approach_tracks_the_m1_reciprocal():
    # Why the approach bearing is stable for a shore launch, pinned as a relationship:
    # the pad is 22.4 km from M1 while the grid is a few km across, so from the pad the
    # exit corner is only a handful of degrees off the mooring itself. This is what makes
    # the pilot-notes approach warning predictable enough to brief in advance -- and it
    # is a property of THIS geometry, not a law, which is why a boat launch gets its own
    # assertion in Tier 3.
    plan = _plan()
    pad = Point(plan.waypoints[0].longitude, plan.waypoints[0].latitude)
    m1 = Point(CONST.M1_MOORING_LONG, CONST.M1_MOORING_LAT)

    outbound_to_m1 = G.bearing_between(pad, m1)
    reciprocal = (outbound_to_m1 + 180) % CONST.FULL_CIRCLE_DEG

    assert P._angular_distance(plan.approach_bearing_deg, reciprocal) < 15


def test_camera_starts_an_inset_past_every_turn():
    # THE invariant of the camera rollout fix. Every collect point sits the inset in from its
    # turn waypoint, at both ends of every line, so the aircraft has rolled out of the turn
    # before the camera starts. Line 1's first turn sits a further pushback out (Strat 1).
    # The inset is the plan's own, sized from its aircraft and design wind, and it is checked
    # at both ends of the wind range, so it holds for two different N.
    for design_wind_ms in (0, P._BlackSwift_S3.vehicle_wind_rating):
        plan = P.plan_default_mission("rollout", design_wind_aloft_ms=design_wind_ms)
        inset = plan.collection_inset_m
        pushback = plan.entry_pushback_m
        assert inset is not None and pushback is not None
        assert plan.line_length_m is not None and plan.parallax_m is not None

        # The S3 captures its waypoints early, so its camera starts early by its capture
        # distance, not by PX4's measured figure (K-4).
        capture_m = A.waypoint_capture_distance_m(plan.aircraft)
        assert capture_m is not None
        assert inset == pytest.approx(
            A.rollout_inset_m(plan.aircraft, design_wind_ms, camera_early_start_m=capture_m)
        )

        # the inset clears the turn itself, which the old 52 m against a 57 m radius did not
        assert inset > A.ground_turn_radius_m(plan.aircraft, design_wind_ms)

        # Each line is extended by parallax + inset at both ends, so every collect point sits
        # exactly one parallax outside the science box and image 1's boresight lands on the
        # box edge. Extend by any other inset and the box's first metres go unimaged.
        box_edge_m = plan.line_length_m / 2 + plan.parallax_m

        for index, leg in enumerate(_legs(plan.waypoints[1:-1])):
            in_turn, collect_start, center, collect_stop, out_turn = (_point(w) for w in leg)
            lead_in = inset + pushback if index == 0 else inset

            assert G.distance_between(in_turn, collect_start) == pytest.approx(lead_in, abs=1.0)
            assert G.distance_between(collect_stop, out_turn) == pytest.approx(inset, abs=1.0)
            assert G.distance_between(center, collect_start) == pytest.approx(box_edge_m, abs=1.0)
            assert G.distance_between(center, collect_stop) == pytest.approx(box_edge_m, abs=1.0)


def test_line_one_entry_meets_the_turn_rule():
    # Strat 1. The pushback is aircraft_math's formula at the arrival angle the plan records,
    # and that angle is the turn the route actually flies onto line 1. Moving the waypoint
    # back widens the turn slightly and never narrows it: well under a degree from the shore.
    plan = _plan()
    angle = plan.entry_arrival_angle_deg
    assert angle is not None and plan.entry_pushback_m is not None
    assert plan.entry_pushback_m == pytest.approx(
        A.entry_pushback_m(plan.aircraft, plan.mission_request.design_wind_aloft_ms, angle)
    )

    wps = plan.waypoints
    flown = P._angular_distance(
        G.bearing_between(_point(wps[0]), _point(wps[1])),
        G.bearing_between(_point(wps[1]), _point(wps[2])),
    )
    assert 0 <= flown - angle < 1

    # the moved waypoint stays on line 1's axis
    assert P._angular_distance(
        G.bearing_between(_point(wps[1]), _point(wps[2])),
        G.bearing_between(_point(wps[2]), _point(wps[3])),
    ) == pytest.approx(0, abs=0.5)

    # A turn of 90 deg or less needs no pushback, and line 1 keeps the plain inset. 08:00
    # local on 2026-02-15 arrives at about 40 deg. The date is past, so no forecast is fetched.
    gentle = P.plan_default_mission(
        "gentle_entry", datetime.datetime(2026, 2, 15, 16, 0, tzinfo=datetime.timezone.utc)
    )
    assert gentle.entry_arrival_angle_deg is not None and gentle.collection_inset_m is not None
    assert gentle.entry_arrival_angle_deg <= 90
    assert gentle.entry_pushback_m == 0

    gentle_wps = gentle.waypoints
    assert G.distance_between(_point(gentle_wps[1]), _point(gentle_wps[2])) == pytest.approx(
        gentle.collection_inset_m, abs=1.0
    )
