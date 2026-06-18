import random
import subprocess
import sys

import emoji
import regex

_EMOJI_RE = regex.compile(r'\p{Emoji_Presentation}|\p{Emoji}\uFE0F')


def main() -> None:
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", "-25"],
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        print(f"Failed to run git: {exc}", file=sys.stderr)
        sys.exit(1)

    no_commits = result.returncode != 0 and "does not have any commits" in result.stderr
    if result.returncode != 0 and not no_commits:
        print(f"git log failed: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)

    # Preserve first-appearance order so output is deterministic
    off_limits = list(dict.fromkeys(_EMOJI_RE.findall(result.stdout)))
    all_emoji = list(emoji.EMOJI_DATA)

    pick = None
    for _ in range(3):
        pick = random.choice(all_emoji)
        if pick not in off_limits:
            break

    line = f"seed: {pick}"
    if off_limits:
        line += f"  off-limits: {' '.join(off_limits)}"
    print(line)
