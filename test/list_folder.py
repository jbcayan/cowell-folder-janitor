import sys
from drive_config import get_service, PARENT_FOLDER_ID

TARGET_FOLDER_NAME = 'Testing2200'


def get_folder_id(service, folder_name, parent_id):
    query = (
        f"name = '{folder_name}'"
        f" and '{parent_id}' in parents"
        f" and mimeType = 'application/vnd.google-apps.folder'"
        f" and trashed = false"
    )
    results = service.files().list(q=query, fields='files(id, name)').execute()
    items = results.get('files', [])
    return items[0]['id'] if items else None


def list_subdirectories():
    try:
        service = get_service()

        target_folder_id = get_folder_id(service, TARGET_FOLDER_NAME, PARENT_FOLDER_ID)

        if not target_folder_id:
            print(f"Folder '{TARGET_FOLDER_NAME}' not found in the parent folder.")
            return

        print(f"Listing contents of {TARGET_FOLDER_NAME} (ID: {target_folder_id}):")
        query = f"'{target_folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query, fields='files(id, name, mimeType)'
        ).execute()
        items = results.get('files', [])

        if not items:
            print("No files or folders found.")
        else:
            for item in items:
                type_label = (
                    "Folder"
                    if item['mimeType'] == 'application/vnd.google-apps.folder'
                    else "File"
                )
                print(f"[{type_label}] {item['name']} (ID: {item['id']})")

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)


if __name__ == '__main__':
    list_subdirectories()
