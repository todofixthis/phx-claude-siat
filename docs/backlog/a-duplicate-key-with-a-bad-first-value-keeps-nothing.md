# A duplicate frontmatter key whose first value is bad should not claim that value stands

> Recorded 2026-11-16, from the test-analyst pass on the 9.0.1 fix for cascading
> frontmatter verdicts. Never a GitHub issue.

## What

`parse_fields()` in [`frontmatter.py`] keeps the first line for a key and reports any later
one as "sets field scope twice; the first value stands". Where that first value then fails
to load, nothing stands:

```text
scope: [{{x}}/]
scope: [a/]
```

reports both "sets field scope twice; the first value stands" and "field scope is not valid
YAML", and the valid second line is discarded unread. The duplicate message predates 9.0.0,
but the YAML loader in 9.0.0 makes a bad first value much easier to hit.

## Why it is still worth doing

The reader is told a value stands that the tool threw away. A writer fixing the YAML error
by deleting the first line ends up fine, but one who trusts "the first value stands" and
deletes the second loses the only valid line.

The duplicate message is appended during the line scan, before `_load_field` runs, so any
fix has to hold it until the first value's load result is known. A precedent exists: a
block-scalar first line is never stored, so a valid later line for the same key is used and
no duplicate is reported. Falling back to the second line here would match it, but the
duplicate branch currently `continue`s before setting `sequence_key`, so a second line that
opens a block sequence (`scope:` then indented `- item` lines) would lose its items, each
reported as "continued onto another line". A fallback has to keep them.

## Acceptance

- Where the first value for a key fails to load, no message says that value stands. Using
  the second line, naming it as discarded, or reporting the duplicate with no verdict on
  which stands all count.
- A test in [`test_frontmatter.py`] covers a duplicate key whose first value fails to load,
  asserting `parse_fields()`'s whole result — fields, problems and rejected keys. `parse_adr()`
  in [`adr.py`] reads the rejected keys, so a fix that changes them changes its verdicts too.
  Where the fix falls back to the second line, a second case covers a second line opening a
  block sequence.

[`adr.py`]: ../../skills/writing-adrs/adr.py

[`frontmatter.py`]: ../../skills/writing-adrs/frontmatter.py
[`test_frontmatter.py`]: ../../skills/writing-adrs/tests/test_frontmatter.py
