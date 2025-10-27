"""Authentication helpers for Google Drive API access."""

from pathlib import Path

import httplib2
from apiclient import discovery
from oauth2client import client, tools
from oauth2client.file import Storage

from .constants import APPLICATION_NAME, CLIENT_SECRET_FILE, SCOPES


def get_credentials(flags):
    """Obtain or refresh OAuth2 credentials."""
    credential_path = Path("token.json")
    store = Storage(str(credential_path))
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:
            credentials = tools.run(flow, store)
        print(f"Storing credentials to {credential_path}")
    return credentials


def build_drive_service(credentials):
    """Create an authorized Drive service client."""
    http = credentials.authorize(httplib2.Http())
    return discovery.build("drive", "v3", http=http)
