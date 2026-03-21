# DogVid — Automated Long-Form YouTube Video Generator for Dogs

Fully automated platform for creating 10-hour YouTube videos scientifically optimized for dogs. Generates video and audio entirely from code using FFmpeg — no external assets needed.

## Canine Science

Videos are optimized based on peer-reviewed research on canine perception:

**Vision** — Dogs have dichromatic vision (blue + yellow only). All visuals use the blue-yellow color spectrum for maximum visibility. Red and green appear as gray to dogs.

**Motion** — Dogs are attracted to moderate, smooth motion with objects 5-30% of screen size. Scene durations are 30-90 seconds (canine attention span).

**Audio** — Uses calming frequencies (136-639 Hz solfeggio range), nature sounds, and heartbeat rhythms. Volume is kept low (dogs hear 4x better than humans). Based on Wells et al. (2002) research showing classical/soft music reduces stress in dogs.

## Quick Start

```bash
# Install
pip install -e .

# Generate a 30-second preview
dogvid preview --scene floating_orbs --duration 30s

# Generate a full 10-hour video
dogvid generate --preset calming_sleep

# Upload to YouTube
dogvid upload output/calming_sleep.mp4 --title "10 Hours Calming Dog TV" --privacy private
```

## Requirements

- Python 3.9+
- FFmpeg (with libx264)
- Google API credentials (for YouTube upload only)

## Presets

| Preset | Mood | Use Case |
|--------|------|----------|
| `calming_sleep` | Deep calm | Bedtime, anxious dogs |
| `separation_anxiety` | Relaxed | Dogs home alone |
| `playful_enrichment` | Engaged | Bored dogs, enrichment |
| `ocean_dreams` | Deep calm | Underwater theme, very soothing |
| `night_sky` | Deep calm | Overnight, twinkling stars |

## Scene Types

| Scene | Description |
|-------|-------------|
| `floating_orbs` | Blue/yellow orbs drifting (firefly-like) |
| `wave_pattern` | Ocean-like sine wave ripples |
| `gradient_sweep` | Rotating blue-to-yellow gradient |
| `bouncing_shapes` | Shapes bouncing (triggers attention) |
| `starfield` | Twinkling stars on deep blue |
| `lava_lamp` | Slow-moving blue/yellow blobs |

## Audio Types

| Audio | Description |
|-------|-------------|
| `calming_drone` | Layered solfeggio frequencies |
| `nature_ambience` | Synthesized rain, wind, birds |
| `heartbeat_rhythm` | Slow heartbeat rhythm |
| `binaural_relaxation` | Binaural beat patterns |

## Custom Generation

```bash
# Specific scenes and audio
dogvid generate \
  --name "custom_video" \
  --scenes "floating_orbs,bouncing_shapes,lava_lamp" \
  --audio "nature_ambience,heartbeat_rhythm" \
  --mood relaxed \
  --duration 10h \
  --unique 30m \
  --resolution 1080p

# Higher resolution
dogvid generate --preset calming_sleep --resolution 4k

# Shorter video
dogvid generate --preset playful_enrichment --duration 2h
```

## YouTube Upload Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a project and enable **YouTube Data API v3**
3. Create OAuth 2.0 credentials (Desktop application)
4. Download `client_secrets.json` to `~/.dogvid/client_secrets.json`
5. First upload will open a browser for OAuth consent

```bash
dogvid upload output/my_video.mp4 \
  --title "10 Hours Calming Dog TV - Separation Anxiety Relief" \
  --privacy public \
  --thumbnail output/my_video_thumbnail.jpg
```

## Pipeline

1. **Scene Generation** — Individual video clips via FFmpeg filtergraphs
2. **Audio Synthesis** — Calming soundscapes via FFmpeg audio filters
3. **Concatenation** — Scenes joined with crossfade transitions
4. **Audio Mixing** — Multiple audio layers mixed together
5. **Looping** — Unique segment looped to target duration (zero re-encode)
6. **Thumbnail** — Auto-generated dog-optimized thumbnail
7. **Upload** — Automated YouTube upload with SEO tags

## References

- Miller & Murphy (1995) — Canine color vision
- Pretterer et al. (2004) — Dogs' auditory preferences
- Bowman et al. (2015) — Auditory stimulation effects on shelter dogs
- Wells et al. (2002) — Music influence on dog behavior
- Lindig et al. (2020) — Media enrichment for kennelled dogs
