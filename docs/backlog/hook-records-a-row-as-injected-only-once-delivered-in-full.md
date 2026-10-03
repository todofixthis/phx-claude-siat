# The ADR hook should record a row as injected only once it has been delivered in full

> Recorded 2026-10-03, from a review of whether [`hook.py`][] re-injects decisions
> redundantly. Not a GitHub issue (ADR 020).

## What

`on_pre_tool_use` in [`skills/writing-adrs/hook.py`][`hook.py`] appends each row's key to the
agent's `injected` list as it collects the row, before `rows[:MAX_ROWS]` and
`fit_bound_rows` decide what is rendered in full. A row that lands on the "Also binding, by
number and path" line is therefore recorded as injected having delivered only its number.
Every later touch of a path it binds skips it, so its title, summary and `revisit-when` never
arrive.

Record a key only for a row rendered in full. `fit_bound_rows` will need to report which
rows it kept in `shown`.

## Reproduction

Drive `hook.main()` with `PreToolUse` `Read` events in one session, the repository as `cwd`:

1. `skills/writing-adrs/hook.py` binds fourteen decisions: ten arrive in full (003 to 025)
   and 026, 027, 028 and 031 arrive by number only.
2. `pyproject.toml`, which only ADR 031's scope names, returns nothing. `031` is never
   delivered in full.

## Why it is still worth doing

ADR 025 injects rows so an agent does not relitigate a decision it was never shown. A row
that is named but never shown fails that, and the label's "these paths, not the whole
corpus" gives the reader no sign a summary is missing.

## Complications

- Rows left unrecorded keep appearing on the "Also binding" line until a touch has room to
  deliver them in full. The repeated line is short and shrinks as rows land.
- Not measured: a tool call denied after `PreToolUse` has run. The row is recorded at hook
  time, so a denial would also lose it. Check whether the harness delivers the context of a
  denied call before designing for it.

## Acceptance

- A test in [`skills/writing-adrs/tests/test_hook.py`][`test_hook.py`] touches a path whose
  rows overflow `MAX_ROWS`, then a path binding an overflowed row, and asserts the second
  delivers that row in full.
- A second test uses rows under `MAX_ROWS` whose summaries overrun `MAX_CHARS`, and asserts
  a row `fit_bound_rows` moved to the number-only line is delivered in full on a later touch.
- A test asserts no row is delivered in full twice to one agent in one session. It passes
  today; it guards the fix against trading one fault for the other.
- The reproduction above delivers `031` in full on the `pyproject.toml` touch.

[`hook.py`]: ../../skills/writing-adrs/hook.py
[`test_hook.py`]: ../../skills/writing-adrs/tests/test_hook.py
