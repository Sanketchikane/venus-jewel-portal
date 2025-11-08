import json, os
from backends.email_service import send_email

DATA_FILE = "data/pending_users.json"
ADMIN_EMAIL = "admin@venusjewel.com"

def handle_registration(form):
    user_data = {
        "full_name": form.get("full_name"),
        "username": form.get("username"),
        "password": form.get("password"),
        "contact_number": form.get("contact_number"),
        "organization": form.get("organization")
    }

    # Save to pending list
    os.makedirs("data", exist_ok=True)
    if not os.path.exists(DATA_FILE):
        json.dump([], open(DATA_FILE, "w"))

    with open(DATA_FILE, "r+") as f:
        users = json.load(f)
        users.append(user_data)
        f.seek(0)
        json.dump(users, f, indent=4)

    # Email to Admin
    subject = "🆕 New Registration Request - Venus Jewel File Portal"
    body = f"""
    <h3>New Registration Request</h3>
    <p><b>Name:</b> {user_data['full_name']}<br>
    <b>Username:</b> {user_data['username']}<br>
    <b>Contact:</b> {user_data['contact_number']}<br>
    <b>Organization:</b> {user_data['organization']}</p>
    <p><a href='https://yourdomain.com/admin/approve?username={user_data['username']}'>
    ✅ Approve User</a></p>
    """
    send_email(ADMIN_EMAIL, subject, body)
    return True
