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

def check_folder(service, folder_id):
    try:
        # Get full folder metadata
        file = service.files().get(
            fileId=folder_id,
            fields='id,name,mimeType,createdTime,modifiedTime,owners,permissions,capabilities,trashed,parents'
        ).execute()
        
        print(f"📁 Folder Details for: {folder_id}")
        print(f"   Name: {file.get('name')}")
        print(f"   MIME: {file.get('mimeType')}")
        print(f"   Created: {file.get('createdTime')}")
        print(f"   Modified: {file.get('modifiedTime')}")
        print(f"   Trashed: {file.get('trashed')}")
        print(f"   Parents: {file.get('parents', [])}")
        
        # Check ownership
        owners = file.get('owners', [])
        print(f"\n👤 Owners:")
        for owner in owners:
            print(f"   - {owner.get('displayName', 'N/A')} ({owner.get('emailAddress', 'N/A')})")
            print(f"     Me: {owner.get('me', False)}")
        
        # Check permissions
        permissions = file.get('permissions', [])
        print(f"\n🔐 Permissions:")
        for perm in permissions:
            print(f"   - Type: {perm.get('type')}, Role: {perm.get('role')}, Email: {perm.get('emailAddress', 'N/A')}, Name: {perm.get('displayName', 'N/A')}")
        
        # Check capabilities
        caps = file.get('capabilities', {})
        print(f"\n⚡ Capabilities:")
        print(f"   Can trash: {caps.get('canTrash')}")
        print(f"   Can delete: {caps.get('canDelete')}")
        print(f"   Can move: {caps.get('canMoveItemIntoNewDrive')}")
        
        # Check if service account is the owner
        sa_email = "cowell-ocr-drive-exporter@sports-academy-alamin-393006.iam.gserviceaccount.com"
        is_owner = any(o.get('emailAddress') == sa_email for o in owners)
        is_editor = any(p.get('emailAddress') == sa_email and p.get('role') in ['writer', 'organizer', 'fileOrganizer'] for p in permissions)
        
        print(f"\n📋 Service Account ({sa_email}):")
        print(f"   Is Owner: {is_owner}")
        print(f"   Is Editor: {is_editor}")
        
        if not is_owner and not is_editor:
            print(f"\n⚠️  ISSUE: Service account lacks Editor permission on this folder!")
            print(f"   Solution: Share this folder with the service account as Editor in Google Drive UI")
        
    except HttpError as e:
        if e.resp.status == 404:
            print(f"❌ Folder not found: {folder_id}")
        elif e.resp.status == 403:
            print(f"❌ Permission denied - can't even read folder metadata")
        else:
            print(f"❌ Error: {e}")
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 test/check_folder_perms.py <folder_id>")
        print("Example: python3 test/check_folder_perms.py 1qpT24dLi2hbY5wrV3GRJ9rGKfwzgz43L")
        return
    
    folder_id = sys.argv[1]
    service = get_drive_service()
    check_folder(service, folder_id)

if __name__ == '__main__':
    main()