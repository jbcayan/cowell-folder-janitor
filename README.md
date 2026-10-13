# Cowell Auto File Deletion

A serverless AWS Lambda function that automatically cleans up expired export folders from Google Drive.

## Overview

This utility runs on a schedule (every 5 minutes via EventBridge) and moves folders older than a configurable threshold (default: 24 hours) to the Google Drive Trash. This prevents accumulation of OCR export folders in the shared "Co Test" directory.

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌────────────────┐     ┌──────────────┐
│  EventBridge│────▶│    Lambda    │────▶│  Google Drive  │────▶│  CloudWatch  │
│  (5 min)    │     │  (Janitor)   │     │  API (Trash)   │     │  (Logs)      │
└─────────────┘     └──────────────┘     └────────────────┘     └──────────────┘
                          │
                          ▼
                 ┌─────────────────┐
                 │  Service Account │
                 │  (test-co@...)   │
                 └─────────────────┘
```

## Features

- **Automatic cleanup**: Runs every 5 minutes via EventBridge Scheduler
- **Configurable retention**: Set `EXPIRATION_HOURS` environment variable (default: 24)
- **Safe deletion**: Uses Google Drive "trash" instead of permanent delete
- **Owner-agnostic**: Works even when service account doesn't own the folders
- **Monitoring**: Logs all activity to CloudWatch

## Project Structure

```
Cowel-auto-file-deletion/
├── lambda_handler.py       # Main Lambda function code
├── requirements.txt        # Python dependencies
├── DEPLOYMENT_GUIDE.md    # AWS deployment instructions
├── .gitignore             # Git ignore rules
├── test/                   # Local testing scripts
│   ├── test_local_cleanup.py
│   ├── list_parent_folder.py
│   ├── create_folder.py
│   └── ... (other test utilities)
└── README.md              # This file
```

## Prerequisites

- AWS Account with Lambda, EventBridge, and CloudWatch permissions
- Google Cloud Project with Drive API enabled
- Service Account with Editor access to the target Google Drive folder

## Quick Start

### 1. Local Development

```bash
# Install dependencies
pip3 install -r requirements.txt

# Run local test (uses 1-hour expiration for testing)
python3 test/test_local_cleanup.py
```

### 2. AWS Deployment

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed steps.

Quick summary:
1. Build deployment package:
   ```bash
   pip3 install -t lambda_package/ -r requirements.txt
   cp lambda_handler.py lambda_package/
   zip -r deployment_package.zip lambda_package/
   ```
2. Create Lambda function (Python 3.12, arm64)
3. Upload `deployment_package.zip`
4. Set environment variables:
   - `GOOGLE_SERVICE_ACCOUNT_JSON`: Full service account JSON
   - `PARENT_FOLDER_ID`: Google Drive folder ID (default: Co Test)
   - `EXPIRATION_HOURS`: Retention period (default: 24)
5. Add EventBridge trigger: `rate(5 minutes)`
6. Set timeout to 60 seconds, memory to 256 MB

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Yes | - | Full service account JSON as string |
| `PARENT_FOLDER_ID` | No | `1IGVqByX0Nr_skGrV2NqxzxwTqv6Sc4uW` | Google Drive parent folder ID |
| `EXPIRATION_HOURS` | No | `24` | Hours before folder is trashed |

## How It Works

1. **Trigger**: EventBridge invokes Lambda every 5 minutes
2. **Authenticate**: Lambda uses service account credentials to access Google Drive API
3. **Scan**: Lists all folders in the parent directory
4. **Filter**: Identifies folders where `createdTime < (now - EXPIRATION_HOURS)`
5. **Trash**: Moves expired folders to Trash using `files().update(trashed=True)`
6. **Log**: Reports results to CloudWatch

## Why Trash Instead of Delete?

Google Drive permissions:
- **Owner** can permanently delete
- **Editor** can only move to Trash

Since the service account may not own folders created by users, we use `trashed=true` which works with Editor permissions. Trashed items are auto-purged by Google after 30 days.

## Testing

### Local Test
```bash
python3 test/test_local_cleanup.py
```
Shows all folders with age status, asks for confirmation before trashing.

### Manual Lambda Test
In AWS Console → Lambda → Test tab → Create test event → Test

## Monitoring

Check CloudWatch Logs for:
- Folders found and their ages
- Which folders were trashed
- Any errors (permission issues, API limits)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| `403 insufficientFilePermissions` | Use trash (already implemented), or ensure service account owns folders |
| `404 File not found` | Verify `PARENT_FOLDER_ID` and service account access |
| `No module named '_cffi_backend'` | Rebuild deployment package with `google-auth<2.30` |
| Timeout | Increase Lambda timeout to 60s, memory to 256MB |

## Security Notes

- Store service account JSON in AWS Secrets Manager for production
- Never commit credentials to git (see .gitignore)
- Use least-privilege IAM roles for Lambda
- Rotate service account keys periodically

## License

Internal use - Cowell Project