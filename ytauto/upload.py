"""Upload to YouTube with the Data API v3 using the saved OAuth token."""
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from . import config

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
]


def _youtube():
    creds = Credentials.from_authorized_user_file(str(config.TOKEN_FILE), SCOPES)
    if not creds.valid:
        creds.refresh(Request())
        config.TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def upload(video_path, script, kind, thumbnail_path=None, publish_at=None):
    hashtags = " ".join(script["hashtags"])
    credits = script.get("credits") or []
    credit_text = ("\n\nVisual credits:\n" + "\n".join(credits)) if credits else ""
    title = script["title"]
    if kind == "short" and "#shorts" not in title.lower():
        title = f"{title} #Shorts"

    body = {
        "snippet": {
            "title": title[:100],
            "description": f"{script['description']}{credit_text}\n\n{hashtags}"[:5000],
            "tags": script["tags"],
            "categoryId": config.YOUTUBE_CATEGORY_ID,
            "defaultLanguage": "hi",
            "defaultAudioLanguage": "hi",
        },
        "status": {
            "privacyStatus": config.UPLOAD_PRIVACY,
            "selfDeclaredMadeForKids": False,
            # Honest AI disclosure: synthetic voice narration.
            "containsSyntheticMedia": True,
        },
    }

    if publish_at:  # YouTube keeps it private and makes it public by itself at this time
        body["status"]["privacyStatus"] = "private"
        body["status"]["publishAt"] = publish_at

    youtube = _youtube()
    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=MediaFileUpload(str(video_path), chunksize=8 << 20, resumable=True),
    )
    response = None
    while response is None:
        _, response = request.next_chunk()
    video_id = response["id"]

    if thumbnail_path:
        youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(thumbnail_path))).execute()
    return video_id
