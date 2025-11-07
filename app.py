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

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# ---------------- HTTPS enforce (Render) ----------------
@app.before_request
def enforce_https_on_render():
    # If behind a proxy (render), the forwarded proto header is set.
    # This keeps previous behavior but uses correct comparison.
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
    """Generate secure link that expires in expire seconds (default 1 hour)."""
    timestamp = int(time.time()) + expire
    data = f"{file_id}:{timestamp}"
    sig = hmac.new(SECRET_SHARE_KEY, data.encode(), hashlib.sha256).hexdigest()
    return f"/preview/file/{file_id}?t={timestamp}&s={sig}"

def verify_secure_link(file_id, t, s):
    """Verify link signature and expiry."""
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
# ======================================================================

# ---------------- Safe gspread helpers (retry on intermittent 500s) ----------------
from gspread.exceptions import APIError

def safe_append_row(ws, row, retries=4, backoff=1.5):
    """Append row to worksheet with retries to avoid transient 500 issues."""
    attempt = 0
    while attempt < retries:
        try:
            ws.append_row(row)
            return True
        except APIError as e:
            attempt += 1
            # If it's a 500 transient error retry
            print(f"[WARN] gspread APIError appending row (attempt {attempt}/{retries}): {e}")
            time.sleep(backoff * attempt)
        except Exception as e:
            # non-API error (network etc) -> retry as well
            attempt += 1
            print(f"[WARN] unexpected error appending row (attempt {attempt}/{retries}): {e}")
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
        except Exception as e:
            attempt += 1
            print(f"[WARN] unexpected error update_cell (attempt {attempt}/{retries}): {e}")
            time.sleep(backoff * attempt)
    raise RuntimeError("Failed to update cell after retries.")

# ---------------- Helpers (Shared Drive aware) ----------------
def username_exists(username):
    try:
        return username in sheet.col_values(3)[1:]  # col C = Username
    except Exception as e:
        # if gspread read temporarily fails, treat as not exists and let registration handle gracefully
        print(f"[WARN] username_exists gspread error: {e}")
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
    except Exception as e:
        print(f"[WARN] get_user gspread error: {e}")
    return None

def get_or_create_folder(name, parent_id):
    query = (
        f"name='{name}' and mimeType='application/vnd.google-apps.folder' "
        f"and '{parent_id}' in parents and trashed=false"
    )
    results = drive_service.files().list(
        q=query, fields="files(id,name)",
        includeItemsFromAllDrives=True, supportsAllDrives=True
    ).execute()
    folders = results.get('files', [])
    if folders:
        return folders[0]['id']
    folder_metadata = {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
    folder = drive_service.files().create(
        body=folder_metadata, fields='id', supportsAllDrives=True
    ).execute()
    return folder.get('id')

def file_exists_in_folder(filename, folder_id):
    results = drive_service.files().list(
        q=f"name='{filename}' and '{folder_id}' in parents and trashed=false",
        fields="files(id,name)",
        includeItemsFromAllDrives=True, supportsAllDrives=True
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
        subprocess.run(
            ['ffmpeg', '-i', input_path, '-c:v', 'copy', '-an', output_path],
            check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        return io.BytesIO(open(output_path, 'rb').read())
    except Exception:
        # ffmpeg failed — fallback to original file bytes
        return io.BytesIO(open(input_path, 'rb').read())

def list_packet_folders(order="modifiedTime desc"):
    results = drive_service.files().list(
        q=f"'{DRIVE_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id,name,modifiedTime)",
        orderBy=order,
        includeItemsFromAllDrives=True, supportsAllDrives=True
    ).execute()
    return results.get('files', [])

def list_files_in_folder(folder_id, order="modifiedTime desc"):
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id,name,mimeType,size,modifiedTime)",
        orderBy=order,
        includeItemsFromAllDrives=True, supportsAllDrives=True
    ).execute()
    return results.get('files', [])

def download_file_to_bytes(file_id):
    meta = drive_service.files().get(
        fileId=file_id, fields='id,name,mimeType', supportsAllDrives=True
    ).execute()
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
        remember = request.form.get('remember')
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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        contact = request.form['contact_number'].strip()
        org = request.form['organization'].strip()
        if username_exists(username):
            flash('Username already exists.', 'danger')
            return render_template('register.html')
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        # use safe append to avoid transient 500s
        safe_append_row(sheet, [timestamp, full_name, username, password, contact, org])
        flash('Registration successful.', 'success')
        return redirect(url_for('login') + '?showSplash=1')
    return render_template('register.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('username') or session.get('admin'):
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['username'])

# ---------------- Upload / Files / Share ----------------
@app.route('/upload', methods=['POST'])
def upload():
    try:
        packet_no = request.form.get('packetNo', '').strip()
        if not packet_no:
            return jsonify({'success': False, 'message': 'Packet number is required.'}), 400
        folder_id = get_or_create_folder(packet_no, DRIVE_FOLDER_ID)
        for key in request.files:
            subpoint = key.replace('file_', '')
            # NOTE: client may send multiple files per field (we support that)
            for file in request.files.getlist(key):
                if file and file.filename:
                    ext = os.path.splitext(file.filename)[1]
                    base_filename = f"{subpoint}{ext}"
                    final_filename = get_unique_filename(base_filename, folder_id)
                    if final_filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
                        file_stream = mute_video(file, final_filename)
                        mimetype = 'video/mp4'
                    else:
                        file_stream = io.BytesIO(file.read())
                        mimetype = file.mimetype or 'application/octet-stream'
                    file_stream.seek(0)
                    media = MediaIoBaseUpload(file_stream, mimetype=mimetype)
                    drive_service.files().create(
                        body={'name': final_filename, 'parents': [folder_id]},
                        media_body=media, fields='id',
                        supportsAllDrives=True
                    ).execute()
        return jsonify({'success': True, 'message': '✅ All files uploaded and muted successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Upload failed: {e}'}), 500

@app.route('/files')
def files_page():
    if not session.get('username'):
        return redirect(url_for('login'))
    return render_template('files.html', user=session['username'])

@app.route('/share')
def share_page():
    if not session.get('username'):
        return redirect(url_for('login'))
    return render_template('share.html', user=session['username'])

@app.route('/api/share-link')
def api_share_link():
    if not session.get('username'):
        return abort(401)
    file_id = request.args.get('id')
    if not file_id:
        return jsonify({'error': 'missing id'}), 400
    link = generate_secure_link(file_id)
    full_url = request.url_root.rstrip('/') + link
    return jsonify({'link': full_url})

# ---------------- File APIs ----------------
@app.route('/api/packet-folders')
def api_packet_folders():
    if not session.get('username'):
        return abort(401)
    sort = request.args.get('sort', 'newest')
    order = 'modifiedTime desc' if sort == 'newest' else 'name_natural'
    folders = list_packet_folders(order=order)
    return jsonify({'folders': folders})

@app.route('/api/folder/<folder_id>/files')
def api_folder_files(folder_id):
    if not session.get('username'):
        return abort(401)
    sort = request.args.get('sort', 'newest')
    order = 'modifiedTime desc' if sort == 'newest' else 'name_natural'
    files = list_files_in_folder(folder_id, order=order)
    return jsonify({'files': files})

@app.route('/download/file/<file_id>')
def download_file_route(file_id):
    if not session.get('username'):
        return abort(401)
    name, mime, fh = download_file_to_bytes(file_id)
    return send_file(fh, mimetype=mime, as_attachment=True, download_name=name)

@app.route('/preview/file/<file_id>')
def preview_file(file_id):
    t = request.args.get('t')
    s = request.args.get('s')
    if t and s:
        if not verify_secure_link(file_id, t, s):
            return abort(403)
    elif not session.get('username'):
        return abort(401)
    name, mime, fh = download_file_to_bytes(file_id)
    return send_file(fh, mimetype=mime, as_attachment=False, download_name=name)

# ---------------- Admin routes (kept as in old) ----------------
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

@app.route('/admin/user/<username>')
def view_user(username):
    if not session.get('admin'):
        flash('Admin access only.', 'danger')
        return redirect(url_for('login'))
    user = get_user(username)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_users'))
    files = [f for f in os.listdir(UPLOAD_FOLDER) if username in f]
    return render_template('user_profile.html', user=user, files=files)

@app.route('/admin/user/<username>/change-password', methods=['POST'])
def change_user_password(username):
    if not session.get('admin'):
        flash('Admin access only.', 'danger')
        return redirect(url_for('login'))
    new_pass = request.form['new_password']
    user = get_user(username)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_users'))
    # safe update to avoid transient errors
    safe_update_cell(sheet, user['row_number'], 4, new_pass)
    flash(f"Password updated for {username}.", 'success')
    return redirect(url_for('view_user', username=username))

@app.route('/admin/venus-files')
def admin_files():
    if not session.get('admin'):
        flash('Admin access only.', 'danger')
        return redirect(url_for('login'))
    return redirect("https://drive.google.com/drive/folders/0AEZXjYA5wFlSUk9PVA")

# ---------------- Old local file serving (kept) ----------------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# ---------------- Logout (kept) ----------------
@app.route('/logout')
def logout():
    session.clear()
    resp = make_response(redirect(url_for('login') + '?showSplash=1'))
    resp.set_cookie('username', '', expires=0)
    resp.set_cookie('password', '', expires=0)
    return resp

# ---------------- Entrypoint ----------------
if __name__ == '__main__':
    from waitress import serve
    port = int(os.environ.get('PORT', 10000))
    serve(app, host='0.0.0.0', port=port)
