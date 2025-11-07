# app.py — FINAL Venus Jewel File Portal (All features + Safe Sheets + Folder Download)

from flask import (
    Flask, render_template, request, redirect, url_for, session, flash,
    send_from_directory, jsonify, make_response, abort, send_file
)
import gspread
from google.oauth2 import service_account
from datetime import datetime
import os
import io
import tempfile
import zipfile
import subprocess
import time, hmac, hashlib
from werkzeug.utils import secure_filename
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
from gspread.exceptions import APIError

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ---------------- HTTPS enforce ----------------
@app.before_request
def enforce_https_on_render():
    if request.headers.get('X-Forwarded-Proto', request.scheme) != 'https':
        return redirect(request.url.replace("http://", "https://", 1))

# ---------------- Google Auth / Drive / Sheets ----------------
CREDENTIALS_PATH = '/etc/secrets/Credentials.json' if os.environ.get('RENDER') else 'Credentials.json'
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)

client = gspread.authorize(creds)
SHEET_ID = '181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro'
sheet = client.open_by_key(SHEET_ID).worksheet('Registration')

DRIVE_FOLDER_ID = '0AEZXjYA5wFlSUk9PVA'
drive_service = build('drive', 'v3', credentials=creds)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'Admin@2211'
VENUSFILES_USERNAME = 'Venusfiles'
VENUSFILES_PASSWORD = 'Natural@1969'

# ======================= SHARE LINK SECURITY ==========================
SECRET_SHARE_KEY = b"venus_secure_share_key_2025"

def generate_secure_link(file_id, expire=3600):
    timestamp = int(time.time()) + expire
    data = f"{file_id}:{timestamp}"
    sig = hmac.new(SECRET_SHARE_KEY, data.encode(), hashlib.sha256).hexdigest()
    return f"/preview/file/{file_id}?t={timestamp}&s={sig}"

def verify_secure_link(file_id, t, s):
    if not t or not s:
        return False
    try:
        data = f"{file_id}:{t}"
        expected = hmac.new(SECRET_SHARE_KEY, data.encode(), hashlib.sha256).hexdigest()
        return s == expected and int(t) > int(time.time())
    except Exception:
        return False

# ---------------- Safe gspread helpers ----------------
def safe_append_row(ws, row, retries=4, backoff=1.5):
    attempt = 0
    while attempt < retries:
        try:
            ws.append_row(row)
            return True
        except APIError as e:
            attempt += 1
            print(f"[WARN] gspread APIError appending row (attempt {attempt}/{retries}): {e}")
            time.sleep(backoff * attempt)
        except Exception as e:
            attempt += 1
            print(f"[WARN] unexpected error appending row: {e}")
            time.sleep(backoff * attempt)
    raise RuntimeError("Failed to append row after retries.")

def safe_update_cell(ws, row, col, value, retries=4, backoff=1.5):
    attempt = 0
    while attempt < retries:
        try:
            ws.update_cell(row, col, value)
            return True
        except APIError as e:
            attempt += 1
            print(f"[WARN] gspread APIError update_cell (attempt {attempt}/{retries}): {e}")
            time.sleep(backoff * attempt)
    raise RuntimeError("Failed to update cell after retries.")

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
                def col(n): return row[n] if len(row) > n else ''
                return {
                    'row_number': i,
                    'Full Name': col(1),
                    'Username': col(2),
                    'Password': col(3),
                    'Contact Number': col(4),
                    'Organization': col(5)
                }
    except:
        pass
    return None

def get_or_create_folder(name, parent_id):
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    res = drive_service.files().list(q=query, fields="files(id)", supportsAllDrives=True, includeItemsFromAllDrives=True).execute()
    folders = res.get('files', [])
    if folders:
        return folders[0]['id']
    meta = {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
    folder = drive_service.files().create(body=meta, fields='id', supportsAllDrives=True).execute()
    return folder['id']

def list_packet_folders(order="modifiedTime desc"):
    res = drive_service.files().list(
        q=f"'{DRIVE_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id,name,modifiedTime)",
        orderBy=order,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    return res.get('files', [])

def list_files_in_folder(folder_id, order="modifiedTime desc"):
    res = drive_service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id,name,mimeType,size,modifiedTime)",
        orderBy=order,
        supportsAllDrives=True,
        includeItemsFromAllDrives=True
    ).execute()
    return res.get('files', [])

def download_file_to_bytes(file_id):
    meta = drive_service.files().get(fileId=file_id, fields='id,name,mimeType', supportsAllDrives=True).execute()
    fh = io.BytesIO()
    req = drive_service.files().get_media(fileId=file_id, supportsAllDrives=True)
    downloader = MediaIoBaseDownload(fh, req)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return meta['name'], meta.get('mimeType', 'application/octet-stream'), fh

# ---------------- Core Pages ----------------
@app.route('/')
def home(): return redirect(url_for('splash'))

@app.route('/splash')
def splash(): return render_template('splash.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username, password = request.form['username'].strip(), request.form['password'].strip()
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.update({'username': username, 'admin': True})
            return redirect(url_for('admin_dashboard'))
        user = get_user(username)
        if user and user['Password'] == password:
            session.update({'username': username})
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        safe_append_row(sheet, [ts, request.form['full_name'], request.form['username'], request.form['password'], request.form['contact_number'], request.form['organization']])
        flash('Registration successful.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('username'): return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['username'])

@app.route('/files')
def files_page():
    if not session.get('username'): return redirect(url_for('login'))
    return render_template('files.html', user=session['username'])

@app.route('/api/packet-folders')
def api_packet_folders():
    if not session.get('username'): return abort(401)
    sort = request.args.get('sort', 'newest')
    order = 'modifiedTime desc' if sort == 'newest' else 'name_natural'
    return jsonify({'folders': list_packet_folders(order)})

@app.route('/api/folder/<folder_id>/files')
def api_folder_files(folder_id):
    if not session.get('username'): return abort(401)
    sort = request.args.get('sort', 'newest')
    order = 'modifiedTime desc' if sort == 'newest' else 'name_natural'
    return jsonify({'files': list_files_in_folder(folder_id, order)})

@app.route('/api/share-link')
def api_share_link():
    if not session.get('username'): return abort(401)
    file_id = request.args.get('id')
    link = generate_secure_link(file_id)
    full_url = request.url_root.rstrip('/') + link
    return jsonify({'link': full_url})

@app.route('/download/file/<file_id>')
def download_file_route(file_id):
    if not session.get('username'): return abort(401)
    name, mime, fh = download_file_to_bytes(file_id)
    return send_file(fh, mimetype=mime, as_attachment=True, download_name=name)

@app.route('/preview/file/<file_id>')
def preview_file(file_id):
    t, s = request.args.get('t'), request.args.get('s')
    if t and s and not verify_secure_link(file_id, t, s): return abort(403)
    elif not session.get('username'): return abort(401)
    name, mime, fh = download_file_to_bytes(file_id)
    return send_file(fh, mimetype=mime, as_attachment=False, download_name=name)

# ---------------- Folder Download ----------------
@app.route('/download/folder/<folder_id>')
def download_folder(folder_id):
    if not session.get('username'): return abort(401)
    try:
        meta = drive_service.files().get(fileId=folder_id, fields='name', supportsAllDrives=True).execute()
        folder_name = meta.get('name', 'folder')
    except Exception as e:
        return abort(404, description=f"Folder not found: {e}")
    files = list_files_in_folder(folder_id)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{folder_name}.zip")
    tmp_path = tmp.name; tmp.close()
    with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            if f['mimeType'] == 'application/vnd.google-apps.folder': continue
            fname, _, fh = download_file_to_bytes(f['id'])
            zf.writestr(fname, fh.read())
    return send_file(tmp_path, as_attachment=True, download_name=f"{folder_name}.zip")

@app.route('/download/folders', methods=['POST'])
def download_multiple_folders():
    if not session.get('username'): return abort(401)
    folder_ids = request.form.getlist('folder_ids[]') or []
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix='_packets.zip')
    tmp_path = tmp.name; tmp.close()
    with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for fid in folder_ids:
            try:
                meta = drive_service.files().get(fileId=fid, fields='name', supportsAllDrives=True).execute()
                name = meta.get('name', fid)
            except: name = fid
            files = list_files_in_folder(fid)
            for f in files:
                if f['mimeType'] == 'application/vnd.google-apps.folder': continue
                fname, _, fh = download_file_to_bytes(f['id'])
                zf.writestr(f"{name}/{fname}", fh.read())
    return send_file(tmp_path, as_attachment=True, download_name='packets.zip')

# ---------------- Logout ----------------
@app.route('/logout')
def logout():
    session.clear()
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('username', '', expires=0)
    return resp

# ---------------- Entrypoint ----------------
if __name__ == '__main__':
    from waitress import serve
    port = int(os.environ.get('PORT', 10000))
    serve(app, host='0.0.0.0', port=port)
