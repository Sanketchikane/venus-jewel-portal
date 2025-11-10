import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

from config import (
    GOOGLE_SHEET_ID_REGISTRATION,
    GOOGLE_SHEET_ID_CREDENTIALS
)

def get_gsheet(sheet_id, tab_name):
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file("credentials.json", scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id)
    return sheet.worksheet(tab_name)

def get_approved_users():
    sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    data = sheet.get_all_records()
    return [r for r in data if str(r.get("Status")).strip() == "✅ Approved"]

def get_pending_users():
    sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    data = sheet.get_all_records()
    return [r for r in data if str(r.get("Status")).strip().lower() == "pending"]

def create_credential_entry(email, username, password):
    """Adds approved user to Credentials tab & marks as Approved in Registration tab."""
    reg_sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    cred_sheet = get_gsheet(GOOGLE_SHEET_ID_CREDENTIALS, "Credentials")

    reg_data = reg_sheet.get_all_records()
    row_index = None
    user_row = None

    for i, row in enumerate(reg_data, start=2):  # row 2 because row 1 is headers
        if str(row.get("Email Address")).strip().lower() == email.strip().lower():
            row_index = i
            user_row = row
            break

    if not row_index:
        raise Exception("User not found in Registration tab")

    # Add to Credentials tab
    cred_sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user_row.get("Full Name"),
        username,
        password,
        user_row.get("Contact Number"),
        user_row.get("Organisation"),
        email
    ])

    # Update Registration status to Approved
    reg_sheet.update_cell(row_index, list(reg_data[0].keys()).index("Status") + 1, "✅ Approved")
