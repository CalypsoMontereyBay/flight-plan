'''
Geographic math for Engine V1.

geo.py owns spatial calculations only: bearings, destination points, line
offsets, grid sizing, grid area, and M1-centered lawnmower geometry. It does
not create CandidatePlan objects, estimate battery, validate legality, or
write output files.

FOV note: cross-track and along-track FOV are orthogonal.
  * Cross-track FOV  -> ground swath width  -> line-to-line offset / grid
                        spacing. Drives the lawnmower lattice.
  * Along-track FOV  -> instantaneous ground footprint length in the flight
                        direction. Relevant to image trigger rate and to the
                        "free" coverage you get past each line endpoint. V1
                        does not consume this for routing; the helper is here
                        for reporting and for future trigger-rate logic.

MOUNTING NOTE (V2C.1) -- READ BEFORE TOUCHING THE FOV MATH:
The camera is mounted ALONG-track (pitched forward under the nose, 30 deg
off-nadir). It used to be mounted CROSS-track (rolled sideways, 40 deg).

Only ONE axis is ever tilted, and the tilt decides which formula each axis uses:
  * tilted axis   -> h * (tan(th + fov/2) - tan(th - fov/2))   asymmetric stretch
  * untilted axis -> 2 * (h / cos(th)) * tan(fov/2)            symmetric, slant range

When the mount rotated, the tilt moved from cross-track to along-track, so
ground_swath_width_m and ground_footprint_along_m SWAPPED formula bodies. That
swap looks like a bug in git blame; it is not. Two consequences worth knowing:
the cross-track swath is now centred on the ground track (it used to sit entirely
off to one side, so the M1 overflight imaged nothing), and both leg directions now
collect science, which is why science_lines == total_lines below.
'''

import constants as CONST

import math

from pyproj import Geod
from shapely.geometry import Point, LineString


WGS84_GEOD = Geod(ellps="WGS84")


def _as_point(point):
    if isinstance(point, Point):
        return point
    if hasattr(point, "point"):
        return point.point
    raise TypeError("Expected a Shapely Point or an object with a .point property")


def normalize_heading(heading_deg):
    '''
    Normalize heading into 0 <= heading < 360 degrees.
    '''
    if not isinstance(heading_deg, (int, float)):
        raise TypeError("heading_deg must be an int or float")
    return heading_deg % CONST.FULL_CIRCLE_DEG


def destination_point(start_point, heading_deg, distance_m):
    '''
    Move from a start point along a heading for distance_m meters.
    '''
    start = _as_point(start_point)
    heading = normalize_heading(heading_deg)
    new_lon, new_lat, _ = WGS84_GEOD.fwd(start.x, start.y, heading, distance_m)
    return Point(new_lon, new_lat)


def bearing_between(point_a, point_b):
    '''
    Return the forward bearing from point_a to point_b in degrees.
    '''
    start = _as_point(point_a)
    end = _as_point(point_b)
    forward_azimuth, _, _ = WGS84_GEOD.inv(start.x, start.y, end.x, end.y)
    return normalize_heading(forward_azimuth)


def distance_between(point_a, point_b):
    '''
    Return geodesic distance between two points in meters.
    '''
    start = _as_point(point_a)
    end = _as_point(point_b)
    _, _, distance_m = WGS84_GEOD.inv(start.x, start.y, end.x, end.y)
    return abs(distance_m)

def ground_swath_width_m(altitude_m, cross_track_fov_deg, off_nadir_deg):
    '''
    Computes the CROSS-TRACK GSW in meters, with the new formula for V2C.1 below.

    V2C MOUNT CHANGE: the camera is now pitched ALONG-track, so cross-track is no
    longer the tilted axis. Cross-track the camera just looks down a longer slant
    range (h / cos(off-nadir)) with no tilt stretch, so this is a plain symmetric
    FOV projection. The old tan-difference form moved to ground_footprint_along_m,
    which is now the tilted axis.

    Formula:
        2 * ( (h/cos(off-nadir)) * tan(cross_fov/2))
    '''
    if altitude_m <= 0:
        raise ValueError("altitude_m must be positive")
    if cross_track_fov_deg <= 0:
        raise ValueError("cross_track_fov_deg must be positive")
    if abs(off_nadir_deg) >= CONST.DEGREE_NINETY:
        raise ValueError("off-nadir angle must stay within +/- 90 degrees")

    half_fov_rad = math.radians(cross_track_fov_deg / 2)
    slant_range_m = altitude_m / math.cos(math.radians(off_nadir_deg))

    return 2 * (slant_range_m * math.tan(half_fov_rad))


def ground_footprint_along_m(altitude_m, along_track_fov_deg, off_nadir_deg):
    '''
    Compute the along-track ground footprint length.

    V2C MOUNT CHANGE: the camera is pitched forward ALONG-track, so along-track is
    now the TILTED axis. The tilt stretches the far edge of the footprint and
    compresses the near edge -- that asymmetry is exactly what the tan-difference
    form below captures. Before the remount this axis was untilted and used the
    slant form, which now lives in ground_swath_width_m.

    Reporting only: nothing in the routing path consumes this. It matters for
    image trigger rate.

    Formula:
        h * (tan(off-nadir + (along_fov/2)) - tan(off-nadir - (along_fov/2)))
    '''
    if altitude_m <= 0:
        raise ValueError("altitude_m must be positive")
    if along_track_fov_deg <= 0:
        raise ValueError("along_track_fov_deg must be positive")
    if abs(off_nadir_deg) >= CONST.DEGREE_NINETY:
        raise ValueError("off_nadir_deg must satisfy |off_nadir| < 90 degrees")

    lower_angle_deg = off_nadir_deg - (along_track_fov_deg / 2)
    upper_angle_deg = off_nadir_deg + (along_track_fov_deg / 2)

    # The tan-difference form diverges as an FOV edge approaches the horizon. This
    # guard travelled here WITH the formula -- it used to live in ground_swath_width_m
    # and it protects the tilted axis, whichever axis that currently is.
    if lower_angle_deg <= -CONST.DEGREE_NINETY or upper_angle_deg >= CONST.DEGREE_NINETY:
        raise ValueError("FOV and off-nadir angle must stay within +/- 90 degrees")

    lower_angle_rads = math.radians(lower_angle_deg)
    upper_angle_rads = math.radians(upper_angle_deg)

    return altitude_m * (math.tan(upper_angle_rads) - math.tan(lower_angle_rads))


def offset_distance_m(swath_width_m, desired_overlap_pct):
    '''
    Convert swath width and desired overlap into line-to-line offset distance.
    '''
    if swath_width_m <= 0:
        raise ValueError("swath_width_m must be positive")
    if desired_overlap_pct < 0 or desired_overlap_pct >= 100:
        raise ValueError("desired_overlap_pct must satisfy 0 <= overlap < 100")

    return swath_width_m * (1 - (desired_overlap_pct / 100))

def sensor_parallax_m(altitude_m, off_nadir_deg):

    """
    Along-track distance between the point the aircraft is OVER (nadir) and the point
    the camera is LOOKING AT (boresight ground intercept).

    Because the strip is displaced forward by this amount, the same distance at the
    near end of each line goes un-imaged -- ~8% of a line at the current altitude.
    **NOTE** NOT used in any corrections as of V2C.1, just simple reporting.

    formula: parallax = h * tan(θ)
    """

    if altitude_m <= 0:
        raise ValueError ("Altitude must be positive!")
    elif abs(off_nadir_deg) >= CONST.DEGREE_NINETY:
        raise ValueError ("Viewing angle must be < 90.")
    else:
        return (altitude_m * math.tan(math.radians(off_nadir_deg)))
    
    
def furthest_point_distance_m (reference_point, points: list):
    '''
    Distance from reference_point to whichever of `points` lies furthest from it, plus
    that point itself.

    The RTH gate needs the worst case: if the aircraft can reach home from the furthest
    point on the route, it can reach home from any of them. The point is returned as well
    so the caller can take bearing_between(point, reference_point) without searching twice.

    Max over ALL route points rather than the four grid corners. For a convex rectangle
    those are equivalent, but this form is trivially correct and survives any future
    non-rectangular grid.
    '''
    if len(points) == 0 :
        raise ValueError ("List of Points is empty, expected non-zero.")

    # Every distance is measured FROM reference_point -- the landing waypoint. Measuring
    # between route points instead answers a different (and much smaller) question: the
    # grid's own diagonal rather than how far from home its far corner sits.
    furthest_point = points[0]
    max_dist_m = distance_between(reference_point, furthest_point)

    for point in points:

        distance_m = distance_between(reference_point, point)

        if distance_m > max_dist_m:

            max_dist_m = distance_m
            furthest_point = point

    return (max_dist_m, furthest_point)


def calculate_line_length_m(offset_m, total_lines):
    '''
    Calculate square-grid side length for V1.
    '''
    if offset_m <= 0:
        raise ValueError("offset_m must be positive")
    if total_lines < 2:
        raise ValueError("total_lines must be at least 2")

    return offset_m * (total_lines - 1)


def calculate_grid_area_m2(offset_m, total_lines):
    '''
    Calculate V1 grid area using (offset * (N - 1)) ** 2.
    '''
    line_length_m = calculate_line_length_m(offset_m, total_lines)
    return line_length_m ** 2

def make_line_through_point(center_point, grid_orientation_deg, line_length_m):
    '''
    Create a LineString centered on center_point and aligned to grid_orientation_deg.
    '''
    center = _as_point(center_point)
    if line_length_m <= 0:
        raise ValueError("line_length_m must be positive")

    half_length_m = line_length_m / 2
    start = destination_point(center, normalize_heading(grid_orientation_deg + 180), half_length_m)
    end = destination_point(center, grid_orientation_deg, half_length_m)
    
    if half_length_m > CONST.V1_COLLECTION_INSET_m:
        collect_start = destination_point(center, normalize_heading(grid_orientation_deg + 180), half_length_m - CONST.V1_COLLECTION_INSET_m)
        collect_end = destination_point(center, grid_orientation_deg, half_length_m - CONST.V1_COLLECTION_INSET_m)
    
    else:
        #For a tiny grid, just place the collection points halfway between the middle and the turns. 
        collect_start = destination_point(center, normalize_heading(grid_orientation_deg + 180), half_length_m / 2 )
        collect_end = destination_point(center, grid_orientation_deg, half_length_m  / 2)
        
    return LineString([(start.x, start.y), (collect_start.x, collect_start.y), (center.x, center.y), (collect_end.x, collect_end.y), (end.x, end.y)])


def offset_line(line, offset_heading_deg, offset_m):
    '''
    Offset every coordinate in a LineString by offset_m along offset_heading_deg.
    '''
    if offset_m < 0:
        raise ValueError("offset_m cannot be negative")

    offset_points = []
    for lon, lat in line.coords:
        offset_points.append(destination_point(Point(lon, lat), offset_heading_deg, offset_m))

    return LineString([(point.x, point.y) for point in offset_points])


def _route_distance_m(route_points):
    total_distance_m = 0
    for i in range(1, len(route_points)):
        total_distance_m += distance_between(route_points[i - 1], route_points[i])
    return total_distance_m


def _initial_total_lines_from_budget(usable_distance_m, offset_m):
    if usable_distance_m <= 0:
        raise ValueError("usable_distance_m must be positive")
    if offset_m <= 0:
        raise ValueError("offset_m must be positive")

    # Solve N * offset * (N - 1) <= usable_distance as a conservative first estimate.
    total_lines = math.floor((1 + math.sqrt(1 + (4 * usable_distance_m / offset_m))) / 2)
    # V1 forces odd N so the center line passes through M1 -> free overflight, no detour.
    if total_lines % 2 == 0:
        total_lines -= 1

    return max(3, total_lines)


def _build_centered_grid(center_point, grid_orientation_deg, offset_m, total_lines, line_extension_m=0):
    line_length_m = (calculate_line_length_m(offset_m, total_lines) + line_extension_m)
    center_line = make_line_through_point(center_point, grid_orientation_deg, line_length_m)
    perpendicular_heading = normalize_heading(grid_orientation_deg + 90)
    opposite_perpendicular_heading = normalize_heading(grid_orientation_deg - 90)

    line_offsets = [
        (i - ((total_lines - 1) / 2)) * offset_m
        for i in range(total_lines)
    ]

    flight_lines = []
    for line_offset_m in line_offsets:
        if line_offset_m >= 0:
            flight_lines.append(offset_line(center_line, perpendicular_heading, line_offset_m))
        else:
            flight_lines.append(offset_line(center_line, opposite_perpendicular_heading, abs(line_offset_m)))

    route_points = []
    for line_index, line in enumerate(flight_lines):
        line_points = [Point(lon, lat) for lon, lat in line.coords]
        if line_index % 2 != 0:
            line_points.reverse()
        route_points.extend(line_points)

    # With odd total_lines the center line (index total_lines // 2) sits at offset 0
    # and passes through M1. make_line_through_point emits [start, midpoint, end],
    # so M1 is always the middle coord of that line -> +1 within its 5-point block.
    center_line_index = total_lines // 2
    m1_route_index = ((center_line_index * CONST.V1_POINTS_PER_LINE) + (CONST.V1_POINTS_PER_LINE // 2))

    return flight_lines, route_points, m1_route_index


def make_lawnmower_grid_through_m1(center_point, grid_orientation_deg, usable_distance_m,
                                   altitude_m, cross_track_fov_deg,
                                   desired_overlap_pct, off_nadir_deg):
    '''
    Build the largest V1 M1-centered lawnmower grid that fits usable_distance_m.

    V1 uses an odd total_lines so the center line passes directly through M1; the
    M1 overflight is then a natural waypoint at route_points[metrics["m1_route_index"]]
    and adds zero detour distance.

    Returns:
        flight_lines, route_points, metrics
    '''
    swath_width_m = ground_swath_width_m(
        altitude_m,
        cross_track_fov_deg,
        off_nadir_deg,
    )
    offset_m = offset_distance_m(swath_width_m, desired_overlap_pct)


    total_lines = _initial_total_lines_from_budget(usable_distance_m, offset_m)

    # Depends only on altitude + viewing angle, so it is constant across the shrink
    # loop below -- compute once, outside.
    parallax_m = sensor_parallax_m(altitude_m, off_nadir_deg)
    
    #Calculates the along-track spacing:
    #FORMULA: (Along_track footprint distance (meters)) * (1 - along-track overlap/100)
    camera_trigger_distance_m = ((ground_footprint_along_m(altitude_m, CONST.V1_DEFAULT_SENSOR_ALONG_TRACK_FOV_DEG, off_nadir_deg)) * (1 - (CONST.V2_DEFAULT_ALONGTRACK_OVERLAP_PCT/100)))
    
    extension_m = ((parallax_m + CONST.V1_COLLECTION_INSET_m) * 2)

    while total_lines >= 3:
        flight_lines, route_points, m1_route_index = _build_centered_grid(
            center_point,
            grid_orientation_deg,
            offset_m,
            total_lines,
            line_extension_m=extension_m
        )
        total_grid_distance_m = _route_distance_m(route_points)

        if total_grid_distance_m <= usable_distance_m:
            line_length_m = calculate_line_length_m(offset_m, total_lines)
            metrics = {
                "total_grid_distance_m": total_grid_distance_m,
                "usable_endurance_distance_m": usable_distance_m,
                "grid_area_m2": calculate_grid_area_m2(offset_m, total_lines),
                "offset_distance_m": offset_m,
                # TWO lengths, because they answer different questions and are no longer
                # the same number. line_length_m is the SCIENCE length -- the intended
                # coverage, and what grid_area_m2 is built from, so reported area stays
                # true coverage. physical_line_length_m is what actually gets FLOWN,
                # extended so the imaged strip covers that science box instead of sitting
                # forward of it. Feeding the physical length into area would overstate
                # coverage; feeding the science length into route distance would
                # understate the flight.
                "line_length_m": line_length_m,
                "physical_line_length_m": line_length_m + extension_m,
                "line_extension_m": extension_m,
                "total_lines": total_lines,
                "science_lines": total_lines,
                "traverse_lines": 0,
                "offset_lines": total_lines - 1,
                "m1_route_index": m1_route_index,
                "cross_track_swath_m": swath_width_m,
                "sensor_parallax_m": parallax_m,
                "camera_trigger_distance_m": camera_trigger_distance_m
            }
            return flight_lines, route_points, metrics

        total_lines -= 2  # preserve odd parity

    raise ValueError("Usable endurance distance is too small for a V1 grid")
