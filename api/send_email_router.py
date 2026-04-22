"""
send_email_router.py — API endpoint to email quiz results to the student.
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List

from send_email import _send_email

router = APIRouter(prefix="/lessons", tags=["Email Results"])


class QuestionResult(BaseModel):
    question_number: int
    question: str
    user_answer: str
    grading_result: str
    tutor_feedback: str = ""


class EmailResultsRequest(BaseModel):
    recipient_email: str = Field(..., description="Student email to send results to")
    lesson_number: int = Field(..., ge=1)
    score: int = Field(..., ge=0)
    total: int = Field(..., ge=1)
    results: List[QuestionResult]


@router.post("/{lesson_number}/email-results")
def email_quiz_results(lesson_number: int, body: EmailResultsRequest):
    """Build and send an HTML email with the quiz results."""

    # Build HTML
    rows = ""
    for r in body.results:
        is_correct = "CORRECT" in r.grading_result.upper() and "INCORRECT" not in r.grading_result.upper()
        color = "#16a34a" if is_correct else "#dc2626"
        bg = "#f0fdf4" if is_correct else "#fef2f2"
        badge = "Correct" if is_correct else "Incorrect"

        rows += f"""
        <div style="background:{bg}; border-radius:8px; padding:14px 16px; margin-bottom:10px;">
            <div style="display:flex; justify-content:space-between; margin-bottom:8px;">
                <strong style="color:#2563eb;">Q{r.question_number}</strong>
                <span style="color:{color}; font-weight:600; font-size:13px;">{badge}</span>
            </div>
            <p style="margin:0 0 6px; color:#1e293b; font-size:14px;"><strong>Question:</strong> {r.question}</p>
            <p style="margin:0 0 6px; color:#334155; font-size:14px;"><strong>Your answer:</strong> {r.user_answer}</p>
            <p style="margin:0; color:#555; font-size:13px;">{r.grading_result}</p>
            {"<p style='margin:6px 0 0; color:#374151; font-size:13px;'><em>" + r.tutor_feedback + "</em></p>" if r.tutor_feedback else ""}
        </div>
        """

    percentage = round((body.score / body.total) * 100)
    score_color = "#16a34a" if percentage >= 60 else "#dc2626"

    html = f"""
    <div style="font-family:Arial,sans-serif; max-width:600px; margin:0 auto; padding:30px;">
        <h2 style="color:#2563eb; text-align:center; margin-bottom:4px;">Quiz Mock Master</h2>
        <p style="text-align:center; color:#64748b; font-size:14px;">Quiz Results — Lesson {body.lesson_number}</p>

        <div style="text-align:center; margin:24px 0; padding:20px; background:#f8fafc; border-radius:12px;">
            <div style="font-size:42px; font-weight:700; color:{score_color};">{body.score} / {body.total}</div>
            <div style="font-size:14px; color:#64748b; margin-top:4px;">{percentage}% correct</div>
        </div>

        <h3 style="color:#1e293b; font-size:16px; margin-bottom:12px;">Detailed Results</h3>
        {rows}

        <hr style="border:none; border-top:1px solid #e2e8f0; margin:24px 0;" />
        <p style="color:#94a3b8; font-size:12px; text-align:center;">— Lesson Quiz Assessment System</p>
    </div>
    """

    subject = f"Quiz Results: Lesson {body.lesson_number} — {body.score}/{body.total} ({percentage}%)"
    result = _send_email(body.recipient_email, subject, html)

    if result.startswith("Error"):
        raise HTTPException(status_code=500, detail=result)

    return {"status": "success", "message": result}
