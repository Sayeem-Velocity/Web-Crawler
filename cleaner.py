"""
cleaner.py
----------
Takes raw Markdown text and strips noise that would hurt LLM training quality.
"""

import re
import logging

logger = logging.getLogger(__name__)


def clean_markdown(text: str) -> str:
    """
    Clean a Markdown string for LLM consumption.

    Steps
    -----
    1. Normalize line endings.
    2. Remove HTML tags that html2text may have left behind.
    3. Remove image references.
    4. Collapse excessive blank lines.
    5. Strip leading/trailing whitespace per line.
    6. Remove navigation / boilerplate lines.
    7. Strip zero-width and non-breaking spaces.
    """
    if not text:
        return ""

    # 1 - normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 2 - remove residual HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # 3 - remove markdown image syntax ![alt](url)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)

    # 4 - remove lines that are purely URLs (leftover link dumps)
    text = re.sub(r"^\s*https?://\S+\s*$", "", text, flags=re.MULTILINE)

    # 5 - remove boilerplate / nav patterns common in blogs
    boilerplate_patterns = [
        r"^posted by\s.*$",
        r"^labels?:\s.*$",
        r"^Share\s*$",
        r"^Tweet\s*$",
        r"^Email This.*$",
        r"^BlogThis!.*$",
        r"^Share to (Twitter|Facebook|Pinterest).*$",
        r"^\d+ comments?:?\s*$",
        r"^Newer Post.*Older Post.*Home\s*$",
        r"^Subscribe to:.*$",
    ]
    for pattern in boilerplate_patterns:
        text = re.sub(pattern, "", text, flags=re.MULTILINE | re.IGNORECASE)

    # 6 - strip zero-width / non-breaking spaces
    text = text.replace("\u200b", "").replace("\u00a0", " ").replace("\ufeff", "")

    # 7 - strip each line, then collapse runs of 3+ newlines into 2
    lines = [line.strip() for line in text.split("\n")]
    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text.strip()


def clean_posts(posts: list[dict]) -> list[dict]:
    """Apply clean_markdown to the 'markdown' field of every post."""
    cleaned = []
    for post in posts:
        body = clean_markdown(post.get("markdown", ""))
        if len(body) < 50:
            logger.warning("Skipping post '%s' -- body too short after cleaning (%d chars).",
                           post.get("title", "?"), len(body))
            continue
        cleaned.append({**post, "markdown": body})
    logger.info("Cleaning complete. %d / %d posts retained.", len(cleaned), len(posts))
    return cleaned
