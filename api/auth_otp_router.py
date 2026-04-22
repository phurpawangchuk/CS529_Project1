"""
auth_otp_router.py — API endpoints for OTP authentication via email.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from auth_otp import send_otp_email, verify_otp, GMAIL_RECIPIENT

router = APIRouter(prefix="/auth", tags=["Authentication"])


class SendOTPRequest(BaseModel):
    email: str = Field(
        default=None,
        description="Recipient email. Defaults to GMAIL_RECIPIENT from .env if omitted.",
    )


class VerifyOTPRequest(BaseModel):
    email: str = Field(..., description="Email the OTP was sent to")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


@router.get("/check")
def auth_check():
    """Check if OTP authentication is required (disabled on HF Spaces where SMTP is blocked)."""
    skip = bool(os.getenv("SPACE_ID"))
    return {"otp_required": not skip}


@router.post("/send-otp")
def send_otp(body: SendOTPRequest = SendOTPRequest()):
    """Generate and send an OTP to the given email address."""
    recipient = body.email or GMAIL_RECIPIENT
    if not recipient:
        raise HTTPException(
            status_code=400,
            detail="No recipient email provided and GMAIL_RECIPIENT is not set in .env",
        )

    try:
        send_otp_email(recipient)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send OTP: {e}")

    return {"message": f"OTP sent to {recipient}", "email": recipient}


@router.post("/verify-otp")
def verify(body: VerifyOTPRequest):
    """Verify the OTP code for the given email."""
    if verify_otp(body.email, body.otp):
        return {"verified": True, "message": "OTP verified successfully"}

    raise HTTPException(status_code=401, detail="Invalid or expired OTP")
