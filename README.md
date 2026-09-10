# Automated YouTube Shorts Gaming News Bot

An automated pipeline running every 4 hours via GitHub Actions that aggregates gaming news, generates scripts via Gemini, voices them via ElevenLabs (with Edge-TTS fallback), animates a 2-frame talking fish anchor, renders 9:16 Shorts with FFmpeg, and uploads to YouTube.

## Features
- **4-Hour Autonomous Runs**: Fits 100% within YouTube free API (9,600/10,000 units/day) and GitHub Actions free tier (600/2,000 mins/mo).
- **Multi-Source News Aggregator**: Real-time RSS feeds (VGC, IGN, GameSpot, PC Gamer, Gematsu) + Reddit (r/Games, r/GamingLeaksAndRumours).
- **No Top Header**: Clean, focused 9:16 mobile framing.
- **2-Frame Audio-Reactive Mascot**: SpongeBob-style fish news anchor at the bottom that flaps its mouth when talking and shuts on pauses.
- **Smart Audio Fallback**: ElevenLabs primary + Edge-TTS fallback when credits run out.
- **Deduplication Engine**: `posted_history.json` tracking ensures no story is repeated.

## Project Structure
```
├── .github/
│   └── workflows/
│       └── run_bot.yml       # Scheduled GitHub Action cron
├── assets/
│   ├── sprites/              # fish_open.png, fish_closed.png
│   ├── audio/                # Background music loops
│   └── backgrounds/          # Looping ambient backgrounds
├── src/
│   ├── news/                 # RSS scrapers, Reddit monitors, deduplication
│   ├── generator/            # Gemini scriptwriting & ElevenLabs/Edge-TTS
│   ├── visuals/              # Steam/article asset fetcher & fish lip-sync
│   ├── video/                # FFmpeg 9:16 compositor & subtitles
│   └── uploader/             # YouTube Data API v3 uploader
├── posted_history.json       # Cache of processed article IDs
├── requirements.txt
└── main.py
```
