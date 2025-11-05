# ✅ Full Updated app.py with Shared Drive Support
# (Replaces ALL your previous backend code)

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify, make_response
import gspread
from google.oauth2 import service_account
from datetime import datetime
import os
import io
import tempfile
import subprocess
from werkzeug.utils import secure_filename
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Enforce HTTPS on Render
@app.before_request
def enforce_https_on_render():
    if request.headers.get('X-Forwarded-Proto', 'https') != 'https':
        return redirect(request.url.replace("http://", "https://", 1))

# ✅ Correct Service Account JSON file
CREDENTIALS_PATH = '/etc/secrets/Credentials.json' if os.environ.get('RENDER') else 'Credentials.json'

# ✅ Google Auth
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=SCOPES)

# ✅ Sheets Setup
SHEET_ID = '19c2tlUmzSQsQhqNvWRuKMgdw86M0PLsKrWk51m7apA4'
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).worksheet('Sheet1')

# ✅ NEW SHARED DRIVE ROOT FOLDER
DRIVE_FOLDER_ID = '0AEZXjYA5wFlSUk9PVA'

# ✅ Google Drive API (Shared Drive Supported)
drive_service = build('drive', 'v3', credentials=creds)

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'Admin@2211'

VENUSFILES_USERNAME = 'Venusfiles'
VENUSFILES_PASSWORD = 'Natural@1969'

# ✅ Shared Drive Compatible Helper Functions

def username_exists(username):
    return username in sheet.col_values(3)[1:]

def get_user(username):
    for i, u in enumerate(sheet.col_values(3)[1:], start=2):
        if u == username:
            row = sheet.row_values(i)
            return {
                'row_number': i,
                'Timestamp': row[0],
                'Full Name': row[1],
                'Username': row[2],
                'Password': row[3],
                'Contact Number': row[4],
                'Organization': row[5]
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

    folder_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
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
    while file_exists_in_folder(base_filename, folder_id):
        base_filename = f"{name}(new{count}){ext}"
        count += 1
    return base_filename


def mute_video(file_storage, filename):
    ext = os.path.splitext(filename)[1]
    temp_dir = tempfile.mkdtemp()
    input_path = os.path.join(temp_dir, f"input{ext}")
    output_path = os.path.join(temp_dir, f"muted{ext}")
    file_storage.save(input_path)
    try:
        subprocess.run(['ffmpeg', '-i', input_path, '-c:v', 'copy', '-an', output_path], check=True)
        return io.BytesIO(open(output_path, 'rb').read())
    except:
        return io.BytesIO(open(input_path, 'rb').read())

# ✅ Routes unchanged below

@app.route('/')
def home():
    return redirect(url_for('splash'))
@app.route('/splash')
def splash(): return render_template('splash.html')

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
    if not session.get('username') or session.get('admin'):return redirect('/login')
    return render_template('dashboard.html',user=session['username'])

@app.route('/venus-upload')
def venus_upload_dashboard():
    if not session.get('venus_user'):return redirect('/login')
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

@app.route('/logout')
def logout(): session.clear(); return redirect('/login')

if __name__=='__main__':
    from waitress import serve; serve(app,host='0.0.0.0',port=int(os.environ.get('PORT',10000)))
