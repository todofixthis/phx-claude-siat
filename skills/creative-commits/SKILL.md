---
name: creative-commits
description: Use when creating Git commits — produces distinctive emoji-adorned commit messages with creative visual metaphors
---
# Creative Commits
Craft Git commits that read like an illustrated story — grounded words, expressive emoji.

**Division of labour — a different persona drafts each part:**
- **Title — the grounding.** Names the concrete change; light voice welcome.
- **Body — the record.** Plain prose: what changed and why, no storytelling.
- **Emoji — the illustrator.** The sole home of metaphor and story.
## Rules
- Commit via HEREDOC with three parts separated by blank lines: title, body, co-authored-by. Git treats the whole first paragraph as the subject, so a missing blank line after the title swallows the body into it and leaves the trailer unparsed
- `Co-Authored-By` names the model authoring the commit — your own identity, stated in full. Never copy a model name from this file or from Git history: both name whoever ran last, not you
- Check project docs for commit invocation; run commands sequentially
## Title
Name the **concrete change** — which part of the system changed and how — in plain words a maintainer recognises when scanning `git log --oneline`. Metaphor belongs to the emoji, not the words.
- `<= 50` chars, emoji at **end** of the title line
- Playful voice is welcome **as long as the concrete change survives it** — grounded, not a stripped changelog line
- **Bisect test:** cover the emoji and read only the words. If they could describe almost any commit (`Take the medicine we prescribed for others`), reground on the actual change. They pass when a maintainer bisecting a regression could judge from the words alone whether this commit is a plausible culprit

| Too abstract | Grounded (same change) |
|---|---|
| Give the code its first proper wash 🫧 | Run the formatter the repo forgot it declared 🫧 |
| Tune to the note the piano actually plays 🎹 | Pin setup action to its exact release tag 🎹 |
| Make every change stop at the crossing 🦓 | Add PR checks running each skill's tooling 🦓 |
| Let each decision stand on its own 🎭 | Split the combined ADR into one per decision 🎭 |

Same emoji, same story — the words now carry the change. The first row keeps its voice; the rest stay plainer. All pass the bisect test.
## Commit Body
The body is the plain record: state **what changed and why**, matter-of-factly. No storytelling, no personifying the codebase or tooling — if a bullet reads like narration ("Teach the build to…", "Split the record so…"), rewrite it as a plain statement of the change. No file paths or function names; describe the change, not the source line.
- Group related changes into a single bullet
- Scale to the commit: 1 bullet for trivial, 3–5 for larger changes; omit body for self-evident changes
- Each bullet: change, then rationale (e.g. "Add X so Y" / "Remove X to Y")

| Storytelling | Prosaic record |
|---|---|
| Teach the build to assert the rule about new tooling… | Add a CI check that fails when a skill declares a tool no workflow runs |
### Example
```
Add path aliases and strict compiler config 🧱

- Add shared path aliases so imports stay clean across packages
- Set strict compiler options to catch errors at build time

Co-Authored-By: Claude <your model> <noreply@anthropic.com>
```
## Emoji Selection
Emphasise the **human story** behind each change — why someone made it, who it serves, what it enables — not just what changed mechanically. This scene work feeds the **emoji only**; the title and body stay literal.
### Process
1. Run `uv run --project <this skill's directory> emoji-seed` — substitute the base directory reported when this skill loaded. This prints your **seed emoji** and the off-limits list — the emoji recent commits already used. The seed is off-limits as a final selection too; its role is to constrain the scene, not become the commit emoji
2. Stage the files to commit with `git add`, then run `git diff --staged` — grasp the high-level change. Also run `git status` and check for any remaining unstaged or untracked files that belong in this commit (e.g. lock files after `uv add`/`npm install`, generated files, configs updated alongside code). Stage and include them before proceeding — do not leave related files behind.
3. Ask: what **human intent or impact** does this change represent?
4. Translate that intent into a **concrete, everyday human scene** that places the seed emoji at its centre — it should be the central image, symbol, or prop. If the first angle feels forced, reframe from a different angle until it clicks; do not abandon the seed
5. From the scene in step 4, pick the single emoji — excluding the seed and everything on the off-limits list — with the strongest narrative link to the commit; run it through the three-stage filter:
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
