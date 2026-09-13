import time
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Optional
import feedparser
import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 GamingShortsBot/1.0"
)

@dataclass
class NewsItem:
    id: str
    title: str
    link: str
    summary: str
    source: str
    published_at: datetime
    image_url: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    upvotes: int = 0
    comments: int = 0

class GamingNewsScraper:
    FEEDS = [
        {"name": "VGC", "url": "https://www.videogameschronicle.com/feed/"},
        {"name": "IGN", "url": "https://feeds.feedburner.com/ign/news"},
        {"name": "GameSpot", "url": "https://www.gamespot.com/feeds/mashup/"},
        {"name": "PC Gamer", "url": "https://www.pcgamer.com/rss/"},
        {"name": "Gematsu", "url": "https://www.gematsu.com/feed"},
        {"name": "Eurogamer", "url": "https://www.eurogamer.net/feed"},
        {"name": "Reddit r/Games", "url": "https://www.reddit.com/r/Games/hot.json"},
        {"name": "Reddit r/GamingLeaksAndRumours", "url": "https://www.reddit.com/r/GamingLeaksAndRumours/hot.json"},
        {"name": "Reddit r/gaming", "url": "https://www.reddit.com/r/gaming/hot.json"},
        {"name": "Reddit r/pcgaming", "url": "https://www.reddit.com/r/pcgaming/hot.json"},
    ]

    def __init__(self, request_timeout: int = 10):
        self.timeout = request_timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch_all(self, max_age_hours: int = 4, fallback_hours: int = 24) -> List[NewsItem]:
        """
        Fetch news from all feeds. If no news found within max_age_hours,
        falls back to fallback_hours to ensure content is always available.
        """
        all_items: List[NewsItem] = []
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=max_age_hours)

        for feed_info in self.FEEDS:
            try:
                logger.info(f"Fetching RSS feed: {feed_info['name']}")
                resp = self.session.get(feed_info["url"], timeout=self.timeout)
                if resp.status_code != 200:
                    logger.warning(f"Failed to fetch {feed_info['name']}: HTTP {resp.status_code}")
                    continue

                if ".json" in feed_info["url"]:
                    items = self._parse_reddit_json(resp.json(), feed_info["name"])
                    all_items.extend(items)
                else:
                    parsed = feedparser.parse(resp.content)
                    for entry in parsed.entries:
                        item = self._parse_entry(entry, feed_info["name"])
                        if item:
                            all_items.append(item)
            except Exception as e:
                logger.warning(f"Error reading feed {feed_info['name']}: {e}")

        # Filter by primary window
        recent_items = [i for i in all_items if i.published_at >= cutoff]
        if recent_items:
            logger.info(f"Found {len(recent_items)} news items in the last {max_age_hours} hours.")
            return sorted(recent_items, key=lambda x: x.published_at, reverse=True)

        # Fallback if news was quiet in the last 4 hours
        fallback_cutoff = now - timedelta(hours=fallback_hours)
        fallback_items = [i for i in all_items if i.published_at >= fallback_cutoff]
        logger.info(f"No items in last {max_age_hours}h; fallback returned {len(fallback_items)} items in {fallback_hours}h.")
        return sorted(fallback_items, key=lambda x: x.published_at, reverse=True)

    def _parse_reddit_json(self, data: dict, source: str) -> List[NewsItem]:
        items = []
        try:
            children = data.get("data", {}).get("children", [])
            for child in children:
                post = child.get("data", {})
                
                # Skip stickied posts
                if post.get("stickied"):
                    continue
                    
                title = post.get("title", "").strip()
                url = post.get("url", "")
                permalink = post.get("permalink", "")
                link = f"https://www.reddit.com{permalink}" if permalink else url
                
                if not title or not link:
                    continue
                    
                item_id = post.get("id", link)
                published_at = datetime.fromtimestamp(post.get("created_utc", time.time()), tz=timezone.utc)
                summary = post.get("selftext", "")
                upvotes = post.get("score", 0)
                comments = post.get("num_comments", 0)
                
                image_url = None
                if post.get("url_overridden_by_dest", "").lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                    image_url = post.get("url_overridden_by_dest")
                    
                items.append(NewsItem(
                    id=item_id,
                    title=title,
                    link=link,
                    summary=summary,
                    source=source,
                    published_at=published_at,
                    image_url=image_url,
                    upvotes=upvotes,
                    comments=comments
                ))
        except Exception as e:
            logger.debug(f"Error parsing Reddit JSON: {e}")
        return items

    def _parse_entry(self, entry, source: str) -> Optional[NewsItem]:
        try:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            if not title or not link:
                return None

            item_id = entry.get("id", link)

            # Published timestamp
            published_parsed = entry.get("published_parsed") or entry.get("updated_parsed")
            if published_parsed:
                published_at = datetime.fromtimestamp(time.mktime(published_parsed), tz=timezone.utc)
            else:
                published_at = datetime.now(timezone.utc)

            # Clean summary
            summary = entry.get("summary", "") or entry.get("description", "")
            clean_summary = self._clean_html(summary)

            # Try to grab image from RSS entry
            image_url = self._extract_image_from_entry(entry)

            tags = [t.get("term", "") for t in entry.get("tags", []) if isinstance(t, dict)]

            return NewsItem(
                id=item_id,
                title=title,
                link=link,
                summary=clean_summary,
                source=source,
                published_at=published_at,
                image_url=image_url,
                tags=tags
            )
        except Exception as e:
            logger.debug(f"Error parsing entry: {e}")
            return None

    def _extract_image_from_entry(self, entry) -> Optional[str]:
        # Check media_content
        media = entry.get("media_content", [])
        if media and isinstance(media, list):
            for m in media:
                url = m.get("url")
                if url and any(url.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                    return url

        # Check media_thumbnail
        thumbs = entry.get("media_thumbnail", [])
        if thumbs and isinstance(thumbs, list) and len(thumbs) > 0:
            return thumbs[0].get("url")

        # Check enclosures
        enclosures = entry.get("enclosures", [])
        if enclosures and isinstance(enclosures, list):
            for enc in enclosures:
                url = enc.get("href")
                if url:
                    return url

        return None

    def extract_og_image_from_url(self, url: str) -> Optional[str]:
        """Fallback to scraping og:image from the destination web page."""
        try:
            resp = self.session.get(url, timeout=6)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, "html.parser")
                og_img = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
                if og_img and og_img.get("content"):
                    return og_img["content"]
        except Exception as e:
            logger.debug(f"Could not extract og:image from {url}: {e}")
        return None

    def _clean_html(self, raw_html: str) -> str:
        if not raw_html:
            return ""
        soup = BeautifulSoup(raw_html, "html.parser")
        return " ".join(soup.get_text().split())
