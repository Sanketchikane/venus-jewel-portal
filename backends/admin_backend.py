import gspread
from datetime import datetime
from backends.register_backend import find_registration_by_email, update_registration_status_by_row

SHEET_KEY = "181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro"
REG_WS_NAME = "Registration"
CREDS_WS_NAME = "Credentials"


def create_credentials_from_request(email, username, password, creds):
    """Approve a pending user and update both sheets. (No email sent)"""
    try:
        client = gspread.authorize(creds)
        reg_entry = find_registration_by_email(email, creds)

        if not reg_entry:
            print(f"[ERROR] No registration found for {email}")
            return False

        row_data = reg_entry["row"]
        row_num = reg_entry["row_number"]

        full_name = row_data.get("Full Name", "")
        email_field = row_data.get("Email Address") or row_data.get("Email") or email
        contact = row_data.get("Contact Number", "")
        org = row_data.get("Organization", "")

        creds_ws = client.open_by_key(SHEET_KEY).worksheet(CREDS_WS_NAME)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # ✅ Add user to Credentials sheet
        creds_ws.append_row([ts, full_name, username, password, contact, org, email_field])

        # ✅ Update Registration sheet to Approved
        update_registration_status_by_row(row_num, "✅ Approved", creds)

        print(f"[INFO] User {full_name} ({email_field}) approved successfully.")
        return True
    except Exception as e:
        print(f"[ERROR] create_credentials_from_request: {e}")
        return False
