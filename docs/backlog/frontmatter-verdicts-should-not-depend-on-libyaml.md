# A frontmatter value's verdict should not depend on whether libyaml is installed

> Recorded 2026-10-14, from the reviewer pass over PR #92's answer to the ultrareview. Not a
> GitHub issue (ADR 020).

## What

[`frontmatter.py`][] parses each field with `CBaseLoader` if PyYAML was built with
libyaml, and with the pure-Python `BaseLoader` otherwise. Its `LOADER` holds that choice,
made at import. The two loaders disagree on two kinds of input, and `LoaderDifferenceTests`
in [`test_frontmatter.py`][] pins today's behaviour:

- **A tab inside a plain value** (`summary: a<TAB>b`) loads under `CBaseLoader`, and
  `BaseLoader` reports it as invalid YAML. A tab inside *quotes* (`summary: "a<TAB>b"`)
  loads under both.
- **A literal byte-order mark (U+FEFF) in a value** loads under `CBaseLoader` and gives a
  false "holds a comment" problem under `BaseLoader`. That holds whether the mark is plain
  (`a<BOM>b`), leading (`<BOM>a`), or inside double quotes (`"a<BOM>b"`). Only the escaped
  form, `"a\ufeffb"`, loads under both.

So a hand-written ADR that holds either input passes `check` on a machine with libyaml and
fails it on one without. Make the verdict the same under both loaders.

**By default, report both inputs under both loaders**, in `_load_field`:

- Report a tab in a *plain* scalar, with a message that says to quote the value. The check
  must look at plain scalars only. A quoted tab must keep loading under both loaders,
  because `yaml_value` in [`adr.py`][] writes a tab exactly that way.
- Report a literal U+FEFF anywhere in a value, quoted or not, with a message that points to
  the `\ufeff` escape. Quoting alone doesn't help here.

Choose "accept under both" instead only if you can make `BaseLoader` load these inputs
without rewriting the value. That option changes the fallback ADR 034 records ("falling
back to the pure-Python `BaseLoader`"), so if you take it, add a note to that ADR.

## Why it is still worth doing

The tool's own writer is already safe. `yaml_value` writes a value plain only when it reads
back under both loaders, so it quotes a tab and escapes a BOM. Only hand-written values are
exposed, and they're rare. But a corpus whose `check` passes in one CI and fails in another
is the kind of disagreement ADR 034 set out to remove, and the person who meets it can't
see the cause.

## Acceptance

- Tests that assert one verdict under both loaders replace `LoaderDifferenceTests`. They
  switch loader by patching `frontmatter.LOADER`, as its `parse_under` helper does, and
  cover each of these inputs:
  - a tab in a plain value
  - a literal BOM in a plain value, a leading BOM, and a literal BOM inside quotes
  - controls that must still load under both loaders: a quoted tab, and the escaped
    `"a\ufeffb"`
- `yaml_value`'s output for a value that holds a tab or a BOM still reads back verbatim
  under both loaders.

[`adr.py`]: ../../skills/writing-adrs/adr.py
[`frontmatter.py`]: ../../skills/writing-adrs/frontmatter.py
[`test_frontmatter.py`]: ../../skills/writing-adrs/tests/test_frontmatter.py
