import os
import asyncio
import logging
from pathlib import Path
from typing import Optional
import requests
import edge_tts
from ..config import DEFAULT_EDGE_TTS_VOICE

logger = logging.getLogger(__name__)

class VoiceoverGenerator:
    def __init__(self, elevenlabs_key: str = "", elevenlabs_voice_id: str = "ErXwobaYiN019PkySvjV"):
        self.elevenlabs_key = elevenlabs_key
        self.voice_id = elevenlabs_voice_id

    def generate(self, text: str, output_path: Path) -> Path:
        """
        Synthesizes speech from text. Tries ElevenLabs first.
        If ElevenLabs key is missing, invalid, or exhausts quota,
        it automatically falls back to Edge-TTS.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if self.elevenlabs_key and self.elevenlabs_key != "your_elevenlabs_api_key_here":
            try:
                success = self._generate_elevenlabs(text, output_path)
                if success:
                    return output_path
            except Exception as e:
                logger.warning(f"ElevenLabs generation failed: {e}. Falling back to Edge-TTS.")

        # Fallback to Edge-TTS
        logger.info("Using Edge-TTS for voiceover synthesis.")
        self._generate_edge_tts(text, output_path)
        return output_path

    def _generate_elevenlabs(self, text: str, output_path: Path) -> bool:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
        headers = {
            "xi-api-key": self.elevenlabs_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.85,
                "style": 0.35,
                "use_speaker_boost": True
            }
        }

        resp = requests.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(resp.content)
            logger.info(f"ElevenLabs audio saved successfully: {output_path}")
            return True
        else:
            logger.warning(f"ElevenLabs returned HTTP {resp.status_code}: {resp.text}")
            return False

    def _generate_edge_tts(self, text: str, output_path: Path):
        """Asynchronous Edge-TTS generator run synchronously via asyncio."""
        async def _run():
            # slightly boosted rate for energetic gaming news
            communicate = edge_tts.Communicate(text, voice=DEFAULT_EDGE_TTS_VOICE, rate="+8%")
            await communicate.save(str(output_path))

        asyncio.run(_run())
        logger.info(f"Edge-TTS audio saved successfully: {output_path}")
