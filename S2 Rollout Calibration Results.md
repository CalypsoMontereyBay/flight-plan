# S2 rollout calibration sweep: results

Flown 2026-10-08 in uas_sim (Gazebo + PX4 v1.18 SITL), for flight-plan's turn-model fix to the
camera-rollout defect (`flight-plan_camera-rollout-issue.md`, run `run-20260928-150115-529e`).
Nothing in the flight-plan repo was changed; every mission was built in the sweep's own folder.

## Summary

- **The planning model holds as an envelope, not as a predictor.** Over the worst wind direction
  at each speed, D_level = **2.48 R_g + 44 m** (R² 0.98, 5 points, every point within 31 m).
  Over all directions, D_level has no relation to R_g (R² 0.003): at 15 m/s it runs from 5 m to
  506 m.
- **What sets D_level is the new line's own tailwind.** D_level ≈ 2.5 x 57 (1 + w_line/18)²
  (R² 0.81). Lines alternate direction, so the downwind one is always there, and a fixed inset
  must be sized on R_g.
- **flight-plan's guess (2 R_g + 50) is short** of the envelope by 24-97 m, before the early
  camera start.
- **Transit entries (117.7°) need about what a turn between lines needs** on this plan. R_g ·
  tan(θ/2) + (a - 1) R_g + b, with the fitted a and b, over-predicts the worst measured transit
  by 9-103 m.
- **PX4's early camera start is up to 71 m, not 50 m,** and it is largest (≈ 2 s of ground
  speed) exactly on the downwind line that is still turning. 25 of 159 entries exceeded 50 m.
- **Part B (inset 325.8 m) fails at 8, 10, 11 and 15 m/s** in the worst directions:
  - 12 of the 13 entries onto a downwind line had image 1 banked 6.6-35° (3 of 9 first images
    failed at 8 m/s, 4 of 9 at 10 and 11, 1 of 3 at 15).
  - Every line flown into the wind passed.
  - Coverage of the box's first 100 m still came out at 98-100 %, but only because the early
    camera start moved image 2 back over the box start.
- **Repeat flights:** identical flights agree within 2-22 m, except one bimodal case at 11 m/s
  (356 vs 449 m). An envelope that clears every flight seen is about 2.5 R_g + 80 m.
- **Planning inset suggested by these runs: about 2.5 R_g + 150 m.** That is the 2.5 R_g + 80 m
  envelope plus about 70 m for PX4's early camera start: ~500 m at 10 m/s, ~630 m at the
  15 m/s rating. Details under "What this means for flight-plan's turn model".
- **Setup notes:** one PX4 parameter changed (`ASPD_DO_CHECKS` 3, see Setup); the sweep flew at
  8x after a speed check; one run was discarded and re-flown for a host-timing fault.


## Setup

### Aircraft, firmware and parameters

- **Same aircraft as 2026-09-28:** `--profile blackswift_s2`: PX4 v1.18.0-beta1 SITL on the
  derived Gazebo model of the S2 (3.048 m span, 9.5 kg, 18 m/s cruise, 57 m still-air turn
  radius, `FW_R_LIM` 30.1°). The profile, the 29 computed PX4 parameters, the physics
  (`physics.json`) and the Gazebo model are byte-identical to run 529e (checked by diff).
- **One parameter changed: `ASPD_DO_CHECKS` 7 → 3** (PX4's airspeed innovation check off; the
  missing-data and stuck-sensor checks stay on). It is in every Part A and Part B run's
  `params.json` and was read back from the autopilot (`param_check.json`).
  - **Why:** in 2 of the first 5 Part A runs PX4 declared the airspeed sensor failed
    (`Airspeed sensor failure detected`, 389 s and 658 s into the flight). The new transit
    approach adds 6-8 km straight, crabbed legs (the climb north and the run back to T1). On
    them, the airspeed selector's own wind estimate drifted until its ground-speed-minus-wind
    airspeed was 15 m/s away from the sensor's. The simulated pitot is exact, so the check
    was rejecting a good sensor. Run 529e (which climbed in a spiral at T1) never tripped it.
  - **What it broke:** with no valid airspeed PX4 flies on a synthetic one, which is a
    different control mode. uas_sim's energy model also prices a missing airspeed as 1 m/s
    (`orchestrator.py` `_power_now`: `airspeed_ms or 0.0`, then `max(v, 1)` in the drag
    polar), which is ~765 W. The simulated battery emptied, and PX4's low-battery failsafe cut
    line 3 short at 2031 m (run `run-20261008-112759-da7e`). **That energy-model fallback is a
    uas_sim bug** (it should use Gazebo's true airspeed, or cruise speed, when the firmware
    reports none); it was not changed during the sweep.
  - Every Part A run was re-flown with the change, so the whole data set has one parameter set.
- **No gusts, no turbulence** (`gust_amplitude_ms` 0, `turbulence_intensity` 0). Shear exponent
  0.143, 15 °C, flat ground at launch elevation (the aircraft flies 593.6 m above it).

### Speed factor

The brief asked for a re-fly of the 2026-09-28 case (6@300 at 10 m) at the intended speed.

| Run | Speed | Line 3: bank < 5° from | within 10 m from | worst excursion | Line 2: bank < 5° / within 10 m |
|---|---|---|---|---|---|
| run-20260928-150115-529e (the reference) | 3x | 282 m | 186 m | 89 m | 101 / 62 m |
| run-20261008-111149-1cb6 (re-fly) | 3x | 242 m | 191 m | 83 m | 111 / 76 m |
| run-20261008-110231-8950 | 8x | 240 m | 189 m | 83 m | 111 / 77 m |
| run-20261008-110626-d024 | 8x | 241 m | 192 m | 85 m | 110 / 73 m |
| run-20261008-110051-8d94 | 15x | flipped over on the runway; never flew | | | |

- **15x is unusable.** PX4 follows Gazebo's clock rather than locking step with it, and at
  15x it could not keep up: one start never produced a MAVLink heartbeat, and the other
  rolled the aircraft over on the runway.
- **8x reproduces 3x.** Today's 3x re-fly and both 8x flights agree within 3-5 m on every
  line-3 number.
- **The 281 m of 2026-09-28 was not reproduced at either speed.** The difference is the end of
  the S-turn back onto the line. In 529e the aircraft held its +30° recovery bank a little
  longer and swung through to -5.9° at 280 m, just over the 5° threshold. The cross-track
  numbers agree (186 vs 189-192 m). Because 3x and 8x agree with each other, a lower speed
  factor would not change it: it is run-to-run spread (see "How noisy is D_level" below).
- **The sweep flew at 8x** (7.9x over a whole run, startup included; 4.5-8 min of wall time
  per run).

### Run quality gate

PX4 is not in lockstep with Gazebo, so a busy host can starve it of IMU data. That happened
once. In `run-20261008-124856-fadb` (A-15-147), PX4 saw 20 IMU gaps of 50-190 ms within 26 s,
a burst of host load whose source I did not pin down. Its estimator diverged (velocity and
position test ratios 2.0), and the aircraft departed controlled flight on line 3 (95° of bank,
50 m height loss). That run was discarded and re-flown. From then on, my own log analysis ran
at background priority (`taskpolicy -b`) while flights were up. Every run in the data set
passed this gate:

- PX4 airspeed valid all flight;
- at most 2 IMU gaps over 50 ms while flying the lines (all used runs: 0);
- EKF velocity and position test ratios below 1 on the lines (all used runs: ≤ 0.66);
- landed with every mission item reached.

### Missions

- **Lines:** items 1-21 of `V2 Plan_20260922-1240.plan`, unchanged (609.6 m AMSL = 593.6 m above
  the V2 home, 313.4 m spacing, 52 m inset, 206 items at 280.74 m, 28.5 m acceptance), moved
  20.5 km north, with exp2.plan's takeoff and landing. With no approach waypoint this rebuilds
  run 529e's mission byte for byte (checked).
- **Transit approach (new):** one waypoint on bearing 354.8° from T1. The aircraft must be level
  at cruise altitude before it, and the climb from home (3.35 m/s) covers 3.3-6 km of ground
  northward depending on the tailwind. So the waypoint went further out than 3 km, as the brief
  allows: 6.0-8.5 km, chosen per wind from the climb time and the northbound tailwind, plus
  1 km of level flight (per-run values in the run index). Measured: cruise altitude was reached
  1.4-3.9 km before the waypoint in every run, and the aircraft was within 4 m of cruise
  altitude when it switched to T1. It then flew a 6-8.5 km straight leg on 174.8° into T1.
- **Part B:** each line's first and last nav items moved 273.8 m outward along the line (line 1's
  first a further 90.2 m, 364.0 m in all). collect_start, the centre, collect_stop and the
  camera items are unchanged. Insets are then 325.8 m (416.0 m on line 1), and the offset legs
  stay 313.4 m long. The approach waypoint is re-placed on 354.8° from the moved T1.
- Every flown plan is in `~/.uas_sim/sweeps/s2_rollout/missions/`, and in each run's `inputs.json`.

### Wind

- **Conversion:** uas_sim's shear is v(h) = v10 (h / 10 m)^0.143 at the vehicle's height above
  home. At 593.6 m that is a factor of 1.793, so the 10 m inputs were W / 1.793: 2.788, 4.461,
  5.577, 6.135 and 8.365 m/s for 5, 8, 10, 11 and 15 m/s aloft. This matches the brief's table.
- **Measured:** the wind uas_sim set at the aircraft while above 580 m equalled the target in
  every run (to 0.01 m/s), so W in the fits is the target. PX4's own wind estimate over the
  lines read 0.43 m/s low to 0.35 m/s high, within 13° of the set direction. Both are in the
  run index.

### What was measured, and how

- **Source:** PX4's own flight log (ULog), which records Gazebo's ground truth at ~20 Hz of
  simulated time whatever the speed factor (position from `vehicle_local_position_groundtruth`,
  bank from `vehicle_attitude_groundtruth`). Waypoint switches come from
  `mission_result.seq_current`, and images from `camera_trigger`. On run 529e this reproduces
  the 2026-09-28 write-up's numbers to within a few metres (bank < 5° from 282 vs 281 m,
  within 10 m from 186 vs 186 m, worst excursion 89 vs 89 m, image 1 at 0.4 m and -25.9° vs
  0 m and -25.3°).
- **Line frame:** the origin is the line's first turn waypoint T, `along` runs toward
  collect_start, and cross-track is positive to the right. The window runs from the moment the
  aircraft heads for T until it reaches collect_stop.
- **Bank < 5° from / within 10 m from:** the along-track position of the last sample in the
  window with |bank| ≥ 5° (or |cross-track| ≥ 10 m). **D_level** is the larger of the two.
- **Largest excursion:** the largest |cross-track| after the aircraft first comes within 10 m of
  the line. "Overshoot" means it lies on the far side from where the turn came in.
- **Camera on:** where the aircraft was when PX4 moved past collect_start (that is when it runs
  the 206 item). "Early" is collect_start's along-track distance minus that position. Image 1
  is the first CAMERA_TRIGGER after that.
- **Coverage:** defined as in the 2026-09-28 write-up, which this reproduces exactly for run 529e
  (100 / 100 / 50.3 % and 100 / 100 / 96.7 %). The science box starts at collect_start +
  352 m (flight-plan's parallax, i.e. 404 m past T on today's lines), spans half the line
  spacing either side of the line, and is covered by every flown footprint. Neighbouring lines'
  images count there (the grid has 50 % side overlap), so the table also gives the line's own
  images alone ("own-line"). Lines 1 and 3 are edge lines in this 3-line test, so their
  all-image coverage has only one neighbour.
- **Entry types:** the transit entry onto line 1 (117.7° left turn). The turn between lines onto
  line 2 is a right turn at the north-east end, after the offset leg on 147.1°; the one onto
  line 3 is a left turn at the south-west end, after the same offset bearing. "Upwind" or
  "downwind" describes the offset leg (the leg before the final turn): within 67.5° of
  head- or tailwind.

## Part A: today's geometry (52 m inset)

33 runs: still air, plus 5, 8, 11 and 15 m/s from 8 directions; 99 line entries.

### D_level by wind direction

D_level (m) for each entry type. The worst cell at each wind speed is in bold.

**Turn between lines onto line 2** (right turn at the north-east end; line 2 runs 237.1°):

| Wind from | 0 m/s (R_g 57 m) | 5 m/s (R_g 93 m) | 8 m/s (R_g 119 m) | 11 m/s (R_g 148 m) | 15 m/s (R_g 192 m) |
|---|---|---|---|---|---|
| calm | **180** | - | - | - | - |
| 12° | - | 227 | 275 | **443** | 496 |
| 57° | - | **266** | **329** | 322 | **506** |
| 102° | - | 166 | 179 | 254 | 264 |
| 147° | - | 103 | 80 | 30 | 26 |
| 192° | - | 69 | 28 | 32 | 5 |
| 237° | - | 82 | 33 | 21 | 20 |
| 282° | - | 141 | 121 | 99 | 58 |
| 327° | - | 190 | 174 | 160 | 94 |

**Turn between lines onto line 3** (left turn at the south-west end; line 3 runs 57.1°):

| Wind from | 0 m/s (R_g 57 m) | 5 m/s (R_g 93 m) | 8 m/s (R_g 119 m) | 11 m/s (R_g 148 m) | 15 m/s (R_g 192 m) |
|---|---|---|---|---|---|
| calm | **188** | - | - | - | - |
| 12° | - | 149 | 120 | 98 | 56 |
| 57° | - | 84 | 33 | 21 | 21 |
| 102° | - | 68 | 29 | 32 | 5 |
| 147° | - | 105 | 74 | 30 | 28 |
| 192° | - | 167 | 175 | 254 | 245 |
| 237° | - | 245 | **327** | **387** | 443 |
| 282° | - | **254** | 274 | 347 | **499** |
| 327° | - | 200 | 180 | 153 | 66 |

**Transit entry onto line 1** (117.7° left turn; line 1 runs 57.1°):

| Wind from | 0 m/s (R_g 57 m) | 5 m/s (R_g 93 m) | 8 m/s (R_g 119 m) | 11 m/s (R_g 148 m) | 15 m/s (R_g 192 m) |
|---|---|---|---|---|---|
| calm | **214** | - | - | - | - |
| 12° | - | 167 | 135 | 104 | 70 |
| 57° | - | 143 | 108 | 77 | 39 |
| 102° | - | 154 | 111 | 26 | 20 |
| 147° | - | 189 | 144 | 74 | 26 |
| 192° | - | 250 | 263 | 266 | 283 |
| 237° | - | **299** | **314** | **424** | **562** |
| 282° | - | 261 | 284 | 366 | 90 |
| 327° | - | 218 | 196 | 180 | 173 |

What the matrices show:

- **The new line's tailwind sets D_level.** A line flown downwind takes 230-510 m. One flown into
  the wind at 8 m/s or more is level and on the line within 5-35 m (68-84 m at 5 m/s), because
  the aircraft never overshoots it. In one 15 m/s run (wind from 57°) line 2 took 506 m and
  line 3 took 21 m.
- **The worst cases are wind along the line axis, or 45° off it.** For the turn onto line 2
  that is wind from 57° (a pure tailwind on 237°) or 12° (tailwind plus a crosswind pushing the
  aircraft outward, past the line). For line 3 it is the mirror pair, 237° and 282°.
- **The two turn types are mirror images.** Reflecting about the offset-leg axis
  (147°/327°) maps a right turn onto line 2 in wind from d to a left turn onto line 3 in wind
  from 294° - d. The pairs agree, which is a built-in repeat flight:

  | | 5 m/s | 8 m/s | 11 m/s | 15 m/s |
  |---|---|---|---|---|
  | Right turn, wind from 12° / left turn, from 282° | 227 / 254 | 275 / 274 | 443 / 347 | 496 / 499 |
  | Right turn, 57° / left turn, 237° | 266 / 245 | 329 / 327 | 322 / 387 | 506 / 443 |
  | Right turn, 102° / left turn, 192° | 166 / 167 | 179 / 175 | 254 / 254 | 264 / 245 |

- **Still air is not small.** With no wind D_level is 180-188 m (3.2-3.3 x 57 m). PX4's
  fly-by of the 313 m offset leg ends in an overshoot and an S-turn back onto the line even
  then.
- **Into-wind lines get shorter as the wind rises** (wind from 327°: 190 → 94 m on line 2), while
  downwind lines get longer. One direction-free line through all of them cannot fit both.

### Fits for the turns between lines (D_level = a · R_g + b)

| Fit | Points | a | b (m) | R² | Largest residual |
|---|---|---|---|---|---|
| All turns between lines | 66 | 0.17 | 141 | 0.003 | +332 m (A-15-57 line 2) |
| Worst direction at each wind speed (the planning case) | 5 | 2.48 | 44 | 0.98 | +31 m (A-11-12 line 2) |
| flight-plan's guess, for comparison | | 2 | 50 | | |

The planning-case points:

| Wind aloft (measured) | R_g (m) | Worst entry | D_level (m) | Fit (m) | Residual (m) | Guess 2 R_g + 50 (m) |
|---|---|---|---|---|---|---|
| 0 m/s | 57 | A-0-0 line 3 (left turn) | 188 | 186 | +2 | 164 |
| 5 m/s | 93 | A-5-57 line 2 (right turn) | 266 | 275 | -9 | 236 |
| 8 m/s | 119 | A-8-57 line 2 (right turn) | 329 | 339 | -10 | 288 |
| 11 m/s | 148 | A-11-12 line 2 (right turn) | 443 | 412 | +31 | 346 |
| 15 m/s | 192 | A-15-57 line 2 (right turn) | 506 | 520 | -14 | 433 |

![D_level against R_g](<S2 Rollout Calibration Results - charts/dlevel_vs_rg.svg>)

- **All turns: there is no relation to R_g.** R² is 0.003. At any one wind speed D_level
  spans 5-510 m depending on direction, so a direction-free R_g cannot predict a given turn.
- **The worst direction is linear in R_g.** D_level = 2.48 R_g + 44 m,
  R² 0.98, and every point is within 31 m. This is the envelope a fixed inset has to
  clear.
- **flight-plan's guess (2 R_g + 50) is short of the envelope at every wind:** by 24 m in still
  air, 30-41 m at 5-8 m/s, 97 m at 11 m/s and 73 m at 15 m/s. Its 50 m was also meant to
  cover the early camera start, which comes on top (below).

### Transit entries onto line 1 (117.7°)

Compared with R_g · tan(θ/2) + (a - 1) · R_g + b, using each fit's a and b:

| Wind aloft | R_g (m) | Worst transit D_level (m), wind from | Median of 8 directions (m) | Formula, worst-direction fit (m) | Formula, all-turns fit (m) | flight-plan's guess, a = 2, b = 50 (m) |
|---|---|---|---|---|---|---|
| 0 m/s | 57 | 214, calm | 214 | 223 | 188 | 201 |
| 5 m/s | 93 | 299, 237° | 203 | 336 | 218 | 297 |
| 8 m/s | 119 | 314, 237° | 170 | 417 | 239 | 366 |
| 11 m/s | 148 | 424, 237° | 142 | 508 | 263 | 443 |
| 15 m/s | 192 | 562, 237° | 80 | 645 | 299 | 559 |

- **The worst transit entry is about as long as the worst turn between lines,** within the
  run-to-run spread: 214 vs 188 m in still air, 299 vs 266 m at 5 m/s, 314 vs 329 m at 8,
  424 vs 443 m at 11, and 562 vs 506 m at 15. The worst case is again wind along the new
  line: from 237°, a tailwind on line 1.
- **With the planning-case a and b the formula is conservative:** it is 9-103 m above the worst
  measured transit at every wind. Its extra (tan(θ/2) - 1) · R_g (0.65 R_g) is not needed on
  this plan, but it does no harm.
- **flight-plan's own guess (a = 2, b = 50) happens to track the worst transit:** it is between
  13 m below and 52 m above it. That is a lower a happening to balance the larger tan(θ/2)
  term; the same guess is short on the turns between lines.
- **The all-turns fit under-predicts every transit worst case** by 26-263 m. Don't use it.

### When PX4 switches the camera on (how early)

Distance before collect_start at which PX4 ran the camera-on item:

| Where | Entries | Median | Max | Over 50 m |
|---|---|---|---|---|
| Part A, turns between lines (collect_start 52 m past T) | 66 | 41 m | 60 m | 11 |
| Part A, transit entries | 33 | 24 m | 50 m | 0 |
| Part B, aircraft already level and on the line when the camera came on | 18 | 21 m | 61 m* | 1 |
| Part B, aircraft not yet level and on the line (all on the downwind line, or the transit from 237°) | 12 | 64 m | 71 m | 11 |

\* B-8-237's transit entry: level and on the line 2 m before the camera came on, 61 m early.

- **50 m does not cover it.** 25 of 159 entries started the camera more than 50 m early, up to 71 m.
- **It grows with ground speed exactly when it hurts.** With Part B's long insets the early start
  tracks the ground speed on the line (Part B, turns between lines: early ≈ 2.0 s x ground speed
  + 5 m, r = 0.95). PX4 effectively accepts collect_start about 2 s before reaching it, and the
  fastest ground speed is on the downwind line, the one that is still turning.
- **Budget about 2 s of downwind ground speed** instead of a flat 50 m: 2 x (18 + W), which is
  56 m at 10 m/s and 66 m at 15 m/s, about 70 m with the scatter.
- With today's 52 m inset the camera came on a median 12 m past T on the turns between lines
  (8 m before T to 43 m past it), as on 2026-09-28 (0-15 m). Collect_start that close to T
  bounds how early it can be.

### First images and coverage with the 52 m inset

- **Image 1 was level and on the line in 7 of 66 turns between lines and 3 of 33 transit
  entries.** The median |bank| at image 1 was 30°.
- **Coverage of the box's first 100 m** (all images, the 2026-09-28 definition) fell below 60 %
  in 13 entries, down to 1.6 % (A-15-282 line 3: images 1 and 2 both banked about 30°, at 0 m
  and 280 m).
  - Lines 1 and 3 are edge lines in this test, so a missing image there is not backed up by a
    neighbour.
  - Some of the lowest numbers at 15 m/s crosswind (A-15-327 line 3, A-15-147 line 1) come from
    the 56° crab: a hard-mounted, forward-tilted camera then looks ~290 m sideways. That is a
    property of the hard mount, not of the rollout.

### How noisy is D_level

Each planning case, the worst turn between lines at its wind speed, was flown twice more with
identical inputs (-r2 and -r3). Two other flights repeat the same turn: the Part B
flight in the same wind (the turn relative to T is unchanged), and the mirror-image case.

| Wind | Case | Designed run | Repeats (-r2, -r3) | Part B, same turn | Mirror case | Spread of identical flights | Spread of all |
|---|---|---|---|---|---|---|---|
| 0 m/s | still air, lines 2 and 3 | 180, 188 | 187, 186, 166, 178 | - | - | 22 m | 22 m |
| 5 m/s | from 57°, line 2 | 266 | 265, 267 | - | 245 | 2 m | 22 m |
| 8 m/s | from 57°, line 2 | 329 | 324, 318 | 326 | 327 | 12 m | 12 m |
| 11 m/s | from 12°, line 2 | 443 | 449, 356 | 436 | 347 | 93 m | 102 m |
| 15 m/s | from 57°, line 2 | 506 | 495, 490 | 475 | 443 | 16 m | 63 m |

The planning fit (D_level = a R_g + b) on different summaries of these flights:

| Fit over the 5 planning cases | a | b (m) | R² | Largest residual (m) | At 10 m/s (m) | At 15 m/s (m) |
|---|---|---|---|---|---|---|
| Designed runs only (the brief's fit) | 2.48 | 44 | 0.98 | 31 | 387 | 520 |
| Mean of the identical flights | 2.40 | 44 | 0.99 | 16 | 376 | 504 |
| Largest of all flights of the turn | 2.50 | 44 | 0.97 | 36 | 388 | 522 |

- **Identical flights mostly agree within 2-22 m** (median spread 16 m). The
  exception is 11 m/s from 12°, which is bimodal: 443, 449 and 436 m (designed run, -r2, and
  Part B) against 356 and 353 m (-r3, and run-20261008-112242-5533, flown before the
  parameter change, whose airspeed check never tripped).
  - The overshoot repeats in all five flights: 97-104 m off the line, 135-143 m past T.
  - What differs is the recovery. Two flights settled one swing of the S-turn earlier (within
    10 m by ~225 m, level by ~355 m); three settled one swing later (~330 m and ~445 m).
  - The other cases show the same thing on a smaller scale: the S-turn's tail decays
    slowly, and both thresholds catch it at slightly different points.
- **The designed flights sat near the top of each case's spread,** so the planning fit hardly
  moves: 2.50 R_g + 44 m through the largest flight of each case, against 2.48 R_g + 44 m.
  The largest flight still lies 36 m above that line (11 m/s), so a fixed inset that
  must clear every flight seen needs about 2.5 R_g + 80 m.

### The model's form

- **D_level does not scale with R_g across directions** (R² 0.003). It scales with the
  ground radius at the new line's own tailwind:

  | Predictor (all 66 turns between lines) | a | b | R² | Largest residual |
  |---|---|---|---|---|
  | R_g = 57 (1 + W/18)² (direction-free) | 0.17 | +141 m | 0.00 | 332 m |
  | 57 (1 + w_line/18)², w_line = tailwind component along the new line | 2.53 | -4 m | 0.81 | 151 m |
  | 57 (1 + w_max/18)², w_max = largest tailwind during the final turn | 1.98 | -24 m | 0.53 | 289 m |

  ![D_level against the line's tailwind radius](<S2 Rollout Calibration Results - charts/dlevel_vs_line_radius.svg>)

- **So D_level ≈ 2.5 x the ground radius at the new line's tailwind.** When the wind lies along
  the line axis, w_line = W, and the expression reduces to flight-plan's form with a ≈ 2.5.
  With the 50 % side overlap the lines alternate direction, so every other line is the
  downwind one. A fixed inset therefore has to be sized on the worst case, R_g, and the
  envelope fit is the right planning model.
- **The residual scatter has two sources.** A crosswind pushing the aircraft outward past the
  line adds to the overshoot, which w_line alone misses. At 11 m/s, wind from 12° (7.8 m/s of
  tailwind plus 7.8 m/s outward) gave 443 m on line 2, against 322 m from 57° (11 m/s of pure
  tailwind). And the S-turn
  back onto the line decays slowly, so its tail crosses the 5° and 10 m thresholds at
  different points from flight to flight.
- **D_level is mostly the S-turn, not the turn.** In the 27 entries with D_level over 250 m the
  aircraft overshoots by up to 135 m, 70-175 m past T, then takes another 150-360 m to settle.
  The bank criterion (|bank| < 5°) was the later of the two in every one of the 159 entries.

## Part B: the candidate geometry (inset 325.8 m; 416.0 m on line 1)

### Pre-flight analysis (`uas-sim analyze`)

All 32 combinations of {8, 10, 11, 15} m/s with the eight directions were analysed. There is
**no `turn_too_tight` finding on any line entry or offset leg.** Two turns outside the grid are
flagged:

- **Every Part B mission:** the 150° turn from line 3's end toward exp2's landing pattern. The
  end leg is now 326 m long, but the turn needs 438 m (8 m/s), 508 m (10), 545 m (11) or
  705 m (15).
- **11 m/s from 147° or 192°, and every direction at 15 m/s:** the 51-57° turn after the 72 m
  takeoff leg (the climb-out).

uas_sim checks each leg against one turn (R_g · tan(θ/2)). The 313 m offset legs therefore
pass, although the two 90° turns at their ends need 2 R_g between them: 383 m at 15 m/s,
which is longer than the leg. The analyses are in `~/.uas_sim/sweeps/s2_rollout/analyze_b/`.

### Verdicts

Directions: 12°, 57° and 237°, the three worst Part A found for the turns between lines
(12° worst overall; 237° also gives the worst transit entry). 15 m/s was flown once, from 57°,
the single worst turn between lines at that speed.

| Wind aloft | First images level and on the line | Which failed | First 100 m coverage, all images (min) | Own-line (min) |
|---|---|---|---|---|
| 8 m/s | 6 of 9 | the downwind line in all three runs (bank 6.6°, 11.2°, 7.7°) | 100 % | 88 % |
| 10 m/s | 5 of 9 | the downwind line in all three (bank 31°, 29°, 27°), and the transit from 237° (6.2°) | 98 % | 72 % |
| 11 m/s | 5 of 9 | the downwind line in all three (bank 31°, 31°, 35°), and the transit from 237° (24°) | 99 % | 68 % |
| 15 m/s (57° only) | 2 of 3 | line 2, downwind (bank 7.6°, 44 m off the line) | 100 % | 99.5 % |

- **The candidate inset fails at its own design wind (10 m/s) and below it**, always on the line
  flown downwind:
  - The worst D_level was 370 m at 10 m/s, 436 m at 11 and 475 m at 15. Part A's envelope
    predicts 388, 412 and 520 m.
  - PX4 switched the camera on 47-71 m before collect_start on exactly those lines, so image 1
    fired at 256-280 m past T, inside the S-turn.
- **What decides it is whether the new line is flown downwind.** Every line flown into the wind
  passed (17 of 17), with image 1 level at 297-405 m. 12 of the 13 downwind entries failed. The
  exception, B-8-237's transit entry with its longer 416 m inset, passed with 4.7° of bank.
- **Coverage held up only because of the early camera start.** Image 2 came 280.74 m after an
  early image 1, at 537-557 m past T. Its footprint's near edge (125 m ahead) then sat at
  662-682 m, at or before the box start at 677.8 m. In the 15 m/s run, where it fell just
  short, image 1's footprint still covered the box start.
- **With an autopilot that fires exactly at collect_start**, image 2 would start imaging at
  731.6 m, and the box's first 54 m would depend on the banked image 1.
- **D_level in Part B matches Part A** for the same wind and direction. The turn geometry
  relative to T is unchanged, so these are effectively repeat flights:

  | Case | Part A | Part B |
  |---|---|---|
  | 8 m/s from 12°, line 2 | 275 | 271 |
  | 8 m/s from 57°, line 2 | 329 | 326 |
  | 8 m/s from 237°, line 3 | 327 | 264 |
  | 8 m/s from 237°, transit | 314 | 353 |
  | 11 m/s from 12°, line 2 | 443 | 436 |
  | 11 m/s from 57°, line 2 | 322 | 320 |
  | 11 m/s from 237°, line 3 | 387 | 381 |
  | 11 m/s from 237°, transit | 425 | 375 |
  | 15 m/s from 57°, line 2 | 506 | 475 |

- **How the 15 m/s case failed:** the turn onto line 2, with a pure tailwind, overshot by 90 m
  at 157 m past T. PX4 switched the camera on 47 m early (at 279 m), and image 1 fired at
  7.6° of bank, still 44 m off the line. The aircraft was level and on the line only at 475 m,
  149 m past collect_start. Line 1's transit entry and line 3, both into the wind, were level
  and on the line by 36 m and 23 m.

Per-entry Part B table: see the appendix.

## What this means for flight-plan's turn model

These are recommendations for the user and the flight-plan agent; flight-plan was not changed.

- **D_level, the planning envelope:**
  - 2.48 R_g + 44 m through the worst direction at each wind speed (the brief's single-flight
    fit); 2.50 R_g + 44 m through the largest repeat flight.
  - To clear every flight seen: about **2.5 R_g + 80 m**, 426 m at 10 m/s and 559 m at the
    15 m/s rating.
- **Add PX4's early camera start as its own term:** about 70 m. That is the most measured (71 m),
  and about 2 s of downwind ground speed at 10-15 m/s. It replaces the 50 m folded into b.
- **Taken together: inset ≈ 2.5 R_g + 150 m,** about 500 m at a 10 m/s design wind and 630 m at
  the 15 m/s rating.
  - Today's 52 m, the 2 R_g + 50 guess (327 m at 10 m/s, 433 m at 15) and Part B's 325.8 m all
    fall short.
  - Checked against Part B's failures: the worst need was 370 + 69 = 439 m at 10 m/s, 436 + 71 =
    507 m at 11 and 475 + 47 = 522 m at 15. These are under 2.5 R_g + 150 (496, 520 and 629 m),
    though at 11 m/s by only 13 m.
- **The transit entry needs no more than a turn between lines on this plan.** The tan(θ/2) form
  with the fitted a and b covers it conservatively; the early camera start must be added there
  too.
- **Long insets cost distance:** about 2 x (630 - 52) ≈ 1.2 km per line at the rating. That makes
  fix B (a lead-in that joins the line's axis outside the grid) worth checking in the
  simulator. Most of D_level is the overshoot and S-turn after a downwind 90° turn onto the
  line, which a lead-in is designed to remove.


## Run ids

Every run in the data set, with the wind set and measured at altitude, PX4's own wind
estimate, the approach-waypoint distance and the quality gate. All runs are in
`~/.uas_sim/runs/`.

| Job | Run id | Wind input at 10 m | Wind aloft (set) | PX4 estimate | Approach WP from T1 | Cruise altitude reached before it | IMU gaps > 50 ms |
|---|---|---|---|---|---|---|---|
| A-0-0 | run-20261008-144017-f8ce | 0.000 m/s @ 0° | calm | 0.2 m/s @ 286° | 6000 m | 1789 m | 0 |
| A-0-0-r2 | run-20261008-154853-bc52 | 0.000 m/s @ 0° | calm | 0.2 m/s @ 289° | 6000 m | 1727 m | 0 |
| A-0-0-r3 | run-20261008-155258-676b | 0.000 m/s @ 0° | calm | 0.2 m/s @ 319° | 6000 m | 1745 m | 0 |
| A-5-12 | run-20261008-140512-df45 | 2.788 m/s @ 12° | 5.00 m/s @ 12° | 5.0 m/s @ 16° | 6000 m | 2409 m | 0 |
| A-5-57 | run-20261008-140929-47dd | 2.788 m/s @ 57° | 5.00 m/s @ 57° | 4.7 m/s @ 52° | 6000 m | 2300 m | 0 |
| A-5-57-r2 | run-20261008-155703-f890 | 2.788 m/s @ 57° | 5.00 m/s @ 57° | 4.5 m/s @ 45° | 6000 m | 2297 m | 0 |
| A-5-57-r3 | run-20261008-160119-7cd3 | 2.788 m/s @ 57° | 5.00 m/s @ 57° | 4.7 m/s @ 50° | 6000 m | 2295 m | 0 |
| A-5-102 | run-20261008-141349-22d2 | 2.788 m/s @ 102° | 5.00 m/s @ 102° | 4.8 m/s @ 98° | 6500 m | 2302 m | 0 |
| A-5-147 | run-20261008-141813-a57f | 2.788 m/s @ 147° | 5.00 m/s @ 147° | 4.8 m/s @ 144° | 7000 m | 2224 m | 0 |
| A-5-192 | run-20261008-142245-e67d | 2.788 m/s @ 192° | 5.00 m/s @ 192° | 4.9 m/s @ 192° | 7000 m | 2116 m | 0 |
| A-5-237 | run-20261008-142720-bfc6 | 2.788 m/s @ 237° | 5.00 m/s @ 237° | 5.0 m/s @ 242° | 6500 m | 1711 m | 0 |
| A-5-282 | run-20261008-143146-8c09 | 2.788 m/s @ 282° | 5.00 m/s @ 282° | 5.0 m/s @ 284° | 6000 m | 2066 m | 0 |
| A-5-327 | run-20261008-143603-cca0 | 2.788 m/s @ 327° | 5.00 m/s @ 327° | 5.0 m/s @ 326° | 6000 m | 2270 m | 0 |
| A-8-12 | run-20261008-132727-c884 | 4.461 m/s @ 12° | 8.00 m/s @ 12° | 7.9 m/s @ 12° | 6000 m | 2945 m | 0 |
| A-8-57 | run-20261008-133205-05fc | 4.461 m/s @ 57° | 8.00 m/s @ 57° | 7.8 m/s @ 45° | 6000 m | 2665 m | 0 |
| A-8-57-r2 | run-20261008-160537-fb7f | 4.461 m/s @ 57° | 8.00 m/s @ 57° | 7.7 m/s @ 50° | 6000 m | 2748 m | 0 |
| A-8-57-r3 | run-20261008-161018-aca0 | 4.461 m/s @ 57° | 8.00 m/s @ 57° | 7.9 m/s @ 46° | 6000 m | 2696 m | 0 |
| A-8-102 | run-20261008-133646-1b19 | 4.461 m/s @ 102° | 8.00 m/s @ 102° | 8.0 m/s @ 103° | 6500 m | 2448 m | 0 |
| A-8-147 | run-20261008-134130-2a2e | 4.461 m/s @ 147° | 8.00 m/s @ 147° | 8.0 m/s @ 144° | 7000 m | 2014 m | 0 |
| A-8-192 | run-20261008-134621-eb3b | 4.461 m/s @ 192° | 8.00 m/s @ 192° | 7.9 m/s @ 193° | 7500 m | 2110 m | 0 |
| A-8-237 | run-20261008-135123-0fff | 4.461 m/s @ 237° | 8.00 m/s @ 237° | 8.1 m/s @ 240° | 6500 m | 1451 m | 0 |
| A-8-282 | run-20261008-135611-28e2 | 4.461 m/s @ 282° | 8.00 m/s @ 282° | 8.1 m/s @ 285° | 6000 m | 2151 m | 0 |
| A-8-327 | run-20261008-140043-241b | 4.461 m/s @ 327° | 8.00 m/s @ 327° | 7.7 m/s @ 329° | 6000 m | 2648 m | 0 |
| A-11-12 | run-20261008-114209-f140 | 6.135 m/s @ 12° | 11.00 m/s @ 12° | 10.8 m/s @ 16° | 6000 m | 3381 m | 0 |
| A-11-12-r2 | run-20261008-161456-795c | 6.135 m/s @ 12° | 11.00 m/s @ 12° | 10.7 m/s @ 17° | 6000 m | 3341 m | 0 |
| A-11-12-r3 | run-20261008-162014-ecbc | 6.135 m/s @ 12° | 11.00 m/s @ 12° | 11.0 m/s @ 11° | 6000 m | 3349 m | 0 |
| A-11-57 | run-20261008-114726-cb84 | 6.135 m/s @ 57° | 11.00 m/s @ 57° | 11.1 m/s @ 62° | 6000 m | 3129 m | 0 |
| A-11-102 | run-20261008-115252-ce7a | 6.135 m/s @ 102° | 11.00 m/s @ 102° | 11.2 m/s @ 100° | 6500 m | 2722 m | 0 |
| A-11-147 | run-20261008-115813-5a53 | 6.135 m/s @ 147° | 11.00 m/s @ 147° | 10.8 m/s @ 144° | 7500 m | 2221 m | 0 |
| A-11-192 | run-20261008-120353-2956 | 6.135 m/s @ 192° | 11.00 m/s @ 192° | 11.0 m/s @ 194° | 8000 m | 2096 m | 0 |
| A-11-237 | run-20261008-120958-92a3 | 6.135 m/s @ 237° | 11.00 m/s @ 237° | 10.9 m/s @ 236° | 7000 m | 1676 m | 0 |
| A-11-282 | run-20261008-121540-67da | 6.135 m/s @ 282° | 11.00 m/s @ 282° | 10.8 m/s @ 285° | 6000 m | 2495 m | 0 |
| A-11-327 | run-20261008-122051-4d01 | 6.135 m/s @ 327° | 11.00 m/s @ 327° | 10.8 m/s @ 329° | 6000 m | 3050 m | 0 |
| A-15-12 | run-20261008-122554-9002 | 8.365 m/s @ 12° | 15.00 m/s @ 12° | 14.6 m/s @ 18° | 6000 m | 3879 m | 0 |
| A-15-57 | run-20261008-123324-f0d9 | 8.365 m/s @ 57° | 15.00 m/s @ 57° | 15.1 m/s @ 55° | 6000 m | 3792 m | 0 |
| A-15-57-r2 | run-20261008-162534-ccc6 | 8.365 m/s @ 57° | 15.00 m/s @ 57° | 15.3 m/s @ 59° | 6000 m | 3793 m | 0 |
| A-15-57-r3 | run-20261008-163259-58ec | 8.365 m/s @ 57° | 15.00 m/s @ 57° | 15.3 m/s @ 56° | 6000 m | 3796 m | 0 |
| A-15-102 | run-20261008-124055-7cdb | 8.365 m/s @ 102° | 15.00 m/s @ 102° | 15.0 m/s @ 96° | 7000 m | 3717 m | 0 |
| A-15-147 | run-20261008-144426-1842 | 8.365 m/s @ 147° | 15.00 m/s @ 147° | 14.9 m/s @ 145° | 8000 m | 2287 m | 0 |
| A-15-192 | run-20261008-125648-0801 | 8.365 m/s @ 192° | 15.00 m/s @ 192° | 14.9 m/s @ 196° | 8500 m | 2036 m | 0 |
| A-15-237 | run-20261008-130534-7c7a | 8.365 m/s @ 237° | 15.00 m/s @ 237° | 15.0 m/s @ 239° | 7000 m | 1394 m | 0 |
| A-15-282 | run-20261008-131332-8e07 | 8.365 m/s @ 282° | 15.00 m/s @ 282° | 14.8 m/s @ 278° | 6000 m | 2941 m | 0 |
| A-15-327 | run-20261008-132017-be50 | 8.365 m/s @ 327° | 15.00 m/s @ 327° | 14.8 m/s @ 329° | 6000 m | 3675 m | 0 |
| B-8-12 | run-20261008-145215-ea41 | 4.461 m/s @ 12° | 8.00 m/s @ 12° | 7.8 m/s @ 15° | 6000 m | 2624 m | 0 |
| B-8-57 | run-20261008-145709-0c3d | 4.461 m/s @ 57° | 8.00 m/s @ 57° | 8.0 m/s @ 44° | 6000 m | 2406 m | 0 |
| B-8-237 | run-20261008-150205-ada3 | 4.461 m/s @ 237° | 8.00 m/s @ 237° | 8.1 m/s @ 238° | 7000 m | 1694 m | 0 |
| B-10-12 | run-20261008-150714-9628 | 5.577 m/s @ 12° | 10.00 m/s @ 12° | 9.8 m/s @ 13° | 6000 m | 2913 m | 0 |
| B-10-57 | run-20261008-151229-60e7 | 5.577 m/s @ 57° | 10.00 m/s @ 57° | 9.9 m/s @ 51° | 6000 m | 2635 m | 0 |
| B-10-237 | run-20261008-151750-0299 | 5.577 m/s @ 237° | 10.00 m/s @ 237° | 9.9 m/s @ 236° | 7000 m | 1543 m | 0 |
| B-11-12 | run-20261008-152326-1f38 | 6.135 m/s @ 12° | 11.00 m/s @ 12° | 11.0 m/s @ 13° | 6000 m | 3054 m | 0 |
| B-11-57 | run-20261008-152902-0861 | 6.135 m/s @ 57° | 11.00 m/s @ 57° | 11.3 m/s @ 60° | 6000 m | 2819 m | 0 |
| B-11-237 | run-20261008-153446-5ce5 | 6.135 m/s @ 237° | 11.00 m/s @ 237° | 11.0 m/s @ 237° | 7000 m | 1496 m | 0 |
| B-15-57 | run-20261008-154047-2c67 | 8.365 m/s @ 57° | 15.00 m/s @ 57° | 14.9 m/s @ 62° | 6000 m | 3466 m | 0 |

Not in the data set (kept in `~/.uas_sim/runs/` and listed in `ledger.jsonl`):

| Run | What it was |
|---|---|
| run-20261008-111149-1cb6 | speed check at 3x (6@300, the 2026-09-28 mission) |
| run-20261008-110231-8950, run-20261008-110626-d024 | speed check at 8x (both) |
| run-20261008-105842-67f9, run-20261008-110051-8d94 | speed check at 15x: no heartbeat; flipped on the runway |
| run-20261008-112242-5533, -112759-da7e, -113228-6859, -113749-8d52 | the first Part A attempts with PX4's default `ASPD_DO_CHECKS` (da7e and 8d52 lost their airspeed) |
| run-20261008-124856-fadb | A-15-147, discarded by the quality gate (IMU starvation, loss of control); re-flown as run-20261008-144426-1842 |

## Caveats

- **PX4 stands in for Black Swift's own autopilot.** The geometry (ground turn radius, which
  line is downwind) holds for any autopilot. The S-turn back onto the line, its length, and the
  early camera start are PX4's NPFG guidance, waypoint switching and stock fixed-wing gains on
  a scaled Gazebo model. The model's inertia is scaled for PX4's stock gains, not the real
  airframe (2026-09-28 notes), so roll response is not the real S2's.
- **The simulated ground is flat at launch elevation**, so the aircraft flew 593.6 m above it,
  not 609.6 m above the sea. Footprints are ~2.6 % smaller. Coverage uses flight-plan's 352 m
  parallax (609.6 m x tan 30°) for the box start, as the 2026-09-28 write-up did.
- **Steady wind only:** no gusts, turbulence or shear changes along the line. Real wind will add
  scatter.
- **One flight per case** in the main sweep. The planning cases were flown three times; the
  other 28 Part A cases, and the 10 Part B runs, once. Identical flights mostly agree within
  2-22 m, but one planning case
  was bimodal (356 vs 449 m), so any single number here can sit one S-turn swing (~90 m)
  away from a repeat.
- **One parameter differs from run 529e** (`ASPD_DO_CHECKS` 3), for the reason given in Setup.
- **The approach waypoint is 6-8.5 km out**, not 3 km, so that the aircraft is level at cruise
  altitude before it. The arrival at T1 is the brief's: a straight run in on 174.8°.
- **Three lines, not nine:** lines 1 and 3 are edge lines, which matters only for the all-image
  coverage numbers.
- **Coverage assumes a flat sea surface and a hard-mounted camera** (FLIR Boson, 30° forward), as
  in the 2026-09-28 write-up.

## Where everything is

- **Runs:** `~/.uas_sim/runs/<run id>/`. Each has the inputs, parameters with readback,
  telemetry, the PX4 ULog (`px4_work/log/`), footprints and `report.html`.
- **Sweep folder:** `~/.uas_sim/sweeps/s2_rollout/`:
  - `missions/`: every flown plan;
  - `ledger.jsonl`: every attempt, including discarded ones;
  - `results/<run id>.json`: per-entry measurements;
  - `analysis.json`, `tables.json`;
  - `analyze_b/`: the Part B pre-flight analyses;
  - `scripts/`: `build_missions.py`, `sweep.py` (drives the uas-sim web server, so every run
    showed live in the UI), `measure.py`, `remeasure.py`, `analyze_sweep.py`, `noise.py`,
    `make_charts.py`, `write_report.py`;
  - `charts/`: the two SVG charts (copied next to this file as well);
  - `logs/sweep.log`.
- **Re-run the analysis:**
  ```bash
  cd ~/programs/Python/CMB/CLAUDE_UAS_SIM
  S=~/.uas_sim/sweeps/s2_rollout/scripts
  PYTHONPATH=~/.uas_sim/sweeps/s2_rollout/pylib .venv/bin/python $S/remeasure.py
  .venv/bin/python $S/analyze_sweep.py
  .venv/bin/python $S/noise.py
  .venv/bin/python $S/make_charts.py ~/.uas_sim/sweeps/s2_rollout/charts
  .venv/bin/python $S/write_report.py "<out.md>" "<charts dir, relative to out.md>"
  ```

## Appendix: per-entry tables

Columns as the brief asked. "Entry" gives the type and, in brackets, the leg flown before the
final turn: upwind, downwind or crosswind. Distances are past the line's first turn waypoint T.
"Camera on early by" is how far before collect_start PX4 ran the camera-on item. Coverage is
the box's first 100 m / next 200 m with every image, then with this line's own images.

### Part A (52 m inset)

| Job | Run | Wind aloft (m/s @ from) | Line | Entry (leg before) | Bank < 5° from (m) | Within 10 m from (m) | **D_level** (m) | Max excursion (m, at m past T) | Image 1 (m past T, bank) | Image 1 level? | Camera on early by (m) | Coverage first 100 m / next 200 m (%) | Own-line coverage (%) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A-0-0 | run-20261008-144017-f8ce | calm | 1 | transit (calm) | 214 | 154 | **214** | 65 at 70 | 52, -30.9° | no | 1 | 78.8 / 100.0 | 43.7 / 100.0 |
| A-0-0-r2 | run-20261008-154853-bc52 | calm | 1 | transit (calm) | 213 | 152 | **213** | 62 at 67 | 52, -31.0° | no | 1 | 88.2 / 100.0 | 51.9 / 100.0 |
| A-0-0-r3 | run-20261008-155258-676b | calm | 1 | transit (calm) | 218 | 161 | **218** | 66 at 72 | 51, -31.6° | no | 1 | 84.8 / 100.0 | 49.2 / 100.0 |
| A-0-0 | run-20261008-144017-f8ce | calm | 2 | between, right (calm) | 180 | 110 | **180** | 30 at 59 | 8, 30.5° | no | 44 | 100.0 / 100.0 | 80.9 / 100.0 |
| A-0-0-r2 | run-20261008-154853-bc52 | calm | 2 | between, right (calm) | 187 | 114 | **187** | 31 at 59 | 8, 31.2° | no | 45 | 100.0 / 100.0 | 91.1 / 100.0 |
| A-0-0-r3 | run-20261008-155258-676b | calm | 2 | between, right (calm) | 166 | 103 | **166** | 27 at 57 | 9, 31.2° | no | 44 | 100.0 / 100.0 | 89.7 / 100.0 |
| A-0-0 | run-20261008-144017-f8ce | calm | 3 | between, left (calm) | 188 | 114 | **188** | 31 at 60 | 8, -30.8° | no | 44 | 100.0 / 100.0 | 85.8 / 100.0 |
| A-0-0-r2 | run-20261008-154853-bc52 | calm | 3 | between, left (calm) | 186 | 113 | **186** | 31 at 61 | 9, -31.1° | no | 44 | 100.0 / 100.0 | 88.3 / 100.0 |
| A-0-0-r3 | run-20261008-155258-676b | calm | 3 | between, left (calm) | 178 | 111 | **178** | 30 at 60 | 9, -30.3° | no | 43 | 100.0 / 100.0 | 81.8 / 100.0 |
| A-5-12 | run-20261008-140512-df45 | 5.00 @ 12° | 1 | transit (downwind) | 167 | 128 | **167** | 79 at 65 | 24, -0.2° | yes | 27 | 95.7 / 100.0 | 72.8 / 100.0 |
| A-5-12 | run-20261008-140512-df45 | 5.00 @ 12° | 2 | between, right (downwind) | 227 | 174 | **227** | 57 at 93 | 3, 33.6° | no | 50 | 100.0 / 100.0 | 91.4 / 100.0 |
| A-5-12 | run-20261008-140512-df45 | 5.00 @ 12° | 3 | between, left (downwind) | 149 | 100 | **149** | 33 at 58 | 5, -33.1° | no | 47 | 86.6 / 100.0 | 85.6 / 100.0 |
| A-5-57 | run-20261008-140929-47dd | 5.00 @ 57° | 1 | transit (downwind) | 143 | 99 | **143** | 47 at 47 | 52, -30.2° | no | 1 | 70.4 / 100.0 | 69.9 / 100.0 |
| A-5-57-r2 | run-20261008-155703-f890 | 5.00 @ 57° | 1 | transit (downwind) | 132 | 86 | **132** | 40 at 43 | 15, -18.3° | no | 36 | 99.7 / 100.0 | 88.3 / 100.0 |
| A-5-57-r3 | run-20261008-160119-7cd3 | 5.00 @ 57° | 1 | transit (downwind) | 123 | 86 | **123** | 41 at 42 | 15, -17.1° | no | 36 | 95.2 / 100.0 | 71.2 / 100.0 |
| A-5-57 | run-20261008-140929-47dd | 5.00 @ 57° | 2 | between, right (crosswind) | 266 | 180 | **266** | 48 at 87 | 5, 32.9° | no | 47 | 100.0 / 100.0 | 95.0 / 100.0 |
| A-5-57-r2 | run-20261008-155703-f890 | 5.00 @ 57° | 2 | between, right (crosswind) | 265 | 183 | **265** | 50 at 90 | 5, 32.9° | no | 47 | 100.0 / 100.0 | 91.7 / 100.0 |
| A-5-57-r3 | run-20261008-160119-7cd3 | 5.00 @ 57° | 2 | between, right (crosswind) | 267 | 180 | **267** | 50 at 90 | 5, 31.5° | no | 47 | 100.0 / 100.0 | 91.3 / 100.0 |
| A-5-57 | run-20261008-140929-47dd | 5.00 @ 57° | 3 | between, left (crosswind) | 84 | 56 | **84** | 16 at 36 | 22, -29.6° | no | 30 | 100.0 / 100.0 | 72.0 / 100.0 |
| A-5-57-r2 | run-20261008-155703-f890 | 5.00 @ 57° | 3 | between, left (crosswind) | 88 | 54 | **88** | 14 at 36 | 22, -29.6° | no | 30 | 100.0 / 100.0 | 85.8 / 100.0 |
| A-5-57-r3 | run-20261008-160119-7cd3 | 5.00 @ 57° | 3 | between, left (crosswind) | 82 | 59 | **82** | 16 at 38 | 19, -30.1° | no | 33 | 92.2 / 100.0 | 71.9 / 100.0 |
| A-5-102 | run-20261008-141349-22d2 | 5.00 @ 102° | 1 | transit (crosswind) | 154 | 101 | **154** | 34 at 46 | 44, -31.5° | no | 9 | 54.5 / 100.0 | 46.3 / 100.0 |
| A-5-102 | run-20261008-141349-22d2 | 5.00 @ 102° | 2 | between, right (upwind) | 166 | 117 | **166** | 26 at 61 | 11, 30.9° | no | 41 | 100.0 / 100.0 | 78.4 / 100.0 |
| A-5-102 | run-20261008-141349-22d2 | 5.00 @ 102° | 3 | between, left (upwind) | 68 | 2 | **68** | 9 at 3 | 20, -29.8° | no | 32 | 100.0 / 100.0 | 78.8 / 100.0 |
| A-5-147 | run-20261008-141813-a57f | 5.00 @ 147° | 1 | transit (upwind) | 189 | 115 | **189** | 34 at 54 | 27, -31.6° | no | 25 | 63.4 / 100.0 | 63.4 / 100.0 |
| A-5-147 | run-20261008-141813-a57f | 5.00 @ 147° | 2 | between, right (upwind) | 103 | 66 | **103** | 14 at 43 | 15, 30.6° | no | 37 | 100.0 / 100.0 | 74.6 / 100.0 |
| A-5-147 | run-20261008-141813-a57f | 5.00 @ 147° | 3 | between, left (upwind) | 105 | 66 | **105** | 14 at 42 | 17, -29.7° | no | 36 | 100.0 / 100.0 | 72.7 / 100.0 |
| A-5-192 | run-20261008-142245-e67d | 5.00 @ 192° | 1 | transit (upwind) | 250 | 160 | **250** | 48 at 72 | 30, -30.6° | no | 22 | 56.9 / 100.0 | 54.9 / 100.0 |
| A-5-192 | run-20261008-142245-e67d | 5.00 @ 192° | 2 | between, right (upwind) | 69 | 2 | **69** | 10 at 33 | 20, 29.6° | no | 33 | 100.0 / 100.0 | 64.7 / 100.0 |
| A-5-192 | run-20261008-142245-e67d | 5.00 @ 192° | 3 | between, left (upwind) | 167 | 119 | **167** | 26 at 63 | 11, -30.5° | no | 41 | 100.0 / 100.0 | 74.2 / 100.0 |
| A-5-237 | run-20261008-142720-bfc6 | 5.00 @ 237° | 1 | transit (upwind) | 299 | 213 | **299** | 80 at 96 | 52, -31.0° | no | 1 | 95.5 / 100.0 | 58.2 / 100.0 |
| A-5-237 | run-20261008-142720-bfc6 | 5.00 @ 237° | 2 | between, right (crosswind) | 82 | 57 | **82** | 16 at 38 | 20, 29.8° | no | 32 | 100.0 / 100.0 | 71.7 / 100.0 |
| A-5-237 | run-20261008-142720-bfc6 | 5.00 @ 237° | 3 | between, left (crosswind) | 245 | 172 | **245** | 45 at 86 | 6, -32.5° | no | 46 | 100.0 / 100.0 | 99.7 / 100.0 |
| A-5-282 | run-20261008-143146-8c09 | 5.00 @ 282° | 1 | transit (crosswind) | 261 | 202 | **261** | 104 at 100 | 8, -33.7° | no | 44 | 100.0 / 100.0 | 99.6 / 100.0 |
| A-5-282 | run-20261008-143146-8c09 | 5.00 @ 282° | 2 | between, right (downwind) | 141 | 95 | **141** | 33 at 55 | 5, 32.4° | no | 47 | 100.0 / 100.0 | 76.8 / 100.0 |
| A-5-282 | run-20261008-143146-8c09 | 5.00 @ 282° | 3 | between, left (downwind) | 254 | 187 | **254** | 62 at 98 | 3, -34.0° | no | 50 | 99.5 / 100.0 | 99.5 / 100.0 |
| A-5-327 | run-20261008-143603-cca0 | 5.00 @ 327° | 1 | transit (downwind) | 218 | 159 | **218** | 105 at 87 | 22, -1.8° | yes | 30 | 97.9 / 100.0 | 64.1 / 100.0 |
| A-5-327 | run-20261008-143603-cca0 | 5.00 @ 327° | 2 | between, right (downwind) | 190 | 139 | **190** | 50 at 78 | 3, 33.2° | no | 49 | 100.0 / 100.0 | 73.5 / 100.0 |
| A-5-327 | run-20261008-143603-cca0 | 5.00 @ 327° | 3 | between, left (downwind) | 200 | 146 | **200** | 53 at 84 | 3, -33.1° | no | 49 | 81.1 / 100.0 | 81.1 / 100.0 |
| A-8-12 | run-20261008-132727-c884 | 8.00 @ 12° | 1 | transit (downwind) | 135 | 99 | **135** | 83 at 56 | 28, -0.2° | yes | 24 | 99.2 / 100.0 | 67.0 / 100.0 |
| A-8-12 | run-20261008-132727-c884 | 8.00 @ 12° | 2 | between, right (downwind) | 275 | 218 | **275** | 83 at 121 | 2, 34.0° | no | 50 | 100.0 / 100.0 | 94.4 / 100.0 |
| A-8-12 | run-20261008-132727-c884 | 8.00 @ 12° | 3 | between, left (downwind) | 120 | 81 | **120** | 30 at 51 | 6, -34.9° | no | 46 | 72.8 / 99.8 | 72.8 / 99.8 |
| A-8-57 | run-20261008-133205-05fc | 8.00 @ 57° | 1 | transit (downwind) | 108 | 53 | **108** | 31 at 31 | 17, -13.2° | no | 35 | 88.8 / 100.0 | 71.4 / 100.0 |
| A-8-57-r2 | run-20261008-160537-fb7f | 8.00 @ 57° | 1 | transit (downwind) | 108 | 54 | **108** | 32 at 31 | 17, -11.1° | no | 35 | 97.8 / 100.0 | 83.4 / 100.0 |
| A-8-57-r3 | run-20261008-161018-aca0 | 8.00 @ 57° | 1 | transit (downwind) | 110 | 56 | **110** | 31 at 32 | 18, -7.7° | no | 33 | 88.3 / 100.0 | 71.2 / 100.0 |
| A-8-57 | run-20261008-133205-05fc | 8.00 @ 57° | 2 | between, right (crosswind) | 329 | 229 | **329** | 63 at 110 | 5, 32.3° | no | 48 | 100.0 / 100.0 | 91.3 / 100.0 |
| A-8-57-r2 | run-20261008-160537-fb7f | 8.00 @ 57° | 2 | between, right (crosswind) | 324 | 221 | **324** | 61 at 108 | 4, 32.4° | no | 48 | 100.0 / 100.0 | 85.8 / 100.0 |
| A-8-57-r3 | run-20261008-161018-aca0 | 8.00 @ 57° | 2 | between, right (crosswind) | 318 | 221 | **318** | 61 at 108 | 4, 32.9° | no | 48 | 100.0 / 100.0 | 98.0 / 100.0 |
| A-8-57 | run-20261008-133205-05fc | 8.00 @ 57° | 3 | between, left (crosswind) | 33 | 2 | **33** | 10 at 3 | 29, -14.5° | no | 23 | 100.0 / 100.0 | 100.0 / 100.0 |
| A-8-57-r2 | run-20261008-160537-fb7f | 8.00 @ 57° | 3 | between, left (crosswind) | 34 | 2 | **34** | 10 at 3 | 28, -17.6° | no | 24 | 100.0 / 100.0 | 100.0 / 100.0 |
| A-8-57-r3 | run-20261008-161018-aca0 | 8.00 @ 57° | 3 | between, left (crosswind) | 34 | 2 | **34** | 9 at 3 | 30, -14.9° | no | 23 | 100.0 / 100.0 | 100.0 / 100.0 |
| A-8-102 | run-20261008-133646-1b19 | 8.00 @ 102° | 1 | transit (crosswind) | 111 | 61 | **111** | 20 at 32 | 30, -31.4° | no | 22 | 51.2 / 99.6 | 50.6 / 99.6 |
| A-8-102 | run-20261008-133646-1b19 | 8.00 @ 102° | 2 | between, right (upwind) | 179 | 122 | **179** | 24 at 64 | 13, 29.7° | no | 40 | 100.0 / 100.0 | 74.3 / 100.0 |
| A-8-102 | run-20261008-133646-1b19 | 8.00 @ 102° | 3 | between, left (upwind) | 29 | 2 | **29** | 9 at 2 | 22, -19.3° | no | 30 | 100.0 / 100.0 | 68.0 / 100.0 |
| A-8-147 | run-20261008-134130-2a2e | 8.00 @ 147° | 1 | transit (upwind) | 144 | 74 | **144** | 18 at 41 | 23, -29.2° | no | 29 | 38.2 / 97.1 | 38.2 / 97.1 |
| A-8-147 | run-20261008-134130-2a2e | 8.00 @ 147° | 2 | between, right (upwind) | 80 | 1 | **80** | 10 at 35 | 18, 29.8° | no | 35 | 100.0 / 100.0 | 50.2 / 95.4 |
| A-8-147 | run-20261008-134130-2a2e | 8.00 @ 147° | 3 | between, left (upwind) | 74 | 1 | **74** | 9 at 2 | 18, -29.9° | no | 34 | 100.0 / 100.0 | 56.2 / 99.5 |
| A-8-192 | run-20261008-134621-eb3b | 8.00 @ 192° | 1 | transit (upwind) | 263 | 166 | **263** | 43 at 72 | 20, -30.1° | no | 32 | 62.7 / 100.0 | 62.7 / 100.0 |
| A-8-192 | run-20261008-134621-eb3b | 8.00 @ 192° | 2 | between, right (upwind) | 28 | 2 | **28** | 9 at 2 | 23, 16.0° | no | 30 | 100.0 / 100.0 | 64.9 / 100.0 |
| A-8-192 | run-20261008-134621-eb3b | 8.00 @ 192° | 3 | between, left (upwind) | 175 | 125 | **175** | 25 at 64 | 13, -29.8° | no | 39 | 100.0 / 100.0 | 69.6 / 100.0 |
| A-8-237 | run-20261008-135123-0fff | 8.00 @ 237° | 1 | transit (upwind) | 314 | 244 | **314** | 86 at 110 | 50, -30.6° | no | 2 | 91.9 / 100.0 | 43.2 / 100.0 |
| A-8-237 | run-20261008-135123-0fff | 8.00 @ 237° | 2 | between, right (crosswind) | 33 | 2 | **33** | 9 at 3 | 29, 17.0° | no | 24 | 100.0 / 100.0 | 100.0 / 100.0 |
| A-8-237 | run-20261008-135123-0fff | 8.00 @ 237° | 3 | between, left (crosswind) | 327 | 221 | **327** | 60 at 108 | 5, -32.4° | no | 47 | 100.0 / 100.0 | 81.9 / 100.0 |
| A-8-282 | run-20261008-135611-28e2 | 8.00 @ 282° | 1 | transit (crosswind) | 284 | 220 | **284** | 135 at 124 | 10, -30.4° | no | 42 | 100.0 / 100.0 | 89.6 / 100.0 |
| A-8-282 | run-20261008-135611-28e2 | 8.00 @ 282° | 2 | between, right (downwind) | 121 | 80 | **121** | 30 at 50 | 5, 33.7° | no | 47 | 100.0 / 100.0 | 77.5 / 100.0 |
| A-8-282 | run-20261008-135611-28e2 | 8.00 @ 282° | 3 | between, left (downwind) | 274 | 216 | **274** | 83 at 121 | 2, -33.2° | no | 50 | 84.5 / 100.0 | 84.5 / 100.0 |
| A-8-327 | run-20261008-140043-241b | 8.00 @ 327° | 1 | transit (downwind) | 196 | 151 | **196** | 132 at 96 | 27, -0.5° | yes | 25 | 100.0 / 100.0 | 64.3 / 100.0 |
| A-8-327 | run-20261008-140043-241b | 8.00 @ 327° | 2 | between, right (downwind) | 174 | 134 | **174** | 56 at 86 | 2, 31.8° | no | 51 | 100.0 / 100.0 | 59.5 / 95.9 |
| A-8-327 | run-20261008-140043-241b | 8.00 @ 327° | 3 | between, left (downwind) | 180 | 137 | **180** | 47 at 85 | 1, -30.7° | no | 51 | 78.0 / 100.0 | 78.0 / 100.0 |
| A-11-12 | run-20261008-114209-f140 | 11.00 @ 12° | 1 | transit (downwind) | 104 | 80 | **104** | 93 at 52 | 31, -0.3° | yes | 21 | 100.0 / 100.0 | 65.7 / 100.0 |
| A-11-12-r2 | run-20261008-161456-795c | 11.00 @ 12° | 1 | transit (downwind) | 103 | 79 | **103** | 93 at 51 | 31, -0.4° | yes | 20 | 100.0 / 100.0 | 61.4 / 100.0 |
| A-11-12-r3 | run-20261008-162014-ecbc | 11.00 @ 12° | 1 | transit (downwind) | 106 | 81 | **106** | 96 at 52 | 31, -0.6° | yes | 20 | 100.0 / 100.0 | 60.7 / 100.0 |
| A-11-12 | run-20261008-114209-f140 | 11.00 @ 12° | 2 | between, right (downwind) | 443 | 328 | **443** | 98 at 136 | 1, 29.0° | no | 51 | 97.6 / 100.0 | 0.0 / 10.6 |
| A-11-12-r2 | run-20261008-161456-795c | 11.00 @ 12° | 2 | between, right (downwind) | 449 | 334 | **449** | 97 at 135 | 1, 28.9° | no | 51 | 88.1 / 100.0 | 0.0 / 9.4 |
| A-11-12-r3 | run-20261008-162014-ecbc | 11.00 @ 12° | 2 | between, right (downwind) | 356 | 228 | **356** | 104 at 143 | 1, 31.2° | no | 51 | 100.0 / 100.0 | 5.8 / 7.0 |
| A-11-12 | run-20261008-114209-f140 | 11.00 @ 12° | 3 | between, left (downwind) | 98 | 73 | **98** | 37 at 52 | 9, 7.5° | no | 43 | 99.3 / 99.1 | 99.3 / 99.1 |
| A-11-12-r2 | run-20261008-161456-795c | 11.00 @ 12° | 3 | between, left (downwind) | 98 | 74 | **98** | 32 at 50 | 8, -5.2° | no | 44 | 70.8 / 100.0 | 70.8 / 100.0 |
| A-11-12-r3 | run-20261008-162014-ecbc | 11.00 @ 12° | 3 | between, left (downwind) | 102 | 76 | **102** | 34 at 53 | 11, 12.5° | no | 42 | 99.9 / 100.0 | 99.9 / 100.0 |
| A-11-57 | run-20261008-114726-cb84 | 11.00 @ 57° | 1 | transit (downwind) | 77 | 50 | **77** | 30 at 27 | 19, -7.6° | no | 33 | 90.2 / 100.0 | 69.0 / 100.0 |
| A-11-57 | run-20261008-114726-cb84 | 11.00 @ 57° | 2 | between, right (crosswind) | 322 | 244 | **322** | 66 at 117 | 5, 31.6° | no | 47 | 100.0 / 100.0 | 16.1 / 19.5 |
| A-11-57 | run-20261008-114726-cb84 | 11.00 @ 57° | 3 | between, left (crosswind) | 21 | 2 | **21** | 10 at 3 | 37, -3.5° | yes | 16 | 100.0 / 100.0 | 100.0 / 100.0 |
| A-11-102 | run-20261008-115252-ce7a | 11.00 @ 102° | 1 | transit (crosswind) | 26 | 8 | **26** | 9 at 7 | 31, 2.3° | yes | 21 | 100.0 / 100.0 | 100.0 / 100.0 |
| A-11-102 | run-20261008-115252-ce7a | 11.00 @ 102° | 2 | between, right (upwind) | 254 | 152 | **254** | 29 at 72 | 12, 30.4° | no | 40 | 100.0 / 100.0 | 49.0 / 86.4 |
| A-11-102 | run-20261008-115252-ce7a | 11.00 @ 102° | 3 | between, left (upwind) | 32 | 2 | **32** | 9 at 2 | 32, -5.4° | no | 20 | 100.0 / 100.0 | 88.9 / 99.5 |
| A-11-147 | run-20261008-115813-5a53 | 11.00 @ 147° | 1 | transit (upwind) | 74 | 7 | **74** | 10 at 6 | 22, -30.2° | no | 31 | 44.5 / 82.5 | 44.5 / 82.5 |
| A-11-147 | run-20261008-115813-5a53 | 11.00 @ 147° | 2 | between, right (upwind) | 30 | 0 | **30** | 9 at 0 | 19, 20.1° | no | 34 | 100.0 / 100.0 | 47.7 / 86.8 |
| A-11-147 | run-20261008-115813-5a53 | 11.00 @ 147° | 3 | between, left (upwind) | 30 | 0 | **30** | 9 at 1 | 21, -15.1° | no | 32 | 100.0 / 100.0 | 47.1 / 93.7 |
| A-11-192 | run-20261008-120353-2956 | 11.00 @ 192° | 1 | transit (upwind) | 266 | 158 | **266** | 34 at 74 | 18, -29.7° | no | 34 | 59.8 / 100.0 | 59.8 / 100.0 |
| A-11-192 | run-20261008-120353-2956 | 11.00 @ 192° | 2 | between, right (upwind) | 32 | 1 | **32** | 9 at 1 | 32, 5.1° | no | 20 | 100.0 / 100.0 | 75.3 / 97.4 |
| A-11-192 | run-20261008-120353-2956 | 11.00 @ 192° | 3 | between, left (upwind) | 254 | 152 | **254** | 29 at 73 | 13, -30.8° | no | 40 | 100.0 / 100.0 | 50.8 / 84.8 |
| A-11-237 | run-20261008-120958-92a3 | 11.00 @ 237° | 1 | transit (upwind) | 424 | 273 | **424** | 93 at 126 | 51, -29.5° | no | 2 | 100.0 / 100.0 | 2.7 / 1.3 |
| A-11-237 | run-20261008-120958-92a3 | 11.00 @ 237° | 2 | between, right (crosswind) | 21 | 2 | **21** | 9 at 3 | 36, 4.6° | yes | 16 | 100.0 / 100.0 | 100.0 / 100.0 |
| A-11-237 | run-20261008-120958-92a3 | 11.00 @ 237° | 3 | between, left (crosswind) | 387 | 271 | **387** | 74 at 128 | 5, -32.1° | no | 47 | 34.9 / 39.3 | 25.6 / 23.9 |
| A-11-282 | run-20261008-121540-67da | 11.00 @ 282° | 1 | transit (crosswind) | 366 | 317 | **366** | 158 at 142 | 8, -32.4° | no | 43 | 100.0 / 100.0 | 2.1 / 4.1 |
| A-11-282 | run-20261008-121540-67da | 11.00 @ 282° | 2 | between, right (downwind) | 99 | 76 | **99** | 34 at 49 | 8, 4.4° | yes | 45 | 100.0 / 100.0 | 61.6 / 96.5 |
| A-11-282 | run-20261008-121540-67da | 11.00 @ 282° | 3 | between, left (downwind) | 347 | 231 | **347** | 106 at 147 | 2, -32.2° | no | 50 | 13.3 / 10.9 | 13.3 / 10.9 |
| A-11-327 | run-20261008-122051-4d01 | 11.00 @ 327° | 1 | transit (downwind) | 180 | 142 | **180** | 162 at 105 | 30, -0.3° | yes | 22 | 100.0 / 100.0 | 46.3 / 93.7 |
| A-11-327 | run-20261008-122051-4d01 | 11.00 @ 327° | 2 | between, right (downwind) | 160 | 123 | **160** | 49 at 89 | -3, -6.3° | no | 56 | 100.0 / 100.0 | 100.0 / 87.6 |
| A-11-327 | run-20261008-122051-4d01 | 11.00 @ 327° | 3 | between, left (downwind) | 153 | 118 | **153** | 44 at 82 | -6, -8.0° | no | 58 | 60.6 / 87.1 | 60.6 / 87.1 |
| A-15-12 | run-20261008-122554-9002 | 15.00 @ 12° | 1 | transit (downwind) | 70 | 60 | **70** | 108 at 43 | 35, -0.3° | yes | 17 | 100.0 / 100.0 | 49.6 / 92.5 |
| A-15-12 | run-20261008-122554-9002 | 15.00 @ 12° | 2 | between, right (downwind) | 496 | 374 | **496** | 135 at 174 | 0, 27.2° | no | 52 | 100.0 / 100.0 | 0.0 / 11.0 |
| A-15-12 | run-20261008-122554-9002 | 15.00 @ 12° | 3 | between, left (downwind) | 56 | 37 | **56** | 10 at 35 | 13, -27.3° | no | 39 | 63.5 / 98.8 | 63.5 / 98.8 |
| A-15-57 | run-20261008-123324-f0d9 | 15.00 @ 57° | 1 | transit (downwind) | 39 | 27 | **39** | 19 at 17 | 42, 2.3° | yes | 11 | 100.0 / 100.0 | 100.0 / 100.0 |
| A-15-57-r2 | run-20261008-162534-ccc6 | 15.00 @ 57° | 1 | transit (downwind) | 42 | 30 | **42** | 20 at 18 | 41, 6.8° | no | 11 | 100.0 / 100.0 | 100.0 / 100.0 |
| A-15-57-r3 | run-20261008-163259-58ec | 15.00 @ 57° | 1 | transit (downwind) | 38 | 23 | **38** | 17 at 16 | 41, 2.2° | yes | 11 | 100.0 / 100.0 | 100.0 / 100.0 |
| A-15-57 | run-20261008-123324-f0d9 | 15.00 @ 57° | 2 | between, right (crosswind) | 506 | 427 | **506** | 86 at 150 | 6, 30.5° | no | 46 | 100.0 / 100.0 | 0.0 / 9.9 |
| A-15-57-r2 | run-20261008-162534-ccc6 | 15.00 @ 57° | 2 | between, right (crosswind) | 495 | 310 | **495** | 84 at 146 | 6, 30.5° | no | 46 | 100.0 / 97.2 | 0.0 / 9.9 |
| A-15-57-r3 | run-20261008-163259-58ec | 15.00 @ 57° | 2 | between, right (crosswind) | 490 | 310 | **490** | 84 at 146 | 7, 30.1° | no | 46 | 100.0 / 100.0 | 0.0 / 9.3 |
| A-15-57 | run-20261008-123324-f0d9 | 15.00 @ 57° | 3 | between, left (crosswind) | 21 | 2 | **21** | 9 at 3 | 42, 0.6° | yes | 10 | 100.0 / 100.0 | 100.0 / 100.0 |
| A-15-57-r2 | run-20261008-162534-ccc6 | 15.00 @ 57° | 3 | between, left (crosswind) | 22 | 2 | **22** | 9 at 3 | 42, 0.5° | yes | 10 | 100.0 / 100.0 | 100.0 / 100.0 |
| A-15-57-r3 | run-20261008-163259-58ec | 15.00 @ 57° | 3 | between, left (crosswind) | 21 | 2 | **21** | 10 at 2 | 42, 0.6° | yes | 10 | 100.0 / 100.0 | 100.0 / 100.0 |
| A-15-102 | run-20261008-124055-7cdb | 15.00 @ 102° | 1 | transit (crosswind) | 20 | 7 | **20** | 9 at 6 | 41, 0.3° | yes | 12 | 95.3 / 97.0 | 95.3 / 97.0 |
| A-15-102 | run-20261008-124055-7cdb | 15.00 @ 102° | 2 | between, right (upwind) | 264 | 147 | **264** | 25 at 70 | 14, 29.9° | no | 38 | 100.0 / 100.0 | 42.9 / 74.0 |
| A-15-102 | run-20261008-124055-7cdb | 15.00 @ 102° | 3 | between, left (upwind) | 5 | 1 | **5** | 10 at 1 | 40, 0.4° | yes | 12 | 100.0 / 100.0 | 92.1 / 97.1 |
| A-15-147 | run-20261008-144426-1842 | 15.00 @ 147° | 1 | transit (upwind) | 26 | 6 | **26** | 10 at 6 | 23, -10.2° | no | 30 | 30.2 / 44.9 | 30.2 / 44.9 |
| A-15-147 | run-20261008-144426-1842 | 15.00 @ 147° | 2 | between, right (upwind) | 26 | -0 | **26** | 9 at -0 | 25, 6.4° | no | 27 | 100.0 / 100.0 | 36.3 / 55.9 |
| A-15-147 | run-20261008-144426-1842 | 15.00 @ 147° | 3 | between, left (upwind) | 28 | 0 | **28** | 10 at 0 | 27, -6.1° | no | 26 | 100.0 / 100.0 | 37.0 / 65.1 |
| A-15-192 | run-20261008-125648-0801 | 15.00 @ 192° | 1 | transit (upwind) | 283 | 160 | **283** | 28 at 74 | 17, -29.5° | no | 35 | 52.9 / 95.6 | 52.9 / 95.6 |
| A-15-192 | run-20261008-125648-0801 | 15.00 @ 192° | 2 | between, right (upwind) | 5 | 0 | **5** | 10 at 0 | 41, -0.3° | yes | 11 | 100.0 / 100.0 | 75.4 / 84.1 |
| A-15-192 | run-20261008-125648-0801 | 15.00 @ 192° | 3 | between, left (upwind) | 245 | 130 | **245** | 21 at 66 | 16, -29.5° | no | 36 | 100.0 / 100.0 | 50.7 / 93.4 |
| A-15-237 | run-20261008-130534-7c7a | 15.00 @ 237° | 1 | transit (upwind) | 562 | 486 | **562** | 115 at 161 | 51, -30.9° | no | 1 | 86.7 / 73.7 | 0.0 / 0.0 |
| A-15-237 | run-20261008-130534-7c7a | 15.00 @ 237° | 2 | between, right (crosswind) | 20 | 2 | **20** | 9 at 3 | 40, -0.4° | yes | 12 | 100.0 / 100.0 | 100.0 / 100.0 |
| A-15-237 | run-20261008-130534-7c7a | 15.00 @ 237° | 3 | between, left (crosswind) | 443 | 335 | **443** | 95 at 158 | 6, -31.0° | no | 46 | 40.9 / 47.2 | 28.6 / 45.1 |
| A-15-282 | run-20261008-131332-8e07 | 15.00 @ 282° | 1 | transit (crosswind) | 90 | 27 | **90** | 52 at -26 | 2, -10.7° | no | 50 | 100.0 / 100.0 | 69.0 / 99.4 |
| A-15-282 | run-20261008-131332-8e07 | 15.00 @ 282° | 2 | between, right (downwind) | 58 | 52 | **58** | 19 at 45 | 15, -17.8° | no | 38 | 100.0 / 100.0 | 100.0 / 100.0 |
| A-15-282 | run-20261008-131332-8e07 | 15.00 @ 282° | 3 | between, left (downwind) | 499 | 381 | **499** | 131 at 175 | -0, -27.9° | no | 52 | 1.6 / 11.6 | 0.0 / 9.9 |
| A-15-327 | run-20261008-132017-be50 | 15.00 @ 327° | 1 | transit (downwind) | 173 | 147 | **173** | 214 at 123 | 32, -0.4° | yes | 19 | 100.0 / 100.0 | 69.6 / 100.0 |
| A-15-327 | run-20261008-132017-be50 | 15.00 @ 327° | 2 | between, right (downwind) | 94 | 64 | **94** | 17 at 50 | -8, 33.3° | no | 60 | 100.0 / 100.0 | 81.0 / 44.0 |
| A-15-327 | run-20261008-132017-be50 | 15.00 @ 327° | 3 | between, left (downwind) | 66 | 36 | **66** | 16 at 20 | 43, 2.2° | yes | 9 | 28.8 / 77.6 | 28.8 / 56.5 |

### Part B (325.8 m inset; 416.0 m on line 1)

| Job | Run | Wind aloft (m/s @ from) | Line | Entry (leg before) | Bank < 5° from (m) | Within 10 m from (m) | **D_level** (m) | Max excursion (m, at m past T) | Image 1 (m past T, bank) | Image 1 level? | Camera on early by (m) | Coverage first 100 m / next 200 m (%) | Own-line coverage (%) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B-8-12 | run-20261008-145215-ea41 | 8.00 @ 12° | 1 | transit (downwind) | 140 | 102 | **140** | 88 at 58 | 388, -0.1° | yes | 28 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-8-12 | run-20261008-145215-ea41 | 8.00 @ 12° | 2 | between, right (downwind) | 271 | 204 | **271** | 78 at 116 | 270, -6.6° | no | 57 | 100.0 / 100.0 | 88.3 / 100.0 |
| B-8-12 | run-20261008-145215-ea41 | 8.00 @ 12° | 3 | between, left (downwind) | 121 | 84 | **121** | 28 at 51 | 298, -0.4° | yes | 28 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-8-57 | run-20261008-145709-0c3d | 8.00 @ 57° | 1 | transit (downwind) | 103 | 63 | **103** | 33 at 32 | 392, 0.3° | yes | 25 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-8-57 | run-20261008-145709-0c3d | 8.00 @ 57° | 2 | between, right (crosswind) | 326 | 229 | **326** | 63 at 110 | 265, -11.2° | no | 61 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-8-57 | run-20261008-145709-0c3d | 8.00 @ 57° | 3 | between, left (crosswind) | 34 | 3 | **34** | 10 at 3 | 301, 0.2° | yes | 25 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-8-237 | run-20261008-150205-ada3 | 8.00 @ 237° | 1 | transit (upwind) | 353 | 253 | **353** | 91 at 114 | 356, 4.7° | yes | 61 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-8-237 | run-20261008-150205-ada3 | 8.00 @ 237° | 2 | between, right (crosswind) | 34 | 3 | **34** | 9 at 3 | 301, 0.0° | yes | 25 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-8-237 | run-20261008-150205-ada3 | 8.00 @ 237° | 3 | between, left (crosswind) | 264 | 200 | **264** | 53 at 99 | 260, 7.7° | no | 67 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-10-12 | run-20261008-150714-9628 | 10.00 @ 12° | 1 | transit (downwind) | 114 | 87 | **114** | 93 at 54 | 392, -0.2° | yes | 24 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-10-12 | run-20261008-150714-9628 | 10.00 @ 12° | 2 | between, right (downwind) | 345 | 280 | **345** | 91 at 130 | 270, -30.9° | no | 56 | 100.0 / 100.0 | 71.8 / 97.2 |
| B-10-12 | run-20261008-150714-9628 | 10.00 @ 12° | 3 | between, left (downwind) | 107 | 80 | **107** | 42 at 52 | 303, 0.1° | yes | 23 | 98.1 / 99.8 | 98.1 / 99.8 |
| B-10-57 | run-20261008-151229-60e7 | 10.00 @ 57° | 1 | transit (downwind) | 76 | 46 | **76** | 27 at 25 | 396, 0.4° | yes | 20 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-10-57 | run-20261008-151229-60e7 | 10.00 @ 57° | 2 | between, right (crosswind) | 370 | 243 | **370** | 66 at 118 | 258, -29.3° | no | 68 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-10-57 | run-20261008-151229-60e7 | 10.00 @ 57° | 3 | between, left (crosswind) | 25 | 3 | **25** | 9 at 3 | 306, -0.3° | yes | 20 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-10-237 | run-20261008-151750-0299 | 10.00 @ 237° | 1 | transit (upwind) | 351 | 272 | **351** | 93 at 123 | 350, 6.2° | no | 66 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-10-237 | run-20261008-151750-0299 | 10.00 @ 237° | 2 | between, right (crosswind) | 23 | 2 | **23** | 10 at 3 | 306, 0.1° | yes | 20 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-10-237 | run-20261008-151750-0299 | 10.00 @ 237° | 3 | between, left (crosswind) | 366 | 250 | **366** | 68 at 121 | 262, 27.3° | no | 66 | 100.0 / 100.0 | 98.7 / 100.0 |
| B-11-12 | run-20261008-152326-1f38 | 11.00 @ 12° | 1 | transit (downwind) | 103 | 79 | **103** | 94 at 51 | 395, -0.0° | yes | 21 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-11-12 | run-20261008-152326-1f38 | 11.00 @ 12° | 2 | between, right (downwind) | 436 | 314 | **436** | 102 at 139 | 272, -31.4° | no | 55 | 100.0 / 100.0 | 68.0 / 93.3 |
| B-11-12 | run-20261008-152326-1f38 | 11.00 @ 12° | 3 | between, left (downwind) | 96 | 73 | **96** | 35 at 50 | 305, -0.2° | yes | 21 | 98.8 / 99.9 | 98.8 / 99.9 |
| B-11-57 | run-20261008-152902-0861 | 11.00 @ 57° | 1 | transit (downwind) | 73 | 50 | **73** | 29 at 25 | 399, -0.4° | yes | 18 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-11-57 | run-20261008-152902-0861 | 11.00 @ 57° | 2 | between, right (crosswind) | 320 | 246 | **320** | 66 at 119 | 256, -31.3° | no | 71 | 100.0 / 100.0 | 99.0 / 100.0 |
| B-11-57 | run-20261008-152902-0861 | 11.00 @ 57° | 3 | between, left (crosswind) | 21 | 2 | **21** | 9 at 3 | 309, -0.2° | yes | 17 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-11-237 | run-20261008-153446-5ce5 | 11.00 @ 237° | 1 | transit (upwind) | 375 | 282 | **375** | 96 at 131 | 348, 24.2° | no | 69 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-11-237 | run-20261008-153446-5ce5 | 11.00 @ 237° | 2 | between, right (crosswind) | 22 | 2 | **22** | 9 at 3 | 308, 0.3° | yes | 18 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-11-237 | run-20261008-153446-5ce5 | 11.00 @ 237° | 3 | between, left (crosswind) | 381 | 273 | **381** | 76 at 129 | 263, 34.9° | no | 63 | 99.7 / 100.0 | 99.0 / 100.0 |
| B-15-57 | run-20261008-154047-2c67 | 15.00 @ 57° | 1 | transit (downwind) | 36 | 23 | **36** | 18 at 16 | 404, -0.2° | yes | 12 | 100.0 / 100.0 | 100.0 / 100.0 |
| B-15-57 | run-20261008-154047-2c67 | 15.00 @ 57° | 2 | between, right (crosswind) | 475 | 327 | **475** | 90 at 156 | 280, 7.6° | no | 46 | 100.0 / 100.0 | 99.5 / 100.0 |
| B-15-57 | run-20261008-154047-2c67 | 15.00 @ 57° | 3 | between, left (crosswind) | 23 | 3 | **23** | 9 at 3 | 315, -0.1° | yes | 11 | 100.0 / 100.0 | 100.0 / 100.0 |
