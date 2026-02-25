# Web Scraping Pipeline for LLM Data

A production-ready web scraping system that crawls **any website**, converts
pages to clean Markdown, chunks content into token-sized pieces, attaches
metadata, and exports everything as a JSONL file ready for LLM fine-tuning
or embedding / RAG.

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture](#architecture)
3. [Pipeline Stages](#pipeline-stages)
4. [File Structure](#file-structure)
5. [Setup](#setup)
6. [Usage](#usage)
7. [Changing the Target Site](#changing-the-target-site)
8. [Configuration Reference](#configuration-reference)
9. [Output Format](#output-format)
10. [Extending the Pipeline](#extending-the-pipeline)

---

## Project Overview

This pipeline automates the collection and preparation of text data from
any website.  The output is a single JSONL file where each line is a
self-contained JSON object with a chunk of text and rich metadata.  This
format is directly usable by:

- RAG (retrieval-augmented generation) vector stores
- OpenAI / Hugging Face fine-tuning pipelines
- Embedding APIs (text-embedding-ada-002, sentence-transformers, etc.)
- Any system that accepts newline-delimited JSON

The pipeline uses five focused Python modules and five lightweight
dependencies.  To scrape a different site, change one line in `config.py`.

---

## Architecture

```
Any Website
    |
    v
+-----------+     +-----------+     +-----------+     +-----------+
|  SCRAPE   | --> |   CLEAN   | --> |   CHUNK   | --> |  EXPORT   |
| scraper.py|     | cleaner.py|     | chunker.py|     |exporter.py|
+-----------+     +-----------+     +-----------+     +-----------+
    |                                                      |
    v                                                      v
output/raw_markdown/                              output/dataset.jsonl
(one .md file per page)                           (final LLM-ready output)
```

All stages are orchestrated by `pipeline.py`.

---

## Pipeline Stages

### Stage 1 -- Scrape (`scraper.py`)

- Uses BFS (breadth-first search) to crawl all internal pages starting
  from `BASE_URL`.
- Respects `SAME_DOMAIN_ONLY` -- will not follow links to external sites.
- Skips binary files (images, PDFs, CSS, JS, etc.) automatically.
- Extracts title from OG meta tags, `<h1>`, or `<title>`.
- Extracts date from `<meta property="article:published_time">`, `<time>`,
  or common date CSS class patterns.
- Finds the main content via a priority list of CSS selectors defined in
  `config.py` -- no hardcoded site-specific logic.
- Strips noisy elements (nav, footer, sidebar, ads, scripts) before
  conversion.
- Converts the content block from HTML to Markdown using `html2text`.
- Polite delay between requests (configurable).

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

### Limit the number of pages crawled

```bash
python pipeline.py --max-pages 20
```

### Output

After the pipeline finishes it prints a summary:

```
==================================================
  PIPELINE SUMMARY
==================================================
  Records : 87
  Tokens  : 42,301
  File    : D:\Web Scraping\output\dataset.jsonl
  Size    : 183.4 KB
==================================================
```

---

## Changing the Target Site

### Step 1 -- Set the URL in `config.py`

```python
BASE_URL = "https://docs.python.org/3/"        # docs site
BASE_URL = "https://realpython.com/"           # tutorial blog
BASE_URL = "https://en.wikipedia.org/wiki/Python_(programming_language)"
```

That is the **only required change** for most sites.

### Step 2 -- Optionally tune content selectors

If the default selectors do not capture the right content, inspect the
site's HTML (browser DevTools -> right-click -> Inspect) and add your
selector to the top of `CONTENT_SELECTORS` in `config.py`:

```python
CONTENT_SELECTORS = [
    ".my-custom-content",   # add site-specific selector at the top
    "article",
    "main",
    ...
]
```

### Step 3 -- Optionally allow cross-domain crawling

```python
SAME_DOMAIN_ONLY = False  # follow links to any domain
```

### Common site selectors quick reference

| Site type          | Likely selector             |
|--------------------|-----------------------------|
| WordPress blog     | `.entry-content`            |
| Medium article     | `article`                   |
| ReadTheDocs        | `.rst-content`              |
| GitBook docs       | `.page-inner`               |
| Confluence wiki    | `#main-content`             |
| Ghost blog         | `.post-content`             |

---

## Configuration Reference

All settings are in `config.py`:

| Setting             | Default           | Description                                     |
|---------------------|-------------------|-------------------------------------------------|
| `BASE_URL`          | Python blog URL   | Starting URL for the crawl                      |
| `MAX_PAGES`         | 50                | Max pages to crawl (None = unlimited)           |
| `SAME_DOMAIN_ONLY`  | True              | Restrict crawl to the same domain               |
| `CONTENT_SELECTORS` | (list)            | Priority-ordered CSS selectors for main content |
| `STRIP_TAGS`        | (list)            | Tags/selectors stripped before conversion       |
| `REQUEST_DELAY`     | 1.5               | Seconds between requests (be polite)            |
| `REQUEST_TIMEOUT`   | 30                | HTTP timeout in seconds                         |
| `CHUNK_SIZE`        | 512               | Target tokens per chunk                         |
| `CHUNK_OVERLAP`     | 64                | Overlapping tokens between chunks               |
| `ENCODING_NAME`     | cl100k_base       | Tiktoken encoding (GPT-4 compatible)            |
| `OUTPUT_DIR`        | output            | Directory for output files                      |
| `JSONL_FILENAME`    | dataset.jsonl     | Name of the final JSONL file                    |

---

## Output Format

Each line in `dataset.jsonl` is a JSON object with this schema:

```json
{
  "id": "a3f8c1e902b7d4e1",
  "text": "Python 3.12 introduces several new features ...",
  "metadata": {
    "title": "What's New In Python 3.12",
    "url": "https://docs.python.org/3/whatsnew/3.12.html",
    "date": "2024-10-01T00:00:00",
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
- `metadata.title` -- Page title.
- `metadata.url` -- Source page URL.
- `metadata.date` -- Publication date detected on the page.
- `metadata.source` -- The crawl root (BASE_URL).
- `metadata.chunk_index` -- Zero-based index of this chunk within its post.
- `metadata.total_chunks` -- How many chunks the parent post was split into.
- `metadata.token_count` -- Exact token count (cl100k_base encoding).
- `metadata.scraped_at` -- UTC timestamp of when the scrape ran.

---

## Extending the Pipeline

### Use data for RAG / Vector DB

```python
import json

with open("output/dataset.jsonl") as f:
    for line in f:
        record = json.loads(line)
        text = record["text"]          # embed this
        metadata = record["metadata"]  # store alongside the vector
```

### Use data for fine-tuning

Convert to the OpenAI messages format:

```python
import json

with open("output/dataset.jsonl") as f:
    for line in f:
        record = json.loads(line)
        training_example = {
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Summarize: " + record["text"][:200]},
                {"role": "assistant", "content": record["text"]}
            ]
        }

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
