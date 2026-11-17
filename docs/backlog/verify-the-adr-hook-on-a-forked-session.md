# Verify whether a forked session re-injects the decisions its parent already delivered

> Recorded 2026-10-03, from a review of whether [`hook.py`][] re-injects decisions
> redundantly. Unconfirmed. The code suggests it, but nothing has been run. Not a GitHub
> issue (ADR 020).

## What

[`hook.py`][] keys its record of injected rows by `session_id`, and
[`hooks/hooks.json`][] runs `SessionStart` on `fork`. [ADR 026][] says `fork` starts a new
session and re-baselines. If a fork gets a new `session_id` but inherits the parent's
transcript, the hook injects the rows already in that transcript again on first touch.

The hooks reference lists `fork` as a `SessionStart` source but doesn't say whether the
session id changes. It also says forked sessions reported `resume` before Claude Code
v2.1.214, which would skip the reset logic entirely. To settle the question, run the steps
below, then act on the outcome.

## Manual steps

Run these steps in a terminal from the repository root, with the plugin loaded
(`claude --plugin-dir ./` for the working tree). Make sure no other Claude session is
running, so the state files below belong to these sessions alone. Note the output of
`claude --version`.

1. Find where state lives:
   `find ~/.claude/plugins/data /tmp/phx-writing-adrs -path '*/sessions/*.json' -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -n 3`.
   `SessionStart` writes the state file at launch, so the first entry is the parent's. Its
   filename is the parent's session id, **A**. The command uses GNU `find`. Empty output
   means a different data directory, so use the directory that
   `python3 -c 'import tempfile; print(tempfile.gettempdir())'` prints in place of `/tmp`.
   Confirm **A** against the id Claude Code itself shows (`/status`, or the filename of the
   newest transcript under `~/.claude/projects/`).
2. In the parent session, ask the agent to read `hooks/hooks.json`. Rows 022, 025, and 026
   should arrive. Ask again, and nothing should arrive.
3. Fork the session with either `claude --resume <A> --fork-session` or the in-session
   `/fork` or `/branch`, whichever your version has. On the command form, pass
   `--plugin-dir ./` again, or the fork has no hook at all. Before any tool call, read the
   fork's session id (**B**) the same independent way as in step 1, and list the sessions
   directory again.
   - If **B** differs from **A**, the fork has a new session id. A new state file with a
     populated `roots` entry shows that `SessionStart` ran for the fork. No new file means
     it did not run. Possible causes include a version that reports `fork` as `resume`, or a
     fork that uses another plugin data directory.
   - If **B** equals **A**, the id is shared and there is no redundancy. You can stop here.
4. In the fork, with no tool call, ask the agent to quote verbatim the first line of the
   decisions block it received for `hooks/hooks.json`. A verbatim quote ("Decisions binding
   hooks/hooks.json — these paths, not the whole corpus …") means the transcript carried
   the rows over. An agent that can only paraphrase has no copy.
5. In the fork, ask the agent to read `hooks/hooks.json`. The redundancy shows as rows 022,
   025, and 026 arriving again.

Read the outcome from this table:

| Step 3 | Step 4 | Step 5 | Reading |
|---|---|---|---|
| shared id | — | — | No redundancy. |
| new id, `SessionStart` ran | quoted | rows arrive | Confirmed. A fork repeats its parent's rows. |
| new id, `SessionStart` ran | no copy | rows arrive | Correct. The fork has no copy to duplicate. |
| new id, `SessionStart` did not run | quoted | rows arrive | Confirmed, and `SessionStart` is not firing on `fork` either. Record the version and the `source` it reported. |
| new id, `SessionStart` did not run | no copy | rows arrive | Correct, but `SessionStart` is not firing on `fork`. Record the same. |

Under a new id, step 5 always shows rows arriving, because the first touch creates an empty
state whether or not `SessionStart` ran. The step 4 quote is what separates redundant from
correct.

## Why it is still worth doing

Each repeated row costs context in a session the user forked precisely because it already
holds useful context. ADR 025 also promises that each row lands once.

## Acceptance

- The outcome, with the Claude Code version, is recorded on the branch that closes this
  item.
- If the redundancy is confirmed, a backlog item for the fix replaces this one. Seeding the
  fork's state from its parent needs the parent's id, which the `SessionStart` event may
  not carry.
- If the redundancy is not confirmed, this item is deleted. If the session id turned out to
  be shared, ADR 026 also gets a `## Revisit watch` entry.
- The branch that closes this item removes the **Forking** sentence under Edge cases in
  [`docs/writing-adrs-hooks.md`][writing-adrs-hooks], which links to this item.

[`hook.py`]: ../../skills/writing-adrs/hook.py
[`hooks/hooks.json`]: ../../hooks/hooks.json
[ADR 026]: ../adr/026-report-findings-by-delta-from-a-session-baseline.md
[writing-adrs-hooks]: ../writing-adrs-hooks.md
