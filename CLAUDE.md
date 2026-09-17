# CLAUDE.md

Guidance for Claude Code when working in this repository.

## Working agreement

- **Git is mine.** I (the user) run all git commands — `add`, `commit`, `branch`,
  `push`, `pull`, `merge`, `rebase`, tags, etc. Do **not** stage, commit, or push
  on my behalf, and do not suggest doing so as part of a task unless I explicitly
  ask. You may edit files; I will handle version control.
- **Workflow.** I usually ask you to audit/plan first and implement the code changes
  myself, then ask you to audit my work against the plan. Follow that rhythm unless I
  say otherwise.
- **QGroundControl Constants** shall only be modified by the user. Do **not** modify these constants
unless given express permission from the user.

## Project overview

Calypso Monterey Bay flight-planning engine. A sun-aware flight planner for uncrewed
aircraft collecting ocean-color / SST data over Monterey Bay. It builds a lawnmower grid
oriented for minimum sun glint (science legs held **90° off the sun**) and exports the
route as `.kml` and `.png`. See [`README.md`](README.md) for the full description.

**V1 (proof-of-engine) is complete and tested. V2 Steps A (selectable date/time), B
(live NWS weather) and C-1 (along-track payload mount) are complete and tested. C-2 is
HALF BUILT and has been RE-SCOPED — it is no longer a gate. Everything on the V2 roadmap
is SIDELINED behind Step J (JSON output).** See
[Operating constraints](#operating-constraints--2026-09-08-supersedes-earlier-scoping) and
the [V2 roadmap](#v2-roadmap--what-comes-next).

**Step J progress as of 2026-09-17: J-0 through J-4.5 are DONE and tested (71 tests
green). J-5 (the writer) is the next step and the only substantial one left.** The two
largest defects the warning box used to carry — the transit-blind budget and the stale
launch coordinates — are **fixed**. The engine now sizes N against a budget that pays for
the commute, reports a duration for the route actually flown, and carries the approach
and departure bearings it commits the aircraft to.

## Operating constraints — 2026-09-08 (SUPERSEDES EARLIER SCOPING)

The engine is no longer a single-mission tool for one aircraft flying one site. It is
becoming a planner other partners run, and that changes the design. **These four items
override anything written before this date.** Where an older section conflicts, this
section wins.

1. **JSON output is the exclusive active priority.** A QGC-compatible `.plan` (JSON)
   writer must exist before *any* other V2 work resumes. Everything else on the roadmap —
   C-2, D, E, and the new configurability work — is **sidelined** until it lands. See
   [Step J](#j-json-plan-output--current-and-exclusive-priority).
2. **The mission must become configurable.** Users set line length, grid width, center
   point, launch point, landing point, desired grid area (honoured when mathematically
   feasible), overlap percentage in **both** the along- and cross-track directions, and
   the camera viewing angle. See [Step F](#f-mission-configurability-sidelined).
   MAVLINK PROTOCOL MUST BE ACCOUNTED FOR (SEE LINK): https://docs.qgroundcontrol.com/master/en/qgc-dev-guide/file_formats/plan.html
3. **The aircraft must become configurable.** Fixed-wing, quadcopter, or hexacopter. For
   a fixed wing every performance constant currently hard-coded to the BlackSwift S2 must
   be user-settable. Multirotor constraints get scoped once the fixed-wing config lands.
   See [Step G](#g-aircraft-configurability-sidelined).
   MAVLINK PROTOCOL MUST BE ACCOUNTED FOR (SEE LINK): https://docs.qgroundcontrol.com/master/en/qgc-dev-guide/file_formats/plan.html
4. **Wind is compensated onboard — the engine must not gate or steer on it.** Assume all
   aircraft carry wind sensing and adjust heading and speed in flight for best
   performance. Therefore:
   - **No plan may be rejected** because of crab angle or any live weather parameter.
   - **The grid never rotates in response to wind.** Orientation is decided by the sun and
     by data quality, full stop.
   - Wind math is still **computed and reported** — into a separate pilot-notes document,
     not into the `.kml` / `.png` / `.json`.
   - Net effect: **V2C is stripped to math + reporting.** Its gating and
     plan-altering functionality is cancelled, not deferred. See
     [C-2 re-scoped](#c-2-boresight--wind-reporting--re-scoped-2026-09-08-sidelined).

**Default launch/land is now UCSC Coastal Science Campus — Terrace Point** (Santa Cruz,
north shore) at **36.94840 N, 122.06538 W**, and stays that way until re-specified. This is
a standing assumption, not a per-mission choice, even though item 2 also makes it
user-settable. **Launch and land are the SAME point** — the two-waypoint (beach launch /
road land) split from V1 collapses.

**Vehicle facts that follow from the constraints** (recorded here because they decide the
takeoff/land commands Step J must emit):
- **BlackSwift S2 — pure fixed wing.** This is the default aircraft and the only one
  currently available. No VTOL, therefore **no transition altitude**.
- **The S3 was the tri-motor VTOL, and the only airframe was destroyed in company
  testing.** The VTOL vehicle class is real but has no instance today.
- **Custom partner vehicles are essentially always rotorcraft**, flashed with PX4 and
  driven from QGC.
- **No vehicle is ever hand-launched.** Every launch is from land or a **stationary boat**.
  A boat launch near M1 is operationally significant — see the transit note in Step J.

> ## ⚠️ READ THIS BEFORE TRUSTING A GENERATED PLAN
>
> A generated plan is a **planning sketch for review**, never a flyable mission. This box
> used to carry three reasons. **Two are fixed as of 2026-09-17** and are recorded below
> as history, because the reasoning is worth keeping and because re-measuring is expensive.
>
> **1. Nothing validates anything.** `validator.py` holds a docstring and no code. Note
> that under the 2026-09-08 constraints this is *no longer* about wind: the RTH/crosswind
> gate C-2 was scoping is **cancelled**. What survives as a genuine open question is
> whether **battery/endurance feasibility** stays a gate or also becomes a report — see
> [Step E](#e-validatorpy--legalityfeasibility-gating-sidelined-and-narrowed). Note that
> J-4 makes the *sizing* honest; it does not add a *gate*, and the two are different jobs.
>
> **2. No output has been flown, or even round-tripped through QGC.** The `.plan` writer
> does not exist yet (J-5). Until a generated file has been loaded into QGC, re-exported
> and diffed, treat the format as unverified.
>
> ### ✅ FIXED — kept as history, do not re-diagnose
>
> **~~The distance budget ignores the transit legs.~~ Fixed in J-4.** `geo` was handed the
> entire 82,620 m budget and allowed to size a grid that consumed all of it, so nothing
> paid for the 44.8 km round trip to M1. The engine emitted **N=15 = 127,559 m = 120.4 min
> against a 90 min battery, and printed +11.4 min of margin.** `planner` now reserves the
> transit before `geo` chooses N. Default mission is **N=9 / 77,296 m / 72.9 min /
> 17.1 min margin**. See the J step table in the roadmap.
>
> **~~The launch point in `constants.py` is stale.~~ Fixed in J-1.** The constants held
> the south shore (36.637, −121.936) while the waypoint names said Seymour. They now hold
> **Terrace Point, 36.94840 N / 122.06538 W**, one pad for both launch and land, **22,386 m
> from M1**. ⚠️ **The waypoint NAMES in `planner.py` are still `Seymour-Beach-Launch` /
> `Seymour-Road-Land`** — cosmetic, reaches the KML labels, worth fixing in J-8.
>
> The one V2C-2 change that IS live is the parallax line extension in
> `geo.make_lawnmower_grid_through_m1` — it lengthens every line by 808 m.

## Layout

- `flight_plan_maker.py` — terminal entry point (run this). CLI flags: `--name`, `--out-dir`, `--date`, `--time`.
- `src/` — engine modules:
  - `constants.py` — engine constants (aircraft, M1, sensor, date/time defaults + timezone, weather, actions).
  - `objects.py` — core classes (Aircraft, **Vehicle**, Sensor, Weather, CurrentSunState,
    Waypoint, MissionRequest, CandidatePlan). `Vehicle(Aircraft)` adds the MAVLink protocol
    identity Step J needs — `vehicle_type`, `firmware_type`, `is_VTOL`, `hover_speed_ms`.
    ⚠️ **Nothing constructs a `Vehicle` yet** — see the J-5 prerequisite in the roadmap.
  - `sun.py` — local→UTC datetime resolver (`resolve_mission_datetime`, `mission_datetime`) + pysolar sun azimuth/elevation (`create_sun_state`).
  - `aircraft_math.py` — endurance → distance budget, duration, battery margin, plus the
    V2C wind triangle (**reporting only** as of 2026-09-08 — see constraint 4).
  - `geo.py` — geodesic math + M1-centered lawnmower grid geometry (the M1-centering
    becomes a *default* rather than an invariant under Step F).
  - `weather.py` — **leaf**: live NWS weather for a lat/lon/datetime → populated `Weather`, or `None` (planner falls back to the stub).
  - `planner.py` — the hub: assembles objects, scores glint, builds the plan.
  - `outputs.py` — KML + PNG writers. **Step J adds the QGC `.plan` (JSON) writer here**,
    and a separate pilot-notes document is where wind/crab reporting goes (constraint 4).
  - `validator.py` — **docstring only, no code.** Its docstring still describes the
    **cancelled** C-2 RTH/crosswind gate; read it as history, not as a spec. What
    validation survives is narrowed and sidelined — see Step E.
- `tests/` — tiered pytest harness (`test_0_*` … `test_6_*`, **seven** tiers, 71 tests); see [Setup & run](#setup--run).
- `exp2.plan` — a **real QGroundControl export for this site**, and the only ground truth
  the repo has for the `.plan` format. J-5 must be checked against it; several format
  questions that docs left ambiguous are settled by reading it. See
  [What `exp2.plan` settles](#what-exp2plan-settles).
- `conftest.py`, `pytest.ini`, `requirements-dev.txt`, `pyrightconfig.json` — test wiring
  and editor import resolution (`pyrightconfig` sets `extraPaths: ["src"]` so Pylance
  resolves the flat `import geo` / `planner` / `constants` style).

## Design conventions

- **"Dumb unidirectionality":** each module knows only as much about the rest of
  the program as it strictly needs. `planner.py` is the hub that knows the other
  modules; the other modules do not reach back. Preserve this when adding code —
  new V2 modules (e.g. a `weather.py`, a fleshed-out `validator.py`) must be **leaves**
  that `planner.py` orchestrates, not modules that reach back into the hub.
- `outputs.py` is a black box that renders whatever the plan contains — it does
  not validate correctness. (Its docstring anticipates moving *behind* validation so it
  only renders approved plans; whether that ever happens now depends on the open
  battery-feasibility decision in Step E.)
- **Compute vs. permit are separate jobs** (constraint 4 sharpens this). A module may
  calculate any number honestly — crab, ground speed, return time — without that number
  being allowed to veto or steer a plan. Wind math *reports*; it does not decide.
- Modules import flat (`import constants as CONST`, `from geo import ...`); the entry
  point and `conftest.py` put `src/` on `sys.path`.
- **Functions work from their parameters, not from module-level singletons.** `planner`
  declares `_Black_Swift`, `_Launch_Waypoint`, `_M1_Waypoint` and
  `_Black_Swift_usable_endurance_m` at module scope, and `build_candidate_plan` also
  *receives* all of them. Reaching for the global inside the function is silently correct
  today — the singleton is what gets passed — and wrong the moment Step F makes the launch
  point user-settable or Step G deletes the aircraft singleton. It also makes the function
  untestable with any other site or airframe, which is not hypothetical: the J-4 retry and
  boat-launch tests both require passing a different `MissionRequest`.
- **⚠️ When a name stops describing its contents, SPLIT it — do not redefine it.** This is
  the single most repeated defect shape in this codebase, three times and counting:
  - `line_length_m` (science coverage) vs `physical_line_length_m` (what gets flown)
  - `total_grid_distance_m` (the grid) vs `total_flight_distance_m` (the whole route)
  - `grid_budget_m` (what `geo` was handed) vs `usable_endurance_distance_m` (the battery)

  Each time, one name quietly came to mean two things, every caller kept working, and the
  error only surfaced as an impossible number much later. Before reusing an existing field
  for a changed quantity, add a second field instead.

## Setup & run

Run from the repo root with the virtualenv active:

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python flight_plan_maker.py        # optional: --name NAME --out-dir DIR
```

Output defaults to `./CALYPSO_OUTPUT` (repo-relative, created on first run); pass
`--out-dir` to write elsewhere.

**Tests** (tiered gate — pure math at the bottom, grid/classification/rendering
indicators above; `pytest.ini` runs `-x` so the run stops at the first broken tier):

```bash
pip install -r requirements-dev.txt   # one time: pytest
pytest                                 # all tiers, gated bottom-up
pytest tests/test_2_derived_math.py -o addopts=""   # one tier, no fail-fast
```

## Current state — what the engine actually does (context for future work)

Read this before touching the grid, classification, or output code.

- **Selectable date/time (V2 Step A, done).** `flight_plan_maker` takes `--date`/`--time`
  as **Monterey-local** strings; `sun.resolve_mission_datetime` converts them to a tz-aware
  UTC instant (DST-aware via `zoneinfo`), defaulting to the V2 constants when omitted, and
  is lenient (bad input → defaults). `planner._build_dated_objects` builds the sun state /
  mission request / weather **per run** from that instant, so the sun azimuth (and thus
  glint) track the chosen time. `plan_default_mission(name, mission_datetime=None)` falls
  back to the module default. The summary echoes local + UTC.

- **Live weather (V2 Step B, done).** `weather.py` is a **leaf**: `get_weather(lat, lon, when)`
  returns a `Weather` populated from live NWS data, or `None` (outside the ~7-day forecast
  horizon, or any network/parse failure). `planner._build_dated_objects` uses it and falls
  back to the clear-sky / zero-wind stub on `None`, so a plan is always produced. Wind arrives
  in km/h (`_to_ms` → m/s); `condition` from `skyCover` thresholds; absent fields (often
  `visibility`) fall to `DEFAULT_*`. Offline tests monkeypatch the fetch (`tests/test_3_weather.py`).

- **Along-track payload mount (V2 Step C-1, done).** ⚠️ **Read the MOUNTING NOTE at the top
  of `geo.py` before touching any FOV math.** The SST camera is now pitched **along-track**
  (forward, under the nose, 30° off-nadir); it used to be rolled **cross-track** at 40°.
  Only one axis is ever tilted, and the tilt decides which formula each axis uses:
  tilted → `h·(tan(θ+fov/2) − tan(θ−fov/2))`, untilted → `2·(h/cos θ)·tan(fov/2)`.
  When the mount rotated, `ground_swath_width_m` and `ground_footprint_along_m`
  **swapped formula bodies** — that swap looks like a bug in `git blame` and is not.
  Three consequences drive everything else below:
  1. Science legs are held **90° off the sun** (was 135°), gated at `V1_GLINT_TOLERANCE_DEG`
     (held at 15°, not tightened — see the note on that constant).
  2. The cross-track swath is now **centered on the ground track**. Under the old roll it
     sat 33.8–241.9 m off to *one side*, so the "free M1 overflight" imaged nothing at M1.
  3. **Both leg directions collect science**, because `sun ± 90` describes one grid axis
     flown both ways. This is why `_candidate_orientation`'s two candidates come out 180°
     apart — documented, not a bug.
  `Sensor.mounting` records the assumption; `planner._build_grid_for_orientation` raises if
  a `Sensor` declares anything other than along-track. `geo.sensor_parallax_m` reports the
  **352 m** offset between nadir and the boresight ground point. The parallax **line
  extension** in `make_lawnmower_grid_through_m1` is live (+808 m/line); the crab-shear half
  of that correction is cancelled with the rest of C-2's plan-altering work.
  ⚠️ Step F makes off-nadir angle user-settable, so none of these numbers stay constant.
- **5-point flight lines.** `geo.make_line_through_point` emits
  `[turn, collect_start, line_label (center), collect_stop, turn]`
  (`V1_POINTS_PER_LINE = 5`, the single source of truth — do not re-hardcode `5`).
  The center is the M1 overflight if it's the center line; the
  `collect_start`/`collect_stop` inset points sit one `V1_COLLECTION_INSET_m` in from
  each turn (camera on/off after roll-out). **Every** leg collects, so the serpentine no
  longer alternates science/transit.
- **Classification.** `planner._classify_waypoints` tags purely by position within the
  5-point leg — there is no science-vs-transit decision left to make. The old
  reversal-safety hazard (that `_reorient_to_launch` flips every leg's heading) is
  **designed out** rather than guarded: reversal cannot change which legs collect when
  all of them do. The invariant now lives in the Tier 4 "heading-safety" test, which pins
  the physical requirement — every leg's flown bearing is within tolerance of 90° relative
  azimuth to the sun. Don't regress to index/parity tagging, and don't reintroduce a
  heading branch here.
- **Delimiter rendering.** `outputs._segment_builder` walks the route with a
  `collecting` flag: `collect_start` opens a green (science) run, `collect_stop`
  closes it, everything between (incl. `line_label`) is green. Science legs render as
  full lines with small symmetric gray gaps at the turns.
- **Metrics.** `science_lines = N`, `traverse_lines = 0`, `offset_lines = N-1`
  where `N = total_lines` (odd, so the center line passes through M1 → free overflight).
  `cross_track_swath_m`, `sensor_parallax_m` and `camera_trigger_distance_m` ride the same
  metrics dict and reach the plan via `set_grid_metrics`.

- **Transit-aware sizing (V2 Step J-4, done).** ⚠️ **Read this before touching the budget,
  `geo`'s signature, or anything named `*_distance_m`.** `planner.build_candidate_plan`
  reserves the transit *before* `geo` is allowed to choose N:
  1. `seed = 2 × distance(launch, M1)` — accurate to **+0.40%** against the measured
     entry/exit legs at the Terrace Point geometry, so one pass normally suffices.
  2. `grid_budget = usable_endurance − seed`, handed to `_pick_best_orientation`.
  3. After `_reorient_to_launch` and `_classify_waypoints`, the **true** transit is measured
     from the real corners: `d(launch_wp, route[1]) + d(route[-2], land_wp)`.
  4. If the total does not fit, re-seed with the **measured** transit and loop, bounded by
     `CONST.TRANSIT_FIT_MAX_PASSES`. The measured value is strictly larger than the estimate
     that just failed, so the budget strictly shrinks and the loop **cannot spin**. If it
     shrinks past a 3-line grid, `geo` raises — the honest "no grid fits this launch point".
  - **The subtraction lives in `planner`, never `geo`.** `make_lawnmower_grid_through_m1`
    takes a centre, an orientation and a distance; it does not know where launch is and
    **must not learn**. Passing launch/land into `geo` is the naive fix and it breaks
    unidirectionality.
  - **⚠️ `CONST.TRANSIT_FIT_MAX_PASSES` is NOT `RTH_MAX_ITERATIONS`.** The RTH loop bounded a
    *weather* gate that was cancelled; this one bounds a *geometric* convergence. Do not
    merge them.
  - **Four names, four distances** — the distinction is load-bearing:
    - `plan.usable_endurance_distance_m` — what the **battery** affords (82,620 m). Set by
      `planner`, because only the hub knows it.
    - `plan.grid_budget_m` — what `geo` was **handed** (endurance − transit, 37,847 m).
      Arrives via the metrics dict.
    - `plan.total_grid_distance_m` — what the **grid** costs (32,343 m). From `geo`.
    - `plan.total_flight_distance` — what is actually **flown** (77,296 m). Computed by
      `planner` over the classified route, and what `route_duration_min` consumes.

    Collapsing any two of these reintroduces the defect. It has already happened twice under
    different names — see the last bullet in [Design conventions](#design-conventions).

- **Transit bearings (V2 Step J-4.5, done).** `plan.departure_bearing_deg` (**174.8°**) and
  `plan.approach_bearing_deg` (**344.6°**) are set by `set_transit_bearings` from the same
  two waypoint pairs J-4 measures for the transit. **Reporting only** — they reach the
  terminal summary and the pilot-notes PDF, never the `.plan` (a heading in the file would
  mean a commanded yaw, which the null-yaw decision rules out).
  - ⚠️ **Measure after `_reorient_to_launch`, never before.** Reorientation decides which end
    of the serpentine the aircraft exits from; read off the raw grid the approach comes out
    ~10° wrong. Pinned by a Tier 4 assertion that the reported approach equals
    `bearing_between(waypoints[-2], waypoints[-1])`, mutation-verified to fail otherwise.
  - The approach sits **5.0° off the pad→M1 reciprocal** (349.6°) for a shore launch,
    because 22.4 km of transit dominates a few-km grid. **A boat launch breaks that** —
    from 2 km out it swings to 308.5°. Never brief the number from memory; recompute it.
  - Operational use: a wind **from ~164.6°** is a pure tailwind on the approach, which is
    the case worth warning about on a belly-landing airframe. Crab on approach at 18 m/s
    cruise: 6.4° at 2 m/s crosswind, 12.8° at 4, 19.5° at 6, 26.4° at 8, 33.8° at 10.

- **Tests.** Tier 0 (primitives) and Tier 2 (derived math) are pure closed-form math
  (must never fail); Tier 1 pins the date/time resolver, sun-state, and weather-leaf wiring; Tiers 3–5 drive
  the real mission and assert structural invariants as *indicators* that the math is sound.
  **Tier 2 needed no rebasing for J-4** — those tests check `route_duration_min` in closed
  form rather than asserting the default mission's N, which is exactly what the tiering was
  for. The J-4/J-4.5 additions live in Tier 3 (`test_4_grid_assembly.py`: both budget
  assertions, the retry-convergence probe, the boat-launch science gain and bearing swing)
  and Tier 4 (`test_5_classification.py`: bearings reach the plan, are measured on the final
  route, and track the M1 reciprocal from shore).
- **Known defects and deferred items:**
  - ✅ ~~The budget and the reported duration exclude the transit legs.~~ **Fixed in J-4.**
  - ✅ ~~Launch/land constants are stale.~~ **Fixed in J-1.** The *waypoint names* in
    `planner.py` are still `Seymour-Beach-Launch` / `Seymour-Road-Land` and reach the KML
    labels — cosmetic, fix in J-8.
  - ✅ ~~Along-track overlap does not exist.~~ **Built in J-2/J-3.** `Sensor` carries
    `cross_track_overlap` and `along_track_overlap` separately;
    `metrics["camera_trigger_distance_m"]` is **280.74 m** (561.48 m footprint × 50%) and
    reaches the plan. `ground_footprint_along_m` finally has a caller.
  - 🔴 **`Vehicle` is never instantiated.** `planner._Black_Swift` is a plain `Aircraft`, so
    `plan.aircraft` has no `is_VTOL`, `vehicle_type`, `firmware_type` or `hover_speed_ms`.
    **This blocks J-5** — the writer branches on all four. See the J-5 prerequisite.
  - **Grid sizing is budget-derived, not requested.** `geo._initial_total_lines_from_budget`
    picks N from the endurance budget. `V1_DEFAULT_GRID_WIDTH_km`,
    `V1_DEFAULT_LINE_LENGTH_km` and `V1_DEFAULT_LINE_SPACING_km` are declared but never
    read. They were removal candidates; under **Step F they are reinstated** as the defaults
    behind user-settable dimensions. Do not delete them.
  - **Climb and descent are still unmodeled.** The whole route is costed at cruise speed
    with zero vertical time, which J-4 did not change — it made the *horizontal* distance
    honest, nothing more. At 609.6 m that is ~3 min of climb and ~5.6 min of descent counted
    as zero, against a 17.1 min margin. Scoped into Step G.
  - **Parallax is reported, and only half-corrected.** The line extension is live; the
    crab-shear term is cancelled per constraint 4.

## V2 roadmap — what comes next

**Execution order as of 2026-09-08: `J` → `F` → `G` → `C-2 (re-scoped)` → `D` → `E`.**
Nothing but **J** is active. Letters record the order steps were *scoped*, not the order
they are *built* — the same convention the `V1_` constant prefixes follow.

The original through-line was "make the mission situation-aware, fold that into ranking,
then gate for legality." Constraint 4 retires the gating half of that: the aircraft
compensates for wind in flight, so the engine's job is to **describe** conditions
accurately, not to veto or re-steer on them. The new through-line is **make the engine
configurable and its output machine-usable, and report honestly.** Preserve dumb
unidirectionality throughout.

### J. JSON `.plan` output — CURRENT AND EXCLUSIVE PRIORITY
A `.plan` (JSON) writer, so a plan can be uploaded and flown instead of merely looked at.
`constants.EXTENSION_JSON` already exists and `outputs.write_kml`'s docstring already names
the intended helper (`write_qgc_plan`). Today's KML is **visualization only** in QGC — it
does not import as a flyable mission — which is the entire reason this jumped the queue.
**No other roadmap step may start until this ships.**

> **STATUS 2026-09-17 — J-0 through J-4.5 are DONE, 71 tests green.** The engine produces
> a correct, honest, fully-populated `CandidatePlan`; what is missing is the serializer.
> **J-5 is the next step and the only substantial one left.** Everything below marked
> "settled" or "done" is history — read it for the reasoning, not as work to do.

**Scoping settled 2026-09-08:**
- **Two consumers.** QGroundControl driving **PX4** (custom rotorcraft), and BlackSwift's
  **FMS** taking BlackSwift vehicles as-is. Whether literal fields (`firmwareType`,
  `vehicleType`) matter to the FMS is unconfirmed — cross that bridge if reached.
- **Plain waypoint list (`SimpleItem`), never a survey/`ComplexItem`.** A survey block
  lets the GCS regenerate the lawnmower from its own parameters, which would **discard the
  sun-oriented geometry this engine exists to compute**. The waypoint list preserves
  exactly what was planned. This is the single most important format decision in J.
- **Camera control is automated into the file** — reduce RPIC workload. Use
  **distance-based triggering**, not time-based. Beyond the usual reason, distance
  triggering is **wind-immune**: ground spacing holds no matter what wind does to ground
  speed, so the along-track overlap survives conditions the engine deliberately no longer
  models (constraint 4). Time-based triggering would silently stretch and compress the
  overlap leg by leg.
- **Home position** = the Terrace Point launch/land coordinate.

**The structural fact of J — waypoints expand 1→N.** Camera control is a *separate mission
item*, not an attribute of a waypoint, so one `Waypoint` can emit two items. Consequences:
- `doJumpId` must be assigned **while building the item list**, never taken from
  `Waypoint.waypoint_ID`. The existing `WP001` / `WP000` / `WP_END` scheme is for humans
  and KML and will not line up with item indices.
- Item count is roughly `5N + 2N + 2` (nav points, camera toggles, takeoff/land).

| waypoint action | items emitted |
|---|---|
| `launch` | takeoff item for the vehicle class |
| `turn`, `transit`, `line_label`, `m1_overflight` | nav waypoint |
| `collect_start` | nav waypoint **+** set trigger distance = *d* |
| `collect_stop` | nav waypoint **+** set trigger distance = 0 |
| `land` | land item for the vehicle class |

**Build once, serialize per dialect.** `_plan_items(plan)` produces a vehicle-neutral item
list — the engine's truth — and `_serialize_qgc(items, plan)` renders it. A future
`_serialize_blackswift(...)` is then a sibling, not a rewrite. This split is what keeps the
two-consumer requirement from becoming a fork.

**Two slices of later steps were pulled forward, because J cannot emit a correct file
without them. Both are BUILT as of J-2/J-3:**
- ✅ *From G:* the **vehicle class**, built as `Vehicle(Aircraft)` rather than as a field on
  `Aircraft` — it carries `vehicle_type`, `firmware_type`, `is_VTOL` and `hover_speed_ms`.
  Same move `Sensor.mounting` already makes: record the assumption as data on the object
  instead of burying it in a formula. **Neither class in use today needs a transition
  altitude** (the S2 is a pure fixed wing; custom vehicles are pure rotorcraft);
  `TRANSITION_REL_m = 50` is provisional, applies to the VTOL class only, and that class has
  no instance. ⚠️ **The class exists but nothing constructs one** — see the J-5 prerequisite.
- ✅ *From F:* the **along-track overlap** on `Sensor`, because distance triggering needs a
  spacing. `Sensor` now carries `cross_track_overlap` and `along_track_overlap` separately,
  and `geo.ground_footprint_along_m` finally has a caller. Measured: footprint **561.48 m**,
  spacing = footprint × (1 − overlap) = **280.74 m at 50%** = one frame every 15.6 s at
  cruise, carried as `metrics["camera_trigger_distance_m"]`.
  ⚠️ **`geo` takes both as parameters and reads neither from `constants`** — the same
  contract `cross_track_fov_deg` already had. Step F makes them user-settable, and a
  `Sensor` read inside `geo` would be silently ignored.

**Where the numbers come from — follow the existing metrics path.** `geo` already computes
`sensor_parallax_m` and `cross_track_swath_m` during grid assembly and they ride the metrics
dict into `set_grid_metrics`. Along-track footprint and trigger distance go the same way. No
new plumbing, and `outputs` stays a black box rendering what the plan carries — a third
sibling to `write_kml` / `write_png`, not a new decision layer.

**✅ THE TRANSIT FIX — SHIPPED IN J-4** (scoped 2026-09-08, built 2026-09-17). A `.plan` is
machine-consumed — unlike a KML that a human eyeballs, this file gets uploaded and flown —
so the engine may not ship its first flyable artifact on a budget that omits a third of the
flight. Implementation detail is in
[Current state](#current-state--what-the-engine-actually-does-context-for-future-work);
what follows is the measurement, kept because re-deriving it is expensive.

Measured from Terrace Point: **22,386 m to M1**, bearing 169.6°, round-trip transit
**44.8 km ≈ 41.5 min of a 90 min battery**, barely varying with grid size (45,239 m at N=15
vs. 44,800 m at N=3) because M1 dominates. The old engine emitted **N=15 = 127,559 m =
120.4 min**, thirty minutes past the battery, and printed +11.4 min of margin. Now:

```
usable (15% reserve)      82,620 m
seed transit 2·d(L,M1)    44,773 m   ->  grid budget 37,847 m
geo picks                 N=9, grid 32,343 m
true transit (entry 21,952 + exit 23,001)  44,953 m   [seed error +180 m, +0.40%]
TOTAL FLIGHT              77,296 m  |  72.9 min  |  margin 17.1 min   FITS
```

- **A sizing correction, NOT a gate.** This is the distinction that keeps it consistent with
  constraint 4, and it is worth restating because the two look alike. Wind and RTH reason
  about *conditions* the aircraft compensates for in flight — hence cancelled. Transit
  distance is *geometry*, known exactly at plan time, and **no onboard sensor makes a route
  shorter**. J-4 changed which number `geo` is handed; it rejects nothing. The open Step E
  question (does endurance feasibility become a gate?) is separate and unprejudiced by it.
- **Tier 2 duration expectations did NOT shift** — the earlier prediction that they would
  was wrong. Those tests check `route_duration_min` in closed form rather than asserting the
  default mission's N, so the tiering absorbed the change.
- **"or a stationary boat" is the escape hatch, and it is now measurable.** A launch 2 km
  from M1 yields **N=13 instead of N=9**, pinned by a Tier 3 test. Transit is **54% of the
  battery** before a single science line is flown. That reframes Step F from partner
  convenience into the largest efficiency lever the engine has.

**✅ LAUNCH AND RECOVERY — SETTLED, AND SIMPLER THAN FEARED** (decided 2026-09-08).
The S2 **launches from a stand** and **lands on its belly at a very low stall speed with
steep descent capability**, which is precisely why Terrace Point works as a single pad. So:
- **`geo` needs no approach geometry.** J-5 emits a plain land item at the pad coordinate.
  No landing pattern, no loiter-to-alt, no new geometry anywhere.
- **The approach direction is a RECOMMENDATION to the RPIC**, derived from the wind math and
  delivered in the pilot-notes PDF — never baked into the `.plan`. This is constraint 4
  applied to landing: the engine computes and advises, the pilot decides. **The RPIC can
  always take manual control of the landing, as with any QGC plan.**
- **⚠️ The `.plan` still encodes an approach direction implicitly**, and as of **J-4.5 the
  engine now computes and carries it** — `plan.approach_bearing_deg` = **344.6°**,
  `plan.departure_bearing_deg` = **174.8°**. A *fact of the geometry*, not a wind decision,
  and the RPIC must be told it. This gives the pilot-notes document its **first genuinely
  operational customer**: compare the arrival bearing against the into-wind heading and
  state the headwind/crosswind/tailwind component the pilot will meet. A belly-landing
  airframe on a tailwind approach is exactly the case worth warning about. Details and
  caveats in [Current state](#current-state--what-the-engine-actually-does-context-for-future-work).
- The **launch item's altitude** is a climb-out altitude, not the 609.6 m mission altitude
  the launch waypoint carries. Set in J-1 as `TAKEOFF_REL_m = 50` (relative frame), with
  `LANDING_REL_m = 0` for the land item.

**Step table:**

| Step | File | Work | State |
|---|---|---|---|
| J-0 | — | Pin schema against the field list; confirm takeoff/land commands per vehicle class | ✅ |
| J-1 | `constants.py` | Terrace Point coords (launch = land); along-track overlap; climb-out altitude (`TAKEOFF_REL_m`); per-command param constants in `[2,3,16,21,22,84,85,206]` order; schema literals | ✅ |
| J-2 | `objects.py` | `Vehicle(Aircraft)` with MAVLink identity; `Sensor` split into cross/along-track overlap; `CandidatePlan` trigger-distance + total-flight-distance fields | ✅ |
| J-3 | `geo.py` | Trigger distance into the metrics dict (along-track FOV/overlap passed as **parameters**, not read from `constants`); `total_route_distance_m` → `total_grid_distance_m` | ✅ |
| J-4 | `planner.py` | Reserve the transit before `geo` sizes anything; measure the true transit; bounded retry; duration from the total; `grid_budget_m` vs `usable_endurance_distance_m` split | ✅ |
| J-4.5 | `planner.py`, `objects.py` | Departure + approach bearings measured on the **final** route, reporting only | ✅ |
| J-5 | `outputs.py` | `_plan_items` → `_serialize_qgc` → `write_qgc_plan`; plain land item at the pad | ❌ **NEXT** |
| J-6 | `flight_plan_maker.py` | Emit and report the `.plan` path; print grid/transit split and bearings | ❌ |
| J-7 | `tests/test_6_outputs.py` | Item ordering, camera toggles paired, monotonic `doJumpId`, per-class frames, home position | ❌ |
| J-8 | docs | Closeout; fix the stale `Seymour-*` waypoint names | ❌ |

**⚠️ J-5 HAS A PREREQUISITE — `Vehicle` is never instantiated.** `planner._Black_Swift` is
a plain `Aircraft`, so `plan.aircraft` has **no** `is_VTOL`, `vehicle_type`, `firmware_type`
or `hover_speed_ms` — and `_serialize_qgc` needs all four. J-2 built the class and nothing
adopted it. Do this first:
- Add `BLACKSWIFT_VEHICLE_TYPE = 1` (Fixed Wing) and `BLACKSWIFT_FIRMWARE_TYPE = 12` (PX4)
  to `constants.py`; there are no such constants today.
- Change `_Black_Swift = Aircraft(...)` to `Vehicle(...)` with those two arguments.
- `Vehicle.__init__` **raises** on an invalid vehicle type and **warns + defaults to PX4**
  on an invalid firmware type, so a typo fails loudly rather than writing a bad file.
- Add a Tier 1 or Tier 3 assertion that the default plan's aircraft *is* a `Vehicle` — the
  gap survived three steps precisely because nothing checked.

**The last open decision in J: which landing item.** `exp2.plan` expresses its fixed-wing
landing as a **`ComplexItem` of `complexItemType: "fwLandingPattern"`** — with
`landingApproachCoordinate`, `loiterRadius: 75`, `loiterClockwise`, `finalApproachSpeed`
and `stopTakingPhotos` — not as a `NAV_LAND` SimpleItem.
**Recommendation: plain `NAV_LAND` (21).** The S2 belly-lands with steep descent capability
and needs no loiter pattern; `fwLandingPattern` would force the engine to invent an approach
coordinate and loiter geometry, which is exactly the work the roadmap settled it would not
do, and its `stopTakingPhotos` flag overlaps our explicit camera items. Note the "never a
`ComplexItem`" rule was aimed at **survey** blocks, which regenerate and therefore destroy
the sun-oriented grid — a landing pattern destroys nothing, so that rule does not by itself
bar this if a partner later requires it.

**Follows J, lower priority:** the **PDF pilot-notes document** from constraint 4 — the
wind / crab / return-time reporting, deliberately kept out of the machine-readable outputs.
Its first operational customer is already known and now computed: the **recommended landing
approach**, comparing `plan.approach_bearing_deg` against the into-wind heading. That is
also the first time any of C-2's wind math will have done real work for anybody.

### What `exp2.plan` settles

`exp2.plan` in the repo root is a **real QGroundControl export for this site** and the only
ground truth available for the format. Read it before writing the serializer. What it
resolves:

**Frames are NOT uniform, and this is the easiest thing in J-5 to get wrong:**

| item | `frame` | `AltitudeMode` | altitude |
|---|---|---|---|
| takeoff / land | 3 (relative) | 1 | `TAKEOFF_REL_m` 50 / `LANDING_REL_m` 0 |
| cruise nav | 0 (AMSL) | 2 | 609.6 |
| DO camera | 2 (mission) | — | 0 |

An earlier revision of the planning notes said "every nav item carries frame 3". **That is
wrong.** Cruise waypoints are `frame 0` / `AltitudeMode 2`. This *is* the mixed-datum
decision expressed per item, and it is why `globalPlanAltitudeMode = 0` (Mixed).

The rest:

- **QGC writes keys alphabetically sorted with 4-space indent** —
  `json.dump(obj, f, indent=4, sort_keys=True)` reproduces it closely, which makes a diff
  against a QGC re-export readable.
- **Both `cruiseSpeed` and `hoverSpeed` are always present**, even on a fixed wing (15 and
  5). Write both; the vehicle class decides which the aircraft honours. Simpler than
  branching, and it matches what QGC produces.
- **`AMSLAltAboveTerrain` is `null` on every item**, and cruise `params[3]` (yaw) is `null`.
  Both confirmed, both required.
- **Two divergences from `constants.py`**, flagged not changed — these are QGC constants and
  therefore user territory:
  - QGC writes `0` for takeoff yaw where `TAKEOFF_YAW_deg = None` would emit `null`.
  - QGC writes `0` for acceptance radius where `ACCEPTANCE_RADIUS_m = 28.5`. `0` means "use
    the vehicle default"; 28.5 m is a deliberate override tied to the S2 turn radius. Valid
    either way, but a round-trip diff will show it — expected, not a bug.
- **No `DO_SET_CAM_TRIGG_DIST` items appear in it**, so the camera half of our output has no
  reference. **Round-trip the first file J-5 produces**: load into QGC, re-export, diff.
  Anything QGC rewrites is something we got wrong.

### F. Mission configurability (SIDELINED)
Per constraint 2, the user sets: line length, grid width, center point, launch point,
landing point, desired grid area (honoured **when mathematically feasible**, otherwise
reported as infeasible with the closest achievable), cross-track overlap %, along-track
overlap %, and camera off-nadir viewing angle.
- **This dissolves three current invariants.** The grid is no longer necessarily
  M1-centered; the M1 overflight is no longer necessarily required; and grid size is no
  longer necessarily derived from the endurance budget. `geo.make_lawnmower_grid_through_m1`,
  `_initial_total_lines_from_budget`, and the odd-N parity rule all assume otherwise. The
  odd-N rule exists to put the center line through M1 — with a configurable center it
  generalises to "center-point overflight" and should stay, but as a *default*.
- **Requested-vs-derived sizing is a real design fork.** Today N falls out of the budget.
  With a requested area/length/width, the budget becomes a **feasibility check** on a
  requested grid rather than the source of its dimensions. Both modes need to coexist
  ("fill my endurance" vs. "cover this box").
- The three unread constants (`V1_DEFAULT_GRID_WIDTH_km`, `V1_DEFAULT_LINE_LENGTH_km`,
  `V1_DEFAULT_LINE_SPACING_km`) become the defaults behind these inputs.
- ✅ **Along-track overlap already exists** — J-3 pulled it forward. `Sensor` carries both
  overlaps, `geo` takes both as parameters, and the trigger distance rides the metrics dict.
  F only has to make them *user-settable*; the physics is done.
- **The launch point is the highest-value knob, not a convenience.** J-4 made the cost
  visible: transit is **54% of the battery** from Terrace Point, and a launch 2 km from M1
  takes the mission from N=9 to N=13. Whatever the delivery mechanism, launch/land coordinates
  should be first-class.
- Delivery mechanism (CLI flags vs. a mission config file) is undecided. The flag list is
  already at four and this adds ~9 more, which argues for a config file.

### G. Aircraft configurability (SIDELINED)
Per constraint 3. Fixed-wing, quadcopter, or hexacopter, with every fixed-wing performance
constant user-settable rather than hard-coded to the BlackSwift S2.
- `objects.Aircraft` is already a general constructor — the hard-coding lives in
  `planner._Black_Swift`, a module-level singleton built from `BLACKSWIFT_*` constants.
  That singleton is what has to go. J-4 already removed the *reach-ins* to it from inside
  `build_candidate_plan`, so the function now works from its parameters — deleting the
  singleton is a smaller job than it was.
- ✅ **Step J pulled the vehicle *class* forward** as `Vehicle(Aircraft)` (fixed wing /
  multirotor / VTOL), because takeoff and land commands differ per class. G inherits the
  rest: the performance numbers.
- Multirotor is **not** just different numbers. `aircraft_math` assumes forward flight
  (cruise speed, turn penalty, turn radius); a multirotor hovers, turns in place, and has a
  materially different endurance-vs-speed curve. `geo`'s turn geometry and
  `route_duration_min`'s turn-penalty model both need a multirotor branch. Scope after the
  fixed-wing config lands, per the user.
- **Climb and descent are unmodeled — and this is now the largest remaining optimism in the
  duration.** `Aircraft` carries climb 3.35 m/s and descent 1.80 m/s and `route_duration_min`
  uses neither; the whole route is flown at cruise with zero vertical time. A full-altitude
  vertical profile at 609.6 m would be ~3 min up and ~5.6 min down. The real fixed-wing
  profile climbs in forward flight so it is less than that, but it is not zero — and it is
  now being compared against a **17.1 min margin** rather than an imaginary one. J-4 made
  the horizontal distance honest and nothing more; do not read the new margin as slack until
  this is modelled.
- **Vehicle facts:** the S2 is a **pure fixed wing** (no VTOL, no transition altitude); the
  tri-motor VTOL **S3 is not an option**, its only airframe having been destroyed in company
  testing; custom partner vehicles are essentially always **rotorcraft** on PX4/QGC. Nothing
  is ever hand-launched.

### A. Selectable mission date/time ✅ DONE
`flight_plan_maker` exposes `--date YYYY-MM-DD` / `--time HH:MM` (**Monterey local**, each
optional). `sun.resolve_mission_datetime` fills missing halves from the V2 defaults
(`V2_DEFAULT_MISSION_LOCAL_HOUR/MINUTE`, `V1_DEFAULT_MISSION_{YEAR,MONTH,DAY_OF_MONTH}`),
attaches `V2_MISSION_INPUT_TIMEZONE` (`America/Los_Angeles`, DST-aware) and converts to a
tz-aware UTC instant; module-level `sun.mission_datetime` is the default when no flags are
given. `planner.plan_default_mission(name, mission_datetime=None)` → `_build_dated_objects`
builds the sun state / mission request / weather per run, so sun azimuth (and glint)
track the chosen time.
- The old latent bug is fixed: `create_sun_state` now stores `CurrentSunState`'s
  day/hour/minute from the passed `date`, not the constants.
- Input handling is **lenient**: unparseable `--date`/`--time` silently falls back to the
  defaults (the try/except catches both `ValueError` and `TypeError` — `TypeError` is what
  `date.fromisoformat(None)` raises when a flag is omitted). Switch to hard-reject later if
  strict validation is wanted.

### B. Weather integration ✅ DONE
`weather.py` is a **leaf** the hub orchestrates: `weather.get_weather(lat, lon, when)` returns
a `Weather` populated from live NWS data, or `None` (out of forecast horizon, or any
network/parse failure); `planner._build_dated_objects` falls back to the clear-sky /
zero-wind stub on `None`, so a plan is always produced. The leaf never reaches back into the hub.
- **NWS (no API key; `User-Agent` required — `constants.NWS_USER_AGENT`).** Two-call flow:
  `GET /points/{lat},{lon}` → `properties.forecastGridData` URL (launch point = office **MTR**,
  grid **91,52**), then `GET` that gridpoint doc. Fields are time-series with a `uom`:
  `skyCover` (percent), `windSpeed`/`windGust` (**km/h — `_to_ms` ÷3.6 → m/s**),
  `windDirection` (deg). `visibility` (metres) is **sometimes absent** → `get_weather` fills
  `DEFAULT_VISIBILITY_m`. `_value_at_time` picks the latest interval whose `validTime` start ≤ T
  (no duration parsing).
- `_within_forecast_horizon` short-circuits any datetime outside `[now, now+7d]` to the stub
  **with no network call** (forecasts cover ~7 days from *now*).
- `_condition_from_skycover` maps `skyCover` → `"clear"` / `"partly cloudy"` / `"overcast"`
  via `CLEAR_SKY_THRESHOLD_PERCENTAGE` / `OVERCAST_SKY_THRESHOLD_PERCENTAGE`.
- Tests: `tests/test_3_weather.py` (offline; fetch monkeypatched) + a Tier 4 check that the
  planner uses the leaf's populated result.

### C-1. Along-track payload mount ✅ DONE
The SST camera was remounted: **yawed to face forward under the nose and pitched to 30°
off-nadir**, replacing the cross-track roll at 40°. See the C-1 bullet in
[Current state](#current-state--what-the-engine-actually-does-context-for-future-work)
for what that changed and why the two FOV formulas traded places.
- Target relative azimuth moved 135° → **90°** (`SCIENCE_RELATIVE_AZIMUTH_deg`), tolerance
  **held at 15°**. Also raised in the same pass: altitude → 609.6 m (2000 ft), overlap → 50%.
- Both leg directions now collect, which made the old **SCIENCE/TRANSIT OFFSET CORRECTION**
  block in `geo.py` obsolete — its premise (only alternate lines collect) is dead, so
  `offset_m` as computed is already correct. It was **deleted**, not deferred.
- `geo.sensor_parallax_m` added; `Sensor.mounting` added and guarded in `planner`.

### C-2. Boresight + wind REPORTING ⏳ RE-SCOPED 2026-09-08 (SIDELINED)

> **What changed.** C-2 was scoped as *boresight referencing + an RTH safety gate*.
> Constraint 4 cancels the gate. Onboard wind sensing plus in-flight compensation is now
> assumed on every aircraft, so the engine must **never** reject a plan or rotate a grid
> because of wind. C-2 is reduced to **math + reporting**, and what it reports goes into a
> **separate pilot-notes document**, not into the `.kml` / `.png` / `.json`.
>
> This is a cancellation, not a deferral. Do not resurrect `_rth_safe_budget`,
> `_evaluate_boresight` as a gate, or the wind-derived reserve loop.

**Step status — steps 1–4 built, and now that is most of what C-2 needs.**

| Step | What | State |
|---|---|---|
| 1 | `constants.py` — six RTH constants; `V1_EMERGENCY_RESERVE_FRACTION` retired to a seed | ✅ done (several now unused — see below) |
| 2 | `objects.py` / `weather.py` — `wind_direction`/`visibility` getters, `wind_is_measured`, `stale_fields`, C-2 plan setters | ✅ done |
| 3 | `aircraft_math.py` — wind triangle, `return_time_min`, derived reserve | ✅ done + tested |
| 3.5 | `weather.py` — `_value_at_time` honours interval duration; per-field staleness | ✅ done + tested |
| 4 | `geo.py` — parallax line extension, `furthest_point_distance_m` | ✅ done |
| ~~5~~ | ~~`planner._rth_safe_budget`, `_evaluate_boresight`, budget wiring~~ | ❌ **CANCELLED — plan-altering** |
| ~~6~~ | ~~`validator.py` RTH / crosswind gate~~ | ❌ **CANCELLED — gating** |
| **5′** | **pilot-notes document: crab, boresight error, ground speeds, worst-case return, crosswind headroom** | ❌ not started |
| 6′ | `planner` calls the wind math for **reporting only** and populates the C-2 setters | ❌ not started |
| 7 | Tier 4+ tests that the reported numbers reach the notes document | ❌ not started |
| 8 | docs | ⏳ this section |

**What is LIVE vs INERT.** Step 4's parallax extension is inside
`make_lawnmower_grid_through_m1`, so it changes every plan today (+808 m per line; grid
distance 82,320 m). **Everything else built in C-2 has zero callers**:
`wind_correction_angle_deg`, `ground_speed_ms`, `effective_lawnmower_speed_ms`,
`return_time_min`, `required_reserve_time_min`, `wind_aware_usable_distance_m`,
`max_crosswind_tolerance_ms`, `cross_wind_component_ms`, `head_wind_component_ms`,
`furthest_point_distance_m`. `Weather.wind_is_measured` and `.stale_fields` are populated
and read by nobody. `route_duration_min` accepts `weather`/`axis_deg` but `planner` calls
it with three arguments, so duration is still-air.

**None of that math is wasted — its destination changed.** It was built to *decide*; it
now exists to *inform the RPIC*. The functions themselves are correct and stay. What dies
is the branch that would have shrunk a grid or refused a plan.

**Constants left stranded by the re-scope.** `RTH_SAFETY_FACTOR`, `RTH_TERMINAL_ALLOWANCE_min`,
`MANUAL_RTH_MAX_CROSSWIND_ms`, `RTH_INCLUDES_GLIDE`, `RTH_SEED_RESERVE_FRACTION` and
`RTH_MAX_ITERATIONS` were sized for the cancelled gate. `RTH_SEED_RESERVE_FRACTION` is
still read (it is the reserve the budget uses); the rest are now reporting inputs at best.
Decide their fate when C-2 resumes — **do not delete them before then**, the reasoning
behind each is recorded in `constants.py` and in the 2026-08-19 log entry.

**The boresight geometry still holds and is still worth reporting.** The 90° ± 15 is
measured on the camera **boresight** — the fuselage heading, not the ground track — so
crab moves the imaged geometry even though it no longer moves the plan.
- **The closed form:** flying ground track χ, the outbound heading is χ+δ and the return is
  χ−δ (**not** reciprocal — they differ from reciprocal by 2δ). Putting the grid axis exactly
  on the target lands the two directions at **+δ and −δ**, so worst-case error is exactly δ.
  Rotating the axis to chase a smaller δ **provably never helps** (|dδ/dα| ≤ w/V < 1), so
  α = 0 is always optimal. Under constraint 4 this stops being an argument for *not
  rotating* and becomes simply the *reported* error.
- `|δ| ≤ 15°` ⟺ crosswind across the science axis ≤ `V·sin(15°)` ≈ **4.66 m/s** at S2
  cruise. Report it as **science-quality headroom** for the RPIC, never as a gate.
- `cross_track_strip_offset_m = parallax · sin(crab)` — report, do not correct.

### D. Fold weather into scoring (SIDELINED, NARROWED)
`planner._score_glint` is still the **only** ranking metric. Constraint 4 removes wind from
this step entirely — wind is neither a preference nor a gate — so D narrows to
**sun-and-data-quality** factors:
- Date/time (A) already varies the sun azimuth feeding glint.
- Cloud cover is the surviving weather input: overcast diffuses sunlight, so glint matters
  less. That is a genuine data-quality signal and belongs in ranking.
- **Removed from D:** the wind-rating feasibility gate and any wind term in ranking.
  Visibility/VLOS moves to E (legality), where it always belonged.
- `aircraft_math.route_duration_min` still uses cruise **airspeed** for the whole route.
  Wind-aware duration is now a **reporting** improvement, not a planning one — the wind
  path in that function already exists and is unused.

### E. `validator.py` — legality/feasibility gating (SIDELINED AND NARROWED)
`validator.py` holds only a docstring, and that docstring describes the **cancelled** RTH
gate — read it as history. What remains for E:
- **Legality** — Part 107 and friends: **altitude ceiling** (the default is 609.6 m /
  2000 ft; COA authorization is in progress with partners and may go **higher**, so gate on
  the ceiling the mission is *authorized* for, never a hard-coded 400 ft);
  **daylight / civil twilight** (use `CurrentSunState.elevation`); **VLOS**; **airspace
  authorization**; **over-water operations**.
- **⚠️ OPEN DECISION — does battery/endurance feasibility stay a gate?** Constraint 4
  removes *weather-driven* gating, and the user's stated priority is that "legality and
  safety are still our priority." A route longer than the battery is not a weather problem
  and no onboard sensor fixes it. Until this is decided, treat endurance feasibility as
  **unresolved**, not as cancelled.
- **J-4 narrowed this question without answering it.** The engine now *sizes* the grid so
  the route fits the battery, which removes the everyday case E would have caught. What is
  left for E is the case sizing cannot reach: a **user-requested** grid under Step F that
  does not fit, where the engine must either refuse or report-and-proceed. That is a
  genuinely different decision from the one that was open before, and a smaller one.
- Wiring, if E stays a gate: `planner` builds a candidate → `validator` gates it → only
  valid plans reach `outputs`. Keep `validator` a leaf. `CandidatePlan` already carries
  `_is_legal`, `_is_aircraft_feasible`, `_validation_messages`, `_passes_over_m1`.
- The **re-derive rule** in the existing docstring survives any re-scope: a validator that
  reads back what the planner stored is checking the builder's arithmetic against itself.

## Notes

- Target Python 3.12+ (developed/tested on 3.14.4). `itertools.batched` (used in
  `planner._classify_waypoints`) requires 3.12.
- V1 was a proof-of-engine build (fixed aircraft, clear skies, fixed date/time, assumed
  legal-to-fly, glint-only ranking). V2 replaces those one at a time: **Steps A (date/time),
  B (live NWS weather) and C-1 (along-track mount) are done**. Remaining, in execution
  order: **J** (JSON output — active, J-0…J-4.5 done, **J-5 next**), **F** (mission
  configurability), **G** (aircraft configurability), **C-2 re-scoped** (wind reporting),
  **D** (sun/cloud ranking), **E** (legality).
- Many constants still carry `V1_` prefixes but hold V2 values (e.g.
  `V1_DEFAULT_SENSOR_OFF_NADIR_deg` is 30, the V2C angle). The prefix records where the
  constant was introduced, not which version's value it holds — don't infer currency from it.
  **Roadmap letters work the same way** — they record scoping order, not build order.
- **When a doc and a measurement disagree, measure.** Several numbers in these docs
  (route distance, margin, N) were verified by instrumenting the engine on 2026-09-08 and
  re-verified on 2026-09-17, and one long-standing claim — that `total_route_distance_m` is
  the route — turned out to be false. Re-measure before trusting a figure that predates a
  geometry change. Two 2026-09-17 examples of this rule paying off, both of which would have
  been baked into tests otherwise:
  - The approach bearing was briefly recorded as 354.8°. That was measured on the raw grid
    endpoint **before** `_reorient_to_launch`; on the final route it is 344.6°, and the older
    docs were right.
  - The planning notes said "every nav item carries frame 3". `exp2.plan` shows cruise
    waypoints at `frame 0` / `AltitudeMode 2`.
- **A quiet success deserves the same note as a defect.** The prediction that J-4 would force
  every Tier 2 duration expectation to be rebased was **wrong** — those tests assert
  closed-form math rather than the default mission's N, so the change passed straight
  through. That is the tiered harness doing exactly what it was designed for; preserve the
  property when adding tests (**assert relationships in N, not literals**).
