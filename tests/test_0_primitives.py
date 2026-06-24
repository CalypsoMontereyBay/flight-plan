"""
Testing harness for the basic mathematical functions that make up the foundation of the Calypso Flight Engine
math. If these functions fail, the entire system should be stopped. If function will have a description above it.
"""

# imports:

from src import geo as G, planner as P, constants as CONST


def _test_normalize_heading(heading):

    if isinstance(heading, int):

        normalized_heading = G.normalize_heading(heading)

        return normalized_heading

    else:
        raise TypeError


def _test_destination_point(start, heading, distance):

    if isinstance(heading, int):

        dest_point = G.destination_point(start, heading, distance)

        return dest_point

    else:

        raise TypeError


def _test_distance_between(start, dest, distance):

    tolerance = 1e-6

    if isinstance(start, G.Point) and isinstance(dest, G.Point):

        distance_between_start_end = G.distance_between(start, dest)

        distance_between_start = G.distance_between(start, start)

        if (
            abs(distance - distance_between_start_end) <= tolerance
            and distance_between_start == 0
        ):

            return 0

        else:

            return 1

    else:

        raise TypeError


def _test_bearing_between(start, dest, heading):

    tolerance = 1e-6

    if isinstance(start, G.Point) and isinstance(dest, G.Point):

        bearing_between_start_end = G.bearing_between(start, dest)

        if abs(heading - bearing_between_start_end) <= tolerance:

            return 0

        else:

            return 1

    else:

        raise TypeError


def _test_ground_swath_width(height=118, cross_FOV=48, off_nadir=40):

    if height <= 0 or cross_FOV <= 0 or off_nadir >= 90:

        raise ValueError

    else:

        swath_width = G.ground_swath_width_m(height, cross_FOV, off_nadir)

        return swath_width


def _test_ground_footprint_along(height=118, along_FOV=36.8, off_nadir=40):

    if height <= 0 or along_FOV <= 0 or off_nadir >= 90:

        raise ValueError

    else:

        ground_footprint = G.ground_footprint_along_m(height, along_FOV, off_nadir)

        return ground_footprint


def _test_offest_distance(swath=200, pct_overlap=30):

    if pct_overlap >= 100 or pct_overlap < 0 or swath <= 0:

        raise ValueError

    else:

        offset_d = G.offset_distance_m(swath, pct_overlap)

        return offset_d


def _test_angular_distance(heading1, heading2):

    if isinstance(heading1, int) and isinstance(heading2, int):

        angular_distance = P._angular_distance(heading1, heading2)

        return angular_distance

    else:

        raise TypeError


def _test_score_glint(heading, sun_az=0):

    if isinstance(heading, int):

        glint_score = P._score_glint(heading, sun_az)

        return glint_score

    else:

        raise TypeError


