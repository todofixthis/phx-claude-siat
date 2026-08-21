---
name: receiving-code-review
description: Use when responding to review feedback on a pull request, before making any of the changes
---

# Receiving Code Review

**REQUIRED SUB-SKILL:** Use `superpowers:receiving-code-review` for how to evaluate and answer feedback, then apply the conventions below, which cover the pull-request mechanics it leaves out.

## Additional Convention: Gather Every Thread First

Fetch all review comments before answering any of them:

```bash
PR=123
gh repo view --json nameWithOwner -q .nameWithOwner || exit 1
gh api "repos/{owner}/{repo}/pulls/$PR/comments" --paginate \
  --jq '.[] | select(.in_reply_to_id == null) | "\(.id)\t\(.path):\(.line // .original_line)\t\(.body)"' \
  || exit 1
```

**Read the repository name it prints before anything else.** `GH_REPO` silently outranks the
checked-out repo and a readable one answers 200, so every exit code passes while you read —
and then answer — a stranger's review. No later check saves you: by the time the tally below
runs, the replies are posted.

`gh` fills `{owner}`, `{repo}` and `{branch}` from the checked-out repository — or from
`GH_REPO`, which silently wins, so on a fork or with that set they may name a repository
the pull request is not on. It does not fill the pull-request number, which 404s if you
leave it as a placeholder. The `select` keeps
top-level comments only: the endpoint returns replies mixed in, and looping over the lot
means replying to replies, including your own from the last sitting.

`gh pr view --json reviews` returns review *bodies*, which are often empty — the substance is in the inline comments, which that field omits. Review batches also accumulate across sittings, so the newest review is rarely the whole ask. Enumerate the lot, then decide what the response is.

## Additional Convention: Answer Every Thread

Reply in the thread (`gh api .../pulls/$PR/comments/$ID/replies`), one per inline review
comment, even where the reply is just "Applied." A thread with no reply reads as
overlooked, and the reviewer cannot resolve it. Skip a bot unless it asked something, and
skip threads you opened yourself — the `select` above keeps those too, since it filters
replies rather than authors.

Feedback also lands on two surfaces the gather above misses. Read both, and answer a
direct question on either — there is no thread to reply into, so answer in the conversation:

```bash
PR=123
gh api "repos/{owner}/{repo}/pulls/$PR/reviews" --paginate \
  --jq '.[] | select(.body != "") | "\(.user.login) [\(.state)]\t\(.body)"' || exit 1
gh api "repos/{owner}/{repo}/issues/$PR/comments" --paginate \
  --jq '.[] | "\(.user.login)\t\(.body)"' || exit 1
```

Only the inline threads need a reply each. Neither of those surfaces has a thread to reply
into, so answer in the conversation — `gh pr comment "$PR" --body-file -`, which reads the
body from stdin and posts when it runs.

**Substitute your own pull-request number and comment ids** — the reply block posts the
moment it runs, as does the `gh pr comment` above. Every block is POSIX shell and behaves
identically under `bash`, `zsh` and `dash`; keep it that way, because a bashism here fails
by printing nothing and exiting 0, which reads as a clean run.

**Define the footer, `PR`, the helper and every call in one shell invocation.** Each tool
call is its own shell, so a helper defined in an earlier one is gone and `$REPLY_FOOTER` is
empty, which posts unsigned replies and exits 0 — the failure this convention exists to
prevent. The footer holds two real newlines rather than `$'…'`, which is not ANSI-C quoting
under POSIX `sh` and would post as its own backslash-n while still exiting 0.

```bash
# Substitute the signature your own instructions require; this one is the author's
REPLY_FOOTER="

🤖 _Generated with [Claude Code](https://claude.com/claude-code) — Claude <your model>_"
PR=123
reply() {
  gh api -X POST "repos/{owner}/{repo}/pulls/$PR/comments/$1/replies" \
    -f body="$2$REPLY_FOOTER" --silent || { echo "FAILED: comment $1" >&2; return 1; }
}

failed=0
reply 3762661948 'Applied.' || failed=$((failed + 1))
body=$(cat <<'EOF'
Not doing this, because it doesn't hold once a second caller exists …
EOF
)
reply 3762666372 "$body" || failed=$((failed + 1))
[ "$failed" -eq 0 ] || { echo "$failed replies failed" >&2; exit 1; }
```

Check the exit code rather than reading the output: a helper that swallows a failed POST
reproduces the whole-batch failure it exists to prevent — `cmd || echo` exits 0, so the
branch must `return 1`, and every call has to collect it or the swallow moves up a level.
Pass any body containing an apostrophe through a quoted heredoc, as above; written inline
in single quotes, `doesn't` closes the literal early.

Then ask **which threads you did not have the last word on**, rather than counting
replies: a count has nothing to compare against, since replies accumulate across sittings
and other authors' count too.

```bash
PR=123
ME=$(gh api user --jq .login) || { echo "gh is not authenticated" >&2; exit 1; }
threads=$(mktemp)
trap 'rm -f "$threads"' EXIT
gh api "repos/{owner}/{repo}/pulls/$PR/comments" --paginate \
  --jq '.[] | "\(.in_reply_to_id // .id)\t\(.id)\t\(.user.login)\t\(.path):\(.line // .original_line)"' \
  > "$threads" || { echo "could not fetch review comments" >&2; exit 1; }
sort -t "$(printf '\t')" -k1,1n -k2,2n "$threads" \
  | awk -F'\t' -v me="$ME" '{ who[$1]=$3; where[$1]=$4 }
      END { for (t in who) if (who[t] != me) print t "\t" where[t] }' \
  | sort -n
```

**Last word, not "did I ever reply".** Checking whether one of your replies exists in the
thread answers the wrong question: reply "Applied.", have the reviewer come back with
"still not addressed", and a presence test drops the thread for ever — on the one comment
that most needs you. Ordering by comment id and keeping the last author survives that,
since ids ascend as comments are drafted. Not quite an invariant: a reviewer who drafts a
reply, waits for yours, then submits the review holds the lower id, and the thread drops
out. `created_at` is stamped at drafting too, so nothing in the payload fixes it — open a
pending review's own threads rather than trusting this.

The block reports bot threads and threads you opened as well. That is deliberate: a bot
that asked a real question needs an answer, and no query can tell that from a nit. Skip
those yourself, having read them, rather than letting the filter decide silently.

**An empty result is trustworthy only because every call is checked.** A failed fetch
yields an empty file and nothing downstream complains, so an unset `$PR` or an
unauthenticated `gh` would otherwise report every thread answered. Each `||` is what stops
that; the sorting and tallying after them only read a file already proved to have arrived.
With those in place, a pull request reviewed solely through summary bodies genuinely has
nothing to show here.

A thread the reviewer resolved without replying still appears: REST carries no resolved
flag, which lives on GraphQL `reviewThreads.isResolved`. Reply anyway — it costs a line.

Re-run only the ids this prints. Re-running the reply block double-posts every reply that
already landed, which is also how a batch trips GitHub's secondary rate limit.

Count nothing with `| length`: under `--paginate` each page is filtered separately, so it
prints a number per page and the first looks like the answer. (`--slurp` would join them
but is refused alongside `--jq`.)

## Additional Convention: Sweep for Stale References

Answering a review deletes files, renames symbols, and moves documentation. Before declaring the response done, search the repo **and the PR body** for references to anything the response removed or renamed. The PR body is the one nothing else checks, so it holds the freshest-looking stale reference in the whole change.

## Additional Convention: Review-Driven Decisions Earn an ADR

Where a review question is answered by a decision rather than an edit — a constraint accepted, an option rejected, a trade-off taken — record it via `phx:writing-adrs` in the same response. A reviewer's question is evidence the reasoning was not discoverable; a reply is read once, an ADR is found by the next person to ask.
