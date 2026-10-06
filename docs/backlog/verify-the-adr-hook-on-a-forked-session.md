# Verify whether a forked session re-injects the decisions its parent already delivered

> Recorded 2026-10-03, from a review of whether [`hook.py`][] re-injects decisions
> redundantly. Unconfirmed: the code suggests it, nothing has been run. Not a GitHub issue
> (ADR 020).

## What

[`hook.py`][] keys its injected-row record by `session_id`, and
[`hooks/hooks.json`][] runs `SessionStart` on `fork`. [ADR 026][] says `fork` starts a new
session and re-baselines. If a fork gets a new `session_id` while inheriting the parent's
transcript, the rows already in that transcript are injected again on first touch.

The hooks reference lists `fork` as a `SessionStart` source but does not say whether the
session id changes. It also says forked sessions reported `resume` before Claude Code
v2.1.214, which would skip the reset logic entirely. Settle it by running the steps below,
then act on the outcome.

## Manual steps

Run in a terminal from the repository root, with the plugin loaded (`claude --plugin-dir ./`
for the working tree) and no other Claude session running, so the state files below belong
to these sessions alone. Note `claude --version`.

1. Find where state lives:
   `find ~/.claude/plugins/data /tmp/phx-writing-adrs -path '*/sessions/*.json' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -n 3`.
   `SessionStart` writes the state file at launch, so the first entry is the parent's; the
   filename is its session id, **A**. The command is GNU `find`; empty output means a
   different data directory, so use `python3 -c 'import tempfile; print(tempfile.gettempdir())'`
   in place of `/tmp`. Confirm **A** against the id Claude Code itself shows
   (`/status`, or the newest transcript's filename under `~/.claude/projects/`).
2. In the parent session, ask it to read `hooks/hooks.json`. Rows 022, 025 and 026 should
   arrive. Ask again: nothing should.
3. Fork it, either `claude --resume <A> --fork-session` or the in-session `/fork` or
   `/branch`, whichever your version has. Pass `--plugin-dir ./` again on the command form,
   or the fork has no hook at all. Before any tool call, read the fork's session id
   the same independent way as in step 1 (**B**), and list the sessions directory again.
   - **B** differs from **A**: the fork has a new session id. A new state file with a
     populated `roots` entry shows `SessionStart` ran for it; no new file means it did not
     (a version that reports `fork` as `resume`, or another plugin data directory).
   - **B** equals **A**: the id is shared, there is no redundancy, and you can stop.
4. In the fork, with no tool call, ask it to quote verbatim the first line of the decisions
   block it received for `hooks/hooks.json`. A verbatim quote ("Decisions binding
   hooks/hooks.json — these paths, not the whole corpus …") means the transcript carried the
   rows over; an agent that can only paraphrase has no copy.
5. In the fork, ask it to read `hooks/hooks.json`. Rows 022, 025 and 026 arriving again is
   the redundancy.

| Step 3 | Step 4 | Step 5 | Reading |
|---|---|---|---|
| shared id | — | — | No redundancy. |
| new id, `SessionStart` ran | quoted | rows arrive | Confirmed: a fork repeats its parent's rows. |
| new id, `SessionStart` ran | no copy | rows arrive | Correct: the fork has no copy to duplicate. |
| new id, `SessionStart` did not run | quoted | rows arrive | Confirmed, and `SessionStart` is not firing on `fork` either: record the version and the `source` it reported. |
| new id, `SessionStart` did not run | no copy | rows arrive | Correct, but `SessionStart` is not firing on `fork`: record the same. |

Step 5 always shows rows arriving under a new id, because the first touch creates an empty
state whether or not `SessionStart` ran; the step 4 quote is what separates redundant from
correct.

## Why it is still worth doing

Each repeated row costs context in a session the user chose to fork precisely because it
already holds useful context, and ADR 025 promises each row lands once.

## Acceptance

- The outcome, with the Claude Code version, is recorded on the branch that closes this
  item.
- If the redundancy is confirmed, a backlog item for the fix replaces this one; seeding the
  fork's state from its parent needs the parent's id, which the `SessionStart` event may
  not carry.
- If it is not, this item is deleted, and ADR 026 gets a `## Revisit watch` entry if the
  session id turned out to be shared.
- The **Forking** sentence under Edge cases in
  [`docs/writing-adrs-hooks.md`][writing-adrs-hooks], which links to this item, is removed
  on the branch that closes it.

[`hook.py`]: ../../skills/writing-adrs/hook.py
[`hooks/hooks.json`]: ../../hooks/hooks.json
[ADR 026]: ../adr/026-report-findings-by-delta-from-a-session-baseline.md
[writing-adrs-hooks]: ../writing-adrs-hooks.md
