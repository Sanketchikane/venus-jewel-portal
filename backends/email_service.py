import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
ADMIN_EMAIL = "admin@venusjewel.com"
ADMIN_PASSWORD = "YOUR_APP_PASSWORD"

def send_email(to_email, subject, html_body):
    msg = MIMEMultipart()
    msg['From'] = ADMIN_EMAIL
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))
    
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(ADMIN_EMAIL, ADMIN_PASSWORD)
            server.send_message(msg)
        print(f"✅ Email sent to {to_email}")
    except Exception as e:
        print(f"❌ Email failed to {to_email}: {e}")
