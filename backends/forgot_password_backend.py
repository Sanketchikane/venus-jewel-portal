# backends/forgot_password_backend.py
import gspread
from backends.email_service import send_email

SHEET_KEY = "181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro"
CREDS_WS_NAME = "Credentials"

def reset_password_for_username(username, new_password, creds):
    """Reset a user's password by username and email them."""
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_KEY).worksheet(CREDS_WS_NAME)
    records = ws.get_all_records()

    for i, row in enumerate(records, start=2):
        if str(row.get("Username", "")).strip().lower() == username.lower():
            ws.update_cell(i, 4, new_password)  # Assuming Password is column 4
            email = row.get("Email", "")
            full_name = row.get("Full Name", "")

            subject = "Venus Jewel Portal – Password Reset"
            body = (
                f"Dear {full_name},\n\n"
                "Your password has been reset by the administrator.\n\n"
                f"New Password: {new_password}\n\n"
                "You can now log in with this password.\n\n"
                "Best regards,\nVenus Jewel Admin Team"
            )

            if email:
                send_email(email, subject, body)
            return True
    return False
