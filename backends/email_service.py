# backends/email_service.py
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# ✅ Ensure environment loads even inside Render submodules
load_dotenv()

"""
Environment variables required:
- Sender_Email         : Gmail sender address (required)
- Sender_Password      : Gmail App Password (required)
Optional:
- Sender_SMTP          : default smtp.gmail.com
- Sender_PORT          : 465 (SSL) or 587 (TLS)
- Sender_USE_TLS       : "true" if STARTTLS, else SSL
- Sender_CC_ADMIN      : "true" if admin should receive a CC
"""

def send_email(to_email, subject, body, cc_admin=True, html_body=None):
    sender_email = os.environ.get("Sender_Email")
    sender_password = os.environ.get("Sender_Password")
    smtp_host = os.environ.get("Sender_SMTP", "smtp.gmail.com")
    smtp_port = int(os.environ.get("Sender_PORT", "465"))
    use_tls = os.environ.get("Sender_USE_TLS", "false").lower() in ("true", "1", "yes")

    if not sender_email or not sender_password:
        print("[EMAIL][ERROR] Missing environment vars: Sender_Email / Sender_Password")
        return False
    if not to_email:
        print("[EMAIL][ERROR] No recipient specified.")
        return False

    msg = MIMEMultipart("alternative") if html_body else MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    recipients = [to_email]
    if cc_admin:
        msg["Cc"] = sender_email
        recipients.append(sender_email)

    msg.attach(MIMEText(body, "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    print(f"[EMAIL][DEBUG] Trying {smtp_host}:{smtp_port} as {sender_email} (TLS={use_tls})")

    try:
        if use_tls:
            # STARTTLS
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
            server.starttls(context=ssl.create_default_context())
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipients, msg.as_string())
            server.quit()
        else:
            # SSL
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=20) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipients, msg.as_string())

        print(f"[EMAIL][SENT] ✅ To: {to_email}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL][AUTH ERROR] {e}")
        return False
    except Exception as e:
        print(f"[EMAIL][ERROR] Unexpected: {e}")
        return False
