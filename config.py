"""
Configuration for the web scraping pipeline.
All settings are centralized here for easy modification.
"""

# ---------------------------------------------------------------------------
# TARGET
# Change BASE_URL to any website you want to scrape.
# ---------------------------------------------------------------------------
BASE_URL = "https://blog.python.org/"

# Maximum number of pages to crawl (set to None to crawl the entire site)
MAX_PAGES = 50

# Only follow links that stay on the same domain as BASE_URL
SAME_DOMAIN_ONLY = True

# ---------------------------------------------------------------------------
# CONTENT EXTRACTION
# The scraper tries each selector in order and uses the first one that matches.
# This covers most common site layouts: blogs, docs, news, wikis, etc.
# Add or reorder selectors here to tune extraction for a specific site.
# ---------------------------------------------------------------------------
CONTENT_SELECTORS = [
    "article",
    "main",
    "[role='main']",
    ".post-body",
    ".post-content",
    ".entry-content",
    ".article-content",
    ".article-body",
    ".content-body",
    ".td-post-content",
    ".blog-post",
    "#content",
    "#main",
    ".content",
    ".page-content",
    "div.post",
    "body",   # last-resort fallback
]

# Tags to strip from content before conversion (noise / boilerplate)
STRIP_TAGS = [
    "nav", "header", "footer", "aside",
    "script", "style", "noscript",
    "form", "button", "iframe",
    ".sidebar", ".advertisement", ".ads", ".social-share",
    ".comments", "#comments",
]

# ---------------------------------------------------------------------------
# REQUEST
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT = 30  # seconds per request
REQUEST_DELAY = 1.5   # polite delay between requests (seconds)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# ---------------------------------------------------------------------------
# CHUNKING
# ---------------------------------------------------------------------------
CHUNK_SIZE = 512       # target tokens per chunk
CHUNK_OVERLAP = 64     # overlap tokens between consecutive chunks
ENCODING_NAME = "cl100k_base"  # tiktoken encoding (GPT-4 / text-embedding-ada-002)

# ---------------------------------------------------------------------------
# OUTPUT
# ---------------------------------------------------------------------------
OUTPUT_DIR = "output"
JSONL_FILENAME = "dataset.jsonl"
RAW_DIR = "output/raw_markdown"

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
