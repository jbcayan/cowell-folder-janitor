import os
import json
from datetime import datetime, timedelta, timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- Configuration ---
SERVICE_ACCOUNT_FILE = 'service-credentials.json'
PARENT_FOLDER_ID = '1IGVqByX0Nr_skGrV2NqxzxwTqv6Sc4uW'
EXPIRATION_HOURS = 1  # Set to 1 hour for testing

def get_drive_service():
    scopes = ['https://www.googleapis.com/auth/drive']
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=scopes)
    return build('drive', 'v3', credentials=creds)

def main():
    print("=" * 60)
    print("  Google Drive Janitor - LOCAL TEST (1 Hour Expiration)")
    print("=" * 60)

    service = get_drive_service()

    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=EXPIRATION_HOURS)
    cutoff_time_str = cutoff_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    print(f"\nCurrent UTC Time : {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Cutoff Time (UTC): {cutoff_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Folders created before the cutoff will be DELETED.\n")

    # Step 1: List ALL folders first
    query_all = (f"'{PARENT_FOLDER_ID}' in parents and "
                 f"mimeType = 'application/vnd.google-apps.folder' and "
                 f"trashed = false")

    all_results = service.files().list(
        q=query_all,
        fields="files(id, name, createdTime)",
        pageSize=100
    ).execute()

    all_items = all_results.get('files', [])

    if not all_items:
        print("No folders found in the parent directory.")
        return

    print(f"📂 All folders in Co Test ({len(all_items)} total):")
    print("-" * 60)
    for item in all_items:
        created = datetime.strptime(item['createdTime'], '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
        age = datetime.now(timezone.utc) - created
        hours = age.total_seconds() / 3600
        status = "🔴 EXPIRED" if created < cutoff_time else "🟢 SAFE"
        print(f"  {status}  {item['name']}")
        print(f"          Created: {item['createdTime']}  |  Age: {hours:.1f} hours")

    # Step 2: Find expired folders
    query_expired = (f"'{PARENT_FOLDER_ID}' in parents and "
                     f"mimeType = 'application/vnd.google-apps.folder' and "
                     f"trashed = false and "
                     f"createdTime < '{cutoff_time_str}'")

    expired_results = service.files().list(
        q=query_expired,
        fields="files(id, name, createdTime)",
        pageSize=100
    ).execute()

    expired_items = expired_results.get('files', [])

    if not expired_items:
        print("\n✅ No expired folders found. Nothing to delete.")
        return

    print(f"\n⚠️  Found {len(expired_items)} expired folder(s) to delete:")
    for item in expired_items:
        print(f"  - {item['name']} (Created: {item['createdTime']})")

    # Step 3: Ask for confirmation before deleting
    confirm = input(f"\n🗑️  Type 'DELETE' to permanently delete {len(expired_items)} folder(s): ")

    if confirm.strip() != 'DELETE':
        print("❌ Aborted. No folders were deleted.")
        return

    # Step 4: Delete expired folders
    deleted_count = 0
    for item in expired_items:
        try:
            service.files().delete(fileId=item['id']).execute()
            print(f"  ✅ Deleted: {item['name']} ({item['id']})")
            deleted_count += 1
        except HttpError as e:
            print(f"  ❌ Failed to delete {item['name']}: {e}")

    print(f"\n🎉 Cleanup complete! Deleted {deleted_count} folder(s).")

if __name__ == '__main__':
    main()
