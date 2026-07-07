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
    
    with pytest.raises(ValueError):
        G.ground_swath_width_m(118, 48, 70)


def test_ground_swath_width():
    
    height= 118 
    cross_FOV= 48 
    off_nadir= 40
    
    expected = 208.10
    
    assert G.ground_swath_width_m(height, cross_FOV, off_nadir) == pytest.approx(expected, abs=0.1)


def test_ground_footprint_along():
    
    height=118
    along_FOV=36.8
    off_nadir=40
    expected = 102.5
    
    with pytest.raises(ValueError):
        G.ground_footprint_along_m(0, along_FOV, off_nadir)
        
    with pytest.raises(ValueError):
        G.ground_footprint_along_m(height, along_FOV, 90)
        
    with pytest.raises(ValueError):
        G.ground_footprint_along_m(height, along_FOV, 100)
 
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

    heading1 = 135
    sun_az1 = 0
    
    heading2 = 225
    
    heading3 = 90
    
    heading4 = 0
    
    assert P._score_glint(heading1, sun_az1) == pytest.approx(0)
    assert P._score_glint(heading2, sun_az1) == pytest.approx(0)
    assert P._score_glint(heading3, sun_az1) == pytest.approx(45)
    assert P._score_glint(heading4, sun_az1) == pytest.approx(135)


