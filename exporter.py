"""
exporter.py
-----------
Writes chunked records to JSONL format, ready for LLM fine-tuning or embedding.
"""

import json
import logging
import os
import hashlib
from datetime import datetime, timezone

import config

logger = logging.getLogger(__name__)


def _make_id(record: dict) -> str:
    """Generate a stable, unique ID for a chunk based on its content and metadata."""
    key = f"{record.get('url', '')}-{record.get('chunk_index', 0)}-{record.get('text', '')[:100]}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]


def build_jsonl_records(chunks: list[dict]) -> list[dict]:
    """
    Transform raw chunk dicts into the final JSONL schema.

    Schema per line:
    {
        "id": str,            -- unique hash
        "text": str,          -- the chunk content
        "metadata": {
            "title": str,
            "url": str,
            "date": str,
            "source": str,
            "chunk_index": int,
            "total_chunks": int,
            "token_count": int,
            "scraped_at": str  -- ISO 8601 timestamp
        }
    }
    """
    scraped_at = datetime.now(timezone.utc).isoformat()
    records = []
    for chunk in chunks:
        record = {
            "id": _make_id(chunk),
            "text": chunk["text"],
            "metadata": {
                "title": chunk["title"],
                "url": chunk["url"],
                "date": chunk["date"],
                "source": chunk["source"],
                "chunk_index": chunk["chunk_index"],
                "total_chunks": chunk["total_chunks"],
                "token_count": chunk["token_count"],
                "scraped_at": scraped_at,
            },
        }
        records.append(record)
    return records


def write_jsonl(records: list[dict], filepath: str | None = None) -> str:
    """
    Write records to a JSONL file.  Returns the absolute path written.
    """
    if filepath is None:
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        filepath = os.path.join(config.OUTPUT_DIR, config.JSONL_FILENAME)

    with open(filepath, "w", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    abs_path = os.path.abspath(filepath)
    logger.info("Wrote %d records to %s", len(records), abs_path)
    return abs_path


def export(chunks: list[dict], filepath: str | None = None) -> str:
    """Full export: build records then write JSONL. Returns path."""
    records = build_jsonl_records(chunks)
    return write_jsonl(records, filepath)
