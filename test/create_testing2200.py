import sys
from drive_config import get_service, PARENT_FOLDER_ID

FOLDER_NAME = 'Testing2200'


def main():
    try:
        service = get_service()

        file_metadata = {
            'name': FOLDER_NAME,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [PARENT_FOLDER_ID],
        }

        created = service.files().create(
            body=file_metadata,
            fields='id,name,webViewLink',
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
