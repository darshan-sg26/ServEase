import asyncio
import base64
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.core.config import settings

logger = logging.getLogger(__name__)

GMAIL_SEND_SCOPE = "https://www.googleapis.com/auth/gmail.send"

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

def check_email_service_status() -> dict:
    """
    Returns a safe diagnostic dictionary indicating whether Gmail API and SMTP
    configurations are loaded, without exposing secret values or tokens.
    """
    return {
        "GMAIL_CLIENT_ID_configured": bool(settings.GMAIL_CLIENT_ID),
        "GMAIL_CLIENT_SECRET_configured": bool(settings.GMAIL_CLIENT_SECRET),
        "GMAIL_REFRESH_TOKEN_configured": bool(settings.GMAIL_REFRESH_TOKEN),
        "GMAIL_SENDER_EMAIL": settings.GMAIL_SENDER_EMAIL,
        "GMAIL_FROM_NAME": settings.GMAIL_FROM_NAME,
        "SMTP_USER_configured": bool(settings.SMTP_USER),
        "SMTP_PASSWORD_configured": bool(settings.SMTP_PASSWORD),
        "SMTP_HOST": settings.SMTP_HOST,
        "SMTP_PORT": settings.SMTP_PORT,
    }

def check_gmail_api_status() -> dict:
    """Backward compatibility alias for check_email_service_status."""
    return check_email_service_status()

def _send_gmail_api_sync(to_email: str, subject: str, html_content: str, text_content: str):
    """
    Synchronous helper executed in thread pool that constructs and dispatches
    the email via the official Google Gmail API over HTTPS (port 443).
    """
    token = (settings.GMAIL_REFRESH_TOKEN or "").strip().strip("'\"")
    client_id = (settings.GMAIL_CLIENT_ID or "").strip().strip("'\"")
    client_secret = (settings.GMAIL_CLIENT_SECRET or "").strip().strip("'\"")

    if not client_id or not client_secret or not token:
        raise RuntimeError("Gmail API OAuth credentials (CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN) are not fully configured.")

    creds = Credentials(
        token=None,
        refresh_token=token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=[GMAIL_SEND_SCOPE],
    )

    service = build("gmail", "v1", credentials=creds, cache_discovery=False)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    from_name = settings.GMAIL_FROM_NAME or "ServEase"
    from_addr = settings.GMAIL_SENDER_EMAIL or "servease.dev@gmail.com"
    msg["From"] = formataddr((from_name, from_addr))
    msg["To"] = to_email

    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    body = {"raw": raw}

    try:
        service.users().messages().send(userId="me", body=body).execute()
        logger.info(f"Verification email successfully dispatched to {to_email} via Google Gmail API.")
    except Exception as e:
        logger.error(f"Failed to dispatch email via Google Gmail API to {to_email}: {e}")
        raise RuntimeError(f"Gmail API delivery failed: {str(e)}")

def _send_smtp_sync(to_email: str, subject: str, html_content: str, text_content: str):
    """
    Synchronous SMTP helper that sends email via configured SMTP server
    (e.g., smtp.gmail.com on port 587 with STARTTLS or port 465 with SSL).
    """
    smtp_user = (settings.SMTP_USER or "").strip().strip("'\"")
    smtp_pwd = (settings.SMTP_PASSWORD or "").replace(" ", "").strip().strip("'\"")

    if not smtp_user or not smtp_pwd:
        raise RuntimeError("SMTP credentials (SMTP_USER, SMTP_PASSWORD) are not fully configured.")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    from_name = settings.SMTP_FROM_NAME or settings.GMAIL_FROM_NAME or "ServEase"
    from_addr = smtp_user
    msg["From"] = formataddr((from_name, from_addr))
    msg["To"] = to_email

    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    if settings.SMTP_PORT == 465:
        with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.login(smtp_user, smtp_pwd)
            server.sendmail(from_addr, [to_email], msg.as_string())
    else:
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(smtp_user, smtp_pwd)
            server.sendmail(from_addr, [to_email], msg.as_string())

    logger.info(f"Verification email successfully dispatched to {to_email} via SMTP ({settings.SMTP_HOST}:{settings.SMTP_PORT}).")

def _dispatch_email_sync(to_email: str, subject: str, html_content: str, text_content: str):
    """
    Dispatches email using available service providers:
    1. First attempts Google Gmail API over HTTPS (port 443).
    2. If Gmail API fails or is unconfigured, attempts SMTP delivery as fallback.
    """
    errors = []

    # 1. Try Gmail API if credentials are provided
    has_gmail_oauth = bool(
        settings.GMAIL_CLIENT_ID
        and settings.GMAIL_CLIENT_SECRET
        and settings.GMAIL_REFRESH_TOKEN
    )
    if has_gmail_oauth:
        try:
            _send_gmail_api_sync(to_email, subject, html_content, text_content)
            return
        except Exception as e:
            errors.append(f"Gmail API error: {e}")
            logger.warning(f"Gmail API delivery attempt failed for {to_email}: {e}. Checking for SMTP fallback...")

    # 2. Try SMTP if credentials are provided
    has_smtp = bool(settings.SMTP_USER and settings.SMTP_PASSWORD)
    if has_smtp:
        try:
            _send_smtp_sync(to_email, subject, html_content, text_content)
            return
        except Exception as e:
            errors.append(f"SMTP error: {e}")
            logger.error(f"SMTP delivery attempt failed for {to_email}: {e}")

    # 3. If neither method succeeded, raise error detailing failure
    if not has_gmail_oauth and not has_smtp:
        raise RuntimeError("No email service is configured. Please configure Gmail API OAuth credentials or SMTP credentials.")

    err_summary = "; ".join(errors)
    raise RuntimeError(f"Email delivery failed across all available methods: {err_summary}")

async def send_otp_email(to_email: str, otp: str, recipient_name: str = "") -> bool:
    """
    Asynchronously dispatches a branded verification OTP email to the user.
    Uses Google Gmail API over HTTPS (port 443) with automatic SMTP fallback.
    """
    subject = f"{otp} is your ServEase verification code"
    html_content = _build_html_email(otp, recipient_name, settings.OTP_EXPIRE_MINUTES)
    text_content = (
        f"SERVEASE - Account Verification\n\n"
        f"Your verification code is: {otp}\n\n"
        f"This code will expire in {settings.OTP_EXPIRE_MINUTES} minutes.\n"
        f"If you did not request this verification, please safely ignore this email.\n"
    )

    await asyncio.to_thread(_dispatch_email_sync, to_email, subject, html_content, text_content)
    return True

