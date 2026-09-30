"""
Tier 5 -- rendering invariants.

Top of the cake: depends on everything below. Two halves:

  1. KML/PNG. The delimiter segment builder turns the classified route into full science
     legs (not stubs) with clean boundaries. The aliasing assert specifically guards the
     flush bug we fixed (segments must not share a mutable list object).
  2. QGC .plan (J-7), the file the aircraft would actually fly. Every expected MAVLink value
     is a literal from the MAVLink spec or is read out of one of the repo's three files that
     QGC wrote: exp2.plan and exp..plan, QGC's own exports, and roundtrip_qgc.plan, our
     default plan after a QGC load and save. None comes from constants.py: a test that read
     the QGC constants back would pass on the very typo it exists to catch.
"""

import copy
import json
import math
from pathlib import Path

import pytest

import constants as CONST
import flight_plan_maker
import objects as OBJ
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


"""
============================================================================
==           QGC .plan (J-7) -- the machine-consumed output               ==
============================================================================
"""

# MAV_CMD and MAV_TYPE values from the MAVLink common message set
# (https://mavlink.io/en/messages/common.html). Literals on purpose: these tests check
# constants.py against the standard, so they must not read constants.py.
MAV_CMD_NAV_WAYPOINT = 16
MAV_CMD_NAV_LAND = 21
MAV_CMD_NAV_TAKEOFF = 22
MAV_CMD_NAV_VTOL_TAKEOFF = 84
MAV_CMD_NAV_VTOL_LAND = 85
MAV_CMD_DO_CHANGE_SPEED = 178
MAV_CMD_DO_SET_CAM_TRIGG_DIST = 206

MAV_TYPE_QUADROTOR = 2
MAV_TYPE_VTOL_FIXEDROTOR = 22

CAMERA_KEYWORDS = ("cam_on", "cam_off")

REPO_ROOT = Path(__file__).parent.parent


def _reference_plan(filename):
    with open(REPO_ROOT / filename, encoding="utf-8") as reference:
        return json.load(reference)


def _reference_item(reference_plan, command):
    # the first SimpleItem in a QGC export that carries this MAV_CMD
    return next(
        item for item in reference_plan["mission"]["items"]
        if item["type"] == "SimpleItem" and item["command"] == command
    )


def _default_plan():
    return P.plan_default_mission("t5_plan")


def _vehicle(vehicle_type, hover_speed_ms=0):
    # The S2's performance under a different MAVLink identity. The planner never branches on
    # vehicle class, so only the writer's output should change.
    return OBJ.Vehicle(
        CONST.BLACKSWIFT_ENDURANCE_min,
        CONST.BLACKSWIFT_WIND_RATING_ms,
        CONST.BLACKSWIFT_CLIMB_RATE_ms,
        CONST.BLACKSWIFT_DESCENT_RATE_ms,
        CONST.BLACKSWIFT_TURN_RADIUS_m,
        CONST.BLACKSWIFT_TURN_PENALTY_s,
        CONST.BLACKSWIFT_MIN_GROUND_SPEED_ms,
        CONST.BLACKSWIFT_CRUISE_SPEED_ms,
        vehicle_type,
        CONST.BLACKSWIFT_FIRMWARE_TYPE,
        hover_speed_ms=hover_speed_ms
    )


def _plan_built_with(aircraft=None, mission_request=None):
    # The default mission with the aircraft or the mission request swapped out, through the
    # same build_candidate_plan the entry point uses.
    sun_state, default_request, weather_state, sun_az = P._build_dated_objects(
        P.DEFAULT_MISSION_DATETIME
    )
    return P.build_candidate_plan(
        mission_aircraft=aircraft or P._Black_Swift,
        mission_aircraft_endurance_m=P._Black_Swift_usable_endurance_m,
        payload=P._Calypso_payload,
        mission_request=mission_request or default_request,
        mission_weather=weather_state,
        mission_azimuth=sun_az,
        mission_sun_state=sun_state,
        candidate_name="t5_variant"
    )


def _boat_plan():
    # Launch and land on the same boat, ~2 km north of M1: the Tier 3 boat geometry.
    pad_lat = CONST.M1_MOORING_LAT + 0.018
    pad_long = CONST.M1_MOORING_LONG

    launch = OBJ.Waypoint(
        "WP000", pad_lat, pad_long,
        CONST.V1_DEFAULT_AIRCRAFT_ALTITUDE_m, CONST.BLACKSWIFT_CRUISE_SPEED_ms,
        CONST.WAYPOINT_ACTION_LAUNCH, "launch", "Test-Boat-Launch",
    )
    land = OBJ.Waypoint(
        "WP_END", pad_lat, pad_long,
        CONST.V1_DEFAULT_LAND_ALTITUDE_m, CONST.BLACKSWIFT_CRUISE_SPEED_ms,
        CONST.WAYPOINT_ACTION_LAND, "land", "Test-Boat-Land",
    )
    boat_request = OBJ.MissionRequest(
        mission_name="boat launch",
        launch_waypoint=launch,
        land_waypoint=land,
        m1_waypoint=P._M1_Waypoint,
        altitude_m=CONST.V1_DEFAULT_AIRCRAFT_ALTITUDE_m,
        valid_time=P.DEFAULT_MISSION_DATETIME,
        require_m1_overflight=True,
        grid_orientation_deg=None,
        notes="boat launch",
        included_target_waypoints=[P._M1_Waypoint],
    )
    return _plan_built_with(mission_request=boat_request)


def _serialized(plan):
    # (neutral items, QGC document). Items and document items share an order, so zipping
    # them pairs each QGC item with the neutral item it was built from.
    items = OUT._plan_items(plan)
    return items, OUT._serialize_qgc(plan, items)


def _numbers_in(node):
    # every int/float anywhere in a JSON document; bools and nulls are not numbers here
    if isinstance(node, dict):
        for value in node.values():
            yield from _numbers_in(value)
    elif isinstance(node, list):
        for value in node:
            yield from _numbers_in(value)
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        yield node


def _reject_non_json(token):
    raise ValueError(f"{token} is not valid JSON")


def _camera_item_shape(qgc_item):
    # a camera item minus its position in the file and its trigger distance
    return {
        key: (value[1:] if key == "params" else value)
        for key, value in qgc_item.items() if key != "doJumpId"
    }


def test_plan_aircraft_is_a_vehicle():
    # The writer branches on four Vehicle fields. J-2 built the class and it went unused for
    # three steps, because no test looked. This one looks.
    assert isinstance(_default_plan().aircraft, OBJ.Vehicle)


def test_item_count_and_order():
    # A waypoint becomes one item, except collect_start and collect_stop, which each add a
    # camera item: 5N nav + 2N camera + takeoff + land = 7N + 2. Asserted in N, never as 65,
    # so a Step F grid-size change passes straight through.
    plan = _default_plan()
    items, doc = _serialized(plan)
    qgc_items = doc["mission"]["items"]
    n = plan.total_lines
    assert n is not None

    assert len(items) == len(qgc_items) == CONST.V1_POINTS_PER_LINE * n + 2 * n + 2
    assert len(items) == len(plan.waypoints) + 2 * n

    keywords = [item["Keyword"] for item in items]
    assert keywords.count("nav") == CONST.V1_POINTS_PER_LINE * n
    assert keywords.count("cam_on") == keywords.count("cam_off") == n
    assert keywords[0] == "takeoff" and keywords.count("takeoff") == 1
    assert keywords[-1] == "land" and keywords.count("land") == 1


def test_do_jump_ids_are_contiguous_from_one():
    # doJumpId is position in THIS file, assigned while serializing. It must never be taken
    # from waypoint_ID, which stops lining up after the first camera item.
    _, doc = _serialized(_default_plan())
    jump_ids = [item["doJumpId"] for item in doc["mission"]["items"]]
    assert jump_ids == list(range(1, len(jump_ids) + 1))


def test_commands_follow_the_mavlink_spec():
    # A misplaced bracket in the _QGC_COMMAND lookup once crashed on the first item; a wrong
    # integer in the QGC constants would write silently. Both fail here.
    expected = {
        "takeoff": MAV_CMD_NAV_TAKEOFF,
        "nav": MAV_CMD_NAV_WAYPOINT,
        "cam_on": MAV_CMD_DO_SET_CAM_TRIGG_DIST,
        "cam_off": MAV_CMD_DO_SET_CAM_TRIGG_DIST,
        "land": MAV_CMD_NAV_LAND,
    }
    items, doc = _serialized(_default_plan())
    for item, qgc_item in zip(items, doc["mission"]["items"]):
        assert qgc_item["command"] == expected[item["Keyword"]]


def test_frames_match_qgcs_own_exports():
    # The J-5 audit found _QGC_ALT_FRAME's AMSL and MISSION rows swapped: every cruise
    # waypoint in the mission frame, and the file still wrote without an error. The expected
    # frame and AltitudeMode for each class of item come from QGC's own files.
    exp2 = _reference_plan("exp2.plan")
    takeoff_ref = _reference_item(exp2, MAV_CMD_NAV_TAKEOFF)
    cruise_ref = _reference_item(exp2, MAV_CMD_NAV_WAYPOINT)
    do_ref = _reference_item(_reference_plan("exp..plan"), MAV_CMD_DO_CHANGE_SPEED)

    # exp2.plan lands with a fwLandingPattern rather than a NAV_LAND. Its altitudes are
    # relative, which is why our NAV_LAND shares the takeoff's relative frame.
    landing_pattern = next(
        item for item in exp2["mission"]["items"]
        if item.get("complexItemType") == "fwLandingPattern"
    )
    assert landing_pattern["altitudesAreRelative"] is True

    relative = (takeoff_ref["frame"], takeoff_ref["AltitudeMode"])
    expected = {
        "takeoff": relative,
        "land": relative,
        "nav": (cruise_ref["frame"], cruise_ref["AltitudeMode"]),
        "cam_on": (do_ref["frame"], None),
        "cam_off": (do_ref["frame"], None),
    }
    items, doc = _serialized(_default_plan())
    for item, qgc_item in zip(items, doc["mission"]["items"]):
        assert (qgc_item["frame"], qgc_item.get("AltitudeMode")) == expected[item["Keyword"]]


def test_key_sets_match_qgcs_own_exports():
    # Top-level, header and positional-item keys as exp2.plan writes them. Camera items are
    # DO items, so their keys come from exp..plan's DO_CHANGE_SPEED, which carries none of
    # the three altitude keys.
    exp2 = _reference_plan("exp2.plan")
    cruise_ref = _reference_item(exp2, MAV_CMD_NAV_WAYPOINT)
    do_ref = _reference_item(_reference_plan("exp..plan"), MAV_CMD_DO_CHANGE_SPEED)

    items, doc = _serialized(_default_plan())
    assert set(doc) == set(exp2)
    assert set(doc["mission"]) == set(exp2["mission"])

    for item, qgc_item in zip(items, doc["mission"]["items"]):
        reference = do_ref if item["Keyword"] in CAMERA_KEYWORDS else cruise_ref
        assert set(qgc_item) == set(reference)


def test_nulls_match_qgcs_own_export():
    # QGC writes AMSLAltAboveTerrain as null (no terrain data) and cruise yaw as null (no
    # commanded nose direction). A number in either would be a fabricated altitude or a
    # commanded yaw.
    cruise_ref = _reference_item(_reference_plan("exp2.plan"), MAV_CMD_NAV_WAYPOINT)
    assert cruise_ref["AMSLAltAboveTerrain"] is None
    assert cruise_ref["params"][3] is None

    items, doc = _serialized(_default_plan())
    for item, qgc_item in zip(items, doc["mission"]["items"]):
        if item["Keyword"] in CAMERA_KEYWORDS:
            continue
        assert qgc_item["AMSLAltAboveTerrain"] is None
        if item["Keyword"] == "nav":
            assert qgc_item["params"][3] is None


def test_header_matches_the_vehicle_and_qgcs_export():
    # The vehicle fields come from the plan's own Vehicle. The fixed fields are what QGC
    # writes, including globalPlanAltitudeMode 0 (mixed), because takeoff and land are
    # relative while cruise is AMSL.
    exp2 = _reference_plan("exp2.plan")
    plan = _default_plan()
    aircraft = plan.aircraft
    assert isinstance(aircraft, OBJ.Vehicle)

    _, doc = _serialized(plan)
    mission = doc["mission"]
    assert mission["vehicleType"] == aircraft.vehicle_type
    assert mission["firmwareType"] == aircraft.firmware_type
    assert mission["cruiseSpeed"] == aircraft.vehicle_cruise_speed
    assert mission["hoverSpeed"] == aircraft.hover_speed_ms

    assert mission["globalPlanAltitudeMode"] == exp2["mission"]["globalPlanAltitudeMode"]
    assert mission["version"] == exp2["mission"]["version"]
    for key in ("fileType", "groundStation", "version", "geoFence", "rallyPoints"):
        assert doc[key] == exp2[key]


def test_camera_toggles_pair_and_follow_their_nav():
    # One on/off pair per science line, alternating, starting on and ending off, so the file
    # never ends still triggering. Each camera item sits directly after the nav item of the
    # waypoint that caused it.
    plan = _default_plan()
    items, _ = _serialized(plan)
    keywords = [item["Keyword"] for item in items]

    assert plan.science_lines is not None
    assert [k for k in keywords if k in CAMERA_KEYWORDS] == ["cam_on", "cam_off"] * plan.science_lines

    caused_by = {
        "cam_on": CONST.WAYPOINT_ACTION_COLLECT_START,
        "cam_off": CONST.WAYPOINT_ACTION_COLLECT_STOP,
    }
    for index, item in enumerate(items):
        if item["Keyword"] in CAMERA_KEYWORDS:
            previous = items[index - 1]
            assert previous["Keyword"] == "nav"
            assert previous["Source_Action"] == item["Source_Action"] == caused_by[item["Keyword"]]


def test_trigger_distance_comes_from_the_plan():
    # Pins the metrics path end to end (geo -> metrics -> plan -> file). The distance is the
    # plan's live value, not the 280.74 snapshot in constants.py. Distance 0 is what stops
    # triggering in MAVLink.
    plan = _default_plan()
    assert plan.camera_trigger_distance_m is not None
    assert plan.camera_trigger_distance_m > 0

    items, doc = _serialized(plan)
    for item, qgc_item in zip(items, doc["mission"]["items"]):
        if item["Keyword"] == "cam_on":
            assert qgc_item["params"][0] == plan.camera_trigger_distance_m
        elif item["Keyword"] == "cam_off":
            assert qgc_item["params"][0] == 0


def test_camera_items_match_qgcs_round_trip():
    # roundtrip_qgc.plan is our default plan after QGC loaded and saved it (2026-09-30), and
    # the first file in which QGC itself wrote DO_SET_CAM_TRIGG_DIST items. QGC folds each
    # camera item into the waypoint before it and writes it back from its own template, so
    # its version is what QGC would upload. The round trip changed exactly one thing:
    # params[2], "trigger once immediately", went from 0 to 1 on every stop item. Ours must
    # now match QGC's field for field, apart from the jump id and the trigger distance (the
    # plan's own, pinned above). Checked on the shore and boat plans, so it holds for two N.
    round_trip = _reference_plan("roundtrip_qgc.plan")
    qgc_camera = [
        item for item in round_trip["mission"]["items"]
        if item["command"] == MAV_CMD_DO_SET_CAM_TRIGG_DIST
    ]
    # A distance of 0 stops triggering, which is what tells QGC's stop items from its start
    # items. Every item of a kind must be alike, so each kind has one template.
    templates = {
        "cam_on": [_camera_item_shape(item) for item in qgc_camera if item["params"][0] > 0],
        "cam_off": [_camera_item_shape(item) for item in qgc_camera if item["params"][0] == 0],
    }
    for shapes in templates.values():
        assert shapes and all(shape == shapes[0] for shape in shapes)

    for plan in (_default_plan(), _boat_plan()):
        items, doc = _serialized(plan)
        for item, qgc_item in zip(items, doc["mission"]["items"]):
            if item["Keyword"] in CAMERA_KEYWORDS:
                assert _camera_item_shape(qgc_item) == templates[item["Keyword"]][0]


def test_summary_carries_the_rpic_note(capsys):
    # Every stop item fires one final frame (pinned just above). Nobody has yet checked that
    # frame's glint, or the aircraft's attitude as it leaves the line for the turn, so the
    # RPIC is told to disregard it on every run. The summary is the only RPIC-facing text the
    # engine writes today; the pilot-notes document will owe the same note.
    flight_plan_maker._print_summary(
        _default_plan(), "t5.kml", "t5.png", "t5.plan", P.DEFAULT_MISSION_DATETIME
    )
    assert CONST.RPIC_NOTE_FINAL_FRAME in capsys.readouterr().out


def test_positions_come_from_the_waypoints():
    # Every coordinate reaches the file from the waypoint it describes, in flight order, and
    # the display altitude agrees with the uploaded one (params[6]).
    plan = _default_plan()
    _, doc = _serialized(plan)
    positional = [
        qgc_item for qgc_item in doc["mission"]["items"]
        if qgc_item["command"] != MAV_CMD_DO_SET_CAM_TRIGG_DIST
    ]

    assert len(positional) == len(plan.waypoints)
    for waypoint, qgc_item in zip(plan.waypoints, positional):
        assert qgc_item["params"][4:6] == [waypoint.latitude, waypoint.longitude]
        assert qgc_item["Altitude"] == qgc_item["params"][6]


def test_altitudes_by_class():
    # Cruise flies the plan's own altitude, AMSL. Takeoff and land are relative to home: the
    # land altitude must be 0 (anything else lands above or below the pad), and the
    # climb-out must sit above the pad and below the cruise altitude.
    plan = _default_plan()
    cruise_altitude_m = plan.mission_request.altitude
    items, doc = _serialized(plan)
    by_keyword = {}
    for item, qgc_item in zip(items, doc["mission"]["items"]):
        by_keyword.setdefault(item["Keyword"], []).append(qgc_item)

    assert all(nav["Altitude"] == cruise_altitude_m for nav in by_keyword["nav"])
    assert by_keyword["land"][0]["Altitude"] == 0
    assert 0 < by_keyword["takeoff"][0]["Altitude"] < cruise_altitude_m


def test_bearings_are_not_serialized():
    # J-4.5's bearings are reporting-only. In the file, a heading would be a commanded yaw,
    # which the null-yaw decision rules out. Neither bearing may appear as any number.
    plan = _default_plan()
    departure = plan.departure_bearing_deg
    approach = plan.approach_bearing_deg
    assert departure is not None and approach is not None

    _, doc = _serialized(plan)
    numbers = list(_numbers_in(doc))
    for bearing in (departure, approach):
        assert not any(math.isclose(number, bearing, abs_tol=1e-6) for number in numbers)


def test_no_engine_fields_reach_the_file():
    # Every QGC item is built field by field. A lazy dict(item) spread would carry our
    # provenance field and the neutral keys into a file QGC has to parse.
    _, doc = _serialized(_default_plan())
    text = json.dumps(doc)
    for key in ("Source_Action", "Keyword", "Alt_Frame_Ref", "Altitude_m", "Trigger_Distance_m"):
        assert f'"{key}"' not in text


def test_neutral_items_are_read_only_and_distinct():
    # _plan_items builds a fresh list of fresh dicts on every call, and serializing never
    # modifies it. The distinct-objects check is the one that would have caught the
    # aliasing defect where 47 waypoint slots shared 20 dicts.
    plan = _default_plan()
    items = OUT._plan_items(plan)
    snapshot = copy.deepcopy(items)

    OUT._serialize_qgc(plan, items)

    assert items == snapshot
    assert len({id(item) for item in items}) == len(items)
    assert OUT._plan_items(plan) == snapshot


def test_home_follows_the_takeoff():
    # Home is wherever THIS plan takes off. Asserted on a boat launch as well as the shore,
    # because a hardcoded site passes on the shore plan alone.
    homes = []
    for plan in (_default_plan(), _boat_plan()):
        _, doc = _serialized(plan)
        home = doc["mission"]["plannedHomePosition"]
        takeoff = doc["mission"]["items"][0]
        launch = plan.waypoints[0]

        assert home[:2] == takeoff["params"][4:6] == [launch.latitude, launch.longitude]
        homes.append(home)

    shore_home, boat_home = homes
    assert shore_home[:2] != boat_home[:2]


def test_vtol_uses_the_vtol_commands():
    # The takeoff and land columns switch on is_VTOL; cruise and camera items do not change.
    plan = _plan_built_with(aircraft=_vehicle(MAV_TYPE_VTOL_FIXEDROTOR, hover_speed_ms=5))
    items, doc = _serialized(plan)
    commands = {}
    for item, qgc_item in zip(items, doc["mission"]["items"]):
        commands.setdefault(item["Keyword"], set()).add(qgc_item["command"])

    assert commands["takeoff"] == {MAV_CMD_NAV_VTOL_TAKEOFF}
    assert commands["land"] == {MAV_CMD_NAV_VTOL_LAND}
    assert commands["nav"] == {MAV_CMD_NAV_WAYPOINT}
    assert commands["cam_on"] == commands["cam_off"] == {MAV_CMD_DO_SET_CAM_TRIGG_DIST}


def test_multirotor_uses_standard_commands_and_its_hover_speed():
    # A multirotor takes off vertically but never transitions, so it is not a VTOL: plain
    # takeoff and land. Its hover speed reaches the header, where a fixed wing's is 0.
    plan = _plan_built_with(aircraft=_vehicle(MAV_TYPE_QUADROTOR, hover_speed_ms=5))
    _, doc = _serialized(plan)
    mission = doc["mission"]

    assert mission["items"][0]["command"] == MAV_CMD_NAV_TAKEOFF
    assert mission["items"][-1]["command"] == MAV_CMD_NAV_LAND
    assert mission["vehicleType"] == MAV_TYPE_QUADROTOR
    assert mission["hoverSpeed"] == 5

    _, fixed_wing_doc = _serialized(_default_plan())
    assert fixed_wing_doc["mission"]["hoverSpeed"] == 0


def test_bad_input_fails_loudly():
    # Steps F and G will add item kinds. A forgotten branch must fail at plan time, not write
    # a null for QGC's parser to find.
    with pytest.raises(ValueError):
        OUT._qgc_params({"Keyword": "loiter"}, False)

    items = OUT._plan_items(_default_plan())
    with pytest.raises(ValueError):
        OUT._qgc_home([item for item in items if item["Keyword"] != "takeoff"])


def test_written_file_is_the_serialized_document(tmp_path):
    # What reaches disk is exactly the document the tests above checked: valid JSON with no
    # NaN or Infinity, in QGC's own formatting (sorted keys, 4-space indent, final newline),
    # so a diff against a QGC re-export stays readable.
    plan = _default_plan()
    path = Path(OUT.write_qgc_plan(plan, str(tmp_path)))

    assert path.parent == tmp_path
    assert path.suffix == f".{CONST.EXTENSION_PLAN}"

    text = path.read_text(encoding="utf-8")
    on_disk = json.loads(text, parse_constant=_reject_non_json)

    assert on_disk == OUT._serialize_qgc(plan, OUT._plan_items(plan))
    assert text == json.dumps(on_disk, indent=4, sort_keys=True) + "\n"
