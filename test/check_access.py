import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service-credentials.json'
FOLDER_IDS = ['1cLphf_Li0f3fiJaaKAqmiChoT4QRqzM6', '1R0rosM6mvwAnntWnnY6lA-X9obZDpj9R']

def check_access():
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        for fid in FOLDER_IDS:
            try:
                file = service.files().get(fileId=fid, fields='id, name').execute()
                print(f"✅ Access Granted: {file['name']} ({fid})")
            except Exception as e:
                print(f"❌ Access Denied for {fid}: {e}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    check_access()
