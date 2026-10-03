# Measure whether a tool call denied after `PreToolUse` loses the ADR rows injected for it

> Recorded 2026-10-03, carried over from the backlog item on recording rows only once
> delivered in full, whose fix left this unmeasured. Not a GitHub issue (ADR 020).

## What

`on_pre_tool_use` in [`skills/writing-adrs/hook.py`][`hook.py`] records a row as injected
when it returns the row's text. If the harness then denies the tool call and drops that
call's `additionalContext`, the row is recorded but never seen, and no later touch
delivers it.

## Measuring it

In a scratch checkout, make `hook.py` append a unique token per case to
`additionalContext`, and load that checkout with `claude --plugin-dir <checkout>`, since
the plugin runs `${CLAUDE_PLUGIN_ROOT}/skills/writing-adrs/hook.py`. Trigger each denial
below on a path that binds a decision, then search the session's transcript JSONL under
`~/.claude/projects/` for the token. Asking the model whether it saw the rows is weaker
evidence.

Run an allowed call first as the positive control: if its token is not in the transcript,
hook context is not written there and the method cannot tell lost from delivered. Give
each case, the control included, a fresh session: the hook records rows per decision, not
per path, so any later touch binding a decision already delivered returns nothing, and
that silent repeat reads as lost.

Test each denial separately, since they can differ:

- a refused permission prompt;
- another `PreToolUse` hook returning a deny;
- an auto-mode classifier denial;
- a settings `deny` rule, which may stop the call before `PreToolUse` runs at all, in which
  case nothing is recorded and nothing is lost.

If every case either delivers the token or never runs the hook, delete this item. If any
loses it, design the fix. [`hooks/hooks.json`][] registers `PostToolBatch`, not
`PostToolUse`: before deferring the record to either, check whether its event lists the
denied call. If it does, moving the record there fixes nothing.

## Acceptance

- The outcome per denial case, with the Claude Code version, goes in a `## Revisit watch`
  entry on ADR 025, which owns the once-per-row delivery promise.
- If rows are lost, a test in [`skills/writing-adrs/tests/test_hook.py`][`test_hook.py`]
  stands a denial in as a `PreToolUse` with no later post event, then asserts a second
  touch of the same path delivers the row in full.
- If the fix moves the record to a post event, a second test issues two parallel
  `PreToolUse` events on one path followed by one post event, and asserts the row arrives
  in full once. Today the `State` lock already covers parallel `PreToolUse` calls.

[`hook.py`]: ../../skills/writing-adrs/hook.py
[`hooks/hooks.json`]: ../../hooks/hooks.json
[`test_hook.py`]: ../../skills/writing-adrs/tests/test_hook.py
