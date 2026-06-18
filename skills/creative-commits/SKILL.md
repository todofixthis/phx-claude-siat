---
name: creative-commits
description: Use when creating Git commits — produces distinctive emoji-adorned commit messages with creative visual metaphors
---
# Creative Commits
Craft Git commits with distinctive, metaphorical emoji and concise messages.
## Rules
- Title <= 50 chars, emoji at **end** of title line
- Commit via HEREDOC with three parts separated by blank lines: title, body, co-authored-by
- Check project docs for commit invocation; run commands sequentially
## Commit Body
Bullet the logical changes — what shifted and why. No file paths or function names; keep it conceptual.
- Group related changes into a single bullet
- Scale to the commit: 1 bullet for trivial, 3–5 for larger changes; omit body for self-evident changes
- Each bullet: change, then rationale (e.g. "Add X so Y" / "Remove X to Y")
### Example
```
Lay the foundation stones 🧱
- Add shared path aliases so imports stay clean across packages
- Set strict compiler options to catch errors at build time
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
```
## Emoji Selection
Emphasise the **human story** behind each change — why someone made it, who it serves, what it enables — not just what changed mechanically.
### Process
1. Run `uv run --project "$(cat $HOME/.claude/plugins/data/phx.root)/skills/creative-commits" emoji-seed` — this prints your **seed emoji** and the off-limits list. The seed is off-limits as a final selection — its role is to constrain the scene, not become the commit emoji
2. Stage the files to commit with `git add`, then run `git diff --staged` — grasp the high-level change. Also run `git status` and check for any remaining unstaged or untracked files that belong in this commit (e.g. lock files after `uv add`/`npm install`, generated files, configs updated alongside code). Stage and include them before proceeding — do not leave related files behind.
3. Ask: what **human intent or impact** does this change represent?
4. Translate that intent into a **concrete, everyday human scene** that places the seed emoji at its centre — it should be the central image, symbol, or prop. If the first angle feels forced, reframe from a different angle until it clicks; do not abandon the seed
5. From the scene in step 4, pick the single emoji — other than the seed — with the strongest narrative link to the commit; run it through the three-stage filter:
| Stage | Verdict | Action |
|-------|---------|--------|
| **Too safe** — predictable, cliché, category-label (🐛 for bug, 📝 for docs, ✨ for feature), or literal echo of a word in the message | Drop | Always discard |
| **Just right** — novel yet tells a clear story linking back to the commit's theme | Accept | Use this |
| **Too weird** — abstract, opaque, requires explanation to connect | Drop | Always discard |
6. **Explain your scene and selection reasoning in session output** (not in the commit text)
- Avoid building a personal repertoire; each commit should feel like a fresh creative act
### Examples
| Message | Emoji | Why |
|---------|-------|-----|
| Add release changelog | 📣 | Someone announcing news to people, not just listing items |
| Hybrid background script | 🌉 | Bridge connects two worlds — emphasises unifying intent |
| NZ English convention | 🥝 | Cultural identity of the people behind the convention |
| Refine agent docs | 🪥 | Morning-routine care — someone tidying things for others |
| Rich-text clipboard plan | 🦎 | Adapting to surroundings like a person reading the room |
**Goal:** Git log reads like a human narrative — each emoji reflects intent, care, and craft rather than category.
