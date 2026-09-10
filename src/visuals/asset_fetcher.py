import os
import re
import logging
from pathlib import Path
from typing import List, Optional
import requests
from PIL import Image, ImageDraw, ImageFilter
from ..config import BACKGROUNDS_DIR

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"

class AssetFetcher:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch_game_visuals(self, article_image_url: Optional[str], game_name: str, target_dir: Path) -> List[Path]:
        """
        Gathers 1-3 high quality images for the video:
        1. Direct article hero image (if available)
        2. Official Steam store screenshots
        3. Fallback procedural gaming card if no images download successfully
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        downloaded_paths: List[Path] = []

        # 1. Download article image
        if article_image_url:
            art_path = target_dir / "article_hero.jpg"
            if self._download_image(article_image_url, art_path):
                downloaded_paths.append(art_path)

        # 2. Fetch Steam screenshots for the game
        if len(downloaded_paths) < 2 and game_name:
            steam_screenshots = self._fetch_steam_screenshots(game_name, target_dir)
            downloaded_paths.extend(steam_screenshots)

        # 3. Fallback if no images succeeded
        if not downloaded_paths:
            logger.info("No remote images fetched; generating high-tech procedural gaming backdrop.")
            fallback_path = target_dir / "procedural_backdrop.jpg"
            self._create_procedural_backdrop(game_name or "GAMING NEWS", fallback_path)
            downloaded_paths.append(fallback_path)

        return downloaded_paths

    def _download_image(self, url: str, save_path: Path) -> bool:
        try:
            resp = self.session.get(url, timeout=10)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(save_path, "wb") as f:
                    f.write(resp.content)
                # Verify valid image with Pillow
                with Image.open(save_path) as img:
                    img.verify()
                return True
        except Exception as e:
            logger.debug(f"Failed to download image {url}: {e}")
            if save_path.exists():
                save_path.unlink()
        return False

    def _fetch_steam_screenshots(self, game_name: str, target_dir: Path) -> List[Path]:
        results: List[Path] = []
        try:
            clean_name = re.sub(r"[^a-zA-Z0-9\s]", "", game_name).strip()
            search_url = f"https://store.steampowered.com/api/storesearch/?term={clean_name}&l=english&cc=US"
            resp = self.session.get(search_url, timeout=6)
            if resp.status_code != 200:
                return results

            data = resp.json()
            items = data.get("items", [])
            if not items:
                return results

            app_id = items[0].get("id")
            if not app_id:
                return results

            # App details
            details_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
            det_resp = self.session.get(details_url, timeout=6)
            if det_resp.status_code != 200:
                return results

            det_data = det_resp.json()
            app_info = det_data.get(str(app_id), {}).get("data", {})
            screenshots = app_info.get("screenshots", [])

            for idx, s in enumerate(screenshots[:2]):
                img_url = s.get("path_full")
                if img_url:
                    save_path = target_dir / f"steam_screen_{idx+1}.jpg"
                    if self._download_image(img_url, save_path):
                        results.append(save_path)

        except Exception as e:
            logger.debug(f"Error querying Steam API: {e}")

        return results

    def _create_procedural_backdrop(self, title: str, output_path: Path):
        """Generates a stylish 1920x1080 neon gaming background card as safe fallback."""
        width, height = 1920, 1080
        img = Image.new("RGB", (width, height), (15, 18, 30))
        draw = ImageDraw.Draw(img)

        # Gradient effect
        for y in range(height):
            ratio = y / height
            r = int(15 + 20 * ratio)
            g = int(18 + 15 * ratio)
            b = int(35 + 40 * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        # Geometric gaming grid lines
        grid_color = (40, 50, 85)
        for x in range(0, width, 80):
            draw.line([(x, 0), (x, height)], fill=grid_color, width=1)
        for y in range(0, height, 80):
            draw.line([(0, y), (width, y)], fill=grid_color, width=1)

        # Subtle vignette glow
        draw.rectangle([100, 100, width - 100, height - 100], outline=(70, 120, 220), width=3)
        img.save(output_path, "JPEG", quality=90)
