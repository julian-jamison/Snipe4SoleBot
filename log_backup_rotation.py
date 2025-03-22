import os
import json
from datetime import datetime, timedelta
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

LOG_FILE = "trade_log.json"
BACKUP_FOLDER = "backups"
RETENTION_DAYS = 3


def authenticate_drive():
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("mycreds.txt")

    if gauth.credentials is None:
        gauth.LocalWebserverAuth()
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()

    gauth.SaveCredentialsFile("mycreds.txt")
    return GoogleDrive(gauth)


def upload_log_to_drive():
    if not os.path.exists(LOG_FILE):
        print("⚠️ No log file found to upload.")
        return

    drive = authenticate_drive()

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    upload_file_name = f"log_backup_{timestamp}.json"

    file = drive.CreateFile({'title': upload_file_name})
    file.SetContentFile(LOG_FILE)
    file.Upload()

    print(f"✅ Uploaded log to Google Drive: {upload_file_name}")


def rotate_old_backups():
    if not os.path.exists(BACKUP_FOLDER):
        os.makedirs(BACKUP_FOLDER)
        return

    now = datetime.now()
    for file in os.listdir(BACKUP_FOLDER):
        filepath = os.path.join(BACKUP_FOLDER, file)
        if os.path.isfile(filepath):
            created_time = datetime.fromtimestamp(os.path.getctime(filepath))
            if (now - created_time).days > RETENTION_DAYS:
                os.remove(filepath)
                print(f"🗑 Deleted old backup: {file}")


def clean_old_models():
    for file in os.listdir('.'):
        if file.startswith("lstm_model") and file.endswith(".h5"):
            created_time = datetime.fromtimestamp(os.path.getctime(file))
            if (datetime.now() - created_time).days > RETENTION_DAYS:
                os.remove(file)
                print(f"🧹 Deleted old model: {file}")


if __name__ == "__main__":
    upload_log_to_drive()
    rotate_old_backups()
    clean_old_models()
