# backends/email_service.py
import os
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

"""
Robust email sender used by admin_backend.create_credentials_from_request and reset flows.

Environment variables:
- Sender_Email         (required) : sender email address (Gmail recommended)
- Sender_Password      (required) : app password (Gmail App Password) or SMTP password
- Sender_SMTP          (optional) : SMTP host (default smtp.gmail.com)
- Sender_PORT          (optional) : SMTP port (default 465 for SSL; 587 for STARTTLS)
- Sender_USE_TLS       (optional) : "true" to use STARTTLS (port 587) otherwise SSL on port 465
- Sender_CC_ADMIN      (optional) : "true" to add sender as CC by default
"""

def send_email(to_email, subject, body, cc_admin=True, html_body=None):
    """
    Send an email. Returns True on success, False on failure.
    - to_email: recipient email (string)
    - subject: subject string
    - body: plain-text body
    - cc_admin: boolean whether to CC sender (admin)
    - html_body: optional HTML body string (if provided message will be multipart/alternative)
    """

    # Load config from environment
    sender_email = os.environ.get("Sender_Email")
    sender_password = os.environ.get("Sender_Password")
    smtp_host = os.environ.get("Sender_SMTP", "smtp.gmail.com")
    smtp_port_env = os.environ.get("Sender_PORT", "")
    use_tls_env = os.environ.get("Sender_USE_TLS", "").lower()
    cc_admin_env = os.environ.get("Sender_CC_ADMIN", "").lower()

    # Interpret booleans
    use_starttls = use_tls_env in ("1", "true", "yes", "y")
    default_cc_admin = cc_admin_env in ("1", "true", "yes", "y")
    if cc_admin is None:
        cc_admin = default_cc_admin

    # choose default port if not provided
    if smtp_port_env:
        try:
            smtp_port = int(smtp_port_env)
        except Exception:
            smtp_port = 465 if not use_starttls else 587
    else:
        smtp_port = 587 if use_starttls else 465

    # Basic validation
    if not sender_email or not sender_password:
        print("[EMAIL][ERROR] Missing Sender_Email or Sender_Password environment variables.")
        return False
    if not to_email or not isinstance(to_email, str):
        print("[EMAIL][ERROR] Invalid recipient email.")
        return False

    # Build message
    msg = MIMEMultipart("alternative") if html_body else MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject

    # Prepare recipients list
    recipients = [to_email]
    if cc_admin:
        msg["Cc"] = sender_email
        recipients.append(sender_email)

    # Attach plain text and optionally HTML
    txt = MIMEText(body, "plain", "utf-8")
    msg.attach(txt)
    if html_body:
        html = MIMEText(html_body, "html", "utf-8")
        msg.attach(html)

    # Send mail (support both SSL and STARTTLS)
    try:
        if use_starttls:
            # STARTTLS flow (port usually 587)
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=20)
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipients, msg.as_string())
            server.quit()
        else:
            # SSL flow (port usually 465)
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=20) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipients, msg.as_string())

        print(f"[EMAIL][SENT] to={to_email} subject={subject}")
        return True

    except smtplib.SMTPAuthenticationError as e:
        print(f"[EMAIL][ERROR] Authentication failed: {e}")
        return False
    except smtplib.SMTPRecipientsRefused as e:
        print(f"[EMAIL][ERROR] Recipient refused: {e}")
        return False
    except Exception as e:
        print(f"[EMAIL][ERROR] Unexpected error sending email: {e}")
        return False
