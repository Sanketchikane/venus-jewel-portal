import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(to_email, subject, body, cc_admin=True):
    """
    Send an email with credentials using Gmail SMTP (App Password required).
    - Reads Sender_Email and Sender_Password from environment.
    - Optionally CCs admin to confirm successful delivery.
    Returns True if sent, False if error.
    """

    sender_email = os.environ.get("Sender_Email")
    sender_password = os.environ.get("Sender_Password")

    if not sender_email or not sender_password:
        print("[ERROR] Missing environment variables Sender_Email or Sender_Password.")
        return False

    if not to_email:
        print("[ERROR] No recipient email specified.")
        return False

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    recipients = [to_email]
    if cc_admin:
        recipients.append(sender_email)
        msg["Cc"] = sender_email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipients, msg.as_string())
        print(f"[EMAIL SENT] To: {to_email} | Subject: {subject}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL ERROR] Authentication failed — check Gmail App Password: {e}")
        return False
    except smtplib.SMTPRecipientsRefused:
        print(f"[EMAIL ERROR] Recipient refused: {to_email}")
        return False
    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        return False
