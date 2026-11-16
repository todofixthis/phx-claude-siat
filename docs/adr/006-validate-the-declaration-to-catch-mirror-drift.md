---
status: Accepted
date: 2026-07-16
scope: [.github/workflows/pr.yml, scripts/ci/validate_manifests.py]
summary: Catch mirror drift by having CI check each skill's declaration against the workflow — failing the build when a declared tool is never run — rather than making the declaration executable and retiring the mirror.
revisit-when: A skill ships a package.json rather than a pyproject.toml.
---

# 006: Validate the declaration to catch mirror drift

## Context

[ADR 005][] made CI run the tooling each skill declares, but left a person to keep the
mirror in step: someone reads `[tool.autohooks]` and writes the matching job. ADR 005
deferred what happens when the declaration and the job get out of step.

They get out of step in two ways, and neither reports itself:

- A skill ships tooling, and no job gates it at all.
- A gated skill's declaration gains a tool that its job never runs. For example, someone
  adds `mypy` to `skills/creative-commits`, and CI goes on running only `ruff`, `black`,
  and `pytest` without any warning.

Both repeat the fault ADR 005 was written against, one layer up: a declaration that
nothing runs, decaying unnoticed. ADR 005's own standing rule, that a skill gaining
tooling gains matching checks, has the same fault. It is prose, and it binds only a reader
who finds it.

The force is that this repo has already lost this bet once, recently. The inert
`[tool.autohooks]` block went unrun for so long that `black` had never run against the code
it supposedly governed. Enforcing `black` reformatted both files the first time. A rule
that lives only in a document is what failed, and a document is what ADR 005 added.

## Options

### Option 1: Do nothing

Leave a person keeping the mirror in step, and the rule in prose.

**Pros:** Nothing to build or maintain.

**Cons:** Nothing reports drift, by design. The failure is that nobody is told.

**Risks:** A skill's tooling and its gate diverge, and the first sign is a fault on `main`
that a declared tool would have caught.

### Option 2: Have CI check the declaration against the workflow (Accepted)

Extend [`validate_manifests.py`][], which CI and [`releasing`][] already run. It reads each
skill's `[tool.autohooks]` with `tomllib`, and fails when the workflow never names a
declared tool or never mentions a skill that ships tooling.

**Pros:** Cheap to build and cheaper to maintain. It adds a few dozen lines to a script
that already loops over the skills and reads the workflow. It needs no dependency the repo
lacks, and it runs locally as easily as in CI.

**Cons:** It reads one declaration format, so it can't see tooling declared any other way.
The mirror still exists, and a person still writes it by hand. The check reports drift
but doesn't prevent it.

**Risks:** A name match loose enough to pass by coincidence.

### Option 3: Make the declaration executable and retire the mirror

Have CI run the declaration itself, so there is no second copy to keep in step.

**Pros:** Drift becomes impossible, not merely detected. This is the better end state.

**Cons:** Nothing here can run the declaration. [autohooks][] is the obvious runner and is
already a dev dependency, but its CLI offers only `activate`, `check`, and `plugins`.
`check` inspects the installed hook and doesn't run the tools. Its plugins run from that
hook over *staged* files. CI stages nothing, so there is no runner to call, and someone
would have to write one. Generating the workflow from the declaration doesn't help either.
The generated file is still committed and reviewed, so it is still a mirror, and Option 2's
check would be needed to prove it current.

**Risks:** A runner or a schema mapping tools to commands, designed against one package, so
any generality in it would be a guess.

## Decision

Adopt Option 2. Detection gives most of Option 3's value at a small fraction of its cost,
and cost settles this: a few dozen lines, against a whole subsystem, to serve one package.
`tomllib` is in the standard library, and the declaration is a flat list of dotted strings,
so reading it costs almost nothing.

We refuse Option 3 on timing, not merit. A schema needs more than one example to be
designed against. With one package, it would encode guesses about tools nobody has adopted
yet. ~~Revisit at the second package with tooling — the first point the mapping
has anything real to answer to.~~ ADR 017 used up that trigger. It reached the second
package and generalised the mirror into a matrix instead of making the declaration
executable. The `package.json` half of the trigger is still live.

Option 1 loses on this repo's evidence, not on principle. Trusting prose is the exact bet
this repo already lost. It would be a strange ADR that answered a decayed declaration with
another declaration and expected a different result. The same reasoning applies to ADR
005's standing rule, which is why CI now asserts it instead of trusting an agent to have
read it.

## Consequences

- Adding a tool to a skill's declaration without gating it fails the build.
  `[tool.autohooks]` now matters: it decides what CI must run, so editing it changes the
  build contract.
- The check matches the tool name as a substring of the whole workflow, not against that
  skill's own job. A name anywhere satisfies it, even in a comment. Once there is a second
  package, one skill's job would satisfy another skill's declaration. Scoping the match
  needs the workflow parsed as YAML, and the repo has no dependency for that. Both halves
  of the check are substring tests and share that weakness. The check proves a name is
  present, never that a job runs it. It catches the drift people actually commit, not
  deliberate evasion.
- A tool in `dev` dependencies but missing from `[tool.autohooks]` raises nothing. That
  follows from ADR 005 making the declaration the specification. By that definition, an
  undeclared tool isn't yet required. So the declaration can list less than a skill really
  uses, and nothing detects the gap.
- Skills that ship a `package.json` get only the ungated-skill check, because they have no
  equivalent declaration to read. A JavaScript skill reopens this decision instead of
  extending it.
- `validate_manifests.py` now needs `tomllib`, which is in the standard library from
  Python 3.11. The script runs on the runner's system `python3` with no `setup-python`
  step, so a runner image older than 3.11 breaks the `manifests` job.

[ADR 005]: 005-mirror-declared-tooling-as-pr-checks.md
[autohooks]: https://github.com/greenbone/autohooks
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
