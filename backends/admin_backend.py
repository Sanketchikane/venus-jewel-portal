# backends/admin_backend.py
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from config import (
    GOOGLE_SHEET_ID_REGISTRATION,
    GOOGLE_SHEET_ID_CREDENTIALS,
    CREDENTIALS_PATH
)

# -------------------------
# Utility: Connect to Google Sheet
# -------------------------
def get_gsheet(sheet_id, tab_name):
    """Connect safely to a specific Google Sheet tab"""
    scopes = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(CREDENTIALS_PATH, scopes=scopes)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(sheet_id)
    try:
        return sheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        # Create the worksheet if it doesn't exist
        sheet.add_worksheet(title=tab_name, rows="1000", cols="20")
        return sheet.worksheet(tab_name)


# -------------------------
# Fetch Approved Users
# -------------------------
def get_approved_users():
    """Return all approved users from the Registration sheet"""
    sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    data = sheet.get_all_records()
    approved = [r for r in data if str(r.get("Status", "")).strip().lower() in ["approved", "✅ approved"]]
    return approved


# -------------------------
# Fetch Pending Users
# -------------------------
def get_pending_users():
    """Return all pending users awaiting admin approval"""
    sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    data = sheet.get_all_records()
    pending = [r for r in data if str(r.get("Status", "")).strip().lower() == "pending"]
    return pending


# -------------------------
# Approve a User + Create Credential Entry
# -------------------------
def create_credential_entry(email, username, password):
    """
    Moves a pending registration to Approved and creates an entry
    in the Credentials sheet for login access.
    """
    reg_sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    cred_sheet = get_gsheet(GOOGLE_SHEET_ID_CREDENTIALS, "Credentials")

    reg_data = reg_sheet.get_all_records()
    if not reg_data:
        raise Exception("No data found in Registration sheet")

    header = list(reg_data[0].keys())
    status_index = header.index("Status") + 1 if "Status" in header else None

    user_row_index = None
    user_row_data = None

    # Normalize keys (for column names that vary: Email, Email Address)
    for i, row in enumerate(reg_data, start=2):
        row_email = row.get("Email") or row.get("Email Address") or ""
        if row_email.strip().lower() == email.strip().lower():
            user_row_index = i
            user_row_data = row
            break

    if not user_row_index:
        raise Exception(f"User with email '{email}' not found in Registration sheet")

    # Create row in Credentials sheet
    cred_sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        user_row_data.get("Full Name", ""),
        username,
        password,
        user_row_data.get("Contact Number") or user_row_data.get("Contact", ""),
        user_row_data.get("Organization") or user_row_data.get("Organisation", ""),
        email,
        "Active"
    ])

    # Update status in Registration sheet
    if status_index:
        reg_sheet.update_cell(user_row_index, status_index, "✅ Approved")

    print(f"User '{username}' approved successfully and added to Credentials sheet.")
    return True
