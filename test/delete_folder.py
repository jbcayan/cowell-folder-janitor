import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service-credentials.json'
# The ID for "Me and My" folder
FOLDER_ID_TO_DELETE = '1S0EX9tnYggKJ5_-fDt4IXVLnNJyam3TJ'

def delete_folder():
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        # First, verify the name of the folder we are about to delete
        file = service.files().get(fileId=FOLDER_ID_TO_DELETE, fields='name').execute()
        folder_name = file.get('name')
        
        print(f"Attempting to permanently delete folder: {folder_name} ({FOLDER_ID_TO_DELETE})")
        
        # Permanent deletion
        service.files().delete(fileId=FOLDER_ID_TO_DELETE).execute()
        
        print(f"✅ Successfully deleted folder: {folder_name}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    delete_folder()
