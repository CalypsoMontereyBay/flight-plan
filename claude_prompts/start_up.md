# Getting started 

## Goals

This repository will be used to design code for Calypso Monterey Bay flight plans.

## Prompts

> **Note (2026-08-13):** both bootstrap prompts below are already complete — `CLAUDE.md`
> and the base Python-repo files exist. A fresh session should **not** re-run them; read
> `CLAUDE.md` and `README.md` for current project context instead.

1. Read this file.  Execute the 1st task under "Claude/CLAUDE.md file"
2. Read this file.  Execute the 1st task under "Basic start up"

## Claude

### CLAUDE.md file  ✅ DONE

1. Please generate a basic CLAUDE.md file for this project.  Have it indicate:

    - I will perform git commands

> **Done** — `CLAUDE.md` exists and is actively maintained (V1 + V2 A/B). Do not regenerate it.

### Skills

### Settings

## Basic start up  ✅ DONE

1. Generate the basic files that one needs for a Python GitHub repository, e.g. a file for dependencies.  Examine the other Repositories in Oceanography/python to see how I tend to organize things.

> **Done** — `requirements.txt`, `requirements-dev.txt`, `README.md`, `conftest.py`,
> `pytest.ini`, `pyrightconfig.json`, and the `src/` + `tests/` layout all exist. Do not regenerate them.

### Report

## Logging

The "Logs" section will record Claude's work.  Please use the following format:

### <Date> (Short summary of the work)

<Detailed description of the work and what you learned>

### <Date> (Short summary of the work)

<Detailed description of the work and what you learned>

...

## Logs

### 2026-08-15 (V2C-1 — along-track payload mount)

The SST camera was remounted: yawed to face forward under the nose and pitched to 30°
off-nadir, replacing a cross-track roll at 40°. Scoped as V2C and split into C-1 (viewing
geometry, done) and C-2 (boresight/crab, next). Also raised in the same pass: altitude to
609.6 m (2000 ft), overlap to 50%, grid-width constant to 2 mi.

**What the change actually was.** It presented as "a few constants" and wasn't. The formula
`h·(tan(θ+fov/2) − tan(θ−fov/2))` never computed "swath width" — it computes ground extent
along whichever axis is *tilted*, and that was cross-track only because the camera was rolled.
Moving the tilt to along-track meant `ground_swath_width_m` and `ground_footprint_along_m`
had to **swap formula bodies**. Changing only the angle would have reported 775 m against a
true 627 m — a +23.6% over-estimate feeding straight into line spacing, with no crash and no
failing test. A `MOUNTING NOTE` now sits at the top of `geo.py` so the swap doesn't read as a
bug in `git blame`.

**Two things fell out that we didn't go looking for.** First, the old roll imaged a strip
33.8–241.9 m off to *one side* of the ground track, so the "free M1 overflight" — the
mission's one hard science requirement — was collecting nothing at M1. The new mount centres
the swath on the track and fixes it. Second, `sun ± 90` describes a single grid axis flown
both ways, so **both leg directions now collect**. That made the long-deferred SCIENCE/TRANSIT
OFFSET CORRECTION block obsolete rather than pending — its premise was dead, so it was
deleted. Net effect: bounding-box area fell 10.3 → 6.5 km² at the old altitude, but *true*
science coverage rose, because half the flight stopped being wasted transit.

**What the process caught.** Auditing the implementation turned up an inverted guard that
raised on valid input, `math.cos` fed degrees, `math.radians()` applied to a length, a
`total_lines -= 1` that silently broke the odd-parity invariant the M1 overflight depends on,
and a `metrics["sensor_parralax"]` typo that `.get()` would have swallowed into `None`
forever. The tiered harness also flagged a half-applied refactor on its own: Tier 5 went red
because `geo` was reporting 15 science lines while `planner` still tagged 8. That was a true
positive across a module boundary, and it cleared itself once the planner caught up.

**A rendering bug the new geometry exposed.** Eyeballing the first 90° plan raised "these
lines look perpendicular to the sun, not parallel" — perpendicular is correct (that *is* what
90° relative azimuth means; the old 135° target sat obliquely, which is what the eye was
calibrated to). But checking it surfaced a real defect: `outputs._sun_vector` built the arrow
from degrees of lon/lat without dividing Δlon by cos(latitude), so it drew the sun 5.49° off
true and rendered the sun-to-track angle as 84.5° on a plan holding exactly 90.0°. Plan
unaffected — flight lines are real geodesic points and plot true — but the one instrument
available for eyeballing a plan was itself lying. Fixed, with a Tier 5 regression test that
pins the property (the arrow points where the sun is) rather than the formula.

**Deliberately not done.** Parallax (352 m at 2000 ft) is reported, not corrected — it pairs
with crab shear in C-2 since both are along-track displacements. Tolerance stayed at 15°
rather than tightening to 10°, because the boresight follows the fuselage and crosswind crab
spends that budget first. Two constants were dropped from the plan for being born unread.

Suite: **51 passing**. Engine: N=15, 67.3 min, 22.7 min margin.
