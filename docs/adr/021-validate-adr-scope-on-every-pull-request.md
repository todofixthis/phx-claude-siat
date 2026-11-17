---
status: Accepted
date: 2026-09-01
scope: [.github/workflows/pr.yml]
summary: Run `pr.yml`'s `adr` job on every pull request rather than gating it on `docs/adr/` or `scripts/` changing, so a `scope` entry left dangling by an unrelated rename fails at that PR rather than a later, unrelated one.
revisit-when: The job's runtime grows enough to matter across every PR, or a session-time hook system for `writing-adrs` is built and taken as the authoritative check instead.
---

# 021: Validate ADR scope on every pull request

## Context

[ADR 013][] keys ADR `scope` entries to the paths a decision binds, and has [`adr.py`][]
reject any entry that names nothing on disk. That check runs only where something invokes
it. On a pull request, the only place that happens is [`pr.yml`][]'s `adr` job, which runs
only when the diff touches `docs/adr/` or `scripts/`. A rename or deletion under any other
scoped path, such as `skills/`, `.claude-plugin/`, or `.githooks/`, passes its own PR clean.
The stale entry it leaves behind surfaces only on some later, unrelated commit that touches
an ADR. The fix then falls to whoever is committing at that point, rather than to whoever
did the rename.

ADR 013's own Known Tensions section names this gap exactly, and calls it deliberately
accepted rather than a trigger. It says the real remedy is "to watch paths continuously,"
which needs "a system with its own hooks, tools and state" beyond the current pair of skill
and scripts.

Two directions were weighed for closing the gap. One extends the existing scripts. The
other converts `writing-adrs` into a standalone Claude Code plugin built around hooks, slash
commands, and agents. That plugin is the "system" ADR 013 gestured at, and this
repository's acknowledged long-term direction. `generate_index.py` does not need to know
what a diff touched, because it revalidates every ADR's `scope` on every run. The filter on
`pr.yml`'s `adr` job exists only to avoid running that check needlessly. The check itself is
not selective.

## Options

### Option 1: Do nothing

**Pros:** CI does not change, run time does not grow, and nothing can break.
**Cons:** The gap ADR 013 named stays open. A rename or deletion under a scoped path outside
`docs/adr/` and `scripts/` passes review with nothing reported. The stale entry surfaces, if
it ever does, on whichever later, unrelated ADR commit happens to trip the filter.
**Risks:** As the corpus grows, more of the repository gains `scope` entries outside those
two prefixes. `skills/`, `.claude-plugin/`, and `.githooks/` already have them. The blind
spot widens, and nothing measures it.

### Option 2: Run the `adr` job on every pull request (Accepted)

**Pros:** `generate_index.py` already revalidates every `scope` entry on every run, whatever
changed, so this needs no new mechanism. It only drops the filter. Widening the filter to
today's scoped prefixes instead would not hold: the next ADR to name a new prefix would
narrow it again at once, reproducing the mirror-drift failure that [ADR 006][] named for
skill tooling. The job installs no dependencies, so the added cost is a checkout and a
stdlib script on every PR, rather than only on the PRs that used to trigger it.
**Cons:** It reaches only the review path. The deeper gap that ADR 013 accepted stays open.
That gap covers the omission case, a `scope` entry that should exist but was never added,
where `generate_index.py` checks for existence and never for completeness. It also covers
[ADR 009][]'s `develop` bypass.
**Risks:** If the ADR corpus or the script's runtime ever grows enough to matter, that cost
now lands on every PR instead of only the subset that used to trigger it. At a few dozen
small text files, checked with a stdlib line parser, that point is a long way off. Today the
cost is only latency. Actions minutes are free on this repository's public tier, so there is
no billing exposure to price in.

### Option 3: Convert `writing-adrs` into a standalone plugin with session-time hooks

**Pros:** It is the only shape that could plausibly close what Option 2 leaves open. A hook
that fires on an agent's edit or rename could run the reverse `--for` lookup live, and
prompt the agent to update `scope` in the same change. That moves detection from the PR gate
to edit time, and catches the omission case that Option 2 cannot.
**Cons:** "Standalone" runs into [ADR 012][]'s cap of one marketplace entry per catalogue. A
second plugin is "not a manifest edit but an architectural change," and it reopens
versioning, changelog format, and the tag scheme before any benefit to rot detection lands.
Nothing in the repository today defines what such a hook would do when it fires, or how a
slash command or agent would fit around it.
**Risks:** Designed now, against no concrete use case beyond this one and with no hook
infrastructure to build on, the plugin is the same guess that ADR 012 rejected for a second
plugin in general: "designed against a guess ... likelier to be wrong than absent."

## Decision

Adopt Option 2. Drop the path filter on `pr.yml`'s `adr` job so the job runs
unconditionally.

This closes the specific mechanism ADR 013 named, a stale `scope` entry that surfaces only
on some later, unrelated commit. It uses validation that `generate_index.py` already
performs on every run, so there is nothing new to design or build. [ADR 005][] chose CI,
rather than the opt-in local hook, as the layer enforcement depends on. That choice is why
the fix belongs in `pr.yml` and not in `.githooks/pre-commit`.

Option 3 stays this repository's acknowledged long-term direction. Building toward it now,
though, would mean designing a hook's behaviour and a plugin split against a single use
case, with no other need for either yet. That is the same order of guess ADR 012 rejected
when it declined to generalise the release flow for a second plugin nobody had proposed.

Neither option touches ADR 013's own decision to key `scope` to paths, so this ADR neither
supersedes nor discharges it. It makes Known Tension #1 less silent, for the review path
only.

## Consequences

- `pr.yml`'s `adr` job runs on every PR. Three parts of the filter become dead and go with
  this change: the `changes` job's `adr` output, the `docs/adr/*|scripts/*` branch that sets
  it, and the `adr=true` arm of the `.github/workflows/*` branch. The filter step then gates
  only `manifests` and `python`, which still need it. The `adr` job's own `needs: changes`
  goes too. It existed only to read that output, and dropping it lets the job start at once
  instead of waiting on the filter step.
- The omission case, the `develop` bypass, and detection at the PR gate rather than at edit
  time all remain open, as ADR 013 already accepted. Closing them is Option 3's job,
  whenever someone takes it up.
- The local pre-commit hook still regenerates the index only when an ADR file is staged.
  This decision does not change that. ADR 005 makes CI the layer enforcement depends on, so
  widening the hook too is a local convenience to add later, not a requirement here.

## Revisit watch

- 2026-09-02: [ADR 022][] built the session-time hook system that Option 3 described. The
  trigger has not fired, because the hooks are advisory, and CI stays the layer enforcement
  depends on. Reopen only if the hooks are ever taken as the authoritative check instead.

[ADR 005]: 005-mirror-declared-tooling-as-pr-checks.md
[ADR 006]: 006-validate-the-declaration-to-catch-mirror-drift.md
[ADR 009]: 009-keep-a-standing-develop-bypass.md
[ADR 012]: 012-advertise-one-plugin-per-catalogue.md
[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[`pr.yml`]: ../../.github/workflows/pr.yml
