# Release Automation (Phase 2) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Worktree:** current checkout at `/Users/phx/Documents/phx-claude-siat` (branch: `feature/release-automation`) — reused, not a new worktree, because the branch is already checked out here.

**Goal:** Move release Phase 2 (tag, publish, back-merge) into a GitHub Actions workflow that runs when the release PR merges to `main`, so a release finishes with no standing human/agent bypass on `develop`.

**Architecture:** A `push: [main]`-triggered workflow authenticates as a GitHub App (a `develop`-scoped bypass actor, `Contents: write` only) to create an unsigned annotated tag, publish the Release from the CHANGELOG top-slice, and back-merge `main`→`develop`. A stdlib Python helper does the CHANGELOG parsing. The `releasing` skill shrinks to Phase 1. The maintainer performs the one-time GitHub setup (App, secrets, ruleset split, tag ruleset) from a durable runbook.

**Completed pre-work (already committed, not a task):** commit `884ba04` added the "Design specs and plans" section to `AGENTS.md`, recording that specs/plans are transient. No further AGENTS.md change is needed.

**Tech Stack:** GitHub Actions, `actions/create-github-app-token`, `gh` CLI, stdlib Python 3 (`json`, `re`, `argparse`, `unittest`).

## Global Constraints

- **NZ English throughout** — spelling, not just prose (`AGENTS.md`).
- **No root Python project.** `scripts/ci/` is stdlib-only by design (`validate_manifests.py` docstring; ADR 006). The new helper and its tests use only the standard library — no `pyproject.toml`, no PyPI deps, no pytest at the root.
- **Comments on the line preceding the code**, never trailing (`AGENTS.md`).
- **Pin every GitHub Action to a commit digest** with a trailing `# vX.Y.Z` comment; Renovate keeps pins current (existing `pr.yml` pattern).
- **Tag format:** `X.Y.Z`, no `v` prefix — matches the `plugin.json` version string.
- **Alphabetise unordered collections** (enums, config sections, object keys).

---

### Task 1: CHANGELOG release-notes helper

A stdlib module that returns the newest CHANGELOG entry's version and body, plus a CLI that writes the notes to a file and fails if the entry's version disagrees with `plugin.json`. This is the only unit-testable component; build it test-first.

**Files:**
- Create: `scripts/ci/release_notes.py`
- Test: `scripts/ci/test_release_notes.py`
- Modify: `.github/workflows/pr.yml` (add a step running the unit tests)

**Interfaces:**
- Produces: `top_entry(changelog: str) -> tuple[str, str]` returning `(version, notes)`; `plugin_version(plugin_file: Path) -> str`; a CLI `python3 scripts/ci/release_notes.py [--changelog PATH] [--plugin PATH] [--out PATH]` that prints the validated version to stdout, writes notes to `--out` (or stdout), and exits `1` on version mismatch. Task 2's workflow consumes the CLI.

- [ ] **Step 1: Write the failing tests**

```python
# scripts/ci/test_release_notes.py
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from release_notes import main, plugin_version, top_entry

CHANGELOG = """# Changelog

## 1.3.0 - 2026-07-22

### For phx plugin users

#### Changed

- Something changed.

## 1.2.0 - 2026-07-16

- Older entry.
"""


class TopEntryTests(unittest.TestCase):
    def test_returns_newest_version(self):
        version, _ = top_entry(CHANGELOG)
        self.assertEqual(version, "1.3.0")

    def test_notes_stop_before_the_previous_entry(self):
        _, notes = top_entry(CHANGELOG)
        self.assertIn("Something changed.", notes)
        self.assertNotIn("Older entry.", notes)

    def test_subsection_headers_are_not_boundaries(self):
        _, notes = top_entry(CHANGELOG)
        self.assertIn("#### Changed", notes)

    def test_missing_entry_raises(self):
        with self.assertRaises(ValueError):
            top_entry("# Changelog\n\nNo entries yet.\n")


class CliTests(unittest.TestCase):
    def test_version_mismatch_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as directory:
            changelog = Path(directory) / "CHANGELOG.md"
            changelog.write_text("# Changelog\n\n## 1.3.0 - 2026-07-22\n\n- x\n")
            plugin = Path(directory) / "plugin.json"
            plugin.write_text('{"version": "1.2.0"}')
            out = Path(directory) / "notes.md"
            with contextlib.redirect_stderr(io.StringIO()):
                code = main(
                    ["--changelog", str(changelog), "--plugin", str(plugin),
                     "--out", str(out)]
                )
            self.assertEqual(code, 1)

    def test_plugin_version_reads_the_field(self):
        with tempfile.TemporaryDirectory() as directory:
            plugin = Path(directory) / "plugin.json"
            plugin.write_text('{"version": "9.9.9"}')
            self.assertEqual(plugin_version(plugin), "9.9.9")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python3 -m unittest discover -s scripts/ci -t scripts/ci -p 'test_*.py'`
Expected: FAIL with `ModuleNotFoundError: No module named 'release_notes'`.

- [ ] **Step 3: Write the helper**

```python
#!/usr/bin/env python3
"""Extract the top CHANGELOG entry and assert it matches plugin.json's version.

Stdlib-only, run from the repo root, for the same reason as
scripts/ci/validate_manifests.py: the repo carries no root Python project.

    python3 scripts/ci/release_notes.py --out notes.md   # prints version; notes to file
"""

import argparse
import json
import re
import sys
from pathlib import Path

CHANGELOG_FILE = Path("CHANGELOG.md")
PLUGIN_FILE = Path(".claude-plugin/plugin.json")

# A version-entry heading: "## X.Y.Z - YYYY-MM-DD". Sub-sections use ### / ####,
# which this does not match (character 3 is "#", not a space).
RE_ENTRY = re.compile(r"^## (?P<version>\d+\.\d+\.\d+) - \d{4}-\d{2}-\d{2}\s*$")


def plugin_version(plugin_file: Path = PLUGIN_FILE) -> str:
    return json.loads(plugin_file.read_text(encoding="utf-8"))["version"]


def top_entry(changelog: str) -> tuple[str, str]:
    """Return (version, notes) for the newest CHANGELOG entry.

    notes is every line after the heading up to (not including) the next
    "## " entry heading, trimmed of surrounding blank lines.
    """
    lines = changelog.splitlines()
    start = None
    version = None
    for index, line in enumerate(lines):
        match = RE_ENTRY.match(line)
        if match:
            start, version = index, match.group("version")
            break
    if start is None:
        raise ValueError("no '## X.Y.Z - DATE' entry found in CHANGELOG")
    body = []
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        body.append(line)
    return version, "\n".join(body).strip() + "\n"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--changelog", type=Path, default=CHANGELOG_FILE)
    parser.add_argument("--plugin", type=Path, default=PLUGIN_FILE)
    parser.add_argument("--out", type=Path, help="write notes here instead of stdout")
    args = parser.parse_args(argv)

    version, notes = top_entry(args.changelog.read_text(encoding="utf-8"))
    declared = plugin_version(args.plugin)
    if version != declared:
        print(
            f"CHANGELOG top entry is {version} but plugin.json is {declared}",
            file=sys.stderr,
        )
        return 1
    if args.out:
        args.out.write_text(notes, encoding="utf-8")
        print(version)
    else:
        print(version)
        sys.stdout.write(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python3 -m unittest discover -s scripts/ci -t scripts/ci -p 'test_*.py'`
Expected: PASS (6 tests).

- [ ] **Step 5: Verify the CLI end-to-end against the real repo files**

Run: `out=$(mktemp) && python3 scripts/ci/release_notes.py --out "$out" && echo "---" && head -3 "$out"` (`mktemp` honours the session `TMPDIR`/scratchpad rather than hard-coding `/tmp`).
Expected: prints `1.3.0`, exit 0, and the notes file begins with the 1.3.0 entry body (the `### For phx plugin users` heading). (Confirms the match-assertion passes when CHANGELOG and `plugin.json` agree, as they do at `1.3.0`.)

- [ ] **Step 6: Wire the tests into CI**

In `.github/workflows/pr.yml`, the `changes` filter already sets `manifests=true` for `scripts/ci/*`. Add a step to the `manifests` job, after the "Validate the manifests and skill frontmatter" step:

```yaml
      - name: Unit-test the release-notes helper
        run: python3 -m unittest discover -s scripts/ci -t scripts/ci -p 'test_*.py'
```

- [ ] **Step 7: Commit**

Run `git status` to catch any related unstaged or untracked files, then use the `creative-commits` skill.

---

### Task 2: Release workflow

The `push: [main]` workflow that owns Phase 2. Each step is guarded so the job is safe to re-run to completion from any point — it never short-circuits on the first artefact found.

**Files:**
- Create: `.github/workflows/release.yml`

**Interfaces:**
- Consumes: `scripts/ci/release_notes.py` (Task 1); secrets `APP_ID`, `APP_PRIVATE_KEY` (maintainer setup, Task 3 runbook).

- [ ] **Step 1: Resolve the `create-github-app-token` digest**

Look up the current `actions/create-github-app-token` v2 release and its commit digest (e.g. `gh api repos/actions/create-github-app-token/releases/latest --jq '.tag_name'`, then the tag's commit SHA), to pin it like the repo's other actions. Use that `SHA # vX.Y.Z` in Step 2.

- [ ] **Step 2: Write the workflow**

```yaml
# Finishes release Phase 2 (tag, Release, back-merge) as the release GitHub App.
# The App permissions, the develop/main/tag rulesets, and the rollout order this
# workflow relies on live in docs/release-automation.md — change both together.
name: Release

on:
  push:
    branches: [main]

# Serialise release runs so a second push cannot race a back-merge in flight.
concurrency:
  group: release
  cancel-in-progress: false

# The workflow token needs nothing; every write uses the App token below.
permissions:
  contents: read

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      # A per-run installation token for the App, which is the develop-scoped
      # bypass actor. Minted here, revoked in the final step.
      - name: Mint an App installation token
        id: app-token
        uses: actions/create-github-app-token@<PINNED-DIGEST> # vX.Y.Z
        with:
          app-id: ${{ secrets.APP_ID }}
          private-key: ${{ secrets.APP_PRIVATE_KEY }}

      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          fetch-depth: 0
          token: ${{ steps.app-token.outputs.token }}

      - name: Read the release version
        id: version
        run: |
          version=$(python3 -c "import json; print(json.load(open('.claude-plugin/plugin.json'))['version'])")
          echo "version=$version" >> "$GITHUB_OUTPUT"

      # Every step below runs on every push and guards itself, so a re-run after
      # a partial failure finishes the missing steps without redoing the done
      # ones. There is NO whole-job guard: gating everything on tag-presence
      # would skip the Release and back-merge the moment the tag exists, hiding a
      # half-release behind a green check.

      # Asserts the CHANGELOG top entry matches plugin.json (exit 1 if not), and
      # writes the notes. Cheap and safe to run even when nothing needs releasing
      # (a consistent repo always has CHANGELOG top == plugin.json version).
      - name: Build the release notes
        run: python3 scripts/ci/release_notes.py --out notes.md

      - name: Create and push the tag if absent
        env:
          VERSION: ${{ steps.version.outputs.version }}
        run: |
          if git ls-remote --exit-code --tags origin "refs/tags/$VERSION" >/dev/null 2>&1; then
            echo "$VERSION already tagged; skipping"
          else
            # Identity is cosmetic: tags are unsigned (the ruleset does not enforce
            # signatures), so this is an unsigned annotated tag.
            git config user.name "github-actions[bot]"
            git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
            git tag -a "$VERSION" -m "Release $VERSION" "$GITHUB_SHA"
            git push origin "refs/tags/$VERSION"
          fi

      - name: Publish the GitHub Release if absent
        env:
          GH_TOKEN: ${{ steps.app-token.outputs.token }}
          VERSION: ${{ steps.version.outputs.version }}
        run: |
          if gh release view "$VERSION" >/dev/null 2>&1; then
            echo "release $VERSION already exists; skipping"
          else
            gh release create "$VERSION" --title "$VERSION" --notes-file notes.md
          fi

      - name: Back-merge main into develop if needed
        run: |
          git fetch origin main develop
          if git merge-base --is-ancestor origin/main origin/develop; then
            echo "develop already contains main; nothing to back-merge"
          else
            git checkout -B develop origin/develop
            # A real merge, not --ff-only: develop may have advanced since the PR
            # was cut. A conflict fails the job for manual resolution (the App is
            # Contents:write only, by design, so it cannot open a fallback PR).
            git merge --no-edit origin/main
            git push origin develop
          fi

      - name: Verify the back-merge on the remote
        run: |
          git fetch origin
          git merge-base --is-ancestor origin/main origin/develop

      - name: Revoke the App token
        if: always()
        env:
          GH_TOKEN: ${{ steps.app-token.outputs.token }}
        run: gh api --method DELETE /installation/token || true
```

- [ ] **Step 3: Static self-check of the workflow**

The container has no `actionlint`; do not install one (escalate if a check needs it). Instead verify structurally:

Run: `python3 -c "import pathlib; t=pathlib.Path('.github/workflows/release.yml').read_text(); assert 'on:\n  push:\n    branches: [main]' in t; assert 'permissions:\n  contents: read' in t; assert 'steps.guard' not in t, 'no whole-job guard'; assert 'gh release view' in t and 'ls-remote --exit-code --tags' in t, 'per-step idempotency guards present'; assert '<PINNED-DIGEST>' not in t, 'digest still a placeholder'; assert 'docs/release-automation.md' in t, 'cross-link to the runbook present'; print('ok')"`
Expected: `ok`. (Asserts there is no whole-job guard, that the tag and Release steps self-guard, and that Step 1's real digest replaced the placeholder before commit.)

Real validation is the dry-run in the Testing section and GitHub's own parse on push.

- [ ] **Step 4: Commit**

Run `git status` to catch any related unstaged or untracked files, then use the `creative-commits` skill.

---

### Task 3: Maintainer setup runbook

A durable operational doc (the transient spec will be deleted after implementation) covering the one-time GitHub setup and the rollout order.

**Files:**
- Create: `docs/release-automation.md`

- [ ] **Step 1: Write the runbook**

Write `docs/release-automation.md` with these sections, in NZ English:

- **Overview** — one paragraph: the `push: [main]` workflow finishes Phase 2 as the App; the `releasing` skill does only Phase 1. End with an explicit sync pointer: "The workflow implementing this setup is [`.github/workflows/release.yml`](../.github/workflows/release.yml); keep the two in sync when either changes." (The workflow carries the reciprocal comment pointing back here.)
- **One-time setup:**
  1. Create a GitHub App (repository permission **Contents: write only**), install it on `todofixthis/phx-claude-siat`, note the App ID, generate a private key.
  2. Add repository Actions secrets `APP_ID` and `APP_PRIVATE_KEY`.
  3. Split the **Trunk** ruleset into **Trunk–develop** (target `~DEFAULT_BRANCH`; add the App as a bypass actor, mode `always`) and **Trunk–main** (target `refs/heads/main`; no bypass). Both keep the existing rules (`deletion`, `non_fast_forward`, `pull_request` merge-only, `required_status_checks: gate`).
  4. Add a **tag ruleset** on `refs/tags/*`: `non_fast_forward` + `deletion`. No `required_signatures` — release tags are unsigned.
- **Rollout order (important):** keep the temporary Admin bypass on `develop` until the App is installed and one release has completed through the workflow; only then remove it. Closing the bypass before the App works strands the next release's Phase 2.
- **Recovery** — point to the `releasing` skill's manual-recovery checklist for a half-finished release.

- [ ] **Step 2: Verify links and spelling**

Run: `python3 scripts/ci/validate_manifests.py; echo "exit: $?" && rg -q 'release-automation.md' .github/workflows/release.yml && rg -q 'release.yml' docs/release-automation.md && echo "cross-links present"`
Expected: `exit: 0`, then `cross-links present` (both files point at each other). Re-read the doc for NZ English spelling.

- [ ] **Step 3: Commit**

Run `git status` to catch any related unstaged or untracked files, then use the `creative-commits` skill.

---

### Task 4: Slim the `releasing` skill to Phase 1

Remove Phase 2 and phase-detection; the skill now ends at "open the PR — CI finishes it," with a manual-recovery checklist that preserves the Phase 2 knowledge as a fallback. Do this last, after the workflow and runbook exist.

**Files:**
- Modify: `.agents/skills/releasing/SKILL.md`

- [ ] **Step 1: Rewrite the overview (lines 8–11)**

Replace the opening paragraph with:

```markdown
Drive Phase 1 of the gitflow release: open the `develop`→`main` PR. When a human merges
it, the `release` GitHub Actions workflow finishes the release — tag, GitHub Release,
back-merge — as the App. The release notes come from `phx:writing-release-notes`; this
skill owns the version number and every piece of version metadata that skill leaves to
its caller.
```

- [ ] **Step 2: Delete the "Phase detection" section (lines 50–64)**

Remove it entirely; the skill is invoked once, to prepare. Keep the "open PR already exists → reuse it" behaviour in Phase 1 step 7 and Edge cases.

- [ ] **Step 3: Rewrite Phase 1 step 7's back-merge clause (lines 90–98)**

The clause referencing "the step 11 back-merge" no longer has a step 11. Replace the merge-commit rationale sentence so it reads:

```markdown
7. **Open the PR** `develop`→`main` with the notes as the body
   (`gh pr create --base main --head develop`). If an open `develop`→`main` PR already
   exists (a prior aborted run), update its body rather than creating a duplicate. Tell
   the maintainer to **merge via a merge commit, not squash or rebase** — a merge commit
   keeps `develop`'s tip a parent of `main`, so the CI back-merge carries no content; a
   squash or rebase replays the work under new SHAs and the back-merge then conflicts.
   Report the PR URL and stop. Merging the PR triggers the `release` workflow; tell the
   maintainer to confirm it goes green, since a failed run leaves the release half-done.
```

- [ ] **Step 4: Replace the "Phase 2 — publish" section (lines 100–132) with a recovery checklist**

```markdown
## After merge — CI publishes

Merging the release PR triggers `.github/workflows/release.yml`, which as the App tags
the merge commit `X.Y.Z` (unsigned annotated), publishes the GitHub Release from the
CHANGELOG top entry, and back-merges `main`→`develop`. The skill's work ends at Phase 1;
confirm the workflow succeeded.

### Manual recovery (only if the workflow fails)

The workflow is idempotent; each step is independently checkable. Do only the missing
steps, then re-run the workflow or finish by hand from `develop`:

- **Tag missing?** `git tag -a X.Y.Z -m "Release X.Y.Z" <merge-commit-oid>` then
  `git push origin X.Y.Z`. Read the merge commit from
  `gh pr view <N> --json mergeCommit`. A hand-cut tag is signed (local `tag.gpgsign`);
  a mix of signed and unsigned release tags is fine, since signing is unenforced.
- **Release missing?** `gh release create X.Y.Z --notes-file <notes>`, notes from
  `python3 scripts/ci/release_notes.py --out notes.md`.
- **Back-merge missing?** From `develop`: `git fetch origin && git merge --no-edit origin/main && git push`.
  A direct push to `develop` needs the App or a temporary bypass. Verify on the remote:
  `git fetch origin && git merge-base --is-ancestor origin/main origin/develop`.
- **Issues to close?** Rare here (notes cite ADRs). Close any `#NNN` the notes reference
  by hand with a link to the Release.
```

- [ ] **Step 5: Update the Defaults "Tag format" bullet (lines 172–177)**

Replace it so it describes CI's unsigned annotated tag and the immutable-tag ruleset:

```markdown
- **Tag format:** `X.Y.Z`, no `v` prefix — matches the `plugin.json` version string. CI
  creates an **unsigned** annotated tag (`git tag -a X.Y.Z -m "Release X.Y.Z"`); a
  `refs/tags/*` ruleset makes release tags immutable (`non_fast_forward` + `deletion`)
  rather than signed. A hand-cut recovery tag is signed by local `tag.gpgsign`, which is
  harmless since signing is unenforced.
```

- [ ] **Step 6: Reword the two remaining "step 11" references (lines 149, 186)**

After deleting Phase 2, two mentions of "step 11" in the Validation gate and Edge cases point at nothing. Reword both to name the CI back-merge:

- Line ~149 (Validation gate): "The usual cause of failure is a skipped **step 11** back-merge; the other is a hotfix committed to `main` that never came back." → "The usual cause of failure is a failed CI back-merge; the other is a hotfix committed to `main` that never came back."
- Line ~186 (Edge cases): "...into `develop` first ... Usually a skipped **step 11**, not a hotfix." → "...into `develop` first ... Usually a failed CI back-merge, not a hotfix."

(Line numbers shift as earlier steps edit the file; match on the quoted text.)

- [ ] **Step 7: Delete the stale edge case**

Remove the "Phase 2 invoked before the PR has merged" bullet — there is no Phase 2 in the skill now.

- [ ] **Step 8: Verify the skill still validates and no "step 11"/"Phase 2" references remain**

Run: `python3 scripts/ci/validate_manifests.py; echo "exit: $?" && rg -n 'step 11|Phase 2' .agents/skills/releasing/SKILL.md || echo "no stale references"`
Expected: `exit: 0`, then `no stale references`.

- [ ] **Step 9: Commit**

Run `git status` to catch any related unstaged or untracked files, then use the `creative-commits` skill.

---

## Testing

- **Task 1 helper:** unit tests (`python3 -m unittest discover -s scripts/ci -t scripts/ci -p 'test_*.py'`) and the end-to-end CLI check against the real repo files.
- **Task 2 workflow:** cannot be unit-tested. After the maintainer setup exists, add a temporary `workflow_dispatch:` trigger and a dry-run guard that skips the tag-push/release/back-merge pushes (echo instead), confirm the run is green, then remove the dry-run scaffolding. The first real end-to-end is the **1.4.0** release, cut with the maintainer watching and the manual recovery checklist as the safety net.
- **Tasks 3–4 docs:** `validate_manifests.py` stays green; re-read for NZ English.

## Intentional Decisions

*(Populated during review — reviewers must not re-raise these)*

- **No ruleset drift-check workflow.** Reading rulesets via the API needs `Administration: read`; adding that to the release App to self-check its own rulesets widens its blast radius against the whole point of keeping it `Contents: write` only. Deferred rather than forcing admin scope. (Spec listed it; consciously cut here.)
- **No auto-opened fallback PR on back-merge conflict.** That needs `Pull requests: write`; keeping the App at `Contents: write` only is worth more than auto-recovering a near-impossible conflict (the ruleset forces merge-commit merges, so `develop` is normally an ancestor of `main`). A conflict fails the job loudly for manual resolution.
- **No CHANGELOG entry in this plan.** Per ADR 002 the changelog records released versions only, written fresh at release time; the change this plan ships is documented in the notes of whatever version carries it (1.4.0), by the `releasing` flow.
- **No ADR for this change.** Consistent with the maintainer's earlier call on the release-branch decision: low relitigation risk, and `docs/release-automation.md` carries the durable operational rationale.
- **Tests use stdlib `unittest`, not pytest.** A root pytest project is precluded by the no-root-project decision (ADR 006); `unittest` needs no dependency.

## Self-Review Checklist

- [ ] Every task ends with an independently testable deliverable.
- [ ] Does the plan header include a `**Worktree:**` field naming the existing worktree/checkout and branch?
- [ ] Does every commit step remind the agent to run `git status` first?
- [ ] Does the plan include an Intentional Decisions section?
- [ ] Spec coverage: helper (Task 1), workflow (Task 2), runbook + one-time setup + rollout (Task 3), slimmed skill + recovery (Task 4), AGENTS.md note (pre-work `884ba04`). Drift-check and CHANGELOG entry consciously deferred (Intentional Decisions).
- [ ] No placeholders: the only `<...>` tokens are the App-token digest (Task 2 Step 1 resolves it; Step 3 asserts it's gone) and merge-commit OID / PR number in recovery commands (runtime values).
- [ ] Type consistency: `top_entry`/`plugin_version` signatures and the CLI flags match between Task 1 and Task 2's `release_notes.py --out` call.
