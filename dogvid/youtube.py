"""
YouTube upload automation using the YouTube Data API v3.

Setup requirements:
1. Create a Google Cloud project at https://console.cloud.google.com
2. Enable the YouTube Data API v3
3. Create OAuth 2.0 credentials (Desktop application)
4. Download the client_secrets.json file
5. Place it at ~/.dogvid/client_secrets.json (or specify via --credentials)

First run will open a browser for OAuth consent.
Token is cached at ~/.dogvid/youtube_token.json for subsequent uploads.
"""

import os
import json
import httplib2
from pathlib import Path
from dataclasses import dataclass, field

try:
    from googleapiclient.discovery import build
    from googleapiclient.http import MediaFileUpload
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.oauth2.credentials import Credentials
    HAS_GOOGLE_API = True
except ImportError:
    HAS_GOOGLE_API = False


CONFIG_DIR = os.path.expanduser("~/.dogvid")
DEFAULT_CREDENTIALS = os.path.join(CONFIG_DIR, "client_secrets.json")
TOKEN_PATH = os.path.join(CONFIG_DIR, "youtube_token.json")

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Dog video category: Pets & Animals = 15
YOUTUBE_CATEGORY_PETS = "15"

# Optimized tags for dog video discovery
DEFAULT_TAGS = [
    "dog tv", "dogs", "videos for dogs", "dog entertainment",
    "dog relaxation", "calming dog video", "dog anxiety",
    "separation anxiety dogs", "dog music", "relax my dog",
    "10 hours for dogs", "leave on for dog", "dog alone",
    "pet tv", "tv for dogs", "dog calming", "puppy video",
    "dog enrichment", "canine relaxation", "dogs home alone",
]


@dataclass
class UploadConfig:
    """YouTube upload configuration."""
    video_path: str
    title: str = ""
    description: str = ""
    tags: list[str] = field(default_factory=lambda: DEFAULT_TAGS.copy())
    category: str = YOUTUBE_CATEGORY_PETS
    privacy: str = "private"  # private, unlisted, public
    thumbnail_path: str | None = None
    credentials_path: str = DEFAULT_CREDENTIALS
    playlist_id: str | None = None
    language: str = "en"
    made_for_kids: bool = False

    def __post_init__(self):
        if not self.title:
            basename = os.path.splitext(os.path.basename(self.video_path))[0]
            self.title = basename.replace("_", " ").title()

        if not self.description:
            self.description = self._generate_description()

    def _generate_description(self) -> str:
        return (
            f"{self.title}\n\n"
            "Scientifically optimized video designed for dogs. "
            "Uses colors in the canine-visible spectrum (blue & yellow), "
            "gentle motion patterns, and calming audio frequencies.\n\n"
            "Perfect for:\n"
            "- Dogs with separation anxiety\n"
            "- Keeping your dog calm while home alone\n"
            "- Puppy entertainment and enrichment\n"
            "- Dog relaxation and sleep aid\n\n"
            "Based on canine vision and auditory research.\n"
            "Colors optimized for dichromatic (blue-yellow) dog vision.\n"
            "Audio uses calming frequencies (396-639 Hz solfeggio range).\n\n"
            "#DogTV #DogsOfYouTube #CalmDog #DogRelaxation"
        )


def get_authenticated_service(credentials_path: str):
    """Get an authenticated YouTube API service."""
    if not HAS_GOOGLE_API:
        raise ImportError(
            "Google API libraries not installed. Run:\n"
            "  pip install google-api-python-client google-auth-oauthlib google-auth-httplib2"
        )

    os.makedirs(CONFIG_DIR, exist_ok=True)
    creds = None

    # Load cached token
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)

    # If no valid creds, do OAuth flow
    if not creds or not creds.valid:
        if not os.path.exists(credentials_path):
            raise FileNotFoundError(
                f"OAuth credentials not found at {credentials_path}\n"
                "Download from Google Cloud Console and place at:\n"
                f"  {DEFAULT_CREDENTIALS}\n"
                "See: https://console.cloud.google.com/apis/credentials"
            )

        flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
        creds = flow.run_local_server(port=0)

        # Save token for next time
        with open(TOKEN_PATH, "w") as f:
            f.write(creds.to_json())
        print(f"  Token cached at {TOKEN_PATH}")

    return build("youtube", "v3", credentials=creds)


def upload_video(config: UploadConfig) -> str | None:
    """
    Upload a video to YouTube.
    Returns the video ID on success, or None on failure.
    """
    if not os.path.exists(config.video_path):
        print(f"  ERROR: Video file not found: {config.video_path}")
        return None

    print(f"\n  Uploading to YouTube...")
    print(f"  Title: {config.title}")
    print(f"  Privacy: {config.privacy}")
    print(f"  Category: {config.category} (Pets & Animals)")

    try:
        youtube = get_authenticated_service(config.credentials_path)
    except (ImportError, FileNotFoundError) as e:
        print(f"  ERROR: {e}")
        return None

    body = {
        "snippet": {
            "title": config.title,
            "description": config.description,
            "tags": config.tags,
            "categoryId": config.category,
            "defaultLanguage": config.language,
        },
        "status": {
            "privacyStatus": config.privacy,
            "selfDeclaredMadeForKids": config.made_for_kids,
        },
    }

    media = MediaFileUpload(
        config.video_path,
        mimetype="video/mp4",
        resumable=True,
        chunksize=50 * 1024 * 1024,  # 50MB chunks
    )

    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media,
    )

    video_id = None
    print("  Uploading", end="", flush=True)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"\r  Uploading: {pct}%", end="", flush=True)

    video_id = response["id"]
    print(f"\r  Upload complete! Video ID: {video_id}")
    print(f"  URL: https://www.youtube.com/watch?v={video_id}")

    # Set thumbnail if provided
    if config.thumbnail_path and os.path.exists(config.thumbnail_path):
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(config.thumbnail_path, mimetype="image/jpeg"),
            ).execute()
            print(f"  Thumbnail set successfully")
        except Exception as e:
            print(f"  WARNING: Thumbnail upload failed: {e}")

    # Add to playlist if specified
    if config.playlist_id:
        try:
            youtube.playlistItems().insert(
                part="snippet",
                body={
                    "snippet": {
                        "playlistId": config.playlist_id,
                        "resourceId": {
                            "kind": "youtube#video",
                            "videoId": video_id,
                        },
                    },
                },
            ).execute()
            print(f"  Added to playlist: {config.playlist_id}")
        except Exception as e:
            print(f"  WARNING: Playlist add failed: {e}")

    return video_id
