# Pull Requests

## Goals

This file will be used to generate pull requests for the Calypso Monterey Bay flight plans.

## Prompts

1. Read this file.  Execute the 1st task under "Prep"
2. Read this file.  Execute the 1st task under "Review"

## Review

1. There is an active PR on this repository.  Please review the latest changes made and then suggest any changes that are needed.  Log your work in the Logs section below.

## Prep

1. I wish for you to teach me how to have Claude examine an active PR for this Repository on GitHub and perform code review.  Please write a Report below.

### Report

> **⚠️ Current environment (as of 2026-08-13):** this machine is **macOS** (not Linux as
> noted in the dated write-up below — on macOS use `brew install gh`, not `apt`). The active
> branch is **`second_flight_engine_build`** (V2); the "one open PR #1 (V1)" referenced below
> is historical. V2 Steps A (date/time) and B (live NWS weather) are complete. The `gh` /
> `/review` workflow and the division-of-labor guidance below remain accurate.

#### TL;DR

Once the GitHub CLI (`gh`) is installed and authenticated, you just tell Claude
which PR to look at (a number or a URL), and Claude can pull the diff, read it,
and run a structured review. The fastest path is the built-in **`/review`**
slash command:

```
/review 12
```

or, for a PR in another repo / by URL:

```
/review https://github.com/CalypsoMontereyBay/flight-plan/pull/12
```

The rest of this report explains the prerequisites, the available review
commands, and the recommended workflow.

---

#### 1. One-time prerequisite: install & authenticate `gh`  ✅ DONE

**Status (as of 2026-06-28): this prerequisite is already satisfied.** The
GitHub CLI is installed and you are authenticated, so you can skip straight to
section 2.

```
gh version 2.45.0
gh auth status  ->  ✓ Logged in to github.com account profxj
  Token scopes: 'gist', 'read:org', 'repo', 'workflow'
origin  https://github.com/CalypsoMontereyBay/flight-plan.git
```

The `repo` scope on your token is what lets Claude (via `gh`) read PRs and post
review comments.

If you ever set this up on a fresh machine, the one-time steps are:

```bash
# Debian/Ubuntu (this machine is Linux)
sudo apt install gh
# or see https://cli.github.com for other platforms

gh auth login        # choose GitHub.com -> HTTPS -> browser
gh auth status       # confirm you are logged in
```

> Without `gh`, Claude can still review code, but only what is already on disk
> (the current branch / working-tree diff). It cannot *discover* or fetch a
> remote PR by number until `gh` is available — but here, `gh` is ready to go.

---

#### 2. The review commands you can ask Claude to run

Claude Code ships three relevant slash commands ("skills"):

| Command | What it does | When to use it |
|---|---|---|
| **`/review <PR>`** | Reviews a pull request end-to-end: fetches the PR with `gh`, reads the diff, and reports findings. | The normal "review this PR" request. |
| **`/code-review`** | Reviews the *current diff* (your branch vs. base) for correctness bugs + simplification/efficiency cleanups. Flags: `--comment` posts findings as inline PR comments; `--fix` applies fixes to the working tree. | Reviewing local changes before pushing, or posting inline comments on a checked-out PR. |
| **`/security-review`** | Security-focused review of the pending changes on the current branch. | When you specifically want a security pass. |

You can also just say it in plain English — e.g. *"Review PR #12 on this repo and
tell me what's wrong"* — and Claude will do the same thing.

---

#### 3. Recommended workflow for an active PR

1. **Find the PR.** Ask Claude to list open PRs, or run it yourself:
   ```bash
   gh pr list
   ```
   Right now there is exactly one open PR:
   ```
   #1  Calypso Flight Engine V1  (branch: first_flight_engine_build)  OPEN
   ```
2. **Kick off the review.** Give Claude the PR number or URL:
   ```
   /review 1
   ```
   Claude will fetch the PR (title, description, changed files, diff) and read it.
3. **Read Claude's findings.** Claude reports correctness issues, design concerns,
   and cleanup suggestions, citing `file:line` so you can click straight to them.
4. **(Optional) Post comments to GitHub.** If you want the review left *on the PR*
   rather than just in chat, check out the PR branch and run the inline-comment
   pass:
   ```bash
   gh pr checkout 12          # you run this
   ```
   ```
   /code-review --comment      # Claude posts inline comments
   ```
5. **(Optional) Apply fixes.** `/code-review --fix` lets Claude apply its
   suggested edits to the working tree. **You** then review, commit, and push
   (per our CLAUDE.md agreement, Claude never commits or pushes).

---

#### 4. Division of labor (important)

- **Claude does:** fetch/read the PR, analyze the diff, report findings, and —
  if asked — post review comments or apply edits to files.
- **You do:** install/authenticate `gh`, decide which PR to review, and run all
  git state-changing commands (`checkout`, `commit`, `push`, merging the PR).

This keeps version-control actions in your hands while letting Claude do the
reading and reasoning.

## Report

### 2026-06-28 (Refreshed the report — `gh` prerequisite now satisfied)

Re-ran the Prep task and updated the teaching report to match the current
environment. Key changes since the 2026-06-19 writeup:
- `gh` (GitHub CLI) is now **installed and authenticated** (v2.45.0, account
  `profxj`, token scopes include `repo`). The earlier blocker ("`gh` not
  installed") is resolved, so the prerequisite section is marked ✅ DONE.
- Confirmed exactly one open PR on the repo: **#1 "Calypso Flight Engine V1"**
  (branch `first_flight_engine_build`). Made the workflow example concrete by
  using `/review 1`.
- The `origin` remote is unchanged and correct.

### 2026-06-19 (Documented the PR code-review workflow)

Investigated how Claude can examine and review an active GitHub PR for this
repository and wrote the teaching report above.

What I learned about this environment:
- `gh` (GitHub CLI) is **not installed** here, and is a prerequisite for Claude
  to fetch/discover remote PRs by number or URL. Documented the install + auth
  steps as a one-time *user* action.
- The `origin` remote is already correct
  (`https://github.com/CalypsoMontereyBay/flight-plan.git`), so no remote setup
  is needed.
- Three relevant built-in review commands exist: `/review` (full PR review),
  `/code-review` (current-diff review, with `--comment` to post inline PR
  comments and `--fix` to apply edits), and `/security-review`.
- Reinforced the CLAUDE.md working agreement: Claude reads/analyzes/comments,
  but the user runs all git state-changing commands.

## Logs

### 2026-06-29 (Reviewed PR #1 "Calypso Flight Engine V1")

Reviewed the open PR #1 by Robert Wandel (`first_flight_engine_build` -> `main`,
+3018 / -32, 17 files). Read all core modules (`flight_plan_maker.py`, plus
`src/`: constants, geo, aircraft_math, sun, objects, planner, outputs;
`validator.py` is empty). Did not run the engine — deps not installed in this
env and no venv present — so findings are from static review.

**Headline bug found (high):** science legs never render as "science". The
planner tags collection points as `collect_start` / `collect_stop` /
`line_label` / `turn` and never assigns `WAYPOINT_ACTION_SCIENCE` ("science").
`outputs.categorize()` returns "science" ONLY when `action == "science"`, so it
always returns "transit" -> the entire KML/PNG route draws gray and the
science-vs-transit color distinction is dead.

Other findings:
- `geo.calculate_total_lines()` is unused dead code and forces EVEN N, which
  contradicts the odd-N (center-line-through-M1) design used everywhere else.
- No plan-level validation yet (`validator.py` empty): battery margin can go
  negative without rejection; `CandidatePlan._is_legal` /
  `_is_aircraft_feasible` / `_passes_over_m1` set but never used;
  `has_m1_overflight()` never called. Acknowledged as future work.
- `sun.py` azimuth docstring describes the pre-0.7 pysolar convention; pinned
  pysolar is 0.13 (clockwise-from-north 0-360), so the doc is stale (math is
  fine).
- Glint gate (`_passes_glint_gate`) can never reject in V1 since both candidate
  orientations are constructed exactly 135 deg off-sun (score 0).
- Minor: `_metrics_caption` emits unrounded floats; `_output_path` uses naive
  `datetime.now()` (local) while the mission is UTC.

Suggested the science-tagging fix as the one blocking change before merge; the
rest are follow-ups. Did not run any git state-changing commands (per CLAUDE.md).
### 2026-10-13 (Reviewed PR #2 "Second flight engine build")

Reviewed the open PR #2 by Robert Wandel (`second_flight_engine_build` -> `main`, head
`ae74fe9`, +7617 / -1160, 33 files, 40 commits). Read `planner.py`, `weather.py`, the
`.plan` half of `outputs.py` and the grid half of `geo.py`. Ran the suite and the entry point
from a clean `git archive` export of `ae74fe9`: **94 tests pass**, and the default run gives
N=9, 72.9 min, 17.1 min margin, with the RPIC note printed. `gh` is installed and
authenticated as `sub250Rob`. I did not run any git commands that change state.

**Blocking, and it is not code.** `profxj` submitted CHANGES_REQUESTED on 2026-10-11:
*add the prompts you issued to Claude as a separate Markdown doc in the repo, and I'll
approve.* Nothing on the branch does that yet. `claude_prompts/start_up.md` and
`pull_requests.md` hold the two bootstrap prompts and Claude's logs, not the prompts issued
across V2 A, B, C-1 and J. Add one doc (for example `claude_prompts/v2_prompts.md`), dated and
grouped by step, then push and re-request review. Source for the prompts: the session
transcripts in `~/.claude/projects/` for this repo.

**No correctness bug found in the reviewed paths.** The J-4 transit loop is sound (a pass that
fails to fit has a measured transit strictly above the seed, so the budget shrinks and the
loop cannot spin), and the `.plan` writer matches its documented rules.

Follow-ups, none blocking:
- **Unflown, and the PR body should say so.** The body says "complete". The file is still
  unverified for flight: BlackSwift's takeoff-on-the-pad reply is pending, and the camera
  rollout defect (first image of each line is taken banked) is open. Both are in CLAUDE.md;
  put one line of each in the PR description, since the reviewer reads that first.
- **Climb and descent are counted as zero time**, against a 17.1 min margin. The body asks
  that changes "consider real world flight physics", and this is the largest optimism left.
- **ArduPilot is named in the body but the file is PX4-only.** `firmwareType` is hard-coded
  to 12, and the takeoff, land and nav params follow PX4/QGC semantics. If ArduPilot sims
  consume this file, say how, or note that they do not yet.
- **`weather.get_weather` can still crash a plan.** Its docstring promises a plan is always
  produced, but it catches only `RequestException`, `KeyError` and `ValueError`. A naive
  `when` datetime reaches `_value_at_time`, where comparing with NWS's aware datetimes raises
  `TypeError`. The planner always passes an aware datetime today, so this is latent.
- **Home altitude is the Terrace Point constant for every plan** (`_qgc_home`), so a boat
  launch gets the pad's 16 m. Already documented as a residual that Step F fixes.
- **History noise:** 40 commits including "Test commit" and "reverted test commit". Squash-merge
  would keep `main` readable.

Environment note: this session began on `rollout_hotfix`, whose CLAUDE.md describes R-2 work
(99 tests) that is not on this branch. The review above is of `second_flight_engine_build`.

### 2026-11-03 (Reviewed PR #3 "Rollout hotfix is complete, along with the additional steps needed for wiring")

**Scope.** Reviewed open PR #3 by Robert Wandel: `rollout_hotfix` → `main`, head `d07201a`,
52 commits, 38 files, +10,838 / −1,195. It contains all of PR #2 (`second_flight_engine_build`
merged into `rollout_hotfix` at `b2ed3f6`), plus the camera-rollout fast track and Step K
(10 commits, 19 files).
- PR #2's half was reviewed on 2026-10-13 (above), so this review covers the 10 new commits.
- I built most of that code myself, so a separate reviewer agent read the code diff
  independently. I confirmed each of its findings by probe or by reading the code.

**Verification.** From a clean `git archive` of `d07201a`:
- **120 tests pass.**
- The entry point runs with no warnings under `-W error` (default plan: 9 lines, 74.3 min,
  15.7 min margin).
- GitHub reports the PR as mergeable. `main` and `second_flight_engine_build` are both
  ancestors of the head, so the merge cannot conflict.

I ran no git command that changes state.

**What this PR merges.** The PR body is one sentence; this entry is its description.
- **Step J:** the QGC `.plan` writer, transit-aware sizing, transit bearings, and the
  grid/transit split in the summary.
- **The camera-rollout fix:** a collection inset sized from a design wind the RPIC sets
  (`--design-wind`), and Strat 1's pushback of line 1's first waypoint.
- **Step K:** the BlackSwift S3 as the default aircraft; its climb orbit, descent and
  operator hand-offs paid for in the budget; a 10 m transition for every VTOL; and pilot
  notes on every plan (winds above the aircraft's rating, weather that isn't a forecast,
  the hand-offs and the final frame).
- **Not built:** the BlackSwift XML writer (K-5), left out on purpose by the user on
  2026-11-03 because the default aircraft may change.
- **Unflown and provisional:**
  - No output has been flown.
  - The rollout constants (2.5, 80) come from PX4 SITL flying the retired S2.
  - The S3's climb and descent rates are the S2's.

**The reviewer's request from PR #2 is met.** The user clarified (2026-11-03) that "a
separate Markdown doc" meant Claude's review of the PR, added to this file, so that any
agent reviewing the PR independently can read it. `c6bb8ee` did that for PR #2, and this
entry does it for PR #3.

**Blocking: none in the code.**

**Before merge:**
- **BlackSwift's example plans come out of the repo and its history** (the user's decision,
  2026-11-03). The repo is PUBLIC, BlackSwift declined to share its S3 model on IP grounds,
  and the files are BlackSwift's.
  - All three were added in one commit, `a902cc2`. Only `rollout_hotfix` contains it, so the
    rewrite touches the 7 commits from `a902cc2` to the head. `main`, other branches and
    forks (there are none) are unaffected.
  - The rewrite was dry-run on a throwaway clone:
    - no commit on the branch carries the files;
    - the new head differs from the old only by the three deleted files;
    - all 52 commits and the 120 tests survive.
  - The head SHA changes, so `d07201a` above names the pre-rewrite head.
  - The files stay on the user's disk, ignored by `.gitignore`. No code reads them.
  - GitHub keeps the old commits reachable by SHA from PR #3's history until GitHub
    Support purges them. A complete removal needs that request.
  - `BlackSwift Response Writeup.txt`, the user's notes of the BlackSwift meeting, is also
    public on the branch. Whether it stays is the user's call.
- **A stray `test` line is still in `src/constants.py`'s module docstring (line 19)**, from
  commit `88cd726 test`. Delete it.
- **The re-seed test proves nothing since K-4** (`tests/test_4_grid_assembly.py:174`).
  - `retried.append(plan.grid_budget_m < usable)` assumed that a launch at M1 hands `geo`
    the full budget on pass 1. Since K-4, pass 1 also subtracts the climb and hand-off
    reserve, so the condition is true at every design wind.
  - Probe: winds 0–11 m/s fit on one pass and still count as "retried"; only 12–15 m/s
    actually re-seed. The code is correct; the test would not notice if the re-seed broke.
  - Line 177 is weak in the same way: it checks `flight <= usable`, but the loop's real fit
    condition is `flight + phases <= usable`.
  - Fix: compare against the budget with the phases subtracted, and check the phases in the
    fit assertion.
- **A gust in an unknown unit reads as a 0 m/s forecast** (`src/weather.py:268-271`).
  - Unit failures mark only `windSpeed` and `windDirection` stale. A `windGust` that fails
    conversion becomes 0 m/s and is not marked stale.
  - The K-6 pilot notes trust any gust that isn't stale, so a gust above the rating would go
    unreported, with no "not checked" note.
  - It triggers only if NWS changes the gust unit. The fix is one line, plus a test beside
    `test_get_weather_bad_unit_is_stale`.

**Follow-ups for F-1 / F-1.5. Not reachable from the CLI today:** both need a custom
`MissionRequest`, which F-1 makes a user input.
- **The default climb point can land past line 1's first waypoint**
  (`planner._default_climb_waypoint`). It is always 600 m from the pad toward WP001, but
  Strat 1 measures the turn from the pad.
  - Probed with pads within 600 m of WP001: the recorded arrival differs from the one flown
    from the climb point by 5°–180°.
    - Pad 250 m behind WP001: recorded 0°, flown 180°.
    - Pad 400 m off at 135°: recorded 114°, flown 53°, with an 86 m pushback that isn't
      needed.
  - The transit runs 400–860 m past the direct route, against the docstring's "no longer
    than the transit without it".
  - The 500 m orbit is then centred 32–431 m from WP001, so it overlaps line 1.
  - Fix with F-1: place the climb point using the pad-to-line-1 distance, and measure
    Strat 1's arrival from the climb point.
- **`_check_minimum_legs` checks a leg that isn't flown** (`planner.py:426`). It walks
  `plan.waypoints`, so it checks pad→WP001 and never climb point→WP001.
  - A pad 100 m from WP001 is wrongly rejected, although the leg flown is 500 m.
  - A climb point 32 m from WP001 passes, although that is below the 126 m capture distance.
- **`--design-wind nan` or `inf` passes the argument check.** The run then fails in `geo` with
  a grid-too-small message that blames the wrong input. Reject non-finite values in
  `_design_wind_ms`.

**Merge method:** squash, or a rebase that drops the "test" commits (`88cd726`, the
`3b43c8f`, `37d2c86` and its revert `65439d1`). 52 commits would make `main` hard to read.

Everything verified also checked out: the duration/transit split, the fit loop's use of
values across passes, units, Optional paths and the VTOL takeoff altitude.
