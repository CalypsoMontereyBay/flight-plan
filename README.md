# Calypso Flight Planning Engine — V1

A **sun-aware** flight-planning engine for a fixed-wing UAV (Currently the BlackSwift S2) that
collects ocean-color and Sea Surface Temperature data. The aircraft can only
collect valid science when its science legs are flown **135° in azimuth relative
to the sun** (to avoid sun glint), so the engine builds a lawnmower data collection grid centered on the M1 Mooring Station in the Pacific Ocean, orients it for minimum glint, picks the launch-nearest corner as the start, and exports the route for review.

V1 produces two artifacts per run:

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
Mission : v1_m1_test
Lines   : 23  |  Glint Score: 0.0
Duration: 74.9 min | Margin: 15.1 min
KML -> ./CALYPSO_OUTPUT/v1_m1_test_20260609-1529.kml
PNG -> ./CALYPSO_OUTPUT/v1_m1_test_20260609-1529.png
```

### Options

| Flag | Default | Meaning |
|---|---|---|
| `--name` | `v1_m1_test` (from `constants.py`) | Mission name; used in the output filenames and titles. |
| `--out-dir` | `OUTPUT_DIRECTORY` in `constants.py` | Directory to write the `.kml` / `.png` into (created if missing). |

```bash
python flight_plan_maker.py --name my_mission --out-dir ./outputs
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
│   ├── constants.py         # all V1 assumed constants (aircraft, M1, sensor, dates)
│   ├── objects.py           # Aircraft, Sensor, Weather, CurrentSunState, Waypoint,
│   │                        #   MissionRequest, CandidatePlan
│   ├── sun.py               # pysolar -> CurrentSunState (sun azimuth/elevation)
│   ├── aircraft_math.py     # endurance -> distance budget, duration, battery margin
│   ├── geo.py               # geodesic math + M1-centered lawnmower grid geometry
│   ├── planner.py           # the hub: assembles objects, scores glint, builds the plan
│   ├── outputs.py           # KML + PNG writers
│   └── validator.py         # (empty — reserved for V2 legality/feasibility gating)
└── tests/                   # tiered pytest harness (test_0_* … test_4_*)
```

---

## Running the tests

The suite is a **tiered gate**: pure math (`test_0`, `test_1`) at the bottom, then
grid / classification / rendering indicators (`test_2`–`test_4`). `pytest.ini` sets
`-x` (fail-fast), so a run stops at the first broken tier — fix the lowest red tier,
re-run, climb.

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt   # one time: installs pytest
pytest                                # runs all tiers, gated
```

To see every test in one tier despite a failure: `pytest tests/test_1_derived_math.py -o addopts=""`.

---

## V1 assumptions

V1 is a proof-of-engine build. It assumes:

- A fixed aircraft (**BlackSwift S2**) with constant endurance/speed/turn values.
- **Clear skies**, a fixed mission date/time (**Jan 1 2026, 18:00 UTC ≈ 10:00 local**), and no wind.
- **Legal** to fly (no airspace checks yet).
- The grid is always centered on the **M1 mooring**, and the route always includes an **M1 overflight**.
- **Sun glint** is the only ranking metric (science legs held 135° off the sun, gated at a 15° tolerance).
