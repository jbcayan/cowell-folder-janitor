import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service-credentials.json'
PARENT_FOLDER_ID = '1IGVqByX0Nr_skGrV2NqxzxwTqv6Sc4uW'
TARGET_FOLDER_NAME = 'Testing2200'

def get_folder_id(service, folder_name, parent_id):
    query = f"name = '{folder_name}' and '{parent_id}' in parents and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    return items[0]['id'] if items else None

def list_subdirectories():
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        target_folder_id = get_folder_id(service, TARGET_FOLDER_NAME, PARENT_FOLDER_ID)
        
        if not target_folder_id:
            print(f"Folder '{TARGET_FOLDER_NAME}' not found in the parent folder.")
            return

        print(f"Listing contents of {TARGET_FOLDER_NAME} (ID: {target_folder_id}):")
        query = f"'{target_folder_id}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        items = results.get('files', [])

        if not items:
            print("No files or folders found.")
        else:
            for item in items:
                type_label = "Folder" if item['mimeType'] == 'application/vnd.google-apps.folder' else "File"
                print(f"[{type_label}] {item['name']} (ID: {item['id']})")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    list_subdirectories()
