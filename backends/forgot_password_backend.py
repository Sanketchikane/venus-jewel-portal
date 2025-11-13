# backends/forgot_password_backend.py
from datetime import datetime
from backends.utils_backend import get_registration_sheet, get_credentials_sheet

def submit_forgot_password_request(form_data):
    """
    Store forgot password request in a dedicated sheet tab named
    'Forgot_Password_Requests'. This will create the tab if missing.
    """
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
    Admin-side utility to reset password for a username in Credentials sheet.
    Returns True if updated, False if not found.
    """
    ws = get_credentials_sheet()
    try:
        usernames = ws.col_values(3)[1:]  # column C, skip header
        for i, u in enumerate(usernames, start=2):
            if str(u).strip() == str(username).strip():
                # Password is column index 4 (1-based), that's index 3 in zero-based:
                ws.update_cell(i, 4, new_password)
                return True
        return False
    except Exception as e:
        print("ERROR reset_password_for_username:", e)
        return False
