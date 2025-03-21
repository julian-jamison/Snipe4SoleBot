import os
import json
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

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

def restore_from_gdrive():
    """Downloads the latest encrypted config backup from Google Drive."""
    drive = authenticate_gdrive()
    file_list = drive.ListFile({'q': "title contains 'backup_'"}).GetList()
    
    if not file_list:
        print("⚠️ No backup files found in Google Drive.")
        return "No backup found."
    
    # Sort by most recent backup
    file_list.sort(key=lambda x: x['title'], reverse=True)
    latest_backup = file_list[0]
    latest_backup.GetContentFile("config.enc")
    print("✅ Backup restored successfully.")
    return "Backup restored from Google Drive."

if __name__ == "__main__":
    restore_from_gdrive()
