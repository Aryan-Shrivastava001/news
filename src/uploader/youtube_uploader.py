import os
import logging
from pathlib import Path
from typing import List, Optional
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from ..config import (
    YOUTUBE_CLIENT_ID,
    YOUTUBE_CLIENT_SECRET,
    YOUTUBE_REFRESH_TOKEN,
    YOUTUBE_PRIVACY_STATUS
)

logger = logging.getLogger(__name__)

class YouTubeUploader:
    def __init__(
        self,
        client_id: str = YOUTUBE_CLIENT_ID,
        client_secret: str = YOUTUBE_CLIENT_SECRET,
        refresh_token: str = YOUTUBE_REFRESH_TOKEN,
        privacy_status: str = YOUTUBE_PRIVACY_STATUS
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.privacy_status = privacy_status

    def is_configured(self) -> bool:
        return bool(
            self.client_id and self.client_id != "your_client_id.apps.googleusercontent.com"
            and self.client_secret and self.client_secret != "your_client_secret"
            and self.refresh_token and self.refresh_token != "your_refresh_token"
        )

    def upload_short(
        self,
        video_path: Path,
        title: str,
        description: str,
        tags: List[str]
    ) -> Optional[str]:
        """
        Uploads an MP4 file to YouTube as a Short using OAuth2 Refresh Token.
        Returns the published YouTube Video ID.
        If credentials are not yet configured, performs a safe dry-run.
        """
        if not self.is_configured():
            logger.warning(
                "YouTube credentials not configured in environment/secrets. "
                "Simulating upload (DRY RUN)."
            )
            logger.info(f"Mock Upload Target -> Title: '{title}' | Tags: {tags}")
            return "DRY_RUN_VIDEO_ID"

        try:
            creds = Credentials(
                None,
                refresh_token=self.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=["https://www.googleapis.com/auth/youtube.upload"]
            )

            youtube = build("youtube", "v3", credentials=creds)

            # Ensure #shorts is in title or description
            if "#shorts" not in title.lower():
                title = f"{title} #shorts"

            body = {
                "snippet": {
                    "title": title[:100],
                    "description": description,
                    "tags": tags,
                    "categoryId": "20" # Category 20 = Gaming
                },
                "status": {
                    "privacyStatus": self.privacy_status,
                    "selfDeclaredMadeForKids": False
                }
            }

            media = MediaFileUpload(
                str(video_path),
                mimetype="video/mp4",
                resumable=True,
                chunksize=1024 * 1024 * 5 # 5MB chunks
            )

            logger.info(f"Starting YouTube upload: '{title}' ({self.privacy_status})...")
            request = youtube.videos().insert(
                part="snippet,status",
                body=body,
                media_body=media
            )

            response = None
            while response is None:
                status, response = request.next_chunk()
                if status:
                    logger.info(f"Uploaded {int(status.progress() * 100)}%...")

            video_id = response.get("id")
            logger.info(f"Video uploaded successfully! Link: https://youtube.com/shorts/{video_id}")
            return video_id

        except Exception as e:
            logger.error(f"YouTube upload failed: {e}")
            return None
