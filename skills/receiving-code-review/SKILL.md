---
name: receiving-code-review
description: Use when responding to review feedback on a pull request, before making any of the changes
---

# Receiving Code Review

**REQUIRED SUB-SKILL:** Use `superpowers:receiving-code-review` for how to evaluate and answer feedback, then apply the conventions below, which cover the pull-request mechanics it leaves out.

## Additional Convention: Gather Every Thread First

Fetch all review comments before answering any of them:

```bash
gh api repos/{owner}/{repo}/pulls/{pr}/comments --paginate
```

`gh pr view --json reviews` returns review *bodies*, which are often empty — the substance is in the inline comments, which that field omits. Review batches also accumulate across sittings, so the newest review is rarely the whole ask. Enumerate the lot, then decide what the response is.

## Additional Convention: Answer Every Thread

Reply in the thread (`gh api .../pulls/{pr}/comments/{id}/replies`), one per comment, even where the reply is just "Applied." A thread with no reply reads as overlooked, and the reviewer cannot resolve it.

Each reply is a comment you authored, so it carries whatever signature your instructions require. Define that signature once and send every reply through it — written out per call site, it goes missing from all of them at once:

```bash
# Substitute the signature your own instructions require; this one is the author's
REPLY_FOOTER=$'\n\n🤖 _Generated with [Claude Code](https://claude.com/claude-code) — Claude <model>_'
PR=123
reply() {
  gh api -X POST "repos/{owner}/{repo}/pulls/$PR/comments/$1/replies" \
    -f body="$2$REPLY_FOOTER" --silent || echo "FAILED: comment $1"
}
```

`gh api` fills `{owner}` and `{repo}` from the checked-out repository but not the pull-request number, so that one is a shell variable. Check the exit code rather than reading the output: a helper that swallows a failed POST reproduces the whole-batch failure it exists to prevent.

Add a single PR comment on top only for what spans threads or exceeds what was asked: findings you made beyond the review, decisions the reviewer must weigh, and a map from comment to commit.

## Additional Convention: Sweep for Stale References

Answering a review deletes files, renames symbols, and moves documentation. Before declaring the response done, search the repo **and the PR body** for references to anything the response removed or renamed. The PR body is the one nothing else checks — it is written once and cited afterwards, so it holds the freshest-looking stale reference in the whole change.

## Additional Convention: Review-Driven Decisions Earn an ADR

Where a review question is answered by a decision rather than an edit — a constraint accepted, an option rejected, a trade-off taken — record it via `phx:writing-adrs` in the same response. A reviewer's question is evidence the reasoning was not discoverable; a reply is read once, an ADR is found by the next person to ask.
