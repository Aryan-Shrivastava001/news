import json
import re
import logging
from pathlib import Path
from typing import List, Optional, Tuple, Set
from .rss_scraper import NewsItem

logger = logging.getLogger(__name__)

VIRAL_KEYWORDS = [
    "gta", "grand theft auto", "playstation", "ps5", "xbox", "nintendo", "switch",
    "valve", "steam", "elden ring", "fortnite", "call of duty", "minecraft",
    "cyberpunk", "wolverine", "witcher", "bethesda", "skyrim", "fallout",
    "release date", "trailer", "gameplay", "leaked", "leak", "delayed",
    "cancelled", "free", "announcement", "state of play", "direct", "update"
]

class NewsDeduplicator:
    def __init__(self, history_file_path: Path):
        self.history_file = history_file_path
        self.posted_ids: Set[str] = set()
        self.posted_titles: List[str] = []
        self._load_history()

    def _load_history(self):
        if self.history_file.exists():
            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.posted_ids = set(data.get("posted_ids", []))
                    self.posted_titles = data.get("posted_titles", [])
            except Exception as e:
                logger.warning(f"Failed to load posted history: {e}")
                self.posted_ids = set()
                self.posted_titles = []
        else:
            self._save_history()

    def _save_history(self):
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump({
                    "posted_ids": list(self.posted_ids),
                    "posted_titles": self.posted_titles[-100:] # Keep last 100 titles
                }, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save posted history: {e}")

    def is_duplicate(self, item: NewsItem) -> bool:
        """Check if ID or similar title was already posted."""
        if item.id in self.posted_ids:
            return True

        clean_title = self._normalize_title(item.title)
        for old_title in self.posted_titles:
            clean_old = self._normalize_title(old_title)
            if self._word_overlap_ratio(clean_title, clean_old) > 0.65:
                return True
        return False

    def select_top_stories(self, items: List[NewsItem], limit: int = 5) -> List[NewsItem]:
        """
        Filters out duplicates and scores the remaining stories to pick
        the top candidates for the AI to choose from.
        """
        candidates = [item for item in items if not self.is_duplicate(item)]
        if not candidates:
            logger.info("All fetched news items were already posted.")
            return []

        scored: List[Tuple[float, NewsItem]] = []
        for item in candidates:
            score = self._calculate_viral_score(item)
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        top_items = [item for score, item in scored[:limit]]
        
        for i, item in enumerate(top_items):
            logger.info(f"Top {i+1} candidate (Score: {scored[i][0]:.1f}): {item.title} [{item.source}]")
            
        return top_items

    def record_posted(self, item: NewsItem):
        """Mark item as posted and persist to disk."""
        self.posted_ids.add(item.id)
        self.posted_titles.append(item.title)
        self._save_history()

    def _calculate_viral_score(self, item: NewsItem) -> float:
        score = 10.0
        text = f"{item.title} {item.summary}".lower()

        # Keyword boosts
        for kw in VIRAL_KEYWORDS:
            if kw in text:
                score += 5.0

        # Title length preference (punchy titles)
        if 20 <= len(item.title) <= 90:
            score += 3.0

        # Has direct image boost
        if item.image_url:
            score += 4.0

        # Math Brain (Reddit Upvotes & Comments)
        if item.upvotes > 0:
            # e.g., 5000 upvotes = +50 points
            score += min(item.upvotes / 100.0, 50.0) 
        if item.comments > 0:
            # e.g., 1000 comments = +30 points
            score += min(item.comments / 33.3, 30.0)

        return score

    @staticmethod
    def _normalize_title(title: str) -> str:
        return re.sub(r"[^a-zA-Z0-9\s]", "", title.lower()).strip()

    @staticmethod
    def _word_overlap_ratio(s1: str, s2: str) -> float:
        w1 = set(s1.split())
        w2 = set(s2.split())
        if not w1 or not w2:
            return 0.0
        intersection = w1.intersection(w2)
        return len(intersection) / min(len(w1), len(w2))
