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

Two failure modes bound the answer. ADR 013 prescribes dropping an entry where the rot is
real and asking whether a decision binding nothing should stay `Accepted`; a hook that
raises a finding on every turn until it closes gets the first half without the second,
since deleting the entry is the fastest way to make the noise stop, and the tool cannot
tell that from a considered removal. And a repository that already carries a stale entry
when the session opens would nag every turn about a fault the agent was never asked to
touch, which is how ADR 013's Known Tension #2 says an advisory dies: tuned out.

`additionalContext` reaches the agent as a system reminder the human never sees;
`systemMessage` is shown to the user. A `Stop` hook's `additionalContext` continues the
turn as non-error feedback, under the same eight-continuation cap as a block. Every hook
matching an event runs in parallel, and session files are kept for thirty days by default.
Verified against the [hooks reference][hooks] on 2026-09-02.

## Options

### Option 1: Do nothing — report every finding on every check

**Pros:** Nothing is ever missed while it stands.
**Cons:** A pre-existing fault nags every turn; an agent under the continuation cap at
`Stop` deletes the entry to make the noise stop.
**Risks:** The advisory is tuned out.

### Option 2: Delta from a baseline, raised at most twice (Accepted)

`SessionStart` snapshots the findings present and reports them once, to the agent as
context and to the human as a `systemMessage`; they belong to the repository. A finding
that arises in the session is the agent's: reported once when it appears, once more at
`Stop` or `SubagentStop` if still open, then silent. What the agent leaves open reaches the
next session's baseline, and so the human.

**Pros:** Each finding reaches an agent twice and a human at least once, and nothing is
raised often enough to be worth silencing.
**Cons:** A finding the agent ignores twice is gone until the next session.
**Risks:** State lives outside the repository; a lost state file re-baselines, billing the
agent's own open findings to the repository — though the human then sees them.

### Option 3: Block the turn until findings close

Return `decision: block` from `Stop`.

**Pros:** Nothing ships with a dangling entry.
**Cons:** The remedy for a dangling entry is often a human call — whether the decision
still binds anything — and a blocked agent cannot make it. It deletes instead.
**Risks:** Hooks become the authoritative check, which fires [ADR 021][]'s second trigger
and inverts [ADR 005][].

## Decision

Option 2. The hook is advisory, as ADR 013 made the lookup, and an advisory that repeats is
one that gets silenced. Twice is enough for an agent to act and little enough not to
coerce, and the baseline keeps a repository's history from being billed to the session that
opened it. `check` still exits non-zero on every finding, baseline or not: CI is where a
standing fault is gated, and the hooks do not change that.

## Consequences

- Session state lives under the plugin's data directory, one file per session: the
  baseline and the reported set keyed by managed root, and the injected rows of
  [ADR 025][] keyed by agent, so a subagent shares the session's baseline and keeps its own
  context. Updates take a lock on a sidecar file, since hooks run in parallel, and files are
  pruned after thirty days to match session retention.
- A finding is identified by its kind and the value that would have to change: the entry
  for a dangling scope, the number for a collision, the file for a malformed ADR, the root
  for a stale index. A renumber therefore mints no new finding; a rename of a malformed
  file does.
- `compact` keeps the baseline and the reported set and resets only the injected rows;
  `clear` and `fork` start a new session and re-baseline, so an open finding is reported
  again as the repository's and the human sees it.
- A repository the session touches without having started in it has no baseline until its
  first check, which snapshots one then — after the write that triggered it, so a finding
  that write introduced is billed to the repository and reaches the human that way.
- The per-batch check runs for every root a file tool in the batch wrote an ADR under,
  regenerating each, and for the root resolved from the hook's `cwd` ([ADR 024][]), which
  it only reports on. A root the session only ever reads from is injected into, never
  checked.

[ADR 005]: 005-mirror-declared-tooling-as-pr-checks.md
[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 021]: 021-validate-adr-scope-on-every-pull-request.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[ADR 024]: 024-resolve-the-repository-root-from-the-path-in-hand.md
[ADR 025]: 025-deliver-binding-decisions-by-hook-at-first-touch.md
[hooks]: https://code.claude.com/docs/en/hooks
