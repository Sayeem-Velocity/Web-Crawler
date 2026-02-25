"""
Configuration for the web scraping pipeline.
All settings are centralized here for easy modification.
"""

# -- Target --
BASE_URL = "https://blog.python.org/"
MAX_POSTS = 50  # maximum blog posts to scrape (set to None for all)

# -- Request --
REQUEST_TIMEOUT = 30  # seconds
REQUEST_DELAY = 1.5   # polite delay between requests (seconds)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# -- Chunking --
CHUNK_SIZE = 512       # target tokens per chunk
CHUNK_OVERLAP = 64     # overlap tokens between consecutive chunks
ENCODING_NAME = "cl100k_base"  # tiktoken encoding (GPT-4 / text-embedding-ada-002)

# -- Output --
OUTPUT_DIR = "output"
JSONL_FILENAME = "dataset.jsonl"
RAW_DIR = "output/raw_markdown"

# -- Logging --
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"
