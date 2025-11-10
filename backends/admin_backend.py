# backends/admin_backend.py
import gspread
from datetime import datetime
from backends.email_service import send_email
from backends.register_backend import find_registration_by_email, update_registration_status_by_row

SHEET_KEY = "181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro"
CREDS_WS_NAME = "Credentials"

def create_credentials_from_request(email, username, password, creds):
    """Approve user, add credentials, update status, and send email."""
    try:
        client = gspread.authorize(creds)
        reg_entry = find_registration_by_email(email, creds)

        if not reg_entry:
            print(f"[ADMIN][ERROR] No registration found for {email}")
            return False

        row_data = reg_entry["row"]
        row_num = reg_entry["row_number"]

        full_name = row_data.get("Full Name", "")
        email_field = row_data.get("Email Address") or row_data.get("Email") or email
        contact = row_data.get("Contact Number", "")
        org = row_data.get("Organization", "")

        creds_ws = client.open_by_key(SHEET_KEY).worksheet(CREDS_WS_NAME)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        creds_ws.append_row([ts, full_name, username, password, contact, org, email_field])
        update_registration_status_by_row(row_num, "✅ Approved", creds)

        subject = "Venus Jewel Portal – Your Account Has Been Approved"
        body = (
            f"Dear {full_name or 'User'},\n\n"
            "Your Venus Jewel File Portal account has been approved.\n\n"
            f"Username: {username}\nPassword: {password}\n\n"
            "Login: https://your-venus-file-portal-url/login\n\n"
            "Best regards,\nVenus Jewel Admin Team"
        )

        print(f"[ADMIN][INFO] Sending email to {email_field}")
        sent = send_email(email_field, subject, body)
        if sent:
            print(f"[ADMIN][OK] Email sent to {email_field}")
        else:
            print(f"[ADMIN][WARN] Email failed for {email_field}")
        return sent

    except Exception as e:
        print(f"[ADMIN][ERROR] {e}")
        return False
