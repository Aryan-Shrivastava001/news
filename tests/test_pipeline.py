import pytest
from pathlib import Path
from datetime import datetime, timezone
from src.news.rss_scraper import NewsItem
from src.news.deduplicator import NewsDeduplicator
from src.generator.script_writer import ScriptWriter
from src.generator.voiceover import VoiceoverGenerator
from src.visuals.subtitles import SubtitleGenerator
from src.visuals.lip_sync import FishLipSyncEngine

def test_deduplicator(tmp_path):
    history_file = tmp_path / "test_history.json"
    dedup = NewsDeduplicator(history_file)

    item1 = NewsItem(
        id="item_1",
        title="GTA 6 Release Date Finally Revealed",
        link="https://example.com/1",
        summary="Rockstar Games announced GTA 6 date.",
        source="IGN",
        published_at=datetime.now(timezone.utc)
    )

    assert not dedup.is_duplicate(item1)
    dedup.record_posted(item1)
    assert dedup.is_duplicate(item1)

    # Similar title should also be flagged as duplicate
    item2 = NewsItem(
        id="item_2",
        title="GTA 6 Release Date Revealed by Rockstar",
        link="https://example.com/2",
        summary="Different outlet reporting same thing.",
        source="VGC",
        published_at=datetime.now(timezone.utc)
    )
    assert dedup.is_duplicate(item2)

def test_script_writer_fallback():
    writer = ScriptWriter(api_key="")
    item = NewsItem(
        id="item_3",
        title="PlayStation Announces Massive New State of Play",
        link="https://example.com/3",
        summary="Sony will reveal several brand new PS5 games this week.",
        source="PlayStation",
        published_at=datetime.now(timezone.utc)
    )
    script = writer.generate_script(item)
    assert script.full_script is not None
    assert len(script.full_script) > 50
    assert "PlayStation" in script.full_script or "PlayStation" in script.youtube_title

def test_subtitles_generation(tmp_path):
    gen = SubtitleGenerator()
    out = tmp_path / "test.ass"
    gen.generate_ass("THIS IS A FAST PACED TEST SCRIPT FOR SHORTS", 10.0, out)
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    assert "[Script Info]" in content
    assert "THIS IS A" in content
