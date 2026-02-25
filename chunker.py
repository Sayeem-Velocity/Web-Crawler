"""
chunker.py
----------
Splits cleaned Markdown into token-counted chunks with overlap.
Uses tiktoken so chunk sizes align with OpenAI-style model token limits.
"""

import logging
from typing import Optional

import tiktoken

import config

logger = logging.getLogger(__name__)

_encoder: Optional[tiktoken.Encoding] = None


def _get_encoder() -> tiktoken.Encoding:
    """Lazy-load the tiktoken encoder."""
    global _encoder
    if _encoder is None:
        _encoder = tiktoken.get_encoding(config.ENCODING_NAME)
    return _encoder


def chunk_text(text: str,
               chunk_size: int = config.CHUNK_SIZE,
               overlap: int = config.CHUNK_OVERLAP) -> list[dict]:
    """
    Split *text* into chunks of approximately *chunk_size* tokens,
    with *overlap* tokens shared between consecutive chunks.

    Returns a list of dicts:
      {"text": str, "token_count": int, "chunk_index": int}
    """
    enc = _get_encoder()
    tokens = enc.encode(text)
    total_tokens = len(tokens)

    if total_tokens == 0:
        return []

    if total_tokens <= chunk_size:
        return [{"text": text, "token_count": total_tokens, "chunk_index": 0}]

    chunks = []
    start = 0
    idx = 0

    while start < total_tokens:
        end = min(start + chunk_size, total_tokens)
        chunk_tokens = tokens[start:end]
        chunk_text_str = enc.decode(chunk_tokens)

        chunks.append({
            "text": chunk_text_str,
            "token_count": len(chunk_tokens),
            "chunk_index": idx,
        })

        # advance by (chunk_size - overlap) so the next chunk shares 'overlap' tokens
        start += chunk_size - overlap
        idx += 1

    logger.debug("Chunked %d tokens into %d chunks.", total_tokens, len(chunks))
    return chunks


def chunk_posts(posts: list[dict]) -> list[dict]:
    """
    Take a list of post dicts (with 'markdown' field) and return
    a flat list of chunk dicts, each inheriting the post metadata.
    """
    all_chunks = []
    for post in posts:
        chunks = chunk_text(post["markdown"])
        for chunk in chunks:
            record = {
                "title": post["title"],
                "url": post.get("url", ""),
                "date": post.get("date", ""),
                "source": config.BASE_URL,
                "chunk_index": chunk["chunk_index"],
                "total_chunks": len(chunks),
                "token_count": chunk["token_count"],
                "text": chunk["text"],
            }
            all_chunks.append(record)

    logger.info("Chunking complete. %d posts -> %d chunks.", len(posts), len(all_chunks))
    return all_chunks
