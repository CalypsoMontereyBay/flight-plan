

'''
This file contains all the geographic math currently needed for V1 of the flight planning engine.
It is not designed to be knowledgable of ANY aircraft parameters. Just like a mission request
object, geo.py is simply concerned with the ROUTE. For now, the functions here also
assume perfectly legality and other constants according to constants.py.

It contains the following functions (descriptions soon to follow):

        1. normalize_heading(heading_deg)
        2. destination_point(start_lon, start_lat, heading_deg, distance_km)
        3. bearing_between(point A, point B)
        4. distance_between(point A, point B)
        5. make_line_through_point(center_point, heading_deg, length_km)
        6. offset_line(line, offset_heading_deg, offset_km)
        7. make_lawnmower_grid_through_m1()
'''

# IMPORTS:
from pyproj import Geod
from shapely.geometry import Point, LineString
import math
#from typing import List, Tuple

'''
FUNCTION: normalize_heading(heading_deg)
This function standarizes heading inputs into the following range:
0 <= heading < 360.
(0 degress is considered equivalent to 360 in this context)
(This effectively makes the range: 0 <= heading <= 359)

PARAMETER(S): heading_deg: a heading value in degress, floats are rejected

RETURNS: heading_deg standardized to the range 0 <= heading < 360 
'''

def normalize_heading(heading_deg):
        
        while isinstance(heading_deg, int) is not True:
                print("Invalid input! Please input an integer!\n")
                heading_deg = int(input("Input an integer heading value: "))

        print("Success!")
        
        if heading_deg < 0:
                print("Heading normalized.")
                return (heading_deg + 360)
        elif heading_deg > 359:
                print("Heading normalized.")
                return (heading_deg % 360)
        else:
                print("Heading normalized.")
                return heading_deg
        
        
        
