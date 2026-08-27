---
name: writing-release-notes
description: Use when preparing a release and you need release notes or a changelog entry for a new version.
---

# Writing Release Notes

Investigate *what* changed and *why* across a release range, then produce grouped,
audience-checked release notes plus an advisory semver level. **Your only deliverable
is the notes text and the recommended level** — writing them to a `CHANGELOG.md`,
publishing a GitHub Release, choosing the version number, and tagging are the caller's
job, not yours.

**Announce at start:** "I'm using the writing-release-notes skill to draft the release notes."

## Arguments

All optional:

- **`base`** — the comparison base: any identifier `git rev-parse` accepts (a tag,
  commit, or branch). The range is `<base>..HEAD`. Omit only for a first release.
- **`model`** — model for the gather subagents; default the cheapest capable model
  (e.g. Haiku).
- **`path`** — restrict the range, diff, and PR discovery to a subtree (monorepos).

## Procedure

### 1. Resolve the range

With a `base`, it MUST satisfy both `git rev-parse --verify <base>` and
`git merge-base --is-ancestor <base> HEAD`. If either fails, **stop and report the
error** — do not guess another base. The range is `<base>..HEAD` (scoped by `path`).
Without a `base`, this is a first release: review the full history. State the resolved
range before continuing.

### 2. Gather (parallel subagents on the cheap `model`)

Dispatch three subagents, each returning a structured summary. The three gathers are
independent, which is what earns the fan-out; the cheap `model` only chooses what runs
it, and keeps the context each gather reads out of this session:

- **What:** read `git diff --stat <range>` to map changed areas, then read full diffs
  per area in bounded chunks — fan out per area if the diffstat is large, so the cheap
  model's context isn't exceeded. Summarise by area.
- **Why:** parse `#NNN` references from `git log <range> --format=%s%n%b` (squash
  subjects `(#123)`, merge commits `Merge pull request #123`, body trailers like
  `Closes #45`); de-duplicate, then `gh pr view <N>` / `gh issue view <N>`. **Recurse**
  into `#NNN` references found in the fetched PR/issue bodies (visited set, bounded
  depth) — a PR often cites an issue no commit mentions. **Beware cross-repo refs:**
  dependency-bump PRs cite the *upstream* project's numbers; only attribute references
  that belong to this repo.
- **Significant-but-uncovered:** read commit message bodies for notable changes the
  diff and PR/issue summaries don't explain.

A pull request describes the *work*, not the released state, so its body routinely
recounts defects the same pull request introduced and fixed. Treat everything a PR or
commit body calls a bug as a candidate whose provenance is unestablished until gate 0
settles it against the base.

Normalise non-English source material to the notes' language.

### 3. Sense-check

Reconcile the three summaries yourself. Resolve contradictions and investigate
anything that looks off before trusting it. Don't silently drop a change a gather
subagent surfaced; if you reclassify or exclude one, record why, and when unsure keep
it. Err toward inclusion.

### 4. Draft

**Classify every entry by audience first: user-facing or maintainer-facing.**
User-facing changes affect someone *consuming* the project (installing it, calling its
API, invoking its skills/commands). Maintainer-facing changes affect someone
*contributing to* the project (its build, tests, contributor workflow, internal
tooling, or repo-local dev-environment setup) without changing what a consumer
installs or calls. A change touching both gets one entry per affected audience — don't
force a single framing. When genuinely unclear which audience a change belongs to,
default to user-facing (the more visible, harder-to-miss placement).

**Write for a human reader, whichever audience the entry is in.** Agents read release
notes too and disambiguate better than people do, so writing for the person is what makes
the notes serve both. The trap is person rather than vocabulary: in a project whose
product is invoked *through* a coding agent, "you" slides onto whoever performs each step,
and the reader is told they used to type commands an agent typed. Address the reader for
what is theirs — their machine, their repository, their upgrade — and name the agent as
the actor everywhere it acts. Where a detail exists only so an agent can execute the step,
it belongs in the skill rather than the notes.

Write to the template below: high-level, grouped logically within each audience. Flag
security-sensitive or embargoed material (CVE details, undisclosed advisories) for
human decision rather than publishing it unreviewed.

**Three gates decide what reaches the reader.** Gate 0 decides whether an entry is true;
gates 1 and 2 decide whether it earns its length, which is what gets notes skimmed or
skipped. Put every candidate entry through all three, in order:

0. **Was the reader ever exposed to this?** A defect introduced *and* fixed inside the
   range never shipped, so no released version carries it and no reader can have met it.
   It is not a fix, and an entry describing it sends people to audit work they never did.
   This gate governs every `Fixed` entry and every claim that something used to be
   broken; `Added` and `Changed` entries do not pass through it.

   Establish it from the base, not from the story: **read** the base's copy of the file —
   `git show <base>:<path>` — and satisfy yourself that what you read carries the defect.
   A file that exists is not a file that is broken, and stopping at "the command returned
   something" is the same mistake as trusting a link because it returned 200.

   Two results are not absence. Where the file was **renamed** inside the range, `git
   show` fails on its new name; recover the old one with
   `git log --follow --name-status --diff-filter=R <range> -- <path>` before concluding it
   was absent. Where the path genuinely did not exist at the base, `git show` exits
   non-zero, and here that exit **is the answer rather than an error to stop on**: the
   range built the thing, so the entry belongs under `Added` where the machinery is
   something a reader invokes, and nowhere at all where it is not.

   This is the one gate a PR body cannot answer, since a PR body records the work rather
   than the released state.
1. **Does this belong in a changelog at all?** The reader wants what changed for them
   and what to do about it. Refactors nobody outside can observe, dead code removed,
   rewordings that changed no behaviour, and caveats the runtime environment already
   precludes all fail this gate — drop them.
2. **Is it already explained in full elsewhere?** Where a decision record, issue, or
   doc sets out the reasoning, give the change in a sentence or two and link there
   instead of restating the argument.

These gates decide *publication*, not investigation: step 3's "err toward inclusion"
still governs the sense-check, so nothing is cut before it is understood. **Gates 1 and 2**
cannot drop a breaking change or trim its migration steps, and neither licenses cutting an
entry for being awkward to explain — gate 1 turns on the reader's interest, not the
writer's convenience. Gate 0 is not in that exemption and outranks it: a break the range
introduced and repaired before releasing broke nobody, whatever a PR body calls it.

**Pin every link in the notes to a commit or a tag, never a branch** — migration steps
and gate 2's links-out alike, since all of them freeze when the changelog does. A
`…/blob/main/…` link is wrong at both moments it is read: during review the release has
not merged, so the branch still serves the pre-change file, and afterwards the branch
moves on while the entry does not.

Two things to check, because a link that loads is not a link that is right. **Read what it
serves** — `git show <sha>:<path>` locally reads the same bytes — since the wrong file
behind a working URL is the harder error to spot. And **pick a ref that survives the
merge**: a commit on the release branch is durable where the project merges with a merge
commit, and gone where it squashes or rebases, so in a squashing project link the tag of
an already-published release, or add the link once the release commit exists.

**Breaking changes — flag, don't dismiss.** "Breaking" is broader than runtime API
breaks, and applies independently within *each* audience. The test: **if the consumer
or contributor does nothing differently, does anything — not just compile-time or
runtime behaviour — end up broken, stale, or silently out of sync?** That covers
changed or removed public API or behaviour; **type-surface** changes (altered public
signatures, or removed base classes/protocols that typed consumers may depend on);
**build- or contributor-workflow** changes (renamed dependency groups, changed
install/build/test commands, a new opt-in step like a hook that must be activated or
its output silently goes stale); and **dropped runtime or version support**. When a
change is plausibly breaking under this test, or a commit/PR/issue signals it — even if
you can argue it still works at runtime — put it under that audience's **Breaking
changes** with migration steps and let the human decide. Do not reason a flagged break
out of the notes.

### 5. Audience-surrogate review

Dispatch one subagent **on the main model** (a reasoning task, not a cheap one) per
**non-empty** audience block from step 4, each reading only that block and critiquing
it for clarity, gaps, and jargon from that audience's perspective:

- **User block reviewer:** infer the specific user audience from the README / package
  manifest / repo description; default to "a downstream developer consuming this
  project"; ask if genuinely ambiguous.
- **Maintainer block reviewer:** read as "a contributor to this project."

Each reviewer must also check **breaking-change completeness** for its block: would
someone in that audience be caught out by a change that isn't under that block's
Breaking changes — an altered contract, type surface, build/test/contributor workflow,
or dropped version support? Anything missing, under-called, or misclassified into the
wrong audience gets flagged.

Each reviewer also **checks the block's claims against the thing each describes** — the
code at both ends of the range, the workflow file, the live setting via `gh` — rather than
against the draft's account of them. Reading only that block keeps the other audience's
prose away from the reviewer; it does not deny it the repository, which it needs for this.
Where a claim rests on prior behaviour, hand it the pre-image (`git show <base>:<path>`):
the diff shows what a change became, never what it displaced, and prior behaviour is the
half no gather subagent saw either.

> *"the validator now rejects a manifest of the wrong shape"* — true, and the entry implies
> it used to accept one. It crashed. A reader who upgrades to fix silent acceptance was
> never exposed to it.

Each reviewer also re-runs gate 0 over its block: for every `Fixed` entry, the defect must
be findable in the pre-image, and an entry whose defect is not there is reporting work the
range did to itself. This is the failure a draft is most likely to reach the reviewer
carrying, because the gather subagents read pull requests, which describe exactly that
work.

Where a reviewer's budget runs out, verification outranks the rest: an unclear entry costs
a reader a minute, a false one sends them the wrong way.

Address the feedback from both reviewers before continuing.

### 6. Quality pass

Remove repetition, regroup related items, and tighten without losing clarity. **Re-apply
step 4's three gates over the reviewed draft, and re-check every link it gained** — a
reviewer asking for a migration step is how an unpinned link enters after the only check
has run. Surrogate reviewers optimise for completeness and reliably ask for more, so
the draft reaches this step longer than it
left step 4, and some of what they added earns its place while some does not. Then,
**only if the project uses NZ English** (per its stated convention or agent
instructions), run `phx:nz-english`. Other locales — including US English — get no
spelling pass.

### 7. Recommend the semver level (advisory)

Major for breaking changes, minor for backwards-compatible additions, patch for fixes
only — **except under `0.y.z`, where breaking changes are a minor bump**. For a first
release, label it the initial release and give no recommendation. Recommend the
*level* only; never compute or write the version number.

### 8. Output

Present the finished notes and the recommended level. Do not persist them: writing to
a changelog, choosing a version heading, publishing a Release, and tagging are the
caller's responsibility.

## Template

Two top-level audience blocks, **each emitted only when it has content**: a heading for
users (e.g. "For \<project\> users") and one for maintainers (e.g. "For contributors").
Within each block, Keep-a-Changelog sections, emitted only when non-empty: **Added,
Changed, Deprecated, Removed, Fixed, Security.** Above those, a dedicated **Breaking
changes** block listing that audience's breaking changes with migration steps. (This
block is a deliberate, opinionated deviation from Keep-a-Changelog's `**breaking**`
prefix.) A single-audience release omits the other block entirely rather than emitting
it empty. Entries are high-level and grouped — never a per-commit dump. The caller adds
any version heading.

## Edge cases

- **First release (no `base`):** review the full history; initial-release framing; no
  semver recommendation.
- **`gh` unavailable or unauthenticated:** likely unintentional — **stop and tell the
  human**, rather than silently degrading coverage by skipping the PR/issue gather.
  Proceed without it only if the human explicitly confirms.
- **Non-GitHub remote:** there is nothing for `gh` to fetch — skip the PR/issue gather,
  rely on the diff and commit bodies, and **state what you skipped** in the output.
- **`base` unresolvable or not an ancestor of `HEAD`:** stop with an error.
- **Empty range (no changes since `base`):** report that there is nothing to release
  and stop.
