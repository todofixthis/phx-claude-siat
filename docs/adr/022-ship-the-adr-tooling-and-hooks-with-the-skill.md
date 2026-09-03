---
status: Accepted
date: 2026-09-02
scope: [.claude-plugin/, .githooks/pre-commit, .github/workflows/pr.yml, hooks/, skills/writing-adrs/]
summary: Ship the ADR generator, index and scope checks as a stdlib tool beside the writing-adrs skill, wired to sessions by hooks the phx plugin declares — not a standalone plugin, and not hooks declared in the skill's frontmatter alone.
revisit-when: A consumer needs the skills without the hooks and Claude Code offers no per-hook opt-out, or a hook needs more than a POSIX shell and python3 to run, or a hook event's median cost is measured above 100 ms on this repository's corpus.
---

# 022: Ship the ADR tooling and hooks with the skill

## Context

[`writing-adrs`][] describes a contract — frontmatter fields, a generated `INDEX.md`, a
reverse lookup from a path to the decisions binding it — and tells a consumer to port the
reference implementation, [`adr.py`][] with its parser and tests, stripping the
[`pre-commit`][] wiring that runs it here. Every consumer that wants the checks builds them
again, and one that does not gets a skill whose rules nothing enforces; the reverse lookup,
the half of [ADR 013][] that reaches a reader who did not go looking, runs on no consumer
at all.

ADR 013 accepted two tensions on that footing and named the remedy for both as a system
"with its own hooks, tools and state" rather than a different keying. [ADR 021][] weighed
converting the skill into a standalone plugin with session hooks and deferred it, there
being "no hook infrastructure to build on" and no use case beyond one. The maintainer has
now asked for that system: an agent with the plugin installed should get the index, the
checks and the delivery of decisions without the consumer setting anything up beyond the
first ADR.

Claude Code plugins ship [`hooks/hooks.json`][hooks], with `${CLAUDE_PLUGIN_ROOT}` and
`${CLAUDE_PROJECT_DIR}` expanded in hook commands; a [skill body][skills] may use
`${CLAUDE_SKILL_DIR}`, substituted in its content and in `allowed-tools`, to reach a file
bundled beside it — the harness's own form of the skill-relative resolution [ADR 003][]
chose. Both verified against the references on 2026-09-02, though, as Consequences records,
a grant did not pre-approve the command when measured.

## Options

Options 2 to 4 all move the generator into shipped code and cost the same port. That is set
aside; what ranks them is where the hooks are declared, and so whom they reach.

### Option 1: Do nothing

Keep the generator, the pre-commit hook and the CI job as this repository's, and keep
telling consumers to port them.

**Pros:** Nothing to build, and this repository's checks stay where its other checks are.
**Cons:** The skill's rules bind only where someone rebuilt the tooling.
**Risks:** Each port drifts from the contract, and the skill has no way to tell.

### Option 2: A stdlib tool beside the skill, hooks declared by the plugin (Accepted)

`skills/writing-adrs/` gains the tool; the `phx` plugin's `hooks/hooks.json` wires it to
`SessionStart`, `SubagentStart`, `PreToolUse`, `PostToolBatch` and `Stop`. Each hook line
exits before starting Python unless the project's `docs/adr/INDEX.md` opens with the tool's
own header, so a repository without a managed corpus pays one shell test per event.

**Pros:** Reaches an agent that never invoked the skill, which is the reader ADR 013 wants.
No install step, as [ADR 017][] requires of shipped tooling.
**Cons:** Every `phx` user carries the hooks, and Claude Code offers no per-hook opt-out:
a consumer who wants the skills without them has `disableAllHooks` or uninstall. In a
managed repository each hooked event starts Python once, per subagent; the budget is
100 ms on this repository's corpus. Measured 2026-09-03 over twenty `PreToolUse` events on
this container: median 74 ms, worst 111 ms — the budget is met at the median and missed at
the worst. The median divides into 2 ms for the shell gate, 15 ms of interpreter start,
24 ms importing the modules, 5 ms of the handler's own work over 24 decisions, and the
remaining 28 ms in process spawning and container jitter. The corpus is the smallest term,
so the cost tracks the interpreter rather than the number of decisions, and a median over
budget would mean something else had changed — which is why it is a revisit condition.
**Risks:** A hook that misbehaves does so in every consumer's session at once, with no
version pin between them and this repository's `main`.

#### Sub-question: how a consumer's CI reaches the tool

The plugin cache is on no CI runner. The skill gains a `pyproject.toml` for its dev
toolchain, as `nz-english` has, carrying a `phx-adr` entry point and a build backend, so a
consumer runs `uvx --from 'git+https://github.com/todofixthis/phx-claude-siat@<tag>#subdirectory=skills/writing-adrs' phx-adr check`.
The tool itself stays standard library; the backend packages it and installs nothing into
it. A session tracks `main` ([ADR 010][]) while CI pins a tag, so the two can run different
versions of the tool until the consumer bumps the tag.

### Option 3: A standalone plugin

ADR 021's Option 3: split `writing-adrs` into its own plugin with its own hooks.

**Pros:** A consumer who wants the skills without the hooks can choose, which is the one
thing Option 2 cannot give them.
**Cons:** [ADR 012][] caps the catalogue at one entry and makes a second an architectural
change reopening versioning and release flow.
**Risks:** Two release trains for one skill's prose and its code, which is the drift ADR 017
holds together with a test.

### Option 4: Hooks declared in the skill's frontmatter only

Claude Code registers a skill's frontmatter hooks when the skill is invoked and keeps them
for the session.

**Pros:** No plugin-level configuration; a repository sees the hooks only after the skill
has been used in the session.
**Cons:** An agent editing a bound file in a session that never invoked the skill receives
nothing. That agent is the whole point.
**Risks:** Delivery that depends on the skill having fired reads as delivery, and is not.

## Decision

Option 2. The consumer-facing gap is reach, and only plugin-declared hooks reach an agent
that has not invoked the skill. ADR 012 rules out Option 3, and the gate answers its cost
argument; what it cannot answer is choice, which is why the lack of a per-hook opt-out is
the revisit condition. Option 4 fails the reader the system is for.

This repository deletes `scripts/adr/` and consumes the shipped tool from its pre-commit
hook and its `adr` job, so it is the first consumer rather than a second implementation.

ADR 017's trigger — a third skill ships tooling, so the per-skill coupling assertions want
generalising — fires here and is answered without generalising: this skill's drift test
couples the Format template and the field names between `SKILL.md` and the tool, a shape
`nz-english`'s table test does not share, so there is still nothing common to lift. That
arm is spent from 017's `revisit-when`.

## Consequences

- `pr.yml`'s `python` matrix gains `skills/writing-adrs`, the check [ADR 005][] requires of
  a skill that gains tooling, and the `changes` job's `case` arm that selects the matrix
  names it too — a leg alone never runs, and the manifest check's substring test would not
  notice. One step runs the `uvx` recipe against the checkout so it cannot rot unnoticed.
- `hooks/` at the plugin root is a new kind of shipped artefact.
- Hook commands run under a POSIX shell and need `python3` on `PATH`; where it is missing
  the `SessionStart` line says so in context and every other entry exits silently. Windows
  without Git Bash is out of scope.
- Deleting `scripts/adr/` dangles the `scope` entries ADR 013 and [ADR 019][] carry for it,
  and every reference link to `generate_index.py`; both are corrected in the same change,
  the links retargeted to the tool's new path.
- What the tool may write is [ADR 023][]'s question; how it finds the repository is
  [ADR 024][]'s; what the hooks inject and when they nag are ADR 025's and 026's.
- `AGENTS.md`'s test-run line gains the skill's pytest leg, and the README replaces its
  generator instructions with the tool's and the CI recipe.
- The skill carries no `allowed-tools` grant. Measured 2026-09-03 in headless sessions: a
  skill carrying one is denied at invocation, and with the invocation allowed the grant
  still did not pre-approve the `adr.py` command under either rule form. Each command
  prompts as `nz-english`'s does; a backlog item holds the retry.

[ADR 003]: 003-locate-skill-assets-relative-to-skill-directory.md
[ADR 005]: 005-mirror-declared-tooling-as-pr-checks.md
[ADR 010]: 010-pin-the-marketplace-entry-to-main.md
[ADR 012]: 012-advertise-one-plugin-per-catalogue.md
[ADR 013]: 013-scope-adrs-by-the-paths-they-bind.md
[ADR 017]: 017-move-a-skills-deterministic-steps-into-shipped-code.md
[ADR 019]: 019-do-not-generate-path-scoped-rules-from-adr-frontmatter.md
[ADR 021]: 021-validate-adr-scope-on-every-pull-request.md
[ADR 023]: 023-let-a-shipped-tool-write-what-it-wholly-owns.md
[ADR 024]: 024-resolve-the-repository-root-from-the-path-in-hand.md
[ADR 025]: 025-deliver-binding-decisions-by-hook-at-first-touch.md
[ADR 026]: 026-report-findings-by-delta-from-a-session-baseline.md
[`adr.py`]: ../../skills/writing-adrs/adr.py
[hooks]: https://code.claude.com/docs/en/hooks
[`pre-commit`]: ../../.githooks/pre-commit
[skills]: https://code.claude.com/docs/en/skills
[`writing-adrs`]: ../../skills/writing-adrs/SKILL.md
