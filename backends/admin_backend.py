# backends/admin_backend.py
import gspread
from datetime import datetime
from backends.email_service import send_email
from backends.register_backend import find_registration_by_email, update_registration_status_by_row

SHEET_KEY = "181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro"
REG_WS_NAME = "Registration"
CREDS_WS_NAME = "Credentials"

def create_credentials_from_request(email, username, password, creds):
    """Approve a pending user and send credentials via email"""
    client = gspread.authorize(creds)
    reg_entry = find_registration_by_email(email, creds)
    if not reg_entry:
        print(f"[ERROR] No registration found for {email}")
        return False

    row_data = reg_entry["row"]
    row_num = reg_entry["row_number"]

    full_name = row_data.get("Full Name", "")
    email_field = row_data.get("Email Address") or row_data.get("Email") or email
    contact = row_data.get("Contact Number", "")
    org = row_data.get("Organization", "")

    creds_ws = client.open_by_key(SHEET_KEY).worksheet(CREDS_WS_NAME)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    creds_ws.append_row([ts, full_name, username, password, contact, org, email_field])

    update_registration_status_by_row(row_num, "✅ Approved", creds)

    subject = "Venus Jewel Portal – Your Account Has Been Approved"
    body = (
        f"Dear {full_name},\n\n"
        f"Your Venus Jewel File Portal account has been approved.\n\n"
        f"Login details:\n"
        f"Username: {username}\n"
        f"Password: {password}\n\n"
        "You can log in here:\nhttps://your-venus-file-portal-url\n\n"
        "Best regards,\nVenus Jewel Admin Team"
    )

    print(f"[INFO] Sending approval email to {email_field}")
    return send_email(email_field, subject, body)
