"""
Testing harness for the basic mathematical functions that make up the foundation of the Calypso Flight Engine
math. If these functions fail, the entire system should be stopped.
"""

# imports:
import pytest
from shapely.geometry import Point
#red squiggles are just warnings, proper virtual environment setup and usage
#does not cause an error with this test harness.
import geo as G, planner as P, constants as CONST


def test_normalize_heading():

    assert G.normalize_heading(370) == 10
    assert G.normalize_heading(-10) == 350
    assert G.normalize_heading(360) == 0
    assert G.normalize_heading(50) == 50

def test_normalize_heading_rejects_non_Num():
    
    with pytest.raises(TypeError):
        G.normalize_heading("north")
        
def test_geodesic_full_trip():
    
    p = Point(CONST.M1_MOORING_LONG, CONST.M1_MOORING_LAT)
    
    heading = 73.0
    
    distance = 1500.0
    
    q = G.destination_point(p, heading, distance)
    
    assert G.distance_between(p, q) == pytest.approx(distance, abs=1e-3)
    assert G.bearing_between(p, q) == pytest.approx(heading, abs=1e-6)
    assert G.distance_between(p,p) == pytest.approx(0)

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
    height= 118
    cross_FOV= 48
    off_nadir= 30

    expected = 121.329

    assert G.ground_swath_width_m(height, cross_FOV, off_nadir) == pytest.approx(expected, abs=0.1)


def test_ground_footprint_along():

    # V2C along-track mount: along-track is now the TILTED axis and uses the
    # tan-difference form, h * (tan(th + fov/2) - tan(th - fov/2)).
    height=118
    along_FOV=36.8
    off_nadir=30
    expected = 108.685

    with pytest.raises(ValueError):
        G.ground_footprint_along_m(0, along_FOV, off_nadir)

    with pytest.raises(ValueError):
        G.ground_footprint_along_m(height, along_FOV, 90)

    with pytest.raises(ValueError):
        G.ground_footprint_along_m(height, along_FOV, 100)

    # The FOV-edge guard MOVED here with the tan-difference formula: 70 + 48/2 = 94 deg
    # puts the far edge past the horizon. It used to live in ground_swath_width_m.
    with pytest.raises(ValueError):
        G.ground_footprint_along_m(height, 48, 70)

    assert G.ground_footprint_along_m(height, along_FOV, off_nadir) == pytest.approx(expected, abs=0.1)


def test_offset_distance():
    
    swath=200 
    pct_overlap=30
    
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


