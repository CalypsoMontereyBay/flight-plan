"""
sun.py populates the CurrentSunState object found in objects.py. Given a latitude,
longitude and datetime, it returns a populated sun state.

One sun state serves the whole mission: the aircraft's return heading is not
determined by sun azimuth, so launch and land do not need separate ones.

The helpers are written in the order of the CurrentSunState constructor's parameters.
"""

import datetime
import warnings
from contextlib import contextmanager
from zoneinfo import ZoneInfo

from pysolar.solar import get_azimuth, get_altitude

from constants import (
    V1_LAUNCH_POINT_LAT,
    V1_LAUNCH_POINT_LONG,
    V1_DEFAULT_MISSION_YEAR,
    V1_DEFAULT_MISSION_MONTH,
    V1_DEFAULT_MISSION_DAY_OF_MONTH,
    V2_DEFAULT_MISSION_LOCAL_HOUR,
    V2_MISSION_INPUT_TIMEZONE,
    V2_DEFAULT_MISSION_LOCAL_MINUTE
)
from objects import CurrentSunState


_PYSOLAR_LEAP_SECOND_WARNING = r"Leap seconds for year \d+ are not available"


@contextmanager
def _pysolar_without_leap_second_warning():
    """
    J-6 WARNING GATE -- pysolar's leap-second warning is filtered HERE, and only here.

    pysolar 0.13's leap-second table ends at 2025, so it raises
    "UserWarning: Leap seconds for year 2025 are not available" for every date after
    2026-06-30 -- which is every real mission from now on, not just the tests.

    It cannot be fixed in engine code, and it is safe to silence:
      - no leap second has been inserted since 2016-12-31, so pysolar's "no further
        adjustments" assumption is the correct one;
      - even a missed leap second is a 1 s timing error. Measured with pysolar at Terrace
        Point, 1 s moves the sun <= 0.008 deg in azimuth and <= 0.003 deg in elevation,
        against a 15 deg glint tolerance.

    The filter is scoped to the two pysolar calls below (catch_warnings restores the filters
    on exit) and matches this one message, so every other warning -- ours included -- still
    reaches the console. Revisit when pysolar ships a newer table.
    """

    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore", message=_PYSOLAR_LEAP_SECOND_WARNING, category=UserWarning, module="pysolar"
        )
        yield


def calc_azimuth(latitude, longitude, date):
    """
    Azimuth of the sun, in decimal degrees, at a coordinate and datetime. The engine
    passes the launch position and the mission datetime.

    pysolar 0.13 returns azimuth clockwise from North (0-360).
    """

    with _pysolar_without_leap_second_warning():
        launch_point_sun_az_deg = get_azimuth(latitude, longitude, date)

    return launch_point_sun_az_deg


def calc_elevation(latitude, longitude, date):
    """
    Elevation of the sun, in decimal degrees, at a coordinate and datetime. The engine
    passes the launch position and the mission datetime.
    """

    with _pysolar_without_leap_second_warning():
        launch_point_sun_elev_deg = get_altitude(latitude, longitude, date)

    return launch_point_sun_elev_deg


def calc_zenith(solar_elevation_deg):
    """
    Zenith angle of the sun, in decimal degrees. It takes only the elevation because date,
    time and coordinates are already accounted for there, so calc_elevation must run
    first (pysolar has no zenith function).
    """

    launch_point_solar_zenith_deg = 90.0 - solar_elevation_deg

    return launch_point_solar_zenith_deg


def resolve_mission_datetime(date_str: str | None = None, time_str: str | None = None):
    """
    Convert a local Pacific date and time (DST-aware) into a tz-aware UTC instant, so the
    engine is date/time aware for its weather, flight restrictions and sun data. Either
    half falls back to its V2 default when omitted or unparseable.
    """

    try:
        mission_date_component = datetime.date.fromisoformat(date_str)  # type: ignore[arg-type]

    except (ValueError, TypeError):
        mission_date_component = datetime.date(
            V1_DEFAULT_MISSION_YEAR,
            V1_DEFAULT_MISSION_MONTH,
            V1_DEFAULT_MISSION_DAY_OF_MONTH,
        )

    try:
        mission_time_component = datetime.time.fromisoformat(time_str)  # type: ignore[arg-type]

    except (ValueError, TypeError):
        mission_time_component = datetime.time(
            V2_DEFAULT_MISSION_LOCAL_HOUR,
            V2_DEFAULT_MISSION_LOCAL_MINUTE,
        )

    local_datetime = datetime.datetime.combine(mission_date_component, mission_time_component, tzinfo=ZoneInfo(V2_MISSION_INPUT_TIMEZONE))

    return local_datetime.astimezone(datetime.timezone.utc)


# Module-level default instant, used when no CLI date/time is supplied: the V2
# local-time defaults resolved to UTC. create_sun_state and planner fall back to
# this so a plan can still be built with no --date/--time chosen.
mission_datetime = resolve_mission_datetime()


def create_sun_state(
    latitude=V1_LAUNCH_POINT_LAT, longitude=V1_LAUNCH_POINT_LONG, date=mission_datetime
):
    """
    Populate and return a CurrentSunState from the helpers above. Latitude, longitude and
    date default to the launch point and the V2 default mission datetime.
    """

    # calculating launch point azimuth for object
    current_launch_point_az_deg = calc_azimuth(latitude, longitude, date)

    # calculating launch point elevation for object
    current_launch_point_elev_deg = calc_elevation(latitude, longitude, date)

    # calculating launch point zenith for object
    current_launch_point_zen_deg = calc_zenith(current_launch_point_elev_deg)

    launch_sun_state = CurrentSunState(
        current_launch_point_az_deg,
        current_launch_point_elev_deg,
        current_launch_point_zen_deg,
        date.day,
        date.hour,
        date.minute,
    )

    return launch_sun_state
