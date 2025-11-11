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

# gspread sheet access helpers
def get_registration_sheet():
    return _gspread_client.open_by_key(config.SHEET_ID).worksheet("Registration")

def get_credentials_sheet():
    return _gspread_client.open_by_key(config.SHEET_ID).worksheet("Credentials")

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

# upload helper for created MediaIoBaseUpload objects
def upload_media_to_drive(name, parent_id, media):
    body = {"name": name, "parents": [parent_id]}
    _drive_service.files().create(body=body, media_body=media, fields="id", supportsAllDrives=True).execute()

# folder / file helpers
def get_or_create_folder(name, parent_id=config.DRIVE_FOLDER_ID):
    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    res = _drive_service.files().list(q=q, fields="files(id,name)", includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
    files = res.get("files", [])
    if files:
        return files[0]["id"]
    meta = {"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]}
    folder = _drive_service.files().create(body=meta, fields="id", supportsAllDrives=True).execute()
    return folder.get("id")

def file_exists_in_folder(filename, folder_id):
    q = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
    res = _drive_service.files().list(q=q, fields="files(id,name)", includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
    return len(res.get("files", [])) > 0

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
    import os, tempfile, subprocess, io
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
        return io.BytesIO(open(input_path, "rb").read())

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

# secure share link helpers (use config.SECRET_SHARE_KEY)
def generate_secure_link(file_id, expire=3600):
    timestamp = int(time.time()) + expire
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

# helpers for Credentials sheet user lookup
def get_user_record(username):
    ws = get_credentials_sheet()
    usernames = ws.col_values(3)[1:]  # column C
    for i, u in enumerate(usernames, start=2):
        if u == username:
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
