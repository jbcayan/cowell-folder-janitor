# 🚀 Google Drive Auto-Deletion Deployment Guide

This guide explains how to deploy the "Janitor" Lambda function to automatically **move to Trash** folders older than a configurable threshold (default: 24 hours) from your Google Drive parent folder.

## Architecture Overview

```
EventBridge (5 min) → Lambda (Python 3.12, arm64) → Google Drive API (trashed=true) → CloudWatch Logs
```

## 1. Google Drive Setup

Before deploying, ensure your service account has the correct access:
*   **Service Account Email:** `cowell-ocr-drive-exporter@sports-academy-alamin-393006.iam.gserviceaccount.com` (or your service account)
*   **Permission:** The service account must have **Editor** access to the parent folder.

**Why Editor (not Owner)?** The function uses `trashed=true` which works with Editor permissions. This allows the service account to trash folders it doesn't own (created by users). Trashed items are auto-purged by Google after 30 days.

---

## 2. AWS Lambda Configuration

### A. Create the Lambda Function

1.  Log in to the **AWS Management Console**.
2.  Navigate to **Lambda** → **Create function**.
3.  Choose **Author from scratch**.
4.  **Function name:** `cowell-folder-janitor`
5.  **Runtime:** Select **Python 3.12**.
6.  **Architecture:** Select **arm64** (cheaper, faster; matches our build).
6.  Click **Create function**.

### B. Environment Variables

Go to **Configuration** tab → **Environment variables** → **Edit** → **Add environment variable**:

| Key | Value | Description |
| :--- | :--- | :--- |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full JSON from `service-credentials.json` | Copy **entire content** as a single line string. |
| `PARENT_FOLDER_ID` | `1S0EX9tnYggKJ5_-fDt4IXVLnNJyam3TJ` | The ID of the parent folder ("JBC-COWELL"). |
| `EXPIRATION_MINUTES` | `60` | **Primary:** Minutes before a folder is trashed (e.g., `60` = 1 hour, `5` = 5 min). |
| `EXPIRATION_HOURS` | `1` | **Fallback (legacy):** Hours before a folder is trashed. Used only if `EXPIRATION_MINUTES` not set. |

**Priority:** `EXPIRATION_MINUTES` → `EXPIRATION_HOURS` → default (24 hours)

### C. Build & Upload Deployment Package (No Layer Needed)

We build a self-contained zip with all dependencies. **No Lambda Layer required.**

**On your local machine (requires Docker):**

```bash
# 1. Navigate to project root
cd Cowel-auto-file-deletion

# 2. Build package using Docker (gets Linux/ARM binaries)
docker run --rm --entrypoint "" -v "$(pwd):/var/task" public.ecr.aws/lambda/python:3.12 \
  bash -c "pip install --no-cache-dir \
    'google-auth<2.30' \
    google-api-python-client \
    google-auth-httplib2 \
    rsa \
    pyasn1 \
    pyasn1-modules \
    -t /var/task/ && \
  cp lambda_handler.py /var/task/ && \
  chmod -R 755 /var/task"

# 3. Copy the built handler back and zip from host (not inside container!)
cd /Users/fazlulayankoushik/Documents/Projects/JB\ CONNECT/COWELL\ PROJECT
cp Cowel-auto-file-deletion/lambda_handler.py lambda_package/lambda_handler.py
cd lambda_package && zip -r -q ../deployment_package.zip .

# 4. Upload deployment_package.zip to Lambda
#    Code tab → Upload from → .zip file → Select deployment_package.zip
```

**Note:** The `zip` command runs on your **host machine** (Mac/Linux), not inside the Docker container. The Docker step only installs the Linux/ARM binaries into `lambda_package/`.

**Alternative (if you have a Linux/ARM machine natively):**
```bash
pip3 install -t lambda_package/ -r requirements.txt
cp lambda_handler.py lambda_package/
cd lambda_package && zip -r ../deployment_package.zip .
```

### D. Configure Function Settings

1.  **Configuration** → **General configuration** → **Edit**
2.  **Timeout:** `1 min 0 sec` (3 seconds is too short for Drive API calls)
3.  **Memory:** `256 MB` (also gives more CPU)
4.  **Save**

---

## 3. EventBridge Scheduler Setup (The Trigger)

To make the Lambda run every 5 minutes:

1.  Navigate to **Amazon EventBridge** → **Schedules** → **Create schedule**.
2.  **Name:** `every-5-mins-drive-cleanup`
3.  **Schedule pattern:** Recurring schedule → Rate-based schedule → **Every 5 minutes**.
4.  **Target:** **AWS Lambda** → Select `cowell-folder-janitor`.
5.  **Permissions:** Allow EventBridge to invoke your Lambda function (creates resource-based policy automatically).
6.  **Create schedule**.

**Other schedule options:**
| Frequency | Expression |
|-----------|------------|
| Every 5 minutes | `rate(5 minutes)` |
| Every 15 minutes | `rate(15 minutes)` |
| Every 1 hour | `rate(1 hour)` |
| Every 6 hours | `rate(6 hours)` |
| Daily at midnight UTC | `cron(0 0 * * ? *)` |

---

## 4. Testing Strategy

### A. Local Testing (Recommended First)

```bash
# Uses 1-hour expiration for fast feedback
python3 test/test_local_cleanup.py
```
- Lists all folders with age and status (SAFE/EXPIRED)
- Asks for `YES` confirmation before trashing
- Uses same logic as Lambda (supports minutes)

### B. Lambda Test Mode (Quick Test)

1.  In Lambda console, set `EXPIRATION_MINUTES` = `5` (trashes folders older than 5 min).
2.  Create a test event (empty JSON `{}`).
3.  Click **Test**.
4.  Check Google Drive → **Trash** for moved folders.
5.  **Reset** `EXPIRATION_MINUTES` to `60` (or your production value).

### C. Verify Logs

Check **Monitor** → **View CloudWatch logs** for:
```
Starting Google Drive Janitor cleanup...
EXPIRATION_DELTA = 0:05:00
PARENT_FOLDER_ID = 1S0EX9tnYggKJ5_-fDt4IXVLnNJyam3TJ
Total folders in parent: 5
  Found: Testing2200 | Created: 2026-10-15T10:24:50.000Z | ID: 10UNuWrPGwbDKrPnzlugnmQ-QEUN7T9pi
  Found: Testing2200 | Created: 2026-10-15T10:18:11.000Z | ID: 1sLuTtRUYJinDy7tf_snA1rrbEP6RT7Hj
  ...
Current UTC: 2026-10-15T10:35:00Z
Cutoff time: 2026-10-15T10:30:00Z
Found 3 expired folders. Starting trashing...
Successfully trashed: Testing2200 (ID: 10UNuWrPGwbDKrPnzlugnmQ-QEUN7T9pi)
Successfully trashed: Testing2200 (ID: 1sLuTtRUYJinDy7tf_snA1rrbEP6RT7Hj)
Cleanup complete. Total folders trashed: 2
```

---

## 5. Troubleshooting

| Issue | Solution |
|-------|----------|
| `403 insufficientFilePermissions` | Use `trashed=true` (already implemented). Ensure service account has **Editor** on parent folder. |
| `404 File not found` | Verify `PARENT_FOLDER_ID` is correct and service account has access. |
| `No module named '_cffi_backend'` | Rebuild package with `google-auth<2.30` (uses pure Python `rsa`). |
| `Request timed out` | Increase Lambda timeout to 60s, memory to 256 MB. |
| `Unable to import module` | Ensure architecture is **arm64** and zip contains `lambda_handler.py` at root. |
| `cp: same file` error | Ignore — it means the handler was already copied. |

---

## 6. Production Hardening

1.  **Secrets:** Store `GOOGLE_SERVICE_ACCOUNT_JSON` in **AWS Secrets Manager**, reference via Lambda environment variable.
2.  **IAM:** Use least-privilege role for Lambda (only `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`).
3.  **Monitoring:** Create CloudWatch Alarm on `Errors` metric > 0.
4.  **Rotation:** Rotate service account keys periodically (Google Cloud Console → IAM → Service Accounts → Keys).

---

## 7. Quick Reference

| Setting | Value |
|---------|-------|
| Function Name | `cowell-folder-janitor` |
| Runtime | Python 3.12 (arm64) |
| Handler | `lambda_handler.lambda_handler` |
| Timeout | 60 seconds |
| Memory | 256 MB |
| Trigger | EventBridge `rate(5 minutes)` |
| Retention | Configurable via `EXPIRATION_MINUTES` (default 24h) |
| Action | Move to Trash (`trashed=true`) |

---

## 8. Project Structure

```
Cowel-auto-file-deletion/
├── lambda_handler.py          # Main Lambda function (supports minutes + hours)
├── requirements.txt           # Python dependencies
├── DEPLOYMENT_GUIDE.md        # This file
├── .gitignore                 # Git ignore rules
├── README.md                  # Project overview
├── deployment_package.zip     # Built deployment artifact (~21 MB)
├── lambda_package/            # Docker build output (dependencies + handler)
└── test/                      # Local testing utilities
    ├── test_local_cleanup.py  # Interactive cleanup test (minutes)
    ├── list_parent_folder.py  # List all folders with creation times
    ├── create_testing2200.py  # Create test folders
    ├── trash_folders.py       # Trash folders by ID (interactive or args)
    └── check_*.py             # Diagnostic scripts
```