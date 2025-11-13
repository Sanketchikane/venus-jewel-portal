# backends/forgot_password_backend.py
from backends.utils_backend import get_registration_sheet, get_credentials_sheet
from datetime import datetime
import logging

logger = logging.getLogger("forgot_password_backend")

def submit_forgot_password_request(form_data):
    """Store forgot password request in a dedicated sheet tab."""
    ws = get_registration_sheet("Forgot_Password_Requests")
    data = [
        form_data.get("full_name", ""),
        form_data.get("username", ""),
        form_data.get("email", ""),
        form_data.get("organization", ""),
        form_data.get("contact_number", ""),
        "Pending",
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    ]
    ws.append_row(data)
    return True

def reset_password_for_username(username, new_password):
    """
    Admin-approved direct reset helper used by the web forgot-password flow.
    Finds username in Credentials worksheet and updates the Password column.
    Returns True if updated, False if username not found.
    """
    try:
        ws = get_credentials_sheet()
        usernames = ws.col_values(3)[1:]  # column C values ignoring header
        for i, u in enumerate(usernames, start=2):
            if str(u).strip().lower() == str(username).strip().lower():
                # Password is column 4 (1-based index), update cell
                ws.update_cell(i, 4, new_password)
                return True
        return False
    except Exception as e:
        logger.exception("Error resetting password for %s: %s", username, e)
        raise
