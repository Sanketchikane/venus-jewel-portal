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
# APPROVED USERS
# ---------------------------
def get_approved_users():
    sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    data = sheet.get_all_records()

    approved = []
    for r in data:
        status = str(r.get("Status", "")).strip().lower()
        if status not in ["approved", "✅ approved"]:
            continue

        approved.append({
            "Full Name": r.get("Full Name", ""),
            "Username": "",  # Will be filled only after approval
            "Email": r.get("Email Address", ""),
            "Organization": r.get("Organization", ""),
            "Contact": r.get("Contact Number", "")
        })

    return approved


# ---------------------------
# PENDING USERS
# ---------------------------
def get_pending_users():
    sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    data = sheet.get_all_records()

    pending = []
    for r in data:
        status = str(r.get("Status", "")).strip().lower()
        if status.startswith("pending"):
            pending.append({
                "Full Name": r.get("Full Name", ""),
                "Email": r.get("Email Address", ""),
                "Contact": r.get("Contact Number", ""),
                "Organization": r.get("Organization", ""),
                "Status": r.get("Status", "")
            })
    return pending


# ---------------------------
# APPROVE USER
# ---------------------------
def create_credential_entry(email, username, password):
    reg_sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    cred_sheet = get_gsheet(GOOGLE_SHEET_ID_CREDENTIALS, "Credentials")

    reg_data = reg_sheet.get_all_records()

    # Column "Status" is column 6
    status_col = 6

    user_row = None
    row_data = None

    # Match correct column: Email Address
    for i, row in enumerate(reg_data, start=2):
        reg_email = str(row.get("Email Address", "")).strip().lower()
        if reg_email == email.strip().lower():
            user_row = i
            row_data = row
            break

    if not user_row:
        raise Exception(f"User with email '{email}' not found in Registration sheet")

    # Credentials row MUST follow exact order of your sheet:
    cred_sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),   # Timestamp
        row_data.get("Full Name", ""),                  # Full Name
        username,                                       # Username
        password,                                       # Password
        row_data.get("Contact Number", ""),             # Contact Number
        row_data.get("Organization", ""),               # Organization
        email                                           # Email
    ])

    # Update registration status
    try:
        reg_sheet.update_cell(user_row, status_col, "Approved")
    except Exception as e:
        print("Warning: could not update registration status:", e)

    print(f"User '{username}' approved successfully.")
    return True
