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
# APPROVED USERS (from Credentials sheet)
# ---------------------------
def get_approved_users():
    """
    Return users from the Credentials sheet (these are approved users).
    The Credentials sheet columns expected:
    [Timestamp, Full Name, Username, Password, Contact Number, Organization, Email]
    """
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


# ---------------------------
# PENDING USERS (from Registration sheet)
# ---------------------------
def get_pending_users():
    """
    Return pending registration rows from Registration sheet. Expected columns:
    [Timestamps, Full Name, Email Address, Contact Number, Organization, Status]
    """
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


# ---------------------------
# APPROVE USER -> Create entry in Credentials sheet & update Registration status
# ---------------------------
def create_credential_entry(email, username, password):
    reg_sheet = get_gsheet(GOOGLE_SHEET_ID_REGISTRATION, "Registration")
    cred_sheet = get_gsheet(GOOGLE_SHEET_ID_CREDENTIALS, "Credentials")

    try:
        reg_data = reg_sheet.get_all_records()
    except Exception as e:
        raise Exception(f"Could not read Registration sheet: {e}")

    # Column "Status" we assume is column 6 (per your sheet layout). We'll attempt safe update.
    status_col = None
    try:
        # find header index for "Status" if possible
        header_row = reg_sheet.row_values(1)
        if "Status" in header_row:
            status_col = header_row.index("Status") + 1
        else:
            # fallback to column 6 (as your sheet layout shows)
            status_col = 6
    except Exception:
        status_col = 6

    user_row = None
    row_data = None

    # Match correct column: Email Address (or Email)
    for i, row in enumerate(reg_data, start=2):
        reg_email = str(row.get("Email Address", "") or row.get("Email", "")).strip().lower()
        if reg_email == (email or "").strip().lower():
            user_row = i
            row_data = row
            break

    if not user_row:
        raise Exception(f"User with email '{email}' not found in Registration sheet")

    # Append to Credentials sheet in the order you use in your sheet:
    # Timestamp | Full Name | Username | Password | Contact Number | Organization | Email
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

    # Update registration status to "✅ Approved" (or "Approved")
    try:
        reg_sheet.update_cell(user_row, status_col, "✅ Approved")
    except Exception as e:
        # non-fatal: log but continue
        print("Warning: could not update registration status:", e)

    return True
