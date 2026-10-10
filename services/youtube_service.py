"""
ActionBridge AI - YouTube Video Ingestion & Transcript Extraction Service
Extracts video metadata, channel details, and closed-caption transcripts to power
video-driven diagnostic strategic analysis.
"""

import re
from typing import Any, Dict, Optional
import requests

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    HAS_YOUTUBE_API = True
except ImportError:
    HAS_YOUTUBE_API = False

from core.schemas import YouTubeVideoContext


def extract_youtube_video_id(url_or_id: str) -> Optional[str]:
    """
    Extracts the 11-character YouTube video ID from various YouTube URL formats
    or validates an already-provided video ID.
    Supports:
    - https://www.youtube.com/watch?v=VIDEO_ID
    - https://youtu.be/VIDEO_ID
    - https://www.youtube.com/embed/VIDEO_ID
    - https://www.youtube.com/shorts/VIDEO_ID
    - https://www.youtube.com/live/VIDEO_ID
    - Direct VIDEO_ID
    """
    if not url_or_id or not isinstance(url_or_id, str):
        return None

    cleaned = url_or_id.strip()

    # Regex covering standard watch URLs, shortlinks, shorts, embeds, and lives
    patterns = [
        r"(?:v=|\/v\/|youtu\.be\/|\/embed\/|\/shorts\/|\/live\/)([a-zA-Z0-9_-]{11})",
        r"^([a-zA-Z0-9_-]{11})$"
    ]

    for pattern in patterns:
        match = re.search(pattern, cleaned)
        if match:
            return match.group(1)

    return None


def fetch_youtube_metadata(video_id: str) -> Dict[str, str]:
    """
    Fetches public oEmbed metadata (Title, Author/Channel, Thumbnail) without requiring an API key.
    """
    fallback_thumbnail = f"https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
    metadata = {
        "title": f"YouTube Video ({video_id})",
        "channel_title": "YouTube Creator",
        "thumbnail_url": fallback_thumbnail
    }

    try:
        oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        res = requests.get(oembed_url, timeout=8)
        if res.status_code == 200:
            data = res.json()
            metadata["title"] = data.get("title", metadata["title"])
            metadata["channel_title"] = data.get("author_name", metadata["channel_title"])
            metadata["thumbnail_url"] = data.get("thumbnail_url", fallback_thumbnail)
    except Exception as e:
        print(f"[ActionBridge] oEmbed fetch notice: {e}")

    return metadata


def fetch_youtube_transcript(video_id: str, max_chars: int = 40000) -> Optional[str]:
    """
    Fetches full closed captions / transcript for the video if available.
    Supports both youtube-transcript-api v1.2+ (fetch/to_raw_data) and legacy (get_transcript).
    """
    if not HAS_YOUTUBE_API:
        return None

    try:
        raw_items = []
        api = YouTubeTranscriptApi()

        # Check for v1.2+ .fetch() method
        if hasattr(api, "fetch"):
            fetched = api.fetch(video_id)
            if hasattr(fetched, "to_raw_data"):
                raw_items = fetched.to_raw_data()
        # Fallback to class-level get_transcript if available
        elif hasattr(YouTubeTranscriptApi, "get_transcript"):
            raw_items = YouTubeTranscriptApi.get_transcript(video_id)

        if not raw_items:
            return None

        # Concatenate text snippets
        text_snippets = []
        for item in raw_items:
            snippet = item.get("text", "").strip()
            # Remove music notes like [Music] or (Music)
            snippet = re.sub(r"\[.*?\]|\(.*?\)", "", snippet).strip()
            if snippet:
                text_snippets.append(snippet)

        full_text = " ".join(text_snippets)
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "... [transcript truncated for optimal reasoning]"

        return full_text if full_text.strip() else None

    except Exception as e:
        print(f"[ActionBridge] Transcript fetch notice for {video_id}: {e}")
        return None


def get_youtube_video_context(url_or_id: str) -> YouTubeVideoContext:
    """
    High-level orchestrator: parses URL, fetches video metadata and transcript,
    and returns a structured YouTubeVideoContext.
    """
    video_id = extract_youtube_video_id(url_or_id)
    if not video_id:
        raise ValueError(
            "Could not parse a valid YouTube Video ID. Please check the URL (e.g., https://www.youtube.com/watch?v=... or https://youtu.be/...)."
        )

    canonical_url = f"https://www.youtube.com/watch?v={video_id}"
    metadata = fetch_youtube_metadata(video_id)
    transcript = fetch_youtube_transcript(video_id)

    has_transcript = bool(transcript and len(transcript.strip()) > 50)
    word_count = len(transcript.split()) if has_transcript else 0

    return YouTubeVideoContext(
        video_id=video_id,
        url=canonical_url,
        title=metadata["title"],
        channel_title=metadata["channel_title"],
        thumbnail_url=metadata["thumbnail_url"],
        transcript_text=transcript or "",
        has_transcript=has_transcript,
        word_count=word_count
    )
