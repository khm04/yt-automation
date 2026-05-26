"""
TikTok Content Posting API uploader.

Auth model:
  - TIKTOK_ACCESS_TOKEN   — current bearer token (expires in 24 h)
  - TIKTOK_REFRESH_TOKEN  — long-lived token (365 days) used to mint a new access token
  - TIKTOK_CLIENT_KEY / TIKTOK_CLIENT_SECRET — app credentials for the refresh call

Usage:
  from modules.tiktok_uploader import upload_to_tiktok
  tiktok_url = upload_to_tiktok(video_path, title, tags)
"""

import math
import os
import time

import requests

# ──────────────────────────────────────────────
# Config (read at call time so env vars set after
# import are honoured — critical for GitHub Actions)
# ──────────────────────────────────────────────

BASE_URL = "https://open.tiktokapis.com/v2"
CHUNK_SIZE = 10 * 1024 * 1024  # 10 MB


def _cfg(key: str, default: str = "") -> str:
    return os.getenv(key, default)


# ──────────────────────────────────────────────
# Token refresh
# ──────────────────────────────────────────────

def refresh_access_token() -> str:
    """
    Exchange TIKTOK_REFRESH_TOKEN for a fresh access token.
    Returns the new access token string.
    Raises RuntimeError on failure.
    """
    client_key = _cfg("TIKTOK_CLIENT_KEY")
    client_secret = _cfg("TIKTOK_CLIENT_SECRET")
    refresh_token = _cfg("TIKTOK_REFRESH_TOKEN")

    if not all([client_key, client_secret, refresh_token]):
        raise RuntimeError(
            "TikTok refresh requires TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET, "
            "and TIKTOK_REFRESH_TOKEN to be set."
        )

    resp = requests.post(
        f"{BASE_URL}/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": client_key,
            "client_secret": client_secret,
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("error"):
        raise RuntimeError(f"TikTok token refresh failed: {data}")
    return data["access_token"]


def _get_access_token() -> str:
    """
    Return a valid access token, refreshing if TIKTOK_REFRESH_TOKEN is available.
    Precedence:
      1. TIKTOK_ACCESS_TOKEN env var
      2. Refresh via TIKTOK_REFRESH_TOKEN (if set)
    """
    token = _cfg("TIKTOK_ACCESS_TOKEN")
    if token:
        return token
    # Try refresh
    print("  [TikTok] No access token found — attempting refresh...")
    return refresh_access_token()


# ──────────────────────────────────────────────
# Upload initialization
# ──────────────────────────────────────────────

def _build_caption(title: str, tags: list) -> str:
    """Build TikTok caption: title + hashtags, max 2 200 chars."""
    hashtags = " ".join(f"#{t.replace(' ', '').lower()}" for t in tags)
    caption = f"{title}\n\n{hashtags}"
    return caption[:2200]


def init_upload(
    access_token: str,
    video_size: int,
    title: str,
    tags: list,
) -> dict:
    """
    Call /v2/post/publish/video/init/ and return the response data dict
    containing ``publish_id`` and ``upload_url``.
    """
    total_chunks = math.ceil(video_size / CHUNK_SIZE)
    caption = _build_caption(title, tags)

    payload = {
        "post_info": {
            "title": caption,
            "privacy_level": "PUBLIC_TO_EVERYONE",
            "disable_comment": False,
            "auto_add_music": True,
        },
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": video_size,
            "chunk_size": CHUNK_SIZE,
            "total_chunk_count": total_chunks,
        },
    }

    resp = requests.post(
        f"{BASE_URL}/post/publish/video/init/",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        },
        json=payload,
        timeout=30,
    )
    resp.raise_for_status()
    body = resp.json()
    if body.get("error", {}).get("code", "ok") != "ok":
        raise RuntimeError(f"TikTok init_upload error: {body}")
    return body["data"]


# ──────────────────────────────────────────────
# Chunked file upload
# ──────────────────────────────────────────────

def upload_chunks(upload_url: str, video_path: str, video_size: int) -> None:
    """Upload the video file to TikTok's upload URL in 10 MB chunks."""
    total_chunks = math.ceil(video_size / CHUNK_SIZE)
    print(f"  [TikTok] Uploading {video_size / 1024 / 1024:.1f} MB in {total_chunks} chunk(s)...")

    with open(video_path, "rb") as fh:
        for chunk_idx in range(total_chunks):
            start = chunk_idx * CHUNK_SIZE
            end = min(start + CHUNK_SIZE, video_size) - 1
            chunk_data = fh.read(CHUNK_SIZE)
            chunk_len = len(chunk_data)

            resp = requests.put(
                upload_url,
                headers={
                    "Content-Type": "video/mp4",
                    "Content-Range": f"bytes {start}-{end}/{video_size}",
                    "Content-Length": str(chunk_len),
                },
                data=chunk_data,
                timeout=120,
            )
            if resp.status_code not in (200, 206):
                raise RuntimeError(
                    f"TikTok chunk upload failed (chunk {chunk_idx}): "
                    f"{resp.status_code} {resp.text[:300]}"
                )
            print(f"  [TikTok]   Chunk {chunk_idx + 1}/{total_chunks} OK")


# ──────────────────────────────────────────────
# Publish status polling
# ──────────────────────────────────────────────

def check_publish_status(
    access_token: str,
    publish_id: str,
    max_retries: int = 20,
    poll_interval: int = 5,
) -> str:
    """
    Poll until the video transitions out of PROCESSING_UPLOAD / PROCESSING_DOWNLOAD.
    Returns the final status string (e.g. "PUBLISH_COMPLETE").
    Raises RuntimeError if it fails or times out.
    """
    for attempt in range(max_retries):
        resp = requests.post(
            f"{BASE_URL}/post/publish/status/fetch/",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json; charset=UTF-8",
            },
            json={"publish_id": publish_id},
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()

        status = body.get("data", {}).get("status", "UNKNOWN")
        print(f"  [TikTok] Publish status ({attempt + 1}/{max_retries}): {status}")

        if status == "PUBLISH_COMPLETE":
            return status
        if status in ("FAILED", "PUBLISH_FAILED"):
            fail_reason = body.get("data", {}).get("fail_reason", "unknown")
            raise RuntimeError(f"TikTok publish failed: {fail_reason}")

        time.sleep(poll_interval)

    raise RuntimeError(
        f"TikTok publish status did not complete after {max_retries} polls."
    )


# ──────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────

def upload_to_tiktok(
    video_path: str,
    title: str,
    tags: list,
) -> str:
    """
    Upload *video_path* to TikTok and return the profile URL.

    Steps:
      1. Obtain a valid access token (from env or refresh).
      2. Initialize upload → get publish_id + upload_url.
      3. Upload video in chunks.
      4. Poll publish status until complete.

    Returns:
        str: TikTok profile URL (videos are live on the authenticated account).

    Raises:
        RuntimeError: on any API or auth error.
        EnvironmentError: if no TikTok credentials are configured at all.
    """
    # Guard: skip silently when no TikTok credentials are configured
    if not _cfg("TIKTOK_ACCESS_TOKEN") and not _cfg("TIKTOK_REFRESH_TOKEN"):
        raise EnvironmentError(
            "TikTok upload skipped: neither TIKTOK_ACCESS_TOKEN nor "
            "TIKTOK_REFRESH_TOKEN is set."
        )

    print(f"  [TikTok] Starting upload: {os.path.basename(video_path)}")

    access_token = _get_access_token()
    video_size = os.path.getsize(video_path)

    # 1. Init upload
    print("  [TikTok] Initializing upload...")
    upload_data = init_upload(access_token, video_size, title, tags)
    publish_id = upload_data["publish_id"]
    upload_url = upload_data["upload_url"]
    print(f"  [TikTok] publish_id: {publish_id}")

    # 2. Upload chunks
    upload_chunks(upload_url, video_path, video_size)

    # 3. Poll for completion
    print("  [TikTok] Waiting for publish to complete...")
    check_publish_status(access_token, publish_id)

    # TikTok direct-post videos appear on the user's profile.
    # The API doesn't return a per-video URL at publish time, so we return
    # the account's video feed URL.
    profile_url = "https://www.tiktok.com/@RedditStoriesDaily"
    print(f"  [TikTok] Published! Profile: {profile_url}")
    return profile_url
