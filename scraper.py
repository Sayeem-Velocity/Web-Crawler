"""
scraper.py
----------
Fetches blog posts from the Python blog and converts HTML to Markdown.
Each post is returned as a dict with title, date, url, and markdown body.
"""

import logging
import time
from typing import Optional
from urllib.parse import urljoin

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


def _get_session() -> requests.Session:
    """Return a requests session with standard headers."""
    session = requests.Session()
    session.headers.update({
        "User-Agent": config.USER_AGENT,
        "Accept": "text/html,application/xhtml+xml",
        "Accept-Language": "en-US,en;q=0.9",
    })
    return session


def _fetch_page(session: requests.Session, url: str) -> Optional[BeautifulSoup]:
    """Fetch a single page and return a BeautifulSoup object, or None on failure."""
    try:
        response = session.get(url, timeout=config.REQUEST_TIMEOUT)
        response.raise_for_status()
        return BeautifulSoup(response.text, "lxml")
    except requests.RequestException as exc:
        logger.error("Failed to fetch %s: %s", url, exc)
        return None


def _parse_post_links(soup: BeautifulSoup) -> list[dict]:
    """Extract post metadata (title, url, date) from a blog listing page."""
    posts = []
    for entry in soup.select("div.post"):
        title_tag = entry.select_one("h3.post-title a") or entry.select_one("h3.post-title")
        date_tag = entry.select_one("h2.date-header span") or entry.select_one("span.post-timestamp")

        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        url = title_tag.get("href", "")
        date_text = date_tag.get_text(strip=True) if date_tag else "unknown"

        posts.append({
            "title": title,
            "url": url,
            "date": date_text,
        })
    return posts


def _get_next_page_url(soup: BeautifulSoup) -> Optional[str]:
    """Return the URL for the next (older posts) page, or None."""
    older_link = soup.select_one("a.blog-pager-older-link")
    if older_link and older_link.get("href"):
        return older_link["href"]
    return None


def _fetch_post_body(session: requests.Session, post_url: str) -> str:
    """Fetch a single post page and return its body as Markdown."""
    soup = _fetch_page(session, post_url)
    if soup is None:
        return ""

    body_div = soup.select_one("div.post-body")
    if body_div is None:
        body_div = soup.select_one("div.post")

    if body_div is None:
        return ""

    html_content = str(body_div)
    markdown = _converter.handle(html_content)
    return markdown.strip()


def scrape_blog(max_posts: Optional[int] = None) -> list[dict]:
    """
    Crawl the Python blog and return a list of post dicts.

    Each dict contains:
      - title: str
      - url: str
      - date: str
      - markdown: str  (body converted to Markdown)

    Parameters
    ----------
    max_posts : int or None
        Stop after collecting this many posts. None means collect all reachable posts.
    """
    if max_posts is None:
        max_posts = config.MAX_POSTS or 9999

    session = _get_session()
    all_posts: list[dict] = []
    current_url = config.BASE_URL
    page_num = 0

    logger.info("Starting crawl at %s (max %d posts)", config.BASE_URL, max_posts)

    while current_url and len(all_posts) < max_posts:
        page_num += 1
        logger.info("Fetching listing page %d: %s", page_num, current_url)

        soup = _fetch_page(session, current_url)
        if soup is None:
            break

        page_posts = _parse_post_links(soup)
        if not page_posts:
            logger.info("No posts found on page %d, stopping.", page_num)
            break

        for post in page_posts:
            if len(all_posts) >= max_posts:
                break

            if not post["url"]:
                # Post body is inline on the listing page; grab it from the entry
                entry = soup.find("h3", string=post["title"])
                if entry:
                    parent = entry.find_parent("div", class_="post")
                    if parent:
                        body_div = parent.select_one("div.post-body")
                        post["markdown"] = _converter.handle(str(body_div)).strip() if body_div else ""
                    else:
                        post["markdown"] = ""
                else:
                    post["markdown"] = ""
            else:
                logger.info("  Fetching post: %s", post["title"])
                post["markdown"] = _fetch_post_body(session, post["url"])
                time.sleep(config.REQUEST_DELAY)

            all_posts.append(post)

        current_url = _get_next_page_url(soup)
        if current_url:
            time.sleep(config.REQUEST_DELAY)

    logger.info("Crawl complete. Collected %d posts.", len(all_posts))
    return all_posts
