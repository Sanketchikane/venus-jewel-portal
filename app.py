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

# ✅ HTTPS handling for Render (to prevent redirect loop)
@app.before_request
def enforce_https_on_render():
    if request.headers.get('X-Forwarded-Proto', 'http') != 'https':
        url = request.url.replace("http://", "https://", 1)
        return redirect(url)

# Unified credentials path for both Sheets and Drive
CREDENTIALS_PATH = '/etc/secrets/Credentials.json' if os.environ.get('RENDER') else 'Credentials.json'

# Google Sheets setup
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
client = gspread.authorize(creds)

SHEET_ID = '19c2tlUmzSQsQhqNvWRuKMgdw86M0PLsKrWk51m7apA4'
spreadsheet = client.open_by_key(SHEET_ID)
sheet = spreadsheet.worksheet('Sheet1')

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ADMIN_USERNAME = 'admin'
ADMIN_PASSWORD = 'Admin@123'
VENUSFILES_USERNAME = 'Venusfiles'
VENUSFILES_PASSWORD = 'Natural1969'

# Google Drive setup
DRIVE_FOLDER_ID = '1Yjvp5TMg7mERWxq4dsYJq748CcQIucLK'
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']
drive_creds = service_account.Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=DRIVE_SCOPES)
drive_service = build('drive', 'v3', credentials=drive_creds)


def username_exists(username):
    usernames = sheet.col_values(3)
    return username in usernames[1:]


def get_user(username):
    usernames = sheet.col_values(3)
    for i, u in enumerate(usernames[1:], start=2):
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
    items = results.get('files', [])
    if items:
        return items[0]['id']
    file_metadata = {
        'name': name,
        'mimeType': 'application/vnd.google-apps.folder',
        'parents': [parent_id]
    }
    folder = drive_service.files().create(body=file_metadata, fields='id').execute()
    return folder.get('id')


def mute_video(file_storage, filename):
    ext = os.path.splitext(filename)[1]
    temp_dir = tempfile.mkdtemp()
    input_path = os.path.join(temp_dir, f"input{ext}")
    output_path = os.path.join(temp_dir, f"muted{ext}")
    file_storage.save(input_path)

    try:
        subprocess.run(['ffmpeg', '-i', input_path, '-c:v', 'copy', '-an', output_path], check=True)
        with open(output_path, 'rb') as f:
            return io.BytesIO(f.read())
    except Exception as e:
        print(f"[FFMPEG ERROR] {filename}: {e}")
        with open(input_path, 'rb') as f:
            return io.BytesIO(f.read())


@app.route('/')
def home():
    username = request.cookies.get('username')
    password = request.cookies.get('password')
    if username and password:
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['username'] = username
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        elif username == VENUSFILES_USERNAME and password == VENUSFILES_PASSWORD:
            session['username'] = username
            session['venus_user'] = True
            return redirect(url_for('venus_upload_dashboard'))
        else:
            user = get_user(username)
            if user and user['Password'] == password:
                session['username'] = username
                session['admin'] = False
                return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        remember = request.form.get('remember')

        response = make_response(redirect(url_for('dashboard')))

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['username'] = username
            session['admin'] = True
            if remember:
                response.set_cookie('username', username, max_age=60 * 60 * 24 * 30)
                response.set_cookie('password', password, max_age=60 * 60 * 24 * 30)
            return redirect(url_for('admin_dashboard'))

        if username == VENUSFILES_USERNAME and password == VENUSFILES_PASSWORD:
            session['username'] = username
            session['venus_user'] = True
            if remember:
                response.set_cookie('username', username, max_age=60 * 60 * 24 * 30)
                response.set_cookie('password', password, max_age=60 * 60 * 24 * 30)
            return redirect(url_for('venus_upload_dashboard'))

        user = get_user(username)
        if user and user['Password'] == password:
            session['username'] = username
            session['admin'] = False
            if remember:
                response.set_cookie('username', username, max_age=60 * 60 * 24 * 30)
                response.set_cookie('password', password, max_age=60 * 60 * 24 * 30)
            return response

        flash('Invalid credentials.', 'danger')
    return render_template('login.html')


@app.route('/venus-upload')
def venus_upload_dashboard():
    if 'username' not in session or not session.get('venus_user'):
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))
    return render_template('Venus_Upload.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        full_name = request.form['full_name'].strip()
        username = request.form['username'].strip()
        password = request.form['password'].strip()
        contact_number = request.form['contact_number'].strip()
        organization = request.form['organization'].strip()

        if username_exists(username):
            flash('Username already exists. Please choose another.', 'danger')
            return render_template('register.html')

        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sheet.append_row([timestamp, full_name, username, password, contact_number, organization])
        flash('Registration successful. Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    if 'username' not in session or session.get('admin'):
        flash('Access denied.', 'danger')
        return redirect(url_for('login'))
    return render_template('dashboard.html', user=session['username'])


@app.route('/upload', methods=['POST'])
def upload():
    try:
        packet_no = request.form.get('packetNo', '').strip()
        if not packet_no:
            return jsonify({'success': False, 'message': 'Packet number is required.'}), 400

        packet_folder_id = get_or_create_folder(packet_no, DRIVE_FOLDER_ID)

        for key in request.files:
            files = request.files.getlist(key)
            subpoint = key.replace('file_', '')
            for file in files:
                if file and file.filename:
                    ext = os.path.splitext(file.filename)[1]
                    filename = f"{subpoint}{ext}"

                    if filename.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.webm')):
                        file_stream = mute_video(file, filename)
                        mimetype = 'video/mp4'
                    else:
                        file_stream = io.BytesIO(file.read())
                        mimetype = file.mimetype

                    file_stream.seek(0)
                    media = MediaIoBaseUpload(file_stream, mimetype=mimetype)
                    drive_service.files().create(
                        body={'name': filename, 'parents': [packet_folder_id]},
                        media_body=media,
                        fields='id'
                    ).execute()

        return jsonify({'success': True, 'message': '✅ All files uploaded and muted successfully.'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'Upload failed: {e}'}), 500


@app.route('/admin-dashboard')
def admin_dashboard():
    if 'username' not in session or not session.get('admin'):
        flash('Admin access only.', 'danger')
        return redirect(url_for('login'))
    return render_template('admin_dashboard.html', user=session['username'])


@app.route('/admin/users')
def admin_users():
    if 'username' not in session or not session.get('admin'):
        flash('Admin access only.', 'danger')
        return redirect(url_for('login'))
    all_records = sheet.get_all_values()
    headers = all_records[0]
    users = [dict(zip(headers, row)) for row in all_records[1:]]
    return render_template('admin_users.html', users=users)


@app.route('/admin/venus-files')
def admin_files():
    if 'username' not in session or not session.get('admin'):
        flash('Admin access only.', 'danger')
        return redirect(url_for('login'))
    return redirect("https://drive.google.com/drive/u/0/folders/1Yjvp5TMg7mERWxq4dsYJq748CcQIucLK")


@app.route('/admin/user/<username>')
def view_user(username):
    if 'username' not in session or not session.get('admin'):
        flash('Admin access only.', 'danger')
        return redirect(url_for('admin_users'))
    user = get_user(username)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_users'))
    files = [f for f in os.listdir(UPLOAD_FOLDER) if username in f]
    return render_template('user_profile.html', user=user, files=files)


@app.route('/admin/user/<username>/change-password', methods=['POST'])
def change_user_password(username):
    if 'username' not in session or not session.get('admin'):
        flash('Admin access only.', 'danger')
        return redirect(url_for('admin_users'))
    new_password = request.form['new_password']
    user = get_user(username)
    if not user:
        flash('User not found.', 'danger')
        return redirect(url_for('admin_users'))
    row_number = user['row_number']
    sheet.update_cell(row_number, 4, new_password)
    flash(f"Password updated for {username}.", 'success')
    return redirect(url_for('view_user', username=username))


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/logout')
def logout():
    session.clear()
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('username', '', expires=0)
    resp.set_cookie('password', '', expires=0)
    return resp


if __name__ == '__main__':
    from waitress import serve
    import os

    port = int(os.environ.get('PORT', 10000))
    serve(app, host='0.0.0.0', port=port)
