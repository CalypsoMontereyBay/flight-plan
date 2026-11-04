# Calypso Flight Planning Engine — V2

A **sun-aware** flight-planning engine for an uncrewed aircraft (currently the BlackSwift S3,
a tilt-rotor VTOL) that collects ocean-color and Sea Surface Temperature data. The aircraft can only
collect valid science when its science legs are flown **90° in azimuth relative
to the sun** (to avoid sun glint), so the engine builds a lawnmower data collection grid centered on the M1 Mooring Station in the Pacific Ocean, orients it for minimum glint, picks the launch-nearest corner as the start, and exports the route for review.

> **Direction as of 2026-09-08**
>
> The engine is moving from a single-mission tool to something partner organizations can
> run. Four constraints now drive development, and they supersede earlier planning:
>
> 1. **A QGC-compatible `.plan` (JSON) writer is the exclusive priority.** All other V2 work
>    is sidelined until it exists — including the half-built V2C wind work. ✅ **It shipped
>    on 2026-09-30** (Step J).
> 2. **The mission becomes configurable:** line length, grid width, center point, launch and
>    landing points, desired grid area (when feasible), along- **and** cross-track overlap,
>    and camera viewing angle.
> 3. **The aircraft becomes configurable:** fixed-wing, quadcopter, or hexacopter, with every
>    fixed-wing performance number user-settable.
> 4. **Wind is compensated onboard.** All aircraft are assumed to carry wind sensing and to
>    adjust heading and speed in flight. The engine therefore **never rejects a plan and never
>    rotates a grid because of wind** — it computes wind effects and reports them to a
>    separate pilot-notes document. Grid orientation answers to the sun and to data quality
>    alone.
>
> Default launch/land is the **UCSC Coastal Science Campus — Terrace Point** (Santa Cruz).
> See [`CLAUDE.md`](CLAUDE.md) for the full roadmap and the current defect list.

---

> **Payload note:** the SST camera is mounted **along-track** — pitched forward under the
> nose at 30° off-nadir. Because a ±90° relative azimuth is satisfied flying the grid axis in
> *either* direction, **every** leg of the lawnmower collects science, not just alternating
> ones. The engine was built around a cross-track mount (135°, 40° off-nadir) through V1;
> see the mounting note at the top of `src/geo.py` before changing any field-of-view math.

The engine produces three artifacts per run:

- **`.kml`** — for visual review in QGroundControl, BlackSwift's FMS, or Google Earth.
- **`.png`** — a quick visual reference (grid, route, launch/land/M1 markers, sun arrow, metrics).
- **`.plan`** — a QGroundControl mission file (JSON) that QGC loads as a mission. None has
  been flown yet; see the warning box below.

> **Note on KML + QGroundControl:** a KML in QGC is **visualization only** — it
> does *not* import as a flyable mission with auto-generated headings. That is why the
> engine also writes the `.plan` (Step J, complete 2026-09-30).

The `.plan` is a **plain waypoint list, never a survey block** — a survey item lets the
ground station regenerate the lawnmower from its own parameters, which would discard the
sun-oriented geometry this engine exists to compute. Camera control is **baked into the
file** using distance-based triggering, both to cut pilot workload and because constant
ground spacing holds regardless of what wind does to ground speed.

The S3 takes off vertically, transitions to forward flight 10 m above the pad, and climbs
in an orbit to mission altitude before it heads out. The engine places that **climb orbit**
600 m out from the pad on the departure bearing, so the whole orbit stays clear of it. On
the way home the aircraft **descends along the approach**, transitions back to hover 10 m
over the pad, and lands vertically. Every VTOL transitions at 10 m. The `.plan` ends with a
plain **land item at the pad** (a vertical landing for a VTOL), and the **approach direction is a recommendation to the
RPIC**, not part of the flight plan. The pilot can take manual control of the landing, as
with any QGC plan.

> **The engine does not write the S3's own files.** BlackSwift's flight management system
> flies the S3 from three XML files (takeoff, mission and landing). That writer was left
> unbuilt on purpose on 2026-11-03, because the default aircraft may change. The engine
> writes the `.plan` for every aircraft. See Step K in [`CLAUDE.md`](CLAUDE.md).

A fourth artifact — a **PDF pilot-notes document** carrying the wind/crab/return numbers — is
planned, so that reporting stays out of the machine-readable outputs. Its
first job is that landing recommendation, and **the engine already computes the input**:
every plan carries the bearing it departs on (**176.3°** from Terrace Point) and the one it
arrives home on (**343.3°**). The notes compare the arrival against the into-wind heading
and state the component the pilot will actually meet — a wind from about **163.3°** is a
pure tailwind on that approach, which is the case worth warning about as the aircraft
slows to transition. The notes will also carry the **final-frame note** the terminal
summary prints today: disregard the last photograph of each science line (see below). An
emergency belly landing is possible on the S3, but it may damage the front two motors and
the props.

> The arrival bearing is **recomputed for every plan, never assumed.** From shore it barely
> moves, because the 22 km run to the mooring dominates a grid a few kilometres across. From
> a boat 2 km off M1 it swings by more than 30°.

---

## Requirements

- **Python 3.12 or newer.** Developed and tested on **Python 3.14.4**.
- The Python packages listed in [`requirements.txt`](requirements.txt):

  | Package | Version | Used by |
  |---|---|---|
  | `pyproj` | 3.7.2 | geodesic math (bearings, destination points) — `geo.py` |
  | `shapely` | 2.1.2 | geometry primitives (`Point`, `LineString`) — `geo.py`, `objects.py` |
  | `simplekml` | 1.3.6 | KML output — `outputs.py` |
  | `matplotlib` | 3.10.9 | PNG output — `outputs.py` |
  | `pysolar` | 0.13 | sun azimuth/elevation — `sun.py` |
  | `requests` | 2.34.2 | NWS weather API client — `weather.py` |
  | `numpy` | 2.4.4 | pulled in transitively by the above |

---

## Setup (one time)

All commands are run from the **repository root** (`flight-plan/`, the folder that
contains `flight_plan_maker.py`).

**1. Create a virtual environment** named `.venv` in the repo root:

```bash
cd /path/to/flight-plan
python3 -m venv .venv
```

**2. Activate it:**

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

Your shell prompt should now be prefixed with `(.venv)`.

**3. Install the dependencies into the active venv:**

```bash
pip install -r requirements.txt
```

---

## Generating a flight plan

**Always activate the virtual environment first** so the engine finds its
packages (this avoids `ModuleNotFoundError`):

```bash
cd /path/to/flight-plan
source .venv/bin/activate          # macOS / Linux  (Windows: .venv\Scripts\Activate.ps1)
python flight_plan_maker.py
```

That single command runs the whole engine and writes a timestamped `.kml`, `.png` and
QGroundControl `.plan`, then prints a summary, e.g.:

```
Mission : V2 Plan
When    : 2026-01-01 10:00 local  (2026-01-01 18:00 UTC)
Lines   : 9  |  Glint Score: 0.0
Total Flight Duration: 74.3 min
Transit Flight: 40.79 min, 45218.87 meters
Grid Flight: 33.53 min, 42241.59 meters
Phases: climb 2.90 min | descent overrun 0.00 min | hand-offs 2.00 min (all inside Transit Flight's time)
Margin: 15.7 min
Departure Bearing: 176.33 deg | Approach Bearing: 343.28 deg
Climb Orbit: 500 m radius around 36.94300, -122.06495, from its 10 m transition above home to 609.6 m
Design Wind: 9.0 m/s at flight altitude (planning input) | Collection Inset: 601.92 m
Line 1 Lead-in: 110.26 m, for a 118.96 deg turn in from the transit
Forecast Wind: none for this date and time (reported only, never applied)
KML -> ./CALYPSO_OUTPUT/V2 Plan_20261103-170259.kml
PNG -> ./CALYPSO_OUTPUT/V2 Plan_20261103-170259.png
PLAN -> ./CALYPSO_OUTPUT/V2 Plan_20261103-170259.plan
RPIC NOTE: No live NWS forecast was available for this date and time: it is in the past, more than 7 days out, or NWS could not be reached. The plan holds clear-sky, calm defaults, and the wind has not been checked against the aircraft's wind rating. Re-run the plan within 7 days of the flight.
RPIC NOTE: The aircraft orbits at the climb point after takeoff, and again after the last waypoint, until you move it on. The plan budgets 1 min for each hand-off.
RPIC NOTE: Disregard the last photograph of each science line. The camera fires one final frame where triggering stops, at the end of the line as the aircraft heads into the turn, and that frame's glint and attitude have not been verified.
```

> ⚠️ **Read every `RPIC NOTE`.** They report and never change the plan. The engine adds
> one when it applies, most urgent first:
>
> - **A wind above the aircraft's wind rating** (15 m/s for the S3): the design wind you
>   set, or the forecast's sustained wind or gust at 10 m. The forecast is compared as NWS
>   gives it, not scaled to flight altitude, so the note also reminds you that the morning
>   wind aloft runs about 1.15 times the 10 m wind.
> - **Weather that isn't a forecast.** Either there was no live forecast at all (the date is
>   in the past or more than 7 days out, or NWS was unreachable), or NWS had no forecast at
>   the mission time for some fields, which the engine then filled with defaults. The note
>   names them. Visibility is the usual one, because NWS forecasts it only 8 to 30 hours
>   ahead. A wind that was filled with a default is never compared with the rating, and
>   the note says it went unchecked.
> - **The operator hand-offs:** the aircraft orbits after its climb and after the last
>   waypoint until you move it on.
> - **The last photograph of each science line,** on every run, until that frame is
>   characterized. Every line ends with one extra photograph where triggering stops,
>   because that is how QGroundControl writes a camera-stop item. Nobody has yet checked
>   its sun glint or the aircraft's attitude as it leaves the line, so treat it as unusable.
>
> The `When` line shows the mission time you selected in **Monterey local** and the
> **UTC** instant the engine actually computed the sun position with.
>
> The `Design Wind` line is the wind at flight altitude that the plan is sized for, which
> you set with `--design-wind`. After every turn the aircraft needs a straight stretch to
> level out before the camera starts, and that stretch grows with the wind: 601.92 m at the
> default 9 m/s. `Line 1 Lead-in` is the extra straight before the first line, because the
> turn in from the transit is sharper than the turns between lines. `Forecast Wind` is the
> National Weather Service forecast, which is for 10 m above the sea. It is shown for
> comparison only and never changes the plan. Don't read it as the wind at flight altitude:
> on a Monterey Bay morning the wind at 2000 ft runs about 1.15 times the 10 m wind.
>
> ✅ **`Total Flight Duration` and `Margin` cover the whole flight**: transit since
> 2026-09-17, and climb, descent and the operator hand-offs since 2026-10-27. They used to
> measure the grid alone, which made a 106-minute flight look like it had 11 minutes to
> spare on a 90-minute battery. The engine now reserves the round trip to the mooring, the
> 2.9 min climb orbit and two 1 min operator hand-offs *before* deciding how many flight
> lines fit. The descent is flown along the approach, so it costs extra time only when the
> approach is too short to hold it. The `Phases` line shows each of them, and
> `Transit Flight`'s time includes them. `Climb Orbit` is where the aircraft climbs, on the
> departure bearing and clear of the pad. The rates are provisional (see the warning box
> below).

### Options

| Flag | Default | Meaning |
|---|---|---|
| `--name` | `V2 Plan` | Mission name; used in the output filenames and titles. |
| `--out-dir` | `OUTPUT_DIRECTORY` in `constants.py` (`./CALYPSO_OUTPUT`) | Directory to write the `.kml` / `.png` into (created if missing). |
| `--date` | `2026-01-01` (V2 defaults in `constants.py`) | Mission date `YYYY-MM-DD`, interpreted as **Monterey local time**. |
| `--time` | `10:00` local | Mission start `HH:MM`, Monterey local; converted to UTC (DST-aware) to drive the sun position and glint scoring. |
| `--design-wind` | `9` (`DEFAULT_DESIGN_WIND_ALOFT_ms` in `constants.py`) | The wind the plan is sized for, in m/s **at flight altitude**, not the 10 m forecast. A higher value gives longer, safer straights after each turn and may fit fewer lines. Must be 0 or more. |

Each flag is independent; omit either `--date` or `--time` and it falls back to its
default. Unparseable values also fall back to the defaults rather than erroring.

```bash
python flight_plan_maker.py --name my_mission --out-dir ./outputs
python flight_plan_maker.py --date 2026-07-15 --time 14:30    # afternoon sun, Monterey local
python flight_plan_maker.py --design-wind 12                  # plan for 12 m/s at altitude
```

> **Output directory:** the default `OUTPUT_DIRECTORY` in `src/constants.py` is
> `./CALYPSO_OUTPUT` (repo-relative), created on first run. Pass `--out-dir` to
> write elsewhere.

When finished, leave the environment with:

```bash
deactivate
```

---

## Project layout

```
flight-plan/
├── flight_plan_maker.py     # terminal entry point (run this)
├── requirements.txt         # runtime dependencies
├── requirements-dev.txt     # test-only dependencies (pytest)
├── conftest.py              # puts src/ on sys.path for the test suite
├── pytest.ini               # test config + the tiered -x "gate"
├── pyrightconfig.json       # editor: resolves the flat src/ imports (Pylance/Pyright)
├── README.md
├── src/
│   ├── constants.py         # engine constants (aircraft, M1, sensor, date/time defaults, weather)
│   ├── objects.py           # Aircraft, Sensor, Weather, CurrentSunState, Waypoint,
│   │                        #   MissionRequest, CandidatePlan
│   ├── sun.py               # local->UTC datetime resolver + pysolar CurrentSunState (azimuth/elev)
│   ├── aircraft_math.py     # endurance -> distance budget, duration, battery margin
│   ├── geo.py               # geodesic math + M1-centered lawnmower grid geometry
│   ├── weather.py           # leaf: live NWS weather -> Weather object (or None -> stub)
│   ├── planner.py           # the hub: assembles objects, scores glint, builds the plan
│   ├── outputs.py           # KML, PNG and QGC .plan writers
│   └── validator.py         # docstring only, NO CODE — its docstring describes the
│                            #   CANCELLED RTH gate; read it as history (see CLAUDE.md, Step E)
└── tests/                   # tiered pytest harness (test_0_* … test_6_*, seven tiers)
```

---

## Running the tests

The suite is a **tiered gate** (seven tiers, 120 tests): primitives (`test_0`), date/time +
sun (`test_1`), derived math incl. the wind triangle (`test_2`), the weather leaf (`test_3`),
then grid / classification / rendering indicators (`test_4`–`test_6`). `pytest.ini` sets `-x` (fail-fast), so a run stops at
the first broken tier — fix the lowest red tier, re-run, climb.

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt   # one time: installs pytest
pytest                                # runs all tiers, gated
```

To see every test in one tier despite a failure: `pytest tests/test_2_derived_math.py -o addopts=""`.

---

## V2 status & remaining assumptions

V1 (proof-of-engine) is complete. **Done:** Step A — selectable mission date/time
(`--date` / `--time`, Monterey local → UTC), which drives the sun azimuth and therefore
glint; Step B — live **NWS weather** (`weather.py`), a leaf that populates the `Weather`
object for in-horizon dates and gracefully falls back to a clear-sky stub otherwise; and
Step C-1 — the **along-track payload mount** (90° relative azimuth, 30° off-nadir, every
leg collecting).

**Step J is complete (2026-09-30).** Every run writes a QGroundControl `.plan`: a plain
waypoint list with distance-triggered camera items, sized against a budget that pays for
the transit. The summary reports the grid/transit split, both bearings and the RPIC note.
The file has been round-tripped through QGC: QGC changed one camera value on load and
save, the engine now writes that value too, and a fresh plan matches QGC's save exactly.

**Step K, adopting the BlackSwift S3, closed on 2026-11-03.** BlackSwift retired the S2.
The S3 is now the default aircraft, and its takeoff, climb orbit, descent and hand-offs are
budgeted. The summary shows the climb orbit and phase times, and pilot notes for winds
above the aircraft's rating and for weather that isn't a forecast. The engine does **not**
write the S3's three XML files: that writer was left unbuilt on purpose, because the
default aircraft may change.

**Remaining work, in execution order:** **F** — mission configurability; **G** —
aircraft configurability; **C-2** — wind/boresight reporting (half built, re-scoped from a
safety gate to report-only); **D** — sun/cloud-quality ranking; **E** — legality gating.

> ### ⚠️ A generated plan is a planning sketch, not a flyable mission
>
> This box lists the reasons that still stand. What has been fixed is kept below as history.
>
> **1. Nothing validates anything.** `src/validator.py` holds a docstring and no code. Note
> that its docstring describes the **cancelled** return-to-home gate: per the 2026-09-08
> constraints the engine no longer gates on wind at all. Whether **battery/endurance**
> feasibility remains a gate is an open decision — though the everyday case is now handled
> by sizing rather than gating (see below).
>
> **2. No output has ever been flown.**
>
> **3. The camera-rollout fix is built, but its constants are provisional** (2026-10-18).
> Each line now leaves a straight stretch after its turn, sized from the design wind, so
> the aircraft is level before the camera starts (601.9 m for the S3 at the default 9 m/s). The sizes
> come from a simulator calibration of PX4 flying a model of the BlackSwift S2. The S2 is
> end of life, and the S3 that replaces it is flown by BlackSwift's own flight management
> system, which is nothing like PX4. So the constants are provisional placeholders for the
> S3. The S2 simulation that was to check the finished geometry was cancelled, and
> BlackSwift has declined to share an S3 model or its numbers, so no S3 check is planned.
> And on a day windier than the design wind, the first photograph of some lines may be
> taken while the aircraft is still banked, so set `--design-wind` for the day.
>
> **4. Climb, descent and hand-offs use provisional rates** (2026-10-27). They are now
> budgeted, but the climb and descent rates are the retired S2's, and BlackSwift can't share
> the S3's. Every aircraft is charged the climb orbit and the hand-offs, which over-counts
> one that climbs on its way out.
>
> #### ✅ Fixed on 2026-10-18
>
> **The camera used to start before the aircraft had rolled out of its turns.** Each
> science line's first photograph was taken while the S2 was still banked (20–35° in
> simulation), and it was the only photograph of the first ~54 m of that line's science
> area. The camera started 52 m after each turn point, less than the S2's 57 m turn radius
> in still air. The straight is now sized from the design wind, and the turn onto the first
> line gets extra room.
>
> #### ✅ Fixed on 2026-09-17
>
> **The distance budget used to leave out the transit legs.** The engine budgeted and
> reported the **grid only**, so nothing paid for the flight out to the mooring and back —
> 112,187 m actually flown from the old south-shore pads against a 90-minute battery,
> reported as +11.4 min of margin. (From Terrace Point the same defect would have flown
> 127,559 m.)
> The engine now reserves the round trip *before* choosing how many flight lines fit. The
> default mission became **9 lines / 77,296 m / 72.9 min / 17.1 min margin** on the S2
> (9 lines / 87,460 m / 74.3 min / 15.7 min on the S3 today, climb and hand-offs included),
> and `Total Flight Duration` and `Margin` describe the route that would actually be flown.
>
> **The launch/land coordinates used to be stale**, holding a south-shore position while
> their waypoint names said Seymour. They now hold **Terrace Point** (36.94840 N,
> 122.06538 W) — a single pad for both launch and land, **22,386 m from M1**.

Still assumed (V2 work in progress):

- A fixed aircraft — the **BlackSwift S3, a tilt-rotor VTOL** (90 min, 21 m/s cruise) —
  never hand-launched. BlackSwift retired the S2 on 2026-10-13. Making the aircraft
  user-configurable, and adding rotorcraft support for partner vehicles (PX4 + QGC), is
  step **G**. The S3's turn radius (77.6 m) is derived, and its climb and descent rates are
  the S2's until better numbers exist.
- **Legal** to fly (no airspace / Part 107 checks yet — step **E**). ⚠️ The default
  altitude is **2000 ft**, five times the Part 107 ceiling of 400 ft. COA authorization is
  in progress with partner organizations and may permit **higher**, so the engine should
  eventually gate on the ceiling a mission is actually authorized for rather than a
  hard-coded 400 ft. Until then, **do not treat a generated plan as flyable as-is**.
- The grid is always centered on the **M1 mooring**, always includes an **M1 overflight**,
  and is always sized from the endurance budget rather than from a requested size. All
  three become user-settable in step **F**, along with line length, grid width, launch and
  landing points, along- and cross-track overlap, and the camera viewing angle.
- **Where you launch from is the biggest lever on how much science you get.** From Terrace
  Point the round trip to the mooring consumes **47% of the usable battery** before a single
  science line is flown. Launching from a stationary boat 2 km off M1 takes the same
  aircraft from 9 flight lines to 11. Making the launch point user-settable (step **F**) is
  therefore an efficiency feature, not just a convenience one.
- **A design wind of 9 m/s at flight altitude**, unless you set another with
  `--design-wind`. It sizes the straight after every turn. The engine never takes it from
  the forecast: the forecast is for 10 m, and choosing the day's value is the pilot's call.
- **Sun glint** is the only ranking metric (science legs held 90° off the sun at a 15°
  tolerance). Cloud cover is fetched but not yet folded into ranking (step **D**).
- The 90° is measured on the **camera boresight**, which follows the fuselage, so crosswind
  crab shifts it — roughly 4.7 m/s of crosswind across the science axis consumes the full
  15° at cruise. As of 2026-09-08 this is **reported, never enforced**: aircraft are assumed
  to sense and compensate for wind in flight, so no plan is rejected and no grid is rotated
  because of it (step **C-2**, re-scoped to math + reporting).
- The imaged strip sits **352 m forward** of the aircraft (30° off-nadir at 2000 ft). Each
  flight line is extended to compensate; the crab-induced sideways shear of that strip is
  reported but not corrected.
