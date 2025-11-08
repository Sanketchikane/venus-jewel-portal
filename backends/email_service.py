# backends/email_service.py
import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email(to_email, subject, body):
    """
    Send an email using the configured Gmail account (via App Password).
    Environment variables:
      Sender_Email
      Sender_Password
    """
    sender_email = os.environ.get("Sender_Email")
    sender_password = os.environ.get("Sender_Password")

    if not sender_email or not sender_password:
        print("[ERROR] Missing Sender_Email or Sender_Password env variable.")
        return False

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        print(f"[EMAIL SENT] → {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False
