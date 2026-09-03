---
status: Accepted
date: 2026-09-01
scope: [.github/workflows/pr.yml]
summary: Run `pr.yml`'s `adr` job on every pull request rather than gating it on `docs/adr/` or `scripts/` changing, so a `scope` entry left dangling by an unrelated rename fails at that PR rather than a later, unrelated one.
revisit-when: The job's runtime grows enough to matter across every PR, or a session-time hook system for `writing-adrs` is built and taken as the authoritative check instead.
---

# 021: Validate ADR scope on every pull request

## Context

[ADR 013][] keys ADR `scope` entries to the paths a decision binds and has
[`adr.py`][] reject any entry naming nothing on disk. That check runs only where
something invokes it, and on a pull request the sole place that happens is [`pr.yml`][]'s
`adr` job, gated on the diff touching `docs/adr/` or `scripts/`. A rename or deletion under
any other scoped path — `skills/`, `.claude-plugin/`, `.githooks/` — passes that PR clean,
and the stale entry it leaves behind surfaces only on some later, unrelated ADR-touching
commit, landing the fix on whoever is committing then rather than whoever renamed.

ADR 013's own Known Tensions section names this exactly and calls it deliberately accepted
rather than a trigger: the real remedy is "to watch paths continuously," which needs "a
system with its own hooks, tools and state" beyond the current skill-and-scripts pair.

Two directions were weighed for closing the gap: extend the existing scripts, or convert
`writing-adrs` into a standalone Claude Code plugin built around hooks, slash commands and
agents — the "system" ADR 013 gestured at, and this repository's acknowledged long-term
direction. `generate_index.py` does not need to know what a diff touched; it revalidates
every ADR's `scope` on every run. The filter on `pr.yml`'s `adr` job exists only to avoid
running that check needlessly, not because the check itself is selective.

## Options

### Option 1: Do nothing

**Pros:** No change to CI, no added run time, nothing to break.
**Cons:** The gap ADR 013 named stays open: a rename or deletion under a scoped path outside
`docs/adr/` and `scripts/` passes review silently, and the stale entry surfaces — if it ever
does — on whichever later, unrelated ADR commit happens to trip the filter.
**Risks:** More of the repo accumulates `scope` entries outside those two prefixes as the
corpus grows — `skills/`, `.claude-plugin/` and `.githooks/` already do — widening the blind
spot with nothing measuring it.

### Option 2: Run the `adr` job on every pull request (Accepted)

**Pros:** `generate_index.py` already revalidates every `scope` entry on every run regardless
of what changed, so this needs no new mechanism — only dropping the filter, rather than
widening it to today's scoped prefixes, which the next ADR naming a new one would immediately
re-narrow, reproducing the mirror-drift failure [ADR 006][] named for skill tooling. The job
installs no dependencies, so the added cost is a checkout and a stdlib script on every PR
rather than only the ones that used to trigger it.
**Cons:** Reaches the review path only — the deeper gap ADR 013 accepted stays open: the
omission case (a `scope` entry that should exist but was never added, which `generate_index.py`
checks for existence, never completeness) and [ADR 009][]'s `develop` bypass.
**Risks:** If the ADR corpus or the script's runtime ever grows enough to matter, that cost
now lands on every PR instead of only the subset that used to trigger it — though at a few
dozen small text files, checked with a stdlib line parser, that is a long way off, and today
it costs only latency: Actions minutes are free on this repository's public tier, so there is
no billing exposure to price in.

### Option 3: Convert `writing-adrs` into a standalone plugin with session-time hooks

**Pros:** The only shape that could plausibly close what Option 2 leaves open — a hook firing
on an agent's edit or rename could run the reverse `--for` lookup live and prompt updating
`scope` in the same change, moving detection from PR-gate time to edit time and catching the
omission case Option 2 cannot.
**Cons:** "Standalone" runs into [ADR 012][]'s cap of one marketplace entry per catalogue: a
second plugin is "not a manifest edit but an architectural change," reopening versioning,
changelog format and the tag scheme before any rot-detection benefit lands. Nothing in the
repository today defines what such a hook would do when it fires, or how a slash command or
agent would fit around it.
**Risks:** Designed now, against no concrete use case beyond this one and no hook
infrastructure to build on, it is the same guess ADR 012 rejected for a second plugin
generally — "designed against a guess ... likelier to be wrong than absent."

## Decision

Adopt Option 2: drop the path filter on `pr.yml`'s `adr` job so it runs unconditionally.

This closes the specific mechanism ADR 013 named — a stale `scope` entry surfacing only on
some later, unrelated commit — using validation `generate_index.py` already performs on every
run, nothing new to design or build. [ADR 005][]'s choice of CI as the layer enforcement
depends on, rather than the opt-in local hook, is why the fix belongs in `pr.yml` and not
`.githooks/pre-commit`.

Option 3 stays this repository's acknowledged long-term direction, but building toward it now
would mean designing a hook's behaviour and a plugin split against a single use case, with no
other need for either yet — the same order of guess ADR 012 rejected when it declined to
generalise the release flow for a second plugin nobody had proposed.

Neither option touches ADR 013's own decision — keying `scope` to paths — so this neither
supersedes nor discharges it. It narrows how silent Known Tension #1 is, for the review path
only.

## Consequences

- `pr.yml`'s `adr` job runs on every PR. The `changes` job's `adr` output, the
  `docs/adr/*|scripts/*` branch that sets it, and the `.github/workflows/*` branch's
  `adr=true` arm all become dead and go with this change, leaving that filter step to gate
  only `manifests` and `python`, which still need it. The `adr` job's own `needs: changes`
  goes too — it existed only to read that output, and dropping it lets the job start
  immediately instead of waiting on the filter step.
- The omission case, the `develop` bypass, and PR-gate rather than edit-time detection remain
  open, as ADR 013 already accepted. Closing them is Option 3's job, whenever it is taken up.
- The local pre-commit hook's index regeneration stays gated on a staged ADR file, unchanged
  by this decision — ADR 005 makes CI the layer enforcement depends on, so widening the hook
  too is a local convenience to reach for later, not a requirement here.

## Revisit watch

- 2026-09-02: [ADR 022][] built the session-time hook system Option 3 described. The trigger
  has not fired: the hooks are advisory, and CI stays the layer enforcement depends on.
  Reopen only if the hooks are ever taken as the authoritative check instead.

[ADR 005]: 005-mirror-declared-tooling-as-pr-checks.md
[ADR 006]: 006-validate-the-declaration-to-catch-mirror-drift.md
[ADR 009]: 009-keep-a-standing-develop-bypass.md
[ADR 012]: 012-advertise-one-plugin-per-catalogue.md
[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[`pr.yml`]: ../../.github/workflows/pr.yml
