# Design: reference linking for the `writing-adrs` skill

## Problem

In `todofixthis/class-registry` PR #101, an agent used the `writing-adrs` skill to
generate ADRs that named GitHub issue #100 without linking to it, leaving developers
to hunt for the original context. The skill currently gives no guidance on linking
references, so this gap is unaddressed and will recur.

The goal: make the skill require links to references — GitHub issues/PRs, web pages,
and code symbols — without overloading the document with markup.

## Decision

Use **reference-style Markdown links** with definitions collected at the foot of the
ADR (the approach weighed and chosen during brainstorming over inline links and a
rendered References section). The prose carries only brackets; every target lives once
in a definition block at the bottom. This keeps prose clean, centralises targets for
auditing, and gives a reader of the bare Markdown an implicit reference list.

## Convention rules

These are the rules the skill will instruct the agent to follow.

- **What to link.** Every reference to something outside the ADR's own prose: GitHub
  issues/PRs, web pages, and code symbols (files, skills, functions, classes). If you
  name it as a source of context, link it.
- **Mechanism.** Reference-style Markdown links using the named/shortcut form, so the
  label *is* the anchor (`[#100]`, `` [`ClassRegistry`] ``). Definitions are collected
  in one block at the very bottom of the file, after Consequences.
- **First mention only.** Link the first occurrence of a given reference; later
  mentions stay plain — a code span for symbols, plain text for issues. This stops a
  repeated code symbol from peppering the document with links.
- **Symbols link to the file, not the line.** Use a relative repo path (e.g.
  `skills/writing-adrs/SKILL.md`). No line numbers and no commit SHAs — both go stale
  and are not worth keeping in sync.
- **Targets by type.** GitHub issue/PR → the full issue/PR URL; web page → its
  canonical URL; code symbol → the relative repo path to the defining file.
- **Order definitions alphabetically by label**, ignoring surrounding markup (so
  `` [`ClassRegistry`] `` sorts under C). Consistent with the repo-wide convention to
  alphabetise unordered collections, and avoids an ordering that looks arbitrary —
  ordering by type fails because the target name rarely reveals its type.

### Worked example

```markdown
Following [#100][], we adopted the registry pattern from [`ClassRegistry`][].
See the [PEP 8 naming guidance][] for the convention.

[#100]: https://github.com/todofixthis/class-registry/issues/100
[`ClassRegistry`]: src/class_registry/registry.py
[PEP 8 naming guidance]: https://peps.python.org/pep-0008/#naming-conventions
```

## Changes to SKILL.md

1. **New `## Linking references` section**, placed after `## Conventions`. It carries
   the convention rules above plus the worked example. Standalone rather than a bullet
   under Conventions, because it carries four sub-rules and an example.

2. **`## Format` template update.** Add a trailing comment in the skeleton showing the
   reference-definition block at the very bottom, after Consequences, so the structure
   is visible at a glance.

3. **Review section additions.** Reference-style links have one weak spot: a missing or
   mismatched definition renders as literal text rather than erroring. Add an explicit
   verification check to the conciseness pass (Pass 2):
   - Every reference label used has a matching definition.
   - Every definition is used — no orphans. Call out the specific hazard that an
     overly-aggressive conciseness pass removes a reference's last usage but leaves its
     definition behind.
   - Each target resolves: the issue/PR exists, the path exists, the URL is valid.

## Scope / non-goals

- No tooling or lint hook. This is skill-guidance only, enforced the same way as the
  skill's other conventions — by the agent, checked in the review passes.
- No changes to frontmatter, numbering, or supersession rules.

## Testing

Skill changes are verified by RED/GREEN subagent testing per `superpowers:writing-skills`,
honouring the repo's dogfooding constraint (the working tree must be live via
`--plugin-dir ./`, with `/reload-plugins` between runs). The RED control: an ADR
referencing a GitHub issue and a repeated code symbol, drafted without the new
guidance, should leave the issue unlinked. GREEN: with the guidance, the issue is
linked reference-style, the symbol is linked on first mention only, and definitions sit
alphabetically ordered at the foot of the file.
