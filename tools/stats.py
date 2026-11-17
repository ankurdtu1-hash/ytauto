"""python tools/stats.py [token files]  --  read-only channel and recent video stats for both channels (YouTube Data API, readonly scope)."""
import sys
from datetime import datetime, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

sys.stdout.reconfigure(encoding="utf-8")
SCOPES = ["https://www.googleapis.com/auth/youtube.upload", "https://www.googleapis.com/auth/youtube.readonly"]

for token in sys.argv[1:] or ("token_trending.json", "token.json"):
    creds = Credentials.from_authorized_user_file(token, SCOPES)
    if not creds.valid:
        creds.refresh(Request())  # in memory only
    yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
    ch = yt.channels().list(part="snippet,statistics,contentDetails", mine=True).execute()["items"][0]
    st = ch["statistics"]
    print(f"\n=== {ch['snippet']['title']}: {st.get('subscriberCount')} subs, {st['viewCount']} views, {st['videoCount']} videos")
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids = [i["contentDetails"]["videoId"] for i in
           yt.playlistItems().list(part="contentDetails", playlistId=uploads, maxResults=50).execute()["items"]]
    vids = yt.videos().list(part="snippet,statistics,status", id=",".join(ids)).execute()["items"]
    now = datetime.now(timezone.utc)
    for v in vids:
        s, sn, stt = v["statistics"], v["snippet"], v["status"]
        when = stt.get("publishAt") or sn["publishedAt"]
        state = "scheduled" if stt.get("publishAt") and stt["privacyStatus"] == "private" else stt["privacyStatus"]
        print(f"{when[:16]} {state:9} {int(s.get('viewCount', 0)):6} views {int(s.get('likeCount', 0)):4} likes "
              f"{int(s.get('commentCount', 0)):3} cmts  {sn['title'][:60]}")
