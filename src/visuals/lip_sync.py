import os
import wave
import subprocess
import logging
from pathlib import Path
from typing import List, Tuple
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

class FishLipSyncEngine:
    """
    Audio-reactive 2-frame lip sync engine for the fish news anchor.
    Calculates RMS volume for each video frame.
    - If volume < threshold: Mouth CLOSED (silence/breathing/pause)
    - If volume >= threshold: Mouth FLAPPING (alternates open/closed at ~5 Hz)
    """

    def __init__(self, closed_sprite: Path, open_sprite: Path, fps: int = 30):
        self.closed_sprite = closed_sprite
        self.open_sprite = open_sprite
        self.fps = fps

    def get_audio_duration(self, audio_path: Path) -> float:
        cmd = [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1", str(audio_path)
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return float(res.stdout.strip())
        except Exception:
            return 35.0 # default estimate

    def generate_mouth_schedule(self, audio_path: Path, threshold_factor: float = 0.15) -> List[Path]:
        """
        Extracts PCM audio, computes RMS per frame, and outputs a list of
        which sprite (open vs closed) to show for each video frame.
        """
        temp_wav = audio_path.parent / "temp_mono.wav"
        # Convert audio to mono 16kHz PCM WAV for instant NumPy reading
        cmd = [
            "ffmpeg", "-y", "-i", str(audio_path),
            "-ac", "1", "-ar", "16000", "-f", "wav", str(temp_wav)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        with wave.open(str(temp_wav), "rb") as wf:
            sample_rate = wf.getframerate()
            num_samples = wf.getnframes()
            raw_bytes = wf.readframes(num_samples)
            samples = np.frombuffer(raw_bytes, dtype=np.int16).astype(np.float32)

        if temp_wav.exists():
            temp_wav.unlink()

        # Compute RMS per frame window
        samples_per_frame = int(sample_rate / self.fps)
        total_frames = int(np.ceil(num_samples / samples_per_frame))

        max_val = np.max(np.abs(samples)) if len(samples) > 0 else 1.0
        normalized = samples / (max_val + 1e-6)

        rms_list = []
        for f in range(total_frames):
            start = f * samples_per_frame
            end = min(start + samples_per_frame, len(normalized))
            frame_chunk = normalized[start:end]
            if len(frame_chunk) > 0:
                rms = np.sqrt(np.mean(frame_chunk ** 2))
            else:
                rms = 0.0
            rms_list.append(rms)

        # Baseline noise threshold
        avg_rms = np.mean(rms_list)
        silence_threshold = avg_rms * threshold_factor

        schedule: List[Path] = []
        # Flap cycle: 3 frames open, 3 frames closed during speech = 5 flaps/sec at 30 fps
        flap_counter = 0

        for rms in rms_list:
            if rms > silence_threshold:
                # Talking
                is_open = (flap_counter % 6) < 3
                schedule.append(self.open_sprite if is_open else self.closed_sprite)
                flap_counter += 1
            else:
                # Silence / pause
                schedule.append(self.closed_sprite)
                flap_counter = 0

        logger.info(f"Generated lip-sync schedule for {len(schedule)} frames ({len(schedule)/self.fps:.1f}s)")
        return schedule

    def render_transparent_anchor_video(self, audio_path: Path, output_video: Path, target_size: Tuple[int, int] = (1080, 1080)) -> Path:
        """
        Renders a transparent QuickTime Animation (RLE) or PNG sequence video
        that can be seamlessly overlaid onto the final video using FFmpeg.
        """
        schedule = self.generate_mouth_schedule(audio_path)
        frames_dir = output_video.parent / "temp_fish_frames"
        frames_dir.mkdir(parents=True, exist_ok=True)

        # Cache pre-resized sprites
        img_closed = Image.open(self.closed_sprite).convert("RGBA").resize(target_size, Image.Resampling.LANCZOS)
        img_open = Image.open(self.open_sprite).convert("RGBA").resize(target_size, Image.Resampling.LANCZOS)

        saved_closed = frames_dir / "cache_closed.png"
        saved_open = frames_dir / "cache_open.png"
        img_closed.save(saved_closed)
        img_open.save(saved_open)

        # Write FFmpeg concat demuxer file for zero-disk frame overhead
        concat_list_path = frames_dir / "frames.txt"
        with open(concat_list_path, "w", encoding="utf-8") as f:
            for sprite_path in schedule:
                target = saved_open if sprite_path == self.open_sprite else saved_closed
                f.write(f"file '{target.name}'\n")
                f.write(f"duration {1.0 / self.fps:.6f}\n")

        # Encode transparent video using qtrle
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat", "-safe", "0", "-i", str(concat_list_path),
            "-c:v", "qtrle",
            "-pix_fmt", "argb",
            "-r", str(self.fps),
            str(output_video)
        ]
        logger.info("Encoding transparent fish anchor overlay video...")
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

        # Clean up temporary frames directory
        for item in frames_dir.glob("*"):
            item.unlink()
        frames_dir.rmdir()

        return output_video
