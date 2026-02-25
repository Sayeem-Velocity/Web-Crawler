"""
scraper.py
----------
Generic site crawler.  Works with any website by:
  - Following all internal links (BFS, same domain)
  - Extracting main content via a priority list of CSS selectors
  - Converting HTML to Markdown with html2text
  - Pulling title and date from common meta / structural tags

To use with a different site, change BASE_URL in config.py.
To tune content extraction, adjust CONTENT_SELECTORS in config.py.
"""

import logging
import re
import time
from collections import deque
from typing import Optional
from urllib.parse import urljoin, urlparse, urldefrag

import html2text
import requests
from bs4 import BeautifulSoup

import config

logger = logging.getLogger(__name__)

# ---- html2text converter setup ----
_converter = html2text.HTML2Text()
_converter.ignore_links = False
_converter.ignore_images = True
_converter.ignore_emphasis = False
_converter.body_width = 0  # no wrapping

# Regex: skip non-HTML/text resources
_SKIP_EXTENSIONS = re.compile(
    r"\.(png|jpg|jpeg|gif|svg|webp|ico|css|js|pdf|zip|gz|tar|mp4|mp3|woff2?)$",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        "User-Agent": config.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return session


def _fetch_page(session: requests.Session, url: str) -> Optional[BeautifulSoup]:
    """Fetch a URL and return BeautifulSoup, or None on failure."""
    try:
        response = session.get(url, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "text/html" not in content_type:
            return None
        return BeautifulSoup(response.text, "lxml")
    except requests.RequestException as exc:
        logger.warning("Skipping %s: %s", url, exc)
        return None


def _normalize_url(url: str, base: str) -> str:
    """Resolve relative URLs and strip fragment identifiers."""
    full, _ = urldefrag(urljoin(base, url))
    return full


def _same_domain(url: str, base_domain: str) -> bool:
    """Return True if url belongs to the same domain (or a subdomain)."""
    parsed = urlparse(url)
    host = parsed.netloc.lower().lstrip("www.")
    return host == base_domain or host.endswith("." + base_domain)


def _collect_links(soup: BeautifulSoup, page_url: str, base_domain: str) -> list[str]:
    """Return all internal links found on the page."""
    links = []
    for tag in soup.find_all("a", href=True):
        href = tag["href"].strip()
        if not href or href.startswith("mailto:") or href.startswith("javascript:"):
            continue
        full = _normalize_url(href, page_url)
        if not full.startswith("http"):
            continue
        if _SKIP_EXTENSIONS.search(urlparse(full).path):
            continue
        if config.SAME_DOMAIN_ONLY and not _same_domain(full, base_domain):
            continue
        links.append(full)
    return links


def _extract_title(soup: BeautifulSoup) -> str:
    """Extract the page title from common locations."""
    # Try OG title first (most accurate for blog posts)
    og = soup.find("meta", property="og:title")
    if og and og.get("content"):
        return og["content"].strip()
    # Try the first <h1>
    h1 = soup.find("h1")
    if h1:
        return h1.get_text(strip=True)
    # Fall back to <title> tag
    if soup.title and soup.title.string:
        return soup.title.string.strip()
    return "Untitled"


def _extract_date(soup: BeautifulSoup) -> str:
    """Extract publish date from common meta / structural tags."""
    # <meta property="article:published_time" ...>
    meta = soup.find("meta", property="article:published_time")
    if meta and meta.get("content"):
        return meta["content"].strip()
    # <time datetime="...">
    time_tag = soup.find("time", attrs={"datetime": True})
    if time_tag:
        return time_tag["datetime"].strip()
    # <time> text only
    time_tag = soup.find("time")
    if time_tag:
        return time_tag.get_text(strip=True)
    # Common CSS class patterns  (e.g. class="date", "published", "post-date", etc.)
    for cls in ["date", "published", "post-date", "entry-date", "article-date",
                "post-timestamp", "timestamp", "byline"]:
        tag = soup.find(class_=re.compile(cls, re.IGNORECASE))
        if tag:
            text = tag.get_text(strip=True)
            if text:
                return text
    return "unknown"


def _extract_content(soup: BeautifulSoup) -> str:
    """
    Extract the main content block as Markdown.
    Tries CONTENT_SELECTORS in order; falls back to <body>.
    Strips noisy tags (nav, footer, ads, etc.) before conversion.
    """
    # Work on a copy so we don't mutate the original soup
    working = BeautifulSoup(str(soup), "lxml")

    # Remove noisy elements
    for selector in config.STRIP_TAGS:
        for el in working.select(selector):
            el.decompose()

    # Find the best content container
    content_el = None
    for selector in config.CONTENT_SELECTORS:
        el = working.select_one(selector)
        if el and len(el.get_text(strip=True)) > 100:
            content_el = el
            break

    if content_el is None:
        content_el = working.find("body") or working

    return _converter.handle(str(content_el)).strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def scrape_site(max_pages: Optional[int] = None) -> list[dict]:
    """
    Crawl BASE_URL and all reachable internal pages (BFS).

    Returns a list of page dicts, each containing:
      - title    : str
      - url      : str
      - date     : str
      - markdown : str  (main content converted to Markdown)

    Parameters
    ----------
    max_pages : int or None
        Stop after collecting this many pages. Defaults to config.MAX_PAGES.
    """
    if max_pages is None:
        max_pages = config.MAX_PAGES or 9999

    base_domain = urlparse(config.BASE_URL).netloc.lower().lstrip("www.")
    session = _get_session()

    visited: set[str] = set()
    queue: deque[str] = deque([config.BASE_URL])
    pages: list[dict] = []

    logger.info("Crawling %s (domain: %s, max pages: %d)", config.BASE_URL, base_domain, max_pages)

    while queue and len(pages) < max_pages:
        url = queue.popleft()
        url = _normalize_url(url, config.BASE_URL)

        if url in visited:
            continue
        visited.add(url)

        logger.info("[%d/%d] Fetching: %s", len(pages) + 1, max_pages, url)
        soup = _fetch_page(session, url)
        if soup is None:
            continue

        title = _extract_title(soup)
        date = _extract_date(soup)
        markdown = _extract_content(soup)

        if len(markdown) >= 50:
            pages.append({
                "title": title,
                "url": url,
                "date": date,
                "markdown": markdown,
            })
        else:
            logger.debug("Skipping %s -- content too short.", url)

        # Enqueue new links found on this page
        for link in _collect_links(soup, url, base_domain):
            if link not in visited:
                queue.append(link)

        time.sleep(config.REQUEST_DELAY)

    logger.info("Crawl complete. %d pages collected (%d visited).", len(pages), len(visited))
    return pages


# ---------------------------------------------------------------------------
# Backward-compatible alias used by pipeline.py
# ---------------------------------------------------------------------------
def scrape_blog(max_posts: Optional[int] = None) -> list[dict]:
    """Alias of scrape_site for backward compatibility."""
    return scrape_site(max_pages=max_posts)
