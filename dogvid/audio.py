"""
Audio engine — generates dog-optimized soundscapes using FFmpeg.

All audio is generated synthetically via FFmpeg's audio filters:
- Sine wave tones at calming frequencies
- Pink/brown noise for nature-like ambience
- Binaural-adjacent beats for relaxation (within dog hearing range)
- Layered nature sound synthesis

Key principles:
- Keep volume moderate (dogs have ~4x human hearing sensitivity)
- Avoid frequencies above 20kHz in generated content (uncomfortable at high volume)
- Use slow amplitude modulation (mimics natural sound patterns)
- Layer multiple soft sounds rather than one loud sound
"""

from dataclasses import dataclass
from .science import (
    CALMING_FREQUENCIES_HZ,
    BPM_DEEP_CALM,
    BPM_RELAXED,
    BPM_ENGAGED,
    DOG_HEARING_MAX_HZ,
)


@dataclass
class AudioConfig:
    """Configuration for audio generation."""
    duration_sec: int
    sample_rate: int = 48000
    mood: str = "relaxed"  # deep_calm, relaxed, engaged
    volume: float = 0.3    # Keep low for dog comfort (0.0-1.0)


def _get_bpm_range(mood: str) -> tuple[int, int]:
    """Get BPM range for the given mood."""
    return {
        "deep_calm": BPM_DEEP_CALM,
        "relaxed": BPM_RELAXED,
        "engaged": BPM_ENGAGED,
    }.get(mood, BPM_RELAXED)


def generate_calming_drone(cfg: AudioConfig) -> list[str]:
    """
    Generate a calming drone using layered sine waves at solfeggio frequencies.
    Includes slow amplitude modulation for organic feel.
    """
    f1 = CALMING_FREQUENCIES_HZ[0]  # 136.1 Hz
    f2 = CALMING_FREQUENCIES_HZ[2]  # 528 Hz
    f3 = CALMING_FREQUENCIES_HZ[3]  # 639 Hz

    vol = cfg.volume

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", (
            f"sine=frequency={f1}:duration={cfg.duration_sec}:sample_rate={cfg.sample_rate},"
            f"volume={vol * 0.4},"
            f"tremolo=f=0.1:d=0.3"
        ),
        "-f", "lavfi",
        "-i", (
            f"sine=frequency={f2}:duration={cfg.duration_sec}:sample_rate={cfg.sample_rate},"
            f"volume={vol * 0.25},"
            f"tremolo=f=0.07:d=0.2"
        ),
        "-f", "lavfi",
        "-i", (
            f"sine=frequency={f3}:duration={cfg.duration_sec}:sample_rate={cfg.sample_rate},"
            f"volume={vol * 0.15},"
            f"tremolo=f=0.05:d=0.15"
        ),
        "-filter_complex", (
            f"[0:a][1:a][2:a]amix=inputs=3:duration=longest:normalize=0"
        ),
        "-t", str(cfg.duration_sec),
        "-c:a", "aac", "-b:a", "192k",
    ]
    return cmd


def generate_nature_ambience(cfg: AudioConfig) -> list[str]:
    """
    Synthesize nature-like ambience using filtered noise.
    - Brown noise = distant wind/ocean
    - Filtered pink noise = gentle rain
    - Soft sine modulation = bird-like tones
    """
    vol = cfg.volume

    cmd = [
        "ffmpeg", "-y",
        # Brown noise — ocean/wind base
        "-f", "lavfi",
        "-i", (
            f"anoisesrc=color=brown:duration={cfg.duration_sec}"
            f":sample_rate={cfg.sample_rate}:amplitude={vol * 0.3},"
            f"lowpass=f=800,tremolo=f=0.03:d=0.4"
        ),
        # Pink noise — rain-like texture
        "-f", "lavfi",
        "-i", (
            f"anoisesrc=color=pink:duration={cfg.duration_sec}"
            f":sample_rate={cfg.sample_rate}:amplitude={vol * 0.15},"
            f"bandpass=f=2000:width_type=o:w=2,"
            f"tremolo=f=0.08:d=0.5"
        ),
        # Gentle high tone — distant bird-like
        "-f", "lavfi",
        "-i", (
            f"sine=frequency=2200:duration={cfg.duration_sec}"
            f":sample_rate={cfg.sample_rate},"
            f"volume={vol * 0.05},"
            f"tremolo=f=0.15:d=0.8,"
            f"aecho=0.8:0.7:40:0.3"
        ),
        "-filter_complex", (
            f"[0:a][1:a][2:a]amix=inputs=3:duration=longest:normalize=0"
        ),
        "-t", str(cfg.duration_sec),
        "-c:a", "aac", "-b:a", "192k",
    ]
    return cmd


def generate_heartbeat_rhythm(cfg: AudioConfig) -> list[str]:
    """
    Generate a slow heartbeat-like rhythm.
    Mimics resting heartbeat — deeply calming for dogs (reminds of mother/pack).
    ~60 BPM with soft sub-bass thump.
    """
    bpm_low, bpm_high = _get_bpm_range(cfg.mood)
    bpm = (bpm_low + bpm_high) // 2
    beat_freq = bpm / 60.0  # Hz
    vol = cfg.volume

    cmd = [
        "ffmpeg", "-y",
        # Sub-bass heartbeat thump
        "-f", "lavfi",
        "-i", (
            f"sine=frequency=55:duration={cfg.duration_sec}"
            f":sample_rate={cfg.sample_rate},"
            f"volume={vol * 0.5},"
            f"tremolo=f={beat_freq}:d=0.9,"
            f"lowpass=f=120"
        ),
        # Soft white noise bed
        "-f", "lavfi",
        "-i", (
            f"anoisesrc=color=brown:duration={cfg.duration_sec}"
            f":sample_rate={cfg.sample_rate}:amplitude={vol * 0.1},"
            f"lowpass=f=400"
        ),
        "-filter_complex", (
            f"[0:a][1:a]amix=inputs=2:duration=longest:normalize=0"
        ),
        "-t", str(cfg.duration_sec),
        "-c:a", "aac", "-b:a", "192k",
    ]
    return cmd


def generate_binaural_relaxation(cfg: AudioConfig) -> list[str]:
    """
    Generate binaural-style beats for deep relaxation.
    Uses two close frequencies to create a slow 'wobble' effect.
    Dogs can perceive this as a pulsing tone — research shows calming effect.
    """
    base_freq = 200  # Hz — well within dog hearing
    beat_freq = 4    # Hz difference — theta wave range (relaxation)
    vol = cfg.volume

    cmd = [
        "ffmpeg", "-y",
        # Left channel tone
        "-f", "lavfi",
        "-i", (
            f"sine=frequency={base_freq}:duration={cfg.duration_sec}"
            f":sample_rate={cfg.sample_rate},"
            f"volume={vol * 0.3},"
            f"pan=stereo|c0=c0|c1=0*c0"
        ),
        # Right channel tone (slightly offset)
        "-f", "lavfi",
        "-i", (
            f"sine=frequency={base_freq + beat_freq}:duration={cfg.duration_sec}"
            f":sample_rate={cfg.sample_rate},"
            f"volume={vol * 0.3},"
            f"pan=stereo|c0=0*c0|c1=c0"
        ),
        # Background pad
        "-f", "lavfi",
        "-i", (
            f"sine=frequency={base_freq * 2}:duration={cfg.duration_sec}"
            f":sample_rate={cfg.sample_rate},"
            f"volume={vol * 0.08},"
            f"tremolo=f=0.04:d=0.3"
        ),
        "-filter_complex", (
            f"[0:a][1:a][2:a]amix=inputs=3:duration=longest:normalize=0"
        ),
        "-t", str(cfg.duration_sec),
        "-c:a", "aac", "-b:a", "192k",
    ]
    return cmd


# Registry of audio generators
AUDIO_GENERATORS = {
    "calming_drone": generate_calming_drone,
    "nature_ambience": generate_nature_ambience,
    "heartbeat_rhythm": generate_heartbeat_rhythm,
    "binaural_relaxation": generate_binaural_relaxation,
}

# Mood-to-audio mapping
MOOD_AUDIO_MAP = {
    "deep_calm": ["heartbeat_rhythm", "calming_drone"],
    "relaxed": ["nature_ambience", "calming_drone", "binaural_relaxation"],
    "engaged": ["nature_ambience", "calming_drone"],
}


def get_audio_for_mood(mood: str) -> list[str]:
    """Get the list of audio types appropriate for a mood."""
    return MOOD_AUDIO_MAP.get(mood, MOOD_AUDIO_MAP["relaxed"])
