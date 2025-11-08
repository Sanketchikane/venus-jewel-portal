import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ⚙️ Gmail/Workspace SMTP configuration
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "noreply@venusjewel.com"  # change to your admin workspace ID
SENDER_PASSWORD = "your_app_password_here"  # use Gmail App Password (not normal password)

def send_email_notification(to_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SENDER_EMAIL, SENDER_PASSWORD)
            server.send_message(msg)

        print(f"[INFO] Email sent to {to_email}")
        return True
    except Exception as e:
        print(f"[ERROR] send_email_notification: {e}")
        return False
