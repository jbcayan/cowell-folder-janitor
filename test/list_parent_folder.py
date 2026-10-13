import os
from datetime import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service-credentials.json'
PARENT_FOLDER_ID = '1IGVqByX0Nr_skGrV2NqxzxwTqv6Sc4uW'

def format_date(date_str):
    # Google API returns date in RFC 3339 format (e.g., 2023-10-13T10:00:00.000Z)
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except ValueError:
        try:
            dt = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%SZ')
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return date_str

def list_parent_contents():
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        service = build('drive', 'v3', credentials=creds)

        print(f"Listing all contents in the Parent folder (Co Test - {PARENT_FOLDER_ID}):")
        
        # Updated fields to include createdTime
        query = f"'{PARENT_FOLDER_ID}' in parents and trashed = false"
        results = service.files().list(q=query, fields="files(id, name, mimeType, createdTime)").execute()
        items = results.get('files', [])

        if not items:
            print("No files or folders found in the parent directory.")
        else:
            folders = [i for i in items if i['mimeType'] == 'application/vnd.google-apps.folder']
            files = [i for i in items if i['mimeType'] != 'application/vnd.google-apps.folder']

            print("\n📂 Directories:")
            if not folders:
                print("  None")
            for folder in folders:
                created = format_date(folder.get('createdTime', 'Unknown'))
                print(f"  - {folder['name']} (ID: {folder['id']}) | Created: {created}")

            print("\n📄 Files:")
            if not files:
                print("  None")
            for file in files:
                created = format_date(file.get('createdTime', 'Unknown'))
                print(f"  - {file['name']} (ID: {file['id']}) | Created: {created}")

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    list_parent_contents()
