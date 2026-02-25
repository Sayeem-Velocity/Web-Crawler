# Python Blog Scraper -- LLM Data Pipeline

A production-ready web scraping system that extracts blog posts from
**https://blog.python.org/**, converts them to clean Markdown, chunks
them into token-sized pieces, attaches metadata, and exports everything
as a JSONL file ready for LLM fine-tuning or embedding.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Pipeline Stages](#pipeline-stages)
4. [File Structure](#file-structure)
5. [Setup](#setup)
6. [Usage](#usage)
7. [Configuration](#configuration)
8. [Output Format](#output-format)
9. [Extending the Pipeline](#extending-the-pipeline)

---

## Project Overview

This project automates the collection and preparation of text data from
the official Python blog.  The output is a single JSONL file where each
line is a self-contained JSON object with a chunk of text and rich
metadata.  This format is directly consumable by:

- OpenAI fine-tuning API
- Embedding pipelines (text-embedding-ada-002, etc.)
- RAG (retrieval-augmented generation) vector stores
- Any system that accepts newline-delimited JSON

The pipeline is intentionally simple -- five small Python modules with
no framework dependencies beyond `requests`, `beautifulsoup4`,
`html2text`, and `tiktoken`.

---

## Architecture

```
blog.python.org
      |
      v
 +-----------+     +-----------+     +-----------+     +-----------+
 |  SCRAPE   | --> |   CLEAN   | --> |   CHUNK   | --> |  EXPORT   |
 | scraper.py|     | cleaner.py|     | chunker.py|     |exporter.py|
 +-----------+     +-----------+     +-----------+     +-----------+
      |                                                      |
      v                                                      v
 output/raw_markdown/                              output/dataset.jsonl
 (debug copies)                                    (final output)
```

All stages are orchestrated by `pipeline.py`, which can be run with a
single command.

---

## Pipeline Stages

### Stage 1 -- Scrape (`scraper.py`)

- Uses `requests` with a polite delay between fetches (configurable).
- Parses listing pages with `BeautifulSoup` to find post links.
- Follows pagination ("Older Posts") to reach historical content.
- Converts each post body from HTML to Markdown using `html2text`.
- Returns a list of dicts: `{title, url, date, markdown}`.

### Stage 2 -- Clean (`cleaner.py`)

- Strips residual HTML tags.
- Removes image references and bare-URL lines.
- Removes boilerplate text (navigation, share buttons, labels).
- Normalizes whitespace and collapses excessive blank lines.
- Discards posts whose cleaned body is shorter than 50 characters.

### Stage 3 -- Chunk (`chunker.py`)

- Tokenizes text using `tiktoken` with the `cl100k_base` encoding
  (the same encoding used by GPT-4 and text-embedding-ada-002).
- Splits each post into chunks of ~512 tokens (configurable).
- Consecutive chunks share a 64-token overlap so context is not lost
  at boundaries.
- Each chunk records its token count and index.

### Stage 4 -- Export (`exporter.py`)

- Attaches structured metadata to every chunk (title, date, URL,
  source, chunk index, total chunks, token count, scrape timestamp).
- Generates a stable SHA-256-based ID for each record.
- Writes one JSON object per line to `output/dataset.jsonl`.

---

## File Structure

```
Web Scraping/
|-- config.py          # All tunable settings (URLs, sizes, paths)
|-- scraper.py         # Stage 1 -- fetch + HTML-to-Markdown
|-- cleaner.py         # Stage 2 -- strip noise
|-- chunker.py         # Stage 3 -- token-based splitting
|-- exporter.py        # Stage 4 -- JSONL writer
|-- pipeline.py        # Orchestrator / CLI entry point
|-- requirements.txt   # Python dependencies
|-- README.md          # This file
|-- output/
|   |-- dataset.jsonl       # Final JSONL output
|   |-- raw_markdown/       # Per-post Markdown (debug)
```

---

## Setup

### 1. Create a virtual environment

```bash
cd "d:\Web Scraping"
python -m venv venv
```

### 2. Activate the environment

```powershell
# Windows PowerShell
.\venv\Scripts\Activate.ps1
```

```bash
# Linux / macOS
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Usage

### Run the full pipeline

```bash
python pipeline.py
```

### Limit the number of posts

```bash
python pipeline.py --max-posts 10
```

### Output location

After the pipeline completes it prints a summary and the path to the
JSONL file, which defaults to `output/dataset.jsonl`.

---

## Configuration

All settings live in `config.py`.  Key options:

| Setting          | Default          | Description                               |
|------------------|------------------|-------------------------------------------|
| `BASE_URL`       | Python blog URL  | Target site to scrape                     |
| `MAX_POSTS`      | 50               | Max posts to collect                      |
| `REQUEST_DELAY`  | 1.5              | Seconds between HTTP requests             |
| `CHUNK_SIZE`     | 512              | Target tokens per chunk                   |
| `CHUNK_OVERLAP`  | 64               | Overlapping tokens between chunks         |
| `ENCODING_NAME`  | cl100k_base      | Tiktoken encoding (GPT-4 compatible)      |
| `OUTPUT_DIR`     | output           | Directory for output files                |
| `JSONL_FILENAME` | dataset.jsonl    | Name of the final JSONL file              |

---

## Output Format

Each line in `dataset.jsonl` is a JSON object with this schema:

```json
{
  "id": "a3f8c1e902b7d4e1",
  "text": "Python 3.12 introduces several new features ...",
  "metadata": {
    "title": "Python 3.12.0 is here",
    "url": "https://blog.python.org/2024/...",
    "date": "Monday, October 02, 2024",
    "source": "https://blog.python.org/",
    "chunk_index": 0,
    "total_chunks": 3,
    "token_count": 498,
    "scraped_at": "2026-02-26T12:00:00+00:00"
  }
}
```

**Field descriptions:**

- `id` -- Stable hash derived from the URL, chunk index, and content.
- `text` -- The cleaned Markdown chunk, ready for model consumption.
- `metadata.title` -- Original blog post title.
- `metadata.url` -- Permalink to the source post.
- `metadata.date` -- Publication date as shown on the blog.
- `metadata.source` -- Root URL of the scraped site.
- `metadata.chunk_index` -- Zero-based index of this chunk within its post.
- `metadata.total_chunks` -- How many chunks the parent post was split into.
- `metadata.token_count` -- Exact token count (cl100k_base encoding).
- `metadata.scraped_at` -- UTC timestamp of when the scrape ran.

---

## Extending the Pipeline

### Use the data for fine-tuning

Convert JSONL records into the OpenAI fine-tuning format:

```python
import json

with open("output/dataset.jsonl") as f:
    for line in f:
        record = json.loads(line)
        # Build your {"messages": [...]} training example here
        print(record["text"][:80])
```

### Use the data for embeddings / RAG

Feed each record's `text` field into your embedding model and store
the resulting vector alongside the `metadata` in your vector database.

### Scrape a different site

Change `BASE_URL` in `config.py` and adjust the CSS selectors in
`scraper.py` (`_parse_post_links`, `_fetch_post_body`) to match the
new site's HTML structure.

---

## Dependencies

| Package        | Purpose                                    |
|----------------|--------------------------------------------|
| requests       | HTTP client for fetching pages             |
| beautifulsoup4 | HTML parsing and element selection         |
| lxml           | Fast HTML parser backend for BeautifulSoup |
| html2text      | HTML to Markdown conversion                |
| tiktoken       | Token counting (OpenAI-compatible BPE)     |

All are listed in `requirements.txt` with pinned versions.
