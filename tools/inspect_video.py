"""python tools/inspect_video.py <token file> <video id> [...]  --  read-only look at any public video and its channel.

For learning from other creators: stats, title, description, tags, length, and the channel's most-viewed uploads.
"""
import sys

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

sys.stdout.reconfigure(encoding="utf-8")
creds = Credentials.from_authorized_user_file(sys.argv[1])
if not creds.valid:
    creds.refresh(Request())
yt = build("youtube", "v3", credentials=creds, cache_discovery=False)
for vid in sys.argv[2:]:
    v = yt.videos().list(part="snippet,statistics,contentDetails", id=vid).execute()["items"][0]
    sn, st = v["snippet"], v["statistics"]
    ch = yt.channels().list(part="snippet,statistics", id=sn["channelId"]).execute()["items"][0]
    cs = ch["statistics"]
    print(f"VIDEO {vid}\n title: {sn['title']}\n channel: {sn['channelTitle']} ({cs.get('subscriberCount')} subs, "
          f"{cs.get('videoCount')} videos, {cs.get('viewCount')} views)\n published: {sn['publishedAt']}  "
          f"length: {v['contentDetails']['duration']}\n views: {st.get('viewCount')}  likes: {st.get('likeCount')}  "
          f"comments: {st.get('commentCount')}\n language: {sn.get('defaultAudioLanguage')}  category: {sn.get('categoryId')}\n"
          f" tags: {', '.join(sn.get('tags', []))}\n description:\n{sn.get('description', '')}\n")
    top = yt.search().list(part="snippet", channelId=sn["channelId"], order="viewCount", type="video", maxResults=15).execute()
    ids = [i["id"]["videoId"] for i in top.get("items", [])]
    rows = yt.videos().list(part="snippet,statistics,contentDetails", id=",".join(ids)).execute().get("items", []) if ids else []
    print(" channel's most viewed:")
    for r in rows:
        print(f"  {int(r['statistics'].get('viewCount', 0)):>10,}  {r['contentDetails']['duration']:>8}  "
              f"{r['snippet']['publishedAt'][:10]}  {r['snippet']['title'][:90]}")
    recent = yt.search().list(part="snippet", channelId=sn["channelId"], order="date", type="video", maxResults=10).execute()
    print(" channel's latest:")
    for i in recent.get("items", []):
        print(f"  {i['snippet']['publishedAt'][:16]}  {i['snippet']['title'][:90]}")
    print()
