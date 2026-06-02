"""
The outputs.py file takes the data from our candidate plan and produces
human readable output in the form of a KML file and a PNG file.

KML's can be uploaded to QGroundControl, BlackSwift's FMS, or Google Earth.

PNG's simply exist as a visual reference for the RPIC and do not serve any other
purpose.

This file does not check if output is "correct", it is simply a black box
that takes the data the engine produces and produces output.

This follows my design of "dumb unidirectionality", meaning that files
are only as knowledgeable of the rest of the program as they have to be
and the engine's pipline follows a linear, unidirectional computational flow.

**NOTE**: Outputs.py may not always be the last link in the chain, once legal
and other sources of validation are needed, its position may change to only produce
output from validated data.
"""

# Calypso engine file imports:
from objects import CandidatePlan, Waypoint
import constants as CONST

# Package imports
import simplekml
import matplotlib

# Setting png backend
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
import math
import datetime
from typing import Optional, Iterable
import os

# Outputs.py helpers are defined below:

#Walks the candidate plan's route and fills a list with the actions needed to generate kml
def _route_coords(plan: CandidatePlan):
    
    #KML list for holding the necessary items to make points using
    #simplekml. 
    kml_wp_list = []
    for point in plan.waypoints:
        
        #Each element in the list is a tuple containing a given waypoint's coordinates, altitude,
        # and action.
        kml_wp = (point.longitude, point.latitude, point.altitude, point.action)
        kml_wp_list.append(kml_wp)
        
    return kml_wp_list

def _segments_by_action(plan: CandidatePlan):
    
    pass


#converts azimuth to a (dx, dy) for PNG arrow denoting sun position/angle
def _sun_vector(sun_az_deg, length):
    
    pass


def _output_path(plan: CandidatePlan, extension: str, out_dir: str= "EMPTY"):
    
    #Won't be used in v1, but when a directory is not found, the engine will make one.
    if out_dir == "EMPTY":
        
        os.mkdir(CONST.OUTPUT_DIRECTORY)
        
    #gets the current date and time after establishing it
    curr_datetime = datetime.datetime.now()
    
    output_path = f"{CONST.OUTPUT_DIRECTORY}/{plan.name}_{{{{{curr_datetime.year}{curr_datetime.month}{curr_datetime.day}}}}}-{{{curr_datetime.hour}{curr_datetime.minute}}}.{extension}"
    
    return output_path


