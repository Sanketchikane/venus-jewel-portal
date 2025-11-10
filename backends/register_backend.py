# backends/register_backend.py
from backends.utils_backend import get_registration_sheet, get_credentials_sheet
from datetime import datetime

def submit_registration(form_data):
    ws = get_registration_sheet()
    full_name = form_data.get("full_name", "").strip()
    email = form_data.get("email_address", "").strip()
    contact = form_data.get("contact_number", "").strip()
    org = form_data.get("organization", "").strip()
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ws.append_row([ts, full_name, email, contact, org, "Pending"])
    return True

def get_pending_requests():
    ws = get_registration_sheet()
    records = ws.get_all_records()
    pending = [r for r in records if str(r.get("Status", "")).strip().lower().startswith("pending")]
    return pending

def find_registration_by_email(email):
    ws = get_registration_sheet()
    records = ws.get_all_records()
    email = (email or "").strip().lower()
    for i, row in enumerate(records, start=2):
        possible_email = str(row.get("Email Address") or row.get("Email") or "").strip().lower()
        if possible_email == email:
            return {"row_number": i, "row": row}
    return None

def update_registration_status_by_row(row_number, status):
    ws = get_registration_sheet()
    ws.update_cell(row_number, 6, status)  # Status is column 6
    return True
