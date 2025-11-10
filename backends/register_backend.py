# backends/register_backend.py
import gspread
from datetime import datetime

SHEET_KEY = "181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro"
REG_WS_NAME = "Registration"
CREDS_WS_NAME = "Credentials"

def submit_registration(form_data, creds):
    """Append registration row to Registration sheet"""
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_KEY).worksheet(REG_WS_NAME)

    full_name = form_data.get("full_name", "").strip()
    email = form_data.get("email_address", "").strip()
    contact = form_data.get("contact_number", "").strip()
    org = form_data.get("organization", "").strip()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    ws.append_row([ts, full_name, email, contact, org, "Pending"])
    return True


def get_pending_requests(creds):
    """Return only pending registration rows."""
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_KEY).worksheet(REG_WS_NAME)
    records = ws.get_all_records()
    pending = [
        r for r in records
        if str(r.get("Status", "")).strip().lower().startswith("pending")
    ]
    return pending


def find_registration_by_email(email, creds):
    """
    Find a specific pending registration row for a given email.
    Prioritize 'Pending' rows to avoid overwriting old ones.
    """
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_KEY).worksheet(REG_WS_NAME)
    records = ws.get_all_records()
    email = (email or "").strip().lower()
    match = None
    for i, row in enumerate(records, start=2):
        possible_email = str(row.get("Email") or row.get("Email Address") or "").strip().lower()
        status = str(row.get("Status", "")).strip().lower()
        if possible_email == email and status.startswith("pending"):
            match = {"row_number": i, "row": row}
            break
    # if no pending match, return the latest occurrence (for safety)
    if not match:
        for i, row in enumerate(reversed(records), start=2):
            possible_email = str(row.get("Email") or row.get("Email Address") or "").strip().lower()
            if possible_email == email:
                match = {"row_number": len(records) - i + 2, "row": row}
                break
    return match


def update_registration_status_by_row(row_number, status, creds):
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_KEY).worksheet(REG_WS_NAME)
    ws.update_cell(row_number, 6, status)
    return True
