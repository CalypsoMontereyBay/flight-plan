"""
Tier 5 -- rendering invariants.

Top of the cake: depends on everything below. Verifies the delimiter segment builder
turns the classified route into full science legs (not stubs) with clean boundaries.
The aliasing assert specifically guards the flush bug we fixed (segments must not share
a mutable list object).
"""

import math

import pytest

import constants as CONST
import outputs as OUT
import planner as P


def _plan_route_segs():
    plan = P.plan_default_mission("t4")
    route = OUT._route_coords(plan)
    segs = OUT._segment_builder(route)
    return plan, route, segs


def test_science_segment_count_and_no_stubs():
    plan, _, segs = _plan_route_segs()
    science_segs = [pts for cat, pts in segs if cat == CONST.WAYPOINT_ACTION_SCIENCE]

    # one continuous green run per science leg
    assert len(science_segs) == plan.science_lines
    # each green run spans collect_start -> line_label -> collect_stop (>= 3 pts), never a stub
    for pts in science_segs:
        assert len(pts) >= 3


def test_no_aliasing():
    # GUARDS THE FLUSH BUG: every segment must own a distinct point list. If the final
    # flush ever slips back inside the loop, segments alias one growing list and this drops.
    _, _, segs = _plan_route_segs()
    assert len({id(pts) for _, pts in segs}) == len(segs)


def test_segment_boundaries_are_shared():
    # consecutive segments meet at a shared coordinate so the polylines connect with no gap
    _, _, segs = _plan_route_segs()
    for current, following in zip(segs, segs[1:]):
        assert current[1][-1] == following[1][0]


def test_route_extent():
    _, route, _ = _plan_route_segs()
    with pytest.raises(ValueError):
        OUT._route_extent([])

    lons = [pt[0] for pt in route]
    lats = [pt[1] for pt in route]
    assert OUT._route_extent(route) == (min(lons), max(lons), min(lats), max(lats))


def test_sun_vector():
    # dx = length * sin(az), dy = length * cos(az); azimuth is compass (0 = north = +y).
    # dx is additionally divided by cos(lat) -- see test_sun_arrow_points_true.
    lat = CONST.M1_MOORING_LAT

    dx, dy = OUT._sun_vector(0, 10, lat)
    assert dx == pytest.approx(0, abs=1e-9)
    assert dy == pytest.approx(10)

    dx, dy = OUT._sun_vector(90, 10, lat)
    assert dx == pytest.approx(10 / math.cos(math.radians(lat)))
    assert dy == pytest.approx(0, abs=1e-9)


def test_sun_arrow_points_true():
    # REGRESSION: the arrow is drawn in DEGREES of lon/lat onto axes whose aspect is
    # 1/cos(lat). A degree of longitude is shorter than a degree of latitude by
    # cos(lat), so without that correction the arrow renders ~5.5 deg off true at
    # Monterey -- it drew the sun-to-track angle as 84.5 deg on a plan holding 90.0,
    # which is exactly the kind of error that makes a correct plan look broken.
    #
    # This pins the PROPERTY (the arrow points where the sun actually is) rather than
    # the formula, so it survives any future change to how the vector is built.
    lat = CONST.M1_MOORING_LAT
    aspect = 1 / math.cos(math.radians(lat))   # matches axes.set_aspect in write_png

    for azimuth in (0, 45, 90, 147.18, 180, 237.18, 315):
        dx, dy = OUT._sun_vector(azimuth, 10, lat)
        rendered = math.degrees(math.atan2(dx, dy * aspect)) % CONST.FULL_CIRCLE_DEG
        assert rendered == pytest.approx(azimuth % CONST.FULL_CIRCLE_DEG, abs=1e-6)
