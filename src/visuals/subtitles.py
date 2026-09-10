import re
import logging
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)

class SubtitleGenerator:
    """
    Generates high-impact, kinetic ASS (Advanced SubStation Alpha) subtitles
    customized for mobile YouTube Shorts.
    - Chunks text into 2-4 word bursts.
    - Bright yellow & white text with thick black outline.
    - Positioned in the lower-middle, just above the fish news anchor.
    """

    def __init__(self, font_name: str = "Arial", font_size: int = 22):
        self.font_name = font_name
        self.font_size = font_size

    def generate_ass(self, script_text: str, total_duration: float, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        chunks = self._chunk_words(script_text)
        if not chunks:
            chunks = ["BREAKING GAMING UPDATE"]

        time_per_chunk = total_duration / max(len(chunks), 1)

        ass_header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: ShortsDefault,{self.font_name},{self.font_size * 2},&H0000FFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,6,3,2,60,60,620,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

        events = []
        for idx, chunk in enumerate(chunks):
            start_sec = idx * time_per_chunk
            end_sec = min((idx + 1) * time_per_chunk, total_duration)

            start_str = self._format_ass_time(start_sec)
            end_str = self._format_ass_time(end_sec)

            # Uppercase for punchiness, highlight key words
            clean_text = chunk.upper().strip()
            events.append(f"Dialogue: 0,{start_str},{end_str},ShortsDefault,,0,0,0,,{clean_text}")

        full_content = ass_header + "\n".join(events) + "\n"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(full_content)

        logger.info(f"Generated {len(chunks)} ASS subtitle bursts at {output_path}")
        return output_path

    def _chunk_words(self, text: str, words_per_chunk: int = 3) -> List[str]:
        clean = re.sub(r"\s+", " ", text).strip()
        words = clean.split()
        chunks = []
        for i in range(0, len(words), words_per_chunk):
            chunks.append(" ".join(words[i:i + words_per_chunk]))
        return chunks

    @staticmethod
    def _format_ass_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        whole_secs = int(secs)
        centis = int(round((secs - whole_secs) * 100))
        if centis >= 100:
            centis = 99
        return f"{hours:01d}:{minutes:02d}:{whole_secs:02d}.{centis:02d}"
