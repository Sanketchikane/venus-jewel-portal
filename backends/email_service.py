# backends/email_service.py
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

SENDER_EMAIL = os.environ.get("Sender_Email", "")
SENDER_PASSWORD = os.environ.get("Sender_Password", "")

def send_email(to_email, subject, body):
    """Send plain text email via Gmail SMTP using app password."""
    try:
        if not SENDER_EMAIL or not SENDER_PASSWORD:
            raise ValueError("Missing Sender_Email or Sender_Password environment variable.")

        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        print(f"[INFO] Email sent successfully to {to_email}")
        return True
    except Exception as e:
        print(f"[ERROR] send_email failed: {e}")
        return False
