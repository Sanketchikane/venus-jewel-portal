# backends/utils_backend.py
import os, io, tempfile, subprocess, time, hmac, hashlib
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import gspread
import config
from googleapiclient.http import MediaIoBaseUpload

# initialize creds & clients once
_creds = service_account.Credentials.from_service_account_file(config.CREDENTIALS_PATH, scopes=config.SCOPES)
_gspread_client = gspread.authorize(_creds)
_drive_service = build("drive", "v3", credentials=_creds)

# Google Sheet access helpers
def get_registration_sheet():
    return _gspread_client.open_by_key(config.SHEET_ID).worksheet("Registration")

def get_credentials_sheet():
    return _gspread_client.open_by_key(config.SHEET_ID).worksheet("Credentials")

# Google Drive folder and file helpers
def list_packet_folders(order="modifiedTime desc"):
    q = f"'{config.DRIVE_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    res = _drive_service.files().list(q=q, fields="files(id,name,modifiedTime)", orderBy=order, includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
    return res.get("files", [])

def list_files_in_folder(folder_id, order="modifiedTime desc"):
    q = f"'{folder_id}' in parents and trashed=false"
    try:
        res = _drive_service.files().list(q=q, fields="files(id,name,mimeType,size,modifiedTime)", orderBy=order, includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
        return res.get("files", [])
    except Exception as e:
        print("Error fetching files:", e)
        return []  # Gracefully handle errors and return empty list

def get_or_create_folder(name, parent_id=config.DRIVE_FOLDER_ID):
    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    res = _drive_service.files().list(q=q, fields="files(id,name)", includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    folder = _drive_service.files().create(body=meta, fields="id", supportsAllDrives=True).execute()
    return folder.get("id")

def upload_media_to_drive(name, parent_id, media):
    body = {"name": name, "parents": [parent_id]}
    _drive_service.files().create(body=body, media_body=media, fields="id", supportsAllDrives=True).execute()

# File helpers
def download_file_to_bytes(file_id):
    meta = _drive_service.files().get(fileId=file_id, fields="id,name,mimeType", supportsAllDrives=True).execute()
    fh = io.BytesIO()
    req = _drive_service.files().get_media(fileId=file_id, supportsAllDrives=True)
    downloader = MediaIoBaseDownload(fh, req)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return meta["name"], meta.get("mimeType", "application/octet-stream"), fh
    # -----------------------------------------
# USER LOOKUP (REQUIRED FOR LOGIN)
# -----------------------------------------
def get_user_record(username):
    """
    Reads the Credentials sheet and returns the user record
    matching the given username.
    """
    try:
        ws = get_credentials_sheet()

        # Column C contains the username list
        usernames = ws.col_values(3)[1:]  # ignore header row

        for i, u in enumerate(usernames, start=2):
            if u == username:
                row = ws.row_values(i)

                def col(n):
                    return row[n] if len(row) > n else ""

                return {
                    "row_number": i,
                    "Timestamp": col(0),
                    "Full Name": col(1),
                    "Username": col(2),
                    "Password": col(3),
                    "Contact Number": col(4),
                    "Organization": col(5),
                }

        return None
    except Exception as e:
        print("ERROR get_user_record:", e)
        return None

