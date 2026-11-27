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
control files by hand to prove those commands could fail, recognise about sixty documented
false positives in the output, and derive a right-end guard character for each rename it
verified. None of that is judgement, and every part of it has failed in practice:

- `rg … || echo "(clean)"` reported nine clean sweeps for searches that never ran, because
  `rg` exits 2 on error, not 1.
- In zsh, an unquoted expansion became one unrecognised flag, and a `path=` assignment
  wiped `$PATH`.
- A command with no trailing path blocked on an open pipe until someone killed it.
- A right-anchored pattern hid `cataloged` and `cataloging` for a month.

Each failure got more prose in answer, until two of the skill's five sections existed
largely to stop an agent typing a command wrongly. Nobody can verify that prose. Nothing
fails when it is wrong, and a clean report is what stops anyone looking again.

The general question is which parts of an LLM-run skill belong in the skill at all.
[ADR 005][] established that a skill gaining tooling gains a matching pull-request check
in the same change. [ADR 006][] declined to design a declaration schema against a single
example. This is the second example.

## Options

Options 2 and 3 both leave the substitution table in two places: `SKILL.md`'s Markdown for
a reader, and a machine-readable copy for the searcher. Both therefore need something that
holds the copies together. That cost is shared and does not rank them. What remains is
where each option's coverage stops, and what a consumer has to install.

### Option 1: Do nothing

Keep the searches in the skill's prose, and keep answering each failure with more prose.

**Pros:** No new code, no new dependency, no version bump. The skill stays one file.
**Cons:** The failures recur, because prose cannot make reliable what it asks of the
reader: retype nine commands exactly, every time. Each fix lengthens the skill, and length
is what gets a skill skimmed.
**Risks:** Every one of these failures is silent. A miss survives indefinitely, because
the search that would have found it reported clean.

### Option 2: Ship a stdlib tool with the skill (Accepted)

A [`scan.py`][] beside `SKILL.md`, standard library only, invoked as
`python3 <skilldir>/scan.py`. It **reports and never edits**. The substitution table
becomes data in [`table.py`][], and the patterns, the noise classification, and the guard
characters all derive from that data.

**Pros:** The hazards disappear by construction. There is no shell quoting, no missing
path, and no exit code to swallow. Discovery through `git ls-files -co --exclude-standard`
honours `.gitignore` without a rule of our own. The tool computes the guard character from
the table, so no reader has to derive it. About a quarter of the skill's prose goes, and
what remains is judgement.
**Cons:** The skill now needs `python3` and a bundled file, a breaking change to how it is
invoked. The table exists in two places, the skill's Markdown and the code, where it used
to exist in one.
**Risks:** A second copy of the table can drift. Three assertions in the bundled tests
answer that risk. Every row must find its word in a US-spelled control, the row counts
must match, and every literal in the skill's US column must exist in the code. Mutation
testing confirmed that each assertion fails for its own reason. It also confirmed that the
first does *not* catch a row added to neither side, and the second exists for that case.

#### What stays with the agent

Triage stays with the agent, and it is per occurrence, not per word: is a name this
repository's to change, or does something outside hold a copy of it? The agent also keeps
the rows that need reading instead of applying, the reading of the diff for conversions
that should not have happened, and the test suite's blind spots. The tool never edits a
file, because a rename is the thing the skill says kills you.

### Option 3: Adopt Vale

[Vale][] is a mature, MIT-licensed prose linter that understands markup, and the case for
it is real. Its `substitution` check is close to this skill's data model. It has regex
keys, an `ignorecase` flag, and an `exceptions:` list that is the documented-noise list as
a first-class concept. Because Vale understands markup, it tells a fenced code block from
prose, and a line-oriented regex cannot. And `Vale.Spelling` with a Hunspell dictionary
would catch US spellings that a seventeen-row table structurally cannot. This skill states
that weakness in its own words.

Vale *can* see the identifiers a repository defines, through Views with
`engine: tree-sitter` and an `expr` query, so the rejection is not a claim about
capability. Vale ships grammars for 27 languages and extracts only comments by default,
so identifiers need a query written per language. A language outside that set, such as
shell, YAML, TOML, Dockerfile, SQL, or [Kotlin][#1125], gets no query at all, because
there is no grammar to write one against. Upstream is not standing still. [#884][] asked
to lint more than comments and was closed in favour of [#769][], which was completed in
June 2025.

**Pros:** All of the above, plus a maintained upstream, a dictionary that reaches words no
enumerated table can, and no word list of ours to keep.
**Cons:** We would write and maintain a tree-sitter query per language for the identifier
half. A consumer must install a Go binary, set a `StylesPath`, and run `vale sync`. No
packaged en_NZ dictionary exists, and en_GB has to be hand-rolled. Vale does not honour
`.gitignore`, so inclusion is globs in `.vale.ini`. And the table would live in a third
place, not a second.
**Risks:** Vale does not report a language nobody wrote a query for as uncovered. That
language is simply absent from the results.

#### Sub-question: Vale for prose, the bundled tool for identifiers

The two are not exclusive. A hybrid answers the coverage objection outright. The bundled
tool still reaches every language, and Vale adds the dictionary and its awareness of prose
versus code on top. What remains is the install step, which the Decision weighs.

## Decision

Adopt Option 2, and treat it as the general rule. **A skill's deterministic steps move
into code that ships with the skill. That code needs no install step, and it reports rather
than edits. Wherever the skill's prose and the code encode the same thing, a test fails
when they drift.** The no-install clause is not decoration. It is what makes a skill
usable on first invocation in a fresh checkout.

That clause is comparative, not absolute, and this ADR should not pretend otherwise. A
machine with no `python3` cannot run this skill either. The difference is one of degree
and shape. `python3` is on most developer machines and needs no setup per repository.
Vale needs a Go binary *and* a `StylesPath` *and* a `vale sync` before the first run, and
someone must redo the last two in every checkout. A Vale advocate can fairly claim the
first half of that comparison, but not the second.

Vale loses on the *shape* of its silence, not on having any. Both options are silent about
what they do not cover. A US spelling outside the seventeen rows, or an `-our` word
outside the thirty enumerated, returns nothing from the bundled tool. That is the same
defect the Hunspell dictionary would have fixed. The difference is that the tool's silence
is per word. It is bounded, enumerated in a file, and inside a report that prints every
row, including the empty ones. A missing tree-sitter query instead hides a whole file
type, and nothing in the output says so. You can audit bounded silence. You cannot audit
unbounded silence.

Limit that claim to the word list, where it holds. Discovery's silence is not bounded.
Honouring `.gitignore` means an ignored subtree drops out with nothing but a file count to
show for it, and Vale's explicit globs are arguably louder there. The claim is that the
*table's* coverage is enumerable, not that the tool is silent about nothing.

The hybrid loses on the install step alone. The coverage argument does not touch the
install step, since the bundled tool would still reach every language underneath.

The three coupling assertions are *this* skill's realisation of the general rule, not part
of the rule. They exist because `nz-english` owns a Markdown table. A future skill with no
table has nothing to couple and will need its own answer. Generalising the assertions now
would be the premature schema that ADR 006 declined to design. Each skill that ships
tooling asks the question again.

ADR 006's revisit trigger, "A second skill ships tooling", fires here. This ADR answers it
by generalising the mirror, not by making the declaration executable: [`pr.yml`][]'s
`python` job becomes a matrix over the skill directories that ship a `pyproject.toml`.
That arm of the trigger is cut from ADR 006's `revisit-when` and struck through where
ADR 006's body sets it out. The other arm, a skill shipping a `package.json`, has not
fired and stays live. ADR 005 already requires the matching check in the same change, and
the matrix satisfies it.

## Consequences

- The skill is a breaking change for its callers, because it now requires `python3` and a
  file that ships beside it. Where the tool cannot run, the skill says to stop and
  escalate, not to improvise the searches back. The deleted commands encoded a guard and a
  noise list that a typed command will not.
- `[tool.autohooks]` in a second `pyproject.toml` is now load-bearing in the same way the
  first one is. The matrix values in `pr.yml` must stay full paths, because the manifest
  check looks for each skill directory as a plain substring of the workflow.
- A change to either skill that ships tooling now runs both matrix legs. That is cheap,
  and it keeps the path filter honest.
- The noise list is a maintained artefact, and only words that are already correct belong
  on it. `colorist` and `behaviorist` sit inside the skill's noise section and are *real*
  hits. An implementer who copied that section wholesale would ship the miss that the
  skill treats as the serious direction.
- **The `-og` blind spot closes, and it is the one place the tool is not a faithful port.**
  The hand-run searches were case-insensitive throughout, so their guard excluded a
  following `U` as well as a `u`. A camel-cased `dialogUrl` reached no search at all. The
  skill had to document that permanent miss and ask for a check by hand. Scoping the flag
  to the guard alone catches it. The cost is that the tool reports a SCREAMING_CASE
  `DIALOGUE`. That is over-reporting, the direction the skill prefers. The differential
  run against the nine commands agrees on every other match and diverges here by one,
  deliberately.
- A consumer's correctness no longer rests on tests they never run, because `--self-check`
  runs the patterns over the bundled controls. Its reach is narrower than it looks, and
  the skill says so. `--self-check` bypasses discovery, so it proves the patterns fire and
  says nothing about whether the sweep reached any files.
- **The word list is ours to maintain, permanently.** It holds seventeen rows, thirty
  enumerated `-our` words, thirteen `-og`, eleven `-re`, and a noise list of about sixty.
  There is no upstream to inherit from, and every addition is an edit in two places that
  the coupling test enforces. Option 3's dictionary would have avoided this cost.
- **`SKILL.md`'s table format is load-bearing.** The coupling test parses the table, so
  reformatting or moving it breaks the suite. `[tool.autohooks]` and the workflow's matrix
  paths were already load-bearing in the same way.
- **Discovery inherits `.gitignore`'s blind spot.** Honouring `.gitignore` keeps
  `node_modules` out, and it also means a tree whose content is ignored sweeps almost
  nothing. Reading zero files is now an error instead of a clean result. A tree that yields
  ten of seven thousand files is not an error, and only the header's file count shows it.
- **The skill now depends on `python3` being present.** Unlike `rg`, which the harness
  ships, `python3` is not guaranteed on a consumer's machine. `scan.py` states its minimum
  version and refuses to run below it instead of dying with a syntax error. But a machine
  with no `python3` at all cannot run this skill.
- [ADR 023][] narrows the "reports rather than edits" clause. A shipped tool may write what
  it wholly owns: a generated index, a field with one right value given the command, its
  own template, and text the agent passed it. It never writes a sentence the agent wrote.
  The other two clauses stand as written.
- [ADR 036][] supersedes ADR 023 and admits one more kind of write: an edit to a
  consumer's file that the agent specified verbatim and the tool reverses before it exits.
- **A sweep is slower than nine `rg` processes**, at about 28,000 lines a second in pure
  Python. That is seconds for an ordinary repository and minutes for a very large
  monorepo. The tool caps the report per row, so the report's size stays bounded whatever
  the tree.

## Revisit watch

- 2026-09-02: [ADR 022][] shipped tooling with `writing-adrs`. The condition was met, and
  the decision stands. ADR 022's drift test couples a template and field names, a shape
  that `nz-english`'s table test does not share, so there is still nothing common to lift.
  The condition stays live for the next skill.

[#769]: https://github.com/vale-cli/vale/issues/769
[#884]: https://github.com/vale-cli/vale/issues/884
[#1125]: https://github.com/vale-cli/vale/issues/1125
[ADR 005]: 005-mirror-declared-tooling-as-pr-checks.md
[ADR 006]: 006-validate-the-declaration-to-catch-mirror-drift.md
[ADR 022]: 022-ship-the-adr-tooling-and-hooks-with-the-skill.md
[ADR 023]: 023-let-a-shipped-tool-write-what-it-wholly-owns.md
[ADR 036]: 036-let-a-shipped-tool-make-an-edit-it-reverses.md
[`nz-english`]: ../../skills/nz-english/SKILL.md
[`pr.yml`]: ../../.github/workflows/pr.yml
[`scan.py`]: ../../skills/nz-english/scan.py
[`table.py`]: ../../skills/nz-english/table.py
[Vale]: https://vale.sh/
