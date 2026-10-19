"""
Move one or more Drive folders to trash using OAuth2 user credentials.

Why OAuth2 and not the service account?
  Only the folder OWNER can trash items in a regular Drive. Folders created
  via the OAuth2 flow are owned by the real user, so the service account
  (Editor role only) gets a 403. The OAuth2 token acts as the real user and
  succeeds on both user-owned and service-account-created folders.

Usage:
    # Pass IDs directly as arguments
    python test/trash_folders.py 1_2QVnm7utUWoFWj20zT0DMeQ2fCwJjFr 1TCFBCkngUo00on02qkBtFcY1_Tan1Xua

    # Interactive mode (no arguments)
    python test/trash_folders.py
"""

import sys
from googleapiclient.errors import HttpError
from drive_config import get_oauth_services, get_service


def trash_folders(oauth_service, sa_service, folder_ids):
    """Trash folders, trying OAuth2 first then falling back to service account.

    Folders created by the OAuth2 user require the OAuth2 token (owner).
    Folders created by the service account require the service account token.
    """
    print(f"\nAttempting to trash {len(folder_ids)} folder(s)...\n")

    success = 0
    for folder_id in folder_ids:
        try:
            file = oauth_service.files().get(fileId=folder_id, fields='name').execute()
            folder_name = file.get('name')

            try:
                # Primary: OAuth2 (owns folders created by the real user)
                oauth_service.files().update(
                    fileId=folder_id,
                    body={'trashed': True},
                ).execute()
                print(f"  ✅ Trashed: {folder_name} ({folder_id})")
                success += 1

            except HttpError as e:
                if e.resp.status != 403:
                    raise

                # Fallback: service account (owns folders it created itself)
                print(f"  ↩️  OAuth2 denied — retrying with service account...")
                sa_service.files().update(
                    fileId=folder_id,
                    body={'trashed': True},
                ).execute()
                print(f"  ✅ Trashed: {folder_name} ({folder_id}) [via service account]")
                success += 1

        except HttpError as e:
            if e.resp.status == 404:
                print(f"  ❌ Not found: {folder_id}")
            elif e.resp.status == 403:
                print(f"  ❌ Permission denied by both OAuth2 and service account: {folder_id}")
            else:
                print(f"  ❌ Error {e.resp.status} for {folder_id}: {e}")
        except Exception as e:
            print(f"  ❌ Unexpected error for {folder_id}: {e}")

    print(f"\n🎉 Done! Successfully trashed {success}/{len(folder_ids)} folders.")


def main():
    folder_ids = sys.argv[1:]

    if not folder_ids:
        print("Enter folder IDs to trash (one per line, empty line to finish):")
        print("Example: 16WSIzD9SU1E37BIr4XajDYj1okpn_gT-")
        while True:
            try:
                line = input("> ").strip()
                if not line:
                    break
                folder_ids.append(line)
            except (KeyboardInterrupt, EOFError):
                print("\nCancelled.")
                return 1

    if not folder_ids:
        print("No folder IDs provided. Exiting.")
        return 0

    print(f"\nYou are about to trash {len(folder_ids)} folder(s):")
    for fid in folder_ids:
        print(f"  - {fid}")

    confirm = input("\nType 'YES' to confirm: ").strip().upper()
    if confirm != 'YES':
        print("Cancelled.")
        return 0

    drive_service, _ = get_oauth_services()
    sa_service = get_service()
    trash_folders(drive_service, sa_service, folder_ids)
    return 0


if __name__ == '__main__':
    sys.exit(main())
