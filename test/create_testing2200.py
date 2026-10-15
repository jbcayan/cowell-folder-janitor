import json
import sys
from google.oauth2 import service_account
from googleapiclient.discovery import build

CREDS_PATH = 'service-credentials.json'
SCOPES = ['https://www.googleapis.com/auth/drive']
# PARENT_FOLDER_ID = '1IGVqByX0Nr_skGrV2NqxzxwTqv6Sc4uW'
PARENT_FOLDER_ID = '1S0EX9tnYggKJ5_-fDt4IXVLnNJyam3TJ'
FOLDER_NAME = 'Testing2200'

def main():
    try:
        with open(CREDS_PATH, 'r') as f:
            creds_info = json.load(f)
        credentials = service_account.Credentials.from_service_account_info(
            creds_info, scopes=SCOPES
        )
        service = build('drive', 'v3', credentials=credentials)
        file_metadata = {
            'name': FOLDER_NAME,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [PARENT_FOLDER_ID]
        }
        created = service.files().create(
            body=file_metadata,
            fields='id,name,webViewLink'
        ).execute()
        print(f"Created folder: {created['name']}")
        print(f"ID: {created['id']}")
        if 'webViewLink' in created:
            print(f"Link: {created['webViewLink']}")
        return 0
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

if __name__ == '__main__':
    sys.exit(main())