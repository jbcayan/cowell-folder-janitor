"""
Delete one or more Drive folders by ID using OAuth2 user credentials.

Why OAuth2 and not the service account?
  Only the file owner can permanently delete items in a regular (non-Shared)
  Drive. The OAuth2 token acts as the real user who owns the folders, so
  deletion succeeds where the service account would get a 403.

Usage:
    # Pass IDs directly as arguments
    python test/delete_folder.py 1Zi-n5xaRuJbn2GcBnTl96ukUF2I-4vWc 17J63okeZ21eNIMfY3JxlBrUpd4W3Iq7P

    # Interactive mode (no arguments)
    python test/delete_folder.py
"""

import sys
from googleapiclient.errors import HttpError
from drive_config import get_oauth_services


def delete_folders(drive_service, folder_ids):
    print(f"\nAttempting to permanently delete {len(folder_ids)} folder(s)...\n")

    success = 0
    for fid in folder_ids:
        try:
            file = drive_service.files().get(fileId=fid, fields='name,mimeType').execute()
            name = file.get('name')
            mime = file.get('mimeType', '')

            if mime != 'application/vnd.google-apps.folder':
                print(f"  ⚠️  Skipped: {name} ({fid}) — not a folder (mimeType: {mime})")
                continue

            drive_service.files().delete(fileId=fid).execute()
            print(f"  ✅ Deleted: {name} ({fid})")
            success += 1

        except HttpError as e:
            if e.resp.status == 404:
                print(f"  ❌ Not found: {fid}")
            elif e.resp.status == 403:
                print(f"  ❌ Permission denied: {fid}")
            else:
                print(f"  ❌ Error {e.resp.status} for {fid}: {e}")
        except Exception as e:
            print(f"  ❌ Unexpected error for {fid}: {e}")

    print(f"\n🎉 Done! Deleted {success}/{len(folder_ids)} folder(s).")


def main():
    folder_ids = sys.argv[1:]

    if not folder_ids:
        print("Enter folder IDs to delete (one per line, empty line to finish):")
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

    print(f"\nYou are about to PERMANENTLY delete {len(folder_ids)} folder(s):")
    for fid in folder_ids:
        print(f"  - {fid}")

    confirm = input("\nType 'YES' to confirm: ").strip().upper()
    if confirm != 'YES':
        print("Cancelled.")
        return 0

    drive_service, _ = get_oauth_services()
    delete_folders(drive_service, folder_ids)
    return 0


if __name__ == '__main__':
    sys.exit(main())
