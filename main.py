import os
import sys
import argparse
import logging
from pathlib import Path
from datetime import datetime, timezone

from src.config import (
    GEMINI_API_KEY,
    ELEVENLABS_API_KEY,
    ELEVENLABS_VOICE_ID,
    SPRITES_DIR,
    AUDIO_DIR,
    OUTPUT_DIR,
    CACHE_FILE,
    NEWS_WINDOW_HOURS
)
from src.news import GamingNewsScraper, NewsDeduplicator, NewsItem
from src.generator import ScriptWriter, VoiceoverGenerator
from src.visuals import AssetFetcher, FishLipSyncEngine, SubtitleGenerator
from src.visuals.generate_mascot import create_default_fish_sprites
from src.video import VideoCompositor
from src.uploader import YouTubeUploader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("GamingShortsBot")

def run_pipeline(dry_run: bool = False, force_topic: str = None) -> bool:
    logger.info("=== Starting Automated Gaming Shorts Pipeline ===")

    # Ensure fish sprites exist
    fish_closed = SPRITES_DIR / "fish_closed.png"
    fish_open = SPRITES_DIR / "fish_open.png"
    if not fish_closed.exists() or not fish_open.exists():
        logger.info("Mascot sprites not found. Generating default fish news anchor sprites...")
        create_default_fish_sprites(SPRITES_DIR)

    # 1. Fetch & Select News Story
    dedup = NewsDeduplicator(CACHE_FILE)

    if force_topic:
        logger.info(f"Using forced topic: {force_topic}")
        chosen_story = NewsItem(
            id=f"forced_{int(datetime.now().timestamp())}",
            title=force_topic,
            link="https://example.com/gaming-news",
            summary=f"Massive announcements and breaking updates regarding {force_topic}.",
            source="Manual Trigger",
            published_at=datetime.now(timezone.utc)
        )
    else:
        scraper = GamingNewsScraper()
        items = scraper.fetch_all(max_age_hours=NEWS_WINDOW_HOURS)
        if not items:
            logger.warning("No news items retrieved from any feed.")
            return False

        chosen_story = dedup.select_best_story(items)
        if not chosen_story:
            logger.info("No new unposted stories found in this run cycle. Exiting gracefully.")
            return True

    logger.info(f"Target News Story: '{chosen_story.title}' ({chosen_story.source})")

    # Timestamped working directory
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = OUTPUT_DIR / f"run_{run_id}"
    work_dir.mkdir(parents=True, exist_ok=True)

    # 2. Generate Script via Gemini
    writer = ScriptWriter(api_key=GEMINI_API_KEY)
    script_data = writer.generate_script(chosen_story)
    logger.info(f"Script Generated. Game: '{script_data.game_name}' | Title: '{script_data.youtube_title}'")
    logger.info(f"Spoken Script: {script_data.full_script}")

    # 3. Voiceover (ElevenLabs with Edge-TTS Fallback)
    voice_gen = VoiceoverGenerator(
        elevenlabs_key=ELEVENLABS_API_KEY,
        elevenlabs_voice_id=ELEVENLABS_VOICE_ID
    )
    voice_audio = work_dir / "voiceover.mp3"
    voice_gen.generate(script_data.full_script, voice_audio)

    # 4. Fetch Visuals (Article Image + Steam Screenshots)
    article_img = chosen_story.image_url
    if not article_img and chosen_story.link:
        logger.info(f"Extracting og:image from article web page: {chosen_story.link}")
        scraper = GamingNewsScraper()
        article_img = scraper.extract_og_image_from_url(chosen_story.link)

    fetcher = AssetFetcher()
    images = fetcher.fetch_game_visuals(
        article_image_url=article_img,
        game_name=script_data.game_name,
        target_dir=work_dir
    )
    logger.info(f"Gathered {len(images)} visual asset(s).")

    # 5. Fish Anchor 2-Frame Lip-Sync Video
    lip_sync = FishLipSyncEngine(closed_sprite=fish_closed, open_sprite=fish_open)
    fish_video = work_dir / "fish_anchor.mov"
    lip_sync.render_transparent_anchor_video(voice_audio, fish_video)

    # 6. Dynamic Subtitles
    audio_dur = lip_sync.get_audio_duration(voice_audio)
    sub_gen = SubtitleGenerator()
    subtitles_path = work_dir / "subtitles.ass"
    sub_gen.generate_ass(script_data.full_script, audio_dur, subtitles_path)

    # 7. Video Assembly (FFmpeg - Clean 9:16 without top header)
    compositor = VideoCompositor()
    final_video = work_dir / "short_ready.mp4"
    bg_music = AUDIO_DIR / "bg_music.mp3"
    compositor.assemble_short(
        images=images,
        voiceover_audio=voice_audio,
        fish_anchor_video=fish_video,
        subtitles_ass=subtitles_path,
        output_mp4=final_video,
        bg_music=bg_music if bg_music.exists() else None
    )

    logger.info(f"Video Production Complete: {final_video}")

    # 8. Upload to YouTube
    uploader = YouTubeUploader()
    if dry_run or not uploader.is_configured():
        logger.info("Upload Mode: DRY RUN / SIMULATED. Video produced and stored locally.")
        video_id = "DRY_RUN_SUCCESS"
    else:
        video_id = uploader.upload_short(
            video_path=final_video,
            title=script_data.youtube_title,
            description=script_data.youtube_description,
            tags=script_data.tags
        )

    # 9. Record to cache so it never repeats
    if video_id:
        dedup.record_posted(chosen_story)
        logger.info("News item successfully marked as posted.")

    logger.info("=== Pipeline Execution Finished Successfully ===")
    return True

def main():
    parser = argparse.ArgumentParser(description="Automated YouTube Shorts Gaming News Bot")
    parser.add_argument("--dry-run", action="store_true", help="Build video without uploading to YouTube")
    parser.add_argument("--force-topic", type=str, default=None, help="Force a specific gaming topic for testing")
    args = parser.parse_args()

    success = run_pipeline(dry_run=args.dry_run, force_topic=args.force_topic)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()
