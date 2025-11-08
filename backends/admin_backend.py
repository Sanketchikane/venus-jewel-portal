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
    Approve pending registration → Add to 'Credentials' sheet → Email credentials to user.
    """
    if not email:
        print("[ERROR] Missing email parameter.")
        return False

    client = gspread.authorize(creds)
    reg_entry = find_registration_by_email(email, creds)
    if not reg_entry:
        print(f"[ERROR] No registration found for {email}")
        return False

    row_data = reg_entry["row"]
    row_num = reg_entry["row_number"]

    # Extract fields safely
    full_name = (
        row_data.get("Full Name") or row_data.get("Name") or ""
    )
    email_field = (
        row_data.get("Email") or row_data.get("Email Address") or row_data.get("E-mail") or email
    )
    contact = (
        row_data.get("Contact Number") or row_data.get("Contact") or ""
    )
    org = (
        row_data.get("Organization") or row_data.get("Company") or ""
    )

    # Update Credentials Sheet
    creds_ws = client.open_by_key(SHEET_KEY).worksheet(CREDS_WS_NAME)
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    creds_ws.append_row([ts, full_name, username, password, contact, org, email_field])

    # Update Registration status
    update_registration_status_by_row(row_num, "✅ Approved", creds)

    # Send email to user
    subject = "Venus Jewel Portal – Account Approved"
    body = (
        f"Dear {full_name},\n\n"
        "Your Venus Jewel File Portal registration has been approved.\n\n"
        f"Login details:\n"
        f"Username: {username}\n"
        f"Password: {password}\n\n"
        "Login here: https://your-venus-file-portal-url\n\n"
        "Keep your credentials safe.\n\n"
        "Best Regards,\nVenus Jewel Admin Team"
    )

    return send_email(email_field, subject, body)
