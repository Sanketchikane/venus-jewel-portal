# backends/email_service.py
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Configure via environment variables in Render/your host, or defaults here for local testing.
SMTP_SERVER = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("EMAIL_PORT", 587))
SMTP_USER = os.environ.get("EMAIL_USER", "admin@venusjewel.com")
SMTP_PASS = os.environ.get("EMAIL_PASS", "")  # set secure app password / smtp password

ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", SMTP_USER)

def send_email(to_email, subject, html_body, text_body=None):
    """Send an HTML email. Returns True on success, False otherwise."""
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = SMTP_USER
        msg["To"] = to_email
        msg["Subject"] = subject

        if text_body is None:
            text_body = "".join(html_body.split("<")[0:1]) if html_body else ""

        part1 = MIMEText(text_body, "plain")
        part2 = MIMEText(html_body, "html")
        msg.attach(part1)
        msg.attach(part2)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [to_email], msg.as_string())
        server.quit()
        return True
    except Exception as e:
        # do not raise — caller can log
        print(f"[WARN] send_email failed: {e}")
        return False
