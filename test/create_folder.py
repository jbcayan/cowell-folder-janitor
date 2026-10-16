import sys
from drive_config import get_service, PARENT_FOLDER_ID

NEW_FOLDER_NAME = 'Testing2200'


def create_folder():
    try:
        service = get_service()

        file_metadata = {
            'name': NEW_FOLDER_NAME,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [PARENT_FOLDER_ID],
        }

        file = service.files().create(
            body=file_metadata,
            fields='id,name,webViewLink',
        ).execute()

        print(f"Created folder: {file['name']}")
        print(f"ID: {file['id']}")
        if 'webViewLink' in file:
            print(f"Link: {file['webViewLink']}")
        return file['id']

    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
        return None


if __name__ == '__main__':
    create_folder()
