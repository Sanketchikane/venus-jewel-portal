# backends/forgot_password_backend.py
import gspread
from backends.email_service import send_email

SHEET_KEY = "181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro"
CREDS_WS_NAME = "Credentials"

def reset_password_for_username(username, new_password, creds):
    """Reset password and notify user via email."""
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_KEY).worksheet(CREDS_WS_NAME)
    records = ws.get_all_records()

    for i, row in enumerate(records, start=2):
        if str(row.get("Username", "")).strip().lower() == username.lower():
            ws.update_cell(i, 4, new_password)
            email = row.get("Email", "")
            full_name = row.get("Full Name", "")
            subject = "Venus Jewel Portal – Password Reset"
            body = (
                f"Dear {full_name},\n\n"
                "Your password has been reset.\n\n"
                f"New Password: {new_password}\n\n"
                "Login: https://your-venus-file-portal-url/login\n\n"
                "Best regards,\nVenus Jewel Admin Team"
            )
            if email:
                return send_email(email, subject, body)
            return False
    print(f"[FORGOT][WARN] Username not found: {username}")
    return False
