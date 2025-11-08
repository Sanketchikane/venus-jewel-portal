import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ✅ Gmail / Google Workspace SMTP Configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ✅ Read from Render environment variables
SENDER_EMAIL = os.environ.get("Sender_Email", "")
SENDER_PASSWORD = os.environ.get("Sender_Password", "")

def send_email(to_email, subject, body):
    """
    Sends an email via Gmail/Google Workspace SMTP using credentials from environment variables.
    """
    try:
        if not SENDER_EMAIL or not SENDER_PASSWORD:
            raise ValueError("Missing email credentials (Sender_Email or Sender_Password).")

        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        # Connect securely to Gmail SMTP
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        print(f"[INFO] Email sent successfully to {to_email}")
        return True

    except Exception as e:
        print(f"[ERROR] send_email failed: {e}")
        return False
