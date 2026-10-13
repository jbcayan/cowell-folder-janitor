import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service-credentials.json'
# IDs of the folders to move
FOLDER_IDS_TO_MOVE = ['1cLphf_Li0f3fiJaaKAqmiChoT4QRqzM6', '1R0rosM6mvwAnntWnnY6lA-X9obZDpj9R']
# ID of the destination folder (Testing2200)
DESTINATION_FOLDER_ID = '1J6h7eSGwM4JJe21wyaOb5weFoTcvdAIO'

def move_folders():
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        for fid in FOLDER_IDS_TO_MOVE:
            # Get current parents to remove them
            file = service.files().get(fileId=fid, fields='parents').execute()
            previous_parents = ",".join(file.get('parents', []))

            # Move the file to the new parent
            service.files().update(
                fileId=fid,
                addParents=DESTINATION_FOLDER_ID,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            print(f"✅ Moved folder {fid} to Testing2200")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    move_folders()
