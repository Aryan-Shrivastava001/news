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
        self.transition_duration = 0.5
        # Variety of transitions for the slideshow
        self.transitions = ["fade", "slideleft", "slideright", "dissolve", "fadeblack"]

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

    def _render_image_segment(self, image_path: Path, duration: float, out_path: Path, zoom_in: bool = True):
        """Creates a Ken Burns video segment from a single image."""
        # Alternating zoom directions
        z_expr = "'min(zoom+0.0015,1.15)'" if zoom_in else "'max(1.15-0.0015*on,1)'"
        
        filter_str = (
            f"[0:v]scale={self.width}:{self.height}:force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.height},boxblur=25:5,eq=brightness=-0.15[bg];"
            f"[0:v]scale=1000:-1:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:380,"
            f"zoompan=z={z_expr}:d={int(duration*self.fps)}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s={self.width}x{self.height}[out]"
        )
        
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", str(image_path),
            "-t", str(duration),
            "-filter_complex", filter_str,
            "-map", "[out]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-r", str(self.fps),
            str(out_path)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    def _render_video_segment(self, video_path: Path, duration: float, out_path: Path):
        """Formats a gameplay video clip to fit the 9:16 layout with blurred background."""
        filter_str = (
            f"[0:v]scale={self.width}:{self.height}:force_original_aspect_ratio=increase,"
            f"crop={self.width}:{self.height},boxblur=25:5,eq=brightness=-0.15[bg];"
            f"[0:v]scale=1000:-1:force_original_aspect_ratio=decrease[fg];"
            f"[bg][fg]overlay=(W-w)/2:380[out]"
        )
        cmd = [
            "ffmpeg", "-y", "-i", str(video_path),
            "-t", str(duration),
            "-filter_complex", filter_str,
            "-map", "[out]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-r", str(self.fps),
            str(out_path)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)

    def _create_slideshow(self, images: List[Path], videos: List[Path], total_duration: float, work_dir: Path) -> Path:
        """Composes multiple segments and crossfades them together into a base video layer."""
        segments = []
        media_queue = []
        
        for img in images:
            media_queue.append(("image", img))
            
        # Splice the video clip into the middle of the images if available
        if videos:
            vid = videos[0]
            vid_dur = self.get_duration(vid)
            if vid_dur > 2:
                insert_idx = len(media_queue) // 2
                media_queue.insert(insert_idx, ("video", vid))

        num_segments = len(media_queue)
        
        # Calculate time required for segments and overlapping transitions
        total_overlap = (num_segments - 1) * self.transition_duration if num_segments > 1 else 0
        required_sum = total_duration + total_overlap
        time_per_segment = required_sum / max(num_segments, 1)

        # 1. Render all independent segments
        for idx, (mtype, path) in enumerate(media_queue):
            seg_path = work_dir / f"segment_{idx:03d}.mp4"
            dur = time_per_segment
            
            if mtype == "video":
                # Ensure we don't request more time than the video has, and cap at 8s
                actual_dur = self.get_duration(path)
                dur = min(dur, actual_dur, 8.0)
                self._render_video_segment(path, dur, seg_path)
            else:
                zoom_in = (idx % 2 == 0) # Alternate zoom directions
                self._render_image_segment(path, dur, seg_path, zoom_in=zoom_in)
                
            segments.append((seg_path, dur))

        if len(segments) == 1:
            return segments[0][0]

        # 2. XFade stitch them all together
        slideshow_path = work_dir / "slideshow.mp4"
        filter_parts = []
        inputs = []
        
        for p, d in segments:
            inputs.extend(["-i", str(p)])
            
        current_offset = segments[0][1] - self.transition_duration
        
        trans = self.transitions[0 % len(self.transitions)]
        filter_parts.append(f"[0:v][1:v]xfade=transition={trans}:duration={self.transition_duration}:offset={current_offset:.2f}[v1];")
        last_lbl = "[v1]"
        
        for i in range(2, len(segments)):
            current_offset += segments[i-1][1] - self.transition_duration
            trans = self.transitions[(i-1) % len(self.transitions)]
            next_lbl = f"[v{i}]"
            filter_parts.append(f"{last_lbl}[{i}:v]xfade=transition={trans}:duration={self.transition_duration}:offset={current_offset:.2f}{next_lbl};")
            last_lbl = next_lbl
            
        filter_str = "".join(filter_parts).rstrip(";")

        cmd = ["ffmpeg", "-y"] + inputs + [
            "-filter_complex", filter_str,
            "-map", last_lbl,
            "-c:v", "libx264", "-preset", "fast", "-crf", "22",
            "-pix_fmt", "yuv420p", "-r", str(self.fps),
            str(slideshow_path)
        ]
        
        logger.info(f"Stitching {len(segments)} segments with xfade transitions...")
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return slideshow_path

    def assemble_short(
        self,
        images: List[Path],
        videos: List[Path],
        voiceover_audio: Path,
        fish_anchor_video: Path,
        subtitles_ass: Optional[Path],
        output_mp4: Path,
        bg_music: Optional[Path] = None
    ) -> Path:
        """
        Assembles the final 9:16 YouTube Short using FFmpeg:
        - Layer 1 (Background): Dynamic slideshow of images & gameplay clips.
        - Layer 2 (Subtitles): Bold yellow kinetic captions above the anchor.
        - Layer 3 (Anchor Mascot): 2-frame talking fish anchor at the bottom.
        - Audio: Voiceover synchronized with low-volume background music.
        """
        output_mp4.parent.mkdir(parents=True, exist_ok=True)
        
        # Enforce YouTube Shorts 60s max limit
        duration = min(self.get_duration(voiceover_audio) + 0.5, 55.0)

        logger.info(f"Generating dynamic slideshow base ({len(images)} images, {len(videos)} videos)...")
        slideshow_video = self._create_slideshow(images, videos, duration, output_mp4.parent)

        sub_filter = ""
        if subtitles_ass and subtitles_ass.exists():
            clean_sub_path = subtitles_ass.as_posix().replace(":", "\\:")
            sub_filter = f",ass='{clean_sub_path}'"

        cmd = [
            "ffmpeg", "-y",
            "-i", str(slideshow_video),
            "-i", str(fish_anchor_video),
            "-i", str(voiceover_audio),
        ]

        if bg_music and bg_music.exists():
            cmd.extend(["-stream_loop", "-1", "-i", str(bg_music)])

        # Place fish anchor over the pre-rendered slideshow
        filter_parts = [
            f"[1:v]scale=450:450[fish]",
            f"[0:v][fish]overlay=(W-w)/2:{self.height-480}[with_fish]"
        ]

        if sub_filter:
            filter_parts.append(f"[with_fish]null{sub_filter}[vout]")
            v_map = "[vout]"
        else:
            v_map = "[with_fish]"

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

        logger.info(f"Rendering final YouTube Short to {output_mp4} ({duration:.1f}s)...")
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        # Cleanup temporary segment files
        for p in output_mp4.parent.glob("segment_*.mp4"):
            p.unlink(missing_ok=True)
        if slideshow_video.name != "segment_000.mp4": # Avoid deleting if it was only 1 segment
            slideshow_video.unlink(missing_ok=True)

        if res.returncode != 0:
            logger.error(f"FFmpeg render error: {res.stderr}")
            raise RuntimeError(f"FFmpeg failed with exit code {res.returncode}: {res.stderr[-400:]}")

        logger.info(f"Render complete! Video saved: {output_mp4} ({output_mp4.stat().st_size / (1024*1024):.2f} MB)")
        return output_mp4
