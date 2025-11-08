# backends/admin_backend.py
import gspread
from datetime import datetime
from backends.email_service import send_email

SHEET_KEY = "181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro"
REG_WS_NAME = "Registration"
CREDS_WS_NAME = "Credentials"

def create_credentials_from_request(reg_email, new_username, new_password, creds):
    """
    Approve a registration by:
     - appending a credentials row to Credentials worksheet
     - updating the Registration sheet status to Approved
     - sending email to user with credentials
    """
    client = gspread.authorize(creds)
    reg_ws = client.open_by_key(SHEET_KEY).worksheet(REG_WS_NAME)
    creds_ws = client.open_by_key(SHEET_KEY).worksheet(CREDS_WS_NAME)

    # Find the registration row
    records = reg_ws.get_all_records()
    reg_email_norm = (reg_email or "").strip().lower()
    for idx, row in enumerate(records, start=2):
        if str(row.get("Email", "")).strip().lower() == reg_email_norm:
            # gather details
            full_name = row.get("Full Name", "")
            contact = row.get("Contact", "")
            org = row.get("Organization", "")
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # Append to Credentials sheet
            # Columns in Credentials sheet: CreatedTimestamp, Full Name, Username, Password, Email, Contact, Organization
            creds_ws.append_row([ts, full_name, new_username, new_password, reg_email, contact, org])
            # Update registration status to Approved (column 6)
            reg_ws.update_cell(idx, 6, "Approved")
            # Send credentials email
            subject = "✅ Your Venus Jewel account is ready"
            body = f"""
            <p>Hi {full_name or ''},</p>
            <p>Your Venus Jewel File Portal account has been created by admin.</p>
            <p><b>Username:</b> {new_username}<br><b>Password:</b> {new_password}</p>
            <p>Please login at <a href="{ 'https://yourdomain.com/login' }">Login</a>.</p>
            <p>— Venus Jewel</p>
            """
            send_email(reg_email, subject, body)
            return True
    return False

def delete_registration_by_email(reg_email, creds):
    client = gspread.authorize(creds)
    reg_ws = client.open_by_key(SHEET_KEY).worksheet(REG_WS_NAME)
    records = reg_ws.get_all_records()
    reg_email_norm = (reg_email or "").strip().lower()
    for idx, row in enumerate(records, start=2):
        if str(row.get("Email", "")).strip().lower() == reg_email_norm:
            reg_ws.delete_rows(idx)
            return True
    return False
