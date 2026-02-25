"""
pipeline.py
-----------
Main entry point.  Runs the full scraping pipeline end-to-end:

    Scrape  ->  Clean  ->  Chunk  ->  Export (JSONL)

Usage:
    python pipeline.py
    python pipeline.py --max-posts 10
"""

import argparse
import json
import logging
import os
import sys
import time

import config
from scraper import scrape_blog
from cleaner import clean_posts
from chunker import chunk_posts
from exporter import export


def _setup_logging() -> None:
    logging.basicConfig(
        level=getattr(logging, config.LOG_LEVEL, logging.INFO),
        format=config.LOG_FORMAT,
    )


def _save_raw_markdown(posts: list[dict]) -> None:
    """Optionally persist the raw markdown per post for inspection."""
    os.makedirs(config.RAW_DIR, exist_ok=True)
    for i, post in enumerate(posts):
        slug = post["title"][:60].replace(" ", "_").replace("/", "_")
        path = os.path.join(config.RAW_DIR, f"{i:03d}_{slug}.md")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(f"# {post['title']}\n\n")
            fh.write(f"Date: {post['date']}\n\n")
            fh.write(f"URL: {post['url']}\n\n---\n\n")
            fh.write(post.get("markdown", ""))


def run(max_posts: int | None = None) -> str:
    """Execute the full pipeline and return the path to the JSONL file."""
    _setup_logging()
    logger = logging.getLogger(__name__)

    start = time.time()

    # -- Step 1: Scrape --
    logger.info("[1/4] Scraping blog posts ...")
    posts = scrape_blog(max_posts=max_posts)
    if not posts:
        logger.error("No posts scraped. Exiting.")
        sys.exit(1)
    logger.info("       Scraped %d posts.", len(posts))

    # Save raw markdown for debugging
    _save_raw_markdown(posts)

    # -- Step 2: Clean --
    logger.info("[2/4] Cleaning markdown ...")
    posts = clean_posts(posts)
    if not posts:
        logger.error("All posts discarded during cleaning. Exiting.")
        sys.exit(1)

    # -- Step 3: Chunk --
    logger.info("[3/4] Chunking into token-sized pieces ...")
    chunks = chunk_posts(posts)
    logger.info("       Produced %d chunks.", len(chunks))

    # -- Step 4: Export --
    logger.info("[4/4] Exporting to JSONL ...")
    output_path = export(chunks)

    elapsed = time.time() - start
    logger.info("Pipeline finished in %.1f seconds.", elapsed)
    logger.info("Output: %s", output_path)

    # Print a quick summary
    _print_summary(output_path)

    return output_path


def _print_summary(jsonl_path: str) -> None:
    """Print a human-readable summary of the output file."""
    total_records = 0
    total_tokens = 0
    with open(jsonl_path, "r", encoding="utf-8") as fh:
        for line in fh:
            record = json.loads(line)
            total_records += 1
            total_tokens += record["metadata"]["token_count"]

    file_size_kb = os.path.getsize(jsonl_path) / 1024

    print("\n" + "=" * 50)
    print("  PIPELINE SUMMARY")
    print("=" * 50)
    print(f"  Records : {total_records}")
    print(f"  Tokens  : {total_tokens:,}")
    print(f"  File    : {jsonl_path}")
    print(f"  Size    : {file_size_kb:.1f} KB")
    print("=" * 50 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Python Blog Scraping Pipeline for LLM")
    parser.add_argument(
        "--max-posts", type=int, default=None,
        help="Maximum number of blog posts to scrape (default: value in config.py)"
    )
    args = parser.parse_args()
    run(max_posts=args.max_posts)


if __name__ == "__main__":
    main()
