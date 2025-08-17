from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory, jsonify, make_response
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import io
import tempfile
import subprocess
from werkzeug.utils import secure_filename
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google_auth_oauthlib.flow import Flow
import google.auth.transport.requests

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Enforce HTTPS
@app.before_request
def enforce_https_on_render():
    if request.headers.get('X-Forwarded-Proto', 'http') != 'https':
        return redirect(request.url.replace("http://", "https://", 1))

CREDENTIALS_PATH = '/etc/secrets/Credentials.json' if os.environ.get('RENDER') else 'Credentials.json'
CLIENT_SECRET_FILE = '/etc/secrets/client_secret.json' if os.environ.get('RENDER') else 'client_secret.json'

scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
client = gspread.authorize(creds)
SHEET_ID = '19c2tlUmzSQsQhqNvWRuKMgdw86M0PLsKrWk51m7apA4'
sheet = client.open_by_key(SHEET_ID).worksheet('Sheet1')

UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'Admin@2211'
VENUSFILES_USERNAME = 'Venusfiles'
VENUSFILES_PASSWORD = 'Natural@1969'

DRIVE_FOLDER_ID = '1Yjvp5TMg7mERWxq4dsYJq748CcQIucLK'
drive_creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=['https://www.googleapis.com/auth/drive'])
drive_service = build('drive', 'v3', credentials=drive_creds)

# ---------------------------
# USER HELPERS
# ---------------------------
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

# ---------------------------
# GOOGLE DRIVE HELPERS
# ---------------------------
def get_or_create_folder(name, parent_id):
    query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and '{parent_id}' in parents and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
    folders = results.get('files', [])
    if folders:
        return folders[0]['id']
    folder_metadata = {'name': name, 'mimeType': 'application/vnd.google-apps.folder', 'parents': [parent_id]}
    folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
    return folder.get('id')

def file_exists_in_folder(filename, folder_id):
    query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
    results = drive_service.files().list(q=query, fields="files(id, name)").execute()
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
    except Exception:
        return io.BytesIO(open(input_path, 'rb').read())

# ---------------------------
# ROUTES
# ---------------------------
@app.route('/')
def home():
    return redirect(url_for('splash'))

@app.route('/splash')
def splash():
    return render_template('splash.html')

# ---------------------------
# FIXED LOGIN WITH GOOGLE OAUTH2
# ---------------------------
@app.route('/login')
def login():
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
        redirect_uri=url_for('oauth2callback', _external=True, _scheme="https")
    )
    auth_url, state = flow.authorization_url(prompt='consent', include_granted_scopes='true')
    session['state'] = state
    return redirect(auth_url)

@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=["openid", "https://www.googleapis.com/auth/userinfo.email", "https://www.googleapis.com/auth/userinfo.profile"],
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True, _scheme="https")
    )
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials
    request_session = google.auth.transport.requests.Request()
    id_info = google.oauth2.id_token.verify_oauth2_token(credentials.id_token, request_session)

    session['username'] = id_info.get("email")
    flash("Login successful via Google!", "success")
    return redirect(url_for('dashboard'))

# ---------------------------
# EXISTING DASHBOARD + REGISTER + UPLOAD + ADMIN ROUTES
# ---------------------------
@app.route('/venus-upload')
def venus_upload_dashboard():
    if not session.get('venus_user'):
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))
    return render_template('Venus_Upload.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('username'):
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['username'])

# (KEEP all your other routes: forgot-password, register, admin-dashboard, upload, etc.)
# ---------------------------

@app.route('/logout')
def logout():
    session.clear()
    resp = make_response(redirect(url_for('login') + '?showSplash=1'))
    resp.set_cookie('username', '', expires=0)
    resp.set_cookie('password', '', expires=0)
    return resp

if __name__ == '__main__':
    from waitress import serve
    port = int(os.environ.get('PORT', 10000))
    serve(app, host='0.0.0.0', port=port)
