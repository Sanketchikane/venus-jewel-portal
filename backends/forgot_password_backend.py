from backends.email_service import send_email

ADMIN_EMAIL = "admin@venusjewel.com"

def request_password_reset(form):
    full_name = form.get("full_name")
    username = form.get("username")

    subject = "🔒 Password Reset Request - Venus Jewel File Portal"
    body = f"""
    <h3>Password Reset Request</h3>
    <p><b>User:</b> {full_name} ({username}) has requested a password reset.</p>
    <a href='https://yourdomain.com/admin/reset_password?username={username}'>Reset Password</a>
    """

    send_email(ADMIN_EMAIL, subject, body)
    return True
