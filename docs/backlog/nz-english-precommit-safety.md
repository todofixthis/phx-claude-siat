# nz-english: make scan.py safe to run from a pre-commit hook over staged files

> Recorded 2026-08-27, raised in review of [#37][] and deferred from 5.0.0.
> Was GitHub issue #39.

## What

Make [`scan.py`][] usable from a pre-commit hook over staged files, and fix the two header
defects that a file-list invocation exposes.

The pre-commit use is a good one — it is how a very large repository avoids a minutes-long
sweep — but the tool has three rough edges that make it escalate against a healthy tree,
so [`SKILL.md`][] currently documents only that the tool takes files, without endorsing
the workflow.

## The header lies about filtering

`used_git` is set only in the directory branch of `discover()`, so a file-list invocation
inside a repository reports `walk`:

```
$ python3 skills/nz-english/scan.py AGENTS.md docs/adr/INDEX.md
swept: /…/phx-claude-siat (2 files, walk)      # inside a repo

$ python3 skills/nz-english/scan.py AGENTS.md docs
swept: /…/phx-claude-siat (27 files, git)      # one directory flips it back
```

So the flag means "at least one target was a directory in a repo", not "filtering
applied". `SKILL.md` now describes that honestly, but the header would be more useful
saying what it means — `files` for an explicit list, distinct from `git` and `walk`.

## A single file breaks the agent-instructions line

`common_base()` returns the file itself when there is one target, so the header computes
`relative_to(base)` against a file:

```
$ python3 skills/nz-english/scan.py AGENTS.md
swept: /…/phx-claude-siat/AGENTS.md (1 files, walk)
agent instructions: .
```

Base should be the parent where the sole target is a file. (`1 files` is worth fixing
while there.)

## Three exit-2 cases a hook hits routinely

`SKILL.md` tells the agent that exit 2 means stop and escalate, so each of these reports a
healthy tool as broken:

- a staged **deleted** path — routine without `--diff-filter` — exits 2 with `no such
  path`;
- a commit staging **only** excluded files (`*.lock`, `CHANGELOG.md`) exits 2 with `no
  files to search`, which is the correct outcome for a hook and not a misconfiguration;
- an **empty** argument list falls back to `Path.cwd()` and sweeps the whole tree,
  silently, on a commit that touched nothing relevant.

The first two want an exit code distinct from a broken run, or a flag saying an empty
selection is expected. The third is the dangerous one, since it does the opposite of what
a hook wants and says nothing.

## Acceptance

- A file-list invocation reports its provenance honestly in the header.
- A single file target reports its parent as the swept path, and singular/plural agrees.
- A hook can distinguish "nothing staged to check" from "the tool failed" by exit code.
- An empty explicit selection does not silently become a whole-tree sweep.
- `SKILL.md` documents the hook usage once the above hold.

[#37]: https://github.com/todofixthis/phx-claude-siat/pull/37
[`SKILL.md`]: ../../skills/nz-english/SKILL.md
[`scan.py`]: ../../skills/nz-english/scan.py
