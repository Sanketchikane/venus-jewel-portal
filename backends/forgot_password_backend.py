# backends/forgot_password_backend.py
from backends.email_service import send_email
import gspread

SHEET_KEY = "181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro"
CREDS_WS_NAME = "Credentials"
REG_WS_NAME = "Registration"

def request_password_reset(email, creds):
    """
    Send an email to admin notifying about a password reset request.
    Admin will visit the admin console and set new credentials.
    """
    admin_email = send_email.__defaults__[0] if False else None  # no-op - we will use environment in email_service
    subject = "🔒 Password Reset Requested"
    body = f"""
    <p>Password reset requested for: {email}</p>
    <p>Admin may reset credentials via the admin panel.</p>
    """
    # send to admin address configured in email_service module (SMTP_USER or ADMIN_EMAIL)
    from backends.email_service import ADMIN_EMAIL
    send_email(ADMIN_EMAIL, subject, body)
    return True

def reset_password_for_username(username_or_email, new_password, creds):
    """
    Update password in Credentials worksheet where Username or Email matches.
    """
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_KEY).worksheet(CREDS_WS_NAME)
    records = ws.get_all_records()
    target = (username_or_email or "").strip().lower()
    for idx, row in enumerate(records, start=2):
        username = str(row.get("Username", "")).strip().lower()
        email = str(row.get("Email", "")).strip().lower()
        if target == username or target == email:
            # assuming password is column 4 (A=1)
            ws.update_cell(idx, 4, new_password)
            # optionally inform user
            subject = "🔄 Your password has been reset"
            body = f"<p>Your password is now: <b>{new_password}</b></p><p>Please login at <a href='https://yourdomain.com/login'>Login</a>.</p>"
            send_email(row.get("Email"), subject, body)
            return True
    return False
