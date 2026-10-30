# One-time setup (about 1 hour, never again)

After this, the server makes and uploads **1 Short every day at 5:30 PM** and **1 long video every Sunday** by itself.

## 1. YouTube channel (10 min)
1. Create a new Gmail account just for the channel (personal phone number, not work).
2. Open youtube.com → profile picture → **Create a channel**. Name: **Kya Aap Jaante Hain** (or your choice).
3. YouTube Studio → Settings → Channel → **Feature eligibility** → verify phone (unlocks custom thumbnails and long videos).

## 2. Google Cloud – YouTube API (15 min), signed in with the channel Gmail
1. Go to https://console.cloud.google.com → create project **ytauto**.
2. **APIs & Services → Library** → enable **YouTube Data API v3**.
3. **OAuth consent screen** → External → app name `ytauto`, your email → add yourself as test user → Save.
4. Then click **Publish app** (set to "In production"). Without this, the login expires every 7 days.
5. **Credentials → Create credentials → OAuth client ID → Desktop app** → Download JSON.
   Rename it `client_secret.json` and put it in `C:\Users\asingh\personal\`.
6. Fill in YouTube's API audit form so uploads can be public:
   https://support.google.com/youtube/contact/yt_api_form
   (Until approved, videos upload as private.)

## 3. API keys (10 min)
1. **Claude**: https://console.anthropic.com → add ₹500-ish credit → API Keys → create key.
2. **Pixabay** (free stock video): https://pixabay.com/api/docs/ → log in → copy the key shown under "Parameters".
3. Copy `.env.example` to `.env` and paste both keys into it with Notepad.

## 4. Cloud server (15 min)
Any Ubuntu 24.04 server with **2 vCPU / 4 GB RAM** works, for example:
- Hetzner Cloud **CX22** (about ₹450-500/month), or
- DigitalOcean **2 GB droplet** (about ₹1,000/month).

When creating it, choose **Ubuntu 24.04** and add the SSH public key Claude gives you. Send Claude the server IP.

## 5. Claude does the rest
- Runs `auth_youtube.py` once on this PC (a browser opens → pick the channel account → **Allow**).
- Copies the code, `.env` and `token.json` to the server and runs `deploy/setup_server.sh`.
- Makes a test video and checks it before the schedule takes over.

## Monthly cost
| Item | Approx. |
|---|---|
| Server | ₹450–1,000 |
| Claude API (30 Shorts + 4 long videos) | ₹400–600 |
| Voice, stock footage, YouTube API | free |

## Optional
- Put a few royalty-free `.mp3` files in `assets/music/` (e.g. from the YouTube Audio Library) for background music.
