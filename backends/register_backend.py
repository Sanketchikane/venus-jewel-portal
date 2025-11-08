import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

def handle_registration(form_data, creds):
    """
    Saves a new registration request to the first Google Sheet tab.
    Only changed input field mappings. Everything else remains untouched.
    """
    client = gspread.authorize(creds)
    sheet = client.open_by_key("181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro").sheet1  # 'Registration Requests' tab

    # ✅ Extract new fields (updated names)
    full_name = form_data.get("full_name", "").strip()
    email = form_data.get("email_address", "").strip()
    contact = form_data.get("contact_number", "").strip()
    organization = form_data.get("organization", "").strip()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # ✅ Write to sheet (kept structure consistent with admin_users.html view)
    sheet.append_row([
        full_name,
        email,
        contact,
        organization,
        "Pending",   # registration status
        timestamp
    ])

    return True
