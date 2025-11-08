# backends/register_backend.py
import gspread
from datetime import datetime
from backends.email_service import send_email  # ✅ Added import for email

SHEET_KEY = "181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro"
REG_WS_NAME = "Registration"    # tab 1: raw registration requests
CREDS_WS_NAME = "Credentials"   # tab 2: approved credentials

def submit_registration(form_data, creds):
    """
    Append a registration request row to the Registration worksheet and
    send a confirmation email to the user.
    """
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_KEY).worksheet(REG_WS_NAME)

    full_name = form_data.get("full_name", "").strip()
    email = form_data.get("email_address", "").strip()
    contact = form_data.get("contact_number", "").strip()
    org = form_data.get("organization", "").strip()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Append the registration row
    ws.append_row([ts, full_name, email, contact, org, "Pending"])

    # ✅ Send confirmation email
    if email:
        subject = "Venus Jewel Portal – Registration Received"
        body = (
            f"Dear {full_name},\n\n"
            f"Thank you for registering with Venus Jewel File Portal.\n\n"
            f"Your registration request has been received and is currently pending admin approval.\n"
            f"Once approved, you will receive another email with your login credentials.\n\n"
            f"Best regards,\nVenus Jewel Team"
        )
        send_email(email, subject, body)

    return True

def get_pending_requests(creds):
    """Return list of pending registration rows as dicts (header-based)."""
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_KEY).worksheet(REG_WS_NAME)
    records = ws.get_all_records()
    pending = [
        r for r in records
        if str(r.get("Status", "")).strip().lower() in ("pending", "pending ", "⏳ pending")
    ]
    return pending

def find_registration_by_email(email, creds):
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_KEY).worksheet(REG_WS_NAME)
    records = ws.get_all_records()
    email = (email or "").strip().lower()
    for i, row in enumerate(records, start=2):
        if str(row.get("Email", "")).strip().lower() == email:
            return {"row_number": i, "row": row}
    return None

def update_registration_status_by_row(row_number, status, creds):
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_KEY).worksheet(REG_WS_NAME)
    ws.update_cell(row_number, 6, status)  # assuming Status is column 6 (A=1)
    return True
