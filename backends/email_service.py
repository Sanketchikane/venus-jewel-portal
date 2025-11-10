# backends/email_service.py
import smtplib, ssl, os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config

def send_email(to_email, subject, body, cc_admin=True, html_body=None):
    if not config.EMAIL_ENABLED:
        print("[EMAIL] EMAIL_DISABLED - skipping send")
        return False

    sender_email = config.SENDER_EMAIL
    sender_password = config.SENDER_PASSWORD
    smtp_host = config.SENDER_SMTP
    smtp_port_env = config.SENDER_PORT
    use_starttls = config.SENDER_USE_TLS
    cc_admin_default = config.SENDER_CC_ADMIN

    if not sender_email or not sender_password:
        print("[EMAIL][ERROR] Missing Sender_Email or Sender_Password env.")
        return False

    msg = MIMEMultipart("alternative") if html_body else MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject

    recipients = [to_email]
    if cc_admin and cc_admin_default:
        msg["Cc"] = sender_email
        recipients.append(sender_email)

    txt = MIMEText(body, "plain", "utf-8")
    msg.attach(txt)
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    # choose port
    try:
        port = int(smtp_port_env) if smtp_port_env else (587 if use_starttls else 465)
    except Exception:
        port = 587 if use_starttls else 465

    try:
        if use_starttls:
            server = smtplib.SMTP(smtp_host, port, timeout=20)
            server.ehlo()
            server.starttls(context=ssl.create_default_context())
            server.ehlo()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipients, msg.as_string())
            server.quit()
        else:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(smtp_host, port, context=context, timeout=20) as server:
                server.login(sender_email, sender_password)
                server.sendmail(sender_email, recipients, msg.as_string())
        print(f"[EMAIL][SENT] to={to_email} subject={subject}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print("[EMAIL][ERROR] Authentication failed:", e)
        return False
    except Exception as e:
        print("[EMAIL][ERROR] Unexpected error sending email:", e)
        return False
