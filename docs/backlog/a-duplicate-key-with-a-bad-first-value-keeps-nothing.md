# A duplicate frontmatter key whose first value is bad should not claim that value stands

> Recorded 2026-11-16, from the test-analyst pass on the 9.0.1 fix for cascading
> frontmatter verdicts. Never a GitHub issue.

## What

`parse_fields()` in [`frontmatter.py`] keeps the first line for a key and reports any later
line as "sets field scope twice; the first value stands". If that first value then fails
to load, nothing stands:

```text
scope: [{{x}}/]
scope: [a/]
```

For this input the tool reports both "sets field scope twice; the first value stands" and
"field scope is not valid YAML", and discards the valid second line unread. The duplicate
message predates 9.0.0, but the YAML loader in 9.0.0 makes a bad first value much easier
to hit.

## Why it is still worth doing

The tool tells the reader that a value stands after throwing it away. A writer who fixes
the YAML error by deleting the first line ends up fine. A writer who trusts "the first
value stands" and deletes the second line loses the only valid line.

The duplicate message is appended during the line scan, before `_load_field` runs, so a fix
has to hold the message until the first value's load result is known. A precedent exists.
The parser never stores a block-scalar first line, so it uses a valid later line for the
same key and reports no duplicate. Falling back to the second line here would match that
precedent. But the duplicate branch currently `continue`s before it sets `sequence_key`.
A second line that opens a block sequence (`scope:` then indented `- item` lines) would
therefore lose its items, each reported as "continued onto another line". A fallback has
to keep them.

## Acceptance

- If the first value for a key fails to load, no message says that value stands. Any of
  these counts: using the second line, saying which value was discarded, or reporting
  the duplicate with no verdict on which value stands.
- A test in [`test_frontmatter.py`] covers a duplicate key whose first value fails to load.
  It asserts the whole result of `parse_fields()`: fields, problems, and rejected keys.
  `parse_adr()` in [`adr.py`] reads the rejected keys, so a fix that changes them also
  changes its verdicts. If the fix falls back to the second line, a second case covers a
  second line that opens a block sequence.

[`adr.py`]: ../../skills/writing-adrs/adr.py

[`frontmatter.py`]: ../../skills/writing-adrs/frontmatter.py
[`test_frontmatter.py`]: ../../skills/writing-adrs/tests/test_frontmatter.py
