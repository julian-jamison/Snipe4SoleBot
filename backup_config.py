import os
import json
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from datetime import datetime

CONFIG_FILE = "config.enc"
BACKUP_FOLDER = "Snipe4SoleBot_Backups"  # Google Drive folder name
BACKUP_FILENAME = f"backup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.enc"

def authenticate_gdrive():
    """Authenticates Google Drive API using OAuth 2.0."""
    gauth = GoogleAuth()
    gauth.LoadCredentialsFile("mycreds.txt")
    
    if gauth.credentials is None:
        gauth.LocalWebserverAuth()  # Open browser for authentication
    elif gauth.access_token_expired:
        gauth.Refresh()
    else:
        gauth.Authorize()
    
    gauth.SaveCredentialsFile("mycreds.txt")  # Save for future logins
    return GoogleDrive(gauth)

def get_backup_folder_id(drive):
    """Gets the Google Drive folder ID for storing backups."""
    file_list = drive.ListFile({'q': f"title = '{BACKUP_FOLDER}' and mimeType = 'application/vnd.google-apps.folder' and trashed=false"}).GetList()
    
    if file_list:
        return file_list[0]['id']  # Folder already exists
    
    # Create new folder if not found
    folder = drive.CreateFile({'title': BACKUP_FOLDER, 'mimeType': 'application/vnd.google-apps.folder'})
    folder.Upload()
    return folder['id']

def backup_to_gdrive():
    """Uploads encrypted config file to Google Drive inside a designated folder."""
    drive = authenticate_gdrive()
    folder_id = get_backup_folder_id(drive)
    
    file = drive.CreateFile({'title': BACKUP_FILENAME, 'parents': [{'id': folder_id}]})
    file.SetContentFile(CONFIG_FILE)
    file.Upload()
    print(f"✅ Backup uploaded to Google Drive in folder '{BACKUP_FOLDER}': {BACKUP_FILENAME}")

if __name__ == "__main__":
    if os.path.exists(CONFIG_FILE):
        backup_to_gdrive()
    else:
        print("⚠️ No config.enc file found. Backup aborted.")
