import os
import json
import logging
from datetime import datetime, timedelta, timezone

import google.auth.transport.requests
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Configuration — all values come from Lambda environment variables
# ---------------------------------------------------------------------------
PARENT_FOLDER_ID = os.environ.get('PARENT_FOLDER_ID', '')

# Expiration priority: EXPIRATION_MINUTES > EXPIRATION_HOURS > default 24 h
_exp_minutes = os.environ.get('EXPIRATION_MINUTES')
_exp_hours   = os.environ.get('EXPIRATION_HOURS')

if _exp_minutes:
    EXPIRATION_DELTA = timedelta(minutes=int(_exp_minutes))
    logger.info(f"Using EXPIRATION_MINUTES = {_exp_minutes}")
elif _exp_hours:
    EXPIRATION_DELTA = timedelta(hours=int(_exp_hours))
    logger.info(f"Using EXPIRATION_HOURS = {_exp_hours} (legacy)")
else:
    EXPIRATION_DELTA = timedelta(hours=24)
    logger.info("Using default expiration: 24 hours")


# ---------------------------------------------------------------------------
# Auth
#
# Two credential strategies, mirroring the local test scripts:
#
#   get_oauth_service()  — OAuth2 refresh token flow (primary)
#     POST https://oauth2.googleapis.com/token
#       grant_type    = refresh_token
#       client_id     = GOOGLE_DRIVE_CLIENT_ID
#       client_secret = GOOGLE_DRIVE_CLIENT_SECRET
#       refresh_token = GOOGLE_DRIVE_REFRESH_TOKEN
#     → access_token → Authorization: Bearer on every request
#     Owns folders created by the real Google user → can trash them.
#
#   get_sa_service()  — service account (fallback)
#     Owns folders it created itself → can trash those.
#
# The trashing logic tries OAuth2 first; if it gets a 403 it retries with
# the service account.  This covers both ownership cases automatically.
# ---------------------------------------------------------------------------
def get_oauth_service():
    client_id     = os.environ.get('GOOGLE_DRIVE_CLIENT_ID', '')
    client_secret = os.environ.get('GOOGLE_DRIVE_CLIENT_SECRET', '')
    refresh_token = os.environ.get('GOOGLE_DRIVE_REFRESH_TOKEN', '')

    if not all([client_id, client_secret, refresh_token]):
        raise ValueError(
            "Missing one or more required env vars: "
            "GOOGLE_DRIVE_CLIENT_ID, GOOGLE_DRIVE_CLIENT_SECRET, GOOGLE_DRIVE_REFRESH_TOKEN"
        )

    credentials = Credentials(
        token=None,
        refresh_token=refresh_token,
        client_id=client_id,
        client_secret=client_secret,
        token_uri='https://oauth2.googleapis.com/token',
        scopes=['https://www.googleapis.com/auth/drive'],
    )
    credentials.refresh(google.auth.transport.requests.Request())
    logger.info(f"OAuth2 token refreshed (expires: {credentials.expiry} UTC)")
    return build('drive', 'v3', credentials=credentials)


def get_sa_service():
    sa_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '')
    if not sa_json:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON env var is missing or empty.")

    sa_info = json.loads(sa_json)
    creds = service_account.Credentials.from_service_account_info(
        sa_info, scopes=['https://www.googleapis.com/auth/drive']
    )
    return build('drive', 'v3', credentials=creds)


# ---------------------------------------------------------------------------
# Lambda handler
# ---------------------------------------------------------------------------
def lambda_handler(event, context):
    """Trash expired folders in PARENT_FOLDER_ID.

    Tries OAuth2 (real user) first; falls back to the service account for
    folders the service account created itself.
    """
    logger.info("Starting Google Drive Janitor cleanup...")

    if not PARENT_FOLDER_ID:
        logger.error("PARENT_FOLDER_ID environment variable is not set.")
        return {'statusCode': 500, 'body': json.dumps('PARENT_FOLDER_ID not set.')}

    try:
        oauth_service = get_oauth_service()
        sa_service    = get_sa_service()

        logger.info(f"PARENT_FOLDER_ID = {PARENT_FOLDER_ID}")
        logger.info(f"EXPIRATION_DELTA = {EXPIRATION_DELTA}")

        # List ALL non-trashed folders in the parent (for debug visibility)
        all_results = oauth_service.files().list(
            q=(
                f"'{PARENT_FOLDER_ID}' in parents"
                f" and mimeType = 'application/vnd.google-apps.folder'"
                f" and trashed = false"
            ),
            fields="files(id, name, createdTime)",
            pageSize=100,
        ).execute()

        all_items = all_results.get('files', [])
        logger.info(f"Total folders in parent: {len(all_items)}")
        for f in all_items:
            logger.info(f"  Found: {f['name']} | Created: {f['createdTime']} | ID: {f['id']}")

        cutoff_time = datetime.now(timezone.utc) - EXPIRATION_DELTA
        cutoff_str  = cutoff_time.strftime('%Y-%m-%dT%H:%M:%SZ')

        logger.info(f"Current UTC : {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        logger.info(f"Cutoff time : {cutoff_str}")

        # Fetch only the expired folders
        expired_results = oauth_service.files().list(
            q=(
                f"'{PARENT_FOLDER_ID}' in parents"
                f" and mimeType = 'application/vnd.google-apps.folder'"
                f" and trashed = false"
                f" and createdTime < '{cutoff_str}'"
            ),
            fields="files(id, name, createdTime)",
            pageSize=100,
        ).execute()

        items = expired_results.get('files', [])

        if not items:
            logger.info("No expired folders found to trash.")
            return {'statusCode': 200, 'body': json.dumps('No expired folders found.')}

        logger.info(f"Found {len(items)} expired folder(s). Starting trashing...")

        trashed_count = 0
        for item in items:
            folder_id   = item['id']
            folder_name = item['name']
            created_at  = item['createdTime']
            try:
                # Primary: OAuth2 (owns user-created folders)
                oauth_service.files().update(
                    fileId=folder_id,
                    body={'trashed': True},
                ).execute()
                logger.info(f"Trashed: {folder_name} (ID: {folder_id}, Created: {created_at})")
                trashed_count += 1

            except HttpError as e:
                if e.resp.status != 403:
                    logger.error(f"Failed to trash {folder_name} ({folder_id}): {e}")
                    continue

                # Fallback: service account (owns folders it created itself)
                logger.warning(
                    f"OAuth2 denied for {folder_name} ({folder_id}) — retrying with service account..."
                )
                try:
                    sa_service.files().update(
                        fileId=folder_id,
                        body={'trashed': True},
                    ).execute()
                    logger.info(f"Trashed [SA]: {folder_name} (ID: {folder_id}, Created: {created_at})")
                    trashed_count += 1
                except HttpError as e2:
                    logger.error(f"SA also failed for {folder_name} ({folder_id}): {e2}")
                except Exception as e2:
                    logger.error(f"SA unexpected error for {folder_name}: {e2}")

            except Exception as e:
                logger.error(f"Unexpected error trashing {folder_name}: {e}")

        logger.info(f"Cleanup complete. Total folders trashed: {trashed_count}")
        return {'statusCode': 200, 'body': json.dumps(f"Trashed {trashed_count} folder(s).")}

    except Exception as e:
        logger.error(f"Critical error in lambda_handler: {e}")
        return {'statusCode': 500, 'body': json.dumps(f"Internal Server Error: {str(e)}")}
