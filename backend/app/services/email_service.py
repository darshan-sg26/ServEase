import asyncio
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from app.core.config import settings

def _build_html_email(otp: str, recipient_name: str, expire_minutes: int) -> str:
    """
    Renders a responsive, high-aesthetic HTML email template for ServEase OTP verification.
    """
    display_name = recipient_name.strip() if recipient_name and recipient_name.strip() else "User"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ServEase Account Verification</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background-color: #F6F2E9;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      color: #12140F;
    }}
    .email-container {{
      max-width: 540px;
      margin: 40px auto;
      background: #FFFFFF;
      border-radius: 16px;
      border: 1px solid #E3DCC9;
      overflow: hidden;
      box-shadow: 0 4px 20px rgba(22, 36, 31, 0.08);
    }}
    .header {{
      background-color: #16241F;
      padding: 32px 24px;
      text-align: center;
    }}
    .brand-title {{
      color: #FFFFFF;
      font-size: 26px;
      font-weight: 700;
      letter-spacing: -0.5px;
      margin: 0;
    }}
    .brand-subtitle {{
      color: #C9A227;
      font-size: 13px;
      font-weight: 600;
      margin-top: 6px;
      text-transform: uppercase;
      letter-spacing: 1.5px;
    }}
    .content {{
      padding: 36px 32px;
      text-align: center;
    }}
    .greeting {{
      font-size: 20px;
      font-weight: 700;
      color: #16241F;
      margin-top: 0;
      margin-bottom: 12px;
    }}
    .instruction {{
      font-size: 15px;
      color: #4A5049;
      line-height: 1.6;
      margin-bottom: 28px;
    }}
    .otp-box {{
      background: #EFE9DA;
      border: 2px dashed #C9A227;
      border-radius: 12px;
      padding: 20px;
      margin: 0 auto 28px;
      display: inline-block;
      min-width: 240px;
    }}
    .otp-code {{
      font-family: 'Courier New', Courier, monospace;
      font-size: 36px;
      font-weight: 800;
      letter-spacing: 10px;
      color: #16241F;
      margin: 0;
      padding-left: 10px;
    }}
    .badge-expiry {{
      display: inline-block;
      font-size: 13px;
      font-weight: 600;
      color: #B3412E;
      background: #FDF2F0;
      border: 1px solid #F6D5D0;
      padding: 6px 14px;
      border-radius: 20px;
      margin-bottom: 24px;
    }}
    .security-notice {{
      border-top: 1px solid #EFE9DA;
      padding-top: 20px;
      font-size: 13px;
      color: #7D857C;
      line-height: 1.5;
    }}
    .footer {{
      background-color: #F6F2E9;
      padding: 20px;
      text-align: center;
      font-size: 12px;
      color: #7D857C;
      border-top: 1px solid #E3DCC9;
    }}
  </style>
</head>
<body>
  <div class="email-container">
    <div class="header">
      <h1 class="brand-title">ServEase</h1>
      <div class="brand-subtitle">Skilled Workforce Marketplace</div>
    </div>
    <div class="content">
      <h2 class="greeting">Verify Your Email Address</h2>
      <p class="instruction">
        Hello <strong>{display_name}</strong>,<br>
        Thank you for joining ServEase. Use the 6-digit verification code below to complete your account registration:
      </p>
      <div class="otp-box">
        <div class="otp-code">{otp}</div>
      </div>
      <div>
        <span class="badge-expiry">⏱ Valid for {expire_minutes} minutes</span>
      </div>
      <div class="security-notice">
        If you did not request this registration, you can safely ignore this email.<br>
        <strong>Never share this OTP with anyone.</strong>
      </div>
    </div>
    <div class="footer">
      © 2026 ServEase • Secure Digital Trust Platform
    </div>
  </div>
</body>
</html>
"""

def _send_smtp_sync(to_email: str, subject: str, html_content: str, text_content: str):
    """
    Synchronous SMTP delivery helper executed in worker thread.
    """
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((settings.SMTP_FROM_NAME, settings.SMTP_USER))
    msg["To"] = to_email

    # Attach plain text and HTML alternatives
    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    if settings.SMTP_PORT == 465:
        # SSL
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, [to_email], msg.as_string())
    else:
        # STARTTLS (default 587)
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USER, [to_email], msg.as_string())

async def send_otp_email(to_email: str, otp: str, recipient_name: str = "") -> bool:
    """
    Asynchronously dispatches a branded verification OTP email to the user via Gmail SMTP.
    """
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        raise RuntimeError("SMTP_USER and SMTP_PASSWORD must be configured in environment variables.")

    subject = f"{otp} is your ServEase verification code"
    html_content = _build_html_email(otp, recipient_name, settings.OTP_EXPIRE_MINUTES)
    text_content = (
        f"SERVEASE - Account Verification\n\n"
        f"Your verification code is: {otp}\n\n"
        f"This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.\n"
        f"If you did not request this verification, please safely ignore this email.\n"
    )

    # Run blocking smtplib network I/O in thread pool to prevent blocking FastAPI event loop
    await asyncio.to_thread(_send_smtp_sync, to_email, subject, html_content, text_content)
    return True
