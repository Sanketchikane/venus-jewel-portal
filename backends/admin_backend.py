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


# ---------------------------
# GET APPROVED USERS
# ---------------------------
def get_approved_users():
    sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    data = sheet.get_all_records()

    approved = [
        {
            "Full Name": r.get("Full Name", ""),
            "Username": "",
            "Email": r.get("Email Address", ""),
            "Organization": r.get("Organization", ""),
            "Contact Number": r.get("Contact Number", "")
        }
        for r in data
        if str(r.get("Status", "")).strip().lower() in ["approved", "✅ approved"]
    ]

    return approved


# ---------------------------
# GET PENDING USERS
# ---------------------------
def get_pending_users():
    sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    data = sheet.get_all_records()

    pending = [
        {
            "Full Name": r.get("Full Name", ""),
            "Email": r.get("Email Address", ""),
            "Contact": r.get("Contact Number", ""),
            "Organization": r.get("Organization", ""),
            "Status": r.get("Status", "")
        }
        for r in data
        if str(r.get("Status", "")).strip().lower().startswith("pending")
    ]

    return pending


# ---------------------------
# APPROVE USER + CREATE CREDENTIALS ENTRY
# ---------------------------
def create_credential_entry(email, username, password):
    reg_sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    cred_sheet = get_gsheet(GOOGLE_SHEET_ID_CREDENTIALS, "Credentials")

    reg_data = reg_sheet.get_all_records()

    status_index = 6  # Column F = Status

    user_row_index = None
    user_row_data = None

    # Match by Email Address column
    for i, row in enumerate(reg_data, start=2):
        email_cell = str(row.get("Email Address", "")).strip().lower()
        if email_cell == email.strip().lower():
            user_row_index = i
            user_row_data = row
            break

    if not user_row_index:
        raise Exception(f"User with email '{email}' not found in Registration sheet")

    # Append to Credentials sheet → MUST follow your exact sheet order
    cred_sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),  # Timestamp
        user_row_data.get("Full Name", ""),           # Full Name
        username,                                     # Username
        password,                                     # Password
        user_row_data.get("Contact Number", ""),      # Contact Number
        user_row_data.get("Organization", ""),        # Organization
        email                                         # Email
    ])

    # Update status to Approved
    try:
        reg_sheet.update_cell(user_row_index, status_index, "Approved")
    except Exception as e:
        print("Warning: Could not update registration status:", e)

    print(f"✅ User '{username}' approved successfully.")
    return True
