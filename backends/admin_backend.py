# backends/admin_backend.py
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from config import (
    GOOGLE_SHEET_ID_REGISTRATION,
    GOOGLE_SHEET_ID_CREDENTIALS,
    CREDENTIALS_PATH
)

def get_gsheet(sheet_id, tab_name):
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id)
    return sheet.worksheet(tab_name)

def get_approved_users():
    try:
        sheet = get_gsheet(GOOGLE_SHEET_ID_CREDENTIALS, "Credentials")
        data = sheet.get_all_records()
    except Exception as e:
        print("Error reading Credentials sheet:", e)
        return []

    users = []
    for r in data:
        users.append({
            "Full Name": r.get("Full Name", "") or "",
            "Username": r.get("Username", "") or "",
            "Email": r.get("Email", "") or "",
            "Organization": r.get("Organization", "") or "",
            "Contact Number": r.get("Contact Number", "") or ""
        })
    return users

def get_pending_users():
    try:
        sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
        data = sheet.get_all_records()
    except Exception as e:
        print("Error reading Registration sheet:", e)
        return []

    pending = []
    for r in data:
        status = str(r.get("Status", "")).strip().lower()
        if status.startswith("pending"):
            pending.append({
                "Full Name": r.get("Full Name", ""),
                "Email Address": r.get("Email Address", "") or r.get("Email", ""),
                "Contact Number": r.get("Contact Number", "") or r.get("Contact", ""),
                "Organization": r.get("Organization", ""),
                "Status": r.get("Status", "Pending")
            })
    return pending

def create_credential_entry(email, username, password):
    reg_sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    cred_sheet = get_gsheet(GOOGLE_SHEET_ID_CREDENTIALS, "Credentials")

    try:
        reg_data = reg_sheet.get_all_records()
    except Exception as e:
        raise Exception(f"Could not read Registration sheet: {e}")

    # find status column safely
    status_col = None
    try:
        header_row = reg_sheet.row_values(1)
        if "Status" in header_row:
            status_col = header_row.index("Status") + 1
        else:
            status_col = 6
    except Exception:
        status_col = 6

    user_row = None
    row_data = None
    for i, row in enumerate(reg_data, start=2):
        reg_email = str(row.get("Email Address", "") or row.get("Email", "")).strip().lower()
        if reg_email == (email or "").strip().lower():
            user_row = i
            row_data = row
            break

    if not user_row:
        raise Exception(f"User with email '{email}' not found in Registration sheet")

    try:
        cred_sheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            row_data.get("Full Name", "") or "",
            username or "",
            password or "",
            row_data.get("Contact Number", "") or row_data.get("Contact", "") or "",
            row_data.get("Organization", "") or "",
            email or ""
        ])
    except Exception as e:
        raise Exception(f"Could not append to Credentials sheet: {e}")

    try:
        reg_sheet.update_cell(user_row, status_col, "✅ Approved")
    except Exception as e:
        print("Warning: could not update registration status:", e)

    return True
