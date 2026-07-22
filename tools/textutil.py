#!/usr/bin/env python3
"""Small text helpers shared by the faceless-video tools.

Kept dependency-free so any tool in `tools/` can `import textutil` (the script's
own directory is on sys.path when run as `python tools/<tool>.py` from the repo
root).
"""
from __future__ import annotations
import re

# Emoji / pictograph ranges. Deliberately targeted at emoji — NOT typographic
# arrows/symbols the scene renderers use on screen (e.g. the "→" between steps),
# since this only ever touches narration/caption *text*.
_EMOJI_RE = re.compile(
    "["
    "\U0001F300-\U0001FAFF"  # symbols & pictographs (incl. supplemental + extended-A): 🚀🤖💖🤝
    "\U0001F000-\U0001F0FF"  # mahjong / dominoes / playing cards
    "\U00002600-\U000026FF"  # miscellaneous symbols
    "\U00002700-\U000027BF"  # dingbats
    "\U00002B00-\U00002BFF"  # misc symbols & arrows (⭐ etc.)
    "\U0001F1E6-\U0001F1FF"  # regional indicators (flags)
    "\U0000FE00-\U0000FE0F"  # variation selectors
    "\U0000200D"             # zero-width joiner
    "\U00002640-\U00002642"  # gender signs used in ZWJ sequences
    "]",
    flags=re.UNICODE,
)


def strip_emoji(text: str) -> str:
    """Remove emoji/pictographs and tidy the whitespace they leave behind.

    Used so captions never show emoji and the voice-over never tries to speak
    them. Returns a clean, single-spaced, trimmed string.
    """
    if not text:
        return text
    out = _EMOJI_RE.sub("", text)
    out = re.sub(r"\s{2,}", " ", out)          # collapse the gaps emoji leave
    out = re.sub(r"\s+([;,.!?])", r"\1", out)  # no space before punctuation
    return out.strip()
