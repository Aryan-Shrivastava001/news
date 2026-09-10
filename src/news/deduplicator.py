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

    def select_best_story(self, items: List[NewsItem]) -> Optional[NewsItem]:
        """
        Filters out duplicates and scores the remaining stories to pick
        the most viral candidate for the next Short.
        """
        candidates = [item for item in items if not self.is_duplicate(item)]
        if not candidates:
            logger.info("All fetched news items were already posted.")
            return None

        scored: List[Tuple[float, NewsItem]] = []
        for item in candidates:
            score = self._calculate_viral_score(item)
            scored.append((score, item))

        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_item = scored[0]
        logger.info(f"Selected top story (Score: {best_score:.1f}): {best_item.title} [{best_item.source}]")
        return best_item

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
