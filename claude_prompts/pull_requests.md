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