# backends/forgot_password_backend.py
from backends.utils_backend import get_credentials_sheet
import backends.email_service as email_service
import config

def reset_password_for_username(username, new_password):
    ws = get_credentials_sheet()
    records = ws.get_all_records()
    for i, row in enumerate(records, start=2):
        if str(row.get("Username", "")).strip().lower() == username.lower():
            ws.update_cell(i, 4, new_password)  # Password is column 4
            email = row.get("Email", "")
            full_name = row.get("Full Name", "")
            subject = "Venus Jewel Portal – Password Reset"
            body = (
                f"Dear {full_name},\n\nYour password has been reset by the administrator.\n\n"
                f"New Password: {new_password}\n\nYou can now log in with this password.\n\nBest regards,\nVenus Jewel Admin Team"
            )
            if config.EMAIL_ENABLED and email:
                return email_service.send_email(email, subject, body)
            return True
    return False
