"""
Scene generators — create individual video scenes using FFmpeg filtergraph.

Each scene generator produces an FFmpeg filter_complex string that creates
visually engaging, dog-optimized animations entirely via FFmpeg's built-in
filters (no external assets needed).
"""

import math
import random
from dataclasses import dataclass, field

from .science import (
    DOG_VISIBLE_COLORS,
    DOG_CONTRAST_PAIRS,
    SCENE_DURATION_MIN_SEC,
    SCENE_DURATION_MAX_SEC,
    OBJECT_SIZE_OPTIMAL,
    get_scene_palette,
)


@dataclass
class SceneConfig:
    """Configuration for a single scene."""
    scene_type: str
    duration_sec: int
    width: int = 1920
    height: int = 1080
    fps: int = 30
    seed: int = field(default_factory=lambda: random.randint(0, 999999))

    @property
    def object_size(self):
        return int(min(self.width, self.height) * OBJECT_SIZE_OPTIMAL)


def _color_hex(rgb_tuple):
    """Convert RGB tuple to hex color string for FFmpeg."""
    return "0x{:02X}{:02X}{:02X}".format(*rgb_tuple)


def _ffmpeg_color(rgb_tuple):
    """Convert RGB tuple to FFmpeg color format."""
    return "#{:02X}{:02X}{:02X}".format(*rgb_tuple)


def generate_floating_orbs(cfg: SceneConfig) -> list[str]:
    """
    Floating blue/yellow orbs drifting across a dark background.
    Mimics fireflies or gentle particles — proven to hold canine attention.
    """
    palette = get_scene_palette("abstract")
    bg = palette[4] if len(palette) > 4 else (20, 20, 40)
    orb1 = palette[0]  # blue
    orb2 = palette[1]  # yellow

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", (
            f"color=c={_ffmpeg_color(bg)}:s={cfg.width}x{cfg.height}"
            f":d={cfg.duration_sec}:r={cfg.fps}"
        ),
        "-f", "lavfi",
        "-i", (
            f"color=c={_ffmpeg_color(orb1)}:s={cfg.object_size}x{cfg.object_size}"
            f":d={cfg.duration_sec}:r={cfg.fps}"
        ),
        "-f", "lavfi",
        "-i", (
            f"color=c={_ffmpeg_color(orb2)}:s={cfg.object_size}x{cfg.object_size}"
            f":d={cfg.duration_sec}:r={cfg.fps}"
        ),
        "-filter_complex", (
            # Make orbs circular with geq
            f"[1:v]format=yuva444p,geq="
            f"'lum=lum(X,Y):a=if(lt(hypot(X-{cfg.object_size//2},Y-{cfg.object_size//2}),{cfg.object_size//2}),255,0)'"
            f"[orb1];"
            f"[2:v]format=yuva444p,geq="
            f"'lum=lum(X,Y):a=if(lt(hypot(X-{cfg.object_size//2},Y-{cfg.object_size//2}),{cfg.object_size//2}),255,0)'"
            f"[orb2];"
            # Animate orb1: sine wave horizontal, slow vertical drift
            f"[0:v][orb1]overlay="
            f"x='({cfg.width}/2)+({cfg.width}/3)*sin(t*0.4)-{cfg.object_size//2}':"
            f"y='({cfg.height}/2)+({cfg.height}/4)*cos(t*0.25)-{cfg.object_size//2}'"
            f"[bg1];"
            # Animate orb2: opposite phase
            f"[bg1][orb2]overlay="
            f"x='({cfg.width}/3)+({cfg.width}/4)*cos(t*0.35)-{cfg.object_size//2}':"
            f"y='({cfg.height}/3)+({cfg.height}/3)*sin(t*0.3)-{cfg.object_size//2}'"
        ),
        "-t", str(cfg.duration_sec),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
    ]
    return cmd


def generate_wave_pattern(cfg: SceneConfig) -> list[str]:
    """
    Gentle sine-wave distortion pattern — ocean-like ripples.
    Blue-dominant palette. Hypnotic and calming for dogs.
    """
    palette = get_scene_palette("underwater")
    bg_color = palette[0]
    wave_color = palette[2]

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", (
            f"color=c={_ffmpeg_color(bg_color)}:s={cfg.width}x{cfg.height}"
            f":d={cfg.duration_sec}:r={cfg.fps}"
        ),
        "-f", "lavfi",
        "-i", (
            f"color=c={_ffmpeg_color(wave_color)}:s={cfg.width}x{cfg.height}"
            f":d={cfg.duration_sec}:r={cfg.fps}"
        ),
        "-filter_complex", (
            f"[0:v]format=yuva444p,geq="
            f"'r=clip(r(X,Y)+40*sin(2*PI*(X/{cfg.width//4})+t*1.5),0,255):"
            f"g=clip(g(X,Y)+30*sin(2*PI*(X/{cfg.width//3})+t*1.2),0,255):"
            f"b=clip(b(X,Y)+60*sin(2*PI*(X/{cfg.width//5})+t*0.8),0,255)'"
            f"[waves];"
            f"[waves]boxblur=3:1[smooth];"
            f"[smooth]format=yuv420p"
        ),
        "-t", str(cfg.duration_sec),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
    ]
    return cmd


def generate_gradient_sweep(cfg: SceneConfig) -> list[str]:
    """
    Slowly rotating color gradient across the screen.
    Uses blue-to-yellow sweep — maximum dog-visible contrast.
    """
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", (
            f"color=c=black:s={cfg.width}x{cfg.height}"
            f":d={cfg.duration_sec}:r={cfg.fps}"
        ),
        "-filter_complex", (
            f"[0:v]geq="
            f"'r=clip(128+127*sin(2*PI*(X+Y*0.5)/{cfg.width}+t*0.3),0,255):"
            f"g=clip(128+100*sin(2*PI*(X+Y*0.3)/{cfg.width}+t*0.25+1),0,255):"
            f"b=clip(180+75*sin(2*PI*(X*0.7+Y*0.3)/{cfg.width}+t*0.2+2),0,255)'"
            f"[grad];[grad]format=yuv420p"
        ),
        "-t", str(cfg.duration_sec),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
    ]
    return cmd


def generate_bouncing_shapes(cfg: SceneConfig) -> list[str]:
    """
    Multiple shapes bouncing around the screen.
    Mimics small animal movement — triggers positive attention in dogs.
    """
    palette = get_scene_palette("nature")
    bg = (15, 15, 35)
    shape_color = palette[0]
    shape2_color = palette[3]
    sz = cfg.object_size
    sz2 = int(sz * 0.7)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", (
            f"color=c={_ffmpeg_color(bg)}:s={cfg.width}x{cfg.height}"
            f":d={cfg.duration_sec}:r={cfg.fps}"
        ),
        "-f", "lavfi",
        "-i", (
            f"color=c={_ffmpeg_color(shape_color)}:s={sz}x{sz}"
            f":d={cfg.duration_sec}:r={cfg.fps}"
        ),
        "-f", "lavfi",
        "-i", (
            f"color=c={_ffmpeg_color(shape2_color)}:s={sz2}x{sz2}"
            f":d={cfg.duration_sec}:r={cfg.fps}"
        ),
        "-filter_complex", (
            # Circle mask for shape 1
            f"[1:v]format=yuva444p,geq="
            f"'lum=lum(X,Y):a=if(lt(hypot(X-{sz//2},Y-{sz//2}),{sz//2}),255,0)'"
            f"[s1];"
            # Circle mask for shape 2
            f"[2:v]format=yuva444p,geq="
            f"'lum=lum(X,Y):a=if(lt(hypot(X-{sz2//2},Y-{sz2//2}),{sz2//2}),255,0)'"
            f"[s2];"
            # Bounce shape 1 — absolute value of sawtooth creates bounce
            f"[0:v][s1]overlay="
            f"x='abs(mod(t*120+{random.randint(0, 500)},{cfg.width*2})-{cfg.width})-{sz//2}':"
            f"y='abs(mod(t*80+{random.randint(0, 300)},{cfg.height*2})-{cfg.height})-{sz//2}'"
            f"[out1];"
            # Bounce shape 2 — different speed
            f"[out1][s2]overlay="
            f"x='abs(mod(t*95+{random.randint(0, 400)},{cfg.width*2})-{cfg.width})-{sz2//2}':"
            f"y='abs(mod(t*65+{random.randint(0, 200)},{cfg.height*2})-{cfg.height})-{sz2//2}'"
        ),
        "-t", str(cfg.duration_sec),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
    ]
    return cmd


def generate_starfield(cfg: SceneConfig) -> list[str]:
    """
    Slowly twinkling stars on deep blue background.
    Night-sky simulation — calming scene for evening/sleep content.
    """
    palette = get_scene_palette("night_sky")
    bg = palette[0]

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", (
            f"color=c={_ffmpeg_color(bg)}:s={cfg.width}x{cfg.height}"
            f":d={cfg.duration_sec}:r={cfg.fps}"
        ),
        "-filter_complex", (
            f"[0:v]geq="
            f"'r=r(X,Y)+255*lt(abs(random(1)*1000-500),2)*gt(sin(t*0.5+random(1)*6.28),0.7):"
            f"g=g(X,Y)+255*lt(abs(random(1)*1000-500),2)*gt(sin(t*0.5+random(1)*6.28),0.7):"
            f"b=b(X,Y)+255*lt(abs(random(1)*1000-500),2)*gt(sin(t*0.5+random(1)*6.28),0.7)'"
            f"[stars];[stars]format=yuv420p"
        ),
        "-t", str(cfg.duration_sec),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
    ]
    return cmd


def generate_lava_lamp(cfg: SceneConfig) -> list[str]:
    """
    Smooth, slow-moving blob animation resembling a lava lamp.
    Blue and yellow blobs on dark background — maximum dog-visible contrast.
    """
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", (
            f"color=c=#0A0A28:s={cfg.width}x{cfg.height}"
            f":d={cfg.duration_sec}:r={cfg.fps}"
        ),
        "-filter_complex", (
            f"[0:v]geq="
            f"'r=clip(40*sin(2*PI*hypot(X-{cfg.width//2}+200*sin(t*0.2),Y-{cfg.height//2}+150*cos(t*0.15))/200)+20,0,255):"
            f"g=clip(40*sin(2*PI*hypot(X-{cfg.width//2}+200*sin(t*0.2),Y-{cfg.height//2}+150*cos(t*0.15))/200)+20,0,255):"
            f"b=clip(180+75*sin(2*PI*hypot(X-{cfg.width//2}+200*sin(t*0.2),Y-{cfg.height//2}+150*cos(t*0.15))/200),0,255)"
            f"+clip(200+55*sin(2*PI*hypot(X-{cfg.width*3//4}+180*cos(t*0.18),Y-{cfg.height//3}+120*sin(t*0.22))/180),0,255)*0'"
            f"[lava];"
            # Add a second blob overlay via blend
            f"color=c=#0A0A28:s={cfg.width}x{cfg.height}:d={cfg.duration_sec}:r={cfg.fps},"
            f"geq="
            f"'r=clip(200+55*sin(2*PI*hypot(X-{cfg.width*3//4}+180*cos(t*0.18),Y-{cfg.height//3}+120*sin(t*0.22))/180),0,255):"
            f"g=clip(180+55*sin(2*PI*hypot(X-{cfg.width*3//4}+180*cos(t*0.18),Y-{cfg.height//3}+120*sin(t*0.22))/180),0,255):"
            f"b=clip(30+20*sin(2*PI*hypot(X-{cfg.width*3//4}+180*cos(t*0.18),Y-{cfg.height//3}+120*sin(t*0.22))/180),0,255)'"
            f"[blob2];"
            f"[lava][blob2]blend=all_mode=screen[combined];"
            f"[combined]boxblur=8:3[smooth];"
            f"[smooth]format=yuv420p"
        ),
        "-t", str(cfg.duration_sec),
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
    ]
    return cmd


# Registry of all available scene types
SCENE_GENERATORS = {
    "floating_orbs": generate_floating_orbs,
    "wave_pattern": generate_wave_pattern,
    "gradient_sweep": generate_gradient_sweep,
    "bouncing_shapes": generate_bouncing_shapes,
    "starfield": generate_starfield,
    "lava_lamp": generate_lava_lamp,
}


def get_random_scene_duration():
    """Get a random scene duration within the scientifically optimal range."""
    return random.randint(SCENE_DURATION_MIN_SEC, SCENE_DURATION_MAX_SEC)


def build_scene_sequence(total_duration_sec, width=1920, height=1080, fps=30):
    """
    Build a sequence of scenes that fills the requested duration.
    Ensures variety by cycling through scene types.
    """
    scenes = []
    elapsed = 0
    scene_types = list(SCENE_GENERATORS.keys())
    idx = 0

    while elapsed < total_duration_sec:
        remaining = total_duration_sec - elapsed
        duration = min(get_random_scene_duration(), remaining)
        if duration < 10:
            # Too short for a scene, extend the previous one
            if scenes:
                scenes[-1].duration_sec += duration
            break

        scene_type = scene_types[idx % len(scene_types)]
        scenes.append(SceneConfig(
            scene_type=scene_type,
            duration_sec=duration,
            width=width,
            height=height,
            fps=fps,
        ))
        elapsed += duration
        idx += 1

    return scenes
