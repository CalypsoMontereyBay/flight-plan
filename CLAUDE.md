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
- **Pull requests.** I open each PR by hand. Claude's review, appended to the Logs section
  of `claude_prompts/pull_requests.md`, is the PR's description: the reviewer and his agents
  read it there. Write each entry for them. It covers the scope, what merges, what isn't
  built, what's unflown or provisional, the verification, the findings and the merge
  advice.
- **This repo is public.** Never commit third-party files, such as BlackSwift's example
  plans, which are kept locally in the git-ignored `BS_EXAMPLES/`.

## Project overview

Calypso Monterey Bay flight-planning engine. A sun-aware flight planner for uncrewed
aircraft collecting ocean-color / SST data over Monterey Bay. It builds a lawnmower grid
oriented for minimum sun glint (science legs held **90° off the sun**) and exports the
route as `.kml` and `.png`. See [`README.md`](README.md) for the full description.

**V1 (proof-of-engine) is complete and tested. V2 Steps A (selectable date/time), B
(live NWS weather) and C-1 (along-track payload mount) are complete and tested. C-2 is
HALF BUILT and has been RE-SCOPED — it is no longer a gate. Step J (JSON output) is
COMPLETE as of 2026-09-30, Step K (S3 adoption) CLOSED on 2026-11-03, and Step F (mission
and aircraft configurability) is next. Its design was settled with the user on 2026-11-06.
None of it is built, and F-1's functions are agreed with the user before any code.** See
[Operating constraints](#operating-constraints--2026-09-08-supersedes-earlier-scoping) and
the [V2 roadmap](#v2-roadmap--what-comes-next).

**Step J is COMPLETE as of 2026-09-30: J-0 through J-8 are done (94 tests green, also
under `-W error`). Every run writes a QGC `.plan`, and the terminal summary reports the
grid/transit split, both bearings (J-6) and the final-frame RPIC note. 22 Tier 5 tests pin
the file against the MAVLink spec and QGC's own files (J-7). The QGC round trip is clean:
QGC changed one value, a camera-stop parameter, and the engine now writes the same value.
**BlackSwift answered on 2026-10-13: the S2 is end of life, and the S3, a VTOL, is the
default and only non-copter aircraft** (see [BlackSwift response](#blackswift-response--2026-10-13-supersedes-the-s2-vehicle-facts)). The
camera-rollout fast track was BUILT on 2026-10-18 (R-3 to R-7, 104 tests green): every line
leaves 2.5·R_g + 80 m plus the aircraft's early camera start between its turn and the
camera, sized from a design wind the RPIC sets. Its constants came from PX4 flying an S2
model, so they are provisional placeholders for the S3, and the S2 loop sweep that was to
check them is cancelled (warning box item 4).** **Step K CLOSED on 2026-11-03 (120 tests
green).** K-1 to K-4 (2026-10-27) made the S3 the default aircraft, deleted the S2's
constants, paid for the climb, descent and hand-offs, and set every VTOL to transition
10 m above home. K-6 (2026-11-03) put the climb orbit and phase times in the summary and
pilot notes on every plan, including winds above the aircraft's rating and weather that
isn't a forecast. The default plan is 9 lines, 74.3 min, with a 15.7 min margin. **K-5, the
BlackSwift XML writer, was not built** (the user, 2026-11-03): the default aircraft may
change, and no S3-only work is wanted until that is settled. Step F's design, its settings
list and its F-1 to F-7 slicing were settled on 2026-11-06 (see Step F). The two
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
   [Step J](#j-json-plan-output--complete-2026-09-30). ✅ **It landed on 2026-09-30:**
   Step J is complete, and F is next in the execution order.
2. **The mission must become configurable.** Users set line length, grid width, center
   point, launch point, landing point, desired grid area (honoured when mathematically
   feasible), overlap percentage in **both** the along- and cross-track directions, and
   the camera viewing angle. See [Step F](#f-mission-and-aircraft-configurability-next--design-settled-2026-11-06).
   MAVLINK PROTOCOL MUST BE ACCOUNTED FOR (SEE LINK): https://docs.qgroundcontrol.com/master/en/qgc-dev-guide/file_formats/plan.html
3. **The aircraft must become configurable.** Fixed-wing, quadcopter, or hexacopter. For
   a fixed wing every performance constant currently hard-coded to the BlackSwift S2 (the
   S3 since K-3, 2026-10-27) must be user-settable. Multirotor constraints get scoped once the fixed-wing config lands.
   See [Step F](#f-mission-and-aircraft-configurability-next--design-settled-2026-11-06),
   which took in most of Step G on 2026-11-06.
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

**Amended 2026-11-06 (the user, in Step F's design).** Where these differ from items 2 and
3, these win:
- **Item 2:** area is reported, never requested. A grid is requested as line length + grid
  width. The centre is a location, with no overflight required, and a plan can be made
  anywhere on earth.
- **Item 3:** aircraft configuration moves into Step F, multirotors included. The first
  real-world test flies a PX4 VTOL and a hexacopter through QGC.
- **Four requirements for Step F:**
  1. An unflyable plan is never written, and the user is told why.
  2. The CLI and a config file are interchangeable: the same plan made either way gives
     the same output.
  3. AI agents, as well as humans, can make plans.
  4. Every setting is listed before development starts (done: see Step F).

**Default launch/land is now UCSC Coastal Science Campus — Terrace Point** (Santa Cruz,
north shore) at **36.94840 N, 122.06538 W**, and stays that way until re-specified. This is
a standing assumption, not a per-mission choice, even though item 2 also makes it
user-settable. **Launch and land are the SAME point** — the two-waypoint (beach launch /
road land) split from V1 collapses. A boat launch is the exception: BlackSwift advises
launching from a boat and landing on solid ground (2026-10-13).

**Vehicle facts that follow from the constraints** (recorded here because they decide the
takeoff/land commands Step J must emit):
- **~~BlackSwift S2 — pure fixed wing, the default aircraft.~~ End of life (BlackSwift,
  2026-10-13).** K-3 (2026-10-27) removed it from the code.
- **The BlackSwift S3, a tri-motor VTOL, is the default and only non-copter aircraft
  (2026-10-13).** Its only airframe was destroyed in company testing; BlackSwift has since
  changed its PDB, with no change to endurance, electrics or aerodynamics. It takes off and
  lands vertically and transitions at ~10–15 m AGL; the engine sets every VTOL to
  transition 10 m above home (2026-10-27). See
  [BlackSwift response](#blackswift-response--2026-10-13-supersedes-the-s2-vehicle-facts).
- **Custom partner vehicles are essentially always rotorcraft**, flashed with PX4 and
  driven from QGC.
- **No vehicle is ever hand-launched.** Every launch is from land or a **stationary boat**.
  A boat launch near M1 is operationally significant — see the transit note in Step J.

## BlackSwift response — 2026-10-13 (SUPERSEDES the S2 vehicle facts)

BlackSwift answered our questions in a meeting on 2026-10-13. The user's write-up,
`BlackSwift Response Writeup.txt`, is kept locally in the repo root and is git-ignored; the
user removed it from the public repo and its history on 2026-11-03. Where an older section of this file
conflicts with this one, this one wins. Step K replaced the S2 in the code (K-3,
2026-10-27), and the full list of changes, with the reason for each, is in the planning artifact's
"BlackSwift response" section.

- **The S2 is end of life.** It comes out of the engine and the sim. The **S3 is the default
  and only non-copter aircraft.**
- **S3 takeoff: it never flies back over home.** It hovers to ~10–15 m AGL, transitions to
  forward flight, then climbs in an orbit to a **takeoff waypoint** between home and the
  first mission waypoint, at mission altitude. BlackSwift recommends a 300–500 m orbit
  radius, or as large as is legal. It orbits there until the operator starts the mission.
- **Three XML files per plan:** takeoff (home, takeoff waypoint, orbit radius), mission and
  landing. The S3 will not launch without the takeoff and landing files. It orbits after
  the takeoff file and after the last mission waypoint until the operator moves it on.
  There are no automatic transitions and no combined plan (as of 2026-10-13).
- **Example plan files** arrived on 2026-10-14. They are BlackSwift's, so they are kept
  locally in `BS_EXAMPLES/`, which git ignores. The user decided on 2026-11-03 to remove
  them from the repo and its history, because the repo is public. **Still to come by
  email:** the minimum waypoint acceptance radius of BlackSwift's flight management system
  (adjustable within software limits).
- **Landing (question 6, answered by the user 2026-10-27):** the S3 **descends along the
  approach**, transitions to hover 10 m over the pad, and lands vertically. The descent
  costs time only where the approach is too short to hold it.
- **Firmware: nothing like PX4 or ArduPilot** (a cascading closed-loop architecture), and
  BlackSwift simulates in JSBSim, not Gazebo. PX4 SITL results do not describe the S3.
- **Emergency belly landing** is supported, but it may damage the front two motors and the
  non-folding props.
- **Boats:** launch from a boat, and land on solid ground where possible.
- **Payload:** BlackSwift's thermal photogrammetry payload uses a FLIR camera, so a
  hard-mounted Boson-R cannot stand in for it.

**Decided 2026-10-18:** S3 adoption is its own step, **Step K**, built before Step F. Which
camera flies Calypso science on the S3 is **not decided**, so our payload model stays,
marked provisional. The rollout constants stay as provisional S2/PX4 placeholders, and the
S2 Strat 2 loop sweep is **cancelled**. Its prompt was never sent to the sim agent, so there
is nothing to call back.

**Declined (reported 2026-10-27):** BlackSwift will not share its JSBSim S3 model or the
numbers behind it, on IP grounds. No S3 data is coming from BlackSwift to replace the
provisional rollout constants (2.5, 80) or the S2 climb and descent rates, and no S3
simulation of Strat 1 or the Strat 2 loop is planned.

**Test aircraft (the user, 2026-11-06):** the first real-world test of Step F's plans flies a
PX4 VTOL and a hexacopter through QGC. The S3 stays as a built-in aircraft profile that
anchors the regression tests, and its operator hand-offs become a profile field.

**S3 numbers (2026-10-18, from the user):**
- **Given:** endurance 90 min; cruise **21 m/s**; stall speed and wind rating as the S2's;
  best transition at 10–15 m AGL. The waypoint capture distance is 2 × cruise × lookahead,
  with a lookahead of 3.0 (a BlackSwift flight-controller constant), so **126 m**.
- **Derived:** turn radius **77.6 m**, the S2's 30.1° bank flown at 21 m/s (to be confirmed
  with BlackSwift). Turn penalty **0 s**, because fly-by arcs are shorter than the corners
  the engine already counts.
- **Placeholders:** climb and descent are the S2's 3.35 and 1.80 m/s, labelled provisional.
  BlackSwift's limits can't be shared.
- **Max hover speed: 1 m/s** (the user, 2026-10-27, `BLACKSWIFT_S3_MAX_HOVER_SPEED_ms`).
  The S3 isn't designed to travel laterally in hover and almost never does.
- **MAVLink identity (2026-10-27, the user):** vehicle type 21, tilt-rotor VTOL, the more
  precise term for the kind of VTOL the S3 is; firmware 0, generic, because it isn't PX4.

**How the engine treats BlackSwift's example plans (local only, not in the repo):** as the file format,
not as a template. The engine serves many vehicles that BlackSwift doesn't make, and
launch, landing and climb points are chosen for legality and operational feasibility.
- The climb orbit sits on the departure bearing, seaward and clear of the pad, with a
  500 m default radius. F-1's config can override it, and Step E checks it.
- Each operator hand-off gets a small time reserve.

**Measured at the S3 numbers:**
- The default plan returns to 9 lines (96.4 km usable): 74.3 min with a 15.7 min margin
  once K-4 paid for the phases.
- W* drops to 8.84 m/s, under the 9 m/s default, so the two turns between lines no longer fit
  in the 313.4 m line spacing at the default design wind.

> ## ⚠️ READ THIS BEFORE TRUSTING A GENERATED PLAN
>
> A generated plan is a **planning sketch for review**, never a flyable mission. This box
> lists the reasons that still stand. The ones fixed since are recorded below as history,
> because the reasoning is worth keeping and because re-measuring is expensive.
>
> **1. Nothing validates anything yet.** `validator.py` holds a docstring and no code, and
> the engine checks no legality. The RTH/crosswind gate C-2 was scoping is **cancelled**
> (constraint 4). **Decided 2026-11-06:** an unflyable plan (battery, invalid input,
> geometry, legality) will be refused with its reasons, which Step F builds (F-1, F-6).
> Until then, two findings from the 2026-11-06 research stand: a Terrace Point plan climbs
> and descends below 1,000 ft over the Monterey Bay sanctuary's Zone 1, which needs a NOAA
> permit, and a grid reaching ~3 nm southeast of M1 enters Monterey's Class C at 2,000 ft.
> See Step F.
>
> **2. No output has been flown.** We are still deep in the construction and design phase
> of this software and of the actual UAS hardware, and a Gazebo (GZ) simulation for our
> possible vehicle types and plans is under construction. BlackSwift's answers (2026-10-13)
> settle the takeoff question and raise a larger one: the S3 flies three XML files through
> BlackSwift's own flight management system, which the engine does not write (the user did
> not build K-5, 2026-11-03), and its firmware is nothing like PX4, so PX4 SITL and Gazebo
> runs do not describe it.
>
> **3. Climb, descent and hand-offs are modelled with provisional rates** (K-4,
> 2026-10-27). The climb orbit costs 2.9 min and the two hand-offs 2 min. The descent rides
> the approach and costs nothing from the shore. Both rates are the S2's, which BlackSwift
> can't replace, and every vehicle is charged the orbit climb and the hand-offs, which
> over-counts for a vehicle that climbs on its way out.
>
> **4. The camera-rollout fix is built, with provisional constants** (2026-10-18). Every
> line now leaves a collection inset of 2.5·R_g + 80 m plus the aircraft's early camera
> start (the S3's 126 m capture distance, or PX4's 70 m) between its turn waypoint and the
> camera, 601.9 m for the S3 at the 9 m/s default design wind, and line 1's first turn moves back for
> the turn in from the transit (Strat 1). The constants were calibrated on PX4 SITL flying
> an S2 model. The S2 is end of life and the S3's firmware is nothing like PX4, so they are
> **provisional placeholders** for the S3, and the S2 sweep that was to check them is
> cancelled. On a day windier than the design wind the downwind lines' first images are
> banked again. The RPIC sets the
> design wind per plan (`--design-wind`, m/s at flight altitude). See the Known defects
> entry.
>
> **5. Today's `.plan` is not ready for a PX4 VTOL or a hexacopter** (read from PX4's
> source on 2026-11-06; nothing flown). The VTOL takeoff item sits on the pad, so PX4's
> transition heading is undefined and the mission can abort. VTOL land back-transitions at
> the last waypoint's altitude, ~594 m up, and hovers down for ~6.6 min the budget doesn't
> count. A hexacopter flies PX4's 5 m/s default with no speed item, cuts every corner by the
> 28.5 m acceptance radius, and descends vertically from ~594 m to land. The climb orbit and
> hand-offs K-4 charges don't exist in a QGC mission. Camera triggering needs `TRIG_MODE=4`
> set on the vehicle. Step F-2 fixes the plan side.
>
> ### ✅ FIXED — kept as history, do not re-diagnose
>
> **~~The distance budget ignores the transit legs.~~ Fixed in J-4.** `geo` was handed the
> entire 82,620 m budget and allowed to size a grid that consumed all of it, so nothing
> paid for the 44.8 km round trip to M1. The engine emitted **N=15 = 127,559 m = 120.4 min
> against a 90 min battery, and printed +11.4 min of margin.** `planner` now reserves the
> transit before `geo` chooses N. The default mission after J-4 was **N=9 / 77,296 m /
> 72.9 min / 17.1 min margin**; the rollout fix (2026-10-18) takes it to **N=7 / 71,630 m /
> 67.3 min / 22.7 min margin**, and the S3 with its takeoff and landing phases (K-4) to
> **N=9 / 87,460 m / 74.3 min / 15.7 min margin**. See the J step table in the roadmap.
>
> **~~The launch point in `constants.py` is stale.~~ Fixed in J-1.** The constants held
> the south shore (36.637, −121.936) while the waypoint names said Seymour. They now hold
> **Terrace Point, 36.94840 N / 122.06538 W**, one pad for both launch and land, **22,386 m
> from M1**. The waypoint names followed in J-8 (`e0630ff`): `Terrace-Point-Launch` /
> `Terrace-Point-Land`.
>
> **~~No output has been round-tripped through QGC.~~ Done 2026-09-30, clean.** The `.plan`
> writer exists as of 2026-09-22 (J-5). Its key sets and per-class frames match `exp2.plan`,
> its camera items match `exp..plan`'s DO item, and since 2026-09-25 the suite enforces all
> of that (J-7). A generated file was **loaded into QGC and checked by eye** (no stray
> waypoints, a home icon, and direction lines through every waypoint), then saved by QGC
> and diffed. QGC changed one value, `params[2]` on the camera-stop items, and ours now
> matches, so every science line ends with a final frame the RPIC disregards (see the
> final-frame bullet under the J-5 writer). QGC has no Save As and its Save writes back to
> the file it opened, so a manual round trip opens a copy, then saves the copy. The full
> procedure is in [What `exp2.plan` settles](#what-exp2plan-settles).
>
> **~~The camera starts before the S2 has rolled out of its turns.~~ Fixed in code
> 2026-10-18 (fast track R-3 to R-7).** `V1_COLLECTION_INSET_m` = 52 m was shorter than the
> S2's 57 m still-air turn radius, so every line's first image was taken banked (20–35° in
> PX4 SITL), and it was the only image of the first ~54 m of the science box. The constant
> is retired, and `planner` sizes the inset from the design wind. Its constants are
> provisional for the S3 (item 4 above).
>
> The one V2C-2 change that IS live is the parallax line extension in
> `geo.make_lawnmower_grid_through_m1`. Each end of every line grows by the parallax plus
> the collection inset: 2 × (352 + 601.9) = 1,908 m per line for the S3 at the 9 m/s
> default (1,645 m for the S2 after the rollout fix, 808 m with the old 52 m inset).

## Layout

- `flight_plan_maker.py` — terminal entry point (run this). CLI flags: `--name`, `--out-dir`, `--date`, `--time`,
  `--design-wind` (m/s at flight altitude; default `DEFAULT_DESIGN_WIND_ALOFT_ms`).
  Writes the KML, PNG and `.plan`, then prints the total, transit and grid duration and
  distance, the margin, both bearings, the design wind with the inset and line 1 lead-in it
  produced, the forecast wind beside them (reported only), the three output paths, and
  every pilot note on the plan (`RPIC NOTE:` lines). Since K-6 it also prints the phase
  times (climb, descent overrun, hand-offs) and the climb orbit. See the K-6 bullet under
  Current state.
- `src/` — engine modules:
  - `constants.py` — engine constants (aircraft, M1, sensor, date/time defaults + timezone, weather, actions).
  - `objects.py` — core classes (Aircraft, **Vehicle**, Sensor, Weather, CurrentSunState,
    Waypoint, MissionRequest, CandidatePlan). `Vehicle(Aircraft)` adds the MAVLink protocol
    identity Step J needs — `vehicle_type`, `firmware_type`, `is_VTOL`, `hover_speed_ms` —
    and, since K-2, the optional `transition_height_agl_m` and `waypoint_lookahead_s`.
    `MissionRequest` carries an optional `climb_waypoint` (K-2).
    ✅ `planner._BlackSwift_S3` constructs one (the S3, since K-3).
  - `sun.py` — local→UTC datetime resolver (`resolve_mission_datetime`, `mission_datetime`) + pysolar sun azimuth/elevation (`create_sun_state`).
    The two pysolar calls run inside `_pysolar_without_leap_second_warning()`; see the J-6
    warning gate below.
  - `aircraft_math.py` — endurance → distance budget, duration, battery margin, plus the
    V2C wind triangle (**reporting only** as of 2026-09-08 — see constraint 4), the
    camera-rollout math, and `waypoint_capture_distance_m` (K-2).
  - `geo.py` — geodesic math + M1-centered lawnmower grid geometry (the M1-centering
    becomes a *default* rather than an invariant under Step F).
  - `weather.py` — **leaf**: live NWS weather for a lat/lon/datetime → populated `Weather`, or `None` (planner falls back to the stub).
  - `planner.py` — the hub: assembles objects, scores glint, builds the plan.
  - `outputs.py` — KML, PNG and QGC `.plan` writers (`write_kml`, `write_png`,
    `write_qgc_plan`). The pilot-notes document (constraint 4) is still to come. Files are
    named `<name>_<YYYYMMDD-HHMMSS>.<ext>`. Seconds were added on 2026-09-25, after two runs
    within one minute overwrote each other.
  - `validator.py` — **docstring only, no code.** Its docstring still describes the
    **cancelled** C-2 RTH/crosswind gate; read it as history, not as a spec. What
    validation survives is narrowed and sidelined — see Step E.
- `tests/` — tiered pytest harness (`test_0_*` … `test_6_*`, **seven** files, 120 tests); see [Setup & run](#setup--run).
- `exp2.plan`, `exp..plan` — **real QGroundControl exports for this site**, and until
  2026-09-30 the only ground truth the repo had for the `.plan` format. Several format
  questions that docs left ambiguous are settled by reading them, and the J-7 tests read
  both. `roundtrip_qgc.plan` joined them on 2026-09-30: our own default plan after a QGC
  load and save, and the first file in which QGC itself wrote camera items. `.gitignore`
  ignores `*.plan` but makes explicit exceptions for these three, so generated plans are
  never committed and the references always are. See
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
  declares `_BlackSwift_S3`, `_Launch_Waypoint`, `_M1_Waypoint` and
  `_BlackSwift_S3_usable_endurance_m` at module scope, and `build_candidate_plan` also
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
- **House style** (set by the 2026-09-22 cleanup across `src/` and `tests/`; keep new code
  consistent with it):
  - **Imports:** three groups separated by a blank line: standard library, third-party,
    engine modules. No header comments. One module per `import` line. `constants` is always
    `import constants as CONST`. The only code allowed between imports is an ordering
    constraint with a comment saying why (`matplotlib.use("Agg")`, the `sys.path` insert in
    `flight_plan_maker.py`).
  - **Documentation:** a docstring goes *inside* the `def` or `class` it documents, never as
    a bare string or comment block above it. Every class and every public module-level
    function has one. Private helpers, `__init__`, getters and setters, `main()` and tests
    may go without when the name and body say enough; a test explains itself with `#`
    comments inside. Module docstrings sit at the top, and section banners stay as
    module-level `"""` strings. Comments inside functions explain *why*. (Corrected
    2026-09-25: this line used to say *every* function, which about 180 accessors and tests
    never did. Placement is what the cleanup enforced.)
  - **Comments** start with `#` and one space; inline comments sit at least two spaces after
    the code.
  - **Formatting:** PEP 8 blank lines (two around top-level defs, one between methods), no
    trailing whitespace, one newline at EOF. No space before `(`, and `name=value` for
    keyword args.
  - **Names:** snake_case for locals, parameters and private attributes. Public attribute
    and function names are an API; tests and CLAUDE.md reference them. Rename one only
    as its own change, never as style. The known holdouts are `is_VTOL`, `waypoint_ID`,
    `to_CSV_row`, `total_flight_distance` (no `_m`), `V1_DEFAULT_SENSOR_ALONG_TRACK_FOV_DEG`
    (`_DEG`), and the capitalized `planner` singletons (`_BlackSwift_S3`, ...).
  - **Tests** reach objects through public getters, never `obj._private` attributes.
  - **Writing:** comments state what is true *now*. History stays, but dated and labeled
    as history (the `⚠️ 2026-09-08` notes). A claim about a module that does not exist yet
    (validator) is written as future tense, never present.
  - **Not covered:** the QGC-constants block of `constants.py`, which is user territory, and
    line length.

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
  extension** in `make_lawnmower_grid_through_m1` is live (parallax + inset at each end,
  +1,908 m/line for the S3 at the 9 m/s default); the crab-shear half
  of that correction is cancelled with the rest of C-2's plan-altering work.
  ⚠️ Step F makes off-nadir angle user-settable, so none of these numbers stay constant.
- **5-point flight lines.** `geo.make_line_through_point` emits
  `[turn, collect_start, line_label (center), collect_stop, turn]`
  (`V1_POINTS_PER_LINE = 5`, the single source of truth — do not re-hardcode `5`).
  The center is the M1 overflight if it's the center line; the
  `collect_start`/`collect_stop` points sit one collection inset in from each turn (camera
  on/off after roll-out), and line 1's first turn sits a further pushback out (see the
  camera rollout bullet below). **Every** leg collects, so the serpentine no longer
  alternates science/transit.
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
  1. `seed = 2 × distance(launch, M1)`. From Terrace Point it falls **1.0% short** of the
     measured transit for the S3 (44,773 m against 45,219 m; 0.40% short for the S2 at J-4),
     and the default plan still fits on the first pass.
  2. `grid_budget = usable_endurance − seed`, handed to `_pick_best_orientation`. Since
     K-4 the takeoff and landing phases are subtracted too (see the K-4 bullet below).
  3. After `_reorient_to_launch` and `_classify_waypoints`, the **true** transit is measured
     from the real corners: `d(launch_wp, climb point) + d(climb point, route[1])` plus
     line 1's lead-in on the way out (K-4 and the rollout fix), and `d(route[-2], land_wp)`
     on the way back.
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
    - `plan.usable_endurance_distance_m` — what the **battery** affords (96,390 m for the
      S3; 82,620 m for the S2). Set by `planner`, because only the hub knows it.
    - `plan.grid_budget_m` — what `geo` was **handed** (endurance − transit − the phase
      reserve, 45,439 m; 37,847 m for the S2 at J-4, before the phases). Arrives via the
      metrics dict.
    - `plan.total_grid_distance_m` — what the **grid** costs (42,242 m; for the S2, 26,559 m
      after the rollout fix and 32,343 m at J-4). From `geo`.
    - `plan.total_flight_distance` — what is actually **flown** (87,460 m; for the S2,
      71,630 m and 77,296 m). Computed by `planner` over the classified route, and what
      `route_duration_min` consumes.

    Collapsing any two of these reintroduces the defect. It has already happened twice under
    different names — see the last bullet in [Design conventions](#design-conventions).
    Since J-6 the plan also carries the **measured transit** itself: `plan.transit_distance_m`
    (45,219 m, set by `set_transit_distance_m`; for the S2, 45,071 m and 44,953 m at J-4).
    It is stored, not derived,
    so no consumer subtracts two of the four. Since the rollout fix it includes line 1's
    lead-in (see the camera rollout bullet below).

- **Grid/transit split (V2 Step J-6, built 2026-09-25).** The summary reports the flight as a
  grid part and a transit part: `plan.grid_duration_min` / `plan.total_grid_distance_m` and
  `plan.transit_duration_min` / `plan.transit_distance_m`. Default plan for the S3 (K-4):
  **grid 33.5 min / 42,242 m, transit 40.8 min / 45,219 m, total 74.3 min**. The transit
  time includes the 4.9 min of phases. For the S2 it was 25.6 / 41.7 / 67.3 after the
  rollout fix, and 31.3 / 41.6 / 72.9 at J-6. At J-6 a boat launch 2 km from M1 flipped it
  to grid 60.5 min, transit 6.6 min: the Step F argument in two numbers. The S3's boat
  plan: grid 46.5 min, transit 13.2 min, 7.4 min of it phases.
  - **The grid is costed; the transit is the remainder.** `planner` Step 9 calls
    `route_duration_min(total_grid_distance_m, N, aircraft)` for the grid and subtracts it
    from the total. Every one of the N−1 turn penalties is a grid turn, and the transit legs
    carry none. Since K-4 the climb, the descent's overrun and the hand-offs are added to
    the total on top of `route_duration_min`, and the transit remainder picks them up. A
    separate transit formula would silently miss them, and the parts would stop summing to
    the total.
  - ⚠️ **Two wrong ways that look right.** `route_duration_min(transit_m, 0, ...)` counts
    `(0 − 1)` turns, a negative turn, and comes out 10 s short. Splitting the total by distance
    share spreads the grid's turn time into the transit and gives **42.4 / 30.5**, which is
    what the docs and the artifact quoted before this was built. Correct, on the J-6
    default plan: **41.6 / 31.3**.
  - Pinned in Tier 3 (`test_flight_splits_into_grid_and_transit`, shore and boat), in closed
    form. The line that asserts transit = distance ÷ cruise is the one to rebase in Step G.

- **Transit bearings (V2 Step J-4.5, done).** `plan.departure_bearing_deg` (**176.3°**
  for the S3; 174.9° for the S2 after the rollout fix) and `plan.approach_bearing_deg`
  (**343.3°**; 344.6° for the S2) are set by `set_transit_bearings` from the same
  waypoint pairs J-4 measures for the transit. Since K-4 the departure bearing points from
  the pad to the climb point. **Reporting only** — they reach the
  terminal summary and the pilot-notes PDF, never the `.plan` (a heading in the file would
  mean a commanded yaw, which the null-yaw decision rules out).
  - ⚠️ **Measure after `_reorient_to_launch`, never before.** Reorientation decides which end
    of the serpentine the aircraft exits from; read off the raw grid the approach comes out
    ~10° wrong. Pinned by a Tier 4 assertion that the reported approach equals
    `bearing_between(waypoints[-2], waypoints[-1])`, mutation-verified to fail otherwise.
  - The approach sits **6.3° off the pad→M1 reciprocal** (349.6°) for a shore launch (5.0°
    for the S2), because 22.4 km of transit dominates a few-km grid. **A boat launch breaks
    that** — from 2 km out the S3's approach is 55.4° (305.2° for the S2). Never brief the
    number from memory; recompute it.
  - Operational use: a wind **from ~163.3°** is a pure tailwind on the approach, which the
    S3 meets as it slows to transition to hover over the pad. A belly landing is now an
    emergency only. Crab on approach at the S3's 21 m/s cruise: 5.5° at 2 m/s crosswind,
    11.0° at 4, 16.6° at 6, 22.4° at 8, 28.4° at 10 (6.4° to 33.8° at the S2's 18 m/s).

- **Camera rollout geometry (fast track, built 2026-10-18).** ⚠️ **Read this before touching
  the inset, line 1's first waypoint, or the transit figure.**
  - `MissionRequest.design_wind_aloft_ms` is the RPIC's planning input, in m/s at flight
    altitude (`--design-wind`, default `DEFAULT_DESIGN_WIND_ALOFT_ms` = 9). The summary
    prints the forecast beside it at the 10 m NWS gives it, and never applies it
    (constraint 4).
  - `planner` Step 2 sizes `collection_inset_m = rollout_inset_m(aircraft, design wind)` once,
    with the aircraft's capture distance as its early camera start when it has one (K-4),
    and hands it to `geo`, which places it at both ends of every line and extends each line
    by parallax + inset at each end. `geo` takes it as a parameter, the same contract as the
    payload figures. `V1_COLLECTION_INSET_m` is retired.
  - **Strat 1, `planner._apply_entry_pushback`.** After `_reorient_to_launch`, and before the
    transit and bearings are measured, line 1's first turn waypoint moves back along line 1
    by `entry_pushback_m` at the arrival angle θ (0 at θ ≤ 90°). The plan records
    `entry_pushback_m` and `entry_arrival_angle_deg`. Moving the waypoint widens θ by ~0.2°
    from the shore, inside the formula's margin, so it is not iterated.
  - **The lead-in is counted in the transit.** `geo`'s grid distance starts at the turn
    waypoint `geo` placed, so the pushback is flown but outside the grid, and the launch
    point sets it. It is added to the outbound transit, which keeps grid + transit = flight,
    keeps the J-6 split exact, and lets the J-4 re-seed pay for it. Tier 3 also asserts that
    the flight equals the distance along the plan's own waypoints; that is the check that
    fails if the lead-in is left out.
  - ⚠️ **Strat 1 explodes near a reversal.** tan(θ/2) runs to infinity at 180°. Shore launches
    arrive at 1°–126° (60 samples across 2026, 08:00–16:00, measured for the S3 on
    2026-11-03). The Tier 3/5 boat launch 2 km north of M1 arrived at 178.2° with the S2,
    and its line 1 lead-in was **7,990 m**. With the S3 it arrives at 113.9° and flies 85 m,
    but a launch point F-1 makes settable can still arrive near 180°. No CLI path reaches a
    boat launch until F-1, so this must be settled before or with F-1 (see F-1.5).
  - Default plan (S3, K-4): 9 lines, inset 601.92 m, θ 118.96°, pushback 110.26 m, 65
    `.plan` items. For the S2 after the rollout fix: 7 lines, 470.62 m, 117.56°, 83.4 m, 51
    items.
  - Pinned by Tier 3 (`test_higher_design_wind_never_gives_more_lines`, the waypoint-sum
    check in `test_flight_splits_into_grid_and_transit`), Tier 4
    (`test_camera_starts_an_inset_past_every_turn`, which also pins the parallax extension,
    and `test_line_one_entry_meets_the_turn_rule`) and Tier 5
    (`test_summary_reports_the_design_wind_beside_the_forecast`,
    `test_design_wind_flag_rejects_bad_values`). The build was broken eight ways in a
    scratch copy, and every break turned at least one of them red.
  - `test_transit_seed_retry_converges` now plans every design wind from 0 to the 15 m/s
    rating from a launch at M1. At the 9 m/s default the first pass fits, so the old
    single-launch probe no longer reached the re-seed.

- **Takeoff and landing phases (V2 Step K-4, built 2026-10-27).** ⚠️ **Read the K-4 entry
  in [Step K](#k-s3-adoption-closed-2026-11-03--k-5-not-built) before touching the
  budget, the transit or the takeoff item.** In short:
  - **Climb point:** a plan field, not a waypoint.
  - **Budget:** the climb and hand-offs are reserved before sizing, and the descent rides
    the approach.
  - **Takeoff altitude:** a VTOL's is its transition height (10 m standard).
  - **Camera and legs:** the S3's capture distance is its early camera start and its
    shortest allowed leg.

- **Pilot notes (V2 Step K-6, built 2026-11-03).** `planner._pilot_notes` builds a tuple of
  notes in Step 8, and `CandidatePlan.pilot_notes` carries it. The summary prints each as
  an `RPIC NOTE:` line, and the pilot-notes document will read the same tuple. The texts are
  `PILOT_NOTE_*` templates in `constants.py`, beside `RPIC_NOTE_FINAL_FRAME`. **Notes report;
  none rejects or reshapes a plan** (constraint 4). In print order, most urgent first:
  1. **The design wind above the aircraft's wind rating** (`vehicle_wind_rating`, strictly
     above).
  2. **The forecast's sustained wind or gust at 10 m above the rating**, compared as NWS
     gives it and never scaled aloft (the user's choice, 2026-11-03). The note quotes the
     measured morning ratio over M1, ~1.15, and the engine never applies it.
  3. **Weather that isn't a forecast.** If the weather's source isn't NWS (the stub), the
     plan had no live forecast, and the note says to re-run within 7 days of the flight. If
     NWS left fields uncovered, it names `Weather.stale_fields` by their
     `NWS_FIELD_LABELS`. Visibility is the everyday case, since NWS covers it only
     8–30 h ahead. "Out of date" means exactly this (the user's choice, 2026-11-03): no
     forecast-age or lead-time threshold exists.
  4. **The two operator hand-offs**, every plan, because every vehicle is charged them.
  5. **`RPIC_NOTE_FINAL_FRAME`**, every plan, moved into the tuple unchanged.
  - ⚠️ **A default never stands in for a forecast.** A wind field `weather.py` defaulted
    reads as dead calm, so it is never compared with the rating, and when the sustained
    wind was defaulted the note says it went unchecked. The stub is never compared at all.
  - Not built, by the user's choice: the S3-only belly-landing note. The summary's phase
    line also states that `Transit Flight`'s time includes the phases.
  - The `.plan` and KML are byte-identical to K-4's (shore and live-forecast dates).

- **QGC `.plan` writer (V2 Step J-5, built 2026-09-22).** ⚠️ **Read this before touching
  Section 2 of `outputs.py`.** The call chain is
  `write_qgc_plan(plan, out_dir)` → `_plan_items(plan)` → `_serialize_qgc(plan, items)`,
  and `_serialize_qgc` calls `_qgc_item(item, jump_id, is_vtol)` once per item. Each
  `_qgc_item` call reads `_QGC_COMMAND`, `_QGC_ALT_FRAME`, `_qgc_params(item, is_vtol)` and
  `_qgc_home(items)`. The rules, all enforced and measured:
  1. **The neutral list is read-only** once `_plan_items` returns it. Every QGC dict is
     new, built field by field, so `Source_Action` never reaches the file and a future
     `_serialize_blackswift` can consume the same list.
  2. **Structural dialect differences go in `_plan_items`; numeric ones go in the two
     tables.** No MAV_CMD or MAV_FRAME integer appears anywhere else in `outputs.py`.
  3. **`doJumpId` is assigned by `enumerate(items, start=1)` inside `_serialize_qgc`**, and
     never stored on an item.
  4. **Every number has one source.** Coordinates and altitude come from the item, and the
     serializer never re-reads a constant the item already resolved.
  5. **Unknown keywords raise** `ValueError` in `_qgc_params`. A missing takeoff raises in
     `_qgc_home`.
  - **Home position is derived**, not fixed. `_qgc_home` returns the takeoff item's lat/lon
    plus `TERRACE_POINT_AMSL_m`, so a boat launch gets its own home (verified on the Tier 3
    boat plan). `_QGC_PLANNED_HOME_POSITION` was **retired**; it had put the 50 m climb-out
    height where QGC expects the home's AMSL altitude. Residual: a boat deck sits near sea
    level, not 16 m. Step F makes launch elevation part of the launch point.
  - **Camera items omit all three altitude keys** (`Altitude`, `AltitudeMode`,
    `AMSLAltAboveTerrain`), keyed on the `MISSION` row's `None`. `exp..plan`'s own DO item
    confirms this is what QGC writes; see "What `exp..plan` adds".
  - ⚠️ **`_CRUISING_MISSION_ALT_FRAME` is the CRUISE frame (0), not `MAV_FRAME_MISSION`
    (2).** The J-5 audit caught the `AMSL` and `MISSION` rows of `_QGC_ALT_FRAME` swapped.
    That would have put every cruise waypoint in the mission frame, and it fails
    silently: the file still writes. The word "MISSION" in the constant's name is the
    trap; a note beside the table says so. The constant is a QGC constant, so renaming it is
    the user's call.
  - Measured on the default plan, flown by the S3 since K-3 (2026-11-03): 65 items = 7N + 2;
    commands 16×45, 206×18, 84×1, 85×1 (VTOL takeoff and land); frames 0×45, 2×18, 3×2;
    header vehicle 21, firmware 0, cruise 21, hover 1; 34,257 bytes. The S3's boat plan gives
    79 = 7·11 + 2. A PX4 fixed wing flying the default mission (`_fixed_wing_plan()`, the S2's
    numbers) gives 51 = 7·7 + 2 with 22/21, and a multirotor gives 22/21 with `hoverSpeed`.
    For the S2 at J-5 the default was 65 items with 22/21, 34,248 bytes (35,615 before the
    camera-key fix).
  - **All of the above is pinned by J-7** (`tests/test_6_outputs.py`, 22 tests). ⚠️ **Every
    expected value there is a MAVLink-spec literal or is read out of `exp2.plan`,
    `exp..plan` or `roundtrip_qgc.plan`, never out of `constants.py`.** A test that read the
    QGC constants back would pass on the typo it exists to catch. Keep it that way when
    adding tests. Verified by breaking the writer 15 ways in a scratch copy (swapped frame
    rows, a `NAV_LAND` typo, inverted VTOL columns, a hard-coded home, a leaked
    `Source_Action`, a bearing written as yaw, unsorted keys and more). Each break turned
    its test red.
  - **⚠️ The final frame and its RPIC note (2026-09-30).** The QGC round trip changed one
    value: QGC sets `params[2]` of `DO_SET_CAM_TRIGG_DIST` ("trigger once immediately") to 1
    on every stop item. It folds each camera item into the waypoint before it and writes the
    item back from its own template. Our stop items now match, so every science line ends
    with one final frame, whichever ground station uploads the plan. That frame's glint, and
    the aircraft's attitude as it leaves the line for the turn, are **unverified**. So every
    plan's pilot notes end with `CONST.RPIC_NOTE_FINAL_FRAME` (since K-6; the summary
    printed it directly before), and the summary prints it on every run, telling the RPIC to
    disregard the last photograph of each science line. **The note is permanent until that
    frame is characterized**, and the pilot-notes document inherits it. Two tests hold the
    two halves, and each turned red when broken in a scratch copy:
    `test_camera_items_match_qgcs_round_trip` (against `roundtrip_qgc.plan`, on the shore and
    boat plans) and `test_summary_carries_the_rpic_note`.

- **J-6 warning gate (cleared 2026-09-22; held when J-6 landed; re-run 2026-09-25,
  2026-09-30, 2026-10-18, 2026-10-27 and 2026-11-03).** The console must stay quiet enough for J-6's new output to be read. That is
  a **state to keep**, not a task that was done once. The 2026-09-30 re-run, after the RPIC
  note joined the summary: the entry point exits 0 with nothing on stderr under `-W error`
  on the default date, a live-forecast date and an out-of-forecast date; 94 tests pass under
  `-W error`, and under `-W always` with no warnings shown; pyright reports 0 errors. The
  2026-10-18 re-run, after the design wind and forecast joined the summary, held the same
  on all three dates with 104 tests. Re-run again on 2026-10-27 after K-1 to K-4, which
  changed the numbers the summary prints but not its lines. It held on all three dates, with
  115 tests passing under `-W error` and pyright at 0 errors. Re-run on 2026-11-03 after K-6
  added the phase, climb-orbit and pilot-note lines. It held on all three dates, with 119
  tests passing under `-W error` and pyright at 0 errors, and again after K-7 with 120.
  - `simplekml`'s `codecs.open()` DeprecationWarning is **fixed at source**. `write_kml`
    writes `kml.kml()` itself with `open(..., encoding="utf-8", newline="")` instead of
    calling `kml.save()`. Verified byte-identical to `save()`.
  - pysolar 0.13's leap-second UserWarning fires for **every date after 2026-06-30**,
    because its table ends at 2025. It is filtered only in `sun.py`, by a `catch_warnings`
    scope around the two pysolar calls that matches that one message. Measured: 1 s of
    error moves the sun ≤ 0.008° in azimuth, against a 15° glint tolerance. No leap second
    has been added since 2016-12-31. Revisit when pysolar ships a newer table.
  - Pyright found two real gaps in `src/`, both fixed:
    - `planner._pick_best_orientation` now guards `best_entry is None` explicitly.
    - `weather._http_get_json` could fall off its retry loop and return `None` when
      `NWS_MAX_RETRIES < 0`. The resulting `TypeError` escaped `get_weather`'s stub
      fallback and crashed the planner. It now raises `RequestException`, which
      `get_weather` catches.
  - **Re-run after any dependency bump, and before any change to what the entry point prints:**
    - the entry point under `-W error`;
    - `pytest -o addopts="" -W error`;
    - pyright over `src tests flight_plan_maker.py conftest.py`.

    Pyright isn't installed on this machine, so use a throwaway venv. Any new warning gets
    fixed, or filtered at its call site, never blanket-suppressed.
  - **The suite half is now permanent:** `pytest.ini` sets `filterwarnings = error`, so a new
    warning fails the suite. As of the 2026-09-22 cleanup, pyright also reports 0 errors
    over `tests/` (it had 6, all Optional operands in `test_4`, now narrowed with
    `assert ... is not None`).

- **Tests.** Tier 0 (primitives) and Tier 2 (derived math) are pure closed-form math
  (must never fail); Tier 1 pins the date/time resolver, sun-state, and weather-leaf wiring; Tiers 3–5 drive
  the real mission and assert structural invariants as *indicators* that the math is sound.
  **Tier 2 needed no rebasing for J-4** — those tests check `route_duration_min` in closed
  form rather than asserting the default mission's N, which is exactly what the tiering was
  for. The J-4/J-4.5 additions live in Tier 3 (`test_4_grid_assembly.py`: both budget
  assertions, the retry-convergence probe, the boat-launch science gain and bearing swing)
  and Tier 4 (`test_5_classification.py`: bearings reach the plan, are measured on the final
  route, and track the M1 reciprocal from shore). J-6 added the grid/transit split test to
  Tier 3. J-7 added the `.plan` half of Tier 5 (`test_6_outputs.py`, 20 tests, described
  under the J-5 writer bullet above). The 2026-09-30 round trip added two more: the camera
  items against `roundtrip_qgc.plan`, and the RPIC note in the summary. The camera rollout
  fast track added five Tier 2 tests (R-2) and five more across Tiers 3–5 (R-7), listed
  under the camera rollout bullet above: 104 in all. K-2 added four Tier 2 tests (the
  capture distance, `Vehicle`'s new fields, the S3 constants, `climb_waypoint`): 108.
  K-4 added seven (two Tier 2: climb/descent durations and the descent overrun; four Tier 3:
  phases paid for, slower climbs never give more lines, the climb point, the shortest leg;
  one Tier 5: the VTOL takeoff at the transition height), and rebased the Tier 3 split's
  transit line: 115. K-6 added four Tier 5 tests (a wind above the rating, never comparing
  a default, weather that isn't a forecast, and the summary's phases and notes): 119. K-7
  (2026-11-03) found four branches no test reached, each confirmed by a break that passed
  the suite. It added one Tier 5 test (the notes use the plan's own aircraft's rating) and
  extended three: `test_altitudes_by_class` now also checks a fixed wing, against
  `roundtrip_qgc.plan`'s 50 m climb-out (unpinned since K-3 made the default a VTOL); the
  VTOL takeoff test checks a vehicle's own transition height; and the summary test checks
  "from the pad". 120.
- **Known defects and deferred items:**
  - ✅ ~~The budget and the reported duration exclude the transit legs.~~ **Fixed in J-4.**
  - ✅ ~~Launch/land constants are stale.~~ **Fixed in J-1**, and the waypoint names followed
    in J-8 (`Terrace-Point-Launch` / `Terrace-Point-Land`, `e0630ff`).
  - ✅ ~~Along-track overlap does not exist.~~ **Built in J-2/J-3.** `Sensor` carries
    `cross_track_overlap` and `along_track_overlap` separately;
    `metrics["camera_trigger_distance_m"]` is **280.74 m** (561.48 m footprint × 50%) and
    reaches the plan. `ground_footprint_along_m` finally has a caller.
  - ✅ ~~`Vehicle` is never instantiated.~~ **Fixed.** `planner._BlackSwift_S3` is a
    `Vehicle` (the S2's `_Black_Swift` until K-3). Measured on the default plan:
    `vehicle_type 21`, `firmware_type 0`, `is_VTOL True`, `hover_speed_ms 1` (the S2 gave 1,
    12, False, 0) — all four fields the writer branches on are reachable. ✅ Asserted
    since J-7 by `test_plan_aircraft_is_a_vehicle`. The gap had survived three steps precisely
    because no test looked.
  - ✅ **The camera started before the S2 had rolled out of its turn. Fixed in code
    2026-10-18; its constants are provisional for the S3.** Found 2026-09-28 by flying V2's lines in
    uas_sim (PX4 SITL); a fast-track fix opened 2026-10-06 on its own branch
    (`rollout_hotfix`). `V1_COLLECTION_INSET_m` = 52 m was shorter than the S2's 57 m
    still-air turn radius, so each line's first image was taken banked (20–35° in SITL). That
    image was the only one covering the first ~54 m of the science box. Write-ups:
    `flight-plan_camera-rollout-issue.md` (the defect) and `S2 Rollout Calibration
    Results.md` (the 2026-10-08 sweep, 43 runs and 159 line entries).
    - **The calibrated model (2026-10-08 sweep).** D_level, the distance past the turn
      waypoint at which the aircraft is wings-level and on the line, is
      **2.5·R_g + 80 m** over every flight seen in the worst wind direction, with
      R_g = R·(1 + W/V)² at the design wind W at altitude. PX4 then starts the camera up to
      **71 m before** collect_start (about 2 s of ground speed), so the planning inset is
      **2.5·R_g + 150 m**: 293 m in still air, 495 m at 10 m/s, 629 m at the 15 m/s rating.
      The pre-sweep guess, 2·R_g + 50, was short at every wind, and a 326 m inset failed at
      8, 10 and 11 m/s.
    - **What sets D_level is the new line's own tailwind.** A line flown into the wind
      settles within ~35 m; a downwind one overshoots and S-turns for 230–510 m. Lines
      alternate direction, so every grid has downwind lines and a fixed inset must be sized
      on the worst case. Over all directions D_level has no relation to R_g (R² 0.003).
      Don't fit to the mean.
    - **Strat 1 stays for the turn onto line 1:** when the arrival angle θ > 90°, line 1's
      first turn waypoint moves back by R_g·(tan(θ/2) − 1). The sweep found it conservative
      by 9–103 m on the 117.7° default entry, and kept it. The Strat 2 loop is deferred to
      Step F.
    - **Decided:**
      - The design wind is a planning input the RPIC owns (2026-10-06). The engine reports the
        forecast beside it and never changes the geometry on the forecast by itself, per
        constraint 4.
      - The default is a **fixed value**, overridable per plan, and it must be derived from
        Monterey Bay wind data, not set arbitrarily (2026-10-09). Its value is **9 m/s at
        altitude** (2026-10-09): the 90th percentile of the 10:00 wind at 609.6 m over M1.
        For the S2 that gave R_g = 128.25 m, an inset of 470.6 m, 7 lines and a 22.7 min
        margin. For the S3 it gives R_g = 158.4 m, an inset of 601.9 m (with its 126 m early
        start), 9 lines and a 15.7 min margin.
      - `V1_COLLECTION_INSET_m` is **retired** (2026-10-09). It went in R-4, not R-3: R-3
        made the inset a parameter of `geo` with `planner` still passing 52 m, a pure
        refactor that left both test plans byte-identical, and R-4 removed the last reader.
      - The defect is in both warning boxes now, not at the fast track's close (2026-10-09).
    - **R-2 built 2026-10-09:** the rollout constants in `constants.py`, and
      `ground_turn_radius_m`, `rollout_inset_m` and `entry_pushback_m` in `aircraft_math.py`.
      Five closed-form Tier 2 tests took the suite to 99.
    - **R-3 to R-7 built 2026-10-18:** `geo` takes the inset as a parameter, `planner` sizes
      it from `MissionRequest.design_wind_aloft_ms` and applies Strat 1, `--design-wind`
      reaches the summary with the forecast beside it, and five relationship tests take the
      suite to 104. How it works is in the camera rollout bullet under Current state.
    - **What still stands:**
      - The S2 loop sweep that was to check the geometry as built is cancelled (2026-10-18),
        because the S2 is end of life. Its prompt was never sent. The constants 2.5, 80 and
        70 are provisional S2/PX4 placeholders, and BlackSwift has declined to share S3
        model data (2026-10-27), so no source for S3 values is in sight.
      - The 70 m early-camera allowance is PX4's. BlackSwift is sending the minimum
        acceptance radius of the S3's flight management system.
      - A design wind below the day's real wind brings back banked first images on the
        downwind lines. The summary shows the forecast beside the design wind for that reason.
      - Strat 1 near a reversal (the boat case above) waits on F-1.5.
    - **Measured cost, with Strat 1, for the S3** (2026-11-03, K-4 phases paid for):
      - 9 lines hold up to a design wind of **14.1 m/s at altitude**. The margin falls from
        18.7 min at 0 m/s to 15.7 min at 9 m/s and 13.6 min at 14 m/s.
      - At the 15 m/s rating the grid drops to 7 lines (inset 776.1 m, 24.7 min margin).
    - **The same for the S2, kept as history** (it drove the F-4 argument):
      - 9 lines held only up to ~2.8 m/s (inset ~340 m). Above that the grid dropped to 7
        lines, with a 24.4 min margin at 3 m/s and 20.5 min at 15 m/s.
      - The 7-line grid has 56% of the 9-line area, because the grid is square. At 9 m/s, a
        7-line grid with 1.5 km longer lines covered 6.36 km² (against 6.29 km² for 9 lines)
        with a 12.9 min margin.
    - **Wind data for the default (2026-10-09, not in the repo).** Archived model winds over
      M1 for 2022–2025, at 10:00 local, interpolated to 609.6 m: mean 4.9 m/s, p90 8.8 m/s,
      ≤ 2.8 m/s on 26% of mornings. The wind at 609.6 m is only ~1.15× the 10 m wind on
      morning flights (0.84× in the afternoon), not the 1.79× of the simulator's 1/7 power
      law. **Never scale a 10 m forecast to altitude with the 1/7 law.** The M1 buoy (NDBC
      46092, 2015–2025, anemometer 4 m) agrees at the surface: 3.5 m/s mean at 10:00.
  - **Grid sizing is budget-derived, not requested.** `geo._initial_total_lines_from_budget`
    picks N from the endurance budget. `V1_DEFAULT_GRID_WIDTH_km`,
    `V1_DEFAULT_LINE_LENGTH_km` and `V1_DEFAULT_LINE_SPACING_km` are declared but never
    read. They were removal candidates; under **Step F they are reinstated** as the defaults
    behind user-settable dimensions. Do not delete them.
  - ✅ ~~Climb and descent are still unmodeled.~~ **Fixed in K-4 (2026-10-27).** The climb,
    the descent's overrun and the hand-offs are reserved before `geo` sizes the grid, and
    added to the duration. See Step K. History: through J-4 and the rollout fix the whole
    route was costed at cruise with zero vertical time, about 3 min of climb and 5.6 min of
    descent counted as zero.
  - **Parallax is reported, and only half-corrected.** The line extension is live; the
    crab-shear term is cancelled per constraint 4.

## V2 roadmap — what comes next

**Execution order as of 2026-11-06: `J` → `K` → `F` → `C-2 (re-scoped)` → `D`.** F took in
most of `G` and `E`'s legality checks on 2026-11-06, so neither has scope of its own left.
**J is complete (2026-09-30). K, S3 adoption, CLOSED on 2026-11-03 without K-5, the
BlackSwift writer. F is next, and its design was settled on 2026-11-06.** Letters record the order
steps were *scoped*, not the order they are *built* — the same convention the `V1_`
constant prefixes follow.

The original through-line was "make the mission situation-aware, fold that into ranking,
then gate for legality." Constraint 4 retires the gating half of that: the aircraft
compensates for wind in flight, so the engine's job is to **describe** conditions
accurately, not to veto or re-steer on them. The new through-line is **make the engine
configurable and its output machine-usable, and report honestly.** Preserve dumb
unidirectionality throughout.

### J. JSON `.plan` output — COMPLETE (2026-09-30)
A `.plan` (JSON) writer, so a plan can be uploaded and flown instead of merely looked at.
`constants.EXTENSION_JSON` already exists and `outputs.write_kml`'s docstring already names
the intended helper (`write_qgc_plan`). Today's KML is **visualization only** in QGC — it
does not import as a flyable mission — which is the entire reason this jumped the queue.
**No other roadmap step may start until this ships.** ✅ Shipped 2026-09-30.

> **STATUS 2026-09-30 — STEP J IS COMPLETE. J-0 through J-8 are done, 94 tests green (also
> under `-W error`).** Every run writes a `.plan`, and the summary reports the grid/transit
> split, both bearings and the final-frame RPIC note (J-6). The 27 ad hoc J-5 checks are now
> permanent Tier 5 tests (J-7), 22 of them: key sets and per-class frames against QGC's
> exports, MAVLink commands, contiguous `doJumpId`, paired camera toggles, no
> `Source_Action` leak, a home that follows the takeoff, the VTOL and multirotor branches,
> and, since the round trip, the camera items against QGC's own re-export. **The QGC round
> trip is clean (2026-09-30):** after one camera value was matched, a fresh default plan has
> exactly the same values as `roundtrip_qgc.plan`. The S2/S3 takeoff question was then
> with BlackSwift (answered 2026-10-13); it blocked a flight test, not J. Everything below marked
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
- **Home position** = the plan's own takeoff coordinate, which is Terrace Point by default.
  It is derived by `outputs._qgc_home` rather than read from a constant (decided
  2026-09-22), and its altitude is `TERRACE_POINT_AMSL_m`.

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
list — the engine's truth — and `_serialize_qgc(plan, items)` renders it. The plan comes
first, as in every other `outputs` function. A future
`_serialize_blackswift(...)` is then a sibling, not a rewrite. This split is what keeps the
two-consumer requirement from becoming a fork.

**Two slices of later steps were pulled forward, because J cannot emit a correct file
without them. Both are BUILT as of J-2/J-3:**
- ✅ *From G:* the **vehicle class**, built as `Vehicle(Aircraft)` rather than as a field on
  `Aircraft` — it carries `vehicle_type`, `firmware_type`, `is_VTOL` and `hover_speed_ms`.
  Same move `Sensor.mounting` already makes: record the assumption as data on the object
  instead of burying it in a formula. **At J, neither class in use needed a transition
  altitude** (the S2 was a pure fixed wing; custom vehicles are pure rotorcraft), and
  `TRANSITION_REL_m = 50` had no instance. Since K-3 the default S3 is a VTOL, and since
  2026-10-27 `TRANSITION_REL_m` is 10 and is its takeoff altitude. ✅ `planner._BlackSwift_S3`
  constructs a `Vehicle` (the S2's `_Black_Swift` until K-3).
- ✅ *From F:* the **along-track overlap** on `Sensor`, because distance triggering needs a
  spacing. `Sensor` now carries `cross_track_overlap` and `along_track_overlap` separately,
  and `geo.ground_footprint_along_m` finally has a caller. Measured: footprint **561.48 m**,
  spacing = footprint × (1 − overlap) = **280.74 m at 50%** = one frame every 13.4 s at the
  S3's 21 m/s (15.6 s at the S2's 18), carried as `metrics["camera_trigger_distance_m"]`.
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

Measured from Terrace Point, for the S2 at J-4: **22,386 m to M1**, bearing 169.6°,
round-trip transit **44.8 km ≈ 41.5 min of a 90 min battery** at 18 m/s, barely varying with grid size (45,239 m at N=15
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
  battery** before a single science line is flown (47% of the S3's usable distance, which
  gets 11 lines from that boat against 9 from the shore). That reframes Step F from partner
  convenience into the largest efficiency lever the engine has.

**✅ LAUNCH AND RECOVERY — SETTLED, AND SIMPLER THAN FEARED** (decided 2026-09-08, for the
S2; history). Since K-4 the default S3 takes off vertically to its 10 m transition height,
climbs in an orbit at the climb point, descends along the approach and lands vertically,
so the `.plan` carries `NAV_VTOL_TAKEOFF` (84) and `NAV_VTOL_LAND` (85). A fixed wing still
gets what follows. The S2 **launches from a stand** and **lands on its belly at a very low stall speed with
steep descent capability**, which is precisely why Terrace Point works as a single pad. So:
- **`geo` needs no approach geometry.** J-5 emits a plain land item at the pad coordinate.
  No landing pattern, no loiter-to-alt, no new geometry anywhere.
- **The approach direction is a RECOMMENDATION to the RPIC**, derived from the wind math and
  delivered in the pilot-notes PDF — never baked into the `.plan`. This is constraint 4
  applied to landing: the engine computes and advises, the pilot decides. **The RPIC can
  always take manual control of the landing, as with any QGC plan.**
- **⚠️ The `.plan` still encodes an approach direction implicitly**, and as of **J-4.5 the
  engine now computes and carries it** — `plan.approach_bearing_deg` = **344.6°**,
  `plan.departure_bearing_deg` = **174.8°** for the S2 at J-4.5 (343.3° and 176.3° for the
  S3). A *fact of the geometry*, not a wind decision,
  and the RPIC must be told it. This gives the pilot-notes document its **first genuinely
  operational customer**: compare the arrival bearing against the into-wind heading and
  state the headwind/crosswind/tailwind component the pilot will meet. A belly-landing
  airframe on a tailwind approach is exactly the case worth warning about. Details and
  caveats in [Current state](#current-state--what-the-engine-actually-does-context-for-future-work).
- The **launch item's altitude** is a climb-out altitude, not the 609.6 m mission altitude
  the launch waypoint carries. Set in J-1 as `TAKEOFF_REL_m = 50` (relative frame), with
  `LANDING_REL_m = 0` for the land item. Since K-4 a VTOL's takeoff item takes the plan's
  transition height instead (10 m for the S3).
- **✅ ANSWERED 2026-10-13, and moot: the S2 is end of life.** The S3 never flies back over
  home; it climbs in an orbit to a takeoff waypoint (see
  [BlackSwift response](#blackswift-response--2026-10-13-supersedes-the-s2-vehicle-facts)). The question as it stood, kept as history:
  **how the S2 behaves with its takeoff waypoint on the launch point** (recorded
  2026-09-22, when the user could not answer it; **asked BlackSwift 2026-09-30, for the S2 and
  the S3, reply pending**). Our `NAV_TAKEOFF` sits exactly on the pad
  (0.0 m from home). QGC's own fixed-wing export (`exp2.plan`) puts it **71.7 m out at
  64.1°**, as a climb-out target. The file cannot tell which of two things the S2 does
  during the climb to 50 m:
  - **(a)** it holds the launch heading from the stand to clearance altitude, then turns for
    the first grid waypoint. This is the intended behaviour, and it keeps the launch
    direction with the stand and the RPIC's read of the wind, per constraint 4.
  - **(b)** it treats the takeoff point as a position to reach, and loops back over the pad at
    low altitude before heading out.

  QGC's display cannot distinguish them. **Asked BlackSwift on 2026-09-30, for both the S2
  and the S3; the reply is pending.** The S3 half bears on the VTOL branch
  (`NAV_VTOL_TAKEOFF`, 84), which has no instance today. A PX4 SITL run shows what PX4 does,
  which answers it for the S2 only if the S2 runs PX4's takeoff logic: this file names
  BlackSwift's FMS as the S2's consumer (see "Two consumers" above), and `firmwareType 12`
  in our output is unconfirmed for it. It does not gate the close of J. If the answer is (a),
  no change is needed. Do **not** move the waypoint along
  `departure_bearing_deg` without that answer, because that would be the engine choosing a
  launch direction. The landing has no equivalent question: `NAV_LAND` approaches along the
  line from the last grid waypoint (344.6°).
- **✅ Speed is not commanded, by design (confirmed 2026-09-22).** The header `cruiseSpeed` is
  a QGC planning estimate only; a MAVLink mission upload carries items, not the header. The
  aircraft flies its autopilot's configured cruise speed. The user confirmed the S2's was
  18 m/s, the speed every budget assumed until K-3. Since K-3 the default is the S3 at
  **21 m/s = `BLACKSWIFT_S3_CRUISE_SPEED_ms`**, which the header carries. The S3 doesn't fly
  a QGC file at all (it flies BlackSwift's XML, which the engine does not write), so the
  header speaks only to a QGC-flown vehicle. So no `DO_CHANGE_SPEED` (178) is emitted. **Step G must revisit this:** once the
  aircraft is user-settable, the engine's cruise speed and the autopilot's can differ.
  Emitting a `DO_CHANGE_SPEED` after takeoff is then the fix (QGC's own "Flight speed"
  setting does exactly that).

**Step table:**

| Step | File | Work | State |
|---|---|---|---|
| J-0 | — | Pin schema against the field list; confirm takeoff/land commands per vehicle class | ✅ |
| J-1 | `constants.py` | Terrace Point coords (launch = land); along-track overlap; climb-out altitude (`TAKEOFF_REL_m`); per-command param constants in `[2,3,16,21,22,84,85,206]` order; schema literals | ✅ |
| J-2 | `objects.py` | `Vehicle(Aircraft)` with MAVLink identity; `Sensor` split into cross/along-track overlap; `CandidatePlan` trigger-distance + total-flight-distance fields | ✅ |
| J-3 | `geo.py` | Trigger distance into the metrics dict (along-track FOV/overlap passed as **parameters**, not read from `constants`); `total_route_distance_m` → `total_grid_distance_m` | ✅ |
| J-4 | `planner.py` | Reserve the transit before `geo` sizes anything; measure the true transit; bounded retry; duration from the total; `grid_budget_m` vs `usable_endurance_distance_m` split | ✅ |
| J-4.5 | `planner.py`, `objects.py` | Departure + approach bearings measured on the **final** route, reporting only | ✅ |
| J-5 | `outputs.py` | `_plan_items` → `_serialize_qgc` → `write_qgc_plan`; plain land item at the pad | ✅ built 2026-09-22; round trip clean 2026-09-30, after the camera-stop trigger was matched to QGC's |
| J-6 gate | `outputs.py`, `sun.py`, `planner.py`, `weather.py` | Clear every handleable warning before the entry point changes | ✅ 2026-09-22 |
| J-6 | `flight_plan_maker.py`, `planner.py`, `objects.py` | Emit and report the `.plan` path; print grid/transit split and bearings | ✅ 2026-09-25 — split computed in `planner` Step 9, pinned in Tier 3 |
| J-7 | `tests/test_6_outputs.py` | Item ordering, camera toggles paired, monotonic `doJumpId`, per-class frames, home position | ✅ 2026-09-25 — 20 tests, broken 15 ways to confirm each catches its defect; 22 since the 2026-09-30 round trip |
| J-8 | docs | Closeout: warning box narrowed, round trip recorded, stale `Seymour-*` waypoint names fixed (`Terrace-Point-*`, `e0630ff`), status lines | ✅ 2026-09-30 |

**✅ J-5's PREREQUISITE IS CLEARED — `Vehicle` is adopted.** At J, `BLACKSWIFT_VEHICLE_TYPE
= 1` (Fixed Wing) and `BLACKSWIFT_FIRMWARE_TYPE = 12` (PX4) were in `constants.py`, and
`planner._Black_Swift = Vehicle(...)` read them. K-3 deleted both with the S2; the S3 is
`BLACKSWIFT_S3_VEHICLE_TYPE = 21` and `BLACKSWIFT_S3_FIRMWARE_TYPE = 0`. Measured on the
default plan at J:
`vehicle_type 1`, `firmware_type 12`, `is_VTOL False`, `hover_speed_ms 0` — all four fields
`_serialize_qgc` branches on are reachable. `Vehicle.__init__` **raises** on an invalid
vehicle type and **warns + defaults to PX4** on an invalid firmware type, so a typo fails
loudly rather than writing a bad file.

- ✅ **The default plan's aircraft is asserted to be a `Vehicle`** (J-7,
  `test_plan_aircraft_is_a_vehicle`). The gap survived three steps precisely because nothing
  checked.

**✅ Landing item — SETTLED as plain `NAV_LAND` (21)** for a fixed wing, which is what
`_qgc_params` builds; a VTOL gets `NAV_VTOL_LAND` (85), the default S3's since K-3.
`exp2.plan` expresses its fixed-wing landing as a **`ComplexItem` of
`complexItemType: "fwLandingPattern"`** — with `landingApproachCoordinate`,
`loiterRadius: 75`, `loiterClockwise`, `finalApproachSpeed` and `stopTakingPhotos` — not
as a `NAV_LAND` SimpleItem. Why not the pattern: the S2 belly-lands with steep descent
capability and needs no loiter pattern; `fwLandingPattern` would force the engine to invent an approach
coordinate and loiter geometry, which is exactly the work the roadmap settled it would not
do, and its `stopTakingPhotos` flag overlaps our explicit camera items. Note the "never a
`ComplexItem`" rule was aimed at **survey** blocks, which regenerate and therefore destroy
the sun-oriented grid — a landing pattern destroys nothing, so that rule does not by itself
bar this if a partner later requires it.

**Follows J, lower priority:** the **PDF pilot-notes document** from constraint 4 — the
wind / crab / return-time reporting, deliberately kept out of the machine-readable outputs.
Its first operational customer is already known and now computed: the **recommended landing
approach**, comparing `plan.approach_bearing_deg` against the into-wind heading. That is
also the first time any of C-2's wind math will have done real work for anybody. It also
inherits the **pilot notes** (`plan.pilot_notes`, K-6), which end with the final-frame
RPIC note and live in the terminal summary until the document exists.

### What `exp2.plan` settles

`exp2.plan` in the repo root is a **real QGroundControl export for this site** and the only
ground truth available for the format. Read it before writing the serializer. What it
resolves:

**Frames are NOT uniform, and this is the easiest thing in J-5 to get wrong:**

| item | `frame` | `AltitudeMode` | altitude |
|---|---|---|---|
| takeoff / land | 3 (relative) | 1 | `TAKEOFF_REL_m` 50 (a VTOL's transition height, 10, since K-4) / `LANDING_REL_m` 0 |
| cruise nav | 0 (AMSL) | 2 | 609.6 |
| DO camera | 2 (mission) | **omitted** | **omitted** (and so is `AMSLAltAboveTerrain`) |

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
    either way.
  - **The 2026-09-30 round trip kept both of ours.** QGC writes these values when it builds
    a plan itself, and keeps ours when it loads our file.
- **No `DO_SET_CAM_TRIGG_DIST` items appear in it.** The camera reference is
  **`roundtrip_qgc.plan`** instead: our default plan after a QGC load and save on
  2026-09-30, and the first file in which QGC wrote camera items. QGC kept every value but
  one: it set `params[2]` ("trigger once immediately") to 1 on every camera-stop item, and
  ours now writes the same (see the final-frame bullet under the J-5 writer).
  **To repeat a round trip:** generate a fresh file and open a *copy* in QGC with no vehicle
  connected. QGC has no Save As, and its Save writes back to the file it opened. Save, then
  compare the two files with `python -m json.tool --sort-keys`. Anything QGC rewrites is
  something we got wrong.

**What `exp..plan` adds** (the repo's second QGC export, diffed against our output on
2026-09-22):

- **It is the first ground truth for a DO item.** Its opening `DO_CHANGE_SPEED` (178,
  frame 2) carries only `autoContinue`, `command`, `doJumpId`, `frame`, `params` and
  `type`. So QGC writes `Altitude`, `AltitudeMode` and `AMSLAltAboveTerrain` **only on items
  that have an altitude**. `_qgc_item` now omits all three on camera items, keyed on the
  `MISSION` row's `None`.
- **That `DO_CHANGE_SPEED` is QGC's optional Mission Start "Flight speed" setting**, not
  something the vehicle type requires: it has the same vehicle and firmware as `exp2.plan`,
  which has none. See "Speed is not commanded" above.
- It is an **all-relative** plan (`globalPlanAltitudeMode` 1, nav in frame 3), an older style.
  `exp2.plan`'s mixed datum (0) is the one we match.
- **Formatting-only differences** that do not affect loading: QGC writes empty arrays as a
  bracket on its own line, and we write `[]`. Both files end with a newline, as ours now
  does.

### K. S3 adoption (CLOSED 2026-11-03 — K-5 not built)
Decided 2026-10-18, from BlackSwift's answers (see [BlackSwift response](#blackswift-response--2026-10-13-supersedes-the-s2-vehicle-facts)):
retire the end-of-life S2 and make the S3 the default aircraft, before Step F, so F-1 builds
on the aircraft that will fly. The planning artifact's §K has the step cards and the reason
for each change. In outline:
- **S3 constants and identity** replace the S2's, under new names (split, don't redefine):
  the numbers in [BlackSwift response](#blackswift-response--2026-10-13-supersedes-the-s2-vehicle-facts).
  - ✅ **K-1 built 2026-10-27.** The `BLACKSWIFT_S3_*` block sits **beside** the S2 block,
    with `BLACKSWIFT_FMS_LOOKAHEAD_s` = 3.0, `CLIMB_ORBIT_RADIUS_m` = 500,
    `CLIMB_ORBIT_PAD_CLEARANCE_m` = 100, `OPERATOR_HANDOFF_RESERVE_min` = 1 and
    `EXTENSION_XML`. The S2 block was **deleted in K-3**, with its last reader (the R-3/R-4
    pattern). The user's decisions: vehicle type **21 (`MAV_TYPE_VTOL_TILTROTOR`)**,
    firmware **0 (`MAV_AUTOPILOT_GENERIC`)**, and `BLACKSWIFT_S3_MAX_HOVER_SPEED_ms` =
    **1 m/s** (2026-10-27: the S3 was not designed to travel laterally in hover and almost
    never does). The user renamed the 70 m allowance to `PX4_CAMERA_EARLY_START_m`, and it
    is still `rollout_inset_m`'s default.
  - ✅ **K-2 built 2026-10-27.** `Vehicle` takes optional `transition_height_agl_m` (only a
    VTOL may have one; it raises otherwise) and `waypoint_lookahead_s`, with getters and no
    setters. `aircraft_math.waypoint_capture_distance_m(vehicle)` = 2 × cruise × lookahead,
    or `None` without one. `MissionRequest` takes an optional `climb_waypoint` (`climb_wp`).
    Nothing read any of it until K-3 and K-4, and K-2 left the default plan byte-identical.
  - **No "who flies it" field (decided 2026-10-27).** The planning difference between
    BlackSwift's flight management system and PX4 is already carried by the lookahead.
    Which files get written is an **output choice**, not a fact of the vehicle. DJI will
    mix XML and KML too, so tying output types to the flight controller would fight that.
    K-6 decides it as an explicit selection or as "write every format".
  - ✅ **K-3 built 2026-10-27. The S3 is the default aircraft.** `planner._BlackSwift_S3`
    and `_BlackSwift_S3_usable_endurance_m` replace `_Black_Swift` and its budget. The S2
    block in `constants.py` is gone, and nothing reads a `BLACKSWIFT_*` S2 name. Tier 5's
    checks of a fixed wing's commands fly `_fixed_wing_plan()`, a PX4 fixed wing built from
    literals, and `_plan_built_with` sizes each plan from its own aircraft's battery. Tier 3
    pins that the default plan's budget is its own aircraft's: handing it the S2's
    82,620 m passed every other test.
  - **Measured default plan after K-3** (2026-01-01, 9 m/s design wind):
    - **9 lines**, usable 96,390 m, grid budget 51,617 m.
    - Grid 41,234 m / 32.7 min, transit 45,206 m / 35.9 min, **68.6 min, 21.4 min margin**.
    - Inset 545.9 m, line 1 lead-in 109.6 m at a 118.8° entry.
    - Departure 176.2°, approach 343.4°.
    - **65 `.plan` items, commands 16×45, 206×18, 84×1, 85×1**: VTOL takeoff and land, so
      the QGC `TRANSITION_*` constants are in play. Header: vehicle 21, firmware 0,
      cruise 21, hover 1.
  - K-3 was an intermediate state; its numbers are superseded by K-4's below. At 77.6 m,
    2·R_g = 316.7 m at 9 m/s, more than the 313.4 m line spacing: the two turns between
    lines no longer fit (W* = 8.84 m/s). K-8 (2026-11-03) rewrote the S2-era default-plan
    figures elsewhere in this file. An S2 number that remains is labelled as the S2's or as
    history.
- **Takeoff and landing phases:** a hover takeoff, a transition at ~10–15 m AGL, an orbit
  climb to a takeoff waypoint, and the descent along the approach.
  - ✅ **Transition standardized 2026-10-27 (the user, with permission to edit these QGC
    constants):** `TRANSITION_REL_m` = **10** and `TRANSITION_AMSL_m` = 10 +
    `TERRACE_POINT_AMSL_m`, for every VTOL. The S3 takes `TRANSITION_REL_m`, and
    `BLACKSWIFT_S3_TRANSITION_AGL_m` is gone. Until then `TRANSITION_REL_m` had **no
    reader**: a QGC VTOL took off to `TAKEOFF_REL_m` (50 m), which is where it transitions.
    The plan now carries `transition_height_agl_m` (the vehicle's own, else
    `TRANSITION_REL_m`, else `None` for a vehicle that never transitions), and `_plan_items`
    gives a VTOL takeoff that altitude. A fixed wing or multirotor keeps `TAKEOFF_REL_m`.
    `TRANSITION_AMSL_m` still has no reader.
  - ✅ **K-4 built 2026-10-27.**
    - **Climb point:** `MissionRequest.climb_wp`, or by default the centre of an orbit on
      the departure bearing, `CLIMB_ORBIT_RADIUS_m` + `CLIMB_ORBIT_PAD_CLEARANCE_m` (600 m)
      out from the pad, in line with line 1's first waypoint. It is a plan field
      (`climb_waypoint`, `climb_orbit_radius_m`), **not** a waypoint, so the `.plan` and the
      KML keep their shape. The outbound transit runs through it, the departure bearing
      points at it, and Strat 1 measures line 1's arrival from a given climb point.
    - **Phases:** the climb from the transition height over the pad to cruise altitude
      (583.6 m, 2.90 min), and 2 × `OPERATOR_HANDOFF_RESERVE_min`. The descent rides the
      approach leg: `descent_overrun_min` charges only what that leg can't hold. All are
      reserved, as cruise-distance equivalents, before `geo` sizes the grid and inside
      J-4's fit loop, and added to the duration. The transit remainder (J-6) carries them.
    - **Early camera start:** a vehicle with a lookahead starts early by its capture
      distance (126 m for the S3), so the default inset is 601.9 m.
    - **Shortest leg:** `_check_minimum_legs` raises if any leg is shorter than the capture
      distance. It's geometry, a sizing failure, not a gate.
    - **Applies to every vehicle:** there is no "who flies it" field, so a PX4 vehicle is
      also charged the orbit climb and the hand-offs. That's conservative.
  - **Measured after K-4** (2026-01-01, 9 m/s): **9 lines, 74.3 min, 15.7 min margin**
    (grid 33.5 / transit 40.8 min, 87,460 m flown). Inset 601.9 m, lead-in 110.3 m at
    119.0°, departure 176.3°, approach 343.3°. The climb point is 600 m out on 176.3°. The
    shore approach is 22.8 km, against the 6.8 km the descent needs, so the overrun is 0.
    The `.plan` has 65 items, its VTOL takeoff at 10 m. **The K-3 prediction of 7 lines was
    wrong:** it charged the 5.4 min descent as extra time, which the descend-on-approach
    answer removes. The boat 2 km north of M1: 11 lines, 59.7 min, a 3.6 km approach and a
    **2.5 min overrun**. It now arrives at 113.9° with an 85 m lead-in, not the S2's 178.2°.
- **K-1 to K-4 and K-6 were committed by the user** (`b3337b6`, `677f68a`, `afcb6f4`, `701794c`). The two
  decisions left open at the 2026-10-27 pause were settled on 2026-11-03:
  1. **Per-vehicle phase charging is left to Step G.** The default aircraft may change
     soon, so no more S3-only work is wanted until that is settled.
  2. **K-6's summary half is built** (2026-11-03), with the user's addition: pilot notes for
     winds above the aircraft's wind rating and for weather that isn't a forecast. See the
     K-6 bullet under Current state. The S3-only belly-landing note was not built.
- ✅ **K-7 built 2026-11-03: the test audit.** Every test the K-7 card listed already
  existed from K-2 to K-4, except the BlackSwift XML tests, which went with K-5. Four
  branches had no test, and a break of each passed the suite: a fixed wing's takeoff
  altitude (unpinned since K-3 made the default a VTOL), a VTOL's own transition height,
  the pilot notes' choice of wind rating, and the summary's "from the pad". One new Tier 5
  test and three extended tests now catch all four: 120 tests.
- ✅ **K-8 built 2026-11-03: the docs.** CLAUDE.md's S2-era figures were re-measured on the
  S3 and rewritten, or labelled as the S2's history. README was already current.
- ❌ **K-5, the BlackSwift writer, was NOT built (the user, 2026-11-03).** The default
  aircraft may change, and the writer would be lost work if BlackSwift goes. It would write
  three XML files (takeoff, mission, landing) as a sibling of the QGC writer, from the same
  neutral item list, in the format of BlackSwift's example files (the format, not a
  template). Those files are local only and must never be committed: the repo is public,
  so a K-5 test could not read them from the repo as the J-7 tests read QGC's files.
  It needs BlackSwift's answers first: altitude units and datum, home, waypoint numbering,
  climbs a leg can't hold, how a vertical landing is written, camera control, orbit radius
  limits, and FLY_OVER. The planning artifact lists them as questions 1–9. **Revisit only
  if BlackSwift stays.** K-6's writer selection goes with it: which writers run stays an
  output selection, never inferred from the vehicle (see the K-2 decision above).
- ✅ **Tests** that read the S2 as the default aircraft were rebased in K-3, and the gap
  K-3 left (a fixed wing's takeoff altitude) was closed in K-7.

### F. Mission and aircraft configurability (NEXT — DESIGN SETTLED 2026-11-06)
Per constraints 2 and 3 as amended on 2026-11-06. Step F's goal is **plans ready for a
real-world test on a PX4 VTOL and a hexacopter, both flown through QGC.** It takes in most
of Step G (aircraft profiles, the multirotor branch, per-vehicle phases) and Step E's
legality checks. The design was settled with the user in a 33-question session on
2026-11-06. **Nothing is built.** The user wants to be closely involved in this phase:
F-1's functions are agreed with the user before any code or artifact change.

**▶ START HERE (2026-11-06): the F-1 function discussion.**
- **Git.** PR #3 merged as `f2dab26` on `origin/main`. Local `main` was at `aef8a40` at the
  pause. F starts on a fresh branch from an updated `main` (the user's git).
- Open with the [F-1 agenda](#f-1-for-discussion). Agree each function's job, signature and
  home module with the user, then update the planning artifact, then write code.

#### Decided 2026-11-06
- **Refusals.** No unflyable plan is ever written: the user is told why, and no files are
  written. Unflyable means a route longer than the battery, invalid input, geometry the
  vehicle can't fly, or a legality failure. A legality check refuses only when its data is
  available. With no data, the plan is made and a pilot note says what went unchecked
  ("trust the pilot", the user). Wind and weather minima stay reports (constraint 4). This
  closes Step E's endurance-gate question.
- **A requested grid too big for the battery** is refused, and the reason names the closest
  grid that fits. This replaces F-0's "report the closest and proceed".
- **Agents use the CLI.** `--json` prints the result, or the refusal reasons, as one object.
  Exit codes: 0 plan written, 1 refused, 2 engine error. A command lists every setting with
  its unit, default and range. No Python API or MCP server.
- **CLI ≡ config.** One schema defines each setting once, and the JSON config key and the
  CLI flag both come from it. The CLI overrides the file (`--mission FILE`), which
  overrides the defaults. The summary and the JSON mark each value as default or given,
  never as file or CLI, so a plan made either way writes identical files.
- **Resolved settings.** Every run writes its resolved settings as JSON beside the outputs,
  with each profile's name, a hash of its contents, and the engine version. Re-running that
  file refuses if a profile has changed since; a different engine version adds a note. The
  flight files never read the weather, so they reproduce exactly.
- **Aircraft** is a named profile, **required, with no default**. The S3 stays as a built-in
  profile and anchors the regression tests. Operator hand-offs become a profile field: 2 for
  the S3, 0 for PX4 vehicles, whose missions run straight through.
- **Profiles and sites are JSON.** The built-ins the tests need live in the repo. Users' own
  aircraft, authorization and site files stay on their machines, outside the repo, at a
  location the user gives: the engine assumes no user directory.
- **Camera.** Both test aircraft hard-mount it, with pitch compensated in the mount and the
  maximum pitch limited in software, so 30° off-nadir holds and the geometry is unchanged.
- **VTOL phases (PX4).** The takeoff item sits 300 m out on the departure bearing (QGC's
  default) at the transition height. A loiter-to-altitude item (MAV_CMD 31) at the climb
  point climbs to mission altitude. Its radius comes from the profile, and a mission can
  override the radius and the climb point. Homeward, a top-of-descent waypoint, then a low
  waypoint near the pad, make it descend along the approach before VTOL land.
- **Hexacopter phases (PX4).** It climbs vertically over the launch to mission altitude, and
  descends along the return leg to a low waypoint over the landing point. Any remainder is
  vertical, and budgeted. A speed item (MAV_CMD 178) sets its cruise speed. Its collection
  inset is the distance to accelerate from corner speed back to cruise, each corner's
  slow-down is turn time, and Strat 1 doesn't apply.
- **Acceptance radius** is written as 0 on every nav item, so each vehicle uses its own (the
  user's decision on the QGC constant `ACCEPTANCE_RADIUS_m`).
- **F-1.5 is option B.** Strat 1 is capped at **120°**, just past the 117.7° entry the PX4
  sweep validated, and above it an RPIC note says line 1's first image may be banked. It
  applies to vehicles that bank through turns.
- **Grid.** The centre is a location (default M1), and a plan can be made anywhere on earth.
  Any line count from **1** up. An "overfly the centre" flag, off by default, forces an odd
  count. A request is **line length + grid width**, both or neither, measured as the
  **imaged** box, with the line count rounded up. Area is reported, never requested.
- **More settings:** mission altitude, battery reserve % and which outputs to write. The
  glint target and tolerance stay constants.
- **Legality** compares the plan with a named authorization profile, required from F-6.
  Checks: ceiling, operating area, line-of-sight range, the daylight window, the
  sanctuary's overflight zones, FAA airspace classes and TFRs.
- **Time.** `--time` is takeoff, in a time-zone setting (default `America/Los_Angeles`), with
  UTC shown in the summary and notes. The grid is oriented for the sun at mid-grid: over M1
  the azimuth moves 4.5° in 20 min on a January morning and 19.8° on a June early
  afternoon, against the 15° glint tolerance.
- **Weather** comes from both the launch and the grid centre. The notes compare the stronger
  wind with the rating and say where. NWS covers M1 (gridpoint MTR 89,57).
- **The Monterey defaults stay:** centre M1, launch and land at Terrace Point (16 m), design
  wind 9 m/s, Pacific time.

#### The settings (the user's requirement 4)
Names are provisional until F-1 settles them.

| Mission setting (a JSON key and a CLI flag each) | Default |
|---|---|
| `name`, `out_dir`, `outputs` (kml, png, plan) | "V2 Plan", `./CALYPSO_OUTPUT`, all three. The resolved settings are always written. |
| `date`, `time` (takeoff), `timezone` | 2026-01-01, 10:00, `America/Los_Angeles` |
| `aircraft` | required: a profile name |
| `authorization` | required from F-6: a profile name |
| `launch`, `land` | Terrace Point. A site name or lat/lon/elevation AMSL; `land` defaults to `launch`. |
| `centre`, `overfly_centre` | M1, false |
| `line_length_m`, `grid_width_m` | none, which fills the battery with a square grid |
| `altitude_m` (AMSL), `design_wind_ms` (aloft), `battery_reserve_pct` | 609.6, 9, 15 |
| `cross_track_overlap_pct`, `along_track_overlap_pct` | 50, 50 |
| `off_nadir_deg`, `climb_point`, `climb_orbit_radius_m` | the profile's, or computed; a mission may override |

- **Aircraft profile:** MAVLink vehicle type (13 hexacopter, 21 or 22 VTOL) and firmware
  type; endurance, cruise speed, wind rating, climb and descent rates, operator hand-offs,
  and an optional waypoint lookahead. Fixed wing or VTOL: turn radius, turn penalty, stall
  speed. VTOL: transition height (10 m), takeoff transition distance (300 m), climb-orbit
  radius, hover speed. Multirotor: horizontal acceleration, hover speed. Payload: sensor
  name, both FOVs, mount, off-nadir angle (30°).
- **Authorization profile:** regime label; ceiling AGL; an operating-area polygon or none;
  BVLOS approved, or a line-of-sight range; twilight allowed; night allowed; sanctuary
  permit; authorized airspace classes.
- **Site:** name, lat, lon, elevation AMSL. Terrace Point is built in.
- **Constants, not settings:** glint 90° ± 15°; the rollout constants (2.5, 80, 70, still
  provisional); the Strat 1 cap (120°); the 1-line minimum; 1 min per hand-off; the QGC
  constants.

#### Slicing (all seven land before the flight test)
| Step | Builds |
|---|---|
| F-1 | Settings and places: see [F-1, for discussion](#f-1-for-discussion) |
| F-2 | Aircraft profiles (built-in S3, test VTOL, test hexacopter) and PX4-correct plans: per-class phases, the new `.plan` items, home from the launch point rather than the takeoff item, the multirotor grid branch, pilot notes (`TRIG_MODE=4`; hand-offs only when the profile has them), QGC round trips on both aircraft |
| F-3 | The remaining mission settings: altitude, reserve, overlaps, off-nadir, outputs, climb point and radius |
| F-4 | The grid model: centre as a location, any count ≥ 1, the overflight flag, the requested imaged box, imaged area. It also decides the fate of the three unread `V1_DEFAULT_*_km` constants, since no default request exists |
| F-5 | The sun at mid-grid, and forecasts at launch and grid centre |
| F-6 | Legality: authorization profiles and the seven checks |
| F-7 | Audit, docs, PR log |

**Regression baselines move on purpose.** Acceptance radius 0, the VTOL items and the
mid-grid sun all change the S3's `.plan` and orientation. Re-record the baselines once,
with the reason, and keep tests asserting relationships in N.

#### F-1, for discussion
**Scope:** the settings schema; the JSON config and the CLI flags generated from it;
precedence; refusals with reasons; `--json`, exit codes and the settings listing; the
resolved-settings file; the site library; launch, land, centre and their elevations; the
time zone and strict date/time parsing; the `aircraft` setting, with the S3 its only
built-in until F-2. Settable launch points make four latent defects reachable, so F-1 also
fixes them: the Terrace Point reach-ins, the transit seed, and the two PR #3 bugs. The
Strat 1 cap lands with it.

**Agenda, one function or decision at a time:**
1. How a setting is declared once (name, type, unit, default, range, help), and how its
   flag and JSON key derive from that.
2. Loading and precedence: defaults, `--mission FILE`, CLI. Unknown keys and half a grid
   request are invalid input.
3. The refusal: what carries the rule, the message and, for a grid, the closest fit; which
   of today's `ValueError`s become refusals and which stay engine errors.
4. The `--json` shape beside the human summary, and how defaults are marked.
5. The resolved-settings file: its name, contents, fingerprints and the re-run check.
6. How the user tells the engine where their profile and site files are.
7. Sites: the built-ins (Terrace Point, and M1 as the default centre), the site file, and
   separate launch and land elevations.
8. The `aircraft` setting before F-2's profiles exist.
9. The time-zone setting and strict date/time parsing.
10. Where F-1 takes the sun and the weather: the plan's own launch point, until F-5.
11. The transit seed, the climb point, the minimum-leg check, the Strat 1 cap.
12. Tests: config ≡ CLI with the weather stubbed; refusals; the S3 baseline.
13. The PR #3 small items.

**Code touchpoints (checked 2026-11-06):**
- `flight_plan_maker.py`: `_parse_args` holds five flags; `_design_wind_ms` accepts `nan`
  and `inf`; `main` has no error handling, so a `ValueError` reaches the user as a
  traceback.
- `sun.resolve_mission_datetime` falls back to the defaults on bad input, silently, and
  reads `V2_MISSION_INPUT_TIMEZONE`. `sun.create_sun_state` defaults to the launch
  constants, though every caller passes coordinates.
- `planner`'s module singletons `_BlackSwift_S3`, `_BlackSwift_S3_usable_endurance_m`,
  `_Calypso_payload`, `_Launch_Waypoint`, `_Land_Waypoint` and `_M1_Waypoint` feed only
  `plan_default_mission` and `_build_dated_objects`. `build_candidate_plan` already works
  from its parameters, so F-1 replaces the singletons, not the function.
- **The four Terrace Point reach-ins:**
  1. `_build_dated_objects` builds the sun state at `CONST.V1_LAUNCH_POINT_*`.
  2. It fetches the weather there too, and the clear-sky stub carries those coordinates.
  3. `outputs._qgc_home` gives every home `TERRACE_POINT_AMSL_m` (16 m), even a boat deck.
  4. `build_candidate_plan` Step 2 floors the climb and the descent at
     `TERRACE_POINT_AMSL_m`. A boat launch that lands ashore needs both elevations.
- **The transit seed** `2·d(launch, M1)` becomes `d(launch, centre) + d(centre, land)`. For
  the S2, a boat launch landing at Terrace Point seeded 4.0 km where 24.4 km was right, and
  cost a wasted pass.
- **The two PR #3 bugs** (`claude_prompts/pull_requests.md`):
  - `_default_climb_waypoint` always sits 600 m from the pad toward WP001, and
    `_apply_entry_pushback` measures the arrival from the pad. A pad within 600 m of line 1
    puts the climb point past or beside WP001, the recorded arrival is up to 180° wrong, and
    the orbit overlaps line 1.
  - `_check_minimum_legs` walks `plan.waypoints`, so it checks pad→WP001, which isn't flown,
    and never climb point→WP001, which is.
- `aircraft_math.entry_pushback_m` raises at 180°; the 120° cap sits in front of it.
- `objects.MissionRequest` stores `require_m1_overflight` and `grid_orientation_deg`, and
  nothing reads either. `Waypoint` has no elevation.
- **PR #3 small items:** the stray `test` line in `constants.py`'s docstring (line 19); the
  re-seed test that proves nothing since K-4 (`tests/test_4_grid_assembly.py:174`); a
  `windGust` in an unknown unit isn't marked stale (`weather.py:268`).
- `geo` keeps its signature through F-1: it already takes the centre as a parameter and
  never learns where launch is.

**Facts still needed (none blocks F-1):** the real numbers for both test airframes, for the
user's own profiles; the authority the test flies under; whether a sanctuary permit is held.
Without a permit, every Terrace Point VTOL plan fails the zone check. A hexacopter can't
reach M1 from Terrace Point, so its test plan needs a boat launch.

#### Research behind the decisions (2026-11-06, primary sources, nothing flown)
**PX4** (source v1.16.2, the same logic in v1.17.0; QGC v5.1.5). Where docs.px4.io and the
source disagree, the source is right.
- VTOL takeoff (84): PX4 reads only param4 (yaw). It climbs vertically to param7, yaws
  toward the item's own lat/lon (the mission fails past `MIS_YAW_TMT`), transitions, flies
  there, and goes on without loitering. With the item on the pad, that heading is GPS noise.
- A fixed-wing waypoint counts as reached only within `NAV_FW_ALT_RAD` (10 m) of its
  altitude; below it the aircraft orbits at `NAV_LOITER_RAD` (80 m) until it climbs.
- Loiter-to-altitude (31): param2 is the radius (its sign sets the direction; 0 uses
  `NAV_LOITER_RAD`). param1 = 1 leaves heading for the next waypoint, param4 = 1 leaves on
  a tangent. QGC writes it as a SimpleItem.
- VTOL land (85): it flies at the previous waypoint's altitude, back-transitions
  v²/(2·`VT_B_DEC_MSS`) short of the point (~110 m at 21 m/s), then descends at
  `MPC_Z_V_AUTO_DN` (1.5 m/s). Params 1, 3 and 7 are unused.
- Multicopter: takeoff (22) climbs vertically to param7. param2 acceptance is honoured only
  on multicopters. A 90° corner is flown at √(`MPC_XY_TRAJ_P`·`MPC_ACC_HOR`·R·tan(α/2)):
  1.7 m/s at R = 2 m, 6.5 m/s at 28.5 m. Speed is `MPC_XY_CRUISE` (5 m/s) unless a 178
  sets it, and a VTOL transition resets it. `MPC_YAW_MODE` 0 points the nose along the
  track. Vertical speed is held to 3 m/s up and 1.5 m/s down by slowing the whole leg.
- The camera trigger (206) works on multicopters and on VTOLs in either mode, with
  `TRIG_MODE=4` set on the vehicle.
- MAVLink types: hexarotor 13, tilt-rotor VTOL 21, standard VTOL 22; PX4 firmware 12.
  Missions hold 500 items by default, and the geofence is off by default.
- A multicopter flying forward pitches nose-down, which tips a forward-pitched camera toward
  nadir (30° − θ, not + θ). The user's mounts compensate for it.

**Airspace and the sanctuary** (eCFR current 2026-11-04; FAA chart cycle 2026-10-29 to
2026-12-24):
- 15 CFR 922.132(a)(6) bars motorized aircraft below 1,000 ft over four Monterey Bay
  sanctuary zones, and NOAA says it covers drones. Zone 1 runs from mean high water to
  3 nmi offshore, between 220° true off Point Santa Cruz and 240° true off 2 nmi north of
  Pescadero Point, so it begins at the shore below Terrace Point. A climb or descent below
  1,000 ft there needs a sanctuary permit (§922.133); an FAA authorization doesn't replace
  it. M1, the grid and a boat near M1 are outside all four zones. NOAA publishes no zone
  data, so build it from Appendix B's text. The sanctuary boundary is at
  `sanctuaries.noaa.gov/library/imast/mbnms_py2.zip`.
- The pad and the first ~8.3 km of the route sit under Class E from 700 ft. At 2,000 ft the
  cruise is in Class E. Monterey's Class C shelf (1,500–4,200 ft) is 3.0 nm southeast of
  M1. No special-use airspace is near, and M1 is inside the 12 nm territorial sea.
- Part 107: 400 ft AGL (§107.51) and visual line of sight (§107.31). Outside Alaska, civil
  twilight is the 30 min before official sunrise and after official sunset (§107.29(c)),
  flown with an anti-collision light. Under a public COA, BVLOS needs a concept of
  operations sent to AFS-750, and flight above 400 ft needs CAPS (Notice N JO 7200.21).
- Data with no key needed: the FAA ArcGIS `Class_Airspace` and `Special_Use_Airspace`
  FeatureServers (8-week cycle), UAS Facility Maps, the TFR list at `tfr.faa.gov`
  (undocumented), and NOAA's 12 nm line KMZ.

#### History (scoping before 2026-11-06)
- **F-0, decided 2026-10-09:** F-1 first; a mission config file, keeping the existing flags;
  both sizing modes, with "fill my endurance" the default. Its fourth decision, "report the
  closest grid and proceed", was replaced on 2026-11-06 by refusing and naming the closest.
- ✅ **Along-track overlap already exists:** J-3 pulled it forward. `Sensor` carries both
  overlaps, and `geo` takes both as parameters.
- **The launch point is the highest-value knob.** Transit is 54% of the battery from Terrace
  Point (47% of the S3's usable distance). For the S3, a boat 2 km north of M1 gets 11
  lines against the shore's 9. With the S2 that boat arrived at 178.2° and spent 7,990 m on
  Strat 1's lead-in, the case the 120° cap now bounds.
- **F-4 also undid most of the rollout fix's cost for the S2** (history: for the S3 the
  default holds 9 lines up to a 14.1 m/s design wind, so F-4's case now rests on
  configurability alone). For the S2 the camera-rollout inset dropped the default grid from
  9 lines to 7 at any design wind above ~2.8 m/s, and the square-grid rule
  (side = offset × (N − 1)) then shrinks the lines too, to 56% of the area. With line length
  independent of N, the freed margin buys longer lines. Measured 2026-10-09 at a 9 m/s
  design wind: 7 lines, 1.5 km longer, 6.36 km² against today's 6.29 km², with a 12.9 min
  margin. The box is 1.9 × 3.4 km instead of 2.5 × 2.5 km, which is a science call.
- **The Strat 2 loop (noted 2026-10-06; not built, because F-1.5 chose option B, the 120°
  cap, on 2026-11-06).** The camera-rollout fast track (see Known
  defects) fixes each line's entry with a longer collection inset, plus **Strat 1** for the
  turn from the transit onto line 1: line 1's first turn waypoint moves back along the line,
  with no new waypoints. Strat 1's cost grows with tan(θ/2) of the arrival angle θ, and it
  passes the loop's cost at about 118° at every wind speed. Shore launches arrive at
  1°–126° (S3, 2026-11-03), but a launch point F makes settable (a boat) can arrive near
  180°.
  - **The Strat 2 loop:** keep the outbound heading, turn onto a leg running opposite to
    line 1 and offset from it by 2·R_g, then make a 180° turn onto line 1 with a straight
    run-in before the camera starts.
  - The same loop replaces the two 90° turns **between lines** once the design wind passes
    `W*`, where 2·R_g is wider than the 313.4 m line spacing. For the S3, W* ≈ **8.84 m/s**,
    under the 9 m/s default design wind (11.8 m/s for the S2).
  - Size the offset from R_g at the design wind, never from the still-air radius (77.6 m
    for the S3). For the S2 at 15 m/s, a 114 m offset overshot line 1 by up to ~270 m.
  - **The 2026-10-08 sweep makes the case for the loop stronger.** Most of D_level is not
    the turn but the overshoot and S-turn after a downwind 90° fly-by onto the line, which
    PX4 did even in still air (the S2 in SITL: D_level 180–188 m against a 57 m radius). A loop or lead-in
    that joins the line's axis outside the grid is designed to remove exactly that. It
    needs its own sim sweep before it is built, because waypoint-following is not
    arc-following. **That sweep was requested 2026-10-09** (the user's choice: now, in
    parallel with building Strat 1). It also validates Strat 1 at the 9 m/s default, tests
    turns flown through waypoints on an arc, and compares the loop with Strat 1 onto line 1
    at a 160° arrival. Results go to `~/Desktop/S2 Strat 2 Loop Sweep Results.md`.
    **Cancelled 2026-10-18; the prompt was never sent, so it was never flown.** It was
    written for the S2, which is end of life. A loop sweep for the S3 needs an S3 model, and
    BlackSwift declined to share theirs or its numbers on IP grounds (2026-10-27).
  - The turn onto line 1 depends on the launch point, so its loop lives in `planner`, and
    `geo` still never learns where launch is. The loop between lines is grid geometry and can
    live in `geo`, with R_g passed in as a parameter.
  - **Measured 2026-10-18 for the S2, once Strat 1 was built:** the Tier 3/5 boat launch
    2 km north of M1 arrived at 178.2°, and Strat 1 pushed line 1's first waypoint back
    **7,990 m**. With the S3 (K-4) that boat arrives at 113.9°, so today's test boat no
    longer reaches the blow-up, but a launch point F-1 makes settable can. A
    near-reversal fly-by is not what the formula models, and with the S2 sweep cancelled no
    simulation shows what the S3 would fly instead. F-1 makes this reachable from the CLI, so F-1.5,
    or a cap on Strat 1 the user chooses, has to land with or before F-1. **Decided
    2026-11-06:** the 120° cap, which lands with F-1.

### G. Aircraft configurability (TAKEN INTO STEP F, 2026-11-06)
**Step F builds this now** (F-2): named aircraft profiles, the multirotor branch and
per-vehicle phases, for a PX4 VTOL and a hexacopter. What follows is the scoping it came from.
Per constraint 3. Fixed-wing, quadcopter, or hexacopter, with every fixed-wing performance
constant user-settable rather than hard-coded to the BlackSwift S3 (the S2 until K-3).
- `objects.Aircraft` is already a general constructor — the hard-coding lives in
  `planner._BlackSwift_S3`, a module-level singleton built from `BLACKSWIFT_S3_*` constants (the S2's `_Black_Swift` until K-3).
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
- **Climb and descent: modelled in K-4 (2026-10-27), for every vehicle alike.** Every
  vehicle is charged an orbit climb from its transition height and two operator hand-offs,
  and descends along its approach. G makes that per vehicle (left to G by the user,
  2026-11-03): a fixed wing that climbs on its way out is over-counted today, and a
  multirotor hovers its whole climb. The rates are
  still the S2's provisional 3.35 and 1.80 m/s.
- **Vehicle facts (updated 2026-10-13):** the S2, a pure fixed wing, is **end of life**. The
  tri-motor VTOL **S3 is the default and only non-copter aircraft**, and Step K adopts it
  ahead of G. Custom partner vehicles are essentially always **rotorcraft** on PX4/QGC.
  Nothing is ever hand-launched.

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
  grid **91,52** when written, **90,66** when re-checked on 2026-11-06, so never hard-code
  it), then `GET` that gridpoint doc. Fields are time-series with a `uom`:
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
`make_lawnmower_grid_through_m1`, so it changes every plan today (+1,908 m per line for the
S3 at the 9 m/s default since the rollout fix; +808 m per line, grid distance 82,320 m, when
this was written). **Everything else built in C-2 has zero callers**:
`wind_correction_angle_deg`, `ground_speed_ms`, `effective_lawnmower_speed_ms`,
`return_time_min`, `required_reserve_time_min`, `wind_aware_usable_distance_m`,
`max_crosswind_tolerance_ms`, `cross_wind_component_ms`, `head_wind_component_ms`,
`furthest_point_distance_m`. `Weather.wind_is_measured` and `.stale_fields` are read by
the summary's forecast line and, since K-6, by the pilot notes. `route_duration_min` accepts `weather`/`axis_deg` but `planner` calls
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
- `|δ| ≤ 15°` ⟺ crosswind across the science axis ≤ `V·sin(15°)` ≈ **5.44 m/s** at the
  S3's 21 m/s cruise (4.66 m/s at the S2's 18). Report it as **science-quality headroom** for the RPIC, never as a gate.
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
**Taken into Step F on 2026-11-06 (F-6),** with the endurance question below decided.
`validator.py` holds only a docstring, and that docstring describes the **cancelled** RTH
gate — read it as history. What remains for E:
- **Legality** — Part 107 and friends: **altitude ceiling** (the default is 609.6 m /
  2000 ft; COA authorization is in progress with partners and may go **higher**, so gate on
  the ceiling the mission is *authorized* for, never a hard-coded 400 ft);
  **daylight / civil twilight** (use `CurrentSunState.elevation`); **VLOS**; **airspace
  authorization**; **over-water operations**.
- **✅ Decided 2026-11-06: an unflyable plan is refused, with its reasons.** A route longer
  than the battery, invalid input, geometry the vehicle can't fly and a legality failure all
  refuse; a requested grid too big is refused, naming the closest that fits. The question
  as it stood, kept as history:
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
  B (live NWS weather), C-1 (along-track mount) and J (JSON `.plan` output, completed
  2026-09-30) and K (S3 adoption, closed 2026-11-03 without the BlackSwift writer) are
  done**. Remaining, in execution order: **F** (mission and aircraft configurability, with
  E's legality checks; design settled 2026-11-06), **C-2 re-scoped** (wind reporting),
  **D** (sun/cloud ranking).
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
