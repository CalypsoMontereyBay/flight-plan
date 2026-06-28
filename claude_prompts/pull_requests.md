# Pull Requests

## Goals

This file will be used to generate pull requests for the Calypso Monterey Bay flight plans.

## Prompts

1. Read this file.  Execute the 1st task under "Prep"

## Review

1. There is an active PR on this 

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

#### 1. One-time prerequisite: install & authenticate `gh`

This environment does **not** currently have the GitHub CLI installed
(`gh: command not found`). Claude reviews PRs by calling `gh`, so install it
once:

```bash
# Debian/Ubuntu (this machine is Linux)
sudo apt install gh
# or see https://cli.github.com for other platforms
```

Then authenticate (this is a *you* step — Claude does not handle your
credentials):

```bash
gh auth login        # choose GitHub.com -> HTTPS -> browser
gh auth status       # confirm you are logged in
```

The remote is already set correctly, so no extra configuration is needed:

```
origin  https://github.com/CalypsoMontereyBay/flight-plan.git
```

> Without `gh`, Claude can still review code, but only what is already on disk
> (the current branch / working-tree diff). It cannot *discover* or fetch a
> remote PR by number until `gh` is available.

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
2. **Kick off the review.** Give Claude the PR number or URL:
   ```
   /review 12
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