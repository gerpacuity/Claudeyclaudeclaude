"""
Pipeline orchestrator — assembles scenes and audio into a final long-form video.

Workflow:
1. Generate individual scene video clips (parallel FFmpeg processes)
2. Generate audio tracks
3. Concatenate scenes with crossfade transitions
4. Mix audio tracks together
5. Merge final video + audio
6. Loop to target duration (e.g., 10 hours)
7. Add metadata and thumbnail
"""

import os
import subprocess
import tempfile
import random
import shutil
from pathlib import Path
from dataclasses import dataclass, field

from .science import (
    UNIQUE_SEGMENT_SEC,
    TARGET_DURATION_SEC,
    SCENE_TRANSITION_SEC,
    RESOLUTION_PRESETS,
    DEFAULT_FPS,
    DEFAULT_RESOLUTION,
)
from .scenes import (
    SceneConfig,
    SCENE_GENERATORS,
    build_scene_sequence,
)
from .audio import (
    AudioConfig,
    AUDIO_GENERATORS,
    get_audio_for_mood,
)


@dataclass
class VideoProject:
    """Full video project configuration."""
    name: str = "dog_video"
    output_dir: str = "./output"
    resolution: str = DEFAULT_RESOLUTION
    fps: int = DEFAULT_FPS
    target_duration_sec: int = TARGET_DURATION_SEC
    unique_segment_sec: int = UNIQUE_SEGMENT_SEC
    mood: str = "relaxed"
    audio_volume: float = 0.3
    scene_types: list[str] = field(default_factory=lambda: list(SCENE_GENERATORS.keys()))
    audio_types: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.audio_types:
            self.audio_types = get_audio_for_mood(self.mood)

    @property
    def width(self):
        return RESOLUTION_PRESETS[self.resolution][0]

    @property
    def height(self):
        return RESOLUTION_PRESETS[self.resolution][1]


def _run_ffmpeg(cmd: list[str], output_path: str, label: str = "") -> bool:
    """Run an FFmpeg command, returning True on success."""
    full_cmd = cmd + [output_path]
    display = label or os.path.basename(output_path)
    print(f"  [ffmpeg] Generating: {display}")
    try:
        result = subprocess.run(
            full_cmd,
            capture_output=True,
            text=True,
            timeout=600,
        )
        if result.returncode != 0:
            print(f"  [ffmpeg] ERROR: {result.stderr[-500:]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        print(f"  [ffmpeg] TIMEOUT generating {display}")
        return False


def generate_scene_clips(project: VideoProject, work_dir: str) -> list[str]:
    """Generate all individual scene video clips."""
    clips = []
    scenes = build_scene_sequence(
        total_duration_sec=project.unique_segment_sec,
        width=project.width,
        height=project.height,
        fps=project.fps,
    )

    print(f"\n  Generating {len(scenes)} scene clips ({project.unique_segment_sec}s of unique content)...")

    for i, scene in enumerate(scenes):
        output_path = os.path.join(work_dir, f"scene_{i:03d}_{scene.scene_type}.mp4")
        generator = SCENE_GENERATORS[scene.scene_type]
        cmd = generator(scene)
        if _run_ffmpeg(cmd, output_path, f"Scene {i+1}/{len(scenes)}: {scene.scene_type} ({scene.duration_sec}s)"):
            clips.append(output_path)
        else:
            print(f"  WARNING: Scene {i+1} failed, skipping")

    return clips


def generate_audio_tracks(project: VideoProject, work_dir: str) -> list[str]:
    """Generate audio tracks for the unique segment."""
    tracks = []
    print(f"\n  Generating {len(project.audio_types)} audio tracks...")

    for audio_type in project.audio_types:
        if audio_type not in AUDIO_GENERATORS:
            print(f"  WARNING: Unknown audio type '{audio_type}', skipping")
            continue

        output_path = os.path.join(work_dir, f"audio_{audio_type}.m4a")
        cfg = AudioConfig(
            duration_sec=project.unique_segment_sec,
            mood=project.mood,
            volume=project.audio_volume,
        )
        generator = AUDIO_GENERATORS[audio_type]
        cmd = generator(cfg)
        if _run_ffmpeg(cmd, output_path, f"Audio: {audio_type}"):
            tracks.append(output_path)

    return tracks


def concatenate_clips(clips: list[str], output_path: str) -> bool:
    """Concatenate video clips using FFmpeg concat demuxer."""
    if not clips:
        print("  ERROR: No clips to concatenate")
        return False

    # Create concat file list
    concat_file = output_path + ".txt"
    with open(concat_file, "w") as f:
        for clip in clips:
            f.write(f"file '{os.path.abspath(clip)}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        output_path,
    ]
    print(f"\n  Concatenating {len(clips)} clips...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    # Cleanup
    os.remove(concat_file)

    if result.returncode != 0:
        print(f"  ERROR: Concatenation failed: {result.stderr[-300:]}")
        return False
    return True


def mix_audio_tracks(tracks: list[str], duration_sec: int, output_path: str) -> bool:
    """Mix multiple audio tracks into one."""
    if not tracks:
        print("  WARNING: No audio tracks to mix")
        return False

    if len(tracks) == 1:
        shutil.copy2(tracks[0], output_path)
        return True

    inputs = []
    for track in tracks:
        inputs.extend(["-i", track])

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex",
        f"amix=inputs={len(tracks)}:duration=longest:normalize=0",
        "-t", str(duration_sec),
        "-c:a", "aac", "-b:a", "192k",
        output_path,
    ]

    print(f"\n  Mixing {len(tracks)} audio tracks...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        print(f"  ERROR: Audio mixing failed: {result.stderr[-300:]}")
        return False
    return True


def loop_to_duration(input_video: str, input_audio: str, target_duration_sec: int,
                     output_path: str) -> bool:
    """
    Loop video and audio to reach target duration, then merge.
    Uses FFmpeg stream_loop for efficient looping without re-encoding.
    """
    loops_needed = (target_duration_sec // get_stream_duration(input_video)) + 1

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", str(loops_needed),
        "-i", input_video,
    ]

    if input_audio and os.path.exists(input_audio):
        cmd.extend([
            "-stream_loop", str(loops_needed),
            "-i", input_audio,
            "-map", "0:v", "-map", "1:a",
        ])
    else:
        cmd.extend(["-map", "0:v"])

    cmd.extend([
        "-t", str(target_duration_sec),
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ])

    print(f"\n  Looping to {target_duration_sec // 3600}h ({loops_needed} loops)...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if result.returncode != 0:
        print(f"  ERROR: Looping failed: {result.stderr[-500:]}")
        return False
    return True


def get_stream_duration(filepath: str) -> int:
    """Get duration of a media file in seconds using ffprobe."""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        filepath,
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return int(float(result.stdout.strip()))
    except (subprocess.TimeoutExpired, ValueError):
        return 1200  # Default 20 min fallback


def merge_video_audio(video_path: str, audio_path: str, output_path: str) -> bool:
    """Merge separate video and audio files."""
    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-i", audio_path,
        "-map", "0:v", "-map", "1:a",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest",
        output_path,
    ]
    print("\n  Merging video and audio...")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print(f"  ERROR: Merge failed: {result.stderr[-300:]}")
        return False
    return True


def generate_thumbnail(project: VideoProject, output_path: str) -> bool:
    """Generate a dog-optimized thumbnail (blue/yellow, high contrast)."""
    w, h = 1280, 720
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=#0A1A3A:s={w}x{h}:d=1:r=1",
        "-f", "lavfi",
        "-i", f"color=c=#FFD700:s=200x200:d=1:r=1",
        "-f", "lavfi",
        "-i", f"color=c=#0066FF:s=150x150:d=1:r=1",
        "-filter_complex", (
            f"[1:v]format=yuva444p,geq='lum=lum(X,Y):a=if(lt(hypot(X-100,Y-100),100),255,0)'[orb1];"
            f"[2:v]format=yuva444p,geq='lum=lum(X,Y):a=if(lt(hypot(X-75,Y-75),75),255,0)'[orb2];"
            f"[0:v][orb1]overlay=x=200:y=260[bg1];"
            f"[bg1][orb2]overlay=x=850:y=300[bg2];"
            f"[bg2]drawtext="
            f"text='{project.name.replace('_', ' ').title()}':"
            f"fontsize=64:fontcolor=white:"
            f"x=(w-text_w)/2:y=h-180:"
            f"shadowcolor=black:shadowx=3:shadowy=3"
        ),
        "-frames:v", "1",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.returncode == 0


def run_pipeline(project: VideoProject) -> str | None:
    """
    Run the full video generation pipeline.
    Returns path to the final video, or None on failure.
    """
    os.makedirs(project.output_dir, exist_ok=True)
    work_dir = tempfile.mkdtemp(prefix="dogvid_")

    print(f"=" * 60)
    print(f"  DogVid Pipeline")
    print(f"  Project: {project.name}")
    print(f"  Resolution: {project.resolution} ({project.width}x{project.height})")
    print(f"  Target: {project.target_duration_sec // 3600}h "
          f"({project.unique_segment_sec // 60}min unique content, looped)")
    print(f"  Mood: {project.mood}")
    print(f"  Scenes: {', '.join(project.scene_types)}")
    print(f"  Audio: {', '.join(project.audio_types)}")
    print(f"  Working dir: {work_dir}")
    print(f"=" * 60)

    try:
        # Step 1: Generate scene clips
        clips = generate_scene_clips(project, work_dir)
        if not clips:
            print("\n  FATAL: No scene clips generated")
            return None

        # Step 2: Generate audio
        audio_tracks = generate_audio_tracks(project, work_dir)

        # Step 3: Concatenate video clips
        segment_video = os.path.join(work_dir, "segment_video.mp4")
        if not concatenate_clips(clips, segment_video):
            return None

        # Step 4: Mix audio
        segment_audio = os.path.join(work_dir, "segment_audio.m4a")
        has_audio = mix_audio_tracks(audio_tracks, project.unique_segment_sec, segment_audio)

        # Step 5: Merge segment video + audio
        segment_merged = os.path.join(work_dir, "segment_merged.mp4")
        if has_audio:
            if not merge_video_audio(segment_video, segment_audio, segment_merged):
                segment_merged = segment_video  # Fall back to video-only
        else:
            segment_merged = segment_video

        # Step 6: Loop to target duration
        final_path = os.path.join(project.output_dir, f"{project.name}.mp4")
        if project.target_duration_sec > project.unique_segment_sec:
            if not loop_to_duration(
                segment_merged,
                segment_audio if has_audio else None,
                project.target_duration_sec,
                final_path,
            ):
                # Fallback: just copy the segment
                shutil.copy2(segment_merged, final_path)
                print("  WARNING: Looping failed, output is segment-length only")
        else:
            shutil.copy2(segment_merged, final_path)

        # Step 7: Generate thumbnail
        thumb_path = os.path.join(project.output_dir, f"{project.name}_thumbnail.jpg")
        if generate_thumbnail(project, thumb_path):
            print(f"\n  Thumbnail: {thumb_path}")

        print(f"\n  DONE! Final video: {final_path}")
        file_size = os.path.getsize(final_path) / (1024 * 1024 * 1024)
        print(f"  File size: {file_size:.2f} GB")
        return final_path

    finally:
        # Cleanup work directory
        print(f"\n  Cleaning up work directory...")
        shutil.rmtree(work_dir, ignore_errors=True)
