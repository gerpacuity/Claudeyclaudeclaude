"""
Canine perception science constants and utilities.

Based on peer-reviewed research:
- Miller & Murphy (1995) — canine color vision (dichromatic: blue + yellow)
- Pretterer et al. (2004) — dogs' auditory preferences
- Bowman et al. (2015) — effect of auditory stimulation on shelter dogs
- Lindig et al. (2020) — media enrichment for kennelled dogs
- Wells et al. (2002) — influence of auditory stimulation on behaviour of dogs
"""

# =============================================================================
# CANINE COLOR VISION
# =============================================================================
# Dogs have dichromatic vision with two cone types:
#   - Short wavelength (S-cones): ~429-435nm (blue)
#   - Long wavelength (L-cones): ~555nm (yellow-green)
# They CANNOT distinguish red from green (similar to human deuteranopia)

# Colors that dogs see VIBRANTLY (use these)
DOG_VISIBLE_COLORS = {
    "blue":         (0, 100, 255),
    "dark_blue":    (0, 50, 180),
    "light_blue":   (100, 180, 255),
    "sky_blue":     (135, 200, 255),
    "yellow":       (255, 255, 0),
    "golden":       (255, 200, 0),
    "amber":        (255, 170, 0),
    "white":        (255, 255, 255),
    "gray_light":   (180, 180, 180),
    "gray_mid":     (120, 120, 120),
    "gray_dark":    (60, 60, 60),
    "violet":       (80, 0, 200),
    "deep_blue":    (0, 0, 160),
}

# Colors dogs see as DULL/GRAY (avoid as primary — ok for backgrounds)
DOG_MUTED_COLORS = {
    "red":    (180, 120, 80),   # appears brownish-gray to dogs
    "green":  (140, 140, 80),   # appears yellowish-gray to dogs
    "orange": (200, 160, 60),   # appears dull yellow to dogs
}

# High-contrast pairs that dogs can clearly distinguish
DOG_CONTRAST_PAIRS = [
    ("blue", "yellow"),
    ("blue", "white"),
    ("dark_blue", "golden"),
    ("violet", "amber"),
    ("deep_blue", "yellow"),
    ("blue", "gray_light"),
    ("sky_blue", "gray_dark"),
]

# =============================================================================
# CANINE MOTION PREFERENCES
# =============================================================================
# Research shows dogs are attracted to:
# - Moderate, smooth motion (not jerky or too fast)
# - Horizontal movement patterns (prey-drive stimulation at low level)
# - Organic/natural motion curves (not rigid geometric)
# - Objects 5-30% of screen size (mimics small animals at distance)

MOTION_SPEED_SLOW = 0.3       # Fraction of screen width per 10 seconds
MOTION_SPEED_MODERATE = 0.6   # Optimal engagement
MOTION_SPEED_FAST = 1.2       # Brief bursts only

OBJECT_SIZE_MIN = 0.03        # 3% of screen dimension
OBJECT_SIZE_OPTIMAL = 0.10    # 10% — best engagement
OBJECT_SIZE_MAX = 0.30        # 30% — largest before disinterest

# Smooth motion curve parameters
MOTION_BEZIER_CONTROL_POINTS = 4  # Number of control points for bezier paths
MOTION_PATH_DURATION_SEC = 8      # How long one motion path takes

# =============================================================================
# CANINE AUDIO SCIENCE
# =============================================================================
# Dogs hear 67 Hz – 45,000 Hz (humans: 20 Hz – 20,000 Hz)
# Research-backed calming frequencies and sounds:

DOG_HEARING_MIN_HZ = 67
DOG_HEARING_MAX_HZ = 45000
DOG_PEAK_SENSITIVITY_HZ = 8000  # Most sensitive frequency

# Calming audio profiles (Wells et al., 2002; Bowman et al., 2015)
CALMING_FREQUENCIES_HZ = [
    136.1,   # Earth frequency (Om) — grounding
    396.0,   # Solfeggio — liberating
    528.0,   # Solfeggio — "love frequency"
    639.0,   # Solfeggio — connecting
]

# BPM ranges for different states
BPM_DEEP_CALM = (40, 50)      # Deep relaxation / sleep
BPM_RELAXED = (50, 70)        # Relaxed but awake
BPM_ENGAGED = (70, 90)        # Moderate engagement
BPM_STIMULATED = (90, 120)    # Active play-level

# Nature sounds dogs respond positively to
NATURE_SOUNDS = [
    "rain",
    "gentle_stream",
    "ocean_waves",
    "birds_distant",
    "wind_through_leaves",
    "crickets",
    "heartbeat",
]

# Sounds to AVOID (cause anxiety in many dogs)
AVOID_SOUNDS = [
    "thunder",
    "fireworks",
    "sirens",
    "vacuum",
    "sharp_whistles",
    "sudden_loud_noises",
]

# =============================================================================
# VIDEO PARAMETERS
# =============================================================================
RESOLUTION_PRESETS = {
    "720p":  (1280, 720),
    "1080p": (1920, 1080),
    "1440p": (2560, 1440),
    "4k":    (3840, 2160),
}

DEFAULT_FPS = 30
DEFAULT_RESOLUTION = "1080p"

# Scene timing for engagement (Lindig et al., 2020)
# Dogs maintain visual attention for 30-90 seconds on average
SCENE_DURATION_MIN_SEC = 30
SCENE_DURATION_MAX_SEC = 90
SCENE_TRANSITION_SEC = 3       # Smooth crossfade between scenes

# For 10-hour video
TARGET_DURATION_HOURS = 10
TARGET_DURATION_SEC = TARGET_DURATION_HOURS * 3600  # 36000 seconds

# Loop segment length — generate this much unique content, then loop
UNIQUE_SEGMENT_MINUTES = 20    # 20 min of unique content
UNIQUE_SEGMENT_SEC = UNIQUE_SEGMENT_MINUTES * 60
LOOPS_NEEDED = TARGET_DURATION_SEC / UNIQUE_SEGMENT_SEC  # 30 loops


def simulate_dog_vision(r, g, b):
    """
    Simulate how a dog perceives an RGB color.
    Dogs have dichromatic vision (blue-yellow axis only).
    Returns the approximate RGB as a dog would see it.
    """
    # Convert to dog's dichromatic perception
    # Dogs lack M-cones, seeing only through S-cones (blue) and L-cones (yellow)
    luminance = 0.299 * r + 0.587 * g + 0.114 * b
    blue_channel = 0.2 * r + 0.1 * g + 0.7 * b
    yellow_channel = 0.5 * r + 0.4 * g + 0.1 * b

    dog_r = int(min(255, max(0, 0.6 * yellow_channel + 0.4 * luminance)))
    dog_g = int(min(255, max(0, 0.5 * yellow_channel + 0.5 * luminance)))
    dog_b = int(min(255, max(0, 0.7 * blue_channel + 0.3 * luminance)))

    return (dog_r, dog_g, dog_b)


def get_scene_palette(scene_type):
    """Get an optimized color palette for a given scene type."""
    palettes = {
        "nature": ["blue", "sky_blue", "golden", "white", "gray_light"],
        "underwater": ["deep_blue", "blue", "light_blue", "white", "sky_blue"],
        "abstract": ["blue", "yellow", "violet", "amber", "white"],
        "night_sky": ["deep_blue", "dark_blue", "white", "golden", "blue"],
        "meadow": ["sky_blue", "golden", "yellow", "white", "light_blue"],
        "calming": ["light_blue", "sky_blue", "white", "gray_light", "blue"],
    }
    colors = palettes.get(scene_type, palettes["nature"])
    return [DOG_VISIBLE_COLORS[c] for c in colors]
