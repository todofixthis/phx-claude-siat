---
status: Accepted
date: 2026-09-02
scope: [hooks/, skills/writing-adrs/]
summary: A session hook reports a corpus finding — a dangling scope entry, a malformed ADR, a shared number, a stale index — once to the human and the agent where it was already present at session start, and where it arose during the session once when it appears and once more at Stop; never on every turn until fixed, and never by blocking.
revisit-when: A finding reported at baseline survives three consecutive sessions unfixed, or a consumer's CI cannot gate on the tool and blocking becomes the only enforcement.
---

# 026: Report findings by delta from a session baseline

## Context

[ADR 022][] gives the ADR tool a per-batch check and a `Stop` hook. The check finds what
[ADR 013][]'s Known Tension #1 wanted watched continuously: a `scope` entry that names
nothing after a rename or deletion. The question is what to do with a finding, and how
often.

Two failure modes bound the answer.

First, ADR 013 prescribes dropping an entry where the rot is real, and asking whether a
decision that binds nothing should stay `Accepted`. A hook that raises a finding on every
turn until it closes gets the first half without the second. Deleting the entry is the
fastest way to stop the noise, and the tool cannot tell that from a considered removal.

Second, a repository that already carries a stale entry when the session opens would nag
every turn about a fault the agent was never asked to touch. ADR 013's Known Tension #2
says this is how an advisory dies: people tune it out.

`additionalContext` reaches the agent as a system reminder that the human never sees.
`systemMessage` is shown to the user. A `Stop` hook's `additionalContext` continues the
turn as non-error feedback, under the same eight-continuation cap as a block. Every hook
that matches an event runs in parallel, and session files are kept for thirty days by
default. These facts were verified against the [hooks reference][hooks] on 2026-09-02.

## Options

### Option 1: Do nothing — report every finding on every check

**Pros:** Nothing is ever missed while it stands.
**Cons:** A pre-existing fault nags every turn. An agent under the continuation cap at
`Stop` deletes the entry to stop the noise.
**Risks:** People tune the advisory out.

### Option 2: Delta from a baseline, raised at most twice (Accepted)

`SessionStart` takes a snapshot of the findings present and reports them once, to the
agent as context and to the human as a `systemMessage`. These findings belong to the
repository. A finding that arises during the session belongs to the agent. The hook
reports it once when it appears, and once more at `Stop` or `SubagentStop` if it is still
open, then stays silent. What the agent leaves open reaches the next session's baseline,
and so reaches the human.

**Pros:** Each finding reaches an agent twice and a human at least once. Nothing is raised
often enough to be worth silencing.
**Cons:** A finding the agent ignores twice is gone until the next session.
**Risks:** State lives outside the repository. A lost state file triggers a new baseline,
which bills the agent's own open findings to the repository, though the human then sees
them.

### Option 3: Block the turn until findings close

Return `decision: block` from `Stop`.

**Pros:** Nothing ships with a dangling entry.
**Cons:** The fix for a dangling entry is often a human call: whether the decision still
binds anything. A blocked agent cannot make that call, so it deletes the entry instead.
**Risks:** Hooks become the authoritative check. That fires [ADR 021][]'s second trigger
and inverts [ADR 005][].

## Decision

Option 2. The hook is advisory, as ADR 013 made the lookup, and people silence an advisory
that repeats. Twice is enough for an agent to act, and few enough not to coerce it. The
baseline keeps a repository's history from being billed to the session that opened it.
`check` still exits non-zero on every finding, baseline or not. CI is where a standing
fault is gated, and the hooks do not change that.

## Consequences

- Session state lives under the plugin's data directory, one file per session. The file
  holds the baseline and the reported set, keyed by managed root, and the injected rows of
  [ADR 025][], keyed by agent. A subagent therefore shares the session's baseline and keeps
  its own context. Hooks run in parallel, so updates take a lock on a sidecar file. Files
  are pruned after thirty days to match session retention.
- A finding is identified by its kind and by the value that would have to change: the
  entry for a dangling scope, the number for a collision, the file for a malformed ADR,
  and the root for a stale index. A renumber therefore creates no new finding, but a rename
  of a malformed file does.
- `compact` keeps the baseline and the reported set, and resets only the injected rows.
  `clear` and `fork` start a new session and take a new baseline. An open finding is then
  reported again as the repository's, and the human sees it.
- A repository that the session touches without having started in it has no baseline
  until its first check. That check takes the snapshot after the write that triggered it,
  so a finding the write introduced is billed to the repository and reaches the human that
  way.
- The per-batch check runs for every root that a file tool in the batch wrote an ADR under,
  and regenerates the index for each. It also runs for the root resolved from the hook's
  `cwd` ([ADR 024][]), but only reports on that root. A root that the session only reads
  from gets injections and is never checked.

[ADR 005]: 005-mirror-declared-tooling-as-pr-checks.md
[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 021]: 021-validate-adr-scope-on-every-pull-request.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[ADR 024]: 024-resolve-the-repository-root-from-the-path-in-hand.md
[ADR 025]: 025-deliver-binding-decisions-by-hook-at-first-touch.md
[hooks]: https://code.claude.com/docs/en/hooks
