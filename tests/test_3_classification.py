"""
Tier 3 -- planner classification + heading-safety.

Depends on every tier below: it drives the REAL mission and checks that the route the
planner hands downstream is semantically correct. The crown jewel is the heading-safety
test, which pins the subtle reversal fix (science follows the actual flown heading, not a
pre-reversal index) so V2 can never silently regress it.
"""

from collections import Counter

from shapely.geometry import Point
import constants as CONST, planner as P, geo as G


def _plan():
    return P.plan_default_mission("t3")


def _legs(grid_wps):
    step = CONST.V1_POINTS_PER_LINE
    return [grid_wps[i:i + step] for i in range(0, len(grid_wps), step)]


def test_route_shape_and_endpoints():
    plan = _plan()
    wps = plan.waypoints
    N = plan.total_lines

    assert len(wps) == CONST.V1_POINTS_PER_LINE * N + 2      # grid + launch + land
    assert wps[0].action == CONST.WAYPOINT_ACTION_LAUNCH
    assert wps[-1].action == CONST.WAYPOINT_ACTION_LAND


def test_action_counts():
    plan = _plan()
    N = plan.total_lines
    counts = Counter(w.action for w in plan.waypoints)

    assert counts[CONST.WAYPOINT_ACTION_TURN] == 2 * N            # 2 turns per line
    assert counts[CONST.WAYPOINT_ACTION_M1_OVERFLIGHT] == 1
    assert counts[CONST.WAYPOINT_ACTION_LINE_LABEL] == N - 1      # centers, minus the M1 override
    assert counts[CONST.WAYPOINT_ACTION_COLLECT_START] == (N + 1) // 2
    assert counts[CONST.WAYPOINT_ACTION_COLLECT_STOP] == (N + 1) // 2
    assert counts[CONST.WAYPOINT_ACTION_TRANSIT] == 2 * (N // 2)  # 2 interior pts per transit line


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
    # CROWN JEWEL: a leg is science-tagged if and only if it is actually flown at the
    # winning orientation H. This holds regardless of whether _reorient_to_launch reversed
    # the route (which flips every leg's heading), because tagging follows measured bearing.
    plan = _plan()
    H = plan.chosen_orientation
    grid = plan.waypoints[1:-1]

    for leg in _legs(grid):
        start = Point(leg[0].longitude, leg[0].latitude)
        end = Point(leg[-1].longitude, leg[-1].latitude)
        flown_at_H = P._angular_distance(G.bearing_between(start, end), H) < CONST.DEGREE_NINETY

        has_collection = CONST.WAYPOINT_ACTION_COLLECT_START in {w.action for w in leg}
        assert has_collection == flown_at_H


def test_glint_gate_helpers():
    assert P._passes_glint_gate(0)
    assert not P._passes_glint_gate(CONST.V1_GLINT_TOLERANCE_DEG + 1)
    # _score_candidate is a thin pass-through to the glint score for the science leg
    assert P._score_candidate(135, 0) == P._score_glint(135, 0)
