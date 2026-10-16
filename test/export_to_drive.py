"""
Export sample files to Google Drive using OAuth2 user credentials.

  - 86_n.jpg   → uploaded as an image file
  - test.json  → created as a Google Sheet (rows written via Sheets API)

Both are placed directly inside PARENT_FOLDER_ID read from service-credentials.json.

Why OAuth2 and not the service account?
  Service accounts have no Drive storage quota of their own, so binary file
  uploads and even native Google file creation fail with storageQuotaExceeded.
  OAuth2 credentials act as the real user who owns the Drive, so their quota
  is used and both operations succeed normally.

Usage (run from the repo root or the test/ directory):
    python test/export_to_drive.py
"""

import json
import os
import sys

from googleapiclient.http import MediaFileUpload

from drive_config import PARENT_FOLDER_ID, get_oauth_services

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.normpath(os.path.join(_HERE, '..', 'sample-export'))

IMAGE_FILE = os.path.join(SAMPLE_DIR, '86_n.jpg')
JSON_FILE = os.path.join(SAMPLE_DIR, 'test.json')

EXPORT_FOLDER_NAME = 'sample-export'


# ---------------------------------------------------------------------------
# 0. Create child folder inside PARENT_FOLDER_ID
# ---------------------------------------------------------------------------
def create_child_folder(drive_service, folder_name):
    print(f"📁 Creating child folder: '{folder_name}' inside parent...")

    file_metadata = {
        'name': folder_name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [PARENT_FOLDER_ID],
    }
    folder = drive_service.files().create(
        body=file_metadata,
        fields='id,name,webViewLink',
    ).execute()

    print(f"  ✅ Created folder: {folder['name']}")
    print(f"     ID:   {folder['id']}")
    if 'webViewLink' in folder:
        print(f"     Link: {folder['webViewLink']}")
    return folder['id']


# ---------------------------------------------------------------------------
# 1. Upload image into child folder
# ---------------------------------------------------------------------------
def upload_image(drive_service, folder_id):
    print(f"\n📤 Uploading image: {os.path.basename(IMAGE_FILE)}")

    media = MediaFileUpload(IMAGE_FILE, mimetype='image/jpeg', resumable=False)
    uploaded = drive_service.files().create(
        body={'name': os.path.basename(IMAGE_FILE), 'parents': [folder_id]},
        media_body=media,
        fields='id,name,webViewLink',
    ).execute()
    media._fd.close()  # release file handle immediately after upload

    print(f"  ✅ Uploaded: {uploaded['name']}")
    print(f"     ID:   {uploaded['id']}")
    if 'webViewLink' in uploaded:
        print(f"     Link: {uploaded['webViewLink']}")
    return uploaded['id']


# ---------------------------------------------------------------------------
# 2. Convert test.json → Google Sheet inside child folder
# ---------------------------------------------------------------------------
def create_sheet_from_json(drive_service, sheets_service, folder_id):
    print(f"\n📊 Creating Google Sheet from: {os.path.basename(JSON_FILE)}")

    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    rows = data.get('rows', [])
    if not rows:
        print("  ⚠️  No rows found in test.json — sheet will be empty.")
        headers = []
    else:
        headers = list(rows[0].keys())

    sheet_name = os.path.splitext(os.path.basename(JSON_FILE))[0]  # "test"

    # --- Step A: create an empty Google Sheet inside the child folder ---
    created = drive_service.files().create(
        body={
            'name': sheet_name,
            'mimeType': 'application/vnd.google-apps.spreadsheet',
            'parents': [folder_id],
        },
        fields='id,name,webViewLink',
    ).execute()

    spreadsheet_id = created['id']
    print(f"  Created spreadsheet: {created['name']} ({spreadsheet_id})")

    # --- Step B: write header row + data rows via the Sheets API ---
    if headers:
        values = [headers] + [
            [str(row.get(h, '')) for h in headers] for row in rows
        ]
        sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range='Sheet1!A1',
            valueInputOption='RAW',
            body={'values': values},
        ).execute()
        print(f"  ✅ Written {len(rows)} data rows + header to Sheet1")

    if 'webViewLink' in created:
        print(f"     Link: {created['webViewLink']}")

    return spreadsheet_id


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    try:
        drive_service, sheets_service = get_oauth_services()

        folder_id = create_child_folder(drive_service, EXPORT_FOLDER_NAME)
        upload_image(drive_service, folder_id)
        create_sheet_from_json(drive_service, sheets_service, folder_id)

        print("\n🎉 Export complete.")
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
