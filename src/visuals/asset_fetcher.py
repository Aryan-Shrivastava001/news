import os
import re
import logging
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field
import requests
from bs4 import BeautifulSoup
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36"

@dataclass
class MediaAssets:
    images: List[Path] = field(default_factory=list)
    videos: List[Path] = field(default_factory=list)

class AssetFetcher:
    def __init__(self, session: Optional[requests.Session] = None):
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    def fetch_game_visuals(self, article_url: Optional[str], article_image_url: Optional[str], game_name: str, target_dir: Path) -> MediaAssets:
        """
        Gathers multiple high-quality media items for a dynamic slideshow:
        1. Direct article hero image
        2. Extracted article inline images
        3. Steam screenshots
        4. Steam gameplay trailer
        """
        target_dir.mkdir(parents=True, exist_ok=True)
        assets = MediaAssets()

        # 1. Download article hero image
        if article_image_url:
            art_path = target_dir / "article_hero.jpg"
            if self._download_file(article_image_url, art_path, is_image=True):
                assets.images.append(art_path)

        # 2. Extract additional images from the article page
        if article_url:
            extra_images = self._extract_article_images(article_url, target_dir)
            assets.images.extend(extra_images)

        # 3. Fetch Steam screenshots & trailer
        if game_name:
            steam_images, steam_videos = self._fetch_steam_assets(game_name, target_dir)
            assets.images.extend(steam_images)
            assets.videos.extend(steam_videos)

        # Ensure we have a reasonable limit (e.g. max 8 images) to prevent massive memory usage
        assets.images = assets.images[:8]

        # 4. Fallback if no images succeeded
        if not assets.images:
            logger.info("No remote images fetched; generating high-tech procedural gaming backdrop.")
            fallback_path = target_dir / "procedural_backdrop.jpg"
            self._create_procedural_backdrop(game_name or "GAMING NEWS", fallback_path)
            assets.images.append(fallback_path)

        return assets

    def _download_file(self, url: str, save_path: Path, is_image: bool = True) -> bool:
        try:
            resp = self.session.get(url, timeout=10, stream=True)
            if resp.status_code == 200:
                with open(save_path, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                if is_image:
                    with Image.open(save_path) as img:
                        img.verify()
                return True
        except Exception as e:
            logger.debug(f"Failed to download {url}: {e}")
            if save_path.exists():
                save_path.unlink()
        return False

    def _extract_article_images(self, url: str, target_dir: Path) -> List[Path]:
        results = []
        try:
            resp = self.session.get(url, timeout=8)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.content, "html.parser")
                imgs = soup.find_all("img")
                count = 0
                for img in imgs:
                    src = img.get("src") or img.get("data-src")
                    if not src: continue
                    if src.startswith("//"): src = "https:" + src
                    elif src.startswith("/"):
                        from urllib.parse import urlparse
                        parsed = urlparse(url)
                        src = f"{parsed.scheme}://{parsed.netloc}{src}"
                    
                    if any(ext in src.lower() for ext in [".jpg", ".jpeg", ".png", ".webp"]):
                        save_path = target_dir / f"article_extra_{count}.jpg"
                        if self._download_file(src, save_path, is_image=True):
                            # Validate size to skip tiny thumbnails/icons
                            with Image.open(save_path) as im:
                                if im.width >= 400 and im.height >= 250:
                                    results.append(save_path)
                                    count += 1
                                else:
                                    save_path.unlink()
                    if count >= 3:
                        break
        except Exception as e:
            logger.debug(f"Error scraping article images: {e}")
        return results

    def _fetch_steam_assets(self, game_name: str, target_dir: Path) -> tuple[List[Path], List[Path]]:
        images = []
        videos = []
        try:
            clean_name = re.sub(r"[^a-zA-Z0-9\s]", "", game_name).strip()
            search_url = f"https://store.steampowered.com/api/storesearch/?term={clean_name}&l=english&cc=US"
            resp = self.session.get(search_url, timeout=6)
            if resp.status_code != 200: return images, videos
            
            items = resp.json().get("items", [])
            if not items: return images, videos
            
            app_id = items[0].get("id")
            if not app_id: return images, videos
            
            # App details
            details_url = f"https://store.steampowered.com/api/appdetails?appids={app_id}"
            det_resp = self.session.get(details_url, timeout=6)
            if det_resp.status_code != 200: return images, videos
            
            app_info = det_resp.json().get(str(app_id), {}).get("data", {})
            
            # Screenshots (up to 4)
            screenshots = app_info.get("screenshots", [])
            for idx, s in enumerate(screenshots[:4]):
                img_url = s.get("path_full")
                if img_url:
                    save_path = target_dir / f"steam_screen_{idx+1}.jpg"
                    if self._download_file(img_url, save_path, is_image=True):
                        images.append(save_path)

            # Trailer (1 if available)
            movies = app_info.get("movies", [])
            if movies:
                # prefer 480p mp4/webm to keep processing fast
                video_url = movies[0].get("webm", {}).get("480") or movies[0].get("mp4", {}).get("480")
                if video_url:
                    video_url = video_url.split("?")[0] # clean query params
                    vid_path = target_dir / "steam_trailer.mp4"
                    if self._download_file(video_url, vid_path, is_image=False):
                        videos.append(vid_path)

        except Exception as e:
            logger.debug(f"Error querying Steam API: {e}")
            
        return images, videos

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
