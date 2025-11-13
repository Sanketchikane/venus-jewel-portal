# backends/utils_backend.py
import os
import io
import tempfile
import subprocess
import time
import hmac
import hashlib
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaIoBaseUpload
import gspread
import config

# initialize creds & clients once (fail early if creds missing)
_creds = service_account.Credentials.from_service_account_file(
    config.CREDENTIALS_PATH, scopes=config.SCOPES
)
_gspread_client = gspread.authorize(_creds)
_drive_service = build("drive", "v3", credentials=_creds)

# ---------------------------
# Google Sheet helpers
# ---------------------------
def get_registration_sheet(tab_name="Registration"):
    """
    Return a worksheet object for registration-related tabs.
    If tab doesn't exist, try to create it.
    """
    sh = _gspread_client.open_by_key(config.SHEET_ID)
    try:
        return sh.worksheet(tab_name)
    except Exception:
        # Create a worksheet with a default header if it doesn't exist
        try:
            ws = sh.add_worksheet(title=tab_name, rows="1000", cols="20")
            # add minimal header for registration-type sheet
            if tab_name == "Registration":
                ws.append_row(["Timestamp", "Full Name", "Email Address", "Contact Number", "Organization", "Status"])
            elif tab_name == "Forgot_Password_Requests":
                ws.append_row(["Full Name", "Username", "Email", "Organization", "Contact Number", "Status", "Timestamp"])
            else:
                ws.append_row(["A","B","C"])
            return ws
        except Exception as e:
            print("ERROR creating worksheet", tab_name, e)
            raise

def get_credentials_sheet():
    """
    Return the Credentials worksheet (expected tab name 'Credentials').
    """
    sh = _gspread_client.open_by_key(config.SHEET_ID)
    try:
        return sh.worksheet("Credentials")
    except Exception:
        # create a credentials tab with standard header if missing
        try:
            ws = sh.add_worksheet(title="Credentials", rows="1000", cols="20")
            ws.append_row(["Timestamp", "Full Name", "Username", "Password", "Contact Number", "Organization", "Email"])
            return ws
        except Exception as e:
            print("ERROR creating Credentials worksheet", e)
            raise

# convenience to return all credential rows as dicts
def read_credentials_all_rows():
    ws = get_credentials_sheet()
    records = ws.get_all_values()
    if not records or len(records) < 2:
        return []
    headers = records[0]
    rows = []
    for row in records[1:]:
        while len(row) < len(headers):
            row.append("")
        rows.append(dict(zip(headers, row)))
    return rows

# ---------------------------
# Google Drive helpers
# ---------------------------
def list_packet_folders(order="modifiedTime desc"):
    """List folders under the configured DRIVE_FOLDER_ID"""
    q = f"'{config.DRIVE_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    try:
        res = _drive_service.files().list(
            q=q,
            fields="files(id,name,modifiedTime)",
            orderBy=order,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()
        return res.get("files", [])
    except Exception as e:
        print("Error in list_packet_folders:", e)
        return []

def list_files_in_folder(folder_id, order="modifiedTime desc"):
    """List files inside a folder id"""
    q = f"'{folder_id}' in parents and trashed=false"
    try:
        res = _drive_service.files().list(
            q=q,
            fields="files(id,name,mimeType,size,modifiedTime)",
            orderBy=order,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True
        ).execute()
        return res.get("files", [])
    except Exception as e:
        print("Error fetching files for folder", folder_id, ":", e)
        return []

def get_or_create_folder(name, parent_id=config.DRIVE_FOLDER_ID):
    """Get a folder id by name under parent; create if absent"""
    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    try:
        res = _drive_service.files().list(q=q, fields="files(id,name)", includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
        files = res.get("files", [])
        if files:
            return files[0]["id"]
        meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
        folder = _drive_service.files().create(body=meta, fields="id", supportsAllDrives=True).execute()
        return folder.get("id")
    except Exception as e:
        print("Error in get_or_create_folder:", e)
        raise

def upload_media_to_drive(name, parent_id, media):
    """Upload an already-created MediaIoBaseUpload object to Drive."""
    try:
        body = {"name": name, "parents": [parent_id]}
        _drive_service.files().create(body=body, media_body=media, fields="id", supportsAllDrives=True).execute()
    except Exception as e:
        print("Error uploading media:", e)
        raise

# ---------------------------
# File download / preview
# ---------------------------
def download_file_to_bytes(file_id):
    """Return (name, mime, BytesIO) for a Drive file id"""
    try:
        meta = _drive_service.files().get(fileId=file_id, fields="id,name,mimeType", supportsAllDrives=True).execute()
        fh = io.BytesIO()
        req = _drive_service.files().get_media(fileId=file_id, supportsAllDrives=True)
        downloader = MediaIoBaseDownload(fh, req)
        done = False
        while not done:
            status, done = downloader.next_chunk()
        fh.seek(0)
        return meta["name"], meta.get("mimeType", "application/octet-stream"), fh
    except Exception as e:
        print("Error download_file_to_bytes:", e)
        raise

# ---------------------------
# Utilities: filename uniqueness, muting video
# ---------------------------
def file_exists_in_folder(filename, folder_id):
    q = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
    try:
        res = _drive_service.files().list(q=q, fields="files(id,name)", includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
        return len(res.get("files", [])) > 0
    except Exception as e:
        print("file_exists_in_folder error:", e)
        return False

def get_unique_filename(base_filename, folder_id):
    import os
    name, ext = os.path.splitext(base_filename)
    count = 1
    candidate = base_filename
    while file_exists_in_folder(candidate, folder_id):
        candidate = f"{name}(new{count}){ext}"
        count += 1
    return candidate

def mute_video(file_storage, filename):
    """Save file to temp, run ffmpeg to remove audio, return BytesIO of result"""
    import os, io, tempfile, subprocess
    ext = os.path.splitext(filename)[1] or ".mp4"
    temp_dir = tempfile.mkdtemp()
    input_path = os.path.join(temp_dir, f"input{ext}")
    output_path = os.path.join(temp_dir, f"muted{ext}")
    file_storage.save(input_path)
    try:
        subprocess.run(["ffmpeg", "-i", input_path, "-c:v", "copy", "-an", output_path],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return io.BytesIO(open(output_path, "rb").read())
    except Exception:
        # fallback to original file bytes
        return io.BytesIO(open(input_path, "rb").read())

# ---------------------------
# Secure share link helpers
# ---------------------------
def generate_secure_link(file_id, expire=3600):
    timestamp = int(time.time()) + int(expire)
    data = f"{file_id}:{timestamp}"
    sig = hmac.new(config.SECRET_SHARE_KEY, data.encode(), hashlib.sha256).hexdigest()
    return f"/preview/file/{file_id}?t={timestamp}&s={sig}"

def verify_secure_link(file_id, t, s):
    if not t or not s:
        return False
    try:
        data = f"{file_id}:{t}"
        expected = hmac.new(config.SECRET_SHARE_KEY, data.encode(), hashlib.sha256).hexdigest()
        if s != expected or int(t) < int(time.time()):
            return False
        return True
    except Exception:
        return False

# ---------------------------
# USER LOOKUP (REQUIRED FOR LOGIN)
# ---------------------------
def get_user_record(username):
    """
    Reads the Credentials sheet and returns the user record
    matching the given username.
    """
    try:
        ws = get_credentials_sheet()
        # column index is 3 (1-based) for Username
        usernames = ws.col_values(3)[1:]  # ignore header
        for i, u in enumerate(usernames, start=2):
            if str(u).strip() == str(username).strip():
                row = ws.row_values(i)
                def col(n): return row[n] if len(row) > n else ""
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
