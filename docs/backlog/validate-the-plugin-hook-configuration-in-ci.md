# Nothing in CI parses `hooks/hooks.json`, so a syntax error ships to every consumer

> Recorded 2026-09-03, from the final review of the writing-adrs system branch. Never
> filed as a GitHub issue.

## What

`hooks/hooks.json` wires the plugin's session hooks. `.github/workflows/pr.yml` selects no
job for a change under `hooks/`, and `scripts/ci/validate_manifests.py` never reads the
file, so a malformed edit passes the pull-request gate and reaches every consumer on their
next plugin update, where every hooked event then fails with a notice.

## Why it is still worth doing

ADR 022 makes `hooks/` a shipped artefact with no opt-in; ADR 005 makes CI the layer
enforcement depends on. The two together say this file needs a check where the other
shipped manifests have one.

## Acceptance

- `scripts/ci/validate_manifests.py` parses `hooks/hooks.json`, checks the `{"hooks": …}`
  shape, and fails on any entry whose `command` does not name `skills/writing-adrs/hook.py`
  or whose `type` is not `command`.
- `pr.yml`'s `changes` job sets `manifests=true` for a change under `hooks/`.
- A fixture in `scripts/ci/test_validate_manifests.py` proves the check can fail.
