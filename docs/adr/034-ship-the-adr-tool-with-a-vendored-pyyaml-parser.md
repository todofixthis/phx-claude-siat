---
status: Accepted
date: 2026-10-07
scope: [.claude-plugin/, .githooks/pre-commit, .github/workflows/pr.yml, hooks/, pyproject.toml, renovate.json, scripts/frontmatter.py, skills/writing-adrs/]
summary: Ship the ADR tool beside the writing-adrs skill and run it and its plugin-declared hooks on bare python3 with nothing installed, deferring every frontmatter value that is not provably plain to a pure-Python PyYAML vendored there and loaded lazily under a private name — not a hand-written grammar, a uv-resolved dependency or an optional import, and not a standalone plugin or skill-frontmatter hooks.
revisit-when: A consumer needs the skills without the hooks and Claude Code offers no per-hook opt-out, or a hook needs more than a POSIX shell and python3 to run, or a hook event's median cost is measured above 100 ms on a corpus whose frontmatter loads PyYAML or on this repository's, or Claude Code plugins gain a way to install their own Python dependencies.
---

# 034: Ship the ADR tool with a vendored PyYAML parser

## Context

[ADR 022][] ships [`adr.py`][] and `hook.py` beside the `writing-adrs` skill as a
standard-library tool, run by consumers and by every hook event as bare `python3` with no
install step, which [ADR 017][] requires of shipped tooling. Its parser,
[`frontmatter.py`][], reads frontmatter line by line as a grammar this repository defines.
GitHub renders the same block through a YAML parser, so `yaml_hazard()` in `adr.py` refuses
values a YAML reader would misread, judged by a hand-written character class.

[ADR 007][]'s Revisit watch predicted on 2026-09-03 that this class would be "wrong on
exactly the inputs nobody tried". On 2026-10-07 the two cookiecutter template repositories
tried one. Their ADRs scope paths under a directory literally named
`{{ cookiecutter.github_project_name }}/`, which YAML needs quoted in a flow sequence:
unquoted, `{` opens a mapping. [PyYAML][] reads the quoted form as intended; `yaml_hazard()`
refuses any entry opening with a quote, and refuses the unquoted form too. No spelling of a
path under the templated tree passes, so `check`, `index` and every writing command refuse
in both repositories, and `for` skips those ADRs, injecting nothing for the files they
govern. `frontmatter.py` also keeps the quotes when it splits a list, so a matcher would
miss the path even if the refusal were lifted.

[ADR 031][] gave `scripts/` a dependency path, and a [backlog item][] deferred the PyYAML
swap, to be declared in `scripts/pyproject.toml`. That reaches the repository's own
environment and nothing a consumer runs. The same module also parses skill frontmatter for
[`validate_manifests.py`][], through the symlink [ADR 023][] chose.

Cost bounds every option. ADR 022 measured a hook event's median at 74 ms against a 100 ms
budget, finding that cost tracked the interpreter rather than the corpus. Measured on this
container on 2026-10-07 over this repository's 35 ADRs, pure-Python PyYAML costs 8–18 ms to
import warm (50 ms on a cold first run), and `safe_load` over every block 14.5 ms, against
0.12 ms for the line parser. Parsing every block on every event would overrun the budget
and make the cost grow with the corpus.

This ADR restates ADR 022 with its standard-library claim narrowed, and supersedes it.

## Options

Every option keeps the line-level pass `frontmatter.py` runs now — one field per line, no
block scalar, no duplicate key — because those are this repository's own rules, stricter
than YAML's: PyYAML accepts a wrapped value and keeps the *last* of two duplicate keys. All
keep writing line-based too, since ADR 023 forbids the tool rewriting a sentence the agent
wrote. What ranks the options is who decides what a *value* means.

### Option 1: Do nothing

Keep the hand-written value grammar and extend it per case. At its strongest: accept a
list entry quoted end to end with no escapes, strip the quotes, and refuse the rest as
`yaml_hazard()` does now.

**Pros:** About twenty lines of standard library, no third-party code, no cost added.
**Cons:** Splitting a list on commas breaks a quoted entry holding `, `, so the narrow fix
needs a flow-sequence tokeniser as well. Anything outside the subset is refused although
it is valid YAML.
**Risks:** Each refusal is found by a consumer, as this one was, and each costs a plugin
release to lift.

### Option 2: Defer non-plain values to a vendored PyYAML (Accepted)

Copy PyYAML's pure-Python `yaml/` package — 6.0.3, MIT-licensed, 252 KB without its
optional C extension, requiring Python 3.8 or later — into `skills/writing-adrs/`. A value
on an allowlist is taken as written: it opens with an ASCII letter, an ASCII digit, `.`,
`/` or `_`, and holds only those, U+0020 and a fixed punctuation set, kept in
`frontmatter.py`, that excludes `:` and `#`. In a list, the rule applies to each
comma-separated entry, with `[` and `]` only as delimiters, and the set further excludes
`,[]{}?` inside an entry. Every other line goes to PyYAML's `BaseLoader`, imported only
then. An allowlist errs by deferring a safe value, which costs an import, never by
misreading one.

**Pros:** The tool accepts any single-line value YAML accepts, and reads it as YAML does.
`BaseLoader` resolves no types, so `yes`, `34` and an ISO date stay strings. A corpus of
plain values never imports PyYAML: all 198 frontmatter values in this repository's ADRs and
skills pass the allowlist, and the pass costs 0.17 ms.
**Cons:** Third-party code in the tree, kept out of this repository's lint, format and
spelling checks. A corpus with one quoted value pays the import on every hook event, since
each event parses the whole corpus.
**Risks:** The allowlist is itself hand-written; a value it accepts that YAML reads
differently is the old bug back. PyYAML is not GitHub's renderer, so a value the two read
differently goes unflagged where `yaml_hazard()` might have caught it — unlikely for a
single-line scalar, but that guard goes. Renovate updates declared dependencies, not copied
files, so a vendored copy goes stale silently, security fixes included.

#### Sub-question: which library

[ruamel.yaml][] 0.19.1 is also MIT-licensed and pure Python, at 604 KB. What it adds is
round-tripping, which buys nothing where writes stay line-based. PyYAML.

### Option 3: Declare PyYAML a runtime dependency, run through `uv`

Add PyYAML to `skills/writing-adrs/pyproject.toml` and have the hooks and the skill invoke
the tool with `uv run`.

**Pros:** Renovate's `pep621` manager tracks it, and no third-party code enters the tree.
**Cons:** Every consumer needs `uv` on `PATH`, and the hooks need more than a POSIX shell
and `python3` — ADR 022's revisit condition, fired by choice rather than need.
**Risks:** A cold resolve on a slow or absent network stalls a hook — the risk ADR 007
named for `scripts/` — in every session of every consumer.

### Option 4: Import PyYAML when installed, else fall back

Try `import yaml`; where it fails, use the hand-written grammar.

**Pros:** No vendored code, no install step.
**Cons:** Which grammar decides a value depends on the environment.
**Risks:** A consumer without PyYAML keeps today's bug, and a corpus can pass in CI, where
PyYAML is installed, and fail in a session, or the reverse.

## Decision

Option 2. The value grammar is YAML's, so YAML's parser should have the last word on any
value the tool cannot prove plain. Option 1 keeps refusing valid YAML, a consumer at a
time. Of the routes to PyYAML, vendoring alone keeps ADR 017's no-install-step rule and ADR
022's `python3`-only hooks; Option 3 moves a maintenance cost off this repository and onto
every consumer's setup, and Option 4 keeps the bug for exactly the consumers who would hit
it.

Deferring only what is not provably plain answers the cost for a corpus like this one. The
cookiecutter corpora quote a path in most ADRs, so they pay the import on nearly every
event: an estimated 82–92 ms median on ADR 022's figures, inside the budget with little
headroom. It is measured at implementation on one of them, and the carried trigger names
such a corpus, so a breach there reopens this decision.

Option 2's remaining risk, an allowlist wrong in the permissive direction, is one a test can
close: every value the allowlist accepts must load to the same string under the vendored
`BaseLoader`. The generated cases must reach where a plain scalar breaks: every character of
the punctuation set and every YAML indicator at a value's opening, middle and end, inside and
outside a list entry; `:` and `#` beside a space and a tab; C0 control characters and
non-ASCII whitespace. A fixture value the allowlist must defer shows the test can fail. A
wrong allowlist then fails CI, where today's character class fails a consumer.

Everything else ADR 022 decided stands, for the reasons it gives: the tool sits beside the
skill, the plugin's `hooks/hooks.json` declares the hooks, and neither a standalone plugin
([ADR 012][]) nor hooks declared in the skill's frontmatter alone replace that. This ADR
supersedes it only because its summary and its sub-question call the tool standard library
only, which no longer holds.

## Consequences

- `frontmatter.py` loads the vendored package from its own resolved path under a private
  module name, so neither an installed PyYAML nor the `scripts/frontmatter.py` symlink can
  substitute another copy.
- `yaml_hazard()`'s character class goes; a value PyYAML refuses is reported as any other
  malformed field. A quoted `scope` entry becomes valid, with a regression test for the
  templated-path case above.
- `skills/writing-adrs/pyproject.toml`'s wheel `only-include` gains the vendored package and
  its licence, so ADR 022's `uvx` recipe ships them too.
- PyYAML is pinned to an exact version in the root `pyproject.toml`'s dev dependencies, which
  Renovate's `pep621` manager already reads, and `pr.yml` fails when the vendored tree
  differs from that release's sdist `lib/yaml/`. A Renovate bump then fails CI until the
  tree is re-vendored, rather than leaving the copy behind unnoticed.
- `scripts/frontmatter.py` reaches the vendored package through the symlink, which breaks
  ADR 007's stdlib-only rule for `scripts/`; [ADR 035][] restates that rule.
- The skill's frontmatter rules, the "standard library only" claims in `adr.py`'s and
  `frontmatter.py`'s docstrings, the skill's `pyproject.toml` comment and the README are
  corrected in the implementing change, along with the README's example naming ADR 007.
  The backlog item tracks that change and is deleted when it lands.

[ADR 007]: 007-keep-repo-scripts-stdlib-only.md
[ADR 012]: 012-advertise-one-plugin-per-catalogue.md
[ADR 017]: 017-move-a-skills-deterministic-steps-into-shipped-code.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[ADR 023]: 023-let-a-shipped-tool-write-what-it-wholly-owns.md
[ADR 031]: 031-adopt-a-uv-workspace-at-the-repository-root.md
[ADR 035]: 035-keep-repo-scripts-stdlib-only-bar-the-vendored-yaml-parser.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[backlog item]: ../backlog/scripts-frontmatter-parser-should-use-pyyaml.md
[`frontmatter.py`]: ../../skills/writing-adrs/frontmatter.py
[PyYAML]: https://pypi.org/project/PyYAML/
[ruamel.yaml]: https://pypi.org/project/ruamel.yaml/
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
