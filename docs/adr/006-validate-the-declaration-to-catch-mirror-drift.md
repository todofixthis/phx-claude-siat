---
status: Accepted
date: 2026-07-16
tags: [autohooks, ci, drift, github-actions, pull-requests, pyproject, python, skills, tomllib, tooling, validation]
summary: Catch mirror drift by having CI check each skill's declaration against the workflow — failing the build when a declared tool is never run — rather than making the declaration executable and retiring the mirror.
---

# 006: Validate the declaration to catch mirror drift

## Context

[ADR 005][] made CI run the tooling each skill declares, and left the mirror held by hand:
someone reads `[tool.autohooks]` and writes the matching job. It deferred what happens when
the two fall out of step.

They fall out of step in two ways, neither of which announces itself:

- A skill ships tooling and no job gates it at all.
- A gated skill's declaration grows a tool its job never runs — `mypy` added to
  `skills/creative-commits`, CI still quietly running only `ruff`, `black`, and `pytest`.

Both are the pathology ADR 005 was written against, one layer up: a declaration nobody
executes, decaying unnoticed. So is ADR 005's own standing rule — that a skill gaining
tooling gains matching checks — which is prose, and binds only a reader who finds it.

The force is that this repo has already lost this bet once, and recently. The inert
`[tool.autohooks]` block sat unexecuted long enough that `black` had never run against the
code it nominally governed; enforcing it reformatted both files on first contact. A rule
that lives only in a document is the thing that failed, and a document is what ADR 005
added.

## Options

### Option 1: Do nothing

Leave the mirror hand-held, and the rule in prose.

**Pros:** Nothing to build or maintain.

**Cons:** Drift is silent by construction — the failure is that no one is told.

**Risks:** A skill's tooling and its gate diverge, and the first thing to notice is a fault
in `main` that a declared tool would have caught.

### Option 2: Have CI check the declaration against the workflow (Accepted)

Extend [`validate_manifests.py`][] — already run by CI and by [`releasing`][] — to read each
skill's `[tool.autohooks]` with `tomllib` and fail when the workflow never names a declared
tool, or when a skill shipping tooling is not referenced at all.

**Pros:** A few dozen lines in a script that already loops the skills and reads the
workflow. Runs locally as readily as in CI, and needs no dependency the repo lacks.

**Cons:** Reads one declaration shape; tooling declared another way is invisible to it. The
mirror still exists and must still be written by hand — this reports drift rather than
preventing it.

**Risks:** A name matched loosely enough to pass on a coincidence.

### Option 3: Make the declaration executable and retire the mirror

Have CI run the declaration itself, so there is no second copy to keep in step.

**Pros:** Drift becomes unrepresentable rather than merely detected — the strictly better
end state.

**Cons:** Nothing here can execute it. [autohooks][] is the obvious runner and is already a
dev dependency, but its CLI offers only `activate`, `check`, and `plugins` — `check`
inspects the installed hook, it does not run the tools. Its plugins run from that hook over
*staged* files; CI stages nothing, so there is no runner to invoke and one would have to be
written. Generating the workflow from the declaration is no escape either: the generated
file is still committed and reviewed, so it is still a mirror — one that would want
Option 2's check to prove it current.

**Risks:** A runner or a tool-to-invocation schema, designed against a single package, so
its generality would be guesswork.

## Decision

Adopt Option 2. Detection is most of Option 3's value for a small fraction of its cost, and
the cost is what settles this — a few dozen lines against a subsystem, to serve one package.
`tomllib` is standard library and the declaration is a flat list of dotted strings, so the
reading is nearly free.

Option 3 is refused on timing, not merit. A schema wants more than one example to be
designed against; with a single package it would encode guesses about tools nobody has
adopted yet. Revisit at the second package with tooling — the first point the mapping has
anything real to answer to.

Option 1 loses on this repo's evidence rather than on principle. Trusting prose is the
specific bet already lost here, and it would be a strange ADR that answered a rotted
declaration with another declaration and hoped for a different result. That reasoning
applies reflexively, and is why ADR 005's standing rule becomes a thing CI asserts rather
than a thing an agent is trusted to have read.

## Consequences

- Adding a tool to a skill's declaration without gating it fails the build. `[tool.autohooks]`
  is now load-bearing: it decides what CI must run, so editing it changes the build contract.
- The tool name is matched as a substring of the whole workflow, not against that skill's
  own job — so a name appearing anywhere satisfies it, including in a comment, and at a
  second package one skill's job would satisfy another skill's declaration. Scoping the
  match needs the workflow parsed as YAML, which the repo has no dependency for. Both
  halves are substring tests and share that blindness: this proves a name is present, never
  that a job runs it. It catches the drift people actually commit, not an adversary.
- A tool in `dev` dependencies but absent from `[tool.autohooks]` draws no signal. That
  follows from ADR 005 making the declaration the specification: an undeclared tool is, by
  that definition, not yet required. The declaration can therefore under-state what a skill
  really uses, and nothing detects that.
- Skills shipping a `package.json` keep the ungated-skill check only; there is no equivalent
  declaration to read. A JavaScript skill reopens this decision rather than extending it.
- `validate_manifests.py` now needs `tomllib` — standard library from Python 3.11, run on
  the runner's system `python3` with no `setup-python` step. A runner image older than 3.11
  breaks the `manifests` job.

[ADR 005]: 005-mirror-declared-tooling-as-pr-checks.md
[autohooks]: https://github.com/greenbone/autohooks
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
[`validate_manifests.py`]: ../../scripts/ci/validate_manifests.py
