import os
import json
from datetime import datetime, timedelta, timezone
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# --- Configuration ---
# These can be moved to environment variables for flexibility
PARENT_FOLDER_ID = os.environ.get('PARENT_FOLDER_ID', '1IGVqByX0Nr_skGrV2NqxzxwTqv6Sc4uW')
EXPIRATION_HOURS = int(os.environ.get('EXPIRATION_HOURS', '24'))

def get_drive_service():
    """Initializes the Google Drive API service using credentials from environment variables."""
    try:
        # Expecting the full JSON content of the service-credentials.json file in this variable
        service_account_info = json.loads(os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON', '{}'))
        if not service_account_info:
            raise ValueError("Environment variable GOOGLE_SERVICE_ACCOUNT_JSON is empty or missing.")
            
        scopes = ['https://www.googleapis.com/auth/drive']
        creds = service_account.Credentials.from_service_account_info(service_account_info, scopes=scopes)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"Authentication Error: {e}")
        raise e

def lambda_handler(event, context):
    """
    AWS Lambda handler to delete folders in a specific Google Drive parent folder 
    that are older than a specified number of hours.
    """
    logger.info("Starting Google Drive Janitor cleanup...")
    
    try:
        service = get_drive_service()
        
        logger.info(f"EXPIRATION_HOURS = {EXPIRATION_HOURS}")
        logger.info(f"PARENT_FOLDER_ID = {PARENT_FOLDER_ID}")
        
        # Debug: List ALL folders in the parent first
        all_query = (f"'{PARENT_FOLDER_ID}' in parents and "
                     f"mimeType = 'application/vnd.google-apps.folder' and "
                     f"trashed = false")
        all_results = service.files().list(
            q=all_query,
            fields="files(id, name, createdTime)",
            pageSize=100
        ).execute()
        all_items = all_results.get('files', [])
        logger.info(f"Total folders in parent: {len(all_items)}")
        for f in all_items:
            logger.info(f"  Found: {f['name']} | Created: {f['createdTime']} | ID: {f['id']}")
        
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=EXPIRATION_HOURS)
        cutoff_time_str = cutoff_time.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        logger.info(f"Current UTC: {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}")
        logger.info(f"Cutoff time: {cutoff_time_str}")

        query = (f"'{PARENT_FOLDER_ID}' in parents and "
                 f"mimeType = 'application/vnd.google-apps.folder' and "
                 f"trashed = false and "
                 f"createdTime < '{cutoff_time_str}'")
        
        results = service.files().list(
            q=query, 
            fields="files(id, name, createdTime)", 
            pageSize=100
        ).execute()
        
        items = results.get('files', [])

        if not items:
            logger.info("No expired folders found to delete.")
            return {
                'statusCode': 200,
                'body': json.dumps('No expired folders found.')
            }

        logger.info(f"Found {len(items)} expired folders. Starting trashing...")
        
        trashed_count = 0
        for item in items:
            try:
                folder_id = item['id']
                folder_name = item['name']
                created_time = item['createdTime']
                
                # Move to trash (trashed=true) instead of permanent delete
                # This works even if the service account is not the owner
                service.files().update(
                    fileId=folder_id,
                    body={'trashed': True}
                ).execute()
                logger.info(f"Successfully trashed: {folder_name} (ID: {folder_id}, Created: {created_time})")
                trashed_count += 1
            except HttpError as e:
                logger.error(f"Failed to trash {item['name']} ({item['id']}): {e}")
            except Exception as e:
                logger.error(f"Unexpected error trashing {item['name']}: {e}")

        logger.info(f"Cleanup complete. Total folders trashed: {trashed_count}")
        
        return {
            'statusCode': 200,
            'body': json.dumps(f"Successfully trashed {trashed_count} folders.")
        }

    except Exception as e:
        logger.error(f"Critical Error in lambda_handler: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Internal Server Error: {str(e)}")
        }
