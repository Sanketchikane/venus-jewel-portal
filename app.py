# ✅ Full Updated app.py with Shared Drive Support + In-Dashboard File Browser, Downloads, Search/Sort, MP4 Preview

from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify, abort, send_file
import gspread
from google.oauth2 import service_account
from datetime import datetime
import os
import io
import tempfile
import zipfile
import subprocess
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Enforce HTTPS on Render
@app.before_request
def enforce_https_on_render():
    if request.headers.get('X-Forwarded-Proto', 'https') != 'https':
        return redirect(request.url.replace("http://", "https://", 1))

# ✅ Service Account JSON path
CREDENTIALS_PATH = '/etc/secrets/Credentials.json' if os.environ.get('RENDER') else 'Credentials.json'

# ✅ Google Auth
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)

# ✅ Sheets Setup
SHEET_ID = '19c2tlUmzSQsQhqNvWRuKMgdw86M0PLsKrWk51m7apA4'
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet('Sheet1')

# ✅ Shared Drive Root (Packet No folders live directly under this)
DRIVE_FOLDER_ID = '0AEZXjYA5wFlSUk9PVA'

# ✅ Google Drive API
drive_service = build('drive', 'v3', credentials=creds)

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'Admin@2211'
VENUSFILES_USERNAME = 'Venusfiles'
VENUSFILES_PASSWORD = 'Natural@1969'

# ========= Helpers =========

def username_exists(username):
    return username in sheet.col_values(3)[1:]

def get_user(username):
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
    return None

def get_or_create_folder(name, parent_id):
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    results = drive_service.files().list(
        q=query,
        fields="files(id, name)",
        includeItemsFromAllDrives=True,
        supportsAllDrives=True
    ).execute()
    folders = results.get('files', [])
    if folders:
        return folders[0]['id']
    folder_metadata = {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
    folder = drive_service.files().create(
        body=folder_metadata,
        fields='id',
        supportsAllDrives=True
    ).execute()
    return folder.get('id')

def file_exists_in_folder(filename, folder_id):
    query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
    results = drive_service.files().list(
        q=query,
        fields="files(id, name)",
        includeItemsFromAllDrives=True,
        supportsAllDrives=True
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
    ext = os.path.splitext(filename)[1]
    temp_dir = tempfile.mkdtemp()
    input_path = os.path.join(temp_dir, f"input{ext}")
    output_path = os.path.join(temp_dir, f"muted{ext}")
    file_storage.save(input_path)
    try:
        subprocess.run(['ffmpeg', '-i', input_path, '-c:v', 'copy', '-an', output_path], check=True)
        return io.BytesIO(open(output_path, 'rb').read())
    except Exception:
        return io.BytesIO(open(input_path, 'rb').read())

def list_packet_folders():
    """All Packet No folders directly under DRIVE_FOLDER_ID."""
    results = drive_service.files().list(
        q=f"'{DRIVE_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false",
        fields="files(id,name,modifiedTime)",
        orderBy="modifiedTime desc, name_natural",  # newest first by default
        includeItemsFromAllDrives=True,
        supportsAllDrives=True
    ).execute()
    return results.get('files', [])

def list_files_in_folder(folder_id, order="modifiedTime desc"):
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents and trashed=false",
        fields="files(id,name,mimeType,size,modifiedTime)",
        orderBy=order,  # name_natural or modifiedTime desc
        includeItemsFromAllDrives=True,
        supportsAllDrives=True
    ).execute()
    return results.get('files', [])

def download_file_to_bytes(file_id):
    """Return (name, mimetype, BytesIO) from Drive."""
    meta = drive_service.files().get(
        fileId=file_id, fields='id,name,mimeType',
        supportsAllDrives=True
    ).execute()
    fh = io.BytesIO()
    request = drive_service.files().get_media(fileId=file_id)
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)
    return meta['name'], meta.get('mimeType', 'application/octet-stream'), fh

# ========= Routes =========

@app.route('/')
def home():
    return redirect(url_for('splash'))

@app.route('/splash')
def splash():
    return render_template('splash.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method=='POST':
        u=request.form['username'].strip(); p=request.form['password'].strip()
        if u==ADMIN_USERNAME and p==ADMIN_PASSWORD:
            session.update({'username':u,'admin':True});return redirect('/admin-dashboard')
        if u==VENUSFILES_USERNAME and p==VENUSFILES_PASSWORD:
            session.update({'username':u,'venus_user':True});return redirect('/venus-upload')
        user=get_user(u)
        if user and user['Password']==p:
            session.update({'username':u,'admin':False});return redirect('/dashboard')
        flash('Invalid credentials.','danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('username') or session.get('admin'):
        return redirect('/login')
    return render_template('dashboard.html', user=session['username'])

@app.route('/venus-upload')
def venus_upload_dashboard():
    if not session.get('venus_user'):
        return redirect('/login')
    return render_template('Venus_Upload.html')

@app.route('/upload', methods=['POST'])
def upload():
    try:
        packet_no=request.form.get('packetNo','').strip()
        if not packet_no:
            return jsonify({'success':False,'message':'Packet number required'}),400

        folder_id=get_or_create_folder(packet_no, DRIVE_FOLDER_ID)
        for key in request.files:
            name=key.replace('file_','')
            for file in request.files.getlist(key):
                if file and file.filename:
                    ext=os.path.splitext(file.filename)[1]
                    fname=get_unique_filename(f"{name}{ext}",folder_id)
                    # If video → mute, else passthrough
                    if fname.lower().endswith(('.mp4','.mov','.avi','.mkv','.webm')):
                        stream=mute_video(file,fname); mime='video/mp4'
                    else:
                        stream=io.BytesIO(file.read()); mime=file.mimetype
                    stream.seek(0)
                    media=MediaIoBaseUpload(stream,mimetype=mime)
                    drive_service.files().create(
                        body={'name':fname,'parents':[folder_id]},
                        media_body=media,
                        fields='id',
                        supportsAllDrives=True
                    ).execute()
        return jsonify({'success':True,'message':'✅ Uploaded to Shared Drive'})
    except Exception as e:
        return jsonify({'success':False,'message':f'Upload failed: {e}'}),500

# ======== NEW: Dashboard File APIs (login required; all users see all Packet No) ========

@app.route('/api/packet-folders')
def api_packet_folders():
    if not session.get('username'):
        return abort(401)
    folders = list_packet_folders()
    return jsonify({'folders': folders})

@app.route('/api/folder/<folder_id>/files')
def api_folder_files(folder_id):
    if not session.get('username'):
        return abort(401)
    # allow client to pass ?sort=name or ?sort=newest
    sort = request.args.get('sort', 'newest')
    order = 'modifiedTime desc' if sort == 'newest' else 'name_natural'
    files = list_files_in_folder(folder_id, order=order)
    return jsonify({'files': files})

@app.route('/download/file/<file_id>')
def download_file(file_id):
    if not session.get('username'):
        return abort(401)
    name, mime, fh = download_file_to_bytes(file_id)
    return send_file(fh, mimetype=mime or 'application/octet-stream', as_attachment=True, download_name=name)

@app.route('/download/folder/<folder_id>')
def download_folder(folder_id):
    if not session.get('username'):
        return abort(401)
    # Zip all immediate files in the packet folder (no deep recursion)
    files = list_files_in_folder(folder_id, order='name_natural')
    packet_meta = drive_service.files().get(fileId=folder_id, fields='name', supportsAllDrives=True).execute()
    packet_name = packet_meta.get('name', 'packet')

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=f'_{packet_name}.zip')
    tmp_path = tmp.name
    tmp.close()

    with zipfile.ZipFile(tmp_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for f in files:
            if f.get('mimeType') == 'application/vnd.google-apps.folder':
                continue  # skip nested
            fname, _, fh = download_file_to_bytes(f['id'])
            zf.writestr(fname, fh.read())

    return send_file(tmp_path, as_attachment=True, download_name=f'{packet_name}.zip')

# NEW: Inline preview (no attachment) for MP4 (and other previewables)
@app.route('/preview/file/<file_id>')
def preview_file(file_id):
    if not session.get('username'):
        return abort(401)
    name, mime, fh = download_file_to_bytes(file_id)
    # Stream without forcing download; browser will preview if it can (e.g., video/mp4)
    return send_file(fh, mimetype=mime or 'application/octet-stream', as_attachment=False, download_name=name)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

# Optional Admin stub
@app.route('/admin-dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect('/login')
    return render_template('admin_dashboard.html', user=session['username']) if os.path.exists('templates/admin_dashboard.html') else "Admin dashboard"

if __name__=='__main__':
    from waitress import serve
    serve(app,host='0.0.0.0',port=int(os.environ.get('PORT',10000)))
