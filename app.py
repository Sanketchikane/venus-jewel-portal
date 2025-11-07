# app.py — FINAL VENUS JEWEL FILE PORTAL
# (All old features + Folder ZIP download + File Share + Mobile + Secure)

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash,
    send_from_directory, jsonify, make_response, abort, send_file
)
import gspread, os, io, time, zipfile, tempfile, subprocess, hmac, hashlib
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from datetime import datetime
from gspread.exceptions import APIError

app = Flask(__name__)
app.secret_key = "venus_secret_key_2025"

# ---------------- HTTPS enforce ----------------
@app.before_request
def enforce_https_on_render():
    if request.headers.get("X-Forwarded-Proto", request.scheme) != "https":
        return redirect(request.url.replace("http://", "https://", 1))

# ---------------- Google setup ----------------
CREDENTIALS_PATH = "/etc/secrets/Credentials.json" if os.environ.get("RENDER") else "Credentials.json"
SCOPES = ["https://www.googleapis.com/auth/drive", "https://www.googleapis.com/auth/spreadsheets"]
creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)

client = gspread.authorize(creds)
SHEET_ID = "181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro"
sheet = client.open_by_key(SHEET_ID).worksheet("Registration")

DRIVE_FOLDER_ID = "0AEZXjYA5wFlSUk9PVA"
drive_service = build("drive", "v3", credentials=creds)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_USERNAME, ADMIN_PASSWORD = "admin", "Admin@2211"
VENUSFILES_USERNAME, VENUSFILES_PASSWORD = "Venusfiles", "Natural@1969"

# ---------------- Secure share helpers ----------------
SECRET_SHARE_KEY = b"venus_secure_share_key_2025"

def generate_secure_link(file_id, expire=3600):
    ts = int(time.time()) + expire
    data = f"{file_id}:{ts}"
    sig = hmac.new(SECRET_SHARE_KEY, data.encode(), hashlib.sha256).hexdigest()
    return f"/preview/file/{file_id}?t={ts}&s={sig}"

def verify_secure_link(file_id, t, s):
    try:
        exp = int(t)
        sig = hmac.new(SECRET_SHARE_KEY, f"{file_id}:{t}".encode(), hashlib.sha256).hexdigest()
        return sig == s and exp > int(time.time())
    except:
        return False

# ---------------- Safe gspread writes ----------------
def safe_append_row(ws, row, retries=4, backoff=1.5):
    for i in range(retries):
        try:
            ws.append_row(row)
            return True
        except APIError:
            time.sleep(backoff * (i+1))
    raise RuntimeError("Failed to append row after retries")

def safe_update_cell(ws, row, col, value, retries=4, backoff=1.5):
    for i in range(retries):
        try:
            ws.update_cell(row, col, value)
            return True
        except APIError:
            time.sleep(backoff * (i+1))
    raise RuntimeError("Failed to update cell after retries")

# ---------------- Helpers ----------------
def username_exists(username):
    try:
        return username in sheet.col_values(3)[1:]
    except:
        return False

def get_user(username):
    try:
        for i, u in enumerate(sheet.col_values(3)[1:], start=2):
            if u == username:
                row = sheet.row_values(i)
                return {"row_number": i, "Username": row[2], "Password": row[3]}
    except:
        return None
    return None

def get_or_create_folder(name, parent_id):
    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    res = drive_service.files().list(q=q, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    folders = res.get("files", [])
    if folders:
        return folders[0]["id"]
    folder = drive_service.files().create(
        body={"name": name, "mimeType": "application/vnd.google-apps.folder", "parents": [parent_id]},
        fields="id", supportsAllDrives=True
    ).execute()
    return folder["id"]

def mute_video(file_storage, filename):
    ext = os.path.splitext(filename)[1] or ".mp4"
    temp_dir = tempfile.mkdtemp()
    inp, out = os.path.join(temp_dir, f"i{ext}"), os.path.join(temp_dir, f"o{ext}")
    file_storage.save(inp)
    try:
        subprocess.run(["ffmpeg", "-i", inp, "-c:v", "copy", "-an", out], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return io.BytesIO(open(out, "rb").read())
    except:
        return io.BytesIO(open(inp, "rb").read())

def list_packet_folders(order="modifiedTime desc"):
    res = drive_service.files().list(
        q=f"'{DRIVE_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id,name,modifiedTime)", orderBy=order,
        supportsAllDrives=True, includeItemsFromAllDrives=True
    ).execute()
    return res.get("files", [])

def list_files_in_folder(fid, order="modifiedTime desc"):
    res = drive_service.files().list(
        q=f"'{fid}' in parents and trashed=false",
        fields="files(id,name,mimeType,modifiedTime)", orderBy=order,
        supportsAllDrives=True, includeItemsFromAllDrives=True
    ).execute()
    return res.get("files", [])

def download_file_to_bytes(fid):
    meta = drive_service.files().get(fileId=fid, fields="id,name,mimeType", supportsAllDrives=True).execute()
    fh = io.BytesIO()
    req = drive_service.files().get_media(fileId=fid, supportsAllDrives=True)
    downloader = MediaIoBaseDownload(fh, req)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    fh.seek(0)
    return meta["name"], meta.get("mimeType", "application/octet-stream"), fh

# ---------------- Core Routes ----------------
@app.route("/")
def home(): return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u, p = request.form["username"].strip(), request.form["password"].strip()
        if u == ADMIN_USERNAME and p == ADMIN_PASSWORD:
            session.update({"username": u, "admin": True})
            return redirect(url_for("admin_dashboard"))
        if u == VENUSFILES_USERNAME and p == VENUSFILES_PASSWORD:
            session.update({"username": u})
            return redirect(url_for("dashboard"))
        user = get_user(u)
        if user and user["Password"] == p:
            session.update({"username": u})
            return redirect(url_for("dashboard"))
        flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data = [ts, request.form["full_name"], request.form["username"], request.form["password"], request.form["contact_number"], request.form["organization"]]
        if username_exists(request.form["username"]):
            flash("Username already exists", "danger")
            return render_template("register.html")
        safe_append_row(sheet, data)
        flash("Registration successful", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/dashboard")
def dashboard():
    if not session.get("username"): return redirect(url_for("login"))
    return render_template("dashboard.html", user=session["username"])

# ---------------- Upload ----------------
@app.route("/upload", methods=["POST"])
def upload():
    try:
        packet = request.form.get("packetNo", "").strip()
        if not packet: return jsonify({"success": False, "message": "Packet No required"}), 400
        fid = get_or_create_folder(packet, DRIVE_FOLDER_ID)
        for k in request.files:
            sub = k.replace("file_", "")
            for f in request.files.getlist(k):
                if f and f.filename:
                    ext = os.path.splitext(f.filename)[1]
                    final = f"{sub}{ext}"
                    stream = mute_video(f, final) if final.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")) else io.BytesIO(f.read())
                    stream.seek(0)
                    drive_service.files().create(
                        body={"name": final, "parents": [fid]},
                        media_body=MediaIoBaseUpload(stream, mimetype=f.mimetype or "application/octet-stream"),
                        fields="id", supportsAllDrives=True
                    ).execute()
        return jsonify({"success": True, "message": "✅ All files uploaded"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

# ---------------- Files & Share ----------------
@app.route("/files")
def files_page():
    if not session.get("username"): return redirect(url_for("login"))
    return render_template("files.html", user=session["username"])

@app.route("/api/packet-folders")
def api_packet_folders():
    if not session.get("username"): return abort(401)
    sort = request.args.get("sort", "newest")
    order = "modifiedTime desc" if sort == "newest" else "name_natural"
    return jsonify({"folders": list_packet_folders(order)})

@app.route("/api/folder/<fid>/files")
def api_folder_files(fid):
    if not session.get("username"): return abort(401)
    sort = request.args.get("sort", "newest")
    order = "modifiedTime desc" if sort == "newest" else "name_natural"
    return jsonify({"files": list_files_in_folder(fid, order)})

@app.route("/api/share-link")
def api_share_link():
    if not session.get("username"): return abort(401)
    fid = request.args.get("id")
    link = generate_secure_link(fid)
    return jsonify({"link": request.url_root.rstrip("/") + link})

@app.route("/download/file/<fid>")
def download_file(fid):
    if not session.get("username"): return abort(401)
    n, m, f = download_file_to_bytes(fid)
    return send_file(f, mimetype=m, as_attachment=True, download_name=n)

@app.route("/preview/file/<fid>")
def preview_file(fid):
    t, s = request.args.get("t"), request.args.get("s")
    if t and s and not verify_secure_link(fid, t, s): return abort(403)
    if not session.get("username"): return abort(401)
    n, m, f = download_file_to_bytes(fid)
    return send_file(f, mimetype=m, as_attachment=False, download_name=n)

# ---------------- Folder ZIP download ----------------
@app.route("/download/folder/<fid>")
def download_folder(fid):
    if not session.get("username"): return abort(401)
    meta = drive_service.files().get(fileId=fid, fields="name", supportsAllDrives=True).execute()
    name = meta.get("name", "folder")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in list_files_in_folder(fid):
            if f["mimeType"] == "application/vnd.google-apps.folder": continue
            fn, _, fh = download_file_to_bytes(f["id"])
            zf.writestr(fn, fh.read())
    return send_file(tmp.name, as_attachment=True, download_name=f"{name}.zip")

# ---------------- Logout ----------------
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- Entrypoint ----------------
if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=10000)
