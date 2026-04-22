"""
send_email.py — Email Sender Agent Tool

Exposes a @function_tool that sends an email via Gmail SMTP using App Password.
Can be used by the orchestrator to email quiz results to the student.

Requires these variables in .env:
    GMAIL_APP_PASSWORD  — Gmail App Password (not your regular password)
    GMAIL_SENDER        — Sender email address
    GMAIL_RECIPIENT     — Default recipient email address

Pattern reference: 4_AgenticPatterns/tools/functionastool.ipynb (@function_tool)
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv
from agents import Agent, function_tool

# Load .env from the repo root (one level above Project1/)
_env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(_env_path)

# ---------------------------------------------------------------------------
# Gmail SMTP configuration
# ---------------------------------------------------------------------------
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
GMAIL_SENDER = os.getenv("GMAIL_SENDER")
GMAIL_RECIPIENT = os.getenv("GMAIL_RECIPIENT")
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # SSL (port 587 STARTTLS times out on this network)


def _send_email(to_email: str, subject: str, body: str) -> str:
    """Send an email via Gmail SMTP SSL. Returns a status message."""
    if not GMAIL_APP_PASSWORD or not GMAIL_SENDER:
        return "Error: GMAIL_APP_PASSWORD or GMAIL_SENDER not configured in .env"

    msg = MIMEMultipart()
    msg["From"] = GMAIL_SENDER
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.login(GMAIL_SENDER, GMAIL_APP_PASSWORD)
            server.send_message(msg)
        return f"Email sent successfully to {to_email}"
    except smtplib.SMTPAuthenticationError:
        return "Error: Gmail authentication failed. Check GMAIL_APP_PASSWORD."
    except Exception as e:
        return f"Error sending email: {str(e)}"


# ---------------------------------------------------------------------------
# Function tool — send email (used by orchestrator agent)
# ---------------------------------------------------------------------------
@function_tool
def send_quiz_results_email_agent(
    recipient_email: str,
    subject: str,
    body: str,
) -> str:
    """
    Send an email with quiz results or feedback to the student.

    Args:
        recipient_email: The student's email address.
        subject:         Email subject line.
        body:            Email body content (supports HTML).

    Returns:
        A status message confirming delivery or describing the error.
    """
    return _send_email(recipient_email, subject, body)
