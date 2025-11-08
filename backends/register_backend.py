import gspread
from datetime import datetime
from backends.email_service import send_email

SHEET_ID = "181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro"
ADMIN_EMAIL = "admin@venusjewel.com"

def handle_registration(form, creds):
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1  # assuming single sheet

    full_name = form.get("full_name")
    username = form.get("username")
    password = form.get("password")
    contact = form.get("contact_number")
    org = form.get("organization")

    # Save to Sheet
    sheet.append_row([
        full_name, username, password, contact, org, "⏳ Pending", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ])

    # Send mail to Admin
    subject = f"🆕 New Registration Request - {full_name}"
    body = f"""
    <h3>New Registration Request</h3>
    <p><b>Name:</b> {full_name}<br>
    <b>Username:</b> {username}<br>
    <b>Contact:</b> {contact}<br>
    <b>Organization:</b> {org}</p>
    <p><a href='https://yourdomain.com/admin/approve?username={username}'>
    ✅ Approve User</a></p>
    """

    send_email(ADMIN_EMAIL, subject, body)
    return True
