# The ADR hook never shows the agent `binding()`'s per-path "binds nothing here" warning

> Recorded 2026-10-03, from a review of whether [`hook.py`][] repeats anything redundantly.
> Low value; delete it if the lost signal never bites. Not a GitHub issue (ADR 020).

## What

[`binding()`][`adr.py`] prints a warning to stderr for a shared ADR number, a heading
disagreeing with its filename, and an unreadable ADR (ADR 029), each saying the ADR "binds
nothing here". The hooks reference says stderr from a hook that exits 0 goes to the debug
log only, and `hook.py` always exits 0, so the agent never sees that line through the hook.
Three `hook.py` runs on one path in a fixture corpus with two files numbered 003 printed it
to stderr three times and put none of it in stdout.

The fault itself is not silent. `inspect()` reports it as a finding, which `SessionStart`
reports at baseline (with a `systemMessage` to the human), `PostToolBatch` reports when it
appears mid-session, and `Stop` raises once more (ADR 026); a fixture run confirmed the
baseline and mid-session cases. What is lost is which paths are affected: an agent
editing a file the colliding ADR scopes gets no sign that its decisions are not loaded.

If it bites, return the warnings from `binding()` (keep the stderr print for `adr.py for`)
and deliver each once per session through `additionalContext` from
[`on_pre_tool_use`][`hook.py`].

## Complications

- `on_pre_tool_use` returns `None` when no row is new. A colliding ADR binds nothing, so the
  case that warrants a warning is usually the one with no rows; that early return has to
  change.
- Once per session needs state keyed by the warning text. `State.root()` records `reported`
  by `Finding.id`, and these warnings are strings.
- Changing what `binding()` returns changes its callers and their tests.
- ADR 029's Consequences say the warnings print on every touched path, so this wants an ADR
  amendment via `phx:writing-adrs`, not a code change alone.

## Acceptance

- A test in [`skills/writing-adrs/tests/test_hook.py`][] builds a corpus with a shared
  number and asserts the first `PreToolUse` on a path the colliding ADR scopes carries the
  "binds nothing here" line in `additionalContext`, and a second does not.
- `adr.py for` still prints the warning to stderr and exits 0.
- ADR 029's Consequences match.

[`adr.py`]: ../../skills/writing-adrs/adr.py
[`hook.py`]: ../../skills/writing-adrs/hook.py
[`skills/writing-adrs/tests/test_hook.py`]: ../../skills/writing-adrs/tests/test_hook.py
