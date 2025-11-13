# backends/forgot_password_backend.py
from backends.utils_backend import get_registration_sheet
from datetime import datetime

def submit_forgot_password_request(form_data):
    """
    Store forgot password request in the 'Forgot_Password_Requests' tab.
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
