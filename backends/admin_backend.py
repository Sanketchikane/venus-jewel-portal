# backends/admin_backend.py
from datetime import datetime
from backends.register_backend import find_registration_by_email, update_registration_status_by_row
from backends.utils_backend import get_credentials_sheet
import backends.email_service as email_service
import config

def create_credentials_from_request(email, username, password):
    try:
        reg_entry = find_registration_by_email(email)
        if not reg_entry:
            print(f"[ERROR] No registration found for {email}")
            return False

        row = reg_entry["row"]
        row_num = reg_entry["row_number"]
        full_name = row.get("Full Name", "")
        email_field = row.get("Email Address") or row.get("Email") or email
        contact = row.get("Contact Number", "") or row.get("Contact", "")
        org = row.get("Organisation", "") or row.get("Organization", "")

        ws = get_credentials_sheet()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ws.append_row([ts, full_name, username, password, contact, org, email_field])

        update_registration_status_by_row(row_num, "✅ Approved")

        # send email if enabled
        subject = "Venus Jewel Portal – Your Account Has Been Approved"
        body = (
            f"Dear {full_name or 'User'},\n\n"
            "Your Venus Jewel File Portal account has been approved.\n\n"
            f"Login details:\nUsername: {username}\nPassword: {password}\n\n"
            "You can log in here:\nhttps://your-venus-file-portal-url/login\n\n"
            "Best regards,\nVenus Jewel Admin Team"
        )

        if config.EMAIL_ENABLED:
            sent = email_service.send_email(email_field, subject, body)
            if not sent:
                print(f"[WARN] Email not sent to {email_field}")
                # still consider process successful (admin may want to retry)
                return False

        return True
    except Exception as e:
        print(f"[ERROR] create_credentials_from_request: {e}")
        return False
