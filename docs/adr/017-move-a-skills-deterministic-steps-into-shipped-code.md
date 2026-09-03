---
status: Accepted
date: 2026-08-22
scope: [.agents/skills/, .github/workflows/pr.yml, skills/]
summary: Move a skill's deterministic steps into a tool that ships beside it, needs no install step, and reports rather than edits, holding the skill's prose and that code together with a test that fails when they drift — not an external linter such as Vale.
revisit-when: Another skill ships tooling, so the per-skill coupling assertions want generalising, or nz-english's scope narrows back to prose only.
---

# 017: Move a Skill's Deterministic Steps into Shipped Code

## Context

[`phx:nz-english`][`nz-english`] asked an agent to type nine `rg` commands, build two
control files by hand to prove those commands could fail, recognise about sixty
documented false positives in the output, and derive a right-end guard character for
each rename it verified. None of that is judgement, and every part of it has failed in practice:

- `rg … || echo "(clean)"` reported nine clean sweeps for searches that never ran, `rg`
  exiting 2 on error rather than 1.
- An unquoted expansion in zsh became one unrecognised flag; a `path=` assignment wiped
  `$PATH`.
- A command with no trailing path blocked on an open pipe until killed.
- `cataloged` and `cataloging` went missing for a month behind a right-anchored pattern.

Each was answered with more prose, until two of the skill's five sections existed
largely to stop an agent typing a command wrongly. That prose is unverifiable: nothing
fails when it is wrong, and a clean report is what stops anyone looking again.

The general question is which parts of an LLM-run skill belong in the skill at all.
[ADR 005][] established that a skill gaining tooling gains a matching pull-request
check in the same change, and [ADR 006][] declined to design a declaration schema
against a single example. This is the second example.

## Options

Options 2 and 3 both leave the substitution table in two places — `SKILL.md`'s Markdown
for a reader, and a machine-readable copy for the searcher — and both therefore need
something holding the copies together. That cost is shared and does not rank them. What
remains is where each one's coverage stops, and what a consumer has to install.

### Option 1: Do nothing

Keep the searches in the skill's prose and keep answering each failure with more of it.

**Pros:** No new code, no new dependency, no version bump. The skill stays one file.
**Cons:** The failures recur, because what is asked of the reader — retype nine commands
exactly, every time — is not something prose can make reliable. Each fix lengthens the
skill, and length is what gets a skill skimmed.
**Risks:** Every one of these failures is silent. A miss survives indefinitely, because
the search that would have found it reported clean.

### Option 2: Ship a stdlib tool with the skill (Accepted)

A [`scan.py`][] beside `SKILL.md`, standard library only, invoked as
`python3 <skilldir>/scan.py`. It **reports and never edits**. The substitution table
becomes data in [`table.py`][], from which the patterns, the noise classification and the
guard characters all derive.

**Pros:** The hazards disappear by construction — no shell quoting, no missing path, no
exit code to swallow. Discovery through `git ls-files -co --exclude-standard` honours
`.gitignore` without a rule of our own. The guard character is computed from the table
rather than derived by a reader. Roughly a quarter of the skill's prose goes, and what
remains is judgement.
**Cons:** The skill now needs `python3` and a bundled file, which is a breaking change
to how it is invoked. The table exists in two places — the skill's Markdown and the
code — where it used to exist in one.
**Risks:** A second copy of the table can drift. Answered by three assertions in the
bundled tests: every row must find its word in a US-spelled control, the row counts must
match, and every literal in the skill's US column must exist in the code. Mutation
testing confirmed each fails for its own reason, and that the first does *not* catch a
row added to neither side — which is why the second exists.

#### What stays with the agent

Triage is per occurrence, not per word: whether a name is this repo's to change, or one
something outside holds a copy of. So are the rows that need reading rather than
applying, reading the diff for conversions that should not have happened, and the test
suite's blind spots. The tool never edits a file, because a rename is the thing the
skill says kills you.

### Option 3: Adopt Vale

[Vale][] is a mature, MIT-licensed, markup-aware prose linter, and the case for it is
real. Its `substitution` check is close to this skill's data model — regex keys, an
`ignorecase` flag, and an `exceptions:` list that is exactly the documented-noise list as
a first-class concept. Being markup-aware, it distinguishes a fenced code block from
prose, which a line-oriented regex cannot. And `Vale.Spelling` with a Hunspell dictionary
would catch US spellings a seventeen-row table structurally cannot — a weakness this
skill states in its own words.

Vale *can* see repo-defined identifiers, through Views with `engine: tree-sitter` and an
`expr` query — the rejection is not a capability claim. It ships grammars for 27
languages and extracts comments only by default, so identifiers need a query written per
language, and a language outside that set — shell, YAML, TOML, Dockerfile, SQL,
[Kotlin][#1125] — has none to write. Upstream is moving rather than standing still:
[#884][] asked to lint more than comments and was closed in favour of [#769][], which
completed in June 2025.

**Pros:** All of the above, plus a maintained upstream, a dictionary that reaches words no
enumerated table can, and no word list of ours to keep.
**Cons:** A tree-sitter query per language, written and maintained by us, for the
identifier half. A consumer must install a Go binary, set a `StylesPath` and run
`vale sync`. No packaged en_NZ dictionary — en_GB is a hand-rolled exercise. `.gitignore`
is not honoured; inclusion is globs in `.vale.ini`. And the table would live in a third
place rather than a second.
**Risks:** A language nobody wrote a query for is not reported as uncovered — it is
simply absent from the results.

#### Sub-question: Vale for prose, the bundled tool for identifiers

The two are not exclusive. A hybrid answers the coverage objection outright — the bundled
tool still reaches every language, and Vale adds the dictionary and the prose-versus-code
awareness on top — so what remains is the install step, weighed in Decision.

## Decision

Adopt Option 2, and treat it as the general rule: **a skill's deterministic steps move
into code that ships with the skill; that code needs no install step, reports rather than
edits, and wherever the skill's prose and the code encode the same thing, a test fails
when they drift.** The no-install clause is not decoration — it is what makes a skill
usable on first invocation in a fresh checkout.

That clause is comparative rather than absolute, and the ADR should not pretend
otherwise: a machine with no `python3` cannot run this skill either. The difference is
degree and shape. `python3` is present on most developer machines and needs no
per-repository setup; Vale needs a Go binary *and* a `StylesPath` *and* a `vale sync`
before the first run, and the last two are per-repository work someone must redo in every
checkout. A Vale advocate is entitled to the first half of that and not the second.

Vale loses on the *shape* of its silence rather than on having any. Both options are
silent about what they do not cover: a US spelling outside the seventeen rows, or an
`-our` word outside the thirty enumerated, returns nothing from the bundled tool, and
that is the same defect the Hunspell dictionary would have fixed. The difference is that
the tool's silence is per word — bounded, enumerated in a file, and surrounded by a
report that prints every row including the empty ones — where a missing tree-sitter query
takes a whole file type dark with nothing in the output saying so. Bounded silence you
can audit; unbounded silence you cannot.

Scope that to the word list, which is where it holds. Discovery's silence is not bounded:
honouring `.gitignore` means an ignored subtree goes dark behind nothing but a file count,
and Vale's explicit globs are arguably louder there. The claim is that the *table's*
coverage is enumerable, not that the tool is silent about nothing.

The hybrid loses on the install step alone — the coverage argument does not touch it,
since the bundled tool would still reach every language underneath.

The three coupling assertions are *this* skill's realisation of the general rule, not
part of it. They exist because `nz-english` owns a Markdown table; a future skill with no
table has nothing to couple and will need its own answer. Generalising them now would be
the premature schema ADR 006 declined to design; each skill that ships tooling asks again.

ADR 006's revisit trigger — "A second skill ships tooling" — fires here, and is
answered by generalising the mirror rather than by making the declaration executable:
[`pr.yml`][]'s `python` job becomes a matrix over the skill directories that ship a
`pyproject.toml`. That arm is cut from ADR 006's `revisit-when` and struck through where
its body sets it out; the other arm, a skill shipping a `package.json`, has not fired and
stays live. ADR 005 already requires the matching check in the same change, and this
satisfies it.

## Consequences

- The skill is a breaking change for its callers: it now requires `python3` and a file
  that ships beside it. Where the tool cannot run, the skill says to stop and escalate
  rather than improvise the searches back, since the deleted commands encoded a guard
  and a noise list a typed command will not.
- `[tool.autohooks]` in a second `pyproject.toml` is now load-bearing in the same way the
  first one is, and the matrix values in `pr.yml` must stay full paths — the manifest
  check looks for each skill directory as a plain substring of the workflow.
- A change to either tooling-shipping skill now runs both matrix legs. Cheap, and it
  keeps the path filter honest.
- The noise list is a maintained artefact. Only already-correct words belong on it:
  `colorist` and `behaviorist` sit inside the skill's noise section and are *real* hits,
  so an implementer lifting that section wholesale would ship the miss the skill treats
  as the serious direction.
- **The `-og` blind spot closes, and it is the one place this is not a faithful port.**
  The hand-run searches were case-insensitive throughout, so their guard excluded a
  following `U` as well as a `u`, and a camel-cased `dialogUrl` reached no search at all —
  a permanent miss the skill had to document and ask for by hand. Scoping the flag to the
  guard alone catches it, at the cost of reporting a SCREAMING_CASE `DIALOGUE`, which is
  over-reporting and the direction the skill prefers. The differential run against the
  nine commands agrees on every other match and diverges here by one, deliberately.
- A consumer's correctness no longer rests on tests they never run, because
  `--self-check` runs the patterns over the bundled controls. Its reach is narrower than
  it looks and the skill says so: it bypasses discovery, so it proves the patterns fire
  and nothing about whether the sweep reached any files.
- **The word list is ours to maintain, permanently.** Seventeen rows, thirty enumerated
  `-our` words, thirteen `-og`, eleven `-re`, and a noise list of about sixty — with no
  upstream to inherit from, and every addition a two-place edit the coupling test
  enforces. This is the cost the dictionary in Option 3 would have avoided.
- **`SKILL.md`'s table format is load-bearing.** The coupling test parses it, so
  reformatting the table or moving it breaks the suite — alongside `[tool.autohooks]` and
  the workflow's matrix paths, which were already.
- **Discovery inherits `.gitignore`'s blind spot.** Honouring it is what keeps
  `node_modules` out, and it also means a tree whose content is ignored sweeps almost
  nothing. Reading zero files is now an error rather than a clean result, but a tree that
  yields ten of seven thousand files is not, and only the header's file count says so.
- **The skill now depends on `python3` being present**, which — unlike `rg`, which the
  harness ships — is not guaranteed on a consumer's machine. `scan.py` states its floor
  and refuses to run below it rather than dying with a syntax error, but a machine with no
  `python3` at all cannot run this skill.
- [ADR 023][] narrows the "reports rather than edits" clause: a shipped tool may write what
  it wholly owns — a generated index, a field with one right value given the command, its
  own template, text the agent passed it — and never a sentence the agent wrote. The other
  two clauses stand as written.
- **A sweep is slower than nine `rg` processes**, at roughly 28,000 lines a second in pure
  Python: seconds for an ordinary repository, minutes for a very large monorepo. The
  report is capped per row so its size stays bounded whatever the tree.

## Revisit watch

- 2026-09-02: [ADR 022][] shipped tooling with `writing-adrs`. Met, and the decision stands:
  its drift test couples a template and field names, a shape `nz-english`'s table test
  does not share, so there is still nothing common to lift. The condition stays live for
  the next skill.

[#769]: https://github.com/vale-cli/vale/issues/769
[#884]: https://github.com/vale-cli/vale/issues/884
[#1125]: https://github.com/vale-cli/vale/issues/1125
[ADR 005]: 005-mirror-declared-tooling-as-pr-checks.md
[ADR 006]: 006-validate-the-declaration-to-catch-mirror-drift.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[ADR 023]: 023-let-a-shipped-tool-write-what-it-wholly-owns.md
[`nz-english`]: ../../skills/nz-english/SKILL.md
[`pr.yml`]: ../../.github/workflows/pr.yml
[`scan.py`]: ../../skills/nz-english/scan.py
[`table.py`]: ../../skills/nz-english/table.py
[Vale]: https://vale.sh/
