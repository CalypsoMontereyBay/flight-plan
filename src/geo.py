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
'''

import math

from pyproj import Geod
from shapely.geometry import Point, LineString


WGS84_GEOD = Geod(ellps="WGS84")
FULL_CIRCLE_DEG = 360


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
    return heading_deg % FULL_CIRCLE_DEG


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

def ground_swath_width_m(altitude_m, cross_track_fov_deg, off_nadir_deg=40):
    '''
    Compute cross-track ground footprint width for an off-nadir camera.

    Cross-track only. Along-track FOV is orthogonal and handled separately
    by ground_footprint_along_m; it does not affect swath width or grid
    spacing.

    Formula:
        h * (tan(theta + fov / 2) - tan(theta - fov / 2))
    '''
    if altitude_m <= 0:
        raise ValueError("altitude_m must be positive")
    if cross_track_fov_deg <= 0:
        raise ValueError("cross_track_fov_deg must be positive")

    lower_angle_deg = off_nadir_deg - (cross_track_fov_deg / 2)
    upper_angle_deg = off_nadir_deg + (cross_track_fov_deg / 2)

    if lower_angle_deg <= -90 or upper_angle_deg >= 90:
        raise ValueError("FOV and off-nadir angle must stay within +/- 90 degrees")

    lower_angle_rad = math.radians(lower_angle_deg)
    upper_angle_rad = math.radians(upper_angle_deg)
    return altitude_m * (math.tan(upper_angle_rad) - math.tan(lower_angle_rad))


def ground_footprint_along_m(altitude_m, along_track_fov_deg, off_nadir_deg=0):
    '''
    Compute the along-track ground footprint length for a camera that may be
    cross-track-rolled by off_nadir_deg (V1's camera rolls sideways for glint
    avoidance, not pitched forward/back).

    A tilted camera sees a longer along-track patch because the ground is
    further away on the slant: slant_range = h / cos(off_nadir).

    Formula:
        2 * (h / cos(off_nadir)) * tan(fov_along / 2)
    '''
    if altitude_m <= 0:
        raise ValueError("altitude_m must be positive")
    if along_track_fov_deg <= 0:
        raise ValueError("along_track_fov_deg must be positive")
    if abs(off_nadir_deg) >= 90:
        raise ValueError("off_nadir_deg must satisfy |off_nadir| < 90 degrees")

    slant_range_m = altitude_m / math.cos(math.radians(off_nadir_deg))
    half_fov_rad = math.radians(along_track_fov_deg / 2)
    return 2 * slant_range_m * math.tan(half_fov_rad)


def offset_distance_m(swath_width_m, desired_overlap_pct):
    '''
    Convert swath width and desired overlap into line-to-line offset distance.
    '''
    if swath_width_m <= 0:
        raise ValueError("swath_width_m must be positive")
    if desired_overlap_pct < 0 or desired_overlap_pct >= 100:
        raise ValueError("desired_overlap_pct must satisfy 0 <= overlap < 100")

    return swath_width_m * (1 - (desired_overlap_pct / 100))


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


def calculate_total_lines(usable_distance_m, line_length_m):
    '''
    Calculate the largest even line count that fits the distance budget.
    '''
    if usable_distance_m <= 0:
        raise ValueError("usable_distance_m must be positive")
    if line_length_m <= 0:
        raise ValueError("line_length_m must be positive")

    total_lines = math.floor(usable_distance_m / line_length_m)
    if total_lines % 2 != 0:
        total_lines -= 1

    return max(0, total_lines)


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
    return LineString([(start.x, start.y), (center.x, center.y), (end.x, end.y)])


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


def _build_centered_grid(center_point, grid_orientation_deg, offset_m, total_lines):
    line_length_m = calculate_line_length_m(offset_m, total_lines)
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
    # so M1 is always the middle coord of that line -> +1 within its 3-point block.
    center_line_index = total_lines // 2
    m1_route_index = center_line_index * 3 + 1

    return flight_lines, route_points, m1_route_index


def make_lawnmower_grid_through_m1(center_point, grid_orientation_deg, usable_distance_m,
                                   altitude_m, cross_track_fov_deg,
                                   desired_overlap_pct, off_nadir_deg=40):
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

    # ------------------------------------------------------------------
    # SCIENCE / TRANSIT OFFSET CORRECTION  (documented, NOT yet active)
    # ------------------------------------------------------------------
    # PROBLEM:
    #   The live offset_m above is sized as the line-to-line spacing
    #   assuming EVERY adjacent line collects science -- a copter-style
    #   bidirectional lawnmower. The fixed-wing BlackSwift has no yaw
    #   axis to de-rotate the camera, so only the legs flown at the
    #   science heading H collect data; the return legs at H+180 are
    #   transit (camera off, wrong glint direction).
    #
    #   In the serpentine built by _build_centered_grid, even-indexed
    #   lines are flown at H (science) and odd-indexed lines at H+180
    #   (transit). So the SCIENCE lines are really spaced 2 * offset_m
    #   apart, not offset_m. Two consequences:
    #     1. The science swaths do not abut at the intended overlap --
    #        they leave cross-track gaps (under-sampled ocean).
    #     2. metrics["science_lines"] = total_lines overcounts the real
    #        science lines by roughly 2x.
    #
    # FIX:
    #   Treat the swath/overlap result as the desired SCIENCE-line
    #   spacing, then halve it to get the physical line spacing, so the
    #   interleaved transit line falls exactly between two science lines.
    #
    #   science_offset_m = offset_distance_m(swath_width_m, desired_overlap_pct)
    #   line_offset_m    = science_offset_m / 2
    #   offset_m         = line_offset_m   # physical spacing fed to the grid
    #
    # METRICS that must change with the fix (total_lines is odd):
    #   science_lines = (total_lines + 1) // 2   # even-indexed, flown at H
    #   transit_lines =  total_lines // 2        # odd-indexed, flown at H+180
    #   offset_lines  =  total_lines - 1
    #   grid_area_m2  =  science area. With the halved offset the science
    #                    swaths close their gaps, so the bounding-square
    #                    area equals true science coverage again -- but for
    #                    the SAME total_lines the grid is now half the
    #                    linear size (a quarter of the area), OR you need
    #                    ~2x the lines (and ~2x the route distance, since
    #                    half is transit) to cover the same area.
    #
    # DOWNSTREAM EFFECT:
    #   For a fixed endurance budget the honest achievable science area
    #   roughly halves versus the current optimistic model, because ~50%
    #   of the flight distance is non-collecting transit. Activate this
    #   block only once planner/outputs report science vs transit lines
    #   separately and the area-based ranking expects true science area.
    # ------------------------------------------------------------------

    total_lines = _initial_total_lines_from_budget(usable_distance_m, offset_m)

    while total_lines >= 3:
        flight_lines, route_points, m1_route_index = _build_centered_grid(
            center_point,
            grid_orientation_deg,
            offset_m,
            total_lines,
        )
        total_route_distance_m = _route_distance_m(route_points)

        if total_route_distance_m <= usable_distance_m:
            line_length_m = calculate_line_length_m(offset_m, total_lines)
            metrics = {
                "total_route_distance_m": total_route_distance_m,
                "usable_endurance_distance_m": usable_distance_m,
                "grid_area_m2": calculate_grid_area_m2(offset_m, total_lines),
                "offset_distance_m": offset_m,
                "line_length_m": line_length_m,
                "total_lines": total_lines,
                "science_lines": total_lines,
                "traverse_lines": total_lines - 1,
                "offset_lines": total_lines - 1,
                "m1_route_index": m1_route_index,
            }
            return flight_lines, route_points, metrics

        total_lines -= 2  # preserve odd parity

    raise ValueError("Usable endurance distance is too small for a V1 grid")
