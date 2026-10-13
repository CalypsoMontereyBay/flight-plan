"""
Tier 0 -- geometric and scoring primitives.

The basic mathematical functions the whole Calypso Flight Engine is built on: geodesy,
swath/footprint/parallax geometry, line offsets, angular distance and the glint score.
If these fail, the entire system should be stopped -- the -x gate halts the run here.
"""

import math

import pytest
from shapely.geometry import Point

import constants as CONST
import geo as G
import planner as P


def test_normalize_heading():

    assert G.normalize_heading(370) == 10
    assert G.normalize_heading(-10) == 350
    assert G.normalize_heading(360) == 0
    assert G.normalize_heading(50) == 50


def test_normalize_heading_rejects_non_numeric():

    with pytest.raises(TypeError):
        G.normalize_heading("north")


def test_geodesic_full_trip():

    p = Point(CONST.M1_MOORING_LONG, CONST.M1_MOORING_LAT)

    heading = 73.0

    distance = 1500.0

    q = G.destination_point(p, heading, distance)

    assert G.distance_between(p, q) == pytest.approx(distance, abs=1e-3)
    assert G.bearing_between(p, q) == pytest.approx(heading, abs=1e-6)
    assert G.distance_between(p, p) == pytest.approx(0)


def test_ground_swath_width_rejects_bad_geometry1():

    with pytest.raises(ValueError):
        G.ground_swath_width_m(0, 48, 40)


def test_ground_swath_width_rejects_bad_geometry2():

    # V2C: cross-track is now the UNTILTED axis, so the slant form has no FOV edge
    # that can swing up to the horizon -- 70 deg off-nadir is legal here now. The
    # only remaining geometric limit is the off-nadir angle itself.
    with pytest.raises(ValueError):
        G.ground_swath_width_m(118, 48, 90)


def test_ground_swath_width():

    # V2C along-track mount: cross-track uses the SLANT form,
    #   2 * (h / cos(off_nadir)) * tan(fov / 2)
    height = 118
    cross_fov = 48
    off_nadir = 30

    expected = 121.329

    assert G.ground_swath_width_m(height, cross_fov, off_nadir) == pytest.approx(expected, abs=0.1)


def test_ground_footprint_along():

    # V2C along-track mount: along-track is now the TILTED axis and uses the
    # tan-difference form, h * (tan(th + fov/2) - tan(th - fov/2)).
    height = 118
    along_fov = 36.8
    off_nadir = 30
    expected = 108.685

    with pytest.raises(ValueError):
        G.ground_footprint_along_m(0, along_fov, off_nadir)

    with pytest.raises(ValueError):
        G.ground_footprint_along_m(height, along_fov, 90)

    with pytest.raises(ValueError):
        G.ground_footprint_along_m(height, along_fov, 100)

    # The FOV-edge guard MOVED here with the tan-difference formula: 70 + 48/2 = 94 deg
    # puts the far edge past the horizon. It used to live in ground_swath_width_m.
    with pytest.raises(ValueError):
        G.ground_footprint_along_m(height, 48, 70)

    assert G.ground_footprint_along_m(height, along_fov, off_nadir) == pytest.approx(expected, abs=0.1)


def test_swath_uses_the_untilted_slant_form():

    # GUARDS THE V2C FORMULA SWAP. Both the slant form and the retired tan-difference
    # form agree at nadir and diverge as the camera tilts, so a nadir check alone
    # proves nothing. The discriminator is the GROWTH LAW: the untilted (slant) axis
    # obeys s(theta) = s(0) / cos(theta) exactly. The tilted form does not -- at 30 deg
    # it returns 150.01 against the slant form's 121.33, a ~24% over-report that would
    # feed straight into line spacing and silently under-sample the ocean.
    #
    # NOTE: sign symmetry does NOT discriminate. tan is odd, so tan(th+f) - tan(th-f)
    # is even in theta and BOTH forms are symmetric in the sign of off-nadir.

    height = 118
    cross_fov = 48
    off_nadir = 30

    at_nadir = 2 * height * math.tan(math.radians(cross_fov / 2))

    assert G.ground_swath_width_m(height, cross_fov, 0) == pytest.approx(at_nadir, abs=0.01)
    assert G.ground_swath_width_m(height, cross_fov, off_nadir) == pytest.approx(
        at_nadir / math.cos(math.radians(off_nadir)), abs=0.01
    )


def test_sensor_parallax_m():

    # Along-track distance between the point the aircraft is OVER and the point the
    # camera is LOOKING AT. Reporting only in V2C-1 -- nothing corrects for it yet.

    assert G.sensor_parallax_m(118, 30) == pytest.approx(68.127, abs=0.01)

    # a nadir-pointing camera has no parallax at all
    assert G.sensor_parallax_m(118, 0) == pytest.approx(0)

    with pytest.raises(ValueError):
        G.sensor_parallax_m(0, 30)

    with pytest.raises(ValueError):
        G.sensor_parallax_m(118, 90)


def test_offset_distance():

    swath = 200
    pct_overlap = 30

    with pytest.raises(ValueError):
        G.offset_distance_m(swath, 100)

    with pytest.raises(ValueError):
        G.offset_distance_m(swath, -1)

    with pytest.raises(ValueError):
        G.offset_distance_m(0, pct_overlap)

    assert G.offset_distance_m(swath, pct_overlap) == pytest.approx(140)


def test_angular_distance():

    heading1 = 10
    heading2 = 10

    heading3 = 0
    heading4 = 180

    heading5 = 350
    heading6 = 10

    assert P._angular_distance(heading1, heading2) == pytest.approx(0)
    assert P._angular_distance(heading3, heading4) == pytest.approx(180)
    assert P._angular_distance(heading5, heading6) == pytest.approx(20)


def test_score_glint():

    # V2C along-track mount: the ideal is SCIENCE_RELATIVE_AZIMUTH_deg (90) off the sun,
    # and its mirror at 270 -- glint is symmetric about the solar principal plane, so the
    # sun off either shoulder scores the same.

    sun_az1 = 0

    heading1 = 90       # on target

    heading2 = 270      # mirror of the target, equally good

    heading3 = 135      # the retired V1 ideal -- now 45 deg off target

    heading4 = 0        # flying straight at the sun -- worst case

    assert P._score_glint(heading1, sun_az1) == pytest.approx(0)
    assert P._score_glint(heading2, sun_az1) == pytest.approx(0)
    assert P._score_glint(heading3, sun_az1) == pytest.approx(45)
    assert P._score_glint(heading4, sun_az1) == pytest.approx(90)
