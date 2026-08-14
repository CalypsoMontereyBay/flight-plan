# Calypso Flight Planning Engine — V2

A **sun-aware** flight-planning engine for a fixed-wing UAV (Currently the BlackSwift S2) that
collects ocean-color and Sea Surface Temperature data. The aircraft can only
collect valid science when its science legs are flown **135° in azimuth relative
to the sun** (to avoid sun glint), so the engine builds a lawnmower data collection grid centered on the M1 Mooring Station in the Pacific Ocean, orients it for minimum glint, picks the launch-nearest corner as the start, and exports the route for review.

The engine produces two artifacts per run:

- **`.kml`** — for visual review in QGroundControl, BlackSwift's FMS, or Google Earth.
- **`.png`** — a quick visual reference (grid, route, launch/land/M1 markers, sun arrow, metrics).

> **Note on KML + QGroundControl:** a KML in QGC is **visualization only** — it
> does *not* import as a flyable mission with auto-generated headings. A QGC
> `.plan` (JSON) exporter is planned for V2.

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

That single command runs the whole engine and writes a timestamped `.kml` and
`.png` pair, then prints a summary, e.g.:

```
Mission : V2 Plan
When    : 2026-01-01 10:00 local  (2026-01-01 18:00 UTC)
Lines   : 23  |  Glint Score: 0.0
Duration: 74.9 min | Margin: 15.1 min
KML -> ./CALYPSO_OUTPUT/V2 Plan_20260720-1329.kml
PNG -> ./CALYPSO_OUTPUT/V2 Plan_20260720-1329.png
```

> The `When` line shows the mission time you selected in **Monterey local** and the
> **UTC** instant the engine actually computed the sun position with.

### Options

| Flag | Default | Meaning |
|---|---|---|
| `--name` | `V2 Plan` | Mission name; used in the output filenames and titles. |
| `--out-dir` | `OUTPUT_DIRECTORY` in `constants.py` (`./CALYPSO_OUTPUT`) | Directory to write the `.kml` / `.png` into (created if missing). |
| `--date` | `2026-01-01` (V2 defaults in `constants.py`) | Mission date `YYYY-MM-DD`, interpreted as **Monterey local time**. |
| `--time` | `10:00` local | Mission start `HH:MM`, Monterey local; converted to UTC (DST-aware) to drive the sun position and glint scoring. |

Each flag is independent; omit either `--date` or `--time` and it falls back to its
default. Unparseable values also fall back to the defaults rather than erroring.

```bash
python flight_plan_maker.py --name my_mission --out-dir ./outputs
python flight_plan_maker.py --date 2026-07-15 --time 14:30    # afternoon sun, Monterey local
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
│   ├── outputs.py           # KML + PNG writers
│   └── validator.py         # (empty — reserved for V2 legality/feasibility gating)
└── tests/                   # tiered pytest harness (test_0_* … test_5_*)
```

---

## Running the tests

The suite is a **tiered gate** (six tiers): primitives (`test_0`), date/time + sun +
weather wiring (`test_1`), derived math (`test_2`), then grid / classification / rendering
indicators (`test_3`–`test_5`). `pytest.ini` sets `-x` (fail-fast), so a run stops at
the first broken tier — fix the lowest red tier, re-run, climb.

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt   # one time: installs pytest
pytest                                # runs all tiers, gated
```

To see every test in one tier despite a failure: `pytest tests/test_2_derived_math.py -o addopts=""`.

---

## V2 status & remaining assumptions

V1 (proof-of-engine) is complete. V2 makes the mission situation-aware one step at a
time. **Done:** Step A — selectable mission date/time (`--date` / `--time`, Monterey
local → UTC), which drives the sun azimuth and therefore glint; and Step B — live
**NWS weather** (`weather.py`), a leaf that populates the `Weather` object for
in-horizon dates and gracefully falls back to a clear-sky stub otherwise.

Still assumed (V2 work in progress):

- A fixed aircraft (**BlackSwift S2**) with constant endurance/speed/turn values.
- **Legal** to fly (no airspace / Part 107 checks yet — step **E**).
- The grid is always centered on the **M1 mooring**, and the route always includes an **M1 overflight**.
- **Sun glint** is the only ranking metric (science legs held 135° off the sun, gated at a 15° tolerance) — weather is fetched but not yet folded into ranking (step **D**).
