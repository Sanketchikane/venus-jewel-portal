# backends/admin_backend.py
import gspread
from datetime import datetime
from backends.email_service import send_email
from backends.register_backend import find_registration_by_email, update_registration_status_by_row

SHEET_KEY = "181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro"
REG_WS_NAME = "Registration"
CREDS_WS_NAME = "Credentials"

def create_credentials_from_request(email, username, password, creds):
    """
    Move a registration from 'Registration' to 'Credentials' after admin approval.
    Updates both sheets and emails the user their credentials.
    """
    client = gspread.authorize(creds)

    # Find registration record
    reg_entry = find_registration_by_email(email, creds)
    if not reg_entry:
        print(f"[ERROR] Registration not found for {email}")
        return False

    row_data = reg_entry["row"]
    row_num = reg_entry["row_number"]

    full_name = row_data.get("Full Name", "")
    contact = row_data.get("Contact", "")
    org = row_data.get("Organization", "")

    # Write credentials to the 'Credentials' sheet
    creds_ws = client.open_by_key(SHEET_KEY).worksheet(CREDS_WS_NAME)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    creds_ws.append_row([ts, full_name, username, password, contact, org, email])

    # Update registration status
    update_registration_status_by_row(row_num, "✅ Approved", creds)

    # Send credentials email
    subject = "Venus Jewel Portal – Account Approved"
    body = (
        f"Dear {full_name},\n\n"
        "Your Venus Jewel File Portal registration has been approved.\n\n"
        f"Here are your login credentials:\n"
        f"Username: {username}\n"
        f"Password: {password}\n\n"
        "You can now log in at: https://your-venus-file-portal-url\n\n"
        "Please keep your credentials secure.\n\n"
        "Best regards,\nVenus Jewel Admin Team"
    )
    return send_email(email, subject, body)
