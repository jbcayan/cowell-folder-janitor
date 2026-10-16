"""
Shared Google Drive configuration loaded from service-credentials.json.

Provides two credential strategies:

  get_service()       – service-account credentials (Drive metadata ops,
                        folder management, trashing, etc.)
  get_oauth_services() – OAuth2 user credentials (uploads, Sheet creation;
                         anything that requires real Drive storage quota).

Usage in any test script:
    from drive_config import get_service, get_oauth_services, PARENT_FOLDER_ID
"""

import json
import os

from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']

# Resolve the credentials file relative to this file's directory so scripts
# can be run from any working directory.
CREDS_PATH = os.path.join(os.path.dirname(__file__), '..', 'service-credentials.json')
CREDS_PATH = os.path.normpath(CREDS_PATH)

with open(CREDS_PATH, 'r') as _f:
    _creds_info = json.load(_f)

PARENT_FOLDER_ID: str = _creds_info['PARENT_FOLDER_ID']


def get_service():
    """Return a Drive v3 client authenticated as the service account.

    Use for folder management, listing, trashing — operations that do not
    require the acting user to have Drive storage quota.
    """
    credentials = service_account.Credentials.from_service_account_info(
        _creds_info, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=credentials)


def get_oauth_services():
    """Return (drive_service, sheets_service) authenticated as the real user
    via OAuth2 refresh token.

    Use for file uploads and Google Sheet creation, which require Drive
    storage quota that service accounts do not possess.

    Flow (explicit, upfront):
      POST https://oauth2.googleapis.com/token
        grant_type=refresh_token
        client_id=...
        client_secret=...
        refresh_token=...
      → access_token received → used as Authorization: Bearer on every call.
    """
    import google.auth.transport.requests

    credentials = Credentials(
        token=None,
        refresh_token=_creds_info['GOOGLE_DRIVE_REFRESH_TOKEN'],
        client_id=_creds_info['GOOGLE_DRIVE_CLIENT_ID'],
        client_secret=_creds_info['GOOGLE_DRIVE_CLIENT_SECRET'],
        token_uri='https://oauth2.googleapis.com/token',
        scopes=[
            'https://www.googleapis.com/auth/drive',
            'https://www.googleapis.com/auth/spreadsheets',
        ],
    )

    # Exchange the refresh token for an access token RIGHT NOW, before any
    # Drive/Sheets call.  This is the explicit:
    #   POST https://oauth2.googleapis.com/token  (grant_type=refresh_token)
    # The resulting access_token is then attached as Authorization: Bearer
    # by the google-auth transport layer on every subsequent request.
    credentials.refresh(google.auth.transport.requests.Request())
    print(f"🔑 OAuth2 token refreshed  (expires: {credentials.expiry} UTC)")

    drive_service = build('drive', 'v3', credentials=credentials)
    sheets_service = build('sheets', 'v4', credentials=credentials)
    return drive_service, sheets_service
