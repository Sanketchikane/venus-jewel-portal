import json, os
from backends.email_service import send_email

PENDING_FILE = "data/pending_users.json"
REGISTERED_FILE = "data/registered_users.json"

def load_json(path):
    if os.path.exists(path):
        return json.load(open(path))
    return []

def save_json(path, data):
    json.dump(data, open(path, "w"), indent=4)

def approve_user(username):
    pending = load_json(PENDING_FILE)
    registered = load_json(REGISTERED_FILE)
    
    user = next((u for u in pending if u["username"] == username), None)
    if not user:
        return False

    pending = [u for u in pending if u["username"] != username]
    registered.append(user)
    
    save_json(PENDING_FILE, pending)
    save_json(REGISTERED_FILE, registered)

    subject = "✅ Account Approved - Venus Jewel File Portal"
    body = f"""
    <h3>Welcome, {user['full_name']}</h3>
    <p>Your Venus Jewel File Portal account is ready.</p>
    <p><b>Username:</b> {user['username']}<br>
    <b>Password:</b> {user['password']}</p>
    <a href='https://yourdomain.com/login'>Login Now</a>
    """
    send_email(user["username"], subject, body)
    return True
