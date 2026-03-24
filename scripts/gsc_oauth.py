# scripts/gsc_oauth.py
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

flow = InstalledAppFlow.from_client_secrets_file(
    "/path/to/client_secret_.json",
    SCOPES
)
creds = flow.run_local_server(port=0)

# Save token for later use
import json
with open(".gsc_token.json", "w") as f:
    f.write(creds.to_json())

print("OAuth token saved to .gsc_token.json")
