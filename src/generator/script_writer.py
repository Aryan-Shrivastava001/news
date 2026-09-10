import json
import re
import logging
from dataclasses import dataclass
from typing import List, Optional
import requests
from ..news.rss_scraper import NewsItem

logger = logging.getLogger(__name__)

@dataclass
class ShortScript:
    game_name: str
    youtube_title: str
    full_script: str
    youtube_description: str
    tags: List[str]
    hook: str
    outro: str

class ScriptWriter:
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Gemini 2.5/2.0 Flash REST endpoint
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"

    def generate_script(self, item: NewsItem) -> ShortScript:
        """
        Generate a high-retention 35-45 second script for YouTube Shorts.
        If no API key is provided, falls back to a high-quality template script.
        """
        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            logger.warning("No GEMINI_API_KEY provided; using dynamic fallback script generator.")
            return self._generate_fallback(item)

        prompt = f"""
You are a top gaming news producer writing a viral YouTube Short script (under 50 seconds, 75-90 words max).
Write the script to be spoken by a lively, fast-paced gaming news anchor.

NEWS TOPIC:
Title: {item.title}
Source: {item.source}
Summary: {item.summary}

RULES:
1. Script length: EXACTLY between 75 and 90 words.
2. Hook: The first sentence must be an explosive, immediate hook (NO "Hey guys", NO "Welcome back").
3. Content: 2-3 fast facts about what actually happened.
4. Outro: End with an engaging question that forces viewers to comment.
5. PURE SPOKEN TEXT: Do NOT include parenthetical sound cues, asterisks, brackets, or stage directions (e.g. do NOT write "(laughs)" or "[Music]"). Only write the words to be spoken.
6. JSON FORMAT: Return strictly valid JSON with no markdown backticks or wrappers.

JSON SCHEMA:
{{
  "game_name": "Primary game or company name (e.g. GTA 6, PlayStation 5, Nintendo)",
  "youtube_title": "Catchy YouTube Short title under 60 chars with 1 emoji",
  "hook": "First sentence hook",
  "full_script": "The complete spoken script without stage directions",
  "outro": "The ending call to comment",
  "youtube_description": "2 sentence description with #shorts #gaming hashtags",
  "tags": ["shorts", "gaming", "news", "game_name_here"]
}}
"""

        try:
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "temperature": 0.7,
                    "responseMimeType": "application/json"
                }
            }
            resp = requests.post(self.endpoint, json=payload, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                clean_json = self._clean_json_string(text)
                parsed = json.loads(clean_json)

                return ShortScript(
                    game_name=parsed.get("game_name", "Gaming News"),
                    youtube_title=parsed.get("youtube_title", f"{item.title} #shorts")[:90],
                    full_script=parsed.get("full_script", "").strip(),
                    youtube_description=parsed.get("youtube_description", f"{item.title}\n\n#shorts #gamingnews"),
                    tags=parsed.get("tags", ["shorts", "gaming", "news"]),
                    hook=parsed.get("hook", ""),
                    outro=parsed.get("outro", "")
                )
            else:
                logger.error(f"Gemini API error (HTTP {resp.status_code}): {resp.text}")
        except Exception as e:
            logger.error(f"Error calling Gemini API: {e}")

        return self._generate_fallback(item)

    def _generate_fallback(self, item: NewsItem) -> ShortScript:
        """Create a clean, punchy script without needing an active API key."""
        clean_title = re.sub(r"\[.*?\]|\(.*?\)", "", item.title).strip()
        words = item.summary.split()
        summary_snippet = " ".join(words[:45]) if words else "Huge news just dropped across the gaming world."
        
        # Extract game/subject guess from title
        parts = clean_title.split(":")
        game_guess = parts[0].strip() if len(parts) > 1 else clean_title.split()[0]

        script = (
            f"Breaking gaming alert! {clean_title}. "
            f"{summary_snippet} "
            f"This is causing major waves right now. Are you hyped for this, or did they drop the ball? "
            f"Drop your thoughts in the comments and subscribe for 4-hour gaming drops!"
        )

        return ShortScript(
            game_name=game_guess,
            youtube_title=f"{clean_title[:50]}! 🎮 #shorts",
            full_script=script,
            youtube_description=f"{item.title}\n\nSource: {item.source}\n#shorts #gaming #gamingnews #{game_guess.replace(' ', '')}",
            tags=["shorts", "gaming", "gamingnews", game_guess.lower()],
            hook=f"Breaking gaming alert! {clean_title}.",
            outro="Drop your thoughts in the comments and subscribe!"
        )

    @staticmethod
    def _clean_json_string(raw: str) -> str:
        raw = raw.strip()
        if raw.startswith("```json"):
            raw = raw[7:]
        elif raw.startswith("```"):
            raw = raw[3:]
        if raw.endswith("```"):
            raw = raw[:-3]
        return raw.strip()
