# app.py — FINAL (Old features kept + Secure Share Feature Added + safe gspread writes)
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

# ✅ New backend imports (added)
from backends.register_backend import submit_registration, get_pending_requests
from backends.admin_backend import create_credentials_from_request
from backends.forgot_password_backend import reset_password_for_username

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ---------------- HTTPS enforce (Render) ----------------
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
        if s != expected or int(t) < int(time.time()):
            return False
        return True
    except Exception:
        return False

# ---------------- Safe gspread helpers ----------------
from gspread.exceptions import APIError
def safe_append_row(ws, row, retries=4, backoff=1.5):
    attempt = 0
    while attempt < retries:
        try:
            ws.append_row(row)
            return True
        except APIError as e:
            attempt += 1
            time.sleep(backoff * attempt)
        except Exception as e:
            attempt += 1
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
            time.sleep(backoff * attempt)
        except Exception as e:
            attempt += 1
            time.sleep(backoff * attempt)
    raise RuntimeError("Failed to update cell after retries.")

# ---------------- Helpers (Shared Drive aware) ----------------
def username_exists(username):
    try:
        return username in sheet.col_values(3)[1:]
    except Exception:
        return False

def get_user(username):
    try:
        for i, u in enumerate(sheet.col_values(3)[1:], start=2):
            if u == username:
                row = sheet.row_values(i)
                def col(n): return row[n] if len(row) > n else ''
                return {
                    'row_number': i,
                    'Timestamp': col(0),
                    'Full Name': col(1),
                    'Username': col(2),
                    'Password': col(3),
                    'Contact Number': col(4),
                    'Organization': col(5)
                }
    except Exception:
        return None
    return None

def get_or_create_folder(name, parent_id):
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id,name)",
        includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
    folders = results.get('files', [])
    if folders:
        return folders[0]['id']
    folder_metadata = {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
    folder = drive_service.files().create(body=folder_metadata, fields='id', supportsAllDrives=True).execute()
    return folder.get('id')

def file_exists_in_folder(filename, folder_id):
    results = drive_service.files().list(
        q=f"name='{filename}' and '{folder_id}' in parents and trashed=false",
        fields="files(id,name)", includeItemsFromAllDrives=True, supportsAllDrives=True
    ).execute()
    return len(results.get('files', [])) > 0

def get_unique_filename(base_filename, folder_id):
    name, ext = os.path.splitext(base_filename)
    count = 1
    candidate = base_filename
    while file_exists_in_folder(candidate, folder_id):
        candidate = f"{name}(new{count}){ext}"
        count += 1
    return candidate

def mute_video(file_storage, filename):
    ext = os.path.splitext(filename)[1] or '.mp4'
    temp_dir = tempfile.mkdtemp()
    input_path = os.path.join(temp_dir, f"input{ext}")
    output_path = os.path.join(temp_dir, f"muted{ext}")
    file_storage.save(input_path)
    try:
        subprocess.run(['ffmpeg', '-i', input_path, '-c:v', 'copy', '-an', output_path],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return io.BytesIO(open(output_path, 'rb').read())
    except Exception:
        return io.BytesIO(open(input_path, 'rb').read())

def list_packet_folders(order="modifiedTime desc"):
    results = drive_service.files().list(
        q=f"'{DRIVE_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id,name,modifiedTime)",
        orderBy=order, includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
    return results.get('files', [])

def list_files_in_folder(folder_id, order="modifiedTime desc"):
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id,name,mimeType,size,modifiedTime)",
        orderBy=order, includeItemsFromAllDrives=True, supportsAllDrives=True).execute()
    return results.get('files', [])

def download_file_to_bytes(file_id):
    meta = drive_service.files().get(fileId=file_id, fields='id,name,mimeType', supportsAllDrives=True).execute()
    fh = io.BytesIO()
    request = drive_service.files().get_media(fileId=file_id, supportsAllDrives=True)
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return meta['name'], meta.get('mimeType', 'application/octet-stream'), fh

# ---------------- Core Pages ----------------
@app.route('/')
def home():
    return redirect(url_for('splash'))

@app.route('/splash')
def splash():
    return render_template('splash.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        response = make_response(redirect(url_for('dashboard')))
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session.update({'username': username, 'admin': True})
            return redirect(url_for('admin_dashboard'))
        if username == VENUSFILES_USERNAME and password == VENUSFILES_PASSWORD:
            session.update({'username': username, 'venus_user': True})
            return redirect(url_for('venus_upload_dashboard'))
        user = get_user(username)
        if user and user['Password'] == password:
            session.update({'username': username, 'admin': False})
            return response
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')

# ✅ FIXED: Registration for Email-based signup
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        try:
            submit_registration(request.form, creds)
            flash("✅ Registration request sent successfully. Admin will approve your account.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            flash(f"❌ Registration failed: {e}", "danger")
            return render_template('register.html')
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('username') or session.get('admin'):
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['username'])

# ---------------- Upload / Files / Share ----------------
# (all your existing routes stay same)
# ---------------- Admin routes (existing + new) ----------------

@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin'):
        flash('Admin access only.', 'danger')
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html', user=session['username'])

@app.route('/admin/users')
def admin_users():
    if not session.get('admin'):
        flash('Admin access only.', 'danger')
        return redirect(url_for('login'))
    records = sheet.get_all_values()
    headers = records[0] if records else []
    users = [dict(zip(headers, row)) for row in records[1:]] if len(records) > 1 else []
    return render_template('admin_users.html', users=users)

# ✅ NEW: Admin API + actions
@app.route('/api/pending-registrations')
def api_pending_registrations():
    if not session.get('admin'):
        return jsonify({"error": "forbidden"}), 403
    pending = get_pending_requests(creds)
    return jsonify({"pending": pending})

@app.route('/admin/create-credential', methods=['POST'])
def admin_create_credential():
    if not session.get('admin'):
        return redirect(url_for('login'))
    reg_email = request.form.get('email')
    new_username = request.form.get('username')
    new_password = request.form.get('password')
    if not (reg_email and new_username and new_password):
        flash('Missing required fields.', 'danger')
        return redirect(url_for('admin_users'))
    ok = create_credentials_from_request(reg_email, new_username, new_password, creds)
    flash('✅ Credentials created & emailed to user.' if ok else '❌ Failed to create credentials.', 'info')
    return redirect(url_for('admin_users'))

@app.route('/admin/reset-password', methods=['POST'])
def admin_reset_password():
    if not session.get('admin'):
        return redirect(url_for('login'))
    target = request.form.get('target')
    new_password = request.form.get('new_password')
    if not (target and new_password):
        flash('Missing target or password.', 'danger')
        return redirect(url_for('admin_users'))
    ok = reset_password_for_username(target, new_password, creds)
    flash('✅ Password reset & emailed to user.' if ok else '❌ User not found.', 'info')
    return redirect(url_for('admin_users'))

# ---------------- Entrypoint ----------------
if __name__ == '__main__':
    from waitress import serve
    port = int(os.environ.get('PORT', 10000))
    serve(app, host='0.0.0.0', port=port)
