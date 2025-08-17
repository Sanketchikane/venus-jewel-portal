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

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Enforce HTTPS
@app.before_request
def enforce_https_on_render():
    if request.headers.get('X-Forwarded-Proto', 'http') != 'https':
        return redirect(request.url.replace("http://", "https://", 1))

CREDENTIALS_PATH = '/etc/secrets/Credentials.json' if os.environ.get('RENDER') else 'Credentials.json'

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
            if remember:
                response.set_cookie('username', username, max_age=2592000)
                response.set_cookie('password', password, max_age=2592000)
            return redirect(url_for('admin_dashboard'))
        if username == VENUSFILES_USERNAME and password == VENUSFILES_PASSWORD:
            session.update({'username': username, 'venus_user': True})
            if remember:
                response.set_cookie('username', username, max_age=2592000)
                response.set_cookie('password', password, max_age=2592000)
            return redirect(url_for('venus_upload_dashboard'))
        user = get_user(username)
        if user and user['Password'] == password:
            session.update({'username': username, 'admin': False})
            if remember:
                response.set_cookie('username', username, max_age=2592000)
                response.set_cookie('password', password, max_age=2592000)
            return response
        flash('Invalid credentials.', 'danger')
    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        username = request.form['username'].strip()
        new_password = request.form['new_password'].strip()
        confirm_password = request.form['confirm_password'].strip()

        user = get_user(username)
        if not user:
            flash('User not found.', 'danger')
        elif user['Full Name'].lower() != full_name.lower():
            flash('Full name mismatch.', 'danger')
        elif new_password != confirm_password:
            flash('Passwords do not match.', 'danger')
        else:
            sheet.update_cell(user['row_number'], 4, new_password)
            flash('Password updated successfully.', 'success')
            return redirect(url_for('login') + '?showSplash=1')
    return render_template('forgot_password.html')

@app.route('/venus-upload')
def venus_upload_dashboard():
    if not session.get('venus_user'):
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))
    return render_template('Venus_Upload.html')

@app.route('/dashboard')
def dashboard():
    if not session.get('username') or session.get('admin'):
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['username'])

@app.route('/upload', methods=['POST'])
def upload():
    try:
        packet_no = request.form.get('packetNo', '').strip()
        if not packet_no:
            return jsonify({'success': False, 'message': 'Packet number is required.'}), 400

        folder_id = get_or_create_folder(packet_no, DRIVE_FOLDER_ID)

        for key in request.files:
            subpoint = key.replace('file_', '')
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
                        mimetype = file.mimetype

                    file_stream.seek(0)
                    media = MediaIoBaseUpload(file_stream, mimetype=mimetype)
                    drive_service.files().create(
                        body={'name': final_filename, 'parents': [folder_id]},
                        media_body=media,
                        fields='id'
                    ).execute()

        return jsonify({'success': True, 'message': '✅ All files uploaded and muted successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Upload failed: {e}'}), 500

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
        sheet.append_row([timestamp, full_name, username, password, contact, org])
        flash('Registration successful.', 'success')
        return redirect(url_for('login') + '?showSplash=1')
    return render_template('register.html')

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
    headers = records[0]
    users = [dict(zip(headers, row)) for row in records[1:]]
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
    sheet.update_cell(user['row_number'], 4, new_pass)
    flash(f"Password updated for {username}.", 'success')
    return redirect(url_for('view_user', username=username))

@app.route('/admin/venus-files')
def admin_files():
    if not session.get('admin'):
        flash('Admin access only.', 'danger')
        return redirect(url_for('login'))
    return redirect("https://drive.google.com/drive/u/0/folders/1Yjvp5TMg7mERWxq4dsYJq748CcQIucLK")

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

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
