"""
DogVid CLI — command-line interface for the dog video generator.

Usage:
    dogvid generate --name "Calming Ocean" --mood relaxed --duration 10h
    dogvid generate --preset calming_sleep --duration 10h
    dogvid upload output/calming_ocean.mp4 --title "10 Hours Calming Dog TV"
    dogvid preview --preset playful_meadow --duration 30s
    dogvid list-presets
    dogvid list-scenes
"""

import os
import sys
import yaml
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .pipeline import VideoProject, run_pipeline
from .scenes import SCENE_GENERATORS
from .audio import AUDIO_GENERATORS, get_audio_for_mood
from .youtube import UploadConfig, upload_video, DEFAULT_TAGS
from .science import (
    RESOLUTION_PRESETS,
    DOG_VISIBLE_COLORS,
    DOG_CONTRAST_PAIRS,
    CALMING_FREQUENCIES_HZ,
)

console = Console()

PRESETS_DIR = os.path.join(os.path.dirname(__file__), "..", "presets")


def _parse_duration(duration_str: str) -> int:
    """Parse duration string like '10h', '30m', '90s' to seconds."""
    duration_str = duration_str.strip().lower()
    if duration_str.endswith("h"):
        return int(float(duration_str[:-1]) * 3600)
    elif duration_str.endswith("m"):
        return int(float(duration_str[:-1]) * 60)
    elif duration_str.endswith("s"):
        return int(float(duration_str[:-1]))
    else:
        return int(duration_str)


def _load_preset(preset_name: str) -> dict:
    """Load a preset YAML file."""
    preset_path = os.path.join(PRESETS_DIR, f"{preset_name}.yaml")
    if not os.path.exists(preset_path):
        console.print(f"[red]Preset not found: {preset_name}[/red]")
        console.print(f"Available presets: {', '.join(_list_presets())}")
        sys.exit(1)
    with open(preset_path) as f:
        return yaml.safe_load(f)


def _list_presets() -> list[str]:
    """List available preset names."""
    if not os.path.exists(PRESETS_DIR):
        return []
    return [
        os.path.splitext(f)[0]
        for f in os.listdir(PRESETS_DIR)
        if f.endswith(".yaml")
    ]


@click.group()
@click.version_option(version="1.0.0")
def main():
    """DogVid — Automated Long-Form YouTube Video Generator for Dogs"""
    pass


@main.command()
@click.option("--name", "-n", default="dog_video", help="Project name (used for output filename)")
@click.option("--preset", "-p", default=None, help="Use a preset configuration")
@click.option("--duration", "-d", default="10h", help="Target duration (e.g., 10h, 30m, 90s)")
@click.option("--unique", "-u", default="20m", help="Unique content length before looping (e.g., 20m)")
@click.option("--resolution", "-r", default="1080p", type=click.Choice(list(RESOLUTION_PRESETS.keys())))
@click.option("--fps", default=30, type=int, help="Frames per second")
@click.option("--mood", "-m", default="relaxed", type=click.Choice(["deep_calm", "relaxed", "engaged"]))
@click.option("--volume", default=0.3, type=float, help="Audio volume 0.0-1.0 (keep low for dogs)")
@click.option("--output-dir", "-o", default="./output", help="Output directory")
@click.option("--scenes", default=None, help="Comma-separated scene types to use")
@click.option("--audio", default=None, help="Comma-separated audio types to use")
def generate(name, preset, duration, unique, resolution, fps, mood, volume, output_dir, scenes, audio):
    """Generate a dog-optimized video."""

    # Start from preset if specified
    if preset:
        preset_data = _load_preset(preset)
        name = preset_data.get("name", name)
        mood = preset_data.get("mood", mood)
        resolution = preset_data.get("resolution", resolution)
        volume = preset_data.get("volume", volume)
        scenes = preset_data.get("scenes", scenes)
        audio = preset_data.get("audio", audio)
        duration = preset_data.get("duration", duration)
        unique = preset_data.get("unique_segment", unique)

    scene_list = scenes.split(",") if isinstance(scenes, str) else None
    audio_list = audio.split(",") if isinstance(audio, str) else None

    project = VideoProject(
        name=name,
        output_dir=output_dir,
        resolution=resolution,
        fps=fps,
        target_duration_sec=_parse_duration(duration),
        unique_segment_sec=_parse_duration(unique),
        mood=mood,
        audio_volume=volume,
    )

    if scene_list:
        valid = [s for s in scene_list if s in SCENE_GENERATORS]
        if valid:
            project.scene_types = valid
    if audio_list:
        valid = [a for a in audio_list if a in AUDIO_GENERATORS]
        if valid:
            project.audio_types = valid

    console.print(Panel.fit(
        f"[bold blue]DogVid[/bold blue] — Generating: [yellow]{name}[/yellow]\n"
        f"Duration: {duration} | Unique: {unique} | Mood: {mood}\n"
        f"Resolution: {resolution} @ {fps}fps | Volume: {volume}",
        title="Dog Video Generator",
        border_style="blue",
    ))

    result = run_pipeline(project)

    if result:
        console.print(f"\n[bold green]Video generated successfully![/bold green]")
        console.print(f"Output: [cyan]{result}[/cyan]")
        size_gb = os.path.getsize(result) / (1024 ** 3)
        console.print(f"Size: {size_gb:.2f} GB")
    else:
        console.print(f"\n[bold red]Video generation failed.[/bold red]")
        sys.exit(1)


@main.command()
@click.argument("video_path")
@click.option("--title", "-t", default=None, help="Video title")
@click.option("--description", default=None, help="Video description")
@click.option("--privacy", default="private", type=click.Choice(["private", "unlisted", "public"]))
@click.option("--thumbnail", default=None, help="Path to thumbnail image")
@click.option("--credentials", default=None, help="Path to Google OAuth credentials JSON")
@click.option("--playlist", default=None, help="YouTube playlist ID to add video to")
@click.option("--tags", default=None, help="Comma-separated tags (adds to defaults)")
def upload(video_path, title, description, privacy, thumbnail, credentials, playlist, tags):
    """Upload a video to YouTube."""

    tag_list = DEFAULT_TAGS.copy()
    if tags:
        tag_list.extend(tags.split(","))

    config = UploadConfig(
        video_path=video_path,
        title=title or "",
        description=description or "",
        tags=tag_list,
        privacy=privacy,
        thumbnail_path=thumbnail,
        playlist_id=playlist,
    )
    if credentials:
        config.credentials_path = credentials

    console.print(Panel.fit(
        f"[bold blue]DogVid Upload[/bold blue]\n"
        f"File: {video_path}\n"
        f"Title: {config.title}\n"
        f"Privacy: {privacy}",
        title="YouTube Upload",
        border_style="blue",
    ))

    video_id = upload_video(config)
    if video_id:
        console.print(f"\n[bold green]Upload successful![/bold green]")
        console.print(f"Video ID: {video_id}")
        console.print(f"URL: https://www.youtube.com/watch?v={video_id}")
    else:
        console.print(f"\n[bold red]Upload failed.[/bold red]")
        sys.exit(1)


@main.command()
@click.option("--preset", "-p", default=None, help="Preview a preset")
@click.option("--scene", "-s", default=None, help="Preview a specific scene type")
@click.option("--duration", "-d", default="30s", help="Preview duration")
@click.option("--resolution", "-r", default="720p")
@click.option("--mood", "-m", default="relaxed")
def preview(preset, scene, duration, resolution, mood):
    """Generate a short preview clip."""

    if preset:
        preset_data = _load_preset(preset)
        scene_types = preset_data.get("scenes", "").split(",") if preset_data.get("scenes") else None
    elif scene:
        if scene not in SCENE_GENERATORS:
            console.print(f"[red]Unknown scene: {scene}[/red]")
            console.print(f"Available: {', '.join(SCENE_GENERATORS.keys())}")
            sys.exit(1)
        scene_types = [scene]
    else:
        scene_types = None

    dur = _parse_duration(duration)
    project = VideoProject(
        name="preview",
        output_dir="./output",
        resolution=resolution,
        target_duration_sec=dur,
        unique_segment_sec=dur,
        mood=mood,
    )
    if scene_types:
        project.scene_types = scene_types

    console.print(f"[blue]Generating {duration} preview...[/blue]")
    result = run_pipeline(project)
    if result:
        console.print(f"[green]Preview: {result}[/green]")


@main.command("list-scenes")
def list_scenes():
    """List available scene types."""
    table = Table(title="Available Scene Types", border_style="blue")
    table.add_column("Scene", style="cyan")
    table.add_column("Description")

    descriptions = {
        "floating_orbs": "Blue/yellow orbs drifting on dark background (firefly-like)",
        "wave_pattern": "Ocean-like sine wave ripples in blue tones",
        "gradient_sweep": "Slowly rotating blue-to-yellow gradient",
        "bouncing_shapes": "Shapes bouncing around (triggers prey-drive attention)",
        "starfield": "Twinkling stars on deep blue (calming night sky)",
        "lava_lamp": "Slow-moving blue/yellow blobs (hypnotic, calming)",
    }

    for name in SCENE_GENERATORS:
        table.add_row(name, descriptions.get(name, ""))

    console.print(table)


@main.command("list-audio")
def list_audio():
    """List available audio types."""
    table = Table(title="Available Audio Types", border_style="blue")
    table.add_column("Audio", style="cyan")
    table.add_column("Description")
    table.add_column("Best For")

    descriptions = {
        "calming_drone": ("Layered solfeggio frequency drones (136-639 Hz)", "Relaxation, anxiety"),
        "nature_ambience": ("Synthesized rain, wind, distant birds", "General calm, enrichment"),
        "heartbeat_rhythm": ("Slow heartbeat-like rhythm (sub-bass)", "Deep sleep, separation anxiety"),
        "binaural_relaxation": ("Binaural beat patterns (theta waves)", "Deep calm, nervous dogs"),
    }

    for name in AUDIO_GENERATORS:
        desc, best = descriptions.get(name, ("", ""))
        table.add_row(name, desc, best)

    console.print(table)


@main.command("list-presets")
def list_presets():
    """List available presets."""
    presets = _list_presets()
    if not presets:
        console.print("[yellow]No presets found. Create .yaml files in the presets/ directory.[/yellow]")
        return

    table = Table(title="Available Presets", border_style="blue")
    table.add_column("Preset", style="cyan")
    table.add_column("Mood")
    table.add_column("Duration")
    table.add_column("Description")

    for name in presets:
        data = _load_preset(name)
        table.add_row(
            name,
            data.get("mood", ""),
            data.get("duration", ""),
            data.get("description", ""),
        )

    console.print(table)


@main.command()
def science():
    """Show the canine science behind the video optimization."""
    console.print(Panel.fit(
        "[bold]Canine Vision Science[/bold]\n\n"
        "Dogs have [blue]dichromatic vision[/blue] — they see in blue and yellow.\n"
        "They cannot distinguish red from green (similar to human deuteranopia).\n\n"
        "[bold]Optimal Colors:[/bold]\n"
        "  Blue (#0064FF) + Yellow (#FFFF00) = Maximum contrast for dogs\n"
        "  White, grays, and violet are also clearly visible\n"
        "  Red and green appear as brownish-gray\n\n"
        "[bold]Motion:[/bold]\n"
        "  - Dogs are attracted to moderate, smooth motion\n"
        "  - Objects 5-30% of screen size (mimics small animals)\n"
        "  - Attention span per scene: 30-90 seconds\n\n"
        "[bold]Audio:[/bold]\n"
        "  - Dog hearing: 67 Hz — 45,000 Hz\n"
        "  - Calming frequencies: 136.1, 396, 528, 639 Hz\n"
        "  - Classical/soft music reduces barking (Wells, 2002)\n"
        "  - Heavy metal increases agitation\n"
        "  - Nature sounds (rain, streams) are calming\n"
        "  - Heartbeat sounds reduce anxiety (maternal association)\n\n"
        "[bold]References:[/bold]\n"
        "  Miller & Murphy (1995) - Canine color vision\n"
        "  Pretterer et al. (2004) - Dogs' auditory preferences\n"
        "  Bowman et al. (2015) - Auditory stimulation in shelters\n"
        "  Wells et al. (2002) - Music influence on dog behavior\n"
        "  Lindig et al. (2020) - Media enrichment for kennelled dogs",
        title="Canine Perception Science",
        border_style="blue",
    ))


if __name__ == "__main__":
    main()
