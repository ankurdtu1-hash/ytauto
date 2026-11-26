"""python tools/set_privacy.py <token file> <video id> <private|unlisted|public>  --  change one video's privacy."""
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

token, video_id, privacy = sys.argv[1:4]
assert privacy in ("private", "unlisted", "public")
creds = Credentials.from_authorized_user_file(token)
if not creds.valid:
    creds.refresh(Request())  # in memory only
yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
items = yt.videos().list(part="status,snippet", id=video_id).execute().get("items", [])
if not items:
    sys.exit(f"{video_id} not found on this channel")
status = {k: v for k, v in items[0]["status"].items() if k in ("privacyStatus", "embeddable", "license",
                                                                 "publicStatsViewable", "selfDeclaredMadeForKids")}
status["privacyStatus"] = privacy
yt.videos().update(part="status", body={"id": video_id, "status": status}).execute()
print(f"{video_id} ({items[0]['snippet']['title']}) is now {privacy}")
