# Calypso Flight Planning Engine — V2

A **sun-aware** flight-planning engine for a fixed-wing UAV (Currently the BlackSwift S2) that
collects ocean-color and Sea Surface Temperature data. The aircraft can only
collect valid science when its science legs are flown **90° in azimuth relative
to the sun** (to avoid sun glint), so the engine builds a lawnmower data collection grid centered on the M1 Mooring Station in the Pacific Ocean, orients it for minimum glint, picks the launch-nearest corner as the start, and exports the route for review.

> **Direction as of 2026-09-08**
>
> The engine is moving from a single-mission tool to something partner organizations can
> run. Four constraints now drive development, and they supersede earlier planning:
>
> 1. **A QGC-compatible `.plan` (JSON) writer is the exclusive priority.** All other V2 work
>    is sidelined until it exists — including the half-built V2C wind work.
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

The engine produces two artifacts per run:

- **`.kml`** — for visual review in QGroundControl, BlackSwift's FMS, or Google Earth.
- **`.png`** — a quick visual reference (grid, route, launch/land/M1 markers, sun arrow, metrics).

> **Note on KML + QGroundControl:** a KML in QGC is **visualization only** — it
> does *not* import as a flyable mission with auto-generated headings. A QGC
> `.plan` (JSON) exporter is **the current top-priority work item** (Step J); until it
> lands, nothing this engine emits can be uploaded and flown.

The `.plan` will be a **plain waypoint list, never a survey block** — a survey item lets the
ground station regenerate the lawnmower from its own parameters, which would discard the
sun-oriented geometry this engine exists to compute. Camera control is **baked into the
file** using distance-based triggering, both to cut pilot workload and because constant
ground spacing holds regardless of what wind does to ground speed.

The mission ends with a plain **land item at the pad** — the S2 launches from a stand and
belly-lands at a very low stall speed with steep descent capability, so no approach pattern
is generated. The **approach direction is a recommendation to the RPIC**, not part of the
flight plan, and the pilot can take manual control of the landing as with any QGC plan.

A third artifact — a **PDF pilot-notes document** carrying the wind/crab/return numbers — is
planned after the JSON, so that reporting stays out of the machine-readable outputs. Its
first job is that landing recommendation: the plan always arrives on a fixed **344.6°**
bearing (the M1 → Terrace Point reciprocal), so the notes compare that against the into-wind
heading and state the wind component the pilot will actually meet on approach.

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
Lines   : 15  |  Glint Score: 0.0
Duration: 78.6 min | Margin: 11.4 min
KML -> ./CALYPSO_OUTPUT/V2 Plan_20260720-1329.kml
PNG -> ./CALYPSO_OUTPUT/V2 Plan_20260720-1329.png
```

> The `When` line shows the mission time you selected in **Monterey local** and the
> **UTC** instant the engine actually computed the sun position with.
>
> ⚠️ **`Duration` and `Margin` cover the grid only** — the transit out to the grid and back
> is not included in either. On the mission above the true flown time is ~106 min, so the
> real margin is **negative**. See the warning under
> [V2 status](#v2-status--remaining-assumptions).

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
│   ├── outputs.py           # KML + PNG writers (QGC .plan JSON writer goes here — Step J)
│   └── validator.py         # docstring only, NO CODE — its docstring describes the
│                            #   CANCELLED RTH gate; read it as history (see CLAUDE.md, Step E)
└── tests/                   # tiered pytest harness (test_0_* … test_6_*, seven tiers)
```

---

## Running the tests

The suite is a **tiered gate** (seven tiers, 66 tests): primitives (`test_0`), date/time +
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

**Remaining work, in execution order:** **J** — QGC `.plan` JSON output (*active, and the
only active step*); **F** — mission configurability; **G** — aircraft configurability;
**C-2** — wind/boresight reporting (half built, re-scoped from a safety gate to
report-only); **D** — sun/cloud-quality ranking; **E** — legality gating. Everything after
J is sidelined until J ships.

> ### ⚠️ A generated plan is a planning sketch, not a flyable mission
>
> Three separate reasons, largest first:
>
> **1. The distance budget and the printed duration leave out the transit legs.** The
> engine budgets and reports the **grid only**; the flight from launch out to the grid and
> back to the landing site is not counted. Measured on the current default mission: grid
> 82,320 m + transit 29,867 m = **112,187 m actually flown → 106.2 min against a 90-minute
> endurance.** The summary prints **+11.4 min of margin on a flight that is 16.2 minutes
> over the battery.** This is an arithmetic gap, not a weather one — onboard wind
> compensation does not help it. **The fix is scheduled into Step J**; afterwards the
> default mission from Terrace Point is 9 lines / 77,296 m / 72.9 min, with a 17.1 min
> margin.
>
> **2. The launch/land coordinates in `constants.py` are stale.** They still hold a
> south-shore position (14,615 m from M1) while their waypoint names say Seymour. The
> standing default site is **Terrace Point** (36.94840 N, 122.06538 W) on the north shore —
> a single pad for both launch and land — which measures **22,386 m from M1, 53% further**.
> Round-trip transit alone is **44.8 km ≈ 41.5 min of a 90-minute battery**. Taken together
> with defect 1, an honest budget from Terrace Point supports **9 flight lines, not the 15
> the engine emits** (15 lines works out to 120.4 min of flying).
>
> **3. Nothing validates anything.** `src/validator.py` holds a docstring and no code. Note
> that its docstring describes the **cancelled** return-to-home gate: per the 2026-09-08
> constraints the engine no longer gates on wind at all. Whether **battery/endurance**
> feasibility remains a gate is an open decision.

Still assumed (V2 work in progress):

- A fixed aircraft — the **BlackSwift S2, a pure fixed wing** (no VTOL) — with constant
  endurance/speed/turn values, never hand-launched. Making this user-configurable, and
  adding rotorcraft support for partner vehicles (PX4 + QGC), is step **G**. The tri-motor
  VTOL S3 is not an option; its only airframe was destroyed in company testing.
- **Level flight throughout.** Climb and descent rates are carried on the `Aircraft` object
  but are not used — the whole route is timed at cruise, with zero vertical time.
- **Legal** to fly (no airspace / Part 107 checks yet — step **E**). ⚠️ The default
  altitude is **2000 ft**, five times the Part 107 ceiling of 400 ft. COA authorization is
  in progress with partner organizations and may permit **higher**, so the engine should
  eventually gate on the ceiling a mission is actually authorized for rather than a
  hard-coded 400 ft. Until then, **do not treat a generated plan as flyable as-is**.
- The grid is always centered on the **M1 mooring**, always includes an **M1 overflight**,
  and is always sized from the endurance budget rather than from a requested size. All
  three become user-settable in step **F**, along with line length, grid width, launch and
  landing points, along- and cross-track overlap, and the camera viewing angle.
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
