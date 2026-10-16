import sys
from datetime import datetime
from drive_config import get_service, PARENT_FOLDER_ID


def format_date(date_str):
    for fmt in ('%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ'):
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
    return date_str


def list_parent_contents():
    try:
        service = get_service()

        print(f"Listing all contents in the Parent folder (ID: {PARENT_FOLDER_ID}):")

        query = f"'{PARENT_FOLDER_ID}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            fields='files(id, name, mimeType, createdTime)',
        ).execute()
        items = results.get('files', [])

        if not items:
            print("No files or folders found in the parent directory.")
            return

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
        print(f"An error occurred: {e}", file=sys.stderr)


if __name__ == '__main__':
    list_parent_contents()
