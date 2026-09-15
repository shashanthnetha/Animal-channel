"""
YouTube Data API v3 Direct Uploader.

Uploads YouTube Shorts directly to YouTube using OAuth2 credentials
(client_id, client_secret, refresh_token).
Supports resumable upload and automatic token refresh via standard HTTPS requests.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from typing import Any, List, Optional

import requests
from loguru import logger


YOUTUBE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
YOUTUBE_UPLOAD_URL = (
    "https://www.googleapis.com/upload/youtube/v3/videos"
    "?uploadType=resumable&part=snippet,status"
)


class YouTubeUploadError(Exception):
    """Raised when YouTube upload fails."""


def refresh_access_token(
    client_id: str,
    client_secret: str,
    refresh_token: str,
) -> str:
    """
    Exchange refresh_token for a fresh short-lived access_token.
    """
    payload = {
        "client_id": client_id,
        "client_secret": client_secret,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",
    }
    response = requests.post(YOUTUBE_OAUTH_TOKEN_URL, data=payload, timeout=30)
    if response.status_code != 200:
        raise YouTubeUploadError(
            f"Failed to refresh YouTube access token (HTTP {response.status_code}): {response.text}"
        )
    data = response.json()
    access_token = data.get("access_token")
    if not access_token:
        raise YouTubeUploadError(f"OAuth response missing access_token: {data}")
    return access_token


def upload_video_to_youtube(
    video_path: str,
    title: str,
    description: str,
    tags: Optional[List[str]] = None,
    category_id: str = "15",  # 15 = Pets & Animals
    privacy_status: str = "public",  # public, unlisted, private
    made_for_kids: bool = False,
    client_id: Optional[str] = None,
    client_secret: Optional[str] = None,
    refresh_token: Optional[str] = None,
) -> dict[str, Any]:
    """
    Upload a video file to YouTube via Resumable Upload protocol.
    """
    client_id = client_id or os.getenv("YOUTUBE_CLIENT_ID", "")
    client_secret = client_secret or os.getenv("YOUTUBE_CLIENT_SECRET", "")
    refresh_token = refresh_token or os.getenv("YOUTUBE_REFRESH_TOKEN", "")

    if not (client_id and client_secret and refresh_token):
        raise YouTubeUploadError(
            "Missing YouTube credentials. Please set YOUTUBE_CLIENT_ID, "
            "YOUTUBE_CLIENT_SECRET, and YOUTUBE_REFRESH_TOKEN."
        )

    if not os.path.isfile(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    file_size = os.path.getsize(video_path)
    logger.info(f"Refreshing YouTube OAuth token...")
    access_token = refresh_access_token(client_id, client_secret, refresh_token)

    # Ensure title fits YouTube's 100 character limit
    final_title = title[:100]

    # Ensure #Shorts is present
    if "#Shorts" not in final_title and "#shorts" not in final_title:
        final_title = f"{final_title[:92]} #Shorts"

    metadata = {
        "snippet": {
            "title": final_title,
            "description": description,
            "tags": tags or ["animals", "wildlife", "nature", "shorts"],
            "categoryId": category_id,
        },
        "status": {
            "privacyStatus": privacy_status,
            "selfDeclaredMadeForKids": made_for_kids,
            "embeddable": True,
        },
    }

    # Step 1: Initiate Resumable Upload session
    init_headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=UTF-8",
        "X-Upload-Content-Length": str(file_size),
        "X-Upload-Content-Type": "video/mp4",
    }

    logger.info(f"Initiating YouTube resumable upload session for: {final_title}")
    init_response = requests.post(
        YOUTUBE_UPLOAD_URL,
        headers=init_headers,
        data=json.dumps(metadata),
        timeout=60,
    )

    if init_response.status_code not in (200, 201):
        raise YouTubeUploadError(
            f"Failed to initiate YouTube upload (HTTP {init_response.status_code}): {init_response.text}"
        )

    upload_url = init_response.headers.get("Location")
    if not upload_url:
        raise YouTubeUploadError(
            f"YouTube upload initialization did not return a Location header. Response: {init_response.text}"
        )

    # Step 2: Upload the video file bytes
    logger.info(f"Uploading {file_size / (1024 * 1024):.2f} MB to YouTube...")
    upload_headers = {
        "Content-Length": str(file_size),
        "Content-Type": "video/mp4",
    }

    with open(video_path, "rb") as video_file:
        upload_response = requests.put(
            upload_url,
            headers=upload_headers,
            data=video_file,
            timeout=600,
        )

    if upload_response.status_code not in (200, 201):
        raise YouTubeUploadError(
            f"Failed to upload video content (HTTP {upload_response.status_code}): {upload_response.text}"
        )

    result = upload_response.json()
    video_id = result.get("id")
    video_url = f"https://www.youtube.com/shorts/{video_id}"
    logger.success(f"🎉 YouTube Short successfully uploaded! ID: {video_id} -> {video_url}")

    return {
        "success": True,
        "video_id": video_id,
        "video_url": video_url,
        "title": final_title,
        "privacy_status": privacy_status,
        "raw": result,
    }


def main():
    parser = argparse.ArgumentParser(description="Upload a video to YouTube Data API v3")
    parser.add_argument("--video", required=True, help="Path to the video file")
    parser.add_argument("--title", required=True, help="Video title")
    parser.add_argument("--description", default="", help="Video description")
    parser.add_argument("--tags", default="", help="Comma separated tags")
    parser.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"], help="Privacy status")
    parser.add_argument("--category", default="15", help="YouTube Category ID (default: 15 Pets & Animals)")

    args = parser.parse_args()
    tags_list = [t.strip() for t in args.tags.split(",") if t.strip()]

    try:
        res = upload_video_to_youtube(
            video_path=args.video,
            title=args.title,
            description=args.description,
            tags=tags_list,
            category_id=args.category,
            privacy_status=args.privacy,
        )
        print(json.dumps(res, indent=2))
    except Exception as exc:
        logger.error(f"Upload failed: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
