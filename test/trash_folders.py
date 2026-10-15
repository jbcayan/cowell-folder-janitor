import sys
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service-credentials.json'

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    return build('drive', 'v3', credentials=creds)

def trash_folders(service, folder_ids):
    """Move folders to trash by their IDs."""
    if not folder_ids:
        print("No folder IDs provided.")
        return

    print(f"Attempting to trash {len(folder_ids)} folder(s)...\n")
    
    success_count = 0
    for folder_id in folder_ids:
        try:
            # Get folder name first for confirmation
            file = service.files().get(fileId=folder_id, fields='name').execute()
            folder_name = file.get('name')
            
            # Move to trash
            service.files().update(
                fileId=folder_id,
                body={'trashed': True}
            ).execute()
            
            print(f"  ✅ Trashed: {folder_name} ({folder_id})")
            success_count += 1
            
        except HttpError as e:
            if e.resp.status == 404:
                print(f"  ❌ Not found: {folder_id}")
            elif e.resp.status == 403:
                print(f"  ❌ Permission denied: {folder_id} (service account needs to be the folder OWNER to trash; Editor role is insufficient)")
            else:
                print(f"  ❌ Failed to trash {folder_id}: {e}")
        except Exception as e:
            print(f"  ❌ Error with {folder_id}: {e}")

    print(f"\n🎉 Done! Successfully trashed {success_count}/{len(folder_ids)} folders.")

def main():
    folder_ids = []
    
    # Option 1: Pass IDs as command-line arguments
    # python3 test/trash_folders.py 16WSIzD9SU1E37BIr4XajDYj1okpn_gT- 1sLuTtRUYJinDy7tf_snA1rrbEP6RT7Hj
    if len(sys.argv) > 1:
        folder_ids = sys.argv[1:]
    
    # Option 2: Interactive input if no args
    else:
        print("Enter folder IDs to trash (one per line, empty line to finish):")
        print("Example: 16WSIzD9SU1E37BIr4XajDYj1okpn_gT-")
        while True:
            try:
                line = input("> ").strip()
                if not line:
                    break
                folder_ids.append(line)
            except KeyboardInterrupt:
                print("\nCancelled.")
                return
            except EOFError:
                break
    
    if not folder_ids:
        print("No folder IDs provided. Exiting.")
        return

    # Confirm before trashing
    print(f"\nYou are about to trash {len(folder_ids)} folder(s):")
    for fid in folder_ids:
        print(f"  - {fid}")
    
    confirm = input("\nType 'YES' to confirm: ").strip().upper()
    if confirm != 'YES':
        print("Cancelled.")
        return

    service = get_drive_service()
    trash_folders(service, folder_ids)

if __name__ == '__main__':
    main()