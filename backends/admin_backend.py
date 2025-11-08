import gspread
from backends.email_service import send_email
from datetime import datetime

SHEET_ID = "181GnSNYNBciNNUlWLXsIYNZ5qsxpDkIftfBzHrycHro"

def approve_user(username, creds):
    client = gspread.authorize(creds)
    sheet = client.open_by_key(SHEET_ID).sheet1
    records = sheet.get_all_records()

    for idx, row in enumerate(records, start=2):  # row 1 = header
        if str(row.get("Username")).strip().lower() == username.strip().lower():
            # Update status in sheet
            sheet.update_cell(idx, 6, "✅ Approved")  # Status column
            sheet.update_cell(idx, 7, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

            # Send user email
            subject = "✅ Account Approved - Venus Jewel File Portal"
            body = f"""
            <h3>Welcome, {row.get('Full Name')}</h3>
            <p>Your Venus Jewel File Portal account is approved.</p>
            <p><b>Username:</b> {row.get('Username')}<br>
            <b>Password:</b> {row.get('Password')}</p>
            <a href='https://yourdomain.com/login'>Login Now</a>
            """
            send_email(row.get("Username"), subject, body)
            return True
    return False
