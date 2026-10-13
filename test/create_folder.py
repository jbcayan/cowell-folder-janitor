import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service-credentials.json'
PARENT_FOLDER_ID = '1IGVqByX0Nr_skGrV2NqxzxwTqv6Sc4uW'
NEW_FOLDER_NAME = 'Testing2200'

def create_folder():
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        file_metadata = {
            'name': NEW_FOLDER_NAME,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [PARENT_FOLDER_ID]
        }
        
        file = service.files().create(body=file_metadata, fields='id').execute()
        print(f"Successfully created folder '{NEW_FOLDER_NAME}' with ID: {file.get('id')}")
        return file.get('id')
    except Exception as e:
        print(f"An error occurred: {e}")
        print("\nTIP: Ensure the service account email (test-co@test-co-511505.iam.gserviceaccount.com) has 'Editor' access to the parent folder.")
        return None

if __name__ == '__main__':
    create_folder()
