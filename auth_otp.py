"""
auth_otp.py — OTP generation and email delivery via Gmail SMTP.

Generates a 6-digit OTP, stores it in-memory with expiry,
and sends it to the recipient using Gmail SMTP (App Password).
"""

import os
import random
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load .env from the repo root (one level above Project1/)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(_env_path)

# ---------------------------------------------------------------------------
# Gmail SMTP configuration (from .env)
# ---------------------------------------------------------------------------
GMAIL_SENDER = os.getenv("GMAIL_SENDER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_RECIPIENT = os.getenv("GMAIL_RECIPIENT")

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL

# ---------------------------------------------------------------------------
# In-memory OTP store: { email: { "otp": str, "expires_at": float } }
# ---------------------------------------------------------------------------
_otp_store: dict[str, dict] = {}

OTP_EXPIRY_SECONDS = 300  # 5 minutes


def generate_otp() -> str:
    """Return a random 6-digit OTP string."""
    return str(random.randint(100000, 999999))


def send_otp_email(recipient_email: str) -> str:
    """
    Generate an OTP, store it, and send it to the given email address.

    Returns the OTP for testing convenience (production should not expose this).
    Raises RuntimeError if SMTP credentials are missing or sending fails.
    """
    if not GMAIL_SENDER or not GMAIL_APP_PASSWORD:
        raise RuntimeError(
            "Gmail SMTP credentials not configured. "
            "Set GMAIL_SENDER and GMAIL_APP_PASSWORD in .env"
        )

    otp = generate_otp()

    # Store with expiry
    _otp_store[recipient_email] = {
        "otp": otp,
        "expires_at": time.time() + OTP_EXPIRY_SECONDS,
    }

    # Build HTML email for OTP
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 480px; margin: 0 auto; padding: 30px;">
        <h2 style="color: #2563eb; text-align: center;">Quiz Mock Master</h2>
        <p>Hello,</p>
        <p>Your one-time password (OTP) is:</p>
        <div style="text-align: center; margin: 24px 0;">
            <span style="font-size: 32px; font-weight: 700; letter-spacing: 8px; color: #1e293b;
                         background: #f1f5f9; padding: 12px 24px; border-radius: 8px;">{otp}</span>
        </div>
        <p>This code expires in <strong>{OTP_EXPIRY_SECONDS // 60} minutes</strong>.</p>
        <p style="color: #94a3b8; font-size: 13px;">If you did not request this, please ignore this email.</p>
        <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;" />
        <p style="color: #94a3b8; font-size: 12px; text-align: center;">— Lesson Quiz Assessment System</p>
    </div>
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = GMAIL_SENDER
    msg["To"] = recipient_email
    msg["Subject"] = "Your OTP Code — Lesson Quiz Assessment"
    msg.attach(MIMEText(html_body, "html"))

    # Send via Gmail SMTP (SSL on port 465)
    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
        server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
        server.send_message(msg)

    return otp


def verify_otp(email: str, otp: str) -> bool:
    """
    Verify the OTP for the given email.

    Returns True if valid and not expired, False otherwise.
    Consumed on successful verification (one-time use).
    """
    record = _otp_store.get(email)
    if not record:
        return False

    if time.time() > record["expires_at"]:
        _otp_store.pop(email, None)
        return False

    if record["otp"] != otp:
        return False

    # Consume the OTP after successful verification
    _otp_store.pop(email, None)
    return True
