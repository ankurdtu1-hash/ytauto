"""One-time YouTube login. Opens a browser; sign in with the CHANNEL's Google account and click Allow.

Creates token.json next to this file. Copy token.json to the server together with the code.
"""
from google_auth_oauthlib.flow import InstalledAppFlow

from ytauto import config
from ytauto.upload import SCOPES

flow = InstalledAppFlow.from_client_secrets_file(str(config.CLIENT_SECRET_FILE), SCOPES)
creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
config.TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
print(f"Saved {config.TOKEN_FILE}")
