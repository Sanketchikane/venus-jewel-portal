# config.py
import os

# === Google Drive & Sheets Configuration ===
CREDENTIALS_PATH = '/etc/secrets/Credentials.json' if os.environ.get('RENDER') else os.environ.get('CREDENTIALS_PATH', 'Credentials.json')
SCOPES = [
    'https://www.googleapis.com/auth/drive',
    'https://www.googleapis.com/auth/spreadsheets'
]

# === Main Google Sheets ===
# Same main sheet used for Registration and Credentials
GOOGLE_SHEET_ID_REGISTRATION = os.environ.get('GOOGLE_SHEET_ID_REGISTRATION', '181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro')
GOOGLE_SHEET_ID_CREDENTIALS = os.environ.get('GOOGLE_SHEET_ID_CREDENTIALS', '181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro')

# ✅ Added Forgot Password Request Sheet (New)
GOOGLE_SHEET_ID_FORGOT_PASSWORD = os.environ.get('GOOGLE_SHEET_ID_FORGOT_PASSWORD', '181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro')
# (If using same file, this will simply create/use a tab named "Forgot_Password_Requests")

# ✅ Add backward compatibility for utils_backend.py (older versions)
SHEET_ID = GOOGLE_SHEET_ID_CREDENTIALS

# Default shared Google Drive parent folder
DRIVE_FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID', '0AEZXjYA5wFlSUk9PVA')

# Local upload folder (for temporary processing)
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')

# === Admin Defaults ===
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Admin@2211')
VENUSFILES_USERNAME = os.environ.get('VENUSFILES_USERNAME', 'Venusfiles')
VENUSFILES_PASSWORD = os.environ.get('VENUSFILES_PASSWORD', 'Natural@1969')

# === Email (disabled or optional) ===
EMAIL_ENABLED = os.environ.get('EMAIL_ENABLED', 'false').lower() in ('1', 'true', 'yes')
SENDER_EMAIL = os.environ.get('Sender_Email')
SENDER_PASSWORD = os.environ.get('Sender_Password')
SENDER_SMTP = os.environ.get('Sender_SMTP', 'smtp.gmail.com')
SENDER_PORT = os.environ.get('Sender_PORT', '')
SENDER_USE_TLS = os.environ.get('Sender_USE_TLS', 'false').lower() in ('1', 'true', 'yes')
SENDER_CC_ADMIN = os.environ.get('Sender_CC_ADMIN', 'true').lower() in ('1', 'true', 'yes')

# === Secure Share Key ===
SECRET_SHARE_KEY = os.environ.get('SECRET_SHARE_KEY', 'venus_secure_share_key_2025').encode()
