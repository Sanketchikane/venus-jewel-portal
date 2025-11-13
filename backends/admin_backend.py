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
    sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    data = sheet.get_all_records()
    approved = [r for r in data if str(r.get("Status", "")).strip().lower() in ["approved", "✅ approved"]]
    return approved

def get_pending_users():
    sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    data = sheet.get_all_records()
    pending = [r for r in data if str(r.get("Status", "")).strip().lower().startswith("pending")]
    return pending

def create_credential_entry(email, username, password):
    reg_sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    cred_sheet = get_gsheet(GOOGLE_SHEET_ID_CREDENTIALS, "Credentials")

    reg_data = reg_sheet.get_all_records()
    header = list(reg_data[0].keys()) if reg_data else []
    status_index = header.index("Status") + 1 if "Status" in header else None

    user_row_index = None
    user_row_data = None

    for i, row in enumerate(reg_data, start=2):
        email_field = str(row.get("Email") or row.get("Email Address") or "").strip().lower()
        if email_field == (email or "").strip().lower():
            user_row_index = i
            user_row_data = row
            break

    if not user_row_index:
        raise Exception(f"User with email '{email}' not found in Registration sheet")

    # Append to Credentials sheet
    cred_sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user_row_data.get("Full Name", ""),
        username,
        password,
        user_row_data.get("Contact") or user_row_data.get("Contact Number", ""),
        user_row_data.get("Organization", "") or user_row_data.get("Organisation", ""),
        email
    ])

    # Update Registration sheet status
    if status_index:
        try:
            reg_sheet.update_cell(user_row_index, status_index, "✅ Approved")
        except Exception as e:
            print("Warning: could not update registration status:", e)

    print(f"✅ User '{username}' approved successfully.")
    return True
