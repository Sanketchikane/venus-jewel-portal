# backends/utils_backend.py
import os, io, tempfile, subprocess, time, hmac, hashlib, logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import gspread
import config
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.errors import HttpError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("utils_backend")

# initialize creds & clients once
_creds = service_account.Credentials.from_service_account_file(
    config.CREDENTIALS_PATH, scopes=config.SCOPES
)
_gspread_client = gspread.authorize(_creds)
_drive_service = build("drive", "v3", credentials=_creds)

# -------------------------
# Sheets helpers
# -------------------------
def get_registration_sheet(tab_name="Registration"):
    """
    Return a worksheet for registration. If tab doesn't exist, create it.
    """
    sh = _gspread_client.open_by_key(config.SHEET_ID)
    try:
        return sh.worksheet(tab_name)
    except Exception:
        # create worksheet with reasonable default rows/cols
        try:
            ws = sh.add_worksheet(title=tab_name, rows="1000", cols="20")
            return ws
        except Exception as e:
            logger.exception("Failed creating worksheet %s: %s", tab_name, e)
            raise

def get_credentials_sheet(tab_name="Credentials"):
    sh = _gspread_client.open_by_key(config.SHEET_ID)
    try:
        return sh.worksheet(tab_name)
    except Exception:
        # If it doesn't exist, create it with expected headers
        try:
            ws = sh.add_worksheet(title=tab_name, rows="1000", cols="20")
            headers = ["Timestamp", "Full Name", "Username", "Password", "Contact Number", "Organization", "Email"]
            ws.append_row(headers)
            return ws
        except Exception as e:
            logger.exception("Failed creating Credentials worksheet: %s", e)
            raise

# -------------------------
# Drive helpers (Shared Drive ready)
# -------------------------
def list_packet_folders(order="modifiedTime desc"):
    """
    List folders under configured DRIVE_FOLDER_ID (works for Shared Drive too).
    """
    q = f"'{config.DRIVE_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
    try:
        res = _drive_service.files().list(
            q=q,
            fields="files(id,name,modifiedTime)",
            orderBy=order,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            pageSize=1000
        ).execute()
        return res.get("files", [])
    except HttpError as e:
        logger.exception("Drive API error listing packet folders: %s", e)
        raise
    except Exception as e:
        logger.exception("Unexpected error listing packet folders: %s", e)
        return []

def list_files_in_folder(folder_id, order="modifiedTime desc"):
    """
    Return files in a folder (works for Shared Drive).
    """
    q = f"'{folder_id}' in parents and trashed=false"
    try:
        res = _drive_service.files().list(
            q=q,
            fields="files(id,name,mimeType,size,modifiedTime)",
            orderBy=order,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            pageSize=1000
        ).execute()
        return res.get("files", [])
    except HttpError as e:
        logger.exception("Drive API error listing files in folder %s: %s", folder_id, e)
        raise
    except Exception as e:
        logger.exception("Unexpected error listing files in folder %s: %s", folder_id, e)
        return []

def get_or_create_folder(name, parent_id=config.DRIVE_FOLDER_ID):
    """
    Find or create a folder with given name inside parent_id.
    """
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
        logger.exception("Error get_or_create_folder(%s): %s", name, e)
        raise

def upload_media_to_drive(name, parent_id, media):
    body = {"name": name, "parents": [parent_id]}
    try:
        _drive_service.files().create(body=body, media_body=media, fields="id", supportsAllDrives=True).execute()
    except Exception as e:
        logger.exception("Error uploading %s to folder %s: %s", name, parent_id, e)
        raise

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

# -------------------------
# Download helpers
# -------------------------
def download_file_to_bytes(file_id):
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
    except HttpError as e:
        logger.exception("Drive API error downloading file %s: %s", file_id, e)
        raise
    except Exception as e:
        logger.exception("Unexpected error downloading file %s: %s", file_id, e)
        raise

# -------------------------
# Video mute helper (ffmpeg must be present on host)
# -------------------------
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
        # if ffmpeg not available or fails, return original file bytes
        return io.BytesIO(open(input_path, "rb").read())

# -------------------------
# Secure share link helpers (use config.SECRET_SHARE_KEY)
# -------------------------
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
    except Exception as e:
        logger.exception("verify_secure_link error: %s", e)
        return False

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

        # Column C contains the username list (1-based columns in Sheets)
        usernames = ws.col_values(3)[1:]  # ignore header row

        for i, u in enumerate(usernames, start=2):
            if str(u).strip().lower() == str(username).strip().lower():
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
                    "Email": col(6) if len(row) > 6 else ""
                }

        return None
    except Exception as e:
        logger.exception("ERROR get_user_record: %s", e)
        return None
