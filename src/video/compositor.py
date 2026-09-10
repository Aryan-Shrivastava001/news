import os
import subprocess
import logging
from pathlib import Path
from typing import List, Optional
from ..config import VIDEO_WIDTH, VIDEO_HEIGHT, VIDEO_FPS

logger = logging.getLogger(__name__)

class VideoCompositor:
    def __init__(self, width: int = VIDEO_WIDTH, height: int = VIDEO_HEIGHT, fps: int = VIDEO_FPS):
        self.width = width
        self.height = height
        self.fps = fps

    def get_duration(self, file_path: Path) -> float:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(file_path)
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return float(res.stdout.strip())
        except Exception as e:
            logger.warning(f"Failed to probe duration for {file_path}: {e}")
            return 35.0

    def assemble_short(
        self,
        images: List[Path],
        voiceover_audio: Path,
        fish_anchor_video: Path,
        subtitles_ass: Optional[Path],
        output_mp4: Path,
        bg_music: Optional[Path] = None
    ) -> Path:
        """
        Assembles the final 9:16 YouTube Short using FFmpeg:
        - Layer 1 (Background): Cinematic blurred & zoomed game backdrop.
        - Layer 2 (Center Card): Crisp 16:9 game screenshot/artwork with glowing border.
        - Layer 3 (Subtitles): Bold yellow kinetic captions above the anchor.
        - Layer 4 (Anchor Mascot): 2-frame talking fish anchor at the bottom.
        - Audio: Voiceover synchronized with low-volume background music.
        - NO TOP HEADER BANNER (per user's request).
        """
        output_mp4.parent.mkdir(parents=True, exist_ok=True)
        duration = self.get_duration(voiceover_audio) + 0.5 # tiny padding

        primary_image = images[0]

        # Escape path for FFmpeg subtitles filter on Windows
        sub_filter = ""
        if subtitles_ass and subtitles_ass.exists():
            clean_sub_path = subtitles_ass.as_posix().replace(":", "\\:")
            sub_filter = f",ass='{clean_sub_path}'"

        # Build FFmpeg command with complex filter graph
        # Inputs:
        # 0: primary image
        # 1: fish anchor video (transparent quicktime animation)
        # 2: voiceover audio
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1", "-t", f"{duration:.2f}", "-i", str(primary_image),
            "-i", str(fish_anchor_video),
            "-i", str(voiceover_audio),
        ]

        if bg_music and bg_music.exists():
            cmd.extend(["-stream_loop", "-1", "-i", str(bg_music)])

        # Filter Graph:
        # [0:v] split into background (blurred, fills 1080x1920) and foreground (sharp 16:9 card, width 1000)
        filter_parts = [
            # Background layer: scale to fill 1080x1920, crop, heavy blur, subtle dim
            f"[0:v]scale={self.width}:{self.height}:force_original_aspect_ratio=increase,crop={self.width}:{self.height},boxblur=25:5,eq=brightness=-0.15[bg]",
            # Foreground card: scale to width 1000, keep aspect ratio
            "[0:v]scale=1000:-1:force_original_aspect_ratio=decrease[fg]",
            # Place foreground card centered vertically in the upper half (y=380)
            "[bg][fg]overlay=(W-w)/2:380[base_scene]",
            # Overlay the fish anchor at bottom center
            f"[1:v]scale=450:450[fish]",
            f"[base_scene][fish]overlay=(W-w)/2:{self.height-480}[with_fish]"
        ]

        if sub_filter:
            filter_parts.append(f"[with_fish]null{sub_filter}[vout]")
            v_map = "[vout]"
        else:
            v_map = "[with_fish]"

        # Audio mixing
        if bg_music and bg_music.exists():
            filter_parts.append("[3:a]volume=0.10[bgm];[2:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]")
            a_map = "[aout]"
        else:
            a_map = "2:a"

        cmd.extend([
            "-filter_complex", ";".join(filter_parts),
            "-map", v_map,
            "-map", a_map,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "20",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-r", str(self.fps),
            "-t", f"{duration:.2f}",
            str(output_mp4)
        ])

        logger.info(f"Rendering YouTube Short to {output_mp4} ({duration:.1f}s)...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            logger.error(f"FFmpeg render error: {res.stderr}")
            raise RuntimeError(f"FFmpeg failed with exit code {res.returncode}: {res.stderr[-400:]}")

        logger.info(f"Render complete! Video saved: {output_mp4} ({output_mp4.stat().st_size / (1024*1024):.2f} MB)")
        return output_mp4
