# config.py
import os

# Google / drive / sheets
CREDENTIALS_PATH = '/etc/secrets/Credentials.json' if os.environ.get('RENDER') else os.environ.get('CREDENTIALS_PATH', 'Credentials.json')
SCOPES = ['https://www.googleapis.com/auth/drive', 'https://www.googleapis.com/auth/spreadsheets']
SHEET_ID = os.environ.get('SHEET_ID', '181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro')
DRIVE_FOLDER_ID = os.environ.get('DRIVE_FOLDER_ID', '0AEZXjYA5wFlSUk9PVA')

# Uploads folder
UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'uploads')

# Admin defaults
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'Admin@2211')
VENUSFILES_USERNAME = os.environ.get('VENUSFILES_USERNAME', 'Venusfiles')
VENUSFILES_PASSWORD = os.environ.get('VENUSFILES_PASSWORD', 'Natural@1969')

# Email toggles / SMTP
EMAIL_ENABLED = os.environ.get('EMAIL_ENABLED', 'true').lower() in ('1', 'true', 'yes')
SENDER_EMAIL = os.environ.get('Sender_Email')
SENDER_PASSWORD = os.environ.get('Sender_Password')
SENDER_SMTP = os.environ.get('Sender_SMTP', 'smtp.gmail.com')
SENDER_PORT = os.environ.get('Sender_PORT', '')
SENDER_USE_TLS = os.environ.get('Sender_USE_TLS', 'false').lower() in ('1', 'true', 'yes')
SENDER_CC_ADMIN = os.environ.get('Sender_CC_ADMIN', 'true').lower() in ('1', 'true', 'yes')

# secure share
SECRET_SHARE_KEY = os.environ.get('SECRET_SHARE_KEY', 'venus_secure_share_key_2025').encode()
