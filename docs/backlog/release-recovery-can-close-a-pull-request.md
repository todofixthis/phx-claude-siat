# The release recovery path can close a pull request instead of an issue

> Recorded 2026-08-28, found while writing [ADR 020][]. Never filed as a GitHub issue.

## What

[`releasing`][]'s `### If the run fails` section carries a by-hand recovery bullet:

> **Issues to close?** Rare here (notes cite ADRs). Close any `#NNN` the notes reference
> by hand with a link to the Release.

A `#NNN` reaching the notes is usually a **pull request**: [`phx:writing-release-notes`][]
parses them from commit subjects and merge commits, alongside body trailers such as
`Closes #45`, which do name issues. And `gh issue` resolves a pull-request number rather
than rejecting it:

```
$ gh issue view 37 --json number,title
{"number":37,"title":"Release 5.0.0"}
```

So a session following the bullet against an unmerged pull request would close it and
comment on it, then report the step done.

ADR 020 makes this likelier rather than rarer: deferred work no longer becomes an issue, so
a `#NNN` in the notes is now almost always a pull request.

## Why it is still worth doing

It has not bitten yet: the bullet is on the recovery path rather than the normal one, and
it only runs over references the notes carry — 5.0.0's carried none, the entries citing
ADRs. So it is latent, and latent is the argument for fixing it rather than against.

A recovery path runs when a release has already gone wrong, under someone working by hand
because the automation did not. That is the worst moment to hand out an instruction whose
failure is closing the wrong object and reporting success. The rarity that has kept it
harmless is also what stops anyone noticing it.

## Acceptance

- The bullet resolves each `#NNN` before acting, and skips anything that is a pull request,
  or says plainly that it must be checked by hand first.
- A test or stated check covers the resolution, since the failure is silent and the
  recovery path is exercised rarely.
- `phx:writing-release-notes` is untouched: it ships to consumers, and how they close
  references is theirs.

[ADR 020]: ../adr/020-track-deferred-work-in-the-repository.md
[`phx:writing-release-notes`]: ../../skills/writing-release-notes/SKILL.md
[`releasing`]: ../../.agents/skills/releasing/SKILL.md
