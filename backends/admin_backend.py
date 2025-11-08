import gspread
from datetime import datetime
from google.oauth2 import service_account
from backends.email_service import send_email_notification

# Google Sheet ID (same as app.py)
SHEET_ID = "181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro"

def create_credentials_from_request(email, username, password, creds):
    """
    Creates credentials for a user whose email exists in Registration sheet.
    Writes to 'Credentials' sheet and marks the request as approved.
    Sends login details via email.
    """
    try:
        client = gspread.authorize(creds)
        reg_ws = client.open_by_key(SHEET_ID).worksheet("Registration")
        cred_ws = client.open_by_key(SHEET_ID).worksheet("Credentials")

        records = reg_ws.get_all_records()
        target_row = None
        reg_data = None

        for i, row in enumerate(records, start=2):  # skip header
            if str(row.get("Email", "")).strip().lower() == email.strip().lower():
                target_row = i
                reg_data = row
                break

        if not reg_data:
            print(f"[WARN] No registration found for email: {email}")
            return False

        # Prepare row for Credentials sheet
        row_to_insert = [
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            reg_data.get("Full Name", ""),
            username,
            password,
            reg_data.get("Contact Number", ""),
            reg_data.get("Organization", ""),
            email
        ]

        cred_ws.append_row(row_to_insert)

        # Mark registration as Approved
        reg_ws.update_cell(target_row, 6, "Approved")

        # Email user
        subject = "✅ Venus Jewel File Portal Credentials Approved"
        message = f"""
Dear {reg_data.get('Full Name', '')},

Your registration for the Venus Jewel File Portal has been approved.

Here are your login credentials:

🔹 Username: {username}
🔹 Password: {password}

Please log in at:
https://venus-file-portal.onrender.com/login

Thank you,
Venus Jewel Admin Team
"""
        send_email_notification(email, subject, message)
        print(f"[INFO] Credentials created and emailed to {email}")
        return True

    except Exception as e:
        print(f"[ERROR] create_credentials_from_request: {e}")
        return False
