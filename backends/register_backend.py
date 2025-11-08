# backends/register_backend.py
import gspread
from datetime import datetime

SHEET_KEY = "181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro"
# Expected worksheet names:
REG_WS_NAME = "Registration"    # where raw registration requests go (tab 1)
CREDS_WS_NAME = "Credentials"   # where approved credentials are stored (tab 2)

def submit_registration(form_data, creds):
    """
    Append a registration request row to the Registration worksheet.
    form_data: a dict-like with full_name, email_address, contact_number, organization
    creds: google service_account.Credentials instance
    """
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_KEY).worksheet(REG_WS_NAME)

    full_name = form_data.get("full_name", "").strip()
    email = form_data.get("email_address", "").strip()
    contact = form_data.get("contact_number", "").strip()
    org = form_data.get("organization", "").strip()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Append row (keeps same column order as you planned)
    ws.append_row([ts, full_name, email, contact, org, "Pending"])
    return True

def get_pending_requests(creds):
    """Return list of pending registration rows as dicts (header-based)."""
    client = gspread.authorize(creds)
    ws = client.open_by_key(SHEET_KEY).worksheet(REG_WS_NAME)
    records = ws.get_all_records()
    pending = [r for r in records if str(r.get("Status", "")).strip().lower() in ("pending", "pending " , "⏳ pending")]
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
